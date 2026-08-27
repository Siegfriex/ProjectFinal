"""W5F — v3 runner orchestration + evidence package 방출.

## 이 파일이 증명하려는 것

수집기 테스트가 쉽게 빠지는 함정은 **"돌았다"를 "맞게 돌았다"로 세는 것**이다. 그래서 여기서는
성공 경로만 보지 않고, 거부되어야 할 것이 실제로 거부되는지를 같은 비중으로 본다. 해시 검증
3종은 전부 **양성 대조**(정상 해시는 통과)를 함께 둔다 — 그러지 않으면 "무조건 거부하는 코드"도
같은 초록불을 받는다(`무결과 검증엔 대조군이 필요하다`).

`REPLAY_BROKEN` 은 값이 기록되는지만 보지 않는다. `03 §5` 가 금지한 것은 **자유탐색으로의 조용한
대체**이므로, scout spy 의 호출횟수 0 을 함께 확인한다. 값은 맞는데 뒤에서 재탐색이 돌았다면
그 관측은 frozen path 의 관측이 아니다.

derived 위임도 마찬가지로 "호출됐다"에서 멈추지 않는다. fake 가 돌려준 **sentinel 객체가 결과에
그대로(identity 비교) 실렸는지**, 그리고 경계 구현을 빼면 그 자리가 `None` 이 되는지를 함께 본다.
runner 안에 대체 계산이 있으면 후자가 `None` 이 아니게 된다.
"""

from __future__ import annotations

import json
import sys
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest

REPO = Path(__file__).resolve().parents[1]
RESEARCH = REPO / "research" / "landing_accessibility"
sys.path.insert(0, str(RESEARCH / "src"))

from landing_accessibility.v3_runner.evidence import (  # noqa: E402
    CoordinateDropError,
    DenominatorError,
    DepthAttributionEvidenceError,
    EvidenceOverwriteError,
    EvidencePayload,
    EvidenceRunWriter,
    EvidenceSlot,
    InlinedBinaryError,
    LayerQualificationError,
    ManifestLinkageError,
    ObservationKey,
    Replacement,
    ReplacementLedger,
    RunSealedError,
    assert_coordinates_preserved,
    assert_depth_attribution_evidenced,
    assert_layer_qualified,
    build_denominator_chain,
    build_retention_manifest,
    denominator_for_metric,
    load_evidence_manifest,
    qualified_layer_text,
    sha256_of_file,
    verify_denominator_chain,
    verify_evidence_run,
    verify_manifest_linkage,
    verify_retention_manifest,
)
from landing_accessibility.v3_runner.runner import (  # noqa: E402
    CANONICAL_ACTION_TOKENS,
    DEPTH_CONDITIONAL_TOKENS,
    DEPTH_IN_TOKENS,
    DEPTH_OUT_TOKENS,
    ContractHashMismatchError,
    FlowStep,
    PathManifestHashMismatchError,
    Phase,
    PlannedAction,
    ProhibitedActionError,
    RawTransition,
    ReplayStatus,
    RunnerError,
    ScoutBudget,
    SurfaceObservation,
    TaskContract,
    V3Runner,
    build_family_aggregate,
    build_path_manifest,
    path_manifest_sha256,
)

# ---------------------------------------------------------------------------
# fake 경계 구현 — 다른 lane 의 파일은 아직 없다. Protocol 로만 붙인다.
# ---------------------------------------------------------------------------

TASK_HASH = "a" * 64
ENDPOINT_HASH = "b" * 64


def make_contract(**overrides: Any) -> TaskContract:
    base = TaskContract(
        target_id="svc_f2_0003",
        family_id="F2",
        service="svc_f2_0003",
        starting_url="https://fixture.invalid/f2/0003",
        frozen_task="t_f2_item_detail",
        task_instruction="상품 검색 후 상품 상세 진입",
        fixed_fixture="fixture_f2_query_v1",
        fixture_override=None,
        endpoint_contract="상품명과 가격이 확인되는 최초 상태",
        forbidden_actions=("SELECT_DATE",),
        task_contract_hash=TASK_HASH,
        endpoint_contract_hash=ENDPOINT_HASH,
        legacy_archetype="ITEM_DETAIL",
        mobile_web_eligibility="ELIGIBLE_PUBLIC_MOBILE_WEB",
    )
    return replace(base, **overrides)


class FakeHasher:
    """W5A `contracts.py` 자리. 계약이 들고 있는 해시를 그대로 재계산했다고 본다."""

    def __init__(self, task: str | None = TASK_HASH, endpoint: str | None = ENDPOINT_HASH) -> None:
        self.task = task
        self.endpoint = endpoint

    def task_contract_hash(self, contract: TaskContract) -> str | None:
        return self.task

    def endpoint_contract_hash(self, contract: TaskContract) -> str | None:
        return self.endpoint


class RecordingSafety:
    """W5G `safety.py` 자리. 실제 금지판정은 W5G 소관이고 여기서는 호출만 센다."""

    def __init__(self, deny: frozenset[str] = frozenset()) -> None:
        self.calls: list[PlannedAction] = []
        self.deny = deny

    def assert_action_allowed(self, contract: TaskContract, action: PlannedAction) -> None:
        self.calls.append(action)
        if action.action_token in self.deny:
            raise ProhibitedActionError(f"safety guard 거부: {action.action_token}")


def make_payload(
    node_id: str, url: str, *, screenshot: bytes | None = b"\x89PNG-fake"
) -> EvidencePayload:
    return EvidencePayload(
        node_id=node_id,
        url=url,
        dom=f"<html data-node='{node_id}'></html>",
        ax={"role": "WebArea", "name": node_id},
        probe={"viewport": [390, 844], "entry_x_norm": 0.5, "entry_y_norm": 0.12},
        control_facts={"selector": "#entry", "role": "link", "visible_text": "상품"},
        screenshot=screenshot,
    )


class FakeDriver:
    """fixture 전용 세션. 네트워크가 없다 — 이 lane 은 실사이트에 접촉하지 않는다."""

    def __init__(self, *, transitions: list[RawTransition], states: int = 2) -> None:
        self._transitions = list(transitions)
        self._states = states
        self.activations: list[PlannedAction] = []

    def capture_surface(self, contract: TaskContract) -> list[SurfaceObservation]:
        return [
            SurfaceObservation(
                state_index=f"S{index}",
                scroll_y=float(index * 844),
                viewport_width=390,
                viewport_height=844,
                url=contract.starting_url,
                payload=make_payload(f"raw-{index}", contract.starting_url),
            )
            for index in range(self._states)
        ]

    def activate(self, action: PlannedAction) -> RawTransition:
        self.activations.append(action)
        if not self._transitions:
            raise AssertionError("fixture 가 준비한 transition 을 넘겨 activate 했다")
        return self._transitions.pop(0)


