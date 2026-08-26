"""AI Review 골격 — deterministic -> semantic -> Reviewer A -> Reviewer B ->
Arbiter -> HUMAN_FINAL(<=5) -> UNDETERMINED/ABSTAIN (SSOT 00 §9).

이 fixture 레인은 실제 VLM/embedding 을 호출하지 않는다 — 각 단계는
pluggable callable 이고, 테스트는 결정론적 스텁 분류기를 주입해 **배선**을
검증한다(실제 판정 정확도는 이 레인의 범위 밖).

강제하는 불변식:
    - HUMAN_FINAL 큐는 ``HUMAN_FINAL_REVIEW_MAX`` 를 절대 넘지 않는다.
      예산 소진 후에는 강제분류하지 않고 UNDETERMINED/ABSTAIN 으로 떨어진다.
    - Reviewer A/B 가 불일치하면 반드시 Arbiter 를 거친다 — 둘 중 하나를
      임의로 채택하지 않는다.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field

Label = str
Classifier = Callable[[dict], "Label | None"]  # None = 이 단계에서 abstain

HUMAN_FINAL_REVIEW_MAX = 5


@dataclass
class CascadeResult:
    item_id: str
    stage_reached: str
    label: Label | None
    disagreement: bool = False
    reviewer_a_label: Label | None = None
    reviewer_b_label: Label | None = None
    arbiter_label: Label | None = None
    trace: list[str] = field(default_factory=list)


@dataclass
class ReviewCascade:
    deterministic: Classifier
    semantic: Classifier
    reviewer_a: Classifier
    reviewer_b: Classifier
    arbiter: Callable[[dict, Label, Label], Label | None]
    human_final_budget: int = HUMAN_FINAL_REVIEW_MAX
    _human_final_used: int = field(default=0, init=False)
    _human_final_queue: list[str] = field(default_factory=list, init=False)

    def review(self, item_id: str, evidence: dict) -> CascadeResult:
        trace: list[str] = []

        label = self.deterministic(evidence)
        trace.append(f"deterministic={label}")
        if label is not None:
            return CascadeResult(item_id, "deterministic", label, trace=trace)

        label = self.semantic(evidence)
        trace.append(f"semantic={label}")
        if label is not None:
            return CascadeResult(item_id, "semantic", label, trace=trace)

        a = self.reviewer_a(evidence)
        b = self.reviewer_b(evidence)
        trace.append(f"reviewer_a={a} reviewer_b={b}")
        if a is not None and a == b:
            return CascadeResult(
                item_id,
                "reviewer_agreement",
                a,
                reviewer_a_label=a,
                reviewer_b_label=b,
                trace=trace,
            )

        arb: Label | None = None
        if a is not None and b is not None and a != b:
            arb = self.arbiter(evidence, a, b)
            trace.append(f"arbiter={arb}")
            if arb is not None:
                return CascadeResult(
                    item_id,
                    "arbiter",
                    arb,
                    disagreement=True,
                    reviewer_a_label=a,
                    reviewer_b_label=b,
                    arbiter_label=arb,
                    trace=trace,
                )

        # arbiter 도 확신 못하거나 리뷰어 자체가 abstain -> HUMAN_FINAL 큐,
        # 예산 초과 시 강제분류하지 않고 UNDETERMINED.
        if self._human_final_used < self.human_final_budget:
            self._human_final_used += 1
            self._human_final_queue.append(item_id)
            trace.append("routed_to_HUMAN_FINAL")
            return CascadeResult(
                item_id,
                "HUMAN_FINAL_QUEUED",
                None,
                disagreement=(a != b),
                reviewer_a_label=a,
                reviewer_b_label=b,
                trace=trace,
            )

        trace.append("HUMAN_FINAL_budget_exhausted -> UNDETERMINED/ABSTAIN")
        return CascadeResult(
            item_id,
            "UNDETERMINED",
            "UNDETERMINED",
            disagreement=(a != b),
            reviewer_a_label=a,
            reviewer_b_label=b,
            trace=trace,
        )

    @property
    def human_final_queue(self) -> list[str]:
        return list(self._human_final_queue)

    @property
    def human_final_used(self) -> int:
        return self._human_final_used
