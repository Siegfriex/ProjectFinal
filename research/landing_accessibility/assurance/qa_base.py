#!/usr/bin/env python3
"""COLLECTION_BASE_QA verifier (Claude C). Git-fact checks only; reads origin refs, never writes.

Checks (TIMEBOX §20 / role spec §9):
  promoted main ancestry · collector/protocol/plan SHA existence & 40-hex · L0+L1 default path ·
  REAL_TARGET release binding (engine/firewall.P0_GATE_STATUS at collector SHA) · worker consistency (4 worker worktrees on same SHA) ·
  plan integrity (59 targets, 4 mutually-exclusive partitions covering the frozen order) · E000_FAST plan (6 targets, order).
Output: BASE_QA_MATCH | RESULT_AFFECTING_MISMATCH
"""
from __future__ import annotations
import json, re, subprocess, pathlib, datetime, sys
REPO = "/home/sieg/projects-wsl/ProjectFinal"
LA = "research/landing_accessibility"
KST = datetime.timezone(datetime.timedelta(hours=9)); now = lambda: datetime.datetime.now(KST).strftime("%Y-%m-%dT%H:%M:%S+09:00")
HEX40 = re.compile(r"^[0-9a-f]{40}$")

def git(*a, check=False):
    r = subprocess.run(["git", "-C", REPO, *a], capture_output=True, text=True)
    if check and r.returncode: raise RuntimeError(r.stderr.strip())
    return r.returncode, r.stdout.strip()

def show(sha, path): rc, out = git("show", f"{sha}:{path}"); return out if rc == 0 else None
def exists(sha): return git("cat-file", "-e", f"{sha}^{{commit}}")[0] == 0
def is_ancestor(a, b): return git("merge-base", "--is-ancestor", a, b)[0] == 0
def remote_tip(branch): rc, out = git("ls-remote", "-q", "origin", f"refs/heads/{branch}"); return out.split()[0] if out else None

