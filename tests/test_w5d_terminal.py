"""W5D — terminal 8종 분류 검정.

지키려는 명제:

0. 층 한정 (`R6-Q8`) — `AUTH_GATE`/`ABSTAIN` 은 여러 층에 같은 문자열로 존재하므로
   항상 `terminal=` / `endpoint_status=` / `action_token=` 으로 층을 명시한다.
1. terminal 8종은 각각 별개다. **하나의 `FAILED` 로 합치지 않는다.** 8종 전부가 실제로
   산출되고, 서로 다른 입력에서 나온다.
2. 인접 terminal 과 갈리는 대조군이 있다 — 특히 `EVIDENCE_DEFECT`(우리 도구의 결함)와
   `PUBLIC_WEB_UNOBSERVABLE`(사이트의 성질).
3. 동시에 참인 신호를 조용히 버리지 않는다 (`competing_signals`).
4. 산출 불능은 `None` + `UNDETERMINED` 다. `FAILED` 로 바꾸지 않는다.
5. CAPTCHA 는 존재 관측과 terminal 분류까지다 — 해결·우회 경로가 없다.
6. 성공/실패 해석은 하지 않는다 (`R2`) — family 를 아는 상위 층의 일이다.
"""

from __future__ import annotations

import dataclasses
import inspect
import json
import re
import sys
from pathlib import Path
from typing import Any

import pytest

REPO = Path(__file__).resolve().parents[1]
RESEARCH = REPO / "research" / "landing_accessibility"
sys.path.insert(0, str(RESEARCH / "src"))

from landing_accessibility.v3_runner import terminal as terminal_module  # noqa: E402
from landing_accessibility.v3_runner.terminal import (  # noqa: E402
    ALLOWED_ENDPOINT_STATUS_REASONS,
    TERMINAL_PRECEDENCE,
    TERMINAL_TO_ENDPOINT_STATUS,
    AuthGateStage,
    EndpointStatus,
    TerminalCombinationError,
    TerminalKind,
    TerminalOutcome,
    TerminalReason,
    TerminalReasonNoteError,
    TerminalResolution,
    TerminalSignals,
    classify_terminal,
    validate_status_reason,
)

FIXTURE = RESEARCH / "fixtures" / "w5d" / "terminal_cases.json"


def _load() -> dict[str, Any]:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def _signals(raw: dict[str, Any]) -> TerminalSignals:
    kwargs = dict(raw)
    if "auth_gate_stage" in kwargs:
        kwargs["auth_gate_stage"] = AuthGateStage(kwargs["auth_gate_stage"])
    return TerminalSignals(**kwargs)


@pytest.fixture(scope="module")
def cases() -> dict[str, dict[str, Any]]:
    return {c["case_id"]: c for c in _load()["cases"]}


def _case_ids() -> list[str]:
    return [c["case_id"] for c in _load()["cases"]]


# ── fixture 전건 회귀 ────────────────────────────────────────────────────────
@pytest.mark.parametrize("case_id", _case_ids())
def test_fixture_case_matches_expected_outcome(
    case_id: str, cases: dict[str, dict[str, Any]]
) -> None:
    case = cases[case_id]
    got = classify_terminal(_signals(case["signals"]))
    expect = case["expect"]

    assert (got.terminal.value if got.terminal else None) == expect["terminal"], (
        f"{case_id}: terminal"
    )
    assert (got.endpoint_status.value if got.endpoint_status else None) == expect[
        "endpoint_status"
    ], f"{case_id}: endpoint_status"
    assert (got.terminal_reason.value if got.terminal_reason else None) == expect[
        "terminal_reason"
    ], f"{case_id}: terminal_reason"
    assert got.resolution.value == expect["resolution"], f"{case_id}: resolution"
    assert got.auth_gate_stage.value == expect["auth_gate_stage"], f"{case_id}: auth_gate_stage"
    assert [k.value for k in got.competing_signals] == expect["competing_signals"], (
        f"{case_id}: competing_signals"
    )


# ── 1. 8종 전부가 별개로 산출된다 ────────────────────────────────────────────
def test_all_eight_terminals_are_produced_by_the_fixture_suite(
    cases: dict[str, dict[str, Any]],
) -> None:
    produced = {classify_terminal(_signals(c["signals"])).terminal for c in cases.values()}
    produced.discard(None)
    assert produced == set(TerminalKind), f"산출되지 않은 terminal: {set(TerminalKind) - produced}"


