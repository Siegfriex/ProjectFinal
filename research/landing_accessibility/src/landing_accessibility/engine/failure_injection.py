"""실패주입 harness — `02 §14` + `A2 §1.11` V-a~V-g + `A2 §6.3.1` I-1~I-29.

`02 §14`: *모든 guard 가 실제로 차단하는지 확인한다.*
guard 를 세워 두고 한 번도 태우지 않으면 `E000_V2_VALIDATED` 가 **비어 있는 근거로** 닫힌다.

## 두 종류의 기대

| 기대 | 뜻 |
|---|---|
| `BLOCKED` | guard 가 실제로 차단해야 한다 |
| `MUST_PASS` | **차단되면 안 된다.** 정당한 값을 막는 과탐(over-blocking)도 결함이다 |

`A2 §6.3.1` 이 I-4 · I-14 두 건을 일부러 `MUST_PASS` 로 넣은 이유가 그것이다 —
차단만 태우면 규칙 S-3 이 정당한 값을 막아 파이프라인을 세우는 사고가 검증되지 않는다.

## 이 harness 는 fixture 만 다룬다

주입 대상은 전부 로컬 자료구조와 임시 디렉터리다. 어떤 케이스도 네트워크에 나가지 않는다.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Any

from ..evidence_manifest import (
    MissingRunManifestError,
    load_run_manifest,
    verify_run,
)
from . import reporting
from .ai_review import (
    CRITERION_ALLOWED_LABELS,
    EvidencePackage,
    HumanFinalQueue,
    ReviewCascade,
    StubArbiter,
    StubReviewer,
)
from .depth import (
    DepthRuleError,
    assert_detail_rollup,
    assert_gate_endpoint_allowed,
    assign_depth_segments,
    auth_gate_before_endpoint,
    compute_depth,
    gate_outcome,
    gate_outcome_from_decision,
)
from .evidence import (
    DuplicateObservationError,
    EvidenceError,
    EvidenceOverwriteError,
    EvidenceRun,
    PreregistrationError,
    RecollectionPreregistration,
    RunSealedError,
    SymlinkEscapeError,
    select_canonical_run,
)
from .firewall import (
    ExecutionMode,
    NavigationBlockedError,
    RealTargetBlockedError,
    UnknownExecutionModeError,
    assert_mode_allowed,
    assert_navigation_allowed,
)
from .gate_classifier import (
    GateClassificationStatus,
    GateEvidenceError,
    GateSignals,
    assert_gate_kind_evidence,
    classify_gate_kind,
)
from .transitions import (
    LaunderingBlocked,
    TransitionError,
    TransitionInput,
    assert_no_measurement_status_reclassification,
    assert_not_eligible_has_evidence,
    assert_not_used_as_transition_condition,
    assert_supersede_direction,
    assert_transition_allowed,
    assert_triage_label_domain,
    assert_verdict_state_immutable,
    resolve_final_status,
)
from .vocabulary import (
    AdjudicationStatus,
    ClosedVocabularyError,
    EndpointStatus,
    EndpointStatusDetail,
    GateKind,
    InteractionArchetype,
    MeasurementStatus,
    ReviewTaskType,
    VerdictState,
    is_measurement_failed,
    validate,
)


class Expectation(StrEnum):
    BLOCKED = "BLOCKED"
    MUST_PASS = "MUST_PASS"


@dataclass(frozen=True)
class InjectionCase:
    case_id: str
    rule: str
    description: str
    expectation: Expectation
    run: Callable[[Path], None]


@dataclass
class CaseResult:
    case_id: str
    rule: str
    expectation: str
    outcome: str
    detail: str

    @property
    def ok(self) -> bool:
        return self.outcome == "AS_EXPECTED"


def _package(labels: tuple[str, ...]) -> EvidencePackage:
    return EvidencePackage(
        package_id="pkg-fixture",
        observation_id="obs-fixture",
        screenshot_crop_relpath="l0a/screen_initial.png",
        surrounding_screenshot_relpath=None,
        dom_facts={"role": "dialog"},
        ax_facts={"name": "안내"},
        bbox={"x": 0, "y": 0, "w": 10, "h": 10},
        relevant_text="안내",
        allowed_labels=labels,
    )


def _seed_run(tmp: Path, name: str) -> EvidenceRun:
    run = EvidenceRun.create(tmp, name, execution_mode=ExecutionMode.FIXTURE)
    run.open_observation("obs-1")
    run.write_artifact("obs-1", "l0a/dom.html", b"<html></html>")
    return run


# ── 02 §14 핵심 8종 + firewall ────────────────────────────────────────────────
def _c_real_target(tmp: Path) -> None:
    assert_mode_allowed(ExecutionMode.REAL_TARGET)


def _c_real_target_string(tmp: Path) -> None:
    assert_mode_allowed("REAL_TARGET")


def _c_real_target_navigation(tmp: Path) -> None:
    assert_navigation_allowed("REAL_TARGET", "https://www.example.co.kr/")


def _c_http_in_fixture_mode(tmp: Path) -> None:
    assert_navigation_allowed(ExecutionMode.FIXTURE, "https://www.example.co.kr/")


def _c_dry_run_navigation(tmp: Path) -> None:
    assert_navigation_allowed(ExecutionMode.SHADOW_DRY_RUN, "file:///tmp/x.html")


def _c_unknown_mode(tmp: Path) -> None:
    assert_mode_allowed("LIVE")


def _c_fixture_mode_allowed(tmp: Path) -> None:
    assert_mode_allowed(ExecutionMode.FIXTURE)


def _c_duplicate_observation(tmp: Path) -> None:
    run = _seed_run(tmp, "dup")
    run.open_observation("obs-1")


def _c_missing_manifest(tmp: Path) -> None:
    empty = tmp / "no-manifest"
    empty.mkdir()
    load_run_manifest(empty)


def _c_evidence_swap(tmp: Path) -> None:
    run = _seed_run(tmp, "swap")
    run.write_artifact("obs-1", "l0a/probe.json", b'{"a":1}')
    run.seal()
    (run.run_dir / "l0a" / "probe.json").write_bytes(b'{"a":2}')
    report = verify_run(run.run_dir)
    if report["status"] != "FAILED":
        raise AssertionError(f"evidence swap 이 검출되지 않았다: {report['status']}")
    raise _Detected(
        f"verify_run status = {report['status']}, hash_mismatch={report['hash_mismatch']}"
    )


def _c_overwrite(tmp: Path) -> None:
    run = _seed_run(tmp, "over")
    run.write_artifact("obs-1", "l0a/dom.html", b"<html>2</html>")


def _c_symlink_escape(tmp: Path) -> None:
    outside = tmp / "outside"
    outside.mkdir()
    run = _seed_run(tmp, "sym")
    (run.run_dir / "l0a" / "escape").symlink_to(outside, target_is_directory=True)
    run.write_artifact("obs-1", "l0a/escape/leak.json", b"{}")


def _c_reseal(tmp: Path) -> None:
    run = _seed_run(tmp, "reseal")
    run.seal()
    run.seal()


def _c_absolute_relpath(tmp: Path) -> None:
    run = _seed_run(tmp, "abs")
    run.write_artifact("obs-1", "/etc/passwd", b"x")


def _c_parent_relpath(tmp: Path) -> None:
    run = _seed_run(tmp, "parent")
    run.write_artifact("obs-1", "../escape.json", b"{}")


def _c_ai_disagreement(tmp: Path) -> None:
    """A·B 불일치 + arbiter 기권 → `ABSTAIN` 이어야 하고 `RESOLVED` 로 내려가면 안 된다."""
    cascade = ReviewCascade(
        reviewer_a=StubReviewer("A", label="PASS"),
        reviewer_b=StubReviewer("B", label="FAIL"),
        arbiter=StubArbiter(abstain=True),
    )
    result = cascade.run(
        review_item_id="ri-1",
        review_task_type=ReviewTaskType.CRITERION_VERDICT,
        verdict_state=VerdictState.PASS,
        package=_package(CRITERION_ALLOWED_LABELS),
    )
    if result.adjudication.final_status != AdjudicationStatus.ABSTAIN.value:
        raise AssertionError(f"불일치가 {result.adjudication.final_status} 로 끝났다")
    if result.criterion_final_status != VerdictState.UNDETERMINED.value:
        raise AssertionError("ABSTAIN 이 UNDETERMINED 로 보수화되지 않았다 (T-4)")
    raise _Detected("A·B 불일치 → ABSTAIN → criterion UNDETERMINED (T-4)")


def _c_human_budget(tmp: Path) -> None:
    """`HUMAN_FINAL_REVIEW_MAX = 5` 초과 시 `RESOLVED` 로 내리지 않는다 (규칙 A-1 · X-6)."""
    queue = HumanFinalQueue()
    cascade = ReviewCascade(
        reviewer_a=StubReviewer("A", label="PASS"),
        reviewer_b=StubReviewer("B", label="FAIL"),
        arbiter=StubArbiter(escalate_to_human=True),
        human_queue=queue,
    )
    statuses = []
    for i in range(7):
        r = cascade.run(
            review_item_id=f"ri-{i}",
            review_task_type=ReviewTaskType.CRITERION_VERDICT,
            verdict_state=VerdictState.FAIL,
            package=_package(CRITERION_ALLOWED_LABELS),
        )
        statuses.append(r.adjudication.final_status)
    queue.assert_within_budget()
    if queue.used != 5:
        raise AssertionError(f"human queue 가 5에서 멈추지 않았다: {queue.used}")
    if statuses[5:] != ["ABSTAIN", "ABSTAIN"]:
        raise AssertionError(f"예산 소진 후 상태가 ABSTAIN 이 아니다: {statuses[5:]}")
    raise _Detected("6·7번째는 ESCALATION_DECLINED_BUDGET + ABSTAIN (규칙 A-1)")


def _c_banner_mutation(tmp: Path) -> None:
    """fixture 를 몰래 바꿔치기하면 manifest 해시가 잡아낸다 (`02 §14` banner mutation)."""
    run = _seed_run(tmp, "banner")
    run.write_artifact("obs-1", "l0a/banner.html", b"<div>original banner</div>")
    run.seal()
    (run.run_dir / "l0a" / "banner.html").write_bytes(b"<div>mutated banner</div>")
    report = verify_run(run.run_dir)
    if report["status"] != "FAILED":
        raise AssertionError("banner mutation 이 검출되지 않았다")
    raise _Detected(f"hash_mismatch={len(report['hash_mismatch'])} 건")


def _c_manifest_only_mode_not_verified(tmp: Path) -> None:
    """raw 없는 clone 의 구조검증을 `VERIFIED` 로 세지 않는다 (`07 §4`)."""
    run = _seed_run(tmp, "structonly")
    run.seal()
    report = verify_run(run.run_dir, require_files=False)
    if report["status"] != "MANIFEST_WELL_FORMED_FILES_NOT_CHECKED":
        raise AssertionError(f"구조검증 상태가 어긋난다: {report['status']}")
    raise _Detected("STRUCTURE_ONLY_RAW_ABSENT 가 VERIFIED 와 구분된다")


# ── A2 §1.11 실패주입 V-a ~ V-g ──────────────────────────────────────────────
def _v_undetermined_to(final: VerdictState) -> Callable[[Path], None]:
    def _run(tmp: Path) -> None:
        assert_transition_allowed(VerdictState.UNDETERMINED, final)

    return _run


def _v_c_resolved_pass(tmp: Path) -> None:
    """감사가 실증한 정확한 laundering 경로: UNDETERMINED ∧ RESOLVED ∧ arbiter=PASS ∧ gap=0."""
    status, _rule = resolve_final_status(
        TransitionInput(
            verdict_state=VerdictState.UNDETERMINED,
            ai_review_required=1,
            adjudication_status=AdjudicationStatus.RESOLVED,
            confirmed_label=VerdictState.PASS,
        )
    )
    if status is not VerdictState.UNDETERMINED:
        raise AssertionError(f"V-c 가 새어나갔다: {status.value}")
    assert_triage_label_domain(
        ReviewTaskType.CRITERION_UNDETERMINED_TRIAGE, {"arbiter_label": "PASS"}
    )


def _v_f_na_abstain(tmp: Path) -> None:
    status, _ = resolve_final_status(
        TransitionInput(
            verdict_state=VerdictState.NA,
            ai_review_required=1,
            adjudication_status=AdjudicationStatus.ABSTAIN,
        )
    )
    if status is not VerdictState.NA:
        raise AssertionError(f"T-6 이 T-4 보다 우선하지 않았다: {status.value}")
    assert_transition_allowed(VerdictState.NA, VerdictState.UNDETERMINED)


def _v_g_optional_stopping(tmp: Path) -> None:
    select_canonical_run(
        [
            {
                "evidence_run_id": "r1",
                "measurement_status": "MEASURED",
                "verdict_state": "UNDETERMINED",
            },
            {"evidence_run_id": "r2", "measurement_status": "MEASURED", "verdict_state": "PASS"},
        ]
    )


# ── A2 §6.3.1 I-1 ~ I-29 ─────────────────────────────────────────────────────
def _i1(tmp: Path) -> None:
    """금융 + 로그인 gate 를 `AUTH_GATE_REACHED` 로 기록하려는 시도."""
    status, _detail = gate_outcome(InteractionArchetype.FINANCIAL_ACTION_ENTRY, GateKind.LOGIN)
    if status is EndpointStatus.AUTH_GATE_REACHED:
        raise AssertionError("E-5 가 발화하지 않았다")
    assert_gate_endpoint_allowed(InteractionArchetype.FINANCIAL_ACTION_ENTRY, GateKind.LOGIN)
    # 여기까지는 정상. 이제 잘못된 기록을 시도한다.
    assert_detail_rollup(
        EndpointStatus.AUTH_GATE_REACHED,
        EndpointStatusDetail.ENDPOINT_VIA_AUTH_GATE,
        InteractionArchetype.FINANCIAL_ACTION_ENTRY,
    )


def _i2(tmp: Path) -> None:
    assert_detail_rollup(
        EndpointStatus.FUNCTION_ENDPOINT_REACHED,
        EndpointStatusDetail.ENDPOINT_VIA_AUTH_GATE,
        InteractionArchetype.QUERY,
    )


def _i3(tmp: Path) -> None:
    assert_gate_endpoint_allowed(
        InteractionArchetype.COMMUNICATION_ENTRY, GateKind.IDENTITY_VERIFICATION
    )


def _i4(tmp: Path) -> None:
    """**통과해야 한다** — 커뮤니티의 본인인증 gate 는 `AUTH_GATE_REACHED` 로 남는다."""
    status, detail = gate_outcome(
        InteractionArchetype.COMMUNICATION_ENTRY, GateKind.IDENTITY_VERIFICATION
    )
    if status is not EndpointStatus.AUTH_GATE_REACHED or detail is not None:
        raise AssertionError(f"무주지 재발: {status.value} / {detail}")
    assert_detail_rollup(status, detail, InteractionArchetype.COMMUNICATION_ENTRY)
    validate("endpoint_status", status.value)


def _i5(tmp: Path) -> None:
    """gate 관측 이후 activation 이 더 있는 궤적 — 규칙 E-7 gate 통과 금지."""
    depth = compute_depth(
        archetype=InteractionArchetype.FINANCIAL_ACTION_ENTRY,
        area_step_index=1,
        endpoint_step_index=2,
        endpoint_status=EndpointStatus.FUNCTION_ENDPOINT_REACHED,
        endpoint_status_detail=EndpointStatusDetail.ENDPOINT_VIA_AUTH_GATE,
    )
    assign_depth_segments(4, depth)  # endpoint 이후에도 step 이 2개 더 있다


def _i6(tmp: Path) -> None:
    entries = [
        {
            "archetype": "FINANCIAL_ACTION_ENTRY",
            "endpoint_status": "FUNCTION_ENDPOINT_REACHED",
            "endpoint_status_detail": "ENDPOINT_VIA_AUTH_GATE",
            "auth_gate_before_endpoint": 0,
        }
    ]
    reporting.assert_auth_gate_aggregation(entries, reported=0)


def _i7(tmp: Path) -> None:
    value = auth_gate_before_endpoint(
        auth_gate_detected_per_step=[0, 1],
        endpoint_status_detail=EndpointStatusDetail.ENDPOINT_VIA_AUTH_GATE,
    )
    if value != 0:
        raise AssertionError("endpoint 를 실현한 gate 가 before 로 세어졌다")
    raise _Detected("endpoint gate step 은 before 에서 제외된다 (E-9)")


def _i8(tmp: Path) -> None:
    validate("endpoint_status", None)  # NULL 을 허용값처럼 쓰려는 시도


def _i9(tmp: Path) -> None:
    summary = {"FINANCIAL_ACTION_ENTRY": {"n": 3, "mpfed_median": 2.0}}
    reporting.assert_stratified(summary)


def _i10(tmp: Path) -> None:
    assert_triage_label_domain(
        ReviewTaskType.CRITERION_UNDETERMINED_TRIAGE, {"reviewer_a_label": "FAIL"}
    )


def _i11(tmp: Path) -> None:
    from .transitions import assert_frame_column_not_modified

    assert_frame_column_not_modified(
        observation_writes={"measurement_status": "MEASURED", "web_eligibility_status": "EXCLUDED"}
    )


def _i12(tmp: Path) -> None:
    assert_supersede_direction("EXCLUDED", "ELIGIBLE_WEB")


def _i13(tmp: Path) -> None:
    reporting.phase5_measurement_quality(
        adjudications=[],
        not_eligible_at_collection_count=2,
        eligibility_reversal_rate=None,
        recollection_runs=0,
        decision_coverage_first_run=None,
        decision_coverage_canonical_run=None,
        unpreregistered_recollection_runs=0,
        over_limit_recollection_runs=0,
    )


def _i14(tmp: Path) -> None:
    """**실패하면 안 된다** — S-3 은 표에 *없는* 값의 규칙이다 (규칙 M-3 오탐 회귀검사)."""
    status = validate("measurement_status", "NOT_ELIGIBLE_AT_COLLECTION")
    assert status is MeasurementStatus.NOT_ELIGIBLE_AT_COLLECTION
    validate("measurement_status_detail", "APP_ONLY_AT_COLLECTION")


def _i15(tmp: Path) -> None:
    assert_not_eligible_has_evidence({"final_url": "file:///x.html"})


def _i16(tmp: Path) -> None:
    assert_no_measurement_status_reclassification(
        "FAILED_ACCESS_BLOCKED", "NOT_ELIGIBLE_AT_COLLECTION"
    )


def _i17(tmp: Path) -> None:
    if is_measurement_failed(MeasurementStatus.NOT_ELIGIBLE_AT_COLLECTION):
        raise AssertionError("계열 경계가 무너졌다 — N-6 위반")
    raise _Detected("NOT_ELIGIBLE_AT_COLLECTION 은 LIKE 'FAILED_%' 에 걸리지 않는다")


def _i18(tmp: Path) -> None:
    reporting.assert_undetermined_not_dropped(before=["c1", "c2"], after=["c1"])


def _i19(tmp: Path) -> None:
    reporting.assert_abstention_split({"rate": 0.1})


def _i20(tmp: Path) -> None:
    status, rule = resolve_final_status(
        TransitionInput(
            verdict_state=VerdictState.UNDETERMINED,
            ai_review_required=1,
            adjudication_status=AdjudicationStatus.RESOLVED,
            confirmed_label=VerdictState.FAIL,
        )
    )
    if status is not VerdictState.UNDETERMINED or rule != "T-8":
        raise AssertionError(f"T-8 이 T-7 보다 우선하지 않았다: {status.value}/{rule}")
    assert_transition_allowed(VerdictState.UNDETERMINED, VerdictState.FAIL)


def _i21(tmp: Path) -> None:
    reporting.phase5_measurement_quality(
        adjudications=[{"review_task_type": "CRITERION_VERDICT", "final_status": "PENDING"}],
        not_eligible_at_collection_count=0,
        eligibility_reversal_rate=None,
        recollection_runs=0,
        decision_coverage_first_run=None,
        decision_coverage_canonical_run=None,
        unpreregistered_recollection_runs=0,
        over_limit_recollection_runs=0,
    )


def _i22(tmp: Path) -> None:
    assert_verdict_state_immutable(VerdictState.UNDETERMINED, VerdictState.PASS)


def _i23(tmp: Path) -> None:
    assert_not_used_as_transition_condition({"evidence_gap", "impact_level"})


def _i24(tmp: Path) -> None:
    chosen = select_canonical_run(
        [
            {"evidence_run_id": "r1", "measurement_status": "MEASURED"},
            {
                "evidence_run_id": "r2",
                "measurement_status": "MEASURED",
                "attempt_index": 2,
                "preregistration": {"expected_evidence": ["probe"]},
                "produced_evidence": ["probe"],
            },
        ]
    )
    if chosen["evidence_run_id"] != "r1":
        raise AssertionError("RC-1 상한 초과 run 이 정본이 됐다")
    raise _Detected("attempt_index 2 > MAX_RECOLLECTION_RUNS_PER_WEB_TARGET(1) → 정본 제외")


def _i25(tmp: Path) -> None:
    RecollectionPreregistration(
        target_criterion_observation_ids=["c1"],
        reason_evidence_gap=1,
        reason_impact_level="HIGH",
        expected_evidence=["probe"],
        attempt_index=1,
        preregistered_at="2026-08-27T10:00:00.000000Z",
    ).validate(collection_started_at="2026-08-27T09:00:00.000000Z")


def _i25b(tmp: Path) -> None:
    RecollectionPreregistration(
        target_criterion_observation_ids=["c1"],
        reason_evidence_gap=1,
        reason_impact_level="HIGH",
        expected_evidence=[],
        attempt_index=1,
        preregistered_at="2026-08-27T08:00:00.000000Z",
    ).validate(collection_started_at="2026-08-27T09:00:00.000000Z")


def _i25c(tmp: Path) -> None:
    """항상 산출되는 `manifest` 를 expected_evidence 로 적어 교체조건을 자동 충족시키려는 시도."""
    RecollectionPreregistration(
        target_criterion_observation_ids=["c1"],
        reason_evidence_gap=1,
        reason_impact_level="HIGH",
        expected_evidence=["manifest"],
        attempt_index=1,
        preregistered_at="2026-08-27T08:00:00.000000Z",
    ).validate(collection_started_at="2026-08-27T09:00:00.000000Z")


def _i26(tmp: Path) -> None:
    """판정 결과를 중단 조건으로 삼은 궤적 — `select_canonical_run` 이 결과를 아예 못 본다."""
    select_canonical_run(
        [{"evidence_run_id": "r1", "measurement_status": "MEASURED", "final_status": "PASS"}]
    )


def _i27(tmp: Path) -> None:
    chosen = select_canonical_run(
        [
            {"evidence_run_id": "r1", "measurement_status": "MEASURED"},
            {
                "evidence_run_id": "r2",
                "measurement_status": "MEASURED",
                "attempt_index": 1,
                "preregistration": {"expected_evidence": ["ax"]},
                "produced_evidence": ["dom"],
            },
        ]
    )
    if chosen["evidence_run_id"] != "r1":
        raise AssertionError("사전선언 evidence 를 못 낸 재수집 run 이 정본이 됐다")
    raise _Detected("expected_evidence 미산출 → 민감도 분석 전용, 정본 아님 (RC-3)")


def _i28(tmp: Path) -> None:
    chosen = select_canonical_run(
        [
            {"evidence_run_id": "r1", "measurement_status": "MEASURED"},
            {
                "evidence_run_id": "r2",
                "measurement_status": "MEASURED",
                "attempt_index": 1,
                "produced_evidence": ["probe"],
            },
        ]
    )
    if chosen["evidence_run_id"] != "r1":
        raise AssertionError("미선언 재수집 run 이 정본이 됐다")
    raise _Detected("recollection_preregistration 없는 run 은 정본이 아니다 (RC-4)")


def _i28b(tmp: Path) -> None:
    """criterion 마다 다른 run 을 골라 섞는 시도 — 교체는 **run 단위 일괄** 이다."""
    runs: list[dict[str, Any]] = [
        {"evidence_run_id": "r1", "measurement_status": "MEASURED"},
        {
            "evidence_run_id": "r2",
            "measurement_status": "MEASURED",
            "attempt_index": 1,
            "preregistration": {"expected_evidence": ["probe"]},
            "produced_evidence": ["probe"],
        },
    ]
    first = select_canonical_run(runs)
    second = select_canonical_run(runs)
    if first["evidence_run_id"] != second["evidence_run_id"]:
        raise AssertionError("같은 입력에서 다른 정본이 나왔다 — run 단위 일괄이 아니다")
    raise _Detected(f"정본은 run 단위로 하나로 고정된다: {first['evidence_run_id']}")


def _i29(tmp: Path) -> None:
    reporting.phase5_measurement_quality(
        adjudications=[],
        not_eligible_at_collection_count=0,
        eligibility_reversal_rate=None,
        recollection_runs=1,
        decision_coverage_first_run=0.8,
        decision_coverage_canonical_run=None,
        unpreregistered_recollection_runs=0,
        over_limit_recollection_runs=0,
    )


# ── Q-9: gate 종류 판별 (오케스트레이터 P1) ──────────────────────────────────
#: 두 fixture 가 실제로 내보내는 신호를 그대로 옮긴 것이다. 판별기는 `data-gate-kind` 를 읽지 않는다.
_LOGIN_SIGNALS = GateSignals(
    text="로그인 아이디 비밀번호 아이디 찾기 비밀번호 찾기 회원가입",
    password_input_count=1,
    username_autocomplete_count=1,
)
_IDENTITY_SIGNALS = GateSignals(
    text=(
        "휴대폰 본인확인 PASS 앱 인증 카카오 인증 네이버 인증 토스 인증 통신사 "
        "SKT KT LG U+ 알뜰폰 이름 생년월일 주민등록번호 뒷자리 휴대전화번호 인증번호"
    ),
    tel_autocomplete_count=1,
    identity_number_input_count=2,
    otp_input_count=1,
    carrier_option_count=4,
    simple_auth_provider_count=4,
)
_AMBIGUOUS_SIGNALS = GateSignals(
    text=(
        "로그인 또는 본인확인으로 계속하기 아이디 비밀번호 통신사 SKT KT LG U+ 알뜰폰 "
        "휴대전화번호 인증번호"
    ),
    password_input_count=1,
    username_autocomplete_count=1,
    tel_autocomplete_count=1,
    otp_input_count=1,
    carrier_option_count=4,
)


def _q9_1(tmp: Path) -> None:
    """**통과해야 한다** — 로그인 fixture 는 신호만으로 LOGIN 으로 갈린다."""
    d = classify_gate_kind(_LOGIN_SIGNALS)
    if not d.resolved or d.gate_kind is not GateKind.LOGIN:
        raise AssertionError(f"로그인 gate 판별 실패: {d.as_dict()}")
    assert_gate_kind_evidence(GateKind.LOGIN, _LOGIN_SIGNALS)


def _q9_2(tmp: Path) -> None:
    """**통과해야 한다** — 본인인증 fixture 는 신호만으로 IDENTITY_VERIFICATION 으로 갈린다."""
    d = classify_gate_kind(_IDENTITY_SIGNALS)
    if not d.resolved or d.gate_kind is not GateKind.IDENTITY_VERIFICATION:
        raise AssertionError(f"본인인증 gate 판별 실패: {d.as_dict()}")
    assert_gate_kind_evidence(GateKind.IDENTITY_VERIFICATION, _IDENTITY_SIGNALS)


def _q9_3(tmp: Path) -> None:
    """오판 주입 — 커뮤니티의 본인인증 gate 를 LOGIN 으로 기록하려는 시도.

    규칙 E-6a 만으로는 잡히지 않는다. 오판된 값 자체는 그 규칙이 **정당한 것으로 통과시키기**
    때문이다. 근거 검사(`assert_gate_kind_evidence`)가 그 조용한 오판을 잡는다.
    """
    assert_gate_kind_evidence(GateKind.LOGIN, _IDENTITY_SIGNALS)


def _q9_4(tmp: Path) -> None:
    """오판의 **결과**가 실제로 위험한지 보인다 — 없어야 할 ENDPOINT_VIA_AUTH_GATE 가 생긴다."""
    status, detail = gate_outcome(InteractionArchetype.COMMUNICATION_ENTRY, GateKind.LOGIN)
    if status is not EndpointStatus.FUNCTION_ENDPOINT_REACHED:
        raise AssertionError("전제가 깨졌다 — 커뮤니티+로그인은 endpoint 여야 한다 (E-5)")
    if detail is not EndpointStatusDetail.ENDPOINT_VIA_AUTH_GATE:
        raise AssertionError("전제가 깨졌다 — ENDPOINT_VIA_AUTH_GATE 여야 한다 (E-5)")
    correct, correct_detail = gate_outcome(
        InteractionArchetype.COMMUNICATION_ENTRY, GateKind.IDENTITY_VERIFICATION
    )
    if correct is not EndpointStatus.AUTH_GATE_REACHED or correct_detail is not None:
        raise AssertionError("본인인증은 커뮤니티에서 비-endpoint 여야 한다 (E-6a)")
    raise _Detected(
        "오판 시 endpoint_reached 가 0 → 1 로 뒤집히고 MPFED 가 NULL → 정수로 바뀐다. "
        "근거 검사(Q9-3)가 없으면 이 뒤집힘이 조용히 통과한다"
    )


def _q9_5(tmp: Path) -> None:
    """**통과해야 한다** — 모호한 gate 는 강제분류되지 않는다 (abstain 경로 실증)."""
    d = classify_gate_kind(_AMBIGUOUS_SIGNALS)
    if d.status is not GateClassificationStatus.UNDETERMINED or d.gate_kind is not None:
        raise AssertionError(f"모호한 gate 가 강제분류됐다: {d.as_dict()}")
    if not (d.login_basis and d.identity_basis):
        raise AssertionError("판별 불가의 근거가 기록되지 않았다")


def _q9_6(tmp: Path) -> None:
    """확정하지 못한 gate 를 LOGIN 으로 기록하려는 시도."""
    assert_gate_kind_evidence(GateKind.LOGIN, _AMBIGUOUS_SIGNALS)


def _q9_7(tmp: Path) -> None:
    """**통과해야 한다** — 판별 불가 gate 는 어느 archetype 에서도 endpoint 로 승격되지 않는다."""
    d = classify_gate_kind(_AMBIGUOUS_SIGNALS)
    for archetype in (
        InteractionArchetype.FINANCIAL_ACTION_ENTRY,
        InteractionArchetype.COMMUNICATION_ENTRY,
        InteractionArchetype.QUERY,
    ):
        status, detail = gate_outcome_from_decision(archetype, d)
        if status is not EndpointStatus.AUTH_GATE_REACHED or detail is not None:
            raise AssertionError(
                f"{archetype.value} 에서 판별 불가 gate 가 승격됐다: {status.value}/{detail}"
            )


class _Detected(Exception):
    """guard 가 예외가 아니라 **검출 리포트**로 차단을 증명한 경우의 신호."""


def registry() -> list[InjectionCase]:
    """`02 §14` + `A2 §1.11` + `A2 §6.3.1` 전건. 순서는 문서 순서를 따른다."""
    B, P = Expectation.BLOCKED, Expectation.MUST_PASS
    return [
        # ── REAL-TARGET FIREWALL (PHASE_GATES §4.5) ──
        InjectionCase("FW-1", "§4.5", "REAL_TARGET 모드로 수집기 기동", B, _c_real_target),
        InjectionCase("FW-2", "§4.5", "문자열 'REAL_TARGET' 우회", B, _c_real_target_string),
        InjectionCase("FW-3", "§4.5", "REAL_TARGET 로 실제 URL 항해", B, _c_real_target_navigation),
        InjectionCase("FW-4", "§4.5", "FIXTURE 모드에서 https 항해", B, _c_http_in_fixture_mode),
        InjectionCase("FW-5", "§4.5", "SHADOW_DRY_RUN 이 항해 시도", B, _c_dry_run_navigation),
        InjectionCase("FW-6", "S-3", "알 수 없는 execution_mode", B, _c_unknown_mode),
        InjectionCase(
            "FW-7", "§4.5", "FIXTURE 모드는 허용된다(과탐 회귀)", P, _c_fixture_mode_allowed
        ),
        # ── 02 §14 핵심 ──
        InjectionCase("C-1", "02 §14", "observation id duplicate", B, _c_duplicate_observation),
        InjectionCase("C-2", "07 §4", "manifest missing", B, _c_missing_manifest),
        InjectionCase("C-3", "02 §14", "evidence file swap", B, _c_evidence_swap),
        InjectionCase("C-4", "02 §12", "evidence overwrite", B, _c_overwrite),
        InjectionCase("C-5", "02 §14", "symlink escape", B, _c_symlink_escape),
        InjectionCase("C-6", "07 §3", "절대경로 relpath", B, _c_absolute_relpath),
        InjectionCase("C-7", "07 §3", "'..' relpath", B, _c_parent_relpath),
        InjectionCase("C-8", "02 §12", "봉인된 run 재봉인", B, _c_reseal),
        InjectionCase("C-9", "00 §9", "AI disagreement", B, _c_ai_disagreement),
        InjectionCase("C-10", "A-1 · X-6", "HUMAN_FINAL 5건 초과", B, _c_human_budget),
        InjectionCase("C-11", "02 §14", "banner mutation", B, _c_banner_mutation),
        InjectionCase(
            "C-12",
            "07 §4",
            "구조검증을 VERIFIED 로 세지 않음",
            B,
            _c_manifest_only_mode_not_verified,
        ),
        # ── A2 §1.11 V-a ~ V-g ──
        InjectionCase(
            "V-a", "X-1", "UNDETERMINED ∧ gap=1 → PASS", B, _v_undetermined_to(VerdictState.PASS)
        ),
        InjectionCase(
            "V-b", "X-1", "UNDETERMINED ∧ gap=0 → PASS", B, _v_undetermined_to(VerdictState.PASS)
        ),
        InjectionCase("V-c", "T-8 · A-2", "RESOLVED ∧ arbiter=PASS 전파", B, _v_c_resolved_pass),
        InjectionCase("V-d", "X-13", "UNDETERMINED → NA", B, _v_undetermined_to(VerdictState.NA)),
        InjectionCase(
            "V-e", "X-11", "UNDETERMINED → FAIL", B, _v_undetermined_to(VerdictState.FAIL)
        ),
        InjectionCase("V-f", "T-6 · X-15", "NA ∧ ABSTAIN → UNDETERMINED", B, _v_f_na_abstain),
        InjectionCase("V-g", "X-14", "결과를 보고 정본 run 선택", B, _v_g_optional_stopping),
        # ── A2 §6.3.1 I-1 ~ I-29 ──
        InjectionCase("I-1", "E-5", "금융 로그인 gate 를 AUTH_GATE_REACHED 로", B, _i1),
        InjectionCase("I-2", "E-6", "QUERY 에 ENDPOINT_VIA_AUTH_GATE", B, _i2),
        InjectionCase("I-3", "E-6a", "커뮤니티 본인인증 gate 를 endpoint 로", B, _i3),
        InjectionCase("I-4", "E-6a", "커뮤니티 본인인증 → AUTH_GATE_REACHED (통과해야)", P, _i4),
        InjectionCase("I-5", "E-7", "gate 관측 이후 activation", B, _i5),
        InjectionCase("I-6", "E-8", "auth gate 를 endpoint_status 단독 집계", B, _i6),
        InjectionCase("I-7", "E-9", "endpoint gate 를 before 로 계수", B, _i7),
        InjectionCase("I-8", "E-9", "auth_gate_before_endpoint 를 NULL 로", B, _i8),
        InjectionCase("I-9", "E-10", "두 archetype MPFED 합산만 산출", B, _i9),
        InjectionCase("I-10", "A-2", "triage label 에 PASS/FAIL", B, _i10),
        InjectionCase("I-11", "W-1 · T-11", "관측이 Frame 컬럼 in-place 수정", B, _i11),
        InjectionCase("I-12", "W-2", "supersede 를 범위 안으로 되돌림", B, _i12),
        InjectionCase("I-13", "W-3", "eligibility_reversal_rate 미보고", B, _i13),
        InjectionCase("I-14", "M-3", "NOT_ELIGIBLE_AT_COLLECTION 기록 (통과해야)", P, _i14),
        InjectionCase("I-15", "M-4", "증거 없이 NOT_ELIGIBLE 기록", B, _i15),
        InjectionCase("I-16", "M-5 · X-12", "FAILED_* → NOT_ELIGIBLE 재분류", B, _i16),
        InjectionCase("I-17", "N-6", "NOT_ELIGIBLE 을 FAILED_% 계열로", B, _i17),
        InjectionCase("I-18", "N-7", "UNDETERMINED 행 삭제", B, _i18),
        InjectionCase("I-19", "B-2", "abstention rate 합산", B, _i19),
        InjectionCase("I-20", "T-7 vs T-8", "UNDETERMINED 에 T-7 적용", B, _i20),
        InjectionCase("I-21", "T-9", "Phase 5 에 PENDING 잔여", B, _i21),
        InjectionCase("I-22", "T-10 · X-10", "verdict_state 를 고쳐 씀", B, _i22),
        InjectionCase("I-23", "X-9", "evidence_gap 을 전이 허가 조건으로", B, _i23),
        InjectionCase("I-24", "RC-1", "상한 초과 run 을 정본으로", B, _i24),
        InjectionCase("I-25", "RC-2", "preregistered_at >= collection_started_at", B, _i25),
        InjectionCase("I-25b", "RC-2", "expected_evidence 없는 사전선언", B, _i25b),
        InjectionCase("I-25c", "RC-2 · X-14", "manifest 를 expected_evidence 로", B, _i25c),
        InjectionCase("I-26", "RC-2 · X-14", "판정 결과를 중단 조건으로", B, _i26),
        InjectionCase("I-27", "RC-3", "expected_evidence 미산출 run 을 정본으로", B, _i27),
        InjectionCase("I-28", "RC-4", "미선언 run 을 분자·분모에", B, _i28),
        InjectionCase("I-28b", "RC-3", "criterion 마다 다른 run 을 섞음", B, _i28b),
        InjectionCase("I-29", "RC-5", "재수집 전후 병기 누락", B, _i29),
        # ── Q-9: gate 종류 판별 ──
        InjectionCase("Q9-1", "E-6a", "로그인 fixture → LOGIN 판별 (통과해야)", P, _q9_1),
        InjectionCase("Q9-2", "E-6a", "본인인증 fixture → IDENTITY 판별 (통과해야)", P, _q9_2),
        InjectionCase("Q9-3", "E-6a", "본인인증 gate 를 LOGIN 으로 오판 기록", B, _q9_3),
        InjectionCase("Q9-4", "E-6a", "오판의 결과 — 없어야 할 ENDPOINT_VIA_AUTH_GATE", B, _q9_4),
        InjectionCase("Q9-5", "abstain", "모호한 gate 는 강제분류되지 않는다 (통과해야)", P, _q9_5),
        InjectionCase("Q9-6", "abstain", "판별 불가 gate 를 LOGIN 으로 기록", B, _q9_6),
        InjectionCase("Q9-7", "A2 §1.5.1a", "판별 불가 gate 미승격 (통과해야)", P, _q9_7),
    ]


def run_case(case: InjectionCase, workdir: Path) -> CaseResult:
    """한 케이스를 태운다. 기대와 실제가 어긋나면 `outcome != AS_EXPECTED` 다."""
    workdir.mkdir(parents=True, exist_ok=True)
    # EvidenceError 는 Duplicate/Overwrite/SymlinkEscape/RunSealed/Preregistration 의 상위 클래스다.
    # 하위 클래스를 함께 적는 것은 "무엇이 잡히는지" 를 읽는 사람에게 보이기 위함이다.
    guard_errors = (
        RealTargetBlockedError,
        NavigationBlockedError,
        UnknownExecutionModeError,
        DuplicateObservationError,
        EvidenceOverwriteError,
        SymlinkEscapeError,
        RunSealedError,
        EvidenceError,
        MissingRunManifestError,
        PreregistrationError,
        LaunderingBlocked,
        TransitionError,
        DepthRuleError,
        ClosedVocabularyError,
        reporting.ReportingError,
        GateEvidenceError,
        _Detected,
    )
    try:
        case.run(workdir)
    except guard_errors as exc:
        detail = f"{type(exc).__name__}: {exc}"
        outcome = "AS_EXPECTED" if case.expectation is Expectation.BLOCKED else "OVER_BLOCKED"
        return CaseResult(case.case_id, case.rule, case.expectation.value, outcome, detail)
    except AssertionError as exc:
        return CaseResult(
            case.case_id,
            case.rule,
            case.expectation.value,
            "GUARD_FAILED",
            f"AssertionError: {exc}",
        )
    except Exception as exc:
        return CaseResult(
            case.case_id,
            case.rule,
            case.expectation.value,
            "UNEXPECTED_ERROR",
            f"{type(exc).__name__}: {exc}",
        )
    outcome = "AS_EXPECTED" if case.expectation is Expectation.MUST_PASS else "NOT_BLOCKED"
    return CaseResult(case.case_id, case.rule, case.expectation.value, outcome, "예외 없이 통과")


def run_all(workroot: Path) -> dict[str, Any]:
    """전건을 태우고 보고서를 만든다. `02 §14` 가 요구한 "실제로 차단하는지"의 증거다."""
    from .provenance import ShadowProvenance

    results = [run_case(case, Path(workroot) / case.case_id) for case in registry()]
    blocked = [r for r in results if r.expectation == Expectation.BLOCKED.value]
    must_pass = [r for r in results if r.expectation == Expectation.MUST_PASS.value]
    return {
        "provenance": ShadowProvenance().as_dict(),
        "total": len(results),
        "blocked_cases": len(blocked),
        "must_pass_cases": len(must_pass),
        "as_expected": sum(1 for r in results if r.ok),
        "failures": [r.__dict__ for r in results if not r.ok],
        "results": [r.__dict__ for r in results],
    }


def write_report(workroot: Path, out_path: Path) -> dict[str, Any]:
    report = run_all(workroot)
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    Path(out_path).write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return report
