#!/usr/bin/env python3
"""C 3-way scope test for V2_DIAGNOSTIC (D-R0-82 + C-COMPLETION-001151 F3).

Runs against a scratchpad clone of the integration SHA (never a worker worktree, D-R0-69).
  T1 allow   : every manifest target URL passes the navigation/scope check under V2_DIAGNOSTIC
  T2 reject  : an E001 URL outside the manifest (and a non-E001 URL) is rejected
  T3 tamper  : a one-byte change in the in-tree manifest makes the loader refuse (sha mismatch)
Network: none. REAL_TARGET is never opened — only the allowlist/scope decision functions are called.

Usage: scope_threeway_test.py <sut_root> <out_json>
The SUT interface is discovered by introspection (enum member + loader/assert functions) so the
harness does not depend on W1's exact naming; whatever it finds is recorded in the output.
"""
from __future__ import annotations
import sys, json, hashlib, importlib, inspect, pathlib, shutil, subprocess, traceback

MANIFEST_REL = "research/landing_accessibility/control/pilot/DIAGNOSTIC_PILOT_MANIFEST.json"
EXPECTED_SHA = "78f2e32a8fc1e732e485debc41ccdec618a63a832813de83e19a2cf50b51b799"
OUTSIDE_E001_URL = "https://www.11st.co.kr/"          # E001 frame target, NOT in manifest
OUTSIDE_NON_E001_URL = "https://example.org/"


def _find(mod, *needles):
    out = []
    for name, obj in inspect.getmembers(mod):
        if callable(obj) and all(n in name.lower() for n in needles):
            out.append((name, obj))
    return out


def _try(fn, *a, **kw):
    try:
        return {"ok": True, "value": repr(fn(*a, **kw))[:300]}
    except Exception as e:  # rejection is a valid outcome — record class + message
        return {"ok": False, "exc": type(e).__name__, "msg": str(e)[:300]}


