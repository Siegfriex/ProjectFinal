#!/usr/bin/env python3
"""selftest — hand-written synthetic runner output (exactly the gate1_adapter_spec.md shape) for one fixture per
lane, graded PASS; then a mutated copy graded FAIL. Proves the comparators discriminate (P-67: a checker that
cannot fail is not a checker). No runner, no browser, no network.

    python3 selftest.py [--workdir DIR] [--keep]        # exit 0 iff every lane is PASS on clean and FAIL on mutated
"""
from __future__ import annotations

import argparse
import copy
import json
import pathlib
import shutil
import sys
import tempfile

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from adapter_map import AdapterMap  # noqa: E402
from common import load_json  # noqa: E402
import compare_lane1, compare_lane2, compare_lane3, grade_lane4  # noqa: E402

GATE1 = HERE.parent
FIX = "file:///C/fixture.html"
# spec defaults + the C-requested terminal_dom extension (the only rows the spec lacks that these fixtures need)
SELFTEST_MAP = {"use_spec_defaults": True,
                "files": {"terminal_dom": "terminal_dom.json"},
                "fields": {"terminal_dom.body_attrs": "body_attrs", "terminal_dom.visible_markers": "visible_markers",
                           "terminal_dom.input_values": "input_values", "terminal_dom.text_by_id": "text_by_id"}}


def run_result(extra_files: dict | None = None) -> dict:
    files = {"flow": "flow.json", "fact_surface_state": "surface_states.json", "fact_task_obstruction": "obstructions.json",
             "action_log": "action_log.jsonl", "candidate_states": "candidate_states.json"}
    files.update(extra_files or {})
    return {"sha": "0" * 40, "exit": 0, "files": files, "refusal_reason": None, "non_file_requests_aborted": 0,
            "route_policy_doc": "docs/route_policy.md", "route_policy_sha256": "f" * 64}


def write(d: pathlib.Path, files: dict) -> pathlib.Path:
    d.mkdir(parents=True, exist_ok=True)
    for name, content in files.items():
        p = d / name
        if name.endswith(".jsonl"):
            p.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in content), encoding="utf-8")
        else:
            p.write_text(json.dumps(content, ensure_ascii=False, indent=1), encoding="utf-8")
    return d


def step(i: int, sb: str, tok: str, sa: str, sel: str, bb=None, ba=None) -> dict:
    return {"step_index": i, "state_before_id": sb, "action_token": tok, "state_after_id": sa, "control_selector": sel,
            "url_before": f"{FIX}#{sb}" if sb != "LANDING" else FIX, "url_after": f"{FIX}#{sa}", "bbox_before": bb, "bbox_after": ba}


# ----------------------------------------------------------------------------------------------- lane1 (C-F2-POS-01)
def lane1_output() -> dict:
    c = next(k for k in load_json(GATE1 / "lane1_task_binding" / "task_contracts.json")["contracts"] if k["task_id"] == "C-F2-POS-01")
    flow = {k: c[k] for k in ("task_id", "family_id", "endpoint_contract", "contract_sha256")}
    flow.update({"legacy_archetype": "ITEM_DETAIL", "task_flow_sequence": ["INPUT_QUERY", "SUBMIT_QUERY", "OPEN_ITEM_DETAIL", "ENDPOINT_REACHED"],
                 "experienced_flow_sequence": ["INPUT_QUERY", "SUBMIT_QUERY", "OPEN_ITEM_DETAIL", "ENDPOINT_REACHED"],
                 "activation_depth": 2, "flow_step_count": 3, "menu_dependency": 0, "nav_container_depth": 0, "forced_dismissal_count": 0,
                 "auth_gate_stage": "NONE", "endpoint_status": "REACHED", "terminal_reason": None, "terminal_note": None, "task_role": "PRIMARY",
                 "fixture_input_mode": "FREE_TEXT", "endpoint_surface_rendered_before_gate": None, "first_visible_scroll_state": "S0",
                 "steps": [step(0, "S0", "INPUT_QUERY", "S0_FILLED", "#q"), step(1, "S0_FILLED", "SUBMIT_QUERY", "F2_RESULT_LIST", "button[type=submit]"),
                           step(2, "F2_RESULT_LIST", "OPEN_ITEM_DETAIL", "F2_ITEM_DETAIL", "a.item")]})
    return {"run_result.json": run_result({"terminal_dom": "terminal_dom.json"}), "flow.json": flow,
            "surface_states.json": [{"state_index": "S0", "task_control_visible": True}], "obstructions.json": [],
            "action_log.jsonl": [{"log_active": True}], "candidate_states.json": [],
            "terminal_dom.json": {"body_attrs": {"data-c-state": "F2_ITEM_DETAIL", "data-c-query": "생수"}, "visible_markers": ["F2_ITEM_DETAIL"],
                                  "input_values": {}, "text_by_id": {"ITEM_NAME": "삼다수 2L", "ITEM_PRICE": "1,200원"}}}


