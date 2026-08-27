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
from typing import Any, Iterable, Mapping, Sequence

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
# Unambiguous state-changing activations (open / switch / expand / select / detail):
ACTIVATION_CORE: frozenset[str] = frozenset({
    "OPEN_GLOBAL_MENU", "OPEN_LOCAL_MENU", "SWITCH_TAB", "EXPAND_ACCORDION",
    "SELECT_CATEGORY", "SELECT_FUNCTION", "SELECT_RESULT",
    "OPEN_ITEM_DETAIL", "OPEN_PLACE_DETAIL",
})
# C CHOICE C-1: SUBMIT_QUERY executes a control and changes page state → counted as activation.
#   Flip with derive(..., submit_is_activation=False); derive always also reports
#   activation_depth_excl_submit.
SUBMIT_IS_ACTIVATION_DEFAULT: bool = True
# C CHOICE C-2: form-intent tokens are typing / value-selection, NOT activation depth (04 §5 "typing 제외").
#   derive always also reports activation_depth_incl_form (the flipped value).
FORM_INTENT_TOKENS: frozenset[str] = frozenset({
    "INPUT_QUERY", "SELECT_ORIGIN", "SELECT_DESTINATION", "SELECT_DATE",
})
# ---- 04 §5 menu_dependency / nav_container_depth: "OPEN/REVEAL 계열 token"
# C CHOICE C-3: reveal = OPEN_GLOBAL_MENU, OPEN_LOCAL_MENU, EXPAND_ACCORDION (the three named in 04 §5).
#   SWITCH_TAB is a view switch, not a container reveal → NOT reveal (menu_dependency_incl_tab reported as alt).
REVEAL_TOKENS: frozenset[str] = frozenset({"OPEN_GLOBAL_MENU", "OPEN_LOCAL_MENU", "EXPAND_ACCORDION"})
REVEAL_TOKENS_INCL_TAB: frozenset[str] = REVEAL_TOKENS | {"SWITCH_TAB"}
# ---- 04 §5 flow_step_count: "task-intent token 수. typing/submit/auth encounter 포함, scroll/passive 제외."
# C CHOICE C-4: task-intent = every canonical token except DISMISS_OBSTRUCTION (obstruction, not task),
#   ENDPOINT_REACHED (terminal state marker, not an action) and ABSTAIN (non-judgement).
TASK_INTENT_TOKENS: frozenset[str] = (ACTIVATION_CORE | FORM_INTENT_TOKENS | {"SUBMIT_QUERY", "AUTH_GATE"})
# ---- nav_container_depth anchor ("task control 노출 전"):
# C CHOICE C-5: the task control is considered exposed at the first token that acts ON the task control
#   itself (not a container, not a category): SELECT_FUNCTION or any task-body token.
TASK_CONTROL_ANCHOR_TOKENS: frozenset[str] = frozenset({
    "SELECT_FUNCTION", "INPUT_QUERY", "SELECT_ORIGIN", "SELECT_DESTINATION", "SELECT_DATE",
    "SUBMIT_QUERY", "SELECT_RESULT", "OPEN_ITEM_DETAIL", "OPEN_PLACE_DETAIL",
})
# ---- auth_gate_stage positions (00 §6 / 04 §4):
# C CHOICE C-6: task discovery/select = SELECT_FUNCTION or SELECT_CATEGORY; task body = form + submit + result/detail.
TASK_SELECT_TOKENS: frozenset[str] = frozenset({"SELECT_FUNCTION", "SELECT_CATEGORY"})
TASK_BODY_TOKENS: frozenset[str] = FORM_INTENT_TOKENS | {
    "SUBMIT_QUERY", "SELECT_RESULT", "OPEN_ITEM_DETAIL", "OPEN_PLACE_DETAIL",
}
TERMINAL_TOKENS: frozenset[str] = frozenset({"ENDPOINT_REACHED", "AUTH_GATE", "ABSTAIN"})

