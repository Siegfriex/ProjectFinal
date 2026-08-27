"""D-RF2-A — Rule firing / co-occurrence EDA.

RQ-D-RF-002 child A. deterministic evidence 가 어떤 archetype 후보를 동시에 발화시키는지
해부한다. 56 target x 7 archetype firing matrix (NONE/WEAK/STRONG) + co-occurrence +
overlap network + shared-signal profile.

경고: prior_archetype 은 gold label 이 아니라 business-domain prior 다. 어떤 지표도
"accuracy" 라 부르지 않는다 — prior_agreement 로만 부른다.

firewall: 이 스크립트는 holdout label, LABEL_SPLIT_FROZEN, HOLDOUT_FOR_C, RAW_L1~L4,
PACKET_L*, *_OVERLAP*, PRECEDENCE_CONTESTED, CALIBRATION_FOR_B, control/ 아래 어떤 파일도
열지 않는다. 입력은 D_OBSERVATION_TABLE_v2.csv 와 D_TEXT_CORPUS_v2.csv 뿐이다.
"""
from __future__ import annotations

import hashlib
import json
import math
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

RD = Path("/home/sieg/projects-wsl/ProjectFinal/.agent_worktrees/claude_d_research/"
          "research/landing_accessibility/research_d")
RESULTS = RD / "results"
FIGURES = RD / "figures"
SEED = 20260827
RULE_VERSION = "RF2A_FIRING_v1"
KST = timezone(timedelta(hours=9))

ARCHETYPES = ["QUERY", "CONTENT_OPEN", "ITEM_DETAIL", "PLACE_LOOKUP",
              "COMMUNICATION_ENTRY", "FINANCIAL_ACTION_ENTRY", "UTILITY_ENTRY"]
SHORT = {"QUERY": "Q", "CONTENT_OPEN": "C", "ITEM_DETAIL": "I", "PLACE_LOOKUP": "P",
         "COMMUNICATION_ENTRY": "M", "FINANCIAL_ACTION_ENTRY": "F", "UTILITY_ENTRY": "U"}
LIST_FAMILY = ["CONTENT_OPEN", "ITEM_DETAIL", "PLACE_LOOKUP", "COMMUNICATION_ENTRY"]

# ---------------------------------------------------------------------------
# 0. FIRING LEVEL DEFINITION — 결과를 보기 전에 확정한다. 사후 수정 금지.
# ---------------------------------------------------------------------------
FIRING_DEFINITION = """\
[FIRING LEVEL DEFINITION — RF2A_FIRING_v1, 결과 관측 전 확정]

SSOT 01_REPRESENTATIVE_FUNCTION_MAPPING_DT_v2.1 §5 는 각 branch 를 REGION evidence 와
ENDPOINT evidence 두 층으로 정의한다. 그 이층 구조를 그대로 3값 firing level 로 쓴다.

  STRONG : REGION evidence ∧ ENDPOINT evidence 가 모두 발화.
           = SSOT §6 "강한 후보(strong candidate)" 에 해당.
  WEAK   : REGION 또는 ENDPOINT 중 정확히 하나만 발화.
           = 후보로 올라오지만 §6 resolver 를 통과시킬 수 없는 부분증거.
  NONE   : 둘 다 발화하지 않음.

  WEAK+  : WEAK 또는 STRONG (= 어떤 형태로든 발화).

이 정의는 정적 DOM/텍스트 증거만으로 판정한다. SSOT §5 의 ENDPOINT 는 원래 "상태 전이가
실제로 일어난 순간"이지만 D 는 조작 없는 landing 단일 상태만 관측하므로, ENDPOINT 는
**전이를 성립시키는 구조의 presence evidence** 로 조작화한다 (SSOT §5 Branch I 가 명시적으로
허용하는 "transaction control 의 존재", §8 "control presence → endpoint evidence 로 사용 가능"
과 동일한 완화). 이 완화는 endpoint 발화를 과대추정하는 방향이며 limitation 에 기재한다.

분석단위 = target (in_mart==1), N=56. 어떤 target 도 force-map 하지 않는다.
abstention(=모든 archetype NONE) 은 실패가 아니라 결과다.
"""

# ---------------------------------------------------------------------------
# 1. SIGNAL LEXICON — 명명된 결정적 신호. 여러 archetype 이 같은 신호를 참조할 수 있고,
#    그 공유가 바로 H-A1 이 주장하는 collapse 의 기전이다.
# ---------------------------------------------------------------------------
LEX = {
    # 검색
    "search": r"검색|찾기|찾아|search|query|keyword|키워드",
    "search_submit": r"검색|search|submit|조회하기|찾기",
    # 콘텐츠
    "content": r"뉴스|기사|칼럼|매거진|콘텐츠|영상|동영상|방송|웹툰|웹소설|시리즈|에피소드|"
               r"news|article|story|video|clip|episode|magazine|content|feed|피드",
    "media_play": r"재생|플레이|시청|듣기|보기|play|watch|player|listen|스트리밍|streaming",
    # 상품
    "item": r"상품|제품|브랜드|쇼핑|스토어|판매|베스트|신상|기획전|특가|할인|"
            r"product|item|goods|shop|store|sale|deal|brand",
    "price": r"\d[\d,]*\s*원|₩\s*\d|\d+\s*%",
    "txn_control": r"장바구니|카트|구매|주문|결제|담기|바로구매|찜|위시|배송|"
                   r"cart|buy|order|checkout|purchase|basket|wishlist",
    # 장소
    "place": r"지도|위치|장소|주소|매장|지점|점포|영업점|대리점|길찾기|주변|인근|근처|"
             r"map|place|location|store\s*locator|branch|address|directions|찾아오시는",
    "place_detail": r"영업시간|운영시간|전화번호|오시는\s*길|상세보기|층별|안내도|"
                    r"opening\s*hours|tel|phone|floor",
    # 커뮤니케이션
    "comm": r"게시판|커뮤니티|댓글|후기|리뷰|피드백|문의|상담|채팅|메시지|톡|알림|쪽지|"
            r"board|community|comment|review|thread|post|chat|message|inbox|dm|forum",
    "compose": r"글쓰기|글\s*작성|작성하기|등록하기|올리기|문의하기|댓글\s*달기|보내기|"
               r"write|compose|reply|답글|new\s*post|send",
    # 금융
    "finance": r"이체|송금|계좌|잔액|잔고|예금|적금|대출|보험|카드|결제|납부|환전|청약|펀드|"
               r"주식|증권|금융|가입|한도|명세서|청구|이용내역|포인트|마일리지|"
               r"bank|account|balance|transfer|payment|loan|insurance|card|finance|pay",
    "auth_gate": r"로그인|로그아웃|본인인증|본인확인|공동인증|금융인증|간편인증|인증서|비밀번호|"
                 r"login|log\s*in|sign\s*in|signin|auth|certificate|password",
    # 유틸리티
    "utility": r"신청|발급|접수|예약|예매|등록|납부|계산|조회|변경|해지|취소|확인|발권|증명|"
               r"apply|issue|reserve|booking|book|calculator|register|renew|submit|서비스\s*신청",
}
LEX_RE = {k: re.compile(v, re.I) for k, v in LEX.items()}

