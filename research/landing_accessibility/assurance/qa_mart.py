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
    # cross-out_dir provenance drift (E000 vs E001 workers): expected & approved by A when --expected-drift is set
    provs = {}
    for _, r in C.iterrows():
        pv = r.get("run_provenance");
        if isinstance(pv, dict): provs.setdefault(json.dumps({k: pv.get(k) for k in ("base_sha", "shadow_lane", "protocol_version", "execution_scope")}, sort_keys=True), set()).add(r["_out_dir"])
    if len(provs) > 1:
        add("C2" if a.expected_drift else "C1", "PROVENANCE_DRIFT_ACROSS_OUTDIRS", ("A-approved expected drift (E000 batch-0 reuse void): " if a.expected_drift else "") + f"{len(provs)} provenance variants across out_dirs", variants={k: sorted(v) for k, v in provs.items()})
    C = C.drop_duplicates("target_id", keep="first").set_index("target_id")
    mart = pathlib.Path(a.mart_dir)
    rd = lambda n: pd.read_csv(mart / f"{n}.csv", dtype=str) if (mart / f"{n}.csv").is_file() else None
    fte, flo, fcr, dcert = rd("fact_task_entry"), rd("fact_landing_observation"), rd("fact_criterion_result"), rd("dim_certification")
    per_target = []; var_rows = []
    # ---- MART_ACCEPTANCE §1 (A 12:55): row counts / keys / target coverage / L0-L1 coverage / execution_mode / input SHA
    frame = json.loads(pathlib.Path(a.plan).read_text(encoding="utf-8")); plan_ids = {t["target_id"] for t in frame.get("targets") or []}
    disk_runs_total = sum(len(list((pathlib.Path(od) / "evidence").iterdir())) for od in a.out_dirs if (pathlib.Path(od) / "evidence").is_dir())
    if flo is not None:
        oc = _col(flo, "observation_id"); n_rows = len(flo); n_null = int(flo[oc].isna().sum()) if oc else None; n_dup = int(flo[oc].duplicated().sum()) if oc else None
        acc1 = {"mart_rows": n_rows, "batch_referenced_runs": int(C["evidence_run_id"].notna().sum()), "disk_runs_total": disk_runs_total, "obs_id_null": n_null, "obs_id_dup": n_dup}
        if n_null or n_dup: add("C1", "MART_KEYS", f"observation_id null={n_null} dup={n_dup}")
        if n_rows != acc1["batch_referenced_runs"]: add("C1", "MART_ROW_COUNT", f"mart rows {n_rows} != batch-referenced runs {acc1['batch_referenced_runs']} (disk runs {disk_runs_total}; retry-superseded/guard runs explain disk>referenced only)")
        tc = _col(flo, "web_target_id"); outside = sorted(set(flo[tc].astype(str)) - plan_ids) if tc else []
        if outside: add("C1", "MART_TARGET_OUTSIDE_PLAN", f"{len(outside)} mart targets not in frozen plan", ids=outside[:10])
        em = _col(flo, "execution_mode")
        if em and not set(flo[em].dropna().astype(str)) <= {"FIXTURE", "SHADOW_DRY_RUN", "REAL_TARGET"}: add("C1", "MART_EXECUTION_MODE_ENUM", f"execution_mode outside closed set: {sorted(set(flo[em].astype(str)))}")
        for col in ("dom_path", "ax_path", "screenshot_path", "probe_path"):
            c_ = _col(flo, col)
            if c_ is None: add("C2", "MART_L0_COVERAGE_COL_MISSING", f"fact_landing_observation lacks {col}")
            elif flo[c_].isna().any(): add("C1", "MART_L0_COVERAGE_NULL", f"{int(flo[c_].isna().sum())} rows with null {col}")
    else: acc1 = {"mart_rows": None}
    manifest_path = pathlib.Path(a.mart_dir) / "FROZEN_MART_MANIFEST.json"
    if not manifest_path.is_file(): manifest_path = pathlib.Path(a.mart_dir).parent / "FROZEN_MART_MANIFEST.json"
    prov_check = {}
    if manifest_path.is_file():
        M = json.loads(manifest_path.read_text(encoding="utf-8")); mp = M.get("provenance") or {}
        decl = {"collector_sha": a.collector_sha, "protocol_sha": a.protocol_sha, "plan_hash": a.plan_hash, "older_relevance_registry_sha256": "da4b5208c91dd7634fc9e50d7a883674ad7666fc3828f359e4f428b3be863f8e"}
        for k, v in decl.items():
            got = mp.get(k) or M.get(k) or next((mp[x] for x in mp if k.split("_")[0] in x and isinstance(mp[x], str)), None)
            prov_check[k] = {"declared": v, "mart": got, "match": (v is None) or (got is not None and str(got).startswith(str(v)[:12]))}
            if v and not prov_check[k]["match"]: add("C1", "MART_INPUT_SHA", f"mart provenance {k}={got} != declared {v}")
        if M.get("frozen") is False: add("C2", "MART_NOT_FROZEN_FLAG", "FROZEN_MART_MANIFEST.frozen=false")
    else: add("C1", "FROZEN_MART_MANIFEST_MISSING", "FROZEN_MART_MANIFEST.json not found (MART_ACCEPTANCE §1-7/8 unverifiable)")
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
    # COLLECTION_WINDOW_RULE §3 (A 12:48): heterogeneity checks — fire only if extension branch; always computed, flagged by --e001-start
    import datetime as _dt
    def _kst(ts):
        try: return _dt.datetime.fromisoformat(str(ts).replace("Z", "+00:00")).astimezone(_dt.timezone(_dt.timedelta(hours=9)))
        except Exception: return None
    und = {t: fr.get(t, {}).get("undetermined_rate") for t in jv.index}
    buckets = {}
    for t, r in jv.iterrows():
        k = _kst(r.get("sealed_at")); b = (k.strftime("%H:%M")[:4] + ("0" if k.minute < 30 else "3") + "0") if k else "UNKNOWN"
        buckets.setdefault(b, []).append(und.get(t))
    und_by_bucket = {b: {"n": len(v), "undetermined_rate_mean": (float(np.nanmean([x for x in v if x is not None])) if any(x is not None for x in v) else None)} for b, v in sorted(buckets.items())}
    confound = st.spearman_tie_aware([np.nan if und.get(t) is None else und[t] for t in jv.index], [np.nan if fr.get(t, {}).get("fail_rate") is None else fr[t]["fail_rate"] for t in jv.index])
    ext = bool(a.e001_start and a.e001_start >= "13:15")
    confound_flag = confound["rho"] is not None and ((confound["p_value"] is not None and confound["p_value"] < 0.05) or abs(confound["rho"]) >= 0.3)
    arch_by_bucket = {b: jv.loc[[t for t in jv.index if ((_kst(jv.loc[t, "sealed_at"]).strftime("%H:%M")[:4] + ("0" if _kst(jv.loc[t, "sealed_at"]).minute < 30 else "3") + "0") if _kst(jv.loc[t, "sealed_at"]) else "UNKNOWN") == b], "archetype"].value_counts().to_dict() for b in buckets}
    window = {"e001_start_kst": a.e001_start, "extension_branch": ext, "undetermined_rate_by_sealed_at_bucket": und_by_bucket, "archetype_by_bucket": arch_by_bucket,
              "confound_spearman_undetermined_rate_x_fail_rate": confound, "confound_flag": confound_flag,
              "grade_demotion_required": bool(ext and confound_flag), "rule": ".agent_bus/landing_v2/COLLECTION_WINDOW_RULE.md §3 items 1-4"}
    if ext and confound_flag: add("C1", "WINDOW_CONFOUND_GRADE_DEMOTION", f"extension branch + undetermined_rate correlated with fail_rate (rho={confound['rho']:.3f}, p={confound['p_value']}) — primary claim grade must drop one level")
    kw = st.kruskal_wallis({a_: g["mpfed"].astype(float).tolist() for a_, g in jv.groupby("archetype")})
    desc = {a_: st.describe_discrete(g["mpfed"].astype(float).tolist()) for a_, g in jv.groupby("archetype")}; desc["ALL"] = st.describe_discrete(jv["mpfed"].astype(float).tolist())
    stats = {"artifact": "QA_STAT_REPLAY", "generated_by": "C", "generated_at": now(), "n_joint_valid": int(len(jv)), "grade": grade, "archetype_medians": med, "descriptive": desc,
             "primary_spearman_mpfed_failrate": prim, "structure_adjusted_spearman_excess_failrate": adj, "secondary_selection": sec, "secondary_spearman_excess_obstruction": secr,
             "leave_one_archetype_out": loao, "collection_window_heterogeneity": window, "undet_bounds": {"lower_all_undet_pass": lo, "upper_all_undet_fail": up}, "direction_stability": direction, "kruskal_wallis": kw,
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
             "verdict": "MART_QA_MATCH" if sev in (None, "C2") else "MART_QA_MISMATCH", "severity_max": sev, "summary_contract_1_3": summary, "mart_acceptance_s1": {"counts_keys": acc1, "input_sha": prov_check}, "per_target_variables": per_target,
             "fail_rate_c": fr, "stats_comparison": cmp_stats, "findings": findings}
    out = pathlib.Path(a.out); out.mkdir(parents=True, exist_ok=True)
    (out / "QA_MART_RECONCILIATION.json").write_text(json.dumps(recon, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    (out / "QA_STAT_REPLAY.json").write_text(json.dumps(stats, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    jv.reset_index().to_csv(out / "C_joint_valid_table.csv", index=False)
    print(json.dumps({"verdict": recon["verdict"], "severity_max": sev, **{k: summary[k] for k in ("attempted_n", "joint_valid_n", "excluded_by_reason", "grade")}, "primary_rho": prim["rho"], "primary_n": prim["n_pairwise_complete"]}, ensure_ascii=False, default=str))
    for x in findings[:25]: print(x["severity"], x["code"], x["msg"])

if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--out-dirs", nargs="+", required=True); ap.add_argument("--mart-dir", required=True); ap.add_argument("--older-relevant", default=str(pathlib.Path(__file__).resolve().parent / "out" / "older_relevant_registry.json")); ap.add_argument("--plan", required=True)
    ap.add_argument("--b-stats"); ap.add_argument("--collector-sha"); ap.add_argument("--protocol-sha"); ap.add_argument("--plan-hash", default="b48be3cb5e2cb992c0b9ee44306a4f3bd3cee8fbd601de5f14ebb82f75a9e2bc"); ap.add_argument("--expected-drift", action="store_true", help="A approved collector change between E000 and E001 (E000 reuse void)"); ap.add_argument("--e001-start", help="KST HH:MM of actual E001 start (extension branch if >= 13:15)"); ap.add_argument("--state-dir"); ap.add_argument("--out", default="out"); main(ap.parse_args())
