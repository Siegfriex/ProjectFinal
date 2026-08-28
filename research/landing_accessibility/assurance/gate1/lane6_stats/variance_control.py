#!/usr/bin/env python3
"""CI-20 constant-variable control (structural zero variance) — Claude C lane6_stats.

Authority: GATE1_RUNBOOK_C Addendum r8 CI-20 (T-B-V3-BLK-016 part3; D-V3-FINDING-003/013).

Rule. For every derived variable that C's fixture set is *designed to vary* — i.e. the pre-registered
expectations across fixtures contain >= 2 distinct values — a runner whose outputs over those same
fixtures show exactly 1 distinct value has a structurally constant variable: finding
`STRUCTURALLY_CONSTANT`, severity `SYSTEMIC`, overall verdict `FAIL_SYSTEMIC`. This is a variance
control, independent of per-item comparison: it fires even when every per-item diff is individually
explained (the `menu_dependency ≡ False` / `nav_container_depth ≡ 0` shape and D's `H1_NO_EFFECT`).

Variables whose expectations are themselves constant over the fixtures in scope cannot be tested by
this control and are reported as `NOT_TESTABLE_BY_DESIGN` (not a failure).

Pure python3 stdlib. No B/D code is imported.
"""
from __future__ import annotations

import json
from typing import Any, Iterable, Mapping, Sequence

CHECK_ID = "CI-20"

# finding codes
STRUCTURALLY_CONSTANT = "STRUCTURALLY_CONSTANT"    # expectations vary, runner emitted exactly 1 distinct value → SYSTEMIC
NOT_EMITTED = "NOT_EMITTED"                        # expectations vary, runner emitted the variable on no row → SYSTEMIC
VARIES = "VARIES"                                  # expectations vary and observed values vary → control passed
NOT_TESTABLE_BY_DESIGN = "NOT_TESTABLE_BY_DESIGN"  # expectations constant over the fixtures in scope → not testable, not a failure
NOT_IN_EXPECTATIONS = "NOT_IN_EXPECTATIONS"        # no fixture in scope pre-registers the variable → out of this fixture set's design

SEV_SYSTEMIC = "SYSTEMIC"
SEV_NONE = "NONE"

VERDICT_PASS = "PASS"
VERDICT_FAIL_SYSTEMIC = "FAIL_SYSTEMIC"

# the derived variables CI-20 names (RUNBOOK r8); callers may pass any subset or other variables
CI20_VARIABLES: tuple[str, ...] = (
    "menu_dependency", "nav_container_depth", "nav_container_type", "first_visible_scroll_state",
    "auth_gate_stage", "activation_depth", "label_relation", "entry_zone",
)

_ABSENT = object()


def _canon(v: Any) -> str:
    """Canonical hashable form for distinctness. json keeps False ('false') and 0 ('0') distinct, None → 'null',
    lists/dicts compare structurally; anything non-JSON falls back to str()."""
    return json.dumps(v, sort_keys=True, ensure_ascii=False, default=str)


def _as_fixture_map(items: Any, fixture_key: str, *, what: str) -> dict[str, Mapping[str, Any]]:
    """Accept {fixture: {var: val}}, or a sequence of dicts carrying `fixture_key` (lane2 EXPECTATIONS-style
    entries with a nested `expected` block are unwrapped). Duplicate fixture ids raise — one row per fixture."""
    out: dict[str, Mapping[str, Any]] = {}
    if isinstance(items, Mapping):
        for k, v in items.items():
            if not isinstance(v, Mapping):
                raise TypeError(f"{what}[{k!r}] must be a mapping of variable -> value")
            out[str(k)] = v
        return out
    if isinstance(items, (str, bytes)) or not isinstance(items, Iterable):
        raise TypeError(f"{what} must be a mapping keyed by fixture or a sequence of row dicts")
    for i, it in enumerate(items):
        if not isinstance(it, Mapping) or fixture_key not in it:
            raise TypeError(f"{what}[{i}] must be a mapping carrying {fixture_key!r}")
        fid = str(it[fixture_key])
        if fid in out:
            raise ValueError(f"{what}: duplicate fixture id {fid!r} (one row per fixture)")
        body = it["expected"] if ("expected" in it and isinstance(it["expected"], Mapping)) else it
        out[fid] = body
    return out


