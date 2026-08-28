#!/usr/bin/env python3
"""C demonstrator for Δ46-exit2 / Δ50-exit2-common (+ D-V3-FINDING-023 except sweep, D-V3-ADDENDUM-006 benign-default
sweep, T-B-V3-FC-005/R43 vacuous-pass sweep) over every executable entry point under assurance/ except the owner-excluded
tools. Writes gate1/EXIT_SEMANTICS_AUDIT_C.json. Each proof runs a real subprocess (or an in-process function call for
library-level fixes); mutated copies are written to the scratchpad (lane directories) or as `_esd_*` temp siblings that are
deleted afterwards — the real tool files are never mutated.

  must_flag     : missing input / injected crash / empty input  ⇒ exit 2 (3 for evidence_lineage_check) + did-not-run message
  must_not_flag : the tool's usual fixture/selftest run          ⇒ exit 0 and its usual counts

Exit: 0 = every case matched its expectation · 1 = at least one case did not · 2 = the demonstrator itself crashed.
"""
from __future__ import annotations

import ast
import datetime as _dt
import hashlib
import json
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile
import time

HERE = pathlib.Path(__file__).resolve().parent            # gate1/
A = HERE.parent                                            # assurance/
PY = sys.executable
KST = _dt.timezone(_dt.timedelta(hours=9), "KST")
SP = pathlib.Path(os.environ.get("ESD_SCRATCH", "/tmp/claude-1000/-home-sieg-projects-wsl-ProjectFinal/9025a829-6001-41cc-967e-a7eebf607234/scratchpad/exit_audit_demo"))
OUT = HERE / "EXIT_SEMANTICS_AUDIT_C.json"
DNR = "did not run"
EXCLUDED_BY_OWNER = {"c_bus_scan.py": "converted earlier (A/C shared convention)", "gate1/intake/r32_inventory.py": "converted earlier",
                     "gate1/run_gate1.py": "converted earlier", "gate1/control_failure_demo_c.py": "converted earlier",
                     "gate1/lane4_safety_adapter/two_layer_scope_probe.py": "converted earlier", "c_hb_measure.py": "converted earlier",
                     "mirror_sync.py": "R51 in progress (C body)"}
ENTRY_POINTS = [  # rel path → hand-authored semantics (before = at HEAD 67842d7, after = working tree)
    ("bus.py", "0 ran (any subcommand) · 1 selftest FAIL (explicit) · crash/IndexError(no argv)/missing ticket → Python default 1", "0 ran · 1 selftest AssertionError (ran and failed) · 2 crash / missing ticket / missing argv + message", False, True, "inline CLI block wrapped (module globals preserved)"),
    ("clean0/qa_retention.py", "0 always (report; MISMATCH still 0) · crash / missing A manifest or B mart → 1", "0 ran (report-only, verdict in JSON) · 2 crash / missing input + message", False, True, "reads A/B worktrees — normal run NOT_EXERCISED by this worker"),
    ("gate1/c_terminal_table.py", "0 selftest OK · 1 selftest problems · crash → 1", "0 · 1 · 2 crash + message", False, True, ""),
    ("gate1/comparators/adapter_map.py", "0 always · missing --show file → 1 (crash)", "0 · 2 missing file / crash", False, True, ""),
    ("gate1/comparators/compare_lane1.py", "0 PASS · 1 anything else incl. NOT_TESTABLE (nothing compared) · crash/missing map → 1", "0 PASS · 1 FAIL (ran) · 2 NOT_TESTABLE (no item ran) / crash / missing input + message", False, True, "run_gate1.py uses compare_all in-process; CLI exit only"),
    ("gate1/comparators/compare_lane2.py", "same as lane1", "same as lane1 (after)", False, True, ""),
    ("gate1/comparators/compare_lane3.py", "same as lane1", "same as lane1 (after)", False, True, ""),
    ("gate1/comparators/grade_lane4.py", "same as lane1", "same as lane1 (after)", False, True, ""),
    ("gate1/comparators/selftest.py", "0 OK · 1 FAILED · crash → 1", "0 · 1 · 2 crash + message", False, True, ""),
    ("gate1/intake/r32_selftest.py", "0 all pass · 1 any step fails · crash (incl. AssertionError on tamper anchor) → 1", "0 · 1 · 2 crash/precondition + message", False, True, ""),
    ("gate1/lane1_task_binding/selfcheck.py", "0 PASS · 1 FAIL · missing task_contracts.json → 1 (crash)", "0 · 1 · 2 missing fixture / crash + message", False, True, "harness-defect anchor line untouched (control_failure_demo_c / run_gate1_selftest)"),
    ("gate1/lane2_label_reveal/measure_geometry.py", "0 all fixtures PASS (0/0 too) · 1 otherwise · missing EXPECTATIONS/playwright → 1 (import-time)", "0 · 1 · 2 crash / missing EXPECTATIONS / no playwright / zero fixtures + message", False, True, "module-level guards for EXPECTATIONS + playwright import"),
    ("gate1/lane3_sequence_dismiss_auth/walk_fixture.py", "0 ALL PASS (0/0 too) · 1 · import-time crash → 1", "0 · 1 · 2 crash / missing EXPECTATIONS / no playwright / zero fixtures + message", False, True, ""),
    ("gate1/lane4_safety_adapter/adapter_interface_stub.py", "0 always · crash → 1", "0 ran · 2 crash + message", False, True, ""),
    ("gate1/lane5_evidence/evidence_lineage_check.py", "0 no systemic · 2 SYSTEMIC · 3 usage · crash → 1 · EMPTY DIR → 0 COMPLETE_WITH_ISOLATED_DEFECTS (vacuous)", "0 · 2 SYSTEMIC (tool-local ≡ A's 1) · 3 usage / crash / NO_EVIDENCE_INPUT (tool-local did-not-run ≡ A's 2) + message · checks_performed field", True, True, "NOT renumbered: run_gate1.py L5 binds expect_rc=2 on bad_* fixtures — a crash or an empty dir must never satisfy that negative-control expectation, so did-not-run is 3 here"),
    ("gate1/lane5_evidence/make_synthetic_evidence.py", "0 · crash → 1", "0 · 2 crash + message", False, True, "generator"),
    ("gate1/lane6_stats/synthetic_family_demo.py", "0 · Q8 ValueError (ran, failed) → 1 · crash → 1 (same code)", "0 · 1 R6 Q8 rejection (ran and failed) · 2 crash + message", False, True, ""),
    ("gate1/lane6_stats/variance_control.py", "0 controls ok · 1 not · crash → 1", "0 · 1 · 2 crash + message", False, True, ""),
    ("gate1/lane7_grain_determinism/converge_check.py", "0 PASS/NEGCTRL_OK (n_ok>0 required) · 1 · crash / impl_b SystemExit(str) → 1", "0 · 1 · 2 crash / missing probe_like / impl_b fixture-shape SystemExit(str) + message", False, True, ""),
    ("gate1/lane7_grain_determinism/determinism_check.py", "0 PASS · 1 FAIL · 2 runner failed / fields missing (already) · crash (e.g. missing --policy-doc) → 1", "0 · 1 · 2 runner failed / fields missing / crash / missing input + message", False, True, ""),
    ("gate1/lane7_grain_determinism/fake_runner_det.py", "0 · missing fixture → 1", "0 · 2 missing fixture / crash + message", False, True, "fake SUT; determinism_check reads rc≠0 as runner failed"),
    ("gate1/lane7_grain_determinism/fake_runner_rand.py", "same", "same (after)", False, True, ""),
    ("gate1/lane7_grain_determinism/impl_a.py", "0 · missing fixture → 1", "0 · 2 + message", False, True, "library CLI"),
    ("gate1/lane7_grain_determinism/impl_b.py", "0 · missing fixture → 1 · malformed fixture SystemExit(str) → 1", "0 · 2 missing/malformed fixture / crash + message", False, True, "library raise SystemExit(str) untouched; CLI maps it to 2"),
    ("gate1/lane7_grain_determinism/validate_probe_like_playwright.py", "0 validated (0 checks too) · 1 mismatch · crash → 1", "0 · 1 · 2 crash / no playwright / zero checks + message", False, True, ""),
    ("gate1/run_gate1_selftest.py", "0 · 1 · crash (incl. AssertionError anchors) → 1", "0 · 1 · 2 crash/precondition + message", False, True, ""),
    ("mlflow_log.py", "0 prints constants", "unchanged: no inputs, no verdict (prints TRACKING_URI/EXPERIMENT)", None, False, "UNCHANGED"),
    ("pilot/e001_runner_unchanged_check.py", "0 unchanged · 1 changed — ALSO 1 when repo/sha unresolvable or no ref blobs (conflation) · crash → 1", "0 · 1 changed (ran) · 2 sha unresolvable / no baseline blobs / crash + message", False, True, ""),
    ("pilot/preflight_sampling.py", "module-level script (no __main__): 0 ran · crash/missing git object → 1", "0 ran · 2 crash + message (whole body wrapped at module level; globals preserved)", False, True, "not matched by the __main__/argparse grep — found by the denominator walk"),
    ("pilot/scope_threeway_test.py", "0 always (verdict in JSON) · missing SUT → 1 (crash)", "0 ran · 2 crash / missing SUT + message", False, True, "normal run needs a SUT clone — NOT_EXERCISED"),
    ("qa_base.py", "0 · missing ticket → 1", "0 · 2 missing ticket / crash + message", False, True, ""),
    ("qa_claim.py", "0 · 2 scan invalid (already did-not-run class) · crash → 1", "0 · 2 scan invalid (+message) / crash + message", False, True, ""),
    ("qa_evidence.py", "0 always (verdict in JSON; MATCH with zero batches = vacuous) · crash/missing plan → 1", "0 ran · 2 crash / missing input / NO_INPUT (zero sealed batches, checks_performed=0) + message", False, True, ""),
    ("qa_mart.py", "0 always (incl. 'no raw rows' early return) · crash → 1", "0 ran · 2 crash / missing input / no raw rows + message", False, True, ""),
    ("recovery/fixtures/run_partial_depth_fixtures.py", "0 · 1 · crash / firewall assert → 1", "0 · 1 · 2 crash / precondition / zero cases + message", False, True, "imports B worker engine — normal run NOT_EXERCISED; _check() control in-process"),
    ("stats_replay.py", "0 self-test OK · assert fail → 1 · scipy missing/crash → 1 (same code)", "0 · 1 self-test assertion (ran and failed) · 2 crash + message", False, True, "__main__ block is mid-file"),
    ("stream_qa.py", "daemon: never exits normally · crash → 1", "crash → 2 + message", False, True, "scans other planes' out_dirs — NOT_EXERCISED"),
    ("w1/dup_launch_harness.py", "0 always — missing SUT script ⇒ INCONCLUSIVE + 0 (conflation) · crash → 1", "0 ran · 2 missing SUT script / crash + message", False, True, ""),
    ("w1/lock_race_harness.py", "main() return value DISCARDED ⇒ always 0 (even exactly_once_holds=false) · crash → 1", "0 holds · 1 does not hold (ran) · 2 SUT absent / no worker decision / crash + message", False, True, "return value now propagated"),
    ("w2/dom_replay_probe.py", "0 always · missing probe js / B mart → 1", "0 ran · 2 crash / missing input / no playwright + message", False, True, "reads B artifacts — NOT_EXERCISED"),
    ("w2/holdout_scorer.py", "0 always · 2 usage (already) · missing files → 1", "0 ran · 2 usage (+message) / missing files / crash + message", False, True, ""),
]


