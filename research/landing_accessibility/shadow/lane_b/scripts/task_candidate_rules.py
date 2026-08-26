"""LANE B / P-B PREWORK — 대표 task **candidate** 규칙.

status = SHADOW_PREPARATORY · authoritative = false

## 왜 candidate 에서 멈추는가

`A2 §1.9` 규칙 P-1: `FROZEN` 전이는 KWCAG 결과·`certified_current` 를 **읽기 전에** 일어나야 한다.
`PHASE_GATES` 의 `TARGET_TASK_FRAME_FROZEN` Gate 는 P0 이후다.
따라서 여기서 만드는 값은 전부 `mapping_status ∈ {CANDIDATE, AMBIGUOUS_UNRESOLVED, EXCLUDED}` 이며
`FROZEN` 은 **한 건도 만들지 않는다.**

## 입력 금지 목록 (`PHASE_GATES §4.6`)

```
쓰지 않는다   certified_current · 인증 join 결과
쓰지 않는다   접근성 결과 일체 (존재하지도 않는다)
쓴다          service_name_canonical · domain(APP/RETAIL) · LANE A codebook 정의문
```

`assign_candidate()` 시그니처에 인증·접근성 인자가 **아예 없다.** 경계를 문서가 아니라
함수 시그니처로 막는다.

## 판정 근거

`mapping_basis = RULE` — LANE A codebook 의 `business_domain.values[].inclusion` /
`boundary_rules` 를 서비스 정체성에 적용한 규칙 판정이다. embedding·AI review 를 쓰지 않았다.

`archetype` 은 원칙적으로 `business_domain.typical_archetype` 을 따르되,
codebook 이 명시한 비대각 사례(D1·D3 등)에 해당하면 그쪽을 따른다.

## abstain 경로

codebook `BD-5`(중고거래 자기규정) 및 slash-pair entity 는 **자동 확정하지 않는다.**
`AMBIGUOUS_UNRESOLVED` 또는 `human_final_required = 1` 로 둔다.
`HUMAN_FINAL_REVIEW_MAX = 5` 예산을 넘기지 않도록 abstain 은 최소로 유지한다.
"""

from __future__ import annotations

import re
from typing import Any

PORTAL_SEARCH = "PORTAL_SEARCH"
CONTENT_VIDEO = "CONTENT_VIDEO"
NEWS_CONTENT = "NEWS_CONTENT"
SHOPPING_COMMERCE = "SHOPPING_COMMERCE"
MAP_MOBILITY = "MAP_MOBILITY"
FINANCE_PAYMENT = "FINANCE_PAYMENT"
SOCIAL_COMMUNICATION = "SOCIAL_COMMUNICATION"
UTILITY_OTHER = "UTILITY_OTHER"

QUERY = "QUERY"
CONTENT_OPEN = "CONTENT_OPEN"
ITEM_DETAIL = "ITEM_DETAIL"
PLACE_LOOKUP = "PLACE_LOOKUP"
COMMUNICATION_ENTRY = "COMMUNICATION_ENTRY"
FINANCIAL_ACTION_ENTRY = "FINANCIAL_ACTION_ENTRY"
UTILITY_ENTRY = "UTILITY_ENTRY"

TYPICAL = {
    PORTAL_SEARCH: QUERY,
    CONTENT_VIDEO: CONTENT_OPEN,
    NEWS_CONTENT: CONTENT_OPEN,
    SHOPPING_COMMERCE: ITEM_DETAIL,
    MAP_MOBILITY: PLACE_LOOKUP,
    FINANCE_PAYMENT: FINANCIAL_ACTION_ENTRY,
    SOCIAL_COMMUNICATION: COMMUNICATION_ENTRY,
    UTILITY_OTHER: UTILITY_ENTRY,
}

CANDIDATE = "CANDIDATE"
AMBIGUOUS_UNRESOLVED = "AMBIGUOUS_UNRESOLVED"
EXCLUDED = "EXCLUDED"

