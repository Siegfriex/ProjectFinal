"""E001 배치 오케스트레이터 — `E001_PLAN`을 append-only batch로 순회한다.

이 모듈이 하는 일은 정확히 네 가지이며, 전부 이 파일 안에서 조립만 한다
(엔진 재구현 없음):

1. 진입점에서 **두 개의 독립된** REAL_TARGET firewall을 통과해야 한다 —
   `layer_firewall.assert_batch_execution_mode_safe`(이 층 고유)와
   `landing_accessibility.engine.firewall.assert_mode_allowed`(엔진 정본).
2. `plan`을 `batch_size`씩 잘라 순회하고, target 하나는 `executor.py`의
   FIXTURE 실행기(또는 테스트가 주입한 `target_executor`)로 실행한다.
3. target 실행은 `retry.run_with_retry`로 감싸 정확히 1회까지만 재시도한다.
4. batch 하나가 끝나면 `ledger.BatchLedger`로 봉인한다 — 실패한 target이
   있어도 batch 자체는 끝까지 순회하고 봉인한다(격리).

## 기본 실행기는 L0 + L1 이다 (2026-08-27 시정)

`_default_fixture_executor`는 처음에는 `executor.run_l0`만 불렀다 — L1(Scout)은
`target_executor=runner.l1_executor`를 호출부가 **명시적으로 넘겨야만** 실행되는
opt-in 이었다. Claude A가 그 구조를 지적했다: "W8이 지적한 '기본 executor가
L0-only'는 지금 반드시 해소하라 — 모든 run에서 L0와 L1이 함께 켜져야 한다."

그래서 이제 `_default_fixture_executor`는 `executor.run_l1_if_safe`를 부른다 —
L0 관측을 먼저 하고, 계정 행동 가드를 통과한 target만 Scout(L1)까지 이어서
돈다. `l1_executor`는 하위 호환을 위해 남겨두되(`target_executor=runner.
l1_executor`를 명시적으로 넘기는 기존 호출부가 깨지지 않게) 이제는
`_default_fixture_executor`와 **완전히 같은 코드 경로**를 탄다 — "L1은 opt-in"
이라는 구조 자체가 없어졌다.

가드는 전혀 약화되지 않는다 — `run_l1_if_safe`가 걸리면 여전히 `Scout`를
아예 만들지 않는다(`tests/test_e001_account_action_guard.py`,
`tests/test_e001_default_executor_l0_l1.py` 가 이제 이 사실을 **기본 경로**로도
증명한다 — 더 이상 `target_executor=runner.l1_executor`를 명시해야만 검증되는
별도 경로가 아니다).

## target 하나 전체에 대한 wall-clock 상한 (2026-08-27 추가)

L1이 기본으로 켜지면서, target 하나(L0 + Scout + Freeze/Replay, 재시도 포함)를
감싸는 **상위 시간 상한**이 없다는 것이 드러났다 — L0의 `NAV_TIMEOUT_MS`나
Scout 자신의 `ScoutBudget.max_scout_wall_clock_s`는 각자 자기 범위만 잰다.
`wall_clock.run_with_wall_clock_cap`이 `retry.run_with_retry(attempt)` 호출
**전체**를 감싼다 — `DEFAULT_TARGET_WALL_CLOCK_CAP_S`(6분) 안에 끝나지 않으면
그 target은 `TargetOutcome.TRANSPORT_FAILURE`로 기록되고 배치는 계속 순회한다.
**절대 `UNDETERMINED`(콘텐츠 판정 축)로 흡수하지 않는다** — 이건 measurement
outcome이 아니라 transport failure다(Claude A 지시, 2026-08-27).
"""

from __future__ import annotations

import fcntl
import hashlib
import json
import os
import re
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Protocol

from landing_accessibility.engine.firewall import (
    ExecutionMode,
    ExecutionScope,
    FirewallError,
    assert_mode_allowed,
)
from landing_accessibility.engine.provenance import (
    PROTOCOL_VERSION,
    RealTargetProvenance,
    ShadowProvenance,
)
from landing_accessibility.engine.vocabulary import MeasurementStatus, is_measurement_failed

from .guard import AccountActionBlockedError
from .layer_firewall import BatchRealTargetBlockedError, assert_batch_execution_mode_safe
from .ledger import BatchLedger, BatchManifest
from .outcomes import TargetOutcome, is_failure_isolated, map_engine_result
from .plan import (
    TargetSpec,
    validate_no_real_navigation_fields_required,
    validate_real_target_scope_allowlist,
)
from .retry import MAX_RETRIES_PER_TARGET, run_with_retry
from .wall_clock import (
    DEFAULT_TARGET_WALL_CLOCK_CAP_S,
    TargetWallClockExceededError,
    run_with_wall_clock_cap,
)

#: 이 lane 이 갈라져 나온 base. `landing_accessibility.engine.provenance.BASE_SHA`
#: (P-C의 base, d5f1da5)와 **다르다** (`PHASE_GATES.md §4.3` 요구대로 lane마다
#: 자기 base_sha를 적는다). 원래 `claude-b/e001-runner`(2025e56 기준)에서 시작한
#: 배치 오케스트레이션 층을, CR-001/002/003 해소 + dom_order 최신화가 끝난
#: `claude-b/integration-current`(397a10d) 위로 selective port 했다 — 이 lane의
#: base는 그래서 397a10d다.
E001_RUNNER_BASE_SHA = "397a10d"
#: `claude-b/e001-runner-l1fix` — L0-only opt-in 기본값을 L0+L1 표준 경로로
#: 시정한 lane. 이전 `E001_RUNNER`(2025e56 기준) 산출물과 구분하기 위해
#: shadow_lane 자체를 바꾼다 — provenance만으로 "이 산출물이 어느 시정 이전/
#: 이후에서 나왔는지"를 구분할 수 있어야 한다.
E001_RUNNER_SHADOW_LANE = "E001_RUNNER_L0L1_DEFAULT_FIX"

