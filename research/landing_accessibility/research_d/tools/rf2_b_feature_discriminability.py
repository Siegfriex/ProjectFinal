"""D-RF2-B — Feature discriminability study (RQ-D-RF-002 child).

목적: **존재하는 feature** 와 **구별력이 있는 feature** 를 분리한다.

원칙 (위반 금지):
  * `prior_archetype` 은 gold label 이 아니라 **prior** 다. exploratory coloring / reference 로만 쓴다.
    "prior 를 정답으로 학습했다" 고 표현하지 않는다. "accuracy" 라는 단어를 쓰지 않는다.
    prior 와의 통계적 관계는 `prior_agreement` / `information_about_prior` 로 부른다.
  * MI 는 n=56 · 7 class · 최소 class n=3 에서 **상향 편향**된다. 따라서 permutation null
    (prior 셔플) 없이 MI 를 보고하지 않는다.
  * feature 정의(임계값 포함)는 MI 계산 **이전에** 확정하고, 결과를 보고 사후 수정하지 않는다.
    threshold 는 prior 를 보지 않은 상태에서 각 변수의 **주변 분포만** 보고 골랐다.

방화벽: 이 스크립트는 holdout label · LABEL_SPLIT_FROZEN* · HOLDOUT_FOR_C* · RAW_L1~L4* ·
PACKET_L* · *_OVERLAP* · PRECEDENCE_CONTESTED* · CALIBRATION_FOR_B* · **/control/** 를
**열지 않았다**. 입력은 아래 두 파일뿐이다.
"""
from __future__ import annotations

import hashlib
import json
import math
import re
import sys
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd

RD = Path("/home/sieg/projects-wsl/ProjectFinal/.agent_worktrees/claude_d_research/"
          "research/landing_accessibility/research_d")
OBS = RD / "results" / "D_OBSERVATION_TABLE_v2.csv"
TXT = RD / "results" / "D_TEXT_CORPUS_v2.csv"
OUT_JSON = RD / "results" / "RF2_B_feature_discriminability.json"
FIGDIR = RD / "figures"
SEED = 20260827
N_PERM = 20000
PARENT = "ae754858ba3a4be391e5f811640d3fd8"

ARCHETYPES = ["ITEM_DETAIL", "FINANCIAL_ACTION_ENTRY", "UTILITY_ENTRY",
              "COMMUNICATION_ENTRY", "PLACE_LOOKUP", "QUERY", "CONTENT_OPEN"]

# ---------------------------------------------------------------- 어휘 사전 (전문)
# 모든 매칭은 lowercase 후 **부분 문자열** 포함 검사다. 한국어는 형태소 분석 없이 문자열
# 포함으로만 판정하므로 과탐(예: FIN 의 "카드" 가 "카드뉴스" 에 맞음)이 발생할 수 있다.
# 이 한계는 결과 문서 limitation 에 명시한다.
LEXICON: dict[str, list[str]] = {
    "SEARCH": [
        "검색", "찾기", "찾아", "조회", "search", "찾으시는", "검색어", "통합검색",
        "keyword", "키워드", "query", "쿼리",
    ],
    "SUBMIT": [
        "확인", "제출", "등록", "적용", "완료", "저장", "보내기", "전송", "신청하기",
        "submit", "apply", "send", "confirm", "ok", "go", "이동", "다음",
    ],
    "PRICE_LEX": [
        "가격", "정가", "판매가", "할인", "원가", "특가", "최저가", "무료배송", "배송비",
        "price", "won", "sale", "discount", "krw",
    ],
    "TXN": [
        "장바구니", "담기", "구매", "주문", "결제", "바로구매", "구입", "쇼핑백", "찜",
        "예약하기", "cart", "buy", "order", "checkout", "purchase", "basket", "add to",
    ],
    "PLACE": [
        "지도", "위치", "주소", "매장", "지점", "점포", "길찾기", "오시는", "찾아오시는",
        "영업시간", "층", "근처", "주변", "지역", "배송지", "map", "location", "address",
        "store locator", "branch", "directions", "nearby", "route",
    ],
    "COMM": [
        "댓글", "글쓰기", "작성", "메시지", "쪽지", "채팅", "문의", "게시", "게시판",
        "커뮤니티", "후기", "리뷰", "상담", "톡", "답글", "구독", "팔로우",
        "comment", "post", "message", "chat", "write", "reply", "review", "community",
        "follow", "inquiry", "contact us",
    ],
    "AUTH": [
        "로그인", "로그아웃", "회원가입", "가입하기", "인증", "본인확인", "비밀번호",
        "아이디", "인증서", "간편인증", "공동인증", "마이페이지", "내정보",
        "login", "log in", "sign in", "signin", "signup", "sign up", "register",
        "password", "auth", "mypage", "account",
    ],
    "FIN": [
        "결제", "송금", "이체", "계좌", "카드", "대출", "한도", "잔액", "납부", "청구",
        "보험", "적금", "예금", "펀드", "투자", "환전", "포인트", "마일리지", "금융",
        "이자", "상환", "요금", "충전",
        "pay", "payment", "transfer", "remit", "account balance", "loan", "credit",
        "banking", "invest", "insurance", "billing",
    ],
    "UTIL": [
        "계산", "계산기", "변환", "발급", "신청", "접수", "예약", "등록", "조회하기",
        "확인하기", "다운로드", "설치", "업로드", "제출하기", "예매",
        "calculator", "convert", "issue", "apply", "reserve", "booking", "download",
        "upload", "lookup", "tracking",
    ],
}
PRICE_REGEX = r"(?:\d[\d,]{2,}\s*원)|(?:₩\s*\d)|(?:krw\s*\d)|(?:\d+\s*%\s*(?:할인|off))"

