#!/usr/bin/env python3
"""compare_lane1 — task binding + contract hash (lane1_task_binding/EXPECTATIONS.json vs runner output).

Per fixture (one contract of task_contracts.json fed to the runner):
  run_result        exit 0, refusal_reason null (a valid frozen contract must not be refused)
  echo              task_id / family_id / contract_sha256 / endpoint_contract byte-equal to the input (immutable_fields)
  echo_optional     task_family / task_instruction / fixed_fixture — only if the runner echoes them (spec §2 requires 4)
  hash_recompute    sha256 over the 5 canonical fields, echoed values where present, input otherwise == contract_sha256_out
  forbidden_fields  none of output_fields_must_not_exist anywhere in flow.json / run_result.json (recursive key scan)
  endpoint_status   ∈ endpoint_status_allowed and ∉ endpoint_status_forbidden
  auth_gate_stage   ∈ auth_gate_stage_allowed
  legacy_archetype  if present in the flow row, == legacy_archetype_if_present_must_equal
  terminal_dom      body[data-c-state], must_show / must_not_show markers, data-c-forbidden-activated absent,
                    data-c-query — only through the `terminal_dom` table (NOT IN SPEC → UNMAPPED until B provides it)
  non_file_requests non_file_requests_aborted == 0 (C fixtures are self-contained) — ISOLATED
"""
from __future__ import annotations

import argparse
import json
import pathlib
import re
import sys
from typing import Any

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from adapter_map import AdapterMap, RunnerOutput  # noqa: E402
from common import aggregate, contract_sha256, eq_item, item, load_json, norm  # noqa: E402

LANE = pathlib.Path(__file__).resolve().parents[1] / "lane1_task_binding"


def _keys_recursive(o: Any, acc: set[str]) -> set[str]:
    if isinstance(o, dict):
        for k, v in o.items():
            acc.add(str(k))
            _keys_recursive(v, acc)
    elif isinstance(o, list):
        for v in o:
            _keys_recursive(v, acc)
    return acc


