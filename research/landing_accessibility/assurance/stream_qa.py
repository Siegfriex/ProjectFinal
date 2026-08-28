#!/usr/bin/env python3
"""Streaming batch QA daemon (Claude C). Watches runner out_dirs; QA's every newly sealed batch immediately.

- Discovery: explicit --roots, plus auto-scan of .agent_worktrees/claude_b_* and artifacts/ for BATCH_CHAIN.jsonl / batches/.
- Per new (or changed) batch file: run qa_evidence.run_qa on that out_dir (worker-scoped if path hints worker_NN),
  write out/stream/<outdir-slug>/batch_<idx>.json, append QA_COLLECTION_RECONCILIATION.jsonl, update heartbeat,
  and print one event line per batch (stdout → Monitor notification). Never writes into B dirs.
"""
from __future__ import annotations
import argparse, json, pathlib, re, sys, time, hashlib, datetime, subprocess
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from assurance.qa_evidence import run_qa
from assurance import bus

REPO = pathlib.Path("/home/sieg/projects-wsl/ProjectFinal")
OUT = pathlib.Path(__file__).resolve().parent / "out" / "stream"
KST = datetime.timezone(datetime.timedelta(hours=9)); now = lambda: datetime.datetime.now(KST).strftime("%Y-%m-%dT%H:%M:%S+09:00")

def discover(extra):
    roots = set(pathlib.Path(r).resolve() for r in extra if pathlib.Path(r).is_dir())
    for base in [REPO / ".agent_worktrees", REPO / "artifacts", REPO / "research"]:
        if not base.is_dir(): continue
        for p in base.rglob("BATCH_CHAIN.jsonl"):
            if "claude_c_assurance" in str(p) or "node_modules" in str(p) or "/tests/" in str(p): continue
            roots.add(p.parent.resolve())
        for p in base.rglob("batches"):
            if p.is_dir() and any(p.glob("batch_*.json")) and "claude_c_assurance" not in str(p) and "/tests/" not in str(p): roots.add(p.parent.resolve())
    return sorted(roots)

def worker_of(path: pathlib.Path):
    m = re.search(r"worker[_-]?(\d{2})", str(path)); return f"worker_{m.group(1)}" if m else None

CROSS = {}

