"""P-B `dim_certification` join 인프라 — join 만 만든다. 접근성 verdict 는 만들지 않는다.

## 이 모듈이 하지 않는 것

`research/landing_accessibility/CLAUDE.md` Reuse 절과 `docs/v2/00_SSOT_v2.0.md` §4 Axis C:

> WA 품질인증은 고령 사용자의 실제 성공 여부를 나타내는 gold label이 아니다.
> 다만 공인된 접근성 참조라벨로 사용한다.

이 모듈은 `certified_current` 를 계산할 **입력**(join)만 만든다. 그 값을 KWCAG 판정이나
접근성 결론으로 전환하지 않으며, 어떤 target/task 선택에도 이 join 결과를 근거로 쓰지
않는다 (오케스트레이터 지시서 "REAL TARGET 방화벽": eligibility 가 먼저, 인증/접근성
결과가 target 선택에 개입하면 순서가 거꾸로다).

## 정본

- `docs/v2/01_DATA_SPEC_v2.0.md` §8 `dim_certification`
- `docs/v2/00_SSOT_v2.0.md` §4 Axis C
- 인증 레지스트리 스냅샷: `sources/certification/certification_registry.csv`
  (`KWACC_WA_20260826`, COMPLETE, 227 VALID / 226 valid_at_audit — 1건은 유효기간이
  감사일 다음날 시작해 `cert_valid_candidate=0`. `control/state.json` `registry_source_defects`
  참고)

## join 키

인증 목록의 `certified_target_url_listed` 는 자유 형식 href 다(스킴 결여 26건, URL 대신
텍스트 3건, 결측 4건 — `control/state.json` `registry_source_defects` 실측). 문자열
동일 비교는 `https://naver.com` 과 `http://www.naver.com/`을 다른 값으로 본다.
그래서 join 키는 원문 문자열이 아니라 **PSL 등록도메인**이다(`registered_domain.py`,
`same_registered_domain()` — "모르는 것을 같다고 하지 않는다").
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date

from landing_accessibility.registered_domain import (
    RegisteredDomainError,
    registered_domain,
)

# ── 01 §8 dim_certification 정본 필드 + join 보조 필드 ──────────────────────

TARGET_SCOPE_MATCH: frozenset[str] = frozenset(
    {"EXACT_DOMAIN", "SUBDOMAIN_OF_CERT", "CERT_IS_SUBDOMAIN_OF_TARGET", "NO_MATCH"}
)
SERVICE_IDENTITY_MATCH: frozenset[str] = frozenset(
    {"NAME_EXACT", "NAME_CONTAINS", "NAME_MISMATCH", "NEEDS_REVIEW"}
)
MATCH_BASIS: frozenset[str] = frozenset(
    {"REGISTERED_DOMAIN_EXACT", "REGISTERED_DOMAIN_SUBDOMAIN", "NO_CANDIDATE"}
)


class CertificationJoinError(ValueError):
    pass


def _href_looks_like_url(value: str | None) -> bool:
    """`registry_source_defects` `href-is-text-not-url`(3건) 을 걸러낸다.

    "보건복지부 홈페이지" 같은 텍스트가 URL 자리에 들어간 3건, `-` 1건이 실재 확인됐다.
    스킴 결여 href(26건)는 텍스트가 아니라 URL 이므로 통과시킨다 — `registered_domain()`
    이 스킴 없는 호스트도 처리한다.
    """
    if not value or not value.strip() or value.strip() == "-":
        return False
    # 한글이 포함되면 href 가 아니라 안내 문구다.
    return not re.search(r"[가-힣]", value)


def _safe_registered_domain(url_or_host: str | None) -> str | None:
    if not url_or_host or not _href_looks_like_url(url_or_host):
        return None
    try:
        return registered_domain(url_or_host)
    except RegisteredDomainError:
        return None


@dataclass(frozen=True)
class CertificationCandidate:
    """레지스트리 한 행이 web target 등록도메인과 매칭된 결과."""

    certification_number: str
    service_name: str
    certified_target_url_listed: str | None
    certified_target_registered_domain: str | None
    cert_start_date: str | None
    cert_end_date: str | None
    cert_valid_candidate: int
    target_scope_match: str
    match_basis: str


def find_certification_candidates(
    web_target_registered_domain: str,
    certification_rows: list[dict[str, object]],
) -> list[CertificationCandidate]:
    """등록도메인이 일치하는 레지스트리 행을 전부 찾는다 (0건·다건 모두 가능).

    `EXACT_DOMAIN` 만 판정한다 — 서브도메인 포함관계(SUBDOMAIN_OF_CERT 등)는 이 join
    함수가 아니라 `classify_scope_match()` 가 두 원문 URL 을 직접 비교해 판정한다.
    등록도메인이 다르면 서브도메인 관계도 성립하지 않으므로, 이 필터가 후보 축소의
    1차 관문이다.
    """
    if not web_target_registered_domain:
        raise CertificationJoinError("web_target_registered_domain 이 비어 있다")

    out: list[CertificationCandidate] = []
    for row in certification_rows:
        listed = row.get("certified_target_url_listed")
        cert_rd = _safe_registered_domain(listed if isinstance(listed, str) else None)
        if not cert_rd or cert_rd != web_target_registered_domain:
            continue
        out.append(
            CertificationCandidate(
                certification_number=str(row.get("certification_number")),
                service_name=str(row.get("service_name") or ""),
                certified_target_url_listed=listed if isinstance(listed, str) else None,
                certified_target_registered_domain=cert_rd,
                cert_start_date=row.get("cert_start_date"),  # type: ignore[arg-type]
                cert_end_date=row.get("cert_end_date"),  # type: ignore[arg-type]
                cert_valid_candidate=int(row.get("cert_valid_candidate") or 0),  # type: ignore[call-overload]
                target_scope_match="EXACT_DOMAIN",
                match_basis="REGISTERED_DOMAIN_EXACT",
            )
        )
    return out


# ── service_identity_match — 결정적 문자열 판정만. 모호하면 NEEDS_REVIEW ──────


def _normalize_name(name: str) -> str:
    """비교용 정규화. 공백·괄호·법인 접미사를 지운다. **표시용이 아니다.**"""
    text = re.sub(r"[()\[\]{}]", " ", name)
    text = re.sub(r"\s+", "", text)
    for suffix in (
        "주식회사",
        "㈜",
        "(주)",
        "코퍼레이션",
        "corp",
        "corporation",
        "inc",
        "co",
        "ltd",
    ):
        text = re.sub(re.escape(suffix), "", text, flags=re.IGNORECASE)
    return text.strip().lower()


def classify_service_identity(
    web_target_service_name: str,
    certification_service_name: str,
) -> str:
    """결정적 이름 비교만 한다. AI/VLM 을 호출하지 않는다 (`00 §10` cascade 1단계).

    완전/포함 일치가 아니면 `NEEDS_REVIEW` 다 — 이 함수는 `NAME_MISMATCH` 를 확정적으로
    선언하지 않는다. 같은 서비스가 인증 목록에는 법인명으로, 원문에는 브랜드명으로
    등재된 사례가 실재하므로(예: 발행처 원문 = "국립망향의동산", 인증 목록 기관명 =
    "망향의동산관리원") 결정적 일치 실패를 자동으로 '다른 서비스'로 단정하면 위양성이
    아니라 위음성(실제 인증을 놓침)이 생긴다.
    """
    a = _normalize_name(web_target_service_name)
    b = _normalize_name(certification_service_name)
    if not a or not b:
        return "NEEDS_REVIEW"
    if a == b:
        return "NAME_EXACT"
    if a in b or b in a:
        return "NAME_CONTAINS"
    return "NEEDS_REVIEW"


# ── 유효기간 판정 — 레지스트리가 이미 계산한 값을 재사용, 재계산하지 않는다 ──


def certified_current(
    *,
    target_scope_match: str,
    service_identity_match: str,
    cert_valid_candidate: int,
) -> int:
    """01 §8: `certified_current = 1` 은 유효기간 + 대상범위 + 서비스 동일성이 모두 맞아야 한다.

    `cert_valid_candidate` 는 `sources/landing_accessibility/registry.py`
    `annotate_validity()` 가 감사일 기준으로 이미 계산해 둔 값을 그대로 쓴다 — 유효기간
    판정을 여기서 다시 하지 않는다(레지스트리와 이 모듈이 서로 다른 감사일을 쓰면
    두 계산이 어긋날 수 있으므로 단일 원천을 유지한다). `registry_source_defects`
    `valid-flag-but-outside-audit-window`(인증번호 2521)가 바로 이 분리가 필요한 이유다 —
    목록 상태 `VALID` 플래그만 보면 이 1건을 놓친다.
    """
    if target_scope_match not in TARGET_SCOPE_MATCH:
        raise CertificationJoinError(f"target_scope_match={target_scope_match!r} 미허용값")
    if service_identity_match not in SERVICE_IDENTITY_MATCH:
        raise CertificationJoinError(f"service_identity_match={service_identity_match!r} 미허용값")
    if cert_valid_candidate not in (0, 1):
        raise CertificationJoinError(
            f"cert_valid_candidate={cert_valid_candidate!r} 은 0/1 이 아니다"
        )

    scope_ok = target_scope_match in {"EXACT_DOMAIN", "SUBDOMAIN_OF_CERT"}
    identity_ok = service_identity_match in {"NAME_EXACT", "NAME_CONTAINS"}
    return int(scope_ok and identity_ok and cert_valid_candidate == 1)


@dataclass(frozen=True)
class CertificationJoinResult:
    """`dim_certification` 한 행 (01 §8 정본 필드 그대로)."""

    web_target_id: str
    certified_current: int
    certification_number: str | None
    cert_start: str | None
    cert_end: str | None
    target_scope_match: str
    service_identity_match: str
    match_basis: str


def build_dim_certification_row(
    *,
    web_target_id: str,
    web_target_service_name: str,
    web_target_registered_domain: str | None,
    certification_rows: list[dict[str, object]],
) -> CertificationJoinResult:
    """web target 하나에 대해 `dim_certification` 행 하나를 만든다.

    후보가 여러 건이면(같은 등록도메인에 인증이 두 개 이상 등재) **가장 최근 종료일**의
    후보를 쓰고, 나머지는 이 함수가 버리지 않는다 — 호출자가
    `find_certification_candidates()` 전체를 보존해야 재현 가능하다.
    """
    if not web_target_registered_domain:
        return CertificationJoinResult(
            web_target_id=web_target_id,
            certified_current=0,
            certification_number=None,
            cert_start=None,
            cert_end=None,
            target_scope_match="NO_MATCH",
            service_identity_match="NEEDS_REVIEW",
            match_basis="NO_CANDIDATE",
        )

    candidates = find_certification_candidates(web_target_registered_domain, certification_rows)
    if not candidates:
        return CertificationJoinResult(
            web_target_id=web_target_id,
            certified_current=0,
            certification_number=None,
            cert_start=None,
            cert_end=None,
            target_scope_match="NO_MATCH",
            service_identity_match="NEEDS_REVIEW",
            match_basis="NO_CANDIDATE",
        )

    def _sort_key(c: CertificationCandidate) -> str:
        return c.cert_end_date or ""

    best = max(candidates, key=_sort_key)
    identity = classify_service_identity(web_target_service_name, best.service_name)
    current = certified_current(
        target_scope_match=best.target_scope_match,
        service_identity_match=identity,
        cert_valid_candidate=best.cert_valid_candidate,
    )
    return CertificationJoinResult(
        web_target_id=web_target_id,
        certified_current=current,
        certification_number=best.certification_number,
        cert_start=best.cert_start_date,
        cert_end=best.cert_end_date,
        target_scope_match=best.target_scope_match,
        service_identity_match=identity,
        match_basis=best.match_basis,
    )


def audit_window_note(audit_date: date) -> str:
    """`registry_source_defects` `valid-flag-but-outside-audit-window` 재확인 문구.

    join 소비자가 "목록 상태 VALID = 유효" 로 오해하지 않도록 감사일을 명시적으로
    남긴다. 이 함수는 계산을 하지 않는다 — 문서화용 재확인일 뿐이다.
    """
    return (
        f"cert_valid_candidate 는 감사일 {audit_date.isoformat()} 기준으로 registry.py 가 "
        "계산했다. 목록의 certification_status_listed='VALID' 플래그만으로 유효를 "
        "판정하지 않는다 (인증번호 2521 사례 — VALID 인데 시작일이 감사일 다음날)."
    )