DEFAULT_BATCH_SIZE = 3


# ══════════════════════════════════════════════════════════════════════════
# Exactly-once — `T-A-W1-001` §3 (D-R0-38 · D-R0-46 · D-R0-46b)
# ══════════════════════════════════════════════════════════════════════════
#
# 근거는 가설이 아니다: 2026-08-27 05:14 worker_02 에서 프로세스 2개가 같은
# `batch_0001` target 4건을 동시에 실사이트로 두 번 발사했다(`C_CLEAN0_AUDIT §6.1`).
# 원인은 batch 원장의 **check-then-act**(먼저 존재를 확인하고 나중에 만든다) —
# 그 확인과 생성 사이의 창에서 두 번째 프로세스가 "아직 없다"를 본다.
#
# D-R0-46 이 계약을 **확정**했다(잠정 아님 — 이전 초안의 "설정 가능하게 두고
# 잠정 표시" 지시는 A의 재확정으로 대체됐다):
#
#   run_id            A 가 발행하는 **수집 회차** id. ticket 단위로 고정 — target
#                     1회 시도 식별자와 다르다(그건 `attempt_id`, D-R0-46b).
#   idempotency_key   ticket_id + run_id + target_id + collector_sha + protocol_sha
#   lock              target 단위. state ∈ {RUNNING, DONE, FAILED_RETRYABLE} + attempts
#   retry 허용조건    state == FAILED_RETRYABLE AND attempts < max
#   lock 삭제         하지 않는다(삭제하면 두 번째 프로세스가 lock 부재를 다시 본다)
#   억제 지점         `EvidenceRun.create` **이전** — 실사이트 접속 전
#   중복 시 동작      launch 하지 않고 `DUPLICATE_SUPPRESSED` event 기록
#
# `max_attempts`(재실행 상한 숫자)는 A 가 특정 값을 지정한 적이 없다 — 그래서
# `DEFAULT_MAX_LOCK_ATTEMPTS`는 합리적 기본값이고 `BatchRunner(max_lock_attempts=...)`
# 로 override 가능하게 남긴다(주석으로 잠정임을 표시). 상태 어휘·삭제 금지·억제
# 지점은 D-R0-46 로 이미 확정이므로 더 이상 잠정이 아니다.


class LockState:
    """target lock 의 상태 어휘(`D-R0-46`, 확정)."""

    RUNNING = "RUNNING"
    DONE = "DONE"
    FAILED_RETRYABLE = "FAILED_RETRYABLE"


#: 재실행(다른 프로세스 기동) 횟수 상한 — **잠정값**. `retry.MAX_RETRIES_PER_TARGET`
#: (같은 프로세스 안에서의 1회 재시도)과는 다른 축이다.
DEFAULT_MAX_LOCK_ATTEMPTS = 3

#: FIXTURE/SHADOW 배치가 `ticket_id`/`run_id`를 넘기지 않았을 때 쓰는 기본값
#: (`C-FINDING-214553` — C의 독립 감사가 지적한 구멍: lock 이 REAL_TARGET 경로에만
#: 배선돼 있어 FIXTURE 로는 "네트워크 없이 프로세스 2개 동시 기동 → 억제 1건"을
#: end-to-end 로 증명할 방법이 없었다). **REAL_TARGET 과 같은 코드 경로**를 태우되,
#: 기존 FIXTURE 테스트 수십 개를 깨뜨리지 않기 위해 값을 강제하지 않고 안전한
#: 기본값으로 채운다 — lock 디렉터리 자체가 `out_dir`(테스트마다 고유) 아래로
#: 기본 스코프되므로(`_resolve_lock_dir`), 이 상수 값이 고정이어도 서로 다른
#: 테스트끼리 lock 파일이 충돌하지 않는다.
FIXTURE_DEFAULT_TICKET_ID = "FIXTURE"
FIXTURE_DEFAULT_RUN_ID = "FIXTURE_DEFAULT_ROUND"

#: `_seal_batch`의 `TargetOutcome(...)` 캐스팅 대상이 **아니다** — `outcomes.py`는
#: 이 티켓의 소유 파일이 아니므로(소유권 경계) 새 닫힌-집합 값을 그쪽에 추가하지
#: 않는다. 이 상수는 **batch 오케스트레이션 레벨에서만** 의미를 갖는 exactly-once
#: 전용 신호이고, `TargetResult.outcome`(그냥 `str` 필드)에 담긴다. `_seal_batch`가
#: 이 값을 별도로 isolated 집계에 넣는다(아래).
DUPLICATE_SUPPRESSED_OUTCOME = "DUPLICATE_SUPPRESSED"


class ExactlyOnceConfigError(RuntimeError):
    """REAL_TARGET 배치에 idempotency key 성분(ticket_id/run_id)이 없다."""


def _default_lock_dir() -> Path:
    """`.agent_bus/landing_v2/locks/` — 저장소 공유 transport(git 미추적,
    `R0_RECOVERY_CONTRACT_v2.1.md §8` · `.gitignore`: "orchestration transport,
    not research authority"). 워크트리 안에서 돌아도 **메인 저장소의 같은 경로**를
    가리켜야 한다 — 워커마다 다른 lock 디렉터리를 보면 상호배제가 아예 성립하지
    않는다(`engine.firewall`의 `_MAIN_REPO_ROOT` 계산과 같은 패턴).
    """
    repo_root = Path(__file__).resolve().parents[5]
    if repo_root.parent.name == ".agent_worktrees":
        # 워크트리 루트(`.agent_worktrees/<name>`)에서 메인 저장소 루트로 두 단계
        # 올라간다 — `engine.firewall._MAIN_REPO_ROOT`와 같은 계산.
        repo_root = repo_root.parents[1]
    return repo_root / ".agent_bus" / "landing_v2" / "locks"


