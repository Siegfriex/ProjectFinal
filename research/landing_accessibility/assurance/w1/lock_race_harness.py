#!/usr/bin/env python3
"""C adversarial harness — cross-process race on B's TargetLock (SUT), N processes x K keys, same lock_dir.
Expected (D-R0-46): per key exactly 1 proceed=True; all others proceed=False with DUPLICATE_SUPPRESSED reason;
retry allowed only after mark_failed_retryable and attempts<max; lock files never deleted.
Usage: lock_race_harness.py <sut_src_dir> <lock_dir> [n_procs=3] [n_keys=3]
"""
import sys, json, subprocess, pathlib, collections, datetime
WORKER = r'''
import sys, json, time
sys.path.insert(0, sys.argv[1])
from landing_accessibility.e001_runner.batch import TargetLock, IdempotencyKey
lock = TargetLock(sys.argv[2]); out = []
t0 = float(sys.argv[4]); time.sleep(max(0, t0 - time.time()))   # barrier: all procs start together
for i in range(int(sys.argv[3])):
    k = IdempotencyKey(ticket_id="T-C-RACE", run_id="R1", target_id=f"wt-race-{i}", collector_sha="deadbeef", protocol_sha="cafebabe")
    d = lock.acquire(k, max_attempts=2)
    out.append({"target": k.target_id, "proceed": d.proceed, "reason": d.reason, "prior_state": d.prior_state, "attempt_id": d.attempt_id})
print(json.dumps(out))
'''
def main(src, lock_dir, n_procs=3, n_keys=3):
    import time
    if not (pathlib.Path(src) / "landing_accessibility" / "e001_runner" / "batch.py").is_file():  # Δ46-exit2: SUT absent = did not run
        print(f"lock_race_harness: SUT batch.py not under {src!r} — did not run — read neither as pass nor fail (exit 2)", file=sys.stderr); return 2
    lock_dir = pathlib.Path(lock_dir); lock_dir.mkdir(parents=True, exist_ok=True)
    w = pathlib.Path(lock_dir) / "_worker.py"; w.write_text(WORKER)
    t0 = time.time() + 1.5
    procs = [subprocess.Popen([sys.executable, str(w), src, str(lock_dir), str(n_keys), str(t0)], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True) for _ in range(n_procs)]
    res = []; errs = []
    for p in procs:
        o, e = p.communicate(timeout=120)
        if p.returncode != 0: errs.append(e[-800:]); continue
        res.append(json.loads(o))
    if not res:  # Δ46-exit2: every worker died before deciding — nothing was measured
        print("lock_race_harness: no worker produced a decision — did not run — read neither as pass nor fail (exit 2)\n" + "\n".join(errs), file=sys.stderr); return 2
    per = collections.defaultdict(list)
    for r in res:
        for d in r: per[d["target"]].append(d)
    verdict = {"artifact": "C_W1_LOCK_RACE_HARNESS", "generated_at": datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9))).isoformat(timespec="seconds"),
               "sut_src": src, "n_procs": n_procs, "n_keys": n_keys, "errors": errs, "per_key": {}, "lock_files": sorted(p.name for p in lock_dir.glob("*.lock.json"))}
    ok = not errs
    for k, ds in per.items():
        proceeds = sum(1 for d in ds if d["proceed"]); supp = sum(1 for d in ds if not d["proceed"] and d["reason"] and "DUPLICATE_SUPPRESSED" in d["reason"])
        verdict["per_key"][k] = {"proceed": proceeds, "suppressed": supp, "decisions": ds}
        ok = ok and proceeds == 1 and supp == len(ds) - 1
    # second wave: retry after mark_failed_retryable should proceed once; after DONE must be suppressed
    verdict["exactly_once_holds"] = ok
    print(json.dumps(verdict, ensure_ascii=False, indent=1)); return 0 if ok else 1
if __name__ == "__main__":
    try:
        _rc = main(sys.argv[1], sys.argv[2], int(sys.argv[3]) if len(sys.argv) > 3 else 3, int(sys.argv[4]) if len(sys.argv) > 4 else 3)
    except Exception:  # Δ46-exit2 / Δ50-exit2-common: crash or missing input = did not run, never exit 1 (ran and failed)
        import traceback
        traceback.print_exc()
        print("lock_race_harness: did not run — read neither as pass nor fail (exit 2)", file=sys.stderr)
        _rc = 2
    sys.exit(_rc)
