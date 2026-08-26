"""P-C LANE C — 전이 규칙 · AI review cascade · 집계 가드.

`A2 §1.7` · `§1.8` · `§1.11` · `§3` · `§4` / `00 §9`.

가장 중요한 성질 하나: **`UNDETERMINED → PASS` 경로 수는 0이다.**
전건표 32조합을 남김없이 훑어 그것을 확인한다 — 한 줄짜리 assert 로는 증명되지 않는다.
"""

from __future__ import annotations

import itertools
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
RESEARCH = REPO / "research" / "landing_accessibility"
sys.path.insert(0, str(RESEARCH / "src"))

from landing_accessibility.engine import reporting  # noqa: E402
from landing_accessibility.engine.ai_review import (  # noqa: E402
    CRITERION_ALLOWED_LABELS,
    HUMAN_FINAL_REVIEW_MAX,
    TRIAGE_ALLOWED_LABELS,
    EvidencePackage,
    HumanFinalQueue,
    ReviewCascade,
    StubArbiter,
    StubReviewer,
)
from landing_accessibility.engine.transitions import (  # noqa: E402
    LaunderingBlocked,
    TransitionError,
    TransitionInput,
    assert_automation_grade,
    assert_counts_identity,
    assert_frame_column_not_modified,
    assert_no_measurement_status_reclassification,
    assert_not_eligible_has_evidence,
    assert_not_used_as_transition_condition,
    assert_supersede_direction,
    assert_transition_allowed,
    assert_triage_label_domain,
    assert_verdict_state_immutable,
    resolve_final_status,
)
from landing_accessibility.engine.vocabulary import (  # noqa: E402
    AdjudicationStatus,
    AutomationGrade,
    ReviewTaskType,
    VerdictState,
)

V = VerdictState
ADJ = AdjudicationStatus


def _pkg(labels: tuple[str, ...] = CRITERION_ALLOWED_LABELS) -> EvidencePackage:
    return EvidencePackage(
        package_id="p1",
        observation_id="o1",
        screenshot_crop_relpath="o1/l0a/screen_initial.png",
        surrounding_screenshot_relpath=None,
        dom_facts={"role": "dialog"},
        ax_facts={"name": "안내"},
        bbox={"x": 0, "y": 0, "w": 8, "h": 8},
        relevant_text="안내",
        allowed_labels=labels,
    )


# ── 전건표 (A2 §1.11.1) ──────────────────────────────────────────────────────
def test_every_combination_in_the_table_is_covered_and_none_leaks_to_pass() -> None:
    """`verdict_state` 4  x  `ai_review_required` 2  x  adjudication 4 = 32 조합 전수."""
    seen = 0
    for verdict, required, adj in itertools.product(V, (0, 1), [None, *ADJ]):
        if (required == 0) != (adj is None):
            continue
        labels = [None] if adj is not ADJ.RESOLVED else [V.PASS, V.FAIL]
        for label in labels:
            inp = TransitionInput(verdict, required, adj, label)
            try:
                final, _rule = resolve_final_status(inp)
            except TransitionError:
                continue  # 표에 없는 조합은 실패하는 것이 정답이다
            seen += 1
            if verdict is V.UNDETERMINED:
                assert final is V.UNDETERMINED, f"{inp} → {final}"
            if verdict is V.NA:
                assert final is V.NA, f"{inp} → {final}"
    assert seen >= 20


