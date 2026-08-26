"""전이 규칙 T-1~T-11 과 금지 전이 X-1~X-15 — `A2 §1.11`.

`A2 §6.3` 은 이 표를 **표 그대로 구현**하고 표에 없는 조합에서 실패시키라고 요구한다.
그래서 `resolve_final_status` 는 `if/else` 의 나열이 아니라 §1.11.1 전건표를 순서대로 적용한다.

    규칙 충돌 해소 순서: T-6(NA) > T-8(UNDETERMINED) > T-7 · T-4 · T-9

두 상위 규칙은 `verdict_state` **하나만** 보고 결과를 고정하므로 adjudication 값과 label 을
읽기 전에 끝난다. 그것이 `UNDETERMINED → PASS` 경로 수를 0으로 만드는 두 겹 중 하나다
(다른 하나는 규칙 A-2 label 도메인 격리).
"""

from __future__ import annotations

from dataclasses import dataclass

from .vocabulary import (
    GRADES_REQUIRING_AI_REVIEW,
    AdjudicationStatus,
    AutomationGrade,
    ReviewTaskType,
    TriageLabel,
    VerdictState,
)


class TransitionError(ValueError):
    """`A2 §1.11` 전이 규칙 위반 — 금지 전이거나 표에 없는 조합."""


class LaunderingBlocked(TransitionError):
    """금지 전이 X-1 · X-11 · X-13 · X-15 — 판정 세탁 시도."""


#: `A2 §1.11.1` 전건표에서 `verdict_state` 하나로 결과가 고정되는 두 값.
_FIXED_BY_VERDICT: dict[VerdictState, VerdictState] = {
    # T-6 — adjudication 은 NA 를 바꾸지 못한다. 네 값 어느 것도 예외가 아니다.
    VerdictState.NA: VerdictState.NA,
    # T-8 — 같은 evidence 를 다시 읽는 어떤 절차도 "확정할 수 없다"를 반증하지 못한다.
    VerdictState.UNDETERMINED: VerdictState.UNDETERMINED,
}


@dataclass(frozen=True)
class TransitionInput:
    verdict_state: VerdictState
    ai_review_required: int
    adjudication_status: AdjudicationStatus | None = None
    confirmed_label: VerdictState | None = None
    review_task_type: ReviewTaskType | None = None


def resolve_final_status(inp: TransitionInput) -> tuple[VerdictState, str]:
    """`A2 §1.11.1` 전건표. 결과와 **적용된 규칙 id** 를 함께 돌려준다.

    규칙 id 를 함께 내는 이유: `03 Phase 6` 역추적 요구가 "왜 그 값이 됐는가"를 묻기 때문이다.
    """
    if inp.ai_review_required not in (0, 1):
        raise TransitionError(f"ai_review_required 는 0/1 이다: {inp.ai_review_required!r}")

    # 표 1~4행 — adjudication 행이 존재하지 않는다.
    if inp.ai_review_required == 0:
        if inp.adjudication_status is not None:
            raise TransitionError(
                "ai_review_required = 0 인데 adjudication 행이 있다 — "
                "전건표에 없는 조합이다 (규칙 S-3 · T-3)"
            )
        if inp.verdict_state is VerdictState.UNDETERMINED:
            # 4행 — §1.7 이 ai_review_required = 1 을 강제하므로 존재할 수 없는 조합이나,
            # 그래도 결과는 T-8 로 UNDETERMINED 다.
            return VerdictState.UNDETERMINED, "T-8"
        if inp.verdict_state is VerdictState.NA:
            return VerdictState.NA, "T-2·T-6"
        return inp.verdict_state, "T-2"

    if inp.adjudication_status is None:
        raise TransitionError(
            "ai_review_required = 1 인데 adjudication 행이 없다 (전건표 5~20행 전제)"
        )

    # 충돌 해소 1순위·2순위 — verdict_state 하나만 보고 고정한다 (19·20행, 15~18행).
    fixed = _FIXED_BY_VERDICT.get(inp.verdict_state)
    if fixed is not None:
        rule = "T-6" if inp.verdict_state is VerdictState.NA else "T-8"
        return fixed, rule

    # 여기부터 verdict_state ∈ {PASS, FAIL} — 5~14행.
    match inp.adjudication_status:
        case AdjudicationStatus.RESOLVED:
            if inp.confirmed_label is None:
                raise TransitionError("RESOLVED 인데 확정 label 이 없다 (T-7)")
            if inp.confirmed_label not in (VerdictState.PASS, VerdictState.FAIL):
                raise TransitionError(
                    f"T-7 의 확정 label 도메인은 {{PASS, FAIL}} 이다: {inp.confirmed_label.value}"
                )
            return inp.confirmed_label, "T-7"
        case AdjudicationStatus.ABSTAIN:
            return VerdictState.UNDETERMINED, "T-4"
        case AdjudicationStatus.ESCALATED_HUMAN_FINAL | AdjudicationStatus.PENDING:
            return VerdictState.UNDETERMINED, "T-9"

    raise TransitionError(f"전건표에 없는 조합: {inp}")  # pragma: no cover


