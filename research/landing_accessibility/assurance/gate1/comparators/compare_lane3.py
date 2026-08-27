#!/usr/bin/env python3
"""compare_lane3 — sequence / dismiss / auth (lane3_sequence_dismiss_auth/EXPECTATIONS.json vs runner output).

Per fixture:
  seq.task_flow_sequence / seq.experienced_flow_sequence   exact token equality
  lossless                 runner fact_flow_step rows (by step_index, canonical non-terminal tokens) as
                           (state_before, action_token, state_after) == lossless_check, in order, none missing
  lossless.url_changes     url_before != url_after on every recorded token step (fixture changes location.hash)
  derived.<f>              three-way: lane3 expectation vs C recompute (c_flow_derive.derive on the RUNNER's own
                           sequences) vs runner-stored value; any disagreement FAIL naming the pair(s)
                           f ∈ activation_depth flow_step_count menu_dependency nav_container_depth forced_dismissal_count
                               auth_gate_stage endpoint_status
  auth_gate_stage_positional   runner-stored vs C positional rule (P-13/P-14) — explicit item
  obstruction.dismiss_required_for_task / task_control_occlusion_s0 (±0.02, null ≠ 0)
  first_visible_scroll_state   exact (null only for the login wall)
  terminal_R11             validate_terminal(endpoint_status, terminal_reason, note).ok
  q8_field_qualification   q8_bare_mentions(flow row) == []
  scroll_states            surface rows S0..Sk present when the fixture needs them (03 §3); the scroll fixture item
                           carries coverage=scroll_capture_03_s3
  credential_check         needs terminal DOM / input values — UNMAPPED under the current spec
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys
from typing import Any

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "lane6_stats"))
from adapter_map import AdapterMap, RunnerOutput  # noqa: E402
from common import aggregate, as_int, eq_item, item, load_json, norm, state_key  # noqa: E402
import c_flow_derive as cfd  # noqa: E402

LANE = HERE.parent / "lane3_sequence_dismiss_auth"
OCC_TOL = 0.02
DERIVED = ("activation_depth", "flow_step_count", "menu_dependency", "nav_container_depth", "forced_dismissal_count",
           "auth_gate_stage", "endpoint_status")
SCROLL_FIXTURE = "seq_typing_and_scroll_not_depth"


def _seq(v: Any) -> list[str] | None:
    if v is None:
        return None
    if isinstance(v, str):
        return [t.strip() for t in v.replace(">", ",").split(",") if t.strip()]
    return [str(t) for t in v]


def _norm_derived(f: str, v: Any) -> Any:
    if v is None:
        return None
    if f in ("menu_dependency",):
        return as_int(v)
    if f in ("activation_depth", "flow_step_count", "nav_container_depth", "forced_dismissal_count"):
        return as_int(v)
    return norm(v)


def compare_fixture(name: str, fx: dict, out: RunnerOutput) -> list[dict]:
    items: list[dict] = []
    flow = out.record("flow")
    tfs = out.rec_field("flow", "task_flow_sequence")
    efs = out.rec_field("flow", "experienced_flow_sequence")
    # ---- sequences ------------------------------------------------------------------------------
    for f, lk in (("task_flow_sequence", tfs), ("experienced_flow_sequence", efs)):
        if lk.ok:
            ok = _seq(lk.value) == fx[f]
            items.append(item(name, f"seq.{f}", fx[f], _seq(lk.value), "PASS" if ok else "FAIL", None if ok else "token sequence differs"))
        else:
            items.append(item(name, f"seq.{f}", fx[f], None, "UNMAPPED", lk.reason))

    # ---- lossless triples -----------------------------------------------------------------------
    steps = out.table("steps")
    if steps.ok:
        ordered = sorted(steps.value, key=lambda r: (as_int(out.field("step.step_index", r).value) if out.field("step.step_index", r).ok and as_int(out.field("step.step_index", r).value) is not None else 10**6))
        triples, url_bad, unmapped = [], [], None
        for r in ordered:
            tk = out.field("step.action_token", r)
            sb, sa = out.field("step.state_before", r), out.field("step.state_after", r)
            if not (tk.ok and sb.ok and sa.ok):
                unmapped = next(l.reason for l in (tk, sb, sa) if not l.ok)
                break
            t = str(tk.value)
            if t not in cfd.CANONICAL_TOKENS or t in cfd.TERMINAL_TOKENS:
                continue
            triples.append([str(sb.value), t, str(sa.value)])
            ub, ua = out.field("step.url_before", r), out.field("step.url_after", r)
            if ub.ok and ua.ok and ub.value == ua.value:
                url_bad.append(t)
        if unmapped:
            items.append(item(name, "lossless", fx["lossless_check"], None, "UNMAPPED", unmapped))
        else:
            ok = triples == [list(t) for t in fx["lossless_check"]]
            missing = [t for t in fx["lossless_check"] if list(t) not in triples]
            items.append(item(name, "lossless", fx["lossless_check"], triples, "PASS" if ok else "FAIL",
                              None if ok else (f"missing triple(s) {missing}" if missing else "extra/reordered triples")))
            if fx["lossless_check"]:
                ub_any = any(out.field("step.url_before", r).ok for r in ordered)
                if ub_any:
                    items.append(item(name, "lossless.url_changes", "url_before != url_after on every token step", url_bad or "all changed",
                                      "PASS" if not url_bad else "FAIL", None if not url_bad else f"url unchanged on {url_bad}"))
                else:
                    items.append(item(name, "lossless.url_changes", "url change per step", None, "UNMAPPED", "step.url_before/url_after not in output"))
        # terminal state of the last token step must equal lossless_terminal.state (when any step exists)
        if not unmapped and ordered and fx["lossless_check"]:
            last_sa = out.field("step.state_after", ordered[-1])
            items.append(eq_item(name, "lossless.terminal_state", fx["lossless_terminal"]["state"], last_sa, normalize=True))
    else:
        items.append(item(name, "lossless", fx["lossless_check"], None, "UNMAPPED", steps.reason))

    # ---- derived three-way ----------------------------------------------------------------------
    if tfs.ok and efs.ok and _seq(tfs.value) is not None:
        esrbg = out.rec_field("flow", "endpoint_surface_rendered_before_gate")
        kw: dict[str, Any] = {}
        needs_flag = bool(fx.get("endpoint_surface_rendered_without_auth"))
        if esrbg.ok and esrbg.value is not None:
            kw["endpoint_surface_rendered_before_gate"] = bool(esrbg.value)
        d = cfd.derive(_seq(tfs.value), _seq(efs.value), **kw)
        for f in DERIVED:
            lk = out.rec_field("flow", f)
            exp_v = _norm_derived(f, fx[f])
            c_v = _norm_derived(f, d[f])
            if f == "auth_gate_stage" and needs_flag and not (esrbg.ok and esrbg.value is not None):
                items.append(item(name, f"derived.{f}", exp_v, {"runner": lk.value if lk.ok else None, "c_recomputed": c_v}, "UNMAPPED",
                                  "AT_ENDPOINT needs the runner's endpoint_surface_rendered_before_gate observation (P-14) — " + (esrbg.reason or "value null")))
                continue
            if f == "endpoint_status" and c_v == "UNRESOLVED_FROM_SEQUENCE":
                c_v = None
            if not lk.ok:
                items.append(item(name, f"derived.{f}", exp_v, {"runner": None, "c_recomputed": c_v}, "UNMAPPED", lk.reason))
                continue
            r_v = _norm_derived(f, lk.value)
            pairs = []
            if c_v is not None and exp_v != c_v:
                pairs.append("EXP≠C")
            if exp_v != r_v:
                pairs.append("EXP≠RUNNER")
            if c_v is not None and c_v != r_v:
                pairs.append("C≠RUNNER")
            items.append(item(name, f"derived.{f}", exp_v, {"runner": r_v, "c_recomputed": c_v}, "PASS" if not pairs else "FAIL",
                              None if not pairs else f"disagreement: {pairs}" + (" (rule drift: runner sequence right, derivation wrong)" if pairs == ["EXP≠RUNNER", "C≠RUNNER"] else "")))
        # explicit positional-rule item
        ag = out.rec_field("flow", "auth_gate_stage")
        if ag.ok and not (needs_flag and not (esrbg.ok and esrbg.value is not None)):
            ok = norm(ag.value) == d["auth_gate_stage"]
            items.append(item(name, "auth_gate_stage_positional", d["auth_gate_stage"], ag.value, "PASS" if ok else "FAIL",
                              None if ok else "runner-stored stage ≠ C positional rule (T-A-V3-STEP1-011 P-13/P-14) on the runner's own sequence"))
        if d["violations"]:
            items.append(item(name, "derive.violations", [], d["violations"], "FAIL", "codebook contract violated by the runner's sequences (04 §2-§3)"))
    else:
        for f in DERIVED:
            items.append(item(name, f"derived.{f}", fx[f], None, "UNMAPPED", (tfs if not tfs.ok else efs).reason))

    # ---- obstruction row ------------------------------------------------------------------------
    obs = out.table("obstruction")
    if obs.ok:
        rows = obs.value
        s0 = None
        for r in rows:
            si = out.field("obstruction.state_index", r)
            if si.ok and state_key(si.value) == "S0":
                s0 = r
                break
        if s0 is None and len(rows) == 1 and not out.field("obstruction.state_index", rows[0]).ok:
            s0 = rows[0]
        any_required = []
        for r in rows:
            dr = out.field("obstruction.dismiss_required_for_task", r)
            if dr.ok and dr.value is True:
                any_required.append(r)
        dr_mapped = any(out.field("obstruction.dismiss_required_for_task", r).ok for r in rows) or not rows
        if dr_mapped:
            ok = bool(any_required) == bool(fx["dismiss_required_for_task"])
            items.append(item(name, "obstruction.dismiss_required_for_task", fx["dismiss_required_for_task"], len(any_required), "PASS" if ok else "FAIL",
                              None if ok else ("blocking proof missing" if fx["dismiss_required_for_task"] else "non-blocking interrupt reported as forced dismissal (geometric overlap ≠ obstruction)")))
            if fx["dismiss_required_for_task"] and any_required:
                dc = out.field("obstruction.dismiss_control_accessible_name", any_required[0])
                exp_dc = (fx.get("dismiss_control") or {}).get("accessible_name")
                if exp_dc:
                    items.append(eq_item(name, "obstruction.dismiss_control_accessible_name", exp_dc, dc, normalize=True))
        else:
            items.append(item(name, "obstruction.dismiss_required_for_task", fx["dismiss_required_for_task"], None, "UNMAPPED", "obstruction.dismiss_required_for_task absent"))
        exp_occ = fx["task_control_occlusion_s0"]
        if s0 is None:
            if exp_occ is None and not rows:
                items.append(item(name, "obstruction.task_control_occlusion_s0", None, "no row", "PASS", "no S0 obstruction row and none expected (control not observed at S0)"))
            else:
                items.append(item(name, "obstruction.task_control_occlusion_s0", exp_occ, None, "FAIL" if exp_occ is not None else "PASS",
                                  "no S0 fact_task_obstruction row" if exp_occ is not None else None))
        else:
            oc = out.field("obstruction.task_control_occlusion", s0)
            if not oc.ok:
                items.append(item(name, "obstruction.task_control_occlusion_s0", exp_occ, None, "UNMAPPED", oc.reason))
            elif exp_occ is None:
                ok = oc.value is None
                items.append(item(name, "obstruction.task_control_occlusion_s0", None, oc.value, "PASS" if ok else "FAIL",
                                  None if ok else "expected null (not observed, GAP-04) but runner wrote a number (0 ≠ null)"))
            elif oc.value is None:
                items.append(item(name, "obstruction.task_control_occlusion_s0", exp_occ, None, "FAIL", "runner wrote null where the control was observable"))
            else:
                ok = abs(float(oc.value) - float(exp_occ)) <= OCC_TOL
                items.append(item(name, "obstruction.task_control_occlusion_s0", exp_occ, oc.value, "PASS" if ok else "FAIL", None if ok else f"|Δ| > {OCC_TOL}"))
    else:
        items.append(item(name, "obstruction.row", {"dismiss_required_for_task": fx["dismiss_required_for_task"], "task_control_occlusion_s0": fx["task_control_occlusion_s0"]},
                          None, "UNMAPPED", obs.reason))

    # ---- first_visible_scroll_state ------------------------------------------------------------
    fv = out.rec_field("flow", "first_visible_scroll_state")
    if not fv.ok and flow.ok:
        # spec lists it on fact_surface_state rows too — accept the S0 row's value
        tb = out.table("surface")
        if tb.ok:
            for r in tb.value:
                si = out.field("surface.state_index", r)
                if si.ok and state_key(si.value) == "S0":
                    fv = out.field("surface.first_visible_scroll_state", r)
                    break
    exp_fv = fx["first_visible_scroll_state"]
    if fv.ok:
        got = None if fv.value is None else state_key(fv.value)
        ok = got == exp_fv
        items.append(item(name, "first_visible_scroll_state", exp_fv, fv.value, "PASS" if ok else "FAIL",
                          None if ok else ("null allowed ONLY when the control was never observed (GAP-02)" if got is None else "mismatch")))
    else:
        items.append(item(name, "first_visible_scroll_state", exp_fv, None, "UNMAPPED", fv.reason))

    # ---- terminal R11 + Q8 ---------------------------------------------------------------------
    es, tr, tn = out.rec_field("flow", "endpoint_status"), out.rec_field("flow", "terminal_reason"), out.rec_field("flow", "terminal_note")
    if es.ok and tr.ok:
        v = cfd.validate_terminal(es.value, tr.value, tn.value if tn.ok else None)
        items.append(item(name, "terminal_R11", "allowed endpoint_status × terminal_reason", {"endpoint_status": v["endpoint_status"], "terminal_reason": v["terminal_reason"]},
                          "PASS" if v["ok"] else "FAIL", None if v["ok"] else "; ".join(v["violations"])))
    else:
        items.append(item(name, "terminal_R11", "endpoint_status × terminal_reason", None, "UNMAPPED", (es if not es.ok else tr).reason))
    if flow.ok:
        bare = cfd.q8_bare_mentions(flow.value, "flow")
        items.append(item(name, "q8_field_qualification", [], bare, "PASS" if not bare else "FAIL", None if not bare else "AUTH_GATE/ABSTAIN used without layer qualification (R6 Q8)"))
    else:
        items.append(item(name, "q8_field_qualification", [], None, "UNMAPPED", flow.reason))

    # ---- scroll states (03 §3) -----------------------------------------------------------------
    need = fx.get("scroll_states_expected") or (["S0", "S1"] if exp_fv == "S1" else None)
    if need:
        tb = out.table("surface")
        extra = {"coverage": "scroll_capture_03_s3"} if name == SCROLL_FIXTURE else {}
        if not tb.ok:
            items.append(item(name, "scroll_states_present", need, None, "UNMAPPED", tb.reason, **extra))
        else:
            have = sorted({state_key(out.field("surface.state_index", r).value) for r in tb.value if out.field("surface.state_index", r).ok})
            miss = [s for s in need if s not in have]
            obs_ok = None
            if not miss and name == SCROLL_FIXTURE:
                vis = {}
                for r in tb.value:
                    si = out.field("surface.state_index", r)
                    tv = out.field("surface.task_control_visible", r)
                    if si.ok and tv.ok:
                        vis[state_key(si.value)] = tv.value
                obs_ok = (vis.get("S0") is False and vis.get("S1") is True) if ("S0" in vis and "S1" in vis) else None
            ok = not miss and obs_ok is not False
            items.append(item(name, "scroll_states_present", need, {"rows": have, "task_control_visible_S0_S1": obs_ok}, "PASS" if ok else "FAIL",
                              None if ok else (f"scroll-only states missing {miss} (03 §3: emit even when the page fits)" if miss else "S0 must be not-visible and S1 visible for the scroll fixture"), **extra))

    # ---- credential check (needs terminal DOM) --------------------------------------------------
    td = out.record("terminal_dom")
    if td.ok:
        battrs = out.field("terminal_dom.body_attrs", td.value)
        iv = out.field("terminal_dom.input_values", td.value)
        if battrs.ok:
            hit = "data-c-forbidden-hit" in (battrs.value or {})
            filled = [k for k, v in (iv.value or {}).items() if v] if iv.ok else None
            ok = not hit and not filled
            items.append(item(name, "credential_check", fx["credential_check"], {"forbidden_hit": hit, "filled_forbidden_inputs": filled}, "PASS" if ok else "FAIL",
                              None if ok else "forbidden input filled / forbidden control activated", hard_stop=None if ok else "forbidden_action"))
        else:
            items.append(item(name, "credential_check", fx["credential_check"], None, "UNMAPPED", battrs.reason))
    else:
        items.append(item(name, "credential_check", fx["credential_check"], None, "UNMAPPED", td.reason + " — terminal DOM capture is not in gate1_adapter_spec.md"))
    return items


def compare_all(runner_dirs: dict[str, str | pathlib.Path | None], amap: AdapterMap, lane_dir: pathlib.Path = LANE) -> dict:
    ex = load_json(lane_dir / "EXPECTATIONS.json")
    items: list[dict] = []
    for name, fx in ex["fixtures"].items():
        items += compare_fixture(name, fx, RunnerOutput(runner_dirs.get(name), amap))
    summ = aggregate(items)
    pos = sorted({i["fixture"] for i in items if i["status"] == "FAIL" and i.get("severity") != "ISOLATED" and ex["fixtures"][i["fixture"]]["control_role"] == "POSITIVE_CONTROL"})
    if pos:
        summ["positive_control_failed"] = pos
        summ["reason"] = (summ.get("reason") or "") + f" · POSITIVE CONTROL(s) failed {pos} ⇒ negatives uninterpretable (P-67)"
    scroll = [i for i in items if i.get("coverage") == "scroll_capture_03_s3"]
    summ["scroll_capture_03_s3"] = scroll[0]["status"] if scroll else "NOT_TESTABLE"
    summ["scroll_capture_reason"] = scroll[0].get("reason") if scroll else "scroll fixture produced no scroll_states_present item"
    summ["hard_stop_observed"] = sorted({i["hard_stop"] for i in items if i.get("hard_stop") and i["status"] == "FAIL"})
    return {"lane": "lane3", "items": items, "summary": summ}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="lane3 comparator")
    ap.add_argument("--runner-root"); ap.add_argument("--adapter-map", default=None); ap.add_argument("--out", default=None)
    a = ap.parse_args(argv)
    ex = load_json(LANE / "EXPECTATIONS.json")
    dirs = {n: (pathlib.Path(a.runner_root) / n if a.runner_root else None) for n in ex["fixtures"]}
    res = compare_all(dirs, AdapterMap.load(a.adapter_map))
    if a.out:
        pathlib.Path(a.out).write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps({k: res["summary"][k] for k in ("status", "reason", "counts", "scroll_capture_03_s3")}, ensure_ascii=False))
    return 0 if res["summary"]["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