def test_no_single_failed_bucket_exists() -> None:
    """`FAILED` 라는 값이 어휘에 없다 — 8종을 합칠 자리를 만들지 않는다."""
    assert "FAILED" not in {k.value for k in TerminalKind}
    assert "FAILED" not in {s.value for s in EndpointStatus}
    assert len(set(TerminalKind)) == 8


def test_terminals_are_not_collapsed_by_endpoint_status(
    cases: dict[str, dict[str, Any]],
) -> None:
    """terminal → endpoint_status 는 다대일이다. 그래서 두 축을 **둘 다** 보존한다.

    `endpoint_status` 만 남기면 `TIMEOUT` 과 `EVIDENCE_DEFECT` 가, `SAFETY_STOP` 과
    `NO_SAFE_ROUTE_FOUND` 가 각각 구분 불가능해진다.
    """
    assert (
        TERMINAL_TO_ENDPOINT_STATUS[TerminalKind.TIMEOUT]
        == TERMINAL_TO_ENDPOINT_STATUS[TerminalKind.EVIDENCE_DEFECT]
    )
    assert (
        TERMINAL_TO_ENDPOINT_STATUS[TerminalKind.SAFETY_STOP]
        == TERMINAL_TO_ENDPOINT_STATUS[TerminalKind.NO_SAFE_ROUTE_FOUND]
    )

    timeout = classify_terminal(_signals(cases["timeout"]["signals"]))
    defect = classify_terminal(_signals(cases["evidence_defect"]["signals"]))
    assert timeout.endpoint_status == defect.endpoint_status
    assert timeout.terminal is not defect.terminal, "endpoint_status 가 같아도 terminal 은 다르다"

    safety = classify_terminal(_signals(cases["safety_stop"]["signals"]))
    noroute = classify_terminal(_signals(cases["no_safe_route_found"]["signals"]))
    assert safety.endpoint_status == noroute.endpoint_status
    assert safety.terminal is not noroute.terminal


def test_endpoint_status_vocabulary_is_the_04_section4_set() -> None:
    """`04 §4` 어휘 7종. 값을 늘리지 않는다."""
    assert {s.value for s in EndpointStatus} == {
        "REACHED",
        "AUTH_GATE",
        "PUBLIC_WEB_UNOBSERVABLE",
        "APP_REQUIRED",
        "EVIDENCE_DEFECT",
        "BLOCKED",
        "ABSTAIN",
    }
    assert set(TERMINAL_TO_ENDPOINT_STATUS) == set(TerminalKind), "매핑에 빠진 terminal 이 없다"
    assert set(TERMINAL_PRECEDENCE) == set(TerminalKind), "우선순위에 빠진 terminal 이 없다"
    assert len(TERMINAL_PRECEDENCE) == len(set(TERMINAL_PRECEDENCE))


# ── 2. 인접 terminal 대조군 ──────────────────────────────────────────────────
def test_evidence_defect_is_our_fault_and_unobservable_is_the_site(
    cases: dict[str, dict[str, Any]],
) -> None:
    """가장 혼동하기 쉬운 한 쌍.

    같은 "endpoint 에 못 갔다"라도, 증거가 깨진 것(우리 결함, 재수집 대상)과 공개 모바일웹
    에서 관측되지 않는 것(사이트의 성질, 분석 대상)은 다른 사실이다. 둘이 동시에 참이면
    증거 결함이 이긴다 — 증거가 깨졌으면 사이트에 대해 아무것도 주장할 수 없기 때문이다.
    """
    defect = classify_terminal(_signals(cases["evidence_defect"]["signals"]))
    site = classify_terminal(_signals(cases["public_web_unobservable"]["signals"]))

    assert defect.terminal is TerminalKind.EVIDENCE_DEFECT
    assert defect.endpoint_status is EndpointStatus.EVIDENCE_DEFECT
    assert defect.evidence_defect_reason == "dom_capture_empty"

    assert site.terminal is TerminalKind.PUBLIC_WEB_UNOBSERVABLE
    assert site.endpoint_status is EndpointStatus.PUBLIC_WEB_UNOBSERVABLE
    assert site.evidence_defect_reason is None

    both = classify_terminal(
        _signals(cases["control_evidence_defect_beats_public_web_unobservable"]["signals"])
    )
    assert both.terminal is TerminalKind.EVIDENCE_DEFECT
    assert TerminalKind.PUBLIC_WEB_UNOBSERVABLE in both.competing_signals


