#!/usr/bin/env python3
"""C GATE 1 SAFETY adapter — runner-agnostic skeleton (lane 4).

`run_gate1_safety(sut_root, runner_cmd_template, out_dir)` orchestrates C's existing harnesses against a
scratchpad clone of B's exact SHA (never a B worker worktree — D-R0-69) and leaves TODO hooks for the two
pieces that cannot be written until B's V3 task-first runner interface is known:

  * how the runner is invoked for a FIXTURE plan with a frozen `task_id` (`runner_cmd_template`), and
  * the output schema of the runner's per-candidate action log (needed to score forbidden actions
    against `forbidden_action_matrix.json`).

Steps (each writes its own JSON under `out_dir`; a step that cannot run records SKIPPED + reason, never
raises past `run_gate1_safety`):

  S1  exactly-once      ../../w1/dup_launch_harness.py <sut_root> <out>/s1_dup      (2 procs, FIXTURE, network 0)
  S1b lock race         ../../w1/lock_race_harness.py  <sut_src> <out>/s1b_locks 3 3
  S2  scope fail-closed ./two_layer_scope_probe.py --repo-root <sut_root> --out <out>/s2_scope.json
  S2b 3-way allowlist   ../../pilot/scope_threeway_test.py <sut_root> <out>/s2b_threeway.json
  S3  E001 unchanged    ../../pilot/e001_runner_unchanged_check.py <sut_root> <ref_sha> <cand_sha>
  S4  forbidden actions TODO — needs runner_cmd_template + action-log schema (see `score_forbidden_actions`)

Positive / negative controls are the caller's duty (see GATE1_SAFETY_PLAN.md): S1 must be run once against
a pre-W1 SHA (expect DUPLICATE_LAUNCH_NOT_SUPPRESSED) so that "EXACTLY_ONCE_HOLDS" is known to be a
discriminating verdict rather than an empty-result artefact.

    python3 adapter_interface_stub.py --dry-run            # print planned steps, exit 0
    python3 adapter_interface_stub.py --sut-root DIR --out DIR --ref-sha SHA [--cand-sha SHA] [--runner-cmd 'TEMPLATE']
"""
from __future__ import annotations

import argparse
import json
import pathlib
import subprocess
import sys
import time

HERE = pathlib.Path(__file__).resolve().parent
ASSURANCE = HERE.parents[1]  # research/landing_accessibility/assurance
DUP_LAUNCH = ASSURANCE / "w1" / "dup_launch_harness.py"
LOCK_RACE = ASSURANCE / "w1" / "lock_race_harness.py"
THREEWAY = ASSURANCE / "pilot" / "scope_threeway_test.py"
E001_UNCHANGED = ASSURANCE / "pilot" / "e001_runner_unchanged_check.py"
SCOPE_PROBE = HERE / "two_layer_scope_probe.py"
MATRIX = HERE / "forbidden_action_matrix.json"
SRC_REL = "research/landing_accessibility/src"

#: reference SHA whose E001_FULL runner path (run_e001_real.py / batch.py / layer_firewall.py) is the
#: baseline. joint10 clone HEAD at the time this stub was written. Override with --ref-sha at B's V3 SHA
#: ruling time — C does not hard-code B's future SHA.
DEFAULT_E001_REF_SHA = "e02eee4b46b83bafc4576f4f96e8ef540ec37ae9"

#: Placeholder for B's V3 task-first runner invocation. Tokens: {sut_root} {plan} {out} {task_id}.
#: Unknown today (Phase V3-5 not delivered) — the adapter refuses to run S4 while it is None.
RUNNER_CMD_TEMPLATE_UNKNOWN = None


def _run(cmd: list[str], cwd: pathlib.Path | None, log: pathlib.Path, timeout: int = 900) -> dict:
    """Run one harness as a subprocess; never raise — return rc/duration/log path."""
    t0 = time.time()
    try:
        with open(log, "w", encoding="utf-8") as fh:
            rc = subprocess.run(cmd, cwd=str(cwd) if cwd else None, stdout=fh, stderr=subprocess.STDOUT,
                                timeout=timeout).returncode
        return {"status": "RAN", "rc": rc, "seconds": round(time.time() - t0, 1), "log": str(log)}
    except (OSError, subprocess.SubprocessError) as e:
        return {"status": "ERROR", "rc": None, "error": f"{type(e).__name__}: {e}"[:300], "log": str(log)}


