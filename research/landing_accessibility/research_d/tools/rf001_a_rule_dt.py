"""D-RF-001-A — Rule Decision Tree baseline for Representative Function Mapping.

SSOT: /home/sieg/projects-wsl/ProjectFinal/SSOTV2/01_REPRESENTATIVE_FUNCTION_MAPPING_DT_v2.1.md
      (LA-RFDT-2.1)  S2 Stage 0 / S4 Stage 2 / S5 Stage 3 branch tree /
      S6 Stage 4 multi-candidate resolver / S8 guard / S9 leaf schema / S10 release gate

H-RF001-A   : SSOT 01 S5 의 rule DT 를 결정론적으로 구현하면 관측 가능한 DOM/AX/form/URL
              신호만으로 상당수 target 에서 유일 leaf 가 닫힌다.
H-A-null    : rule 은 대부분 다중후보를 남기고, 유일 leaf 가 닫히는 경우도 prior 와
              체계적으로 어긋난다 (= rule 이 정보가 없다).

설계 원칙 (사후에 바꾸지 않는다):
  1. force-map 금지. 유일 강후보가 아니면 abstain.
  2. prior_archetype / prior_business_domain / prior_service 는 **규칙 입력이 아니다**.
     SSOT S6 evidence precedence 4-5 (source/business prior, service name token) 는
     의도적으로 보류한다. 이걸 쓰면 prior_agreement 가 순환논증이 된다.
     대신 S6-4 tiebreak 를 켠 variant 를 민감도 분석으로 따로 돌린다.
  3. 정적 landing snapshot 만 있다. SSOT 의 endpoint 는 "전이가 실제로 일어난 순간"이지만
     여기서는 관측 불가능하므로 **endpoint-enabling control 의 존재**로 강등 정의한다
     (DEFINITION-level deviation, FINDINGS 에 명시).

read-only. production 경로를 수정하지 않는다. gold label / holdout 을 읽지 않는다.
산출: results/RF001_A_rule_dt.json / results/RF001_A_FINDINGS.md / figures/RF001_A_*.png
"""
from __future__ import annotations

import hashlib
import json
import math
import re
import sys
from collections import Counter
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

SEED = 20260827
np.random.seed(SEED)

RD = Path("/home/sieg/projects-wsl/ProjectFinal/.agent_worktrees/claude_d_research"
          "/research/landing_accessibility/research_d")
OBS = RD / "results" / "D_OBSERVATION_TABLE.csv"
TXT = RD / "results" / "D_TEXT_CORPUS.csv"
SSOT = Path("/home/sieg/projects-wsl/ProjectFinal/SSOTV2"
            "/01_REPRESENTATIVE_FUNCTION_MAPPING_DT_v2.1.md")
RULE_VERSION = "RULE_DT_SSOT01_v2.1"

ARCHETYPES = ["QUERY", "CONTENT_OPEN", "ITEM_DETAIL", "PLACE_LOOKUP",
              "COMMUNICATION_ENTRY", "FINANCIAL_ACTION_ENTRY", "UTILITY_ENTRY"]
ABSTAIN_LEAVES = ["AMBIGUOUS_UNRESOLVED__MULTI_CANDIDATE",
                  "AMBIGUOUS_UNRESOLVED__NO_STRONG_CANDIDATE",
                  "UNDETERMINED_URL_EVIDENCE"]

# ---------------------------------------------------------------------------
# Stage 2 — lexicon (SSOT S4 feature families 를 관측 가능한 토큰으로 조작화)
# 사후 수정 금지. 모든 패턴은 rule_definitions.txt 로 MLflow 에 그대로 기록된다.
# ---------------------------------------------------------------------------
LEX = {
    # Query-like (S4 Query-like, S5 Branch Q)
    "search_widget":  r"검색어|검색창|통합검색|무엇을 찾|찾으시는|검색해|search|물어보세요|질의",
    "search_submit":  r"^검색$|^검색하기$|^통합검색$|^search$|검색 버튼|검색하기",
    "search_param":   r"^(q|query|keyword|kw|wd|search|searchword|searchkeyword|"
                      r"sword|term)$",
    # Content-like (S4 Content-like, S5 Branch C)
    "content_item":   r"기사|뉴스|칼럼|사설|연재|웹툰|에피소드|회차|동영상|영상|클립|숏폼|"
                      r"방송|다시보기|시리즈|플레이리스트|article|episode|video|clip|news",
    "content_play":   r"재생|플레이|시청|보러가기|이어보기|다시보기|자세히 보기|본문 보기|"
                      r"play|watch|listen|스트리밍",
    # Item-like (S4 Item-like, S5 Branch I)
    "price":          r"\d[\d,]{2,}\s*원|₩\s*\d|\d[\d,]{2,}\s*won|품절|일시품절|판매종료|"
                      r"가격\s*미정|SOLD ?OUT",
    "item_card":      r"상품|제품|아이템|메뉴|신상|베스트|기획전|특가|세일|할인|product|item",
    "txn_control":    r"장바구니|카트에 담기|쇼핑카트|담기|바로구매|구매하기|주문하기|"
                      r"결제하기|구매|주문|cart|add to bag|add to cart|buy now|checkout",
    # Place-like (S4 Place-like, S5 Branch P)
    "place_widget":   r"장소|주소|지번|도로명|목적지|출발지|길찾기|지도|맵|내비|주변|근처|"
                      r"현위치|로드뷰|정류장|지하철|map|address|directions|place",
    "place_detail":   r"길찾기|상세보기|로드뷰|주변|이 지역|재검색|거리뷰|매장 찾기|지점 찾기|"
                      r"store locator|directions",
    # Communication-like (S4, S5 Branch M)
    "comm_list":      r"게시글|게시판|피드|타임라인|스레드|댓글|커뮤니티|동네생활|모임|밴드|"
                      r"채팅방|대화방|메시지함|post|feed|thread|timeline|community",
    "comm_compose":   r"글쓰기|새 글|글 작성|댓글 달기|댓글 쓰기|메시지 보내기|채팅하기|"
                      r"대화하기|compose|write a post|new post|send message",
    # Finance-like (S4, S5 Branch F)
    "fin_function":   r"이체|송금|계좌조회|계좌|잔액|출금|입금|카드대금|명세서|이용내역|"
                      r"이용한도|한도|대출|적금|예금|환전|납부|청구|결제일|자산관리|"
                      r"transfer|balance|account",
    "auth_gate":      r"공동인증|공인인증|간편인증|본인확인|본인인증|인증서|OTP|보안카드|"
                      r"비밀번호|패스워드|password|생체인증|지문|얼굴인식",
    # Utility-like (S4, S5 Branch U)
    "tool_function":  r"조회하기|계산기|계산하기|변환|환산|측정|스캔|검사|진단|발급|신청하기|"
                      r"접수하기|예약하기|등록하기|신고하기|충전하기|잔여|남은|만보기|걸음",
    "tool_primary":   r"조회|계산|변환|측정|스캔|검사|진단|발급|신청|접수|예약|등록|충전|시작하기",
    # Stage 0 / guard
    # 주의: 맨 처음 구현은 bare `404` 를 썼고 상품 규격 "(404G)" 에 걸려 롯데마트를 잘못
    # Stage0 기각했다. 토큰 경계를 강제한다 (결과 개선용 튜닝이 아니라 구현 결함 시정).
    "error_page":     r"page not found|(?<![\w,.])404(?![\w,.])|not found|error 페이지|"
                      r"페이지를 찾을 수 없|존재하지 않는 페이지|서비스 점검|"
                      r"access denied|접근이 거부",
    "app_interstitial": r"앱에서 (열기|보기)|앱 열기|앱으로 보기|앱 설치|앱 다운로드|"
                        r"open in app|open app|install the app|앱에서 계속",
}
LEXC = {k: re.compile(v, re.I) for k, v in LEX.items()}
# CP949/EUC-KR bytes 가 latin-1 로 읽힌 mojibake 시그니처
MOJIBAKE = re.compile("[À-ÿ][-¿]")

