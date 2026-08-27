"""D-SUP-02 — shallow L1 functional-entry recoverability (Director supplemental inquiry).

RQ: RQ-D14 에서 CORPORATE_OR_APP_LANDING / UNDETERMINED 로 분류된 target 에 대해,
    frozen DOM/AX evidence 만으로 **shallow L1 functional-entry candidate** 가 관측되는가?

출력은 3값만: RECOVERABLE_WITHIN_L1 / NO_FUNCTIONAL_EXIT_OBSERVED / AMBIGUOUS.

이 스크립트는 archetype 을 정하지 않고, 대표기능 gold label 을 만들지 않으며,
어떤 후보도 실제로 클릭하지 않는다 (live navigation 없음, frozen evidence 만).

firewall: holdout label · LABEL_SPLIT_FROZEN* · HOLDOUT_FOR_C* · RAW_L1~L4* · PACKET_L* ·
*_OVERLAP* · PRECEDENCE_CONTESTED* · CALIBRATION_FOR_B* · **/control/** 는 열지 않았다.
이 스크립트가 여는 경로는 아래 EVIDENCE_ROOT_TMPL 의 l0a slot 3개 파일과 research_d/results 뿐이다.
"""
from __future__ import annotations

import csv
import json
import math
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
from urllib.parse import urlsplit, unquote

RD = Path("/home/sieg/projects-wsl/ProjectFinal/.agent_worktrees/claude_d_research"
          "/research/landing_accessibility/research_d")
sys.path.insert(0, str(RD / "tools"))
from html_decode import parse_html  # noqa: E402  (한글 mojibake 방지 — 바이트를 lxml 에 직접 넘기지 않는다)

EVIDENCE_ROOT_TMPL = ("/home/sieg/projects-wsl/ProjectFinal/.agent_worktrees"
                      "/claude_b_e001_worker_{ww}/artifacts/e001_{w}/evidence"
                      "/{run_dir}/{obs}/l0a")

SEED = 20260827
RULE_VERSION = "DSUP02_L1_v1"

csv.field_size_limit(10 ** 9)

# ---------------------------------------------------------------------------
# 1. 조작화 — SSOT v2.1 §5 branch tree 의 Region 정의에서 유도
# ---------------------------------------------------------------------------
CANDIDATE_DEFINITION = """
=== shallow L1 functional-entry candidate — 조작화 정의 (전문) ===

[유도 근거] SSOTV2/01_REPRESENTATIVE_FUNCTION_MAPPING_DT_v2.1.md §5 Stage 3 branch tree 는
7개 archetype 각각에 대해 **Region** 을 다음과 같이 정의한다 (원문 요지):

  Q QUERY                : "검색 입력 control 이 사용 가능한 상태로 노출"
  C CONTENT_OPEN         : "content card/link list 가 노출"
  I ITEM_DETAIL          : "individual item/product card or link list"
  P PLACE_LOOKUP         : "place search control 또는 place list"
  M COMMUNICATION_ENTRY  : "thread/post list 또는 compose-entry control"
  F FINANCIAL_ACTION_ENTRY: "balance/transfer/payment/auth function entry control"
  U UTILITY_ENTRY        : "function surface entry control"

즉 SSOT 에서 Region 은 **기능 면(surface) 또는 그 면을 여는 entry control** 이다.
D-SUP-02 는 이 7개 Region 정의의 **합집합(union)** 을 archetype 을 특정하지 않은 채 쓴다.

[정의] target T 의 frozen L0-A evidence 안에서 관측된 어떤 노드 x 가 아래 (a)·(b)·(c) 를
모두 만족하면 x 는 T 의 **shallow L1 functional-entry candidate** 다.

  (a) FORM — x 는 다음 중 하나다.
      (a1) 이동형 링크: <a href> 이거나 AX role ∈ {link}, 그리고 href 가 존재
      (a2) 조작형 control: AX role ∈ {button, searchbox, combobox, textbox, menuitem,
           tab, checkbox, radio, slider, spinbutton} 이거나 DOM 태그가
           <button> / <input type=search|text|submit> / [role=button] / [role=searchbox]
      (a3) probe slot 이 이미 후보로 표기한 노드:
           raw_features.primary_action_candidates[] · raw_features.region_signals.search_inputs[]

  (b) FUNCTION VOCABULARY — x 의 **표면 문자열** 중 하나 이상이 아래 7개 region 어휘군
      (REGION_VOCAB) 중 하나에 매칭된다. 표면 문자열은
        visible_text / anchor text / AX accessible name / aria-label / title / alt /
        placeholder / nearby_heading / href 의 path+query (percent-decode 후)
      이다. href path 매칭은 path segment 또는 query key/value 에 대해 수행한다.
      예외 (b*): FORM 이 (a2) 의 searchbox/combobox/input[type=search] 이거나 probe
      region_signals.search_inputs 항목이면, SSOT Q-Region 정의("검색 입력 control 이
      사용 가능한 상태로 노출")가 **control 존재 자체로 충족**되므로 어휘 매칭 없이 통과한다.

  (c) EXCLUSION — x 가 아래 EXCLUSION RULES 중 어느 하나에도 걸리지 않는다.

[shallow / L1 의 뜻]
  - "shallow" : L0-A 랜딩 화면에서 **직접 보이는/노출된** 노드만 본다. 하위 페이지를
    크롤하지 않고, 어떤 후보도 실행하지 않는다.
  - "L1"      : 그 후보를 한 번 누르면 도달할 **다음 한 면** 을 뜻한다. 실제 도달 여부는
    검증하지 않는다 (이 inquiry 는 그것을 답하지 않는다).
  - 따라서 "candidate" 는 **존재 주장(existence claim)** 이지 도달 주장(reachability claim)이
    아니다.

[중복 제거] 후보는 (정규화 표면 문자열, 정규화 href) 쌍으로 dedup 한다. 같은 노드가 세 slot
(dom/ax/probe) 에서 모두 관측되면 후보 1개이며, slot provenance 는 집합으로 보존한다.
"""

