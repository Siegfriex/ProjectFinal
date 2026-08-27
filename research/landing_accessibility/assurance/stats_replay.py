#!/usr/bin/env python3
"""Independent statistical verifier for Claude C.

Deliberately does NOT import any Claude B analysis code. Core statistics are implemented
from first principles (ranks, Pearson-on-ranks, permutation) and cross-checked against
scipy only as a secondary reference. Contract: ANALYSIS_CONTRACT LA-AC-20260827 §3, §4;
TIMEBOX_1630 §8, §10.
"""
from __future__ import annotations
import math
from collections import Counter
from typing import Iterable, Sequence
import numpy as np

# ----------------------------------------------------------------------------- ranks / spearman

def average_ranks(x: Sequence[float]) -> np.ndarray:
    """Tie-aware (average) ranks, 1-based. Implemented independently of scipy.rankdata."""
    a = np.asarray(x, dtype=float)
    order = np.argsort(a, kind="mergesort")
    ranks = np.empty(len(a), dtype=float)
    i = 0
    while i < len(a):
        j = i
        while j + 1 < len(a) and a[order[j + 1]] == a[order[i]]:
            j += 1
        avg = (i + j) / 2.0 + 1.0
        ranks[order[i:j + 1]] = avg
        i = j + 1
    return ranks

def pearson(x: np.ndarray, y: np.ndarray) -> float:
    x = np.asarray(x, float); y = np.asarray(y, float)
    xm, ym = x - x.mean(), y - y.mean()
    den = math.sqrt((xm * xm).sum() * (ym * ym).sum())
    return float((xm * ym).sum() / den) if den > 0 else float("nan")

def pairwise_complete(x, y):
    x = np.asarray(x, dtype=float); y = np.asarray(y, dtype=float)
    m = ~(np.isnan(x) | np.isnan(y))
    return x[m], y[m], int(m.sum())

def spearman_tie_aware(x, y, *, permutations: int = 0, seed: int = 20260827, n_headline_min: int = 10) -> dict:
    """Tie-aware Spearman rho = Pearson(avg-ranks). p-value: permutation (independent seed) when
    requested, else t-approximation. Reports N first (contract §19: compare N before p)."""
    xs, ys, n = pairwise_complete(x, y)
    out = {"n_pairwise_complete": n, "rho": None, "p_value": None, "p_method": None,
           "headline_allowed": n >= n_headline_min, "ties_x": int(n - len(set(xs.tolist()))),
           "ties_y": int(n - len(set(ys.tolist())))}
    if n < 3:
        out["p_method"] = "n<3_no_estimate"; return out
    rx, ry = average_ranks(xs), average_ranks(ys)
    rho = pearson(rx, ry)
    out["rho"] = rho
    if math.isnan(rho):
        out["p_method"] = "constant_input"; return out
    if permutations and permutations > 0:
        rng = np.random.default_rng(seed)
        cnt = 0
        for _ in range(permutations):
            r = pearson(rx, rng.permutation(ry))
            if abs(r) >= abs(rho) - 1e-12:
                cnt += 1
        out["p_value"] = (cnt + 1) / (permutations + 1)
        out["p_method"] = f"permutation(two-sided, B={permutations}, seed={seed})"
    else:
        t = rho * math.sqrt((n - 2) / max(1e-12, 1 - rho * rho)) if abs(rho) < 1 else float("inf")
        try:
            from scipy import stats as _st
            out["p_value"] = float(2 * _st.t.sf(abs(t), n - 2))
        except Exception:
            out["p_value"] = None
        out["p_method"] = "t_approx(two-sided)"
    # secondary cross-check (reference only)
    try:
        from scipy import stats as _st
        ref = _st.spearmanr(xs, ys)
        out["scipy_rho_ref"] = float(ref.statistic); out["scipy_p_ref"] = float(ref.pvalue)
        out["rho_matches_scipy"] = abs(out["scipy_rho_ref"] - rho) < 1e-9
    except Exception:
        pass
    return out

# ----------------------------------------------------------------------------- descriptive

