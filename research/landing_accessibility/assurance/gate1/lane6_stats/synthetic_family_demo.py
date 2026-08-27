"""Synthetic family demo — Claude C lane6_stats.

Builds ONE synthetic family (family_id=F_SYN, n=10 service×task rows) with varied raw sequences,
labels and geometry, runs the whole c_flow_derive pipeline, prints the family summary, the 10×10
distance matrices and the denominator chain, and writes demo_output.json next to this file.

Rows are synthetic and fixed (no randomness) so the output is reproducible and hand-checkable.
No B/D data is read. Run:  python3 synthetic_family_demo.py
"""
from __future__ import annotations

import json
import os

import c_flow_derive as C

SYNONYMS = {"로그인": "LOGIN", "login": "LOGIN", "검색": "SEARCH", "찾기": "SEARCH", "조회": "SEARCH",
            "전체메뉴": "MENU", "메뉴": "MENU", "전체 메뉴": "MENU"}

# raw rows: only inputs C is allowed to use (02 §4 raw + label + geometry)
RAW = [
    # service, task_flow, experienced_flow, visible, accessible, x, y, floating, drawer
    ("S01", "OPEN_GLOBAL_MENU > SELECT_FUNCTION > AUTH_GATE",
            "DISMISS_OBSTRUCTION > OPEN_GLOBAL_MENU > SELECT_FUNCTION > AUTH_GATE",
            "조회", "조회", 0.50, 0.30, False, True),
    ("S02", "SELECT_FUNCTION > INPUT_QUERY > SUBMIT_QUERY > SELECT_RESULT > ENDPOINT_REACHED",
            "SELECT_FUNCTION > INPUT_QUERY > SUBMIT_QUERY > SELECT_RESULT > ENDPOINT_REACHED",
            "검색", "검색", 0.50, 0.08, False, False),
    ("S03", "SWITCH_TAB > SELECT_FUNCTION > INPUT_QUERY > SUBMIT_QUERY > ENDPOINT_REACHED",
            "DISMISS_OBSTRUCTION > DISMISS_OBSTRUCTION > SWITCH_TAB > SELECT_FUNCTION > INPUT_QUERY > SUBMIT_QUERY > ENDPOINT_REACHED",
            "조회", "찾기", 0.20, 0.12, False, False),
    ("S04", "OPEN_GLOBAL_MENU > EXPAND_ACCORDION > SELECT_CATEGORY > SELECT_FUNCTION > ENDPOINT_REACHED",
            "OPEN_GLOBAL_MENU > EXPAND_ACCORDION > SELECT_CATEGORY > SELECT_FUNCTION > ENDPOINT_REACHED",
            "", "조회 메뉴", 0.10, 0.20, False, True),
    ("S05", "SELECT_FUNCTION > ENDPOINT_REACHED",
            "SELECT_FUNCTION > ENDPOINT_REACHED",
            "조회하기", "", 0.85, 0.05, False, False),
    ("S06", "AUTH_GATE",
            "DISMISS_OBSTRUCTION > AUTH_GATE",
            None, None, 0.50, 0.50, False, False),
    ("S07", "SELECT_FUNCTION > INPUT_QUERY > SUBMIT_QUERY > AUTH_GATE",
            "SELECT_FUNCTION > INPUT_QUERY > SUBMIT_QUERY > AUTH_GATE",
            "조 회", "조회", 0.90, 0.92, True, False),
    ("S08", "OPEN_LOCAL_MENU > SELECT_FUNCTION > SELECT_RESULT > OPEN_ITEM_DETAIL > ENDPOINT_REACHED",
            "OPEN_LOCAL_MENU > SELECT_FUNCTION > SELECT_RESULT > OPEN_ITEM_DETAIL > ENDPOINT_REACHED",
            "조회", "예약", 0.50, 0.60, False, False),
    ("S09", "SELECT_CATEGORY > SELECT_FUNCTION > SELECT_DATE > SUBMIT_QUERY > ENDPOINT_REACHED",
            "SELECT_CATEGORY > SELECT_FUNCTION > SELECT_DATE > SUBMIT_QUERY > ENDPOINT_REACHED",
            "조회", "조회", 0.50, 0.88, False, False),
    ("S10", "ABSTAIN", "ABSTAIN", "조회", "조회", 0.33, 0.10, False, False),
]


def build_rows() -> list[dict]:
    rows = []
    for sid, tf, ef, vis, ax, x, y, fl, dr in RAW:
        d = C.derive(tf, ef)
        d["service_id"] = sid
        d["family_id"] = "F_SYN"
        d["visible_label_text"] = vis
        d["accessible_name"] = ax
        d["label_relation"] = C.label_relation(vis, ax, SYNONYMS)
        d["entry_x_norm"], d["entry_y_norm"] = x, y
        d["entry_zone"] = C.entry_zone(x, y, fl, dr)
        d["signature"] = C.signature(d["task_flow_sequence"])
        rows.append(d)
    return rows