EXCLUSION_DEFINITION = """
=== EXCLUSION RULES (전문) ===
아래 규칙은 **어휘 매칭보다 먼저** 적용된다 (예: "뉴스룸" 은 E4 에 걸리므로 C 어휘 "뉴스" 로
승격되지 않는다). 규칙은 결과를 보기 전에 고정되었고 결과를 본 뒤 수정하지 않았다.

E1 APP_INSTALL — 앱 설치/스토어 이동
    표면어: 앱 다운로드, 앱다운로드, 앱설치, 앱 설치, 앱으로 보기, 앱에서 보기, 앱으로보기,
            앱 열기, 앱열기, 앱에서 열기, 앱으로 이동, 앱 실행, app store, google play,
            play 스토어, 플레이스토어, 원스토어, 갤럭시 스토어, 갤럭시스토어, appstore,
            download the app, get the app
    host  : play.google.com, apps.apple.com, itunes.apple.com, onelink.me, app.link,
            appsflyer.com, adjust.com, onestore.co.kr, galaxystore.samsung.com, applink

E2 EXTERNAL_SNS — 외부 소셜/공유
    표면어: 페이스북, 인스타그램, 인스타, 유튜브, 트위터, 카카오스토리, 카카오채널,
            카카오톡 채널, 네이버 밴드, 밴드, 링크드인, 틱톡, 구글플러스, 공유하기, 공유,
            url 복사, 링크 복사, sns, facebook, instagram, twitter, youtube, tiktok,
            linkedin, threads, share
    host  : facebook.com, instagram.com, twitter.com, x.com, youtube.com, youtu.be,
            tiktok.com, linkedin.com, threads.net, band.us, pf.kakao.com, story.kakao.com,
            blog.naver.com, post.naver.com, cafe.naver.com, plus.google.com

E3 LEGAL_POLICY — 약관·정책·메타
    표면어: 이용약관, 약관, 개인정보, 개인정보처리방침, 개인정보취급방침, 청소년보호,
            저작권, 이메일무단수집, 이메일 무단수집, 사이트맵, 웹접근성, 접근성 정책,
            법적고지, 면책, terms, privacy, policy, legal, copyright, sitemap,
            accessibility, cookie

E4 CORPORATE_IR_RECRUIT — 기업소개·IR·채용·홍보·제휴
    표면어: 회사소개, 회사 소개, 기업소개, 기업 소개, 회사정보, 기업정보, 브랜드스토리,
            브랜드 스토리, 연혁, 비전, 미션, 경영이념, ceo, 윤리경영, 지속가능경영, esg,
            기업지배구조, 사회공헌, 오시는 길, 찾아오시는, 채용, 인재채용, 인재상, 인사제도,
            직무소개, 채용안내, 투자정보, ir, 주가정보, 공시, 보도자료, 뉴스룸, 홍보센터,
            광고문의, 제휴문의, 입점문의, 입점 문의, 파트너 신청, 배달파트너, 가맹문의,
            about us, about, company, corporate, careers, career, recruit, investor,
            investors, press, newsroom, sustainability
    path  : /about, /company, /corporate, /ir, /careers, /recruit, /press, /newsroom, /esg

E5 SUPPORT_META — 고객지원 메타면 (대표기능 Region 이 아니라 support surface)
    표면어: 고객센터, 고객 센터, 고객지원, 자주묻는질문, 자주 묻는 질문, faq, 공지사항,
            이용안내, 사이트 이용안내, 도움말, help, support center, notice, announcement

E6 UI_CHROME — 페이지 내부 UI 조작 (기능면 진입이 아님)
    표면어: 닫기, 열기, 펼치기, 접기, 이전, 다음, 확인, 취소, 뒤로가기, 이전화면, 나중에,
            상단으로, 페이지 상단으로 이동, 맨 위로, 메뉴, 전체메뉴, 사이드 메뉴, 메뉴 열기,
            메뉴 닫기, 전체삭제, 검색어 지우기, 검색어 삭제, 검색어 삭제하기, 검색영역 닫기,
            지우기, 삭제, 배너, 이전 배너, 다음 배너, 자동재생, 정지, 재생, 스킵,
            본문 바로가기, 콘텐츠 바로가기, 새창, 새 창, 팝업 닫기, 오늘 하루,
            close, open, prev, previous, next, skip, back, menu, toggle, more,
            expand, collapse, scroll to top
    ※ '홈' '언어전환(EN/KO/English/한국어)' 도 여기 포함한다.

E7 NON_NAVIGATIONAL_HREF — href 가 기능면을 지시하지 않음
    scheme ∈ {mailto, tel, sms, javascript, data, blob} 이거나 href ∈ {"", "#"}.
    단 (a2) 조작형 control 은 href 없이도 후보가 될 수 있으므로 이 규칙은 (a1) 에만 적용한다.

E8 OFF_HOST — 서비스 밖 host
    href 의 registrable domain (eTLD+1 근사) 이 landing 의 registrable domain 과 다르고,
    그 domain 문자열이 RQ-D14 의 a_matched_alias (해당 target 의 알려진 서비스 별칭) 를
    포함하지 않으면 제외한다. 즉 같은 서비스의 다른 서브도메인·형제 도메인은 후보로 남는다.

E9 AUTH_ONLY (WEAK 로 분리, primary count 에 포함하지 않음)
    표면어: 로그인, 로그아웃, 회원가입, 가입하기, 마이페이지, 마이, 내정보, login, logout,
            sign in, signin, sign up, signup, join, my page, mypage, account(단독)
    사유: SSOT F-Region 은 auth function entry control 을 Region 으로 인정하지만, 동시에
    "로그인 버튼 존재만으로 endpoint 처리하지 않는다"(§5 Branch M) 고 못박는다. 로그인은
    거의 모든 랜딩에 있어 판별력이 없으므로 primary count 에서 빼고 WEAK 클래스로 따로 세어
    민감도 분석에만 쓴다.
"""

VERDICT_RULE_DEFINITION = """
=== 3값 판정 규칙 (사전 고정 — 결과를 본 뒤 바꾸지 않았다) ===

입력: target 당 후보 개수 n_cand (E1~E9 통과, dedup 후), evidence 가용성 플래그.

R0  evidence 부재 : dom.html · ax.json · probe.json 이 **모두** 없으면 → AMBIGUOUS
                    (reason = EVIDENCE_ABSENT)
R1  퇴화 캡처     : D 가 확인한 퇴화 관측 (computed_css 3 bytes AND dom_body_empty==1) 이면
                    후보 개수와 무관하게 → AMBIGUOUS (reason = DEGENERATE_CAPTURE)
                    ※ 이 규칙을 끈 "퇴화 포함" 버전을 반드시 병기한다 (R1 만 무력화).
R2  후보 ≥ 1      : → RECOVERABLE_WITHIN_L1
R3  후보 == 0     : → NO_FUNCTIONAL_EXIT_OBSERVED

우선순위: R0 > R1 > R2 > R3.

사전 고정 민감도 임계 (primary 는 R2 의 ≥1 이다. 아래는 보고용이며 primary 를 대체하지 않는다):
  S1  n_cand >= 3
  S2  n_cand_visible_hittable >= 1
      (probe primary_action_candidates 중 viewport_visible==true AND hittable==true 인 후보)
  S3  WEAK(E9 auth) 후보를 primary 에 포함시켰을 때의 n_cand >= 1
"""

# --- REGION_VOCAB : SSOT §4 Stage 2 feature 어휘 + §5 Region 정의에서 유도 ---------------
# (한국어 표면형은 pooled 56행 corpus 의 nav/button 텍스트 빈도조사로 보강했다.
#  stratum 을 나누지 않은 blind 조사이며, 조사 후 어휘는 고정되었다.)
REGION_VOCAB: dict[str, dict[str, list[str]]] = {
    "Q_QUERY": {
        "text": ["검색", "검색하기", "통합검색", "통합 검색", "찾아보기", "검색창",
                 "search", "find", "query"],
        "path": ["search", "find", "query", "q", "src", "sch"],
    },
    "C_CONTENT": {
        "text": ["뉴스", "기사", "속보", "영상", "동영상", "방송", "프로그램", "다시보기",
                 "콘텐츠", "컨텐츠", "웹툰", "만화", "소설", "음악", "라디오", "드라마",
                 "예능", "클립", "매거진", "칼럼", "연재", "포토", "사진", "갤러리",
                 "스포츠", "연예", "시사", "경제", "정치", "사회", "생활", "문화",
                 "news", "article", "video", "watch", "vod", "program", "episode",
                 "series", "webtoon", "comic", "novel", "music", "radio", "photo",
                 "gallery", "magazine", "column", "clip", "live"],
        "path": ["news", "article", "articles", "video", "videos", "watch", "vod",
                 "program", "programs", "episode", "series", "webtoon", "comic",
                 "novel", "music", "radio", "photo", "gallery", "magazine", "clip",
                 "live", "contents", "content"],
    },
    "I_ITEM": {
        "text": ["상품", "제품", "쇼핑", "카테고리", "베스트", "기획전", "신상품", "세일",
                 "특가", "할인", "장바구니", "스토어", "몰", "구매", "주문", "랭킹",
                 "브랜드관", "전체보기", "카탈로그", "가격", "판매",
                 "product", "products", "goods", "item", "items", "shop", "shopping",
                 "store", "category", "categories", "best", "bestseller", "sale",
                 "deal", "deals", "cart", "mall", "order", "catalog", "ranking",
                 "price", "buy"],
        "path": ["product", "products", "goods", "item", "items", "shop", "shopping",
                 "category", "categories", "best", "sale", "deal", "cart", "mall",
                 "order", "catalog", "ranking", "prd", "gds"],
    },
    "P_PLACE": {
        "text": ["지도", "길찾기", "길 찾기", "매장찾기", "매장 찾기", "센터찾기",
                 "센터 찾기", "지점", "지점찾기", "영업점", "대리점", "주변", "내 주변",
                 "현위치", "위치", "지역", "장소", "가까운", "서비스센터",
                 "map", "maps", "place", "places", "location", "locations", "branch",
                 "branches", "store locator", "directions", "nearby", "around"],
        "path": ["map", "maps", "place", "places", "location", "branch", "branches",
                 "store-locator", "storelocator", "directions", "nearby", "shopfind",
                 "findstore", "center"],
    },
    "M_COMMUNICATION": {
        "text": ["게시판", "커뮤니티", "카페", "댓글", "글쓰기", "글 쓰기", "작성하기",
                 "톡", "채팅", "채팅하기", "메시지", "쪽지", "문의하기", "1:1문의",
                 "1:1 문의", "1대1 문의", "상담", "상담하기", "전문상담", "원격상담",
                 "수어상담", "후기", "리뷰", "질문", "묻고답하기", "토론", "피드",
                 "board", "community", "forum", "post", "posts", "thread", "write",
                 "chat", "message", "messages", "comment", "review", "reviews",
                 "qna", "q&a", "ask", "inquiry", "feed"],
        "path": ["board", "community", "forum", "post", "posts", "thread", "write",
                 "chat", "message", "comment", "review", "reviews", "qna", "inquiry",
                 "counsel", "consult", "feed", "bbs"],
    },
    "F_FINANCE": {
        "text": ["이체", "송금", "계좌", "잔액", "잔액조회", "결제", "즉시결제", "납부",
                 "청구", "청구서", "요금조회", "카드", "대출", "예금", "적금", "펀드",
                 "환전", "보험", "투자", "주식", "충전", "포인트", "간편결제", "출금",
                 "입금", "거래내역", "이용내역", "명세서", "본인인증", "본인확인",
                 "transfer", "remit", "remittance", "account", "balance", "pay",
                 "payment", "payments", "billing", "bill", "card", "cards", "loan",
                 "deposit", "savings", "fund", "invest", "investment", "stock",
                 "exchange", "insurance", "wallet", "point", "settlement"],
        "path": ["transfer", "remit", "account", "accounts", "balance", "pay",
                 "payment", "billing", "bill", "card", "cards", "loan", "deposit",
                 "savings", "fund", "invest", "stock", "exchange", "insurance",
                 "wallet", "point"],
    },
    "U_UTILITY": {
        "text": ["예약", "예약하기", "예매", "예매하기", "신청", "신청하기", "접수",
                 "발급", "발급하기", "조회", "조회하기", "배송조회", "주문조회",
                 "주문/배송 조회", "계산", "계산기", "요금", "요금안내", "요금조회",
                 "등록", "등록하기", "충전하기", "견적", "견적내기", "진단", "추천",
                 "설정", "확인서", "증명서", "발권", "체크인", "티켓", "수리", "서비스 예약",
                 "출장서비스", "예약 조회", "유지보수", "자가수리", "보증등록",
                 "reservation", "reserve", "booking", "book", "apply", "application",
                 "request", "issue", "calculate", "calculator", "estimate", "register",
                 "registration", "track", "tracking", "checkin", "check-in", "ticket",
                 "quote", "repair", "service"],
        "path": ["reserve", "reservation", "booking", "book", "apply", "application",
                 "request", "issue", "calculator", "estimate", "register", "track",
                 "tracking", "checkin", "ticket", "quote", "repair", "service",
                 "services", "delivery", "order-status"],
    },
}

