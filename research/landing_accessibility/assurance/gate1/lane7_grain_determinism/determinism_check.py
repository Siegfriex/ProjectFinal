#!/usr/bin/env python3
"""determinism_check.py — runner-agnostic route-policy determinism test (GATE 1 must_include 4).

Usage:
  determinism_check.py --cmd "<template with {fixture} and {out}>" --fixture F.html [--n 3] [--label NAME]
                       [--policy-doc POLICY.md]

Runs the command N times on the SAME fixture; each run must write a sequence JSON to {out}. From each JSON it
extracts (1) task_flow_sequence, (2) experienced_flow_sequence, (3) the ordered list of selected control
selectors (steps[*].control_selector, or selected_controls). Each is serialised canonically and hashed.
PASS iff every run yields byte-identical serialisations for all three. The raw file hash is shown for
information only (timestamps etc. are allowed to differ). --policy-doc prints the sha256 of the route-policy
document so the GATE record binds the result to a frozen policy text. Exit 0 = PASS, 1 = FAIL, 2 = usage/runner error."""
from __future__ import annotations
import argparse, hashlib, json, pathlib, shlex, subprocess, sys, time

FIELDS = ("task_flow_sequence", "experienced_flow_sequence", "selected_control_selectors")


def canon(v):
    return json.dumps(v, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def sha(b):
    return hashlib.sha256(b).hexdigest()


def extract(doc):
    if "selected_control_selectors" in doc:
        sels = doc["selected_control_selectors"]
    elif "steps" in doc:
        sels = [s.get("control_selector") for s in doc["steps"]]
    else:
        sels = doc.get("selected_controls")
    return {"task_flow_sequence": doc.get("task_flow_sequence"),
            "experienced_flow_sequence": doc.get("experienced_flow_sequence"),
            "selected_control_selectors": sels}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cmd", required=True); ap.add_argument("--fixture", required=True)
    ap.add_argument("--n", type=int, default=3); ap.add_argument("--label", default="run")
    ap.add_argument("--workdir", default=str(pathlib.Path(__file__).resolve().parent / "out"))
    ap.add_argument("--policy-doc", default=None)
    a = ap.parse_args()
    wd = pathlib.Path(a.workdir) / f"det_{a.label}"; wd.mkdir(parents=True, exist_ok=True)
    fixture = str(pathlib.Path(a.fixture).resolve())
    runs = []
    for i in range(a.n):
        out = wd / f"seq_{i}.json"
        if out.exists():
            out.unlink()
        cmd = a.cmd.format(fixture=shlex.quote(fixture), out=shlex.quote(str(out)))
        t0 = time.time()
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        if r.returncode != 0 or not out.exists():
            print(f"run {i}: runner failed rc={r.returncode} stderr={r.stderr[-400:]}"); sys.exit(2)
        raw = out.read_bytes()
        doc = json.loads(raw.decode("utf-8"))
        ex = extract(doc)
        missing = [f for f in FIELDS if ex[f] is None]
        if missing:
            print(f"run {i}: sequence JSON lacks {missing}"); sys.exit(2)
        runs.append({"run": i, "elapsed_s": round(time.time() - t0, 3), "raw_sha256": sha(raw),
                     **{f: sha(canon(ex[f])) for f in FIELDS}, "values": ex})
    verdict = "PASS"
    per_field = {}
    for f in FIELDS:
        distinct = sorted({r[f] for r in runs})
        per_field[f] = len(distinct)
        if len(distinct) != 1:
            verdict = "FAIL"
    raw_distinct = len({r["raw_sha256"] for r in runs})
    hdr = "run | task_flow sha8 | experienced_flow sha8 | selectors sha8 | raw file sha8 | experienced_flow"
    print(hdr)
    for r in runs:
        print(f"{r['run']} | {r['task_flow_sequence'][:8]} | {r['experienced_flow_sequence'][:8]} | "
              f"{r['selected_control_selectors'][:8]} | {r['raw_sha256'][:8]} | {' > '.join(r['values']['experienced_flow_sequence'])}")
    print(f"label={a.label} n={a.n} distinct-per-field={per_field} raw-file-distinct={raw_distinct} (informational) -> {verdict}")
    rec = {"label": a.label, "cmd": a.cmd, "fixture": fixture, "n": a.n, "verdict": verdict, "distinct_per_field": per_field,
           "raw_file_distinct": raw_distinct, "runs": runs}
    if a.policy_doc:
        pd = pathlib.Path(a.policy_doc)
        rec["policy_doc"] = {"path": str(pd), "sha256": sha(pd.read_bytes())}
        print(f"policy_doc={pd.name} sha256={rec['policy_doc']['sha256']}")
    (wd / "result.json").write_text(json.dumps(rec, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    sys.exit(0 if verdict == "PASS" else 1)


if __name__ == "__main__":
    try:
        _rc = main()
    except Exception:  # Δ46-exit2 / Δ50-exit2-common: crash or missing input = did not run, never exit 1 (ran and failed)
        import traceback
        traceback.print_exc()
        print("determinism_check: did not run — read neither as pass nor fail (exit 2)", file=sys.stderr)
        _rc = 2
    sys.exit(_rc)
