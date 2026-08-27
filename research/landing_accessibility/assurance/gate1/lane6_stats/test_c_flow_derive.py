"""pytest for c_flow_derive — Claude C lane6_stats.

All expected values in this file were computed BY HAND from SSOTV3
04_FLOW_CODEBOOK_v3.0 (§2/§3/§5) and 05_ANALYSIS_PLAN_v3.0 (§1/§4/§6)
BEFORE the implementation was written. Each test states the arithmetic.
"""
import math

import c_flow_derive as C
import pytest

# ---------------------------------------------------------------- tokens

def test_classify_activation_tokens():
    # expected computed by hand: 04 §5 — activation = state-changing, excl scroll/typing/passive/dismiss
    for t in ["OPEN_GLOBAL_MENU", "OPEN_LOCAL_MENU", "SWITCH_TAB", "EXPAND_ACCORDION",
              "SELECT_CATEGORY", "SELECT_FUNCTION", "SELECT_RESULT",
              "OPEN_ITEM_DETAIL", "OPEN_PLACE_DETAIL"]:
        assert C.classify_token(t)["state_changing_activation"] is True, t
    # C-1 CONFIRMED_BY_A (T-A-V3-STEP1-006): SUBMIT_QUERY is IN activation_depth (flip = sensitivity only)
    assert C.classify_token("SUBMIT_QUERY")["state_changing_activation"] is True
    assert C.classify_token("SUBMIT_QUERY", submit_is_activation=False)["state_changing_activation"] is False
    # STEP1-006 OUT: INPUT_QUERY is typing → flow_step_count only
    assert C.classify_token("INPUT_QUERY")["state_changing_activation"] is False
    assert C.classify_token("INPUT_QUERY")["task_intent"] is True
    assert C.classify_token("INPUT_QUERY")["conditional"] is False
    # STEP1-006 CONDITIONAL: SELECT_ORIGIN/SELECT_DESTINATION/SELECT_DATE depend on the input means used
    for t in ["SELECT_ORIGIN", "SELECT_DESTINATION", "SELECT_DATE"]:
        assert C.classify_token(t)["conditional"] is True, t
        assert C.classify_token(t)["task_intent"] is True, t
        assert C.classify_token(t)["state_changing_activation"] is False          # no mode → UNRESOLVED → OUT
        assert C.classify_token(t)["activation_decision"] == "UNRESOLVED"
        for mode in ("DROPDOWN", "MAP_PAN", "PICKER", "CALENDAR", "dropdown"):
            assert C.classify_token(t, input_mode=mode)["state_changing_activation"] is True, (t, mode)
            assert C.classify_token(t, input_mode=mode)["activation_decision"] == "IN"
        assert C.classify_token(t, input_mode="FREE_TEXT")["state_changing_activation"] is False
        assert C.classify_token(t, input_mode="FREE_TEXT")["activation_decision"] == "OUT"
        for mode in ("MIXED", "OTHER"):
            assert C.classify_token(t, input_mode=mode)["activation_decision"] == "UNRESOLVED"
    # the A IN-list is exactly the 10 tokens of the ruling; SWITCH_TAB is IN activation_depth but not a reveal
    assert {"OPEN_GLOBAL_MENU", "OPEN_LOCAL_MENU", "SWITCH_TAB", "EXPAND_ACCORDION",
                                      "SELECT_CATEGORY", "SELECT_FUNCTION", "SUBMIT_QUERY", "SELECT_RESULT",
                                      "OPEN_ITEM_DETAIL", "OPEN_PLACE_DETAIL"} == C.ACTIVATION_IN_TOKENS
    assert C.ACTIVATION_IN_TOKENS | C.ACTIVATION_OUT_TOKENS | C.CONDITIONAL_ACTIVATION_TOKENS == C.CANONICAL_TOKENS
    assert C.classify_token("SWITCH_TAB")["state_changing_activation"] is True
    assert C.classify_token("SWITCH_TAB")["reveal"] is False
    for t in ["DISMISS_OBSTRUCTION", "AUTH_GATE", "ENDPOINT_REACHED", "ABSTAIN"]:
        assert C.classify_token(t)["state_changing_activation"] is False, t
    # states / obstruction
    assert C.classify_token("DISMISS_OBSTRUCTION")["dismiss"] is True
    assert C.classify_token("DISMISS_OBSTRUCTION")["task_intent"] is False
    assert C.classify_token("AUTH_GATE")["auth"] is True
    assert C.classify_token("AUTH_GATE")["task_intent"] is True   # "auth encounter 포함"
    assert C.classify_token("ENDPOINT_REACHED")["endpoint"] is True
    assert C.classify_token("ENDPOINT_REACHED")["task_intent"] is False
    assert C.classify_token("OPEN_GLOBAL_MENU")["reveal"] is True
    assert C.classify_token("SWITCH_TAB")["reveal"] is False


def test_classify_unknown_token_raises():
    with pytest.raises(ValueError):
        C.classify_token("SCROLL")


# ---------------------------------------------------------------- derive: 04 §3 example

def test_derive_codebook_example():
    # 04 §3: task = OPEN_GLOBAL_MENU > SELECT_FUNCTION > AUTH_GATE
    #        experienced = DISMISS_OBSTRUCTION > OPEN_GLOBAL_MENU > SELECT_FUNCTION > AUTH_GATE
    # expected computed by hand:
    #   activation_depth      = 2  (OPEN_GLOBAL_MENU, SELECT_FUNCTION; AUTH_GATE is a state, not activation)
    #   flow_step_count       = 3  (2 activations + AUTH_GATE encounter, 04 §5 "auth encounter 포함")
    #   menu_dependency       = 1  (OPEN_GLOBAL_MENU before terminal)
    #   nav_container_depth   = 1  (one reveal before SELECT_FUNCTION)
    #   forced_dismissal_count= 1
    #   auth_gate_stage       = AFTER_TASK_SELECT (auth directly after SELECT_FUNCTION, no task body)
    #   auth_gate_stage_alt   = AT_ENDPOINT (literal rule: terminal AUTH_GATE replaces endpoint)
    #   endpoint_status       = AUTH_GATE
    d = C.derive(["OPEN_GLOBAL_MENU", "SELECT_FUNCTION", "AUTH_GATE"],
                 ["DISMISS_OBSTRUCTION", "OPEN_GLOBAL_MENU", "SELECT_FUNCTION", "AUTH_GATE"])
    assert d["activation_depth"] == 2
    assert d["activation_depth_excl_submit"] == 2
    assert d["flow_step_count"] == 3
    assert d["menu_dependency"] == 1
    assert d["nav_container_depth"] == 1
    assert d["forced_dismissal_count"] == 1
    assert d["auth_gate_stage"] == "AFTER_TASK_SELECT"
    assert d["auth_gate_stage_alt_terminal_is_endpoint"] == "AT_ENDPOINT"
    assert d["endpoint_status"] == "AUTH_GATE"
    assert d["sequence_consistent"] is True
    assert d["violations"] == []


def test_derive_typing_and_submit_sequence():
    # task = SELECT_FUNCTION > INPUT_QUERY > SUBMIT_QUERY > SELECT_RESULT > ENDPOINT_REACHED
    # expected computed by hand:
    #   activation_depth            = 3 (SELECT_FUNCTION, SUBMIT_QUERY, SELECT_RESULT; INPUT_QUERY is typing → OUT)
    #   activation_depth_excl_submit= 2
    #   flow_step_count             = 4 (all except ENDPOINT_REACHED)
    #   menu_dependency             = 0
    #   nav_container_depth         = 0
    #   forced_dismissal_count      = 0
    #   auth_gate_stage             = NONE ; endpoint_status = REACHED
    seq = ["SELECT_FUNCTION", "INPUT_QUERY", "SUBMIT_QUERY", "SELECT_RESULT", "ENDPOINT_REACHED"]
    d = C.derive(seq, seq)
    assert d["activation_depth"] == 3
    assert d["activation_depth_excl_submit"] == 2
    assert d["depth_conditional_tokens"] == []                      # no conditional token in this flow
    assert d["activation_depth_conditional_all_in"] == 3 and d["activation_depth_conditional_all_out"] == 3
    assert d["flow_step_count"] == 4
    assert d["menu_dependency"] == 0
    assert d["nav_container_depth"] == 0
    assert d["forced_dismissal_count"] == 0
    assert d["auth_gate_stage"] == "NONE"
    assert d["endpoint_status"] == "REACHED"


def test_derive_scroll_marker_is_rejected_by_default_but_droppable():
    # scroll is NOT a canonical token (04 §4: scroll measured separately). Strict mode raises;
    # lenient mode drops it and records the drop. expected: same numbers as without SCROLL.
    seq = ["SCROLL", "SELECT_FUNCTION", "ENDPOINT_REACHED"]
    with pytest.raises(ValueError):
        C.derive(seq, seq)
    d = C.derive(seq, seq, drop_noncanonical=True)
    assert d["activation_depth"] == 1
    assert d["flow_step_count"] == 1
    assert d["dropped_noncanonical"] == ["SCROLL"]          # unique dropped tokens
    assert d["dropped_noncanonical_count"] == 2             # once per sequence (task + experienced)


