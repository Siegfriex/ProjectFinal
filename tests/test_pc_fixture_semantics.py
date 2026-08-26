"""P-C FIXTURE — 순수 판정 로직 검증 (verdict / domain_scope / gate / dedup).

Playwright 를 쓰지 않는다. 각 테스트는 ``research/refcohort`` 감사
(``research/refcohort/audit/findings_registry.jsonl``)가 실측으로 확인한
결함 하나에 대응하고, 그 결함이 여기서는 재발하지 않음을 확인한다.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

RESEARCH = Path(__file__).resolve().parents[1] / "research" / "landing_accessibility"
sys.path.insert(0, str(RESEARCH / "src"))

from landing_accessibility.pc_fixture import dedup, domain_scope, gate, verdict  # noqa: E402

# ---------------------------------------------------------------------------
# verdict.py — 닫는 결함: guard-blind-to-na-undetermined-laundering (CRITICAL),
# undetermined-absorbed-into-pass (HIGH)
# ---------------------------------------------------------------------------


def test_partial_undetermined_stays_undetermined_not_pass():
    """refcohort 실증 사례 재현: c_1_2_1 에 media_track 1건(PASS) +
    media_embed 5건(UNDETERMINED) 을 넣으면 refcohort 는 verdict_state=PASS 를
    냈다(6개 중 5개가 증거 불충분인데 통과로 보고). 여기서는 UNDETERMINED 다."""
    obs = verdict.make_criterion_observation(
        "c_1_2_1", pass_count=1, fail_count=0, undetermined_count=5
    )
    assert obs.verdict_state == "UNDETERMINED"
    assert obs.partial_pass_count == 1  # 보존은 하되 승격 근거로 쓰지 않는다
    assert obs.applicable_count == 6


def test_na_requires_zero_applicable():
    """T1/T3 위조 재현: verdict_state=NA 인데 undetermined_count>0 을 직접
    구성하려 하면 생성 시점에 예외가 나야 한다 (guard 가 아니라 구조로 차단)."""
    with pytest.raises(verdict.VerdictSemanticError):
        verdict.CriterionObservation(
            criterion_id="c_x",
            applicable_count=12,
            pass_count=0,
            fail_count=0,
            undetermined_count=12,
            verdict_state="NA",
        )


def test_pass_requires_positive_applicable():
    """T2 위조 재현: applicable_count=0 인데 verdict_state=PASS."""
    with pytest.raises(verdict.VerdictSemanticError):
        verdict.CriterionObservation(
            criterion_id="c_x",
            applicable_count=0,
            pass_count=0,
            fail_count=0,
            undetermined_count=0,
            verdict_state="PASS",
        )


def test_na_with_fail_count_rejected():
    """T4 위조 재현: verdict_state=NA 인데 fail_count=9."""
    with pytest.raises(verdict.VerdictSemanticError):
        verdict.CriterionObservation(
            criterion_id="c_x",
            applicable_count=9,
            pass_count=0,
            fail_count=9,
            undetermined_count=0,
            verdict_state="NA",
        )


def test_undetermined_to_pass_laundering_rejected():
    """SSOT 02 §14 가 명시한 실패주입: UNDETERMINED->PASS 시도. applicable_count
    가 pass+fail+undetermined 항등식은 맞아도(6=1+0+5) verdict_state 를 손으로
    PASS 라고 우기면 구성 시점에 막혀야 한다."""
    with pytest.raises(verdict.VerdictSemanticError):
        verdict.CriterionObservation(
            criterion_id="c_1_2_1",
            applicable_count=6,
            pass_count=1,
            fail_count=0,
            undetermined_count=5,
            verdict_state="PASS",
        )


def test_identity_violation_rejected():
    with pytest.raises(verdict.VerdictSemanticError):
        verdict.CriterionObservation(
            criterion_id="c_x",
            applicable_count=5,
            pass_count=1,
            fail_count=1,
            undetermined_count=1,  # 1+1+1=3 != 5
            verdict_state="FAIL",
        )


def test_fail_dominates_partial_undetermined():
    obs = verdict.make_criterion_observation(
        "c_y", pass_count=1, fail_count=1, undetermined_count=4
    )
    assert obs.verdict_state == "FAIL"


# ---------------------------------------------------------------------------
# domain_scope.py — 닫는 결함: scope-relation-suffix-truncation (HIGH)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "cert,final,expected",
    [
        # refcohort 실측 오판 사례 — last-2-label 비교는 이걸 MOBILE_SUBDOMAIN_REDIRECT 로 냈다
        ("https://www.abc.co.kr/", "https://m.xyz.co.kr/", "EXTERNAL_PARTNER_DOMAIN"),
        ("https://www.seoul.go.kr/", "https://www.busan.go.kr/", "EXTERNAL_PARTNER_DOMAIN"),
        (
            "https://www.kwacc.or.kr/",
            "https://www.totally-unrelated.or.kr/",
            "EXTERNAL_PARTNER_DOMAIN",
        ),
        # r1 실측 오판 2건과 동형
        ("https://rcda.or.kr/", "https://www.rcs.or.kr/", "EXTERNAL_PARTNER_DOMAIN"),
        # 진짜 같은 서비스의 모바일 서브도메인 리다이렉트는 여전히 옳게 판정돼야 한다
        ("https://www.example.co.kr/", "https://m.example.co.kr/", "MOBILE_SUBDOMAIN_REDIRECT"),
        ("https://example.com/", "https://m.example.com/", "MOBILE_SUBDOMAIN_REDIRECT"),
    ],
)
def test_scope_relation_registered_domain_boundary(cert, final, expected):
    assert domain_scope.scope_relation(cert, final) == expected


def test_external_partner_and_unresolved_excluded_from_aggregation():
    assert domain_scope.is_in_scope_for_aggregation("EXTERNAL_PARTNER_DOMAIN") is False
    assert domain_scope.is_in_scope_for_aggregation("UNRESOLVED") is False
    assert domain_scope.is_in_scope_for_aggregation("EXACT_URL") is True


# ---------------------------------------------------------------------------
# gate.py — 닫는 결함: gate-detection-false-negative (MEDIUM)
# ---------------------------------------------------------------------------


def test_login_title_without_password_input_still_detected():
    """refcohort 미탐 재현: /MobileWeb/Login 리다이렉트 페이지에 password input
    이 없어도(예: 아이디만 먼저 받는 2단계 로그인) 제목이 '로그인'이면 잡아야 한다."""
    ev = gate.GateEvidence(
        final_url_path="/MobileWeb/Login",
        page_title="로그인",
        has_password_input=False,
        landmark_text="",
    )
    sig = gate.detect_gate(ev)
    assert sig.tag == "LOGIN_REQUIRED"
    assert sig.fired_signals  # 근거가 남아야 한다 (감사 가능성)


def test_footer_payment_keyword_does_not_false_positive():
    """refcohort 오탐 재현: 푸터의 '결제 안내' 텍스트만으로 PAYMENT_REQUIRED 가
    됐었다. 여기서는 landmark_text 에 그 문구가 없으면(footer는 landmark 가
    아니므로 애초에 안 들어온다) 오탐하지 않는다."""
    ev = gate.GateEvidence(
        final_url_path="/",
        page_title="다음메일",
        has_password_input=False,
        landmark_text="받은편지함 보낸편지함",  # footer '결제 안내' 는 여기 없음
    )
    sig = gate.detect_gate(ev)
    assert sig.tag == "NONE"


def test_payment_text_in_landmark_is_detected():
    ev = gate.GateEvidence(
        final_url_path="/checkout",
        page_title="주문서 작성",
        landmark_text="결제하기 버튼을 눌러주세요",
    )
    sig = gate.detect_gate(ev)
    assert sig.tag == "PAYMENT_REQUIRED"


def test_http_401_403_is_login_gate():
    ev = gate.GateEvidence(final_url_path="/", page_title="", http_status=401)
    assert gate.detect_gate(ev).tag == "LOGIN_REQUIRED"


# ---------------------------------------------------------------------------
# dedup.py — 닫는 결함: duplicate-endpoints-double-counted (HIGH)
# ---------------------------------------------------------------------------


def test_duplicate_endpoint_detected_across_certification_numbers():
    """refcohort 실측 재현: LG Content Store(모바일웹)/LG Content Store 가
    인증번호만 다르고 둘 다 kr.lgappstv.com/main 를 가리켜 이중 계상됐다."""
    records = [
        {
            "record_id": "REF:2486",
            "certification_number": "2486",
            "final_url": "https://kr.lgappstv.com/main",
        },
        {
            "record_id": "REF:2485",
            "certification_number": "2485",
            "final_url": "https://kr.lgappstv.com/main/",
        },
    ]
    with pytest.raises(ValueError, match="이중계상"):
        dedup.assert_measured_records_unique(records)


def test_distinct_endpoints_pass():
    records = [
        {"record_id": "A", "final_url": "https://a.example.com/x"},
        {"record_id": "B", "final_url": "https://b.example.com/y"},
    ]
    dedup.assert_measured_records_unique(records)  # 예외 없이 통과해야 한다


def test_dedup_endpoints_groups_and_warns_on_url_drift():
    endpoints, warnings = dedup.dedup_endpoints(
        [
            {"record_id": "A", "dom_sha256": "deadbeef", "final_url": "https://a.example.com/x"},
            {"record_id": "B", "dom_sha256": "deadbeef", "final_url": "https://a.example.com/y"},
        ]
    )
    assert len(endpoints) == 1
    assert set(endpoints[0].member_ids) == {"A", "B"}
    assert warnings  # url 드리프트 경고가 남아야 한다