# (business_domain, archetype_override|None, 근거 토큰, human_final_required)
DOMAIN_TABLE: dict[str, tuple[str, str | None, str, bool]] = {
    # ── APP 38 ──────────────────────────────────────────────────────────────
    "11st": (SHOPPING_COMMERCE, None, "오픈마켓", False),
    "adot_call": (UTILITY_OTHER, None, "단일목적 통화 보조 도구", False),
    "band": (SOCIAL_COMMUNICATION, None, "커뮤니티·게시판", False),
    "cashwalk": (UTILITY_OTHER, None, "걸음수 리워드 적립 도구 (BD 경계규칙 명시)", False),
    "chrome": (PORTAL_SEARCH, None, "범용 검색을 전면에 둔 브라우저 시작면", False),
    "coupang_app": (SHOPPING_COMMERCE, None, "오픈마켓", False),
    "danggeun": (SOCIAL_COMMUNICATION, None, "BD-5 — 자기규정이 지역생활 커뮤니티", True),
    "daum": (PORTAL_SEARCH, None, "종합 포털", False),
    "device_care": (UTILITY_OTHER, None, "기기 관리·보안", False),
    "gmarket_app": (SHOPPING_COMMERCE, None, "오픈마켓", False),
    "google": (PORTAL_SEARCH, None, "범용 검색엔진", False),
    "google_photos": (UTILITY_OTHER, None, "파일·사진 관리", False),
    "hana_bank": (FINANCE_PAYMENT, None, "은행", False),
    "hyundai_card": (FINANCE_PAYMENT, None, "카드사", False),
    "instagram": (SOCIAL_COMMUNICATION, None, "SNS", False),
    "kakaomap": (MAP_MOBILITY, None, "지도", False),
    "kakaotalk": (SOCIAL_COMMUNICATION, None, "메신저", False),
    "kb_pay": (FINANCE_PAYMENT, None, "간편결제", False),
    "kb_starbanking": (FINANCE_PAYMENT, None, "은행", False),
    "monimo": (FINANCE_PAYMENT, None, "통합자산조회", False),
    "my_files": (UTILITY_OTHER, None, "파일 관리", False),
    "naver_app": (PORTAL_SEARCH, None, "종합 포털 (BD-2 관문 정체성 1차)", False),
    "naver_map": (MAP_MOBILITY, None, "지도", False),
    "netflix": (CONTENT_VIDEO, None, "OTT", False),
    "nh_cok_bank": (FINANCE_PAYMENT, None, "은행", False),
    "nh_smart_banking": (FINANCE_PAYMENT, None, "은행", False),
    "samsung_calculator": (UTILITY_OTHER, None, "계산기류 생산성 도구", False),
    "samsung_card": (FINANCE_PAYMENT, None, "카드사", False),
    "samsung_internet_browser": (
        PORTAL_SEARCH,
        None,
        "범용 검색을 전면에 둔 브라우저 시작면",
        False,
    ),
    "samsung_notes": (UTILITY_OTHER, None, "메모 생산성 도구", False),
    "samsung_wallet": (FINANCE_PAYMENT, None, "BD 경계규칙 — 결제수단 관리가 1차", True),
    "shinhan_sol_bank": (FINANCE_PAYMENT, None, "은행", False),
    "tiktok": (CONTENT_VIDEO, None, "숏폼", False),
    "tiktok_lite": (CONTENT_VIDEO, None, "숏폼", False),
    "tmap": (MAP_MOBILITY, None, "내비게이션", False),
    "toss": (FINANCE_PAYMENT, None, "간편결제·송금", False),
    "v3_mobile_plus": (UTILITY_OTHER, None, "보안·백신", False),
    "youtube": (CONTENT_VIDEO, None, "동영상 플랫폼", False),
    # ── RETAIL 33 ───────────────────────────────────────────────────────────
    "baemin": (SHOPPING_COMMERCE, None, "배달 주문", False),
    "cj_onstyle": (SHOPPING_COMMERCE, None, "홈쇼핑", False),
    "compose_coffee": (SHOPPING_COMMERCE, None, "브랜드 자사몰·주문", False),
    "costco": (SHOPPING_COMMERCE, None, "오프라인 점포 브랜드·상품 탐색", False),
    "coupang_eats": (SHOPPING_COMMERCE, None, "배달 주문", False),
    "coupang_retail": (SHOPPING_COMMERCE, None, "오픈마켓", False),
    "cu": (SHOPPING_COMMERCE, None, "편의점 브랜드", False),
    "daiso": (SHOPPING_COMMERCE, None, "오프라인 점포 브랜드", False),
    "emart": (SHOPPING_COMMERCE, None, "종합몰", False),
    "emart24": (SHOPPING_COMMERCE, None, "편의점 브랜드", False),
    "gmarket_auction": (SHOPPING_COMMERCE, None, "오픈마켓 (slash pair)", True),
    "gs25": (SHOPPING_COMMERCE, None, "편의점 브랜드", False),
    "gs_homeshopping_gsshop": (SHOPPING_COMMERCE, None, "홈쇼핑 (slash pair)", False),
    "home_and_shopping": (SHOPPING_COMMERCE, None, "홈쇼핑", False),
    "homeplus": (SHOPPING_COMMERCE, None, "종합몰", False),
    "hyundai_department_store": (SHOPPING_COMMERCE, None, "백화점", False),
    "hyundai_homeshopping_hmall": (SHOPPING_COMMERCE, None, "홈쇼핑 (slash pair)", False),
    "kakao_t": (MAP_MOBILITY, None, "택시·차량 호출 (BD inclusion 명시)", False),
    "korean_air": (SHOPPING_COMMERCE, None, "항공 예약 (BD 경계규칙 명시)", False),
    "lotte_department_store": (SHOPPING_COMMERCE, None, "백화점", False),
    "lotte_himart": (SHOPPING_COMMERCE, None, "전자기기 종합몰", False),
    "lotte_homeshopping": (SHOPPING_COMMERCE, None, "홈쇼핑", False),
    "lotte_mart": (SHOPPING_COMMERCE, None, "종합몰", False),
    "market_kurly": (SHOPPING_COMMERCE, None, "식료품 배송", False),
    "mega_coffee": (SHOPPING_COMMERCE, None, "브랜드 자사몰·주문", False),
    "naver_naverpay": (
        FINANCE_PAYMENT,
        None,
        "BD 경계 — 네이버(포털)와 네이버페이(간편결제)의 slash pair. "
        "RETAIL 패널이 잰 것은 결제이나 measurement entity 가 두 정체성을 합산한다",
        True,
    ),
    "nc_dept_newcore_outlet": (SHOPPING_COMMERCE, None, "백화점·아울렛 (slash pair)", False),
    "nonghyup_hanaro_mart": (SHOPPING_COMMERCE, None, "종합몰", False),
    "ns_homeshopping": (SHOPPING_COMMERCE, None, "홈쇼핑", False),
    "paris_baguette_pariscroissant": (
        SHOPPING_COMMERCE,
        None,
        "브랜드 자사몰·주문 (slash pair)",
        False,
    ),
    "seven_eleven": (SHOPPING_COMMERCE, None, "편의점 브랜드", False),
    "shinsegae_department_store": (SHOPPING_COMMERCE, None, "백화점", False),
    "top_mart": (SHOPPING_COMMERCE, None, "종합몰", False),
}

