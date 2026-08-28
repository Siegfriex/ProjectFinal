#!/usr/bin/env python3
"""probe_v2_measure_c.py — T-A-V3-PROBE-V2-001: four hand-countable numbers from artifacts/v3_probe_v2/ ONLY (never the sealed census).
1 AX alive?  every *ax*.json under the probe root: bytes and node count (JSON walk: dict/list nodes with a role/name/children key or any dict);
             alive = bytes > 60 AND nodes > 1; files that are the 60 B `_error` stub are counted as STUB.
2 candidate_count > 0 targets / 21  (from any json/jsonl record carrying target_id + candidate_count; max over records per target)
3 ENDPOINT_REACHED targets (attempt_status or terminal_reason == ENDPOINT_REACHED)
4 selection order: attempted targets vs PROBE_TARGET_SET ascending; skipped / out-of-set listed; order by first timestamp seen.
Exit 0 ran · 3 NO_INPUT (no E output yet) · 2 crash. Prints JSON; writes gate3/probe/out/PROBE_V2_MEASURE_C.json."""
import glob, json, os, re, sys, pathlib, datetime, hashlib
P = pathlib.Path("/home/sieg/projects-wsl/ProjectFinal/artifacts/v3_probe_v2"); OUT = pathlib.Path(__file__).resolve().parent / "out" / "PROBE_V2_MEASURE_C.json"
KST = datetime.timezone(datetime.timedelta(hours=9))


def nodes(o):
    if isinstance(o, dict): return 1 + sum(nodes(v) for v in o.values() if isinstance(v, (dict, list)))
    if isinstance(o, list): return sum(nodes(v) for v in o if isinstance(v, (dict, list)))
    return 0


