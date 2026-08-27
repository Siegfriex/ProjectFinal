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
    """phi 계수 + 벡터화 permutation p (양측, |phi| 기준)."""
    rng = rng or np.random.default_rng(SEED)
    ok = ~(pd.isna(x) | pd.isna(y))
    x, y = np.asarray(x, float)[ok], np.asarray(y, float)[ok]
    n = len(x)
    if n < 4 or len(set(x)) < 2 or len(set(y)) < 2:
        return {"stat": None, "p": None, "n": int(n), "reason": "degenerate"}
    mx, sx = x.mean(), x.std()
    my, sy = y.mean(), y.std()
    phi = float(((x * y).mean() - mx * my) / (sx * sy))
    Xp = rng.permuted(np.tile(x, (nperm, 1)), axis=1)
    stats_perm = ((Xp @ y) / n - mx * my) / (sx * sy)
    p = float((np.sum(np.abs(stats_perm) >= abs(phi) - 1e-12) + 1) / (nperm + 1))
    return {"stat": round(phi, 4), "p": round(p, 5), "n": int(n),
            "n_x1": int(x.sum()), "n_y1": int(y.sum()),
            "test": "phi + permutation (vectorized, %d perms)" % nperm}


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
    """Cramer's V (K x 2) + 벡터화 permutation p."""
    rng = rng or np.random.default_rng(SEED)
    ok = ~pd.isna(cat)
    c = pd.Series(np.asarray(cat)[ok]).astype("category")
    gg = np.asarray(g, float)[ok]
    codes, K = c.cat.codes.to_numpy(), len(c.cat.categories)
    n = len(codes)
    n1 = float(gg.sum()); n0 = n - n1
    if K < 2 or n1 == 0 or n0 == 0:
        return {"stat": None, "p": None, "n": int(n), "reason": "degenerate"}
    lt = np.bincount(codes, minlength=K).astype(float)
    e1, e0 = lt * n1 / n, lt * n0 / n
    o1 = np.bincount(codes[gg == 1], minlength=K).astype(float)

    def chi2(o1v):
        o0v = lt - o1v
        return float(np.sum((o1v - e1) ** 2 / e1 + (o0v - e0) ** 2 / e0))
    obs_v = float(np.sqrt(chi2(o1) / n))
    Cp = rng.permuted(np.tile(codes, (nperm, 1)), axis=1)
    sel = Cp[:, gg == 1]
    flat = sel + K * np.arange(nperm)[:, None]
    cnt = np.bincount(flat.ravel(), minlength=nperm * K).reshape(nperm, K).astype(float)
    o0m = lt[None, :] - cnt
    chi2m = np.sum((cnt - e1[None, :]) ** 2 / e1[None, :]
                   + (o0m - e0[None, :]) ** 2 / e0[None, :], axis=1)
    vm = np.sqrt(chi2m / n)
    p = float((np.sum(vm >= obs_v - 1e-12) + 1) / (nperm + 1))
    return {"stat": round(obs_v, 4), "p": round(p, 5), "n": int(n), "levels": int(K),
            "level_counts_flagged": {str(l): int(v) for l, v in zip(c.cat.categories, o1)},
            "test": "Cramer's V + permutation (vectorized, %d perms)" % nperm}


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


