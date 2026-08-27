#!/usr/bin/env python3
"""c_terminal_table — the ONE C table for T-A-V3-STEP1-007 R11 (endpoint_status × terminal_reason).

Pure data + one validation function, stdlib only. Imported by BOTH
  lane5_evidence/evidence_lineage_check.py  (raw evidence records: ALLOWED_TERMINAL is an alias of TERMINAL_ALLOWED)
  lane6_stats/c_flow_derive.py               (validate_terminal / compare_with_mart_row)
so the two lanes can never disagree on the same B row again (RULING_INDEX_COVERAGE_C.md "C-internal defects": lane5
admitted OTHER for every non-REACHED status while lane6 admitted OTHER only with ABSTAIN — BLOCKED×OTHER passed lane5
and failed lane6).

STATUS OF THIS TABLE — C's PRE-REGISTERED PROPOSAL, not a ruling.
  T-A-V3-STEP1-007 R11 (A ruling) fixes: (1) terminal_reason is the mandatory companion of endpoint_status on every
  terminal observation; (2) the 13-value terminal_reason enum; (3) OTHER requires a note; (4) B declares the allowed
  combination table in its runner schema and C verifies it at GATE 1. The combination table below is therefore C's
  pre-registered proposal to be COMPARED with B's schema at GATE 1 (run_gate1 item L5-terminal-reason-table);
  a differing B table is an interpretation-mismatch finding to A (GATE1_RUNBOOK_C.md §5, R14), not a C edit.

C rule for OTHER (unified 2026-08-28):
  OTHER is allowed with ANY non-REACHED endpoint_status (a closed 12-value reason list cannot anticipate every
  non-reach cause, and forcing a wrong specific reason would be worse than an annotated OTHER), but it ALWAYS requires a
  non-empty free-text note (terminal_note); OTHER without a note is a SCHEMA_VIOLATION in lane5 and a violation in lane6.
  REACHED admits no terminal_reason at all (null only) — REACHED × OTHER is impossible like REACHED × TIMEOUT.

Layer separation kept (T-A-V3-STEP1-011 P-17): endpoint_status=ABSTAIN ("we do not know") is distinct from
endpoint_status=PUBLIC_WEB_UNOBSERVABLE × terminal_reason=TASK_SURFACE_ABSENT ("we know it is absent"), and
action_token=ABSTAIN is a different layer from endpoint_status altogether.

Self-test:  python3 c_terminal_table.py   (exit 0 iff the table's structural invariants hold)
"""
from __future__ import annotations

RULE_ID = "T-A-V3-STEP1-007 R11 + T-A-V3-STEP1-027 Δ30 (A ruling: companion field + 16-value enum [BUDGET_EXCEEDED Δ30, NO_TASK_CANDIDATE_FOUND Δ32, PATH_NOT_FOUND_BY_POLICY Δ47] + OTHER needs note; combination table = C proposal; endpoint_status=ABSTAIN × terminal_reason=BUDGET_EXCEEDED = A ruled)"

# endpoint_status enum (04_FLOW_CODEBOOK §4, unchanged by R11) — order as in SSOT
ENDPOINT_STATUSES: tuple[str, ...] = (
    "REACHED", "AUTH_GATE", "PUBLIC_WEB_UNOBSERVABLE", "APP_REQUIRED", "EVIDENCE_DEFECT", "BLOCKED", "ABSTAIN",
)
# terminal_reason 16 values (R11 + Δ30 BUDGET_EXCEEDED + Δ32 NO_TASK_CANDIDATE_FOUND + Δ47 PATH_NOT_FOUND_BY_POLICY)
TERMINAL_REASONS: tuple[str, ...] = (
    "TIMEOUT", "WAF_BLOCK", "ACTIVE_CHALLENGE", "NO_PUBLIC_MOBILE_WEB", "TASK_SURFACE_ABSENT", "APP_REQUIRED",
    "CONTROL_DISABLED_OR_INERT", "FORBIDDEN_ACTION_REQUIRED", "AUTH_REQUIRED", "EVIDENCE_DEFECT",
    "REPLAY_BROKEN", "AMBIGUOUS_MULTIPLE_CANDIDATES", "OTHER", "BUDGET_EXCEEDED", "NO_TASK_CANDIDATE_FOUND", "PATH_NOT_FOUND_BY_POLICY",
)
# auth_gate_stage incl. UNDETERMINED (R13)
AUTH_GATE_STAGES: tuple[str, ...] = ("NONE", "BEFORE_TASK_DISCOVERY", "AFTER_TASK_SELECT", "AT_ENDPOINT", "UNDETERMINED")

