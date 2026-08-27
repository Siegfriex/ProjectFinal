"""Stage 1 evaluator 공용 타입 — `D-R0-21`·`D-R0-22`·`D-R0-23`, `D-R0-51`·`D-R0-52`.

네 단계(Applicability → Required evidence slots → Expectation → Outcome)를 독립
dataclass/함수로 드러낸다. 마지막에 `_finalize`(`stage1_pipeline.py`)만 이 네 결과를
`CriterionOutcome` 하나로 합치고, **그 합치는 지점에서만** 금지 규칙(`D-R0-23`)을
강제한다 — 다른 어떤 코드도 `CriterionOutcome`을 직접 만들 수 없다(frozen dataclass
+ 이 모듈 밖에 생성자 없음).

새 판정값을 만들지 않는다 — `VerdictState`(PASS/FAIL/UNDETERMINED/NA)와
`AutomationGrade`(evidence 수집 등급 사다리)는 전부 `engine/vocabulary.py`에서
그대로 가져온다.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from ..vocabulary import AutomationGrade, VerdictState

#: 이 파일이 바뀌면(로직이든 threshold든) 반드시 올린다. 모든 `CriterionOutcome`이
#: 이 문자열을 그대로 들고 다닌다 — `D-R0-21` "exact evaluator version" 요구사항.
EVALUATOR_VERSION = "kwcag-stage1-evaluator@0.1.0"

#: Stage 1은 물리 evidence slot 중 `probe`만 읽는다(`engine/identity.py`의
#: `EVIDENCE_SLOTS` 7종 중 하나). `dom`/`ax`는 이번 단계에서 읽지 않는다 — A가 지적한
#: "dom.html은 렌더 이전 shell인데 probe는 다른 값을 말할 수 있다"는 사례에 대응해,
#: 어느 slot을 읽고 내린 판정인지 모든 결과에 명시적으로 남긴다.
PHYSICAL_EVIDENCE_SLOT = "probe"


class SubsetScopeError(ValueError):
    """`D-R0-13`·`D-R0-52` — older-relevant 22 밖(`applicability == OTHER`) criterion에
    Stage 1을 적용하려는 시도. 이 시점에 시도하는 것 자체가 subset 확대다."""


class UndeterminedLaunderingError(RuntimeError):
    """`D-R0-23` — 이미 구조적으로 UNDETERMINED가 확정된 경로에서 Expectation이
    PASS/FAIL 후보를 냈다. 논리적으로 있을 수 없어야 하는 상태이므로 조용히 무시하지
    않고 예외를 낸다 — 상위 로직의 버그를 잡기 위한 방어선이다."""


class EvidenceRequiredError(RuntimeError):
    """`D-R0-23` — evidence_ref(매칭된 raw evidence 항목)가 없는데 PASS/FAIL을
    내리려는 시도."""


class MeasurementFailureAsFailError(RuntimeError):
    """`D-R0-23` — evidence slot 결측/공란/cap 모호를 FAIL로 전이하려는 시도."""


class ApplicabilityStatus(StrEnum):
    APPLICABLE = "APPLICABLE"
    NOT_APPLICABLE = "NOT_APPLICABLE"
    UNDETERMINED = "UNDETERMINED"


class EvidenceSlotStatus(StrEnum):
    #: raw_features 에 키가 있고, 항목이 있고, cap 절단 의심이 없다.
    PRESENT = "PRESENT"
    #: raw_features 에 키가 있고 항목이 있으나, 항목 수가 `D-R0-53` cap 값과 같아
    #: 절단됐을 수 있다(길이만으로는 확정 불가 — 휴리스틱, 아래 `stage1_evidence.py`
    #: 문서 참조).
    PRESENT_CAP_AMBIGUOUS = "PRESENT_CAP_AMBIGUOUS"
    #: raw_features 에 키가 있으나 항목이 0개(또는 criterion 필터 이후 0개).
    EMPTY = "EMPTY"
    #: 이 criterion이 필요로 하는 raw_features 키 자체가 현재 L0 probe 스키마에 없다
    #: (수집기가 그 신호를 아예 모으지 않는다 — Stage 1이 "구현을 안 한" 게 아니라
    #: "수집기가 없는" 갭이다).
    ABSENT_FROM_PROBE_SCHEMA = "ABSENT_FROM_PROBE_SCHEMA"


@dataclass(frozen=True, slots=True)
class ApplicabilityResult:
    status: ApplicabilityStatus
    reason: str


@dataclass(frozen=True, slots=True)
class EvidenceSlotResult:
    #: probe.json `raw_features` 아래 실제로 참조한 키 이름들.
    slot_names: tuple[str, ...]
    physical_evidence_slot: str
    status: EvidenceSlotStatus
    cap_hit: bool
    item_count: int | None
    reason: str


@dataclass(frozen=True, slots=True)
class ExpectationResult:
    """공식 기준 조건과의 대조 — **아직 최종 Outcome이 아니다.** `_finalize`가
    automation_grade cap·cap_hit 하향·evidence 유무를 반영해 최종 승격 여부를 정한다.
    """

    #: None = 이 criterion의 공식 조건 검사를 Stage 1에서 아직 구현하지 않음(또는
    #: 존재만으로는 결정할 수 없어 의도적으로 결정을 보류함 — `escalate_semantic` 참조).
    candidate_verdict: VerdictState | None
    matched_items: tuple[dict[str, Any], ...]
    reason: str
    #: `T-A-W3-SCHEMA-001` 요구#3 — `candidate_verdict is None` 인데 그 이유가 "존재는
    #: 확인했지만 적절성/작동은 의미 판단이 필요해 여기서 멈춘다"(`D-R0-70` 존재≠작동)면
    #: True. `_finalize` 가 이 값을 `needs_semantic` 에 그대로 반영한다. 그냥 "Stage 1에
    #: 로직이 없다"(구현 갭)와 구분하기 위한 필드 — 기본값 False(기존 동작 그대로).
    escalate_semantic: bool = False


@dataclass(frozen=True, slots=True)
class CriterionOutcome:
    criterion_id: str
    outcome: VerdictState
    reason: str
    evidence_ref: dict[str, Any]
    evaluator_version: str
    needs_semantic: bool
    evidence_automation_grade: AutomationGrade
    stage_trace: dict[str, Any] = field(default_factory=dict)