# ----------------------------------------------------------------------------------------------- lane2 (drawer_left)
def lane2_output() -> dict:
    s0 = {"state_index": "S0", "visible_label_text": "NOT_OBSERVED", "accessible_name": "NOT_OBSERVED", "accessible_name_source": "NOT_OBSERVED",
          "label_relation": "NOT_OBSERVED", "entry_label_modality": "HIDDEN_UNTIL_REVEAL", "entry_control_type": "NOT_OBSERVED",
          "entry_x_norm": None, "entry_y_norm": None, "entry_zone": "NOT_OBSERVED", "entry_observed_state": "POST_REVEAL:LEFT_DRAWER",
          "nav_container_type": "LEFT_DRAWER", "nav_container_chain": ["LEFT_DRAWER"], "reveal_direction": "LEFT", "menu_dependency": 1,
          "nav_container_depth": 1, "task_control_visible": False, "dom_ax_divergence": False, "first_visible_scroll_state": "S0"}
    pr = dict(s0, state_index="POST_REVEAL:LEFT_DRAWER", visible_label_text="배송조회", accessible_name="배송조회", accessible_name_source="VISIBLE_TEXT",
              label_relation="MATCH", entry_label_modality="EXPLICIT_TEXT", entry_control_type="TEXT_LINK", entry_x_norm=0.4, entry_y_norm=0.219,
              entry_zone="DRAWER", task_control_visible=True)
    flow = {"task_id": "C-L2-drawer_left", "family_id": None, "menu_dependency": 1, "nav_container_depth": 1,
            "task_flow_sequence": ["OPEN_GLOBAL_MENU", "ENDPOINT_REACHED"], "experienced_flow_sequence": ["OPEN_GLOBAL_MENU", "ENDPOINT_REACHED"],
            "endpoint_status": "REACHED", "terminal_reason": None,
            "steps": [step(0, "S0", "OPEN_GLOBAL_MENU", "POST_REVEAL:LEFT_DRAWER", "[data-c-toggle=menu]",
                           {"x": -296, "y": 162, "width": 280, "height": 46}, {"x": 16, "y": 162, "width": 280, "height": 46})]}
    return {"run_result.json": run_result(), "flow.json": flow, "surface_states.json": [s0, pr], "obstructions.json": [],
            "action_log.jsonl": [{"log_active": True}], "candidate_states.json": []}


# ----------------------------------------------------------------------------------------------- lane3 (seq_with_forced_dismissal)
def lane3_output() -> dict:
    walk = [("LANDING_MODAL", "DISMISS_OBSTRUCTION", "LANDING", "#close"), ("LANDING", "OPEN_GLOBAL_MENU", "MENU_OPEN", "#hamburger"),
            ("MENU_OPEN", "SELECT_CATEGORY", "CATEGORY_BUS", "#cat-bus"), ("CATEGORY_BUS", "SELECT_FUNCTION", "FORM", "#fn-schedule"),
            ("FORM", "INPUT_QUERY", "FORM_FILLED", "#dest"), ("FORM_FILLED", "SUBMIT_QUERY", "RESULT_ROUTES", "#submit"),
            ("RESULT_ROUTES", "SELECT_RESULT", "ENDPOINT_SCHEDULE", "#route-1")]
    flow = {"task_id": "C-L3-seq_with_forced_dismissal", "family_id": "F5",
            "task_flow_sequence": ["OPEN_GLOBAL_MENU", "SELECT_CATEGORY", "SELECT_FUNCTION", "INPUT_QUERY", "SUBMIT_QUERY", "SELECT_RESULT", "ENDPOINT_REACHED"],
            "experienced_flow_sequence": ["DISMISS_OBSTRUCTION", "OPEN_GLOBAL_MENU", "SELECT_CATEGORY", "SELECT_FUNCTION", "INPUT_QUERY", "SUBMIT_QUERY", "SELECT_RESULT", "ENDPOINT_REACHED"],
            "activation_depth": 5, "flow_step_count": 6, "menu_dependency": 1, "nav_container_depth": 1, "forced_dismissal_count": 1,
            "auth_gate_stage": "NONE", "endpoint_status": "REACHED", "terminal_reason": None, "terminal_note": None, "task_role": "PRIMARY",
            "fixture_input_mode": "FREE_TEXT", "endpoint_surface_rendered_before_gate": None, "first_visible_scroll_state": "S0",
            "steps": [step(i, *w) for i, w in enumerate(walk)]}
    return {"run_result.json": run_result({"terminal_dom": "terminal_dom.json"}), "flow.json": flow,
            "surface_states.json": [{"state_index": "S0", "task_control_visible": False, "first_visible_scroll_state": "S0"}],
            "obstructions.json": [{"state_index": "S0", "task_control_occlusion": 1.0, "overlay_coverage": 1.0, "dismiss_required_for_task": True,
                                   "dismiss_control_accessible_name": "닫기", "dismiss_control_selector": "#close"}],
            "action_log.jsonl": [{"log_active": True}], "candidate_states.json": [],
            "terminal_dom.json": {"body_attrs": {"data-c-state": "ENDPOINT_SCHEDULE"}, "input_values": {"login-id": "", "login-pw": ""}}}