# ---- entry_zone thresholds (04 §6 leaves them unspecified)
# C CHOICE C-7: TOP band y < 0.15 (mobile header + first row), BOTTOM band y >= 0.85 (bottom nav / sticky CTA),
#   MID otherwise; TOP band split at thirds of x (x < 1/3 LEFT, 1/3 <= x <= 2/3 CENTER, x > 2/3 RIGHT).
#   DRAWER takes precedence over FLOATING (coordinates of a drawer control are post-reveal and not
#   comparable to landing geometry); FLOATING takes precedence over bands.
ZONE_TOP_Y: float = 0.15
ZONE_BOTTOM_Y: float = 0.85
ZONE_X_LEFT: float = 1.0 / 3.0
ZONE_X_RIGHT: float = 2.0 / 3.0

PSEUDO_REPLICATION_GUARD = "pairs are cells, not independent n"

Tokens = Sequence[str]


# ============================================================================
# token classification
# ============================================================================

def classify_token(token: str, *, submit_is_activation: bool = SUBMIT_IS_ACTIVATION_DEFAULT,
                   form_is_activation: bool = False) -> dict[str, bool]:
    """Classify one canonical token (04 §2) into the derivation classes of 04 §5.

    Returns {state_changing_activation, task_intent, reveal, dismiss, auth, endpoint}.
    Raises ValueError for a non-canonical token (scroll / passive wait are NOT tokens in
    04 §2; they are measured elsewhere — 04 §4 first_visible_scroll_state).
    C choices applied: C-1 (SUBMIT_QUERY), C-2 (form-intent), C-3 (reveal set), C-4 (task-intent set).
    """
    if token not in CANONICAL_TOKENS:
        raise ValueError(f"non-canonical token: {token!r} (04 §2)")
    activation = token in ACTIVATION_CORE
    if token == "SUBMIT_QUERY":
        activation = bool(submit_is_activation)
    if token in FORM_INTENT_TOKENS:
        activation = bool(form_is_activation)
    return {
        "state_changing_activation": activation,
        "task_intent": token in TASK_INTENT_TOKENS,
        "reveal": token in REVEAL_TOKENS,
        "dismiss": token == "DISMISS_OBSTRUCTION",
        "auth": token == "AUTH_GATE",
        "endpoint": token == "ENDPOINT_REACHED",
    }


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

