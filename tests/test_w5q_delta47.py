"""W5Q — `Δ47` ①②③ + `Δ48` ④⑤.

지키려는 명제:

① **`terminal_reason` 16값** — `PATH_NOT_FOUND_BY_POLICY` 가 `OTHER` 에서 떨어져 나왔다.
   `[Δ47 인용]` *"`OTHER` 하나가 **두 뜻**을 갖는다 … 구분이 **자유 텍스트 note 안**에
   산다. **note 로만 구분되는 것은 범주가 아니다.**"* 기존 15값 판정은 회귀 대조군으로
   고정한다.
② **`Δ36` ② 는 `PARTIALLY_IMPLEMENTED`** — 발산 정지는 `path_discovery_outcome` 축의
   자기 값을 갖고, 산출 행이 남은 이음매를 싣는다. `[Δ47 인용]` *"**막은 것이지 고친 것이
   아니다.**"* 이 파일은 그것을 '해결' 로 적지 않는다.
③ **`GATE 1` 이 depth 산출 경로를 실제로 실행한다** — `must_flag`(수) 와
   `must_not_flag`(`None`+사유) 가 **둘 다** 있고 두 출력이 다르다.
④ **`Δ48-R42`** — `ax_node` 형태 위반은 `raise` 로 끝나고 `dom_ax_divergence` 에 값으로
   기여하지 않는다. 정당한 divergence 관측은 살아 있다.
⑤ **`Δ48` ⑤** — `service_id`/`task_id` 가 조용히 다른 값으로 떨어지지 않는다.

**이 파일의 fixture 판정은 synthetic offline fixture 에 대한 결과다.** 실서비스에 대한
research finding 이 아니며 그렇게 인용할 수 없다. 실사이트 접속은 0 이다.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import pytest

REPO = Path(__file__).resolve().parents[1]
RESEARCH = REPO / "research" / "landing_accessibility"
sys.path.insert(0, str(RESEARCH / "src"))

from landing_accessibility.v3_runner import runner as runner_mod  # noqa: E402
from landing_accessibility.v3_runner import surface as surface_mod  # noqa: E402
from landing_accessibility.v3_runner import terminal as terminal_mod  # noqa: E402
from landing_accessibility.v3_runner.contracts import FlowStep  # noqa: E402
from landing_accessibility.v3_runner.discovery import (  # noqa: E402
    V3PathOrderDivergenceError,
)
from landing_accessibility.v3_runner.runner import (  # noqa: E402
    DELTA36_2_REMAINING_SEAM,
    DELTA36_2_STATUS,
    IDENTITY_CALLER_SUPPLIED,
    IDENTITY_DERIVED_FROM_CONTRACT,
    PATH_DISCOVERY_SEAM_REFUSED_V2_ORDER,
    PATH_NOT_FOUND_NOTE,
    SEARCH_STRATEGY,
    ObservationIdentityError,
    PlannedAction,
    RunnerError,
    ScoutBudget,
    assert_no_path_absence_claim,
    assert_path_discovery_declared,
    seam_refusal_result,
)
from landing_accessibility.v3_runner.terminal import (  # noqa: E402
    ALLOWED_ENDPOINT_STATUS_REASONS,
    EndpointStatus,
    TerminalCombinationError,
    TerminalReason,
    TerminalSignals,
    classify_terminal,
    validate_status_reason,
)

# W5F/W5O 의 fake 경계를 재구현하지 않는다 — 정본이 둘이 되면 안 된다.
from test_w5f_runner_core import (  # noqa: E402
    FakeDriver,
    FakeTerminal,
    ObservationKey,
    make_contract,
    make_runner,
    ok_transition,
)
from test_w5o_delta36_delta37 import _NoCandidateBinder, _RealBinder, _ScoutOf  # noqa: E402

V3_FIXTURES = RESEARCH / "fixtures" / "v3"
MATRIX_PATH = V3_FIXTURES / "FIXTURE_DISCRIMINATION_MATRIX.json"
W5D_CASES = RESEARCH / "fixtures" / "w5d" / "terminal_cases.json"

#: `Δ47` 이전에 존재하던 15값. **회귀 대조군의 정본**이며 이 목록은 늘지 않는다.
REASONS_BEFORE_DELTA47 = (
    "TIMEOUT",
    "WAF_BLOCK",
    "ACTIVE_CHALLENGE",
    "NO_PUBLIC_MOBILE_WEB",
    "TASK_SURFACE_ABSENT",
    "APP_REQUIRED",
    "CONTROL_DISABLED_OR_INERT",
    "FORBIDDEN_ACTION_REQUIRED",
    "AUTH_REQUIRED",
    "EVIDENCE_DEFECT",
    "REPLAY_BROKEN",
    "AMBIGUOUS_MULTIPLE_CANDIDATES",
    "OTHER",
    "BUDGET_EXCEEDED",
    "NO_TASK_CANDIDATE_FOUND",
)

#: 이 lane 이 `fixtures/w5d/terminal_cases.json` 에 **더한** case. 회귀 대조군은 이것을
#: 빼고 본다 — 새로 더한 case 가 "기존 판정이 안 바뀌었다" 의 근거가 될 수는 없다.
W5Q_ADDED_CASE_IDS = frozenset(
    {
        "path_not_found_by_policy_is_its_own_category",
        "path_not_found_and_unclassified_are_different_values",
        "budget_exceeded_precedes_path_not_found_by_policy",
        "path_not_found_by_policy_does_not_override_a_real_terminal",
    }
)


def _cases() -> list[dict[str, Any]]:
    return json.loads(W5D_CASES.read_text("utf-8"))["cases"]


def _signals(raw: dict[str, Any]) -> TerminalSignals:
    kwargs = dict(raw)
    if "auth_gate_stage" in kwargs:
        from landing_accessibility.v3_runner.terminal import AuthGateStage

        kwargs["auth_gate_stage"] = AuthGateStage(kwargs["auth_gate_stage"])
    return TerminalSignals(**kwargs)


# ═══════════════════════════════════════════════════════════════════════════
# ① `PATH_NOT_FOUND_BY_POLICY` — 16번째 값
# ═══════════════════════════════════════════════════════════════════════════
def test_delta47_the_sixteenth_value_exists_and_is_registered() -> None:
    """어휘·조합표·모듈 문서 세 곳이 같은 것을 말한다. 한 곳만 고치면 여기서 걸린다."""
    assert len(set(TerminalReason)) == 16
    assert TerminalReason.PATH_NOT_FOUND_BY_POLICY.value == "PATH_NOT_FOUND_BY_POLICY"
    assert (
        TerminalReason.PATH_NOT_FOUND_BY_POLICY
        in ALLOWED_ENDPOINT_STATUS_REASONS[EndpointStatus.ABSTAIN]
    )
    assert "16값" in (terminal_mod.__doc__ or "")
    # 이 값이 **하지 않는** 주장이 값 옆에 적혀 있는가 (`R37` 2항). StrEnum 은 멤버별
    # docstring 을 보존하지 않으므로 원본에서 그 절을 읽는다.
    src = (RESEARCH / "src/landing_accessibility/v3_runner/terminal.py").read_text("utf-8")
    clause = src.split('PATH_NOT_FOUND_BY_POLICY = "PATH_NOT_FOUND_BY_POLICY"', 1)[1]
    clause = clause.split("class TerminalCombinationError", 1)[0]
    assert "사이트에 그런 경로가" in clause
    assert "주장하지 **않는** 것" in clause


def test_negative_control_all_sixteen_values_are_pairwise_distinct() -> None:
    """16값이 서로 구분된다 — 값이 겹치면 어휘가 늘어난 척만 한 것이다."""
    values = [r.value for r in TerminalReason]
    assert len(values) == len(set(values)) == 16
    assert TerminalReason.OTHER is not TerminalReason.PATH_NOT_FOUND_BY_POLICY
    assert TerminalReason.OTHER.value != TerminalReason.PATH_NOT_FOUND_BY_POLICY.value


def test_negative_control_not_found_and_unclassified_take_different_values() -> None:
    """**Δ47 ① 의 핵심 음성대조** — 두 사건이 같은 값으로 접히지 않는다.

    `[Δ47 인용]` *"`OTHER` 에 두면 `OTHER` 하나가 **두 뜻**을 갖는다 — '정책이 못 찾았다'
    와 '분류되지 않았다'."*
    """
    not_found = classify_terminal(
        TerminalSignals(
            evidence_complete=True, task_candidate_count=2, policy_did_not_find_path=True
        )
    )
    unclassified = classify_terminal(
        TerminalSignals(evidence_complete=True, task_candidate_count=2)
    )
    assert not_found.terminal_reason is TerminalReason.PATH_NOT_FOUND_BY_POLICY
    assert unclassified.terminal_reason is TerminalReason.OTHER
    assert not_found.terminal_reason != unclassified.terminal_reason
    # 두 축이 서로를 검증한다 — endpoint_status 는 **같다.** 그래서 이 축이 필요했다.
    assert not_found.endpoint_status is unclassified.endpoint_status is EndpointStatus.ABSTAIN


def test_the_category_does_not_live_in_the_note(tmp_path: Path) -> None:
    """`[Δ47 인용]` *"note 로만 구분되는 것은 범주가 아니다."*

    note 를 통째로 바꿔도 **범주는 그대로**여야 한다. 세는 쪽이 문자열을 볼 필요가 없다는
    것이 이 테스트의 내용이다.
    """
    custom = classify_terminal(
        TerminalSignals(
            evidence_complete=True,
            task_candidate_count=2,
            policy_did_not_find_path=True,
            other_reason_note="완전히 다른 문장",
        )
    )
    assert custom.terminal_reason is TerminalReason.PATH_NOT_FOUND_BY_POLICY
    assert custom.terminal_reason_note == "완전히 다른 문장"

    # runner 경로도 같다 — note 는 실리지만 구분은 값이 갖는다.
    result = make_runner(
        tmp_path, binder=_RealBinder(), scout=_ScoutOf([]), terminal=FakeTerminal(None)
    ).run(make_contract(), driver=FakeDriver(transitions=[]), run_id="w5q-note")
    record = result.as_mart_record()
    assert record["terminal_reason"] == "PATH_NOT_FOUND_BY_POLICY"
    assert record["terminal_reason_note"] == PATH_NOT_FOUND_NOTE  # note 는 유지된다
    # 세려면 값 비교면 된다 — 문자열 매칭이 필요 없다.
    assert record["terminal_reason"] == TerminalReason.PATH_NOT_FOUND_BY_POLICY.value


def test_the_absence_claim_guard_is_still_in_force(tmp_path: Path) -> None:
    """`Δ47`: *"`assert_no_path_absence_claim` 은 그대로 유지해라."* — 그리고 새 값
    자체가 부재 주장 어휘로 읽히지 않는다."""
    from landing_accessibility.v3_runner.runner import PathAbsenceClaimError

    result = make_runner(
        tmp_path, binder=_RealBinder(), scout=_ScoutOf([]), terminal=FakeTerminal(None)
    ).run(make_contract(), driver=FakeDriver(transitions=[]), run_id="w5q-absence")
    record = result.as_mart_record()
    assert_no_path_absence_claim(record)  # 양성 대조 — 새 값이 걸리지 않는다

    # `R31` — 이 단언이 **실제로 실패하는 입력**. 실패 메시지도 고정한다.
    with pytest.raises(PathAbsenceClaimError, match="경로 부재 주장 어휘"):
        assert_no_path_absence_claim({"note": "이 서비스에는 경로가 없다"})


def test_r31_the_combination_table_refuses_the_new_value_where_it_cannot_occur() -> None:
    """`R31` — 새 값이 조합표에 **무조건 통과**하는 값이 아니다."""
    validate_status_reason(  # 양성 대조
        EndpointStatus.ABSTAIN, TerminalReason.PATH_NOT_FOUND_BY_POLICY, "note"
    )
    for status in (EndpointStatus.REACHED, EndpointStatus.BLOCKED, EndpointStatus.AUTH_GATE):
        with pytest.raises(TerminalCombinationError):
            validate_status_reason(status, TerminalReason.PATH_NOT_FOUND_BY_POLICY, "note")


@pytest.mark.parametrize(
    "case",
    [c for c in _cases() if c["case_id"] not in W5Q_ADDED_CASE_IDS],
    ids=lambda c: c["case_id"],
)
def test_regression_control_the_prior_verdicts_are_unchanged(case: dict[str, Any]) -> None:
    """**회귀 대조군** — `Δ47` 이전부터 있던 case 의 판정이 한 건도 안 바뀌었다.

    새 값은 **더해졌을 뿐** 기존 판정을 재정의하지 않았다. 이 lane 이 더한 case 는 위
    parametrize 에서 빠져 있다 — 새로 더한 것이 "안 바뀌었다" 의 근거가 될 수는 없다.
    """
    got = classify_terminal(_signals(case["signals"]))
    reason = got.terminal_reason.value if got.terminal_reason else None
    assert reason == case["expect"]["terminal_reason"], case["case_id"]
    if reason is not None:
        assert reason in REASONS_BEFORE_DELTA47, (
            f"{case['case_id']}: 기존 case 가 Δ47 신설값으로 옮겨 갔다 — 재정의다"
        )


# ═══════════════════════════════════════════════════════════════════════════
# ② `Δ36` ② 는 `PARTIALLY_IMPLEMENTED` — 산출에 남는다
# ═══════════════════════════════════════════════════════════════════════════
def test_delta36_2_status_and_the_remaining_seam_are_on_every_row(tmp_path: Path) -> None:
    """상태만 두면 무엇이 부분인지 복원할 수 없다 — 남은 이음매 서술이 함께 실린다."""
    result = make_runner(tmp_path).run(
        make_contract(),
        driver=FakeDriver(transitions=[ok_transition(0, endpoint=True)] * 2),
        run_id="w5q-seam-row",
    )
    record = result.as_mart_record()
    assert record["delta36_2_seam_status"] == "PARTIALLY_IMPLEMENTED"
    seam = record["delta36_2_remaining_seam"]
    assert "run_task_aware_scout" in seam and "Scout.scout()" in seam
    assert "막은 것이지 고친 것이 아니다" in seam


def test_the_refusal_is_never_written_as_resolved() -> None:
    """`[Δ47 인용]` *"거부를 '해결' 로 적으면 안 된다."*

    발산 정지를 서술하는 자리(상수·예외 docstring)에 완료 어휘가 없다. 양성 대조로
    `PARTIALLY_IMPLEMENTED` 가 **실제로 있다**는 것을 함께 본다 — 그래야 이 grep 이
    아무것도 못 찾는 grep 이 아니다.
    """
    resolved_terms = ("해결됐다", "해결했다", "수정 완료", "완료됐다", "고쳤다")
    texts = [DELTA36_2_REMAINING_SEAM, V3PathOrderDivergenceError.__doc__ or ""]
    texts.append(runner_mod.seam_refusal_result.__doc__ or "")
    for text in texts:
        for term in resolved_terms:
            assert term not in text, f"부분 이행을 완료로 적었다: {term}"
    assert DELTA36_2_STATUS == "PARTIALLY_IMPLEMENTED"
    assert "PARTIALLY_IMPLEMENTED" in (runner_mod.seam_refusal_result.__doc__ or "")


def test_the_divergence_error_carries_the_structure_not_just_a_string() -> None:
    """`pilot 5` 가 "어떤 구조에서 갈렸는가" 를 읽어야 한다 — 메시지 재파싱에 기대지 않는다."""
    err = V3PathOrderDivergenceError(
        "메시지", task_id="t1", v2_order=["a", "b"], v3_order=["b", "a"]
    )
    assert err.task_id == "t1"
    assert err.v2_order == ("a", "b") and err.v3_order == ("b", "a")
    assert "v2(min4)=['a', 'b']" in err.divergence_detail()


def test_negative_control_five_events_do_not_collapse_into_one_output(tmp_path: Path) -> None:
    """**Δ47 ② 의 핵심 음성대조** — 이제 다섯이다. 산출에서 전부 갈린다.

    (1) 발산으로 멈춤 (2) 경로 미발견 (3) 후보 부재 (4) 예산 소진 (5) endpoint 도달 실패.
    둘 이상이 같은 출력이면 `pilot 5` 에서 그 사건의 분모를 복원할 수 없다.
    """
    refused = seam_refusal_result(
        ObservationKey(service_id="svc", task_id="task", run_id="w5q-refused"),
        divergence_detail="v2=[b,a] v3=[a,b]",
    )
    not_found = make_runner(
        tmp_path / "nf", binder=_RealBinder(), scout=_ScoutOf([]), terminal=FakeTerminal(None)
    ).run(make_contract(), driver=FakeDriver(transitions=[]), run_id="w5q-nf")
    no_candidate = make_runner(
        tmp_path / "nc",
        binder=_NoCandidateBinder(),
        scout=_ScoutOf([]),
        terminal=FakeTerminal(None),
    ).run(make_contract(), driver=FakeDriver(transitions=[]), run_id="w5q-nc")
    exhausted = make_runner(
        tmp_path / "bx",
        binder=_RealBinder(),
        scout=_ScoutOf([PlannedAction("SELECT_CATEGORY") for _ in range(4)]),
        budget=ScoutBudget(max_activations=2),
        terminal=FakeTerminal(None),
    ).run(
        make_contract(),
        driver=FakeDriver(transitions=[ok_transition(i) for i in range(6)]),
        run_id="w5q-bx",
    )
    endpoint_failed = make_runner(
        tmp_path / "ef",
        binder=_RealBinder(),
        scout=_ScoutOf([PlannedAction("SELECT_FUNCTION", control_selector="#entry")]),
        terminal=FakeTerminal("AUTH_GATE"),
    ).run(
        make_contract(),
        driver=FakeDriver(transitions=[ok_transition(0, auth=True)] * 2),
        run_id="w5q-ef",
    )

    rows = {
        "refused": refused.as_mart_record(),
        "not_found": not_found.as_mart_record(),
        "no_candidate": no_candidate.as_mart_record(),
        "exhausted": exhausted.as_mart_record(),
        "endpoint_failed": endpoint_failed.as_mart_record(),
    }
    axes = {
        name: (r["path_discovery_outcome"], r["terminal_reason"], r["policy_relative"])
        for name, r in rows.items()
    }
    assert len(set(axes.values())) == 5, f"다섯 사건이 같은 출력으로 접혔다: {axes}"

    # 거부는 **자기 값**을 갖는다 — 다른 미관측 어디에도 접히지 않는다.
    assert rows["refused"]["path_discovery_outcome"] == PATH_DISCOVERY_SEAM_REFUSED_V2_ORDER
    assert rows["refused"]["policy_relative"] is True
    assert rows["refused"]["search_strategy"] == SEARCH_STRATEGY
    outcomes = [r["path_discovery_outcome"] for r in rows.values()]
    assert len(set(outcomes)) == 5, f"path_discovery_outcome 축만으로도 갈려야 한다: {outcomes}"
    # 거부 행도 부재 주장을 하지 않는다.
    assert_no_path_absence_claim(rows["refused"])


def test_r31_the_declaration_guard_fires_on_the_new_outcome() -> None:
    """`R31` — 새 값이 선언 검사를 **그냥 통과하는** 값이 아니다."""
    good = {
        "path_discovery_outcome": PATH_DISCOVERY_SEAM_REFUSED_V2_ORDER,
        "policy_relative": True,
        "search_strategy": SEARCH_STRATEGY,
    }
    assert_path_discovery_declared(good)  # 양성 대조
    with pytest.raises(RunnerError, match="policy_relative 가 True 가 아니다"):
        assert_path_discovery_declared(dict(good, policy_relative=False))
    with pytest.raises(RunnerError, match="search_strategy 가 없다"):
        assert_path_discovery_declared({k: v for k, v in good.items() if k != "search_strategy"})


# ═══════════════════════════════════════════════════════════════════════════
# ③ `GATE 1` — depth 산출 경로를 실제로 실행한다 (fixture 전용, 실사이트 0)
# ═══════════════════════════════════════════════════════════════════════════
pytest.importorskip("playwright.sync_api")

from landing_accessibility.engine.evidence import EvidenceRun  # noqa: E402
from landing_accessibility.engine.firewall import ExecutionMode  # noqa: E402
from landing_accessibility.engine.l0_collector import FixtureTarget, L0Collector  # noqa: E402
from landing_accessibility.engine.vocabulary import InteractionArchetype  # noqa: E402
from landing_accessibility.v3_runner import flow as flow_mod  # noqa: E402
from landing_accessibility.v3_runner.scout_strategy import _to_planned_action  # noqa: E402


def _matrix() -> dict[str, Any]:
    return json.loads(MATRIX_PATH.read_text("utf-8"))["gate1_depth_signal_fixtures"]


@pytest.fixture(scope="module")
def gate1_probe(tmp_path_factory: pytest.TempPathFactory) -> dict[str, Any]:
    """선언된 must_flag/must_not_flag fixture 를 **실제 `l0_probe.js` 로** 관측한다.

    분류기에 손으로 만든 candidate dict 를 먹이면 "fixture 에 신호가 있다" 를 검증하지
    못한다 — `GATE 1` 이 통과했다고 기록되지만 fixture 는 한 번도 읽히지 않는다.
    """
    section = _matrix()
    names = [f["file"] for f in section["must_flag_fixtures"]]
    names.append(section["must_not_flag_control"]["file"])
    tmp = tmp_path_factory.mktemp("w5q-gate1")
    run = EvidenceRun.create(tmp, "w5q-gate1", execution_mode=ExecutionMode.FIXTURE)
    collector = L0Collector(run, fixture_root=V3_FIXTURES)
    return {
        name: collector.collect(
            FixtureTarget(
                web_target_id=f"wt-{name}",
                fixture=name,
                archetype=InteractionArchetype.UTILITY_ENTRY,
            )
        ).raw_features
        for name in names
    }


def _step(index: int, token: str, **overrides: Any) -> FlowStep:
    """`FlowStep` 전 필드를 채운 최소 step. 기본값은 전부 "관측 없음" 이다."""
    base: dict[str, Any] = {
        "step_index": index,
        "action_token": token,
        "state_before_id": f"s{index}",
        "state_after_id": f"s{index + 1}",
        "control_selector": None,
        "control_role": None,
        "control_visible_text": None,
        "control_accessible_name": None,
        "bbox_before": None,
        "url_before": None,
        "url_after": None,
        "auth_gate_detected": False,
        "endpoint_signal_detected": False,
    }
    base.update(overrides)
    return FlowStep(**base)


def _normalize_from_probe(probe_state: dict[str, Any]) -> Any:
    """probe 후보 → `_to_planned_action` → `FlowStep` → `flow.normalize_flow`.

    **depth 산출 경로를 끝까지 실행하는 것이 이 함수의 목적이다.** 마지막에 endpoint
    표지를 붙이는 것은 관측 완결성(`Δ10`) 때문이며, 그 step 은 activation 이 아니다.
    """
    candidates = list(probe_state.get("primary_action_candidates") or [])
    assert candidates, "fixture 에서 후보가 하나도 안 나왔다 — 이 게이트는 헛돈다"
    steps = []
    for index, candidate in enumerate(candidates):
        action = _to_planned_action(candidate)
        steps.append(
            _step(
                index,
                action.action_token,
                token_determinacy=action.token_determinacy,
                control_selector=action.control_selector,
            )
        )
    steps.append(_step(len(steps), "ENDPOINT_REACHED", endpoint_signal_detected=True))
    return flow_mod.normalize_flow(steps)


def test_gate1_must_flag_a_signalled_fixture_produces_a_number(
    gate1_probe: dict[str, Any],
) -> None:
    """`must_flag` — 신호 있는 fixture 최소 1건에서 `activation_depth` 가 **수로 산출**된다."""
    produced: dict[str, Any] = {}
    for entry in _matrix()["must_flag_fixtures"]:
        norm = _normalize_from_probe(gate1_probe[entry["file"]])
        produced[entry["fixture_id"]] = norm
        assert isinstance(norm.activation_depth, int), (
            f"{entry['fixture_id']}: activation_depth 가 수로 산출되지 않았다"
        )
        assert norm.activation_depth == entry["expected_activation_depth"]
        assert norm.activation_depth_undetermined_reason is None
        assert norm.menu_dependency is entry["expected_menu_dependency"]
    assert produced, "must_flag fixture 가 선언되지 않았다"


def test_gate1_must_not_flag_the_signalless_fixture_yields_none_with_a_reason(
    gate1_probe: dict[str, Any],
) -> None:
    """`must_not_flag` — 신호 없는 fixture 에서 `None` + **사유**가 나온다.

    `None` 만 나오고 사유가 없으면 "못 쟀다" 와 "재지 않기로 했다" 가 같은 출력이다.
    """
    control = _matrix()["must_not_flag_control"]
    norm = _normalize_from_probe(gate1_probe[control["file"]])
    assert norm.activation_depth is None
    reason = norm.activation_depth_undetermined_reason or ""
    assert control["expected_activation_depth_undetermined_reason_contains"] in reason


def test_gate1_the_two_outputs_are_demonstrably_different(gate1_probe: dict[str, Any]) -> None:
    """`[Δ47 인용]` *"그리고 **두 출력이 서로 다름을 실증한다.** 한쪽만 만들면 조용한
    상태를 다른 조용한 상태로 바꾼 것뿐이다."*

    같은 코드 경로에 두 fixture 를 넣어 산출을 직접 비교한다. 구조는 동일하고 ARIA 속성
    하나만 다르므로, 갈리는 원인이 그 신호 말고 다른 것일 수 없다.
    """
    section = _matrix()
    control = section["must_not_flag_control"]
    control_norm = _normalize_from_probe(gate1_probe[control["file"]])
    for entry in section["must_flag_fixtures"]:
        flagged = _normalize_from_probe(gate1_probe[entry["file"]])
        assert flagged.activation_depth != control_norm.activation_depth
        assert isinstance(flagged.activation_depth, int)
        assert control_norm.activation_depth is None
        # 사유의 유무도 갈린다 — 한쪽은 값이 있고 다른 쪽은 왜 없는지가 있다.
        assert flagged.activation_depth_undetermined_reason is None
        assert control_norm.activation_depth_undetermined_reason


def test_gate1_the_signal_is_what_differs_not_the_structure(gate1_probe: dict[str, Any]) -> None:
    """대조 짝의 태그 시퀀스가 같다 — 갈린 것이 구조가 아니라 **신호**임을 고정한다."""
    import re as _re

    def tags(name: str) -> list[str]:
        body = (V3_FIXTURES / name).read_text("utf-8").split("<body", 1)[1]
        return _re.findall(r"<\s*([a-zA-Z0-9]+)", body)

    control = _matrix()["must_not_flag_control"]["file"]
    for entry in _matrix()["must_flag_fixtures"]:
        assert entry["dom_tag_sequence_identical_to_control"] is True
        assert tags(entry["file"]) == tags(control), f"{entry['file']}: 구조가 같지 않다"


def test_gate1_the_probe_actually_carries_the_added_signal(gate1_probe: dict[str, Any]) -> None:
    """음성대조 — 대조 fixture 에는 그 신호가 **없다.** 신호가 양쪽에 다 있으면 위 비교는
    무엇도 보이지 않는다."""
    control = _matrix()["must_not_flag_control"]["file"]
    control_cands = gate1_probe[control]["primary_action_candidates"]
    assert all(not c.get("aria_haspopup") for c in control_cands)
    assert all(c.get("controls_is_nav_landmark") is None for c in control_cands)

    signals_seen = set()
    for entry in _matrix()["must_flag_fixtures"]:
        for c in gate1_probe[entry["file"]]["primary_action_candidates"]:
            if c.get("aria_haspopup"):
                signals_seen.add("aria_haspopup")
            if c.get("controls_is_nav_landmark") is True:
                signals_seen.add("aria_controls")
    assert signals_seen == {"aria_haspopup", "aria_controls"}


def test_the_fixture_only_limitation_is_written_down() -> None:
    """`Δ47` 이 **반드시 적으라**고 한 한계가 matrix 와 fixture 파일 양쪽에 있다."""
    limitation = _matrix()["limitation"]
    assert "실사이트에 그 신호가 있다는 근거는 아니다" in limitation
    assert "fixture 근거만" in limitation
    for entry in _matrix()["must_flag_fixtures"]:
        text = (V3_FIXTURES / entry["file"]).read_text("utf-8")
        assert "실사이트에 그 신호가 있다는 근거는 아니다" in text


def test_the_thirteen_original_fixtures_were_not_modified() -> None:
    """`Δ47`: *"v2 fixture 는 건드리지 않는다"* · 기존 v3 fixture 는 **가산만**.

    lane base 커밋과 `--name-status` 로 직접 비교한다 — 선언이 아니라 실측이다.
    `M`(수정)과 `A`(추가)를 나눠 보는 것이 요점이다: 추가는 허용이고 수정은 아니다.
    """
    import subprocess

    base = "abaefd67e9e54b74c23b1e806608fc4de3b11a82"
    out = subprocess.run(
        [
            "git",
            "diff",
            "--name-status",
            base,
            "--",
            "research/landing_accessibility/fixtures/",
        ],
        cwd=REPO,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.splitlines()
    rows = [line.split("\t") for line in out if line.strip()]
    modified = sorted(path for status, path in rows if status != "A")
    added = sorted(path for status, path in rows if status == "A")

    assert not any(p.endswith(".html") for p in modified), (
        f"기존 fixture HTML 이 수정됐다 — 가산만 허용된다: {modified}"
    )
    # 선언 파일(JSON) 갱신은 `Δ47` 이 **요구**했다. 그 밖의 수정은 없다.
    assert modified == [
        "research/landing_accessibility/fixtures/v3/FIXTURE_DISCRIMINATION_MATRIX.json",
        "research/landing_accessibility/fixtures/w5d/terminal_cases.json",
    ], f"예상 밖의 fixture 파일이 수정됐다: {modified}"
    # 추가된 것은 matrix 가 선언한 가산분뿐이다.
    declared = {f"research/landing_accessibility/fixtures/v3/{fid}.html" for fid in _added_ids()}
    assert set(added) <= declared, (
        f"선언되지 않은 fixture 가 추가됐다: {sorted(set(added) - declared)}"
    )
    # `fixtures/w5j/` 는 손대지 않는다(금지 목록).
    assert not any("/w5j/" in path for _status, path in rows)


def _added_ids() -> list[str]:
    section = json.loads(MATRIX_PATH.read_text("utf-8"))["gate1_depth_signal_fixtures"]
    return [f["fixture_id"] for f in section["must_flag_fixtures"]]


# ═══════════════════════════════════════════════════════════════════════════
# ④ `Δ48-R42` — 형태 오류는 관측 변수에 값으로 기여하지 못한다
# ═══════════════════════════════════════════════════════════════════════════
#: `measure_surface` 가 실제로 읽는 probe state 모양의 정본은 W5C fixture 다. 여기서
#: 새로 지어내면 두 정본이 생기므로 그 파일에서 한 건을 읽어 selector 만 바꿔 쓴다.
W5C_CASES = RESEARCH / "fixtures" / "w5c_surface" / "delta15_new_field_cases.json"


def _probe_with(selector: str, present: bool) -> dict[str, Any]:
    """`measure_surface` 입력 — `present=False` 면 DOM 쪽에서 control 을 못 찾은 경로다."""
    import copy

    case = json.loads(W5C_CASES.read_text("utf-8"))["cases"][0]
    state = copy.deepcopy(case["probe_state"])
    features = state["raw_features"]
    for key in ("primary_action_candidates", "accessible_name_sources"):
        for row in features.get(key, []):
            row["selector"] = selector
            row["hittable"] = True
        if not present:
            features[key] = []
    return state


AX_NODE_OK = {"role": "button", "name": "운행정보 조회", "name_computed": True}


@pytest.mark.parametrize("bad", ["문자열", ["list"], 3, True])
def test_r42_a_shape_violation_raises_and_contributes_no_value(bad: Any) -> None:
    """`[Δ48-R42 인용]` *"형태 위반은 `raise` 로 끝나고, 어떤 관측 변수에도 값으로 기여하지
    않는다."*

    이전에는 이 입력이 `dom_ax_divergence=True` 라는 **실질 관측**으로 둔갑했다.
    """
    for present in (True, False):  # DOM 발견 경로 · 미발견 경로 **둘 다**
        with pytest.raises(surface_mod.AxNodeShapeError, match="dict 이거나 None"):
            surface_mod.measure_surface(
                probe_state=_probe_with("button#entry", present),
                task_control={"selector": "button#entry", "ax_node": bad},
                viewport=(390, 844),
            )


def test_r42_a_nested_shape_violation_also_raises() -> None:
    """`ignored` 가 bool 이 아니면 `ax_observed` 가 조용히 `True` 로 떨어진다 — 같은 결함이
    한 겹 안에서 재발하는 자리다."""
    with pytest.raises(surface_mod.AxNodeShapeError, match="ignored"):
        surface_mod.measure_surface(
            probe_state=_probe_with("button#entry", True),
            task_control={"selector": "button#entry", "ax_node": {"ignored": "true"}},
            viewport=(390, 844),
        )


def test_r42_negative_control_three_outcomes_split() -> None:
    """**R42 이행의 핵심 음성대조** — 셋이 갈린다.

    ① 형태 위반 → `raise`(값 없음) ② 실제 DOM/AX 불일치 → `True` ③ 일치 → `False`.
    ②를 죽이면 `R42` 를 이행한 것이 아니라 관측을 없앤 것이다.
    """
    outcomes: dict[str, Any] = {}

    # ① 형태 위반 — 산출이 없다.
    with pytest.raises(surface_mod.AxNodeShapeError):
        surface_mod.measure_surface(
            probe_state=_probe_with("button#entry", True),
            task_control={"selector": "button#entry", "ax_node": "형태 위반"},
            viewport=(390, 844),
        )
    outcomes["shape_violation"] = "RAISED"

    # ② 실제 불일치 — DOM 에는 있고 AX 에는 없다(찾아봤는데 없었다 = `ax_node: None`).
    diverged = surface_mod.measure_surface(
        probe_state=_probe_with("button#entry", True),
        task_control={"selector": "button#entry", "ax_node": None},
        viewport=(390, 844),
    )
    outcomes["real_divergence"] = diverged.dom_ax_divergence

    # ③ 일치 — 양쪽 다 있다.
    agreed = surface_mod.measure_surface(
        probe_state=_probe_with("button#entry", True),
        task_control={"selector": "button#entry", "ax_node": AX_NODE_OK},
        viewport=(390, 844),
    )
    outcomes["agreement"] = agreed.dom_ax_divergence

    assert outcomes["real_divergence"] is True, "정당한 divergence 관측을 죽였다"
    assert outcomes["agreement"] is False
    assert len(set(map(str, outcomes.values()))) == 3, f"셋이 갈리지 않았다: {outcomes}"


def test_r42_the_ignored_ax_node_is_still_a_divergence() -> None:
    """AX 가 무시한 노드는 보조기술에 없는 것이다 — 형태는 멀쩡하므로 **관측**으로 산다."""
    m = surface_mod.measure_surface(
        probe_state=_probe_with("button#entry", True),
        task_control={"selector": "button#entry", "ax_node": dict(AX_NODE_OK, ignored=True)},
        viewport=(390, 844),
    )
    assert m.dom_ax_divergence is True


def test_r42_an_undeclared_ax_node_is_not_a_divergence() -> None:
    """음성대조 — 키를 아예 안 준 것은 "AX 에 없다" 가 아니다. 이것까지 `True` 면 미관측이
    관측으로 승격된다."""
    m = surface_mod.measure_surface(
        probe_state=_probe_with("button#entry", True),
        task_control={"selector": "button#entry"},
        viewport=(390, 844),
    )
    assert m.dom_ax_divergence is False
    assert m.ax_control_observed is False


def test_r42_the_resolver_is_the_only_entry_to_the_divergence_axis() -> None:
    """판정이 한 곳에 있다 — 두 산출 경로가 각자 판정하면 한쪽만 고쳐지는 날이 온다.

    (`Δ48` 이 지적한 결함이 실제로 '못 찾은 경로' 에서만 관측됐다.)
    """
    src = (RESEARCH / "src/landing_accessibility/v3_runner/surface.py").read_text("utf-8")
    body = src.split("def measure_surface(", 1)[1]
    assert body.count("_resolve_ax_observation(") == 1, "판정 입구가 하나가 아니다"
    # `measure_surface` 본문이 자기 판정을 다시 갖고 있지 않다.
    assert 'ax_raw.get("ignored")' not in body
    assert 'ax_declared = "ax_node" in task_control' not in body


# ═══════════════════════════════════════════════════════════════════════════
# ⑤ `service_id`/`task_id` — 조용히 다른 값으로 떨어지지 않는다
# ═══════════════════════════════════════════════════════════════════════════
def test_identity_supplied_is_used_and_marked_as_supplied(tmp_path: Path) -> None:
    """양성 대조 — 호출자가 준 값이 그대로 실리고 출처가 기록된다."""
    result = make_runner(tmp_path).run(
        make_contract(),
        driver=FakeDriver(transitions=[ok_transition(0, endpoint=True)] * 2),
        run_id="w5q-id-1",
        service_id="svc_given",
        task_id="task_given",
    )
    record = result.as_mart_record()
    assert record["service_id"] == "svc_given"
    assert record["task_id"] == "task_given"
    assert record["service_id_provenance"] == IDENTITY_CALLER_SUPPLIED
    assert record["task_id_provenance"] == IDENTITY_CALLER_SUPPLIED


def test_identity_absent_derives_from_contract_and_says_so(tmp_path: Path) -> None:
    """부재 — 계약에서 파생하되 **파생했다는 사실**이 산출에 남는다."""
    contract = make_contract()
    result = make_runner(tmp_path).run(
        contract,
        driver=FakeDriver(transitions=[ok_transition(0, endpoint=True)] * 2),
        run_id="w5q-id-2",
    )
    record = result.as_mart_record()
    assert record["service_id"] == contract.target_id
    assert record["service_id_provenance"] == IDENTITY_DERIVED_FROM_CONTRACT
    assert record["task_id_provenance"] == IDENTITY_DERIVED_FROM_CONTRACT


@pytest.mark.parametrize("bad", ["", "   ", 0, 7, [], {}, False])
def test_identity_shape_violation_raises_instead_of_falling_back(tmp_path: Path, bad: Any) -> None:
    """**Δ48 ⑤ 의 핵심** — 형태 위반이 조용히 계약값으로 떨어지던 경로가 사라졌다.

    이전 코드는 `service_id or contract.target_id` 였다. 아래 입력은 전부 falsy 이거나
    검증되지 않은 값이어서 **다른 서비스 id 로 조용히 떨어졌다.** 이제 멈춘다.
    """
    contract = make_contract()
    with pytest.raises(ObservationIdentityError, match="service_id"):
        make_runner(tmp_path).run(
            contract,
            driver=FakeDriver(transitions=[ok_transition(0, endpoint=True)] * 2),
            run_id="w5q-id-3",
            service_id=bad,
        )


def test_negative_control_the_silent_fallback_path_is_gone(tmp_path: Path) -> None:
    """세 상태가 산출에서 갈린다 — 부재(파생·표시됨) · 형태 위반(행 없음) · 존재(그 값).

    특히 **빈 문자열이 계약값으로 떨어지지 않는다**: 예전에는 `service_id=""` 가
    `contract.target_id` 와 **완전히 같은 행**을 냈다. 그 두 행은 구별 불가능했다.
    """
    contract = make_contract()
    driver_rows = lambda: FakeDriver(transitions=[ok_transition(0, endpoint=True)] * 2)  # noqa: E731

    derived = (
        make_runner(tmp_path / "a")
        .run(contract, driver=driver_rows(), run_id="w5q-id-4")
        .as_mart_record()
    )
    supplied = (
        make_runner(tmp_path / "b")
        .run(contract, driver=driver_rows(), run_id="w5q-id-4", service_id=contract.target_id)
        .as_mart_record()
    )

    # 같은 값이어도 **출처가 갈린다** — 파생이 틀렸을 때 어느 행이 영향을 받았는지 복원된다.
    assert derived["service_id"] == supplied["service_id"] == contract.target_id
    assert derived["service_id_provenance"] != supplied["service_id_provenance"]

    # 형태 위반은 행 자체가 없다.
    with pytest.raises(ObservationIdentityError):
        make_runner(tmp_path / "c").run(
            contract, driver=driver_rows(), run_id="w5q-id-4", service_id=""
        )


def test_identity_derivation_also_refuses_a_broken_contract_value(tmp_path: Path) -> None:
    """파생 자리도 검사한다 — 계약값이 깨져 있으면 파생값이 조용히 깨진 id 가 된다."""
    with pytest.raises(ObservationIdentityError, match=r"contract\.target_id"):
        make_runner(tmp_path).run(
            make_contract(target_id="   "),
            driver=FakeDriver(transitions=[ok_transition(0, endpoint=True)] * 2),
            run_id="w5q-id-5",
        )


def test_no_or_fallback_remains_on_the_identity_fields() -> None:
    """`Δ48` ⑤ 가 지목한 4건이 소스에서 사라졌다 — 선언이 아니라 grep 으로 본다."""
    src = (RESEARCH / "src/landing_accessibility/v3_runner/runner.py").read_text("utf-8")
    offenders = [
        line.strip()
        for line in src.splitlines()
        if ("service_id or" in line or "task_id or" in line)
    ]
    assert offenders == [], f"or fallback 이 남아 있다: {offenders}"
    # 양성 대조 — 대체 경로가 실재한다(이 grep 이 헛돌지 않는다).
    assert "_resolve_identity(" in src


def test_replay_uses_the_same_identity_rule(tmp_path: Path) -> None:
    """`run` 만 고치고 `replay` 를 두면 같은 결함이 다른 문으로 들어온다."""
    runner = make_runner(tmp_path)
    result = runner.run(
        make_contract(),
        driver=FakeDriver(transitions=[ok_transition(0, endpoint=True)] * 2),
        run_id="w5q-id-6",
    )
    manifest = result.path_manifest
    assert manifest is not None
    with pytest.raises(ObservationIdentityError, match="service_id"):
        runner.replay(
            make_contract(),
            driver=FakeDriver(transitions=[ok_transition(0, endpoint=True)] * 2),
            manifest=manifest,
            declared_sha256=result.path_manifest_sha256,
            run_id="w5q-id-7",
            service_id="",
        )


def test_the_seam_refusal_row_declares_its_identity_provenance_too() -> None:
    """`Δ48` ⑤ — 거부 행도 `service_id` 출처를 갖는다. 이 함수는 계약을 받지 않으므로
    파생 검사를 대신할 수 없고, 그 한계가 기본값과 문서에 적혀 있다."""
    key = ObservationKey(service_id="svc", task_id="task", run_id="run")
    row = seam_refusal_result(key).as_mart_record()
    assert row["service_id_provenance"] == IDENTITY_CALLER_SUPPLIED

    derived = seam_refusal_result(
        key, identity_provenance=IDENTITY_DERIVED_FROM_CONTRACT
    ).as_mart_record()
    assert derived["service_id_provenance"] == IDENTITY_DERIVED_FROM_CONTRACT

    # `R31` — 어휘 밖 값은 조용히 실리지 않는다.
    with pytest.raises(ObservationIdentityError, match="어휘 밖"):
        seam_refusal_result(key, identity_provenance="ASSUMED")


def test_the_divergence_error_can_make_its_own_observation_row() -> None:
    """`Δ47` ② — 예외를 잡은 자리에서 **행 만드는 방법을 따로 찾지 않아도** 되게 한다.

    찾아야 하면 그 자리는 결국 행을 만들지 않고, "발생하지 않았다" 와 "거부돼서
    관측하지 못했다" 가 같은 출력(행 없음)이 된다.
    """
    err = V3PathOrderDivergenceError(
        "메시지", task_id="t1", v2_order=["b", "a"], v3_order=["a", "b"]
    )
    row = err.as_observation_row(
        ObservationKey(service_id="svc", task_id="t1", run_id="r1")
    ).as_mart_record()
    assert row["path_discovery_outcome"] == PATH_DISCOVERY_SEAM_REFUSED_V2_ORDER
    assert row["policy_relative"] is True
    assert row["delta36_2_seam_status"] == "PARTIALLY_IMPLEMENTED"
    # 관측된 구조가 행에 실린다 — pilot 5 가 "어떤 구조에서 갈렸는가" 를 읽는다.
    assert "v2(min4)=['b', 'a']" in row["terminal_reason_note"]