@pytest.mark.parametrize(
    ("verdict", "required", "adj", "label", "expected", "rule"),
    [
        (V.PASS, 0, None, None, V.PASS, "T-2"),
        (V.FAIL, 0, None, None, V.FAIL, "T-2"),
        (V.NA, 0, None, None, V.NA, "T-2·T-6"),
        (V.PASS, 1, ADJ.RESOLVED, V.FAIL, V.FAIL, "T-7"),
        (V.FAIL, 1, ADJ.RESOLVED, V.PASS, V.PASS, "T-7"),
        (V.PASS, 1, ADJ.ABSTAIN, None, V.UNDETERMINED, "T-4"),
        (V.FAIL, 1, ADJ.PENDING, None, V.UNDETERMINED, "T-9"),
        (V.UNDETERMINED, 1, ADJ.RESOLVED, V.PASS, V.UNDETERMINED, "T-8"),
        (V.UNDETERMINED, 1, ADJ.ABSTAIN, None, V.UNDETERMINED, "T-8"),
        (V.NA, 1, ADJ.RESOLVED, V.PASS, V.NA, "T-6"),
        (V.NA, 1, ADJ.ABSTAIN, None, V.NA, "T-6"),
    ],
)
def test_table_rows(
    verdict: VerdictState,
    required: int,
    adj: AdjudicationStatus | None,
    label: VerdictState | None,
    expected: VerdictState,
    rule: str,
) -> None:
    final, applied = resolve_final_status(TransitionInput(verdict, required, adj, label))
    assert final is expected
    assert applied == rule


def test_conflict_order_is_t6_over_t8_over_the_rest() -> None:
    """T-6 > T-8 > T-7 · T-4 · T-9 — 상위 둘은 label 을 읽기 전에 결과를 고정한다."""
    assert resolve_final_status(TransitionInput(V.NA, 1, ADJ.RESOLVED, V.PASS))[1] == "T-6"
    assert (
        resolve_final_status(TransitionInput(V.UNDETERMINED, 1, ADJ.RESOLVED, V.PASS))[1] == "T-8"
    )


# ── 금지 전이 ────────────────────────────────────────────────────────────────
@pytest.mark.parametrize("target", [V.PASS, V.FAIL, V.NA])
def test_undetermined_cannot_move_anywhere(target: VerdictState) -> None:
    """X-1 · X-11 · X-13 — **조건 없는** 금지다."""
    with pytest.raises(LaunderingBlocked):
        assert_transition_allowed(V.UNDETERMINED, target)


@pytest.mark.parametrize("target", [V.PASS, V.FAIL, V.UNDETERMINED])
def test_na_cannot_move_anywhere(target: VerdictState) -> None:
    with pytest.raises(LaunderingBlocked):  # X-15
        assert_transition_allowed(V.NA, target)


def test_verdict_state_is_immutable_across_judgment_versions() -> None:
    assert_verdict_state_immutable(V.PASS, V.PASS)
    with pytest.raises(TransitionError):  # X-10
        assert_verdict_state_immutable(V.UNDETERMINED, V.PASS)


def test_signals_cannot_be_used_as_transition_permission() -> None:
    with pytest.raises(LaunderingBlocked):  # X-9
        assert_not_used_as_transition_condition({"evidence_gap"})
    assert_not_used_as_transition_condition({"verdict_state"})


def test_triage_labels_cannot_hold_verdicts() -> None:
    """규칙 A-2 — 두 겹 중 하나. 쓸 수 있게 두면 T-8 이 우회될 여지가 생긴다."""
    assert_triage_label_domain(
        ReviewTaskType.CRITERION_UNDETERMINED_TRIAGE,
        {"arbiter_label": "RECOLLECT_RECOMMENDED"},
    )
    for bad in ("PASS", "FAIL"):
        with pytest.raises(LaunderingBlocked):
            assert_triage_label_domain(
                ReviewTaskType.CRITERION_UNDETERMINED_TRIAGE, {"arbiter_label": bad}
            )


def test_frame_columns_cannot_be_written_by_an_observation() -> None:
    assert_frame_column_not_modified(observation_writes={"measurement_status": "MEASURED"})
    with pytest.raises(TransitionError):  # W-1 · T-11
        assert_frame_column_not_modified(observation_writes={"web_eligibility_status": "EXCLUDED"})


def test_supersede_only_moves_toward_exclusion() -> None:
    assert_supersede_direction("ELIGIBLE_WEB", "EXCLUDED")
    with pytest.raises(TransitionError):  # W-2
        assert_supersede_direction("EXCLUDED", "ELIGIBLE_WEB")


def test_failed_collection_cannot_be_relabelled_as_out_of_scope() -> None:
    with pytest.raises(TransitionError):  # X-12 · M-5
        assert_no_measurement_status_reclassification(
            "FAILED_ACCESS_BLOCKED", "NOT_ELIGIBLE_AT_COLLECTION"
        )


