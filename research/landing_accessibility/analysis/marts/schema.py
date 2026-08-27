"""7개 fact/dim mart의 논리 스키마 — `01_DATA_SPEC_v2.0.md` §4~§9 컬럼 목록의 코드 표현.

이 모듈은 `A2_VOCABULARY_AND_SCHEMA_BINDING.md`가 정의한 닫힌 집합(closed
vocabulary) 중 이 7개 표에 실제로 쓰이는 값만 **로컬로 다시 선언**한다. 새 값을
만들지 않는다 — 전부 A2 원문 또는 `landing_accessibility.engine.vocabulary`에서
그대로 옮겼다(각주 참조).

규칙 S-3 (`A2 §1.0`)을 이 스키마 검증기가 집행한다: 닫힌 집합 밖의 값이 들어오면
파이프라인이 실패해야 하며 `UNKNOWN`으로 조용히 흡수하지 않는다.

컬럼 목록의 출처는 표마다 docstring에 절 번호로 남긴다.

**`fact_ai_adjudication` 갱신 (base `claude-b/integration-current`@397a10d로
승격하며 실행).** `claude-b/analysis-skeleton`(base 2025e56) 시점에는 P-C의
`ai_review.py`가 이 워크트리에 없어 `01_DATA_SPEC §9` 컬럼 목록만으로 스키마를
추정했다. 이제 `agent/landing-pc-fixture`가 merge돼 실제
`AdjudicationRecord`(`src/landing_accessibility/engine/ai_review.py`)를 읽을 수
있어, 아래처럼 대조하고 시정했다:

| 컬럼 | `01_DATA_SPEC §9` | 실제 `AdjudicationRecord` | 처리 |
|---|---|---|---|
| `ai_review_status` | 없음 | 있음 | **추가** — cascade가 실제로 채우는 필드이며 `dim_certification`류 진단(`MODEL_DIAGNOSTICS.md`)에 필요하다 |
| `automation_grade` | 없음 | 있음 | **추가** — cascade 6단계 사다리의 실제 도달 등급 |
| `notes` | 없음 | 있음 (`list[str]`) | **추가** — 자유 텍스트라 enum 검증 없이 문자열로 직렬화(`; ` join)해 보존한다. `adjudication_binding.py`가 이 직렬화를 담당한다 |
| `evidence_package_id` | 있음 | **없음** (dataclass 필드가 아니다 — `EvidencePackage.package_id`가 호출자 쪽에만 있다) | **유지, optional로 좁힘** — `01_DATA_SPEC`이 요구하는 조인 키이므로 mart에서는 남기되, `AdjudicationRecord` 자체에는 없으므로 `adjudication_binding.adjudication_record_to_mart_row()`가 별도 인자로 받아 채운다 |

나머지 12개 컬럼(`review_item_id` · `review_task_type` · `deterministic_label` ·
`semantic_model_label` · `reviewer_a_label` · `reviewer_b_label` ·
`reviewer_agreement` · `arbiter_label` · `evidence_gap` · `impact_level` ·
`review_priority` · `final_status` · `human_required`)은 dataclass 필드명·값
도메인이 그대로 일치한다(값 도메인은 `landing_accessibility.engine.vocabulary`의
`StrEnum`들과 이 파일의 닫힌 집합을 1:1 대조해 확인했다).
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from typing import Any

# ── A2 §1 닫힌 집합 (이 7개 표에 쓰이는 것만) ──────────────────────────────────

#: A2 §1.2 — `fact_landing_observation.measurement_status` (7값, `FAILED_%` 계열 포함).
MEASUREMENT_STATUS = (
    "MEASURED",
    "FAILED_ACCESS_BLOCKED",
    "FAILED_ROBOTS_OR_TRANSPORT",
    "FAILED_BROWSER_CRASH",
    "FAILED_PAGE_TIMEOUT",
    "FAILED_EVIDENCE_INCOMPLETE",
    "NOT_ELIGIBLE_AT_COLLECTION",
)

#: A2 §1.5.1 — `endpoint_status` 동결 7값 (규칙 E-1 집합 불확장).
ENDPOINT_STATUS = (
    "FUNCTION_ENDPOINT_REACHED",
    "AUTH_GATE_REACHED",
    "PAYMENT_GATE_REACHED",
    "PERSONAL_DATA_REQUIRED",
    "CAPTCHA",
    "BLOCKED",
    "UNRESOLVED",
)

#: A2 §1.5.2 — `endpoint_status_detail` 하위 세분 4값 (동반 컬럼, 상위 집합을 넓히지 않는다).
ENDPOINT_STATUS_DETAIL = (
    "UNRESOLVED_DEPTH_BUDGET_EXCEEDED",
    "UNRESOLVED_REPLAY_BROKEN",
    "UNRESOLVED_NO_SIGNAL",
    "ENDPOINT_VIA_AUTH_GATE",
)

#: `00 §6` / A1 §1.2 — interaction archetype 7종.
INTERACTION_ARCHETYPE = (
    "QUERY",
    "CONTENT_OPEN",
    "ITEM_DETAIL",
    "PLACE_LOOKUP",
    "COMMUNICATION_ENTRY",
    "FINANCIAL_ACTION_ENTRY",
    "UTILITY_ENTRY",
)

#: A2 §1.6 — interrupt 분류 진행 상태.
CLASSIFICATION_STATUS = (
    "NOT_CLASSIFIED",
    "DETERMINISTIC",
    "SEMANTIC_MODEL",
    "VLM_REVIEWED",
    "AMBIGUOUS",
)

#: `00 §8` / A2 §1.6 — interrupt 라벨 10종 (새 라벨 추가 금지, `02 §10`).
INTERRUPT_LABEL = (
    "BLOCKING_MODAL",
    "PROMOTION_MODAL",
    "COOKIE_CONSENT",
    "ADVERTISEMENT",
    "APP_INSTALL_PROMPT",
    "LOGIN_PROMPT",
    "CHAT_WIDGET",
    "BANNER",
    "TOAST",
    "UNKNOWN",
)

#: A2 §1.7 — criterion 판정 상태 (`verdict_state`·`final_status`가 같은 도메인을 공유한다,
#: A2 §1.0 `_ENUMS` 대응표).
VERDICT_STATE = ("PASS", "FAIL", "UNDETERMINED", "NA")

#: A2 §3.1 — `automation_grade` 6단계 + `UNGRADED`.
AUTOMATION_GRADE = (
    "A_BROWSER_NATIVE",
    "B_DETERMINISTIC_RULE",
    "C_CV_GEOMETRY",
    "D_EMBEDDING_TEXT",
    "E_VLM",
    "F_HUMAN_FINAL",
    "UNGRADED",
)

#: 01_DATA_SPEC §7 — `fact_criterion_result.older_relevance`.
OLDER_RELEVANCE = ("VISION", "MOTOR", "COGNITIVE_NAVIGATION", "OTHER")

#: A2 §1.8 — `fact_ai_adjudication.review_task_type` 5종.
REVIEW_TASK_TYPE = (
    "CRITERION_VERDICT",
    "CRITERION_UNDETERMINED_TRIAGE",
    "INTERRUPT_LABEL",
    "TASK_MAPPING",
    "PRIMARY_ACTION_SELECTION",
)

#: A2 §1.8 — `fact_ai_adjudication.final_status` (`AdjudicationStatus`).
ADJUDICATION_STATUS = ("RESOLVED", "ABSTAIN", "ESCALATED_HUMAN_FINAL", "PENDING")

#: A2 §1.8 — `impact_level` (결론 중립적 3단계).
IMPACT_LEVEL = ("HIGH", "MEDIUM", "LOW")

#: A2 §1.10 — `ai_review_status` 공유 열거형.
AI_REVIEW_STATUS = (
    "NOT_REQUIRED",
    "QUEUED",
    "COMPLETED_AGREED",
    "COMPLETED_ARBITRATED",
    "ABSTAINED",
    "ESCALATED_HUMAN_FINAL",
    "ESCALATION_DECLINED_BUDGET",
)

#: `reviewer_agreement`은 0/1이거나, 한쪽이라도 ABSTAIN이면 `"NA"`다 (A2 §4.4 · ai_review.py L324).
REVIEWER_AGREEMENT = ("0", "1", "NA")

#: 01_DATA_SPEC §8 `dim_certification` — 이 필드들은 A2가 문형으로 정의하지 않았으므로
#: 0/1 정수로 고정한다(§8 "certified_current = 1은 ... 모두 맞아야 한다").
BOOL01 = ("0", "1")

#: `dim_certification.certification_match_status` — Claude A(governor) 확정
#: (LA-TB-1630-20260827). `certified_current`(BOOL01)만으로는 "왜 0인가"가
#: 사라진다 — 만료/애초 미보유(=NOT_CERTIFIED)와 판정 자체가 불가능했던 경우
#: (=UNDETERMINED)를 구분해서 남긴다. 3값 다 `certified_current="1"`을 뜻하지
#: 않는다 — `CERTIFIED`만 `certified_current="1"`과 대응한다.
CERTIFICATION_MATCH_STATUS = ("CERTIFIED", "NOT_CERTIFIED", "UNDETERMINED")

#: `dim_certification.certification_undetermined_reason` — `certification_match_status
#: =UNDETERMINED`일 때만 채운다(그 외는 NULL). 원인을 데이터로 구분하지 못한다는
#: 사실 자체를 감추지 않기 위해 열거형으로 강제한다 — 자유 텍스트로 흐리지 않는다.
CERTIFICATION_UNDETERMINED_REASON = (
    "NO_URL_FOR_REQUIREMENT_2",  # target_scope_match(요건2) 시험에 쓸 URL이 없음
    "IDENTITY_UNRESOLVED_DOMAIN_MATCH_NAME_MISMATCH",  # 도메인은 일치하나 서비스명 불일치로 동일성(요건3) 미해소
)


class SchemaValidationError(ValueError):
    """규칙 S-3 위반 — 닫힌 집합 밖의 값, 또는 필수 컬럼 결측."""


@dataclass(frozen=True)
class Column:
    name: str
    enum: tuple[str, ...] | None = None
    #: True면 값이 NULL/None이어도 통과한다 (A2 규칙 N-1의 컬럼별 예외 — 예: 성공하지 않은
    #: 관측의 depth 계열은 NULL이 정답이다, §1.5.1 "MPFED = NULL").
    nullable: bool = True
    #: 이 컬럼 자체가 행에 없어도(dict에 key 자체가 없어도) 실패시키지 않는다.
    #: mart 스켈레톤 단계에서는 상위 파이프라인이 아직 채우지 않는 컬럼이 있을 수 있어
    #: 기본은 optional로 두고, grain을 규정하는 식별자 컬럼만 required=True로 좁힌다.
    required: bool = False


def _enum_col(name: str, enum: tuple[str, ...], *, nullable: bool = True) -> Column:
    return Column(name=name, enum=enum, nullable=nullable, required=False)


def _id_col(name: str) -> Column:
    return Column(name=name, required=True, nullable=False)


def _plain_col(name: str, *, required: bool = False) -> Column:
    return Column(name=name, required=required)


# ── 7개 표 — 컬럼 목록은 01_DATA_SPEC_v2.0.md 절 번호를 그대로 따른다 ──────────────

#: 01_DATA_SPEC §4.
FACT_LANDING_OBSERVATION: tuple[Column, ...] = (
    _id_col("observation_id"),
    _id_col("web_target_id"),
    _plain_col("audit_date"),
    _plain_col("protocol_version"),
    _plain_col("requested_url"),
    _plain_col("final_url"),
    _plain_col("redirect_count"),
    _enum_col("measurement_status", MEASUREMENT_STATUS, nullable=False),
    _plain_col("viewport_width"),
    _plain_col("viewport_height"),
    _plain_col("screenshot_path"),
    _plain_col("dom_path"),
    _plain_col("ax_path"),
    _plain_col("probe_path"),
    _plain_col("manifest_path"),
    _plain_col("primary_action_visible_initial"),
    _plain_col("interactive_element_count"),
    _plain_col("visible_link_count"),
    _plain_col("visible_button_count"),
    _plain_col("moving_element_count"),
    _plain_col("modal_candidate_count"),
    _plain_col("blocking_modal_count"),
    _plain_col("max_overlay_coverage"),
    _plain_col("max_primary_action_occlusion"),
)

#: 01_DATA_SPEC §6 `fact_task_entry`.
FACT_TASK_ENTRY: tuple[Column, ...] = (
    _id_col("task_observation_id"),
    _id_col("task_id"),
    _id_col("web_target_id"),
    _enum_col("interaction_archetype", INTERACTION_ARCHETYPE, nullable=False),
    _plain_col("endpoint_definition"),
    _enum_col("endpoint_status", ENDPOINT_STATUS, nullable=False),
    _plain_col("NED"),
    _plain_col("IED"),
    _plain_col("MPFED"),
    _plain_col("text_input_episode_count"),
    _plain_col("scroll_episode_count"),
    _plain_col("forced_dismissal_count"),
    _enum_col("auth_gate_before_endpoint", BOOL01, nullable=False),
    _plain_col("redirect_count"),
    _enum_col("endpoint_reached", BOOL01, nullable=False),
    _plain_col("path_manifest_path"),
    # A2 §1.5.1a 층화 요구(규칙 E-10)를 위한 동반 컬럼. 01_DATA_SPEC 원문에는 없으나
    # A2 §6이 명시한 "아직 물리적으로 없는 것"이라 optional로만 얹는다.
    _enum_col("endpoint_status_detail", ENDPOINT_STATUS_DETAIL),
)

#: 01_DATA_SPEC §6 `fact_task_step`.
FACT_TASK_STEP: tuple[Column, ...] = (
    _id_col("task_observation_id"),
    _id_col("step_index"),
    _plain_col("state_before_id"),
    _plain_col("control_selector"),
    _plain_col("control_role"),
    _plain_col("control_accessible_name"),
    _plain_col("control_visual_text"),
    _plain_col("control_bbox"),
    _plain_col("action_type"),
    _plain_col("url_before"),
    _plain_col("url_after"),
    _plain_col("screenshot_before"),
    _plain_col("screenshot_after"),
    _enum_col("modal_encountered", BOOL01),
    _enum_col("auth_gate_detected", BOOL01),
    _enum_col("endpoint_signal_detected", BOOL01),
)

#: 01_DATA_SPEC §5 `fact_interrupt_element`.
FACT_INTERRUPT_ELEMENT: tuple[Column, ...] = (
    _id_col("observation_id"),
    _id_col("interrupt_id"),
    _plain_col("selector"),
    _plain_col("candidate_source"),
    _plain_col("interrupt_type"),
    _plain_col("bbox_x"),
    _plain_col("bbox_y"),
    _plain_col("bbox_w"),
    _plain_col("bbox_h"),
    _plain_col("viewport_intersection_area"),
    _plain_col("overlay_coverage"),
    _plain_col("z_index"),
    _plain_col("position_type"),
    _enum_col("aria_modal", BOOL01),
    _enum_col("role_dialog", BOOL01),
    _enum_col("backdrop_detected", BOOL01),
    _enum_col("body_scroll_lock", BOOL01),
    _enum_col("blocks_primary_action", BOOL01),
    _plain_col("primary_action_occlusion"),
    _enum_col("dismiss_control_exists", BOOL01),
    _enum_col("dismiss_control_visible", BOOL01),
    _plain_col("dismiss_control_accessible_name"),
    _plain_col("dismiss_control_width"),
    _plain_col("dismiss_control_height"),
    _enum_col("dismiss_succeeded", BOOL01),
    _enum_col("classification_status", CLASSIFICATION_STATUS, nullable=False),
    _enum_col("ai_review_status", AI_REVIEW_STATUS),
    _enum_col("final_label", INTERRUPT_LABEL),
)

#: 01_DATA_SPEC §7 `fact_criterion_result`.
FACT_CRITERION_RESULT: tuple[Column, ...] = (
    _id_col("observation_id"),
    _id_col("criterion_id"),
    _enum_col("older_relevance", OLDER_RELEVANCE),
    _plain_col("applicable_count"),
    _plain_col("pass_count"),
    _plain_col("fail_count"),
    _plain_col("undetermined_count"),
    _enum_col("verdict_state", VERDICT_STATE, nullable=False),
    _enum_col("automation_grade", AUTOMATION_GRADE, nullable=False),
    _enum_col("ai_review_required", BOOL01, nullable=False),
    _enum_col("final_status", VERDICT_STATE, nullable=False),
)

#: 01_DATA_SPEC §9 `fact_ai_adjudication`. `review_item_id`가 grain이며, 이 컬럼
#: 목록은 P-C의 AI review cascade(`src/landing_accessibility/engine/ai_review.py`
#: `AdjudicationRecord`, `claude-b/integration-current`@397a10d에 실재한다)가
#: 산출하는 행과 **실제로 대조해 맞췄다** — 위 모듈 docstring의 대조표를 보라.
#: cascade의 출력을 받는 것이 이 lane의 역할이지 cascade 자체를 다시 만드는 것이
#: 아니다.
FACT_AI_ADJUDICATION: tuple[Column, ...] = (
    _id_col("review_item_id"),
    _enum_col("review_task_type", REVIEW_TASK_TYPE, nullable=False),
    # `AdjudicationRecord`에는 없는 필드다 (`EvidencePackage.package_id`가 호출자
    # 쪽에만 있다) — `01_DATA_SPEC §9`가 조인 키로 요구하므로 optional로 남긴다.
    _plain_col("evidence_package_id"),
    _plain_col("deterministic_label"),
    _plain_col("semantic_model_label"),
    _plain_col("reviewer_a_label"),
    _plain_col("reviewer_b_label"),
    _enum_col("reviewer_agreement", REVIEWER_AGREEMENT),
    _plain_col("arbiter_label"),
    _enum_col("evidence_gap", BOOL01),
    _enum_col("impact_level", IMPACT_LEVEL),
    _plain_col("review_priority"),
    _enum_col("final_status", ADJUDICATION_STATUS, nullable=False),
    _enum_col("human_required", BOOL01, nullable=False),
    # 아래 3컬럼은 `01_DATA_SPEC §9` 원문에는 없으나 실제 `AdjudicationRecord`
    # dataclass 필드다 — 스키마를 실제 코드 출력과 정확히 대조하라는 지시에 따라
    # 추가했다 (드롭하면 cascade가 실제로 채우는 정보를 mart 단계에서 버리게 된다).
    _enum_col("ai_review_status", AI_REVIEW_STATUS),
    _enum_col("automation_grade", AUTOMATION_GRADE),
    # `list[str]`(자유 텍스트) — enum 검증 없이 `adjudication_binding.py`가
    # `"; "`로 join한 문자열로 직렬화해 넣는다.
    _plain_col("notes"),
)

#: 01_DATA_SPEC §8 `dim_certification`. `certification_match_status`·
#: `certification_undetermined_reason`은 `01_DATA_SPEC` 원문에는 없으나 Claude
#: A(governor)가 확정한 3-state 구분(CERTIFIED/NOT_CERTIFIED/UNDETERMINED)을
#: 담는 데 필요해 추가했다 — `certified_current`(BOOL01, 전이 판정용)는 그대로
#: 두고 이 두 컬럼은 descriptive 보고 전용이다 (어떤 전이 조건에도 쓰지 않는다,
#: X-9와 같은 원칙 — 판정을 좌우하지 않는 신호는 판정 조건으로 쓰지 않는다).
DIM_CERTIFICATION: tuple[Column, ...] = (
    _id_col("web_target_id"),
    _enum_col("certified_current", BOOL01, nullable=False),
    _plain_col("certification_number"),
    _plain_col("cert_start"),
    _plain_col("cert_end"),
    _enum_col("target_scope_match", BOOL01),
    _enum_col("service_identity_match", BOOL01),
    _plain_col("match_basis"),
    _enum_col("certification_match_status", CERTIFICATION_MATCH_STATUS, nullable=False),
    _enum_col("certification_undetermined_reason", CERTIFICATION_UNDETERMINED_REASON),
)

TABLE_SCHEMAS: dict[str, tuple[Column, ...]] = {
    "fact_landing_observation": FACT_LANDING_OBSERVATION,
    "fact_task_entry": FACT_TASK_ENTRY,
    "fact_task_step": FACT_TASK_STEP,
    "fact_interrupt_element": FACT_INTERRUPT_ELEMENT,
    "fact_criterion_result": FACT_CRITERION_RESULT,
    "fact_ai_adjudication": FACT_AI_ADJUDICATION,
    "dim_certification": DIM_CERTIFICATION,
}


def column_names(table: str) -> list[str]:
    return [c.name for c in TABLE_SCHEMAS[table]]


def validate_row(table: str, row: Mapping[str, Any], *, row_index: int = 0) -> list[str]:
    """한 행을 검증하고 오류 메시지 목록을 돌려준다 (빈 목록 = 통과).

    규칙 S-3 (`A2 §1.0`): 표에 없는 값이 나오면 실패해야 한다. `UNKNOWN`으로 흡수하지 않는다.
    """
    if table not in TABLE_SCHEMAS:
        raise SchemaValidationError(f"알 수 없는 표: {table!r}")
    errors: list[str] = []
    for col in TABLE_SCHEMAS[table]:
        has_key = col.name in row
        value = row.get(col.name)
        if col.required and not has_key:
            errors.append(f"row {row_index}: 필수 컬럼 '{col.name}' 이 없다")
            continue
        if not has_key:
            continue
        if value is None:
            if col.required and not col.nullable:
                errors.append(f"row {row_index}: '{col.name}' 은 NULL을 허용하지 않는다 (A2 N-1)")
            continue
        if col.enum is not None:
            str_value = str(value)
            if str_value not in col.enum:
                errors.append(
                    f"row {row_index}: '{col.name}' 의 허용값은 {list(col.enum)} 다. "
                    f"받은 값: {value!r} (A2 규칙 S-3)"
                )
    return errors


def validate_rows(table: str, rows: Iterable[Mapping[str, Any]]) -> list[str]:
    """전체 행을 검증하고 오류 메시지를 전부 모아 돌려준다. 빈 입력은 빈 오류 목록이다."""
    errors: list[str] = []
    for idx, row in enumerate(rows):
        errors.extend(validate_row(table, row, row_index=idx))
    return errors
