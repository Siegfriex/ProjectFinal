#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Lane S — Spatial / Control-form / Menu-Reveal analysis harness (V3, outcome-independent).

Scope contract
--------------
This module implements ONLY variables that SSOTV3 `04_FLOW_CODEBOOK_v3.0.md` has already
frozen, plus the descriptive statistics named in `05_ANALYSIS_PLAN_v3.0.md` §2-B / §2-D.

It deliberately does NOT:
  * invent zone boundaries (see AMBIGUOUS_DEFINITION AMB-S01 .. AMB-S03),
  * create thresholds, cut-offs, weights, or any composite / "friction" score,
  * normalize or compare label text (Lane L owns `label_relation` per 04 §5),
  * touch REAL targets, holdout, gold labels, or any mart/evidence artefact.

MAIN50 measurement data does not exist yet (A freeze pending). Everything here is
verified against synthetic fixtures with pre-planted answers, plus mutation testing.

Reproduce:
    /home/sieg/projects-wsl/ProjectFinal/.venv/bin/python \
      .../research_d/tools/v3_harness/lane_s_spatial_control_reveal.py

Writes (and nothing else):
    research_d/results/harness/lane_s/LANE_S_HARNESS.json
    research_d/results/harness/lane_s/LANE_S_FINDINGS.md
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import statistics
import sys
from itertools import combinations
from typing import Any, Callable, Iterable, Sequence

# --------------------------------------------------------------------------------------
# 0. Provenance
# --------------------------------------------------------------------------------------

RD = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
SSOT_DIR = "/home/sieg/projects-wsl/ProjectFinal/SSOTV3"
OUT_DIR = os.path.join(RD, "results", "harness", "lane_s")

BASE_SHA = "7448184a811f5d7d8772f21488bb75418fde3313"
MANIFEST_SELF_SHA256 = "1735c956d4a3461ee9eb2543c5c474942887bcbd117f5876d5486207f2f72e0a"

# Verbatim quotations from SSOTV3. These are the ONLY authority this module implements.
CODEBOOK_VERBATIM: dict[str, str] = {
    "04 §4 s0_task_control_visible":
        "| s0_task_control_visible | Surface | bool | 최초 viewport에서 사전지정 task 진입 control이 직접 보이는가 |",
    "04 §4 first_visible_scroll_state":
        "| first_visible_scroll_state | Surface | S0,S1,... | task 진입 control이 최초 관측된 scroll state. "
        "scroll은 activation depth에 포함하지 않음 |",
    "04 §4 entry_x_norm":
        "| entry_x_norm | Geometry | 0~1 | task-entry control 중심 x 좌표를 viewport로 정규화 |",
    "04 §4 entry_y_norm":
        "| entry_y_norm | Geometry | 0~1 | task-entry control 중심 y 좌표를 viewport로 정규화 |",
    "04 §4 entry_zone":
        "| entry_zone | Geometry | categorical | TOP_LEFT/TOP_CENTER/TOP_RIGHT/MID/BOTTOM/FLOATING/DRAWER |",
    "04 §4 entry_control_type":
        "| entry_control_type | DOM/AX/Visual | categorical | TEXT_LINK/TEXT_BUTTON/ICON_TEXT/ICON_ONLY/TAB/"
        "BOTTOM_NAV/HAMBURGER/CARD/SEARCHBOX/LIST_ITEM/OTHER |",
    "04 §4 nav_container_type":
        "| nav_container_type | Flow | categorical | NONE/HAMBURGER/LEFT_DRAWER/RIGHT_DRAWER/TOP_DROPDOWN/"
        "BOTTOM_SHEET/MODAL_MENU/INLINE_EXPAND |",
    "04 §4 reveal_direction":
        "| reveal_direction | Flow/Geometry | categorical | NONE/LEFT/RIGHT/TOP/BOTTOM/CENTER/INLINE |",
    "04 §4 menu_dependency":
        "| menu_dependency | Derived | bool | action_sequence에 OPEN/REVEAL 계열 token이 endpoint 이전에 존재하는지 |",
    "04 §4 nav_container_depth":
        "| nav_container_depth | Derived | count | task control 노출 전 menu/drawer expansion 수 |",
    "04 §5 menu_dependency rule":
        "- `menu_dependency = 1` iff endpoint 전 OPEN_GLOBAL_MENU/OPEN_LOCAL_MENU/EXPAND_ACCORDION 등 reveal token 존재.",
    "04 §5 nav_container_depth rule":
        "- `nav_container_depth`: task control 노출 전 nested reveal 수.",
    "04 §6 Spatial zone (FULL SECTION)":
        "## 6. Spatial zone\n\nNormalized center `(x,y)`를 보존하고 zone은 요약값으로만 쓴다. 좌표 원자료를 버리지 않는다.",
    "05 §1 analysis unit":
        "Primary: `service × frozen task`.\n\nfamily n=10. 동일 family의 45 pair는 distance matrix의 cell이지 "
        "독립 표본 n=45가 아니다.",
    "05 §2-B Spatial":
        "### B. Spatial\n- x/y distribution\n- zone distribution / entropy\n- service-pair spatial displacement",
    "05 §2-D Control / Reveal":
        "### D. Control / Reveal\n- control type distribution\n- nav container type\n- reveal direction\n"
        "- nav container depth",
    "05 §3 no composite score":
        "가중합 단일 score 생성 금지. Secondary visualization으로 Gower/mixed distance를 쓸 수 있으나 규범적 "
        "threshold나 '고령자 부담 점수'로 해석 금지.",
    "05 §4 family denominator":
        "family별:\n- n=10 denominator 고정\n- median/IQR/range\n- categorical distribution + entropy",
    "03 §1 viewport":
        "- viewport `390×844 CSS px`",
    "02 §3 fact_surface_state":
        "한 행 = 한 target의 한 scroll state. ... `state_index` (`S0`, `S1`...) / `scroll_y` / "
        "`viewport_width/height` / `task_control_visible` / `entry_x_norm / entry_y_norm` / `entry_zone` / "
        "`entry_control_type` / `nav_container_type` / `reveal_direction`",
}

# --------------------------------------------------------------------------------------
# 1. Frozen enumerations — transcribed literally from 04 §4, no additions.
# --------------------------------------------------------------------------------------

ENTRY_ZONE_ENUM = ("TOP_LEFT", "TOP_CENTER", "TOP_RIGHT", "MID", "BOTTOM", "FLOATING", "DRAWER")
# Subset that is a function of normalized (x, y) alone. FLOATING and DRAWER describe
# containment/positioning STATE, not a viewport region — 04 gives no rule to derive them
# from coordinates (AMB-S02), so geometry can never emit them.
ENTRY_ZONE_GEOMETRIC_SUBSET = ("TOP_LEFT", "TOP_CENTER", "TOP_RIGHT", "MID", "BOTTOM")
ENTRY_ZONE_STATE_SUBSET = ("FLOATING", "DRAWER")

ENTRY_CONTROL_TYPE_ENUM = (
    "TEXT_LINK", "TEXT_BUTTON", "ICON_TEXT", "ICON_ONLY", "TAB", "BOTTOM_NAV",
    "HAMBURGER", "CARD", "SEARCHBOX", "LIST_ITEM", "OTHER",
)
NAV_CONTAINER_TYPE_ENUM = (
    "NONE", "HAMBURGER", "LEFT_DRAWER", "RIGHT_DRAWER", "TOP_DROPDOWN",
    "BOTTOM_SHEET", "MODAL_MENU", "INLINE_EXPAND",
)
REVEAL_DIRECTION_ENUM = ("NONE", "LEFT", "RIGHT", "TOP", "BOTTOM", "CENTER", "INLINE")

# 04 §5 names exactly three reveal tokens, then writes "등" (etc.). The set is therefore
# OPEN at the SSOT level (AMB-S06). We implement the three NAMED tokens as a closed set and
# require any extension to be passed in explicitly by the caller.
NAMED_REVEAL_TOKENS = ("OPEN_GLOBAL_MENU", "OPEN_LOCAL_MENU", "EXPAND_ACCORDION")
ENDPOINT_TOKEN = "ENDPOINT_REACHED"

MISSING = None  # sentinel discipline: absence is None, and is NEVER coerced to 0 / 0.0 / "".


class UnresolvedDefinition(RuntimeError):
    """Raised when a computation would require an operationalization SSOTV3 has not frozen."""


class FixtureOnlyPolicyLeak(RuntimeError):
    """Raised if a fixture-only parameterization is used on non-fixture data."""


# --------------------------------------------------------------------------------------
# 2. AMBIGUOUS_DEFINITION register — recorded, NOT filled in by this lane.
# --------------------------------------------------------------------------------------

