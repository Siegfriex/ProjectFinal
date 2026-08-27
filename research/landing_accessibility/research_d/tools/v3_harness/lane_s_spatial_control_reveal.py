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
    research_d/results/harness/lane_s/LANE_S_R7_CONVERGENCE.json
    research_d/results/harness/lane_s/LANE_S_R7_FINDINGS.md

R7 convergence (T-A-V3-STEP1-003)
---------------------------------
`entry_zone` derivation used to be REFUSED here: SSOTV3 04 §6 froze no x/y cuts (AMB-S01,
raised as D-V3-FINDING-007). A froze them in ticket T-A-V3-STEP1-003, key
`R7_entry_zone_operational_definition`, with REAL observations still at zero. Section 4b
implements that ruling; section 8b verifies it. The pre-R7 fixture-only equal-thirds policy
is KEPT UNCHANGED as a control group and still refuses to run outside the fixture suite.
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
                 x_center_max: float, source: str, note: str = "",
                 authority_ticket: Any = MISSING, authority_key: Any = MISSING,
                 decided_at_kst: Any = MISSING, preregistration: Any = MISSING,
                 observations_at_decision: Any = MISSING,
                 recorded_in: Any = MISSING, ssot_original_modified: Any = MISSING) -> None:
        if not source:
            raise UnresolvedDefinition("ZonePolicy.source must declare provenance.")
        self.y_top_max = y_top_max
        self.y_mid_max = y_mid_max
        self.x_left_max = x_left_max
        self.x_center_max = x_center_max
        self.source = source
        self.note = note
        # Provenance carried BY the policy object itself, so a policy can never be applied
        # without its origin travelling with it into the emitted JSON.
        self.authority_ticket = authority_ticket
        self.authority_key = authority_key
        self.decided_at_kst = decided_at_kst
        self.preregistration = preregistration
        self.observations_at_decision = observations_at_decision
        self.recorded_in = recorded_in
        self.ssot_original_modified = ssot_original_modified

    def as_dict(self) -> dict:
        return {
            "y_top_max": self.y_top_max, "y_mid_max": self.y_mid_max,
            "x_left_max": self.x_left_max, "x_center_max": self.x_center_max,
            "source": self.source, "note": self.note,
            "boundary_rule": "lower band is half-open [prev, cut); a value exactly on a cut goes to the UPPER band",
            "authority_ticket": self.authority_ticket,
            "authority_key": self.authority_key,
            "decided_at_kst": self.decided_at_kst,
            "preregistration": self.preregistration,
            "observations_at_decision": self.observations_at_decision,
            "recorded_in": self.recorded_in,
            "ssot_original_modified": self.ssot_original_modified,
        }


FIXTURE_ONLY_ZONE_POLICY = ZonePolicy(
    y_top_max=1.0 / 3.0, y_mid_max=2.0 / 3.0, x_left_max=1.0 / 3.0, x_center_max=2.0 / 3.0,
    source="FIXTURE_ONLY_NOT_SSOT",
    note="Equal thirds. Chosen ONLY to exercise classifier mechanics on synthetic fixtures. "
         "This is NOT an SSOT boundary and must never be used to code real observations.",
)

SSOT_ZONE_POLICY = None  # intentionally absent: SSOTV3 freezes no boundaries (AMB-S01).

# --------------------------------------------------------------------------------------
# 4b. R7 — the A-frozen entry_zone operational definition (T-A-V3-STEP1-003)
#
# AMB-S01/S02/S03 asked A to freeze the zone boundaries or declare entry_zone collector-
# coded only. A froze them, in ticket T-A-V3-STEP1-003, key
# `R7_entry_zone_operational_definition`, WHILE REAL OBSERVATIONS WERE STILL AT ZERO.
# The section below implements that ruling and nothing else. The fixture-only equal-thirds
# policy above is deliberately KEPT, unchanged, as a control group.
# --------------------------------------------------------------------------------------

R7_TICKET_PATH = "/home/sieg/projects-wsl/ProjectFinal/.agent_bus/landing_v2/tickets/T-A-V3-STEP1-003.json"
R7_TICKET_KEY = "R7_entry_zone_operational_definition"
R7_TICKET_SHA256_AT_TRANSCRIPTION = "ea09d3985c71a52b779253bc7c9a6336d5926038c9a83d2c2759264f46e9878d"
R7_DECIDED_AT_KST = "2026-08-28T02:58:00+09:00"          # ticket.created_at_kst
R7_PREREGISTRATION = (
    "관측 0건 상태에서 사전등록됨 — ticket.preregistration_status: "
    "'REAL 접속 누적 0건. 어떤 flow 도 관측되지 않았다. 따라서 이 확정들은 전부 result-blind 다.'"
)
R7_RECORDED_IN = "V3_0_1_SUCCESSOR_DELTA.md Δ8 (SSOTV3 원본은 수정하지 않는다)"

R7_VERBATIM: dict[str, str] = {
    'raised_by':
        'D-V3-FINDING-007 (P1, blocking) — C 독립 확인: SSOTV3 전체 grep 에서 entry_zone 은 값 열거뿐이고 x/y 절단값·임계값 문자열 0건',
    'is_it_blocking':
        "**수집에는 blocking 이 아니다.** 04 §6 이 'Normalized center (x,y) 를 보존하고 zone 은 요약값으로만 쓴다. 좌표 원자료를 버리지 않는다'고 이미 정했다. 원좌표가 남으면 zone 은 언제든 재도출 가능하며 재수집이 필요 없다",
    'ruling':
        '수집은 진행한다. entry_x_norm · entry_y_norm 을 **항상** 저장한다. zone 임계값은 관측 0건인 지금 확정한다 — 나중에 정하면 데이터에 맞춘 것이 된다',
    'thresholds.y_bands':
        'y < 1/3 → TOP · 1/3 ≤ y < 2/3 → MID · y ≥ 2/3 → BOTTOM',
    'thresholds.x_within_TOP':
        'x < 1/3 → TOP_LEFT · 1/3 ≤ x < 2/3 → TOP_CENTER · x ≥ 2/3 → TOP_RIGHT',
    'thresholds.MID_BOTTOM':
        'x 삼등분을 적용하지 않는다. MID · BOTTOM 그대로 둔다 — 04 codebook 의 값 목록에 MID_LEFT 류가 없다',
    'thresholds.coordinate_basis':
        'control bbox 중심을 viewport(390×844 CSS px)로 정규화. scroll 상태와 무관하게 **그 state 의 viewport 기준**이다',
    'structural_overrides.precedence':
        'FLOATING 과 DRAWER 는 기하보다 **우선한다**. 구조적 값이지 위치값이 아니기 때문이다',
    'structural_overrides.FLOATING':
        'computed position 이 fixed 또는 sticky 이고 일반 흐름에서 벗어나 viewport 에 고정된 경우',
    'structural_overrides.DRAWER':
        'control 이 reveal 을 요구하는 nav_container 안에 있는 경우 (menu_dependency=1 을 만든 그 container)',
    'structural_overrides.both':
        '둘 다 해당하면 DRAWER 가 우선한다 — reveal 필요 여부가 사용자에게 더 큰 구조적 부담이다',
    'structural_overrides.record_anyway':
        'override 가 적용돼도 entry_x_norm/entry_y_norm 은 그대로 저장한다. 요약값이 원자료를 덮지 않는다',
    'boundary_rule':
        '경계값은 하한 포함·상한 배제(`[a, b)`)로 통일한다. 정확히 1/3 인 점은 TOP 이자 TOP_CENTER 다',
    'later_changes':
        'zone 은 파생값이므로 임계값을 나중에 바꾸는 것은 재수집이 아니라 재도출이다. 그러나 **선언된 민감도로만 허용한다** — 결과를 보고 조용히 바꾸면 그것이 조작화 fitting 이다. 원 임계값 결과와 병기해야 한다',
    'D_and_C_note':
        "D 의 lane S 와 C 의 lane6 이 각자 잠정 임계값을 두고 있었다. 이제 둘 다 이 정의로 수렴한다. C 가 '잠정 선택(SSOT 아님)'으로 표기하고 A 결정 전 primary 로 쓰지 않은 처리가 옳다",
}


def verify_r7_transcription() -> dict:
    """Re-read the authority file and confirm R7_VERBATIM is a byte-exact transcription.

    A transcription that has silently drifted from the ticket would let this lane converge
    on the wrong definition while claiming the ticket as its source. This check makes that
    failure loud instead of invisible.
    """
    out = {"ticket_path": R7_TICKET_PATH, "ticket_key": R7_TICKET_KEY,
           "ticket_file_present": False, "ticket_sha256": MISSING,
           "sha256_matches_transcription_time": MISSING,
           "verbatim_match": MISSING, "mismatched_keys": [], "missing_keys": [], "extra_keys": []}
    try:
        with open(R7_TICKET_PATH, "rb") as fh:
            raw = fh.read()
    except OSError as exc:
        out["read_error"] = "%s: %s" % (type(exc).__name__, exc)
        return out
    out["ticket_file_present"] = True
    out["ticket_sha256"] = hashlib.sha256(raw).hexdigest()
    out["sha256_matches_transcription_time"] = (
        out["ticket_sha256"] == R7_TICKET_SHA256_AT_TRANSCRIPTION)
    try:
        node = json.loads(raw.decode("utf-8"))[R7_TICKET_KEY]
    except (ValueError, KeyError) as exc:
        out["read_error"] = "%s: %s" % (type(exc).__name__, exc)
        return out
    flat: dict[str, Any] = {}

    def _walk(prefix: str, n: Any) -> None:
        if isinstance(n, dict):
            for k, v in n.items():
                _walk(prefix + "." + k if prefix else k, v)
        else:
            flat[prefix] = n

    _walk("", node)
    out["missing_keys"] = sorted(set(flat) - set(R7_VERBATIM))
    out["extra_keys"] = sorted(set(R7_VERBATIM) - set(flat))
    out["mismatched_keys"] = sorted(k for k in set(flat) & set(R7_VERBATIM)
                                    if flat[k] != R7_VERBATIM[k])
    out["verbatim_match"] = not (out["missing_keys"] or out["extra_keys"]
                                 or out["mismatched_keys"])
    return out


R7_ZONE_POLICY = ZonePolicy(
    y_top_max=1.0 / 3.0, y_mid_max=2.0 / 3.0, x_left_max=1.0 / 3.0, x_center_max=2.0 / 3.0,
    source="T-A-V3-STEP1-003 R7",
    note="A-frozen. y bands 1/3·2/3; x thirds INSIDE the TOP band only; MID/BOTTOM are not "
         "split on x. Structural overrides DRAWER > FLOATING > geometry. Raw entry_x_norm / "
         "entry_y_norm are stored even when an override applies.",
    authority_ticket="T-A-V3-STEP1-003",
    authority_key=R7_TICKET_KEY,
    decided_at_kst=R7_DECIDED_AT_KST,
    preregistration=R7_PREREGISTRATION,
    observations_at_decision=0,
    recorded_in=R7_RECORDED_IN,
    ssot_original_modified=False,
)

# The R7 policy is an authority, but it is NOT in the SSOTV3 originals — it lives in the
# successor delta. Keeping these two names distinct preserves that difference.
SSOT_ZONE_POLICY_R7 = None          # SSOTV3 04 §6 still carries no cut values.
AUTHORITATIVE_ZONE_POLICY = R7_ZONE_POLICY

