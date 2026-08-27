"""c_flow_derive — Claude C independent derivation & statistics library for Flow marts.

Scope (13_PROMPT_C_v3.0): C recomputes every derived quantity from the raw
sequences / labels / geometry WITHOUT using B's code or numbers. This module is
pure python (stdlib only) so it can run identically at GATE 1 (synthetic) and
GATE 3 (final 50).

Authority: SSOTV3/04_FLOW_CODEBOOK_v3.0.md (04), 05_ANALYSIS_PLAN_v3.0.md (05),
02_DATA_SCHEMA_v3.0.md (02), 00_SSOT_v3.0_CROSS_SERVICE_FLOW.md (00).

Every point where the SSOT leaves a rule under-specified is closed here by a
PRE-REGISTERED C CHOICE. Each such choice is a module-level constant (or a
keyword flag) and is listed in README.md so it can be frozen before any real
data is seen. Where a choice materially changes a number, ``derive`` reports
BOTH values (primary + alternative) so the choice is auditable, never hidden.
"""
from __future__ import annotations

import math
import re
import unicodedata
from collections import Counter
from collections.abc import Iterable, Mapping, Sequence
from typing import Any

# ============================================================================
# 04 §2 canonical tokens
# ============================================================================

CANONICAL_TOKENS: frozenset[str] = frozenset({
    "OPEN_GLOBAL_MENU", "OPEN_LOCAL_MENU", "SWITCH_TAB", "EXPAND_ACCORDION",
    "SELECT_CATEGORY", "SELECT_FUNCTION", "INPUT_QUERY", "SELECT_ORIGIN",
    "SELECT_DESTINATION", "SELECT_DATE", "SUBMIT_QUERY", "SELECT_RESULT",
    "OPEN_ITEM_DETAIL", "OPEN_PLACE_DETAIL", "DISMISS_OBSTRUCTION", "AUTH_GATE",
    "ENDPOINT_REACHED", "ABSTAIN",
})

# ---- 04 §5 activation_depth: "state-changing activation token 수. scroll/typing/passive/dismiss 제외."
# T-A-V3-STEP1-006 canonical_18_classification (A ruling): activation_depth = tokens that are intentional
# control activations causing a state transition (three tests: intentional · control · state transition).
#   IN  : OPEN_GLOBAL_MENU OPEN_LOCAL_MENU SWITCH_TAB EXPAND_ACCORDION SELECT_CATEGORY SELECT_FUNCTION
#         SUBMIT_QUERY SELECT_RESULT OPEN_ITEM_DETAIL OPEN_PLACE_DETAIL
#   OUT : INPUT_QUERY (typing; flow_step_count only) DISMISS_OBSTRUCTION AUTH_GATE (encountered state;
#         flow_step_count only) ENDPOINT_REACHED ABSTAIN
#   CONDITIONAL: SELECT_ORIGIN SELECT_DESTINATION SELECT_DATE — IN iff the input means used was a control
#         (DROPDOWN / MAP_PAN / picker / calendar), OUT if FREE_TEXT typing; decided per observation via
#         fixture_input_mode (Δ8-R5); MIXED → the means actually used for that token.
ACTIVATION_CORE: frozenset[str] = frozenset({
    "OPEN_GLOBAL_MENU", "OPEN_LOCAL_MENU", "SWITCH_TAB", "EXPAND_ACCORDION",
    "SELECT_CATEGORY", "SELECT_FUNCTION", "SELECT_RESULT",
    "OPEN_ITEM_DETAIL", "OPEN_PLACE_DETAIL",
})
# C-1 (CONFIRMED_BY_A, T-A-V3-STEP1-006): SUBMIT_QUERY executes a control and changes page state → activation.
#   The flip (submit_is_activation=False) and activation_depth_excl_submit are kept as sensitivity only.
SUBMIT_IS_ACTIVATION_DEFAULT: bool = True
ACTIVATION_IN_TOKENS: frozenset[str] = ACTIVATION_CORE | {"SUBMIT_QUERY"}
# C-2 SUPERSEDED_BY_A_STEP1-006: form-intent tokens are no longer blanket-excluded. INPUT_QUERY is OUT
#   (typing); the three below are CONDITIONAL on the input means actually used.
CONDITIONAL_ACTIVATION_TOKENS: frozenset[str] = frozenset({"SELECT_ORIGIN", "SELECT_DESTINATION", "SELECT_DATE"})
ACTIVATION_OUT_TOKENS: frozenset[str] = frozenset({
    "INPUT_QUERY", "DISMISS_OBSTRUCTION", "AUTH_GATE", "ENDPOINT_REACHED", "ABSTAIN",
})
# FORM_INTENT_TOKENS is still the "typing / value-entry" class for flow_step_count and task-body detection.
FORM_INTENT_TOKENS: frozenset[str] = frozenset({"INPUT_QUERY"}) | CONDITIONAL_ACTIVATION_TOKENS
# fixture_input_mode (Δ8-R5) values that mean "a control had to be activated" vs "typed".
# C reading: PICKER / CALENDAR are accepted as aliases of the control class (A names picker/calendar as
# examples); MIXED at token level is unresolved (the caller must pass the means actually used); OTHER is
# unresolved. Unresolved → token is OUT of the primary activation_depth and a violation is recorded.
CONTROL_INPUT_MODES: frozenset[str] = frozenset({"DROPDOWN", "MAP_PAN", "PICKER", "CALENDAR"})
TYPING_INPUT_MODES: frozenset[str] = frozenset({"FREE_TEXT"})
ACTIVATION_RULE_ID = "T-A-V3-STEP1-006 canonical_18_classification (A ruling; C-1 confirmed, C-2 superseded)"
# ---- 04 §5 menu_dependency / nav_container_depth: "OPEN/REVEAL 계열 token"
# C CHOICE C-3: reveal = OPEN_GLOBAL_MENU, OPEN_LOCAL_MENU, EXPAND_ACCORDION (the three named in 04 §5).
#   SWITCH_TAB is a view switch, not a container reveal → NOT reveal (menu_dependency_incl_tab reported as alt).
REVEAL_TOKENS: frozenset[str] = frozenset({"OPEN_GLOBAL_MENU", "OPEN_LOCAL_MENU", "EXPAND_ACCORDION"})
REVEAL_TOKENS_INCL_TAB: frozenset[str] = REVEAL_TOKENS | {"SWITCH_TAB"}
# ---- 04 §5 flow_step_count: "task-intent token 수. typing/submit/auth encounter 포함, scroll/passive 제외."
# C-4 CONFIRMED_BY_A_GAP03 (T-A-V3-STEP1-012 GAP_03): task-intent = every canonical token except
#   DISMISS_OBSTRUCTION (obstruction, not task), ENDPOINT_REACHED (a measurement marker, not something the
#   user did — 04 §5 does not name it) and ABSTAIN (judgement withheld, not an act). AUTH_GATE IS included
#   (04 §5 names "auth encounter" explicitly). Asymmetric with activation_depth (Δ9 excludes both) by SSOT text.
TASK_INTENT_TOKENS: frozenset[str] = (ACTIVATION_CORE | FORM_INTENT_TOKENS | {"SUBMIT_QUERY", "AUTH_GATE"})
# ---- nav_container_depth anchor ("task control 노출 전"):
# C CHOICE C-5 / P-11 (C-decided rule, GATE1_PREREGISTRATION_C reconciliation): the task control is
#   considered exposed at the FIRST token that acts on the task control itself — SELECT_FUNCTION or, when a
#   flow never names one, the first task-body token (INPUT_QUERY / SELECT_ORIGIN / SELECT_DESTINATION /
#   SELECT_DATE / SUBMIT_QUERY / SELECT_RESULT / OPEN_ITEM_DETAIL / OPEN_PLACE_DETAIL). SELECT_CATEGORY is
#   category navigation, not the task control → not an anchor. Fallback: if none of these occurs but
#   AUTH_GATE does, AUTH_GATE is the anchor (the gate is where the path stopped exposing controls;
#   nav_anchor_action_token="AUTH_GATE"). Otherwise reveals before the terminal are counted, nav_anchor_found=False.
TASK_CONTROL_ANCHOR_TOKENS: frozenset[str] = frozenset({
    "SELECT_FUNCTION", "INPUT_QUERY", "SELECT_ORIGIN", "SELECT_DESTINATION", "SELECT_DATE",
    "SUBMIT_QUERY", "SELECT_RESULT", "OPEN_ITEM_DETAIL", "OPEN_PLACE_DETAIL",
})
NAV_ANCHOR_FALLBACK_TOKENS: frozenset[str] = frozenset({"AUTH_GATE"})
# ---- auth_gate_stage positions (00 §6 / 04 §4): primary rule = T-A-V3-STEP1-011 P-13/P-14 (TASK_SPECIFIC_TOKENS
# below, near auth_gate_stage_from_sequence). C-6's finer split (select vs body) is kept only for the
# declared sensitivity fields; TASK_SELECT_TOKENS / TASK_BODY_TOKENS remain for nav/anchor logic.
TASK_SELECT_TOKENS: frozenset[str] = frozenset({"SELECT_FUNCTION", "SELECT_CATEGORY"})
TASK_BODY_TOKENS: frozenset[str] = FORM_INTENT_TOKENS | {
    "SUBMIT_QUERY", "SELECT_RESULT", "OPEN_ITEM_DETAIL", "OPEN_PLACE_DETAIL",
}
TERMINAL_TOKENS: frozenset[str] = frozenset({"ENDPOINT_REACHED", "AUTH_GATE", "ABSTAIN"})