def test_derive_nested_reveal_and_auth_positions():
    # nav_container_depth counts reveals BEFORE first task-control token.
    # task = OPEN_GLOBAL_MENU > EXPAND_ACCORDION > SELECT_CATEGORY > SELECT_FUNCTION > OPEN_LOCAL_MENU > ENDPOINT_REACHED
    # expected by hand: nav_container_depth = 2 (the OPEN_LOCAL_MENU after SELECT_FUNCTION is excluded)
    #                   activation_depth = 5 ; menu_dependency = 1
    seq = ["OPEN_GLOBAL_MENU", "EXPAND_ACCORDION", "SELECT_CATEGORY", "SELECT_FUNCTION",
           "OPEN_LOCAL_MENU", "ENDPOINT_REACHED"]
    d = C.derive(seq, seq)
    assert d["nav_container_depth"] == 2
    assert d["activation_depth"] == 5
    assert d["menu_dependency"] == 1

    # BEFORE_TASK_DISCOVERY: auth before any SELECT_FUNCTION/SELECT_CATEGORY
    d = C.derive(["OPEN_GLOBAL_MENU", "AUTH_GATE"], ["OPEN_GLOBAL_MENU", "AUTH_GATE"])
    assert d["auth_gate_stage"] == "BEFORE_TASK_DISCOVERY"
    d = C.derive(["AUTH_GATE"], ["DISMISS_OBSTRUCTION", "AUTH_GATE"])
    assert d["auth_gate_stage"] == "BEFORE_TASK_DISCOVERY"
    assert d["forced_dismissal_count"] == 1

    # P-14 (STEP1-011): submit goes straight to login, no result surface → AFTER_TASK_SELECT, not AT_ENDPOINT;
    # the former C-6 task-body reading survives only as the declared sensitivity field
    seq = ["SELECT_FUNCTION", "INPUT_QUERY", "SUBMIT_QUERY", "AUTH_GATE"]
    d = C.derive(seq, seq)
    assert d["auth_gate_stage"] == "AFTER_TASK_SELECT"
    assert d["auth_gate_stage_alt_terminal_is_endpoint"] == "AT_ENDPOINT"
    # AT_ENDPOINT needs the explicit observation that the endpoint surface rendered before the gate
    assert C.derive(seq, seq, endpoint_surface_rendered_before_gate=True)["auth_gate_stage"] == "AT_ENDPOINT"
    assert C.derive(seq, seq, endpoint_surface_rendered_before_gate=False)["auth_gate_stage"] == "AFTER_TASK_SELECT"
    # auth immediately before ENDPOINT_REACHED is a contract violation (00 §6 AUTH_GATE terminal); tokens alone
    # still give AFTER_TASK_SELECT
    seq = ["SELECT_FUNCTION", "AUTH_GATE", "ENDPOINT_REACHED"]
    d = C.derive(seq, seq)
    assert d["auth_gate_stage"] == "AFTER_TASK_SELECT"
    assert any("AUTH_GATE" in v for v in d["violations"])


def test_derive_sequence_consistency_flag():
    # experienced with dismissals removed must equal task_flow (04 §3). Mismatch -> flag, not raise.
    d = C.derive(["SELECT_FUNCTION", "ENDPOINT_REACHED"],
                 ["DISMISS_OBSTRUCTION", "OPEN_GLOBAL_MENU", "SELECT_FUNCTION", "ENDPOINT_REACHED"])
    assert d["sequence_consistent"] is False
    # dismissal inside task_flow is itself a violation of 04 §3
    d = C.derive(["DISMISS_OBSTRUCTION", "SELECT_FUNCTION"], ["DISMISS_OBSTRUCTION", "SELECT_FUNCTION"])
    assert any("task_flow" in v for v in d["violations"])


def test_p13_p14_auth_stage_rule_step1_011():
    f = C.auth_gate_stage_from_sequence
    # A's task_specific_token_set is exactly these 10 (reveals / SWITCH_TAB / DISMISS are general navigation)
    assert {"SELECT_CATEGORY", "SELECT_FUNCTION", "INPUT_QUERY", "SELECT_ORIGIN",
                                      "SELECT_DESTINATION", "SELECT_DATE", "SUBMIT_QUERY", "SELECT_RESULT",
                                      "OPEN_ITEM_DETAIL", "OPEN_PLACE_DETAIL"} == C.TASK_SPECIFIC_TOKENS
    assert not (C.TASK_SPECIFIC_TOKENS & {"OPEN_GLOBAL_MENU", "OPEN_LOCAL_MENU", "SWITCH_TAB", "EXPAND_ACCORDION",
                                          "DISMISS_OBSTRUCTION"})
    # P-13: OPEN_GLOBAL_MENU > SELECT_CATEGORY > AUTH_GATE → AFTER_TASK_SELECT (category expresses task intent)
    assert f(["OPEN_GLOBAL_MENU", "SELECT_CATEGORY", "AUTH_GATE"]) == "AFTER_TASK_SELECT"
    # P-14: SELECT_FUNCTION > INPUT_QUERY > SUBMIT_QUERY > AUTH_GATE → AFTER_TASK_SELECT (no surface rendered)
    assert f(["SELECT_FUNCTION", "INPUT_QUERY", "SUBMIT_QUERY", "AUTH_GATE"]) == "AFTER_TASK_SELECT"
    # general navigation only → BEFORE_TASK_DISCOVERY
    for seq in (["AUTH_GATE"], ["OPEN_GLOBAL_MENU", "AUTH_GATE"], ["SWITCH_TAB", "EXPAND_ACCORDION", "AUTH_GATE"],
                ["OPEN_LOCAL_MENU", "SWITCH_TAB", "AUTH_GATE"]):
        assert f(seq) == "BEFORE_TASK_DISCOVERY", seq
    # any single task-specific token before the gate → AFTER_TASK_SELECT
    for tok in sorted(C.TASK_SPECIFIC_TOKENS):
        assert f(["OPEN_GLOBAL_MENU", tok, "AUTH_GATE"]) == "AFTER_TASK_SELECT", tok
    # AT_ENDPOINT only with the explicit observation; it never applies before task discovery
    assert f(["SELECT_FUNCTION", "SUBMIT_QUERY", "AUTH_GATE"], endpoint_surface_rendered_before_gate=True) == "AT_ENDPOINT"
    assert f(["OPEN_GLOBAL_MENU", "AUTH_GATE"], endpoint_surface_rendered_before_gate=True) == "BEFORE_TASK_DISCOVERY"
    # 04 §3 example is consistent under the rule
    assert f(["OPEN_GLOBAL_MENU", "SELECT_FUNCTION", "AUTH_GATE"]) == "AFTER_TASK_SELECT"
    d = C.derive(["OPEN_GLOBAL_MENU", "SELECT_FUNCTION", "AUTH_GATE"])
    assert "STEP1-011" in d["auth_gate_stage_rule"] and d["endpoint_surface_rendered_before_gate"] is None
    # GATE 3 comparer picks the observation up from the row
    row = {"task_flow_sequence": ["SELECT_FUNCTION", "SUBMIT_QUERY", "AUTH_GATE"], "task_role": "PRIMARY",
           "endpoint_status": "AUTH_GATE", "terminal_reason": "AUTH_REQUIRED",
           "endpoint_surface_rendered_before_gate": True, "auth_gate_stage": "AT_ENDPOINT"}
    assert C.compare_with_mart_row(row)["match"] is True
    row["endpoint_surface_rendered_before_gate"] = False
    assert C.compare_with_mart_row(row)["diffs"]["auth_gate_stage"] == {"B": "AT_ENDPOINT", "C": "AFTER_TASK_SELECT"}
    # P-17: "don't know" (ABSTAIN) vs "know it is absent" (PUBLIC_WEB_UNOBSERVABLE × TASK_SURFACE_ABSENT) never mix
    assert C.validate_terminal("PUBLIC_WEB_UNOBSERVABLE", "TASK_SURFACE_ABSENT")["ok"]
    assert not C.validate_terminal("ABSTAIN", "TASK_SURFACE_ABSENT")["ok"]
    assert not C.validate_terminal("PUBLIC_WEB_UNOBSERVABLE", "AMBIGUOUS_MULTIPLE_CANDIDATES")["ok"]
    # P-17 layer separation: action_token=ABSTAIN sequence vs endpoint_status are separate keys, Q8-clean
    d = C.derive(["ABSTAIN"])
    assert d["task_flow_sequence"] == ["ABSTAIN"] and d["endpoint_status"] == "ABSTAIN" and C.q8_bare_mentions(d) == []