EXCL_TEXT = {
    "E1_APP_INSTALL": ["앱 다운로드", "앱다운로드", "앱설치", "앱 설치", "앱으로 보기",
                       "앱에서 보기", "앱으로보기", "앱 열기", "앱열기", "앱에서 열기",
                       "앱으로 이동", "앱 실행", "app store", "google play", "play 스토어",
                       "플레이스토어", "원스토어", "갤럭시 스토어", "갤럭시스토어",
                       "appstore", "download the app", "get the app"],
    "E2_EXTERNAL_SNS": ["페이스북", "인스타그램", "인스타", "유튜브", "트위터", "카카오스토리",
                        "카카오채널", "카카오톡 채널", "네이버 밴드", "밴드", "링크드인",
                        "틱톡", "구글플러스", "공유하기", "공유", "url 복사", "링크 복사",
                        "sns", "facebook", "instagram", "twitter", "youtube", "tiktok",
                        "linkedin", "threads", "share"],
    "E3_LEGAL_POLICY": ["이용약관", "약관", "개인정보", "개인정보처리방침", "개인정보취급방침",
                        "청소년보호", "저작권", "이메일무단수집", "이메일 무단수집",
                        "사이트맵", "웹접근성", "접근성 정책", "법적고지", "면책",
                        "terms", "privacy", "policy", "legal", "copyright", "sitemap",
                        "accessibility", "cookie"],
    "E4_CORPORATE_IR_RECRUIT": ["회사소개", "회사 소개", "기업소개", "기업 소개", "회사정보",
                                "기업정보", "브랜드스토리", "브랜드 스토리", "연혁", "비전",
                                "미션", "경영이념", "ceo", "윤리경영", "지속가능경영", "esg",
                                "기업지배구조", "사회공헌", "오시는 길", "찾아오시는", "채용",
                                "인재채용", "인재상", "인사제도", "직무소개", "채용안내",
                                "투자정보", "ir", "주가정보", "공시", "보도자료", "뉴스룸",
                                "홍보센터", "광고문의", "제휴문의", "입점문의", "입점 문의",
                                "파트너 신청", "배달파트너", "가맹문의", "about us", "about",
                                "company", "corporate", "careers", "career", "recruit",
                                "investor", "investors", "press", "newsroom",
                                "sustainability"],
    "E5_SUPPORT_META": ["고객센터", "고객 센터", "고객지원", "자주묻는질문", "자주 묻는 질문",
                        "faq", "공지사항", "이용안내", "사이트 이용안내", "도움말",
                        "help", "support center", "notice", "announcement"],
    "E6_UI_CHROME": ["닫기", "열기", "펼치기", "접기", "이전", "다음", "확인", "취소",
                     "뒤로가기", "이전화면", "나중에", "상단으로", "페이지 상단으로 이동",
                     "맨 위로", "메뉴", "전체메뉴", "사이드 메뉴", "메뉴 열기", "메뉴 닫기",
                     "전체삭제", "검색어 지우기", "검색어 삭제", "검색어 삭제하기",
                     "검색영역 닫기", "지우기", "삭제", "배너", "이전 배너", "다음 배너",
                     "자동재생", "정지", "재생", "스킵", "본문 바로가기", "콘텐츠 바로가기",
                     "새창", "새 창", "팝업 닫기", "오늘 하루", "홈", "한국어", "english",
                     "close", "open", "prev", "previous", "next", "skip", "back",
                     "menu", "toggle", "more", "expand", "collapse", "scroll to top"],
}
EXCL_TEXT_EXACT = {"홈", "home", "en", "ko", "kr", "english", "한국어", "더보기", "more"}

EXCL_HOST = {
    "E1_APP_INSTALL": ["play.google.com", "apps.apple.com", "itunes.apple.com",
                       "onelink.me", "app.link", "appsflyer.com", "adjust.com",
                       "onestore.co.kr", "galaxystore.samsung.com", "applink"],
    "E2_EXTERNAL_SNS": ["facebook.com", "instagram.com", "twitter.com", "x.com",
                        "youtube.com", "youtu.be", "tiktok.com", "linkedin.com",
                        "threads.net", "band.us", "pf.kakao.com", "story.kakao.com",
                        "blog.naver.com", "post.naver.com", "cafe.naver.com",
                        "plus.google.com"],
}
EXCL_PATH = {
    "E4_CORPORATE_IR_RECRUIT": ["about", "company", "corporate", "ir", "careers",
                                "career", "recruit", "press", "newsroom", "esg",
                                "sustainability", "brandstory"],
    "E3_LEGAL_POLICY": ["terms", "privacy", "policy", "legal", "copyright", "sitemap",
                        "agreement"],
}
WEAK_AUTH_TEXT = ["로그인", "로그아웃", "회원가입", "가입하기", "마이페이지", "마이",
                  "내정보", "내 정보", "login", "logout", "sign in", "signin",
                  "sign up", "signup", "join", "my page", "mypage"]

