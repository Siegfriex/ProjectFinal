"""P-C FIXTURE — overlay 검출(공간/차단/의미분류)과 AI review cascade 배선 검증.

둘 다 Playwright 를 쓰지 않는다 — overlay 는 순수 기하 계산, cascade 는
결정론적 스텁 분류기로 배선만 확인한다(실제 VLM 호출 없음, 이 레인의 제약).
"""

from __future__ import annotations

import sys
from pathlib import Path

RESEARCH = Path(__file__).resolve().parents[1] / "research" / "landing_accessibility"
sys.path.insert(0, str(RESEARCH / "src"))

from landing_accessibility.pc_fixture import overlay, review_cascade  # noqa: E402

# ---------------------------------------------------------------------------
# overlay.py
# ---------------------------------------------------------------------------


def test_full_screen_modal_is_blocking_and_classified_promotion():
    viewport = overlay.BBox(0, 0, 390, 844)
    primary = overlay.BBox(20, 700, 200, 44)  # 대표기능 버튼, 하단
    candidate = overlay.OverlayCandidate(
        element_ref="promo-modal",
        bbox=overlay.BBox(0, 0, 390, 844),  # 전체화면 덮음
        role_dialog=True,
        aria_modal=True,
        dom_text_sample="지금 앱 설치하고 더 편리하게 이용하세요",
        dismiss_control_present=True,
    )
    assert candidate.is_candidate is True
    result = overlay.assess_overlay(candidate, viewport, primary, must_dismiss_for_primary=True)
    assert result.overlay_coverage == 1.0
    assert result.primary_action_occlusion == 1.0
    assert result.is_blocking is True
    assert result.overlay_class == "APP_INSTALL_PROMPT"
    assert result.classification_source == "DOM_TEXT_RULE"


def test_small_corner_toast_not_blocking():
    viewport = overlay.BBox(0, 0, 390, 844)
    primary = overlay.BBox(20, 700, 200, 44)
    candidate = overlay.OverlayCandidate(
        element_ref="toast",
        bbox=overlay.BBox(10, 10, 200, 40),  # 작은 코너 알림, 대표기능과 안 겹침
        is_fixed_or_sticky=True,
        dom_text_sample="",
    )
    result = overlay.assess_overlay(candidate, viewport, primary, must_dismiss_for_primary=False)
    assert result.is_blocking is False
    assert result.overlay_coverage < 0.1


def test_unclassifiable_overlay_falls_to_unknown_not_silently_dropped():
    viewport = overlay.BBox(0, 0, 390, 844)
    candidate = overlay.OverlayCandidate(
        element_ref="mystery",
        bbox=overlay.BBox(0, 0, 100, 100),
        is_fixed_or_sticky=True,
        dom_text_sample="아무 의미 없는 텍스트 xyz",
    )
    result = overlay.assess_overlay(candidate, viewport, None, must_dismiss_for_primary=False)
    assert result.overlay_class == "UNKNOWN"
    assert result.classification_source == "UNCLASSIFIED"


def test_semantic_classifier_hook_is_used_when_dom_rule_abstains():
    viewport = overlay.BBox(0, 0, 390, 844)
    candidate = overlay.OverlayCandidate(
        element_ref="mystery",
        bbox=overlay.BBox(0, 0, 100, 100),
        is_fixed_or_sticky=True,
        dom_text_sample="아무 의미 없는 텍스트",
    )

    def stub_vlm(_c: overlay.OverlayCandidate) -> str | None:
        return "BANNER"

    result = overlay.assess_overlay(
        candidate, viewport, None, must_dismiss_for_primary=False, classifier=stub_vlm
    )
    assert result.overlay_class == "BANNER"
    assert result.classification_source == "VLM_PENDING_RESOLVED"


# ---------------------------------------------------------------------------
# review_cascade.py
# ---------------------------------------------------------------------------


def _abstain(_evidence: dict) -> str | None:
    return None


def test_deterministic_stage_short_circuits():
    cascade = review_cascade.ReviewCascade(
        deterministic=lambda e: "PASS" if e.get("obvious") else None,
        semantic=_abstain,
        reviewer_a=_abstain,
        reviewer_b=_abstain,
        arbiter=lambda e, a, b: None,
    )
    r = cascade.review("item1", {"obvious": True})
    assert r.stage_reached == "deterministic"
    assert r.label == "PASS"


def test_reviewer_disagreement_goes_through_arbiter_not_picked_arbitrarily():
    cascade = review_cascade.ReviewCascade(
        deterministic=_abstain,
        semantic=_abstain,
        reviewer_a=lambda e: "COOKIE_CONSENT",
        reviewer_b=lambda e: "PROMOTION_MODAL",
        arbiter=lambda e, a, b: "PROMOTION_MODAL",
    )
    r = cascade.review("item2", {})
    assert r.stage_reached == "arbiter"
    assert r.disagreement is True
    assert r.label == "PROMOTION_MODAL"
    assert r.reviewer_a_label == "COOKIE_CONSENT"
    assert r.reviewer_b_label == "PROMOTION_MODAL"


def test_human_final_budget_caps_at_five_then_undetermined():
    cascade = review_cascade.ReviewCascade(
        deterministic=_abstain,
        semantic=_abstain,
        reviewer_a=lambda e: "A",
        reviewer_b=lambda e: "B",
        arbiter=lambda e, a, b: None,  # arbiter 도 확신 못함 -> HUMAN_FINAL
    )
    results = [cascade.review(f"item{i}", {}) for i in range(7)]
    queued = [r for r in results if r.stage_reached == "HUMAN_FINAL_QUEUED"]
    overflowed = [r for r in results if r.stage_reached == "UNDETERMINED"]
    assert len(queued) == 5  # HUMAN_FINAL_REVIEW_MAX
    assert len(overflowed) == 2
    assert all(r.label == "UNDETERMINED" for r in overflowed)
    assert cascade.human_final_used == 5
    assert len(cascade.human_final_queue) == 5


def test_agreement_does_not_consume_human_final_budget():
    cascade = review_cascade.ReviewCascade(
        deterministic=_abstain,
        semantic=_abstain,
        reviewer_a=lambda e: "SAME",
        reviewer_b=lambda e: "SAME",
        arbiter=lambda e, a, b: None,
    )
    for i in range(10):
        cascade.review(f"item{i}", {})
    assert cascade.human_final_used == 0