def test_not_eligible_needs_positive_evidence() -> None:
    assert_not_eligible_has_evidence(
        {"screenshot_initial_path": "a", "dom_path": "b", "final_url": "file:///x"}
    )
    with pytest.raises(TransitionError):  # M-4
        assert_not_eligible_has_evidence({"final_url": "file:///x"})


# ── 항등식 · automation_grade ────────────────────────────────────────────────
def test_applicable_count_identity() -> None:
    assert_counts_identity(applicable_count=3, pass_count=1, fail_count=1, undetermined_count=1)
    with pytest.raises(TransitionError):
        assert_counts_identity(applicable_count=4, pass_count=1, fail_count=1, undetermined_count=1)


def test_automation_grade_constraints() -> None:
    assert_automation_grade(
        grade=AutomationGrade.A_BROWSER_NATIVE,
        final_status=V.PASS,
        ai_review_required=0,
        evidence_present={"probe_path", "dom_path", "ax_path"},
    )
    with pytest.raises(TransitionError):  # G-2
        assert_automation_grade(
            grade=AutomationGrade.E_VLM,
            final_status=V.PASS,
            ai_review_required=0,
            evidence_present={"evidence_package_id", "model_id"},
        )
    with pytest.raises(TransitionError):  # G-5
        assert_automation_grade(
            grade=AutomationGrade.UNGRADED,
            final_status=V.PASS,
            ai_review_required=0,
            evidence_present=set(),
        )
    with pytest.raises(TransitionError):  # G-6
        assert_automation_grade(
            grade=AutomationGrade.A_BROWSER_NATIVE,
            final_status=V.PASS,
            ai_review_required=0,
            evidence_present={"probe_path"},
        )


# ── cascade (00 §9) ──────────────────────────────────────────────────────────
def test_deterministic_stage_short_circuits_the_cascade() -> None:
    """`A1 §1.6` — 1단계에서 판정되면 상위 단계를 호출하지 않는다."""

    class _Det:
        def decide(self, package: EvidencePackage):
            from landing_accessibility.engine.ai_review import DeterministicDecision

            return DeterministicDecision(True, "PASS", AutomationGrade.B_DETERMINISTIC_RULE, "R1")

    class _Boom:
        def review(self, package: EvidencePackage):
            raise AssertionError("상위 단계가 호출됐다")

    result = ReviewCascade(deterministic=_Det(), reviewer_a=_Boom(), reviewer_b=_Boom()).run(
        review_item_id="ri",
        review_task_type=ReviewTaskType.CRITERION_VERDICT,
        verdict_state=V.PASS,
        package=_pkg(),
    )
    assert result.criterion_final_status == "PASS"
    assert result.adjudication.automation_grade == "B_DETERMINISTIC_RULE"


def test_agreeing_reviewers_resolve_and_disagreeing_ones_do_not() -> None:
    agreed = ReviewCascade(
        reviewer_a=StubReviewer("A", "FAIL"), reviewer_b=StubReviewer("B", "FAIL")
    ).run(
        review_item_id="ri",
        review_task_type=ReviewTaskType.CRITERION_VERDICT,
        verdict_state=V.PASS,
        package=_pkg(),
    )
    assert agreed.adjudication.reviewer_agreement == 1
    assert agreed.criterion_final_status == "FAIL"  # T-7 정정

    split = ReviewCascade(
        reviewer_a=StubReviewer("A", "PASS"),
        reviewer_b=StubReviewer("B", "FAIL"),
        arbiter=StubArbiter(abstain=True),
    ).run(
        review_item_id="ri",
        review_task_type=ReviewTaskType.CRITERION_VERDICT,
        verdict_state=V.PASS,
        package=_pkg(),
    )
    assert split.adjudication.final_status == "ABSTAIN"
    assert split.criterion_final_status == "UNDETERMINED"  # T-4 보수화


