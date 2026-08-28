"""pytest for variance_control — Claude C lane6_stats, RUNBOOK Addendum r8 CI-20.

Expected outcomes were fixed from the CI-20 text BEFORE the implementation was written:
  expectations vary (>=2 distinct) and rows show exactly 1 distinct value  -> STRUCTURALLY_CONSTANT / SYSTEMIC / FAIL_SYSTEMIC
  rows equal to expectations                                               -> no finding / PASS
  variable constant in expectations                                         -> NOT_TESTABLE_BY_DESIGN (not a failure)
"""
import json
import pathlib

import pytest
import variance_control as V

HERE = pathlib.Path(__file__).resolve().parent
LANE2_EXP = HERE.parent / "lane2_label_reveal" / "EXPECTATIONS.json"

EXP = V.SYNTHETIC_EXPECTATIONS
VARS = V.SYNTHETIC_VARIABLES


def rows_from(exp, **override):
    return [dict(fixture=f, **{**v, **override}) for f, v in exp.items()]


# ---------------------------------------------------------------- must_flag

def test_must_flag_menu_dependency_always_false():
    # expectations: menu_dependency in {0, 1} (2 distinct); rows: always False (1 distinct) -> SYSTEMIC
    r = V.check_variance(rows_from(EXP, menu_dependency=False), VARS, EXP)
    assert r["verdict"] == V.VERDICT_FAIL_SYSTEMIC
    codes = {f["variable"]: (f["code"], f["severity"]) for f in r["findings"]}
    assert codes == {"menu_dependency": (V.STRUCTURALLY_CONSTANT, V.SEV_SYSTEMIC)}
    pv = r["per_variable"]["menu_dependency"]
    assert pv["observed_distinct"] == ["false"] and pv["constant_value"] is False
    assert sorted(pv["expected_distinct_in_scope"]) == ["0", "1"]
    # the other varying variables were reproduced correctly and are not flagged
    assert r["per_variable"]["nav_container_depth"]["code"] == V.VARIES
    assert r["per_variable"]["label_relation"]["code"] == V.VARIES


def test_must_flag_two_constant_variables_shape_b_found():
    # the BLK-016 part3 shape: reveal never fires -> menu_dependency ≡ 0 AND nav_container_depth ≡ 0
    r = V.check_variance(rows_from(EXP, menu_dependency=0, nav_container_depth=0), VARS, EXP)
    assert r["verdict"] == V.VERDICT_FAIL_SYSTEMIC
    assert sorted(f["variable"] for f in r["findings"]) == ["menu_dependency", "nav_container_depth"]
    assert all(f["severity"] == V.SEV_SYSTEMIC for f in r["findings"])


def test_must_flag_fires_even_when_each_item_is_explained():
    # per-item: every row's constant value equals the expectation on fx_visible only — CI-20 is independent of that
    rows = rows_from(EXP, label_relation="MATCH")     # matches fx_visible, differs on the other two
    r = V.check_variance(rows, ["label_relation"], EXP)
    assert r["verdict"] == V.VERDICT_FAIL_SYSTEMIC
    assert r["findings"][0]["code"] == V.STRUCTURALLY_CONSTANT


def test_must_flag_variable_never_emitted():
    rows = [{k: v for k, v in row.items() if k != "nav_container_depth"} for row in rows_from(EXP)]
    r = V.check_variance(rows, VARS, EXP)
    assert r["verdict"] == V.VERDICT_FAIL_SYSTEMIC
    assert [f["code"] for f in r["findings"]] == [V.NOT_EMITTED]
    assert r["per_variable"]["nav_container_depth"]["n_rows_with_variable"] == 0


# ---------------------------------------------------------------- must_not_flag

def test_must_not_flag_rows_equal_expectations():
    r = V.check_variance(rows_from(EXP), VARS, EXP)
    assert r["verdict"] == V.VERDICT_PASS and r["findings"] == []
    assert r["variables_testable"] == ["menu_dependency", "nav_container_depth", "label_relation"]
    assert all(r["per_variable"][v]["code"] == V.VARIES for v in r["variables_testable"])


def test_must_not_flag_variance_present_with_wrong_values():
    # rows vary (2 distinct) but every value is wrong -> not CI-20's job (per-item comparison catches it)
    rows = rows_from(EXP)
    rows[0]["menu_dependency"], rows[1]["menu_dependency"], rows[2]["menu_dependency"] = 1, 0, 0
    r = V.check_variance(rows, ["menu_dependency"], EXP)
    assert r["verdict"] == V.VERDICT_PASS


# ---------------------------------------------------------------- NOT_TESTABLE_BY_DESIGN