# ---------------------------------------------------------------- feature 조작화 (사전 확정)
# 각 feature 는 (a) 무엇을 재는지, (b) 어떤 컬럼/사전을 쓰는지, (c) 이진화 규칙,
# (d) 임계값 근거 를 전부 명시한다. 임계값은 prior 를 보지 않은 상태에서 주변 분포만 보고
# 정했고, MI 계산 전에 동결했다.
FEATURE_SPEC: list[dict] = [
    dict(fid="F01_search_input", label="search input surface",
         rule="search_inputs_n >= 1  OR  LEX[SEARCH] ∩ CONTROL_SURFACE ≠ ∅",
         cols=["search_inputs_n", "buttons", "nav_links", "aria_labels", "form_labels",
               "placeholders", "input_names"],
         lexicons=["SEARCH"],
         threshold_basis="존재 판정(>=1). 검색 입력은 개수가 아니라 존재 여부가 archetype 신호."),
    dict(fid="F02_submit_form", label="submit form surface",
         rule="dom_input_n >= 1  AND  (form_labels 비어있지 않음  OR  LEX[SUBMIT] ∩ CONTROL_SURFACE ≠ ∅)",
         cols=["dom_input_n", "form_labels", "buttons", "nav_links", "aria_labels",
               "placeholders", "input_names"],
         lexicons=["SUBMIT"],
         threshold_basis="입력 필드가 하나라도 있고 제출 의미의 컨트롤/라벨이 동반될 때만 '폼'으로 본다."),
    dict(fid="F03_repeated_cards", label="repeated card structure",
         rule="card_texts 의 '|' 분할 항목 수 >= 8",
         cols=["card_texts"], lexicons=[],
         threshold_basis="card_texts 는 수집기에서 25개로 절단(censored)된다. 8 은 25 의 1/3 지점으로, "
                         "'반복 구조'와 '단발 링크 몇 개'를 가르는 보수적 경계."),
    dict(fid="F04_price_evidence", label="price evidence",
         rule="PRICE_REGEX 매치  OR  LEX[PRICE_LEX] ∩ ALL_SURFACE ≠ ∅",
         cols=["card_texts", "headings", "title", "meta_description", "buttons",
               "nav_links", "aria_labels"],
         lexicons=["PRICE_LEX"],
         threshold_basis="존재 판정. 가격은 1회만 나타나도 item-like 증거."),
    dict(fid="F05_transaction_controls", label="transaction controls",
         rule="LEX[TXN] ∩ (CONTROL_SURFACE ∪ CARD_SURFACE) ≠ ∅",
         cols=["buttons", "nav_links", "aria_labels", "form_labels", "placeholders",
               "input_names", "card_texts"],
         lexicons=["TXN"], threshold_basis="존재 판정 (SSOT §4 Item-like: presence evidence only)."),
    dict(fid="F06_map_address_route", label="map / address / route evidence",
         rule="LEX[PLACE] ∩ ALL_SURFACE ≠ ∅",
         cols=["buttons", "nav_links", "aria_labels", "form_labels", "placeholders",
               "input_names", "card_texts", "headings", "title", "meta_description",
               "landmarks", "url_tokens"],
         lexicons=["PLACE"], threshold_basis="존재 판정."),
    dict(fid="F07_communication_surface", label="communication vocabulary / control",
         rule="LEX[COMM] ∩ ALL_SURFACE ≠ ∅",
         cols=["buttons", "nav_links", "aria_labels", "form_labels", "placeholders",
               "input_names", "card_texts", "headings", "title", "meta_description"],
         lexicons=["COMM"], threshold_basis="존재 판정."),
    dict(fid="F08_auth_structure", label="authentication structure",
         rule="gate_password_input_n >= 1  OR  LEX[AUTH] ∩ (CONTROL_SURFACE ∪ url_tokens) ≠ ∅",
         cols=["gate_password_input_n", "buttons", "nav_links", "aria_labels",
               "form_labels", "placeholders", "input_names", "url_tokens"],
         lexicons=["AUTH"], threshold_basis="존재 판정. password 입력은 1개만 있어도 auth gate."),
    dict(fid="F09_financial_action_controls", label="financial action controls",
         rule="LEX[FIN] ∩ (CONTROL_SURFACE ∪ CARD_SURFACE) ≠ ∅",
         cols=["buttons", "nav_links", "aria_labels", "form_labels", "placeholders",
               "input_names", "card_texts"],
         lexicons=["FIN"], threshold_basis="존재 판정."),
    dict(fid="F10_utility_surface", label="utility function surface",
         rule="LEX[UTIL] ∩ CONTROL_SURFACE ≠ ∅  AND  dom_a_href_n <= 30",
         cols=["buttons", "nav_links", "aria_labels", "form_labels", "placeholders",
               "input_names", "dom_a_href_n"],
         lexicons=["UTIL"],
         threshold_basis="SSOT §4 Utility-like = 'single-purpose tool surface'. 단일 목적성을 링크 "
                         "폭으로 대리한다. 30 은 dom_a_href_n 분포의 하위 1/3 근처(25%tile=19, "
                         "50%tile=65) 로, prior 를 보지 않고 주변 분포만으로 정했다."),
    dict(fid="F11_accessible_name_richness", label="accessible-name richness",
         rule="n_accessible_name_sources >= 100",
         cols=["n_accessible_name_sources"], lexicons=[],
         threshold_basis="이 변수는 300 에서 상한 절단(cap)된다(24% 절단). 100 은 상한의 1/3."),
    dict(fid="F12_primary_candidate_count", label="primary candidate count",
         rule="n_primary_action_candidates >= 50",
         cols=["n_primary_action_candidates"], lexicons=[],
         threshold_basis="이 변수는 200 에서 상한 절단된다(13% 절단). 50 은 상한의 1/4."),
    dict(fid="F13_interactive_count", label="interactive element count",
         rule="dom_interactive_n >= 50",
         cols=["dom_interactive_n"], lexicons=[],
         threshold_basis="절단 없음. 50 은 '탐색 가능한 페이지'와 '단순 페이지'의 라운드 넘버 경계."),
    dict(fid="F14_form_count", label="form input count",
         rule="dom_input_n >= 1",
         cols=["dom_input_n"], lexicons=[],
         threshold_basis="존재 판정. F02 의 구조 없는 원시(raw) 버전 — 중복도 비교용으로 일부러 포함."),
    dict(fid="F15_url_path_tokens", label="URL tokens beyond host",
         rule="url_tokens 의 공백 분할 토큰 수 >= 5",
         cols=["url_tokens"], lexicons=[],
         threshold_basis="'https www x com' = 4 토큰(호스트만). 5 이상이면 경로가 있다는 뜻."),
    dict(fid="F16_landmark_structure", label="landmark structure",
         rule="landmarks 비어있지 않음  AND  dom_role_n >= 5",
         cols=["landmarks", "dom_role_n"], lexicons=[],
         threshold_basis="landmark 텍스트 존재 + ARIA role 이 최소 5개(header/nav/main/footer/search 급)."),
]

ORDINAL_SPEC = {  # MI 의 이진화 손실을 보기 위한 보조 변형 (3분위 고정 경계)
    "F03_repeated_cards": ("card_count", [0, 1, 8]),
    "F11_accessible_name_richness": ("n_accessible_name_sources", [0, 50, 200]),
    "F12_primary_candidate_count": ("n_primary_action_candidates", [0, 20, 100]),
    "F13_interactive_count": ("dom_interactive_n", [0, 20, 100]),
    "F14_form_count": ("dom_input_n", [0, 1, 4]),
    "F15_url_path_tokens": ("url_token_count", [0, 4, 6]),
}

TEXT_CONTROL = ["buttons", "nav_links", "aria_labels", "form_labels", "placeholders", "input_names"]
TEXT_CARD = ["card_texts"]
TEXT_CTX = ["headings", "title", "meta_description", "landmarks", "url_tokens"]


# ---------------------------------------------------------------- helpers
def s(v) -> str:
    return "" if not isinstance(v, str) else v


def surface(row: pd.Series, cols: list[str]) -> str:
    return " | ".join(s(row.get(c)) for c in cols).lower()


def lex_hit(text: str, keys: list[str]) -> list[str]:
    hits = []
    for k in keys:
        for term in LEXICON[k]:
            if term in text:
                hits.append(f"{k}:{term}")
    return hits