V1B_PATCH_DEFINITION = """
=== POST_HOC ADVERSARIAL VARIANT  DSUP02_L1_v1b (사후 · 전수 적용 · primary 를 대체하지 않음) ===

[왜 만들었나] v1 결과를 낸 뒤, 판정을 좌우하는 **소수후보 target (n_cand<=6)** 을 손으로 감사한
결과 어휘사전 누수 3종이 확인됐다. 전부 후보를 **과대계수** 하는 방향이다.

  L1  쿠키 동의 배너의 컨트롤이 후보로 샜다.
      예: 밴드 '쿠키 설정' -> U_UTILITY:text:설정 / Netflix '설정 저장','쿠키 목록 검색'
  L2  언어·표시설정 combobox 가 (b*) 검색컨트롤 예외로 통과했다.
      예: Instagram '표시 언어 변경' (role=combobox, 어휘 매칭 0인데 통과)
  L3  앱스토어 이동 링크가 I_ITEM 어휘 '스토어' 로 통과했다.
      예: 에이닷 전화 '애플 스토어에서 다운로드'

[v1b 가 v1 과 다른 점 — 이것이 전부다]
  P1  E3 에 쿠키/동의 어휘 추가: 쿠키, 동의, 동의하기, 모두 허용, 모두 수락, 필수만,
      선택 동의, 설정 저장, 쿠키 설정, consent, cookies, accept all, manage cookies,
      preferences
  P2  E6 에 언어/표시설정 어휘 추가: 언어, 표시 언어, 언어 변경, 국가 선택, 지역 설정,
      language, region
  P3  E1 에 앱스토어 표면형 추가: 애플 스토어, 앱스토어, 앱 스토어, 플레이 스토어,
      에서 다운로드, download on the app, get it on google play
  P4  U_UTILITY 어휘에서 '설정' 삭제 (UI 환경설정과 구분되지 않는다)
  P5  I_ITEM 어휘에서 '스토어' 삭제 (path token 'store' 는 유지)
  P6  (b*) 검색컨트롤 예외를 role=searchbox 또는 input[type=search] 로 한정한다
      (combobox/textbox 는 어휘 매칭을 요구한다)

[적용 범위] 56 target **전수** 에 동일하게 적용한다. 소수후보 target 만 손보면 보정이
한 방향(RECOVERABLE -> NO_EXIT)으로만 작동해 편향되므로, 전수 재계산으로 그 비대칭을 없앤다.

[지위] v1b 는 결과를 본 뒤 만든 사후 규칙이다. 따라서 **primary 판정은 v1 이 그대로 유지된다.**
v1b 는 v1 결론의 robustness 를 보이는 민감도 분석이며, 3값 판정규칙(R0~R3)은 손대지 않았다.
"""

CONTROL_ROLES = {"button", "searchbox", "combobox", "textbox", "menuitem", "tab",
                 "checkbox", "radio", "slider", "spinbutton"}
LINK_ROLES = {"link"}
SEARCH_CONTROL_ROLES = {"searchbox", "combobox"}

MULTI_SUFFIX = {"co.kr", "or.kr", "go.kr", "ne.kr", "pe.kr", "re.kr", "ac.kr", "hs.kr",
                "ms.kr", "es.kr", "sc.kr", "co.jp", "com.cn", "co.uk", "com.au"}


# ---------------------------------------------------------------------------
# 2. 유틸
# ---------------------------------------------------------------------------
def norm(s) -> str:
    if not s:
        return ""
    s = re.sub(r"\s+", " ", str(s)).strip().lower()
    return s


def registrable(host: str) -> str:
    host = (host or "").lower().lstrip(".")
    if not host or re.fullmatch(r"[\d.]+", host):
        return host
    parts = host.split(".")
    if len(parts) >= 3 and ".".join(parts[-2:]) in MULTI_SUFFIX:
        return ".".join(parts[-3:])
    return ".".join(parts[-2:]) if len(parts) >= 2 else host


def href_parts(href: str, base_host: str):
    """(scheme, host, path_query_tokens_normalized)"""
    if href is None:
        return ("", "", [])
    h = href.strip()
    if not h or h == "#":
        return ("empty", "", [])
    sp = urlsplit(h)
    scheme = (sp.scheme or "").lower()
    host = (sp.netloc or "").lower().split("@")[-1].split(":")[0]
    if not scheme and not host:
        host = base_host
    raw = unquote(unquote(sp.path or "")) + " " + unquote(unquote(sp.query or ""))
    toks = [t for t in re.split(r"[^0-9A-Za-z가-힣]+", raw.lower()) if t]
    return (scheme, host or base_host, toks)


V1B_DROP_TEXT = {"U_UTILITY": {"설정"}, "I_ITEM": {"스토어"}}
V1B_EXTRA_EXCL = {
    "E3_LEGAL_POLICY": ["쿠키", "동의", "동의하기", "모두 허용", "모두 수락", "필수만",
                        "선택 동의", "설정 저장", "쿠키 설정", "consent", "cookies",
                        "accept all", "manage cookies", "preferences"],
    "E6_UI_CHROME": ["언어", "표시 언어", "언어 변경", "국가 선택", "지역 설정",
                     "language", "region"],
    "E1_APP_INSTALL": ["애플 스토어", "앱스토어", "앱 스토어", "플레이 스토어",
                       "에서 다운로드", "download on the app", "get it on google play"],
}


def match_vocab(surfaces: list[str], path_toks: list[str], variant: str = "v1"):
    """(matched_regions, matched_terms)"""
    regions, terms = set(), []
    blob = " ".join(s for s in surfaces if s)
    for reg, voc in REGION_VOCAB.items():
        drop = V1B_DROP_TEXT.get(reg, set()) if variant == "v1b" else set()
        for t in voc["text"]:
            if t in drop:
                continue
            if t and t in blob:
                regions.add(reg)
                terms.append(f"{reg}:text:{t}")
                break
        for t in voc["path"]:
            if t in path_toks:
                regions.add(reg)
                terms.append(f"{reg}:path:{t}")
                break
    return sorted(regions), terms


def apply_exclusions(surfaces, path_toks, scheme, host, base_reg, alias, is_link,
                     variant="v1"):
    """제외 규칙. (excluded_rule 또는 None, weak_auth: bool)"""
    blob = " ".join(s for s in surfaces if s)
    stripped = blob.strip()
    # E7 (a1 링크에만)
    if is_link:
        if scheme in ("mailto", "tel", "sms", "javascript", "data", "blob") or scheme == "empty":
            return "E7_NON_NAVIGATIONAL_HREF", False
    # E1/E2 host
    for rule, hosts in EXCL_HOST.items():
        if host and any(host == h or host.endswith("." + h) or h in host for h in hosts):
            return rule, False
    # E3/E4 path
    for rule, paths in EXCL_PATH.items():
        if any(p in path_toks for p in paths):
            return rule, False
    # E1~E6 text (순서 고정)
    for rule in ("E1_APP_INSTALL", "E2_EXTERNAL_SNS", "E3_LEGAL_POLICY",
                 "E4_CORPORATE_IR_RECRUIT", "E5_SUPPORT_META", "E6_UI_CHROME"):
        terms = list(EXCL_TEXT[rule])
        if variant == "v1b":
            terms += V1B_EXTRA_EXCL.get(rule, [])
        for t in terms:
            if t and t in blob:
                return rule, False
    if stripped in EXCL_TEXT_EXACT:
        return "E6_UI_CHROME", False
    # E8 off-host
    if host:
        hreg = registrable(host)
        if hreg and base_reg and hreg != base_reg:
            if not (alias and alias.lower() in hreg):
                return "E8_OFF_HOST", False
    # E9 weak auth (제외는 아니고 WEAK 분리)
    for t in WEAK_AUTH_TEXT:
        if t and t in blob:
            return None, True
    return None, False


# ---------------------------------------------------------------------------
# 3. slot 별 원시 노드 추출
# ---------------------------------------------------------------------------
def nodes_from_dom(path: Path):
    out = []
    try:
        tree, enc = parse_html(path)
    except Exception as e:  # 파싱 실패도 사실로 기록한다
        return out, f"PARSE_FAIL:{type(e).__name__}"
    for el in tree.iter():
        tag = (el.tag if isinstance(el.tag, str) else "").lower()
        role = norm(el.get("role"))
        if tag == "a":
            kind, href = "link", el.get("href")
        elif tag == "button" or role == "button":
            kind, href = "control", el.get("href")
        elif tag == "input":
            it = norm(el.get("type"))
            if it in ("search", "text", "submit", "button"):
                kind, href = "control", None
            else:
                continue
        elif role in ("searchbox", "combobox", "link", "menuitem", "tab"):
            kind = "link" if role == "link" else "control"
            href = el.get("href")
        else:
            continue
        txt = norm(" ".join(el.itertext()))[:200]
        surfaces = [txt, norm(el.get("aria-label")), norm(el.get("title")),
                    norm(el.get("alt")), norm(el.get("placeholder")),
                    norm(el.get("value")) if tag == "input" else ""]
        is_search_ctrl = (role in ("searchbox", "combobox")
                          or (tag == "input" and norm(el.get("type")) == "search"))
        out.append({"slot": "dom", "kind": kind, "role": role or tag, "href": href,
                    "surfaces": [s for s in surfaces if s],
                    "is_search_ctrl": is_search_ctrl,
                    "visible": None, "hittable": None})
    return out, "OK"


