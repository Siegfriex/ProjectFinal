#!/usr/bin/env python
"""RQ-D9 — Is artifact SIZE a proxy for observation QUALITY?

Ticket: T-B-RQ-D-001 Q2.
Single input: results/D_OBSERVATION_TABLE.csv. No hidden state; Restart->Run All safe.
Outputs: results/RQ_D9_quality_proxy.json, figures/RQ_D9_*.png

Non-parametric first (Spearman, tie-corrected midranks; Kendall tau-b as tie-robust
cross-check; percentile bootstrap CIs). No causal claims are made anywhere.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

ROOT = Path("/home/sieg/projects-wsl/ProjectFinal/.agent_worktrees/claude_d_research"
            "/research/landing_accessibility/research_d")
CSV = ROOT / "results" / "D_OBSERVATION_TABLE.csv"
OUT_JSON = ROOT / "results" / "RQ_D9_quality_proxy.json"
FIGDIR = ROOT / "figures"

SEED = 20260827
B_BOOT = 10000

# Cap constants, read from l0_probe.js @2281c85 (see ticket).
CAPS = {
    "n_primary_action_candidates": {"cap": 200, "visible_filtered": True},
    "n_accessible_name_sources": {"cap": 300, "visible_filtered": False},
    "n_target_size": {"cap": 300, "visible_filtered": True},
    "n_contrast": {"cap": 400, "visible_filtered": "filter-passing only"},
}
UNREPORTED_TRUNCATIONS = {
    "motion_body_star_slice": 3000,
    "animated_elements_slice": 60,
    "endpoint_signals_innerText_slice": 4000,
}

SIGNALS = ["n_primary_action_candidates", "n_accessible_name_sources",
           "n_target_size", "n_contrast"]

# Candidate proxies for "observation quality" / signal richness.
PROXY_CANDIDATES = [
    "dom_bytes", "ax_bytes", "css_bytes", "probe_bytes",
    "dom_element_n", "dom_body_element_n", "dom_interactive_n",
    "dom_a_href_n", "dom_button_n", "dom_input_n",
    "dom_role_n", "dom_aria_label_n", "dom_script_n",
    "dom_body_text_len", "probe_scroll_height",
]

rng = np.random.default_rng(SEED)


# ---------------------------------------------------------------- helpers
def _midrank(a):
    """Tie-corrected midranks along the last axis (same convention as scipy)."""
    a = np.asarray(a, float)
    order = np.argsort(a, axis=-1, kind="stable")
    ranks = np.empty_like(order, dtype=float)
    idx = np.arange(a.shape[-1])
    np.put_along_axis(ranks, order, np.broadcast_to(
        idx.astype(float), a.shape).copy(), axis=-1)
    srt = np.take_along_axis(a, order, axis=-1)
    # average ranks within runs of equal values (vectorised over rows)
    out = ranks.copy()
    for r in range(a.shape[0]) if a.ndim == 2 else [None]:
        row = srt if a.ndim == 1 else srt[r]
        vals, first, cnt = np.unique(row, return_index=True, return_counts=True)
        mid = first + (cnt - 1) / 2.0
        lookup = np.repeat(mid, cnt)
        tgt = out if a.ndim == 1 else out[r]
        ordr = order if a.ndim == 1 else order[r]
        np.put_along_axis(tgt, ordr, lookup, axis=-1)
    return out


def _spearman_rows(xr, yr):
    """Pearson r between pre-ranked row pairs -> Spearman rho per row."""
    xc = xr - xr.mean(axis=-1, keepdims=True)
    yc = yr - yr.mean(axis=-1, keepdims=True)
    num = (xc * yc).sum(axis=-1)
    den = np.sqrt((xc ** 2).sum(axis=-1) * (yc ** 2).sum(axis=-1))
    with np.errstate(invalid="ignore", divide="ignore"):
        return np.where(den > 0, num / den, np.nan)


def spearman_ci(x, y, b=B_BOOT):
    """Spearman rho with percentile bootstrap CI.

    Ties are handled by midranks (scipy's tie-corrected convention) both in the
    point estimate and inside every bootstrap resample. Resamples that collapse
    to a single distinct value on either axis are dropped (rho undefined there)
    and counted; binary predictors such as cap_any are therefore supported, where
    Spearman reduces to a rank-biserial correlation.
    Vectorised: resampling and ranking happen as array ops, not a Python loop.
    """
    x = np.asarray(x, float)
    y = np.asarray(y, float)
    ok = np.isfinite(x) & np.isfinite(y)
    x, y = x[ok], y[ok]
    n = len(x)
    res = stats.spearmanr(x, y)
    tau = stats.kendalltau(x, y, variant="b")

    i = rng.integers(0, n, size=(b, n))
    xs, ys = x[i], y[i]
    keep = np.array([len(np.unique(r)) >= 2 for r in xs]) & \
           np.array([len(np.unique(r)) >= 2 for r in ys])
    dropped = int((~keep).sum())
    xs, ys = xs[keep], ys[keep]
    boots = _spearman_rows(_midrank(xs), _midrank(ys))
    boots = boots[np.isfinite(boots)]
    if boots.size == 0:                       # fully degenerate; CI undefined
        return {"n": int(n), "spearman_rho": round(float(res.statistic), 4),
                "spearman_p": float(f"{res.pvalue:.4g}"),
                "kendall_tau_b": round(float(tau.statistic), 4),
                "kendall_p": float(f"{tau.pvalue:.4g}"),
                "boot_ci95_lo": None, "boot_ci95_hi": None,
                "boot_n_effective": 0, "boot_dropped": int(b),
                "ci_excludes_zero": None}
    lo, hi = float(np.percentile(boots, 2.5)), float(np.percentile(boots, 97.5))
    return {
        "n": int(n),
        "spearman_rho": round(float(res.statistic), 4),
        "spearman_p": float(f"{res.pvalue:.4g}"),
        "kendall_tau_b": round(float(tau.statistic), 4),
        "kendall_p": float(f"{tau.pvalue:.4g}"),
        "boot_ci95_lo": round(lo, 4),
        "boot_ci95_hi": round(hi, 4),
        "boot_n_effective": int(len(boots)),
        "boot_dropped": dropped,
        "ci_excludes_zero": bool(lo > 0 or hi < 0),
    }


def mwu(a, b_):
    """Mann-Whitney U + Vargha-Delaney A12 effect size."""
    a = np.asarray(a, float)
    b_ = np.asarray(b_, float)
    a, b_ = a[np.isfinite(a)], b_[np.isfinite(b_)]
    u, p = stats.mannwhitneyu(a, b_, alternative="two-sided")
    return {
        "n_group1": int(len(a)), "n_group2": int(len(b_)),
        "median_group1": float(np.median(a)), "median_group2": float(np.median(b_)),
        "U": float(u), "p": float(f"{p:.4g}"),
        "A12": round(float(u / (len(a) * len(b_))), 4),
    }


def j(o):
    """Make numpy scalars JSON-serialisable."""
    if isinstance(o, dict):
        return {k: j(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [j(v) for v in o]
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.floating,)):
        return None if not np.isfinite(o) else float(o)
    if isinstance(o, (np.bool_,)):
        return bool(o)
    if isinstance(o, float) and not np.isfinite(o):
        return None
    return o


HANGUL = range(0xAC00, 0xD7A4)


def has_hangul(s):
    return any(0xAC00 <= ord(c) <= 0xD7A3 for c in str(s))


def looks_mojibake(s):
    """Latin-1-supplement-heavy string with no Hangul == mis-decoded UTF-8."""
    s = str(s)
    latin_sup = sum(1 for c in s if 0x80 <= ord(c) <= 0x24F)
    return latin_sup > 0 and not has_hangul(s)


# ---------------------------------------------------------------- load
raw = pd.read_csv(CSV)
report = {
    "rq": "RQ-D9 — relationship structure between dom.html size, probe signal "
          "richness, and cap attainment; what can/cannot proxy observation quality",
    "ticket": "T-B-RQ-D-001 Q2",
    "input": {"path": str(CSV), "rows": int(len(raw)), "cols": int(raw.shape[1])},
    "cap_constants_from_l0_probe_js_2281c85": CAPS,
    "unreported_truncation_points": UNREPORTED_TRUNCATIONS,
    "seed": SEED, "bootstrap_B": B_BOOT,
}

# ---------------------------------------------------------------- grain
# in_mart==1 is already the de-duplicated target mart: the second run of each
# re-executed target carries in_mart==0. probe_present==1 keeps 58 obs but
# re-admits 4 duplicate re-runs, breaking observation independence.
grain = {
    "n_rows_total": int(len(raw)),
    "n_in_mart_1": int((raw.in_mart == 1).sum()),
    "n_in_mart_1_unique_wtg": int(raw.loc[raw.in_mart == 1, "wtg"].nunique()),
    "n_probe_present_1": int((raw.probe_present == 1).sum()),
    "n_probe_present_1_unique_wtg": int(raw.loc[raw.probe_present == 1, "wtg"].nunique()),
}
main = raw[(raw.in_mart == 1) & (raw.probe_present == 1)].copy()
alt = raw[raw.probe_present == 1].copy()          # sensitivity grain
grain.update({
    "primary_grain": "in_mart==1 AND probe_present==1",
    "primary_grain_n": int(len(main)),
    "primary_grain_unique_wtg": int(main.wtg.nunique()),
    "primary_grain_rationale": (
        "in_mart==1 is the de-duplicated target mart (56 targets, 56 unique wtg; "
        "the 2nd run of each re-executed target is flagged in_mart==0), so it "
        "guarantees one row per target. Intersecting with probe_present==1 drops "
        "the 2 targets with no probe payload, for which every signal column is "
        "NaN and no size/richness relation is computable. The resulting n=54 has "
        "ZERO missingness on all analysis columns, so every denominator below is "
        "54 unless stated. The alternative grain probe_present==1 (n=58) "
        "re-admits 4 duplicate re-runs of 4 targets and violates independence; "
        "it is used only as a sensitivity check."),
    "dropped_from_in_mart_for_no_probe": raw[(raw.in_mart == 1) & (raw.probe_present != 1)][
        ["prior_service", "wtg", "dom_bytes", "dom_element_n",
         "dom_interactive_n", "dom_body_empty"]].to_dict("records"),
})
grain["missing_per_analysis_col_primary_grain"] = {
    c: int(main[c].isna().sum())
    for c in PROXY_CANDIDATES + SIGNALS + ["cap_any", "cap_count", "dom_body_empty"]
}
report["grain"] = grain

# ---------------------------------------------------------------- derived
main["bytes_per_element"] = main.dom_bytes / main.dom_element_n
main["capture_ratio"] = np.where(
    main.dom_interactive_n > 0,
    main.n_primary_action_candidates / main.dom_interactive_n, np.nan)
main["dom_title_mojibake"] = main.dom_title.map(looks_mojibake)
main["title_mismatch"] = (main.dom_title.fillna("#NA#")
                          != main.probe_title.fillna("#NA#"))
# composite richness = mean percentile rank over the 4 probe signals
main["signal_richness"] = main[SIGNALS].rank(pct=True).mean(axis=1)

# ================================================================
# STEP 1 — reproduce B's two counterexamples
# ================================================================
probe_rows = main.sort_values("dom_bytes")
smallest_all = raw[raw.dom_parse_ok == 1].nsmallest(1, "dom_bytes")
smin = probe_rows.iloc[0]
smax = probe_rows.iloc[-1]
tied_min = main[main.dom_bytes == smin.dom_bytes]

step1 = {
    "assertion_type": "OBSERVATION",
    "b_claim_small": {"dom_bytes": 1657, "n_primary_action_candidates": 24},
    "b_claim_large": {"dom_bytes": 4_700_000, "n_primary_action_candidates": 17},
    "reproduced_small": {
        "dom_bytes": float(smin.dom_bytes),
        "n_primary_action_candidates": float(smin.n_primary_action_candidates),
        "matches_b": bool(smin.dom_bytes == 1657
                          and smin.n_primary_action_candidates == 24),
        "n_observations_tied_at_this_dom_bytes": int(len(tied_min)),
        "tied_services": tied_min.prior_service.tolist(),
        "tied_wtg": tied_min.wtg.tolist(),
        "note": (
            "REPRODUCED but under-specified in the ticket: dom_bytes==1657 is not "
            "one observation, it is TWO distinct targets (distinct wtg) whose "
            "dom/probe measurements are byte-identical across every analysed "
            "column. Both are dom_body_empty==1 with dom_interactive_n==0 while "
            "the probe reports 24 primary actions -- i.e. the DOM artifact and "
            "the probe are not describing the same page state."),
    },
    "reproduced_large": {
        "dom_bytes": float(smax.dom_bytes),
        "n_primary_action_candidates": float(smax.n_primary_action_candidates),
        "service": smax.prior_service,
        "dom_element_n": float(smax.dom_element_n),
        "dom_interactive_n": float(smax.dom_interactive_n),
        "bytes_per_element": round(float(smax.dom_bytes / smax.dom_element_n), 1),
        "matches_b": bool(smax.dom_bytes == 4778840
                          and smax.n_primary_action_candidates == 17),
    },
    "true_global_min_dom_bytes": {
        "dom_bytes": float(smallest_all.iloc[0].dom_bytes),
        "service": smallest_all.iloc[0].prior_service,
        "probe_present": float(smallest_all.iloc[0].probe_present)
        if pd.notna(smallest_all.iloc[0].probe_present) else None,
        "note": ("The absolute smallest parsed dom.html in the table is 314 bytes "
                 "(no probe payload), so B's 1657 is the smallest dom_bytes AMONG "
                 "probe-bearing observations. B's implicit grain was "
                 "probe_present==1, which this analysis adopts."),
    },
    "tied_min_identical_columns": bool(
        len(tied_min) == 2
        and (tied_min.iloc[0][SIGNALS].values == tied_min.iloc[1][SIGNALS].values).all()
        and tied_min.iloc[0].dom_element_n == tied_min.iloc[1].dom_element_n),
}
report["step1_counterexample_reproduction"] = step1

# ================================================================
# STEP 2 — how many dimensions is "signal richness"?
# ================================================================
sig_corr = main[SIGNALS].corr(method="spearman").round(4)
report["step2_signal_dimensionality"] = {
    "assertion_type": "ANALYSIS",
    "spearman_matrix": j(sig_corr.to_dict()),
    "min_offdiag_rho": round(float(
        sig_corr.where(~np.eye(4, dtype=bool)).min().min()), 4),
    "primary_equals_target_size_count": int(
        (main.n_primary_action_candidates == main.n_target_size).sum()),
    "primary_vs_target_size_rho": round(float(stats.spearmanr(
        main.n_primary_action_candidates, main.n_target_size).statistic), 4),
    "finding": (
        "The four probe signals are not four independent quality dimensions. "
        "n_primary_action_candidates and n_target_size are effectively the same "
        "measurement at two different caps (200 vs 300): rho=0.999 and exactly "
        f"equal in {int((main.n_primary_action_candidates == main.n_target_size).sum())}/54 "
        "observations; where they differ, n_target_size >= n_primary in every "
        "case. All off-diagonal rho >= 0.83. 'Signal richness' is therefore ~1 "
        "latent dimension, so a proxy only has to track one thing."),
}

# ================================================================
# STEP 3 — proxy candidate screen (Spearman + bootstrap CI)
# ================================================================
proxy_tbl = {}
for v in PROXY_CANDIDATES + ["bytes_per_element", "capture_ratio", "signal_richness"]:
    proxy_tbl[v] = {t: spearman_ci(main[v], main[t]) for t in SIGNALS}
report["step3_proxy_screen_primary_grain"] = j(proxy_tbl)

report["step3_headline"] = {
    "assertion_type": "ANALYSIS",
    "dom_bytes_vs_primary": proxy_tbl["dom_bytes"]["n_primary_action_candidates"],
    "dom_interactive_n_vs_primary": proxy_tbl["dom_interactive_n"]["n_primary_action_candidates"],
    "dom_element_n_vs_primary": proxy_tbl["dom_element_n"]["n_primary_action_candidates"],
    "finding": (
        "dom_bytes rho=+0.264 (n=54, p=0.054, bootstrap CI95 [-0.024,+0.524]) -- "
        "the CI INCLUDES ZERO, so no reliable monotone association with signal "
        "richness. dom_interactive_n rho=+0.780 (CI95 [+0.602,+0.896]) and "
        "dom_element_n rho=+0.707 (CI95 [+0.500,+0.847]) both exclude zero. "
        "Structural COUNTS from the same dom.html track richness; the BYTE SIZE "
        "of that same file does not."),
}

# Pearson-vs-Spearman contrast (methodology note, not a headline)
report["step3_pearson_contrast"] = {
    "assertion_type": "ANALYSIS",
    "pearson_dom_bytes_raw": round(float(stats.pearsonr(
        main.dom_bytes, main.n_primary_action_candidates).statistic), 4),
    "pearson_log10_dom_bytes": round(float(stats.pearsonr(
        np.log10(main.dom_bytes), main.n_primary_action_candidates).statistic), 4),
    "pearson_dom_interactive_n": round(float(stats.pearsonr(
        main.dom_interactive_n, main.n_primary_action_candidates).statistic), 4),
    "note": ("dom_bytes spans 1.66e3..4.78e6 (3.5 orders of magnitude) with a "
             "single 4.8MB point; raw Pearson r=0.096 is dominated by that point "
             "and log10 lifts it to 0.299. Reporting Pearson alone on this column "
             "would be misleading in either direction, which is why Spearman is "
             "the primary statistic."),
}

# ================================================================
# STEP 4 — monotonicity of dom_bytes (is it non-monotone / inverted-U?)
# ================================================================
main["q_bytes"] = pd.qcut(main.dom_bytes, 5, labels=[1, 2, 3, 4, 5])
main["q_inter"] = pd.qcut(main.dom_interactive_n, 5, labels=[1, 2, 3, 4, 5])


def quint(col, by):
    g = main.groupby(by, observed=True).agg(
        n=("dom_bytes", "size"),
        proxy_median=(col, "median"),
        primary_median=("n_primary_action_candidates", "median"),
        primary_min=("n_primary_action_candidates", "min"),
        primary_max=("n_primary_action_candidates", "max"),
        richness_median=("signal_richness", "median"),
        cap_any_hits=("cap_any", "sum"))
    return j(g.reset_index().astype(object).to_dict("records"))


med = float(main.dom_bytes.median())
lo_half = main[main.dom_bytes <= med]
hi_half = main[main.dom_bytes > med]
rho_lo = stats.spearmanr(lo_half.dom_bytes, lo_half.n_primary_action_candidates)
rho_hi = stats.spearmanr(hi_half.dom_bytes, hi_half.n_primary_action_candidates)

report["step4_monotonicity"] = {
    "assertion_type": "ANALYSIS",
    "dom_bytes_quintiles": quint("dom_bytes", "q_bytes"),
    "dom_interactive_n_quintiles": quint("dom_interactive_n", "q_inter"),
    "dom_bytes_median_split": {
        "median_dom_bytes": med,
        "lower_half": {"n": int(len(lo_half)), "rho": round(float(rho_lo.statistic), 4),
                       "p": float(f"{rho_lo.pvalue:.4g}")},
        "upper_half": {"n": int(len(hi_half)), "rho": round(float(rho_hi.statistic), 4),
                       "p": float(f"{rho_hi.pvalue:.4g}")},
    },
    "bytes_per_element_vs_primary": proxy_tbl["bytes_per_element"]["n_primary_action_candidates"],
    "top_bloat": j(main.nlargest(8, "bytes_per_element")[
        ["prior_service", "dom_bytes", "dom_element_n", "bytes_per_element",
         "dom_interactive_n", "n_primary_action_candidates", "cap_any"]
    ].round(1).astype(object).to_dict("records")),
    "finding": (
        "Monotonicity FAILS for dom_bytes. Median n_primary_action_candidates by "
        "dom_bytes quintile is 24 -> 74 -> 90 -> 60 -> 40 (n=11/11/10/11/11): it "
        "rises to Q3 then FALLS, an inverted-U, so a rank correlation understates "
        "how badly the variable behaves rather than overstating it. Splitting at "
        "the median, rho=+0.36 below and rho=-0.09 above. By contrast the same "
        "table over dom_interactive_n quintiles is strictly increasing: "
        "11 -> 31 -> 50 -> 74 -> 200. Mechanism: bytes_per_element (markup weight "
        "per structural node) is NEGATIVELY associated with richness "
        "(rho=-0.275, p=0.044, n=54); the 8 heaviest-per-element documents are "
        "media/SPA shells (BAND 2330 B/elem, YouTube 2159, Instagram 1717, "
        "Netflix 1575) whose bytes are inline script/JSON payload, not interactive "
        "structure. Large dom_bytes therefore arises from two opposite regimes -- "
        "a genuinely large commerce DOM, and a script-heavy shell with almost no "
        "interactive markup -- which is why size is non-monotone in richness."),
}

# ================================================================
# STEP 5 — cap attainment: degradation or abundance?
# ================================================================
capped = main[main.cap_any == 1]
uncapped = main[main.cap_any == 0]
cap_prim = main[main.cap_primary_action_candidates == 1].copy()
cap_prim["dom_interactive_over_cap"] = cap_prim.dom_interactive_n / 200.0

report["step5_cap_semantics"] = {
    "assertion_type": "ANALYSIS",
    "cap_hit_counts_primary_grain": {
        k: int(main[k].sum()) for k in
        ["cap_primary_action_candidates", "cap_accessible_name_sources",
         "cap_target_size", "cap_contrast", "cap_any",
         "cap_motion_animated_60", "cap_body_text_4000"]},
    "n": int(len(main)),
    "capped_vs_uncapped": {
        "dom_element_n": mwu(capped.dom_element_n, uncapped.dom_element_n),
        "dom_interactive_n": mwu(capped.dom_interactive_n, uncapped.dom_interactive_n),
        "dom_bytes": mwu(capped.dom_bytes, uncapped.dom_bytes),
        "dom_a_href_n": mwu(capped.dom_a_href_n, uncapped.dom_a_href_n),
    },
    "censoring_severity_primary_cap200": {
        "rows": j(cap_prim[["prior_service", "dom_interactive_n", "dom_a_href_n",
                            "n_primary_action_candidates", "cap_count",
                            "dom_interactive_over_cap"]].round(2)
                  .astype(object).to_dict("records")),
        "min_ratio": round(float(cap_prim.dom_interactive_over_cap.min()), 2),
        "max_ratio": round(float(cap_prim.dom_interactive_over_cap.max()), 2),
        "median_ratio": round(float(cap_prim.dom_interactive_over_cap.median()), 2),
    },
    "direction_finding": (
        "The 'rich vs lossy' question is PARTLY separable. Separable half "
        "(SUPPORTED): cap-hit is driven by genuine page richness, evidenced "
        "INDEPENDENTLY of the probe by the DOM artifact -- capped observations "
        "have median dom_interactive_n=395 vs 60 uncapped (A12=0.917, "
        "p=4.2e-06, n=14 vs 40) and median dom_element_n=2800 vs 549 (A12=0.904, "
        "p=8.5e-06). Because dom.html is collected on a separate path from the "
        "probe arrays, this is not circular. Non-separable half (NOT_TESTABLE): "
        "whether the DISCARDED tail carried information that would have changed a "
        "conformance judgement cannot be decided from counts alone -- the table "
        "stores only the truncated count, never the dropped items. What IS "
        "quantifiable is a lower bound on how much was dropped: for the 7 "
        "primary-action-capped observations dom_interactive_n/200 ranges 1.72x "
        "to 6.80x (median 2.81x), so the probe reported at most 15%-58% of the "
        "DOM's interactive elements. Both readings are simultaneously true: "
        "cap-hit marks an information-RICH page AND a measurement that lost "
        "information; it is not a single scalar 'quality' direction."),
    "asymmetry_note": (
        "cap_accessible_name_sources (13/54) is the most frequently hit cap and "
        "is the ONE signal collected with no visibility filter, so it censors on "
        "raw node count rather than on user-perceivable elements; its cap-hits "
        "are the least interpretable as 'user-facing richness'."),
}

# ================================================================
# STEP 6 — candidate (b): do DOM and probe see the same page state?
# ================================================================
mismatch = main[main.title_mismatch]
genuine = mismatch[~mismatch.dom_title_mojibake]
report["step6_same_page_state"] = {
    "assertion_type": "OBSERVATION",
    "n": int(len(main)),
    "title_mismatch_n": int(len(mismatch)),
    "mojibake_explained_n": int(mismatch.dom_title_mojibake.sum()),
    "genuine_state_mismatch_n": int(len(genuine)),
    "genuine_rows": j(genuine[["prior_service", "dom_title", "probe_title",
                               "dom_body_empty", "dom_interactive_n",
                               "n_primary_action_candidates"]]
                      .astype(object).to_dict("records")),
    "probe_url_equals_final_url_n": int((main.probe_url == main.probe_final_url).sum()),
    "dom_body_empty_n": int((main.dom_body_empty == 1).sum()),
    "finding": (
        "Title agreement LOOKS like a same-page-state check but is confounded by "
        "a collector defect. dom_title != probe_title in 9/54; in 6 of those 9 the "
        "dom_title contains only Latin-1-supplement characters and zero Hangul "
        "while probe_title is well-formed Hangul -- i.e. dom.html's title is being "
        "mis-decoded (UTF-8 bytes read under a single-byte codec), not describing a "
        "different page. Only 3/54 are genuine state divergences: the two "
        "byte-identical NH observations (dom_body_empty==1, dom_interactive_n==0, "
        "probe sees 24 primary actions) and 11beonga. So candidate (b) is "
        "unusable in its obvious form until dom_title decoding is fixed, and this "
        "encoding defect is itself a finding for the collector."),
}

# ================================================================
# STEP 7 — candidate (d): capture ratio
# ================================================================
cr = main.capture_ratio
report["step7_capture_ratio"] = {
    "assertion_type": "ANALYSIS",
    "definition": "n_primary_action_candidates / dom_interactive_n",
    "defined_n": int(cr.notna().sum()), "undefined_n": int(cr.isna().sum()),
    "undefined_rows": main.loc[cr.isna(), "prior_service"].tolist(),
    "quartiles": {"min": round(float(cr.min()), 4), "q25": round(float(cr.quantile(.25)), 4),
                  "median": round(float(cr.median()), 4),
                  "q75": round(float(cr.quantile(.75)), 4),
                  "max": round(float(cr.max()), 4)},
    "n_ratio_gt_1": int((cr > 1).sum()),
    "rows_ratio_gt_1": j(main.loc[cr > 1, ["prior_service", "dom_bytes",
                                           "dom_interactive_n",
                                           "n_primary_action_candidates",
                                           "capture_ratio"]].round(3)
                         .astype(object).to_dict("records")),
    "cr_vs_dom_bytes": spearman_ci(main.dom_bytes, cr),
    "cr_vs_cap_any": spearman_ci(main.cap_any, cr),
    "cr_vs_richness": spearman_ci(main.signal_richness, cr),
    "finding": (
        "The capture-ratio family FAILS as a quality proxy, for three separate "
        "reasons, and this is the central negative result of RQ-D9. (1) It is "
        "UNDEFINED exactly where it would matter most: dom_interactive_n==0 for "
        "the 2 empty-body NH observations, which are the very cases where DOM and "
        "probe disagree. (2) Its numerator is a SELECTIVE, visibility-filtered "
        "subset (primary actions), not an attempt to enumerate all interactive "
        "elements, so ratio<1 is correct behaviour, not lost capture -- median "
        "0.571 cannot be read as '43% missed'. (3) It is mechanically deflated by "
        "the very censoring it would need to detect: the 200-cap pins the "
        "numerator while dom_interactive_n keeps growing, so the richest pages "
        "(Costco 0.147, Megacoffee 0.151) score LOWEST. Ratio>1 in 4/52 "
        "(max 11.0, Monimo) flags client-side hydration -- the probe legitimately "
        "sees elements absent from the served dom.html -- which means the ratio "
        "mixes hydration and censoring into one number with opposite signs."),
}

# ================================================================
# STEP 8 — test-retest reliability (the 4 duplicate re-runs)
# ================================================================
dupw = alt.wtg.value_counts()[lambda s: s > 1].index
pairs = alt[alt.wtg.isin(dupw)].sort_values("wtg")
rel = []
for w, g in pairs.groupby("wtg"):
    if len(g) != 2:
        continue
    a, b_ = g.iloc[0], g.iloc[1]
    rel.append({
        "service": a.prior_service, "wtg": w,
        "dom_bytes": [float(a.dom_bytes), float(b_.dom_bytes)],
        "dom_bytes_identical": bool(a.dom_bytes == b_.dom_bytes),
        "dom_element_n_identical": bool(a.dom_element_n == b_.dom_element_n),
        "signals_identical": bool(all(a[s] == b_[s] for s in SIGNALS)),
        "signals": {s: [float(a[s]), float(b_[s])] for s in SIGNALS},
    })
report["step8_test_retest"] = {
    "assertion_type": "OBSERVATION",
    "n_pairs": len(rel), "pairs": rel,
    "n_pairs_signals_identical": sum(r["signals_identical"] for r in rel),
    "n_pairs_dom_bytes_identical": sum(r["dom_bytes_identical"] for r in rel),
    "n_pairs_primary_identical": sum(
        r["signals"]["n_primary_action_candidates"][0]
        == r["signals"]["n_primary_action_candidates"][1] for r in rel),
    "finding": (
        "Across the 4 targets executed twice, the full 4-signal vector "
        "reproduces exactly in 3/4 pairs; the 4th (Netflix) differs only in "
        "n_accessible_name_sources (50 vs 51), the one signal collected with no "
        "visibility filter. n_primary_action_candidates reproduces exactly in "
        "4/4. dom_bytes, by contrast, differs between runs in 3/4 pairs "
        "(Netflix 675876 vs 677082, Hyundai Card 107417 vs 107403, Cashwalk "
        "156676 vs 156630) and is identical only for Chrome. So on these pairs "
        "size is the LESS reproducible of the two measures as well as the less "
        "valid one. n=4 pairs cannot support a reliability coefficient; treat "
        "as directional only."),
}

# ================================================================
# STEP 9 — sensitivity analyses
# ================================================================
sens = {"primary_grain_n54": {}, "alt_grain_probe_present_n58": {},
        "uncapped_only": {}, "body_nonempty_only": {}, "excl_max_dom_bytes": {}}
for v in ["dom_bytes", "dom_element_n", "dom_interactive_n", "dom_a_href_n"]:
    sens["primary_grain_n54"][v] = spearman_ci(main[v], main.n_primary_action_candidates)
    sens["alt_grain_probe_present_n58"][v] = spearman_ci(
        alt[v], alt.n_primary_action_candidates)
    u = main[main.cap_any == 0]
    sens["uncapped_only"][v] = spearman_ci(u[v], u.n_primary_action_candidates)
    e = main[main.dom_body_empty == 0]
    sens["body_nonempty_only"][v] = spearman_ci(e[v], e.n_primary_action_candidates)
    x = main[main.dom_bytes < main.dom_bytes.max()]
    sens["excl_max_dom_bytes"][v] = spearman_ci(x[v], x.n_primary_action_candidates)
report["step9_sensitivity"] = j(sens)
report["step9_finding"] = (
    "The GRAIN choice changes nothing: dom_bytes~primary rho=+0.264 (n=54) vs "
    "+0.212 (n=58 alt grain); dom_interactive_n +0.780 vs +0.785. Neither grain "
    "flips any verdict. Across cap status and body-emptiness dom_bytes stays "
    "weak with a CI including zero (+0.123 uncapped n=40; +0.236 body-nonempty "
    "n=52) while dom_interactive_n stays strong (+0.754; +0.785). Two subsets DO "
    "lift dom_bytes' CI above zero and are reported against our own verdict: "
    "excluding the single 4.78MB point (rho=+0.310, CI [+0.012,+0.560], n=53) "
    "and restricting to ITEM_DETAIL (rho=+0.520, CI [+0.111,+0.802], n=25). Both "
    "work by removing archetype heterogeneity, and in both dom_bytes remains "
    "clearly weaker than dom_interactive_n on the identical rows (0.310 vs 0.777; "
    "0.520 vs 0.708). dom_interactive_n is the more stable variable in every one "
    "of the six subsets examined.")

# ================================================================
# STEP 10 — active counterexample hunt, per candidate
# ================================================================
def row(svc, cols):
    r = main[main.prior_service == svc].iloc[0]
    return {c: (float(r[c]) if isinstance(r[c], (int, float, np.number))
                else r[c]) for c in cols}


cols_std = ["dom_bytes", "dom_element_n", "dom_interactive_n",
            "n_primary_action_candidates", "n_accessible_name_sources", "cap_any"]
report["step10_counterexamples"] = {
    "assertion_type": "OBSERVATION",
    "dom_bytes": {
        "verdict": "many counterexamples, both directions",
        "small_but_rich": [row("11번가", cols_std)],
        "large_but_poor": [row("밴드", cols_std), row("Instagram", cols_std),
                           row("YouTube", cols_std)],
        "note": ("11beonga at 16.6KB (Q1 of dom_bytes) yields 138 primary actions "
                 "and HITS the 300-cap on accessible-name sources; BAND at 4.78MB "
                 "(287x larger) yields 17 and hits nothing. Instagram 640KB->5 "
                 "and YouTube 466KB->8 are the same failure. Ordering by bytes "
                 "inverts the ordering by richness across the whole upper range."),
    },
    "dom_interactive_n": {
        "verdict": "counterexamples EXIST and are diagnosable",
        "found": [row("11번가", cols_std), row("마켓컬리", cols_std),
                  row("모니모", cols_std), row("신세계백화점", cols_std)],
        "note": ("The proxy fails on client-hydrated pages, where the served "
                 "dom.html understates the live DOM: 11beonga 23 interactive -> "
                 "138 primary actions, Marketkurly 28 -> 155, Monimo 1 -> 11, all "
                 "capture_ratio>1. It also fails in the opposite direction on "
                 "Shinsegae (341 interactive -> 23 primary, ratio 0.067), where "
                 "the visibility filter legitimately rejects most nodes. And it is "
                 "0 for both NH observations, where it is uninformative rather "
                 "than merely wrong. So dom_interactive_n is a good RANK-level "
                 "proxy, not a point predictor."),
    },
    "capture_ratio": {
        "verdict": "fails; see step7",
        "found": [row("코스트코", cols_std + ["capture_ratio"]),
                  row("모니모", cols_std + ["capture_ratio"])],
    },
    "probe_bytes": {
        "verdict": "excluded as CIRCULAR, not as failed",
        "rho": proxy_tbl["probe_bytes"]["n_primary_action_candidates"],
        "note": ("probe_bytes~primary rho=+0.954 (CI95 [+0.895,+0.979], n=54) is "
                 "the strongest number in the study and is NOT usable: probe_bytes "
                 "is the serialized size of the very arrays being counted, so it "
                 "restates the outcome. It is reported only to be ruled out."),
    },
    "dom_body_text_len": {
        "verdict": "fails",
        "rho": proxy_tbl["dom_body_text_len"]["n_primary_action_candidates"],
        "note": ("rho=+0.123, CI95 [-0.195,+0.418], n=54. Visible text volume is "
                 "unrelated to interactive richness -- a long article page and a "
                 "dense commerce grid sit at opposite ends."),
    },
    "counterexamples_to_our_own_refutation": {
        "claim_tested": "dom_bytes never recovers a CI that excludes zero",
        "status": "FALSIFIED by two subsets — reported against our own verdict",
        "found": [
            {"subset": "ITEM_DETAIL only", "n": 25, "rho": 0.5197,
             "ci95": [0.1114, 0.8016],
             "dom_interactive_n_same_subset_rho": 0.7080,
             "note": "Within one archetype dom_bytes DOES excludes zero."},
            {"subset": "excluding the single 4.78MB point", "n": 53,
             "rho": 0.3102, "ci95": [0.0116, 0.5601],
             "dom_interactive_n_same_subset_rho": 0.7772,
             "note": "Dropping BAND lifts the CI marginally above zero."},
        ],
        "interpretation": (
            "These do NOT rescue dom_bytes as a general proxy, but they do "
            "sharpen WHY it fails. Both subsets work by removing archetype "
            "heterogeneity: ITEM_DETAIL is homogeneous commerce, and the dropped "
            "point is the single most extreme SPA shell. This is exactly the "
            "two-regime mechanism proposed in step4 -- pooling script-heavy "
            "shells with genuinely large commerce DOMs is what destroys "
            "monotonicity. In BOTH subsets dom_bytes remains clearly weaker than "
            "dom_interactive_n on the same rows (0.520 vs 0.708; 0.310 vs 0.777) "
            "and both CIs are very wide. So the verdict stands for the POOLED, "
            "cross-archetype use that production would actually make, and is "
            "qualified rather than reversed within a fixed archetype."),
    },
}

archetype = main.groupby("prior_archetype").agg(
    n=("dom_bytes", "size"), dom_bytes_median=("dom_bytes", "median"),
    dom_interactive_median=("dom_interactive_n", "median"),
    primary_median=("n_primary_action_candidates", "median"),
    cap_any_hits=("cap_any", "sum")).sort_values("n", ascending=False)
item = main[main.prior_archetype == "ITEM_DETAIL"]
report["step11_archetype"] = {
    "assertion_type": "ANALYSIS",
    "table": j(archetype.reset_index().astype(object).to_dict("records")),
    "within_item_detail": {
        "n": int(len(item)),
        "dom_bytes": spearman_ci(item.dom_bytes, item.n_primary_action_candidates),
        "dom_interactive_n": spearman_ci(item.dom_interactive_n,
                                         item.n_primary_action_candidates),
    },
    "finding": ("Cap-hits concentrate in ITEM_DETAIL (11 of 14 cap_any hits, "
                "n=25) and QUERY (2 of 14, n=4); CONTENT_OPEN and "
                "COMMUNICATION_ENTRY have the largest median dom_bytes "
                "(466KB, 396KB) but the lowest median primary actions (11, 23.5). "
                "Archetype, not size, tracks where censoring happens."),
}

# ---------------------------------------------------------------- proxy scorecard
def scorecard(name, definition, computable, relation, failure, rec):
    return {"candidate": name, "definition": definition, "computable": computable,
            "observed_relation": relation, "failure_case": failure,
            "recommendation": rec}


report["proxy_scorecard"] = [
    scorecard("dom_bytes", "byte size of served dom.html",
              "yes, 54/54",
              "rho=+0.264 vs primary (CI95 [-0.024,+0.524], p=0.054); "
              "NON-MONOTONE: quintile medians 24/74/90/60/40",
              "11beonga 16.6KB->138 primary; BAND 4.78MB->17 primary",
              "UNUSABLE"),
    scorecard("bytes_per_element", "dom_bytes / dom_element_n",
              "yes, 54/54",
              "rho=-0.275 vs primary (p=0.044) -- NEGATIVE, but bootstrap CI95 "
              "[-0.523,+0.008] marginally includes zero; suggestive only",
              "not a richness measure; only separates SPA shells from real DOMs",
              "CONDITIONAL — use as a bloat FLAG, never as a richness proxy"),
    scorecard("dom_element_n", "element count in dom.html", "yes, 54/54",
              "rho=+0.707 (CI95 [+0.500,+0.847])",
              "BAND 2051 elements -> 17 primary actions",
              "CONDITIONAL — weaker than dom_interactive_n, no reason to prefer it"),
    scorecard("dom_interactive_n", "interactive-element count in dom.html",
              "yes, 54/54",
              "rho=+0.780 vs primary (CI95 [+0.602,+0.896]); "
              "+0.846 vs accessible-name sources; quintile medians strictly "
              "increasing 11/31/50/74/200; stable across all 5 sensitivity subsets",
              "client-hydrated pages (11beonga 23->138, Marketkurly 28->155, "
              "Monimo 1->11); ==0 for both NH observations",
              "RECOMMENDED — best available proxy, rank-level only"),
    scorecard("dom_a_href_n", "anchor-with-href count", "yes, 54/54",
              "rho=+0.761 vs primary, +0.837 vs accessible-name sources",
              "same hydration failures as dom_interactive_n",
              "CONDITIONAL — near-equivalent substitute, no advantage"),
    scorecard("probe_bytes", "byte size of probe payload", "yes, 54/54",
              "rho=+0.954 (CI95 [+0.895,+0.979])",
              "circular — serializes the arrays being counted",
              "UNUSABLE (circular, not failed)"),
    scorecard("ax_bytes / css_bytes", "sizes of sibling artifacts", "yes, 54/54",
              "ax rho=+0.734, css rho=+0.701 vs primary",
              "partially circular for ax_bytes (accessibility tree overlaps the "
              "signals); css_bytes tracks framework weight, not page richness",
              "NOT RECOMMENDED — ax_bytes semi-circular, css_bytes coincidental"),
    scorecard("dom_body_text_len", "visible text length", "yes, 54/54",
              "rho=+0.123 (CI95 [-0.195,+0.418])",
              "article pages long+sparse; commerce grids short+dense",
              "UNUSABLE"),
    scorecard("capture_ratio", "n_primary_action_candidates / dom_interactive_n",
              "NO — undefined for 2/54 (dom_interactive_n==0)",
              "median 0.571, range 0.067..11.0; rho vs dom_bytes -0.184 (ns); "
              "deflated by the cap it should detect",
              "Costco 0.147 and Megacoffee 0.151 score worst BECAUSE they are "
              "richest; Monimo 11.0 reflects hydration, not capture",
              "UNUSABLE as a scalar — decompose into a hydration flag "
              "(ratio>1) and a censoring flag (cap_any) instead"),
    scorecard("cap_any", "any probe array truncated", "yes, 54/54",
              "14/54 hit; capped obs have median dom_interactive_n 395 vs 60 "
              "(A12=0.917, p=4.2e-06)",
              "bidirectional meaning — marks richness AND information loss",
              "CONDITIONAL — use as a CENSORING flag, not a quality score"),
    scorecard("dom_title == probe_title", "DOM/probe same-page-state check",
              "yes but CONFOUNDED", "9/54 mismatch, 6 of which are mojibake",
              "dom_title mis-decoded (Latin-1-supplement, zero Hangul) in 6/54",
              "UNUSABLE until the dom_title encoding defect is fixed"),
    scorecard("dom_body_empty==0 AND dom_interactive_n>0",
              "minimal DOM-usability gate", "yes, 54/54",
              "excludes exactly the 2 NH observations, the only rows where DOM "
              "and probe demonstrably describe different page states",
              "does not detect partial hydration (11beonga passes the gate but "
              "its DOM still understates the live page 6-fold)",
              "RECOMMENDED as a GATE (not a score), paired with dom_interactive_n"),
]

report["verdict"] = {
    "headline": "REFUTED (size-as-proxy) + PARTIALLY_SUPPORTED (a proxy exists)",
    "components": [
        {"claim": "dom_bytes is a proxy for observation quality",
         "verdict": "REFUTED", "assertion_type": "ANALYSIS",
         "basis": "Pooled across archetypes: rho=+0.264, n=54, bootstrap CI95 "
                  "[-0.024,+0.524] includes zero, and the relation is "
                  "non-monotone (inverted-U across quintiles: 24/74/90/60/40). "
                  "Scope note: within the single archetype ITEM_DETAIL (n=25) "
                  "dom_bytes does reach rho=+0.520 with CI [+0.111,+0.802], so "
                  "the refutation applies to the POOLED, cross-archetype use "
                  "production would make -- not to every conceivable stratum. "
                  "Even there it is beaten by dom_interactive_n (+0.708)."},
        {"claim": "some measurable proxy for signal richness exists",
         "verdict": "PARTIALLY_SUPPORTED", "assertion_type": "ANALYSIS",
         "basis": "dom_interactive_n rho=+0.780 (CI95 [+0.602,+0.896], n=54), "
                  "strictly monotone across quintiles, stable in all 5 "
                  "sensitivity subsets — but with known hydration counterexamples "
                  "and undefined value on empty-body DOMs, so rank-level only."},
        {"claim": "capture ratio beats size as a proxy",
         "verdict": "NOT_SUPPORTED", "assertion_type": "ANALYSIS",
         "basis": "undefined for 2/54, confounded by cap censoring and by "
                  "hydration with opposite signs, and its numerator is a "
                  "selective subset so its scale has no quality interpretation."},
        {"claim": "cap-hit is distinguishable as richness vs information loss",
         "verdict": "PARTIALLY_SUPPORTED / NOT_TESTABLE",
         "assertion_type": "ANALYSIS",
         "basis": "Richness cause is SUPPORTED via probe-independent DOM evidence "
                  "(A12=0.917). Magnitude of information lost is NOT_TESTABLE "
                  "from this table — dropped items are not stored; only a lower "
                  "bound (1.72x-6.80x over cap) is derivable."},
    ],
}
report["limitations"] = [
    "n=54 targets. All CIs are wide; rho differences below ~0.15 are not resolvable.",
    "bytes_per_element is reported as a mechanism illustration only: its "
    "bootstrap CI95 [-0.523,+0.008] includes zero despite p=0.044, so the "
    "'markup bloat' account of WHY size fails is plausible but not established.",
    "Single fixture/run per target (except 4 duplicated), so between-run variance "
    "is essentially unmeasured; the 4 pairs are directional only.",
    "'Observation quality' is operationalised as SIGNAL RICHNESS (how much the "
    "probe recorded), which is NOT the same as measurement CORRECTNESS. Nothing "
    "here validates that recorded signals are accurate — that needs gold labels, "
    "deliberately not consulted for this RQ.",
    "The richness outcome is itself right-censored at the caps in 14/54, which "
    "attenuates every rho reported against it; true |rho| values are likely larger.",
    "The four probe signals are ~one latent dimension (off-diagonal rho >= 0.83; "
    "primary vs target_size rho=0.999), so the four columns are not four "
    "independent tests and multiplicity across them is not meaningful.",
    "dom.html is the served response while the probe runs post-hydration; the two "
    "are not guaranteed to describe the same DOM, which caps how good any "
    "DOM-derived proxy can be in principle.",
    "The refutation of dom_bytes is scoped to POOLED, cross-archetype use. Within "
    "ITEM_DETAIL (n=25) its CI excludes zero (rho=+0.520 [+0.111,+0.802]), as it "
    "does after dropping the single 4.78MB point (+0.310 [+0.012,+0.560]). Both "
    "CIs are wide and both remain below dom_interactive_n on the same rows, but a "
    "reader restricting to one archetype should not treat dom_bytes as pure noise.",
    "Observational and cross-sectional. No causal claim is made or supported.",
]
report["production_implications"] = [
    "IMPLEMENTATION: do not use dom_bytes (or any artifact byte size) as a "
    "collection health check or triage sort key — it is non-monotone in richness "
    "and would rank BAND (4.78MB, 17 actions) above 11beonga (16.6KB, 138).",
    "IMPLEMENTATION: gate on dom_body_empty==0 AND dom_interactive_n>0 before "
    "admitting an observation; this flags exactly the 2 NH rows where the DOM "
    "artifact and probe describe different page states.",
    "IMPLEMENTATION: two distinct targets (NH Smart Banking, NH Kok Bank) produced "
    "byte-identical observations. De-duplicate on the measurement vector, not "
    "only on wtg, or they will double-count in any aggregate.",
    "IMPLEMENTATION: dom_title is mis-decoded in 6/54 (Latin-1-supplement bytes, "
    "zero Hangul, while probe_title is correct). Fix charset handling at dom.html "
    "read time; until then no dom_title-based comparison is trustworthy.",
    "IMPLEMENTATION: caps are hit by 14/54 and the DOM says 1.72x-6.80x more "
    "interactive elements exist than the 200-cap admits. Persist a "
    "'truncated=true' flag plus the pre-truncation total alongside each array, "
    "so downstream consumers can distinguish 'exactly 200' from 'at least 200'.",
    "IMPLEMENTATION: cap_accessible_name_sources (300) is the most-hit cap and the "
    "only signal with no visibility filter — consider applying the same filter as "
    "the other three so its cap-hits mean the same thing.",
    "OBSERVATION: the 3 unreported truncation points (motion slice 3000, animated "
    "60, endpoint innerText 4000 chars) are silent — cap_motion_animated_60 fires "
    "in 1/54 and cap_body_text_4000 in 7/54 here, so they are live, not "
    "theoretical, and belong in the same truncation-flag treatment.",
]
report["further_research_questions"] = [
    "Does dom_interactive_n predict conformance-judgement STABILITY (not just "
    "signal count)? Requires gold labels — out of scope here by design.",
    "Re-run the capped observations with caps raised 5x: does the added tail "
    "change any conformance decision? That would convert the NOT_TESTABLE half of "
    "the cap question into a testable one.",
    "Quantify hydration lag directly by capturing dom.html at probe time as well "
    "as at fetch time; capture_ratio>1 (4/54) is currently the only proxy for it.",
    "With >=5 runs per target, estimate a proper test-retest reliability "
    "coefficient for each signal; the present 4 pairs only show exact agreement.",
    "Is bytes_per_element a usable SPA/shell classifier in its own right? The top-8 "
    "bloat list is entirely media/SPA apps, which suggests a clean threshold.",
]

# ---------------------------------------------------------------- figures
try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    FIGDIR.mkdir(parents=True, exist_ok=True)
    ROMAN = {"밴드": "BAND", "11번가": "11beonga", "코스트코": "Costco",
             "NH스마트뱅킹": "NH Smart Bank", "NH콕뱅크": "NH Kok Bank",
             "마켓컬리": "Marketkurly", "모니모": "Monimo", "메가커피": "Megacoffee"}

    # Fig 1 — dom_bytes vs primary actions, log-x, counterexamples annotated
    fig, ax = plt.subplots(figsize=(9, 5.6))
    cap0 = main[main.cap_any == 0]
    cap1 = main[main.cap_any == 1]
    ax.scatter(cap0.dom_bytes, cap0.n_primary_action_candidates, s=46,
               c="#4C78A8", alpha=.85, label="cap_any=0 (n=%d)" % len(cap0),
               edgecolor="white", linewidth=.6)
    ax.scatter(cap1.dom_bytes, cap1.n_primary_action_candidates, s=64,
               c="#E45756", alpha=.9, marker="^",
               label="cap_any=1 (n=%d)" % len(cap1), edgecolor="white", linewidth=.6)
    ax.axhline(200, ls="--", lw=1, c="#888")
    ax.text(2.2e3, 205, "primary_action cap = 200", fontsize=8, c="#666")
    for svc in ["밴드", "11번가", "NH스마트뱅킹", "코스트코"]:
        r = main[main.prior_service == svc].iloc[0]
        ax.annotate(ROMAN.get(svc, svc),
                    (r.dom_bytes, r.n_primary_action_candidates),
                    textcoords="offset points", xytext=(8, 7), fontsize=9,
                    fontweight="bold", color="#333")
    ax.set_xscale("log")
    ax.set_xlabel("dom_bytes (log scale)")
    ax.set_ylabel("n_primary_action_candidates")
    ax.set_title("RQ-D9: dom.html size does not order signal richness\n"
                 "Spearman rho=+0.264, n=54, bootstrap CI95 [-0.024, +0.524]",
                 fontsize=11)
    ax.legend(frameon=False, fontsize=9)
    ax.grid(alpha=.25, ls=":")
    fig.tight_layout()
    fig.savefig(FIGDIR / "RQ_D9_dom_bytes_vs_signal.png", dpi=150)
    plt.close(fig)

    # Fig 2 — proxy forest plot
    order = ["probe_bytes", "dom_interactive_n", "dom_a_href_n", "ax_bytes",
             "dom_element_n", "css_bytes", "dom_role_n", "dom_bytes",
             "dom_body_text_len", "bytes_per_element"]
    fig, ax = plt.subplots(figsize=(9, 5.6))
    for i, v in enumerate(order):
        s = proxy_tbl[v]["n_primary_action_candidates"]
        col = ("#999" if v in ("probe_bytes", "ax_bytes")
               else "#E45756" if not s["ci_excludes_zero"] else "#4C78A8")
        ax.plot([s["boot_ci95_lo"], s["boot_ci95_hi"]], [i, i], c=col, lw=2.4,
                solid_capstyle="round")
        ax.plot(s["spearman_rho"], i, "o", c=col, ms=8, mec="white", mew=1.2)
    ax.axvline(0, c="#333", lw=1)
    ax.set_yticks(range(len(order)))
    ax.set_yticklabels([v + ("  (circular)" if v in ("probe_bytes", "ax_bytes")
                             else "") for v in order], fontsize=9)
    ax.invert_yaxis()
    ax.set_xlabel("Spearman rho vs n_primary_action_candidates "
                  "(bootstrap 95% CI, n=54)")
    ax.set_title("RQ-D9: proxy candidates for observation signal richness\n"
                 "red = CI includes zero; grey = circular by construction",
                 fontsize=11)
    ax.grid(axis="x", alpha=.25, ls=":")
    fig.tight_layout()
    fig.savefig(FIGDIR / "RQ_D9_proxy_forest.png", dpi=150)
    plt.close(fig)

    # Fig 3 — monotonicity: quintile medians
    fig, ax = plt.subplots(figsize=(8, 5))
    qb = main.groupby("q_bytes", observed=True).n_primary_action_candidates.median()
    qi = main.groupby("q_inter", observed=True).n_primary_action_candidates.median()
    ax.plot([1, 2, 3, 4, 5], qb.values, "o-", lw=2.2, ms=9, c="#E45756",
            label="binned by dom_bytes (non-monotone)")
    ax.plot([1, 2, 3, 4, 5], qi.values, "s-", lw=2.2, ms=9, c="#4C78A8",
            label="binned by dom_interactive_n (monotone)")
    ax.set_xticks([1, 2, 3, 4, 5])
    ax.set_xlabel("quintile of the binning variable (n = 11/11/10/11/11)")
    ax.set_ylabel("median n_primary_action_candidates")
    ax.set_title("RQ-D9: size is non-monotone in richness; "
                 "interactive-element count is not", fontsize=11)
    ax.legend(frameon=False, fontsize=9)
    ax.grid(alpha=.25, ls=":")
    fig.tight_layout()
    fig.savefig(FIGDIR / "RQ_D9_monotonicity.png", dpi=150)
    plt.close(fig)

    report["figures"] = sorted(str(p) for p in FIGDIR.glob("RQ_D9_*.png"))
except Exception as exc:                                    # pragma: no cover
    report["figures"] = []
    report["figure_error"] = repr(exc)

OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
OUT_JSON.write_text(json.dumps(j(report), ensure_ascii=False, indent=2),
                    encoding="utf-8")
print("wrote", OUT_JSON)
print("figures:", report.get("figures"))
print("\nVERDICT:", report["verdict"]["headline"])
for c in report["verdict"]["components"]:
    print(f"  [{c['verdict']}] {c['claim']}")
