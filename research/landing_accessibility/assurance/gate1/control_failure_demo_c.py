#!/usr/bin/env python3
"""control_failure_demo_c.py — C's demonstrator that three C tools honour their DECLARED failure behaviour (Δ46: R40 / Δ46-declared /
Δ46-exit2 / Δ46-casename).

Never touches the live tools. For each tool it copies the tool (+ the fixtures it needs) into an isolated scratch directory, applies
ONE mutation per failure case, runs the copy as a subprocess and measures the declared behaviour — for r32 the sha256 of the --out
file before/after (R40: exit codes do not survive in files), for the scanner the stdout JSON block. Every case is recorded in the
sidecar CONTROL_FAILURE_DEMOS_C.json with the sha256 of the LIVE tool at demo time; the tools read that sidecar and report
`failure_behaviour_demo.valid_for_this_commit` = (sidecar sha == their own sha now) AND (every case for them PASSed).
run_gate1 cases run in a scratch copy of the whole assurance/ layout (lanes + comparators, no sidecar) with --dry-run --skip-browser and
are measured, like r32, by the sha256 of a pre-seeded --out/GATE1_VERDICT_C.json sentinel before/after plus the written verdict's fields.

Case names state what they demonstrate (Δ46-casename). Declared behaviours demonstrated (Δ46-declared — exactly these, no more):
  c_bus_scan.py
    scanner_emits_index_numbers_when_controls_pass      baseline (must_not_flag): status OK, all MAIN_CHECK_KEYS present, exit 0
    scanner_refuses_index_numbers_when_control_fails    corpus mutated so a real ruling name ("R21") fires in the Δ33 control corpus →
                                                        ruling_record_gaps.status == CONTROLS_FAILED_MAIN_CHECK_REFUSED, no MAIN_CHECK_KEYS,
                                                        summary main-check counters are `n/a`, exit 2
    scanner_exits_2_did_not_run_on_crash                an injected exception in main → exit 2, "did not run — read neither as pass nor
                                                        fail" on stderr, no JSON on stdout (Δ46-exit2)
  gate1/intake/r32_inventory.py
    r32_writes_file_when_controls_pass                  baseline (must_not_flag): --out sentinel sha CHANGES, exit 0
    r32_writes_no_file_when_control_fails               must_flag fixture ctrl_must_flag_ax_node.py mutated to raise → the
                                                        must_flag/task_control_ax_node_silent_none control FAILs → exit 2, sentinel sha unchanged
    r32_exits_3_and_writes_no_file_when_target_unusable empty --target dir → exit 3, sentinel sha unchanged
    r32_exits_2_did_not_run_on_crash                    injected exception after the controls → exit 2, did-not-run message, sentinel unchanged
  gate1/run_gate1.py  (--dry-run --skip-browser)
    run_gate1_writes_verdict_when_controls_pass         baseline (must_not_flag): sentinel sha CHANGES, verdict written with usable true,
                                                        c_harness_defects [], counts.PASS > 0, declared_failure_behaviour + failure_behaviour_demo
                                                        present; exit 1 (dry-run verdict is METHOD_QUALIFIED_WITH_LIMITATIONS, not PASS)
    run_gate1_marks_harness_defect_when_internal_control_fails
                                                        lane1 selfcheck.py (a C_INTERNAL POSITIVE control) mutated to FAIL → verdict
                                                        C_HARNESS_DEFECT, usable false, counts.PASS == 0, every other item NOT_TESTABLE with
                                                        reason `harness_defect`, sentinel sha CHANGES (file IS written — audit trail), exit 1
    run_gate1_exits_2_did_not_run_on_crash              injected exception in evaluate() (the aggregator) → exit 2, did-not-run message,
                                                        sentinel sha unchanged (no verdict file written)

Demonstrator's own controls (`binding`): in a scratch copy of the assurance layout the demo is run, all three tools must report
valid_for_this_commit true (must_not_flag); a one-line comment appended to each scratch tool must flip it to false (must_flag);
re-running the demo against the scratch layout must flip it back to true (must_not_flag).

    control_failure_demo_c.py [--assurance-root DIR] [--out SIDECAR] [--repo DIR] [--scratch DIR] [--skip-binding-control]

exit 0 = every case and binding control PASS (sidecar written) · 1 = ran, some case FAILed (sidecar still written — the failure is the
record) · 2 = did not run (uncaught exception; sidecar untouched).
"""
from __future__ import annotations

import argparse
import datetime as _dt
import hashlib
import json
import pathlib
import shutil
import subprocess
import sys
import tempfile
from typing import Any