def test_gap03_flow_step_count_terminals():
    # T-A-V3-STEP1-012 GAP_03 confirms C-4: ENDPOINT_REACHED excluded, AUTH_GATE included, ABSTAIN excluded
    assert C.classify_token("AUTH_GATE")["task_intent"] is True
    assert C.classify_token("ENDPOINT_REACHED")["task_intent"] is False
    assert C.classify_token("ABSTAIN")["task_intent"] is False
    assert C.classify_token("DISMISS_OBSTRUCTION")["task_intent"] is False
    assert C.CANONICAL_TOKENS - {"ENDPOINT_REACHED", "ABSTAIN", "DISMISS_OBSTRUCTION"} == C.TASK_INTENT_TOKENS
    # SELECT_FUNCTION > SUBMIT_QUERY > AUTH_GATE → 3 ; SELECT_FUNCTION > SUBMIT_QUERY > ENDPOINT_REACHED → 2
    assert C.derive(["SELECT_FUNCTION", "SUBMIT_QUERY", "AUTH_GATE"])["flow_step_count"] == 3
    assert C.derive(["SELECT_FUNCTION", "SUBMIT_QUERY", "ENDPOINT_REACHED"])["flow_step_count"] == 2
    # asymmetry with activation_depth (Δ9 excludes AUTH_GATE) is by SSOT text
    assert C.derive(["SELECT_FUNCTION", "SUBMIT_QUERY", "AUTH_GATE"])["activation_depth"] == 2


def test_gap04_null_convention():
    # T-A-V3-STEP1-012 GAP_04 (+ D AMB-X05): unobserved numerics are None (never 0); unobserved categoricals are
    # the explicit UNDETERMINED / NOT_OBSERVED (never "")
    for seq in ([], ["ABSTAIN"], ""):
        d = C.derive(seq)
        assert d["flow_evaluable"] is False, seq
        for v in ("activation_depth", "activation_depth_excl_submit", "flow_step_count", "menu_dependency",
                  "menu_dependency_incl_tab", "menu_dependency_alt_before_anchor", "nav_container_depth"):
            assert d[v] is None, (seq, v)
        assert d["auth_gate_stage"] == "UNDETERMINED" and d["auth_gate_stage_alt_terminal_is_endpoint"] == "UNDETERMINED"
        assert d["forced_dismissal_count"] == 0            # observed from experienced (empty) — a real 0
        assert "GAP_04" in d["null_convention"]
    assert any("empty" in v for v in C.derive([])["violations"])
    assert C.derive([])["endpoint_status"] == "UNRESOLVED_FROM_SEQUENCE"   # explicit string, never ""
    # family_summary: None is missing (excluded from n), never a 0 — median of [4, 4, None] is 4, n=2, n_missing=1
    rows = [{"service_id": "A", "task_role": "PRIMARY", "nav_container_depth": 4},
            {"service_id": "B", "task_role": "PRIMARY", "nav_container_depth": 4},
            {"service_id": "C", "task_role": "PRIMARY", "nav_container_depth": None}]
    s = C.family_summary(rows, ["nav_container_depth"], [], family_id="F2")
    n = s["numeric"]["nav_container_depth"]
    assert n["n"] == 2 and n["n_missing"] == 1 and n["median"] == 4 and n["min"] == 4
    assert "GAP_04" in s["null_convention"]
    # explicit UNDETERMINED / NOT_OBSERVED stay in the categorical denominator as their own category
    rows = [{"service_id": f"S{i}", "task_role": "PRIMARY", "auth_gate_stage": v}
            for i, v in enumerate(["NONE", "NONE", "UNDETERMINED", "NOT_OBSERVED"])]
    c = C.family_summary(rows, [], ["auth_gate_stage"], family_id="F2")["categorical"]["auth_gate_stage"]
    assert c["n"] == 4 and c["n_missing"] == 0 and c["n_unobserved_explicit"] == 2
    # an empty-string categorical is a schema violation → raise
    rows[3]["auth_gate_stage"] = ""
    with pytest.raises(ValueError):
        C.family_summary(rows, [], ["auth_gate_stage"], family_id="F2")
    # entry_zone_record with unobserved coordinates is null-consistent: None / None / NOT_OBSERVED, never 0 or ""
    rec = C.entry_zone_record(None, None, False, False)
    assert rec["entry_x_norm"] is None and rec["entry_y_norm"] is None
    assert rec["entry_zone"] == "NOT_OBSERVED" and rec["entry_zone_geometry_only"] == "NOT_OBSERVED"
    assert rec["entry_zone_observed"] is False
    assert C.entry_zone_record(0.5, 0.1, False, False)["entry_zone_observed"] is True
    with pytest.raises(ValueError):
        C.entry_zone(None, None, False, False)          # the strict function still refuses


def test_p11_nav_anchor_rule():
    # P-11 (C-decided): anchor = first SELECT_FUNCTION or, if absent, first task-body token; reveals before it count.
    # OPEN_GLOBAL_MENU > INPUT_QUERY > SUBMIT_QUERY > ENDPOINT_REACHED → INPUT_QUERY is the anchor → depth 1
    d = C.derive(["OPEN_GLOBAL_MENU", "INPUT_QUERY", "SUBMIT_QUERY", "ENDPOINT_REACHED"])
    assert d["nav_container_depth"] == 1 and d["nav_anchor_found"] is True and d["nav_anchor_action_token"] == "INPUT_QUERY"
    # OPEN_GLOBAL_MENU > AUTH_GATE → nothing else exists, AUTH_GATE is the anchor → depth 1 (stated fallback)
    d = C.derive(["OPEN_GLOBAL_MENU", "AUTH_GATE"])
    assert d["nav_container_depth"] == 1 and d["nav_anchor_found"] is True and d["nav_anchor_action_token"] == "AUTH_GATE"
    # SELECT_CATEGORY is not an anchor: OPEN_GLOBAL_MENU > SELECT_CATEGORY > OPEN_LOCAL_MENU > SELECT_FUNCTION → 2
    d = C.derive(["OPEN_GLOBAL_MENU", "SELECT_CATEGORY", "OPEN_LOCAL_MENU", "SELECT_FUNCTION", "ENDPOINT_REACHED"])
    assert d["nav_container_depth"] == 2 and d["nav_anchor_action_token"] == "SELECT_FUNCTION"
    # no anchor at all (reveals only, path incomplete) → count reveals, nav_anchor_found False
    d = C.derive(["OPEN_GLOBAL_MENU", "EXPAND_ACCORDION"])
    assert d["nav_container_depth"] == 2 and d["nav_anchor_found"] is False and d["nav_anchor_action_token"] is None
    # menu_dependency alt basis (open A item): before-endpoint (primary) vs before-anchor (alt), both reported
    d = C.derive(["SELECT_FUNCTION", "OPEN_LOCAL_MENU", "SELECT_RESULT", "ENDPOINT_REACHED"])
    assert d["menu_dependency"] == 1 and d["menu_dependency_alt_before_anchor"] == 0 and d["nav_container_depth"] == 0
    # discovery-boundary alt (open A item): OPEN_GLOBAL_MENU > AUTH_GATE → primary BEFORE_TASK_DISCOVERY,
    # alt (reveal counts as discovery) AFTER_TASK_SELECT — both reported, neither picked
    d = C.derive(["OPEN_GLOBAL_MENU", "AUTH_GATE"])
    assert d["auth_gate_stage"] == "BEFORE_TASK_DISCOVERY"
    assert d["auth_gate_stage_alt_reveal_is_discovery"] == "AFTER_TASK_SELECT"
    assert d["auth_gate_stage_alt_terminal_is_endpoint"] == "BEFORE_TASK_DISCOVERY"
    assert C.derive(["AUTH_GATE"])["auth_gate_stage_alt_reveal_is_discovery"] == "BEFORE_TASK_DISCOVERY"
    assert C.derive(["ABSTAIN"])["auth_gate_stage_alt_reveal_is_discovery"] == "UNDETERMINED"


def test_p30_synonym_map_canonical_to_forms():
    # P-30 (C-decided): map shape canonical → [forms], identity implicit, bidirectional lookup
    m = {"배송조회": ["택배조회"]}
    assert C.label_relation("배송조회", "택배조회", m) == "SEMANTIC_EQUIV"     # canonical ↔ form, no identity entry
    assert C.label_relation("택배조회", "배송조회", m) == "SEMANTIC_EQUIV"     # form ↔ canonical
    m2 = {"배송조회": ["택배조회", "배송 조회하기"]}
    assert C.label_relation("택배조회", "배송 조회하기", m2) == "SEMANTIC_EQUIV"   # form ↔ form via the canonical
    assert C.label_relation("택배조회", "예약", m2) == "DIFFERENT"
    assert C.label_relation("배송조회", "배송조회", {}) == "MATCH"
    flat = C.normalize_synonym_map(m2)
    assert flat["배송조회"] == "배송조회" and flat["택배조회"] == "배송조회"
    # legacy form → canonical shape still works and may be mixed in
    assert C.label_relation("로그인", "Login", {"로그인": "LOGIN", "login": "LOGIN"}) == "SEMANTIC_EQUIV"
    assert C.label_relation("로그인", "사인인", {"로그인": "LOGIN", "LOGIN": ["사인인"]}) == "SEMANTIC_EQUIV"
    # a form listed under two canonicals is a map defect
    with pytest.raises(ValueError):
        C.normalize_synonym_map({"배송조회": ["조회"], "검색": ["조회"]})