def ok_transition(index: int, *, endpoint: bool = False, auth: bool = False) -> RawTransition:
    return RawTransition(
        ok=True,
        state_before_id=f"S{index}",
        state_after_id=f"S{index + 1}",
        url_before=f"https://fixture.invalid/{index}",
        url_after=f"https://fixture.invalid/{index + 1}",
        bbox_before=(10.0, 20.0, 100.0, 44.0),
        auth_gate_detected=auth,
        endpoint_signal_detected=endpoint,
        payload_before=make_payload(f"raw-b{index}", f"https://fixture.invalid/{index}"),
        payload_after=make_payload(f"raw-a{index}", f"https://fixture.invalid/{index + 1}"),
    )


class SpyScout:
    """자유탐색 spy. replay 국면에서 이 카운터가 0 이 아니면 `03 §5` 위반이다."""

    def __init__(self, plan: list[PlannedAction]) -> None:
        self._plan = list(plan)
        self.calls = 0

    def propose_next(
        self,
        contract: TaskContract,
        states: Any,
        candidates: Any,
        taken: Any,
    ) -> PlannedAction | None:
        self.calls += 1
        if not self._plan:
            return None
        return self._plan.pop(0)


SURFACE_SENTINEL = object()
FLOW_SENTINEL = object()
OBSTRUCTION_SENTINEL = object()


class SpySurface:
    def __init__(self) -> None:
        self.calls = 0

    def measure(self, contract: TaskContract, states: Any) -> Any:
        self.calls += 1
        return SURFACE_SENTINEL


class SpyFlow:
    def __init__(self) -> None:
        self.calls = 0

    def normalize(self, contract: TaskContract, steps: Any) -> Any:
        self.calls += 1
        return FLOW_SENTINEL


class SpyObstruction:
    def __init__(self) -> None:
        self.calls = 0

    def analyze(self, contract: TaskContract, states: Any, steps: Any) -> Any:
        self.calls += 1
        return OBSTRUCTION_SENTINEL


class FakeTerminal:
    def __init__(self, verdict: str | None = "REACHED") -> None:
        self.verdict = verdict
        self.calls = 0

    def classify(self, contract: TaskContract, steps: Any) -> str | None:
        self.calls += 1
        return self.verdict


class FakeBinder:
    def __init__(self) -> None:
        self.calls = 0

    def bind(self, contract: TaskContract, states: Any) -> list[dict[str, Any]]:
        self.calls += 1
        return [{"selector": "#entry", "role": "link", "visible_text": "상품"}]


class FakeEligibility:
    def __init__(self, verdict: str = "ELIGIBLE_PUBLIC_MOBILE_WEB") -> None:
        self.verdict = verdict

    def check(self, contract: TaskContract) -> str:
        return self.verdict


def make_runner(tmp_path: Path, **overrides: Any) -> V3Runner:
    kwargs: dict[str, Any] = {
        "evidence_root": tmp_path / "evidence",
        "contract_hasher": FakeHasher(),
        "safety": RecordingSafety(),
        "eligibility": FakeEligibility(),
        "binder": FakeBinder(),
        "scout": SpyScout([PlannedAction("SELECT_FUNCTION", control_selector="#entry")]),
        "surface_measurer": SpySurface(),
        "flow_normalizer": SpyFlow(),
        "obstruction": SpyObstruction(),
        "terminal": FakeTerminal(),
    }
    kwargs.update(overrides)
    return V3Runner(**kwargs)


# ---------------------------------------------------------------------------
# 1. 해시 불일치 3종 — 각각 거부 + 양성 대조
# ---------------------------------------------------------------------------


def test_positive_control_all_three_hashes_correct_run_completes(tmp_path: Path) -> None:
    """양성 대조 — 정상 해시 3종이면 파이프라인이 끝까지 간다.

    이 대조가 없으면 아래 세 거부 테스트는 "무조건 거부하는 코드"도 통과시킨다.
    """
    runner = make_runner(tmp_path)
    driver = FakeDriver(transitions=[ok_transition(0, endpoint=True)] * 2)
    result = runner.run(make_contract(), driver=driver, run_id="run-0001")

    assert result.phase_reached is Phase.MART
    assert result.replay_status is ReplayStatus.REPLAYED
    assert result.endpoint_status == "REACHED"
    assert result.path_manifest_sha256 is not None
    assert result.evidence_manifest_sha256 is not None


def test_task_contract_hash_mismatch_refuses_before_any_capture(tmp_path: Path) -> None:
    runner = make_runner(tmp_path, contract_hasher=FakeHasher(task="c" * 64))
    driver = FakeDriver(transitions=[ok_transition(0, endpoint=True)] * 2)
    with pytest.raises(ContractHashMismatchError, match="task_contract_hash"):
        runner.run(make_contract(), driver=driver, run_id="run-0002")
    # fail-closed 는 "브라우저를 열기 전"이어야 한다 — 세션 접촉이 0 이어야 한다.
    assert driver.activations == []
    assert not (tmp_path / "evidence").exists()


def test_absent_task_contract_hash_is_refused_like_a_mismatch(tmp_path: Path) -> None:
    """부재도 불일치와 같은 취급 — 해시 없는 계약은 무엇으로 동결됐는지 알 수 없다."""
    runner = make_runner(tmp_path)
    with pytest.raises(ContractHashMismatchError, match="task_contract_hash"):
        runner.run(
            make_contract(task_contract_hash=""),
            driver=FakeDriver(transitions=[]),
            run_id="run-0003",
        )


def test_endpoint_contract_hash_mismatch_refuses(tmp_path: Path) -> None:
    runner = make_runner(tmp_path, contract_hasher=FakeHasher(endpoint="d" * 64))
    driver = FakeDriver(transitions=[ok_transition(0, endpoint=True)] * 2)
    with pytest.raises(ContractHashMismatchError, match="endpoint_contract_hash"):
        runner.run(make_contract(), driver=driver, run_id="run-0004")
    assert driver.activations == []


def test_absent_endpoint_contract_hash_is_refused(tmp_path: Path) -> None:
    runner = make_runner(tmp_path)
    with pytest.raises(ContractHashMismatchError, match="endpoint_contract_hash"):
        runner.run(
            make_contract(endpoint_contract_hash=""),
            driver=FakeDriver(transitions=[]),
            run_id="run-0005",
        )


