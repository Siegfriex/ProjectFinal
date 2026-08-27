"""D-RF-001-C — SSOT prototype 문장 대비 sentence-embedding 유사도로 archetype prior 를 되찾는가.

SSOT 01 §7 "Prototype texts: 일곱 archetype 각각에 SSOT 정의를 짧은 prototype 문장으로 둔다" 를
그대로 조작화한 zero-shot 실험이다. 학습은 하지 않는다.

사전 등록(코드 작성 시점에 고정, 결과를 본 뒤 수정하지 않는다)
--------------------------------------------------------------
PRIMARY config      = model BAAI/bge-m3 × prototype set A(SSOT_DEF) × representation text_blob
                      (bge-m3 = 셋 중 유일하게 blob 전체를 자르지 않는 8192 context, set A =
                       SSOT DT §5 branch 정의문에서 가장 직접적으로 유도한 세트)
판정 기준선         = stratified (majority 대비 macro F1 lift 는 rigged 이므로 판정에 쓰지 않는다)
prototype set       = 3세트. 결과를 보고 4번째를 추가하지 않는다.
seed                = 20260827
target              = gold label 이 아니라 business-domain prior → 지표명은 prior_agreement

prototype 문장은 SSOT 00 §4 / SSOT 01 §5 의 archetype 정의에서만 유도했고 D_TEXT_CORPUS 를
읽고 만들지 않았다.
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")
os.environ.setdefault("HF_DATASETS_OFFLINE", "1")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")

import numpy as np
import pandas as pd

RD = Path("/home/sieg/projects-wsl/ProjectFinal/.agent_worktrees/claude_d_research"
          "/research/landing_accessibility/research_d")
CORPUS = RD / "results" / "D_TEXT_CORPUS.csv"
OUT_JSON = RD / "results" / "RF001_C_embedding.json"
FIGDIR = RD / "figures"
SEED = 20260827
N_MC = 20000
KST = timezone(timedelta(hours=9))

ARCHETYPES = ["QUERY", "CONTENT_OPEN", "ITEM_DETAIL", "PLACE_LOOKUP",
              "COMMUNICATION_ENTRY", "FINANCIAL_ACTION_ENTRY", "UTILITY_ENTRY"]

# ---------------------------------------------------------------- prototypes
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

MODELS = {
    "bge-m3": dict(hf="BAAI/bge-m3", batch=4,
                   # bge-m3 는 instruction prefix 를 쓰지 않는 것이 공식 규약이다.
                   doc_prefix="", proto_prefix="", max_seq=None),
    "e5-small": dict(hf="intfloat/multilingual-e5-small", batch=16,
                     # e5 규약: 비대칭 검색이면 문서 passage:, 질의 query:.
                     # prototype 을 query, page 를 passage 로 둔 asymmetric 이 PRIMARY.
                     doc_prefix="passage: ", proto_prefix="query: ", max_seq=None),
    "minilm": dict(hf="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2", batch=16,
                   doc_prefix="", proto_prefix="", max_seq=None),
}
PRIMARY = ("bge-m3", "A_SSOT_DEF")


# ---------------------------------------------------------------- statistics
def wilson(k: int, n: int, z: float = 1.959963985) -> tuple[float, float]:
    if n == 0:
        return (float("nan"), float("nan"))
    p = k / n
    d = 1 + z * z / n
    c = p + z * z / (2 * n)
    h = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return (float((c - h) / d), float((c + h) / d))


def macro_f1(y, yhat, classes=ARCHETYPES) -> float:
    fs = []
    for c in classes:
        tp = int(np.sum((y == c) & (yhat == c)))
        fp = int(np.sum((y != c) & (yhat == c)))
        fn = int(np.sum((y == c) & (yhat != c)))
        pr = tp / (tp + fp) if tp + fp else 0.0
        rc = tp / (tp + fn) if tp + fn else 0.0
        fs.append(2 * pr * rc / (pr + rc) if pr + rc else 0.0)
    return float(np.mean(fs))


def weighted_f1(y, yhat, classes=ARCHETYPES) -> float:
    tot, acc = len(y), 0.0
    for c in classes:
        sup = int(np.sum(y == c))
        if not sup:
            continue
        tp = int(np.sum((y == c) & (yhat == c)))
        fp = int(np.sum((y != c) & (yhat == c)))
        fn = sup - tp
        pr = tp / (tp + fp) if tp + fp else 0.0
        rc = tp / sup
        f = 2 * pr * rc / (pr + rc) if pr + rc else 0.0
        acc += f * sup
    return float(acc / tot)


def per_class(y, yhat, classes=ARCHETYPES) -> dict:
    out = {}
    for c in classes:
        sup = int(np.sum(y == c))
        tp = int(np.sum((y == c) & (yhat == c)))
        fp = int(np.sum((y != c) & (yhat == c)))
        fn = sup - tp
        npred = tp + fp
        pr = tp / npred if npred else 0.0
        rc = tp / sup if sup else 0.0
        out[c] = {
            "support": sup, "n_predicted": npred, "tp": tp, "fp": fp, "fn": fn,
            "recall": rc, "recall_wilson95": list(wilson(tp, sup)) if sup else [None, None],
            "recall_fraction": f"{tp}/{sup}",
            "precision": pr,
            "precision_wilson95": list(wilson(tp, npred)) if npred else [None, None],
            "precision_fraction": f"{tp}/{npred}" if npred else "0/0",
            "f1": (2 * pr * rc / (pr + rc)) if pr + rc else 0.0,
        }
    return out


def confusion(y, yhat, classes=ARCHETYPES) -> list[list[int]]:
    return [[int(np.sum((y == a) & (yhat == b))) for b in classes] for a in classes]


def stratified_null(y, rng, n=N_MC) -> dict:
    """계층 무작위 예측기: 관측 class marginal 에서 예측을 뽑는다. 판정 기준선."""
    classes, counts = np.unique(y, return_counts=True)
    p = counts / counts.sum()
    accs, f1s = np.empty(n), np.empty(n)
    for i in range(n):
        yhat = rng.choice(classes, size=len(y), p=p)
        accs[i] = float(np.mean(yhat == y))
        f1s[i] = macro_f1(y, yhat)
    return {"prior_agreement_mean": float(accs.mean()), "prior_agreement_sd": float(accs.std(ddof=1)),
            "prior_agreement_p95": float(np.percentile(accs, 95)),
            "prior_agreement_ci95": [float(np.percentile(accs, 2.5)), float(np.percentile(accs, 97.5))],
            "macro_f1_mean": float(f1s.mean()), "macro_f1_sd": float(f1s.std(ddof=1)),
            "macro_f1_p95": float(np.percentile(f1s, 95)),
            "macro_f1_ci95": [float(np.percentile(f1s, 2.5)), float(np.percentile(f1s, 97.5))],
            "n_draws": n, "_acc": accs, "_f1": f1s}


def perm_null(y, yhat, rng, n=N_MC, strata=None) -> dict:
    """라벨 순열 검정. strata 가 주어지면 층 내에서만 섞어 그 층 변수를 통제한다."""
    y = np.asarray(y)
    accs, f1s = np.empty(n), np.empty(n)
    idx_by_stratum = None
    if strata is not None:
        strata = np.asarray(strata)
        idx_by_stratum = [np.where(strata == s)[0] for s in np.unique(strata)]
    for i in range(n):
        if idx_by_stratum is None:
            yp = rng.permutation(y)
        else:
            yp = y.copy()
            for idx in idx_by_stratum:
                yp[idx] = rng.permutation(y[idx])
        accs[i] = float(np.mean(yhat == yp))
        f1s[i] = macro_f1(yp, yhat)
    return {"acc": accs, "f1": f1s}


def pval(null: np.ndarray, obs: float) -> float:
    """상측 검정. (초과 이상 개수 + 1) / (n + 1)."""
    return float((np.sum(null >= obs) + 1) / (len(null) + 1))


def spearman(a, b) -> tuple[float, float]:
    """rho 와 근사 양측 p (t 근사). scipy 없이 계산."""
    a, b = np.asarray(a, float), np.asarray(b, float)
    n = len(a)
    ra, rb = pd.Series(a).rank().values, pd.Series(b).rank().values
    ra, rb = ra - ra.mean(), rb - rb.mean()
    rho = float((ra @ rb) / np.sqrt((ra @ ra) * (rb @ rb)))
    if abs(rho) >= 1 or n < 4:
        return rho, 0.0
    t = rho * np.sqrt((n - 2) / (1 - rho * rho))
    from math import erf, sqrt
    # t(n-2) 를 정규로 근사 (n=56 에서 충분).
    p = 2 * (1 - 0.5 * (1 + erf(abs(t) / sqrt(2))))
    return rho, float(p)


def mannwhitney(x, y) -> dict:
    """U, rank-biserial, 정규근사 양측 p. tie 보정 포함."""
    x, y = np.asarray(x, float), np.asarray(y, float)
    nx, ny = len(x), len(y)
    if nx == 0 or ny == 0:
        return {"U": None, "p_normal_approx": None, "rank_biserial": None, "n_x": nx, "n_y": ny}
    allv = np.concatenate([x, y])
    r = pd.Series(allv).rank().values
    Rx = r[:nx].sum()
    U = Rx - nx * (nx + 1) / 2
    mu = nx * ny / 2
    _, cnt = np.unique(allv, return_counts=True)
    tie = np.sum(cnt ** 3 - cnt)
    N = nx + ny
    var = nx * ny / 12 * ((N + 1) - tie / (N * (N - 1))) if N > 1 else 0.0
    from math import erf, sqrt
    z = (U - mu) / np.sqrt(var) if var > 0 else 0.0
    p = 2 * (1 - 0.5 * (1 + erf(abs(z) / sqrt(2))))
    return {"U": float(U), "z": float(z), "p_normal_approx": float(p),
            "rank_biserial": float(2 * U / (nx * ny) - 1), "n_x": nx, "n_y": ny}


def cohen_kappa(a, b) -> float:
    a, b = np.asarray(a), np.asarray(b)
    labs = sorted(set(a) | set(b))
    n = len(a)
    po = float(np.mean(a == b))
    pe = sum((np.sum(a == l) / n) * (np.sum(b == l) / n) for l in labs)
    return float((po - pe) / (1 - pe)) if pe < 1 else float("nan")


def margin_curve(margin, correct) -> list[dict]:
    """margin 임계별 coverage / prior_agreement. 임계를 고르지 않고 곡선만 낸다."""
    margin, correct = np.asarray(margin, float), np.asarray(correct, bool)
    n = len(margin)
    thrs = sorted(set(np.round(np.concatenate([[0.0], np.unique(margin)]), 6)))
    rows = []
    for t in thrs:
        m = margin >= t
        cov_n = int(m.sum())
        if cov_n == 0:
            continue
        k = int(correct[m].sum())
        lo, hi = wilson(k, cov_n)
        rows.append({"margin_threshold": float(t), "coverage_n": cov_n,
                     "coverage": cov_n / n, "abstain_n": n - cov_n,
                     "abstention_rate": (n - cov_n) / n,
                     "prior_agreement_covered": k / cov_n,
                     "prior_agreement_fraction": f"{k}/{cov_n}",
                     "wilson95": [lo, hi]})
    return rows


# ---------------------------------------------------------------- experiment
def encode_all(df: pd.DataFrame) -> dict:
    from sentence_transformers import SentenceTransformer
    import torch

    docs = df["text_blob"].fillna("").astype(str).tolist()
    store = {}
    for mname, cfg in MODELS.items():
        print(f"[encode] {mname} ({cfg['hf']})", flush=True)
        torch.manual_seed(SEED)
        m = SentenceTransformer(cfg["hf"], device="cuda" if torch.cuda.is_available() else "cpu")
        if cfg["max_seq"]:
            m.max_seq_length = cfg["max_seq"]
        info = {"max_seq_length": int(m.max_seq_length), "dim": int(m.get_sentence_embedding_dimension())}
        # 문서 subword 길이 (truncation 실태 기록)
        tok = m.tokenizer
        lens = [len(tok(d, add_special_tokens=True)["input_ids"]) for d in docs]
        info["doc_subword_len_median"] = float(np.median(lens))
        info["doc_subword_len_max"] = int(max(lens))
        info["n_docs_truncated"] = int(sum(1 for l in lens if l > m.max_seq_length))

        D = m.encode([cfg["doc_prefix"] + d for d in docs], batch_size=cfg["batch"],
                     normalize_embeddings=True, show_progress_bar=False,
                     convert_to_numpy=True).astype(np.float64)
        P = {}
        for sname, pset in PROTO_SETS.items():
            texts = [cfg["proto_prefix"] + pset[a] for a in ARCHETYPES]
            P[sname] = m.encode(texts, batch_size=8, normalize_embeddings=True,
                                show_progress_bar=False, convert_to_numpy=True).astype(np.float64)
        # e5 대칭 변형 (prefix 규약 민감도)
        alt = None
        if mname == "e5-small":
            Dq = m.encode(["query: " + d for d in docs], batch_size=cfg["batch"],
                          normalize_embeddings=True, show_progress_bar=False,
                          convert_to_numpy=True).astype(np.float64)
            Pq = {s: m.encode(["query: " + pset[a] for a in ARCHETYPES], batch_size=8,
                              normalize_embeddings=True, show_progress_bar=False,
                              convert_to_numpy=True).astype(np.float64)
                  for s, pset in PROTO_SETS.items()}
            alt = {"doc": Dq, "proto": Pq, "note": "symmetric query:/query: prefix"}
        store[mname] = {"doc": D, "proto": P, "info": info, "alt": alt}
        del m
        torch.cuda.empty_cache()
    return store


def score(D, P, y) -> dict:
    S = D @ P.T                                   # cosine (둘 다 L2 정규화)
    order = np.argsort(-S, axis=1)
    top1 = np.array([ARCHETYPES[i] for i in order[:, 0]])
    top2 = np.array([ARCHETYPES[i] for i in order[:, 1]])
    s1 = S[np.arange(len(S)), order[:, 0]]
    s2 = S[np.arange(len(S)), order[:, 1]]
    return {"sim": S, "top1": top1, "top2": top2, "top1_sim": s1, "top2_sim": s2,
            "margin": s1 - s2, "correct": top1 == y,
            "top2_hit": (top1 == y) | (top2 == y)}


def main() -> int:
    rng = np.random.default_rng(SEED)
    df = pd.read_csv(CORPUS)
    df = df.reset_index(drop=True)
    y = df["prior_archetype"].values.astype(object)
    n = len(df)
    toks = df["blob_tokens"].values.astype(float)
    assert set(y) <= set(ARCHETYPES), "출력이 7 archetype 밖으로 나갔다"

    # ---- 입력 품질 실사 (해석 제약으로 반드시 기록)
    dup = df["text_blob"].duplicated(keep=False)
    mojibake = df["text_blob"].fillna("").str.contains(r"[ì|ë|ê|í|¬|¹|½]{2,}", regex=True)
    url_only = toks <= 12
    quality = {
        "n_rows": int(n),
        "dom_found_n": int(df["dom_found"].sum()),
        "duplicate_blob_n": int(dup.sum()),
        "duplicate_blob_services": sorted(df.loc[dup, "prior_service"].tolist()),
        "mojibake_suspect_n": int(mojibake.sum()),
        "mojibake_services": sorted(df.loc[mojibake, "prior_service"].tolist()),
        "near_url_only_n(<=12 tokens)": int(url_only.sum()),
        "near_url_only_services": sorted(df.loc[url_only, "prior_service"].tolist()),
        "blob_tokens": {"min": float(toks.min()), "p25": float(np.percentile(toks, 25)),
                        "median": float(np.median(toks)), "p75": float(np.percentile(toks, 75)),
                        "max": float(toks.max()), "mean": float(toks.mean())},
    }

    # ---- 기준선
    maj = np.array(["ITEM_DETAIL"] * n, dtype=object)
    baselines = {
        "majority": {"rule": "always ITEM_DETAIL (n=26/56)",
                     "prior_agreement": float(np.mean(maj == y)),
                     "prior_agreement_fraction": f"{int(np.sum(maj == y))}/{n}",
                     "macro_f1": macro_f1(y, maj), "weighted_f1": weighted_f1(y, maj)},
    }
    strat = stratified_null(y, np.random.default_rng(SEED), N_MC)
    strat_acc, strat_f1 = strat.pop("_acc"), strat.pop("_f1")
    baselines["stratified"] = strat
    baselines["stratified"]["rule"] = ("관측 class marginal 에서 예측을 무작위 추출. "
                                       "판정 기준선(JUDGMENT BASELINE).")

    # ---- 인코딩 + 9 config
    store = encode_all(df)
    configs, preds = {}, {}
    for mname in MODELS:
        for sname in PROTO_SETS:
            r = score(store[mname]["doc"], store[mname]["proto"][sname], y)
            key = f"{mname}|{sname}"
            preds[key] = r
            pn = perm_null(y, r["top1"], np.random.default_rng(SEED + 1), N_MC)
            f1 = macro_f1(y, r["top1"])
            acc = float(np.mean(r["correct"]))
            k = int(r["correct"].sum())
            configs[key] = {
                "model": mname, "prototype_set": sname,
                "prior_agreement": acc, "prior_agreement_fraction": f"{k}/{n}",
                "prior_agreement_wilson95": list(wilson(k, n)),
                "macro_f1": f1, "weighted_f1": weighted_f1(y, r["top1"]),
                "top2_prior_agreement": float(np.mean(r["top2_hit"])),
                "top2_fraction": f"{int(r['top2_hit'].sum())}/{n}",
                "n_distinct_predicted_classes": int(len(set(r["top1"]))),
                "predicted_class_counts": {a: int(np.sum(r["top1"] == a)) for a in ARCHETYPES},
                "margin_median": float(np.median(r["margin"])),
                "margin_p10": float(np.percentile(r["margin"], 10)),
                "margin_p90": float(np.percentile(r["margin"], 90)),
                "top1_sim_median": float(np.median(r["top1_sim"])),
                "vs_stratified": {
                    "macro_f1_delta": f1 - strat["macro_f1_mean"],
                    "macro_f1_p_vs_stratified_predictor": pval(strat_f1, f1),
                    "macro_f1_gt_stratified_p95": bool(f1 > strat["macro_f1_p95"]),
                    "prior_agreement_delta": acc - strat["prior_agreement_mean"],
                    "prior_agreement_p_vs_stratified_predictor": pval(strat_acc, acc),
                },
                "vs_majority": {"macro_f1_delta": f1 - baselines["majority"]["macro_f1"],
                                "prior_agreement_delta": acc - baselines["majority"]["prior_agreement"]},
                "label_permutation_test": {"macro_f1_p": pval(pn["f1"], f1),
                                           "prior_agreement_p": pval(pn["acc"], acc),
                                           "macro_f1_null_mean": float(pn["f1"].mean()),
                                           "n_permutations": N_MC},
                "beats_judgment_baseline": bool(f1 > strat["macro_f1_p95"]),
            }

    # e5 prefix 규약 ablation
    e5alt = {}
    if store["e5-small"]["alt"]:
        for sname in PROTO_SETS:
            r = score(store["e5-small"]["alt"]["doc"], store["e5-small"]["alt"]["proto"][sname], y)
            e5alt[f"e5-small-symmetric|{sname}"] = {
                "prior_agreement": float(np.mean(r["correct"])),
                "prior_agreement_fraction": f"{int(r['correct'].sum())}/{n}",
                "macro_f1": macro_f1(y, r["top1"]),
                "delta_macro_f1_vs_asymmetric": macro_f1(y, r["top1"]) - configs[f"e5-small|{sname}"]["macro_f1"],
            }

    # ---- PRIMARY 상세
    pkey = f"{PRIMARY[0]}|{PRIMARY[1]}"
    pr = preds[pkey]
    primary = {
        "config": pkey, "preregistered": True,
        **{k: v for k, v in configs[pkey].items()},
        "per_class": per_class(y, pr["top1"]),
        "confusion_matrix": {"rows_true": ARCHETYPES, "cols_pred": ARCHETYPES,
                             "matrix": confusion(y, pr["top1"])},
        "margin_coverage_curve": margin_curve(pr["margin"], pr["correct"]),
        "threshold_declared": None,
        "threshold_note": ("SSOT 01 §7 은 threshold 를 independent label calibration split 에서 "
                           "정하라고 규정한다. 이 worker 는 gold label 과 holdout 에 접근할 수 없으므로 "
                           "임계를 선언하지 않고 곡선만 제출한다."),
    }

    # ---- H-C-prototype: prototype 문구 민감도
    proto_sens = {"per_model": {}, "pairwise_kappa": {}}
    for mname in MODELS:
        f1s = {s: configs[f"{mname}|{s}"]["macro_f1"] for s in PROTO_SETS}
        accs = {s: configs[f"{mname}|{s}"]["prior_agreement"] for s in PROTO_SETS}
        beats = {s: configs[f"{mname}|{s}"]["beats_judgment_baseline"] for s in PROTO_SETS}
        proto_sens["per_model"][mname] = {
            "macro_f1_by_set": f1s, "macro_f1_range": max(f1s.values()) - min(f1s.values()),
            "prior_agreement_by_set": accs,
            "prior_agreement_range": max(accs.values()) - min(accs.values()),
            "beats_stratified_p95_by_set": beats,
            "verdict_flips_across_sets": len(set(beats.values())) > 1,
        }
        for i, s1 in enumerate(PROTO_SETS):
            for s2 in list(PROTO_SETS)[i + 1:]:
                proto_sens["pairwise_kappa"][f"{mname}|{s1}~{s2}"] = {
                    "cohen_kappa": cohen_kappa(preds[f"{mname}|{s1}"]["top1"],
                                               preds[f"{mname}|{s2}"]["top1"]),
                    "raw_prediction_agreement": float(np.mean(
                        preds[f"{mname}|{s1}"]["top1"] == preds[f"{mname}|{s2}"]["top1"])),
                }
    allf1 = [configs[k]["macro_f1"] for k in configs]
    proto_sens["global"] = {
        "macro_f1_min": min(allf1), "macro_f1_max": max(allf1),
        "macro_f1_range_all_9_configs": max(allf1) - min(allf1),
        "n_configs_beating_stratified_p95": int(sum(configs[k]["beats_judgment_baseline"] for k in configs)),
        "n_configs": len(configs),
        "any_verdict_flip": any(proto_sens["per_model"][m]["verdict_flips_across_sets"] for m in MODELS),
    }

    # ---- H-C-length: 길이 교란
    tert = pd.qcut(pd.Series(toks), 3, labels=["T1_short", "T2_mid", "T3_long"], duplicates="drop")
    tert = np.asarray(tert.astype(str))
    length_tests = {"per_config": {}}
    for key, r in preds.items():
        rho_s, p_s = spearman(toks, r["top1_sim"])
        rho_m, p_m = spearman(toks, r["margin"])
        mw = mannwhitney(toks[r["correct"]], toks[~r["correct"]])
        f1 = configs[key]["macro_f1"]
        pn_len = perm_null(y, r["top1"], np.random.default_rng(SEED + 2), N_MC, strata=tert)
        tert_rows = {}
        for t in ["T1_short", "T2_mid", "T3_long"]:
            m = tert == t
            k = int(r["correct"][m].sum())
            tert_rows[t] = {"n": int(m.sum()), "prior_agreement": k / int(m.sum()),
                            "fraction": f"{k}/{int(m.sum())}",
                            "wilson95": list(wilson(k, int(m.sum()))),
                            "token_range": [float(toks[m].min()), float(toks[m].max())]}
        length_tests["per_config"][key] = {
            "spearman_tokens_vs_top1sim": {"rho": rho_s, "p_approx": p_s},
            "spearman_tokens_vs_margin": {"rho": rho_m, "p_approx": p_m},
            "tokens_correct_vs_incorrect_mannwhitney": mw,
            "tokens_median_correct": float(np.median(toks[r["correct"]])) if r["correct"].any() else None,
            "tokens_median_incorrect": float(np.median(toks[~r["correct"]])) if (~r["correct"]).any() else None,
            "prior_agreement_by_length_tertile": tert_rows,
            "length_stratified_permutation": {
                "macro_f1_p": pval(pn_len["f1"], f1),
                "macro_f1_null_mean": float(pn_len["f1"].mean()),
                "macro_f1_null_p95": float(np.percentile(pn_len["f1"], 95)),
                "signal_survives_length_control": bool(f1 > np.percentile(pn_len["f1"], 95)),
                "n_permutations": N_MC,
                "note": "길이 tertile 안에서만 라벨을 섞어 길이-라벨 연관을 보존한 귀무분포",
            },
        }

    # 길이만 쓰는 분류기 baseline (LOO nearest-class-mean on log tokens)
    lt = np.log1p(toks)
    loo = []
    for i in range(n):
        m = np.ones(n, bool); m[i] = False
        cls, best, bd = None, None, np.inf
        for c in ARCHETYPES:
            sel = m & (y == c)
            if not sel.any():
                continue
            d = abs(lt[i] - lt[sel].mean())
            if d < bd:
                bd, cls = d, c
        loo.append(cls)
    loo = np.array(loo, dtype=object)
    length_tests["length_only_classifier_loo"] = {
        "rule": "LOO nearest-class-mean on log1p(blob_tokens) — 길이만으로 얼마나 되는가",
        "prior_agreement": float(np.mean(loo == y)),
        "prior_agreement_fraction": f"{int(np.sum(loo == y))}/{n}",
        "macro_f1": macro_f1(y, loo),
        "beats_stratified_p95": bool(macro_f1(y, loo) > strat["macro_f1_p95"]),
    }
    # 길이-라벨 연관 자체
    ktab = {a: {"n": int(np.sum(y == a)),
                "tokens_median": float(np.median(toks[y == a])) if np.any(y == a) else None}
            for a in ARCHETYPES}
    length_tests["tokens_by_true_archetype"] = ktab

    # ---- 판정
    pcfg = configs[pkey]
    beats = pcfg["beats_judgment_baseline"]
    n_beat = proto_sens["global"]["n_configs_beating_stratified_p95"]
    flip = proto_sens["global"]["any_verdict_flip"]
    surv = length_tests["per_config"][pkey]["length_stratified_permutation"]["signal_survives_length_control"]

    if beats and n_beat >= 7 and not flip and surv:
        verdict = "SUPPORTED"
    elif n_beat >= 5 and surv:
        verdict = "PARTIALLY_SUPPORTED"
    elif n_beat == 0:
        verdict = "NOT_SUPPORTED"
    else:
        verdict = "PARTIALLY_SUPPORTED" if beats else "INCONCLUSIVE"

    h_null = ("REFUTED" if n_beat >= 5 else ("NOT_SUPPORTED" if n_beat == 0 else "INCONCLUSIVE"))
    h_len = ("NOT_SUPPORTED" if surv and
             length_tests["length_only_classifier_loo"]["macro_f1"] <= strat["macro_f1_p95"]
             else ("SUPPORTED" if not surv else "PARTIALLY_SUPPORTED"))
    h_proto = "SUPPORTED" if flip else ("PARTIALLY_SUPPORTED"
                                        if proto_sens["global"]["macro_f1_range_all_9_configs"] >= 0.10
                                        else "NOT_SUPPORTED")

    result = {
        "child_id": "D-RF-001-C",
        "rq_id": "RQ-D-RF-001",
        "hypothesis_id": "H-RF001-C-EMBED-PROTOTYPE",
        "verdict": verdict,
        "hypothesis_verdicts": {
            "H-RF001-C-EMBED-PROTOTYPE": verdict,
            "H-C-null (baseline 과 무차이)": h_null,
            "H-C-length (길이/도메인 어휘밀도를 재는 중)": h_len,
            "H-C-prototype (문구 민감)": h_proto,
        },
        "generated_at_kst": datetime.now(KST).isoformat(),
        "seed": SEED, "n_expected": 59, "n_observed": int(n),
        "analysis_unit": "target state (in_mart==1), 1 row = 1 web target",
        "target_variable": {
            "field": "prior_archetype",
            "warning": "gold label 이 아니라 business-domain prior 다. 지표는 accuracy 가 아니라 prior_agreement.",
            "class_counts": {a: int(np.sum(y == a)) for a in ARCHETYPES},
            "n_classes_with_support_le_5": int(sum(1 for a in ARCHETYPES if 0 < np.sum(y == a) <= 5)),
        },
        "learning": "none (zero-shot). 어떤 파라미터도 prior 로 적합하지 않았다.",
        "representation": "D_TEXT_CORPUS.text_blob (SSOT 01 §7 Text representation 그대로)",
        "input_quality": quality,
        "models": {m: {**MODELS[m], **store[m]["info"]} for m in MODELS},
        "prototype_sets": {s: PROTO_SETS[s] for s in PROTO_SETS},
        "prototype_provenance": ("SSOT 00 §4 archetype 목록과 SSOT 01 §5 Stage-3 branch 정의문에서만 "
                                 "유도했다. D_TEXT_CORPUS 를 읽고 문구를 조정하지 않았고, 결과를 본 "
                                 "뒤에도 수정하지 않았다."),
        "baselines": baselines,
        "configs": configs,
        "e5_prefix_ablation": e5alt,
        "primary": primary,
        "prototype_sensitivity": proto_sens,
        "length_confound": length_tests,
        "assertions": [
            {"type": "STATISTICAL", "claim": "PRIMARY config 의 macro F1 이 stratified 귀무 95퍼센타일을 넘는다",
             "value": pcfg["macro_f1"], "reference": strat["macro_f1_p95"], "holds": beats},
            {"type": "STATISTICAL", "claim": "9개 config 중 stratified p95 를 넘은 수",
             "value": n_beat, "reference": len(configs), "holds": n_beat >= 5},
            {"type": "ROBUSTNESS", "claim": "prototype 문구를 바꿔도 기준선 통과 판정이 뒤집히지 않는다",
             "value": not flip, "holds": not flip},
            {"type": "CONFOUND", "claim": "길이 tertile 내 순열 통제 후에도 PRIMARY 신호가 남는다",
             "value": surv, "holds": surv},
            {"type": "SCOPE", "claim": "예측이 7 archetype 밖으로 나가지 않았다",
             "value": True, "holds": True},
            {"type": "PROCESS", "claim": "gold label 미생산 · holdout 미열람 · threshold 미선언",
             "value": True, "holds": primary["threshold_declared"] is None},
        ],
        "limitation": (
            f"n={n} 에 7 class, 5개 class 가 n<=5 라 per-class 추정의 Wilson CI 가 거의 [0,1] 폭이다. "
            f"target 은 gold label 이 아니라 business-domain prior 이므로 불일치가 모델 오류인지 prior "
            f"오류인지 이 실험은 구분할 수 없다. 입력 DOM 품질 결함(중복 blob "
            f"{quality['duplicate_blob_n']}건, 인코딩 깨짐 의심 {quality['mojibake_suspect_n']}건, "
            f"토큰 12 이하 사실상 URL only {quality['near_url_only_n(<=12 tokens)']}건)이 상한을 누른다. "
            f"MiniLM 은 max_seq_length=128 이라 긴 blob 이 잘린다."
        ),
    }

    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(result, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
    print(f"[write] {OUT_JSON}")

    # ---- 그림
    figs = make_figures(df, y, toks, tert, preds, configs, strat, pkey, primary)

    # ---- MLflow
    log_mlflow(result, figs, preds, pkey, df, y)
    print(f"[verdict] {verdict}")
    return 0


def make_figures(df, y, toks, tert, preds, configs, strat, pkey, primary) -> dict:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams["font.family"] = ["DejaVu Sans"]
    FIGDIR.mkdir(parents=True, exist_ok=True)
    out = {}

    # 1. margin-coverage 곡선 (모든 model × PRIMARY set 비교)
    fig, ax = plt.subplots(1, 2, figsize=(12, 4.6))
    for mname in MODELS:
        k = f"{mname}|A_SSOT_DEF"
        rows = margin_curve(preds[k]["margin"], preds[k]["correct"])
        cov = [r["coverage"] for r in rows]
        pa = [r["prior_agreement_covered"] for r in rows]
        ax[0].plot(cov, pa, marker=".", ms=3, lw=1.2, label=k)
    ax[0].axhline(strat["prior_agreement_mean"], ls="--", c="gray",
                  label=f"stratified mean={strat['prior_agreement_mean']:.3f}")
    ax[0].set_xlabel("coverage (1 - abstention rate)")
    ax[0].set_ylabel("prior_agreement among covered")
    ax[0].set_title("margin-based abstention: coverage vs prior_agreement\n(threshold NOT declared)")
    ax[0].legend(fontsize=7); ax[0].grid(alpha=.3); ax[0].invert_xaxis()
    for mname in MODELS:
        k = f"{mname}|A_SSOT_DEF"
        ax[1].hist(preds[k]["margin"], bins=20, histtype="step", lw=1.4, label=k)
    ax[1].set_xlabel("top1 - top2 cosine margin"); ax[1].set_ylabel("count")
    ax[1].set_title("top1-top2 margin distribution (n=56)")
    ax[1].legend(fontsize=7); ax[1].grid(alpha=.3)
    fig.tight_layout()
    p = FIGDIR / "RF001_C_margin_coverage.png"; fig.savefig(p, dpi=140); plt.close(fig)
    out["margin_coverage"] = p

    # 2. 9-config macro F1 그리드
    fig, ax = plt.subplots(figsize=(7.5, 4.2))
    M = np.array([[configs[f"{m}|{s}"]["macro_f1"] for s in PROTO_SETS] for m in MODELS])
    im = ax.imshow(M, cmap="viridis", vmin=0, vmax=max(0.35, M.max()))
    ax.set_xticks(range(len(PROTO_SETS)), list(PROTO_SETS), fontsize=8)
    ax.set_yticks(range(len(MODELS)), list(MODELS), fontsize=8)
    for i in range(M.shape[0]):
        for j in range(M.shape[1]):
            ax.text(j, i, f"{M[i, j]:.3f}", ha="center", va="center",
                    color="w" if M[i, j] < M.max() * .6 else "k", fontsize=9)
    ax.set_title(f"macro F1 (n=56) — stratified mean={strat['macro_f1_mean']:.3f}, "
                 f"p95={strat['macro_f1_p95']:.3f}", fontsize=9)
    fig.colorbar(im, ax=ax, shrink=.8)
    fig.tight_layout()
    p = FIGDIR / "RF001_C_model_prototype_grid.png"; fig.savefig(p, dpi=140); plt.close(fig)
    out["grid"] = p

    # 3. 길이 교란
    fig, ax = plt.subplots(1, 3, figsize=(14, 4.2))
    r = preds[pkey]
    ax[0].scatter(toks[r["correct"]], r["margin"][r["correct"]], s=26, label="top1 == prior")
    ax[0].scatter(toks[~r["correct"]], r["margin"][~r["correct"]], s=26, marker="x", label="top1 != prior")
    ax[0].set_xscale("log"); ax[0].set_xlabel("blob_tokens (log)"); ax[0].set_ylabel("top1-top2 margin")
    ax[0].set_title(f"{pkey}: length vs margin"); ax[0].legend(fontsize=7); ax[0].grid(alpha=.3)
    ax[1].scatter(toks, r["top1_sim"], s=26, c=["tab:green" if c else "tab:red" for c in r["correct"]])
    ax[1].set_xscale("log"); ax[1].set_xlabel("blob_tokens (log)"); ax[1].set_ylabel("top1 cosine")
    ax[1].set_title("length vs top1 similarity"); ax[1].grid(alpha=.3)
    ts = ["T1_short", "T2_mid", "T3_long"]
    vals = [float(np.mean(r["correct"][tert == t])) for t in ts]
    ns = [int(np.sum(tert == t)) for t in ts]
    ax[2].bar(ts, vals, color="tab:blue")
    ax[2].axhline(strat["prior_agreement_mean"], ls="--", c="gray", label="stratified mean")
    for i, (v, nn) in enumerate(zip(vals, ns)):
        ax[2].text(i, v + .01, f"{v:.2f}\n(n={nn})", ha="center", fontsize=8)
    ax[2].set_ylabel("prior_agreement"); ax[2].set_title("agreement by length tertile")
    ax[2].legend(fontsize=7); ax[2].grid(alpha=.3, axis="y")
    fig.tight_layout()
    p = FIGDIR / "RF001_C_length_confound.png"; fig.savefig(p, dpi=140); plt.close(fig)
    out["length"] = p

    # 4. PRIMARY confusion
    fig, ax = plt.subplots(figsize=(6.6, 5.4))
    C = np.array(primary["confusion_matrix"]["matrix"])
    im = ax.imshow(C, cmap="Blues")
    ax.set_xticks(range(7), [a[:12] for a in ARCHETYPES], rotation=45, ha="right", fontsize=7)
    ax.set_yticks(range(7), [a[:12] for a in ARCHETYPES], fontsize=7)
    for i in range(7):
        for j in range(7):
            if C[i, j]:
                ax.text(j, i, C[i, j], ha="center", va="center", fontsize=9,
                        color="w" if C[i, j] > C.max() * .6 else "k")
    ax.set_xlabel("predicted (top1)"); ax.set_ylabel("prior_archetype (NOT gold label)")
    ax.set_title(f"PRIMARY {pkey} confusion, n=56", fontsize=9)
    fig.colorbar(im, ax=ax, shrink=.8); fig.tight_layout()
    p = FIGDIR / "RF001_C_confusion_primary.png"; fig.savefig(p, dpi=140); plt.close(fig)
    out["confusion"] = p
    return out


def log_mlflow(result, figs, preds, pkey, df, y):
    sys.path.insert(0, str(RD / "tools"))
    import mlflow
    import mlflow_contract as C

    PARENT = "2bf780a9efca4562bdf63a7c165514cc"
    strat = result["baselines"]["stratified"]
    with C.research_run(
            experiment="LA_03_RF_MAPPING", run_name="D-RF-001-C embedding_prototype",
            plane="D", agent_id="D", subagent_id="worker/D-RF-001-C",
            objective=("SSOT 정의에서 유도한 archetype prototype 과의 임베딩 유사도만으로 "
                       "prior 를 되찾을 수 있는가 (zero-shot)"),
            method=("multilingual sentence embedding + prototype cosine similarity, "
                    "3 model x 3 prototype set, prototype/length 민감도 및 margin-coverage 곡선 포함"),
            dataset_grain="target (in_mart==1), n=56",
            n_expected=59, n_observed=result["n_observed"],
            hypothesis_id="H-RF001-C-EMBED-PROTOTYPE",
            competing_hypothesis=("H-C-null baseline 과 무차이 / H-C-length 길이를 재는 중 / "
                                  "H-C-prototype 문구 민감"),
            claim_kind="ANALYSIS", ticket_id="NONE", phase="I1", split="none",
            parent_run_id=PARENT, result_path=OUT_JSON,
            model_or_rule_version="EMBED_PROTOTYPE_v1", seed=SEED,
            extra_tags={"mlflow.parentRunId": PARENT, "rq_id": "RQ-D-RF-001",
                        "child_id": "D-RF-001-C", "zero_shot": "true",
                        "primary_config": pkey,
                        "offline_models": "HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1"},
            extra_params={"n_monte_carlo": N_MC, "primary_config": pkey,
                          "prototype_sets": ",".join(PROTO_SETS),
                          "models": ",".join(MODELS),
                          "e5_prefix_convention": "PRIMARY asymmetric: proto='query: ', page='passage: '"},
    ) as run:
        m = {}
        for key, c in result["configs"].items():
            pfx = key.replace("|", ".")
            m[f"{pfx}.prior_agreement"] = c["prior_agreement"]
            m[f"{pfx}.macro_f1"] = c["macro_f1"]
            m[f"{pfx}.weighted_f1"] = c["weighted_f1"]
            m[f"{pfx}.top2_prior_agreement"] = c["top2_prior_agreement"]
            m[f"{pfx}.margin_median"] = c["margin_median"]
            m[f"{pfx}.macro_f1_p_vs_stratified"] = c["vs_stratified"]["macro_f1_p_vs_stratified_predictor"]
            m[f"{pfx}.beats_stratified_p95"] = float(c["beats_judgment_baseline"])
            m[f"{pfx}.n_distinct_predicted_classes"] = c["n_distinct_predicted_classes"]
        m["baseline.majority.prior_agreement"] = result["baselines"]["majority"]["prior_agreement"]
        m["baseline.majority.macro_f1"] = result["baselines"]["majority"]["macro_f1"]
        m["baseline.stratified.prior_agreement_mean"] = strat["prior_agreement_mean"]
        m["baseline.stratified.macro_f1_mean"] = strat["macro_f1_mean"]
        m["baseline.stratified.macro_f1_p95"] = strat["macro_f1_p95"]
        m["baseline.length_only_loo.macro_f1"] = result["length_confound"]["length_only_classifier_loo"]["macro_f1"]
        m["baseline.length_only_loo.prior_agreement"] = result["length_confound"]["length_only_classifier_loo"]["prior_agreement"]
        pr = result["primary"]
        m["primary.prior_agreement"] = pr["prior_agreement"]
        m["primary.macro_f1"] = pr["macro_f1"]
        m["primary.macro_f1_minus_stratified_mean"] = pr["vs_stratified"]["macro_f1_delta"]
        m["primary.macro_f1_minus_majority"] = pr["vs_majority"]["macro_f1_delta"]
        lc = result["length_confound"]["per_config"][pkey]
        m["primary.spearman_tokens_top1sim"] = lc["spearman_tokens_vs_top1sim"]["rho"]
        m["primary.spearman_tokens_margin"] = lc["spearman_tokens_vs_margin"]["rho"]
        m["primary.length_strat_perm_macro_f1_p"] = lc["length_stratified_permutation"]["macro_f1_p"]
        m["primary.signal_survives_length_control"] = float(lc["length_stratified_permutation"]["signal_survives_length_control"])
        ps = result["prototype_sensitivity"]["global"]
        m["prototype_sensitivity.macro_f1_range_9cfg"] = ps["macro_f1_range_all_9_configs"]
        m["prototype_sensitivity.n_beating_stratified_p95"] = ps["n_configs_beating_stratified_p95"]
        m["prototype_sensitivity.any_verdict_flip"] = float(ps["any_verdict_flip"])
        for c, v in result["primary"]["per_class"].items():
            m[f"primary.per_class.{c}.recall"] = v["recall"]
            m[f"primary.per_class.{c}.precision"] = v["precision"]
            m[f"primary.per_class.{c}.f1"] = v["f1"]
            m[f"primary.per_class.{c}.support"] = v["support"]
        mlflow.log_metrics({k: float(v) for k, v in m.items()})

        proto_txt = []
        for sname, pset in PROTO_SETS.items():
            proto_txt.append(f"===== {sname} =====")
            for a in ARCHETYPES:
                proto_txt.append(f"[{a}]\n{pset[a]}\n")
        proto_txt.append("provenance: " + result["prototype_provenance"])
        mlflow.log_text("\n".join(proto_txt), "prototype_definitions.txt")

        for name, p in figs.items():
            mlflow.log_artifact(str(p), artifact_path="figures")
        mlflow.log_artifact(str(OUT_JSON), artifact_path="result")

        # per-target 예측 테이블은 MLflow 안에만 둔다 (worker 는 허용된 4개 파일 밖을 쓰지 않는다).
        rows = []
        for i in range(len(df)):
            row = {"wtg": df["wtg"].iloc[i], "prior_service": df["prior_service"].iloc[i],
                   "prior_archetype": y[i], "blob_tokens": int(df["blob_tokens"].iloc[i])}
            for key, r in preds.items():
                row[f"{key}.top1"] = r["top1"][i]
                row[f"{key}.margin"] = round(float(r["margin"][i]), 5)
            rows.append(row)
        mlflow.log_text(pd.DataFrame(rows).to_csv(index=False), "result/RF001_C_predictions.csv")

        C.finish(verdict=result["verdict"], limitation=result["limitation"])
        print(f"[mlflow] run_id={run.info.run_id}")


if __name__ == "__main__":
    raise SystemExit(main())