HERE = pathlib.Path(__file__).resolve().parent
DEFAULT_ROOT = HERE.parent                      # research/landing_accessibility/assurance
DEFAULT_REPO = "/home/sieg/projects-wsl/ProjectFinal"
KST = _dt.timezone(_dt.timedelta(hours=9), "KST")
SCANNER_REL = "c_bus_scan.py"
R32_REL = "gate1/intake/r32_inventory.py"
RUN_GATE1_REL = "gate1/run_gate1.py"
RUN_GATE1_LANE1_SELFCHECK_REL = "gate1/lane1_task_binding/selfcheck.py"
RUN_GATE1_ARGS = ("--dry-run", "--skip-browser")
SCRATCH_IGNORE = shutil.ignore_patterns("__pycache__", "*.pyc", "out", "CONTROL_FAILURE_DEMOS_C.json")   # no sidecar in a scratch layout
FIXTURES_REL = "gate1/intake/fixtures_py"
SIDECAR_REL = "gate1/CONTROL_FAILURE_DEMOS_C.json"
INDEX_REF = "origin/control/landing-orchestrator:research/landing_accessibility/control/v3/V3_RULING_INDEX.json"
# must agree with c_bus_scan.MAIN_CHECK_KEYS (asserted at run time against the live source, see _scanner_main_check_keys)
SCANNER_MAIN_CHECK_KEYS = ("a_tickets_v3_era", "tokens_mentioned", "index_to_delta_reachability", "unrecorded_mentions",
                           "resolved_only_via_unsafe_alias", "section_mentions_resolved_by_subrows", "index_rows_unmentioned_in_A_tickets",
                           "delta_headings_without_index_row", "delta_sha256", "delta_heading_counts")
DID_NOT_RUN_FRAGMENT = "did not run — read neither as pass nor fail"

# ---- mutations: (anchor, replacement); the anchor MUST exist or the case is reported as NOT_APPLIED (never silently a pass)
SCANNER_CORPUS_MUTATION = (
    '"회의는 3층 회의실에서 열리고 자료는 공유 폴더에 있다. 예산은 다음 분기에 확정된다."',
    '"회의는 3층 회의실에서 열리고 자료는 공유 폴더에 있다. 예산은 다음 분기에 확정된다. R21 "',   # real ruling name now fires in the corpus
)
SCANNER_CRASH_MUTATION = (
    "    res = scan(bus)\n",
    "    res = scan(bus)\n    raise RuntimeError('injected crash (control_failure_demo_c)')\n",
)
R32_FIXTURE_MUTATION = (   # same tamper as r32_selftest S3: the must_flag fixture now raises → its control must FAIL
    "    if node is None:\n        return None\n",
    "    if node is None:\n        raise TypeError('ax_node missing')\n",
)
R32_CRASH_MUTATION = (
    "    scan = scan_tree(target, include_private)\n    git = git_info(target)\n",
    "    raise RuntimeError('injected crash (control_failure_demo_c)')\n    scan = scan_tree(target, include_private)\n    git = git_info(target)\n",
)
RUN_GATE1_INTERNAL_CONTROL_MUTATION = (   # lane1 selfcheck.py (C_INTERNAL, control_role POSITIVE) now reports one FAIL → exits 1
    '    status = "PASS" if not fails else "FAIL"\n',
    '    fails.append("injected internal-control failure (control_failure_demo_c)")\n    status = "PASS" if not fails else "FAIL"\n',
)
RUN_GATE1_CRASH_MUTATION = (   # the aggregator raises before any verdict file is written
    "def evaluate(c: Ctx) -> dict:\n    items = c.items\n",
    "def evaluate(c: Ctx) -> dict:\n    raise RuntimeError('injected crash (control_failure_demo_c)')\n    items = c.items\n",
)


def now_kst() -> str:
    return _dt.datetime.now(KST).isoformat(timespec="seconds")


def sha256_file(p: pathlib.Path) -> str | None:
    return hashlib.sha256(p.read_bytes()).hexdigest() if p.is_file() else None


def mutate(path: pathlib.Path, mutation: tuple[str, str] | None) -> dict[str, Any]:
    if mutation is None:
        return {"applied": False, "description": "none (unmutated copy)"}
    old, new = mutation
    src = path.read_text(encoding="utf-8")
    if src.count(old) != 1:
        return {"applied": False, "description": f"ANCHOR_NOT_FOUND x{src.count(old)}: {old[:60]!r}"}
    path.write_text(src.replace(old, new, 1), encoding="utf-8")
    return {"applied": True, "description": f"{old.strip()[:70]!r} -> {new.strip()[:90]!r}", "file": path.name}


def run(cmd: list[str], cwd: pathlib.Path | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True, cwd=str(cwd) if cwd else None, timeout=300)


def case_record(tool_rel: str, tool_sha: str, name: str, mutation: dict, expected: dict, observed: dict, checks: dict[str, bool]) -> dict:
    ok = mutation.get("applied", False) or mutation.get("description", "").startswith("none")
    result = "PASS" if ok and all(checks.values()) else ("NOT_APPLIED" if not ok else "FAIL")
    return {"tool_path": tool_rel, "tool_sha256_at_demo": tool_sha, "case_name": name, "mutation": mutation, "expected": expected,
            "observed": observed, "checks": checks, "result": result, "measured_at_kst": now_kst()}