def test_derive_abstain_is_not_flow_evaluable():
    # ABSTAIN (04 §2) → not flow-evaluable (05 §6). expected by hand: derived numerics None, not 0;
    # forced_dismissal_count still counted from experienced (obstruction layer is independent of judgement).
    d = C.derive(["ABSTAIN"], ["DISMISS_OBSTRUCTION", "ABSTAIN"])
    assert d["flow_evaluable"] is False
    assert d["activation_depth"] is None and d["flow_step_count"] is None
    assert d["menu_dependency"] is None and d["nav_container_depth"] is None
    assert d["auth_gate_stage"] == "UNDETERMINED"            # R13: never NONE for an unobserved gate
    assert d["endpoint_status"] == "ABSTAIN"
    assert d["forced_dismissal_count"] == 1
    # family_summary then reports the shrunken denominator explicitly (R2): entry_structure_n=10 (the ABSTAIN
    # row is evidence-bearing) but endpoint_dependent_n=9 → activation_depth n=9 over denominator 9, n_missing=0
    rows = ([{"service_id": f"S{i}", "task_role": "PRIMARY", "activation_depth": 2} for i in range(9)]
            + [{"service_id": "S9", "task_role": "PRIMARY", **d}])
    s = C.family_summary(rows, ["activation_depth"], [], family_id="F2")
    assert s["n_service"] == 10
    assert s["denominators"]["entry_structure_n"] == 10 and s["denominators"]["endpoint_dependent_n"] == 9
    a = s["numeric"]["activation_depth"]
    assert a["denominator"] == "endpoint_dependent_n" and a["denominator_n"] == 9
    assert a["n"] == 9 and a["n_missing"] == 0 and a["median"] == 2


def test_endpoint_status_from_sequence():
    assert C.endpoint_status_from_sequence(["SELECT_FUNCTION", "ENDPOINT_REACHED"]) == "REACHED"
    assert C.endpoint_status_from_sequence(["SELECT_FUNCTION", "AUTH_GATE"]) == "AUTH_GATE"
    assert C.endpoint_status_from_sequence(["ABSTAIN"]) == "ABSTAIN"
    assert C.endpoint_status_from_sequence(["SELECT_FUNCTION"]) == "UNRESOLVED_FROM_SEQUENCE"
    assert C.endpoint_status_from_sequence([]) == "UNRESOLVED_FROM_SEQUENCE"


# ---------------------------------------------------------------- label relation

SYN = {"로그인": "LOGIN", "login": "LOGIN", "사인인": "LOGIN", "검색": "SEARCH", "찾기": "SEARCH"}

def test_label_relation_cases():
    # expected computed by hand
    assert C.label_relation("로그인", "로그인", SYN) == "MATCH"
    # NFD vs NFC of 한글 '로그인': NFC-normalized → MATCH
    import unicodedata
    nfd = unicodedata.normalize("NFD", "로그인")
    assert nfd != "로그인"
    assert C.label_relation("로그인", nfd, SYN) == "MATCH"
    # whitespace: "전체  메뉴 " vs "전체 메뉴" → MATCH
    assert C.label_relation("전체  메뉴 ", "전체 메뉴", SYN) == "MATCH"
    # semantic via explicit map
    assert C.label_relation("로그인", "Login", SYN) == "SEMANTIC_EQUIV"
    assert C.label_relation("검색", "찾기", SYN) == "SEMANTIC_EQUIV"
    # different, both non-empty, not mapped
    assert C.label_relation("로그인", "검색", SYN) == "DIFFERENT"
    assert C.label_relation("로그인", "예약", SYN) == "DIFFERENT"
    # one side empty
    assert C.label_relation("메뉴", "", SYN) == "VISIBLE_ONLY"
    assert C.label_relation("메뉴", None, SYN) == "VISIBLE_ONLY"
    assert C.label_relation("", "메뉴", SYN) == "AX_ONLY"
    assert C.label_relation("   ", "메뉴", SYN) == "AX_ONLY"
    assert C.label_relation("", "", SYN) == "NONE"
    assert C.label_relation(None, None, {}) == "NONE"
    # case: default strict → "Login" vs "login" is SEMANTIC_EQUIV via map only; without map → DIFFERENT
    assert C.label_relation("Login", "login", {}) == "DIFFERENT"
    assert C.label_relation("Login", "login", {}, casefold=True) == "MATCH"


# ---------------------------------------------------------------- sequence distance

def test_levenshtein_and_lcs():
    a = ["OPEN_GLOBAL_MENU", "SELECT_FUNCTION", "ENDPOINT_REACHED"]
    # identical → lev 0, lcs_sim 1
    d = C.seq_distance(a, a)
    assert d["levenshtein"] == 0 and d["levenshtein_norm"] == 0.0 and d["lcs_sim"] == 1.0
    # fully different, same length 3 → lev 3, norm 1.0, lcs 0
    b = ["SWITCH_TAB", "INPUT_QUERY", "AUTH_GATE"]
    d = C.seq_distance(a, b)
    assert d["levenshtein"] == 3 and d["levenshtein_norm"] == 1.0 and d["lcs_len"] == 0 and d["lcs_sim"] == 0.0
    # one insertion: a (3) vs a+1 (4) → lev 1, norm 1/4 = 0.25 ; LCS = 3, lcs_sim = 3/4 = 0.75
    c = ["OPEN_GLOBAL_MENU", "SELECT_FUNCTION", "SUBMIT_QUERY", "ENDPOINT_REACHED"]
    d = C.seq_distance(a, c)
    assert d["levenshtein"] == 1 and d["levenshtein_norm"] == 0.25
    assert d["lcs_len"] == 3 and d["lcs_sim"] == 0.75
    # token-level not character-level: two tokens sharing characters are still fully different
    d = C.seq_distance(["SELECT_FUNCTION"], ["SELECT_CATEGORY"])
    assert d["levenshtein"] == 1 and d["levenshtein_norm"] == 1.0
    # both empty → 0 distance, sim 1 by convention
    d = C.seq_distance([], [])
    assert d["levenshtein_norm"] == 0.0 and d["lcs_sim"] == 1.0
    # substitution + LCS: [A,B,C] vs [A,X,C] → lev 1 (norm 1/3), LCS 2 (sim 2/3)
    d = C.seq_distance(["A", "B", "C"], ["A", "X", "C"])
    assert d["levenshtein"] == 1 and abs(d["levenshtein_norm"] - 1 / 3) < 1e-12
    assert d["lcs_len"] == 2 and abs(d["lcs_sim"] - 2 / 3) < 1e-12


# ---------------------------------------------------------------- R12: three normalisations (T-A-V3-STEP1-007)

def test_seq_distance_r12_three_normalisations():
    # the ticket's worked pair: ['A'] vs ['B'] → max 1.0 / sum 0.5 / Yujian-Bo 2·1/(1+1+1) = 0.667
    d = C.seq_distance(["A"], ["B"])
    assert d["levenshtein_norm"] == 1.0 and d["levenshtein_norm_sum"] == 0.5 and abs(d["yujian_bo"] - 2 / 3) < 1e-12
    assert d["primary_distance"] == "levenshtein_norm"
    # one insertion: len 3 vs 4, lev 1 → max 0.25 ; sum 1/7 ; YB 2/(7+1) = 0.25
    d = C.seq_distance(["A", "B", "C"], ["A", "B", "X", "C"])
    assert d["levenshtein_norm"] == 0.25 and abs(d["levenshtein_norm_sum"] - 1 / 7) < 1e-12 and d["yujian_bo"] == 0.25
    # identical → all 0 ; both empty → all 0
    for a, b in ((["A", "B"], ["A", "B"]), ([], [])):
        d = C.seq_distance(a, b)
        assert d["levenshtein_norm"] == 0.0 and d["levenshtein_norm_sum"] == 0.0 and d["yujian_bo"] == 0.0
    # Yujian-Bo is a metric: triangle inequality on a small triple ([A,B],[A,C],[C]) — computed by hand:
    #   d(AB,AC)=2·1/(4+1)=0.4 ; d(AC,C)=2·1/(3+1)=0.5 ; d(AB,C)=2·2/(3+2)=0.8 ≤ 0.4+0.5
    ab, ac, c = ["A", "B"], ["A", "C"], ["C"]
    yb = lambda x, y: C.seq_distance(x, y)["yujian_bo"]   # noqa: E731
    assert abs(yb(ab, ac) - 0.4) < 1e-12 and abs(yb(ac, c) - 0.5) < 1e-12 and abs(yb(ab, c) - 0.8) < 1e-12
    assert yb(ab, c) <= yb(ab, ac) + yb(ac, c) + 1e-12
    # pairwise_matrix stores all three and flags the clustering companion
    seqs = [["A", "B"]] * 5 + [["A", "C"]] * 5
    m = C.pairwise_matrix(_rows(seqs))
    assert m["primary_distance"] == "levenshtein_norm" and m["single_scalar_source"] == "levenshtein_norm"
    assert m["levenshtein_norm"][0][5] == 0.5 and m["levenshtein_norm_sum"][0][5] == 0.25
    assert abs(m["yujian_bo"][0][5] - 0.4) < 1e-12                      # 2·1/(2+2+1)
    assert m["for_clustering_or_mds"] is False and m["clustering_companion"] is None
    m2 = C.pairwise_matrix(_rows(seqs), for_clustering_or_mds=True)
    assert m2["clustering_companion"] == "yujian_bo" and m2["yujian_bo_cells_median"] is not None
    assert "R12" in m2["distance_rule"] and "C-11 CONFIRMED_BY_A_R12" in m2["distance_rule"]