def main(a):
    OUT.mkdir(parents=True, exist_ok=True); seen = {}; state_dir = OUT / "_state"; state_dir.mkdir(exist_ok=True)
    plan_master = a.plan_master; plan_targets = a.plan_targets
    print(f"STREAM_QA start {now()} roots={a.roots} plan_master={plan_master} plan_targets={plan_targets}", flush=True)
    while True:
        roots = discover(a.roots)
        for root in roots:
            for bf in sorted((root / "batches").glob("batch_*.json")) if (root / "batches").is_dir() else []:
                h = hashlib.sha256(bf.read_bytes()).hexdigest()
                key = str(bf)
                if seen.get(key) == h: continue
                changed = key in seen
                slug = re.sub(r"[^A-Za-z0-9_.-]+", "_", str(root.relative_to(REPO)) if str(root).startswith(str(REPO)) else root.name)
                worker = worker_of(root)
                is_e000 = "e000" in str(root).lower()
                plan_for_root = (a.plan_e000 if is_e000 and a.plan_e000 else (plan_targets or plan_master))
                try:
                    rep = run_qa(str(root), plan_for_root, None if is_e000 else worker, f"STREAM_{slug}", str(state_dir / f"{slug}.seen.json"), extra_plan_targets=(plan_master if plan_for_root != plan_master else None))
                    # patch: master plan supplies order/partition, targets plan supplies ids
                except Exception as ex:
                    print(f"QA_ERROR {bf} {ex}", flush=True); seen[key] = h; continue
                seen[key] = h
                # C1 rule (A 12:22): REAL_TARGET evidence on disk while P0_RELEASE.firewall_gate_status_commit_sha is null
                try:
                    rel = json.loads(subprocess.run(["git", "-C", str(REPO), "show", "origin/control/landing-orchestrator:research/landing_accessibility/control/P0_RELEASE.json"], capture_output=True, text=True).stdout)
                    fw_sha = rel.get("firewall_gate_status_commit_sha")
                except Exception: fw_sha = None
                bmode = json.loads(bf.read_text(encoding="utf-8")).get("execution_mode")
                if bmode == "REAL_TARGET" and not fw_sha:
                    rep["findings"].append({"severity": "C1", "code": "COLLECTION_BEFORE_FIREWALL_BINDING", "msg": "REAL_TARGET batch sealed while P0_RELEASE.firewall_gate_status_commit_sha is null", "file": bf.name}); rep["severity_max"] = "C1" if rep["severity_max"] != "C0" else "C0"; rep["verdict"] = "MISMATCH" if rep["verdict"] == "MATCH" else rep["verdict"]
                idx = re.search(r"batch_(\d+)_", bf.name); idx = idx.group(1) if idx else bf.stem
                d = OUT / slug; d.mkdir(exist_ok=True)
                brow = next((x for x in rep["rows"] if str(x.get("batch_index")).zfill(4) == idx), None)
                batch_rows = [x for x in rep["rows"] if str(x.get("batch_index")).zfill(4) == idx]
                batch_findings = [f for f in rep["findings"] if f.get("target_id") in {x["target_id"] for x in batch_rows} or not f.get("target_id")]
                rec = {"artifact": "QA_BATCH_STREAM", "generated_by": "C", "generated_at": now(), "out_dir": str(root), "worker": worker, "batch_file": bf.name, "batch_file_sha256": h, "rerun_after_change": changed,
                       "verdict_cumulative": rep["verdict"], "severity_max_cumulative": rep["severity_max"], "batch_targets": [(x["target_id"], x["outcome"], x["exclusion_reason_c"]) for x in batch_rows],
                       "cumulative": {k: rep[k] for k in ("attempted_n", "joint_valid_j1_j3_n", "excluded_by_reason", "by_archetype", "n_batches", "batch_hash_all_ok", "outcomes", "orphan_evidence_runs", "run_accounting", "mpfed_null_reason", "mpfed_available_n", "e6b_fail_closed_fired_n", "quarantine")},
                       "append_only": rep["append_only"], "findings_batch": batch_findings, "findings_all_count": len(rep["findings"])}
                (d / f"batch_{idx}.json").write_text(json.dumps(rec, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
                (d / "QA_EVIDENCE_CUMULATIVE.json").write_text(json.dumps(rep, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
                with (OUT / "QA_COLLECTION_RECONCILIATION.jsonl").open("a", encoding="utf-8") as fh: fh.write(json.dumps({k: v for k, v in rec.items() if k != "findings_batch"}, ensure_ascii=False, default=str) + "\n")
                sev = rep["severity_max"]; c0 = [f for f in rep["findings"] if f["severity"] == "C0"]; c1 = [f for f in rep["findings"] if f["severity"] == "C1"]
                try:
                    bus.hb(phase="STREAMING_E001_QA", evidence_seen=rep["attempted_n"], last_completed=f"{slug}/{bf.name}", C0=[f"{f['code']}:{f.get('target_id','')}" for f in c0][:10], C1=[f"{f['code']}:{f.get('target_id','')}" for f in c1][:20])
                    bus._log("STREAM_BATCH_QA", out_dir=str(root), batch=bf.name, verdict=rep["verdict"], severity=sev)
                except Exception: pass
                if c0:
                    bus.emit("SYSTEMIC_HARD_STOP_CANDIDATE", {"out_dir": str(root), "batch_file": bf.name, "findings": c0[:10], "recommendation": "B: stop affected writes; A decides global stop"}, to=("A", "B"))
                if not is_e000:
                    xp = CROSS.setdefault("e001_prov", {})
                    for v in rep.get("provenance_variants") or []: xp.setdefault(v, set()).add(str(root))
                    if len(xp) > 1:
                        print(f"CROSS_WORKER_PROVENANCE_DRIFT C1 variants={len(xp)} roots={[sorted(x) for x in xp.values()]}", flush=True)
                        try: bus._log("CROSS_WORKER_PROVENANCE_DRIFT", variants=len(xp))
                        except Exception: pass
                print(f"BATCH_QA {worker or slug} {bf.name} verdict={rep['verdict']} sev={sev} attempted={rep['attempted_n']} jv13={rep['joint_valid_j1_j3_n']} C0={len(c0)} C1={len(c1)} {'RERUN_CHANGED' if changed else ''}", flush=True)
        time.sleep(a.interval)

if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--roots", nargs="*", default=[]); ap.add_argument("--plan-master", required=True); ap.add_argument("--plan-targets"); ap.add_argument("--plan-e000", help="E000 plan view (order = E000_FAST order) used for out_dirs whose path contains 'e000'"); ap.add_argument("--interval", type=int, default=15)
    try:
        main(ap.parse_args())
    except Exception:  # Δ46-exit2 / Δ50-exit2-common: daemon crash = did not run (the loop never exits normally)
        import traceback
        traceback.print_exc()
        print("stream_qa: did not run — read neither as pass nor fail (exit 2)", file=sys.stderr); sys.exit(2)
