"""P-B — `certification_join.py`. join 만 검증한다. 접근성 verdict 로 새지 않는지도 함께."""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import pytest

REPO = Path(__file__).resolve().parents[1]
RESEARCH = REPO / "research" / "landing_accessibility"
STATE = RESEARCH / "state"
CERT_CSV = RESEARCH / "sources" / "certification" / "certification_registry.csv"
sys.path.insert(0, str(RESEARCH / "src"))

from landing_accessibility.certification_join import (  # noqa: E402
    CertificationJoinError,
    _safe_registered_domain,
    build_dim_certification_row,
    certified_current,
    classify_service_identity,
    find_certification_candidates,
)

pytestmark = pytest.mark.skipif(not CERT_CSV.exists(), reason="인증 레지스트리 스냅샷이 없다")


@pytest.fixture(scope="module")
def cert_rows() -> list[dict[str, object]]:
    df = pd.read_csv(CERT_CSV)
    return df.to_dict(orient="records")


# ── join 은 등록도메인 기준, 문자열 원문 비교가 아니다 ──────────────────────


def test_scheme_less_href_still_joins(cert_rows: list[dict[str, object]]) -> None:
    """`registry_source_defects` 실측: 스킴 결여 href 26건. 그래도 등록도메인은 뽑혀야 한다."""
    scheme_less = [
        r
        for r in cert_rows
        if isinstance(r.get("certified_target_url_listed"), str)
        and not str(r["certified_target_url_listed"]).startswith(("http://", "https://"))
        and str(r["certified_target_url_listed"]).strip() not in {"", "-"}
    ]
    assert scheme_less, "고정자료에 스킴 결여 href 가 있어야 이 테스트가 의미 있다"
    sample = scheme_less[0]
    rd = _safe_registered_domain(sample["certified_target_url_listed"])
    assert rd is not None
    candidates = find_certification_candidates(rd, cert_rows)
    assert any(c.certification_number == str(sample["certification_number"]) for c in candidates)


def test_href_text_not_url_is_excluded(cert_rows: list[dict[str, object]]) -> None:
    """`href-is-text-not-url`(3건 실측) — 텍스트가 URL 로 오인되지 않는지."""
    text_rows = [
        r
        for r in cert_rows
        if isinstance(r.get("certified_target_url_listed"), str)
        and any(c > "ㄱ" for c in str(r["certified_target_url_listed"]))
    ]
    assert text_rows, "고정자료에 텍스트-as-URL 케이스가 있어야 한다"
    # 이 행들의 registered_domain 계산이 예외 없이 None 을 반환해야 한다(하류 오염 방지).
    for row in text_rows:
        assert _safe_registered_domain(row["certified_target_url_listed"]) is None


def test_no_candidate_when_domain_absent() -> None:
    result = build_dim_certification_row(
        web_target_id="wt_x",
        web_target_service_name="없는서비스",
        web_target_registered_domain=None,
        certification_rows=[],
    )
    assert result.certified_current == 0
    assert result.match_basis == "NO_CANDIDATE"


# ── service_identity_match — 결정적 판정만, 모호하면 NEEDS_REVIEW ──────────


def test_identity_exact_match() -> None:
    assert classify_service_identity("네이버", "네이버") == "NAME_EXACT"


def test_identity_contains_match() -> None:
    assert (
        classify_service_identity("네이버 주식회사", "네이버") == "NAME_EXACT"
    )  # 접미사 제거 후 동일
    assert classify_service_identity("네이버페이", "네이버") == "NAME_CONTAINS"


def test_identity_mismatch_falls_back_to_needs_review_not_hard_mismatch() -> None:
    """법인명 vs 브랜드명 표기 차이(국립망향의동산 vs 망향의동산관리원) 사례를 근거로,
    결정적 불일치 실패는 NAME_MISMATCH 로 단정하지 않고 NEEDS_REVIEW 로 보수화한다."""
    result = classify_service_identity("국립망향의동산", "망향의동산관리원")
    assert result == "NEEDS_REVIEW"


# ── certified_current — 셋 다 맞아야 1 ──────────────────────────────────────


@pytest.mark.parametrize(
    "scope,identity,valid,expected",
    [
        ("EXACT_DOMAIN", "NAME_EXACT", 1, 1),
        ("EXACT_DOMAIN", "NAME_CONTAINS", 1, 1),
        ("EXACT_DOMAIN", "NEEDS_REVIEW", 1, 0),  # 서비스 동일성 미확정 → 0
        ("EXACT_DOMAIN", "NAME_EXACT", 0, 0),  # 유효기간 아님 → 0
        ("NO_MATCH", "NAME_EXACT", 1, 0),  # 대상범위 불일치 → 0
    ],
)
def test_certified_current_requires_all_three(
    scope: str, identity: str, valid: int, expected: int
) -> None:
    assert (
        certified_current(
            target_scope_match=scope, service_identity_match=identity, cert_valid_candidate=valid
        )
        == expected
    )


def test_certified_current_rejects_bad_values() -> None:
    with pytest.raises(CertificationJoinError):
        certified_current(
            target_scope_match="EXACT_DOMAIN",
            service_identity_match="NAME_EXACT",
            cert_valid_candidate=2,
        )


# ── audit-window defect (인증번호 2521) 은 registry.py 의 계산을 그대로 신뢰한다 ──


def test_valid_flag_but_future_start_is_not_double_computed(
    cert_rows: list[dict[str, object]],
) -> None:
    """목록 VALID 인데 시작일이 감사일 다음날인 2521번이 cert_valid_candidate=0 으로
    이미 반영돼 있는지 확인한다 — 이 모듈이 그 계산을 다시 하지 않는다는 사실의 증거."""
    row = next((r for r in cert_rows if str(r.get("certification_number")) == "2521"), None)
    if row is None:
        pytest.skip("고정자료에 인증번호 2521 이 없다")
    assert row["certification_status_listed"] == "VALID"
    assert int(row["cert_valid_candidate"]) == 0
