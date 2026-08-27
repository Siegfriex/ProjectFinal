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
    rows = [{"path": p, "ref_blob": blob(repo, ref, p), "cand_blob": blob(repo, cand, p)} for p in FILES]
    for r in rows: r["unchanged"] = r["ref_blob"] is not None and r["ref_blob"] == r["cand_blob"]
    fw = blob(repo, cand, "research/landing_accessibility/src/landing_accessibility/engine/firewall.py")
    out = {"artifact": "C_E001_RUNNER_UNCHANGED_CHECK", "ref": ref, "cand": cand, "files": rows,
           "all_unchanged": all(r["unchanged"] for r in rows), "firewall_blob_cand": fw}
    print(json.dumps(out, indent=1)); return 0 if out["all_unchanged"] else 1
if __name__ == "__main__": sys.exit(main(*sys.argv[1:4]))
