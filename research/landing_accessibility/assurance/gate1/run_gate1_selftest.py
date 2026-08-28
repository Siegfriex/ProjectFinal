#!/usr/bin/env python3
"""run_gate1_selftest.py — controls for the Δ44-R38 input-identity fields written by run_gate1.py.

must_not_flag  re-running run_gate1.py --dry-run --skip-browser on unchanged inputs yields byte-identical sha fields
               (top level, per lane, per item) and identical verdict counts.
must_flag      flipping ONE byte in one lane2 fixture (in a scratch copy of assurance/, never in the worktree) changes
               that lane's fixtures_dir_manifest_sha256 and only that lane's; every other sha field is unchanged.
guard          --compare-with a previous verdict: unchanged inputs ⇒ every shared item comparable, 0 refused;
               a previous verdict whose lane3 fixtures sha differs ⇒ exactly the lane3 items are refused.
recompute      one lane manifest aggregate + one listed file sha re-derived with `sha256sum` (independent tool).
fetch_fail     control_identity on a non-repo path ⇒ fetch_ok False, index/delta shas UNAVAILABLE (no local fallback).
declared       (Δ46) the clean run carries `declared_failure_behaviour` (3 keys), `usable` true and a `failure_behaviour_demo` block.
harness_defect (Δ46 behaviour 1) lane1 selfcheck.py mutated to FAIL in the scratch copy ⇒ verdict C_HARNESS_DEFECT, usable false,
               counts.PASS 0, every other item NOT_TESTABLE reason `harness_defect` with status_before_harness_defect kept; file written; exit 1.
crash          (Δ46 behaviour 2 / Δ46-exit2) evaluate() raises in the scratch copy ⇒ exit 2, did-not-run message, a pre-seeded
               GATE1_VERDICT_C.json at --out left byte-identical (sha256sum).

    python3 run_gate1_selftest.py [--work <scratch dir>]
Exit 0 iff every control holds. Prints one JSON line per control.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import shutil
import subprocess
import sys
import tempfile

HERE = pathlib.Path(__file__).resolve().parent
ASSURANCE = HERE.parent
sys.path.insert(0, str(HERE))
import run_gate1 as rg  # noqa: E402

RESULTS: list[dict] = []


def ctl(name: str, ok: bool, **detail) -> bool:
    rec = {"control": name, "result": "OK" if ok else "VIOLATED", **detail}
    RESULTS.append(rec)
    print(json.dumps(rec, ensure_ascii=False, default=str))
    return ok


def run(script: pathlib.Path, out: pathlib.Path, extra: list[str] | None = None) -> dict:
    cmd = [sys.executable, str(script), "--dry-run", "--skip-browser", "--out", str(out), *(extra or [])]
    p = subprocess.run(cmd, capture_output=True, text=True, timeout=1800)
    doc = json.loads((out / "GATE1_VERDICT_C.json").read_text(encoding="utf-8"))
    doc["_rc"] = p.returncode
    return doc


def sha_fields(doc: dict) -> dict:
    """Every sha field the tool writes, as one flat dict (paths excluded — a scratch copy has different paths)."""
    top = doc["input_identity"]
    flat = {f"top.{k}": top.get(k) for k in rg.TOP_SHA_FIELDS}
    for ln, v in top["lanes"].items():
        for k in ("fixtures_dir_manifest_sha256", "expectations_file_sha256", "expectations_dir_manifest_sha256", "contracts_file_sha256"):
            flat[f"lane.{ln}.{k}"] = v.get(k)
    for it in doc["items"]:
        for k in rg.ITEM_SHA_FIELDS:
            flat[f"item.{it['id']}.{k}"] = (it.get("input_identity") or {}).get(k)
    return flat


def diff(a: dict, b: dict) -> list[str]:
    return sorted(k for k in set(a) | set(b) if a.get(k) != b.get(k))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--work", default=None)
    a = ap.parse_args()
    work = pathlib.Path(a.work).resolve() if a.work else pathlib.Path(tempfile.mkdtemp(prefix="gate1_selftest_"))
    work.mkdir(parents=True, exist_ok=True)
    ok = True

    # --- must_not_flag: two in-place runs on unchanged inputs
    A = run(HERE / "run_gate1.py", work / "run_a")
    B = run(HERE / "run_gate1.py", work / "run_b")
    d_ab = diff(sha_fields(A), sha_fields(B))
    ok &= ctl("must_not_flag", not d_ab and A["counts"] == B["counts"] and A["n_items"] == B["n_items"],
              counts=A["counts"], n_items=A["n_items"], n_sha_fields=len(sha_fields(A)), differing_fields=d_ab,
              control_ref_commit_sha=A["input_identity"]["control_ref_commit_sha"], fetch_ok=A["input_identity"]["fetch_ok"])

    # --- must_flag: scratch copy of assurance/ (depth 4 so HERE.parents[3] exists), one byte flipped in one lane2 fixture
    croot = work / "copy" / "l1" / "l2" / "l3"
    shutil.rmtree(work / "copy", ignore_errors=True)
    shutil.copytree(ASSURANCE, croot / "assurance",
                    ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "intake", "out"))
    fx = croot / "assurance" / "gate1" / "lane2_label_reveal" / "fixtures" / "drawer_left.html"
    raw = bytearray(fx.read_bytes()); raw[-1] ^= 0x01; fx.write_bytes(bytes(raw))
    M = run(croot / "assurance" / "gate1" / "run_gate1.py", work / "run_mut")
    d_am = diff(sha_fields(A), sha_fields(M))
    lane2_ids = {i["id"] for i in A["items"] if i["lane"] == "lane2"}
    expected = {"lane.lane2.fixtures_dir_manifest_sha256"} | {f"item.{i}.fixtures_dir_manifest_sha256" for i in lane2_ids}
    ok &= ctl("must_flag", set(d_am) == expected and len(lane2_ids) > 0,
              mutated_file=str(fx), differing_fields=d_am, expected_differing_fields=sorted(expected),
              lane2_sha_before=A["input_identity"]["lanes"]["lane2"]["fixtures_dir_manifest_sha256"],
              lane2_sha_after=M["input_identity"]["lanes"]["lane2"]["fixtures_dir_manifest_sha256"], counts_in_copy=M["counts"])

    # --- guard: compare_guard with an unchanged previous, then with a doctored previous (lane3 fixtures sha changed)
    G1 = run(HERE / "run_gate1.py", work / "run_g1", ["--compare-with", str(work / "run_a" / "GATE1_VERDICT_C.json")])
    g = G1["compare_guard"]
    ok &= ctl("guard_unchanged_inputs", g["enabled"] and g["usable"] and g["top_level_identity_match"] and g["n_refused"] == 0
              and g["n_comparable"] == A["n_items"] and not g["status_changed_items"],
              n_comparable=g["n_comparable"], n_refused=g["n_refused"], top_level_mismatched_fields=g["top_level_mismatched_fields"])
    prev = json.loads((work / "run_a" / "GATE1_VERDICT_C.json").read_text(encoding="utf-8"))
    for it in prev["items"]:
        if it["lane"] == "lane3":
            it["input_identity"]["fixtures_dir_manifest_sha256"] = "0" * 64
    pp = work / "prev_doctored.json"; pp.write_text(json.dumps(prev, ensure_ascii=False), encoding="utf-8")
    G2 = run(HERE / "run_gate1.py", work / "run_g2", ["--compare-with", str(pp)])
    g2 = G2["compare_guard"]
    lane3_ids = sorted(i["id"] for i in A["items"] if i["lane"] == "lane3")
    ok &= ctl("guard_refuses_differing_inputs", sorted(g2["refused_items"]) == lane3_ids and g2["n_comparable"] == A["n_items"] - len(lane3_ids)
              and all(g2["items"][i]["status_changed"] is None for i in lane3_ids),
              refused_items=g2["refused_items"], expected_refused=lane3_ids, n_comparable=g2["n_comparable"])
    rep = (work / "run_g2" / "GATE1_REPORT_C.md").read_text(encoding="utf-8")
    ok &= ctl("guard_in_report", "## 9. compare_guard" in rep and all(f"`{i}`: refused" in rep for i in lane3_ids))

    # --- recompute: manifest aggregate + one listed file sha via sha256sum (independent of hashlib)
    mtxt = work / "run_a" / "input_identity" / "lane7_fixtures_dir.manifest.txt"
    agg = subprocess.check_output(["sha256sum", str(mtxt)], text=True).split()[0]
    first_rel, first_sha = mtxt.read_text(encoding="utf-8").splitlines()[0].split("\t")
    fsha = subprocess.check_output(["sha256sum", str(HERE / "lane7_grain_determinism" / "fixtures" / first_rel)], text=True).split()[0]
    ok &= ctl("recompute_with_sha256sum", agg == A["input_identity"]["lanes"]["lane7"]["fixtures_dir_manifest_sha256"] and fsha == first_sha,
              manifest=str(mtxt), aggregate_sha256sum=agg, first_file=first_rel, first_file_sha256sum=fsha)
    me = subprocess.check_output(["sha256sum", str(HERE / "run_gate1.py")], text=True).split()[0]
    ok &= ctl("run_gate1_file_sha256_matches_sha256sum", me == A["input_identity"]["run_gate1_file_sha256"], sha256sum=me)

    # --- fetch_fail: no repo ⇒ UNAVAILABLE, never a local fallback
    ci = rg.control_identity(work / "not_a_repo")
    ok &= ctl("fetch_fail_is_unavailable", (not ci["fetch_ok"]) and ci["ruling_index_bytes_sha256"] == "UNAVAILABLE"
              and ci["delta_bytes_sha256"] == "UNAVAILABLE" and ci["control_ref_commit_sha"] is None and bool(ci["fetch_error"]),
              fetch_error=ci["fetch_error"], control_ref=ci["control_ref"])

    # --- declared (Δ46): declaration + R40 binding block present on the clean run, usable true
    fbd = A.get("failure_behaviour_demo") or {}
    dfb = A.get("declared_failure_behaviour") or {}
    ok &= ctl("declared_failure_behaviour_present", A.get("usable") is True and {"internal_control_fails", "aggregator_crash", "normal"} <= set(dfb)
              and {"valid_for_this_commit", "reason", "tool_sha256_now", "sidecar_tool_sha256"} <= set(fbd) and A["_rc"] == A["exit_code"],
              usable=A.get("usable"), declared_keys=sorted(dfb), demo_valid_for_this_commit=fbd.get("valid_for_this_commit"), demo_reason=fbd.get("reason"))

    # --- harness_defect (Δ46 behaviour 1): lane1 selfcheck mutated to FAIL in the scratch copy (never in the worktree)
    sc = croot / "assurance" / "gate1" / "lane1_task_binding" / "selfcheck.py"
    s = sc.read_text(encoding="utf-8"); anchor = '    status = "PASS" if not fails else "FAIL"\n'
    assert s.count(anchor) == 1, "lane1 selfcheck anchor not found"
    sc.write_text(s.replace(anchor, '    fails.append("injected internal-control failure (run_gate1_selftest)")\n' + anchor), encoding="utf-8")
    H = run(croot / "assurance" / "gate1" / "run_gate1.py", work / "run_hd")
    others = [i for i in H["items"] if i["id"] not in H["c_harness_defects"]]
    ok &= ctl("harness_defect_verdict_unusable_zero_pass", H["_rc"] == 1 and H["verdict"] == "C_HARNESS_DEFECT" and H["usable"] is False
              and H["c_harness_defects"] == ["L1-selfcheck"] and H["counts"]["PASS"] == 0 and len(others) == H["n_items"] - 1
              and all(i["status"] == "NOT_TESTABLE" and i["reason"] == rg.HARNESS_DEFECT_REASON and "status_before_harness_defect" in i for i in others)
              and sorted(H["neutralised_items"]) == sorted(i["id"] for i in others),
              rc=H["_rc"], verdict=H["verdict"], usable=H["usable"], counts=H["counts"], c_harness_defects=H["c_harness_defects"],
              n_neutralised=len(H["neutralised_items"]), statuses_before=sorted({i["status_before_harness_defect"] for i in others}))

    # --- crash (Δ46 behaviour 2 / Δ46-exit2): evaluate() raises in the scratch copy ⇒ exit 2, nothing written
    rgp = croot / "assurance" / "gate1" / "run_gate1.py"
    s = rgp.read_text(encoding="utf-8"); anchor = "def evaluate(c: Ctx) -> dict:\n    items = c.items\n"
    assert s.count(anchor) == 1, "evaluate anchor not found"
    rgp.write_text(s.replace(anchor, "def evaluate(c: Ctx) -> dict:\n    raise RuntimeError('injected crash (run_gate1_selftest)')\n    items = c.items\n"),
                   encoding="utf-8")
    cdir = work / "run_crash"; cdir.mkdir(parents=True, exist_ok=True)
    vf = cdir / "GATE1_VERDICT_C.json"; vf.write_text('{"sentinel": "pre-existing verdict file; must be left byte-identical on a crash"}\n', encoding="utf-8")
    before = subprocess.check_output(["sha256sum", str(vf)], text=True).split()[0]
    p = subprocess.run([sys.executable, str(rgp), "--dry-run", "--skip-browser", "--out", str(cdir)], capture_output=True, text=True, timeout=1800)
    after = subprocess.check_output(["sha256sum", str(vf)], text=True).split()[0]
    ok &= ctl("crash_exits_2_writes_no_verdict", p.returncode == 2 and before == after and rg.DID_NOT_RUN_MSG in p.stderr,
              rc=p.returncode, sentinel_sha_before=before, sentinel_sha_after=after, stderr_last=p.stderr.strip().splitlines()[-1:])

    print(json.dumps({"selftest": "run_gate1_selftest", "work": str(work), "all_ok": bool(ok),
                      "controls": {r["control"]: r["result"] for r in RESULTS}}, ensure_ascii=False))
    return 0 if ok else 1


if __name__ == "__main__":
    try:
        _rc = main()
    except Exception:  # Δ46-exit2 / Δ50-exit2-common: crash or missing input = did not run, never exit 1 (ran and failed)
        import traceback
        traceback.print_exc()
        print("run_gate1_selftest: did not run — read neither as pass nor fail (exit 2)", file=sys.stderr)
        _rc = 2
    sys.exit(_rc)