# R7 zone result statuses. None of these are entry_zone VALUES — they qualify the result.
R7_OK = "OK"
R7_OK_UNCONSULTED_AXIS_OUT_OF_RANGE = "OK_UNCONSULTED_AXIS_OUT_OF_RANGE"
R7_MISSING_COORDINATES = "MISSING_COORDINATES"
R7_AMBIGUOUS_OUT_OF_UNIT_RANGE = "AMBIGUOUS_OUT_OF_UNIT_RANGE"
R7_AMBIGUOUS_FLOATING_UNDETERMINED = "AMBIGUOUS_FLOATING_UNDETERMINED"
R7_AMBIGUOUS_DRAWER_UNDETERMINED = "AMBIGUOUS_DRAWER_UNDETERMINED"

R7_AMBIGUOUS_STATUSES = (R7_AMBIGUOUS_OUT_OF_UNIT_RANGE,
                         R7_AMBIGUOUS_FLOATING_UNDETERMINED,
                         R7_AMBIGUOUS_DRAWER_UNDETERMINED)


# ---- R7 primitives. One concept per function, so a mutation is attributable. -----------

def _r7_cuts(policy: ZonePolicy) -> tuple[float, float, float, float]:
    """(y_top_max, y_mid_max, x_left_max, x_center_max) as R7 froze them."""
    return (policy.y_top_max, policy.y_mid_max, policy.x_left_max, policy.x_center_max)


def _r7_band_test(value: float, cut: float) -> bool:
    """R7 boundary_rule: 하한 포함·상한 배제 `[a, b)`. A value ON a cut belongs UPWARD."""
    return value < cut


def _r7_pick_axes(x: float, y: float) -> tuple[float, float]:
    return (x, y)


def _r7_x_split_applies(y_band: str) -> bool:
    """R7 thresholds.MID_BOTTOM: the x thirds apply INSIDE the TOP band only."""
    return y_band == "TOP"


def _r7_range_ok(value: float) -> bool:
    """R7 regulates [0,1]. It says nothing about values outside it (AMB-S04 / AMB-S17)."""
    return 0.0 <= value <= 1.0


def _r7_precedence_order() -> tuple[str, ...]:
    """R7 structural_overrides: FLOATING/DRAWER beat geometry; DRAWER beats FLOATING."""
    return ("DRAWER", "FLOATING")


def _r7_truth(value: Any) -> Any:
    """Accept the two spellings of the same boolean and NOTHING else.

    R7 writes the DRAWER condition as `menu_dependency=1` while 04 §4 types the field as
    bool, so both `True` and `1` have to be read as the same observation. Every other
    value — including truthy ones like `2` or `"1"` — stays MISSING rather than being
    coerced, so a malformed input surfaces as AMBIGUOUS instead of as a confident answer.
    """
    if isinstance(value, bool):
        return value
    if isinstance(value, int) and value in (0, 1):
        return bool(value)
    return MISSING


def r7_y_band(y: float, policy: ZonePolicy = R7_ZONE_POLICY) -> str:
    y_top, y_mid, _, _ = _r7_cuts(policy)
    if _r7_band_test(y, y_top):
        return "TOP"
    if _r7_band_test(y, y_mid):
        return "MID"
    return "BOTTOM"


def r7_top_x_zone(x: float, policy: ZonePolicy = R7_ZONE_POLICY) -> str:
    _, _, x_left, x_center = _r7_cuts(policy)
    if _r7_band_test(x, x_left):
        return "TOP_LEFT"
    if _r7_band_test(x, x_center):
        return "TOP_CENTER"
    return "TOP_RIGHT"


def r7_structural_override(*, computed_position: Any = MISSING,
                           out_of_flow_fixed_to_viewport: Any = MISSING,
                           in_reveal_required_nav_container: Any = MISSING,
                           menu_dependency: Any = MISSING) -> dict:
    """Evaluate the two structural values R7 places ABOVE geometry.

    DRAWER  — `control 이 reveal 을 요구하는 nav_container 안에 있는 경우
               (menu_dependency=1 을 만든 그 container)`
    FLOATING — `computed position 이 fixed 또는 sticky 이고 일반 흐름에서 벗어나
               viewport 에 고정된 경우`

    R7 states FLOATING as a conjunction of two clauses. Whether the second clause is an
    independent observable or a restatement of the first is not settled (AMB-S15), so this
    function requires it and returns UNDETERMINED rather than choosing a reading.
    """
    notes: list[str] = []
    in_reveal_required_nav_container = _r7_truth(in_reveal_required_nav_container)
    menu_dependency = _r7_truth(menu_dependency)
    out_of_flow_fixed_to_viewport = _r7_truth(out_of_flow_fixed_to_viewport)

    # --- DRAWER ---
    drawer: Any = MISSING
    if in_reveal_required_nav_container is True:
        if menu_dependency is True:
            drawer = True
        elif menu_dependency is False:
            drawer = MISSING
            notes.append(
                "in_reveal_required_nav_container=True but menu_dependency=False. R7 identifies the "
                "DRAWER container as 'menu_dependency=1 을 만든 그 container'; with menu_dependency=0 "
                "no such container exists. Inputs are inconsistent — not resolved here (AMB-S16).")
        else:
            drawer = MISSING
            notes.append("menu_dependency unknown; DRAWER cannot be confirmed (AMB-S16).")
    elif in_reveal_required_nav_container is False:
        drawer = False
    else:
        notes.append("in_reveal_required_nav_container unknown; DRAWER undetermined.")

    # --- FLOATING ---
    floating: Any = MISSING
    pos_hit = computed_position in ("fixed", "sticky")
    if computed_position is MISSING:
        notes.append("computed_position unknown; FLOATING undetermined.")
    elif not pos_hit:
        floating = False
    else:
        if out_of_flow_fixed_to_viewport is True:
            floating = True
        elif out_of_flow_fixed_to_viewport is False:
            floating = False
        else:
            floating = MISSING
            notes.append(
                "computed_position=%r satisfies R7's first FLOATING clause but "
                "'일반 흐름에서 벗어나 viewport 에 고정된' is unobserved; FLOATING undetermined "
                "(AMB-S15)." % (computed_position,))

    order = _r7_precedence_order()
    applied: Any = MISSING
    status = R7_OK
    flags = {"DRAWER": drawer, "FLOATING": floating}
    # `live` = there IS positive evidence pointing at this override, but the second half of
    # R7's condition is unobserved, so it can neither be confirmed nor ruled out.
    live = {"DRAWER": (drawer is MISSING and in_reveal_required_nav_container is True),
            "FLOATING": (floating is MISSING and pos_hit)}
    undetermined_status = {"DRAWER": R7_AMBIGUOUS_DRAWER_UNDETERMINED,
                           "FLOATING": R7_AMBIGUOUS_FLOATING_UNDETERMINED}
    # Walk the precedence chain in order and STOP at the first rung that is either
    # confirmed or unresolvable. A confirmed FLOATING must not overtake an unresolved
    # DRAWER: R7 ranks DRAWER above FLOATING, so while DRAWER is open the answer is not
    # yet known to be FLOATING. Falling through to the lower rung would be this lane
    # resolving R7's precedence with a guess.
    for name in order:
        if flags.get(name) is True:
            applied = name
            break
        if live.get(name):
            status = undetermined_status[name]
            notes.append(
                "%s outranks the remaining candidates under R7 and is unresolved, so no lower "
                "value may be returned yet (drawer=%r, floating=%r)." % (name, drawer, floating))
            break
    return {"override": applied, "status": status, "precedence_order": list(order),
            "drawer": drawer, "floating": floating,
            "blocked_by_higher_precedence_unknown": status in R7_AMBIGUOUS_STATUSES,
            "structural_inputs_observed": {
                "computed_position": computed_position is not MISSING,
                "out_of_flow_fixed_to_viewport": out_of_flow_fixed_to_viewport is not MISSING,
                "in_reveal_required_nav_container": in_reveal_required_nav_container is not MISSING,
                "menu_dependency": menu_dependency is not MISSING},
            "notes": notes}


def classify_zone_r7(x_norm: Any, y_norm: Any, *,
                     computed_position: Any = MISSING,
                     out_of_flow_fixed_to_viewport: Any = MISSING,
                     in_reveal_required_nav_container: Any = MISSING,
                     menu_dependency: Any = MISSING,
                     policy: ZonePolicy = R7_ZONE_POLICY) -> dict:
    """entry_zone per T-A-V3-STEP1-003 R7. Returns a RESULT, not a bare string.

    Order of resolution, per R7 `structural_overrides.precedence`:
        1. DRAWER   (beats FLOATING per `structural_overrides.both`)
        2. FLOATING
        3. geometry (y bands; x thirds inside TOP only)

    `entry_x_norm` / `entry_y_norm` are echoed back UNCHANGED in every branch, including
    the override branches — R7 `record_anyway`: 요약값이 원자료를 덮지 않는다.
    """
    res: dict[str, Any] = {
        "entry_zone": MISSING,
        "status": R7_OK,
        "basis": MISSING,
        "entry_x_norm": x_norm,          # record_anyway
        "entry_y_norm": y_norm,          # record_anyway
        "consulted_axes": [],
        "policy_source": policy.source,
        "notes": [],
    }

    ov = r7_structural_override(
        computed_position=computed_position,
        out_of_flow_fixed_to_viewport=out_of_flow_fixed_to_viewport,
        in_reveal_required_nav_container=in_reveal_required_nav_container,
        menu_dependency=menu_dependency)
    res["override_eval"] = ov
    res["notes"].extend(ov["notes"])

    if ov["override"] is not MISSING:
        res["entry_zone"] = ov["override"]
        res["basis"] = "STRUCTURAL_OVERRIDE"
        return res
    if ov["status"] in R7_AMBIGUOUS_STATUSES:
        res["status"] = ov["status"]
        res["basis"] = "STRUCTURAL_OVERRIDE_UNDETERMINED"
        return res

    if x_norm is MISSING or y_norm is MISSING:
        res["status"] = R7_MISSING_COORDINATES
        res["basis"] = "GEOMETRY"
        return res

    x, y = _r7_pick_axes(float(x_norm), float(y_norm))
    res["basis"] = "GEOMETRY"

    if not _r7_range_ok(y):
        res["status"] = R7_AMBIGUOUS_OUT_OF_UNIT_RANGE
        res["consulted_axes"] = ["y"]
        res["notes"].append(
            "y=%r is outside [0,1]. R7 gives cut values but does not regulate out-of-unit "
            "coordinates; not resolved here (AMB-S17)." % (y,))
        return res

    band = r7_y_band(y, policy)
    res["consulted_axes"] = ["y"]
    if not _r7_x_split_applies(band):
        res["entry_zone"] = band
        if not _r7_range_ok(x):
            res["status"] = R7_OK_UNCONSULTED_AXIS_OUT_OF_RANGE
            res["notes"].append(
                "x=%r is outside [0,1] but R7 does not consult x in the %s band, so the zone "
                "is unaffected. Flagged, not silently dropped." % (x, band))
        return res

    res["consulted_axes"] = ["y", "x"]
    if not _r7_range_ok(x):
        res["entry_zone"] = MISSING
        res["status"] = R7_AMBIGUOUS_OUT_OF_UNIT_RANGE
        res["notes"].append(
            "x=%r is outside [0,1] and the TOP band DOES consult x. R7 does not regulate "
            "out-of-unit coordinates; not resolved here (AMB-S17)." % (x,))
        return res
    res["entry_zone"] = r7_top_x_zone(x, policy)
    return res


