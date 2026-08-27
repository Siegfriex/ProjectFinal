"""pytest for c_flow_derive — Claude C lane6_stats.

All expected values in this file were computed BY HAND from SSOTV3
04_FLOW_CODEBOOK_v3.0 (§2/§3/§5) and 05_ANALYSIS_PLAN_v3.0 (§1/§4/§6)
BEFORE the implementation was written. Each test states the arithmetic.
"""
import math

import pytest

import c_flow_derive as C

# ---------------------------------------------------------------- tokens

def test_classify_activation_tokens():
    # expected computed by hand: 04 §5 — activation = state-changing, excl scroll/typing/passive/dismiss
    for t in ["OPEN_GLOBAL_MENU", "OPEN_LOCAL_MENU", "SWITCH_TAB", "EXPAND_ACCORDION",
              "SELECT_CATEGORY", "SELECT_FUNCTION", "SELECT_RESULT",
              "OPEN_ITEM_DETAIL", "OPEN_PLACE_DETAIL"]:
        assert C.classify_token(t)["state_changing_activation"] is True, t
    # C pre-registered choice: SUBMIT_QUERY counted as activation (flag can flip)
    assert C.classify_token("SUBMIT_QUERY")["state_changing_activation"] is True
    assert C.classify_token("SUBMIT_QUERY", submit_is_activation=False)["state_changing_activation"] is False
    # typing / form-intent tokens are NOT activation depth
    for t in ["INPUT_QUERY", "SELECT_ORIGIN", "SELECT_DESTINATION", "SELECT_DATE"]:
        assert C.classify_token(t)["state_changing_activation"] is False, t
        assert C.classify_token(t)["task_intent"] is True, t
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
    d = C.derive("OPEN_GLOBAL_MENU > SELECT_FUNCTION > AUTH_GATE".split(" > "),
                 "DISMISS_OBSTRUCTION > OPEN_GLOBAL_MENU > SELECT_FUNCTION > AUTH_GATE".split(" > "))
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
    #   activation_depth            = 3 (SELECT_FUNCTION, SUBMIT_QUERY, SELECT_RESULT)
    #   activation_depth_excl_submit= 2
    #   activation_depth_incl_form  = 4 (adds INPUT_QUERY)
    #   flow_step_count             = 4 (all except ENDPOINT_REACHED)
    #   menu_dependency             = 0
    #   nav_container_depth         = 0
    #   forced_dismissal_count      = 0
    #   auth_gate_stage             = NONE ; endpoint_status = REACHED
    seq = ["SELECT_FUNCTION", "INPUT_QUERY", "SUBMIT_QUERY", "SELECT_RESULT", "ENDPOINT_REACHED"]
    d = C.derive(seq, seq)
    assert d["activation_depth"] == 3
    assert d["activation_depth_excl_submit"] == 2
    assert d["activation_depth_incl_form"] == 4
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

    # AT_ENDPOINT: auth after task body (query submitted) and terminal
    seq = ["SELECT_FUNCTION", "INPUT_QUERY", "SUBMIT_QUERY", "AUTH_GATE"]
    assert C.derive(seq, seq)["auth_gate_stage"] == "AT_ENDPOINT"
    # AT_ENDPOINT: auth immediately before ENDPOINT_REACHED is a contract violation (00 §6 AUTH_GATE terminal)
    seq = ["SELECT_FUNCTION", "AUTH_GATE", "ENDPOINT_REACHED"]
    d = C.derive(seq, seq)
    assert d["auth_gate_stage"] == "AT_ENDPOINT"
    assert any("AUTH_GATE" in v for v in d["violations"])


def test_derive_sequence_consistency_flag():
    # experienced with dismissals removed must equal task_flow (04 §3). Mismatch -> flag, not raise.
    d = C.derive(["SELECT_FUNCTION", "ENDPOINT_REACHED"],
                 ["DISMISS_OBSTRUCTION", "OPEN_GLOBAL_MENU", "SELECT_FUNCTION", "ENDPOINT_REACHED"])
    assert d["sequence_consistent"] is False
    # dismissal inside task_flow is itself a violation of 04 §3
    d = C.derive(["DISMISS_OBSTRUCTION", "SELECT_FUNCTION"], ["DISMISS_OBSTRUCTION", "SELECT_FUNCTION"])
    assert any("task_flow" in v for v in d["violations"])