def test_unobserved_evidence_completeness_is_not_a_defect_claim() -> None:
    """`evidence_complete=None` 은 미관측이다. 우리 결함이라고 단정하는 것도 주장이다."""
    got = classify_terminal(TerminalSignals(evidence_complete=None))
    assert got.terminal is None
    assert got.resolution is TerminalResolution.UNDETERMINED
    assert "evidence_complete_unobserved" in got.notes


def test_app_required_is_not_app_install_prompt(cases: dict[str, dict[str, Any]]) -> None:
    """채널이 과업을 안 싣는 것과 설치 배너가 뜬 것은 다르다. 후자는 obstruction 이다."""
    required = classify_terminal(_signals(cases["app_required"]["signals"]))
    prompt = classify_terminal(
        _signals(cases["control_app_install_prompt_is_not_app_required"]["signals"])
    )
    assert required.terminal is TerminalKind.APP_REQUIRED
    assert prompt.terminal is None
    assert prompt.endpoint_status is EndpointStatus.REACHED


def test_app_required_and_public_web_unobservable_stay_distinct(
    cases: dict[str, dict[str, Any]],
) -> None:
    got = classify_terminal(
        _signals(cases["control_app_required_beats_public_web_unobservable"]["signals"])
    )
    assert got.terminal is TerminalKind.APP_REQUIRED
    assert got.competing_signals == (TerminalKind.PUBLIC_WEB_UNOBSERVABLE,)


def test_generic_login_control_alone_is_not_terminal_auth_gate(
    cases: dict[str, dict[str, Any]],
) -> None:
    """`03 §7` — generic login 버튼 존재만으로 중단하지 않는다. `terminal=AUTH_GATE` 가 아니다."""
    gate = classify_terminal(_signals(cases["auth_gate"]["signals"]))
    decoy = classify_terminal(
        _signals(cases["control_generic_login_control_is_not_auth_gate"]["signals"])
    )
    assert gate.terminal is TerminalKind.AUTH_GATE
    assert decoy.terminal is None
    assert decoy.endpoint_status is EndpointStatus.REACHED

    # 필드를 단독으로 켜도 terminal 이 되지 않는다.
    lone = classify_terminal(TerminalSignals(generic_login_control_present=True))
    assert lone.terminal is None
    assert lone.resolution is TerminalResolution.UNDETERMINED


def test_auth_gate_stage_is_a_separate_axis(cases: dict[str, dict[str, Any]]) -> None:
    """auth 를 만난 위치는 terminal 여부와 별개로 보존된다."""
    blocked = classify_terminal(_signals(cases["control_waf_beats_auth_gate"]["signals"]))
    assert blocked.terminal is TerminalKind.WAF_OR_CHALLENGE
    assert blocked.auth_gate_stage is AuthGateStage.BEFORE_TASK_DISCOVERY
    assert TerminalKind.AUTH_GATE in blocked.competing_signals


def test_safety_stop_and_no_safe_route_are_distinct(
    cases: dict[str, dict[str, Any]],
) -> None:
    """우리가 멈춘 것과 못 찾은 것은 다르다. 둘 다 `ABSTAIN` 이지만 합치지 않는다."""
    got = classify_terminal(
        _signals(cases["control_safety_stop_and_no_safe_route_stay_distinct"]["signals"])
    )
    assert got.terminal is TerminalKind.SAFETY_STOP
    assert got.prohibited_action_kind == "CART_ADD"
    assert got.competing_signals == (TerminalKind.NO_SAFE_ROUTE_FOUND,)
    assert got.endpoint_status is EndpointStatus.ABSTAIN


def test_timeout_and_evidence_defect_are_distinct(cases: dict[str, dict[str, Any]]) -> None:
    got = classify_terminal(
        _signals(cases["control_timeout_and_evidence_defect_stay_distinct"]["signals"])
    )
    assert got.terminal is TerminalKind.EVIDENCE_DEFECT
    assert got.competing_signals == (TerminalKind.TIMEOUT,)
    assert got.evidence_defect_reason == "manifest_hash_mismatch"