AMBIGUOUS_DEFINITIONS: list[dict[str, str]] = [
    {
        "id": "AMB-S01",
        "variable": "entry_zone",
        "issue": "04 §6 fixes NO numeric boundary for the zone bands. No x cut (LEFT|CENTER|RIGHT) and no "
                 "y cut (TOP|MID|BOTTOM) appears anywhere in SSOTV3 (grep over 00-15 returns nothing). "
                 "entry_zone therefore cannot be derived from (x_norm, y_norm) without new operationalization.",
        "lane_s_action": "classify_zone_geometric() REQUIRES an injected ZonePolicy and ships NO default. "
                         "Fixtures use FIXTURE_ONLY_ZONE_POLICY, which the code refuses to apply to non-fixture "
                         "data. Collected entry_zone values are validated + tabulated, never recomputed.",
        "owner": "A (SSOT) — must freeze boundaries or declare entry_zone collector-coded only.",
    },
    {
        "id": "AMB-S02",
        "variable": "entry_zone",
        "issue": "FLOATING and DRAWER are in the same enum as five viewport-region labels but are containment/"
                 "positioning STATES, not regions. A control can simultaneously be inside a drawer and at the "
                 "top-right of the viewport. No precedence rule is given.",
        "lane_s_action": "Geometry emits only the 5-region subset. State categories are pass-through only, and "
                         "zone-vs-geometry cross-checks are skipped (reported as SKIPPED_STATE_ZONE) for them.",
        "owner": "A (SSOT).",
    },
    {
        "id": "AMB-S03",
        "variable": "entry_zone",
        "issue": "Taxonomy is asymmetric: the TOP band is split three ways on x, MID and BOTTOM are not. Whether "
                 "MID/BOTTOM ignore x, or whether TOP_* also covers non-top controls, is unstated.",
        "lane_s_action": "Implemented as: x is consulted only inside the TOP band. This follows the enum literally "
                         "but is an inference, so it is registered here rather than presented as settled.",
        "owner": "A (SSOT).",
    },
    {
        "id": "AMB-S04",
        "variable": "entry_x_norm / entry_y_norm",
        "issue": "'viewport로 정규화' does not say whether values may fall outside [0,1] (control partially "
                 "off-screen, or below the fold in state Sn), nor whether clamping is allowed, nor which state's "
                 "viewport is the denominator when the control is first seen at S2.",
        "lane_s_action": "No clamping. Out-of-range values are preserved and flagged "
                         "(`out_of_unit_range=True`); the per-state viewport on the same row is used.",
        "owner": "A (SSOT) / B (collector).",
    },
    {
        "id": "AMB-S05",
        "variable": "s0_task_control_visible",
        "issue": "'직접 보이는가' vs `task_control_occlusion` (02 §5): whether a control rendered at S0 but "
                 "covered by an overlay counts as visible is unstated.",
        "lane_s_action": "Pass-through of the collected boolean only. No occlusion arbitration performed.",
        "owner": "A (SSOT).",
    },
    {
        "id": "AMB-S06",
        "variable": "menu_dependency",
        "issue": "04 §5 lists three reveal tokens then writes '등' (etc.), leaving the token set open. SWITCH_TAB "
                 "is a canonical token (04 §2) and is arguably a reveal, but is not named.",
        "lane_s_action": "Closed set = the three NAMED tokens. Any extension must be passed explicitly via "
                         "`extra_reveal_tokens`; the default is empty and SWITCH_TAB is NOT counted.",
        "owner": "A (SSOT).",
    },
    {
        "id": "AMB-S07",
        "variable": "menu_dependency",
        "issue": "'endpoint 전' is undefined when the run terminates at AUTH_GATE / BLOCKED / ABSTAIN and no "
                 "ENDPOINT_REACHED token exists. Also, 04 §4 says 'action_sequence' but 02 §4 stores two "
                 "sequences (task_flow_sequence, experienced_flow_sequence) and no field named action_sequence.",
        "lane_s_action": "Prefix = up to ENDPOINT_REACHED if present, else the whole sequence; the choice is "
                         "reported per row as `endpoint_cut_basis`. `sequence_field` is a REQUIRED argument — "
                         "the harness will not silently pick one of the two sequences.",
        "owner": "A (SSOT).",
    },
    {
        "id": "AMB-S08",
        "variable": "nav_container_depth",
        "issue": "'task control 노출 전 nested reveal 수' presupposes an identifiable exposure step, but no rule "
                 "defines which step index constitutes exposure, nor whether sibling (non-nested) reveals count.",
        "lane_s_action": "recompute_nav_container_depth() requires an explicit `exposure_step_index`; it is never "
                         "inferred. With no index supplied the stored collector value is validated, not recomputed.",
        "owner": "A (SSOT) / B (collector).",
    },
    {
        "id": "AMB-S09",
        "variable": "reveal_direction",
        "issue": "No mapping between nav_container_type and reveal_direction is fixed (e.g. whether LEFT_DRAWER "
                 "must imply LEFT, or INLINE_EXPAND must imply INLINE).",
        "lane_s_action": "Contingency table only (type x direction). No combination is scored, flagged as "
                         "invalid, or corrected.",
        "owner": "A (SSOT).",
    },
    {
        "id": "AMB-S10",
        "variable": "zone entropy (05 §2-B)",
        "issue": "Logarithm base is unspecified, and it is unspecified whether the support k is the full enum "
                 "cardinality (7) or the observed support, and whether missing rows enter the denominator "
                 "given 05 §4's fixed n=10.",
        "lane_s_action": "Shannon entropy reported in BITS with the base recorded; both max_entropy_enum "
                         "(log2 7) and max_entropy_observed (log2 k_obs) reported; proportions computed over "
                         "n_valid with n_declared=10 and n_missing reported alongside. No single figure is "
                         "presented as the entropy.",
        "owner": "A (SSOT) / C (report convention).",
    },
    {
        "id": "AMB-S11",
        "variable": "service-pair spatial displacement (05 §2-B)",
        "issue": "'displacement' names no metric (Euclidean vs Manhattan vs component-wise) and no aspect-ratio "
                 "handling — normalized x and y come from a 390x844 viewport, so one normalized unit of x is "
                 "not one normalized unit of y in physical terms.",
        "lane_s_action": "Raw dx and dy components are reported for every cell alongside the Euclidean value; "
                         "`metric` is an explicit parameter. No physical rescaling is applied or implied.",
        "owner": "A (SSOT).",
    },
    {
        "id": "AMB-S12",
        "variable": "counterexample detector: 'same position, different hierarchy'",
        "issue": "'same position' has no tolerance defined. A coordinate-epsilon comparison would require a "
                 "threshold that SSOTV3 does not contain.",
        "lane_s_action": "Default mode is `zone` — exact equality of the collected categorical entry_zone, "
                         "which introduces no threshold. A `coordinate_epsilon` mode exists but has NO default "
                         "epsilon and raises UnresolvedDefinition unless the caller passes one explicitly.",
        "owner": "A (SSOT).",
    },
    {
        "id": "AMB-S13",
        "variable": "counterexample detector: 'same visible label, different control type'",
        "issue": "Label equivalence (unicode/whitespace normalization, synonym map) is defined in 04 §5 for "
                 "`label_relation` and is Lane L's deliverable, not Lane S's.",
        "lane_s_action": "The detector takes a REQUIRED `label_key_fn` injected by the caller. Lane S ships only "
                         "`identity_label_key` (raw byte-exact, no normalization) so that Lane L's normalizer can "
                         "be plugged in unchanged. Lane S reports the control_type divergence side only.",
        "owner": "L (label normalization).",
    },
]

# --------------------------------------------------------------------------------------
# 3. Mutable primitives.
#    Each primitive isolates ONE decision so mutation testing can corrupt exactly one thing.
# --------------------------------------------------------------------------------------


def _below_cut(value: float, cut: float) -> bool:
    """Band membership test. Lower band is [prev_cut, cut); the cut itself falls upward."""
    return value < cut


def _pick_axes(x: float, y: float) -> tuple[float, float]:
    return (x, y)


def _coord_or_none(value: Any) -> Any:
    """Missing stays missing. This function exists so that 'missing -> 0.0' is a single mutation."""
    return value


def _distance(dx: float, dy: float) -> float:
    return math.hypot(dx, dy)


def _log_p(p: float) -> float:
    return math.log(p, 2)


def _pick_first_state(indices: Sequence[int]) -> int:
    return min(indices)


def _hierarchy_key(obs: dict) -> tuple:
    return (
        obs.get("nav_container_type", MISSING),
        obs.get("reveal_direction", MISSING),
        obs.get("nav_container_depth", MISSING),
        obs.get("menu_dependency", MISSING),
    )


def _label_groupable(label: Any) -> bool:
    """Missing / empty labels must never form a collision group."""
    return isinstance(label, str) and label != ""


def _endpoint_cut(sequence: Sequence[str]) -> int:
    if ENDPOINT_TOKEN in sequence:
        return list(sequence).index(ENDPOINT_TOKEN)
    return len(sequence)


def _family_denominator(declared_n: int, observed_n: int) -> int:
    """05 §4: family n=10 denominator is FIXED. Observed n never replaces it."""
    return declared_n


# --------------------------------------------------------------------------------------
# 4. Zone policy (injected, never defaulted)
# --------------------------------------------------------------------------------------

class ZonePolicy:
    """Boundary parameterization for geometric zone classification.

    SSOTV3 does not define these numbers (AMB-S01). Therefore a policy must be supplied by
    the caller and must declare its provenance. A policy whose `source` is FIXTURE_ONLY may
    only be used with `allow_fixture_only=True`, which the fixture suite sets and the
    production analysis entrypoint never does.
    """

    def __init__(self, *, y_top_max: float, y_mid_max: float, x_left_max: float,
                 x_center_max: float, source: str, note: str = "") -> None:
        if not source:
            raise UnresolvedDefinition("ZonePolicy.source must declare provenance.")
        self.y_top_max = y_top_max
        self.y_mid_max = y_mid_max
        self.x_left_max = x_left_max
        self.x_center_max = x_center_max
        self.source = source
        self.note = note

    def as_dict(self) -> dict:
        return {
            "y_top_max": self.y_top_max, "y_mid_max": self.y_mid_max,
            "x_left_max": self.x_left_max, "x_center_max": self.x_center_max,
            "source": self.source, "note": self.note,
            "boundary_rule": "lower band is half-open [prev, cut); a value exactly on a cut goes to the UPPER band",
        }