# ---------------------------------------------------------------- helpers
def now() -> str:
    return _dt.datetime.now(KST).isoformat(timespec="seconds")


def sha(p: pathlib.Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def git_head_sha(rel: str) -> str | None:
    r = subprocess.run(["git", "-C", str(A), "show", f"HEAD:research/landing_accessibility/assurance/{rel}"], capture_output=True)
    return hashlib.sha256(r.stdout).hexdigest() if r.returncode == 0 else None


def run(cmd: list[str], timeout: int = 900, cwd: pathlib.Path | None = None) -> dict:
    t0 = time.time()
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, cwd=str(cwd) if cwd else None)
        return {"rc": r.returncode, "stdout_tail": r.stdout.strip().splitlines()[-3:], "stderr_last": r.stderr.strip().splitlines()[-1:],
                "seconds": round(time.time() - t0, 1)}
    except subprocess.TimeoutExpired:
        return {"rc": None, "stdout_tail": [], "stderr_last": [f"timeout>{timeout}s"], "seconds": round(time.time() - t0, 1)}


CASES: list[dict] = []


def case(tool: str, name: str, role: str, cmd: list[str], expect_rc: int, expect_msg: str | None = None, note: str = "", timeout: int = 900, cwd=None, counts_from=None):
    r = run(cmd, timeout=timeout, cwd=cwd)
    msg_ok = True if expect_msg is None else any(expect_msg in ln for ln in r["stderr_last"] + r["stdout_tail"])
    ok = (r["rc"] == expect_rc) and msg_ok
    rec = {"tool": tool, "case": name, "control_role": role, "cmd": " ".join(cmd), "expect_rc": expect_rc, "rc": r["rc"], "expect_msg": expect_msg,
           "msg_seen": msg_ok, "stdout_tail": r["stdout_tail"], "stderr_last": r["stderr_last"], "seconds": r["seconds"], "result": "PASS" if ok else "FAIL", "note": note}
    if counts_from:
        rec["counts"] = counts_from(r)
    CASES.append(rec)
    print(f"[{rec['result']}] {tool} :: {name} rc={r['rc']} (expect {expect_rc}) {r['stderr_last'][-1][:110] if r['stderr_last'] else ''}", flush=True)
    return rec


def fn_case(tool: str, name: str, role: str, fn, expect_desc: str, note: str = ""):
    """In-process control: fn() returns (ok: bool, observed: str)."""
    try:
        ok, observed = fn()
    except Exception as e:  # noqa: BLE001
        ok, observed = False, f"RAISED {type(e).__name__}: {e}"
    rec = {"tool": tool, "case": name, "control_role": role, "cmd": "(in-process)", "expect": expect_desc, "observed": str(observed)[:400], "result": "PASS" if ok else "FAIL", "note": note}
    CASES.append(rec)
    print(f"[{rec['result']}] {tool} :: {name} -> {str(observed)[:110]}", flush=True)
    return rec


def mutate_copy(src: pathlib.Path, dst: pathlib.Path, old: str, new: str) -> pathlib.Path:
    s = src.read_text(encoding="utf-8")
    assert s.count(old) == 1, f"anchor x{s.count(old)} in {src}: {old[:60]!r}"
    dst.write_text(s.replace(old, new), encoding="utf-8")
    return dst


def inject_crash_after_def_main(src: pathlib.Path, dst: pathlib.Path) -> pathlib.Path:
    lines = src.read_text(encoding="utf-8").splitlines(keepends=True)
    i = next(k for k, ln in enumerate(lines) if ln.startswith("def main("))
    j = i + 1
    # skip a docstring line block if present
    if lines[j].lstrip().startswith(('"""', "'''")):
        q = lines[j].lstrip()[:3]
        if lines[j].rstrip().endswith(q) and len(lines[j].strip()) > 3:
            j += 1
        else:
            j += 1
            while not lines[j].rstrip().endswith(q):
                j += 1
            j += 1
    lines.insert(j, '    raise RuntimeError("injected crash (exit_semantics_demo_c)")\n')
    dst.write_text("".join(lines), encoding="utf-8")
    return dst


def copy_lane(rel_dir: str) -> pathlib.Path:
    dst = SP / "copies" / rel_dir.replace("/", "_")
    shutil.rmtree(dst, ignore_errors=True)
    shutil.copytree(A / rel_dir, dst, ignore=shutil.ignore_patterns("__pycache__", "out", "_out"))
    return dst


TEMP_SIBLINGS: list[pathlib.Path] = []


def sibling(rel: str, suffix: str = "crash") -> pathlib.Path:
    src = A / rel
    dst = src.parent / f"_esd_{src.stem}_{suffix}.py"
    TEMP_SIBLINGS.append(dst)
    return dst


# ---------------------------------------------------------------- inventory / denominator
def inventory() -> dict:
    files = sorted(p for p in A.rglob("*") if p.is_file() and p.suffix in (".py", ".sh") and "__pycache__" not in p.parts)
    ep = {rel for rel, *_ in ENTRY_POINTS}
    rows, cats = [], {"entry_point": 0, "excluded_by_owner": 0, "library": 0, "fixtures_py": 0, "test_module": 0, "package_init": 0, "shell_entry": 0, "demonstrator": 0}
    for p in files:
        rel = p.relative_to(A).as_posix()
        if rel in EXCLUDED_BY_OWNER:
            cat = "excluded_by_owner"
        elif rel in ep:
            cat = "entry_point"
        elif rel == "gate1/exit_semantics_demo_c.py":
            cat = "demonstrator"
        elif p.suffix == ".sh":
            cat = "shell_entry"
        elif "fixtures_py" in rel:
            cat = "fixtures_py"
        elif p.name.startswith("test_"):
            cat = "test_module"
        elif p.name == "__init__.py":
            cat = "package_init"
        else:
            cat = "library"
        cats[cat] += 1
        rows.append({"path": rel, "category": cat, "sha256_now": sha(p), "sha256_head": git_head_sha(rel), "excluded_reason": EXCLUDED_BY_OWNER.get(rel)})
    return {"rule": "every *.py and *.sh under research/landing_accessibility/assurance/ (recursive, __pycache__ excluded); 전수 = 전수 of N files", "n_files": len(files), "by_category": cats, "files": rows}


# ---------------------------------------------------------------- AST sweeps (HEAD = before, worktree = after)
SWEEP_EXCL = set(EXCLUDED_BY_OWNER) | {"gate1/exit_semantics_demo_c.py"}
SAFE_STR = {"", "OK", "CLEAN", "NO_FIELD", "PASS", "NONE", "N/A", "UNKNOWN", "MATCH", "-", "VERIFIED", "SAFE", "COMPLETE"}


def _benign(node):
    if isinstance(node, ast.Constant):
        v = node.value
        if v is None: return "None"
        if v is False: return "False"
        if isinstance(v, (int, float)) and not isinstance(v, bool) and v == 0: return "0"
        if isinstance(v, str) and (v == "" or v.upper() in SAFE_STR): return repr(v)
        return None
    if isinstance(node, (ast.List, ast.Tuple)) and not node.elts: return "[]"
    if isinstance(node, ast.Dict) and not node.keys: return "{}"
    return None


def _sources(head: bool) -> list[tuple[str, str]]:
    out = []
    for p in sorted(A.rglob("*.py")):
        rel = p.relative_to(A).as_posix()
        if "__pycache__" in p.parts or rel in SWEEP_EXCL or "/out/" in f"/{rel}" or "/_out/" in f"/{rel}":
            continue
        if head:
            r = subprocess.run(["git", "-C", str(A), "show", f"HEAD:research/landing_accessibility/assurance/{rel}"], capture_output=True, text=True)
            if r.returncode != 0:
                continue
            out.append((rel, r.stdout))
        else:
            out.append((rel, p.read_text(encoding="utf-8")))
    return out


def except_sweep(head: bool) -> dict:
    total, safe = 0, 0
    for rel, src in _sources(head):
        try:
            tree = ast.parse(src)
        except SyntaxError:
            continue
        for n in ast.walk(tree):
            if isinstance(n, ast.ExceptHandler):
                total += 1
                sv = False
                for m in ast.walk(n):
                    if isinstance(m, ast.Return) and (m.value is None or _benign(m.value)): sv = True
                    if isinstance(m, ast.Assign) and _benign(m.value): sv = True
                if (len(n.body) == 1 and isinstance(n.body[0], (ast.Pass, ast.Continue))): sv = True
                safe += sv
    return {"handlers_total": total, "safe_looking": safe}


def benign_sweep(head: bool) -> dict:
    from collections import Counter
    c = Counter()
    for rel, src in _sources(head):
        try:
            tree = ast.parse(src)
        except SyntaxError:
            continue
        for n in ast.walk(tree):
            if isinstance(n, ast.If) and any(isinstance(m, ast.Call) and isinstance(m.func, ast.Attribute) and m.func.attr in ("exists", "is_file", "is_dir") for m in ast.walk(n.test)):
                if any(isinstance(b, (ast.Return, ast.Continue)) or (isinstance(b, ast.Assign) and _benign(b.value)) for b in n.body):
                    c["exists_guard"] += 1
            elif isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr == "get" and len(n.args) == 2 and _benign(n.args[1]) not in (None, "None"):
                c["get_default"] += 1
            elif isinstance(n, ast.BoolOp) and isinstance(n.op, ast.Or) and _benign(n.values[-1]) not in (None, "None"):
                c["or_default"] += 1
    return {"exists_guard": c["exists_guard"], "get_default": c["get_default"], "or_default": c["or_default"], "total": sum(c.values())}


