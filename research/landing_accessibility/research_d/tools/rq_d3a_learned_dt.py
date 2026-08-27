"""RQ-D3A — Learned DT 진단 실험.

**이 실험이 무엇을 하는가 (오해 방지)**

목표는 대표기능 분류기를 만드는 것이 **아니다**. SSOT 01 §Layer O 와 D injection §8에
따라, 현재 L0 evidence 에서 뽑히는 browser-native feature 들이 frozen interaction
archetype 을 **어느 정도나 구분하는지 진단**하는 것이다.

target 은 gold label 이 아니라 **business-domain prior**
(`representative_task_candidate_shadow.csv` 의 interaction_archetype)다.
따라서 이 실험이 측정하는 것은:

    "L0 DOM/AX/probe feature 만으로 business-domain prior 를 얼마나 되찾을 수 있는가"

이지, "archetype 을 얼마나 정확히 맞히는가"가 아니다. prior 자체가 틀렸을 수 있고,
observed interaction 이 prior 를 이기는 것이 SSOT 규칙(01 §1)이다.

Learned DT 는 연구 정의를 바꾸지 않는다. 진단 도구다.

산출: MLflow nested runs + results/RQ_D3A_learned_dt.json + figures/
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import warnings
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import mlflow
import numpy as np
import pandas as pd
from sklearn.dummy import DummyClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.inspection import permutation_importance
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (accuracy_score, confusion_matrix, f1_score,
                             precision_recall_fscore_support)
from sklearn.model_selection import (RepeatedStratifiedKFold, StratifiedKFold,
                                     cross_val_predict, cross_validate)
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.tree import DecisionTreeClassifier, export_text

warnings.filterwarnings("ignore")

RD = Path(__file__).resolve().parents[1]
WT = RD.parents[2]
TABLE = RD / "results" / "D_OBSERVATION_TABLE.csv"
TRACKING_URI = "http://127.0.0.1:5000"
EXPERIMENT = "landing_accessibility_D_v21"
BASE_SHA = "bc0b7a087faf2328cbafdfa9b40bd426c5080d7d"
SEED = 20260827

# prior 를 되찾는 데 쓰면 안 되는 열: 식별자, prior 자기 자신, 결과 유래 값
LEAK_COLS = {
    "worker", "wtg", "run_dir", "run_ts", "observation_id", "in_mart", "sealed",
    "prior_archetype", "prior_business_domain", "prior_mapping_status",
    "prior_endpoint_signal_type", "prior_region_signal_type", "prior_service", "prior_url",
    "dom_title", "probe_title", "probe_url", "probe_final_url", "probe_lang",
    "probe_version", "probe_collected_at", "probe_present", "dom_parse_ok", "has_l0c",
}


def git(*a: str) -> str:
    return subprocess.run(["git", *a], cwd=WT, capture_output=True, text=True).stdout.strip()


def load() -> tuple[pd.DataFrame, pd.Series, list[str]]:
    df = pd.read_csv(TABLE)
    # 관측단위 66행에는 중복실행 4 target(각 2관측)이 있다. mart 가 채택한 관측만
    # 쓰면 target 1행 = 관측 1행이 되어 grain 이 닫힌다.
    df = df[df.in_mart == 1].copy()
    # probe 없는 2관측은 feature 절반이 결측이라 제외한다. 제외 사실은 결과에 남긴다.
    df = df[df.probe_present == 1].copy()
    feats = [c for c in df.select_dtypes("number").columns if c not in LEAK_COLS]
    X = df[feats].astype(float)
    X = X.fillna(X.median())
    return X, df["prior_archetype"], feats


def eval_model(name: str, est, X: pd.DataFrame, y: pd.Series, classes: list[str],
               parent_tags: dict, n_splits: int, n_repeats: int) -> dict:
    # OOF 예측은 partition 이어야 하므로 단일 StratifiedKFold 로 뽑는다.
    oof_cv = StratifiedKFold(n_splits=n_splits, shuffle=True, random_state=SEED)
    yp = cross_val_predict(est, X, y, cv=oof_cv, n_jobs=1)
    proba = None
    if hasattr(est, "predict_proba"):
        try:
            proba = cross_val_predict(est, X, y, cv=oof_cv, method="predict_proba", n_jobs=1)
        except Exception:
            proba = None

    # 불확실성은 반복 CV 의 fold 별 점수 분포로 본다. n 이 작아 단일 점수는 못 믿는다.
    rep_cv = RepeatedStratifiedKFold(n_splits=n_splits, n_repeats=n_repeats, random_state=SEED)
    cvres = cross_validate(est, X, y, cv=rep_cv, n_jobs=1,
                           scoring={"macro_f1": "f1_macro", "accuracy": "accuracy"})
    fold_f1 = np.asarray(cvres["test_macro_f1"], dtype=float)
    fold_acc = np.asarray(cvres["test_accuracy"], dtype=float)
    lo, hi = np.percentile(fold_f1, [2.5, 97.5])

    acc = accuracy_score(y, yp)
    f1m = f1_score(y, yp, average="macro", zero_division=0)
    f1w = f1_score(y, yp, average="weighted", zero_division=0)
    p, r, f, sup = precision_recall_fscore_support(y, yp, labels=classes, zero_division=0)
    cm = confusion_matrix(y, yp, labels=classes)

    # abstention: top1 확률이 임계 미만이면 판단 보류. 임계는 고정 선언이 아니라 곡선으로 본다.
    abst = {}
    if proba is not None:
        top1 = proba.max(axis=1)
        for t in (0.0, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8):
            keep = top1 >= t
            abst[f"{t:.1f}"] = {
                "coverage": float(keep.mean()),
                "n_kept": int(keep.sum()),
                "accuracy_on_kept": float(accuracy_score(y[keep], yp[keep])) if keep.sum() else None,
                "macro_f1_on_kept": float(f1_score(y[keep], yp[keep], average="macro",
                                                   zero_division=0)) if keep.sum() else None,
            }

    with mlflow.start_run(run_name=f"RQ-D3A/{name}", nested=True) as run:
        mlflow.set_tags({**parent_tags, "d.model": name, "d.rq_id": "RQ-D3A",
                         "d.experiment_kind": "DIAGNOSTIC_LEARNED_DT",
                         "d.target_semantics": "BUSINESS_DOMAIN_PRIOR_NOT_GOLD_LABEL"})
        mlflow.log_params({"model": name, "cv_splits": n_splits, "cv_repeats": n_repeats,
                           "n_features": X.shape[1], "n_samples": len(y),
                           "n_classes": len(classes), "seed": SEED,
                           "estimator": str(est)[:480]})
        mlflow.log_metrics({
            "accuracy": acc, "macro_f1": f1m, "weighted_f1": f1w,
            "cv_macro_f1_mean": float(fold_f1.mean()), "cv_macro_f1_std": float(fold_f1.std()),
            "cv_macro_f1_p2_5": float(lo), "cv_macro_f1_p97_5": float(hi),
            "cv_accuracy_mean": float(fold_acc.mean()), "cv_accuracy_std": float(fold_acc.std()),
            "cv_n_folds": float(len(fold_f1)),
        })
        # fold 별 점수를 step 으로 남겨 MLflow 에서 분포를 곡선으로 볼 수 있게 한다.
        for i, (a, b) in enumerate(zip(fold_f1, fold_acc)):
            mlflow.log_metric("fold_macro_f1", float(a), step=i)
            mlflow.log_metric("fold_accuracy", float(b), step=i)

        fig, ax = plt.subplots(figsize=(6.5, 3.6))
        ax.hist(fold_f1, bins=12, color="#4C78A8", edgecolor="white")
        ax.axvline(fold_f1.mean(), color="#E45756", lw=2,
                   label=f"mean={fold_f1.mean():.3f}")
        ax.axvspan(lo, hi, color="#E45756", alpha=0.12, label=f"95% [{lo:.3f}, {hi:.3f}]")
        ax.set_xlabel("fold macro F1"); ax.set_ylabel("folds")
        ax.set_title(f"{name} — {len(fold_f1)} folds ({n_splits}x{n_repeats})", fontsize=10)
        ax.legend(fontsize=8)
        fig.tight_layout()
        mlflow.log_figure(fig, f"fold_distribution_{name}.png")
        plt.close(fig)
        for cls, pi, ri, fi, si in zip(classes, p, r, f, sup):
            key = cls.lower()
            mlflow.log_metrics({f"precision.{key}": pi, f"recall.{key}": ri,
                                f"f1.{key}": fi, f"support.{key}": float(si)})
        for t, v in abst.items():
            mlflow.log_metrics({f"coverage.at_{t}": v["coverage"]})
            if v["accuracy_on_kept"] is not None:
                mlflow.log_metrics({f"accuracy_on_kept.at_{t}": v["accuracy_on_kept"],
                                    f"macro_f1_on_kept.at_{t}": v["macro_f1_on_kept"]})

        fig, ax = plt.subplots(figsize=(7.5, 6.5))
        ax.imshow(cm, cmap="Blues")
        ax.set_xticks(range(len(classes)), [c[:14] for c in classes], rotation=45, ha="right", fontsize=8)
        ax.set_yticks(range(len(classes)), [c[:14] for c in classes], fontsize=8)
        for i in range(len(classes)):
            for j in range(len(classes)):
                ax.text(j, i, cm[i, j], ha="center", va="center", fontsize=9,
                        color="white" if cm[i, j] > cm.max() / 2 else "black")
        ax.set_xlabel("predicted"); ax.set_ylabel("prior (true)")
        ax.set_title(f"{name} — confusion (n={len(y)}, macroF1={f1m:.3f})", fontsize=10)
        fig.tight_layout()
        mlflow.log_figure(fig, f"confusion_{name}.png")
        plt.close(fig)

        importances = {}
        est.fit(X, y)
        if isinstance(est, Pipeline):
            inner = est[-1]
        else:
            inner = est
        if hasattr(inner, "feature_importances_"):
            importances = dict(zip(X.columns, map(float, inner.feature_importances_)))
        elif hasattr(inner, "coef_"):
            importances = dict(zip(X.columns, map(float, np.abs(inner.coef_).mean(axis=0))))
        if not importances and name != "baseline_majority":
            pi = permutation_importance(est, X, y, n_repeats=5, random_state=SEED, n_jobs=1)
            importances = dict(zip(X.columns, map(float, pi.importances_mean)))
        if importances:
            top = sorted(importances.items(), key=lambda kv: -kv[1])[:15]
            fig, ax = plt.subplots(figsize=(7.5, 5.5))
            ax.barh([k for k, _ in top][::-1], [v for _, v in top][::-1], color="#4C78A8")
            ax.set_title(f"{name} — top 15 feature importance", fontsize=10)
            ax.tick_params(labelsize=8)
            fig.tight_layout()
            mlflow.log_figure(fig, f"importance_{name}.png")
            plt.close(fig)
            for k, v in top:
                mlflow.log_metrics({f"importance.{k}": v})

        if name == "decision_tree":
            rules = export_text(inner, feature_names=list(X.columns), max_depth=4)
            mlflow.log_text(rules, "decision_tree_rules.txt")
        try:
            mlflow.sklearn.log_model(est, name=f"model_{name}", input_example=X.iloc[:3])
        except Exception as e:  # 모델 저장 실패가 실험을 죽이지 않게
            mlflow.set_tag("d.model_log_error", str(e)[:200])

        return {"model": name, "run_id": run.info.run_id, "accuracy": acc,
                "macro_f1": f1m, "weighted_f1": f1w,
                "cv_macro_f1_mean": float(fold_f1.mean()),
                "cv_macro_f1_std": float(fold_f1.std()),
                "cv_macro_f1_ci95": [float(lo), float(hi)],
                "cv_n_folds": int(len(fold_f1)),
                "per_class": {c: {"precision": float(pi), "recall": float(ri),
                                  "f1": float(fi), "support": int(si)}
                              for c, pi, ri, fi, si in zip(classes, p, r, f, sup)},
                "confusion_matrix": cm.tolist(), "abstention": abst,
                "top_importance": sorted(importances.items(), key=lambda kv: -kv[1])[:15]}


def main() -> int:
    X, y, feats = load()
    classes = sorted(y.unique())
    counts = y.value_counts().to_dict()
    min_class = min(counts.values())
    # 최소 class n 이 split 수보다 작으면 stratify 가 깨진다. n_splits 를 그에 맞춘다.
    n_splits = max(2, min(5, min_class))
    n_repeats = 10 if len(y) < 100 else 3

    mlflow.set_tracking_uri(TRACKING_URI)
    mlflow.set_experiment(EXPERIMENT)
    head = git("rev-parse", "HEAD")
    tags = {
        "d.plane": "D_INDEPENDENT_RESEARCH_SANDBOX",
        "d.authority": "NON_AUTHORITATIVE",
        "d.branch": "claude-d/research-sandbox-v21",
        "d.head_sha": head,
        "d.base_sha": BASE_SHA,
        "d.production_modified": "false",
        "d.labels_produced": "false",
        "d.holdout_accessed": "false",
    }

    with mlflow.start_run(run_name="RQ-D3A parent") as parent:
        mlflow.set_tags({**tags, "d.rq_id": "RQ-D3A",
                         "d.rq": "L0 feature 가 frozen archetype 을 어느 정도 구분하는가 (진단)",
                         "d.target_semantics": "BUSINESS_DOMAIN_PRIOR_NOT_GOLD_LABEL"})
        mlflow.log_params({
            "n_samples": len(y), "n_features": len(feats), "n_classes": len(classes),
            "grain": "target (in_mart==1 & probe_present==1)",
            "cv": f"RepeatedStratifiedKFold({n_splits}x{n_repeats})",
            "min_class_n": min_class, "seed": SEED,
            "table_sha256": hashlib.sha256(TABLE.read_bytes()).hexdigest()[:16],
        })
        for c, n in counts.items():
            mlflow.log_metrics({f"class_n.{c.lower()}": float(n)})
        mlflow.log_metrics({"imbalance_ratio": max(counts.values()) / min_class})

        ds = mlflow.data.from_pandas(X.assign(prior_archetype=y.values), source=str(TABLE),
                                     name="D_OBSERVATION_TABLE.in_mart.probe_complete",
                                     targets="prior_archetype")
        mlflow.log_input(ds, context="diagnostic_training")

        models = {
            "baseline_majority": DummyClassifier(strategy="most_frequent"),
            "baseline_stratified": DummyClassifier(strategy="stratified", random_state=SEED),
            "decision_tree": DecisionTreeClassifier(max_depth=4, min_samples_leaf=3,
                                                    class_weight="balanced", random_state=SEED),
            "random_forest": RandomForestClassifier(n_estimators=400, min_samples_leaf=2,
                                                    class_weight="balanced_subsample",
                                                    random_state=SEED, n_jobs=1),
            "logreg_l2": Pipeline([("sc", StandardScaler()),
                                   ("clf", LogisticRegression(max_iter=4000, class_weight="balanced",
                                                              random_state=SEED))]),
        }
        results = [eval_model(n, m, X, y, classes, tags, n_splits, n_repeats)
                   for n, m in models.items()]

        learned = [r for r in results if not r["model"].startswith("baseline_")]
        best = max(learned, key=lambda r: r["macro_f1"])
        maj = next(r for r in results if r["model"] == "baseline_majority")
        strat = next(r for r in results if r["model"] == "baseline_stratified")

        # majority 대비 macro F1 lift 는 rigged 비교다. majority 는 6개 class 에서
        # recall 0 이라 macro F1 이 구조적으로 바닥이다. 정직한 기준선은 stratified 다.
        lift_maj = best["macro_f1"] - maj["macro_f1"]
        lift_strat = best["macro_f1"] - strat["macro_f1"]
        # 기준선 fold 분포와 겹치는지로 판단한다. 겹치면 구분력 주장 불가.
        overlaps = best["cv_macro_f1_ci95"][0] <= strat["cv_macro_f1_mean"] <= best["cv_macro_f1_ci95"][1]
        mlflow.log_metrics({
            "best_macro_f1": best["macro_f1"],
            "baseline_majority_macro_f1": maj["macro_f1"],
            "baseline_stratified_macro_f1": strat["macro_f1"],
            "lift_over_majority": lift_maj,
            "lift_over_stratified": lift_strat,
            "best_cv_macro_f1_mean": best["cv_macro_f1_mean"],
            "stratified_cv_macro_f1_mean": strat["cv_macro_f1_mean"],
        })
        if lift_strat > 0.15 and not overlaps:
            verdict = "SUPPORTED"
        elif lift_strat > 0.05:
            verdict = "PARTIALLY_SUPPORTED"
        else:
            verdict = "NOT_SUPPORTED"
        mlflow.set_tags({
            "d.best_model": best["model"],
            "d.verdict": verdict,
            "d.headline": (f"L0 numeric feature 만으로 archetype prior 구분: best macroF1 "
                           f"{best['macro_f1']:.3f} vs stratified baseline "
                           f"{strat['macro_f1']:.3f} (lift {lift_strat:+.3f}, n={len(y)})"),
            "d.baseline_note": "majority 대비 lift 는 macro F1 에서 rigged 이므로 헤드라인으로 쓰지 않는다",
        })

        out = {
            "rq": "RQ-D3A",
            "title": "Learned DT 진단 — L0 feature 가 archetype prior 를 어느 정도 되찾는가",
            "target_semantics": "business-domain PRIOR, gold label 아님",
            "grain": "target (in_mart==1 & probe_present==1)",
            "n": len(y), "n_features": len(feats), "features": feats,
            "class_counts": counts, "min_class_n": min_class,
            "cv": f"RepeatedStratifiedKFold(n_splits={n_splits}, n_repeats={n_repeats})",
            "seed": SEED, "parent_run_id": parent.info.run_id,
            "models": results,
            "best_model": best["model"],
            "verdict": verdict,
            "baseline_majority_macro_f1": maj["macro_f1"],
            "baseline_stratified_macro_f1": strat["macro_f1"],
            "lift_over_majority_macro_f1": lift_maj,
            "lift_over_stratified_macro_f1": lift_strat,
            "best_ci95_contains_stratified_mean": bool(overlaps),
            "baseline_note": ("majority 는 6/7 class 에서 recall 0 이라 macro F1 이 구조적으로 "
                              "바닥이다. 정직한 기준선은 stratified 다."),
            "mlflow": {"tracking_uri": TRACKING_URI, "experiment": EXPERIMENT},
        }
        (RD / "results" / "RQ_D3A_learned_dt.json").write_text(
            json.dumps(out, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")

    print(f"n={len(y)} features={len(feats)} classes={len(classes)} cv={n_splits}x{n_repeats}")
    for r in sorted(results, key=lambda r: -r["macro_f1"]):
        print(f"  {r['model']:<22} acc={r['accuracy']:.3f}  macroF1={r['macro_f1']:.3f}  "
              f"weightedF1={r['weighted_f1']:.3f}")
    print(f"best(learned)={best['model']}  macroF1={best['macro_f1']:.3f}")
    print(f"  vs majority   {maj['macro_f1']:.3f}  lift {best['macro_f1']-maj['macro_f1']:+.3f}  (rigged)")
    print(f"  vs stratified {strat['macro_f1']:.3f}  lift {best['macro_f1']-strat['macro_f1']:+.3f}  <- 판정 기준")
    print(f"  best CI95 {best['cv_macro_f1_ci95'][0]:.3f}~{best['cv_macro_f1_ci95'][1]:.3f} "
          f"| stratified mean {strat['cv_macro_f1_mean']:.3f} | 겹침={overlaps}")
    print(f"verdict = {verdict}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
