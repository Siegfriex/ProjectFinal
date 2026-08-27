#!/usr/bin/env python3
"""MART reconciliation + statistical replay (Claude C).

Inputs
  --out-dirs  one or more runner out_dirs (raw batch results → independent per-target table; via qa_evidence.run_qa)
  --mart-dir  B mart directory (fact_task_entry.csv, fact_landing_observation.csv, fact_criterion_result.csv, dim_certification.csv)
  --older-relevant  frozen (criterion_id → older_relevance) table (CSV/JSON) — REQUIRED for FailRate; never inferred from B mart
  --plan      plan JSON (targets[] for archetype / canonical key)
Outputs QA_MART_RECONCILIATION.json + QA_STAT_REPLAY.json. Each variable: B / C / delta / match / severity.
"""
from __future__ import annotations
import argparse, json, math, pathlib, sys, datetime
import pandas as pd, numpy as np
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from assurance.qa_evidence import run_qa
from assurance import stats_replay as st

KST = datetime.timezone(datetime.timedelta(hours=9)); now = lambda: datetime.datetime.now(KST).strftime("%Y-%m-%dT%H:%M:%S+09:00")
TOL = 1e-6

def _num(v):
    try:
        if v is None or (isinstance(v, str) and not v.strip()): return None
        x = float(v); return None if math.isnan(x) else x
    except Exception: return None

def _col(df, *names):
    for n in names:
        if n in df.columns: return n
    return None

def load_older_relevant(path: str) -> dict[str, str]:
    p = pathlib.Path(path)
    if p.suffix == ".json":
        d = json.loads(p.read_text(encoding="utf-8"))
        if isinstance(d, dict) and "table" in d: d = d["table"]
        if isinstance(d, dict): return {str(k): str(v) for k, v in d.items()}
        return {str(r.get("criterion_id")): str(r.get("older_relevance")) for r in d}
    df = pd.read_csv(p, dtype=str); return dict(zip(df[_col(df, "criterion_id")], df[_col(df, "older_relevance")]))

def compare(name, b, c, sev="C1", tol=TOL):
    if b is None and c is None: return {"var": name, "B": b, "C": c, "delta": None, "match": True, "severity": None}
    if b is None or c is None: return {"var": name, "B": b, "C": c, "delta": None, "match": False, "severity": sev}
    if isinstance(b, (int, float)) and isinstance(c, (int, float)):
        d = float(c) - float(b); ok = abs(d) <= tol
        return {"var": name, "B": b, "C": c, "delta": d, "match": ok, "severity": None if ok else ("C2" if abs(d) < 1e-3 else sev)}
    ok = str(b) == str(c); return {"var": name, "B": b, "C": c, "delta": None, "match": ok, "severity": None if ok else sev}

def build_c_table(out_dirs, plan, state_dir) -> pd.DataFrame:
    rows = []
    for od in out_dirs:
        rep = run_qa(od, plan, None, "MART_INPUT", str(pathlib.Path(state_dir) / (pathlib.Path(od).name + ".seen.json")) if state_dir else None)
        for r in rep["rows"]:
            r["_out_dir"] = od; rows.append(r)
    return pd.DataFrame(rows)