def test_derive_abstain_is_not_flow_evaluable():
    # ABSTAIN (04 §2) → not flow-evaluable (05 §6). expected by hand: derived numerics None, not 0;
    # forced_dismissal_count still counted from experienced (obstruction layer is independent of judgement).
    d = C.derive(["ABSTAIN"], ["DISMISS_OBSTRUCTION", "ABSTAIN"])
    assert d["flow_evaluable"] is False
    assert d["activation_depth"] is None and d["flow_step_count"] is None
    assert d["menu_dependency"] is None and d["nav_container_depth"] is None
    assert d["auth_gate_stage"] is None
    assert d["endpoint_status"] == "ABSTAIN"
    assert d["forced_dismissal_count"] == 1
    # family_summary then reports n=9 / n_missing=1 instead of diluting with a 0
    rows = [{"service_id": f"S{i}", "activation_depth": 2} for i in range(9)] + [{"service_id": "S9", **d}]
    s = C.family_summary(rows, ["activation_depth"], [])
    assert s["n_service"] == 10 and s["numeric"]["activation_depth"]["n"] == 9
    assert s["numeric"]["activation_depth"]["n_missing"] == 1 and s["numeric"]["activation_depth"]["median"] == 2


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


def _rows(seqs):
    return [{"service_id": f"S{i:02d}", "task_flow_sequence": s} for i, s in enumerate(seqs)]


def test_pairwise_matrix_and_signatures():
    seqs = [["A", "B"]] * 5 + [["A", "C"]] * 5      # n=10
    m = C.pairwise_matrix(_rows(seqs))
    assert m["n_service"] == 10 and m["n_pairs"] == 45
    assert "pairs are cells" in m["pseudo_replication_guard"]
    L = m["levenshtein_norm"]
    assert len(L) == 10 and all(len(r) == 10 for r in L)
    assert L[0][0] == 0.0 and L[0][1] == 0.0
    assert L[0][5] == 0.5 and L[5][0] == 0.5        # symmetric, one substitution of 2 → 0.5
    # off-diagonal cell count = 45 upper triangle
    assert m["n_pairs"] == sum(1 for i in range(10) for j in range(i + 1, 10))
    sig = C.unique_signatures(_rows(seqs))
    assert sig["n_unique"] == 2
    assert sig["counts"]["A>B"] == 5 and sig["counts"]["A>C"] == 5


# ---------------------------------------------------------------- family summary

def test_family_summary_numeric_and_entropy():
    # activation_depth values 1..10 : median = 5.5 ; Q1 (type-7) = 1 + 0.25*9 = 3.25 ; Q3 = 7.75 ; IQR = 4.5 ; range (1,10)
    rows = [{"service_id": f"S{i}", "activation_depth": i, "entry_zone": z}
            for i, z in zip(range(1, 11), ["TOP_LEFT", "TOP_CENTER", "TOP_RIGHT", "MID", "BOTTOM",
                                           "FLOATING", "DRAWER", "TOP_LEFT", "TOP_CENTER", "TOP_RIGHT"])]
    s = C.family_summary(rows, numeric_vars=["activation_depth"], categorical_vars=["entry_zone"])
    assert s["n_service"] == 10 and s["n_pairs"] == 45
    assert s["pseudo_replication_guard"] == "pairs are cells, not independent n"
    num = s["numeric"]["activation_depth"]
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
    uni = [{"service_id": f"S{i}", "z": f"Z{i}"} for i in range(10)]
    deg = [{"service_id": f"S{i}", "z": "Z0"} for i in range(10)]
    su = C.family_summary(uni, numeric_vars=[], categorical_vars=["z"])["categorical"]["z"]
    sd = C.family_summary(deg, numeric_vars=[], categorical_vars=["z"])["categorical"]["z"]
    assert abs(su["entropy_bits"] - math.log2(10)) < 1e-12 and su["entropy_norm"] == 1.0
    assert sd["entropy_bits"] == 0.0 and sd["entropy_norm"] == 0.0
    # binary 5/5 → 1 bit
    half = [{"service_id": f"S{i}", "z": "A" if i < 5 else "B"} for i in range(10)]
    assert C.family_summary(half, [], ["z"])["categorical"]["z"]["entropy_bits"] == 1.0


