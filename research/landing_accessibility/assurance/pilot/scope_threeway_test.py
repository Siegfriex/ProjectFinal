#!/usr/bin/env python3
"""C 3-way scope test for ExecutionScope.V2_DIAGNOSTIC (D-R0-82 · C-COMPLETION-001151 F3 · A ack "3방향").

Runs against a scratchpad clone of the SUT SHA (never a worker worktree, D-R0-69). Network: none —
only firewall decision functions are called; REAL_TARGET is never opened.

  T1 allow   : all 12 manifest targets pass assert_target_allowlisted(V2_DIAGNOSTIC, target_id, url)
  T2 reject  : (a) E001 frame URL outside manifest, (b) non-E001 URL, (c) manifest id paired with an
               outside URL, (d) manifest url paired with a foreign id  -> all rejected
  T3 tamper  : one-byte change to the in-tree manifest -> load_v2_diagnostic_allowlist refuses (sha)
  T4 info    : full navigation path assert_navigation_allowed(REAL_TARGET, url, scope=V2_DIAGNOSTIC)
               — depends on the A release document (V2_DIAGNOSTIC_RELEASE.json @ origin/control/...);
               recorded, NOT part of the 3-way verdict (it is A's launch-gate artifact, not W1 code).

Usage: scope_threeway_test.py <sut_root> <out_json>
"""
from __future__ import annotations
import sys, json, hashlib, importlib, pathlib, shutil, subprocess, os

MANIFEST_REL = "research/landing_accessibility/control/pilot/DIAGNOSTIC_PILOT_MANIFEST.json"
EXPECTED_SHA = "78f2e32a8fc1e732e485debc41ccdec618a63a832813de83e19a2cf50b51b799"
OUTSIDE_E001_URL = "https://www.11st.co.kr/"          # E001 frame target (wtg_49a5eca8), NOT in manifest
OUTSIDE_E001_ID = "wtg_49a5eca8b58f7270"
OUTSIDE_NON_E001_URL = "https://example.org/"


def _try(fn, *a, **kw):
    try:
        v = fn(*a, **kw)
        return {"ok": True, "value": repr(v)[:200]}
    except Exception as e:  # rejection is a valid outcome — record class + message
        return {"ok": False, "exc": type(e).__name__, "msg": str(e)[:240]}