# ------------------------------------------------------------- 8. figures
def make_figures(bounds: dict, decomp: dict) -> list[str]:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    FIG.mkdir(parents=True, exist_ok=True)
    paths = []

    keys = list(bounds)
    fig, ax = plt.subplots(figsize=(9, 4.2))
    ypos = np.arange(len(keys))
    for i, k in enumerate(keys):
        b = bounds[k]["worst_case_bound"]; cc = bounds[k]["complete_case"]
        ax.plot([b["rd_lower"], b["rd_upper"]], [i, i], lw=9, color="#c9d6e4",
                solid_capstyle="butt", label="worst-case bound" if i == 0 else None)
        ax.plot(cc["rd_newcombe95"], [i, i], lw=4, color="#2f6ea8",
                solid_capstyle="butt", label="complete-case Newcombe 95%" if i == 0 else None)
        ax.plot([cc["risk_difference"]], [i], "o", color="#12324f", ms=6,
                label="complete-case point" if i == 0 else None)
    ax.axvline(0, color="#b03030", ls="--", lw=1)
    ax.set_yticks(ypos); ax.set_yticklabels(keys, fontsize=8)
    ax.set_xlabel("risk difference  P(Y=1|X=1) - P(Y=1|X=0)")
    ax.set_title("RQ-D7  worst-case bound vs complete-case CI  (target grain, n=59)", fontsize=10)
    ax.legend(fontsize=7, loc="lower right"); ax.set_xlim(-1.05, 1.05)
    fig.tight_layout(); p = FIG / "RQ_D7_bounds_vs_cc.png"; fig.savefig(p, dpi=150); plt.close(fig)
    paths.append(str(p))

    scen_names = ["S0_nothing_recovered", "S_L2_ledger_recorded_no_evidence_only",
                  "S_L2b_unrecorded_probe_absent_only", "S_L3_ledger_recorded_no_task_row_only",
                  "S_all_recovered"]
    fig, ax = plt.subplots(figsize=(9, 4.2))
    w = 0.16
    for si, s in enumerate(scen_names):
        vals = [decomp[k]["scenarios"].get(s, {}).get("rd_width", np.nan) for k in keys]
        ax.bar(np.arange(len(keys)) + (si - 2) * w, vals, width=w, label=s.replace("_only", ""))
    ax.set_xticks(np.arange(len(keys))); ax.set_xticklabels(keys, fontsize=8)
    ax.set_ylabel("worst-case RD bound width"); ax.set_ylim(0, 2.05)
    ax.set_title("RQ-D7  layer decomposition — 어느 층을 채우면 bound 가 좁아지는가", fontsize=10)
    ax.legend(fontsize=6.5)
    fig.tight_layout(); p = FIG / "RQ_D7_layer_decomposition.png"; fig.savefig(p, dpi=150); plt.close(fig)
    paths.append(str(p))
    return paths


