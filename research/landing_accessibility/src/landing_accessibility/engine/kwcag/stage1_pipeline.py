"""Stage 1 — Outcome 단계 + 파이프라인 조립.

`_finalize` 가 이 패키지에서 **유일하게** `CriterionOutcome` 을 만드는 지점이다.
`Applicability`/`Required evidence slots`/`Expectation` 세 결과를 받아 다음을
코드로 강제한다(`D-R0-23`, `D-R0-52`):

- `NOT_AUTOMATABLE` → 항상 `UNDETERMINED` (Applicability 조차 자동 확정 불가)
- `AUTO_FLAG_ONLY` → 항상 `UNDETERMINED` (`DECISION-1` — FLAG 를 분자에 포함하지 않는다)
- evidence slot 결측(EMPTY/ABSENT) 인데 candidate_verdict=FAIL → `MeasurementFailureAsFailError`
- 이미 구조적으로 UNDETERMINED 로 귀결돼야 하는 경로에서 candidate_verdict 가 PASS/FAIL
  이면 → `UndeterminedLaunderingError`
- candidate_verdict 가 PASS/FAIL 인데 matched_items(evidence) 가 없으면 →
  `EvidenceRequiredError`
- cap_hit 상태에서 candidate_verdict=PASS → `UNDETERMINED` 로 하향(FAIL 은 그대로 둔다 —
  관측된 결함은 절단과 무관하게 유효한 증거이므로)
"""

from __future__ import annotations

from typing import Any

from ..vocabulary import AutomationGrade, VerdictState
from . import stage1_evidence
from .stage1_expectations import EXPECTATION_FUNCS
from .stage1_types import (
    EVALUATOR_VERSION,
    PHYSICAL_EVIDENCE_SLOT,
    ApplicabilityResult,
    ApplicabilityStatus,
    CriterionOutcome,
    EvidenceRequiredError,
    EvidenceSlotResult,
    EvidenceSlotStatus,
    ExpectationResult,
    MeasurementFailureAsFailError,
    SubsetScopeError,
    UndeterminedLaunderingError,
)

OLDER_RELEVANT_IDS = stage1_evidence.OLDER_RELEVANT_IDS
CODEBOOK_AUTOMATION_GRADE = stage1_evidence.CODEBOOK_AUTOMATION_GRADE


