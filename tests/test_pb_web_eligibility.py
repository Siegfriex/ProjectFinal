"""P-B — `web_eligibility.py` 규칙 EL-1~EL-4, web_target_status 전이, supersede 경로.

이 파일이 지키는 것: **verdict 없이 자격만** 판정하는 인프라가 실제로 그 경계를
지키는지 — 근거 없는 배제, 근거 없는 적격 판정, 허용되지 않는 상태 전이를
구조 규칙으로 막는다.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
RESEARCH = REPO / "research" / "landing_accessibility"
sys.path.insert(0, str(RESEARCH / "src"))

from landing_accessibility.web_eligibility import (  # noqa: E402
    MEASUREMENT_DETAIL_TO_ELIGIBILITY,
    WEB_ELIGIBILITY_STATUS,
    WEB_TARGET_STATUS,
    ProbeSignal,
    UrlEvidenceItem,
    WebEligibilityError,
    brand_match_tokens,
    determine_web_eligibility,
    deterministic_confidence_from_probe,
    deterministic_probe_signal,
    evaluate_supersede,
    probe_evidence_detail,
    suggest_status_from_probe_signal,
    title_identifies_brand,
    validate_target_status_transition,
)

NOW = "2026-08-27T00:00:00+00:00"


def _ev(evidence_type: str, detail: str = "x") -> UrlEvidenceItem:
    return UrlEvidenceItem(evidence_type=evidence_type, detail=detail, observed_at=NOW)


# ── 어휘 정합 ────────────────────────────────────────────────────────────────


def test_vocabulary_matches_a2_1_3_exactly() -> None:
    """A2 §1.3 이 확정한 6값과 정확히 같아야 한다 — 더 많지도 적지도 않다."""
    assert {
        "NOT_ASSESSED",
        "EXCLUDED_INDUSTRY_AXIS",
        "ELIGIBLE_WEB",
        "EXCLUDED_APP_ONLY",
        "EXCLUDED_NO_PUBLIC_WEB_LANDING",
        "UNDETERMINED_URL_EVIDENCE",
    } == WEB_ELIGIBILITY_STATUS


def test_vocabulary_does_not_leak_v1_06_tokens() -> None:
    """v1(`06`) 토큰(WEB_SERVICE 등)이 이 모듈의 상태값 집합에 섞이지 않았는지 확인한다."""
    v1_tokens = {
        "WEB_SERVICE",
        "OFFICIAL_PRODUCT_PAGE",
        "APP_ONLY",
        "SYSTEM_APP",
        "RETAIL_OFFLINE_ONLY",
        "UNRESOLVED",
    }
    assert WEB_ELIGIBILITY_STATUS.isdisjoint(v1_tokens)


def test_target_status_vocabulary_matches_a2_1_4() -> None:
    assert {"DRAFT", "PENDING_URL_REVIEW", "FROZEN", "EXCLUDED", "SUPERSEDED"} == WEB_TARGET_STATUS


# ── 규칙 EL-1: NOT_ASSESSED 만 근거 없이 허용 ───────────────────────────────


def test_not_assessed_requires_no_evidence() -> None:
    det = determine_web_eligibility(
        status="NOT_ASSESSED",
        basis="아직 평가 안 함",
        evidence=[],
        confidence=0.0,
        reviewer="tester",
    )
    assert det.web_eligibility_status == "NOT_ASSESSED"


def test_excluded_industry_axis_requires_evidence() -> None:
    with pytest.raises(WebEligibilityError):
        determine_web_eligibility(
            status="EXCLUDED_INDUSTRY_AXIS",
            basis="업종 축",
            evidence=[],
            confidence=1.0,
            reviewer="tester",
        )


# ── 규칙 EL-2: PRIOR_HYPOTHESIS 단독으로 배제 판정 불가 ─────────────────────


def test_prior_hypothesis_alone_cannot_justify_app_only_exclusion() -> None:
    """`system_app_hypothesis.json` 류의 사전판단만으로는 EXCLUDED_APP_ONLY 를 못 낸다."""
    with pytest.raises(WebEligibilityError, match="EL-2"):
        determine_web_eligibility(
            status="EXCLUDED_APP_ONLY",
            basis="선탑재 가설",
            evidence=[_ev("PRIOR_HYPOTHESIS", "system_app_hypothesis.json 11건 중 1건")],
            confidence=0.6,
            reviewer="tester",
        )


def test_prior_hypothesis_plus_dom_inspection_can_justify_exclusion() -> None:
    det = determine_web_eligibility(
        status="EXCLUDED_APP_ONLY",
        basis="사전 가설을 실제 접속으로 확인함",
        evidence=[
            _ev("PRIOR_HYPOTHESIS", "선탑재 가설"),
            _ev("DOM_INSPECTION", "접속 시 앱스토어 리다이렉트만 존재, 공개 웹 랜딩 없음"),
        ],
        confidence=0.9,
        reviewer="tester",
    )
    assert det.web_eligibility_status == "EXCLUDED_APP_ONLY"


def test_no_public_web_landing_requires_confirming_evidence() -> None:
    with pytest.raises(WebEligibilityError, match="EL-2"):
        determine_web_eligibility(
            status="EXCLUDED_NO_PUBLIC_WEB_LANDING",
            basis="추측",
            evidence=[_ev("MANUAL_REVIEW_NOTE", "아마 없을 것 같다")],
            confidence=0.5,
            reviewer="tester",
        )


# ── 규칙 EL-3: URL 존재 ≠ 적격 ──────────────────────────────────────────────


def test_eligible_web_requires_both_reachability_and_identity_evidence() -> None:
    """HTTP_PROBE 만으로는(URL 이 열린다는 사실만으로는) ELIGIBLE_WEB 을 낼 수 없다."""
    with pytest.raises(WebEligibilityError, match="EL-3"):
        determine_web_eligibility(
            status="ELIGIBLE_WEB",
            basis="접속은 됨",
            evidence=[_ev("HTTP_PROBE", "HTTP 200")],
            confidence=0.9,
            reviewer="tester",
        )


def test_eligible_web_with_reachability_and_identity_evidence_succeeds() -> None:
    det = determine_web_eligibility(
        status="ELIGIBLE_WEB",
        basis="접속 확인 + 원문 표기와 등록도메인 대조 완료",
        evidence=[
            _ev("HTTP_PROBE", "HTTP 200, 리다이렉트 없음"),
            _ev("SOURCE_LABEL_MATCH", "A1 원문 표기 '네이버'와 일치"),
        ],
        confidence=0.95,
        reviewer="tester",
    )
    assert det.web_eligibility_status == "ELIGIBLE_WEB"
    assert len(det.evidence) == 2


def test_confidence_out_of_range_rejected() -> None:
    with pytest.raises(WebEligibilityError):
        determine_web_eligibility(
            status="NOT_ASSESSED",
            basis="x",
            evidence=[],
            confidence=1.5,
            reviewer="t",
        )


def test_empty_basis_rejected() -> None:
    with pytest.raises(WebEligibilityError):
        determine_web_eligibility(
            status="NOT_ASSESSED",
            basis="   ",
            evidence=[],
            confidence=0.0,
            reviewer="t",
        )


def test_unknown_evidence_type_rejected() -> None:
    with pytest.raises(WebEligibilityError):
        UrlEvidenceItem(evidence_type="GUESS", detail="x", observed_at=NOW)


# ── web_target_status 전이 (A2 §1.4) ────────────────────────────────────────


@pytest.mark.parametrize(
    "src,dst",
    [
        ("DRAFT", "PENDING_URL_REVIEW"),
        ("PENDING_URL_REVIEW", "FROZEN"),
        ("PENDING_URL_REVIEW", "EXCLUDED"),
        ("FROZEN", "SUPERSEDED"),
    ],
)
def test_allowed_transitions(src: str, dst: str) -> None:
    validate_target_status_transition(src, dst)  # 예외 없이 통과해야 한다


@pytest.mark.parametrize(
    "src,dst",
    [
        ("DRAFT", "FROZEN"),  # PENDING_URL_REVIEW 건너뜀
        ("EXCLUDED", "FROZEN"),  # terminal 에서 탈출
        ("SUPERSEDED", "FROZEN"),  # terminal 에서 탈출
        ("FROZEN", "EXCLUDED"),  # FROZEN 은 SUPERSEDED 로만 나간다
        ("FROZEN", "DRAFT"),  # 역행
    ],
)
def test_forbidden_transitions_rejected(src: str, dst: str) -> None:
    with pytest.raises(WebEligibilityError):
        validate_target_status_transition(src, dst)


# ── supersede 경로 (A2 §1.4.1, 규칙 W-1~W-3) ────────────────────────────────


def test_supersede_requires_frozen_source() -> None:
    with pytest.raises(WebEligibilityError):
        evaluate_supersede(
            current_target_status="PENDING_URL_REVIEW",
            measurement_status_detail="APP_ONLY_AT_COLLECTION",
        )


@pytest.mark.parametrize(
    "detail,expected_eligibility",
    list(MEASUREMENT_DETAIL_TO_ELIGIBILITY.items()),
)
def test_supersede_maps_detail_to_eligibility(detail: str, expected_eligibility: str) -> None:
    result = evaluate_supersede(current_target_status="FROZEN", measurement_status_detail=detail)
    assert result.observation_measurement_status == "NOT_ELIGIBLE_AT_COLLECTION"
    assert result.superseded_web_target_status == "SUPERSEDED"
    assert result.new_web_target_status == "EXCLUDED"
    assert result.new_web_eligibility_status == expected_eligibility


def test_supersede_only_moves_toward_exclusion() -> None:
    """규칙 W-2 — 이 함수 자체가 배제 방향 결과만 낼 수 있는 구조인지 (반환 도메인 검사)."""
    for detail in MEASUREMENT_DETAIL_TO_ELIGIBILITY:
        result = evaluate_supersede(
            current_target_status="FROZEN", measurement_status_detail=detail
        )
        assert result.new_web_target_status == "EXCLUDED"


# ── deterministic probe signal (AI 호출 없음, 00 §10 cascade 1단계) ────────


def test_app_store_redirect_flags_terminates_at_app_store() -> None:
    record = {
        "target_url": "https://example.com",
        "final_url": "https://play.google.com/store/apps/details?id=com.example",
        "http_status": 200,
        "error": None,
        "final_registered_domain": "google.com",
        "target_registered_domain": "example.com",
    }
    signal = deterministic_probe_signal(record)
    assert signal.terminates_at_app_store is True
    status, needs_review = suggest_status_from_probe_signal(signal)
    assert status == "EXCLUDED_APP_ONLY"
    assert needs_review is True  # 제안일 뿐, 자동 확정이 아니다


def test_suggestion_alone_cannot_be_written_as_final_determination() -> None:
    """suggest_status_from_probe_signal 의 출력을 그대로 determine_web_eligibility 에
    evidence 없이 넣으면 EL-1/EL-2 가 막아야 한다 — 제안과 판정 사이에 검증이 있다."""
    signal = ProbeSignal(
        reachable=False,
        terminates_at_app_store=False,
        final_registered_domain=None,
        target_registered_domain="example.com",
        same_registered_domain=False,
        http_status=None,
        error="ConnectionError",
    )
    status, _ = suggest_status_from_probe_signal(signal)
    assert status == "UNDETERMINED_URL_EVIDENCE"
    # UNDETERMINED_URL_EVIDENCE 도 evidence 최소 1건은 필요하다 (EL-1).
    with pytest.raises(WebEligibilityError):
        determine_web_eligibility(
            status=status,
            basis="접속 실패",
            evidence=[],
            confidence=0.3,
            reviewer="t",
        )


# ── C013 salvage helpers (confidence_of / brand_tokens / title_identifies_brand /
#    evidence_of 재구현) — c013_salvage_ledger.json 이 "전용 단위테스트 없음" 이라 적은
#    격차를 닫는다. ──────────────────────────────────────────────────────────────


def test_deterministic_confidence_high_when_reachable_with_title() -> None:
    record = {"http_status": 200, "error": None, "page_title": "네이버"}
    assert deterministic_confidence_from_probe(record) == 0.9


def test_deterministic_confidence_medium_when_reachable_without_title() -> None:
    record = {"http_status": 200, "error": None, "page_title": None}
    assert deterministic_confidence_from_probe(record) == 0.5


def test_deterministic_confidence_medium_when_blocked_status() -> None:
    record = {"http_status": 403, "error": None, "page_title": None}
    assert deterministic_confidence_from_probe(record) == 0.5


def test_deterministic_confidence_low_on_error() -> None:
    record = {"http_status": None, "error": "ConnectionError", "page_title": None}
    assert deterministic_confidence_from_probe(record) == 0.2


def test_deterministic_confidence_low_on_server_error_status() -> None:
    record = {"http_status": 500, "error": None, "page_title": None}
    assert deterministic_confidence_from_probe(record) == 0.2


def test_brand_match_tokens_includes_name_key_and_domain() -> None:
    tokens = brand_match_tokens("네이버", "naver_app", "https://www.naver.com")
    assert "네이버" in tokens
    assert "naver" in tokens  # canonical_service_key 파생
    assert "naver" in tokens  # 등록도메인 첫 라벨(중복이어도 무방 — set 기반)


def test_brand_match_tokens_without_url_still_works() -> None:
    tokens = brand_match_tokens("밴드", "band", None)
    assert "밴드" in tokens
    assert "band" in tokens


def test_title_identifies_brand_true_when_token_present() -> None:
    tokens = brand_match_tokens("네이버", "naver_app", "https://www.naver.com")
    result = title_identifies_brand({"page_title": "네이버 : 대한민국 대표 포털"}, tokens)
    assert result is True


def test_title_identifies_brand_none_when_title_missing() -> None:
    tokens = brand_match_tokens("네이버", "naver_app", None)
    assert title_identifies_brand({"page_title": None}, tokens) is None
    assert title_identifies_brand({}, tokens) is None


def test_title_identifies_brand_false_when_unrelated_title() -> None:
    tokens = brand_match_tokens("네이버", "naver_app", "https://www.naver.com")
    result = title_identifies_brand({"page_title": "완전히 무관한 페이지 제목입니다"}, tokens)
    assert result is False


def test_probe_evidence_detail_no_url() -> None:
    assert probe_evidence_detail({}, None) == "확정할 URL이 없다."


def test_probe_evidence_detail_error() -> None:
    detail = probe_evidence_detail({"error": "Timeout"}, "https://example.com")
    assert "접속 실패" in detail
    assert "Timeout" in detail


def test_probe_evidence_detail_success_includes_status_and_title() -> None:
    record = {
        "http_status": 200,
        "error": None,
        "final_url": "https://example.com/",
        "redirect_chain": [{"status": 301, "from": "http://example.com", "to": None}],
        "page_title": "Example Domain",
        "final_registered_domain": "example.com",
    }
    detail = probe_evidence_detail(record, "https://example.com")
    assert "HTTP 200" in detail
    assert "최종 URL" in detail
    assert "리다이렉트 1회" in detail
    assert "Example Domain" in detail
    assert "example.com" in detail


def test_probe_evidence_detail_missing_title_says_so() -> None:
    record = {
        "http_status": 200,
        "error": None,
        "final_url": None,
        "redirect_chain": [],
        "page_title": None,
    }
    detail = probe_evidence_detail(record, "https://example.com")
    assert "페이지 제목 미획득" in detail