# ---------------------------------------------------------------- R13: auth_gate_stage UNDETERMINED

def test_auth_gate_stage_undetermined_vs_none():
    f = C.auth_gate_stage_from_sequence
    # NONE only for a fully observed path with no gate
    assert f(["SELECT_FUNCTION", "ENDPOINT_REACHED"]) == "NONE"
    assert f(["OPEN_GLOBAL_MENU", "SELECT_FUNCTION", "SUBMIT_QUERY", "ENDPOINT_REACHED"]) == "NONE"
    # incomplete path (no terminal) → UNDETERMINED, never NONE
    assert f(["SELECT_FUNCTION"]) == "UNDETERMINED"
    assert f(["OPEN_GLOBAL_MENU", "SELECT_FUNCTION", "INPUT_QUERY"]) == "UNDETERMINED"
    assert f([]) == "UNDETERMINED"
    assert f(["ABSTAIN"]) == "UNDETERMINED"
    # explicit endpoint evidence overrides the sequence reading in both directions
    assert f(["SELECT_FUNCTION"], endpoint_reached=True) == "NONE"
    assert f(["SELECT_FUNCTION", "ENDPOINT_REACHED"], endpoint_reached=False) == "UNDETERMINED"
    # gate positions unchanged
    assert f(["AUTH_GATE"]) == "BEFORE_TASK_DISCOVERY"
    assert f(["SELECT_FUNCTION", "AUTH_GATE"]) == "AFTER_TASK_SELECT"
    assert {"NONE", "UNDETERMINED", "BEFORE_TASK_DISCOVERY", "AFTER_TASK_SELECT", "AT_ENDPOINT"} == C.AUTH_GATE_STAGES
    # derive: a truncated non-ABSTAIN path is UNDETERMINED; ABSTAIN is UNDETERMINED (not None, not NONE)
    assert C.derive(["SELECT_FUNCTION", "INPUT_QUERY"])["auth_gate_stage"] == "UNDETERMINED"
    assert C.derive(["ABSTAIN"])["auth_gate_stage"] == "UNDETERMINED"
    assert C.derive(["ABSTAIN"])["auth_gate_stage_alt_terminal_is_endpoint"] == "UNDETERMINED"
    # aggregation keeps UNDETERMINED as a category (R13 "분모에서 빼지 말고 별도 범주로")
    rows = [{"service_id": f"S{i}", "task_role": "PRIMARY", "auth_gate_stage": "NONE" if i < 7 else "UNDETERMINED"}
            for i in range(10)]
    c = C.family_summary(rows, [], ["auth_gate_stage"], family_id="F3")["categorical"]["auth_gate_stage"]
    assert c["n"] == 10 and c["n_missing"] == 0 and c["distribution"] == {"NONE": 7, "UNDETERMINED": 3}


# ---------------------------------------------------------------- STEP1-006: conditional activation tokens

def test_conditional_tokens_dropdown_vs_free_text():
    # F3-style flow: SELECT_FUNCTION > SELECT_ORIGIN > SELECT_DESTINATION > SELECT_DATE > SUBMIT_QUERY > ENDPOINT_REACHED
    # expected by hand (STEP1-006): base IN = SELECT_FUNCTION + SUBMIT_QUERY = 2
    #   all three conditional via DROPDOWN → 2 + 3 = 5 ; all FREE_TEXT → 2 ; flow_step_count = 5 either way
    seq = ["SELECT_FUNCTION", "SELECT_ORIGIN", "SELECT_DESTINATION", "SELECT_DATE", "SUBMIT_QUERY", "ENDPOINT_REACHED"]
    dd = C.derive(seq, input_modes="DROPDOWN")
    ft = C.derive(seq, input_modes="FREE_TEXT")
    assert dd["activation_depth"] == 5 and ft["activation_depth"] == 2
    assert dd["flow_step_count"] == 5 and ft["flow_step_count"] == 5
    assert dd["violations"] == [] and ft["violations"] == []
    assert [t["decision"] for t in dd["depth_conditional_tokens"]] == ["IN", "IN", "IN"]
    assert [t["decision"] for t in ft["depth_conditional_tokens"]] == ["OUT", "OUT", "OUT"]
    assert [t["index"] for t in dd["depth_conditional_tokens"]] == [1, 2, 3]
    assert dd["depth_conditional_tokens"][2]["token"] == "SELECT_DATE"
    assert dd["depth_conditional_tokens"][2]["fixture_input_mode"] == "DROPDOWN"
    # the required test: SELECT_DATE under DROPDOWN vs FREE_TEXT differs by exactly 1
    seq2 = ["SELECT_FUNCTION", "INPUT_QUERY", "SELECT_DATE", "SUBMIT_QUERY", "ENDPOINT_REACHED"]
    d_drop = C.derive(seq2, input_modes={2: "DROPDOWN"})
    d_free = C.derive(seq2, input_modes={2: "FREE_TEXT"})
    assert d_drop["activation_depth"] - d_free["activation_depth"] == 1
    assert d_drop["activation_depth"] == 3 and d_free["activation_depth"] == 2      # SELECT_FUNCTION + SUBMIT (+ DATE)
    assert d_drop["activation_depth_conditional_all_in"] == 3 and d_drop["activation_depth_conditional_all_out"] == 2
    assert d_free["activation_depth_conditional_all_in"] == 3 and d_free["activation_depth_conditional_all_out"] == 2
    # MIXED per observation: per-token means actually used (origin typed, date via calendar picker)
    mx = C.derive(seq, input_modes=[None, "FREE_TEXT", "FREE_TEXT", "CALENDAR", None, None])
    assert mx["activation_depth"] == 3
    assert [t["decision"] for t in mx["depth_conditional_tokens"]] == ["OUT", "OUT", "IN"]
    # unresolved (no mode / MIXED at token level) → counted OUT in primary and flagged, bounds reported
    un = C.derive(seq2)
    assert un["activation_depth"] == 2 and un["depth_conditional_tokens"][0]["decision"] == "UNRESOLVED"
    assert any("SELECT_DATE" in v and "fixture_input_mode" in v for v in un["violations"])
    un2 = C.derive(seq2, input_modes="MIXED")
    assert un2["depth_conditional_tokens"][0]["decision"] == "UNRESOLVED"
    with pytest.raises(ValueError):
        C.derive(seq2, input_modes=["DROPDOWN"])           # misaligned per-token list
    # a row-level fixture_input_mode is picked up by the GATE 3 comparer
    row = {"task_flow_sequence": seq2, "fixture_input_mode": "DROPDOWN", "activation_depth": 3, "task_role": "PRIMARY",
           "endpoint_status": "REACHED"}
    assert C.compare_with_mart_row(row)["match"] is True
    row["activation_depth"] = 2
    assert C.compare_with_mart_row(row)["diffs"]["activation_depth"] == {"B": 2, "C": 3}
    assert "T-A-V3-STEP1-006" in C.derive(seq2, input_modes="DROPDOWN")["activation_rule"]


# ---------------------------------------------------------------- R11: terminal_reason companion

