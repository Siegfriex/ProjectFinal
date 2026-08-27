#!/usr/bin/env python3
"""impl_A — source axis = PROBE.
Reads a probe-like JSON (raw_features.dismiss_control_candidates = list of containers, each with a
dismiss_control_candidates list of {selector, hittable, visible, accessible_name, bbox, ...}, plus
path_control = the CURRENT-STATE path control with a 9x9 elementFromPoint hit grid, and per-container
blocking_proof) and derives the dismiss_control_exists family at target / container / step units for
populations all / blocking.
Standalone on purpose: shares no code with impl_b.py (DISMISS_DEFINITION_C.md §2-§6, v1.2 after
C-DECISION_REQUEST-031138 P-23/P-24: hit-test primary, blocking proof primary)."""
from __future__ import annotations
import json, sys, pathlib

VIEW = (0, 0, 390, 844)
ABSENT = "NAME_ABSENT"
OUT = ("dismiss_control_exists", "dismiss_control_visible", "dismiss_control_accessible_name",
       "dismiss_required_for_task", "dismiss_required_signal", "task_control_occlusion", "occlusion_geom_crosscheck",
       "dismiss_control_hittable_s0", "selected_selector")


def inter(a, b):
    if not a or not b:
        return 0.0
    w = min(a[0] + a[2], b[0] + b[2]) - max(a[0], b[0])
    h = min(a[1] + a[3], b[1] + b[3]) - max(a[1], b[1])
    return max(w, 0) * max(h, 0)


def occl_geom(task, cont):
    """Cross-check only (P-23): area(T∩C∩V)/area(T∩V) on the FROZEN task-entry control T, 3dp."""
    tv = inter(task, VIEW)
    if tv <= 0:
        return None
    x0, y0 = max(task[0], 0), max(task[1], 0)
    x1, y1 = min(task[0] + task[2], VIEW[2]), min(task[1] + task[3], VIEW[3])
    return round(inter((x0, y0, x1 - x0, y1 - y0), cont) / tv, 3)


def hit_points(pc):
    """Decode the probe's 9x9 hit grid on the current-state path control: list of legend keys per in-viewport point
    ('.' = control or descendant; '-' = point outside the viewport, excluded from the denominator)."""
    if not pc or not pc.get("hit_grid"):
        return None
    pts = [ch for row in pc["hit_grid"]["rows"] for ch in row if ch != "-"]
    return pts or None


def signal_str(s):
    return "+".join(sorted(s)) if s else "NONE"


def container_facts(c, task, pc, pts):
    cands = []
    for k in c["dismiss_control_candidates"]:
        bbox = tuple(k["bbox"]) if k.get("bbox") else None
        vis = bool(k.get("visible")) and inter(bbox, VIEW) > 0           # probe visible ∧ in viewport
        ax = bool(k.get("ax_exposed"))
        nm = " ".join((k.get("accessible_name") or "").split())
        cands.append(dict(sel=k["selector"], vis=vis, ax=ax, hit=bool(k.get("hittable")) and vis,
                          name=nm if (ax and nm) else ABSENT, order=k["dom_order"]))
    geom = occl_geom(task, tuple(c["bbox"]) if c.get("bbox") else None)
    letter = (pc or {}).get("hit_grid", {}).get("legend_inv", {}).get(c["container_selector"]) if pc else None
    if pts is not None:
        n_hit = sum(1 for p in pts if p == letter) if letter else 0
        hit = round(n_hit / len(pts), 3)
    else:
        n_hit, hit = 0, None                                                 # no path control → primary undefined
    required = bool(c.get("blocking_proof")) if pc else None                 # P-24: the executed blocking proof IS the verdict
    sig = set()
    if c.get("aria_modal"):
        sig.add("ARIA_MODAL")
    if (hit or 0) > 0:
        sig.add("OCCLUSION_GT0")
    if (geom or 0) > 0:
        sig.add("GEOM_OVERLAP_GT0")
    pick = min(cands, key=lambda k: (not k["vis"], not k["ax"], not k["hit"], k["order"])) if cands else None
    return dict(id=c["container_selector"], z=c.get("z_index") or 0, order=c["dom_order"],
                exists=bool(cands), visible=any(k["vis"] for k in cands) if cands else None,
                name=pick["name"] if pick else None, required=required, signal=sig, occl=hit, n_hit=n_hit, geom=geom,
                hit=pick["hit"] if pick else None, sel=pick["sel"] if pick else None)


def as_out(f):
    return dict(zip(OUT, (f["exists"], f["visible"], f["name"], f["required"], signal_str(f["signal"]), f["occl"], f["geom"],
                          f["hit"], f["sel"])))


def target_row(P, pts):
    if not P:
        return dict(zip(OUT, (None, None, None, False, "NONE", 0.0 if pts is not None else None, 0.0, None, None)))
    def all_true(key):
        if any(not f["exists"] for f in P):
            return False
        return all(bool(f[key]) for f in P)
    occl = round(sum(f["n_hit"] for f in P) / len(pts), 3) if pts is not None else None   # union: each point hits ≤ 1 container
    return dict(zip(OUT, (all(f["exists"] for f in P), all_true("visible"),
                          json.dumps([f["name"] for f in P], ensure_ascii=False),
                          any(bool(f["required"]) for f in P) if all(f["required"] is not None for f in P) else None,
                          signal_str(set().union(*(f["signal"] for f in P))),
                          occl, max((f["geom"] or 0.0) for f in P),
                          all_true("hit"), json.dumps([f["sel"] for f in P], ensure_ascii=False))))


def run(path):
    return run_probe(json.loads(pathlib.Path(path).read_text(encoding="utf-8")))


def run_probe(p):
    task = tuple(p["task_control"]["bbox"])
    pc = p.get("path_control")
    if pc and pc.get("hit_grid"):
        pc["hit_grid"]["legend_inv"] = {v: k for k, v in pc["hit_grid"]["legend"].items()}
    pts = hit_points(pc)
    facts = sorted((container_facts(c, task, pc, pts) for c in p["raw_features"]["dismiss_control_candidates"]),
                   key=lambda f: (-f["z"], f["order"]))                   # dismissal order
    rows = []
    fx = p["fixture"]
    for pop in ("all", "blocking"):
        P = [f for f in facts if pop == "all" or f["required"]]
        for f in P:
            rows.append(dict(fixture=fx, unit="container", population=pop, row_id=f["id"], **as_out(f)))
        rows.append(dict(fixture=fx, unit="target", population=pop, row_id="TARGET", **target_row(P, pts)))
        for i, f in enumerate(f for f in facts if f["required"]):
            rows.append(dict(fixture=fx, unit="step", population=pop, row_id=f"step{i}:{f['id']}", **as_out(f)))
    return rows


if __name__ == "__main__":
    for a in sys.argv[1:]:
        for r in run(a):
            print(json.dumps(r, ensure_ascii=False))
