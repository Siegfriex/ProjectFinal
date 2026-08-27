"""D-SUP-01 — RF embedding signal 은 interaction semantics 인가 business/domain semantics 인가.

Director supplemental inquiry. 기존 D autonomous queue 와 별개이며 기존 RQ 의 우선순위·판정·
산출물을 바꾸지 않는다. 기존 D 결과와 충돌하는 부분은 기존 파일을 고치지 않고 이 산출물의
superseding_finding 절에 기록한다.

설계 고정 사항 (실행 전에 확정, 결과를 보고 바꾸지 않는다)
---------------------------------------------------------
* 모델: BAAI/bge-m3 단일. 모델 비교는 이 inquiry 의 주제가 아니다.
* prototype: RF001-C 에서 쓴 frozen 3세트를 그대로 재사용한다. 문구를 재작성하지 않았다.
  (안정성 측정을 위해 최소 2세트 유지 요건 → 3세트 유지)
* representation: FULL / CONTROL_ONLY / TOPIC_ONLY / NO_BRAND_DOMAIN 4종. 정의는 아래 REPS
  와 PREREG 에 전문으로 박아 두었고, 결과를 본 뒤 정의를 수정하지 않는다.
* 판정 우선순위는 top-1 이 아니라 stability(예측 안정성) → top-2 stability → margin →
  class coverage 다. prior_agreement 는 diagnostic 으로만 쓴다. prior_archetype 은
  학습·튜닝에 쓰지 않았다(zero-shot). "accuracy" 라 부르지 않는다.
* 기준선은 stratified. majority 대비 lift 는 rigged 이므로 병기만 한다. permutation null
  (prior 셔플)로 각 representation 의 관측값 위치를 보고한다.

방화벽
------
holdout label · LABEL_SPLIT_FROZEN* · HOLDOUT_FOR_C* · RAW_L1~L4* · PACKET_L* ·
*_OVERLAP* · PRECEDENCE_CONTESTED* · CALIBRATION_FOR_B* · **/control/** · B/C 의
target-level holdout error report 는 **열지 않았다**. 이 스크립트가 읽는 파일은 아래
INPUTS 에 열거된 것이 전부다. gold label 을 만들지 않았고 REAL_TARGET 에 접속하지 않았다.
네트워크 다운로드 없음(HF_HUB_OFFLINE=1, TRANSFORMERS_OFFLINE=1).
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import sys
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlparse

os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")

import numpy as np
import pandas as pd

RD = Path("/home/sieg/projects-wsl/ProjectFinal/.agent_worktrees/claude_d_research/"
          "research/landing_accessibility/research_d")
sys.path.insert(0, str(RD / "tools"))

RESULTS = RD / "results"
FIGDIR = RD / "figures"
OUT = RESULTS / "DSUP01_representation_ablation.json"

SEED = 20260827
N_PERM = 20000
N_STRAT = 20000
N_BOOT = 2000
KST = timezone(timedelta(hours=9))

ARCHETYPES = ["QUERY", "CONTENT_OPEN", "ITEM_DETAIL", "PLACE_LOOKUP",
              "COMMUNICATION_ENTRY", "FINANCIAL_ACTION_ENTRY", "UTILITY_ENTRY"]
A2I = {a: i for i, a in enumerate(ARCHETYPES)}

INPUTS = {
    "corpus": RESULTS / "D_TEXT_CORPUS_v2.csv",
    "observation_table": RESULTS / "D_OBSERVATION_TABLE_v2.csv",
    "strata": RESULTS / "RQ_D14_frame_validity.json",
}

# ------------------------------------------------------------------ prototypes
# RF001-C 에서 동결된 3세트를 문구 그대로 재사용한다. provenance: SSOT 00 §4 archetype 목록 +
# SSOT 01 §5 Stage-3 branch 정의문. D_TEXT_CORPUS 를 읽고 조정한 적 없고, 결과를 본 뒤에도
# 수정하지 않는다.
PROTO_SSOT_DEF = {
    "QUERY":
        "사용자가 검색 입력창에 자유 텍스트 질의를 입력하고 제출하여 검색 결과 목록 상태로 "
        "전환하는 것이 대표행동이다. 검색 입력 control, 검색 form, 검색 제출 버튼이 대표 "
        "표면이다. search box, search form, submit query, search results.",
    "CONTENT_OPEN":
        "이미 존재하는 기사, 영상, 콘텐츠 한 건을 목록에서 선택해 본문을 열거나 재생을 "
        "시작하는 것이 대표행동이다. 콘텐츠 카드 목록, 기사 본문, 미디어 재생이 대표 "
        "표면이다. article body, news, video playback, content card list.",
    "ITEM_DETAIL":
        "거래 대상 상품 한 건의 상세면에 들어가 상품명, 가격, 거래 control 의 존재를 확인하는 "
        "것이 대표행동이다. 반복되는 상품 카드 목록과 상품 상세 문서가 대표 표면이다. "
        "product name, price, cart, order, shopping mall, item detail page.",
    "PLACE_LOOKUP":
        "장소를 질의하거나 특정 장소의 상세면을 여는 것이 대표행동이다. 장소 검색 control, "
        "장소 목록, 지도, 주소, 장소 상세 패널이 대표 표면이다. map, place search, address, "
        "location, route, navigation.",
    "COMMUNICATION_ENTRY":
        "사람 사이의 게시물, 스레드, 메시지를 교환하는 공간에 진입하는 것이 대표행동이다. "
        "스레드 목록, 게시글 목록, 글쓰기 진입 control, 실제 로그인 gate 가 대표 표면이다. "
        "message, chat, post, thread, community, social feed, comment.",
    "FINANCIAL_ACTION_ENTRY":
        "금융처리 기능의 시작면을 열거나 그 기능을 시작하기 위해 필요한 실제 로그인 및 "
        "본인인증 gate 까지 진입하는 것이 대표행동이다. 잔액 조회, 이체, 송금, 결제, 카드, "
        "보험, 인증 기능 진입 control 이 대표 표면이다. bank, transfer, payment, balance, "
        "card, insurance, login, identity verification.",
    "UTILITY_ENTRY":
        "특정 목적의 도구 기능면을 열고 첫 primary control 을 사용할 수 있는 상태로 만드는 "
        "것이 대표행동이다. 단일 목적 기능 진입 control 과 그 기능 화면이 대표 표면이다. "
        "utility tool, service function, apply, reserve, issue, lookup, settings.",
}
PROTO_USER_BEHAVIOR = {
    "QUERY": "나는 궁금한 것을 검색창에 입력하고 검색 버튼을 눌러 결과 목록을 본다.",
    "CONTENT_OPEN": "나는 목록에서 기사나 영상 하나를 골라 눌러서 읽거나 본다.",
    "ITEM_DETAIL": "나는 사고 싶은 물건 하나를 눌러 상세 화면에서 가격과 정보를 확인한다.",
    "PLACE_LOOKUP": "나는 가려는 장소를 찾아보고 그 장소의 위치와 상세 정보를 확인한다.",
    "COMMUNICATION_ENTRY": "나는 다른 사람이 올린 글이나 메시지를 보러 대화 공간에 들어간다.",
    "FINANCIAL_ACTION_ENTRY": "나는 은행이나 카드 업무를 시작하려고 로그인 화면까지 들어간다.",
    "UTILITY_ENTRY": "나는 필요한 기능 하나를 열어서 바로 쓸 수 있는 상태까지 간다.",
}
PROTO_TERSE_LABEL = {
    "QUERY": "검색 질의 search query",
    "CONTENT_OPEN": "콘텐츠 열람 content open article video",
    "ITEM_DETAIL": "상품 상세 item detail product price",
    "PLACE_LOOKUP": "장소 조회 place lookup map location",
    "COMMUNICATION_ENTRY": "커뮤니케이션 진입 communication message post",
    "FINANCIAL_ACTION_ENTRY": "금융 기능 진입 financial action bank payment",
    "UTILITY_ENTRY": "도구 기능 진입 utility function tool",
}
PROTO_SETS = {"A_SSOT_DEF": PROTO_SSOT_DEF,
              "B_USER_BEHAVIOR": PROTO_USER_BEHAVIOR,
              "C_TERSE_LABEL": PROTO_TERSE_LABEL}
PRIMARY_PROTO = "A_SSOT_DEF"
MODEL_HF = "BAAI/bge-m3"   # bge-m3 공식 규약: instruction prefix 를 쓰지 않는다.

# ------------------------------------------------- representation 조작화 정의 (전문)
CTRL_FIELDS = ["buttons", "aria_labels", "placeholders", "form_labels", "input_names"]
TOPIC_FIELDS = ["title", "meta_description", "headings"]
ALL_FIELDS = ["title", "meta_description", "headings", "landmarks", "nav_links",
              "buttons", "aria_labels", "placeholders", "form_labels", "input_names",
              "card_texts", "url_tokens"]

REPS = ["FULL", "CONTROL_ONLY", "TOPIC_ONLY", "NO_BRAND_DOMAIN"]

REP_DEFINITION_TEXT = {
    "FULL": (
        "D_TEXT_CORPUS_v2.text_blob 을 그대로 쓴다. text_blob 은 12개 필드"
        "(title, meta_description, headings, landmarks, nav_links, buttons, aria_labels, "
        "placeholders, form_labels, input_names, card_texts, url_tokens)를 corpus 빌더의 "
        "정본 순서대로 ' \\n ' 로 결합하되 빈 필드는 생략한 문자열이다. 현행 RF NLP fallback "
        "representation 과 동일하다."
    ),
    "CONTROL_ONLY": (
        "상호작용 컨트롤 표면만 남긴다. 필드 = buttons + aria_labels + placeholders + "
        "form_labels + input_names, 정본 결합 규약(' \\n ' join, 빈 필드 생략)과 동일. "
        "buttons = //button | //*[@role='button'] | //input[@type='submit'] 의 텍스트, "
        "aria_labels = //*[@aria-label] 의 aria-label 속성, placeholders = input/textarea 의 "
        "placeholder 속성, form_labels = //label 텍스트, input_names = //input[@name] 의 name "
        "속성. 즉 '이 화면에서 무엇을 조작할 수 있는가' 의 표면이며 업종 서술 텍스트가 아니다. "
        "title/meta/headings/card/nav/landmark/url 은 모두 제외한다."
    ),
    "TOPIC_ONLY": (
        "주제·업종 어휘만 남긴다. 필드 = title + meta_description + headings, 정본 결합 규약 "
        "동일. 컨트롤 텍스트(buttons/aria/placeholder/label/input name)와 카드·내비·랜드마크·"
        "URL 토큰은 모두 제외한다. 즉 '이 사이트가 무엇에 관한 것인가' 의 표면이다."
    ),
    "NO_BRAND_DOMAIN": (
        "FULL 에서 브랜드·도메인 토큰만 제거한 것. 필드 구성은 FULL 과 같고 제거 규칙만 다르다. "
        "제거 대상 토큰 집합(target 별로 따로 만든다) = "
        "(1) prior_service 를 [a-zA-Z0-9가-힣]+ 로 토큰화한 것 중 길이>=2 인 토큰 + 공백 제거 "
        "압축형(예: '신한 SOL뱅크' → 신한/sol/뱅크/신한sol뱅크), "
        "(2) 대상 host 의 라벨 토큰 — host 는 prior_url 의 hostname 이며 RQ-D14 per_target 의 "
        "a_host 와 대조해 확인했다(wtg 자체는 16자리 불투명 id 라 host 문자열을 담고 있지 않다). "
        "host 를 [.-] 로 쪼갠 라벨 중 길이>=2 인 것 전부, "
        "(3) url_tokens 의 도메인 성분 — scheme/host 유래 구문 토큰 "
        "{https, http, www, com, co, kr, net, org} 를 항상 포함, "
        "(4) RQ-D14 per_target 의 a_matched_alias(브랜드 alias)가 있으면 그 토큰. "
        "제거 방식: 라틴 토큰은 앞뒤가 [A-Za-z0-9] 가 아닌 위치에서만 대소문자 무시 치환, "
        "한글 토큰은 어절 경계가 없으므로 단순 부분문자열 치환(대소문자 무시). 치환 결과는 "
        "공백 1칸으로 바꾸고 줄 단위로 공백을 정규화하며, 비게 된 줄은 버린다. "
        "제거된 토큰과 target 별 제거 횟수는 removed_brand_domain_tokens 로 전문 공개한다."
    ),
}

# domain syntax tokens — 항상 제거 대상에 넣는다(3번 규칙).
URL_SYNTAX_TOKENS = ["https", "http", "www", "com", "co", "kr", "net", "org"]

# ------------------------------------------------------------------- 사전 예측
# 결과를 보기 전에 확정한 예측과 판정 규칙. 실행 후 수정하지 않는다.
PREREG = {
    "primary_metric_order": [
        "prediction stability across representations (4-way unanimity, pairwise agreement)",
        "prototype stability (agreement + Cohen kappa)",
        "top-2 set stability",
        "margin (top1-top2 cosine gap) distribution",
        "class coverage (7 archetype 중 실제 예측된 class 수)",
        "prior_agreement / macro F1 은 diagnostic 으로만",
    ],
    "primary_analysis_set": "complete_case (4개 representation 모두 토큰>=2 인 target)",
    "primary_prototype_set": PRIMARY_PROTO,
    "decision_baseline": "stratified (permutation null 병기, majority 는 참고용)",
    "quantities": {
        "d_ctrl_topic": "macro_f1(CONTROL_ONLY) - macro_f1(TOPIC_ONLY), complete_case, proto A",
        "drop_brand": "macro_f1(FULL) - macro_f1(NO_BRAND_DOMAIN), complete_case, proto A",
        "pred_change_brand": "1 - top1_agreement(FULL, NO_BRAND_DOMAIN), complete_case, proto A",
        "agree_ctrl_topic": "top1_agreement(CONTROL_ONLY, TOPIC_ONLY), complete_case, proto A",
    },
    "hypotheses": {
        "H-SUP01-INTERACTION": {
            "statement": "신호는 상호작용 구조(검색 제출·항목 열기·인증 진입·도구 진입)에서 온다.",
            "prediction": ("CONTROL_ONLY 가 TOPIC_ONLY 보다 강하고(d_ctrl_topic > +0.05), "
                           "브랜드·도메인 토큰을 지워도 신호가 유지된다"
                           "(drop_brand < 0.05 이고 pred_change_brand < 0.15)."),
            "rule": ("SUPPORTED = 세 조건 모두. PARTIALLY_SUPPORTED = 방향(d_ctrl_topic>0)이 맞고 "
                     "나머지 중 일부만. REFUTED = d_ctrl_topic < -0.05. 그 외 NOT_SUPPORTED."),
        },
        "H-SUP01-DOMAIN": {
            "statement": ("신호는 업종/브랜드 어휘에서 온다. archetype 과 업종이 상관돼 있어 "
                          "상호작용을 재는 것처럼 보일 뿐이다."),
            "prediction": ("TOPIC_ONLY 가 CONTROL_ONLY 보다 강하고(d_ctrl_topic < -0.05), "
                           "NO_BRAND_DOMAIN 에서 신호가 크게 무너진다"
                           "(drop_brand > 0.10 또는 pred_change_brand > 0.25)."),
            "rule": ("SUPPORTED = 두 limb 모두. PARTIALLY_SUPPORTED = 한 limb 만"
                     "(예: 주제 어휘 우위는 맞지만 브랜드 토큰 의존은 아님). "
                     "REFUTED = d_ctrl_topic > +0.05. 그 외 NOT_SUPPORTED."),
        },
        "H-SUP01-BOTH": {
            "statement": "둘 다 기여하며 분리 가능하다.",
            "prediction": ("CONTROL_ONLY 와 TOPIC_ONLY 가 각각 stratified p95 를 넘고, 두 "
                           "representation 의 top1 일치율이 낮으며(agree_ctrl_topic < 0.60), "
                           "FULL 이 둘 중 최대치 이상이다(>= max - 0.02)."),
            "rule": "SUPPORTED = 세 조건 모두. PARTIALLY_SUPPORTED = 두 개. 그 외 NOT_SUPPORTED.",
        },
        "H-SUP01-INSEPARABLE": {
            "statement": "이 표본에서는 두 원천을 분리할 수 없다.",
            "prediction": ("d_ctrl_topic 의 95% paired bootstrap CI 가 0 을 포함하고 "
                           "drop_brand 의 CI 도 0 을 포함한다. 즉 어느 쪽이 신호원인지 "
                           "표본이 구분하지 못한다."),
            "rule": ("SUPPORTED = 두 CI 모두 0 포함. PARTIALLY_SUPPORTED = 하나만 0 포함. "
                     "그 외 NOT_SUPPORTED."),
        },
    },
    "overall_rule": ("INTERACTION/DOMAIN/BOTH 중 정확히 하나가 SUPPORTED 면 전체 verdict = "
                     "SUPPORTED(신호원 특정). 최상위가 PARTIALLY_SUPPORTED 면 "
                     "PARTIALLY_SUPPORTED. INSEPARABLE 이 SUPPORTED 이거나 어느 것도 "
                     "PARTIALLY 이상에 도달하지 못하면 INCONCLUSIVE."),
    "known_prior_from_RF001_C": ("v1 코퍼스에서 bge-m3 macro F1 0.497 vs stratified 0.139, "
                                 "prototype 문구 민감도 SUPPORTED, UTILITY_ENTRY 0/5. "
                                 "정답으로 쓰지 않고 전부 재계산한다."),
}

TOK = re.compile(r"[a-zA-Z0-9가-힣]+")
HANGUL = re.compile(r"[가-힣]")


# ---------------------------------------------------------------- statistics
def wilson(k: int, n: int, z: float = 1.959963985) -> list[float]:
    if n == 0:
        return [float("nan"), float("nan")]
    p = k / n
    d = 1 + z * z / n
    c = p + z * z / (2 * n)
    h = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return [float((c - h) / d), float((c + h) / d)]


def macro_f1(pred: np.ndarray, true: np.ndarray, k: int = 7) -> float:
    f1s = []
    for c in range(k):
        tp = int(((pred == c) & (true == c)).sum())
        fp = int(((pred == c) & (true != c)).sum())
        fn = int(((pred != c) & (true == c)).sum())
        den = 2 * tp + fp + fn
        f1s.append(0.0 if den == 0 else 2 * tp / den)
    return float(np.mean(f1s))


def macro_f1_batch(pred: np.ndarray, true: np.ndarray, k: int = 7) -> np.ndarray:
    """pred (n,) 고정 · true (m,n) 또는 pred (m,n) · true (n,) 배치 macro F1."""
    if pred.ndim == 1:
        pred = pred[None, :]
    if true.ndim == 1:
        true = true[None, :]
    m = max(pred.shape[0], true.shape[0])
    out = np.zeros((m, k))
    for c in range(k):
        pc = pred == c
        tc = true == c
        tp = (pc & tc).sum(axis=1)
        fp = (pc & ~tc).sum(axis=1)
        fn = (~pc & tc).sum(axis=1)
        den = 2 * tp + fp + fn
        out[:, c] = np.where(den == 0, 0.0, 2 * tp / np.maximum(den, 1))
    return out.mean(axis=1)


def cohen_kappa(a: list[str], b: list[str]) -> float:
    cats = sorted(set(a) | set(b))
    n = len(a)
    if n == 0:
        return float("nan")
    po = sum(1 for x, y in zip(a, b) if x == y) / n
    ca, cb = Counter(a), Counter(b)
    pe = sum((ca[c] / n) * (cb[c] / n) for c in cats)
    if abs(1 - pe) < 1e-12:
        return float("nan")
    return float((po - pe) / (1 - pe))


def mcnemar_exact(a_correct: np.ndarray, b_correct: np.ndarray) -> dict:
    """paired binary 비교의 정확 이항검정 (a 가 맞고 b 가 틀린 쌍 vs 반대)."""
    b01 = int(((a_correct == 1) & (b_correct == 0)).sum())
    b10 = int(((a_correct == 0) & (b_correct == 1)).sum())
    n = b01 + b10
    if n == 0:
        return {"b_a_only": 0, "b_b_only": 0, "n_discordant": 0, "p_two_sided": 1.0}
    from math import comb
    k = min(b01, b10)
    p = sum(comb(n, i) for i in range(0, k + 1)) / (2 ** n) * 2
    return {"b_a_only": b01, "b_b_only": b10, "n_discordant": n,
            "p_two_sided": float(min(1.0, p))}


# --------------------------------------------------------------- text builders
def sha256_file(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def join_fields(row: pd.Series, fields: list[str]) -> str:
    """text_blob 과 동일한 결합 규약(' \\n ' join, 빈 필드 생략)."""
    parts = [str(row[f]).strip() for f in fields if str(row.get(f, "")).strip()]
    return " \n ".join(parts)


def brand_domain_tokens(row: pd.Series, alias: str | None) -> list[str]:
    toks: set[str] = set()
    svc = str(row.get("prior_service", "") or "")
    for t in TOK.findall(svc):
        if len(t) >= 2:
            toks.add(t.lower())
    compact = re.sub(r"\s+", "", svc)
    if len(compact) >= 2:
        toks.add(compact.lower())
    host = (urlparse(str(row.get("prior_url", "") or "")).hostname or "").lower()
    for lab in re.split(r"[.\-]", host):
        if len(lab) >= 2:
            toks.add(lab)
    toks.update(URL_SYNTAX_TOKENS)
    if alias:
        for t in TOK.findall(str(alias)):
            if len(t) >= 2:
                toks.add(t.lower())
    return sorted(toks, key=lambda s: (-len(s), s))


def strip_brand(text: str, toks: list[str]) -> tuple[str, Counter]:
    removed: Counter = Counter()
    out = text
    for t in toks:
        if HANGUL.search(t):
            pat = re.compile(re.escape(t), re.IGNORECASE)
        else:
            pat = re.compile(r"(?<![A-Za-z0-9])" + re.escape(t) + r"(?![A-Za-z0-9])",
                             re.IGNORECASE)
        out, n = pat.subn(" ", out)
        if n:
            removed[t] = n
    lines = []
    for ln in out.split("\n"):
        ln = re.sub(r"[ \t]+", " ", ln).strip()
        if ln:
            lines.append(ln)
    return " \n ".join(lines), removed


# --------------------------------------------------------------------- encode
def encode(texts: list[str]) -> np.ndarray:
    from sentence_transformers import SentenceTransformer
    import torch
    torch.manual_seed(SEED)
    dev = "cuda" if torch.cuda.is_available() else "cpu"
    m = SentenceTransformer(MODEL_HF, device=dev)
    V = m.encode(texts, batch_size=4, normalize_embeddings=True,
                 convert_to_numpy=True, show_progress_bar=False)
    tok_counts = [len(m.tokenizer(t)["input_ids"]) for t in texts]
    max_seq = int(m.max_seq_length)
    del m
    torch.cuda.empty_cache()
    return V, tok_counts, max_seq


# -------------------------------------------------------------------- metrics
def config_metrics(sims: np.ndarray, true_idx: np.ndarray, idx: np.ndarray) -> dict:
    """idx 로 지정한 subset 에 대한 진단 지표."""
    s = sims[idx]
    order = np.argsort(-s, axis=1)
    p1 = order[:, 0]
    marg = s[np.arange(len(idx)), order[:, 0]] - s[np.arange(len(idx)), order[:, 1]]
    t = true_idx[idx]
    top2_hit = np.array([t[i] in order[i, :2] for i in range(len(idx))])
    n = len(idx)
    k = int((p1 == t).sum())
    return {
        "n": n,
        "prior_agreement": float(k / n) if n else float("nan"),
        "prior_agreement_fraction": f"{k}/{n}",
        "prior_agreement_wilson95": wilson(k, n),
        "macro_f1": macro_f1(p1, t),
        "top2_prior_containment": float(top2_hit.mean()) if n else float("nan"),
        "n_distinct_predicted_classes": int(len(set(p1.tolist()))),
        "predicted_class_counts": {ARCHETYPES[c]: int((p1 == c).sum())
                                   for c in range(7) if (p1 == c).sum()},
        "never_predicted_classes": [ARCHETYPES[c] for c in range(7) if not (p1 == c).sum()],
        "margin_median": float(np.median(marg)) if n else float("nan"),
        "margin_p10": float(np.percentile(marg, 10)) if n else float("nan"),
        "margin_p90": float(np.percentile(marg, 90)) if n else float("nan"),
        "margin_mean": float(marg.mean()) if n else float("nan"),
        "top1_sim_median": float(np.median(s[np.arange(len(idx)), order[:, 0]])) if n else float("nan"),
    }


def main() -> int:
    rng = np.random.default_rng(SEED)
    FIGDIR.mkdir(parents=True, exist_ok=True)

    # ---------------------------------------------------------------- inputs
    df = pd.read_csv(INPUTS["corpus"]).fillna("")
    n_rows = len(df)
    d14 = json.loads(INPUTS["strata"].read_text(encoding="utf-8"))
    strata_map = {r["wtg"]: r.get("identity_class") for r in d14["per_target"]}
    alias_map = {r["wtg"]: r.get("a_matched_alias") for r in d14["per_target"]}
    host_map = {r["wtg"]: r.get("a_host") for r in d14["per_target"]}
    df["identity_class"] = df["wtg"].map(strata_map)
    n_missing_stratum = int(df["identity_class"].isna().sum())
    df["identity_class"] = df["identity_class"].fillna("UNMAPPED")

    obs = pd.read_csv(INPUTS["observation_table"]).fillna("")
    obs_join_ok = bool(set(df["wtg"]) <= set(obs["wtg"]))

    true_idx = df["prior_archetype"].map(A2I).to_numpy()

    # ------------------------------------------------- build representations
    texts: dict[str, list[str]] = {}
    texts["FULL"] = [str(t) for t in df["text_blob"]]
    texts["CONTROL_ONLY"] = [join_fields(r, CTRL_FIELDS) for _, r in df.iterrows()]
    texts["TOPIC_ONLY"] = [join_fields(r, TOPIC_FIELDS) for _, r in df.iterrows()]

    nb_texts, removal_audit, all_removed = [], [], Counter()
    host_mismatch = []
    for i, r in df.iterrows():
        toks = brand_domain_tokens(r, alias_map.get(r["wtg"]))
        stripped, removed = strip_brand(texts["FULL"][i], toks)
        nb_texts.append(stripped)
        all_removed.update(removed)
        h_url = (urlparse(str(r["prior_url"])).hostname or "").lower()
        h_d14 = (host_map.get(r["wtg"]) or "").lower()
        if h_d14 and h_url != h_d14:
            host_mismatch.append({"wtg": r["wtg"], "prior_url_host": h_url, "d14_a_host": h_d14})
        removal_audit.append({
            "wtg": r["wtg"], "prior_service": r["prior_service"],
            "host": h_url, "d14_a_host": h_d14, "d14_a_matched_alias": alias_map.get(r["wtg"]),
            "blacklist_tokens": toks,
            "removed_token_counts": dict(sorted(removed.items())),
            "n_removed_occurrences": int(sum(removed.values())),
            "tokens_before": len(TOK.findall(texts["FULL"][i])),
            "tokens_after": len(TOK.findall(stripped)),
        })
    texts["NO_BRAND_DOMAIN"] = nb_texts

    # ---- PLACEBO 제거 대조군 (사전등록 후 추가. 아래 POSTHOC_ADDITIONS 에 사유를 밝힌다)
    # NO_BRAND_DOMAIN 의 예측 변화율은 '브랜드 토큰이 특별한가' 를 혼자서는 말해주지 못한다.
    # 같은 개수의 임의 비브랜드 토큰을 지웠을 때의 변화율과 비교해야 해석된다.
    def placebo_strip(text: str, blacklist: list[str], n_remove: int, r) -> str:
        spans = [m.span() for m in TOK.finditer(text)]
        toks = [text[a:b].lower() for a, b in spans]
        bl = set(blacklist)
        bl_hangul = [t for t in bl if HANGUL.search(t)]
        elig = [i for i, t in enumerate(toks)
                if t not in bl and not any(h in t for h in bl_hangul)]
        k = min(int(n_remove), len(elig))
        chosen = set(r.choice(elig, size=k, replace=False).tolist()) if k else set()
        out, last = [], 0
        for i, (a, b) in enumerate(spans):
            if i in chosen:
                out.append(text[last:a]); out.append(" "); last = b
        out.append(text[last:])
        s2 = "".join(out)
        lines = [re.sub(r"[ \t]+", " ", ln).strip() for ln in s2.split("\n")]
        return " \n ".join(ln for ln in lines if ln)

    N_PLACEBO = 3
    prng = np.random.default_rng(SEED + 101)
    for rep_i in range(N_PLACEBO):
        texts[f"_PLACEBO_{rep_i + 1}"] = [
            placebo_strip(texts["FULL"][i], removal_audit[i]["blacklist_tokens"],
                          removal_audit[i]["tokens_before"] - removal_audit[i]["tokens_after"],
                          prng)
            for i in range(n_rows)]

    # RF2-C 의 primary_controls 는 필드 집합이 CONTROL_ONLY 와 동일하나 결합 순서가 다르다.
    # 순서 차이가 결론을 흔드는지 보려고 replication 용으로만 하나 더 만든다(주 4종에는 넣지 않음).
    RF2C_ORDER = ["buttons", "aria_labels", "form_labels", "placeholders", "input_names"]
    texts["_REPL_CONTROL_RF2C_ORDER"] = [join_fields(r, RF2C_ORDER) for _, r in df.iterrows()]

    tokcount = {k: np.array([len(TOK.findall(t)) for t in v]) for k, v in texts.items()}
    valid = {k: tokcount[k] >= 2 for k in texts}
    complete = np.ones(n_rows, dtype=bool)
    for r in REPS:
        complete &= valid[r]
    idx_all = np.arange(n_rows)
    idx_complete = idx_all[complete]

    # ------------------------------------------------------------- encoding
    order_keys = list(texts.keys())
    flat, offsets = [], {}
    for k in order_keys:
        offsets[k] = len(flat)
        flat.extend(texts[k])
    proto_keys = []
    for sname, pset in PROTO_SETS.items():
        for a in ARCHETYPES:
            proto_keys.append((sname, a))
            flat.append(pset[a])
    print(f"[encode] {len(flat)} texts on {MODEL_HF}", flush=True)
    V, tok_ids, max_seq = encode(flat)

    doc_vec = {k: V[offsets[k]: offsets[k] + n_rows] for k in order_keys}
    p_off = len(order_keys) * n_rows
    proto_vec = {}
    for j, (sname, a) in enumerate(proto_keys):
        proto_vec.setdefault(sname, {})[a] = V[p_off + j]
    P = {s: np.stack([proto_vec[s][a] for a in ARCHETYPES]) for s in PROTO_SETS}

    sims = {(rep, s): doc_vec[rep] @ P[s].T for rep in texts for s in PROTO_SETS}
    preds = {}
    top2 = {}
    margins = {}
    for key, sm in sims.items():
        o = np.argsort(-sm, axis=1)
        preds[key] = o[:, 0]
        top2[key] = [frozenset(o[i, :2].tolist()) for i in range(n_rows)]
        margins[key] = sm[np.arange(n_rows), o[:, 0]] - sm[np.arange(n_rows), o[:, 1]]

    # ------------------------------------------------------------- baselines
    counts = np.array([int((true_idx == c).sum()) for c in range(7)])
    p_class = counts / counts.sum()

    def strat_null(idx: np.ndarray) -> dict:
        t = true_idx[idx]
        draws = rng.choice(7, size=(N_STRAT, len(idx)), p=p_class)
        f1 = macro_f1_batch(draws, t)
        pa = (draws == t[None, :]).mean(axis=1)
        return {"n_draws": N_STRAT,
                "macro_f1_mean": float(f1.mean()), "macro_f1_p50": float(np.percentile(f1, 50)),
                "macro_f1_p95": float(np.percentile(f1, 95)), "macro_f1_p99": float(np.percentile(f1, 99)),
                "prior_agreement_mean": float(pa.mean()),
                "prior_agreement_p95": float(np.percentile(pa, 95))}

    def majority_ref(idx: np.ndarray) -> dict:
        t = true_idx[idx]
        c = int(np.bincount(t, minlength=7).argmax())
        p = np.full(len(idx), c)
        return {"predicts": ARCHETYPES[c], "prior_agreement": float((p == t).mean()),
                "macro_f1": macro_f1(p, t),
                "note": ("majority 는 6/7 class 에서 recall 0 이라 macro F1 lift 의 판정 기준선이 "
                         "될 수 없다. 참고용으로만 병기한다.")}

    perms = {}
    for name, idx in (("all56", idx_all), ("complete_case", idx_complete)):
        t = true_idx[idx]
        pm = np.stack([rng.permutation(t) for _ in range(N_PERM)])
        perms[name] = (idx, t, pm)

    def perm_position(rep: str, s: str, setname: str) -> dict:
        idx, t, pm = perms[setname]
        p1 = preds[(rep, s)][idx]
        obs_f1 = macro_f1(p1, t)
        obs_pa = float((p1 == t).mean())
        null_f1 = macro_f1_batch(p1, pm)
        null_pa = (pm == p1[None, :]).mean(axis=1)
        return {
            "observed_macro_f1": obs_f1,
            "perm_null_macro_f1_p50": float(np.percentile(null_f1, 50)),
            "perm_null_macro_f1_p95": float(np.percentile(null_f1, 95)),
            "perm_p_macro_f1": float((1 + int((null_f1 >= obs_f1).sum())) / (N_PERM + 1)),
            "perm_percentile_macro_f1": float((null_f1 < obs_f1).mean()),
            "observed_prior_agreement": obs_pa,
            "perm_null_prior_agreement_p95": float(np.percentile(null_pa, 95)),
            "perm_p_prior_agreement": float((1 + int((null_pa >= obs_pa).sum())) / (N_PERM + 1)),
        }

    baselines = {
        "all56": {"stratified": strat_null(idx_all), "majority_reference": majority_ref(idx_all)},
        "complete_case": {"stratified": strat_null(idx_complete),
                          "majority_reference": majority_ref(idx_complete)},
    }

    # ------------------------------------------------------- per-config table
    per_config = {}
    for rep in REPS:
        for s in PROTO_SETS:
            key = f"{rep}|{s}"
            per_config[key] = {
                "representation": rep, "prototype_set": s,
                "all56": config_metrics(sims[(rep, s)], true_idx, idx_all),
                "complete_case": config_metrics(sims[(rep, s)], true_idx, idx_complete),
                "nonempty_only": config_metrics(sims[(rep, s)], true_idx, idx_all[valid[rep]]),
                "permutation_null_complete_case": perm_position(rep, s, "complete_case"),
                "permutation_null_all56": perm_position(rep, s, "all56"),
                "beats_stratified_p95_complete_case": bool(
                    config_metrics(sims[(rep, s)], true_idx, idx_complete)["macro_f1"]
                    > baselines["complete_case"]["stratified"]["macro_f1_p95"]),
                "n_valid_targets": int(valid[rep].sum()),
                "n_empty_or_degenerate": int((~valid[rep]).sum()),
                "tokens_median": float(np.median(tokcount[rep])),
                "tokens_min": int(tokcount[rep].min()),
                "tokens_max": int(tokcount[rep].max()),
            }

    # ----------------------------------------------- PRIMARY: stability first
    def pair_stability(idx: np.ndarray, s: str) -> dict:
        out = {}
        for i, a in enumerate(REPS):
            for b in REPS[i + 1:]:
                pa_, pb_ = preds[(a, s)][idx], preds[(b, s)][idx]
                k = int((pa_ == pb_).sum())
                t2a = [top2[(a, s)][j] for j in idx]
                t2b = [top2[(b, s)][j] for j in idx]
                k2 = sum(1 for x, y in zip(t2a, t2b) if x == y)
                out[f"{a}~{b}"] = {
                    "top1_agreement": float(k / len(idx)),
                    "top1_agreement_fraction": f"{k}/{len(idx)}",
                    "top1_agreement_wilson95": wilson(k, len(idx)),
                    "top1_cohen_kappa": cohen_kappa([ARCHETYPES[c] for c in pa_],
                                                    [ARCHETYPES[c] for c in pb_]),
                    "top2_set_agreement": float(k2 / len(idx)),
                    "top2_set_agreement_fraction": f"{k2}/{len(idx)}",
                    "top2_set_agreement_wilson95": wilson(k2, len(idx)),
                }
        return out

    def unanimity(idx: np.ndarray, s: str) -> dict:
        M = np.stack([preds[(r, s)][idx] for r in REPS])
        una = int((M == M[0]).all(axis=0).sum())
        T2 = [[top2[(r, s)][j] for j in idx] for r in REPS]
        una2 = sum(1 for j in range(len(idx)) if len({T2[k][j] for k in range(4)}) == 1)
        ndist = [int(len(set(M[:, j].tolist()))) for j in range(len(idx))]
        return {
            "n": int(len(idx)),
            "four_way_top1_unanimity": float(una / len(idx)) if len(idx) else float("nan"),
            "four_way_top1_unanimity_fraction": f"{una}/{len(idx)}",
            "four_way_top1_unanimity_wilson95": wilson(una, len(idx)),
            "four_way_top2_set_unanimity": float(una2 / len(idx)) if len(idx) else float("nan"),
            "four_way_top2_set_unanimity_fraction": f"{una2}/{len(idx)}",
            "four_way_top2_set_unanimity_wilson95": wilson(una2, len(idx)),
            "distinct_predictions_per_target_hist": {str(v): ndist.count(v) for v in sorted(set(ndist))},
            "mean_distinct_predictions_per_target": float(np.mean(ndist)) if len(idx) else float("nan"),
        }

    stability = {
        "note": ("판정 우선순위 1순위. 같은 target 이 4개 representation 에서 같은 archetype 을 "
                 "받는가. prior label 과 무관한 지표라 gold label 없이도 해석 가능하다."),
        "primary_prototype_set": PRIMARY_PROTO,
        "complete_case": {s: {"pairwise": pair_stability(idx_complete, s),
                              "unanimity": unanimity(idx_complete, s)} for s in PROTO_SETS},
        "all56": {s: {"pairwise": pair_stability(idx_all, s),
                      "unanimity": unanimity(idx_all, s)} for s in PROTO_SETS},
    }

    # prototype stability: 같은 representation 에서 prototype 세트만 바꿨을 때
    proto_stability = {}
    for rep in REPS:
        idxr = idx_all[valid[rep]]
        pairs = {}
        setnames = list(PROTO_SETS)
        for i, a in enumerate(setnames):
            for b in setnames[i + 1:]:
                pa_, pb_ = preds[(rep, a)][idxr], preds[(rep, b)][idxr]
                k = int((pa_ == pb_).sum())
                t2a = [top2[(rep, a)][j] for j in idxr]
                t2b = [top2[(rep, b)][j] for j in idxr]
                k2 = sum(1 for x, y in zip(t2a, t2b) if x == y)
                pairs[f"{a}~{b}"] = {
                    "top1_agreement": float(k / len(idxr)),
                    "top1_agreement_fraction": f"{k}/{len(idxr)}",
                    "cohen_kappa": cohen_kappa([ARCHETYPES[c] for c in pa_],
                                               [ARCHETYPES[c] for c in pb_]),
                    "top2_set_agreement": float(k2 / len(idxr)),
                }
        M = np.stack([preds[(rep, s)][idxr] for s in setnames])
        una = int((M == M[0]).all(axis=0).sum())
        f1s = {s: per_config[f"{rep}|{s}"]["complete_case"]["macro_f1"] for s in setnames}
        proto_stability[rep] = {
            "n_valid": int(len(idxr)),
            "pairwise": pairs,
            "three_way_unanimity": float(una / len(idxr)),
            "three_way_unanimity_fraction": f"{una}/{len(idxr)}",
            "macro_f1_by_prototype_set_complete_case": f1s,
            "macro_f1_range": float(max(f1s.values()) - min(f1s.values())),
            "verdict_flip_vs_stratified_p95": bool(
                any(v > baselines["complete_case"]["stratified"]["macro_f1_p95"] for v in f1s.values())
                and any(v <= baselines["complete_case"]["stratified"]["macro_f1_p95"] for v in f1s.values())),
        }

    # ------------------------------------------------------------ strata 분해
    strata_names = ["FUNCTIONAL_LANDING", "UNDETERMINED", "CORPORATE_OR_APP_LANDING"]
    by_strata = {}
    for st in strata_names:
        mask = (df["identity_class"] == st).to_numpy()
        idx_st_all = idx_all[mask]
        idx_st_cc = idx_all[mask & complete]
        entry = {
            "n_all56": int(mask.sum()),
            "n_complete_case": int(len(idx_st_cc)),
            "estimability_note": ("n=3 은 사실상 추정 불가에 가깝다. Wilson CI 폭이 거의 전 구간이라 "
                                  "어떤 순위 비교도 이 stratum 단독으로는 성립하지 않는다."
                                  if int(mask.sum()) <= 5 else "n>=20, 구간추정 가능하나 여전히 소표본."),
            "per_representation": {},
        }
        for rep in REPS:
            entry["per_representation"][rep] = {
                "complete_case": config_metrics(sims[(rep, PRIMARY_PROTO)], true_idx, idx_st_cc)
                if len(idx_st_cc) else {"n": 0},
                "all56": config_metrics(sims[(rep, PRIMARY_PROTO)], true_idx, idx_st_all)
                if len(idx_st_all) else {"n": 0},
            }
        if len(idx_st_cc):
            entry["stability_complete_case"] = {
                "pairwise": pair_stability(idx_st_cc, PRIMARY_PROTO),
                "unanimity": unanimity(idx_st_cc, PRIMARY_PROTO),
            }
        by_strata[st] = entry

    # ----------------------------------------------------- 판정용 핵심 수치
    s = PRIMARY_PROTO
    f1cc = {rep: per_config[f"{rep}|{s}"]["complete_case"]["macro_f1"] for rep in REPS}
    pacc = {rep: per_config[f"{rep}|{s}"]["complete_case"]["prior_agreement"] for rep in REPS}
    d_ctrl_topic = f1cc["CONTROL_ONLY"] - f1cc["TOPIC_ONLY"]
    drop_brand = f1cc["FULL"] - f1cc["NO_BRAND_DOMAIN"]
    agree_fn = stability["complete_case"][s]["pairwise"]["FULL~NO_BRAND_DOMAIN"]["top1_agreement"]
    pred_change_brand = 1.0 - agree_fn
    agree_ctrl_topic = stability["complete_case"][s]["pairwise"]["CONTROL_ONLY~TOPIC_ONLY"]["top1_agreement"]

    # paired bootstrap CI (target 재표집)
    tcc = true_idx[idx_complete]
    pr = {rep: preds[(rep, s)][idx_complete] for rep in REPS}
    boot_d, boot_drop = [], []
    nn = len(idx_complete)
    for _ in range(N_BOOT):
        b = rng.integers(0, nn, nn)
        boot_d.append(macro_f1(pr["CONTROL_ONLY"][b], tcc[b]) - macro_f1(pr["TOPIC_ONLY"][b], tcc[b]))
        boot_drop.append(macro_f1(pr["FULL"][b], tcc[b]) - macro_f1(pr["NO_BRAND_DOMAIN"][b], tcc[b]))
    ci_d = [float(np.percentile(boot_d, 2.5)), float(np.percentile(boot_d, 97.5))]
    ci_drop = [float(np.percentile(boot_drop, 2.5)), float(np.percentile(boot_drop, 97.5))]

    mcn_ctrl_topic = mcnemar_exact((pr["CONTROL_ONLY"] == tcc).astype(int),
                                   (pr["TOPIC_ONLY"] == tcc).astype(int))
    mcn_brand = mcnemar_exact((pr["FULL"] == tcc).astype(int),
                              (pr["NO_BRAND_DOMAIN"] == tcc).astype(int))

    strat_p95 = baselines["complete_case"]["stratified"]["macro_f1_p95"]
    ctrl_beats = f1cc["CONTROL_ONLY"] > strat_p95
    topic_beats = f1cc["TOPIC_ONLY"] > strat_p95

    # ------------------------------------------------------------- 판정 적용
    hv = {}

    # INTERACTION
    dir_i = d_ctrl_topic > 0
    mag_i = d_ctrl_topic > 0.05
    rob_i = (drop_brand < 0.05) and (pred_change_brand < 0.15)
    if mag_i and rob_i:
        hv["H-SUP01-INTERACTION"] = "SUPPORTED"
    elif d_ctrl_topic < -0.05:
        hv["H-SUP01-INTERACTION"] = "REFUTED"
    elif dir_i and (mag_i or rob_i):
        hv["H-SUP01-INTERACTION"] = "PARTIALLY_SUPPORTED"
    else:
        hv["H-SUP01-INTERACTION"] = "NOT_SUPPORTED"

    # DOMAIN
    mag_d = d_ctrl_topic < -0.05
    brand_dep = (drop_brand > 0.10) or (pred_change_brand > 0.25)
    if mag_d and brand_dep:
        hv["H-SUP01-DOMAIN"] = "SUPPORTED"
    elif d_ctrl_topic > 0.05:
        hv["H-SUP01-DOMAIN"] = "REFUTED"
    elif mag_d or brand_dep:
        hv["H-SUP01-DOMAIN"] = "PARTIALLY_SUPPORTED"
    else:
        hv["H-SUP01-DOMAIN"] = "NOT_SUPPORTED"

    # BOTH
    cond_both = [bool(ctrl_beats and topic_beats), bool(agree_ctrl_topic < 0.60),
                 bool(f1cc["FULL"] >= max(f1cc["CONTROL_ONLY"], f1cc["TOPIC_ONLY"]) - 0.02)]
    hv["H-SUP01-BOTH"] = ("SUPPORTED" if all(cond_both)
                          else "PARTIALLY_SUPPORTED" if sum(cond_both) == 2
                          else "NOT_SUPPORTED")

    # INSEPARABLE
    zero_in_d = ci_d[0] <= 0 <= ci_d[1]
    zero_in_drop = ci_drop[0] <= 0 <= ci_drop[1]
    hv["H-SUP01-INSEPARABLE"] = ("SUPPORTED" if (zero_in_d and zero_in_drop)
                                 else "PARTIALLY_SUPPORTED" if (zero_in_d or zero_in_drop)
                                 else "NOT_SUPPORTED")

    main3 = {k: hv[k] for k in ("H-SUP01-INTERACTION", "H-SUP01-DOMAIN", "H-SUP01-BOTH")}
    n_sup = sum(1 for v in main3.values() if v == "SUPPORTED")
    if hv["H-SUP01-INSEPARABLE"] == "SUPPORTED":
        overall = "INCONCLUSIVE"
    elif n_sup == 1:
        overall = "SUPPORTED"
    elif any(v == "PARTIALLY_SUPPORTED" for v in main3.values()):
        overall = "PARTIALLY_SUPPORTED"
    else:
        overall = "INCONCLUSIVE"

    # ------------------------------------------------------------- 반례 목록
    counterexamples = []
    for j in idx_complete:
        row = df.iloc[j]
        pj = {rep: ARCHETYPES[preds[(rep, s)][j]] for rep in REPS}
        if len(set(pj.values())) >= 3:
            counterexamples.append({
                "wtg": row["wtg"], "prior_service": row["prior_service"],
                "prior_archetype": row["prior_archetype"],
                "identity_class": row["identity_class"],
                "predictions": pj,
                "margin_FULL": float(margins[("FULL", s)][j]),
                "note": "4개 representation 이 3개 이상 서로 다른 archetype 을 준 target",
            })
    brand_flips = []
    for j in idx_complete:
        if preds[("FULL", s)][j] != preds[("NO_BRAND_DOMAIN", s)][j]:
            row = df.iloc[j]
            brand_flips.append({
                "wtg": row["wtg"], "prior_service": row["prior_service"],
                "prior_archetype": row["prior_archetype"],
                "FULL": ARCHETYPES[preds[("FULL", s)][j]],
                "NO_BRAND_DOMAIN": ARCHETYPES[preds[("NO_BRAND_DOMAIN", s)][j]],
                "n_removed_occurrences": removal_audit[j]["n_removed_occurrences"],
            })

    # ------------------------------------------------- RF2-C 대조 (replication)
    repl = {}
    for s2 in [PRIMARY_PROTO]:
        m_ctrl = config_metrics(sims[("CONTROL_ONLY", s2)], true_idx, idx_all)
        m_ctrl_rf2 = config_metrics(sims[("_REPL_CONTROL_RF2C_ORDER", s2)], true_idx, idx_all)
        m_full = config_metrics(sims[("FULL", s2)], true_idx, idx_all)
        repl = {
            "note": ("RF2-C(field ablation) 의 primary_controls 는 CONTROL_ONLY 와 필드 집합이 "
                     "같고 결합 순서만 다르다(RF2-C: buttons,aria,form,placeholder,input / "
                     "여기: buttons,aria,placeholder,form,input). text_blob__ALL 은 FULL 과 동일 정의다. "
                     "재현 여부를 대조해 이 run 의 파이프라인이 기존 D 파이프라인과 어긋나지 "
                     "않는지 확인한다."),
            "rf2c_reported": {"primary_controls_macro_f1": 0.2543,
                              "primary_controls_prior_agreement_all56": 0.3036,
                              "text_blob_ALL_macro_f1": 0.5088,
                              "text_blob_ALL_prior_agreement_all56": 0.6786,
                              "source": "results/RF2_C_field_ablation.json (읽기 전용 참조)"},
            "dsup01_recomputed": {
                "CONTROL_ONLY_macro_f1_all56": m_ctrl["macro_f1"],
                "CONTROL_ONLY_prior_agreement_all56": m_ctrl["prior_agreement"],
                "CONTROL_ONLY_RF2C_FIELD_ORDER_macro_f1_all56": m_ctrl_rf2["macro_f1"],
                "CONTROL_ONLY_RF2C_FIELD_ORDER_prior_agreement_all56": m_ctrl_rf2["prior_agreement"],
                "FULL_macro_f1_all56": m_full["macro_f1"],
                "FULL_prior_agreement_all56": m_full["prior_agreement"],
            },
        }
        repl["field_order_effect_on_macro_f1"] = abs(
            m_ctrl["macro_f1"] - m_ctrl_rf2["macro_f1"])

    # ------------------------------------------------------------------ JSON
    result = {
        "verdict": overall,
        "rq_id": "D-SUP-01",
        "child_id": "D-SUP-01",
        "inquiry_kind": "DIRECTOR_SUPPLEMENTAL",
        "depends_on": "RQ-D14",
        "hypothesis_id": "H-SUP01-SIGNAL-SOURCE",
        "competing_hypothesis": "INTERACTION / DOMAIN / BOTH / INSEPARABLE",
        "title": ("RF embedding signal 은 representative interaction semantics 인가 "
                  "business/domain semantics 인가 — representation ablation 기반 반증"),
        "generated_at_kst": datetime.now(KST).isoformat(),
        "seed": SEED,
        "model": {"hf_id": MODEL_HF, "single_model_by_design": True,
                  "max_seq_length": max_seq,
                  "note": ("모델 비교는 이 inquiry 의 주제가 아니다. bge-m3 고정. "
                           "instruction prefix 미사용(bge-m3 공식 규약)."),
                  "offline": {"HF_HUB_OFFLINE": os.environ.get("HF_HUB_OFFLINE"),
                              "TRANSFORMERS_OFFLINE": os.environ.get("TRANSFORMERS_OFFLINE")}},
        "learning": "none (zero-shot). prior_archetype 으로 어떤 파라미터도 적합하지 않았다.",
        "target_variable": {
            "field": "prior_archetype",
            "warning": ("gold label 이 아니라 business-domain prior 다. 지표 이름은 accuracy 가 "
                        "아니라 prior_agreement 이며 diagnostic 으로만 쓴다. 헤드라인 판정은 "
                        "stability 계열이다."),
            "class_counts": {a: int(counts[A2I[a]]) for a in ARCHETYPES},
        },
        "analysis_unit": "target state (in_mart==1), 1 row = 1 web target",
        "n_expected": 56,
        "n_observed": n_rows,
        "missing": {
            "n_missing_stratum_join": n_missing_stratum,
            "n_empty_or_degenerate_by_representation": {r: int((~valid[r]).sum()) for r in REPS},
            "empty_representation_targets": {
                r: [{"wtg": df.iloc[j]["wtg"], "prior_service": df.iloc[j]["prior_service"],
                     "tokens": int(tokcount[r][j])}
                    for j in idx_all[~valid[r]]] for r in REPS},
            "n_complete_case": int(complete.sum()),
            "complete_case_rule": "4개 representation 모두 토큰 수 >= 2",
            "observation_table_join_ok": obs_join_ok,
            "host_mismatch_prior_url_vs_d14": host_mismatch,
        },
        "inputs": {
            k: {"path": str(v), "sha256": sha256_file(v), "bytes": v.stat().st_size,
                "rows": (n_rows if k == "corpus" else (len(obs) if k == "observation_table" else 56))}
            for k, v in INPUTS.items()},
        "firewall": {
            "opened_files": [str(v) for v in INPUTS.values()],
            "not_opened": ("holdout label · LABEL_SPLIT_FROZEN* · HOLDOUT_FOR_C* · RAW_L1~L4* · "
                           "PACKET_L* · *_OVERLAP* · PRECEDENCE_CONTESTED* · CALIBRATION_FOR_B* · "
                           "**/control/** · B/C target-level holdout error report 를 열지 않았다."),
            "labels_produced": False, "real_target_contacted": False, "network_download": False,
            "production_modified": False,
            "threshold_or_go_nogo": "선언하지 않는다. 이 산출물은 threshold 도 GO/NO-GO 도 정하지 않는다.",
        },
        "prereg": PREREG,
        "prototype_sets": PROTO_SETS,
        "prototype_provenance": ("RF001-C 에서 동결된 3세트를 문구 그대로 재사용했다. 원 provenance 는 "
                                 "SSOT 00 §4 archetype 목록 + SSOT 01 §5 Stage-3 branch 정의문이며, "
                                 "D_TEXT_CORPUS 를 읽고 조정하지 않았고 결과를 본 뒤에도 수정하지 않았다."),
        "representation_definitions": REP_DEFINITION_TEXT,
        "representation_fields": {"FULL": ALL_FIELDS, "CONTROL_ONLY": CTRL_FIELDS,
                                  "TOPIC_ONLY": TOPIC_FIELDS, "NO_BRAND_DOMAIN": ALL_FIELDS},
        "brand_domain_removal": {
            "rule_text": REP_DEFINITION_TEXT["NO_BRAND_DOMAIN"],
            "url_syntax_tokens_always_removed": URL_SYNTAX_TOKENS,
            "n_distinct_tokens_removed": len(all_removed),
            "n_total_removed_occurrences": int(sum(all_removed.values())),
            "removed_token_occurrence_counts_global": dict(all_removed.most_common()),
            "per_target": removal_audit,
            "collateral_risk_note": ("한글 브랜드 토큰은 어절 경계가 없어 부분문자열로 지운다. "
                                     "'다음'(Daum) 처럼 브랜드명이 일반어와 같은 경우 일반어까지 "
                                     "지워진다. 해당 사례와 제거 횟수는 per_target 에 전부 남겼다."),
        },
        "token_stats": {r: {"median": float(np.median(tokcount[r])),
                            "p10": float(np.percentile(tokcount[r], 10)),
                            "p90": float(np.percentile(tokcount[r], 90)),
                            "min": int(tokcount[r].min()), "max": int(tokcount[r].max()),
                            "n_zero": int((tokcount[r] == 0).sum())} for r in REPS},
        "baselines": baselines,
        "stability_across_representations": stability,
        "prototype_stability": proto_stability,
        "per_config": per_config,
        "by_strata": by_strata,
        "strata_source": {"file": str(INPUTS["strata"]),
                          "field": "per_target[].identity_class", "join_key": "wtg",
                          "counts": {k: int((df["identity_class"] == k).sum()) for k in strata_names}},
        "decision_quantities": {
            "prototype_set": PRIMARY_PROTO, "analysis_set": "complete_case",
            "macro_f1_by_representation": f1cc,
            "prior_agreement_by_representation_diagnostic": pacc,
            "d_ctrl_topic": d_ctrl_topic,
            "d_ctrl_topic_boot95": ci_d,
            "drop_brand": drop_brand,
            "drop_brand_boot95": ci_drop,
            "pred_change_brand": pred_change_brand,
            "agree_ctrl_topic": agree_ctrl_topic,
            "stratified_p95_macro_f1": strat_p95,
            "control_only_beats_stratified_p95": bool(ctrl_beats),
            "topic_only_beats_stratified_p95": bool(topic_beats),
            "mcnemar_control_vs_topic_prior_agreement": mcn_ctrl_topic,
            "mcnemar_full_vs_nobrand_prior_agreement": mcn_brand,
            "n_bootstrap": N_BOOT, "n_permutation": N_PERM, "n_stratified_draws": N_STRAT,
        },
        "hypothesis_verdicts": hv,
        "counterexamples": {
            "high_disagreement_targets": counterexamples,
            "brand_removal_flips": brand_flips,
            "n_high_disagreement": len(counterexamples),
            "n_brand_removal_flips": len(brand_flips),
        },
        "replication_check_vs_RF2_C": repl,
        "per_target": [
            {"wtg": df.iloc[j]["wtg"], "prior_service": df.iloc[j]["prior_service"],
             "prior_archetype": df.iloc[j]["prior_archetype"],
             "prior_business_domain": df.iloc[j]["prior_business_domain"],
             "identity_class": df.iloc[j]["identity_class"],
             "complete_case": bool(complete[j]),
             "tokens": {r: int(tokcount[r][j]) for r in REPS},
             "pred": {r: ARCHETYPES[preds[(r, PRIMARY_PROTO)][j]] for r in REPS},
             "top2": {r: sorted(ARCHETYPES[c] for c in top2[(r, PRIMARY_PROTO)][j]) for r in REPS},
             "margin": {r: float(margins[(r, PRIMARY_PROTO)][j]) for r in REPS},
             "n_distinct_pred_across_reps": int(len({preds[(r, PRIMARY_PROTO)][j] for r in REPS}))}
            for j in range(n_rows)],
        "figures": sorted(p.name for p in FIGDIR.glob("DSUP01_*.png")),
        "limitation": (
            f"(1) target 은 gold label 이 아니라 business-domain prior 다. prior_agreement 는 "
            f"진리 대비 정확도가 아니라 prior 와의 일치도이고, prior 자체가 업종에서 유도됐기 "
            f"때문에 '업종 어휘가 prior 를 맞힌다' 는 결과는 부분적으로 순환이다. 이 순환을 "
            f"끊지 못하는 것이 이 inquiry 의 가장 무거운 한계다. "
            f"(2) n={n_rows} 에 7 class, 5개 class 가 n<=5 라 per-class 추정의 CI 가 거의 [0,1] 이다. "
            f"(3) CORPORATE_OR_APP_LANDING stratum 은 n=3 이라 사실상 추정 불가에 가깝다. "
            f"(4) CONTROL_ONLY 는 {int((~valid['CONTROL_ONLY']).sum())}개 target 에서 비어 있어 "
            f"'컨트롤 표면이 약하다' 는 결과가 컨트롤의 의미론적 무력함인지 수집 시점의 DOM "
            f"부재(SPA·앱 인터스티셜)인지 이 설계로는 분리되지 않는다. "
            f"(5) 한글 브랜드 토큰 제거는 어절 경계가 없어 부분문자열로 지우므로 일반어 부수 제거가 "
            f"발생한다(감사 목록 전문 공개). "
            f"(6) 단일 모델·단일 임베딩 공간이며 cross-encoder 2차 모델은 시험하지 않았다. "
            f"(7) 이 산출물은 threshold 도 GO/NO-GO 도 정하지 않는다."),
        "further_questions": [
            "prior_archetype 대신 독립 gold label 로 같은 ablation 을 돌리면 순환이 끊기는가 "
            "(라벨 생산은 D 권한 밖이므로 A 의 labeler worker 필요).",
            "CONTROL_ONLY 가 빈 target 을 렌더 후 DOM(SPA hydration 이후)으로 다시 수집하면 "
            "컨트롤 표면의 신호가 살아나는가.",
            "업종(prior_business_domain)을 통제한 within-domain 대조 — 같은 업종 안에서 "
            "archetype 이 갈리는 target 쌍이 존재하는 표본을 모으면 두 원천이 분리 가능한가.",
            "title 단독이 FULL 보다 강하다는 RF2-C 관측이 brand token 제거 후에도 유지되는가 "
            "(TOPIC_ONLY 내부의 필드별 재분해).",
            "top-2 집합이 안정적인 target 만 자동 매핑하고 나머지를 abstain 시키는 운영 규칙의 "
            "coverage-정확도 곡선(단, threshold 선언은 A 권한).",
        ],
    }

    # ------------------------------------------------------------------ 그림
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    short = {"FULL": "FULL", "CONTROL_ONLY": "CTRL", "TOPIC_ONLY": "TOPIC",
             "NO_BRAND_DOMAIN": "NOBRAND"}

    # fig 1 — stability
    fig, ax = plt.subplots(1, 3, figsize=(15, 4.4))
    M1 = np.zeros((4, 4)); M2 = np.zeros((4, 4))
    for i, a in enumerate(REPS):
        for j, b in enumerate(REPS):
            if i == j:
                M1[i, j] = M2[i, j] = 1.0
            else:
                k = f"{a}~{b}" if f"{a}~{b}" in stability["complete_case"][s]["pairwise"] else f"{b}~{a}"
                M1[i, j] = stability["complete_case"][s]["pairwise"][k]["top1_agreement"]
                M2[i, j] = stability["complete_case"][s]["pairwise"][k]["top2_set_agreement"]
    for k, (M, ttl) in enumerate(((M1, "top-1 agreement"), (M2, "top-2 set agreement"))):
        im = ax[k].imshow(M, vmin=0, vmax=1, cmap="viridis")
        ax[k].set_xticks(range(4), [short[r] for r in REPS], rotation=30)
        ax[k].set_yticks(range(4), [short[r] for r in REPS])
        for i in range(4):
            for j in range(4):
                ax[k].text(j, i, f"{M[i, j]:.2f}", ha="center", va="center",
                           color="w" if M[i, j] < 0.6 else "k", fontsize=9)
        ax[k].set_title(f"{ttl} (complete-case n={len(idx_complete)})", fontsize=10)
        fig.colorbar(im, ax=ax[k], fraction=0.046)
    labels, vals, errs = [], [], []
    for st in ["ALL"] + strata_names:
        if st == "ALL":
            u = stability["complete_case"][s]["unanimity"]
        else:
            u = by_strata[st].get("stability_complete_case", {}).get("unanimity")
            if not u:
                continue
        SHORT_STRATA = {"ALL": "ALL", "FUNCTIONAL_LANDING": "FUNC", "UNDETERMINED": "UNDET", "CORPORATE_OR_APP_LANDING": "CORP"}
        labels.append(f"{SHORT_STRATA[st]}\nn={u['n']}")
        vals.append(u["four_way_top1_unanimity"])
        lo, hi = u["four_way_top1_unanimity_wilson95"]
        errs.append([u["four_way_top1_unanimity"] - lo, hi - u["four_way_top1_unanimity"]])
    ax[2].bar(range(len(vals)), vals, color="#4c72b0",
              yerr=np.array(errs).T, capsize=4)
    ax[2].set_xticks(range(len(vals)), labels, fontsize=8)
    ax[2].set_ylim(0, 1); ax[2].set_ylabel("4-way top-1 unanimity")
    ax[2].set_title("prediction stability by stratum (Wilson 95%)", fontsize=10)
    fig.suptitle("D-SUP-01 prediction stability across 4 representations (bge-m3, proto A)",
                 fontsize=11)
    fig.tight_layout()
    fig.savefig(FIGDIR / "DSUP01_stability_matrix.png", dpi=140); plt.close(fig)

    # fig 2 — signal strength / margin / coverage
    fig, ax = plt.subplots(1, 3, figsize=(15, 4.4))
    xs = np.arange(4)
    f1v = [f1cc[r] for r in REPS]
    pav = [pacc[r] for r in REPS]
    ax[0].bar(xs - 0.18, f1v, 0.36, label="macro F1", color="#4c72b0")
    ax[0].bar(xs + 0.18, pav, 0.36, label="prior_agreement (diagnostic)", color="#dd8452")
    ax[0].axhline(strat_p95, ls="--", c="k", lw=1,
                  label=f"stratified p95 macroF1={strat_p95:.3f}")
    ax[0].set_xticks(xs, [short[r] for r in REPS])
    ax[0].set_ylim(0, 1); ax[0].legend(fontsize=7)
    ax[0].set_title(f"signal vs stratified null (complete-case n={len(idx_complete)})", fontsize=10)
    data = [margins[(r, s)][idx_complete] for r in REPS]
    ax[1].boxplot(data, showfliers=False)
    ax[1].set_xticks(range(1, 5), [short[r] for r in REPS])
    ax[1].set_ylabel("top1 - top2 cosine margin")
    ax[1].set_title("margin distribution", fontsize=10)
    cov = [per_config[f"{r}|{s}"]["complete_case"]["n_distinct_predicted_classes"] for r in REPS]
    ax[2].bar(xs, cov, color="#55a868")
    ax[2].axhline(7, ls="--", c="k", lw=1, label="7 archetypes")
    for i, v in enumerate(cov):
        ax[2].text(i, v + 0.1, str(v), ha="center")
    ax[2].set_xticks(xs, [short[r] for r in REPS]); ax[2].set_ylim(0, 7.8)
    ax[2].set_ylabel("distinct predicted classes"); ax[2].legend(fontsize=8)
    ax[2].set_title("class coverage", fontsize=10)
    fig.suptitle("D-SUP-01 representation ablation — diagnostic strength, margin, coverage",
                 fontsize=11)
    fig.tight_layout()
    fig.savefig(FIGDIR / "DSUP01_signal_margin_coverage.png", dpi=140); plt.close(fig)

    # fig 3 — strata
    fig, ax = plt.subplots(1, 2, figsize=(12, 4.4))
    w = 0.22
    for i, st in enumerate(strata_names):
        vals, errs = [], []
        for r in REPS:
            m = by_strata[st]["per_representation"][r]["complete_case"]
            if m.get("n", 0) == 0:
                vals.append(np.nan); errs.append([0, 0]); continue
            v = m["prior_agreement"]; lo, hi = m["prior_agreement_wilson95"]
            vals.append(v); errs.append([v - lo, hi - v])
        ax[0].bar(np.arange(4) + (i - 1) * w, vals, w,
                  yerr=np.array(errs).T, capsize=3,
                  label=f"{st} (n={by_strata[st]['n_complete_case']})")
    ax[0].set_xticks(range(4), [short[r] for r in REPS])
    ax[0].set_ylim(0, 1.05); ax[0].legend(fontsize=7)
    ax[0].set_ylabel("prior_agreement (diagnostic, Wilson 95%)")
    ax[0].set_title("by identity stratum (RQ-D14) — n=3 stratum is near-inestimable", fontsize=9)
    for i, st in enumerate(strata_names):
        vals = []
        for r in REPS:
            m = by_strata[st]["per_representation"][r]["complete_case"]
            vals.append(m.get("macro_f1", np.nan) if m.get("n", 0) else np.nan)
        ax[1].bar(np.arange(4) + (i - 1) * w, vals, w, label=st)
    ax[1].set_xticks(range(4), [short[r] for r in REPS])
    ax[1].set_ylim(0, 1.05); ax[1].legend(fontsize=7)
    ax[1].set_ylabel("macro F1 vs prior"); ax[1].set_title("macro F1 by stratum", fontsize=9)
    fig.suptitle("D-SUP-01 strata decomposition (proto A, complete-case)", fontsize=11)
    fig.tight_layout()
    fig.savefig(FIGDIR / "DSUP01_strata.png", dpi=140); plt.close(fig)

    # fig 4 — prototype stability
    fig, ax = plt.subplots(1, 2, figsize=(12, 4.2))
    setnames = list(PROTO_SETS)
    K = np.zeros((4, 3))
    for i, r in enumerate(REPS):
        for j, pair in enumerate(proto_stability[r]["pairwise"]):
            K[i, j] = proto_stability[r]["pairwise"][pair]["cohen_kappa"]
    im = ax[0].imshow(K, vmin=-0.1, vmax=1, cmap="magma")
    ax[0].set_yticks(range(4), [short[r] for r in REPS])
    ax[0].set_xticks(range(3), [p.replace("_", " ") for p in proto_stability[REPS[0]]["pairwise"]],
                     rotation=20, fontsize=7)
    for i in range(4):
        for j in range(3):
            ax[0].text(j, i, f"{K[i, j]:.2f}", ha="center", va="center", color="w", fontsize=9)
    ax[0].set_title("prototype-set Cohen kappa (same representation)", fontsize=10)
    fig.colorbar(im, ax=ax[0], fraction=0.046)
    for j, ps in enumerate(setnames):
        ax[1].bar(np.arange(4) + (j - 1) * 0.26,
                  [per_config[f"{r}|{ps}"]["complete_case"]["macro_f1"] for r in REPS],
                  0.26, label=ps)
    ax[1].axhline(strat_p95, ls="--", c="k", lw=1, label="stratified p95")
    ax[1].set_xticks(range(4), [short[r] for r in REPS]); ax[1].set_ylim(0, 1)
    ax[1].legend(fontsize=7); ax[1].set_ylabel("macro F1")
    ax[1].set_title("prototype sensitivity of the ranking", fontsize=10)
    fig.suptitle("D-SUP-01 prototype stability", fontsize=11)
    fig.tight_layout()
    fig.savefig(FIGDIR / "DSUP01_prototype_stability.png", dpi=140); plt.close(fig)

    result["figures"] = sorted(p.name for p in FIGDIR.glob("DSUP01_*.png"))
    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"[write] {OUT}  verdict={result['verdict']}")
    for k, v in hv.items():
        print(f"   {k:<26} {v}")
    print(f"   d_ctrl_topic={d_ctrl_topic:+.4f} CI{ci_d}  drop_brand={drop_brand:+.4f} CI{ci_drop}")
    print(f"   4-way unanimity={stability['complete_case'][s]['unanimity']['four_way_top1_unanimity']:.4f}")

    # ---------------------------------------------------------------- MLflow
    import mlflow
    import mlflow_contract as C

    prototype_texts = []
    for sname, pset in PROTO_SETS.items():
        prototype_texts.append(f"### {sname}")
        for a in ARCHETYPES:
            prototype_texts.append(f"{a}: {pset[a]}")
        prototype_texts.append("")
    prototype_texts.append("provenance: " + result["prototype_provenance"])
    prototype_texts = "\n".join(prototype_texts)

    rb = ["# 제거된 브랜드·도메인 토큰 (NO_BRAND_DOMAIN)", "",
          result["brand_domain_removal"]["rule_text"], "",
          "## 전역 제거 횟수 (token<TAB>occurrences)"]
    for t, c in all_removed.most_common():
        rb.append(f"{t}\t{c}")
    rb.append("")
    rb.append("## target 별 blacklist 와 실제 제거")
    for a in removal_audit:
        rb.append(f"- {a['wtg']} / {a['prior_service']} / host={a['host']}")
        rb.append(f"  blacklist: {', '.join(a['blacklist_tokens'])}")
        rb.append(f"  removed: {a['removed_token_counts']}  "
                  f"tokens {a['tokens_before']} -> {a['tokens_after']}")
    removed_brand_tokens = "\n".join(rb)

    with C.research_run(
            experiment="LA_03_RF_MAPPING", run_name="D-SUP-01 representation ablation",
            plane="D", agent_id="D", subagent_id="worker/D-SUP-01",
            objective=("RF embedding signal 이 interaction semantics 인가 business/domain "
                       "semantics 인가 (falsification)"),
            method=("BGE-M3 고정 + frozen prototype + FULL/CONTROL_ONLY/TOPIC_ONLY/"
                    "NO_BRAND_DOMAIN ablation + strata 분해"),
            dataset_grain=("target (in_mart==1), n=56 / strata FUNCTIONAL 27·UNDETERMINED 26·"
                           "CORPORATE 3"),
            n_expected=56, n_observed=n_rows,
            hypothesis_id="H-SUP01-SIGNAL-SOURCE",
            competing_hypothesis="INTERACTION / DOMAIN / BOTH / INSEPARABLE",
            claim_kind="ANALYSIS", ticket_id="NONE", phase="I1", split="none",
            parent_run_id="NONE", result_path=OUT,
            model_or_rule_version="DSUP01_ABLATION_v1", seed=SEED,
            code_path=Path(__file__),
            notebook="DSUP01_representation_ablation.ipynb",
            extra_tags={"rq_id": "D-SUP-01", "child_id": "D-SUP-01",
                        "inquiry_kind": "DIRECTOR_SUPPLEMENTAL", "depends_on": "RQ-D14"},
            extra_params={"model": MODEL_HF, "prototype_sets": ",".join(PROTO_SETS),
                          "primary_prototype_set": PRIMARY_PROTO,
                          "representations": ",".join(REPS),
                          "primary_analysis_set": "complete_case",
                          "n_permutation": N_PERM, "n_stratified_draws": N_STRAT,
                          "n_bootstrap": N_BOOT,
                          "offline_models": "HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1"}) as run:
        m = {}
        u = stability["complete_case"][s]["unanimity"]
        m["stability.four_way_top1_unanimity"] = u["four_way_top1_unanimity"]
        m["stability.four_way_top2_set_unanimity"] = u["four_way_top2_set_unanimity"]
        m["stability.mean_distinct_pred_per_target"] = u["mean_distinct_predictions_per_target"]
        for pair, d in stability["complete_case"][s]["pairwise"].items():
            key = pair.replace("~", "_vs_").replace("NO_BRAND_DOMAIN", "NOBRAND")
            m[f"stability.top1_agreement.{key}"] = d["top1_agreement"]
            m[f"stability.top2_agreement.{key}"] = d["top2_set_agreement"]
        for r in REPS:
            rr = r.replace("NO_BRAND_DOMAIN", "NOBRAND")
            cc = per_config[f"{r}|{s}"]["complete_case"]
            m[f"rep.{rr}.macro_f1"] = cc["macro_f1"]
            m[f"rep.{rr}.prior_agreement_diagnostic"] = cc["prior_agreement"]
            m[f"rep.{rr}.top2_prior_containment"] = cc["top2_prior_containment"]
            m[f"rep.{rr}.class_coverage"] = cc["n_distinct_predicted_classes"]
            m[f"rep.{rr}.margin_median"] = cc["margin_median"]
            m[f"rep.{rr}.perm_p_macro_f1"] = per_config[f"{r}|{s}"][
                "permutation_null_complete_case"]["perm_p_macro_f1"]
            m[f"rep.{rr}.proto_three_way_unanimity"] = proto_stability[r]["three_way_unanimity"]
            m[f"rep.{rr}.proto_macro_f1_range"] = proto_stability[r]["macro_f1_range"]
        m["decision.d_ctrl_topic"] = d_ctrl_topic
        m["decision.d_ctrl_topic_ci_lo"] = ci_d[0]
        m["decision.d_ctrl_topic_ci_hi"] = ci_d[1]
        m["decision.drop_brand"] = drop_brand
        m["decision.drop_brand_ci_lo"] = ci_drop[0]
        m["decision.drop_brand_ci_hi"] = ci_drop[1]
        m["decision.pred_change_brand"] = pred_change_brand
        m["decision.agree_ctrl_topic"] = agree_ctrl_topic
        m["baseline.stratified_p95_macro_f1"] = strat_p95
        m["n.complete_case"] = float(len(idx_complete))
        m["n.brand_removal_flips"] = float(len(brand_flips))
        m["n.high_disagreement_targets"] = float(len(counterexamples))
        for st in strata_names:
            tag = {"FUNCTIONAL_LANDING": "FUNC", "UNDETERMINED": "UNDET",
                   "CORPORATE_OR_APP_LANDING": "CORP"}[st]
            for r in REPS:
                mm = by_strata[st]["per_representation"][r]["complete_case"]
                if mm.get("n", 0):
                    rr = r.replace("NO_BRAND_DOMAIN", "NOBRAND")
                    m[f"strata.{tag}.{rr}.prior_agreement"] = mm["prior_agreement"]
                    m[f"strata.{tag}.{rr}.macro_f1"] = mm["macro_f1"]
        mlflow.log_metrics({k: float(v) for k, v in m.items() if v == v})

        mlflow.log_text(prototype_texts, "prototype_definitions.txt")
        mlflow.log_text(removed_brand_tokens, "removed_brand_domain_tokens.txt")
        mlflow.log_text(json.dumps(REP_DEFINITION_TEXT, ensure_ascii=False, indent=1),
                        "representation_definitions.json")
        mlflow.log_text(json.dumps(PREREG, ensure_ascii=False, indent=1),
                        "preregistration.json")
        mlflow.log_text(json.dumps(hv, ensure_ascii=False, indent=1), "hypothesis_verdicts.json")
        mlflow.log_artifact(str(OUT))
        for f in sorted(FIGDIR.glob("DSUP01_*.png")):
            mlflow.log_artifact(str(f), artifact_path="figures")
        C.finish(verdict=result["verdict"], limitation=result["limitation"])
        run_id = run.info.run_id

    result["mlflow_run_id"] = run_id
    result["mlflow_experiment"] = "LA_03_RF_MAPPING"
    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")
    print("mlflow run_id:", run_id)
    return result


if __name__ == "__main__":
    r = main()
    print("verdict:", r["verdict"], r["hypothesis_verdicts"])