# ── 3. 동시 신호를 버리지 않는다 ─────────────────────────────────────────────
def test_competing_signals_are_never_silently_dropped(
    cases: dict[str, dict[str, Any]],
) -> None:
    """우선순위에서 밀린 참인 조건은 전부 남는다."""
    signals = TerminalSignals(
        evidence_complete=False,
        run_timed_out=True,
        active_blocking_challenge=True,
        app_required=True,
        public_web_task_observable=False,
        auth_required_to_proceed=True,
        prohibited_action_required=True,
        permitted_routes_exhausted=True,
    )
    got = classify_terminal(signals)
    assert got.terminal is TerminalKind.EVIDENCE_DEFECT
    assert set(got.competing_signals) == set(TerminalKind) - {TerminalKind.EVIDENCE_DEFECT}
    # 순서는 우선순위 순으로 안정적이다 — 감사 가능해야 한다.
    assert list(got.competing_signals) == [
        k for k in TERMINAL_PRECEDENCE if k is not TerminalKind.EVIDENCE_DEFECT
    ]


def test_endpoint_reached_claim_is_not_trusted_under_evidence_defect() -> None:
    """증거가 깨졌으면 endpoint 도달 주장도 신뢰할 수 없다."""
    got = classify_terminal(TerminalSignals(evidence_complete=False, endpoint_reached=True))
    assert got.terminal is TerminalKind.EVIDENCE_DEFECT
    assert got.endpoint_status is EndpointStatus.EVIDENCE_DEFECT
    assert "endpoint_reached_claim_unverifiable" in got.notes


def test_endpoint_reached_signal_is_kept_alongside_terminal() -> None:
    got = classify_terminal(
        TerminalSignals(
            evidence_complete=True, endpoint_reached=True, auth_required_to_proceed=True
        )
    )
    assert got.terminal is TerminalKind.AUTH_GATE
    assert "endpoint_reached_signal_present_with_terminal" in got.notes
    # `R2` — 이 note 는 성공/실패 판정이 아니다. F1 처럼 계약이 auth gate 를 endpoint 로
    # 명시하는 family 에서는 상위 층이 이것을 도달로 셀 수 있다.
    assert not hasattr(got, "is_success")


# ── 4. 산출 불능 ─────────────────────────────────────────────────────────────
def test_no_signal_yields_undetermined_not_failed(cases: dict[str, dict[str, Any]]) -> None:
    got = classify_terminal(_signals(cases["undetermined_no_signal"]["signals"]))
    assert got.terminal is None
    assert got.resolution is TerminalResolution.UNDETERMINED
    assert got.endpoint_status is EndpointStatus.ABSTAIN


def test_terminal_none_has_two_distinguishable_meanings(
    cases: dict[str, dict[str, Any]],
) -> None:
    """`terminal=None` 은 두 가지 뜻이다. `resolution` 이 그 둘을 가른다."""
    reached = classify_terminal(_signals(cases["endpoint_reached"]["signals"]))
    unknown = classify_terminal(_signals(cases["undetermined_no_signal"]["signals"]))

    assert reached.terminal is unknown.terminal is None
    assert reached.resolution is TerminalResolution.NOT_TERMINAL_ENDPOINT_REACHED
    assert unknown.resolution is TerminalResolution.UNDETERMINED
    assert reached.endpoint_status is not unknown.endpoint_status


# ── 5. CAPTCHA — 관측까지다 ──────────────────────────────────────────────────
def test_inactive_captcha_is_observed_but_not_terminal(
    cases: dict[str, dict[str, Any]],
) -> None:
    """`03 §8` — active blocking challenge 만 terminal 이다. 존재만으로는 아니다."""
    active = classify_terminal(_signals(cases["waf_or_challenge"]["signals"]))
    hidden = classify_terminal(
        _signals(cases["control_inactive_captcha_is_not_terminal"]["signals"])
    )
    assert active.terminal is TerminalKind.WAF_OR_CHALLENGE
    assert active.challenge_kind == "RECAPTCHA_INTERSTITIAL"

    assert hidden.terminal is None
    # 관측 사실은 그대로 남는다 — terminal 이 아니라고 증거를 버리지 않는다.
    assert hidden.challenge_kind == "RECAPTCHA_HIDDEN_IFRAME"


