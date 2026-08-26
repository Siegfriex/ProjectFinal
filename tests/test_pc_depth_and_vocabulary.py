"""P-C LANE C — Depth 산출 · gate 분기 · 상태값 어휘.

`A1 §1` · `§2` / `A2 §1.5` · `§1.5.1a` · `§1.11` · `§1.14`.

여기서 지키는 규범은 하나로 요약된다: **결측을 0으로 바꾸지 않는다.**
`MPFED` 를 예산 상한값 `8` 로 채우면 "이 서비스는 깊었다" 는 문장이 관측 없이 만들어진다.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
RESEARCH = REPO / "research" / "landing_accessibility"
sys.path.insert(0, str(RESEARCH / "src"))

from landing_accessibility.engine.depth import (  # noqa: E402
    ENDPOINT_GATE_KINDS,
    DepthRuleError,
    assert_detail_rollup,
    assert_gate_endpoint_allowed,
    assign_depth_segments,
    auth_gate_before_endpoint,
    auth_gate_observed,
    compute_depth,
    gate_outcome,
    gate_outcome_from_decision,
)
from landing_accessibility.engine.gate_classifier import (  # noqa: E402
    GateClassificationStatus,
    GateEvidenceError,
    GateSignals,
    assert_gate_kind_evidence,
    classify_gate_kind,
)
from landing_accessibility.engine.vocabulary import (  # noqa: E402
    DETAIL_ROLLUP,
    AreaSignalStatus,
    ClosedVocabularyError,
    DepthSegment,
    EndpointStatus,
    EndpointStatusDetail,
    GateKind,
    InteractionArchetype,
    InterruptLabel,
    MeasurementStatus,
    is_measurement_failed,
    validate,
)

A = InteractionArchetype


# ── 어휘 (A2 §1) ─────────────────────────────────────────────────────────────
def test_endpoint_status_is_exactly_the_frozen_seven() -> None:
    assert {e.value for e in EndpointStatus} == {
        "FUNCTION_ENDPOINT_REACHED",
        "AUTH_GATE_REACHED",
        "PAYMENT_GATE_REACHED",
        "PERSONAL_DATA_REQUIRED",
        "CAPTCHA",
        "BLOCKED",
        "UNRESOLVED",
    }


def test_interrupt_labels_are_the_ten_from_ssot_section_8() -> None:
    assert len(set(InterruptLabel)) == 10


def test_measurement_status_family_boundary_excludes_not_eligible() -> None:
    """규칙 N-6 — 적격성 반증은 수집 실패가 아니다."""
    assert is_measurement_failed(MeasurementStatus.FAILED_ACCESS_BLOCKED) is True
    assert is_measurement_failed(MeasurementStatus.NOT_ELIGIBLE_AT_COLLECTION) is False


def test_closed_vocabulary_rejects_unknown_values() -> None:
    with pytest.raises(ClosedVocabularyError):
        validate("endpoint_status", "UNRESOLVED_DEPTH_BUDGET_EXCEEDED")
    with pytest.raises(ClosedVocabularyError):
        validate("final_label", "PAYWALL")


def test_state_columns_reject_null() -> None:
    """규칙 N-1 — 상태 컬럼을 `NULL` 로 비워두지 않는다."""
    with pytest.raises(ClosedVocabularyError):
        validate("endpoint_status", None)
    assert validate("endpoint_status_detail", None, allow_null=True) is None


def test_detail_rollup_is_single_valued() -> None:
    assert DETAIL_ROLLUP[EndpointStatusDetail.UNRESOLVED_NO_SIGNAL] is EndpointStatus.UNRESOLVED
    assert (
        DETAIL_ROLLUP[EndpointStatusDetail.ENDPOINT_VIA_AUTH_GATE]
        is EndpointStatus.FUNCTION_ENDPOINT_REACHED
    )


# ── gate 분기 (A2 §1.5.1a 규칙 E-5 · E-6 · E-6a) ─────────────────────────────
def test_only_two_archetypes_have_gate_endpoints_and_with_different_kinds() -> None:
    """`00 §3` 원문: 금융은 `로그인/인증`, 커뮤니티는 `로그인` 뿐이다."""
    assert ENDPOINT_GATE_KINDS[A.FINANCIAL_ACTION_ENTRY] == {
        GateKind.LOGIN,
        GateKind.IDENTITY_VERIFICATION,
    }
    assert ENDPOINT_GATE_KINDS[A.COMMUNICATION_ENTRY] == {GateKind.LOGIN}
    for archetype in (A.QUERY, A.CONTENT_OPEN, A.ITEM_DETAIL, A.PLACE_LOOKUP, A.UTILITY_ENTRY):
        assert ENDPOINT_GATE_KINDS[archetype] == frozenset()


@pytest.mark.parametrize(
    ("archetype", "kind", "status", "detail"),
    [
        (
            A.FINANCIAL_ACTION_ENTRY,
            GateKind.LOGIN,
            "FUNCTION_ENDPOINT_REACHED",
            "ENDPOINT_VIA_AUTH_GATE",
        ),
        (
            A.FINANCIAL_ACTION_ENTRY,
            GateKind.IDENTITY_VERIFICATION,
            "FUNCTION_ENDPOINT_REACHED",
            "ENDPOINT_VIA_AUTH_GATE",
        ),
        (
            A.COMMUNICATION_ENTRY,
            GateKind.LOGIN,
            "FUNCTION_ENDPOINT_REACHED",
            "ENDPOINT_VIA_AUTH_GATE",
        ),
        # 규칙 E-6a — 커뮤니티의 본인인증 gate 는 endpoint 가 **아니다** (주입 I-4 가 통과하는 자리)
        (A.COMMUNICATION_ENTRY, GateKind.IDENTITY_VERIFICATION, "AUTH_GATE_REACHED", None),
        (A.QUERY, GateKind.LOGIN, "AUTH_GATE_REACHED", None),
        (A.QUERY, GateKind.IDENTITY_VERIFICATION, "AUTH_GATE_REACHED", None),
        (A.FINANCIAL_ACTION_ENTRY, GateKind.PAYMENT, "PAYMENT_GATE_REACHED", None),
        (A.COMMUNICATION_ENTRY, GateKind.CAPTCHA, "CAPTCHA", None),
    ],
)
def test_gate_outcome_matches_a2_table(
    archetype: InteractionArchetype, kind: GateKind, status: str, detail: str | None
) -> None:
    got_status, got_detail = gate_outcome(archetype, kind)
    assert got_status.value == status
    assert (got_detail.value if got_detail else None) == detail


def test_no_gate_kind_is_left_unmapped() -> None:
    """규칙 S-3 이 발화할 무주지가 없어야 한다 — 전 archetype  x  전 gate 종류를 훑는다."""
    for archetype in A:
        for kind in GateKind:
            status, detail = gate_outcome(archetype, kind)
            assert status in set(EndpointStatus)
            assert_detail_rollup(status, detail, archetype)


def test_promoting_a_gate_the_archetype_does_not_own_is_blocked() -> None:
    with pytest.raises(DepthRuleError):  # 주입 I-3
        assert_gate_endpoint_allowed(A.COMMUNICATION_ENTRY, GateKind.IDENTITY_VERIFICATION)
    with pytest.raises(DepthRuleError):  # 주입 I-2
        assert_detail_rollup(
            EndpointStatus.FUNCTION_ENDPOINT_REACHED,
            EndpointStatusDetail.ENDPOINT_VIA_AUTH_GATE,
            A.QUERY,
        )


# ── gate 종류 판별 (Q-9) ─────────────────────────────────────────────────────
LOGIN_SIGNALS = GateSignals(
    text="로그인 아이디 비밀번호 아이디 찾기 회원가입",
    password_input_count=1,
    username_autocomplete_count=1,
)
IDENTITY_SIGNALS = GateSignals(
    text="휴대폰 본인확인 PASS 앱 인증 카카오 인증 통신사 SKT KT LG U+ 알뜰폰 생년월일 인증번호",
    tel_autocomplete_count=1,
    identity_number_input_count=2,
    otp_input_count=1,
    carrier_option_count=4,
    simple_auth_provider_count=2,
)
AMBIGUOUS_SIGNALS = GateSignals(
    text="로그인 또는 본인확인으로 계속하기 아이디 비밀번호 통신사 SKT KT 인증번호",
    password_input_count=1,
    username_autocomplete_count=1,
    tel_autocomplete_count=1,
    otp_input_count=1,
    carrier_option_count=2,
)


def test_login_and_identity_gates_are_separable_by_observation_alone() -> None:
    """판별기는 fixture 의 `data-gate-kind` 를 읽지 않는다 — 신호만으로 갈라야 한다."""
    login = classify_gate_kind(LOGIN_SIGNALS)
    assert login.resolved and login.gate_kind is GateKind.LOGIN
    assert login.login_basis

    identity = classify_gate_kind(IDENTITY_SIGNALS)
    assert identity.resolved and identity.gate_kind is GateKind.IDENTITY_VERIFICATION
    assert identity.identity_basis


def test_ambiguous_gate_is_not_force_classified() -> None:
    """이 연구에서 강제분류는 금지다 — abstain 경로가 실제로 존재해야 한다."""
    d = classify_gate_kind(AMBIGUOUS_SIGNALS)
    assert d.status is GateClassificationStatus.UNDETERMINED
    assert d.gate_kind is None
    assert d.login_basis and d.identity_basis  # 판별 불가의 근거가 남는다


def test_undetermined_gate_is_never_promoted_to_endpoint() -> None:
    """`A2 §1.5.1a` — 모호할 때 endpoint 로 올리는 기본값을 두지 않는다."""
    d = classify_gate_kind(AMBIGUOUS_SIGNALS)
    for archetype in A:
        status, detail = gate_outcome_from_decision(archetype, d)
        assert status is EndpointStatus.AUTH_GATE_REACHED
        assert detail is None


def test_misclassifying_an_identity_gate_as_login_is_caught() -> None:
    """Q-9 오판 케이스 — 규칙 E-6a 만으로는 조용히 통과한다."""
    assert_gate_kind_evidence(GateKind.IDENTITY_VERIFICATION, IDENTITY_SIGNALS)
    with pytest.raises(GateEvidenceError):
        assert_gate_kind_evidence(GateKind.LOGIN, IDENTITY_SIGNALS)
    with pytest.raises(GateEvidenceError):
        assert_gate_kind_evidence(GateKind.LOGIN, AMBIGUOUS_SIGNALS)


def test_misclassification_would_flip_endpoint_reached() -> None:
    """오판이 왜 위험한지를 값으로 고정한다."""
    wrong, wrong_detail = gate_outcome(A.COMMUNICATION_ENTRY, GateKind.LOGIN)
    right, right_detail = gate_outcome(A.COMMUNICATION_ENTRY, GateKind.IDENTITY_VERIFICATION)
    assert wrong_detail is EndpointStatusDetail.ENDPOINT_VIA_AUTH_GATE
    assert wrong is EndpointStatus.FUNCTION_ENDPOINT_REACHED
    assert right is EndpointStatus.AUTH_GATE_REACHED and right_detail is None


# ── Depth 산출 (A1 §1.3 ~ §1.5) ──────────────────────────────────────────────
def _depth(**kw: object):
    base: dict = {
        "archetype": A.CONTENT_OPEN,
        "area_step_index": 0,
        "endpoint_step_index": 0,
        "endpoint_status": EndpointStatus.FUNCTION_ENDPOINT_REACHED,
    }
    return compute_depth(**{**base, **kw})  # type: ignore[arg-type]


def test_landing_is_both_region_and_endpoint() -> None:
    d = _depth(area_step_index=0, endpoint_step_index=0)
    assert (d.ned, d.ied, d.mpfed) == (0, 0, 0)
    assert d.area_signal_status is AreaSignalStatus.OBSERVED


def test_ned_ied_split() -> None:
    d = _depth(area_step_index=2, endpoint_step_index=3)
    assert (d.ned, d.ied, d.mpfed) == (2, 1, 3)
    assert d.mpfed == d.ned + d.ied  # `00 §7` 항등식


def test_endpoint_before_region_is_retroactively_attributed() -> None:
    d = _depth(area_step_index=None, endpoint_step_index=2)
    assert (d.ned, d.ied, d.mpfed) == (2, 0, 2)
    assert d.area_signal_status is AreaSignalStatus.INFERRED_FROM_ENDPOINT


def test_budget_exhaustion_yields_null_not_the_budget_value() -> None:
    """금지 전이 X-5 — `MPFED = 8` 이 아니라 `NULL` 이다."""
    d = compute_depth(
        archetype=A.UTILITY_ENTRY,
        area_step_index=None,
        endpoint_step_index=None,
        endpoint_status=EndpointStatus.UNRESOLVED,
        endpoint_status_detail=EndpointStatusDetail.UNRESOLVED_DEPTH_BUDGET_EXCEEDED,
    )
    assert (d.ned, d.ied, d.mpfed) == (None, None, None)
    assert d.endpoint_reached == 0
    assert d.area_signal_status is AreaSignalStatus.NOT_OBSERVED


def test_region_seen_but_endpoint_not_keeps_ned_and_nulls_the_rest() -> None:
    d = compute_depth(
        archetype=A.QUERY,
        area_step_index=1,
        endpoint_step_index=None,
        endpoint_status=EndpointStatus.AUTH_GATE_REACHED,
    )
    assert (d.ned, d.ied, d.mpfed) == (1, None, None)
    assert d.area_signal_status is AreaSignalStatus.OBSERVED


def test_not_observed_region_is_distinct_from_ned_zero() -> None:
    """규칙 N-3 — 관측된 0 과 미관측은 다른 사실이다."""
    zero = _depth(area_step_index=0, endpoint_step_index=0)
    null = compute_depth(
        archetype=A.QUERY,
        area_step_index=None,
        endpoint_step_index=None,
        endpoint_status=EndpointStatus.UNRESOLVED,
    )
    assert zero.ned == 0
    assert null.ned is None


def test_endpoint_reached_without_endpoint_step_is_a_contradiction() -> None:
    with pytest.raises(DepthRuleError):
        _depth(endpoint_step_index=None)


# ── step 귀속 (A1 §1.7) ──────────────────────────────────────────────────────
def test_segments_split_at_the_region_boundary() -> None:
    d = _depth(area_step_index=2, endpoint_step_index=3)
    assert assign_depth_segments(3, d) == [
        DepthSegment.NED,
        DepthSegment.NED,
        DepthSegment.IED,
    ]


def test_all_steps_are_unassigned_when_region_was_never_seen() -> None:
    d = compute_depth(
        archetype=A.QUERY,
        area_step_index=None,
        endpoint_step_index=None,
        endpoint_status=EndpointStatus.UNRESOLVED,
    )
    assert assign_depth_segments(2, d) == [DepthSegment.UNASSIGNED] * 2


def test_activation_after_endpoint_is_a_gate_pass_violation() -> None:
    """규칙 E-7 · `02 §7` 즉시종료 (주입 I-5)."""
    d = _depth(area_step_index=1, endpoint_step_index=2)
    with pytest.raises(DepthRuleError):
        assign_depth_segments(4, d)


# ── auth gate 계수 (규칙 E-8 · E-9) ──────────────────────────────────────────
def test_the_gate_that_realised_the_endpoint_is_not_counted_as_before() -> None:
    assert (
        auth_gate_before_endpoint(
            auth_gate_detected_per_step=[0, 1],
            endpoint_status_detail=EndpointStatusDetail.ENDPOINT_VIA_AUTH_GATE,
        )
        == 0
    )
    assert (
        auth_gate_before_endpoint(
            auth_gate_detected_per_step=[1, 0, 1],
            endpoint_status_detail=EndpointStatusDetail.ENDPOINT_VIA_AUTH_GATE,
        )
        == 1
    )


def test_auth_gate_observed_is_the_two_term_union() -> None:
    """규칙 E-8 — `endpoint_status` 단독 집계는 두 archetype 에서 과소집계된다."""
    assert (
        auth_gate_observed(
            auth_gate_before_endpoint_value=0,
            endpoint_status_detail=EndpointStatusDetail.ENDPOINT_VIA_AUTH_GATE,
        )
        == 1
    )
    assert auth_gate_observed(auth_gate_before_endpoint_value=1, endpoint_status_detail=None) == 1
    assert auth_gate_observed(auth_gate_before_endpoint_value=0, endpoint_status_detail=None) == 0