def assert_transition_allowed(verdict_state: VerdictState, final_status: VerdictState) -> None:
    """금지 전이 X-1 · X-11 · X-13 · X-15 를 **기록 직전**에 막는다.

    `resolve_final_status` 를 우회해 값을 직접 쓰려는 경로에 세운 두 번째 방벽이다.
    실패주입 V-a ~ V-f 가 이 함수를 태운다.
    """
    if verdict_state is VerdictState.UNDETERMINED and final_status is not VerdictState.UNDETERMINED:
        rule = {
            VerdictState.PASS: "X-1",
            VerdictState.FAIL: "X-11",
            VerdictState.NA: "X-13",
        }[final_status]
        raise LaunderingBlocked(
            f"{rule}: verdict_state = UNDETERMINED 를 final_status = {final_status.value} 로 "
            "전이할 수 없다. 조건 없는 금지다 — evidence_gap 값·automation_grade·"
            "reviewer 합의·arbiter 판정·사람 최종검토 어느 것도 예외가 아니다 (T-8)"
        )
    if verdict_state is VerdictState.NA and final_status is not VerdictState.NA:
        raise LaunderingBlocked(
            f"X-15: verdict_state = NA 를 final_status = {final_status.value} 로 전이할 수 없다. "
            "T-6 이 T-4·T-7·T-9 보다 우선한다 — 적용기회 유무의 재판정은 새 evidence run 이다"
        )


def assert_verdict_state_immutable(previous: VerdictState, proposed: VerdictState) -> None:
    """금지 전이 X-10 / 규칙 T-10 — `verdict_state` 는 evidence 의 함수이며 **불변**이다."""
    if previous is not proposed:
        raise TransitionError(
            f"X-10: 새 judgment version 으로 verdict_state 를 "
            f"{previous.value} → {proposed.value} 로 고쳐 쓸 수 없다. "
            "값을 바꾸려면 새 evidence run 이 필요하다 (02 §12 · §1.7)"
        )


def assert_counts_identity(
    *, applicable_count: int, pass_count: int, fail_count: int, undetermined_count: int
) -> None:
    """`A2 §1.7` 항등식. `NA` 는 `applicable_count` 에 들어가지 않는다."""
    total = pass_count + fail_count + undetermined_count
    if applicable_count != total:
        raise TransitionError(
            f"applicable_count({applicable_count}) != pass+fail+undetermined({total}) "
            "— A2 §1.7 항등식 위반"
        )