def _finalize(
    criterion_id: str,
    applicability: ApplicabilityResult,
    evidence_slot: EvidenceSlotResult,
    expectation: ExpectationResult,
    *,
    codebook_grade: str,
    evidence_ref_base: dict[str, Any],
) -> CriterionOutcome:
    trace: dict[str, Any] = {
        "applicability": applicability,
        "evidence_slot": evidence_slot,
        "expectation": expectation,
    }

    def _ref(**extra: Any) -> dict[str, Any]:
        return {**evidence_ref_base, "physical_evidence_slot": PHYSICAL_EVIDENCE_SLOT, **extra}

    def _undetermined(
        reason: str,
        needs_semantic: bool,
        *,
        evidence_automation_grade: AutomationGrade = AutomationGrade.UNGRADED,
    ) -> CriterionOutcome:
        if expectation.candidate_verdict in (VerdictState.PASS, VerdictState.FAIL):
            raise UndeterminedLaunderingError(
                f"{criterion_id}: 구조적으로 UNDETERMINED 로 귀결돼야 하는데 Expectation 이 "
                f"candidate_verdict={expectation.candidate_verdict} 를 냈다 — 세탁 시도로 간주해 거부한다"
            )
        return CriterionOutcome(
            criterion_id=criterion_id,
            outcome=VerdictState.UNDETERMINED,
            reason=reason,
            evidence_ref=_ref(),
            evaluator_version=EVALUATOR_VERSION,
            needs_semantic=needs_semantic,
            evidence_automation_grade=evidence_automation_grade,
            stage_trace=trace,
        )

    # 1) NOT_AUTOMATABLE — Applicability 조차 자동 확정 불가 (코드북 정의, D-R0-52 구조적 하한).
    if codebook_grade == "NOT_AUTOMATABLE":
        return _undetermined(
            "automation_grade=NOT_AUTOMATABLE — 코드북 정의상 적용기회 자체를 자동 확정할 수 없다",
            True,
        )

    # 2) Applicability 가 UNDETERMINED (여기 오면 원인은 항상 schema gap — NOT_AUTOMATABLE 은 위에서 소진).
    if applicability.status == ApplicabilityStatus.UNDETERMINED:
        return _undetermined(applicability.reason, True)

    # 3) NOT_APPLICABLE → NA. evidence 는 "적용기회가 없다는 관측" 자체가 근거다.
    if applicability.status == ApplicabilityStatus.NOT_APPLICABLE:
        if expectation.candidate_verdict is not None:
            raise UndeterminedLaunderingError(
                f"{criterion_id}: applicability=NOT_APPLICABLE 인데 Expectation 이 "
                f"candidate_verdict={expectation.candidate_verdict} 를 냈다"
            )
        return CriterionOutcome(
            criterion_id=criterion_id,
            outcome=VerdictState.NA,
            reason=applicability.reason,
            evidence_ref=_ref(),
            evaluator_version=EVALUATOR_VERSION,
            needs_semantic=False,
            evidence_automation_grade=AutomationGrade.B_DETERMINISTIC_RULE,
            stage_trace=trace,
        )

    # 여기부터 applicability == APPLICABLE.

    # 4) 내부 일관성 방어선 — APPLICABLE 이면 evidence_slot 도 항목이 있어야 한다
    #    (둘 다 같은 probe 에서 같은 extract 함수로 유도되므로 불일치는 버그다).
    if evidence_slot.status in (
        EvidenceSlotStatus.ABSENT_FROM_PROBE_SCHEMA,
        EvidenceSlotStatus.EMPTY,
    ):
        if expectation.candidate_verdict == VerdictState.FAIL:
            raise MeasurementFailureAsFailError(
                f"{criterion_id}: evidence_slot={evidence_slot.status.value}(측정 결측) 인데 "
                "candidate_verdict=FAIL — 측정 실패를 FAIL 로 전이하는 것은 금지된다(D-R0-23)"
            )
        raise UndeterminedLaunderingError(
            f"{criterion_id}: applicability=APPLICABLE 인데 evidence_slot={evidence_slot.status.value} "
            "— 내부 불일치(버그)"
        )

    # 5) AUTO_FLAG_ONLY — 후보 신호는 기록하되 최종 Outcome 은 항상 UNDETERMINED (DECISION-1).
    if codebook_grade == "AUTO_FLAG_ONLY":
        return _undetermined(
            f"automation_grade=AUTO_FLAG_ONLY — 후보 신호 있음(evidence_slot={evidence_slot.status.value}, "
            f"item_count={evidence_slot.item_count})이나 최종 판정은 사람 검토 필요 "
            "(D-R0-22 우선순위, DECISION-1: FLAG 는 DecisionCoverage 분자에 포함하지 않는다)",
            True,
        )

    # 여기부터 codebook_grade == AUTO_DECIDABLE, applicability == APPLICABLE.

    # 6) Stage 1 에 이 criterion 의 Expectation(공식 조건) 로직이 없다 — 구현 갭이지 measurement
    #    실패가 아니다. FAIL 로 전이하지 않는다(애초에 candidate 자체가 없다).
    if expectation.candidate_verdict is None:
        return _undetermined(
            expectation.reason or "Stage 1 에 이 criterion 의 Expectation 로직이 없다 (구현 갭)",
            False,
        )

    candidate = expectation.candidate_verdict
    if candidate not in (VerdictState.PASS, VerdictState.FAIL):
        raise UndeterminedLaunderingError(
            f"{criterion_id}: AUTO_DECIDABLE 경로에서 candidate_verdict={candidate} 는 있을 수 없다"
        )

    # 7) evidence 없는 PASS/FAIL 생성 금지.
    if not expectation.matched_items:
        raise EvidenceRequiredError(
            f"{criterion_id}: candidate_verdict={candidate.value} 인데 matched_items 가 비어있다"
        )

    # 8) cap 절단 의심 + PASS → 안전한 방향(UNDETERMINED)으로만 내린다. FAIL 은 그대로 둔다.
    #    `_undetermined()` 는 쓰지 않는다 — 그 헬퍼는 "candidate_verdict 가 PASS/FAIL 인데
    #    구조적으로는 UNDETERMINED 여야 하는 경로에 도달했다 = 세탁 시도"를 잡는 방어선이라,
    #    여기서 그대로 쓰면 이 **의도된** 하향까지 세탁으로 오판해 예외를 던진다. 이 분기는
    #    "진짜 candidate=PASS 를 계산해놓고, cap 때문에 일부러 낮춘다"는 별개의 정당한 경로다.
    if evidence_slot.cap_hit and candidate == VerdictState.PASS:
        return CriterionOutcome(
            criterion_id=criterion_id,
            outcome=VerdictState.UNDETERMINED,
            reason=(
                "cap_hit=True 상태에서 candidate=PASS — 절단된 나머지 항목까지 통과를 보장할 "
                f"수 없어 UNDETERMINED 로 하향한다 (D-R0-53). 근거: {expectation.reason}"
            ),
            evidence_ref=_ref(
                matched_item_count=len(expectation.matched_items),
                matched_items_sample=list(expectation.matched_items[:5]),
                cap_hit=True,
                downgraded_from_candidate="PASS",
            ),
            evaluator_version=EVALUATOR_VERSION,
            needs_semantic=False,
            evidence_automation_grade=AutomationGrade.B_DETERMINISTIC_RULE,
            stage_trace=trace,
        )

    return CriterionOutcome(
        criterion_id=criterion_id,
        outcome=candidate,
        reason=expectation.reason,
        evidence_ref=_ref(
            matched_item_count=len(expectation.matched_items),
            matched_items_sample=list(expectation.matched_items[:5]),
            cap_hit=evidence_slot.cap_hit,
        ),
        evaluator_version=EVALUATOR_VERSION,
        needs_semantic=False,
        evidence_automation_grade=AutomationGrade.B_DETERMINISTIC_RULE,
        stage_trace=trace,
    )