def describe_discrete(v: Iterable[float]) -> dict:
    a = np.asarray([x for x in v if x is not None and not (isinstance(x, float) and math.isnan(x))], float)
    if len(a) == 0:
        return {"n": 0}
    q1, med, q3 = np.percentile(a, [25, 50, 75], method="linear")
    c = Counter(a.tolist()); top = max(c.values())
    modes = sorted(k for k, cnt in c.items() if cnt == top)
    xs = np.sort(a); ecdf = {str(x): float((a <= x).mean()) for x in sorted(set(xs.tolist()))}
    bins = {"0": int((a == 0).sum()), "1": int((a == 1).sum()), "2": int((a == 2).sum()),
            "3": int((a == 3).sum()), "4+": int((a >= 4).sum())}
    return {"n": int(len(a)), "median": float(med), "iqr": float(q3 - q1), "q1": float(q1), "q3": float(q3),
            "mode": modes, "min": float(a.min()), "max": float(a.max()), "ecdf": ecdf, "bins_0_1_2_3_4plus": bins}

# ----------------------------------------------------------------------------- archetype logic (contract §3)

def archetype_medians(mpfed_by_arch: dict[str, list[float]]) -> dict[str, dict]:
    """Per-archetype median + contract §3.1 min-N tier. n>=5 full; 3-4 LOW_N; <=2 NULL."""
    res = {}
    for arch, vals in mpfed_by_arch.items():
        vals = [v for v in vals if v is not None and not (isinstance(v, float) and math.isnan(v))]
        n = len(vals)
        tier = "FULL" if n >= 5 else ("LOW_N" if n >= 3 else "NULL")
        res[arch] = {"n": n, "median": (float(np.median(vals)) if n >= 3 else None), "tier": tier,
                     "excess_depth_allowed": n >= 3, "kw_eligible": n >= 5}
    return res

def excess_depth(mpfed: float | None, arch: str, med: dict[str, dict]):
    if mpfed is None or arch not in med or med[arch]["median"] is None:
        return None
    return float(mpfed - med[arch]["median"])

def kruskal_wallis(groups: dict[str, list[float]], min_n: int = 5) -> dict:
    """Contract §4.6: only groups with n>=min_n; skip omnibus if <2 groups remain."""
    kept = {k: [float(x) for x in v if x is not None] for k, v in groups.items() if len([x for x in v if x is not None]) >= min_n}
    out = {"groups_included": sorted(kept), "groups_excluded": sorted(set(groups) - set(kept)), "n_per_group": {k: len(v) for k, v in kept.items()}}
    if len(kept) < 2:
        out.update({"ran": False, "reason": "fewer_than_2_groups_with_n>=5"}); return out
    from scipy import stats as _st
    H, p = _st.kruskal(*kept.values())
    out.update({"ran": True, "H": float(H), "p_value": float(p)}); return out

# ----------------------------------------------------------------------------- fail rate (contract §2)

def fail_rate(decisions: dict[str, str], older_relevant: set[str]) -> dict:
    """decisions: criterion_id -> PASS/FAIL/UNDETERMINED/NA. Denominator = older-relevant with PASS/FAIL.
    Returns rate (None if denominator 0), undetermined_n/rate, and best/worst-case bounds (§2.1)."""
    rel = {c: d for c, d in decisions.items() if c in older_relevant}
    det = {c: d for c, d in rel.items() if d in ("PASS", "FAIL")}
    und = [c for c, d in rel.items() if d == "UNDETERMINED"]
    na = [c for c, d in rel.items() if d in ("NA", "N/A", "NOT_APPLICABLE")]
    elig = len(det); fails = sum(1 for d in det.values() if d == "FAIL")
    rate = (fails / elig) if elig else None
    lower = (fails / (elig + len(und))) if (elig + len(und)) else None                 # all UNDET -> PASS
    upper = ((fails + len(und)) / (elig + len(und))) if (elig + len(und)) else None    # all UNDET -> FAIL
    return {"eligible_older_relevant": elig, "fail_older_relevant": fails, "fail_rate": rate,
            "undetermined_n": len(und), "undetermined_rate": (len(und) / len(rel)) if rel else None,
            "na_n": len(na), "bound_lower_all_undet_pass": lower, "bound_upper_all_undet_fail": upper}

# ----------------------------------------------------------------------------- robustness

