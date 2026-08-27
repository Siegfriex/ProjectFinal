"""REAL-TARGET FIREWALL — `PHASE_GATES.md §4.5`.

P0(`V2_SSOT_FROZEN`)가 닫히기 전에는 **실제 서비스 target에 접속해 접근성 결과를 생성하는
어떤 코드도 실행되어서는 안 된다.** `PHASE_GATES §4.1` 2~5항이 그것을 금지하고,
`§4.5`가 그 금지를 수집기의 `execution_mode`로 기계화하라고 지시한다.

    FIXTURE          허용 — 로컬 synthetic fixture (file:// 만)
    SHADOW_DRY_RUN   허용 — 어떤 항해도 하지 않는 계획/검증 전용
    REAL_TARGET      scope 없이는 hard FAIL

이 모듈이 그 표다. **문서가 아니라 이 파일이 금지를 집행한다.**

## 왜 enum 값을 지우지 않고 남겨 두는가

`REAL_TARGET`을 어휘에서 삭제하면 "그 모드를 요청했다"는 사건 자체를 표현할 수 없게 되고,
호출부는 오타·`KeyError`로 실패한다. 그러면 실패의 이유가 "금지된 모드를 요청했다"가 아니라
"알 수 없는 값"이 되어, 실패주입 harness가 **무엇을 차단했는지 증명하지 못한다.**
값은 남기고 **게이트를 닫는다.**

## `ExecutionMode`는 3값 닫힌 집합으로 유지한다 (A2 규칙 S-3)

P0 승격 후 실제 수집이 필요해졌을 때 `REAL_TARGET_E000` 같은 **네 번째 enum 값을 추가하지
않는다.** `A2 규칙 S-3`이 `{FIXTURE, SHADOW_DRY_RUN, REAL_TARGET}`을 닫힌 집합으로
정의하고 물리 스키마의 `execution_mode` 컬럼이 그 어휘에 바인딩돼 있다 — 값을 늘리면
스키마 위반이며, 독립 검산기가 그 배치를 무효로 잡는다.

대신 **직교하는 축을 하나 더 둔다**: `ExecutionScope`. `execution_mode`는 "무엇을 여는가"
(fixture냐 실제 서비스냐)를, `execution_scope`는 "어느 승인 범위 안에서 여는가"를 말한다.
`REAL_TARGET`은 scope 없이는 **여전히 무조건 hard FAIL**이고, 승인된 scope가 명시적으로
주어졌을 때만, 그리고 그 scope의 릴리스 문서가 런타임에 확인됐을 때만 열린다.

## 게이트를 여는 것은 코드 상수가 아니라 런타임 릴리스 문서다

`P0_GATE_STATUS` 상수는 **감사용 기계적 증거**다 — 이 값을 전이시키는 커밋 SHA가
릴리스 문서에 바인딩되어 "승인 없이 수집이 시작되지 않았다"를 증명한다. 그러나 그 상수만
고쳐서는 아무것도 열리지 않는다: 실제 허용 판정은 `control/P0_RELEASE.json`을
**git ref에서 직접 읽어** `status == RELEASED` · `promoted_main_sha` 채워짐 ·
`e000_allowed == true` 를 모두 확인한 뒤에만 내려진다. 문서가 없거나 조건이 하나라도
어긋나면 차단이다 (fail-closed).

워킹트리 파일이 아니라 `git show <ref>:<path>`로 읽는 이유는, 로컬에서 파일 하나를
만들어 두는 것만으로 게이트가 열리는 일을 막기 위해서다.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from urllib.parse import urlparse

#: `PHASE_GATES.md §1` — 이 게이트가 닫히기 전까지 REAL_TARGET 은 hard FAIL 이다.
P0_GATE_NAME = "V2_SSOT_FROZEN"

#: `EXECUTION_AUTHORITY §1` — P0 게이트 상태 상수.
#:
#: 이 상수는 **감사용 표식**이며 허가 판정의 근거가 아니다. 실제 판정은
#: `evaluate_execution_scope()`가 런타임에 릴리스 문서를 읽어 내린다. 이 값을 전이시키는
#: 커밋 SHA 가 `P0_RELEASE.json.firewall_gate_status_commit_sha` 에 바인딩된다.
#:
#: 2026-08-27 `OPEN` → `CLOSED`. 근거: `control/P0_RELEASE.json` status=RELEASED,
#: promoted_main_sha=bc0b7a087faf2328cbafdfa9b40bd426c5080d7d
#: (`research/landing-accessibility-main` 실제 승격, 이전 tip 5a9015d1).
#: **이 전이만으로는 아무것도 열리지 않는다** — 허가는 `evaluate_execution_scope()` 가
#: 그 문서를 런타임에 읽어 내리고, 이 상수를 되돌려도 그 판정은 바뀌지 않는다.
#: 이 값이 여는 것은 감사 경로 하나뿐이다: 이 커밋의 SHA 가 릴리스 문서의
#: `firewall_gate_status_commit_sha` 에 바인딩되어 "승인 없이 수집이 시작되지 않았다" 의
#: 기계적 증거가 된다.
P0_GATE_STATUS = "CLOSED"

#: `PHASE_GATES.md §4.4` — 이 코드가 속한 lane.
SHADOW_LANE = "LANE_C"


class ExecutionMode(StrEnum):
    """`PHASE_GATES §4.5`의 세 값. 닫힌 집합이다 (A2 규칙 S-3).

    **네 번째 값을 추가하지 않는다.** 실제 수집의 범위 제한은 `ExecutionScope`가 맡는다.
    """

    FIXTURE = "FIXTURE"
    SHADOW_DRY_RUN = "SHADOW_DRY_RUN"
    REAL_TARGET = "REAL_TARGET"


class ExecutionScope(StrEnum):
    """`REAL_TARGET` 을 어느 승인 범위에서 여는가. `ExecutionMode` 와 직교한다.

    - `E000_FAST` — 오늘의 E000 빠른 검증. `E000_FAST_PLAN` 의 동결된 6 target 만.
    - `E001_FULL` — E001 본수집. `E001_MASTER_PLAN` 의 동결된 59 target 만.
      `control/E001_RELEASE.json` 이 `status == RELEASED` · `promoted_main_sha` ·
      `e001_allowed == true` 로 **런타임에 확인될 때만** 열린다 (A 의 별도 릴리스
      티켓). 문서가 없거나 조건이 하나라도 어긋나면 차단이다 — P0_RELEASE 하나로는
      절대 열리지 않는다.
    """

    E000_FAST = "E000_FAST"
    E001_FULL = "E001_FULL"


#: P0 종료 전 허용되는 모드.
MODES_ALLOWED_BEFORE_P0: frozenset[ExecutionMode] = frozenset(
    {ExecutionMode.FIXTURE, ExecutionMode.SHADOW_DRY_RUN}
)

#: FIXTURE 모드에서 허용되는 유일한 URL scheme.
FIXTURE_URL_SCHEMES: frozenset[str] = frozenset({"file"})

#: `REAL_TARGET` + 승인된 scope 에서만 허용되는 scheme. FIXTURE 는 절대 이 집합을 보지 않는다.
REAL_TARGET_URL_SCHEMES: frozenset[str] = frozenset({"https", "http"})

# ── 릴리스 문서 위치 (워킹트리가 아니라 git ref 에서 읽는다) ──────────────────────
P0_RELEASE_REF = "origin/control/landing-orchestrator"
P0_RELEASE_PATH = "research/landing_accessibility/control/P0_RELEASE.json"
E001_RELEASE_PATH = "research/landing_accessibility/control/E001_RELEASE.json"

#: 릴리스 문서에서 "승인됨" 으로 인정하는 유일한 status 값.
RELEASE_STATUS_RELEASED = "RELEASED"

_RESEARCH_ROOT = Path(__file__).resolve().parents[3]
_REPO_ROOT = _RESEARCH_ROOT.parents[1]

#: E000_FAST allowlist 의 정본 후보 경로. 앞에서부터 찾아 처음 존재하는 것을 쓴다.
E000_FAST_PLAN_CANDIDATES: tuple[Path, ...] = (
    _RESEARCH_ROOT / "shadow" / "e000_plan" / "E000_FAST_PLAN.json",
    _REPO_ROOT
    / ".agent_worktrees"
    / "claude_b_e000_fast"
    / "research"
    / "landing_accessibility"
    / "shadow"
    / "e000_plan"
    / "E000_FAST_PLAN.json",
)

#: 워크트리 안에서 실행되면 `.agent_worktrees/<name>` 의 부모가 메인 저장소 루트다.
#: P-B 산출물(lane_b state CSV)은 그 아래의 다른 워크트리에 있고 **읽기 전용**으로만 쓴다.
_MAIN_REPO_ROOT: Path = (
    _REPO_ROOT.parents[1] if _REPO_ROOT.parent.name == ".agent_worktrees" else _REPO_ROOT
)


def _plan_candidates(*relative: str) -> tuple[Path, ...]:
    """이 워크트리 안 → 메인 저장소 → 형제 워크트리 순으로 후보 경로를 만든다."""
    rel = Path(*relative)
    return (
        _RESEARCH_ROOT / rel,
        _MAIN_REPO_ROOT / "research" / "landing_accessibility" / rel,
    )


#: `E001_FULL` allowlist 의 정본(동결 계획). 앞에서부터 처음 존재하는 것을 쓴다.
E001_MASTER_PLAN_CANDIDATES: tuple[Path, ...] = (
    *_plan_candidates("shadow", "e001_plan", "E001_MASTER_PLAN.json"),
    _MAIN_REPO_ROOT
    / ".agent_worktrees"
    / "claude_b_e001_master_plan"
    / "research"
    / "landing_accessibility"
    / "shadow"
    / "e001_plan"
    / "E001_MASTER_PLAN.json",
)

#: `E001_MASTER_PLAN.json` 이 선언한 동결 계획 해시. 재계산과 다르면 **차단**이다.
E001_FROZEN_PLAN_HASH = "b48be3cb5e2cb992c0b9ee44306a4f3bd3cee8fbd601de5f14ebb82f75a9e2bc"
E001_FROZEN_PLAN_HASH_FIELD = "frozen_plan_hash_candidate"

#: 계획에는 key 만 있다 — URL/target_id 는 P-B(lane_b) 산출물에서 조인한다.
#: **두 파일 모두 읽기 전용으로만 연다.**
_LANE_B_STATE = ("shadow", "lane_b", "state")
E001_ELIGIBILITY_CSV_CANDIDATES: tuple[Path, ...] = (
    *_plan_candidates(*_LANE_B_STATE, "web_eligibility_shadow.csv"),
    _MAIN_REPO_ROOT
    / ".agent_worktrees"
    / "landing_pb_prework"
    / "research"
    / "landing_accessibility"
    / "shadow"
    / "lane_b"
    / "state"
    / "web_eligibility_shadow.csv",
)
E001_TASK_CSV_CANDIDATES: tuple[Path, ...] = (
    *_plan_candidates(*_LANE_B_STATE, "representative_task_candidate_shadow.csv"),
    _MAIN_REPO_ROOT
    / ".agent_worktrees"
    / "landing_pb_prework"
    / "research"
    / "landing_accessibility"
    / "shadow"
    / "lane_b"
    / "state"
    / "representative_task_candidate_shadow.csv",
)

#: `worker_partition.assignments` 의 닫힌 키 집합. 그 밖의 워커 id 는 실행할 수 없다.
E001_WORKER_IDS: tuple[str, ...] = ("worker_01", "worker_02", "worker_03", "worker_04")

#: eligibility CSV 에서 실제 수집을 허용하는 유일한 상태.
E001_ELIGIBLE_STATUS = "ELIGIBLE_WEB"


class FirewallError(RuntimeError):
    """REAL-TARGET FIREWALL 위반. 절대 삼키지 않는다."""


class RealTargetBlockedError(FirewallError):
    """`REAL_TARGET` 모드 요청 — `PHASE_GATES §4.5` hard FAIL."""


class UnknownExecutionModeError(FirewallError):
    """닫힌 집합 밖의 모드 값 (A2 규칙 S-3 — `UNKNOWN`으로 흡수하지 않는다)."""


class UnknownExecutionScopeError(FirewallError):
    """닫힌 집합 밖의 scope 값."""


class ExecutionScopeBlockedError(FirewallError):
    """scope 는 알려진 값이나 그 scope 의 릴리스 조건이 충족되지 않았다."""


class TargetNotAllowlistedError(FirewallError):
    """승인된 scope 안이지만 그 scope 의 allowlist 에 없는 target 이다."""


class NavigationBlockedError(FirewallError):
    """허용된 모드이나 그 모드가 허가하지 않는 항해를 시도했다."""


def p0_closed() -> bool:
    """P0 게이트 상수가 CLOSED 로 전이됐는가.

    **이 함수만으로는 아무것도 열리지 않는다.** 허가는 `evaluate_execution_scope()` 가
    런타임 릴리스 문서를 읽어 내린다.
    """
    return P0_GATE_STATUS == "CLOSED"


def real_target_permitted() -> bool:
    """*무제한* `REAL_TARGET` 이 허용되는가 — **영구히 `False`** 다.

    scope 없는 `REAL_TARGET` 은 "아무 URL 이나 열 수 있는 모드" 이고, 그런 경로는
    이 연구에서 열리지 않는다. 실제 수집은 반드시 승인된 `ExecutionScope` 를 통해
    범위가 좁혀진 상태로만 일어난다 (`assert_real_target_scope_allowed`).
    """
    return False


# ── 릴리스 문서 판독 ─────────────────────────────────────────────────────────
@dataclass(frozen=True)
class ReleaseVerdict:
    """scope 하나에 대한 허가 판정. 보고서에 그대로 실을 수 있게 원시값만 담는다."""

    scope: str
    allowed: bool
    reason: str
    release_status: str | None = None
    promoted_main_sha: str | None = None
    document_sha256: str | None = None
    document_ref: str | None = None

    def as_dict(self) -> dict[str, object]:
        return {
            "scope": self.scope,
            "allowed": self.allowed,
            "reason": self.reason,
            "release_status": self.release_status,
            "promoted_main_sha": self.promoted_main_sha,
            "document_sha256": self.document_sha256,
            "document_ref": self.document_ref,
        }


@dataclass(frozen=True)
class ReleaseDocument:
    ref: str
    path: str
    data: dict[str, object] | None
    sha256: str | None
    error: str | None = None


_RELEASE_CACHE: dict[tuple[str, str], ReleaseDocument] = {}


def reset_release_cache() -> None:
    """릴리스 문서 캐시를 비운다. 테스트와 장기 실행 프로세스용."""
    _RELEASE_CACHE.clear()


def read_release_document(
    *,
    ref: str = P0_RELEASE_REF,
    path: str = P0_RELEASE_PATH,
    repo_dir: Path | None = None,
    use_cache: bool = True,
) -> ReleaseDocument:
    """`git show <ref>:<path>` 로 릴리스 문서를 읽는다. 실패는 예외가 아니라 값이다.

    워킹트리 파일을 읽지 않는다 — 로컬에 파일 하나를 만들어 두는 것으로 게이트가
    열리는 경로를 없앤다. 읽기에 실패하면 `data is None` 이고, 그 상태는 호출부에서
    **차단**으로 해석된다 (fail-closed).
    """
    key = (ref, path)
    if use_cache and key in _RELEASE_CACHE:
        return _RELEASE_CACHE[key]

    cwd = Path(repo_dir) if repo_dir is not None else _REPO_ROOT
    try:
        proc = subprocess.run(
            ["git", "-C", str(cwd), "show", f"{ref}:{path}"],
            capture_output=True,
            timeout=30,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        doc = ReleaseDocument(ref, path, None, None, f"{type(exc).__name__}: {exc}")
    else:
        if proc.returncode != 0:
            doc = ReleaseDocument(
                ref, path, None, None, f"git show 실패(rc={proc.returncode}): {proc.stderr[:400]!r}"
            )
        else:
            raw = proc.stdout
            digest = hashlib.sha256(raw).hexdigest()
            try:
                data = json.loads(raw.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                doc = ReleaseDocument(ref, path, None, digest, f"JSON 파싱 실패: {exc}")
            else:
                if not isinstance(data, dict):
                    doc = ReleaseDocument(ref, path, None, digest, "릴리스 문서가 객체가 아니다")
                else:
                    doc = ReleaseDocument(ref, path, data, digest, None)

    if use_cache:
        _RELEASE_CACHE[key] = doc
    return doc


def _looks_like_sha(value: object) -> bool:
    return (
        isinstance(value, str) and len(value) >= 7 and all(c in "0123456789abcdef" for c in value)
    )


def _evaluate_release_document(
    doc: ReleaseDocument, *, scope: ExecutionScope, allow_flag: str
) -> ReleaseVerdict:
    def verdict(
        allowed: bool,
        reason: str,
        *,
        release_status: str | None = None,
        promoted_main_sha: str | None = None,
    ) -> ReleaseVerdict:
        return ReleaseVerdict(
            scope=scope.value,
            allowed=allowed,
            reason=reason,
            release_status=release_status,
            promoted_main_sha=promoted_main_sha,
            document_sha256=doc.sha256,
            document_ref=f"{doc.ref}:{doc.path}",
        )

    if doc.data is None:
        return verdict(
            False, f"릴리스 문서를 읽지 못했다 — {doc.error or '알 수 없는 이유'} (fail-closed)"
        )
    data = doc.data
    status = data.get("status")
    status_str = status if isinstance(status, str) else None
    if status_str != RELEASE_STATUS_RELEASED:
        return verdict(
            False,
            f"status 가 {RELEASE_STATUS_RELEASED} 가 아니다: {status!r}",
            release_status=status_str,
        )
    promoted = data.get("promoted_main_sha")
    if not _looks_like_sha(promoted):
        # `E001_RELEASE.json` 은 승격 SHA 를 `authority_refs` 블록 안에 둔다. 최상위 키가
        # 없을 때만 그 한 곳을 더 본다 — **다른 어떤 위치도 보지 않는다.** 값이 거기에도
        # 없으면 그대로 차단이다 (fail-closed). E000 문서는 최상위 키를 가지므로 이
        # 경로를 타지 않는다 — 기존 판정은 한 글자도 바뀌지 않는다.
        refs = data.get("authority_refs")
        if isinstance(refs, dict):
            promoted = refs.get("promoted_main_sha")
    if not _looks_like_sha(promoted):
        return verdict(
            False,
            f"promoted_main_sha 가 채워지지 않았다: {promoted!r}",
            release_status=status_str,
        )
    if data.get(allow_flag) is not True:
        return verdict(
            False,
            f"{allow_flag} 가 true 가 아니다: {data.get(allow_flag)!r}",
            release_status=status_str,
            promoted_main_sha=str(promoted),
        )
    if data.get("real_target_allowed") is False:
        return verdict(
            False,
            "real_target_allowed 가 명시적으로 false 다",
            release_status=status_str,
            promoted_main_sha=str(promoted),
        )
    return verdict(
        True,
        f"{allow_flag}=true · status={RELEASE_STATUS_RELEASED} · promoted_main_sha 확인",
        release_status=status_str,
        promoted_main_sha=str(promoted),
    )


def resolve_execution_scope(value: object) -> ExecutionScope:
    """임의 입력을 `ExecutionScope` 로 좁힌다. 모르는 값은 **실패**한다."""
    if isinstance(value, ExecutionScope):
        return value
    if isinstance(value, str):
        try:
            return ExecutionScope(value)
        except ValueError as exc:
            raise UnknownExecutionScopeError(
                f"execution_scope 는 닫힌 집합이다: {sorted(s.value for s in ExecutionScope)}. "
                f"받은 값: {value!r}"
            ) from exc
    raise UnknownExecutionScopeError(
        f"execution_scope 를 지정해야 한다. 받은 값: {value!r} (REAL_TARGET 은 scope 필수)"
    )


def evaluate_execution_scope(
    scope: object, *, repo_dir: Path | None = None, use_cache: bool = True
) -> ReleaseVerdict:
    """scope 하나가 지금 실제 수집을 허가받았는지 **런타임에** 판정한다."""
    resolved = resolve_execution_scope(scope)
    if resolved is ExecutionScope.E000_FAST:
        doc = read_release_document(
            ref=P0_RELEASE_REF, path=P0_RELEASE_PATH, repo_dir=repo_dir, use_cache=use_cache
        )
        return _evaluate_release_document(doc, scope=resolved, allow_flag="e000_allowed")
    doc = read_release_document(
        ref=P0_RELEASE_REF, path=E001_RELEASE_PATH, repo_dir=repo_dir, use_cache=use_cache
    )
    return _evaluate_release_document(doc, scope=resolved, allow_flag="e001_allowed")


# ── E000_FAST allowlist ──────────────────────────────────────────────────────
@dataclass(frozen=True)
class TargetAllowlist:
    """한 scope 가 열 수 있는 target 의 동결된 목록."""

    scope: str
    source_path: str
    plan_sha256: str
    target_ids: frozenset[str] = field(default_factory=frozenset)
    canonical_service_keys: frozenset[str] = field(default_factory=frozenset)
    official_urls: frozenset[str] = field(default_factory=frozenset)
    hosts: frozenset[str] = field(default_factory=frozenset)

    def as_dict(self) -> dict[str, object]:
        return {
            "scope": self.scope,
            "source_path": self.source_path,
            "plan_sha256": self.plan_sha256,
            "target_count": len(self.target_ids),
            "target_ids": sorted(self.target_ids),
            "hosts": sorted(self.hosts),
        }


class AllowlistUnavailableError(FirewallError):
    """allowlist 정본을 찾지 못했다 — scope 실행은 차단이다 (fail-closed)."""


_ALLOWLIST_CACHE: dict[str, TargetAllowlist] = {}


def reset_allowlist_cache() -> None:
    _ALLOWLIST_CACHE.clear()


def load_e000_fast_allowlist(path: str | Path | None = None) -> TargetAllowlist:
    """`E000_FAST_PLAN.json` 에서 allowlist 를 만든다. 파일이 없으면 **차단**한다."""
    candidates = (Path(path),) if path is not None else E000_FAST_PLAN_CANDIDATES
    chosen: Path | None = next((c for c in candidates if c.is_file()), None)
    if chosen is None:
        raise AllowlistUnavailableError(
            "E000_FAST allowlist 정본(E000_FAST_PLAN.json)을 찾지 못했다: "
            f"{[str(c) for c in candidates]} — allowlist 없이 실제 수집을 시작하지 않는다."
        )
    key = str(chosen)
    if path is None and key in _ALLOWLIST_CACHE:
        return _ALLOWLIST_CACHE[key]

    raw = chosen.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    data = json.loads(raw.decode("utf-8"))
    targets = data.get("targets")
    if not isinstance(targets, list) or not targets:
        raise AllowlistUnavailableError(f"{chosen} 에 targets 배열이 없다")

    ids: set[str] = set()
    keys: set[str] = set()
    urls: set[str] = set()
    hosts: set[str] = set()
    for row in targets:
        if not isinstance(row, dict):
            continue
        if row.get("target_id"):
            ids.add(str(row["target_id"]))
        if row.get("canonical_service_key"):
            keys.add(str(row["canonical_service_key"]))
        url = row.get("official_url")
        if url:
            urls.add(str(url))
            host = urlparse(str(url)).netloc.lower()
            if host:
                hosts.add(host)

    allowlist = TargetAllowlist(
        scope=ExecutionScope.E000_FAST.value,
        source_path=str(chosen),
        plan_sha256=digest,
        target_ids=frozenset(ids),
        canonical_service_keys=frozenset(keys),
        official_urls=frozenset(urls),
        hosts=frozenset(hosts),
    )
    if path is None:
        _ALLOWLIST_CACHE[key] = allowlist
    return allowlist


# ── E001_FULL allowlist ──────────────────────────────────────────────────────
@dataclass(frozen=True)
class E001TargetRow:
    """`E001_MASTER_PLAN` 의 key 하나를 P-B 산출물과 조인한 결과."""

    canonical_service_key: str
    target_id: str
    official_url: str
    interaction_archetype: str
    worker_id: str
    order_index: int
    service_name_canonical: str | None = None
    endpoint_definition: str | None = None
    task_id: str | None = None
    #: `T-A-W1-001` §2 (D-R0-07~09) — 이전에는 이 조인이 `representative_task_
    #: candidate_shadow.csv`의 5필드 중 `endpoint_definition`·`task_id`만 옮기고
    #: 나머지 셋을 읽고도 버렸다(그 결과가 `e001_runner.executor.
    #: default_task_definition`의 하드코딩 `CODEBOOK_PENDING`이었다). CSV 자체에는
    #: 71행 전건에 다섯 필드가 다 있다 — 여기서 놓치는 게 이 lineage 단절의 실제
    #: 지점이었다.
    region_definition: str | None = None
    region_signal_type: str | None = None
    endpoint_signal_type: str | None = None


def _first_existing(candidates: tuple[Path, ...], what: str) -> Path:
    chosen = next((c for c in candidates if c.is_file()), None)
    if chosen is None:
        raise AllowlistUnavailableError(
            f"{what} 정본을 찾지 못했다: {[str(c) for c in candidates]} — "
            "정본 없이 실제 수집을 시작하지 않는다."
        )
    return chosen


def _read_key_indexed_csv(path: Path, *, what: str) -> dict[str, dict[str, str]]:
    """`canonical_service_key` 로 색인된 CSV 를 읽는다. **읽기 전용이다.**"""
    import csv

    with open(path, encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    indexed: dict[str, dict[str, str]] = {}
    for row in rows:
        key = (row.get("canonical_service_key") or "").strip()
        if not key:
            continue
        if key in indexed:
            raise AllowlistUnavailableError(
                f"{what}({path}) 에 canonical_service_key 중복: {key!r} — "
                "어느 행이 정본인지 알 수 없으므로 차단한다."
            )
        indexed[key] = row
    if not indexed:
        raise AllowlistUnavailableError(f"{what}({path}) 에서 읽은 행이 없다")
    return indexed


def recompute_plan_hash(data: dict[str, object], hash_field: str) -> str:
    """동결 계획의 hash candidate 를 재계산한다 (`scripts/verify_plan_hash.py` 와 같은 규칙).

    payload = 계획 dict 에서 hash 필드 **하나만** 제거한 것 (키 순서 그대로),
    blob = `json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=False)`.
    """
    payload = {k: v for k, v in data.items() if k != hash_field}
    blob = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=False).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()


def load_e001_master_plan(path: str | Path | None = None) -> tuple[Path, dict[str, object]]:
    """`E001_MASTER_PLAN.json` 을 읽고 **동결 해시를 재계산해 대조한다**.

    선언값과 재계산값이 다르거나, 이 코드가 아는 동결 해시
    (`E001_FROZEN_PLAN_HASH`) 와 다르면 차단한다 — 계획이 결과를 보고 바뀌지
    않았다는 것을 실행 직전에 기계적으로 확인하는 자리다.
    """
    chosen = (
        Path(path)
        if path is not None
        else _first_existing(
            E001_MASTER_PLAN_CANDIDATES, "E001_FULL allowlist 정본(E001_MASTER_PLAN.json)"
        )
    )
    if not chosen.is_file():
        raise AllowlistUnavailableError(f"E001_MASTER_PLAN.json 이 없다: {chosen}")
    data = json.loads(chosen.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise AllowlistUnavailableError(f"{chosen} 이 객체가 아니다")
    declared = data.get(E001_FROZEN_PLAN_HASH_FIELD)
    recomputed = recompute_plan_hash(data, E001_FROZEN_PLAN_HASH_FIELD)
    if declared != recomputed:
        raise AllowlistUnavailableError(
            f"{chosen} 의 {E001_FROZEN_PLAN_HASH_FIELD} 재계산 불일치 — "
            f"declared={declared!r} recomputed={recomputed!r}. 동결 계획이 변조됐거나 "
            "다른 규칙으로 만들어졌다 — 실행하지 않는다."
        )
    if declared != E001_FROZEN_PLAN_HASH:
        raise AllowlistUnavailableError(
            f"{chosen} 의 동결 해시가 이 코드가 아는 값과 다르다 — "
            f"기대 {E001_FROZEN_PLAN_HASH}, 파일 {declared!r}."
        )
    return chosen, data


def load_e001_full_targets(path: str | Path | None = None) -> tuple[E001TargetRow, ...]:
    """동결 순서 그대로 조인된 `E001_FULL` target 목록을 만든다. **재정렬하지 않는다.**

    조인에 실패한 key 가 하나라도 있으면 **조용히 빼지 않고 차단한다** — 동결된
    집합에서 무언가가 빠지는 것은 결과 조건부 재선택과 구분되지 않기 때문이다.
    """
    chosen, data = load_e001_master_plan(path)

    order = data.get("frozen_collection_order")
    if not isinstance(order, list) or not order:
        raise AllowlistUnavailableError(f"{chosen} 에 frozen_collection_order 가 없다")
    keys = [str(k) for k in order]
    if len(keys) != len(set(keys)):
        raise AllowlistUnavailableError("frozen_collection_order 에 중복 key 가 있다")

    partition = data.get("worker_partition")
    assignments = partition.get("assignments") if isinstance(partition, dict) else None
    if not isinstance(assignments, dict):
        raise AllowlistUnavailableError(f"{chosen} 에 worker_partition.assignments 가 없다")
    if tuple(sorted(assignments)) != tuple(sorted(E001_WORKER_IDS)):
        raise AllowlistUnavailableError(
            f"worker_partition.assignments 의 워커 집합이 다르다: {sorted(assignments)!r}"
        )
    worker_of: dict[str, str] = {}
    for worker_id in E001_WORKER_IDS:
        bucket = assignments[worker_id]
        if not isinstance(bucket, list) or not bucket:
            raise AllowlistUnavailableError(f"{worker_id} 의 배정이 비어 있다")
        for raw_key in bucket:
            key = str(raw_key)
            if key in worker_of:
                raise AllowlistUnavailableError(
                    f"워커 배정이 겹친다: {key!r} 가 {worker_of[key]} 와 {worker_id} 양쪽에 있다"
                )
            worker_of[key] = worker_id
    if set(worker_of) != set(keys):
        missing = sorted(set(keys) - set(worker_of))
        extra = sorted(set(worker_of) - set(keys))
        raise AllowlistUnavailableError(
            f"워커 배정이 동결 순서와 일치하지 않는다 — 누락 {missing}, 초과 {extra}"
        )

    eligibility_path = _first_existing(E001_ELIGIBILITY_CSV_CANDIDATES, "web_eligibility_shadow")
    task_path = _first_existing(E001_TASK_CSV_CANDIDATES, "representative_task_candidate_shadow")
    eligibility = _read_key_indexed_csv(eligibility_path, what="web_eligibility_shadow")
    tasks = _read_key_indexed_csv(task_path, what="representative_task_candidate_shadow")

    rows: list[E001TargetRow] = []
    for index, key in enumerate(keys):
        elig = eligibility.get(key)
        task = tasks.get(key)
        if elig is None or task is None:
            raise AllowlistUnavailableError(
                f"canonical_service_key={key!r} 를 조인하지 못했다 "
                f"(eligibility={elig is not None}, task={task is not None}) — "
                "동결된 집합의 일부를 조용히 빼지 않는다."
            )
        status = (elig.get("web_eligibility_status") or "").strip()
        if status != E001_ELIGIBLE_STATUS:
            raise AllowlistUnavailableError(
                f"{key!r} 의 web_eligibility_status 가 {E001_ELIGIBLE_STATUS} 가 아니다: {status!r}"
            )
        url = (elig.get("web_target_url") or "").strip()
        target_id = (task.get("web_target_id") or "").strip() or (
            elig.get("web_target_group_id") or ""
        ).strip()
        archetype = (task.get("interaction_archetype") or "").strip()
        if not url or not target_id or not archetype:
            raise AllowlistUnavailableError(
                f"{key!r} 의 조인 결과에 필수 값이 비었다 "
                f"(url={url!r}, target_id={target_id!r}, archetype={archetype!r})"
            )
        scheme = urlparse(url).scheme.lower()
        if scheme not in REAL_TARGET_URL_SCHEMES:
            raise AllowlistUnavailableError(
                f"{key!r} 의 web_target_url scheme 이 허용 밖이다: {url!r}"
            )
        rows.append(
            E001TargetRow(
                canonical_service_key=key,
                target_id=target_id,
                official_url=url,
                interaction_archetype=archetype,
                worker_id=worker_of[key],
                order_index=index,
                service_name_canonical=(elig.get("service_name_canonical") or "").strip() or None,
                endpoint_definition=(task.get("endpoint_definition") or "").strip() or None,
                task_id=(task.get("task_id") or "").strip() or None,
                region_definition=(task.get("region_definition") or "").strip() or None,
                region_signal_type=(task.get("region_signal_type") or "").strip() or None,
                endpoint_signal_type=(task.get("endpoint_signal_type") or "").strip() or None,
            )
        )

    ids = [r.target_id for r in rows]
    if len(ids) != len(set(ids)):
        dupes = sorted({i for i in ids if ids.count(i) > 1})
        raise AllowlistUnavailableError(f"조인 결과 target_id 중복: {dupes}")
    return tuple(rows)


def load_e001_full_allowlist(path: str | Path | None = None) -> TargetAllowlist:
    """`E001_MASTER_PLAN.json` + P-B 조인으로 `E001_FULL` allowlist 를 만든다."""
    chosen = (
        Path(path)
        if path is not None
        else _first_existing(
            E001_MASTER_PLAN_CANDIDATES, "E001_FULL allowlist 정본(E001_MASTER_PLAN.json)"
        )
    )
    key = f"E001_FULL::{chosen}"
    if path is None and key in _ALLOWLIST_CACHE:
        return _ALLOWLIST_CACHE[key]

    rows = load_e001_full_targets(chosen)
    hosts = {urlparse(r.official_url).netloc.lower() for r in rows}
    hosts.discard("")
    allowlist = TargetAllowlist(
        scope=ExecutionScope.E001_FULL.value,
        source_path=str(chosen),
        plan_sha256=E001_FROZEN_PLAN_HASH,
        target_ids=frozenset(r.target_id for r in rows),
        canonical_service_keys=frozenset(r.canonical_service_key for r in rows),
        official_urls=frozenset(r.official_url for r in rows),
        hosts=frozenset(hosts),
    )
    if path is None:
        _ALLOWLIST_CACHE[key] = allowlist
    return allowlist


def load_scope_allowlist(scope: object, *, path: str | Path | None = None) -> TargetAllowlist:
    resolved = resolve_execution_scope(scope)
    if resolved is ExecutionScope.E000_FAST:
        return load_e000_fast_allowlist(path)
    if resolved is ExecutionScope.E001_FULL:
        return load_e001_full_allowlist(path)
    raise AllowlistUnavailableError(
        f"{resolved.value} 의 allowlist 정본이 아직 없다 — 이 scope 는 실행할 수 없다."
    )


def assert_target_allowlisted(
    scope: object,
    *,
    target_id: str | None = None,
    url: str | None = None,
    canonical_service_key: str | None = None,
    allowlist: TargetAllowlist | None = None,
) -> TargetAllowlist:
    """이 target 이 그 scope 의 동결된 목록 안에 있는지 확인한다.

    `target_id` 와 `url` 중 **주어진 것은 전부** 검사한다 — 하나만 맞고 다른 하나가
    목록 밖이면 차단이다. 둘 다 주어지지 않으면 검사할 것이 없으므로 차단한다.
    """
    resolved_list = allowlist or load_scope_allowlist(scope)
    if target_id is None and url is None:
        raise TargetNotAllowlistedError(
            f"{resolved_list.scope} allowlist 검사에 target_id 도 url 도 주어지지 않았다 — "
            "무엇을 여는지 모르는 채로 실제 수집을 시작하지 않는다."
        )
    if target_id is not None and target_id not in resolved_list.target_ids:
        raise TargetNotAllowlistedError(
            f"target_id={target_id!r} 는 {resolved_list.scope} allowlist 에 없다 "
            f"(허용 {len(resolved_list.target_ids)}건, 정본 {resolved_list.source_path})."
        )
    if canonical_service_key is not None and (
        canonical_service_key not in resolved_list.canonical_service_keys
    ):
        raise TargetNotAllowlistedError(
            f"canonical_service_key={canonical_service_key!r} 는 "
            f"{resolved_list.scope} allowlist 에 없다."
        )
    if url is not None:
        host = urlparse(url).netloc.lower()
        if url not in resolved_list.official_urls and host not in resolved_list.hosts:
            raise TargetNotAllowlistedError(
                f"url={url!r} (host={host!r}) 는 {resolved_list.scope} allowlist 밖이다 — "
                "동결된 target 목록 밖으로 나가는 항해는 차단된다."
            )
    return resolved_list


def assert_real_target_scope_allowed(
    scope: object,
    *,
    target_id: str | None = None,
    url: str | None = None,
    canonical_service_key: str | None = None,
    allowlist: TargetAllowlist | None = None,
    repo_dir: Path | None = None,
) -> ReleaseVerdict:
    """`REAL_TARGET` 을 이 scope·이 target 으로 열어도 되는지 한 번에 판정한다.

    두 조건을 **모두** 통과해야 한다:

    1. scope 의 릴리스 문서가 런타임에 확인된다 (`evaluate_execution_scope`).
    2. target 이 그 scope 의 동결된 allowlist 안에 있다 (`assert_target_allowlisted`).

    target 식별자가 주어지지 않으면 (1)만 확인한다 — 배치 진입점처럼 "이 scope 자체가
    열려 있는가"만 물을 때 쓰는 경로다. 실제 항해 직전에는 반드시 (2)까지 걸린다.
    """
    verdict = evaluate_execution_scope(scope, repo_dir=repo_dir)
    if not verdict.allowed:
        raise ExecutionScopeBlockedError(
            f"REAL_TARGET scope={verdict.scope} 차단 — {verdict.reason} "
            f"(문서 {verdict.document_ref}). P0_GATE_STATUS 상수만으로는 열리지 않는다."
        )
    if target_id is not None or url is not None:
        assert_target_allowlisted(
            scope,
            target_id=target_id,
            url=url,
            canonical_service_key=canonical_service_key,
            allowlist=allowlist,
        )
    return verdict


def resolve_execution_mode(value: object) -> ExecutionMode:
    """임의 입력을 `ExecutionMode`로 좁힌다. 모르는 값은 **실패**한다.

    `None`을 기본값으로 흡수하지 않는다 — 모드를 지정하지 않은 호출은 사고다.
    """
    if isinstance(value, ExecutionMode):
        return value
    if isinstance(value, str):
        try:
            return ExecutionMode(value)
        except ValueError as exc:
            raise UnknownExecutionModeError(
                f"execution_mode 는 닫힌 집합이다: {sorted(m.value for m in ExecutionMode)}. "
                f"받은 값: {value!r} (A2 규칙 S-3 — UNKNOWN 으로 흡수하지 않는다)"
            ) from exc
    raise UnknownExecutionModeError(
        f"execution_mode 를 지정해야 한다. 받은 값: {value!r} (PHASE_GATES §4.5)"
    )


def assert_mode_allowed(mode: object, *, scope: object | None = None) -> ExecutionMode:
    """이 시점에 그 모드로 수집기를 켤 수 있는지 확인한다.

    `REAL_TARGET`은 `scope` 없이는 **무조건** 차단된다 (`PHASE_GATES §4.5`).
    `scope`가 주어지면 그 scope 의 릴리스 문서를 런타임에 읽어 판정한다 — 코드 상수를
    고치는 것만으로는 열리지 않는다.
    """
    resolved = resolve_execution_mode(mode)
    if resolved is ExecutionMode.REAL_TARGET:
        if scope is None:
            raise RealTargetBlockedError(
                "scope 없는 REAL_TARGET 은 hard FAIL 이다 — 무제한 실제 수집 경로는 "
                "이 연구에서 열리지 않는다 (PHASE_GATES §4.5). 실제 수집은 승인된 "
                f"ExecutionScope({sorted(s.value for s in ExecutionScope)}) 를 통해서만 한다."
            )
        assert_real_target_scope_allowed(scope)
        return resolved
    if scope is not None:
        raise FirewallError(
            f"execution_scope 는 REAL_TARGET 에서만 의미가 있다: mode={resolved.value} "
            f"scope={scope!r} — 모드와 범위를 섞어 쓰지 않는다."
        )
    if resolved not in MODES_ALLOWED_BEFORE_P0:
        raise FirewallError(f"{resolved.value} 는 이 경로로 허용되지 않는다 (PHASE_GATES §4.5)")
    return resolved


def assert_navigation_allowed(
    mode: object,
    url: str,
    *,
    fixture_root: Path | None = None,
    scope: object | None = None,
    target_id: str | None = None,
    canonical_service_key: str | None = None,
    allowlist: TargetAllowlist | None = None,
) -> str:
    """항해 직전 호출한다. 통과하면 정규화된 URL을 돌려준다.

    - `REAL_TARGET` + scope 없음 — 차단 (`assert_mode_allowed`).
    - `REAL_TARGET` + 승인된 scope — 네트워크 scheme 만, 그리고 그 scope 의 allowlist
      안쪽 target 만 허용한다. `file://` 은 이 경로에서 차단이다 — fixture 실행기와
      실제 수집 경로가 서로의 URL 을 열 수 없어야 한다.
    - `SHADOW_DRY_RUN` — **어떤 항해도 하지 않는다.** 계획·스키마 검증 전용 모드이므로
      URL이 file:// 이어도 차단한다. 이 구분이 없으면 dry-run 이 조용히 수집기가 된다.
    - `FIXTURE` — `file://` 만, 그리고 `fixture_root` 안쪽만 허용한다.
      `http`/`https`/`ws`/`data` 는 전부 차단이다. **이 제약은 어떤 scope 로도 완화되지
      않는다** — FIXTURE 는 scope 를 받을 수조차 없다 (`assert_mode_allowed`).
    """
    resolved = assert_mode_allowed(mode, scope=scope)

    if resolved is ExecutionMode.SHADOW_DRY_RUN:
        raise NavigationBlockedError(
            "SHADOW_DRY_RUN 은 항해하지 않는다 (PHASE_GATES §4.5). "
            f"요청된 URL: {url!r}. fixture 를 실제로 열려면 FIXTURE 모드를 쓴다."
        )

    parsed = urlparse(url)
    scheme = parsed.scheme.lower()

    if resolved is ExecutionMode.REAL_TARGET:
        if scheme not in REAL_TARGET_URL_SCHEMES:
            raise NavigationBlockedError(
                f"실제 수집은 {sorted(REAL_TARGET_URL_SCHEMES)} scheme 만 연다. "
                f"받은 scheme: {scheme!r} (url={url!r}) — 로컬 파일은 FIXTURE 모드의 것이다."
            )
        if not parsed.netloc:
            raise NavigationBlockedError(f"host 가 없는 URL 이다: {url!r}")
        assert_real_target_scope_allowed(
            scope,
            target_id=target_id,
            url=url,
            canonical_service_key=canonical_service_key,
            allowlist=allowlist,
        )
        return url

    if scheme not in FIXTURE_URL_SCHEMES:
        raise NavigationBlockedError(
            f"FIXTURE 모드는 {sorted(FIXTURE_URL_SCHEMES)} scheme 만 허용한다. "
            f"받은 scheme: {scheme!r} (url={url!r}). "
            "네트워크 scheme 은 real-target measurement 이며 PHASE_GATES §4.1 2항 금지다."
        )
    if parsed.netloc not in ("", "localhost"):
        raise NavigationBlockedError(
            f"file:// URL 에 host 가 붙어 있다: {parsed.netloc!r} (url={url!r})"
        )

    target = Path(parsed.path).resolve()
    if fixture_root is not None:
        root = Path(fixture_root).resolve()
        if not target.is_relative_to(root):
            raise NavigationBlockedError(
                f"fixture_root({root}) 바깥의 경로다: {target} — "
                "fixture 세트 밖 파일을 여는 것은 이 lane 의 범위가 아니다."
            )
    return f"file://{target}"


def firewall_state(scope: object | None = None) -> dict[str, object]:
    """감사·보고용 상태 스냅샷. 보고서에 그대로 실을 수 있게 원시값만 담는다.

    `scope` 를 주면 그 scope 의 런타임 릴리스 판정까지 함께 싣는다 — 실제 수집 run 의
    provenance 는 이 값을 그대로 쓴다.
    """
    state: dict[str, object] = {
        "p0_gate_name": P0_GATE_NAME,
        "p0_gate_status": P0_GATE_STATUS,
        "shadow_lane": SHADOW_LANE,
        "allowed_modes": sorted(m.value for m in MODES_ALLOWED_BEFORE_P0),
        "known_scopes": sorted(s.value for s in ExecutionScope),
        "real_target_permitted": real_target_permitted(),
        "real_target_measurement": False,
        "fixture_only": True,
    }
    if scope is None:
        return state
    verdict = evaluate_execution_scope(scope)
    state["execution_scope"] = verdict.scope
    state["scope_verdict"] = verdict.as_dict()
    state["real_target_measurement"] = verdict.allowed
    state["fixture_only"] = not verdict.allowed
    return state


__all__ = [
    "E000_FAST_PLAN_CANDIDATES",
    "E001_RELEASE_PATH",
    "FIXTURE_URL_SCHEMES",
    "MODES_ALLOWED_BEFORE_P0",
    "P0_GATE_NAME",
    "P0_GATE_STATUS",
    "P0_RELEASE_PATH",
    "P0_RELEASE_REF",
    "REAL_TARGET_URL_SCHEMES",
    "SHADOW_LANE",
    "AllowlistUnavailableError",
    "ExecutionMode",
    "ExecutionScope",
    "ExecutionScopeBlockedError",
    "FirewallError",
    "NavigationBlockedError",
    "RealTargetBlockedError",
    "ReleaseDocument",
    "ReleaseVerdict",
    "TargetAllowlist",
    "TargetNotAllowlistedError",
    "UnknownExecutionModeError",
    "UnknownExecutionScopeError",
    "assert_mode_allowed",
    "assert_navigation_allowed",
    "assert_real_target_scope_allowed",
    "assert_target_allowlisted",
    "evaluate_execution_scope",
    "firewall_state",
    "load_e000_fast_allowlist",
    "load_scope_allowlist",
    "p0_closed",
    "read_release_document",
    "real_target_permitted",
    "reset_allowlist_cache",
    "reset_release_cache",
    "resolve_execution_mode",
    "resolve_execution_scope",
]
