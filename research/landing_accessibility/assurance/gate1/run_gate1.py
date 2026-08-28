#!/usr/bin/env python3
"""run_gate1.py — Claude C GATE 1 orchestrator (runner-agnostic skeleton, offline).

Runs every C lane under gate1/ against a system-under-test (a scratchpad clone of B's exact SHA), collects
one JSON result per lane item, evaluates the pre-registered verdict rules (GATE1_RUNBOOK_C.md §5) and writes
    <out>/GATE1_VERDICT_C.json   machine verdict (single source; the report is derived from it)
    <out>/GATE1_REPORT_C.md      report skeleton with every mandatory section pre-filled
Exit 0 ONLY on verdict PASS.

Declared failure behaviour (Δ46-declared / Δ46-exit2 / R40 — demonstrated on an isolated copy by gate1/control_failure_demo_c.py,
recorded in gate1/CONTROL_FAILURE_DEMOS_C.json; the verdict JSON carries `declared_failure_behaviour` and `failure_behaviour_demo`
whose `valid_for_this_commit` is true only while the sidecar's run_gate1.py sha256 equals this file's sha256 now):
  (1) any C_INTERNAL control item (the harness's own selftests: lane selfchecks, converge/determinism controls, pytest, synthetic
      demo, comparators import) FAILs / ERRORs / is MISSING ⇒ verdict `C_HARNESS_DEFECT`; no PASS is counted — every other item
      (lane items AND the C_INTERNAL items that passed) is rewritten to NOT_TESTABLE with reason `harness_defect` (its original
      status is kept in `status_before_harness_defect`), `counts.PASS` is 0; the verdict file IS written (audit trail, like D's
      firewall CONTROL_FAIL record) with `usable: false`; exit 1.
  (2) the aggregator crashes (uncaught exception anywhere in main — lane drivers are caught per lane and become C_INTERNAL ERROR
      items under (1)) ⇒ exit 2 + 'did not run — read neither as pass nor fail' on stderr; NO verdict file is written (a
      pre-existing GATE1_VERDICT_C.json at --out is left byte-identical; the report is written before the verdict so a crash
      while writing either leaves no verdict file).
  (3) normal: exit 0 iff verdict PASS; exit 1 for every other verdict that was reached (METHOD_QUALIFIED_WITH_LIMITATIONS,
      FAIL_SYSTEMIC, HARD_STOP, C_HARNESS_DEFECT) — exit 1 always means "ran and did not pass", never "did not run".

    run_gate1.py --sut <clone_root> --sha <sha> --out <dir>
                 [--runner-cmd '<template with {fixture} {contract} {out}>'] [--adapter-map MAP.json]
                 [--control-sha SHA] [--ssot-snapshot-sha SHA] [--ref-sha SHA] [--skip-browser] [--dry-run]
                 [--compare-with <previous GATE1_VERDICT_C.json>]

Input identity (Δ44-R38: measurement records carry input identity; sha fields are written by the tool, never by hand)
  Every item carries `input_identity` — byte sha256 of the item's inputs, computed by this script at record time:
  `fixtures_dir_manifest_sha256` (deterministic manifest of the lane's fixture files: sorted relative paths + per-file
  sha256 → one aggregate sha; manifest text written to <out>/input_identity/), `expectations_file_sha256`,
  `contracts_file_sha256`, `script_file_sha256` (the script the item executed). Top level `input_identity` adds
  `run_gate1_file_sha256`, `comparators_dir_manifest_sha256`, and the ruling index / delta bytes actually read from A's
  PUSHED branch `origin/control/landing-orchestrator` (fetched first; `control_ref_commit_sha`, `fetched_at_kst`;
  fetch failure ⇒ UNAVAILABLE, never a fallback to the local branch — T-A-V3-FC-007).
  `--compare-with` adds `compare_guard`: item-by-item comparison is refused for any item whose input shas differ.

Item kinds
  C_INTERNAL   fixture self-validation / C-internal check — always runs (needs no SUT).
  RUNNER       needs B's runner on C fixtures — runs only with --runner-cmd; the comparison additionally needs
               --adapter-map (field mapping, comparators/adapter_map.py; template comparators/adapter_map.default.json);
               without it the raw runner output is captured and the item is NOT_TESTABLE(UNMAPPED). With it the
               comparators (comparators/compare_lane1-3.py, grade_lane4.py) grade the captured output; a map row left
               null stays UNMAPPED. Never PASS by silence.
  RUNNER_TREE  needs a runner-produced evidence tree / mart rows (lane5, lane6) — same rule.
  SUT_STATIC   needs only the SUT checkout (lane4 scope probe, E001 blob check) — runs whenever --sut is given.

Status vocabulary per item: PASS | FAIL | NOT_TESTABLE | ERROR | MISSING_SCRIPT.
A C-internal item that FAILs/ERRORs is a C harness defect (P-67: positive control failing ⇒ harness defect),
not a B finding — the verdict then is C_HARNESS_DEFECT and no claim about B is made.

--dry-run: sut = the C worktree containing this file, no runner, lane4 stub in plan-only mode.
"""
from __future__ import annotations

import argparse
import datetime as _dt
import hashlib
import json
import os
import pathlib
import shlex
import subprocess
import sys
import time

HERE = pathlib.Path(__file__).resolve().parent                     # .../assurance/gate1
C_WORKTREE = HERE.parents[3]                                       # .../claude_c_assurance_v21
LANES = {
    "lane1": HERE / "lane1_task_binding",
    "lane2": HERE / "lane2_label_reveal",
    "lane3": HERE / "lane3_sequence_dismiss_auth",
    "lane4": HERE / "lane4_safety_adapter",
    "lane5": HERE / "lane5_evidence",
    "lane6": HERE / "lane6_stats",
    "lane7": HERE / "lane7_grain_determinism",
}
ASSURANCE = HERE.parent                                            # .../assurance (lane4 guard fixtures live in w1/)
# Δ44-R38 input identity: which files are "the inputs" of each lane's items (hashed by this tool, never by hand)
LANE_INPUTS: dict[str, dict] = {
    "lane1": {"fixtures_dir": "fixtures", "expectations_file": "EXPECTATIONS.json", "contracts_file": "task_contracts.json"},
    "lane2": {"fixtures_dir": "fixtures", "expectations_file": "EXPECTATIONS.json"},
    "lane3": {"fixtures_dir": "fixtures", "expectations_file": "EXPECTATIONS.json"},
    "lane4": {"fixtures_from_matrix": "forbidden_action_matrix.json", "contracts_file": "forbidden_action_matrix.json"},
    "lane5": {"fixtures_dir": "fixtures"},
    "lane6": {},
    "lane7": {"fixtures_dir": "fixtures", "expectations_dir": "probe_like"},
}
# ruling index / delta are read from what A has PUSHED (T-A-V3-FC-007), never from the local control branch
MAIN_REPO = pathlib.Path("/home/sieg/projects-wsl/ProjectFinal")
CONTROL_REMOTE, CONTROL_BRANCH = "origin", "control/landing-orchestrator"
CONTROL_REF = f"{CONTROL_REMOTE}/{CONTROL_BRANCH}"
RULING_INDEX_PATH = "research/landing_accessibility/control/v3/V3_RULING_INDEX.json"
DELTA_PATH = "research/landing_accessibility/control/v3/V3_0_1_SUCCESSOR_DELTA.md"
MANIFEST_RULE = ("lines '<posix relative path>\\t<sha256 hex of file bytes>\\n' sorted by path (bytewise), "
                 "__pycache__/*.pyc excluded; aggregate = sha256 of the UTF-8 manifest text")
ITEM_SHA_FIELDS = ("fixtures_dir_manifest_sha256", "expectations_file_sha256", "expectations_dir_manifest_sha256",
                   "contracts_file_sha256", "script_file_sha256")
TOP_SHA_FIELDS = ("run_gate1_file_sha256", "comparators_dir_manifest_sha256", "ruling_index_bytes_sha256", "delta_bytes_sha256")
# comparators (gate1/comparators): turn runner output into PASS/FAIL/UNMAPPED items; a missing adapter-map row ⇒ UNMAPPED
sys.path.insert(0, str(HERE / "comparators"))
try:
    from adapter_map import AdapterMap
    import compare_lane1, compare_lane2, compare_lane3, grade_lane4
    COMPARATORS_ERR: str | None = None
except Exception as _e:  # noqa: BLE001 — recorded as a C harness defect, never raised past the driver
    COMPARATORS_ERR = f"{type(_e).__name__}: {_e}"
SSOT_SNAPSHOT_SHA_DEFAULT = "cad8ad45"      # origin control snapshot C verified 0/22 mismatch (T-A-V3-STEP1-013.C ack)
E001_REF_SHA_DEFAULT = "e02eee4b46b83bafc4576f4f96e8ef540ec37ae9"   # lane4 stub baseline; override at ruling time

# R9 canonical 8 (T-A-V3-STEP1-004) — hard-stop vocabulary. Any observed trigger ⇒ HARD_STOP, never PASS.
HARD_STOP_8 = ["wrong_scope", "target_outside_manifest", "forbidden_action", "evidence_overwrite",
               "duplicate_launch", "task_contract_drift", "task_or_outcome_leakage", "denominator_corruption"]
VERDICTS = ["PASS", "METHOD_QUALIFIED_WITH_LIMITATIONS", "FAIL_SYSTEMIC", "HARD_STOP", "C_HARNESS_DEFECT"]
# Δ46/R40: sidecar written by gate1/control_failure_demo_c.py (isolated mutated copies); this tool only READS it and compares shas.
DEMO_SIDECAR = HERE / "CONTROL_FAILURE_DEMOS_C.json"
TOOL_REL = "gate1/run_gate1.py"
DID_NOT_RUN_MSG = "run_gate1: did not run — read neither as pass nor fail (exit 2)"
HARNESS_DEFECT_REASON = "harness_defect"
DECLARED_FAILURE_BEHAVIOUR = {
    "internal_control_fails": "any C_INTERNAL item FAIL/ERROR/MISSING_SCRIPT ⇒ verdict C_HARNESS_DEFECT, usable=false, counts.PASS=0: every "
                              "other item rewritten to NOT_TESTABLE reason 'harness_defect' (original status kept in status_before_harness_defect); "
                              "verdict file IS written (audit trail); exit 1",
    "aggregator_crash": "uncaught exception ⇒ exit 2 + 'did not run — read neither as pass nor fail' on stderr; NO verdict file written "
                        "(pre-existing GATE1_VERDICT_C.json left byte-identical)",
    "normal": "exit 0 iff verdict PASS; exit 1 for any other reached verdict (ran, did not pass)",
    "ruling_refs": ["Δ46-R40", "Δ46-declared", "Δ46-exit2", "Δ46-casename", "P-67"],
}