def test_module_contains_no_challenge_solving_or_retry_path() -> None:
    """CAPTCHA 해결·우회 로직이 없음을 소스에서 확인한다 (`03 §8` 금지)."""
    source = inspect.getsource(terminal_module).lower()
    # 단어 경계로 본다 — `_resolve_reason` 의 "resolve" 를 "solve" 로 오탐하지 않는다.
    forbidden = (
        r"\bsolve\b",
        r"\bsolving\b",
        r"\bbypass",
        r"\baudio_challenge\b",
        r"\banticaptcha\b",
        r"2captcha",
        r"\bretry_challenge\b",
    )
    hits = [pat for pat in forbidden if re.search(pat, source)]
    assert not hits, f"금지된 challenge 처리 흔적: {hits}"


# ── R1 · R2 · R6-Q8 (A 사전등록 조작적 정의) ─────────────────────────────────
def test_defect_unobservable_and_abstain_are_three_distinct_outcomes(
    cases: dict[str, dict[str, Any]],
) -> None:
    """`R1` — "과업을 끝까지 못 갔다"로 보이는 세 결과가 서로 다른 층의 진술이다.

    - `endpoint_status=EVIDENCE_DEFECT` — 우리 도구. 증거가 깨져 아무 주장도 못 한다.
    - `endpoint_status=PUBLIC_WEB_UNOBSERVABLE` — 사이트. 그 과업 surface 가 공개
      모바일웹에 없다.
    - `endpoint_status=ABSTAIN` — 우리 판정의 유보. 증거는 있으나 경로가 불확정이다.

    셋을 하나로 합치면 재수집 대상과 분석 대상과 결측이 같은 값이 된다.
    """
    defect = classify_terminal(_signals(cases["evidence_defect"]["signals"]))
    site = classify_terminal(_signals(cases["public_web_unobservable"]["signals"]))
    abstain = classify_terminal(
        _signals(cases["task_comparability_concern_unperformable_abstains"]["signals"])
    )

    statuses = [defect.endpoint_status, site.endpoint_status, abstain.endpoint_status]
    assert len(set(statuses)) == 3, f"세 결과가 서로 다른 endpoint_status 여야 한다: {statuses}"
    assert defect.endpoint_status is EndpointStatus.EVIDENCE_DEFECT
    assert site.endpoint_status is EndpointStatus.PUBLIC_WEB_UNOBSERVABLE
    assert abstain.endpoint_status is EndpointStatus.ABSTAIN

    terminals = [defect.terminal, site.terminal, abstain.terminal]
    assert len(set(terminals)) == 3, f"terminal 층에서도 셋이 갈려야 한다: {terminals}"

    # 판정 유보 쪽은 증거가 온전하다 — 우리 결함이 아니다.
    assert abstain.evidence_defect_reason is None
    # 그리고 사이트 성질을 주장하지 않는다 — surface 부재는 관측되지 않았다.
    assert TerminalKind.PUBLIC_WEB_UNOBSERVABLE not in abstain.competing_signals


def test_task_comparability_concern_is_not_a_terminal() -> None:
    """`R1` — 교체 사유를 늘리지 않는다. comparability concern 은 finding 이지 terminal 이 아니다."""
    assert "TASK_COMPARABILITY_CONCERN" not in {k.value for k in TerminalKind}
    assert "TASK_COMPARABILITY_CONCERN" not in {s.value for s in EndpointStatus}
    # 입력에도 comparability 축이 없다 — 이 모듈이 그 판단을 하지 않는다는 뜻이다.
    fields = {f.name for f in dataclasses.fields(TerminalSignals)}
    assert not {f for f in fields if "comparab" in f}