def r7_zone(x_norm: Any, y_norm: Any, **kw: Any) -> Any:
    """Thin accessor: the zone string, or None when R7 does not settle it."""
    return classify_zone_r7(x_norm, y_norm, **kw)["entry_zone"]



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
    "entry_zone boundary values as an invention of this lane — SSOTV3 freezes none, and the cuts now "
    "used come from T-A-V3-STEP1-003 R7, not from Lane S (AMB-S01 resolved; see r7_convergence).",
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




# --------------------------------------------------------------------------------------
# 8b. R7 convergence fixtures — boundaries, precedence, policy contrast, mutation
# --------------------------------------------------------------------------------------

THIRD = 1.0 / 3.0
TWO_THIRDS = 2.0 / 3.0


def _r7_case(name: str, kind: str, got: Any, expected: Any, notes: str = "") -> dict:
    return _check(name, kind, got, expected, notes)


def _zs(res: dict) -> tuple:
    """(entry_zone, status) — the pair every R7 fixture asserts on."""
    return (res["entry_zone"], res["status"])


def run_r7_boundary_fixtures() -> list[dict]:
    """Every cut named by R7, hit EXACTLY, plus the neighbours on either side of it.

    R7 boundary_rule: `경계값은 하한 포함·상한 배제([a, b))로 통일한다.`
    Under that rule, and under the inequality tables R7 writes out
    (`1/3 ≤ y < 2/3 → MID`), a coordinate sitting exactly on a cut belongs to the UPPER
    band. The same sentence then adds `정확히 1/3 인 점은 TOP 이자 TOP_CENTER 다`, which
    contradicts its own y table. See AMB-S14; both readings are reported.
    """
    r: list[dict] = []
    K = "r7_boundary"
    below = lambda v: math.nextafter(v, 0.0)
    above = lambda v: math.nextafter(v, 1.0)

    # --- y cuts, hit exactly (x held inside the LEFT third so the answer is unambiguous)
    r.append(_r7_case("R7-B y=1/3 EXACT (x=0.10)", K, _zs(classify_zone_r7(0.10, THIRD)),
                      ("MID", R7_OK),
                      "R7 thresholds.y_bands `1/3 ≤ y < 2/3 → MID` + boundary_rule `[a, b)`. "
                      "R7's own example clause would say TOP_LEFT here — AMB-S14."))
    r.append(_r7_case("R7-B y=2/3 EXACT (x=0.10)", K, _zs(classify_zone_r7(0.10, TWO_THIRDS)),
                      ("BOTTOM", R7_OK), "`y ≥ 2/3 → BOTTOM`"))
    r.append(_r7_case("R7-B y just below 1/3", K, _zs(classify_zone_r7(0.10, below(THIRD))),
                      ("TOP_LEFT", R7_OK), "`y < 1/3 → TOP`"))
    r.append(_r7_case("R7-B y just above 1/3", K, _zs(classify_zone_r7(0.10, above(THIRD))),
                      ("MID", R7_OK)))
    r.append(_r7_case("R7-B y just below 2/3", K, _zs(classify_zone_r7(0.10, below(TWO_THIRDS))),
                      ("MID", R7_OK)))
    r.append(_r7_case("R7-B y just above 2/3", K, _zs(classify_zone_r7(0.10, above(TWO_THIRDS))),
                      ("BOTTOM", R7_OK)))

    # --- x cuts, hit exactly, INSIDE the TOP band (the only band that consults x)
    r.append(_r7_case("R7-B x=1/3 EXACT (y=0.10, TOP band)", K, _zs(classify_zone_r7(THIRD, 0.10)),
                      ("TOP_CENTER", R7_OK),
                      "`1/3 ≤ x < 2/3 → TOP_CENTER`. Here the inequality table and R7's example "
                      "clause AGREE."))
    r.append(_r7_case("R7-B x=2/3 EXACT (y=0.10, TOP band)", K,
                      _zs(classify_zone_r7(TWO_THIRDS, 0.10)), ("TOP_RIGHT", R7_OK),
                      "`x ≥ 2/3 → TOP_RIGHT`"))
    r.append(_r7_case("R7-B x just below 1/3", K, _zs(classify_zone_r7(below(THIRD), 0.10)),
                      ("TOP_LEFT", R7_OK)))
    r.append(_r7_case("R7-B x just above 1/3", K, _zs(classify_zone_r7(above(THIRD), 0.10)),
                      ("TOP_CENTER", R7_OK)))
    r.append(_r7_case("R7-B x just below 2/3", K, _zs(classify_zone_r7(below(TWO_THIRDS), 0.10)),
                      ("TOP_CENTER", R7_OK)))
    r.append(_r7_case("R7-B x just above 2/3", K, _zs(classify_zone_r7(above(TWO_THIRDS), 0.10)),
                      ("TOP_RIGHT", R7_OK)))

    # --- x cuts hit exactly OUTSIDE the TOP band: R7 says x is not consulted at all
    r.append(_r7_case("R7-B x=1/3 EXACT in MID band -> plain MID", K,
                      _zs(classify_zone_r7(THIRD, 0.50)), ("MID", R7_OK),
                      "R7 thresholds.MID_BOTTOM: `x 삼등분을 적용하지 않는다`. MID_CENTER does not exist."))
    r.append(_r7_case("R7-B x=2/3 EXACT in BOTTOM band -> plain BOTTOM", K,
                      _zs(classify_zone_r7(TWO_THIRDS, 0.90)), ("BOTTOM", R7_OK)))
    r.append(_r7_case("R7-B the exact point (1/3, 1/3)", K, _zs(classify_zone_r7(THIRD, THIRD)),
                      ("MID", R7_OK),
                      "The point R7's example clause names. Inequality table -> MID; example "
                      "clause -> TOP_CENTER. AMB-S14."))

    # --- unit-square corners
    r.append(_r7_case("R7-B corner (0.0, 0.0)", K, _zs(classify_zone_r7(0.0, 0.0)),
                      ("TOP_LEFT", R7_OK)))
    r.append(_r7_case("R7-B corner (1.0, 0.0)", K, _zs(classify_zone_r7(1.0, 0.0)),
                      ("TOP_RIGHT", R7_OK)))
    r.append(_r7_case("R7-B corner (0.0, 1.0)", K, _zs(classify_zone_r7(0.0, 1.0)),
                      ("BOTTOM", R7_OK), "x is not consulted in BOTTOM"))
    r.append(_r7_case("R7-B corner (1.0, 1.0)", K, _zs(classify_zone_r7(1.0, 1.0)),
                      ("BOTTOM", R7_OK)))

    # --- outside [0,1]: R7 gives cuts but never regulates out-of-unit coordinates
    for x, y, label in ((-0.001, 0.10, "x slightly negative, TOP band"),
                        (1.001, 0.10, "x slightly >1, TOP band"),
                        (-5.0, 0.10, "x far negative, TOP band")):
        r.append(_r7_case("R7-B out-of-range %s" % label, K, _zs(classify_zone_r7(x, y)),
                          (MISSING, R7_AMBIGUOUS_OUT_OF_UNIT_RANGE),
                          "x IS consulted in TOP; R7 does not define out-of-unit behaviour "
                          "(AMB-S17). Not filled in here."))
    for x, y, label in ((0.10, -0.001, "y slightly negative"),
                        (0.10, 1.001, "y slightly >1"),
                        (0.10, 9.9, "y far above 1")):
        r.append(_r7_case("R7-B out-of-range %s" % label, K, _zs(classify_zone_r7(x, y)),
                          (MISSING, R7_AMBIGUOUS_OUT_OF_UNIT_RANGE),
                          "y is consulted in every band (AMB-S17)."))
    r.append(_r7_case("R7-B out-of-range x, MID band (x never consulted)", K,
                      _zs(classify_zone_r7(1.4, 0.50)),
                      ("MID", R7_OK_UNCONSULTED_AXIS_OUT_OF_RANGE),
                      "The out-of-unit axis is not read by R7 in this band, so the zone stands; "
                      "the fact is flagged rather than dropped."))
    r.append(_r7_case("R7-B out-of-range x, BOTTOM band (x never consulted)", K,
                      _zs(classify_zone_r7(-2.0, 0.90)),
                      ("BOTTOM", R7_OK_UNCONSULTED_AXIS_OUT_OF_RANGE)))

    # --- missing coordinates never become a zone and never become 0.0
    r.append(_r7_case("R7-B both coordinates MISSING", K, _zs(classify_zone_r7(MISSING, MISSING)),
                      (MISSING, R7_MISSING_COORDINATES)))
    r.append(_r7_case("R7-B x MISSING only", K, _zs(classify_zone_r7(MISSING, 0.10)),
                      (MISSING, R7_MISSING_COORDINATES)))
    r.append(_r7_case("R7-B y MISSING only", K, _zs(classify_zone_r7(0.10, MISSING)),
                      (MISSING, R7_MISSING_COORDINATES)))

    # --- record_anyway: raw coordinates survive verbatim on EVERY path
    for x, y, tag in ((0.10, 0.10, "plain geometry"), (1.4, 0.50, "unconsulted out-of-range"),
                      (-0.001, 0.10, "ambiguous out-of-range"), (MISSING, MISSING, "missing")):
        res = classify_zone_r7(x, y)
        r.append(_r7_case("R7-B record_anyway raw coords preserved (%s)" % tag, K,
                          (res["entry_x_norm"], res["entry_y_norm"]), (x, y),
                          "R7 record_anyway: 요약값이 원자료를 덮지 않는다"))

    # --- the y band never produces an x-split label, in either direction
    grid_zones = {classify_zone_r7(i / 50.0, j / 50.0)["entry_zone"]
                  for i in range(51) for j in range(51)}
    r.append(_r7_case("R7-B MID/BOTTOM never gain an x split", K,
                      sorted(str(z) for z in grid_zones),
                      ["BOTTOM", "MID", "TOP_CENTER", "TOP_LEFT", "TOP_RIGHT"],
                      "51x51 sweep of the unit square emits exactly the 5 geometric labels"))
    r.append(_r7_case("R7-B geometry alone never emits FLOATING/DRAWER", K,
                      sorted(z for z in grid_zones if z in ENTRY_ZONE_STATE_SUBSET), []))
    r.append(_r7_case("R7-B every emitted label is in the 04 §4 enum", K,
                      sorted({validate_categorical(z, ENTRY_ZONE_ENUM)["status"]
                              for z in grid_zones}), ["VALID"]))
    return r


