"""REAL-TARGET FIREWALL — ``docs/v2/PHASE_GATES.md`` §4.5 (A0 결정, 2026-08-27).

P0(``P0_V2_REFREEZE``)가 닫히기 전에는 이 레인의 어떤 collector/engine 도 실제
서비스에 닿을 수 없다. 이 모듈은 그 금지를 문서 규칙이 아니라 코드가 절대
통과시키지 않는 값 검사로 만든다.

    execution_mode ∈ {FIXTURE, SHADOW_DRY_RUN, REAL_TARGET}

    FIXTURE          P0 종료 전 허용 — 로컬 ``file://`` 픽스처만 대상으로 한다.
    SHADOW_DRY_RUN   P0 종료 전 허용 — 실제 fetch/navigate 를 하지 않고
                     배선만 검증하는 dry-run.
    REAL_TARGET      P0 종료 전 **hard FAIL**. 이 값이 들어오는 즉시
                     ``RealTargetForbiddenError`` 를 던지고 아무 것도
                     실행하지 않는다.

이 가드는 이 레인의 모든 진입점(``guarded_writer.GuardedEvidenceWriter.__init__``,
``l0_collector.collect_l0_fixture``, ``scout.run_scout``,
``path_freeze.replay_path``)에서 다른 어떤 부수효과보다 먼저 호출된다 —
append-only 가드가 "정의만 되고 호출 안 되는" 실수를 반복했던 것과 같은
실패 모드를 여기서는 만들지 않는다: ``execution_mode`` 를 각 함수 서명의
필수 키워드 인자로 두어, 호출자가 실수로 가드를 건너뛸 수 없게 한다.
"""

from __future__ import annotations

ALLOWED_BEFORE_P0_CLOSE = frozenset({"FIXTURE", "SHADOW_DRY_RUN"})
EXECUTION_MODES = frozenset({"FIXTURE", "SHADOW_DRY_RUN", "REAL_TARGET"})

# 이 레인(P-C FIXTURE, worktree=claude_b_pc_fixture)은 Gate 를 스스로 닫지 않는다
# (PHASE_GATES.md §5 — orchestrator + 두 감사만 닫을 권한이 있다). 이 상수를 여기서
# True 로 바꾸는 것은 이 워크트리의 권한 밖이다. 실제 P0 종료 여부는 항상
# control/state.json (landing_orchestrator 워크트리, 커밋된 ref) 을 원본으로 재확인한다.
P0_CLOSED = False


class RealTargetForbiddenError(RuntimeError):
    """execution_mode=REAL_TARGET 이 P0 종료 전에 들어왔다 — hard FAIL."""


def enforce_real_target_firewall(execution_mode: str) -> None:
    """호출자가 반드시 첫 줄에서 불러야 하는 fail-closed 가드.

    알 수 없는 값도 통과시키지 않는다 — "허용 목록에 없으면 거부"가
    "금지 목록에 있으면 거부"보다 안전하다 (오탈자·새 값 추가 시 open-fail 방지).
    """
    if execution_mode not in EXECUTION_MODES:
        raise ValueError(
            f"알 수 없는 execution_mode: {execution_mode!r} (허용값: {sorted(EXECUTION_MODES)})"
        )
    if execution_mode == "REAL_TARGET" and not P0_CLOSED:
        raise RealTargetForbiddenError(
            "execution_mode=REAL_TARGET 은 P0_V2_REFREEZE 종료 전 hard FAIL 이다 "
            "(docs/v2/PHASE_GATES.md §4.5 REAL-TARGET FIREWALL). "
            "이 레인(P-C FIXTURE)은 FIXTURE 또는 SHADOW_DRY_RUN 만 허용한다."
        )