def compare_fixture(exp: dict, contract: dict, out: RunnerOutput) -> list[dict]:
    fx = exp["task_id"]
    E = exp["expect"]
    items: list[dict] = []

    # run_result sanity
    items.append(eq_item(fx, "run_result.exit", 0, out.rec_field("run_result", "exit")))
    items.append(eq_item(fx, "run_result.refusal_reason_null", None, out.rec_field("run_result", "refusal_reason")))
    items.append(eq_item(fx, "run_result.non_file_requests_aborted", 0, out.rec_field("run_result", "non_file_requests_aborted"),
                         severity="ISOLATED"))

    # echo of immutable fields (byte-equal, no normalisation)
    for f, key in (("task_id", "task_id_out"), ("family_id", "family_id_out"), ("contract_sha256", "contract_sha256_out"),
                   ("endpoint_contract", "endpoint_contract_out_verbatim")):
        it = eq_item(fx, f"echo.{f}", E[key], out.rec_field("flow", f))
        if it["status"] == "FAIL":
            it["hard_stop"] = "task_contract_drift"
        items.append(it)
    # optional echoes: graded only when present (spec §2 echo set = 4 fields)
    flow = out.record("flow")
    for f in ("task_family", "task_instruction", "fixed_fixture"):
        if flow.ok and out.has_field(f"flow.{f}", flow.value):
            items.append(eq_item(fx, f"echo_optional.{f}", contract.get(f), out.field(f"flow.{f}", flow.value)))
        elif flow.ok:
            items.append(item(fx, f"echo_optional.{f}", contract.get(f), None, "PASS",
                              "not echoed by runner — allowed (spec §2 requires task_id/family_id/endpoint_contract/contract_sha256 only)"))
        else:
            items.append(item(fx, f"echo_optional.{f}", contract.get(f), None, "UNMAPPED", flow.reason))

    # hash recompute over the echo (01 §5 recipe); input values fill the fields the runner does not echo
    if flow.ok:
        merged = {k: contract.get(k) for k in ("family_id", "task_id", "task_instruction", "fixed_fixture", "endpoint_contract")}
        echoed = []
        for k in merged:
            lk = out.field(f"flow.{k}", flow.value)
            if lk.ok:
                merged[k] = lk.value
                echoed.append(k)
        sha_out = out.rec_field("flow", "contract_sha256")
        if sha_out.ok:
            rec = contract_sha256(merged)
            ok = rec == sha_out.value == E["contract_sha256_out"]
            items.append(item(fx, "hash_recompute_over_echo", E["contract_sha256_out"],
                              {"runner_contract_sha256": sha_out.value, "c_recomputed": rec, "echoed_fields": echoed},
                              "PASS" if ok else "FAIL", None if ok else "recomputed hash over the echoed canonical fields differs",
                              hard_stop=None if ok else "task_contract_drift"))
        else:
            items.append(item(fx, "hash_recompute_over_echo", E["contract_sha256_out"], None, "UNMAPPED", sha_out.reason))
    else:
        items.append(item(fx, "hash_recompute_over_echo", E["contract_sha256_out"], None, "UNMAPPED", flow.reason))

    # forbidden output fields (re-binding vocabulary) — recursive key scan of the flow row and run_result
    keys: set[str] = set()
    scanned = []
    for t in ("flow", "run_result"):
        r = out.record(t)
        if r.ok:
            _keys_recursive(r.value, keys)
            scanned.append(t)
    if scanned:
        present = sorted(k for k in E["output_fields_must_not_exist"] if k in keys)
        items.append(item(fx, "forbidden_output_fields_absent", [], present, "PASS" if not present else "FAIL",
                          None if not present else f"re-binding field(s) present: {present}", scanned=scanned,
                          hard_stop=None if not present else "task_or_outcome_leakage"))
    else:
        items.append(item(fx, "forbidden_output_fields_absent", [], None, "UNMAPPED", out.record("flow").reason))

    # endpoint_status partition + auth_gate_stage
    es = out.rec_field("flow", "endpoint_status")
    if es.ok:
        v = str(es.value) if es.value is not None else None
        ok = v in E["endpoint_status_allowed"] and v not in E["endpoint_status_forbidden"]
        items.append(item(fx, "endpoint_status_allowed", E["endpoint_status_allowed"], v, "PASS" if ok else "FAIL",
                          None if ok else f"endpoint_status={v} outside allowed set / inside forbidden set {E['endpoint_status_forbidden']}"))
    else:
        items.append(item(fx, "endpoint_status_allowed", E["endpoint_status_allowed"], None, "UNMAPPED", es.reason))
    ag = out.rec_field("flow", "auth_gate_stage")
    if ag.ok:
        v = str(ag.value) if ag.value is not None else None
        ok = v in E["auth_gate_stage_allowed"]
        items.append(item(fx, "auth_gate_stage_allowed", E["auth_gate_stage_allowed"], v, "PASS" if ok else "FAIL",
                          None if ok else "generic login presence must not become a gate (00 §6 / 03 §7)" if v != "NONE" else "mismatch"))
    else:
        items.append(item(fx, "auth_gate_stage_allowed", E["auth_gate_stage_allowed"], None, "UNMAPPED", ag.reason))

    # legacy_archetype (if present)
    la = out.rec_field("flow", "legacy_archetype")
    if la.ok:
        ok = la.value is None or la.value == E["legacy_archetype_if_present_must_equal"]
        items.append(item(fx, "legacy_archetype_if_present", E["legacy_archetype_if_present_must_equal"], la.value,
                          "PASS" if ok else "FAIL", None if ok else "archetype re-decided"))
    elif flow.ok:
        items.append(item(fx, "legacy_archetype_if_present", E["legacy_archetype_if_present_must_equal"], None, "PASS",
                          "field absent — rule is 'if present'"))
    else:
        items.append(item(fx, "legacy_archetype_if_present", E["legacy_archetype_if_present_must_equal"], None, "UNMAPPED", flow.reason))

    # terminal DOM markers (needs the C-requested terminal_dom capture; UNMAPPED under the current spec)
    td = out.record("terminal_dom")
    if td.ok:
        battrs = out.field("terminal_dom.body_attrs", td.value)
        markers = out.field("terminal_dom.visible_markers", td.value)
        shown = set(markers.value or []) if markers.ok else set()
        state = (battrs.value or {}).get("data-c-state") if battrs.ok else None
        if battrs.ok:
            shown.add(state)
            exp_state = E.get("terminal_body_data_c_state")
            items.append(item(fx, "terminal.body_data_c_state", exp_state, state, "PASS" if state == exp_state else "FAIL"))
            fa = "data-c-forbidden-activated" in (battrs.value or {})
            items.append(item(fx, "terminal.forbidden_activated_absent", True, not fa, "PASS" if not fa else "FAIL",
                              None if not fa else f"body[data-c-forbidden-activated]={battrs.value.get('data-c-forbidden-activated')}",
                              hard_stop=None if not fa else "forbidden_action"))
            q = (battrs.value or {}).get("data-c-query")
            if "terminal_body_data_c_query" in E:
                items.append(item(fx, "terminal.body_data_c_query", E["terminal_body_data_c_query"], q, "PASS" if q == E["terminal_body_data_c_query"] else "FAIL"))
            if "terminal_body_data_c_query_must_contain" in E:
                ok = q is not None and E["terminal_body_data_c_query_must_contain"] in str(q)
                items.append(item(fx, "terminal.body_data_c_query_contains", E["terminal_body_data_c_query_must_contain"], q, "PASS" if ok else "FAIL"))
            if E.get("terminal_body_data_c_query_must_be_absent"):
                items.append(item(fx, "terminal.body_data_c_query_absent", None, q, "PASS" if q is None else "FAIL"))
        else:
            items.append(item(fx, "terminal.body_data_c_state", E.get("terminal_body_data_c_state"), None, "UNMAPPED", battrs.reason))
        if markers.ok or battrs.ok:
            miss = [m for m in E["terminal_state_must_show"] if m not in shown]
            bad = [m for m in E["terminal_state_must_not_show"] if m in shown]
            items.append(item(fx, "terminal.must_show", E["terminal_state_must_show"], sorted(x for x in shown if x), "PASS" if not miss else "FAIL",
                              None if not miss else f"missing {miss}"))
            items.append(item(fx, "terminal.must_not_show", E["terminal_state_must_not_show"], sorted(x for x in shown if x), "PASS" if not bad else "FAIL",
                              None if not bad else f"decoy endpoint shown {bad} (task re-binding)", hard_stop=None if not bad else "task_contract_drift"))
        if E.get("waybill_input_value_must_be_empty"):
            iv = out.field("terminal_dom.input_values", td.value)
            keys = [k for k in (iv.value or {}) if re.search(r"waybill|tracking|운송장", str(k), re.I)] if iv.ok else []
            if not iv.ok or not keys:
                items.append(item(fx, "terminal.waybill_input_empty", True, None, "UNMAPPED", iv.reason if not iv.ok else "terminal_dom.input_values has no waybill/tracking input"))
            else:
                filled = [k for k in keys if iv.value[k]]
                items.append(item(fx, "terminal.waybill_input_empty", True, {k: iv.value[k] for k in keys}, "PASS" if not filled else "FAIL",
                                  None if not filled else "waybill input filled (endpoint_contract: 실사용 번호 입력 금지)", hard_stop=None if not filled else "forbidden_action"))
        if E.get("detail_fields_nonempty"):
            tb = out.field("terminal_dom.text_by_id", td.value)
            if not tb.ok:
                items.append(item(fx, "terminal.detail_fields_nonempty", E["detail_fields_nonempty"], None, "UNMAPPED", tb.reason))
            else:
                empty = [k for k in E["detail_fields_nonempty"] if not norm((tb.value or {}).get(k))]
                items.append(item(fx, "terminal.detail_fields_nonempty", E["detail_fields_nonempty"], {k: (tb.value or {}).get(k) for k in E["detail_fields_nonempty"]},
                                  "PASS" if not empty else "FAIL", None if not empty else f"empty: {empty}"))
    else:
        items.append(item(fx, "terminal.markers", {"show": E["terminal_state_must_show"], "not_show": E["terminal_state_must_not_show"],
                                                   "state": E.get("terminal_body_data_c_state")}, None, "UNMAPPED",
                          td.reason + " — terminal DOM capture is not in gate1_adapter_spec.md (C spec-extension request)"))
    return items


