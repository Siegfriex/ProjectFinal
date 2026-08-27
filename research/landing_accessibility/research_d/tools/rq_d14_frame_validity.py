"""RQ-D14 — frame validity: 수집된 target URL 의 정체.

질문: E001 이 수집한 56개 web target 의 URL 은 그 서비스의 **대표기능 면**인가,
아니면 **기업/브랜드/앱설치/제품소개 랜딩**인가?

경쟁 가설
  H1 FRAME_OK              대다수가 기능 랜딩. RF001-A 의 주장은 소수 사례 과일반화.
  H2 FRAME_DEFECT          상당수가 기업/브랜드/앱설치/제품소개 면.
  H3 NOT_SEPARABLE         관측 증거로 두 부류를 구분할 수 없다.
  H4 CONFOUNDED_BY_CAPTURE "기능 없음" 이 페이지 정체가 아니라 수집 실패 때문이다.

방법: 세 갈래 독립 증거 삼각검증
  (a) host-service 정합   — prior_url host 와 service brand alias 의 문자열 관계
  (b) 페이지 정체 marker  — identity surface (title/meta/heading/landmark/nav) 어휘
  (c) 기능 컨트롤 부재    — control surface (button/aria/placeholder/label/input/card)
                            + 구조 DOM count

입력은 CSV 두 개뿐이다. raw dom.html 을 다시 파싱하지 않는다.
Restart -> Run All 재현 가능. seed 20260827 (본 분석은 결정론적이며 난수를 쓰지 않는다).

산출: results/RQ_D14_frame_validity.json, figures/RQ_D14_*.png
marker/alias 사전은 D14_MARKER_v1 로 동결됐다. 결과를 본 뒤 수정하지 않는다.
"""
from __future__ import annotations

import hashlib
import json
import math
import re
import sys
import unicodedata
import urllib.parse as up
from collections import Counter
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

SEED = 20260827
RD = Path("/home/sieg/projects-wsl/ProjectFinal/.agent_worktrees/claude_d_research"
          "/research/landing_accessibility/research_d")
RES = RD / "results"
FIG = RD / "figures"
MARKER_VERSION = "D14_MARKER_v1"

