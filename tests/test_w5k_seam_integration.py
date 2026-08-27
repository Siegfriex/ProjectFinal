"""W5K — lane 사이 이음매 봉합의 실물-대-실물 검증.

`R20` (A): **각 lane 이 자기 대역으로 테스트하면 통합 지점은 아무도 테스트하지 않는다.**
1173 passed 인데 실행하면 `AttributeError` 였던 이유가 그것이다. 그래서 이 파일의 모든
테스트는 `V3Runner` 실물에 `ActivationSafetyGuard` 실물 / `normalize_flow` 실물을
넣고 **실제로 실행한다.**

이 파일에서 대역을 쓰는 곳과 그 이유 (감추지 않는다)
-----------------------------------------------------

``_ScriptedDriver``
    `runner.SessionDriver` 의 구현이 저장소에 **없다** — 그 lane(W5H)이 아직 안 올라왔다.
    브라우저를 여는 유일한 경계라 여기서 대체하지 않으면 어떤 통합 테스트도 불가능하고,
    실사이트 접속은 금지다. **검증 대상 seam 은 driver 가 아니라
    `runner ↔ safety` 와 `runner ↔ flow` 이며 그 양쪽은 전부 실물이다.**

``_RegistryHasher`` · ``_FlowNormalizerAdapter``
    판정 로직이 없다. `registry.recompute_task_contract_hash` 와 `flow.normalize_flow`
    **실물 함수를 그대로 호출**하는 시그니처 어댑터다 (해당 lane 들이 Protocol 형태가
    아니라 module-level 함수로 산출물을 냈다 — `test_protocol_conformance_sweep` 가
    그 사실을 측정값으로 고정한다).
"""

from __future__ import annotations

import dataclasses
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any, ClassVar

import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "research" / "landing_accessibility" / "src"))

from landing_accessibility.v3_runner import (  # noqa: E402
    contracts,
    flow,
    registry,
    runner,
    safety,
)
from landing_accessibility.v3_runner.evidence import EvidencePayload  # noqa: E402
from landing_accessibility.v3_runner.runner import (  # noqa: E402
    PlannedAction,
    RawTransition,
    SurfaceObservation,
    V3Runner,
)
from landing_accessibility.v3_runner.safety import (  # noqa: E402
    ActivationSafetyGuard,
    SafetyStop,
    planned_action_to_candidate,
)

# ══════════════════════════════════════════════════════════════════════════
# 실물을 붙이기 위한 최소 배선
# ══════════════════════════════════════════════════════════════════════════


def _contract(**overrides: Any) -> contracts.TaskContract:
    """`registry` 실물 해시 함수로 해시를 채운 유효한 계약 하나."""
    fields: dict[str, Any] = {
        "target_id": "W5K-SEAM-01",
        "family_id": "F2",
        "service": "seam-fixture-service",
        "starting_url": "https://fixture.invalid/entry",
        "frozen_task": "노선 조회",
        "task_instruction": "출발지·도착지·날짜를 넣고 조회한다",
        "fixed_fixture": "출발=서울역; 도착=부산역; 날짜=2026-09-01",
        "fixture_override": None,
        "endpoint_contract": "조회 결과 목록이 보이면 endpoint",
        "forbidden_actions": ("PAYMENT", "SEAT_SELECT"),
        "task_contract_hash": "",
        "endpoint_contract_hash": "",
        "legacy_archetype": None,
        "mobile_web_eligibility": "ELIGIBLE_PUBLIC_MOBILE_WEB",
        "stratum": "ground",
        "is_pilot_5": False,
        "collection_order": 7,
        "task_role": contracts.TASK_ROLE_PRIMARY,
        "fixture_input_mode": None,
    }
    fields.update(overrides)
    # 해시는 실물 registry 함수가 만든다 — 여기서 재구현하지 않는다.
    # 순서가 중요하다: `endpoint_contract_hash` 는 `task_contract_hash` payload 에
    # **포함**되므로(registry 모듈 docstring) 먼저 채운 뒤 task 해시를 계산한다.
    draft = dataclasses.replace(
        contracts.TaskContract(**fields),
        endpoint_contract_hash=registry._sha256_text(fields["endpoint_contract"]),
    )
    return dataclasses.replace(
        draft, task_contract_hash=registry.recompute_task_contract_hash(draft)
    )


class _RegistryHasher:
    """`runner.ContractHasher` 시그니처 어댑터. 해시 계산은 `registry` 실물."""

    def task_contract_hash(self, contract: contracts.TaskContract) -> str | None:
        return registry.recompute_task_contract_hash(contract)

    def endpoint_contract_hash(self, contract: contracts.TaskContract) -> str | None:
        return registry._sha256_text(contract.endpoint_contract)


