"""P-B — `registered_domain.py` 포팅 검증. `co.kr` 등 다중라벨 public suffix 를 다룬다."""

from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
RESEARCH = REPO / "research" / "landing_accessibility"
sys.path.insert(0, str(RESEARCH / "src"))

from landing_accessibility.registered_domain import (  # noqa: E402
    RegisteredDomainError,
    host_of,
    psl_provenance,
    registered_domain,
    same_registered_domain,
)


def test_co_kr_is_not_a_registered_domain_by_itself() -> None:
    """`co.kr` 자체는 public suffix 이지 등록도메인이 아니다."""
    assert registered_domain("co.kr") is None


def test_gmarket_and_auction_co_kr_are_different_registered_domains() -> None:
    """docstring 이 든 반례 — 마지막 두 라벨 비교였다면 둘 다 'co.kr' 로 같아졌을 것."""
    assert registered_domain("https://www.gmarket.co.kr/") == "gmarket.co.kr"
    assert registered_domain("https://www.auction.co.kr/") == "auction.co.kr"
    assert not same_registered_domain("https://www.gmarket.co.kr/", "https://www.auction.co.kr/")


def test_same_registered_domain_true_for_subdomain_variants() -> None:
    assert same_registered_domain("https://www.naver.com/", "https://map.naver.com/x")


def test_same_registered_domain_false_when_either_side_unresolvable() -> None:
    """모르는 것을 같다고 하지 않는다."""
    assert not same_registered_domain("not a url at all", "https://naver.com")


def test_host_of_strips_port_and_trailing_dot() -> None:
    assert host_of("https://Example.com.:8443/path") == "example.com."[:-1]


def test_host_of_raises_on_empty_host() -> None:
    import pytest

    with pytest.raises(RegisteredDomainError):
        host_of("not-a-url")


def test_psl_provenance_reports_no_network_fetch() -> None:
    prov = psl_provenance()
    assert prov["network_fetch"] is False
    assert prov["list_sha256"].startswith("sha256:")