# ---------------------------------------------------------------- the proofs
def proofs() -> None:
    SP.mkdir(parents=True, exist_ok=True)
    missing = str(SP / "does_not_exist")
    empty = SP / "empty_dir"; empty.mkdir(exist_ok=True)

    # --- bus.py
    case("bus.py", "ack_missing_ticket", "must_flag", [PY, str(A / "bus.py"), "ack", "no_such_ticket.json", "x"], 2, f"bus: {DNR}")
    case("bus.py", "no_argv", "must_flag", [PY, str(A / "bus.py")], 2, f"bus: {DNR}")
    case("bus.py", "selftest", "must_not_flag", [PY, str(A / "bus.py"), "selftest"], 0, None, counts_from=lambda r: r["stdout_tail"][-1:])

    # --- clean0/qa_retention.py (hard-coded A/B paths → mutated copy pointing at a missing manifest)
    d = copy_lane("clean0")
    mutate_copy(A / "clean0/qa_retention.py", d / "qa_retention.py",
                'A_MANIFEST = pathlib.Path("', f'A_MANIFEST = pathlib.Path("{missing}/')
    case("clean0/qa_retention.py", "missing_A_manifest(mutated copy)", "must_flag", [PY, str(d / "qa_retention.py")], 2, f"qa_retention: {DNR}")
    CASES.append({"tool": "clean0/qa_retention.py", "case": "normal", "control_role": "must_not_flag", "result": "NOT_EXERCISED", "note": "reads A/B worktrees (other planes) — not run by this worker"})

    # --- gate1/c_terminal_table.py
    case("gate1/c_terminal_table.py", "selftest", "must_not_flag", [PY, str(A / "gate1/c_terminal_table.py")], 0, None, counts_from=lambda r: r["stdout_tail"][-1:])
    s = sibling("gate1/c_terminal_table.py")
    mutate_copy(A / "gate1/c_terminal_table.py", s, "        probs = selftest()\n", '        raise RuntimeError("injected crash (exit_semantics_demo_c)")\n')
    case("gate1/c_terminal_table.py", "injected_crash(temp sibling)", "must_flag", [PY, str(s)], 2, f"c_terminal_table: {DNR}")

    # --- comparators
    case("gate1/comparators/adapter_map.py", "show_missing_map", "must_flag", [PY, str(A / "gate1/comparators/adapter_map.py"), "--show", missing], 2, f"adapter_map: {DNR}")
    case("gate1/comparators/adapter_map.py", "write_default", "must_not_flag", [PY, str(A / "gate1/comparators/adapter_map.py"), "--write-default", str(SP / "map.json")], 0, None, counts_from=lambda r: r["stdout_tail"][-1:])
    for ln in ("compare_lane1", "compare_lane2", "compare_lane3", "grade_lane4"):
        t = f"gate1/comparators/{ln}.py"
        case(t, "missing_adapter_map", "must_flag", [PY, str(A / t), "--adapter-map", missing], 2, f"{ln}: {DNR}")
        case(t, "no_map_nothing_compared→NOT_TESTABLE", "must_flag", [PY, str(A / t)], 2, f"{ln}: {DNR}", note="was exit 1 (read as 'ran and failed')")
        CASES.append({"tool": t, "case": "exit0_PASS_path", "control_role": "must_not_flag", "result": "NOT_EXERCISED", "note": "CLI exit 0 needs B runner output at the joint SHA; in-process PASS on synthetic output is proven by comparators/selftest.py (exit 0 below)"})
    case("gate1/comparators/selftest.py", "selftest", "must_not_flag", [PY, str(A / "gate1/comparators/selftest.py")], 0, "SELFTEST OK", counts_from=lambda r: r["stdout_tail"][-1:])
    s = sibling("gate1/comparators/selftest.py")
    inject_crash_after_def_main(A / "gate1/comparators/selftest.py", s)
    case("gate1/comparators/selftest.py", "injected_crash(temp sibling)", "must_flag", [PY, str(s)], 2, f"comparators/selftest: {DNR}")

    # --- intake r32_selftest
    s = sibling("gate1/intake/r32_selftest.py")
    inject_crash_after_def_main(A / "gate1/intake/r32_selftest.py", s)
    case("gate1/intake/r32_selftest.py", "injected_crash(temp sibling)", "must_flag", [PY, str(s)], 2, f"r32_selftest: {DNR}")
    case("gate1/intake/r32_selftest.py", "selftest", "must_not_flag", [PY, str(A / "gate1/intake/r32_selftest.py")], 0, "ALL PASS", counts_from=lambda r: r["stderr_last"][-1:], timeout=1200)

    # --- lane1 selfcheck
    case("gate1/lane1_task_binding/selfcheck.py", "selfcheck", "must_not_flag", [PY, str(A / "gate1/lane1_task_binding/selfcheck.py")], 0, "SELFCHECK PASS", counts_from=lambda r: r["stdout_tail"][-1:])
    d = copy_lane("gate1/lane1_task_binding"); (d / "task_contracts.json").unlink()
    case("gate1/lane1_task_binding/selfcheck.py", "missing_task_contracts(lane copy)", "must_flag", [PY, str(d / "selfcheck.py")], 2, f"selfcheck: {DNR}")

    # --- lane2 measure_geometry (browser)
    case("gate1/lane2_label_reveal/measure_geometry.py", "fixtures", "must_not_flag", [PY, str(A / "gate1/lane2_label_reveal/measure_geometry.py")], 0, "RESULT:", counts_from=lambda r: [l for l in r["stdout_tail"] if l.startswith("RESULT")][-1:])
    d = copy_lane("gate1/lane2_label_reveal"); (d / "EXPECTATIONS.json").unlink()
    case("gate1/lane2_label_reveal/measure_geometry.py", "missing_EXPECTATIONS(lane copy)", "must_flag", [PY, str(d / "measure_geometry.py")], 2, f"measure_geometry: {DNR}")
    d = copy_lane("gate1/lane2_label_reveal"); e = json.loads((d / "EXPECTATIONS.json").read_text(encoding="utf-8")); e["fixtures"] = []; (d / "EXPECTATIONS.json").write_text(json.dumps(e), encoding="utf-8")
    case("gate1/lane2_label_reveal/measure_geometry.py", "zero_fixtures→not PASS (lane copy)", "must_flag", [PY, str(d / "measure_geometry.py")], 2, f"measure_geometry: {DNR}", note="R43 vacuous-pass fix: was exit 0 '0/0 PASS'")

    # --- lane3 walk_fixture (browser)
    case("gate1/lane3_sequence_dismiss_auth/walk_fixture.py", "fixtures", "must_not_flag", [PY, str(A / "gate1/lane3_sequence_dismiss_auth/walk_fixture.py")], 0, "RESULT: ALL PASS", counts_from=lambda r: [l for l in r["stdout_tail"] if l.startswith("RESULT")][-1:])
    d = copy_lane("gate1/lane3_sequence_dismiss_auth"); (d / "EXPECTATIONS.json").unlink()
    case("gate1/lane3_sequence_dismiss_auth/walk_fixture.py", "missing_EXPECTATIONS(lane copy)", "must_flag", [PY, str(d / "walk_fixture.py")], 2, f"walk_fixture: {DNR}")
    d = copy_lane("gate1/lane3_sequence_dismiss_auth"); e = json.loads((d / "EXPECTATIONS.json").read_text(encoding="utf-8")); e["fixtures"] = {}; e["conditional_pairs"] = []; (d / "EXPECTATIONS.json").write_text(json.dumps(e), encoding="utf-8")
    case("gate1/lane3_sequence_dismiss_auth/walk_fixture.py", "zero_fixtures→not ALL PASS (lane copy)", "must_flag", [PY, str(d / "walk_fixture.py")], 2, f"walk_fixture: {DNR}", note="R43: was exit 0 'ALL PASS (0/0)'")

    # --- lane4 adapter stub
    case("gate1/lane4_safety_adapter/adapter_interface_stub.py", "dry_run", "must_not_flag", [PY, str(A / "gate1/lane4_safety_adapter/adapter_interface_stub.py"), "--dry-run", "--out", str(SP / "stub_out")], 0, None, counts_from=lambda r: r["stdout_tail"][-1:])
    s = sibling("gate1/lane4_safety_adapter/adapter_interface_stub.py")
    inject_crash_after_def_main(A / "gate1/lane4_safety_adapter/adapter_interface_stub.py", s)
    case("gate1/lane4_safety_adapter/adapter_interface_stub.py", "injected_crash(temp sibling)", "must_flag", [PY, str(s), "--dry-run", "--out", str(SP / "stub_out2")], 2, f"adapter_interface_stub: {DNR}")

    # --- lane5
    case("gate1/lane5_evidence/make_synthetic_evidence.py", "regen", "must_not_flag", [PY, str(A / "gate1/lane5_evidence/make_synthetic_evidence.py")], 0, None, counts_from=lambda r: r["stdout_tail"][-1:])
    s = sibling("gate1/lane5_evidence/make_synthetic_evidence.py")
    inject_crash_after_def_main(A / "gate1/lane5_evidence/make_synthetic_evidence.py", s)
    case("gate1/lane5_evidence/make_synthetic_evidence.py", "injected_crash(temp sibling)", "must_flag", [PY, str(s)], 2, f"make_synthetic_evidence: {DNR}")
    chk = A / "gate1/lane5_evidence/evidence_lineage_check.py"; fx = A / "gate1/lane5_evidence/fixtures"
    for name, rc in (("good", 0), ("bad_overwrite", 2), ("bad_lineage", 2)):
        case("gate1/lane5_evidence/evidence_lineage_check.py", f"fixture_{name}", "must_not_flag", [PY, str(chk), str(fx / name), "--path-manifest", str(fx / name / "path_manifest.json"), "--quiet", "--out", str(SP / f"elc_{name}.json")], rc, None,
             note="unchanged numbering (0 / 2 systemic)", counts_from=lambda r, n=name: [json.loads((SP / f"elc_{n}.json").read_text()).get("verdict"), json.loads((SP / f"elc_{n}.json").read_text()).get("checks_performed")])
    case("gate1/lane5_evidence/evidence_lineage_check.py", "empty_root→NO_EVIDENCE_INPUT", "must_flag", [PY, str(chk), str(empty), "--quiet", "--out", str(SP / "elc_empty.json")], 3, f"evidence_lineage_check: {DNR}",
         note="R43 hit (C body): was exit 0 COMPLETE_WITH_ISOLATED_DEFECTS; now verdict NO_EVIDENCE_INPUT checks_performed=0 exit 3 (tool-local did-not-run; 2 is bound by run_gate1 L5 expect_rc)",
         counts_from=lambda r: [json.loads((SP / "elc_empty.json").read_text()).get("verdict"), json.loads((SP / "elc_empty.json").read_text()).get("checks_performed")])
    case("gate1/lane5_evidence/evidence_lineage_check.py", "missing_root(usage)", "must_flag", [PY, str(chk), missing, "--quiet"], 3, "root is not a directory")
    s = sibling("gate1/lane5_evidence/evidence_lineage_check.py")
    inject_crash_after_def_main(chk, s)
    case("gate1/lane5_evidence/evidence_lineage_check.py", "injected_crash(temp sibling)", "must_flag", [PY, str(s), str(fx / "good"), "--quiet"], 3, f"evidence_lineage_check: {DNR}", note="was exit 1 (uncaught); 3 = this tool's did-not-run code")

    # --- lane6
    case("gate1/lane6_stats/synthetic_family_demo.py", "demo", "must_not_flag", [PY, str(A / "gate1/lane6_stats/synthetic_family_demo.py")], 0, None, counts_from=lambda r: r["stdout_tail"][-1:])
    s = sibling("gate1/lane6_stats/synthetic_family_demo.py")
    inject_crash_after_def_main(A / "gate1/lane6_stats/synthetic_family_demo.py", s)
    case("gate1/lane6_stats/synthetic_family_demo.py", "injected_crash(temp sibling)", "must_flag", [PY, str(s)], 2, f"synthetic_family_demo: {DNR}")
    s = sibling("gate1/lane6_stats/synthetic_family_demo.py", "q8")
    mutate_copy(A / "gate1/lane6_stats/synthetic_family_demo.py", s, '    C.assert_field_qualified(out, "demo_output")', '    raise ValueError("T-A-V3-STEP1-003 R6 Q8 field qualification violated: injected (exit_semantics_demo_c)")')
    case("gate1/lane6_stats/synthetic_family_demo.py", "injected_R6Q8_rejection→ran_and_failed", "must_flag", [PY, str(s)], 1, "FAIL (ran)", note="ran-and-failed stays exit 1, distinct from crash")
    case("gate1/lane6_stats/variance_control.py", "controls", "must_not_flag", [PY, str(A / "gate1/lane6_stats/variance_control.py")], 0, None)
    s = sibling("gate1/lane6_stats/variance_control.py")
    mutate_copy(A / "gate1/lane6_stats/variance_control.py", s, "        res = run_controls()\n", '        raise RuntimeError("injected crash (exit_semantics_demo_c)")\n')
    case("gate1/lane6_stats/variance_control.py", "injected_crash(temp sibling)", "must_flag", [PY, str(s)], 2, f"variance_control: {DNR}")

    # --- lane7
    L7 = A / "gate1/lane7_grain_determinism"; f01 = L7 / "fixtures" / "f01_blocking_modal_visible_close.html"; f04 = L7 / "fixtures" / "f04_two_overlays_one_blocking.html"
    case("gate1/lane7_grain_determinism/converge_check.py", "converge", "must_not_flag", [PY, str(L7 / "converge_check.py")], 0, "PASS", counts_from=lambda r: [l for l in r["stdout_tail"] if l.startswith("mode=")][-1:])
    case("gate1/lane7_grain_determinism/converge_check.py", "negative_control", "must_not_flag", [PY, str(L7 / "converge_check.py"), "--negative-control"], 0, None, counts_from=lambda r: [l for l in r["stdout_tail"] if l.startswith("mode=")][-1:])
    d = copy_lane("gate1/lane7_grain_determinism"); shutil.rmtree(d / "probe_like")
    case("gate1/lane7_grain_determinism/converge_check.py", "missing_probe_like(lane copy)", "must_flag", [PY, str(d / "converge_check.py")], 2, f"converge_check: {DNR}")
    d = copy_lane("gate1/lane7_grain_determinism")
    bad = d / "fixtures" / "two_task_entries.html"; bad.write_text('<html><body><button id="a" data-c-control="task-entry">a</button><button id="b" data-c-control="task-entry">b</button></body></html>', encoding="utf-8")
    case("gate1/lane7_grain_determinism/impl_b.py", "malformed_fixture_SystemExit(str)→2", "must_flag", [PY, str(L7 / "impl_b.py"), str(bad)], 2, f"impl_b: {DNR}", note="library raise SystemExit(str) untouched; was exit 1")
    case("gate1/lane7_grain_determinism/impl_b.py", "missing_fixture", "must_flag", [PY, str(L7 / "impl_b.py"), missing], 2, f"impl_b: {DNR}")
    case("gate1/lane7_grain_determinism/impl_b.py", "f01", "must_not_flag", [PY, str(L7 / "impl_b.py"), str(f01)], 0, None, counts_from=lambda r: [f"rows={len(r['stdout_tail'])}+"])
    case("gate1/lane7_grain_determinism/impl_a.py", "missing_probe", "must_flag", [PY, str(L7 / "impl_a.py"), missing], 2, f"impl_a: {DNR}")
    case("gate1/lane7_grain_determinism/impl_a.py", "f01_probe", "must_not_flag", [PY, str(L7 / "impl_a.py"), str(L7 / "probe_like" / "f01.json")], 0, None)
    for fr in ("fake_runner_det", "fake_runner_rand"):
        case(f"gate1/lane7_grain_determinism/{fr}.py", "missing_fixture", "must_flag", [PY, str(L7 / f"{fr}.py"), missing, str(SP / "fr.json")], 2, f"{fr}: {DNR}")
        case(f"gate1/lane7_grain_determinism/{fr}.py", "f04", "must_not_flag", [PY, str(L7 / f"{fr}.py"), str(f04), str(SP / f"{fr}.json")], 0, None)
    det = L7 / "determinism_check.py"; wd = SP / "det"
    case("gate1/lane7_grain_determinism/determinism_check.py", "posctrl_det_f04", "must_not_flag", [PY, str(det), "--cmd", f"{PY} {L7 / 'fake_runner_det.py'} {{fixture}} {{out}}", "--fixture", str(f04), "--n", "3", "--label", "det_f04", "--workdir", str(wd), "--policy-doc", str(L7 / "ROUTE_POLICY_DETERMINISM_SPEC.md")], 0, "PASS")
    case("gate1/lane7_grain_determinism/determinism_check.py", "negctrl_rand_f04→ran_and_failed", "must_not_flag", [PY, str(det), "--cmd", f"{PY} {L7 / 'fake_runner_rand.py'} {{fixture}} {{out}}", "--fixture", str(f04), "--n", "3", "--label", "rand_f04", "--workdir", str(wd)], 1, "FAIL")
    case("gate1/lane7_grain_determinism/determinism_check.py", "missing_policy_doc", "must_flag", [PY, str(det), "--cmd", f"{PY} {L7 / 'fake_runner_det.py'} {{fixture}} {{out}}", "--fixture", str(f04), "--n", "1", "--label", "pd", "--workdir", str(wd), "--policy-doc", missing], 2, f"determinism_check: {DNR}")
    case("gate1/lane7_grain_determinism/determinism_check.py", "runner_missing(already 2)", "must_flag", [PY, str(det), "--cmd", f"{PY} {missing} {{fixture}} {{out}}", "--fixture", str(f04), "--n", "1", "--label", "rm", "--workdir", str(wd)], 2, "runner failed")
    case("gate1/lane7_grain_determinism/validate_probe_like_playwright.py", "probe_like_vs_browser", "must_not_flag", [PY, str(L7 / "validate_probe_like_playwright.py")], 0, "PROBE_LIKE_VALIDATED", counts_from=lambda r: r["stdout_tail"][-1:])
    d = copy_lane("gate1/lane7_grain_determinism"); shutil.rmtree(d / "probe_like")
    case("gate1/lane7_grain_determinism/validate_probe_like_playwright.py", "missing_probe_like(lane copy)", "must_flag", [PY, str(d / "validate_probe_like_playwright.py")], 2, f"validate_probe_like_playwright: {DNR}")
    d = copy_lane("gate1/lane7_grain_determinism")
    mutate_copy(L7 / "validate_probe_like_playwright.py", d / "validate_probe_like_playwright.py", "PROBE = {", "PROBE = {} and {")
    case("gate1/lane7_grain_determinism/validate_probe_like_playwright.py", "zero_checks→not VALIDATED (lane copy)", "must_flag", [PY, str(d / "validate_probe_like_playwright.py")], 2, f"validate_probe_like_playwright: {DNR}", note="R43: was exit 0 'checked=0 -> PROBE_LIKE_VALIDATED'")

    # --- run_gate1_selftest: crash proof here; the full selftest is long and is run separately (see run_gate1_selftest_full)
    s = sibling("gate1/run_gate1_selftest.py")
    inject_crash_after_def_main(A / "gate1/run_gate1_selftest.py", s)
    case("gate1/run_gate1_selftest.py", "injected_crash(temp sibling)", "must_flag", [PY, str(s), "--work", str(SP / "rgs")], 2, f"run_gate1_selftest: {DNR}")

    # --- mlflow_log (unchanged)
    case("mlflow_log.py", "print_constants", "must_not_flag", [PY, str(A / "mlflow_log.py")], 0, None, note="UNCHANGED tool")

    # --- pilot
    e001 = A / "pilot/e001_runner_unchanged_check.py"
    repo = SP / "e001_repo"; shutil.rmtree(repo, ignore_errors=True); repo.mkdir(parents=True)
    genv = {**os.environ, "GIT_AUTHOR_NAME": "c", "GIT_AUTHOR_EMAIL": "c@c", "GIT_COMMITTER_NAME": "c", "GIT_COMMITTER_EMAIL": "c@c"}
    subprocess.run(["git", "-C", str(repo), "init", "-q"], check=True, env=genv)
    for rel in ("research/landing_accessibility/scripts/run_e001_real.py", "research/landing_accessibility/src/landing_accessibility/e001_runner/batch.py", "research/landing_accessibility/src/landing_accessibility/e001_runner/layer_firewall.py"):
        (repo / rel).parent.mkdir(parents=True, exist_ok=True); (repo / rel).write_text("x = 1\n")
    subprocess.run(["git", "-C", str(repo), "add", "-A"], check=True, env=genv); subprocess.run(["git", "-C", str(repo), "commit", "-qm", "a"], check=True, env=genv)
    c1 = subprocess.check_output(["git", "-C", str(repo), "rev-parse", "HEAD"], text=True).strip()
    (repo / "README").write_text("r\n"); subprocess.run(["git", "-C", str(repo), "add", "-A"], check=True, env=genv); subprocess.run(["git", "-C", str(repo), "commit", "-qm", "b"], check=True, env=genv)
    c2 = subprocess.check_output(["git", "-C", str(repo), "rev-parse", "HEAD"], text=True).strip()
    (repo / "research/landing_accessibility/scripts/run_e001_real.py").write_text("x = 2\n"); subprocess.run(["git", "-C", str(repo), "add", "-A"], check=True, env=genv); subprocess.run(["git", "-C", str(repo), "commit", "-qm", "c"], check=True, env=genv)
    c3 = subprocess.check_output(["git", "-C", str(repo), "rev-parse", "HEAD"], text=True).strip()
    case("pilot/e001_runner_unchanged_check.py", "unchanged(scratch repo)", "must_not_flag", [PY, str(e001), str(repo), c1, c2], 0, None)
    case("pilot/e001_runner_unchanged_check.py", "changed→ran_and_failed(scratch repo)", "must_not_flag", [PY, str(e001), str(repo), c1, c3], 1, None)
    case("pilot/e001_runner_unchanged_check.py", "unresolvable_sha", "must_flag", [PY, str(e001), str(repo), "0" * 40, c2], 2, f"{DNR}", note="was exit 1 = 'changed'")
    case("pilot/e001_runner_unchanged_check.py", "missing_repo", "must_flag", [PY, str(e001), missing, c1, c2], 2, f"{DNR}")
    case("pilot/e001_runner_unchanged_check.py", "no_baseline_blobs(C worktree lacks runner files)", "must_flag", [PY, str(e001), str(A.parents[2]), "HEAD", "HEAD"], 2, "reference blobs resolve", note="was exit 1 = 'changed'")
    case("pilot/e001_runner_unchanged_check.py", "missing_argv", "must_flag", [PY, str(e001)], 2, f"{DNR}")
    case("pilot/scope_threeway_test.py", "missing_sut", "must_flag", [PY, str(A / "pilot/scope_threeway_test.py"), missing, str(SP / "s3.json")], 2, f"scope_threeway_test: {DNR}")
    CASES.append({"tool": "pilot/scope_threeway_test.py", "case": "normal", "control_role": "must_not_flag", "result": "NOT_EXERCISED", "note": "needs a SUT clone with the V2 firewall"})
    s = sibling("pilot/preflight_sampling.py")
    mutate_copy(A / "pilot/preflight_sampling.py", s, 'FRAME_SHA = "', 'FRAME_SHA = "0000000000')
    case("pilot/preflight_sampling.py", "bad_git_object(temp sibling)", "must_flag", [PY, str(s)], 2, f"preflight_sampling: {DNR}", note="module-level script: whole body wrapped")
    CASES.append({"tool": "pilot/preflight_sampling.py", "case": "normal", "control_role": "must_not_flag", "result": "NOT_EXERCISED", "note": "reads B mart / evidence dom.html (other plane)"})

    # --- qa_*
    case("qa_base.py", "missing_ticket", "must_flag", [PY, str(A / "qa_base.py"), missing], 2, f"qa_base: {DNR}")
    CASES.append({"tool": "qa_base.py", "case": "normal", "control_role": "must_not_flag", "result": "NOT_EXERCISED", "note": "needs a real E001 release ticket (network git fetch); WALL_CLOCK injection below is in-process"})
    case("qa_claim.py", "missing_claims_file→SCAN_INVALID(already 2)", "must_flag", [PY, str(A / "qa_claim.py"), "--claims", missing, "--out", str(SP / "claim.md")], 2, "qa_claim: scan INVALID")
    shutil.rmtree(SP / "does_not_exist_out", ignore_errors=True)
    case("qa_claim.py", "unwritable_out", "must_flag", [PY, str(A / "qa_claim.py"), "--claims", str(A / "gate1/GATE1_RUNBOOK_C.md"), "--out", str(SP / "does_not_exist_out" / "x" / "claim.md")], 2, DNR, note="either crash (wrapper) or SCAN_INVALID — both are the did-not-run class with the message")
    case("qa_claim.py", "scan_one_C_doc_without_positive_control→SCAN_INVALID", "must_flag", [PY, str(A / "qa_claim.py"), "--claims", str(A / "gate1/GATE1_RUNBOOK_C.md"), "--out", str(SP / "claim2.md")], 2, "scan INVALID", note="a single doc carries no positive control → scan_ok False → designed did-not-run (exit 2); exit 0 needs the full claims set + controls")
    CASES.append({"tool": "qa_claim.py", "case": "normal(exit 0)", "control_role": "must_not_flag", "result": "NOT_EXERCISED", "note": "needs A's claim documents + C positive-control files at their recorded paths"})
    case("qa_evidence.py", "missing_plan", "must_flag", [PY, str(A / "qa_evidence.py"), "--out-dir", str(empty), "--plan", missing], 2, f"qa_evidence: {DNR}")
    eo = SP / "qe_empty"; (eo / "batches").mkdir(parents=True, exist_ok=True); plan = SP / "plan.json"; plan.write_text('{"targets": []}')
    case("qa_evidence.py", "zero_batches→NO_INPUT", "must_flag", [PY, str(A / "qa_evidence.py"), "--out-dir", str(eo), "--plan", str(plan)], 2, f"qa_evidence: {DNR}", note="R43: was exit 0 verdict MATCH with n_batches 0")
    CASES.append({"tool": "qa_evidence.py", "case": "normal", "control_role": "must_not_flag", "result": "NOT_EXERCISED", "note": "needs a B out_dir with sealed batches + evidence; synthetic single-batch injections below exercise the judging paths"})
    case("qa_mart.py", "missing_out_dirs→no_raw_rows", "must_flag", [PY, str(A / "qa_mart.py"), "--out-dirs", missing, "--mart-dir", missing, "--plan", missing, "--out", str(SP / "qm")], 2, f"qa_mart: {DNR}", note="was exit 0 'no raw rows'")
    CASES.append({"tool": "qa_mart.py", "case": "normal", "control_role": "must_not_flag", "result": "NOT_EXERCISED", "note": "needs B mart + out_dirs"})
    CASES.append({"tool": "stream_qa.py", "case": "normal/crash", "control_role": "must_not_flag", "result": "NOT_EXERCISED", "note": "daemon; discover() scans other planes' out_dirs by design; wrapper is the same pattern as qa_evidence (py_compile OK)"})
    case("stats_replay.py", "selftest", "must_not_flag", [PY, str(A / "stats_replay.py")], 0, "self-test OK", counts_from=lambda r: r["stdout_tail"][:1])
    s = sibling("stats_replay.py")
    mutate_copy(A / "stats_replay.py", s, "    rng = np.random.default_rng(1)\n", '    raise RuntimeError("injected crash (exit_semantics_demo_c)")\n')
    case("stats_replay.py", "injected_crash(temp sibling)", "must_flag", [PY, str(s)], 2, f"stats_replay: {DNR}")
    s = sibling("stats_replay.py", "assert")
    mutate_copy(A / "stats_replay.py", s, '    assert r["rho_matches_scipy"], r\n', '    assert False, "injected self-test failure (exit_semantics_demo_c)"\n')
    case("stats_replay.py", "injected_assert→ran_and_failed", "must_flag", [PY, str(s)], 1, "self-test FAIL (ran)")
    CASES.append({"tool": "recovery/fixtures/run_partial_depth_fixtures.py", "case": "normal/crash", "control_role": "must_not_flag", "result": "NOT_EXERCISED", "note": "imports the B worker engine at module level (other plane); _check() vacuous control is in-process below"})

    # --- w1 / w2
    case("w1/dup_launch_harness.py", "missing_sut_script", "must_flag", [PY, str(A / "w1/dup_launch_harness.py"), missing, str(SP / "dl")], 2, f"{DNR}", note="was exit 0 INCONCLUSIVE")
    CASES.append({"tool": "w1/dup_launch_harness.py", "case": "normal", "control_role": "must_not_flag", "result": "NOT_EXERCISED", "note": "needs B's run_e001_batch_dryrun.py"})
    case("w1/lock_race_harness.py", "missing_sut_src", "must_flag", [PY, str(A / "w1/lock_race_harness.py"), missing, str(SP / "lr")], 2, f"{DNR}", note="was exit 1 (worker errors → exactly_once_holds=false) and even that was discarded (always 0)")
    CASES.append({"tool": "w1/lock_race_harness.py", "case": "normal", "control_role": "must_not_flag", "result": "NOT_EXERCISED", "note": "needs B's TargetLock"})
    case("w2/dom_replay_probe.py", "missing_probe_js", "must_flag", [PY, str(A / "w2/dom_replay_probe.py"), missing, str(SP / "dr")], 2, f"dom_replay_probe: {DNR}")
    CASES.append({"tool": "w2/dom_replay_probe.py", "case": "normal", "control_role": "must_not_flag", "result": "NOT_EXERCISED", "note": "needs B mart + evidence dom.html"})
    case("w2/holdout_scorer.py", "usage", "must_flag", [PY, str(A / "w2/holdout_scorer.py")], 2, "usage error")
    case("w2/holdout_scorer.py", "missing_labels", "must_flag", [PY, str(A / "w2/holdout_scorer.py"), missing, missing, missing, str(SP / "ho.json")], 2, f"holdout_scorer: {DNR}")
    lab = SP / "labels.jsonl"; lab.write_text('{"observation_id": "o1", "archetype_label": "QUERY", "region_present": true}\n', encoding="utf-8")
    split = SP / "split.json"; split.write_text(json.dumps({"label_sha256": hashlib.sha256(lab.read_bytes()).hexdigest(), "holdout": ["o1"], "calibration": []}), encoding="utf-8")
    detp = SP / "det.jsonl"; detp.write_text('{"observation_id": "o1", "archetype_pred": "QUERY", "region_detected": true}\n', encoding="utf-8")
    case("w2/holdout_scorer.py", "synthetic_1_row", "must_not_flag", [PY, str(A / "w2/holdout_scorer.py"), str(lab), str(split), str(detp), str(SP / "ho2.json")], 0, None, counts_from=lambda r: [json.loads((SP / "ho2.json").read_text()).get("holdout_n"), json.loads((SP / "ho2.json").read_text()).get("evaluated_n")])