# ---------------------------------------------------------------- scanner
def _scanner_main_check_keys(live_scanner: pathlib.Path) -> tuple[str, ...]:
    """Read MAIN_CHECK_KEYS from the live scanner source so the demo asserts the tool's OWN declaration, not a stale copy."""
    ns: dict[str, Any] = {}
    src = live_scanner.read_text(encoding="utf-8")
    start = src.index("MAIN_CHECK_KEYS = (")
    end = src.index(")", src.index('"delta_heading_counts"', start)) + 1
    exec(src[start:end], ns)  # a tuple literal only
    keys = tuple(ns["MAIN_CHECK_KEYS"])
    assert keys == SCANNER_MAIN_CHECK_KEYS, f"demo/tool MAIN_CHECK_KEYS drift: {keys} vs {SCANNER_MAIN_CHECK_KEYS}"
    return keys


def make_temp_bus(td: pathlib.Path, repo: str) -> pathlib.Path:
    """A minimal v3-era bus: one A ticket mentioning R21 and Δ21 (so the main check has a token to resolve) with a real base_sha."""
    head = run(["git", "-C", repo, "rev-parse", "HEAD"]).stdout.strip()
    bus = td / "bus"
    for sub in ("tickets", "acks", "completions"):
        (bus / sub).mkdir(parents=True)
    t = {"ticket_id": "T-A-V3-DEMO-001", "created_at_kst": "2026-08-28T06:00:00+09:00", "from": "A", "to": ["C"], "type": "RULING",
         "priority": "P2", "base_sha": head, "body": "Δ21 cross-check; alias R21 resolves; demo ticket for control_failure_demo_c"}
    (bus / "tickets" / "T-A-V3-DEMO-001.json").write_text(json.dumps(t, ensure_ascii=False), encoding="utf-8")
    return bus


def run_scanner_case(name: str, root: pathlib.Path, repo: str, index_file: pathlib.Path, mutation: tuple[str, str] | None,
                     expected: dict, judge) -> dict:
    live = root / SCANNER_REL
    live_sha = sha256_file(live)
    with tempfile.TemporaryDirectory(prefix="cfd_scanner_") as d:
        td = pathlib.Path(d)
        copy = td / "c_bus_scan.py"
        shutil.copy2(live, copy)
        assert sha256_file(copy) == live_sha
        m = mutate(copy, mutation)
        m["mutated_copy_sha256"] = sha256_file(copy)
        bus = make_temp_bus(td, repo)
        cp = run([sys.executable, str(copy), str(bus), "--repo", repo, "--index-file", str(index_file)])
        try:
            doc = json.loads(cp.stdout) if cp.stdout.strip() else None
        except json.JSONDecodeError:
            doc = None
        observed = {"exit": cp.returncode, "stdout_is_json": doc is not None, "stderr_tail": cp.stderr.strip().splitlines()[-3:]}
        if isinstance(doc, dict):
            rg = doc.get("ruling_record_gaps", {})
            observed.update({"ruling_record_gaps.status": rg.get("status"),
                             "failed_controls": [c["control"] for c in rg.get("controls", []) if c.get("result") == "FAIL"],
                             "main_check_keys_present": [k for k in SCANNER_MAIN_CHECK_KEYS if k in rg],
                             "summary": doc.get("summary"),
                             "failure_behaviour_demo.reason_in_copy": (doc.get("failure_behaviour_demo") or {}).get("reason")})
        checks = judge(observed, doc)
    return case_record(SCANNER_REL, live_sha, name, m, expected, observed, checks)


