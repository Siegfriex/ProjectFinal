"""D-RF2-C — Field-wise semantic ablation.

연구질문(RQ-D-RF-002 / child D-RF2-C)
    페이지의 semantic information 이 정확히 어느 evidence field 에 있는가?
    특히: "전체 페이지 텍스트(text_blob)보다 primary controls / accessibility text 가
    더 informative 한가?"

사전 등록 (코드 작성 시점 고정. 결과를 보고 prototype 문구·임계값·representation 목록을
수정하지 않는다. 수정이 필요하면 새 hypothesis_id + 새 run.)
-------------------------------------------------------------------------------
PRIMARY config      = model BAAI/bge-m3 × prototype set A(SSOT_DEF)
                      (bge-m3 = 셋 중 유일하게 8192 context 라 blob 을 자르지 않음)
비교의 축           = FIELD (representation). 모델 비교는 secondary 이며 모델별로 표를 분리한다.
prototype           = 모든 field 에 대해 **동일한 frozen 세트**를 쓴다. field 별로 문구를
                      바꾸지 않는다. 세트는 3개(A/B/C) 로 고정 — 안정성 측정용.
                      문장은 SSOT 00 §4 / SSOT 01 §5·§7 정의에서만 유도했고 D_TEXT_CORPUS 를
                      읽고 만들지 않았다. D-RF-001-C 에서 쓴 세트와 문자 단위로 동일하다.
판정 기준선         = stratified (macro F1 에서 majority 대비 lift 는 rigged — majority 는
                      6/7 class 에서 recall 0). most_frequent 도 보고하되 헤드라인은 stratified.
불확실성            = prior 셔플 permutation null (P=20000, 모든 config 공유 permutation).
target              = prior_archetype 은 gold label 이 아니라 prior. 지표명은 prior_agreement.
                      "accuracy" 라는 말을 쓰지 않는다.
seed                = 20260827
empty representation= 해당 field 가 빈 target 은 ABSTAIN 으로 두고 전체-56 분모에서 오답
                      처리한다(정보가 없으면 맞출 수 없다). 동시에 non-empty 부분집합의
                      조건부 수치도 자체 분모와 함께 보고한다.
가설
    H-C1  text_blob 전체가 최선이다
    H-C2  primary controls / accessibility text 가 text_blob 보다 더 informative 하다
    H-C3  field 간 차이가 prototype 문구 노이즈보다 작다
"""
from __future__ import annotations

import hashlib
import json
import re
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")
os.environ.setdefault("HF_DATASETS_OFFLINE", "1")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")

import numpy as np
import pandas as pd

RD = Path("/home/sieg/projects-wsl/ProjectFinal/.agent_worktrees/claude_d_research"
          "/research/landing_accessibility/research_d")
CORPUS_V2 = RD / "results" / "D_TEXT_CORPUS_v2.csv"
CORPUS_V1 = RD / "results" / "D_TEXT_CORPUS.csv"
OBS_V2 = RD / "results" / "D_OBSERVATION_TABLE_v2.csv"
OUT_JSON = RD / "results" / "RF2_C_field_ablation.json"
FIGDIR = RD / "figures"
SEED = 20260827
N_PERM = 20000
N_MC = 20000
KST = timezone(timedelta(hours=9))

ARCHETYPES = ["QUERY", "CONTENT_OPEN", "ITEM_DETAIL", "PLACE_LOOKUP",
              "COMMUNICATION_ENTRY", "FINANCIAL_ACTION_ENTRY", "UTILITY_ENTRY"]
KT = len(ARCHETYPES)          # true classes
KP = KT + 1                   # + ABSTAIN(=7) as a prediction-only class
A2I = {a: i for i, a in enumerate(ARCHETYPES)}

# ---------------------------------------------------------------- prototypes
# D-RF-001-C 와 문자 단위로 동일한 frozen 세트. field 별로 바꾸지 않는다.
# Set A — SSOT 01 §5 Stage-3 branch 정의(질문 + Region + Endpoint)의 축약형.
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
# Set B — 같은 SSOT 정의를 1인칭 사용자 행동 서술로 다시 쓴 것. 어휘 register 를 크게 바꾼다.
PROTO_USER_BEHAVIOR = {
    "QUERY": "나는 궁금한 것을 검색창에 입력하고 검색 버튼을 눌러 결과 목록을 본다.",
    "CONTENT_OPEN": "나는 목록에서 기사나 영상 하나를 골라 눌러서 읽거나 본다.",
    "ITEM_DETAIL": "나는 사고 싶은 물건 하나를 눌러 상세 화면에서 가격과 정보를 확인한다.",
    "PLACE_LOOKUP": "나는 가려는 장소를 찾아보고 그 장소의 위치와 상세 정보를 확인한다.",
    "COMMUNICATION_ENTRY": "나는 다른 사람이 올린 글이나 메시지를 보러 대화 공간에 들어간다.",
    "FINANCIAL_ACTION_ENTRY": "나는 은행이나 카드 업무를 시작하려고 로그인 화면까지 들어간다.",
    "UTILITY_ENTRY": "나는 필요한 기능 하나를 열어서 바로 쓸 수 있는 상태까지 간다.",
}
# Set C — SSOT 00 §4 archetype 이름 자체의 최소 gloss. 문장이 아니라 라벨에 가깝다.
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
PROTO_PROVENANCE = (
    "SSOT 00 §4 archetype 목록과 SSOT 01 §5 Stage-3 branch 정의문 / §7 Prototype texts 조항에서만 "
    "유도했다. D_TEXT_CORPUS 의 내용을 읽고 문구를 맞추지 않았다. D-RF-001-C 의 세트와 동일하며 "
    "이 run 에서 문구를 수정하지 않았다.")