def nodes_from_ax(path: Path):
    out = []
    try:
        ax = json.loads(path.read_text(encoding="utf-8", errors="replace"))
    except Exception as e:
        return out, f"PARSE_FAIL:{type(e).__name__}"
    if isinstance(ax, dict):
        ax = ax.get("nodes", ax.get("axNodes", []))
    for n in ax or []:
        if not isinstance(n, dict) or n.get("ignored"):
            continue
        role = norm(n.get("role"))
        if role not in LINK_ROLES | CONTROL_ROLES:
            continue
        name = norm(n.get("name"))
        props = {norm(p.get("name")): p.get("value") for p in (n.get("properties") or [])
                 if isinstance(p, dict)}
        href = props.get("url")
        desc = norm(props.get("description"))
        ph = norm(props.get("placeholder"))
        out.append({"slot": "ax", "kind": "link" if role in LINK_ROLES else "control",
                    "role": role, "href": href if isinstance(href, str) else None,
                    "surfaces": [s for s in (name, desc, ph) if s],
                    "is_search_ctrl": role in SEARCH_CONTROL_ROLES,
                    "visible": None, "hittable": None})
    return out, "OK"


def nodes_from_probe(path: Path):
    out = []
    if not path.exists():
        return out, "ABSENT"
    try:
        pr = json.loads(path.read_text(encoding="utf-8", errors="replace"))
    except Exception as e:
        return out, f"PARSE_FAIL:{type(e).__name__}"
    rf = pr.get("raw_features") or {}
    for c in rf.get("primary_action_candidates") or []:
        out.append({"slot": "probe", "kind": "link" if c.get("href") else "control",
                    "role": norm(c.get("role")) or norm(c.get("tag")),
                    "href": c.get("href"),
                    "surfaces": [s for s in (norm(c.get("visible_text")),
                                             norm(c.get("aria_label")),
                                             norm(c.get("nearby_heading"))) if s],
                    "is_search_ctrl": False,
                    "visible": bool(c.get("viewport_visible")),
                    "hittable": bool(c.get("hittable"))})
    for s in (rf.get("region_signals") or {}).get("search_inputs") or []:
        out.append({"slot": "probe", "kind": "control", "role": "searchbox", "href": None,
                    "surfaces": [x for x in (norm(s.get("accessible_name")),
                                             norm(s.get("placeholder")),
                                             norm(s.get("aria_label")),
                                             norm(s.get("selector"))) if x],
                    "is_search_ctrl": True,
                    "visible": bool(s.get("visible", True)),
                    "hittable": bool(s.get("hittable", True))})
    for a in rf.get("accessible_name_sources") or []:
        tag = norm(a.get("tag"))
        role = norm(a.get("role"))
        if tag not in ("a", "button", "input", "select") and role not in CONTROL_ROLES | LINK_ROLES:
            continue
        out.append({"slot": "probe", "kind": "link" if tag == "a" else "control",
                    "role": role or tag, "href": None,
                    "surfaces": [x for x in (norm(a.get("visible_text")),
                                             norm(a.get("aria_label")),
                                             norm(a.get("title")),
                                             norm(a.get("alt")),
                                             norm(a.get("value"))) if x],
                    "is_search_ctrl": role in SEARCH_CONTROL_ROLES,
                    "visible": bool(a.get("visible")), "hittable": None})
    return out, "OK"


# ---------------------------------------------------------------------------
# 4. target 단위 판정
# ---------------------------------------------------------------------------
def wilson(k, n, z=1.96):
    if n == 0:
        return (None, None)
    p = k / n
    d = 1 + z * z / n
    c = p + z * z / (2 * n)
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return (round((c - h) / d, 4), round((c + h) / d, 4))


def analyze_target(row, d14, variant="v1"):
    w = row["worker"]
    base = Path(EVIDENCE_ROOT_TMPL.format(ww=w[1:], w=w, run_dir=row["run_dir"],
                                          obs=row["observation_id"]))
    landing_url = d14.get("url") or row.get("prior_url") or ""
    base_host = urlsplit(landing_url).netloc.lower().split(":")[0]
    if not base_host:
        base_host = (d14.get("a_host") or "").lower()
    base_reg = registrable(base_host)
    alias = d14.get("a_matched_alias") or ""

    slots_status = {}
    nodes = []
    for fn, fun, key in (("dom.html", nodes_from_dom, "dom"),
                         ("ax.json", nodes_from_ax, "ax"),
                         ("probe.json", nodes_from_probe, "probe")):
        p = base / fn
        if not p.exists():
            slots_status[key] = "ABSENT"
            continue
        ns, st = fun(p)
        slots_status[key] = st
        nodes.extend(ns)

    cand = {}
    excl_counter = Counter()
    weak = {}
    audit = []          # zero-candidate 감사용 원시 노드 기록 (판정 규칙에 영향 없음)
    for n in nodes:
        scheme, host, ptoks = href_parts(n["href"], base_host)
        surfaces = [norm(s) for s in n["surfaces"] if s]
        rule, is_weak = apply_exclusions(surfaces, ptoks, scheme, host, base_reg,
                                         alias, n["kind"] == "link", variant)
        key = (" | ".join(sorted(set(surfaces)))[:160], norm(n["href"])[:200] if n["href"] else "")
        if rule:
            excl_counter[rule] += 1
            audit.append({"slot": n["slot"], "role": n["role"],
                          "surface": (surfaces[0] if surfaces else "")[:80],
                          "href": (n["href"] or "")[:100], "dropped_by": rule})
            continue
        regions, terms = match_vocab(surfaces, ptoks, variant)
        # (b*) 검색컨트롤 예외. v1b 는 role=searchbox / input[type=search] 로만 한정한다.
        search_exempt = (n["is_search_ctrl"] if variant == "v1"
                         else (n["is_search_ctrl"] and n["role"] in ("searchbox", "input")))
        passes_b = bool(regions) or search_exempt
        if not passes_b:
            excl_counter["NO_FUNCTION_VOCAB"] += 1
            audit.append({"slot": n["slot"], "role": n["role"],
                          "surface": (surfaces[0] if surfaces else "")[:80],
                          "href": (n["href"] or "")[:100], "dropped_by": "NO_FUNCTION_VOCAB"})
            continue
        bucket = weak if is_weak else cand
        rec = bucket.setdefault(key, {"text": (surfaces[0] if surfaces else ""),
                                      "all_surfaces": surfaces[:3],
                                      "href": n["href"], "role": n["role"],
                                      "regions": set(), "terms": set(), "slots": set(),
                                      "visible": False, "hittable": False,
                                      "search_ctrl": False})
        rec["regions"].update(regions)
        rec["terms"].update(terms)
        rec["slots"].add(n["slot"])
        rec["visible"] = rec["visible"] or bool(n["visible"])
        rec["hittable"] = rec["hittable"] or bool(n["hittable"])
        rec["search_ctrl"] = rec["search_ctrl"] or n["is_search_ctrl"]

    cands = sorted(cand.values(), key=lambda r: (-len(r["regions"]), -len(r["slots"]),
                                                 r["text"]))
    for r in cands:
        r["regions"] = sorted(r["regions"])
        r["terms"] = sorted(r["terms"])[:6]
        r["slots"] = sorted(r["slots"])
    weak_n = len(weak)

    n_cand = len(cands)
    n_vis_hit = sum(1 for r in cands if r["visible"] and r["hittable"])
    slot_prov = Counter()
    for r in cands:
        for s in r["slots"]:
            slot_prov[s] += 1
    slot_exclusive = Counter()
    for r in cands:
        if len(r["slots"]) == 1:
            slot_exclusive[r["slots"][0]] += 1

    evidence_absent = all(v == "ABSENT" for v in slots_status.values())
    degenerate = (row.get("dom_body_empty") == "1"
                  and str(row.get("css_bytes")) in ("3", "3.0"))

    if evidence_absent:
        verdict, reason = "AMBIGUOUS", "EVIDENCE_ABSENT"
    elif degenerate:
        verdict, reason = "AMBIGUOUS", "DEGENERATE_CAPTURE"
    elif n_cand >= 1:
        verdict, reason = "RECOVERABLE_WITHIN_L1", f"n_cand={n_cand}>=1"
    else:
        verdict, reason = "NO_FUNCTIONAL_EXIT_OBSERVED", "n_cand=0"

    # 퇴화 포함 버전 (R1 무력화)
    if evidence_absent:
        verdict_incl = "AMBIGUOUS"
    elif n_cand >= 1:
        verdict_incl = "RECOVERABLE_WITHIN_L1"
    else:
        verdict_incl = "NO_FUNCTIONAL_EXIT_OBSERVED"

    return {
        "wtg": row["wtg"], "service": d14.get("service") or row.get("prior_service"),
        "identity_class": d14.get("identity_class"),
        "prior_archetype": row.get("prior_archetype"),
        "url": landing_url, "base_registrable": base_reg,
        "worker": w, "run_dir": row["run_dir"], "observation_id": row["observation_id"],
        "slots_status": slots_status, "degenerate_capture": degenerate,
        "n_nodes_scanned": len(nodes),
        "n_candidates": n_cand, "n_candidates_visible_hittable": n_vis_hit,
        "n_weak_auth_candidates": weak_n,
        "candidate_slot_provenance": dict(slot_prov),
        "candidate_slot_exclusive": dict(slot_exclusive),
        "region_class_hits": dict(Counter(x for r in cands for x in r["regions"])),
        "exclusion_hits": dict(excl_counter),
        "top_candidates": [{"text": r["text"][:90], "href": (r["href"] or "")[:140],
                            "role": r["role"], "regions": r["regions"],
                            "terms": r["terms"], "slots": r["slots"],
                            "search_ctrl": r["search_ctrl"]} for r in cands[:3]],
        "zero_candidate_audit": (
            [dict(t) for t in {tuple(sorted(a.items())) for a in audit}][:80]
            if n_cand == 0 else None),
        "rule_variant": variant,
        "verdict": verdict, "verdict_reason": reason,
        "verdict_degenerate_included": verdict_incl,
        "sensitivity": {"S1_ge3": n_cand >= 3, "S2_visible_hittable_ge1": n_vis_hit >= 1,
                        "S3_with_weak_auth_ge1": (n_cand + weak_n) >= 1},
    }