def scanner_cases(root: pathlib.Path, repo: str, td: pathlib.Path) -> list[dict]:
    raw = run(["git", "-C", repo, "show", INDEX_REF]).stdout
    if not raw.strip():
        raise RuntimeError(f"index unavailable: git show {INDEX_REF}")
    index_file = td / "V3_RULING_INDEX.json"
    index_file.write_text(raw, encoding="utf-8")
    _scanner_main_check_keys(root / SCANNER_REL)
    summary_counters = ("ruling_unrecorded_mentions", "resolved_by_subrows", "alias_collisions", "unsafe_aliases", "empty_alias_rows",
                        "delta_headings_without_index_row")

    def _counters(summary: str | None) -> dict[str, str]:
        out = {}
        for tok in (summary or "").split():
            k, _, v = tok.partition("=")
            if k in summary_counters:
                out[k] = v
        return out

    def judge_pass(o, doc):
        return {"exit_0": o["exit"] == 0, "status_OK": o.get("ruling_record_gaps.status") == "OK",
                "all_main_check_keys_present": o.get("main_check_keys_present") == list(SCANNER_MAIN_CHECK_KEYS),
                "summary_counters_are_numbers": bool(_counters(o.get("summary"))) and all(v.isdigit() for v in _counters(o.get("summary")).values())}

    def judge_refuse(o, doc):
        return {"exit_2": o["exit"] == 2, "status_CONTROLS_FAILED_MAIN_CHECK_REFUSED": o.get("ruling_record_gaps.status") == "CONTROLS_FAILED_MAIN_CHECK_REFUSED",
                "a_control_actually_failed": bool(o.get("failed_controls")),
                "no_main_check_key_emitted": o.get("main_check_keys_present") == [],
                "summary_counters_are_n/a": bool(_counters(o.get("summary"))) and all(v == "n/a" for v in _counters(o.get("summary")).values())}

    def judge_crash(o, doc):
        return {"exit_2": o["exit"] == 2, "did_not_run_message_on_stderr": any(DID_NOT_RUN_FRAGMENT in ln for ln in o["stderr_tail"]),
                "no_json_on_stdout": not o["stdout_is_json"]}

    return [
        run_scanner_case("scanner_emits_index_numbers_when_controls_pass", root, repo, index_file, None,
                         {"exit": 0, "ruling_record_gaps.status": "OK", "main_check_keys": "all present", "summary_counters": "numbers"}, judge_pass),
        run_scanner_case("scanner_refuses_index_numbers_when_control_fails", root, repo, index_file, SCANNER_CORPUS_MUTATION,
                         {"exit": 2, "ruling_record_gaps.status": "CONTROLS_FAILED_MAIN_CHECK_REFUSED", "main_check_keys": "none emitted",
                          "summary_counters": "n/a (never 0)"}, judge_refuse),
        run_scanner_case("scanner_exits_2_did_not_run_on_crash", root, repo, index_file, SCANNER_CRASH_MUTATION,
                         {"exit": 2, "stderr": DID_NOT_RUN_FRAGMENT, "stdout": "no JSON"}, judge_crash),
    ]


# ---------------------------------------------------------------- r32
def run_r32_case(name: str, root: pathlib.Path, tool_mutation: tuple[str, str] | None, fixture_mutation: tuple[str, str] | None,
                 target_mode: str, expected: dict, judge) -> dict:
    live = root / R32_REL
    live_sha = sha256_file(live)
    with tempfile.TemporaryDirectory(prefix="cfd_r32_") as d:
        td = pathlib.Path(d)
        intake = td / "gate1" / "intake"
        intake.mkdir(parents=True)
        copy = intake / "r32_inventory.py"
        shutil.copy2(live, copy)
        assert sha256_file(copy) == live_sha
        shutil.copytree(root / FIXTURES_REL, intake / "fixtures_py", ignore=shutil.ignore_patterns("__pycache__"))
        target = td / "target"
        shutil.copytree(root / FIXTURES_REL, target, ignore=shutil.ignore_patterns("__pycache__"))
        m = mutate(copy, tool_mutation) if tool_mutation else {"applied": False, "description": "none (unmutated copy)"}
        m["mutated_copy_sha256"] = sha256_file(copy)
        if fixture_mutation:
            fm = mutate(intake / "fixtures_py" / "ctrl_must_flag_ax_node.py", fixture_mutation)
            m = {"applied": fm["applied"], "description": "fixture " + fm["description"], "file": "fixtures_py/ctrl_must_flag_ax_node.py",
                 "mutated_copy_sha256": m["mutated_copy_sha256"]}
        if target_mode == "empty":
            target = td / "empty_target"
            target.mkdir()
        out = td / "r32_inventory_C.json"
        out.write_text('{"sentinel": "pre-existing file at --out; the tool must leave it byte-identical unless it legitimately writes"}\n', encoding="utf-8")
        before = sha256_file(out)
        cp = run([sys.executable, str(copy), "--target", str(target), "--fixtures-dir", str(intake / "fixtures_py"), "--out", str(out), "--label", name])
        after = sha256_file(out)
        failed = [ln.strip() for ln in cp.stderr.splitlines() if ln.strip().startswith("FAIL")]
        observed = {"exit": cp.returncode, "output_sha_before": before, "output_sha_after": after, "output_changed": before != after,
                    "failed_control_lines": failed, "stderr_tail": cp.stderr.strip().splitlines()[-3:]}
        if after is not None and before != after:
            try:
                doc = json.loads(out.read_text(encoding="utf-8"))
                observed["written_doc_keys_sample"] = [k for k in ("tool", "controls_all_pass", "failure_behaviour_demo") if k in doc]
                observed["failure_behaviour_demo.reason_in_copy"] = (doc.get("failure_behaviour_demo") or {}).get("reason")
            except json.JSONDecodeError:
                observed["written_doc_keys_sample"] = "NOT_JSON"
        checks = judge(observed)
    return case_record(R32_REL, live_sha, name, m, expected, observed, checks)