# 반복 구조의 최소 항목 수. 2 는 pair, 3 부터 list 로 본다. 민감도에서 2/5 로 흔든다.
REPEAT_MIN_DEFAULT = 3

TEXT_FIELDS = ["title", "meta_description", "headings", "landmarks", "nav_links",
               "buttons", "aria_labels", "placeholders", "form_labels",
               "input_names", "card_texts", "url_tokens"]


def sha256_file(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def wilson(k: int, n: int, z: float = 1.959963984540054) -> tuple[float, float]:
    """Wilson score interval. n==0 이면 (nan, nan)."""
    if n == 0:
        return (float("nan"), float("nan"))
    p = k / n
    d = 1 + z * z / n
    c = p + z * z / (2 * n)
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return ((c - h) / d, (c + h) / d)


def split_items(s) -> list[str]:
    return [x.strip() for x in str(s or "").split("|") if x.strip()]


# ---------------------------------------------------------------------------
# Stage 2 — feature extraction (관측 테이블 + 텍스트 코퍼스만 사용)
# ---------------------------------------------------------------------------
def features(row: pd.Series) -> dict:
    f: dict = {}
    txt = {c: str(row.get(c) if row.get(c) is not None else "") for c in TEXT_FIELDS}
    txt = {c: ("" if v.lower() == "nan" else v) for c, v in txt.items()}
    blob = " \n ".join(v for v in txt.values() if v)
    controls = " | ".join([txt["buttons"], txt["aria_labels"], txt["nav_links"],
                           txt["form_labels"]])
    cards = split_items(txt["card_texts"])
    navs = split_items(txt["nav_links"])
    inames = [x.lower() for x in split_items(txt["input_names"])]

    f["n_cards"] = len(cards)
    f["n_navs"] = len(navs)
    f["encoding_degraded"] = int(len(MOJIBAKE.findall(blob)) >= 5)

    def num(k, default=0.0):
        v = row.get(k)
        if v is None:
            return default
        try:
            fv = float(v)
        except (TypeError, ValueError):
            return default
        return default if math.isnan(fv) else fv

    f["search_inputs_n"] = num("search_inputs_n")
    f["article_present"] = num("article_present")
    f["password_n"] = num("gate_password_input_n")
    f["captcha_n"] = num("gate_captcha_iframe_n")
    f["dom_input_n"] = num("dom_input_n")
    f["dom_button_n"] = num("dom_button_n")
    f["dom_a_href_n"] = num("dom_a_href_n")
    f["dom_body_empty"] = num("dom_body_empty")
    f["probe_present"] = num("probe_present")

    def hit(key, s):
        return bool(LEXC[key].search(s))

    def cnt(key, s):
        return len(LEXC[key].findall(s))

    # Query-like
    f["has_search_input"] = int(f["search_inputs_n"] >= 1
                                or (f["dom_input_n"] >= 1
                                    and (hit("search_widget", txt["placeholders"])
                                         or any(LEXC["search_param"].match(x) for x in inames))))
    f["has_search_submit"] = int(
        any(LEXC["search_submit"].search(x) for x in
            split_items(txt["buttons"]) + split_items(txt["aria_labels"]))
        or any(LEXC["search_param"].match(x) for x in inames))
    # Content-like
    f["content_item_cards"] = sum(1 for c in cards + navs if hit("content_item", c))
    f["has_content_play"] = int(hit("content_play", controls))
    # Item-like
    f["price_hits"] = cnt("price", blob)
    f["item_cards"] = sum(1 for c in cards + navs if hit("item_card", c) or hit("price", c))
    f["has_txn_control"] = int(hit("txn_control", controls)
                               or hit("txn_control", txt["card_texts"]))
    # Place-like
    f["has_place_widget"] = int(hit("place_widget", txt["placeholders"])
                                or hit("place_widget", controls))
    f["place_cards"] = sum(1 for c in cards + navs if hit("place_widget", c))
    f["has_place_detail"] = int(hit("place_detail", controls)
                                or hit("place_detail", txt["card_texts"]))
    # Communication-like
    f["comm_cards"] = sum(1 for c in cards + navs if hit("comm_list", c))
    f["has_comm_compose"] = int(hit("comm_compose", controls)
                                or hit("comm_compose", txt["placeholders"]))
    # Finance-like
    f["fin_controls"] = sum(1 for c in split_items(txt["buttons"]) + navs
                            if hit("fin_function", c))
    f["has_auth_gate"] = int(f["password_n"] >= 1 or hit("auth_gate", controls)
                             or hit("auth_gate", txt["form_labels"]))
    # Utility-like
    f["has_tool_function"] = int(hit("tool_function", controls))
    f["has_tool_primary_form"] = int(f["dom_input_n"] >= 1 and hit("tool_primary", controls))
    # Stage 0 / guard
    f["is_error_page"] = int(hit("error_page", txt["title"]) or hit("error_page", txt["headings"]))
    f["is_app_interstitial"] = int(hit("app_interstitial", controls)
                                   and f["n_cards"] + f["n_navs"] <= 4
                                   and f["dom_a_href_n"] <= 20)
    return f


# ---------------------------------------------------------------------------
# Stage 3 — branch tree (S5). 각 branch 는 region evidence R 과 endpoint evidence E 를
# **모두** 요구한다. 하나라도 없으면 강후보가 아니다.
# ---------------------------------------------------------------------------
def branch_spec(rmin: int) -> dict:
    return {
        "QUERY": {
            "R": ("R_Q  focusable search input / searchbox / combobox 노출",
                  lambda f: f["has_search_input"] == 1),
            "E": ("E_Q  submit 가능한 form 또는 submit control (자동완성만으로는 불가)",
                  lambda f: f["has_search_submit"] == 1),
            "region": "search input control이 사용 가능한 상태로 노출된 영역",
            "endpoint": ("질의 제출 후 결과 state 전이 "
                         "(정적 snapshot에서는 submit control 존재로 강등 관측)"),
            "region_signal": "SEARCH_INPUT_PRESENT",
            "endpoint_signal": "QUERY_SUBMIT_CONTROL_PRESENT",
            "forbidden": "자동완성 노출을 endpoint로 처리하지 않는다",
        },
        "CONTENT_OPEN": {
            "R": (f"R_C  content card/link list 노출 (반복 content 항목 >= {rmin})",
                  lambda f: f["content_item_cards"] >= rmin),
            "E": ("E_C  article body open 또는 main media playback 진입 control",
                  lambda f: f["article_present"] >= 1 or f["has_content_play"] == 1),
            "region": "content card/link list가 노출된 영역",
            "endpoint": "article body open 또는 main media playback start",
            "region_signal": "CONTENT_CARD_LIST_PRESENT",
            "endpoint_signal": "CONTENT_OPEN_CONTROL_PRESENT",
            "forbidden": "미리보기/hover/광고 pre-roll은 endpoint가 아니다",
        },
        "ITEM_DETAIL": {
            "R": (f"R_I  반복 product/item card or link list (>= {rmin})",
                  lambda f: f["item_cards"] >= rmin),
            "E": ("E_I  item name + price(또는 명시적 price unavailable) + "
                  "transaction control의 **존재**",
                  lambda f: f["price_hits"] >= 1 and f["has_txn_control"] == 1),
            "region": "individual item/product card or link list",
            "endpoint": "item 상세면에서 name+price+transaction control 존재 확인",
            "region_signal": "ITEM_CARD_LIST_PRESENT",
            "endpoint_signal": "ITEM_PRICE_AND_TXN_CONTROL_PRESENT",
            "forbidden": "구매/장바구니/주문 control을 클릭하지 않는다 (presence evidence only)",
        },
        "PLACE_LOOKUP": {
            "R": (f"R_P  place search control 또는 place list (>= {rmin})",
                  lambda f: f["has_place_widget"] == 1 or f["place_cards"] >= rmin),
            "E": ("E_P  place query submit 또는 place detail open control",
                  lambda f: f["has_place_detail"] == 1
                  or (f["has_place_widget"] == 1 and f["has_search_submit"] == 1)),
            "region": "place search control 또는 place list",
            "endpoint": "place query submitted 또는 place detail opened",
            "region_signal": "PLACE_SEARCH_OR_LIST_PRESENT",
            "endpoint_signal": "PLACE_DETAIL_CONTROL_PRESENT",
            "forbidden": "pan/zoom은 endpoint가 아니다. 차량 호출/배차 확정은 절대 제외",
        },
        "COMMUNICATION_ENTRY": {
            "R": (f"R_M  thread/post list(>= {rmin}) 또는 compose-entry control",
                  lambda f: f["comm_cards"] >= rmin or f["has_comm_compose"] == 1),
            "E": ("E_M  post/thread open / compose area entry / 실제 login gate 도달 "
                  "(로그인 버튼 존재만으로는 불가)",
                  lambda f: f["has_comm_compose"] == 1 or f["comm_cards"] >= rmin
                  or f["password_n"] >= 1),
            "region": "thread/post list 또는 compose-entry control",
            "endpoint": "post/thread open / compose area entry / actual login gate reached",
            "region_signal": "THREAD_LIST_OR_COMPOSE_PRESENT",
            "endpoint_signal": "THREAD_OPEN_OR_COMPOSE_OR_LOGIN_GATE",
            "forbidden": "메시지 발신/게시 완료 금지. 로그인 버튼 존재만으로 endpoint 처리 금지",
        },
        "FINANCIAL_ACTION_ENTRY": {
            "R": (f"R_F  balance/transfer/payment/auth function entry control (>= {rmin})",
                  lambda f: f["fin_controls"] >= rmin),
            "E": ("E_F  실제 LOGIN/IDENTITY gate 구조 도달 (password/인증 control)",
                  lambda f: f["has_auth_gate"] == 1),
            "region": "balance/transfer/payment/auth function entry control",
            "endpoint": "finance function surface open 또는 actual LOGIN/IDENTITY gate reached",
            "region_signal": "FIN_FUNCTION_ENTRY_PRESENT",
            "endpoint_signal": "IDENTITY_GATE_STRUCTURE_PRESENT",
            "forbidden": "송금/이체/결제 수행 금지",
        },
        "UTILITY_ENTRY": {
            "R": ("R_U  단일목적 function surface entry control",
                  lambda f: f["has_tool_function"] == 1),
            "E": ("E_U  function surface가 열리고 primary control이 present/actionable",
                  lambda f: f["has_tool_primary_form"] == 1),
            "region": "function surface entry control",
            "endpoint": "function surface open + primary control present/actionable",
            "region_signal": "TOOL_ENTRY_CONTROL_PRESENT",
            "endpoint_signal": "TOOL_PRIMARY_CONTROL_ACTIONABLE",
            "forbidden": "도구별 완료작업을 수행하지 않는다",
        },
    }


BRANCH_SPEC = branch_spec(REPEAT_MIN_DEFAULT)

# 안전: endpoint 정의/신호에 구매/결제/전송 "수행"이 들어가면 안 된다
# (SSOT S10 release gate: unsafe endpoint false-positive = 0).
UNSAFE_ENDPOINT_PAT = re.compile(
    r"(구매|결제|주문|송금|이체|출금|전송|발송|게시)\s*(수행|완료|실행|확정|제출)|"
    r"purchase_(complete|submit)|payment_(complete|submit)|transfer_(execute|submit)|"
    r"checkout_submit|order_submit", re.I)


def classify(f: dict, rmin: int = REPEAT_MIN_DEFAULT,
             prior_tiebreak: str | None = None) -> dict:
    """SSOT S2 Stage0 -> S5 Stage3 -> S6 Stage4 -> S9 leaf."""
    spec_all = branch_spec(rmin)
    trace: list[dict] = []

    # -- Stage 0 (S2) --------------------------------------------------------
    if f["dom_body_empty"] == 1:
        trace.append({"stage": "Stage0", "rule": "S0_NO_RENDERED_SURFACE", "fired": True,
                      "evidence": (f"dom_body_text_len<50 (dom_body_empty=1), "
                                   f"probe_present={f['probe_present']:.0f}")})
        return {"leaf": "UNDETERMINED_URL_EVIDENCE",
                "unresolved_reason": ("rendered public mobile web surface not observable "
                                      "in frozen evidence (empty body)"),
                "candidate_archetypes": [], "decision_trace": trace,
                "next_fallback_stage": "re-collection (Stage 0 재판정). NLP fallback 불가"}
    if f["is_error_page"] == 1:
        trace.append({"stage": "Stage0", "rule": "S0_ERROR_PAGE", "fired": True,
                      "evidence": "title/headings match error_page lexicon"})
        return {"leaf": "UNDETERMINED_URL_EVIDENCE",
                "unresolved_reason": ("target URL resolves to an error/not-found page - "
                                      "conflicting URL evidence (SSOT S2 NO branch)"),
                "candidate_archetypes": [], "decision_trace": trace,
                "next_fallback_stage": "URL re-resolution by A (이름/도메인 추론 금지)"}

    # -- Stage 3 (S5) --------------------------------------------------------
    strong, weak = [], []
    for a, spec in spec_all.items():
        (rlab, rfn), (elab, efn) = spec["R"], spec["E"]
        r, e = bool(rfn(f)), bool(efn(f))
        trace.append({"stage": "Stage3", "rule": f"{a}.R", "fired": r, "evidence": rlab})
        trace.append({"stage": "Stage3", "rule": f"{a}.E", "fired": e, "evidence": elab})
        if r and e:
            strong.append(a)
        elif r or e:
            weak.append(a)

    guard = {"login_gate": int(f["password_n"] >= 1),
             "captcha_iframe": int(f["captcha_n"] >= 1),
             "app_interstitial": int(f["is_app_interstitial"])}

    def mapped(a: str, basis: str) -> dict:
        s = spec_all[a]
        return {"leaf": a, "archetype": a,
                "region_definition": s["region"], "region_signal_type": s["region_signal"],
                "endpoint_definition": s["endpoint"], "endpoint_signal_type": s["endpoint_signal"],
                "mapping_basis": basis, "forbidden_continuation": s["forbidden"],
                "candidate_archetypes": strong, "decision_trace": trace,
                "guard_annotation": guard}

    # -- Stage 4 (S6) multi-candidate resolver -------------------------------
    if len(strong) == 1:
        trace.append({"stage": "Stage4", "rule": "UNIQUE_STRONG_CANDIDATE", "fired": True,
                      "evidence": f"strong={strong} weak={weak}"})
        return mapped(strong[0], "OBSERVED_INTERACTION_STRUCTURE (SSOT S6 precedence 1-3)")
    if len(strong) >= 2:
        if prior_tiebreak and prior_tiebreak in strong:
            trace.append({"stage": "Stage4", "rule": "PRIOR_TIEBREAK(S6 precedence 4)",
                          "fired": True, "evidence": f"strong={strong} prior={prior_tiebreak}"})
            return mapped(prior_tiebreak, "SOURCE_BUSINESS_PRIOR (SSOT S6 precedence 4)")
        trace.append({"stage": "Stage4", "rule": "MULTI_STRONG_CANDIDATE_ABSTAIN",
                      "fired": True, "evidence": f"strong={strong}"})
        return {"leaf": "AMBIGUOUS_UNRESOLVED__MULTI_CANDIDATE",
                "unresolved_reason": "두 개 이상 강한 후보. SSOT S6은 첫 매칭을 선택하지 않는다",
                "candidate_archetypes": strong, "decision_trace": trace,
                "next_fallback_stage": "NLP fallback (SSOT S7)"}

    trace.append({"stage": "Stage4", "rule": "NO_STRONG_CANDIDATE_ABSTAIN", "fired": True,
                  "evidence": f"strong=[] weak={weak}"})
    return {"leaf": "AMBIGUOUS_UNRESOLVED__NO_STRONG_CANDIDATE",
            "unresolved_reason": "region+endpoint evidence를 동시에 만족하는 branch 없음",
            "candidate_archetypes": weak, "decision_trace": trace,
            "next_fallback_stage": "NLP fallback (SSOT S7) / VLM / Human Final"}


# ---------------------------------------------------------------------------
def load() -> pd.DataFrame:
    obs = pd.read_csv(OBS)
    obs = obs[obs["in_mart"] == 1].copy()
    txt = pd.read_csv(TXT)
    df = obs.merge(txt.drop(columns=["run_dir", "observation_id", "prior_archetype",
                                     "prior_business_domain", "prior_service", "prior_url"]),
                   on="wtg", how="left", validate="one_to_one")
    return df.sort_values("wtg").reset_index(drop=True)


def run_variant(df: pd.DataFrame, rmin: int, use_prior_tiebreak: bool) -> list[dict]:
    out = []
    for _, row in df.iterrows():
        f = features(row)
        leaf = classify(f, rmin=rmin,
                        prior_tiebreak=row["prior_archetype"] if use_prior_tiebreak else None)
        leaf["target_id"] = row["wtg"]
        leaf["prior_archetype"] = row["prior_archetype"]
        leaf["prior_business_domain"] = row["prior_business_domain"]
        leaf["prior_service"] = row["prior_service"]
        leaf["prior_url"] = row["prior_url"]
        leaf["encoding_degraded"] = f["encoding_degraded"]
        leaf["app_interstitial"] = f["is_app_interstitial"]
        leaf["evidence_refs"] = {k: (round(v, 3) if isinstance(v, float) else v)
                                 for k, v in f.items()}
        out.append(leaf)
    return out


def metrics(leaves: list[dict]) -> dict:
    n = len(leaves)
    mapped = [x for x in leaves if x["leaf"] in ARCHETYPES]
    undet = [x for x in leaves if x["leaf"] == "UNDETERMINED_URL_EVIDENCE"]
    n_ana = n - len(undet)
    multi = [x for x in leaves if x["leaf"] == "AMBIGUOUS_UNRESOLVED__MULTI_CANDIDATE"]
    noev = [x for x in leaves if x["leaf"] == "AMBIGUOUS_UNRESOLVED__NO_STRONG_CANDIDATE"]
    agree = [x for x in mapped if x["leaf"] == x["prior_archetype"]]
    cov_lo, cov_hi = wilson(len(mapped), n)
    return {
        "n_targets": n, "n_analyzable": n_ana,
        "n_mapped": len(mapped), "n_undetermined": len(undet),
        "n_abstain_multi": len(multi), "n_abstain_no_evidence": len(noev),
        "coverage": len(mapped) / n, "coverage_ci_lo": cov_lo, "coverage_ci_hi": cov_hi,
        "coverage_analyzable": (len(mapped) / n_ana) if n_ana else float("nan"),
        "abstention_rate": (len(multi) + len(noev)) / n,
        "abstention_rate_incl_undetermined": (n - len(mapped)) / n,
        "prior_agreement_within_coverage": (len(agree) / len(mapped)) if mapped else float("nan"),
        "prior_agreement_within_coverage_ci_lo": wilson(len(agree), len(mapped))[0],
        "prior_agreement_within_coverage_ci_hi": wilson(len(agree), len(mapped))[1],
        "prior_agreement_overall": len(agree) / n,
        "prior_agreement_overall_ci_lo": wilson(len(agree), n)[0],
        "prior_agreement_overall_ci_hi": wilson(len(agree), n)[1],
        "n_encoding_degraded": sum(x["encoding_degraded"] for x in leaves),
        "n_app_interstitial": sum(x["app_interstitial"] for x in leaves),
    }


def per_class(leaves: list[dict]) -> dict:
    out = {}
    for a in ARCHETYPES:
        prior_n = sum(1 for x in leaves if x["prior_archetype"] == a)
        pred_n = sum(1 for x in leaves if x["leaf"] == a)
        tp = sum(1 for x in leaves if x["leaf"] == a and x["prior_archetype"] == a)
        rlo, rhi = wilson(tp, prior_n)
        plo, phi = wilson(tp, pred_n)
        out[a] = {"n_prior": prior_n, "n_rule_mapped": pred_n, "tp": tp,
                  "recall_vs_prior": (tp / prior_n) if prior_n else float("nan"),
                  "recall_ci_lo": rlo, "recall_ci_hi": rhi,
                  "precision_vs_prior": (tp / pred_n) if pred_n else float("nan"),
                  "precision_ci_lo": plo, "precision_ci_hi": phi}
    return out


def confusion(leaves: list[dict]):
    cols = ARCHETYPES + ABSTAIN_LEAVES
    mat = pd.DataFrame(0, index=ARCHETYPES, columns=cols, dtype=int)
    for x in leaves:
        mat.loc[x["prior_archetype"], x["leaf"]] += 1
    return mat, cols


def firing_counts(leaves: list[dict]) -> dict:
    fired = Counter()
    for x in leaves:
        for t in x["decision_trace"]:
            if t["fired"]:
                fired[f'{t["stage"]}::{t["rule"]}'] += 1
    strong = Counter()
    for x in leaves:
        seenR = {t["rule"].split(".")[0] for t in x["decision_trace"]
                 if t["stage"] == "Stage3" and t["fired"] and t["rule"].endswith(".R")}
        seenE = {t["rule"].split(".")[0] for t in x["decision_trace"]
                 if t["stage"] == "Stage3" and t["fired"] and t["rule"].endswith(".E")}
        for a in seenR & seenE:
            strong[a] += 1
    return {"predicate_fired": dict(sorted(fired.items(), key=lambda kv: -kv[1])),
            "strong_candidate_per_branch": dict(sorted(strong.items(), key=lambda kv: -kv[1]))}


def safety_audit(leaves: list[dict]) -> dict:
    viol = []
    for x in leaves:
        if x["leaf"] not in ARCHETYPES:
            continue
        for k in ("endpoint_definition", "endpoint_signal_type"):
            if UNSAFE_ENDPOINT_PAT.search(x.get(k, "")):
                viol.append({"target_id": x["target_id"], "field": k, "value": x[k]})
        if not x.get("forbidden_continuation"):
            viol.append({"target_id": x["target_id"], "field": "forbidden_continuation",
                         "value": "MISSING"})
        if not x.get("decision_trace"):
            viol.append({"target_id": x["target_id"], "field": "decision_trace",
                         "value": "MISSING"})
    scan = [{"branch": a, "endpoint_signal_type": s["endpoint_signal"],
             "unsafe": bool(UNSAFE_ENDPOINT_PAT.search(s["endpoint_signal"] + s["endpoint"]))}
            for a, s in BRANCH_SPEC.items()]
    return {"unsafe_endpoint_false_positive_n":
            len([v for v in viol if v["field"].startswith("endpoint")]),
            "leaves_missing_evidence_trace_n":
            len([v for v in viol if v["field"] == "decision_trace"]),
            "leaves_missing_forbidden_continuation_n":
            len([v for v in viol if v["field"] == "forbidden_continuation"]),
            "force_mapped_n": 0,
            "violations": viol, "branch_endpoint_scan": scan,
            "note": ("ITEM_DETAIL의 transaction control은 SSOT S4/S8에 따라 presence evidence로만 "
                     "쓰이며 activation을 endpoint로 삼는 규칙은 존재하지 않는다.")}


def rules_text() -> str:
    lines = [f"# {RULE_VERSION}", f"# SSOT: {SSOT}",
             f"# seed={SEED}  REPEAT_MIN={REPEAT_MIN_DEFAULT}", "",
             "## Stage 0 (SSOT S2)",
             "S0_NO_RENDERED_SURFACE : dom_body_empty==1 -> UNDETERMINED_URL_EVIDENCE",
             "S0_ERROR_PAGE          : error_page lexicon in title|headings "
             "-> UNDETERMINED_URL_EVIDENCE",
             "", "## Stage 3 branch predicates (SSOT S5) - R AND E 를 모두 만족해야 강후보"]
    for a, s in BRANCH_SPEC.items():
        lines += [f"[{a}]", f"  {s['R'][0]}", f"  {s['E'][0]}",
                  f"  region_signal_type     = {s['region_signal']}",
                  f"  endpoint_signal_type   = {s['endpoint_signal']}",
                  f"  forbidden_continuation = {s['forbidden']}"]
    lines += ["", "## Stage 4 resolver (SSOT S6)",
              "len(strong)==1 -> MAPPED (mapping_basis=OBSERVED_INTERACTION_STRUCTURE)",
              "len(strong)>=2 -> AMBIGUOUS_UNRESOLVED__MULTI_CANDIDATE  (next: NLP fallback S7)",
              "len(strong)==0 -> AMBIGUOUS_UNRESOLVED__NO_STRONG_CANDIDATE "
              "(next: NLP/VLM/Human)",
              "prior tiebreak (S6 precedence 4) 은 기본 OFF - prior_agreement 순환 방지. "
              "민감도 variant 에서만 ON.",
              "", "## Lexicon (Stage 2, SSOT S4)"]
    for k, v in LEX.items():
        lines.append(f"{k:18s} = {v}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
SHORT = {"QUERY": "QUERY", "CONTENT_OPEN": "CONTENT", "ITEM_DETAIL": "ITEM",
         "PLACE_LOOKUP": "PLACE", "COMMUNICATION_ENTRY": "COMM",
         "FINANCIAL_ACTION_ENTRY": "FIN", "UTILITY_ENTRY": "UTIL",
         "AMBIGUOUS_UNRESOLVED__MULTI_CANDIDATE": "ABSTAIN\nmulti",
         "AMBIGUOUS_UNRESOLVED__NO_STRONG_CANDIDATE": "ABSTAIN\nno-evid",
         "UNDETERMINED_URL_EVIDENCE": "UNDET\nurl-evid"}


def fig_confusion(mat: pd.DataFrame, path: Path):
    fig, ax = plt.subplots(figsize=(11, 5.2))
    data = mat.values
    im = ax.imshow(data, cmap="Blues", aspect="auto")
    ax.set_xticks(range(len(mat.columns)))
    ax.set_xticklabels([SHORT[c] for c in mat.columns], fontsize=8)
    ax.set_yticks(range(len(mat.index)))
    ax.set_yticklabels([f"{SHORT[r]} (n={mat.loc[r].sum()})" for r in mat.index], fontsize=8)
    mx = max(data.max(), 1)
    for i in range(data.shape[0]):
        for j in range(data.shape[1]):
            if data[i, j]:
                ax.text(j, i, data[i, j], ha="center", va="center", fontsize=9,
                        color="white" if data[i, j] > mx * .6 else "black")
    ax.axvline(len(ARCHETYPES) - .5, color="crimson", lw=1.6)
    ax.set_xlabel("rule DT leaf   (right of red line = abstention / undetermined)", fontsize=9)
    ax.set_ylabel("business-domain prior", fontsize=9)
    ax.set_title(f"RF-001-A  rule DT leaf vs prior   (n=56, {RULE_VERSION})", fontsize=10)
    fig.colorbar(im, ax=ax, shrink=.8, label="targets")
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    return fig


def fig_firing(fc: dict, path: Path, n: int):
    pf = {k.replace("Stage3::", ""): v for k, v in fc["predicate_fired"].items()
          if k.startswith("Stage3::")}
    for a in ARCHETYPES:
        pf.setdefault(f"{a}.R", 0)
        pf.setdefault(f"{a}.E", 0)
    keys = sorted(pf, key=lambda k: (-pf[k], k))
    fig, ax = plt.subplots(figsize=(9, 6))
    colors = ["#1f77b4" if k.endswith(".R") else "#ff7f0e" for k in keys]
    ax.barh(range(len(keys)), [pf[k] for k in keys], color=colors)
    ax.set_yticks(range(len(keys)))
    ax.set_yticklabels(keys, fontsize=8)
    ax.invert_yaxis()
    ax.set_xlabel(f"targets where predicate fired   (denominator n={n})", fontsize=9)
    ax.set_title("Which rules actually do work?  (blue = region R, orange = endpoint E)",
                 fontsize=10)
    for i, k in enumerate(keys):
        ax.text(pf[k] + .4, i, str(pf[k]), va="center", fontsize=8)
    ax.set_xlim(0, n)
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    return fig


def fig_outcome(leaves: list[dict], path: Path):
    cats = ["MAPPED", "ABSTAIN multi", "ABSTAIN no-evidence", "UNDETERMINED"]
    key = {"AMBIGUOUS_UNRESOLVED__MULTI_CANDIDATE": "ABSTAIN multi",
           "AMBIGUOUS_UNRESOLVED__NO_STRONG_CANDIDATE": "ABSTAIN no-evidence",
           "UNDETERMINED_URL_EVIDENCE": "UNDETERMINED"}
    tab = pd.DataFrame(0, index=ARCHETYPES, columns=cats, dtype=int)
    for x in leaves:
        tab.loc[x["prior_archetype"], key.get(x["leaf"], "MAPPED")] += 1
    fig, ax = plt.subplots(figsize=(9, 4.6))
    bottom = np.zeros(len(ARCHETYPES))
    cmap = {"MAPPED": "#2ca02c", "ABSTAIN multi": "#ff7f0e",
            "ABSTAIN no-evidence": "#d62728", "UNDETERMINED": "#7f7f7f"}
    for c in cats:
        ax.bar(range(len(ARCHETYPES)), tab[c].values, bottom=bottom, label=c, color=cmap[c])
        bottom += tab[c].values
    ax.set_xticks(range(len(ARCHETYPES)))
    ax.set_xticklabels([f"{SHORT[a]}\nn={tab.loc[a].sum()}" for a in ARCHETYPES], fontsize=8)
    ax.set_ylabel("targets")
    ax.set_title("Rule DT outcome by prior archetype (n=56)", fontsize=10)
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    return fig


def compute() -> dict:
    df = load()
    n = len(df)
    leaves = run_variant(df, REPEAT_MIN_DEFAULT, False)
    m = metrics(leaves)
    pc = per_class(leaves)
    mat, cols = confusion(leaves)
    fc = firing_counts(leaves)
    sa = safety_audit(leaves)

    counter = [{"target_id": x["target_id"], "prior_service": x["prior_service"],
                "prior_url": x["prior_url"], "prior_archetype": x["prior_archetype"],
                "rule_leaf": x["leaf"], "mapping_basis": x["mapping_basis"],
                "region_signal_type": x["region_signal_type"],
                "endpoint_signal_type": x["endpoint_signal_type"],
                "evidence_refs": x["evidence_refs"]}
               for x in leaves if x["leaf"] in ARCHETYPES and x["leaf"] != x["prior_archetype"]]
    agreed = [{"target_id": x["target_id"], "prior_service": x["prior_service"],
               "archetype": x["leaf"]}
              for x in leaves if x["leaf"] in ARCHETYPES and x["leaf"] == x["prior_archetype"]]

    sens = {}
    keys = ("n_mapped", "coverage", "abstention_rate",
            "prior_agreement_within_coverage", "prior_agreement_overall")
    for rm in (2, 3, 5):
        sens[f"repeat_min_{rm}"] = {k: metrics(run_variant(df, rm, False))[k] for k in keys}
    sens["prior_tiebreak_on"] = {
        k: metrics(run_variant(df, REPEAT_MIN_DEFAULT, True))[k] for k in keys}
    deg = [x for x in leaves if not x["encoding_degraded"]]
    sens["exclude_encoding_degraded"] = {"n": len(deg),
                                         **{k: metrics(deg)[k] for k in keys[:4]}}
    ana = [x for x in leaves if x["leaf"] != "UNDETERMINED_URL_EVIDENCE"]
    sens["exclude_stage0_undetermined"] = {"n": len(ana),
                                           **{k: metrics(ana)[k] for k in keys[:4]}}

    cov, pa = m["coverage"], m["prior_agreement_within_coverage"]
    if cov >= .75 and pa == pa and pa >= .85:
        verdict = "SUPPORTED"
    elif cov >= .30 and pa == pa and pa >= .60:
        verdict = "PARTIALLY_SUPPORTED"
    elif m["n_mapped"] == 0:
        verdict = "REFUTED"
    else:
        verdict = "NOT_SUPPORTED"

    out = {
        "verdict": verdict,
        "hypothesis_id": "H-RF001-A-RULE-DT",
        "competing_hypothesis": ("rule 은 대부분 다중후보를 남기고 유일 leaf 도 prior 와 "
                                 "체계적으로 어긋난다"),
        "child_id": "D-RF-001-A", "rq_id": "RQ-D-RF-001",
        "rule_version": RULE_VERSION, "seed": SEED,
        "assertion_types": {
            "coverage / abstention / prior_agreement 수치": "OBSERVATION",
            "rule 이 정보를 갖는가에 대한 판단": "ANALYSIS",
            "endpoint 을 'endpoint-enabling control 존재'로 강등한 것": "DEFINITION",
            "rule DT 코드 자체": "IMPLEMENTATION",
            "REAL_TARGET 으로의 일반화": "PROJECTION"},
        "inputs": [
            {"path": str(OBS), "rows_total": 66, "rows_used": n, "sha256": sha256_file(OBS)},
            {"path": str(TXT), "rows": len(pd.read_csv(TXT)), "sha256": sha256_file(TXT)},
            {"path": str(SSOT), "sha256": sha256_file(SSOT)}],
        "analysis_unit": "web target (wtg), in_mart==1",
        "n_expected": 59, "n_observed": n,
        "prior_class_counts": dict(Counter(df["prior_archetype"])),
        "metrics": m, "per_class": pc,
        "confusion_matrix": {"rows_prior": ARCHETYPES, "cols_rule_leaf": cols,
                             "matrix": mat.values.tolist()},
        "rule_firing_counts": fc, "safety_audit": sa,
        "counterexamples_mapped_but_disagree_with_prior": counter,
        "mapped_and_agree_with_prior": agreed,
        "sensitivity": sens,
        "leaves": leaves,
    }
    return {"out": out, "mat": mat, "df": df, "leaves": leaves, "fc": fc}


def mlflow_metrics(out: dict) -> dict:
    """metric key 는 영문/숫자/_-./: 만."""
    m = dict(out["metrics"])
    md = {k: float(v) for k, v in m.items() if isinstance(v, (int, float))}
    for a, pc in out["per_class"].items():
        s = {"QUERY": "query", "CONTENT_OPEN": "content", "ITEM_DETAIL": "item",
             "PLACE_LOOKUP": "place", "COMMUNICATION_ENTRY": "comm",
             "FINANCIAL_ACTION_ENTRY": "fin", "UTILITY_ENTRY": "util"}[a]
        for k, v in pc.items():
            if isinstance(v, (int, float)) and not (isinstance(v, float) and math.isnan(v)):
                md[f"class/{s}/{k}"] = float(v)
    for b, v in out["rule_firing_counts"]["strong_candidate_per_branch"].items():
        md[f"strong/{b}"] = float(v)
    for k, v in out["rule_firing_counts"]["predicate_fired"].items():
        md[f"fired/{k.replace('::', '/')}"] = float(v)
    for k, v in out["safety_audit"].items():
        if isinstance(v, int):
            md[f"safety/{k}"] = float(v)
    for var, d in out["sensitivity"].items():
        for k, v in d.items():
            if isinstance(v, (int, float)) and not (isinstance(v, float) and math.isnan(v)):
                md[f"sens/{var}/{k}"] = float(v)
    md["n_counterexamples"] = float(len(out["counterexamples_mapped_but_disagree_with_prior"]))
    return md


def log_mlflow(out: dict, figs: dict) -> str:
    import sys as _sys
    _sys.path.insert(0, str(RD / "tools"))
    import mlflow
    import mlflow_contract as C

    parent = json.loads((RD / "results" / "RF001_PARENT_RUN.json").read_text())["parent_run_id"]
    with C.research_run(
            experiment="LA_03_RF_MAPPING", run_name="D-RF-001-A rule_dt",
            plane="D", agent_id="D", subagent_id="worker/D-RF-001-A",
            objective=("SSOT 01 S5 rule DT 를 결정론적으로 구현해 "
                       "유일 leaf 가 어디까지 닫히는지 측정"),
            method="deterministic rule decision tree + explicit abstention",
            dataset_grain="target (in_mart==1), n=56",
            n_expected=59, n_observed=out["n_observed"],
            hypothesis_id="H-RF001-A-RULE-DT",
            competing_hypothesis=out["competing_hypothesis"],
            claim_kind="ANALYSIS", ticket_id="NONE", phase="I1", split="none",
            parent_run_id=parent,
            result_path=RD / "results" / "RF001_A_rule_dt.json",
            model_or_rule_version=RULE_VERSION, seed=SEED,
            extra_tags={"mlflow.parentRunId": parent, "rq_id": "RQ-D-RF-001",
                        "child_id": "D-RF-001-A"},
            extra_params={"repeat_min": REPEAT_MIN_DEFAULT,
                          "prior_used_as_rule_input": "false",
                          "endpoint_definition_downgrade":
                              "endpoint-enabling control presence (static snapshot)"},
    ) as run:
        mlflow.log_metrics(mlflow_metrics(out))
        for name, fig in figs.items():
            mlflow.log_figure(fig, name)
        mlflow.log_artifact(str(RD / "results" / "RF001_A_FINDINGS.md"), artifact_path="result")
        mlflow.log_artifact(str(RD / "results" / "RF001_A_rule_dt.json"), artifact_path="result")
        mlflow.log_text(rules_text(), "rule_definitions.txt")
        mlflow.log_text(json.dumps(out["counterexamples_mapped_but_disagree_with_prior"],
                                   ensure_ascii=False, indent=1), "counterexamples.json")
        mlflow.log_text(json.dumps(out["safety_audit"], ensure_ascii=False, indent=1),
                        "safety_audit.json")
        C.finish(
            verdict=out["verdict"],
            limitation=("가장 무거운 한계: prior_archetype 은 서비스(앱)의 대표기능인데 수집된 URL "
                        "상당수가 기업/브랜드/앱설치 유도 랜딩이라 어떤 archetype 의 region/endpoint 도 "
                        "존재하지 않는다. 이는 DT 결함이 아니라 Stage0/1 target URL 정의 문제이며 "
                        "DT 수정으로는 해결되지 않는다. 부수적으로 (a) 정적 단일 snapshot 이라 "
                        "endpoint 를 control 존재로 강등했고(coverage 상한 추정), "
                        "(b) 공용 텍스트 코퍼스가 절단되어 있으며, "
                        "(c) 8/56 이 CP949 mojibake 로 한글 증거가 소실됐고, "
                        "(d) gold label 이 없어 prior_agreement 는 정확도가 아니다."))
        return run.info.run_id


def main():
    r = compute()
    out, mat, fc = r["out"], r["mat"], r["fc"]
    (RD / "results" / "RF001_A_rule_dt.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    figs = {
        "confusion_rule_dt.png": fig_confusion(mat, RD / "figures" / "RF001_A_confusion.png"),
        "rule_firing.png": fig_firing(fc, RD / "figures" / "RF001_A_rule_firing.png",
                                      out["n_observed"]),
        "outcome_by_prior.png": fig_outcome(r["leaves"],
                                            RD / "figures" / "RF001_A_outcome_by_prior.png"),
    }
    print(json.dumps({"verdict": out["verdict"], **out["metrics"]}, ensure_ascii=False, indent=1))
    print("\nstrong per branch:", fc["strong_candidate_per_branch"])
    print("\nconfusion:\n", mat.to_string())
    print("\ncounterexamples:",
          [(c["prior_service"], c["prior_archetype"], "->", c["rule_leaf"])
           for c in out["counterexamples_mapped_but_disagree_with_prior"]])
    print("\nagreed:", [(a["prior_service"], a["archetype"])
                        for a in out["mapped_and_agree_with_prior"]])
    print("\nsensitivity:", json.dumps(out["sensitivity"], ensure_ascii=False, indent=1))
    print("\nsafety:", {k: v for k, v in out["safety_audit"].items() if k.endswith("_n")})
    if "--no-mlflow" not in sys.argv:
        rid = log_mlflow(out, figs)
        print(f"\nmlflow run_id = {rid}")
    return out, figs


if __name__ == "__main__":
    main()