# ---- entry_zone thresholds — T-A-V3-STEP1-003 R7 (A ruling, supersedes C-7)
# y bands:  y < 1/3 → TOP · 1/3 ≤ y < 2/3 → MID · y ≥ 2/3 → BOTTOM
# x split ONLY within TOP:  x < 1/3 → TOP_LEFT · 1/3 ≤ x < 2/3 → TOP_CENTER · x ≥ 2/3 → TOP_RIGHT
# MID / BOTTOM keep no x split (04 codebook has no MID_LEFT-type values). All boundaries are [a, b).
# Structural overrides FLOATING (position fixed/sticky) and DRAWER (inside a reveal-requiring container)
# take precedence over geometry; DRAWER over FLOATING when both. x/y_norm are always retained.
# The former provisional C-7 values (0.15 / 0.85, x-centre inclusive) are SUPERSEDED and no longer used.
ZONE_TOP_Y: float = 1.0 / 3.0        # y <  1/3 → TOP band
ZONE_BOTTOM_Y: float = 2.0 / 3.0     # y >= 2/3 → BOTTOM band
ZONE_X_LEFT: float = 1.0 / 3.0       # x <  1/3 → TOP_LEFT
ZONE_X_RIGHT: float = 2.0 / 3.0      # x >= 2/3 → TOP_RIGHT
ZONE_RULE_ID = "T-A-V3-STEP1-003 R7 (A ruling, supersedes C-7)"

PSEUDO_REPLICATION_GUARD = "pairs are cells, not independent n"
# T-A-V3-STEP1-012 GAP_04 (extends Δ10-R13 to every variable): an unobserved NUMERIC derived value is None
# (never 0); an unobserved CATEGORICAL value is the explicit string UNDETERMINED / NOT_OBSERVED (never "");
# a row never mixes null representations. family_summary excludes None from n and REFUSES "" values.
NULL_CONVENTION_ID = "T-A-V3-STEP1-012 GAP_04 (numeric unobserved = None, categorical unobserved = UNDETERMINED/NOT_OBSERVED)"
UNOBSERVED_CATEGORICAL: frozenset[str] = frozenset({"UNDETERMINED", "NOT_OBSERVED"})

# ---- T-A-V3-STEP1-003 R3: task_role isolation
TASK_ROLES: frozenset[str] = frozenset({"PRIMARY", "SECONDARY_REPEATED"})
PRIMARY_FILTER_CONDITION = "task_role == 'PRIMARY'"   # literal string emitted by every aggregate

# ---- T-A-V3-STEP1-003 R2: AUTH_GATE terminal semantics per family
# F1's endpoint_contract names AUTH_GATE as the endpoint → counts as endpoint reached.
# F2..F5: AUTH_GATE is an evidence-bearing terminal that is NOT endpoint reached.
AUTH_GATE_IS_ENDPOINT_BY_FAMILY: dict[str, bool] = {"F1": True, "F2": False, "F3": False, "F4": False, "F5": False}
# Which denominator each summarised variable uses (R2 "critical": entry-flow metrics are computed
# regardless of AUTH_GATE; only endpoint-dependent metrics use the flow-evaluable n).
ENTRY_STRUCTURE_VARS: frozenset[str] = frozenset({
    "entry_zone", "entry_x_norm", "entry_y_norm", "entry_control_type", "control_type",
    "visible_label_text", "accessible_name", "label_relation",
    "menu_dependency", "menu_dependency_incl_tab", "nav_container_depth", "nav_container_type",
    "nav_anchor_found", "auth_gate_stage", "auth_gate_stage_alt_terminal_is_endpoint",
    "forced_dismissal_count", "first_visible_scroll_state", "endpoint_status", "terminal_reason",
    "fixture_input_mode",
})
ENDPOINT_DEPENDENT_VARS: frozenset[str] = frozenset({
    "activation_depth", "activation_depth_excl_submit", "activation_depth_conditional_all_in",
    "activation_depth_conditional_all_out", "flow_step_count", "endpoint_reached",
    "post_endpoint_sequence_length",
})
DENOMINATOR_NAMES = ("entry_structure_n", "endpoint_dependent_n")

# ---- T-A-V3-STEP1-003 R4: replacement reasons allowed in the denominator chain (Director's 4)
REPLACEMENT_REASONS: frozenset[str] = frozenset({
    "APP_REQUIRED_EXCLUDE", "NO_PUBLIC_MOBILE_WEB", "DEAD_OR_INVALID_URL", "PRECHECK_EVIDENCE_DEFECT",
})
REPLACEMENT_ITEM_KEYS = ("target_id", "reason", "reserve_rank", "decided_at", "decided_by")

# ---- T-A-V3-STEP1-003 R6 Q8: AUTH_GATE / ABSTAIN exist in two layers (action_token, endpoint_status).
# They may only be emitted under a qualifying key, never as bare values in a mixed list / free text.
Q8_AMBIGUOUS_VALUES: frozenset[str] = frozenset({"AUTH_GATE", "ABSTAIN"})
Q8_QUALIFYING_KEYS: frozenset[str] = frozenset({
    "endpoint_status", "action_token", "task_flow_sequence", "experienced_flow_sequence",
    "signature", "signature_counts",      # a signature is by construction a joined action_token sequence
})
_Q8_BARE_RE = re.compile(r"(?<!endpoint_status=)(?<!action_token=)\b(AUTH_GATE|ABSTAIN)\b")

Tokens = Sequence[str]


# ============================================================================
# token classification
# ============================================================================

def resolve_input_mode(input_mode: str | None) -> str:
    """T-A-V3-STEP1-006 CONDITIONAL rule: map a fixture_input_mode (Δ8-R5) to IN / OUT / UNRESOLVED."""
    if input_mode is None:
        return "UNRESOLVED"
    m = str(input_mode).strip().upper()
    if m in CONTROL_INPUT_MODES:
        return "IN"
    if m in TYPING_INPUT_MODES:
        return "OUT"
    return "UNRESOLVED"       # MIXED (needs the means actually used), OTHER, unknown


def classify_token(token: str, *, submit_is_activation: bool = SUBMIT_IS_ACTIVATION_DEFAULT,
                   input_mode: str | None = None) -> dict[str, Any]:
    """Classify one canonical token (04 §2) into the derivation classes of 04 §5.

    Returns {state_changing_activation, task_intent, reveal, dismiss, auth, endpoint,
             conditional, input_mode, activation_decision}.
    Raises ValueError for a non-canonical token (scroll / passive wait are NOT tokens in
    04 §2; they are measured elsewhere — 04 §4 first_visible_scroll_state).

    activation_depth membership follows T-A-V3-STEP1-006 canonical_18_classification:
    IN = ACTIVATION_IN_TOKENS (incl. SWITCH_TAB and SUBMIT_QUERY — C-1 CONFIRMED_BY_A);
    OUT = INPUT_QUERY / DISMISS_OBSTRUCTION / AUTH_GATE / ENDPOINT_REACHED / ABSTAIN;
    CONDITIONAL = SELECT_ORIGIN / SELECT_DESTINATION / SELECT_DATE → IN iff ``input_mode`` is a control
    means (DROPDOWN / MAP_PAN / picker / calendar), OUT if FREE_TEXT, UNRESOLVED (counted OUT, flagged)
    if missing / MIXED / OTHER. C-2 (blanket form exclusion) is SUPERSEDED by this rule.
    Other C choices applied: C-3 (reveal set — SWITCH_TAB is IN activation_depth but is NOT a reveal
    token for menu_dependency), C-4 (task-intent set).
    """
    if token not in CANONICAL_TOKENS:
        raise ValueError(f"non-canonical token: {token!r} (04 §2)")
    conditional = token in CONDITIONAL_ACTIVATION_TOKENS
    decision: str
    if token == "SUBMIT_QUERY":
        decision = "IN" if submit_is_activation else "OUT_SENSITIVITY"
    elif token in ACTIVATION_CORE:
        decision = "IN"
    elif conditional:
        decision = resolve_input_mode(input_mode)
    else:
        decision = "OUT"
    return {
        "state_changing_activation": decision == "IN",
        "task_intent": token in TASK_INTENT_TOKENS,
        "reveal": token in REVEAL_TOKENS,
        "dismiss": token == "DISMISS_OBSTRUCTION",
        "auth": token == "AUTH_GATE",
        "endpoint": token == "ENDPOINT_REACHED",
        "conditional": conditional,
        "input_mode": (str(input_mode).strip().upper() if input_mode is not None else None) if conditional else None,
        "activation_decision": decision,
    }


def _input_modes_by_index(input_modes: Any, task: Sequence[str]) -> dict[int, str | None]:
    """Normalise the ``input_modes`` argument of derive() to {task_index: fixture_input_mode}.

    Accepts: None; a single str (row-level fixture_input_mode applied to every conditional token — only
    meaningful when it is not MIXED); a Mapping[int, str] keyed by index in the cleaned task_flow_sequence;
    or a Sequence aligned 1:1 with the task_flow_sequence (None for non-conditional positions).
    """
    if input_modes is None:
        return {}
    if isinstance(input_modes, str):
        return {i: input_modes for i, t in enumerate(task) if t in CONDITIONAL_ACTIVATION_TOKENS}
    if isinstance(input_modes, Mapping):
        return {int(k): (None if v is None else str(v)) for k, v in input_modes.items()}
    seq = list(input_modes)
    if len(seq) != len(task):
        raise ValueError(f"input_modes sequence length {len(seq)} != task_flow length {len(task)}")
    return {i: (None if v is None else str(v)) for i, v in enumerate(seq)}


def _clean(seq: Iterable[str] | str | None, *, drop_noncanonical: bool) -> tuple[list[str], list[str]]:
    """Normalise a sequence (list or 'A > B' string) to a list of canonical tokens."""
    if seq is None:
        return [], []
    if isinstance(seq, str):
        seq = [t for t in re.split(r"\s*>\s*", seq.strip()) if t]
    toks = [str(t).strip().upper() for t in seq]
    dropped = [t for t in toks if t not in CANONICAL_TOKENS]
    if dropped and not drop_noncanonical:
        raise ValueError(f"non-canonical tokens {dropped} (04 §2); pass drop_noncanonical=True to drop")
    return [t for t in toks if t in CANONICAL_TOKENS], dropped


def _before_terminal(seq: list[str]) -> list[str]:
    """Tokens strictly before the first terminal token (ENDPOINT_REACHED / AUTH_GATE / ABSTAIN);
    whole sequence if no terminal (C choice: 'endpoint 전' == whole path when endpoint never observed)."""
    for i, t in enumerate(seq):
        if t == "ENDPOINT_REACHED":
            return seq[:i]
    return seq