MODELS = {
    "bge-m3": dict(hf="BAAI/bge-m3", batch=8, doc_prefix="", proto_prefix=""),
    "e5-small": dict(hf="intfloat/multilingual-e5-small", batch=32,
                     # e5 공식 규약: 비대칭이면 문서 "passage: ", 질의 "query: ".
                     # prototype=query, page=passage 로 두는 asymmetric 배치를 지켰다.
                     doc_prefix="passage: ", proto_prefix="query: "),
    "minilm": dict(hf="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
                   batch=32, doc_prefix="", proto_prefix=""),
}
PRIMARY_MODEL, PRIMARY_PROTO = "bge-m3", "A_SSOT_DEF"

# ---------------------------------------------------------------- field defs
BASE_FIELDS = ["title", "meta_description", "headings", "landmarks", "nav_links",
               "buttons", "aria_labels", "placeholders", "form_labels", "input_names",
               "card_texts", "url_tokens"]

SINGLE = {f: [f] for f in BASE_FIELDS}
COMBOS = {
    # 과제 지정 조합
    "first_screen_interaction": ["buttons", "aria_labels", "placeholders"],
    # accessibility text = accessible name 계열만
    "accessibility_text": ["aria_labels", "form_labels", "placeholders", "input_names"],
    # primary controls = 조작 가능한 표면 전체
    "primary_controls": ["buttons", "aria_labels", "form_labels", "placeholders",
                         "input_names"],
    # 정체성 계열 (브랜드/도메인)
    "identity": ["title", "meta_description", "url_tokens"],
    # 구조 계열
    "structure": ["title", "headings", "landmarks"],
    # 본문/콘텐츠 계열
    "content_body": ["headings", "card_texts"],
    # 내비게이션 표면
    "nav_surface": ["landmarks", "nav_links"],
    # SSOT 01 §7 Text representation 조항 그대로
    "ssot7_bundle": ["title", "headings", "landmarks", "aria_labels", "buttons",
                     "form_labels", "card_texts", "url_tokens"],
    # controls + 정체성 (production 후보)
    "controls_plus_identity": ["title", "url_tokens", "buttons", "aria_labels",
                               "form_labels", "placeholders", "input_names"],
}
CONTROL = {"text_blob__ALL": list(BASE_FIELDS)}          # 대조군 = 12 field 전체
LOO = {f"blob_minus__{f}": [x for x in BASE_FIELDS if x != f] for f in BASE_FIELDS}
REPS: dict[str, list[str]] = {**SINGLE, **COMBOS, **CONTROL, **LOO}
REP_GROUP = ({k: "single" for k in SINGLE} | {k: "combo" for k in COMBOS}
             | {k: "control" for k in CONTROL} | {k: "loo" for k in LOO})


def build_rep(df: pd.DataFrame, fields: list[str]) -> list[str]:
    """text_blob 과 동일한 결합 규약(' \\n ' join, 빈 필드는 생략)을 그대로 쓴다."""
    cols = [df[f].fillna("").astype(str).str.strip() for f in fields]
    out = []
    for i in range(len(df)):
        parts = [c.iloc[i] for c in cols if c.iloc[i]]
        out.append(" \n ".join(parts))
    return out



# ---------------------------------------------------------------- post-hoc
# POST-HOC / EXPLORATORY (사전 등록 아님, 결과를 본 뒤 추가한 confound 진단).
# prototype 문구도 임계값도 바꾸지 않는다. 새 표현(brand-masked)을 하나 더 볼 뿐이다.
# 동기: prior_archetype 은 business domain prior 에서 왔고 business domain 은 service
# identity 에서 왔다. title 이 이기는 것이 "상호작용 의미" 때문인지 "브랜드 식별" 때문인지
# 분리하지 않으면 순환이다.
STOP_HOST = {"www", "com", "co", "kr", "net", "org", "m", "mobile", "go", "or", "https", "http"}


def brand_terms(service: str, url: str) -> list[str]:
    """service 명과 URL host 토큰에서 브랜드 식별 문자열을 만든다."""
    out = set()
    service = service if isinstance(service, str) else ""
    url = url if isinstance(url, str) else ""
    sv = service.strip()
    if len(sv) >= 2:
        out.add(sv.lower())
        out.add(sv.replace(" ", "").lower())
        for w in sv.split():
            if len(w) >= 2:
                out.add(w.lower())
    host = re.sub(r"^https?://", "", (url or "")).split("/")[0]
    for t in re.split(r"[.\-]", host):
        t = t.strip().lower()
        if len(t) >= 2 and t not in STOP_HOST:
            out.add(t)
    return sorted(out, key=len, reverse=True)