def failure_demo_binding(tool_path: pathlib.Path = pathlib.Path(__file__), sidecar: pathlib.Path = DEMO_SIDECAR, tool_rel: str = TOOL_REL) -> dict:
    """R40 binding: valid_for_this_commit iff the sidecar's tool sha256 (recorded at demo time) == this file's sha256 now and all demo cases PASSed."""
    now = hashlib.sha256(tool_path.read_bytes()).hexdigest()
    out = {"rule": "Δ46/R40: failure behaviour demonstrated on a mutated copy by gate1/control_failure_demo_c.py; binding = tool sha256", "sidecar": str(sidecar),
           "tool_sha256_now": now, "sidecar_present": sidecar.is_file(), "sidecar_tool_sha256": None, "sha_match": False, "cases": [], "demo_all_pass": False,
           "valid_for_this_commit": False, "reason": None}
    if not sidecar.is_file():
        out["reason"] = "NO_SIDECAR: demonstration never run (or not for this checkout)"; return out
    try:
        sc = json.loads(sidecar.read_text(encoding="utf-8"))
        cases = [c for c in sc.get("cases", []) if c.get("tool_path") == tool_rel]
    except Exception as e:  # noqa: BLE001
        out["reason"] = f"SIDECAR_UNREADABLE: {type(e).__name__}: {e}"[:160]; return out
    out["sidecar_measured_at_kst"] = sc.get("measured_at_kst"); out["sidecar_sha256"] = hashlib.sha256(sidecar.read_bytes()).hexdigest()
    shas = sorted({c.get("tool_sha256_at_demo") for c in cases})
    out["cases"] = [{"case_name": c.get("case_name"), "result": c.get("result")} for c in cases]
    if not cases: out["reason"] = "NO_CASES_FOR_THIS_TOOL"; return out
    if len(shas) != 1: out["reason"] = f"SIDECAR_INCONSISTENT: {len(shas)} distinct tool shas for one tool"; return out
    out["sidecar_tool_sha256"] = shas[0]; out["sha_match"] = shas[0] == now
    out["demo_all_pass"] = all(c.get("result") == "PASS" for c in cases)
    out["valid_for_this_commit"] = out["sha_match"] and out["demo_all_pass"]
    out["reason"] = "OK" if out["valid_for_this_commit"] else ("TOOL_CHANGED_SINCE_DEMO: re-run gate1/control_failure_demo_c.py" if not out["sha_match"] else "DEMO_CASE_FAILED")
    return out


# ----------------------------------------------------------------------------------------------- helpers
def now_kst() -> str:
    return _dt.datetime.now(_dt.timezone(_dt.timedelta(hours=9))).isoformat(timespec="seconds")


def git(root: pathlib.Path, *args: str) -> str | None:
    try:
        return subprocess.check_output(["git", "-C", str(root), *args], text=True, stderr=subprocess.DEVNULL).strip()
    except (OSError, subprocess.SubprocessError):
        return None


def run_cmd(cmd: list[str] | str, cwd: pathlib.Path, log: pathlib.Path, timeout: int, shell: bool = False) -> dict:
    """Run a subprocess; never raise. Returns rc/seconds/log (rc None on error/timeout)."""
    log.parent.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    try:
        with open(log, "w", encoding="utf-8") as fh:
            fh.write(f"$ {cmd if isinstance(cmd, str) else ' '.join(shlex.quote(c) for c in cmd)}\n(cwd={cwd})\n\n")
            fh.flush()
            rc = subprocess.run(cmd, cwd=str(cwd), stdout=fh, stderr=subprocess.STDOUT, timeout=timeout,
                                shell=shell).returncode
        return {"rc": rc, "seconds": round(time.time() - t0, 1), "log": str(log)}
    except subprocess.TimeoutExpired:
        return {"rc": None, "seconds": round(time.time() - t0, 1), "log": str(log), "error": f"timeout>{timeout}s"}
    except OSError as e:
        return {"rc": None, "seconds": round(time.time() - t0, 1), "log": str(log), "error": f"{type(e).__name__}: {e}"}


def tail(path: str | pathlib.Path, n: int = 3) -> list[str]:
    try:
        lines = [ln.rstrip() for ln in pathlib.Path(path).read_text(encoding="utf-8", errors="replace").splitlines() if ln.strip()]
        return lines[-n:]
    except OSError:
        return []


def load_json(p: pathlib.Path):
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


# ----------------------------------------------------------------------------------------------- input identity (Δ44-R38)
def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def sha256_file(p: pathlib.Path) -> str | None:
    try:
        h = hashlib.sha256()
        with open(p, "rb") as fh:
            for chunk in iter(lambda: fh.read(1 << 20), b""):
                h.update(chunk)
        return h.hexdigest()
    except OSError:
        return None


def _skip(p: pathlib.Path) -> bool:
    return "__pycache__" in p.parts or p.suffix == ".pyc"


def file_manifest(files: list[tuple[str, pathlib.Path]]) -> dict:
    """Deterministic manifest over (relative posix path, absolute path): MANIFEST_RULE. Missing files are listed as MISSING."""
    rows = sorted(files, key=lambda t: t[0].encode("utf-8"))
    text = "".join(f"{rel}\t{sha256_file(p) or 'MISSING'}\n" for rel, p in rows)
    return {"n_files": len(rows), "manifest_text": text, "manifest_sha256": sha256_bytes(text.encode("utf-8"))}


def dir_manifest(root: pathlib.Path) -> dict:
    if not root.is_dir():
        return {"n_files": 0, "manifest_text": "", "manifest_sha256": None, "missing_dir": str(root)}
    files = [(p.relative_to(root).as_posix(), p) for p in root.rglob("*") if p.is_file() and not _skip(p)]
    return file_manifest(files)


def lane_input_identity(lane: str, lane_dir: pathlib.Path | None, assurance: pathlib.Path) -> dict:
    """Byte identity of one lane's fixtures / expectations / contracts. Every sha here is computed from file bytes now."""
    spec = LANE_INPUTS.get(lane)
    if spec is None or lane_dir is None:
        return {"fixtures_dir": None, "fixtures_dir_manifest_sha256": None, "fixtures_n_files": 0,
                "expectations_file": None, "expectations_file_sha256": None,
                "contracts_file": None, "contracts_file_sha256": None, "note": f"no lane input spec for '{lane}'"}
    out: dict = {}
    if "fixtures_dir" in spec:
        d = lane_dir / spec["fixtures_dir"]
        m = dir_manifest(d)
        out.update(fixtures_dir=str(d), fixtures_dir_manifest_sha256=m["manifest_sha256"], fixtures_n_files=m["n_files"],
                   _fixtures_manifest_text=m["manifest_text"])
    elif "fixtures_from_matrix" in spec:
        mp = lane_dir / spec["fixtures_from_matrix"]
        rels = [f.get("fixture") for f in (load_json(mp) or {}).get("fixtures", []) if f.get("fixture")]
        m = file_manifest([(rel, (assurance / rel).resolve()) for rel in rels])
        out.update(fixtures_dir=f"{assurance} (files listed in {mp.name})", fixtures_dir_manifest_sha256=m["manifest_sha256"],
                   fixtures_n_files=m["n_files"], _fixtures_manifest_text=m["manifest_text"])
    else:
        out.update(fixtures_dir=None, fixtures_dir_manifest_sha256=None, fixtures_n_files=0)
    for key in ("expectations_file", "contracts_file"):
        if key in spec:
            p = lane_dir / spec[key]
            out[key] = str(p); out[f"{key}_sha256"] = sha256_file(p)
        else:
            out[key] = None; out[f"{key}_sha256"] = None
    if "expectations_dir" in spec:
        d = lane_dir / spec["expectations_dir"]; m = dir_manifest(d)
        out.update(expectations_dir=str(d), expectations_dir_manifest_sha256=m["manifest_sha256"],
                   expectations_dir_n_files=m["n_files"], _expectations_manifest_text=m["manifest_text"])
    return out


def control_identity(repo: pathlib.Path) -> dict:
    """Fetch A's PUSHED control branch and hash the ruling index / delta bytes actually read from it (T-A-V3-FC-007).
    Fetch failure ⇒ UNAVAILABLE; no fallback to the local branch."""
    rec: dict = {"control_repo": str(repo), "control_ref": CONTROL_REF, "control_ref_commit_sha": None,
                 "fetched_at_kst": None, "fetch_ok": False, "fetch_error": None,
                 "ruling_index_path": RULING_INDEX_PATH, "ruling_index_bytes_sha256": "UNAVAILABLE", "ruling_index_bytes": None,
                 "delta_path": DELTA_PATH, "delta_bytes_sha256": "UNAVAILABLE", "delta_bytes": None}
    try:
        r = subprocess.run(["git", "-C", str(repo), "fetch", "-q", CONTROL_REMOTE, CONTROL_BRANCH],
                           capture_output=True, text=True, timeout=120)
        rec["fetched_at_kst"] = now_kst()
        if r.returncode != 0:
            rec["fetch_error"] = f"rc={r.returncode}: {(r.stderr or r.stdout).strip()[:300]}"
            return rec
    except (OSError, subprocess.SubprocessError) as e:
        rec["fetched_at_kst"] = now_kst(); rec["fetch_error"] = f"{type(e).__name__}: {e}"[:300]
        return rec
    rec["fetch_ok"] = True
    rec["control_ref_commit_sha"] = git(repo, "rev-parse", "--verify", f"refs/remotes/{CONTROL_REF}^{{commit}}")
    if not rec["control_ref_commit_sha"]:
        rec["fetch_error"] = f"{CONTROL_REF} not resolvable after fetch"
        return rec
    for key, path in (("ruling_index", RULING_INDEX_PATH), ("delta", DELTA_PATH)):
        try:
            b = subprocess.check_output(["git", "-C", str(repo), "show", f"{rec['control_ref_commit_sha']}:{path}"],
                                        stderr=subprocess.DEVNULL, timeout=60)
            rec[f"{key}_bytes_sha256"] = sha256_bytes(b); rec[f"{key}_bytes"] = len(b)
        except (OSError, subprocess.SubprocessError):
            rec[f"{key}_bytes_sha256"] = "UNAVAILABLE"
    return rec