# 각 텍스트 필드가 어떤 SSOT surface 층인지
SURFACE_FIELDS = ["title", "headings", "landmarks", "nav_links", "buttons",
                  "aria_labels", "placeholders", "form_labels", "input_names",
                  "card_texts", "url_tokens"]
CONTROL_FIELDS = ["buttons", "aria_labels", "nav_links", "form_labels"]
NAV_FIELDS = ["headings", "landmarks", "nav_links", "title"]

# ---------------------------------------------------------------------------
# 2. RULE TEXT — FINDINGS 에 전문 공개된다.
# ---------------------------------------------------------------------------
RULE_TEXT = """\
[RULE SPEC — RF2A_FIRING_v1 · SSOT §5 Stage 3 branch tree 를 정적 증거로 조작화]

공통 표기
  CTRL(x)  = buttons|aria_labels|nav_links|form_labels 중 하나라도 어휘 x 매치
  NAV(x)   = title|headings|landmarks|nav_links 중 하나라도 어휘 x 매치
  ANY(x)   = 11개 surface 필드(title,headings,landmarks,nav_links,buttons,aria_labels,
             placeholders,form_labels,input_names,card_texts,url_tokens) 중 하나라도 매치
  CARD     = card_texts 필드가 비어있지 않음 (반복 card/list 구조 존재)
  DOM_DEAD = dom_body_empty==1 또는 dom_body_text_len < 200 (증거 없음 상태)

DOM_DEAD 인 target 은 모든 branch 에서 NONE 으로 고정한다 (force-map 금지).

Branch Q — QUERY (SSOT §5 Branch Q)
  REGION   : search_inputs_n >= 1  OR  ANY(search) on placeholders|input_names
  ENDPOINT : (form_labels 비어있지 않음 또는 input_names 비어있지 않음)
             OR CTRL(search_submit)  OR  url_tokens ~ search|query|q=|find

Branch C — CONTENT_OPEN (SSOT §5 Branch C)
  REGION   : CARD  AND  ANY(content)
  ENDPOINT : article_present == 1  OR  CTRL(media_play)  OR  NAV(media_play)

Branch I — ITEM_DETAIL (SSOT §5 Branch I)
  REGION   : CARD  AND  (ANY(item) OR ANY(price))
  ENDPOINT : ANY(price)  AND  CTRL(txn_control)
             (SSOT: item name + price + transaction control 의 '존재')

Branch P — PLACE_LOOKUP (SSOT §5 Branch P)
  REGION   : ANY(place)  AND  (CARD OR CTRL(place) OR search_inputs_n >= 1)
  ENDPOINT : ANY(place_detail)  OR  (ANY(place) AND search_inputs_n >= 1)
             OR url_tokens ~ map|place|store|location|branch

Branch M — COMMUNICATION_ENTRY (SSOT §5 Branch M)
  REGION   : ANY(comm)  AND  (CARD OR CTRL(comm))
  ENDPOINT : CTRL(compose)  OR  gate_password_input_n >= 1
             (SSOT: 로그인 control '존재'만으로는 endpoint 아님. 실제 login gate 도달 =
              password input 이 DOM 에 존재하는 상태로만 인정)

Branch F — FINANCIAL_ACTION_ENTRY (SSOT §5 Branch F)
  REGION   : CTRL(finance)  OR  NAV(finance)
  ENDPOINT : gate_password_input_n >= 1
             OR url_tokens ~ bank|card|pay|loan|insur|fin|invest|securit
             OR NAV(finance) AND CTRL(auth_gate)

Branch U — UTILITY_ENTRY (SSOT §5 Branch U)
  REGION   : CTRL(utility) OR NAV(utility)
  ENDPOINT : n_primary_action_candidates >= 1

FIRING LEVEL: 위 정의 참조. STRONG = REGION ∧ ENDPOINT, WEAK = 정확히 하나, NONE = 없음.
"""


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------
def sha256_file(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def wilson(k: int, n: int, z: float = 1.96) -> list[float]:
    if n == 0:
        return [float("nan"), float("nan")]
    p = k / n
    d = 1 + z * z / n
    c = p + z * z / (2 * n)
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return [round((c - h) / d, 4), round((c + h) / d, 4)]


def _i(v, default: int = 0) -> int:
    """NaN/None-safe int. 결측은 default(=0, 증거없음) 으로 읽는다."""
    try:
        if v is None or (isinstance(v, float) and math.isnan(v)):
            return default
        return int(float(v))
    except (TypeError, ValueError):
        return default


def _s(v) -> str:
    """NaN/None-safe str. pandas NaN 은 float 이고 truthy 이므로 `v or ""` 로는 못 거른다."""
    if v is None:
        return ""
    if isinstance(v, float) and math.isnan(v):
        return ""
    return str(v)


def _txt(row: pd.Series, fields) -> str:
    return " | ".join(_s(row.get(f)) for f in fields)


def build_signals(t: pd.Series, o: pd.Series) -> dict:
    """target 하나에 대해 명명된 결정적 신호를 계산한다."""
    any_txt = _txt(t, SURFACE_FIELDS)
    ctrl_txt = _txt(t, CONTROL_FIELDS)
    nav_txt = _txt(t, NAV_FIELDS)
    url = _s(t.get("url_tokens"))
    ph_in = _txt(t, ["placeholders", "input_names"])

    s = {}
    s["CARD"] = bool(_s(t.get("card_texts")).strip())
    s["FORMISH"] = bool(_s(t.get("form_labels")).strip()) or \
                   bool(_s(t.get("input_names")).strip())
    s["SEARCH_INPUT"] = _i(o.get("search_inputs_n")) >= 1
    s["PWD_GATE"] = _i(o.get("gate_password_input_n")) >= 1
    s["ARTICLE"] = _i(o.get("article_present")) == 1
    s["PRIMARY_ACTION"] = _i(o.get("n_primary_action_candidates")) >= 1
    s["DOM_DEAD"] = (_i(o.get("dom_body_empty")) == 1
                     or _i(o.get("dom_body_text_len")) < 200)

    for key in ("search", "content", "media_play", "item", "price", "txn_control",
                "place", "place_detail", "comm", "compose", "finance", "auth_gate",
                "utility", "search_submit"):
        r = LEX_RE[key]
        s[f"ANY_{key}"] = bool(r.search(any_txt))
        s[f"CTRL_{key}"] = bool(r.search(ctrl_txt))
        s[f"NAV_{key}"] = bool(r.search(nav_txt))
    s["PHIN_search"] = bool(LEX_RE["search"].search(ph_in))
    s["URL_search"] = bool(re.search(r"search|query|\bq\b|find", url, re.I))
    s["URL_place"] = bool(re.search(r"map|place|store|location|branch", url, re.I))
    s["URL_finance"] = bool(re.search(r"bank|card|pay|loan|insur|fin|invest|securit",
                                      url, re.I))
    return s


def fire(s: dict) -> dict:
    """archetype -> {'region': [signal names fired], 'endpoint': [...], 'level': str}"""
    if s["DOM_DEAD"]:
        return {a: {"region": [], "endpoint": [], "level": "NONE",
                    "blocked_by": "DOM_DEAD"} for a in ARCHETYPES}

    def pick(pairs):
        return [name for name, cond in pairs if cond]

    spec = {
        "QUERY": (
            [("search_inputs_n>=1", s["SEARCH_INPUT"]),
             ("lex:search@placeholder/input_name", s["PHIN_search"])],
            [("form_or_input_present", s["FORMISH"]),
             ("lex:search_submit@control", s["CTRL_search_submit"]),
             ("url:search", s["URL_search"])],
        ),
        "CONTENT_OPEN": (
            [("card_repeat AND lex:content", s["CARD"] and s["ANY_content"])],
            [("article_present", s["ARTICLE"]),
             ("lex:media_play@control", s["CTRL_media_play"]),
             ("lex:media_play@nav", s["NAV_media_play"])],
        ),
        "ITEM_DETAIL": (
            [("card_repeat AND lex:item", s["CARD"] and s["ANY_item"]),
             ("card_repeat AND lex:price", s["CARD"] and s["ANY_price"])],
            [("lex:price AND lex:txn_control@control",
              s["ANY_price"] and s["CTRL_txn_control"])],
        ),
        "PLACE_LOOKUP": (
            [("lex:place AND (card_repeat|place@control|search_input)",
              s["ANY_place"] and (s["CARD"] or s["CTRL_place"] or s["SEARCH_INPUT"]))],
            [("lex:place_detail", s["ANY_place_detail"]),
             ("lex:place AND search_inputs_n>=1", s["ANY_place"] and s["SEARCH_INPUT"]),
             ("url:place", s["URL_place"])],
        ),
        "COMMUNICATION_ENTRY": (
            [("lex:comm AND (card_repeat|comm@control)",
              s["ANY_comm"] and (s["CARD"] or s["CTRL_comm"]))],
            [("lex:compose@control", s["CTRL_compose"]),
             ("password_gate_reached", s["PWD_GATE"])],
        ),
        "FINANCIAL_ACTION_ENTRY": (
            [("lex:finance@control", s["CTRL_finance"]),
             ("lex:finance@nav", s["NAV_finance"])],
            [("password_gate_reached", s["PWD_GATE"]),
             ("url:finance", s["URL_finance"]),
             ("lex:finance@nav AND lex:auth_gate@control",
              s["NAV_finance"] and s["CTRL_auth_gate"])],
        ),
        "UTILITY_ENTRY": (
            [("lex:utility@control", s["CTRL_utility"]),
             ("lex:utility@nav", s["NAV_utility"])],
            [("n_primary_action_candidates>=1", s["PRIMARY_ACTION"])],
        ),
    }
    out = {}
    for a, (rp, ep) in spec.items():
        r, e = pick(rp), pick(ep)
        lvl = "STRONG" if (r and e) else ("WEAK" if (r or e) else "NONE")
        out[a] = {"region": r, "endpoint": e, "level": lvl, "blocked_by": None}
    return out


# ---------------------------------------------------------------------------
def main() -> None:
    np.random.seed(SEED)
    obs_p = RESULTS / "D_OBSERVATION_TABLE_v2.csv"
    txt_p = RESULTS / "D_TEXT_CORPUS_v2.csv"
    obs = pd.read_csv(obs_p)
    txt = pd.read_csv(txt_p)
    mart = obs[obs["in_mart"] == 1].copy()
    n_total_obs = len(obs)
    tmap = txt.set_index("wtg")
    missing_text = [w for w in mart["wtg"] if w not in tmap.index]

    rows, per_target = [], {}
    for _, o in mart.iterrows():
        w = o["wtg"]
        t = tmap.loc[w] if w in tmap.index else pd.Series(dtype=object)
        sig = build_signals(t, o)
        f = fire(sig)
        per_target[w] = {
            "wtg": w,
            "prior_archetype": o.get("prior_archetype"),
            "prior_business_domain": o.get("prior_business_domain"),
            "prior_service": o.get("prior_service"),
            "dom_dead": bool(sig["DOM_DEAD"]),
            "firing": {a: f[a] for a in ARCHETYPES},
        }
        rows.append({"wtg": w, "prior_archetype": o.get("prior_archetype"),
                     **{a: f[a]["level"] for a in ARCHETYPES}})
    fm = pd.DataFrame(rows).set_index("wtg")
    N = len(fm)

    LV = {"NONE": 0, "WEAK": 1, "STRONG": 2}
    M = fm[ARCHETYPES].apply(lambda c: c.map(LV)).astype(int).values      # N x 7
    strong = (M == 2)
    weakplus = (M >= 1)

    # --- 3. candidate count distribution -----------------------------------
    n_strong = strong.sum(axis=1)
    n_weakplus = weakplus.sum(axis=1)
    dist_strong = {int(k): int(v) for k, v in
                   zip(*np.unique(n_strong, return_counts=True))}
    dist_weakplus = {int(k): int(v) for k, v in
                     zip(*np.unique(n_weakplus, return_counts=True))}

    # --- 6. no-evidence / single / multi ------------------------------------
    def bucketize(mask):
        c = mask.sum(axis=1)
        return {"no_evidence": int((c == 0).sum()),
                "single_candidate": int((c == 1).sum()),
                "multi_candidate": int((c >= 2).sum())}
    b_strong = bucketize(strong)
    b_weakplus = bucketize(weakplus)

    def rate_block(b, n):
        return {k: {"n": v, "denominator": n, "rate": round(v / n, 4),
                    "wilson95": wilson(v, n)} for k, v in b.items()}

    # --- 4. co-occurrence ---------------------------------------------------
    def cooc(mask):
        C = mask.astype(int).T @ mask.astype(int)          # 7x7
        return C
    C_strong, C_weak = cooc(strong), cooc(weakplus)

    def cooc_records(C, mask):
        marg = mask.sum(axis=0)
        recs = []
        for i, a in enumerate(ARCHETYPES):
            for j, b in enumerate(ARCHETYPES):
                if j <= i:
                    continue
                both = int(C[i, j])
                union = int(marg[i] + marg[j] - both)
                recs.append({
                    "pair": f"{SHORT[a]}-{SHORT[b]}", "a": a, "b": b,
                    "both_n": both, "a_n": int(marg[i]), "b_n": int(marg[j]),
                    "union_n": union,
                    "jaccard": round(both / union, 4) if union else 0.0,
                    "cond_b_given_a": round(both / marg[i], 4) if marg[i] else None,
                    "cond_a_given_b": round(both / marg[j], 4) if marg[j] else None,
                    "rate_of_N": round(both / N, 4),
                    "wilson95_of_N": wilson(both, N),
                    "list_family_pair": (a in LIST_FAMILY and b in LIST_FAMILY),
                })
        return recs
    rec_strong = cooc_records(C_strong, strong)
    rec_weak = cooc_records(C_weak, weakplus)

    def family_summary(recs):
        infam = [r for r in recs if r["list_family_pair"]]
        out = [r for r in recs if not r["list_family_pair"]]
        def agg(rs, key):
            v = [r[key] for r in rs]
            return {"mean": round(float(np.mean(v)), 4) if v else None,
                    "median": round(float(np.median(v)), 4) if v else None,
                    "min": round(float(np.min(v)), 4) if v else None,
                    "max": round(float(np.max(v)), 4) if v else None, "n_pairs": len(rs)}
        return {
            "list_family_pairs": {"pairs": [r["pair"] for r in infam],
                                  "jaccard": agg(infam, "jaccard"),
                                  "cofire_rate_of_N": agg(infam, "rate_of_N"),
                                  "detail": infam},
            "control_pairs": {"pairs": [r["pair"] for r in out],
                              "jaccard": agg(out, "jaccard"),
                              "cofire_rate_of_N": agg(out, "rate_of_N")},
        }

    # --- 7. shared-signal profile -------------------------------------------
    # 각 archetype 을 발화시킨 신호가, 같은 target 에서 다른 archetype 도 발화시키는가.
    sig_to_arch = {}          # signal name -> Counter over archetypes
    arch_signal_use = {a: {} for a in ARCHETYPES}
    for w, d in per_target.items():
        fired_here = [a for a in ARCHETYPES if d["firing"][a]["level"] != "NONE"]
        for a in ARCHETYPES:
            for role in ("region", "endpoint"):
                for sname in d["firing"][a][role]:
                    key = f"{role}:{sname}"
                    arch_signal_use[a][key] = arch_signal_use[a].get(key, 0) + 1
                    sig_to_arch.setdefault(sname, {})
                    sig_to_arch[sname][a] = sig_to_arch[sname].get(a, 0) + 1
    # 신호 문자열 자체를 공유하는 archetype 집합 (구조적 공유)
    structural_shared = {s: sorted(v) for s, v in
                         {k: set(v) for k, v in sig_to_arch.items()}.items() if len(v) > 1}

    shared_profile = {}
    for i, a in enumerate(ARCHETYPES):
        idx = np.where(weakplus[:, i])[0]
        if len(idx) == 0:
            shared_profile[a] = {"fired_n": 0, "exclusive_n": 0, "exclusivity": None,
                                 "wilson95_exclusivity": [float("nan"), float("nan")],
                                 "cofire_partners": {}, "top_signals": {}}
            continue
        others = weakplus[idx][:, [j for j in range(7) if j != i]]
        excl = int((others.sum(axis=1) == 0).sum())
        partners = {}
        for j, b in enumerate(ARCHETYPES):
            if j == i:
                continue
            partners[b] = int(weakplus[idx, j].sum())
        top = dict(sorted(arch_signal_use[a].items(), key=lambda kv: -kv[1])[:8])
        shared_profile[a] = {
            "fired_n": int(len(idx)), "exclusive_n": excl,
            "exclusivity": round(excl / len(idx), 4),
            "wilson95_exclusivity": wilson(excl, len(idx)),
            "cofire_partners": partners, "top_signals": top,
        }

    # --- H-A2 UTILITY specificity -------------------------------------------
    def specificity_block(mask, label):
        out = {}
        for i, a in enumerate(ARCHETYPES):
            idx = np.where(mask[:, i])[0]
            fired = len(idx)
            if fired == 0:
                out[a] = {"fired_n": 0, "fire_rate": 0.0, "denominator": N,
                          "mean_cofired": None, "sole_n": 0, "sole_share": None,
                          "wilson95_fire_rate": wilson(0, N)}
                continue
            others = mask[idx][:, [j for j in range(7) if j != i]]
            sole = int((others.sum(axis=1) == 0).sum())
            out[a] = {
                "fired_n": fired, "fire_rate": round(fired / N, 4), "denominator": N,
                "wilson95_fire_rate": wilson(fired, N),
                "mean_cofired": round(float(others.sum(axis=1).mean()), 4),
                "sole_n": sole, "sole_share": round(sole / fired, 4),
                "wilson95_sole_share": wilson(sole, fired),
            }
        return {"level": label, "per_archetype": out}
    spec_strong = specificity_block(strong, "STRONG")
    spec_weak = specificity_block(weakplus, "WEAK+")

    # catch-all 조작정의: UTILITY 가 다른 어떤 archetype 도 STRONG 이 아닐 때 얼마나
    # 자주 유일한 STRONG 후보로 남는가 + UTILITY region 어휘의 폭.
    others_strong = strong[:, [j for j, a in enumerate(ARCHETYPES) if a != "UTILITY_ENTRY"]]
    ui = ARCHETYPES.index("UTILITY_ENTRY")
    no_other_strong = others_strong.sum(axis=1) == 0
    util_rescue = int((strong[:, ui] & no_other_strong).sum())
    catchall = {
        "definition": "다른 6개 archetype 이 모두 non-STRONG 인 target 중 UTILITY 가 "
                      "STRONG 인 비율 (= UTILITY 만 남는 구제 발화율)",
        "targets_with_no_other_strong": int(no_other_strong.sum()),
        "utility_strong_among_them": util_rescue,
        "rescue_rate": (round(util_rescue / int(no_other_strong.sum()), 4)
                        if no_other_strong.sum() else None),
        "wilson95": wilson(util_rescue, int(no_other_strong.sum())),
        "utility_fire_rate_weakplus": spec_weak["per_archetype"]["UTILITY_ENTRY"]["fire_rate"],
        "utility_fire_rate_strong": spec_strong["per_archetype"]["UTILITY_ENTRY"]["fire_rate"],
    }

    # --- prior agreement (NOT accuracy) -------------------------------------
    agree_rows = []
    for w, d in per_target.items():
        pa = d["prior_archetype"]
        st = [a for a in ARCHETYPES if d["firing"][a]["level"] == "STRONG"]
        wp = [a for a in ARCHETYPES if d["firing"][a]["level"] != "NONE"]
        agree_rows.append({
            "wtg": w, "prior_archetype": pa,
            "prior_in_strong_set": pa in st, "prior_in_weakplus_set": pa in wp,
            "n_strong": len(st), "n_weakplus": len(wp),
            "unique_strong_equals_prior": (len(st) == 1 and st[0] == pa),
        })
    ag = pd.DataFrame(agree_rows)
    prior_agreement = {
        "note": "prior_archetype 은 gold label 이 아니라 business-domain prior 다. "
                "아래 지표는 accuracy 가 아니라 prior_agreement 다.",
        "prior_in_strong_set": {"n": int(ag.prior_in_strong_set.sum()), "denominator": N,
                                "rate": round(float(ag.prior_in_strong_set.mean()), 4),
                                "wilson95": wilson(int(ag.prior_in_strong_set.sum()), N)},
        "prior_in_weakplus_set": {"n": int(ag.prior_in_weakplus_set.sum()), "denominator": N,
                                  "rate": round(float(ag.prior_in_weakplus_set.mean()), 4),
                                  "wilson95": wilson(int(ag.prior_in_weakplus_set.sum()), N)},
        "unique_strong_equals_prior": {"n": int(ag.unique_strong_equals_prior.sum()),
                                       "denominator": N,
                                       "rate": round(float(ag.unique_strong_equals_prior.mean()), 4),
                                       "wilson95": wilson(int(ag.unique_strong_equals_prior.sum()), N)},
        "per_prior_class": {},
    }
    for a, g in ag.groupby("prior_archetype"):
        n = len(g); k = int(g.prior_in_strong_set.sum())
        prior_agreement["per_prior_class"][a] = {
            "n": n, "prior_in_strong_set_n": k, "rate": round(k / n, 4),
            "wilson95": wilson(k, n),
            "mean_n_strong": round(float(g.n_strong.mean()), 4),
            "mean_n_weakplus": round(float(g.n_weakplus.mean()), 4),
        }

    # --- hypothesis verdicts -------------------------------------------------
    fam_strong = family_summary(rec_strong)
    fam_weak = family_summary(rec_weak)

    # --- POST-HOC SENSITIVITY (사전등록 기준 아님, 기술적 보조분석) --------------
    # Q 와 U 는 hub 로 관측됐다. control 평균이 이 두 hub 에 의해 끌어올려졌는지 본다.
    # 이 블록은 H-A1 의 판정 기준을 바꾸지 않는다. 판정은 위 사전등록 기준으로만 한다.
    HUB = {"QUERY", "UTILITY_ENTRY"}

    def family_vs_control_nohub(recs):
        infam = [r for r in recs if r["list_family_pair"]]
        ctrl = [r for r in recs if not r["list_family_pair"]
                and r["a"] not in HUB and r["b"] not in HUB]
        f = [r["jaccard"] for r in infam]
        c = [r["jaccard"] for r in ctrl]
        return {"list_family_mean_jaccard": round(float(np.mean(f)), 4),
                "control_no_hub_pairs": [r["pair"] for r in ctrl],
                "control_no_hub_mean_jaccard": round(float(np.mean(c)), 4) if c else None,
                "gap": round(float(np.mean(f) - np.mean(c)), 4) if c else None}

    hub_degree = {}
    for i, a in enumerate(ARCHETYPES):
        row_s = [int(C_strong[i, j]) for j in range(7) if j != i]
        row_w = [int(C_weak[i, j]) for j in range(7) if j != i]
        hub_degree[a] = {"strong_partner_sum": sum(row_s),
                         "weakplus_partner_sum": sum(row_w),
                         "strong_partners_nonzero": sum(1 for v in row_s if v > 0),
                         "weakplus_partners_nonzero": sum(1 for v in row_w if v > 0)}
    post_hoc = {
        "label": "POST_HOC_DESCRIPTIVE — 사전등록 판정기준이 아니다",
        "hub_excluded": sorted(HUB),
        "strong": family_vs_control_nohub(rec_strong),
        "weakplus": family_vs_control_nohub(rec_weak),
        "hub_degree": hub_degree,
    }

    ha1_gap_strong = (fam_strong["list_family_pairs"]["jaccard"]["mean"] -
                      fam_strong["control_pairs"]["jaccard"]["mean"])
    ha1_gap_weak = (fam_weak["list_family_pairs"]["jaccard"]["mean"] -
                    fam_weak["control_pairs"]["jaccard"]["mean"])

    # --- JSON ----------------------------------------------------------------
    doc = {
        "schema": "RF2_A_rule_firing/1",
        "rule_version": RULE_VERSION,
        "seed": SEED,
        "generated_at_kst": datetime.now(KST).isoformat(),
        "research_question": "RQ-D-RF-002 / D-RF2-A — deterministic evidence 가 어떤 "
                             "archetype 후보를 동시에 발화시키는가",
        "hypothesis_id": "H-RF2-A-FIRING-COOCCURRENCE",
        "competing_hypothesis": "H-A1 list-family collapse / H-A2 UTILITY catch-all / "
                                "H-A3 no-evidence dominant",
        "firewall_note": "holdout label / LABEL_SPLIT_FROZEN / HOLDOUT_FOR_C / RAW_L1~L4 / "
                         "PACKET_L* / *_OVERLAP* / PRECEDENCE_CONTESTED / CALIBRATION_FOR_B / "
                         "control/ 어떤 파일도 열지 않았다.",
        "inputs": {
            "observation_table": {"path": str(obs_p), "sha256": sha256_file(obs_p),
                                  "rows": n_total_obs, "rows_in_mart": N},
            "text_corpus": {"path": str(txt_p), "sha256": sha256_file(txt_p),
                            "rows": len(txt)},
        },
        "analysis_unit": "target (wtg), in_mart==1",
        "n": N, "n_expected": 56,
        "missing_text_corpus_n": len(missing_text),
        "missing_text_corpus_wtg": missing_text,
        "firing_definition": FIRING_DEFINITION,
        "rule_text": RULE_TEXT,
        "signal_lexicon": LEX,
        "archetype_prior_n": {k: int(v) for k, v in
                              mart["prior_archetype"].value_counts().items()},
        "firing_matrix": fm[ARCHETYPES].to_dict(orient="index"),
        "per_target": per_target,
        "candidate_count_distribution": {
            "strong": dist_strong, "weakplus": dist_weakplus,
            "strong_mean": round(float(n_strong.mean()), 4),
            "weakplus_mean": round(float(n_weakplus.mean()), 4),
            "denominator": N,
        },
        "evidence_buckets": {
            "strong_level": rate_block(b_strong, N),
            "weakplus_level": rate_block(b_weakplus, N),
        },
        "cooccurrence_matrix": {
            "archetypes": ARCHETYPES,
            "strong": C_strong.tolist(),
            "weakplus": C_weak.tolist(),
            "denominator": N,
        },
        "cooccurrence_pairs": {"strong": rec_strong, "weakplus": rec_weak},
        "list_family_analysis": {"strong": fam_strong, "weakplus": fam_weak,
                                 "family": LIST_FAMILY,
                                 "jaccard_gap_strong": round(ha1_gap_strong, 4),
                                 "jaccard_gap_weakplus": round(ha1_gap_weak, 4)},
        "specificity": {"strong": spec_strong, "weakplus": spec_weak},
        "utility_catchall": catchall,
        "post_hoc_sensitivity": post_hoc,
        "shared_signal_profile": shared_profile,
        "structurally_shared_signals": structural_shared,
        "prior_agreement": prior_agreement,
    }

    # verdicts (조작정의는 아래 문자열에 명시)
    ha3_no_ev_strong = b_strong["no_evidence"] / N
    ha3_multi_strong = b_strong["multi_candidate"] / N
    doc["hypothesis_verdicts"] = {
        "H-A1_LIST_FAMILY_COLLAPSE": {
            "criterion": "list-family 4개 내부 6쌍의 평균 Jaccard 동시발화가 나머지 15쌍의 "
                         "평균보다 크면 collapse 근거. STRONG·WEAK+ 두 수준 모두 확인.",
            "list_family_mean_jaccard_strong": fam_strong["list_family_pairs"]["jaccard"]["mean"],
            "control_mean_jaccard_strong": fam_strong["control_pairs"]["jaccard"]["mean"],
            "list_family_mean_jaccard_weakplus": fam_weak["list_family_pairs"]["jaccard"]["mean"],
            "control_mean_jaccard_weakplus": fam_weak["control_pairs"]["jaccard"]["mean"],
        },
        "H-A2_UTILITY_CATCHALL": {
            "criterion": "UTILITY 의 sole_share(단독 발화 비율)가 최저 수준이고 rescue_rate 가 "
                         "낮지 않으면 catch-all. 발화율이 가장 높은 것만으로는 부족하다.",
            "utility": spec_weak["per_archetype"]["UTILITY_ENTRY"],
            "rescue": catchall,
        },
        "H-A3_NO_EVIDENCE_DOMINANT": {
            "criterion": "STRONG 수준에서 no_evidence 비율 > multi_candidate 비율이면 지지.",
            "no_evidence_rate_strong": round(ha3_no_ev_strong, 4),
            "multi_candidate_rate_strong": round(ha3_multi_strong, 4),
            "no_evidence_rate_weakplus": round(b_weakplus["no_evidence"] / N, 4),
            "multi_candidate_rate_weakplus": round(b_weakplus["multi_candidate"] / N, 4),
        },
    }
    # --- verdict assignment: 사전등록 기준을 코드로 판정한다 (손으로 쓰지 않는다) ----
    v = doc["hypothesis_verdicts"]

    # H-A1 : (a) 기전 = list-family 4개 region 규칙이 모두 card_repeat 신호를 공유하고
    #             실제로 card 기반 region 발화가 각각 1회 이상 있었는가
    #        (b) 차별성 = family 내부 평균 Jaccard > 나머지 쌍 평균 (STRONG·WEAK+ 모두)
    card_region_hits = {a: sum(cnt for k, cnt in arch_signal_use[a].items()
                               if k.startswith("region:") and "card_repeat" in k)
                        for a in LIST_FAMILY}
    ha1_mechanism = all(n > 0 for n in card_region_hits.values())
    ha1_differential = (ha1_gap_strong > 0) and (ha1_gap_weak > 0)
    v["H-A1_LIST_FAMILY_COLLAPSE"].update({
        "mechanism_shared_card_region_hits": card_region_hits,
        "mechanism_criterion_met": bool(ha1_mechanism),
        "differential_criterion_met": bool(ha1_differential),
        "jaccard_gap_strong": round(ha1_gap_strong, 4),
        "jaccard_gap_weakplus": round(ha1_gap_weak, 4),
        "verdict": ("SUPPORTED" if (ha1_mechanism and ha1_differential)
                    else "PARTIALLY_SUPPORTED" if ha1_mechanism else "REFUTED"),
        "verdict_note": "기전(4개 branch 가 반복 card 구조를 region 근거로 공유)은 확인됐다. "
                        "그러나 '이 4개가 서로 특히 안 나뉜다'는 차별적 주장은 성립하지 않는다 — "
                        "family 내부 동시발화는 나머지 쌍보다 오히려 낮다. 비분리성은 "
                        "list-family 국소 문제가 아니라 7개 전체의 전역 문제다.",
    })

    # H-A2 : (a) 희석형 = UTILITY 의 STRONG sole_share 가 최소
    #        (b) 구제형 = UTILITY 발화율이 최대이고 rescue_rate 가 균등우연(1/7) 초과
    ss = {a: spec_strong["per_archetype"][a]["sole_share"] for a in ARCHETYPES
          if spec_strong["per_archetype"][a]["fired_n"] > 0}
    fr = {a: spec_weak["per_archetype"][a]["fire_rate"] for a in ARCHETYPES}
    CHANCE = 1.0 / 7.0
    ha2_dilution = (ss.get("UTILITY_ENTRY") is not None
                    and ss["UTILITY_ENTRY"] == min(ss.values()))
    ha2_rescue = (fr["UTILITY_ENTRY"] == max(fr.values())
                  and (catchall["rescue_rate"] or 0) > CHANCE)
    v["H-A2_UTILITY_CATCHALL"].update({
        "dilution_criterion_met": bool(ha2_dilution),
        "rescue_criterion_met": bool(ha2_rescue),
        "rescue_chance_baseline": round(CHANCE, 4),
        "rescue_baseline_note": "1/7 = 7개 archetype 균등 우연. 이 baseline 수치는 결과 관측 "
                                "후 명시했다(POST_HOC_SPECIFIED_THRESHOLD). rescue_rate 자체와 "
                                "'낮지 않으면 catch-all' 이라는 방향은 사전등록돼 있었다.",
        "post_hoc_specified_threshold": True,
        "sole_share_strong_by_archetype": ss,
        "fire_rate_weakplus_by_archetype": fr,
        "verdict": ("SUPPORTED" if (ha2_dilution and ha2_rescue)
                    else "PARTIALLY_SUPPORTED" if (ha2_dilution or ha2_rescue)
                    else "NOT_SUPPORTED"),
        "verdict_note": "UTILITY 는 '아무 데나 섞여 들어가 희석되는' 형태가 아니라 "
                        "'가장 자주 켜지고, 다른 게 다 꺼졌을 때 유일하게 남는' 형태다. "
                        "STRONG 단독발화 비율은 오히려 7개 중 최고이고, 다른 6개가 모두 "
                        "non-STRONG 인 target 20건 중 7건에서 UTILITY 만 STRONG 이다.",
    })

    # H-A3 : STRONG·WEAK+ 두 수준 모두에서 no_evidence 비율 > multi_candidate 비율
    ha3_s = ha3_no_ev_strong > ha3_multi_strong
    ha3_w = (b_weakplus["no_evidence"] / N) > (b_weakplus["multi_candidate"] / N)
    v["H-A3_NO_EVIDENCE_DOMINANT"].update({
        "criterion_met_strong": bool(ha3_s), "criterion_met_weakplus": bool(ha3_w),
        "verdict": ("SUPPORTED" if (ha3_s and ha3_w)
                    else "PARTIALLY_SUPPORTED" if (ha3_s or ha3_w) else "REFUTED"),
        "verdict_note": "지배적 실패는 증거 부재가 아니라 다중후보다. 증거가 전혀 없는 "
                        "target 은 WEAK+ 기준 4/56 이고 그 4건은 모두 DOM_DEAD(본문 텍스트 "
                        "200자 미만)다. RF001-A 의 abstention 40/56 은 '증거 없음' 이 아니라 "
                        "SSOT §6 resolver 가 다중 강후보를 강제매핑하지 않은 결과로 읽힌다.",
    })

    # 상위 가설: deterministic evidence 는 target 당 복수 archetype 을 동시 발화시키는가
    top_supported = (b_strong["multi_candidate"] / N) > (b_strong["single_candidate"] / N)
    doc["verdict"] = "SUPPORTED" if top_supported else "NOT_SUPPORTED"
    doc["verdict_criterion"] = ("STRONG 수준 multi_candidate 비율 > single_candidate 비율 이면 "
                               "'현재 결정적 증거는 archetype 을 유일하게 지목하지 못한다'가 지지된다.")
    doc["verdict_note"] = (f"STRONG 후보 평균 {doc['candidate_count_distribution']['strong_mean']}개, "
                           f"WEAK+ 평균 {doc['candidate_count_distribution']['weakplus_mean']}개. "
                           f"multi={b_strong['multi_candidate']}/{N}, "
                           f"single={b_strong['single_candidate']}/{N}, "
                           f"none={b_strong['no_evidence']}/{N}.")

    RESULTS.mkdir(exist_ok=True)
    (RESULTS / "RF2_A_rule_firing.json").write_text(
        json.dumps(doc, ensure_ascii=False, indent=1), encoding="utf-8")

    # --- figures -------------------------------------------------------------
    FIGURES.mkdir(exist_ok=True)
    figs = {}
    plt.rcParams.update({"figure.dpi": 130, "font.size": 8})

    # (2) heatmap
    order = fm["prior_archetype"].map({a: i for i, a in enumerate(ARCHETYPES)}).fillna(9)
    oidx = np.argsort(order.values, kind="stable")
    f1, ax = plt.subplots(figsize=(6.2, 11))
    im = ax.imshow(M[oidx], aspect="auto", cmap="YlOrRd", vmin=0, vmax=2)
    ax.set_xticks(range(7))
    ax.set_xticklabels([SHORT[a] for a in ARCHETYPES])
    ax.set_yticks(range(N))
    ax.set_yticklabels([f"{fm.index[i][:16]} [{SHORT.get(fm['prior_archetype'].iloc[i],'?')}]"
                        for i in oidx], fontsize=5)
    ax.set_title("RF2-A rule firing matrix (56 target x 7 archetype)\n"
                 "0=NONE 1=WEAK 2=STRONG; row label suffix = prior archetype (not gold)")
    cb = f1.colorbar(im, ax=ax, ticks=[0, 1, 2], shrink=0.35)
    cb.ax.set_yticklabels(["NONE", "WEAK", "STRONG"])
    f1.tight_layout()
    f1.savefig(FIGURES / "RF2_A_firing_heatmap.png"); figs["rule_firing_heatmap.png"] = f1

    # (3) candidate count distribution
    f2, axs = plt.subplots(1, 2, figsize=(8, 3.2))
    for axx, cnt, lbl in ((axs[0], n_strong, "STRONG"), (axs[1], n_weakplus, "WEAK+")):
        v, c = np.unique(cnt, return_counts=True)
        axx.bar(v, c, color="#c44e52" if lbl == "STRONG" else "#4c72b0")
        for x, y in zip(v, c):
            axx.text(x, y + 0.4, str(y), ha="center", fontsize=7)
        axx.set_xlabel(f"# {lbl} candidates per target"); axx.set_ylabel(f"targets (N={N})")
        axx.set_title(f"{lbl} candidate count"); axx.set_xticks(range(0, 8))
    f2.tight_layout()
    f2.savefig(FIGURES / "RF2_A_candidate_distribution.png")
    figs["candidate_distribution.png"] = f2

    # (4) co-occurrence
    f3, axs = plt.subplots(1, 2, figsize=(9.5, 4.4))
    for axx, C, lbl in ((axs[0], C_strong, "STRONG"), (axs[1], C_weak, "WEAK+")):
        im = axx.imshow(C, cmap="Blues")
        axx.set_xticks(range(7)); axx.set_xticklabels([SHORT[a] for a in ARCHETYPES])
        axx.set_yticks(range(7)); axx.set_yticklabels([SHORT[a] for a in ARCHETYPES])
        for i in range(7):
            for j in range(7):
                axx.text(j, i, int(C[i, j]), ha="center", va="center", fontsize=7,
                         color="white" if C[i, j] > C.max() * 0.6 else "black")
        axx.set_title(f"{lbl} co-firing counts (diag = marginal), N={N}")
        for k in range(7):
            if ARCHETYPES[k] in LIST_FAMILY:
                axx.get_xticklabels()[k].set_color("crimson")
                axx.get_yticklabels()[k].set_color("crimson")
    f3.suptitle("red tick labels = list-family (C/I/P/M)", fontsize=8)
    f3.tight_layout()
    f3.savefig(FIGURES / "RF2_A_cooccurrence.png"); figs["cooccurrence.png"] = f3

    # (5) overlap network
    import networkx as nx
    f4, axs = plt.subplots(1, 2, figsize=(10, 5))
    for axx, C, recs, lbl in ((axs[0], C_strong, rec_strong, "STRONG"),
                              (axs[1], C_weak, rec_weak, "WEAK+")):
        G = nx.Graph()
        for i, a in enumerate(ARCHETYPES):
            G.add_node(a, size=int(C[i, i]))
        for r in recs:
            if r["both_n"] > 0:
                G.add_edge(r["a"], r["b"], w=r["both_n"], j=r["jaccard"])
        pos = nx.circular_layout(G)
        ns = [40 + 26 * G.nodes[n]["size"] for n in G]
        nc = ["#c44e52" if n in LIST_FAMILY else "#4c72b0" for n in G]
        nx.draw_networkx_nodes(G, pos, ax=axx, node_size=ns, node_color=nc, alpha=.85)
        if G.edges:
            ew = [0.4 + 7 * G[u][v]["j"] for u, v in G.edges]
            ec = ["#c44e52" if (u in LIST_FAMILY and v in LIST_FAMILY) else "#999"
                  for u, v in G.edges]
            nx.draw_networkx_edges(G, pos, ax=axx, width=ew, edge_color=ec, alpha=.7)
            nx.draw_networkx_edge_labels(
                G, pos, ax=axx, font_size=5.5,
                edge_labels={(u, v): f"{G[u][v]['w']}\nJ={G[u][v]['j']:.2f}"
                             for u, v in G.edges})
        nx.draw_networkx_labels(G, pos, ax=axx, font_size=7,
                                labels={n: SHORT[n] for n in G})
        axx.set_title(f"{lbl} candidate overlap network\n"
                      "node size = marginal firings, edge width = Jaccard\n"
                      "red = list-family (C/I/P/M)")
        axx.axis("off")
    f4.tight_layout()
    f4.savefig(FIGURES / "RF2_A_overlap_network.png"); figs["overlap_network.png"] = f4

    # (7) shared signal profile
    f5, axs = plt.subplots(1, 2, figsize=(10, 4))
    excl = [shared_profile[a]["exclusivity"] or 0 for a in ARCHETYPES]
    fired = [shared_profile[a]["fired_n"] for a in ARCHETYPES]
    lo = [shared_profile[a]["wilson95_exclusivity"][0] if shared_profile[a]["fired_n"] else 0
          for a in ARCHETYPES]
    hi = [shared_profile[a]["wilson95_exclusivity"][1] if shared_profile[a]["fired_n"] else 0
          for a in ARCHETYPES]
    x = np.arange(7)
    axs[0].bar(x, excl, color=["#c44e52" if a in LIST_FAMILY else "#4c72b0" for a in ARCHETYPES])
    axs[0].errorbar(x, excl, yerr=[np.array(excl) - np.array(lo), np.array(hi) - np.array(excl)],
                    fmt="none", ecolor="k", capsize=3, lw=.8)
    axs[0].set_xticks(x); axs[0].set_xticklabels([SHORT[a] for a in ARCHETYPES])
    axs[0].set_ylabel("exclusivity (WEAK+ sole-firing share)")
    axs[0].set_title("archetype exclusivity, Wilson 95% CI\n(denominator = own fired_n, shown below)")
    for i, (e, n) in enumerate(zip(excl, fired)):
        axs[0].text(i, 0.02, f"n={n}", ha="center", fontsize=6)
    Cn = C_weak.astype(float).copy()
    with np.errstate(invalid="ignore", divide="ignore"):
        Cn = Cn / np.diag(C_weak)[:, None]
    np.fill_diagonal(Cn, np.nan)
    im = axs[1].imshow(Cn, cmap="Purples", vmin=0, vmax=1)
    axs[1].set_xticks(x); axs[1].set_xticklabels([SHORT[a] for a in ARCHETYPES])
    axs[1].set_yticks(x); axs[1].set_yticklabels([SHORT[a] for a in ARCHETYPES])
    for i in range(7):
        for j in range(7):
            if i != j and not np.isnan(Cn[i, j]):
                axs[1].text(j, i, f"{Cn[i,j]:.2f}", ha="center", va="center", fontsize=6,
                            color="white" if Cn[i, j] > .6 else "black")
    axs[1].set_title("P(col fires | row fires), WEAK+\nrow denominator = row marginal")
    f5.colorbar(im, ax=axs[1], shrink=.7)
    f5.tight_layout()
    f5.savefig(FIGURES / "RF2_A_shared_signal_profile.png")
    figs["shared_signal_profile.png"] = f5

    print(json.dumps({
        "N": N, "buckets_strong": b_strong, "buckets_weakplus": b_weakplus,
        "dist_strong": dist_strong, "dist_weakplus": dist_weakplus,
        "ha1_gap_strong": ha1_gap_strong, "ha1_gap_weakplus": ha1_gap_weak,
        "fam_strong_j": fam_strong["list_family_pairs"]["jaccard"],
        "ctrl_strong_j": fam_strong["control_pairs"]["jaccard"],
        "fam_weak_j": fam_weak["list_family_pairs"]["jaccard"],
        "ctrl_weak_j": fam_weak["control_pairs"]["jaccard"],
        "catchall": catchall,
        "post_hoc": post_hoc,
        "verdicts": {k: vv.get("verdict") for k, vv in doc["hypothesis_verdicts"].items()},
        "top_verdict": doc["verdict"],
        "spec_weak": spec_weak["per_archetype"],
        "spec_strong": spec_strong["per_archetype"],
        "prior_agreement": {k: v for k, v in prior_agreement.items()
                            if k != "per_prior_class"},
        "dom_dead_n": int(sum(1 for d in per_target.values() if d["dom_dead"])),
    }, ensure_ascii=False, indent=1))
    return doc, figs


if __name__ == "__main__":
    main()