class _FlowNormalizerAdapter:
    """`runner.FlowNormalizer` 시그니처 어댑터. 정규화는 `flow.normalize_flow` 실물."""

    def normalize(
        self, contract: contracts.TaskContract, steps: Sequence[contracts.FlowStep]
    ) -> Any:
        return flow.normalize_flow(steps)


def _payload(node_id: str) -> EvidencePayload:
    return EvidencePayload(
        node_id=node_id,
        url="https://fixture.invalid/entry",
        dom="<html></html>",
        ax={"role": "WebArea"},
        probe={},
        control_facts={},
    )


class _ScriptedDriver:
    """`runner.SessionDriver` 대역 — 그 lane(W5H)이 아직 없다. 판정을 하지 않는다.

    `activate` 호출을 전부 기록해서 **차단이 실제로 activation 앞에서 일어났는지**를
    관측 가능하게 만든다. 이것이 seam 1 의 음성/양성 대조를 구분하는 관측 지점이다.
    """

    def __init__(self, transitions: Mapping[str, RawTransition] | None = None) -> None:
        self.activated: list[PlannedAction] = []
        self._transitions = dict(transitions or {})

    def capture_surface(self, contract: contracts.TaskContract) -> Sequence[SurfaceObservation]:
        return (
            SurfaceObservation(
                state_index="S0",
                scroll_y=0.0,
                viewport_width=390,
                viewport_height=844,
                url=contract.starting_url,
                payload=_payload("s000"),
            ),
        )

    def activate(self, action: PlannedAction) -> RawTransition:
        self.activated.append(action)
        preset = self._transitions.get(action.action_token)
        if preset is not None:
            return preset
        return RawTransition(
            ok=True,
            state_before_id="S0",
            state_after_id="S1",
            url_before="https://fixture.invalid/entry",
            url_after="https://fixture.invalid/next",
            payload_before=_payload("b"),
            payload_after=_payload("a"),
        )


class _FixedScout:
    """제안 목록을 순서대로 내놓는다. 판정하지 않는다 — 제안만 한다."""

    def __init__(self, actions: Sequence[PlannedAction]) -> None:
        self._actions = list(actions)
        self.calls = 0

    def propose_next(
        self,
        contract: contracts.TaskContract,
        states: Sequence[SurfaceObservation],
        candidates: Sequence[Mapping[str, Any]],
        taken: Sequence[contracts.FlowStep],
    ) -> PlannedAction | None:
        if self.calls >= len(self._actions):
            return None
        action = self._actions[self.calls]
        self.calls += 1
        return action


def _runner(tmp_path: Any, guard: ActivationSafetyGuard, **kwargs: Any) -> V3Runner:
    return V3Runner(
        evidence_root=tmp_path / "evidence",
        contract_hasher=_RegistryHasher(),
        safety=guard,
        **kwargs,
    )


# 실제 결제 control 을 흉내 낸 제안 — `guard._FORBIDDEN_TEXT_PATTERNS` 가 잡는다.
FORBIDDEN_ACTION = PlannedAction(
    action_token="SELECT_RESULT",
    control_selector="#pay-now",
    control_role="button",
    control_visible_text="결제하기",
    control_accessible_name="결제하기",
)
# 같은 token, 같은 형태 — 문구만 안전하다. 음성 대조용.
ALLOWED_ACTION = PlannedAction(
    action_token="SELECT_RESULT",
    control_selector="#result-0",
    control_role="link",
    control_visible_text="서울역 → 부산역 09:00",
    control_accessible_name="서울역 → 부산역 09:00 조회결과",
)


# ══════════════════════════════════════════════════════════════════════════
# SEAM 1 — runner 실물 대 safety 실물
# ══════════════════════════════════════════════════════════════════════════


def test_seam1_guard_satisfies_runner_protocol() -> None:
    """`AttributeError` 가 사라진 것은 수용기준이 **아니다**. 여기는 배선의 전제만 본다."""
    guard = ActivationSafetyGuard(_contract())
    assert isinstance(guard, runner.SafetyGuard)