def test_path_manifest_hash_mismatch_refuses_replay(tmp_path: Path) -> None:
    """세 번째 해시 — frozen path 가 freeze 당시 그대로가 아니면 재생하지 않는다."""
    contract = make_contract()
    key = ObservationKey(service_id=contract.target_id, task_id=contract.frozen_task, run_id="r1")
    manifest = build_path_manifest(
        key=key,
        contract=contract,
        steps=[
            FlowStep(
                step_index=0,
                action_token="SELECT_FUNCTION",
                state_before_id="S0",
                state_after_id="S1",
                control_selector="#entry",
                control_role="link",
                control_visible_text="상품",
                control_accessible_name="상품",
                bbox_before=None,
                url_before="https://fixture.invalid/0",
                url_after="https://fixture.invalid/1",
                auth_gate_detected=False,
                endpoint_signal_detected=True,
            )
        ],
    )
    runner = make_runner(tmp_path)
    driver = FakeDriver(transitions=[ok_transition(0, endpoint=True)] * 2)
    with pytest.raises(PathManifestHashMismatchError):
        runner.replay(
            contract,
            driver=driver,
            manifest=manifest,
            declared_sha256="e" * 64,
            run_id="run-0006",
        )
    assert driver.activations == []


def test_absent_path_manifest_hash_is_refused(tmp_path: Path) -> None:
    contract = make_contract()
    key = ObservationKey(service_id=contract.target_id, task_id=contract.frozen_task, run_id="r1")
    manifest = build_path_manifest(key=key, contract=contract, steps=[])
    runner = make_runner(tmp_path)
    with pytest.raises(PathManifestHashMismatchError, match="해시가 없다"):
        runner.replay(
            contract,
            driver=FakeDriver(transitions=[]),
            manifest=manifest,
            declared_sha256=None,
            run_id="run-0007",
        )


def test_positive_control_correct_path_manifest_hash_replays(tmp_path: Path) -> None:
    """양성 대조 — 해시가 맞으면 같은 manifest 로 replay 가 진행된다."""
    contract = make_contract()
    key = ObservationKey(service_id=contract.target_id, task_id=contract.frozen_task, run_id="r1")
    manifest = build_path_manifest(
        key=key,
        contract=contract,
        steps=[
            FlowStep(
                step_index=0,
                action_token="SELECT_FUNCTION",
                state_before_id="S0",
                state_after_id="S1",
                control_selector="#entry",
                control_role="link",
                control_visible_text="상품",
                control_accessible_name="상품",
                bbox_before=None,
                url_before="https://fixture.invalid/0",
                url_after="https://fixture.invalid/1",
                auth_gate_detected=False,
                endpoint_signal_detected=True,
            )
        ],
    )
    runner = make_runner(tmp_path)
    driver = FakeDriver(transitions=[ok_transition(0, endpoint=True)] * 2)
    result = runner.replay(
        contract,
        driver=driver,
        manifest=manifest,
        declared_sha256=path_manifest_sha256(manifest),
        run_id="run-0008",
    )
    assert result.replay_status is ReplayStatus.REPLAYED
    assert len(driver.activations) == 1


# ---------------------------------------------------------------------------
# 2. REPLAY_BROKEN — 자유탐색이 일어나지 않았음을 spy 로 증명
# ---------------------------------------------------------------------------


def _one_step_manifest(contract: TaskContract) -> dict[str, Any]:
    key = ObservationKey(service_id=contract.target_id, task_id=contract.frozen_task, run_id="r1")
    return build_path_manifest(
        key=key,
        contract=contract,
        steps=[
            FlowStep(
                step_index=0,
                action_token="SELECT_FUNCTION",
                state_before_id="S0",
                state_after_id="S1",
                control_selector="#entry",
                control_role="link",
                control_visible_text="상품",
                control_accessible_name="상품",
                bbox_before=None,
                url_before="https://fixture.invalid/0",
                url_after="https://fixture.invalid/1",
                auth_gate_detected=False,
                endpoint_signal_detected=True,
            )
        ],
    )


def test_broken_replay_records_replay_broken_and_never_free_explores(tmp_path: Path) -> None:
    """`03 §5` · `00 §9` 금지 — 깨진 replay 는 기록으로 끝나고 재탐색으로 대체되지 않는다.

    scout 는 runner 에 **주입되어 있다**. 그런데도 호출횟수가 0 이어야 한다 —
    "접근할 수 없어서 안 불렀다" 가 아니라 "접근할 수 있는데도 안 불렀다" 를 본다.
    """
    contract = make_contract()
    scout = SpyScout([PlannedAction("SELECT_FUNCTION", control_selector="#entry")])
    runner = make_runner(tmp_path, scout=scout, terminal=FakeTerminal("REACHED"))
    manifest = _one_step_manifest(contract)
    broken = RawTransition(
        ok=False,
        state_before_id="S0",
        state_after_id="S0",
        url_before="https://fixture.invalid/0",
        url_after="https://fixture.invalid/0",
        failure_reason="selector #entry not found",
    )
    result = runner.replay(
        contract,
        driver=FakeDriver(transitions=[broken]),
        manifest=manifest,
        declared_sha256=path_manifest_sha256(manifest),
        run_id="run-0100",
    )

    assert result.replay_status is ReplayStatus.REPLAY_BROKEN
    assert result.replay_failure_reason == "selector #entry not found"
    assert scout.calls == 0, "replay 가 깨지자 자유탐색이 돌았다 — 03 §5 위반"


def test_broken_replay_leaves_endpoint_status_none_not_fail(tmp_path: Path) -> None:
    """`09 D3-05` — 산출 불능은 `None` 이다. 0 이나 FAIL 로 환산하지 않는다."""
    contract = make_contract()
    terminal = FakeTerminal("REACHED")
    runner = make_runner(tmp_path, terminal=terminal)
    manifest = _one_step_manifest(contract)
    broken = RawTransition(
        ok=False,
        state_before_id="S0",
        state_after_id="S0",
        url_before="https://fixture.invalid/0",
        url_after="https://fixture.invalid/0",
    )
    result = runner.replay(
        contract,
        driver=FakeDriver(transitions=[broken]),
        manifest=manifest,
        declared_sha256=path_manifest_sha256(manifest),
        run_id="run-0101",
    )
    assert result.endpoint_status is None
    assert terminal.calls == 0, "깨진 replay 를 terminal classifier 로 판정해 버렸다"
    assert result.raw_steps == ()