FIXTURE_ONLY_ZONE_POLICY = ZonePolicy(
    y_top_max=1.0 / 3.0, y_mid_max=2.0 / 3.0, x_left_max=1.0 / 3.0, x_center_max=2.0 / 3.0,
    source="FIXTURE_ONLY_NOT_SSOT",
    note="Equal thirds. Chosen ONLY to exercise classifier mechanics on synthetic fixtures. "
         "This is NOT an SSOT boundary and must never be used to code real observations.",
)

SSOT_ZONE_POLICY = None  # intentionally absent: SSOTV3 freezes no boundaries (AMB-S01).


# --------------------------------------------------------------------------------------
# 5. Variable implementations
# --------------------------------------------------------------------------------------

def normalize_center(bbox: Any, viewport_width: Any, viewport_height: Any) -> dict:
    """04 §4: control centre normalized by viewport. No clamping (AMB-S04).

    Every exit path — including the missing-input paths — routes its value through
    `_coord_or_none`, so that "missing silently becomes 0.0" is reachable as a single
    mutation (M02). An earlier revision guarded missingness with early `return`s; that
    left `_coord_or_none` off the missing path and M02 escaped undetected. Recorded in
    fixture_results.mutation_notes.
    """
    raw_x: Any = MISSING
    raw_y: Any = MISSING
    reason = "OK"
    if not isinstance(bbox, dict):
        reason = "MISSING_BBOX"
    else:
        try:
            bx, by = float(bbox["x"]), float(bbox["y"])
            bw, bh = float(bbox["width"]), float(bbox["height"])
        except (KeyError, TypeError, ValueError):
            reason = "MALFORMED_BBOX"
        else:
            if viewport_width in (None, 0) or viewport_height in (None, 0):
                reason = "MISSING_VIEWPORT"
            else:
                vw, vh = float(viewport_width), float(viewport_height)
                if vw <= 0 or vh <= 0:
                    reason = "NONPOSITIVE_VIEWPORT"
                else:
                    raw_x = (bx + bw / 2.0) / vw
                    raw_y = (by + bh / 2.0) / vh
    x = _coord_or_none(raw_x)
    y = _coord_or_none(raw_y)
    out = {"entry_x_norm": x, "entry_y_norm": y, "reason": reason,
           "out_of_unit_range": MISSING}
    if x is not MISSING and y is not MISSING:
        out["out_of_unit_range"] = not (0.0 <= float(x) <= 1.0 and 0.0 <= float(y) <= 1.0)
    return out


def classify_zone_geometric(x_norm: Any, y_norm: Any, policy: ZonePolicy | None = None,
                            *, allow_fixture_only: bool = False) -> Any:
    """Geometric zone from normalized centre. Requires an injected ZonePolicy (AMB-S01).

    Emits only ENTRY_ZONE_GEOMETRIC_SUBSET. FLOATING/DRAWER are unreachable here (AMB-S02).
    Missing coordinates return None, never a zone.
    """
    if policy is None:
        raise UnresolvedDefinition(
            "entry_zone cannot be derived: SSOTV3 04 §6 freezes no zone boundaries (AMB-S01). "
            "Supply an explicit ZonePolicy or use the collected entry_zone field."
        )
    if policy.source == "FIXTURE_ONLY_NOT_SSOT" and not allow_fixture_only:
        raise FixtureOnlyPolicyLeak(
            "FIXTURE_ONLY_ZONE_POLICY may not be applied outside the fixture suite."
        )
    if x_norm is MISSING or y_norm is MISSING:
        return MISSING
    x, y = _pick_axes(float(x_norm), float(y_norm))
    if _below_cut(y, policy.y_top_max):
        if _below_cut(x, policy.x_left_max):
            return "TOP_LEFT"
        if _below_cut(x, policy.x_center_max):
            return "TOP_CENTER"
        return "TOP_RIGHT"
    if _below_cut(y, policy.y_mid_max):
        return "MID"          # AMB-S03: x is not consulted outside the TOP band
    return "BOTTOM"


def validate_categorical(value: Any, enum: Sequence[str]) -> dict:
    if value is MISSING:
        return {"value": MISSING, "status": "MISSING"}
    if value in enum:
        return {"value": value, "status": "VALID"}
    return {"value": value, "status": "OUT_OF_ENUM"}   # never coerced


def s0_task_control_visible(states: Iterable[dict]) -> Any:
    """Pass-through of the S0 row's collected task_control_visible (AMB-S05)."""
    for st in states:
        if st.get("state_index") == "S0":
            v = st.get("task_control_visible", MISSING)
            return v if isinstance(v, bool) else MISSING
    return MISSING  # no S0 row observed -> unknown, NOT False


def first_visible_scroll_state(states: Iterable[dict]) -> Any:
    """Lowest-index state where task_control_visible is True. None if never visible."""
    idxs: list[int] = []
    for st in states:
        si = st.get("state_index")
        if st.get("task_control_visible") is True and isinstance(si, str) and si.startswith("S"):
            try:
                idxs.append(int(si[1:]))
            except ValueError:
                continue
    if not idxs:
        return MISSING  # never observed visible -> None, NOT "S0" and NOT 0
    return "S%d" % _pick_first_state(idxs)


def menu_dependency(sequence: Any, *, sequence_field: str,
                    extra_reveal_tokens: Sequence[str] = ()) -> dict:
    """04 §5. Reveal token present strictly before the endpoint cut (AMB-S06, AMB-S07)."""
    if sequence_field not in ("task_flow_sequence", "experienced_flow_sequence"):
        raise UnresolvedDefinition(
            "sequence_field must be named explicitly: 04 §4 says 'action_sequence' but 02 §4 stores "
            "task_flow_sequence and experienced_flow_sequence (AMB-S07)."
        )
    if sequence is MISSING:
        return {"menu_dependency": MISSING, "endpoint_cut_basis": MISSING,
                "sequence_field": sequence_field, "reason": "MISSING_SEQUENCE"}
    seq = list(sequence)
    cut = _endpoint_cut(seq)
    tokens = set(NAMED_REVEAL_TOKENS) | set(extra_reveal_tokens)
    present = [t for t in seq[:cut] if t in tokens]
    return {
        "menu_dependency": bool(present),
        "reveal_tokens_before_endpoint": present,
        "endpoint_cut_index": cut,
        "endpoint_cut_basis": "ENDPOINT_REACHED" if ENDPOINT_TOKEN in seq else "SEQUENCE_END_NO_ENDPOINT_TOKEN",
        "sequence_field": sequence_field,
        "reveal_token_set": sorted(tokens),
        "reason": "OK",
    }


def recompute_nav_container_depth(sequence: Any, exposure_step_index: Any,
                                  *, extra_reveal_tokens: Sequence[str] = ()) -> dict:
    """04 §5. Requires an explicit exposure step index — never inferred (AMB-S08)."""
    if exposure_step_index is MISSING:
        return {"nav_container_depth": MISSING, "reason": "NO_EXPOSURE_INDEX_SUPPLIED_AMB_S08"}
    if sequence is MISSING:
        return {"nav_container_depth": MISSING, "reason": "MISSING_SEQUENCE"}
    seq = list(sequence)
    tokens = set(NAMED_REVEAL_TOKENS) | set(extra_reveal_tokens)
    n = sum(1 for t in seq[:int(exposure_step_index)] if t in tokens)
    return {"nav_container_depth": n, "exposure_step_index": int(exposure_step_index),
            "nesting_verified": False, "reason": "OK_FLAT_COUNT_NESTING_NOT_VERIFIED_AMB_S08"}


# --------------------------------------------------------------------------------------
# 6. Descriptive statistics (05 §2-B / §2-D, §4). No thresholds, no composites.
# --------------------------------------------------------------------------------------

def coordinate_summary(observations: Sequence[dict], *, declared_family_n: int = 10) -> dict:
    """x/y distribution per 05 §2-B, with the fixed n=10 denominator of 05 §4."""
    xs = [o.get("entry_x_norm") for o in observations]
    ys = [o.get("entry_y_norm") for o in observations]
    out = {"n_declared": _family_denominator(declared_family_n, len(observations)),
           "n_rows": len(observations)}
    for name, vals in (("entry_x_norm", xs), ("entry_y_norm", ys)):
        valid = [float(v) for v in vals if v is not MISSING]
        d: dict[str, Any] = {"n_valid": len(valid), "n_missing": len(vals) - len(valid)}
        if valid:
            s = sorted(valid)
            q = statistics.quantiles(s, n=4, method="inclusive") if len(s) >= 2 else [s[0], s[0], s[0]]
            d.update({"min": s[0], "q1": q[0], "median": statistics.median(s), "q3": q[2],
                      "max": s[-1], "iqr": q[2] - q[0], "range": s[-1] - s[0]})
        else:
            d.update({k: MISSING for k in ("min", "q1", "median", "q3", "max", "iqr", "range")})
        out[name] = d
    return out