def main(a):
    findings = []; add = lambda sev, code, msg, **kw: findings.append({"severity": sev, "code": code, "msg": msg, **kw})
    C = build_c_table(a.out_dirs, a.plan, a.state_dir)
    if C.empty: print("no raw rows"); return
    dup = C[C.duplicated("target_id", keep=False)]["target_id"].unique().tolist()
    if dup: add("C1", "DUP_TARGET_ACROSS_OUTDIRS", "target attempted in more than one out_dir", target_ids=dup)
    C = C.drop_duplicates("target_id", keep="first").set_index("target_id")
    mart = pathlib.Path(a.mart_dir)
    rd = lambda n: pd.read_csv(mart / f"{n}.csv", dtype=str) if (mart / f"{n}.csv").is_file() else None
    fte, flo, fcr, dcert = rd("fact_task_entry"), rd("fact_landing_observation"), rd("fact_criterion_result"), rd("dim_certification")
    per_target = []; var_rows = []
    # ---- task entry reconciliation (NED/IED/MPFED/archetype/endpoint)
    if fte is not None:
        k = _col(fte, "web_target_id"); fte = fte.set_index(k)
        cN, cI, cM = _col(fte, "MPFED", "mpfed"), _col(fte, "NED", "ned"), _col(fte, "IED", "ied"); cA = _col(fte, "interaction_archetype", "archetype"); cE = _col(fte, "endpoint_status")
        for tid, cr in C.iterrows():
            if tid not in fte.index:
                if cr.get("l1_present"): add("C1", "MART_TASK_ROW_MISSING", "raw L1 exists but no fact_task_entry row", target_id=tid)
                continue
            b = fte.loc[tid]; b = b.iloc[0] if isinstance(b, pd.DataFrame) else b
            for name, bcol, ckey in (("MPFED", cN, "mpfed"), ("NED", cI, "ned"), ("IED", cI if False else cM, "ied")):
                pass
            cmp = [compare(f"{tid}.MPFED", _num(b.get(cN)), _num(cr.get("mpfed"))), compare(f"{tid}.NED", _num(b.get(cI)), _num(cr.get("ned"))), compare(f"{tid}.IED", _num(b.get(cM)), _num(cr.get("ied"))),
                   compare(f"{tid}.archetype", b.get(cA), cr.get("archetype")), compare(f"{tid}.endpoint_status", b.get(cE), cr.get("endpoint_status"))]
            for x in cmp:
                if not x["match"]: add(x["severity"], "TASK_ENTRY_MISMATCH", f"{x['var']}: B={x['B']} C={x['C']}", target_id=tid)
            per_target.extend(cmp)
        for tid in fte.index:
            if tid not in C.index: add("C1", "MART_ROW_NOT_IN_RAW", "fact_task_entry row without raw batch evidence (sample inclusion mismatch)", target_id=tid)
    # ---- landing observation reconciliation (obstruction vars)
    if flo is not None:
        k = _col(flo, "web_target_id"); flo2 = flo.set_index(k)
        for tid, cr in C.iterrows():
            if tid not in flo2.index: continue
            b = flo2.loc[tid]; b = b.iloc[0] if isinstance(b, pd.DataFrame) else b
            for name, ckey in (("max_overlay_coverage", "max_overlay_coverage"), ("max_primary_action_occlusion", "max_primary_action_occlusion"), ("blocking_modal_count", "blocking_modal_count")):
                col = _col(flo, name)
                if col:
                    x = compare(f"{tid}.{name}", _num(b.get(col)), _num(cr.get(ckey)))
                    if not x["match"]: add(x["severity"], "LANDING_MISMATCH", f"{x['var']}: B={x['B']} C={x['C']}", target_id=tid)
                    per_target.append(x)
            oc = _col(flo, "observation_id")
            if oc and cr.get("observation_id") and str(b.get(oc)) != str(cr.get("observation_id")): add("C1", "OBS_ID_MART", "mart observation_id != raw", target_id=tid)
    # ---- FailRate from fact_criterion_result with FROZEN older-relevant set (never from mart's own tag column)
    fr = {}
    if fcr is not None:
        SUSPECT = {"2.4.7": "not in KWCAG 2.2 (WCAG Focus Visible) — registry LA-ORS-20260827 §4"}
        cid0 = _col(fcr, "criterion_id"); hits = sorted(set(fcr[cid0].astype(str)) & set(SUSPECT))
        if hits: add("C1", "SUSPECT_CRITERION_ID", f"mart contains criterion ids flagged by A as invalid/mixed WCAG: {hits}", detail={h: SUSPECT[h] for h in hits})
    if fcr is not None and a.older_relevant:
        orl = load_older_relevant(a.older_relevant); older = {c for c, t in orl.items() if t != "OTHER"}
        obs2t = {}
        if flo is not None: obs2t = dict(zip(flo[_col(flo, "observation_id")], flo[_col(flo, "web_target_id")]))
        cid, cfs, coid = _col(fcr, "criterion_id"), _col(fcr, "final_status"), _col(fcr, "observation_id")
        ctag = _col(fcr, "older_relevance")
        if ctag:
            bad = fcr[fcr[cid].map(lambda c: orl.get(str(c))) .ne(fcr[ctag]) & fcr[cid].map(lambda c: str(c) in orl)]
            if len(bad): add("C1", "OLDER_TAG_DRIFT", f"{len(bad)} criterion rows whose mart older_relevance != frozen table", sample=bad[[cid, ctag]].head(5).values.tolist())
            unknown = sorted(set(fcr[cid].astype(str)) - set(orl)); 
            if unknown: add("C1", "CRITERION_NOT_IN_FROZEN_SET", f"{len(unknown)} criterion_ids absent from frozen older-relevant table", ids=unknown[:10])
        for oid, g in fcr.groupby(coid):
            tid = obs2t.get(oid, oid)
            fr[tid] = st.fail_rate(dict(zip(g[cid].astype(str), g[cfs].astype(str))), older)
    elif fcr is not None: add("C1", "OLDER_RELEVANT_TABLE_MISSING", "cannot recompute FailRate: no frozen older-relevant table supplied (contract §2)")
    # ---- joint-valid J1..J4 and contract §1.3 reporting
    C["j4"] = [ (fr.get(t, {}).get("eligible_older_relevant", 0) > 0) if fr else None for t in C.index ]
    C["joint_valid"] = C["j1_j3_valid"] & (C["j4"].fillna(False) if fr else True)
    C.loc[C["j1_j3_valid"] & (C["j4"] == False), "exclusion_reason_c"] = "KWCAG_ALL_UNDETERMINED_OR_NONE"
    attempted = C[C["outcome"] != "PLANNED_NOT_EXECUTED"]
    summary = {"attempted_n": int(len(attempted)), "joint_valid_n": int(attempted["joint_valid"].sum()), "excluded_n": int((~attempted["joint_valid"]).sum()),
               "excluded_by_reason": attempted.loc[~attempted["joint_valid"], "exclusion_reason_c"].value_counts().to_dict(),
               "gate_reached_mpfed_null_n": int((attempted["exclusion_reason_c"] == "GATE_REACHED_MPFED_NULL").sum()),
               "gate_reached_by_archetype": attempted.loc[attempted["exclusion_reason_c"] == "GATE_REACHED_MPFED_NULL", "archetype"].value_counts().to_dict(),
               "by_archetype": {a_: {"attempted": int(len(g)), "joint_valid": int(g["joint_valid"].sum())} for a_, g in attempted.groupby(attempted["archetype"].fillna("UNKNOWN"))}}
    jv = attempted[attempted["joint_valid"]].copy()
    grade = "GREEN" if len(jv) >= 36 else "YELLOW" if len(jv) >= 28 else "RED_USABLE" if len(jv) >= 20 else "PRELIMINARY"
    summary["grade"] = grade
    # ---- statistics replay on C's own table
    med = st.archetype_medians({a_: g["mpfed"].astype(float).tolist() for a_, g in jv.groupby("archetype")})
    jv["excess_depth"] = [st.excess_depth(_num(m), a_, med) for m, a_ in zip(jv["mpfed"], jv["archetype"])]
    jv["fail_rate"] = [fr.get(t, {}).get("fail_rate") for t in jv.index]
    jv["fail_lower"] = [fr.get(t, {}).get("bound_lower_all_undet_pass") for t in jv.index]; jv["fail_upper"] = [fr.get(t, {}).get("bound_upper_all_undet_fail") for t in jv.index]
    rows = jv.reset_index().to_dict("records")
    sec = st.select_secondary_by_missingness([{"OverlayCoverage": _num(r.get("max_overlay_coverage")), "PrimaryActionOcclusion": _num(r.get("max_primary_action_occlusion")), "blocking_modal_count": _num(r.get("blocking_modal_count")), "forced_dismissal_count": _num(r.get("forced_dismissal_count"))} for r in rows])
    seckey = {"OverlayCoverage": "max_overlay_coverage", "PrimaryActionOcclusion": "max_primary_action_occlusion", "blocking_modal_count": "blocking_modal_count", "forced_dismissal_count": "forced_dismissal_count"}[sec["selected"]]
    def sp(xk, yk): 
        x = [_num(r.get(xk)) for r in rows]; y = [_num(r.get(yk)) for r in rows]
        x = [np.nan if v is None else v for v in x]; y = [np.nan if v is None else v for v in y]
        n = sum(1 for a_, b_ in zip(x, y) if not (np.isnan(a_) or np.isnan(b_)))
        return st.spearman_tie_aware(x, y, permutations=(9999 if n < 30 else 0), seed=20260827)
    prim = sp("mpfed", "fail_rate"); adj = sp("excess_depth", "fail_rate"); secr = sp("excess_depth", seckey)
    loao = st.leave_one_archetype_out([{"x": _num(r.get("mpfed")) or np.nan, "y": _num(r.get("fail_rate")) or np.nan, "archetype": r.get("archetype")} for r in rows if _num(r.get("mpfed")) is not None and _num(r.get("fail_rate")) is not None], "x", "y")
    lo, up = sp("mpfed", "fail_lower"), sp("mpfed", "fail_upper")
    direction = st.direction_stability(prim["rho"], loao, lo["rho"], up["rho"])
    kw = st.kruskal_wallis({a_: g["mpfed"].astype(float).tolist() for a_, g in jv.groupby("archetype")})
    desc = {a_: st.describe_discrete(g["mpfed"].astype(float).tolist()) for a_, g in jv.groupby("archetype")}; desc["ALL"] = st.describe_discrete(jv["mpfed"].astype(float).tolist())
    stats = {"artifact": "QA_STAT_REPLAY", "generated_by": "C", "generated_at": now(), "n_joint_valid": int(len(jv)), "grade": grade, "archetype_medians": med, "descriptive": desc,
             "primary_spearman_mpfed_failrate": prim, "structure_adjusted_spearman_excess_failrate": adj, "secondary_selection": sec, "secondary_spearman_excess_obstruction": secr,
             "leave_one_archetype_out": loao, "undet_bounds": {"lower_all_undet_pass": lo, "upper_all_undet_fail": up}, "direction_stability": direction, "kruskal_wallis": kw,
             "note": "B code not imported; tie-aware Spearman = Pearson on average ranks; permutation two-sided seed 20260827 when n<30"}
    # ---- compare with B STATISTICAL_RESULTS if present
    bstats = pathlib.Path(a.b_stats) if a.b_stats else None; cmp_stats = []
    if bstats and bstats.is_file():
        B = json.loads(bstats.read_text(encoding="utf-8"))
        def take(d, *ks):
            for k in ks:
                d = d.get(k) if isinstance(d, dict) else None
            return d
        pairs = [("primary.n", take(B, "primary_association", "n"), prim["n_pairwise_complete"]), ("primary.rho", take(B, "primary_association", "effect", "spearman_rho"), prim["rho"]),
                 ("adjusted.n", take(B, "primary_structure_adjusted_association", "n"), adj["n_pairwise_complete"]), ("adjusted.rho", take(B, "primary_structure_adjusted_association", "effect", "spearman_rho"), adj["rho"]),
                 ("kw.executed", take(B, "kruskal_wallis_mpfed_by_archetype", "executed"), kw.get("ran")), ("kw.H", take(B, "kruskal_wallis_mpfed_by_archetype", "statistic"), kw.get("H"))]
        for name, b, c in pairs:
            x = compare(name, b, c, tol=1e-3); cmp_stats.append(x)
            if not x["match"]: add(x["severity"], "STATS_MISMATCH", f"{name}: B={b} C={c}")
        if take(B, "primary_association", "n") is not None and take(B, "primary_association", "n") != prim["n_pairwise_complete"]:
            add("C1", "N_MISMATCH_STOP", "N differs — stop comparing coefficients; find sample inclusion mismatch first (§19)")
    sev = min((x["severity"] for x in findings if x["severity"]), key=lambda s: {"C0": 0, "C1": 1, "C2": 2}[s], default=None)
    recon = {"artifact": "QA_MART_RECONCILIATION", "generated_by": "C", "generated_at": now(), "inputs": {"out_dirs": a.out_dirs, "mart_dir": a.mart_dir, "older_relevant": a.older_relevant, "plan": a.plan},
             "verdict": "MART_QA_MATCH" if sev in (None, "C2") else "MART_QA_MISMATCH", "severity_max": sev, "summary_contract_1_3": summary, "per_target_variables": per_target,
             "fail_rate_c": fr, "stats_comparison": cmp_stats, "findings": findings}
    out = pathlib.Path(a.out); out.mkdir(parents=True, exist_ok=True)
    (out / "QA_MART_RECONCILIATION.json").write_text(json.dumps(recon, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    (out / "QA_STAT_REPLAY.json").write_text(json.dumps(stats, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    jv.reset_index().to_csv(out / "C_joint_valid_table.csv", index=False)
    print(json.dumps({"verdict": recon["verdict"], "severity_max": sev, **{k: summary[k] for k in ("attempted_n", "joint_valid_n", "excluded_by_reason", "grade")}, "primary_rho": prim["rho"], "primary_n": prim["n_pairwise_complete"]}, ensure_ascii=False, default=str))
    for x in findings[:25]: print(x["severity"], x["code"], x["msg"])

if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--out-dirs", nargs="+", required=True); ap.add_argument("--mart-dir", required=True); ap.add_argument("--older-relevant", default=str(pathlib.Path(__file__).resolve().parent / "out" / "older_relevant_registry.json")); ap.add_argument("--plan", required=True)
    ap.add_argument("--b-stats"); ap.add_argument("--state-dir"); ap.add_argument("--out", default="out"); main(ap.parse_args())