def test_full_run_with_broken_replay_does_not_rescout(tmp_path: Path) -> None:
    """full 파이프라인에서도 scout 국면은 정확히 한 번이다 — 실패 뒤 재탐색이 없다."""
    scout = SpyScout([PlannedAction("SELECT_FUNCTION", control_selector="#entry")])
    runner = make_runner(tmp_path, scout=scout)
    broken = RawTransition(
        ok=False,
        state_before_id="S1",
        state_after_id="S1",
        url_before="https://fixture.invalid/1",
        url_after="https://fixture.invalid/1",
        failure_reason="replay diverged",
    )
    driver = FakeDriver(transitions=[ok_transition(0, endpoint=True), broken])
    result = runner.run(make_contract(), driver=driver, run_id="run-0102")

    assert result.replay_status is ReplayStatus.REPLAY_BROKEN
    assert result.endpoint_status is None
    # scout 는 "다음 action" 1건 + "끝" 신호 1건까지만 호출된다. 재탐색이 있었다면 더 늘어난다.
    assert scout.calls == 1


# ---------------------------------------------------------------------------
# 3. append-only — 같은 identity 로 두 번 쓰면 두 번째가 거부되고 기존 바이트는 불변
# ---------------------------------------------------------------------------


def test_same_service_task_run_twice_second_write_refused_bytes_unchanged(tmp_path: Path) -> None:
    """`02 §8` — 재수집은 새 run 이다. 기존 evidence 는 한 바이트도 바뀌지 않는다."""
    root = tmp_path / "evidence"
    key = ObservationKey(service_id="svc_f2_0003", task_id="t_f2_item_detail", run_id="run-A")

    first = EvidenceRunWriter(root, key).open()
    first.write_payload(make_payload("s000", "https://fixture.invalid/0"))
    seal = first.seal(path_manifest_sha256="f" * 64)

    dom_path = seal.run_dir / "s000" / "dom.html"
    before_bytes = dom_path.read_bytes()
    before_sha = sha256_of_file(dom_path)

    with pytest.raises(EvidenceOverwriteError):
        EvidenceRunWriter(root, key).open()

    assert dom_path.read_bytes() == before_bytes
    assert sha256_of_file(dom_path) == before_sha


def test_writing_same_slot_twice_in_one_run_is_refused(tmp_path: Path) -> None:
    key = ObservationKey(service_id="s1", task_id="t1", run_id="r1")
    writer = EvidenceRunWriter(tmp_path / "ev", key).open()
    writer.write_payload(make_payload("s000", "https://fixture.invalid/0"))
    with pytest.raises(EvidenceOverwriteError):
        writer.write_payload(make_payload("s000", "https://fixture.invalid/0"))


def test_sealed_run_refuses_further_writes(tmp_path: Path) -> None:
    key = ObservationKey(service_id="s1", task_id="t1", run_id="r1")
    writer = EvidenceRunWriter(tmp_path / "ev", key).open()
    writer.write_payload(make_payload("s000", "https://fixture.invalid/0"))
    writer.seal(path_manifest_sha256="a" * 64)
    with pytest.raises(RunSealedError):
        writer.write_payload(make_payload("s001", "https://fixture.invalid/1"))


def test_different_run_id_is_a_new_run_and_coexists(tmp_path: Path) -> None:
    """양성 대조 — 새 `run_id` 는 막히지 않는다. 막히면 재수집 자체가 불가능해진다."""
    root = tmp_path / "ev"
    for run_id in ("run-A", "run-B"):
        key = ObservationKey(service_id="s1", task_id="t1", run_id=run_id)
        writer = EvidenceRunWriter(root, key).open()
        writer.write_payload(make_payload("s000", "https://fixture.invalid/0"))
        writer.seal(path_manifest_sha256="a" * 64)
    assert len(list(root.iterdir())) == 2


# ---------------------------------------------------------------------------
# 4. identity — display name 이 file id 가 되지 않는다
# ---------------------------------------------------------------------------


def test_observation_identity_is_the_three_ids_only(tmp_path: Path) -> None:
    key = ObservationKey(service_id="svc_0003", task_id="t_f2", run_id="run-A")
    assert len(key.observation_id()) == 32
    assert key.observation_id() != ObservationKey("svc_0003", "t_f2", "run-B").observation_id()


def test_display_name_cannot_become_a_file_id(tmp_path: Path) -> None:
    """`02 §8` — 표시명은 공백을 갖는다. 그 형태는 id 로 통과하지 않는다."""
    with pytest.raises(Exception, match="machine id"):
        ObservationKey(service_id="쿠팡 모바일", task_id="t1", run_id="r1").observation_id()


def test_run_directory_name_is_the_hash_not_any_supplied_name(tmp_path: Path) -> None:
    root = tmp_path / "ev"
    key = ObservationKey(service_id="svc_0003", task_id="t_f2", run_id="run-A")
    writer = EvidenceRunWriter(root, key).open()
    assert writer.run_dir.name == key.observation_id()
    assert "svc_0003" not in writer.run_dir.name


# ---------------------------------------------------------------------------
# 5. screenshot 은 포인터 + sha256 만
# ---------------------------------------------------------------------------


def test_screenshot_is_a_pointer_never_inlined_in_json(tmp_path: Path) -> None:
    key = ObservationKey(service_id="s1", task_id="t1", run_id="r1")
    writer = EvidenceRunWriter(tmp_path / "ev", key).open()
    writer.write_payload(make_payload("s000", "https://fixture.invalid/0", screenshot=b"\x89PNG-x"))
    seal = writer.seal(path_manifest_sha256="a" * 64)

    entries = load_evidence_manifest(seal.run_dir)
    shot = next(entry for entry in entries if entry.slot == EvidenceSlot.SCREENSHOT.value)
    assert shot.relpath == "s000/screenshot.png"
    assert shot.bytes == len(b"\x89PNG-x")
    manifest_text = (seal.run_dir / "manifest.jsonl").read_text(encoding="utf-8")
    assert "PNG" not in manifest_text
    for line in manifest_text.splitlines():
        assert set(json.loads(line)) == {
            "observation_id",
            "node_id",
            "slot",
            "relpath",
            "sha256",
            "bytes",
        }


def test_json_slot_refuses_inlined_binary_and_data_uri(tmp_path: Path) -> None:
    key = ObservationKey(service_id="s1", task_id="t1", run_id="r1")
    writer = EvidenceRunWriter(tmp_path / "ev", key).open()
    with pytest.raises(InlinedBinaryError):
        writer.write_json_slot("s000", EvidenceSlot.PROBE, {"shot": b"\x89PNG"})
    with pytest.raises(InlinedBinaryError):
        writer.write_json_slot("s001", EvidenceSlot.PROBE, {"shot": "data:image/png;base64,AAAA"})
    with pytest.raises(InlinedBinaryError):
        writer.write_json_slot("s002", EvidenceSlot.PROBE, {"screenshot_b64": "AAAA"})


# ---------------------------------------------------------------------------
# 6. path manifest ↔ evidence manifest hash 연결
# ---------------------------------------------------------------------------


