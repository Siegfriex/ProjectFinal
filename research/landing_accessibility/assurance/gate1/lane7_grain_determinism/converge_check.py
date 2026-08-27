#!/usr/bin/env python3
"""converge_check.py — runs impl_a (PROBE) and impl_b (DOM_AX) on every fixture at all three units × two
populations and prints a row-by-row table. PASS only if every row is identical (canonical JSON equality).
Writes out/converge_rows_{a,b}.jsonl and out/converge_result.json."""
from __future__ import annotations
import json, sys, pathlib
HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import impl_a, impl_b

PROBE = {"f01": "f01_blocking_modal_visible_close.html", "f02": "f02_overlay_control_hidden.html",
         "f03": "f03_overlay_control_after_scroll.html", "f04": "f04_two_overlays_one_blocking.html", "f05": "f05_no_overlay.html"}
FIELDS = ["dismiss_control_exists", "dismiss_control_visible", "dismiss_control_accessible_name", "dismiss_required_for_task",
          "task_control_occlusion", "dismiss_control_hittable_s0", "selected_selector"]
def short(v):
    if v is None:
        return "NULL"
    if isinstance(v, bool):
        return "T" if v else "F"
    if isinstance(v, float):
        return f"{v:.3f}"
    return str(v)


MUTATIONS = {  # negative control: in-memory perturbations of the PROBE input that MUST surface as DIFF rows
    "f01": lambda p: p["raw_features"]["dismiss_control_candidates"][0]["dismiss_control_candidates"][0].update(visible=False),
    "f04": lambda p: p["raw_features"]["dismiss_control_candidates"][1].update(z_index=100),   # flips dismissal order
    "f05": lambda p: p["raw_features"]["dismiss_control_candidates"].append(
        {"container_selector": "#phantom", "container_role": None, "aria_modal": False, "z_index": 1, "bbox": [0, 0, 10, 10],
         "dom_order": 9, "dismiss_control_candidates": []}),                                      # phantom container, no control
}


def canon(r):
    return json.dumps(r, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def key(r):
    return (r["fixture"], r["unit"], r["population"], r["row_id"])


def main():
    negative = "--negative-control" in sys.argv
    out = HERE / "out"; out.mkdir(exist_ok=True)
    tag = "negctrl" if negative else "converge"
    A, B = {}, {}
    for k, fx in PROBE.items():
        probe = json.loads((HERE / "probe_like" / f"{k}.json").read_text(encoding="utf-8"))
        if negative and k in MUTATIONS:
            MUTATIONS[k](probe)
        for r in impl_a.run_probe(probe):
            A[key(r)] = r
        for r in impl_b.run(HERE / "fixtures" / fx):
            B[key(r)] = r
    (out / f"{tag}_rows_a.jsonl").write_text("\n".join(canon(A[k]) for k in sorted(A)) + "\n", encoding="utf-8")
    (out / f"{tag}_rows_b.jsonl").write_text("\n".join(canon(B[k]) for k in sorted(B)) + "\n", encoding="utf-8")
    keys = sorted(set(A) | set(B), key=lambda k: (k[0], ["target", "container", "step"].index(k[1]), k[2], k[3]))
    hdr = ["fixture", "unit", "pop", "row", "exists", "visible", "acc_name", "required", "occl", "hittable", "selected", "A==B"]
    lines = [" | ".join(hdr)]
    n_ok = n_bad = 0
    diffs = []
    for k in keys:
        a, b = A.get(k), B.get(k)
        same = a is not None and b is not None and canon(a) == canon(b)
        n_ok += same; n_bad += (not same)
        src = a or b
        cells = [k[0][:3], k[1], k[2], k[3]] + [short(src[f]) for f in FIELDS] + ["ok" if same else "DIFF"]
        lines.append(" | ".join(str(c) for c in cells))
        if not same:
            diffs.append({"key": k, "A": a, "B": b, "differing_fields": [f for f in FIELDS if (a or {}).get(f) != (b or {}).get(f)]})
    n_units = {u: sum(1 for k in keys if k[1] == u) for u in ("target", "container", "step")}
    verdict = "PASS" if n_bad == 0 and n_ok > 0 else "FAIL"
    if negative:   # control group: the check must FAIL, and every mutated fixture must show at least one DIFF row
        hit = {k for k in MUTATIONS if any(d["key"][0].startswith(k) for d in diffs)}
        verdict = "NEGCTRL_OK(check detects disagreement)" if hit == set(MUTATIONS) else f"NEGCTRL_BROKEN(missed {set(MUTATIONS) - hit})"
    print("\n".join(lines))
    print(f"\nmode={'NEGATIVE-CONTROL' if negative else 'CONVERGE'} rows compared={n_ok + n_bad} identical={n_ok} differing={n_bad} per-unit={n_units} -> {verdict}")
    for d in diffs:
        print("DIFF", json.dumps(d, ensure_ascii=False))
    (out / f"{tag}_result.json").write_text(json.dumps({"verdict": verdict, "rows": n_ok + n_bad, "identical": n_ok, "differing": n_bad,
                                                          "per_unit": n_units, "diffs": diffs}, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    sys.exit(0 if verdict.startswith(("PASS", "NEGCTRL_OK")) else 1)


if __name__ == "__main__":
    main()