# archetype 별 대표 기능명 — archetype 코드를 그대로 복사하지 않는다 (codebook 제약)
PRIMARY_FUNCTION = {
    QUERY: "검색어 제출",
    CONTENT_OPEN: "콘텐츠 1건 열기",
    ITEM_DETAIL: "상품 상세 확인",
    PLACE_LOOKUP: "장소 탐색",
    COMMUNICATION_ENTRY: "교환공간 진입",
    FINANCIAL_ACTION_ENTRY: "금융기능 진입면 도달",
    UTILITY_ENTRY: "도구 기능면 진입",
}


def _archetype_block(codebook: dict[str, Any] | None, code: str) -> dict[str, Any] | None:
    if not codebook:
        return None
    for v in codebook["interaction_archetype"]["values"]:
        if v["code"] == code:
            return v
    return None


def assign_candidate(
    *,
    canonical_service_key: str,
    service_name: str,
    domain: str,
    web_target_group_id: str | None,
    web_target_url: str | None,
    eligibility: str,
    codebook: dict[str, Any] | None,
) -> dict[str, Any]:
    """한 entity 의 대표 task candidate 한 행.

    인증·접근성 인자는 **시그니처에 없다** (`PHASE_GATES §4.6`).
    """
    entry = DOMAIN_TABLE.get(canonical_service_key)
    if entry is None:
        return {
            "task_id": f"task_shadow_{canonical_service_key}",
            "canonical_service_key": canonical_service_key,
            "web_target_id": web_target_group_id,
            "business_domain": None,
            "interaction_archetype": None,
            "primary_function_name": None,
            "endpoint_definition": None,
            "endpoint_signal_type": None,
            "region_definition": None,
            "region_signal_type": None,
            "mapping_basis": "RULE",
            "mapping_status": AMBIGUOUS_UNRESOLVED,
            "mapping_ai_review_status": "NOT_REVIEWED",
            "human_final_required": 1,
            "mapping_note": "codebook 규칙표에 대응 항목이 없다.",
        }

    bd, override, basis_token, needs_human = entry
    arch = override or TYPICAL[bd]
    block = _archetype_block(codebook, arch)

    # 적격성이 확정되지 않으면 task 를 확정하지 않는다. 다만 **배제하지도 않는다.**
    if eligibility != "ELIGIBLE_WEB":
        status, note = (
            AMBIGUOUS_UNRESOLVED,
            f"web_eligibility_status = {eligibility} 이므로 대표 task 를 확정할 수 없다. "
            "적격성이 확정되면 재판정한다. 배제가 아니다.",
        )
    elif re.search(r"[/／]", service_name):
        status, note = (
            AMBIGUOUS_UNRESOLVED,
            "measurement entity 가 slash pair 라 대표 task 의 귀속 브랜드가 하나로 정해지지 않는다.",
        )
        needs_human = True
    else:
        status, note = CANDIDATE, f"codebook inclusion '{basis_token}' 에 의한 규칙 판정."

    endpoint_def = endpoint_sig = None
    if block:
        branches = block.get("endpoint_branches") or []
        if branches:
            endpoint_def = branches[0].get("text")
            endpoint_sig = branches[0].get("endpoint_signal_type")
        else:
            endpoint_def = block.get("endpoint_definition")
            endpoint_sig = (block.get("endpoint_signal_type_allowed") or [None])[0]

    # 규칙 P-2 — UTILITY_ENTRY 는 codebook 채택 전까지 CODEBOOK_PENDING 이고 FROZEN 불가.
    region_sig = (block or {}).get("region_signal_type_default", "CODEBOOK_PENDING")

    return {
        "task_id": f"task_shadow_{canonical_service_key}",
        "canonical_service_key": canonical_service_key,
        "service_name_canonical": service_name,
        "panel_domain": domain,
        "web_target_id": web_target_group_id,
        "web_target_url": web_target_url,
        "business_domain": bd,
        "interaction_archetype": arch,
        "primary_function_name": PRIMARY_FUNCTION[arch],
        "endpoint_definition": endpoint_def,
        "endpoint_signal_type": endpoint_sig,
        "region_definition": (block or {}).get("region_definition"),
        "region_signal_type": region_sig,
        "mapping_basis": "RULE",
        "mapping_status": status,
        "mapping_ai_review_status": "NOT_REVIEWED",
        "human_final_required": int(bool(needs_human)),
        "mapping_note": note,
        "freeze_blocked_reason": (
            "TARGET_TASK_FRAME_FROZEN Gate 는 P0 이후다 (PHASE_GATES §4.1 · A2 규칙 P-1). "
            "LANE B 는 candidate 에서 멈춘다."
        ),
    }
