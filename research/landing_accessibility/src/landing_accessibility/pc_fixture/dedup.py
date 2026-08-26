"""endpoint 단위 canonical 통합 — 인증번호/서비스 id 가 달라도 같은
URL/DOM 이면 하나로 묶는다.

닫는 결함(Pilot 감사 duplicate-endpoints-double-counted, HIGH):
    ``research/refcohort/src/refcohort/targets.py``/``report.py`` 는 같은
    정규화 endpoint 를 인증번호가 다르다는 이유로 두 번 측정해 분모와 FAIL
    수를 이중 계상했다. 실측: dom_sha256 동일 그룹 5개, 정규화 final_url
    동일 그룹 7개(예: LG Content Store 모바일웹/일반 표기 2건이 같은
    ``kr.lgappstv.com/main`` 을 각각 측정, 각각 criteria_fail=7).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from urllib.parse import urlparse, urlunparse


def normalize_url(url: str) -> str:
    p = urlparse(url)
    path = p.path.rstrip("/") or "/"
    return urlunparse((p.scheme.lower(), p.netloc.lower(), path, "", "", ""))


@dataclass
class CanonicalEndpoint:
    canonical_key: str
    member_ids: list[str] = field(default_factory=list)
    certification_numbers: list[str] = field(default_factory=list)
    normalized_url: str | None = None
    dom_sha256: str | None = None


def canonical_key(normalized_url: str | None, dom_sha256: str | None) -> str:
    """dom_sha256 을 url 보다 우선한다 — 렌더된 내용이 완전히 같다는 신호가
    URL 문자열(리다이렉트·쿼리스트링으로 흔들릴 수 있다)보다 더 강한
    동일성 근거이기 때문이다."""
    if dom_sha256:
        return f"dom:{dom_sha256}"
    if normalized_url:
        return f"url:{normalized_url}"
    raise ValueError("canonical key 를 만들 최소 하나(정규화 url 또는 dom hash)가 필요하다")


def dedup_endpoints(records: list[dict]) -> tuple[list[CanonicalEndpoint], list[str]]:
    """records: 각각 ``{'record_id', 'certification_number'?, 'final_url'?, 'dom_sha256'?}``.

    반환: (canonical endpoint 목록, 경고 목록). 경고는 자동으로 병합하지 않고
    표시만 하는 모호한 사례다 (예: 같은 canonical key 인데 정규화 url 이 갈리는 경우).
    """
    by_key: dict[str, CanonicalEndpoint] = {}
    warnings: list[str] = []
    for r in records:
        url = r.get("final_url")
        norm = normalize_url(url) if url else None
        dom = r.get("dom_sha256")
        try:
            key = canonical_key(norm, dom)
        except ValueError:
            warnings.append(f"{r.get('record_id')}: canonical key 없음 (url/dom 둘 다 없음)")
            key = f"unresolved:{r.get('record_id')}"
        ep = by_key.setdefault(
            key, CanonicalEndpoint(canonical_key=key, normalized_url=norm, dom_sha256=dom)
        )
        ep.member_ids.append(str(r.get("record_id")))
        if r.get("certification_number"):
            ep.certification_numbers.append(str(r["certification_number"]))
        if norm and ep.normalized_url and norm != ep.normalized_url:
            warnings.append(
                f"{key}: 같은 canonical key 인데 정규화 url 이 다름 ({ep.normalized_url} vs {norm})"
            )
    return list(by_key.values()), warnings


def assert_measured_records_unique(records: list[dict]) -> None:
    """guard 불변식: MEASURED 레코드의 canonical endpoint 는 코호트 내 유일해야 한다.

    위반 시 예외를 던진다 — 이중계상을 조용히 통과시키지 않는다.
    """
    endpoints, _ = dedup_endpoints(records)
    dupes = [ep for ep in endpoints if len(set(ep.member_ids)) > 1]
    if dupes:
        detail = "; ".join(f"{ep.canonical_key} <- {sorted(set(ep.member_ids))}" for ep in dupes)
        raise ValueError(f"중복 endpoint 이중계상 발견 (guard 위반): {detail}")