def categorical_distribution(observations: Sequence[dict], field: str, enum: Sequence[str],
                             *, declared_family_n: int = 10) -> dict:
    """Counts + proportions + Shannon entropy in bits. Base and support both reported (AMB-S10)."""
    counts: dict[str, int] = {}
    n_missing = 0
    out_of_enum: list[Any] = []
    for o in observations:
        v = o.get(field, MISSING)
        if v is MISSING:
            n_missing += 1
            continue
        if v not in enum:
            out_of_enum.append(v)
            continue
        counts[v] = counts.get(v, 0) + 1
    n_valid = sum(counts.values())
    props = {k: v / n_valid for k, v in counts.items()} if n_valid else {}
    ent = -sum(p * _log_p(p) for p in props.values() if p > 0) if props else (0.0 if n_valid else MISSING)
    k_obs = len(counts)
    return {
        "field": field,
        "n_declared": _family_denominator(declared_family_n, len(observations)),
        "n_rows": len(observations),
        "n_valid": n_valid,
        "n_missing": n_missing,
        "n_out_of_enum": len(out_of_enum),
        "out_of_enum_values": out_of_enum,
        "counts": counts,
        "proportions_over_n_valid": props,
        "proportions_over_n_declared": {k: v / declared_family_n for k, v in counts.items()},
        "entropy_bits": ent,
        "entropy_log_base": 2,
        "max_entropy_bits_observed_support": (math.log(k_obs, 2) if k_obs > 1 else 0.0) if n_valid else MISSING,
        "max_entropy_bits_full_enum": math.log(len(enum), 2),
        "entropy_denominator_note": "proportions over n_valid; n_declared and n_missing reported separately (AMB-S10)",
    }


def pairwise_spatial_displacement(observations: Sequence[dict], *, metric: str = "euclidean",
                                  declared_family_n: int = 10) -> dict:
    """05 §2-B service-pair displacement.

    45 cells for a family of 10 are MATRIX CELLS, not n=45 independent samples (05 §1).
    The reported denominator stays n=10.
    """
    if metric != "euclidean":
        raise UnresolvedDefinition(
            "05 §2-B names no metric (AMB-S11); only the explicitly-labelled 'euclidean' option is implemented."
        )
    ids = [o.get("service_id") for o in observations]
    cells = []
    n_computable = 0
    for (i, a), (j, b) in combinations(list(enumerate(observations)), 2):
        ax, ay = a.get("entry_x_norm"), a.get("entry_y_norm")
        bx, by = b.get("entry_x_norm"), b.get("entry_y_norm")
        if MISSING in (ax, ay, bx, by):
            cells.append({"a": ids[i], "b": ids[j], "dx": MISSING, "dy": MISSING,
                          "displacement": MISSING, "reason": "MISSING_COORDINATE"})
            continue
        dx = float(bx) - float(ax)
        dy = float(by) - float(ay)
        cells.append({"a": ids[i], "b": ids[j], "dx": dx, "dy": dy,
                      "displacement": _distance(dx, dy), "reason": "OK"})
        n_computable += 1
    vals = [c["displacement"] for c in cells if c["displacement"] is not MISSING]
    return {
        "analysis_denominator_n": _family_denominator(declared_family_n, len(observations)),
        "denominator_note": "05 §1: the pair cells are distance-matrix cells, NOT independent samples. "
                            "n stays the family n; pair count is reported only as matrix coverage.",
        "matrix_cell_count": len(cells),
        "matrix_cells_computable": n_computable,
        "matrix_cells_missing": len(cells) - n_computable,
        "metric": metric,
        "components_reported": True,
        "cells": cells,
        "cell_value_median": statistics.median(vals) if vals else MISSING,
        "cell_value_min": min(vals) if vals else MISSING,
        "cell_value_max": max(vals) if vals else MISSING,
    }


def reveal_contingency(observations: Sequence[dict]) -> dict:
    """05 §2-D: nav_container_type x reveal_direction cross-tab. No combination is judged (AMB-S09)."""
    table: dict[str, dict[str, int]] = {}
    for o in observations:
        t = o.get("nav_container_type", MISSING)
        d = o.get("reveal_direction", MISSING)
        tk = t if t is not MISSING else "__MISSING__"
        dk = d if d is not MISSING else "__MISSING__"
        table.setdefault(tk, {})
        table[tk][dk] = table[tk].get(dk, 0) + 1
    return {"table": table,
            "note": "descriptive only; SSOTV3 fixes no type->direction mapping (AMB-S09)"}


# --------------------------------------------------------------------------------------
# 7. Counterexample detectors
# --------------------------------------------------------------------------------------

def detect_same_position_different_hierarchy(observations: Sequence[dict], *, mode: str = "zone",
                                             epsilon: Any = None) -> dict:
    """Counterexample A: position agrees, menu hierarchy does not.

    mode='zone'            -> exact equality of the collected categorical entry_zone (no threshold).
    mode='coordinate_epsilon' -> requires an explicitly supplied epsilon (AMB-S12); no default exists.
    """
    if mode == "coordinate_epsilon" and epsilon is None:
        raise UnresolvedDefinition(
            "'same position' has no tolerance in SSOTV3 (AMB-S12); pass epsilon explicitly or use mode='zone'."
        )
    if mode not in ("zone", "coordinate_epsilon"):
        raise UnresolvedDefinition("unknown position-equivalence mode: %r" % (mode,))

    hits, negatives = [], []
    for a, b in combinations(observations, 2):
        if mode == "zone":
            za, zb = a.get("entry_zone", MISSING), b.get("entry_zone", MISSING)
            if za is MISSING or zb is MISSING:
                continue                      # missing never forms a match
            same_pos = (za == zb)
            basis = {"entry_zone": za}
        else:
            ax, ay = a.get("entry_x_norm"), a.get("entry_y_norm")
            bx, by = b.get("entry_x_norm"), b.get("entry_y_norm")
            if MISSING in (ax, ay, bx, by):
                continue
            same_pos = _distance(float(bx) - float(ax), float(by) - float(ay)) <= float(epsilon)
            basis = {"epsilon": float(epsilon)}
        if not same_pos:
            continue
        ka, kb = _hierarchy_key(a), _hierarchy_key(b)
        rec = {"a": a.get("service_id"), "b": b.get("service_id"),
               "position_basis": basis,
               "hierarchy_a": {"nav_container_type": ka[0], "reveal_direction": ka[1],
                               "nav_container_depth": ka[2], "menu_dependency": ka[3]},
               "hierarchy_b": {"nav_container_type": kb[0], "reveal_direction": kb[1],
                               "nav_container_depth": kb[2], "menu_dependency": kb[3]}}
        (hits if ka != kb else negatives).append(rec)
    return {"detector": "same_position_different_hierarchy", "mode": mode,
            "counterexamples": hits, "same_position_same_hierarchy": negatives,
            "counterexample_count": len(hits),
            "note": "descriptive counterexample listing; no severity, score, or threshold attached"}


def identity_label_key(label: Any) -> Any:
    """Byte-exact identity. Lane S performs NO label normalization (04 §5 / AMB-S13 -> Lane L)."""
    return label


def detect_same_label_different_control_type(observations: Sequence[dict],
                                             label_key_fn: Callable[[Any], Any]) -> dict:
    """Counterexample B: the visible label agrees but entry_control_type does not.

    `label_key_fn` is REQUIRED and injected: label equivalence is Lane L's deliverable.
    Lane S only reports the control_type side of the divergence.
    """
    if label_key_fn is None:
        raise UnresolvedDefinition("label_key_fn must be supplied by Lane L (AMB-S13).")
    groups: dict[Any, list[dict]] = {}
    ungroupable = 0
    for o in observations:
        raw = o.get("visible_label_text", MISSING)
        if not _label_groupable(raw):
            ungroupable += 1
            continue
        groups.setdefault(label_key_fn(raw), []).append(o)
    hits, negatives = [], []
    for key, members in groups.items():
        types = {m.get("entry_control_type", MISSING) for m in members}
        rec = {"label_key": key,
               "services": [m.get("service_id") for m in members],
               "control_types": sorted(str(t) for t in types),
               "distinct_control_type_count": len(types)}
        (hits if len(types) > 1 else negatives).append(rec)
    return {"detector": "same_label_different_control_type",
            "label_key_fn": getattr(label_key_fn, "__name__", "injected"),
            "label_normalization_owner": "LANE_L",
            "rows_ungroupable_missing_label": ungroupable,
            "counterexamples": hits, "same_label_same_control_type": negatives,
            "counterexample_count": len(hits),
            "note": "control_type divergence only; label equivalence judgement is not made here"}


# --------------------------------------------------------------------------------------
# 8. Synthetic fixtures with pre-planted answers
# --------------------------------------------------------------------------------------

VP_W, VP_H = 390, 844   # 03 §1


def _obs(sid, **kw):
    d = {"service_id": sid, "family_id": "FX", "entry_x_norm": MISSING, "entry_y_norm": MISSING,
         "entry_zone": MISSING, "entry_control_type": MISSING, "visible_label_text": MISSING,
         "nav_container_type": MISSING, "reveal_direction": MISSING,
         "nav_container_depth": MISSING, "menu_dependency": MISSING}
    d.update(kw)
    return d


def _check(name, kind, got, expected, notes=""):
    ok = (got == expected)
    return {"fixture": name, "kind": kind, "expected": expected, "observed": got,
            "pass": ok, "notes": notes}