def r32_cases(root: pathlib.Path) -> list[dict]:
    def judge_pass(o):
        return {"exit_0": o["exit"] == 0, "output_changed": o["output_changed"],
                "written_doc_has_binding_block": "failure_behaviour_demo" in (o.get("written_doc_keys_sample") or [])}

    def judge_ctrl_fail(o):
        return {"exit_2": o["exit"] == 2, "output_unchanged": not o["output_changed"],
                "must_flag_ax_node_control_FAILed": any("must_flag/task_control_ax_node_silent_none" in ln for ln in o["failed_control_lines"])}

    def judge_exit3(o):
        return {"exit_3": o["exit"] == 3, "output_unchanged": not o["output_changed"]}

    def judge_crash(o):
        return {"exit_2": o["exit"] == 2, "output_unchanged": not o["output_changed"],
                "did_not_run_message_on_stderr": any(DID_NOT_RUN_FRAGMENT in ln for ln in o["stderr_tail"])}

    return [
        run_r32_case("r32_writes_file_when_controls_pass", root, None, None, "fixtures",
                     {"exit": 0, "output": "sha changes (written)"}, judge_pass),
        run_r32_case("r32_writes_no_file_when_control_fails", root, None, R32_FIXTURE_MUTATION, "fixtures",
                     {"exit": 2, "output": "sha unchanged (not written)", "control": "must_flag/task_control_ax_node_silent_none FAIL"}, judge_ctrl_fail),
        run_r32_case("r32_exits_3_and_writes_no_file_when_target_unusable", root, None, None, "empty",
                     {"exit": 3, "output": "sha unchanged (not written)"}, judge_exit3),
        run_r32_case("r32_exits_2_did_not_run_on_crash", root, R32_CRASH_MUTATION, None, "fixtures",
                     {"exit": 2, "output": "sha unchanged (not written)", "stderr": DID_NOT_RUN_FRAGMENT}, judge_crash),
    ]


# ---------------------------------------------------------------- run_gate1
def make_scratch_assurance(root: pathlib.Path, td: pathlib.Path) -> pathlib.Path:
    """Copy the whole assurance/ layout (lanes, comparators, intake fixtures) into td/assurance — without any sidecar, __pycache__ or out/."""
    S = td / "assurance"
    shutil.copytree(root, S, ignore=SCRATCH_IGNORE, symlinks=True)
    assert not (S / SIDECAR_REL).exists()
    return S


def run_run_gate1(tool: pathlib.Path, out: pathlib.Path) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(tool), *RUN_GATE1_ARGS, "--out", str(out)], capture_output=True, text=True, timeout=1800)


