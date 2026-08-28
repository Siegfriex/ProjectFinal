#!/usr/bin/env python3
"""r32_selftest.py — proves r32_inventory.py's controls, its refusal path, and its fixtures, before any target run.

Steps (all must pass; exit 0 only then):
  S1  in-process controls on fixtures_py/ → every CONTROL PASS; per-fixture site / flagged / out_of_unit counts printed.
  S2  fixtures behave as their controls claim (exec'd from path, never imported into production):
        measure_surface(non-dict | {} | {"envelope": "x"}) raises ShapeError; well-formed → value;
        bind_task({}) is None and bind_task({"ax_node": None}) is None  (absent ≡ wrong shape — the violation);
        score({"envelope": {"raw": 3}}) == 6, score({}) raises KeyError; add(1, 2) == 3.
  S3  refusal path — the tool run as a subprocess with a tampered fixtures dir (must_flag ax_node fixture made to
      raise; separately must_not_flag surface fixture with its raise removed) exits 2 and writes NOTHING.
  S4  happy path — subprocess with the real fixtures, --target fixtures_py, --out → exit 0, file exists, schema keys.
  S5  exit 3 on an unusable target (empty dir).
  S6  smoke run on C's own gate1/comparators (real code, no expectation, counts only — not a claim about anything).

Prints a JSON summary on stdout; human lines on stderr.
"""
from __future__ import annotations

import importlib.util
import json
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile

HERE = pathlib.Path(__file__).resolve().parent
TOOL = HERE / "r32_inventory.py"
FIXTURES = HERE / "fixtures_py"
SCRATCH = pathlib.Path(os.environ.get("R32_SCRATCH", tempfile.mkdtemp(prefix="r32_selftest_")))

sys.path.insert(0, str(HERE))
import r32_inventory as inv  # noqa: E402


def log(msg: str) -> None:
    print(msg, file=sys.stderr)


def load_fixture(name: str):
    spec = importlib.util.spec_from_file_location(f"_r32fx_{name}", FIXTURES / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


def expect_raises(fn, exc_type, *args) -> bool:
    try:
        fn(*args)
    except exc_type:
        return True
    except Exception:
        return False
    return False


def run_tool(args: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(TOOL), *args], capture_output=True, text=True)