def pipe_n(v) -> int:
    t = s(v)
    return len([x for x in t.split("|") if x.strip()])


def entropy_bits(counts) -> float:
    c = np.asarray([x for x in counts if x > 0], dtype=float)
    if c.sum() == 0:
        return 0.0
    p = c / c.sum()
    return float(-(p * np.log2(p)).sum())


def mi_bits(x: np.ndarray, y: np.ndarray) -> float:
    """plug-in (maximum-likelihood) mutual information in bits."""
    n = len(x)
    if n == 0:
        return 0.0
    hx = entropy_bits(list(Counter(x).values()))
    hy = entropy_bits(list(Counter(y).values()))
    hxy = entropy_bits(list(Counter(zip(x.tolist(), y.tolist())).values()))
    return float(max(0.0, hx + hy - hxy))


def miller_madow(x: np.ndarray, y: np.ndarray) -> float:
    """Miller-Madow bias-corrected MI (bits). H_MM = H_plugin + (m-1)/(2n)."""
    n = len(x)
    if n == 0:
        return 0.0
    def h_mm(vals):
        c = Counter(vals)
        m = sum(1 for v in c.values() if v > 0)
        return entropy_bits(list(c.values())) + (m - 1) / (2 * n * math.log(2))
    hx = h_mm(x.tolist()); hy = h_mm(y.tolist())
    hxy = h_mm(list(zip(x.tolist(), y.tolist())))
    return float(hx + hy - hxy)


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    if n == 0:
        return (float("nan"), float("nan"))
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (max(0.0, c - h), min(1.0, c + h))


def bh_fdr(pvals: list[float]) -> list[float]:
    m = len(pvals)
    order = np.argsort(pvals)
    q = np.empty(m)
    prev = 1.0
    for rank in range(m - 1, -1, -1):
        i = order[rank]
        prev = min(prev, pvals[i] * m / (rank + 1))
        q[i] = prev
    return q.tolist()


def cramers_v(x: np.ndarray, y: np.ndarray) -> float:
    tab = pd.crosstab(pd.Series(x), pd.Series(y)).values
    n = tab.sum()
    if n == 0 or min(tab.shape) < 2:
        return float("nan")
    exp = np.outer(tab.sum(1), tab.sum(0)) / n
    chi2 = float(((tab - exp) ** 2 / np.where(exp == 0, np.nan, exp)).sum())
    return float(math.sqrt((chi2 / n) / (min(tab.shape) - 1)))


# ---------------------------------------------------------------- 1. load
def load() -> tuple[pd.DataFrame, dict]:
    obs = pd.read_csv(OBS)
    txt = pd.read_csv(TXT)
    mart = obs[obs["in_mart"] == 1].copy()
    df = mart.merge(txt.drop(columns=[c for c in txt.columns
                                      if c in mart.columns and c != "observation_id"]),
                    on="observation_id", how="left", validate="one_to_one")
    prov = {
        "observation_table": {"path": str(OBS), "sha256": hashlib.sha256(OBS.read_bytes()).hexdigest(),
                              "rows": int(len(obs)), "cols": int(obs.shape[1])},
        "text_corpus": {"path": str(TXT), "sha256": hashlib.sha256(TXT.read_bytes()).hexdigest(),
                        "rows": int(len(txt)), "cols": int(txt.shape[1])},
        "join": {"key": "observation_id", "filter": "in_mart == 1",
                 "n_after_filter": int(len(mart)), "n_joined": int(len(df)),
                 "unmatched": int(df["text_blob"].isna().sum()) if "text_blob" in df else None},
    }
    return df, prov