def expectations_from_lane2(exp_json: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    """lane2 EXPECTATIONS.json → {fixture: expected-block}."""
    return _as_fixture_map(exp_json["fixtures"], "fixture", what="expectations")


def check_variance(rows: Sequence[Mapping[str, Any]] | Mapping[str, Mapping[str, Any]],
                   variables: Sequence[str],
                   expectations: Sequence[Mapping[str, Any]] | Mapping[str, Mapping[str, Any]],
                   *, fixture_key: str = "fixture") -> dict[str, Any]:
    """CI-20. rows = runner outputs across fixtures; variables = derived variable names; expectations = per-fixture
    expected values. Returns a record with per-variable status, findings and an overall verdict.

    Scope = fixtures that have BOTH a runner row and an expectation. Design variance is judged over that scope so an
    incomplete run is not flagged for fixtures it never ran; the full-set variance is reported alongside.
    Empty inputs raise — an empty observation set is never a pass (a control must be able to fail)."""
    if not rows:
        raise ValueError("CI-20: no runner rows — an empty observation set is not a pass")
    if not variables:
        raise ValueError("CI-20: no variables named")
    exp = _as_fixture_map(expectations, fixture_key, what="expectations")
    obs = _as_fixture_map(rows, fixture_key, what="rows")
    if not exp:
        raise ValueError("CI-20: expectations are empty")
    in_scope = [f for f in obs if f in exp]
    ignored_rows = [f for f in obs if f not in exp]
    missing_rows = [f for f in exp if f not in obs]
    if not in_scope:
        raise ValueError("CI-20: no runner row matches any expectation fixture id")

    per_variable: dict[str, dict[str, Any]] = {}
    findings: list[dict[str, Any]] = []
    for var in variables:
        exp_vals_scope = {_canon(exp[f][var]) for f in in_scope if var in exp[f]}
        exp_vals_full = {_canon(e[var]) for e in exp.values() if var in e}
        present = [(f, obs[f][var]) for f in in_scope if var in obs[f]]
        obs_vals = {_canon(v) for _, v in present}
        n_absent = len(in_scope) - len(present)
        rec: dict[str, Any] = {
            "variable": var,
            "n_fixtures_in_scope": len(in_scope),
            "expected_distinct_in_scope": sorted(exp_vals_scope),
            "expected_distinct_full_set": sorted(exp_vals_full),
            "observed_distinct": sorted(obs_vals),
            "n_rows_with_variable": len(present),
            "n_rows_without_variable": n_absent,
        }
        if not exp_vals_full:
            code, sev = NOT_IN_EXPECTATIONS, SEV_NONE
        elif len(exp_vals_scope) < 2:
            code, sev = NOT_TESTABLE_BY_DESIGN, SEV_NONE
            if len(exp_vals_full) >= 2:
                rec["note"] = "expectations vary over the full fixture set but not over the fixtures this run covered"
        elif not present:
            code, sev = NOT_EMITTED, SEV_SYSTEMIC
        elif len(obs_vals) == 1:
            code, sev = STRUCTURALLY_CONSTANT, SEV_SYSTEMIC
            rec["constant_value"] = present[0][1]
        else:
            code, sev = VARIES, SEV_NONE
        rec["code"] = code
        rec["severity"] = sev
        per_variable[var] = rec
        if sev == SEV_SYSTEMIC:
            findings.append({
                "check": CHECK_ID, "variable": var, "code": code, "severity": sev,
                "fixtures": list(in_scope),
                "expected_distinct": rec["expected_distinct_in_scope"],
                "observed_distinct": rec["observed_distinct"],
                "constant_value": rec.get("constant_value"),
                "note": "structurally constant across fixtures designed to vary it; independent of per-item diffs",
            })
    return {
        "check": CHECK_ID,
        "verdict": VERDICT_FAIL_SYSTEMIC if findings else VERDICT_PASS,
        "n_rows": len(obs),
        "n_fixtures_in_scope": len(in_scope),
        "fixtures_in_scope": in_scope,
        "rows_ignored_no_expectation": ignored_rows,
        "expectation_fixtures_without_row": missing_rows,
        "variables_testable": [v for v, r in per_variable.items() if r["code"] in (VARIES, STRUCTURALLY_CONSTANT, NOT_EMITTED)],
        "variables_not_testable_by_design": [v for v, r in per_variable.items() if r["code"] == NOT_TESTABLE_BY_DESIGN],
        "variables_not_in_expectations": [v for v, r in per_variable.items() if r["code"] == NOT_IN_EXPECTATIONS],
        "per_variable": per_variable,
        "findings": findings,
    }


# ---------------------------------------------------------------- controls (the check must be shown to be able to fail)

SYNTHETIC_EXPECTATIONS: dict[str, dict[str, Any]] = {
    # three synthetic fixtures; menu_dependency / nav_container_depth / label_relation vary, dom_ax_divergence is constant
    "fx_visible":  {"menu_dependency": 0, "nav_container_depth": 0, "label_relation": "MATCH",        "dom_ax_divergence": False},
    "fx_drawer":   {"menu_dependency": 1, "nav_container_depth": 1, "label_relation": "NOT_OBSERVED", "dom_ax_divergence": False},
    "fx_nested":   {"menu_dependency": 1, "nav_container_depth": 2, "label_relation": "AX_ONLY",      "dom_ax_divergence": False},
}
SYNTHETIC_VARIABLES = ("menu_dependency", "nav_container_depth", "label_relation", "dom_ax_divergence")


def run_controls() -> dict[str, Any]:
    """must_flag: a runner whose menu_dependency is always False (reveal never fired) while the expectations vary;
    must_not_flag: rows equal to the expectations; not_testable: a variable constant in the expectations."""
    exp = SYNTHETIC_EXPECTATIONS
    rows_flag = [dict(fixture=f, **{**v, "menu_dependency": False}) for f, v in exp.items()]
    rows_ok = [dict(fixture=f, **v) for f, v in exp.items()]
    r_flag = check_variance(rows_flag, SYNTHETIC_VARIABLES, exp)
    r_ok = check_variance(rows_ok, SYNTHETIC_VARIABLES, exp)
    must_flag = r_flag["verdict"] == VERDICT_FAIL_SYSTEMIC and any(
        f["variable"] == "menu_dependency" and f["code"] == STRUCTURALLY_CONSTANT for f in r_flag["findings"])
    must_not_flag = r_ok["verdict"] == VERDICT_PASS and not r_ok["findings"]
    not_testable = (r_ok["per_variable"]["dom_ax_divergence"]["code"] == NOT_TESTABLE_BY_DESIGN
                    and r_flag["per_variable"]["dom_ax_divergence"]["code"] == NOT_TESTABLE_BY_DESIGN)
    return {
        "must_flag": {"passed": must_flag, "verdict": r_flag["verdict"], "findings": r_flag["findings"]},
        "must_not_flag": {"passed": must_not_flag, "verdict": r_ok["verdict"], "findings": r_ok["findings"]},
        "not_testable_by_design": {"passed": not_testable, "variable": "dom_ax_divergence",
                                   "code": r_ok["per_variable"]["dom_ax_divergence"]["code"]},
        "controls_ok": must_flag and must_not_flag and not_testable,
    }


if __name__ == "__main__":
    import sys
    res = run_controls()
    print(json.dumps(res, ensure_ascii=False, indent=1, default=str))
    sys.exit(0 if res["controls_ok"] else 1)
