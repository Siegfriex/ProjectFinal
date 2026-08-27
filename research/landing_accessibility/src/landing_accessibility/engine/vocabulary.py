"""상태값 어휘 — `A2_VOCABULARY_AND_SCHEMA_BINDING.md §1` 의 코드 표현.

`A2` 규칙 **S-3**: 모든 열거형은 **닫힌 집합**이다. 표에 없는 값이 나오면 파이프라인이
실패해야 하며 `UNKNOWN` 으로 조용히 흡수하지 않는다. 이 모듈이 그 실패를 낸다.

`A2` 규칙 **S-1**: 한 사실은 정확히 한 수준의 한 컬럼에만 기록한다.
그래서 수준별로 열거형을 나눠 두고, `LEVEL_OF` 로 어느 수준의 값인지 되물을 수 있게 한다.

여기 있는 값은 전부 `A2` 원문에서 그대로 옮긴 것이다. **새 값을 만들지 않는다.**
"""

from __future__ import annotations

from enum import StrEnum


class ClosedVocabularyError(ValueError):
    """`A2` 규칙 S-3 위반 — 닫힌 집합 밖의 값."""


# ── Observation 수준 (A2 §1.2) ────────────────────────────────────────────────
class MeasurementStatus(StrEnum):
    MEASURED = "MEASURED"
    FAILED_ACCESS_BLOCKED = "FAILED_ACCESS_BLOCKED"
    FAILED_ROBOTS_OR_TRANSPORT = "FAILED_ROBOTS_OR_TRANSPORT"
    FAILED_BROWSER_CRASH = "FAILED_BROWSER_CRASH"
    FAILED_PAGE_TIMEOUT = "FAILED_PAGE_TIMEOUT"
    FAILED_EVIDENCE_INCOMPLETE = "FAILED_EVIDENCE_INCOMPLETE"
    NOT_ELIGIBLE_AT_COLLECTION = "NOT_ELIGIBLE_AT_COLLECTION"


class MeasurementStatusDetail(StrEnum):
    APP_ONLY_AT_COLLECTION = "APP_ONLY_AT_COLLECTION"
    NO_PUBLIC_WEB_LANDING_AT_COLLECTION = "NO_PUBLIC_WEB_LANDING_AT_COLLECTION"


def is_measurement_failed(status: MeasurementStatus) -> bool:
    """`A2 §1.2` 계열 술어 — `LIKE 'FAILED_%'`.

    `NOT_ELIGIBLE_AT_COLLECTION` 은 **의도적으로 이 패턴에 걸리지 않는다** (규칙 N-6).
    """
    return status.value.startswith("FAILED_")


# ── Task 수준 (A2 §1.5) ──────────────────────────────────────────────────────
class EndpointStatus(StrEnum):
    """`02 §7` 이 열거한 7값. **확장하지 않는다** (규칙 E-1)."""

    FUNCTION_ENDPOINT_REACHED = "FUNCTION_ENDPOINT_REACHED"
    AUTH_GATE_REACHED = "AUTH_GATE_REACHED"
    PAYMENT_GATE_REACHED = "PAYMENT_GATE_REACHED"
    PERSONAL_DATA_REQUIRED = "PERSONAL_DATA_REQUIRED"
    CAPTCHA = "CAPTCHA"
    BLOCKED = "BLOCKED"
    UNRESOLVED = "UNRESOLVED"


class EndpointStatusDetail(StrEnum):
    """`A2 §1.5.2` 하위 세분 4값. 상위 7값 집합을 확장하지 않기 위한 동반 컬럼."""

    UNRESOLVED_DEPTH_BUDGET_EXCEEDED = "UNRESOLVED_DEPTH_BUDGET_EXCEEDED"
    UNRESOLVED_REPLAY_BROKEN = "UNRESOLVED_REPLAY_BROKEN"
    UNRESOLVED_NO_SIGNAL = "UNRESOLVED_NO_SIGNAL"
    ENDPOINT_VIA_AUTH_GATE = "ENDPOINT_VIA_AUTH_GATE"