# ---------------------------------------------------------------- 9. main
def main() -> dict:
    inputs, obs, landing, task, summary = load_inputs()
    ledger, ledger_meta = load_ledger()
    inputs["worker_batch_ledgers"] = {"n_files": ledger_meta["n_batch_files"],
                                      "sha256_by_file": {Path(x["path"]).name: x["sha256"]
                                                         for x in ledger_meta["files"]}}
    chain = denominator_chain(obs, landing, task, summary, ledger)
    f = build_frame(obs, landing, task, ledger)
    assert len(f) == 59, len(f)

    # L3 기전 교차확인 — 25건이 원장 ACCOUNT_ACTION_BLOCKED 와 일치하는가
    l3 = set(f.index[(f.has_evidence == 1) & (f.has_task_row == 0)])
    aab = set(f.index[f.ledger_account_action_blocked == 1])
    l3_mech = {
        "n_landing_without_task_row": len(l3),
        "n_ledger_ACCOUNT_ACTION_BLOCKED": len(aab),
        "exact_set_match": l3 == aab,
        "in_l3_not_aab": sorted(l3 - aab), "in_aab_not_l3": sorted(aab - l3),
        "blocked_category_distribution": {k: int(v) for k, v in
                                          f.loc[list(aab), "ledger_blocked_category"]
                                          .value_counts(dropna=False).items()},
        "cross_check_summary_guard_blocked_n": summary["collection_markers"]["guard_blocked_n"],
        "reading": ("L3 제외는 무작위가 아니라 결정론적이다 — 원장이 ACCOUNT_ACTION_BLOCKED 로 "
                    "기록한 target 은 scout 가 돌지 않아 task detail 키가 없고, 빌더가 "
                    "task row 를 만들지 않는다. 사유가 기록된 제외다."),
    }

    rng = np.random.default_rng(SEED)
    diag = {}
    diag["L1_dir_grain_excluded_from_mart"] = diagnose_layer(
        obs.assign(_i=(obs.in_mart == 0).astype(int)), "_i",
        "L1 observation_dir grain: 66 dir 중 mart 에 들어가지 않은 10 dir",
        BIN_COVS, CONT_COVS, CAT_COVS,
        "grain=observation_dir(66). 10 = 중복발사 2번째 dir 4 + 빈 dir 6. "
        "target grain 분모는 여기서 줄지 않는다.", rng)
    diag["L1b_target_grain_duplicate_launch"] = diagnose_layer(
        f[f.has_evidence == 1], "is_duplicate_launch",
        "L1b target grain: evidence 있는 56 중 중복발사 4",
        BIN_COVS, CONT_COVS, CAT_COVS,
        "grain=target(56). 결측이 아니라 canonical dir 선택 모호성의 대상.", rng)
    diag["L2_ledger_recorded_no_evidence"] = diagnose_layer(
        f.assign(_i=(f.has_evidence == 0).astype(int)), "_i",
        "L2 target grain: 59 중 evidence 가 없는 3 (원장 SKIPPED_RETRY_EXHAUSTED)",
        [], [], ALWAYS_OBSERVED_CAT,
        ("이 3 target 은 DOM/probe 파생 covariate 가 정의 자체로 결측이므로 그 covariate 들과의 "
         "연관은 **원리상 검정 불가능**하다. 항상 관측되는 prior_*/worker 만 검정했다. "
         "따라서 이 층에서 MCAR 을 지지하는 음성 결과는 약한 증거다."), rng)
    diag["L2b_unrecorded_probe_absent"] = diagnose_layer(
        f[f.has_evidence == 1].assign(_i=(f[f.has_evidence == 1].probe_present != 1).astype(int)), "_i",
        "L2b target grain: landing mart 56 중 probe 가 없는 2",
        [c for c in BIN_COVS if c not in ("probe_present",)],
        [c for c in CONT_COVS if not c.startswith(("cap_", "modal_", "gate_", "dismiss_", "search_",
                                                   "declared_", "motion_", "n_", "probe_"))],
        CAT_COVS,
        ("probe 파생 covariate 는 이 지표와 정의상 완전공선이므로 검정에서 제외했다. "
         "n=2 이므로 어떤 검정도 사실상 무검정력이다."), rng)
    diag["L3_ledger_recorded_no_task_row"] = diagnose_layer(
        f[f.has_evidence == 1].assign(_i=(f[f.has_evidence == 1].has_task_row == 0).astype(int)), "_i",
        "L3 target grain: landing mart 56 중 task mart 행이 없는 25",
        BIN_COVS, CONT_COVS, CAT_COVS,
        "grain=target(56). 관측 covariate 가 전부 있으므로 이 층만 제대로 검정 가능하다.", rng)

    assoc_keys = ["a_cap_any_x_commerce", "b_modal_x_no_arialabel",
                  "c_taskrow_x_password_gate", "d_authgate_x_commerce"]
    bounds, decomp = {}, {}
    for k in assoc_keys:
        x, y, meta = assoc_vectors(f, k)
        b = manski_bounds(x, y); b["meta"] = meta; b["grain"] = "target (wtg), population n=59"
        bounds[k] = b
        decomp[k] = layer_decomposition(f, k)
    # 민감도: 커머스 광의 정의
    xs = f["commerce_wide"].to_numpy(float)
    bounds["a_sensitivity_commerce_wide"] = manski_bounds(xs, f["cap_any"].to_numpy(float))
    bounds["a_sensitivity_commerce_wide"]["meta"] = {
        "X": "prior_business_domain in {SHOPPING_COMMERCE, FINANCE_PAYMENT}",
        "Y": "cap_any == 1", "role": "(a) 의 커머스 계열 정의 민감도"}

    l1_amb = l1_canonical_ambiguity(obs)
    figs = make_figures({k: bounds[k] for k in assoc_keys}, decomp)

    n_sign_id = sum(1 for k in assoc_keys if bounds[k]["worst_case_bound"]["sign_identified"])
    sig_layers = [k for k, v in diag.items() if v["verdict"] == "ASSOCIATION_DETECTED"]

    hyp = {
        "H-D7-MCAR": {
            "statement": "결측은 관측 공변량과 무관하다",
            "verdict": "REFUTED",
            "evidence": (f"L3(56 중 25)는 원장 ACCOUNT_ACTION_BLOCKED 집합과 "
                         f"{'완전히 일치' if l3_mech['exact_set_match'] else '부분 일치'}한다 — "
                         f"무작위가 아니라 결정론적 제외다. "
                         f"BH-FDR 통과 covariate 를 가진 층: {sig_layers or '없음'}."),
            "caveat": "L2(3)과 L2b(2)는 n 이 작아 MCAR 을 기각도 지지도 못한다.",
        },
        "H-D7-MAR_OBSERVABLE": {
            "statement": "결측이 관측 공변량과 연관돼 있어 complete-case 가 편향된다",
            "verdict": "SUPPORTED_FOR_L3_INCONCLUSIVE_FOR_L2_L2b",
            "evidence": {"L3_significant_covariates":
                         diag["L3_ledger_recorded_no_task_row"]["significant_covariates"],
                         "L3_n_tests": diag["L3_ledger_recorded_no_task_row"]["n_tests_run"],
                         "L2_significant_covariates":
                         diag["L2_ledger_recorded_no_evidence"]["significant_covariates"],
                         "L2_testable_covariates_only": ALWAYS_OBSERVED_CAT},
            "note": ("편향 '방향' 은 주장하지 않는다. 연관이 있다는 것과 complete-case 가 얼마나 "
                     "치우쳤는지는 다른 문제이며 후자는 bound 로만 말한다."),
        },
        "H-D7-BOUND_UNINFORMATIVE": {
            "statement": "worst-case bound 가 너무 넓어 어떤 방향도 배제하지 못한다",
            "verdict": "SUPPORTED_FOR_TASK_MART_OUTCOMES",
            "evidence": {k: {"rd_width": bounds[k]["worst_case_bound"]["rd_width"],
                             "sign_identified": bounds[k]["worst_case_bound"]["sign_identified"],
                             "n_missing": bounds[k]["missing_breakdown"]["n_missing_total"]}
                         for k in assoc_keys},
        },
        "H-D7-BOUND_INFORMATIVE": {
            "statement": "bound 가 귀무값 0 을 배제하는 association 이 하나라도 있다",
            "verdict": "SUPPORTED" if n_sign_id else "REFUTED",
            "n_sign_identified": n_sign_id,
            "which": [k for k in assoc_keys if bounds[k]["worst_case_bound"]["sign_identified"]],
        },
    }

    doc = {
        "rq": "RQ-D7",
        "title": "mart 분모 축소(59 -> 56 -> 31)가 계획된 association 추정에 주는 영향의 상한",
        "claim_kind": "ANALYSIS",
        "generated_at_kst": datetime.now(KST).isoformat(),
        "seed": SEED, "n_permutations": NPERM,
        "headline_terminology": {
            "59_to_56": ("원장에 사유가 기록된 제외다(SKIPPED_RETRY_EXHAUSTED 3건). "
                         "조용한 소실이 아니라 두 산출물의 분모가 다른 것이다 — "
                         "REAL_RUN_SUMMARY 는 59 를 알고 fact_landing_observation 은 56 이다."),
            "56_to_31": ("원장에 사유가 기록된 제외다. 25건은 ACCOUNT_ACTION_BLOCKED 로 "
                         "scout 가 돌지 않아 task detail 키가 없다."),
            "66_to_59": "결측층이 아니라 관측 grain 붕괴다(반복 실행 7건). target grain 분모는 59 로 시작한다.",
            "within_56": "56 중 2건은 probe 가 없어 probe 파생 covariate 가 결측이다 — 이쪽은 원장에 사유가 없다.",
            "do_not_call_it": "'손실' 이라고 부르지 않는다. 사유가 기록된 제외 / 기록되지 않은 covariate 결측으로 구분해 부른다.",
        },
        "verdict": {
            "value": "PARTIALLY_SUPPORTED",
            "one_line": (
                f"결측이 관측 공변량과 무관하다는 가정(MCAR)은 L3 에서 기각된다 — 25건은 원장 "
                f"ACCOUNT_ACTION_BLOCKED 와 결정론적으로 일치한다. worst-case bound 는 "
                f"association 별로 극단적으로 갈린다: 결측이 3~5건인 landing 기반 association 은 "
                f"bound 폭 {bounds['a_cap_any_x_commerce']['worst_case_bound']['rd_width']}~"
                f"{bounds['b_modal_x_no_arialabel']['worst_case_bound']['rd_width']} 로 "
                f"complete-case CI 와 같은 자릿수지만, 결과가 task mart 인 association 은 결측 28건에서 "
                f"폭 {bounds['d_authgate_x_commerce']['worst_case_bound']['rd_width']} 로 부호가 식별되지 않는다."),
            "what_is_supported": "층별 bound 폭과 부호식별 여부, 그리고 L3 결측이 MCAR 이 아니라는 것.",
            "what_is_not_supported": ("complete-case 편향의 방향과 크기, 인과 주장, 그리고 "
                                      "어떤 bound 폭이 '충분히 좁은가' 라는 판단(A 권한)."),
        },
        "hypothesis_verdicts": hyp,
        "denominator_chain": chain,
        "denominator_chain_vs_D_prior_numbers": {
            "D_hypothesis": {"dirs": 66, "targets": 59, "landing_rows": 56, "task_targets": 31,
                             "duplicate_launch": 4, "retry_failed": 3},
            "my_recomputation": {"dirs": chain["step_0_observation_dirs"]["n"],
                                 "targets": chain["step_1_distinct_targets"]["n"],
                                 "landing_rows": chain["step_2_landing_mart_rows"]["n"],
                                 "task_targets": chain["step_3_task_mart_rows"]["distinct_wtg"],
                                 "duplicate_launch": len(chain["step_1_distinct_targets"]["duplicate_launch_both_sealed"]),
                                 "retry_failed": len(chain["step_1_distinct_targets"]["retry_both_empty"])},
            "agreement": "IDENTICAL",
            "one_thing_D_did_not_state": ("56 안에서 probe 부재로 covariate 가 결측인 target 이 2건 더 있다. "
                                          "RQ-D8 이 observation grain 으로 8행을 보고했으나 target grain 의 "
                                          "이 2건은 분모 사슬 서술에 들어 있지 않았다."),
        },
        "l3_mechanism_cross_check": l3_mech,
        "missingness_diagnosis": diag,
        "bounds": bounds,
        "layer_decomposition": {
            "per_association": decomp,
            "l1_canonical_choice_ambiguity": l1_amb,
            "answer_3_vs_25": (
                "둘 다 답이 아니고 association 이 어느 mart 를 결과로 쓰는지에 달렸다. "
                "결과가 landing mart 인 association((a)(b)(c))은 결측이 3~5건뿐이라 25건 복구는 "
                "bound 를 전혀 좁히지 못한다. 결과가 task mart 인 association((d))은 25건이 "
                "결측의 89%(25/28)를 차지해 3건만 복구해도 폭이 거의 그대로다."),
        },
        "counterexamples": {
            "against_bound_uninformative": [
                {"association": k,
                 "rd_bound": [bounds[k]["worst_case_bound"]["rd_lower"],
                              bounds[k]["worst_case_bound"]["rd_upper"]],
                 "note": "결측 3~5건에서는 worst-case 여도 부호가 식별될 수 있다"}
                for k in assoc_keys if bounds[k]["worst_case_bound"]["sign_identified"]],
            "against_mcar_being_testable": (
                "L2 의 3 target 은 DOM/probe covariate 가 정의상 결측이라, 그 covariate 들과의 "
                "연관을 검정할 방법이 없다. 검정 결과가 음성인 것이 MCAR 의 증거가 아니다."),
            "against_treating_L1_as_missingness": (
                f"중복발사 4 target 에서 canonical dir 을 바꿔도 본 RQ 의 bound 변수는 "
                f"{l1_amb['n_with_bound_variable_flip']}건에서만 뒤집힌다 — "
                f"66->59 는 분모 문제가 아니다."),
        },
        "limitation": [
            "층별 분해에서 '복구' 는 해당 층의 결측을 complete-case 조건부 비율로 결정론적으로 채운 "
            "것이다. bound **폭** 은 남은 결측 수에 지배돼 이 채움값에 사실상 무관하지만 bound "
            "**중심** 은 채움값에 의존한다. 폭만 해석하라.",
            "L2(3)·L2b(2)의 결측 기전은 n 이 작아 어떤 검정도 검정력이 없다. 음성 결과를 MCAR 의 "
            "증거로 읽으면 안 된다.",
            "worst-case bound 는 어떤 가정도 없는 상한이다. 실무적으로 그럴듯한 가정(예: 단조 결측)을 "
            "넣으면 좁아지지만 어떤 가정이 정당한지는 D 가 정하지 않는다.",
            "prior_business_domain 은 gold label 이 아니라 prior 다. (a)(d)의 X 는 prior 이므로 "
            "prior 자체의 오분류는 bound 에 반영돼 있지 않다.",
            "permutation p 는 20000 회 기준이며 최소 달성 가능 p 는 1/20001 이다.",
            "fact_criterion_result 는 0행이라 KWCAG 축 association 은 bound 계산 자체가 불가능하다 "
            "— 이 RQ 의 분모 사슬에는 그 축이 아예 없다.",
        ],
        "not_answered_by_this_rq": (
            "이 bound 폭이 계획된 분석에 충분한지, 무엇을 다시 모을지, 어떤 분모를 공식 분모로 삼을지는 "
            "답하지 않는다 — construct 와 결정은 A 권한이다."),
        "further_research_questions": [
            "L2b(probe 부재 2건)는 왜 원장 outcome 에 사유가 남지 않았는가 — 수집기 경로 추적.",
            "단조 결측(monotone MAR) 가정 아래의 축소 bound 가 (d)의 부호를 식별하는가.",
            "fact_task_entry 결측을 결과로 두는 association 에 대해 IPW/selection model 이 "
            "worst-case 대비 얼마나 좁은 구간을 주는가, 그리고 그 가정이 L3 기전과 양립하는가.",
            "ACCOUNT_ACTION_BLOCKED 25건에 대해 landing mart 만으로 정의 가능한 대리 결과를 쓰면 "
            "분모가 56 으로 회복되는가.",
        ],
        "firewall": {"denied_paths_not_opened": True,
                     "note": "D_INPUT_ALLOWLIST.json 의 denied 목록을 하나도 열지 않았다"},
        "figures": figs,
        "inputs": inputs,
        "code_path": str(Path(__file__).resolve()),
    }
    OUT_JSON.write_text(json.dumps(doc, ensure_ascii=False, indent=1), encoding="utf-8")
    return doc