# ============================================================================
# derived variables (04 §5, 02 §4 fact_flow_observation)
# ============================================================================

AUTH_GATE_STAGES: frozenset[str] = frozenset({
    "NONE", "UNDETERMINED", "BEFORE_TASK_DISCOVERY", "AFTER_TASK_SELECT", "AT_ENDPOINT",
})
# T-A-V3-STEP1-011 P-13/P-14 (A accepted C's reading; operational rule now fixed): the task-specific tokens.
# General navigation (OPEN_GLOBAL_MENU · OPEN_LOCAL_MENU · SWITCH_TAB · EXPAND_ACCORDION · DISMISS_OBSTRUCTION)
# does NOT express task intent — an AUTH_GATE after only those is BEFORE_TASK_DISCOVERY.
TASK_SPECIFIC_TOKENS: frozenset[str] = frozenset({
    "SELECT_CATEGORY", "SELECT_FUNCTION", "INPUT_QUERY", "SELECT_ORIGIN", "SELECT_DESTINATION", "SELECT_DATE",
    "SUBMIT_QUERY", "SELECT_RESULT", "OPEN_ITEM_DETAIL", "OPEN_PLACE_DETAIL",
})
AUTH_STAGE_RULE_ID = "T-A-V3-STEP1-011 P-13/P-14 (A ruling: single operational rule; C-6 task-body sub-rule dropped)"


def auth_gate_stage_from_sequence(seq: Tokens, *, terminal_auth_is_endpoint: bool = False,
                                  endpoint_reached: bool | None = None,
                                  reveal_is_discovery: bool = False,
                                  endpoint_surface_rendered_before_gate: bool | None = None) -> str:
    """auth_gate_stage (04 §4, 00 §6, 03 §7) — operational rule fixed by T-A-V3-STEP1-011 P-13/P-14.

    NONE                  — no AUTH_GATE **and the path was fully observed** (ENDPOINT_REACHED present, or
                            ``endpoint_reached=True`` passed as explicit evidence). T-A-V3-STEP1-007 R13:
                            NONE is an affirmative claim that requires evidence.
    UNDETERMINED          — no AUTH_GATE but the path is incomplete (no terminal token), ABSTAIN, or evidence
                            defect (R13: never write NONE for an unobserved gate). ``endpoint_reached=False``
                            forces UNDETERMINED even if the sequence looks complete.
    BEFORE_TASK_DISCOVERY — no TASK_SPECIFIC token precedes the first AUTH_GATE: only general navigation
                            (OPEN_GLOBAL_MENU / OPEN_LOCAL_MENU / SWITCH_TAB / EXPAND_ACCORDION /
                            DISMISS_OBSTRUCTION) or nothing at all.
    AFTER_TASK_SELECT     — at least one TASK_SPECIFIC token precedes AUTH_GATE and the endpoint contract is
                            not yet met. P-13: ``OPEN_GLOBAL_MENU > SELECT_CATEGORY > AUTH_GATE`` → here.
                            P-14: ``SELECT_FUNCTION > INPUT_QUERY > SUBMIT_QUERY > AUTH_GATE`` (submit goes
                            straight to login, no result surface) → here, NOT AT_ENDPOINT.
    AT_ENDPOINT           — the endpoint surface rendered WITHOUT auth and the gate hit on accessing its
                            content. Not derivable from tokens alone: requires the explicit observation
                            ``endpoint_surface_rendered_before_gate=True``. Default None → position rule.
    Declared sensitivities (both always reported by derive(); neither is primary):
      ``terminal_auth_is_endpoint=True``  literal reading — any terminal AUTH_GATE after a task-specific
                                          token is AT_ENDPOINT (former C-6 sub-rule, rejected by P-14).
      ``reveal_is_discovery=True``        a reveal token already counts as task discovery.
    """
    seq = list(seq)
    if "AUTH_GATE" not in seq:
        if endpoint_reached is False or "ABSTAIN" in seq:
            return "UNDETERMINED"
        if endpoint_reached is True or (seq and seq[-1] == "ENDPOINT_REACHED"):
            return "NONE"
        return "UNDETERMINED"
    i = seq.index("AUTH_GATE")
    before = seq[:i]
    task_specific = TASK_SPECIFIC_TOKENS | (REVEAL_TOKENS if reveal_is_discovery else frozenset())
    if not any(t in task_specific for t in before):
        return "BEFORE_TASK_DISCOVERY"
    if endpoint_surface_rendered_before_gate is True:
        return "AT_ENDPOINT"
    if terminal_auth_is_endpoint and i == len(seq) - 1:
        return "AT_ENDPOINT"
    return "AFTER_TASK_SELECT"


def endpoint_status_from_sequence(seq: Tokens) -> str:
    """endpoint_status (04 §4) as far as the sequence alone can tell.

    REACHED if ENDPOINT_REACHED present; else AUTH_GATE if AUTH_GATE present; else ABSTAIN if ABSTAIN
    present; else UNRESOLVED_FROM_SEQUENCE (PUBLIC_WEB_UNOBSERVABLE / APP_REQUIRED / EVIDENCE_DEFECT /
    BLOCKED are evidence-level statuses that a sequence cannot distinguish — C compares B's value
    against this and flags REACHED/AUTH_GATE/ABSTAIN mismatches only).
    """
    seq = list(seq)
    if "ENDPOINT_REACHED" in seq:
        return "REACHED"
    if "AUTH_GATE" in seq:
        return "AUTH_GATE"
    if "ABSTAIN" in seq:
        return "ABSTAIN"
    return "UNRESOLVED_FROM_SEQUENCE"