def leave_one_archetype_out(rows: list[dict], xkey: str, ykey: str, archkey: str = "archetype") -> dict:
    """rows: dicts with x,y,archetype. Returns rho per left-out archetype and sign stability."""
    base = spearman_tie_aware([r[xkey] for r in rows], [r[ykey] for r in rows])
    res = {"base_rho": base["rho"], "base_n": base["n_pairwise_complete"], "left_out": {}}
    signs = set()
    for arch in sorted({r[archkey] for r in rows}):
        sub = [r for r in rows if r[archkey] != arch]
        s = spearman_tie_aware([r[xkey] for r in sub], [r[ykey] for r in sub])
        res["left_out"][arch] = {"rho": s["rho"], "n": s["n_pairwise_complete"]}
        if s["rho"] is not None and not math.isnan(s["rho"]):
            signs.add(math.copysign(1, s["rho"]) if s["rho"] != 0 else 0)
    res["sign_stable"] = (len(signs - {0}) <= 1) and (base["rho"] is None or all(
        (v["rho"] is None) or (v["rho"] == 0) or (math.copysign(1, v["rho"]) == math.copysign(1, base["rho"])) for v in res["left_out"].values()))
    return res

if __name__ == "__main__":  # self-test vs scipy
    rng = np.random.default_rng(1)
    x = rng.integers(0, 5, 40).astype(float); y = rng.random(40) * (x + 1) / 5
    r = spearman_tie_aware(x, y, permutations=2000)
    assert r["rho_matches_scipy"], r
    from scipy.stats import rankdata
    assert np.allclose(average_ranks(x), rankdata(x, method="average"))
    print("self-test OK:", {k: r[k] for k in ("n_pairwise_complete", "rho", "p_value", "p_method", "scipy_p_ref")})
    print(describe_discrete([0, 1, 1, 2, 3, 5, 1]))
    print(fail_rate({"1.1.1": "FAIL", "1.3.3": "PASS", "2.1.1": "UNDETERMINED", "9.9.9": "FAIL"}, {"1.1.1", "1.3.3", "2.1.1"}))

# ----------------------------------------------------------------------------- A-confirmed operationalizations (2026-08-27 ~11:58)

SECONDARY_CANDIDATES_CONTRACT_ORDER = ("OverlayCoverage", "PrimaryActionOcclusion", "blocking_modal_count", "forced_dismissal_count")

def select_secondary_by_missingness(rows: list[dict], candidates=SECONDARY_CANDIDATES_CONTRACT_ORDER) -> dict:
    """§4.4: choose the obstruction variable with the LOWEST missing rate; ties broken by contract order.
    Correlation must never enter this decision. Reports missing rate for ALL candidates."""
    n = len(rows)
    miss = {}
    for c in candidates:
        m = sum(1 for r in rows if r.get(c) is None or (isinstance(r.get(c), float) and math.isnan(r.get(c))))
        miss[c] = {"missing_n": m, "missing_rate": (m / n) if n else None}
    best = min(candidates, key=lambda c: (miss[c]["missing_rate"] if miss[c]["missing_rate"] is not None else 1.0, candidates.index(c)))
    return {"selected": best, "missingness_all_candidates": miss, "rule": "min missing_rate; tie -> contract order; correlation not used"}

def _sign(v):
    if v is None or (isinstance(v, float) and math.isnan(v)) or v == 0:
        return 0
    return 1 if v > 0 else -1

def direction_stability(base_rho: float | None, loao: dict, undet_lower_rho: float | None, undet_upper_rho: float | None) -> dict:
    """§2.1 as operationalized by A: 'direction' = sign of Spearman rho. Judge on TWO axes separately —
    leave-one-archetype-out (sample composition) AND UNDETERMINED lower/upper (measurement uncertainty).
    A flip on EITHER axis -> grade C or lower; report which axis flipped."""
    b = _sign(base_rho)
    loao_flips = [a for a, v in loao.get("left_out", {}).items() if _sign(v.get("rho")) not in (0, b)]
    undet_flips = [name for name, r in (("lower_all_undet_pass", undet_lower_rho), ("upper_all_undet_fail", undet_upper_rho)) if _sign(r) not in (0, b)]
    flipped = bool(loao_flips or undet_flips)
    return {"base_sign": b, "loao_flipped_by": loao_flips, "undet_flipped_by": undet_flips,
            "direction_flipped": flipped, "grade_cap": ("C" if flipped else None),
            "axes": ["leave_one_archetype_out", "undetermined_bounds"]}