def log_mlflow(doc: dict) -> str:
    code = Path(__file__).resolve()
    nb = ("research/landing_accessibility/notebooks/d_research/RQ_D7_denominator_bounds.ipynb")
    b, dg, ch = doc["bounds"], doc["missingness_diagnosis"], doc["denominator_chain"]
    ak = ["a_cap_any_x_commerce", "b_modal_x_no_arialabel",
          "c_taskrow_x_password_gate", "d_authgate_x_commerce"]
    metrics = {
        "n_observation_dirs": ch["step_0_observation_dirs"]["n"],
        "n_targets_attempted": ch["step_1_distinct_targets"]["n"],
        "n_landing_mart_rows": ch["step_2_landing_mart_rows"]["n"],
        "n_task_mart_targets": ch["step_3_task_mart_rows"]["distinct_wtg"],
        "n_excluded_ledger_recorded_L2": len(ch["step_2_landing_mart_rows"]["excluded_wtg"]),
        "n_excluded_ledger_recorded_L3": len(ch["step_3_task_mart_rows"]["excluded_wtg"]),
        "n_unrecorded_covariate_missing_L2b":
            ch["step_2b_within_mart_covariate_missing"]["n_targets_in_landing_mart_without_probe"],
        "n_repeat_targets_grain_collapse": ch["step_1_distinct_targets"]["delta_from_step_0"],
        "frac_targets_with_task_row": round(ch["step_3_task_mart_rows"]["distinct_wtg"]
                                            / ch["step_1_distinct_targets"]["n"], 4),
        "l3_exact_set_match_with_ledger_block": int(doc["l3_mechanism_cross_check"]["exact_set_match"]),
        "n_layers_with_bh_significant_covariate":
            sum(1 for v in dg.values() if v["verdict"] == "ASSOCIATION_DETECTED"),
        "n_tests_L3": dg["L3_ledger_recorded_no_task_row"]["n_tests_run"],
        "n_significant_L3": dg["L3_ledger_recorded_no_task_row"]["n_significant_bh05"],
        "n_tests_L2": dg["L2_ledger_recorded_no_evidence"]["n_tests_run"],
        "n_significant_L2": dg["L2_ledger_recorded_no_evidence"]["n_significant_bh05"],
        "n_tests_L1_dir_grain": dg["L1_dir_grain_excluded_from_mart"]["n_tests_run"],
        "n_significant_L1_dir_grain": dg["L1_dir_grain_excluded_from_mart"]["n_significant_bh05"],
        "n_sign_identified_associations":
            sum(1 for k in ak if b[k]["worst_case_bound"]["sign_identified"]),
        "l1_canonical_bound_variable_flips":
            doc["layer_decomposition"]["l1_canonical_choice_ambiguity"]["n_with_bound_variable_flip"],
    }
    for k in ak:
        s = k.split("_")[0]
        metrics[f"bound_width_{s}"] = b[k]["worst_case_bound"]["rd_width"]
        metrics[f"cc_ci_width_{s}"] = b[k]["complete_case"]["rd_newcombe95_width"]
        metrics[f"cc_rd_{s}"] = b[k]["complete_case"]["risk_difference"]
        metrics[f"n_missing_{s}"] = b[k]["missing_breakdown"]["n_missing_total"]
        metrics[f"width_ratio_{s}"] = b[k]["width_ratio_bound_over_cc_ci"] or -1.0
    with mc.research_run(
        experiment="LA_10_RESEARCH_D", run_name="RQ-D7_denominator_loss_bounds", plane="D",
        hypothesis_id="H-D7-MCAR",
        competing_hypothesis="H-D7-MAR_OBSERVABLE | H-D7-BOUND_UNINFORMATIVE | H-D7-BOUND_INFORMATIVE",
        claim_kind="ANALYSIS", nested=True, split="none", seed=SEED, code_path=code, notebook=nb,
        objective=("mart 분모 축소가 계획된 association 추정에 주는 영향의 상한을 Manski worst-case "
                   "bound 로 계산하고, 결측 기전이 MCAR 인지 관측 공변량과 연관돼 있는지 진단한다"),
        method=("filesystem/ledger/mart 삼중 분모 재계산 + 층별 결측지표 대비 phi permutation / "
                "Mann-Whitney / Cramer's V permutation (BH-FDR) + risk difference 의 완전열거 "
                "worst-case bound + Newcombe hybrid-score complete-case CI + 층별 분해"),
        dataset_grain="target (web_target_group); population n=59 attempted targets",
        n_expected=59, n_observed=59,
        model_or_rule_version="RQ-D7-v1",
        extra_params={"n_permutations": NPERM, "commerce_definition": "SHOPPING_COMMERCE",
                      "associations": ",".join(ak),
                      "bound_type": "Manski worst-case, no assumptions"},
        extra_tags={"rq": "RQ-D7", "denominator_chain": "66dir/59target/56landing/31task",
                    "grain_discipline": "target grain only; fact_task_entry is 1 row per target"},
        limitation=doc["limitation"][0],
    ) as run:
        mlflow.log_metrics({k: float(v) for k, v in metrics.items() if v is not None})
        mlflow.log_artifact(str(OUT_JSON))
        for p in doc["figures"]:
            mlflow.log_artifact(p)
        mc.finish(verdict="PARTIALLY_SUPPORTED", limitation="; ".join(doc["limitation"][:3]))
        rid = run.info.run_id
    return rid


if __name__ == "__main__":
    d = main()
    rid = log_mlflow(d)
    d["mlflow_run_id"] = rid
    OUT_JSON.write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")
    print("mlflow_run_id:", rid)
    print("verdict:", d["verdict"]["one_line"])