# ----------------------------------------------------------------------------------------------- lane4 (S1/S1b/S2/S3 + S4 on 13 guard fixtures)
def lane4_s4_outputs() -> dict[str, dict]:
    matrix = load_json(grade_lane4.MATRIX)
    outs = {}
    for f in matrix["fixtures"]:
        tag = pathlib.Path(f["fixture"]).stem
        cands = [{"selector": c["selector"], "state": c["expected_state"]} for c in f["controls"] if c["expected_state"] != "UNKNOWN"]
        log = [{"log_active": True}]
        if tag == "naver_like_login_plus_query":
            log += [{"ts": "2026-08-28T10:00:01+09:00", "type": "fill", "target_selector": "#q", "accessible_name": "검색어", "value_len": 2, "step_index": 0},
                    {"ts": "2026-08-28T10:00:02+09:00", "type": "click", "target_selector": "form[role=search] button[type=submit]", "accessible_name": "검색", "value_len": None, "step_index": 1}]
        else:
            log += [{"heartbeat": True, "step_index": 0}]
        outs[tag] = {"run_result.json": run_result(), "flow.json": {"task_id": f"C-L4-{tag}", "steps": []}, "surface_states.json": [], "obstructions.json": [],
                     "action_log.jsonl": log, "candidate_states.json": cands}
    return outs


def lane4_harness_outputs(d: pathlib.Path) -> dict:
    s1 = d / "s1_dup"; s1.mkdir(parents=True, exist_ok=True)
    (s1 / "C_W1_DUP_LAUNCH_HARNESS.json").write_text(json.dumps({"rc": [0, 0], "targets": 2, "evidence_runs_total": 2, "runs_per_target": {"t1": 1, "t2": 1},
                                                                  "duplicate_suppressed_events": 2, "verdict": "EXACTLY_ONCE_HOLDS"}), encoding="utf-8")
    (s1 / "proc2.log").write_text("start\nDUPLICATE_SUPPRESSED t1\nDUPLICATE_SUPPRESSED t2\nexit 0\n", encoding="utf-8")
    (d / "S1b.log").write_text("$ cmd\n" + json.dumps({"errors": [], "per_key": {"k1": {"proceed": 1, "suppressed": 2, "decisions": [1, 2, 3]}}, "exactly_once_holds": True}), encoding="utf-8")
    (d / "S3.log").write_text("$ cmd\n" + json.dumps({"ref": "e02eee4", "cand": "0" * 40, "files": [{"path": "batch.py", "ref_blob": "a1", "cand_blob": "a1", "unchanged": True}],
                                                      "all_unchanged": True}), encoding="utf-8")
    deny = {"outcome": "DENY", "allowed": False}
    rows = [{"scope": s, "l1": dict(deny), "l2": dict(deny)} for s in ("E001_FULL", "V3_MAIN50", "V3_PILOT_5", "unknown")]
    rows += [{"scope": "V2_DIAGNOSTIC", "l1": {"outcome": "ALLOW", "allowed": True}, "l2": {"outcome": "BLOCK", "allowed": False}},
             {"scope": "E000_FAST", "l1": dict(deny), "l2": dict(deny)}]
    (d / "s2_scope.json").write_text(json.dumps({"layers": {"l1": {"imported": True}, "l2": {"imported": True}}, "rows": rows,
                                                 "layer2_imports_layer1": False, "layer2_mentions_manifest_sha": False, "layer2_known_real_scopes": ["E000_FAST", "E001_FULL"]}), encoding="utf-8")
    return {"s1": s1, "s1b": d / "S1b.log", "s2": d / "s2_scope.json", "s3": d / "S3.log"}


