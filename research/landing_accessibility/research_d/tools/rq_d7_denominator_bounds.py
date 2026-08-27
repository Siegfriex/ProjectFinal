"""RQ-D7 — mart 분모 축소가 계획된 association 추정에 주는 영향의 상한.

complete-case 점추정이 아니라 **결측이 최악으로 배치됐을 때의 Manski worst-case bound** 를
계산한다. 결정·threshold·재수집 권고는 하지 않는다 (A 권한). "bound 는 X 다" 까지만.

용어 규율
---------
* 59 -> 56 의 3건은 **원장에 사유가 기록된 제외**(SKIPPED_RETRY_EXHAUSTED)다. 조용한 소실이
  아니다. RQ-D1 초기 보고가 "조용히 사라진다" 라고 잘못 말했다가 RQ-D13c 에서 시정됐다.
* 56 -> 31 의 25건은 **원장에 사유가 기록된 제외**(ACCOUNT_ACTION_BLOCKED 가설, 본 스크립트가
  독립 확인)다.
* 56 안에서 probe 가 없는 2건은 **사유가 원장에 기록되지 않은 covariate 결측**이다.
* 66 -> 59 는 결측층이 아니라 **관측 grain 붕괴**(반복 실행 7건)다. target grain 에서는 분모가
  줄지 않는다.
* prior_* 는 gold label 이 아니라 prior 다. accuracy 라는 말을 쓰지 않는다.
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

sys.path.insert(0, str(Path(__file__).resolve().parent))
import mlflow_contract as mc  # noqa: E402
import mlflow  # noqa: E402

KST = timezone(timedelta(hours=9))
RD = Path("/home/sieg/projects-wsl/ProjectFinal/.agent_worktrees/claude_d_research/"
          "research/landing_accessibility/research_d")
WT = Path("/home/sieg/projects-wsl/ProjectFinal/.agent_worktrees")
MART = WT / "claude_b_analysis_current/artifacts/e001_real_marts"
OBS_CSV = RD / "results" / "D_OBSERVATION_TABLE_v2.csv"
OUT_JSON = RD / "results" / "RQ_D7_denominator_bounds.json"
FIG = RD / "figures"
SEED = 20260828
NPERM = 20000
RNG = np.random.default_rng(SEED)

# 커머스 계열 정의 — 본 RQ 에서 사전 고정한다.
COMMERCE_PRIMARY = {"SHOPPING_COMMERCE"}
COMMERCE_WIDE = {"SHOPPING_COMMERCE", "FINANCE_PAYMENT"}


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


# ---------------------------------------------------------------- 1. 입력
def load_inputs() -> tuple[dict, pd.DataFrame, list, list, dict]:
    inputs = {}
    obs = pd.read_csv(OBS_CSV)
    inputs["D_OBSERVATION_TABLE_v2.csv"] = {"path": str(OBS_CSV), "sha256": sha256_file(OBS_CSV),
                                            "rows": int(len(obs)), "cols": int(obs.shape[1])}
    landing = json.loads((MART / "fact_landing_observation.json").read_text())
    task = json.loads((MART / "fact_task_entry.json").read_text())
    summary = json.loads((MART / "REAL_RUN_SUMMARY.json").read_text())
    for f in ("fact_landing_observation.json", "fact_task_entry.json",
              "fact_interrupt_element.json", "REAL_RUN_SUMMARY.json",
              "FROZEN_MART_MANIFEST.json"):
        p = MART / f
        inputs[f] = {"path": str(p), "sha256": sha256_file(p),
                     "rows": len(json.loads(p.read_text())) if f.startswith("fact_") else None}
    for prior in ("RQ_D1_reconstruction.json", "RQ_D11_ledger_vs_evidence.json",
                  "RQ_D13C_mart_row_dropping.json", "RQ_D8_cap_bias.json"):
        p = RD / "results" / prior
        if p.exists():
            inputs[prior] = {"path": str(p), "sha256": sha256_file(p),
                             "role": "prior D output — hypothesis only, independently recomputed"}
    return inputs, obs, landing, task, summary


def load_ledger() -> tuple[pd.DataFrame, dict]:
    """워커 batch 원장에서 target 별 outcome 을 독립 재구성한다."""
    rows, files = [], []
    for wdir in sorted(WT.glob("claude_b_e001_worker_0*/artifacts/e001_w0*")):
        worker = wdir.name.replace("e001_", "")
        for bf in sorted((wdir / "batches").glob("*.json")):
            files.append({"path": str(bf), "sha256": sha256_file(bf)})
            doc = json.loads(bf.read_text())
            for r in doc.get("results", []):
                d = r.get("detail") or {}
                rows.append({
                    "worker": worker,
                    "wtg": str(r.get("web_target_id") or r.get("target_id") or "").replace("wtg_", ""),
                    "ledger_outcome": r.get("outcome") or d.get("endpoint_status"),
                    "ledger_attempts": r.get("attempts"),
                    "ledger_has_l0": bool(d.get("l0")),
                    "ledger_has_task_key": bool(d.get("task_observation_id") or d.get("endpoint_status")),
                    "ledger_blocked_category": (d.get("blocked_category")
                                                or (r.get("detail") or {}).get("blocked_category")),
                    "ledger_endpoint_status": d.get("endpoint_status"),
                    "ledger_archetype": d.get("archetype"),
                    "batch_id": doc.get("batch_id"),
                })
    return pd.DataFrame(rows), {"n_batch_files": len(files), "files": files}


# ------------------------------------------------- 2. 분모 사슬 독립 재계산
def denominator_chain(obs, landing, task, summary, ledger) -> dict:
    dirs_fs = []
    for wdir in sorted(WT.glob("claude_b_e001_worker_0*/artifacts/e001_w0*/evidence")):
        worker = wdir.parent.name.replace("e001_", "")
        for d in sorted(wdir.iterdir()):
            if not d.is_dir():
                continue
            m = re.match(r"e001_full-wtg_([0-9a-f]+)-(.+)$", d.name)
            n_files = sum(1 for _ in d.rglob("*") if _.is_file())
            dirs_fs.append({"worker": worker, "dir": d.name,
                            "wtg": m.group(1) if m else None, "ts": m.group(2) if m else None,
                            "n_files": n_files, "sealed": bool(n_files)})
    fs = pd.DataFrame(dirs_fs)

    wtg_fs = set(fs.wtg)
    wtg_obs = set(obs.wtg)
    wtg_ledger = set(ledger.wtg)
    wtg_landing = {r["web_target_id"].replace("wtg_", "") for r in landing}
    wtg_task = {r["web_target_id"].replace("wtg_", "") for r in task}
    repeats = {w: sorted(g["dir"]) for w, g in fs.groupby("wtg") if len(g) > 1}
    sealed_by_wtg = {w: sorted(g["sealed"]) for w, g in fs.groupby("wtg")}
    dup_launch = sorted(w for w in repeats if all(sealed_by_wtg[w]))
    retry_empty = sorted(w for w in repeats if not any(sealed_by_wtg[w]))

    cm = summary["collection_markers"]["analysis_sample"]
    return {
        "grain_warning": ("observation_dir grain 과 target(wtg) grain 은 다른 분모다. "
                          "fact_task_entry 는 target 당 1행(31행/31 target)이므로 target grain 이다 — "
                          "step grain 이 아니다."),
        "step_0_observation_dirs": {
            "n": int(len(fs)), "source": "filesystem enumeration of evidence/e001_full-wtg_*",
            "per_worker": {k: int(v) for k, v in fs.worker.value_counts().sort_index().items()},
            "sealed_dirs": int(fs.sealed.sum()), "empty_dirs": int((~fs.sealed).sum()),
        },
        "step_1_distinct_targets": {
            "n": len(wtg_fs), "source": "distinct wtg over the same dirs",
            "delta_from_step_0": int(len(fs) - len(wtg_fs)),
            "delta_kind": "GRAIN_COLLAPSE_NOT_MISSINGNESS",
            "repeat_targets": {w: repeats[w] for w in sorted(repeats)},
            "duplicate_launch_both_sealed": dup_launch,
            "retry_both_empty": retry_empty,
            "cross_check_summary_attempted_observations": cm["attempted_observations"],
            "cross_check_summary_unique_targets": cm["unique_targets"],
            "agrees_with_summary": len(wtg_fs) == cm["unique_targets"],
        },
        "step_2_landing_mart_rows": {
            "n": len(landing), "distinct_wtg": len(wtg_landing),
            "delta_from_step_1": len(wtg_fs) - len(wtg_landing),
            "delta_kind": "LEDGER_RECORDED_EXCLUSION",
            "excluded_wtg": sorted(wtg_fs - wtg_landing),
            "ledger_reason": {w: sorted(set(ledger.loc[ledger.wtg == w, "ledger_outcome"].dropna()))
                              for w in sorted(wtg_fs - wtg_landing)},
            "recorded_in_summary_as": {"skipped_retry_exhausted_n":
                                       summary["collection_markers"]["skipped_retry_exhausted_n"]},
            "not_silent": True,
        },
        "step_3_task_mart_rows": {
            "n": len(task), "distinct_wtg": len(wtg_task),
            "rows_per_target": round(len(task) / max(len(wtg_task), 1), 4),
            "delta_from_step_2": len(wtg_landing) - len(wtg_task),
            "delta_kind": "LEDGER_RECORDED_EXCLUSION (mechanism verified below)",
            "excluded_wtg": sorted(wtg_landing - wtg_task),
            "task_subset_of_landing": wtg_task <= wtg_landing,
        },
        "step_2b_within_mart_covariate_missing": {
            "n_targets_in_landing_mart_without_probe": int((obs[obs.in_mart == 1].probe_present != 1).sum()),
            "wtg": sorted(obs.loc[(obs.in_mart == 1) & (obs.probe_present != 1), "wtg"]),
            "delta_kind": "UNRECORDED_COVARIATE_MISSING",
            "note": ("이 2건은 landing mart 에 행이 있으나 probe.json 이 없어 probe 파생 covariate "
                     "(cap_*, modal_overlay_n, gate_*)가 전부 결측이다. 원장 outcome 에는 사유가 "
                     "기록돼 있지 않다 — 위 두 제외층과 성격이 다르다."),
        },
        "set_consistency": {
            "fs_wtg_equals_obs_table_wtg": wtg_fs == wtg_obs,
            "fs_wtg_equals_ledger_wtg": wtg_fs == wtg_ledger,
            "obs_in_mart_flag_equals_landing_set":
                set(obs.loc[obs.in_mart == 1, "wtg"]) == wtg_landing,
        },
    }


# ------------------------------------------------------------ 3. target frame
BIN_COVS = ["dom_body_empty", "probe_present", "has_l0c", "article_present", "body_scroll_locked",
            "cap_any", "cap_primary_action_candidates", "cap_accessible_name_sources",
            "cap_target_size", "cap_contrast", "cap_motion_animated_60", "cap_body_text_4000"]
CONT_COVS = ["dom_bytes", "ax_bytes", "css_bytes", "dom_element_n", "dom_body_element_n",
             "dom_interactive_n", "dom_a_href_n", "dom_button_n", "dom_input_n", "dom_role_n",
             "dom_aria_label_n", "dom_script_n", "dom_body_text_len", "probe_scroll_height",
             "modal_overlay_n", "dismiss_control_n", "search_inputs_n", "declared_regions_n",
             "declared_endpoints_n", "motion_animated_n", "gate_password_input_n",
             "gate_captcha_iframe_n", "gate_visible_text_len", "n_primary_action_candidates",
             "n_accessible_name_sources", "n_target_size", "n_contrast", "cap_count"]
CAT_COVS = ["worker", "prior_business_domain", "prior_archetype", "prior_mapping_status",
            "prior_endpoint_signal_type", "prior_region_signal_type"]
ALWAYS_OBSERVED_CAT = CAT_COVS


def build_frame(obs, landing, task, ledger) -> pd.DataFrame:
    """target grain frame (59행). in_mart 행을 canonical 로 삼는다."""
    canon = obs.sort_values(["wtg", "in_mart", "run_ts"], ascending=[True, False, True])
    canon = canon.drop_duplicates("wtg", keep="first").set_index("wtg")
    wtg_landing = {r["web_target_id"].replace("wtg_", "") for r in landing}
    task_by = {r["web_target_id"].replace("wtg_", ""): r for r in task}
    ledg = ledger.drop_duplicates("wtg").set_index("wtg")

    f = canon.copy()
    f["has_evidence"] = f.index.isin(wtg_landing).astype(int)
    f["has_task_row"] = f.index.isin(task_by).astype(int)
    n_dirs = obs.groupby("wtg").size()
    f["n_dirs"] = n_dirs.reindex(f.index).astype(int)
    f["is_repeat_target"] = (f["n_dirs"] > 1).astype(int)
    f["is_duplicate_launch"] = ((f["n_dirs"] > 1) & (f["has_evidence"] == 1)).astype(int)
    for c in ("ledger_outcome", "ledger_attempts", "ledger_blocked_category"):
        f[c] = ledg[c].reindex(f.index)
    f["ledger_account_action_blocked"] = (f.ledger_outcome == "ACCOUNT_ACTION_BLOCKED").astype(int)
    for k, col in (("endpoint_status", "task_endpoint_status"),
                   ("auth_gate_before_endpoint", "task_auth_gate_before_endpoint"),
                   ("endpoint_reached", "task_endpoint_reached"),
                   ("interaction_archetype", "task_interaction_archetype"),
                   ("forced_dismissal_count", "task_forced_dismissal_count")):
        f[col] = [task_by.get(w, {}).get(k) for w in f.index]
    for c in ("task_auth_gate_before_endpoint", "task_endpoint_reached"):
        f[c] = pd.to_numeric(f[c], errors="coerce")
    f["commerce_primary"] = f.prior_business_domain.isin(COMMERCE_PRIMARY).astype(int)
    f["commerce_wide"] = f.prior_business_domain.isin(COMMERCE_WIDE).astype(int)
    return f


# ------------------------------------------------- 4. 결측 기전 진단 도구
def phi_perm(x: np.ndarray, y: np.ndarray, nperm=NPERM, rng=None) -> dict:
    rng = rng or np.random.default_rng(SEED)
    ok = ~(pd.isna(x) | pd.isna(y))
    x, y = np.asarray(x, float)[ok], np.asarray(y, float)[ok]
    n = len(x)
    if n < 4 or len(set(x)) < 2 or len(set(y)) < 2:
        return {"stat": None, "p": None, "n": int(n), "reason": "degenerate"}
    phi = float(np.corrcoef(x, y)[0, 1])
    perm = np.array([abs(np.corrcoef(rng.permutation(x), y)[0, 1]) for _ in range(nperm)])
    p = float((np.sum(perm >= abs(phi) - 1e-12) + 1) / (nperm + 1))
    return {"stat": round(phi, 4), "p": round(p, 5), "n": int(n), "test": "phi + permutation"}


def mwu(x: np.ndarray, g: np.ndarray) -> dict:
    ok = ~pd.isna(x)
    x, g = np.asarray(x, float)[ok], np.asarray(g)[ok]
    a, b = x[g == 1], x[g == 0]
    if len(a) < 2 or len(b) < 2 or len(set(x)) < 2:
        return {"stat": None, "p": None, "n1": int(len(a)), "n0": int(len(b)), "reason": "degenerate"}
    u, p = stats.mannwhitneyu(a, b, alternative="two-sided")
    auc = float(u / (len(a) * len(b)))
    return {"stat": round(auc, 4), "p": round(float(p), 5), "n1": int(len(a)), "n0": int(len(b)),
            "median_1": float(np.median(a)), "median_0": float(np.median(b)),
            "test": "Mann-Whitney U (stat = rank-biserial AUC)"}


def cramers_v_perm(cat: pd.Series, g: np.ndarray, nperm=NPERM, rng=None) -> dict:
    rng = rng or np.random.default_rng(SEED)
    ok = ~pd.isna(cat)
    c, gg = np.asarray(cat)[ok], np.asarray(g)[ok]
    tab = pd.crosstab(pd.Series(c), pd.Series(gg))
    if tab.shape[0] < 2 or tab.shape[1] < 2:
        return {"stat": None, "p": None, "n": int(len(c)), "reason": "degenerate"}

    def v(t):
        chi2 = stats.chi2_contingency(t, correction=False)[0]
        n = t.values.sum()
        return float(np.sqrt(chi2 / (n * (min(t.shape) - 1))))
    obs_v = v(tab)
    cnt = 0
    for _ in range(nperm):
        t = pd.crosstab(pd.Series(rng.permutation(c)), pd.Series(gg))
        if t.shape[0] > 1 and t.shape[1] > 1 and v(t) >= obs_v - 1e-12:
            cnt += 1
    return {"stat": round(obs_v, 4), "p": round((cnt + 1) / (nperm + 1), 5), "n": int(len(c)),
            "levels": int(tab.shape[0]), "test": "Cramer's V + permutation"}


def bh_fdr(pvals: list[float | None], alpha=0.05) -> list[float | None]:
    idx = [i for i, p in enumerate(pvals) if p is not None]
    m = len(idx)
    out: list[float | None] = [None] * len(pvals)
    if not m:
        return out
    order = sorted(idx, key=lambda i: pvals[i])
    prev = 1.0
    for rank, i in enumerate(reversed(order), start=1):
        q = min(prev, pvals[i] * m / (m - rank + 1))
        out[i] = round(min(q, 1.0), 5)
        prev = out[i]
    return out


def diagnose_layer(df: pd.DataFrame, indicator: str, label: str, bins, conts, cats,
                   note: str, rng) -> dict:
    g = df[indicator].to_numpy(float)
    tests = []
    for c in cats:
        if c in df:
            r = cramers_v_perm(df[c], g, rng=rng); r.update(covariate=c, kind="categorical"); tests.append(r)
    for c in bins:
        if c in df:
            r = phi_perm(df[c].to_numpy(float), g, rng=rng); r.update(covariate=c, kind="binary"); tests.append(r)
    for c in conts:
        if c in df:
            r = mwu(df[c].to_numpy(float), g); r.update(covariate=c, kind="continuous"); tests.append(r)
    qs = bh_fdr([t["p"] for t in tests])
    for t, q in zip(tests, qs):
        t["q_bh"] = q
        t["significant_bh05"] = bool(q is not None and q < 0.05)
    sig = [t["covariate"] for t in tests if t["significant_bh05"]]
    n_test = sum(1 for t in tests if t["p"] is not None)
    return {
        "layer": label, "indicator": indicator, "universe_n": int(len(df)),
        "n_flagged": int(g.sum()), "n_not_flagged": int(len(g) - g.sum()),
        "note": note, "n_tests_run": n_test,
        "n_degenerate_skipped": len(tests) - n_test,
        "n_significant_bh05": len(sig), "significant_covariates": sig,
        "verdict": ("ASSOCIATION_DETECTED" if sig else
                    ("NO_ASSOCIATION_DETECTED_BUT_UNDERPOWERED" if n_test else "NOT_TESTABLE")),
        "tests": sorted(tests, key=lambda t: (t["p"] is None, t["p"])),
    }


# --------------------------------------------------------------- 5. bounds
def wilson(k: int, n: int, z=1.959963985) -> tuple[float, float]:
    if n == 0:
        return (0.0, 1.0)
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (max(0.0, c - h), min(1.0, c + h))


def newcombe_rd(a, b, c, d) -> tuple[float, float]:
    """RD = p1 - p2 의 Newcombe hybrid-score 95% CI. p1 = a/(a+b), p2 = c/(c+d)."""
    n1, n2 = a + b, c + d
    if n1 == 0 or n2 == 0:
        return (-1.0, 1.0)
    p1, p2 = a / n1, c / n2
    l1, u1 = wilson(a, n1)
    l2, u2 = wilson(c, n2)
    lo = (p1 - p2) - np.sqrt((p1 - l1) ** 2 + (u2 - p2) ** 2)
    hi = (p1 - p2) + np.sqrt((u1 - p1) ** 2 + (p2 - l2) ** 2)
    return (max(-1.0, lo), min(1.0, hi))


def _rd_phi(a, b, c, d):
    n1, n2 = a + b, c + d
    if n1 == 0 or n2 == 0:
        return None, None
    rd = a / n1 - c / n2
    num = a * d - b * c
    den = np.sqrt(float(n1) * n2 * (a + c) * (b + d))
    return rd, (float(num / den) if den > 0 else None)


def manski_bounds(x, y) -> dict:
    """x, y in {0,1,nan}. 결측이 최악으로 배치됐을 때의 RD/phi 하한·상한을 완전열거로 구한다."""
    x = np.asarray(x, float); y = np.asarray(y, float)
    kx, ky = ~np.isnan(x), ~np.isnan(y)
    a = int(np.sum(kx & ky & (x == 1) & (y == 1)))
    b = int(np.sum(kx & ky & (x == 1) & (y == 0)))
    c = int(np.sum(kx & ky & (x == 0) & (y == 1)))
    d = int(np.sum(kx & ky & (x == 0) & (y == 0)))
    m_x1 = int(np.sum(kx & ~ky & (x == 1)))     # X=1, Y 결측 -> a or b
    m_x0 = int(np.sum(kx & ~ky & (x == 0)))     # X=0, Y 결측 -> c or d
    m_y1 = int(np.sum(~kx & ky & (y == 1)))     # Y=1, X 결측 -> a or c
    m_y0 = int(np.sum(~kx & ky & (y == 0)))     # Y=0, X 결측 -> b or d
    m_bb = int(np.sum(~kx & ~ky))               # 둘 다 결측 -> a|b|c|d
    best = {"rd_min": None, "rd_max": None, "phi_min": None, "phi_max": None}
    arg = {}
    for i in range(m_x1 + 1):
        for j in range(m_x0 + 1):
            for k in range(m_y1 + 1):
                for l in range(m_y0 + 1):
                    for p in range(m_bb + 1):
                        for q in range(m_bb - p + 1):
                            for r in range(m_bb - p - q + 1):
                                s = m_bb - p - q - r
                                A = a + i + k + p
                                B = b + (m_x1 - i) + l + q
                                C = c + j + (m_y1 - k) + r
                                D = d + (m_x0 - j) + (m_y0 - l) + s
                                rd, phi = _rd_phi(A, B, C, D)
                                if rd is None:
                                    continue
                                if best["rd_min"] is None or rd < best["rd_min"]:
                                    best["rd_min"] = rd; arg["rd_min"] = (A, B, C, D)
                                if best["rd_max"] is None or rd > best["rd_max"]:
                                    best["rd_max"] = rd; arg["rd_max"] = (A, B, C, D)
                                if phi is not None:
                                    if best["phi_min"] is None or phi < best["phi_min"]:
                                        best["phi_min"] = phi
                                    if best["phi_max"] is None or phi > best["phi_max"]:
                                        best["phi_max"] = phi
    rd_cc, phi_cc = _rd_phi(a, b, c, d)
    lo, hi = newcombe_rd(a, b, c, d)
    n_missing = m_x1 + m_x0 + m_y1 + m_y0 + m_bb
    return {
        "complete_case": {
            "table_a_x1y1": a, "table_b_x1y0": b, "table_c_x0y1": c, "table_d_x0y0": d,
            "n_complete": a + b + c + d,
            "p_y1_given_x1": round(a / (a + b), 4) if a + b else None,
            "wilson95_y1_given_x1": [round(v, 4) for v in wilson(a, a + b)] if a + b else None,
            "p_y1_given_x0": round(c / (c + d), 4) if c + d else None,
            "wilson95_y1_given_x0": [round(v, 4) for v in wilson(c, c + d)] if c + d else None,
            "risk_difference": round(rd_cc, 4) if rd_cc is not None else None,
            "rd_newcombe95": [round(lo, 4), round(hi, 4)],
            "rd_newcombe95_width": round(hi - lo, 4),
            "phi": round(phi_cc, 4) if phi_cc is not None else None,
        },
        "missing_breakdown": {"x1_y_missing": m_x1, "x0_y_missing": m_x0,
                              "y1_x_missing": m_y1, "y0_x_missing": m_y0,
                              "both_missing": m_bb, "n_missing_total": n_missing},
        "worst_case_bound": {
            "rd_lower": round(best["rd_min"], 4), "rd_upper": round(best["rd_max"], 4),
            "rd_width": round(best["rd_max"] - best["rd_min"], 4),
            "rd_lower_witness_table": arg.get("rd_min"), "rd_upper_witness_table": arg.get("rd_max"),
            "phi_lower": round(best["phi_min"], 4) if best["phi_min"] is not None else None,
            "phi_upper": round(best["phi_max"], 4) if best["phi_max"] is not None else None,
            "excludes_null_rd0": bool(best["rd_min"] > 0 or best["rd_max"] < 0),
            "sign_identified": bool(best["rd_min"] > 0 or best["rd_max"] < 0),
        },
        "width_ratio_bound_over_cc_ci": round((best["rd_max"] - best["rd_min"]) / (hi - lo), 3)
        if hi > lo else None,
    }


# ------------------------------------------------- 6. association 정의
def assoc_vectors(f: pd.DataFrame, key: str) -> tuple[np.ndarray, np.ndarray, dict]:
    """(x, y, meta). nan = 결측. 전부 target grain, n=59."""
    if key == "a_cap_any_x_commerce":
        x = f["commerce_primary"].to_numpy(float)
        y = f["cap_any"].to_numpy(float)
        meta = {"X": "prior_business_domain == SHOPPING_COMMERCE (커머스 계열, 본 RQ 사전 고정)",
                "Y": "cap_any == 1 (측정 cap 절단이 하나라도 걸림)",
                "derived_from": "RQ-D8",
                "x_missing_source": "none — prior 표는 59 target 전부 보유",
                "y_missing_source": "L2(3, 원장기록 제외) + L2b(2, probe 부재 covariate 결측)"}
    elif key == "b_modal_x_no_arialabel":
        x = np.where(np.isnan(f["dom_aria_label_n"].to_numpy(float)), np.nan,
                     (f["dom_aria_label_n"].to_numpy(float) == 0).astype(float))
        y = np.where(np.isnan(f["modal_overlay_n"].to_numpy(float)), np.nan,
                     (f["modal_overlay_n"].to_numpy(float) > 0).astype(float))
        meta = {"X": "dom_aria_label_n == 0", "Y": "modal_overlay_n > 0",
                "derived_from": "PILOT-E E-P2",
                "x_missing_source": "L2(3) — DOM 이 없는 target",
                "y_missing_source": "L2(3) + L2b(2) — probe 파생"}
    elif key == "c_taskrow_x_password_gate":
        x = np.where(np.isnan(f["gate_password_input_n"].to_numpy(float)), np.nan,
                     (f["gate_password_input_n"].to_numpy(float) > 0).astype(float))
        y = f["has_task_row"].to_numpy(float)
        meta = {"X": "gate_password_input_n > 0", "Y": "fact_task_entry 에 행이 존재",
                "derived_from": "RQ-D6b",
                "x_missing_source": "L2(3) + L2b(2)",
                "y_missing_source": "none — 결측 자체가 결과변수라 59 전부 관측된다",
                "caveat": ("Y 는 mart 포함 여부다. '결측이 결과' 인 association 이므로 "
                           "L3 은 이 추정치에서 결측층이 아니라 결과의 분포다.")}
    elif key == "d_authgate_x_commerce":
        x = f["commerce_primary"].to_numpy(float)
        y = f["task_auth_gate_before_endpoint"].to_numpy(float)
        meta = {"X": "prior_business_domain == SHOPPING_COMMERCE",
                "Y": "fact_task_entry.auth_gate_before_endpoint == 1",
                "derived_from": "RQ-D7 자체 추가 — task mart 를 결과로 쓰는 계획된 association 대표",
                "x_missing_source": "none",
                "y_missing_source": "L2(3) + L3(25) = 28 — task mart 에 행이 없으면 정의되지 않는다",
                "why_added": ("(a)(b)(c) 는 전부 L2/L2b 만 결측이라 3~5건 문제다. "
                              "56->31 의 25건이 실제로 무는 곳을 보여주려면 결과가 task mart 인 "
                              "association 이 하나 필요하다.")}
    else:
        raise KeyError(key)
    return x, y, meta


LAYER_MEMBERS_FN = {
    "L2_ledger_recorded_no_evidence": lambda f: list(f.index[f.has_evidence == 0]),
    "L2b_unrecorded_probe_absent": lambda f: list(f.index[(f.has_evidence == 1) & (f.probe_present != 1)]),
    "L3_ledger_recorded_no_task_row": lambda f: list(f.index[(f.has_evidence == 1) & (f.has_task_row == 0)]),
}


def impute_recover(f, x, y, members) -> tuple[np.ndarray, np.ndarray]:
    """지정한 layer 의 target 을 '복구' 했다고 두고 결측을 CC 조건부 비율로 결정론적 채움.

    bound 폭은 남아 있는 결측 수에 지배되며 채움값 선택에 거의 무관하다 — 중심만 채움에 의존한다.
    이 가정은 JSON limitation 에 명시한다.
    """
    x, y = x.copy(), y.copy()
    idx = {w: i for i, w in enumerate(f.index)}
    pos = sorted(idx[w] for w in members if w in idx)
    kx, ky = ~np.isnan(x), ~np.isnan(y)
    px = float(np.nanmean(x)) if kx.any() else 0.5
    both = kx & ky
    p_y_x1 = float(y[both & (x == 1)].mean()) if (both & (x == 1)).any() else 0.5
    p_y_x0 = float(y[both & (x == 0)].mean()) if (both & (x == 0)).any() else 0.5
    for rank, i in enumerate(pos):
        if np.isnan(x[i]):
            x[i] = 1.0 if ((rank % 100) / 100.0) < px else 0.0
        if np.isnan(y[i]):
            p = p_y_x1 if x[i] == 1 else p_y_x0
            y[i] = 1.0 if ((rank % 100) / 100.0) < p else 0.0
    return x, y


def layer_decomposition(f: pd.DataFrame, key: str) -> dict:
    x0, y0, meta = assoc_vectors(f, key)
    layers = {k: fn(f) for k, fn in LAYER_MEMBERS_FN.items()}
    base = manski_bounds(x0, y0)
    scen = {"S0_nothing_recovered": {
        "recovered_layers": [], "n_recovered_targets": 0,
        "n_missing_remaining": base["missing_breakdown"]["n_missing_total"],
        "rd_bound": [base["worst_case_bound"]["rd_lower"], base["worst_case_bound"]["rd_upper"]],
        "rd_width": base["worst_case_bound"]["rd_width"],
        "sign_identified": base["worst_case_bound"]["sign_identified"]}}
    for name, members in layers.items():
        xr, yr = impute_recover(f, x0, y0, members)
        r = manski_bounds(xr, yr)
        scen[f"S_{name}_only"] = {
            "recovered_layers": [name], "n_recovered_targets": len(members),
            "n_missing_remaining": r["missing_breakdown"]["n_missing_total"],
            "rd_bound": [r["worst_case_bound"]["rd_lower"], r["worst_case_bound"]["rd_upper"]],
            "rd_width": r["worst_case_bound"]["rd_width"],
            "width_reduction_vs_S0": round(base["worst_case_bound"]["rd_width"]
                                           - r["worst_case_bound"]["rd_width"], 4),
            "sign_identified": r["worst_case_bound"]["sign_identified"]}
    allm = sorted({w for m in layers.values() for w in m})
    xa, ya = impute_recover(f, x0, y0, allm)
    ra = manski_bounds(xa, ya)
    scen["S_all_recovered"] = {
        "recovered_layers": list(layers), "n_recovered_targets": len(allm),
        "n_missing_remaining": ra["missing_breakdown"]["n_missing_total"],
        "rd_bound": [ra["worst_case_bound"]["rd_lower"], ra["worst_case_bound"]["rd_upper"]],
        "rd_width": ra["worst_case_bound"]["rd_width"],
        "width_reduction_vs_S0": round(base["worst_case_bound"]["rd_width"]
                                       - ra["worst_case_bound"]["rd_width"], 4),
        "sign_identified": ra["worst_case_bound"]["sign_identified"]}
    contrib = {k: v.get("width_reduction_vs_S0") for k, v in scen.items() if k.startswith("S_") and "only" in k}
    dom = max(contrib, key=lambda k: contrib[k]) if contrib else None
    return {"association": key, "meta": meta, "scenarios": scen,
            "dominant_layer": dom,
            "dominant_layer_width_reduction": contrib.get(dom) if dom else None,
            "answer_3_vs_25": (
                "이 association 의 결측은 전부 L2/L2b(<=5건)이므로 25건은 무관하다"
                if base["missing_breakdown"]["n_missing_total"] <= 5 else
                "이 association 은 L3 25건이 결측의 대부분을 차지한다")}


# --------------------------------------- 7. L1 반복실행의 측정 모호성
def l1_canonical_ambiguity(obs: pd.DataFrame) -> dict:
    """중복발사 4 target 에서 canonical dir 선택이 bound 변수 값을 바꾸는가."""
    bound_vars = ["cap_any", "dom_aria_label_n", "modal_overlay_n", "gate_password_input_n",
                  "probe_present", "dom_body_empty"]
    out = {}
    for w, g in obs.groupby("wtg"):
        if len(g) < 2 or g.sealed.sum() == 0:
            continue
        rec = {}
        for v in bound_vars:
            vals = list(g[v])
            same = (vals[0] == vals[1]) or (pd.isna(vals[0]) and pd.isna(vals[1]))
            rec[v] = {"values": [None if pd.isna(x) else float(x) for x in vals], "identical": bool(same)}
        derived = {
            "X_b_aria0": sorted({None if pd.isna(v) else bool(v == 0) for v in g.dom_aria_label_n}),
            "Y_b_modal_gt0": sorted({None if pd.isna(v) else bool(v > 0) for v in g.modal_overlay_n},
                                    key=str),
            "X_c_password_gt0": sorted({None if pd.isna(v) else bool(v > 0) for v in g.gate_password_input_n},
                                       key=str),
            "Y_a_cap_any": sorted({None if pd.isna(v) else bool(v == 1) for v in g.cap_any}, key=str),
        }
        rec["derived_binary_flips"] = {k: len(v) > 1 for k, v in derived.items()}
        rec["any_bound_variable_flips"] = any(rec["derived_binary_flips"].values())
        out[w] = rec
    n_flip = sum(1 for v in out.values() if v["any_bound_variable_flips"])
    return {"n_duplicate_launch_targets_checked": len(out),
            "n_with_bound_variable_flip": n_flip,
            "contribution_to_bound_width": ("0 — canonical dir 선택은 본 RQ 의 bound 변수 4개 중"
                                            " 어느 것도 뒤집지 않는다" if n_flip == 0 else
                                            "비영 — canonical 선택이 bound 변수를 뒤집는 target 이 있다"),
            "per_target": out}