def main():
    if not P.exists(): print("NO_INPUT: probe root missing (exit 3)"); return 3
    ts = json.load(open(P / "PROBE_TARGET_SET.json")); tl = ts if isinstance(ts, list) else ts.get("targets") or ts.get("target_ids") or ts
    tset = sorted(x["target_id"] if isinstance(x, dict) else x for x in tl)
    ax = []
    for f in glob.glob(str(P / "**" / "*ax*.json"), recursive=True):
        b = open(f, "rb").read(); n = None; err = None; declared = None
        try:
            o = json.loads(b.decode("utf-8")); err = o.get("_error") if isinstance(o, dict) else None
            # E writes {"aria_snapshot": "<yaml-like tree>", "node_count": N}: C counts tree lines itself ('- ' bullets), never trusts node_count alone
            if isinstance(o, dict) and isinstance(o.get("aria_snapshot"), str):
                n = sum(1 for ln in o["aria_snapshot"].splitlines() if re.match(r"^\s*- ", ln)); declared = o.get("node_count")
            else: n = nodes(o); declared = None
        except Exception as e: err = f"UNPARSABLE:{type(e).__name__}"
        m = re.search(r"/(F\d-\d\d)/", f); ax.append({"file": os.path.relpath(f, P), "target": m.group(1) if m else None, "bytes": len(b), "nodes": n, "node_count_declared": declared, "error": err, "alive": (len(b) > 60 and (n or 0) > 1 and not err)})
    recs = []
    for f in glob.glob(str(P / "**" / "*.json*"), recursive=True):
        if "ax" in os.path.basename(f) or f.endswith("PROBE_TARGET_SET.json"): continue
        try:
            if f.endswith(".jsonl"): objs = [json.loads(l) for l in open(f, encoding="utf-8") if l.strip()]
            else:
                o = json.load(open(f, encoding="utf-8")); objs = o if isinstance(o, list) else [o]
        except Exception: continue
        for o in objs:
            if isinstance(o, dict) and o.get("target_id"): recs.append({**o, "_file": os.path.relpath(f, P)})
    per = {}
    for r in recs:
        t = r["target_id"]; d = per.setdefault(t, {"candidate_count_max": None, "endpoint": False, "first_ts": None, "terminal": set(), "files": set()})
        cc = r.get("candidate_count")
        if isinstance(cc, (int, float)): d["candidate_count_max"] = max(cc, d["candidate_count_max"] or 0)
        for br in (r.get("attempted_branches") or []):   # E_ROUTE_CANDIDATE: attempted_branches[].candidate_count (TBX-013 R74 criterion)
            if isinstance(br, dict) and isinstance(br.get("candidate_count"), (int, float)): d["candidate_count_max"] = max(br["candidate_count"], d["candidate_count_max"] or 0)
        if r.get("route_diagnosis"): d["terminal"].add("route_diagnosis=" + str(r["route_diagnosis"]))
        if r.get("scout_status"): d["terminal"].add("scout_status=" + str(r["scout_status"]))
        if "ENDPOINT_REACHED" in (r.get("attempt_status"), r.get("terminal_reason"), r.get("scout_status")): d["endpoint"] = True   # E_ROUTE_CANDIDATE carries scout_status
        if r.get("terminal_reason"): d["terminal"].add(str(r["terminal_reason"]))
        for k in ("captured_at_kst", "dispatched_at_kst", "started_at_kst", "captured_at", "ts"):
            if r.get(k): d["first_ts"] = min(d["first_ts"] or str(r[k]), str(r[k]))
        d["files"].add(r["_file"])
    attempted = sorted(per)
    ax_by_t = {}
    for a in ax: ax_by_t.setdefault(a["target"], []).append(a)
    if not ax and not recs: print("NO_INPUT: no E output under probe root yet (exit 3)"); return 3
    order = sorted(attempted, key=lambda t: per[t]["first_ts"] or "")
    res = {"measured_at_kst": datetime.datetime.now(KST).isoformat(timespec="seconds"), "root": str(P), "target_set_n": len(tset),
           "1_ax": {"files": len(ax), "alive": sum(1 for a in ax if a["alive"]), "stub_60B_or_error": sum(1 for a in ax if a["bytes"] <= 60 or a["error"]), "targets_with_alive_ax": sorted({a["target"] for a in ax if a["alive"] and a["target"]}),
                    "bytes_min_max": [min(a["bytes"] for a in ax), max(a["bytes"] for a in ax)] if ax else None, "nodes_min_max": [min((a["nodes"] or 0) for a in ax), max((a["nodes"] or 0) for a in ax)] if ax else None, "rule": "alive = bytes>60 AND nodes>1 AND no _error"},
           "2_candidate_gt0": {"n": sum(1 for t in tset if (per.get(t, {}).get("candidate_count_max") or 0) > 0), "of": 21, "targets": sorted(t for t in tset if (per.get(t, {}).get("candidate_count_max") or 0) > 0), "targets_with_no_candidate_count_field": sorted(t for t in attempted if per[t]["candidate_count_max"] is None)},
           "3_endpoint_reached": {"n": sum(1 for t in tset if per.get(t, {}).get("endpoint")), "targets": sorted(t for t in tset if per.get(t, {}).get("endpoint"))},
           "4_selection": {"attempted_n": len(attempted), "attempted_in_set": len([t for t in attempted if t in tset]), "out_of_set": sorted(t for t in attempted if t not in tset), "not_yet_attempted": sorted(t for t in tset if t not in per),
                           "order_seen": order, "ascending_order_respected": order == sorted(order), "skips_inside_prefix": [t for t in tset if t < (max(attempted) if attempted else "") and t not in per]},
           "terminal_distribution": {t: sorted(per[t]["terminal"]) for t in attempted},
           "go_no_go_rule": "GO ≥8/21 · PARTIAL 3–7 · NO-GO 0–2 (A pre-fixed); C reports the number, A decides"}
    k = res["2_candidate_gt0"]["n"]; res["go_no_go_by_rule"] = "GO" if k >= 8 else "PARTIAL_GO" if k >= 3 else "NO-GO"
    OUT.parent.mkdir(parents=True, exist_ok=True); OUT.write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps({k: v for k, v in res.items() if k != "terminal_distribution"}, ensure_ascii=False)); return 0


if __name__ == "__main__":
    try: sys.exit(main())
    except SystemExit: raise
    except Exception:
        import traceback; traceback.print_exc(); print("did not run (exit 2)", file=sys.stderr); sys.exit(2)