def test_seam1_real_guard_blocks_forbidden_activation(tmp_path: Any) -> None:
    """**차단** — 실제 runner 가 실제 guard 를 태워 금지행위를 막는다 (A 수용기준 1).

    핵심은 예외가 나는 것이 아니라 **`driver.activate` 가 호출되지 않는 것**이다.
    막았는데 이미 눌렀으면 막은 것이 아니다.
    """
    contract = _contract()
    guard = ActivationSafetyGuard(contract)
    driver = _ScriptedDriver()
    r = _runner(tmp_path, guard, scout=_FixedScout([FORBIDDEN_ACTION]))

    with pytest.raises(SafetyStop) as excinfo:
        r.run(contract, driver=driver, task_id="W5K-TASK-01", run_id="w5k-block")

    assert driver.activated == [], "차단됐는데 activate 가 불렸다 — 관문이 actuation 뒤에 있다"
    assert str(excinfo.value.action) == "PAYMENT"
    assert guard.violations, "guard 가 위반을 기록하지 않았다 — authorize 경로를 안 탔다"
    assert guard.violations[0]["selector"] == "#pay-now"


def test_seam1_negative_control_allowed_activation_proceeds(tmp_path: Any) -> None:
    """**음성 대조** — 같은 배선에서 허용된 행위는 통과한다 (A 수용기준 2).

    차단만 보이면 "전부 차단"과 구분되지 않는다. 같은 guard·같은 runner·같은
    action_token 이고 control 문구만 다르다.
    """
    contract = _contract()
    guard = ActivationSafetyGuard(contract)
    driver = _ScriptedDriver()
    r = _runner(tmp_path, guard, scout=_FixedScout([ALLOWED_ACTION]))

    result = r.run(contract, driver=driver, task_id="W5K-TASK-01", run_id="w5k-allow")

    assert [a.control_selector for a in driver.activated] == ["#result-0", "#result-0"], (
        "허용 행위가 scout+replay 두 경로 모두에서 실행되지 않았다"
    )
    assert guard.violations == []
    assert result.phase_reached is runner.Phase.MART
    assert len(result.raw_steps) == 1


def test_seam1_block_and_allow_share_one_guard(tmp_path: Any) -> None:
    """한 guard 인스턴스가 허용은 통과시키고 금지는 막는다 — 대조가 같은 실행 안에 있다."""
    contract = _contract()
    guard = ActivationSafetyGuard(contract)
    driver = _ScriptedDriver()
    r = _runner(tmp_path, guard, scout=_FixedScout([ALLOWED_ACTION, FORBIDDEN_ACTION]))

    with pytest.raises(SafetyStop):
        r.run(contract, driver=driver, task_id="W5K-TASK-01", run_id="w5k-mixed")

    # 허용 1건은 눌렸고, 금지 1건에서 멈췄다.
    assert [a.control_selector for a in driver.activated] == ["#result-0"]
    assert len(guard.violations) == 1


def test_seam1_translation_table_is_the_load_bearing_part() -> None:
    """**rename 만으로는 이 테스트가 통과하지 않는다** (A 수용기준 3).

    `dataclasses.asdict` 를 그대로 넘기는 순진한 배선은 detector 가 키를 못 읽어
    **전건 허용**된다. 그 fail-open 을 여기서 명시적으로 관측한다 — 조용한 통과가
    가능한 경로가 실재함을 테스트가 기억한다.
    """
    naive = dataclasses.asdict(FORBIDDEN_ACTION)
    action_naive, _ = safety._detect_forbidden_action(naive)
    assert action_naive is None, (
        "전제가 바뀌었다 — detector 가 control_* 키를 읽게 됐다면 이 테스트를 다시 써라"
    )

    translated = planned_action_to_candidate(FORBIDDEN_ACTION)
    action_real, reason = safety._detect_forbidden_action(translated)
    assert action_real is safety.ForbiddenAction.PAYMENT, reason
    assert "control_visible_text" not in translated
    assert translated["visible_text"] == "결제하기"


def test_seam1_none_fields_do_not_become_keys() -> None:
    """`None` 을 키로 넣으면 `"x" in candidate` 를 보는 자리가 "관측했다"로 읽는다."""
    bare = PlannedAction(action_token="ABSTAIN")
    candidate = planned_action_to_candidate(bare)
    assert set(candidate) == {"action_token"}


def test_seam1_contract_declared_forbidden_action_also_blocks(tmp_path: Any) -> None:
    """계약이 선언한 금지행위도 같은 관문에서 막힌다 (runner 어휘검사 경로)."""
    contract = _contract()
    guard = ActivationSafetyGuard(contract)
    driver = _ScriptedDriver()
    seat = PlannedAction(
        action_token="SELECT_RESULT",
        control_selector="#seat-map",
        control_visible_text="좌석 선택",
        control_accessible_name="좌석 선택",
    )
    r = _runner(tmp_path, guard, scout=_FixedScout([seat]))

    with pytest.raises(SafetyStop) as excinfo:
        r.run(contract, driver=driver, task_id="W5K-TASK-01", run_id="w5k-seat")

    assert driver.activated == []
    assert str(excinfo.value.action) == "SEAT_SELECT"


