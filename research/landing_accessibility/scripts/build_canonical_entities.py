"""C003/C009 — measurement_entity / web_target 2층 구조 생성.

입력 (읽기 전용):
    state/source_ranking_rows.parquet   261행 원자료 (axis_type 포함)
    state/panel_registry.parquet        17패널

출력:
    state/panel_registry.parquet        (+ panel_scope)
    state/service_master.parquet        measurement_entity 층
    state/entity_alias_map.parquet      (entity_name_raw, domain) -> service_id
    state/source_membership.parquet
    state/web_target_group.parquet      web_target 층 (URL 미확정)
    state/entity_candidates.json        중간산출물 (원문 표기 인벤토리)
    state/extraction_corrections.json
    state/_researcher_priors/system_app_hypothesis.json   **Source Layer 아님 — 연구자 가설**
    state/*.csv (사람이 읽는 사본)

C009 구조 변경 — 측정 단위와 수집 단위를 분리한다
    두 감사관이 반대편에서 같은 결함을 지적했다. 하나는 쿠팡을 entity_kind='BOTH' 로 합친 것의
    부정합을, 다른 하나는 네이버·G마켓 분리가 수집 단위까지 전파돼 2중 수집이 되는 것을 지적했다.
    같은 층에서 두 요구를 동시에 만족시킬 수 없어서 층을 나눈다.

    measurement_entity (이 파일의 service_master)
        원문 패널이 실제로 잰 대상 단위다. APP 지표(사용자·사용시간)와 RETAIL 지표(카드
        결제추정금액)는 서로 다른 것을 재므로, 원문 표기가 같아도 별개다. 쿠팡도 예외가 아니다.
        키는 (entity_name_raw, domain) 이며 entity_kind='BOTH' 는 존재하지 않는다.

    web_target (web_target_group.parquet)
        실제로 방문할 랜딩 URL 단위다. 여러 measurement_entity 가 같은 web_target 을 가리킬 수
        있고, 그 경우 관측은 정확히 1회만 수행한다. 다만 **URL 증거를 아직 하나도 갖고 있지 않다.**
        그래서 그룹은 확정이 아니라 grouping_status='CANDIDATE_PENDING_URL_REVIEW' 로 둔다.

C009 감사 지적 반영
    D1  entity_kind 가 도메인(APP/RETAIL)과 축유형(브랜드/업종)을 혼재시켜
        `== 'RETAIL_BRAND'` 필터가 리테일 1위 쿠팡을 조용히 누락시켰다.
        → domain 과 axis_type 을 별도 컬럼으로 분리한다. entity_kind 는 삭제한다.
    D2  web_collectable 은 게이트 결론을 선점한 명명이었다. True 70건이 URL 증거 없이
        '업종이 아니다' 만으로 찍혔고 그 안에 선탑재 시스템 앱이 섞여 있었다.
        → web_eligibility_status 로 개명하고 기본값을 NOT_ASSESSED 로 되돌린다.
           확정은 INDUSTRY_CATEGORY 의 EXCLUDED_INDUSTRY_AXIS 뿐이다.
    D6  entity_candidates.json 이 고아 산출물이었다. → 이 스크립트의 중간산출물로 편입한다.
    C   source_row_count 를 app_row_count / retail_row_count 로 분리해
        measurement_entity 축에서 도메인 교차 합산이 성립하지 않게 만든다.

C011 감사 지적 반영
    P1-1 web_target_group 의 member_service_ids / member_canonical_keys / member_domains 가
         각각 독립 정렬돼 위치가 어긋났다(naver 그룹에서 naver_app↔RETAIL 로 읽힘).
         → 하나의 정렬 키로 동시에 정렬한다. 세 배열은 이제 위치가 대응한다.
    P1-2 SYSTEM_APP_CANDIDATE 11건은 A1~A4 인용이 0건인 하드코딩 이름 목록이었다.
         → 상태값에서 제거하고 NOT_ASSESSED 로 되돌린다. 선탑재 추정은 Source Layer 밖의
           state/_researcher_priors/system_app_hypothesis.json 으로 분리한다.

실행 순서 (C011/P2-4)
    1) scripts/build_source_rows_from_journal.py   저널 → 261행 + 17패널
    2) scripts/build_canonical_entities.py         (이 파일) 위 산출물 → 2층 구조 + panel_scope
    panel_scope 의 소유자는 이 파일이다. (1)을 단독 실행해도 (1)이 기존 panel_registry 에서
    panel_scope 를 이어받으므로 스키마가 깨지지 않는다.

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

EXPECTED_ROWS = 261

# --------------------------------------------------------------------------
# 1. 패널 부분집합 범위 — 원문 이미지 판독 결과
#    axis_type / period_axis / row_count_verification 은 build_source_rows_from_journal.py 가
#    저널에서 직접 채운다. 여기서는 panel_scope 만 얹는다.
# --------------------------------------------------------------------------
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
# 2. measurement_entity 사양 — 키는 (entity_name_raw, domain) 이다.
#    같은 원문 표기라도 도메인이 다르면 다른 것을 잰 것이므로 별개 entity 다.
#    값: (canonical_service_key, canonicalization_basis, needs_human_review)
#    axis_type 은 원자료에서 유도한다(하드코딩하지 않는다).
# --------------------------------------------------------------------------
SOLO = "원문 표기 1종만 존재 — 별칭 병합 없이 1:1 대응."
SLASH = (
    "원문이 한 셀에 슬래시로 묶어 표기한 단일 측정 단위 — 분해하지 않고 그대로 1개 entity 로 둔다."
)
INDUSTRY = "fig07_t1 의 축은 표 헤더가 '업종' 인 업종 카테고리다. 브랜드가 아니므로 웹 수집 대상에서 제외한다."

ENTITY_SPEC: dict[tuple[str, str], tuple[str, str, bool]] = {
    ("11번가", "APP"): ("11st", SOLO, False),
    ("Chrome", "APP"): ("chrome", SOLO, False),
    ("Google", "APP"): ("google", SOLO, False),
    ("Google 포토", "APP"): ("google_photos", SOLO, False),
    ("G마켓", "APP"): (
        "gmarket_app",
        "APP 도메인 원문은 'G마켓', RETAIL 도메인 원문은 'G마켓/옥션' 으로 표기가 다르다. 측정 대상(앱 사용자 vs 옥션 합산 결제)이 달라 별개 entity 로 둔다.",
        True,
    ),
    ("Instagram", "APP"): ("instagram", SOLO, False),
    ("KB Pay", "APP"): ("kb_pay", SOLO, False),
    ("KB스타뱅킹", "APP"): ("kb_starbanking", SOLO, False),
    ("NH스마트뱅킹", "APP"): ("nh_smart_banking", SOLO, False),
    ("NH콕뱅크", "APP"): ("nh_cok_bank", SOLO, False),
    ("Netflix", "APP"): ("netflix", SOLO, False),
    ("TikTok", "APP"): ("tiktok", SOLO, False),
    ("TikTok Lite", "APP"): (
        "tiktok_lite",
        "원문이 'TikTok' 과 'TikTok Lite' 를 별도 행으로 올렸다(fig01_t2 동시 등장). 별개 앱이다.",
        False,
    ),
    ("V3 Mobile Plus", "APP"): ("v3_mobile_plus", SOLO, False),
    ("YouTube", "APP"): ("youtube", SOLO, False),
    ("내 파일", "APP"): ("my_files", SOLO, False),
    ("네이버", "APP"): (
        "naver_app",
        "APP 도메인 원문은 '네이버', RETAIL 도메인 원문은 '네이버/네이버페이' 로 표기가 다르다. 앱 사용자와 네이버페이 결제는 다른 측정 대상이므로 별개 entity 로 둔다.",
        True,
    ),
    ("네이버지도", "APP"): ("naver_map", SOLO, False),
    ("다음", "APP"): ("daum", SOLO, False),
    ("당근", "APP"): ("danggeun", SOLO, False),
    ("디바이스 케어", "APP"): ("device_care", SOLO, False),
    ("모니모", "APP"): ("monimo", SOLO, False),
    ("밴드", "APP"): ("band", SOLO, False),
    ("삼성 계산기", "APP"): ("samsung_calculator", SOLO, False),
    ("삼성 노트", "APP"): ("samsung_notes", SOLO, False),
    ("삼성 월렛", "APP"): ("samsung_wallet", SOLO, False),
    ("삼성 인터넷 브라우저", "APP"): ("samsung_internet_browser", SOLO, False),
    ("삼성카드", "APP"): ("samsung_card", SOLO, False),
    ("신한 SOL뱅크", "APP"): ("shinhan_sol_bank", SOLO, False),
    ("에이닷 전화", "APP"): ("adot_call", SOLO, False),
    ("카카오맵", "APP"): ("kakaomap", SOLO, False),
    ("카카오톡", "APP"): ("kakaotalk", SOLO, False),
    ("캐시워크", "APP"): ("cashwalk", SOLO, False),
    ("토스", "APP"): ("toss", SOLO, False),
    ("티맵", "APP"): ("tmap", SOLO, False),
    ("하나은행", "APP"): (
        "hana_bank",
        "fig04 아이콘은 '1Q 하나원큐' 지만 라벨 텍스트가 '하나은행' 이다. 원문 라벨 표기를 따른다.",
        False,
    ),
    ("현대카드", "APP"): ("hyundai_card", SOLO, False),
    ("쿠팡", "APP"): (
        "coupang_app",
        "APP 도메인은 앱 사용자·사용시간을, RETAIL 도메인은 카드 결제추정금액을 잰다. "
        "원문 표기가 같아도 측정 대상이 다르므로 measurement_entity 로는 별개다.",
        True,
    ),
    ("쿠팡", "RETAIL"): (
        "coupang_retail",
        "APP 도메인은 앱 사용자·사용시간을, RETAIL 도메인은 카드 결제추정금액을 잰다. "
        "원문 표기가 같아도 측정 대상이 다르므로 measurement_entity 로는 별개다.",
        True,
    ),
    ("CJ온스타일", "RETAIL"): ("cj_onstyle", SOLO, False),
    ("CU", "RETAIL"): ("cu", SOLO, False),
    ("GS25", "RETAIL"): ("gs25", SOLO, False),
    ("GS홈쇼핑/GS Shop", "RETAIL"): ("gs_homeshopping_gsshop", SLASH, False),
    ("G마켓/옥션", "RETAIL"): (
        "gmarket_auction",
        "슬래시 묶음 표기이자 APP 의 'G마켓' 과 다른 원문 표기. 원문 단위를 측정 단위로 보고 별개 entity 로 둔다.",
        True,
    ),
    ("NC백화점/뉴코아아울렛", "RETAIL"): ("nc_dept_newcore_outlet", SLASH, False),
    ("NS홈쇼핑", "RETAIL"): ("ns_homeshopping", SOLO, False),
    ("emart24", "RETAIL"): (
        "emart24",
        "원문이 '이마트'(fig06_t1) 와 'emart24'(fig06_t2) 를 별도 행으로 표기했다. 편의점 브랜드로 별개 entity 다.",
        False,
    ),
    ("네이버/네이버페이", "RETAIL"): (
        "naver_naverpay",
        "슬래시 묶음 표기이자 APP 의 '네이버' 와 다른 원문 표기. 결제 기준 측정 단위로 별개 entity 로 둔다.",
        True,
    ),
    ("농협하나로마트", "RETAIL"): ("nonghyup_hanaro_mart", SOLO, False),
    ("다이소", "RETAIL"): ("daiso", SOLO, False),
    ("대한항공", "RETAIL"): ("korean_air", SOLO, False),
    ("롯데마트", "RETAIL"): ("lotte_mart", SOLO, False),
    ("롯데백화점", "RETAIL"): ("lotte_department_store", SOLO, False),
    ("롯데하이마트", "RETAIL"): ("lotte_himart", SOLO, False),
    ("롯데홈쇼핑", "RETAIL"): ("lotte_homeshopping", SOLO, False),
    ("마켓컬리", "RETAIL"): ("market_kurly", SOLO, False),
    ("메가커피", "RETAIL"): ("mega_coffee", SOLO, False),
    ("배달의민족", "RETAIL"): ("baemin", SOLO, False),
    ("세븐일레븐", "RETAIL"): ("seven_eleven", SOLO, False),
    ("신세계백화점", "RETAIL"): ("shinsegae_department_store", SOLO, False),
    ("이마트", "RETAIL"): ("emart", SOLO, False),
    ("카카오T", "RETAIL"): ("kakao_t", SOLO, False),
    ("컴포즈커피", "RETAIL"): ("compose_coffee", SOLO, False),
    ("코스트코", "RETAIL"): ("costco", SOLO, False),
    ("쿠팡이츠", "RETAIL"): (
        "coupang_eats",
        "원문이 '쿠팡'(fig06_t1/t2) 과 '쿠팡이츠'(fig06_t2) 를 같은 표에 별도 행으로 올렸다. 별개 측정 대상이다.",
        False,
    ),
    ("탑마트", "RETAIL"): ("top_mart", SOLO, False),
    ("파리바게뜨/파리크라상", "RETAIL"): ("paris_baguette_pariscroissant", SLASH, False),
    ("현대백화점", "RETAIL"): ("hyundai_department_store", SOLO, False),
    ("현대홈쇼핑/현대Hmall", "RETAIL"): (
        "hyundai_homeshopping_hmall",
        "fig10_t2 의 '현대홈쇼핑/현대Hmallord' 와 같은 브랜드다. 같은 그림 안의 동일 5개 브랜드 세트이고 로고 이미지도 동일하며, 발행처 태그 목록에도 '현대홈쇼핑/현대Hmall' 만 실려 있다. 'ord' 는 원문(발행물) 자체의 렌더링 오타로 확인되어 별칭으로 흡수했다.",
        True,
    ),
    ("현대홈쇼핑/현대Hmallord", "RETAIL"): ("hyundai_homeshopping_hmall", "", False),
    ("홈앤쇼핑", "RETAIL"): ("home_and_shopping", SOLO, False),
    ("홈플러스", "RETAIL"): ("homeplus", SOLO, False),
    ("인터넷 쇼핑", "RETAIL"): ("industry_internet_shopping", INDUSTRY, False),
    ("오프라인 마트", "RETAIL"): ("industry_offline_mart", INDUSTRY, False),
    ("백화점/아울렛", "RETAIL"): ("industry_department_store_outlet", INDUSTRY, False),
    ("홈쇼핑", "RETAIL"): ("industry_home_shopping", INDUSTRY, False),
    ("여행/교통", "RETAIL"): ("industry_travel_transport", INDUSTRY, False),
    ("편의점", "RETAIL"): ("industry_convenience_store", INDUSTRY, False),
    ("전자기기", "RETAIL"): ("industry_electronics", INDUSTRY, False),
    ("식품", "RETAIL"): ("industry_food", INDUSTRY, False),
    ("배달", "RETAIL"): ("industry_delivery", INDUSTRY, False),
    ("식음료", "RETAIL"): ("industry_food_beverage", INDUSTRY, False),
}

# 대표 표기: canonical_key -> entity_name_raw (원문 표기 중 하나. 창작 금지)
CANONICAL_DISPLAY: dict[str, str] = {
    "hyundai_homeshopping_hmall": "현대홈쇼핑/현대Hmall",
}

# 별칭이 대표 표기와 다를 때의 match_basis / reviewer_note
ALIAS_OVERRIDE: dict[tuple[str, str], tuple[str, str]] = {
    ("현대홈쇼핑/현대Hmallord", "RETAIL"): (
        "REVIEWED",
        "fig10.png 하단 막대차트 라벨을 4배 확대 판독한 결과 원문이 실제로 "
        "'현대홈쇼핑/현대Hmallord' 로 렌더링돼 있음을 확인했다(판독 오류 아님, 발행물 오타). "
        "원자료 entity_name_raw 는 보정하지 않고 별칭으로만 흡수한다.",
    ),
}

# --------------------------------------------------------------------------
# 3. web_eligibility_status — 웹 수집 적격 여부. **확정은 업종 축 배제뿐이다.**
#    C009(D2): 이전 web_collectable 은 URL 증거 없이 True 70건을 찍어 게이트 결론을 선점했다.
#    C011(P1-2): 그 시정판이 남긴 SYSTEM_APP_CANDIDATE 11건도 같은 결함이었다. 두 감사관이
#    독립적으로 지적했다 — 근거 11개가 전부 "…로 알려져 있다" 형식이고 A1~A4 인용이 0건이며,
#    같은 GMS 번들인데 Google 포토는 찍히고 YouTube 는 안 찍히는 임의성이 실증됐다.
#    → 상태값은 {NOT_ASSESSED, EXCLUDED_INDUSTRY_AXIS} 둘뿐이다. 선탑재 추정은 Source Layer 가
#      아니라 state/_researcher_priors/system_app_hypothesis.json 으로 분리한다.
# --------------------------------------------------------------------------
STATUS_NOT_ASSESSED = "NOT_ASSESSED"
STATUS_EXCLUDED_INDUSTRY = "EXCLUDED_INDUSTRY_AXIS"
ALLOWED_ELIGIBILITY_STATUS = {STATUS_NOT_ASSESSED, STATUS_EXCLUDED_INDUSTRY}

# --------------------------------------------------------------------------
# 3-b. 연구자 사전판단 — **연구 결과가 아니다. Source Layer 가 아니다.**
#      아래 문구는 취득 자료(A1~A4) 어디에도 근거를 두지 않은 연구자의 배경지식이다.
#      service_master 에 상태값으로 찍으면 근거 없는 판정이 데이터가 된다. 그래서 분리해
#      가설 파일로만 남기고, 해소는 URL 증거를 보는 web_eligibility 게이트에 맡긴다.
#      basis 문구는 C009 판본 그대로 옮긴다(사후 윤색 금지).
# --------------------------------------------------------------------------
SYSTEM_APP_HYPOTHESIS_BASIS: dict[str, str] = {
    "samsung_calculator": "삼성 단말 기본 탑재 계산기 유틸리티로 알려져 있다. 단독 서비스 랜딩페이지가 존재하는지 미확인.",
    "samsung_notes": "삼성 단말 기본 탑재 메모 유틸리티로 알려져 있다. 단독 서비스 랜딩페이지가 존재하는지 미확인.",
    "samsung_wallet": "삼성 단말 기본 탑재 결제/월렛 앱으로 알려져 있다. 제조사 제품 페이지로 귀결될 가능성이 있다.",
    "samsung_internet_browser": "삼성 단말 기본 탑재 브라우저로 알려져 있다. 제조사 제품 페이지로 귀결될 가능성이 있다.",
    "my_files": "삼성 단말 기본 탑재 파일 관리자('내 파일')로 알려져 있다. 단독 랜딩페이지 부재 가능성이 높다.",
    "device_care": "삼성 단말 기본 탑재 기기 관리 유틸리티('디바이스 케어')로 알려져 있다. 단독 랜딩페이지 부재 가능성이 높다.",
    "chrome": "Android 기본 탑재 브라우저로 알려져 있다. OS 사업자 제품 페이지로 귀결될 가능성이 있다.",
    "google": "Android 기본 탑재 검색 앱으로 알려져 있다. OS 사업자 제품 페이지로 귀결될 가능성이 있다.",
    "google_photos": "Android 다수 기종에 기본 탑재되는 사진 앱으로 알려져 있다. 선탑재 범위가 기종별로 다르다.",
    "adot_call": "이동통신사(SKT)가 자사 출고 단말에 기본 탑재하는 전화 앱으로 알려져 있다. 통신사·기종 의존이라 확정 불가.",
    "v3_mobile_plus": "국내 출고 단말에 통신사/제조사가 번들하는 보안 앱으로 알려져 있다. 번들 범위가 출고 시기별로 달라 확정 불가.",
}

# --------------------------------------------------------------------------
# 4. web_target 그룹 후보 — 같은 랜딩 URL 로 귀결될 가능성이 있는 measurement_entity 묶음.
#    **URL 증거가 아직 하나도 없다.** 그래서 확정이 아니라 후보로만 둔다.
#    이 그룹이 확정되면 그룹당 관측을 정확히 1회만 수행해 2중 수집을 막는다.
# --------------------------------------------------------------------------
WEB_TARGET_GROUP_CANDIDATES: dict[str, tuple[list[str], str]] = {
    "coupang": (
        ["coupang_app", "coupang_retail"],
        "원문이 APP 과 RETAIL 양쪽에서 동일하게 '쿠팡' 으로 표기했다. 같은 브랜드의 랜딩 URL 이 "
        "하나일 가능성이 높지만 URL 을 확인하지 않았다.",
    ),
    "naver": (
        ["naver_app", "naver_naverpay"],
        "APP 표기 '네이버' 와 RETAIL 표기 '네이버/네이버페이' 는 측정 대상이 다르지만 "
        "랜딩 URL 은 하나로 귀결될 수 있다. URL 을 확인하지 않았다.",
    ),
    "gmarket": (
        ["gmarket_app", "gmarket_auction"],
        "APP 표기 'G마켓' 과 RETAIL 표기 'G마켓/옥션' 은 측정 대상이 다르지만 랜딩 URL 은 "
        "하나로 귀결될 수 있다. 옥션이 별도 URL 을 갖는지도 확인하지 않았다.",
    ),
}

GROUPING_CANDIDATE = "CANDIDATE_PENDING_URL_REVIEW"
GROUPING_SINGLETON = "SINGLETON_PENDING_URL_REVIEW"
ALLOWED_GROUPING_STATUS = {GROUPING_CANDIDATE, GROUPING_SINGLETON}


def sid(canonical_key: str) -> str:
    return "svc_" + hashlib.sha256(canonical_key.encode("utf-8")).hexdigest()[:16]


def aid(raw: str, domain: str, service_id: str) -> str:
    return "als_" + hashlib.sha256(f"{raw}\x1f{domain}\x1f{service_id}".encode()).hexdigest()[:16]


def wtg(web_target_key: str) -> str:
    return "wtg_" + hashlib.sha256(web_target_key.encode("utf-8")).hexdigest()[:16]


def main() -> None:
    rows = pd.read_parquet(STATE / "source_ranking_rows.parquet")
    panels = pd.read_parquet(STATE / "panel_registry.parquet")

    assert len(rows) == EXPECTED_ROWS, f"원자료 행수가 {EXPECTED_ROWS}이 아니다: {len(rows)}"
    assert "axis_type" in rows.columns, "원자료에 axis_type 이 없다 — 저널 재생성을 먼저 돌려라"

    # ---------------- panel_registry: panel_scope ----------------
    panels["panel_scope"] = panels["panel_id"].map(PANEL_SCOPE)
    missing_scope = panels.loc[panels["panel_scope"].isna(), "panel_id"].tolist()
    assert not missing_scope, f"panel_scope 미지정 패널: {missing_scope}"

    # ---------------- 원자료 커버리지 검사 ----------------
    rows["entity_key"] = list(zip(rows["entity_name_raw"], rows["domain"], strict=True))
    observed = sorted(set(rows["entity_key"]))
    unknown = [k for k in observed if k not in ENTITY_SPEC]
    assert not unknown, f"ENTITY_SPEC 에 없는 (원문 표기, 도메인): {unknown}"
    unused = [k for k in ENTITY_SPEC if k not in set(observed)]
    assert not unused, f"원자료에 없는 ENTITY_SPEC 항목: {unused}"

    # axis_type 은 원자료에서 유도한다. 한 entity 가 두 축에 걸치면 스키마가 깨진 것이다.
    axis_by_entity = rows.groupby("entity_key")["axis_type"].unique()
    mixed = {k: list(v) for k, v in axis_by_entity.items() if len(v) > 1}
    assert not mixed, f"축 유형이 둘 이상인 entity: {mixed}"
    entity_axis = {k: v[0] for k, v in axis_by_entity.items()}

    # ---------------- entity_candidates.json (중간산출물) ----------------
    # C009(D6): 고아 산출물이었다. 생성 경로를 이 스크립트로 편입한다.
    candidates = [
        {
            "entity_name_raw": raw,
            "domain": domain,
            "axis_type": entity_axis[(raw, domain)],
            "panels": sorted(
                rows.loc[rows["entity_key"] == (raw, domain), "panel_id"].unique().tolist()
            ),
            "n_rows": int((rows["entity_key"] == (raw, domain)).sum()),
            "canonical_service_key": ENTITY_SPEC[(raw, domain)][0],
        }
        for raw, domain in observed
    ]

    # ---------------- entity_alias_map ----------------
    # 키가 (entity_name_raw, domain) 이므로 같은 원문 표기가 도메인별로 다른 별칭을 갖는다.
    alias_recs = []
    for raw, domain in observed:
        ckey, _basis, _rev = ENTITY_SPEC[(raw, domain)]
        service_id = sid(ckey)
        display = CANONICAL_DISPLAY.get(ckey, raw)
        if (raw, domain) in ALIAS_OVERRIDE:
            basis, note = ALIAS_OVERRIDE[(raw, domain)]
        elif raw == display:
            basis, note = "EXACT", ""
        else:
            basis, note = "NORMALIZED", ""
        sub = rows[rows["entity_key"] == (raw, domain)]
        alias_recs.append(
            {
                "alias_id": aid(raw, domain, service_id),
                "service_id": service_id,
                "entity_name_raw": raw,
                "domain": domain,
                "axis_type": entity_axis[(raw, domain)],
                "panel_ids": ",".join(sorted(sub["panel_id"].unique())),
                "match_basis": basis,
                "reviewer_note": note,
            }
        )
    alias_map = pd.DataFrame(alias_recs).sort_values(
        ["service_id", "entity_name_raw"], ignore_index=True
    )

    # ---------------- service_master (measurement_entity 층) ----------------
    key2ckey = {k: v[0] for k, v in ENTITY_SPEC.items()}
    rows_ck = rows.assign(canonical_service_key=rows["entity_key"].map(key2ckey))

    # canonical_key -> web_target_group
    group_of: dict[str, tuple[str, str, str]] = {}
    for wkey, (members, basis) in WEB_TARGET_GROUP_CANDIDATES.items():
        for member in members:
            group_of[member] = (wtg(wkey), wkey, basis)

    svc_recs = []
    for ckey, sub in rows_ck.groupby("canonical_service_key"):
        pairs = sorted(set(zip(sub["entity_name_raw"], sub["domain"], strict=True)))
        raws = sorted({p[0] for p in pairs})
        domains = sorted({p[1] for p in pairs})
        assert len(domains) == 1, f"{ckey}: measurement_entity 가 도메인을 넘나든다 {domains}"
        domain = domains[0]
        axes = sorted({entity_axis[p] for p in pairs})
        assert len(axes) == 1, f"{ckey}: 축 유형이 둘 이상 {axes}"
        axis_type = axes[0]

        primary = CANONICAL_DISPLAY.get(ckey, raws[0])
        spec_src = next(p for p in pairs if ENTITY_SPEC[p][0] == ckey and ENTITY_SPEC[p][1])
        _, basis, needs_review = ENTITY_SPEC[spec_src]

        if axis_type == "INDUSTRY_CATEGORY":
            eligibility, elig_basis = STATUS_EXCLUDED_INDUSTRY, INDUSTRY
            group_id: str | None = None
            group_key: str | None = None
            grouping_status: str | None = None
        else:
            # C011(P1-2): 선탑재 추정으로 상태를 가르지 않는다. 브랜드 축은 전부 미평가다.
            eligibility = STATUS_NOT_ASSESSED
            elig_basis = "웹 수집 적격 여부를 아직 평가하지 않았다. URL 증거가 없다."
            if ckey in group_of:
                group_id, group_key, _ = group_of[ckey]
                grouping_status = GROUPING_CANDIDATE
            else:
                group_key = ckey
                group_id = wtg(ckey)
                grouping_status = GROUPING_SINGLETON

        # C009(C): 도메인 교차 합산이 성립하지 않도록 행 수를 도메인별로 나눠 담는다.
        app_rows = int((sub["domain"] == "APP").sum())
        retail_rows = int((sub["domain"] == "RETAIL").sum())
        svc_recs.append(
            {
                "service_id": sid(ckey),
                "canonical_service_key": ckey,
                "service_name_canonical": primary,
                "domain": domain,
                "axis_type": axis_type,
                "appears_in_app_panels": int(sub.loc[sub["domain"] == "APP", "panel_id"].nunique()),
                "appears_in_retail_panels": int(
                    sub.loc[sub["domain"] == "RETAIL", "panel_id"].nunique()
                ),
                "app_row_count": app_rows,
                "retail_row_count": retail_rows,
                "alias_count": len(pairs),
                "canonicalization_basis": basis,
                "needs_human_review": bool(needs_review),
                "web_eligibility_status": eligibility,
                "web_eligibility_basis": elig_basis,
                "web_target_group_id": group_id,
                "web_target_key": group_key,
                "web_target_grouping_status": grouping_status,
            }
        )
    service_master = pd.DataFrame(svc_recs).sort_values(
        ["domain", "axis_type", "canonical_service_key"], ignore_index=True
    )
    key2name = dict(
        zip(
            service_master["canonical_service_key"],
            service_master["service_name_canonical"],
            strict=True,
        )
    )

    # C011(P1-2): 상태값 도메인을 코드에서 닫는다. 근거 없는 새 상태값이 들어오지 못한다.
    bad_status = set(service_master["web_eligibility_status"]) - ALLOWED_ELIGIBILITY_STATUS
    assert not bad_status, f"허용되지 않은 web_eligibility_status: {bad_status}"

    # 도메인 순수성 — measurement_entity 는 정확히 한 도메인에만 행을 갖는다.
    both = service_master[
        (service_master["app_row_count"] > 0) & (service_master["retail_row_count"] > 0)
    ]
    assert both.empty, (
        f"도메인을 넘나드는 measurement_entity: {both['canonical_service_key'].tolist()}"
    )

    # ---------------- web_target_group (web_target 층) ----------------
    web_recs = []
    for wkey, sub in service_master[service_master["web_target_key"].notna()].groupby(
        "web_target_key"
    ):
        is_candidate = wkey in WEB_TARGET_GROUP_CANDIDATES
        # C011(P1-1): 세 배열을 각각 독립 정렬하면 위치가 어긋난다. wtg_6d5510a695d0a614(naver)
        # 에서 naver_app 이 RETAIL 과, naver_naverpay 가 APP 과 같은 자리에 놓여 읽혔다.
        # 집합 수준은 정확했지만, 네이버·G마켓 2중수집을 막으려고 만든 표가 같은 혼동을
        # 재생산했다. 하나의 정렬 키(service_id)로 튜플을 정렬한 뒤 풀어서 위치를 일치시킨다.
        members = sorted(
            zip(
                sub["service_id"],
                sub["canonical_service_key"],
                sub["domain"],
                strict=True,
            )
        )
        member_ids = [m[0] for m in members]
        member_keys = [m[1] for m in members]
        member_domains = [m[2] for m in members]
        web_recs.append(
            {
                "web_target_group_id": wtg(str(wkey)),
                "web_target_key": wkey,
                "member_service_ids": ",".join(member_ids),
                "member_canonical_keys": ",".join(member_keys),
                "member_count": len(members),
                # 위치 i 는 member_service_ids[i] 의 도메인이다. 집합이 아니라 배열이므로
                # 같은 도메인이 두 번 나올 수 있다 — 그것이 정상이다.
                "member_domains": ",".join(member_domains),
                "grouping_status": GROUPING_CANDIDATE if is_candidate else GROUPING_SINGLETON,
                "grouping_basis": (
                    WEB_TARGET_GROUP_CANDIDATES[str(wkey)][1]
                    if is_candidate
                    else "다른 measurement_entity 와 묶을 원문 근거가 없다. 단독 web_target 후보."
                ),
                # URL 증거가 없다. 그룹이 확정되기 전에는 이 두 칸이 비어 있어야 한다.
                "web_target_url": None,
                "url_evidence": None,
            }
        )
    web_target_group = pd.DataFrame(web_recs).sort_values(
        ["grouping_status", "web_target_key"], ignore_index=True
    )
    unresolved = web_target_group[web_target_group["web_target_url"].notna()]
    assert unresolved.empty, "URL 미확정 상태에서 web_target_url 이 채워졌다"
    bad_grouping = set(web_target_group["grouping_status"]) - ALLOWED_GROUPING_STATUS
    assert not bad_grouping, f"허용되지 않은 grouping_status: {bad_grouping}"

    # C011(P1-1): 세 member_* 배열의 위치 대응을 산출 시점에 강제한다.
    domain_of = dict(zip(service_master["service_id"], service_master["domain"], strict=True))
    key_of = dict(
        zip(service_master["service_id"], service_master["canonical_service_key"], strict=True)
    )
    for rec in web_target_group.itertuples():
        ids = rec.member_service_ids.split(",")
        keys = rec.member_canonical_keys.split(",")
        doms = rec.member_domains.split(",")
        assert len(ids) == len(keys) == len(doms) == rec.member_count, (
            f"{rec.web_target_group_id}: member_* 배열 길이 불일치"
        )
        for i, s_id in enumerate(ids):
            assert domain_of[s_id] == doms[i] and key_of[s_id] == keys[i], (
                f"{rec.web_target_group_id}[{i}]: member_* 위치 어긋남"
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
        "schema": "extraction_corrections/v2",
        "generated_by": "research/landing_accessibility/scripts/build_canonical_entities.py",
        "note": (
            "C003 단계의 판독 검증 2건(COR-001/002)과 C009 감사 수용에 따른 스키마 시정 2건"
            "(COR-003/004)을 함께 기록한다. 원자료(source_ranking_rows.parquet) 값 시정은 "
            "누적 0건이며 261행은 그대로다."
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
                    "panel_registry 와 source_ranking_rows 에 axis_type 컬럼을 두어 fig07_t1 만 "
                    "INDUSTRY_CATEGORY, 나머지 16패널은 SERVICE_BRAND 로 표시. 해당 10개 entity 는 "
                    "web_eligibility_status='EXCLUDED_INDUSTRY_AXIS' 로 브랜드 entity 공간과 분리했다."
                ),
                "corrected_by": "exec-agent(C003) / 이미지 직접 판독",
            },
            {
                "correction_id": "COR-003",
                "row_id": None,
                "affected_row_ids": [],
                "panel_id": None,
                "field": "service_master.entity_kind",
                "before": "entity_kind ∈ {APP, RETAIL_BRAND, INDUSTRY_CATEGORY, BOTH}",
                "after": "domain ∈ {APP, RETAIL} × axis_type ∈ {SERVICE_BRAND, INDUSTRY_CATEGORY}",
                "action": "SCHEMA_FIX_AXIS_DOMAIN_SPLIT",
                "evidence": (
                    "entity_kind 한 컬럼이 도메인(무엇을 쟀는가)과 축유형(브랜드인가 업종인가)을 섞고 있었다. "
                    "그 결과 `entity_kind == 'RETAIL_BRAND'` 필터가 entity_kind='BOTH' 였던 쿠팡을 "
                    "조용히 누락시켰다. 쿠팡은 리테일 순 결제추정금액 1위다 — 필터가 1위를 떨어뜨렸다."
                ),
                "resolution": (
                    "domain 과 axis_type 을 별도 컬럼으로 분리하고 entity_kind 를 삭제했다. "
                    "리테일 브랜드 집합은 이제 (domain=='RETAIL') & (axis_type=='SERVICE_BRAND') 로 "
                    "표현되며 업종 축과 브랜드 축이 컬럼 수준에서 갈린다."
                ),
                "corrected_by": "exec-agent(C009) / SSOT·적대적 감사 수용",
            },
            {
                "correction_id": "COR-004",
                "row_id": None,
                "affected_row_ids": [],
                "panel_id": None,
                "field": "measurement_entity key",
                "before": "entity_name_raw (쿠팡 = 1개 entity, entity_kind='BOTH')",
                "after": "(entity_name_raw, domain) (쿠팡 = coupang_app + coupang_retail)",
                "action": "SCHEMA_FIX_MEASUREMENT_WEB_TWO_LAYER",
                "evidence": (
                    "APP 패널은 앱 사용자·사용시간을, RETAIL 패널은 카드 결제추정금액을 잰다. 두 지표는 "
                    "모집단도 단위도 다르다. 원문 표기가 같다는 이유로 하나의 entity 로 묶으면 "
                    "서로 다른 것을 잰 값이 한 축에서 합산 가능해진다. 반대로 네이버·G마켓처럼 표기가 "
                    "다르다는 이유로 분리하면 그 분리가 수집 단위까지 전파돼 같은 랜딩페이지를 2번 방문하게 된다."
                ),
                "resolution": (
                    "층을 나눴다. measurement_entity 는 (entity_name_raw, domain) 을 키로 삼아 "
                    "무엇을 쟀는지를 보존하고, web_target 층(web_target_group.parquet)이 같은 랜딩 URL 로 "
                    "귀결될 후보를 묶어 관측 1회를 보장한다. URL 증거가 없으므로 그룹은 "
                    "grouping_status='CANDIDATE_PENDING_URL_REVIEW' 로 미확정이다. "
                    "source_row_count 는 app_row_count / retail_row_count 로 분리해 도메인 교차 합산을 막았다."
                ),
                "corrected_by": "exec-agent(C009) / 오케스트레이터 재결",
            },
            {
                "correction_id": "COR-005",
                "row_id": None,
                "affected_row_ids": [],
                "panel_id": None,
                "field": "service_master.web_eligibility_status",
                "before": "SYSTEM_APP_CANDIDATE 11건 + NOT_ASSESSED 60건 + EXCLUDED_INDUSTRY_AXIS 10건",
                "after": "NOT_ASSESSED 71건 + EXCLUDED_INDUSTRY_AXIS 10건",
                "action": "UNSOURCED_PRIOR_SEPARATED_FROM_SOURCE_LAYER",
                "evidence": (
                    "SYSTEM_APP_CANDIDATE 11건은 스크립트의 하드코딩 dict 에서 `ckey in ...` "
                    "한 줄로 나왔고, 근거 11개가 전부 '…로 알려져 있다' 형식이며 A1~A4 인용이 "
                    "0건이다. 적대적 감사가 임의성의 증거를 찾았다 — 같은 GMS 번들인데 "
                    "Google 포토는 찍혔고 YouTube 는 안 찍혔다. 두 감사관이 독립적으로 지적했다."
                ),
                "resolution": (
                    "상태값 도메인을 {NOT_ASSESSED, EXCLUDED_INDUSTRY_AXIS} 로 닫았다. 확정 판정은 "
                    "업종 축 배제 10건뿐이다. 선탑재 추정은 Source Layer 밖의 "
                    "state/_researcher_priors/system_app_hypothesis.json 으로 옮기고 각 항목에 "
                    "status='UNSOURCED_RESEARCHER_PRIOR', evidence_pointer=null 을 명시했다. "
                    "해소는 URL 증거를 보는 web_eligibility 게이트가 한다."
                ),
                "corrected_by": "exec-agent(C011) / 독립감사 2건 수용",
            },
            {
                "correction_id": "COR-006",
                "row_id": None,
                "affected_row_ids": [],
                "panel_id": None,
                "field": "web_target_group.member_* 3개 배열",
                "before": "member_service_ids / member_canonical_keys / member_domains 각각 독립 정렬",
                "after": "service_id 기준 튜플 정렬 후 unzip — 세 배열의 위치가 대응",
                "action": "SCHEMA_FIX_POSITIONAL_ALIGNMENT",
                "evidence": (
                    "wtg_6d5510a695d0a614(naver)에서 member_service_ids 정렬 순서와 "
                    "member_domains 정렬 순서가 달라, 위치로 읽으면 naver_app↔RETAIL, "
                    "naver_naverpay↔APP 으로 읽혔다. 집합 수준은 정확해 값 손실은 없었으나, "
                    "네이버·G마켓 2중수집을 막으려고 만든 표가 같은 혼동을 재생산했다."
                ),
                "resolution": (
                    "세 배열을 하나의 정렬 키로 동시에 정렬한다. member_domains 는 집합이 아니라 "
                    "위치 배열이므로 같은 도메인이 중복 등장할 수 있다. "
                    "tests/test_c009_two_layer.py 가 위치별로 대조한다."
                ),
                "corrected_by": "exec-agent(C011) / 독립감사 2건 수용",
            },
        ],
        "row_value_changes_applied": 0,
        "source_row_count_before": EXPECTED_ROWS,
        "source_row_count_after": len(rows),
    }

    # ---------------- 연구자 사전판단 분리 (C011/P1-2) ----------------
    # Source Layer 밖에 둔다. 이 파일은 근거가 아니라 다음 게이트가 검증할 가설 목록이다.
    known_keys = set(service_master["canonical_service_key"])
    unknown_hyp = sorted(set(SYSTEM_APP_HYPOTHESIS_BASIS) - known_keys)
    assert not unknown_hyp, f"service_master 에 없는 가설 대상: {unknown_hyp}"
    priors = {
        "schema": "researcher_priors/system_app_hypothesis/v1",
        "generated_by": "research/landing_accessibility/scripts/build_canonical_entities.py",
        "NOT_A_SOURCE_LAYER": (
            "이것은 연구 결과가 아니라 가설이며 Source Layer 가 아니다. "
            "아래 항목은 취득 자료(A1 와이즈앱 원문 / A2 인증 레지스트리 / A3 / A4) 어디에도 "
            "근거를 두지 않은 연구자의 배경지식이다. 어떤 판정·집계·필터의 입력으로도 "
            "사용하지 않는다. service_master.web_eligibility_status 는 이 파일을 참조하지 않는다."
        ),
        "why_separated": (
            "C009 판본은 이 목록을 service_master.web_eligibility_status='SYSTEM_APP_CANDIDATE' "
            "11건으로 찍었다. 두 감사관이 독립적으로 지적했다 — 근거 11개가 전부 "
            "'…로 알려져 있다' 형식이고 A1~A4 인용이 0건이다. 적대적 감사는 임의성의 증거로 "
            "같은 GMS 번들인데 Google 포토는 찍히고 YouTube 는 안 찍힌 사실을 들었다. "
            "근거 없는 추정이 상태값이 되면 데이터가 된다. 그래서 층을 분리했다."
        ),
        "resolves_at": "web_eligibility gate via URL evidence",
        "hypothesis_count": len(SYSTEM_APP_HYPOTHESIS_BASIS),
        "hypotheses": [
            {
                "canonical_service_key": ckey,
                "service_id": sid(ckey),
                "service_name_canonical": key2name[ckey],
                "hypothesis": (
                    "단말 제조사(OEM)·통신사 또는 OS 사업자가 기본 탑재해, 사용자의 설치 행위 "
                    "없이 단말에 존재했을 가능성이 있다. 그 경우 단독 서비스 랜딩페이지가 "
                    "없거나 제조사 제품 페이지로 귀결될 수 있다."
                ),
                "basis": basis,
                "evidence_pointer": None,
                "status": "UNSOURCED_RESEARCHER_PRIOR",
                "resolves_at": "web_eligibility gate via URL evidence",
            }
            for ckey, basis in sorted(SYSTEM_APP_HYPOTHESIS_BASIS.items())
        ],
    }

    # ---------------- 저장 ----------------
    (STATE / "_researcher_priors").mkdir(exist_ok=True)
    (STATE / "_researcher_priors" / "system_app_hypothesis.json").write_text(
        json.dumps(priors, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    panels.to_parquet(STATE / "panel_registry.parquet", index=False)
    panels.to_csv(STATE / "panel_registry.csv", index=False, encoding="utf-8-sig")
    for name, df in [
        ("service_master", service_master),
        ("entity_alias_map", alias_map),
        ("source_membership", mem),
        ("web_target_group", web_target_group),
    ]:
        df.to_parquet(STATE / f"{name}.parquet", index=False)
        df.to_csv(STATE / f"{name}.csv", index=False, encoding="utf-8-sig")
    (STATE / "entity_candidates.json").write_text(
        json.dumps(candidates, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    (STATE / "extraction_corrections.json").write_text(
        json.dumps(corrections, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    # ---------------- 요약 ----------------
    print(f"source_ranking_rows  : {len(rows)} 행 (불변)")
    print(f"panel_registry       : {len(panels)} 패널")
    print(f"measurement_entity   : {len(service_master)} 개")
    print(service_master.groupby(["domain", "axis_type"]).size().to_string())
    print(f"entity_alias_map     : {len(alias_map)} 별칭 ((표기, 도메인) 키)")
    print(f"source_membership    : {len(mem)} 행")
    print(f"web_target_group     : {len(web_target_group)} 그룹")
    print(web_target_group["grouping_status"].value_counts().to_string())
    print("web_eligibility_status:")
    print(service_master["web_eligibility_status"].value_counts().to_string())
    print(
        f"행수 도메인 분리      : app {int(service_master['app_row_count'].sum())} + "
        f"retail {int(service_master['retail_row_count'].sum())} = "
        f"{int(service_master['app_row_count'].sum() + service_master['retail_row_count'].sum())}"
    )
    nr = service_master[service_master["needs_human_review"]]
    print(f"needs_human_review   : {len(nr)}")
    for r in nr.itertuples():
        print(f"  - {r.service_id} {r.canonical_service_key} ({r.service_name_canonical})")


if __name__ == "__main__":
    main()