def auth_gate_stage_from_sequence(seq: Tokens, *, terminal_auth_is_endpoint: bool = False) -> str:
    """Position-based auth_gate_stage (04 §4, 00 §6) from a task_flow_sequence.

    NONE                  — no AUTH_GATE.
    BEFORE_TASK_DISCOVERY — no TASK_SELECT token (SELECT_FUNCTION/SELECT_CATEGORY) precedes the first
                            AUTH_GATE. (A reveal like OPEN_GLOBAL_MENU alone is not discovery.)
    AT_ENDPOINT           — AUTH_GATE immediately precedes ENDPOINT_REACHED, OR AUTH_GATE is the last token
                            and at least one TASK_BODY token (form/submit/result/detail) occurred after
                            task select (the task body was entered; auth blocks only the final view).
    AFTER_TASK_SELECT     — otherwise (auth encountered right after selecting the task, before any body).
    C CHOICE C-6. ``terminal_auth_is_endpoint=True`` gives the literal alternative reading in which any
    terminal AUTH_GATE that replaces ENDPOINT_REACHED is AT_ENDPOINT; derive() reports both.
    """
    seq = list(seq)
    if "AUTH_GATE" not in seq:
        return "NONE"
    i = seq.index("AUTH_GATE")
    before = seq[:i]
    if not any(t in TASK_SELECT_TOKENS for t in before):
        return "BEFORE_TASK_DISCOVERY"
    is_last = i == len(seq) - 1
    next_is_endpoint = (i + 1 < len(seq)) and seq[i + 1] == "ENDPOINT_REACHED"
    if next_is_endpoint:
        return "AT_ENDPOINT"
    if is_last:
        if terminal_auth_is_endpoint:
            return "AT_ENDPOINT"
        first_sel = next(k for k, t in enumerate(before) if t in TASK_SELECT_TOKENS)
        if any(t in TASK_BODY_TOKENS for t in before[first_sel + 1:]):
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
           drop_noncanonical: bool = False) -> dict[str, Any]:
    """Recompute every derived field of 02 §4 fact_flow_observation from the two raw sequences (00 §7).

    activation_depth        04 §5 — count of state-changing activation tokens in task_flow (C-1, C-2).
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
                violations.append(f"{name}: terminal token {t} at index {i} is not last (00 §6 AUTH_GATE terminal / 04 §2)")
                break

    cls = {t: classify_token(t, submit_is_activation=submit_is_activation) for t in set(task)}
    activation_depth = sum(1 for t in task if cls[t]["state_changing_activation"])
    activation_excl_submit = sum(1 for t in task if classify_token(t, submit_is_activation=False)["state_changing_activation"])
    activation_incl_form = sum(1 for t in task if classify_token(t, submit_is_activation=submit_is_activation,
                                                                 form_is_activation=True)["state_changing_activation"])
    flow_step_count = sum(1 for t in task if cls[t]["task_intent"])

    pre_end = _before_terminal(task)
    menu_dependency = int(any(t in REVEAL_TOKENS for t in pre_end))
    menu_dependency_incl_tab = int(any(t in REVEAL_TOKENS_INCL_TAB for t in pre_end))

    anchor_idx = next((i for i, t in enumerate(task) if t in TASK_CONTROL_ANCHOR_TOKENS), None)
    if anchor_idx is None:
        nav_depth = sum(1 for t in pre_end if t in REVEAL_TOKENS)
        anchor_found = False
    else:
        nav_depth = sum(1 for t in task[:anchor_idx] if t in REVEAL_TOKENS)
        anchor_found = True

    # C CHOICE C-9: an ABSTAIN sequence (04 §2) is not flow-evaluable (05 §6); its flow-derived numeric
    # fields are None (missing), never 0, so family denominators shrink instead of being diluted.
    flow_evaluable = "ABSTAIN" not in task
    if not flow_evaluable:
        activation_depth = activation_excl_submit = activation_incl_form = None  # type: ignore[assignment]
        flow_step_count = menu_dependency = menu_dependency_incl_tab = nav_depth = None  # type: ignore[assignment]
    return {
        "task_flow_sequence": task,
        "experienced_flow_sequence": exp,
        "flow_evaluable": flow_evaluable,
        "activation_depth": activation_depth,
        "activation_depth_excl_submit": activation_excl_submit,
        "activation_depth_incl_form": activation_incl_form,
        "flow_step_count": flow_step_count,
        "menu_dependency": menu_dependency,
        "menu_dependency_incl_tab": menu_dependency_incl_tab,
        "nav_container_depth": nav_depth,
        "nav_anchor_found": anchor_found,
        "forced_dismissal_count": sum(1 for t in exp if t == "DISMISS_OBSTRUCTION"),
        "auth_gate_stage": auth_gate_stage_from_sequence(task) if flow_evaluable else None,
        "auth_gate_stage_alt_terminal_is_endpoint": (auth_gate_stage_from_sequence(task, terminal_auth_is_endpoint=True)
                                                     if flow_evaluable else None),
        "endpoint_status": endpoint_status_from_sequence(task),
        "sequence_consistent": consistent,
        "violations": violations,
        "dropped_noncanonical": sorted(set(dropped_t + dropped_e)),
        "dropped_noncanonical_count": len(dropped_t) + len(dropped_e),
        "submit_is_activation": bool(submit_is_activation),
    }


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


def label_relation(visible: str | None, accessible: str | None, synonym_map: Mapping[str, str], *,
                   casefold: bool = False) -> str:
    """label_relation (04 §4/§5): MATCH / SEMANTIC_EQUIV / DIFFERENT / VISIBLE_ONLY / AX_ONLY / NONE.

    Exact after NFC + whitespace normalisation → MATCH. Otherwise, if both normalised forms map to the
    same canonical key in the EXPLICIT synonym_map (form → key; lookup casefold-insensitive, C-8) →
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
    smap = {normalize_label(k, casefold=True): str(val) for k, val in synonym_map.items()}
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


def seq_distance(a: Tokens | str, b: Tokens | str) -> dict[str, float | int]:
    """Token-level (not character-level) distances for 05 §2 E.

    levenshtein_norm = lev / max(|a|,|b|)  (0 when both empty).
    lcs_sim          = LCS / max(|a|,|b|)  (1 when both empty)  — C choice; lcs_sim_dice = 2·LCS/(|a|+|b|)
    is reported as the alternative normalisation.
    """
    a, _ = _clean(a, drop_noncanonical=True) if isinstance(a, str) else (list(a), [])
    b, _ = _clean(b, drop_noncanonical=True) if isinstance(b, str) else (list(b), [])
    m = max(len(a), len(b))
    lev = _levenshtein(a, b)
    lcs = _lcs(a, b)
    return {
        "len_a": len(a), "len_b": len(b),
        "levenshtein": lev,
        "levenshtein_norm": (lev / m) if m else 0.0,
        "lcs_len": lcs,
        "lcs_sim": (lcs / m) if m else 1.0,
        "lcs_sim_dice": (2 * lcs / (len(a) + len(b))) if (len(a) + len(b)) else 1.0,
    }


