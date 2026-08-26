"""C003 — canonical service entity / alias map / membership 생성.

입력 (읽기 전용):
    state/source_ranking_rows.parquet   261행 원자료
    state/panel_registry.parquet        17패널

출력:
    state/panel_registry.parquet        (+ axis_type, panel_scope)
    state/service_master.parquet
    state/entity_alias_map.parquet
    state/source_membership.parquet
    state/extraction_corrections.json
    state/*.csv (사람이 읽는 사본)

원칙
    - 원자료 261행은 삭제/병합하지 않는다. entity_name_raw 는 그대로 보존한다.
    - service_id 는 sha256(canonical_service_key) 기반이며 한글을 포함하지 않는다.
    - 원문 표기가 다르면 기본은 별개 entity. 병합은 근거를 남기고 needs_human_review=True.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
STATE = ROOT / "state"

# --------------------------------------------------------------------------
# 1. 패널 축 유형 / 부분집합 범위 — 원문 이미지 판독 결과
#    fig07_t1 의 표 헤더 컬럼명은 '업종' 이며 아이콘도 브랜드 로고가 아닌 픽토그램이다.
#    나머지 패널의 헤더는 '앱' 또는 '리테일 브랜드' 이므로 SERVICE_BRAND 다.
# --------------------------------------------------------------------------
AXIS_TYPE: dict[str, str] = {"fig07_t1": "INDUSTRY_CATEGORY"}

PANEL_SCOPE: dict[str, str] = {
    # 부분집합 패널 — 원문 제목이 명시한 선별 조건 (전수 순위표가 아님)
    "fig04_t1": "SUBSET: 액티브시니어+ 세대 앱 사용자 비율이 높은 '주요 금융 앱' 5개 (선별 기준 미공개)",
    "fig04_t2": "SUBSET: 액티브시니어+ 세대 앱 사용자 비율이 높은 '주요 금융 앱' 5개 (선별 기준 미공개)",
    "fig05_t1": "SUBSET: 액티브시니어+ 세대 앱 사용자가 많이 성장한 '주요 쇼핑 앱' 3개 (선별 기준 미공개)",
    "fig05_t2": "SUBSET: 액티브시니어+ 세대 앱 사용자가 많이 성장한 '주요 쇼핑 앱' 3개 (선별 기준 미공개)",
    "fig10_t1": "SUBSET: 순 결제추정금액 비율이 높은 '주요 홈쇼핑 리테일 브랜드' 5개 (홈쇼핑 업종 한정)",
    "fig10_t2": "SUBSET: 순 결제추정금액 비율이 높은 '주요 홈쇼핑 리테일 브랜드' 5개 (홈쇼핑 업종 한정)",
    "fig11_t1": "SUBSET: 순 결제추정금액이 많이 성장한 '주요 오프라인 마트 리테일 브랜드' 3개 (오프라인 마트 업종 한정)",
    "fig11_t2": "SUBSET: 순 결제추정금액이 많이 성장한 '주요 오프라인 마트 리테일 브랜드' 3개 (오프라인 마트 업종 한정)",
    # 임계값 필터가 걸린 전수 순위 패널
    "fig02_t1": "THRESHOLD: 25년 하반기 액티브시니어+ 세대 월간 사용자 평균 200만 명 이상인 앱",
    "fig03_t1": "THRESHOLD: 월간 사용자 평균 200만 명 이상 + 액티브시니어+ 세대 비율 25% 이상인 앱",
    "fig08_t1": "THRESHOLD: 25년 하반기 액티브시니어+ 세대 순 결제추정금액 합 5천억 원 이상인 리테일 브랜드",
    "fig09_t1": "THRESHOLD: 순 결제추정금액 합 5천억 원 이상 + 액티브시니어+ 세대 비율 30% 이상인 리테일 브랜드",
    "fig07_t1": "AGGREGATE: 24~25년 12월 월간 순 결제추정금액 50억 원 초과 브랜드를 업종으로 집계 (브랜드 축 아님)",
    "fig01_t1": "FULL: 액티브시니어+ 세대 앱 사용자 평균 TOP15 (별도 선별 조건 없음)",
    "fig01_t2": "FULL: 액티브시니어+ 세대 앱 사용시간 평균 TOP15 (별도 선별 조건 없음)",
    "fig06_t1": "FULL: 액티브시니어+ 세대 순 결제추정금액 합 인덱스 TOP15 (별도 선별 조건 없음)",
    "fig06_t2": "FULL: 액티브시니어+ 세대 총 결제횟수 평균 TOP15 (별도 선별 조건 없음)",
}

# --------------------------------------------------------------------------
# 2. canonical_service_key — 안정적 로마자 슬러그. 한글을 쓰지 않는다.
#    key -> (canonical_service_key, entity_kind, canonicalization_basis, needs_human_review)
#    dict 의 키는 entity_name_raw 원문 그대로다.
# --------------------------------------------------------------------------
SOLO = "원문 표기 1종만 존재 — 별칭 병합 없이 1:1 대응."
SLASH = (
    "원문이 한 셀에 슬래시로 묶어 표기한 단일 측정 단위 — 분해하지 않고 그대로 1개 entity 로 둔다."
)
INDUSTRY = "fig07_t1 의 축은 표 헤더가 '업종' 인 업종 카테고리다. 브랜드가 아니므로 웹 수집 대상에서 제외한다."

# (canonical_key, kind, basis, needs_review)
ENTITY_SPEC: dict[str, tuple[str, str, str, bool]] = {
    # ---- APP ----
    "11번가": ("11st", "APP", SOLO, False),
    "Chrome": ("chrome", "APP", SOLO, False),
    "Google": ("google", "APP", SOLO, False),
    "Google 포토": ("google_photos", "APP", SOLO, False),
    "G마켓": (
        "gmarket_app",
        "APP",
        "APP 도메인 원문은 'G마켓', RETAIL 도메인 원문은 'G마켓/옥션' 으로 표기가 다르다. "
        "측정 대상(앱 사용자 vs 옥션 합산 결제)이 달라 별개 entity 로 둔다.",
        True,
    ),
    "Instagram": ("instagram", "APP", SOLO, False),
    "KB Pay": ("kb_pay", "APP", SOLO, False),
    "KB스타뱅킹": ("kb_starbanking", "APP", SOLO, False),
    "NH스마트뱅킹": ("nh_smart_banking", "APP", SOLO, False),
    "NH콕뱅크": ("nh_cok_bank", "APP", SOLO, False),
    "Netflix": ("netflix", "APP", SOLO, False),
    "TikTok": ("tiktok", "APP", SOLO, False),
    "TikTok Lite": (
        "tiktok_lite",
        "APP",
        "원문이 'TikTok' 과 'TikTok Lite' 를 별도 행으로 올렸다(fig01_t2 동시 등장). 별개 앱이다.",
        False,
    ),
    "V3 Mobile Plus": ("v3_mobile_plus", "APP", SOLO, False),
    "YouTube": ("youtube", "APP", SOLO, False),
    "내 파일": ("my_files", "APP", SOLO, False),
    "네이버": (
        "naver_app",
        "APP",
        "APP 도메인 원문은 '네이버', RETAIL 도메인 원문은 '네이버/네이버페이' 로 표기가 다르다. "
        "앱 사용자와 네이버페이 결제는 다른 측정 대상이므로 별개 entity 로 둔다.",
        True,
    ),
    "네이버지도": ("naver_map", "APP", SOLO, False),
    "다음": ("daum", "APP", SOLO, False),
    "당근": ("danggeun", "APP", SOLO, False),
    "디바이스 케어": ("device_care", "APP", SOLO, False),
    "모니모": ("monimo", "APP", SOLO, False),
    "밴드": ("band", "APP", SOLO, False),
    "삼성 계산기": ("samsung_calculator", "APP", SOLO, False),
    "삼성 노트": ("samsung_notes", "APP", SOLO, False),
    "삼성 월렛": ("samsung_wallet", "APP", SOLO, False),
    "삼성 인터넷 브라우저": ("samsung_internet_browser", "APP", SOLO, False),
    "삼성카드": ("samsung_card", "APP", SOLO, False),
    "신한 SOL뱅크": ("shinhan_sol_bank", "APP", SOLO, False),
    "에이닷 전화": ("adot_call", "APP", SOLO, False),
    "카카오맵": ("kakaomap", "APP", SOLO, False),
    "카카오톡": ("kakaotalk", "APP", SOLO, False),
    "캐시워크": ("cashwalk", "APP", SOLO, False),
    "토스": ("toss", "APP", SOLO, False),
    "티맵": ("tmap", "APP", SOLO, False),
    "하나은행": (
        "hana_bank",
        "APP",
        "fig04 아이콘은 '1Q 하나원큐' 지만 라벨 텍스트가 '하나은행' 이다. 원문 라벨 표기를 따른다.",
        False,
    ),
    "현대카드": ("hyundai_card", "APP", SOLO, False),
    # ---- APP + RETAIL ----
    "쿠팡": (
        "coupang",
        "BOTH",
        "APP(fig01) 과 RETAIL(fig06, fig09) 양쪽에서 원문이 동일하게 '쿠팡' 으로 표기했다. "
        "동일 표기이므로 하나의 entity 로 묶고 membership 으로 두 도메인을 기록한다.",
        False,
    ),
    # ---- RETAIL ----
    "CJ온스타일": ("cj_onstyle", "RETAIL_BRAND", SOLO, False),
    "CU": ("cu", "RETAIL_BRAND", SOLO, False),
    "GS25": ("gs25", "RETAIL_BRAND", SOLO, False),
    "GS홈쇼핑/GS Shop": ("gs_homeshopping_gsshop", "RETAIL_BRAND", SLASH, False),
    "G마켓/옥션": (
        "gmarket_auction",
        "RETAIL_BRAND",
        "슬래시 묶음 표기이자 APP 의 'G마켓' 과 다른 원문 표기. 원문 단위를 측정 단위로 보고 별개 entity 로 둔다.",
        True,
    ),
    "NC백화점/뉴코아아울렛": ("nc_dept_newcore_outlet", "RETAIL_BRAND", SLASH, False),
    "NS홈쇼핑": ("ns_homeshopping", "RETAIL_BRAND", SOLO, False),
    "emart24": (
        "emart24",
        "RETAIL_BRAND",
        "원문이 '이마트'(fig06_t1) 와 'emart24'(fig06_t2) 를 별도 행으로 표기했다. 편의점 브랜드로 별개 entity 다.",
        False,
    ),
    "네이버/네이버페이": (
        "naver_naverpay",
        "RETAIL_BRAND",
        "슬래시 묶음 표기이자 APP 의 '네이버' 와 다른 원문 표기. 결제 기준 측정 단위로 별개 entity 로 둔다.",
        True,
    ),
    "농협하나로마트": ("nonghyup_hanaro_mart", "RETAIL_BRAND", SOLO, False),
    "다이소": ("daiso", "RETAIL_BRAND", SOLO, False),
    "대한항공": ("korean_air", "RETAIL_BRAND", SOLO, False),
    "롯데마트": ("lotte_mart", "RETAIL_BRAND", SOLO, False),
    "롯데백화점": ("lotte_department_store", "RETAIL_BRAND", SOLO, False),
    "롯데하이마트": ("lotte_himart", "RETAIL_BRAND", SOLO, False),
    "롯데홈쇼핑": ("lotte_homeshopping", "RETAIL_BRAND", SOLO, False),
    "마켓컬리": ("market_kurly", "RETAIL_BRAND", SOLO, False),
    "메가커피": ("mega_coffee", "RETAIL_BRAND", SOLO, False),
    "배달의민족": ("baemin", "RETAIL_BRAND", SOLO, False),
    "세븐일레븐": ("seven_eleven", "RETAIL_BRAND", SOLO, False),
    "신세계백화점": ("shinsegae_department_store", "RETAIL_BRAND", SOLO, False),
    "이마트": ("emart", "RETAIL_BRAND", SOLO, False),
    "카카오T": ("kakao_t", "RETAIL_BRAND", SOLO, False),
    "컴포즈커피": ("compose_coffee", "RETAIL_BRAND", SOLO, False),
    "코스트코": ("costco", "RETAIL_BRAND", SOLO, False),
    "쿠팡이츠": (
        "coupang_eats",
        "RETAIL_BRAND",
        "원문이 '쿠팡'(fig06_t1/t2) 과 '쿠팡이츠'(fig06_t2) 를 같은 표에 별도 행으로 올렸다. 별개 측정 대상이다.",
        False,
    ),
    "탑마트": ("top_mart", "RETAIL_BRAND", SOLO, False),
    "파리바게뜨/파리크라상": ("paris_baguette_pariscroissant", "RETAIL_BRAND", SLASH, False),
    "현대백화점": ("hyundai_department_store", "RETAIL_BRAND", SOLO, False),
    "현대홈쇼핑/현대Hmall": (
        "hyundai_homeshopping_hmall",
        "RETAIL_BRAND",
        "fig10_t2 의 '현대홈쇼핑/현대Hmallord' 와 같은 브랜드다. 같은 그림 안의 동일 5개 브랜드 세트이고 "
        "로고 이미지도 동일하며, 발행처 태그 목록에도 '현대홈쇼핑/현대Hmall' 만 실려 있다. "
        "'ord' 는 원문(발행물) 자체의 렌더링 오타로 확인되어 별칭으로 흡수했다.",
        True,
    ),
    "현대홈쇼핑/현대Hmallord": ("hyundai_homeshopping_hmall", "RETAIL_BRAND", "", False),
    "홈앤쇼핑": ("home_and_shopping", "RETAIL_BRAND", SOLO, False),
    "홈플러스": ("homeplus", "RETAIL_BRAND", SOLO, False),
    # ---- INDUSTRY CATEGORY (fig07_t1) ----
    "인터넷 쇼핑": ("industry_internet_shopping", "INDUSTRY_CATEGORY", INDUSTRY, False),
    "오프라인 마트": ("industry_offline_mart", "INDUSTRY_CATEGORY", INDUSTRY, False),
    "백화점/아울렛": ("industry_department_store_outlet", "INDUSTRY_CATEGORY", INDUSTRY, False),
    "홈쇼핑": ("industry_home_shopping", "INDUSTRY_CATEGORY", INDUSTRY, False),
    "여행/교통": ("industry_travel_transport", "INDUSTRY_CATEGORY", INDUSTRY, False),
    "편의점": ("industry_convenience_store", "INDUSTRY_CATEGORY", INDUSTRY, False),
    "전자기기": ("industry_electronics", "INDUSTRY_CATEGORY", INDUSTRY, False),
    "식품": ("industry_food", "INDUSTRY_CATEGORY", INDUSTRY, False),
    "배달": ("industry_delivery", "INDUSTRY_CATEGORY", INDUSTRY, False),
    "식음료": ("industry_food_beverage", "INDUSTRY_CATEGORY", INDUSTRY, False),
}

# 대표 표기: canonical_key -> entity_name_raw (원문 표기 중 하나. 창작 금지)
CANONICAL_DISPLAY: dict[str, str] = {
    "hyundai_homeshopping_hmall": "현대홈쇼핑/현대Hmall",
}

# 별칭이 대표 표기와 다를 때의 match_basis / reviewer_note
ALIAS_OVERRIDE: dict[str, tuple[str, str]] = {
    "현대홈쇼핑/현대Hmallord": (
        "REVIEWED",
        "fig10.png 하단 막대차트 라벨을 4배 확대 판독한 결과 원문이 실제로 "
        "'현대홈쇼핑/현대Hmallord' 로 렌더링돼 있음을 확인했다(판독 오류 아님, 발행물 오타). "
        "원자료 entity_name_raw 는 보정하지 않고 별칭으로만 흡수한다.",
    ),
}

# 웹 수집 대상 제외 사유
NOT_COLLECTABLE = {"INDUSTRY_CATEGORY"}


def sid(canonical_key: str) -> str:
    return "svc_" + hashlib.sha256(canonical_key.encode("utf-8")).hexdigest()[:16]


def aid(raw: str, service_id: str) -> str:
    return "als_" + hashlib.sha256(f"{raw}\x1f{service_id}".encode()).hexdigest()[:16]


def main() -> None:
    rows = pd.read_parquet(STATE / "source_ranking_rows.parquet")
    panels = pd.read_parquet(STATE / "panel_registry.parquet")

    assert len(rows) == 261, f"원자료 행수가 261이 아니다: {len(rows)}"

    # ---------------- panel_registry: axis_type / panel_scope ----------------
    panels["axis_type"] = panels["panel_id"].map(AXIS_TYPE).fillna("SERVICE_BRAND")
    panels["panel_scope"] = panels["panel_id"].map(PANEL_SCOPE)
    missing_scope = panels.loc[panels["panel_scope"].isna(), "panel_id"].tolist()
    assert not missing_scope, f"panel_scope 미지정 패널: {missing_scope}"
    axis_by_panel = dict(zip(panels["panel_id"], panels["axis_type"], strict=True))

    # ---------------- 원자료 커버리지 검사 ----------------
    raw_names = sorted(rows["entity_name_raw"].unique())
    unknown = [n for n in raw_names if n not in ENTITY_SPEC]
    assert not unknown, f"ENTITY_SPEC 에 없는 원문 표기: {unknown}"
    unused = [n for n in ENTITY_SPEC if n not in set(raw_names)]
    assert not unused, f"원자료에 없는 ENTITY_SPEC 항목: {unused}"

    # ---------------- entity_alias_map ----------------
    per_raw = (
        rows.groupby("entity_name_raw")
        .agg(
            domain=("domain", lambda s: "|".join(sorted(set(s)))),
            panel_ids=("panel_id", lambda s: ",".join(sorted(set(s)))),
            n_rows=("source_row_id", "size"),
        )
        .reset_index()
    )

    alias_recs = []
    for r in per_raw.itertuples():
        raw = r.entity_name_raw
        ckey, _kind, _basis, _rev = ENTITY_SPEC[raw]
        service_id = sid(ckey)
        display = CANONICAL_DISPLAY.get(ckey, raw)
        if raw in ALIAS_OVERRIDE:
            basis, note = ALIAS_OVERRIDE[raw]
        elif raw == display:
            basis, note = "EXACT", ""
        else:
            basis, note = "NORMALIZED", ""
        alias_recs.append(
            {
                "alias_id": aid(raw, service_id),
                "service_id": service_id,
                "entity_name_raw": raw,
                "domain": r.domain,
                "panel_ids": r.panel_ids,
                "match_basis": basis,
                "reviewer_note": note,
            }
        )
    alias_map = pd.DataFrame(alias_recs).sort_values(["service_id", "entity_name_raw"])

    # ---------------- service_master ----------------
    raw2ckey = {raw: spec[0] for raw, spec in ENTITY_SPEC.items()}
    rows_ck = rows.assign(canonical_service_key=rows["entity_name_raw"].map(raw2ckey))
    rows_ck["axis_type"] = rows_ck["panel_id"].map(axis_by_panel)

    svc_recs = []
    for ckey, sub in rows_ck.groupby("canonical_service_key"):
        raws = sorted(sub["entity_name_raw"].unique())
        primary = CANONICAL_DISPLAY.get(ckey, raws[0])
        spec_src = next(r for r in raws if ENTITY_SPEC[r][0] == ckey and ENTITY_SPEC[r][2])
        _, kind, basis, needs_review = ENTITY_SPEC[spec_src]
        app_panels = sub.loc[sub["domain"] == "APP", "panel_id"].nunique()
        retail_panels = sub.loc[sub["domain"] == "RETAIL", "panel_id"].nunique()
        svc_recs.append(
            {
                "service_id": sid(ckey),
                "canonical_service_key": ckey,
                "service_name_canonical": primary,
                "entity_kind": kind,
                "appears_in_app_panels": int(app_panels),
                "appears_in_retail_panels": int(retail_panels),
                "source_row_count": len(sub),
                "alias_count": len(raws),
                "canonicalization_basis": basis,
                "needs_human_review": bool(needs_review),
                "web_collectable": kind not in NOT_COLLECTABLE,
            }
        )
    service_master = pd.DataFrame(svc_recs).sort_values(
        ["entity_kind", "canonical_service_key"], ignore_index=True
    )

    # ---------------- source_membership ----------------
    mem = (
        rows_ck.assign(service_id=rows_ck["canonical_service_key"].map(sid))
        .groupby(["service_id", "panel_id", "figure_id", "domain", "axis_type"], as_index=False)
        .agg(rank=("rank", "min"), n_metrics=("metric_name", "nunique"))
        .sort_values(["service_id", "panel_id"], ignore_index=True)
    )

    # ---------------- extraction_corrections.json ----------------
    corrections = {
        "schema": "extraction_corrections/v1",
        "generated_by": "research/landing_accessibility/scripts/build_canonical_entities.py",
        "note": (
            "오케스트레이터가 지목한 판독 의심 2건을 원본 이미지 재판독으로 검증했다. "
            "결론: 원자료(source_ranking_rows.parquet) 값 시정은 0건이며, "
            "1건은 발행물 자체의 오타로 확인되어 원문 보존 + 별칭 흡수, "
            "1건은 판독 오류가 아니라 축 유형 오분류로 panel_registry 스키마 확장으로 처리했다."
        ),
        "corrections": [
            {
                "correction_id": "COR-001",
                "row_id": None,
                "affected_row_ids": [],
                "panel_id": "fig10_t2",
                "field": "entity_name_raw",
                "before": "현대홈쇼핑/현대Hmallord",
                "after": "현대홈쇼핑/현대Hmallord",
                "action": "NO_CHANGE_SOURCE_TYPO_CONFIRMED",
                "evidence": (
                    "sources/wiseapp/images/fig10.png 하단 막대차트 x축 라벨을 4배 확대(LANCZOS) 판독한 결과 "
                    "'현대홈쇼핑/현대Hmallord' 로 실제 렌더링돼 있음. 같은 그림 상단 도넛 패널(fig10_t1)의 대응 "
                    "라벨은 '현대홈쇼핑/현대Hmall' 이고 브랜드 로고 이미지는 두 패널이 동일. 추가로 "
                    "sources/wiseapp/authority_manifest.json 의 발행처 태그 목록에도 '현대홈쇼핑/현대Hmall' 만 존재. "
                    "→ 추출 단계 판독 오류가 아니라 발행물 자체의 오타."
                ),
                "resolution": (
                    "원자료 entity_name_raw 는 원문 그대로 보존한다. canonical 단계에서만 "
                    "service_id=svc_(hyundai_homeshopping_hmall) 로 흡수하고 alias.match_basis='REVIEWED', "
                    "service_master.needs_human_review=True 로 표시한다."
                ),
                "corrected_by": "exec-agent(C003) / 이미지 직접 판독",
            },
            {
                "correction_id": "COR-002",
                "row_id": None,
                "affected_row_ids": [],
                "panel_id": "fig07_t1",
                "field": "panel_registry.axis_type",
                "before": "(컬럼 없음 — 모든 패널이 서비스 축으로 암묵 취급됨)",
                "after": "INDUSTRY_CATEGORY",
                "action": "SCHEMA_FIX_AXIS_TYPE",
                "evidence": (
                    "sources/wiseapp/images/fig07.png 판독: 표 헤더 컬럼명이 '업종' 이고 행 아이콘이 브랜드 로고가 "
                    "아닌 업종 픽토그램이다. 각주도 '리테일 브랜드를 업종별로 분류하여 각 업종별 합을 산출' 이라고 "
                    "명시한다. 10개 행(인터넷 쇼핑·오프라인 마트·백화점/아울렛·홈쇼핑·여행/교통·편의점·전자기기·"
                    "식품·배달·식음료)은 브랜드가 아니라 업종 카테고리다."
                ),
                "resolution": (
                    "panel_registry 에 axis_type 컬럼을 추가해 fig07_t1 만 INDUSTRY_CATEGORY, 나머지 16패널은 "
                    "SERVICE_BRAND 로 표시. 해당 10개 entity 는 entity_kind='INDUSTRY_CATEGORY', "
                    "web_collectable=False 로 두어 브랜드 entity 공간과 분리했다."
                ),
                "corrected_by": "exec-agent(C003) / 이미지 직접 판독",
            },
        ],
        "row_value_changes_applied": 0,
        "source_row_count_before": 261,
        "source_row_count_after": len(rows),
    }

    # ---------------- 저장 ----------------
    panels.to_parquet(STATE / "panel_registry.parquet", index=False)
    panels.to_csv(STATE / "panel_registry.csv", index=False, encoding="utf-8-sig")
    for name, df in [
        ("service_master", service_master),
        ("entity_alias_map", alias_map),
        ("source_membership", mem),
    ]:
        df.to_parquet(STATE / f"{name}.parquet", index=False)
        df.to_csv(STATE / f"{name}.csv", index=False, encoding="utf-8-sig")
    (STATE / "extraction_corrections.json").write_text(
        json.dumps(corrections, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    # ---------------- 요약 ----------------
    print(f"source_ranking_rows : {len(rows)} 행 (불변)")
    print(f"panel_registry      : {len(panels)} 패널")
    print(panels["axis_type"].value_counts().to_string())
    print(f"service_master      : {len(service_master)} 서비스")
    print(service_master["entity_kind"].value_counts().to_string())
    print(f"entity_alias_map    : {len(alias_map)} 별칭")
    print(f"source_membership   : {len(mem)} 행")
    nr = service_master[service_master["needs_human_review"]]
    print(f"needs_human_review  : {len(nr)}")
    for r in nr.itertuples():
        print(f"  - {r.service_id} {r.canonical_service_key} ({r.service_name_canonical})")


if __name__ == "__main__":
    main()