def test_path_and_evidence_manifests_are_linked_by_hash(tmp_path: Path) -> None:
    contract = make_contract()
    key = ObservationKey(service_id="s1", task_id="t1", run_id="r1")
    manifest = build_path_manifest(key=key, contract=contract, steps=[])
    manifest_bytes = json.dumps(
        manifest, sort_keys=True, ensure_ascii=False, separators=(",", ":")
    ).encode("utf-8")

    writer = EvidenceRunWriter(tmp_path / "ev", key).open()
    writer.write_payload(make_payload("s000", "https://fixture.invalid/0"))
    seal = writer.seal(path_manifest_sha256=path_manifest_sha256(manifest))

    report = verify_manifest_linkage(seal.run_dir, path_manifest_bytes=manifest_bytes)
    assert report["linked"] is True

    tampered = dict(manifest)
    tampered["steps"] = [{"step_index": 0, "action_token": "SELECT_FUNCTION"}]
    tampered_bytes = json.dumps(
        tampered, sort_keys=True, ensure_ascii=False, separators=(",", ":")
    ).encode("utf-8")
    with pytest.raises(ManifestLinkageError, match="path manifest"):
        verify_manifest_linkage(seal.run_dir, path_manifest_bytes=tampered_bytes)


def test_replacing_evidence_manifest_breaks_the_link(tmp_path: Path) -> None:
    contract = make_contract()
    key = ObservationKey(service_id="s1", task_id="t1", run_id="r1")
    manifest = build_path_manifest(key=key, contract=contract, steps=[])
    manifest_bytes = json.dumps(
        manifest, sort_keys=True, ensure_ascii=False, separators=(",", ":")
    ).encode("utf-8")
    writer = EvidenceRunWriter(tmp_path / "ev", key).open()
    writer.write_payload(make_payload("s000", "https://fixture.invalid/0"))
    seal = writer.seal(path_manifest_sha256=path_manifest_sha256(manifest))

    (seal.run_dir / "manifest.jsonl").write_text("", encoding="utf-8")
    with pytest.raises(ManifestLinkageError, match="evidence manifest"):
        verify_manifest_linkage(seal.run_dir, path_manifest_bytes=manifest_bytes)


def test_verify_evidence_run_catches_a_tampered_artifact(tmp_path: Path) -> None:
    key = ObservationKey(service_id="s1", task_id="t1", run_id="r1")
    writer = EvidenceRunWriter(tmp_path / "ev", key).open()
    writer.write_payload(make_payload("s000", "https://fixture.invalid/0"))
    seal = writer.seal(path_manifest_sha256="a" * 64)
    assert verify_evidence_run(seal.run_dir)["ok"] is True

    (seal.run_dir / "s000" / "dom.html").write_text("<html>swapped</html>", encoding="utf-8")
    report = verify_evidence_run(seal.run_dir)
    assert report["ok"] is False
    assert "s000/dom.html" in report["mismatched"]


# ---------------------------------------------------------------------------
# 7. retention manifest
# ---------------------------------------------------------------------------


def test_retention_manifest_sha256_matches_real_files(tmp_path: Path) -> None:
    root = tmp_path / "artifacts" / "run-A"
    root.mkdir(parents=True)
    (root / "a.json").write_text('{"x":1}', encoding="utf-8")
    (root / "b.png").write_bytes(b"\x89PNG-bytes")

    manifest = build_retention_manifest(
        manifest_id="ARM-V3-TEST",
        producer="B",
        producer_sha="0" * 40,
        roots=[root],
        base=tmp_path,
    )
    record = manifest["roots"][0]
    assert record["artifact_count"] == 2
    assert record["bytes"] == (root / "a.json").stat().st_size + (root / "b.png").stat().st_size
    for file_record in record["files"]:
        target = tmp_path / file_record["path"]
        assert file_record["sha256"] == sha256_of_file(target)
        assert file_record["bytes"] == target.stat().st_size

    assert verify_retention_manifest(manifest, base=tmp_path)["ok"] is True


def test_retention_manifest_detects_a_changed_byte(tmp_path: Path) -> None:
    root = tmp_path / "artifacts" / "run-A"
    root.mkdir(parents=True)
    (root / "a.json").write_text('{"x":1}', encoding="utf-8")
    manifest = build_retention_manifest(
        manifest_id="ARM-V3-TEST",
        producer="B",
        producer_sha="0" * 40,
        roots=[root],
        base=tmp_path,
    )
    (root / "a.json").write_text('{"x":2}', encoding="utf-8")
    report = verify_retention_manifest(manifest, base=tmp_path)
    assert report["ok"] is False
    assert report["mismatched"] == ["artifacts/run-A/a.json"]


# ---------------------------------------------------------------------------
# 8. derived 계산이 runner 안에 없다 — Protocol 경계가 실제로 불린다
# ---------------------------------------------------------------------------


def test_derived_values_come_from_the_protocol_boundaries_by_identity(tmp_path: Path) -> None:
    """호출됐다에서 멈추지 않는다 — fake 가 돌려준 sentinel 이 결과에 그대로 실렸는지 본다."""
    surface, flow, obstruction = SpySurface(), SpyFlow(), SpyObstruction()
    runner = make_runner(
        tmp_path, surface_measurer=surface, flow_normalizer=flow, obstruction=obstruction
    )
    result = runner.run(
        make_contract(),
        driver=FakeDriver(transitions=[ok_transition(0, endpoint=True)] * 2),
        run_id="run-0200",
    )
    assert (surface.calls, flow.calls, obstruction.calls) == (1, 1, 1)
    assert result.derived_surface is SURFACE_SENTINEL
    assert result.derived_flow is FLOW_SENTINEL
    assert result.derived_obstruction is OBSTRUCTION_SENTINEL


def test_without_boundaries_derived_slots_are_none_not_recomputed(tmp_path: Path) -> None:
    """경계를 빼면 그 자리는 `None` 이다. runner 안에 대체 계산이 있으면 여기서 값이 나온다."""
    runner = make_runner(
        tmp_path,
        surface_measurer=None,
        flow_normalizer=None,
        obstruction=None,
        terminal=None,
    )
    result = runner.run(
        make_contract(),
        driver=FakeDriver(transitions=[ok_transition(0, endpoint=True)] * 2),
        run_id="run-0201",
    )
    assert result.derived_surface is None
    assert result.derived_flow is None
    assert result.derived_obstruction is None
    assert result.endpoint_status is None
    # raw 는 그대로 남아 있어야 한다 — derived 부재가 raw 손실이 되면 안 된다.
    assert len(result.raw_steps) == 1
    assert len(result.raw_states) == 2


