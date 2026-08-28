"""Synthetic family demo — Claude C lane6_stats.

Builds ONE synthetic family (family_id=F_SYN, n=10 PRIMARY service×task rows + 1 SECONDARY_REPEATED row)
with varied raw sequences, labels, geometry, fixture_input_mode and terminal_reason, runs the whole
c_flow_derive pipeline, prints the family summary (under the F1 and the F2 AUTH_GATE rule), the 10×10
distance matrices (three R12 normalisations) and the denominator chain (R4 format), and writes
demo_output.json next to this file.

A rulings exercised: T-A-V3-STEP1-003 R2/R3/R4/R7 + R6 Q8, T-A-V3-STEP1-006 (conditional tokens),
T-A-V3-STEP1-007 R11/R12/R13.
Rows are synthetic and fixed (no randomness) so the output is reproducible and hand-checkable.
No B/D data is read. Run:  python3 synthetic_family_demo.py
"""
from __future__ import annotations

import json
import os

import c_flow_derive as C

# P-30 shape: canonical → [forms], identity implicit (bidirectional lookup in label_relation)
SYNONYMS = {"LOGIN": ["로그인", "login"], "SEARCH": ["검색", "찾기", "조회"], "MENU": ["전체메뉴", "메뉴", "전체 메뉴"]}

# raw rows: only inputs C is allowed to use (02 §4 raw + label + geometry + Δ8-R5 fixture_input_mode + R11 terminal_reason)
RAW = [
    # service, task_role, task_flow, experienced_flow, visible, accessible, x, y, floating, drawer, fixture_input_mode, terminal_reason
    ("S01", "PRIMARY", "OPEN_GLOBAL_MENU > SELECT_FUNCTION > AUTH_GATE",
            "DISMISS_OBSTRUCTION > OPEN_GLOBAL_MENU > SELECT_FUNCTION > AUTH_GATE",
            "조회", "조회", 0.50, 0.30, False, True, None, "AUTH_REQUIRED"),
    ("S02", "PRIMARY", "SELECT_FUNCTION > INPUT_QUERY > SUBMIT_QUERY > SELECT_RESULT > ENDPOINT_REACHED",
            "SELECT_FUNCTION > INPUT_QUERY > SUBMIT_QUERY > SELECT_RESULT > ENDPOINT_REACHED",
            "검색", "검색", 0.50, 0.08, False, False, "FREE_TEXT", None),
    ("S03", "PRIMARY", "SWITCH_TAB > SELECT_FUNCTION > INPUT_QUERY > SUBMIT_QUERY > ENDPOINT_REACHED",
            "DISMISS_OBSTRUCTION > DISMISS_OBSTRUCTION > SWITCH_TAB > SELECT_FUNCTION > INPUT_QUERY > SUBMIT_QUERY > ENDPOINT_REACHED",
            "조회", "찾기", 0.20, 0.12, False, False, "FREE_TEXT", None),
    ("S04", "PRIMARY", "OPEN_GLOBAL_MENU > EXPAND_ACCORDION > SELECT_CATEGORY > SELECT_FUNCTION > ENDPOINT_REACHED",
            "OPEN_GLOBAL_MENU > EXPAND_ACCORDION > SELECT_CATEGORY > SELECT_FUNCTION > ENDPOINT_REACHED",
            "", "조회 메뉴", 0.10, 0.20, False, True, None, None),
    ("S05", "PRIMARY", "SELECT_FUNCTION > ENDPOINT_REACHED",
            "SELECT_FUNCTION > ENDPOINT_REACHED",
            "조회하기", "", 0.85, 0.05, False, False, None, None),
    ("S06", "PRIMARY", "AUTH_GATE",
            "DISMISS_OBSTRUCTION > AUTH_GATE",
            None, None, 0.50, 0.50, False, False, None, "AUTH_REQUIRED"),
    ("S07", "PRIMARY", "SELECT_FUNCTION > INPUT_QUERY > SUBMIT_QUERY > AUTH_GATE",
            "SELECT_FUNCTION > INPUT_QUERY > SUBMIT_QUERY > AUTH_GATE",
            "조 회", "조회", 0.90, 0.92, True, False, "FREE_TEXT", "AUTH_REQUIRED"),
    ("S08", "PRIMARY", "OPEN_LOCAL_MENU > SELECT_FUNCTION > SELECT_RESULT > OPEN_ITEM_DETAIL > ENDPOINT_REACHED",
            "OPEN_LOCAL_MENU > SELECT_FUNCTION > SELECT_RESULT > OPEN_ITEM_DETAIL > ENDPOINT_REACHED",
            "조회", "예약", 0.50, 0.60, False, False, None, None),
    ("S09", "PRIMARY", "SELECT_CATEGORY > SELECT_FUNCTION > SELECT_DATE > SUBMIT_QUERY > ENDPOINT_REACHED",
            "SELECT_CATEGORY > SELECT_FUNCTION > SELECT_DATE > SUBMIT_QUERY > ENDPOINT_REACHED",
            "조회", "조회", 0.50, 0.88, False, False, "DROPDOWN", None),
    ("S10", "PRIMARY", "ABSTAIN", "ABSTAIN", "조회", "조회", 0.33, 0.10, False, False, None, "AMBIGUOUS_MULTIPLE_CANDIDATES"),
    # R3: F1-style secondary repeated task (balance check) on S01 — separate task_id, never in the main n
    ("S01", "SECONDARY_REPEATED", "OPEN_GLOBAL_MENU > SELECT_FUNCTION > ENDPOINT_REACHED",
            "OPEN_GLOBAL_MENU > SELECT_FUNCTION > ENDPOINT_REACHED",
            "잔액", "잔액", 0.50, 0.30, False, True, None, None),
]