def _default_protocol_sha() -> str:
    """`idempotency_key`의 `protocol_sha` 성분 기본값 — 엔진의
    `provenance.PROTOCOL_VERSION`을 sha256으로 접는다. E000/E001이 같은 프로토콜
    버전으로 돈다는 기존 불변식(`provenance.py` 참고)을 그대로 재사용한다 — 새
    프로토콜 식별자를 발명하지 않는다."""
    return hashlib.sha256(PROTOCOL_VERSION.encode("utf-8")).hexdigest()[:16]


def _append_bus_event(event_log_path: Path, payload: dict[str, Any]) -> None:
    """공유 bus event log에 이벤트 1건을 append한다(`R0_RECOVERY_CONTRACT_v2.1.md §9`).

    이 파일은 orchestration transport이지 연구 authority가 아니다(git 미추적) —
    여기 쓰기 실패가 exactly-once **판정 자체**를 막지는 않는다: lock 판정은 이
    함수 호출 이전에 이미 `TargetLock.acquire()`로 확정돼 있다. 이 함수는 그
    확정된 판정을 감사 로그에 옮겨 적는 것뿐이라 fail-open으로 둔다.
    """
    try:
        event_log_path.parent.mkdir(parents=True, exist_ok=True)
        line = json.dumps(payload, ensure_ascii=False, sort_keys=True)
        with open(event_log_path, "a", encoding="utf-8") as handle:
            handle.write(line + "\n")
    except OSError:
        pass


@dataclass(frozen=True)
class IdempotencyKey:
    """`D-R0-46` — 다섯 성분. `run_id`는 **수집 회차 id**(ticket 단위로 고정)이지
    target 1회 시도 식별자가 아니다 — 그건 `attempt_id`(`D-R0-46b`)다."""

    ticket_id: str
    run_id: str
    target_id: str
    collector_sha: str
    protocol_sha: str

    def canonical(self) -> str:
        return "::".join(
            [self.ticket_id, self.run_id, self.target_id, self.collector_sha, self.protocol_sha]
        )

    def digest(self) -> str:
        return hashlib.sha256(self.canonical().encode("utf-8")).hexdigest()[:32]


@dataclass
class LockDecision:
    proceed: bool
    attempt_id: str | None
    lock_path: Path
    reason: str | None  # `None` 이면 `proceed=True`인 정상 판정
    prior_state: str | None = None
    prior_attempts: int = 0


class TargetLock:
    """target 단위 exactly-once lock(`D-R0-38`·`D-R0-46`).

    핵심 불변식: **lock 파일 '생성' 그 자체가 승패를 가른다.** 두 프로세스가 완전히
    같은 순간에 `acquire()`를 불러도, `os.open(path, O_CREAT|O_EXCL)`은 커널이
    직렬화한다(POSIX가 파일 생성의 원자성을 보장한다) — 정확히 하나만 생성에
    성공한다. **"존재를 먼저 확인하고 나중에 만든다"는 코드는 이 클래스 어디에도
    없다** — 그게 정확히 05:14 사고의 경로였다(batch 원장의 check-then-act).

    lock 파일이 이미 있는 경우(두 번째 요청, 또는 재실행)는 `fcntl.flock`(advisory
    exclusive lock)로 읽기-판단-쓰기 전체를 임계구역으로 감싼다 — "이미 있으니
    retry로 갱신하자"를 두 프로세스가 동시에 시도하는 두 번째 경쟁도 이걸로 막는다.
    """

    def __init__(self, lock_dir: Path | str | None = None) -> None:
        self.lock_dir = Path(lock_dir) if lock_dir is not None else _default_lock_dir()
        self.lock_dir.mkdir(parents=True, exist_ok=True)

    def _path(self, key: IdempotencyKey) -> Path:
        safe_target = re.sub(r"[^A-Za-z0-9_.-]", "_", key.target_id) or "target"
        return self.lock_dir / f"{safe_target}__{key.digest()}.lock.json"

    def acquire(
        self, key: IdempotencyKey, *, max_attempts: int = DEFAULT_MAX_LOCK_ATTEMPTS
    ) -> LockDecision:
        path = self._path(key)
        attempt_id = f"{key.target_id}-{uuid.uuid4().hex[:12]}"
        now = _utc_now_iso()
        fresh_payload = {
            "idempotency_key": key.canonical(),
            "ticket_id": key.ticket_id,
            "run_id": key.run_id,
            "target_id": key.target_id,
            "collector_sha": key.collector_sha,
            "protocol_sha": key.protocol_sha,
            "state": LockState.RUNNING,
            "attempts": 1,
            "attempt_ids": [attempt_id],
            "created_at": now,
            "updated_at": now,
        }
        try:
            fd = os.open(str(path), os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o644)
        except FileExistsError:
            pass
        else:
            # 이 프로세스가 '생성'에 이겼다 — 그 사실 자체가 exactly-once 승인이다.
            # 다른 프로세스는 이 `open()`이 끝나기 전에도 `O_EXCL`에서 이미 졌으므로
            # (파일 생성 자체가 원자적) 아래 `except FileExistsError` 분기로 간다 —
            # "생성 시도"와 "판정"이 같은 syscall 안에서 일어난다.
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                json.dump(fresh_payload, handle, ensure_ascii=False, indent=2, sort_keys=True)
            return LockDecision(proceed=True, attempt_id=attempt_id, lock_path=path, reason=None)

        with open(path, "r+", encoding="utf-8") as handle:
            fcntl.flock(handle, fcntl.LOCK_EX)
            try:
                handle.seek(0)
                raw = handle.read()
                try:
                    existing: dict[str, Any] = json.loads(raw) if raw else {}
                except json.JSONDecodeError:
                    existing = {}
                state = existing.get("state")
                attempts = int(existing.get("attempts") or 0)
                if state == LockState.FAILED_RETRYABLE and attempts < max_attempts:
                    attempts += 1
                    existing["state"] = LockState.RUNNING
                    existing["attempts"] = attempts
                    existing.setdefault("attempt_ids", []).append(attempt_id)
                    existing["updated_at"] = _utc_now_iso()
                    handle.seek(0)
                    handle.truncate()
                    json.dump(existing, handle, ensure_ascii=False, indent=2, sort_keys=True)
                    return LockDecision(
                        proceed=True,
                        attempt_id=attempt_id,
                        lock_path=path,
                        reason=None,
                        prior_state=state,
                        prior_attempts=attempts,
                    )
                return LockDecision(
                    proceed=False,
                    attempt_id=None,
                    lock_path=path,
                    reason=(
                        f"DUPLICATE_SUPPRESSED: state={state!r} attempts={attempts} "
                        f"max_attempts={max_attempts} key={key.canonical()!r}"
                    ),
                    prior_state=state,
                    prior_attempts=attempts,
                )
            finally:
                fcntl.flock(handle, fcntl.LOCK_UN)

    def mark_done(self, key: IdempotencyKey) -> None:
        self._update_state(key, LockState.DONE)

    def mark_failed_retryable(self, key: IdempotencyKey) -> None:
        self._update_state(key, LockState.FAILED_RETRYABLE)

    def _update_state(self, key: IdempotencyKey, new_state: str) -> None:
        """lock 을 **삭제하지 않는다**(D-R0-46) — 상태만 갱신한다."""
        path = self._path(key)
        if not path.is_file():
            return  # acquire 가 없었다 — 갱신할 게 없다(방어적).
        with open(path, "r+", encoding="utf-8") as handle:
            fcntl.flock(handle, fcntl.LOCK_EX)
            try:
                handle.seek(0)
                raw = handle.read()
                try:
                    existing: dict[str, Any] = json.loads(raw) if raw else {}
                except json.JSONDecodeError:
                    existing = {}
                existing["state"] = new_state
                existing["updated_at"] = _utc_now_iso()
                handle.seek(0)
                handle.truncate()
                json.dump(existing, handle, ensure_ascii=False, indent=2, sort_keys=True)
            finally:
                fcntl.flock(handle, fcntl.LOCK_UN)


