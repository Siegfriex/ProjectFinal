#!/usr/bin/env python3
"""C GATE 1 SAFETY (c) — two-layer scope fail-closed probe. OFFLINE: no network, no browser.

Imports BOTH firewall layers of the SUT independently and asks each the same question,
"may REAL_TARGET open under scope S?", for a list of scope names (known, hypothetical, unknown).

  layer 1  engine/firewall.py            evaluate_execution_scope(S)          -> ReleaseVerdict(allowed, reason)
  layer 2  e001_runner/layer_firewall.py assert_batch_execution_mode_safe(REAL_TARGET, S) -> pass | exception class

Also records (i) mode-only rows (FIXTURE / SHADOW_DRY_RUN / REAL_TARGET without scope) for layer 2,
(ii) which release document path each layer binds per scope (read from module constants — not from
the other layer), (iii) whether layer 2's SOURCE mentions a manifest sha anywhere (grep), which is the
current T-B-BLK-009 gap: layer 2 does not re-verify DIAGNOSTIC_PILOT_MANIFEST_SHA256.

Both layers read their release document with `git show origin/control/landing-orchestrator:...` on the
given repo root — a local git object read, not a network call (the clone's remote is a filesystem path).
Import failures are recorded per layer, never raised: an unimportable layer is itself a finding.

Usage: two_layer_scope_probe.py [--repo-root DIR] [--scopes S1 S2 ...] [--out JSON]
Exit 0 always when the probe itself ran (verdicts are data; a "deny" is not a probe failure).
"""
from __future__ import annotations

import argparse
import importlib
import json
import os
import pathlib
import re
import subprocess
import sys
import traceback

DEFAULT_ROOT = (
    "/tmp/claude-1000/-home-sieg-projects-wsl-ProjectFinal/"
    "9025a829-6001-41cc-967e-a7eebf607234/scratchpad/joint10"
)
DEFAULT_SCOPES = ["E000_FAST", "E001_FULL", "V2_DIAGNOSTIC", "V3_MAIN50", "unknown"]
SRC_REL = "research/landing_accessibility/src"
L1_MOD = "landing_accessibility.engine.firewall"
L2_MOD = "landing_accessibility.e001_runner.layer_firewall"
MANIFEST_SHA_PATTERN = re.compile(r"manifest_sha|MANIFEST_SHA|manifest_sha256|DIAGNOSTIC_PILOT_MANIFEST", re.I)


def _import(name: str) -> tuple[object | None, str | None]:
    try:
        return importlib.import_module(name), None
    except Exception:  # noqa: BLE001 — import failure is a recorded finding
        return None, traceback.format_exc(limit=3)[-600:]


def _short(s: object, n: int = 110) -> str:
    return re.sub(r"\s+", " ", str(s))[:n]


def layer1_verdict(fw: object, scope: str, root: pathlib.Path) -> dict:
    try:
        v = fw.evaluate_execution_scope(scope, repo_dir=root, use_cache=False)  # type: ignore[attr-defined]
        return {"allowed": bool(v.allowed), "outcome": "ALLOW" if v.allowed else "DENY",
                "reason": _short(v.reason), "doc": v.document_ref, "exc": None}
    except Exception as e:  # noqa: BLE001
        return {"allowed": False, "outcome": "DENY(exc)", "reason": _short(e), "doc": None,
                "exc": type(e).__name__}


def layer2_verdict(lf: object, mode: str, scope: str | None) -> dict:
    try:
        r = lf.assert_batch_execution_mode_safe(mode, scope)  # type: ignore[attr-defined]
        return {"allowed": True, "outcome": "PASS", "reason": f"returned {r!r}", "exc": None}
    except Exception as e:  # noqa: BLE001
        return {"allowed": False, "outcome": "BLOCK(exc)", "reason": _short(e), "exc": type(e).__name__}


def layer1_binding(fw: object, scope: str) -> str | None:
    """Which release doc layer 1 binds to `scope` — derived from layer-1 constants only."""
    m = {"E000_FAST": "P0_RELEASE_PATH", "V2_DIAGNOSTIC": "V2_DIAGNOSTIC_RELEASE_PATH"}
    members = {s.value for s in getattr(fw, "ExecutionScope", [])} if hasattr(fw, "ExecutionScope") else set()
    if scope not in members:
        return None
    const = m.get(scope, "E001_RELEASE_PATH")
    return f"{getattr(fw, 'P0_RELEASE_REF', '?')}:{getattr(fw, const, '?')}"