def run_fixtures() -> list[dict]:
    r: list[dict] = []
    P = FIXTURE_ONLY_ZONE_POLICY
    z = lambda x, y: classify_zone_geometric(x, y, P, allow_fixture_only=True)

    # ---- POSITIVE: zone grid, answers planted by construction --------------------------
    grid = [(0.10, 0.10, "TOP_LEFT"), (0.50, 0.10, "TOP_CENTER"), (0.90, 0.10, "TOP_RIGHT"),
            (0.10, 0.50, "MID"), (0.50, 0.50, "MID"), (0.90, 0.50, "MID"),
            (0.10, 0.90, "BOTTOM"), (0.50, 0.90, "BOTTOM"), (0.90, 0.90, "BOTTOM")]
    for x, y, exp in grid:
        r.append(_check("P-ZONE-GRID x=%.2f y=%.2f" % (x, y), "positive", z(x, y), exp,
                        "AMB-S03: x consulted only inside TOP band"))

    # ---- POSITIVE: exact boundary values -----------------------------------------------
    r.append(_check("P-ZONE-BOUND y=1/3 exact", "positive", z(0.10, 1.0 / 3.0), "MID",
                    "value on a cut goes to the UPPER band (half-open [prev, cut))"))
    r.append(_check("P-ZONE-BOUND y=2/3 exact", "positive", z(0.10, 2.0 / 3.0), "BOTTOM"))
    r.append(_check("P-ZONE-BOUND x=1/3 exact", "positive", z(1.0 / 3.0, 0.10), "TOP_CENTER"))
    r.append(_check("P-ZONE-BOUND x=2/3 exact", "positive", z(2.0 / 3.0, 0.10), "TOP_RIGHT"))
    r.append(_check("P-ZONE-BOUND y just below 1/3", "positive", z(0.10, 1.0 / 3.0 - 1e-9), "TOP_LEFT"))
    r.append(_check("P-ZONE-BOUND corner (0,0)", "positive", z(0.0, 0.0), "TOP_LEFT"))
    r.append(_check("P-ZONE-BOUND corner (1,1)", "positive", z(1.0, 1.0), "BOTTOM"))

    # ---- POSITIVE: normalize_center ----------------------------------------------------
    got = normalize_center({"x": 195.0, "y": 0.0, "width": 0.0, "height": 84.4}, VP_W, VP_H)
    r.append(_check("P-NORM centre of 390x844", "positive",
                    (round(got["entry_x_norm"], 6), round(got["entry_y_norm"], 6), got["out_of_unit_range"]),
                    (0.5, 0.05, False)))
    got = normalize_center({"x": 380.0, "y": 800.0, "width": 40.0, "height": 100.0}, VP_W, VP_H)
    r.append(_check("P-NORM off-viewport preserved not clamped", "positive",
                    (round(got["entry_x_norm"], 6) > 1.0, round(got["entry_y_norm"], 6) > 1.0,
                     got["out_of_unit_range"]),
                    (True, True, True), "AMB-S04: no clamping"))

    # ---- POSITIVE: surface-state variables ---------------------------------------------
    states = [{"state_index": "S0", "task_control_visible": False},
              {"state_index": "S1", "task_control_visible": False},
              {"state_index": "S2", "task_control_visible": True},
              {"state_index": "S3", "task_control_visible": True}]
    r.append(_check("P-S0VIS collected False at S0", "positive", s0_task_control_visible(states), False))
    r.append(_check("P-FVSS first visible = S2", "positive", first_visible_scroll_state(states), "S2"))
    r.append(_check("P-FVSS visible already at S0", "positive",
                    first_visible_scroll_state([{"state_index": "S0", "task_control_visible": True},
                                                {"state_index": "S1", "task_control_visible": True}]), "S0"))

    # ---- POSITIVE: menu_dependency -----------------------------------------------------
    seq_a = ["OPEN_GLOBAL_MENU", "SELECT_FUNCTION", "ENDPOINT_REACHED"]
    md = menu_dependency(seq_a, sequence_field="task_flow_sequence")
    r.append(_check("P-MD reveal before endpoint", "positive",
                    (md["menu_dependency"], md["endpoint_cut_index"]), (True, 2)))
    seq_b = ["SELECT_FUNCTION", "ENDPOINT_REACHED", "OPEN_LOCAL_MENU"]
    md = menu_dependency(seq_b, sequence_field="task_flow_sequence")
    r.append(_check("P-MD reveal AFTER endpoint is not counted", "positive", md["menu_dependency"], False,
                    "guards the endpoint prefix rule of 04 §5"))
    md = menu_dependency(["SWITCH_TAB", "SELECT_FUNCTION", "ENDPOINT_REACHED"],
                         sequence_field="task_flow_sequence")
    r.append(_check("P-MD SWITCH_TAB not in named reveal set", "positive", md["menu_dependency"], False,
                    "AMB-S06: '등' left the set open; only the three NAMED tokens are counted"))
    md = menu_dependency(["OPEN_GLOBAL_MENU", "SELECT_FUNCTION", "AUTH_GATE"],
                         sequence_field="task_flow_sequence")
    r.append(_check("P-MD auth-terminal cut basis", "positive",
                    (md["menu_dependency"], md["endpoint_cut_basis"]),
                    (True, "SEQUENCE_END_NO_ENDPOINT_TOKEN"), "AMB-S07 recorded per row"))

    # ---- POSITIVE: nav_container_depth -------------------------------------------------
    d = recompute_nav_container_depth(
        ["OPEN_GLOBAL_MENU", "EXPAND_ACCORDION", "SELECT_FUNCTION", "ENDPOINT_REACHED"], 2)
    r.append(_check("P-NCD two reveals before exposure idx 2", "positive", d["nav_container_depth"], 2))

    # ---- POSITIVE: displacement (3-4-5 triangle) ---------------------------------------
    pair = [_obs("A", entry_x_norm=0.10, entry_y_norm=0.20),
            _obs("B", entry_x_norm=0.40, entry_y_norm=0.60)]
    pd = pairwise_spatial_displacement(pair, declared_family_n=10)
    r.append(_check("P-DISP euclidean 0.3/0.4 -> 0.5", "positive",
                    round(pd["cells"][0]["displacement"], 10), 0.5))
    r.append(_check("P-DISP denominator stays family n=10", "positive",
                    (pd["analysis_denominator_n"], pd["matrix_cell_count"]), (10, 1),
                    "05 §1: pairs are matrix cells, not n"))
    ten = [_obs("S%d" % i, entry_x_norm=0.1 * i, entry_y_norm=0.05 * i) for i in range(10)]
    pd10 = pairwise_spatial_displacement(ten, declared_family_n=10)
    r.append(_check("P-DISP family of 10 -> 45 cells, n=10", "positive",
                    (pd10["matrix_cell_count"], pd10["analysis_denominator_n"]), (45, 10)))

    # ---- POSITIVE: entropy -------------------------------------------------------------
    uni = [_obs("S%d" % i, entry_zone=zz) for i, zz in
           enumerate(["TOP_LEFT", "TOP_CENTER", "MID", "BOTTOM"])]
    cd = categorical_distribution(uni, "entry_zone", ENTRY_ZONE_ENUM, declared_family_n=10)
    r.append(_check("P-ENT uniform over 4 -> 2.0 bits", "positive", round(cd["entropy_bits"], 10), 2.0))
    r.append(_check("P-ENT fixed denominator n=10 with 4 rows", "positive",
                    (cd["n_declared"], cd["n_valid"]), (10, 4), "05 §4"))
    deg = [_obs("S%d" % i, entry_zone="MID") for i in range(5)]
    cd2 = categorical_distribution(deg, "entry_zone", ENTRY_ZONE_ENUM, declared_family_n=10)
    r.append(_check("P-ENT degenerate single category -> 0.0 bits", "positive", cd2["entropy_bits"], 0.0))

    # ---- POSITIVE: detector A ----------------------------------------------------------
    a_pos = [_obs("A", entry_zone="TOP_RIGHT", nav_container_type="HAMBURGER",
                  reveal_direction="LEFT", nav_container_depth=1, menu_dependency=True),
             _obs("B", entry_zone="TOP_RIGHT", nav_container_type="NONE",
                  reveal_direction="NONE", nav_container_depth=0, menu_dependency=False)]
    da = detect_same_position_different_hierarchy(a_pos)
    r.append(_check("P-DETA same zone, different hierarchy", "positive", da["counterexample_count"], 1))
    a_depth = [_obs("A", entry_zone="MID", nav_container_type="HAMBURGER", reveal_direction="LEFT",
                    nav_container_depth=1, menu_dependency=True),
               _obs("B", entry_zone="MID", nav_container_type="HAMBURGER", reveal_direction="LEFT",
                    nav_container_depth=2, menu_dependency=True)]
    r.append(_check("P-DETA depth-only difference still detected", "positive",
                    detect_same_position_different_hierarchy(a_depth)["counterexample_count"], 1))

    # ---- POSITIVE: detector B ----------------------------------------------------------
    b_pos = [_obs("A", visible_label_text="예매", entry_control_type="TEXT_LINK"),
             _obs("B", visible_label_text="예매", entry_control_type="CARD")]
    db = detect_same_label_different_control_type(b_pos, identity_label_key)
    r.append(_check("P-DETB same label, different control type", "positive", db["counterexample_count"], 1))

    # ---- NEGATIVE ----------------------------------------------------------------------
    a_neg1 = [_obs("A", entry_zone="MID", nav_container_type="NONE", reveal_direction="NONE",
                   nav_container_depth=0, menu_dependency=False),
              _obs("B", entry_zone="MID", nav_container_type="NONE", reveal_direction="NONE",
                   nav_container_depth=0, menu_dependency=False)]
    r.append(_check("N-DETA same zone, identical hierarchy -> no hit", "negative",
                    detect_same_position_different_hierarchy(a_neg1)["counterexample_count"], 0))
    a_neg2 = [_obs("A", entry_zone="TOP_LEFT", nav_container_type="HAMBURGER", reveal_direction="LEFT",
                   nav_container_depth=1, menu_dependency=True),
              _obs("B", entry_zone="BOTTOM", nav_container_type="NONE", reveal_direction="NONE",
                   nav_container_depth=0, menu_dependency=False)]
    r.append(_check("N-DETA different zone -> no hit even though hierarchy differs", "negative",
                    detect_same_position_different_hierarchy(a_neg2)["counterexample_count"], 0))
    a_neg3 = [_obs("A", entry_zone=MISSING, nav_container_type="HAMBURGER", nav_container_depth=1),
              _obs("B", entry_zone=MISSING, nav_container_type="NONE", nav_container_depth=0)]
    r.append(_check("N-DETA missing zone never matches missing zone", "negative",
                    detect_same_position_different_hierarchy(a_neg3)["counterexample_count"], 0,
                    "None is not a value"))
    b_neg1 = [_obs("A", visible_label_text="예매", entry_control_type="TEXT_LINK"),
              _obs("B", visible_label_text="예매", entry_control_type="TEXT_LINK")]
    r.append(_check("N-DETB same label, same control type -> no hit", "negative",
                    detect_same_label_different_control_type(b_neg1, identity_label_key)["counterexample_count"], 0))
    b_neg2 = [_obs("A", visible_label_text="예매", entry_control_type="TEXT_LINK"),
              _obs("B", visible_label_text="조회", entry_control_type="CARD")]
    r.append(_check("N-DETB different labels -> no hit", "negative",
                    detect_same_label_different_control_type(b_neg2, identity_label_key)["counterexample_count"], 0))
    b_neg3 = [_obs("A", visible_label_text=MISSING, entry_control_type="ICON_ONLY"),
              _obs("B", visible_label_text=MISSING, entry_control_type="CARD")]
    res_b3 = detect_same_label_different_control_type(b_neg3, identity_label_key)
    r.append(_check("N-DETB missing labels never group", "negative",
                    (res_b3["counterexample_count"], res_b3["rows_ungroupable_missing_label"]), (0, 2)))
    b_neg4 = [_obs("A", visible_label_text="", entry_control_type="ICON_ONLY"),
              _obs("B", visible_label_text="", entry_control_type="CARD")]
    r.append(_check("N-DETB empty-string labels never group", "negative",
                    detect_same_label_different_control_type(b_neg4, identity_label_key)["counterexample_count"], 0))

    g = normalize_center({"x": 10, "y": 10, "width": 10, "height": 10}, None, VP_H)
    r.append(_check("N-NORM missing viewport -> None not 0.0", "negative",
                    (g["entry_x_norm"], g["entry_y_norm"], g["reason"]),
                    (None, None, "MISSING_VIEWPORT")))
    g = normalize_center(MISSING, VP_W, VP_H)
    r.append(_check("N-NORM missing bbox -> None not 0.0", "negative",
                    (g["entry_x_norm"], g["reason"]), (None, "MISSING_BBOX")))
    r.append(_check("N-FVSS never visible -> None not S0", "negative",
                    first_visible_scroll_state([{"state_index": "S0", "task_control_visible": False},
                                                {"state_index": "S1", "task_control_visible": False}]), None))
    r.append(_check("N-S0VIS no S0 row -> None not False", "negative",
                    s0_task_control_visible([{"state_index": "S1", "task_control_visible": True}]), None))
    r.append(_check("N-ZONE missing coords -> None not a zone", "negative", z(MISSING, MISSING), None))

    try:
        classify_zone_geometric(0.5, 0.5, None)
        got = "NO_RAISE"
    except UnresolvedDefinition:
        got = "UnresolvedDefinition"
    r.append(_check("N-ZONE no policy -> refuses to derive", "negative", got, "UnresolvedDefinition",
                    "AMB-S01: SSOTV3 freezes no boundaries"))
    try:
        classify_zone_geometric(0.5, 0.5, FIXTURE_ONLY_ZONE_POLICY)
        got = "NO_RAISE"
    except FixtureOnlyPolicyLeak:
        got = "FixtureOnlyPolicyLeak"
    r.append(_check("N-ZONE fixture policy blocked outside fixtures", "negative", got, "FixtureOnlyPolicyLeak"))
    try:
        detect_same_position_different_hierarchy(a_pos, mode="coordinate_epsilon")
        got = "NO_RAISE"
    except UnresolvedDefinition:
        got = "UnresolvedDefinition"
    r.append(_check("N-DETA epsilon mode has no default tolerance", "negative", got, "UnresolvedDefinition",
                    "AMB-S12"))
    try:
        menu_dependency(["OPEN_GLOBAL_MENU"], sequence_field="action_sequence")
        got = "NO_RAISE"
    except UnresolvedDefinition:
        got = "UnresolvedDefinition"
    r.append(_check("N-MD sequence_field must be an existing schema field", "negative", got,
                    "UnresolvedDefinition", "AMB-S07"))
    r.append(_check("N-NCD no exposure index -> None not 0", "negative",
                    recompute_nav_container_depth(["OPEN_GLOBAL_MENU"], MISSING)["nav_container_depth"], None,
                    "AMB-S08"))
    r.append(_check("N-ENUM out-of-enum zone is flagged not coerced", "negative",
                    validate_categorical("TOP_MIDDLE", ENTRY_ZONE_ENUM)["status"], "OUT_OF_ENUM"))
    r.append(_check("N-ENUM geometry can never emit FLOATING/DRAWER", "negative",
                    any(z(x / 20.0, y / 20.0) in ENTRY_ZONE_STATE_SUBSET
                        for x in range(21) for y in range(21)), False, "AMB-S02"))
    mixed = [_obs("A", entry_x_norm=0.1, entry_y_norm=0.1), _obs("B")]
    pdm = pairwise_spatial_displacement(mixed, declared_family_n=10)
    r.append(_check("N-DISP missing coord -> None cell not 0.0", "negative",
                    (pdm["cells"][0]["displacement"], pdm["matrix_cells_missing"]), (None, 1)))
    part = [_obs("S%d" % i, entry_x_norm=0.5, entry_y_norm=0.5) for i in range(7)] + \
           [_obs("S%d" % i) for i in range(7, 10)]
    cs = coordinate_summary(part, declared_family_n=10)
    r.append(_check("N-DENOM missing rows keep n_declared=10", "negative",
                    (cs["n_declared"], cs["entry_x_norm"]["n_valid"], cs["entry_x_norm"]["n_missing"]),
                    (10, 7, 3), "05 §4: denominator is not shrunk to observed n"))
    return r


