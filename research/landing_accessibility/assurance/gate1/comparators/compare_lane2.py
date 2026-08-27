#!/usr/bin/env python3
"""compare_lane2 — label / reveal surface-state rows (lane2_label_reveal/EXPECTATIONS.json vs runner output).

Rows: the runner's fact_surface_state table (`surface`), keyed by state_index. S0 row = the S0 facts; entry row =
the row whose state_index == expected entry_observed_state (S0 or POST_REVEAL:<nav_container_type>).
Checks per fixture (all exact after NFC/whitespace normalisation unless noted):
  entry_control_identity   surface.entry_selector == entry_selector, or accessible-name match (entry row)
  s0.*                     visible_label_text, accessible_name, accessible_name_source, label_relation, entry_label_modality
                           (NOT_OBSERVED may be encoded null by the runner — GAP-04), task_control_visible, x/y null
  gap04.<row>              null convention on every row: unobserved ⇒ numerics null (never 0) and text NOT_OBSERVED/null
                           (never ''); observed ⇒ numerics present, categoricals never ''; no mixing
  entry.*                  entry_control_type, nav_container_type, nav_container_chain (len == nav_container_depth),
                           reveal_direction, entry_zone, entry_observed_state, dom_ax_divergence (ISOLATED)
  post_reveal.*            after_reveal label fields on the entry row (reveal fixtures)
  label_relation_recompute c_flow_derive.label_relation(runner visible, runner ax, frozen synonym map) — 3-way
  geometry.xy              entry_x/y_norm within ±0.02 of C's measure_result.json at that state
  entry_zone_recompute     band from runner x/y (c_flow_derive.entry_zone) vs entry_zone_band_R7; full zone with
                           DRAWER (runner nav_container_type≠NONE) / FLOATING (surface.entry_is_floating, if mapped)
  reveal_direction_geom    first reveal step's entry bbox_before/after centre delta: axis/sign/|Δ| ≥ min_abs_delta_px
  flow.menu_dependency / flow.nav_container_depth
  pseudo_provenance        04 §7: '배송조회'+PSEUDO_ELEMENT or ''+rendered_pseudo_text; bare '' FAILS
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "lane6_stats"))
from adapter_map import AdapterMap, RunnerOutput  # noqa: E402
from common import aggregate, as_int, bbox_center, eq_item, item, load_json, norm, state_key  # noqa: E402
import c_flow_derive as cfd  # noqa: E402

LANE = HERE.parent / "lane2_label_reveal"
XY_TOL = 0.02
TEXT_FIELDS = ("visible_label_text", "accessible_name", "accessible_name_source", "label_relation", "entry_label_modality")
CATEGORICAL_NEVER_EMPTY = ("accessible_name_source", "label_relation", "entry_zone", "entry_label_modality", "entry_control_type")
UNOBS = {"NOT_OBSERVED", "UNDETERMINED"}


def _rows_by_state(out: RunnerOutput, rows: list) -> dict[str, dict]:
    by: dict[str, dict] = {}
    for r in rows:
        lk = out.field("surface.state_index", r)
        if lk.ok:
            by.setdefault(state_key(lk.value), r)
    return by


def _c_reference(fixture: str) -> dict | None:
    p = LANE / "out" / "measure_result.json"
    if not p.exists():
        return None
    for rec in load_json(p).get("records", []):
        if rec.get("fixture") == fixture:
            return rec
    return None


def _gap04(fx: str, out: RunnerOutput, key: str, row: dict) -> dict:
    """GAP-04 null convention for one row."""
    x, y = out.field("surface.entry_x_norm", row), out.field("surface.entry_y_norm", row)
    if not (x.ok and y.ok):
        return item(fx, f"gap04.{key}", "null convention", None, "UNMAPPED", (x if not x.ok else y).reason)
    unobserved = x.value is None or y.value is None
    problems = []
    if unobserved:
        if (x.value, y.value) != (None, None):
            problems.append(f"mixed numerics x={x.value} y={y.value}")
        for f in TEXT_FIELDS + ("entry_zone",):
            lk = out.field(f"surface.{f}", row)
            if lk.ok and (lk.value == "" or lk.value == 0):
                problems.append(f"{f}='' / 0 at an unobserved state (must be NOT_OBSERVED or null)")
            if lk.ok and f in ("accessible_name_source", "label_relation", "entry_zone") and lk.value not in UNOBS and lk.value is not None:
                problems.append(f"{f}={lk.value!r} at an unobserved state (mixing observed value with null geometry)")
    else:
        for v, n in ((x.value, "entry_x_norm"), (y.value, "entry_y_norm")):
            if not isinstance(v, (int, float)) or isinstance(v, bool) or not (0.0 <= float(v) <= 1.0):
                problems.append(f"{n}={v!r} not a number in [0,1]")
        for f in CATEGORICAL_NEVER_EMPTY:
            lk = out.field(f"surface.{f}", row)
            if lk.ok and lk.value == "":
                problems.append(f"categorical {f}='' (must be a category)")
    return item(fx, f"gap04.{key}", "GAP-04 null convention", problems or "consistent", "PASS" if not problems else "FAIL",
                None if not problems else "; ".join(problems))


def compare_fixture(exp: dict, out: RunnerOutput, synonym_map: dict) -> list[dict]:
    fx = exp["fixture"]
    E = exp["expected"]
    AR = exp.get("after_reveal")
    entry_state = E["entry_observed_state"]
    items: list[dict] = []
    tbl = out.table("surface")
    if not tbl.ok:
        items.append(item(fx, "surface_rows", "fact_surface_state rows", None, "UNMAPPED", tbl.reason))
        # still try flow-level fields so the map gap is visible per field
    rows = tbl.value if tbl.ok else []
    by = _rows_by_state(out, rows) if rows else {}
    s0 = by.get("S0")
    entry = by.get(state_key(entry_state))
    if tbl.ok and s0 is None:
        items.append(item(fx, "surface_rows.S0", "S0 row", sorted(by), "FAIL", "no S0 fact_surface_state row (03 §3: S0 must always be emitted)"))
    if tbl.ok and entry is None:
        items.append(item(fx, "surface_rows.entry", entry_state, sorted(by), "FAIL",
                          f"no fact_surface_state row for entry_observed_state={entry_state} (GAP-07 / 03 §3 POST_REVEAL rows)"))

    # ---- S0 row -------------------------------------------------------------------------------
    if s0 is not None:
        for f in TEXT_FIELDS:
            items.append(eq_item(fx, f"s0.{f}", E[f], out.field(f"surface.{f}", s0), normalize=True, accept_none_for="NOT_OBSERVED"))
        items.append(eq_item(fx, "s0.task_control_visible", E["s0_task_control_visible"], out.field("surface.task_control_visible", s0)))
        if "s0_entry_x_norm" in E:   # reveal fixtures: S0 geometry must be null
            items.append(eq_item(fx, "s0.entry_x_norm_null", None, out.field("surface.entry_x_norm", s0)))
            items.append(eq_item(fx, "s0.entry_y_norm_null", None, out.field("surface.entry_y_norm", s0)))
        items.append(eq_item(fx, "s0.dom_ax_divergence", E["dom_ax_divergence"], out.field("surface.dom_ax_divergence", s0), severity="ISOLATED"))
    for k, r in sorted(by.items()):
        items.append(_gap04(fx, out, k, r))

    # ---- entry row ----------------------------------------------------------------------------
    if entry is not None:
        for f in ("entry_control_type", "nav_container_type", "reveal_direction", "entry_zone", "entry_observed_state"):
            items.append(eq_item(fx, f"entry.{f}", E[f], out.field(f"surface.{f}", entry), normalize=True))
        ch = out.field("surface.nav_container_chain", entry)
        if ch.ok:
            ok = list(ch.value or []) == list(E["nav_container_chain"]) and len(ch.value or []) == E["nav_container_depth"]
            items.append(item(fx, "entry.nav_container_chain", E["nav_container_chain"], ch.value, "PASS" if ok else "FAIL",
                              None if ok else f"chain mismatch or len != nav_container_depth={E['nav_container_depth']} (GAP-06)"))
        else:
            items.append(item(fx, "entry.nav_container_chain", E["nav_container_chain"], None, "UNMAPPED", ch.reason))
        if entry is not s0:
            items.append(eq_item(fx, "entry.dom_ax_divergence", E["dom_ax_divergence"], out.field("surface.dom_ax_divergence", entry), severity="ISOLATED"))
        # post-reveal label facts
        if AR:
            for f in TEXT_FIELDS:
                items.append(eq_item(fx, f"post_reveal.{f}", AR[f], out.field(f"surface.{f}", entry), normalize=True))
        # identity: selector or ax-name
        exp_ax = (AR or E)["accessible_name"]
        sel = out.field("surface.entry_selector", entry)
        ax = out.field("surface.accessible_name", entry)
        if sel.ok and norm(sel.value) == norm(exp["entry_selector"]):
            items.append(item(fx, "entry_control_identity", exp["entry_selector"], sel.value, "PASS"))
        elif ax.ok and exp_ax not in ("", "NOT_OBSERVED") and norm(ax.value) == norm(exp_ax):
            items.append(item(fx, "entry_control_identity", exp["entry_selector"], {"selector": sel.value if sel.ok else None, "ax_name": ax.value},
                              "PASS", "matched by accessible name" + ("" if sel.ok else " (surface.entry_selector UNMAPPED)")))
        elif sel.ok or (ax.ok and exp_ax not in ("", "NOT_OBSERVED")):
            items.append(item(fx, "entry_control_identity", exp["entry_selector"], {"selector": sel.value if sel.ok else None, "ax_name": ax.value if ax.ok else None},
                              "FAIL", "neither selector nor accessible name identifies the C entry control"))
        else:
            items.append(item(fx, "entry_control_identity", exp["entry_selector"], None, "UNMAPPED",
                              "surface.entry_selector not in spec and the expected accessible name is empty — identity not decidable"))
        # label_relation recompute (3-way)
        vis, lr = out.field("surface.visible_label_text", entry), out.field("surface.label_relation", entry)
        exp_lr = (AR or E)["label_relation"]
        if vis.ok and ax.ok and lr.ok:
            c_lr = cfd.label_relation(vis.value, ax.value, synonym_map)
            pairs = [p for p, bad in (("EXP≠C", c_lr != exp_lr), ("EXP≠RUNNER", norm(lr.value) != exp_lr), ("C≠RUNNER", norm(lr.value) != c_lr)) if bad]
            items.append(item(fx, "label_relation_recompute", exp_lr, {"runner": lr.value, "c_recomputed": c_lr}, "PASS" if not pairs else "FAIL",
                              None if not pairs else f"disagreement: {pairs}"))
        else:
            items.append(item(fx, "label_relation_recompute", exp_lr, None, "UNMAPPED", next(l.reason for l in (vis, ax, lr) if not l.ok)))
        # geometry ±0.02 vs C reference, zone recompute
        x, y = out.field("surface.entry_x_norm", entry), out.field("surface.entry_y_norm", entry)
        ref = _c_reference(fx)
        ref_row = None
        if ref:
            ref_row = ref.get("s0") if entry_state == "S0" else ref.get("s1_after_reveal")
        if not (x.ok and y.ok):
            items.append(item(fx, "geometry.xy", None, None, "UNMAPPED", (x if not x.ok else y).reason))
        elif x.value is None or y.value is None:
            items.append(item(fx, "geometry.xy", "observed geometry at entry row", None, "FAIL", "entry row geometry null (control declared observed here)"))
        elif not ref_row or ref_row.get("entry_x_norm") is None:
            items.append(item(fx, "geometry.xy", None, (x.value, y.value), "NOT_TESTABLE", "C reference geometry missing — run lane2/measure_geometry.py first"))
        else:
            dx, dy = abs(float(x.value) - ref_row["entry_x_norm"]), abs(float(y.value) - ref_row["entry_y_norm"])
            ok = dx <= XY_TOL and dy <= XY_TOL
            items.append(item(fx, "geometry.xy", (ref_row["entry_x_norm"], ref_row["entry_y_norm"]), (x.value, y.value), "PASS" if ok else "FAIL",
                              None if ok else f"|Δx|={dx:.3f} |Δy|={dy:.3f} > {XY_TOL}"))
        if x.ok and y.ok and x.value is not None and y.value is not None:
            try:
                band = cfd.entry_zone(x.value, y.value, False, False)
                items.append(item(fx, "entry_zone_band_recompute", E["entry_zone_band_R7"], band, "PASS" if band == E["entry_zone_band_R7"] else "FAIL"))
                nct = out.field("surface.nav_container_type", entry)
                fl = out.field("surface.entry_is_floating", entry)
                rz = out.field("surface.entry_zone", entry)
                if nct.ok and rz.ok and (fl.ok or E["entry_zone"] != "FLOATING"):
                    is_drawer = norm(nct.value) not in ("", "NONE")
                    is_float = bool(fl.value) if fl.ok else False
                    cz = cfd.entry_zone(x.value, y.value, is_float, is_drawer)
                    pairs = [p for p, bad in (("EXP≠C", cz != E["entry_zone"]), ("EXP≠RUNNER", norm(rz.value) != E["entry_zone"]), ("C≠RUNNER", norm(rz.value) != cz)) if bad]
                    items.append(item(fx, "entry_zone_recompute", E["entry_zone"], {"runner": rz.value, "c_recomputed": cz, "is_drawer": is_drawer, "is_floating": is_float},
                                      "PASS" if not pairs else "FAIL", None if not pairs else f"disagreement: {pairs}"))
                else:
                    items.append(item(fx, "entry_zone_recompute", E["entry_zone"], None, "UNMAPPED",
                                      fl.reason if not fl.ok else (nct.reason if not nct.ok else rz.reason)))
            except ValueError as e:
                items.append(item(fx, "entry_zone_band_recompute", E["entry_zone_band_R7"], (x.value, y.value), "FAIL", str(e)))
        # pseudo-element provenance (04 §7)
        if E.get("visible_text_provenance") == "PSEUDO_ELEMENT" and vis.ok:
            prov = out.field("surface.visible_text_provenance", entry)
            rpt = out.field("surface.rendered_pseudo_text", entry)
            v = norm(vis.value)
            if v == E["visible_label_text"] and prov.ok and norm(prov.value) == "PSEUDO_ELEMENT":
                st, why = "PASS", "encoding (a)"
            elif v == "" and rpt.ok and norm(rpt.value) == E["visible_label_text"]:
                st, why = "PASS", "encoding (b)"
            elif v == E["visible_label_text"] and not prov.ok:
                st, why = "UNMAPPED", "text correct but provenance field not in spec (surface.visible_text_provenance) — 04 §7 provenance unverified"
            else:
                st, why = "FAIL", "bare '' without provenance, or wrong text (04 §7)"
            items.append(item(fx, "pseudo_provenance", {"text": E["visible_label_text"], "provenance": "PSEUDO_ELEMENT"},
                              {"visible": vis.value, "provenance": prov.value if prov.ok else None, "rendered_pseudo_text": rpt.value if rpt.ok else None}, st, why))

    # ---- flow-level menu_dependency / nav_container_depth ---------------------------------------
    for f in ("menu_dependency", "nav_container_depth"):
        lk = out.rec_field("flow", f)
        if lk.ok:
            ok = as_int(lk.value) == E[f]
            items.append(item(fx, f"flow.{f}", E[f], lk.value, "PASS" if ok else "FAIL"))
        else:
            items.append(item(fx, f"flow.{f}", E[f], None, "UNMAPPED", lk.reason))

    # ---- reveal direction from step geometry ----------------------------------------------------
    if AR and exp.get("reveal_tokens"):
        motion = AR["motion"]
        steps = out.table("steps")
        if not steps.ok:
            items.append(item(fx, "reveal_direction_geom", motion, None, "UNMAPPED", steps.reason))
        else:
            rev = None
            for s in sorted(steps.value, key=lambda r: as_int(out.field("step.step_index", r).value) if out.field("step.step_index", r).ok else 0):
                tk = out.field("step.action_token", s)
                if tk.ok and tk.value in exp["reveal_tokens"]:
                    rev = s
                    break
            if rev is None:
                items.append(item(fx, "reveal_direction_geom", motion, None, "FAIL", f"no fact_flow_step with a reveal token {exp['reveal_tokens']}"))
            else:
                bb, ba = out.field("step.entry_bbox_before", rev), out.field("step.entry_bbox_after", rev)
                if not (bb.ok and ba.ok):
                    items.append(item(fx, "reveal_direction_geom", motion, None, "UNMAPPED", (bb if not bb.ok else ba).reason))
                else:
                    c0, c1 = bbox_center(bb.value), bbox_center(ba.value)
                    axis = motion.get("axis")
                    if c1 is None:
                        st, obs, why = "FAIL", {"before": bb.value, "after": ba.value}, "bbox_after not a bbox (control must be laid out after the reveal)"
                    elif c0 is None:
                        ok = axis == "none" and motion.get("before_rendered") is False
                        st, obs, why = ("PASS" if ok else "FAIL"), {"before": bb.value, "after": ba.value}, (None if ok else "bbox_before missing but motion expected")
                    else:
                        dx, dy = c1[0] - c0[0], c1[1] - c0[1]
                        obs = {"dx": round(dx, 1), "dy": round(dy, 1)}
                        if axis == "none":
                            ok = max(abs(dx), abs(dy)) <= motion.get("max_abs_delta_px", 4)
                            why = None if ok else "control moved although no motion expected"
                        else:
                            d = dx if axis == "x" else dy
                            other = dy if axis == "x" else dx
                            ok = abs(d) >= motion["min_abs_delta_px"] and abs(d) >= abs(other) and ((d > 0) == (motion["sign"] == "+"))
                            why = None if ok else f"expected axis={axis} sign={motion['sign']} |Δ|≥{motion['min_abs_delta_px']}; geometry wins over class/id names"
                        st = "PASS" if ok else "FAIL"
                    items.append(item(fx, "reveal_direction_geom", motion, obs, st, why))
    return items


def compare_all(runner_dirs: dict[str, str | pathlib.Path | None], amap: AdapterMap, lane_dir: pathlib.Path = LANE) -> dict:
    ex = load_json(lane_dir / "EXPECTATIONS.json")
    syn = ex["meta"]["synonym_map_fixed"]
    items: list[dict] = []
    for exp in ex["fixtures"]:
        items += compare_fixture(exp, RunnerOutput(runner_dirs.get(exp["fixture"]), amap), syn)
    summ = aggregate(items)
    pos = sorted({i["fixture"] for i in items if i["status"] == "FAIL" and i.get("severity") != "ISOLATED"
                  and next(f for f in ex["fixtures"] if f["fixture"] == i["fixture"])["control_role"] == "POSITIVE_CONTROL"})
    if pos:
        summ["positive_control_failed"] = pos
        summ["reason"] = (summ.get("reason") or "") + f" · POSITIVE CONTROL(s) failed {pos} ⇒ negatives uninterpretable (P-67)"
    return {"lane": "lane2", "items": items, "summary": summ}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="lane2 comparator")
    ap.add_argument("--runner-root"); ap.add_argument("--adapter-map", default=None); ap.add_argument("--out", default=None)
    a = ap.parse_args(argv)
    ex = load_json(LANE / "EXPECTATIONS.json")
    dirs = {f["fixture"]: (pathlib.Path(a.runner_root) / f["fixture"] if a.runner_root else None) for f in ex["fixtures"]}
    res = compare_all(dirs, AdapterMap.load(a.adapter_map))
    if a.out:
        pathlib.Path(a.out).write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps({k: res["summary"][k] for k in ("status", "reason", "counts")}, ensure_ascii=False))
    return 0 if res["summary"]["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
