"""P-C AI review cascade(`src/landing_accessibility/engine/ai_review.py`)에 대한
단일 import 지점.

`sys.path` 조작(연구 하위 프로젝트의 `src/` layout, `tests/test_pc_transitions_and_review.py`
가 쓰는 것과 같은 패턴)을 이 파일 하나에 모은다 — `synthetic.py`·`adjudication_binding.py`
양쪽이 각자 경로를 조작하면 드리프트할 수 있다.
"""

from __future__ import annotations

import sys
from pathlib import Path

_ENGINE_SRC = Path(__file__).resolve().parents[2] / "src"
if str(_ENGINE_SRC) not in sys.path:
    sys.path.insert(0, str(_ENGINE_SRC))

from landing_accessibility.engine.ai_review import (  # noqa: E402
    CRITERION_ALLOWED_LABELS,
    HUMAN_FINAL_REVIEW_MAX,
    TRIAGE_ALLOWED_LABELS,
    AdjudicationRecord,
    ArbiterOutput,
    CascadeResult,
    EvidencePackage,
    HumanFinalQueue,
    ReviewCascade,
    ReviewerOutput,
    StubArbiter,
    StubReviewer,
)
from landing_accessibility.engine.vocabulary import (  # noqa: E402
    AdjudicationStatus,
    AutomationGrade,
    ImpactLevel,
    ReviewTaskType,
    TriageLabel,
    VerdictState,
)


def triage_allowed_labels() -> tuple[str, ...]:
    return TRIAGE_ALLOWED_LABELS


def verdict_allowed_labels() -> tuple[str, ...]:
    return CRITERION_ALLOWED_LABELS


__all__ = [
    "HUMAN_FINAL_REVIEW_MAX",
    "AdjudicationRecord",
    "AdjudicationStatus",
    "ArbiterOutput",
    "AutomationGrade",
    "CascadeResult",
    "EvidencePackage",
    "HumanFinalQueue",
    "ImpactLevel",
    "ReviewCascade",
    "ReviewTaskType",
    "ReviewerOutput",
    "StubArbiter",
    "StubReviewer",
    "TriageLabel",
    "VerdictState",
    "triage_allowed_labels",
    "verdict_allowed_labels",
]