def mask_brand(text: str, terms: list[str]) -> str:
    low = text
    for t in terms:
        low = re.sub(re.escape(t), " ", low, flags=re.IGNORECASE)
    return re.sub(r"[ \t]{2,}", " ", low).strip()


# ---------------------------------------------------------------- statistics
def wilson(k: int, n: int, z: float = 1.959963985) -> tuple[float, float]:
    if n == 0:
        return (float("nan"), float("nan"))
    p = k / n
    d = 1 + z * z / n
    c = p + z * z / (2 * n)
    h = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return (float((c - h) / d), float((c + h) / d))


def macro_f1_codes(y: np.ndarray, yhat: np.ndarray) -> float:
    """y in 0..6, yhat in 0..7 (7=ABSTAIN). ABSTAIN 은 어떤 class 의 tp/fp 도 되지 않고
    해당 true class 의 fn 으로만 잡힌다."""
    cm = np.bincount(y * KP + yhat, minlength=KT * KP).reshape(KT, KP)
    tp = np.diag(cm[:, :KT]).astype(float)
    fp = cm[:, :KT].sum(0) - tp
    fn = cm.sum(1) - tp
    pr = np.where(tp + fp > 0, tp / np.maximum(tp + fp, 1e-12), 0.0)
    rc = np.where(tp + fn > 0, tp / np.maximum(tp + fn, 1e-12), 0.0)
    f = np.where(pr + rc > 0, 2 * pr * rc / np.maximum(pr + rc, 1e-12), 0.0)
    return float(f.mean())


def macro_f1_batch(Y: np.ndarray, yhat: np.ndarray) -> np.ndarray:
    """Y (P,n) 참값 여러 벌 × 고정 예측 yhat (n,) → macro F1 (P,)."""
    P, n = Y.shape
    idx = Y * KP + yhat[None, :]
    off = (np.arange(P) * (KT * KP))[:, None]
    cm = np.bincount((idx + off).ravel(), minlength=P * KT * KP).reshape(P, KT, KP)
    tp = np.einsum("pii->pi", cm[:, :, :KT]).astype(float)
    fp = cm[:, :, :KT].sum(1) - tp
    fn = cm.sum(2) - tp
    pr = np.where(tp + fp > 0, tp / np.maximum(tp + fp, 1e-12), 0.0)
    rc = np.where(tp + fn > 0, tp / np.maximum(tp + fn, 1e-12), 0.0)
    f = np.where(pr + rc > 0, 2 * pr * rc / np.maximum(pr + rc, 1e-12), 0.0)
    return f.mean(1)


def macro_f1_batch_pred(y: np.ndarray, YH: np.ndarray) -> np.ndarray:
    """고정 참값 y (n,) × 예측 여러 벌 YH (P,n) → macro F1 (P,)."""
    P, n = YH.shape
    idx = y[None, :] * KP + YH
    off = (np.arange(P) * (KT * KP))[:, None]
    cm = np.bincount((idx + off).ravel(), minlength=P * KT * KP).reshape(P, KT, KP)
    tp = np.einsum("pii->pi", cm[:, :, :KT]).astype(float)
    fp = cm[:, :, :KT].sum(1) - tp
    fn = cm.sum(2) - tp
    pr = np.where(tp + fp > 0, tp / np.maximum(tp + fp, 1e-12), 0.0)
    rc = np.where(tp + fn > 0, tp / np.maximum(tp + fn, 1e-12), 0.0)
    f = np.where(pr + rc > 0, 2 * pr * rc / np.maximum(pr + rc, 1e-12), 0.0)
    return f.mean(1)


def per_class(y: np.ndarray, yhat: np.ndarray) -> dict:
    cm = np.bincount(y * KP + yhat, minlength=KT * KP).reshape(KT, KP)
    out = {}
    for i, a in enumerate(ARCHETYPES):
        tp = int(cm[i, i]); fp = int(cm[:, i].sum() - tp); fn = int(cm[i].sum() - tp)
        pr = tp / (tp + fp) if tp + fp else 0.0
        rc = tp / (tp + fn) if tp + fn else 0.0
        lo, hi = wilson(tp, int(cm[i].sum()))
        out[a] = {"n": int(cm[i].sum()), "tp": tp, "precision": round(pr, 4),
                  "recall": round(rc, 4),
                  "f1": round(2 * pr * rc / (pr + rc), 4) if pr + rc else 0.0,
                  "recall_wilson95": [round(lo, 4), round(hi, 4)]}
    return out


# ---------------------------------------------------------------- embedding
def load_model(key: str):
    from sentence_transformers import SentenceTransformer
    import torch
    dev = "cuda" if torch.cuda.is_available() else "cpu"
    m = SentenceTransformer(MODELS[key]["hf"], device=dev)
    return m


def encode(model, texts: list[str], prefix: str, batch: int) -> np.ndarray:
    v = model.encode([prefix + t for t in texts], batch_size=batch,
                     normalize_embeddings=True, show_progress_bar=False,
                     convert_to_numpy=True)
    return v.astype(np.float32)