def test_module_does_not_interpret_success_or_failure() -> None:
    """`R2` — terminal 은 관측값이다. 성공/미도달 해석은 family 를 아는 상위 층에 위임한다.

    그래서 입력에 `endpoint_contract` / `family_id` 가 없고, 산출에 `is_success` 류의
    파생 필드가 없다. F1 은 `endpoint_status=AUTH_GATE` 를 도달로 세고 F2~F5 는 미도달로
    세는데, 그 분기를 이 모듈이 하드코딩하면 family 마다 틀린 답을 낸다.
    """
    signal_fields = {f.name for f in dataclasses.fields(TerminalSignals)}
    outcome_fields = {f.name for f in dataclasses.fields(TerminalOutcome)}

    forbidden_inputs = {"endpoint_contract", "family_id", "task_family", "family"}
    assert not (signal_fields & forbidden_inputs), (
        f"family 의존 입력이 들어왔다: {signal_fields & forbidden_inputs}"
    )
    forbidden_outputs = {"is_success", "success", "endpoint_reached_effective", "flow_evaluable"}
    assert not (outcome_fields & forbidden_outputs), (
        f"성공/실패 파생 필드가 생겼다: {outcome_fields & forbidden_outputs}"
    )

    # 같은 auth gate 관측이 family 정보 없이 하나의 결과만 낸다 — 해석은 하류의 몫이다.
    got = classify_terminal(
        TerminalSignals(
            evidence_complete=True,
            auth_required_to_proceed=True,
            auth_gate_stage=AuthGateStage.AT_ENDPOINT,
        )
    )
    assert got.terminal is TerminalKind.AUTH_GATE
    assert got.endpoint_status is EndpointStatus.AUTH_GATE
    assert got.resolution is TerminalResolution.TERMINAL


def test_layer_qualification_is_documented_and_used() -> None:
    """`R6-Q8` — 두 다층 값은 층 한정 없이 산문에 등장하지 않는다."""
    doc = terminal_module.__doc__ or ""
    for qualified in ("terminal=AUTH_GATE", "endpoint_status=AUTH_GATE", "endpoint_status=ABSTAIN"):
        assert qualified in doc, f"층 한정 표기 누락: {qualified}"

    # terminal 층에는 ABSTAIN 이라는 값이 없다 — 그 자리는 세 값이 나눠 갖는다.
    assert "ABSTAIN" not in {k.value for k in TerminalKind}
    assert EndpointStatus.ABSTAIN in set(TERMINAL_TO_ENDPOINT_STATUS.values())


# ── R11 · terminal_reason 16값(R11 13 + Δ30 1 + Δ32 1 + Δ47 1)과 허용 조합표 ──
def test_all_sixteen_reasons_are_produced_by_the_fixture_suite(
    cases: dict[str, dict[str, Any]],
) -> None:
    """16값 각각이 실제 입력에서 나온다. 한 값이라도 도달 불가면 어휘가 죽은 것이다.

    `Δ10-R11` 13값 + `Δ30` `BUDGET_EXCEEDED` + `Δ32` `NO_TASK_CANDIDATE_FOUND`
    + `Δ47` `PATH_NOT_FOUND_BY_POLICY`."""
    produced = {classify_terminal(_signals(c["signals"])).terminal_reason for c in cases.values()}
    produced.discard(None)
    missing = set(TerminalReason) - produced
    assert not missing, f"산출되지 않은 terminal_reason: {sorted(r.value for r in missing)}"


def test_every_terminal_observation_carries_both_axes(
    cases: dict[str, dict[str, Any]],
) -> None:
    """`R11` — 모든 terminal 관측은 `endpoint_status` 와 `terminal_reason` 을 둘 다 갖는다."""
    for case_id, case in cases.items():
        got = classify_terminal(_signals(case["signals"]))
        if got.resolution is not TerminalResolution.TERMINAL:
            continue
        assert got.endpoint_status is not None, f"{case_id}: endpoint_status 누락"
        assert got.terminal_reason is not None, f"{case_id}: terminal_reason 누락"


def test_abstain_is_never_emitted_without_a_reason(cases: dict[str, dict[str, Any]]) -> None:
    """사유 없는 `endpoint_status=ABSTAIN` 이 나오지 않는다 — 그게 R11 이 막는 해상도 손실이다."""
    for case_id, case in cases.items():
        got = classify_terminal(_signals(case["signals"]))
        if got.endpoint_status is not EndpointStatus.ABSTAIN:
            continue
        assert got.terminal_reason is not None, f"{case_id}: ABSTAIN 인데 사유가 없다"
        if got.terminal_reason is TerminalReason.OTHER:
            assert (got.terminal_reason_note or "").strip(), f"{case_id}: OTHER 인데 note 가 없다"