def test_not_testable_by_design_constant_in_expectations():
    for rows in (rows_from(EXP), rows_from(EXP, dom_ax_divergence=True)):
        r = V.check_variance(rows, VARS, EXP)
        pv = r["per_variable"]["dom_ax_divergence"]
        assert pv["code"] == V.NOT_TESTABLE_BY_DESIGN and pv["severity"] == V.SEV_NONE
        assert "dom_ax_divergence" in r["variables_not_testable_by_design"]
        assert not any(f["variable"] == "dom_ax_divergence" for f in r["findings"])


def test_not_testable_when_run_covers_only_a_constant_subset():
    # a partial run over fixtures where the expectation happens to be constant must not be flagged
    rows = [dict(fixture="fx_drawer", **EXP["fx_drawer"]), dict(fixture="fx_nested", **EXP["fx_nested"])]
    r = V.check_variance(rows, ["menu_dependency"], EXP)
    pv = r["per_variable"]["menu_dependency"]
    assert pv["code"] == V.NOT_TESTABLE_BY_DESIGN and "note" in pv
    assert pv["expected_distinct_full_set"] == ["0", "1"] and pv["expected_distinct_in_scope"] == ["1"]
    assert r["expectation_fixtures_without_row"] == ["fx_visible"]


def test_variable_absent_from_expectations_is_reported_not_failed():
    r = V.check_variance(rows_from(EXP), ["auth_gate_stage"], EXP)
    assert r["per_variable"]["auth_gate_stage"]["code"] == V.NOT_IN_EXPECTATIONS
    assert r["verdict"] == V.VERDICT_PASS and r["variables_not_in_expectations"] == ["auth_gate_stage"]


# ---------------------------------------------------------------- distinctness / input shapes / empty is not a pass

def test_false_and_zero_are_distinct_none_is_a_value():
    exp = {"a": {"x": 0}, "b": {"x": 1}}
    assert V.check_variance([{"fixture": "a", "x": False}, {"fixture": "b", "x": 0}], ["x"], exp)["verdict"] == V.VERDICT_PASS
    r = V.check_variance([{"fixture": "a", "x": None}, {"fixture": "b", "x": None}], ["x"], exp)
    assert r["findings"][0]["code"] == V.STRUCTURALLY_CONSTANT and r["per_variable"]["x"]["observed_distinct"] == ["null"]


def test_accepts_lane2_style_expectation_entries_and_ignores_unknown_rows():
    exp_list = [{"fixture": f, "expected": v} for f, v in EXP.items()]
    rows = rows_from(EXP) + [{"fixture": "not_in_expectations", "menu_dependency": 0}]
    r = V.check_variance(rows, VARS, exp_list)
    assert r["verdict"] == V.VERDICT_PASS and r["rows_ignored_no_expectation"] == ["not_in_expectations"]


def test_empty_inputs_raise_not_pass():
    with pytest.raises(ValueError):
        V.check_variance([], VARS, EXP)
    with pytest.raises(ValueError):
        V.check_variance(rows_from(EXP), [], EXP)
    with pytest.raises(ValueError):
        V.check_variance([{"fixture": "zzz", "menu_dependency": 0}], VARS, EXP)
    with pytest.raises(ValueError):
        V.check_variance(rows_from(EXP) + [rows_from(EXP)[0]], VARS, EXP)   # duplicate fixture id


def test_run_controls_all_pass():
    c = V.run_controls()
    assert c["controls_ok"] is True
    assert c["must_flag"]["passed"] and c["must_not_flag"]["passed"] and c["not_testable_by_design"]["passed"]


# ---------------------------------------------------------------- CI-20 premise on C's real lane2 fixture set

def test_lane2_expectations_are_designed_to_vary_the_ci20_variables():
    # CI-20 premise: for every CI-20 variable that lane2 pre-registers, the expectations hold >= 2 distinct values
    exp = V.expectations_from_lane2(json.loads(LANE2_EXP.read_text(encoding="utf-8")))
    rows = [dict(fixture=f, **v) for f, v in exp.items()]          # rows == expectations → must_not_flag on real data
    r = V.check_variance(rows, V.CI20_VARIABLES, exp)
    assert r["verdict"] == V.VERDICT_PASS
    present = [v for v in V.CI20_VARIABLES if r["per_variable"][v]["code"] != V.NOT_IN_EXPECTATIONS]
    assert set(present) >= {"menu_dependency", "nav_container_depth", "nav_container_type", "label_relation", "entry_zone"}
    for v in present:
        assert r["per_variable"][v]["code"] == V.VARIES, (v, r["per_variable"][v])
    # and a runner that never fires a reveal is caught on the real fixture set
    bad = [dict(row, menu_dependency=0, nav_container_depth=0) for row in rows]
    rb = V.check_variance(bad, V.CI20_VARIABLES, exp)
    assert rb["verdict"] == V.VERDICT_FAIL_SYSTEMIC
    assert sorted(f["variable"] for f in rb["findings"]) == ["menu_dependency", "nav_container_depth"]