def derive(task_flow_sequence: Tokens | str, experienced_flow_sequence: Tokens | str | None = None, *,
           submit_is_activation: bool = SUBMIT_IS_ACTIVATION_DEFAULT,
           drop_noncanonical: bool = False,
           input_modes: Any = None,
           endpoint_surface_rendered_before_gate: bool | None = None) -> dict[str, Any]:
    """Recompute every derived field of 02 §4 fact_flow_observation from the two raw sequences (00 §7).

    activation_depth        04 §5 + T-A-V3-STEP1-006 canonical_18_classification — count of tokens that are
                             intentional control activations causing a state transition (IN set incl.
                             SWITCH_TAB and SUBMIT_QUERY; INPUT_QUERY/DISMISS/AUTH_GATE/ENDPOINT/ABSTAIN OUT;
                             SELECT_ORIGIN/SELECT_DESTINATION/SELECT_DATE CONDITIONAL on ``input_modes``).
    input_modes             per-token fixture_input_mode for the conditional tokens: a str (row-level mode,
                             applied to all conditional tokens), {task_index: mode}, or a list aligned with
                             task_flow. Control means (DROPDOWN/MAP_PAN/picker/calendar) → IN; FREE_TEXT → OUT;
                             missing/MIXED/OTHER → UNRESOLVED (counted OUT in the primary value + violation).
    depth_conditional_tokens  STEP1-006 "record": one entry per conditional token in task_flow with its index,
                             fixture_input_mode, decision (IN/OUT/UNRESOLVED) and basis.
    activation_depth_conditional_all_in / _all_out  bounds if every conditional token were IN / OUT.
    endpoint_surface_rendered_before_gate  T-A-V3-STEP1-011 P-14: explicit observation that the endpoint
                             surface rendered without auth and the gate hit on its content → AT_ENDPOINT.
                             None (default) → auth_gate_stage by the token-position rule.
    flow_step_count         04 §5 — count of task-intent tokens in task_flow (C-4).
    menu_dependency         04 §5 — 1 iff a reveal token (C-3) occurs before ENDPOINT_REACHED (or anywhere
                                     if endpoint never reached).
    nav_container_depth     04 §5 — reveal tokens before the first task-control anchor token (C-5);
                                     if no anchor, all reveals before terminal and nav_anchor_found=False.
    forced_dismissal_count  04 §4 — DISMISS_OBSTRUCTION count in experienced_flow (04 §3).
    auth_gate_stage         04 §4 / 00 §6 — see auth_gate_stage_from_sequence (C-6), alt reported.
    endpoint_status         04 §4 — see endpoint_status_from_sequence.
    sequence_consistent     04 §3 — experienced minus DISMISS_OBSTRUCTION must equal task_flow.
    flow_evaluable          05 §6 — False for an ABSTAIN sequence; then all flow-derived fields are None (C-9).
    violations              list of codebook-contract violations found in the raw sequences (never raises).
    """
    task, dropped_t = _clean(task_flow_sequence, drop_noncanonical=drop_noncanonical)
    if experienced_flow_sequence is None:
        exp, dropped_e = list(task), []
    else:
        exp, dropped_e = _clean(experienced_flow_sequence, drop_noncanonical=drop_noncanonical)

    violations: list[str] = []
    if "DISMISS_OBSTRUCTION" in task:
        violations.append("task_flow contains DISMISS_OBSTRUCTION (04 §3: task_flow excludes dismissals)")
    exp_wo_dismiss = [t for t in exp if t != "DISMISS_OBSTRUCTION"]
    consistent = exp_wo_dismiss == task
    if not consistent:
        violations.append("experienced_flow minus DISMISS_OBSTRUCTION != task_flow (04 §3)")
    for name, s in (("task_flow", task), ("experienced_flow", exp)):
        for i, t in enumerate(s):
            if t in TERMINAL_TOKENS and i != len(s) - 1:
                # Q8: the token is named with its layer (action_token=...), never bare.
                violations.append(f"{name}: terminal action_token={t} at index {i} is not last "
                                  f"(00 §6 action_token=AUTH_GATE is terminal / 04 §2)")
                break

    modes = _input_modes_by_index(input_modes, task)
    per_tok = [classify_token(t, submit_is_activation=submit_is_activation, input_mode=modes.get(i))
               for i, t in enumerate(task)]
    cls = {t: classify_token(t, submit_is_activation=submit_is_activation) for t in set(task)}
    activation_depth = sum(1 for c in per_tok if c["state_changing_activation"])
    activation_excl_submit = sum(1 for i, t in enumerate(task)
                                 if classify_token(t, submit_is_activation=False, input_mode=modes.get(i))["state_changing_activation"])
    n_conditional = sum(1 for c in per_tok if c["conditional"])
    n_conditional_in = sum(1 for c in per_tok if c["conditional"] and c["activation_decision"] == "IN")
    activation_all_in = activation_depth + (n_conditional - n_conditional_in)
    activation_all_out = activation_depth - n_conditional_in
    depth_conditional_tokens = []
    for i, (t, c) in enumerate(zip(task, per_tok, strict=True)):
        if not c["conditional"]:
            continue
        basis = {"IN": "control means (DROPDOWN/MAP_PAN/picker/calendar) had to be activated",
                 "OUT": "FREE_TEXT typing — flow_step_count only",
                 "UNRESOLVED": "fixture_input_mode missing/MIXED/OTHER — counted OUT in primary, flagged"}[c["activation_decision"]]
        depth_conditional_tokens.append({"index": i, "token": t, "fixture_input_mode": c["input_mode"],
                                         "decision": c["activation_decision"], "basis": basis,
                                         "rule": "T-A-V3-STEP1-006 CONDITIONAL"})
        if c["activation_decision"] == "UNRESOLVED":
            violations.append(f"task_flow: conditional token {t} at index {i} has no resolved fixture_input_mode="
                              f"{c['input_mode']} (T-A-V3-STEP1-006: pass the means actually used)")
    flow_step_count = sum(1 for t in task if cls[t]["task_intent"])

    pre_end = _before_terminal(task)
    menu_dependency = int(any(t in REVEAL_TOKENS for t in pre_end))
    menu_dependency_incl_tab = int(any(t in REVEAL_TOKENS_INCL_TAB for t in pre_end))

    # C-5 / P-11: first anchor token; AUTH_GATE is the fallback anchor when no task control ever appears.
    anchor_idx = next((i for i, t in enumerate(task) if t in TASK_CONTROL_ANCHOR_TOKENS), None)
    anchor_token: str | None = None
    if anchor_idx is None:
        anchor_idx = next((i for i, t in enumerate(task) if t in NAV_ANCHOR_FALLBACK_TOKENS), None)
    if anchor_idx is None:
        nav_depth = sum(1 for t in pre_end if t in REVEAL_TOKENS)
        anchor_found = False
    else:
        nav_depth = sum(1 for t in task[:anchor_idx] if t in REVEAL_TOKENS)
        anchor_found = True
        anchor_token = task[anchor_idx]
    # alt basis for menu_dependency (open A item "menu_dependency basis"): reveal before the task-control
    # anchor rather than anywhere before the endpoint. Both are reported; C does not pick.
    menu_dependency_alt_before_anchor = int(nav_depth > 0)

    # C CHOICE C-9 + T-A-V3-STEP1-012 GAP_04: an ABSTAIN sequence (04 §2) or an EMPTY sequence (nothing
    # observed; D AMB-X05) is not flow-evaluable (05 §6); its flow-derived numeric fields are None (missing),
    # never 0, and auth_gate_stage is the explicit UNDETERMINED, so family denominators shrink instead of
    # being diluted.
    if not task:
        violations.append("task_flow_sequence is empty: nothing observed (GAP_04: derived numerics None, not 0)")
    flow_evaluable = bool(task) and "ABSTAIN" not in task
    if not flow_evaluable:
        activation_depth = activation_excl_submit = activation_all_in = activation_all_out = None  # type: ignore[assignment]
        flow_step_count = menu_dependency = menu_dependency_incl_tab = nav_depth = None  # type: ignore[assignment]
        menu_dependency_alt_before_anchor = None  # type: ignore[assignment]
    out = {
        "task_flow_sequence": task,
        "experienced_flow_sequence": exp,
        "flow_evaluable": flow_evaluable,
        "activation_depth": activation_depth,
        "activation_depth_excl_submit": activation_excl_submit,
        "activation_depth_conditional_all_in": activation_all_in,
        "activation_depth_conditional_all_out": activation_all_out,
        "depth_conditional_tokens": depth_conditional_tokens,
        "activation_rule": ACTIVATION_RULE_ID,
        "flow_step_count": flow_step_count,
        "menu_dependency": menu_dependency,
        "menu_dependency_incl_tab": menu_dependency_incl_tab,
        "menu_dependency_alt_before_anchor": menu_dependency_alt_before_anchor,
        "nav_container_depth": nav_depth,
        "nav_anchor_found": anchor_found,
        "nav_anchor_action_token": anchor_token,      # Q8: the key names the layer (action_token)
        "forced_dismissal_count": sum(1 for t in exp if t == "DISMISS_OBSTRUCTION"),
        # R13: an ABSTAIN / incomplete path is UNDETERMINED (a category, kept in the denominator), never NONE.
        "auth_gate_stage": (auth_gate_stage_from_sequence(
            task, endpoint_surface_rendered_before_gate=endpoint_surface_rendered_before_gate)
            if flow_evaluable else "UNDETERMINED"),
        "auth_gate_stage_rule": AUTH_STAGE_RULE_ID,
        "endpoint_surface_rendered_before_gate": endpoint_surface_rendered_before_gate,
        "auth_gate_stage_alt_terminal_is_endpoint": (auth_gate_stage_from_sequence(task, terminal_auth_is_endpoint=True)
                                                     if flow_evaluable else "UNDETERMINED"),
        "auth_gate_stage_alt_reveal_is_discovery": (auth_gate_stage_from_sequence(task, reveal_is_discovery=True)
                                                    if flow_evaluable else "UNDETERMINED"),
        "endpoint_status": endpoint_status_from_sequence(task),
        "sequence_consistent": consistent,
        "violations": violations,
        "dropped_noncanonical": sorted(set(dropped_t + dropped_e)),
        "dropped_noncanonical_count": len(dropped_t) + len(dropped_e),
        "submit_is_activation": bool(submit_is_activation),
        "null_convention": NULL_CONVENTION_ID,
    }
    assert_field_qualified(out, "derive")       # R6 Q8 self-check
    return out


# ============================================================================
# label relation (04 §5, 00 §8)
# ============================================================================

_WS = re.compile(r"\s+")


def normalize_label(text: str | None, *, casefold: bool = False) -> str:
    """NFC + whitespace collapse/strip (04 §5). casefold is OFF by default (C choice: 04 §5 says 'exact')."""
    if text is None:
        return ""
    s = unicodedata.normalize("NFC", str(text))
    s = _WS.sub(" ", s).strip()
    return s.casefold() if casefold else s


def normalize_synonym_map(synonym_map: Mapping[str, Any]) -> dict[str, str]:
    """P-30 (C-decided): the frozen synonym map is ``canonical → [forms]`` with the identity implicit
    (a canonical never has to list itself). Returns a flat ``normalised form → canonical`` lookup that
    contains every listed form AND every canonical, so lookups work in both directions
    (form → canonical, canonical → itself, hence canonical ↔ form and form ↔ form).
    The legacy ``form → canonical`` shape (string values) is still accepted; the two may be mixed.
    A form listed under two different canonicals is a map defect → ValueError.
    """
    flat: dict[str, str] = {}

    def put(form: str, canon: str) -> None:
        k = normalize_label(form, casefold=True)
        if not k:
            return
        if k in flat and flat[k] != canon:
            raise ValueError(f"synonym map: form {form!r} listed under both {flat[k]!r} and {canon!r} (P-30)")
        flat[k] = canon

    for key, val in synonym_map.items():
        if isinstance(val, str):                       # legacy form → canonical
            put(key, val)
            put(val, val)
        else:                                          # canonical → [forms]
            canon = str(key)
            put(canon, canon)
            for form in val:
                put(str(form), canon)
    return flat


def label_relation(visible: str | None, accessible: str | None, synonym_map: Mapping[str, Any], *,
                   casefold: bool = False) -> str:
    """label_relation (04 §4/§5): MATCH / SEMANTIC_EQUIV / DIFFERENT / VISIBLE_ONLY / AX_ONLY / NONE.

    Exact after NFC + whitespace normalisation → MATCH. Otherwise, if both normalised forms resolve to the
    same canonical in the EXPLICIT synonym_map (P-30 shape ``canonical → [forms]``, identity implicit,
    bidirectional lookup; legacy ``form → canonical`` also accepted; lookup casefold-insensitive, C-8) →
    SEMANTIC_EQUIV. Embedding similarity is never used (04 §5 prohibits automatic merge).
    """
    v = normalize_label(visible, casefold=casefold)
    a = normalize_label(accessible, casefold=casefold)
    if not v and not a:
        return "NONE"
    if v and not a:
        return "VISIBLE_ONLY"
    if a and not v:
        return "AX_ONLY"
    if v == a:
        return "MATCH"
    # C CHOICE C-8: synonym-map lookup is always casefold-insensitive (case is not a semantic difference);
    # MATCH itself stays case-strict unless casefold=True.
    smap = normalize_synonym_map(synonym_map)
    kv, ka = smap.get(v.casefold()), smap.get(a.casefold())
    if kv is not None and kv == ka:
        return "SEMANTIC_EQUIV"
    return "DIFFERENT"


# ============================================================================
# sequence distance (05 §2 E)
# ============================================================================

def _levenshtein(a: Sequence[str], b: Sequence[str]) -> int:
    if not a:
        return len(b)
    if not b:
        return len(a)
    prev = list(range(len(b) + 1))
    for i, ta in enumerate(a, 1):
        cur = [i]
        for j, tb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ta != tb)))
        prev = cur
    return prev[-1]


def _lcs(a: Sequence[str], b: Sequence[str]) -> int:
    if not a or not b:
        return 0
    prev = [0] * (len(b) + 1)
    for ta in a:
        cur = [0]
        for j, tb in enumerate(b, 1):
            cur.append(prev[j - 1] + 1 if ta == tb else max(prev[j], cur[j - 1]))
        prev = cur
    return prev[-1]