class TargetExecutor(Protocol):
    def __call__(self, target: TargetSpec) -> dict[str, Any]: ...


@dataclass
class TargetResult:
    target_id: str
    outcome: str
    attempts: int
    detail: dict[str, Any] = field(default_factory=dict)
    error: str | None = None
    same_cause_on_retry: bool | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "target_id": self.target_id,
            "outcome": self.outcome,
            "attempts": self.attempts,
            "detail": self.detail,
            "error": self.error,
            "same_cause_on_retry": self.same_cause_on_retry,
        }


def _utc_now_iso() -> str:
    return datetime.now(UTC).isoformat(timespec="microseconds").replace("+00:00", "Z")


def _chunk(items: list[TargetSpec], size: int) -> list[list[TargetSpec]]:
    if size < 1:
        raise ValueError(f"batch_size 는 1 이상이어야 한다: {size}")
    return [items[i : i + size] for i in range(0, len(items), size)]


def _is_retryable_engine_failure(result: dict[str, Any]) -> bool:
    """엔진이 **내부적으로 잡아** 반환한(예외로 새지 않은) 측정 실패인가.

    `L0Collector.collect()`는 브라우저/타임아웃 오류를 스스로 catch해 `L0Observation`
    으로 돌려준다 — 예외가 아니라 `measurement_status`값으로 나타난다. 그래서 이
    검사가 없으면 그런 실패는 재시도 대상에서 조용히 빠진다. 엔진 자신의
    `is_measurement_failed` 술어를 그대로 재사용한다(재구현하지 않는다).
    """
    status = result.get("measurement_status")
    if not status:
        return False
    try:
        return is_measurement_failed(MeasurementStatus(status))
    except ValueError:
        return False


