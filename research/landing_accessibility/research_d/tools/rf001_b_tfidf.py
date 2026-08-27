"""D-RF-001-B — TF-IDF + linear baseline for archetype PRIOR recovery.

RQ-D-RF-001 child B.  Target is NOT a gold label: it is `prior_archetype`, the
business-domain-derived prior recorded in the observation table.  Every score
reported here is therefore *prior_agreement*, never "accuracy" against truth.

Hypotheses
  H-RF001-B-TFIDF : page text alone recovers the 7-class archetype prior above a
                    stratified baseline.
  H-B-null        : with n=56 / 7 classes / min class n=3 the linear TF-IDF model
                    is indistinguishable from the stratified baseline.
  H-B-leak        : any recovery is memorisation of service/brand tokens, not
                    archetype-functional vocabulary.

Pre-declared design (fixed BEFORE any score was inspected):
  feature sets  A_blob_full, B_title_head_nav, C_blob_no_url, D_deleak, E_brand_only
  analyzers     word 1-2gram, char_wb 2-5gram
  models        logreg (LogisticRegression), linsvc (LinearSVC)
  => 5 x 2 x 2 = 20 configs, ALL reported.  Baselines: most_frequent, stratified.
  PRIMARY (declared in advance)  A_blob_full x word x logreg
  DELEAK PRIMARY (declared in advance)  D_deleak x word x logreg
  CV  RepeatedStratifiedKFold(n_splits=3, n_repeats=10, random_state=20260827)

read-only w.r.t. every input.  Writes only results/RF001_B_tfidf.json and figures/RF001_B_*.png
"""
from __future__ import annotations

import json
import re
import sys
import warnings
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlparse

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.dummy import DummyClassifier
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import confusion_matrix, f1_score, precision_recall_fscore_support
from sklearn.model_selection import (RepeatedStratifiedKFold, StratifiedKFold,
                                     permutation_test_score)
from sklearn.pipeline import Pipeline
from sklearn.svm import LinearSVC

warnings.filterwarnings("ignore")

RD = Path("/home/sieg/projects-wsl/ProjectFinal/.agent_worktrees/claude_d_research/"
          "research/landing_accessibility/research_d")
CORPUS = RD / "results" / "D_TEXT_CORPUS.csv"
OBS = RD / "results" / "D_OBSERVATION_TABLE.csv"
OUT_JSON = RD / "results" / "RF001_B_tfidf.json"
FIGDIR = RD / "figures"
SEED = 20260827
KST = timezone(timedelta(hours=9))

FIELDS = ["title", "meta_description", "headings", "landmarks", "nav_links", "buttons",
          "aria_labels", "placeholders", "form_labels", "input_names", "card_texts",
          "url_tokens"]
TOK = re.compile(r"[a-zA-Z0-9가-힣]+")

# ------------------------------------------------------------------ brand vocab
# 상위 기업/서비스 계열 토큰. prior_service + URL host 에서 자동 유도되지 않는 모기업명·
# 한글 변형을 손으로 보강한다. 과하게 지우는 쪽(conservative)으로 만든다.
BRAND_EXTRA = {
    "쿠팡", "쿠팡이츠", "카카오", "카카오톡", "카카오맵", "카카오t", "카카오모빌리티", "네이버", "네이버지도",
    "롯데", "롯데온", "롯데마트", "롯데백화점", "롯데홈쇼핑", "롯데하이마트", "하이마트", "신세계", "이마트",
    "이마트24", "현대", "현대카드", "현대백화점", "더현대", "삼성", "삼성카드", "삼성전자", "신한", "쏠", "sol",
    "하나", "하나은행", "국민", "국민은행", "kb", "kb페이", "kb스타뱅킹", "스타뱅킹", "농협", "nh", "콕뱅크",
    "홈플러스", "배민", "배달의민족", "우아한형제들", "토스", "지마켓", "g마켓", "티맵", "티맵모빌리티", "당근",
    "당근마켓", "컬리", "마켓컬리", "다이소", "세븐일레븐", "메가커피", "컴포즈", "컴포즈커피", "홈앤쇼핑",
    "넷플릭스", "유튜브", "구글", "크롬", "인스타그램", "틱톡", "밴드", "다음", "모니모", "캐시워크", "안랩",
    "에이닷", "sk텔레콤", "skt", "gs", "gs25", "지에스", "씨유", "cu", "미니스톱", "탑마트", "서원유통",
    "농협하나로마트", "하나로마트", "코스트코", "cj", "cj온스타일", "온스타일", "ns홈쇼핑", "11번가", "십일번가",
    "netflix", "youtube", "google", "chrome", "instagram", "tiktok", "kakao", "naver", "coupang",
    "coupangeats", "toss", "baemin", "kurly", "emart", "homeplus", "lotte", "shinsegae", "hyundai",
    "samsung", "shinhan", "hana", "kbstar", "kbcard", "nonghyup", "nhbank", "bgfretail", "gsretail",
    "daiso", "eleven", "ahnlab", "sktelecom", "band", "daangn", "11st", "gmarket", "cjonstyle",
    "hnsmall", "nsmall", "himart", "megacoffee", "composecoffee", "costco", "monimo", "cashwalk",
    "tmap", "tmapmobility", "seowon", "nhhanaro", "lottemart", "lotteon", "ellotte", "ehyundai",
    "thehyundaiseoul", "samsungsvc", "samsungcard", "hyundaicard", "daum", "lottehomeshopping",
    "kakaocorp", "navercorp", "kakaomobility", "lottemartzetta", "mplweb", "omoney", "mbiz",
    "zetta", "v3", "mycompany", "bank", "banking",
}
HOST_STOP = {"www", "com", "co", "kr", "net", "org", "im", "us", "http", "https", "m", "go", "or"}