def test_validate_terminal_table():
    ok = lambda es, tr, note=None: C.validate_terminal(es, tr, note)["ok"]   # noqa: E731
    # allowed pairs (C proposal table)
    assert ok("REACHED", None)
    assert ok("AUTH_GATE", "AUTH_REQUIRED")
    for tr in ("TIMEOUT", "WAF_BLOCK", "ACTIVE_CHALLENGE", "CONTROL_DISABLED_OR_INERT", "FORBIDDEN_ACTION_REQUIRED"):
        assert ok("BLOCKED", tr), tr
    for tr in ("NO_PUBLIC_MOBILE_WEB", "TASK_SURFACE_ABSENT"):
        assert ok("PUBLIC_WEB_UNOBSERVABLE", tr), tr
    assert ok("APP_REQUIRED", "APP_REQUIRED")
    for tr in ("EVIDENCE_DEFECT", "REPLAY_BROKEN"):
        assert ok("EVIDENCE_DEFECT", tr), tr
    assert ok("ABSTAIN", "AMBIGUOUS_MULTIPLE_CANDIDATES")
    assert ok("ABSTAIN", "OTHER", "two equally plausible task controls; see screenshot")
    # unified C rule (gate1/c_terminal_table.py, shared with lane5): OTHER allowed with ANY non-REACHED status, note mandatory
    for es in sorted(C.ENDPOINT_STATUSES - {"REACHED"}):
        assert ok(es, "OTHER", "annotated"), es
        assert not ok(es, "OTHER"), es
        assert not ok(es, "OTHER", ""), es
    assert not ok("REACHED", "OTHER", "annotated")           # REACHED admits null only
    import c_terminal_table as T
    assert C.TERMINAL_ALLOWED == {es: (frozenset({None}) if es == "REACHED" else rs) for es, rs in T.TERMINAL_ALLOWED.items()}
    assert T.selftest() == []
    # every R11 value is reachable from at least one endpoint_status
    covered = set().union(*(s - {None} for s in C.TERMINAL_ALLOWED.values()))
    assert covered == C.TERMINAL_REASONS
    assert set(C.TERMINAL_ALLOWED) == C.ENDPOINT_STATUSES
    # impossible / missing combinations
    assert not ok("REACHED", "TIMEOUT")                      # ticket's example
    assert not ok("REACHED", "AUTH_REQUIRED")
    assert not ok("AUTH_GATE", None)                         # both fields mandatory for a non-REACHED terminal
    assert not ok("AUTH_GATE", "TIMEOUT")
    assert not ok("BLOCKED", "AUTH_REQUIRED")
    assert not ok("PUBLIC_WEB_UNOBSERVABLE", "APP_REQUIRED")
    assert not ok("ABSTAIN", "OTHER")                        # OTHER without note
    assert not ok("ABSTAIN", "OTHER", "   ")
    assert not ok(None, "TIMEOUT")
    assert not ok("DONE", None)                              # not in SSOT enum
    assert not ok("BLOCKED", "RATE_LIMIT")                   # not in R11 enum
    r = C.validate_terminal("REACHED", "TIMEOUT")
    assert r["violations"] and "REACHED" in r["violations"][0] and C.q8_bare_mentions(r) == []
    with pytest.raises(ValueError):
        C.assert_terminal("REACHED", "TIMEOUT")
    # compare_with_mart_row flags an impossible pair on a B row
    row = {"task_flow_sequence": ["SELECT_FUNCTION", "ENDPOINT_REACHED"], "task_role": "PRIMARY",
           "endpoint_status": "REACHED", "terminal_reason": "TIMEOUT"}
    d = C.compare_with_mart_row(row)
    assert d["match"] is False and "terminal_reason" in d["diffs"]
    row["terminal_reason"] = None
    assert C.compare_with_mart_row(row)["match"] is True


def _rows(seqs, role="PRIMARY"):
    return [{"service_id": f"S{i:02d}", "task_role": role, "task_flow_sequence": s} for i, s in enumerate(seqs)]


def test_pairwise_matrix_and_signatures():
    seqs = [["A", "B"]] * 5 + [["A", "C"]] * 5      # n=10
    m = C.pairwise_matrix(_rows(seqs))
    assert m["n_service"] == 10 and m["n_pairs"] == 45
    assert m["filter_condition"] == "task_role == 'PRIMARY'"          # R3 literal
    assert "pairs are cells" in m["pseudo_replication_guard"]
    L = m["levenshtein_norm"]
    assert len(L) == 10 and all(len(r) == 10 for r in L)
    assert L[0][0] == 0.0 and L[0][1] == 0.0
    assert L[0][5] == 0.5 and L[5][0] == 0.5        # symmetric, one substitution of 2 → 0.5
    # off-diagonal cell count = 45 upper triangle
    assert m["n_pairs"] == sum(1 for i in range(10) for j in range(i + 1, 10))
    sig = C.unique_signatures(_rows(seqs))
    assert sig["n_unique"] == 2
    assert sig["signature_counts"]["A>B"] == 5 and sig["signature_counts"]["A>C"] == 5
    # Q8: a single-token signature such as 'AUTH_GATE' is legal only under the qualifying signature keys
    one = C.unique_signatures(_rows([["AUTH_GATE"], ["ABSTAIN"], ["SELECT_FUNCTION", "ENDPOINT_REACHED"]]))
    assert one["signature_counts"]["AUTH_GATE"] == 1 and C.q8_bare_mentions(one) == []
    assert C.q8_bare_mentions({"signature": "AUTH_GATE"}) == [] and C.q8_bare_mentions({"sig": "AUTH_GATE"})


# ---------------------------------------------------------------- family summary

def test_family_summary_numeric_and_entropy():
    # activation_depth values 1..10 : median = 5.5 ; Q1 (type-7) = 1 + 0.25*9 = 3.25 ; Q3 = 7.75 ; IQR = 4.5 ; range (1,10)
    rows = [{"service_id": f"S{i}", "task_role": "PRIMARY", "activation_depth": i, "entry_zone": z}
            for i, z in zip(range(1, 11), ["TOP_LEFT", "TOP_CENTER", "TOP_RIGHT", "MID", "BOTTOM",
                                           "FLOATING", "DRAWER", "TOP_LEFT", "TOP_CENTER", "TOP_RIGHT"], strict=True)]
    s = C.family_summary(rows, numeric_vars=["activation_depth"], categorical_vars=["entry_zone"], family_id="F3")
    assert s["n_service"] == 10 and s["n_pairs"] == 45
    assert s["pseudo_replication_guard"] == "pairs are cells, not independent n"
    num = s["numeric"]["activation_depth"]
    assert num["denominator"] == "endpoint_dependent_n" and num["denominator_n"] == 10   # R2: stated per block
    assert s["categorical"]["entry_zone"]["denominator"] == "entry_structure_n"
    assert num["n"] == 10 and num["median"] == 5.5
    assert num["q1"] == 3.25 and num["q3"] == 7.75 and num["iqr"] == 4.5
    assert num["min"] == 1 and num["max"] == 10
    # entropy: 3 zones with 2 each, 4 zones with 1 each → H = 3*(0.2*log2(5)) + 4*(0.1*log2(10))
    H = 3 * 0.2 * math.log2(5) + 4 * 0.1 * math.log2(10)
    cat = s["categorical"]["entry_zone"]
    assert abs(cat["entropy_bits"] - H) < 1e-12
    assert cat["distribution"]["TOP_LEFT"] == 2 and cat["k_observed"] == 7


def test_family_summary_uniform_vs_degenerate_entropy():
    # uniform over 10 distinct categories → H = log2(10) ; degenerate → 0
    DM = {"z": "entry_structure_n"}     # R2: an undeclared variable must be assigned a denominator
    uni = [{"service_id": f"S{i}", "task_role": "PRIMARY", "z": f"Z{i}"} for i in range(10)]
    deg = [{"service_id": f"S{i}", "task_role": "PRIMARY", "z": "Z0"} for i in range(10)]
    su = C.family_summary(uni, numeric_vars=[], categorical_vars=["z"], family_id="F4", denominator_map=DM)["categorical"]["z"]
    sd = C.family_summary(deg, numeric_vars=[], categorical_vars=["z"], family_id="F4", denominator_map=DM)["categorical"]["z"]
    assert abs(su["entropy_bits"] - math.log2(10)) < 1e-12 and su["entropy_norm"] == 1.0
    assert sd["entropy_bits"] == 0.0 and sd["entropy_norm"] == 0.0
    # binary 5/5 → 1 bit
    half = [{"service_id": f"S{i}", "task_role": "PRIMARY", "z": "A" if i < 5 else "B"} for i in range(10)]
    assert C.family_summary(half, [], ["z"], family_id="F4", denominator_map=DM)["categorical"]["z"]["entropy_bits"] == 1.0
    # undeclared denominator → raise (never silently picked)
    with pytest.raises(ValueError):
        C.family_summary(half, [], ["z"], family_id="F4")


def test_family_summary_missing_and_n_not_10():
    DM = {"v": "entry_structure_n"}
    rows = [{"service_id": f"S{i}", "task_role": "PRIMARY", "v": (i if i < 7 else None)} for i in range(10)]
    s = C.family_summary(rows, ["v"], [], family_id="F5", denominator_map=DM)
    assert s["numeric"]["v"]["n"] == 7 and s["numeric"]["v"]["n_missing"] == 3
    assert s["numeric"]["v"]["denominator_n"] == 10
    assert s["numeric"]["v"]["median"] == 3        # 0..6 → median 3
    s9 = C.family_summary(rows[:9], ["v"], [], family_id="F5", denominator_map=DM)
    assert s9["n_service"] == 9 and s9["n_pairs"] == 36 and s9["n_service_warning"]


# ---------------------------------------------------------------- R2: two denominators (T-A-V3-STEP1-003)

