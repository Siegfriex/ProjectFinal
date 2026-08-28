#!/usr/bin/env python3
"""C adversarial harness — duplicate launch of the SAME worker/plan into the SAME out dir (W1 exactly-once).

Reproduces the observed 2026-08-27 05:14 failure shape (two processes, same partition, ~seconds apart)
OFFLINE: uses B's FIXTURE-mode runner (synthetic local HTML, network 0). B code is the system under test,
not imported for any C computation.

Expected on pre-W1 code (positive control): evidence runs per target == 2, second process errors at batch
exclusive-create (post-hoc ledger block), DUPLICATE_SUPPRESSED == 0.
Expected after W1 (negative test): evidence runs per target == 1, DUPLICATE_SUPPRESSED >= targets, locks 1/target,
second process exits 0 without creating evidence.

Usage: dup_launch_harness.py <research_root_of_SUT> <out_dir> [delay_seconds]
"""
from __future__ import annotations
import json, os, re, subprocess, sys, time, pathlib, collections, datetime, hashlib

def main(sut_root: str, out: str, delay: float = 1.5) -> int:
    sut = pathlib.Path(sut_root).resolve(); outp = pathlib.Path(out).resolve(); outp.mkdir(parents=True, exist_ok=True)
    script = sut / "research/landing_accessibility/scripts/run_e001_batch_dryrun.py"
    if not script.is_file():  # Δ46-exit2: no SUT script = harness did not run (was: INCONCLUSIVE + exit 0)
        print(f"dup_launch_harness: SUT script missing {script} — did not run — read neither as pass nor fail (exit 2)", file=sys.stderr); return 2
    cmd = [sys.executable, str(script), "--mode", "FIXTURE", "--out", str(outp)]
    env = {**os.environ, "PYTHONUNBUFFERED": "1"}
    t0 = time.time()
    p1 = subprocess.Popen(cmd, cwd=str(sut), env=env, stdout=open(outp / "proc1.log", "w"), stderr=subprocess.STDOUT)
    time.sleep(delay)
    p2 = subprocess.Popen(cmd, cwd=str(sut), env=env, stdout=open(outp / "proc2.log", "w"), stderr=subprocess.STDOUT)
    rc1 = p1.wait(timeout=600); rc2 = p2.wait(timeout=600)
    ev = outp / "evidence"
    runs = sorted(d.name for d in ev.iterdir() if d.is_dir()) if ev.exists() else []
    per_target = collections.Counter()
    for r in runs:
        m = re.match(r"e001-(.+)-\d{4}-\d{2}-\d{2}T", r); per_target[m.group(1) if m else r] += 1
    batches = sorted(p.name for p in (outp / "batches").glob("*.json")) if (outp / "batches").exists() else []
    chain = (outp / "BATCH_CHAIN.jsonl")
    chain_len = len([l for l in chain.read_text().splitlines() if l.strip()]) if chain.exists() else 0
    logs = (outp / "proc1.log").read_text(errors="replace") + "\n" + (outp / "proc2.log").read_text(errors="replace")
    dup_suppressed = len(re.findall(r"DUPLICATE_SUPPRESSED", logs))
    ev_log = outp / "event_log.jsonl"
    if ev_log.exists(): dup_suppressed += sum(1 for l in ev_log.read_text().splitlines() if "DUPLICATE_SUPPRESSED" in l)
    bus_locks = pathlib.Path("/home/sieg/projects-wsl/ProjectFinal/.agent_bus/landing_v2/locks")
    locks_local = sorted(p.name for p in (outp / "locks").glob("*")) if (outp / "locks").exists() else []
    post_hoc_block = bool(re.search(r"BatchOverwriteError|ChainBrokenError|FileExistsError|이미 봉인", logs))
    res = {"artifact": "C_W1_DUP_LAUNCH_HARNESS", "generated_at": datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9))).isoformat(timespec="seconds"),
           "sut_root": str(sut), "sut_head": subprocess.run(["git", "rev-parse", "HEAD"], cwd=str(sut), capture_output=True, text=True).stdout.strip(),
           "delay_seconds": delay, "rc": [rc1, rc2], "elapsed_s": round(time.time() - t0, 1),
           "targets": len(per_target), "evidence_runs_total": len(runs), "runs_per_target": dict(per_target),
           "batches_files": batches, "chain_len": chain_len, "duplicate_suppressed_events": dup_suppressed,
           "post_hoc_ledger_block_seen": post_hoc_block, "locks_local": locks_local, "bus_locks_count": len(list(bus_locks.glob("*"))) if bus_locks.exists() else None,
           "verdict": None}
    if all(v == 1 for v in per_target.values()) and dup_suppressed >= len(per_target) and rc2 == 0:
        res["verdict"] = "EXACTLY_ONCE_HOLDS (launch-level suppression observed)"
    elif any(v >= 2 for v in per_target.values()):
        res["verdict"] = "DUPLICATE_LAUNCH_NOT_SUPPRESSED (evidence produced twice; " + ("post-hoc ledger block only" if post_hoc_block else "no block at all") + ")"
    else:
        res["verdict"] = "INCONCLUSIVE"
    (outp / "C_W1_DUP_LAUNCH_HARNESS.json").write_text(json.dumps(res, ensure_ascii=False, indent=2))
    print(json.dumps(res, ensure_ascii=False, indent=1)); return 0

if __name__ == "__main__":
    try:
        _rc = main(sys.argv[1], sys.argv[2], float(sys.argv[3]) if len(sys.argv) > 3 else 1.5)
    except Exception:  # Δ46-exit2 / Δ50-exit2-common: crash or missing input = did not run, never exit 1 (ran and failed)
        import traceback
        traceback.print_exc()
        print("dup_launch_harness: did not run — read neither as pass nor fail (exit 2)", file=sys.stderr)
        _rc = 2
    sys.exit(_rc)