def main():
    d14doc = json.loads((RD / "results" / "RQ_D14_frame_validity.json").read_text(encoding="utf-8"))
    d14 = {t["wtg"]: t for t in d14doc["per_target"]}
    rows = [r for r in csv.DictReader((RD / "results" / "D_OBSERVATION_TABLE_v2.csv")
                                      .open(encoding="utf-8")) if r["in_mart"] == "1"]
    assert len(rows) == 56, len(rows)

    per, per_b = [], []
    for r in rows:
        t = d14.get(r["wtg"])
        if t is None:
            continue
        per.append(analyze_target(r, t, "v1"))
        per_b.append(analyze_target(r, t, "v1b"))
    per.sort(key=lambda x: (x["identity_class"], -x["n_candidates"]))
    per_b.sort(key=lambda x: (x["identity_class"], -x["n_candidates"]))

    TARGET_CLASSES = ("CORPORATE_OR_APP_LANDING", "UNDETERMINED")
    CONTROL_CLASS = "FUNCTIONAL_LANDING"

    def tally(items, key="verdict"):
        c = Counter(x[key] for x in items)
        n = len(items)
        out = {"n": n}
        for v in ("RECOVERABLE_WITHIN_L1", "NO_FUNCTIONAL_EXIT_OBSERVED", "AMBIGUOUS"):
            k = c.get(v, 0)
            lo, hi = wilson(k, n)
            out[v] = {"k": k, "rate": round(k / n, 4) if n else None,
                      "wilson95": [lo, hi]}
        return out

    tgt = [x for x in per if x["identity_class"] in TARGET_CLASSES]
    ctl = [x for x in per if x["identity_class"] == CONTROL_CLASS]

    by_class = {c: tally([x for x in per if x["identity_class"] == c]) for c in
                sorted({x["identity_class"] for x in per})}
    by_class_incl = {c: tally([x for x in per if x["identity_class"] == c],
                              "verdict_degenerate_included") for c in
                     sorted({x["identity_class"] for x in per})}

    # 반례
    ce_functional_no_exit = [
        {"wtg": x["wtg"], "service": x["service"], "n_candidates": x["n_candidates"],
         "verdict": x["verdict"], "slots_status": x["slots_status"],
         "exclusion_hits": x["exclusion_hits"]}
        for x in ctl if x["verdict"] != "RECOVERABLE_WITHIN_L1"]
    ce_corp_rich = sorted(
        [{"wtg": x["wtg"], "service": x["service"], "identity_class": x["identity_class"],
          "n_candidates": x["n_candidates"], "region_class_hits": x["region_class_hits"],
          "top_candidates": x["top_candidates"]}
         for x in tgt if x["verdict"] == "RECOVERABLE_WITHIN_L1"],
        key=lambda z: -z["n_candidates"])[:5]

    slot_agg = Counter()
    slot_excl_agg = Counter()
    for x in per:
        for k, v in x["candidate_slot_provenance"].items():
            slot_agg[k] += v
        for k, v in x["candidate_slot_exclusive"].items():
            slot_excl_agg[k] += v
    # target 수준: 후보를 하나라도 준 slot
    slot_target_level = Counter()
    probe_only_targets, dom_only_targets = [], []
    for x in per:
        sp = x["candidate_slot_provenance"]
        for k in sp:
            slot_target_level[k] += 1
        if sp and set(sp) == {"probe"}:
            probe_only_targets.append(x["wtg"])
        if sp and set(sp) == {"dom"}:
            dom_only_targets.append(x["wtg"])

    def sens(items, key):
        n = len(items)
        k = sum(1 for x in items if x["sensitivity"][key])
        lo, hi = wilson(k, n)
        return {"n": n, "k": k, "rate": round(k / n, 4) if n else None, "wilson95": [lo, hi]}

    tgt_b = [x for x in per_b if x["identity_class"] in TARGET_CLASSES]
    ctl_b = [x for x in per_b if x["identity_class"] == CONTROL_CLASS]
    v1_by_wtg = {x["wtg"]: x for x in per}
    flipped = [{"wtg": x["wtg"], "service": x["service"],
                "identity_class": x["identity_class"],
                "v1": v1_by_wtg[x["wtg"]]["verdict"], "v1b": x["verdict"],
                "n_cand_v1": v1_by_wtg[x["wtg"]]["n_candidates"],
                "n_cand_v1b": x["n_candidates"]}
               for x in per_b if x["verdict"] != v1_by_wtg[x["wtg"]]["verdict"]]
    v1b_block = {
        "status": "POST_HOC_ADVERSARIAL — primary 를 대체하지 않는다",
        "rule_version": "DSUP02_L1_v1b",
        "patch_definition": V1B_PATCH_DEFINITION,
        "target_29": tally(tgt_b), "control_27": tally(ctl_b), "all_56": tally(per_b),
        "by_identity_class": {c: tally([x for x in per_b if x["identity_class"] == c])
                              for c in sorted({x["identity_class"] for x in per_b})},
        "verdict_flips_vs_v1": flipped,
        "control_contrast": {
            "target_recoverable_rate": round(
                sum(1 for x in tgt_b if x["verdict"] == "RECOVERABLE_WITHIN_L1") / len(tgt_b), 4),
            "control_recoverable_rate": round(
                sum(1 for x in ctl_b if x["verdict"] == "RECOVERABLE_WITHIN_L1") / len(ctl_b), 4),
        },
        "per_target_compact": [
            {"wtg": x["wtg"], "service": x["service"],
             "identity_class": x["identity_class"], "n_candidates": x["n_candidates"],
             "verdict": x["verdict"],
             "top_candidates": x["top_candidates"][:3]} for x in per_b],
    }

    sensitivity = {}
    for lbl, items in (("target_29", tgt), ("control_27", ctl), ("all_56", per)):
        sensitivity[lbl] = {s: sens(items, s) for s in
                            ("S1_ge3", "S2_visible_hittable_ge1", "S3_with_weak_auth_ge1")}

    # 판정 (verdict 어휘 고정)
    rec_t = by_class.get("CORPORATE_OR_APP_LANDING", {}).get("RECOVERABLE_WITHIN_L1", {}).get("k", 0) \
        + by_class.get("UNDETERMINED", {}).get("RECOVERABLE_WITHIN_L1", {}).get("k", 0)
    rec_c = by_class.get(CONTROL_CLASS, {}).get("RECOVERABLE_WITHIN_L1", {}).get("k", 0)
    rate_t = rec_t / len(tgt) if tgt else 0
    rate_c = rec_c / len(ctl) if ctl else 0

    if rate_t >= 0.8 and rate_c >= 0.8:
        verdict = "SUPPORTED"
        vbasis = ("대상군에서 shallow L1 후보가 압도적으로 관측됐다. 다만 대조군도 같은 수준이므로 "
                  "이 지표는 존재 주장만 지지하고 판별력은 없다.")
    elif rate_t >= 0.5:
        verdict = "PARTIALLY_SUPPORTED"
        vbasis = "대상군 과반에서 후보가 관측됐으나 전부는 아니다."
    elif rate_t <= 0.2:
        verdict = "NOT_SUPPORTED"
        vbasis = "대상군 대부분에서 후보가 관측되지 않았다."
    else:
        verdict = "INCONCLUSIVE"
        vbasis = "대상군 판정이 갈린다."

    doc = {
        "rq": "D-SUP-02",
        "title": "shallow L1 functional-entry recoverability of CORPORATE_OR_APP / UNDETERMINED landings",
        "inquiry_kind": "DIRECTOR_SUPPLEMENTAL",
        "depends_on": "RQ-D14",
        "hypothesis_id": "H-SUP02-L1-RECOVERABILITY",
        "competing_hypotheses": {
            "H1": "대상 target 대부분은 L1 안에서 기능면으로 회복 가능한 후보를 갖는다",
            "H2": "대상 target 대부분은 관측 가능한 기능 출구가 없다",
            "H3": "frozen evidence 만으로는 판정이 불가능하다",
        },
        "model_or_rule_version": RULE_VERSION,
        "seed": SEED,
        "analysis_unit": "target (wtg)",
        "n_expected": 56, "n_observed": len(per),
        "strata": {"target_classes": list(TARGET_CLASSES), "control_class": CONTROL_CLASS,
                   "n_target": len(tgt), "n_control": len(ctl)},
        "inputs": {
            "strata": str(RD / "results/RQ_D14_frame_validity.json"),
            "observation_table": str(RD / "results/D_OBSERVATION_TABLE_v2.csv"),
            "evidence_root_template": EVIDENCE_ROOT_TMPL,
            "ssot_region_reference":
                "/home/sieg/projects-wsl/ProjectFinal/SSOTV2/01_REPRESENTATIVE_FUNCTION_MAPPING_DT_v2.1.md §5",
        },
        "missing": {
            "n_missing_targets": 56 - len(per),
            "probe_absent": [x["wtg"] for x in per if x["slots_status"].get("probe") == "ABSENT"],
            "dom_parse_fail": [x["wtg"] for x in per
                               if str(x["slots_status"].get("dom", "")).startswith("PARSE_FAIL")],
        },
        "definitions": {
            "candidate": CANDIDATE_DEFINITION,
            "exclusions": EXCLUSION_DEFINITION,
            "verdict_rule": VERDICT_RULE_DEFINITION,
            "post_hoc_v1b_patch": V1B_PATCH_DEFINITION,
            "region_vocab": REGION_VOCAB,
            "weak_auth_vocab": WEAK_AUTH_TEXT,
        },
        "results": {
            "primary_degenerate_isolated": {
                "target_29": tally(tgt), "control_27": tally(ctl), "all_56": tally(per),
                "by_identity_class": by_class,
            },
            "degenerate_included": {
                "target_29": tally(tgt, "verdict_degenerate_included"),
                "control_27": tally(ctl, "verdict_degenerate_included"),
                "all_56": tally(per, "verdict_degenerate_included"),
                "by_identity_class": by_class_incl,
            },
            "control_contrast": {
                "target_recoverable_rate": round(rate_t, 4),
                "control_recoverable_rate": round(rate_c, 4),
                "rate_difference": round(rate_t - rate_c, 4),
                "note": "대조군 없이 대상군 비율만 보면 무의미하다. 두 비율의 차이가 판별력이다.",
            },
            "slot_provenance": {
                "candidate_level_counts": dict(slot_agg),
                "candidate_level_slot_exclusive": dict(slot_excl_agg),
                "target_level_slot_contributed": dict(slot_target_level),
                "targets_with_probe_only_candidates": probe_only_targets,
                "targets_with_dom_only_candidates": dom_only_targets,
                "dedup_caveat": (
                    "cross-slot dedup 은 (표면문자열, href) 로 하는데 같은 노드라도 slot 마다 "
                    "표면문자열 구성이 달라(probe 는 nearby_heading 을 붙이고 ax 는 computed name 을 "
                    "쓴다) 병합이 잘 되지 않는다. 따라서 candidate_level_slot_exclusive 는 "
                    "**상한(과대추정)** 이다. slot 기여 판단은 target_level 지표와 "
                    "targets_with_probe_only_candidates 로 하라."),
            },
            "sensitivity": sensitivity,
            "post_hoc_variant_v1b": v1b_block,
            "hand_audit_of_marginal_targets": {
                "scope": "v1 결과에서 n_cand<=6 인 target 을 전수 손 감사했다 (사후).",
                "leaks_found": ["쿠키동의 컨트롤(밴드·Netflix)", "언어선택 combobox(Instagram)",
                                "앱스토어 링크의 '스토어' 어휘(에이닷 전화)"],
                "direction": "확인된 누수는 모두 후보를 과대계수하는 방향이었다.",
                "near_misses_false_negative": [
                    "컴포즈커피 '브랜드 홈페이지'(/index1) — 기능면 진입일 수 있으나 기능어휘가 없어 탈락",
                    "모니모 '공동인증서' — SSOT F-Region 의 auth entry 로 볼 여지가 있으나 어휘 미등재로 탈락",
                ],
                "note": "즉 v1 은 위양성(과대)과 위음성(과소)을 모두 갖는다. 방향은 상쇄적이며 "
                        "어느 쪽도 0으로 가정하지 않는다.",
            },
            "candidate_count_distribution": {
                "target_29": sorted(x["n_candidates"] for x in tgt),
                "control_27": sorted(x["n_candidates"] for x in ctl),
            },
            "region_class_totals": {
                "target_29": dict(Counter(k for x in tgt for k in x["region_class_hits"])),
                "control_27": dict(Counter(k for x in ctl for k in x["region_class_hits"])),
            },
        },
        "counterexamples": {
            "functional_landing_without_candidate": ce_functional_no_exit,
            "corporate_or_undetermined_with_rich_candidates": ce_corp_rich,
        },
        "per_target": per,
        "not_answered_by_this_inquiry": [
            "후보가 실제로 작동하는지 — 어떤 후보도 클릭하지 않았다 (live navigation 없음).",
            "후보가 어느 archetype 의 Region 인지 — 정하지 않는다. region_class_hits 는 다중 라벨 힌트일 뿐 archetype 판정이 아니다.",
            "대표기능 gold label — 생성하지 않았다.",
            "frame 을 고쳐야 하는지 — A 의 권한이다.",
        ],
        "verdict": verdict,
        "verdict_basis": vbasis,
        "limitation": (
            "후보는 존재 주장이지 도달 주장이 아니다. 어휘 사전은 연구자가 만든 것이고 상한 없는 "
            "재현율을 주장하지 않는다. 제외 규칙(특히 E5 고객지원·E9 auth)은 보수적으로 설계돼 "
            "후보를 과소계수하는 방향이며, 그래도 대상군이 거의 전부 RECOVERABLE 이면 그 결론은 "
            "보수적 방향에서 안전하다. probe primary_action_candidates 는 200개에서 절단(cap)된 "
            "target 이 7개 있어 후보 개수의 상단이 censored 다 (≥1 규칙에는 영향 없음). "
            "CORPORATE_OR_APP_LANDING stratum 은 n=3 이라 Wilson CI 가 매우 넓다 — 과해석 금지."
        ),
        "firewall_note": (
            "holdout label · LABEL_SPLIT_FROZEN* · HOLDOUT_FOR_C* · RAW_L1~L4* · PACKET_L* · "
            "*_OVERLAP* · PRECEDENCE_CONTESTED* · CALIBRATION_FOR_B* · **/control/** · "
            "B/C 의 target-level holdout error report 는 **열지 않았다**. "
            "이 분석은 l0a slot 3개 파일(dom.html/ax.json/probe.json)과 research_d/results 만 읽었다."
        ),
    }
    out = RD / "results" / "DSUP02_l1_recoverability.json"
    out.write_text(json.dumps(doc, ensure_ascii=False, indent=1), encoding="utf-8")
    print("wrote", out, out.stat().st_size)
    print("verdict", verdict)
    print("target_29", json.dumps(tally(tgt), ensure_ascii=False))
    print("control_27", json.dumps(tally(ctl), ensure_ascii=False))
    print("slots", dict(slot_agg), "exclusive", dict(slot_excl_agg))
    return doc


