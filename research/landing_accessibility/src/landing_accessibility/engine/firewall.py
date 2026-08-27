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
P0_GATE_STATUS = "OPEN"

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
    - `E001_FULL` — E001 본수집. **지금은 항상 차단**이며, `E001_RELEASE.json` 이
      `status == RELEASED` 로 존재해야만 열린다 (A 의 별도 릴리스 티켓).
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


def load_scope_allowlist(scope: object, *, path: str | Path | None = None) -> TargetAllowlist:
    resolved = resolve_execution_scope(scope)
    if resolved is ExecutionScope.E000_FAST:
        return load_e000_fast_allowlist(path)
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