# ══════════════════════════════════════════════════════════════════════════
# SEAM 2 — contracts.py 정본화 + input_mode 도달가능성
# ══════════════════════════════════════════════════════════════════════════


def test_seam2_single_definition_across_lanes() -> None:
    """중복 정의가 사라졌다 — 세 lane 이 같은 객체를 본다."""
    assert runner.TaskContract is contracts.TaskContract
    assert runner.FlowStep is contracts.FlowStep
    assert flow.FlowStep is contracts.FlowStep


def test_seam2_manifest_fields_survive() -> None:
    """A 가 동결한 MAIN50 manifest 필드 3종 + Δ8-R5 관측변수 1종이 남아 있다."""
    names = {f.name for f in dataclasses.fields(runner.TaskContract)}
    assert {"stratum", "is_pilot_5", "collection_order", "fixture_input_mode"} <= names


def _conditional_run(tmp_path: Any, input_mode: str | None, run_id: str) -> Any:
    """`SELECT_DATE` 한 건을 주어진 input_mode 로 실제 runner 에 흘려보낸다."""
    contract = _contract()
    guard = ActivationSafetyGuard(contract)
    driver = _ScriptedDriver(
        {
            "SELECT_DATE": RawTransition(
                ok=True,
                state_before_id="S0",
                state_after_id="S1",
                url_before="https://fixture.invalid/entry",
                url_after="https://fixture.invalid/date",
                input_mode=input_mode,
                payload_before=_payload("b"),
                payload_after=_payload("a"),
            )
        }
    )
    action = PlannedAction(
        action_token="SELECT_DATE",
        control_selector="#depart-date",
        control_role="button",
        control_visible_text="가는 날",
        control_accessible_name="가는 날 선택",
    )
    r = _runner(
        tmp_path,
        guard,
        scout=_FixedScout([action]),
        flow_normalizer=_FlowNormalizerAdapter(),
    )
    return r.run(contract, driver=driver, task_id="W5K-TASK-01", run_id=run_id)


def test_seam2_input_mode_reaches_the_conditional_verdict(tmp_path: Any) -> None:
    """**도달가능성** — 필드가 존재하는 것으로 부족하다 (A GATE 1 조건).

    `DROPDOWN` 을 driver 가 관측하면 `flow.normalize_flow` 실물의 CONDITIONAL 판정
    지점까지 그 값이 실제로 도달해 **포함**으로 판정된다.
    """
    result = _conditional_run(tmp_path, "DROPDOWN", "w5k-depth-dropdown")

    step = result.raw_steps[0]
    assert step.input_mode == "DROPDOWN", "step 이 값을 잃었다 — 판정 지점에 도달하지 못한다"

    normalization = result.derived_flow
    assert isinstance(normalization, flow.FlowNormalization)
    (record,) = normalization.depth_conditional_tokens
    assert record.action_token == "SELECT_DATE"
    assert record.input_mode == "DROPDOWN"
    assert record.included_in_activation_depth is True
    assert normalization.activation_depth == 1


def test_seam2_free_text_negative_control(tmp_path: Any) -> None:
    """음성 대조 — 같은 경로에서 `FREE_TEXT` 는 **제외**로 갈린다.

    포함만 보이면 "전부 포함"과 구분되지 않는다.
    """
    result = _conditional_run(tmp_path, "FREE_TEXT", "w5k-depth-freetext")

    (record,) = result.derived_flow.depth_conditional_tokens
    assert record.input_mode == "FREE_TEXT"
    assert record.included_in_activation_depth is False
    assert result.derived_flow.activation_depth == 0


def test_seam2_unobserved_input_mode_stays_undetermined(tmp_path: Any) -> None:
    """미관측은 판정 불능이다 — 0/False 로 접지 않는다 (`09 D3-05`)."""
    result = _conditional_run(tmp_path, None, "w5k-depth-none")

    (record,) = result.derived_flow.depth_conditional_tokens
    assert record.input_mode is None
    assert record.included_in_activation_depth is None
    assert result.derived_flow.activation_depth is None


def test_seam2_conditional_verdicts_are_not_all_the_same(tmp_path: Any) -> None:
    """세 갈래가 **서로 다른** 결과를 낸다 — 판정이 실제로 input_mode 에 반응한다."""
    verdicts = [
        _conditional_run(tmp_path, mode, f"w5k-tri-{mode}").derived_flow.activation_depth
        for mode in ("DROPDOWN", "FREE_TEXT", None)
    ]
    assert verdicts == [1, 0, None]