#: `A2 §1.5.2` roll-up 규칙 — 각 세분값은 상위 값 **하나만** 갖는다.
DETAIL_ROLLUP: dict[EndpointStatusDetail, EndpointStatus] = {
    EndpointStatusDetail.UNRESOLVED_DEPTH_BUDGET_EXCEEDED: EndpointStatus.UNRESOLVED,
    EndpointStatusDetail.UNRESOLVED_REPLAY_BROKEN: EndpointStatus.UNRESOLVED,
    EndpointStatusDetail.UNRESOLVED_NO_SIGNAL: EndpointStatus.UNRESOLVED,
    EndpointStatusDetail.ENDPOINT_VIA_AUTH_GATE: EndpointStatus.FUNCTION_ENDPOINT_REACHED,
}


class AreaSignalStatus(StrEnum):
    OBSERVED = "OBSERVED"
    INFERRED_FROM_ENDPOINT = "INFERRED_FROM_ENDPOINT"
    NOT_OBSERVED = "NOT_OBSERVED"


class DepthSegment(StrEnum):
    NED = "NED"
    IED = "IED"
    UNASSIGNED = "UNASSIGNED"


class InteractionArchetype(StrEnum):
    """`00 §6` archetype 7종 (`A1 §1.2` 신호표의 행)."""

    QUERY = "QUERY"
    CONTENT_OPEN = "CONTENT_OPEN"
    ITEM_DETAIL = "ITEM_DETAIL"
    PLACE_LOOKUP = "PLACE_LOOKUP"
    COMMUNICATION_ENTRY = "COMMUNICATION_ENTRY"
    FINANCIAL_ACTION_ENTRY = "FINANCIAL_ACTION_ENTRY"
    UTILITY_ENTRY = "UTILITY_ENTRY"


class GateKind(StrEnum):
    """관측된 gate 의 종류.

    `A2 §1.5.1a` 규칙 E-6a 가 **archetype 별로 gate 종류를 달리** 취급하므로
    (금융 = 로그인/인증, 커뮤니티 = 로그인만) 종류를 분리해 관측한다.
    종류의 판별기준 자체는 P-A endpoint codebook 이 동결한다 — 수집기의 재량이 아니다.
    """

    LOGIN = "LOGIN"
    IDENTITY_VERIFICATION = "IDENTITY_VERIFICATION"
    PAYMENT = "PAYMENT"
    CAPTCHA = "CAPTCHA"
    PERSONAL_DATA = "PERSONAL_DATA"


class RegionSignalType(StrEnum):
    """`A2 §1.9` — `endpoint_signal_type` 과 **같은 열거형을 공유**한다."""

    DOM_AX_ROLE = "DOM_AX_ROLE"
    FORM_STRUCTURE = "FORM_STRUCTURE"
    URL_PATTERN = "URL_PATTERN"
    MEDIA_STATE = "MEDIA_STATE"
    GATE_SIGNAL = "GATE_SIGNAL"
    CODEBOOK_PENDING = "CODEBOOK_PENDING"


# ── Interrupt 수준 (A2 §1.6) ─────────────────────────────────────────────────
class ClassificationStatus(StrEnum):
    NOT_CLASSIFIED = "NOT_CLASSIFIED"
    DETERMINISTIC = "DETERMINISTIC"
    SEMANTIC_MODEL = "SEMANTIC_MODEL"
    VLM_REVIEWED = "VLM_REVIEWED"
    AMBIGUOUS = "AMBIGUOUS"


class InterruptLabel(StrEnum):
    """`00 §8` 이 열거한 10종. 새 라벨을 추가하지 않는다 (`02 §10`)."""

    BLOCKING_MODAL = "BLOCKING_MODAL"
    PROMOTION_MODAL = "PROMOTION_MODAL"
    COOKIE_CONSENT = "COOKIE_CONSENT"
    ADVERTISEMENT = "ADVERTISEMENT"
    APP_INSTALL_PROMPT = "APP_INSTALL_PROMPT"
    LOGIN_PROMPT = "LOGIN_PROMPT"
    CHAT_WIDGET = "CHAT_WIDGET"
    BANNER = "BANNER"
    TOAST = "TOAST"
    UNKNOWN = "UNKNOWN"