def test_runner_module_has_no_representative_function_classifier() -> None:
    """`09 D3-03` — RF 7-way classifier 는 critical path 에서 퇴역했다."""
    source = (RESEARCH / "src" / "landing_accessibility" / "v3_runner" / "runner.py").read_text(
        encoding="utf-8"
    )
    for banned in (
        "RandomForest",
        "predict_proba",
        "rf_classifier",
        "classify_representative",
        "sklearn",
    ):
        assert banned not in source, f"runner 가 {banned} 를 참조한다 — D3-03 위반"


# ---------------------------------------------------------------------------
# 9. 금지 조작 — 닫힌 어휘 + 계약 금지목록 + W5G safety
# ---------------------------------------------------------------------------


def test_action_token_outside_the_codebook_is_refused(tmp_path: Path) -> None:
    """`04 §2` 밖의 token 은 실행되지 않는다 — 새 조작화를 코드로 발명하는 경로를 막는다."""
    assert "SUBMIT_PAYMENT" not in CANONICAL_ACTION_TOKENS
    scout = SpyScout([PlannedAction("SUBMIT_PAYMENT")])
    runner = make_runner(tmp_path, scout=scout)
    driver = FakeDriver(transitions=[ok_transition(0)])
    with pytest.raises(ProhibitedActionError, match="canonical token"):
        runner.run(make_contract(), driver=driver, run_id="run-0300")
    assert driver.activations == []


def test_contract_forbidden_action_is_refused(tmp_path: Path) -> None:
    scout = SpyScout([PlannedAction("SELECT_DATE")])
    runner = make_runner(tmp_path, scout=scout)
    driver = FakeDriver(transitions=[ok_transition(0)])
    with pytest.raises(ProhibitedActionError, match="forbidden_actions"):
        runner.run(make_contract(), driver=driver, run_id="run-0301")
    assert driver.activations == []


def test_safety_guard_is_consulted_for_every_activation(tmp_path: Path) -> None:
    safety = RecordingSafety()
    runner = make_runner(tmp_path, safety=safety)
    runner.run(
        make_contract(),
        driver=FakeDriver(transitions=[ok_transition(0, endpoint=True)] * 2),
        run_id="run-0302",
    )
    # scout 1회 + replay 1회 = 같은 action 을 두 번 모두 safety 에 통과시켰다.
    assert [action.action_token for action in safety.calls] == [
        "SELECT_FUNCTION",
        "SELECT_FUNCTION",
    ]


# ---------------------------------------------------------------------------
# 10. eligibility / budget — 불능은 None
# ---------------------------------------------------------------------------


def test_app_required_stops_before_evidence_run(tmp_path: Path) -> None:
    """`03 §2` — app-only 는 main frame 에서 교체 대상이고 수집으로 넘어가지 않는다."""
    runner = make_runner(tmp_path, eligibility=FakeEligibility("APP_REQUIRED_EXCLUDE"))
    result = runner.run(
        make_contract(),
        driver=FakeDriver(transitions=[]),
        run_id="run-0400",
    )
    assert result.phase_reached is Phase.ELIGIBILITY
    assert result.eligibility == "APP_REQUIRED_EXCLUDE"
    assert result.endpoint_status is None
    assert not (tmp_path / "evidence").exists()


def test_scout_budget_exhaustion_is_recorded_not_converted_to_a_number(tmp_path: Path) -> None:
    """예산에 걸린 관측은 "N" 이 아니라 "N 회 안에서는 관측되지 않았다" 다."""
    plan = [PlannedAction("SELECT_CATEGORY") for _ in range(5)]
    runner = make_runner(
        tmp_path,
        scout=SpyScout(plan),
        budget=ScoutBudget(max_activations=2),
        terminal=FakeTerminal(None),
    )
    driver = FakeDriver(transitions=[ok_transition(index) for index in range(6)])
    result = runner.run(make_contract(), driver=driver, run_id="run-0401")
    assert result.scout_budget_exhausted is True
    assert result.endpoint_status is None
    assert len(result.path_manifest["steps"]) == 2  # type: ignore[index]


# ---------------------------------------------------------------------------
# 11. R6-Q8 — AUTH_GATE / ABSTAIN 층 한정
# ---------------------------------------------------------------------------


def test_auth_gate_alone_in_an_unqualified_column_is_a_violation() -> None:
    with pytest.raises(LayerQualificationError):
        assert_layer_qualified({"status": "AUTH_GATE"})
    with pytest.raises(LayerQualificationError):
        assert_layer_qualified({"outcome": "ABSTAIN"})
    with pytest.raises(LayerQualificationError):
        assert_layer_qualified({"values": ["AUTH_GATE"]})


def test_layer_qualified_columns_pass() -> None:
    """양성 대조 — 층이 명시된 컬럼명 아래에서는 같은 값이 정상이다."""
    assert_layer_qualified({"endpoint_status": "AUTH_GATE"})
    assert_layer_qualified({"steps": [{"action_token": "AUTH_GATE"}]})
    assert qualified_layer_text("endpoint_status", "AUTH_GATE") == "endpoint_status=AUTH_GATE"
    with pytest.raises(LayerQualificationError):
        qualified_layer_text("status", "AUTH_GATE")


def test_mart_record_emits_auth_gate_only_under_qualifying_keys(tmp_path: Path) -> None:
    runner = make_runner(tmp_path, terminal=FakeTerminal("AUTH_GATE"))
    result = runner.run(
        make_contract(),
        driver=FakeDriver(transitions=[ok_transition(0, auth=True)] * 2),
        run_id="run-0500",
    )
    record = result.as_mart_record()  # 위반이면 여기서 예외가 난다
    assert record["endpoint_status"] == "AUTH_GATE"
    assert record["task_role"] == "PRIMARY"


# ---------------------------------------------------------------------------
# 12. R7 — 요약값이 좌표를 덮지 않는다
# ---------------------------------------------------------------------------


def test_zone_without_coordinates_is_refused() -> None:
    with pytest.raises(CoordinateDropError):
        assert_coordinates_preserved({"entry_zone": "TOP_LEFT"})


def test_structural_override_zones_still_require_coordinates() -> None:
    """`FLOATING`/`DRAWER` override 가 걸려도 좌표는 그대로 남는다."""
    for zone in ("FLOATING", "DRAWER"):
        with pytest.raises(CoordinateDropError):
            assert_coordinates_preserved({"entry_zone": zone})
        assert_coordinates_preserved(
            {"entry_zone": zone, "entry_x_norm": 0.91, "entry_y_norm": 0.88}
        )


def test_unobserved_coordinates_are_none_not_missing_keys() -> None:
    """관측 못 한 좌표는 `None` 으로 남는다 — 키 자체가 사라지는 것과 구분한다."""
    assert_coordinates_preserved({"entry_zone": "MID", "entry_x_norm": None, "entry_y_norm": None})