def injection_controls() -> None:
    """D-V3-FINDING-023 / ADDENDUM-006 / R43 in-process controls: corrupt → sentinel appears; restore → normal."""
    sys.path.insert(0, str(A)); sys.path.insert(0, str(A.parent)); sys.path.insert(0, str(A / "gate1/comparators")); sys.path.insert(0, str(A / "gate1"))
    import qa_evidence as QE  # noqa: E402
    import qa_mart as QM  # noqa: E402
    import compare_lane2  # noqa: E402
    import grade_lane4  # noqa: E402
    import selftest as CS  # noqa: E402
    from adapter_map import AdapterMap  # noqa: E402

    # qa_evidence: FORBIDDEN_LABEL_SCAN_UNREADABLE (a directory named *.json is unreadable as a file, root-proof)
    out = SP / "qe_unreadable"; shutil.rmtree(out, ignore_errors=True); (out / "batches").mkdir(parents=True); (out / "corrupt.json").mkdir()
    plan = SP / "plan.json"; plan.write_text('{"targets": []}')
    def _codes(o):
        return sorted({x["code"] for x in QE.run_qa(str(o), str(plan), None, "T", None)["findings"]})
    fn_case("qa_evidence.py", "except_sweep:FORBIDDEN_LABEL_SCAN_UNREADABLE (dir named corrupt.json)", "must_flag", lambda: ("FORBIDDEN_LABEL_SCAN_UNREADABLE" in _codes(out), _codes(out)), "finding present", "was: except Exception: pass (unreadable == clean)")
    (out / "corrupt.json").rmdir()
    fn_case("qa_evidence.py", "except_sweep:FORBIDDEN_LABEL_SCAN_UNREADABLE restored", "must_not_flag", lambda: ("FORBIDDEN_LABEL_SCAN_UNREADABLE" not in _codes(out), _codes(out)), "finding absent")

    # qa_evidence: single synthetic batch → COLLECTION_STARTED_AT_UNPARSEABLE / STEPS_ABSENT / BATCH_COMMITTED_AT_MISSING / NO_INPUT
    def batch(cs, steps, committed):
        det = {"l0": {"observation_id": "o1", "evidence_run_id": "r1", "collection_started_at": cs, "requested_url": "u", "protocol_version": "v", "web_target_id": "t1", "measurement_status": "MEASURED"},
               "task_manifest": {"endpoint_status": "AUTH_GATE_REACHED", **({"steps": steps} if steps is not None else {})}}
        m = {"batch_index": 0, "batch_id": "b0", "execution_mode": "FIXTURE", "target_ids": ["t1"], "previous_batch_hash": None,
             "results": [{"target_id": "t1", "outcome": "MEASURED", "attempts": 1, "detail": det}]}
        if committed: m["committed_at"] = "2026-08-27T10:00:00+09:00"
        m["batch_hash"] = hashlib.sha256(QE.canon(m)).hexdigest()
        return m
    def _run(cs, steps, committed):
        o = SP / "qe_batch"; shutil.rmtree(o, ignore_errors=True); (o / "batches").mkdir(parents=True)
        (o / "batches" / "batch_0000.json").write_text(json.dumps(batch(cs, steps, committed)), encoding="utf-8")
        rep = QE.run_qa(str(o), str(plan), None, "T", None)
        return rep["verdict"], rep["checks_performed"], sorted({x["code"] for x in rep["findings"]})
    fn_case("qa_evidence.py", "except_sweep:COLLECTION_STARTED_AT_UNPARSEABLE + benign:STEPS_ABSENT + benign:BATCH_COMMITTED_AT_MISSING (corrupt)", "must_flag",
            lambda: (lambda v, n, c: (all(k in c for k in ("COLLECTION_STARTED_AT_UNPARSEABLE", "STEPS_ABSENT", "BATCH_COMMITTED_AT_MISSING")), (v, n, c)))(*_run("not-a-time", None, False)), "3 sentinels present")
    fn_case("qa_evidence.py", "same batch restored (ISO time, steps=[], committed_at)", "must_not_flag",
            lambda: (lambda v, n, c: (not any(k in c for k in ("COLLECTION_STARTED_AT_UNPARSEABLE", "STEPS_ABSENT", "BATCH_COMMITTED_AT_MISSING")) and n == 2, (v, n, c)))(*_run("2026-08-27T10:00:00+09:00", [], True)), "sentinels absent, checks_performed=2")
    fn_case("qa_evidence.py", "vacuous:run_qa(zero batches)→NO_INPUT checks_performed=0", "must_flag",
            lambda: (lambda rep: (rep["verdict"] == "NO_INPUT" and rep["checks_performed"] == 0, (rep["verdict"], rep["checks_performed"])))(QE.run_qa(str(SP / "qe_empty"), str(plan), None, "T", None)), "NO_INPUT / 0", "was verdict MATCH")
    fn_case("qa_evidence.py", "vacuous:check_plan_order([]) carries checks_performed=0", "must_flag",
            lambda: (lambda r: (r.get("checks_performed") == 0, r))(QE.check_plan_order([], {}, None, QE.F(), "L")), "checks_performed: 0")

    # qa_mart: _num coercion log
    QM.COERCION_LOG.clear()
    fn_case("qa_mart.py", "except_sweep:_num('abc') logs UNREADABLE (not silently missing)", "must_flag", lambda: (QM._num("abc") is None and QM.COERCION_LOG == ["'abc'"], (QM._num("abc"), list(QM.COERCION_LOG))), "None + COERCION_LOG ['abc']")
    QM.COERCION_LOG.clear()
    fn_case("qa_mart.py", "_num('1.5') / _num('') / _num(None) do not log", "must_not_flag", lambda: (QM._num("1.5") == 1.5 and QM._num("") is None and QM._num(None) is None and QM.COERCION_LOG == [], (QM._num("1.5"), list(QM.COERCION_LOG))), "1.5, no log")
    CASES.append({"tool": "qa_mart.py", "case": "except_sweep:MART_FILE_UNPARSEABLE", "control_role": "must_flag", "result": "NOT_EXERCISED", "note": "code path sits inside main() after build_c_table (needs B mart + out_dirs); finding added at the former `except Exception: pass` site"})

    # compare_lane2: UNREADABLE_BBOX
    amap = AdapterMap.from_dict(CS.SELFTEST_MAP, source="selftest")
    o = CS.lane2_output(); d = CS.write(SP / "cl2_clean" / "drawer_left", o)
    def geom(dd):
        res = compare_lane2.compare_all({"drawer_left": dd}, amap)
        it = [i for i in res["items"] if i["fixture"] == "drawer_left" and i["check"] == "reveal_direction_geom"]
        return (it[0]["status"], it[0].get("reason")) if it else (None, None)
    fn_case("gate1/comparators/compare_lane2.py", "reveal_direction_geom on clean synthetic output", "must_not_flag", lambda: (geom(d)[0] == "PASS", geom(d)), "PASS")
    ob = json.loads(json.dumps(o)); st = ob["flow.json"]["steps"]
    rev = next(s for s in st if s.get("bbox_before") is not None); rev["bbox_before"] = {"x": "garbage", "y": None, "width": "w", "height": "h"}
    db = CS.write(SP / "cl2_bad" / "drawer_left", ob)
    fn_case("gate1/comparators/compare_lane2.py", "except_sweep:bbox_before present-but-unreadable → FAIL UNREADABLE_BBOX (not 'missing')", "must_flag", lambda: (geom(db)[0] == "FAIL" and "UNREADABLE_BBOX" in (geom(db)[1] or ""), geom(db)), "FAIL UNREADABLE_BBOX", "was: bbox_center→None == absent")

    # grade_lane4: never_activate selector unbound → NOT_TESTABLE
    outs = CS.lane4_s4_outputs(); dirs = {tag: CS.write(SP / "gl4" / tag, files) for tag, files in outs.items()}
    def never_status(matrix_path):
        res = grade_lane4.grade_s4(dirs, amap, matrix_path=matrix_path)
        return {i["fixture"]: i["status"] for i in res["items"] if i["check"] == "never_activate"}
    base = never_status(grade_lane4.MATRIX)
    fn_case("gate1/comparators/grade_lane4.py", "never_activate on clean synthetic output (original matrix)", "must_not_flag", lambda: (all(v == "PASS" for v in base.values()) and bool(base), base), "all PASS")
    mx = json.loads(grade_lane4.MATRIX.read_text(encoding="utf-8")); f0 = mx["fixtures"][0]; f0["never_activate"] = ["[[[unparsable"] + f0["never_activate"][1:]
    mp = SP / "matrix_bad.json"; mp.write_text(json.dumps(mx), encoding="utf-8"); tag0 = pathlib.Path(f0["fixture"]).stem
    fn_case("gate1/comparators/grade_lane4.py", "except_sweep:never_activate selector unparsable → NOT_TESTABLE (not PASS)", "must_flag", lambda: (never_status(mp).get(tag0) == "NOT_TESTABLE", never_status(mp)), f"{tag0}: NOT_TESTABLE", "was: resolve→None or [] silently shrank `never` → PASS")

    # grade_lane4 S2: layer2_imports_layer1 absent → NOT_TESTABLE
    def s2rec(with_key):
        rows = [{"scope": s, "l1": {"allowed": False, "outcome": "DENY"}, "l2": {"allowed": False, "outcome": "DENY"}} for s in grade_lane4.MUST_DENY_BOTH]
        rec = {"layers": {"l1": {"imported": True}, "l2": {"imported": True}}, "rows": rows}
        if with_key: rec["layer2_imports_layer1"] = False
        p = SP / f"s2_{int(with_key)}.json"; p.write_text(json.dumps(rec), encoding="utf-8")
        return {i["check"]: i["status"] for i in grade_lane4.grade_s2(p)}["layer2_independent_of_layer1"]
    fn_case("gate1/comparators/grade_lane4.py", "benign:S2 layer2_imports_layer1 absent → NOT_TESTABLE", "must_flag", lambda: (s2rec(False) == "NOT_TESTABLE", s2rec(False)), "NOT_TESTABLE", "was PASS (absent ≡ False)")
    fn_case("gate1/comparators/grade_lane4.py", "benign:S2 layer2_imports_layer1=false → PASS", "must_not_flag", lambda: (s2rec(True) == "PASS", s2rec(True)), "PASS")

    # evidence_lineage_check: run(empty) in-process
    sys.path.insert(0, str(A / "gate1/lane5_evidence")); import evidence_lineage_check as ELC  # noqa: E402
    fn_case("gate1/lane5_evidence/evidence_lineage_check.py", "vacuous:run(empty dir) → NO_EVIDENCE_INPUT checks_performed=0", "must_flag",
            lambda: (lambda r: (r["verdict"] == "NO_EVIDENCE_INPUT" and r["checks_performed"] == 0, (r["verdict"], r["checks_performed"])))(ELC.run(SP / "empty_dir", None)), "NO_EVIDENCE_INPUT / 0", "was COMPLETE_WITH_ISOLATED_DEFECTS")
    fn_case("gate1/lane5_evidence/evidence_lineage_check.py", "run(fixtures/good) → COMPLETE checks_performed>0", "must_not_flag",
            lambda: (lambda r: (r["verdict"] == "COMPLETE" and r["checks_performed"] > 0, (r["verdict"], r["checks_performed"])))(ELC.run(A / "gate1/lane5_evidence/fixtures/good", A / "gate1/lane5_evidence/fixtures/good/path_manifest.json")), "COMPLETE / >0")

    # run_partial_depth_fixtures._check — extracted (module imports the B engine)
    src = (A / "recovery/fixtures/run_partial_depth_fixtures.py").read_text(encoding="utf-8")
    mod = ast.parse(src); fdef = next(n for n in mod.body if isinstance(n, ast.FunctionDef) and n.name == "_check")
    ns = {"Any": object}; exec(compile(ast.Module(body=[fdef], type_ignores=[]), "rp", "exec"), ns)
    fn_case("recovery/fixtures/run_partial_depth_fixtures.py", "vacuous:_check({}, {}) → VACUOUS marker (not PASS)", "must_flag", lambda: (ns["_check"]({}, {}) and "VACUOUS" in ns["_check"]({}, {})[0], ns["_check"]({}, {})), "['VACUOUS: ...']", "was [] → PASS")
    fn_case("recovery/fixtures/run_partial_depth_fixtures.py", "_check({'ned': 1}, {'ned': 1}) → []", "must_not_flag", lambda: (ns["_check"]({"ned": 1}, {"ned": 1}) == [], ns["_check"]({"ned": 1}, {"ned": 1})), "[]")

    # qa_base: WALL_CLOCK_FILE_UNREADABLE (collector sha = C HEAD, where wall_clock.py does not exist) — in-process, network fetch
    try:
        import qa_base as QB  # noqa: E402
        head = subprocess.check_output(["git", "-C", str(A), "rev-parse", "HEAD"], text=True).strip()
        rep = QB.run({"collector_sha": head})
        codes = sorted({x["code"] for x in rep.get("findings", rep.get("f", []))} if isinstance(rep, dict) else set())
        if "RUNNER_MISSING" in codes:
            CASES.append({"tool": "qa_base.py", "case": "benign:WALL_CLOCK_FILE_UNREADABLE", "control_role": "must_flag", "result": "NOT_EXERCISED", "note": f"the wall-clock branch runs only when batch.py exists at collector_sha; C's repo has no such commit (codes={codes})"})
        else:
            fn_case("qa_base.py", "benign:WALL_CLOCK_FILE_UNREADABLE when wall_clock.py absent at collector sha", "must_flag", lambda: ("WALL_CLOCK_FILE_UNREADABLE" in codes, codes), "finding present", "was: `or ''` → cap None → treated as OK")
    except Exception as e:  # noqa: BLE001
        CASES.append({"tool": "qa_base.py", "case": "benign:WALL_CLOCK_FILE_UNREADABLE", "control_role": "must_flag", "result": "NOT_EXERCISED", "note": f"qa_base.run needs fetch/remote state: {type(e).__name__}: {str(e)[:120]}"})
    CASES.append({"tool": "qa_base.py", "case": "benign:WALL_CLOCK cap present → no UNREADABLE finding", "control_role": "must_not_flag", "result": "NOT_EXERCISED", "note": "no commit in C's repo carries wall_clock.py (B file)"})