def build_brand_terms(df: pd.DataFrame) -> list[str]:
    terms: set[str] = set(BRAND_EXTRA)
    for s in df["prior_service"].fillna(""):
        s = s.strip()
        if len(s) >= 2:
            terms.add(s.lower())
        for p in re.split(r"[\s/·\-]+", s):
            if len(p) >= 2:
                terms.add(p.lower())
    for u in df["prior_url"].fillna(""):
        host = urlparse(u).hostname or ""
        for t in re.split(r"[.\-]", host):
            if t and t not in HOST_STOP and len(t) >= 2:
                terms.add(t.lower())
    # 긴 것부터 지워야 부분 매칭으로 조각이 남지 않는다
    return sorted(terms, key=len, reverse=True)


def strip_brands(text: str, pattern: re.Pattern) -> str:
    return re.sub(r"\s+", " ", pattern.sub(" ", text)).strip()


def keep_brands_only(text: str, pattern: re.Pattern) -> str:
    return " ".join(m.group(0).lower() for m in pattern.finditer(text))


# ------------------------------------------------------------------ feature sets
def make_featuresets(df: pd.DataFrame, brand_pat: re.Pattern) -> dict[str, list[str]]:
    blob_full = df["text_blob"].fillna("").astype(str).tolist()
    title_head_nav = [" \n ".join(x for x in (r.get("title") or "", r.get("headings") or "",
                                              r.get("nav_links") or "") if x)
                      for _, r in df.fillna("").iterrows()]
    no_url = [" \n ".join(str(r[f]) for f in FIELDS if f != "url_tokens" and str(r[f]).strip())
              for _, r in df.fillna("").iterrows()]
    deleak = [strip_brands(t, brand_pat) for t in no_url]
    brand_only = [keep_brands_only(t, brand_pat) for t in blob_full]
    return {"A_blob_full": blob_full, "B_title_head_nav": title_head_nav,
            "C_blob_no_url": no_url, "D_deleak": deleak, "E_brand_only": brand_only}


def make_vec(analyzer: str) -> TfidfVectorizer:
    if analyzer == "word":
        return TfidfVectorizer(analyzer="word", ngram_range=(1, 2), lowercase=True,
                               token_pattern=r"(?u)\b\w{2,}\b", min_df=1, sublinear_tf=True)
    return TfidfVectorizer(analyzer="char_wb", ngram_range=(2, 5), lowercase=True,
                           min_df=2, sublinear_tf=True)


def make_clf(model: str):
    if model == "logreg":
        return LogisticRegression(max_iter=5000, C=1.0, class_weight="balanced",
                                  random_state=SEED)
    return LinearSVC(C=1.0, class_weight="balanced", random_state=SEED, max_iter=20000)


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    if n == 0:
        return (float("nan"), float("nan"))
    p = k / n
    d = 1 + z * z / n
    c = p + z * z / (2 * n)
    h = z * ((p * (1 - p) / n + z * z / (4 * n * n)) ** 0.5)
    return ((c - h) / d, (c + h) / d)