DISTANCE_RULE_ID = "T-A-V3-STEP1-007 R12 (A ruling; C-11 CONFIRMED_BY_A_R12)"
PRIMARY_DISTANCE_KEY = "levenshtein_norm"          # = lev / max(len) — the ONLY key that feeds single-scalar reports


def seq_distance(a: Tokens | str, b: Tokens | str) -> dict[str, float | int]:
    """Token-level (not character-level) distances for 05 §2 E, normalised per T-A-V3-STEP1-007 R12.

    levenshtein_norm      PRIMARY  = lev / max(|a|,|b|)   (0 when both empty)  — single-scalar reports use this only
    levenshtein_norm_sum  stored   = lev / (|a|+|b|)      (0 when both empty)
    yujian_bo             stored   = 2·lev / (|a|+|b|+lev) (0 when both empty) — a true metric (triangle
                          inequality); MUST be reported alongside whenever clustering / MDS is done.
    lcs_sim               = LCS / max(|a|,|b|) (1 when both empty) — C choice; lcs_sim_dice = 2·LCS/(|a|+|b|) alt.
    The ticket's worked pair (['A'] vs ['B']): max 1.0 / sum 0.5 / Yujian-Bo 0.667.
    """
    a, _ = _clean(a, drop_noncanonical=True) if isinstance(a, str) else (list(a), [])
    b, _ = _clean(b, drop_noncanonical=True) if isinstance(b, str) else (list(b), [])
    m = max(len(a), len(b))
    s = len(a) + len(b)
    lev = _levenshtein(a, b)
    lcs = _lcs(a, b)
    return {
        "len_a": len(a), "len_b": len(b),
        "levenshtein": lev,
        "levenshtein_norm": (lev / m) if m else 0.0,
        "levenshtein_norm_sum": (lev / s) if s else 0.0,
        "yujian_bo": (2 * lev / (s + lev)) if (s + lev) else 0.0,
        "primary_distance": PRIMARY_DISTANCE_KEY,
        "lcs_len": lcs,
        "lcs_sim": (lcs / m) if m else 1.0,
        "lcs_sim_dice": (2 * lcs / s) if s else 1.0,
    }


def signature(seq: Tokens | str) -> str:
    toks = list(seq) if not isinstance(seq, str) else _clean(seq, drop_noncanonical=True)[0]
    return ">".join(toks)


def _task_role_of(row: Mapping[str, Any]) -> str:
    """T-A-V3-STEP1-003 R3: every mart row carries task_role ∈ {PRIMARY, SECONDARY_REPEATED}.
    A missing or unknown value is a schema violation → ValueError (never silently treated as PRIMARY)."""
    role = row.get("task_role")
    if role is None:
        raise ValueError(f"row {row.get('service_id')!r} has no task_role (T-A-V3-STEP1-003 R3: mandatory)")
    role = str(role)
    if role not in TASK_ROLES:
        raise ValueError(f"row {row.get('service_id')!r}: task_role={role!r} not in {sorted(TASK_ROLES)} (R3)")
    return role


def split_by_task_role(rows: Sequence[Mapping[str, Any]]) -> tuple[list[Mapping[str, Any]], list[Mapping[str, Any]]]:
    """T-A-V3-STEP1-003 R3: (primary_rows, secondary_repeated_rows). Raises on missing/unknown task_role."""
    primary, secondary = [], []
    for r in rows:
        (primary if _task_role_of(r) == "PRIMARY" else secondary).append(r)
    return primary, secondary


def pairwise_matrix(family_rows: Sequence[Mapping[str, Any]], *, seq_key: str = "task_flow_sequence",
                    id_key: str = "service_id", for_clustering_or_mds: bool = False) -> dict[str, Any]:
    """n×n distance matrices for one family (05 §2 E, §4), normalised per T-A-V3-STEP1-007 R12.

    Three Levenshtein normalisations are ALWAYS computed and stored: ``levenshtein_norm`` (max len,
    PRIMARY — the only one that feeds single-scalar reports), ``levenshtein_norm_sum`` and ``yujian_bo``
    (true metric). ``for_clustering_or_mds=True`` declares that the matrix will be clustered / embedded,
    which per R12 requires Yujian-Bo to be reported alongside: the output then carries
    ``clustering_companion = "yujian_bo"`` and both cell medians. LCS similarity stays as C's alt.
    05 §1: the 45 off-diagonal cells of a 10×10 family are CELLS of one matrix, not 45 independent
    observations; n_service and n_pairs are reported separately with pseudo_replication_guard.
    T-A-V3-STEP1-003 R3: only task_role == 'PRIMARY' rows enter the matrix; the literal
    filter_condition string is emitted and SECONDARY_REPEATED ids are listed as excluded.
    """
    primary, secondary = split_by_task_role(family_rows)
    family_rows = primary
    ids = [str(r[id_key]) for r in family_rows]
    seqs = [list(r[seq_key]) if not isinstance(r[seq_key], str) else _clean(r[seq_key], drop_noncanonical=True)[0]
            for r in family_rows]
    n = len(ids)
    lev = [[0.0] * n for _ in range(n)]
    lev_sum = [[0.0] * n for _ in range(n)]
    yb = [[0.0] * n for _ in range(n)]
    lcs = [[1.0] * n for _ in range(n)]
    for i in range(n):
        for j in range(i + 1, n):
            d = seq_distance(seqs[i], seqs[j])
            lev[i][j] = lev[j][i] = d["levenshtein_norm"]
            lev_sum[i][j] = lev_sum[j][i] = d["levenshtein_norm_sum"]
            yb[i][j] = yb[j][i] = d["yujian_bo"]
            lcs[i][j] = lcs[j][i] = d["lcs_sim"]
    upper = [lev[i][j] for i in range(n) for j in range(i + 1, n)]
    upper_yb = [yb[i][j] for i in range(n) for j in range(i + 1, n)]
    out = {
        "filter_condition": PRIMARY_FILTER_CONDITION,
        "n_input_rows": len(primary) + len(secondary),
        "n_secondary_repeated_excluded": len(secondary),
        "secondary_repeated_ids": [str(r.get(id_key)) for r in secondary],
        "denominator_name": "entry_structure_n",
        "service_ids": ids,
        "n_service": n,
        "n_pairs": n * (n - 1) // 2,
        "n_service_warning": None if n == 10 else f"family n={n}, expected 10 (05 §1)",
        "pseudo_replication_guard": PSEUDO_REPLICATION_GUARD,
        "distance_rule": DISTANCE_RULE_ID,
        "primary_distance": PRIMARY_DISTANCE_KEY,
        "single_scalar_source": PRIMARY_DISTANCE_KEY,
        "for_clustering_or_mds": bool(for_clustering_or_mds),
        "clustering_companion": "yujian_bo" if for_clustering_or_mds else None,
        "levenshtein_norm": lev,
        "levenshtein_norm_sum": lev_sum,
        "yujian_bo": yb,
        "lcs_sim": lcs,
        "levenshtein_norm_cells_median": _median(upper) if upper else None,
        "levenshtein_norm_cells_range": [min(upper), max(upper)] if upper else None,
        "yujian_bo_cells_median": _median(upper_yb) if upper_yb else None,
    }
    assert_field_qualified(out, "pairwise_matrix")
    return out


def unique_signatures(family_rows: Sequence[Mapping[str, Any]], *, seq_key: str = "task_flow_sequence") -> dict[str, Any]:
    """Unique flow signatures (05 §2 E, §4): signature = action tokens joined by '>'.
    Counts are emitted under ``signature_counts`` (a Q8-qualifying key: the keys are action_token sequences)."""
    c = Counter(signature(r[seq_key]) for r in family_rows)
    return {"n_rows": len(family_rows), "n_unique": len(c), "signature_counts": dict(c.most_common())}


# ============================================================================
# family summary (05 §1, §4)
# ============================================================================