# --------------------------------------------------------------------------------------
# 9. Mutation testing — corrupt one primitive, confirm the fixtures catch it, restore.
# --------------------------------------------------------------------------------------

MUTANTS: list[tuple[str, str, str, Callable]] = [
    ("M01", "_below_cut", "boundary comparison < becomes <= (cut falls into the LOWER band)",
     lambda v, c: v <= c),
    ("M02", "_coord_or_none", "missing coordinate silently coerced to 0.0",
     lambda v: 0.0 if v is None else v),
    ("M03", "_distance", "Euclidean displacement replaced by Manhattan",
     lambda dx, dy: abs(dx) + abs(dy)),
    ("M04", "_log_p", "entropy logarithm base 2 replaced by natural log",
     lambda p: math.log(p)),
    ("M05", "_pick_first_state", "first visible scroll state uses max instead of min",
     lambda idxs: max(idxs)),
    ("M06", "_hierarchy_key", "nav_container_depth dropped from the hierarchy key",
     lambda o: (o.get("nav_container_type"), o.get("reveal_direction"), o.get("menu_dependency"))),
    ("M07", "_label_groupable", "missing/empty labels allowed to form collision groups",
     lambda label: True),
    ("M08", "_endpoint_cut", "menu_dependency scans the whole sequence, ignoring the endpoint cut",
     lambda seq: len(seq)),
    ("M09", "_family_denominator", "fixed family n=10 replaced by observed n",
     lambda declared, observed: observed),
    ("M10", "_pick_axes", "x and y axes swapped in zone classification",
     lambda x, y: (y, x)),
]


def run_mutation_tests(baseline: list[dict]) -> list[dict]:
    mod = sys.modules[__name__]
    base_ok = all(f["pass"] for f in baseline)
    out = []
    for mid, target, desc, impl in MUTANTS:
        original = getattr(mod, target)
        setattr(mod, target, impl)
        try:
            try:
                res = run_fixtures()
                failed = [f["fixture"] for f in res if not f["pass"]]
                errored = None
            except Exception as exc:                    # a mutation may crash a fixture
                failed = ["<exception>"]
                errored = "%s: %s" % (type(exc).__name__, exc)
        finally:
            setattr(mod, target, original)
        out.append({
            "mutation_id": mid, "target_primitive": target, "mutation": desc,
            "baseline_all_passed": base_ok,
            "caught": bool(failed),
            "n_fixtures_failed_under_mutation": len(failed),
            "example_failing_fixtures": failed[:4],
            "exception_under_mutation": errored,
        })
    restored = run_fixtures()
    return out, all(f["pass"] for f in restored), len(restored)


# --------------------------------------------------------------------------------------
# 10. Entry point
# --------------------------------------------------------------------------------------