def layer2_binding(lf: object, scope: str) -> str | None:
    scopes = getattr(lf, "BATCH_LAYER_REAL_SCOPES", {})
    b = scopes.get(scope)
    return f"{getattr(lf, 'BATCH_LAYER_RELEASE_REF', '?')}:{b[0]} flag={b[1]}" if b else None


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--repo-root", default=DEFAULT_ROOT)
    ap.add_argument("--scopes", nargs="*", default=DEFAULT_SCOPES)
    ap.add_argument("--out", default=None, help="write full JSON record here")
    args = ap.parse_args(argv)

    root = pathlib.Path(args.repo_root).resolve()
    rec: dict = {"artifact": "C_GATE1_TWO_LAYER_SCOPE_PROBE", "repo_root": str(root), "network": "none",
                 "browser": "none", "sut_head": None, "layers": {}, "rows": [], "mode_rows": []}
    try:
        rec["sut_head"] = subprocess.check_output(["git", "-C", str(root), "rev-parse", "HEAD"],
                                                  text=True, timeout=30).strip()
    except Exception as e:  # noqa: BLE001
        rec["sut_head"] = f"unavailable: {type(e).__name__}"

    src = root / SRC_REL
    sys.path.insert(0, str(src))
    os.chdir(root) if root.exists() else None
    fw, e1 = _import(L1_MOD)
    lf, e2 = _import(L2_MOD)
    if fw is None or lf is None:   # Δ46-exit2: a probe that could not import the layers DID NOT RUN — it must not print 'fail-closed'
        rec["did_not_run"] = True; rec["note"] = "did not run — layer import failed; read neither as fail-closed nor as allow"
        print("two_layer_scope_probe: did not run — layer import failed (exit 2)", file=sys.stderr)
        if args.out: pathlib.Path(args.out).write_text(json.dumps(rec, ensure_ascii=False, indent=1), encoding="utf-8")
        sys.exit(2)
    rec["layers"]["layer1_engine_firewall"] = {"module": L1_MOD, "imported": fw is not None, "error": e1,
                                              "file": getattr(fw, "__file__", None)}
    rec["layers"]["layer2_batch_layer_firewall"] = {"module": L2_MOD, "imported": lf is not None, "error": e2,
                                                   "file": getattr(lf, "__file__", None)}

    # (iii) grep layer 2 SOURCE for any manifest-sha mention — independence evidence for T-B-BLK-009.
    l2_path = src / "landing_accessibility/e001_runner/layer_firewall.py"
    l2_text = l2_path.read_text(encoding="utf-8", errors="replace") if l2_path.exists() else ""
    hits = [f"L{i}: {_short(line, 90)}" for i, line in enumerate(l2_text.splitlines(), 1)
            if MANIFEST_SHA_PATTERN.search(line)]
    rec["layer2_mentions_manifest_sha"] = bool(hits)
    rec["layer2_manifest_sha_hits"] = hits
    # actual import statements only — docstrings mention engine.firewall by name on purpose
    rec["layer2_imports_layer1"] = bool(re.search(r"^\s*(from|import)\s+\S*engine", l2_text, re.M))
    rec["layer2_known_real_scopes"] = sorted(getattr(lf, "BATCH_LAYER_REAL_SCOPES", {}).keys()) if lf else None
    rec["layer1_known_scopes"] = sorted(s.value for s in fw.ExecutionScope) if fw and hasattr(fw, "ExecutionScope") else None
    rec["layer1_frozen_manifest_sha"] = getattr(fw, "DIAGNOSTIC_PILOT_MANIFEST_SHA256", None) if fw else None

    for scope in args.scopes:
        row = {"scope": scope}
        row["l1"] = layer1_verdict(fw, scope, root) if fw else {"outcome": "IMPORT_FAIL", "reason": _short(e1), "exc": None, "allowed": False}
        row["l1_binding"] = layer1_binding(fw, scope) if fw else None
        row["l2"] = layer2_verdict(lf, "REAL_TARGET", scope) if lf else {"outcome": "IMPORT_FAIL", "reason": _short(e2), "exc": None, "allowed": False}
        row["l2_binding"] = layer2_binding(lf, scope) if lf else None
        row["both_deny"] = (not row["l1"]["allowed"]) and (not row["l2"]["allowed"])
        row["agree"] = row["l1"]["allowed"] == row["l2"]["allowed"]
        rec["rows"].append(row)

    for mode, scope in [("FIXTURE", None), ("SHADOW_DRY_RUN", None), ("REAL_TARGET", None),
                        ("FIXTURE", "E000_FAST"), ("BOGUS_MODE", None)]:
        mr = {"mode": mode, "scope": scope}
        mr["l2"] = layer2_verdict(lf, mode, scope) if lf else {"outcome": "IMPORT_FAIL", "reason": _short(e2), "exc": None, "allowed": False}
        if fw:
            try:
                r = fw.assert_mode_allowed(mode, scope=scope)  # type: ignore[attr-defined]
                mr["l1"] = {"outcome": "PASS", "reason": repr(r), "exc": None, "allowed": True}
            except Exception as e:  # noqa: BLE001
                mr["l1"] = {"outcome": "BLOCK(exc)", "reason": _short(e), "exc": type(e).__name__, "allowed": False}
        else:
            mr["l1"] = {"outcome": "IMPORT_FAIL", "reason": _short(e1), "exc": None, "allowed": False}
        rec["mode_rows"].append(mr)

    # ── print markdown table ──
    print(f"SUT {rec['sut_head']}  root={root}")
    print(f"layer1 imported={fw is not None}  layer2 imported={lf is not None}  "
          f"layer2_imports_layer1={rec['layer2_imports_layer1']}  layer2_mentions_manifest_sha={rec['layer2_mentions_manifest_sha']}")
    print("| scope | L1 engine firewall | L1 exc | L2 batch layer_firewall | L2 exc | both deny | L2 binding |")
    print("|---|---|---|---|---|---|---|")
    for r in rec["rows"]:
        print(f"| {r['scope']} | {r['l1']['outcome']}: {_short(r['l1']['reason'], 70)} | {r['l1']['exc'] or '-'} "
              f"| {r['l2']['outcome']}: {_short(r['l2']['reason'], 70)} | {r['l2']['exc'] or '-'} "
              f"| {'yes' if r['both_deny'] else 'NO'} | {r['l2_binding'] or 'none (fail-closed)'} |")
    print("| mode / scope | L1 assert_mode_allowed | L2 assert_batch_execution_mode_safe |")
    print("|---|---|---|")
    for m in rec["mode_rows"]:
        print(f"| {m['mode']} / {m['scope']} | {m['l1']['outcome']} {m['l1']['exc'] or ''} | {m['l2']['outcome']} {m['l2']['exc'] or ''} |")
    print("layer2 manifest-sha grep hits:", hits or "NONE")

    if args.out:
        pathlib.Path(args.out).write_text(json.dumps(rec, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
        print("wrote", args.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