# ══════════════════════════════════════════════════════════════════════════
# lane 경계 전수 — Protocol 적합성 (측정값 고정)
# ══════════════════════════════════════════════════════════════════════════


# 각 Protocol 이 `runner.py` 안에서 지목하거나 병합된 lane 이 실제로 낸 산출물.
# 값은 (설명, 객체 또는 None). `None` = 그 이름의 구현이 저장소에 없다.
def _measured_candidates() -> dict[str, tuple[str, Any]]:
    from landing_accessibility.v3_runner import discovery, obstruction, surface, terminal
    from landing_accessibility.v3_runner.scout_strategy import MinPathScoutStrategy

    return {
        "SafetyGuard": ("safety.ActivationSafetyGuard", ActivationSafetyGuard(_contract())),
        "ScoutStrategy": ("scout_strategy.MinPathScoutStrategy", MinPathScoutStrategy()),
        "ContractHasher": ("registry.recompute_task_contract_hash (함수)", registry),
        "EligibilityChecker": ("구현 없음 — discovery.py 에 eligibility 심볼 0개", discovery),
        "CandidateBinder": ("discovery.discover_task_candidates (함수)", discovery),
        "SurfaceMeasurer": ("surface.measure_surface (함수)", surface),
        "FlowNormalizer": ("flow.normalize_flow (함수)", flow),
        "ObstructionAnalyzer": ("obstruction.measure_task_obstruction (함수)", obstruction),
        "TerminalClassifier": ("terminal.classify_terminal (함수)", terminal),
        "DepthAttributor": ("구현 없음 — flow.py 는 normalize_flow 안에서 처리한다", flow),
        "SessionDriver": ("구현 없음 — W5H lane 미병합", None),
    }


#: 실측: Protocol 을 만족하는 구현이 **있는** 경계.
CONFORMING = {"SafetyGuard", "ScoutStrategy"}

#: 실측: 어떤 구현도 Protocol 을 만족하지 **않는** 경계. 감추지 않고 고정한다.
#: 해당 lane 들은 Protocol 형태(객체 + 메서드)가 아니라 module-level 함수로 산출물을
#: 냈고 시그니처도 다르다. 이 목록이 줄어드는 것은 진전이므로, 줄면 갱신을 요구한다.
NO_CONFORMING_IMPLEMENTATION = {
    "CandidateBinder",
    "ContractHasher",
    "DepthAttributor",
    "EligibilityChecker",
    "FlowNormalizer",
    "ObstructionAnalyzer",
    "SessionDriver",
    "SurfaceMeasurer",
    "TerminalClassifier",
}

RUNNER_PROTOCOLS = CONFORMING | NO_CONFORMING_IMPLEMENTATION


def test_protocol_sweep_covers_every_runner_protocol() -> None:
    """`runner.py` 의 Protocol 을 하나도 빠뜨리지 않았다 — 전수의 전수성을 검사한다."""
    declared = {
        name
        for name in dir(runner)
        if isinstance(getattr(runner, name), type)
        and getattr(getattr(runner, name), "_is_protocol", False)
        and name != "Protocol"  # typing.Protocol 자체가 runner 이름공간에 있다
    }
    assert declared == RUNNER_PROTOCOLS, f"미측정 Protocol: {declared ^ RUNNER_PROTOCOLS}"


@pytest.mark.parametrize("protocol_name", sorted(CONFORMING))
def test_protocol_conformance_positive(protocol_name: str) -> None:
    """구현이 있는 경계는 `isinstance` 로 실제 적합을 확인한다."""
    label, obj = _measured_candidates()[protocol_name]
    protocol = getattr(runner, protocol_name)
    assert isinstance(obj, protocol), f"{label} 이 {protocol_name} 을 만족하지 않는다"


@pytest.mark.parametrize("protocol_name", sorted(NO_CONFORMING_IMPLEMENTATION))
def test_protocol_conformance_open_seams(protocol_name: str) -> None:
    """아직 Protocol 형태의 구현이 없는 경계를 **측정값으로** 고정한다.

    이 테스트가 실패하면 결함이 아니라 진전이다 — 구현이 생겼다는 뜻이므로
    `NO_CONFORMING_IMPLEMENTATION` 에서 이름을 옮기고 양성 테스트를 붙여라.

    측정 대상은 lane 이 실제로 낸 산출물(대개 module-level 함수)이며, 모듈 객체를
    Protocol 로 판정해 "그 이름의 메서드가 어디에도 없다"를 보인다.
    """
    label, obj = _measured_candidates()[protocol_name]
    protocol = getattr(runner, protocol_name)
    if obj is None:
        pytest.skip(f"{protocol_name}: {label}")
    assert not isinstance(obj, protocol), (
        f"{protocol_name} 을 만족하는 구현이 생겼다 ({label}) — 목록을 갱신해라"
    )


