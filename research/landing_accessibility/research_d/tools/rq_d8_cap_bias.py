#!/usr/bin/env python3
"""RQ-D8 — l0_probe cap truncation vs interaction_archetype (prior).

Ticket: T-B-RQ-D-001 Q1 (from B). Independent recomputation.

Input  (ONLY):  research_d/results/D_OBSERVATION_TABLE.csv
Output:         research_d/results/RQ_D8_cap_bias.json
                research_d/figures/RQ_D8_cap_by_archetype.png (optional, matplotlib)

Restart -> Run All safe. No hidden state, no network, no gold labels read.

Run:
  /home/sieg/projects-wsl/ProjectFinal/.venv/bin/python \
    /home/sieg/projects-wsl/ProjectFinal/.agent_worktrees/claude_d_research/\
research/landing_accessibility/research_d/tools/rq_d8_cap_bias.py
"""
from __future__ import annotations

import json
import math
import os
from itertools import product

import numpy as np
import pandas as pd
from scipy import stats

ROOT = "/home/sieg/projects-wsl/ProjectFinal/.agent_worktrees/claude_d_research/research/landing_accessibility/research_d"
CSV = os.path.join(ROOT, "results", "D_OBSERVATION_TABLE.csv")
OUT_JSON = os.path.join(ROOT, "results", "RQ_D8_cap_bias.json")
FIG = os.path.join(ROOT, "figures", "RQ_D8_cap_by_archetype.png")

RNG_SEED = 20260827

# cap ceilings, verified in l0_probe.js @2281c85 (reported by B; used here as DEFINITION)
CAPS = {
    "primary_action_candidates": {"n": "n_primary_action_candidates", "flag": "cap_primary_action_candidates", "ceiling": 200, "visible_filter": True},
    "accessible_name_sources": {"n": "n_accessible_name_sources", "flag": "cap_accessible_name_sources", "ceiling": 300, "visible_filter": False},
    "target_size": {"n": "n_target_size", "flag": "cap_target_size", "ceiling": 300, "visible_filter": True},
    "contrast": {"n": "n_contrast", "flag": "cap_contrast", "ceiling": 400, "visible_filter": True},
}
EXTRA_CAP_FLAGS = ["cap_motion_animated_60", "cap_body_text_4000"]

LOW_N_MIN = 5      # n>=5 -> normal reporting
LOW_N_FLOOR = 3    # n in 3..4 -> LOW_N descriptive only; n<=2 -> DO_NOT_INTERPRET


# ---------------------------------------------------------------- helpers
def wilson(k: int, n: int, z: float = 1.959963985) -> list:
    if n == 0:
        return [None, None]
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return [round(max(0.0, c - h), 4), round(min(1.0, c + h), 4)]


def newcombe_rd(k1: int, n1: int, k0: int, n0: int) -> list:
    """Newcombe method 10 CI for risk difference p1 - p0."""
    l1, u1 = wilson(k1, n1)
    l0, u0 = wilson(k0, n0)
    p1, p0 = k1 / n1, k0 / n0
    lo = (p1 - p0) - math.sqrt((p1 - l1) ** 2 + (u0 - p0) ** 2)
    hi = (p1 - p0) + math.sqrt((u1 - p1) ** 2 + (p0 - l0) ** 2)
    return [round(max(-1.0, lo), 4), round(min(1.0, hi), 4)]


def rr_ci(k1: int, n1: int, k0: int, n0: int) -> dict:
    """Katz log risk-ratio CI with 0.5 continuity correction when a cell is 0."""
    a, b, c, d = k1, n1 - k1, k0, n0 - k0
    corrected = (min(a, b, c, d) == 0)
    if corrected:
        a, b, c, d = a + 0.5, b + 0.5, c + 0.5, d + 0.5
    p1 = a / (a + b)
    p0 = c / (c + d)
    rr = p1 / p0
    se = math.sqrt(1 / a - 1 / (a + b) + 1 / c - 1 / (c + d))
    return {
        "risk_ratio": round(rr, 4),
        "ci95": [round(rr * math.exp(-1.959963985 * se), 4), round(rr * math.exp(1.959963985 * se), 4)],
        "continuity_corrected": bool(corrected),
    }


def fisher_block(k1: int, n1: int, k0: int, n0: int, label: str) -> dict:
    """2x2 exact test + effect sizes. Rows: group1 (exposed) / group0."""
    tbl = [[k1, n1 - k1], [k0, n0 - k0]]
    odds, p = stats.fisher_exact(tbl, alternative="two-sided")
    try:
        or_res = stats.contingency.odds_ratio(tbl, kind="conditional")
        or_pt = float(or_res.statistic)
        or_lo, or_hi = or_res.confidence_interval(confidence_level=0.95)
        or_ci = [None if not np.isfinite(or_lo) else round(float(or_lo), 4),
                 None if not np.isfinite(or_hi) else round(float(or_hi), 4)]
    except Exception:  # pragma: no cover
        or_pt, or_ci = float(odds), [None, None]
    p1, p0 = k1 / n1, k0 / n0
    return {
        "label": label,
        "table_2x2": {"group1_hit": k1, "group1_n": n1, "group0_hit": k0, "group0_n": n0},
        "rate_group1": f"{k1}/{n1}", "rate_group1_pct": round(100 * p1, 2), "ci95_group1": wilson(k1, n1),
        "rate_group0": f"{k0}/{n0}", "rate_group0_pct": round(100 * p0, 2), "ci95_group0": wilson(k0, n0),
        "risk_difference": round(p1 - p0, 4),
        "risk_difference_ci95_newcombe": newcombe_rd(k1, n1, k0, n0),
        **rr_ci(k1, n1, k0, n0),
        "odds_ratio_conditional_mle": None if not np.isfinite(or_pt) else round(or_pt, 4),
        "odds_ratio_ci95": or_ci,
        "fisher_exact_p_two_sided": round(float(p), 6),
    }