def test_abstaining_reviewer_makes_agreement_na_not_zero() -> None:
    """`A2 §4.4` — `NA` 를 0 으로 세지 않는다."""
    r = ReviewCascade(
        reviewer_a=StubReviewer("A", None, abstain=True),
        reviewer_b=StubReviewer("B", "FAIL"),
        arbiter=StubArbiter(abstain=True),
    ).run(
        review_item_id="ri",
        review_task_type=ReviewTaskType.CRITERION_VERDICT,
        verdict_state=V.FAIL,
        package=_pkg(),
    )
    assert r.adjudication.reviewer_agreement == "NA"


def test_reviewer_cannot_invent_a_label() -> None:
    """`02 §10` 자유로운 새 기준 생성 금지."""
    with pytest.raises(TransitionError):
        ReviewCascade(
            reviewer_a=StubReviewer("A", "PROBABLY_PASS"), reviewer_b=StubReviewer("B", "PASS")
        ).run(
            review_item_id="ri",
            review_task_type=ReviewTaskType.CRITERION_VERDICT,
            verdict_state=V.PASS,
            package=_pkg(),
        )


def test_undetermined_rows_must_go_through_triage() -> None:
    with pytest.raises(TransitionError):
        ReviewCascade(
            reviewer_a=StubReviewer("A", "PASS"), reviewer_b=StubReviewer("B", "PASS")
        ).run(
            review_item_id="ri",
            review_task_type=ReviewTaskType.CRITERION_VERDICT,
            verdict_state=V.UNDETERMINED,
            package=_pkg(),
        )


def test_triage_of_an_undetermined_row_never_changes_the_verdict() -> None:
    r = ReviewCascade(
        reviewer_a=StubReviewer("A", "RECOLLECT_RECOMMENDED"),
        reviewer_b=StubReviewer("B", "RECOLLECT_RECOMMENDED"),
    ).run(
        review_item_id="ri",
        review_task_type=ReviewTaskType.CRITERION_UNDETERMINED_TRIAGE,
        verdict_state=V.UNDETERMINED,
        package=_pkg(TRIAGE_ALLOWED_LABELS),
    )
    assert r.adjudication.final_status == "RESOLVED"  # triage 는 확정됐다
    assert r.criterion_final_status == "UNDETERMINED"  # 판정은 그대로다
    assert r.applied_rule == "T-8"


def test_human_final_budget_is_five_and_overflow_becomes_abstain() -> None:
    """규칙 A-1 · 금지 전이 X-6 — 예산 부족을 이유로 RESOLVED 로 내리지 않는다."""
    queue = HumanFinalQueue()
    cascade = ReviewCascade(
        reviewer_a=StubReviewer("A", "PASS"),
        reviewer_b=StubReviewer("B", "FAIL"),
        arbiter=StubArbiter(escalate_to_human=True),
        human_queue=queue,
    )
    outcomes = [
        cascade.run(
            review_item_id=f"ri-{i}",
            review_task_type=ReviewTaskType.CRITERION_VERDICT,
            verdict_state=V.FAIL,
            package=_pkg(),
        ).adjudication
        for i in range(HUMAN_FINAL_REVIEW_MAX + 2)
    ]
    assert queue.used == HUMAN_FINAL_REVIEW_MAX
    queue.assert_within_budget()
    assert [o.final_status for o in outcomes[:5]] == ["ESCALATED_HUMAN_FINAL"] * 5
    assert [o.final_status for o in outcomes[5:]] == ["ABSTAIN"] * 2
    assert outcomes[5].ai_review_status == "ESCALATION_DECLINED_BUDGET"


def test_evidence_package_cannot_carry_a_live_target() -> None:
    """`02 §10` — AI 에게는 evidence package 만 전달한다."""
    bad = EvidencePackage(
        package_id="p",
        observation_id="o",
        screenshot_crop_relpath=None,
        surrounding_screenshot_relpath=None,
        dom_facts={"href": "https://service.example.co.kr/login"},
        ax_facts={},
        bbox=None,
        relevant_text=None,
        allowed_labels=CRITERION_ALLOWED_LABELS,
    )
    with pytest.raises(TransitionError):
        bad.assert_no_live_target()