OTHER = "OTHER"
OTHER_REQUIRES_NOTE = True   # R11: OTHER 는 note 필수

# Specific (non-OTHER) reasons per endpoint_status. REACHED → none (terminal_reason must be null).
_SPECIFIC: dict[str, frozenset[str]] = {
    "REACHED": frozenset(),
    "AUTH_GATE": frozenset({"AUTH_REQUIRED"}),
    "PUBLIC_WEB_UNOBSERVABLE": frozenset({"NO_PUBLIC_MOBILE_WEB", "TASK_SURFACE_ABSENT"}),
    "APP_REQUIRED": frozenset({"APP_REQUIRED"}),
    "EVIDENCE_DEFECT": frozenset({"EVIDENCE_DEFECT", "REPLAY_BROKEN"}),
    "BLOCKED": frozenset({"TIMEOUT", "WAF_BLOCK", "ACTIVE_CHALLENGE", "CONTROL_DISABLED_OR_INERT",
                          "FORBIDDEN_ACTION_REQUIRED"}),
    "ABSTAIN": frozenset({"AMBIGUOUS_MULTIPLE_CANDIDATES", "BUDGET_EXCEEDED", "NO_TASK_CANDIDATE_FOUND", "PATH_NOT_FOUND_BY_POLICY"}),  # Δ47: 정책 상대적 미발견(R37) — policy_relative+search_strategy 동반  # Δ30 MIN-7 · Δ32 후보 실제 부재(관측); 계약 위반은 RunnerError 이지 행이 아니다
}
# THE table: allowed non-null terminal_reason values per endpoint_status (OTHER on every non-REACHED status).
TERMINAL_ALLOWED: dict[str, frozenset[str]] = {
    es: (rs | {OTHER} if es != "REACHED" else rs) for es, rs in _SPECIFIC.items()
}


def validate_pair(endpoint_status: str | None, terminal_reason: str | None, note: str | None = None) -> list[str]:
    """Return the list of R11 violations for one terminal observation (empty list = OK). Pure; never raises.

    Rules: endpoint_status ∈ ENDPOINT_STATUSES; terminal_reason ∈ TERMINAL_REASONS (None only for REACHED);
    (endpoint_status, terminal_reason) ∈ TERMINAL_ALLOWED; OTHER requires a non-empty note.
    Values are compared after strip().upper() so that a lower-cased B value is reported as the same pair.
    """
    v: list[str] = []
    es = None if endpoint_status is None else str(endpoint_status).strip().upper()
    tr = None if terminal_reason is None else str(terminal_reason).strip().upper()
    if es is None:
        v.append("endpoint_status missing (R11: every terminal observation carries endpoint_status)")
    elif es not in ENDPOINT_STATUSES:
        v.append(f"endpoint_status={es} not in the 7-value SSOT enum (04 §4)")
    if tr is None:
        if es is not None and es != "REACHED":
            v.append(f"terminal_reason missing for endpoint_status={es} (R11: both fields are mandatory)")
    elif tr not in TERMINAL_REASONS:
        v.append(f"terminal_reason={tr} not in R11/Δ30/Δ32/Δ47 16-value enum")
    if es in TERMINAL_ALLOWED and tr is not None and tr in TERMINAL_REASONS and tr not in TERMINAL_ALLOWED[es]:
        if es == "REACHED":
            v.append(f"impossible combination REACHED × terminal_reason={tr} (REACHED admits null only)")
        else:
            v.append(f"endpoint_status={es} × terminal_reason={tr} not an allowed combination "
                     f"(C proposal allows {sorted(TERMINAL_ALLOWED[es])})")
    if tr == OTHER and OTHER_REQUIRES_NOTE and not (isinstance(note, str) and note.strip()):
        v.append("terminal_reason=OTHER requires a non-empty note (R11)")
    return v