# ----------------------------------------------------------------------------------------------- mutations
def mutate_lane1(o: dict) -> dict:
    m = copy.deepcopy(o); m["flow.json"]["family_id"] = "F3"; m["flow.json"]["inferred_family"] = "F3"; return m


def mutate_lane2(o: dict) -> dict:
    m = copy.deepcopy(o)
    st = m["flow.json"]["steps"][0]; st["bbox_before"], st["bbox_after"] = st["bbox_after"], st["bbox_before"]   # geometry says RIGHT, runner says LEFT
    m["surface_states.json"][0]["visible_label_text"] = ""; m["surface_states.json"][0]["entry_x_norm"] = 0        # GAP-04 violations
    return m


def mutate_lane3(o: dict) -> dict:
    m = copy.deepcopy(o); f = m["flow.json"]
    f["task_flow_sequence"].remove("INPUT_QUERY"); f["experienced_flow_sequence"].remove("INPUT_QUERY")   # dropped typing
    f["steps"] = [s for s in f["steps"] if s["action_token"] != "INPUT_QUERY"]
    return m


def mutate_lane4(outs: dict[str, dict], h: dict, d: pathlib.Path) -> tuple[dict, dict]:
    m = copy.deepcopy(outs)
    m["finance_login_gate"]["action_log.jsonl"].append({"ts": "2026-08-28T10:00:03+09:00", "type": "fill", "target_selector": "input[name=pw]", "accessible_name": "", "value_len": 8, "step_index": 1})
    s1 = d / "s1_dup_bad"; s1.mkdir(parents=True, exist_ok=True)
    (s1 / "C_W1_DUP_LAUNCH_HARNESS.json").write_text(json.dumps({"rc": [0, 1], "evidence_runs_total": 4, "runs_per_target": {"t1": 2, "t2": 2}, "duplicate_suppressed_events": 0}), encoding="utf-8")
    (s1 / "proc2.log").write_text("Scout launched\nBatchOverwriteError\n", encoding="utf-8")
    return m, dict(h, s1=s1)