IMPLEMENTED_VARIABLES = [
    {"variable": "entry_x_norm", "status": "IMPLEMENTED", "fn": "normalize_center",
     "caveat": "no clamping; out-of-[0,1] preserved and flagged (AMB-S04)"},
    {"variable": "entry_y_norm", "status": "IMPLEMENTED", "fn": "normalize_center",
     "caveat": "same as entry_x_norm"},
    {"variable": "entry_zone", "status": "IMPLEMENTED_POLICY_REQUIRED",
     "fn": "classify_zone_geometric / validate_categorical",
     "caveat": "derivation refuses to run without an injected ZonePolicy; SSOTV3 freezes none (AMB-S01/02/03). "
               "Collected values are validated and tabulated."},
    {"variable": "entry_control_type", "status": "IMPLEMENTED_VALIDATION_ONLY",
     "fn": "validate_categorical / categorical_distribution",
     "caveat": "collector-coded; Lane S does not assign control types"},
    {"variable": "nav_container_type", "status": "IMPLEMENTED_VALIDATION_ONLY",
     "fn": "validate_categorical / categorical_distribution / reveal_contingency", "caveat": ""},
    {"variable": "reveal_direction", "status": "IMPLEMENTED_VALIDATION_ONLY",
     "fn": "validate_categorical / reveal_contingency",
     "caveat": "no type->direction mapping asserted (AMB-S09)"},
    {"variable": "nav_container_depth", "status": "IMPLEMENTED_EXPLICIT_INPUT_REQUIRED",
     "fn": "recompute_nav_container_depth",
     "caveat": "exposure step index must be supplied; nesting not verified (AMB-S08)"},
    {"variable": "menu_dependency", "status": "IMPLEMENTED",
     "fn": "menu_dependency",
     "caveat": "closed reveal-token set of the three NAMED tokens; sequence_field explicit (AMB-S06/07)"},
    {"variable": "s0_task_control_visible", "status": "IMPLEMENTED_PASSTHROUGH",
     "fn": "s0_task_control_visible", "caveat": "no occlusion arbitration (AMB-S05)"},
    {"variable": "first_visible_scroll_state", "status": "IMPLEMENTED",
     "fn": "first_visible_scroll_state", "caveat": "never-visible -> None, never 'S0'"},
]

DESCRIPTIVE_STATS = [
    {"name": "x/y distribution (05 §2-B)", "fn": "coordinate_summary",
     "denominator": "family n=10 fixed; n_valid/n_missing reported"},
    {"name": "zone distribution + entropy (05 §2-B)", "fn": "categorical_distribution",
     "denominator": "proportions over n_valid AND over n_declared=10"},
    {"name": "service-pair spatial displacement (05 §2-B)", "fn": "pairwise_spatial_displacement",
     "denominator": "n=10; 45 cells reported as matrix coverage only (05 §1)"},
    {"name": "control type distribution (05 §2-D)", "fn": "categorical_distribution", "denominator": "n=10"},
    {"name": "nav container type distribution (05 §2-D)", "fn": "categorical_distribution", "denominator": "n=10"},
    {"name": "reveal direction contingency (05 §2-D)", "fn": "reveal_contingency", "denominator": "n=10"},
    {"name": "nav container depth distribution (05 §2-D)", "fn": "coordinate-free count summary",
     "denominator": "n=10"},
]

NOT_IMPLEMENTED = [
    "entry_zone boundary values — SSOTV3 freezes none; Lane S must not invent them (AMB-S01).",
    "FLOATING / DRAWER derivation — state categories with no geometric rule (AMB-S02).",
    "Any threshold, cut-off, or composite/weighted 'friction' score (05 §3 prohibits it).",
    "Label normalization, synonym mapping, label_relation — Lane L owns 04 §5 (AMB-S13).",
    "Gower / mixed-type distance — 05 §3 allows it only as secondary visualization; not needed pre-freeze.",
    "Any inferential test, effect size, or significance claim — 05 §4 is descriptive.",
    "Any REAL target access, URL fetch, or candidate-list read.",
    "Occlusion arbitration for s0_task_control_visible (AMB-S05).",
    "Nesting verification inside nav_container_depth (AMB-S08).",
    "GO/NO-GO judgement, gold labels, holdout access.",
]

LIMITATION = (
    "MAIN50 measurement data does not exist yet (A freeze pending, REAL unpublished). Every result "
    "in this file comes from synthetic fixtures with pre-planted answers; nothing here is an empirical "
    "finding about any service. The harness has never been executed against a real observation row, so "
    "schema-drift between this implementation and B's emitted columns is unverified. The single largest "
    "blocker is AMB-S01: entry_zone is listed as a Geometry variable but SSOTV3 defines no boundary, so "
    "zone derivation is inoperable until A freezes one or declares entry_zone collector-coded only; the "
    "fixture-only equal-thirds policy exercises mechanics and is not a proposal. Fixture coverage is "
    "structural, not distributional: fixtures confirm the calculators recover planted answers and reject "
    "planted non-cases, but say nothing about behaviour on real coordinate distributions, real Korean "
    "label strings, or real sequence lengths. Mutation testing covers ten single-primitive corruptions; "
    "a mutation the fixtures do not cover would go unnoticed."
)


def main() -> int:
    os.makedirs(OUT_DIR, exist_ok=True)
    fixtures = run_fixtures()
    mutations, restored_ok, restored_n = run_mutation_tests(fixtures)

    pos = [f for f in fixtures if f["kind"] == "positive"]
    neg = [f for f in fixtures if f["kind"] == "negative"]
    pos_pass = sum(1 for f in pos if f["pass"])
    neg_pass = sum(1 for f in neg if f["pass"])
    mut_caught = sum(1 for m in mutations if m["caught"])

    all_green = (pos_pass == len(pos) and neg_pass == len(neg)
                 and mut_caught == len(mutations) and restored_ok)
    verdict = ("READY_WITH_AMBIGUITY" if all_green else "NOT_READY")

    payload = {
        "verdict": verdict,
        "verdict_basis": (
            "All fixtures and all mutations pass, so the implemented calculators are verified; the verdict is "
            "not plain READY because %d definitions the lane was asked to implement are unresolved in SSOTV3, "
            "AMB-S01 (entry_zone has no frozen boundary) being blocking for zone derivation."
            % len(AMBIGUOUS_DEFINITIONS)
        ) if all_green else "One or more fixtures or mutations failed; see fixture_results.",
        "lane": "S — Spatial / Control-form / Menu-Reveal",
        "generated_by": os.path.relpath(os.path.abspath(__file__), RD),
        "base_sha": BASE_SHA,
        "ssot_dir": SSOT_DIR,
        "ssot_manifest_self_sha256": MANIFEST_SELF_SHA256,
        "data_status": "NO_REAL_DATA — MAIN50 not collected; outcome-independent preparation only",
        "codebook_definitions_verbatim": CODEBOOK_VERBATIM,
        "implemented_variables": IMPLEMENTED_VARIABLES,
        "descriptive_statistics": DESCRIPTIVE_STATS,
        "denominator_discipline": {
            "rule": "05 §1/§4 — family n=10 is the fixed denominator; the 45 within-family pairs are "
                    "distance-matrix cells, never n=45.",
            "enforced_by": "_family_denominator(); fixture P-DISP family of 10 -> 45 cells, n=10; "
                           "mutation M09 corrupts it and is caught.",
        },
        "missing_value_policy": {
            "sentinel": "None",
            "rule": "Absence is None and is never coerced to 0, 0.0, False, or ''. Missing never forms a "
                    "detector match, never enters a distribution's valid count, and never shrinks n_declared.",
            "enforced_by": "_coord_or_none(), _label_groupable(); mutations M02 and M07 corrupt these and "
                           "are caught by N-NORM/N-DISP and N-DETB fixtures.",
        },
        "boundary_policy": {
            "rule": "Bands are half-open [prev_cut, cut); a value exactly on a cut falls into the UPPER band.",
            "status": "MECHANISM_ONLY — the cut VALUES are not defined by SSOTV3 (AMB-S01); this rule "
                      "describes tie-handling, not the boundaries themselves.",
            "enforced_by": "_below_cut(); fixtures P-ZONE-BOUND *; mutation M01 flips < to <= and is caught.",
        },
        "zone_policy_used_in_fixtures": FIXTURE_ONLY_ZONE_POLICY.as_dict(),
        "ssot_zone_policy": None,
        "fixture_results": {
            "positive": {"passed": pos_pass, "total": len(pos), "cases": pos},
            "negative": {"passed": neg_pass, "total": len(neg), "cases": neg},
            "mutation": {"caught": mut_caught, "total": len(mutations), "cases": mutations,
                         "restored_after_mutation": restored_ok,
                         "restored_fixture_count": restored_n,
                         "mutation_notes": [
                             "First run of the suite reported positive 35/35, negative 21/21 but mutation "
                             "9/10: M02 ('missing coordinate coerced to 0.0') ESCAPED. Cause was a defect in "
                             "this harness, not in the fixtures — normalize_center() guarded missing inputs "
                             "with early `return`s, so the primitive `_coord_or_none` never saw a None and the "
                             "corruption was unreachable. normalize_center() was restructured to route every "
                             "exit path, missing ones included, through `_coord_or_none`; M02 is now caught. "
                             "This is the concrete payoff of mutation testing here: the pass-only view "
                             "(56/56 fixtures green) would have shipped a dead guard.",
                         ]},
        },
        "ambiguous_definitions": AMBIGUOUS_DEFINITIONS,
        "counterexample_detectors": [
            {
                "id": "CE-A",
                "name": "same_position_different_hierarchy",
                "question": "위치는 같은데 menu hierarchy 가 다른 경우",
                "position_equivalence": "default mode 'zone' = exact equality of the collected categorical "
                                        "entry_zone (introduces no threshold). mode 'coordinate_epsilon' exists "
                                        "but has no default epsilon and refuses to run without one (AMB-S12).",
                "hierarchy_key": ["nav_container_type", "reveal_direction", "nav_container_depth",
                                  "menu_dependency"],
                "output": "pair list of counterexamples AND the same-position/same-hierarchy pairs, so the "
                          "negative side is inspectable; no severity or score attached",
                "verified_by": ["P-DETA same zone, different hierarchy",
                                "P-DETA depth-only difference still detected",
                                "N-DETA same zone, identical hierarchy -> no hit",
                                "N-DETA different zone -> no hit even though hierarchy differs",
                                "N-DETA missing zone never matches missing zone",
                                "N-DETA epsilon mode has no default tolerance",
                                "mutation M06"],
            },
            {
                "id": "CE-B",
                "name": "same_label_different_control_type",
                "question": "visible label 은 같은데 control type 이 다른 경우",
                "interface": "detect_same_label_different_control_type(observations, label_key_fn) — label_key_fn "
                             "is REQUIRED and injected. Lane S ships only identity_label_key (byte-exact, no "
                             "normalization). Lane L's normalizer plugs in unchanged.",
                "lane_s_scope": "control_type divergence side only; Lane S makes no label-equivalence judgement "
                                "(04 §5 belongs to Lane L, AMB-S13)",
                "output": "group list of counterexamples AND same-label/same-type groups; count of rows dropped "
                          "for missing/empty labels",
                "verified_by": ["P-DETB same label, different control type",
                                "N-DETB same label, same control type -> no hit",
                                "N-DETB different labels -> no hit",
                                "N-DETB missing labels never group",
                                "N-DETB empty-string labels never group",
                                "mutation M07"],
            },
        ],
        "limitation": LIMITATION,
        "not_implemented": NOT_IMPLEMENTED,
        "prohibitions_observed": [
            "no new operationalization: every unresolved definition is registered in ambiguous_definitions "
            "rather than filled in",
            "no threshold / cut-off / composite score (05 §3)",
            "no REAL target access, no candidate URL opened",
            "no write outside results/harness/lane_s/ and tools/v3_harness/lane_s_spatial_control_reveal.py",
            "no read or write of other lanes' files",
            "no git add/commit/push",
            "no gold label, no holdout access, no GO/NO-GO",
        ],
    }

    jpath = os.path.join(OUT_DIR, "LANE_S_HARNESS.json")
    with open(jpath, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=2)

    _write_findings(payload, os.path.join(OUT_DIR, "LANE_S_FINDINGS.md"))

    print("verdict=%s positive=%d/%d negative=%d/%d mutation_caught=%d/%d restored=%s"
          % (verdict, pos_pass, len(pos), neg_pass, len(neg), mut_caught, len(mutations), restored_ok))
    print("wrote %s" % jpath)
    return 0 if all_green else 1