def _strip_private(d: dict) -> dict:
    return {k: v for k, v in d.items() if not k.startswith("_")}


class Ctx:
    def __init__(self, a: argparse.Namespace):
        self.sut = pathlib.Path(a.sut).resolve()
        self.out = pathlib.Path(a.out).resolve()
        self.sha = a.sha
        self.runner_cmd = a.runner_cmd
        self.adapter_map = load_json(pathlib.Path(a.adapter_map)) if a.adapter_map else None
        self.adapter_map_path = a.adapter_map
        self.amap = (AdapterMap.load(a.adapter_map) if a.adapter_map else AdapterMap.none()) if not COMPARATORS_ERR else None
        self.dry_run = a.dry_run
        self.skip_browser = a.skip_browser
        self.timeout = a.timeout
        self.ref_sha = a.ref_sha
        self.items: list[dict] = []
        self.py = sys.executable
        self.compare_with = a.compare_with

    # -- Δ44-R38 input identity per item: hashed from bytes at record time (after the item's script finished; lane
    #    scripts do not write into their fixture inputs except L5-regen-fixtures, which produces lane5's fixtures) ----
    def input_identity(self, lane: str | None, script: pathlib.Path | None) -> dict:
        ident = _strip_private(lane_input_identity(lane or "", LANES.get(lane or ""), ASSURANCE))
        ident["script_file"] = str(script) if script else None
        ident["script_file_sha256"] = sha256_file(script) if script else None
        ident["hashed_at_kst"] = now_kst()
        return ident

    # -- generic recorders ------------------------------------------------------------------------
    def add(self, **kw) -> dict:
        script = kw.pop("_script", None)
        kw.setdefault("hard_stop", None)
        kw.setdefault("severity_if_fail", "SYSTEMIC")
        kw.setdefault("control_role", None)
        kw.setdefault("detail", {})
        kw["input_identity"] = self.input_identity(kw.get("lane"), script)
        self.items.append(kw)
        return kw

    def script_item(self, *, id: str, lane: str, kind: str, script: pathlib.Path, args: list[str], expect_rc: int,
                    description: str, verifies: str, cwd: pathlib.Path | None = None, needs_browser: bool = False,
                    shell_cmd: str | None = None, **meta) -> dict:
        """Run one existing lane script as a subprocess and grade it by exit code."""
        log = self.out / lane / f"{id}.log"
        base = dict(id=id, lane=lane, kind=kind, description=description, verifies=verifies,
                    cmd=shell_cmd or " ".join([self.py, str(script), *args]), _script=script, **meta)
        if needs_browser and self.skip_browser:
            return self.add(**base, status="NOT_TESTABLE", reason="--skip-browser", detail={})
        if not script.exists():
            return self.add(**base, status="MISSING_SCRIPT", reason=f"script not found: {script}", detail={})
        r = run_cmd(shell_cmd or [self.py, str(script), *args], cwd or script.parent, log, self.timeout,
                    shell=shell_cmd is not None)
        if r["rc"] is None:
            status = "ERROR"
        elif r["rc"] == 2 and expect_rc == 0:
            status = "NOT_TESTABLE"   # Δ46-exit2 / Δ50-exit2-common: exit 2 = the tool DID NOT RUN — neither pass nor fail
            r["reason"] = "did_not_run(exit 2): " + (r.get("reason") or "tool reported it could not run (e.g. layer import failed)")
        elif r["rc"] == expect_rc:
            status = "PASS"
        elif expect_rc != 0 and r["rc"] == 0:
            status = "FAIL"           # negative control did not fail ⇒ the check is not discriminating
        else:
            status = "FAIL"
        return self.add(**base, status=status, expect_rc=expect_rc, **r, stdout_tail=tail(log), detail={})

    def runner_dependent(self, *, id: str, lane: str, kind: str, description: str, verifies: str, **meta) -> dict:
        """Record a runner-dependent item as NOT_TESTABLE with the exact reason (never PASS by silence)."""
        if not self.runner_cmd:
            reason = "runner_cmd absent (B runner CLI unknown / --runner-cmd not given)"
        elif self.adapter_map is None:
            reason = "UNMAPPED: --adapter-map absent; C expectation fields not bound to B output fields"
        else:
            reason = "UNMAPPED: comparison for this item not implemented in this skeleton"
        return self.add(id=id, lane=lane, kind=kind, description=description, verifies=verifies,
                        status="NOT_TESTABLE", reason=reason, **meta)

    def can_compare(self) -> bool:
        return bool(self.runner_cmd) and self.amap is not None and self.amap.present

    def compare_item(self, *, id: str, lane: str, kind: str, description: str, verifies: str, result: dict,
                     status_override: str | None = None, reason_override: str | None = None, **meta) -> dict:
        """Record a comparator result ({items, summary}) as ONE lane item. Sub-items (non-PASS) go to detail;
        the full item list is written to <out>/<lane>/<id>.comparison.json."""
        s = result["summary"]
        status = status_override or s["status"]
        reason = reason_override or s.get("reason")
        (self.out / lane).mkdir(parents=True, exist_ok=True)
        cpath = self.out / lane / f"{id}.comparison.json"
        cpath.write_text(json.dumps(result, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
        non_pass = [i for i in result["items"] if i["status"] != "PASS"]
        it = self.add(id=id, lane=lane, kind=kind, description=description, verifies=verifies, status=status, reason=reason,
                      detail={"summary": {k: v for k, v in s.items() if k not in ("unmapped", "not_testable")},
                              "unmapped_rows": (self.amap.unmapped_rows() if self.amap and self.amap.present else None),
                              "non_pass_items": non_pass[:80], "comparison_file": str(cpath)}, **meta)
        hs = s.get("hard_stop_observed") or []
        if status == "FAIL" and hs:
            it["hard_stop_observed"] = hs[0]
        if s.get("positive_control_failed"):
            it["control_role"] = "POSITIVE_FAILED"
        return it

    def unmapped_item(self, *, id: str, lane: str, kind: str, description: str, verifies: str, compare_fn, **meta) -> dict:
        """Runner/map absent: NOT_TESTABLE with the exact reason, plus the comparator's own UNMAPPED item list."""
        it = self.runner_dependent(id=id, lane=lane, kind=kind, description=description, verifies=verifies, **meta)
        if COMPARATORS_ERR:
            it["detail"] = {"comparators_import_error": COMPARATORS_ERR}
        else:
            try:
                res = compare_fn({}, AdapterMap.none())
                it["detail"] = {"comparator_summary": {k: v for k, v in res["summary"].items() if k in ("status", "counts", "n_items")}}
            except Exception as e:  # noqa: BLE001
                it["detail"] = {"comparator_error": f"{type(e).__name__}: {e}"[:300]}
        return it

    # -- runner invocation on a C fixture (raw capture; comparison is the adapter's job) -----------
    def run_runner(self, lane: str, fixture: pathlib.Path, contract: dict, tag: str) -> dict | None:
        cdir = self.out / "contracts"; cdir.mkdir(parents=True, exist_ok=True)
        cpath = cdir / f"{lane}_{tag}.json"
        cpath.write_text(json.dumps(contract, ensure_ascii=False, indent=1), encoding="utf-8")
        odir = self.out / lane / "runner" / tag; odir.mkdir(parents=True, exist_ok=True)
        cmd = self.runner_cmd.format(fixture=shlex.quote(str(fixture)), contract=shlex.quote(str(cpath)),
                                     out=shlex.quote(str(odir)))
        r = run_cmd(cmd, self.sut, odir / "runner.log", self.timeout, shell=True)
        files = sorted(str(p.relative_to(odir)) for p in odir.rglob("*") if p.is_file())
        return {"fixture": str(fixture), "contract": str(cpath), "out": str(odir), "files": files, **r}


# ----------------------------------------------------------------------------------------------- lanes
def lane4(c: Ctx) -> None:
    L = LANES["lane4"]; lane = "lane4"
    # S2 two-layer scope probe — SUT_STATIC, import-only, no browser/network. Runs against any checkout.
    probe_out = c.out / lane / "s2_scope.json"
    it = c.script_item(id="L4-S2-two-layer-scope-probe", lane=lane, kind="SUT_STATIC",
                       script=L / "two_layer_scope_probe.py", args=["--repo-root", str(c.sut), "--out", str(probe_out)],
                       expect_rc=0, description="scope fail-closed at BOTH firewall layers (FREEZE must_include 1)",
                       verifies="00 §13; T-A-V3-STEP1-FREEZE D.C must_include 1; STEP1-004 R9 wrong_scope",
                       hard_stop="wrong_scope")
    rec = load_json(probe_out)
    if rec:
        rows = rec.get("rows", [])
        denied_both = [r["scope"] for r in rows if not r["l1"].get("allowed") and not r["l2"].get("allowed")]
        allowed_any = [r["scope"] for r in rows if r["l1"].get("allowed") or r["l2"].get("allowed")]
        imported = all(v.get("imported") for v in rec.get("layers", {}).values())
        it["detail"] = {"sut_head": rec.get("sut_head"), "layers_imported": imported,
                        "layer2_mentions_manifest_sha": rec.get("layer2_mentions_manifest_sha"),
                        "layer2_imports_layer1": rec.get("layer2_imports_layer1"),
                        "layer2_known_real_scopes": rec.get("layer2_known_real_scopes"),
                        "denied_both": denied_both, "allowed_at_any_layer": allowed_any}
        if not imported:
            it["status"] = "NOT_TESTABLE"; it["reason"] = "firewall modules not importable from this SUT (see s2_scope.json layers.*.error)"
        elif any(s in allowed_any for s in ("V3_MAIN50", "V3_PILOT_5", "unknown")):
            it["status"] = "FAIL"; it["reason"] = f"unreleased/unknown scope allowed at a layer: {allowed_any}"
            it["hard_stop_observed"] = "wrong_scope"
        # FREEZE must_include 2: layer 2 independent manifest-sha re-check when a V3 scope is opened
        v3_open = [s for s in (rec.get("layer2_known_real_scopes") or []) if str(s).startswith("V3")]
        if v3_open and not rec.get("layer2_mentions_manifest_sha"):
            c.add(id="L4-S2-layer2-manifest-sha-independent", lane=lane, kind="SUT_STATIC", status="FAIL",
                  description="layer 2 opens a V3 scope but has no own manifest_sha256 literal (FREEZE must_include 2)",
                  verifies="T-A-V3-STEP1-FREEZE C_BLK_009 ③ binding_rule", hard_stop="target_outside_manifest",
                  hard_stop_observed="target_outside_manifest", detail={"layer2_known_real_scopes": v3_open})
        else:
            c.add(id="L4-S2-layer2-manifest-sha-independent", lane=lane, kind="SUT_STATIC",
                  status="PASS" if v3_open else "NOT_TESTABLE",
                  reason=None if v3_open else "no V3 scope present in layer 2 at this SHA — rule not exercisable (fail-closed state observed)",
                  description="layer 2 re-verifies manifest sha256 from file bytes with its own literal when a V3 scope is open",
                  verifies="T-A-V3-STEP1-FREEZE C_BLK_009 ③", hard_stop="target_outside_manifest",
                  detail={"layer2_known_real_scopes": rec.get("layer2_known_real_scopes"),
                          "layer2_mentions_manifest_sha": rec.get("layer2_mentions_manifest_sha")})
    # Full safety battery S1/S1b/S2b/S3(/S4) via the lane4 stub — plan-only in dry-run.
    stub = L / "adapter_interface_stub.py"
    if c.dry_run:
        c.script_item(id="L4-stub-plan", lane=lane, kind="SUT_STATIC", script=stub, args=["--dry-run"], expect_rc=0,
                      description="lane4 stub plan listing (dry-run: nothing executed)", verifies="GATE1_SAFETY_PLAN.md",
                      severity_if_fail="C_HARNESS")
        for sid, name, hs in (("S1", "exactly-once duplicate launch", "duplicate_launch"),
                              ("S1b", "TargetLock cross-process race", "duplicate_launch"),
                              ("S2b", "3-way allowlist (allow / outside-deny / tamper-deny)", "target_outside_manifest"),
                              ("S3", "E001_FULL runner path unchanged (blob ids)", None),
                              ("S4", "forbidden-action scoring on 13 guard fixtures", "forbidden_action")):
            c.add(id=f"L4-{sid}", lane=lane, kind="RUNNER" if sid == "S4" else "SUT_STATIC", status="NOT_TESTABLE",
                  reason="dry-run: stub executed in plan-only mode", description=name,
                  verifies="GATE1_SAFETY_PLAN.md (a)-(d); STEP1-004 R9", hard_stop=hs)
        return
    sdir = c.out / lane / "stub"
    args = ["--sut-root", str(c.sut), "--out", str(sdir), "--ref-sha", c.ref_sha, "--cand-sha", c.sha]
    if c.runner_cmd:
        args += ["--runner-cmd", c.runner_cmd]
    c.script_item(id="L4-stub-run", lane=lane, kind="SUT_STATIC", script=stub, args=args, expect_rc=0,
                  description="lane4 safety battery driver (per-step evidence below)", verifies="GATE1_SAFETY_PLAN.md",
                  severity_if_fail="C_HARNESS")
    rec = load_json(sdir / "C_GATE1_SAFETY_ADAPTER.json") or {}
    hs_map = {"S1": "duplicate_launch", "S1b": "duplicate_launch", "S2": "wrong_scope",
              "S2b": "target_outside_manifest", "S3": None, "S4": "forbidden_action"}
    # real pass rules (comparators/grade_lane4.py) for S1 / S1b / S3 from the harness outputs; S2b stays rc-based
    graders = {} if COMPARATORS_ERR else {
        "S1": lambda s: grade_lane4.grade_s1(sdir / "s1_dup"),
        "S1b": lambda s: grade_lane4.grade_s1b(s.get("log") or (sdir / "S1b.log")),
        "S3": lambda s: grade_lane4.grade_s3(s.get("log") or (sdir / "S3.log")),
    }
    for s in rec.get("steps", []):
        sid = s["id"]
        if sid == "S2":
            continue  # already graded from the probe JSON above
        if sid == "S4":
            continue  # graded below through the runner + action log
        st = s.get("status")
        detail = {"pass_rule": s.get("pass"), "log": s.get("log")}
        if st == "RAN" and sid in graders:
            g = graders[sid](s)
            status, reason = g["status"], g.get("reason")
            detail["graded"] = g
        elif st == "RAN":
            status = "PASS" if s.get("rc") == 0 else "FAIL"
            reason = None if status == "PASS" else f"rc={s.get('rc')} (read {s.get('log')} and apply GATE1_SAFETY_PLAN.md pass rule)"
        elif st == "SKIPPED":
            status, reason = "NOT_TESTABLE", s.get("reason")
        else:
            status, reason = "ERROR", s.get("error")
        c.add(id=f"L4-{sid}", lane=lane, kind="SUT_STATIC", status=status, reason=reason,
              description=s.get("name"), verifies="GATE1_SAFETY_PLAN.md", hard_stop=hs_map.get(sid),
              hard_stop_observed=hs_map.get(sid) if status == "FAIL" and hs_map.get(sid) else None, detail=detail)
    # S2 ruling table (A "must" columns in GATE1_SAFETY_PLAN.md (c)) on the same probe JSON
    if not COMPARATORS_ERR:
        s2_items = grade_lane4.grade_s2(probe_out)
        from common import aggregate as _agg
        c.compare_item(id="L4-S2-ruling-table", lane=lane, kind="SUT_STATIC", result={"items": s2_items, "summary": _agg(s2_items)},
                       description="S2 probe rows vs A ruling table: E001_FULL/V3_MAIN50/V3_PILOT_5/unknown denied at BOTH layers; V2_DIAGNOSTIC L2 open only with own sha literal; L2 independent of L1",
                       verifies="GATE1_SAFETY_PLAN.md (c); T-A-V3-STEP1-FREEZE must_include 1-2", hard_stop="wrong_scope")
    # S4 forbidden actions: runner on the 13 guard fixtures under a frozen task_id, graded from the mapped action log
    meta4 = dict(id="L4-S4", lane=lane, kind="RUNNER", hard_stop="forbidden_action",
                 description="forbidden-action scoring on 13 guard fixtures under frozen task_id: zero activation on never_activate controls (DOM-resolved), cross-fixture invariants, candidate states vs matrix, positive control (검색 submit activated)",
                 verifies="GATE1_SAFETY_PLAN.md (b); 03 §7-§8; STEP1-004 R9 forbidden_action")
    if c.can_compare():
        runs4 = [c.run_runner(lane, fx, contract, tag) for tag, fx, contract in grade_lane4.guard_contracts()]
        c.add(id="L4-S4-runner-capture", lane=lane, kind="RUNNER", status="PASS" if all(r["rc"] == 0 for r in runs4) else "FAIL",
              description="runner invoked on 13 guard fixtures (raw capture only)", verifies="03 §7", severity_if_fail="ISOLATED",
              detail={"runs": runs4})
        dirs4 = {pathlib.Path(r["out"]).name: r["out"] for r in runs4}
        c.compare_item(result=grade_lane4.grade_s4(dirs4, c.amap), **meta4)
    else:
        c.unmapped_item(compare_fn=(lambda d, m: grade_lane4.grade_s4(d, m)) if not COMPARATORS_ERR else None, **meta4)


def lane1(c: Ctx) -> None:
    L = LANES["lane1"]; lane = "lane1"
    c.script_item(id="L1-selfcheck", lane=lane, kind="C_INTERNAL", script=L / "selfcheck.py", args=[], expect_rc=0,
                  description="4 fixtures parse, expectations↔contracts 1:1, contract_sha256 recomputed, registry verbatim",
                  verifies="00 §1.1/§5/§9; 01 §5; 02 dim_task_contract", severity_if_fail="C_HARNESS", control_role="POSITIVE")
    tc = load_json(L / "task_contracts.json") or {}
    contracts = tc.get("contracts", [])
    if c.runner_cmd:
        runs = [c.run_runner(lane, (L / k["fixture_path"]).resolve(), k, k["task_id"]) for k in contracts]
        c.add(id="L1-runner-capture", lane=lane, kind="RUNNER", status="PASS" if all(r["rc"] == 0 for r in runs) else "FAIL",
              description="runner invoked on 4 binding fixtures (raw capture only)", verifies="03 §4",
              severity_if_fail="ISOLATED", detail={"runs": runs})
    meta1 = dict(id="L1-binding-and-hash", lane=lane, kind="RUNNER", hard_stop="task_contract_drift",
                 description="task_id/family_id/contract_sha256/endpoint_contract echoed verbatim; endpoint_status∈allowed; decoy endpoint never; forbidden fields absent; no data-c-forbidden activation",
                 verifies="00 §5/§9; 01 §5; 04 §4; STEP1-004 R9 task_contract_drift + forbidden_action")
    if c.can_compare():
        dirs = {pathlib.Path(r["out"]).name: r["out"] for r in runs}
        c.compare_item(result=compare_lane1.compare_all(dirs, c.amap), **meta1)
    else:
        c.unmapped_item(compare_fn=compare_lane1.compare_all if not COMPARATORS_ERR else None, **meta1)


def lane2(c: Ctx) -> None:
    L = LANES["lane2"]; lane = "lane2"
    c.script_item(id="L2-measure-geometry", lane=lane, kind="C_INTERNAL", script=L / "measure_geometry.py", args=[],
                  expect_rc=0, needs_browser=True, severity_if_fail="C_HARNESS", control_role="POSITIVE",
                  description="14 fixtures: visible/AX name separation, modality, relation, reveal direction from geometry (Playwright file:// only)",
                  verifies="04 §4-§7; 00 §8; A R7; STEP1-012 GAP-04/05/06/07")
    ex = load_json(L / "EXPECTATIONS.json") or {}
    if c.runner_cmd:
        runs = []
        for fx in ex.get("fixtures", []):
            contract = {"c_lane": lane, "c_fixture": fx["fixture"], "entry_selector": fx.get("entry_selector"),
                        "task_id": f"C-L2-{fx['fixture']}", "family_id": None,
                        "endpoint_contract": "task-entry control observed at its entry_observed_state (no endpoint required)"}
            runs.append(c.run_runner(lane, (L / "fixtures" / f"{fx['fixture']}.html").resolve(), contract, fx["fixture"]))
        c.add(id="L2-runner-capture", lane=lane, kind="RUNNER", status="PASS" if all(r["rc"] == 0 for r in runs) else "FAIL",
              description="runner invoked on 14 label/reveal fixtures (raw capture only)", verifies="04 §4",
              severity_if_fail="ISOLATED", detail={"runs": runs})
    meta2 = dict(id="L2-surface-state-compare", lane=lane, kind="RUNNER",
                 description="fact_surface_state S0 row + first post-reveal fact_flow_step vs EXPECTATIONS (exact fields, geometry ±0.02, GAP-04 null convention, entry_observed_state, nav_container_chain, dom_ax_divergence)",
                 verifies="04 §4-§7; STEP1-003 R7; STEP1-012")
    if c.can_compare():
        dirs = {pathlib.Path(r["out"]).name: r["out"] for r in runs}
        c.compare_item(result=compare_lane2.compare_all(dirs, c.amap), **meta2)
    else:
        c.unmapped_item(compare_fn=compare_lane2.compare_all if not COMPARATORS_ERR else None, **meta2)


def lane3(c: Ctx) -> None:
    L = LANES["lane3"]; lane = "lane3"
    c.script_item(id="L3-walk-fixtures", lane=lane, kind="C_INTERNAL", script=L / "walk_fixture.py", args=[], expect_rc=0,
                  needs_browser=True, severity_if_fail="C_HARNESS", control_role="POSITIVE",
                  description="8 fixtures walked: lossless triples, DISMISS only in experienced flow, auth stage from A positional rule, fvss, occlusion hit-test",
                  verifies="04 §2-§5; 03 §3/§5-§9; STEP1-011; STEP1-012 GAP-02/03/04/05")
    ex = load_json(L / "EXPECTATIONS.json") or {}
    if c.runner_cmd:
        runs = []
        for name, fx in ex.get("fixtures", {}).items():
            contract = {"c_lane": lane, "c_fixture": name, "task_id": f"C-L3-{name}", "family_id": fx.get("family"),
                        "endpoint_contract": f"terminal body[data-c-state]={fx.get('final_terminal')}",
                        "expected_endpoint_status": fx.get("endpoint_status")}
            runs.append(c.run_runner(lane, (L / "fixtures" / fx["file"]).resolve(), contract, name))
        c.add(id="L3-runner-capture", lane=lane, kind="RUNNER", status="PASS" if all(r["rc"] == 0 for r in runs) else "FAIL",
              description="runner invoked on 8 sequence/dismiss/auth fixtures (raw capture only)", verifies="04 §2",
              severity_if_fail="ISOLATED", detail={"runs": runs})
    meta3 = dict(id="L3-sequence-compare", lane=lane, kind="RUNNER",
                 description="fact_flow_step (state_before, action_token, state_after) list equality; task/experienced sequences; derived counts recomputed by C (three-way); auth_gate_stage; obstruction row; R11 terminal; Q8; credential_check",
                 verifies="04 §2-§5; 03 §5-§9; STEP1-011 P-13/P-14", hard_stop="forbidden_action")
    meta3s = dict(id="L3-scroll-capture-03s3", lane=lane, kind="RUNNER",
                  description="03 §3 scroll-only surface capture: runner emits fact_surface_state S0 and S1 for seq_typing_and_scroll_not_depth with first_visible_scroll_state=S1 (single scroll fixture in the C set)",
                  verifies="03 §3; 04 §4 first_visible_scroll_state; STEP1-012 GAP-02 coverage_gap_elevated",
                  coverage="scroll_capture_03_s3")
    if c.can_compare():
        dirs = {pathlib.Path(r["out"]).name: r["out"] for r in runs}
        res = compare_lane3.compare_all(dirs, c.amap)
        scroll_items = [i for i in res["items"] if i.get("coverage") == "scroll_capture_03_s3"]
        res_main = {"items": [i for i in res["items"] if i.get("coverage") != "scroll_capture_03_s3"], "summary": res["summary"]}
        c.compare_item(result=res_main, **meta3)
        sc = res["summary"].get("scroll_capture_03_s3", "NOT_TESTABLE")
        c.add(status="NOT_TESTABLE" if sc in ("UNMAPPED", "NOT_TESTABLE") else sc,
              reason=res["summary"].get("scroll_capture_reason"), detail={"items": scroll_items}, **meta3s)
    else:
        c.unmapped_item(compare_fn=compare_lane3.compare_all if not COMPARATORS_ERR else None, **meta3)
        c.runner_dependent(**meta3s)


def lane5(c: Ctx) -> None:
    L = LANES["lane5"]; lane = "lane5"
    c.script_item(id="L5-regen-fixtures", lane=lane, kind="C_INTERNAL", script=L / "make_synthetic_evidence.py", args=[],
                  expect_rc=0, severity_if_fail="C_HARNESS", description="regenerate 3 synthetic evidence trees (mtimes matter)",
                  verifies="EVIDENCE_CONTRACT_C.md")
    chk = L / "evidence_lineage_check.py"
    for name, rc, role in (("good", 0, "POSITIVE"), ("bad_overwrite", 2, "NEGATIVE"), ("bad_lineage", 2, "NEGATIVE")):
        c.script_item(id=f"L5-fixture-{name}", lane=lane, kind="C_INTERNAL", script=chk,
                      args=[str(L / "fixtures" / name), "--path-manifest", str(L / "fixtures" / name / "path_manifest.json"),
                            "--out", str(c.out / lane / f"report_{name}.json"), "--quiet"],
                      expect_rc=rc, severity_if_fail="C_HARNESS", control_role=role,
                      description=f"checker on synthetic '{name}' must exit {rc}", verifies="03 §10/§12; 02 §8; STEP1-007 R11/R13")
    tree = c.sut / "artifacts" / "v3_evidence"   # placeholder location; the adapter map may override
    if c.adapter_map and c.adapter_map.get("evidence_root"):
        tree = pathlib.Path(c.adapter_map["evidence_root"])
    if c.runner_cmd and tree.exists():
        it = c.script_item(id="L5-runner-evidence-tree", lane=lane, kind="RUNNER_TREE", script=chk,
                           args=[str(tree), "--out", str(c.out / lane / "report_runner_tree.json"), "--quiet"], expect_rc=0,
                           description=f"lineage/completeness/append-only check on runner output tree {tree}",
                           verifies="03 §10/§12; STEP1-004 R9 evidence_overwrite", hard_stop="evidence_overwrite")
        rep = load_json(c.out / lane / "report_runner_tree.json") or {}
        it["detail"] = {"verdict": rep.get("verdict"), "counts_by_kind": rep.get("counts_by_kind"), "systemic": rep.get("systemic")}
        if rep.get("counts_by_kind", {}).get("OVERWRITE_DETECTED"):
            it["hard_stop_observed"] = "evidence_overwrite"
        if it["status"] == "FAIL" and not rep.get("systemic"):
            it["status"] = "PASS"; it["severity_if_fail"] = "ISOLATED"; it["reason"] = "isolated defects only (COMPLETE_WITH_ISOLATED_DEFECTS)"
    else:
        c.runner_dependent(id="L5-runner-evidence-tree", lane=lane, kind="RUNNER_TREE", hard_stop="evidence_overwrite",
                           description="evidence_lineage_check.py on the runner-produced evidence tree (all C fixtures, one run each)",
                           verifies="03 §10/§12; 02 §8; STEP1-007 R11/R13; STEP1-004 R9 evidence_overwrite")
    c.runner_dependent(id="L5-terminal-reason-table", lane=lane, kind="RUNNER_TREE",
                       description="B's declared endpoint_status × terminal_reason table reconciled with C's ALLOWED_TERMINAL (R11); impossible pairs rejected by B schema",
                       verifies="STEP1-007 R11 consistency")


def lane6(c: Ctx) -> None:
    L = LANES["lane6"]; lane = "lane6"
    c.script_item(id="L6-pytest", lane=lane, kind="C_INTERNAL", script=L / "test_c_flow_derive.py", args=[], expect_rc=0,
                  shell_cmd=f"{shlex.quote(c.py)} -m pytest -q {shlex.quote(str(L / 'test_c_flow_derive.py'))}",
                  severity_if_fail="C_HARNESS", control_role="POSITIVE",
                  description="hand-computed expectations for derive/family_summary/pairwise/denominator_chain/entry_zone/validate_terminal/Q8 guard",
                  verifies="04 §2-§6; 05 §1-§6; STEP1-003 R2/R3/R4/R6/R7; STEP1-006; STEP1-007 R11/R12/R13")
    c.script_item(id="L6-synthetic-demo", lane=lane, kind="C_INTERNAL", script=L / "synthetic_family_demo.py", args=[],
                  expect_rc=0, severity_if_fail="C_HARNESS",
                  description="fixed synthetic family through the whole pipeline; artifact passes assert_field_qualified",
                  verifies="05 §2-§3; STEP1-003 R6 Q8")
    c.runner_dependent(id="L6-recompute-compare", lane=lane, kind="RUNNER_TREE",
                       description="compare_with_mart_row on every runner-produced fact_flow_observation row (C fixtures): diffs must be empty; schema checks task_role/entry_x_y/fixture_input_mode/terminal_reason/auth_gate_stage∈AUTH_GATE_STAGES; q8_bare_mentions empty",
                       verifies="04 §5; 05; STEP1-003; STEP1-006; STEP1-007")
    c.runner_dependent(id="L6-denominator-chain", lane=lane, kind="RUNNER_TREE", hard_stop="denominator_corruption",
                       description="denominator_chain monotonic, replaced stage explicit (k=0 written), reasons ⊂ 4 — on any runner-emitted chain/manifest",
                       verifies="05 §6; STEP1-003 R4; STEP1-004 R9 denominator_corruption")


def lane7(c: Ctx) -> None:
    L = LANES["lane7"]; lane = "lane7"
    c.script_item(id="L7-converge", lane=lane, kind="C_INTERNAL", script=L / "converge_check.py", args=[], expect_rc=0,
                  severity_if_fail="C_HARNESS", control_role="POSITIVE",
                  description="dismiss_control_exists 3-axis rows: impl_a (PROBE) == impl_b (DOM_AX) on f01-f06 (FREEZE must_include 3)",
                  verifies="02 §5; 03 §9; DISMISS_DEFINITION_C.md v1.2; STEP1-FREEZE ruling_11")
    c.script_item(id="L7-converge-negctrl", lane=lane, kind="C_INTERNAL", script=L / "converge_check.py",
                  args=["--negative-control"], expect_rc=0, severity_if_fail="C_HARNESS", control_role="NEGATIVE",
                  description="6 planted PROBE mutations each produce ≥1 DIFF row (check discriminates)", verifies="P-67 / R14")
    c.script_item(id="L7-probe-like-validated", lane=lane, kind="C_INTERNAL", script=L / "validate_probe_like_playwright.py",
                  args=[], expect_rc=0, needs_browser=True, severity_if_fail="C_HARNESS",
                  description="hand-authored probe_like JSON vs real browser (bbox/hittable/AX name/hit grids/blocking proofs)",
                  verifies="DISMISS_DEFINITION_C.md §8 A4/A7")
    det = L / "determinism_check.py"; f04 = L / "fixtures" / "f04_two_overlays_one_blocking.html"
    wd = c.out / lane / "det"
    c.script_item(id="L7-determinism-posctrl", lane=lane, kind="C_INTERNAL", script=det,
                  args=["--cmd", f"{c.py} {L / 'fake_runner_det.py'} {{fixture}} {{out}}", "--fixture", str(f04), "--n", "3",
                        "--label", "det_f04", "--workdir", str(wd), "--policy-doc", str(L / "ROUTE_POLICY_DETERMINISM_SPEC.md")],
                  expect_rc=0, severity_if_fail="C_HARNESS", control_role="POSITIVE",
                  description="deterministic fake runner ×3 on f04 → PASS", verifies="ROUTE_POLICY_DETERMINISM_SPEC.md")
    c.script_item(id="L7-determinism-negctrl", lane=lane, kind="C_INTERNAL", script=det,
                  args=["--cmd", f"{c.py} {L / 'fake_runner_rand.py'} {{fixture}} {{out}}", "--fixture", str(f04), "--n", "3",
                        "--label", "rand_f04", "--workdir", str(wd)],
                  expect_rc=1, severity_if_fail="C_HARNESS", control_role="NEGATIVE",
                  description="random fake runner ×3 on f04 → FAIL (probabilistic, P[false PASS]<1/1000)", verifies="RP-03")
    if c.runner_cmd:
        # runner-agnostic: determinism_check only needs task_flow_sequence / experienced_flow_sequence / steps[].control_selector
        contract = {"c_lane": lane, "task_id": "C-L7-DET-01", "family_id": None, "entry_selector": "[data-c-control=task-entry]",
                    "endpoint_contract": "task-entry control activated (ENDPOINT_REACHED)"}
        cpath = c.out / "contracts" / "lane7_det.json"; cpath.parent.mkdir(parents=True, exist_ok=True)
        cpath.write_text(json.dumps(contract, ensure_ascii=False, indent=1), encoding="utf-8")
        # B's runner writes a directory; determinism_check reads ONE file at {out}. Bridge: run into {out}.d and copy the
        # flow file (adapter spec §3, default <out>/flow.json; override via adapter_map["flow_file"]).
        flow_file = (c.adapter_map or {}).get("flow_file", "flow.json")
        tmpl = ("mkdir -p {out}.d && " + c.runner_cmd.replace("{contract}", shlex.quote(str(cpath))).replace("{out}", "{out}.d")
                + f" && cp {{out}}.d/{shlex.quote(flow_file)} {{out}}")
        for fx in sorted((L / "fixtures").glob("f0*.html")):
            it = c.script_item(id=f"L7-determinism-runner-{fx.stem[:3]}", lane=lane, kind="RUNNER", script=det,
                               args=["--cmd", tmpl, "--fixture", str(fx), "--n", "3", "--label", f"B_{fx.stem[:3]}",
                                     "--workdir", str(wd), "--policy-doc", str(L / "ROUTE_POLICY_DETERMINISM_SPEC.md")],
                               expect_rc=0, description=f"B runner ×3 on {fx.name}: byte-identical sequences + selectors (FREEZE must_include 4)",
                               verifies="STEP1-FREEZE D.B route_policy Δ6-d; ROUTE_POLICY_DETERMINISM_SPEC.md")
            if it.get("rc") == 2:
                it["status"] = "NOT_TESTABLE"; it["reason"] = "runner wrote nothing or output lacks task_flow_sequence/experienced_flow_sequence/steps[].control_selector (adapter spec §2)"
    else:
        c.runner_dependent(id="L7-determinism-runner", lane=lane, kind="RUNNER",
                           description="B runner ×3 on each f01-f06: task_flow_sequence, experienced_flow_sequence, ordered control_selector list byte-identical; policy doc sha bound",
                           verifies="STEP1-FREEZE D.C must_include 4; Δ6-d")
    c.runner_dependent(id="L7-route-policy-doc", lane=lane, kind="RUNNER",
                       description="B's route-selection policy document present at the SHA and answers the 12-item checklist (candidate ranking, tie-break, shortest-path definition, stop conditions)",
                       verifies="STEP1-FREEZE D.B route_policy; ROUTE_POLICY_DETERMINISM_SPEC.md checklist")


# ----------------------------------------------------------------------------------------------- verdict
def evaluate(c: Ctx) -> dict:
    items = c.items
    by = lambda st: [i for i in items if i["status"] == st]
    hard_stops = sorted({i["hard_stop_observed"] for i in items if i.get("hard_stop_observed")})
    harness_defects = [i["id"] for i in items if i["kind"] == "C_INTERNAL" and i["status"] in ("FAIL", "ERROR", "MISSING_SCRIPT")]
    systemic = [i["id"] for i in items if i["status"] == "FAIL" and i["kind"] != "C_INTERNAL" and i.get("severity_if_fail") == "SYSTEMIC"]
    isolated = [i["id"] for i in items if i["status"] == "FAIL" and i["kind"] != "C_INTERNAL" and i.get("severity_if_fail") == "ISOLATED"]
    not_testable = [i["id"] for i in items if i["status"] in ("NOT_TESTABLE", "MISSING_SCRIPT", "ERROR") and i["kind"] != "C_INTERNAL"]
    scroll = [i for i in items if i.get("coverage") == "scroll_capture_03_s3"]
    scroll_status = scroll[0]["status"] if scroll else "NOT_TESTABLE"
    if hard_stops:
        verdict = "HARD_STOP"
    elif harness_defects:
        verdict = "C_HARNESS_DEFECT"
    elif systemic:
        verdict = "FAIL_SYSTEMIC"
    elif not_testable or scroll_status != "PASS":
        verdict = "METHOD_QUALIFIED_WITH_LIMITATIONS"
    else:
        verdict = "PASS"
    neutralised: list[str] = []
    if verdict == "C_HARNESS_DEFECT":
        # declared failure behaviour (1): no PASS is counted — every item other than the failing controls is NOT_TESTABLE/harness_defect
        for i in items:
            if i["id"] in harness_defects:
                continue
            i["status_before_harness_defect"] = i["status"]; i["status"] = "NOT_TESTABLE"; i["reason"] = HARNESS_DEFECT_REASON
            i["neutralised_by"] = harness_defects; neutralised.append(i["id"])
        systemic, isolated = [], []
        not_testable = [i["id"] for i in items if i["status"] == "NOT_TESTABLE" and i["kind"] != "C_INTERNAL"]
        scroll_status = "NOT_TESTABLE"
    counts = {st: len(by(st)) for st in ("PASS", "FAIL", "NOT_TESTABLE", "ERROR", "MISSING_SCRIPT")}
    return {"verdict": verdict, "exit_code": 0 if verdict == "PASS" else 1, "usable": verdict != "C_HARNESS_DEFECT",
            "counts": counts, "n_items": len(items), "neutralised_items": neutralised,
            "hard_stop_triggers_observed": hard_stops, "hard_stop_vocabulary_R9": HARD_STOP_8,
            "systemic_defects": systemic, "isolated_or_site_level_defects": isolated,
            "c_harness_defects": harness_defects, "not_testable_items": not_testable,
            "coverage": {"scroll_capture_03_s3": "VERIFIED" if scroll_status == "PASS" else "NOT_VERIFIED_DECLARED"},
            "rule": ("PASS iff 0 hard-stop AND 0 C-harness defect AND 0 systemic defect AND 0 NOT_TESTABLE runner item "
                     "AND 03 §3 scroll capture VERIFIED; any UNMAPPED/NOT_TESTABLE ⇒ at best METHOD_QUALIFIED_WITH_LIMITATIONS; "
                     "systemic = R9 8-vocabulary trigger OR fixture-reproducible defect (R8 ②); isolated/site-level listed, non-blocking")}


def next_action(v: str) -> str:
    return {
        "PASS": "issue C-GATE1-VERDICT ticket (PASS) to A cc B/D/E with this JSON + report; A may then release V3_PILOT_5 (R10 template, preconditions[] cite B sha + this C sha)",
        "METHOD_QUALIFIED_WITH_LIMITATIONS": "send gate1_adapter_spec.md request to B for the UNMAPPED items; re-run run_gate1.py at the SAME B sha with --runner-cmd/--adapter-map; no release recommendation",
        "FAIL_SYSTEMIC": "issue HOLD (P0) to A cc B: list systemic ids with exact field/value evidence; B fixes and re-COMPLETEs at a new sha; C re-runs from step 1",
        "HARD_STOP": "C hard-stop: issue P0 HOLD to A + DIRECTOR naming the R9 trigger(s); no further lanes are interpreted until A rules",
        "C_HARNESS_DEFECT": "no claim about B. Fix the failing C-internal item (positive control) first, re-run; negatives are uninterpretable until then (P-67)",
    }[v]


# ----------------------------------------------------------------------------------------------- input identity / compare guard
def top_level_identity(c: Ctx) -> dict:
    """Top-level input identity: this script, the comparators package, A's pushed ruling index + delta, per-lane inputs.
    Manifest texts are written to <out>/input_identity/ so every aggregate sha can be recomputed by hand."""
    idir = c.out / "input_identity"; idir.mkdir(parents=True, exist_ok=True)
    comp = dir_manifest(HERE / "comparators")
    (idir / "comparators_dir.manifest.txt").write_text(comp["manifest_text"], encoding="utf-8")
    lanes = {}
    for ln, d in LANES.items():
        li = lane_input_identity(ln, d, ASSURANCE)
        if li.get("_fixtures_manifest_text") is not None:
            (idir / f"{ln}_fixtures_dir.manifest.txt").write_text(li["_fixtures_manifest_text"], encoding="utf-8")
        if li.get("_expectations_manifest_text") is not None:
            (idir / f"{ln}_expectations_dir.manifest.txt").write_text(li["_expectations_manifest_text"], encoding="utf-8")
        lanes[ln] = _strip_private(li)
    me = pathlib.Path(__file__).resolve()
    return {"rule": "Δ44-R38: sha fields below are computed by run_gate1.py from bytes; never edited by hand; values with different input shas are not compared",
            "hash_algorithm": "sha256", "manifest_rule": MANIFEST_RULE, "manifests_dir": str(idir),
            "run_gate1_file": str(me), "run_gate1_file_sha256": sha256_file(me),
            "comparators_dir": str(HERE / "comparators"), "comparators_dir_manifest_sha256": comp["manifest_sha256"],
            "comparators_dir_n_files": comp["n_files"],
            **control_identity(MAIN_REPO),
            "field_glossary": {
                "fixtures_dir_manifest_sha256": "aggregate sha256 of the manifest (path + per-file sha256) of the lane's fixture files",
                "expectations_file_sha256": "sha256 of the lane's EXPECTATIONS.json bytes",
                "expectations_dir_manifest_sha256": "lane7: manifest sha of probe_like/*.json (hand-authored expectations)",
                "contracts_file_sha256": "sha256 of the lane's contracts JSON bytes (lane1 task_contracts.json, lane4 forbidden_action_matrix.json)",
                "script_file_sha256": "sha256 of the script file the item executed (null: item ran no script)",
                "run_gate1_file_sha256": "sha256 of this orchestrator's own bytes",
                "comparators_dir_manifest_sha256": "manifest sha of gate1/comparators/ (graders used for runner items)",
                "ruling_index_bytes_sha256": f"sha256 of `git show {CONTROL_REF}:{RULING_INDEX_PATH}` bytes at control_ref_commit_sha",
                "delta_bytes_sha256": f"sha256 of `git show {CONTROL_REF}:{DELTA_PATH}` bytes at control_ref_commit_sha",
                "control_ref_commit_sha": f"commit {CONTROL_REF} resolved to right after `git fetch` (A's pushed state, not the local branch)"},
            "lanes": lanes}


def compare_guard(c: Ctx, top: dict) -> dict:
    """--compare-with: refuse item-by-item comparison for any item whose input shas differ from the previous verdict."""
    policy = "Δ44-R38: values with different input shas are not compared; a refused item carries no claim of change or sameness"
    if not c.compare_with:
        return {"enabled": False, "policy": policy, "previous_verdict_file": None}
    pp = pathlib.Path(c.compare_with)
    prev = load_json(pp)
    g: dict = {"enabled": True, "policy": policy, "previous_verdict_file": str(pp), "previous_file_sha256": sha256_file(pp)}
    if not isinstance(prev, dict) or "items" not in prev:
        g.update(usable=False, reason="previous verdict file unreadable or has no items[]", items={}, n_comparable=0, n_refused=0,
                 refused_items=[], top_level_mismatched_fields=[], missing_in_previous=[], missing_in_current=[])
        return g
    ptop = prev.get("input_identity") or {}
    top_mism = [k for k in TOP_SHA_FIELDS if ptop.get(k) != top.get(k)]
    g["top_level_mismatched_fields"] = top_mism
    g["top_level_identity_match"] = not top_mism
    g["previous_control_ref_commit_sha"] = ptop.get("control_ref_commit_sha")
    pitems = {i.get("id"): i for i in prev.get("items", []) if isinstance(i, dict)}
    items, refused, comparable = {}, [], []
    for it in c.items:
        pid = pitems.get(it["id"])
        if pid is None:
            continue
        pi, ci = pid.get("input_identity") or {}, it.get("input_identity") or {}
        if not pi:
            mism = ["<previous item has no input_identity>"]
        else:
            mism = [k for k in ITEM_SHA_FIELDS if pi.get(k) != ci.get(k)]
        ok = not mism
        rec = {"comparable": ok, "mismatched_input_sha_fields": mism, "previous_status": pid.get("status"), "current_status": it["status"],
               "status_changed": (pid.get("status") != it["status"]) if ok else None,
               "note": None if ok else "REFUSED: input shas differ — statuses are not compared (Δ44-R38)"}
        items[it["id"]] = rec
        (comparable if ok else refused).append(it["id"])
    g.update(usable=True, items=items, n_comparable=len(comparable), n_refused=len(refused), refused_items=refused,
             status_changed_items=[k for k, v in items.items() if v["status_changed"]],
             missing_in_previous=[i["id"] for i in c.items if i["id"] not in pitems],
             missing_in_current=[k for k in pitems if k not in {i["id"] for i in c.items}])
    return g


def identity_report_md(top: dict, guard: dict) -> str:
    lanes = "\n".join(f"| {ln} | `{v.get('fixtures_dir_manifest_sha256')}` ({v.get('fixtures_n_files')} files) | `{v.get('expectations_file_sha256') or v.get('expectations_dir_manifest_sha256')}` | `{v.get('contracts_file_sha256')}` |"
                      for ln, v in top["lanes"].items())
    md = f"""
## 8. Input identity (Δ44-R38 — sha fields written by run_gate1.py from bytes, never by hand)
Manifest rule: {top['manifest_rule']}. Manifest texts: `{top['manifests_dir']}`.

| what is hashed | sha256 |
|---|---|
| run_gate1.py bytes (`run_gate1_file_sha256`) | `{top['run_gate1_file_sha256']}` |
| gate1/comparators/ manifest (`comparators_dir_manifest_sha256`, {top['comparators_dir_n_files']} files) | `{top['comparators_dir_manifest_sha256']}` |
| control ref read (`control_ref`, A's pushed branch, fetched {top['fetched_at_kst']}, fetch_ok={top['fetch_ok']}) | `{top['control_ref']}` → commit `{top['control_ref_commit_sha']}` {('· fetch_error: ' + str(top['fetch_error'])) if top.get('fetch_error') else ''} |
| `{top['ruling_index_path']}` bytes at that commit (`ruling_index_bytes_sha256`) | `{top['ruling_index_bytes_sha256']}` |
| `{top['delta_path']}` bytes at that commit (`delta_bytes_sha256`) | `{top['delta_bytes_sha256']}` |

| lane | fixtures_dir_manifest_sha256 | expectations (file sha / probe_like manifest sha) | contracts_file_sha256 |
|---|---|---|---|
{lanes}

## 9. compare_guard
"""
    if not guard["enabled"]:
        return md + "no `--compare-with` given — no item-by-item comparison with a previous verdict was attempted.\n"
    if not guard.get("usable"):
        return md + f"previous file `{guard['previous_verdict_file']}` unusable: {guard['reason']}\n"
    ref = "\n".join(f"- `{k}`: refused — differing input sha fields {json.dumps(guard['items'][k]['mismatched_input_sha_fields'])}" for k in guard["refused_items"]) or "- (none)"
    chg = "\n".join(f"- `{k}`: {guard['items'][k]['previous_status']} → {guard['items'][k]['current_status']}" for k in guard["status_changed_items"]) or "- (none)"
    return md + f"""previous: `{guard['previous_verdict_file']}` (sha256 `{guard['previous_file_sha256']}`, control commit `{guard['previous_control_ref_commit_sha']}`)
top-level identity match: {guard['top_level_identity_match']} (mismatched: {json.dumps(guard['top_level_mismatched_fields'])})
comparable items: {guard['n_comparable']} · refused (input shas differ — NOT compared): {guard['n_refused']} · missing in previous: {json.dumps(guard['missing_in_previous'])} · missing in current: {json.dumps(guard['missing_in_current'])}

Refused items:
{ref}

Status changes among comparable items:
{chg}
"""


# ----------------------------------------------------------------------------------------------- report
def write_report(c: Ctx, verdict: dict, shas: dict, path: pathlib.Path, top: dict | None = None, guard: dict | None = None) -> None:
    def row(i: dict) -> str:
        r = i.get("reason") or ""
        hs = i.get("hard_stop") or ""
        return f"| {i['id']} | {i['kind']} | {i.get('control_role') or ''} | **{i['status']}** | {hs} | {i['description'][:110]} | {r[:120]} |"
    lanes_md = []
    for ln in LANES:
        its = [i for i in c.items if i["lane"] == ln]
        lanes_md.append(f"\n### {ln} — {LANES[ln].name}\n\n| item | kind | ctl | status | hard-stop class | what | reason / note |\n|---|---|---|---|---|---|---|\n"
                        + "\n".join(row(i) for i in its))
    nt = [i for i in c.items if i["id"] in verdict["not_testable_items"]]
    unverified = "\n".join(f"- `{i['id']}` ({i['lane']}): {i['description'][:140]} — {i.get('reason','')}" for i in nt) or "- (none)"
    scroll_line = ("03 §3 scroll-only surface capture: **VERIFIED** on the single C scroll fixture (`seq_typing_and_scroll_not_depth`, S1)."
                   if verdict["coverage"]["scroll_capture_03_s3"] == "VERIFIED" else
                   "03 §3 scroll-only surface capture: **NOT VERIFIED — declared** (T-A-V3-STEP1-012 GAP-02 coverage ruling). C's set holds exactly one scroll fixture (`seq_typing_and_scroll_not_depth`); the runner's S0/S1 `fact_surface_state` rows for it were not compared.")
    md = f"""# GATE1_REPORT_C — Claude C GATE 1 verdict (skeleton generated by run_gate1.py)

**Verdict**: **{verdict['verdict']}** · usable={verdict['usable']} · generated {shas['generated_at_kst']} · dry_run={c.dry_run}
Machine source of truth: `GATE1_VERDICT_C.json` (same directory). This file is derived; edit only the free-text sections marked `<<fill>>`.

## 1. Exact SHAs
| what | value |
|---|---|
| B system under test (`--sha`, must equal B COMPLETION ticket exact SHA) | `{shas['sut_sha_claimed']}` |
| SUT clone HEAD (`git rev-parse HEAD` in `--sut`) | `{shas['sut_head']}` · tree `{shas['sut_tree']}` · dirty={shas['sut_dirty']} |
| SUT matches claimed sha | {shas['sut_matches_claim']} |
| C lanes (this worktree HEAD) | `{shas['c_head']}` · tree(gate1) `{shas['c_gate1_tree']}` · dirty(gate1)={shas['c_gate1_dirty']} |
| control (`control/landing-orchestrator` local ref) | `{shas['control_sha']}` |
| SSOT snapshot (control `control/v3/ssot_snapshot/`, C verified 0/22 mismatch) | `{shas['ssot_snapshot_sha']}` |
| E001 reference blob baseline (lane4 S3) | `{shas['e001_ref_sha']}` |
| runner cmd template | `{c.runner_cmd or '(none — runner-dependent items NOT_TESTABLE)'}` |
| adapter map | `{c.adapter_map_path or '(none — comparisons UNMAPPED)'}` |

## 2. Per-lane results
Independence statement: every fixture, expectation and checker below was authored by C from SSOTV3 text and A rulings only; no B/D fixture, code or expected output was read or imported (T-A-V3-STEP1-007 R14). C fixtures ≠ B fixtures by construction; a C-vs-B result divergence is reported as an interpretation-mismatch signal, never smoothed.
Counts: {json.dumps(verdict['counts'])} over {verdict['n_items']} items.
{''.join(lanes_md)}

## 3. Reconciliation of lane contradictions
<<fill>> — list any item where two lanes disagree on the same field (e.g. lane3 vs lane7 occlusion/blocking-proof, lane2 vs lane6 label_relation, lane5 vs lane6 R11 table). Pre-registered resolutions: GATE1_PREREGISTRATION_C.md §2 (P-06/09/11/13/14/17/23/24/30). A new contradiction ⇒ RECONCILIATION_REQUIRED to A, not a silent choice.

## 4. 검증하지 않은 것 (mandatory — T-A-V3-P0-001 gate_rule)
{unverified}
- {scroll_line}
- Real-site behaviour (WAF/timeout/site-specific surfaces): not verified — GATE 1 is fixture-only; site-level failures are observations, not defects (R8 ③).
- <<fill>> anything C chose not to run at this SHA.

## 5. Known limitations
- **R14 shared-reading risk**: C's fixtures and C's expectations come from the same C reading of SSOTV3. Mutation/negative controls catch implementation errors only; an interpretation error shared by fixture and expectation is invisible here. Mitigation is the C≠B independence above and A's rulings; residual risk is declared, not removed.
- {scroll_line}
- SSOT snapshot integrity: sha256 0/22 mismatch was verified at `{shas['ssot_snapshot_sha']}`; non-tampering between 01:52–03:19 KST is circumstantial, not proven (T-A-V3-STEP1-013.C honest_limit).
- lane5 append-only detection is mtime-based on this filesystem; a rewrite that preserves mtime is not caught by OVERWRITE_DETECTED (HASH_MISMATCH still fires).
- lane7 determinism negative control is probabilistic (P[false PASS] < 1/1000 on f04).
- lane4 exactly-once discrimination requires the pre-W1 positive control (`2281c85`) to have been run at this session — <<fill: cite the run or mark not re-run>>.
- <<fill>>

## 6. Hard-stop triggers observed (R9 canonical 8; must be 0 for PASS)
observed: `{json.dumps(verdict['hard_stop_triggers_observed'])}` of vocabulary {json.dumps(HARD_STOP_8)}
systemic (fixture-reproducible, R8 ②): `{json.dumps(verdict['systemic_defects'])}` · isolated/site-level (listed, non-blocking): `{json.dumps(verdict['isolated_or_site_level_defects'])}` · C harness defects: `{json.dumps(verdict['c_harness_defects'])}`

## 7. Next automatic action
{next_action(verdict['verdict'])}
"""
    if top is not None and guard is not None:
        md += identity_report_md(top, guard)
    path.write_text(md, encoding="utf-8")


# ----------------------------------------------------------------------------------------------- main
def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="C GATE 1 orchestrator (offline, runner-agnostic)")
    ap.add_argument("--sut", help="scratchpad clone root of B's exact SHA (dry-run: defaults to the C worktree)")
    ap.add_argument("--sha", help="B COMPLETION exact SHA (dry-run: C worktree HEAD)")
    ap.add_argument("--out", help="output dir (dry-run default: <gate1>/out/dry_run)")
    ap.add_argument("--runner-cmd", default=None, help="B runner template with {fixture} {contract} {out}")
    ap.add_argument("--adapter-map", default=None, help="JSON binding C expectation fields → B output fields (see GATE1_RUNBOOK_C.md §3)")
    ap.add_argument("--control-sha", default=None)
    ap.add_argument("--ssot-snapshot-sha", default=SSOT_SNAPSHOT_SHA_DEFAULT)
    ap.add_argument("--ref-sha", default=E001_REF_SHA_DEFAULT, help="E001_FULL runner-path reference sha for lane4 S3")
    ap.add_argument("--skip-browser", action="store_true", help="skip Playwright items (recorded NOT_TESTABLE)")
    ap.add_argument("--timeout", type=int, default=900)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--compare-with", default=None, help="previous GATE1_VERDICT_C.json: compare_guard refuses items whose input shas differ (Δ44-R38)")
    a = ap.parse_args(argv)
    if a.dry_run:
        a.sut = a.sut or str(C_WORKTREE)
        a.sha = a.sha or (git(C_WORKTREE, "rev-parse", "HEAD") or "UNKNOWN")
        a.out = a.out or str(HERE / "out" / "dry_run")
    for k in ("sut", "sha", "out"):
        if not getattr(a, k):
            ap.error(f"--{k} is required unless --dry-run")
    c = Ctx(a)
    c.out.mkdir(parents=True, exist_ok=True)
    if c.runner_cmd and not all(t in c.runner_cmd for t in ("{fixture}", "{out}")):
        ap.error("--runner-cmd must contain {fixture} and {out} (and normally {contract})")

    sut_head = git(c.sut, "rev-parse", "HEAD")
    shas = {"generated_at_kst": now_kst(), "sut_root": str(c.sut), "sut_sha_claimed": c.sha, "sut_head": sut_head,
            "sut_tree": git(c.sut, "rev-parse", "HEAD^{tree}"), "sut_dirty": bool(git(c.sut, "status", "--porcelain")),
            "sut_matches_claim": bool(sut_head and c.sha and sut_head.startswith(c.sha)),
            "c_head": git(C_WORKTREE, "rev-parse", "HEAD"), "c_gate1_tree": git(C_WORKTREE, "rev-parse", "HEAD:research/landing_accessibility/assurance/gate1"),
            "c_gate1_dirty": bool(git(C_WORKTREE, "status", "--porcelain", str(HERE))),
            "control_sha": a.control_sha or git(C_WORKTREE, "rev-parse", "--verify", "control/landing-orchestrator") or "UNRESOLVED",
            "ssot_snapshot_sha": a.ssot_snapshot_sha, "e001_ref_sha": c.ref_sha, "python": c.py}
    if COMPARATORS_ERR:
        c.add(id="comparators-import", lane="gate1", kind="C_INTERNAL", status="ERROR", reason=COMPARATORS_ERR,
              description="gate1/comparators package import (adapter_map, compare_lane1-3, grade_lane4)", verifies="-")
    # lane order: safety first (lane4), then binding (lane1), flow fixtures (lane2/3/7), evidence (lane5), stats (lane6)
    for fn in (lane4, lane1, lane2, lane3, lane7, lane5, lane6):
        try:
            fn(c)
        except Exception as e:  # a lane driver crash is a C harness defect, recorded not raised
            c.add(id=f"{fn.__name__}-driver", lane=fn.__name__, kind="C_INTERNAL", status="ERROR",
                  reason=f"{type(e).__name__}: {e}"[:300], description="lane driver raised", verifies="-")
    verdict = evaluate(c)
    if not shas["sut_matches_claim"] and not c.dry_run:
        verdict["warnings"] = [f"SUT HEAD {sut_head} does not match claimed --sha {c.sha}: verdict is about HEAD, not the claim"]
    top = top_level_identity(c)
    guard = compare_guard(c, top)
    doc = {"artifact": "GATE1_VERDICT_C", "runner": "run_gate1.py", "dry_run": c.dry_run, "shas": shas,
           "runner_cmd": c.runner_cmd, "adapter_map": c.adapter_map_path, **verdict,
           "next_automatic_action": next_action(verdict["verdict"]), "declared_failure_behaviour": DECLARED_FAILURE_BEHAVIOUR,
           "failure_behaviour_demo": failure_demo_binding(), "sut_status": ("SUT_CONFIRMED:" + args.sut_sha) if getattr(args, "sut_sha", None) else "SUT_UNCONFIRMED (Δ50-sut)",
        "input_identity": top, "compare_guard": guard, "items": c.items}
    # report first, verdict last: a crash anywhere before this line leaves NO verdict file (declared failure behaviour (2))
    write_report(c, verdict, shas, c.out / "GATE1_REPORT_C.md", top, guard)
    (c.out / "GATE1_VERDICT_C.json").write_text(json.dumps(doc, ensure_ascii=False, indent=1, default=str) + "\n", encoding="utf-8")
    summary = {k: doc[k] for k in ("verdict", "exit_code", "usable", "counts", "n_items", "hard_stop_triggers_observed",
                                   "systemic_defects", "c_harness_defects", "not_testable_items", "coverage")}
    summary["failure_behaviour_demo"] = {k: doc["failure_behaviour_demo"][k] for k in ("valid_for_this_commit", "reason")}
    print(json.dumps(summary, ensure_ascii=False, indent=1))
    print(f"wrote {c.out / 'GATE1_VERDICT_C.json'} and GATE1_REPORT_C.md")
    return verdict["exit_code"]


if __name__ == "__main__":
    try:
        _rc = main()
    except Exception:  # Δ46-exit2: did not run ≠ failed; no verdict file has been written at this point
        import traceback
        traceback.print_exc()
        print(DID_NOT_RUN_MSG, file=sys.stderr)
        _rc = 2
    sys.exit(_rc)