# ---------------------------------------------------------------------------
# 13. R3 / R2 / R4 — task_role 필터 · 두 분모 · 분모 사슬
# ---------------------------------------------------------------------------


def test_secondary_repeated_task_is_excluded_and_the_filter_string_is_recorded() -> None:
    """`R3` — "적용했다"는 주장이 아니라 필터 조건 문자열이 산출물에 실린다."""
    records = [
        {"observation_id": "o1", "task_role": "PRIMARY"},
        {"observation_id": "o2", "task_role": "SECONDARY_REPEATED"},
        {"observation_id": "o3", "task_role": "PRIMARY"},
    ]
    aggregate = build_family_aggregate(family_id="F1", metric="entry_zone", records=records)
    assert aggregate["applied_filter"] == "task_role == 'PRIMARY'"
    assert aggregate["denominator_n"] == 2
    assert aggregate["excluded_observation_ids"] == ["o2"]


def test_entry_flow_metrics_use_evidence_bearing_not_flow_evaluable() -> None:
    """`R2` — 진입 flow 지표에서 AUTH_GATE target 을 빼면 selection 이 생긴다."""
    for metric in ("entry_zone", "entry_x_norm", "nav_container_depth", "auth_gate_stage"):
        assert denominator_for_metric(metric) == "evidence_bearing_n"
    for metric in ("endpoint_reach_rate", "activation_depth"):
        assert denominator_for_metric(metric) == "flow_evaluable_n"
    with pytest.raises(DenominatorError):
        denominator_for_metric("some_new_metric")


def test_invalid_task_role_is_refused_before_execution(tmp_path: Path) -> None:
    runner = make_runner(tmp_path)
    with pytest.raises(ContractHashMismatchError, match="task_role"):
        runner.run(
            make_contract(task_role="OPTIONAL"),
            driver=FakeDriver(transitions=[]),
            run_id="run-0600",
        )


def test_denominator_chain_states_zero_replacements_explicitly() -> None:
    """`R4` — `k=0` 이어도 0 을 명시한다. 필드 부재와 0 이 같아 보이면 안 된다."""
    ledger = ReplacementLedger(family_id="F2", frozen_at="2026-08-28T00:00:00Z")
    chain = build_denominator_chain(
        family_id="F2",
        candidate_target_ids=[f"t{i}" for i in range(10)],
        ledger=ledger,
        frozen_target_ids=[f"t{i}" for i in range(10)],
        attempted_target_ids=[f"t{i}" for i in range(10)],
        evidence_bearing_target_ids=[f"t{i}" for i in range(10)],
        flow_evaluable_target_ids=[f"t{i}" for i in range(8)],
    )
    replaced_stage = next(s for s in chain["chain"] if s["stage"] == "replaced")
    assert replaced_stage["n"] == 0
    assert chain["replacement_ledger"]["replaced_count"] == 0
    assert "replaced_count" in chain["replacement_ledger"]
    assert chain["applied_filter"] == "task_role == 'PRIMARY'"


def test_replacement_detail_carries_all_five_provenance_fields() -> None:
    ledger = ReplacementLedger(
        family_id="F4",
        frozen_at="2026-08-28T00:00:00Z",
        replacements=(
            Replacement(
                excluded_target_id="t7",
                reason="APP_REQUIRED_EXCLUDE",
                reserve_rank=11,
                decided_at="2026-08-28T00:10:00Z",
                decided_by="A",
            ),
        ),
    )
    chain = build_denominator_chain(
        family_id="F4",
        candidate_target_ids=[f"t{i}" for i in range(10)],
        ledger=ledger,
        frozen_target_ids=[f"t{i}" for i in range(10)],
        attempted_target_ids=[f"t{i}" for i in range(10)],
        evidence_bearing_target_ids=[f"t{i}" for i in range(10)],
        flow_evaluable_target_ids=[],
    )
    detail = next(s for s in chain["chain"] if s["stage"] == "replaced")["detail"][0]
    assert set(detail) == {
        "excluded_target_id",
        "reason",
        "reserve_rank",
        "decided_at",
        "decided_by",
    }
    assert verify_denominator_chain(chain, ledger=ledger)["linked"] is True


def test_replacement_added_after_attempted_breaks_the_chain_hash() -> None:
    """`R4` — 교체는 precheck 에서만 가능하다. 나중에 끼워 넣으면 해시가 깨진다."""
    ledger = ReplacementLedger(family_id="F3", frozen_at="2026-08-28T00:00:00Z")
    chain = build_denominator_chain(
        family_id="F3",
        candidate_target_ids=["t1"],
        ledger=ledger,
        frozen_target_ids=["t1"],
        attempted_target_ids=["t1"],
        evidence_bearing_target_ids=["t1"],
        flow_evaluable_target_ids=["t1"],
    )
    late = ReplacementLedger(
        family_id="F3",
        frozen_at="2026-08-28T00:00:00Z",
        replacements=(
            Replacement(
                excluded_target_id="t1",
                reason="결과를 본 뒤 교체",
                reserve_rank=11,
                decided_at="2026-08-28T09:00:00Z",
                decided_by="B",
            ),
        ),
    )
    with pytest.raises(DenominatorError, match="attempted 이후"):
        verify_denominator_chain(chain, ledger=late)


def test_flow_evaluable_must_be_a_subset_of_evidence_bearing() -> None:
    ledger = ReplacementLedger(family_id="F5", frozen_at="2026-08-28T00:00:00Z")
    with pytest.raises(DenominatorError, match="부분집합"):
        build_denominator_chain(
            family_id="F5",
            candidate_target_ids=["t1", "t2"],
            ledger=ledger,
            frozen_target_ids=["t1", "t2"],
            attempted_target_ids=["t1", "t2"],
            evidence_bearing_target_ids=["t1"],
            flow_evaluable_target_ids=["t1", "t2"],
        )


# ---------------------------------------------------------------------------
# 14. Δ9 — depth 조건부 토큰의 귀속 근거를 raw 로 보존한다
# ---------------------------------------------------------------------------


def test_depth_attribution_table_partitions_the_18_canonical_tokens() -> None:
    """`T-A-V3-STEP1-006` — IN 10 · OUT 5 · CONDITIONAL 3 이 18종을 정확히 분할한다."""
    assert len(DEPTH_IN_TOKENS) == 10
    assert len(DEPTH_OUT_TOKENS) == 5
    assert len(DEPTH_CONDITIONAL_TOKENS) == 3
    union = DEPTH_IN_TOKENS | DEPTH_OUT_TOKENS | DEPTH_CONDITIONAL_TOKENS
    assert union == CANONICAL_ACTION_TOKENS
    assert not (DEPTH_IN_TOKENS & DEPTH_OUT_TOKENS)
    assert not (DEPTH_IN_TOKENS & DEPTH_CONDITIONAL_TOKENS)
    assert not (DEPTH_OUT_TOKENS & DEPTH_CONDITIONAL_TOKENS)