def token_stats(model, texts: list[str], prefix: str) -> dict:
    tk = model.tokenizer
    ms = int(model.max_seq_length)
    ns = []
    for t in texts:
        if not t:
            ns.append(0)
            continue
        ns.append(len(tk(prefix + t, add_special_tokens=True)["input_ids"]))
    ns = np.array(ns)
    nz = ns[ns > 0]
    return {"model_max_seq": ms,
            "tokens_median": float(np.median(nz)) if len(nz) else 0.0,
            "tokens_p90": float(np.percentile(nz, 90)) if len(nz) else 0.0,
            "tokens_max": int(nz.max()) if len(nz) else 0,
            "n_truncated": int((ns > ms).sum()),
            "truncation_rate": round(float((ns > ms).sum() / len(ns)), 4)}


# ---------------------------------------------------------------- core eval
def evaluate(sim: np.ndarray, empty: np.ndarray, y: np.ndarray) -> dict:
    """sim (n,7) 코사인 유사도. empty (n,) bool. y (n,) 참 prior 코드."""
    n = len(y)
    order = np.argsort(-sim, axis=1)
    top1 = order[:, 0]
    margin = sim[np.arange(n), order[:, 0]] - sim[np.arange(n), order[:, 1]]
    yhat = np.where(empty, KT, top1).astype(int)          # KT = ABSTAIN
    hit = (yhat == y)
    k = int(hit.sum())
    lo, hi = wilson(k, n)
    ne = ~empty
    k_ne = int(hit[ne].sum()); n_ne = int(ne.sum())
    lo2, hi2 = wilson(k_ne, n_ne)
    mg = margin[ne] if n_ne else np.array([0.0])
    return {
        "n_all": n, "n_empty": int(empty.sum()), "n_nonempty": n_ne,
        "prior_agreement_all56": round(k / n, 4), "n_agree_all56": k,
        "prior_agreement_all56_wilson95": [round(lo, 4), round(hi, 4)],
        "prior_agreement_nonempty": round(k_ne / n_ne, 4) if n_ne else None,
        "n_agree_nonempty": k_ne,
        "prior_agreement_nonempty_wilson95": [round(lo2, 4), round(hi2, 4)],
        "macro_f1": round(macro_f1_codes(y, yhat), 4),
        "margin_median": round(float(np.median(mg)), 5),
        "margin_p25": round(float(np.percentile(mg, 25)), 5),
        "margin_p75": round(float(np.percentile(mg, 75)), 5),
        "margin_mean": round(float(np.mean(mg)), 5),
        "pred_class_counts": {ARCHETYPES[i]: int((yhat == i).sum()) for i in range(KT)}
                             | {"ABSTAIN": int((yhat == KT).sum())},
        "_yhat": yhat.tolist(),
    }