def test_task_surface_absent_and_no_public_mobile_web_diverge(
    cases: dict[str, dict[str, Any]],
) -> None:
    """`R11` — `endpoint_status=PUBLIC_WEB_UNOBSERVABLE` 안에서 두 사유가 갈린다.

    채널이 없는 것과 채널은 있는데 그 과업이 없는 것은 다른 관측이다. 기록 해상도를 위한
    구분이며 **교체 사유는 여전히 `NO_PUBLIC_MOBILE_WEB` 하나뿐**이다 (다른 층).
    """
    absent_channel = classify_terminal(_signals(cases["reason_no_public_mobile_web"]["signals"]))
    absent_surface = classify_terminal(_signals(cases["public_web_unobservable"]["signals"]))
    unresolved = classify_terminal(
        _signals(cases["reason_unobservable_channel_presence_unresolved_is_other"]["signals"])
    )

    assert absent_channel.endpoint_status is absent_surface.endpoint_status
    assert absent_channel.terminal_reason is TerminalReason.NO_PUBLIC_MOBILE_WEB
    assert absent_surface.terminal_reason is TerminalReason.TASK_SURFACE_ABSENT

    # 미관측을 한쪽으로 밀어 넣지 않는다.
    assert unresolved.terminal_reason is TerminalReason.OTHER
    assert (unresolved.terminal_reason_note or "").strip()


def test_disabled_control_is_not_folded_into_absent_control(
    cases: dict[str, dict[str, Any]],
) -> None:
    """presence != operative — control 이 있는데 작동하지 않는 것을 '없음'으로 접지 않는다."""
    inert = classify_terminal(_signals(cases["reason_control_disabled_or_inert"]["signals"]))
    absent = classify_terminal(
        _signals(cases["reason_control_absent_is_task_surface_absent"]["signals"])
    )

    assert inert.terminal_reason is TerminalReason.CONTROL_DISABLED_OR_INERT
    assert absent.terminal_reason is TerminalReason.TASK_SURFACE_ABSENT
    assert inert.terminal_reason is not absent.terminal_reason
    # 상위 축에서도 갈린다 — 하나는 우리 판정 유보, 하나는 사이트의 성질이다.
    assert inert.endpoint_status is EndpointStatus.ABSTAIN
    assert absent.endpoint_status is EndpointStatus.PUBLIC_WEB_UNOBSERVABLE


def test_waf_block_and_active_challenge_diverge(cases: dict[str, dict[str, Any]]) -> None:
    """`endpoint_status=BLOCKED` 안에서 두 사유가 갈린다."""
    waf = classify_terminal(_signals(cases["reason_waf_block"]["signals"]))
    challenge = classify_terminal(_signals(cases["waf_or_challenge"]["signals"]))
    assert waf.endpoint_status is challenge.endpoint_status is EndpointStatus.BLOCKED
    assert waf.terminal_reason is TerminalReason.WAF_BLOCK
    assert challenge.terminal_reason is TerminalReason.ACTIVE_CHALLENGE


def test_forbidden_action_required_is_a_record_not_a_failure(
    cases: dict[str, dict[str, Any]],
) -> None:
    """금지행위를 하지 않았다는 기록이지 실패가 아니다."""
    got = classify_terminal(_signals(cases["safety_stop"]["signals"]))
    assert got.terminal_reason is TerminalReason.FORBIDDEN_ACTION_REQUIRED
    assert got.terminal is TerminalKind.SAFETY_STOP
    assert "FAILED" not in (got.endpoint_status.value if got.endpoint_status else "")
    doc = TerminalReason.__doc__ or ""
    source = inspect.getsource(terminal_module)
    assert "금지행위를 하지 않았다는 기록이지 실패가 아니다" in source
    assert doc  # 어휘 자체에도 근거가 붙어 있다


def test_other_without_note_is_rejected() -> None:
    """`OTHER` + note 없음 → 예외."""
    with pytest.raises(TerminalReasonNoteError):
        validate_status_reason(EndpointStatus.ABSTAIN, TerminalReason.OTHER, None)
    with pytest.raises(TerminalReasonNoteError):
        validate_status_reason(EndpointStatus.ABSTAIN, TerminalReason.OTHER, "   ")


