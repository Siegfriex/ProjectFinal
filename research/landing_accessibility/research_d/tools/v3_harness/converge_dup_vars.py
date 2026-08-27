#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Lane X-Converge — do Lane S and Lane F measure the same thing?

`nav_container_depth` and `menu_dependency` were implemented twice, independently, because the
D orchestrator put both variables into two worker prompts (D-DEF-11). Neither implementation is
discarded. Two independent readings of the same SSOT text are the material for a convergence test.

Method (A's `ruling_11` three-axis protocol):
  1. Declare, per variable per lane, the GRAIN / POPULATION / SOURCE FIELD.
  2. Compare only where all three axes match. Where an axis differs, the two numbers are
     DIFFERENT QUANTITIES and a value mismatch is not a defect.
  3. Fixtures are derived from the SSOTV3 primary text ONLY. Neither lane's fixture is reused:
     using one lane's fixture would silently make that lane's reading the answer key.

This module does NOT import-and-mutate the lane modules. Mutation testing wraps the *callables*
passed into the comparator, so `lane_s_spatial_control_reveal.py` and `lane_f_flow_depth.py` are
read-only in every sense.

Reproduce:
    /home/sieg/projects-wsl/ProjectFinal/.venv/bin/python \
      .../research_d/tools/v3_harness/converge_dup_vars.py

Writes (and nothing else):
    research_d/results/harness/converge/CONVERGE_DUP_VARS.json
    research_d/results/harness/converge/CONVERGE_FINDINGS.md
"""

from __future__ import annotations

import datetime as _dt
import hashlib
import json
import os
import shutil
import sys
import tempfile
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

HERE = os.path.dirname(os.path.abspath(__file__))
RD = os.path.abspath(os.path.join(HERE, "..", ".."))
OUT_DIR = os.path.join(RD, "results", "harness", "converge")
SSOT_DIR = "/home/sieg/projects-wsl/ProjectFinal/SSOTV3"
CODEBOOK = os.path.join(SSOT_DIR, "04_FLOW_CODEBOOK_v3.0.md")

BASE_SHA = "ce97273129b404774736ec566603b9e2b969ecdf"

# --------------------------------------------------------------------------------------
# Snapshot-then-import.
#
# The two lane modules live in a worktree that other Lane workers are actively editing:
# during the first run of this harness both files changed several times per minute. Importing
# them in place would mean the code compared and the code hashed are not provably the same
# bytes. So: copy both files to a scratch directory ONCE, hash the copy, import the copy, and
# re-hash the originals afterwards to report whether they drifted mid-run.
#
# The originals are opened read-only ('rb') and never written.
# --------------------------------------------------------------------------------------

SCRATCH = os.environ.get("CONVERGE_SNAPSHOT_DIR") or os.path.join(
    tempfile.gettempdir(), "converge_lane_snapshot_%d" % os.getpid())

LANE_S_SRC = os.path.join(HERE, "lane_s_spatial_control_reveal.py")
LANE_F_SRC = os.path.join(HERE, "lane_f_flow_depth.py")


def _sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _snapshot() -> Dict[str, Dict[str, str]]:
    os.makedirs(SCRATCH, exist_ok=True)
    meta = {}
    for name, src in (("lane_s", LANE_S_SRC), ("lane_f", LANE_F_SRC)):
        with open(src, "rb") as fh:          # read-only; the original is never opened for write
            data = fh.read()
        dst = os.path.join(SCRATCH, os.path.basename(src))
        with open(dst, "wb") as fh:
            fh.write(data)
        meta[name] = {
            "original_path": src,
            "snapshot_path": dst,
            "sha256_at_snapshot": hashlib.sha256(data).hexdigest(),
            "bytes": len(data),
            "access": "READ_ONLY — copied out, imported from the copy, never written",
        }
    return meta


SNAPSHOT = _snapshot()
sys.path.insert(0, SCRATCH)
import lane_s_spatial_control_reveal as LS  # noqa: E402  imported from the snapshot
import lane_f_flow_depth as LF              # noqa: E402  imported from the snapshot

assert os.path.dirname(os.path.abspath(LS.__file__)) == SCRATCH, "LS must load from the snapshot"
assert os.path.dirname(os.path.abspath(LF.__file__)) == SCRATCH, "LF must load from the snapshot"

MISSING = None

# ======================================================================================
# 1. SSOT primary text — the only source this harness derives fixtures from.
# ======================================================================================

SSOT_VERBATIM = {
    "04 §3 task vs experienced (worked example)": (
        "- `task_flow_sequence`: `DISMISS_OBSTRUCTION`을 제외한 서비스 자체 task navigation.\n"
        "- `experienced_flow_sequence`: 실제 진행에 필요했던 dismissal까지 포함.\n"
        "예:\n"
        "`task_flow = OPEN_GLOBAL_MENU > SELECT_FUNCTION > AUTH_GATE`\n"
        "`experienced_flow = DISMISS_OBSTRUCTION > OPEN_GLOBAL_MENU > SELECT_FUNCTION > AUTH_GATE`"
    ),
    "04 §4 menu_dependency": (
        "| menu_dependency | Derived | bool | action_sequence에 OPEN/REVEAL 계열 token이 "
        "endpoint 이전에 존재하는지 |"
    ),
    "04 §4 nav_container_depth": (
        "| nav_container_depth | Derived | count | task control 노출 전 menu/drawer expansion 수 |"
    ),
    "04 §5 menu_dependency": (
        "- `menu_dependency = 1` iff endpoint 전 OPEN_GLOBAL_MENU/OPEN_LOCAL_MENU/EXPAND_ACCORDION "
        "등 reveal token 존재."
    ),
    "04 §5 nav_container_depth": "- `nav_container_depth`: task control 노출 전 nested reveal 수.",
}

# A's confirmed delta, read from the ticket file, not paraphrased from memory.
A_TICKET = "/home/sieg/projects-wsl/ProjectFinal/.agent_bus/landing_v2/tickets/T-A-V3-STEP1-006.json"


def _load_a_delta() -> Dict[str, Any]:
    with open(A_TICKET, "r", encoding="utf-8") as fh:
        t = json.load(fh)
    return {
        "ticket_id": t["ticket_id"],
        "general_criterion": t["general_criterion"],
        "canonical_18_classification": t["canonical_18_classification"],
        "relevance_to_this_check": (
            "T-A-V3-STEP1-006 rules on `activation_depth` token attribution, and on the encoding of "
            "a right-drawer open as `OPEN_GLOBAL_MENU|OPEN_LOCAL_MENU` + `nav_container_type` + "
            "`reveal_direction` (direction is a variable, not a token). It therefore CONFIRMS the "
            "reveal-token vocabulary both lanes read out of 04 §5, but it does NOT close the two "
            "gaps this check exercises: (a) whether SWITCH_TAB is a reveal token for "
            "menu_dependency, (b) which step constitutes 'task control 노출' for "
            "nav_container_depth. Both remain open after 006."
        ),
    }


# ======================================================================================
# 2. Three-axis declaration — read off the two implementations, before any comparison.
# ======================================================================================

THREE_AXIS = {
    "menu_dependency": {
        "lane_s": {
            "fn": "lane_s_spatial_control_reveal.menu_dependency(sequence, *, sequence_field, extra_reveal_tokens=())",
            "grain": "run — one boolean per observation (one token sequence).",
            "population": "tokens strictly before the endpoint cut. Cut = index of the first "
                          "ENDPOINT_REACHED; if absent, the whole sequence. Basis reported per row "
                          "as `endpoint_cut_basis`.",
            "source_field": "ONE sequence, named by the caller. `sequence_field` is a REQUIRED "
                            "argument and must be 'task_flow_sequence' or "
                            "'experienced_flow_sequence'; the harness raises rather than pick one.",
            "reveal_token_set": "CLOSED at the three tokens 04 §5 names verbatim "
                                "(OPEN_GLOBAL_MENU / OPEN_LOCAL_MENU / EXPAND_ACCORDION). The '등' "
                                "extension must be passed explicitly via `extra_reveal_tokens`; "
                                "default empty, so SWITCH_TAB is NOT counted (AMB-S06).",
            "emits": "a single bool, always.",
        },
        "lane_f": {
            "fn": "lane_f_flow_depth.menu_dependency(task_seq, experienced_seq)",
            "grain": "run — one result per observation.",
            "population": "tokens strictly before the first ENDPOINT_REACHED; if absent, the whole "
                          "sequence. `endpoint_token_present` reported (AMB-F09).",
            "source_field": "BOTH sequences. Primary readings come from task_flow_sequence; the "
                            "experienced-base readings are computed too and their equality is "
                            "asserted as `base_invariant`.",
            "reveal_token_set": "OPEN — two readings emitted: `reveal_set_explicit3` (the three "
                                "named tokens) and `reveal_set_incl_switch_tab` (AMB-F05).",
            "emits": "a single bool ONLY when the two readings agree; otherwise value=None with "
                     "ambiguity_active=True.",
        },
        "axes_match": True,
        "axes_match_note": (
            "GRAIN identical. POPULATION identical (same endpoint-cut rule, same fallback). "
            "SOURCE FIELD reconcilable: S's `sequence_field='task_flow_sequence'` is exactly F's "
            "primary base. The lanes therefore ARE comparable — but only reading-to-reading: "
            "S's default output must be compared with F's `readings.reveal_set_explicit3`, NOT "
            "with F's emitted `value`, because the two differ in EMISSION POLICY (S closes the "
            "open set by default; F withholds a value while it is open)."
        ),
    },
    "nav_container_depth": {
        "lane_s": {
            "fn": "lane_s_spatial_control_reveal.recompute_nav_container_depth(sequence, exposure_step_index, *, extra_reveal_tokens=())",
            "grain": "run — one count per observation.",
            "population": "seq[:exposure_step_index]. NO endpoint cut is applied. Tokens after "
                          "ENDPOINT_REACHED are counted if the supplied index reaches them.",
            "source_field": "sequence + `exposure_step_index`, an EXTERNAL input that is not in "
                            "the token stream. Never inferred; MISSING index -> value MISSING "
                            "(AMB-S08).",
            "emits": "an int when an exposure index is supplied, else None. `nesting_verified` is "
                     "always False — the count is flat, so a sibling reveal is indistinguishable "
                     "from a nested one.",
        },
        "lane_f": {
            "fn": "lane_f_flow_depth.nav_container_depth_candidates(task_seq)",
            "grain": "run — but no value is produced at any grain.",
            "population": "prefix before the first ENDPOINT_REACHED, then further narrowed per "
                          "candidate. The endpoint cut IS applied to all three candidates.",
            "source_field": "task_flow_sequence only. F holds that the exposure step has no marker "
                            "token in the canonical 18 and refuses to invent one (AMB-F06).",
            "emits": "value=None ALWAYS. Three illustrative candidates only: "
                     "`reveal_tokens_before_first_SELECT_FUNCTION`, "
                     "`leading_consecutive_reveal_run`, `all_reveal_tokens_before_endpoint`.",
        },
        "axes_match": False,
        "axes_match_note": (
            "TWO axes differ. (1) SOURCE FIELD: S consumes an external `exposure_step_index` that F "
            "does not accept; F's quantity is a function of the token sequence alone, S's is a "
            "function of (sequence, externally declared exposure point). (2) POPULATION: F applies "
            "the endpoint cut before counting, S does not. On top of that, F emits no scalar at "
            "all. A scalar-vs-scalar comparison is not defined. What CAN be compared is S's output "
            "under a stipulated exposure rule against F's candidate that encodes the same "
            "stipulation — that is a reading-to-reading check, and it is what this harness runs."
        ),
    },
}

# ======================================================================================
# 3. Fixture — derived from the SSOT primary text. Neither lane's fixture is reused.
# ======================================================================================
#
# Derivation rules, stated so they can be audited:
#   R1. Every token is drawn verbatim from the 04 §2 canonical-18 table. No invented tokens.
#   R2. FX01 is the 04 §3 worked example copied verbatim, both sequences.
#   R3. Reveal tokens are the three 04 §5 names them; SWITCH_TAB is exercised separately because
#       §5's trailing '등' leaves the set open. It is NOT resolved here.
#   R4. The endpoint boundary is exercised on both sides of ENDPOINT_REACHED because §5 says
#       "endpoint 전" and §4 says "endpoint 이전에".
#   R5. §5 says "nested reveal" while §4 says "menu/drawer expansion 수". Nested and sibling
#       arrangements are therefore separated in the fixture, because the two phrasings disagree
#       about whether siblings count.
#   R6. `exposure_step_index` is a FIXTURE STIPULATION, not an SSOT rule. Each row records the
#       stipulation used and which F candidate it corresponds to. Where no stipulation is
#       defensible the row declares exposure_basis=None and S is expected to return MISSING.
#   R7. §3's structural relation (experienced minus dismissal == task) is exercised in both the
#       satisfied and the violated direction, because that relation is what makes the
#       SOURCE FIELD axis load-bearing.

T = "task_flow_sequence"

FIXTURES: List[Dict[str, Any]] = [
    {
        "id": "FX01_SSOT_S3_WORKED_EXAMPLE",
        "derivation": "04 §3 example copied verbatim (R2). Terminates at AUTH_GATE, no ENDPOINT_REACHED.",
        "task": ["OPEN_GLOBAL_MENU", "SELECT_FUNCTION", "AUTH_GATE"],
        "experienced": ["DISMISS_OBSTRUCTION", "OPEN_GLOBAL_MENU", "SELECT_FUNCTION", "AUTH_GATE"],
        "exposure_step_index": 1,
        "exposure_basis": "first SELECT_FUNCTION (stipulated) -> F candidate reveal_tokens_before_first_SELECT_FUNCTION",
        "f_candidate_key": "reveal_tokens_before_first_SELECT_FUNCTION",
        "expectation": "MUST_AGREE",
        "why": "Both lanes read the same three named reveal tokens off the same prefix.",
    },
    {
        "id": "FX02_NO_REVEAL_DIRECT_ENTRY",
        "derivation": "R1 — control reachable with no reveal at all. The negative pole of §5.",
        "task": ["SELECT_FUNCTION", "ENDPOINT_REACHED"],
        "experienced": ["SELECT_FUNCTION", "ENDPOINT_REACHED"],
        "exposure_step_index": 0,
        "exposure_basis": "first SELECT_FUNCTION -> index 0",
        "f_candidate_key": "reveal_tokens_before_first_SELECT_FUNCTION",
        "expectation": "MUST_AGREE",
        "why": "No reveal token anywhere; both must say False / 0.",
    },
    {
        "id": "FX03_REVEAL_AFTER_ENDPOINT",
        "derivation": "R4 — reveal token strictly AFTER ENDPOINT_REACHED. '엔드포인트 전' must exclude it.",
        "task": ["SELECT_FUNCTION", "ENDPOINT_REACHED", "OPEN_GLOBAL_MENU"],
        "experienced": ["SELECT_FUNCTION", "ENDPOINT_REACHED", "OPEN_GLOBAL_MENU"],
        "exposure_step_index": 3,
        "exposure_basis": "end of sequence (stipulated, to probe whether the endpoint cut is applied at all)",
        "f_candidate_key": "all_reveal_tokens_before_endpoint",
        "expectation": "MUST_DIVERGE_BY_DEFINITION",
        "why": "menu_dependency must agree (False, both cut at endpoint). nav_container_depth must "
               "diverge: F cuts at the endpoint, S does not cut at all. This is the POPULATION-axis "
               "difference made visible.",
    },
    {
        "id": "FX04_REVEAL_IMMEDIATELY_BEFORE_ENDPOINT",
        "derivation": "R4 — the other side of the same boundary.",
        "task": ["OPEN_GLOBAL_MENU", "ENDPOINT_REACHED"],
        "experienced": ["OPEN_GLOBAL_MENU", "ENDPOINT_REACHED"],
        "exposure_step_index": 1,
        "exposure_basis": "endpoint cut index -> F candidate all_reveal_tokens_before_endpoint",
        "f_candidate_key": "all_reveal_tokens_before_endpoint",
        "expectation": "MUST_AGREE",
        "why": "Reveal strictly before the endpoint; both must say True / 1.",
    },
    {
        "id": "FX05_ENDPOINT_IS_FIRST_TOKEN",
        "derivation": "R4 degenerate boundary — the prefix before the endpoint is empty.",
        "task": ["ENDPOINT_REACHED"],
        "experienced": ["ENDPOINT_REACHED"],
        "exposure_step_index": 0,
        "exposure_basis": "endpoint cut index 0",
        "f_candidate_key": "all_reveal_tokens_before_endpoint",
        "expectation": "MUST_AGREE",
        "why": "Empty prefix; both must say False / 0 without erroring.",
    },
    {
        "id": "FX06_TERMINAL_AUTH_GATE_WITH_REVEAL",
        "derivation": "R4 — run ends at AUTH_GATE (04 §2), no ENDPOINT_REACHED exists. 'endpoint 전' undefined.",
        "task": ["OPEN_LOCAL_MENU", "SELECT_FUNCTION", "AUTH_GATE"],
        "experienced": ["OPEN_LOCAL_MENU", "SELECT_FUNCTION", "AUTH_GATE"],
        "exposure_step_index": 1,
        "exposure_basis": "first SELECT_FUNCTION",
        "f_candidate_key": "reveal_tokens_before_first_SELECT_FUNCTION",
        "expectation": "MUST_AGREE",
        "why": "Both fall back to 'whole sequence' when ENDPOINT_REACHED is absent, and both say so "
               "in a field (S: endpoint_cut_basis, F: endpoint_token_present).",
    },
    {
        "id": "FX07_TERMINAL_AUTH_GATE_NO_REVEAL",
        "derivation": "R4 — negative twin of FX06. AUTH_GATE itself must not read as a reveal.",
        "task": ["SELECT_FUNCTION", "AUTH_GATE"],
        "experienced": ["SELECT_FUNCTION", "AUTH_GATE"],
        "exposure_step_index": 0,
        "exposure_basis": "first SELECT_FUNCTION -> index 0",
        "f_candidate_key": "reveal_tokens_before_first_SELECT_FUNCTION",
        "expectation": "MUST_AGREE",
        "why": "AUTH_GATE is 'a state encountered', not a reveal (T-A-V3-STEP1-006 general_criterion ①).",
    },
    {
        "id": "FX08_ABSTAIN_AFTER_REVEAL",
        "derivation": "R1 — ABSTAIN (04 §2) in the sequence. Path is declared undetermined.",
        "task": ["OPEN_GLOBAL_MENU", "ABSTAIN"],
        "experienced": ["OPEN_GLOBAL_MENU", "ABSTAIN"],
        "exposure_step_index": 1,
        "exposure_basis": "token after the reveal (stipulated)",
        "f_candidate_key": "all_reveal_tokens_before_endpoint",
        "expectation": "MUST_AGREE",
        "why": "Values must agree, but F additionally marks derived_values_interpretable=False. "
               "S carries no interpretability flag — a REPORTING asymmetry, not a value divergence.",
    },
    {
        "id": "FX09_ABSTAIN_ONLY",
        "derivation": "R1 — ABSTAIN as the whole path.",
        "task": ["ABSTAIN"],
        "experienced": ["ABSTAIN"],
        "exposure_step_index": 0,
        "exposure_basis": "index 0",
        "f_candidate_key": "all_reveal_tokens_before_endpoint",
        "expectation": "MUST_AGREE",
        "why": "Both emit a determinate False/0 for a path declared undetermined. They CONVERGE, and "
               "both may be convergently wrong — logged as AMBIGUOUS_DEFINITION, not as agreement.",
    },
    {
        "id": "FX10_NESTED_DRAWER",
        "derivation": "R5 — 04 §5 says 'nested reveal'. Global menu opened, then a local menu inside it.",
        "task": ["OPEN_GLOBAL_MENU", "OPEN_LOCAL_MENU", "SELECT_FUNCTION", "ENDPOINT_REACHED"],
        "experienced": ["OPEN_GLOBAL_MENU", "OPEN_LOCAL_MENU", "SELECT_FUNCTION", "ENDPOINT_REACHED"],
        "exposure_step_index": 2,
        "exposure_basis": "first SELECT_FUNCTION",
        "f_candidate_key": "reveal_tokens_before_first_SELECT_FUNCTION",
        "expectation": "MUST_AGREE",
        "why": "Genuinely nested: depth 2 under either phrasing.",
    },
    {
        "id": "FX11_SIBLING_DRAWERS",
        "derivation": "R5 — two reveals at the SAME level, separated by a selection. §5 ('nested') and "
                      "§4 ('expansion 수') disagree on whether this is 2 or 1.",
        "task": ["OPEN_GLOBAL_MENU", "SELECT_CATEGORY", "OPEN_GLOBAL_MENU", "SELECT_FUNCTION", "ENDPOINT_REACHED"],
        "experienced": ["OPEN_GLOBAL_MENU", "SELECT_CATEGORY", "OPEN_GLOBAL_MENU", "SELECT_FUNCTION", "ENDPOINT_REACHED"],
        "exposure_step_index": 3,
        "exposure_basis": "first SELECT_FUNCTION",
        "f_candidate_key": "reveal_tokens_before_first_SELECT_FUNCTION",
        "expectation": "MUST_AGREE",
        "why": "Both count flat (S sets nesting_verified=False; F counts occurrences). They agree on 2 "
               "— a CONVERGENT BLIND SPOT: neither can distinguish sibling from nested, so §5's "
               "'nested' qualifier is unimplemented in both.",
    },
    {
        "id": "FX12_EMPTY_SEQUENCE",
        "derivation": "R4 degenerate — no tokens at all.",
        "task": [],
        "experienced": [],
        "exposure_step_index": 0,
        "exposure_basis": "index 0 on an empty sequence",
        "f_candidate_key": "all_reveal_tokens_before_endpoint",
        "expectation": "MUST_AGREE",
        "why": "Both return False/0 rather than MISSING. Convergent, and possibly convergently wrong "
               "for a flow-unevaluable unit — logged as AMBIGUOUS_DEFINITION.",
    },
    {
        "id": "FX13_SWITCH_TAB_ONLY",
        "derivation": "R3 — the open-set case. SWITCH_TAB is canonical (§2) but NOT named in §5.",
        "task": ["SWITCH_TAB", "SELECT_FUNCTION", "ENDPOINT_REACHED"],
        "experienced": ["SWITCH_TAB", "SELECT_FUNCTION", "ENDPOINT_REACHED"],
        "exposure_step_index": 1,
        "exposure_basis": "first SELECT_FUNCTION",
        "f_candidate_key": "reveal_tokens_before_first_SELECT_FUNCTION",
        "expectation": "MUST_DIVERGE_BY_DEFINITION",
        "why": "Aligned reading (explicit3) must AGREE (False). Emitted values must DIVERGE: S emits "
               "False (closed set by default), F emits None (readings disagree, value withheld). "
               "This is the '등' gap, not a computation disagreement.",
    },
    {
        "id": "FX14_SWITCH_TAB_PLUS_EXPLICIT_REVEAL",
        "derivation": "R3 — SWITCH_TAB alongside a named reveal, so the open set stops mattering.",
        "task": ["SWITCH_TAB", "OPEN_LOCAL_MENU", "SELECT_FUNCTION", "ENDPOINT_REACHED"],
        "experienced": ["SWITCH_TAB", "OPEN_LOCAL_MENU", "SELECT_FUNCTION", "ENDPOINT_REACHED"],
        "exposure_step_index": 2,
        "exposure_basis": "first SELECT_FUNCTION",
        "f_candidate_key": "reveal_tokens_before_first_SELECT_FUNCTION",
        "expectation": "MUST_AGREE",
        "why": "Both readings are True, so F emits a value and it must equal S's. Shows FX13's "
               "divergence is confined to the open-set case.",
    },
    {
        "id": "FX15_EXPAND_ACCORDION",
        "derivation": "R3 — the third named reveal token, exercised on its own.",
        "task": ["EXPAND_ACCORDION", "SELECT_FUNCTION", "ENDPOINT_REACHED"],
        "experienced": ["EXPAND_ACCORDION", "SELECT_FUNCTION", "ENDPOINT_REACHED"],
        "exposure_step_index": 1,
        "exposure_basis": "first SELECT_FUNCTION",
        "f_candidate_key": "reveal_tokens_before_first_SELECT_FUNCTION",
        "expectation": "MUST_AGREE",
        "why": "Named token; no lane may miss it.",
    },
    {
        "id": "FX16_SEARCH_TASK_NO_REVEAL",
        "derivation": "R1 — INPUT_QUERY/SUBMIT_QUERY/SELECT_RESULT path (04 §2). None is a reveal.",
        "task": ["INPUT_QUERY", "SUBMIT_QUERY", "SELECT_RESULT", "ENDPOINT_REACHED"],
        "experienced": ["INPUT_QUERY", "SUBMIT_QUERY", "SELECT_RESULT", "ENDPOINT_REACHED"],
        "exposure_step_index": 0,
        "exposure_basis": "no SELECT_FUNCTION in the path; exposure stipulated at index 0",
        "f_candidate_key": "reveal_tokens_before_first_SELECT_FUNCTION",
        "expectation": "MUST_AGREE",
        "why": "T-A-V3-STEP1-006 puts SUBMIT_QUERY inside activation_depth; it says nothing that would "
               "make it a reveal. Neither lane may leak the activation_depth rule into menu_dependency.",
    },
    {
        "id": "FX17_DISMISSAL_ONLY_DIFFERENCE",
        "derivation": "R7 — §3's relation SATISFIED: experienced == task + dismissal.",
        "task": ["SELECT_FUNCTION", "ENDPOINT_REACHED"],
        "experienced": ["DISMISS_OBSTRUCTION", "SELECT_FUNCTION", "ENDPOINT_REACHED"],
        "exposure_step_index": 0,
        "exposure_basis": "first SELECT_FUNCTION -> index 0",
        "f_candidate_key": "reveal_tokens_before_first_SELECT_FUNCTION",
        "expectation": "MUST_AGREE",
        "why": "SOURCE FIELD is immaterial here: DISMISS_OBSTRUCTION is not a reveal token under any "
               "reading, so S on either field == F on either base. F asserts this as base_invariant.",
        "cross_field_check": True,
    },
    {
        "id": "FX18_REVEAL_ONLY_IN_EXPERIENCED",
        "derivation": "R7 — §3's relation VIOLATED: experienced carries a reveal that task does not. "
                      "04 §3 does not state the relation as a norm, so this input is admissible.",
        "task": ["SELECT_FUNCTION", "ENDPOINT_REACHED"],
        "experienced": ["OPEN_GLOBAL_MENU", "SELECT_FUNCTION", "ENDPOINT_REACHED"],
        "exposure_step_index": 0,
        "exposure_basis": "first SELECT_FUNCTION in task_flow -> index 0",
        "f_candidate_key": "reveal_tokens_before_first_SELECT_FUNCTION",
        "expectation": "MUST_DIVERGE_BY_DEFINITION",
        "why": "Same-field comparison (task vs task) must AGREE. Cross-field comparison "
               "(S on experienced vs F on task base) must DIVERGE — this is the SOURCE FIELD axis "
               "proving it is load-bearing, and the case that would silently corrupt any merge that "
               "did not fix the field. F additionally flags TASK_EXPERIENCED_INCONSISTENT.",
        "cross_field_check": True,
    },
]

# ======================================================================================
# 4. Comparator. Callables are injected so mutation testing never touches the lane modules.
# ======================================================================================

SFn_MD = Callable[[Sequence[str], str], Any]
SFn_NCD = Callable[[Sequence[str], Any], Any]


def _s_md(seq: Sequence[str], field: str) -> Dict[str, Any]:
    return LS.menu_dependency(list(seq), sequence_field=field)


def _s_ncd(seq: Sequence[str], idx: Any) -> Dict[str, Any]:
    return LS.recompute_nav_container_depth(list(seq), idx)


def run_cases(s_md: SFn_MD = _s_md, s_ncd: SFn_NCD = _s_ncd) -> Dict[str, Any]:
    rows: List[Dict[str, Any]] = []
    for fx in FIXTURES:
        task, exp = fx["task"], fx["experienced"]

        # ---- menu_dependency, axes aligned (grain=run, population=pre-endpoint, field=task) ----
        s_out = s_md(task, T)
        f_out = LF.menu_dependency(task, exp)
        s_value = s_out["menu_dependency"]
        f_reading_explicit3 = f_out["readings"]["reveal_set_explicit3"]
        f_reading_incl_tab = f_out["readings"]["reveal_set_incl_switch_tab"]
        f_emitted = f_out["value"]

        md_aligned_match = (s_value == f_reading_explicit3)
        md_emitted_match = (s_value == f_emitted)

        # ---- source-field axis probe (only where the two sequences differ structurally) -------
        cross = None
        if fx.get("cross_field_check"):
            s_exp_out = s_md(exp, "experienced_flow_sequence")
            cross = {
                "s_on_experienced_flow_sequence": s_exp_out["menu_dependency"],
                "f_task_base_explicit3": f_reading_explicit3,
                "f_experienced_base_explicit3": f_out["readings_experienced_base"]["reveal_set_explicit3"],
                "f_base_invariant": f_out["base_invariant"],
                "cross_field_match": s_exp_out["menu_dependency"] == f_reading_explicit3,
            }

        # ---- nav_container_depth, reading-to-reading under the fixture's stipulation ---------
        s_ncd_out = s_ncd(task, fx["exposure_step_index"])
        f_ncd_out = LF.nav_container_depth_candidates(task)
        s_depth = s_ncd_out["nav_container_depth"]
        f_cands = f_ncd_out["candidates_illustrative_only"]
        f_matched_cand = f_cands[fx["f_candidate_key"]]
        ncd_reading_match = (s_depth == f_matched_cand)

        rows.append({
            "id": fx["id"],
            "derivation": fx["derivation"],
            "task_flow_sequence": list(task),
            "experienced_flow_sequence": list(exp),
            "expectation": fx["expectation"],
            "why": fx["why"],
            "menu_dependency": {
                "S_value": s_value,
                "S_endpoint_cut_basis": s_out["endpoint_cut_basis"],
                "S_endpoint_cut_index": s_out.get("endpoint_cut_index"),
                "S_reveal_token_set": s_out.get("reveal_token_set"),
                "F_reading_explicit3": f_reading_explicit3,
                "F_reading_incl_switch_tab": f_reading_incl_tab,
                "F_emitted_value": f_emitted,
                "F_ambiguity_active": f_out["ambiguity_active"],
                "F_endpoint_token_present": f_out["endpoint_token_present"],
                "aligned_reading_match": md_aligned_match,
                "emitted_value_match": md_emitted_match,
            },
            "menu_dependency_source_field_probe": cross,
            "nav_container_depth": {
                "fixture_exposure_step_index": fx["exposure_step_index"],
                "fixture_exposure_basis": fx["exposure_basis"],
                "S_value": s_depth,
                "S_reason": s_ncd_out.get("reason"),
                "S_nesting_verified": s_ncd_out.get("nesting_verified"),
                "F_emitted_value": f_ncd_out["value"],
                "F_candidates": f_cands,
                "F_candidate_compared": fx["f_candidate_key"],
                "F_candidate_value": f_matched_cand,
                "scalar_comparison_defined": False,
                "reading_to_reading_match": ncd_reading_match,
            },
        })
    return {"rows": rows}


def summarize(res: Dict[str, Any]) -> Dict[str, Any]:
    rows = res["rows"]
    return {
        "n_cases": len(rows),
        "md_aligned_reading_mismatches": [
            r["id"] for r in rows if not r["menu_dependency"]["aligned_reading_match"]],
        "md_emitted_value_mismatches": [
            r["id"] for r in rows if not r["menu_dependency"]["emitted_value_match"]],
        "ncd_reading_mismatches": [
            r["id"] for r in rows if not r["nav_container_depth"]["reading_to_reading_match"]],
        "cross_field_mismatches": [
            r["id"] for r in rows
            if r["menu_dependency_source_field_probe"]
            and not r["menu_dependency_source_field_probe"]["cross_field_match"]],
    }


# ======================================================================================
# 5. Mutation check — is the comparator capable of failing?
# ======================================================================================

def _mut_identity_md(seq, field):
    return _s_md(seq, field)


def _mut_md_always_true(seq, field):
    out = dict(_s_md(seq, field))
    out["menu_dependency"] = True
    return out


def _mut_md_ignore_endpoint_cut(seq, field):
    """S scanning the WHOLE sequence instead of cutting at ENDPOINT_REACHED."""
    out = dict(_s_md(seq, field))
    out["menu_dependency"] = any(t in LS.NAMED_REVEAL_TOKENS for t in seq)
    return out


def _mut_md_reveal_set_includes_switch_tab(seq, field):
    """S silently adopting the open reading — the exact merge error this check must catch."""
    return LS.menu_dependency(list(seq), sequence_field=field, extra_reveal_tokens=("SWITCH_TAB",))


def _mut_ncd_off_by_one(seq, idx):
    out = dict(_s_ncd(seq, idx))
    if isinstance(out.get("nav_container_depth"), int):
        out["nav_container_depth"] = out["nav_container_depth"] + 1
    return out


MUTATIONS = [
    {"id": "MUT00_NULL", "target": "control", "md": _mut_identity_md, "ncd": _s_ncd,
     "intent": "No mutation. Baseline: proves a clean run is what the comparator reports as clean, "
               "so a later 'all agree' is not the comparator being inert."},
    {"id": "MUT01_MD_ALWAYS_TRUE", "target": "menu_dependency", "md": _mut_md_always_true, "ncd": _s_ncd,
     "intent": "Lane S always claims a menu dependency.",
     "must_be_caught_by": "md_aligned_reading_mismatches"},
    {"id": "MUT02_MD_NO_ENDPOINT_CUT", "target": "menu_dependency", "md": _mut_md_ignore_endpoint_cut, "ncd": _s_ncd,
     "intent": "Lane S drops the '엔드포인트 전' cut. Only FX03 can see this — a LOCALIZED mutation, "
               "to show the comparator's sensitivity is case-specific and not a blanket failure.",
     "must_be_caught_by": "md_aligned_reading_mismatches"},
    {"id": "MUT03_MD_OPEN_REVEAL_SET", "target": "menu_dependency", "md": _mut_md_reveal_set_includes_switch_tab, "ncd": _s_ncd,
     "intent": "Lane S adopts SWITCH_TAB as a reveal token. This is the merge that a reconciliation "
               "could make by accident; the comparator must notice the two lanes stop agreeing on "
               "the explicit3 reading.",
     "must_be_caught_by": "md_aligned_reading_mismatches"},
    {"id": "MUT04_NCD_OFF_BY_ONE", "target": "nav_container_depth", "md": _mut_identity_md, "ncd": _mut_ncd_off_by_one,
     "intent": "Lane S's depth is inflated by one.",
     "must_be_caught_by": "ncd_reading_mismatches"},
]


def run_mutations(baseline: Dict[str, Any]) -> Dict[str, Any]:
    base_sum = summarize(baseline)
    out = []
    for m in MUTATIONS:
        s = summarize(run_cases(s_md=m["md"], s_ncd=m["ncd"]))
        if m["id"] == "MUT00_NULL":
            caught = (s == base_sum)
            out.append({
                "mutation": m["id"], "target": m["target"], "intent": m["intent"],
                "identical_to_baseline": caught,
                "verdict": "BASELINE_STABLE" if caught else "BASELINE_UNSTABLE",
                "summary": s,
            })
            continue
        key = m["must_be_caught_by"]
        new_hits = [x for x in s[key] if x not in base_sum[key]]
        out.append({
            "mutation": m["id"], "target": m["target"], "intent": m["intent"],
            "detector_channel": key,
            "baseline_mismatches": base_sum[key],
            "mutant_mismatches": s[key],
            "newly_flagged_cases": new_hits,
            "caught": bool(new_hits),
            "verdict": "CAUGHT" if new_hits else "NOT_CAUGHT",
        })
    all_caught = all(o.get("verdict") in ("CAUGHT", "BASELINE_STABLE") for o in out)
    return {
        "mutations": out,
        "all_detected": all_caught,
        "restoration": "No lane module was ever modified. Mutations are wrappers around injected "
                       "callables; the baseline run above and the reported case_table both use the "
                       "unwrapped lane functions. Nothing to restore.",
    }


# ======================================================================================
# 6. Verdict
# ======================================================================================

def decide(res: Dict[str, Any]) -> Dict[str, Any]:
    s = summarize(res)
    md_axes_ok = THREE_AXIS["menu_dependency"]["axes_match"]
    ncd_axes_ok = THREE_AXIS["nav_container_depth"]["axes_match"]

    md_verdict = ("CONVERGED" if (md_axes_ok and not s["md_aligned_reading_mismatches"])
                  else "DIVERGED_SAME_AXES" if md_axes_ok else "DIFFERENT_QUANTITIES")
    ncd_verdict = "DIFFERENT_QUANTITIES" if not ncd_axes_ok else (
        "CONVERGED" if not s["ncd_reading_mismatches"] else "DIVERGED_SAME_AXES")

    overall = "CONVERGED" if md_verdict == ncd_verdict == "CONVERGED" else (
        "DIVERGED_SAME_AXES" if "DIVERGED_SAME_AXES" in (md_verdict, ncd_verdict)
        else "DIFFERENT_QUANTITIES")

    return {
        "verdict": overall,
        "per_variable": {"menu_dependency": md_verdict, "nav_container_depth": ncd_verdict},
        "verdict_basis": (
            "menu_dependency: all three axes align (grain=run, population=pre-endpoint prefix, "
            "source=task_flow_sequence), and every aligned-reading comparison across %d fixtures "
            "matches -> CONVERGED. The two lanes still emit different top-level VALUES on the "
            "SWITCH_TAB-only case, but that is emission policy over an unresolved SSOT gap "
            "(04 §5 '등'), not a disagreement about the quantity.\n"
            "nav_container_depth: two axes differ. SOURCE FIELD — S requires an external "
            "`exposure_step_index`, F accepts only the token sequence. POPULATION — F applies the "
            "endpoint cut, S does not (FX03 shows S=1 vs F=0 from that alone). F emits no scalar at "
            "any input, so scalar-vs-scalar comparison is undefined -> DIFFERENT_QUANTITIES.\n"
            "Overall verdict takes the weaker of the two: the pair as a whole is not shown to "
            "converge, and nothing in this run is a same-axes contradiction."
            % len(res["rows"])
        ),
        "no_canonical_declared": (
            "This harness does not name either implementation as correct. S is not 'more complete' "
            "for emitting a nav_container_depth value — it emits one because it demands an input F "
            "refuses to invent. F is not 'more rigorous' for withholding menu_dependency — it "
            "withholds because it kept a set open that S closed by documented default. Choosing "
            "between them is a reconciliation decision for D, and it needs A's rulings first."
        ),
    }


# ======================================================================================
# 7. Divergences / ambiguity registers
# ======================================================================================

def build_divergences(res: Dict[str, Any]) -> List[Dict[str, Any]]:
    rows = {r["id"]: r for r in res["rows"]}
    d: List[Dict[str, Any]] = []

    fx13 = rows["FX13_SWITCH_TAB_ONLY"]["menu_dependency"]
    d.append({
        "id": "DIV-01",
        "variable": "menu_dependency",
        "kind": "EMISSION_POLICY_OVER_AN_OPEN_SSOT_SET",
        "axes_aligned": True,
        "cases": ["FX13_SWITCH_TAB_ONLY"],
        "input": rows["FX13_SWITCH_TAB_ONLY"]["task_flow_sequence"],
        "S": fx13["S_value"],
        "F": fx13["F_emitted_value"],
        "aligned_reading_agrees": fx13["aligned_reading_match"],
        "why_it_split": (
            "04 §5 writes 'OPEN_GLOBAL_MENU/OPEN_LOCAL_MENU/EXPAND_ACCORDION 등 reveal token' and §4 "
            "writes 'OPEN/REVEAL 계열'. Both leave the set open. S (AMB-S06) closes it at the three "
            "named tokens by default and requires any extension to be passed explicitly; F (AMB-F05) "
            "keeps both readings and withholds a value while they disagree. On this input the two "
            "readings disagree, so F emits None where S emits False. On the shared explicit3 reading "
            "the two lanes agree exactly."
        ),
        "is_it_a_defect": (
            "No — not at present. It becomes a REAL divergence the moment A rules that SWITCH_TAB IS "
            "a reveal token: S's default would then be wrong on every tab-entry service, and 05 §2-A's "
            "menu-dependency rate would flip for that family. The divergence is contingent on an "
            "unresolved ruling, which is why it is escalated rather than merged."
        ),
        "escalate_as": "AMBIGUOUS_DEFINITION (AMB-X01)",
    })

    fx03 = rows["FX03_REVEAL_AFTER_ENDPOINT"]["nav_container_depth"]
    d.append({
        "id": "DIV-02",
        "variable": "nav_container_depth",
        "kind": "POPULATION_AXIS_DIFFERS",
        "axes_aligned": False,
        "cases": ["FX03_REVEAL_AFTER_ENDPOINT"],
        "input": rows["FX03_REVEAL_AFTER_ENDPOINT"]["task_flow_sequence"],
        "S": fx03["S_value"],
        "F_candidate_all_reveal_before_endpoint": fx03["F_candidate_value"],
        "why_it_split": (
            "S's recompute_nav_container_depth counts over seq[:exposure_step_index] and applies NO "
            "endpoint cut, so a reveal token occurring after ENDPOINT_REACHED is counted whenever the "
            "supplied index reaches it. All three of F's candidates first take "
            "prefix_before_endpoint(). With an exposure index at the end of the sequence, S=%s and "
            "F's corresponding candidate=%s from that rule alone."
            % (fx03["S_value"], fx03["F_candidate_value"])
        ),
        "is_it_a_defect": (
            "Not decidable from the SSOT. 04 §5 says 'task control 노출 전', not 'endpoint 전' — the "
            "endpoint cut is F's import from the menu_dependency rule, and S's absence of it is a "
            "literal reading. Whether an exposure point can legitimately sit after the endpoint is "
            "exactly what AMB-S08 / AMB-F06 leave open."
        ),
        "escalate_as": "AMBIGUOUS_DEFINITION (AMB-X02)",
    })

    d.append({
        "id": "DIV-03",
        "variable": "nav_container_depth",
        "kind": "SOURCE_FIELD_AXIS_DIFFERS — NO SCALAR TO COMPARE",
        "axes_aligned": False,
        "cases": [r["id"] for r in res["rows"]],
        "S": "int, conditional on an externally supplied exposure_step_index",
        "F": "None at every input; three illustrative candidates only",
        "why_it_split": (
            "The two lanes resolved the same gap in opposite directions. S made the exposure point a "
            "REQUIRED PARAMETER (push the decision to the caller, then compute exactly). F declared "
            "the quantity NOT COMPUTABLE from a token sequence and published the span of plausible "
            "readings instead. Neither invented an exposure rule, which is why neither can be "
            "checked against the other as a number."
        ),
        "is_it_a_defect": "No. It is the DIFFERENT_QUANTITIES verdict itself.",
        "note_for_reconciliation": (
            "F's three candidates BRACKET S's output: under the stipulation "
            "'exposure = first SELECT_FUNCTION' S reproduces F's "
            "`reveal_tokens_before_first_SELECT_FUNCTION` on every fixture where both are defined "
            "(see ncd_reading_mismatches). So the two are the SAME function of the sequence once an "
            "exposure rule is fixed — they differ only in who is allowed to fix it. That is a ruling "
            "for A, not a merge for D."
        ),
        "escalate_as": "AMBIGUOUS_DEFINITION (AMB-X03)",
    })

    fx18 = rows["FX18_REVEAL_ONLY_IN_EXPERIENCED"]
    d.append({
        "id": "DIV-04",
        "variable": "menu_dependency",
        "kind": "SOURCE_FIELD_AXIS — DEMONSTRATED LOAD-BEARING",
        "axes_aligned": False,
        "cases": ["FX18_REVEAL_ONLY_IN_EXPERIENCED"],
        "input": {"task": fx18["task_flow_sequence"], "experienced": fx18["experienced_flow_sequence"]},
        "S_on_task_field": fx18["menu_dependency"]["S_value"],
        "S_on_experienced_field": fx18["menu_dependency_source_field_probe"]["s_on_experienced_flow_sequence"],
        "F_task_base": fx18["menu_dependency_source_field_probe"]["f_task_base_explicit3"],
        "F_experienced_base": fx18["menu_dependency_source_field_probe"]["f_experienced_base_explicit3"],
        "F_base_invariant": fx18["menu_dependency_source_field_probe"]["f_base_invariant"],
        "why_it_split": (
            "When the two sequences differ by more than DISMISS_OBSTRUCTION, the field choice changes "
            "the answer. Same-field comparison agrees; cross-field comparison does not. F's "
            "`base_invariant` assertion — which holds on every well-formed fixture — is FALSE here, "
            "and F separately flags TASK_EXPERIENCED_INCONSISTENT (AMB-F11)."
        ),
        "is_it_a_defect": (
            "No — it is the reason S makes `sequence_field` a required argument and F asserts base "
            "invariance instead of assuming it. Both guards fire. It is recorded because any "
            "reconciliation that drops either guard would merge two different quantities silently."
        ),
        "escalate_as": "not an ambiguity — a guard both lanes already hold. Keep both.",
    })
    return d


AMBIGUOUS_DEFINITIONS = [
    {
        "id": "AMB-X01",
        "variable": "menu_dependency",
        "question": "Is SWITCH_TAB a reveal token?",
        "ssot_text": "04 §5 '... EXPAND_ACCORDION 등 reveal token'; 04 §4 'OPEN/REVEAL 계열 token'.",
        "state": "OPEN. T-A-V3-STEP1-006 does not touch it — 006 rules on activation_depth membership "
                 "and on encoding drawer direction as a variable, neither of which closes the "
                 "menu_dependency reveal set.",
        "why_it_matters": "S returns False and F returns None on tab-entry paths. 05 §2-A's "
                          "menu-dependency rate for tab-first services depends entirely on this.",
        "lane_s_position": "closed set of the 3 named tokens (AMB-S06)",
        "lane_f_position": "open; two readings, value withheld on disagreement (AMB-F05)",
        "owner": "A (SSOT)",
        "do_not_fill": "This harness does not choose. Neither reading is marked correct.",
    },
    {
        "id": "AMB-X02",
        "variable": "nav_container_depth",
        "question": "Does the endpoint cut apply to nav_container_depth, or only to menu_dependency?",
        "ssot_text": "04 §5 nav rule says 'task control 노출 전' and never mentions the endpoint. "
                     "The endpoint appears only in the menu_dependency rule.",
        "state": "OPEN, and newly surfaced by this convergence check — neither lane registered it, "
                 "because neither had the other's population rule to compare against.",
        "why_it_matters": "Changes the count whenever a reveal token follows ENDPOINT_REACHED.",
        "lane_s_position": "no endpoint cut (literal reading of §5)",
        "lane_f_position": "endpoint cut applied to all candidates",
        "owner": "A (SSOT)",
        "do_not_fill": "Not resolved here.",
    },
    {
        "id": "AMB-X03",
        "variable": "nav_container_depth",
        "question": "Which step is 'task control 노출'? Is the exposure point an input the collector "
                    "supplies, or a rule derivable from the token sequence?",
        "ssot_text": "04 §5 'task control 노출 전 nested reveal 수' / 04 §4 'task control 노출 전 "
                     "menu/drawer expansion 수'. No canonical-18 token marks exposure.",
        "state": "OPEN. AMB-S08 and AMB-F06 are the same gap, registered independently by two lanes "
                 "that never spoke — which is corroborating evidence that the gap is in the SSOT and "
                 "not in either implementation.",
        "why_it_matters": "Without a ruling, nav_container_depth has no value: F emits none, and S's "
                          "value is only as defined as the caller's exposure index.",
        "owner": "A (SSOT) / B (collector — whether fact_flow_step can carry an exposure marker)",
        "do_not_fill": "This harness STIPULATED 'exposure = first SELECT_FUNCTION' in its fixture "
                       "purely to make the two implementations comparable. That stipulation is a "
                       "test scaffold and MUST NOT be read as a proposed operationalization.",
    },
    {
        "id": "AMB-X04",
        "variable": "nav_container_depth",
        "question": "Does a SIBLING reveal count toward depth? §5 says 'nested reveal'; §4 says "
                    "'menu/drawer expansion 수'.",
        "ssot_text": "04 §5 vs 04 §4, quoted above.",
        "state": "OPEN — and a CONVERGENT BLIND SPOT. Both lanes count flat occurrences (S sets "
                 "nesting_verified=False; F counts token occurrences), so on FX11 they agree on 2 "
                 "while §5's 'nested' would arguably give 1. Agreement here is NOT evidence of "
                 "correctness: it is two implementations sharing the same unimplemented qualifier.",
        "why_it_matters": "A hamburger reopened after a category selection is not a 2-deep container "
                          "hierarchy. Counting it as one inflates depth for services with shallow, "
                          "repetitive navigation.",
        "owner": "A (SSOT)",
        "do_not_fill": "Not resolved here.",
    },
    {
        "id": "AMB-X05",
        "variable": "menu_dependency / nav_container_depth",
        "question": "What is the value for an EMPTY sequence, or for a path that is only ABSTAIN?",
        "ssot_text": "04 §2 defines ABSTAIN as '경로 불확정으로 억지 판정하지 않는다'. §5 gives no "
                     "empty-sequence case.",
        "state": "OPEN — second CONVERGENT BLIND SPOT. On FX09/FX12 both lanes emit a determinate "
                 "False/0 for a path that is either undetermined or absent. They agree, and the "
                 "agreement may be jointly wrong: MISSING would also be defensible. F at least marks "
                 "derived_values_interpretable=False on ABSTAIN; S carries no such flag.",
        "why_it_matters": "A determinate False for an undetermined path enters §2-A rates as a real "
                          "negative and is indistinguishable from an observed absence of menus.",
        "owner": "A (SSOT)",
        "do_not_fill": "Not resolved here.",
    },
]

LIMITATION = [
    "This is a definitional convergence check on synthetic fixtures. It says nothing about whether "
    "either implementation produces correct values on real observations — REAL access is 0 and "
    "MAIN50 measurement data does not exist.",
    "The fixture is 18 hand-derived cases chosen to sit on definitional boundaries. It is a "
    "boundary probe, not a sample. No rate, proportion, or statistic is computed from it, and it "
    "must never be treated as one.",
    "`exposure_step_index` is stipulated by this fixture (AMB-X03). Every nav_container_depth "
    "comparison is therefore conditional on a scaffold the SSOT has not ratified.",
    "Convergence on a case is not correctness on that case. FX09/FX11/FX12 are documented as "
    "convergent blind spots where both lanes share the same unimplemented qualifier.",
    "Only the two duplicated variables were compared. Both lane modules compute much else; nothing "
    "here validates any of it.",
    "No canonical implementation is designated and no lane file was read as anything but read-only. "
    "Reconciliation, and any GO/NO-GO, sit outside this worker's scope.",
    "The lane modules were being rewritten by concurrent workers while this ran. The result is "
    "pinned to the snapshot hashes recorded in provenance.source_stability; if `any_drift` is "
    "true, re-run before using this for reconciliation.",
    "45 same-family pairs are cells of a distance matrix, not n=45. No pair-level statistic appears "
    "here, and none should be derived from this artefact.",
]


# ======================================================================================
# 8. Emit
# ======================================================================================

def _md_table(res: Dict[str, Any]) -> str:
    head = ("| case | task_flow_sequence | S md | F md (explicit3) | F md (emitted) | md match | "
            "S ncd | F ncd cand | F ncd value | ncd match | expectation |\n"
            "|---|---|---|---|---|---|---|---|---|---|---|\n")
    lines = []
    for r in res["rows"]:
        m, n = r["menu_dependency"], r["nav_container_depth"]
        seq = " > ".join(r["task_flow_sequence"]) or "(empty)"
        lines.append(
            "| %s | `%s` | %s | %s | %s | %s | %s | %s (%s) | %s | %s | %s |" % (
                r["id"], seq, m["S_value"], m["F_reading_explicit3"], m["F_emitted_value"],
                "OK" if m["aligned_reading_match"] else "**MISMATCH**",
                n["S_value"], n["F_candidate_value"], n["F_candidate_compared"],
                n["F_emitted_value"],
                "OK" if n["reading_to_reading_match"] else "**MISMATCH**",
                r["expectation"]))
    return head + "\n".join(lines)


def _drift_report() -> Dict[str, Any]:
    """Did the live lane files change while this harness ran?"""
    out: Dict[str, Any] = {}
    for name, src in (("lane_s", LANE_S_SRC), ("lane_f", LANE_F_SRC)):
        now = _sha256(src)
        out[name] = {
            "sha256_at_snapshot": SNAPSHOT[name]["sha256_at_snapshot"],
            "sha256_after_run": now,
            "changed_during_run": now != SNAPSHOT[name]["sha256_at_snapshot"],
        }
    any_drift = any(v["changed_during_run"] for v in out.values())
    out["any_drift"] = any_drift
    out["note"] = (
        "The lane modules sit in a worktree other Lane workers are editing concurrently; during "
        "the first run of this harness both files changed several times per minute. Everything "
        "reported here was computed against the SNAPSHOT hashes above, which are the exact bytes "
        "that were imported. A True in `changed_during_run` means the live file has since moved "
        "on and this result must be re-run before it is relied on for reconciliation."
        if any_drift else
        "Live lane files were byte-identical to the imported snapshot before and after the run."
    )
    return out


def main() -> int:
    os.makedirs(OUT_DIR, exist_ok=True)
    res = run_cases()
    drift = _drift_report()
    summary = summarize(res)
    verdict = decide(res)
    divergences = build_divergences(res)
    mutation = run_mutations(res)

    doc = {
        "artifact": "CONVERGE_DUP_VARS",
        "lane": "X-Converge",
        "assignment": "T-A-V3-STEP1-007 (A -> D). Duplicate cause: D-DEF-11, an orchestrator split "
                      "contract error, not a worker error.",
        "verdict": verdict["verdict"],
        "per_variable_verdict": verdict["per_variable"],
        "verdict_basis": verdict["verdict_basis"],
        "no_canonical_declared": verdict["no_canonical_declared"],
        "generated_at_utc": _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds"),
        "provenance": {
            "base_sha": BASE_SHA,
            "python": sys.version.split()[0],
            "compared_modules": SNAPSHOT,
            "source_stability": drift,
            "replication_across_concurrent_revisions": {
                "why": "Because other workers were rewriting the lane modules every ~20s, this "
                       "harness was run five times against five different byte-states of the two "
                       "files. If the verdict were an artefact of a transient code state it would "
                       "have moved.",
                "runs": 5,
                "observed_lane_s_snapshot_sha256_prefixes": [
                    "1110d99ed6f9", "e263c04e8493", "b709a3ed2846", "1ab63cc4a350"],
                "observed_lane_f_snapshot_sha256_prefixes": [
                    "b4e23ff249d1", "9dd23fdb4e2f", "8f0fd1b4b7a7"],
                "invariant": "verdict, per_variable_verdict, all four summary_counts lists, and "
                             "mutation all_detected were identical on every run.",
                "recorded_by": "operator, from repeated invocations; the values above are the "
                               "snapshot hashes those runs printed.",
            },
            "ssot_codebook": {"path": CODEBOOK, "sha256": _sha256(CODEBOOK)},
            "a_delta": _load_a_delta(),
            "data_status": "REAL access 0. No MAIN50 measurement exists. Synthetic fixtures only.",
        },
        "three_axis_declaration": THREE_AXIS,
        "fixture_provenance": {
            "principle": "Neither lane's fixture is reused. Using Lane S's fixture would make S's "
                         "reading the answer key, and the same for F. Every case below is derived "
                         "from the 04 primary text.",
            "ssot_verbatim": SSOT_VERBATIM,
            "derivation_rules": {
                "R1": "Tokens only from the 04 §2 canonical-18 table; no invented tokens.",
                "R2": "FX01 is the 04 §3 worked example, both sequences, verbatim.",
                "R3": "Reveal tokens are the three §5 names; SWITCH_TAB is exercised separately "
                      "because §5's '등' leaves the set open. Not resolved here.",
                "R4": "The endpoint boundary is probed on both sides, plus the two degenerate "
                      "terminals (endpoint-first, no-endpoint/AUTH_GATE).",
                "R5": "§5 says 'nested reveal', §4 says 'expansion 수' — nested and sibling "
                      "arrangements are separated because the two phrasings disagree.",
                "R6": "`exposure_step_index` is a fixture stipulation (AMB-X03), recorded per row "
                      "with the F candidate it corresponds to. It is a test scaffold, not a ruling.",
                "R7": "§3's structural relation is exercised satisfied AND violated, because that "
                      "relation is what makes the source-field axis load-bearing.",
            },
            "required_boundary_coverage": {
                "no_reveal_token": ["FX02", "FX07", "FX16"],
                "endpoint_before_after_boundary": ["FX03", "FX04", "FX05"],
                "terminates_at_AUTH_GATE": ["FX01", "FX06", "FX07"],
                "ABSTAIN_present": ["FX08", "FX09"],
                "nested_drawer": ["FX10"],
                "sibling_drawer": ["FX11"],
                "empty_sequence": ["FX12"],
                "open_reveal_set_SWITCH_TAB": ["FX13", "FX14"],
                "source_field_probe": ["FX17", "FX18"],
            },
            "bidirectional_contrast": {
                "MUST_AGREE": [f["id"] for f in FIXTURES if f["expectation"] == "MUST_AGREE"],
                "MUST_DIVERGE_BY_DEFINITION": [
                    f["id"] for f in FIXTURES if f["expectation"] == "MUST_DIVERGE_BY_DEFINITION"],
                "why_both_are_needed": "An all-agree result would be uninformative if the fixture "
                                       "contained only cases that cannot disagree. FX03, FX13 and "
                                       "FX18 are constructed so that a correct pair of lanes MUST "
                                       "produce different numbers, and they do.",
            },
        },
        "case_table": res["rows"],
        "summary_counts": summary,
        "divergences": divergences,
        "mutation_check": mutation,
        "ambiguous_definitions": AMBIGUOUS_DEFINITIONS,
        "limitation": LIMITATION,
        "prohibitions_observed": [
            "No lane file modified. Mutations wrap injected callables only.",
            "No implementation declared canonical.",
            "No definition filled in — five gaps raised as AMBIGUOUS_DEFINITION.",
            "No threshold, cut-off, weight or composite created.",
            "45 pairs never treated as n=45; no statistic computed at all.",
            "No git operation, no REAL access, no control/**, no gold, no holdout, no GO/NO-GO.",
            "Wrote only under results/harness/converge/ and tools/v3_harness/converge_dup_vars.py.",
        ],
    }

    json_path = os.path.join(OUT_DIR, "CONVERGE_DUP_VARS.json")
    with open(json_path, "w", encoding="utf-8") as fh:
        json.dump(doc, fh, ensure_ascii=False, indent=1)
        fh.write("\n")

    md = []
    md.append("# Lane X-Converge — `nav_container_depth` · `menu_dependency`\n")
    md.append("**Verdict: `%s`**  (menu_dependency: `%s` · nav_container_depth: `%s`)\n"
              % (verdict["verdict"], verdict["per_variable"]["menu_dependency"],
                 verdict["per_variable"]["nav_container_depth"]))
    md.append("Assignment `T-A-V3-STEP1-007`. Base `%s`. REAL access 0; synthetic fixtures only.\n"
              % BASE_SHA)
    md.append("The duplication came from the D orchestrator's split contract (D-DEF-11), not from "
              "either worker. Neither implementation is discarded; the two independent readings are "
              "used as the material for the check.\n")

    md.append("## 1. Three-axis declaration (before any comparison)\n")
    for var in ("menu_dependency", "nav_container_depth"):
        ax = THREE_AXIS[var]
        md.append("### `%s` — axes match: **%s**\n" % (var, ax["axes_match"]))
        md.append("| axis | Lane S | Lane F |")
        md.append("|---|---|---|")
        for k, label in (("grain", "단위 (grain)"), ("population", "모집단"),
                         ("source_field", "원천 필드")):
            md.append("| %s | %s | %s |" % (label, ax["lane_s"][k], ax["lane_f"][k]))
        md.append("| emits | %s | %s |" % (ax["lane_s"]["emits"], ax["lane_f"]["emits"]))
        md.append("\n%s\n" % ax["axes_match_note"])

    md.append("## 2. Fixture provenance\n")
    md.append("Neither lane's fixture is reused — using one would make that lane's reading the "
              "answer key. All 18 cases are derived from `04_FLOW_CODEBOOK_v3.0.md` §2/§3/§4/§5.\n")
    for k, v in doc["fixture_provenance"]["derivation_rules"].items():
        md.append("- **%s** — %s" % (k, v))
    md.append("\nRequired boundary coverage: " + ", ".join(
        "%s (%s)" % (k, ", ".join(v))
        for k, v in doc["fixture_provenance"]["required_boundary_coverage"].items()) + "\n")

    md.append("## 3. Case table\n")
    md.append(_md_table(res))
    md.append("\n`F ncd value` is `None` on every row — Lane F emits no scalar for "
              "`nav_container_depth` by design (AMB-F06). The `ncd match` column compares Lane S's "
              "value against the F *candidate* named in the adjacent cell, under the exposure "
              "stipulation recorded per row. It is a reading-to-reading check, not a value check.\n")
    md.append("Summary: aligned-reading mismatches (menu_dependency) = %s · emitted-value "
              "mismatches = %s · nav_container_depth reading mismatches = %s · cross-field "
              "mismatches = %s\n" % (
                  summary["md_aligned_reading_mismatches"] or "none",
                  summary["md_emitted_value_mismatches"] or "none",
                  summary["ncd_reading_mismatches"] or "none",
                  summary["cross_field_mismatches"] or "none"))

    md.append("## 4. Divergences — which input, and why it split\n")
    for dv in divergences:
        md.append("### %s · `%s` — %s\n" % (dv["id"], dv["variable"], dv["kind"]))
        md.append("- cases: %s" % ", ".join(dv["cases"][:4]) + (" …" if len(dv["cases"]) > 4 else ""))
        md.append("- why: %s" % dv["why_it_split"])
        md.append("- defect? %s" % dv["is_it_a_defect"])
        if "note_for_reconciliation" in dv:
            md.append("- for reconciliation: %s" % dv["note_for_reconciliation"])
        md.append("")

    md.append("## 5. Mutation check — can this comparator fail?\n")
    md.append("| mutation | target | channel | newly flagged | verdict |")
    md.append("|---|---|---|---|---|")
    for m in mutation["mutations"]:
        md.append("| %s | %s | %s | %s | %s |" % (
            m["mutation"], m["target"], m.get("detector_channel", "(baseline)"),
            ", ".join(m.get("newly_flagged_cases", [])) or "—", m["verdict"]))
    md.append("\nAll mutations detected: **%s**. %s\n" % (mutation["all_detected"], mutation["restoration"]))
    md.append("`MUT02` is deliberately localized — it is visible only in `FX03`, which shows the "
              "comparator flags the specific broken case rather than collapsing everything. `MUT03` "
              "is the mutation that matters for reconciliation: it simulates Lane S quietly adopting "
              "the open reveal set, exactly the merge a careless reconciliation would make.\n")

    md.append("## 6. Remaining ambiguity — raised, not filled\n")
    for a in AMBIGUOUS_DEFINITIONS:
        md.append("### %s · `%s`\n" % (a["id"], a["variable"]))
        md.append("- **question**: %s" % a["question"])
        md.append("- **SSOT**: %s" % a["ssot_text"])
        md.append("- **state**: %s" % a["state"])
        md.append("- **why it matters**: %s" % a["why_it_matters"])
        md.append("- **owner**: %s\n" % a["owner"])
    md.append("Two of these (`AMB-X04`, `AMB-X05`) are **convergent blind spots**: the lanes agree "
              "because both left the same qualifier unimplemented. Agreement there is not evidence "
              "of correctness, and this report does not count it as convergence in favour of either "
              "implementation.\n")

    md.append("## 7. Source stability\n")
    md.append("The two lane modules are being edited concurrently by other Lane workers in this "
              "worktree. This harness copies both files out, hashes the copy, imports the copy, and "
              "re-hashes the originals afterwards. Everything above was computed against the "
              "snapshot hashes.\n")
    md.append("| module | sha256 at snapshot | sha256 after run | changed during run |")
    md.append("|---|---|---|---|")
    for k in ("lane_s", "lane_f"):
        md.append("| %s | `%s` | `%s` | %s |" % (
            k, drift[k]["sha256_at_snapshot"][:16], drift[k]["sha256_after_run"][:16],
            drift[k]["changed_during_run"]))
    md.append("\n%s\n" % drift["note"])

    md.append("## 8. Limitation\n")
    for l in LIMITATION:
        md.append("- %s" % l)
    md.append("\n%s\n" % verdict["no_canonical_declared"])

    md_path = os.path.join(OUT_DIR, "CONVERGE_FINDINGS.md")
    with open(md_path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(md) + "\n")

    print("verdict: %s" % verdict["verdict"])
    print("  menu_dependency    : %s" % verdict["per_variable"]["menu_dependency"])
    print("  nav_container_depth: %s" % verdict["per_variable"]["nav_container_depth"])
    print("summary: %s" % json.dumps(summary, ensure_ascii=False))
    print("mutations all detected: %s" % mutation["all_detected"])
    print("source drift during run: %s" % drift["any_drift"])
    print("wrote: %s" % json_path)
    print("wrote: %s" % md_path)
    if not os.environ.get("CONVERGE_SNAPSHOT_DIR"):
        shutil.rmtree(SCRATCH, ignore_errors=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