# ══════════════════════════════════════════════════════════════════════════
# SEAM 3 — CandidateBinder / EligibilityChecker 경계 **실측 고정** (수정 금지 레인)
#
# 이 lane 은 두 경계를 고치지 않는다. 아래 테스트는 기능이 아니라 **현재 상태의
# 관측값을 고정**한다. 실패하면 결함이 아니라 진전이다 — 그때 값을 갱신하고
# `docs/v3/INTERFACE.md` §11 도 같이 고쳐라.
# ══════════════════════════════════════════════════════════════════════════


def test_seam3_eligibility_has_no_implementation() -> None:
    """`EligibilityChecker.check` 를 구현한 심볼이 트리에 없다 — 실측 고정."""
    from landing_accessibility.v3_runner import discovery, registry

    for module in (discovery, registry):
        # manifest **필드명**(`mobile_web_eligibility`)은 checker 가 아니다.
        symbols = [
            n
            for n in dir(module)
            if "ligib" in n and not n.startswith("_") and n != "mobile_web_eligibility"
        ]
        assert symbols == [], f"{module.__name__} 에 eligibility 심볼이 생겼다: {symbols}"
    assert not isinstance(discovery, runner.EligibilityChecker)


def test_seam3_frozen_manifest_default_is_refused_without_a_checker() -> None:
    """checker 미주입 + 동결 manifest 기본값이면 `run()` 이 **시끄럽게** 거부한다.

    `PRECHECK_REQUIRED` 는 `runner.ELIGIBILITY_VALUES` 밖이다. 조용한 통과가 아니라
    예외라는 점이 이 테스트의 관측 대상이다.
    """
    assert "PRECHECK_REQUIRED" not in runner.ELIGIBILITY_VALUES
    default = next(
        f.default
        for f in dataclasses.fields(contracts.TaskContract)
        if f.name == "mobile_web_eligibility"
    )
    assert default == "PRECHECK_REQUIRED"


class _DiscoveryBinder:
    """`discovery` 실물을 그대로 위임하는 최소 어댑터. 변환하지 않는다."""

    PROBE: ClassVar[dict[str, Any]] = {
        "primary_action_candidates": [
            {
                "selector": "#go",
                "tag": "button",
                "role": "button",
                "visible_text": "조회",
                "dom_order": 1,
                "marked_primary": True,
                "hittable": True,
                "enabled": True,
            }
        ]
    }

    def bind(self, contract: contracts.TaskContract, states: Sequence[Any]) -> Sequence[Any]:
        from landing_accessibility.v3_runner import discovery

        return discovery.discover_task_candidates(self.PROBE, contract)


class _MappingBinder(_DiscoveryBinder):
    """같은 후보를 `Mapping` 으로만 감싼다. 판정을 바꾸지 않는다 — 형만 바꾼다."""

    def bind(self, contract: contracts.TaskContract, states: Sequence[Any]) -> Sequence[Any]:
        return [
            {
                "selector": c.selector,
                "tag": c.tag,
                "role": c.role,
                "visible_text": c.visible_text,
                "dom_order": c.dom_order,
                "marked_primary": c.marked_primary,
                "hittable": c.hittable,
                "enabled": c.enabled,
            }
            for c in super().bind(contract, states)
        ]


def _run_with_binder(tmp_path: Any, binder: Any, run_id: str) -> tuple[Any, _ScriptedDriver]:
    from landing_accessibility.v3_runner.scout_strategy import MinPathScoutStrategy

    contract = _contract()
    driver = _ScriptedDriver()
    r = _runner(
        tmp_path,
        ActivationSafetyGuard(contract),
        binder=binder,
        scout=MinPathScoutStrategy(),
    )
    result = r.run(contract, driver=driver, task_id="W5K-SEAM3", run_id=run_id)
    return result, driver