def vacuous_probe() -> list[dict]:
    """R43: empty-input probe of the judging functions in scope (function-level; results recorded verbatim)."""
    rows = []
    def t(name, fn, cls, note=""):
        try:
            r = fn(); obs = json.dumps(r, default=str, ensure_ascii=False)[:160]
        except BaseException as e:  # noqa: BLE001
            obs = f"RAISES {type(e).__name__}: {str(e)[:100]}"
        rows.append({"function": name, "empty_input_result": obs, "class": cls, "note": note})
    sys.path.insert(0, str(A / "gate1/comparators")); sys.path.insert(0, str(A / "gate1")); sys.path.insert(0, str(A)); sys.path.insert(0, str(A / "gate1/lane1_task_binding")); sys.path.insert(0, str(A / "gate1/lane4_safety_adapter")); sys.path.insert(0, str(A / "gate1/lane5_evidence")); sys.path.insert(0, str(A / "gate1/lane6_stats")); sys.path.insert(0, str(A / "clean0"))
    import compare_lane1, compare_lane2, compare_lane3, grade_lane4, c_terminal_table as T, selfcheck, adapter_interface_stub as S, evidence_lineage_check as ELC, c_flow_derive as C, variance_control as V, qa_evidence as QE, qa_retention as QR, stats_replay as ST, qa_mart as QM  # noqa: E402
    from adapter_map import AdapterMap  # noqa: E402
    amap = AdapterMap.none(); e = SP / "empty_dir"
    t("compare_lane1.compare_all({}, map)", lambda: compare_lane1.compare_all({}, amap)["summary"]["status"], "DISTINCT (NOT_TESTABLE; CLI now exit 2)")
    t("compare_lane2.compare_all({}, map)", lambda: compare_lane2.compare_all({}, amap)["summary"]["status"], "DISTINCT")
    t("compare_lane3.compare_all({}, map)", lambda: compare_lane3.compare_all({}, amap)["summary"]["status"], "DISTINCT")
    t("grade_lane4.grade_s1(empty dir)", lambda: grade_lane4.grade_s1(e)["status"], "DISTINCT")
    t("grade_lane4.grade_s1b(missing log)", lambda: grade_lane4.grade_s1b(e / "x.log")["status"], "DISTINCT")
    t("grade_lane4.grade_s2(missing json)", lambda: grade_lane4.grade_s2(e / "x.json")[0]["status"], "DISTINCT")
    t("grade_lane4.grade_s3(missing log)", lambda: grade_lane4.grade_s3(e / "x.log")["status"], "DISTINCT")
    t("grade_lane4.grade_s4({}, map)", lambda: grade_lane4.grade_s4({}, amap)["summary"]["status"], "DISTINCT")
    t("c_terminal_table.validate_pair(None,None,None)", lambda: T.validate_pair(None, None, None), "DISTINCT (violation)")
    t("c_terminal_table.validate_zero_depth(None x4)", lambda: T.validate_zero_depth(None, None, None, None), "NOT_APPLICABLE (row predicate: R29 rule does not fire without depth/status; not a pass claim)")
    t("c_terminal_table.validate_policy_relative(None x3)", lambda: T.validate_policy_relative(None, None, None), "NOT_APPLICABLE (row predicate)")
    t("selfcheck.check_fixture(missing, {})", lambda: (selfcheck.check_fixture("/nonexistent.html", {"expect": {}}), list(selfcheck.fails)), "DISTINCT (fail recorded)")
    t("selfcheck.check_registry_verbatim([], {})", lambda: selfcheck.check_registry_verbatim([], {}), "DISTINCT (raises)")
    t("adapter_interface_stub.score_forbidden_actions(empty log)", lambda: S.score_forbidden_actions(e / "log.jsonl", S.MATRIX)["status"], "DISTINCT (SKIPPED)")
    t("evidence_lineage_check.run(empty dir)", lambda: (ELC.run(e, None)["verdict"], ELC.run(e, None)["checks_performed"]), "VACUOUS_PASS → FIXED (NO_EVIDENCE_INPUT, checks_performed=0, exit 3)")
    t("evidence_lineage_check.check_required({}, STATE_REQUIRED)", lambda: (lambda rep: (ELC.check_required({}, ELC.STATE_REQUIRED, "w", rep), len(rep.defects)))(ELC.Report(e, None)), "DISTINCT (MISSING_FIELD per field)")
    t("c_flow_derive.assert_field_qualified({})", lambda: C.assert_field_qualified({}, "x"), "VACUOUS_PASS(form) — NOT FIXED: empty input is a legitimate caller path (denominator_chain.reasons may be {}); the guard's contract is 'no bare mention', for which empty is a true negative")
    t("c_flow_derive.compare_with_mart_row({})", lambda: C.compare_with_mart_row({}), "DISTINCT (raises)")
    t("c_flow_derive._validate_replacement({}, 0)", lambda: C._validate_replacement({}, 0), "DISTINCT (raises)")
    t("c_flow_derive._validate_xy(None, None)", lambda: C._validate_xy(None, None), "DISTINCT (raises)")
    t("c_flow_derive.validate_terminal(None, None, None)", lambda: C.validate_terminal(None, None, None)["ok"], "DISTINCT (ok=False)")
    t("c_flow_derive.family_summary([])", lambda: {k: C.family_summary([], [], [], family_id="F1").get(k) for k in ("n_primary",)}, "DISTINCT (n=0, rate None, warning) — left per coordinator")
    t("variance_control.check_variance([], [], {})", lambda: V.check_variance([], [], {}), "DISTINCT (raises CI-20) — left per coordinator")
    t("qa_evidence.verify_run(empty dir)", lambda: (lambda f: (QE.verify_run(e, f, "t")["status"], [x["code"] for x in f.items]))(QE.F()), "DISTINCT (FAILED)")
    t("qa_evidence.check_plan_order([], {})", lambda: QE.check_plan_order([], {}, None, QE.F(), "L"), "VACUOUS_PASS(form) → FIXED (checks_performed=0 field; run_qa NO_INPUT gate)")
    t("qa_evidence.run_qa(empty out, empty plan)", lambda: (lambda r: (r["verdict"], r["checks_performed"]))(QE.run_qa(str(SP / "qe_empty"), str(SP / "plan.json"), None, "T", None)), "VACUOUS_PASS → FIXED (NO_INPUT, checks_performed=0, exit 2)")
    t("qa_retention.audit_run(empty dir)", lambda: QR.audit_run(e)["has_manifest"], "DISTINCT (has_manifest False → flagged)")
    t("qa_retention.audit_chain(empty dir)", lambda: QR.audit_chain(e), "DISTINCT (present False → linkage_ok falsy)")
    t("stats_replay.spearman_tie_aware([], [])", lambda: {k: ST.spearman_tie_aware([], [])[k] for k in ("n_pairwise_complete", "rho")}, "DISTINCT (n=0, rho None)")
    t("qa_mart.compare('x', None, None)", lambda: QM.compare("x", None, None), "DISTINCT/NOT_APPLICABLE (see result)")
    t("run_partial_depth_fixtures._check({}, {})", lambda: "see injection control", "VACUOUS_PASS(form) → FIXED (VACUOUS marker)")
    t("measure_geometry main (zero fixtures)", lambda: "see subprocess case", "VACUOUS_PASS → FIXED (exit 2)")
    t("walk_fixture main (zero fixtures)", lambda: "see subprocess case", "VACUOUS_PASS → FIXED (exit 2)")
    t("validate_probe_like_playwright main (zero checks)", lambda: "see subprocess case", "VACUOUS_PASS → FIXED (exit 2)")
    t("converge_check main (zero rows)", lambda: "verdict requires n_ok > 0", "DISTINCT (FAIL when nothing compared)")
    t("determinism_check main (--n 0)", lambda: "distinct-per-field 0 != 1 → FAIL", "DISTINCT (ran and failed; not pass)")
    t("qa_mart main (empty C table)", lambda: "see subprocess case", "VACUOUS/did-not-run conflation (exit 0) → FIXED (exit 2)")
    t("holdout_scorer main (empty holdout)", lambda: "gates evaluate to False when n_eval=0", "DISTINCT")
    t("qa_claim main (zero targets)", lambda: "GLOB_EMPTY → SCAN_INVALID → exit 2", "DISTINCT")
    t("lane1 selfcheck main (zero contracts)", lambda: "'no POSITIVE_CONTROL fixture' FAIL", "DISTINCT")
    return rows