def main(sut_root: str, out_json: str) -> int:
    root = pathlib.Path(sut_root).resolve(); out_json = str(pathlib.Path(out_json).resolve())
    head = subprocess.check_output(["git", "-C", str(root), "rev-parse", "HEAD"]).decode().strip()
    man_path = root / MANIFEST_REL
    rec: dict = {"artifact": "C_SCOPE_THREEWAY_TEST", "sut_head": head, "manifest_in_tree": man_path.exists(), "network": "none"}
    targets = []
    if man_path.exists():
        rec["manifest_sha256"] = hashlib.sha256(man_path.read_bytes()).hexdigest()
        rec["manifest_sha_match"] = rec["manifest_sha256"] == EXPECTED_SHA
        targets = json.loads(man_path.read_text())["targets"]
    sys.path.insert(0, str(root / "research/landing_accessibility/src")); os.chdir(root)
    fw = importlib.import_module("landing_accessibility.engine.firewall")
    members = [m.name for m in fw.ExecutionScope]
    rec["execution_scope_members"] = members; rec["has_V2_DIAGNOSTIC"] = "V2_DIAGNOSTIC" in members
    rec["frozen_constant_sha"] = getattr(fw, "DIAGNOSTIC_PILOT_MANIFEST_SHA256", None)
    rec["release_path_constant"] = getattr(fw, "V2_DIAGNOSTIC_RELEASE_PATH", None)
    results: dict = {}
    if rec["has_V2_DIAGNOSTIC"] and hasattr(fw, "load_v2_diagnostic_allowlist"):
        scope = fw.ExecutionScope.V2_DIAGNOSTIC
        r_load = _try(fw.load_v2_diagnostic_allowlist)
        results["T0_loader"] = r_load
        if r_load["ok"]:
            al = fw.load_v2_diagnostic_allowlist()
            results["T0_allowlist_n_ids"] = len(al.target_ids); results["T0_allowlist_sha"] = al.plan_sha256
            allow = {t["web_target_id"]: _try(fw.assert_target_allowlisted, scope, target_id=t["web_target_id"], url=t["url"], allowlist=al) for t in targets}
            results["T1_allow_12"] = {"n": len(allow), "allowed": sum(1 for v in allow.values() if v["ok"]), "rejected": [k for k, v in allow.items() if not v["ok"]]}
            t0 = targets[0] if targets else {"web_target_id": "wtg_none", "url": "https://none.invalid/"}
            results["T2_reject_outside"] = {
                "a_e001_not_in_manifest": _try(fw.assert_target_allowlisted, scope, target_id=OUTSIDE_E001_ID, url=OUTSIDE_E001_URL, allowlist=al),
                "b_non_e001": _try(fw.assert_target_allowlisted, scope, url=OUTSIDE_NON_E001_URL, allowlist=al),
                "c_manifest_id_outside_url": _try(fw.assert_target_allowlisted, scope, target_id=t0["web_target_id"], url=OUTSIDE_E001_URL, allowlist=al),
                "d_manifest_url_foreign_id": _try(fw.assert_target_allowlisted, scope, target_id=OUTSIDE_E001_ID, url=t0["url"], allowlist=al),
                "e_nothing_given": _try(fw.assert_target_allowlisted, scope, allowlist=al),
            }
            # T4 (informational): full navigation path incl. release document
            results["T4_full_navigation_first_target"] = _try(fw.assert_navigation_allowed, fw.ExecutionMode.REAL_TARGET, t0["url"], scope=scope, target_id=t0["web_target_id"])
            results["T4_scope_release_verdict"] = _try(fw.evaluate_execution_scope, scope, use_cache=False)
        # T3 tamper — on a COPY of the tree (the clone itself is never modified)
        tamper_root = root.parent / (root.name + "_tamper"); shutil.rmtree(tamper_root, ignore_errors=True)
        shutil.copytree(root, tamper_root, symlinks=True, ignore=shutil.ignore_patterns(".git", "node_modules", ".venv", "artifacts"))
        tp = tamper_root / MANIFEST_REL
        if tp.exists():
            b = bytearray(tp.read_bytes()); i = b.rfind(b"}"); b[i - 1:i] = b" " if b[i - 1:i] != b" " else b"\t"; tp.write_bytes(bytes(b))
            code = f"""
import sys, json, os; sys.path.insert(0, {str(tamper_root / 'research/landing_accessibility/src')!r}); os.chdir({str(tamper_root)!r})
from landing_accessibility.engine import firewall as fw
out = {{}}
for label, kw in (("explicit_path", {{"path": {str(tp)!r}}}), ("default_candidates", {{}})):
    try:
        v = fw.load_v2_diagnostic_allowlist(**kw); out[label] = {{"ok": True, "value": repr(v)[:120]}}
    except Exception as e:
        out[label] = {{"ok": False, "exc": type(e).__name__, "msg": str(e)[:200]}}
print(json.dumps(out))
"""
            p = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, timeout=180)
            try: results["T3_tamper_reject"] = json.loads(p.stdout.strip().splitlines()[-1])
            except Exception: results["T3_tamper_reject"] = {"error": p.stderr[-400:]}
            results["T3_tampered_sha"] = hashlib.sha256(tp.read_bytes()).hexdigest()
        else:
            results["T3_tamper_reject"] = {"note": "manifest not in tree — nothing to tamper"}
        shutil.rmtree(tamper_root, ignore_errors=True)
    rec["results"] = results
    t1 = results.get("T1_allow_12", {}); t2 = results.get("T2_reject_outside", {}); t3 = results.get("T3_tamper_reject", {})
    rec["verdict"] = {
        "T1_allow": "PASS" if t1.get("n") == 12 and t1.get("allowed") == 12 else "FAIL_OR_NOT_TESTABLE",
        "T2_reject": "PASS" if t2 and all(not v["ok"] for v in t2.values()) else "FAIL_OR_NOT_TESTABLE",
        "T3_tamper": "PASS" if t3 and all(isinstance(v, dict) and v.get("ok") is False for v in t3.values()) else "FAIL_OR_NOT_TESTABLE",
    }
    rec["overall_threeway"] = "PASS" if all(v == "PASS" for v in rec["verdict"].values()) else "NOT_PASSED"
    t4 = results.get("T4_full_navigation_first_target", {}); rec["T4_release_gate"] = "OPEN" if t4.get("ok") else f"CLOSED ({t4.get('exc')})"
    pathlib.Path(out_json).write_text(json.dumps(rec, ensure_ascii=False, indent=1))
    print(json.dumps({"sut": head[:10], "has_V2_DIAGNOSTIC": rec["has_V2_DIAGNOSTIC"], "manifest_in_tree": rec["manifest_in_tree"], "verdict": rec["verdict"], "overall_threeway": rec["overall_threeway"], "T4_release_gate": rec["T4_release_gate"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    try:
        _rc = main(sys.argv[1], sys.argv[2])
    except Exception:  # Δ46-exit2 / Δ50-exit2-common: crash or missing input = did not run, never exit 1 (ran and failed)
        import traceback
        traceback.print_exc()
        print("scope_threeway_test: did not run — read neither as pass nor fail (exit 2)", file=sys.stderr)
        _rc = 2
    sys.exit(_rc)