def run_r7_precedence_fixtures() -> list[dict]:
    """R7 structural_overrides: DRAWER > FLOATING > geometry, verified BOTH directions."""
    r: list[dict] = []
    K = "r7_precedence"
    TL = dict(x_norm=0.10, y_norm=0.10)        # geometry would say TOP_LEFT
    BR = dict(x_norm=0.90, y_norm=0.90)        # geometry would say BOTTOM
    FLOAT_ON = dict(computed_position="fixed", out_of_flow_fixed_to_viewport=True)
    STICKY_ON = dict(computed_position="sticky", out_of_flow_fixed_to_viewport=True)
    FLOAT_OFF = dict(computed_position="static", out_of_flow_fixed_to_viewport=False)
    DRAWER_ON = dict(in_reveal_required_nav_container=True, menu_dependency=True)
    DRAWER_OFF = dict(in_reveal_required_nav_container=False, menu_dependency=False)

    # --- control: no override -> geometry answers
    r.append(_r7_case("R7-P no override -> geometry TOP_LEFT", K,
                      _zs(classify_zone_r7(**TL, **FLOAT_OFF, **DRAWER_OFF)),
                      ("TOP_LEFT", R7_OK)))
    r.append(_r7_case("R7-P no override -> geometry BOTTOM", K,
                      _zs(classify_zone_r7(**BR, **FLOAT_OFF, **DRAWER_OFF)),
                      ("BOTTOM", R7_OK)))

    # --- FLOATING beats geometry, from BOTH geometric starting points
    r.append(_r7_case("R7-P geometry TOP_LEFT + FLOATING(fixed) -> FLOATING", K,
                      _zs(classify_zone_r7(**TL, **FLOAT_ON, **DRAWER_OFF)),
                      ("FLOATING", R7_OK), "`FLOATING 과 DRAWER 는 기하보다 우선한다`"))
    r.append(_r7_case("R7-P geometry BOTTOM + FLOATING(sticky) -> FLOATING", K,
                      _zs(classify_zone_r7(**BR, **STICKY_ON, **DRAWER_OFF)),
                      ("FLOATING", R7_OK)))

    # --- DRAWER beats geometry, from BOTH geometric starting points
    r.append(_r7_case("R7-P geometry TOP_LEFT + DRAWER -> DRAWER", K,
                      _zs(classify_zone_r7(**TL, **FLOAT_OFF, **DRAWER_ON)),
                      ("DRAWER", R7_OK)))
    r.append(_r7_case("R7-P geometry BOTTOM + DRAWER -> DRAWER", K,
                      _zs(classify_zone_r7(**BR, **FLOAT_OFF, **DRAWER_ON)),
                      ("DRAWER", R7_OK)))

    # --- both fire: DRAWER wins (R7 structural_overrides.both)
    r.append(_r7_case("R7-P FLOATING and DRAWER both -> DRAWER (TOP geometry)", K,
                      _zs(classify_zone_r7(**TL, **FLOAT_ON, **DRAWER_ON)),
                      ("DRAWER", R7_OK), "`둘 다 해당하면 DRAWER 가 우선한다`"))
    r.append(_r7_case("R7-P FLOATING and DRAWER both -> DRAWER (BOTTOM geometry)", K,
                      _zs(classify_zone_r7(**BR, **STICKY_ON, **DRAWER_ON)),
                      ("DRAWER", R7_OK)))
    r.append(_r7_case("R7-P precedence order is literally DRAWER before FLOATING", K,
                      classify_zone_r7(**TL, **FLOAT_ON, **DRAWER_ON)["override_eval"]
                      ["precedence_order"], ["DRAWER", "FLOATING"]))

    # --- reverse direction: an override must NOT fire when its condition is absent
    r.append(_r7_case("R7-P position static -> not FLOATING", K,
                      _zs(classify_zone_r7(**TL, computed_position="static",
                                           out_of_flow_fixed_to_viewport=True, **DRAWER_OFF)),
                      ("TOP_LEFT", R7_OK),
                      "R7's first FLOATING clause fails, so the second cannot carry it alone"))
    r.append(_r7_case("R7-P position relative -> not FLOATING", K,
                      _zs(classify_zone_r7(**TL, computed_position="relative",
                                           out_of_flow_fixed_to_viewport=False, **DRAWER_OFF)),
                      ("TOP_LEFT", R7_OK)))
    r.append(_r7_case("R7-P sticky but NOT fixed to viewport -> not FLOATING", K,
                      _zs(classify_zone_r7(**TL, computed_position="sticky",
                                           out_of_flow_fixed_to_viewport=False, **DRAWER_OFF)),
                      ("TOP_LEFT", R7_OK), "R7 states FLOATING as a conjunction"))
    r.append(_r7_case("R7-P container present but no reveal required -> not DRAWER", K,
                      _zs(classify_zone_r7(**TL, **FLOAT_OFF,
                                           in_reveal_required_nav_container=False,
                                           menu_dependency=True)),
                      ("TOP_LEFT", R7_OK)))

    # --- the second FLOATING clause is unobserved -> R7 is not completed by this lane
    r.append(_r7_case("R7-P sticky, flow-clause UNKNOWN -> undetermined not guessed", K,
                      _zs(classify_zone_r7(**TL, computed_position="sticky", **DRAWER_OFF)),
                      (MISSING, R7_AMBIGUOUS_FLOATING_UNDETERMINED), "AMB-S15"))
    r.append(_r7_case("R7-P fixed, flow-clause UNKNOWN -> undetermined not guessed", K,
                      _zs(classify_zone_r7(**TL, computed_position="fixed", **DRAWER_OFF)),
                      (MISSING, R7_AMBIGUOUS_FLOATING_UNDETERMINED), "AMB-S15"))
    r.append(_r7_case("R7-P in reveal container, menu_dependency UNKNOWN -> undetermined", K,
                      _zs(classify_zone_r7(**TL, **FLOAT_OFF,
                                           in_reveal_required_nav_container=True)),
                      (MISSING, R7_AMBIGUOUS_DRAWER_UNDETERMINED), "AMB-S16"))
    r.append(_r7_case("R7-P in reveal container but menu_dependency=0 -> inconsistent, not DRAWER", K,
                      _zs(classify_zone_r7(**TL, **FLOAT_OFF,
                                           in_reveal_required_nav_container=True,
                                           menu_dependency=False)),
                      (MISSING, R7_AMBIGUOUS_DRAWER_UNDETERMINED),
                      "R7 defines the DRAWER container as the one that produced menu_dependency=1; "
                      "these inputs contradict each other (AMB-S16)"))
    r.append(_r7_case("R7-P DRAWER confirmed outranks an UNDETERMINED FLOATING", K,
                      _zs(classify_zone_r7(**TL, computed_position="fixed", **DRAWER_ON)),
                      ("DRAWER", R7_OK)))
    # The reverse of the line above, and the case an independent re-derivation of R7 caught
    # this harness getting wrong: a CONFIRMED lower-precedence value must not overtake an
    # UNRESOLVED higher-precedence one.
    r.append(_r7_case("R7-P confirmed FLOATING must NOT overtake an undetermined DRAWER", K,
                      _zs(classify_zone_r7(**TL, **FLOAT_ON,
                                           in_reveal_required_nav_container=True)),
                      (MISSING, R7_AMBIGUOUS_DRAWER_UNDETERMINED),
                      "DRAWER outranks FLOATING, so while DRAWER is open the answer is not yet "
                      "known to be FLOATING"))
    r.append(_r7_case("R7-P same, with BOTTOM geometry underneath", K,
                      _zs(classify_zone_r7(**BR, **STICKY_ON,
                                           in_reveal_required_nav_container=True,
                                           menu_dependency=False)),
                      (MISSING, R7_AMBIGUOUS_DRAWER_UNDETERMINED)))
    r.append(_r7_case("R7-P undetermined DRAWER is reported as blocking, not as absence", K,
                      classify_zone_r7(**TL, **FLOAT_ON,
                                       in_reveal_required_nav_container=True)["override_eval"]
                      ["blocked_by_higher_precedence_unknown"], True))
    r.append(_r7_case("R7-P DRAWER ruled OUT lets a confirmed FLOATING through", K,
                      _zs(classify_zone_r7(**TL, **FLOAT_ON,
                                           in_reveal_required_nav_container=False,
                                           menu_dependency=True)),
                      ("FLOATING", R7_OK),
                      "the chain only stops while the higher rung is OPEN"))
    r.append(_r7_case("R7-P unobserved structural fields are reported, not assumed", K,
                      classify_zone_r7(**TL)["override_eval"]["structural_inputs_observed"],
                      {"computed_position": False, "out_of_flow_fixed_to_viewport": False,
                       "in_reveal_required_nav_container": False, "menu_dependency": False},
                      "geometry answers when nothing points at an override, but the consumer can "
                      "see that the structural inputs were never collected (AMB-S16)"))

    # --- an override answers even where geometry could not
    r.append(_r7_case("R7-P DRAWER with out-of-range coordinates still DRAWER", K,
                      _zs(classify_zone_r7(x_norm=-3.0, y_norm=7.0, **FLOAT_OFF, **DRAWER_ON)),
                      ("DRAWER", R7_OK),
                      "override precedes geometry, so the out-of-unit question never arises"))
    r.append(_r7_case("R7-P FLOATING with MISSING coordinates still FLOATING", K,
                      _zs(classify_zone_r7(x_norm=MISSING, y_norm=MISSING, **FLOAT_ON, **DRAWER_OFF)),
                      ("FLOATING", R7_OK)))
    res = classify_zone_r7(x_norm=0.9, y_norm=0.9, **FLOAT_ON, **DRAWER_ON)
    r.append(_r7_case("R7-P record_anyway holds under an override", K,
                      (res["entry_zone"], res["entry_x_norm"], res["entry_y_norm"]),
                      ("DRAWER", 0.9, 0.9),
                      "`override 가 적용돼도 entry_x_norm/entry_y_norm 은 그대로 저장한다`"))
    r.append(_r7_case("R7-P override basis is labelled, not silent", K,
                      classify_zone_r7(**TL, **FLOAT_ON, **DRAWER_OFF)["basis"],
                      "STRUCTURAL_OVERRIDE"))
    r.append(_r7_case("R7-P geometry basis is labelled, not silent", K,
                      classify_zone_r7(**TL, **FLOAT_OFF, **DRAWER_OFF)["basis"], "GEOMETRY"))

    # --- R7 writes `menu_dependency=1`; 04 §4 types it bool. Both spellings, nothing else.
    r.append(_r7_case("R7-P menu_dependency=1 (int) reads as the bool True", K,
                      _zs(classify_zone_r7(**TL, **FLOAT_OFF,
                                           in_reveal_required_nav_container=1,
                                           menu_dependency=1)),
                      ("DRAWER", R7_OK), "R7 structural_overrides.DRAWER says `menu_dependency=1`"))
    r.append(_r7_case("R7-P menu_dependency=0 (int) reads as the bool False", K,
                      _zs(classify_zone_r7(**TL, **FLOAT_OFF,
                                           in_reveal_required_nav_container=0,
                                           menu_dependency=0)),
                      ("TOP_LEFT", R7_OK)))
    for bad in (2, "1", "true", 1.0, []):
        r.append(_r7_case("R7-P non-boolean %r never becomes True" % (bad,), K,
                          _zs(classify_zone_r7(**TL, **FLOAT_OFF,
                                               in_reveal_required_nav_container=bad,
                                               menu_dependency=bad)),
                          ("TOP_LEFT", R7_OK),
                          "unparseable structural input stays MISSING, so DRAWER simply does not "
                          "fire — it is never coerced into firing"))
    r.append(_r7_case("R7-P truthy garbage in the FLOATING flow clause stays undetermined", K,
                      _zs(classify_zone_r7(**TL, computed_position="fixed",
                                           out_of_flow_fixed_to_viewport="yes", **DRAWER_OFF)),
                      (MISSING, R7_AMBIGUOUS_FLOATING_UNDETERMINED)))

    # --- statuses must never be mistakable for zone values
    r.append(_r7_case("R7-P no status string is a member of the 04 §4 entry_zone enum", K,
                      sorted(set((R7_OK, R7_OK_UNCONSULTED_AXIS_OUT_OF_RANGE,
                                  R7_MISSING_COORDINATES) + R7_AMBIGUOUS_STATUSES)
                             & set(ENTRY_ZONE_ENUM)), []))
    r.append(_r7_case("R7-P r7_zone() accessor agrees with the full result", K,
                      (r7_zone(**TL, **FLOAT_OFF, **DRAWER_ON),
                       r7_zone(0.10, 0.90), r7_zone(-1.0, 0.10)),
                      ("DRAWER", "BOTTOM", MISSING)))

    # --- the strongest check in this suite: a second, independent derivation of R7
    xchk = r7_independent_crosscheck()
    r.append(_r7_case("R7-P independent re-derivation of R7 disagrees nowhere", K,
                      (xchk["n_disagreements"], xchk["n_inputs_checked"] > 6000),
                      (0, True),
                      "`_r7_independent_reference()` shares no code with `classify_zone_r7()`; "
                      "it found the FLOATING/DRAWER precedence defect that 60 green fixtures and "
                      "8 caught mutations had missed"))
    return r