def test_family_summary_missing_and_n_not_10():
    rows = [{"service_id": f"S{i}", "v": (i if i < 7 else None)} for i in range(10)]
    s = C.family_summary(rows, ["v"], [])
    assert s["numeric"]["v"]["n"] == 7 and s["numeric"]["v"]["n_missing"] == 3
    assert s["numeric"]["v"]["median"] == 3        # 0..6 → median 3
    s9 = C.family_summary(rows[:9], ["v"], [])
    assert s9["n_service"] == 9 and s9["n_pairs"] == 36 and s9["n_service_warning"]


# ---------------------------------------------------------------- denominator chain

def test_denominator_chain_ok_and_violation():
    t = C.denominator_chain(10, 10, 10, 9, 8, family_id="F1",
                            reasons={"evidence_bearing": ["S03 EVIDENCE_DEFECT"],
                                     "flow_evaluable": ["S07 ABSTAIN"]})
    stages = [r["stage"] for r in t["chain"]]
    assert stages == ["candidate", "eligible_frozen", "attempted", "evidence_bearing", "flow_evaluable"]
    assert [r["count"] for r in t["chain"]] == [10, 10, 10, 9, 8]
    assert [r["dropped"] for r in t["chain"]] == [0, 0, 0, 1, 1]
    assert t["chain"][3]["reasons"] == ["S03 EVIDENCE_DEFECT"]
    with pytest.raises(ValueError):
        C.denominator_chain(10, 10, 10, 9, 10)          # later > earlier
    with pytest.raises(ValueError):
        C.denominator_chain(10, 11, 10, 9, 8)           # eligible > candidate
    with pytest.raises(ValueError):
        C.denominator_chain(10, 10, 10, 9, -1)          # negative
    # replacement after freeze is reported as violation (05 §6): eligible must equal candidate when frozen
    t = C.denominator_chain(10, 9, 9, 9, 9)
    assert t["chain"][1]["dropped"] == 1


# ---------------------------------------------------------------- entry zone

def test_entry_zone_thresholds():
    # C pre-registered: y<0.15 TOP band split x<1/3 | <=2/3 | >2/3 ; 0.15<=y<0.85 MID ; y>=0.85 BOTTOM
    assert C.entry_zone(0.10, 0.05, False, False) == "TOP_LEFT"
    assert C.entry_zone(0.50, 0.05, False, False) == "TOP_CENTER"
    assert C.entry_zone(0.90, 0.05, False, False) == "TOP_RIGHT"
    assert C.entry_zone(0.50, 0.15, False, False) == "MID"          # boundary inclusive to MID
    assert C.entry_zone(0.50, 0.50, False, False) == "MID"
    assert C.entry_zone(0.50, 0.85, False, False) == "BOTTOM"       # boundary inclusive to BOTTOM
    assert C.entry_zone(0.90, 0.90, True, False) == "FLOATING"
    assert C.entry_zone(0.10, 0.10, False, True) == "DRAWER"
    assert C.entry_zone(0.10, 0.10, True, True) == "DRAWER"         # DRAWER precedence
    assert C.entry_zone(1 / 3, 0.0, False, False) == "TOP_CENTER"   # x == 1/3 goes to CENTER
    assert C.entry_zone(2 / 3, 0.0, False, False) == "TOP_CENTER"   # x == 2/3 stays CENTER
    with pytest.raises(ValueError):
        C.entry_zone(1.2, 0.5, False, False)
    with pytest.raises(ValueError):
        C.entry_zone(None, 0.5, False, False)
