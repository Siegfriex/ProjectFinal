"""SHADOW / PREPARATORY 산출물 공통 규약 — `PHASE_GATES.md` §4 (A0 결정, 2026-08-27).

`docs/v2/PHASE_GATES.md` §4 가 SHADOW 정책의 **유일한 정의부**다. 이 모듈은 그 절을
코드로 강제하는 것이지 정책을 다시 선언하지 않는다 — 정책표를 복제하면 그 자체가 drift다
(§4 머리말).

원본 확인 경로 (체크아웃하지 않고 읽기만):

    git -C <repo> show origin/agent/landing-v2-exec:research/landing_accessibility/docs/v2/PHASE_GATES.md

## 이 모듈이 강제하는 것

- §4.5 REAL-TARGET FIREWALL: `execution_mode ∈ {FIXTURE, SHADOW_DRY_RUN}` 만 P0 종료 전
  허용된다. `REAL_TARGET` 은 hard FAIL.
- §4.3 산출물 상태: 모든 P-B 산출물이 갖춰야 하는 provenance 필드 6종(+ `shadow_lane`).
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

#: §4.5 표. `REAL_TARGET` 은 값 자체는 알고 있어야 hard FAIL 을 낼 수 있으므로 열거형에는
#: 포함하되, "P0 종료 전 허용" 집합에서는 뺀다.
EXECUTION_MODES: frozenset[str] = frozenset({"FIXTURE", "SHADOW_DRY_RUN", "REAL_TARGET"})
ALLOWED_BEFORE_P0_CLOSE: frozenset[str] = frozenset({"FIXTURE", "SHADOW_DRY_RUN"})

BASE_SHA = "d5f1da5"  # claude-b/pb-prework 브랜치 base (agent/landing-v2-exec @ d5f1da5)


class RealTargetFirewallError(RuntimeError):
    """§4.5 REAL-TARGET FIREWALL 위반. P0 종료 전에는 예외 없이 hard FAIL 이다."""


def require_execution_mode(mode: str) -> str:
    """`mode` 가 P0 종료 전 허용값인지 검증하고 그대로 돌려준다.

    통과하는 것 자체가 "이 로직이 실제 접근성 verdict 를 생성하지 않는다"는 증거는
    아니다 — 그건 각 모듈이 별도로 지켜야 한다(예: `web_eligibility.py` 는 KWCAG 판정을
    아예 만들지 않는다). 이 함수는 오직 **collector 실행 모드**만 본다.
    """
    if mode not in EXECUTION_MODES:
        raise RealTargetFirewallError(
            f"execution_mode={mode!r} 은 §4.5 의 열거형 밖이다. 허용: {sorted(EXECUTION_MODES)}"
        )
    if mode not in ALLOWED_BEFORE_P0_CLOSE:
        raise RealTargetFirewallError(
            f"execution_mode={mode!r} 은 P0 종료 전 hard FAIL 이다 (PHASE_GATES.md §4.5). "
            f"허용: {sorted(ALLOWED_BEFORE_P0_CLOSE)}"
        )
    return mode


def shadow_provenance(
    *,
    shadow_lane: str,
    execution_mode: str,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """§4.3 이 요구하는 provenance 블록을 만든다.

    `execution_mode` 는 여기서도 검증한다 — provenance 블록을 만드는 것과 실행을
    허가하는 것이 분리된 두 번의 검사여서는 안 된다(하나가 우회되면 다른 하나가 잡는다).
    """
    require_execution_mode(execution_mode)
    block: dict[str, Any] = {
        "base_sha": BASE_SHA,
        "created_at": datetime.now(UTC).isoformat(),
        "created_before_p0_close": True,
        "authoritative": False,
        "real_target_outcome_used": False,
        "requires_post_p0_reconciliation": True,
        "shadow_lane": shadow_lane,
        "execution_mode": execution_mode,
        "status": "SHADOW_PREPARATORY",
    }
    if extra:
        block.update(extra)
    return block