def assert_triage_label_domain(review_task_type: ReviewTaskType, labels: dict[str, object]) -> None:
    """규칙 A-2 — `CRITERION_UNDETERMINED_TRIAGE` item 의 label 에 `PASS`/`FAIL` 금지 (주입 I-10).

    쓸 수 있게 두면 T-8 이 우회될 여지가 생긴다. triage 의 `RESOLVED` 는
    **triage 의 확정**이지 판정의 확정이 아니다.
    """
    if review_task_type is not ReviewTaskType.CRITERION_UNDETERMINED_TRIAGE:
        return
    allowed = {t.value for t in TriageLabel}
    for column, value in labels.items():
        if value is None:
            continue
        text = str(value)
        if text in {VerdictState.PASS.value, VerdictState.FAIL.value}:
            raise LaunderingBlocked(
                f"A-2: CRITERION_UNDETERMINED_TRIAGE 의 {column} 에 {text} 를 쓸 수 없다. "
                f"허용 label 도메인은 {sorted(allowed)} 다 (주입 I-10)"
            )
        if text not in allowed:
            raise TransitionError(
                f"A-2: {column} = {text!r} 는 triage 의 허용 label 이 아니다 (규칙 S-3)"
            )


def assert_automation_grade(
    *,
    grade: AutomationGrade,
    final_status: VerdictState,
    ai_review_required: int,
    evidence_present: set[str],
    required_evidence: dict[AutomationGrade, set[str]] | None = None,
) -> None:
    """`A2 §3.3` 정합 제약 G-2 · G-5 · G-6."""
    if grade in GRADES_REQUIRING_AI_REVIEW and ai_review_required != 1:
        raise TransitionError(f"G-2: {grade.value} 는 ai_review_required = 1 이어야 한다")
    ungraded = grade is AutomationGrade.UNGRADED
    unresolved = final_status in (VerdictState.UNDETERMINED, VerdictState.NA)
    if ungraded != unresolved:
        raise TransitionError(
            f"G-5: automation_grade = UNGRADED ↔ final_status ∈ {{UNDETERMINED, NA}} 는 동치다 "
            f"(grade={grade.value}, final_status={final_status.value})"
        )
    reqs = required_evidence or _DEFAULT_GRADE_EVIDENCE
    missing = reqs.get(grade, set()) - evidence_present
    if missing:
        raise TransitionError(
            f"G-6: {grade.value} 가 요구하는 증거가 없다: {sorted(missing)} "
            "— 증거 없이 상위 등급을 주장하지 않는다"
        )


_DEFAULT_GRADE_EVIDENCE: dict[AutomationGrade, set[str]] = {
    AutomationGrade.A_BROWSER_NATIVE: {"probe_path", "dom_path", "ax_path"},
    AutomationGrade.B_DETERMINISTIC_RULE: {"probe_path", "dom_path", "ax_path", "rule_id"},
    AutomationGrade.C_CV_GEOMETRY: {"screenshot_path", "bbox", "algorithm_id"},
    AutomationGrade.D_EMBEDDING_TEXT: {"input_text", "model_id", "score", "allowed_labels"},
    AutomationGrade.E_VLM: {"evidence_package_id", "model_id"},
    AutomationGrade.F_HUMAN_FINAL: {"reviewer_id", "evidence_package_id", "rationale"},
    AutomationGrade.UNGRADED: set(),
}


def assert_frame_column_not_modified(
    *, observation_writes: dict[str, object], frame_columns: set[str] | None = None
) -> None:
    """규칙 W-1 · T-11 (주입 I-11) — 관측 행이 Frame 컬럼을 in-place 수정하지 못한다.

    `dim_web_target` 은 `A2 §1.4.1` supersede 경로로만 갱신된다. 관측이 Frame 을 직접
    고치는 것은 규칙 S-2 위반이다.
    """
    frame = frame_columns or {
        "web_eligibility_status",
        "web_target_status",
        "review_status",
        "mapping_status",
        "official_url",
    }
    leaked = frame & observation_writes.keys()
    if leaked:
        raise TransitionError(
            f"W-1 · T-11: 관측 행이 Frame 컬럼을 직접 수정하려 했다: {sorted(leaked)}. "
            "Frame 재판정은 §1.4.1 supersede 경로로만 한다 (규칙 S-2 · 주입 I-11)"
        )