def main() -> int:
    summary: dict = {"steps": {}, "all_pass": False, "scratch": str(SCRATCH)}
    SCRATCH.mkdir(parents=True, exist_ok=True)

    # S1 — controls in-process
    ok1, controls, scan = inv.run_controls(FIXTURES)
    summary["steps"]["S1_controls"] = {"pass": ok1, "n_pass": sum(c["result"] == "PASS" for c in controls), "n": len(controls),
                                        "controls": controls, "per_fixture": scan["per_file"], "counts": scan["counts"]}
    log(f"S1 controls: {sum(c['result'] == 'PASS' for c in controls)}/{len(controls)} PASS")
    inv.print_controls(controls)
    for f, c in scan["per_file"].items():
        log(f"  fixture {f}: functions={c['functions']} sites={c['sites']} flagged={c['flagged']} out_of_unit={c['out_of_unit']}")

    # S2 — fixtures behave as claimed
    s2: dict[str, bool] = {}
    surf = load_fixture("ctrl_must_not_flag_surface")
    s2["measure_surface(non_dict)_raises_ShapeError"] = expect_raises(surf.measure_surface, surf.ShapeError, "not-a-dict")
    s2["measure_surface({})_raises_ShapeError"] = expect_raises(surf.measure_surface, surf.ShapeError, {})
    s2["measure_surface(envelope_wrong_shape)_raises_ShapeError"] = expect_raises(surf.measure_surface, surf.ShapeError, {"envelope": "x"})
    s2["measure_surface(absent_raw_features)_is_None_with_reason"] = surf.measure_surface({"envelope": {}}) == {"observed": None, "reason": "raw_features absent"}
    s2["measure_surface(well_formed)_value"] = surf.measure_surface({"envelope": {"raw_features": [1, 2]}}) == {"observed": 2, "reason": None}
    ax = load_fixture("ctrl_must_flag_ax_node")
    s2["bind_task({})_is_None"] = ax.bind_task({}) is None
    s2["bind_task(ax_node_None)_is_None_same_as_absent"] = ax.bind_task({"ax_node": None}) is None
    s2["bind_task(well_formed)_value"] = ax.bind_task({"ax_node": {"role": "button"}}) == {"role": "button", "name": ""}
    oou = load_fixture("ctrl_out_of_unit_nested")
    s2["score(well_formed)==6"] = oou.score({"envelope": {"raw": 3}}) == 6
    s2["score({})_raises_KeyError"] = expect_raises(oou.score, KeyError, {})
    clean = load_fixture("ctrl_clean")
    s2["add(1,2)==3"] = clean.add(1, 2) == 3
    ok2 = all(s2.values())
    summary["steps"]["S2_fixture_behaviour"] = {"pass": ok2, "checks": s2}
    log(f"S2 fixture behaviour: {sum(s2.values())}/{len(s2)} PASS")

    # S3 — refusal path (tampered controls) — the control of the control
    s3: dict[str, dict] = {}
    for tag, fname, old, new in (
        ("tamper_must_flag_ax_node_now_raises", "ctrl_must_flag_ax_node.py",
         "    if node is None:\n        return None\n", "    if node is None:\n        raise TypeError('ax_node missing')\n"),
        ("tamper_must_not_flag_surface_raise_removed", "ctrl_must_not_flag_surface.py",
         "    if not isinstance(probe_state, dict):\n        raise ShapeError(f\"probe_state must be a dict, got {type(probe_state).__name__}\")\n"
         "    if \"envelope\" not in probe_state:\n        raise ShapeError(\"probe_state has no 'envelope'\")\n"
         "    envelope = probe_state[\"envelope\"]\n    if not isinstance(envelope, dict):\n        raise ShapeError(\"probe_state['envelope'] must be a dict\")\n",
         "    envelope = probe_state.get(\"envelope\") or {}\n"),
    ):
        tdir = SCRATCH / tag
        if tdir.exists():
            shutil.rmtree(tdir)
        shutil.copytree(FIXTURES, tdir, ignore=shutil.ignore_patterns("__pycache__"))
        src = (tdir / fname).read_text(encoding="utf-8")
        assert old in src, f"selftest tamper anchor missing in {fname}"
        (tdir / fname).write_text(src.replace(old, new), encoding="utf-8")
        out = SCRATCH / f"{tag}.json"
        if out.exists():
            out.unlink()
        cp = run_tool(["--target", str(FIXTURES), "--fixtures-dir", str(tdir), "--out", str(out)])
        failed = [ln.strip() for ln in cp.stderr.splitlines() if ln.strip().startswith("FAIL")]
        s3[tag] = {"exit_code": cp.returncode, "output_written": out.exists(), "failed_controls": failed,
                   "pass": cp.returncode == 2 and not out.exists() and bool(failed)}
        log(f"S3 {tag}: exit={cp.returncode} written={out.exists()} failed_controls={len(failed)}")
    ok3 = all(v["pass"] for v in s3.values())
    summary["steps"]["S3_refusal_path"] = {"pass": ok3, "runs": s3}

    # S4 — happy path via subprocess
    out4 = SCRATCH / "r32_inventory_fixtures.json"
    if out4.exists():
        out4.unlink()
    cp4 = run_tool(["--target", str(FIXTURES), "--out", str(out4), "--label", "selftest"])
    keys_needed = ["measured_at_kst", "target_root", "target_sha", "unit_predicate", "out_of_unit_predicate", "sites",
                   "out_of_unit_candidates", "counts", "controls", "ordering_record"]
    doc = json.loads(out4.read_text(encoding="utf-8")) if out4.exists() else {}
    missing = [k for k in keys_needed if k not in doc]
    ok4 = cp4.returncode == 0 and out4.exists() and not missing and doc.get("controls_all_pass") is True
    summary["steps"]["S4_happy_path"] = {"pass": ok4, "exit_code": cp4.returncode, "output_written": out4.exists(), "missing_keys": missing,
                                          "counts": doc.get("counts"), "target_sha": doc.get("target_sha"), "out": str(out4)}
    log(f"S4 happy path: exit={cp4.returncode} written={out4.exists()} missing_keys={missing}")

    # S5 — exit 3 on an unusable target
    empty = SCRATCH / "empty_target"
    empty.mkdir(exist_ok=True)
    cp5 = run_tool(["--target", str(empty), "--out", str(SCRATCH / "never.json")])
    ok5 = cp5.returncode == 3 and not (SCRATCH / "never.json").exists()
    summary["steps"]["S5_unusable_target"] = {"pass": ok5, "exit_code": cp5.returncode}
    log(f"S5 unusable target: exit={cp5.returncode}")

    # S6 — smoke run on C's own comparators (counts only, no expectation)
    comp = HERE.parent / "comparators"
    out6 = SCRATCH / "r32_inventory_smoke_comparators.json"
    cp6 = run_tool(["--target", str(comp), "--out", str(out6), "--label", "selftest-smoke"])
    doc6 = json.loads(out6.read_text(encoding="utf-8")) if out6.exists() else {}
    summary["steps"]["S6_smoke_comparators"] = {"pass": cp6.returncode == 0, "exit_code": cp6.returncode, "counts": doc6.get("counts"), "out": str(out6)}
    log(f"S6 smoke comparators: exit={cp6.returncode} counts={json.dumps(doc6.get('counts', {}).get('sites_by_handling'))}")

    summary["all_pass"] = all(v["pass"] for v in summary["steps"].values())
    print(json.dumps(summary, ensure_ascii=False, indent=1))
    log(f"r32_selftest: {'ALL PASS' if summary['all_pass'] else 'FAIL'} (scratch {SCRATCH})")
    return 0 if summary["all_pass"] else 1


if __name__ == "__main__":
    try:
        _rc = main()
    except Exception:  # Δ46-exit2 / Δ50-exit2-common: crash or missing input = did not run, never exit 1 (ran and failed)
        import traceback
        traceback.print_exc()
        print("r32_selftest: did not run — read neither as pass nor fail (exit 2)", file=sys.stderr)
        _rc = 2
    sys.exit(_rc)
