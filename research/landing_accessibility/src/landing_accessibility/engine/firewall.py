"""REAL-TARGET FIREWALL — `PHASE_GATES.md §4.5`.

P0(`V2_SSOT_FROZEN`)가 닫히기 전에는 **실제 서비스 target에 접속해 접근성 결과를 생성하는
어떤 코드도 실행되어서는 안 된다.** `PHASE_GATES §4.1` 2~5항이 그것을 금지하고,
`§4.5`가 그 금지를 수집기의 `execution_mode`로 기계화하라고 지시한다.

    FIXTURE          허용 — 로컬 synthetic fixture (file:// 만)
    SHADOW_DRY_RUN   허용 — 어떤 항해도 하지 않는 계획/검증 전용
    REAL_TARGET      hard FAIL

이 모듈이 그 표다. **문서가 아니라 이 파일이 금지를 집행한다.**

## 왜 enum 값을 지우지 않고 남겨 두는가

`REAL_TARGET`을 어휘에서 삭제하면 "그 모드를 요청했다"는 사건 자체를 표현할 수 없게 되고,
호출부는 오타·`KeyError`로 실패한다. 그러면 실패의 이유가 "금지된 모드를 요청했다"가 아니라
"알 수 없는 값"이 되어, 실패주입 harness가 **무엇을 차단했는지 증명하지 못한다.**
값은 남기고 **게이트를 닫는다.**

## 이 게이트를 여는 방법은 이 파일을 고치는 것뿐이다

환경변수·인자·설정파일로 열리지 않는다. 그렇게 두면 실수 한 번으로 열린다.
P0 종료 후 `PHASE_GATES §4.7` SHADOW RECONCILIATION을 거친 뒤 **의도적으로**
`P0_GATE_STATUS`를 바꾸는 커밋이 있어야 하고, 그 커밋은 감사 대상이 된다.
"""

from __future__ import annotations

from enum import StrEnum
from pathlib import Path
from urllib.parse import urlparse

#: `PHASE_GATES.md §1` — 이 게이트가 닫히기 전까지 REAL_TARGET 은 hard FAIL 이다.
P0_GATE_NAME = "V2_SSOT_FROZEN"

#: `EXECUTION_AUTHORITY §1` — `CURRENT_GATE = V2_SSOT_FROZEN (미달성)`.
P0_GATE_STATUS = "OPEN"

#: `PHASE_GATES.md §4.4` — 이 코드가 속한 lane.
SHADOW_LANE = "LANE_C"


class ExecutionMode(StrEnum):
    """`PHASE_GATES §4.5`의 세 값. 닫힌 집합이다 (A2 규칙 S-3)."""

    FIXTURE = "FIXTURE"
    SHADOW_DRY_RUN = "SHADOW_DRY_RUN"
    REAL_TARGET = "REAL_TARGET"


#: P0 종료 전 허용되는 모드.
MODES_ALLOWED_BEFORE_P0: frozenset[ExecutionMode] = frozenset(
    {ExecutionMode.FIXTURE, ExecutionMode.SHADOW_DRY_RUN}
)

#: FIXTURE 모드에서 허용되는 유일한 URL scheme.
FIXTURE_URL_SCHEMES: frozenset[str] = frozenset({"file"})


class FirewallError(RuntimeError):
    """REAL-TARGET FIREWALL 위반. 절대 삼키지 않는다."""


class RealTargetBlockedError(FirewallError):
    """`REAL_TARGET` 모드 요청 — `PHASE_GATES §4.5` hard FAIL."""


class UnknownExecutionModeError(FirewallError):
    """닫힌 집합 밖의 모드 값 (A2 규칙 S-3 — `UNKNOWN`으로 흡수하지 않는다)."""


class NavigationBlockedError(FirewallError):
    """허용된 모드이나 그 모드가 허가하지 않는 항해를 시도했다."""


def p0_closed() -> bool:
    """P0 게이트가 닫혔는가. 지금은 항상 `False`."""
    return P0_GATE_STATUS == "CLOSED"


def real_target_permitted() -> bool:
    """`REAL_TARGET` 이 허용되는가.

    P0가 닫히기 전에는 항상 `False`다. 닫힌 뒤에도 이 함수가 `True`를 돌려주려면
    `PHASE_GATES §4.7` reconciliation을 거친 명시적 커밋이 필요하다.
    """
    return p0_closed()


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


def assert_mode_allowed(mode: object) -> ExecutionMode:
    """이 시점에 그 모드로 수집기를 켤 수 있는지 확인한다.

    `REAL_TARGET`은 P0 종료 전 **무조건** 차단된다 (`PHASE_GATES §4.5`).
    """
    resolved = resolve_execution_mode(mode)
    if resolved is ExecutionMode.REAL_TARGET and not real_target_permitted():
        raise RealTargetBlockedError(
            "REAL_TARGET 은 hard FAIL 이다 — "
            f"{P0_GATE_NAME} 게이트가 {P0_GATE_STATUS} 이다 (PHASE_GATES §4.5). "
            "P0 종료 전 real-target accessibility evidence collection 은 §4.1 2~5항 금지."
        )
    if resolved not in MODES_ALLOWED_BEFORE_P0 and not p0_closed():
        raise FirewallError(f"{resolved.value} 는 P0 종료 전 허용되지 않는다 (PHASE_GATES §4.5)")
    return resolved


def assert_navigation_allowed(mode: object, url: str, *, fixture_root: Path | None = None) -> str:
    """항해 직전 호출한다. 통과하면 정규화된 URL을 돌려준다.

    - `REAL_TARGET` — 차단 (`assert_mode_allowed`).
    - `SHADOW_DRY_RUN` — **어떤 항해도 하지 않는다.** 계획·스키마 검증 전용 모드이므로
      URL이 file:// 이어도 차단한다. 이 구분이 없으면 dry-run 이 조용히 수집기가 된다.
    - `FIXTURE` — `file://` 만, 그리고 `fixture_root` 안쪽만 허용한다.
      `http`/`https`/`ws`/`data` 는 전부 차단이다.
    """
    resolved = assert_mode_allowed(mode)

    if resolved is ExecutionMode.SHADOW_DRY_RUN:
        raise NavigationBlockedError(
            "SHADOW_DRY_RUN 은 항해하지 않는다 (PHASE_GATES §4.5). "
            f"요청된 URL: {url!r}. fixture 를 실제로 열려면 FIXTURE 모드를 쓴다."
        )

    parsed = urlparse(url)
    scheme = parsed.scheme.lower()
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


def firewall_state() -> dict[str, object]:
    """감사·보고용 상태 스냅샷. 보고서에 그대로 실을 수 있게 원시값만 담는다."""
    return {
        "p0_gate_name": P0_GATE_NAME,
        "p0_gate_status": P0_GATE_STATUS,
        "shadow_lane": SHADOW_LANE,
        "allowed_modes": sorted(m.value for m in MODES_ALLOWED_BEFORE_P0),
        "real_target_permitted": real_target_permitted(),
        "real_target_measurement": False,
        "fixture_only": True,
    }
