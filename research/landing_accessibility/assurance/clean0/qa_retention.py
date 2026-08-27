#!/usr/bin/env python3
"""C independent audit of A's ARTIFACT_RETENTION_MANIFEST (CLEAN-0).

Independence: does NOT import any B/A code. Re-hashes every byte under each lane's
evidence/ subtree, compares to per-run manifest.jsonl and to A's rollup, and re-verifies
BATCH_CHAIN linkage and mart-56 ⊂ evidence. Units are kept separate: dirs / observations /
files / bytes / mart rows.
"""
from __future__ import annotations
import hashlib, json, os, sys, pathlib, datetime

A_MANIFEST = pathlib.Path("/home/sieg/projects-wsl/ProjectFinal/.agent_worktrees/claude_a_control/research/landing_accessibility/control/clean0/ARTIFACT_RETENTION_MANIFEST.json")
MART = pathlib.Path("/home/sieg/projects-wsl/ProjectFinal/.agent_worktrees/claude_b_analysis_current/artifacts/e001_real_marts/fact_landing_observation.json")
OUT = pathlib.Path(__file__).resolve().parent / "QA_RETENTION_MANIFEST_AUDIT.json"
KST = datetime.timezone(datetime.timedelta(hours=9))

def sha(p: pathlib.Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()

def audit_run(run_dir: pathlib.Path) -> dict:
    files = sorted(p for p in run_dir.rglob("*") if p.is_file())
    man = run_dir / "manifest.jsonl"
    entries = {}
    if man.exists():
        for line in man.read_text(encoding="utf-8").splitlines():
            if line.strip():
                e = json.loads(line); entries[e["relpath"]] = e
    actual = {}
    total_bytes = 0
    for p in files:
        rel = p.relative_to(run_dir).as_posix()
        b = p.stat().st_size; total_bytes += b
        actual[rel] = {"bytes": b, "sha256": sha(p)}
    mism, missing_on_disk, not_in_manifest = [], [], []
    for rel, e in entries.items():
        a = actual.get(rel)
        if a is None: missing_on_disk.append(rel); continue
        if a["sha256"] != e["sha256"] or a["bytes"] != e["bytes"]:
            mism.append({"relpath": rel, "manifest": e["sha256"], "actual": a["sha256"], "bytes_manifest": e["bytes"], "bytes_actual": a["bytes"]})
    for rel in actual:
        if rel not in entries and rel not in ("manifest.jsonl", "run.json"):
            not_in_manifest.append(rel)
    rollup = hashlib.sha256("\n".join(f"{r} {entries[r]['sha256']}" for r in sorted(entries)).encode()).hexdigest() if entries else None
    # alternative rollup variants (A's method text is ambiguous about trailing newline)
    rollup_nl = hashlib.sha256(("\n".join(f"{r} {entries[r]['sha256']}" for r in sorted(entries)) + "\n").encode()).hexdigest() if entries else None
    obs = sorted({e["observation_id"] for e in entries.values()})
    if not obs:
        obs = sorted({p.parts[0] for p in (q.relative_to(run_dir) for q in files) if len(p.parts) > 1 and len(p.parts[0]) == 32})
    return {"run_id": run_dir.name, "has_manifest": man.exists(), "file_count": len(files), "bytes": total_bytes,
            "manifest_entries": len(entries), "observations": obs, "sha_mismatch": mism, "manifest_entry_missing_on_disk": missing_on_disk,
            "files_not_in_manifest": not_in_manifest, "rollup_sha256": rollup, "rollup_sha256_trailing_nl": rollup_nl}

def audit_chain(lane_root: pathlib.Path) -> dict:
    chain = lane_root / "BATCH_CHAIN.jsonl"
    if not chain.exists(): return {"present": False}
    rows = [json.loads(l) for l in chain.read_text(encoding="utf-8").splitlines() if l.strip()]
    link_ok = all((rows[i]["previous_batch_hash"] == rows[i-1]["batch_hash"]) for i in range(1, len(rows))) and (rows[0]["previous_batch_hash"] is None)
    # batch file hash check: sha256 of batches/<batch_id>.json vs batch_hash (if file exists)
    bdir = lane_root / "batches"; file_hash_ok = []; 
    for r in rows:
        cands = list(bdir.glob(f"*{r['batch_id']}*.json")) if bdir.exists() else []
        file_hash_ok.append({"batch_id": r["batch_id"], "file": cands[0].name if cands else None, "sha_match": (sha(cands[0]) == r["batch_hash"]) if cands else None})
    return {"present": True, "len": len(rows), "linkage_ok": link_ok, "head": rows[-1]["batch_hash"], "batch_file_hash": file_hash_ok, "target_count_sum": sum(r.get("target_count", 0) for r in rows)}

def main() -> int:
    A = json.loads(A_MANIFEST.read_text(encoding="utf-8"))
    A_sha = sha(A_MANIFEST)
    mart_rows = json.loads(MART.read_text(encoding="utf-8"))
    mart_rows = mart_rows if isinstance(mart_rows, list) else mart_rows.get("rows")
    mart_obs = sorted({r["observation_id"] for r in mart_rows})
    out = {"artifact": "QA_RETENTION_MANIFEST_AUDIT", "producer": "C (claude-c/assurance-v21)", "assertion_type": "OBSERVATION",
           "generated_at": datetime.datetime.now(KST).isoformat(timespec="seconds"), "audited_manifest_sha256": A_sha,
           "audited_manifest_doc_id": A.get("doc_id"), "method": "full byte re-hash of every file under each lane evidence/; compare to manifest.jsonl and to A rollup; BATCH_CHAIN linkage; mart-56 containment",
           "lanes": [], "verdicts": []}
    e001_dirs = 0; e001_obs = set(); e001_nomanifest = []; all_obs = set()
    for lane in A["lanes"]:
        root = pathlib.Path(lane["root_path"]); ev = root / "evidence"
        runs = sorted(p for p in ev.iterdir() if p.is_dir()) if ev.exists() else []
        A_runs = {r["run_id"]: r for r in lane.get("runs", [])}
        lane_out = {"lane": lane["lane"], "root_path": str(root), "root_exists": root.exists(), "evidence_dirs_C": len(runs), "evidence_dirs_A": lane.get("evidence_dirs"),
                    "runs": [], "rollup_match": 0, "rollup_match_trailing_nl": 0, "rollup_mismatch": [], "runs_in_A_not_on_disk": sorted(set(A_runs) - {r.name for r in runs}),
                    "runs_on_disk_not_in_A": sorted({r.name for r in runs} - set(A_runs))}
        files_ev = 0; bytes_ev = 0; obs_lane = set(); nomani = []
        for r in runs:
            ra = audit_run(r); lane_out["runs"].append(ra)
            files_ev += ra["file_count"]; bytes_ev += ra["bytes"]; obs_lane.update(ra["observations"])
            if not ra["has_manifest"]: nomani.append(r.name)
            a = A_runs.get(r.name)
            if a and ra["rollup_sha256"]:
                if a.get("manifest_rollup_sha256") == ra["rollup_sha256"]: lane_out["rollup_match"] += 1
                elif a.get("manifest_rollup_sha256") == ra["rollup_sha256_trailing_nl"]: lane_out["rollup_match_trailing_nl"] += 1
                else: lane_out["rollup_mismatch"].append({"run_id": r.name, "A": a.get("manifest_rollup_sha256"), "C": ra["rollup_sha256"]})
            if a:
                if a.get("file_count") != ra["file_count"] or a.get("bytes") != ra["bytes"]:
                    lane_out.setdefault("count_mismatch", []).append({"run_id": r.name, "A": [a.get("file_count"), a.get("bytes")], "C": [ra["file_count"], ra["bytes"]]})
        lane_out.update({"files_evidence_subtree_C": files_ev, "bytes_evidence_subtree_C": bytes_ev, "files_A": lane.get("total_files"), "bytes_A": lane.get("total_bytes"),
                         "distinct_observations_C": len(obs_lane), "distinct_observations_A": lane.get("distinct_observations"), "dirs_without_manifest_C": nomani,
                         "dirs_without_manifest_A": lane.get("dirs_without_manifest"), "sha_mismatch_total": sum(len(x["sha_mismatch"]) for x in lane_out["runs"]),
                         "missing_on_disk_total": sum(len(x["manifest_entry_missing_on_disk"]) for x in lane_out["runs"]),
                         "not_in_manifest_total": sum(len(x["files_not_in_manifest"]) for x in lane_out["runs"]), "batch_chain": audit_chain(root)})
        if lane["experiment"] == "E001":
            e001_dirs += len(runs); e001_obs |= obs_lane; e001_nomanifest += nomani
        all_obs |= obs_lane
        out["lanes"].append(lane_out)
    pr = A["population_reconciliation"]
    out["population_reconciliation_C"] = {"E001_evidence_dirs": e001_dirs, "E001_distinct_observations": len(e001_obs), "E001_dirs_without_manifest": len(e001_nomanifest),
        "mart_rows": len(mart_rows), "mart_distinct_observations": len(mart_obs), "mart_minus_evidence": sorted(set(mart_obs) - e001_obs), "evidence_minus_mart": sorted(e001_obs - set(mart_obs))}
    out["population_reconciliation_A"] = pr
    def v(name, ok, detail=""): out["verdicts"].append({"check": name, "ok": bool(ok), "detail": detail})
    v("E001_evidence_dirs", e001_dirs == pr["E001_evidence_dirs"], f"C={e001_dirs} A={pr['E001_evidence_dirs']}")
    v("E001_distinct_observations", len(e001_obs) == pr["E001_distinct_observations"], f"C={len(e001_obs)} A={pr['E001_distinct_observations']}")
    v("E001_dirs_without_manifest", len(e001_nomanifest) == pr["E001_dirs_without_manifest"], f"C={len(e001_nomanifest)} A={pr['E001_dirs_without_manifest']}")
    v("mart56_subset_of_evidence", not (set(mart_obs) - e001_obs), f"orphans={sorted(set(mart_obs)-e001_obs)}")
    v("evidence_minus_mart", sorted(e001_obs - set(mart_obs)) == sorted(pr["evidence_minus_mart"]), f"C={sorted(e001_obs-set(mart_obs))}")
    v("byte_rehash_all_manifest_entries_match", all(l["sha_mismatch_total"] == 0 and l["missing_on_disk_total"] == 0 for l in out["lanes"]), "per-lane sha_mismatch_total / missing_on_disk_total")
    v("rollup_reproduced", all(len(l["rollup_mismatch"]) == 0 for l in out["lanes"]), {l["lane"]: [l["rollup_match"], l["rollup_match_trailing_nl"], len(l["rollup_mismatch"])] for l in out["lanes"]})
    v("batch_chain_linkage", all(l["batch_chain"].get("linkage_ok") for l in out["lanes"]), {l["lane"]: l["batch_chain"].get("len") for l in out["lanes"]})
    v("lane_file_counts_match_A", all(l["files_evidence_subtree_C"] == l["files_A"] and l["bytes_evidence_subtree_C"] == l["bytes_A"] for l in out["lanes"]), {l["lane"]: [l["files_evidence_subtree_C"], l["files_A"], l["bytes_evidence_subtree_C"], l["bytes_A"]] for l in out["lanes"]})
    out["overall"] = "MATCH" if all(x["ok"] for x in out["verdicts"]) else "MISMATCH"
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"overall": out["overall"], "verdicts": out["verdicts"], "pop_C": out["population_reconciliation_C"]}, ensure_ascii=False, indent=1))
    return 0
if __name__ == "__main__": sys.exit(main())
