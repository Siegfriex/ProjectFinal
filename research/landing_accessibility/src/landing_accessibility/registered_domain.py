"""등록도메인(registered domain) 판정 — **Public Suffix List 파서로만** 한다 (C013 / 06 §3-3).

## 왜 문자열 비교가 아니라 파서인가

Pilot 은 호스트명의 **마지막 두 라벨**을 붙여 등록도메인이라고 불렀다. 한국 도메인에서
그 규칙은 무너진다.

```
www.gmarket.co.kr   마지막 두 라벨 → "co.kr"     ← 국가 2단계 도메인 전체
www.auction.co.kr   마지막 두 라벨 → "co.kr"     ← 같은 값
→ 서로 무관한 두 사이트가 '같은 등록도메인' 으로 판정된다
```

`.co.kr` / `.or.kr` / `.go.kr` / `.ne.kr` / `.pe.kr` 은 전부 public suffix 이므로 등록도메인은
**세 라벨**(`gmarket.co.kr`)이다. 이 사실은 규칙이 아니라 목록이며, 목록의 정본이 PSL 이다.

## 판본 고정

PSL 은 계속 갱신되는 목록이다. 어느 판본으로 판정했는지 기록하지 않으면 재현되지 않는다.
`psl_provenance()` 가 라이브러리 판본과 **번들된 목록 파일의 sha256** 을 함께 돌려준다.
네트워크에서 목록을 받아오지 않는다 — 패키지에 동봉된 스냅샷만 쓴다.
"""

from __future__ import annotations

import hashlib
from functools import lru_cache
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

import publicsuffixlist
from publicsuffixlist import PublicSuffixList


class RegisteredDomainError(Exception):
    """등록도메인을 판정할 수 없다."""


@lru_cache(maxsize=1)
def _psl() -> PublicSuffixList:
    return PublicSuffixList()


def _library_version() -> str:
    try:
        return version("publicsuffixlist")
    except PackageNotFoundError:  # pragma: no cover - 설치 경로가 없을 때만
        return "unknown"


@lru_cache(maxsize=1)
def psl_provenance() -> dict[str, Any]:
    """판정에 쓴 PSL 판본을 재현 가능한 형태로 돌려준다."""
    data = Path(publicsuffixlist.__file__).parent / "public_suffix_list.dat"
    return {
        "parser": "publicsuffixlist.PublicSuffixList",
        "library_version": _library_version(),
        "list_file": data.name,
        "list_sha256": "sha256:" + hashlib.sha256(data.read_bytes()).hexdigest(),
        "network_fetch": False,
        "rule": "마지막 두 라벨 문자열 비교 금지 — public suffix 목록으로 경계를 찾는다",
    }


def host_of(url: str) -> str:
    """URL 에서 호스트만 뽑는다. 포트·대소문자·후행 점을 정규화한다."""
    host = (urlsplit(url).hostname or "").strip().rstrip(".").lower()
    if not host:
        raise RegisteredDomainError(f"호스트를 뽑을 수 없다: {url!r}")
    return host


def public_suffix(url_or_host: str) -> str | None:
    host = url_or_host if "://" not in url_or_host else host_of(url_or_host)
    return _psl().publicsuffix(host)


def registered_domain(url_or_host: str) -> str | None:
    """등록도메인(= public suffix + 라벨 1개). 판정 불가면 None.

    `co.kr` 처럼 public suffix 자체만 주어지면 등록도메인이 아니므로 None 이다.
    """
    host = url_or_host if "://" not in url_or_host else host_of(url_or_host)
    return _psl().privatesuffix(host)


def same_registered_domain(a: str, b: str) -> bool:
    """두 URL 이 같은 등록도메인인가. 어느 한쪽이 판정 불가면 False 다 (모르는 것을 같다고 하지 않는다)."""
    left = registered_domain(a)
    right = registered_domain(b)
    return bool(left) and left == right
