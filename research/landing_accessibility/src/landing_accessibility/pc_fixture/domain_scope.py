"""scope_relation 판정 — 등록 도메인(eTLD+1) 계산을 last-2-label 절단이 아니라
알려진 2단계 접미사 목록 기반으로 한다.

닫는 결함(Pilot 감사 scope-relation-suffix-truncation, HIGH):
    ``research/refcohort/src/refcohort/collect.py:67`` 는
    ``'.'.join(bare_c.split('.')[-2:]) == '.'.join(bare_f.split('.')[-2:])`` 로
    등록 도메인을 비교했다. ``.co.kr``/``.or.kr``/``.go.kr`` 처럼 2단계 국가
    도메인에서는 이 비교가 항상 참이 되어 서로 무관한 사이트를
    ``MOBILE_SUBDOMAIN_REDIRECT`` 로 오판했다. 실측: ``www.seoul.go.kr`` vs
    ``www.busan.go.kr`` 이 같은 서비스로 판정됐고, r1 데이터에서도
    ``rcda.or.kr`` -> ``rcs.or.kr`` 오판 2건이 실재했다.

    반대 방향 결함도 있었다: ``report.py`` 가 ``scope_relation`` 을 한 번도
    참조하지 않아 ``EXTERNAL_PARTNER_DOMAIN``(카카오 로그인, 회사소개 사이트
    등)이 그대로 집계에 들어갔다. 여기서는 ``is_in_scope_for_aggregation`` 을
    별도로 두고, 이 값을 실제로 호출하는 것을 파이프라인/집계 쪽 책임으로
    명시한다.
"""

from __future__ import annotations

from urllib.parse import urlparse

# 완전한 Public Suffix List 대체가 아니다 — refcohort 가 실측으로 확인한
# 실패군(한국 2단계 국가 도메인)을 최소한으로 덮는다. 운영 배치 시
# publicsuffix2 패키지로 registrable_domain() 의 구현만 교체하면 된다.
KR_TWO_LABEL_SUFFIXES = frozenset(
    {
        "co.kr",
        "or.kr",
        "go.kr",
        "ne.kr",
        "re.kr",
        "pe.kr",
        "ac.kr",
        "hs.kr",
        "ms.kr",
        "es.kr",
        "seoul.kr",
        "busan.kr",
    }
)
GENERIC_TWO_LABEL_SUFFIXES = frozenset({"co.uk", "com.au", "co.jp", "com.br"})
KNOWN_TWO_LABEL_SUFFIXES = KR_TWO_LABEL_SUFFIXES | GENERIC_TWO_LABEL_SUFFIXES


def registrable_domain(netloc: str) -> str:
    """netloc 에서 등록 도메인(eTLD+1)을 뽑는다.

    ``a.b.co.kr`` 처럼 마지막 2 label 이 알려진 국가 2단계 접미사면 3 label 을
    등록 도메인으로 본다. 아니면 naive 2 label.
    """
    host = netloc.split(":")[0].lower()
    labels = host.split(".")
    if len(labels) < 2:
        return host
    last_two = ".".join(labels[-2:])
    if last_two in KNOWN_TWO_LABEL_SUFFIXES and len(labels) >= 3:
        return ".".join(labels[-3:])
    return last_two


SCOPE_RELATIONS = frozenset(
    {
        "EXACT_URL",
        "SAME_ORIGIN_PATH",
        "MOBILE_SUBDOMAIN_REDIRECT",
        "EXTERNAL_PARTNER_DOMAIN",
        "UNRESOLVED",
    }
)

# 프로토콜 표2: 이 두 scope 는 원 인증/canonical 대상의 범위를 넘어선 관측이다.
# 참조 분포 집계에서 제외하고 별도 표로만 보고한다.
AGGREGATION_EXCLUDED_SCOPES = frozenset({"EXTERNAL_PARTNER_DOMAIN", "UNRESOLVED"})


def scope_relation(canonical_url: str, final_url: str | None) -> str:
    if not final_url:
        return "UNRESOLVED"
    c, f = urlparse(canonical_url), urlparse(final_url)

    # 이 레인은 로컬 file:// 픽스처만 다룬다 (execution_mode.py). file:// 는
    # netloc 이 항상 비어 있어 아래 일반 규칙(netloc 비교)이 무의미하다 —
    # 여기서는 경로 동일성으로만 판단한다. 이 분기는 FIXTURE 전용이고 실제
    # http(s) 스킴에는 적용되지 않는다.
    if c.scheme == "file" and f.scheme == "file":
        return "EXACT_URL" if c.path.rstrip("/") == f.path.rstrip("/") else "SAME_ORIGIN_PATH"

    if not c.netloc or not f.netloc:
        return "UNRESOLVED"
    if c.scheme == f.scheme and c.netloc == f.netloc and c.path.rstrip("/") == f.path.rstrip("/"):
        return "EXACT_URL"
    if c.netloc == f.netloc:
        return "SAME_ORIGIN_PATH"
    if registrable_domain(c.netloc) == registrable_domain(f.netloc):
        return "MOBILE_SUBDOMAIN_REDIRECT"
    return "EXTERNAL_PARTNER_DOMAIN"


def is_in_scope_for_aggregation(scope: str) -> bool:
    return scope not in AGGREGATION_EXCLUDED_SCOPES