def build_rows() -> list[dict]:
    rows = []
    for sid, role, tf, ef, vis, ax, x, y, fl, dr, mode, treason in RAW:
        d = C.derive(tf, ef, input_modes=mode)                 # STEP1-006: row-level fixture_input_mode
        d["service_id"] = sid
        d["family_id"] = "F_SYN"
        d["task_role"] = role
        d["task_id"] = f"F_SYN-{sid}-{'PRI' if role == 'PRIMARY' else 'SEC'}"
        d["fixture_input_mode"] = mode
        d["visible_label_text"] = vis
        d["accessible_name"] = ax
        d["label_relation"] = C.label_relation(vis, ax, SYNONYMS)
        d.update(C.entry_zone_record(x, y, fl, dr))          # R7: zone + raw x/y always retained
        d["terminal_reason"] = treason
        d["terminal_validation"] = C.validate_terminal(d["endpoint_status"], treason)   # R11
        d["signature"] = C.signature(d["task_flow_sequence"])
        rows.append(d)
    return rows


def main() -> None:
    rows = build_rows()
    numeric = ["activation_depth", "activation_depth_excl_submit", "flow_step_count",
               "nav_container_depth", "forced_dismissal_count"]
    categorical = ["menu_dependency", "auth_gate_stage", "endpoint_status", "terminal_reason",
                   "label_relation", "entry_zone"]
    # R2: the same rows summarised under the F1 rule (AUTH_GATE = endpoint reached) and the F2 rule (not reached)
    summary_f1 = C.family_summary(rows, numeric, categorical, family_id="F1")
    summary_f2 = C.family_summary(rows, numeric, categorical, family_id="F2")
    matrix = C.pairwise_matrix(rows)                        # R12: three normalisations stored, primary = max len
    sigs = C.unique_signatures([r for r in rows if r["task_role"] == "PRIMARY"])

    # denominator chain (05 §6 + R4): 10 candidate → replaced 0 → 10 frozen → 10 attempted → evidence-bearing → flow-evaluable
    primary = [r for r in rows if r["task_role"] == "PRIMARY"]
    evidence_bearing = [r["service_id"] for r in primary if C.row_evidence_bearing(r)]
    flow_eval = [r["service_id"] for r in primary if C.row_flow_evaluable(r)]
    chain = C.denominator_chain(
        10, 10, 10, len(evidence_bearing), len(flow_eval), family_id="F_SYN", replaced=[], rows=rows,
        reasons={"flow_evaluable": [f"{s} endpoint_status=ABSTAIN" for s in sorted(set(evidence_bearing) - set(flow_eval))]})
    # illustrative k=1 chain (not this family's data): shows the per-item replacement record format
    chain_k1_example = C.denominator_chain(
        10, 10, 10, 10, 9, family_id="F_EXAMPLE",
        replaced=[{"target_id": "F_EXAMPLE-07", "reason": "NO_PUBLIC_MOBILE_WEB", "reserve_rank": 1,
                   "decided_at": "2026-08-28T03:00:00+09:00", "decided_by": "A"}],
        reasons={"flow_evaluable": ["F_EXAMPLE-03 endpoint_status=ABSTAIN"]})

    print("=== per-row derived (C recompute) ===")
    hdr = ("service", "role", "act", "act-sub", "steps", "menu", "navd", "dism", "auth_stage", "endpoint",
           "term_reason", "label", "zone", "geo_zone", "cons")
    print("  ".join(hdr))
    for r in rows:
        print("  ".join(str(v) for v in (r["service_id"], r["task_role"][:3], r["activation_depth"],
                                         r["activation_depth_excl_submit"], r["flow_step_count"],
                                         r["menu_dependency"], r["nav_container_depth"], r["forced_dismissal_count"],
                                         r["auth_gate_stage"], r["endpoint_status"], r["terminal_reason"],
                                         r["label_relation"], r["entry_zone"], r["entry_zone_geometry_only"],
                                         r["sequence_consistent"])))
        if r["depth_conditional_tokens"]:
            print("     depth_conditional_tokens:", r["depth_conditional_tokens"])
        if r["violations"]:
            print("     violations:", r["violations"])
        if not r["terminal_validation"]["ok"]:
            print("     terminal_validation:", r["terminal_validation"]["violations"])
    print("\n=== family summary under the F1 rule (endpoint_status=AUTH_GATE counts as reached) ===")
    print(json.dumps({k: summary_f1[k] for k in ("filter_condition", "n_primary", "n_secondary_repeated", "n_service",
                                                 "n_pairs", "denominators", "endpoint_reach_rate")},
                     ensure_ascii=False, indent=1))
    print("\n=== family summary under the F2 rule (endpoint_status=AUTH_GATE not reached) ===")
    print(json.dumps({k: summary_f2[k] for k in ("denominators", "endpoint_reach_rate")}, ensure_ascii=False, indent=1))
    print("\n=== numeric / categorical (F2 rule) — each block states its denominator ===")
    print(json.dumps({"numeric": summary_f2["numeric"], "categorical": summary_f2["categorical"]},
                     ensure_ascii=False, indent=1))
    print("\n=== secondary_repeated (summarised separately, never in n) ===")
    print(json.dumps(summary_f2["secondary_repeated"], ensure_ascii=False, indent=1))
    print("\n=== unique signatures (PRIMARY) ===")
    print(json.dumps(sigs, ensure_ascii=False, indent=1))
    print(f"\n=== 10x10 PRIMARY distance = {matrix['primary_distance']} (n_service={matrix['n_service']}, "
          f"n_pairs={matrix['n_pairs']}; {matrix['pseudo_replication_guard']}; {matrix['distance_rule']}) ===")
    print("      " + " ".join(f"{s:>5}" for s in matrix["service_ids"]))
    for sid, row in zip(matrix["service_ids"], matrix["levenshtein_norm"], strict=True):
        print(f"{sid:>5} " + " ".join(f"{v:5.2f}" for v in row))
    print("\n=== 10x10 Yujian-Bo (stored; companion for clustering/MDS) ===")
    for sid, row in zip(matrix["service_ids"], matrix["yujian_bo"], strict=True):
        print(f"{sid:>5} " + " ".join(f"{v:5.2f}" for v in row))
    print(f"cells median: levenshtein_norm={matrix['levenshtein_norm_cells_median']:.3f} "
          f"yujian_bo={matrix['yujian_bo_cells_median']:.3f}")
    print("\n=== 10x10 LCS similarity ===")
    for sid, row in zip(matrix["service_ids"], matrix["lcs_sim"], strict=True):
        print(f"{sid:>5} " + " ".join(f"{v:5.2f}" for v in row))
    print(f"\n=== denominator chain ({chain['format']}; {chain['filter_condition']}) ===")
    for st in chain["chain"]:
        if st["stage"] == "replaced":
            print(f"  {st['stage']:>16}: k={st['k']}  items={st['items']}")
        else:
            print(f"  {st['stage']:>16}: {st['count']:2d}  dropped={st['dropped']}  reasons={st['reasons']}")

    out = {"rows": rows, "family_summary_as_F1": summary_f1, "family_summary_as_F2": summary_f2,
           "unique_signatures": sigs, "pairwise": matrix,
           "denominator_chain": chain, "denominator_chain_k1_example": chain_k1_example,
           "synonym_map": SYNONYMS,
           # Q8: token sets are emitted under an explicit action_token key; the R11 table under endpoint_status.
           "pre_registered_choices": {
               "C-1 SUBMIT_QUERY is activation (CONFIRMED_BY_A T-A-V3-STEP1-006)": C.SUBMIT_IS_ACTIVATION_DEFAULT,
               "C-2 SUPERSEDED_BY_A_STEP1-006: INPUT_QUERY OUT; conditional tokens": {"action_token": sorted(C.CONDITIONAL_ACTIVATION_TOKENS)},
               "STEP1-006 activation IN set": {"action_token": sorted(C.ACTIVATION_IN_TOKENS)},
               "STEP1-006 activation OUT set": {"action_token": sorted(C.ACTIVATION_OUT_TOKENS)},
               "C-3 reveal tokens (SWITCH_TAB is IN activation_depth but not a reveal)": {"action_token": sorted(C.REVEAL_TOKENS)},
               "C-4 task-intent tokens": {"action_token": sorted(C.TASK_INTENT_TOKENS)},
               "C-5 nav anchor tokens": {"action_token": sorted(C.TASK_CONTROL_ANCHOR_TOKENS)},
               "C-6 task select tokens": {"action_token": sorted(C.TASK_SELECT_TOKENS)},
               "C-7 SUPERSEDED_BY_A_R7 (T-A-V3-STEP1-003): zone thresholds": {
                   "top_y": C.ZONE_TOP_Y, "bottom_y": C.ZONE_BOTTOM_Y, "x_left": C.ZONE_X_LEFT, "x_right": C.ZONE_X_RIGHT,
                   "rule": C.ZONE_RULE_ID},
               "C-8 synonym lookup casefold": True,
               "C-11 CONFIRMED_BY_A_R12 (T-A-V3-STEP1-007): primary distance": C.PRIMARY_DISTANCE_KEY,
               "R11 endpoint_status x terminal_reason table (C proposal)": {
                   "endpoint_status": {k: sorted(x or "None" for x in v) for k, v in C.TERMINAL_ALLOWED.items()}},
           }}
    C.assert_field_qualified(out, "demo_output")            # R6 Q8: whole artifact must be layer-qualified
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "demo_output.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print(f"\nwrote {path}")


if __name__ == "__main__":
    import sys
    _rc = 0
    try:
        main()
    except ValueError as _e:  # C.assert_field_qualified (R6 Q8) rejected the artifact = the check ran and FAILED
        if "R6 Q8" not in str(_e):
            raise
        print(f"synthetic_family_demo: FAIL (ran): {_e}", file=sys.stderr)
        _rc = 1
    except Exception:  # Δ46-exit2 / Δ50-exit2-common: crash = did not run
        import traceback
        traceback.print_exc()
        print("synthetic_family_demo: did not run — read neither as pass nor fail (exit 2)", file=sys.stderr)
        _rc = 2
    sys.exit(_rc)