def test_other_with_note_is_accepted(cases: dict[str, dict[str, Any]]) -> None:
    """양성 대조 — note 가 있으면 통과한다."""
    validate_status_reason(EndpointStatus.ABSTAIN, TerminalReason.OTHER, "경로 확정 불가")

    got = classify_terminal(_signals(cases["reason_other_with_caller_supplied_note"]["signals"]))
    assert got.terminal_reason is TerminalReason.OTHER
    assert got.terminal_reason_note == (
        "지자체 위임 도메인으로 리다이렉트되어 계약상 endpoint 판정 불가"
    )


@pytest.mark.parametrize(
    ("status", "reason"),
    [
        (EndpointStatus.REACHED, TerminalReason.TIMEOUT),
        (EndpointStatus.REACHED, TerminalReason.AUTH_REQUIRED),
        (EndpointStatus.BLOCKED, TerminalReason.EVIDENCE_DEFECT),
        (EndpointStatus.AUTH_GATE, TerminalReason.APP_REQUIRED),
        (EndpointStatus.ABSTAIN, TerminalReason.TIMEOUT),
        (EndpointStatus.EVIDENCE_DEFECT, TerminalReason.AUTH_REQUIRED),
        (EndpointStatus.APP_REQUIRED, None),
    ],
)
def test_impossible_combinations_are_rejected(
    status: EndpointStatus, reason: TerminalReason | None
) -> None:
    """불가능 조합은 스키마가 거부한다 (`R11`)."""
    with pytest.raises(TerminalCombinationError):
        validate_status_reason(status, reason, "note")


@pytest.mark.parametrize(
    ("status", "reason"),
    [
        (EndpointStatus.REACHED, None),
        (EndpointStatus.AUTH_GATE, TerminalReason.AUTH_REQUIRED),
        (EndpointStatus.BLOCKED, TerminalReason.WAF_BLOCK),
        (EndpointStatus.BLOCKED, TerminalReason.ACTIVE_CHALLENGE),
        (EndpointStatus.EVIDENCE_DEFECT, TerminalReason.TIMEOUT),
        (EndpointStatus.PUBLIC_WEB_UNOBSERVABLE, TerminalReason.TASK_SURFACE_ABSENT),
        (EndpointStatus.ABSTAIN, TerminalReason.CONTROL_DISABLED_OR_INERT),
    ],
)
def test_allowed_combinations_pass(status: EndpointStatus, reason: TerminalReason | None) -> None:
    """양성 대조 — 허용 조합은 통과한다."""
    validate_status_reason(status, reason, "note")


def test_combination_table_covers_every_endpoint_status_and_reason() -> None:
    """표에 구멍이 없다 — 7개 status 전부 등재, 16개 reason 전부 어딘가에서 허용."""
    assert set(ALLOWED_ENDPOINT_STATUS_REASONS) == set(EndpointStatus)
    covered: set[TerminalReason] = set()
    for allowed in ALLOWED_ENDPOINT_STATUS_REASONS.values():
        covered |= {r for r in allowed if r is not None}
    missing = set(TerminalReason) - covered
    assert not missing, (
        f"어느 status 에서도 허용되지 않는 reason: {sorted(r.value for r in missing)}"
    )
    # `Δ10-R11` 13 + `Δ30` `BUDGET_EXCEEDED` + `Δ32` `NO_TASK_CANDIDATE_FOUND`
    # + `Δ47` `PATH_NOT_FOUND_BY_POLICY` = 16.
    assert len(set(TerminalReason)) == 16


def test_classifier_never_emits_an_invalid_combination(
    cases: dict[str, dict[str, Any]],
) -> None:
    """`classify_terminal` 이 내는 모든 결과가 조합표를 통과한다."""
    for case_id, case in cases.items():
        got = classify_terminal(_signals(case["signals"]))
        validate_status_reason(got.endpoint_status, got.terminal_reason, got.terminal_reason_note)
        assert got.endpoint_status is not None, case_id


def test_reached_reason_gap_is_declared_not_invented() -> None:
    """`endpoint_status=REACHED` 의 사유는 04 §4 · 02 §5 에 없다 — 지어내지 않고 공백으로 남긴다."""
    assert ALLOWED_ENDPOINT_STATUS_REASONS[EndpointStatus.REACHED] == frozenset({None})
    doc = terminal_module.__doc__ or ""
    assert "명세 공백" in doc
    assert terminal_module._REACHED_REASON_GAP
