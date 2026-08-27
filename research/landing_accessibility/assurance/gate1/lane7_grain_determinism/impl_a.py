#!/usr/bin/env python3
"""impl_A — source axis = PROBE.
Reads a probe-like JSON (raw_features.dismiss_control_candidates = list of containers, each with a
dismiss_control_candidates list of {selector, hittable, visible, accessible_name, bbox, ...}) and derives the
dismiss_control_exists family at target / container / step units for populations all / blocking.
Standalone on purpose: shares no code with impl_b.py (DISMISS_DEFINITION_C.md §3 PROBE mapping, §4-§6)."""
from __future__ import annotations
import json, sys, pathlib

VIEW = (0, 0, 390, 844)
ABSENT = "NAME_ABSENT"
OUT = ("dismiss_control_exists", "dismiss_control_visible", "dismiss_control_accessible_name",
       "dismiss_required_for_task", "task_control_occlusion", "dismiss_control_hittable_s0", "selected_selector")


def inter(a, b):
    if not a or not b:
        return 0.0
    w = min(a[0] + a[2], b[0] + b[2]) - max(a[0], b[0])
    h = min(a[1] + a[3], b[1] + b[3]) - max(a[1], b[1])
    return max(w, 0) * max(h, 0)


def occl(task, cont):
    """area(T∩C∩V)/area(T∩V), 3dp. Intersection with V first, then with C (∩ is associative)."""
    tv = inter(task, VIEW)
    if tv <= 0:
        return None
    # T∩V as a rect
    x0, y0 = max(task[0], 0), max(task[1], 0)
    x1, y1 = min(task[0] + task[2], VIEW[2]), min(task[1] + task[3], VIEW[3])
    return round(inter((x0, y0, x1 - x0, y1 - y0), cont) / tv, 3)


def container_facts(c, task):
    cands = []
    for k in c["dismiss_control_candidates"]:
        bbox = tuple(k["bbox"]) if k.get("bbox") else None
        vis = bool(k.get("visible")) and inter(bbox, VIEW) > 0           # probe visible ∧ in viewport
        ax = bool(k.get("ax_exposed"))
        nm = " ".join((k.get("accessible_name") or "").split())
        cands.append(dict(sel=k["selector"], vis=vis, ax=ax, hit=bool(k.get("hittable")) and vis,
                          name=nm if (ax and nm) else ABSENT, order=k["dom_order"]))
    o = occl(task, tuple(c["bbox"]) if c.get("bbox") else None)
    req = bool((o or 0) > 0) or bool(c.get("aria_modal"))
    pick = min(cands, key=lambda k: (not k["vis"], not k["ax"], not k["hit"], k["order"])) if cands else None
    return dict(id=c["container_selector"], z=c.get("z_index") or 0, order=c["dom_order"],
                exists=bool(cands), visible=any(k["vis"] for k in cands) if cands else None,
                name=pick["name"] if pick else None, required=req, occl=o,
                hit=pick["hit"] if pick else None, sel=pick["sel"] if pick else None)


def as_out(f):
    return dict(zip(OUT, (f["exists"], f["visible"], f["name"], f["required"], f["occl"], f["hit"], f["sel"])))


def target_row(P):
    if not P:
        return dict(zip(OUT, (None, None, None, False, 0.0, None, None)))
    def all_true(key):
        if any(not f["exists"] for f in P):
            return False
        return all(bool(f[key]) for f in P)
    return dict(zip(OUT, (all(f["exists"] for f in P), all_true("visible"),
                          json.dumps([f["name"] for f in P], ensure_ascii=False),
                          any(f["required"] for f in P), max((f["occl"] or 0.0) for f in P),
                          all_true("hit"), json.dumps([f["sel"] for f in P], ensure_ascii=False))))


def run(path):
    return run_probe(json.loads(pathlib.Path(path).read_text(encoding="utf-8")))


def run_probe(p):
    task = tuple(p["task_control"]["bbox"])
    facts = sorted((container_facts(c, task) for c in p["raw_features"]["dismiss_control_candidates"]),
                   key=lambda f: (-f["z"], f["order"]))                   # dismissal order
    rows = []
    fx = p["fixture"]
    for pop in ("all", "blocking"):
        P = [f for f in facts if pop == "all" or f["required"]]
        for f in P:
            rows.append(dict(fixture=fx, unit="container", population=pop, row_id=f["id"], **as_out(f)))
        rows.append(dict(fixture=fx, unit="target", population=pop, row_id="TARGET", **target_row(P)))
        for i, f in enumerate(f for f in facts if f["required"]):
            rows.append(dict(fixture=fx, unit="step", population=pop, row_id=f"step{i}:{f['id']}", **as_out(f)))
    return rows


if __name__ == "__main__":
    for a in sys.argv[1:]:
        for r in run(a):
            print(json.dumps(r, ensure_ascii=False))