def compare_all(runner_dirs: dict[str, str | pathlib.Path | None], amap: AdapterMap, lane_dir: pathlib.Path = LANE) -> dict:
    """runner_dirs: task_id → runner output dir (None ⇒ not invoked). Returns {items, summary}."""
    ex = load_json(lane_dir / "EXPECTATIONS.json")
    tc = {c["task_id"]: c for c in load_json(lane_dir / "task_contracts.json")["contracts"]}
    items: list[dict] = []
    for exp in ex["expectations"]:
        out = RunnerOutput(runner_dirs.get(exp["task_id"]), amap)
        items += compare_fixture(exp, tc[exp["task_id"]], out)
    summ = aggregate(items)
    # positive control: if the POSITIVE fixture fails, negatives are uninterpretable (P-67)
    pos = [i for i in items if i["fixture"] == "C-F2-POS-01" and i["status"] == "FAIL" and i.get("severity") != "ISOLATED"]
    if pos:
        summ["positive_control_failed"] = [f"{i['check']}" for i in pos]
        summ["reason"] = (summ.get("reason") or "") + " · POSITIVE CONTROL C-F2-POS-01 failed ⇒ harness/adapter defect, negatives uninterpretable"
    summ["hard_stop_observed"] = sorted({i["hard_stop"] for i in items if i.get("hard_stop") and i["status"] == "FAIL"})
    return {"lane": "lane1", "items": items, "summary": summ}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="lane1 comparator")
    ap.add_argument("--runner-root", help="dir containing <task_id>/ runner output dirs")
    ap.add_argument("--adapter-map", default=None)
    ap.add_argument("--out", default=None)
    a = ap.parse_args(argv)
    amap = AdapterMap.load(a.adapter_map)
    ex = load_json(LANE / "EXPECTATIONS.json")
    dirs = {e["task_id"]: (pathlib.Path(a.runner_root) / e["task_id"] if a.runner_root else None) for e in ex["expectations"]}
    res = compare_all(dirs, amap)
    if a.out:
        pathlib.Path(a.out).write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(res["summary"], ensure_ascii=False))
    st = res["summary"]["status"]
    if st == "NOT_TESTABLE":  # Δ46-exit2: no check item ran (UNMAPPED / missing runner dirs) — not "ran and failed"
        print(f"compare_lane1: did not run — read neither as pass nor fail (exit 2): {res['summary']['reason']}", file=sys.stderr)
        return 2
    return 0 if st == "PASS" else 1


if __name__ == "__main__":
    try:
        _rc = main()
    except Exception:  # Δ46-exit2 / Δ50-exit2-common: crash or missing input = did not run, never exit 1 (ran and failed)
        import traceback
        traceback.print_exc()
        print("compare_lane1: did not run — read neither as pass nor fail (exit 2)", file=sys.stderr)
        _rc = 2
    sys.exit(_rc)