# ----------------------------------------------------------------------------------------------- driver
def _fails(res: dict) -> list[str]:
    return [f"{i['fixture']}:{i['check']}" for i in res["items"] if i["status"] == "FAIL" and i.get("severity") != "ISOLATED"]


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--workdir", default=None); ap.add_argument("--keep", action="store_true")
    a = ap.parse_args(argv)
    wd = pathlib.Path(a.workdir) if a.workdir else pathlib.Path(tempfile.mkdtemp(prefix="c_gate1_selftest_"))
    amap = AdapterMap.from_dict(SELFTEST_MAP, source="selftest(spec defaults + terminal_dom)")
    ok = True
    lines = []

    def report(lane: str, clean: dict, bad: dict, expect_in_bad: list[str]) -> None:
        nonlocal ok
        cs, bs = clean["summary"], bad["summary"]
        bad_fails = _fails(bad)
        hit = [c for c in expect_in_bad if any(c in f for f in bad_fails)]
        good = cs["status"] == "PASS" and bs["status"] == "FAIL" and len(hit) == len(expect_in_bad)
        ok = ok and good
        lines.append(f"{lane:<6} clean={cs['status']} ({cs['n_items']} items, unmapped={len(cs['unmapped'])}) | mutated={bs['status']} "
                     f"fails={len(bad_fails)} e.g. {bad_fails[:3]} | expected-fail checks hit {len(hit)}/{len(expect_in_bad)} → {'OK' if good else 'NOT OK'}")
        if cs["status"] != "PASS":
            lines.append(f"       clean not PASS: {cs.get('reason')}")

    # lane1
    o = lane1_output(); d1 = write(wd / "lane1" / "C-F2-POS-01", o); d1b = write(wd / "lane1_bad" / "C-F2-POS-01", mutate_lane1(o))
    only = lambda items, fx: {"items": [i for i in items if i["fixture"] == fx]}  # noqa: E731
    r = compare_lane1.compare_all({"C-F2-POS-01": d1}, amap); rb = compare_lane1.compare_all({"C-F2-POS-01": d1b}, amap)
    # other lane1 fixtures were not run → they are UNMAPPED; restrict the PASS claim to the fixture we synthesised
    from common import aggregate
    r1 = {"items": only(r["items"], "C-F2-POS-01")["items"]}; r1["summary"] = aggregate(r1["items"])
    r1b = {"items": only(rb["items"], "C-F2-POS-01")["items"]}; r1b["summary"] = aggregate(r1b["items"])
    report("lane1", r1, r1b, ["echo.family_id", "hash_recompute_over_echo", "forbidden_output_fields_absent"])
    # lane2
    o = lane2_output(); d2 = write(wd / "lane2" / "drawer_left", o); d2b = write(wd / "lane2_bad" / "drawer_left", mutate_lane2(o))
    r = compare_lane2.compare_all({"drawer_left": d2}, amap); rb = compare_lane2.compare_all({"drawer_left": d2b}, amap)
    r2 = {"items": only(r["items"], "drawer_left")["items"]}; r2["summary"] = aggregate(r2["items"])
    r2b = {"items": only(rb["items"], "drawer_left")["items"]}; r2b["summary"] = aggregate(r2b["items"])
    report("lane2", r2, r2b, ["reveal_direction_geom", "gap04.S0"])
    # lane3
    o = lane3_output(); d3 = write(wd / "lane3" / "seq_with_forced_dismissal", o); d3b = write(wd / "lane3_bad" / "seq_with_forced_dismissal", mutate_lane3(o))
    r = compare_lane3.compare_all({"seq_with_forced_dismissal": d3}, amap); rb = compare_lane3.compare_all({"seq_with_forced_dismissal": d3b}, amap)
    r3 = {"items": only(r["items"], "seq_with_forced_dismissal")["items"]}; r3["summary"] = aggregate(r3["items"])
    r3b = {"items": only(rb["items"], "seq_with_forced_dismissal")["items"]}; r3b["summary"] = aggregate(r3b["items"])
    report("lane3", r3, r3b, ["seq.task_flow_sequence", "lossless", "derived.flow_step_count"])
    # lane4
    outs = lane4_s4_outputs(); h = lane4_harness_outputs(wd / "lane4")
    dirs = {tag: write(wd / "lane4" / "runner" / tag, files) for tag, files in outs.items()}
    outs_b, hb = mutate_lane4(outs, h, wd / "lane4")
    dirs_b = {tag: write(wd / "lane4_bad" / "runner" / tag, files) for tag, files in outs_b.items()}
    def l4(dirs_, h_):
        items = [grade_lane4.grade_s1(h_["s1"]), grade_lane4.grade_s1b(h_["s1b"]), grade_lane4.grade_s3(h_["s3"])] + grade_lane4.grade_s2(h_["s2"])
        items += grade_lane4.grade_s4(dirs_, amap)["items"]
        return {"items": items, "summary": aggregate(items)}
    report("lane4", l4(dirs, h), l4(dirs_b, hb), ["finance_login_gate:never_activate", "cross_fixture_invariants", "S1:exactly_once"])
    # dry-run behaviour: no map ⇒ everything UNMAPPED, nothing PASS
    r0 = compare_lane3.compare_all({"seq_with_forced_dismissal": d3}, AdapterMap.none())["summary"]
    nomap_ok = r0["status"] == "NOT_TESTABLE" and r0["counts"].get("PASS", 0) == 0
    ok = ok and nomap_ok
    lines.append(f"no-map  status={r0['status']} PASS={r0['counts'].get('PASS', 0)} UNMAPPED={r0['counts'].get('UNMAPPED', 0)} → {'OK' if nomap_ok else 'NOT OK'}")
    print("\n".join(lines))
    print(f"SELFTEST {'OK' if ok else 'FAILED'}: clean synthetic output PASS on 4 lanes, mutated copies FAIL on the predicted checks, no-map ⇒ UNMAPPED (workdir {wd})")
    if not a.keep and not a.workdir:
        shutil.rmtree(wd, ignore_errors=True)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