# ── 집계 가드 (A2 §4 · §6.3) ─────────────────────────────────────────────────
def test_auth_gate_prevalence_exposes_the_undercount() -> None:
    entries = [
        {
            "endpoint_status": "FUNCTION_ENDPOINT_REACHED",
            "endpoint_status_detail": "ENDPOINT_VIA_AUTH_GATE",
            "auth_gate_before_endpoint": 0,
        },
        {"endpoint_status": "AUTH_GATE_REACHED", "auth_gate_before_endpoint": 1},
    ]
    stats = reporting.auth_gate_prevalence(entries)
    assert stats["auth_gate_observed"] == 2
    assert stats["naive_endpoint_status_only"] == 1
    reporting.assert_auth_gate_aggregation(entries, reported=2)
    with pytest.raises(reporting.ReportingError):
        reporting.assert_auth_gate_aggregation(entries, reported=1)


def test_gate_endpoint_archetypes_must_be_stratified() -> None:
    entries = [
        {
            "archetype": "COMMUNICATION_ENTRY",
            "endpoint_status_detail": "ENDPOINT_VIA_AUTH_GATE",
            "mpfed": 1,
            "endpoint_reached": 1,
        },
        {
            "archetype": "COMMUNICATION_ENTRY",
            "endpoint_status_detail": None,
            "mpfed": 3,
            "endpoint_reached": 1,
        },
    ]
    summary = reporting.archetype_mpfed_summary(entries)
    reporting.assert_stratified(summary)
    assert summary["COMMUNICATION_ENTRY"]["endpoint_via_auth_gate_rate"] == 0.5
    assert summary["COMMUNICATION_ENTRY"]["strata"]["ENDPOINT_VIA_AUTH_GATE"]["n"] == 1
    with pytest.raises(reporting.ReportingError):
        reporting.assert_stratified({"COMMUNICATION_ENTRY": {"n": 2, "mpfed_median": 2.0}})


def test_censored_observations_are_counted_separately_not_imputed() -> None:
    entries = [
        {
            "archetype": "QUERY",
            "endpoint_status_detail": "UNRESOLVED_DEPTH_BUDGET_EXCEEDED",
            "mpfed": None,
            "endpoint_reached": 0,
        },
        {"archetype": "QUERY", "endpoint_status_detail": None, "mpfed": 2, "endpoint_reached": 1},
    ]
    summary = reporting.archetype_mpfed_summary(entries)["QUERY"]
    assert summary["censored_n"] == 1
    assert summary["mpfed_median"] == 2.0  # 절단분을 8 로 대입하지 않았다
    assert summary["n"] == 2


def test_phase5_report_fails_when_required_disclosures_are_missing() -> None:
    ok = reporting.phase5_measurement_quality(
        adjudications=[{"review_task_type": "CRITERION_VERDICT", "final_status": "RESOLVED"}],
        not_eligible_at_collection_count=0,
        eligibility_reversal_rate=None,
        recollection_runs=0,
        decision_coverage_first_run=None,
        decision_coverage_canonical_run=None,
        unpreregistered_recollection_runs=0,
        over_limit_recollection_runs=0,
    )
    assert "abstention" in ok

    for kwargs in (
        {"adjudications": [{"review_task_type": "CRITERION_VERDICT", "final_status": "PENDING"}]},
        {"not_eligible_at_collection_count": 1},
        {"recollection_runs": 1, "decision_coverage_first_run": 0.8},
        {"unpreregistered_recollection_runs": 1},
    ):
        base = {
            "adjudications": [],
            "not_eligible_at_collection_count": 0,
            "eligibility_reversal_rate": None,
            "recollection_runs": 0,
            "decision_coverage_first_run": None,
            "decision_coverage_canonical_run": None,
            "unpreregistered_recollection_runs": 0,
            "over_limit_recollection_runs": 0,
        }
        with pytest.raises(reporting.ReportingError):
            reporting.phase5_measurement_quality(**{**base, **kwargs})  # type: ignore[arg-type]


def test_undetermined_rows_cannot_be_dropped_from_stress_bound() -> None:
    with pytest.raises(reporting.ReportingError):  # 규칙 N-7
        reporting.assert_undetermined_not_dropped(before=["c1", "c2"], after=["c1"])