def selftest() -> list[str]:
    """Structural invariants of the table; returns problems (empty = OK)."""
    p: list[str] = []
    if set(TERMINAL_ALLOWED) != set(ENDPOINT_STATUSES):
        p.append("table keys != ENDPOINT_STATUSES")
    covered = set().union(*TERMINAL_ALLOWED.values())
    if covered != set(TERMINAL_REASONS):
        p.append(f"reasons unreachable or foreign: {sorted(covered ^ set(TERMINAL_REASONS))}")
    if TERMINAL_ALLOWED["REACHED"]:
        p.append("REACHED must admit no terminal_reason")
    for es in ENDPOINT_STATUSES:
        if es != "REACHED" and OTHER not in TERMINAL_ALLOWED[es]:
            p.append(f"OTHER missing for {es}")
    # every specific reason maps to exactly one endpoint_status (P-17 layer separation stays unambiguous)
    for r in TERMINAL_REASONS:
        if r == OTHER:
            continue
        owners = [es for es, rs in _SPECIFIC.items() if r in rs]
        if len(owners) != 1:
            p.append(f"{r} owned by {owners}")
    if validate_pair("REACHED", None) or validate_pair("BLOCKED", "OTHER", "waf page without challenge markup"):
        p.append("positive pairs rejected")
    if not validate_pair("REACHED", "OTHER", "x") or not validate_pair("BLOCKED", "OTHER") or not validate_pair("ABSTAIN", "TASK_SURFACE_ABSENT"):
        p.append("negative pairs accepted")
    return p


if __name__ == "__main__":
    import sys
    probs = selftest()
    print("c_terminal_table selftest:", "OK" if not probs else probs)
    sys.exit(0 if not probs else 1)


# ---------------------------------------------------------------- Δ32-R29 (T-A-V3-STEP1-028): zero is a claim, not an observation
def validate_zero_depth(activation_depth, endpoint_status, candidates_bound, endpoint_evidence_present) -> list[str]:
    """R29: ``activation_depth=0`` together with ``endpoint_status=REACHED`` needs BOTH (1) endpoint-contract evidence
    and (2) at least one actually-bound candidate. Zero bound candidates can never yield REACHED (schema rejects).
    Pure; returns a list of violations (empty = OK)."""
    v: list[str] = []
    es = None if endpoint_status is None else str(endpoint_status).strip().upper()
    try:
        cb = int(candidates_bound) if candidates_bound is not None else None
    except (TypeError, ValueError):
        cb = None
    if es == "REACHED" and (cb is None or cb < 1):
        v.append("R29: endpoint_status=REACHED with candidates_bound=%r — zero/unknown bound candidates can never be REACHED" % (candidates_bound,))
    if activation_depth == 0 and es == "REACHED" and not endpoint_evidence_present:
        v.append("R29: activation_depth=0 × endpoint_status=REACHED without endpoint-contract evidence")
    return v


# ---------------------------------------------------------------- Δ43-R37 / Δ47-reason16: policy-relative not-found rows
POLICY_RELATIVE_REASONS: frozenset[str] = frozenset({"PATH_NOT_FOUND_BY_POLICY"})
def validate_policy_relative(terminal_reason, policy_relative, search_strategy) -> list[str]:
    """R37: a not-found-by-policy terminal must carry policy_relative=True and a non-empty search_strategy; a row that
    claims policy_relative without a policy-relative reason is also flagged (the two axes verify each other, Δ47)."""
    v: list[str] = []
    tr = None if terminal_reason is None else str(terminal_reason).strip().upper()
    if tr in POLICY_RELATIVE_REASONS:
        if policy_relative is not True: v.append("R37: terminal_reason=%s requires policy_relative=True (got %r)" % (tr, policy_relative))
        if not (isinstance(search_strategy, str) and search_strategy.strip()): v.append("R37: terminal_reason=%s requires search_strategy (got %r)" % (tr, search_strategy))
    elif policy_relative is True:
        v.append("Δ47: policy_relative=True with terminal_reason=%r — not a policy-relative reason" % (terminal_reason,))
    return v