def main() -> int:
    df = pd.read_csv(CORPUS)
    df = df[df["dom_found"] == 1].reset_index(drop=True)
    y = df["prior_archetype"].astype(str).values
    classes = sorted(set(y))
    n = len(df)

    # --- data integrity notes (reported, not silently fixed) -------------------
    dup_text = df.groupby(df["text_blob"].fillna("")).size()
    import hashlib as _hl
    dup_groups = [{"text_sha_prefix": _hl.sha256(k.encode()).hexdigest()[:12], "n": int(v),
                   "services": df.loc[df["text_blob"].fillna("") == k, "prior_service"].tolist(),
                   "archetypes": sorted(set(df.loc[df["text_blob"].fillna("") == k,
                                                   "prior_archetype"]))}
                  for k, v in dup_text.items() if v > 1]
    dup_url = df[df["prior_url"].notna()].groupby("prior_url").size()
    dup_url_groups = [{"url": k, "n": int(v),
                       "services": df.loc[df["prior_url"] == k, "prior_service"].tolist()}
                      for k, v in dup_url.items() if v > 1]
    ct = pd.crosstab(df["prior_archetype"], df["prior_business_domain"])
    collinear = bool((ct > 0).sum(axis=1).max() == 1 and (ct > 0).sum(axis=0).max() == 1)

    brand_terms = build_brand_terms(df)
    brand_pat = re.compile("|".join(re.escape(t) for t in brand_terms), re.IGNORECASE)
    featuresets = make_featuresets(df, brand_pat)

    fs_stats = {}
    for name, docs in featuresets.items():
        toks = [len(TOK.findall(d)) for d in docs]
        fs_stats[name] = {"n_docs": len(docs), "empty_docs": int(sum(1 for t in toks if t == 0)),
                          "tokens_median": float(np.median(toks)), "tokens_min": int(min(toks)),
                          "tokens_max": int(max(toks)), "tokens_mean": float(np.mean(toks))}

    cv = RepeatedStratifiedKFold(n_splits=3, n_repeats=10, random_state=SEED)
    splits = list(cv.split(np.zeros(n), y))
    n_folds = len(splits)

    def run_config(docs, vec_kind, model_kind):
        """fold 별 macro F1 + OOF 예측(및 확률)을 모은다."""
        X = np.array(docs, dtype=object)
        fold_f1, oof_rows, failures = [], [], 0
        for fi, (tr, te) in enumerate(splits):
            rep = fi // 3
            try:
                pipe = Pipeline([("v", make_vec(vec_kind)), ("c", make_clf(model_kind))])
                pipe.fit(X[tr], y[tr])
                pred = pipe.predict(X[te])
                proba = None
                if model_kind == "logreg":
                    P = pipe.predict_proba(X[te])
                    cls = list(pipe.named_steps["c"].classes_)
                    proba = P.max(axis=1)
                fold_f1.append(f1_score(y[te], pred, average="macro", zero_division=0))
                for j, idx in enumerate(te):
                    oof_rows.append({"i": int(idx), "repeat": rep, "true": y[idx],
                                     "pred": pred[j],
                                     "top1": float(proba[j]) if proba is not None else None})
            except Exception:
                failures += 1
        return np.array(fold_f1, dtype=float), pd.DataFrame(oof_rows), failures

    def run_baseline(strategy):
        fold_f1 = []
        X = np.zeros((n, 1))
        for tr, te in splits:
            d = DummyClassifier(strategy=strategy, random_state=SEED)
            d.fit(X[tr], y[tr])
            fold_f1.append(f1_score(y[te], d.predict(X[te]), average="macro", zero_division=0))
        return np.array(fold_f1, dtype=float)

    def summ(a: np.ndarray) -> dict:
        a = a[~np.isnan(a)]
        return {"n_folds": int(a.size), "mean": float(a.mean()), "std": float(a.std(ddof=1)),
                "median": float(np.median(a)), "min": float(a.min()), "max": float(a.max()),
                "p2_5": float(np.percentile(a, 2.5)), "p97_5": float(np.percentile(a, 97.5))}

    # --- baselines ------------------------------------------------------------
    base = {}
    for strat in ("most_frequent", "stratified"):
        base[strat] = {"fold_scores": run_baseline(strat).tolist()}
        base[strat]["summary"] = summ(np.array(base[strat]["fold_scores"]))
    strat_mean = base["stratified"]["summary"]["mean"]
    mf_mean = base["most_frequent"]["summary"]["mean"]

    # --- full pre-declared grid ----------------------------------------------
    configs, oof_store = {}, {}
    for fs_name, docs in featuresets.items():
        for vec_kind in ("word", "char_wb"):
            for model_kind in ("logreg", "linsvc"):
                key = f"{fs_name}.{vec_kind}.{model_kind}"
                f1s, oof, fails = run_config(docs, vec_kind, model_kind)
                s = summ(f1s) if f1s.size else {"n_folds": 0}
                configs[key] = {
                    "featureset": fs_name, "analyzer": vec_kind, "model": model_kind,
                    "fold_failures": fails, "fold_scores": f1s.tolist(), "summary": s,
                    "lift_vs_stratified": float(s["mean"] - strat_mean) if f1s.size else None,
                    "lift_vs_most_frequent": float(s["mean"] - mf_mean) if f1s.size else None,
                    "ci_includes_stratified_mean": bool(
                        s["p2_5"] <= strat_mean <= s["p97_5"]) if f1s.size else None,
                    "ci_includes_most_frequent_mean": bool(
                        s["p2_5"] <= mf_mean <= s["p97_5"]) if f1s.size else None,
                }
                oof_store[key] = oof
                print(f"  {key:<38} macroF1 {s.get('mean', float('nan')):.3f} "
                      f"+-{s.get('std', float('nan')):.3f}  fails={fails}")

    PRIMARY = "A_blob_full.word.logreg"
    DELEAK_PRIMARY = "D_deleak.word.logreg"

    # --- per-class metrics (primary + deleak primary) -------------------------
    def per_class(key):
        oof = oof_store[key]
        out = {}
        for c in classes:
            sup = int((df["prior_archetype"] == c).sum())
            recs, precs, f1s = [], [], []
            for rep, g in oof.groupby("repeat"):
                p, r, f, _ = precision_recall_fscore_support(
                    g["true"], g["pred"], labels=[c], zero_division=0)
                precs.append(p[0]); recs.append(r[0]); f1s.append(f[0])
            mrec = float(np.mean(recs))
            lo, hi = wilson(int(round(mrec * sup)), sup)
            out[c] = {"support": sup,
                      "recall_mean_over_repeats": mrec, "recall_std": float(np.std(recs, ddof=1)),
                      "precision_mean_over_repeats": float(np.mean(precs)),
                      "f1_mean_over_repeats": float(np.mean(f1s)),
                      "recall_wilson95_lo": lo, "recall_wilson95_hi": hi,
                      "estimable": bool(sup > 5),
                      "note": "support<=5: 사실상 추정 불가" if sup <= 5 else ""}
        return out

    per_class_primary = per_class(PRIMARY)
    per_class_deleak = per_class(DELEAK_PRIMARY)

    # --- abstention curve for every logreg config -----------------------------
    thresholds = [round(t, 2) for t in np.arange(0.0, 0.85, 0.05)]
    abstention = {}
    for key, oof in oof_store.items():
        if "logreg" not in key or oof.empty:
            continue
        rows = []
        tot = len(oof)
        for t in thresholds:
            sel = oof[oof["top1"] >= t]
            cov = len(sel) / tot
            agree = float((sel["true"] == sel["pred"]).mean()) if len(sel) else float("nan")
            mf1 = (f1_score(sel["true"], sel["pred"], average="macro", zero_division=0)
                   if len(sel) else float("nan"))
            rows.append({"threshold": t, "n_kept": int(len(sel)), "n_total": int(tot),
                         "coverage": cov, "prior_agreement_within_coverage": agree,
                         "macro_f1_within_coverage": float(mf1)})
        abstention[key] = rows

    # --- confusion matrix, primary --------------------------------------------
    oofp = oof_store[PRIMARY]
    cm = confusion_matrix(oofp["true"], oofp["pred"], labels=classes)
    cm_norm = cm / 10.0   # 10 repeats

    # --- permutation test on the pre-declared primary -------------------------
    Xp = np.array(featuresets["A_blob_full"], dtype=object)
    pipe_p = Pipeline([("v", make_vec("word")), ("c", make_clf("logreg"))])
    perm_score, perm_scores, perm_p = permutation_test_score(
        pipe_p, Xp, y, scoring="f1_macro", cv=StratifiedKFold(3, shuffle=True, random_state=SEED),
        n_permutations=200, random_state=SEED, n_jobs=1)
    Xd = np.array(featuresets["D_deleak"], dtype=object)
    pipe_d = Pipeline([("v", make_vec("word")), ("c", make_clf("logreg"))])
    perm_score_d, perm_scores_d, perm_p_d = permutation_test_score(
        pipe_d, Xd, y, scoring="f1_macro", cv=StratifiedKFold(3, shuffle=True, random_state=SEED),
        n_permutations=200, random_state=SEED, n_jobs=1)

    # --- top coefficient tokens per class (full-data fit, word analyzer) ------
    def top_tokens(docs, topk=15):
        vec = make_vec("word")
        M = vec.fit_transform(docs)
        clf = make_clf("logreg")
        clf.fit(M, y)
        feats = np.array(vec.get_feature_names_out())
        out = {}
        for ci, c in enumerate(clf.classes_):
            coef = clf.coef_[ci]
            idx = np.argsort(coef)[::-1][:topk]
            toks = []
            for i in idx:
                tk = feats[i]
                is_brand = bool(brand_pat.fullmatch(tk) or
                                any(b in tk for b in brand_terms if len(b) >= 3))
                toks.append({"token": tk, "coef": float(coef[i]), "brand_match": is_brand})
            out[str(c)] = toks
        return out

    top_full = top_tokens(featuresets["A_blob_full"])
    top_deleak = top_tokens(featuresets["D_deleak"])
    brand_share = {c: float(np.mean([t["brand_match"] for t in v])) for c, v in top_full.items()}
    brand_share_deleak = {c: float(np.mean([t["brand_match"] for t in v]))
                          for c, v in top_deleak.items()}

    # --- leak verdict arithmetic ---------------------------------------------
    def m(k):
        return configs[k]["summary"].get("mean", float("nan"))

    leak = {
        "primary_full_macro_f1": m(PRIMARY),
        "primary_deleak_macro_f1": m(DELEAK_PRIMARY),
        "deleak_drop_abs": m(PRIMARY) - m(DELEAK_PRIMARY),
        "deleak_retention_frac": (m(DELEAK_PRIMARY) / m(PRIMARY)) if m(PRIMARY) else None,
        "brand_only_macro_f1_word_logreg": m("E_brand_only.word.logreg"),
        "brand_only_vs_stratified_lift": m("E_brand_only.word.logreg") - strat_mean,
        "deleak_still_above_stratified": bool(
            configs[DELEAK_PRIMARY]["summary"]["p2_5"] > strat_mean),
        "top15_brand_share_full": brand_share,
        "top15_brand_share_deleak": brand_share_deleak,
        "mean_top15_brand_share_full": float(np.mean(list(brand_share.values()))),
        "n_brand_terms_removed": len(brand_terms),
    }

    # --- figures --------------------------------------------------------------
    FIGDIR.mkdir(exist_ok=True)
    figs = {}

    order = list(configs.keys())
    fig1, ax = plt.subplots(figsize=(13, 7))
    data = [np.array(base["stratified"]["fold_scores"]),
            np.array(base["most_frequent"]["fold_scores"])] + \
           [np.array(configs[k]["fold_scores"]) for k in order]
    labels = ["BASE stratified", "BASE most_frequent"] + order
    bp = ax.boxplot(data, vert=False, labels=labels, showmeans=True, widths=0.6)
    for i, d in enumerate(data):
        ax.scatter(d, np.full(d.size, i + 1) + np.random.RandomState(SEED).normal(0, .06, d.size),
                   s=6, alpha=.35, color="tab:blue")
    ax.axvline(strat_mean, color="tab:red", ls="--", lw=1.2,
               label=f"stratified baseline mean={strat_mean:.3f}")
    ax.axvline(mf_mean, color="tab:orange", ls=":", lw=1.2,
               label=f"most_frequent baseline mean={mf_mean:.3f}")
    ax.set_xlabel("fold macro F1 (prior_agreement, NOT gold accuracy)  ·  30 folds = 3-fold x 10 repeats")
    ax.set_title("D-RF-001-B  TF-IDF linear vs baselines — full pre-declared grid (n=56, 7 classes)")
    ax.legend(loc="lower right", fontsize=8)
    ax.tick_params(labelsize=8)
    fig1.tight_layout()
    p1 = FIGDIR / "RF001_B_fold_distribution.png"
    fig1.savefig(p1, dpi=140)
    figs["fold_distribution"] = str(p1)

    fig2, ax = plt.subplots(figsize=(8, 6.5))
    im = ax.imshow(cm_norm, cmap="Blues")
    ax.set_xticks(range(len(classes))); ax.set_xticklabels(classes, rotation=45, ha="right", fontsize=8)
    ax.set_yticks(range(len(classes))); ax.set_yticklabels(classes, fontsize=8)
    for i in range(len(classes)):
        for j in range(len(classes)):
            ax.text(j, i, f"{cm_norm[i, j]:.1f}", ha="center", va="center", fontsize=8,
                    color="white" if cm_norm[i, j] > cm_norm.max() * .6 else "black")
    ax.set_xlabel("predicted"); ax.set_ylabel("prior (target)")
    ax.set_title(f"OOF confusion, {PRIMARY}\ncounts averaged over 10 repeats, n=56")
    fig2.colorbar(im, ax=ax, shrink=.8)
    fig2.tight_layout()
    p2 = FIGDIR / "RF001_B_confusion.png"
    fig2.savefig(p2, dpi=140)
    figs["confusion"] = str(p2)

    fig3, (a1, a2) = plt.subplots(1, 2, figsize=(12, 5))
    for key in (PRIMARY, DELEAK_PRIMARY, "B_title_head_nav.word.logreg",
                "E_brand_only.word.logreg"):
        if key not in abstention:
            continue
        r = pd.DataFrame(abstention[key])
        a1.plot(r["threshold"], r["coverage"], marker="o", ms=3, label=key)
        a2.plot(r["threshold"], r["prior_agreement_within_coverage"], marker="o", ms=3, label=key)
    a1.set_xlabel("top-1 probability threshold"); a1.set_ylabel("coverage")
    a1.set_title("coverage vs abstention threshold"); a1.grid(alpha=.3)
    a2.set_xlabel("top-1 probability threshold")
    a2.set_ylabel("prior_agreement within coverage")
    a2.set_title("agreement inside covered set"); a2.grid(alpha=.3)
    a2.legend(fontsize=7)
    fig3.suptitle("D-RF-001-B abstention curves — NO threshold is declared canonical", fontsize=10)
    fig3.tight_layout()
    p3 = FIGDIR / "RF001_B_abstention.png"
    fig3.savefig(p3, dpi=140)
    figs["abstention"] = str(p3)

    fig4, ax = plt.subplots(figsize=(10, 5.5))
    fss = list(featuresets.keys())
    w = 0.2
    for oi, (vk, mk) in enumerate([("word", "logreg"), ("word", "linsvc"),
                                   ("char_wb", "logreg"), ("char_wb", "linsvc")]):
        vals = [configs[f"{f}.{vk}.{mk}"]["summary"].get("mean", np.nan) for f in fss]
        errs = [configs[f"{f}.{vk}.{mk}"]["summary"].get("std", np.nan) for f in fss]
        ax.bar(np.arange(len(fss)) + (oi - 1.5) * w, vals, w, yerr=errs, capsize=2,
               label=f"{vk}/{mk}")
    ax.axhline(strat_mean, color="tab:red", ls="--", label=f"stratified={strat_mean:.3f}")
    ax.set_xticks(range(len(fss))); ax.set_xticklabels(fss, rotation=15, fontsize=8)
    ax.set_ylabel("mean fold macro F1 (+-1 SD)")
    ax.set_title("brand-leak ablation: A/C full text vs D de-leaked vs E brand-tokens-only")
    ax.legend(fontsize=8)
    fig4.tight_layout()
    p4 = FIGDIR / "RF001_B_brand_ablation.png"
    fig4.savefig(p4, dpi=140)
    figs["brand_ablation"] = str(p4)

    # --- verdict --------------------------------------------------------------
    best_key = max((k for k in configs if configs[k]["summary"].get("n_folds")),
                   key=lambda k: configs[k]["summary"]["mean"])
    best = configs[best_key]
    beats = not best["ci_includes_stratified_mean"] and best["summary"]["p2_5"] > strat_mean
    primary_beats = (not configs[PRIMARY]["ci_includes_stratified_mean"]
                     and configs[PRIMARY]["summary"]["p2_5"] > strat_mean)
    deleak_beats = leak["deleak_still_above_stratified"]

    if beats and deleak_beats and leak["deleak_retention_frac"] and leak["deleak_retention_frac"] > 0.7:
        verdict = "SUPPORTED"
    elif beats and deleak_beats:
        verdict = "PARTIALLY_SUPPORTED"
    elif beats and not deleak_beats:
        verdict = "PARTIALLY_SUPPORTED"
    elif not beats:
        verdict = "NOT_SUPPORTED"
    else:
        verdict = "INCONCLUSIVE"

    h_null = "REFUTED" if beats else "NOT_SUPPORTED"
    if deleak_beats and leak["deleak_retention_frac"] and leak["deleak_retention_frac"] > 0.7:
        h_leak = "NOT_SUPPORTED"
    elif not deleak_beats:
        h_leak = "SUPPORTED"
    else:
        h_leak = "PARTIALLY_SUPPORTED"

    doc = {
        "child_id": "D-RF-001-B", "rq_id": "RQ-D-RF-001",
        "title": "TF-IDF + linear baseline for archetype PRIOR recovery",
        "generated_at_kst": datetime.now(KST).isoformat(),
        "verdict": verdict,
        "hypothesis_verdicts": {
            "H-RF001-B-TFIDF": verdict,
            "H-B-null": h_null,
            "H-B-leak": h_leak,
        },
        "target_semantics": {
            "target_column": "prior_archetype",
            "is_gold_label": False,
            "metric_name": "prior_agreement (macro F1 against the business-domain prior)",
            "assertion_type": "ANALYSIS/NON_CANONICAL",
            "warning": "이 실험의 어떤 수치도 gold label 대비 accuracy 가 아니다. prior 재현율이다.",
            "prior_archetype_is_1to1_with_business_domain": collinear,
        },
        "inputs": {"corpus": str(CORPUS), "observation_table": str(OBS),
                   "n_rows_in_corpus": int(len(pd.read_csv(CORPUS))),
                   "n_used": n, "n_expected_targets": 59,
                   "class_counts": {c: int((df["prior_archetype"] == c).sum()) for c in classes},
                   "min_class_n": int(min((df["prior_archetype"] == c).sum() for c in classes))},
        "data_integrity": {
            "duplicate_text_blob_groups": dup_groups,
            "duplicate_url_groups": dup_url_groups,
            "note": "동일 텍스트가 두 target 에 나타나면 CV 에서 train/test 를 가로질러 새어 나간다.",
        },
        "design": {
            "seed": SEED,
            "cv": "RepeatedStratifiedKFold(n_splits=3, n_repeats=10, random_state=20260827)",
            "n_folds": n_folds,
            "pre_declared_primary": PRIMARY, "pre_declared_deleak_primary": DELEAK_PRIMARY,
            "featuresets": {k: fs_stats[k] for k in featuresets},
            "featureset_definitions": {
                "A_blob_full": "D_TEXT_CORPUS.text_blob 전체(=url_tokens 포함)",
                "B_title_head_nav": "title + headings + nav_links 만",
                "C_blob_no_url": "text_blob 구성 필드 중 url_tokens 제외",
                "D_deleak": "C_blob_no_url 에서 브랜드/서비스명 문자열 전면 제거",
                "E_brand_only": "text_blob 에서 브랜드/서비스명 토큰만 남김 (leak 상한 대조군)",
            },
            "analyzers": {"word": "TfidfVectorizer word 1-2gram, token>=2chars, sublinear_tf",
                          "char_wb": "TfidfVectorizer char_wb 2-5gram, min_df=2, sublinear_tf"},
            "models": {"logreg": "LogisticRegression C=1.0 class_weight=balanced max_iter=5000",
                       "linsvc": "LinearSVC C=1.0 class_weight=balanced"},
            "grid_size": len(configs),
            "no_post_hoc_tuning": "grid 는 결과를 보기 전에 고정했고 20개 셀을 전부 보고한다.",
        },
        "baselines": base,
        "configs": configs,
        "best_config_post_hoc": {"key": best_key, **{k: best[k] for k in
                                                     ("summary", "lift_vs_stratified",
                                                      "lift_vs_most_frequent",
                                                      "ci_includes_stratified_mean")},
                                 "caveat": "20셀 중 최대값이므로 selection bias 가 있다. 판정은 사전 선언 primary 로 한다."},
        "primary_result": {"key": PRIMARY, **configs[PRIMARY],
                           "beats_stratified_by_ci": primary_beats},
        "deleak_primary_result": {"key": DELEAK_PRIMARY, **configs[DELEAK_PRIMARY]},
        "permutation_test": {
            "primary": {"config": PRIMARY, "cv": "StratifiedKFold(3, shuffle, seed)",
                        "score": float(perm_score), "p_value": float(perm_p),
                        "n_permutations": 200,
                        "null_mean": float(np.mean(perm_scores)),
                        "null_p97_5": float(np.percentile(perm_scores, 97.5))},
            "deleak": {"config": DELEAK_PRIMARY, "score": float(perm_score_d),
                       "p_value": float(perm_p_d), "n_permutations": 200,
                       "null_mean": float(np.mean(perm_scores_d)),
                       "null_p97_5": float(np.percentile(perm_scores_d, 97.5))},
        },
        "per_class": {"primary": per_class_primary, "deleak_primary": per_class_deleak,
                      "note": "Wilson CI 의 n 은 class support(독립 표본 수)이고 반복수로 부풀리지 않았다."},
        "confusion_primary": {"labels": classes,
                              "counts_summed_over_10_repeats": cm.tolist(),
                              "counts_per_repeat": cm_norm.round(2).tolist()},
        "brand_leak_test": leak,
        "top_tokens_by_class": {"A_blob_full": top_full, "D_deleak": top_deleak},
        "abstention_curves": abstention,
        "abstention_note": "임의 임계를 영구 기준으로 선언하지 않는다. 곡선 전체를 보고한다.",
        "figures": figs,
        "limitations": [
            "n=56, 7 class, 최소 class n=3. class 5개(n<=5)의 per-class 수치는 사실상 추정 불가.",
            "target 은 gold label 이 아니라 business-domain prior 이며, prior_archetype 은 "
            "prior_business_domain 과 1:1 이라 사실상 '텍스트로 업종을 맞히는' 과제다.",
            "브랜드 제거는 문자열 치환이라 '다음/하나/현대' 같은 일반어 동형이의어까지 지운다 — "
            "de-leak 결과는 보수적(과소평가) 방향이다.",
            "동일 URL/동일 텍스트 중복이 존재하면 CV 폴드를 가로지르는 누출이 남는다.",
            "fold 는 30개지만 표본은 56개뿐이라 fold 점수들은 독립이 아니다. percentile 구간을 "
            "정식 신뢰구간처럼 읽으면 안 된다.",
            "인과 주장 없음. 어떤 토큰이 archetype 을 '만든다'는 해석은 불가.",
        ],
        "production_implication": [
            "이 모델은 production RF mapping 의 1차 판정기로 쓸 수 없다 — prior 재현조차 "
            "class 대부분에서 무너진다.",
            "쓰인다면 rule DT 가 abstain 한 경우의 보조 신호이며, 반드시 abstention 임계와 "
            "함께 쓰고 임계는 별도 데이터로 정해야 한다.",
        ],
        "further_questions": [
            "형태소 분석기(kiwipiepy) 기반 토크나이즈가 word n-gram 열세를 얼마나 회복하는가",
            "archetype 대신 business_domain 을 직접 예측하면(동일 과제) 어휘 사전 기반 규칙이 "
            "TF-IDF 보다 나은가",
            "n 을 59→수백으로 늘렸을 때 minority class 가 추정 가능해지는 최소 규모는",
        ],
    }

    OUT_JSON.write_text(json.dumps(doc, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\nwrote {OUT_JSON}")
    print(f"verdict={verdict}  H-B-null={h_null}  H-B-leak={h_leak}")
    print(f"primary {PRIMARY} mean={configs[PRIMARY]['summary']['mean']:.3f} "
          f"[{configs[PRIMARY]['summary']['p2_5']:.3f},{configs[PRIMARY]['summary']['p97_5']:.3f}] "
          f"stratified={strat_mean:.3f} mf={mf_mean:.3f}")
    print(f"best(post-hoc) {best_key} mean={best['summary']['mean']:.3f}")
    print(f"deleak {DELEAK_PRIMARY} mean={configs[DELEAK_PRIMARY]['summary']['mean']:.3f} "
          f"retention={leak['deleak_retention_frac']}")
    print(f"brand_only word logreg = {leak['brand_only_macro_f1_word_logreg']:.3f}")
    print(f"perm p primary={perm_p:.4f}  deleak={perm_p_d:.4f}")

    # ------------------------------------------------------------------ MLflow
    if "--no-mlflow" in sys.argv:
        return 0
    sys.path.insert(0, str(RD / "tools"))
    import mlflow
    import mlflow_contract as C

    PARENT = "2bf780a9efca4562bdf63a7c165514cc"
    tok_lines = []
    for label, tt in (("A_blob_full", top_full), ("D_deleak", top_deleak)):
        tok_lines.append(f"=== featureset {label} — LogisticRegression top-15 positive coefficients ===")
        for c, toks in tt.items():
            tok_lines.append(f"\n[{c}]  (brand_match share = "
                             f"{np.mean([t['brand_match'] for t in toks]):.2f})")
            for t in toks:
                tok_lines.append(f"   {t['coef']:+.3f}  {'BRAND' if t['brand_match'] else '     '}  {t['token']}")
        tok_lines.append("")
    top_tokens_text = "\n".join(tok_lines)

    with C.research_run(
            experiment="LA_03_RF_MAPPING", run_name="D-RF-001-B tfidf",
            plane="D", agent_id="D", subagent_id="worker/D-RF-001-B",
            objective=("페이지 텍스트 TF-IDF 만으로 archetype prior 를 되찾을 수 있는지와, "
                       "그것이 브랜드 암기가 아닌지"),
            method="TF-IDF(word/char_wb) + LogisticRegression/LinearSVC, RepeatedStratifiedKFold 3x10, 20-cell pre-declared grid",
            dataset_grain="target (in_mart==1), n=56",
            n_expected=59, n_observed=56,
            hypothesis_id="H-RF001-B-TFIDF",
            competing_hypothesis="H-B-null: baseline 과 구분 안 됨 / H-B-leak: 브랜드 토큰 암기",
            claim_kind="ANALYSIS", ticket_id="NONE", phase="I1", split="none",
            parent_run_id=PARENT, result_path=OUT_JSON,
            model_or_rule_version="TFIDF_LINEAR_v1", seed=SEED,
            extra_params={"grid_size": len(configs), "cv": doc["design"]["cv"],
                          "primary_config": PRIMARY, "deleak_primary_config": DELEAK_PRIMARY},
            extra_tags={"mlflow.parentRunId": PARENT, "rq_id": "RQ-D-RF-001",
                        "child_id": "D-RF-001-B",
                        "target_is_prior_not_gold": "true",
                        "metric_semantics": "prior_agreement"}) as run:
        mm = {
            "baseline_stratified.macro_f1_mean": base["stratified"]["summary"]["mean"],
            "baseline_stratified.macro_f1_std": base["stratified"]["summary"]["std"],
            "baseline_most_frequent.macro_f1_mean": mf_mean,
            "baseline_most_frequent.macro_f1_std": base["most_frequent"]["summary"]["std"],
            "n_observed": float(n), "min_class_n": float(doc["inputs"]["min_class_n"]),
            "permutation_p_primary": float(perm_p),
            "permutation_p_deleak": float(perm_p_d),
            "leak.deleak_retention_frac": float(leak["deleak_retention_frac"] or 0.0),
            "leak.deleak_drop_abs": float(leak["deleak_drop_abs"]),
            "leak.brand_only_macro_f1": float(leak["brand_only_macro_f1_word_logreg"]),
            "leak.mean_top15_brand_share": float(leak["mean_top15_brand_share_full"]),
        }
        for k, cfg in configs.items():
            s = cfg["summary"]
            if not s.get("n_folds"):
                continue
            mm[f"{k}.macro_f1_mean"] = s["mean"]
            mm[f"{k}.macro_f1_std"] = s["std"]
            mm[f"{k}.macro_f1_p2_5"] = s["p2_5"]
            mm[f"{k}.macro_f1_p97_5"] = s["p97_5"]
            mm[f"{k}.lift_vs_stratified"] = cfg["lift_vs_stratified"]
        for c, v in per_class_primary.items():
            mm[f"per_class.{c}.recall_mean"] = v["recall_mean_over_repeats"]
            mm[f"per_class.{c}.f1_mean"] = v["f1_mean_over_repeats"]
            mm[f"per_class.{c}.support"] = float(v["support"])
        mlflow.log_metrics({k: float(v) for k, v in mm.items() if v is not None})

        for i, s in enumerate(configs[PRIMARY]["fold_scores"]):
            mlflow.log_metric("fold_macro_f1", float(s), step=i)
        for i, s in enumerate(configs[DELEAK_PRIMARY]["fold_scores"]):
            mlflow.log_metric("fold_macro_f1_deleak", float(s), step=i)
        for i, s in enumerate(base["stratified"]["fold_scores"]):
            mlflow.log_metric("fold_macro_f1_baseline_stratified", float(s), step=i)
        for i, r in enumerate(abstention[PRIMARY]):
            mlflow.log_metric("abstention_coverage", float(r["coverage"]), step=i)
            mlflow.log_metric("abstention_prior_agreement", float(r["prior_agreement_within_coverage"]), step=i)

        mlflow.log_figure(fig1, "fold_distribution.png")
        mlflow.log_figure(fig2, "confusion_tfidf.png")
        mlflow.log_figure(fig3, "abstention.png")
        mlflow.log_figure(fig4, "brand_ablation.png")
        mlflow.log_artifact(str(OUT_JSON), artifact_path="result")
        mlflow.log_text(top_tokens_text, "top_tokens_by_class.txt")
        mlflow.log_text(json.dumps(brand_terms, ensure_ascii=False, indent=1),
                        "brand_terms_removed.json")
        mlflow.log_text(json.dumps(doc["data_integrity"], ensure_ascii=False, indent=1),
                        "data_integrity.json")
        fmd = RD / "results" / "RF001_B_FINDINGS.md"
        if fmd.exists():
            mlflow.log_artifact(str(fmd), artifact_path="result")

        C.finish(verdict=verdict,
                 limitation="; ".join(doc["limitations"])[:3000])
        mlflow.log_text(run.info.run_id, "run_id.txt")
        print("MLFLOW_RUN_ID", run.info.run_id)
        # result JSON 은 run 을 열기 전에 확정했고 result_sha 무결성을 위해 이후 수정하지 않는다.
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