class DismissMethod(StrEnum):
    CONTROL_CLICK = "CONTROL_CLICK"
    DIALOG_CLOSE = "DIALOG_CLOSE"
    ESCAPE_KEY = "ESCAPE_KEY"
    BACKDROP_CLICK = "BACKDROP_CLICK"
    NONE = "NONE"


class DismissFailureMode(StrEnum):
    NO_CONTROL = "NO_CONTROL"
    NOT_HITTABLE = "NOT_HITTABLE"
    NO_STATE_CHANGE = "NO_STATE_CHANGE"
    NEW_INTERRUPT_APPEARED = "NEW_INTERRUPT_APPEARED"
    NAVIGATED_AWAY = "NAVIGATED_AWAY"


#: `A2 §1.6` — 이름이 비어 있음이 **관측된** 경우의 센티널.
#: `NULL`(잴 대상이 없었음)과 섞지 않는다 (규칙 N-4 의 유일한 예외).
NAME_ABSENT = "NAME_ABSENT"


# ── Criterion 수준 (A2 §1.7) ─────────────────────────────────────────────────
class VerdictState(StrEnum):
    PASS = "PASS"
    FAIL = "FAIL"
    UNDETERMINED = "UNDETERMINED"
    NA = "NA"


# ── Adjudication 수준 (A2 §1.8 · §1.10) ──────────────────────────────────────
class AdjudicationStatus(StrEnum):
    RESOLVED = "RESOLVED"
    ABSTAIN = "ABSTAIN"
    ESCALATED_HUMAN_FINAL = "ESCALATED_HUMAN_FINAL"
    PENDING = "PENDING"


class ReviewTaskType(StrEnum):
    CRITERION_VERDICT = "CRITERION_VERDICT"
    CRITERION_UNDETERMINED_TRIAGE = "CRITERION_UNDETERMINED_TRIAGE"
    INTERRUPT_LABEL = "INTERRUPT_LABEL"
    TASK_MAPPING = "TASK_MAPPING"
    PRIMARY_ACTION_SELECTION = "PRIMARY_ACTION_SELECTION"


class TriageLabel(StrEnum):
    """`A2 §1.8` — `CRITERION_UNDETERMINED_TRIAGE` 의 허용 label 도메인.

    규칙 A-2: 이 item 의 어떤 label 컬럼에도 `PASS`/`FAIL` 을 쓰지 않는다.
    """

    EVIDENCE_INSUFFICIENT_CONFIRMED = "EVIDENCE_INSUFFICIENT_CONFIRMED"
    RECOLLECT_RECOMMENDED = "RECOLLECT_RECOMMENDED"


class ImpactLevel(StrEnum):
    """`A2 §1.8` — **evidence 결손의 성격과 복구 가능성**. 결론 중립적으로 정의된다."""

    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class AIReviewStatus(StrEnum):
    NOT_REQUIRED = "NOT_REQUIRED"
    QUEUED = "QUEUED"
    COMPLETED_AGREED = "COMPLETED_AGREED"
    COMPLETED_ARBITRATED = "COMPLETED_ARBITRATED"
    ABSTAINED = "ABSTAINED"
    ESCALATED_HUMAN_FINAL = "ESCALATED_HUMAN_FINAL"
    ESCALATION_DECLINED_BUDGET = "ESCALATION_DECLINED_BUDGET"