class BatchRunner:
    """`E001_PLAN`을 append-only batch로 순회하는 오케스트레이터."""

    def __init__(
        self,
        *,
        out_dir: Path | str,
        fixture_root: Path | str,
        batch_size: int = DEFAULT_BATCH_SIZE,
        target_wall_clock_cap_s: float = DEFAULT_TARGET_WALL_CLOCK_CAP_S,
        ticket_id: str | None = None,
        run_id: str | None = None,
        collector_sha: str = E001_RUNNER_BASE_SHA,
        protocol_sha: str | None = None,
        lock_dir: Path | str | None = None,
        max_lock_attempts: int = DEFAULT_MAX_LOCK_ATTEMPTS,
    ) -> None:
        self.out_dir = Path(out_dir)
        self.fixture_root = Path(fixture_root)
        self.batch_size = batch_size
        #: target 하나(재시도 포함) 전체에 허용하는 wall-clock 상한 — `wall_clock.py`.
        #: 기본값은 Claude A 확정값 6분. 테스트가 아주 짧은 값으로 override해
        #: negative test(고의로 느린 executor로 cap 초과 유도)를 검증한다.
        self.target_wall_clock_cap_s = target_wall_clock_cap_s
        self.ledger = BatchLedger(self.out_dir)
        #: 실제 수집 배치가 돌 때만 채워진다 (`_run_real`). FIXTURE 배치에서는 항상 None.
        self._real_scope: object | None = None
        # ── exactly-once (`D-R0-38`·`D-R0-46`) — REAL_TARGET 배치에서만 쓰인다 ──
        #: A 가 발행하는 **수집 회차** id. target 1회 시도 식별자(`attempt_id`)와
        #: 다르다 — 혼동하면 idempotency key가 매 시도마다 달라져 억제가 영원히
        #: 발화하지 않는다(이전 버그가 정확히 이 혼동이었다: `run_id`가 timestamp
        #: 합성이었다).
        self.ticket_id = ticket_id
        self.run_id = run_id
        self.collector_sha = collector_sha
        self.protocol_sha = protocol_sha or _default_protocol_sha()
        self.max_lock_attempts = max_lock_attempts
        #: 명시적으로 준 값만 저장한다 — 실제 디렉터리는 모드별로 다르게 기본값을
        #: 잡는다(`_resolve_lock_dir`). REAL_TARGET은 저장소 공유 transport
        #: (`.agent_bus/landing_v2/locks/`)로 기본값을 잡아야 프로세스가 달라도
        #: 상호배제가 성립하고, FIXTURE는 `out_dir` 아래로 기본값을 잡아야 서로
        #: 무관한 테스트/실행끼리 lock 파일이 공유 디렉터리를 오염시키지 않는다.
        self._lock_dir_override = lock_dir

    def _resolve_lock_dir(self, *, real: bool) -> Path:
        if self._lock_dir_override is not None:
            return Path(self._lock_dir_override)
        return _default_lock_dir() if real else (self.out_dir / "locks")

    def _target_lock(self, *, real: bool) -> TargetLock:
        return TargetLock(self._resolve_lock_dir(real=real))

    def _idempotency_components(self, *, real: bool) -> tuple[str, str]:
        """`(ticket_id, run_id)` — REAL_TARGET은 명시값을 요구하고(호출부에서
        검사), FIXTURE/SHADOW는 안전한 기본값으로 채운다(`C-FINDING-214553`)."""
        if real:
            return self.ticket_id or "", self.run_id or ""
        return self.ticket_id or FIXTURE_DEFAULT_TICKET_ID, self.run_id or FIXTURE_DEFAULT_RUN_ID

    # ── 진입점 ───────────────────────────────────────────────────────────
    def run(
        self,
        plan: list[TargetSpec],
        *,
        execution_mode: object,
        execution_scope: object | None = None,
        target_executor: TargetExecutor | None = None,
    ) -> list[BatchManifest]:
        """`plan`을 batch로 나눠 순회하고 봉인된 `BatchManifest` 목록을 돌려준다.

        scope 없는 REAL_TARGET을 요청하면 **두 firewall 모두** 통과하지 못하고 즉시
        실패한다. 어느 한쪽만 통과시켜도 이 함수는 진행하지 않는다 — 순서와 무관하게
        둘 다 호출된다. scope 가 주어진 경우에도 두 층이 **각자** 릴리스 문서를 읽어
        판정한다.
        """
        layer_mode = assert_batch_execution_mode_safe(execution_mode, execution_scope)
        engine_mode = assert_mode_allowed(execution_mode, scope=execution_scope)
        assert layer_mode == engine_mode.value  # 두 firewall이 같은 값을 봤다는 것을 명시

        if engine_mode is ExecutionMode.SHADOW_DRY_RUN:
            return [self._run_dry(plan)]

        if engine_mode is ExecutionMode.REAL_TARGET:
            return self._run_real(plan, scope=execution_scope, target_executor=target_executor)

        if engine_mode is not ExecutionMode.FIXTURE:
            # 새 execution_mode가 언젠가 추가돼도 이 함수가 조용히 통과시키지 않게 한다.
            raise FirewallError(f"이 배치 러너가 아는 모드가 아니다: {engine_mode}")

        validate_no_real_navigation_fields_required(plan)
        executor = target_executor or self._default_fixture_executor

        manifests: list[BatchManifest] = []
        for batch_index, batch_targets in enumerate(_chunk(plan, self.batch_size), start=1):
            target_results = [self._run_target_isolated(t, executor) for t in batch_targets]
            manifest = self._seal_batch(batch_index, batch_targets, target_results, "FIXTURE")
            manifests.append(manifest)
        return manifests

    # ── 실제 수집 배치 ───────────────────────────────────────────────────
    def _run_real(
        self,
        plan: list[TargetSpec],
        *,
        scope: object,
        target_executor: TargetExecutor | None = None,
    ) -> list[BatchManifest]:
        """`REAL_TARGET` + 승인된 scope 배치.

        FIXTURE 경로와 **같은** `_run_target_isolated` 를 쓴다 — 재시도 1회 상한,
        wall-clock cap, 실패 격리, 계정 행동 가드가 그대로 적용된다는 뜻이다.
        다른 것은 executor 와 provenance 뿐이다.

        exactly-once(`D-R0-38`, blocking acceptance criterion): `ticket_id`/`run_id`
        (수집 회차 id) 없이는 여기서 즉시 실패한다 — 브라우저를 한 번도 켜지 않고.
        idempotency key 의 필수 성분이 없는 채로 REAL_TARGET 을 진행시키지 않는다.
        **이 검사는 기본 executor(`self._real_executor`, lock 을 실제로 소비하는
        경로)가 쓰일 때만 발화한다** — 호출부가 `target_executor` 를 직접 주입하면
        그 executor 는 이 lock 을 아예 거치지 않으므로(예: firewall/allowlist
        자체를 검증하는 기존 테스트들이 그렇다), 그 경우까지 ticket_id/run_id 를
        강제하면 exactly-once 와 무관한 테스트를 부수는 결합이 생긴다.
        """
        if target_executor is None and (not self.ticket_id or not self.run_id):
            raise ExactlyOnceConfigError(
                "REAL_TARGET 배치는 ticket_id 와 run_id(A가 발행하는 수집 회차 id)가 "
                "있어야 한다 — exactly-once idempotency key(D-R0-46)의 필수 성분이다. "
                f"BatchRunner(ticket_id={self.ticket_id!r}, run_id={self.run_id!r})"
            )
        # 배치가 시작되기 전에 allowlist 전건 확인 — 목록 밖 target 이 하나라도 있으면
        # 브라우저를 한 번도 켜지 않고 실패한다.
        validate_real_target_scope_allowlist(plan, scope=scope)
        self._real_scope = scope
        executor = target_executor or self._real_executor

        manifests: list[BatchManifest] = []
        for batch_index, batch_targets in enumerate(_chunk(plan, self.batch_size), start=1):
            target_results = [self._run_target_isolated(t, executor) for t in batch_targets]
            manifest = self._seal_batch(
                batch_index, batch_targets, target_results, "REAL_TARGET", scope=scope
            )
            manifests.append(manifest)
        return manifests

    # ── exactly-once — REAL/FIXTURE 공유 helper (`C-FINDING-214553`) ───────
    def _acquire_launch_lock(
        self, target: TargetSpec, *, real: bool
    ) -> tuple[TargetLock, IdempotencyKey, str | None, dict[str, Any] | None]:
        """launch(=evidence run 생성/브라우저 기동) **직전**에 lock 을 소비한다.

        `real=True`면 REAL_TARGET 성분(명시적 `ticket_id`/`run_id`, 공유
        `.agent_bus/landing_v2/locks/`)을, `real=False`면 FIXTURE 기본 성분
        (`FIXTURE_DEFAULT_TICKET_ID`/`FIXTURE_DEFAULT_RUN_ID`, `out_dir` 아래
        lock 디렉터리)을 쓴다 — 코드 경로는 완전히 같다.

        반환: `(lock, key, attempt_id, suppressed_result)`. 억제되면
        `attempt_id is None`이고 `suppressed_result`가 그대로 executor의 반환값이
        된다 — 호출부는 `suppressed_result is not None`이면 즉시 그것을 돌려주고
        launch(=evidence run 생성) 코드를 실행하지 않는다.
        """
        ticket_id, run_id = self._idempotency_components(real=real)
        lock = self._target_lock(real=real)
        key = IdempotencyKey(
            ticket_id=ticket_id,
            run_id=run_id,
            target_id=target.target_id,
            collector_sha=self.collector_sha,
            protocol_sha=self.protocol_sha,
        )
        decision = lock.acquire(key, max_attempts=self.max_lock_attempts)
        if not decision.proceed:
            _append_bus_event(
                lock.lock_dir.parent / "event_log.jsonl",
                {
                    "ts": _utc_now_iso(),
                    "agent": "B",
                    "event": DUPLICATE_SUPPRESSED_OUTCOME,
                    "idempotency_key": key.canonical(),
                    "target_id": target.target_id,
                    "reason": decision.reason,
                },
            )
            suppressed = {
                "outcome": DUPLICATE_SUPPRESSED_OUTCOME,
                "scout_invoked": False,
                "idempotency_key": key.canonical(),
                "duplicate_suppressed_reason": decision.reason,
                "prior_lock_state": decision.prior_state,
                "prior_attempts": decision.prior_attempts,
            }
            return lock, key, None, suppressed

        attempt_id = decision.attempt_id or f"{target.target_id}-{uuid.uuid4().hex[:12]}"
        return lock, key, attempt_id, None

    def _real_executor(self, target: TargetSpec) -> dict[str, Any]:
        """실제 수집 executor — L0 + L1 을 함께 수행한다 (L0-only run 을 만들지 않는다).

        exactly-once(`D-R0-38`·`D-R0-46`): **`EvidenceRun.create` 이전에**(=실사이트
        접속 이전에) target lock 을 원자적으로 소비한다. 억제되면 `run_l1_if_safe_real`
        을 호출하지 않는다 — 즉 `Scout`/`L0Collector` 생성도, `playwright` 기동도,
        네트워크 접속도 **전혀 일어나지 않는다**. 이전의 `run_id`(target 1회 시도
        식별자, timestamp 합성)는 이제 `attempt_id`라고 부른다 — evidence 디렉터리
        이름으로만 쓰고 idempotency key 성분으로는 쓰지 않는다(`D-R0-46b`).
        """
        from landing_accessibility.engine.evidence import EvidenceRun

        from .real_executor import run_l1_if_safe_real

        scope = self._real_scope or ExecutionScope.E000_FAST

        lock, key, attempt_id, suppressed = self._acquire_launch_lock(target, real=True)
        if suppressed is not None:
            return suppressed

        # 이 지점을 지나야만 evidence 디렉터리가 생기고, 그 아래에서만 브라우저가
        # 뜬다 — lock 획득이 곧 "실사이트 접속 이전 억제 지점"이다(`D-R0-38`).
        assert attempt_id is not None
        run = EvidenceRun.create(
            self.out_dir / "evidence",
            attempt_id,
            execution_mode=ExecutionMode.REAL_TARGET,
            execution_scope=scope,
            provenance=RealTargetProvenance.for_scope(
                scope, base_sha=E001_RUNNER_BASE_SHA, execution_lane=E001_RUNNER_SHADOW_LANE
            ),
        )
        try:
            result = run_l1_if_safe_real(target, run=run, scope=scope)
        except Exception:
            # transient 실패(예외로 샌 것)는 재실행 가능 상태로 남긴다 — lock 을
            # 지우지 않는다. 이후 재실행이 같은 key 로 들어오면 `acquire()`가
            # FAILED_RETRYABLE + attempts<max 조건에서만 통과시킨다.
            lock.mark_failed_retryable(key)
            run.seal()
            raise
        run.seal()
        result["attempt_id"] = attempt_id
        result["idempotency_key"] = key.canonical()
        if _is_retryable_engine_failure(result):
            lock.mark_failed_retryable(key)
        else:
            # 가드 차단(`ACCOUNT_ACTION_BLOCKED`)도 여기 포함된다 — 그건 정책
            # 위반이지 transient 실패가 아니다(`retry.py`의 기존 원칙과 동일).
            lock.mark_done(key)
        return result

    # ── target 하나 ──────────────────────────────────────────────────────
    def _run_target_isolated(self, target: TargetSpec, executor: TargetExecutor) -> TargetResult:
        """target 하나를 실행한다. **여기서 던진 예외는 이 함수를 벗어나지 않는다**
        (firewall 예외 제외) — 그것이 "실패 격리"의 코드 형태다.

        `retry.run_with_retry(attempt)` 호출 전체(재시도 포함)를
        `wall_clock.run_with_wall_clock_cap`으로 한 번 더 감싼다 — "재시도 1회
        × cap"이 아니라 "이 target에 쓸 수 있는 전체 시간"이 상한이라는 뜻이다.
        """
        attempt_count = 0
        last_result: dict[str, Any] = {}

        def attempt() -> dict[str, Any]:
            nonlocal attempt_count, last_result
            attempt_count += 1  # 최선 노력 카운터 — wall-clock cap 이 발화했을 때도 보고용으로 쓴다
            result = executor(target)
            last_result = result if isinstance(result, dict) else {}
            if result.get("outcome") == TargetOutcome.ACCOUNT_ACTION_BLOCKED.value:
                raise AccountActionBlockedError(
                    f"target {target.target_id!r}: "
                    f"category={result.get('blocked_category')} "
                    f"reason={result.get('blocked_reason')}"
                )
            if _is_retryable_engine_failure(result):
                raise RuntimeError(
                    f"engine measurement_status={result.get('measurement_status')!r} "
                    f"(target={target.target_id!r})"
                )
            return result

        try:
            retry_outcome = run_with_wall_clock_cap(
                lambda: run_with_retry(attempt), cap_s=self.target_wall_clock_cap_s
            )
        except AccountActionBlockedError as exc:
            # L0 관측은 이미 끝났고 evidence 도 디스크에 있다 — 그 lineage 를 결과에서
            # 잃어버리지 않는다 (L0 산출물과 L1 종결상태가 함께 남아야 한다).
            return TargetResult(
                target_id=target.target_id,
                outcome=TargetOutcome.ACCOUNT_ACTION_BLOCKED.value,
                attempts=1,
                detail=last_result,
                error=str(exc),
            )
        except (BatchRealTargetBlockedError, FirewallError):
            raise  # firewall 위반은 격리 대상이 아니다 — 배치 전체를 세운다
        except TargetWallClockExceededError as exc:
            # Claude A 지시: 타임아웃은 transport failure다 — UNDETERMINED(콘텐츠 판정
            # 축)로 세탁하지 않는다. attempt_count 는 백그라운드 스레드가 여전히 실행
            # 중일 수 있어(daemon thread 유기) 정확한 최종값이 아니라 최선 노력 값이다.
            return TargetResult(
                target_id=target.target_id,
                outcome=TargetOutcome.TRANSPORT_FAILURE.value,
                attempts=max(attempt_count, 1),
                error=(
                    f"TIMEOUT_EXCEEDED: target wall-clock cap "
                    f"({self.target_wall_clock_cap_s}s) exceeded — {exc}"
                ),
            )

        if retry_outcome.succeeded:
            value = retry_outcome.value if isinstance(retry_outcome.value, dict) else {}
            if value.get("outcome") == DUPLICATE_SUPPRESSED_OUTCOME:
                # `outcomes.map_engine_result`(닫힌 `TargetOutcome` 집합, W1 소유
                # 파일 아님)는 `DUPLICATE_SUPPRESSED`를 모른다 — 그대로 넘기면
                # measurement_status/endpoint_status 가 둘 다 없어 조용히
                # `MEASURED`로 접힌다(`map_engine_result`의 fallthrough). exactly-once
                # 신호가 `BatchRunner.run()` 표준 경로를 거치는 순간 사라지는 것을
                # 막기 위해 여기서 먼저 가로챈다.
                return TargetResult(
                    target_id=target.target_id,
                    outcome=DUPLICATE_SUPPRESSED_OUTCOME,
                    attempts=retry_outcome.attempts,
                    detail=value,
                )
            outcome = map_engine_result(value)
            return TargetResult(
                target_id=target.target_id,
                outcome=outcome.value,
                attempts=retry_outcome.attempts,
                detail=value,
            )

        return TargetResult(
            target_id=target.target_id,
            outcome=TargetOutcome.SKIPPED_RETRY_EXHAUSTED.value,
            attempts=retry_outcome.attempts,
            error=retry_outcome.last_error,
            same_cause_on_retry=retry_outcome.same_cause_on_retry,
        )

    # ── 기본 실행기 (L0 + L1, opt-in 아님) ────────────────────────────────
    def _run_l0_and_l1(self, target: TargetSpec) -> dict[str, Any]:
        """L0 관측 + (가드를 통과한 target만) L1 activation(Scout)까지 수행한다.

        `_default_fixture_executor`와 `l1_executor`가 **둘 다 이 메서드로 수렴**한다
        — 예전에는 전자가 `executor.run_l0`만, 후자가 `executor.run_l1_if_safe`를
        불러 서로 다른 코드 경로였고 L1은 `target_executor=runner.l1_executor`를
        명시해야만 실행됐다. 그 opt-in 구조를 없앤다(2026-08-27, Claude A 지시 —
        "모든 run에서 L0와 L1이 함께 켜져야 한다").

        가드는 조금도 약해지지 않는다: `executor.run_l1_if_safe`가 내부에서
        `guard.screen_candidates`로 L0 후보를 먼저 스크린하고, 걸리면 `Scout`
        객체 자체를 만들지 않는다 — 이 메서드는 그 계약을 그대로 물려받는다.

        exactly-once(`C-FINDING-214553` — C의 독립 감사): 이전에는 lock 이
        `_real_executor`(REAL_TARGET)에만 배선돼 있어, 네트워크 없이 "프로세스
        2개 동시 기동 → 억제 1건"을 end-to-end 로 증명할 경로가 FIXTURE 쪽에
        없었다. 이제 이 메서드도 `_real_executor`와 **같은** `_acquire_launch_lock`
        을 `EvidenceRun.create` 이전에 태운다 — 코드 경로가 같으므로 lock 자체의
        정확성(원자적 획득·상태·retry 조건)은 `TargetLock` 하나로 양쪽 다 보장된다.
        `ticket_id`/`run_id`를 명시하지 않은 기존 호출부는 `FIXTURE_DEFAULT_*`
        기본값으로 채워진다 — 강제 실패시키지 않는다(FIXTURE 는 REAL_TARGET 처럼
        "blocking acceptance criterion" 대상이 아니다).
        """
        from landing_accessibility.engine.evidence import EvidenceRun

        from .executor import run_l1_if_safe

        lock, key, attempt_id, suppressed = self._acquire_launch_lock(target, real=False)
        if suppressed is not None:
            return suppressed

        assert attempt_id is not None
        run = EvidenceRun.create(
            self.out_dir / "evidence",
            attempt_id,
            execution_mode=ExecutionMode.FIXTURE,
            provenance=ShadowProvenance(
                base_sha=E001_RUNNER_BASE_SHA, shadow_lane=E001_RUNNER_SHADOW_LANE
            ),
        )
        try:
            result = run_l1_if_safe(target, fixture_root=self.fixture_root, run=run)
        except Exception:
            lock.mark_failed_retryable(key)
            run.seal()
            raise
        run.seal()
        result["attempt_id"] = attempt_id
        result["idempotency_key"] = key.canonical()
        if _is_retryable_engine_failure(result):
            lock.mark_failed_retryable(key)
        else:
            lock.mark_done(key)
        return result

    def _default_fixture_executor(self, target: TargetSpec) -> dict[str, Any]:
        """`run()`의 기본 executor. **L0 관측 + L1(Scout) activation을 함께 수행한다**
        — 더 이상 L0-only가 아니다(이전 동작은 opt-in `l1_executor`를 명시해야 했다).
        """
        return self._run_l0_and_l1(target)

    def l1_executor(self, target: TargetSpec) -> dict[str, Any]:
        """`_default_fixture_executor`의 명시적 별칭 — 이제는 기본값과 완전히 같다.

        `target_executor=runner.l1_executor`로 명시적으로 주입하던 기존 호출부
        (`tests/test_e001_account_action_guard.py` 등)를 깨지 않기 위해 남겨둔다.
        새 호출부는 `target_executor`를 아예 넘기지 않아도 같은 L0+L1 경로를 탄다.
        """
        return self._run_l0_and_l1(target)

    # ── batch 봉인 ───────────────────────────────────────────────────────
    def _seal_batch(
        self,
        batch_index: int,
        targets: list[TargetSpec],
        results: list[TargetResult],
        execution_mode: str,
        *,
        scope: object | None = None,
    ) -> BatchManifest:
        # `DUPLICATE_SUPPRESSED_OUTCOME`은 `outcomes.TargetOutcome`(닫힌 집합, W1
        # 소유 파일 아님)의 멤버가 아니다 — `TargetOutcome(...)` 캐스팅 전에
        # 먼저 걸러낸다(안 그러면 `ValueError`로 배치 봉인 자체가 죽는다).
        isolated = sum(
            1
            for r in results
            if r.outcome == DUPLICATE_SUPPRESSED_OUTCOME
            or is_failure_isolated(TargetOutcome(r.outcome))
        )
        provenance = (
            RealTargetProvenance.for_scope(
                scope, base_sha=E001_RUNNER_BASE_SHA, execution_lane=E001_RUNNER_SHADOW_LANE
            )
            if scope is not None
            else ShadowProvenance(
                base_sha=E001_RUNNER_BASE_SHA, shadow_lane=E001_RUNNER_SHADOW_LANE
            )
        )
        manifest = BatchManifest(
            batch_index=batch_index,
            batch_id=f"b{batch_index:04d}",
            execution_mode=execution_mode,
            target_ids=[t.target_id for t in targets],
            results=[r.as_dict() for r in results],
            provenance={
                **provenance.as_dict(),
                "isolated_failure_count": isolated,
                "target_count": len(targets),
                "max_retries_per_target": MAX_RETRIES_PER_TARGET,
            },
            committed_at=_utc_now_iso(),
            previous_batch_hash=self.ledger.last_batch_hash(),
        )
        return self.ledger.append(manifest)

    def _run_dry(self, plan: list[TargetSpec]) -> BatchManifest:
        """SHADOW_DRY_RUN — **executor를 한 번도 호출하지 않는다.** 계획 구조만 검증한다."""
        results = [
            TargetResult(
                target_id=t.target_id,
                outcome=TargetOutcome.PLANNED_NOT_EXECUTED.value,
                attempts=0,
            )
            for t in plan
        ]
        return self._seal_batch(1, plan, results, "SHADOW_DRY_RUN")


__all__ = [
    "DEFAULT_MAX_LOCK_ATTEMPTS",
    "DUPLICATE_SUPPRESSED_OUTCOME",
    "BatchRunner",
    "ExactlyOnceConfigError",
    "IdempotencyKey",
    "LockDecision",
    "LockState",
    "TargetExecutor",
    "TargetLock",
    "TargetResult",
]
