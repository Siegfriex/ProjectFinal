"""P-B — `url_evidence.py` dim_web_target 머티리얼라이제이션. grain 불일치 처리를 검증한다."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
RESEARCH = REPO / "research" / "landing_accessibility"
sys.path.insert(0, str(RESEARCH / "src"))

from landing_accessibility.target_grouping import FalsifierVerdict  # noqa: E402
from landing_accessibility.url_evidence import (  # noqa: E402
    EntityUrlInput,
    UrlEvidenceError,
    materialize_group,
    materialize_singleton,
)
from landing_accessibility.web_eligibility import (  # noqa: E402
    UrlEvidenceItem,
    determine_web_eligibility,
)

NOW = "2026-08-27T00:00:00+00:00"


def _eligible(entity_id: str, url: str) -> EntityUrlInput:
    det = determine_web_eligibility(
        status="ELIGIBLE_WEB",
        basis="테스트 픽스처",
        evidence=[
            UrlEvidenceItem("HTTP_PROBE", "200", NOW),
            UrlEvidenceItem("SOURCE_LABEL_MATCH", "일치", NOW),
        ],
        confidence=0.9,
        reviewer="tester",
    )
    return EntityUrlInput(
        measurement_entity_id=entity_id,
        determination=det,
        official_landing_url=url,
        final_url=url,
        registered_domain=url.split("//")[1].split("/")[0],
        url_confidence=0.9,
    )


def _undetermined(entity_id: str) -> EntityUrlInput:
    det = determine_web_eligibility(
        status="UNDETERMINED_URL_EVIDENCE",
        basis="접속 실패",
        evidence=[UrlEvidenceItem("HTTP_PROBE", "timeout", NOW)],
        confidence=0.2,
        reviewer="tester",
    )
    return EntityUrlInput(measurement_entity_id=entity_id, determination=det)


# ── singleton (member_count=1, 현재 65/68) ──────────────────────────────────


def test_singleton_eligible_becomes_frozen_with_stable_id() -> None:
    entity = _eligible("svc_a", "https://a.example.com")
    row1 = materialize_singleton(entity)
    row2 = materialize_singleton(entity)
    assert row1.web_target_status == "FROZEN"
    assert row1.web_target_id is not None
    assert row1.web_target_id == row2.web_target_id  # 결정적 — 재실행해도 같은 id


def test_singleton_undetermined_stays_pending_without_id() -> None:
    row = materialize_singleton(_undetermined("svc_b"))
    assert row.web_target_status == "PENDING_URL_REVIEW"
    assert row.web_target_id is None


def test_frozen_row_without_web_target_id_is_rejected() -> None:
    """구조 가드: FROZEN 인데 web_target_id 가 없는 행은 허용되지 않는다 (00 §15)."""
    from landing_accessibility.url_evidence import DimWebTargetRow

    with pytest.raises(UrlEvidenceError):
        DimWebTargetRow(
            web_target_id=None,
            measurement_entity_id="x",
            web_eligibility_status="ELIGIBLE_WEB",
            official_landing_url="https://x.com",
            final_url="https://x.com",
            registered_domain="x.com",
            url_evidence=(),
            url_confidence=0.9,
            web_target_status="FROZEN",
        )


# ── group (member_count>=2, coupang/gmarket/naver 시나리오) ─────────────────


def test_group_pending_verdict_keeps_members_unfrozen() -> None:
    verdict = FalsifierVerdict(
        grouping_status="CANDIDATE_PENDING_URL_REVIEW",
        reason="미확정",
        member_registered_domains={"a": None, "b": None},
    )
    rows = materialize_group(
        [_undetermined("a"), _undetermined("b")], verdict, web_target_group_id="wtg_x"
    )
    assert all(r.web_target_status == "PENDING_URL_REVIEW" for r in rows)
    assert all(r.web_target_id is None for r in rows)


def test_group_split_gives_independent_ids() -> None:
    """gmarket 시나리오 — SPLIT 되면 구성원마다 독립 web_target_id."""
    verdict = FalsifierVerdict(
        grouping_status="SPLIT",
        reason="등록도메인 다름",
        member_registered_domains={
            "gmarket_app": "gmarket.co.kr",
            "gmarket_auction": "auction.co.kr",
        },
    )
    entities = [
        _eligible("gmarket_app", "https://www.gmarket.co.kr"),
        _eligible("gmarket_auction", "https://www.auction.co.kr"),
    ]
    rows = materialize_group(entities, verdict, web_target_group_id="wtg_gmarket")
    ids = {r.measurement_entity_id: r.web_target_id for r in rows}
    assert ids["gmarket_app"] != ids["gmarket_auction"]
    assert all(v is not None for v in ids.values())


def test_group_confirmed_shared_target_gives_one_id() -> None:
    """coupang 시나리오 — CONFIRMED 되면 구성원 전원이 같은 web_target_id 를 공유."""
    verdict = FalsifierVerdict(
        grouping_status="CONFIRMED_SHARED_TARGET",
        reason="등록도메인 동일",
        member_registered_domains={"coupang_app": "coupang.com", "coupang_retail": "coupang.com"},
    )
    entities = [
        _eligible("coupang_app", "https://www.coupang.com/a"),
        _eligible("coupang_retail", "https://www.coupang.com/b"),
    ]
    rows = materialize_group(entities, verdict, web_target_group_id="wtg_coupang")
    ids = {r.web_target_id for r in rows}
    assert len(ids) == 1
    assert all(r.web_target_status == "FROZEN" for r in rows)


def test_confirmed_shared_target_rejects_non_eligible_member() -> None:
    """구조 가드 — CONFIRMED_SHARED_TARGET 인데 한 구성원이라도 ELIGIBLE_WEB 이 아니면 거부."""
    verdict = FalsifierVerdict(
        grouping_status="CONFIRMED_SHARED_TARGET",
        reason="x",
        member_registered_domains={"a": "x.com", "b": "x.com"},
    )
    entities = [_eligible("a", "https://x.com"), _undetermined("b")]
    with pytest.raises(UrlEvidenceError):
        materialize_group(entities, verdict, web_target_group_id="wtg_y")


def test_materialize_group_requires_at_least_two_members() -> None:
    verdict = FalsifierVerdict(
        grouping_status="SPLIT", reason="x", member_registered_domains={"a": "x.com"}
    )
    with pytest.raises(UrlEvidenceError):
        materialize_group([_eligible("a", "https://x.com")], verdict, web_target_group_id="wtg_z")