def plan_steps(sut_root: str, runner_cmd_template: str | None, out_dir: str, ref_sha: str,
               cand_sha: str | None) -> list[dict]:
    sut = pathlib.Path(sut_root)
    out = pathlib.Path(out_dir)
    cand = cand_sha or "HEAD"
    return [
        {"id": "S1", "name": "exactly-once duplicate launch (2 procs, FIXTURE, network 0)",
         "cmd": [sys.executable, str(DUP_LAUNCH), str(sut), str(out / "s1_dup"), "1.5"],
         "pass": "runs_per_target all == 1 AND duplicate_suppressed_events >= targets AND rc2 == 0 AND suppression logged BEFORE any evidence dir of proc2 exists",
         "reuse": "as-is; ADAPT: the FIXTURE dryrun script name may change under the V3 task-first runner"},
        {"id": "S1b", "name": "TargetLock cross-process race (3 procs x 3 keys)",
         "cmd": [sys.executable, str(LOCK_RACE), str(sut / SRC_REL), str(out / "s1b_locks"), "3", "3"],
         "pass": "per key exactly 1 proceed=True; others DUPLICATE_SUPPRESSED; lock files never deleted",
         "reuse": "as-is; ADAPT only if IdempotencyKey gains a task_id / task_contract_sha component (C expects it must)"},
        {"id": "S2", "name": "two-layer scope fail-closed probe (import both firewalls, no network)",
         "cmd": [sys.executable, str(SCOPE_PROBE), "--repo-root", str(sut), "--out", str(out / "s2_scope.json")],
         "pass": "unknown / hypothetical scopes denied by BOTH layers; layer 2 source mentions manifest sha (after T-B-BLK-009 ruling); layers agree on every known scope",
         "reuse": "new (this lane)"},
        {"id": "S2b", "name": "3-way allowlist test (allow12 / outside deny / tamper deny)",
         "cmd": [sys.executable, str(THREEWAY), str(sut), str(out / "s2b_threeway.json")],
         "pass": "T1 12/12 allowed, T2 all rejected, T3 tampered manifest refused by sha",
         "reuse": "as-is for V2_DIAGNOSTIC; ADAPT: parametrise MANIFEST_REL/EXPECTED_SHA for V3 main-50 manifest once A freezes it"},
        {"id": "S3", "name": "E001_FULL runner path byte-identical vs reference SHA",
         "cmd": [sys.executable, str(E001_UNCHANGED), str(sut), ref_sha, cand],
         "pass": "all_unchanged == true for run_e001_real.py, batch.py, layer_firewall.py (if layer_firewall.py legitimately changes under T-B-BLK-009, A must ticket the exception and C re-baselines)",
         "reuse": "as-is"},
        {"id": "S4", "name": "forbidden-action scoring on 13 guard fixtures under frozen task_id",
         "cmd": None if not runner_cmd_template else [runner_cmd_template],
         "pass": "zero events on any never_activate control; per-candidate state == expected_state (matrix)",
         "reuse": "BLOCKED on B: runner_cmd_template + action-log schema unknown",
         "blocked": runner_cmd_template is None},
    ]


def score_forbidden_actions(action_log_path: pathlib.Path, matrix_path: pathlib.Path = MATRIX) -> dict:
    """TODO(B interface): score a runner action log against forbidden_action_matrix.json.

    Expected once the schema is known: for each fixture, (a) zero events whose target matches a
    `never_activate` selector, (b) each listed control's reported state == expected_state. Until the
    schema is known this returns a SKIPPED record — it must never return PASS by default (an empty
    log and a passing log must not look the same: verification-requires-control-group).
    """
    return {"status": "SKIPPED", "reason": "runner action-log schema unknown (B V3-5 not delivered)",
            "action_log": str(action_log_path), "matrix": str(matrix_path)}


def run_gate1_safety(sut_root: str, runner_cmd_template: str | None, out_dir: str, *,
                     ref_sha: str = DEFAULT_E001_REF_SHA, cand_sha: str | None = None,
                     dry_run: bool = False) -> dict:
    """Run the GATE 1 SAFETY battery against `sut_root` (a scratchpad clone at B's exact SHA).

    Returns a record with one entry per step. Verdict logic is deliberately NOT collapsed into a single
    boolean here — each step's JSON is the evidence; the plan document defines pass criteria and C
    reads them. `dry_run=True` prints the planned steps and runs nothing.
    """
    out = pathlib.Path(out_dir)
    steps = plan_steps(sut_root, runner_cmd_template, out_dir, ref_sha, cand_sha)
    rec: dict = {"artifact": "C_GATE1_SAFETY_ADAPTER", "sut_root": sut_root, "out_dir": out_dir,
                 "ref_sha": ref_sha, "cand_sha": cand_sha or "HEAD", "dry_run": dry_run, "steps": []}
    for s in steps:
        entry = {k: s[k] for k in ("id", "name", "pass", "reuse")}
        entry["cmd"] = s["cmd"]
        if dry_run:
            entry["status"] = "PLANNED" if s["cmd"] else "BLOCKED_ON_B_INTERFACE"
        elif s.get("blocked") or s["cmd"] is None:
            entry["status"] = "SKIPPED"; entry["reason"] = "runner_cmd_template is None"
        else:
            out.mkdir(parents=True, exist_ok=True)
            entry.update(_run(s["cmd"], pathlib.Path(sut_root), out / f"{s['id']}.log"))
        rec["steps"].append(entry)
    if not dry_run:
        rec["s4_scoring"] = score_forbidden_actions(out / "s4_action_log.jsonl")
        out.mkdir(parents=True, exist_ok=True)
        (out / "C_GATE1_SAFETY_ADAPTER.json").write_text(json.dumps(rec, ensure_ascii=False, indent=1),
                                                          encoding="utf-8")
    return rec


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="C GATE 1 SAFETY adapter (lane 4)")
    ap.add_argument("--sut-root", default="/tmp/claude-1000/-home-sieg-projects-wsl-ProjectFinal/"
                    "9025a829-6001-41cc-967e-a7eebf607234/scratchpad/joint10")
    ap.add_argument("--out", default=str(HERE / "out"))
    ap.add_argument("--ref-sha", default=DEFAULT_E001_REF_SHA)
    ap.add_argument("--cand-sha", default=None)
    ap.add_argument("--runner-cmd", default=RUNNER_CMD_TEMPLATE_UNKNOWN,
                    help="B V3 task-first runner template with {sut_root} {plan} {out} {task_id}; unknown today")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args(argv)
    rec = run_gate1_safety(args.sut_root, args.runner_cmd, args.out, ref_sha=args.ref_sha,
                           cand_sha=args.cand_sha, dry_run=args.dry_run)
    for s in rec["steps"]:
        cmd = " ".join(s["cmd"]) if s["cmd"] else "(no command — blocked on B interface)"
        print(f"[{s['id']}] {s['status']:<24} {s['name']}\n      cmd : {cmd}\n      pass: {s['pass']}\n      reuse: {s['reuse']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
