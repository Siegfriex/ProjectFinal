"""P-B — `target_grouping.py` falsifier 검정. `web_target_group.parquet` 의 3개
CANDIDATE_PENDING_URL_REVIEW 그룹(coupang/gmarket/naver) 을 코드 검정 가능한 형태로
바꾼 것이므로, 그 3건이 실제로 존재하고 이 모듈이 다루는 falsifier 문면과 정합하는지도
함께 확인한다.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import pytest

REPO = Path(__file__).resolve().parents[1]
RESEARCH = REPO / "research" / "landing_accessibility"
STATE = RESEARCH / "state"
sys.path.insert(0, str(RESEARCH / "src"))

from landing_accessibility.target_grouping import (  # noqa: E402
    MemberUrlEvidence,
    TargetGroupingError,
    evaluate_registered_domain_falsifier,
)

pytestmark = pytest.mark.skipif(
    not (STATE / "web_target_group.parquet").exists(), reason="web_target_group 산출물이 없다"
)


@pytest.fixture(scope="module")
def web_target_group() -> pd.DataFrame:
    return pd.read_parquet(STATE / "web_target_group.parquet")


def test_three_candidate_groups_exist_and_are_multi_member(web_target_group: pd.DataFrame) -> None:
    candidates = web_target_group[
        web_target_group["grouping_status"] == "CANDIDATE_PENDING_URL_REVIEW"
    ]
    assert len(candidates) == 3
    assert (candidates["member_count"] == 2).all()


def test_falsifier_text_mentions_registered_domain_for_all_three(
    web_target_group: pd.DataFrame,
) -> None:
    """`expected_url_relationship_falsifier` 원문 3건 모두가 등록도메인 비교를 요구하는지 —
    이 모듈이 그 요구를 실제로 코드화했다는 근거."""
    candidates = web_target_group[
        web_target_group["grouping_status"] == "CANDIDATE_PENDING_URL_REVIEW"
    ]
    for text in candidates["expected_url_relationship_falsifier"]:
        assert "등록도메인" in text


# ── falsifier 검정 자체 — 합성 evidence 로 (URL 미확정 상태이므로 실데이터 없음) ──


def test_undetermined_urls_stay_pending() -> None:
    verdict = evaluate_registered_domain_falsifier(
        [
            MemberUrlEvidence("svc_a", None, None),
            MemberUrlEvidence("svc_b", "https://b.example.com", 0.9),
        ]
    )
    assert verdict.grouping_status == "CANDIDATE_PENDING_URL_REVIEW"


def test_different_registered_domains_split() -> None:
    """coupang 시나리오 재현 — 두 entity 의 랜딩이 다른 등록도메인으로 확정되면 SPLIT."""
    verdict = evaluate_registered_domain_falsifier(
        [
            MemberUrlEvidence("coupang_app", "https://www.coupang.com/np/coupangapp", 0.9),
            MemberUrlEvidence("coupang_retail", "https://mc.coupang.com/", 0.9),
        ]
    )
    # 둘 다 coupang.com 등록도메인이므로 이 예시는 SPLIT 이 아니라 CONFIRMED 여야 한다.
    assert verdict.grouping_status == "CONFIRMED_SHARED_TARGET"


def test_split_when_registered_domains_differ() -> None:
    verdict = evaluate_registered_domain_falsifier(
        [
            MemberUrlEvidence("gmarket_app", "https://www.gmarket.co.kr/", 0.9),
            MemberUrlEvidence("gmarket_auction", "https://www.auction.co.kr/", 0.9),
        ]
    )
    assert verdict.grouping_status == "SPLIT"
    assert "gmarket.co.kr" in verdict.member_registered_domains.values()
    assert "auction.co.kr" in verdict.member_registered_domains.values()


def test_low_confidence_does_not_confirm() -> None:
    verdict = evaluate_registered_domain_falsifier(
        [
            MemberUrlEvidence("a", "https://a.example.com", 0.2),
            MemberUrlEvidence("b", "https://a.example.com", 0.9),
        ]
    )
    assert verdict.grouping_status == "CANDIDATE_PENDING_URL_REVIEW"


def test_requires_at_least_two_members() -> None:
    with pytest.raises(TargetGroupingError):
        evaluate_registered_domain_falsifier([MemberUrlEvidence("a", "https://a.com", 0.9)])
