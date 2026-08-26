"""C013 (W3/W4/W5) — web eligibility 판정 · official landing URL 확정 · web_target_group 승격.

## 실행 순서

    1) scripts/build_source_rows_from_journal.py      저널 → 261행 + 17패널
    2) scripts/build_canonical_entities.py            → measurement_entity 81 / web_target_group 68
    3) scripts/probe_official_urls.py                 (네트워크 1회) → state/url_review_probe.json
    4) scripts/build_web_eligibility_and_url_review.py (이 파일, 결정적)

(3)만 네트워크를 탄다. 관측 결과를 JSON 으로 동결해 두고 (4)는 그것만 읽으므로,
같은 입력에 같은 출력이 나온다 — 멱등성 검사가 성립한다.

## 이 파일이 지키는 것

06 §2-1 의 어휘로만 판정한다.

    WEB_SERVICE / OFFICIAL_PRODUCT_PAGE / APP_ONLY / SYSTEM_APP /
    RETAIL_OFFLINE_ONLY / EXCLUDED_INDUSTRY_AXIS / UNRESOLVED

원칙 셋을 코드가 강제한다.

    (a) **URL 이 존재한다는 사실만으로 WEB_SERVICE 로 두지 않는다** (06 §2-1).
        상태값은 '그 URL 에서 서비스의 핵심 기능을 브라우저로 쓸 수 있는가' 로 갈린다.
    (b) **SYSTEM_APP 확정은 공식 웹 랜딩이 없음을 실제 확인했을 때만이다** (06 §2-3).
        `state/_researcher_priors/system_app_hypothesis.json` 의 11건은 가설이지 근거가 아니다.
        선탑재 여부 자체는 판정 근거가 아니다. 이 파일은 그 JSON 을 **읽지 않는다** —
        가설이 판정의 입력이 되면 층 분리가 무의미해진다.
    (c) **확인 불가는 UNRESOLVED 이고, 제외로 바꾸지 않는다** (06 §2-3).

## 근거 필드 (06 §2-2 · debt: eligibility-basis-fields-narrower-than-06-still-carried)

C012 까지 service_master 에는 `web_eligibility_basis` 한 칸뿐이었다. 71건을 판정하는 순간
근거 없이 상태값만 쌓인다. 그래서 06 §2-2 가 요구한 칸을 전부 만든다.

    web_eligibility_status / eligibility_basis / eligibility_reviewer /
    eligibility_confidence / eligibility_reviewed_at / eligibility_needs_review

`eligibility_needs_review` 는 measurement 층의 `needs_human_review` 와 **별도 컬럼**이다.
두 층이 한 칸을 공유하면 어느 층의 미결인지 구별되지 않는다(ssot C012 지적).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
STATE = ROOT / "state"
sys.path.insert(0, str(ROOT / "src"))

from landing_accessibility.registered_domain import (  # noqa: E402
    psl_provenance,
    registered_domain,
)

REVIEWED_AT = "2026-08-26"
REVIEWER = "exec-agent(C013) / 검색 후보 → 직접 접속 확인"

# ── 06 §2-1 상태 어휘 ────────────────────────────────────────────────────────
WEB_SERVICE = "WEB_SERVICE"
OFFICIAL_PRODUCT_PAGE = "OFFICIAL_PRODUCT_PAGE"
APP_ONLY = "APP_ONLY"
SYSTEM_APP = "SYSTEM_APP"
RETAIL_OFFLINE_ONLY = "RETAIL_OFFLINE_ONLY"
EXCLUDED_INDUSTRY_AXIS = "EXCLUDED_INDUSTRY_AXIS"
UNRESOLVED = "UNRESOLVED"

ALLOWED_STATUS = {
    WEB_SERVICE,
    OFFICIAL_PRODUCT_PAGE,
    APP_ONLY,
    SYSTEM_APP,
    RETAIL_OFFLINE_ONLY,
    EXCLUDED_INDUSTRY_AXIS,
    UNRESOLVED,
}
# 주 분석은 WEB_SERVICE 만 쓴다 (06 §2-1).
ANALYSIS_STATUS = {WEB_SERVICE}

# 71건을 같은 잣대로 가르기 위해 기준을 미리 적어 둔다. 기준 없이 건별로 판단하면
# 같은 성격의 서비스가 서로 다르게 분류되고, 그 차이가 나중에 결과 차이로 읽힌다.
STATUS_CRITERIA = {
    WEB_SERVICE: (
        "그 URL 이 **서비스 자신의 웹 애플리케이션 진입점**이다. 로그인 벽이 있어도 진입점은 "
        "진입점이다(06 §2-1 '사용자가 실제 기능에 진입하는'). 예: 오픈마켓 상품 탐색·구매, "
        "인터넷뱅킹, 웹 지도, 웹 스트리밍."
    ),
    OFFICIAL_PRODUCT_PAGE: (
        "운영사 공식 페이지이지만 그 URL 에 웹 애플리케이션이 없다. 기능 소개와 앱 설치 "
        "유도가 전부다. 예: 앱 소개 페이지, 브랜드 소개 페이지."
    ),
    APP_ONLY: "운영사의 공식 웹 랜딩이 사실상 없다. 확인된 것이 제3자 스토어 등록 페이지뿐이다.",
    SYSTEM_APP: (
        "단말 선탑재·OS 구성요소라 공개 웹 랜딩 개념이 성립하지 않는다. **부재를 실제 확인한 "
        "경우에만** 쓴다(06 §2-3). 선탑재 여부 자체는 근거가 아니다."
    ),
    RETAIL_OFFLINE_ONLY: (
        "오프라인 매장 브랜드이고 공식 랜딩이 매장·기업 안내 페이지다. A1 RETAIL 패널이 잰 것은 "
        "카드 결제인데 그 결제가 이 랜딩에서 일어나지 않는다."
    ),
    UNRESOLVED: "공식 URL 을 하나로 확정하지 못했다. 제외로 바꾸지 않는다(06 §2-3).",
}

# 리테일 브랜드에 기업/브랜드 사이트와 거래 사이트가 둘 다 있을 때 어느 쪽을 랜딩으로 볼 것인가.
RETAIL_LANDING_SELECTION_RULE = (
    "A1 RETAIL 패널이 잰 것은 소비자 카드 결제다. 따라서 같은 브랜드에 기업/브랜드 소개 "
    "사이트와 소비자 거래 사이트가 둘 다 있으면 **거래 사이트**를 랜딩으로 고른다. 거래 "
    "사이트가 없으면 브랜드·기업 사이트를 고르고 RETAIL_OFFLINE_ONLY 로 둔다. "
    "브랜드 단독 거래 사이트가 없고 통합몰(예: 롯데온) 안의 한 관으로만 존재하면 브랜드 "
    "단독 랜딩이 확정되지 않은 것으로 보고 기업 사이트를 쓰되 미결 사유를 남긴다."
)

# ── 06 §3-1 url_type 어휘 (닫힌 4값) ─────────────────────────────────────────
URL_TYPE_WEB_SERVICE_LANDING = "WEB_SERVICE_LANDING"
URL_TYPE_PRODUCT_PAGE = "OFFICIAL_PRODUCT_PAGE"
URL_TYPE_APP_ONLY = "APP_ONLY"
URL_TYPE_UNRESOLVED = "UNRESOLVED"
ALLOWED_URL_TYPE = {
    URL_TYPE_WEB_SERVICE_LANDING,
    URL_TYPE_PRODUCT_PAGE,
    URL_TYPE_APP_ONLY,
    URL_TYPE_UNRESOLVED,
}

# eligibility_status → url_type. 06 §3-1 의 어휘는 4값으로 닫혀 있고 §2-1 은 7값이므로
# 사상이 필요하다. 정보가 뭉개지지 않도록 url_review 는 원 상태값을 그대로 한 칸 더 싣는다.
STATUS_TO_URL_TYPE = {
    WEB_SERVICE: URL_TYPE_WEB_SERVICE_LANDING,
    OFFICIAL_PRODUCT_PAGE: URL_TYPE_PRODUCT_PAGE,
    # 오프라인 결제 브랜드도 공식 페이지 자체는 존재한다. 다만 측정 대상 채널이 아니다.
    RETAIL_OFFLINE_ONLY: URL_TYPE_PRODUCT_PAGE,
    APP_ONLY: URL_TYPE_APP_ONLY,
    # 선탑재 구성요소는 공개 웹 랜딩 개념이 성립하지 않는다 → 랜딩 없음과 같은 칸에 둔다.
    SYSTEM_APP: URL_TYPE_APP_ONLY,
    UNRESOLVED: URL_TYPE_UNRESOLVED,
}

# ── 06 §3-4 그룹 상태 ────────────────────────────────────────────────────────
GROUPING_CANDIDATE = "CANDIDATE_PENDING_URL_REVIEW"
GROUPING_SINGLETON_PENDING = "SINGLETON_PENDING_URL_REVIEW"
GROUPING_CONFIRMED_SHARED = "CONFIRMED_SHARED_TARGET"
GROUPING_SPLIT = "SPLIT"
GROUPING_SINGLETON_CONFIRMED = "SINGLETON_CONFIRMED"
# 06 §3-4 는 '같은 URL 인가' 만 열거한다. 검토를 마쳤는데 **웹 랜딩 자체가 성립하지 않는**
# 경우를 담을 칸이 없어서 한 값을 더 둔다. PENDING 에 남겨 두면 '아직 안 봤다' 와
# '보고 나서 없다고 판정했다' 가 구별되지 않는다.
GROUPING_SINGLETON_NOT_A_WEB_TARGET = "SINGLETON_NOT_A_WEB_TARGET"
ALLOWED_GROUPING_STATUS = {
    GROUPING_CANDIDATE,
    GROUPING_SINGLETON_PENDING,
    GROUPING_CONFIRMED_SHARED,
    GROUPING_SPLIT,
    GROUPING_SINGLETON_CONFIRMED,
    GROUPING_SINGLETON_NOT_A_WEB_TARGET,
}

# ── 가설 검정 결과 어휘 ──────────────────────────────────────────────────────
HYP_CONFIRMED = "CONFIRMED_SAME_LANDING"
HYP_FALSIFIED_DIFFERENT = "FALSIFIED_DIFFERENT_LANDING"
HYP_FALSIFIED_NO_SINGLE = "FALSIFIED_NO_SINGLE_LANDING_FOR_MEMBER"
HYP_NOT_TESTED = "NOT_TESTED_URL_UNRESOLVED"
HYP_NA_SINGLETON = "NOT_APPLICABLE_SINGLETON"
ALLOWED_HYPOTHESIS_OUTCOME = {
    HYP_CONFIRMED,
    HYP_FALSIFIED_DIFFERENT,
    HYP_FALSIFIED_NO_SINGLE,
    HYP_NOT_TESTED,
    HYP_NA_SINGLETON,
}

# ── 관측 결과 등급 ───────────────────────────────────────────────────────────
# 신뢰도는 손으로 매기지 않고 관측에서 유도한다. 사후에 유리하게 조정할 여지를 없앤다.
CONFIDENCE_RULE = (
    "신뢰도는 **관측 품질**만으로 유도한다. 손으로 올리고 내릴 수 없고, 판정이 마음에 드는지와 "
    "무관하다.\n"
    "HIGH   후보 URL 이 HTTP 200 으로 응답했고 페이지 제목을 읽었다. 근거가 우리가 직접 받은 "
    "응답 안에 있다.\n"
    "MEDIUM 응답은 받았으나 제목을 읽지 못했다 — 봇 차단(401/403/406/429/5xx)이거나 "
    "JS 렌더링이라 초기 HTML 에 title 이 없다. URL 이 실재한다는 사실까지만 확인됐다.\n"
    "LOW    아예 응답하지 않았다(DNS/타임아웃/TLS 실패). 우리가 확인한 것이 없다."
)
NEEDS_REVIEW_RULE = (
    "다음 중 하나라도 해당하면 eligibility_needs_review=true 다.\n"
    "  (1) 상태값이 UNRESOLVED 다.\n"
    "  (2) 관측 신뢰도가 LOW 다.\n"
    "  (3) 봇 차단으로 랜딩 화면을 직접 보지 못했다 — URL 은 실재하나 '실제 서비스의 랜딩 "
    "경험' 을 우리가 확인하지는 못했다(06 §2-1).\n"
    "  (4) 최종 URL 이 후보와 **다른 등록도메인**으로 이동했다. 06 §3-3 은 외부 도메인 이동을 "
    "자동으로 같은 서비스라 가정하지 말고 QA 큐로 보내라고 한다.\n"
    "  (5) 페이지 제목을 읽었는데 그 안에 브랜드 토큰이 하나도 없다. 제목이 브랜드를 "
    "확인해 주지 못하면 identity 를 사람이 봐야 한다."
)
BLOCKED_STATUSES = {401, 403, 406, 429, 500, 502, 503, 520, 521, 522, 526}


# --------------------------------------------------------------------------
# 판정표 — 71건. **각 항목은 위 STATUS_CRITERIA 를 그 entity 에 적용한 결과다.**
#
#   status         06 §2-1 어휘
#   url            공식 랜딩으로 확정한 URL. 확정하지 못했으면 넣지 않는다.
#   evidence_url   확정 URL 이 없을 때 '무엇을 열어보고 그렇게 판정했는가'
#   judgment       왜 그 상태인가. URL 이 있다는 사실이 아니라 그 URL 이 무엇인가를 적는다.
#   absence_check  SYSTEM_APP 전용. 공식 웹 랜딩 부재를 어떻게 확인했는가 (06 §2-3)
#   extra_review_reason  기계 규칙이 잡지 못한 미결 사유. 추가만 가능하다.
#
# 신뢰도와 미결 여부는 여기에 적지 않는다 — 관측에서 유도된다.
# --------------------------------------------------------------------------
ELIGIBILITY_DECISIONS: dict[str, dict[str, str]] = {
    # ── APP 도메인 ──────────────────────────────────────────────────────────
    "11st": {
        "status": WEB_SERVICE,
        "url": "https://www.11st.co.kr/",
        "judgment": "오픈마켓 상품 탐색·구매가 브라우저에서 그대로 동작하는 서비스 진입점이다.",
    },
    "adot_call": {
        "status": OFFICIAL_PRODUCT_PAGE,
        "url": "https://www.skt-phone.co.kr/",
        "judgment": (
            "운영사(SKT)의 공식 페이지이지만 통화라는 핵심 기능은 단말 앱에서만 일어난다. "
            "이 URL 에서 하는 일은 기능 소개와 가입 안내다."
        ),
    },
    "band": {
        "status": WEB_SERVICE,
        "url": "https://band.us/",
        "judgment": "밴드 웹 클라이언트의 진입점이다. 로그인 후 글·댓글 등 모임 기능을 브라우저에서 쓴다.",
    },
    "cashwalk": {
        "status": OFFICIAL_PRODUCT_PAGE,
        "url": "https://cashwalk.com/",
        "judgment": (
            "걸음 적립이라는 핵심 기능은 단말 센서에 묶여 앱에서만 성립한다. 이 URL 은 소개 "
            "페이지이며 웹 애플리케이션이 없다."
        ),
    },
    "chrome": {
        "status": OFFICIAL_PRODUCT_PAGE,
        "url": "https://www.google.com/chrome/",
        "judgment": (
            "브라우저 제품 소개·다운로드 페이지다. 06 §2-3 이 말한 두 번째 경로 — 선탑재 "
            "가설을 '공식 랜딩이 OFFICIAL_PRODUCT_PAGE 임을 확인' 으로 해소한다. "
            "선탑재 여부는 판정에 쓰지 않았다."
        ),
    },
    "coupang_app": {
        "status": WEB_SERVICE,
        "url": "https://www.coupang.com/",
        "judgment": (
            "쿠팡 자신의 커머스 사이트이며 상품 탐색·구매가 브라우저에서 일어난다. "
            "다만 우리 요청은 봇 차단(403)으로 막혀 랜딩 화면 자체를 보지 못했다."
        ),
    },
    "danggeun": {
        "status": WEB_SERVICE,
        "url": "https://www.daangn.com/kr",
        "judgment": (
            "지역 중고거래 게시물 탐색·검색이 브라우저에서 동작하는 웹 진입점이다. "
            "채팅 등 일부 기능은 앱으로 넘어간다."
        ),
    },
    "daum": {
        "status": WEB_SERVICE,
        "url": "https://www.daum.net/",
        "judgment": "포털 서비스 본체가 브라우저에서 그대로 동작한다. 앱은 같은 서비스의 다른 채널이다.",
    },
    "device_care": {
        "status": SYSTEM_APP,
        "evidence_url": "https://www.samsungsvc.co.kr/solution/42404",
        "judgment": (
            "단말 관리 유틸리티로, 운영사가 내놓은 소비자용 웹 랜딩이 확인되지 않는다. "
            "확인된 것은 제3자 스토어 등록 페이지와 고객지원 FAQ 문서뿐이다."
        ),
        "absence_check": (
            "탐색 단계에서 삼성전자 공식 앱 소개 색인(samsung.com/sec/apps/)을 열어 등재된 앱 "
            "페이지를 전수 확인했고 '디바이스 케어' 페이지가 없음을 확인했다. 이어서 발견된 "
            "후보 3건을 직접 요청한 결과 Microsoft Store 등록 페이지·Play Store 등록 페이지·"
            "삼성전자서비스 고객지원 FAQ 였다. 선탑재라는 사실 자체는 근거로 쓰지 않았다."
        ),
    },
    "gmarket_app": {
        "status": WEB_SERVICE,
        "url": "https://www.gmarket.co.kr/",
        "judgment": (
            "오픈마켓 본체 사이트다. 응답은 봇 차단(403)이었으나 차단 페이지에도 원문 표기와 "
            "같은 브랜드 제목이 실려 있었다."
        ),
    },
    "google": {
        "status": WEB_SERVICE,
        "url": "https://www.google.co.kr/",
        "judgment": (
            "검색 서비스 본체가 브라우저에서 동작한다. 국가 도메인이 글로벌 도메인으로 "
            "이동하는 것을 관측했고, 등록도메인이 바뀌므로 06 §3-3 에 따라 QA 큐로 보낸다."
        ),
    },
    "google_photos": {
        "status": WEB_SERVICE,
        "url": "https://photos.google.com/",
        "judgment": (
            "사진 라이브러리 웹 애플리케이션의 진입점이다. 로그인하지 않은 우리 요청은 같은 "
            "등록도메인의 소개 경로로 이동했다 — 로그인 벽 앞의 랜딩이라는 뜻이지 웹 앱이 "
            "없다는 뜻이 아니다."
        ),
    },
    "hana_bank": {
        "status": WEB_SERVICE,
        "url": "https://www.hanabank.com/",
        "judgment": "은행 웹 뱅킹 진입점이다. 조회·이체가 브라우저에서 일어난다.",
    },
    "hyundai_card": {
        "status": WEB_SERVICE,
        "url": "https://www.hyundaicard.com/",
        "judgment": (
            "카드사 웹 서비스 진입점이다. 기본 TLS posture 로는 접속되지 않아(서버가 legacy "
            "renegotiation 을 요구) 호환 posture 로 한 번 더 시도해 200 을 받았다. 두 시도를 "
            "모두 기록했다."
        ),
    },
    "instagram": {
        "status": WEB_SERVICE,
        "url": "https://www.instagram.com/",
        "judgment": "웹 클라이언트 진입점이다. 로그인 후 피드·검색·메시지가 브라우저에서 동작한다.",
    },
    "kakaomap": {
        "status": WEB_SERVICE,
        "url": "https://map.kakao.com/",
        "judgment": "웹 지도 애플리케이션 자체다. 장소 검색·길찾기가 브라우저에서 동작한다.",
    },
    "kakaotalk": {
        "status": OFFICIAL_PRODUCT_PAGE,
        "url": "https://www.kakaocorp.com/page/service/service/KakaoTalk",
        "judgment": (
            "운영사 기업 사이트의 서비스 소개 페이지다. 브라우저에서 대화하는 웹 앱이 없고 "
            "페이지가 하는 일은 기능 소개와 설치 유도다. 카카오톡 전용 등록도메인도 아니다."
        ),
    },
    "kb_pay": {
        "status": OFFICIAL_PRODUCT_PAGE,
        "url": "https://card.kbcard.com/SVC/DVIEW/HSCMCXPRISVC0127",
        "judgment": "카드사 사이트 안의 KB Pay 소개 문서다. 결제 자체는 앱에서 일어난다.",
    },
    "kb_starbanking": {
        "status": OFFICIAL_PRODUCT_PAGE,
        "url": "https://omoney.kbstar.com/quics?page=C028156",
        "judgment": (
            "은행 사이트 안의 KB스타뱅킹 **앱 이용안내** 페이지다. 은행의 웹 뱅킹은 별도 "
            "사이트이며 그것은 이 앱과 다른 채널이다."
        ),
    },
    "monimo": {
        "status": OFFICIAL_PRODUCT_PAGE,
        "url": "https://www.monimo.com/",
        "judgment": (
            "운영사 소유 도메인의 브랜드 페이지임을 확인했다. 다만 JS 렌더링이라 초기 응답에서 "
            "웹 애플리케이션 진입점인지까지는 확인하지 못했다 — 관측한 범위에서는 소개 페이지다."
        ),
        "extra_review_reason": "WEB_APP_ENTRY_NOT_CONFIRMED_JS_RENDERED",
    },
    "my_files": {
        "status": SYSTEM_APP,
        "evidence_url": "https://galaxystore.samsung.com/detail/com.sec.android.app.myfiles?langCd=ko",
        "judgment": (
            "단말 파일 관리 구성요소로, 확인된 것은 제조사 스토어 등록 페이지와 고객지원 "
            "문서뿐이다. 공개 웹 랜딩 개념이 성립하지 않는다."
        ),
        "absence_check": (
            "탐색 단계에서 삼성전자 공식 앱 소개 색인(samsung.com/sec/apps/)의 등재 앱 페이지를 "
            "전수 확인했고 '내 파일' 페이지가 없음을 확인했다. 직접 요청한 후보 3건은 Galaxy "
            "Store 등록 페이지·Play Store 등록 페이지·삼성전자서비스 FAQ 였다. 선탑재라는 "
            "사실 자체는 근거로 쓰지 않았다."
        ),
    },
    "naver_app": {
        "status": WEB_SERVICE,
        "url": "https://www.naver.com/",
        "judgment": "포털 서비스 본체가 브라우저에서 그대로 동작한다.",
    },
    "naver_map": {
        "status": WEB_SERVICE,
        "url": "https://map.naver.com/",
        "judgment": (
            "웹 지도 애플리케이션 자체다. 초기 HTML 에 제목이 없는 JS 앱이라 제목 근거는 "
            "얻지 못했고, 확인한 것은 응답과 최종 경로다."
        ),
    },
    "netflix": {
        "status": WEB_SERVICE,
        "url": "https://www.netflix.com/",
        "judgment": "웹 플레이어 진입점이다. 로그인 후 브라우저에서 재생이 일어난다.",
    },
    "nh_cok_bank": {
        "status": UNRESOLVED,
        "evidence_url": "https://banking.nonghyup.com/nhbank.html",
        "judgment": (
            "NH콕뱅크 전용 공식 랜딩을 찾지 못했다. 확인된 운영사 웹 자산은 농협은행 "
            "인터넷뱅킹 사이트인데, 콕뱅크는 상호금융(지역농축협) 앱이라 같은 서비스로 "
            "볼 근거가 없다. 도메인이 같다는 이유로 붙이면 06 §4-2 가 경고한 identity 오탐이 "
            "된다. 확인 불가를 제외로 바꾸지 않는다."
        ),
    },
    "nh_smart_banking": {
        "status": WEB_SERVICE,
        "url": "https://banking.nonghyup.com/nhbank.html",
        "judgment": (
            "농협은행 인터넷뱅킹 진입점이며 앱과 같은 조회·이체 기능을 브라우저에서 수행한다. "
            "다만 '앱 이름' 과 '은행 웹 채널' 을 같은 서비스로 본 판정이므로 identity 를 "
            "사람이 한 번 봐야 한다."
        ),
        "extra_review_reason": "APP_TO_WEB_COUNTERPART_IDENTITY",
    },
    "samsung_calculator": {
        "status": SYSTEM_APP,
        "evidence_url": "https://galaxystore.samsung.com/detail/com.sec.android.app.popupcalculator?langCd=ko",
        "judgment": (
            "단말 기본 유틸리티로, 확인된 것은 제조사 스토어 등록 페이지와 제3자 스토어 "
            "등록 페이지뿐이다. 공개 웹 랜딩 개념이 성립하지 않는다."
        ),
        "absence_check": (
            "탐색 단계에서 삼성전자 공식 앱 소개 색인(samsung.com/sec/apps/)의 등재 앱 페이지를 "
            "전수 확인했고 '계산기' 페이지가 없음을 확인했다. 직접 요청한 후보 2건은 Galaxy "
            "Store 와 Play Store 등록 페이지였다. 선탑재라는 사실 자체는 근거로 쓰지 않았다."
        ),
    },
    "samsung_card": {
        "status": WEB_SERVICE,
        "url": "https://www.samsungcard.com/",
        "judgment": "카드사 웹 서비스 진입점이다. 이용내역 조회·카드 신청이 브라우저에서 일어난다.",
    },
    "samsung_internet_browser": {
        "status": OFFICIAL_PRODUCT_PAGE,
        "url": "https://www.samsung.com/sec/apps/samsung-browser/",
        "judgment": (
            "제조사 공식 앱 소개 페이지다. 06 §2-3 의 두 번째 경로로 선탑재 가설을 해소한다 — "
            "랜딩이 없는 것이 아니라 소개 페이지가 있는 것이다."
        ),
    },
    "samsung_notes": {
        "status": OFFICIAL_PRODUCT_PAGE,
        "url": "https://www.samsung.com/sec/apps/samsung-notes/",
        "judgment": "제조사 공식 앱 소개 페이지다. 메모 작성은 앱에서만 일어난다.",
    },
    "samsung_wallet": {
        "status": OFFICIAL_PRODUCT_PAGE,
        "url": "https://www.samsung.com/sec/apps/samsung-wallet/",
        "judgment": "제조사 공식 앱 소개 페이지다. 결제·카드 등록은 앱에서만 일어난다.",
    },
    "shinhan_sol_bank": {
        "status": WEB_SERVICE,
        "url": "https://bank.shinhan.com/",
        "judgment": (
            "은행 웹 뱅킹 진입점이며 앱과 같은 조회·이체 기능을 브라우저에서 수행한다. "
            "앱 이름과 은행 웹 채널을 같은 서비스로 본 판정이라 identity 확인이 필요하다."
        ),
        "extra_review_reason": "APP_TO_WEB_COUNTERPART_IDENTITY",
    },
    "tiktok": {
        "status": WEB_SERVICE,
        "url": "https://www.tiktok.com/",
        "judgment": (
            "웹 클라이언트 진입점이며 브라우저에서 영상 재생이 동작한다. 초기 HTML 에 제목이 "
            "없는 JS 앱이라 제목 근거는 얻지 못했다."
        ),
    },
    "tiktok_lite": {
        "status": APP_ONLY,
        "evidence_url": "https://ads.tiktok.com/help/article/about-tiktok-lite-japan-and-korea",
        "judgment": (
            "운영사 문서가 한국·일본 한정 앱임을 설명할 뿐 소비자용 웹 랜딩이 없다. "
            "확인된 나머지는 제3자 스토어 등록 페이지다."
        ),
    },
    "tmap": {
        "status": OFFICIAL_PRODUCT_PAGE,
        "url": "https://www.tmapmobility.com/",
        "judgment": (
            "운영사 서비스 소개 사이트다. 브라우저에서 쓰는 웹 지도·내비게이션이 없다. "
            "브랜드 도메인(tmap.co.kr)이 이 사이트로 이동하는 것도 관측했다."
        ),
    },
    "toss": {
        "status": OFFICIAL_PRODUCT_PAGE,
        "url": "https://toss.im/",
        "judgment": "브랜드 소개 페이지이며 송금·조회 같은 핵심 기능은 앱에서만 일어난다.",
    },
    "v3_mobile_plus": {
        "status": OFFICIAL_PRODUCT_PAGE,
        "url": "https://www.ahnlab.com/ko/product/v3-mobile-plus",
        "judgment": "운영사 제품 소개 페이지다. 보안 검사는 단말 앱에서만 일어난다.",
    },
    "youtube": {
        "status": WEB_SERVICE,
        "url": "https://www.youtube.com/",
        "judgment": "웹 플레이어 본체다. 탐색·재생이 브라우저에서 그대로 동작한다.",
    },
    # ── RETAIL 도메인 ───────────────────────────────────────────────────────
    "baemin": {
        "status": OFFICIAL_PRODUCT_PAGE,
        "url": "https://baemin.com/",
        "judgment": "브랜드 소개 페이지다. 주문이라는 핵심 기능은 앱에서만 일어난다.",
    },
    "cj_onstyle": {
        "status": WEB_SERVICE,
        "url": "https://www.cjonstyle.com/",
        "judgment": "홈쇼핑 온라인몰 본체다. 같은 등록도메인 안에서 상품 탐색·구매가 동작한다.",
    },
    "compose_coffee": {
        "status": RETAIL_OFFLINE_ONLY,
        "url": "https://composecoffee.com/",
        "judgment": (
            "매장·메뉴 안내 중심의 브랜드 사이트다. A1 이 잰 카드 결제는 오프라인 매장에서 "
            "일어나며 이 랜딩에서 일어나지 않는다."
        ),
    },
    "costco": {
        "status": WEB_SERVICE,
        "url": "https://www.costco.co.kr/",
        "judgment": (
            "한국 법인이 운영하는 온라인몰 본체다. 상품 탐색·구매가 브라우저에서 동작한다. "
            "다만 A1 이 잰 결제 상당 부분은 창고형 매장 오프라인 결제일 수 있다."
        ),
    },
    "coupang_eats": {
        "status": OFFICIAL_PRODUCT_PAGE,
        "url": "https://www.coupangeats.com/",
        "judgment": (
            "브랜드 소개 페이지다. 주문은 앱에서 일어나고, 같은 도메인의 다른 경로는 "
            "점주용 포털이라 소비자 랜딩이 아니다."
        ),
    },
    "coupang_retail": {
        "status": WEB_SERVICE,
        "url": "https://www.coupang.com/",
        "judgment": (
            "APP 도메인의 coupang_app 과 같은 커머스 사이트다. 우리 요청은 봇 차단(403)으로 "
            "막혀 랜딩 화면 자체를 보지 못했다."
        ),
    },
    "cu": {
        "status": RETAIL_OFFLINE_ONLY,
        "url": "https://cu.bgfretail.com/",
        "judgment": (
            "운영사 사이트의 편의점 브랜드 안내다. 카드 결제는 오프라인 점포에서 일어난다."
        ),
    },
    "daiso": {
        "status": WEB_SERVICE,
        "url": "https://www.daisomall.co.kr/",
        "judgment": (
            "브랜드의 소비자 거래 사이트다(온라인몰). 브랜드 소개 사이트(daiso.co.kr)도 "
            "따로 있으나 A1 이 잰 것이 소비자 결제이므로 거래 사이트를 랜딩으로 잡는다."
        ),
    },
    "emart": {
        "status": WEB_SERVICE,
        "url": "https://emart.ssg.com/",
        "judgment": (
            "브랜드의 소비자 거래 사이트다. 다만 등록도메인이 브랜드 도메인(emart.com)이 "
            "아니라 계열 온라인몰 운영사 도메인(ssg.com)이라 identity 확인이 필요하다."
        ),
        "extra_review_reason": "OPERATOR_DOMAIN_DIFFERS_FROM_BRAND_DOMAIN",
    },
    "emart24": {
        "status": RETAIL_OFFLINE_ONLY,
        "url": "https://emart24.co.kr/",
        "judgment": "편의점 브랜드의 매장 안내 사이트다. 카드 결제는 오프라인 점포에서 일어난다.",
    },
    "gmarket_auction": {
        "status": UNRESOLVED,
        "evidence_url": "https://www.auction.co.kr/",
        "judgment": (
            "A1 원문 표기 'G마켓/옥션' 이 두 브랜드를 한 셀에 묶었는데, 두 브랜드는 각각 "
            "별개의 랜딩을 갖는다 — gmarket.co.kr 과 auction.co.kr 이고 PSL 로 판정한 "
            "등록도메인이 서로 다르다. 어느 한쪽을 이 measurement_entity 의 단일 공식 랜딩으로 "
            "고를 근거가 없다. 확인 불가를 제외로 바꾸지 않는다."
        ),
    },
    "gs25": {
        "status": RETAIL_OFFLINE_ONLY,
        "url": "https://www.gsretail.com/brand/gs25",
        "judgment": "운영사 사이트의 편의점 브랜드 안내다. 카드 결제는 오프라인 점포에서 일어난다.",
    },
    "gs_homeshopping_gsshop": {
        "status": WEB_SERVICE,
        "url": "https://www.gsshop.com/",
        "judgment": (
            "홈쇼핑 온라인몰 본체다. 원문 표기의 두 이름(GS홈쇼핑 · GS Shop)은 같은 채널의 "
            "두 호칭이며 하나의 사이트로 귀결된다."
        ),
    },
    "home_and_shopping": {
        "status": WEB_SERVICE,
        "url": "https://www.hnsmall.com/",
        "judgment": "홈쇼핑 온라인몰 본체다. 상품 탐색·구매가 브라우저에서 동작한다.",
    },
    "homeplus": {
        "status": WEB_SERVICE,
        "url": "https://mfront.homeplus.co.kr/",
        "judgment": (
            "브랜드의 소비자 거래 사이트다. 브랜드 도메인(www.homeplus.co.kr)이 같은 "
            "등록도메인 안에서 이 경로로 이동하는 것을 관측했다."
        ),
    },
    "hyundai_department_store": {
        "status": RETAIL_OFFLINE_ONLY,
        "url": "https://www.ehyundai.com/",
        "judgment": (
            "백화점 점포·행사 안내 사이트다. 계열 온라인몰이 별도 등록도메인으로 존재하지만 "
            "이 브랜드 표기의 단일 거래 랜딩으로 확정할 근거를 얻지 못했다."
        ),
        "extra_review_reason": "SEPARATE_ONLINE_MALL_NOT_RESOLVED",
    },
    "hyundai_homeshopping_hmall": {
        "status": WEB_SERVICE,
        "url": "https://www.hmall.com/",
        "judgment": (
            "홈쇼핑 온라인몰 본체다. 페이지 제목이 원문 표기의 두 이름을 그대로 이어 붙인 "
            "'현대홈쇼핑 - 현대Hmall' 이라 C012 의 MERGE 판정과도 어긋나지 않는다."
        ),
    },
    "kakao_t": {
        "status": OFFICIAL_PRODUCT_PAGE,
        "url": "https://service.kakaomobility.com/launch/kakaot/",
        "judgment": "운영사 서비스 소개 페이지다. 호출·결제는 앱에서만 일어난다.",
    },
    "korean_air": {
        "status": UNRESOLVED,
        "evidence_url": "https://www.koreanair.com/",
        "judgment": (
            "탐색 단계에서 www.koreanair.com 이 공식 사이트로 지목됐으나 우리 요청은 20초·45초 "
            "두 번 모두 read timeout 으로 끝나 랜딩을 확인하지 못했다. 검색 결과만으로 확정하지 "
            "않는다(06 §3-2). 확인 불가를 제외로 바꾸지 않는다."
        ),
    },
    "lotte_department_store": {
        "status": RETAIL_OFFLINE_ONLY,
        "url": "https://www.lotteshopping.com/main",
        "judgment": (
            "백화점 점포·기업 안내 사이트다. 온라인 거래는 계열 통합몰 안의 한 관으로 "
            "존재해 브랜드 단독 거래 랜딩이 확정되지 않는다."
        ),
        "extra_review_reason": "TRANSACTION_CHANNEL_IS_A_SECTION_OF_A_GROUP_MALL",
    },
    "lotte_himart": {
        "status": WEB_SERVICE,
        "url": "https://www.e-himart.co.kr/",
        "judgment": "브랜드의 소비자 거래 사이트다. 상품 탐색·구매가 브라우저에서 동작한다.",
    },
    "lotte_homeshopping": {
        "status": WEB_SERVICE,
        "url": "https://www.lotteimall.com/",
        "judgment": (
            "홈쇼핑 온라인몰 본체다. 초기 HTML 에 제목이 없어 제목 근거는 얻지 못했고 "
            "확인한 것은 응답과 등록도메인이다."
        ),
    },
    "lotte_mart": {
        "status": RETAIL_OFFLINE_ONLY,
        "url": "https://company.lottemart.com/",
        "judgment": (
            "브랜드·점포 안내 사이트다. 온라인 거래 채널이 계열 통합몰의 한 관과 별도 브랜드 "
            "몰로 나뉘어 있어 이 표기의 단일 거래 랜딩이 확정되지 않는다."
        ),
        "extra_review_reason": "TRANSACTION_CHANNEL_SPLIT_ACROSS_TWO_SITES",
    },
    "market_kurly": {
        "status": WEB_SERVICE,
        "url": "https://www.kurly.com/",
        "judgment": "온라인 장보기 서비스 본체다. 상품 탐색·구매가 브라우저에서 동작한다.",
    },
    "mega_coffee": {
        "status": RETAIL_OFFLINE_ONLY,
        "url": "https://www.mega-mgccoffee.com/",
        "judgment": (
            "매장·메뉴 안내 중심의 브랜드 사이트다. 카드 결제는 오프라인 매장에서 일어난다. "
            "페이지 제목의 공식 브랜드명이 A1 원문 표기('메가커피')와 달라 identity 확인이 필요하다."
        ),
    },
    "naver_naverpay": {
        "status": UNRESOLVED,
        "evidence_url": "https://pay.naver.com/",
        "judgment": (
            "A1 원문 표기 '네이버/네이버페이' 가 두 브랜드를 한 셀에 묶었는데, 두 브랜드의 "
            "랜딩은 서로 다른 호스트다 — 포털은 www.naver.com, 결제는 pay.naver.com 이고 "
            "후자는 로그인 벽으로 이동한다. 등록도메인은 같지만 랜딩 경험이 다르고 운영 주체도 "
            "갈린다. 어느 한쪽을 단일 공식 랜딩으로 고를 근거가 없다."
        ),
    },
    "nc_dept_newcore_outlet": {
        "status": RETAIL_OFFLINE_ONLY,
        "url": "https://www.elandretail.com/",
        "judgment": (
            "운영사 사이트이며 원문 표기의 두 브랜드(NC백화점 · 뉴코아아울렛)가 같은 사이트로 "
            "귀결된다. 카드 결제는 오프라인 점포에서 일어난다."
        ),
    },
    "nonghyup_hanaro_mart": {
        "status": RETAIL_OFFLINE_ONLY,
        "url": "https://www.nhhanaro.co.kr/",
        "judgment": (
            "하나로마트 브랜드 사이트다. 카드 결제는 오프라인 점포에서 일어난다. "
            "페이지 제목이 브랜드명을 담고 있지 않아 identity 확인이 필요하다."
        ),
    },
    "ns_homeshopping": {
        "status": WEB_SERVICE,
        "url": "https://www.nsmall.com/",
        "judgment": "홈쇼핑 온라인몰 본체다. 상품 탐색·구매가 브라우저에서 동작한다.",
    },
    "paris_baguette_pariscroissant": {
        "status": RETAIL_OFFLINE_ONLY,
        "url": "https://www.paris.co.kr/",
        "judgment": (
            "제과 브랜드의 메뉴·매장 안내 사이트이며 원문 표기의 두 이름이 같은 사이트로 "
            "귀결된다. 카드 결제는 오프라인 매장에서 일어난다."
        ),
    },
    "seven_eleven": {
        "status": RETAIL_OFFLINE_ONLY,
        "url": "https://www.7-eleven.co.kr/",
        "judgment": "편의점 브랜드의 점포·행사 안내 사이트다. 카드 결제는 오프라인 점포에서 일어난다.",
    },
    "shinsegae_department_store": {
        "status": RETAIL_OFFLINE_ONLY,
        "url": "https://www.shinsegae.com/index.do",
        "judgment": (
            "백화점 점포·행사 안내 사이트다. 계열 온라인몰이 별도 등록도메인으로 존재하지만 "
            "이 브랜드 표기의 단일 거래 랜딩으로 확정할 근거를 얻지 못했다."
        ),
        "extra_review_reason": "SEPARATE_ONLINE_MALL_NOT_RESOLVED",
    },
    "top_mart": {
        "status": RETAIL_OFFLINE_ONLY,
        "url": "https://www.seowon.com/",
        "judgment": (
            "확인된 공식 웹 자산은 운영사(서원유통) 사이트이며 그 안에 점포 목록이 있다. "
            "탑마트 브랜드 단독 랜딩은 확인되지 않았고 페이지 제목도 브랜드명을 담지 않는다 — "
            "identity 확인이 필요하다. 카드 결제는 오프라인 점포에서 일어난다."
        ),
    },
}


def load_probes() -> dict[tuple[str, str], dict[str, Any]]:
    payload = json.loads((STATE / "url_review_probe.json").read_text(encoding="utf-8"))
    return {(p["canonical_service_key"], p["target_url"]): p for p in payload["probes"]}


def confidence_of(probe: dict[str, Any] | None) -> str:
    """관측 품질에서 신뢰도를 유도한다. 손으로 올리고 내릴 수 없다."""
    if probe is None or probe.get("error") or probe.get("http_status") is None:
        return "LOW"
    status = int(probe["http_status"])
    if 200 <= status < 400 and probe.get("page_title"):
        return "HIGH"
    if status in BLOCKED_STATUSES or 200 <= status < 400:
        return "MEDIUM"
    return "LOW"


def brand_tokens(name: str, ckey: str, url: str | None) -> list[str]:
    """제목이 브랜드를 확인해 주는지 볼 때 쓸 토큰. **기계적으로만** 만든다.

    입력은 A1 원문 표기(service_name_canonical), canonical_service_key, 그리고 확정 URL 의
    등록도메인 첫 라벨뿐이다. 손으로 별칭을 보태면 검사가 원하는 결과에 맞춰 휘어진다.
    """
    tokens: set[str] = set()
    for part in name.replace("/", " ").split():
        if len(part) >= 2:
            tokens.add(part.lower())
    tokens.add(name.replace("/", "").replace(" ", "").lower())
    for part in ckey.split("_"):
        if len(part) >= 3:
            tokens.add(part)
    tokens.add(ckey.replace("_", ""))
    domain = registered_domain(url) if url else None
    if domain:
        head = domain.split(".")[0]
        tokens.add(head)
        tokens.add(head.replace("-", ""))
    return sorted(t for t in tokens if len(t) >= 2)


def title_identifies_brand(probe: dict[str, Any] | None, tokens: list[str]) -> bool | None:
    """제목에 브랜드 토큰이 있는가. 제목이 없으면 판정하지 않는다(None)."""
    title = (probe or {}).get("page_title")
    if not title:
        return None
    flat = title.lower().replace(" ", "")
    return any(t in title.lower() or t.replace(" ", "") in flat for t in tokens)


def crossed_registered_domain(probe: dict[str, Any] | None) -> bool:
    """최종 URL 이 후보와 다른 등록도메인으로 갔는가 (06 §3-3 QA 큐 조건)."""
    if not probe:
        return False
    target = probe.get("target_registered_domain")
    final = probe.get("final_registered_domain")
    return bool(target and final and target != final)


def evidence_of(probe: dict[str, Any] | None, url: str | None) -> str:
    """06 §3-1 이 요구한 '확인한 근거' — 실제 확인한 URL·페이지 제목·리다이렉트 결과."""
    if url is None:
        return "확정할 URL 이 없다."
    if probe is None:
        return f"{url} — 관측 기록 없음."
    if probe.get("error"):
        return f"{url} — 접속 실패: {probe['error']}"
    parts = [f"{url} → HTTP {probe['http_status']}"]
    if probe.get("final_url") and probe["final_url"] != url:
        parts.append(f"최종 URL {probe['final_url']}")
    hops = probe.get("redirect_chain") or []
    if hops:
        parts.append(f"리다이렉트 {len(hops)}회")
    if probe.get("page_title"):
        parts.append(f"페이지 제목 '{probe['page_title']}'")
    else:
        parts.append("페이지 제목 미획득(봇 차단 또는 비HTML 응답)")
    if probe.get("final_registered_domain"):
        parts.append(f"등록도메인(PSL) {probe['final_registered_domain']}")
    return " · ".join(parts)


def main() -> None:
    service_master = pd.read_parquet(STATE / "service_master.parquet")
    web_target_group = pd.read_parquet(STATE / "web_target_group.parquet")
    candidates = json.loads((STATE / "url_review_candidates.json").read_text(encoding="utf-8"))
    probes = load_probes()
    discovery = {c["canonical_service_key"]: c for c in candidates["candidates"]}

    # 판정 대상은 '지금 NOT_ASSESSED 인 것' 이 아니라 **브랜드 축 entity 전부**다.
    # 현재 상태값을 기준으로 삼으면 이 스크립트가 자기 출력을 입력으로 먹고 두 번째 실행에서
    # 대상이 0건이 된다 — 멱등이 아니게 된다. 업종 축 10건은 C003 에서 확정된 배제다.
    assessable = set(
        service_master.loc[service_master["axis_type"] == "SERVICE_BRAND", "canonical_service_key"]
    )
    missing = sorted(assessable - set(ELIGIBILITY_DECISIONS))
    extra = sorted(set(ELIGIBILITY_DECISIONS) - assessable)
    if missing or extra:
        raise SystemExit(f"판정 대상 불일치 — 누락 {missing} / 잉여 {extra}")

    names = dict(
        zip(
            service_master["canonical_service_key"],
            service_master["service_name_canonical"],
            strict=True,
        )
    )
    group_of = dict(
        zip(
            service_master["canonical_service_key"],
            service_master["web_target_group_id"],
            strict=True,
        )
    )
    key_of_group = dict(
        zip(service_master["canonical_service_key"], service_master["web_target_key"], strict=True)
    )
    id_of = dict(
        zip(service_master["canonical_service_key"], service_master["service_id"], strict=True)
    )

    # ---------------- W3/W4: entity 별 판정과 URL 확정 ----------------
    url_rows: list[dict[str, Any]] = []
    eligibility: dict[str, dict[str, Any]] = {}
    for ckey in sorted(assessable):
        decision = ELIGIBILITY_DECISIONS[ckey]
        status = decision["status"]
        if status not in ALLOWED_STATUS:
            raise SystemExit(f"{ckey}: 허용되지 않은 상태값 {status}")
        if status == EXCLUDED_INDUSTRY_AXIS:
            raise SystemExit(f"{ckey}: 브랜드 축 entity 에 업종 배제를 줄 수 없다")

        url = decision.get("url")
        # 확정 URL 이 없어도 '무엇을 열어보고 그렇게 판정했는가' 는 남는다.
        # 부재 판정(SYSTEM_APP/APP_ONLY)과 미확정(UNRESOLVED)의 근거가 여기에 있다.
        observed = url or decision.get("evidence_url")
        probe = probes.get((ckey, observed)) if observed else None
        if observed and probe is None:
            raise SystemExit(f"{ckey}: {observed} 을 근거로 삼았는데 관측 기록이 없다")

        # 두 가지를 구분한다.
        #   observation_confidence  우리가 그 페이지를 얼마나 확실히 봤는가
        #   url_confidence          그 URL 을 공식 랜딩으로 확정한 것에 대한 신뢰도
        # UNRESOLVED 는 정의상 확정 신뢰도가 없다. 그러나 관측까지 없었던 것은 아니다 —
        # 둘을 뭉개면 '봤는데 확정 못 했다' 와 '보지도 못했다' 가 같은 값이 된다.
        observation_confidence = confidence_of(probe)
        confidence = "LOW" if status == UNRESOLVED else observation_confidence
        evidence = evidence_of(probe, observed)
        disc = discovery[ckey]["discovery"]

        # 06 §2-1 — URL 이 있다는 사실만으로 WEB_SERVICE 가 되지 않는다.
        if status == WEB_SERVICE and not url:
            raise SystemExit(f"{ckey}: WEB_SERVICE 인데 확정 URL 이 없다")
        if status == UNRESOLVED and url:
            raise SystemExit(f"{ckey}: UNRESOLVED 인데 URL 을 확정했다")
        # 06 §2-3 — SYSTEM_APP 은 '공식 웹 랜딩이 없음을 확인' 했을 때만이다.
        if status == SYSTEM_APP and not decision.get("absence_check"):
            raise SystemExit(
                f"{ckey}: SYSTEM_APP 인데 공식 웹 랜딩 부재를 어떻게 확인했는지가 없다. "
                "선탑재 여부 자체는 판정 근거가 아니다(06 §2-3)."
            )

        tokens = brand_tokens(names[ckey], ckey, url)
        brand_ok = title_identifies_brand(probe, tokens)
        blocked = bool(probe and probe.get("http_status") in BLOCKED_STATUSES)
        crossed = crossed_registered_domain(probe)
        review_reasons: list[str] = []
        if status == UNRESOLVED:
            review_reasons.append("STATUS_UNRESOLVED")
        if observation_confidence == "LOW":
            review_reasons.append("NO_OBSERVATION")
        if blocked:
            review_reasons.append("LANDING_NOT_SEEN_BOT_BLOCKED")
        if crossed:
            review_reasons.append("CROSS_REGISTERED_DOMAIN_REDIRECT")
        if brand_ok is False:
            review_reasons.append("TITLE_DOES_NOT_NAME_BRAND")
        # 기계 규칙이 잡지 못하는 미결은 판정자가 **추가만** 할 수 있다. 규칙이 세운 플래그를
        # 끌 수는 없다 — 끌 수 있으면 파생값이 아니라 손입력이 된다.
        if decision.get("extra_review_reason"):
            review_reasons.append(str(decision["extra_review_reason"]))
        needs_review = bool(review_reasons)
        basis = (
            f"{decision['judgment']} "
            f"[기준] {STATUS_CRITERIA[status]} "
            f"[확인] {evidence} "
            f"[탐색] {disc['method']} — 질의 {len(disc['search_queries'])}건, "
            f"검토한 후보 URL {len(discovery[ckey]['candidate_urls'])}건."
        )
        if decision.get("absence_check"):
            basis += f" [부재확인] {decision['absence_check']}"
        if review_reasons:
            basis += f" [미결사유] {','.join(review_reasons)}"
        eligibility[ckey] = {
            "web_eligibility_status": status,
            "eligibility_basis": basis,
            "eligibility_reviewer": REVIEWER,
            "eligibility_confidence": confidence,
            "eligibility_reviewed_at": REVIEWED_AT,
            "eligibility_needs_review": needs_review,
        }

        url_rows.append(
            {
                "web_target_group_id": group_of[ckey],
                "web_target_key": key_of_group[ckey],
                "service_id": id_of[ckey],
                "canonical_service_key": ckey,
                "service_name_canonical": names[ckey],
                "web_eligibility_status": status,
                "official_landing_url": url,
                "observed_url": observed,
                "resolved_final_url": probe.get("final_url") if probe else None,
                "redirect_chain": json.dumps(
                    probe.get("redirect_chain") if probe else [], ensure_ascii=False
                ),
                "http_status": probe.get("http_status") if probe else None,
                "page_title": probe.get("page_title") if probe else None,
                "registered_domain": (
                    registered_domain(probe["final_url"])
                    if probe and probe.get("final_url")
                    else None
                ),
                "url_type": STATUS_TO_URL_TYPE[status],
                "url_discovery_method": disc["method"],
                "url_evidence": evidence,
                "url_reviewer": REVIEWER,
                "url_confidence": confidence,
                "observation_confidence": observation_confidence,
                "reviewed_at": REVIEWED_AT,
                "review_status": "NEEDS_HUMAN_REVIEW" if needs_review else "REVIEWED",
                "review_reasons": ",".join(review_reasons),
                "brand_token_in_title": brand_ok,
                "cross_registered_domain_redirect": crossed,
                "tls_compat_retry": bool(probe and probe.get("tls_compat_retry")),
                "review_note": decision["judgment"],
            }
        )

    url_review = pd.DataFrame(url_rows).sort_values("canonical_service_key", ignore_index=True)
    bad_type = set(url_review["url_type"]) - ALLOWED_URL_TYPE
    assert not bad_type, f"허용되지 않은 url_type: {bad_type}"

    # ---------------- W5: web_target_group 승격/해체 ----------------
    landing_of = dict(
        zip(url_review["canonical_service_key"], url_review["official_landing_url"], strict=True)
    )
    status_of = dict(
        zip(url_review["canonical_service_key"], url_review["web_eligibility_status"], strict=True)
    )

    new_status: list[str] = []
    outcomes: list[str] = []
    outcome_basis: list[str] = []
    confirmed_by_url: list[bool] = []
    group_url: list[str | None] = []
    group_evidence: list[str | None] = []

    for rec in web_target_group.itertuples():
        members = rec.member_canonical_keys.split(",")
        landings = [landing_of.get(m) for m in members]
        statuses = [status_of.get(m) for m in members]
        web_service = [s == WEB_SERVICE for s in statuses]

        if rec.member_count == 1:
            member = members[0]
            if statuses[0] == UNRESOLVED:
                new_status.append(GROUPING_SINGLETON_PENDING)
                basis = (
                    f"{member}: URL 을 확정하지 못했다. 확인 불가를 제외로 바꾸지 않는다"
                    "(06 §2-3) — 그룹도 미확정으로 둔다."
                )
                url_value = None
            elif web_service[0]:
                new_status.append(GROUPING_SINGLETON_CONFIRMED)
                basis = f"{member}: WEB_SERVICE 랜딩 {landings[0]} 이 확정됐다."
                url_value = landings[0]
            else:
                new_status.append(GROUPING_SINGLETON_NOT_A_WEB_TARGET)
                basis = (
                    f"{member}: 검토 결과 {statuses[0]} 다. 주 분석이 쓰는 web_target 이 "
                    "성립하지 않는다 — '아직 안 봤다' 와 구별해 기록한다."
                )
                url_value = None
            outcomes.append(HYP_NA_SINGLETON)
            outcome_basis.append(basis)
            # 단독 그룹에는 '그룹 내부 URL 관계' 가 없다. 관계 가설이 없으므로 확정도 없다 —
            # URL 이 잡혔다는 사실은 grouping_status 와 web_target_url 이 말한다.
            confirmed_by_url.append(False)
            group_url.append(url_value)
            group_evidence.append(
                None
                if url_value is None
                else url_review.loc[
                    url_review["canonical_service_key"] == members[0], "url_evidence"
                ].iloc[0]
            )
            continue

        # 후보 그룹 — 가설을 URL 로 검정한다.
        reviewed = [(m, landing_of.get(m), status_of.get(m)) for m in members]
        distinct = {u for _m, u, _s in reviewed if u}
        unresolved_members = [m for m, _u, s in reviewed if s == UNRESOLVED]

        if unresolved_members and not distinct - {None}:
            new_status.append(GROUPING_CANDIDATE)
            outcomes.append(HYP_NOT_TESTED)
            outcome_basis.append(
                f"member {unresolved_members} 의 URL 이 미확정이라 가설을 검정하지 못했다."
            )
            confirmed_by_url.append(False)
            group_url.append(None)
            group_evidence.append(None)
            continue

        if all(web_service) and len(distinct) == 1:
            shared = next(iter(distinct))
            new_status.append(GROUPING_CONFIRMED_SHARED)
            outcomes.append(HYP_CONFIRMED)
            outcome_basis.append(
                f"member {members} 의 확정 랜딩이 모두 {shared} 로 같다. "
                "SAME_LANDING_EXPECTED 가설이 URL 로 확인됐다 — 이 그룹은 관측을 1회만 한다."
            )
            confirmed_by_url.append(True)
            group_url.append(shared)
            group_evidence.append(
                url_review.loc[
                    url_review["canonical_service_key"] == members[0], "url_evidence"
                ].iloc[0]
            )
            continue

        # 남은 경우는 전부 '같은 랜딩이 아니다' 다.
        new_status.append(GROUPING_SPLIT)
        detail = "; ".join(f"{m}={u or '(확정 URL 없음)'}[{s}]" for m, u, s in reviewed)
        if unresolved_members:
            outcomes.append(HYP_FALSIFIED_NO_SINGLE)
            outcome_basis.append(
                f"SAME_LANDING_EXPECTED 가설이 **틀렸다.** {detail}. "
                "가설은 두 member 가 각각 하나의 랜딩을 갖고 그것이 같다고 전제했는데, "
                f"{unresolved_members} 는 원문 표기가 서로 다른 랜딩 둘을 묶은 것이어서 "
                "단일 URL 자체가 성립하지 않는다. 전제가 무너졌으므로 그룹을 해체한다."
            )
        else:
            outcomes.append(HYP_FALSIFIED_DIFFERENT)
            outcome_basis.append(
                f"SAME_LANDING_EXPECTED 가설이 **틀렸다.** {detail}. "
                "선언해 둔 반증 조건(서로 다른 등록도메인 또는 다른 경로로 확정되면 SPLIT)이 "
                "충족됐다. 그룹을 해체한다."
            )
        confirmed_by_url.append(False)
        group_url.append(None)
        group_evidence.append(None)

    web_target_group = web_target_group.assign(
        grouping_status=new_status,
        hypothesis_outcome=outcomes,
        hypothesis_outcome_basis=outcome_basis,
        expected_url_relationship_confirmed_by_url=confirmed_by_url,
        web_target_url=group_url,
        url_evidence=group_evidence,
        url_reviewed_at=REVIEWED_AT,
        url_reviewer=REVIEWER,
    )
    bad_group = set(web_target_group["grouping_status"]) - ALLOWED_GROUPING_STATUS
    assert not bad_group, f"허용되지 않은 grouping_status: {bad_group}"
    bad_outcome = set(web_target_group["hypothesis_outcome"]) - ALLOWED_HYPOTHESIS_OUTCOME
    assert not bad_outcome, f"허용되지 않은 hypothesis_outcome: {bad_outcome}"

    # 틀린 가설을 조용히 지우지 않는다 — 선언문과 반증 결과가 같은 행에 남아 있어야 한다.
    for rec in web_target_group.itertuples():
        if rec.expected_url_relationship_is_hypothesis:
            assert rec.expected_url_relationship_falsifier, (
                f"{rec.web_target_key}: 가설인데 반증 조건이 지워졌다"
            )
            assert rec.hypothesis_outcome != HYP_NA_SINGLETON
    confirmed = web_target_group["expected_url_relationship_confirmed_by_url"]
    assert (web_target_group.loc[confirmed, "web_target_url"].notna()).all(), (
        "URL 없이 가설이 확정으로 표시된 그룹이 있다"
    )
    assert web_target_group.loc[confirmed, "hypothesis_outcome"].eq(HYP_CONFIRMED).all(), (
        "가설 확정 표시와 검정 결과가 어긋난다"
    )
    # web_target_url 은 그룹 상태와 정확히 대응한다 — 확정된 그룹만 URL 을 갖는다(06 §3-4).
    has_url = web_target_group["web_target_url"].notna()
    should = web_target_group["grouping_status"].isin(
        {GROUPING_CONFIRMED_SHARED, GROUPING_SINGLETON_CONFIRMED}
    )
    assert has_url.equals(should), (
        "web_target_url 과 grouping_status 가 어긋난다: "
        f"{web_target_group.loc[has_url != should, 'web_target_key'].tolist()}"
    )

    # ---------------- service_master 에 06 §2-2 근거 필드를 얹는다 ----------------
    industry_basis = (
        "fig07_t1 의 축은 표 헤더가 '업종' 인 업종 카테고리다. 브랜드가 아니므로 웹 수집 "
        "대상에서 제외한다."
    )
    columns = [
        "web_eligibility_status",
        "eligibility_basis",
        "eligibility_reviewer",
        "eligibility_confidence",
        "eligibility_reviewed_at",
        "eligibility_needs_review",
    ]
    filled: dict[str, list[Any]] = {c: [] for c in columns}
    for rec in service_master.itertuples():
        if rec.axis_type == "INDUSTRY_CATEGORY":
            values = {
                "web_eligibility_status": EXCLUDED_INDUSTRY_AXIS,
                "eligibility_basis": industry_basis,
                "eligibility_reviewer": "exec-agent(C003) / fig07.png 직접 판독",
                "eligibility_confidence": "HIGH",
                "eligibility_reviewed_at": "2026-08-26",
                "eligibility_needs_review": False,
            }
        else:
            values = eligibility[rec.canonical_service_key]
        for c in columns:
            filled[c].append(values[c])
    service_master = service_master.assign(**filled)
    assert "web_eligibility_basis" not in service_master.columns, (
        "C012 의 한 칸짜리 근거가 06 §2-2 필드와 공존한다 — 어느 쪽이 정본인지 흐려진다"
    )

    bad_status = set(service_master["web_eligibility_status"]) - ALLOWED_STATUS
    assert not bad_status, f"허용되지 않은 web_eligibility_status: {bad_status}"
    assert "NOT_ASSESSED" not in set(service_master["web_eligibility_status"])
    # 두 층의 미결 플래그는 별도 컬럼이다 (ssot C012 지적).
    assert "needs_human_review" in service_master.columns
    assert "eligibility_needs_review" in service_master.columns
    for rec in service_master.itertuples():
        if rec.web_eligibility_status == UNRESOLVED:
            assert rec.eligibility_needs_review, (
                f"{rec.canonical_service_key}: UNRESOLVED 인데 미결이 아니다"
            )
        assert rec.eligibility_basis and rec.eligibility_reviewer and rec.eligibility_confidence

    # service_master ↔ url_review ↔ web_target_group 정합
    brand = service_master[service_master["axis_type"] == "SERVICE_BRAND"]
    assert set(brand["canonical_service_key"]) == set(url_review["canonical_service_key"])
    joined = brand.set_index("canonical_service_key")["web_eligibility_status"]
    for rec in url_review.itertuples():
        assert joined[rec.canonical_service_key] == rec.web_eligibility_status
        assert STATUS_TO_URL_TYPE[rec.web_eligibility_status] == rec.url_type
        if rec.official_landing_url:
            assert rec.registered_domain, f"{rec.canonical_service_key}: 등록도메인 판정 실패"

    group_members = {
        rec.web_target_group_id: rec.member_canonical_keys.split(",")
        for rec in web_target_group.itertuples()
    }
    for rec in web_target_group.itertuples():
        if rec.grouping_status == GROUPING_CONFIRMED_SHARED:
            urls = {landing_of[m] for m in group_members[rec.web_target_group_id]}
            assert len(urls) == 1 and rec.web_target_url in urls

    # ---------------- 저장 ----------------
    for name, df in [
        ("service_master", service_master),
        ("web_target_group", web_target_group),
        ("url_review", url_review),
    ]:
        df.to_parquet(STATE / f"{name}.parquet", index=False)
        df.to_csv(STATE / f"{name}.csv", index=False, encoding="utf-8-sig")

    ledger = {
        "schema": "web_eligibility_and_url_review/v1",
        "generated_by": (
            "research/landing_accessibility/scripts/build_web_eligibility_and_url_review.py"
        ),
        "reviewed_at": REVIEWED_AT,
        "reviewer": REVIEWER,
        "authority": "직접 접속 확인 (state/url_review_probe.json)",
        "principles": {
            "no_status_from_url_existence_alone": (
                "URL 이 존재한다는 사실만으로 WEB_SERVICE 로 두지 않는다(06 §2-1). "
                "상태값은 그 URL 에서 서비스의 핵심 기능을 브라우저로 쓸 수 있는가로 갈린다."
            ),
            "system_app_requires_absence_check": (
                "SYSTEM_APP 확정은 공식 웹 랜딩이 없음을 실제 확인했을 때만이다(06 §2-3). "
                "선탑재 여부 자체는 판정 근거가 아니다. 이 스크립트는 "
                "state/_researcher_priors/system_app_hypothesis.json 을 읽지 않는다."
            ),
            "unresolved_is_not_exclusion": (
                "확인 불가는 UNRESOLVED + eligibility_needs_review=true 이며 제외로 바꾸지 않는다."
            ),
            "no_url_invention": (
                "추측으로 URL 을 만들지 않고 검색 1위를 자동 채택하지 않는다(06 §3-2). "
                "검색은 후보를 얻는 수단이고 확정은 직접 접속 결과로 한다."
            ),
            "status_criteria": STATUS_CRITERIA,
            "retail_landing_selection": RETAIL_LANDING_SELECTION_RULE,
            "confidence_is_derived": CONFIDENCE_RULE,
            "needs_review_is_derived": NEEDS_REVIEW_RULE,
            "psl_only": (
                "등록도메인은 Public Suffix List 파서로만 판정한다(06 §3-3). 마지막 두 라벨 "
                "문자열 비교는 .co.kr/.or.kr/.go.kr 에서 무관한 사이트를 같은 도메인으로 오판한다."
            ),
            "two_layer_review_flags": (
                "measurement 층 needs_human_review 와 web 층 eligibility_needs_review 는 "
                "별도 컬럼이다. 한 칸을 공유하면 어느 층의 미결인지 구별되지 않는다."
            ),
        },
        "psl": psl_provenance(),
        "e001_boundary": (
            "URL 확인은 수집이 아니다(06 §6). evidence/ 아래에 어떤 파일도 만들지 않았고 "
            "DOM/AX/screen/probe 를 저장하지 않았다."
        ),
        "status_distribution": service_master["web_eligibility_status"].value_counts().to_dict(),
        "url_type_distribution": url_review["url_type"].value_counts().to_dict(),
        "confidence_distribution": url_review["url_confidence"].value_counts().to_dict(),
        "needs_review": sorted(
            service_master.loc[service_master["eligibility_needs_review"], "canonical_service_key"]
        ),
        "grouping_status_distribution": web_target_group["grouping_status"]
        .value_counts()
        .to_dict(),
        "hypothesis_outcomes": [
            {
                "web_target_key": rec.web_target_key,
                "members": rec.member_canonical_keys.split(","),
                "expected_url_relationship": rec.expected_url_relationship,
                "declared_as_hypothesis": bool(rec.expected_url_relationship_is_hypothesis),
                "declared_falsifier": rec.expected_url_relationship_falsifier,
                "declared_risk": rec.expected_url_relationship_risk,
                "outcome": rec.hypothesis_outcome,
                "outcome_basis": rec.hypothesis_outcome_basis,
                "grouping_status": rec.grouping_status,
                "web_target_url": rec.web_target_url,
            }
            for rec in web_target_group[
                web_target_group["expected_url_relationship_is_hypothesis"]
            ].itertuples()
        ],
        "hypothesis_note": (
            "틀린 가설을 지우지 않는다. 선언문(expected_url_relationship / falsifier / risk)과 "
            "검정 결과(hypothesis_outcome)를 같은 행에 남긴다 — 무엇을 예상했고 무엇이 "
            "틀렸는지가 이 연구의 자산이다."
        ),
        "decisions": [
            {
                "canonical_service_key": rec.canonical_service_key,
                "service_name_canonical": rec.service_name_canonical,
                "web_eligibility_status": rec.web_eligibility_status,
                "official_landing_url": rec.official_landing_url,
                "resolved_final_url": rec.resolved_final_url,
                "registered_domain": rec.registered_domain,
                "http_status": rec.http_status,
                "page_title": rec.page_title,
                "url_type": rec.url_type,
                "url_confidence": rec.url_confidence,
                "review_status": rec.review_status,
                "judgment": rec.review_note,
                "url_evidence": rec.url_evidence,
            }
            for rec in url_review.itertuples()
        ],
    }
    (STATE / "url_review_ledger.json").write_text(
        json.dumps(ledger, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    print("web_eligibility_status:")
    print(service_master["web_eligibility_status"].value_counts().to_string())
    print(f"\nurl_review           : {len(url_review)} 행")
    print(url_review["url_type"].value_counts().to_string())
    print("url_confidence:")
    print(url_review["url_confidence"].value_counts().to_string())
    print(f"\nweb_target_group     : {len(web_target_group)} 그룹 (수 불변)")
    print(web_target_group["grouping_status"].value_counts().to_string())
    print("\n후보 3건 가설 검정:")
    for h in ledger["hypothesis_outcomes"]:
        print(f"  {h['web_target_key']:<10} {h['outcome']:<40} → {h['grouping_status']}")
    nr = ledger["needs_review"]
    print(f"\neligibility_needs_review: {len(nr)}")
    for k in nr:
        print(f"  - {k}")


if __name__ == "__main__":
    main()