def main() -> int:
    t0 = time.time()
    SP.mkdir(parents=True, exist_ok=True)
    inv = inventory()
    head = subprocess.check_output(["git", "-C", str(A), "rev-parse", "HEAD"], text=True).strip()
    try:
        proofs()
        injection_controls()
        vac = vacuous_probe()
    finally:
        for p in TEMP_SIBLINGS:
            try:
                p.unlink()
            except FileNotFoundError:
                pass
        for p in A.rglob("_esd_*.py"):
            p.unlink()
    exc_before, exc_after = except_sweep(True), except_sweep(False)
    ben_before, ben_after = benign_sweep(True), benign_sweep(False)
    tools = []
    for rel, before, after, dist_before, fixed, note in ENTRY_POINTS:
        p = A / rel
        tools.append({"path": rel, "sha256_head": git_head_sha(rel), "sha256_now": sha(p), "changed": (git_head_sha(rel) != sha(p)),
                      "semantics_before": before, "semantics_after": after,
                      "did_not_run_distinguishable_before": dist_before, "did_not_run_distinguishable_after": True if rel != "mlflow_log.py" else None,
                      "fixed": fixed, "note": note})
    n_pass = sum(1 for c in CASES if c["result"] == "PASS"); n_fail = sum(1 for c in CASES if c["result"] == "FAIL"); n_ne = sum(1 for c in CASES if c["result"] == "NOT_EXERCISED")
    doc = {
        "artifact": "EXIT_SEMANTICS_AUDIT_C", "producer": "C (claude-c/assurance-v21)", "measured_at_kst": now(), "worktree_head": head,
        "rulings": ["Δ46-exit2", "Δ50-exit2-common", "D-V3-FINDING-023 (except sweep)", "D-V3-ADDENDUM-006 (denominator + benign-default sweep)", "T-B-V3-FC-005 / R43 (vacuous pass)"],
        "convention": {"0": "ran and passed", "1": "ran and failed", "2": "did not run — read neither as pass nor fail (crash / missing input / precondition / nothing to check)",
                       "exception": "gate1/lane5_evidence/evidence_lineage_check.py keeps 2 = ran-and-found-SYSTEMIC (bound by gate1/run_gate1.py L5 expect_rc=2 on bad_* fixtures) and uses 3 for did-not-run"},
        "denominator": inv,
        "tools": tools,
        "fixed": [t["path"] for t in tools if t["fixed"]],
        "unchanged": [t["path"] for t in tools if not t["fixed"]],
        "not_safe_to_fix_as_specified": [{"path": "gate1/lane5_evidence/evidence_lineage_check.py", "why": "renumbering SYSTEMIC 2→1 / did-not-run →2 would let a crash or an empty dir satisfy run_gate1.py's expect_rc=2 negative-control expectation (run_gate1.py is owner-excluded); tool-local mapping documented in its docstring: 0≡A0, 2≡A1, 3≡A2"},
                                         {"path": "gate1/lane6_stats/c_flow_derive.assert_field_qualified", "why": "empty artifact is a legitimate caller path (denominator_chain.reasons may be {}); raising on empty would break denominator_chain — recorded as VACUOUS_PASS(form), not fixed"}],
        "proof_cases": CASES, "proof_summary": {"n_cases": len(CASES), "pass": n_pass, "fail": n_fail, "not_exercised": n_ne},
        "except_clause_sweep": {
            "scope": "every ExceptHandler in every in-scope *.py (entry points + libraries + fixtures + tests), AST; counts at HEAD (before) and in the worktree (after; includes the Δ46 wrappers added by this change)",
            "before": exc_before, "after": exc_after,
            "judging_path_classified": 25, "fixed": 6,
            "rows": [
                {"site": "bus.py:43 _log except:pass", "class": "(c) non-judging side channel (event log write)"},
                {"site": "gate1/c_terminal_table.py:146 cb=None", "class": "(b) unknown candidates_bound → R29 violation (flagged)"},
                {"site": "gate1/comparators/common.py:93 bbox_center→None", "class": "(a) unreadable bbox ≡ absent → FIXED in compare_lane2 (UNREADABLE_BBOX FAIL); other consumers none"},
                {"site": "gate1/comparators/grade_lane4.py:102/108 _last_json_in_log→None", "class": "(b) None → NOT_TESTABLE"},
                {"site": "gate1/comparators/grade_lane4.py:120 _parse_ts→None / :170 continue", "class": "(c) ts_check is recorded as evidence only, not judged"},
                {"site": "gate1/comparators/grade_lane4.py:298 resolve→None", "class": "(a) None (unparsable) collapsed to [] by `or []` in never_activate binding → FIXED (never_unbound → NOT_TESTABLE); event attribution already UNMAPPED"},
                {"site": "gate1/intake/fixtures_py/coverage_idioms.py:22", "class": "(c) r32 fixture — the idiom under test"},
                {"site": "gate1/intake/r32_selftest.py:54 expect_raises→False", "class": "(b) wrong exception → check FAIL"},
                {"site": "gate1/lane5_evidence/evidence_lineage_check.py:179 parse_iso→None", "class": "(b) unparseable captured_at → MISSING_FIELD defect (line 310); overwrite check skips only that record"},
                {"site": "gate1/lane5_evidence/evidence_lineage_check.py:212 → []", "class": "(b) MISSING_FIELD defect recorded"},
                {"site": "gate1/lane7_grain_determinism/impl_b.py:189 z→0", "class": "(c) CSS semantics (z-index auto/invalid = 0); impl_a is the independent cross-check"},
                {"site": "qa_base.py:81 fc=None", "class": "(b) → FIREWALL_CLOSE_COMMIT_UNBOUND C1"},
                {"site": "qa_evidence.py:330 forbidden-label scan except:pass", "class": "(a) unreadable ≡ clean → FIXED (FORBIDDEN_LABEL_SCAN_UNREADABLE C1)"},
                {"site": "qa_evidence.py:347 _sealed_at→''", "class": "(b) unreadable run.json → not 'pending' → ORPHAN finding (conservative)"},
                {"site": "qa_evidence.py:361 hardstop except:pass", "class": "(a) unparseable timestamp ≡ before hardstop → FIXED (COLLECTION_STARTED_AT_UNPARSEABLE C1)"},
                {"site": "qa_mart.py:25 _num→None", "class": "(a) unreadable ≡ missing → FIXED additively (COERCION_LOG → NUMERIC_COERCION_UNPARSEABLE C1; stats untouched)"},
                {"site": "qa_mart.py:150 row-count except:pass", "class": "(a) unparseable mart file ≡ row count OK → FIXED (MART_FILE_UNPARSEABLE C1 + parse_error field)"},
                {"site": "qa_mart.py:264 _kst→None", "class": "(b) → bucket 'UNKNOWN'"},
                {"site": "stats_replay.py:71 p_value=None / :80 pass", "class": "(b) null p_value / absent scipy keys are distinct from numbers; reference-only"},
                {"site": "stream_qa.py:61 fw_sha=None", "class": "(b) → COLLECTION_BEFORE_FIREWALL_BINDING C1 (conservative)"},
                {"site": "stream_qa.py:81/:90 bus hb/log except:pass", "class": "(c) side channel"},
                {"site": "gate1/lane2_label_reveal/measure_geometry.py:168 → (None, 'err:…')", "class": "(b) error class carried in the tuple"},
                {"site": "gate1/lane3_sequence_dismiss_auth/walk_fixture.py:280", "class": "(b) EXCEPTION recorded as a fixture fail"},
                {"site": "pilot/scope_threeway_test.py:31/91", "class": "(b) rejection class recorded"},
                {"site": "qa_evidence.py:64/96/111", "class": "(b) C1 findings recorded"},
            ]},
        "benign_default_sweep": {
            "scope": "non-except benign defaults in in-scope *.py (AST): `if not p.exists()/is_file()/is_dir(): return/continue/benign`, `.get(k, benign)`, `x or benign` (benign = None/0/False/''/[]/{} /status-like string)",
            "before": ben_before, "after": ben_after,
            "judging_path_examined": 34, "class_a_fixed": 4, "class_a_noted_not_fixed": 1,
            "rows": [
                {"site": "gate1/comparators/grade_lane4.py S2 rec.get('layer2_imports_layer1') falsy → PASS", "class": "(a) absent ≡ independent → FIXED (NOT_TESTABLE when key absent)"},
                {"site": "qa_evidence.py te.get('steps') or [] → no ACTIVATION_AFTER_GATE / MPFED_GT_STEPS", "class": "(a) absent steps ≡ no activation after gate → FIXED (STEPS_ABSENT C1 on gate outcomes, C2 otherwise)"},
                {"site": "qa_evidence.py committed_at or '' → last_commit '' → every unreferenced run 'pending'", "class": "(a) absent ≡ pending (never orphan) → FIXED (BATCH_COMMITTED_AT_MISSING C1)"},
                {"site": "qa_base.py show(wall_clock.py) or '' → cap None → allowed", "class": "(a) unreadable ≡ cap OK → FIXED (WALL_CLOCK_FILE_UNREADABLE / WALL_CLOCK_CAP_UNPARSED C2)"},
                {"site": "gate1/lane6_stats/c_flow_derive.py row_evidence_bearing / row_flow_evaluable: endpoint_status or '' → counted", "class": "(a) noted, NOT fixed: denominator logic (measurement); validate_terminal(None) flags the row separately, so the artifact carries the violation — changing the count would change statistics"},
                {"site": "gate1/comparators/compare_lane2.py _c_reference → None when C's own measure_result.json is absent", "class": "(b) consumer emits an explicit item when ref_row is missing"},
                {"site": "gate1/comparators/grade_lane4.py rec.get('rows', []) (S2)", "class": "(b) each unprobed scope → NOT_TESTABLE"},
                {"site": "gate1/comparators/grade_lane4.py duplicate_suppressed_events or 0 / per_key or {} / errors or []", "class": "(b) conservative: fewer suppressions / no keys / errors → FAIL or NOT_TESTABLE"},
                {"site": "gate1/comparators/grade_lane4.py layer2_mentions_manifest_sha falsy", "class": "(b) conservative (FAIL when open without literal)"},
                {"site": "gate1/comparators/compare_lane1.py markers/battrs .value or {}", "class": "(b) guarded by Lookup.ok; UNMAPPED otherwise"},
                {"site": "gate1/comparators/compare_lane2.py ch.value or [] (nav_container_chain)", "class": "(c) null chain ≡ empty chain semantically; compared against expectation"},
                {"site": "qa_evidence.py attempts or 0 / sealed_at or '' / archetype or 'UNKNOWN'", "class": "(b)/(c) conservative or reporting"},
                {"site": "qa_evidence.py notes or [] → e6b flags False", "class": "(c) reporting breakdown only"},
                {"site": "qa_mart.py rd()→None when table absent; manifest absent", "class": "(b) FROZEN_MART_MANIFEST_MISSING C1; table None handled downstream"},
                {"site": "qa_claim.py FILE_MISSING → MISMATCH + SCAN_INVALID", "class": "(b)"},
                {"site": "clean0/qa_retention.py chain absent → {present: False}", "class": "(b) linkage_ok falsy → MISMATCH"},
                {"site": "gate1/comparators/adapter_map.py path missing → Lookup UNMAPPED", "class": "(b)"},
                {"site": "gate1/lane5_evidence/evidence_lineage_check.py root/manifest missing → exit 3", "class": "(b)"},
                {"site": "w1/dup_launch_harness.py / w1/lock_race_harness.py SUT missing", "class": "(a) → FIXED under Δ46 (exit 2)"},
                {"site": "lane2/lane3/lane7/impl_*/fake_runner_* `.get(...) or ''`/`or 0` on C's own fixture DOM/probe data", "class": "(c) measurement of C-authored fixtures; converge_check cross-checks impl_a vs impl_b"},
                {"site": "c_flow_derive.py entry_is_floating/entry_in_drawer default False", "class": "(b) C recompute vs B row diff surfaces a mismatch"},
                {"site": "remaining ~200 `.get(k, {})` / `or []` / `or {}` sites", "class": "(c) iteration/reporting data access, not a judging path (bulk-classified by pattern)"},
            ]},
        "vacuous_pass_sweep": {"scope": "judging functions (validate_*/check_*/verify_*/assert_*/selfcheck/compare*/grade*/run_qa/audit_*/mains) called with empty input (dict/list/dir, zero fixtures/rows)",
                               "functions_tested": len(vac), "vacuous_pass_found": sum(1 for r in vac if r["class"].startswith("VACUOUS")), "fixed": sum(1 for r in vac if "→ FIXED" in r["class"]),
                               "not_fixed": [r["function"] for r in vac if r["class"].startswith("VACUOUS") and "→ FIXED" not in r["class"]], "rows": vac},
        "run_gate1_selftest_full": {"status": "PENDING — run separately after this demonstrator (long: 5× run_gate1 with browsers); result merged by the worker"},
        "seconds": round(time.time() - t0, 1),
    }
    OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"\nEXIT_SEMANTICS_DEMO: cases={len(CASES)} pass={n_pass} fail={n_fail} not_exercised={n_ne} -> {OUT} ({doc['seconds']}s)")
    return 0 if n_fail == 0 else 1


if __name__ == "__main__":
    try:
        _rc = main()
    except Exception:  # Δ46-exit2: the demonstrator itself did not run
        import traceback
        traceback.print_exc()
        print(f"exit_semantics_demo_c: {DNR} — read neither as pass nor fail (exit 2)", file=sys.stderr)
        _rc = 2
    sys.exit(_rc)