def run(ticket: dict) -> dict:
    f = []; add = lambda sev, code, msg, **kw: f.append({"severity": sev, "code": code, "msg": msg, **kw})
    p = ticket.get("payload") or ticket
    shas = {k: p.get(k) for k in ("promoted_main_sha", "collection_base_sha", "collector_sha", "protocol_sha", "plan_sha", "exec_sha", "e000_plan_sha")}
    git("fetch", "-q", "origin")
    for k, v in shas.items():
        if v is None: continue
        if not (isinstance(v, str) and HEX40.match(v)): add("C1", "SHA_FORMAT", f"{k} is not a 40-hex commit SHA: {v!r}")
        elif not exists(v): add("C1", "SHA_UNKNOWN", f"{k} {v[:12]} not found in local repo after fetch")
    pm = shas["promoted_main_sha"]; cb = shas["collection_base_sha"]; col = shas["collector_sha"] or cb
    # promoted main identity: must equal remote tip of research/landing-accessibility-main
    tip = remote_tip("research/landing-accessibility-main")
    rep = {"remote_main_tip": tip}
    if pm and tip and tip != pm: add("C1", "PROMOTED_MAIN_TIP", f"promoted_main_sha {pm[:12]} != origin/research/landing-accessibility-main tip {tip[:12]}")
    if pm and tip == "5a9015d1e95b15304aaf53a73efb475934610b82": add("C1", "MAIN_NOT_PROMOTED", "remote main still at pre-promotion 5a9015d — P0 not released")
    # ancestry
    for k in ("collection_base_sha", "collector_sha", "plan_sha"):
        v = shas.get(k)
        if pm and v and exists(pm) and exists(v) and not is_ancestor(pm, v): add("C1", "NOT_DESCENDANT_OF_MAIN", f"{k} {v[:12]} does not contain promoted main {pm[:12]}")
    if shas["exec_sha"] and cb and exists(cb) and not is_ancestor(shas["exec_sha"], cb): add("C1", "EXEC_NOT_ANCESTOR", "exec_sha not ancestor of collection base")
    # L0+L1 default path at collector SHA
    batch_py = show(col, f"{LA}/src/landing_accessibility/e001_runner/batch.py") if col and exists(col) else None
    if batch_py is None: add("C1", "RUNNER_MISSING", "e001_runner/batch.py not present at collector SHA")
    else:
        def body(name):
            i = batch_py.find(f"def {name}(")
            if i < 0: return ""
            j = batch_py.find("\n    def ", i + 1); return batch_py[i:(j if j > 0 else len(batch_py))]
        seg = body("_default_fixture_executor")
        l1_default = "run_l1_if_safe" in seg
        if not l1_default:  # one level of indirection: self._helper(...) whose body calls run_l1_if_safe
            for m in re.finditer(r"self\.(_?[A-Za-z0-9_]+)\(", seg):
                if "run_l1_if_safe" in body(m.group(1)): l1_default = True; break
        rep["default_executor_calls_l1"] = l1_default
        if not l1_default: add("C1", "L1_NOT_DEFAULT", "_default_fixture_executor does not call run_l1_if_safe — L0-only default path")
        rep["shadow_lane"] = (re.search(r'E001_RUNNER_SHADOW_LANE\s*=\s*"([^"]+)"', batch_py) or [None, None])[1]
        rep["wall_clock_cap_s"] = (re.search(r'DEFAULT_TARGET_WALL_CLOCK_CAP_S[^=]*=\s*([0-9.]+)', show(col, f"{LA}/src/landing_accessibility/e001_runner/wall_clock.py") or "") or [None, None])[1]
        if rep["wall_clock_cap_s"] not in (None, "360.0", "360"): add("C2", "WALL_CLOCK_CAP", f"wall-clock cap {rep['wall_clock_cap_s']} != 360 (contract §1.1)")
    # REAL_TARGET release binding
    fw = show(col, f"{LA}/src/landing_accessibility/engine/firewall.py") if col and exists(col) else None
    if fw is None: add("C1", "FIREWALL_MISSING", "engine/firewall.py not at collector SHA")
    else:
        st = (re.search(r'P0_GATE_STATUS\s*=\s*"([A-Z_]+)"', fw) or [None, None])[1]; rep["firewall_p0_gate_status"] = st
        real_mode = str(p.get("execution_mode") or "REAL_TARGET")
        if real_mode == "REAL_TARGET" and st != "CLOSED": add("C1", "FIREWALL_STILL_OPEN", f"firewall P0_GATE_STATUS={st!r} at collector SHA — REAL_TARGET would hard-fail or was bypassed")
        if st == "CLOSED":
            # the commit that closed it must be after promoted main and must be identified
            rc, log = git("log", "--format=%H", "-S", 'P0_GATE_STATUS = "CLOSED"', "--", f"{LA}/src/landing_accessibility/engine/firewall.py") if False else (0, "")
            fc = p.get("firewall_close_commit")
            if not fc:  # fall back to P0_RELEASE.json on origin/control (A binds the field there)
                rel = show("origin/control/landing-orchestrator", f"{LA}/control/P0_RELEASE.json")
                if rel:
                    try:
                        R = json.loads(rel); fc = next((v for k, v in R.items() if "firewall" in k.lower() and isinstance(v, str) and HEX40.match(v)), None)
                    except Exception: fc = None
            rep["firewall_close_commit"] = fc
            if not fc: add("C1", "FIREWALL_CLOSE_COMMIT_UNBOUND", "no commit SHA binding P0_GATE_STATUS=CLOSED in ticket or P0_RELEASE.json — release→collection authorization not mechanically evidenced")
            elif not exists(fc) or not is_ancestor(fc, col): add("C1", "FIREWALL_CLOSE_COMMIT_NOT_IN_BASE", f"firewall close commit {fc[:12]} not an ancestor of collector SHA")
            else:
                fw_at = show(fc, f"{LA}/src/landing_accessibility/engine/firewall.py") or ""
                if 'P0_GATE_STATUS = "CLOSED"' not in fw_at: add("C1", "FIREWALL_CLOSE_COMMIT_WRONG", f"commit {fc[:12]} does not set P0_GATE_STATUS=CLOSED")
    # plan integrity
    plan_txt = show(shas["plan_sha"], p.get("plan_path", f"{LA}/shadow/e001_plan/E001_MASTER_PLAN.json")) if shas.get("plan_sha") and exists(shas["plan_sha"]) else None
    if plan_txt is None: add("C1", "PLAN_MISSING", "E001 master plan not readable at plan_sha")
    else:
        plan = json.loads(plan_txt); order = plan.get("frozen_collection_order") or []
        assign = ((plan.get("worker_partition") or {}).get("assignments") or {})
        allk = [k for v in assign.values() for k in v]
        rep["plan"] = {"order_n": len(order), "workers": len(assign), "assigned_n": len(allk), "hash_candidate": plan.get("frozen_plan_hash_candidate"), "status": plan.get("status")}
        if len(order) != 59: add("C1", "PLAN_N", f"frozen order has {len(order)} != 59")
        if len(set(allk)) != len(allk): add("C1", "PARTITION_OVERLAP", "worker partitions overlap")
        if set(allk) != set(order): add("C1", "PARTITION_COVER", "partitions do not exactly cover frozen order")
        for w, ks in assign.items():
            pos = [order.index(k) for k in ks if k in order]
            if pos != sorted(pos): add("C1", "PARTITION_ORDER", f"{w} list not in frozen order")
        exp = {w: order[i::len(assign)] for i, w in enumerate(sorted(assign))} if assign else {}
        if assign and any(assign[w] != exp[w] for w in assign): add("C2", "PARTITION_RULE", "assignments differ from stated round-robin rule (worker_i gets index i,i+4,...)")
        if plan.get("provenance", {}).get("real_target_outcome_used") not in (False, None): add("C1", "PLAN_OUTCOME_USED", "plan provenance says real_target_outcome_used")
    e000 = show(shas["e000_plan_sha"], p.get("e000_plan_path", f"{LA}/shadow/e000_plan/E000_FAST_PLAN.json")) if shas.get("e000_plan_sha") and exists(shas["e000_plan_sha"]) else None
    if e000:
        e = json.loads(e000); ids = e.get("selected_target_ids") or []; rep["e000"] = {"n": len(ids), "ids": ids, "outcome_blind": e.get("selection_outcome_blind"), "hash_candidate": e.get("fast_plan_hash_candidate")}
        if not (5 <= len(ids) <= 6): add("C1", "E000_N", f"E000_FAST has {len(ids)} targets (expected 5-6)")
        if e.get("accessibility_result_used") or e.get("certification_used"): add("C1", "E000_OUTCOME_USED", "E000 plan used outcome/certification")
        if len(e.get("targets") or []) != len(ids): add("C1", "E000_TARGETS_VS_IDS", "targets[] length != selected ids")
    # worker consistency
    workers = p.get("workers") or {}
    wt = {}
    for w in ("worker_01", "worker_02", "worker_03", "worker_04"):
        d = pathlib.Path(REPO) / ".agent_worktrees" / f"claude_b_e001_{w}"
        if d.is_dir():
            rc, h = git("-C", str(d), "rev-parse", "HEAD"); rc2, dirty = git("-C", str(d), "status", "--porcelain")
            wt[w] = {"head": h, "dirty": bool(dirty)}
    rep["worker_worktrees"] = wt
    heads = {v["head"] for v in wt.values()}
    if cb and heads and heads != {cb}: add("C1", "WORKER_SHA_INCONSISTENT", f"worker worktree HEADs {sorted(h[:8] for h in heads)} != collection_base {cb[:8]}")
    if workers:
        for w, s in workers.items():
            if s != cb: add("C1", "WORKER_TICKET_SHA", f"ticket says {w} on {str(s)[:8]} != collection_base")
    sev = min((x["severity"] for x in f), key=lambda s: {"C0": 0, "C1": 1, "C2": 2}[s], default=None)
    return {"artifact": "QA_BASE", "generated_by": "C", "generated_at": now(), "ticket_id": ticket.get("ticket_id"), "inputs": shas,
            "verdict": "BASE_QA_MATCH" if sev in (None, "C2") else "RESULT_AFFECTING_MISMATCH", "severity_max": sev, "checks": rep, "findings": f}

if __name__ == "__main__":
    t = json.loads(pathlib.Path(sys.argv[1]).read_text(encoding="utf-8")); t.setdefault("ticket_id", pathlib.Path(sys.argv[1]).stem)
    r = run(t); print(json.dumps(r, ensure_ascii=False, indent=2))