def _write_findings(p: dict, path: str) -> None:
    fr = p["fixture_results"]
    L = []
    A = L.append
    A("# Lane S — Spatial / Control-form / Menu·Reveal Harness")
    A("")
    A("- verdict: **%s**" % p["verdict"])
    A("- base SHA: `%s`" % p["base_sha"])
    A("- SSOT: `%s` (MANIFEST self-sha256 `%s`)" % (p["ssot_dir"], p["ssot_manifest_self_sha256"]))
    A("- data status: **%s**" % p["data_status"])
    A("")
    A("## 1. 무엇을 했나")
    A("")
    A("MAIN50 실측이 없으므로 결과 독립적으로, `04_FLOW_CODEBOOK_v3.0.md`가 이미 동결한 정의만 코드로 옮기고")
    A("합성 fixture 로 검산했다. 새 조작화·임계값·합산점수는 만들지 않았고, 정의가 없는 자리는 채우지 않고")
    A("`AMBIGUOUS_DEFINITION` 으로 올렸다.")
    A("")
    A("## 2. 구현한 변수 (%d)" % len(p["implemented_variables"]))
    A("")
    A("| variable | status | caveat |")
    A("|---|---|---|")
    for v in p["implemented_variables"]:
        A("| `%s` | %s | %s |" % (v["variable"], v["status"], v["caveat"] or "—"))
    A("")
    A("## 3. 기술통계")
    A("")
    A("| 통계 | 함수 | 분모 |")
    A("|---|---|---|")
    for s in p["descriptive_statistics"]:
        A("| %s | `%s` | %s |" % (s["name"], s["fn"], s["denominator"]))
    A("")
    A("**분모 규율**: %s" % p["denominator_discipline"]["rule"])
    A("")
    A("## 4. 결측·경계·동점 처리")
    A("")
    A("- 결측 sentinel 은 `None` 이며 **0/0.0/False/'' 로 바꾸지 않는다**. %s"
      % p["missing_value_policy"]["rule"].split(". ", 1)[1])
    A("- 구간은 반열린 `[prev_cut, cut)` 이고 **정확히 경계값에 놓인 좌표는 위쪽 band 로 간다**.")
    A("  단 이는 동점 처리 규칙일 뿐이고, **경계값 자체는 SSOT 에 없다**(AMB-S01).")
    A("- 좌표는 clamp 하지 않는다. `[0,1]` 밖이면 값을 보존하고 `out_of_unit_range` 로 표시한다(AMB-S04).")
    A("- 결측은 detector 매칭을 만들지 않고, 유효 개수에 들어가지 않으며, `n_declared=10` 을 줄이지 않는다.")
    A("")
    A("## 5. Fixture 결과")
    A("")
    A("- positive: **%d/%d**" % (fr["positive"]["passed"], fr["positive"]["total"]))
    A("- negative: **%d/%d**" % (fr["negative"]["passed"], fr["negative"]["total"]))
    A("- mutation caught: **%d/%d** (원복 후 재실행 %d fixture 전부 통과: %s)"
      % (fr["mutation"]["caught"], fr["mutation"]["total"],
         fr["mutation"]["restored_fixture_count"], fr["mutation"]["restored_after_mutation"]))
    A("")
    A("### 변이 검사 상세")
    A("")
    A("| id | 대상 primitive | 고의 결함 | 잡혔나 | 실패 fixture 수 |")
    A("|---|---|---|---|---|")
    for m in fr["mutation"]["cases"]:
        A("| %s | `%s` | %s | %s | %d |"
          % (m["mutation_id"], m["target_primitive"], m["mutation"],
             "yes" if m["caught"] else "**NO**", m["n_fixtures_failed_under_mutation"]))
    A("")
    A("통과만 본 게 아니라, 계산기를 한 군데씩 고의로 틀리게 바꾼 뒤 fixture 가 그걸 잡는지 확인하고 원복했다.")
    A("")
    for note in fr["mutation"].get("mutation_notes", []):
        A("> %s" % note)
    A("")
    A("")
    A("## 6. AMBIGUOUS_DEFINITION (%d)" % len(p["ambiguous_definitions"]))
    A("")
    A("SSOTV3 가 정하지 않아 **내가 채우지 않은** 것들. 소유자가 결정해야 한다.")
    A("")
    for a in p["ambiguous_definitions"]:
        A("### %s — `%s`" % (a["id"], a["variable"]))
        A("")
        A("- 문제: %s" % a["issue"])
        A("- Lane S 처리: %s" % a["lane_s_action"])
        A("- 소유자: %s" % a["owner"])
        A("")
    A("가장 무거운 것은 **AMB-S01** 이다. `entry_zone` 은 04 §4 에서 Geometry categorical 로 선언돼 있지만")
    A("04 §6 은 좌표를 보존하라고만 하고 **x/y 절단값을 하나도 주지 않는다**. SSOTV3 00~15 전체 grep 에서도")
    A("절단값은 나오지 않는다. 따라서 좌표에서 zone 을 유도하는 것은 현재 불가능하고, 이 하네스는 유도를")
    A("거부한다(`UnresolvedDefinition`). fixture 에서 쓴 1/3 등분 정책은 기계 동작 확인용이며 제안이 아니다 —")
    A("`FIXTURE_ONLY_NOT_SSOT` 로 태그돼 있고 fixture 밖에서 쓰면 예외를 던진다.")
    A("")
    A("## 7. 반례 탐지기")
    A("")
    for d in p["counterexample_detectors"]:
        A("### %s `%s`" % (d["id"], d["name"]))
        A("")
        A("- 질문: %s" % d["question"])
        for k in ("position_equivalence", "hierarchy_key", "interface", "lane_s_scope", "output"):
            if k in d:
                val = d[k]
                A("- %s: %s" % (k, ", ".join("`%s`" % x for x in val) if isinstance(val, list) else val))
        A("- 양방향 검증: %s" % ", ".join("`%s`" % v for v in d["verified_by"]))
        A("")
    A("두 탐지기 모두 **탐지돼야 할 것이 탐지되는지**와 **탐지되면 안 되는 것이 안 되는지**를 같이 본다.")
    A("어느 쪽도 심각도·점수·순위를 붙이지 않는다.")
    A("")
    A("## 8. 하지 않은 것")
    A("")
    for n in p["not_implemented"]:
        A("- %s" % n)
    A("")
    A("## 9. Limitation")
    A("")
    A(p["limitation"])
    A("")
    A("## 10. 재현")
    A("")
    A("```bash")
    A("/home/sieg/projects-wsl/ProjectFinal/.venv/bin/python \\")
    A("  %s/tools/v3_harness/lane_s_spatial_control_reveal.py" % RD)
    A("```")
    A("")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(L))


if __name__ == "__main__":
    raise SystemExit(main())