def test_auth_gate_is_out_because_it_is_encountered_not_activated() -> None:
    """기준 ① — `AUTH_GATE` 는 사용자 활성화가 아니라 마주친 상태다."""
    assert "AUTH_GATE" in DEPTH_OUT_TOKENS
    assert "AUTH_GATE" not in DEPTH_IN_TOKENS


def test_auth_gate_step_carries_encountered_state_provenance(tmp_path: Path) -> None:
    """terminal 기록에서 그 구분이 흐려지지 않게 provenance 를 못박는다."""
    scout = SpyScout([PlannedAction("AUTH_GATE")])
    runner = make_runner(tmp_path, scout=scout, terminal=FakeTerminal("AUTH_GATE"))
    driver = FakeDriver(transitions=[ok_transition(0, auth=True), ok_transition(0, auth=True)])
    record = runner.run(make_contract(), driver=driver, run_id="run-0700").as_mart_record()
    step = record["action_sequence_raw"][0]
    assert step["action_token"] == "AUTH_GATE"
    assert step["auth_gate_provenance"] == "ENCOUNTERED_STATE_NOT_USER_ACTIVATION"


def test_conditional_token_basis_is_preserved_as_raw_evidence(tmp_path: Path) -> None:
    """Δ9 — "판정했다" 가 아니라 "무엇을 근거로" 가 evidence package 에 남는다."""
    scout = SpyScout([PlannedAction("SELECT_DESTINATION")])
    runner = make_runner(tmp_path, scout=scout, terminal=FakeTerminal(None))
    dropdown = replace(ok_transition(0, endpoint=True), input_mode="DROPDOWN")
    driver = FakeDriver(transitions=[dropdown, dropdown])
    result = runner.run(make_contract(), driver=driver, run_id="run-0701")

    assert len(result.depth_conditional_tokens) == 1
    entry = result.depth_conditional_tokens[0]
    assert entry["action_token"] == "SELECT_DESTINATION"
    assert entry["step_index"] == 0
    assert entry["input_mode"] == "DROPDOWN"
    # 판정은 W5B 소관이다 — 경계가 없으면 None 이지 False 가 아니다.
    assert entry["included"] is None

    run_dir = result.evidence_run_dir
    assert run_dir is not None
    manifest_relpaths = {entry.relpath for entry in load_evidence_manifest(run_dir)}
    assert "observation/depth_conditional_tokens.json" in manifest_relpaths
    payload = json.loads(
        (run_dir / "observation" / "depth_conditional_tokens.json").read_text(encoding="utf-8")
    )
    assert payload["depth_conditional_tokens"][0]["input_mode"] == "DROPDOWN"


def test_non_conditional_tokens_produce_no_attribution_rows(tmp_path: Path) -> None:
    """IN/OUT 토큰은 조건부가 아니므로 근거 행을 만들지 않는다."""
    runner = make_runner(tmp_path)
    result = runner.run(
        make_contract(),
        driver=FakeDriver(transitions=[ok_transition(0, endpoint=True)] * 2),
        run_id="run-0702",
    )
    assert result.depth_conditional_tokens == ()


def test_depth_attributor_boundary_supplies_the_verdict_not_the_runner(tmp_path: Path) -> None:
    """포함/제외 판정은 W5B 경계에서 온다 — runner 는 계산하지 않는다."""

    class SpyAttributor:
        def __init__(self) -> None:
            self.calls = 0
            self.seen: list[dict[str, Any]] = []

        def attribute_conditional_tokens(
            self, contract: TaskContract, entries: Any
        ) -> list[dict[str, Any]]:
            self.calls += 1
            self.seen = [dict(item) for item in entries]
            return [{**dict(item), "included": True} for item in entries]

    attributor = SpyAttributor()
    scout = SpyScout([PlannedAction("SELECT_DATE")])
    runner = make_runner(
        tmp_path, scout=scout, terminal=FakeTerminal(None), depth_attributor=attributor
    )
    picked = replace(ok_transition(0, endpoint=True), input_mode="MAP_PAN")
    driver = FakeDriver(transitions=[picked, picked])
    result = runner.run(make_contract(forbidden_actions=()), driver=driver, run_id="run-0703")
    assert attributor.calls == 1
    assert attributor.seen[0]["included"] is None, "runner 가 판정을 미리 채워 넘겼다"
    assert result.depth_conditional_tokens[0]["included"] is True


def test_verdict_without_a_basis_is_refused() -> None:
    """근거(`input_mode`) 없이 포함/제외만 있는 record 는 재검증이 불가능하다."""
    with pytest.raises(DepthAttributionEvidenceError, match="근거"):
        assert_depth_attribution_evidenced(
            [
                {
                    "action_token": "SELECT_DATE",
                    "step_index": 0,
                    "input_mode": None,
                    "included": True,
                }
            ]
        )
    # 양성 대조 — 근거가 있으면 통과한다.
    assert_depth_attribution_evidenced(
        [
            {
                "action_token": "SELECT_DATE",
                "step_index": 0,
                "input_mode": "FREE_TEXT",
                "included": False,
            }
        ]
    )


def test_input_mode_outside_the_delta9_vocabulary_is_refused(tmp_path: Path) -> None:
    scout = SpyScout([PlannedAction("SELECT_ORIGIN")])
    runner = make_runner(tmp_path, scout=scout)
    bogus = replace(ok_transition(0, endpoint=True), input_mode="VOICE")
    with pytest.raises(RunnerError, match="input_mode"):
        runner.run(make_contract(), driver=FakeDriver(transitions=[bogus]), run_id="run-0704")


def test_aggregate_declares_within_family_scope_and_the_preregistered_asymmetry() -> None:
    """검색 기반 family 의 높은 depth 는 결함이 아니라 과업 구조의 결과다 (Δ9 사전등록)."""
    aggregate = build_family_aggregate(
        family_id="F2",
        metric="activation_depth",
        records=[{"observation_id": "o1", "task_role": "PRIMARY"}],
    )
    assert aggregate["comparison_scope"] == "WITHIN_FAMILY_PRIMARY"
    assert aggregate["cross_family_use"] == "CROSS_FAMILY_DESCRIPTIVE_ONLY"
    assert "결함으로 처리하지 않는다" in aggregate["preregistered_note"]