def evaluate_criterion(
    criterion_id: str, probe: dict, *, evidence_ref: dict[str, Any] | None = None
) -> CriterionOutcome:
    """Stage 1 유일한 공개 진입점. 4단계를 순서대로 호출하고 `_finalize` 로 합친다.

    `criterion_id` 가 older-relevant 22 밖(= manifest 의 `applicability == OTHER`
    이거나 아예 모르는 id)이면 `SubsetScopeError` — 이 시점에 시도하는 것 자체가
    `D-R0-13` subset 확대다.
    """
    if criterion_id not in OLDER_RELEVANT_IDS:
        raise SubsetScopeError(
            f"{criterion_id!r} 는 older-relevant subset(22개) 밖이다. Stage 1 evaluator 는 "
            "criterion_manifest.json 의 applicability != 'OTHER' 인 criterion 에만 적용된다 "
            "(D-R0-13 · D-R0-52 경계 확정)."
        )

    grade = CODEBOOK_AUTOMATION_GRADE[criterion_id]
    appl = stage1_evidence.applicability(criterion_id, probe)
    slot = stage1_evidence.required_evidence_slots(criterion_id, probe)

    expectation_fn = EXPECTATION_FUNCS.get(criterion_id)
    if (
        appl.status == ApplicabilityStatus.APPLICABLE
        and grade == "AUTO_DECIDABLE"
        and expectation_fn is not None
    ):
        items = stage1_evidence.get_slot_items(criterion_id, probe)
        expect = expectation_fn(items)
    else:
        expect = ExpectationResult(
            None,
            (),
            "이 경로에서는 Expectation 을 시도하지 않는다 "
            "(applicability/automation_grade/Stage1 구현 여부 조건 미충족)",
        )

    return _finalize(
        criterion_id,
        appl,
        slot,
        expect,
        codebook_grade=grade,
        evidence_ref_base=dict(evidence_ref or {}),
    )


def evaluate_older_relevant_subset(
    probe: dict, *, evidence_ref: dict[str, Any] | None = None
) -> dict[str, CriterionOutcome]:
    """22개 전부를 개별 평가한다. **service-level 복제 금지(D-R0-23)** — 한 결과를 22번
    복제하지 않고, criterion 마다 `evaluate_criterion` 을 독립 호출한다."""
    outcomes = {
        criterion_id: evaluate_criterion(criterion_id, probe, evidence_ref=evidence_ref)
        for criterion_id in sorted(OLDER_RELEVANT_IDS)
    }
    assert len(outcomes) == 22, len(outcomes)
    assert all(cid == outcome.criterion_id for cid, outcome in outcomes.items())
    return outcomes
