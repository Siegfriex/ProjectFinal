#!/usr/bin/env python3
"""C check: the full59 runner path is byte-identical between a reference SHA and a candidate SHA.
Usage: e001_runner_unchanged_check.py <repo> <ref_sha> <cand_sha>
"""
import subprocess, sys, json
FILES = ["research/landing_accessibility/scripts/run_e001_real.py",
         "research/landing_accessibility/src/landing_accessibility/e001_runner/batch.py",
         "research/landing_accessibility/src/landing_accessibility/e001_runner/layer_firewall.py"]
def blob(repo, sha, path):
    r = subprocess.run(["git", "-C", repo, "rev-parse", f"{sha}:{path}"], capture_output=True, text=True)
    return r.stdout.strip() if r.returncode == 0 else None
def main(repo, ref, cand):
    for label, sha in (("ref", ref), ("cand", cand)):  # Δ46-exit2: an unresolvable repo/sha must not become "changed" (exit 1)
        if subprocess.run(["git", "-C", repo, "cat-file", "-e", f"{sha}^{{commit}}"], capture_output=True).returncode != 0:
            print(f"e001_runner_unchanged_check: {label} sha {sha!r} does not resolve in {repo!r} — did not run — read neither as pass nor fail (exit 2)", file=sys.stderr); return 2
    rows = [{"path": p, "ref_blob": blob(repo, ref, p), "cand_blob": blob(repo, cand, p)} for p in FILES]
    for r in rows: r["unchanged"] = r["ref_blob"] is not None and r["ref_blob"] == r["cand_blob"]
    if all(r["ref_blob"] is None for r in rows):  # Δ46-exit2: no baseline blob at ref = nothing compared, not "changed"
        print(f"e001_runner_unchanged_check: none of {len(rows)} reference blobs resolve at {ref!r} — did not run — read neither as pass nor fail (exit 2)", file=sys.stderr); return 2
    fw = blob(repo, cand, "research/landing_accessibility/src/landing_accessibility/engine/firewall.py")
    out = {"artifact": "C_E001_RUNNER_UNCHANGED_CHECK", "ref": ref, "cand": cand, "files": rows,
           "all_unchanged": all(r["unchanged"] for r in rows), "firewall_blob_cand": fw}
    print(json.dumps(out, indent=1)); return 0 if out["all_unchanged"] else 1
if __name__ == "__main__":
    try:
        _rc = main(*sys.argv[1:4])
    except Exception:  # Δ46-exit2 / Δ50-exit2-common: crash or missing input = did not run, never exit 1 (ran and failed)
        import traceback
        traceback.print_exc()
        print("e001_runner_unchanged_check: did not run — read neither as pass nor fail (exit 2)", file=sys.stderr)
        _rc = 2
    sys.exit(_rc)