def compare_zone_policies() -> dict:
    """Control group: does the pre-R7 fixture-only equal-thirds policy answer differently?

    The two policies are compared on the SAME inputs. Nothing is merged; agreement is a
    finding to be shown, not an assumption.
    """
    fixture_zone = lambda x, y: classify_zone_geometric(
        x, y, FIXTURE_ONLY_ZONE_POLICY, allow_fixture_only=True)
    points: list[tuple[float, float, str]] = []
    for i in range(41):
        for j in range(41):
            points.append((i / 40.0, j / 40.0, "unit_grid"))
    for v in (THIRD, TWO_THIRDS):
        for w in (0.10, 0.50, 0.90, THIRD, TWO_THIRDS):
            points.append((v, w, "on_cut"))
            points.append((w, v, "on_cut"))
        for nudge in (math.nextafter(v, 0.0), math.nextafter(v, 1.0)):
            points.append((nudge, 0.10, "cut_neighbour"))
            points.append((0.10, nudge, "cut_neighbour"))
    for p in (-5.0, -0.001, 1.001, 3.7):
        for q in (0.10, 0.50, 0.90):
            points.append((p, q, "out_of_unit_range"))
            points.append((q, p, "out_of_unit_range"))

    agree, diverge = [], []
    by_class: dict[str, dict[str, int]] = {}
    for x, y, cls in points:
        f = fixture_zone(x, y)
        r = classify_zone_r7(x, y)
        same = (f == r["entry_zone"])
        slot = by_class.setdefault(cls, {"agree": 0, "diverge": 0})
        slot["agree" if same else "diverge"] += 1
        rec = {"x": x, "y": y, "point_class": cls,
               "fixture_only_policy": f, "r7_policy": r["entry_zone"], "r7_status": r["status"]}
        (agree if same else diverge).append(rec)

    # Independent cross-check: R7's own geometry vs the generic classifier driven by the
    # R7 policy object. Both must agree on every in-range point or one of them has drifted.
    drift = []
    for i in range(41):
        for j in range(41):
            x, y = i / 40.0, j / 40.0
            a = classify_zone_geometric(x, y, R7_ZONE_POLICY)
            b = classify_zone_r7(x, y)["entry_zone"]
            if a != b:
                drift.append({"x": x, "y": y, "generic_with_r7_policy": a, "classify_zone_r7": b})

    return {
        "question": "Do the pre-R7 FIXTURE_ONLY_NOT_SSOT equal-thirds policy and the A-frozen R7 "
                    "policy return the same entry_zone on the same input?",
        "method": "Both policies evaluated on an identical point set. No merging; the fixture "
                  "policy is left in the module untouched as the control.",
        "policies": {"control": FIXTURE_ONLY_ZONE_POLICY.as_dict(),
                     "treatment": R7_ZONE_POLICY.as_dict()},
        "cut_values_identical": (_r7_cuts(FIXTURE_ONLY_ZONE_POLICY) == _r7_cuts(R7_ZONE_POLICY)),
        "n_points": len(points),
        "n_agree": len(agree),
        "n_diverge": len(diverge),
        "by_point_class": by_class,
        "divergences": diverge,
        "in_range_agreement": {
            "n_points": sum(v["agree"] + v["diverge"] for k, v in by_class.items()
                            if k != "out_of_unit_range"),
            "n_agree": sum(v["agree"] for k, v in by_class.items() if k != "out_of_unit_range"),
            "n_diverge": sum(v["diverge"] for k, v in by_class.items() if k != "out_of_unit_range"),
        },
        "divergence_summary": (
            "The two policies carry IDENTICAL cut values (1/3, 2/3 on both axes) and the same "
            "half-open band rule, so inside [0,1] they agree everywhere — %d/%d in-range points, "
            "the exact cuts and their nextafter neighbours included. They diverge only where the "
            "fixture policy answers a question R7 did not settle: out-of-unit coordinates, which "
            "the fixture policy classifies by extrapolating its inequalities and R7 leaves as %s. "
            "Where the out-of-unit axis is one R7 does not consult (x in MID/BOTTOM) the two "
            "agree again. The fixture policy also cannot express the structural overrides at all "
            "(AMB-S02), so FLOATING/DRAWER inputs are outside the comparable domain — agreement "
            "here is agreement on geometry, not on entry_zone as a whole."
            % (sum(v["agree"] for k, v in by_class.items() if k != "out_of_unit_range"),
               sum(v["agree"] + v["diverge"] for k, v in by_class.items()
                   if k != "out_of_unit_range"),
               R7_AMBIGUOUS_OUT_OF_UNIT_RANGE)),
        "r7_internal_consistency_crosscheck": {
            "claim": "classify_zone_r7() and classify_zone_geometric(policy=R7_ZONE_POLICY) agree "
                     "on every in-range grid point; R7's dedicated primitives have not drifted "
                     "from the generic classifier.",
            "n_checked": 41 * 41, "n_drift": len(drift), "drift": drift,
        },
        "boundary_example_clause_contrast": r7_boundary_example_contrast(),
    }


def r7_boundary_example_contrast() -> dict:
    """R7's boundary_rule contradicts itself on the y axis. Both readings, side by side.

    Reading A (implemented): the inequality tables + `하한 포함·상한 배제 [a, b)`
        -> a coordinate exactly on a cut belongs to the UPPER band.
    Reading B: the trailing clause `정확히 1/3 인 점은 TOP 이자 TOP_CENTER 다`
        -> y = 1/3 would be TOP, contradicting `1/3 ≤ y < 2/3 → MID` in the same key.
    On the x axis the two readings AGREE (x = 1/3 -> TOP_CENTER under both).
    """
    def reading_b(x: float, y: float) -> Any:
        """Reading A everywhere EXCEPT the one point R7's clause actually names.

        The clause is applied as literally as it can be: it says `정확히 1/3 인 점` is
        TOP/TOP_CENTER, so only y == 1/3 moves. It is NOT generalized into a global
        `(a, b]` convention — that would be this lane inventing a rule in order to
        dramatise a disagreement.
        """
        y_top, _, _, _ = _r7_cuts(R7_ZONE_POLICY)
        if y == y_top:
            return r7_top_x_zone(x, R7_ZONE_POLICY)
        return classify_zone_r7(x, y)["entry_zone"]

    probes = [(0.10, THIRD), (THIRD, THIRD), (0.90, THIRD), (THIRD, 0.10),
              (TWO_THIRDS, 0.10), (0.10, TWO_THIRDS), (TWO_THIRDS, TWO_THIRDS),
              (0.10, 0.10), (0.90, 0.90), (0.50, 0.50)]
    rows = []
    for x, y in probes:
        a = classify_zone_r7(x, y)["entry_zone"]
        b = reading_b(x, y)
        rows.append({"x": x, "y": y, "reading_A_inequality_table": a,
                     "reading_B_example_clause": b, "same": a == b})
    return {
        "ambiguity_id": "AMB-S14",
        "reading_A": "R7 thresholds tables + `경계값은 하한 포함·상한 배제([a, b))로 통일한다` "
                     "-> a value on a cut goes UPWARD (y=1/3 -> MID). IMPLEMENTED.",
        "reading_B": "R7 `정확히 1/3 인 점은 TOP 이자 TOP_CENTER 다` -> y=1/3 would be TOP. "
                     "NOT implemented; recorded. Applied only to the point the clause names, "
                     "not generalized into a `(a, b]` convention.",
        "why_A": "Two of R7's three statements (the y inequality table and the general half-open "
                 "rule) give MID at y=1/3; only the trailing example gives TOP, and that example "
                 "contradicts the general rule it is appended to. The x axis is unaffected — both "
                 "readings give TOP_CENTER at x=1/3. Note the clause is self-inconsistent even on "
                 "its own terms: to make y=1/3 TOP the cut must belong DOWNWARD, but to make "
                 "x=1/3 TOP_CENTER the cut must belong UPWARD.",
        "resolution_owner": "A — the ambiguity is inside R7 itself and this lane must not pick.",
        "probes": rows,
        "n_probes_diverging": sum(1 for p in rows if not p["same"]),
    }


def _r7_independent_reference(x: Any, y: Any, pos: Any, flow: Any, incont: Any, md: Any) -> Any:
    """A SECOND implementation of R7, written from the ticket prose only.

    It deliberately shares NOTHING with `classify_zone_r7`: no policy object, no `_r7_*`
    primitive, its own hard-coded 1/3 and 2/3. Fixtures written by the same hand that wrote
    the implementation tend to encode the same misreading, and mutation testing cannot help
    — it only corrupts primitives the fixtures already exercise. Two independent derivations
    disagreeing is the cheapest way to surface a misreading neither test suite anticipated.

    This is exactly how the FLOATING-overtakes-unresolved-DRAWER defect was found; see
    `defects_found_during_convergence`.
    """
    # `control 이 reveal 을 요구하는 nav_container 안에 있는 경우 (menu_dependency=1 을 만든 그 container)`
    if incont is True and md is True:
        return "DRAWER"
    # DRAWER outranks FLOATING; while it is open, nothing below it may answer.
    if incont is True:
        return MISSING
    # `computed position 이 fixed 또는 sticky 이고 일반 흐름에서 벗어나 viewport 에 고정된 경우`
    if pos in ("fixed", "sticky") and flow is True:
        return "FLOATING"
    if pos in ("fixed", "sticky") and flow is MISSING:
        return MISSING
    if x is MISSING or y is MISSING:
        return MISSING
    if not (0.0 <= y <= 1.0):
        return MISSING
    if y < 1.0 / 3.0:                       # `y < 1/3 → TOP`
        if not (0.0 <= x <= 1.0):
            return MISSING
        if x < 1.0 / 3.0:                   # `x < 1/3 → TOP_LEFT`
            return "TOP_LEFT"
        if x < 2.0 / 3.0:                   # `1/3 ≤ x < 2/3 → TOP_CENTER`
            return "TOP_CENTER"
        return "TOP_RIGHT"                  # `x ≥ 2/3 → TOP_RIGHT`
    if y < 2.0 / 3.0:                       # `1/3 ≤ y < 2/3 → MID`, x not consulted
        return "MID"
    return "BOTTOM"                         # `y ≥ 2/3 → BOTTOM`, x not consulted