# ---------------------------------------------------------------- 2. featurize
def featurize(df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    rows, evid = [], {}
    for _, r in df.iterrows():
        ctrl = surface(r, TEXT_CONTROL)
        card = surface(r, TEXT_CARD)
        ctx = surface(r, TEXT_CTX)
        alls = " | ".join([ctrl, card, ctx])
        url = s(r.get("url_tokens")).lower()
        card_n = pipe_n(r.get("card_texts"))
        url_n = len(url.split())

        def num(c):
            v = r.get(c)
            return None if pd.isna(v) else float(v)

        out = {"observation_id": r["observation_id"], "prior_archetype": r["prior_archetype"],
               "card_count": card_n, "url_token_count": url_n}
        miss = {}
        e = {}

        # F01
        sn = num("search_inputs_n"); h = lex_hit(ctrl, ["SEARCH"])
        out["F01_search_input"] = int((sn is not None and sn >= 1) or bool(h))
        miss["F01_search_input"] = 0
        e["F01_search_input"] = {"search_inputs_n": sn, "lex_hits": sorted(set(h))[:6]}
        # F02
        di = num("dom_input_n"); fl = bool(s(r.get("form_labels")).strip()); h2 = lex_hit(ctrl, ["SUBMIT"])
        out["F02_submit_form"] = int(di is not None and di >= 1 and (fl or bool(h2))) if di is not None else None
        miss["F02_submit_form"] = int(di is None)
        e["F02_submit_form"] = {"dom_input_n": di, "form_labels_present": fl, "lex_hits": sorted(set(h2))[:6]}
        # F03
        out["F03_repeated_cards"] = int(card_n >= 8); miss["F03_repeated_cards"] = 0
        e["F03_repeated_cards"] = {"card_count": card_n, "censored_at_25": card_n >= 25}
        # F04
        pr = bool(re.search(PRICE_REGEX, alls)); h4 = lex_hit(alls, ["PRICE_LEX"])
        out["F04_price_evidence"] = int(pr or bool(h4)); miss["F04_price_evidence"] = 0
        e["F04_price_evidence"] = {"regex": pr, "lex_hits": sorted(set(h4))[:6]}
        # F05
        h5 = lex_hit(ctrl + " | " + card, ["TXN"])
        out["F05_transaction_controls"] = int(bool(h5)); miss["F05_transaction_controls"] = 0
        e["F05_transaction_controls"] = {"lex_hits": sorted(set(h5))[:6]}
        # F06
        h6 = lex_hit(alls, ["PLACE"])
        out["F06_map_address_route"] = int(bool(h6)); miss["F06_map_address_route"] = 0
        e["F06_map_address_route"] = {"lex_hits": sorted(set(h6))[:6]}
        # F07
        h7 = lex_hit(ctrl + " | " + card + " | " + ctx, ["COMM"])
        out["F07_communication_surface"] = int(bool(h7)); miss["F07_communication_surface"] = 0
        e["F07_communication_surface"] = {"lex_hits": sorted(set(h7))[:6]}
        # F08
        gp = num("gate_password_input_n"); h8 = lex_hit(ctrl + " | " + url, ["AUTH"])
        out["F08_auth_structure"] = int((gp is not None and gp >= 1) or bool(h8)); miss["F08_auth_structure"] = 0
        e["F08_auth_structure"] = {"gate_password_input_n": gp, "lex_hits": sorted(set(h8))[:6]}
        # F09
        h9 = lex_hit(ctrl + " | " + card, ["FIN"])
        out["F09_financial_action_controls"] = int(bool(h9)); miss["F09_financial_action_controls"] = 0
        e["F09_financial_action_controls"] = {"lex_hits": sorted(set(h9))[:6]}
        # F10
        ah = num("dom_a_href_n"); h10 = lex_hit(ctrl, ["UTIL"])
        out["F10_utility_surface"] = int(bool(h10) and ah is not None and ah <= 30) if ah is not None else None
        miss["F10_utility_surface"] = int(ah is None)
        e["F10_utility_surface"] = {"dom_a_href_n": ah, "lex_hits": sorted(set(h10))[:6]}
        # F11..F16
        v = num("n_accessible_name_sources")
        out["F11_accessible_name_richness"] = None if v is None else int(v >= 100)
        miss["F11_accessible_name_richness"] = int(v is None); e["F11_accessible_name_richness"] = {"value": v}
        v = num("n_primary_action_candidates")
        out["F12_primary_candidate_count"] = None if v is None else int(v >= 50)
        miss["F12_primary_candidate_count"] = int(v is None); e["F12_primary_candidate_count"] = {"value": v}
        v = num("dom_interactive_n")
        out["F13_interactive_count"] = None if v is None else int(v >= 50)
        miss["F13_interactive_count"] = int(v is None); e["F13_interactive_count"] = {"value": v}
        v = num("dom_input_n")
        out["F14_form_count"] = None if v is None else int(v >= 1)
        miss["F14_form_count"] = int(v is None); e["F14_form_count"] = {"value": v}
        out["F15_url_path_tokens"] = int(url_n >= 5); miss["F15_url_path_tokens"] = 0
        e["F15_url_path_tokens"] = {"url_token_count": url_n}
        lm = bool(s(r.get("landmarks")).strip()); rn = num("dom_role_n")
        out["F16_landmark_structure"] = None if rn is None else int(lm and rn >= 5)
        miss["F16_landmark_structure"] = int(rn is None)
        e["F16_landmark_structure"] = {"landmarks_present": lm, "dom_role_n": rn}

        rows.append(out)
        evid[r["observation_id"]] = e
    return pd.DataFrame(rows), evid


# ---------------------------------------------------------------- 3. per-feature statistics
def feature_stats(F: pd.DataFrame, rng: np.random.Generator) -> tuple[list[dict], dict]:
    y_all = F["prior_archetype"].to_numpy()
    fids = [sp["fid"] for sp in FEATURE_SPEC]
    stats, perm_store = [], {}
    for sp in FEATURE_SPEC:
        fid = sp["fid"]
        col = F[fid]
        obs_mask = col.notna().to_numpy()
        x = col[obs_mask].astype(int).to_numpy()
        y = y_all[obs_mask]
        n = int(obs_mask.sum())
        k = int(x.sum())
        lo, hi = wilson(k, n)

        # conditional prevalence
        cond = {}
        for a in ARCHETYPES:
            sel = y == a
            na = int(sel.sum()); ka = int(x[sel].sum())
            clo, chi = wilson(ka, na)
            cond[a] = {"n": na, "k": ka,
                       "prevalence": (ka / na) if na else None,
                       "ci95_lo": clo, "ci95_hi": chi,
                       "small_n_warning": na <= 5}

        mi = mi_bits(x, y)
        mi_mm = miller_madow(x, y)
        hy = entropy_bits(list(Counter(y.tolist()).values()))
        # permutation null: prior 를 셔플 (feature 는 고정)
        null = np.empty(N_PERM)
        yp = y.copy()
        for b in range(N_PERM):
            rng.shuffle(yp)
            null[b] = mi_bits(x, yp)
        p = float((1 + int((null >= mi - 1e-12).sum())) / (N_PERM + 1))
        perm_store[fid] = null

        stats.append({
            "feature_id": fid, "label": sp["label"], "rule": sp["rule"],
            "source_columns": sp["cols"], "lexicons": sp["lexicons"],
            "threshold_basis": sp["threshold_basis"],
            "n_defined": n, "n_missing": int(len(F) - n),
            "missing_rate": float((len(F) - n) / len(F)),
            "k_positive": k, "prevalence": (k / n) if n else None,
            "prevalence_ci95": [lo, hi],
            "entropy_bits": entropy_bits([k, n - k]),
            "degenerate": bool(k == 0 or k == n),
            "near_degenerate": bool(min(k, n - k) <= 3),
            "conditional_prevalence": cond,
            "mi_bits_plugin": mi,
            "mi_bits_miller_madow": mi_mm,
            "normalized_mi_over_H_prior": (mi / hy) if hy > 0 else None,
            "H_prior_bits": hy,
            "perm_null_mean_bits": float(null.mean()),
            "perm_null_p95_bits": float(np.percentile(null, 95)),
            "perm_null_p99_bits": float(np.percentile(null, 99)),
            "mi_excess_over_null_mean_bits": float(mi - null.mean()),
            "perm_p": p,
            "cramers_v": cramers_v(x, y),
        })
    qs = bh_fdr([r["perm_p"] for r in stats])
    for r, q in zip(stats, qs):
        r["perm_q_bh"] = float(q)
        r["information_about_prior"] = bool(q < 0.10 and r["mi_excess_over_null_mean_bits"] > 0)
    return stats, perm_store


# ---------------------------------------------------------------- 4. ordinal robustness
def ordinal_variants(F: pd.DataFrame, raw: pd.DataFrame, rng: np.random.Generator) -> list[dict]:
    """이진화가 정보를 버렸을 가능성을 보는 보조 분석. 경계는 사전 확정값(ORDINAL_SPEC)."""
    y_all = F["prior_archetype"].to_numpy()
    pool = F.join(raw.set_index("observation_id")
                  [[c for c in raw.columns if c not in F.columns and raw[c].dtype.kind in "if"]],
                  on="observation_id")
    out = []
    for fid, (col, cuts) in ORDINAL_SPEC.items():
        v = pool[col] if col in pool.columns else None
        if v is None:
            continue
        m = v.notna().to_numpy()
        vv = v[m].astype(float).to_numpy()
        x = np.digitize(vv, cuts[1:], right=False)
        y = y_all[m]
        mi = mi_bits(x, y)
        null = np.empty(N_PERM // 4)
        yp = y.copy()
        for b in range(len(null)):
            rng.shuffle(yp)
            null[b] = mi_bits(x, yp)
        out.append({"feature_id": fid, "ordinal_source": col, "cuts": cuts,
                    "levels": int(len(set(x.tolist()))), "n": int(m.sum()),
                    "mi_bits_plugin": mi, "perm_null_mean_bits": float(null.mean()),
                    "mi_excess_over_null_mean_bits": float(mi - null.mean()),
                    "perm_p": float((1 + int((null >= mi - 1e-12).sum())) / (len(null) + 1)),
                    "n_perm": int(len(null))})
    return out


# ---------------------------------------------------------------- 5. redundancy
def redundancy(F: pd.DataFrame) -> dict:
    fids = [sp["fid"] for sp in FEATURE_SPEC]
    M = F[fids]
    cc = M.dropna()                       # complete cases for the joint matrix
    n_cc = len(cc)
    A = cc.astype(int).to_numpy()
    k = A.shape[1]

    phi = np.eye(k)
    jac = np.eye(k)
    mif = np.zeros((k, k))
    for i in range(k):
        for j in range(k):
            xi, xj = A[:, i], A[:, j]
            if i != j:
                sd = xi.std() * xj.std()
                phi[i, j] = float(np.corrcoef(xi, xj)[0, 1]) if sd > 0 else float("nan")
                inter = int(((xi == 1) & (xj == 1)).sum())
                union = int(((xi == 1) | (xj == 1)).sum())
                jac[i, j] = (inter / union) if union else float("nan")
            mif[i, j] = mi_bits(xi, xj)

    pairs = []
    for i in range(k):
        for j in range(i + 1, k):
            agree = float((A[:, i] == A[:, j]).mean())
            pairs.append({"a": fids[i], "b": fids[j],
                          "phi": None if np.isnan(phi[i, j]) else float(phi[i, j]),
                          "jaccard": None if np.isnan(jac[i, j]) else float(jac[i, j]),
                          "exact_agreement": agree,
                          "mi_bits": float(mif[i, j])})
    pairs.sort(key=lambda d: -(abs(d["phi"]) if d["phi"] is not None else 0))

    # effective dimension from the phi correlation matrix
    P = np.nan_to_num(phi, nan=0.0)
    P = (P + P.T) / 2
    ev = np.linalg.eigvalsh(P)[::-1]
    ev = np.clip(ev, 0, None)
    tot = ev.sum()
    cum = np.cumsum(ev) / tot if tot > 0 else np.zeros_like(ev)
    pr = float((tot ** 2) / float((ev ** 2).sum())) if tot > 0 else float("nan")
    ncomp90 = int(np.searchsorted(cum, 0.90) + 1)
    ncomp_kaiser = int((ev > 1.0).sum())
    # random-matrix reference: same n, same marginals, independent columns
    rng = np.random.default_rng(SEED + 7)
    prs = []
    for _ in range(500):
        R = np.column_stack([rng.permutation(A[:, c]) for c in range(k)])
        Pr = np.nan_to_num(np.corrcoef(R, rowvar=False), nan=0.0)
        e = np.clip(np.linalg.eigvalsh(Pr)[::-1], 0, None)
        t = e.sum()
        prs.append((t ** 2) / float((e ** 2).sum()) if t > 0 else np.nan)
    return {"n_complete_cases": int(n_cc), "features": fids,
            "phi_matrix": [[None if np.isnan(v) else round(float(v), 4) for v in row] for row in phi],
            "jaccard_matrix": [[None if np.isnan(v) else round(float(v), 4) for v in row] for row in jac],
            "feature_feature_mi_bits": [[round(float(v), 4) for v in row] for row in mif],
            "top_pairs_by_abs_phi": pairs[:20],
            "eigenvalues": [round(float(v), 4) for v in ev],
            "cumulative_variance": [round(float(v), 4) for v in cum],
            "participation_ratio": pr,
            "participation_ratio_independent_null_mean": float(np.nanmean(prs)),
            "participation_ratio_independent_null_p05": float(np.nanpercentile(prs, 5)),
            "n_components_90pct_variance": ncomp90,
            "n_components_kaiser_ev_gt_1": ncomp_kaiser,
            "nominal_dimension": k}


# ---------------------------------------------------------------- 6. raw duplicate-vector recheck
def duplicate_recheck(df: pd.DataFrame) -> dict:
    from scipy.stats import pearsonr, spearmanr
    cands = ["n_primary_action_candidates", "n_target_size", "n_accessible_name_sources",
             "n_contrast", "dom_interactive_n", "dom_a_href_n", "dom_button_n", "dom_input_n",
             "modal_overlay_n", "dismiss_control_n", "dom_role_n", "dom_aria_label_n",
             "dom_element_n", "dom_body_element_n", "search_inputs_n", "gate_visible_text_len"]
    cands = [c for c in cands if c in df.columns]
    out = []
    for i in range(len(cands)):
        for j in range(i + 1, len(cands)):
            a, b = cands[i], cands[j]
            sub = df[[a, b]].dropna()
            if len(sub) < 10:
                continue
            xa, xb = sub[a].to_numpy(float), sub[b].to_numpy(float)
            rho = float(spearmanr(xa, xb).statistic)
            r = float(pearsonr(xa, xb).statistic)
            eq = int((xa == xb).sum())
            out.append({"a": a, "b": b, "n": int(len(sub)), "spearman_rho": rho,
                        "pearson_r": r, "n_exact_equal": eq,
                        "exact_equal_rate": eq / len(sub)})
    out.sort(key=lambda d: -abs(d["spearman_rho"]))
    focal = next((d for d in out if {d["a"], d["b"]} ==
                  {"n_primary_action_candidates", "n_target_size"}), None)
    return {"pairs_top30": out[:30],
            "focal_prior_D_observation": {
                "claim": "n_primary_action_candidates 와 n_target_size 는 rho 0.999, 54건 중 30건 값이 정확히 동일",
                "independent_recheck": focal,
                "reproduced": bool(focal and round(focal["spearman_rho"], 3) == 0.999
                                   and focal["n_exact_equal"] == 30 and focal["n"] == 54)},
            "exact_duplicate_columns": [d for d in out if d["exact_equal_rate"] == 1.0]}


# ---------------------------------------------------------------- 7. figures
def figures(stats, perm_store, red, F, dup):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams["font.family"] = ["DejaVu Sans"]
    fids = [r["feature_id"] for r in stats]
    short = [f.split("_", 1)[0] + " " + f.split("_", 1)[1][:22] for f in fids]

    # (1) prevalence overall + by archetype
    fig, ax = plt.subplots(1, 2, figsize=(15, 6.5), gridspec_kw={"width_ratios": [1, 1.5]})
    prev = [r["prevalence"] or 0 for r in stats]
    lo = [p - r["prevalence_ci95"][0] for p, r in zip(prev, stats)]
    hi = [r["prevalence_ci95"][1] - p for p, r in zip(prev, stats)]
    ax[0].barh(range(len(fids)), prev, xerr=[lo, hi], color="#4472C4", ecolor="#888", capsize=2)
    ax[0].set_yticks(range(len(fids)), short, fontsize=7)
    ax[0].invert_yaxis(); ax[0].set_xlim(0, 1); ax[0].grid(alpha=.3, axis="x")
    ax[0].axvline(.05, color="crimson", ls=":", lw=1); ax[0].axvline(.95, color="crimson", ls=":", lw=1)
    ax[0].set_xlabel("prevalence (Wilson 95% CI)")
    ax[0].set_title("Overall prevalence, n=56 (dotted = near-degenerate zone)", fontsize=9)
    M = np.array([[ (r["conditional_prevalence"][a]["prevalence"] or 0) for a in ARCHETYPES]
                  for r in stats])
    im = ax[1].imshow(M, cmap="YlGnBu", vmin=0, vmax=1, aspect="auto")
    ax[1].set_xticks(range(7), [f"{a[:11]}\nn={stats[0]['conditional_prevalence'][a]['n']}"
                               for a in ARCHETYPES], fontsize=7)
    ax[1].set_yticks(range(len(fids)), short, fontsize=7)
    for i in range(len(fids)):
        for j in range(7):
            ax[1].text(j, i, f"{M[i,j]:.2f}", ha="center", va="center", fontsize=6,
                       color="w" if M[i, j] > .6 else "k")
    ax[1].set_title("Conditional prevalence by prior_archetype (exploratory reference only;\n"
                    "prior is a PRIOR, not a gold label; n<=5 classes are not interpretable)", fontsize=8)
    fig.colorbar(im, ax=ax[1], fraction=.03)
    fig.tight_layout(); fig.savefig(FIGDIR / "RF2_B_prevalence.png", dpi=150); plt.close(fig)

    # (2) MI vs permutation null
    fig, ax = plt.subplots(figsize=(13, 7))
    for i, r in enumerate(stats):
        null = perm_store[r["feature_id"]]
        parts = ax.violinplot([null], positions=[i], widths=.8, showextrema=False)
        for b in parts["bodies"]:
            b.set_facecolor("#bbb"); b.set_alpha(.8)
        ax.plot([i], [r["mi_bits_plugin"]], "o",
                color="crimson" if r["perm_q_bh"] < .10 else "#333", ms=7, zorder=5)
        ax.text(i, r["mi_bits_plugin"] + .012, f"p={r['perm_p']:.3f}", ha="center", fontsize=6,
                rotation=90, va="bottom")
    ax.set_xticks(range(len(fids)), short, rotation=60, ha="right", fontsize=7)
    ax.set_ylabel("mutual information with prior_archetype (bits)")
    ax.set_title("Observed MI (dot) vs permutation null (violin, B=%d label shuffles).\n"
                 "Red = BH-FDR q<0.10. Grey mass shows the finite-sample upward bias floor "
                 "at n=56 / 7 classes. This is information ABOUT A PRIOR, not accuracy." % N_PERM,
                 fontsize=9)
    ax.grid(alpha=.3, axis="y"); fig.tight_layout()
    fig.savefig(FIGDIR / "RF2_B_mi_permutation.png", dpi=150); plt.close(fig)

    # (3) redundancy
    fig, ax = plt.subplots(1, 2, figsize=(16, 7), gridspec_kw={"width_ratios": [1.4, 1]})
    P = np.array([[0 if v is None else v for v in row] for row in red["phi_matrix"]])
    im = ax[0].imshow(P, cmap="RdBu_r", vmin=-1, vmax=1)
    ax[0].set_xticks(range(len(fids)), short, rotation=70, ha="right", fontsize=6)
    ax[0].set_yticks(range(len(fids)), short, fontsize=6)
    for i in range(len(fids)):
        for j in range(len(fids)):
            if i != j and abs(P[i, j]) >= .5:
                ax[0].text(j, i, f"{P[i,j]:.2f}", ha="center", va="center", fontsize=5.5)
    ax[0].set_title(f"Feature-feature phi correlation (complete cases n={red['n_complete_cases']})",
                    fontsize=9)
    fig.colorbar(im, ax=ax[0], fraction=.045)
    ev = red["eigenvalues"]; cum = red["cumulative_variance"]
    ax[1].bar(range(1, len(ev) + 1), ev, color="#4472C4", label="eigenvalue")
    ax[1].axhline(1.0, color="crimson", ls="--", lw=1, label="Kaiser (ev=1)")
    a2 = ax[1].twinx(); a2.plot(range(1, len(cum) + 1), cum, "o-", color="#ED7D31", ms=4,
                                label="cumulative variance")
    a2.axhline(.90, color="#ED7D31", ls=":", lw=1)
    ax[1].set_xlabel("component"); ax[1].set_ylabel("eigenvalue"); a2.set_ylabel("cumulative")
    ax[1].set_title("Effective dimension: nominal=%d, PR=%.2f (independent null PR=%.2f),\n"
                    "%d comps for 90%% var, %d with ev>1" %
                    (red["nominal_dimension"], red["participation_ratio"],
                     red["participation_ratio_independent_null_mean"],
                     red["n_components_90pct_variance"], red["n_components_kaiser_ev_gt_1"]),
                    fontsize=9)
    ax[1].legend(loc="upper right", fontsize=7); ax[1].grid(alpha=.3, axis="y")
    fig.tight_layout(); fig.savefig(FIGDIR / "RF2_B_redundancy.png", dpi=150); plt.close(fig)

    # (4) duplicate vector recheck
    fig, ax = plt.subplots(1, 2, figsize=(13, 5.5))
    f = dup["focal_prior_D_observation"]["independent_recheck"]
    d = F.attrs["raw"][["n_primary_action_candidates", "n_target_size"]].dropna()
    eq = d["n_primary_action_candidates"] == d["n_target_size"]
    ax[0].scatter(d.loc[eq, "n_primary_action_candidates"], d.loc[eq, "n_target_size"],
                  c="crimson", s=42, label=f"exactly equal (n={int(eq.sum())})", zorder=4)
    ax[0].scatter(d.loc[~eq, "n_primary_action_candidates"], d.loc[~eq, "n_target_size"],
                  c="#4472C4", s=30, label=f"differ (n={int((~eq).sum())})")
    lim = [0, max(d.max()) * 1.05]
    ax[0].plot(lim, lim, "k--", lw=1, alpha=.6)
    ax[0].set_xlabel("n_primary_action_candidates"); ax[0].set_ylabel("n_target_size")
    ax[0].set_title("Independent recheck: rho=%.4f, %d/%d exactly equal" %
                    (f["spearman_rho"], f["n_exact_equal"], f["n"]), fontsize=9)
    ax[0].legend(fontsize=7); ax[0].grid(alpha=.3)
    tp = dup["pairs_top30"][:14]
    ax[1].barh(range(len(tp)), [t["spearman_rho"] for t in tp], color="#70AD47")
    ax[1].set_yticks(range(len(tp)), [f"{t['a'][:20]} ~ {t['b'][:20]}" for t in tp], fontsize=6)
    ax[1].invert_yaxis(); ax[1].set_xlabel("Spearman rho"); ax[1].grid(alpha=.3, axis="x")
    for i, t in enumerate(tp):
        ax[1].text(t["spearman_rho"], i, f"  eq {t['n_exact_equal']}/{t['n']}", va="center", fontsize=5.5)
    ax[1].set_title("Top raw-column pairs by |rho| (redundancy in the raw measurement layer)", fontsize=9)
    fig.tight_layout(); fig.savefig(FIGDIR / "RF2_B_duplicate_vectors.png", dpi=150); plt.close(fig)


# ---------------------------------------------------------------- main
def main() -> dict:
    FIGDIR.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(SEED)
    df, prov = load()
    F, evid = featurize(df)
    F.attrs["raw"] = df
    stats, perm = feature_stats(F, rng)
    ordv = ordinal_variants(F, df, np.random.default_rng(SEED + 1))
    red = redundancy(F)
    dup = duplicate_recheck(df)
    figures(stats, perm, red, F, dup)

    fids = [r["feature_id"] for r in stats]
    # 보고용 3단계 구분. 이 경계(excess<=0 / q<0.10 / p<0.05)는 표준 관행이며 feature 정의를
    # 바꾸지 않는다. feature 정의와 임계값은 MI 계산 이전에 동결됐다.
    tier_zero = [r["feature_id"] for r in stats
                 if r["mi_excess_over_null_mean_bits"] <= 0]        # null 평균에도 못 미침
    tier_no_fdr = [r["feature_id"] for r in stats if r["perm_q_bh"] >= 0.10]
    tier_marginal = [r["feature_id"] for r in stats
                     if r["perm_p"] < 0.05 and r["perm_q_bh"] >= 0.10]
    degenerate = [r["feature_id"] for r in stats if r["near_degenerate"]]
    no_info = sorted(set(tier_no_fdr) | set(degenerate))
    informative = sorted([r for r in stats if r["information_about_prior"]],
                         key=lambda r: -r["mi_excess_over_null_mean_bits"])
    top_by_excess = sorted(stats, key=lambda r: -r["mi_excess_over_null_mean_bits"])[:5]
    redundant_pairs = [p for p in red["top_pairs_by_abs_phi"]
                       if p["phi"] is not None and abs(p["phi"]) >= 0.60]

    n_informative = len(informative)
    eff_small = red["participation_ratio"] < 0.75 * red["nominal_dimension"]
    if n_informative == 0 and eff_small:
        verdict = "PARTIALLY_SUPPORTED"
        vnote = ("H-B1 지지 + H-B3 지지, H-B2 미지지. 16개 feature 중 BH-FDR(q<0.10) 을 통과해 "
                 "permutation null 을 넘는 feature 는 0개다. 동시에 실효 차원은 명목 차원보다 "
                 "훨씬 작아 feature 들이 서로 같은 것을 재고 있다. 두 가설이 함께 성립하므로 "
                 "단일 SUPPORTED 로 적지 않는다.")
    elif n_informative == 0:
        verdict = "SUPPORTED"
        vnote = "H-B1 지지: permutation null 을 넘는 feature 가 하나도 없다."
    elif n_informative <= 5:
        verdict = "PARTIALLY_SUPPORTED"
        vnote = ("H-B1 과 H-B2 가 동시에 부분 지지된다: 대부분의 feature 는 permutation null 과 "
                 "구분되지 않고, 소수 feature 에만 정보가 몰려 있다.")
    else:
        verdict = "PARTIALLY_SUPPORTED"
        vnote = "H-B2 우세: 다수 feature 가 null 을 넘는다."

    doc = {
        "schema": "RF2_B_feature_discriminability/v1",
        "verdict": verdict,
        "verdict_note": vnote,
        "research_question": "RQ-D-RF-002 / D-RF2-B — 존재하는 feature 와 구별력 있는 feature 를 분리한다",
        "child_id": "D-RF2-B",
        "hypothesis_id": "H-RF2-B-FEATURE-INFORMATION",
        "competing_hypothesis": {
            "H-B1": "대부분 feature 가 정보 없음",
            "H-B2": "소수 feature 에 정보 집중",
            "H-B3": "feature 들이 서로 중복이라 실효 차원이 작다",
        },
        "hypothesis_verdicts": {
            "H-B1": ("SUPPORTED" if n_informative == 0 else
                     "PARTIALLY_SUPPORTED" if n_informative <= 3 else "NOT_SUPPORTED"),
            "H-B2": ("SUPPORTED" if 0 < n_informative <= 5 else
                     "NOT_SUPPORTED" if n_informative == 0 else "PARTIALLY_SUPPORTED"),
            "H-B3": ("SUPPORTED"
                     if red["participation_ratio"] < 0.75 * red["nominal_dimension"]
                     else "NOT_SUPPORTED"),
        },
        "label_semantics": {
            "prior_archetype": "PRIOR, not gold label",
            "usage": "exploratory coloring / reference only",
            "forbidden_term": "accuracy",
            "reported_as": ["prior_agreement", "information_about_prior"],
            "note": "prior 를 정답으로 학습하지 않았다. 어떤 분류기도 적합하지 않았다. "
                    "여기서 계산한 MI 는 feature 가 prior 에 대해 담는 정보량이며, "
                    "feature 가 '옳다'거나 prior 가 '정답'이라는 뜻이 아니다.",
        },
        "provenance": prov,
        "analysis_unit": "target (in_mart == 1)",
        "n": int(len(F)),
        "n_expected": 56,
        "seed": SEED,
        "n_permutations": N_PERM,
        "archetype_counts": {a: int((F["prior_archetype"] == a).sum()) for a in ARCHETYPES},
        "lexicon_full": LEXICON,
        "price_regex": PRICE_REGEX,
        "surface_definitions": {
            "CONTROL_SURFACE": TEXT_CONTROL, "CARD_SURFACE": TEXT_CARD, "CONTEXT_SURFACE": TEXT_CTX,
            "ALL_SURFACE": "CONTROL_SURFACE + CARD_SURFACE + CONTEXT_SURFACE",
            "matching": "lowercase 후 부분 문자열 포함. 형태소 분석 없음.",
        },
        "feature_specs": [{k: sp[k] for k in ("fid", "label", "rule", "cols", "lexicons",
                                              "threshold_basis")} for sp in FEATURE_SPEC],
        "feature_stats": stats,
        "ordinal_variants": ordv,
        "redundancy": red,
        "duplicate_vector_recheck": dup,
        "answers": {
            "features_without_7class_information": no_info,
            "tier_A_zero_information_mi_at_or_below_null_mean": tier_zero,
            "tier_B_no_information_after_bh_fdr_q010": tier_no_fdr,
            "tier_C_marginal_uncorrected_p_lt_005_but_fdr_fails": tier_marginal,
            "degenerate_or_near_degenerate": degenerate,
            "top5_by_mi_excess_over_null": [
                {"feature_id": r["feature_id"], "mi_bits": r["mi_bits_plugin"],
                 "null_mean_bits": r["perm_null_mean_bits"],
                 "excess_bits": r["mi_excess_over_null_mean_bits"],
                 "perm_p": r["perm_p"], "perm_q_bh": r["perm_q_bh"],
                 "normalized_mi": r["normalized_mi_over_H_prior"],
                 "cramers_v": r["cramers_v"]} for r in top_by_excess],
            "informative_features_ranked": [
                {"feature_id": r["feature_id"], "mi_bits": r["mi_bits_plugin"],
                 "null_mean_bits": r["perm_null_mean_bits"],
                 "excess_bits": r["mi_excess_over_null_mean_bits"],
                 "perm_p": r["perm_p"], "perm_q_bh": r["perm_q_bh"],
                 "normalized_mi": r["normalized_mi_over_H_prior"]}
                for r in informative],
            "redundant_pairs_abs_phi_ge_060": redundant_pairs,
            "effective_dimension": {
                "nominal": red["nominal_dimension"],
                "participation_ratio": red["participation_ratio"],
                "independent_null_participation_ratio": red["participation_ratio_independent_null_mean"],
                "n_components_90pct": red["n_components_90pct_variance"],
                "n_components_kaiser": red["n_components_kaiser_ev_gt_1"],
            },
        },
        "per_target_evidence": evid,
        "firewall": {
            "opened_files": [str(OBS), str(TXT)],
            "not_opened": "holdout label, LABEL_SPLIT_FROZEN*, HOLDOUT_FOR_C*, RAW_L1~L4*, "
                          "PACKET_L*, *_OVERLAP*, PRECEDENCE_CONTESTED*, CALIBRATION_FOR_B*, "
                          "**/control/**, B/C target-level holdout error report — 열지 않았다",
            "network": "none", "labels_produced": False, "production_modified": False,
        },
    }
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(doc, ensure_ascii=False, indent=1), encoding="utf-8")
    return doc


def log_mlflow(doc: dict) -> str:
    sys.path.insert(0, str(RD / "tools"))
    import mlflow
    import mlflow_contract as C
    lim = ("n=56, 7 class, 최소 class n=3 (CONTENT_OPEN). MI 는 plug-in 추정이라 상향 편향되며 "
           "permutation null 로 편향 바닥을 제시했으나, class 가 작은 조건부 통계는 여전히 해석 불가. "
           "feature 는 사전 확정 임계값으로 이진화했고 어휘 사전은 형태소 분석 없는 부분 문자열 매칭이라 "
           "과탐이 있다. card_texts 는 25 에서, n_* 지표는 상한에서 절단되어 있다. "
           "prior_archetype 은 gold label 이 아니라 prior 이므로 여기의 어떤 수치도 정확도가 아니다.")
    a = doc["answers"]
    with C.research_run(
            experiment="LA_03_RF_MAPPING", run_name="D-RF2-B feature discriminability",
            plane="D", agent_id="D", subagent_id="worker/D-RF2-B",
            objective="존재하는 feature 와 구별력 있는 feature 를 분리한다",
            method="prevalence·entropy·MI(permutation null)·redundancy·missingness",
            dataset_grain="target (in_mart==1), n=56",
            n_expected=56, n_observed=int(doc["n"]),
            hypothesis_id="H-RF2-B-FEATURE-INFORMATION",
            competing_hypothesis="H-B1 대부분 feature 가 정보 없음 / H-B2 소수 feature 에 정보 집중 / "
                                 "H-B3 feature 들이 서로 중복이라 실효 차원이 작다",
            claim_kind="ANALYSIS", ticket_id="NONE", phase="I1", split="none",
            parent_run_id=PARENT,
            result_path=OUT_JSON,
            model_or_rule_version="RF2B_FEATURES_v1", seed=SEED,
            code_path=Path(__file__),
            notebook="RF2_B_feature_discriminability.ipynb",
            extra_params={"n_features": len(FEATURE_SPEC), "n_permutations": N_PERM,
                          "lexicon_keys": ",".join(LEXICON)},
            extra_tags={"mlflow.parentRunId": PARENT, "rq_id": "RQ-D-RF-002",
                        "child_id": "D-RF2-B"}) as run:
        mlflow.log_metrics({
            "n_targets": float(doc["n"]),
            "n_features": float(len(FEATURE_SPEC)),
            "n_features_informative": float(len(a["informative_features_ranked"])),
            "n_features_no_information": float(len(a["features_without_7class_information"])),
            "n_features_near_degenerate": float(len(a["degenerate_or_near_degenerate"])),
            "n_redundant_pairs_phi_ge_060": float(len(a["redundant_pairs_abs_phi_ge_060"])),
            "effective_dim_participation_ratio": float(a["effective_dimension"]["participation_ratio"]),
            "effective_dim_null_participation_ratio":
                float(a["effective_dimension"]["independent_null_participation_ratio"]),
            "effective_dim_90pct_components": float(a["effective_dimension"]["n_components_90pct"]),
            "H_prior_bits": float(doc["feature_stats"][0]["H_prior_bits"]),
            "max_mi_bits": float(max(r["mi_bits_plugin"] for r in doc["feature_stats"])),
            "max_mi_excess_bits": float(max(r["mi_excess_over_null_mean_bits"]
                                            for r in doc["feature_stats"])),
            "median_perm_null_mean_bits": float(np.median([r["perm_null_mean_bits"]
                                                           for r in doc["feature_stats"]])),
            "min_perm_p": float(min(r["perm_p"] for r in doc["feature_stats"])),
            "focal_dup_spearman_rho": float(
                doc["duplicate_vector_recheck"]["focal_prior_D_observation"]
                ["independent_recheck"]["spearman_rho"]),
            "focal_dup_n_exact_equal": float(
                doc["duplicate_vector_recheck"]["focal_prior_D_observation"]
                ["independent_recheck"]["n_exact_equal"]),
        })
        for r in doc["feature_stats"]:
            f = r["feature_id"]
            mlflow.log_metrics({
                f"prevalence/{f}": float(r["prevalence"]),
                f"entropy_bits/{f}": float(r["entropy_bits"]),
                f"mi_bits/{f}": float(r["mi_bits_plugin"]),
                f"mi_excess_bits/{f}": float(r["mi_excess_over_null_mean_bits"]),
                f"perm_p/{f}": float(r["perm_p"]),
                f"perm_q/{f}": float(r["perm_q_bh"]),
                f"missing_rate/{f}": float(r["missing_rate"]),
            })
        mlflow.log_artifact(str(OUT_JSON), "results")
        for p in sorted(FIGDIR.glob("RF2_B_*.png")):
            mlflow.log_artifact(str(p), "figures")
        mlflow.log_text(json.dumps(LEXICON, ensure_ascii=False, indent=1), "lexicon_full.json")
        mlflow.log_text(json.dumps(doc["feature_specs"], ensure_ascii=False, indent=1),
                        "feature_specs.json")
        rid = run.info.run_id
        C.finish(verdict=doc["verdict"], limitation=lim)
    return rid


if __name__ == "__main__":
    d = main()
    print("verdict:", d["verdict"])
    print("informative:", [x["feature_id"] for x in d["answers"]["informative_features_ranked"]])
    print("no-info    :", d["answers"]["features_without_7class_information"])
    print("eff dim    :", d["answers"]["effective_dimension"])
    if "--no-mlflow" not in sys.argv:
        rid = log_mlflow(d)
        print("mlflow run_id:", rid)
        # run_id 를 결과 JSON 안에 되기록한다 (허용된 산출 파일 목록 밖의 파일을 만들지 않는다).
        d["mlflow_run_id"] = rid
        d["mlflow_parent_run_id"] = PARENT
        OUT_JSON.write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")