def main(sut_root: str, out_json: str) -> int:
    root = pathlib.Path(sut_root).resolve(); out_json = str(pathlib.Path(out_json).resolve())
    head = subprocess.check_output(["git", "-C", str(root), "rev-parse", "HEAD"]).decode().strip()
    man_path = root / MANIFEST_REL
    rec: dict = {"artifact": "C_SCOPE_THREEWAY_TEST", "sut_head": head, "manifest_in_tree": man_path.exists()}
    if man_path.exists():
        rec["manifest_sha256"] = hashlib.sha256(man_path.read_bytes()).hexdigest()
        rec["manifest_sha_match"] = rec["manifest_sha256"] == EXPECTED_SHA
        targets = json.loads(man_path.read_text())["targets"]
    else:
        targets = []
    sys.path.insert(0, str(root / "research/landing_accessibility/src"))
    import os; os.chdir(root)
    fw = importlib.import_module("landing_accessibility.engine.firewall")
    scope_enum = getattr(fw, "ExecutionScope", None)
    members = [m.name for m in scope_enum] if scope_enum else []
    rec["execution_scope_members"] = members
    rec["has_V2_DIAGNOSTIC"] = "V2_DIAGNOSTIC" in members
    loaders = _find(fw, "diagnostic")
    rec["discovered_callables"] = [n for n, _ in loaders]
    nav = _find(fw, "navigation") or _find(fw, "allowed")
    rec["nav_callables"] = [n for n, _ in nav]
    results = {}
    if rec["has_V2_DIAGNOSTIC"] and loaders:
        scope = scope_enum["V2_DIAGNOSTIC"]
        # pick the loader-like callable (one that mentions 'load' or 'allowlist'); fall back to first
        loader = next((o for n, o in loaders if "load" in n.lower() or "allowlist" in n.lower()), loaders[0][1])
        rec["loader_used"] = loader.__name__
        r_load = _try(loader)
        results["T0_loader_on_frozen_manifest"] = r_load
        # T1 / T2 via navigation assert if present, else via loader-returned allowlist membership
        nav_fn = next((o for n, o in nav if "assert" in n.lower()), None)
        if nav_fn is not None:
            sig = str(inspect.signature(nav_fn)); rec["nav_signature"] = sig
            def call_nav(url):
                try:
                    return _try(nav_fn, url, scope)
                except TypeError:
                    return _try(nav_fn, url, scope=scope)
            allow = {t["web_target_id"]: call_nav(t["url"]) for t in targets}
            results["T1_allow_12"] = {"n": len(allow), "allowed": sum(1 for v in allow.values() if v["ok"]), "detail": allow}
            results["T2_reject_outside"] = {"e001_not_in_manifest": call_nav(OUTSIDE_E001_URL), "non_e001": call_nav(OUTSIDE_NON_E001_URL)}
        else:
            results["T1_T2_note"] = "no assert_navigation-like callable found; allowlist membership only"
            if r_load["ok"]:
                results["T1_T2_allowlist_repr"] = r_load["value"]
        # T3 tamper: flip one byte in a COPY of the SUT (never the original clone) — re-import in subprocess
        tamper_root = root.parent / (root.name + "_tamper")
        shutil.rmtree(tamper_root, ignore_errors=True)
        shutil.copytree(root, tamper_root, symlinks=True, ignore=shutil.ignore_patterns(".git", "node_modules", ".venv"))
        tp = tamper_root / MANIFEST_REL
        b = bytearray(tp.read_bytes()); b[-2:-1] = b" "  # change one byte near the end (before final newline/brace)
        tp.write_bytes(bytes(b))
        code = f"""
import sys, json, inspect; sys.path.insert(0, {str(tamper_root / 'research/landing_accessibility/src')!r})
import os; os.chdir({str(tamper_root)!r})
from landing_accessibility.engine import firewall as fw
fn = getattr(fw, {loader.__name__!r})
try:
    v = fn(); print(json.dumps({{"ok": True, "value": repr(v)[:200]}}))
except Exception as e:
    print(json.dumps({{"ok": False, "exc": type(e).__name__, "msg": str(e)[:300]}}))
"""
        p = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, timeout=120)
        try:
            results["T3_tamper_reject"] = json.loads(p.stdout.strip().splitlines()[-1])
        except Exception:
            results["T3_tamper_reject"] = {"ok": None, "stdout": p.stdout[-300:], "stderr": p.stderr[-500:]}
        results["T3_tampered_sha"] = hashlib.sha256(tp.read_bytes()).hexdigest()
        shutil.rmtree(tamper_root, ignore_errors=True)
    rec["results"] = results
    # verdict — all three directions must hold; missing pieces are NOT_TESTABLE, never PASS
    t1 = results.get("T1_allow_12", {}); t2 = results.get("T2_reject_outside", {}); t3 = results.get("T3_tamper_reject", {})
    rec["verdict"] = {
        "T1_allow": "PASS" if t1.get("n") == 12 and t1.get("allowed") == 12 else "FAIL_OR_NOT_TESTABLE",
        "T2_reject": "PASS" if t2 and not t2["e001_not_in_manifest"]["ok"] and not t2["non_e001"]["ok"] else "FAIL_OR_NOT_TESTABLE",
        "T3_tamper": "PASS" if t3.get("ok") is False else "FAIL_OR_NOT_TESTABLE",
    }
    rec["overall"] = "PASS" if all(v == "PASS" for v in rec["verdict"].values()) else "NOT_PASSED"
    pathlib.Path(out_json).write_text(json.dumps(rec, ensure_ascii=False, indent=1))
    print(json.dumps({"sut": head[:10], "has_V2_DIAGNOSTIC": rec["has_V2_DIAGNOSTIC"], "manifest_in_tree": rec["manifest_in_tree"], "verdict": rec["verdict"], "overall": rec["overall"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1], sys.argv[2]))