def r7_independent_crosscheck() -> dict:
    """Sweep both derivations over the same inputs and list every disagreement."""
    specials = [1.0 / 3.0, 2.0 / 3.0, math.nextafter(1.0 / 3.0, 0.0),
                math.nextafter(1.0 / 3.0, 1.0), math.nextafter(2.0 / 3.0, 0.0),
                math.nextafter(2.0 / 3.0, 1.0), 0.0, 1.0, -9.0, -0.001, 1.001, 4.2]
    geo_points = [(i / 80.0, j / 80.0) for i in range(81) for j in range(81)]
    geo_points += [(a, b) for a in specials for b in specials]
    disagreements: list[dict] = []
    n = 0
    for x, y in geo_points:
        n += 1
        a = _r7_independent_reference(x, y, MISSING, MISSING, MISSING, MISSING)
        b = classify_zone_r7(x, y)["entry_zone"]
        if a != b:
            disagreements.append({"x": x, "y": y, "independent": a, "harness": b})
    struct_points = [(0.10, 0.10), (0.90, 0.90), (0.50, 0.50), (1.0 / 3.0, 0.10),
                     (0.50, 1.0 / 3.0), (-3.0, 0.10), (MISSING, MISSING)]
    for pos in (MISSING, "static", "fixed", "sticky", "relative", "absolute"):
        for flow in (MISSING, True, False):
            for incont in (MISSING, True, False):
                for md in (MISSING, True, False):
                    for x, y in struct_points:
                        n += 1
                        a = _r7_independent_reference(x, y, pos, flow, incont, md)
                        b = classify_zone_r7(
                            x, y, computed_position=pos,
                            out_of_flow_fixed_to_viewport=flow,
                            in_reveal_required_nav_container=incont,
                            menu_dependency=md)["entry_zone"]
                        if a != b:
                            disagreements.append(
                                {"x": x, "y": y, "computed_position": pos,
                                 "out_of_flow_fixed_to_viewport": flow,
                                 "in_reveal_required_nav_container": incont,
                                 "menu_dependency": md, "independent": a, "harness": b})
    return {
        "method": "`_r7_independent_reference()` re-derives R7 from the ticket prose with its own "
                  "hard-coded cuts and shares no primitive, policy object, or helper with "
                  "`classify_zone_r7()`. Both are swept over the same inputs.",
        "why": "Fixtures and mutations written alongside an implementation share its blind spots. "
               "A second derivation does not.",
        "n_inputs_checked": n,
        "n_disagreements": len(disagreements),
        "disagreements": disagreements[:50],
        "disagreements_truncated": len(disagreements) > 50,
    }


R7_MUTANTS: list[tuple[str, str, str, Callable]] = [
    ("R7-M01", "_r7_band_test", "half-open `[a, b)` flipped to `(a, b]` — a value ON a cut falls "
                                "into the LOWER band (R7 reading B forced everywhere)",
     lambda v, c: v <= c),
    ("R7-M02", "_r7_x_split_applies", "x thirds applied to MID and BOTTOM too, inventing "
                                      "MID_LEFT-style labels R7 explicitly refuses",
     lambda band: True),
    ("R7-M03", "_r7_precedence_order", "structural overrides ignored — geometry always answers",
     lambda: ()),
    ("R7-M04", "_r7_precedence_order", "precedence reversed — FLOATING beats DRAWER, contradicting "
                                       "`둘 다 해당하면 DRAWER 가 우선한다`",
     lambda: ("FLOATING", "DRAWER")),
    ("R7-M05", "_r7_range_ok", "out-of-unit coordinates silently classified instead of left "
                               "AMBIGUOUS",
     lambda v: True),
    ("R7-M06", "_r7_pick_axes", "x and y axes swapped",
     lambda x, y: (y, x)),
    ("R7-M07", "_r7_cuts", "y and x cut pairs swapped (1/3 and 2/3 exchanged between axes is "
                           "invisible, so the y cuts are pushed to 0.5/0.75)",
     lambda policy: (0.5, 0.75, policy.x_left_max, policy.x_center_max)),
    ("R7-M08", "_r7_cuts", "equal thirds replaced by halves — the classic 'looked fine on a "
                           "coarse grid' error",
     lambda policy: (0.5, 0.5, 0.5, 0.5)),
    ("R7-M09", "_r7_truth", "structural inputs read with plain Python truthiness, so unparseable "
                            "values silently fire an override",
     lambda value: bool(value)),
    ("R7-M10", "_r7_truth", "structural inputs collapsed to MISSING, so overrides never fire and "
                            "geometry always answers",
     lambda value: MISSING),
]


def run_r7_fixtures() -> list[dict]:
    return run_r7_boundary_fixtures() + run_r7_precedence_fixtures()


def run_r7_mutation_tests(baseline: list[dict]) -> tuple[list[dict], bool, int]:
    """Corrupt one R7 primitive at a time; the R7 fixtures must catch every one."""
    mod = sys.modules[__name__]
    base_ok = all(f["pass"] for f in baseline)
    out = []
    for mid, target, desc, impl in R7_MUTANTS:
        original = getattr(mod, target)
        setattr(mod, target, impl)
        try:
            try:
                res = run_r7_fixtures()
                failed = [f["fixture"] for f in res if not f["pass"]]
                errored = None
            except Exception as exc:
                failed = ["<exception>"]
                errored = "%s: %s" % (type(exc).__name__, exc)
        finally:
            setattr(mod, target, original)
        out.append({"mutation_id": mid, "target_primitive": target, "mutation": desc,
                    "baseline_all_passed": base_ok, "caught": bool(failed),
                    "n_fixtures_failed_under_mutation": len(failed),
                    "example_failing_fixtures": failed[:5],
                    "exception_under_mutation": errored})
    restored = run_r7_fixtures()
    return out, all(f["pass"] for f in restored), len(restored)


# --------------------------------------------------------------------------------------
# 10b. R7 convergence report
# --------------------------------------------------------------------------------------

# AMB-S01/S02/S03 were raised against SSOTV3 and are now ANSWERED by T-A-V3-STEP1-003 R7.
# The original entries above are left standing (they record what was missing and when);
# the resolution is stamped onto them here rather than by deleting them.
_R7_RESOLVES = {
    "AMB-S01": "RESOLVED by T-A-V3-STEP1-003 R7 (successor delta Δ8). Cuts frozen at 1/3 and 2/3 "
               "on both axes, half-open bands. SSOTV3 04 §6 itself is still silent — the authority "
               "is the ticket, not the SSOT original.",
    "AMB-S02": "RESOLVED by R7 `structural_overrides`: FLOATING/DRAWER outrank geometry and DRAWER "
               "outranks FLOATING. Geometry still never emits them; `classify_zone_r7` applies the "
               "precedence from separately collected structural inputs.",
    "AMB-S03": "RESOLVED by R7 `thresholds.MID_BOTTOM`: the x thirds apply inside the TOP band only. "
               "Lane S's earlier inference was correct, but it was an inference until R7.",
}
for _a in AMBIGUOUS_DEFINITIONS:
    if _a["id"] in _R7_RESOLVES:
        _a["resolution"] = _R7_RESOLVES[_a["id"]]
        _a["resolution_source"] = "T-A-V3-STEP1-003 R7"
        _a["resolution_preregistered"] = R7_PREREGISTRATION
del _a

R7_AMBIGUOUS_DEFINITIONS: list[dict[str, str]] = [
    {
        "id": "AMB-S14",
        "variable": "entry_zone (R7 boundary_rule)",
        "issue": "R7 contradicts itself on the y axis. `thresholds.y_bands` says `1/3 ≤ y < 2/3 → MID` "
                 "and `boundary_rule` says `경계값은 하한 포함·상한 배제([a, b))로 통일한다` — both put "
                 "y=1/3 in MID. The same `boundary_rule` sentence then adds `정확히 1/3 인 점은 TOP 이자 "
                 "TOP_CENTER 다`, which puts y=1/3 in TOP. The x axis is unaffected: x=1/3 is "
                 "TOP_CENTER under either reading.",
        "lane_s_action": "Implemented the inequality table + the general half-open rule (y=1/3 → MID) "
                         "because two of the three statements agree and the third contradicts the rule "
                         "it is appended to. The alternative reading is computed side by side in "
                         "`r7_boundary_example_contrast()` and every diverging point is listed. This "
                         "lane does NOT decide which reading is A's intent.",
        "owner": "A — the contradiction is inside R7 itself.",
    },
    {
        "id": "AMB-S15",
        "variable": "entry_zone = FLOATING (R7 structural_overrides.FLOATING)",
        "issue": "R7 defines FLOATING as `computed position 이 fixed 또는 sticky 이고 일반 흐름에서 "
                 "벗어나 viewport 에 고정된 경우`. Whether the second clause is an independent observable "
                 "or a restatement of the first is unstated, and it matters: `position: sticky` stays in "
                 "normal flow and is viewport-fixed only while stuck, so under the strict reading a "
                 "sticky header scrolled to its unstuck state is NOT FLOATING.",
        "lane_s_action": "Both clauses are required inputs. When the position clause is satisfied but the "
                         "flow/viewport clause is unobserved the result is "
                         "AMBIGUOUS_FLOATING_UNDETERMINED — no zone, no guess. If A rules the second "
                         "clause a restatement, the fix is one predicate.",
        "owner": "A (ruling) / B (collector — decides whether the flow clause is even captured).",
    },
    {
        "id": "AMB-S16",
        "variable": "entry_zone = DRAWER (R7 structural_overrides.DRAWER)",
        "issue": "R7 identifies the DRAWER container as `menu_dependency=1 을 만든 그 container`. It does "
                 "not say what to do when a control is observed inside a reveal-requiring container while "
                 "menu_dependency=0 — the two observations cannot both hold under R7's own wording, and "
                 "R7 gives no precedence between them.",
        "lane_s_action": "Reported as AMBIGUOUS_DRAWER_UNDETERMINED with the inconsistency named. Neither "
                         "input is trusted over the other and no zone is emitted. Because DRAWER "
                         "outranks FLOATING, an unresolved DRAWER also blocks a confirmed FLOATING from "
                         "being returned.",
        "second_gap": "R7 also does not say what an UNOBSERVED structural field means. This lane treats "
                      "'no signal at all' as 'the override does not fire' — otherwise every row missing "
                      "these fields would be AMBIGUOUS and R7 would be inoperable, which contradicts "
                      "R7's own `수집은 진행한다`. Only POSITIVE evidence (in_reveal_required=True, or "
                      "computed_position in {fixed, sticky}) blocks geometry. That line is this lane's, "
                      "not R7's; `override_eval.structural_inputs_observed` records per-field whether "
                      "the input was ever collected so the choice is auditable and reversible.",
        "owner": "A (ruling) / B (collector — may be a collection defect rather than a definition gap).",
    },
    {
        "id": "AMB-S17",
        "variable": "entry_x_norm / entry_y_norm outside [0,1] under R7",
        "issue": "R7 freezes cut values but does not regulate coordinates outside the unit interval, which "
                 "AMB-S04 already showed are reachable (control partially off-screen, or below the fold in "
                 "state Sn). `y ≥ 2/3 → BOTTOM` read literally would swallow y=9.9 into BOTTOM; whether "
                 "that is intended, or whether such a row should be excluded, is unstated.",
        "lane_s_action": "Coordinates are still never clamped (AMB-S04 behaviour preserved). When an "
                         "out-of-unit coordinate is one R7 actually CONSULTS in that band, the result is "
                         "AMBIGUOUS_OUT_OF_UNIT_RANGE and no zone is emitted. When the out-of-unit axis is "
                         "one R7 does not consult (x in MID/BOTTOM), the zone stands and the fact is "
                         "flagged as OK_UNCONSULTED_AXIS_OUT_OF_RANGE rather than dropped.",
        "owner": "A (SSOT) / B (collector).",
    },
]
AMBIGUOUS_DEFINITIONS.extend(R7_AMBIGUOUS_DEFINITIONS)