class AutomationGrade(StrEnum):
    """`A2 §3.1` — `02 §1` 수집 우선순위 6단계와 같은 사다리."""

    A_BROWSER_NATIVE = "A_BROWSER_NATIVE"
    B_DETERMINISTIC_RULE = "B_DETERMINISTIC_RULE"
    C_CV_GEOMETRY = "C_CV_GEOMETRY"
    D_EMBEDDING_TEXT = "D_EMBEDDING_TEXT"
    E_VLM = "E_VLM"
    F_HUMAN_FINAL = "F_HUMAN_FINAL"
    UNGRADED = "UNGRADED"


#: `A2 §3.3` 제약 G-2 — 이 세 등급은 반드시 `ai_review_required = 1`.
GRADES_REQUIRING_AI_REVIEW: frozenset[AutomationGrade] = frozenset(
    {AutomationGrade.D_EMBEDDING_TEXT, AutomationGrade.E_VLM, AutomationGrade.F_HUMAN_FINAL}
)


# ── Episode 수준 (A2 §1.12) ──────────────────────────────────────────────────
class EpisodeKind(StrEnum):
    TEXT_INPUT = "TEXT_INPUT"
    SCROLL = "SCROLL"


class EpisodeEndedBy(StrEnum):
    BLUR = "BLUR"
    SUBMIT = "SUBMIT"
    FOCUS_MOVED = "FOCUS_MOVED"
    IDLE = "IDLE"
    DIRECTION_REVERSAL = "DIRECTION_REVERSAL"
    CONTAINER_CHANGE = "CONTAINER_CHANGE"
    ACTIVATION = "ACTIVATION"
    STATE_CHANGE = "STATE_CHANGE"
    SCOUT_END = "SCOUT_END"


#: `A2 §1.12` — `ended_by` 값이 어느 `episode_kind` 에 붙을 수 있는가.
ENDED_BY_APPLICABILITY: dict[EpisodeEndedBy, frozenset[EpisodeKind]] = {
    EpisodeEndedBy.BLUR: frozenset({EpisodeKind.TEXT_INPUT}),
    EpisodeEndedBy.SUBMIT: frozenset({EpisodeKind.TEXT_INPUT}),
    EpisodeEndedBy.FOCUS_MOVED: frozenset({EpisodeKind.TEXT_INPUT}),
    EpisodeEndedBy.IDLE: frozenset({EpisodeKind.SCROLL}),
    EpisodeEndedBy.DIRECTION_REVERSAL: frozenset({EpisodeKind.SCROLL}),
    EpisodeEndedBy.CONTAINER_CHANGE: frozenset({EpisodeKind.SCROLL}),
    EpisodeEndedBy.ACTIVATION: frozenset({EpisodeKind.TEXT_INPUT, EpisodeKind.SCROLL}),
    EpisodeEndedBy.STATE_CHANGE: frozenset({EpisodeKind.TEXT_INPUT, EpisodeKind.SCROLL}),
    EpisodeEndedBy.SCOUT_END: frozenset({EpisodeKind.TEXT_INPUT, EpisodeKind.SCROLL}),
}


class InputMode(StrEnum):
    HUMAN_SIMULATED = "HUMAN_SIMULATED"
    PROGRAMMATIC = "PROGRAMMATIC"


# ── Candidate 수준 (A2 §1.13) ────────────────────────────────────────────────
class SelectionBasis(StrEnum):
    DETERMINISTIC_RULE = "DETERMINISTIC_RULE"
    EMBEDDING_RANK = "EMBEDDING_RANK"
    AI_REVIEW = "AI_REVIEW"
    HUMAN_FINAL = "HUMAN_FINAL"


class SelectionStatus(StrEnum):
    SELECTED = "SELECTED"
    RUNNER_UP = "RUNNER_UP"
    REJECTED = "REJECTED"


#: `A2 §1.13` — `selection_basis` ↔ `automation_grade` 대응 (§3 규칙 G-1 과 정합).
SELECTION_BASIS_GRADE: dict[SelectionBasis, AutomationGrade] = {
    SelectionBasis.DETERMINISTIC_RULE: AutomationGrade.B_DETERMINISTIC_RULE,
    SelectionBasis.EMBEDDING_RANK: AutomationGrade.D_EMBEDDING_TEXT,
    SelectionBasis.AI_REVIEW: AutomationGrade.E_VLM,
    SelectionBasis.HUMAN_FINAL: AutomationGrade.F_HUMAN_FINAL,
}