def main() -> None:
    rows = build_rows()
    numeric = ["activation_depth", "activation_depth_excl_submit", "flow_step_count",
               "nav_container_depth", "forced_dismissal_count"]
    categorical = ["menu_dependency", "auth_gate_stage", "endpoint_status", "label_relation", "entry_zone"]
    summary = C.family_summary(rows, numeric, categorical, family_id="F_SYN")
    matrix = C.pairwise_matrix(rows)
    sigs = C.unique_signatures(rows)

    # denominator chain (05 §6): 10 candidate → 10 frozen → 10 attempted → evidence-bearing → flow-evaluable
    # synthetic: S06 has no evidence beyond a login wall? no — it IS evidence-bearing (AUTH_GATE observed).
    # flow-evaluable excludes ABSTAIN (S10).
    evidence_bearing = [r["service_id"] for r in rows]                      # all 10 have a sequence
    flow_eval = [r["service_id"] for r in rows if r["endpoint_status"] != "ABSTAIN"]
    chain = C.denominator_chain(10, 10, 10, len(evidence_bearing), len(flow_eval), family_id="F_SYN",
                                reasons={"flow_evaluable": [f"{s} ABSTAIN" for s in set(evidence_bearing) - set(flow_eval)]})

    print("=== per-row derived (C recompute) ===")
    hdr = ("service", "act", "act-sub", "steps", "menu", "navd", "dism", "auth_stage", "auth_alt", "endpoint", "label", "zone", "cons")
    print("  ".join(hdr))
    for r in rows:
        print("  ".join(str(v) for v in (r["service_id"], r["activation_depth"], r["activation_depth_excl_submit"],
                                         r["flow_step_count"], r["menu_dependency"], r["nav_container_depth"],
                                         r["forced_dismissal_count"], r["auth_gate_stage"],
                                         r["auth_gate_stage_alt_terminal_is_endpoint"], r["endpoint_status"],
                                         r["label_relation"], r["entry_zone"], r["sequence_consistent"])))
        if r["violations"]:
            print("     violations:", r["violations"])
    print("\n=== family summary ===")
    print(json.dumps(summary, ensure_ascii=False, indent=1))
    print("\n=== unique signatures ===")
    print(json.dumps(sigs, ensure_ascii=False, indent=1))
    print(f"\n=== 10x10 normalized Levenshtein (n_service={matrix['n_service']}, n_pairs={matrix['n_pairs']}; "
          f"{matrix['pseudo_replication_guard']}) ===")
    print("      " + " ".join(f"{s:>5}" for s in matrix["service_ids"]))
    for sid, row in zip(matrix["service_ids"], matrix["levenshtein_norm"]):
        print(f"{sid:>5} " + " ".join(f"{v:5.2f}" for v in row))
    print("\n=== 10x10 LCS similarity ===")
    for sid, row in zip(matrix["service_ids"], matrix["lcs_sim"]):
        print(f"{sid:>5} " + " ".join(f"{v:5.2f}" for v in row))
    print("\n=== denominator chain ===")
    for st in chain["chain"]:
        print(f"  {st['stage']:>16}: {st['count']:2d}  dropped={st['dropped']}  reasons={st['reasons']}")

    out = {"rows": rows, "family_summary": summary, "unique_signatures": sigs, "pairwise": matrix,
           "denominator_chain": chain, "synonym_map": SYNONYMS,
           "pre_registered_choices": {
               "C-1 SUBMIT_QUERY is activation": C.SUBMIT_IS_ACTIVATION_DEFAULT,
               "C-2 form-intent tokens excluded from activation": sorted(C.FORM_INTENT_TOKENS),
               "C-3 reveal tokens": sorted(C.REVEAL_TOKENS),
               "C-4 task-intent tokens": sorted(C.TASK_INTENT_TOKENS),
               "C-5 nav anchor tokens": sorted(C.TASK_CONTROL_ANCHOR_TOKENS),
               "C-6 task select tokens": sorted(C.TASK_SELECT_TOKENS),
               "C-7 zone thresholds": {"top_y": C.ZONE_TOP_Y, "bottom_y": C.ZONE_BOTTOM_Y,
                                       "x_left": C.ZONE_X_LEFT, "x_right": C.ZONE_X_RIGHT},
               "C-8 synonym lookup casefold": True}}
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "demo_output.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print(f"\nwrote {path}")


if __name__ == "__main__":
    main()