R7_LIMITATION = (
    "R7 was frozen with REAL observations at zero, and this convergence was built the same way: no "
    "MAIN50 coordinate has ever been measured, so every number here comes from synthetic fixtures with "
    "answers planted by construction. That makes the boundary and precedence behaviour verifiable and "
    "the DISTRIBUTIONAL behaviour entirely unknown — nothing here says how often real controls land on "
    "or near a cut, how often FLOATING/DRAWER fire, or how often coordinates leave [0,1]. Three of R7's "
    "inputs (computed_position, the out-of-flow/viewport-fixed clause, in_reveal_required_nav_container) "
    "are collector-supplied and this lane cannot verify that B will emit them; if they arrive missing, "
    "entry_zone will be AMBIGUOUS rather than wrong, which is the intended failure mode but is still a "
    "gap. The fixture-only equal-thirds policy is retained purely as a control and must never code a "
    "real observation. Mutation coverage is ten single-primitive corruptions of the R7 path, and a "
    "second independent derivation of R7 agrees on every one of ~7.8k swept inputs — but both are "
    "still checks of ONE reading of R7's text. If AMB-S14 is resolved the other way, every green "
    "result above is green against the wrong reading, and the agreement of the two derivations "
    "would not have caught it: they were written from the same reading."
)


def build_r7_convergence(regression: dict) -> dict:
    boundary = run_r7_boundary_fixtures()
    precedence = run_r7_precedence_fixtures()
    all_fx = boundary + precedence
    mutations, restored_ok, restored_n = run_r7_mutation_tests(all_fx)
    comparison = compare_zone_policies()
    transcription = verify_r7_transcription()

    b_pass = sum(1 for f in boundary if f["pass"])
    p_pass = sum(1 for f in precedence if f["pass"])
    m_caught = sum(1 for m in mutations if m["caught"])

    fixtures_green = (b_pass == len(boundary) and p_pass == len(precedence))
    mutations_green = (m_caught == len(mutations)) and restored_ok
    regression_green = regression["all_passed"]
    transcription_green = (transcription.get("verbatim_match") is True)
    drift_green = (comparison["r7_internal_consistency_crosscheck"]["n_drift"] == 0)

    open_ambiguities = [a for a in R7_AMBIGUOUS_DEFINITIONS]

    if fixtures_green and mutations_green and regression_green and transcription_green and drift_green:
        verdict = "CONVERGED_WITH_AMBIGUITY" if open_ambiguities else "CONVERGED"
    else:
        verdict = "NOT_CONVERGED"

    basis = []
    if not transcription_green:
        basis.append("the embedded R7 transcription does not match the authority file")
    if not fixtures_green:
        basis.append("R7 boundary/precedence fixtures failed")
    if not mutations_green:
        basis.append("an R7 mutation escaped, or the suite did not restore cleanly")
    if not regression_green:
        basis.append("the pre-existing Lane S fixture suite regressed")
    if not drift_green:
        basis.append("classify_zone_r7 drifted from the generic classifier under the R7 policy")
    if not basis:
        basis.append(
            "Lane S now derives entry_zone from R7 and only from R7: %d boundary fixtures and %d "
            "precedence fixtures pass, %d/%d R7 mutations are caught, the pre-existing suite still "
            "passes (%d/%d), and the embedded R7 text is byte-identical to the ticket. The verdict is "
            "not plain CONVERGED because R7 leaves %d questions open (AMB-S14..S17), one of which "
            "(AMB-S14) is a contradiction inside R7's own boundary_rule."
            % (len(boundary), len(precedence), m_caught, len(mutations),
               regression["total_passed"], regression["total"], len(open_ambiguities)))

    return {
        "verdict": verdict,
        "verdict_basis": " / ".join(basis),
        "lane": "S — Spatial / Control-form / Menu-Reveal",
        "task": "Lane S-R7 convergence — replace Lane S's refusal to derive entry_zone with A's frozen "
                "operational definition, without inventing anything R7 did not settle.",
        "generated_by": os.path.relpath(os.path.abspath(__file__), RD),
        "base_sha": BASE_SHA,
        "data_status": "NO_REAL_DATA — REAL 접속 누적 0건; synthetic fixtures only",
        "r7_verbatim": R7_VERBATIM,
        "r7_transcription_check": transcription,
        "policy_provenance": {
            "authoritative_policy": R7_ZONE_POLICY.as_dict(),
            "control_policy_retained_unchanged": FIXTURE_ONLY_ZONE_POLICY.as_dict(),
            "ssot_original_carries_no_cuts": SSOT_ZONE_POLICY_R7 is None,
            "why_two_policies_exist": "The pre-R7 fixture-only policy is NOT deleted. It is the control "
                                      "group: keeping it lets the two operationalizations be compared on "
                                      "identical inputs instead of assumed equivalent.",
            "preregistration": R7_PREREGISTRATION,
            "decided_at_kst": R7_DECIDED_AT_KST,
            "observations_at_decision": 0,
            "recorded_in": R7_RECORDED_IN,
            "result_blind": True,
        },
        "implementation": {
            "entrypoint": "classify_zone_r7(x_norm, y_norm, *, computed_position, "
                          "out_of_flow_fixed_to_viewport, in_reveal_required_nav_container, "
                          "menu_dependency)",
            "resolution_order": ["DRAWER (structural)", "FLOATING (structural)", "geometry"],
            "geometry": "y bands via r7_y_band(); x thirds via r7_top_x_zone(), consulted in the TOP "
                        "band only",
            "raw_coordinates": "entry_x_norm / entry_y_norm are echoed unchanged on every path, "
                               "override paths included (R7 record_anyway)",
            "statuses": [R7_OK, R7_OK_UNCONSULTED_AXIS_OUT_OF_RANGE, R7_MISSING_COORDINATES,
                         R7_AMBIGUOUS_OUT_OF_UNIT_RANGE, R7_AMBIGUOUS_FLOATING_UNDETERMINED,
                         R7_AMBIGUOUS_DRAWER_UNDETERMINED],
            "statuses_are_not_zone_values": "None of the status strings is a member of "
                                            "ENTRY_ZONE_ENUM; a status never leaks into the entry_zone "
                                            "column.",
            "no_new_thresholds": "The only cut values in the R7 path are R7's own 1/3 and 2/3. No "
                                 "tolerance, epsilon, score, or weight was introduced.",
        },
        "boundary_fixtures": {"passed": b_pass, "total": len(boundary), "cases": boundary},
        "precedence_fixtures": {"passed": p_pass, "total": len(precedence), "cases": precedence},
        "policy_comparison": comparison,
        "independent_crosscheck": r7_independent_crosscheck(),
        "mutation_results": {"caught": m_caught, "total": len(mutations), "cases": mutations,
                             "restored_after_mutation": restored_ok,
                             "restored_fixture_count": restored_n},
        "defects_found_during_convergence": [
            {
                "found_by": "an independent re-derivation of R7 from the ticket prose, sharing no "
                            "code with this harness, swept over 161k input combinations",
                "defect": "r7_structural_override() walked the precedence chain looking only for a "
                          "TRUE flag. With in_reveal_required_nav_container=True but menu_dependency "
                          "unobserved (DRAWER unresolved) and computed_position=fixed with the flow "
                          "clause True (FLOATING confirmed), it returned FLOATING.",
                "why_it_was_wrong": "R7 ranks DRAWER above FLOATING. While DRAWER is open the answer "
                                    "is not yet known to be FLOATING, so returning FLOATING was this "
                                    "lane silently resolving R7's precedence with a guess. 20 input "
                                    "combinations were affected.",
                "fix": "The chain now stops at the first rung that is confirmed OR unresolvable; a "
                       "confirmed lower value can only be returned once the higher one is ruled OUT.",
                "regression_guard": ["R7-P confirmed FLOATING must NOT overtake an undetermined DRAWER",
                                     "R7-P same, with BOTTOM geometry underneath",
                                     "R7-P undetermined DRAWER is reported as blocking, not as absence",
                                     "R7-P DRAWER ruled OUT lets a confirmed FLOATING through"],
                "lesson": "The R7 fixtures were 60/60 green and all 8 mutations were caught while this "
                          "defect was live. Mutation testing corrupts the primitives the fixtures "
                          "already exercise; it cannot find a case the fixtures never thought to ask "
                          "about. Only the independent re-derivation did.",
            },
        ],
        "regression": regression,
        "remaining_ambiguities": R7_AMBIGUOUS_DEFINITIONS,
        "ambiguities_closed_by_r7": [
            {"id": a["id"], "resolution": a["resolution"]}
            for a in AMBIGUOUS_DEFINITIONS if a.get("resolution")
        ],
        "limitation": R7_LIMITATION,
        "prohibitions_observed": [
            "nothing R7 left unsettled was filled in — four open questions went to AMB-S14..S17",
            "no threshold, cut-off, epsilon, or composite score beyond R7's own 1/3 and 2/3",
            "the pre-R7 FIXTURE_ONLY_NOT_SSOT policy was kept, not deleted or merged",
            "no REAL access, no candidate URL, no control/ read beyond nothing at all",
            "no other lane's file read or written",
            "no git add/commit/push",
            "no gold label, no holdout, no GO/NO-GO",
        ],
    }