def assert_measurement_status_not_counted_as_verdict(measurement_status: str) -> None:
    """금지 전이 X-4 · 규칙 M-1 — 수집 실패를 `FAIL`/`UNDETERMINED` 로 세지 않는다."""
    if measurement_status != "MEASURED":
        raise TransitionError(
            f"T-1 · M-1: measurement_status = {measurement_status} 인 관측은 "
            "fact_criterion_result 행을 생성하지 않는다. FAIL 로도 UNDETERMINED 로도 세지 않는다"
        )


def assert_supersede_direction(previous: str, proposed: str) -> None:
    """규칙 W-2 (주입 I-12) — supersede 는 **배제 방향으로만** 쓴다.

    `EXCLUDED → ELIGIBLE_WEB` 처럼 범위 **안으로 되돌리는** 방향은 금지다.
    관측이 표본을 넓히는 경로를 열면 프레임이 결과를 따라 움직인다.
    """
    if previous == "EXCLUDED" and proposed != "EXCLUDED":
        raise TransitionError(
            f"W-2: supersede 를 배제 방향의 반대로 썼다 ({previous} → {proposed}). "
            "supersede 경로는 배제 방향으로만 쓴다 (주입 I-12)"
        )


def assert_not_eligible_has_evidence(evidence: dict[str, object]) -> None:
    """규칙 M-4 (주입 I-15) — `NOT_ELIGIBLE_AT_COLLECTION` 은 **양의 관측**이다.

    증거 없이 기록할 수 없다. 남기지 못했으면 그것은 이 값이 아니라
    `FAILED_EVIDENCE_INCOMPLETE` 다.
    """
    required = {"screenshot_initial_path", "dom_path", "final_url"}
    missing = {k for k in required if not evidence.get(k)}
    if missing:
        raise TransitionError(
            f"M-4: NOT_ELIGIBLE_AT_COLLECTION 을 증거 없이 기록할 수 없다. 결손: {sorted(missing)}. "
            "증거를 남기지 못했으면 FAILED_EVIDENCE_INCOMPLETE 다 (주입 I-15)"
        )


def assert_no_measurement_status_reclassification(previous: str, proposed: str) -> None:
    """규칙 M-5 · 금지 전이 X-12 (주입 I-16).

    `FAILED_*` 관측을 `NOT_ELIGIBLE_AT_COLLECTION` 으로 재분류해 표본에서 빼지 않는다.
    두 계열은 서로 다른 사건이며 증거 요구도 다르다.
    """
    if previous.startswith("FAILED_") and proposed == "NOT_ELIGIBLE_AT_COLLECTION":
        raise TransitionError(
            f"X-12 · M-5: {previous} 를 {proposed} 로 재분류해 표본에서 뺄 수 없다. "
            "HTTP 401/403/429·차단 인터스티셜은 FAILED_ACCESS_BLOCKED 다 (주입 I-16)"
        )


def assert_not_used_as_transition_condition(condition_keys: set[str]) -> None:
    """금지 전이 X-9 (주입 I-23).

    `evidence_gap` · `impact_level` · `review_priority` · `automation_grade` 는
    재수집 우선순위·보고 분해용 신호이며 **어떤 전이도 허가하지 않는다.**
    """
    forbidden = {"evidence_gap", "impact_level", "review_priority", "automation_grade"}
    leaked = forbidden & condition_keys
    if leaked:
        raise LaunderingBlocked(
            f"X-9: {sorted(leaked)} 를 전이 허가 조건으로 쓸 수 없다. "
            "laundering 을 막는 것은 이 컬럼이 아니라 T-8 과 X-1 이다 (주입 I-23)"
        )