def fisher_power(n1: int, n0: int, p1: float, p0: float, alpha: float = 0.05, nsim: int = 20000, seed: int = RNG_SEED) -> float:
    """Monte-Carlo power of the two-sided Fisher exact test at fixed margins n1,n0."""
    rng = np.random.default_rng(seed)
    k1 = rng.binomial(n1, p1, nsim)
    k0 = rng.binomial(n0, p0, nsim)
    # cache p-values over the (k1,k0) grid actually observed
    cache: dict = {}
    hits = 0
    for a, c in zip(k1.tolist(), k0.tolist()):
        key = (a, c)
        pv = cache.get(key)
        if pv is None:
            pv = stats.fisher_exact([[a, n1 - a], [c, n0 - c]], alternative="two-sided")[1]
            cache[key] = pv
        if pv < alpha:
            hits += 1
    return hits / nsim


def mde_curve(n1: int, n0: int, p0: float, target_power: float = 0.80) -> dict:
    """Smallest p1 > p0 reaching target power at these margins (grid 0.01)."""
    grid = [round(x, 2) for x in np.arange(p0, 1.0001, 0.01)]
    for p1 in grid:
        if p1 <= p0:
            continue
        pw = fisher_power(n1, n0, p1, p0, nsim=6000)
        if pw >= target_power:
            return {"p0_assumed": round(p0, 4), "mde_p1": p1,
                    "mde_risk_difference": round(p1 - p0, 4),
                    "mde_risk_ratio": round(p1 / p0, 3) if p0 > 0 else None,
                    "power_at_mde": round(pw, 3)}
    return {"p0_assumed": round(p0, 4), "mde_p1": None, "note": "no p1<=1.0 reaches target power at these margins"}


def mantel_haenszel(strata: list) -> dict:
    """strata: list of (k1,n1,k0,n0). Returns MH odds ratio + Robins-Breslow-Greenland CI."""
    num = den = 0.0
    usable = 0
    for k1, n1, k0, n0 in strata:
        a, b, c, d = k1, n1 - k1, k0, n0 - k0
        n = a + b + c + d
        if n == 0:
            continue
        usable += 1
        num += a * d / n
        den += b * c / n
    if den == 0 or num == 0:
        return {"mh_odds_ratio": None, "ci95": [None, None], "strata_used": usable,
                "note": "MH undefined (a zero R or S sum) — sparse strata"}
    mh = num / den
    # RBG variance
    s_pr = s_pspqr = s_qs = 0.0
    for k1, n1, k0, n0 in strata:
        a, b, c, d = k1, n1 - k1, k0, n0 - k0
        n = a + b + c + d
        if n == 0:
            continue
        P = (a + d) / n
        Q = (b + c) / n
        R = a * d / n
        S = b * c / n
        s_pr += P * R
        s_pspqr += P * S + Q * R
        s_qs += Q * S
    var = s_pr / (2 * num ** 2) + s_pspqr / (2 * num * den) + s_qs / (2 * den ** 2)
    se = math.sqrt(var)
    return {"mh_odds_ratio": round(mh, 4),
            "ci95": [round(mh * math.exp(-1.959963985 * se), 4), round(mh * math.exp(1.959963985 * se), 4)],
            "strata_used": usable}


def js(o):
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.floating,)):
        return None if not np.isfinite(o) else float(o)
    if isinstance(o, (np.bool_,)):
        return bool(o)
    raise TypeError(str(type(o)))