def signature(seq: Tokens | str) -> str:
    toks = list(seq) if not isinstance(seq, str) else _clean(seq, drop_noncanonical=True)[0]
    return ">".join(toks)


def pairwise_matrix(family_rows: Sequence[Mapping[str, Any]], *, seq_key: str = "task_flow_sequence",
                    id_key: str = "service_id") -> dict[str, Any]:
    """n×n normalised Levenshtein and LCS-similarity matrices for one family (05 §2 E, §4).

    05 §1: the 45 off-diagonal cells of a 10×10 family are CELLS of one matrix, not 45 independent
    observations; n_service and n_pairs are reported separately with pseudo_replication_guard.
    """
    ids = [str(r[id_key]) for r in family_rows]
    seqs = [list(r[seq_key]) if not isinstance(r[seq_key], str) else _clean(r[seq_key], drop_noncanonical=True)[0]
            for r in family_rows]
    n = len(ids)
    lev = [[0.0] * n for _ in range(n)]
    lcs = [[1.0] * n for _ in range(n)]
    for i in range(n):
        for j in range(i + 1, n):
            d = seq_distance(seqs[i], seqs[j])
            lev[i][j] = lev[j][i] = d["levenshtein_norm"]
            lcs[i][j] = lcs[j][i] = d["lcs_sim"]
    upper = [lev[i][j] for i in range(n) for j in range(i + 1, n)]
    return {
        "service_ids": ids,
        "n_service": n,
        "n_pairs": n * (n - 1) // 2,
        "n_service_warning": None if n == 10 else f"family n={n}, expected 10 (05 §1)",
        "pseudo_replication_guard": PSEUDO_REPLICATION_GUARD,
        "levenshtein_norm": lev,
        "lcs_sim": lcs,
        "levenshtein_norm_cells_median": _median(upper) if upper else None,
        "levenshtein_norm_cells_range": [min(upper), max(upper)] if upper else None,
    }


def unique_signatures(family_rows: Sequence[Mapping[str, Any]], *, seq_key: str = "task_flow_sequence") -> dict[str, Any]:
    """Unique flow signatures (05 §2 E, §4): signature = tokens joined by '>'."""
    c = Counter(signature(r[seq_key]) for r in family_rows)
    return {"n_rows": len(family_rows), "n_unique": len(c), "counts": dict(c.most_common())}


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


def family_summary(rows: Sequence[Mapping[str, Any]], numeric_vars: Sequence[str] = (),
                   categorical_vars: Sequence[str] = (), *, family_id: str | None = None) -> dict[str, Any]:
    """Family-level descriptive summary (05 §4): numeric → median/IQR(type-7)/range with n;
    categorical → distribution + Shannon entropy (bits) + entropy_norm = H/log2(k_observed).

    n_service (denominator, 05 §4 "n=10 고정") and n_pairs = n(n-1)/2 are ALWAYS reported separately
    with pseudo_replication_guard (05 §1, 13). No composite score is produced (05 §3).
    """
    n = len(rows)
    out: dict[str, Any] = {
        "family_id": family_id,
        "n_service": n,
        "n_pairs": n * (n - 1) // 2,
        "n_service_warning": None if n == 10 else f"family n={n}, expected 10 (05 §1)",
        "pseudo_replication_guard": PSEUDO_REPLICATION_GUARD,
        "numeric": {},
        "categorical": {},
    }
    for v in numeric_vars:
        vals = [float(r[v]) for r in rows if r.get(v) is not None]
        miss = n - len(vals)
        if not vals:
            out["numeric"][v] = {"n": 0, "n_missing": miss}
            continue
        q1, q3 = _quantile_type7(vals, 0.25), _quantile_type7(vals, 0.75)
        out["numeric"][v] = {
            "n": len(vals), "n_missing": miss,
            "median": _median(vals), "q1": q1, "q3": q3, "iqr": q3 - q1,
            "min": min(vals), "max": max(vals), "range": max(vals) - min(vals),
            "mean": sum(vals) / len(vals),
        }
    for v in categorical_vars:
        vals = [str(r[v]) for r in rows if r.get(v) is not None]
        c = Counter(vals)
        k = len(c)
        h = shannon_entropy_bits(c)
        out["categorical"][v] = {
            "n": len(vals), "n_missing": n - len(vals),
            "distribution": dict(c.most_common()),
            "k_observed": k,
            "entropy_bits": h,
            "entropy_norm": (h / math.log2(k)) if k > 1 else 0.0,
        }
    return out