# ── 수준 대응표 (A2 §1.0) ────────────────────────────────────────────────────
LEVEL_OF: dict[str, str] = {
    "measurement_status": "Observation",
    "measurement_status_detail": "Observation",
    "endpoint_status": "Task",
    "endpoint_status_detail": "Task",
    "area_signal_status": "Task",
    "depth_segment": "Task",
    "classification_status": "Interrupt",
    "final_label": "Interrupt",
    "dismiss_method": "Interrupt",
    "dismiss_failure_mode": "Interrupt",
    "verdict_state": "Criterion",
    "final_status": "Criterion",
    "automation_grade": "Criterion",
    "adjudication_final_status": "Adjudication",
    "human_required": "Adjudication",
    "ai_review_status": "Adjudication",
    "episode_kind": "Episode",
    "ended_by": "Episode",
    "input_mode": "Episode",
    "selection_basis": "Candidate",
    "selection_status": "Candidate",
}

_ENUMS: dict[str, type[StrEnum]] = {
    "measurement_status": MeasurementStatus,
    "measurement_status_detail": MeasurementStatusDetail,
    "endpoint_status": EndpointStatus,
    "endpoint_status_detail": EndpointStatusDetail,
    "area_signal_status": AreaSignalStatus,
    "depth_segment": DepthSegment,
    "archetype": InteractionArchetype,
    "gate_kind": GateKind,
    "region_signal_type": RegionSignalType,
    "classification_status": ClassificationStatus,
    "final_label": InterruptLabel,
    "dismiss_method": DismissMethod,
    "dismiss_failure_mode": DismissFailureMode,
    "verdict_state": VerdictState,
    "final_status": VerdictState,
    "adjudication_final_status": AdjudicationStatus,
    "review_task_type": ReviewTaskType,
    "triage_label": TriageLabel,
    "impact_level": ImpactLevel,
    "ai_review_status": AIReviewStatus,
    "automation_grade": AutomationGrade,
    "episode_kind": EpisodeKind,
    "ended_by": EpisodeEndedBy,
    "input_mode": InputMode,
    "selection_basis": SelectionBasis,
    "selection_status": SelectionStatus,
}


def enum_for(column: str) -> type[StrEnum]:
    """컬럼 이름에 대응하는 닫힌 집합을 돌려준다."""
    try:
        return _ENUMS[column]
    except KeyError as exc:
        raise ClosedVocabularyError(f"알 수 없는 컬럼: {column!r}") from exc


def validate(column: str, value: object, *, allow_null: bool = False) -> StrEnum | None:
    """`A2` 규칙 S-3 집행기.

    표에 없는 값이면 `ClosedVocabularyError`. `UNKNOWN` 으로 흡수하지 않는다.
    `allow_null=True` 인 컬럼에서만 `None` 이 통과한다 — `NULL` 은 상태값이 아니라
    수치·동반 컬럼의 결측 표현이기 때문이다 (규칙 N-1).
    """
    if value is None:
        if allow_null:
            return None
        raise ClosedVocabularyError(
            f"{column} 은 NULL 을 허용하지 않는다 (A2 규칙 N-1 — 상태 컬럼을 비워두지 않는다)"
        )
    enum_cls = enum_for(column)
    if isinstance(value, enum_cls):
        return value
    try:
        return enum_cls(str(value))
    except ValueError as exc:
        allowed = sorted(m.value for m in enum_cls)
        raise ClosedVocabularyError(
            f"{column} 의 허용값은 {allowed} 다. 받은 값: {value!r} "
            "(A2 규칙 S-3 — 표에 없는 값이 나오면 파이프라인이 실패해야 한다)"
        ) from exc