def _r2_rows():
    # 10 PRIMARY rows: 6 REACHED, 3 AUTH_GATE, 1 ABSTAIN. All carry an entry-structure observation
    # (auth_gate_stage / entry_zone) — the ABSTAIN row has auth_gate_stage None (C-9) but a zone.
    rows = []
    for i in range(10):
        es = "REACHED" if i < 6 else ("AUTH_GATE" if i < 9 else "ABSTAIN")
        rows.append({"service_id": f"S{i}", "task_role": "PRIMARY", "endpoint_status": es,
                     "flow_evaluable": es != "ABSTAIN",
                     "activation_depth": None if es == "ABSTAIN" else (i + 1),
                     "auth_gate_stage": ("UNDETERMINED" if es == "ABSTAIN"
                                         else ("AFTER_TASK_SELECT" if es == "AUTH_GATE" else "NONE")),
                     "entry_zone": "TOP_LEFT" if i % 2 else "MID"})
    return rows


def test_family_summary_two_denominators_f1_vs_f2():
    # expected by hand: entry_structure_n = 10 (ABSTAIN + AUTH_GATE rows are evidence-bearing)
    #                   endpoint_dependent_n = 9 (ABSTAIN excluded)
    #   F1: endpoint_status=AUTH_GATE counts as reached → 6 + 3 = 9 / 9 = 1.0
    #   F2: AUTH_GATE is not reached but stays in the denominator → 6 / 9
    for fid, num, rate in (("F1", 9, 1.0), ("F2", 6, 6 / 9)):
        s = C.family_summary(_r2_rows(), ["activation_depth"], ["auth_gate_stage", "entry_zone", "endpoint_status"],
                             family_id=fid)
        d = s["denominators"]
        assert d["entry_structure_n"] == 10 and d["endpoint_dependent_n"] == 9 and d["excluded_from_endpoint_dependent"] == 1
        r = s["endpoint_reach_rate"]
        assert r["denominator"] == "endpoint_dependent_n" and r["denominator_n"] == 9
        assert r["numerator_reached"] == num and abs(r["rate"] - rate) < 1e-12
        assert r["auth_gate_counts_as_reached"] is (fid == "F1")
        assert r["n_endpoint_status_auth_gate_in_denominator"] == 3
        # entry-structure variables use entry_structure_n = 10 regardless of AUTH_GATE (R2 "critical")
        for v in ("auth_gate_stage", "entry_zone", "endpoint_status"):
            assert s["categorical"][v]["denominator"] == "entry_structure_n"
            assert s["categorical"][v]["denominator_n"] == 10
        assert s["categorical"]["entry_zone"]["n"] == 10
        # R13 aggregation: UNDETERMINED is a category in the denominator, not a missing value
        assert s["categorical"]["auth_gate_stage"]["n"] == 10 and s["categorical"]["auth_gate_stage"]["n_missing"] == 0
        assert s["categorical"]["auth_gate_stage"]["distribution"]["AFTER_TASK_SELECT"] == 3
        assert s["categorical"]["auth_gate_stage"]["distribution"]["UNDETERMINED"] == 1
        # endpoint-dependent numeric: denominator 9, split by reached (R6 Q1 visibility)
        a = s["numeric"]["activation_depth"]
        assert a["denominator"] == "endpoint_dependent_n" and a["denominator_n"] == 9 and a["n"] == 9
        assert a["by_endpoint_reached"]["reached"]["n"] == num
        assert a["by_endpoint_reached"]["not_reached"]["n"] == 9 - num
    # per-family rule is never guessed
    with pytest.raises(ValueError):
        C.family_summary(_r2_rows(), ["activation_depth"], [], family_id="F9")
    with pytest.raises(ValueError):
        C.family_summary(_r2_rows(), ["activation_depth"], [])          # AUTH_GATE rows + family_id None
    assert C.row_endpoint_reached({"endpoint_status": "AUTH_GATE"}, "F1") is True
    assert C.row_endpoint_reached({"endpoint_status": "AUTH_GATE"}, "F3") is False
    assert C.row_endpoint_reached({"endpoint_status": "PUBLIC_WEB_UNOBSERVABLE"}, "F1") is False
    assert C.row_endpoint_reached({}, "F1") is None


# ---------------------------------------------------------------- R3: task_role isolation

def test_task_role_filter_and_secondary_summary():
    rows = _r2_rows()
    # one F1 balance-check secondary row for S0: separate task_id, must not raise n
    rows.append({"service_id": "S0", "task_id": "F1-S0-SEC", "task_role": "SECONDARY_REPEATED",
                 "endpoint_status": "REACHED", "flow_evaluable": True, "activation_depth": 42,
                 "auth_gate_stage": "NONE", "entry_zone": "BOTTOM"})
    s = C.family_summary(rows, ["activation_depth"], ["entry_zone"], family_id="F1")
    assert s["filter_condition"] == "task_role == 'PRIMARY'"
    assert s["n_input_rows"] == 11 and s["n_primary"] == 10 and s["n_secondary_repeated"] == 1
    assert s["n_service"] == 10 and s["n_pairs"] == 45
    assert s["numeric"]["activation_depth"]["max"] == 9          # 42 never entered the main sample
    sec = s["secondary_repeated"]
    assert sec["filter_condition"] == "task_role == 'SECONDARY_REPEATED'"
    assert sec["n_rows"] == 1 and sec["task_ids"] == ["F1-S0-SEC"]
    assert sec["numeric"]["activation_depth"]["median"] == 42
    # no secondary rows → field present but None
    assert C.family_summary(_r2_rows(), [], [], family_id="F1")["secondary_repeated"] is None
    # missing / unknown task_role → raise (never silently PRIMARY)
    with pytest.raises(ValueError):
        C.family_summary([{"service_id": "X", "activation_depth": 1}], ["activation_depth"], [], family_id="F1")
    with pytest.raises(ValueError):
        C.family_summary([{"service_id": "X", "task_role": "MAIN"}], [], [], family_id="F1")
    # pairwise_matrix filters the same way
    seq_rows = _rows([["A", "B"]] * 10) + _rows([["A", "C"]], role="SECONDARY_REPEATED")
    m = C.pairwise_matrix(seq_rows)
    assert m["n_service"] == 10 and m["n_pairs"] == 45 and m["n_secondary_repeated_excluded"] == 1
    assert m["filter_condition"] == "task_role == 'PRIMARY'" and m["secondary_repeated_ids"] == ["S00"]
    # denominator_chain cross-checks counts against PRIMARY rows when rows are given
    t = C.denominator_chain(10, 10, 10, 10, 9, family_id="F1", rows=rows)
    assert t["filter_condition"] == "task_role == 'PRIMARY'" and t["n_secondary_repeated_excluded"] == 1
    with pytest.raises(ValueError):
        C.denominator_chain(10, 10, 10, 10, 10, family_id="F1", rows=rows)   # flow_evaluable 10 != PRIMARY 9


# ---------------------------------------------------------------- denominator chain

def test_denominator_chain_ok_and_violation():
    t = C.denominator_chain(10, 10, 10, 9, 8, family_id="F1",
                            reasons={"evidence_bearing": ["S03 EVIDENCE_DEFECT"],
                                     "flow_evaluable": ["S07 endpoint_status=ABSTAIN"]})
    stages = [r["stage"] for r in t["chain"]]
    # R4: replaced sits between candidate and eligible_frozen
    assert stages == ["candidate", "replaced", "eligible_frozen", "attempted", "evidence_bearing", "flow_evaluable"]
    counted = [r for r in t["chain"] if r["stage"] != "replaced"]
    assert [r["count"] for r in counted] == [10, 10, 10, 9, 8]
    assert [r["dropped"] for r in counted] == [0, 0, 0, 1, 1]
    assert t["chain"][4]["stage"] == "evidence_bearing" and t["chain"][4]["reasons"] == ["S03 EVIDENCE_DEFECT"]
    assert t["filter_condition"] == "task_role == 'PRIMARY'"
    with pytest.raises(ValueError):
        C.denominator_chain(10, 10, 10, 9, 10)          # later > earlier
    with pytest.raises(ValueError):
        C.denominator_chain(10, 11, 10, 9, 8)           # eligible > candidate
    with pytest.raises(ValueError):
        C.denominator_chain(10, 10, 10, 9, -1)          # negative
    # replacement after freeze is reported as violation (05 §6): eligible must equal candidate when frozen
    t = C.denominator_chain(10, 9, 9, 9, 9)
    assert t["chain"][2]["stage"] == "eligible_frozen" and t["chain"][2]["dropped"] == 1
    assert any("eligible < candidate" in n for n in t["notes"])


# ---------------------------------------------------------------- R4: replacement in the chain

_REPL = {"target_id": "F2-07", "reason": "NO_PUBLIC_MOBILE_WEB", "reserve_rank": 1,
         "decided_at": "2026-08-28T03:10:00+09:00", "decided_by": "A"}