def run_run_gate1_case(name: str, root: pathlib.Path, mutation_rel: str | None, mutation: tuple[str, str] | None, expected: dict, judge) -> dict:
    live = root / RUN_GATE1_REL
    live_sha = sha256_file(live)
    with tempfile.TemporaryDirectory(prefix="cfd_run_gate1_") as d:
        td = pathlib.Path(d)
        S = make_scratch_assurance(root, td)
        copy = S / RUN_GATE1_REL
        assert sha256_file(copy) == live_sha
        if mutation_rel:
            m = mutate(S / mutation_rel, mutation)
            m["file"] = mutation_rel
        else:
            m = {"applied": False, "description": "none (unmutated copy)"}
        m["mutated_copy_sha256"] = sha256_file(copy)
        out = td / "out"; out.mkdir()
        vf = out / "GATE1_VERDICT_C.json"
        vf.write_text('{"sentinel": "pre-existing file at --out; the tool must leave it byte-identical unless it legitimately writes"}\n', encoding="utf-8")
        before = sha256_file(vf)
        cp = run_run_gate1(copy, out)
        after = sha256_file(vf)
        observed = {"exit": cp.returncode, "output_sha_before": before, "output_sha_after": after, "output_changed": before != after,
                    "stderr_tail": cp.stderr.strip().splitlines()[-3:]}
        if before != after:
            try:
                doc = json.loads(vf.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                doc = None
            if isinstance(doc, dict):
                items = doc.get("items", [])
                observed.update({"verdict": doc.get("verdict"), "usable": doc.get("usable"), "counts": doc.get("counts"), "n_items": doc.get("n_items"),
                                 "c_harness_defects": doc.get("c_harness_defects"),
                                 "n_items_reason_harness_defect": sum(1 for i in items if i.get("reason") == "harness_defect" and i.get("status") == "NOT_TESTABLE"),
                                 "declared_failure_behaviour_present": isinstance(doc.get("declared_failure_behaviour"), dict),
                                 "failure_behaviour_demo.reason_in_copy": (doc.get("failure_behaviour_demo") or {}).get("reason")})
            else:
                observed["verdict"] = "NOT_JSON"
        checks = judge(observed)
    return case_record(RUN_GATE1_REL, live_sha, name, m, expected, observed, checks)


def run_gate1_cases(root: pathlib.Path) -> list[dict]:
    def judge_pass(o):
        return {"exit_1_not_PASS_verdict_in_dry_run": o["exit"] == 1, "output_changed": o["output_changed"],
                "verdict_reached_and_usable": o.get("usable") is True and o.get("verdict") in ("PASS", "METHOD_QUALIFIED_WITH_LIMITATIONS"),
                "no_harness_defect": o.get("c_harness_defects") == [], "some_PASS_counted": (o.get("counts") or {}).get("PASS", 0) > 0,
                "declared_and_demo_blocks_present": bool(o.get("declared_failure_behaviour_present")) and o.get("failure_behaviour_demo.reason_in_copy") is not None}

    def judge_defect(o):
        n_other = (o.get("n_items") or 0) - len(o.get("c_harness_defects") or [])
        return {"exit_1": o["exit"] == 1, "output_changed_file_written": o["output_changed"], "verdict_C_HARNESS_DEFECT": o.get("verdict") == "C_HARNESS_DEFECT",
                "usable_false": o.get("usable") is False, "lane1_selfcheck_is_the_defect": o.get("c_harness_defects") == ["L1-selfcheck"],
                "zero_PASS_counted": (o.get("counts") or {}).get("PASS") == 0,
                "every_other_item_NOT_TESTABLE_harness_defect": n_other > 0 and o.get("n_items_reason_harness_defect") == n_other}

    def judge_crash(o):
        return {"exit_2": o["exit"] == 2, "output_unchanged_no_verdict_written": not o["output_changed"],
                "did_not_run_message_on_stderr": any(DID_NOT_RUN_FRAGMENT in ln for ln in o["stderr_tail"])}

    return [
        run_run_gate1_case("run_gate1_writes_verdict_when_controls_pass", root, None, None,
                           {"exit": 1, "output": "sha changes (verdict written)", "verdict": "METHOD_QUALIFIED_WITH_LIMITATIONS (dry-run)", "usable": True,
                            "c_harness_defects": []}, judge_pass),
        run_run_gate1_case("run_gate1_marks_harness_defect_when_internal_control_fails", root, RUN_GATE1_LANE1_SELFCHECK_REL,
                           RUN_GATE1_INTERNAL_CONTROL_MUTATION,
                           {"exit": 1, "output": "sha changes (verdict written — audit trail)", "verdict": "C_HARNESS_DEFECT", "usable": False,
                            "counts.PASS": 0, "other_items": "NOT_TESTABLE reason harness_defect"}, judge_defect),
        run_run_gate1_case("run_gate1_exits_2_did_not_run_on_crash", root, RUN_GATE1_REL, RUN_GATE1_CRASH_MUTATION,
                           {"exit": 2, "output": "sha unchanged (no verdict written)", "stderr": DID_NOT_RUN_FRAGMENT}, judge_crash),
    ]


# ---------------------------------------------------------------- demo + sidecar
def demo(root: pathlib.Path, repo: str, sidecar: pathlib.Path) -> dict:
    with tempfile.TemporaryDirectory(prefix="cfd_") as d:
        cases = scanner_cases(root, repo, pathlib.Path(d)) + r32_cases(root) + run_gate1_cases(root)
    doc = {
        "artifact": "CONTROL_FAILURE_DEMOS_C", "plane": "C", "ruling_refs": ["Δ46-R40", "Δ46-declared", "Δ46-exit2", "Δ46-casename", "R35", "R36"],
        "measured_at_kst": now_kst(), "assurance_root": str(root), "demonstrator": "gate1/control_failure_demo_c.py",
        "demonstrator_sha256": sha256_file(pathlib.Path(__file__)),
        "method": "each tool copied (with its fixtures; run_gate1: the whole assurance/ layout) into an isolated temp dir; one mutation per case; run as a "
                  "subprocess; r32 and run_gate1 measured by the sha256 of a pre-seeded --out sentinel before/after (R40: exit codes do not survive in files) "
                  "plus, for run_gate1, the written verdict's verdict/usable/counts/reasons; scanner measured by its stdout JSON block. run_gate1 runs with "
                  "--dry-run --skip-browser. Live tools are never modified. The sidecar records the LIVE tool sha256 at demo time; the tools compare it to "
                  "their own sha at run time.",
        "declared_failure_behaviour": {
            SCANNER_REL: "any ruling-index control FAIL ⇒ ruling_record_gaps.status=CONTROLS_FAILED_MAIN_CHECK_REFUSED, none of MAIN_CHECK_KEYS emitted, "
                         "summary main-check counters `n/a`, exit 2; uncaught exception ⇒ exit 2 + 'did not run — read neither as pass nor fail', no JSON",
            R32_REL: "any control FAIL ⇒ exit 2 and --out NOT written (pre-existing file left byte-identical); target unusable ⇒ exit 3, not written; "
                     "uncaught exception ⇒ exit 2 + did-not-run message, not written",
            RUN_GATE1_REL: "any C_INTERNAL control item FAIL/ERROR/MISSING_SCRIPT ⇒ verdict C_HARNESS_DEFECT, usable false, counts.PASS 0, every other item "
                           "NOT_TESTABLE reason `harness_defect` (original status kept in status_before_harness_defect), verdict file IS written (audit "
                           "trail), exit 1; aggregator crash ⇒ exit 2 + did-not-run message, NO verdict file written; normal: exit 0 iff PASS, exit 1 for "
                           "any other reached verdict",
        },
        "exit_semantics": {
            SCANNER_REL: "0 ran, controls passed · 1 ran and FAILED (PARSE_ERRORS_PRESENT / selftest fail) · 2 DID NOT RUN (controls failed or crash) · 3 usage",
            R32_REL: "0 written · 2 DID NOT RUN (controls failed or crash; nothing written) · 3 target unusable (nothing written) · no exit 1: inventory makes no pass/fail claim",
            RUN_GATE1_REL: "0 verdict PASS · 1 ran, verdict reached but not PASS (incl. C_HARNESS_DEFECT, verdict written with usable false) · 2 DID NOT RUN (crash; no verdict written; argparse usage errors also exit 2)",
            "A_convention": "0 pass · 1 ran and failed · 2 did not run — read neither as pass nor fail (Δ46-exit2)",
        },
        "tool_sha256_at_demo": {SCANNER_REL: sha256_file(root / SCANNER_REL), R32_REL: sha256_file(root / R32_REL), RUN_GATE1_REL: sha256_file(root / RUN_GATE1_REL)},
        "cases": cases,
        "all_cases_pass": all(c["result"] == "PASS" for c in cases),
        "limitation": "mutations are the ones C imagined (one control-failure path per tool + one crash + r32 exit 3; run_gate1's failing control is the "
                      "lane1 selfcheck, its crash is in evaluate()); a PASS here says the declared behaviour held under these mutations, not under every "
                      "possible defect. run_gate1 cases use --dry-run --skip-browser: the browser C_INTERNAL items are NOT_TESTABLE in the demo, not exercised",
    }
    sidecar.parent.mkdir(parents=True, exist_ok=True)
    sidecar.write_text(json.dumps(doc, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return doc


def read_binding(root: pathlib.Path, repo: str, index_file: pathlib.Path, td: pathlib.Path) -> dict[str, Any]:
    """Run both tools from `root` normally and return their failure_behaviour_demo blocks (valid_for_this_commit + reason)."""
    bus = make_temp_bus(td / f"bus_{hashlib.sha1(str(root).encode()).hexdigest()[:6]}_{_dt.datetime.now().strftime('%H%M%S%f')}", repo)
    cp = run([sys.executable, str(root / SCANNER_REL), str(bus), "--repo", repo, "--index-file", str(index_file)])
    sdoc = json.loads(cp.stdout) if cp.stdout.strip() else {}
    out = td / f"r32_{_dt.datetime.now().strftime('%H%M%S%f')}.json"
    cp2 = run([sys.executable, str(root / R32_REL), "--target", str(root / FIXTURES_REL), "--fixtures-dir", str(root / FIXTURES_REL), "--out", str(out)])
    rdoc = json.loads(out.read_text(encoding="utf-8")) if out.is_file() else {}
    gout = td / f"rg_{_dt.datetime.now().strftime('%H%M%S%f')}"
    cp3 = run_run_gate1(root / RUN_GATE1_REL, gout)
    gdoc = json.loads((gout / "GATE1_VERDICT_C.json").read_text(encoding="utf-8")) if (gout / "GATE1_VERDICT_C.json").is_file() else {}
    pick = lambda b: {k: b.get(k) for k in ("valid_for_this_commit", "sha_match", "demo_all_pass", "reason", "tool_sha256_now", "sidecar_tool_sha256")}  # noqa: E731
    return {SCANNER_REL: {"exit": cp.returncode, **pick(sdoc.get("failure_behaviour_demo") or {})},
            R32_REL: {"exit": cp2.returncode, **pick(rdoc.get("failure_behaviour_demo") or {})},
            RUN_GATE1_REL: {"exit": cp3.returncode, **pick(gdoc.get("failure_behaviour_demo") or {})}}


def binding_control(root: pathlib.Path, repo: str) -> dict:
    """The demonstrator's own must_flag / must_not_flag, on a scratch copy of the assurance layout (the live layout is never mutated)."""
    with tempfile.TemporaryDirectory(prefix="cfd_binding_") as d:
        td = pathlib.Path(d)
        S = make_scratch_assurance(root, td)     # whole layout (run_gate1 needs lanes + comparators), no sidecar
        index_file = td / "V3_RULING_INDEX.json"
        index_file.write_text(run(["git", "-C", repo, "show", INDEX_REF]).stdout, encoding="utf-8")
        steps = []
        # step 0: no sidecar yet → must be false with NO_SIDECAR
        b0 = read_binding(S, repo, index_file, td)
        steps.append({"step": "before_any_demo", "kind": "must_flag", "expect": "valid false, reason NO_SIDECAR", "observed": b0,
                      "pass": all(not v["valid_for_this_commit"] and str(v["reason"]).startswith("NO_SIDECAR") for v in b0.values())})
        # step 1: demo against scratch → true
        d1 = demo(S, repo, S / SIDECAR_REL)
        b1 = read_binding(S, repo, index_file, td)
        steps.append({"step": "after_demo", "kind": "must_not_flag", "expect": "valid true", "demo_all_cases_pass": d1["all_cases_pass"], "observed": b1,
                      "pass": d1["all_cases_pass"] and all(v["valid_for_this_commit"] is True for v in b1.values())})
        # step 2: mutate both scratch tools (one appended comment line) → false, TOOL_CHANGED_SINCE_DEMO
        for rel in (SCANNER_REL, R32_REL, RUN_GATE1_REL):
            with open(S / rel, "a", encoding="utf-8") as f:
                f.write("\n# binding-control mutation: one appended comment line (control_failure_demo_c)\n")
        b2 = read_binding(S, repo, index_file, td)
        steps.append({"step": "after_mutating_tools", "kind": "must_flag", "expect": "valid false, reason TOOL_CHANGED_SINCE_DEMO", "observed": b2,
                      "pass": all(v["valid_for_this_commit"] is False and str(v["reason"]).startswith("TOOL_CHANGED_SINCE_DEMO") for v in b2.values())})
        # step 3: re-run demo against the mutated scratch tools → true again
        d3 = demo(S, repo, S / SIDECAR_REL)
        b3 = read_binding(S, repo, index_file, td)
        steps.append({"step": "after_rerunning_demo", "kind": "must_not_flag", "expect": "valid true", "demo_all_cases_pass": d3["all_cases_pass"], "observed": b3,
                      "pass": d3["all_cases_pass"] and all(v["valid_for_this_commit"] is True for v in b3.values())})
    return {"what": "demonstrator binding controls on a scratch layout copy (live layout untouched)", "steps": steps,
            "all_pass": all(s["pass"] for s in steps)}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--assurance-root", type=pathlib.Path, default=DEFAULT_ROOT)
    ap.add_argument("--out", type=pathlib.Path, help=f"sidecar path (default <assurance-root>/{SIDECAR_REL})")
    ap.add_argument("--repo", default=DEFAULT_REPO)
    ap.add_argument("--skip-binding-control", action="store_true", help="skip the demonstrator's own must_flag/must_not_flag (not for the record run)")
    a = ap.parse_args(argv)
    root = a.assurance_root.resolve()
    sidecar = (a.out or root / SIDECAR_REL).resolve()
    doc = demo(root, a.repo, sidecar)
    for c in doc["cases"]:
        o = c["observed"]
        if c["tool_path"] == RUN_GATE1_REL:
            extra = f"changed={o['output_changed']} verdict={o.get('verdict')} usable={o.get('usable')} PASS={(o.get('counts') or {}).get('PASS')} harness_defect_items={o.get('n_items_reason_harness_defect')}"
        elif "output_changed" in o:
            extra = f"changed={o['output_changed']}"
        else:
            extra = f"status={o.get('ruling_record_gaps.status')} main_keys={len(o.get('main_check_keys_present') or [])}"
        print(f"  {c['result']:11s} {c['case_name']:58s} exit={o['exit']} {extra}", file=sys.stderr)
    bc = None
    if not a.skip_binding_control:
        bc = binding_control(root, a.repo)
        for s in bc["steps"]:
            print(f"  {'PASS' if s['pass'] else 'FAIL':11s} binding/{s['step']:24s} ({s['kind']}) "
                  + " ".join(f"{k.split('/')[-1]}={v['valid_for_this_commit']}:{str(v['reason']).split(':')[0]}" for k, v in s["observed"].items()), file=sys.stderr)
        doc["demonstrator_controls"] = bc
        sidecar.write_text(json.dumps(doc, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    ok = doc["all_cases_pass"] and (bc is None or bc["all_pass"])
    print(f"control_failure_demo_c: {'PASS' if ok else 'FAIL'} cases={sum(c['result'] == 'PASS' for c in doc['cases'])}/{len(doc['cases'])} "
          f"binding={'skipped' if bc is None else ('PASS' if bc['all_pass'] else 'FAIL')} sidecar={sidecar} "
          f"scanner_sha={doc['tool_sha256_at_demo'][SCANNER_REL][:12]} r32_sha={doc['tool_sha256_at_demo'][R32_REL][:12]} "
          f"run_gate1_sha={doc['tool_sha256_at_demo'][RUN_GATE1_REL][:12]}", file=sys.stderr)
    return 0 if ok else 1


if __name__ == "__main__":
    try:
        _rc = main()
    except Exception:  # Δ46-exit2
        import traceback
        traceback.print_exc()
        print("control_failure_demo_c: did not run — read neither as pass nor fail (exit 2)", file=sys.stderr)
        _rc = 2
    sys.exit(_rc)
