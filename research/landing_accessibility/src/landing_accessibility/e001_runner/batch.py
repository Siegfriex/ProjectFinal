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
from landing_accessibility.engine.provenance import RealTargetProvenance, ShadowProvenance
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
        """
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

    def _real_executor(self, target: TargetSpec) -> dict[str, Any]:
        """실제 수집 executor — L0 + L1 을 함께 수행한다 (L0-only run 을 만들지 않는다)."""
        from landing_accessibility.engine.evidence import EvidenceRun

        from .real_executor import run_l1_if_safe_real

        scope = self._real_scope or ExecutionScope.E000_FAST
        scope_label = getattr(scope, "value", None) or str(scope)
        run_id = (
            f"{scope_label.lower()}-{target.target_id}-"
            f"{_utc_now_iso().replace(':', '').replace('.', '')}"
        )
        run = EvidenceRun.create(
            self.out_dir / "evidence",
            run_id,
            execution_mode=ExecutionMode.REAL_TARGET,
            execution_scope=scope,
            provenance=RealTargetProvenance.for_scope(
                scope, base_sha=E001_RUNNER_BASE_SHA, execution_lane=E001_RUNNER_SHADOW_LANE
            ),
        )
        result = run_l1_if_safe_real(target, run=run, scope=scope)
        run.seal()
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
        """
        from landing_accessibility.engine.evidence import EvidenceRun

        from .executor import run_l1_if_safe

        run_id = f"e001-{target.target_id}-{_utc_now_iso().replace(':', '').replace('.', '')}"
        run = EvidenceRun.create(
            self.out_dir / "evidence",
            run_id,
            execution_mode=ExecutionMode.FIXTURE,
            provenance=ShadowProvenance(
                base_sha=E001_RUNNER_BASE_SHA, shadow_lane=E001_RUNNER_SHADOW_LANE
            ),
        )
        result = run_l1_if_safe(target, fixture_root=self.fixture_root, run=run)
        run.seal()
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
        isolated = sum(1 for r in results if is_failure_isolated(TargetOutcome(r.outcome)))
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


__all__ = ["BatchRunner", "TargetExecutor", "TargetResult"]