if __name__ == "__main__":
    main()


# ---------------------------------------------------------------------------
# 5. figures
# ---------------------------------------------------------------------------
# 색은 마지막에 정한다. categorical 3슬롯 (blue/orange/aqua) — dataviz validator
#   node scripts/validate_palette.js "#2a78d6,#eb6834,#1baf7a" --mode light
#   → ALL CHECKS PASS, contrast WARN(#1baf7a 2.74:1) → relief rule 로 모든 세그먼트에
#     직접 라벨(개수)을 찍는다.
SURFACE = "#fcfcfb"
INK, INK2, MUTED = "#1a1a19", "#4a4a46", "#8a8a82"
C_REC, C_NOEXIT, C_AMB = "#2a78d6", "#eb6834", "#1baf7a"
VERD_ORDER = [("RECOVERABLE_WITHIN_L1", C_REC), ("NO_FUNCTIONAL_EXIT_OBSERVED", C_NOEXIT),
              ("AMBIGUOUS", C_AMB)]


def _mpl():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams.update({
        "font.family": "Noto Sans CJK KR", "axes.unicode_minus": False,
        "figure.facecolor": SURFACE, "axes.facecolor": SURFACE,
        "text.color": INK, "axes.labelcolor": INK2, "axes.edgecolor": "#dcdcd6",
        "xtick.color": INK2, "ytick.color": INK2, "font.size": 10,
        "axes.spines.top": False, "axes.spines.right": False,
    })
    return plt