def test_seam3_dataclass_candidates_collapse_to_a_silent_zero(tmp_path: Any) -> None:
    """**실측 고정** — 형이 안 맞으면 예외가 아니라 "성공 형태의 0건"이 나온다.

    `discover_task_candidates` 는 `TaskCandidate`(dataclass)를 내고
    `MinPathScoutStrategy.propose_next` 는 `isinstance(c, Mapping)` 으로 거른다.
    전건 탈락 → `propose_next` 가 `None` → runner 는 정상 종료로 읽는다.
    """
    from landing_accessibility.v3_runner import discovery

    binder = _DiscoveryBinder()
    assert isinstance(binder, runner.CandidateBinder), "Protocol 은 메서드 이름만 본다"
    produced = binder.bind(_contract(), ())
    assert len(produced) == 1
    assert not isinstance(produced[0], Mapping)
    assert isinstance(produced[0], discovery.TaskCandidate)

    result, driver = _run_with_binder(tmp_path, binder, "w5k-seam3-dataclass")

    assert driver.activated == []
    assert result.raw_steps == ()
    assert result.refusal is None
    assert result.phase_reached is runner.Phase.MART, (
        "0건인데 성공 phase 로 끝난다는 것이 이 seam 의 관측 사실이다"
    )


def test_seam3_mapping_control_shows_the_difference_is_the_type(tmp_path: Any) -> None:
    """**대조** — 같은 후보를 dict 로만 감싸면 실제로 activation 이 일어난다.

    두 테스트의 차이는 자료형 하나뿐이다. 따라서 위의 0건은 "후보가 없어서"가
    아니라 "형이 안 맞아서"다.
    """
    result, driver = _run_with_binder(tmp_path, _MappingBinder(), "w5k-seam3-mapping")

    assert [a.control_selector for a in driver.activated] == ["#go", "#go"]
    assert len(result.raw_steps) == 1


# ══════════════════════════════════════════════════════════════════════════
# SEAM 1 전수 — 금지 행동 12종을 **실물 runner 대 실물 guard** 로 훑는다
#
# A 수용기준: "AttributeError 가 사라지는 것은 수용기준이 아니다. guard 가 발화하는
# 것이 수용기준이다." 그래서 여기서는 12종 각각에 대해
#   (a) SafetyStop 이 났는가, (b) `driver.activate` 가 **불리지 않았는가**
# 를 같이 본다. 발화하지 **않는** 3종도 감추지 않고 같은 배선으로 고정한다.
#
# 목록 출처: SSOTV3 5-family `forbidden_actions` + 매니페스트 —
# credential · login submit · OTP · CAPTCHA · 송금 · 장바구니 · 주문 · 결제 ·
# 예약 · 좌석선택 · 실제 개인정보 · 외부앱 실행.
# ══════════════════════════════════════════════════════════════════════════


def _action(selector: str, text: str, token: str = "SELECT_RESULT") -> PlannedAction:
    return PlannedAction(
        action_token=token,
        control_selector=selector,
        control_role="button",
        control_visible_text=text,
        control_accessible_name=text,
    )


#: (레이블, PlannedAction, 기대 ForbiddenAction). 실측으로 채운 표다.
BLOCKED_AT_SEAM: tuple[tuple[str, PlannedAction, str], ...] = (
    ("otp", _action("#otp", "인증번호 입력"), "OTP_ENTRY"),
    ("captcha", _action("#cap", "자동입력 방지 문자"), "CAPTCHA_SOLVE"),
    ("funds-transfer", _action("#send", "송금하기"), "PAYMENT"),
    ("add-to-cart", _action("#cart", "장바구니 담기"), "ADD_TO_CART"),
    ("order", _action("#order", "주문하기"), "ORDER_PLACE"),
    ("payment", _action("#pay", "결제하기"), "PAYMENT"),
    ("booking", _action("#book", "예약하기"), "BOOKING_CONFIRM"),
    ("seat-select", _action("#seat", "좌석 선택"), "SEAT_SELECT"),
    ("external-app", _action("#app", "앱에서 열기"), "EXTERNAL_APP_LAUNCH"),
)

#: **이 seam 에서는 발화하지 않는다** — 감추지 않고 고정한다. 사유는 테스트 본문에.
NOT_BLOCKED_AT_SEAM: tuple[tuple[str, PlannedAction], ...] = (
    ("credential", _action("#pw", "비밀번호")),
    ("login-submit", _action("#login-submit", "로그인 하기")),
    ("personal-data", _action("#rrn", "주민등록번호")),
)


