#!/usr/bin/env python3
"""C heartbeat measurements (D-V3-FINDING-021 / R38 / Δ46-exit2 shape): safety claims in the heartbeat are MEASURED by
this tool, never hand-written constants. Each claim carries `claim_provenance` (MEASURED | SELF_DECLARED | UNVERIFIED_*) and
its evidence. Unreadable state is reported as UNVERIFIED_*, never as the safe value."""
from __future__ import annotations
import datetime, hashlib, json, pathlib, subprocess, sys
REPO = "/home/sieg/projects-wsl/ProjectFinal"
WT = REPO + "/.agent_worktrees/claude_c_assurance_v21"
BRANCH = "claude-c/assurance-v21"
BASE = "1baa865"                       # branch base recorded in C protocol
ALLOWED_PREFIXES = ("research/landing_accessibility/assurance/",)
def _git(*a, cwd=WT):
    r = subprocess.run(["git", "-C", cwd, *a], capture_output=True, text=True, timeout=60); return r.returncode, r.stdout.strip(), r.stderr.strip()
def measure() -> dict:
    kst = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9))).isoformat(timespec="seconds")
    out = {"measured_at_kst": kst, "tool": "research/landing_accessibility/assurance/c_hb_measure.py",
           "tool_sha256": hashlib.sha256(pathlib.Path(__file__).read_bytes()).hexdigest()}
    rc, head, _ = _git("rev-parse", "HEAD"); out["head_sha"] = head if rc == 0 else None
    # production_modified — MEASURED: any committed path outside C's assurance namespace since BASE, plus dirty tree outside it
    rc1, names, err1 = _git("diff", "--name-only", f"{BASE}..HEAD"); rc2, dirty, err2 = _git("status", "--porcelain")
    if rc1 == 0 and rc2 == 0:
        outside = sorted({n for n in names.splitlines() if n and not n.startswith(ALLOWED_PREFIXES)})
        dirty_outside = sorted({l[3:] for l in dirty.splitlines() if l and not l[3:].startswith(ALLOWED_PREFIXES)})
        out["production_modified"] = bool(outside or dirty_outside)
        out["production_modified_evidence"] = {"provenance": "MEASURED", "base": BASE, "committed_paths_outside_namespace": outside, "dirty_paths_outside_namespace": dirty_outside, "allowed_prefixes": list(ALLOWED_PREFIXES)}
    else:
        out["production_modified"] = "UNVERIFIED_GIT_UNREADABLE"; out["production_modified_evidence"] = {"provenance": "UNVERIFIED", "error": err1 or err2}
    # pushed — MEASURED via ls-remote; unreadable remote is NOT 'not pushed'
    rc, rem, err = _git("ls-remote", "origin", f"refs/heads/{BRANCH}")
    if rc == 0 and rem:
        out["pushed"] = rem.split()[0] == head; out["pushed_evidence"] = {"provenance": "MEASURED", "remote_sha": rem.split()[0], "head_sha": head}
    else:
        out["pushed"] = "UNVERIFIED_REMOTE_UNREADABLE"; out["pushed_evidence"] = {"provenance": "UNVERIFIED", "error": err or "empty ls-remote"}
    # REAL_TARGET — C never opens real targets; this is a policy state, MEASURED only as 'no A REAL GO ticket addressed to C in bus'
    bus = pathlib.Path(REPO + "/.agent_bus/landing_v2/tickets"); go = []
    for f in bus.glob("*.json"):
        try: d = json.loads(f.read_text(encoding="utf-8"))
        except Exception: continue
        if d.get("from") == "A" and "C" in (d.get("to") or []) and "REAL" in json.dumps(d.get("scope", "") + d.get("headline", "") if isinstance(d.get("headline"), str) else "", ensure_ascii=False) and "GO" in json.dumps(d.get("type", ""), ensure_ascii=False):
            go.append(f.name)
    out["REAL_TARGET"] = "NO-GO" if not go else "GO_TICKET_PRESENT_SEE_EVIDENCE"
    out["REAL_TARGET_evidence"] = {"provenance": "MEASURED_BUS_SCAN", "a_real_go_tickets_to_C": go, "note": "C harness runs offline (file:// only); real-target access count is measured per lane run (non-file requests aborted = 0), not here"}
    # holdout / labels — C has no measurement instrument for these; say so instead of writing the safe constant
    out["holdout_accessed"] = "SELF_DECLARED_false"; out["labels_produced"] = "SELF_DECLARED_false"
    out["claim_provenance"] = {"production_modified": out["production_modified_evidence"]["provenance"], "pushed": out["pushed_evidence"]["provenance"], "REAL_TARGET": "MEASURED_BUS_SCAN", "holdout_accessed": "SELF_DECLARED", "labels_produced": "SELF_DECLARED"}
    return out
if __name__ == "__main__":
    try:
        m = measure()
    except Exception as e:                       # Δ46-exit2: did not run ≠ failed
        print(json.dumps({"error": repr(e), "note": "did not run — read neither as safe nor unsafe"})); sys.exit(2)
    print(json.dumps(m, ensure_ascii=False, indent=1)); sys.exit(0)