def _write_r7_findings(p: dict, path: str) -> None:
    L: list[str] = []
    A = L.append
    cmp_ = p["policy_comparison"]
    con = cmp_["boundary_example_clause_contrast"]
    A("# Lane S — R7 `entry_zone` 수렴")
    A("")
    A("- verdict: **%s**" % p["verdict"])
    A("- 권위: `%s` → `%s`" % (R7_TICKET_PATH, R7_TICKET_KEY))
    A("- 확정 시각(KST): `%s` · 확정 시점 관측 수: **%d건**"
      % (R7_DECIDED_AT_KST, p["policy_provenance"]["observations_at_decision"]))
    A("- 사전등록: %s" % R7_PREREGISTRATION)
    A("- 기록 위치: %s" % R7_RECORDED_IN)
    A("- data status: **%s**" % p["data_status"])
    A("")
    A("## 1. 무엇이 바뀌었나")
    A("")
    A("Lane S 는 `entry_zone` 유도를 **거부**하고 있었다. SSOTV3 04 §6 에 x/y 절단값이 없었기 때문이고,")
    A("그 상태를 `D-V3-FINDING-007` 로 올렸다. A 가 `T-A-V3-STEP1-003` R7 로 절단값을 확정했으므로")
    A("이제 유도한다. 확정은 **관측 0건 상태**에서 이뤄졌고, 이 수렴 작업도 실측 없이 fixture 로만 했다.")
    A("")
    A("fixture 용 1/3 등분 정책(`FIXTURE_ONLY_NOT_SSOT`)은 **지우지 않았다**. 대조군으로 쓴다 —")
    A("두 정책이 같은 답을 주는지는 가정이 아니라 확인의 대상이다(§4).")
    A("")
    A("전사 검증: 모듈에 박아둔 R7 원문이 티켓 파일과 **바이트 동일**한가 → `%s` "
      "(ticket sha256 `%s`)"
      % (p["r7_transcription_check"].get("verbatim_match"),
         p["r7_transcription_check"].get("ticket_sha256")))
    A("")
    A("## 2. 경계값 fixture (%d/%d)"
      % (p["boundary_fixtures"]["passed"], p["boundary_fixtures"]["total"]))
    A("")
    A("R7 이 이름 붙인 절단값을 **정확히** 밟고, 그 양옆 `nextafter` 한 칸까지 고정했다.")
    A("")
    A("| fixture | 기대 | 관측 | 통과 |")
    A("|---|---|---|---|")
    for f in p["boundary_fixtures"]["cases"]:
        A("| %s | `%s` | `%s` | %s |"
          % (f["fixture"], f["expected"], f["observed"], "✓" if f["pass"] else "**✗**"))
    A("")
    A("### 2.1 R7 이 자기 자신과 어긋나는 지점 (AMB-S14)")
    A("")
    A("- 읽기 A (구현함): %s" % con["reading_A"])
    A("- 읽기 B (구현 안 함): %s" % con["reading_B"])
    A("- 왜 A 인가: %s" % con["why_A"])
    A("- 두 읽기가 갈리는 probe: **%d/%d**" % (con["n_probes_diverging"], len(con["probes"])))
    A("")
    A("| x | y | 읽기 A | 읽기 B | 동일 |")
    A("|---|---|---|---|---|")
    for pr in con["probes"]:
        A("| %.6f | %.6f | `%s` | `%s` | %s |"
          % (pr["x"], pr["y"], pr["reading_A_inequality_table"],
             pr["reading_B_example_clause"], "예" if pr["same"] else "**아니오**"))
    A("")
    A("이 선택은 **내 판정이 아니다**. 어느 읽기가 A 의 의도인지는 A 가 정한다. 나는 구현한 쪽과")
    A("구현하지 않은 쪽을 둘 다 계산해서 나란히 남겼다.")
    A("")
    A("## 3. Precedence fixture (%d/%d)"
      % (p["precedence_fixtures"]["passed"], p["precedence_fixtures"]["total"]))
    A("")
    A("R7: `FLOATING 과 DRAWER 는 기하보다 우선한다` · `둘 다 해당하면 DRAWER 가 우선한다`.")
    A("양방향으로 봤다 — override 가 기하를 이기는지, 그리고 조건이 없을 때 override 가 **안 걸리는지**.")
    A("")
    A("| fixture | 기대 | 관측 | 통과 |")
    A("|---|---|---|---|")
    for f in p["precedence_fixtures"]["cases"]:
        A("| %s | `%s` | `%s` | %s |"
          % (f["fixture"], f["expected"], f["observed"], "✓" if f["pass"] else "**✗**"))
    A("")
    A("## 4. 정책 간 대조군 — fixture 1/3 정책 vs R7")
    A("")
    A("- 절단값이 문자 그대로 같은가: **%s**" % cmp_["cut_values_identical"])
    A("- 비교한 입력: **%d점** · 일치 **%d** · 불일치 **%d**"
      % (cmp_["n_points"], cmp_["n_agree"], cmp_["n_diverge"]))
    A("")
    A("| 입력 부류 | 일치 | 불일치 |")
    A("|---|---|---|")
    for k, v in sorted(cmp_["by_point_class"].items()):
        A("| %s | %d | %d |" % (k, v["agree"], v["diverge"]))
    A("")
    A(cmp_["divergence_summary"])
    A("")
    if cmp_["divergences"]:
        A("갈린 지점 (전량, %d건):" % len(cmp_["divergences"]))
        A("")
        A("| x | y | 부류 | fixture 정책 | R7 | R7 status |")
        A("|---|---|---|---|---|---|")
        for d in cmp_["divergences"]:
            A("| %s | %s | %s | `%s` | `%s` | `%s` |"
              % (d["x"], d["y"], d["point_class"], d["fixture_only_policy"],
                 d["r7_policy"], d["r7_status"]))
    else:
        A("갈린 지점 없음.")
    A("")
    xc = cmp_["r7_internal_consistency_crosscheck"]
    A("추가 대조: %s → 검사 %d점, 어긋남 **%d건**." % (xc["claim"], xc["n_checked"], xc["n_drift"]))
    A("")
    ic = p["independent_crosscheck"]
    A("### 4.1 독립 재도출 대조")
    A("")
    A("%s" % ic["method"])
    A("")
    A("- 이유: %s" % ic["why"])
    A("- 검사 입력: **%d개** · 불일치 **%d건**" % (ic["n_inputs_checked"], ic["n_disagreements"]))
    A("")
    for d in p["defects_found_during_convergence"]:
        A("> **수렴 중 발견한 결함** — %s" % d["defect"])
        A(">")
        A("> 발견 경로: %s" % d["found_by"])
        A(">")
        A("> 왜 틀렸나: %s" % d["why_it_was_wrong"])
        A(">")
        A("> 조치: %s" % d["fix"])
        A(">")
        A("> 교훈: %s" % d["lesson"])
        A("")
    A("## 5. 변이 검사 (%d/%d 잡힘, 원복 후 %d fixture 재통과: %s)"
      % (p["mutation_results"]["caught"], p["mutation_results"]["total"],
         p["mutation_results"]["restored_fixture_count"],
         p["mutation_results"]["restored_after_mutation"]))
    A("")
    A("| id | 대상 | 고의 결함 | 잡혔나 | 실패 fixture |")
    A("|---|---|---|---|---|")
    for m in p["mutation_results"]["cases"]:
        A("| %s | `%s` | %s | %s | %d |"
          % (m["mutation_id"], m["target_primitive"], m["mutation"],
             "yes" if m["caught"] else "**NO**", m["n_fixtures_failed_under_mutation"]))
    A("")
    A("## 6. 기존 Lane S fixture 회귀")
    A("")
    reg = p["regression"]
    A("| 묶음 | 통과 | 총계 |")
    A("|---|---|---|")
    A("| positive | %d | %d |" % (reg["positive_passed"], reg["positive_total"]))
    A("| negative | %d | %d |" % (reg["negative_passed"], reg["negative_total"]))
    A("| mutation caught | %d | %d |" % (reg["mutation_caught"], reg["mutation_total"]))
    A("")
    A("기준선 대비: %s" % reg["baseline_comparison"])
    A("")
    A("## 7. 남은 모호성 (%d)" % len(p["remaining_ambiguities"]))
    A("")
    A("R7 이 정하지 않은 것들. **채우지 않았다.**")
    A("")
    for a in p["remaining_ambiguities"]:
        A("### %s — `%s`" % (a["id"], a["variable"]))
        A("")
        A("- 문제: %s" % a["issue"])
        A("- Lane S 처리: %s" % a["lane_s_action"])
        A("- 소유자: %s" % a["owner"])
        A("")
    A("### R7 이 닫은 것")
    A("")
    for c in p["ambiguities_closed_by_r7"]:
        A("- **%s** — %s" % (c["id"], c["resolution"]))
    A("")
    A("## 8. Limitation")
    A("")
    A(p["limitation"])
    A("")
    A("## 9. 재현")
    A("")
    A("```bash")
    A("/home/sieg/projects-wsl/ProjectFinal/.venv/bin/python \\")
    A("  %s/tools/v3_harness/lane_s_spatial_control_reveal.py" % RD)
    A("```")
    A("")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(L))


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
            "and AMB-S14..S17 recording what T-A-V3-STEP1-003 R7 left open after it closed "
            "AMB-S01/S02/S03. entry_zone derivation is no longer blocked — see r7_convergence."
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

    # --- R7 convergence: the pre-existing suite above is the regression baseline ---------
    regression = {
        "what": "The Lane S fixture suite as it stood before the R7 convergence, re-run unchanged.",
        "baseline_at_base_sha": {"positive": 35, "negative": 21, "mutation_caught": 10,
                                 "source": "LANE_S_HARNESS.json at 21d7c9e4"},
        "positive_passed": pos_pass, "positive_total": len(pos),
        "negative_passed": neg_pass, "negative_total": len(neg),
        "mutation_caught": mut_caught, "mutation_total": len(mutations),
        "restored_after_mutation": restored_ok,
        "total_passed": pos_pass + neg_pass, "total": len(pos) + len(neg),
        "all_passed": all_green,
    }
    regression["baseline_comparison"] = (
        "unchanged — positive %d/%d, negative %d/%d, mutation %d/%d, identical to the pre-R7 baseline"
        % (pos_pass, len(pos), neg_pass, len(neg), mut_caught, len(mutations))
        if (pos_pass == 35 and len(pos) == 35 and neg_pass == 21 and len(neg) == 21
            and mut_caught == 10 and len(mutations) == 10)
        else "CHANGED from the pre-R7 baseline (35 positive / 21 negative / 10 mutations) — "
             "observed positive %d/%d, negative %d/%d, mutation %d/%d"
             % (pos_pass, len(pos), neg_pass, len(neg), mut_caught, len(mutations)))

    r7 = build_r7_convergence(regression)
    payload["r7_convergence"] = {
        "verdict": r7["verdict"],
        "artifact": "results/harness/lane_s/LANE_S_R7_CONVERGENCE.json",
        "note": "entry_zone derivation is no longer refused: T-A-V3-STEP1-003 R7 froze the cuts. "
                "AMB-S01/S02/S03 above carry their resolutions; AMB-S14..S17 are what R7 left open.",
    }

    jpath = os.path.join(OUT_DIR, "LANE_S_HARNESS.json")
    with open(jpath, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=2)

    _write_findings(payload, os.path.join(OUT_DIR, "LANE_S_FINDINGS.md"))

    r7path = os.path.join(OUT_DIR, "LANE_S_R7_CONVERGENCE.json")
    with open(r7path, "w", encoding="utf-8") as fh:
        json.dump(r7, fh, ensure_ascii=False, indent=2)
    _write_r7_findings(r7, os.path.join(OUT_DIR, "LANE_S_R7_FINDINGS.md"))

    print("verdict=%s positive=%d/%d negative=%d/%d mutation_caught=%d/%d restored=%s"
          % (verdict, pos_pass, len(pos), neg_pass, len(neg), mut_caught, len(mutations), restored_ok))
    print("r7_verdict=%s boundary=%d/%d precedence=%d/%d r7_mutation_caught=%d/%d "
          "policy_diverge=%d/%d transcription_match=%s"
          % (r7["verdict"],
             r7["boundary_fixtures"]["passed"], r7["boundary_fixtures"]["total"],
             r7["precedence_fixtures"]["passed"], r7["precedence_fixtures"]["total"],
             r7["mutation_results"]["caught"], r7["mutation_results"]["total"],
             r7["policy_comparison"]["n_diverge"], r7["policy_comparison"]["n_points"],
             r7["r7_transcription_check"].get("verbatim_match")))
    print("wrote %s" % jpath)
    print("wrote %s" % r7path)
    r7_green = r7["verdict"] in ("CONVERGED", "CONVERGED_WITH_AMBIGUITY")
    return 0 if (all_green and r7_green) else 1


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
        if a.get("resolution"):
            A("- **해소: %s** (출처 `%s`)" % (a["resolution"], a["resolution_source"]))
        A("")
    A("**AMB-S01/S02/S03 은 닫혔다.** 이 셋은 `entry_zone` 에 x/y 절단값이 없다는 문제였고,")
    A("`D-V3-FINDING-007` 로 올라가 A 가 `T-A-V3-STEP1-003` R7 로 확정했다. 그래서 Lane S 는 이제")
    A("좌표에서 zone 을 **유도한다** — `classify_zone_r7()`. 확정은 관측 0건 상태에서 이뤄졌다.")
    A("자세한 내용은 `LANE_S_R7_CONVERGENCE.json` / `LANE_S_R7_FINDINGS.md`.")
    A("")
    A("절단값이 없던 시절 fixture 에서 쓰던 1/3 등분 정책(`FIXTURE_ONLY_NOT_SSOT`)은 **그대로 뒀다**.")
    A("R7 정책과 같은 입력에서 같은 답을 주는지 확인하는 대조군이며, 여전히 fixture 밖에서 쓰면 예외를 던진다.")
    A("남은 모호성은 AMB-S04~S13 과, R7 이 새로 남긴 AMB-S14~S17 이다.")
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
