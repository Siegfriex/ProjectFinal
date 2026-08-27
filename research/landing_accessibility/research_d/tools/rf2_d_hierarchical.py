"""D-RF2-D — Hierarchical interaction architecture vs flat 7-way rule mapping.

parent RQ : RQ-D-RF-002
child     : D-RF2-D
hypothesis: H-RF2-D-HIERARCHY

연구질문
--------
SSOT 01 (`LA-RFDT-2.1`) §5 Stage 3 는 7 개 archetype branch 를 **평평하게** 나열한다.
그런데 §5 의 각 branch 질문을 읽으면 branch 들은 서로 다른 **interaction primitive**
(질의 제출 / 객체 열기 / 인증·행위 진입 / 도구면 진입) 위에 세워져 있다.

그렇다면 7-way 를 한 번에 가르는 대신 **primitive 를 먼저 가르고 그 안에서 archetype 으로
분기**하는 계층 구조가 관측 가능한 evidence 와 더 잘 맞는가?

**최종 output 은 frozen 7 archetype 그대로다.** 새 class 를 만들지 않는다. primitive 는
중간 단계일 뿐 leaf 가 아니다. 최종 leaf 는 반드시 7 archetype 중 하나이거나 ABSTAIN 이다.

`prior_archetype` 은 gold label 이 아니라 **prior** 다. 따라서 accuracy 라는 단어를 쓰지
않고 `prior_agreement` 로만 부른다.

세 구조 (동일 입력 · 동일 atomic predicate · 동일 abstention 원칙)
----------------------------------------------------------------
S1 `flat`          — SSOT §5 branch tree 7-way + §6 resolver (유일 강후보만 확정)
S2 `hier_rule`     — Level 1 primitive rule → Level 2 archetype rule
S3 `hier_semantic` — Level 1 primitive rule → Level 2 는 텍스트 임베딩 유사도 순위
보조 S2s `hier_strict` — Level 1 을 flat 강후보의 단순 조대화(coarsening)로 정의한 민감도

**세 구조는 완전히 동일한 atomic predicate 집합을 공유한다.** 그래야 차이가 lexicon 차이가
아니라 **구조 차이**로 귀속된다.

실행
----
    /home/sieg/projects-wsl/ProjectFinal/.venv/bin/python tools/rf2_d_hierarchical.py
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")

import numpy as np
import pandas as pd

RD = Path("/home/sieg/projects-wsl/ProjectFinal/.agent_worktrees/claude_d_research"
          "/research/landing_accessibility/research_d")
SSOT = Path("/home/sieg/projects-wsl/ProjectFinal/SSOTV2"
            "/01_REPRESENTATIVE_FUNCTION_MAPPING_DT_v2.1.md")
OBS = RD / "results" / "D_OBSERVATION_TABLE_v2.csv"
TXT = RD / "results" / "D_TEXT_CORPUS_v2.csv"
OUT_JSON = RD / "results" / "RF2_D_hierarchical.json"
FIGDIR = RD / "figures"
SEED = 20260827
KST = timezone(timedelta(hours=9))
RULE_VERSION = "RF2D_HIER_v1"
PARENT = "ae754858ba3a4be391e5f811640d3fd8"

ARCHETYPES = ["QUERY", "CONTENT_OPEN", "ITEM_DETAIL", "PLACE_LOOKUP",
              "COMMUNICATION_ENTRY", "FINANCIAL_ACTION_ENTRY", "UTILITY_ENTRY"]

# ======================================================================================
# LEVEL 1 정의 — SSOT §5 branch 질문의 **endpoint 절**에서 유도한다 (데이터에서 유도하지 않음)
# ======================================================================================
# §5 각 branch 의 Endpoint 문장을 그대로 읽으면 네 종류의 서로 다른 상태전이가 있다.
#
#   Branch Q  "질의가 실제 제출되어 결과 state로 전환된 순간"          → 질의 제출
#   Branch P  "place query submitted"                                → 질의 제출
#   Branch C  "article body open" / "main media playback start"      → 객체 열기
#   Branch I  "거래 대상 한 건의 상세면에 들어가"                       → 객체 열기
#   Branch P  "place detail opened"                                  → 객체 열기
#   Branch M  "post/thread open"                                     → 객체 열기
#   Branch M  "compose area entry" / "actual login gate"             → 인증·행위 진입
#   Branch F  "finance function surface open" / "LOGIN/IDENTITY gate" → 인증·행위 진입
#   Branch U  "function surface 열림 + primary control actionable"    → 도구면 진입
#
# 따라서 Level 1 primitive 는 다음 넷이며, 이는 SSOT 텍스트의 재조직이지 새 construct 가 아니다.
LEVEL1 = {
    "L1_QUERY_SUBMISSION": ["QUERY", "PLACE_LOOKUP"],
    "L1_OBJECT_OPENING": ["CONTENT_OPEN", "ITEM_DETAIL", "PLACE_LOOKUP", "COMMUNICATION_ENTRY"],
    "L1_AUTH_ACTION_ENTRY": ["FINANCIAL_ACTION_ENTRY", "COMMUNICATION_ENTRY"],
    "L1_UTILITY_TOOL_ENTRY": ["UTILITY_ENTRY"],
}
# 구조적 사실 (결과가 아니라 정의에서 바로 따라옴):
#   PLACE_LOOKUP 은 primitive 2 개에, COMMUNICATION_ENTRY 도 primitive 2 개에 속한다.
#   즉 SSOT §5 의 branch tree 는 primitive 위의 **분할(partition)이 아니다.**
PRIOR_PRIMITIVES = {a: [p for p, ms in LEVEL1.items() if a in ms] for a in ARCHETYPES}

# ======================================================================================
# LEXICON — 사전 선언. 결과를 본 뒤 수정하지 않는다.
# SSOT §4 Stage 2 의 feature family 이름을 그대로 따른다.
# ======================================================================================
LEX = {
    # §4 Query-like
    "search": ["검색", "서치", "search", "검색어", "찾아보기"],
    "search_submit": ["검색", "search", "찾기", "submit", "조회하기", "검색하기"],
    # §4 Content-like
    "media": ["재생", "play", "동영상", "영상", "시청", "에피소드", "구독", "플레이",
              "watch", "스트리밍", "라이브", "웹툰", "회차", "다시보기"],
    "content_card": ["기사", "뉴스", "칼럼", "아티클", "article", "더보기", "콘텐츠",
                     "영상", "웹툰", "매거진", "리뷰"],
    # §4 Item-like
    "item": ["상품", "제품", "가격", "구매", "판매", "브랜드", "할인", "배송", "쇼핑",
             "item", "product", "price", "스토어", "마켓", "특가", "쿠폰"],
    "txn": ["장바구니", "구매", "주문", "결제", "담기", "바로구매", "cart", "buy",
            "order", "checkout", "구입", "예약하기"],
    # §4 Place-like
    "place": ["지도", "길찾기", "주소", "위치", "장소", "근처", "매장", "지점", "점포",
              "내비", "navigation", "map", "목적지", "출발지", "도착지", "맛집", "명소",
              "오시는 길", "찾아오시는", "이동", "경로", "택시", "지하철", "버스"],
    "place_detail": ["길찾기", "영업시간", "오시는 길", "상세보기", "주소", "전화번호",
                     "예약", "리뷰", "층별", "찾아오시는"],
    # §4 Communication-like
    "comm": ["게시판", "커뮤니티", "댓글", "글쓰기", "피드", "메시지", "채팅", "대화",
             "스레드", "포스트", "게시물", "팔로", "친구", "모임", "오픈채팅", "톡방",
             "밴드", "소통", "구성원", "멤버"],
    "compose": ["글쓰기", "새 글", "글 쓰기", "작성하기", "댓글 쓰기", "메시지 보내기",
                "compose", "write", "새 게시물", "채팅하기", "대화하기", "문의하기"],
    # §4 Finance-like
    "fin": ["계좌", "잔액", "이체", "송금", "결제", "카드", "대출", "보험", "청구",
            "명세서", "한도", "금리", "예금", "적금", "펀드", "환전", "자동이체",
            "입금", "출금", "거래내역", "인증서", "본인인증", "간편인증", "페이",
            "이용 내역", "리워드", "포인트"],
    # §4 Utility-like
    "util": ["사용방법", "사용법", "기능 안내", "이용안내", "이용 안내", "설정",
             "계산기", "계산", "변환", "번역", "진단", "측정", "도구", "매뉴얼",
             "도움말", "신청하기", "조회하기", "확인하기", "다운로드"],
    # Stage 0
    "error": ["page not found", "error", "404", "찾을 수 없", "존재하지 않",
              "not found", "오류가", "서비스 점검", "일시적으로 이용"],
}
PRICE_RE = re.compile(r"(\d[\d,]{2,}\s*원)|(₩\s*\d)|(\d+\s*%\s*(할인|off|OFF))|(최저가)|(판매가)|(정가)")


def hits(text: str, key: str) -> int:
    t = text.lower()
    return sum(1 for w in LEX[key] if w.lower() in t)


def wilson(k: int, n: int, z: float = 1.959963985) -> tuple[float, float]:
    if n == 0:
        return (float("nan"), float("nan"))
    p = k / n
    d = 1 + z * z / n
    c = p + z * z / (2 * n)
    h = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return (float((c - h) / d), float((c + h) / d))


def sha256_file(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


# ======================================================================================
# Stage 2 — atomic predicate 추출 (세 구조가 공유)
# ======================================================================================
TEXTCOLS = ["title", "meta_description", "headings", "landmarks", "nav_links", "buttons",
            "aria_labels", "placeholders", "form_labels", "input_names", "card_texts",
            "url_tokens"]


def atomic_predicates(o: pd.Series, t: pd.Series) -> dict:
    def g(c: str) -> str:
        v = t.get(c)
        return "" if (v is None or (isinstance(v, float) and np.isnan(v))) else str(v)

    title = g("title")
    heads = g("headings")
    lands = g("landmarks")
    navs = g("nav_links")
    btns = g("buttons")
    aria = g("aria_labels")
    place_h = g("placeholders")
    flabels = g("form_labels")
    inames = g("input_names")
    cards = g("card_texts")
    urlt = g("url_tokens")
    blob = " | ".join(g(c) for c in TEXTCOLS)

    # 검색 표면 = 검색 input 을 노출하는 컨트롤 문맥
    query_surface = " ".join([place_h, aria, btns, inames, flabels])
    n_cards = len([c for c in cards.split("|") if c.strip()]) if cards else 0
    n_heads = len([c for c in heads.split("|") if c.strip()]) if heads else 0

    def num(c, default=0.0):
        v = o.get(c)
        try:
            f = float(v)
        except (TypeError, ValueError):
            return default
        return default if np.isnan(f) else f

    P = {}
    # --- Stage 0 (SSOT §2)
    P["EMPTY"] = bool(num("dom_body_empty") >= 1)
    P["ERROR_PAGE"] = hits(title + " " + heads, "error") >= 1
    # --- Query-like (§4)
    P["SEARCH_INPUT"] = bool(num("search_inputs_n") >= 1) or hits(query_surface, "search") >= 1
    P["SEARCH_SUBMIT"] = (hits(btns + " " + aria, "search_submit") >= 1
                          and num("dom_input_n") >= 1) or bool(num("search_inputs_n") >= 1)
    # --- Content-like (§4)
    P["CONTENT_CARDS"] = n_cards >= 3 and hits(cards + " " + heads, "content_card") >= 1
    P["ARTICLE"] = bool(num("article_present") >= 1)
    P["MEDIA_CTRL"] = hits(btns + " " + aria + " " + heads + " " + navs, "media") >= 1
    # --- Item-like (§4)
    P["ITEM_CARDS"] = n_cards >= 3 and hits(cards + " " + heads, "item") >= 2
    P["PRICE"] = bool(PRICE_RE.search(blob))
    P["TXN_CTRL"] = hits(btns + " " + aria + " " + cards + " " + navs, "txn") >= 1
    # --- Place-like (§4)
    P["PLACE_CTRL"] = hits(btns + " " + aria + " " + place_h + " " + navs + " " + urlt, "place") >= 2
    P["PLACE_CARDS"] = n_cards >= 3 and hits(cards, "place") >= 2
    P["PLACE_DETAIL"] = hits(btns + " " + aria + " " + heads + " " + cards, "place_detail") >= 2
    # --- Communication-like (§4)
    P["THREAD_LIST"] = n_cards >= 3 and hits(cards + " " + heads, "comm") >= 2
    P["COMPOSE_CTRL"] = hits(btns + " " + aria + " " + navs, "compose") >= 1
    # SSOT §5 Branch M: "로그인 버튼 존재만으로 endpoint 처리하지 않는다" → 실제 gate 만
    P["LOGIN_GATE"] = bool(num("gate_password_input_n") >= 1)
    # --- Finance-like (§4)
    P["FIN_CTRL"] = hits(heads + " " + navs + " " + cards + " " + lands, "fin") >= 3
    P["FIN_HEAD"] = hits(title + " " + heads, "fin") >= 1
    # --- Utility-like (§4)
    P["TOOL_SURFACE"] = hits(title + " " + heads + " " + navs, "util") >= 1
    P["TOOL_PRIMARY"] = num("dom_input_n") >= 1 and len(btns.strip()) > 0
    P["_n_cards"] = n_cards
    P["_n_heads"] = n_heads
    return P


# ======================================================================================
# Stage 3 — branch tree (SSOT §5).  R = region evidence, E = endpoint-enabling evidence
# 정적 landing snapshot 1 장이므로 endpoint(상태전이)를 관측할 수 없다.
# → 모든 branch 의 E 를 "endpoint-enabling control 의 존재" 로 강등한다 (DEFINITION).
#   이 강등은 coverage 를 낙관적으로 올리는 방향이다.
# ======================================================================================
def branch_RE(P: dict) -> dict:
    return {
        "QUERY": (P["SEARCH_INPUT"], P["SEARCH_SUBMIT"]),
        "CONTENT_OPEN": (P["CONTENT_CARDS"], P["ARTICLE"] or P["MEDIA_CTRL"]),
        "ITEM_DETAIL": (P["ITEM_CARDS"], P["PRICE"] and P["TXN_CTRL"]),
        "PLACE_LOOKUP": (P["PLACE_CTRL"] or P["PLACE_CARDS"],
                         P["PLACE_DETAIL"] or (P["PLACE_CTRL"] and P["SEARCH_SUBMIT"])),
        "COMMUNICATION_ENTRY": (P["THREAD_LIST"] or P["COMPOSE_CTRL"],
                                P["COMPOSE_CTRL"] or P["THREAD_LIST"] or P["LOGIN_GATE"]),
        "FINANCIAL_ACTION_ENTRY": (P["FIN_CTRL"], P["LOGIN_GATE"] or P["FIN_HEAD"]),
        "UTILITY_ENTRY": (P["TOOL_SURFACE"], P["TOOL_PRIMARY"]),
    }


# ======================================================================================
# LEVEL 1 predicate — primitive 수준의 R/E 합집합.
# branch 단위가 아니라 primitive 단위로 region/endpoint 를 본다는 것이 계층 구조의 실체다.
# ======================================================================================
def primitive_RE(P: dict) -> dict:
    return {
        # 질의 제출: 질의 가능한 컨트롤(일반검색 또는 장소검색) + 제출 컨트롤
        "L1_QUERY_SUBMISSION": (P["SEARCH_INPUT"] or P["PLACE_CTRL"] or P["PLACE_CARDS"],
                                P["SEARCH_SUBMIT"]),
        # 객체 열기: 열 수 있는 객체 목록(반복 카드/링크 리스트) + 상세문서 진입 evidence
        "L1_OBJECT_OPENING": (P["CONTENT_CARDS"] or P["ITEM_CARDS"] or P["PLACE_CARDS"]
                              or P["THREAD_LIST"],
                              P["ARTICLE"] or P["MEDIA_CTRL"] or (P["PRICE"] and P["TXN_CTRL"])
                              or P["PLACE_DETAIL"] or P["THREAD_LIST"]),
        # 인증·행위 진입: 행위 기능 entry 컨트롤 + 기능면/게이트 evidence
        "L1_AUTH_ACTION_ENTRY": (P["FIN_CTRL"] or P["COMPOSE_CTRL"],
                                 P["LOGIN_GATE"] or P["FIN_HEAD"] or P["COMPOSE_CTRL"]),
        # 도구면 진입: 단일목적 기능면 + primary control
        "L1_UTILITY_TOOL_ENTRY": (P["TOOL_SURFACE"], P["TOOL_PRIMARY"]),
    }


# ======================================================================================
# LEVEL 2 discriminator — primitive 안에서만 archetype 을 가른다.
# ======================================================================================
def level2_disc(prim: str, P: dict) -> dict:
    if prim == "L1_QUERY_SUBMISSION":
        return {"QUERY": P["SEARCH_INPUT"] and not (P["PLACE_CTRL"] or P["PLACE_CARDS"]),
                "PLACE_LOOKUP": P["PLACE_CTRL"] or P["PLACE_CARDS"]}
    if prim == "L1_OBJECT_OPENING":
        return {"ITEM_DETAIL": P["PRICE"] and P["TXN_CTRL"] and P["ITEM_CARDS"],
                "PLACE_LOOKUP": P["PLACE_CARDS"] or (P["PLACE_CTRL"] and P["PLACE_DETAIL"]),
                "COMMUNICATION_ENTRY": P["THREAD_LIST"] or P["COMPOSE_CTRL"],
                "CONTENT_OPEN": P["ARTICLE"] or (P["CONTENT_CARDS"] and P["MEDIA_CTRL"])}
    if prim == "L1_AUTH_ACTION_ENTRY":
        return {"FINANCIAL_ACTION_ENTRY": P["FIN_CTRL"] and (P["LOGIN_GATE"] or P["FIN_HEAD"]),
                "COMMUNICATION_ENTRY": P["COMPOSE_CTRL"] or P["THREAD_LIST"]}
    if prim == "L1_UTILITY_TOOL_ENTRY":
        return {"UTILITY_ENTRY": True}
    raise KeyError(prim)


# ======================================================================================
# 세 구조의 실행기
# ======================================================================================
def run_flat(P: dict) -> dict:
    if P["EMPTY"] or P["ERROR_PAGE"]:
        return {"leaf": "ABSTAIN", "outcome": "S0_UNDETERMINED", "pred": None,
                "trace": "Stage0: empty body or error page"}
    re_ = branch_RE(P)
    strong = [b for b, (r, e) in re_.items() if r and e]
    weak = [b for b, (r, e) in re_.items() if (r or e) and not (r and e)]
    if len(strong) == 1:
        return {"leaf": "MAPPED", "outcome": "MAPPED", "pred": strong[0],
                "trace": f"unique strong branch={strong[0]}; weak={sorted(weak)}"}
    if len(strong) >= 2:
        return {"leaf": "ABSTAIN", "outcome": "ABSTAIN_MULTI_BRANCH", "pred": None,
                "trace": f"strong={sorted(strong)} (SSOT §6: 2개 이상 강후보 → NLP fallback)"}
    return {"leaf": "ABSTAIN", "outcome": "ABSTAIN_NO_BRANCH", "pred": None,
            "trace": f"no strong branch; weak={sorted(weak)}"}


def run_level1(P: dict, mode: str = "mix") -> dict:
    """mode='mix'  : primitive 수준 R/E 합집합 (계층 구조의 본체)
       mode='strict': flat 강후보 집합의 단순 조대화 (민감도)"""
    if P["EMPTY"] or P["ERROR_PAGE"]:
        return {"prim": None, "outcome": "S0_UNDETERMINED", "strong": []}
    if mode == "mix":
        pre = primitive_RE(P)
        strong = [p for p, (r, e) in pre.items() if r and e]
    else:
        re_ = branch_RE(P)
        sb = [b for b, (r, e) in re_.items() if r and e]
        strong = sorted({p for b in sb for p, ms in LEVEL1.items() if b in ms})
    if len(strong) == 1:
        return {"prim": strong[0], "outcome": "L1_RESOLVED", "strong": strong}
    if len(strong) >= 2:
        return {"prim": None, "outcome": "ABSTAIN_L1_MULTI", "strong": sorted(strong)}
    return {"prim": None, "outcome": "ABSTAIN_L1_NONE", "strong": []}


def run_hier_rule(P: dict, mode: str = "mix") -> dict:
    l1 = run_level1(P, mode)
    if l1["prim"] is None:
        return {"leaf": "ABSTAIN", "outcome": l1["outcome"], "prim": None, "pred": None,
                "trace": f"L1 strong={l1['strong']}"}
    d = level2_disc(l1["prim"], P)
    fired = [a for a, v in d.items() if v]
    if len(fired) == 1:
        return {"leaf": "MAPPED", "outcome": "MAPPED", "prim": l1["prim"], "pred": fired[0],
                "trace": f"L1={l1['prim']} → L2 unique={fired[0]}"}
    if len(fired) >= 2:
        return {"leaf": "ABSTAIN", "outcome": "ABSTAIN_L2_MULTI", "prim": l1["prim"], "pred": None,
                "trace": f"L1={l1['prim']} → L2 tie={sorted(fired)}"}
    return {"leaf": "ABSTAIN", "outcome": "ABSTAIN_L2_NONE", "prim": l1["prim"], "pred": None,
            "trace": f"L1={l1['prim']} → L2 없음"}


# ======================================================================================
# Semantic Level 2 — prototype = SSOT §5 branch 질문 텍스트
# ======================================================================================
PROTO = {
    "QUERY": "사용자가 자유 텍스트 질의를 제출하는 것이 대표행동인가. 검색 입력창, 검색어 입력, "
             "검색 폼, 검색 제출 버튼, 질의 결과 목록으로의 전환.",
    "CONTENT_OPEN": "이미 존재하는 기사·영상·콘텐츠 한 건을 선택해 소비를 시작하는 것이 대표행동인가. "
                    "콘텐츠 카드 목록, 기사 본문 열기, 영상 재생 시작.",
    "ITEM_DETAIL": "거래 대상 한 건의 상세면에 들어가 핵심정보를 보는 것이 대표행동인가. "
                   "상품 카드 목록, 상품명, 가격, 장바구니·구매·주문 컨트롤의 존재.",
    "PLACE_LOOKUP": "장소를 질의하거나 특정 장소 상세를 여는 것이 대표행동인가. "
                    "지도, 장소 검색, 주소, 길찾기, 장소 목록, 장소 상세 패널.",
    "COMMUNICATION_ENTRY": "사람 사이의 게시물·스레드·메시지 교환 공간에 진입하는 것이 대표행동인가. "
                           "게시글 목록, 스레드, 댓글, 글쓰기 진입, 커뮤니티, 메시지.",
    "FINANCIAL_ACTION_ENTRY": "금융처리 기능의 시작면 또는 그 기능을 시작하기 위한 실제 로그인·본인인증 "
                              "게이트까지 가는 것이 대표행동인가. 계좌, 잔액, 이체, 결제, 인증.",
    "UTILITY_ENTRY": "특정 목적의 도구 기능면을 열고 첫 primary control 을 사용할 수 있는 상태로 "
                     "만드는 것이 대표행동인가. 단일 목적 기능 화면과 기본 컨트롤.",
}
EMB_MODEL = "BAAI/bge-m3"


def embed(docs: list[str]) -> tuple[np.ndarray, np.ndarray, dict]:
    from sentence_transformers import SentenceTransformer
    import torch
    torch.manual_seed(SEED)
    m = SentenceTransformer(EMB_MODEL, device="cuda" if torch.cuda.is_available() else "cpu")
    tok = m.tokenizer
    lens = [len(tok(d, add_special_tokens=True)["input_ids"]) for d in docs]
    info = {"model": EMB_MODEL, "max_seq_length": int(m.max_seq_length),
            "dim": int(m.get_sentence_embedding_dimension()),
            "doc_subword_len_median": float(np.median(lens)),
            "doc_subword_len_max": int(max(lens)),
            "n_docs_truncated": int(sum(1 for l in lens if l > m.max_seq_length))}
    D = m.encode(docs, batch_size=4, normalize_embeddings=True, convert_to_numpy=True,
                 show_progress_bar=False).astype(np.float64)
    Pm = m.encode([PROTO[a] for a in ARCHETYPES], batch_size=8, normalize_embeddings=True,
                  convert_to_numpy=True, show_progress_bar=False).astype(np.float64)
    return D, Pm, info


# ======================================================================================
# 평가
# ======================================================================================
def evaluate(name: str, rows: list[dict], n: int) -> dict:
    mapped = [r for r in rows if r[name + "_leaf"] == "MAPPED"]
    cov_n = len(mapped)
    agree = sum(1 for r in mapped if r[name + "_pred"] == r["prior_archetype"])
    lo_c, hi_c = wilson(cov_n, n)
    lo_a, hi_a = wilson(agree, cov_n) if cov_n else (float("nan"), float("nan"))
    lo_ao, hi_ao = wilson(agree, n)
    outc = {}
    for r in rows:
        outc[r[name + "_outcome"]] = outc.get(r[name + "_outcome"], 0) + 1
    per = {}
    for a in ARCHETYPES:
        n_prior = sum(1 for r in rows if r["prior_archetype"] == a)
        n_pred = sum(1 for r in mapped if r[name + "_pred"] == a)
        tp = sum(1 for r in mapped if r[name + "_pred"] == a and r["prior_archetype"] == a)
        rec = tp / n_prior if n_prior else float("nan")
        pre = tp / n_pred if n_pred else float("nan")
        rlo, rhi = wilson(tp, n_prior) if n_prior else (float("nan"),) * 2
        plo, phi = wilson(tp, n_pred) if n_pred else (float("nan"),) * 2
        per[a] = {"support_prior": n_prior, "n_predicted": n_pred, "tp": tp,
                  "recall_vs_prior": rec, "recall_ci": [rlo, rhi],
                  "precision_vs_prior": pre, "precision_ci": [plo, phi]}
    return {
        "structure": name, "n": n,
        "n_mapped": cov_n, "coverage": cov_n / n, "coverage_ci": [lo_c, hi_c],
        "n_abstain": n - cov_n, "abstention_rate": (n - cov_n) / n,
        "n_prior_agree": agree,
        "prior_agreement_within_coverage": (agree / cov_n) if cov_n else float("nan"),
        "prior_agreement_within_coverage_ci": [lo_a, hi_a],
        "prior_agreement_within_coverage_fraction": f"{agree}/{cov_n}",
        "prior_agreement_overall": agree / n,
        "prior_agreement_overall_ci": [lo_ao, hi_ao],
        "prior_agreement_overall_fraction": f"{agree}/{n}",
        "outcome_counts": dict(sorted(outc.items())),
        "per_class": per,
    }


def main() -> dict:
    obs = pd.read_csv(OBS)
    txt = pd.read_csv(TXT)
    mart = obs[obs["in_mart"] == 1].copy()
    n = len(mart)
    tmap = {r["wtg"]: r for _, r in txt.iterrows()}

    rows = []
    pred_fire = {}
    for _, o in mart.iterrows():
        t = tmap.get(o["wtg"], pd.Series(dtype=object))
        P = atomic_predicates(o, t)
        for k, v in P.items():
            if not k.startswith("_"):
                pred_fire[k] = pred_fire.get(k, 0) + int(bool(v))
        flat = run_flat(P)
        h = run_hier_rule(P, "mix")
        hs = run_hier_rule(P, "strict")
        l1 = run_level1(P, "mix")
        rows.append({
            "wtg": o["wtg"], "prior_archetype": o["prior_archetype"],
            "prior_business_domain": o["prior_business_domain"],
            "prior_service": o.get("prior_service"),
            "predicates": {k: bool(v) for k, v in P.items() if not k.startswith("_")},
            "n_cards": P["_n_cards"],
            "flat_leaf": flat["leaf"], "flat_outcome": flat["outcome"],
            "flat_pred": flat["pred"], "flat_trace": flat["trace"],
            "l1_prim": l1["prim"], "l1_outcome": l1["outcome"], "l1_strong": l1["strong"],
            "hier_rule_leaf": h["leaf"], "hier_rule_outcome": h["outcome"],
            "hier_rule_pred": h["pred"], "hier_rule_trace": h["trace"],
            "hier_strict_leaf": hs["leaf"], "hier_strict_outcome": hs["outcome"],
            "hier_strict_pred": hs["pred"], "hier_strict_trace": hs["trace"],
        })

    # ---------------- Structure 3: hierarchical + semantic Level 2
    docs = []
    for r in rows:
        t = tmap.get(r["wtg"])
        docs.append("" if t is None else str(t.get("text_blob", "") or ""))
    D, Pm, einfo = embed(docs)
    aidx = {a: i for i, a in enumerate(ARCHETYPES)}
    for i, r in enumerate(rows):
        sims = D[i] @ Pm.T
        r["sims_all"] = {a: float(sims[aidx[a]]) for a in ARCHETYPES}
        if r["l1_prim"] is None:
            r["hier_sem_leaf"] = "ABSTAIN"
            r["hier_sem_outcome"] = r["l1_outcome"]
            r["hier_sem_pred"] = None
            r["hier_sem_margin"] = float("nan")
            r["hier_sem_trace"] = f"L1 abstain: {r['l1_outcome']}"
            r["hier_sem_m02_leaf"] = "ABSTAIN"
            r["hier_sem_m02_outcome"] = r["l1_outcome"]
            r["hier_sem_m02_pred"] = None
            continue
        cands = LEVEL1[r["l1_prim"]]
        cs = sorted(((float(sims[aidx[a]]), a) for a in cands), reverse=True)
        top = cs[0][1]
        margin = cs[0][0] - cs[1][0] if len(cs) > 1 else float("inf")
        r["hier_sem_leaf"] = "MAPPED"
        r["hier_sem_outcome"] = "MAPPED"
        r["hier_sem_pred"] = top
        r["hier_sem_margin"] = margin
        r["hier_sem_trace"] = (f"L1={r['l1_prim']} → L2 semantic rank "
                               + " > ".join(f"{a}:{s:.4f}" for s, a in cs))
        # 사전 선언한 margin 임계 0.02 (calibration 없음 — 민감도 전용)
        if margin >= 0.02:
            r["hier_sem_m02_leaf"] = "MAPPED"
            r["hier_sem_m02_outcome"] = "MAPPED"
            r["hier_sem_m02_pred"] = top
        else:
            r["hier_sem_m02_leaf"] = "ABSTAIN"
            r["hier_sem_m02_outcome"] = "ABSTAIN_L2_LOW_MARGIN"
            r["hier_sem_m02_pred"] = None

    # 참고 대조: 계층 없이 전체 7-way semantic argmax (Level1 이 실제로 제약하는지 확인용)
    for i, r in enumerate(rows):
        sims = D[i] @ Pm.T
        r["flat_sem_pred"] = ARCHETYPES[int(np.argmax(sims))]

    # ---------------- 평가
    S = {name: evaluate(name, rows, n)
         for name in ["flat", "hier_rule", "hier_strict", "hier_sem", "hier_sem_m02"]}

    # ---------------- Level 1 자체 지표
    l1_resolved = [r for r in rows if r["l1_prim"] is not None]
    n_l1 = len(l1_resolved)
    l1_agree = sum(1 for r in l1_resolved if r["l1_prim"] in PRIOR_PRIMITIVES[r["prior_archetype"]])
    lo, hi = wilson(l1_agree, n_l1) if n_l1 else (float("nan"),) * 2
    l1_out = {}
    for r in rows:
        l1_out[r["l1_outcome"]] = l1_out.get(r["l1_outcome"], 0) + 1
    l1_conf = {}
    for r in rows:
        key = r["prior_archetype"]
        l1_conf.setdefault(key, {})
        k2 = r["l1_prim"] or r["l1_outcome"]
        l1_conf[key][k2] = l1_conf[key].get(k2, 0) + 1

    # Level 2 조건부 (분모 = Level 1 통과분)
    def l2_block(name: str) -> dict:
        m = sum(1 for r in l1_resolved if r[name + "_leaf"] == "MAPPED")
        ag = sum(1 for r in l1_resolved
                 if r[name + "_leaf"] == "MAPPED" and r[name + "_pred"] == r["prior_archetype"])
        lo2, hi2 = wilson(m, n_l1) if n_l1 else (float("nan"),) * 2
        lo3, hi3 = wilson(ag, m) if m else (float("nan"),) * 2
        return {"denominator_note": "분모 = Level 1 이 유일 primitive 를 확정한 target 수",
                "n_level1_passed": n_l1, "n_level2_mapped": m,
                "level2_coverage_conditional": (m / n_l1) if n_l1 else float("nan"),
                "level2_coverage_conditional_ci": [lo2, hi2],
                "level2_abstention_conditional": ((n_l1 - m) / n_l1) if n_l1 else float("nan"),
                "prior_agreement_within_level2_coverage": (ag / m) if m else float("nan"),
                "prior_agreement_within_level2_coverage_ci": [lo3, hi3],
                "fraction": f"{ag}/{m}"}

    level1_block = {
        "definition_source": "SSOT 01 §5 각 branch 의 Endpoint 절",
        "primitives": LEVEL1,
        "archetype_to_primitives": PRIOR_PRIMITIVES,
        "is_partition_of_7": False,
        "multi_primitive_archetypes": [a for a, ps in PRIOR_PRIMITIVES.items() if len(ps) > 1],
        "n": n, "n_l1_resolved": n_l1,
        "l1_coverage": n_l1 / n, "l1_coverage_ci": list(wilson(n_l1, n)),
        "l1_abstention": (n - n_l1) / n,
        "l1_outcome_counts": dict(sorted(l1_out.items())),
        "l1_prior_primitive_agreement": (l1_agree / n_l1) if n_l1 else float("nan"),
        "l1_prior_primitive_agreement_ci": [lo, hi],
        "l1_prior_primitive_agreement_fraction": f"{l1_agree}/{n_l1}",
        "l1_prior_primitive_agreement_note": (
            "PLACE_LOOKUP·COMMUNICATION_ENTRY 는 prior 가 primitive 2 개에 속하므로 "
            "둘 중 어느 쪽이든 일치로 센다. 이 규칙은 L1 agreement 를 낙관적으로 올린다."),
        "l1_confusion_prior_x_primitive": l1_conf,
        "l1_assigned_counts": {p: sum(1 for r in rows if r["l1_prim"] == p) for p in LEVEL1},
    }

    # ---------------- 가설 판정
    cov_f, cov_h = S["flat"]["coverage"], S["hier_rule"]["coverage"]
    ag_f = S["flat"]["prior_agreement_within_coverage"]
    ag_h = S["hier_rule"]["prior_agreement_within_coverage"]
    ago_f, ago_h = S["flat"]["prior_agreement_overall"], S["hier_rule"]["prior_agreement_overall"]

    # flat 과 hier 의 매핑 차이 (동일 7-way output 기준)
    delta = {"flat_only_mapped": [], "hier_only_mapped": [], "both_mapped_same": [],
             "both_mapped_diff": []}
    for r in rows:
        f, h = r["flat_leaf"] == "MAPPED", r["hier_rule_leaf"] == "MAPPED"
        if f and not h:
            delta["flat_only_mapped"].append([r["wtg"], r["flat_pred"], r["prior_archetype"],
                                              r["hier_rule_outcome"]])
        elif h and not f:
            delta["hier_only_mapped"].append([r["wtg"], r["hier_rule_pred"], r["prior_archetype"],
                                              r["flat_outcome"]])
        elif f and h:
            (delta["both_mapped_same"] if r["flat_pred"] == r["hier_rule_pred"]
             else delta["both_mapped_diff"]).append(
                [r["wtg"], r["flat_pred"], r["hier_rule_pred"], r["prior_archetype"]])

    # McNemar 유사 대칭성 검정 (prior 일치 여부의 짝지은 불일치)
    b = sum(1 for r in rows if (r["flat_leaf"] == "MAPPED" and r["flat_pred"] == r["prior_archetype"])
            and not (r["hier_rule_leaf"] == "MAPPED" and r["hier_rule_pred"] == r["prior_archetype"]))
    c = sum(1 for r in rows if not (r["flat_leaf"] == "MAPPED" and r["flat_pred"] == r["prior_archetype"])
            and (r["hier_rule_leaf"] == "MAPPED" and r["hier_rule_pred"] == r["prior_archetype"]))
    try:
        from scipy.stats import binomtest
        p_mc = float(binomtest(min(b, c), b + c, 0.5).pvalue) if (b + c) > 0 else float("nan")
    except Exception:
        p_mc = float("nan")

    hyp = {
        "H-D1_HIERARCHY_HELPS": {
            "statement": "계층 구조가 flat 보다 coverage 를 올리거나 같은 coverage 에서 "
                         "prior_agreement 를 올린다",
            "coverage_flat": cov_f, "coverage_hier": cov_h,
            "prior_agreement_within_coverage_flat": ag_f,
            "prior_agreement_within_coverage_hier": ag_h,
            "prior_agreement_overall_flat": ago_f, "prior_agreement_overall_hier": ago_h,
            "mcnemar_b_flat_only_agree": b, "mcnemar_c_hier_only_agree": c,
            "mcnemar_exact_p": p_mc,
        },
        "H-D2_LEVEL1_IS_EASY": {
            "statement": "Level 1(4 primitive)은 관측 evidence 로 잘 갈리는데 Level 2 가 어렵다",
            "l1_coverage": level1_block["l1_coverage"],
            "l1_prior_primitive_agreement": level1_block["l1_prior_primitive_agreement"],
            "l2_conditional_coverage_rule": l2_block("hier_rule")["level2_coverage_conditional"],
            "l2_agreement_rule": l2_block("hier_rule")["prior_agreement_within_level2_coverage"],
            "warning": "L1 은 4-way, 최종은 7-way 다. 분모와 class 수가 달라 직접 비교하면 안 된다.",
        },
        "H-D3_NO_GAIN": {
            "statement": "계층은 flat 과 실질 차이가 없다",
            "n_both_mapped_same": len(delta["both_mapped_same"]),
            "n_both_mapped_diff": len(delta["both_mapped_diff"]),
            "n_flat_only": len(delta["flat_only_mapped"]),
            "n_hier_only": len(delta["hier_only_mapped"]),
        },
    }

    doc = {
        "verdict": "PENDING",
        "hypothesis_id": "H-RF2-D-HIERARCHY",
        "child_id": "D-RF2-D", "rq_id": "RQ-D-RF-002", "parent_run_id": PARENT,
        "rule_version": RULE_VERSION, "seed": SEED,
        "generated_at_kst": datetime.now(KST).isoformat(),
        "final_output_space": ARCHETYPES + ["ABSTAIN"],
        "construct_note": ("최종 leaf 는 frozen 7 archetype 그대로다. Level 1 primitive 는 "
                           "중간 단계이며 leaf 가 아니다. 새 class 를 만들지 않았다."),
        "label_note": ("prior_archetype 은 gold label 이 아니라 prior 다. 따라서 accuracy 가 "
                       "아니라 prior_agreement 로만 보고한다."),
        "assertion_types": {
            "coverage / abstention / prior_agreement 수치": "OBSERVATION",
            "Level 1 primitive 정의": "DEFINITION",
            "endpoint 를 'endpoint-enabling control 존재' 로 강등": "DEFINITION",
            "계층이 정보를 늘리는가에 대한 판단": "ANALYSIS",
            "규칙·임베딩 구현": "IMPLEMENTATION",
            "REAL_TARGET 일반화": "PROJECTION",
        },
        "inputs": [
            {"path": str(OBS), "rows_used": n, "sha256": sha256_file(OBS)},
            {"path": str(TXT), "rows": len(txt), "sha256": sha256_file(TXT)},
            {"path": str(SSOT), "role": "rule source §5 branch tree · §6 resolver",
             "sha256": sha256_file(SSOT)},
        ],
        "analysis_unit": "web target (wtg), in_mart==1",
        "n_expected": 59, "n_observed": n, "missing_n": 59 - n,
        "prior_class_counts": {a: int((mart["prior_archetype"] == a).sum()) for a in ARCHETYPES},
        "level1": level1_block,
        "level2_conditional": {name: l2_block(name)
                               for name in ["hier_rule", "hier_sem", "hier_sem_m02"]},
        "structures": S,
        "structure_delta_flat_vs_hier": delta,
        "hypotheses": hyp,
        "predicate_firing_counts": dict(sorted(pred_fire.items())),
        "embedding_info": einfo,
        "prototypes": PROTO,
        "flat_semantic_reference": {
            "note": ("Level 1 이 실제로 후보를 제약하는지 확인하기 위한 참고 대조. "
                     "계층 없이 7-way semantic argmax 를 전부 강제 매핑한 경우."),
            "prior_agreement_overall": sum(1 for r in rows
                                           if r["flat_sem_pred"] == r["prior_archetype"]) / n,
            "fraction": f"{sum(1 for r in rows if r['flat_sem_pred'] == r['prior_archetype'])}/{n}",
        },
        "firewall": {
            "holdout_label_opened": False,
            "note": ("holdout label · LABEL_SPLIT_FROZEN* · HOLDOUT_FOR_C* · RAW_L1~L4* · "
                     "PACKET_L* · *_OVERLAP* · PRECEDENCE_CONTESTED* · CALIBRATION_FOR_B* · "
                     "control/ 아래 파일을 하나도 열지 않았다. REAL_TARGET 에 접속하지 않았다. "
                     "gold label 을 만들지 않았다."),
        },
        "rows": rows,
    }
    return doc


def to_jsonable(o):
    if isinstance(o, dict):
        return {str(k): to_jsonable(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [to_jsonable(v) for v in o]
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.floating,)):
        f = float(o)
        return None if np.isnan(f) else f
    if isinstance(o, (np.bool_,)):
        return bool(o)
    if isinstance(o, float):
        return None if np.isnan(o) else o
    if isinstance(o, pd.Series):
        return to_jsonable(o.to_dict())
    if o is None or isinstance(o, (str, int, bool)):
        return o
    return str(o)


if __name__ == "__main__":
    doc = main()
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(to_jsonable(doc), ensure_ascii=False, indent=1),
                        encoding="utf-8")
    S = doc["structures"]
    print(f"n={doc['n_observed']}")
    for k in ["flat", "hier_rule", "hier_strict", "hier_sem", "hier_sem_m02"]:
        s = S[k]
        print(f"{k:14s} cov={s['n_mapped']:2d}/{s['n']}={s['coverage']:.3f}  "
              f"agree_in_cov={s['prior_agreement_within_coverage_fraction']:>7s}  "
              f"agree_overall={s['prior_agreement_overall_fraction']}")
    print("L1:", doc["level1"]["l1_outcome_counts"])
    print("L1 agree:", doc["level1"]["l1_prior_primitive_agreement_fraction"])
    print("predicates:", doc["predicate_firing_counts"])
    print("written:", OUT_JSON)