def _median(xs: Sequence[float]) -> float:
    s = sorted(xs)
    n = len(s)
    if n == 0:
        raise ValueError("median of empty")
    return s[n // 2] if n % 2 else (s[n // 2 - 1] + s[n // 2]) / 2


def _quantile_type7(xs: Sequence[float], q: float) -> float:
    """Linear-interpolation quantile (Hyndman–Fan type 7, numpy default). C choice for IQR."""
    s = sorted(xs)
    n = len(s)
    if n == 1:
        return s[0]
    h = (n - 1) * q
    lo = math.floor(h)
    hi = min(lo + 1, n - 1)
    return s[lo] + (h - lo) * (s[hi] - s[lo])


def shannon_entropy_bits(counts: Mapping[Any, int]) -> float:
    total = sum(counts.values())
    if total == 0:
        return 0.0
    h = 0.0
    for c in counts.values():
        if c:
            p = c / total
            h -= p * math.log2(p)
    return h


def auth_gate_is_endpoint(family_id: str | None) -> bool:
    """T-A-V3-STEP1-003 R2: F1 endpoint_contract names AUTH_GATE as the endpoint → reached; F2..F5 → not.
    Unknown family ids raise (the rule is per-family and must not be guessed)."""
    if family_id is None or str(family_id) not in AUTH_GATE_IS_ENDPOINT_BY_FAMILY:
        raise ValueError(f"family_id={family_id!r}: AUTH_GATE endpoint semantics undefined "
                         f"(T-A-V3-STEP1-003 R2 defines {sorted(AUTH_GATE_IS_ENDPOINT_BY_FAMILY)})")
    return AUTH_GATE_IS_ENDPOINT_BY_FAMILY[str(family_id)]


def row_evidence_bearing(row: Mapping[str, Any]) -> bool:
    """A row is evidence-bearing unless it says otherwise (evidence_bearing=False) or its endpoint_status
    is an evidence-level failure. AUTH_GATE and ABSTAIN rows ARE evidence-bearing (R2 'critical')."""
    if row.get("evidence_bearing") is not None:
        return bool(row["evidence_bearing"])
    return str(row.get("endpoint_status") or "") not in {"EVIDENCE_DEFECT", "NOT_ATTEMPTED"}


def row_flow_evaluable(row: Mapping[str, Any]) -> bool:
    """05 §6 flow-evaluable: explicit row flag if present; else endpoint_status != ABSTAIN (C-9).
    AUTH_GATE rows are flow-evaluable in every family (C reading of R2: F2..F5 'endpoint 도달률 분모에서는
    미도달로 집계' = in the denominator as not-reached)."""
    if row.get("flow_evaluable") is not None:
        return bool(row["flow_evaluable"])
    return str(row.get("endpoint_status") or "") != "ABSTAIN"


def row_endpoint_reached(row: Mapping[str, Any], family_id: str | None) -> bool | None:
    """T-A-V3-STEP1-003 R2: endpoint reached iff endpoint_status == REACHED, or endpoint_status ==
    AUTH_GATE in a family whose endpoint_contract names AUTH_GATE (F1). None if endpoint_status absent."""
    es = row.get("endpoint_status")
    if es is None:
        return None
    es = str(es)
    if es == "REACHED":
        return True
    if es == "AUTH_GATE":
        return auth_gate_is_endpoint(family_id)
    return False


def _numeric_block(vals: list[float], denominator_n: int, denominator_name: str) -> dict[str, Any]:
    miss = denominator_n - len(vals)
    if not vals:
        return {"n": 0, "n_missing": miss, "denominator": denominator_name, "denominator_n": denominator_n}
    q1, q3 = _quantile_type7(vals, 0.25), _quantile_type7(vals, 0.75)
    return {
        "n": len(vals), "n_missing": miss,
        "denominator": denominator_name, "denominator_n": denominator_n,
        "median": _median(vals), "q1": q1, "q3": q3, "iqr": q3 - q1,
        "min": min(vals), "max": max(vals), "range": max(vals) - min(vals),
        "mean": sum(vals) / len(vals),
    }


def _categorical_block(vals: list[str], denominator_n: int, denominator_name: str) -> dict[str, Any]:
    if any(v.strip() == "" for v in vals):
        raise ValueError("categorical value is an empty string: GAP_04 requires the explicit UNDETERMINED / "
                         "NOT_OBSERVED for an unobserved categorical (T-A-V3-STEP1-012)")
    c = Counter(vals)
    k = len(c)
    h = shannon_entropy_bits(c)
    return {
        "n": len(vals), "n_missing": denominator_n - len(vals),
        "denominator": denominator_name, "denominator_n": denominator_n,
        "distribution": dict(c.most_common()),
        "k_observed": k,
        "entropy_bits": h,
        "entropy_norm": (h / math.log2(k)) if k > 1 else 0.0,
    }


def _resolve_denominator(var: str, denominator_map: Mapping[str, str] | None) -> str:
    if denominator_map and var in denominator_map:
        d = denominator_map[var]
    elif var in ENTRY_STRUCTURE_VARS:
        d = "entry_structure_n"
    elif var in ENDPOINT_DEPENDENT_VARS:
        d = "endpoint_dependent_n"
    else:
        raise ValueError(f"family_summary: variable {var!r} has no declared denominator "
                         f"(T-A-V3-STEP1-003 R2: pass denominator_map={{{var!r}: 'entry_structure_n'|'endpoint_dependent_n'}})")
    if d not in DENOMINATOR_NAMES:
        raise ValueError(f"family_summary: denominator {d!r} for {var!r} not in {DENOMINATOR_NAMES}")
    return d


def _summarise_subset(rows: Sequence[Mapping[str, Any]], numeric_vars: Sequence[str],
                      categorical_vars: Sequence[str], family_id: str | None,
                      denominator_map: Mapping[str, str] | None) -> dict[str, Any]:
    evid = [r for r in rows if row_evidence_bearing(r)]
    flow = [r for r in evid if row_flow_evaluable(r)]
    pools = {"entry_structure_n": evid, "endpoint_dependent_n": flow}
    n_entry, n_flow = len(evid), len(flow)
    out: dict[str, Any] = {
        "n_rows": len(rows),
        "n_not_evidence_bearing": len(rows) - n_entry,
        "denominators": {
            "rule": "T-A-V3-STEP1-003 R2",
            "entry_structure_n": n_entry,
            "entry_structure_n_definition": "all evidence-bearing rows regardless of endpoint_status=AUTH_GATE "
                                            "(entry position/label/AX/control type/menu·reveal/nav_container_depth/auth_gate_stage)",
            "endpoint_dependent_n": n_flow,
            "endpoint_dependent_n_definition": "flow-evaluable rows only (endpoint reach rate, post-endpoint sequence length)",
            "excluded_from_endpoint_dependent": n_entry - n_flow,
        },
        "null_convention": NULL_CONVENTION_ID + "; None is excluded from n (n_missing), never counted as 0",
        "numeric": {},
        "categorical": {},
    }
    reached = [row_endpoint_reached(r, family_id) for r in flow] if flow else []
    known = [x for x in reached if x is not None]
    out["endpoint_reach_rate"] = {
        "numerator_reached": sum(1 for x in known if x),
        "denominator": "endpoint_dependent_n", "denominator_n": n_flow,
        "n_endpoint_status_unknown": len(reached) - len(known),
        "rate": (sum(1 for x in known if x) / n_flow) if n_flow else None,
        "auth_gate_counts_as_reached": (auth_gate_is_endpoint(family_id)
                                        if family_id in AUTH_GATE_IS_ENDPOINT_BY_FAMILY else None),
        "n_endpoint_status_auth_gate_in_denominator": sum(1 for r in flow if str(r.get("endpoint_status")) == "AUTH_GATE"),
    }
    for v in numeric_vars:
        dname = _resolve_denominator(v, denominator_map)
        pool = pools[dname]
        vals = [float(r[v]) for r in pool if r.get(v) is not None]
        blk = _numeric_block(vals, len(pool), dname)
        if dname == "endpoint_dependent_n" and vals:
            # R6 Q1: endpoint-dependent lengths can be truncated by an early gate — show the split.
            split: dict[str, Any] = {}
            for label, want in (("reached", True), ("not_reached", False)):
                sub = [float(r[v]) for r in pool if r.get(v) is not None and row_endpoint_reached(r, family_id) is want]
                split[label] = {"n": len(sub), "median": _median(sub) if sub else None}
            blk["by_endpoint_reached"] = split
        out["numeric"][v] = blk
    for v in categorical_vars:
        dname = _resolve_denominator(v, denominator_map)
        pool = pools[dname]
        vals = [str(r[v]) for r in pool if r.get(v) is not None]
        blk = _categorical_block(vals, len(pool), dname)
        blk["n_unobserved_explicit"] = sum(1 for x in vals if x in UNOBSERVED_CATEGORICAL)   # kept in n (R13/GAP_04)
        out["categorical"][v] = blk
    return out


def family_summary(rows: Sequence[Mapping[str, Any]], numeric_vars: Sequence[str] = (),
                   categorical_vars: Sequence[str] = (), *, family_id: str | None = None,
                   denominator_map: Mapping[str, str] | None = None) -> dict[str, Any]:
    """Family-level descriptive summary (05 §4): numeric → median/IQR(type-7)/range with n;
    categorical → distribution + Shannon entropy (bits) + entropy_norm = H/log2(k_observed).

    n_service (05 §4 "n=10 고정") and n_pairs = n(n-1)/2 are ALWAYS reported separately with
    pseudo_replication_guard (05 §1, 13). No composite score is produced (05 §3).

    T-A-V3-STEP1-003 R3: rows are filtered to task_role == 'PRIMARY' and the literal
    ``filter_condition`` string is emitted; SECONDARY_REPEATED rows (if any) are summarised
    separately under ``secondary_repeated`` and never enter n_service / n_pairs.

    T-A-V3-STEP1-003 R2: TWO denominators are reported explicitly —
      entry_structure_n     all evidence-bearing PRIMARY rows regardless of endpoint_status=AUTH_GATE
                            (entry position/label/AX/control type/menu·reveal/nav_container_depth/auth_gate_stage)
      endpoint_dependent_n  flow-evaluable PRIMARY rows only (endpoint reach rate, post-endpoint sequence length)
    Every numeric/categorical block states ``denominator`` and ``denominator_n``. ``family_id`` decides
    whether endpoint_status=AUTH_GATE counts as endpoint reached (F1 yes; F2..F5 no). Variables not in
    ENTRY_STRUCTURE_VARS / ENDPOINT_DEPENDENT_VARS must be assigned via ``denominator_map`` or raise.
    """
    primary, secondary = split_by_task_role(rows)
    if family_id is not None:
        auth_gate_is_endpoint(family_id)          # raise early on an unknown family
    elif any(str(r.get("endpoint_status")) == "AUTH_GATE" for r in rows):
        raise ValueError("family_summary: rows contain endpoint_status=AUTH_GATE but family_id is None "
                         "(T-A-V3-STEP1-003 R2: AUTH_GATE semantics are per family)")
    n = len(primary)
    body = _summarise_subset(primary, numeric_vars, categorical_vars, family_id, denominator_map)
    out: dict[str, Any] = {
        "family_id": family_id,
        "filter_condition": PRIMARY_FILTER_CONDITION,
        "n_input_rows": len(rows),
        "n_primary": n,
        "n_secondary_repeated": len(secondary),
        "n_service": n,
        "n_pairs": n * (n - 1) // 2,
        "n_service_warning": None if n == 10 else f"family n={n}, expected 10 (05 §1)",
        "pseudo_replication_guard": PSEUDO_REPLICATION_GUARD,
        "denominators": body["denominators"],
        "null_convention": body["null_convention"],
        "endpoint_reach_rate": body["endpoint_reach_rate"],
        "numeric": body["numeric"],
        "categorical": body["categorical"],
        "secondary_repeated": None,
    }
    if secondary:
        sec = _summarise_subset(secondary, numeric_vars, categorical_vars, family_id, denominator_map)
        sec["filter_condition"] = "task_role == 'SECONDARY_REPEATED'"
        sec["service_ids"] = [str(r.get("service_id")) for r in secondary]
        sec["task_ids"] = [r.get("task_id") for r in secondary]
        sec["note"] = "separate task_id rows; never added to the main-sample n (00 §4, 01 §3, R3)"
        out["secondary_repeated"] = sec
    assert_field_qualified(out, "family_summary")
    return out


# ============================================================================
# denominator chain (05 §6)
# ============================================================================

_CHAIN_COUNT_STAGES = ("candidate", "eligible_frozen", "attempted", "evidence_bearing", "flow_evaluable")
CHAIN_STAGES = ("candidate", "replaced", "eligible_frozen", "attempted", "evidence_bearing", "flow_evaluable")


def _validate_replacement(item: Mapping[str, Any], idx: int) -> dict[str, Any]:
    """T-A-V3-STEP1-003 R4: one replacement = (target_id, reason, reserve_rank, decided_at, decided_by)."""
    if not isinstance(item, Mapping):
        raise ValueError(f"replaced[{idx}] must be a mapping with keys {REPLACEMENT_ITEM_KEYS}")
    missing = [k for k in REPLACEMENT_ITEM_KEYS if item.get(k) is None]
    if missing:
        raise ValueError(f"replaced[{idx}] missing {missing} (T-A-V3-STEP1-003 R4)")
    reason = str(item["reason"])
    if reason not in REPLACEMENT_REASONS:
        raise ValueError(f"replaced[{idx}] reason={reason!r} not in allowed set {sorted(REPLACEMENT_REASONS)} "
                         f"(T-A-V3-STEP1-003 R1/R4: no 5th reason)")
    rank = item["reserve_rank"]
    if isinstance(rank, bool) or not isinstance(rank, int) or rank < 1:
        raise ValueError(f"replaced[{idx}] reserve_rank={rank!r} must be a positive int")
    for k in ("target_id", "decided_at", "decided_by"):
        if not str(item[k]).strip():
            raise ValueError(f"replaced[{idx}] {k} must be a non-empty string")
    return {"target_id": str(item["target_id"]), "reason": reason, "reserve_rank": int(rank),
            "decided_at": str(item["decided_at"]), "decided_by": str(item["decided_by"])}


def denominator_chain(candidate: int, eligible: int, attempted: int, evidence_bearing: int,
                      flow_evaluable: int, *, family_id: str | None = None,
                      reasons: Mapping[str, Sequence[str]] | None = None,
                      replaced: Sequence[Mapping[str, Any]] | None = None,
                      rows: Sequence[Mapping[str, Any]] | None = None) -> dict[str, Any]:
    """05 §6 chain extended by T-A-V3-STEP1-003 R4:
    candidate → replaced k [per-item target_id/reason/reserve_rank/decided_at/decided_by]
              → eligible/frozen → attempted → evidence-bearing → flow-evaluable.

    * k is ALWAYS emitted (k=0 → ``"k": 0, "items": []``), never an absent field.
    * reasons outside REPLACEMENT_REASONS raise (R1: no 5th reason).
    * Replacement happens only at precheck, so ``replaced`` is frozen before ``attempted``.
    * R3: counts are PRIMARY-only; ``filter_condition`` is emitted as a literal. If ``rows`` are given,
      evidence_bearing / flow_evaluable are cross-checked against the PRIMARY rows and mismatch raises.
    * Q8: reason strings must qualify AUTH_GATE/ABSTAIN (endpoint_status=… / action_token=…).
    Raises ValueError if any later count exceeds an earlier one, or any count is negative.
    """
    counts = [candidate, eligible, attempted, evidence_bearing, flow_evaluable]
    for s, c in zip(_CHAIN_COUNT_STAGES, counts, strict=True):
        if isinstance(c, bool) or not isinstance(c, int) or c < 0:
            raise ValueError(f"denominator chain: {s}={c!r} must be a non-negative int")
    for i in range(1, len(counts)):
        if counts[i] > counts[i - 1]:
            raise ValueError(f"denominator chain non-monotonic: {_CHAIN_COUNT_STAGES[i]}={counts[i]} > "
                             f"{_CHAIN_COUNT_STAGES[i-1]}={counts[i-1]} (05 §6)")
    items = [_validate_replacement(it, i) for i, it in enumerate(replaced or [])]
    k = len(items)
    if k > candidate:
        raise ValueError(f"replaced k={k} > candidate={candidate}")
    ids = [it["target_id"] for it in items]
    if len(set(ids)) != len(ids):
        raise ValueError(f"replaced target_id duplicated: {ids}")
    reasons = dict(reasons or {})
    assert_field_qualified(reasons, "denominator_chain.reasons")

    n_secondary = None
    if rows is not None:
        primary, secondary = split_by_task_role(rows)
        n_secondary = len(secondary)
        eb = sum(1 for r in primary if row_evidence_bearing(r))
        fe = sum(1 for r in primary if row_evidence_bearing(r) and row_flow_evaluable(r))
        if eb != evidence_bearing or fe != flow_evaluable:
            raise ValueError(f"denominator chain: passed evidence_bearing={evidence_bearing}/flow_evaluable="
                             f"{flow_evaluable} but PRIMARY rows give {eb}/{fe} (R3 filter applied)")

    chain: list[dict[str, Any]] = []
    chain.append({"stage": "candidate", "count": candidate, "dropped": 0, "reasons": list(reasons.get("candidate", []))})
    chain.append({"stage": "replaced", "k": k, "items": items,
                  "by_reason": {r: sum(1 for it in items if it["reason"] == r) for r in sorted(REPLACEMENT_REASONS)},
                  "frozen_before": "attempted", "note": "precheck-only; k=0 is reported explicitly (R4)"})
    prev = candidate
    for s, c in zip(_CHAIN_COUNT_STAGES[1:], counts[1:], strict=True):
        chain.append({"stage": s, "count": c, "dropped": prev - c, "reasons": list(reasons.get(s, []))})
        prev = c
    notes = []
    if candidate != 10:
        notes.append(f"candidate={candidate}, expected 10 (05 §1)")
    if eligible < candidate:
        notes.append(f"eligible < candidate by {candidate - eligible}: exclusions not covered by a 1:1 "
                     f"replacement (replaced k={k}); replacement allowed only before freeze (05 §6)")
    if k and eligible != candidate:
        notes.append(f"replaced k={k} but eligible ({eligible}) != candidate ({candidate}): "
                     f"replacement is 1:1 — check the freeze manifest")
    out = {"family_id": family_id, "filter_condition": PRIMARY_FILTER_CONDITION,
           "n_secondary_repeated_excluded": n_secondary, "replaced_k": k,
           "format": "candidate → replaced k → eligible_frozen → attempted → evidence_bearing → flow_evaluable (R4)",
           "chain": chain, "notes": notes}
    assert_field_qualified(out, "denominator_chain")
    return out


# ============================================================================
# spatial zone (04 §4 entry_zone) — thresholds fixed by T-A-V3-STEP1-003 R7 (supersedes C-7)
# ============================================================================

def _validate_xy(x_norm: float | None, y_norm: float | None) -> tuple[float, float]:
    if x_norm is None or y_norm is None:
        raise ValueError("entry_zone needs x_norm and y_norm (04 §6 / R7: entry_x_norm·entry_y_norm are "
                         "ALWAYS stored, even when a structural override applies)")
    x, y = float(x_norm), float(y_norm)
    if not (0.0 <= x <= 1.0 and 0.0 <= y <= 1.0):
        raise ValueError(f"entry_zone: ({x}, {y}) outside [0,1]")
    return x, y


def entry_zone(x_norm: float | None, y_norm: float | None, is_floating: bool, is_drawer: bool) -> str:
    """entry_zone from the normalised control-bbox centre in the 390×844 viewport of that state (04 §4/§6).

    Thresholds: T-A-V3-STEP1-003 R7 (A ruling, supersedes C-7).
      y bands            y < 1/3 → TOP · 1/3 ≤ y < 2/3 → MID · y ≥ 2/3 → BOTTOM
      x within TOP only  x < 1/3 → TOP_LEFT · 1/3 ≤ x < 2/3 → TOP_CENTER · x ≥ 2/3 → TOP_RIGHT
      MID / BOTTOM       no x split (04 codebook has no MID_LEFT-type value)
      boundaries         [a, b) — a point exactly at 1/3 is TOP and TOP_CENTER; exactly 2/3 is BOTTOM / TOP_RIGHT
    Structural overrides take precedence over geometry: DRAWER (control inside a reveal-requiring
    nav_container, the one that makes menu_dependency=1) > FLOATING (computed position fixed/sticky) > bands.
    x/y_norm are always retained: they are validated even when an override applies (R7 record_anyway),
    and this function never discards them — the zone is a summary value only.
    Raises ValueError if x or y is missing or outside [0, 1].
    """
    x, y = _validate_xy(x_norm, y_norm)
    if is_drawer:
        return "DRAWER"
    if is_floating:
        return "FLOATING"
    if y < ZONE_TOP_Y:
        if x < ZONE_X_LEFT:
            return "TOP_LEFT"
        if x < ZONE_X_RIGHT:
            return "TOP_CENTER"
        return "TOP_RIGHT"
    if y < ZONE_BOTTOM_Y:
        return "MID"
    return "BOTTOM"


def entry_zone_record(x_norm: float | None, y_norm: float | None, is_floating: bool, is_drawer: bool) -> dict[str, Any]:
    """R7 helper: the zone together with the raw coordinates it was derived from and the geometry-only zone,
    so an override never hides the position (entry_x_norm / entry_y_norm are always retained).
    GAP_04 (T-A-V3-STEP1-012): if the coordinates were not observed, the record is null-consistent —
    entry_x_norm / entry_y_norm None (never 0) and entry_zone NOT_OBSERVED (never "") — and
    ``entry_zone_observed=False``; entry_zone() itself still raises so a caller cannot silently use it."""
    if x_norm is None or y_norm is None:
        return {
            "entry_x_norm": None, "entry_y_norm": None,
            "entry_zone": "NOT_OBSERVED", "entry_zone_geometry_only": "NOT_OBSERVED",
            "entry_is_floating": bool(is_floating), "entry_in_drawer": bool(is_drawer),
            "entry_zone_observed": False, "zone_rule": ZONE_RULE_ID, "null_convention": NULL_CONVENTION_ID,
        }
    x, y = _validate_xy(x_norm, y_norm)
    return {
        "entry_zone_observed": True,
        "entry_x_norm": x, "entry_y_norm": y,
        "entry_zone": entry_zone(x, y, is_floating, is_drawer),
        "entry_zone_geometry_only": entry_zone(x, y, False, False),
        "entry_is_floating": bool(is_floating), "entry_in_drawer": bool(is_drawer),
        "zone_rule": ZONE_RULE_ID,
    }


# ============================================================================
# T-A-V3-STEP1-003 R6 Q8: field-qualification guard for AUTH_GATE / ABSTAIN
# ============================================================================

def q8_bare_mentions(obj: Any, path: str = "") -> list[str]:
    """Return every place in ``obj`` where AUTH_GATE / ABSTAIN appears WITHOUT a layer qualification.

    Allowed: any value (or dict key) whose ancestor key chain contains a qualifying key
    (endpoint_status / action_token / task_flow_sequence / experienced_flow_sequence / signature*) or a key
    that names the layer as a suffix (…_action_token / …_endpoint_status); a signature
    string 'A>B>AUTH_GATE' (a joined action_token sequence); free text where every mention is written
    as ``endpoint_status=AUTH_GATE`` or ``action_token=AUTH_GATE``.
    Flagged: a bare 'AUTH_GATE'/'ABSTAIN' value in a list or under an unrelated key, a bare dict key,
    or free text mentioning the word without a qualifier.
    """
    found: list[str] = []

    def walk(o: Any, p: str, qualified: bool) -> None:
        if isinstance(o, Mapping):
            for k, v in o.items():
                ks = str(k)
                # a key qualifies if it is a qualifying key or itself names the layer as a suffix
                # (e.g. nav_anchor_action_token, b_endpoint_status)
                q = qualified or ks in Q8_QUALIFYING_KEYS or ks.endswith(("action_token", "endpoint_status"))
                if not q and ks in Q8_AMBIGUOUS_VALUES:
                    found.append(f"{p}.{ks} (bare key)")
                walk(v, f"{p}.{ks}", q)
        elif isinstance(o, (list, tuple, set, frozenset)):
            for i, v in enumerate(o):
                walk(v, f"{p}[{i}]", qualified)
        elif isinstance(o, str):
            if qualified or ">" in o:
                return
            if o in Q8_AMBIGUOUS_VALUES:
                found.append(f"{p} = {o} (bare value)")
            elif _Q8_BARE_RE.search(o):
                found.append(f"{p} = {o!r} (unqualified mention)")

    walk(obj, path, False)
    return found


def assert_field_qualified(obj: Any, path: str = "") -> None:
    """Raise ValueError listing every unqualified AUTH_GATE / ABSTAIN mention (R6 Q8)."""
    bad = q8_bare_mentions(obj, path)
    if bad:
        raise ValueError("T-A-V3-STEP1-003 R6 Q8 field qualification violated: " + "; ".join(bad))


# ============================================================================
# T-A-V3-STEP1-007 R11: terminal_reason companion field + endpoint_status × terminal_reason table
# ============================================================================

# The enums and the allowed combination table live in ONE C module shared with lane5 (gate1/c_terminal_table.py):
# OTHER is allowed with any non-REACHED endpoint_status but ALWAYS needs a non-empty note. C PRE-REGISTERED PROPOSAL,
# to be compared against B's runner schema at GATE 1 (R11 "consistency") — see the module docstring.
import pathlib as _pl
import sys as _sys
_sys.path.insert(0, str(_pl.Path(__file__).resolve().parents[1]))
import c_terminal_table as _T  # noqa: E402
ENDPOINT_STATUSES: frozenset[str] = frozenset(_T.ENDPOINT_STATUSES)
TERMINAL_REASONS: frozenset[str] = frozenset(_T.TERMINAL_REASONS)
# lane6 view of the table: None (= no terminal_reason) is the only admissible value for REACHED.
TERMINAL_ALLOWED: dict[str, frozenset[str | None]] = {
    es: (frozenset({None}) if es == "REACHED" else rs) for es, rs in _T.TERMINAL_ALLOWED.items()
}
TERMINAL_RULE_ID = _T.RULE_ID


def validate_terminal(endpoint_status: str | None, terminal_reason: str | None, note: str | None = None) -> dict[str, Any]:
    """R11 validator: every terminal observation carries BOTH endpoint_status and terminal_reason.

    Returns {ok, endpoint_status, terminal_reason, note, violations}. Never raises — violations are listed
    so a GATE 1/3 checker can collect them; use ``assert_terminal`` for a raising variant.
    Rules: endpoint_status ∈ ENDPOINT_STATUSES; terminal_reason ∈ TERMINAL_REASONS (None only for REACHED);
    the pair must be in TERMINAL_ALLOWED (C proposal shared with lane5 via gate1/c_terminal_table.py, e.g. REACHED ×
    TIMEOUT is impossible); OTHER is allowed with any non-REACHED status but requires a non-empty free-text note
    (note-less OTHER is a schema violation).
    T-A-V3-STEP1-011 P-17 layer separation: ``endpoint_status=ABSTAIN`` (we do NOT know — multiple candidates /
    undetermined path) is distinct from ``endpoint_status=PUBLIC_WEB_UNOBSERVABLE × terminal_reason=
    TASK_SURFACE_ABSENT`` (we KNOW the surface is absent); the table keeps them apart, and
    ``action_token=ABSTAIN`` (what the sequence did) is a different layer from endpoint_status (the result).
    """
    es = None if endpoint_status is None else str(endpoint_status).strip().upper()
    tr = None if terminal_reason is None else str(terminal_reason).strip().upper()
    v = _T.validate_pair(es, tr, note)                      # single table + single rule set (shared with lane5)
    out = {"ok": not v, "endpoint_status": es, "terminal_reason": tr, "note": note, "violations": v,
           "rule": TERMINAL_RULE_ID}
    assert_field_qualified(out, "validate_terminal")
    return out


def assert_terminal(endpoint_status: str | None, terminal_reason: str | None, note: str | None = None) -> None:
    r = validate_terminal(endpoint_status, terminal_reason, note)
    if not r["ok"]:
        raise ValueError("R11 terminal validation failed: " + "; ".join(r["violations"]))


# ============================================================================
# GATE 3 helper: recompute-and-compare against a B mart row
# ============================================================================

DERIVED_COMPARE_FIELDS = ("activation_depth", "flow_step_count", "menu_dependency", "nav_container_depth",
                          "forced_dismissal_count", "auth_gate_stage")


def compare_with_mart_row(row: Mapping[str, Any], *, synonym_map: Mapping[str, str] | None = None,
                          **derive_kw: Any) -> dict[str, Any]:
    """Recompute derived fields from a fact_flow_observation row (02 §4) and diff against B's stored values.

    Reads only raw inputs (task_flow_sequence, experienced_flow_sequence, visible_label_text,
    accessible_name, entry_x_norm/entry_y_norm, nav_container_type). B's stored derived values are used
    ONLY for the comparison column, never as inputs.
    """
    if "input_modes" not in derive_kw and row.get("fixture_input_mode") is not None:
        # STEP1-006: a row-level fixture_input_mode resolves the conditional tokens unless it is MIXED,
        # in which case the caller must pass per-token input_modes (the means actually used).
        derive_kw["input_modes"] = row.get("depth_input_modes") or str(row["fixture_input_mode"])
    if "endpoint_surface_rendered_before_gate" not in derive_kw and row.get("endpoint_surface_rendered_before_gate") is not None:
        derive_kw["endpoint_surface_rendered_before_gate"] = bool(row["endpoint_surface_rendered_before_gate"])
    d = derive(row["task_flow_sequence"], row.get("experienced_flow_sequence"), **derive_kw)
    diffs: dict[str, dict[str, Any]] = {}
    for f in DERIVED_COMPARE_FIELDS:
        if f in row and row[f] is not None and d[f] is not None:
            b_val = int(row[f]) if f != "auth_gate_stage" else str(row[f])
            if b_val != d[f]:
                diffs[f] = {"B": b_val, "C": d[f]}
    if row.get("endpoint_status") is not None:
        c_es = d["endpoint_status"]
        if c_es != "UNRESOLVED_FROM_SEQUENCE" and str(row["endpoint_status"]) != c_es:
            diffs["endpoint_status"] = {"B": row["endpoint_status"], "C": c_es}
        # R11: endpoint_status × terminal_reason must be an allowed pair (C proposal table)
        term = validate_terminal(row["endpoint_status"], row.get("terminal_reason"), row.get("terminal_note"))
        d["terminal_validation"] = term
        if not term["ok"]:
            diffs["terminal_reason"] = {"B": {"endpoint_status": row["endpoint_status"],
                                              "terminal_reason": row.get("terminal_reason")},
                                        "C": term["violations"]}
    if row.get("task_role") is not None:
        d["task_role"] = _task_role_of(row)
    if synonym_map is not None and ("visible_label_text" in row or "accessible_name" in row):
        c_lr = label_relation(row.get("visible_label_text"), row.get("accessible_name"), synonym_map)
        d["label_relation"] = c_lr
        if row.get("label_relation") is not None and str(row["label_relation"]) != c_lr:
            diffs["label_relation"] = {"B": row["label_relation"], "C": c_lr}
    if row.get("entry_x_norm") is not None and row.get("entry_y_norm") is not None:
        nct = str(row.get("nav_container_type") or "NONE")
        c_zone = entry_zone(row["entry_x_norm"], row["entry_y_norm"],
                            bool(row.get("entry_is_floating", False)),
                            nct in {"LEFT_DRAWER", "RIGHT_DRAWER", "HAMBURGER", "MODAL_MENU", "BOTTOM_SHEET"}
                            and bool(row.get("entry_in_drawer", False)))
        d["entry_zone"] = c_zone
        if row.get("entry_zone") is not None and str(row["entry_zone"]) != c_zone:
            diffs["entry_zone"] = {"B": row["entry_zone"], "C": c_zone}
    d["diffs"] = diffs
    d["match"] = not diffs
    return d