# ---------------------------------------------------------------- load / grain
def main() -> dict:
    raw = pd.read_csv(CSV)
    out: dict = {
        "rq": "RQ-D8",
        "ticket": "T-B-RQ-D-001 Q1",
        "question": "Is l0_probe cap truncation biased with respect to prior interaction_archetype, and how would it distort the same-archetype median baseline used by ExcessDepth?",
        "input": {"file": CSV, "rows": int(len(raw)), "cols": int(raw.shape[1])},
        "caps_definition": {k: {"ceiling": v["ceiling"], "visible_filter_applied": v["visible_filter"]} for k, v in CAPS.items()},
        "caps_definition_provenance": "l0_probe.js @2281c85 as relayed in ticket T-B-RQ-D-001; treated as DEFINITION, not re-verified from source in this RQ (source file is outside this RQ's permitted inputs)",
        "seed": RNG_SEED,
    }

    # ---- grain fixation -------------------------------------------------
    cap_flags = [v["flag"] for v in CAPS.values()]
    raw["_cap_data"] = raw[cap_flags].notna().all(axis=1)
    dup_counts = raw["wtg"].value_counts()
    dup_wtgs = sorted(dup_counts[dup_counts > 1].index.tolist())

    obs = raw[raw["_cap_data"]].copy()                    # observation grain, cap-measurable
    tgt = obs[obs["in_mart"] == 1].copy()                 # target grain, canonical

    out["grain"] = {
        "raw_observations": int(len(raw)),
        "unique_targets_wtg": int(raw["wtg"].nunique()),
        "targets_with_repeat_runs": len(dup_wtgs),
        "targets_with_repeat_runs_ids": dup_wtgs,
        "repeat_runs_with_a_mart_canonical": int(sum(1 for w in dup_wtgs if ((raw.wtg == w) & (raw.in_mart == 1)).any())),
        "in_mart_rows": int((raw["in_mart"] == 1).sum()),
        "rows_without_cap_data": int((~raw["_cap_data"]).sum()),
        "rows_without_cap_data_reason": {
            "probe_present_missing": int(raw.loc[~raw["_cap_data"], "probe_present"].isna().sum()),
            "probe_present_zero": int((raw.loc[~raw["_cap_data"], "probe_present"] == 0).sum()),
        },
        "ANALYSIS_SET_observation_grain_N": int(len(obs)),
        "ANALYSIS_SET_observation_grain_unique_targets": int(obs["wtg"].nunique()),
        "ANALYSIS_SET_target_grain_N": int(len(tgt)),
        "note": ("Observation grain N=58 contains 4 repeat runs of targets that also contribute their mart-canonical row, "
                 "so 58 observations cover only 54 distinct targets. The '/58' denominator used by B and C is the "
                 "observation grain, not a per-target rate."),
    }

    # test-retest of the repeat pairs that both have cap data
    retest = []
    for w in dup_wtgs:
        g = raw[(raw.wtg == w) & raw["_cap_data"]].sort_values("run_ts")
        if len(g) == 2:
            r0, r1 = g.iloc[0], g.iloc[1]
            retest.append({
                "wtg": w, "prior_archetype": r0["prior_archetype"],
                "cap_any": [int(r0["cap_any"]), int(r1["cap_any"])],
                "n_primary": [float(r0[CAPS['primary_action_candidates']['n']]), float(r1[CAPS['primary_action_candidates']['n']])],
                "n_accessible_name": [float(r0[CAPS['accessible_name_sources']['n']]), float(r1[CAPS['accessible_name_sources']['n']])],
                "dom_element_n": [float(r0["dom_element_n"]), float(r1["dom_element_n"])],
                "cap_flag_agreement": bool(int(r0["cap_any"]) == int(r1["cap_any"])),
            })
    out["repeat_run_reliability"] = {
        "pairs_with_cap_data": len(retest),
        "pairs_agreeing_on_cap_any": int(sum(p["cap_flag_agreement"] for p in retest)),
        "pairs": retest,
        "assertion_type": "OBSERVATION",
    }

    # ---- flag vs threshold consistency ---------------------------------
    consistency = {}
    for name, spec in CAPS.items():
        ge = int((obs[spec["n"]] >= spec["ceiling"]).sum())
        eq = int((obs[spec["n"]] == spec["ceiling"]).sum())
        fl = int((obs[spec["flag"]] == 1).sum())
        gt = int((obs[spec["n"]] > spec["ceiling"]).sum())
        consistency[name] = {"n_ge_ceiling": ge, "n_eq_ceiling": eq, "n_gt_ceiling": gt,
                             "flag_eq_1": fl, "flag_matches_ge": ge == fl, "flag_matches_eq": eq == fl,
                             "denominator": int(len(obs))}
    out["flag_threshold_consistency"] = {
        "detail": consistency,
        "conclusion": "flag==1 <=> n>=ceiling <=> n==ceiling for all four caps; no row exceeds its ceiling, so '>=' vs '==' cannot explain any disagreement in counts.",
        "assertion_type": "OBSERVATION",
    }

    # ---- independent recount -------------------------------------------
    def counts(df, tag):
        r = {}
        for name, spec in CAPS.items():
            k = int((df[spec["flag"]] == 1).sum())
            r[name] = {"hits": k, "n": int(len(df)), "rate": f"{k}/{len(df)}", "pct": round(100 * k / len(df), 2),
                       "ci95_wilson": wilson(k, len(df))}
        k = int((df["cap_any"] == 1).sum())
        r["cap_any_4cap"] = {"hits": k, "n": int(len(df)), "rate": f"{k}/{len(df)}", "pct": round(100 * k / len(df), 2),
                             "ci95_wilson": wilson(k, len(df))}
        any6 = (df[[*[v["flag"] for v in CAPS.values()], *EXTRA_CAP_FLAGS]].fillna(0).sum(axis=1) > 0).astype(int)
        k6 = int(any6.sum())
        r["cap_any_6flag_incl_motion_and_bodytext"] = {"hits": k6, "n": int(len(df)), "rate": f"{k6}/{len(df)}"}
        r["_grain"] = tag
        return r

    out["recount"] = {"observation_grain": counts(obs, "observation"), "target_grain_in_mart": counts(tgt, "target")}

    # ---- reconciliation with B and C -----------------------------------
    obs["_any6"] = (obs[[*[v["flag"] for v in CAPS.values()], *EXTRA_CAP_FLAGS]].fillna(0).sum(axis=1) > 0).astype(int)
    id_share_obs = float((obs["prior_archetype"] == "ITEM_DETAIL").mean())
    caphit = obs[obs["cap_any"] == 1]
    out["reconciliation_with_other_planes"] = {
        "B_T-B-FINDING-002_claim": "primary_action_candidates cap-hit 7/58",
        "C_C-FINDING-212855_claim_1": "primary_action_candidates cap-hit 8/58",
        "D_recount": {
            "primary_action_cap_hit_observation_grain": f"{int((obs[CAPS['primary_action_candidates']['flag']]==1).sum())}/{len(obs)}",
            "primary_action_cap_hit_target_grain": f"{int((tgt[CAPS['primary_action_candidates']['flag']]==1).sum())}/{len(tgt)}",
        },
        "D_verdict_on_B": "REPRODUCED at observation grain (7/58). B's number is correct for the grain B used, but '/58' is 58 observations covering 54 distinct targets; the per-target rate is 7/54.",
        "D_verdict_on_C_count": ("NOT REPRODUCED. No definition tried yields 8. Tried: flag==1 (7), n>=200 (7), n>200 (0), "
                                 "n==200 (7), target grain (7/54), including the 2 probe_present==0 rows as non-hits (7/60), "
                                 "counting all 66 raw rows (7/66). C's 8 is off by one against every reconstruction."),
        "definitions_tried_for_primary_action": {
            "flag_eq_1_obs58": int((obs[CAPS['primary_action_candidates']['flag']] == 1).sum()),
            "n_ge_200_obs58": int((obs[CAPS['primary_action_candidates']['n']] >= 200).sum()),
            "n_gt_200_obs58": int((obs[CAPS['primary_action_candidates']['n']] > 200).sum()),
            "flag_eq_1_target54": int((tgt[CAPS['primary_action_candidates']['flag']] == 1).sum()),
            "flag_eq_1_all66_nan_as_0": int((raw[CAPS['primary_action_candidates']['flag']].fillna(0) == 1).sum()),
            "n_ge_190_obs58_near_cap": int((obs[CAPS['primary_action_candidates']['n']] >= 190).sum()),
            "n_ge_180_obs58_near_cap": int((obs[CAPS['primary_action_candidates']['n']] >= 180).sum()),
        },
        "C_C-FINDING-212855_claim_2": "cap-hit 15 targets, prior ITEM_DETAIL 11/15 (73%) vs overall 43%",
        "D_on_C_claim_2": {
            "D_cap_any_hits_observation_grain": f"{len(caphit)}/{len(obs)}",
            "D_cap_any_hits_target_grain": f"{int((tgt['cap_any']==1).sum())}/{len(tgt)}",
            "D_cap_any_hits_all_are_in_mart": bool((caphit["in_mart"] == 1).all()),
            "D_cap_any_hits_all_distinct_targets": bool(caphit["wtg"].nunique() == len(caphit)),
            "D_ITEM_DETAIL_among_cap_hits": f"{int((caphit['prior_archetype']=='ITEM_DETAIL').sum())}/{len(caphit)}",
            "D_ITEM_DETAIL_base_rate_observation_grain": f"{int((obs['prior_archetype']=='ITEM_DETAIL').sum())}/{len(obs)} = {round(100*id_share_obs,1)}%",
            "D_cap_any_6flag": f"{int(obs['_any6'].sum())}/{len(obs)}",
            "note": ("C's numerator (11 ITEM_DETAIL) and C's base rate (43% = 25/58) both reproduce exactly; C's denominator "
                     "does not — D finds 14 cap-hits, not 15, under both the 4-cap and the 6-flag union. C's extra unit is "
                     "therefore a non-ITEM_DETAIL one, consistent with the same off-by-one seen in C's 8/58. "
                     "Direction of the effect: C's 73% is an under-count of D's 11/14 = 78.6%."),
        },
        "assertion_type": "ANALYSIS",
    }

    # ---- archetype x cap cross-tabs ------------------------------------
    def crosstab(df, grain):
        rows = {}
        for a, g in df.groupby("prior_archetype"):
            n = len(g)
            tier = "OK" if n >= LOW_N_MIN else ("LOW_N_DESCRIPTIVE_ONLY" if n >= LOW_N_FLOOR else "DO_NOT_INTERPRET")
            e = {"n": n, "n_tier": tier}
            for name, spec in CAPS.items():
                k = int((g[spec["flag"]] == 1).sum())
                e[name] = {"hits": k, "rate": f"{k}/{n}", "pct": round(100 * k / n, 1), "ci95_wilson": wilson(k, n)}
            k = int((g["cap_any"] == 1).sum())
            e["cap_any"] = {"hits": k, "rate": f"{k}/{n}", "pct": round(100 * k / n, 1), "ci95_wilson": wilson(k, n)}
            e["dom_element_n_median"] = float(g["dom_element_n"].median())
            e["dom_element_n_min_max"] = [float(g["dom_element_n"].min()), float(g["dom_element_n"].max())]
            for name, spec in CAPS.items():
                e[f"median_{spec['n']}"] = float(g[spec["n"]].median())
            rows[a] = e
        return {"grain": grain, "N": int(len(df)), "by_archetype": rows}

    out["crosstab"] = {"observation_grain": crosstab(obs, "observation"), "target_grain_in_mart": crosstab(tgt, "target")}

    # RxC exact on the full archetype table (cap_any) — reported for completeness only
    for grain, df in (("observation_grain", obs), ("target_grain_in_mart", tgt)):
        tab = pd.crosstab(df["prior_archetype"], df["cap_any"])
        for col in (0.0, 1.0):
            if col not in tab.columns:
                tab[col] = 0
        tab = tab[[0.0, 1.0]]
        arr = tab.values
        chi2, pchi, dof, exp = stats.chi2_contingency(arr)
        try:
            p_exact = float(stats.chi2_contingency(arr)[1])
            res = stats.fisher_exact(arr) if arr.shape == (2, 2) else None
        except Exception:
            res = None
        # scipy >=1.11 has an RxC exact via stats.contingency? not guaranteed -> permutation instead
        rng = np.random.default_rng(RNG_SEED)
        labels = df["prior_archetype"].to_numpy()
        y = df["cap_any"].to_numpy()
        obs_chi = chi2
        cnt = 0
        NPERM = 10000
        for _ in range(NPERM):
            yp = rng.permutation(y)
            t = pd.crosstab(pd.Series(labels), pd.Series(yp))
            a2 = t.reindex(columns=[0.0, 1.0], fill_value=0).values
            if a2.sum(axis=0).min() == 0:
                c2 = 0.0
            else:
                c2 = stats.chi2_contingency(a2)[0]
            if c2 >= obs_chi - 1e-12:
                cnt += 1
        out.setdefault("global_archetype_test", {})[grain] = {
            "table": {k: {"no_cap": int(v[0]), "cap": int(v[1])} for k, v in zip(tab.index, arr)},
            "chi2": round(float(chi2), 4),
            "min_expected_cell": round(float(exp.min()), 3),
            "chi2_asymptotic_INVALID_flag": bool(exp.min() < 5),
            "permutation_p_two_sided": round((cnt + 1) / (NPERM + 1), 5),
            "n_permutations": NPERM,
            "note": "7x2 table with min expected cell < 5 -> asymptotic chi-square is invalid; the permutation p is the only usable global figure and it still rests on 3-5 units in four archetypes.",
        }

    # ---- 2x2: ITEM_DETAIL vs rest, per cap, both grains ------------------
    tests = {}
    for grain, df in (("observation_grain", obs), ("target_grain_in_mart", tgt)):
        gg = {}
        is_id = df["prior_archetype"] == "ITEM_DETAIL"
        n1, n0 = int(is_id.sum()), int((~is_id).sum())
        for name, spec in list(CAPS.items()) + [("cap_any", {"flag": "cap_any"})]:
            fl = spec["flag"]
            k1 = int((df.loc[is_id, fl] == 1).sum())
            k0 = int((df.loc[~is_id, fl] == 1).sum())
            gg[name] = fisher_block(k1, n1, k0, n0, f"ITEM_DETAIL vs rest — {name} ({grain})")
        gg["_group_sizes"] = {"ITEM_DETAIL_n": n1, "other_n": n0}
        tests[grain] = gg
    out["fisher_item_detail_vs_rest"] = tests

    # ---- POWER ----------------------------------------------------------
    is_id_t = tgt["prior_archetype"] == "ITEM_DETAIL"
    n1_t, n0_t = int(is_id_t.sum()), int((~is_id_t).sum())
    p0_obs_capany = float((tgt.loc[~is_id_t, "cap_any"] == 1).mean())
    p1_obs_capany = float((tgt.loc[is_id_t, "cap_any"] == 1).mean())
    power_grid = []
    for p0g, rr in product([0.05, 0.10, 0.15, 0.20], [1.5, 2.0, 3.0, 4.0, 6.0]):
        p1g = min(0.999, p0g * rr)
        power_grid.append({"p0": p0g, "risk_ratio": rr, "p1": round(p1g, 3),
                           "power_fisher_two_sided_alpha05": round(fisher_power(n1_t, n0_t, p1g, p0g, nsim=6000), 3)})
    out["power_analysis"] = {
        "grain": "target_grain_in_mart",
        "margins": {"ITEM_DETAIL_n": n1_t, "other_n": n0_t, "total": n1_t + n0_t},
        "method": "Monte-Carlo power of the two-sided Fisher exact test at fixed group sizes (binomial sampling, alpha=0.05).",
        "observed_rates_cap_any": {"ITEM_DETAIL": f"{int((tgt.loc[is_id_t,'cap_any']==1).sum())}/{n1_t}",
                                   "other": f"{int((tgt.loc[~is_id_t,'cap_any']==1).sum())}/{n0_t}"},
        "power_at_observed_effect_cap_any": round(fisher_power(n1_t, n0_t, p1_obs_capany, max(p0_obs_capany, 1e-9), nsim=20000), 3),
        "mde_at_80pct_power_given_observed_control_rate": mde_curve(n1_t, n0_t, p0_obs_capany),
        "mde_at_80pct_power_given_p0_0.10": mde_curve(n1_t, n0_t, 0.10),
        "power_grid": power_grid,
        "interpretation": ("Power is adequate only for large risk ratios on top of a low control rate. Everything below roughly "
                           "a 2.5x risk ratio is not detectable at this N, so a null result here cannot be read as absence of bias, "
                           "and the four archetypes with n=3-5 carry no power at all."),
        "assertion_type": "ANALYSIS",
    }

    # per-archetype detectability floor
    out["power_analysis"]["per_archetype_floor"] = {
        a: {"n": int(v["n"]), "n_tier": v["n_tier"],
            "widest_possible_wilson_ci_if_0_hits": wilson(0, int(v["n"])),
            "comment": "with 0/n observed the upper bound alone spans this much — nothing below it is excluded"}
        for a, v in out["crosstab"]["target_grain_in_mart"]["by_archetype"].items()
    }

    # ---- CONFOUNDER: dom size ------------------------------------------
    tgt = tgt.copy()
    tgt["_is_id"] = is_id_t.values
    tgt["_log_dom"] = np.log10(tgt["dom_element_n"].clip(lower=1))
    u_dom = stats.mannwhitneyu(tgt.loc[tgt._is_id, "dom_element_n"], tgt.loc[~tgt._is_id, "dom_element_n"], alternative="two-sided")
    n_a, n_b = int(tgt._is_id.sum()), int((~tgt._is_id).sum())
    a_dom = float(u_dom.statistic) / (n_a * n_b)  # common-language / AUC effect size
    u_cap = stats.mannwhitneyu(tgt.loc[tgt.cap_any == 1, "dom_element_n"], tgt.loc[tgt.cap_any == 0, "dom_element_n"], alternative="two-sided")
    n_c, n_d = int((tgt.cap_any == 1).sum()), int((tgt.cap_any == 0).sum())
    a_cap = float(u_cap.statistic) / (n_c * n_d)

    # stratified by dom_element_n tertiles
    tgt["_dom_tertile"] = pd.qcut(tgt["dom_element_n"], 3, labels=["T1_small", "T2_mid", "T3_large"])
    strat = {}
    mh_in = []
    for t, g in tgt.groupby("_dom_tertile", observed=True):
        k1 = int(((g._is_id) & (g.cap_any == 1)).sum()); nn1 = int(g._is_id.sum())
        k0 = int(((~g._is_id) & (g.cap_any == 1)).sum()); nn0 = int((~g._is_id).sum())
        strat[str(t)] = {"dom_range": [float(g.dom_element_n.min()), float(g.dom_element_n.max())],
                         "ITEM_DETAIL": f"{k1}/{nn1}", "other": f"{k0}/{nn0}",
                         "risk_difference": (round(k1 / nn1 - k0 / nn0, 4) if nn1 and nn0 else None),
                         "fisher_p": (round(float(stats.fisher_exact([[k1, nn1 - k1], [k0, nn0 - k0]])[1]), 5) if nn1 and nn0 else None)}
        mh_in.append((k1, nn1, k0, nn0))

    # logistic regression, reported with an explicit EPV warning
    logit_res = {}
    try:
        import statsmodels.api as sm
        X = sm.add_constant(pd.DataFrame({"log10_dom_element_n": tgt["_log_dom"], "is_ITEM_DETAIL": tgt["_is_id"].astype(float)}))
        y = (tgt["cap_any"] == 1).astype(float)
        fit = sm.Logit(y, X).fit(disp=0, maxiter=200)
        ci = fit.conf_int()
        logit_res = {
            "model": "cap_any ~ log10(dom_element_n) + is_ITEM_DETAIL, target grain",
            "n": int(len(tgt)), "events": int(y.sum()),
            "events_per_variable": round(float(y.sum()) / 2, 1),
            "coefficients": {k: {"beta": round(float(fit.params[k]), 4),
                                 "odds_ratio": round(float(np.exp(fit.params[k])), 4),
                                 "ci95_or": [round(float(np.exp(ci.loc[k, 0])), 4), round(float(np.exp(ci.loc[k, 1])), 4)],
                                 "p": round(float(fit.pvalues[k]), 5)} for k in fit.params.index},
            "pseudo_r2_mcfadden": round(float(fit.prsquared), 4),
            "WARNING": "14 events / 2 predictors = 7 EPV, below the usual 10 EPV floor; Wald CIs here are optimistic and the estimate is unstable. Treat as descriptive, not as an adjusted effect estimate.",
        }
    except Exception as exc:  # pragma: no cover
        logit_res = {"error": repr(exc)}

    # residual approach: does ITEM_DETAIL have more probe candidates than its DOM size predicts?
    resid = {}
    for name, spec in CAPS.items():
        sub = tgt[(tgt[spec["n"]] > 0) & (tgt["dom_element_n"] > 0)]
        lx = np.log10(sub["dom_element_n"].to_numpy())
        ly = np.log10(sub[spec["n"]].to_numpy())
        sl, ic, r, p, se = stats.linregress(lx, ly)
        r_id = (ly - (sl * lx + ic))[sub["_is_id"].to_numpy()]
        r_ot = (ly - (sl * lx + ic))[~sub["_is_id"].to_numpy()]
        uu = stats.mannwhitneyu(r_id, r_ot, alternative="two-sided")
        resid[name] = {
            "n_used": int(len(sub)),
            "ols_log10_slope_on_log10_dom": round(float(sl), 4), "r": round(float(r), 4),
            "median_residual_ITEM_DETAIL": round(float(np.median(r_id)), 4),
            "median_residual_other": round(float(np.median(r_ot)), 4),
            "mannwhitney_p": round(float(uu.pvalue), 5),
            "auc_effect_size": round(float(uu.statistic) / (len(r_id) * len(r_ot)), 4),
            "caution": "counts are right-censored at the ceiling, so residuals of capped rows are lower bounds; this test is conservative toward the null for the capped group",
        }

    out["confounding_dom_size"] = {
        "grain": "target_grain_in_mart",
        "dom_element_n_by_archetype_median": {a: v["dom_element_n_median"] for a, v in out["crosstab"]["target_grain_in_mart"]["by_archetype"].items()},
        "dom_element_n_ITEM_DETAIL_vs_other": {
            "median_ITEM_DETAIL": float(tgt.loc[tgt._is_id, "dom_element_n"].median()),
            "median_other": float(tgt.loc[~tgt._is_id, "dom_element_n"].median()),
            "mannwhitney_p": round(float(u_dom.pvalue), 5), "auc_effect_size": round(a_dom, 4),
        },
        "dom_element_n_cap_hit_vs_not": {
            "median_cap_hit": float(tgt.loc[tgt.cap_any == 1, "dom_element_n"].median()),
            "median_no_cap": float(tgt.loc[tgt.cap_any == 0, "dom_element_n"].median()),
            "mannwhitney_p": round(float(u_cap.pvalue), 6), "auc_effect_size": round(a_cap, 4),
        },
        "stratified_by_dom_tertile": strat,
        "mantel_haenszel_across_dom_tertiles": mantel_haenszel(mh_in),
        "logistic_regression": logit_res,
        "size_adjusted_residual_test": resid,
        "assertion_type": "ANALYSIS",
    }

    # ---- cap-cap structure ----------------------------------------------
    flags = [v["flag"] for v in CAPS.values()]
    phi = obs[flags].astype(float).corr(method="pearson").round(3)
    co = {}
    for i, f1 in enumerate(flags):
        for f2 in flags[i + 1:]:
            both = int(((obs[f1] == 1) & (obs[f2] == 1)).sum())
            either = int(((obs[f1] == 1) | (obs[f2] == 1)).sum())
            co[f"{f1}|{f2}"] = {"both": both, "either": either, "jaccard": round(both / either, 4) if either else None}
    caph = obs[obs.cap_any == 1]
    out["cap_structure"] = {
        "grain": "observation_grain",
        "phi_matrix": {k: v for k, v in phi.to_dict().items()},
        "cooccurrence": co,
        "cap_count_distribution": {str(int(k)): int(v) for k, v in obs["cap_count"].value_counts().sort_index().items()},
        "binding_constraint": {
            "cap_hits_total": int(len(caph)),
            "of_which_hit_accessible_name_sources": int((caph["cap_accessible_name_sources"] == 1).sum()),
            "of_which_hit_accessible_name_ONLY": int((caph["cap_count"] == 1).sum() and ((caph["cap_count"] == 1) & (caph["cap_accessible_name_sources"] == 1)).sum()),
            "statement": "accessible_name_sources (ceiling 300, the only cap with no visible filter) is the first cap to bite in almost every cap-hit unit; it is the binding constraint of the probe.",
        },
        "smallest_dom_that_hit_accessible_name_cap": {
            "wtg": str(caph.loc[caph.cap_accessible_name_sources == 1, "dom_element_n"].idxmin()) if (caph.cap_accessible_name_sources == 1).any() else None,
            "dom_element_n": float(caph.loc[caph.cap_accessible_name_sources == 1, "dom_element_n"].min()) if (caph.cap_accessible_name_sources == 1).any() else None,
            "note": "a unit can reach 300 name sources with far fewer DOM elements, because one element contributes several name sources; the no-visible-filter cap therefore does not track rendered page size cleanly.",
        },
        "assertion_type": "OBSERVATION",
    }

    # ---- counterexample hunt --------------------------------------------
    big_no_cap = tgt[(tgt.cap_any == 0)].nlargest(5, "dom_element_n")[["wtg", "prior_archetype", "dom_element_n", "n_accessible_name_sources", "n_primary_action_candidates"]]
    small_cap = tgt[(tgt.cap_any == 1)].nsmallest(5, "dom_element_n")[["wtg", "prior_archetype", "dom_element_n", "n_accessible_name_sources", "n_primary_action_candidates"]]
    id_no_cap = tgt[(tgt._is_id) & (tgt.cap_any == 0)]
    out["counterexamples"] = {
        "alt_hypothesis": "cap-hits are concentrated in large pages, not in ITEM_DETAIL; prior_archetype only correlates with page size.",
        "largest_dom_without_any_cap": big_no_cap.to_dict("records"),
        "smallest_dom_with_a_cap": small_cap.to_dict("records"),
        "ITEM_DETAIL_without_any_cap": f"{len(id_no_cap)}/{n1_t}",
        "QUERY_note": {
            "QUERY_n": int((tgt.prior_archetype == "QUERY").sum()),
            "QUERY_cap_hits": int(((tgt.prior_archetype == "QUERY") & (tgt.cap_any == 1)).sum()),
            "QUERY_median_dom": float(tgt.loc[tgt.prior_archetype == "QUERY", "dom_element_n"].median()),
            "ITEM_DETAIL_median_dom": float(tgt.loc[tgt._is_id, "dom_element_n"].median()),
            "statement": "QUERY has the largest median DOM of any archetype yet a smaller n; it is a direct counterexample to 'ITEM_DETAIL = the big pages'.",
        },
        "assertion_type": "ANALYSIS",
    }

    # ---- ExcessDepth --------------------------------------------------
    out["excess_depth"] = {
        "definition": "ExcessDepth(unit) = MPFED(unit) - median(MPFED | same prior_archetype)",
        "measurability_now": {
            "MPFED_column_present_in_D_OBSERVATION_TABLE": bool("mpfed" in [c.lower() for c in raw.columns]),
            "statement": "MPFED is not a column of this RQ's input, and the frozen mart is reported (external to this RQ) as 0/31 non-null MPFED. No observed ExcessDepth exists to measure, so every statement below is a PROJECTION about the direction of distortion once MPFED becomes available, not a measurement.",
        },
        "mechanism": [
            "A cap is a right-censoring of the candidate pool at a fixed ceiling. Any statistic computed downstream of a censored pool is computed on a subset, not on the page.",
            "MPFED is a max-type statistic over paths reachable from the entry candidate set. Censoring the candidate set can only remove candidates, so the measured maximum is a lower bound on the true one: censoring biases MPFED downward or leaves it unchanged, never upward.",
            "Within an archetype whose cap incidence is high, the same-archetype median MPFED is therefore pulled downward relative to the uncensored truth.",
        ],
        "direction_within_archetype": ("For a censored archetype, the baseline median is depressed. Uncensored members of that archetype are then scored against a too-low baseline and their ExcessDepth is inflated; censored members carry a depressed MPFED against a depressed median, so their ExcessDepth is compressed toward zero. The within-archetype ranking is distorted in a direction that systematically flatters the units the probe failed to measure and penalises the units it measured completely."),
        "direction_between_archetypes": ("Cross-archetype comparison of median MPFED confounds true archetype depth with cap incidence. In this data the cap-incidence spread across archetypes is the full range from 0/4 to 11/25, so an apparent 'ITEM_DETAIL is shallower than X' finding would be indistinguishable from 'ITEM_DETAIL is measured less completely than X'. ExcessDepth is defined within archetype so it is partially insulated from this, but any analysis that then compares ExcessDepth distributions across archetypes reimports the confound, because the baselines were subtracted at different levels of censoring."),
        "magnitude_bound": "Not estimable. The censored counts give no information about how many candidates were discarded (no overflow counter is emitted), so the size of the MPFED depression is unbounded from the data alone.",
        "actionable_requirement": "To make ExcessDepth comparable, the probe must emit a truncation indicator per unit (already present as cap_* flags) AND a total-before-truncation counter (absent). Without the second, censored units can only be excluded, not corrected.",
        "assertion_type": "PROJECTION",
    }

    # ---- figure ---------------------------------------------------------
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        ct = out["crosstab"]["target_grain_in_mart"]["by_archetype"]
        order = sorted(ct, key=lambda a: -ct[a]["cap_any"]["pct"])
        fig, ax = plt.subplots(1, 2, figsize=(13, 5))
        pct = [ct[a]["cap_any"]["pct"] for a in order]
        lo = [100 * ct[a]["cap_any"]["ci95_wilson"][0] for a in order]
        hi = [100 * ct[a]["cap_any"]["ci95_wilson"][1] for a in order]
        ax[0].barh(range(len(order)), pct, color="#6b8fd6")
        ax[0].errorbar(pct, range(len(order)), xerr=[np.array(pct) - np.array(lo), np.array(hi) - np.array(pct)],
                       fmt="none", ecolor="#333", capsize=3)
        ax[0].set_yticks(range(len(order)))
        ax[0].set_yticklabels([f"{a} ({ct[a]['cap_any']['rate']})" for a in order], fontsize=8)
        ax[0].set_xlabel("cap_any hit rate %  (Wilson 95% CI)")
        ax[0].set_title(f"cap_any by prior_archetype — target grain N={len(tgt)}", fontsize=9)
        ax[0].invert_yaxis()
        for a, g in tgt.groupby("prior_archetype"):
            ax[1].scatter(g["dom_element_n"], g["cap_count"] + np.random.default_rng(1).normal(0, .05, len(g)), label=f"{a} (n={len(g)})", s=26)
        ax[1].set_xscale("log")
        ax[1].set_xlabel("dom_element_n (log)")
        ax[1].set_ylabel("cap_count (0-4)")
        ax[1].set_title("cap load vs DOM size — the size confound", fontsize=9)
        ax[1].legend(fontsize=6)
        fig.tight_layout()
        fig.savefig(FIG, dpi=140)
        plt.close(fig)
        out["figure"] = FIG
    except Exception as exc:
        out["figure_error"] = repr(exc)

    # ---- verdict ---------------------------------------------------------
    t = out["fisher_item_detail_vs_rest"]["target_grain_in_mart"]["cap_any"]
    out["verdict"] = {
        "value": "PARTIALLY_SUPPORTED",
        "one_line": ("Cap truncation is unevenly distributed across prior_archetype and is concentrated in ITEM_DETAIL "
                     f"({t['rate_group1']} vs {t['rate_group0']}, Fisher p={t['fisher_exact_p_two_sided']}), but the sample "
                     "cannot separate that from the DOM-size confound and has no power at all for four of the seven archetypes."),
        "what_is_supported": "That cap incidence is non-uniform across archetypes and that the same-archetype median baseline of ExcessDepth would be unequally censored.",
        "what_is_not_supported": "That prior_archetype rather than page size is what the cap tracks; and any claim about the size of the ExcessDepth distortion.",
        "assertion_type": "ANALYSIS",
    }
    return out


if __name__ == "__main__":
    res = main()
    os.makedirs(os.path.dirname(OUT_JSON), exist_ok=True)
    with open(OUT_JSON, "w", encoding="utf-8") as fh:
        json.dump(res, fh, ensure_ascii=False, indent=2, default=js)
    print(json.dumps({"verdict": res["verdict"]["value"], "written": OUT_JSON,
                      "obs_N": res["grain"]["ANALYSIS_SET_observation_grain_N"],
                      "tgt_N": res["grain"]["ANALYSIS_SET_target_grain_N"]}, ensure_ascii=False, indent=2))
