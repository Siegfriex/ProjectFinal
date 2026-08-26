"""AI review cascade — 인터페이스와 전이 규칙만. **모델을 호출하지 않는다.**

`00 §9` / `02 §10` / `A1 §1.6` / `A2 §1.8` · `§1.10` · `§1.11` · `§4.6`.

## 왜 skeleton 인가

이 lane 의 목적은 "모델이 얼마나 잘 맞히는가" 가 아니라 **cascade 의 전이 규칙이 코드로
강제되는가** 다. 모델을 붙이지 않아도 다음은 전부 검증된다.

- `verdict_state = UNDETERMINED` 행에서 reviewer·arbiter 가 무엇을 내든 결과가 바뀌지 않는가 (T-8)
- triage item 의 label 에 `PASS`/`FAIL` 이 들어가는가 (규칙 A-2)
- 사람 최종검토가 5건을 넘는가 (`HUMAN_FINAL_REVIEW_MAX`)
- 예산 소진 시 `ABSTAIN` 대신 `RESOLVED` 가 기록되는가 (규칙 A-1 · X-6)

`02 §10`: AI 에게는 원본 사이트를 무제한 탐색시키지 않는다. **항상 evidence package 만**
전달하고 출력은 JSON classification only 다. `EvidencePackage` 가 그 경계다.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol

from .transitions import (
    TransitionError,
    TransitionInput,
    assert_triage_label_domain,
    resolve_final_status,
)
from .vocabulary import (
    AdjudicationStatus,
    AIReviewStatus,
    AutomationGrade,
    ImpactLevel,
    ReviewTaskType,
    TriageLabel,
    VerdictState,
)

#: `00 §9` · `EXECUTION_AUTHORITY §1`.
HUMAN_FINAL_REVIEW_MAX = 5


class HumanBudgetExceeded(Exception):
    """`HUMAN_FINAL_REVIEW_MAX = 5` 초과 시도 (제약 G-4)."""


@dataclass(frozen=True)
class EvidencePackage:
    """`02 §10` — AI 에게 전달되는 유일한 입력.

    원본 사이트 접근 경로를 담지 않는다. 그것이 이 dataclass 의 존재 이유다.
    """

    package_id: str
    observation_id: str
    screenshot_crop_relpath: str | None
    surrounding_screenshot_relpath: str | None
    dom_facts: dict[str, Any]
    ax_facts: dict[str, Any]
    bbox: dict[str, float] | None
    relevant_text: str | None
    allowed_labels: tuple[str, ...]
    rule_excerpt: str | None = None

    def assert_no_live_target(self) -> None:
        """package 안에 실제 서비스로 나가는 경로가 섞이지 않았는지 확인한다."""
        blob = repr(self.dom_facts) + repr(self.ax_facts) + (self.relevant_text or "")
        for scheme in ("http://", "https://", "ws://"):
            if scheme in blob:
                raise TransitionError(
                    f"evidence package 에 네트워크 URL 이 들어 있다 ({scheme}) — "
                    "02 §10 은 evidence package 만 전달하라고 요구한다"
                )


@dataclass(frozen=True)
class ReviewerOutput:
    """Reviewer A / Reviewer B 의 출력 스키마. **JSON classification only.**"""

    reviewer_id: str
    label: str | None
    confidence: float | None
    abstain: bool
    evidence_gap: int
    rationale: str

    def validate(self, allowed_labels: tuple[str, ...]) -> None:
        if self.abstain:
            if self.label is not None:
                raise TransitionError("abstain 인데 label 을 냈다 — 억지 분류를 허용하지 않는다")
            return
        if self.label is None:
            raise TransitionError("abstain 이 아닌데 label 이 없다")
        if self.label not in allowed_labels:
            raise TransitionError(
                f"허용 label 목록 밖의 값: {self.label!r} — "
                f"자유로운 새 기준 생성 금지 (02 §10). 허용: {list(allowed_labels)}"
            )


@dataclass(frozen=True)
class ArbiterOutput:
    """A·B 불일치 시 중재자의 출력."""

    arbiter_id: str
    label: str | None
    abstain: bool
    rationale: str
    escalate_to_human: bool = False


class Reviewer(Protocol):
    """모델을 감싸는 자리. 이 lane 은 결정적 stub 만 넣는다."""

    def review(self, package: EvidencePackage) -> ReviewerOutput: ...


class Arbiter(Protocol):
    def arbitrate(
        self, package: EvidencePackage, a: ReviewerOutput, b: ReviewerOutput
    ) -> ArbiterOutput: ...


@dataclass
class DeterministicDecision:
    """cascade 1단계 — `02 §1` 우선순위의 맨 위. 여기서 끝나면 상위 단계를 부르지 않는다."""

    decided: bool
    label: str | None
    automation_grade: AutomationGrade
    rule_id: str | None = None


class DeterministicDecider(Protocol):
    def decide(self, package: EvidencePackage) -> DeterministicDecision: ...


class SemanticDecider(Protocol):
    """cascade 2단계 — text/embedding classifier."""

    def decide(self, package: EvidencePackage) -> DeterministicDecision: ...


@dataclass
class AdjudicationRecord:
    """`fact_ai_adjudication` 한 행 (`A2 §1.8`)."""

    review_item_id: str
    review_task_type: str
    final_status: str
    human_required: int
    ai_review_status: str
    deterministic_label: str | None = None
    semantic_model_label: str | None = None
    reviewer_a_label: str | None = None
    reviewer_b_label: str | None = None
    arbiter_label: str | None = None
    reviewer_agreement: int | str = "NA"
    evidence_gap: int = 0
    impact_level: str | None = None
    review_priority: int | None = None
    automation_grade: str = AutomationGrade.UNGRADED.value
    notes: list[str] = field(default_factory=list)


class HumanFinalQueue:
    """`HUMAN_FINAL_REVIEW_MAX = 5` 를 코드로 강제한다.

    예산이 소진되면 `ESCALATION_DECLINED_BUDGET` + `ABSTAIN` 이며,
    **`RESOLVED` 로 내리지 않는다** (규칙 A-1 · 금지 전이 X-6).
    `fact_ai_adjudication.human_required` 와 `dim_representative_task.human_final_required` 가
    **같은 예산**을 공유하므로 큐는 하나다 (`A2 §1.9`).
    """

    def __init__(self, maximum: int = HUMAN_FINAL_REVIEW_MAX) -> None:
        self.maximum = maximum
        self._items: list[str] = []

    @property
    def used(self) -> int:
        return len(self._items)

    @property
    def remaining(self) -> int:
        return self.maximum - self.used

    def try_escalate(self, review_item_id: str) -> bool:
        if review_item_id in self._items:
            return True
        if self.remaining <= 0:
            return False
        self._items.append(review_item_id)
        return True

    def assert_within_budget(self) -> None:
        if self.used > self.maximum:
            raise HumanBudgetExceeded(
                f"G-4: human_required = 1 인 distinct review_item_id 는 {self.maximum} 이하여야 "
                f"한다. 현재 {self.used}"
            )


@dataclass
class CascadeResult:
    adjudication: AdjudicationRecord
    criterion_final_status: str
    applied_rule: str


class ReviewCascade:
    """`00 §9` 6단계 cascade. 1단계에서 확정되면 상위 단계를 호출하지 않는다 (`A1 §1.6`)."""

    def __init__(
        self,
        *,
        deterministic: DeterministicDecider | None = None,
        semantic: SemanticDecider | None = None,
        reviewer_a: Reviewer | None = None,
        reviewer_b: Reviewer | None = None,
        arbiter: Arbiter | None = None,
        human_queue: HumanFinalQueue | None = None,
    ) -> None:
        self.deterministic = deterministic
        self.semantic = semantic
        self.reviewer_a = reviewer_a
        self.reviewer_b = reviewer_b
        self.arbiter = arbiter
        self.human_queue = human_queue or HumanFinalQueue()

    def run(
        self,
        *,
        review_item_id: str,
        review_task_type: ReviewTaskType,
        verdict_state: VerdictState,
        package: EvidencePackage,
        ai_review_required: int = 1,
    ) -> CascadeResult:
        package.assert_no_live_target()

        record = AdjudicationRecord(
            review_item_id=review_item_id,
            review_task_type=review_task_type.value,
            final_status=AdjudicationStatus.PENDING.value,
            human_required=0,
            ai_review_status=AIReviewStatus.QUEUED.value,
        )

        # `verdict_state = UNDETERMINED` 행의 검토는 **triage** 다 (§1.7 두 번째 행).
        # 그 결과는 판정이 아니라 재수집 대기열의 정렬 정보다.
        is_triage = review_task_type is ReviewTaskType.CRITERION_UNDETERMINED_TRIAGE
        if verdict_state is VerdictState.UNDETERMINED and not is_triage:
            raise TransitionError(
                "verdict_state = UNDETERMINED 인 행은 CRITERION_UNDETERMINED_TRIAGE 로만 "
                "검토한다 (A2 §1.8 review_task_type 표)"
            )

        status, label, grade = self._cascade(package, record, is_triage)
        record.final_status = status.value
        record.human_required = int(status is AdjudicationStatus.ESCALATED_HUMAN_FINAL)
        record.automation_grade = grade.value
        if is_triage:
            record.impact_level = record.impact_level or ImpactLevel.MEDIUM.value
            assert_triage_label_domain(
                review_task_type,
                {
                    "deterministic_label": record.deterministic_label,
                    "semantic_model_label": record.semantic_model_label,
                    "reviewer_a_label": record.reviewer_a_label,
                    "reviewer_b_label": record.reviewer_b_label,
                    "arbiter_label": record.arbiter_label,
                },
            )

        confirmed: VerdictState | None = None
        if not is_triage and label in (VerdictState.PASS.value, VerdictState.FAIL.value):
            confirmed = VerdictState(label)

        final_status, rule = resolve_final_status(
            TransitionInput(
                verdict_state=verdict_state,
                ai_review_required=ai_review_required,
                adjudication_status=status,
                confirmed_label=confirmed,
                review_task_type=review_task_type,
            )
        )
        return CascadeResult(
            adjudication=record, criterion_final_status=final_status.value, applied_rule=rule
        )

    # ── cascade 본체 ─────────────────────────────────────────────────────
    def _cascade(
        self, package: EvidencePackage, record: AdjudicationRecord, is_triage: bool
    ) -> tuple[AdjudicationStatus, str | None, AutomationGrade]:
        if self.deterministic is not None:
            d = self.deterministic.decide(package)
            record.deterministic_label = d.label
            if d.decided:
                record.ai_review_status = AIReviewStatus.NOT_REQUIRED.value
                return AdjudicationStatus.RESOLVED, d.label, d.automation_grade

        if self.semantic is not None:
            s = self.semantic.decide(package)
            record.semantic_model_label = s.label
            if s.decided:
                record.ai_review_status = AIReviewStatus.COMPLETED_AGREED.value
                return AdjudicationStatus.RESOLVED, s.label, AutomationGrade.D_EMBEDDING_TEXT

        if self.reviewer_a is None or self.reviewer_b is None:
            record.ai_review_status = AIReviewStatus.ABSTAINED.value
            return AdjudicationStatus.ABSTAIN, None, AutomationGrade.UNGRADED

        a = self.reviewer_a.review(package)
        a.validate(package.allowed_labels)
        b = self.reviewer_b.review(package)
        b.validate(package.allowed_labels)
        record.reviewer_a_label = a.label
        record.reviewer_b_label = b.label
        record.evidence_gap = int(bool(a.evidence_gap or b.evidence_gap))

        if a.abstain or b.abstain or a.label is None or b.label is None:
            # `reviewer_agreement` — 한쪽이라도 ABSTAIN 이면 `NA` 다. 0 으로 세지 않는다 (§4.4).
            record.reviewer_agreement = "NA"
        else:
            record.reviewer_agreement = int(a.label == b.label)

        if record.reviewer_agreement == 1:
            record.ai_review_status = AIReviewStatus.COMPLETED_AGREED.value
            return AdjudicationStatus.RESOLVED, a.label, AutomationGrade.E_VLM

        if self.arbiter is None:
            record.ai_review_status = AIReviewStatus.ABSTAINED.value
            return AdjudicationStatus.ABSTAIN, None, AutomationGrade.UNGRADED

        arb = self.arbiter.arbitrate(package, a, b)
        record.arbiter_label = arb.label
        if arb.escalate_to_human:
            if self.human_queue.try_escalate(record.review_item_id):
                record.ai_review_status = AIReviewStatus.ESCALATED_HUMAN_FINAL.value
                return AdjudicationStatus.ESCALATED_HUMAN_FINAL, None, AutomationGrade.UNGRADED
            # 규칙 A-1 — 예산 부족을 이유로 RESOLVED 로 내리지 않는다 (X-6).
            record.ai_review_status = AIReviewStatus.ESCALATION_DECLINED_BUDGET.value
            record.notes.append(
                "HUMAN_FINAL_REVIEW_MAX 소진 — 00 §9 는 5건을 초과하는 모호한 사례를 "
                "억지로 분류하지 않는다고 정한다"
            )
            return AdjudicationStatus.ABSTAIN, None, AutomationGrade.UNGRADED
        if arb.abstain or arb.label is None:
            record.ai_review_status = AIReviewStatus.ABSTAINED.value
            return AdjudicationStatus.ABSTAIN, None, AutomationGrade.UNGRADED
        record.ai_review_status = AIReviewStatus.COMPLETED_ARBITRATED.value
        return AdjudicationStatus.RESOLVED, arb.label, AutomationGrade.E_VLM


# ── 결정적 stub — 테스트와 harness 용. 모델을 부르지 않는다. ─────────────────
@dataclass
class StubReviewer:
    reviewer_id: str
    label: str | None
    abstain: bool = False
    evidence_gap: int = 0
    confidence: float | None = 0.9

    def review(self, package: EvidencePackage) -> ReviewerOutput:
        return ReviewerOutput(
            reviewer_id=self.reviewer_id,
            label=self.label,
            confidence=self.confidence,
            abstain=self.abstain,
            evidence_gap=self.evidence_gap,
            rationale="stub",
        )


@dataclass
class StubArbiter:
    arbiter_id: str = "stub-arbiter"
    label: str | None = None
    abstain: bool = True
    escalate_to_human: bool = False

    def arbitrate(
        self, package: EvidencePackage, a: ReviewerOutput, b: ReviewerOutput
    ) -> ArbiterOutput:
        return ArbiterOutput(
            arbiter_id=self.arbiter_id,
            label=self.label,
            abstain=self.abstain,
            rationale="stub",
            escalate_to_human=self.escalate_to_human,
        )


TRIAGE_ALLOWED_LABELS: tuple[str, ...] = tuple(t.value for t in TriageLabel)
CRITERION_ALLOWED_LABELS: tuple[str, ...] = (VerdictState.PASS.value, VerdictState.FAIL.value)