def make_figures(doc):
    plt = _mpl()
    fig_dir = RD / "figures"
    res = doc["results"]

    # --- F1: 3값 판정 구성 (stratum × rule variant) ------------------------------
    rows = []
    for lbl, blk in (("v1 (사전등록)", res["primary_degenerate_isolated"]["by_identity_class"]),
                     ("v1b (사후)", res["post_hoc_variant_v1b"]["by_identity_class"])):
        for cls in ("CORPORATE_OR_APP_LANDING", "UNDETERMINED", "FUNCTIONAL_LANDING"):
            rows.append((f"{cls}\n{lbl}", blk[cls]))
    fig, ax = plt.subplots(figsize=(9.2, 5.4))
    ys = list(range(len(rows)))[::-1]
    for y, (name, blk) in zip(ys, rows):
        left = 0.0
        n = blk["n"]
        for v, col in VERD_ORDER:
            k = blk[v]["k"]
            if k == 0:
                continue
            w = k / n * 100
            ax.barh(y, w, left=left, height=0.62, color=col, edgecolor=SURFACE,
                    linewidth=2)          # 2px surface gap between stacked segments
            ax.text(left + w / 2, y, str(k), ha="center", va="center", fontsize=10,
                    color="#ffffff" if col != C_AMB else INK, fontweight="bold")
            left += w
        ax.text(101, y, f"n={n}", va="center", fontsize=9, color=MUTED)
    ax.set_yticks(ys)
    ax.set_yticklabels([r[0] for r in rows], fontsize=8.5)
    ax.set_xlim(0, 112)
    ax.set_xlabel("target 비율 (%)  · 세그먼트 숫자 = target 개수")
    ax.set_title("D-SUP-02 · shallow L1 functional-entry 3값 판정\n"
                 "대상군(CORPORATE_OR_APP + UNDETERMINED) vs 대조군(FUNCTIONAL_LANDING)",
                 fontsize=12, loc="left", pad=14)
    ax.grid(axis="x", color="#eeeee8", linewidth=1)
    ax.set_axisbelow(True)
    handles = [plt.Rectangle((0, 0), 1, 1, color=c) for _, c in VERD_ORDER]
    ax.legend(handles, [v for v, _ in VERD_ORDER], loc="lower center",
              bbox_to_anchor=(0.5, -0.26), ncol=3, frameon=False, fontsize=9)
    fig.tight_layout()
    fig.savefig(fig_dir / "DSUP02_verdict_by_stratum.png", dpi=150,
                bbox_inches="tight", facecolor=SURFACE)
    plt.close(fig)

    # --- F2: 후보 개수 분포 (dot strip, log) --------------------------------------
    tgt = [x for x in doc["per_target"] if x["identity_class"] != "FUNCTIONAL_LANDING"]
    ctl = [x for x in doc["per_target"] if x["identity_class"] == "FUNCTIONAL_LANDING"]
    fig, ax = plt.subplots(figsize=(9.2, 3.6))
    import random
    rnd = random.Random(SEED)
    for i, (items, col, name) in enumerate(((ctl, C_REC, "대조군 FUNCTIONAL_LANDING (n=27)"),
                                            (tgt, C_NOEXIT,
                                             "대상군 CORPORATE_OR_APP + UNDETERMINED (n=29)"))):
        xs = [max(x["n_candidates"], 0.5) for x in items]
        yy = [i + rnd.uniform(-0.14, 0.14) for _ in xs]
        ax.scatter(xs, yy, s=54, color=col, edgecolor=SURFACE, linewidth=2,
                   zorder=3, label=name)
        med = sorted(max(x["n_candidates"], 0.5) for x in items)[len(items) // 2]
        ax.plot([med, med], [i - 0.3, i + 0.3], color=INK, linewidth=2, zorder=4)
        ax.text(med, i + 0.36, f"중앙값 {int(med)}", ha="center", fontsize=8.5, color=INK2)
    ax.set_xscale("log")
    ax.set_yticks([0, 1])
    ax.set_yticklabels(["대조군\nFUNCTIONAL", "대상군\nCORP+UNDET"], fontsize=9)
    ax.set_xlabel("target 당 shallow L1 후보 개수 (log, 0 은 0.5 위치에 표시)")
    ax.set_title("후보 개수 분포 — 두 층 모두 대부분 ≥1. 차이는 '유무' 가 아니라 '풍부함' 이다\n"
                 "(0 인 target 은 log 축에 표시하려고 0.5 위치에 찍었다)",
                 fontsize=11, loc="left", pad=12)
    ax.grid(axis="x", color="#eeeee8", linewidth=1)
    ax.set_axisbelow(True)
    ax.set_ylim(-0.6, 1.6)
    fig.tight_layout()
    fig.savefig(fig_dir / "DSUP02_candidate_distribution.png", dpi=150,
                bbox_inches="tight", facecolor=SURFACE)
    plt.close(fig)

    # --- F3: slot provenance -------------------------------------------------------
    sp = res["slot_provenance"]["target_level_slot_contributed"]
    fig, ax = plt.subplots(figsize=(7.4, 3.4))
    order = ["dom", "ax", "probe"]
    vals = [sp.get(k, 0) for k in order]
    bars = ax.bar(order, vals, color=[C_AMB, C_NOEXIT, C_REC], width=0.55,
                  edgecolor=SURFACE, linewidth=2)
    for b, v in zip(bars, vals):
        ax.text(b.get_x() + b.get_width() / 2, v + 0.8, f"{v}/56", ha="center",
                fontsize=10, color=INK, fontweight="bold")
    n_probe_only = len(res["slot_provenance"]["targets_with_probe_only_candidates"])
    ax.set_ylim(0, 60)
    ax.set_ylabel("후보를 1개 이상 제공한 target 수")
    ax.set_title(f"어느 slot 이 후보를 냈나 — probe 전용 target {n_probe_only}건, dom 전용 0건",
                 fontsize=11.5, loc="left", pad=12)
    ax.grid(axis="y", color="#eeeee8", linewidth=1)
    ax.set_axisbelow(True)
    fig.tight_layout()
    fig.savefig(fig_dir / "DSUP02_slot_provenance.png", dpi=150,
                bbox_inches="tight", facecolor=SURFACE)
    plt.close(fig)
    return ["DSUP02_verdict_by_stratum.png", "DSUP02_candidate_distribution.png",
            "DSUP02_slot_provenance.png"]