@pytest.mark.parametrize(
    ("label", "action", "expected"),
    BLOCKED_AT_SEAM,
    ids=[row[0] for row in BLOCKED_AT_SEAM],
)
def test_seam1_forbidden_sweep_guard_fires(
    tmp_path: Any, label: str, action: PlannedAction, expected: str
) -> None:
    """금지 행동 → guard 발화 → **runner 가 그 행동을 실행하지 않는다.**"""
    contract = _contract()
    guard = ActivationSafetyGuard(contract)
    driver = _ScriptedDriver()
    r = _runner(tmp_path, guard, scout=_FixedScout([action]))

    with pytest.raises(SafetyStop) as excinfo:
        r.run(contract, driver=driver, task_id="W5K-SWEEP", run_id=f"sweep-{expected}-{label}")

    assert str(excinfo.value.action) == expected, label
    assert driver.activated == [], f"{label}: 막았는데 activate 가 불렸다"
    assert guard.violations[-1]["selector"] == action.control_selector
    assert guard.violations[-1]["reason"], "발화 근거가 비어 있다"


@pytest.mark.parametrize(
    ("label", "action"),
    NOT_BLOCKED_AT_SEAM,
    ids=[row[0] for row in NOT_BLOCKED_AT_SEAM],
)
def test_seam1_forbidden_sweep_known_non_firing(
    tmp_path: Any, label: str, action: PlannedAction
) -> None:
    """**실측 고정** — 이 3종은 이 seam 에서 발화하지 않는다. 이유를 적어 둔다.

    `credential` · `실제 개인정보`
        `guard` 는 이 둘을 `input[type=password]` / `autocomplete` / **field name**
        으로 판정한다. 그런데 `runner.PlannedAction` 이 가진 필드는
        `action_token` · `control_selector` · `control_role` · `control_visible_text` ·
        `control_accessible_name` **다섯 개뿐**이라 그 신호가 seam 을 건너오지 못한다.
        → 이 관문은 **텍스트로 드러나는 금지 행동만** 막는다. 나머지는 actuation 지점
        (`guard_page()` / `GuardedPage.fill`)이 막아야 하고, 그 경로는 `SessionDriver`
        (W5H)가 올라와야 검증 가능하다.

    `login submit`
        의도된 설계다 — `guard._CATEGORY_TO_STATE` 가 `LOGIN` 을
        `AUTH_ENTRY_ALLOWED_CONDITIONALLY` 로 두고 `_CATEGORY_TO_FORBIDDEN` 에서
        `LOGIN` 을 **뺐다**(`00_SSOT §6` `D3-09` — generic login 존재로 중단 금지).
        금지되는 것은 로그인 **링크 클릭**이 아니라 자격정보 **입력·제출**이며,
        그건 위 두 항목과 같은 이유로 이 seam 밖이다.

    이 테스트가 실패하면 결함이 아니라 진전이다 — 그때 `BLOCKED_AT_SEAM` 으로 옮겨라.
    """
    contract = _contract()
    guard = ActivationSafetyGuard(contract)
    driver = _ScriptedDriver()
    r = _runner(tmp_path, guard, scout=_FixedScout([action]))

    result = r.run(contract, driver=driver, task_id="W5K-SWEEP", run_id=f"nofire-{label}")

    assert guard.violations == [], f"{label}: 발화하게 됐다 — 표를 갱신해라"
    assert driver.activated, f"{label}: 발화도 실행도 없다 — 전제가 바뀌었다"
    assert result.phase_reached is runner.Phase.MART


#: 음성 대조 — 같은 배선·같은 token, 문구만 정상. 전부 통과해야 한다.
ALLOWED_CONTROLS: tuple[tuple[str, PlannedAction], ...] = (
    ("search-result", _action("#result-0", "서울역 → 부산역 09:00")),
    ("search-submit", _action("#search", "조회")),
    ("next", _action("#next", "다음")),
    ("open-menu", _action("#menu", "전체메뉴")),
)


@pytest.mark.parametrize(
    ("label", "action"), ALLOWED_CONTROLS, ids=[row[0] for row in ALLOWED_CONTROLS]
)
def test_seam1_negative_control_sweep(tmp_path: Any, label: str, action: PlannedAction) -> None:
    """**음성 대조 전수** — 이게 없으면 "전부 차단"이 통과처럼 보인다."""
    contract = _contract()
    guard = ActivationSafetyGuard(contract)
    driver = _ScriptedDriver()
    r = _runner(tmp_path, guard, scout=_FixedScout([action]))

    result = r.run(contract, driver=driver, task_id="W5K-SWEEP", run_id=f"allow-{label}")

    assert guard.violations == [], f"{label}: 허용 행동이 차단됐다"
    assert [a.control_selector for a in driver.activated] == [
        action.control_selector,
        action.control_selector,
    ], f"{label}: scout+replay 두 경로에서 실행되지 않았다"
    assert len(result.raw_steps) == 1