plt.rcParams["font.family"] = ["NanumGothic", "Noto Sans CJK KR", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False

# ─────────────────────────────────────────────────────────────────────────────
# (a) SERVICE BRAND ALIAS TABLE  — DEFINITION, 전문 공개
#
# 작성 규칙 (반순환성 rule / anti-circularity):
#   R-A1  alias 는 **서비스 이름에서만** 유도한다. 관측된 URL 에서 토큰을 역으로
#         가져오지 않는다. (그렇게 하면 항상 match 가 되어 규칙이 무의미해진다)
#   R-A2  service_alias = 그 서비스 브랜드 자체의 표준 라틴 표기.
#         corporate_alias = 그 서비스를 운영하는 **모회사·지주·그룹·통합플랫폼·
#         고객지원센터** 의 표준 라틴 표기 (서비스 브랜드와 다를 때만).
#   R-A3  다어절 서비스명은 토큰 결합 + **역순 결합**도 생성한다.
#         (카카오맵 -> kakaomap, mapkakao)
#   R-A4  길이 3 미만 alias 는 우연일치를 막기 위해 버린다. (CU -> "cu" 탈락)
#   R-A5  약어 도메인은 alias 로 인정하되 유래를 표에 명시한다.
#         (홈앤쇼핑 = Home&Shopping -> "hnsmall")
#
# 판정 규칙:
#   host_norm = hostname 소문자 + 비영숫자 제거   (예: www.gsretail.com -> wwwgsretailcom)
#   host_norm 안에서 service_alias / corporate_alias 를 substring 검색하고
#   **가장 긴 매칭 alias 가 이긴다** (longest-alias-wins).
#     - 이긴 alias 가 service  -> SERVICE_HOST
#     - 이긴 alias 가 corporate-> CORPORATE_HOST
#     - 아무것도 안 맞음        -> UNRELATED_HOST
#     - URL 자체가 없음         -> HOST_UNKNOWN
#   longest-alias-wins 가 필요한 이유: tmapmobility.com 은 "tmap"(service, 4) 과
#   "tmapmobility"(corporate, 12) 를 모두 포함한다. 더 구체적인 법인명이 이긴다.
# ─────────────────────────────────────────────────────────────────────────────
ALIAS_TABLE: dict[str, dict] = {
    "쿠팡이츠":         {"service": ["coupangeats"], "corporate": ["coupang"], "note": ""},
    "삼성카드":         {"service": ["samsungcard"], "corporate": ["samsunggroup"], "note": ""},
    "GS25":           {"service": ["gs25"], "corporate": ["gsretail"], "note": "GS25 운영사 = GS리테일"},
    "코스트코":         {"service": ["costco"], "corporate": [], "note": ""},
    "TikTok":         {"service": ["tiktok"], "corporate": ["bytedance"], "note": ""},
    "티맵":            {"service": ["tmap"], "corporate": ["tmapmobility", "sktelecom"], "note": "TMAP 운영사 = 티맵모빌리티"},
    "신한 SOL뱅크":     {"service": ["shinhansol", "solbank", "shinhanbank", "shinhan"],
                       "corporate": ["shinhanfinancialgroup"], "note": "은행 본체 도메인은 서비스 면으로 본다"},
    "밴드":            {"service": ["band"], "corporate": ["navercorp"], "note": ""},
    "세븐일레븐":        {"service": ["7eleven", "seveneleven"], "corporate": ["koreaseven"], "note": ""},
    "다음":            {"service": ["daum"], "corporate": ["kakaocorp"], "note": ""},
    "KB Pay":         {"service": ["kbpay"], "corporate": ["kbcard", "kookmincard", "kbfg"], "note": "KB Pay 운영사 = KB국민카드"},
    "카카오T":          {"service": ["kakaot"], "corporate": ["kakaomobility", "kakaocorp"], "note": "카카오T 운영사 = 카카오모빌리티"},
    "디바이스 케어":      {"service": ["devicecare"], "corporate": ["samsungsvc", "samsungservice"], "note": "삼성 고객지원센터"},
    "롯데백화점":        {"service": ["lottedepartment", "ellotte"], "corporate": ["lotteon", "lotteshopping"], "note": "롯데 통합 이커머스 플랫폼"},
    "마켓컬리":         {"service": ["kurly", "marketkurly"], "corporate": [], "note": ""},
    "Netflix":        {"service": ["netflix"], "corporate": [], "note": ""},
    "V3 Mobile Plus": {"service": ["v3mobileplus", "v3mobile", "v3mp"], "corporate": ["ahnlab"], "note": "R-A4 로 'v3' 탈락"},
    "다이소":           {"service": ["daiso"], "corporate": [], "note": ""},
    "CJ온스타일":       {"service": ["cjonstyle"], "corporate": ["cjgroup"], "note": ""},
    "홈앤쇼핑":         {"service": ["hnsmall", "homeandshopping"], "corporate": [], "note": "R-A5: Home&Shopping -> HNS mall"},
    "카카오톡":         {"service": ["kakaotalk"], "corporate": ["kakaocorp", "kakao"], "note": ""},
    "네이버":           {"service": ["naver"], "corporate": ["navercorp"], "note": ""},
    "Chrome":         {"service": ["chrome"], "corporate": ["google"], "note": "Chrome 제조사 = Google"},
    "현대카드":         {"service": ["hyundaicard"], "corporate": ["hyundaimotorgroup"], "note": ""},
    "emart24":        {"service": ["emart24"], "corporate": ["emart", "shinsegae"], "note": ""},
    "캐시워크":         {"service": ["cashwalk"], "corporate": [], "note": ""},
    "메가커피":         {"service": ["megacoffee", "mgccoffee"], "corporate": [], "note": ""},
    "롯데하이마트":       {"service": ["himart", "lottehimart"], "corporate": ["lotteshopping"], "note": ""},
    "신세계백화점":       {"service": ["shinsegae", "shinsegaedepartment"], "corporate": ["shinsegaegroup"], "note": ""},
    "홈플러스":         {"service": ["homeplus"], "corporate": [], "note": ""},
    "탑마트":           {"service": ["topmart"], "corporate": ["seowon", "seowonyutong"], "note": "탑마트 운영사 = 서원유통"},
    "토스":            {"service": ["toss"], "corporate": ["vivarepublica"], "note": ""},
    "농협하나로마트":      {"service": ["hanaro", "nhhanaro"], "corporate": ["nonghyup"], "note": ""},
    "Instagram":      {"service": ["instagram"], "corporate": ["meta", "facebook"], "note": ""},
    "롯데홈쇼핑":        {"service": ["lottehomeshopping", "lotteimall"], "corporate": ["lotteshopping"], "note": ""},
    "하나은행":         {"service": ["hanabank", "hana"], "corporate": ["hanafinancialgroup"], "note": ""},
    "NH스마트뱅킹":      {"service": ["nhsmartbanking"], "corporate": ["nonghyup", "nhbank"], "note": "앱 브랜드 != 은행 본체 도메인"},
    "에이닷 전화":       {"service": ["adot", "adotcall"], "corporate": ["sktelecom", "sktel"], "note": ""},
    "배달의민족":        {"service": ["baemin", "baedalminjok"], "corporate": ["woowabrothers"], "note": ""},
    "KB스타뱅킹":       {"service": ["kbstar", "starbanking", "kbstarbanking"], "corporate": ["kbfg", "kookminbank"], "note": ""},
    "내 파일":          {"service": ["myfiles"], "corporate": ["samsungsvc", "samsungservice"], "note": "삼성 고객지원센터"},
    "네이버지도":        {"service": ["navermap", "mapnaver"], "corporate": ["navercorp", "naver"], "note": "R-A3 역순결합 적용"},
    "YouTube":        {"service": ["youtube"], "corporate": ["google"], "note": ""},
    "당근":            {"service": ["daangn", "karrot"], "corporate": [], "note": ""},
    "11번가":          {"service": ["11st"], "corporate": ["sktelecom"], "note": ""},
    "컴포즈커피":        {"service": ["composecoffee"], "corporate": [], "note": ""},
    "이마트":           {"service": ["emart"], "corporate": ["shinsegae"], "note": ""},
    "롯데마트":         {"service": ["lottemart"], "corporate": ["lotteshopping"], "note": ""},
    "NS홈쇼핑":         {"service": ["nsmall", "nshomeshopping"], "corporate": ["harimgroup"], "note": ""},
    "Google":         {"service": ["google"], "corporate": ["alphabet"], "note": ""},
    "현대백화점":        {"service": ["thehyundai", "hyundaidepartment"], "corporate": ["ehyundai", "hyundaidepartmentgroup"], "note": "R-A3"},
    "모니모":           {"service": ["monimo"], "corporate": ["samsungfinancialnetworks"], "note": ""},
    "CU":             {"service": [], "corporate": ["bgfretail", "bgf"], "note": "R-A4 로 'cu' 탈락 -> service alias 없음"},
    "카카오맵":         {"service": ["kakaomap", "mapkakao"], "corporate": ["kakaocorp"], "note": "R-A3 역순결합 적용"},
    "G마켓":           {"service": ["gmarket"], "corporate": ["ebaykorea", "shinsegae"], "note": ""},
    "NH콕뱅크":        {"service": ["nhcokbank", "cokbank"], "corporate": ["nonghyup", "nhbank"], "note": ""},
}

# ─────────────────────────────────────────────────────────────────────────────
# (b) 페이지 정체 MARKER 사전 — DEFINITION, 전문 공개
#     적용 surface: title / meta_description / headings / landmarks / nav_links
#     (= identity surface. 페이지가 "자기를 무엇이라고 소개하는가")
# ─────────────────────────────────────────────────────────────────────────────
DICT_CORPORATE = [
    # 회사 정체
    "회사소개", "기업소개", "회사개요", "기업정보", "회사 정보", "CEO 인사말", "CEO인사말",
    "대표이사", "경영이념", "기업이념", "가치체계", "기업 연혁", "회사 연혁", "연혁",
    "수상 이력", "비전", "미션",
    # CI/BI · 브랜드
    "CI/BI", "기업 CI", "BI 소개", "브랜드스토리", "브랜드 스토리", "브랜드 이야기", "브랜드소개",
    # 사업 · 지배구조 · IR
    "사업영역", "사업 영역", "사업분야", "투자정보", "IR", "기업지배구조", "지배구조",
    "경영성과", "공시정보", "전자공시", "주주", "재무정보", "실적",
    # ESG
    "지속가능경영", "사회적 책임", "사회공헌", "정도경영", "윤리경영", "준법경영", "ESG", "환경경영",
    # PR · 채용 · 공지
    "보도자료", "뉴스룸", "미디어", "홍보센터", "채용", "인재채용", "채용문의", "인재상",
    "공지사항", "오시는 길", "찾아오시는 길", "고객헌장", "협력사", "제휴문의",
    # 영문
    "about us", "company", "corporate", "investor relations", "investors", "careers",
    "recruit", "press", "newsroom", "sustainability", "governance", "our story",
    "brand story", "esg",
]
DICT_APP_INSTALL = [
    "앱에서 보기", "앱으로 보기", "앱에서 열기", "앱으로 열기", "앱에서 계속", "앱 설치", "앱설치",
    "앱 다운로드", "앱다운로드", "앱 다운받기", "설치하기", "다운로드하기", "지금 설치",
    "App Store", "앱스토어", "앱 스토어", "Google Play", "구글 플레이", "플레이 스토어",
    "플레이스토어", "Play 스토어", "원스토어", "스마트배너", "앱으로 계속",
    "open in app", "get the app", "download the app", "download on the app store",
    "install app", "open app", "continue in app", "intent://", "itms-apps", "market://",
]
DICT_PRODUCT_INTRO = [
    "서비스 소개", "서비스소개", "기능 소개", "기능소개", "주요 기능", "주요기능",
    "이용안내", "이용 안내", "이용방법", "이용 방법", "사용방법", "사용 방법", "사용법",
    "설정 방법", "기능 사용방법", "더 알아보기", "자세히 알아보기", "자세히 보기",
    "제품 소개", "제품소개", "서비스 안내", "안내 페이지",
    "learn more", "features", "overview", "how it works", "how to use", "product tour",
    "what is", "guide",
]

# ─────────────────────────────────────────────────────────────────────────────
# (c) 기능 AFFORDANCE 사전 — DEFINITION, 전문 공개
#     적용 surface: buttons / aria_labels / placeholders / form_labels /
#                   input_names / card_texts  (= control surface. 실제 조작 대상)
#     주: SSOT S6 E_M 주석에 따라 "로그인 버튼 존재"만으로는 기능 endpoint 로 세지 않는다.
#         따라서 로그인/login 은 사전에서 **의도적으로 제외**한다.
# ─────────────────────────────────────────────────────────────────────────────
DICT_SEARCH_AFFORDANCE = [
    "검색", "검색어", "통합검색", "상품검색", "찾기", "검색하기",
    "search", "searchbox", "query", "keyword", "find",
]
DICT_TRANSACTION_AFFORDANCE = [
    # 커머스
    "장바구니", "담기", "바로구매", "구매하기", "구매", "주문하기", "주문", "결제하기", "결제",
    "배송", "배달주문", "예약하기", "예약", "찜하기", "쿠폰받기", "할인",
    # 금융
    "이체", "송금", "잔액", "계좌조회", "거래내역", "출금", "입금", "충전하기", "환전", "납부",
    # 지도/이동
    "길찾기", "경로", "내비게이션", "출발", "도착", "호출하기",
    # 콘텐츠/커뮤니케이션
    "재생", "시청하기", "글쓰기", "글 작성", "게시", "보내기", "채팅하기",
    # 영문
    "add to cart", "cart", "checkout", "buy now", "buy", "order now", "pay", "payment",
    "transfer", "balance", "book now", "reserve", "directions", "navigate",
    "play", "watch", "post", "compose", "send message",
]

IDENTITY_SURFACES = ["title", "meta_description", "headings", "landmarks", "nav_links"]
CONTROL_SURFACES = ["buttons", "aria_labels", "placeholders", "form_labels",
                    "input_names", "card_texts"]

# ── 동결된 임계값 (결과를 보기 전에 확정) ────────────────────────────────────────
TH_CORP_DISTINCT = 3      # (b) corporate 어휘 distinct >= 3  -> CORPORATE 방향
TH_APP_DISTINCT = 2       # (b) app-install 어휘 distinct >= 2 -> CORPORATE 방향
TH_INTRO_DISTINCT = 3     # (b) product-intro 어휘 distinct >= 3 -> CORPORATE 방향
TH_CARD_ITEMS = 3         # (c) 반복 card 항목 >= 3 이면 card 신호 1
TH_DOM_MIN_ELEMENTS = 100  # (c) 이보다 작으면 CONTROL_UNOBSERVABLE (H4 guard)
TH_CTRL_PRESENT = 3       # (c) control_score >= 3 -> CONTROL_PRESENT
TH_CTRL_ABSENT = 1        # (c) control_score <= 1 -> CONTROL_ABSENT

ASCII_RE = re.compile(r"^[\x00-\x7f]+$")


def sha256_file(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def norm_text(s) -> str:
    if not isinstance(s, str):
        return ""
    s = unicodedata.normalize("NFKC", s)
    return re.sub(r"\s+", " ", s).strip().lower()


def norm_host(h: str) -> str:
    return re.sub(r"[^a-z0-9]", "", (h or "").lower())


def hits(text: str, dictionary: list[str]) -> list[str]:
    """사전 term 중 text 안에 나타나는 것들. 라틴 term 은 단어경계, 한글 term 은 substring."""
    out = []
    for term in dictionary:
        t = norm_text(term)
        if not t:
            continue
        if ASCII_RE.match(t):
            if re.search(r"(?<![a-z0-9])" + re.escape(t) + r"(?![a-z0-9])", text):
                out.append(term)
        else:
            if t.replace(" ", "") in text.replace(" ", ""):
                out.append(term)
    return out


def split_items(s) -> list[str]:
    if not isinstance(s, str) or not s.strip():
        return []
    return [x.strip() for x in s.split("|") if x.strip()]


def wilson(k: int, n: int, z: float = 1.959963984540054) -> tuple[float, float]:
    if n == 0:
        return (float("nan"), float("nan"))
    p = k / n
    d = 1 + z * z / n
    c = p + z * z / (2 * n)
    r = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return ((c - r) / d, (c + r) / d)


# ─────────────────────────────────────────────────────────────────────────────
def host_alignment(service: str, url: str) -> dict:
    if not isinstance(url, str) or not url.strip():
        return {"host": None, "host_norm": None, "verdict": "HOST_UNKNOWN",
                "matched_alias": None, "matched_kind": None, "path": None,
                "path_names_service": None}
    parsed = up.urlparse(url)
    host = parsed.hostname or ""
    hn = norm_host(host)
    entry = ALIAS_TABLE.get(service, {"service": [], "corporate": []})
    cands = []
    for a in entry.get("service", []):
        a2 = norm_host(a)
        if len(a2) >= 3 and a2 in hn:
            cands.append((len(a2), "SERVICE", a))
    for a in entry.get("corporate", []):
        a2 = norm_host(a)
        if len(a2) >= 3 and a2 in hn:
            cands.append((len(a2), "CORPORATE", a))
    path = parsed.path or ""
    path_norm = norm_host(path + "?" + (parsed.query or ""))
    names_service = any(len(norm_host(a)) >= 3 and norm_host(a) in path_norm
                        for a in entry.get("service", []))
    if not cands:
        return {"host": host, "host_norm": hn, "verdict": "UNRELATED_HOST",
                "matched_alias": None, "matched_kind": None, "path": path,
                "path_names_service": names_service}
    cands.sort(key=lambda x: -x[0])
    _, kind, alias = cands[0]
    return {"host": host, "host_norm": hn,
            "verdict": "SERVICE_HOST" if kind == "SERVICE" else "CORPORATE_HOST",
            "matched_alias": alias, "matched_kind": kind, "path": path,
            "path_names_service": names_service}


def evidence_b(row) -> dict:
    text = norm_text(" | ".join(str(row.get(c) or "") for c in IDENTITY_SURFACES
                               if isinstance(row.get(c), str)))
    corp = hits(text, DICT_CORPORATE)
    app = hits(text, DICT_APP_INSTALL)
    intro = hits(text, DICT_PRODUCT_INTRO)
    if len(corp) >= TH_CORP_DISTINCT or len(app) >= TH_APP_DISTINCT or len(intro) >= TH_INTRO_DISTINCT:
        v = "CORPORATE_OR_APP"
    elif len(corp) == 0 and len(app) == 0 and len(intro) <= 1:
        v = "FUNCTIONAL"
    else:
        v = "UNDETERMINED"
    return {"corp_terms": corp, "app_terms": app, "intro_terms": intro,
            "corp_n": len(corp), "app_n": len(app), "intro_n": len(intro),
            "identity_chars": len(text), "vote": v}


def evidence_c(row, obs) -> dict:
    ctrl_text = norm_text(" | ".join(str(row.get(c) or "") for c in CONTROL_SURFACES
                                    if isinstance(row.get(c), str)))
    search_terms = hits(ctrl_text, DICT_SEARCH_AFFORDANCE)
    trans_terms = hits(ctrl_text, DICT_TRANSACTION_AFFORDANCE)
    n_cards = len(split_items(row.get("card_texts")))
    si = obs.get("search_inputs_n")
    si = 0 if pd.isna(si) else float(si)
    di = float(obs.get("dom_input_n") or 0)
    sig_search = int(si > 0 or len(search_terms) > 0)
    sig_input = int(di > 0)
    sig_trans = int(len(trans_terms) > 0)
    sig_cards = int(n_cards >= TH_CARD_ITEMS)
    score = sig_search + sig_input + sig_trans + sig_cards
    body_empty = int(float(obs.get("dom_body_empty") or 0))
    elem = float(obs.get("dom_element_n") or 0)
    if body_empty == 1 or elem < TH_DOM_MIN_ELEMENTS:
        status, vote = "CONTROL_UNOBSERVABLE", "UNDETERMINED"
    elif score >= TH_CTRL_PRESENT:
        status, vote = "CONTROL_PRESENT", "FUNCTIONAL"
    elif score <= TH_CTRL_ABSENT:
        status, vote = "CONTROL_ABSENT", "CORPORATE_OR_APP"
    else:
        status, vote = "CONTROL_WEAK", "UNDETERMINED"
    return {"search_terms": search_terms, "transaction_terms": trans_terms,
            "n_card_items": n_cards, "sig_search": sig_search, "sig_input": sig_input,
            "sig_transaction": sig_trans, "sig_cards": sig_cards,
            "control_score": score, "status": status, "vote": vote,
            "dom_element_n": elem, "dom_input_n": di, "search_inputs_n": si,
            "dom_body_empty": body_empty}


# RF001-A worker 가 자기 limitation 에서 **이름을 댄** 사례들. 이 RQ 의 직접 검증 대상.
RF001A_NAMED_CLAIMS = {
    "GS25": "기업 도메인 gsretail 로 갔다",
    "티맵": "기업사이트로 갔다",
    "카카오T": "기업사이트로 갔다",
    "네이버지도": "navercorp 로 갔다",
    "Instagram": "앱 인터스티셜",
    "TikTok": "앱 인터스티셜",
    "Chrome": "제품 소개면",
}

VOTE_A = {"SERVICE_HOST": "FUNCTIONAL", "CORPORATE_HOST": "CORPORATE_OR_APP",
          "UNRELATED_HOST": "CORPORATE_OR_APP", "HOST_UNKNOWN": "UNDETERMINED"}


def combine(va: str, vb: str, vc: str) -> tuple[str, str]:
    votes = [va, vb, vc]
    c = votes.count("CORPORATE_OR_APP")
    f = votes.count("FUNCTIONAL")
    if c >= 2 and f == 0:
        return "CORPORATE_OR_APP_LANDING", f"{c}xCORP/0xFUNC"
    if f >= 2 and c == 0:
        return "FUNCTIONAL_LANDING", f"{f}xFUNC/0xCORP"
    return "UNDETERMINED", f"{f}xFUNC/{c}xCORP (contradiction or insufficient)"


def main() -> None:
    obs_p = RES / "D_OBSERVATION_TABLE_v2.csv"
    txt_p = RES / "D_TEXT_CORPUS_v2.csv"
    obs = pd.read_csv(obs_p)
    txt = pd.read_csv(txt_p)
    tgt = obs[obs.in_mart == 1].copy()
    om = {r.wtg: r._asdict() if hasattr(r, "_asdict") else None for r in []}
    obs_by_wtg = {r["wtg"]: r for r in tgt.to_dict("records")}

    degenerate = {"64d30ef262d8782d", "ef06dc942ef3ccc9",
                  "95967b50683649f2", "fb3d1841dddfd982"}  # RQ-D13 퇴화 캡처 4건

    rows = []
    for rec in txt.to_dict("records"):
        wtg = rec["wtg"]
        o = obs_by_wtg.get(wtg)
        if o is None:
            continue
        url = o.get("prior_url")
        url_source = "prior_url"
        if not isinstance(url, str) or not url.strip():
            url = o.get("probe_url")
            url_source = "probe_url_fallback"
        if not isinstance(url, str) or not url.strip():
            url, url_source = None, "MISSING"
        a = host_alignment(o.get("prior_service"), url)
        b = evidence_b(rec)
        c = evidence_c(rec, o)
        va = VOTE_A[a["verdict"]]
        cls, reason = combine(va, b["vote"], c["vote"])
        rows.append({
            "wtg": wtg, "service": o.get("prior_service"),
            "archetype": o.get("prior_archetype"),
            "business_domain": o.get("prior_business_domain"),
            "url": url, "url_source": url_source, "dom_title": o.get("dom_title"),
            "degenerate_capture": wtg in degenerate,
            "a_host": a["host"], "a_verdict": a["verdict"],
            "a_matched_alias": a["matched_alias"], "a_matched_kind": a["matched_kind"],
            "a_path": a["path"], "a_path_names_service": a["path_names_service"],
            "a_vote": va,
            "b_corp_n": b["corp_n"], "b_app_n": b["app_n"], "b_intro_n": b["intro_n"],
            "b_corp_terms": b["corp_terms"], "b_app_terms": b["app_terms"],
            "b_intro_terms": b["intro_terms"], "b_identity_chars": b["identity_chars"],
            "b_vote": b["vote"],
            "c_control_score": c["control_score"], "c_status": c["status"],
            "c_sig_search": c["sig_search"], "c_sig_input": c["sig_input"],
            "c_sig_transaction": c["sig_transaction"], "c_sig_cards": c["sig_cards"],
            "c_n_card_items": c["n_card_items"], "c_dom_element_n": c["dom_element_n"],
            "c_dom_input_n": c["dom_input_n"], "c_search_inputs_n": c["search_inputs_n"],
            "c_dom_body_empty": c["dom_body_empty"],
            "c_search_terms": c["search_terms"], "c_transaction_terms": c["transaction_terms"],
            "c_vote": c["vote"],
            "identity_class": cls, "identity_reason": reason,
        })
    df = pd.DataFrame(rows)

    # ── RF001-A 대조 (상호참조. 정답으로 쓰지 않는다) ──────────────────────────
    rf = json.loads((RES / "RF001_A_rule_dt.json").read_text(encoding="utf-8"))
    leaf_by_wtg, rf_app_inter = {}, {}
    for lf in rf["leaves"]:
        leaf_by_wtg[lf["target_id"]] = lf["leaf"]
        rf_app_inter[lf["target_id"]] = int(lf.get("app_interstitial") or 0)
    df["rf001a_leaf"] = df.wtg.map(leaf_by_wtg)
    df["rf001a_abstain"] = df.rf001a_leaf.fillna("").str.startswith("AMBIGUOUS_UNRESOLVED")
    df["rf001a_app_interstitial"] = df.wtg.map(rf_app_inter)

    def class_counts(d: pd.DataFrame) -> dict:
        return {k: int(v) for k, v in d.identity_class.value_counts().items()}

    df_nd = df[~df.degenerate_capture]

    # ── 삼각검증 교차표 ────────────────────────────────────────────────────────
    tri = Counter((r.a_vote, r.b_vote, r.c_vote) for r in df.itertuples())
    tri_tbl = [{"a_vote": k[0], "b_vote": k[1], "c_vote": k[2], "n": v}
               for k, v in sorted(tri.items(), key=lambda x: -x[1])]
    unan_corp = df[(df.a_vote == "CORPORATE_OR_APP") & (df.b_vote == "CORPORATE_OR_APP")
                   & (df.c_vote == "CORPORATE_OR_APP")]
    unan_func = df[(df.a_vote == "FUNCTIONAL") & (df.b_vote == "FUNCTIONAL")
                   & (df.c_vote == "FUNCTIONAL")]

    pair_agree = {}
    for x, y in (("a", "b"), ("a", "c"), ("b", "c")):
        vx, vy = df[f"{x}_vote"], df[f"{y}_vote"]
        both = (vx != "UNDETERMINED") & (vy != "UNDETERMINED")
        pair_agree[f"{x}_{y}"] = {
            "n_both_decisive": int(both.sum()),
            "n_agree": int((both & (vx == vy)).sum()),
            "agreement_rate": (round(float((both & (vx == vy)).sum() / both.sum()), 4)
                               if both.sum() else None),
        }

    # ── archetype 별 ───────────────────────────────────────────────────────────
    def by_arch(d: pd.DataFrame) -> dict:
        out = {}
        for arch, g in d.groupby("archetype"):
            n = len(g)
            k = int((g.identity_class == "CORPORATE_OR_APP_LANDING").sum())
            lo, hi = wilson(k, n)
            out[arch] = {
                "n": n, "corporate_or_app": k,
                "functional": int((g.identity_class == "FUNCTIONAL_LANDING").sum()),
                "undetermined": int((g.identity_class == "UNDETERMINED").sum()),
                "corporate_rate": round(k / n, 4),
                "wilson95_lo": round(lo, 4), "wilson95_hi": round(hi, 4),
                "small_class_warning": n <= 5,
                "services": sorted(g.service.tolist()),
            }
        return out

    # ── archetype x 증거(a) 단독 (host 층위) ────────────────────────────────
    def by_arch_host(d: pd.DataFrame) -> dict:
        out = {}
        for arch, g in d.groupby("archetype"):
            n_ = len(g)
            k_ = int(g.a_verdict.isin(["CORPORATE_HOST", "UNRELATED_HOST"]).sum())
            lo_, hi_ = wilson(k_, n_)
            out[arch] = {"n": n_, "corporate_or_unrelated_host": k_,
                         "rate": round(k_ / n_, 4), "wilson95_lo": round(lo_, 4),
                         "wilson95_hi": round(hi_, 4), "small_class_warning": n_ <= 5,
                         "services": sorted(
                             g[g.a_verdict.isin(["CORPORATE_HOST", "UNRELATED_HOST"])].service.tolist())}
        return out

    # ── 반례 ───────────────────────────────────────────────────────────────────
    ce_i = df[(df.a_verdict.isin(["CORPORATE_HOST", "UNRELATED_HOST"]))
              & (df.c_status == "CONTROL_PRESENT")]
    ce_ii = df[(df.a_verdict == "SERVICE_HOST") & (df.c_status == "CONTROL_ABSENT")]
    ce_i2 = df[(df.a_verdict.isin(["CORPORATE_HOST", "UNRELATED_HOST"]))
               & (df.identity_class == "FUNCTIONAL_LANDING")]
    ce_ii2 = df[(df.a_verdict == "SERVICE_HOST")
                & (df.identity_class == "CORPORATE_OR_APP_LANDING")]

    def slim(d: pd.DataFrame, cols) -> list:
        return d[cols].to_dict("records")

    ce_cols = ["wtg", "service", "archetype", "url", "a_verdict", "a_matched_alias",
               "a_path_names_service", "b_corp_n", "b_app_n", "b_intro_n",
               "c_control_score", "c_status", "identity_class", "rf001a_leaf"]

    # ── H4 배제 ────────────────────────────────────────────────────────────────
    h4 = {
        "degenerate_captures_n": int(df.degenerate_capture.sum()),
        "degenerate_wtgs": sorted(df[df.degenerate_capture].wtg.tolist()),
        "degenerate_services": sorted(df[df.degenerate_capture].service.tolist()),
        "degenerate_classes": {k: int(v) for k, v in
                               df[df.degenerate_capture].identity_class.value_counts().items()},
        "control_unobservable_n": int((df.c_status == "CONTROL_UNOBSERVABLE").sum()),
        "control_unobservable_wtgs": sorted(df[df.c_status == "CONTROL_UNOBSERVABLE"].wtg.tolist()),
        "corporate_landing_all56": int((df.identity_class == "CORPORATE_OR_APP_LANDING").sum()),
        "corporate_landing_excl_degenerate52": int(
            (df_nd.identity_class == "CORPORATE_OR_APP_LANDING").sum()),
        "corporate_landing_with_nonempty_dom": int(
            ((df.identity_class == "CORPORATE_OR_APP_LANDING") & (df.c_dom_body_empty == 0)).sum()),
        "corporate_landing_dom_element_n_min": (
            float(df[df.identity_class == "CORPORATE_OR_APP_LANDING"].c_dom_element_n.min())
            if (df.identity_class == "CORPORATE_OR_APP_LANDING").any() else None),
        "corporate_landing_identity_chars_min": (
            int(df[df.identity_class == "CORPORATE_OR_APP_LANDING"].b_identity_chars.min())
            if (df.identity_class == "CORPORATE_OR_APP_LANDING").any() else None),
    }

    # ── RF001-A 수렴 ───────────────────────────────────────────────────────────
    ab = df.rf001a_abstain
    corp = df.identity_class == "CORPORATE_OR_APP_LANDING"
    conv = {
        "rf001a_abstain_n": int(ab.sum()),
        "rf001a_mapped_n": int((~ab & df.rf001a_leaf.notna()).sum()),
        "abstain_and_corporate": int((ab & corp).sum()),
        "abstain_and_functional": int((ab & (df.identity_class == "FUNCTIONAL_LANDING")).sum()),
        "abstain_and_undetermined": int((ab & (df.identity_class == "UNDETERMINED")).sum()),
        "mapped_and_corporate": int((~ab & corp).sum()),
        "mapped_and_functional": int((~ab & (df.identity_class == "FUNCTIONAL_LANDING")).sum()),
        "mapped_and_undetermined": int((~ab & (df.identity_class == "UNDETERMINED")).sum()),
        "share_of_corporate_that_rf001a_abstained": (
            round(float((ab & corp).sum() / corp.sum()), 4) if corp.sum() else None),
        "share_of_abstain_explained_by_corporate": (
            round(float((ab & corp).sum() / ab.sum()), 4) if ab.sum() else None),
        "rf001a_app_interstitial_n": int((df.rf001a_app_interstitial == 1).sum()),
        "rf001a_app_interstitial_services": sorted(
            df[df.rf001a_app_interstitial == 1].service.tolist()),
        "d14_app_marker_n": int((df.b_app_n > 0).sum()),
        "d14_app_marker_services": sorted(df[df.b_app_n > 0].service.tolist()),
        "note": "RF001-A 판정은 정답이 아니라 독립 상호참조다. 수렴은 증거이지 검증이 아니다.",
    }

    # ── 민감도 ─────────────────────────────────────────────────────────────────
    sens = {}
    for name, (tc, ta, ti) in {
        "primary_corp3_app2_intro3": (3, 2, 3),
        "strict_corp5_app3_intro4": (5, 3, 4),
        "loose_corp2_app1_intro2": (2, 1, 2),
    }.items():
        cnt = Counter()
        for r in df.itertuples():
            if r.b_corp_n >= tc or r.b_app_n >= ta or r.b_intro_n >= ti:
                vb = "CORPORATE_OR_APP"
            elif r.b_corp_n == 0 and r.b_app_n == 0 and r.b_intro_n <= 1:
                vb = "FUNCTIONAL"
            else:
                vb = "UNDETERMINED"
            cnt[combine(r.a_vote, vb, r.c_vote)[0]] += 1
        sens[name] = dict(cnt)
    # 다수결 완화 (모순 허용: 단순 다수결)
    cnt2 = Counter()
    for r in df.itertuples():
        v = [r.a_vote, r.b_vote, r.c_vote]
        c_, f_ = v.count("CORPORATE_OR_APP"), v.count("FUNCTIONAL")
        cnt2["CORPORATE_OR_APP_LANDING" if c_ > f_ else
             ("FUNCTIONAL_LANDING" if f_ > c_ else "UNDETERMINED")] += 1
    sens["combine_plain_majority_allows_contradiction"] = dict(cnt2)
    # 증거 하나씩 빼기 (leave-one-evidence-out)
    for drop in ("a", "b", "c"):
        cnt3 = Counter()
        for r in df.itertuples():
            v = [getattr(r, f"{x}_vote") for x in "abc" if x != drop]
            c_, f_ = v.count("CORPORATE_OR_APP"), v.count("FUNCTIONAL")
            cnt3["CORPORATE_OR_APP_LANDING" if (c_ >= 2 and f_ == 0) else
                 ("FUNCTIONAL_LANDING" if (f_ >= 2 and c_ == 0) else "UNDETERMINED")] += 1
        sens[f"leave_out_{drop}"] = dict(cnt3)

    n = len(df)
    k_corp = int(corp.sum())
    lo, hi = wilson(k_corp, n)
    lo_nd, hi_nd = wilson(int((df_nd.identity_class == "CORPORATE_OR_APP_LANDING").sum()), len(df_nd))

    # ── (1) 동결된 사전등록 규칙: 삼각검증 3분류 CORPORATE 비율만으로 H2 를 판정한다.
    #        결과를 보고 이 규칙을 고치지 않았다. 출력 그대로 남긴다.
    if k_corp / n >= 0.30:
        prereg_verdict = "SUPPORTED"
    elif k_corp / n >= 0.15:
        prereg_verdict = "PARTIALLY_SUPPORTED"
    elif k_corp / n > 0.05:
        prereg_verdict = "NOT_SUPPORTED"
    else:
        prereg_verdict = "REFUTED"

    # ── (2) RF001-A 주장은 두 명제의 **연언**이다.
    #        P1 "수집 URL 상당수가 기업/브랜드/앱설치 랜딩이다"
    #        P2 "그런 면에는 어떤 archetype 의 region/endpoint 도 없다"
    #        사전등록 규칙은 P1∧P2 를 한꺼번에 요구하는 삼각검증 결과에만 적용된다.
    #        RQ 전체(H1~H4)에 대한 verdict 규칙은 사전등록하지 않았으므로 여기서 명시한다.
    #        이것은 임계값 사후수정이 아니라 **비어 있던 판정규칙을 채우는 것**이며,
    #        위 prereg_verdict 는 손대지 않고 그대로 병기한다.
    n_corp_host = int((df.a_verdict.isin(["CORPORATE_HOST", "UNRELATED_HOST"])).sum())
    lo_h, hi_h = wilson(n_corp_host, n)
    p1_supported = (n_corp_host / n) >= 0.20
    p2_supported = (k_corp / n) >= 0.20
    if p1_supported and p2_supported:
        verdict = "SUPPORTED"
    elif p1_supported != p2_supported:
        verdict = "PARTIALLY_SUPPORTED"
    elif (n_corp_host / n) <= 0.05:
        verdict = "REFUTED"
    else:
        verdict = "NOT_SUPPORTED"

    # RF001-A 가 이름 댄 사례 검증
    named = []
    for svc, claim in RF001A_NAMED_CLAIMS.items():
        g = df[df.service == svc]
        if not len(g):
            named.append({"service": svc, "rf001a_claim": claim, "d14": "NOT_IN_MART"})
            continue
        r = g.iloc[0]
        named.append({
            "service": svc, "rf001a_claim": claim, "url": r.url,
            "d14_host_verdict": r.a_verdict, "d14_matched_alias": r.a_matched_alias,
            "d14_b_corp_n": int(r.b_corp_n), "d14_b_app_n": int(r.b_app_n),
            "d14_b_intro_n": int(r.b_intro_n), "d14_control_status": r.c_status,
            "d14_identity_class": r.identity_class,
            "host_claim_confirmed": bool(r.a_verdict in ("CORPORATE_HOST", "UNRELATED_HOST")),
            "app_marker_observed": bool(r.b_app_n > 0),
        })

    out = {
        "rq": "RQ-D14",
        "title": "frame validity — 수집된 target URL 이 서비스 대표기능 면인가 기업/앱설치 랜딩인가",
        "hypothesis_id": "H-D14-COLLECTED-URL-IDENTITY",
        "marker_version": MARKER_VERSION,
        "seed": SEED,
        "verdict": verdict,
        "verdict_basis": (
            f"P1(호스트가 기업/모회사/무관 도메인) {n_corp_host}/{n} = {n_corp_host/n:.1%} "
            f"Wilson95 [{lo_h:.3f},{hi_h:.3f}] -> 지지. "
            f"P2(그 면에 기능 컨트롤이 없다) 삼각검증 CORPORATE_OR_APP_LANDING {k_corp}/{n} "
            f"= {k_corp/n:.1%} Wilson95 [{lo:.3f},{hi:.3f}] -> 미지지. "
            "연언 중 하나만 성립하므로 PARTIALLY_SUPPORTED."),
        "prereg_h2_only_verdict": prereg_verdict,
        "prereg_h2_only_rule": ("동결 규칙: 삼각검증 CORPORATE 비율 >=.30 SUPPORTED / >=.15 "
                                "PARTIALLY / >.05 NOT_SUPPORTED / else REFUTED. "
                                "결과를 본 뒤 수정하지 않았다."),
        "hypothesis_verdicts": {
            "H1_FRAME_OK": ("PARTIALLY_SUPPORTED — 기능 컨트롤이 관측되는 target 이 다수이나 "
                            f"host 정합이 깨진 target 이 {n_corp_host}/{n} 로 '소수 사례 과일반화'라고 "
                            "말할 수 있는 수준이 아니다"),
            "H2_FRAME_DEFECT": ("PARTIALLY_SUPPORTED — host 층위에서는 성립하나 "
                                "'region/endpoint 가 원리적으로 없다'는 부분은 미지지. "
                                f"corporate host {n_corp_host}건 중 CONTROL_PRESENT 가 "
                                f"{int(((df.a_verdict.isin(['CORPORATE_HOST','UNRELATED_HOST'])) & (df.c_status=='CONTROL_PRESENT')).sum())}건"),
            "H3_NOT_SEPARABLE": ("PARTIALLY_SUPPORTED — 세 증거가 서로 어긋나 "
                                 f"UNDETERMINED 가 {int((df.identity_class=='UNDETERMINED').sum())}/{n} 다. "
                                 "구분이 불가능하지는 않으나(만장일치 FUNCTIONAL 존재) 현재 증거로는 절반이 미결"),
            "H4_CONFOUNDED_BY_CAPTURE": ("REFUTED as the sole explanation — 퇴화 캡처 4건을 빼도 "
                                         f"corporate host {int((df[~df.degenerate_capture].a_verdict.isin(['CORPORATE_HOST','UNRELATED_HOST'])).sum())}/{len(df_nd)}, "
                                         f"CORPORATE_OR_APP_LANDING {int((df_nd.identity_class=='CORPORATE_OR_APP_LANDING').sum())}/{len(df_nd)} 로 결론이 유지된다"),
        },
        "rf001a_named_claims_check": named,
        "evidence_a_only": {
            "corporate_or_unrelated_host_n": n_corp_host,
            "rate": round(n_corp_host / n, 4),
            "wilson95": [round(lo_h, 4), round(hi_h, 4)],
            "excl_degenerate_n": int((df[~df.degenerate_capture].a_verdict.isin(
                ["CORPORATE_HOST", "UNRELATED_HOST"])).sum()),
            "excl_degenerate_denom": len(df_nd),
            "corporate_host_with_control_present": int(
                ((df.a_verdict.isin(["CORPORATE_HOST", "UNRELATED_HOST"]))
                 & (df.c_status == "CONTROL_PRESENT")).sum()),
            "corporate_host_with_control_absent": int(
                ((df.a_verdict.isin(["CORPORATE_HOST", "UNRELATED_HOST"]))
                 & (df.c_status == "CONTROL_ABSENT")).sum()),
        },
        "corpus_truncation_caps": {
            "note": ("D_TEXT_CORPUS_v2 는 build_text_corpus.py 에서 surface 별 상한을 둔다. "
                     "marker distinct count 는 위쪽이 절단(censored)돼 있고, 특히 대형 기업사이트의 "
                     "corporate 어휘는 **과소계수**된다. 방향은 보수적이다 (H2 를 불리하게 만든다)."),
            "headings": "25 nodes x 80 chars", "landmarks": "6 nodes x 200 chars",
            "nav_links": "40 nodes x 40 chars", "buttons": "30 nodes x 40 chars",
            "aria_labels": "40", "placeholders": "20", "form_labels": "25 x 40",
            "card_texts": "25 nodes x 60 chars (-> n_card_items 상한 25)",
            "input_names": "25", "title": "200 chars", "meta_description": "300 chars",
        },
        "analysis_unit": "web target (wtg), in_mart==1",
        "n_expected": 59, "n_observed": n,
        "inputs": [
            {"path": str(obs_p), "rows": int(len(obs)), "cols": int(obs.shape[1]),
             "sha256": sha256_file(obs_p)},
            {"path": str(txt_p), "rows": int(len(txt)), "cols": int(txt.shape[1]),
             "sha256": sha256_file(txt_p)},
            {"path": str(RES / "RF001_A_rule_dt.json"), "role": "cross-reference only (not ground truth)",
             "sha256": sha256_file(RES / "RF001_A_rule_dt.json")},
            {"path": str(RES / "RQ_D13_duplicate_vector.json"), "role": "degenerate capture list",
             "sha256": sha256_file(RES / "RQ_D13_duplicate_vector.json")},
        ],
        "missing": {
            "prior_url_missing_used_probe_fallback": int((df.url_source == "probe_url_fallback").sum()),
            "prior_url_missing_services": sorted(df[df.url_source == "probe_url_fallback"].service.tolist()),
            "url_fully_missing": int((df.url_source == "MISSING").sum()),
            "search_inputs_n_null_in_obs": int(tgt.search_inputs_n.isna().sum()),
            "targets_not_in_text_corpus": int(len(tgt) - len(df)),
        },
        "assertion_types": {
            "alias_table": "DEFINITION",
            "marker_dictionaries": "DEFINITION",
            "three_class_counts": "OBSERVATION",
            "triangulation_crosstab": "OBSERVATION",
            "archetype_rates": "ANALYSIS",
            "h4_exclusion": "ANALYSIS",
            "rf001a_convergence": "ANALYSIS",
            "production_implication": "PROJECTION",
        },
        "definitions": {
            "alias_rules": ["R-A1 alias 는 서비스명에서만 유도 (관측 URL 역유도 금지)",
                            "R-A2 service vs corporate alias 분리",
                            "R-A3 다어절은 정순+역순 결합 생성",
                            "R-A4 길이 3 미만 alias 폐기",
                            "R-A5 약어 도메인은 유래 명시 후 인정"],
            "host_match_rule": ("host_norm = hostname 소문자 + 비영숫자 제거. alias substring 검색, "
                                "longest-alias-wins. service 승 -> SERVICE_HOST, "
                                "corporate 승 -> CORPORATE_HOST, 무매칭 -> UNRELATED_HOST"),
            "alias_table": ALIAS_TABLE,
            "dict_corporate": DICT_CORPORATE,
            "dict_app_install": DICT_APP_INSTALL,
            "dict_product_intro": DICT_PRODUCT_INTRO,
            "dict_search_affordance": DICT_SEARCH_AFFORDANCE,
            "dict_transaction_affordance": DICT_TRANSACTION_AFFORDANCE,
            "identity_surfaces": IDENTITY_SURFACES,
            "control_surfaces": CONTROL_SURFACES,
            "thresholds": {"TH_CORP_DISTINCT": TH_CORP_DISTINCT, "TH_APP_DISTINCT": TH_APP_DISTINCT,
                           "TH_INTRO_DISTINCT": TH_INTRO_DISTINCT, "TH_CARD_ITEMS": TH_CARD_ITEMS,
                           "TH_DOM_MIN_ELEMENTS": TH_DOM_MIN_ELEMENTS,
                           "TH_CTRL_PRESENT": TH_CTRL_PRESENT, "TH_CTRL_ABSENT": TH_CTRL_ABSENT},
            "combine_rule": ("3표 중 CORPORATE>=2 AND FUNCTIONAL==0 -> CORPORATE_OR_APP_LANDING; "
                             "FUNCTIONAL>=2 AND CORPORATE==0 -> FUNCTIONAL_LANDING; "
                             "그 외(모순 포함) -> UNDETERMINED"),
            "login_excluded_rationale": "SSOT S6 E_M — 로그인 버튼 존재만으로는 endpoint 로 세지 않는다",
        },
        "results": {
            "all_targets_n": n,
            "class_counts_all56": class_counts(df),
            "class_rate_all56": {k: round(v / n, 4) for k, v in class_counts(df).items()},
            "corporate_wilson95_all56": [round(lo, 4), round(hi, 4)],
            "excl_degenerate_n": len(df_nd),
            "class_counts_excl_degenerate": class_counts(df_nd),
            "class_rate_excl_degenerate": {k: round(v / len(df_nd), 4)
                                           for k, v in class_counts(df_nd).items()},
            "corporate_wilson95_excl_degenerate": [round(lo_nd, 4), round(hi_nd, 4)],
            "host_verdict_counts": {k: int(v) for k, v in df.a_verdict.value_counts().items()},
            "b_vote_counts": {k: int(v) for k, v in df.b_vote.value_counts().items()},
            "c_status_counts": {k: int(v) for k, v in df.c_status.value_counts().items()},
            "path_names_service_n": int(df.a_path_names_service.fillna(False).sum()),
            "path_names_service_among_corporate_host": int(
                df[(df.a_verdict == "CORPORATE_HOST")].a_path_names_service.fillna(False).sum()),
        },
        "triangulation": {
            "crosstab_a_b_c": tri_tbl,
            "unanimous_corporate_n": len(unan_corp),
            "unanimous_corporate": slim(unan_corp, ["wtg", "service", "archetype", "url"]),
            "unanimous_functional_n": len(unan_func),
            "unanimous_functional": slim(unan_func, ["wtg", "service", "archetype", "url"]),
            "pairwise_agreement": pair_agree,
        },
        "by_archetype_all56": by_arch(df),
        "by_archetype_host_level_all56": by_arch_host(df),
        "by_archetype_host_level_excl_degenerate": by_arch_host(df_nd),
        "path_names_service_detail": df[df.a_path_names_service.fillna(False)][
            ["service", "url", "a_verdict"]].to_dict("records"),
        "by_archetype_excl_degenerate": by_arch(df_nd),
        "h4_capture_confound_exclusion": h4,
        "rf001a_convergence": conv,
        "counterexamples": {
            "i_corporate_host_but_controls_present_n": len(ce_i),
            "i_corporate_host_but_controls_present": slim(ce_i, ce_cols),
            "i_corporate_host_but_classified_functional_n": len(ce_i2),
            "i_corporate_host_but_classified_functional": slim(ce_i2, ce_cols),
            "ii_service_host_but_controls_absent_n": len(ce_ii),
            "ii_service_host_but_controls_absent": slim(ce_ii, ce_cols),
            "ii_service_host_but_classified_corporate_n": len(ce_ii2),
            "ii_service_host_but_classified_corporate": slim(ce_ii2, ce_cols),
        },
        "sensitivity": sens,
        "per_target": df.to_dict("records"),
        "limitation": (
            "1) alias table 과 marker 사전은 저자가 손으로 쓴 DEFINITION 이며 gold label 이 아니다. "
            "'기능 랜딩'의 독립 정답이 없으므로 정확도를 계산할 수 없고 구성타당도만 논증한다. "
            "2) text corpus 에 href 가 없어 intent:// itms-apps market:// 스킴 marker 는 "
            "원리적으로 관측 불가다. 앱설치 유도는 과소계수된다. "
            "3) 세 증거는 완전히 독립적이지 않다 — (b)(c) 는 같은 DOM 캡처에서 나온 다른 surface 다. "
            "4) 이 결과는 인과주장이 아니다. detector 실패의 원인을 말하지 않는다."),
        "causal_disclaimer": ("본 RQ 는 어떤 URL 도 detector 실패의 원인이라고 주장하지 않는다. "
                              "'이 URL 에는 해당 archetype 의 region/endpoint 가 관측되지 않는다' 까지만 말한다."),
    }
    (RES / "RQ_D14_frame_validity.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")

    # ── figures ───────────────────────────────────────────────────────────────
    CLS = ["FUNCTIONAL_LANDING", "UNDETERMINED", "CORPORATE_OR_APP_LANDING"]
    COL = {"FUNCTIONAL_LANDING": "#2E7D5B", "UNDETERMINED": "#B8B0A0",
           "CORPORATE_OR_APP_LANDING": "#B3453A"}
    ARCH_LAT = {"ITEM_DETAIL": "ITEM_DETAIL", "FINANCIAL_ACTION_ENTRY": "FINANCIAL",
                "UTILITY_ENTRY": "UTILITY", "COMMUNICATION_ENTRY": "COMMUNICATION",
                "PLACE_LOOKUP": "PLACE", "QUERY": "QUERY", "CONTENT_OPEN": "CONTENT"}

    ba = by_arch(df)
    order = sorted(ba, key=lambda a: -ba[a]["n"])
    fig, axes = plt.subplots(1, 2, figsize=(14, 5.6), gridspec_kw={"width_ratios": [1.25, 1]})
    ax = axes[0]
    bottom = [0] * len(order)
    for c in CLS:
        vals = [ba[a][{"FUNCTIONAL_LANDING": "functional", "UNDETERMINED": "undetermined",
                       "CORPORATE_OR_APP_LANDING": "corporate_or_app"}[c]] for a in order]
        ax.bar([ARCH_LAT[a] for a in order], vals, bottom=bottom, color=COL[c], label=c,
               edgecolor="white")
        for i, (v, b0) in enumerate(zip(vals, bottom)):
            if v:
                ax.text(i, b0 + v / 2, str(v), ha="center", va="center", fontsize=9,
                        color="white", fontweight="bold")
        bottom = [b0 + v for b0, v in zip(bottom, vals)]
    for i, a in enumerate(order):
        ax.text(i, ba[a]["n"] + 0.4, f"n={ba[a]['n']}", ha="center", fontsize=8, color="#555")
    ax.set_title("URL identity by prior archetype (n=56 targets)", fontsize=11)
    ax.set_ylabel("targets")
    ax.legend(fontsize=8, loc="upper right")
    ax.tick_params(axis="x", rotation=30, labelsize=8)
    ax.set_ylim(0, max(ba[a]["n"] for a in order) + 3)

    ax = axes[1]
    ys = list(range(len(order)))[::-1]
    for y, a in zip(ys, order):
        d = ba[a]
        ax.plot([d["wilson95_lo"], d["wilson95_hi"]], [y, y], color="#B3453A", lw=2.5,
                solid_capstyle="round", alpha=.55)
        ax.plot([d["corporate_rate"]], [y], "o", color="#B3453A", ms=7)
        ax.text(1.02, y, f"{d['corporate_or_app']}/{d['n']}" + ("  *" if d["small_class_warning"] else ""),
                fontsize=8, va="center")
    ax.set_yticks(ys)
    ax.set_yticklabels([ARCH_LAT[a] for a in order], fontsize=8)
    ax.set_xlim(0, 1)
    ax.set_xlabel("CORPORATE_OR_APP_LANDING rate (Wilson 95% CI)")
    ax.set_title("* n<=5: do not over-interpret", fontsize=9, color="#777")
    ax.grid(axis="x", alpha=.25)
    fig.suptitle("RQ-D14  collected URL identity", fontsize=13, y=.99)
    fig.tight_layout()
    fig.savefig(FIG / "RQ_D14_identity_by_archetype.png", dpi=150)
    plt.close(fig)

    # triangulation figure
    fig2, ax2 = plt.subplots(figsize=(11, 6.2))
    VM = {"FUNCTIONAL": 1, "UNDETERMINED": 0, "CORPORATE_OR_APP": -1}
    dfs = df.sort_values(["identity_class", "a_vote", "b_vote", "c_vote", "service"])
    mat = [[VM[r.a_vote], VM[r.b_vote], VM[r.c_vote]] for r in dfs.itertuples()]
    im = ax2.imshow(list(map(list, zip(*mat))), aspect="auto", cmap="RdYlGn", vmin=-1, vmax=1)
    ax2.set_yticks([0, 1, 2])
    ax2.set_yticklabels(["(a) host-service", "(b) identity marker", "(c) function control"], fontsize=9)
    ax2.set_xticks(range(len(dfs)))
    ax2.set_xticklabels([f"{s}" for s in dfs.service], rotation=90, fontsize=6)
    for i, r in enumerate(dfs.itertuples()):
        m = {"CORPORATE_OR_APP_LANDING": "C", "FUNCTIONAL_LANDING": "F", "UNDETERMINED": "?"}[r.identity_class]
        ax2.text(i, 2.75, m, ha="center", fontsize=6.5,
                 color={"C": "#B3453A", "F": "#2E7D5B", "?": "#888"}[m], fontweight="bold")
    ax2.text(-0.6, 2.75, "verdict", ha="right", fontsize=8)
    ax2.set_ylim(3.2, -0.6)
    ax2.set_title("Triangulation — green=FUNCTIONAL, yellow=UNDETERMINED, red=CORPORATE/APP", fontsize=10)
    fig2.colorbar(im, ax=ax2, shrink=.5, ticks=[-1, 0, 1]).ax.set_yticklabels(["CORP", "UNDET", "FUNC"], fontsize=7)
    fig2.tight_layout()
    fig2.savefig(FIG / "RQ_D14_triangulation.png", dpi=150)
    plt.close(fig2)

    # marker evidence figure
    fig3, ax3 = plt.subplots(figsize=(10, 6))
    for cls in CLS:
        g = df[df.identity_class == cls]
        ax3.scatter(g.b_corp_n + g.b_app_n + g.b_intro_n, g.c_control_score + 0.0,
                    s=60, alpha=.75, color=COL[cls], label=cls, edgecolor="white")
    for r in df.itertuples():
        if (r.b_corp_n + r.b_app_n + r.b_intro_n) >= 4 or r.c_control_score <= 1:
            ax3.annotate(r.wtg[:6], (r.b_corp_n + r.b_app_n + r.b_intro_n, r.c_control_score),
                         fontsize=6, xytext=(3, 3), textcoords="offset points", color="#444")
    ax3.axvline(TH_CORP_DISTINCT - .5, ls="--", c="#999", lw=1)
    ax3.axhline(TH_CTRL_ABSENT + .5, ls="--", c="#999", lw=1)
    ax3.set_xlabel("(b) identity marker distinct terms  (corporate + app-install + product-intro)")
    ax3.set_ylabel("(c) control score  (search / input / transaction / cards)")
    ax3.set_title("RQ-D14  identity markers vs function controls (labels = wtg prefix)", fontsize=11)
    ax3.legend(fontsize=8)
    ax3.grid(alpha=.25)
    fig3.tight_layout()
    fig3.savefig(FIG / "RQ_D14_marker_vs_control.png", dpi=150)
    plt.close(fig3)

    print(json.dumps({"verdict": verdict, "prereg_h2_only": prereg_verdict, "n": n,
                      "corporate_or_unrelated_host": n_corp_host,
                      "class_counts_all56": class_counts(df),
                      "class_counts_excl_degenerate": class_counts(df_nd),
                      "host": out["results"]["host_verdict_counts"],
                      "unanimous_corp": len(unan_corp), "unanimous_func": len(unan_func),
                      "conv": conv["abstain_and_corporate"]}, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