# ============================================================================
# denominator chain (05 §6)
# ============================================================================

_CHAIN_STAGES = ("candidate", "eligible_frozen", "attempted", "evidence_bearing", "flow_evaluable")


def denominator_chain(candidate: int, eligible: int, attempted: int, evidence_bearing: int,
                      flow_evaluable: int, *, family_id: str | None = None,
                      reasons: Mapping[str, Sequence[str]] | None = None) -> dict[str, Any]:
    """05 §6 chain: candidate 10 → eligible/frozen 10 → attempted 10 → evidence-bearing n → flow-evaluable n.

    Every stage is reported with count, dropped (vs previous stage) and the caller-supplied reasons.
    Raises ValueError if any later count exceeds an earlier one, or any count is negative.
    """
    counts = [candidate, eligible, attempted, evidence_bearing, flow_evaluable]
    for s, c in zip(_CHAIN_STAGES, counts):
        if not isinstance(c, int) or c < 0:
            raise ValueError(f"denominator chain: {s}={c!r} must be a non-negative int")
    for i in range(1, len(counts)):
        if counts[i] > counts[i - 1]:
            raise ValueError(f"denominator chain non-monotonic: {_CHAIN_STAGES[i]}={counts[i]} > "
                             f"{_CHAIN_STAGES[i-1]}={counts[i-1]} (05 §6)")
    reasons = reasons or {}
    chain = []
    prev = None
    for s, c in zip(_CHAIN_STAGES, counts):
        chain.append({"stage": s, "count": c, "dropped": 0 if prev is None else prev - c,
                      "reasons": list(reasons.get(s, []))})
        prev = c
    notes = []
    if candidate != 10:
        notes.append(f"candidate={candidate}, expected 10 (05 §1)")
    if eligible < candidate:
        notes.append("eligible < candidate: replacement allowed only before freeze (05 §6)")
    return {"family_id": family_id, "chain": chain, "notes": notes}


# ============================================================================
# spatial zone (04 §4 entry_zone; 04 §6 thresholds unspecified → C-7)
# ============================================================================

def entry_zone(x_norm: float | None, y_norm: float | None, is_floating: bool, is_drawer: bool) -> str:
    """entry_zone from normalised centre (04 §4, §6). Raw (x,y) are never discarded (04 §6); zone is a summary.

    Precedence: DRAWER > FLOATING > band. Bands (C-7): y < 0.15 → TOP_{LEFT|CENTER|RIGHT} by x thirds
    (x < 1/3 LEFT, 1/3 <= x <= 2/3 CENTER, x > 2/3 RIGHT); y >= 0.85 → BOTTOM; else MID.
    Raises ValueError if x or y is missing or outside [0, 1].
    """
    if is_drawer:
        return "DRAWER"
    if is_floating:
        return "FLOATING"
    if x_norm is None or y_norm is None:
        raise ValueError("entry_zone needs x_norm and y_norm (04 §6: coordinates are primary)")
    x, y = float(x_norm), float(y_norm)
    if not (0.0 <= x <= 1.0 and 0.0 <= y <= 1.0):
        raise ValueError(f"entry_zone: ({x}, {y}) outside [0,1]")
    if y < ZONE_TOP_Y:
        if x < ZONE_X_LEFT:
            return "TOP_LEFT"
        if x > ZONE_X_RIGHT:
            return "TOP_RIGHT"
        return "TOP_CENTER"
    if y >= ZONE_BOTTOM_Y:
        return "BOTTOM"
    return "MID"


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
