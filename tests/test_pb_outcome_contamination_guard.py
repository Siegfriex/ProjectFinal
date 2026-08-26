"""P-B — `outcome_contamination_guard.py`. §4.6 교차오염 금지의 코드 레벨 강제."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
RESEARCH = REPO / "research" / "landing_accessibility"
sys.path.insert(0, str(RESEARCH / "src"))

from landing_accessibility.outcome_contamination_guard import (  # noqa: E402
    OutcomeContaminationError,
    assert_selection_input_clean,
    find_contamination,
)


def test_clean_payload_passes() -> None:
    payload = {
        "measurement_entity_id": "svc_a",
        "canonical_service_key": "naver_app",
        "service_name": "네이버",
        "official_landing_url": "https://naver.com",
        "web_eligibility_status": "ELIGIBLE_WEB",
        "source_membership": ["panel_1"],
    }
    assert find_contamination(payload) == []
    assert_selection_input_clean(payload, context="test")  # 예외 없이 통과해야 한다


@pytest.mark.parametrize(
    "forbidden_key,forbidden_value",
    [
        ("verdict_state", "PASS"),
        ("mpfed", 3),
        ("ned", 1),
        ("ied", 2),
        ("popup_detected", True),
        ("overlay_coverage", 0.4),
        ("accessibility_verdict", "FAIL"),
        ("screenshot_initial_path", "evidence/x.png"),
        ("dom_path", "evidence/x.html"),
    ],
)
def test_forbidden_concepts_rejected(forbidden_key: str, forbidden_value: object) -> None:
    payload = {"measurement_entity_id": "svc_a", forbidden_key: forbidden_value}
    findings = find_contamination(payload)
    assert findings, f"{forbidden_key} 가 잡히지 않았다"
    with pytest.raises(OutcomeContaminationError):
        assert_selection_input_clean(payload, context="test")


def test_certified_current_forbidden_only_in_selection_context() -> None:
    """certified_current 필드 자체는 certification_join.py 의 정당한 출력이다 — 존재가
    아니라 selection 입력으로 쓰일 때만 금지된다."""
    payload = {"web_target_id": "wt_x", "certified_current": 1}
    assert find_contamination(payload, selection_context=False) == []
    with pytest.raises(OutcomeContaminationError):
        assert_selection_input_clean(payload, context="task_selection")


def test_nested_payload_is_scanned() -> None:
    payload = {"entity": {"nested": {"kwcag_summary": {"fail_count": 3}}}}
    findings = find_contamination(payload)
    assert findings


def test_real_target_evidence_paths_rejected() -> None:
    payload = {"manifest_path": "evidence/run1/manifest.json"}
    with pytest.raises(OutcomeContaminationError):
        assert_selection_input_clean(payload, context="test")


# ── self-audit — 이 lane 이 만든 모듈들의 출력이 실제로 깨끗한지 ────────────


def test_self_audit_web_eligibility_determination_is_clean() -> None:
    from landing_accessibility.web_eligibility import (
        UrlEvidenceItem,
        determine_web_eligibility,
    )

    det = determine_web_eligibility(
        status="ELIGIBLE_WEB",
        basis="test",
        evidence=[
            UrlEvidenceItem("HTTP_PROBE", "200", "2026-08-27T00:00:00+00:00"),
            UrlEvidenceItem("SOURCE_LABEL_MATCH", "일치", "2026-08-27T00:00:00+00:00"),
        ],
        confidence=0.9,
        reviewer="tester",
    )
    findings = find_contamination(det.as_row(), selection_context=False)
    assert findings == []


def test_self_audit_certification_join_result_is_clean_as_infra_but_flagged_for_selection() -> None:
    """certified_current 는 infra 출력으로는 깨끗하다(selection_context=False) — 다만
    selection 맥락으로 스캔하면 잡혀야 한다(§4.6 이 금지하는 것은 존재가 아니라 용도다)."""
    from dataclasses import asdict

    from landing_accessibility.certification_join import build_dim_certification_row

    result = build_dim_certification_row(
        web_target_id="wt_x",
        web_target_service_name="테스트",
        web_target_registered_domain=None,
        certification_rows=[],
    )
    payload = asdict(result)
    assert find_contamination(payload, selection_context=False) == []
    with pytest.raises(OutcomeContaminationError):
        assert_selection_input_clean(payload, context="self-audit")