def main() -> int:
    rng = np.random.default_rng(SEED)
    df2 = pd.read_csv(CORPUS_V2)
    assert len(df2) == 56, len(df2)
    y = np.array([A2I[a] for a in df2["prior_archetype"]], dtype=int)
    n = len(y)
    cls_counts = {a: int((y == i).sum()) for i, a in enumerate(ARCHETYPES)}

    # ---- baselines -------------------------------------------------------
    prior_p = np.array([cls_counts[a] for a in ARCHETYPES], dtype=float) / n
    mf_code = int(np.argmax(prior_p))
    yhat_mf = np.full(n, mf_code)
    base_mf = {"prior_agreement": round(float((yhat_mf == y).mean()), 4),
               "macro_f1": round(macro_f1_codes(y, yhat_mf), 4),
               "predicts": ARCHETYPES[mf_code],
               "note": "majority 는 6/7 class 에서 recall 0 이므로 macro F1 lift 의 판정 기준선이 "
                       "될 수 없다. 참고용으로만 보고한다."}
    YH = rng.choice(KT, size=(N_MC, n), p=prior_p)
    strat_f1 = macro_f1_batch_pred(y, YH)
    strat_agr = (YH == y[None, :]).mean(1)
    base_strat = {"n_draws": N_MC,
                  "macro_f1_mean": round(float(strat_f1.mean()), 4),
                  "macro_f1_p50": round(float(np.percentile(strat_f1, 50)), 4),
                  "macro_f1_p95": round(float(np.percentile(strat_f1, 95)), 4),
                  "macro_f1_p99": round(float(np.percentile(strat_f1, 99)), 4),
                  "prior_agreement_mean": round(float(strat_agr.mean()), 4),
                  "prior_agreement_p95": round(float(np.percentile(strat_agr, 95)), 4)}

    # ---- shared permutations (prior shuffle) ------------------------------
    PERM = np.stack([rng.permutation(y) for _ in range(N_PERM)])

    # ---- representations -------------------------------------------------
    reps_v2 = {name: build_rep(df2, fs) for name, fs in REPS.items()}
    rep_meta = {}
    for name, txts in reps_v2.items():
        wl = np.array([len(t.split()) for t in txts])
        nz = wl[wl > 0]
        rep_meta[name] = {
            "fields": REPS[name], "group": REP_GROUP[name],
            "n_empty": int((wl == 0).sum()),
            "missingness_rate": round(float((wl == 0).sum() / n), 4),
            "words_median": float(np.median(nz)) if len(nz) else 0.0,
            "words_p90": float(np.percentile(nz, 90)) if len(nz) else 0.0,
            "words_max": int(nz.max()) if len(nz) else 0,
            "chars_median": float(np.median([len(t) for t in txts])),
        }

    # ---- grid ------------------------------------------------------------
    grid: dict = {}
    tokstats: dict = {}
    for mkey, mcfg in MODELS.items():
        print(f"[model] {mkey} loading …", flush=True)
        model = load_model(mkey)
        P = {sname: encode(model, [pset[a] for a in ARCHETYPES],
                           mcfg["proto_prefix"], mcfg["batch"])
             for sname, pset in PROTO_SETS.items()}
        grid[mkey] = {s: {} for s in PROTO_SETS}
        tokstats[mkey] = {}
        for rname, txts in reps_v2.items():
            empty = np.array([not t.strip() for t in txts])
            tokstats[mkey][rname] = token_stats(model, txts, mcfg["doc_prefix"])
            enc_idx = np.where(~empty)[0]
            D = np.zeros((n, P["A_SSOT_DEF"].shape[1]), dtype=np.float32)
            if len(enc_idx):
                D[enc_idx] = encode(model, [txts[i] for i in enc_idx],
                                    mcfg["doc_prefix"], mcfg["batch"])
            for sname in PROTO_SETS:
                sim = D @ P[sname].T
                r = evaluate(sim, empty, y)
                yhat = np.array(r.pop("_yhat"))
                null = macro_f1_batch(PERM, yhat)
                nullagr = (PERM == yhat[None, :]).mean(1)
                r["perm_null"] = {
                    "n_perm": N_PERM,
                    "macro_f1_mean": round(float(null.mean()), 4),
                    "macro_f1_p95": round(float(np.percentile(null, 95)), 4),
                    "macro_f1_p99": round(float(np.percentile(null, 99)), 4),
                    "macro_f1_p_value": round(float((null >= r["macro_f1"]).mean()), 5),
                    "macro_f1_z": round(float((r["macro_f1"] - null.mean())
                                              / max(null.std(), 1e-9)), 3),
                    "prior_agreement_mean": round(float(nullagr.mean()), 4),
                    "prior_agreement_p95": round(float(np.percentile(nullagr, 95)), 4),
                    "prior_agreement_p_value": round(
                        float((nullagr >= r["prior_agreement_all56"]).mean()), 5),
                }
                r["beats_stratified_p95_macro_f1"] = bool(
                    r["macro_f1"] > base_strat["macro_f1_p95"])
                r["yhat"] = [ARCHETYPES[c] if c < KT else "ABSTAIN" for c in yhat]
                if (mkey, sname) == (PRIMARY_MODEL, PRIMARY_PROTO):
                    r["per_class"] = per_class(y, yhat)
                grid[mkey][sname][rname] = r
            print(f"  {mkey:9s} {rname:28s} "
                  f"f1(A)={grid[mkey]['A_SSOT_DEF'][rname]['macro_f1']:.3f}", flush=True)
        del model
        import torch, gc
        gc.collect(); torch.cuda.empty_cache()

    # ---- ablation deltas (vs text_blob__ALL, per model × proto set) --------
    ablation = {}
    for mkey in MODELS:
        ablation[mkey] = {}
        for sname in PROTO_SETS:
            ref = grid[mkey][sname]["text_blob__ALL"]
            rows = {}
            for f in BASE_FIELDS:
                loo = grid[mkey][sname][f"blob_minus__{f}"]
                sg = grid[mkey][sname][f]
                rows[f] = {
                    "blob_macro_f1": ref["macro_f1"],
                    "loo_macro_f1": loo["macro_f1"],
                    "delta_macro_f1_removing_field": round(
                        ref["macro_f1"] - loo["macro_f1"], 4),
                    "blob_prior_agreement": ref["prior_agreement_all56"],
                    "loo_prior_agreement": loo["prior_agreement_all56"],
                    "delta_prior_agreement_removing_field": round(
                        ref["prior_agreement_all56"] - loo["prior_agreement_all56"], 4),
                    "field_alone_macro_f1": sg["macro_f1"],
                    "field_alone_prior_agreement": sg["prior_agreement_all56"],
                    "verdict": ("HELPS" if ref["macro_f1"] - loo["macro_f1"] > 0.02 else
                                "NOISE" if ref["macro_f1"] - loo["macro_f1"] < -0.02
                                else "NEUTRAL"),
                }
            ablation[mkey][sname] = rows

    # ---- prototype stability & field-vs-prototype variance -----------------
    stability = {}
    for mkey in MODELS:
        per_rep = {}
        for rname in REPS:
            vals = [grid[mkey][s][rname]["macro_f1"] for s in PROTO_SETS]
            agr = [grid[mkey][s][rname]["prior_agreement_all56"] for s in PROTO_SETS]
            per_rep[rname] = {
                "macro_f1_by_set": {s: grid[mkey][s][rname]["macro_f1"] for s in PROTO_SETS},
                "macro_f1_min": round(min(vals), 4), "macro_f1_max": round(max(vals), 4),
                "macro_f1_range": round(max(vals) - min(vals), 4),
                "macro_f1_sd": round(float(np.std(vals, ddof=1)), 4),
                "prior_agreement_range": round(max(agr) - min(agr), 4),
                "verdict_flip_vs_stratified_p95": bool(
                    len({v > base_strat["macro_f1_p95"] for v in vals}) > 1),
            }
        # between-field variance vs between-prototype-set variance (H-C3)
        M = np.array([[grid[mkey][s][r]["macro_f1"] for s in PROTO_SETS] for r in REPS])
        field_means = M.mean(1)
        set_means = M.mean(0)
        # 순위 안정성: 세트 간 field 순위 Spearman
        from itertools import combinations
        def spearman(a, b):
            ra = np.argsort(np.argsort(a)); rb = np.argsort(np.argsort(b))
            ra = ra - ra.mean(); rb = rb - rb.mean()
            return float((ra * rb).sum() / np.sqrt((ra ** 2).sum() * (rb ** 2).sum()))
        sl = list(PROTO_SETS)
        rho = {f"{sl[i]}~{sl[j]}": round(spearman(M[:, i], M[:, j]), 4)
               for i, j in combinations(range(len(sl)), 2)}
        stability[mkey] = {
            "per_representation": per_rep,
            "between_field_sd_of_mean_macro_f1": round(float(np.std(field_means, ddof=1)), 4),
            "between_prototype_set_sd_of_mean_macro_f1": round(
                float(np.std(set_means, ddof=1)), 4),
            "between_field_range": round(float(field_means.max() - field_means.min()), 4),
            "between_prototype_set_range": round(float(set_means.max() - set_means.min()), 4),
            "field_rank_spearman_between_sets": rho,
            "n_representations": len(REPS),
        }

    # ---- field ranking (primary) ------------------------------------------
    prim = grid[PRIMARY_MODEL][PRIMARY_PROTO]
    ranking = sorted(
        [{"representation": r, "group": REP_GROUP[r], "fields": REPS[r],
          "macro_f1": prim[r]["macro_f1"],
          "prior_agreement_all56": prim[r]["prior_agreement_all56"],
          "n_agree_all56": prim[r]["n_agree_all56"],
          "prior_agreement_all56_wilson95": prim[r]["prior_agreement_all56_wilson95"],
          "prior_agreement_nonempty": prim[r]["prior_agreement_nonempty"],
          "n_nonempty": prim[r]["n_nonempty"], "n_empty": prim[r]["n_empty"],
          "margin_median": prim[r]["margin_median"],
          "perm_p_macro_f1": prim[r]["perm_null"]["macro_f1_p_value"],
          "beats_stratified_p95": prim[r]["beats_stratified_p95_macro_f1"],
          "tokens_median": tokstats[PRIMARY_MODEL][r]["tokens_median"],
          "truncation_rate": tokstats[PRIMARY_MODEL][r]["truncation_rate"],
          "stability_macro_f1_range":
              stability[PRIMARY_MODEL]["per_representation"][r]["macro_f1_range"]}
         for r in REPS if REP_GROUP[r] != "loo"],
        key=lambda d: -d["macro_f1"])

    # ---- v1 vs v2 (encoding fix) ------------------------------------------
    v1v2 = {"note": "v1 은 한글 인코딩이 깨져 있었다. 동일 코드·동일 prototype 으로 v1/v2 를 "
                    "PRIMARY 모델에서만 재계산해 인코딩 시정 효과를 격리한다."}
    if CORPUS_V1.exists():
        df1 = pd.read_csv(CORPUS_V1)
        common = ["title", "meta_description", "headings", "landmarks", "nav_links",
                  "buttons", "aria_labels", "placeholders", "form_labels",
                  "input_names", "card_texts", "url_tokens"]
        m = df1.set_index("wtg").reindex(df2["wtg"])
        changed = {}
        for f in common:
            a = m[f].fillna("").astype(str).values
            b = df2[f].fillna("").astype(str).values
            changed[f] = int((a != b).sum())
        v1v2["n_targets_with_changed_field"] = {
            "any_field": int(sum(1 for i in range(n)
                                 if any(str(m[f].fillna("").values[i]) != str(df2[f].fillna("").values[i])
                                        for f in common))),
            "per_field": changed}
        v1v2["blob_tokens_median_v1"] = float(df1["blob_tokens"].median())
        v1v2["blob_tokens_median_v2"] = float(df2["blob_tokens"].median())
        print("[v1] recomputing PRIMARY grid on v1 corpus …", flush=True)
        model = load_model(PRIMARY_MODEL)
        mcfg = MODELS[PRIMARY_MODEL]
        Pv = encode(model, [PROTO_SETS[PRIMARY_PROTO][a] for a in ARCHETYPES],
                    mcfg["proto_prefix"], mcfg["batch"])
        m2 = m.reset_index()
        v1rows = {}
        for rname, fs in REPS.items():
            if REP_GROUP[rname] == "loo":
                continue
            txts = build_rep(m2, fs)
            empty = np.array([not t.strip() for t in txts])
            D = np.zeros((n, Pv.shape[1]), dtype=np.float32)
            idx = np.where(~empty)[0]
            if len(idx):
                D[idx] = encode(model, [txts[i] for i in idx], mcfg["doc_prefix"], mcfg["batch"])
            r = evaluate(D @ Pv.T, empty, y)
            r.pop("_yhat")
            v1rows[rname] = {"macro_f1": r["macro_f1"],
                             "prior_agreement_all56": r["prior_agreement_all56"],
                             "n_agree_all56": r["n_agree_all56"]}
        v1v2["primary_v1"] = v1rows
        v1v2["primary_v2"] = {r: {"macro_f1": prim[r]["macro_f1"],
                                  "prior_agreement_all56": prim[r]["prior_agreement_all56"],
                                  "n_agree_all56": prim[r]["n_agree_all56"]}
                              for r in v1rows}
        v1v2["delta_v2_minus_v1"] = {
            r: {"macro_f1": round(prim[r]["macro_f1"] - v1rows[r]["macro_f1"], 4),
                "prior_agreement_all56": round(
                    prim[r]["prior_agreement_all56"] - v1rows[r]["prior_agreement_all56"], 4)}
            for r in v1rows}
        rank1 = sorted(v1rows, key=lambda r: -v1rows[r]["macro_f1"])
        rank2 = sorted(v1rows, key=lambda r: -prim[r]["macro_f1"])
        v1v2["top5_v1"] = rank1[:5]
        v1v2["top5_v2"] = rank2[:5]
        v1v2["rank_top1_changed"] = bool(rank1[0] != rank2[0])
        del model
        import torch, gc
        gc.collect(); torch.cuda.empty_cache()

    # ---- POST-HOC: brand-name masking confound diagnostic -------------------
    print("[post-hoc] brand-masked PRIMARY grid …", flush=True)
    terms = [brand_terms(df2["prior_service"].iloc[i], df2["prior_url"].iloc[i])
             for i in range(n)]
    dfm = df2.copy()
    for f in BASE_FIELDS:
        col = dfm[f].fillna("").astype(str)
        dfm[f] = [mask_brand(col.iloc[i], terms[i]) for i in range(n)]
    model = load_model(PRIMARY_MODEL)
    mcfg = MODELS[PRIMARY_MODEL]
    Pm = encode(model, [PROTO_SETS[PRIMARY_PROTO][a] for a in ARCHETYPES],
                mcfg["proto_prefix"], mcfg["batch"])
    masked = {}
    for rname, fs in REPS.items():
        if REP_GROUP[rname] == "loo":
            continue
        txts = build_rep(dfm, fs)
        empty = np.array([not t.strip() for t in txts])
        D = np.zeros((n, Pm.shape[1]), dtype=np.float32)
        idx = np.where(~empty)[0]
        if len(idx):
            D[idx] = encode(model, [txts[i] for i in idx], mcfg["doc_prefix"], mcfg["batch"])
        r = evaluate(D @ Pm.T, empty, y)
        r.pop("_yhat")
        masked[rname] = {"macro_f1": r["macro_f1"],
                         "prior_agreement_all56": r["prior_agreement_all56"],
                         "n_agree_all56": r["n_agree_all56"],
                         "n_empty": r["n_empty"],
                         "delta_macro_f1_vs_unmasked": round(
                             r["macro_f1"] - prim[rname]["macro_f1"], 4),
                         "delta_prior_agreement_vs_unmasked": round(
                             r["prior_agreement_all56"]
                             - prim[rname]["prior_agreement_all56"], 4)}
    del model
    import torch, gc
    gc.collect(); torch.cuda.empty_cache()
    brand_diag = {
        "status": "POST_HOC_EXPLORATORY — 사전 등록 항목이 아니다. prototype 문구/임계값은 "
                  "바뀌지 않았고 brand-masked 표현을 추가로 평가했을 뿐이다.",
        "rationale": ("prior_archetype 은 business domain prior 에서, business domain 은 "
                      "service identity 에서 왔다. title 이 이기는 것이 상호작용 의미 때문인지 "
                      "브랜드 식별 때문인지 분리하지 않으면 순환 논증이다."),
        "masking": "prior_service 문자열 변형 + URL host 토큰(www/com/co/kr 등 제외)을 "
                   "대소문자 무시로 모든 field 에서 제거",
        "n_targets": n,
        "example_terms": {str(df2["prior_service"].iloc[i]): terms[i] for i in range(3)},
        "results": masked,
        "brand_masked_ranking": sorted(masked, key=lambda r: -masked[r]["macro_f1"])[:8],
    }

    # ---- 반례 --------------------------------------------------------------
    blob_yh = prim["text_blob__ALL"]["yhat"]
    best_ctrl = max(["primary_controls", "first_screen_interaction", "accessibility_text"],
                    key=lambda r: prim[r]["macro_f1"])
    ctrl_yh = prim[best_ctrl]["yhat"]
    counter = []
    for i in range(n):
        t = ARCHETYPES[y[i]]
        if blob_yh[i] != t and ctrl_yh[i] == t:
            counter.append({"wtg": df2["wtg"].iloc[i], "service": df2["prior_service"].iloc[i],
                            "prior": t, "blob_pred": blob_yh[i],
                            f"{best_ctrl}_pred": ctrl_yh[i],
                            "type": "controls_right_blob_wrong"})
        elif blob_yh[i] == t and ctrl_yh[i] != t:
            counter.append({"wtg": df2["wtg"].iloc[i], "service": df2["prior_service"].iloc[i],
                            "prior": t, "blob_pred": blob_yh[i],
                            f"{best_ctrl}_pred": ctrl_yh[i],
                            "type": "blob_right_controls_wrong"})

    # ---- hypotheses --------------------------------------------------------
    blob_f1 = prim["text_blob__ALL"]["macro_f1"]
    top = ranking[0]
    ctrl_reps = ["primary_controls", "first_screen_interaction", "accessibility_text",
                 "buttons", "aria_labels", "form_labels"]
    best_ctrl_f1 = max(prim[r]["macro_f1"] for r in ctrl_reps)
    best_ctrl_name = max(ctrl_reps, key=lambda r: prim[r]["macro_f1"])
    st = stability[PRIMARY_MODEL]
    h1 = "SUPPORTED" if top["representation"] == "text_blob__ALL" else "REFUTED"
    h2 = ("SUPPORTED" if best_ctrl_f1 > blob_f1 + 0.05 else
          "PARTIALLY_SUPPORTED" if best_ctrl_f1 > blob_f1 else "NOT_SUPPORTED")
    h3 = ("SUPPORTED" if st["between_field_sd_of_mean_macro_f1"]
          < st["between_prototype_set_sd_of_mean_macro_f1"] else "REFUTED")
    if h2 in ("SUPPORTED", "PARTIALLY_SUPPORTED") and h3 == "REFUTED":
        verdict = "PARTIALLY_SUPPORTED"
    elif h3 == "SUPPORTED":
        verdict = "INCONCLUSIVE"
    else:
        verdict = "PARTIALLY_SUPPORTED"

    result = {
        "verdict": verdict,
        "child_id": "D-RF2-C", "rq_id": "RQ-D-RF-002",
        "hypothesis_id": "H-RF2-C-FIELD-INFORMATION",
        "generated_at_kst": datetime.now(KST).isoformat(),
        "seed": SEED, "n": n, "grain": "target (in_mart==1)",
        "class_counts": cls_counts,
        "target_note": ("prior_archetype 는 gold label 이 아니라 business-domain prior 다. "
                        "지표는 accuracy 가 아니라 prior_agreement 다."),
        "inputs": {
            "corpus_v2": str(CORPUS_V2),
            "corpus_v2_sha256": hashlib.sha256(CORPUS_V2.read_bytes()).hexdigest(),
            "corpus_v1": str(CORPUS_V1),
            "corpus_v1_sha256": (hashlib.sha256(CORPUS_V1.read_bytes()).hexdigest()
                                 if CORPUS_V1.exists() else "NONE"),
            "observation_table_v2": str(OBS_V2),
        },
        "firewall": ("holdout label · LABEL_SPLIT_FROZEN* · HOLDOUT_FOR_C* · RAW_L1~L4* · "
                     "PACKET_L* · *_OVERLAP* · PRECEDENCE_CONTESTED* · CALIBRATION_FOR_B* · "
                     "control/** · B/C target-level holdout error report 를 열지 않았다. "
                     "입력은 D 자신이 만든 D_TEXT_CORPUS_v2.csv / D_OBSERVATION_TABLE_v2.csv 뿐이다."),
        "prototype_sets": PROTO_SETS,
        "prototype_provenance": PROTO_PROVENANCE,
        "prototype_policy": "모든 field 에 동일한 frozen 세트를 적용했다. field 별로 문구를 바꾸지 않았다.",
        "models": {k: {"hf": v["hf"], "doc_prefix": v["doc_prefix"],
                       "proto_prefix": v["proto_prefix"]} for k, v in MODELS.items()},
        "e5_prefix_convention": ("intfloat/multilingual-e5-small 은 asymmetric 규약을 지켰다: "
                                 "페이지 텍스트에 'passage: ', prototype 에 'query: ' 를 붙였다. "
                                 "bge-m3 / MiniLM 은 prefix 를 쓰지 않는 것이 공식 규약이므로 붙이지 않았다."),
        "primary_config": {"model": PRIMARY_MODEL, "prototype_set": PRIMARY_PROTO,
                           "decision_baseline": "stratified"},
        "representation_definitions": rep_meta,
        "baselines": {"most_frequent": base_mf, "stratified": base_strat},
        "field_ranking_primary": ranking,
        "grid": grid,
        "token_stats": tokstats,
        "ablation_leave_one_field_out": ablation,
        "prototype_stability": stability,
        "v1_vs_v2_encoding_fix": v1v2,
        "posthoc_brand_masking": brand_diag,
        "counterexamples": counter,
        "counterexample_reference": {"blob": "text_blob__ALL", "controls": best_ctrl},
        "hypotheses": {
            "H-C1 text_blob 전체가 최선": h1,
            "H-C2 primary controls·accessibility text 가 더 informative": h2,
            "H-C3 field 간 차이가 prototype 노이즈보다 작다": h3,
        },
        "headline": {
            "best_representation": top["representation"],
            "best_macro_f1": top["macro_f1"],
            "best_prior_agreement_all56": top["prior_agreement_all56"],
            "text_blob_macro_f1": blob_f1,
            "text_blob_prior_agreement_all56": prim["text_blob__ALL"]["prior_agreement_all56"],
            "best_control_surface": best_ctrl_name,
            "best_control_macro_f1": best_ctrl_f1,
            "stratified_p95_macro_f1": base_strat["macro_f1_p95"],
        },
    }
    OUT_JSON.write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"wrote {OUT_JSON}  verdict={verdict}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