def test_denominator_chain_replaced_k_explicit_and_reasons_closed():
    # k=0 must be an explicit 0 with an empty list — never an absent field (R4)
    t = C.denominator_chain(10, 10, 10, 10, 10, family_id="F2")
    rep = t["chain"][1]
    assert rep["stage"] == "replaced" and rep["k"] == 0 and rep["items"] == []
    assert t["replaced_k"] == 0
    assert set(rep["by_reason"]) == {"APP_REQUIRED_EXCLUDE", "NO_PUBLIC_MOBILE_WEB", "DEAD_OR_INVALID_URL",
                                     "PRECHECK_EVIDENCE_DEFECT"}
    assert all(v == 0 for v in rep["by_reason"].values())
    # k=1: candidate 10 → replaced 1 → eligible 10 (1:1 swap) → ...
    t = C.denominator_chain(10, 10, 10, 10, 9, family_id="F2", replaced=[_REPL])
    rep = t["chain"][1]
    assert rep["k"] == 1 and t["replaced_k"] == 1
    assert rep["items"][0] == {"target_id": "F2-07", "reason": "NO_PUBLIC_MOBILE_WEB", "reserve_rank": 1,
                               "decided_at": "2026-08-28T03:10:00+09:00", "decided_by": "A"}
    assert rep["by_reason"]["NO_PUBLIC_MOBILE_WEB"] == 1
    assert [r["count"] for r in t["chain"] if r["stage"] != "replaced"] == [10, 10, 10, 10, 9]
    assert t["notes"] == []
    # k=1 but eligible != candidate → note (replacement is 1:1)
    t = C.denominator_chain(10, 9, 9, 9, 9, family_id="F2", replaced=[_REPL])
    assert any("1:1" in n for n in t["notes"])
    # reasons outside the allowed set raise (R1: no 5th reason)
    with pytest.raises(ValueError):
        C.denominator_chain(10, 10, 10, 10, 10, replaced=[{**_REPL, "reason": "TASK_COMPARABILITY_CONCERN"}])
    with pytest.raises(ValueError):
        C.denominator_chain(10, 10, 10, 10, 10, replaced=[{**_REPL, "reason": "OTHER"}])
    # every per-item field is mandatory
    for k in ("target_id", "reason", "reserve_rank", "decided_at", "decided_by"):
        bad = dict(_REPL)
        del bad[k]
        with pytest.raises(ValueError):
            C.denominator_chain(10, 10, 10, 10, 10, replaced=[bad])
    with pytest.raises(ValueError):
        C.denominator_chain(10, 10, 10, 10, 10, replaced=[{**_REPL, "reserve_rank": 0}])
    with pytest.raises(ValueError):
        C.denominator_chain(10, 10, 10, 10, 10, replaced=[_REPL, _REPL])     # duplicate target_id
    # all four allowed reasons pass
    for r in ("APP_REQUIRED_EXCLUDE", "NO_PUBLIC_MOBILE_WEB", "DEAD_OR_INVALID_URL", "PRECHECK_EVIDENCE_DEFECT"):
        assert C.denominator_chain(10, 10, 10, 10, 10, replaced=[{**_REPL, "reason": r}])["replaced_k"] == 1


# ---------------------------------------------------------------- entry zone — T-A-V3-STEP1-003 R7

def test_entry_zone_r7_thresholds_and_boundaries():
    # A ruling (supersedes C-7): y<1/3 TOP · 1/3<=y<2/3 MID · y>=2/3 BOTTOM ; x thirds within TOP only ; [a,b)
    assert C.ZONE_TOP_Y == 1 / 3 and C.ZONE_BOTTOM_Y == 2 / 3
    assert "T-A-V3-STEP1-003 R7" in C.entry_zone.__doc__ and "supersedes C-7" in C.entry_zone.__doc__
    assert C.entry_zone(0.10, 0.05, False, False) == "TOP_LEFT"
    assert C.entry_zone(0.50, 0.05, False, False) == "TOP_CENTER"
    assert C.entry_zone(0.90, 0.05, False, False) == "TOP_RIGHT"
    assert C.entry_zone(0.50, 0.30, False, False) == "TOP_CENTER"   # y=0.30 < 1/3 is still TOP (was MID under C-7)
    assert C.entry_zone(0.50, 0.50, False, False) == "MID"
    assert C.entry_zone(0.10, 0.50, False, False) == "MID"          # no x split in MID
    assert C.entry_zone(0.90, 0.50, False, False) == "MID"
    assert C.entry_zone(0.10, 0.90, False, False) == "BOTTOM"       # no x split in BOTTOM
    assert C.entry_zone(0.90, 0.70, False, False) == "BOTTOM"       # y=0.70 >= 2/3 is BOTTOM (was MID under C-7)
    # boundaries [a, b): exactly 1/3 → TOP_CENTER (x) ; y exactly 1/3 → MID ; y exactly 2/3 → BOTTOM ; x exactly 2/3 → TOP_RIGHT
    assert C.entry_zone(1 / 3, 0.0, False, False) == "TOP_CENTER"
    assert C.entry_zone(2 / 3, 0.0, False, False) == "TOP_RIGHT"
    assert C.entry_zone(0.50, 1 / 3, False, False) == "MID"
    assert C.entry_zone(0.50, 2 / 3, False, False) == "BOTTOM"
    assert C.entry_zone(1 / 3, 1 / 3, False, False) == "MID"        # y decides first: 1/3 is not TOP
    assert C.entry_zone(0.0, 0.0, False, False) == "TOP_LEFT"
    assert C.entry_zone(1.0, 1.0, False, False) == "BOTTOM"
    # structural overrides beat geometry; DRAWER over FLOATING
    assert C.entry_zone(0.90, 0.90, True, False) == "FLOATING"
    assert C.entry_zone(0.10, 0.10, False, True) == "DRAWER"
    assert C.entry_zone(0.10, 0.10, True, True) == "DRAWER"
    # x/y are always retained → they must exist and be valid even under an override
    with pytest.raises(ValueError):
        C.entry_zone(None, 0.5, False, True)
    with pytest.raises(ValueError):
        C.entry_zone(1.2, 0.5, False, False)
    with pytest.raises(ValueError):
        C.entry_zone(None, 0.5, False, False)
    rec = C.entry_zone_record(0.5, 0.1, True, False)
    assert rec["entry_zone"] == "FLOATING" and rec["entry_zone_geometry_only"] == "TOP_CENTER"
    assert rec["entry_x_norm"] == 0.5 and rec["entry_y_norm"] == 0.1 and "R7" in rec["zone_rule"]


# ---------------------------------------------------------------- R6 Q8: field qualification guard

def test_q8_field_qualification_guard():
    # library outputs are clean
    d = C.derive("OPEN_GLOBAL_MENU > SELECT_FUNCTION > AUTH_GATE")
    assert C.q8_bare_mentions(d) == []
    d = C.derive(["SELECT_FUNCTION", "AUTH_GATE", "ENDPOINT_REACHED"])       # violation message names the layer
    assert d["violations"] and C.q8_bare_mentions(d) == []
    assert "action_token=AUTH_GATE" in d["violations"][0]
    assert C.q8_bare_mentions(C.derive(["ABSTAIN"], ["DISMISS_OBSTRUCTION", "ABSTAIN"])) == []
    s = C.family_summary(_r2_rows(), ["activation_depth"], ["endpoint_status", "auth_gate_stage"], family_id="F2")
    assert C.q8_bare_mentions(s) == []
    assert s["categorical"]["endpoint_status"]["distribution"]["AUTH_GATE"] == 3   # qualified by the var name
    # qualified forms pass
    for ok in ({"endpoint_status": "AUTH_GATE"}, {"action_token": "ABSTAIN"},
               {"nav_anchor_action_token": "AUTH_GATE"}, {"b_endpoint_status": "ABSTAIN"},
               {"task_flow_sequence": ["SELECT_FUNCTION", "AUTH_GATE"]},
               {"reasons": ["S07 endpoint_status=ABSTAIN", "S03 action_token=AUTH_GATE not last"]},
               {"counts": {"OPEN_GLOBAL_MENU>SELECT_FUNCTION>AUTH_GATE": 2}},
               {"signature_counts": {"AUTH_GATE": 2}}):
        assert C.q8_bare_mentions(ok) == [], ok
    # bare forms are flagged
    for bad in ({"reasons": ["S10 ABSTAIN"]}, {"terminal": "AUTH_GATE"}, ["REACHED", "AUTH_GATE", 3],
                {"nav_anchor_token": "AUTH_GATE"}, {"anchor": "AUTH_GATE"},
                {"note": "3 services hit AUTH_GATE early"}, {"AUTH_GATE": 3}, {"x": {"ABSTAIN": 1}}):
        assert C.q8_bare_mentions(bad), bad
        with pytest.raises(ValueError):
            C.assert_field_qualified(bad)
    # denominator_chain refuses bare reasons
    with pytest.raises(ValueError):
        C.denominator_chain(10, 10, 10, 10, 9, reasons={"flow_evaluable": ["S10 ABSTAIN"]})
    assert C.denominator_chain(10, 10, 10, 10, 9, reasons={"flow_evaluable": ["S10 endpoint_status=ABSTAIN"]})
