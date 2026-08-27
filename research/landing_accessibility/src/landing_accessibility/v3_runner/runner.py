"""v3 수집 파이프라인 오케스트레이션 — task 는 화면에서 추론하지 않는다.

`SSOTV3/00 §9` 의 경로를 그대로 집행한다::

    Frozen Task Registry → Mobile Web Eligibility → L0/Scroll Surface Capture
      → Task-specific Candidate Binding → Scout → Path Freeze
      → Deterministic Replay → Flow Mart

## 이 파일이 하지 않는 것이 곧 이 파일의 명세다

| 하지 않음 | 근거 |
|---|---|
| 화면에서 대표기능/task family 를 추론 | `09 D3-02` · `D3-03` — RF 7-way classifier 는 critical path 에서 퇴역 |
| replay 가 깨졌을 때 자유탐색으로 대체 | `00 §9` 금지 · `03 §5` — `REPLAY_BROKEN` 으로 기록만 한다 |
| derived scalar(depth/menu_dependency/occlusion) 계산 | `09 D3-05` — Flow 가 raw primary, derived 는 W5B/W5C/W5D 소관 |
| 산출 불능을 0/FAIL 로 환산 | `09 D3-05` · `engine/l1_engine.py` 예산 규약 — 불능은 `None` |
| 네트워크 접근 | 이 모듈은 `SessionDriver` Protocol 뒤에만 붙는다. 여기에는 소켓이 없다 |

## replay 는 scout 를 **볼 수 없다**

`03 §5` 의 "깨지면 자유탐색으로 조용히 대체하지 않는다" 를 주석으로 적어 두면 다음 사람이
`except: return self._scout(...)` 한 줄로 되돌린다. 그래서 `replay()` 는 구조적으로
`self._scout` 를 참조하지 않는다 — 재탐색 코드가 **쓰여 있지 않다**. 실패는
`ReplayStatus.REPLAY_BROKEN` 과 `endpoint_status=None` 으로만 나간다.

## 세 개의 해시는 실행 **전에** 본다 (fail-closed)

1. `task_contract_hash` — 이 run 이 어떤 과업을 하기로 동결됐는지
2. `endpoint_contract_hash` — 어디서 멈추기로 동결됐는지
3. path manifest hash — replay 가 재생하는 경로가 freeze 당시 그대로인지 (`02 §8`)

셋 중 하나라도 부재/불일치면 브라우저를 열기 전에 거부한다. 열고 나서 거부하면
이미 실사이트에 접촉한 뒤다.

## RECONCILIATION SEAM

`TaskContract` · `FlowStep` 은 W5A `contracts.py` 가 최종 소유자다. 병렬 진행 중이라
아직 존재하지 않으므로 코디네이터가 확정한 형태 그대로 여기에 둔다. reconciliation 단계에서
`from .contracts import TaskContract, FlowStep` 로 교체하면 되도록 필드/순서를 손대지 않았다.
"""

from __future__ import annotations

import dataclasses
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Any, Protocol, runtime_checkable

from .evidence import (
    INPUT_MODE_VALUES,
    OBSERVATION_SCOPE_NODE,
    PRIMARY_TASK_FILTER_EXPR,
    TASK_ROLE_PRIMARY,
    TASK_ROLE_VALUES,
    EvidencePayload,
    EvidenceRunWriter,
    EvidenceSlot,
    ObservationKey,
    assert_coordinates_preserved,
    assert_depth_attribution_evidenced,
    assert_layer_qualified,
    canonical_json_bytes,
    denominator_for_metric,
    qualified_layer_text,
    sha256_of_bytes,
)

# ---------------------------------------------------------------------------
# RECONCILIATION SEAM — W5A `contracts.py` 가 최종 소유자
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class TaskContract:
    """수집 **전에** 동결된 과업 계약 (`02 §2 dim_task_contract` · `00 §1.2`)."""

    target_id: str
    family_id: str
    service: str
    starting_url: str
    frozen_task: str
    task_instruction: str
    fixed_fixture: str
    fixture_override: str | None
    endpoint_contract: str
    forbidden_actions: tuple[str, ...]
    task_contract_hash: str
    endpoint_contract_hash: str
    legacy_archetype: str | None = None
    mobile_web_eligibility: str = "PRECHECK_REQUIRED"
    #: `R3` (A `T-A-V3-STEP1-003`) — 본표본 n 은 `PRIMARY` 만 센다.
    #: F1 은행 10곳의 잔액조회 secondary task 가 분모를 늘리지 않게 하는 필드다.
    task_role: str = TASK_ROLE_PRIMARY


@dataclass(frozen=True)
class FlowStep:
    """`02 §4 fact_flow_step` — raw ordered action 한 건. derived 값은 여기 없다."""

    step_index: int
    action_token: str
    state_before_id: str
    state_after_id: str
    control_selector: str | None
    control_role: str | None
    control_visible_text: str | None
    control_accessible_name: str | None
    bbox_before: tuple[float, float, float, float] | None
    url_before: str
    url_after: str
    auth_gate_detected: bool
    endpoint_signal_detected: bool


# ---------------------------------------------------------------------------
# 닫힌 어휘 — `04 §2` · `03 §2` · `04 §4`
# ---------------------------------------------------------------------------

#: `04 §2` canonical action tokens. **이 집합 밖의 token 은 실행되지 않는다.**
#: 새 조작화(예: 결제/송금 실행 token)를 코드로 발명하는 경로를 어휘 차원에서 막는다.
CANONICAL_ACTION_TOKENS: frozenset[str] = frozenset(
    {
        "OPEN_GLOBAL_MENU",
        "OPEN_LOCAL_MENU",
        "SWITCH_TAB",
        "EXPAND_ACCORDION",
        "SELECT_CATEGORY",
        "SELECT_FUNCTION",
        "INPUT_QUERY",
        "SELECT_ORIGIN",
        "SELECT_DESTINATION",
        "SELECT_DATE",
        "SUBMIT_QUERY",
        "SELECT_RESULT",
        "OPEN_ITEM_DETAIL",
        "OPEN_PLACE_DETAIL",
        "DISMISS_OBSTRUCTION",
        "AUTH_GATE",
        "ENDPOINT_REACHED",
        "ABSTAIN",
    }
)

#: `T-A-V3-STEP1-006` Δ9 — `activation_depth` 토큰 귀속 확정표.
#: 기준 3항: ① 사용자의 의도적 조작인가 ② control 활성화인가 ③ 상태가 전이되는가.
DEPTH_IN_TOKENS: frozenset[str] = frozenset(
    {
        "OPEN_GLOBAL_MENU",
        "OPEN_LOCAL_MENU",
        "SWITCH_TAB",
        "EXPAND_ACCORDION",
        "SELECT_CATEGORY",
        "SELECT_FUNCTION",
        "SUBMIT_QUERY",
        "SELECT_RESULT",
        "OPEN_ITEM_DETAIL",
        "OPEN_PLACE_DETAIL",
    }
)

#: `AUTH_GATE` 가 OUT 인 이유는 기준 ① 이다 — **사용자 활성화가 아니라 마주친 상태**다.
#: terminal 기록에서 이 구분이 흐려지면 depth 가 조용히 1 씩 커진다.
DEPTH_OUT_TOKENS: frozenset[str] = frozenset(
    {"INPUT_QUERY", "DISMISS_OBSTRUCTION", "AUTH_GATE", "ENDPOINT_REACHED", "ABSTAIN"}
)

#: 입력수단에 따라 갈린다. `DROPDOWN`/`MAP_PAN` → 포함, `FREE_TEXT` → 제외,
#: `MIXED` → 실제 사용 수단 기준. **판정은 W5B `flow.py` 소관이고 runner 는 근거만 남긴다.**
DEPTH_CONDITIONAL_TOKENS: frozenset[str] = frozenset(
    {"SELECT_ORIGIN", "SELECT_DESTINATION", "SELECT_DATE"}
)

#: `AUTH_GATE` step 에 남기는 provenance — 활성화가 아니라 마주친 상태임을 기록에 못박는다.
AUTH_GATE_PROVENANCE = "ENCOUNTERED_STATE_NOT_USER_ACTIVATION"

#: family 내 비교가 primary 이고 cross-family 는 기술통계 중심이다 (`05` · Δ9 사전등록).
#: A 가 관측 0건 시점에 사전등록한 예상: 검색 기반 family(F2·F3·F5)의 depth 가 F1·F4 보다
#: 구조적으로 높다. **이 비대칭은 결함이 아니라 과업 구조의 결과다** — 집계가 그것을
#: defect 로 처리하지 않는다. 나중에 "예상대로였다"고 사후 서술하지 않기 위한 기록이다.
WITHIN_FAMILY_COMPARISON = "WITHIN_FAMILY_PRIMARY"
CROSS_FAMILY_COMPARISON = "CROSS_FAMILY_DESCRIPTIVE_ONLY"
PREREGISTERED_DEPTH_ASYMMETRY = (
    "T-A-V3-STEP1-006 Δ9 사전등록: 검색 기반 family(F2·F3·F5) 의 activation_depth 가 "
    "F1·F4 보다 구조적으로 높다. 검색을 거쳐야 하는 과업은 실제로 조작이 더 필요하다. "
    "결함으로 처리하지 않는다."
)

#: `03 §2` mobile-web eligibility. `ELIGIBLE_PUBLIC_MOBILE_WEB` 만 수집으로 넘어간다.
ELIGIBILITY_PROCEEDABLE = "ELIGIBLE_PUBLIC_MOBILE_WEB"
ELIGIBILITY_VALUES: frozenset[str] = frozenset(
    {
        ELIGIBILITY_PROCEEDABLE,
        "APP_REQUIRED_EXCLUDE",
        "ACCESS_BLOCKED_REVIEW",
        "URL_REMAP_REQUIRED",
    }
)

#: `04 §4 endpoint_status`. 이 밖의 값을 runner 가 만들지 않는다.
ENDPOINT_STATUS_VALUES: frozenset[str] = frozenset(
    {
        "REACHED",
        "AUTH_GATE",
        "PUBLIC_WEB_UNOBSERVABLE",
        "APP_REQUIRED",
        "EVIDENCE_DEFECT",
        "BLOCKED",
        "ABSTAIN",
    }
)

PATH_MANIFEST_VERSION = "v3.0"


class Phase(StrEnum):
    """`00 §9` 수집 경로의 단계. 어디까지 갔는지가 결과에 남는다."""

    REGISTRY = "FROZEN_TASK_REGISTRY"
    ELIGIBILITY = "MOBILE_WEB_ELIGIBILITY"
    SURFACE = "L0_SCROLL_SURFACE_CAPTURE"
    BINDING = "TASK_SPECIFIC_CANDIDATE_BINDING"
    SCOUT = "SCOUT"
    FREEZE = "PATH_FREEZE"
    REPLAY = "DETERMINISTIC_REPLAY"
    MART = "FLOW_MART"


class ReplayStatus(StrEnum):
    """`03 §5` — replay 결과는 endpoint_status 와 별개로 남긴다."""

    NOT_ATTEMPTED = "NOT_ATTEMPTED"
    REPLAYED = "REPLAYED"
    REPLAY_BROKEN = "REPLAY_BROKEN"


class RunnerError(RuntimeError):
    """v3 runner 계약 위반."""


class ContractHashMismatchError(RunnerError):
    """`02 §8` — 동결 해시 부재/불일치. 실행 전에 거부한다 (fail-closed)."""


class PathManifestHashMismatchError(RunnerError):
    """frozen path manifest 해시 불일치 — replay 가 다른 경로를 재생하려 했다."""


class ProhibitedActionError(RunnerError):
    """`03 §7` · `§8` · `00 §4` — 계약이 금지한 조작을 실행하려 했다."""


class MissingDependencyError(RunnerError):
    """fail-closed — 필수 경계 구현이 주입되지 않았다."""


# ---------------------------------------------------------------------------
# 다른 lane 과의 경계 — Protocol 로만 붙는다
# ---------------------------------------------------------------------------


@runtime_checkable
class ContractHasher(Protocol):
    """W5A `contracts.py` — 동결 계약의 정규 해시를 재계산한다."""

    def task_contract_hash(self, contract: TaskContract) -> str | None: ...

    def endpoint_contract_hash(self, contract: TaskContract) -> str | None: ...


@runtime_checkable
class EligibilityChecker(Protocol):
    """W1 `discovery.py` — `03 §2` precheck. task 를 수행하지 않고 채널만 본다."""

    def check(self, contract: TaskContract) -> str: ...


@runtime_checkable
class CandidateBinder(Protocol):
    """W1 `discovery.py` — `03 §4`. task label 을 바꾸지 않고 후보만 묶는다."""

    def bind(
        self, contract: TaskContract, states: Sequence[SurfaceObservation]
    ) -> Sequence[Mapping[str, Any]]: ...


@runtime_checkable
class ScoutStrategy(Protocol):
    """`03 §5` Scout — 다음 activation 하나를 제안한다. 끝이면 `None`."""

    def propose_next(
        self,
        contract: TaskContract,
        states: Sequence[SurfaceObservation],
        candidates: Sequence[Mapping[str, Any]],
        taken: Sequence[FlowStep],
    ) -> PlannedAction | None: ...


@runtime_checkable
class SafetyGuard(Protocol):
    """W5G `safety.py` — `03 §7` · `§8` 금지조작 집행. 위반이면 예외를 던진다."""

    def assert_action_allowed(self, contract: TaskContract, action: PlannedAction) -> None: ...


@runtime_checkable
class SessionDriver(Protocol):
    """브라우저/fixture 세션. 이 lane 은 fixture/fake 로만 테스트한다."""

    def capture_surface(self, contract: TaskContract) -> Sequence[SurfaceObservation]: ...

    def activate(self, action: PlannedAction) -> RawTransition: ...


@runtime_checkable
class SurfaceMeasurer(Protocol):
    """W5C `surface.py` — `04 §4` Surface/Geometry derived. runner 는 계산하지 않는다."""

    def measure(
        self, contract: TaskContract, states: Sequence[SurfaceObservation]
    ) -> Any | None: ...


@runtime_checkable
class FlowNormalizer(Protocol):
    """W5B `flow.py` — `04 §5` derived(activation_depth·menu_dependency·flow_step_count)."""

    def normalize(self, contract: TaskContract, steps: Sequence[FlowStep]) -> Any | None: ...


@runtime_checkable
class ObstructionAnalyzer(Protocol):
    """W5D `obstruction.py` — `03 §9` task-specific occlusion/dismiss-required."""

    def analyze(
        self,
        contract: TaskContract,
        states: Sequence[SurfaceObservation],
        steps: Sequence[FlowStep],
    ) -> Any | None: ...


@runtime_checkable
class DepthAttributor(Protocol):
    """W5B `flow.py` — Δ9 조건부 토큰의 포함/제외 **판정**. runner 는 근거만 모은다."""

    def attribute_conditional_tokens(
        self, contract: TaskContract, entries: Sequence[Mapping[str, Any]]
    ) -> Sequence[Mapping[str, Any]]: ...


@runtime_checkable
class TerminalClassifier(Protocol):
    """W5D `terminal.py` — `04 §4 endpoint_status`. runner 가 직접 판정하지 않는다."""

    def classify(self, contract: TaskContract, steps: Sequence[FlowStep]) -> str | None: ...


# ---------------------------------------------------------------------------
# raw 자료구조 — runner 가 모으는 것은 여기까지다
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SurfaceObservation:
    """`02 §3 fact_surface_state` 의 raw 부분. derived 필드는 들어 있지 않다."""

    state_index: str
    scroll_y: float
    viewport_width: int
    viewport_height: int
    url: str
    payload: EvidencePayload


@dataclass(frozen=True)
class PlannedAction:
    """scout 가 제안한 activation 하나. 실행 전에 safety + 어휘 검사를 받는다."""

    action_token: str
    control_selector: str | None = None
    control_role: str | None = None
    control_visible_text: str | None = None
    control_accessible_name: str | None = None

    def as_record(self) -> dict[str, Any]:
        return {
            "action_token": self.action_token,
            "control_selector": self.control_selector,
            "control_role": self.control_role,
            "control_visible_text": self.control_visible_text,
            "control_accessible_name": self.control_accessible_name,
        }


@dataclass(frozen=True)
class RawTransition:
    """driver 가 관측한 한 activation 의 before/after. 판정값은 없다."""

    ok: bool
    state_before_id: str
    state_after_id: str
    url_before: str
    url_after: str
    bbox_before: tuple[float, float, float, float] | None = None
    auth_gate_detected: bool = False
    endpoint_signal_detected: bool = False
    payload_before: EvidencePayload | None = None
    payload_after: EvidencePayload | None = None
    failure_reason: str | None = None
    #: Δ9 — 조건부 토큰의 **실제 사용 수단**. `MIXED` control 이라도 여기에는 실사용값이 온다.
    #: 관측하지 못했으면 `None` 이다 (`09 D3-05` — 0/FREE_TEXT 로 바꾸지 않는다).
    input_mode: str | None = None


@dataclass(frozen=True)
class V3RunResult:
    """한 service-task 의 한 run 결과. raw 와 derived 가 분리되어 있다."""

    observation_id: str
    service_id: str
    task_id: str
    run_id: str
    phase_reached: Phase
    refusal: str | None = None
    eligibility: str | None = None
    raw_states: tuple[SurfaceObservation, ...] = ()
    raw_steps: tuple[FlowStep, ...] = ()
    replay_status: ReplayStatus = ReplayStatus.NOT_ATTEMPTED
    replay_failure_reason: str | None = None
    endpoint_status: str | None = None
    derived_surface: Any | None = None
    derived_flow: Any | None = None
    derived_obstruction: Any | None = None
    path_manifest: Mapping[str, Any] | None = None
    path_manifest_sha256: str | None = None
    evidence_manifest_sha256: str | None = None
    evidence_run_dir: Path | None = None
    scout_budget_exhausted: bool = False
    #: `R3` — mart 의 모든 관측 행이 task_role 을 갖는다.
    task_role: str = TASK_ROLE_PRIMARY
    #: Δ9 — `(action_token, step_index, input_mode, included)` raw 근거.
    depth_conditional_tokens: tuple[Mapping[str, Any], ...] = ()

    def as_mart_record(self) -> dict[str, Any]:
        """`02 §4 fact_flow_observation` 의 raw 부분을 mart 행으로 낸다.

        derived scalar 는 여기에 없다 — 그 자리는 W5B/W5C/W5D 산출물이 채운다
        (`09 D3-05`). `AUTH_GATE`/`ABSTAIN` 은 `endpoint_status` · `action_token`
        키 아래에만 놓이고, 나가기 전에 `assert_layer_qualified` 가 그것을 확인한다 (R6-Q8).
        """
        record: dict[str, Any] = {
            "observation_id": self.observation_id,
            "service_id": self.service_id,
            "task_id": self.task_id,
            "run_id": self.run_id,
            "task_role": self.task_role,
            "phase_reached": self.phase_reached.value,
            "eligibility": self.eligibility,
            "endpoint_status": self.endpoint_status,
            "replay_status": self.replay_status.value,
            "replay_failure_reason": self.replay_failure_reason,
            "scout_budget_exhausted": self.scout_budget_exhausted,
            "path_manifest_sha256": self.path_manifest_sha256,
            "evidence_manifest_sha256": self.evidence_manifest_sha256,
            "comparison_scope": WITHIN_FAMILY_COMPARISON,
            "depth_conditional_tokens": [dict(item) for item in self.depth_conditional_tokens],
            "action_sequence_raw": [
                {
                    "step_index": step.step_index,
                    "action_token": step.action_token,
                    "state_before_id": step.state_before_id,
                    "state_after_id": step.state_after_id,
                    "control_selector": step.control_selector,
                    "control_role": step.control_role,
                    "control_visible_text": step.control_visible_text,
                    "control_accessible_name": step.control_accessible_name,
                    "bbox_before": list(step.bbox_before) if step.bbox_before else None,
                    "url_before": step.url_before,
                    "url_after": step.url_after,
                    "auth_gate_detected": step.auth_gate_detected,
                    "endpoint_signal_detected": step.endpoint_signal_detected,
                    # Δ9 기준 ① — AUTH_GATE 는 활성화가 아니라 마주친 상태다.
                    "auth_gate_provenance": (
                        AUTH_GATE_PROVENANCE if step.action_token == "AUTH_GATE" else None
                    ),
                }
                for step in self.raw_steps
            ],
        }
        assert_layer_qualified(record)
        assert_coordinates_preserved(record)
        assert_depth_attribution_evidenced(record["depth_conditional_tokens"])
        return record


# ---------------------------------------------------------------------------
# path manifest — freeze 산출물. evidence manifest 와 hash 로 이어진다 (`02 §8`)
# ---------------------------------------------------------------------------


def build_path_manifest(
    *, key: ObservationKey, contract: TaskContract, steps: Sequence[FlowStep]
) -> dict[str, Any]:
    """`03 §5 Freeze` — normalized action token + raw selector/evidence 를 manifest 화."""
    return {
        "path_manifest_version": PATH_MANIFEST_VERSION,
        "observation_id": key.observation_id(),
        "service_id": key.service_id,
        "task_id": key.task_id,
        "run_id": key.run_id,
        "task_contract_hash": contract.task_contract_hash,
        "endpoint_contract_hash": contract.endpoint_contract_hash,
        "task_role": contract.task_role,
        "steps": [
            {
                "step_index": step.step_index,
                "action_token": step.action_token,
                "state_before_id": step.state_before_id,
                "state_after_id": step.state_after_id,
                "control_selector": step.control_selector,
                "control_role": step.control_role,
                "control_visible_text": step.control_visible_text,
                "control_accessible_name": step.control_accessible_name,
                "url_before": step.url_before,
                "url_after": step.url_after,
            }
            for step in steps
        ],
    }


def path_manifest_sha256(manifest: Mapping[str, Any]) -> str:
    return sha256_of_bytes(canonical_json_bytes(dict(manifest)))


def verify_path_manifest_hash(manifest: Mapping[str, Any], declared_sha256: str | None) -> str:
    """세 번째 해시 — frozen path 가 freeze 당시 그대로인지 (`02 §8`). 부재도 거부다."""
    if not declared_sha256:
        raise PathManifestHashMismatchError(
            "path manifest 해시가 없다 — 해시 없는 frozen path 는 replay 하지 않는다 (02 §8)"
        )
    actual = path_manifest_sha256(manifest)
    if actual != declared_sha256:
        raise PathManifestHashMismatchError(
            f"path manifest 해시 불일치: declared={declared_sha256} actual={actual}"
        )
    return actual


# ---------------------------------------------------------------------------
# runner
# ---------------------------------------------------------------------------


@dataclass
class ScoutBudget:
    """예산은 금지목록의 기계화다 — 선언만으로는 얕은 진입이 full task 로 변질된다.

    예산에 걸린 관측은 "N 이 아니라 N 회 안에서는 관측되지 않았다" 이며 `None` 으로 나간다.
    """

    max_activations: int = 8


class V3Runner:
    """`00 §9` 파이프라인 오케스트레이터.

    입력은 `TaskContract` **하나**다. 대표기능을 추론하지 않고, 화면에서 task 를 다시 정하지
    않는다. derived 계산은 전부 경계 밖(W5B/W5C/W5D)에 있다.
    """

    def __init__(
        self,
        *,
        evidence_root: Path,
        contract_hasher: ContractHasher,
        safety: SafetyGuard,
        eligibility: EligibilityChecker | None = None,
        binder: CandidateBinder | None = None,
        scout: ScoutStrategy | None = None,
        surface_measurer: SurfaceMeasurer | None = None,
        flow_normalizer: FlowNormalizer | None = None,
        obstruction: ObstructionAnalyzer | None = None,
        terminal: TerminalClassifier | None = None,
        depth_attributor: DepthAttributor | None = None,
        budget: ScoutBudget | None = None,
    ) -> None:
        if contract_hasher is None:
            raise MissingDependencyError(
                "contract_hasher 없이는 해시 검증을 할 수 없다 (fail-closed)"
            )
        if safety is None:
            raise MissingDependencyError("safety guard 없이는 activation 을 실행하지 않는다")
        self._evidence_root = Path(evidence_root)
        self._hasher = contract_hasher
        self._safety = safety
        self._eligibility = eligibility
        self._binder = binder
        self._scout = scout
        self._surface_measurer = surface_measurer
        self._flow_normalizer = flow_normalizer
        self._obstruction = obstruction
        self._terminal = terminal
        self._depth_attributor = depth_attributor
        self._budget = budget or ScoutBudget()

    # -- fail-closed 해시 검증 ------------------------------------------------

    def verify_contract_hashes(self, contract: TaskContract) -> None:
        """`task_contract_hash` · `endpoint_contract_hash` 를 실행 **전에** 검증한다.

        부재도 불일치와 같은 취급이다 — 해시가 없는 계약은 무엇으로 동결됐는지 알 수 없다.
        """
        if contract.task_role not in TASK_ROLE_VALUES:
            raise ContractHashMismatchError(
                f"task_role 이 R3 어휘 밖이다: {contract.task_role!r} — 실행 거부 (fail-closed)"
            )
        declared_task = contract.task_contract_hash
        declared_endpoint = contract.endpoint_contract_hash
        if not declared_task:
            raise ContractHashMismatchError("task_contract_hash 가 없다 — 실행 거부 (fail-closed)")
        if not declared_endpoint:
            raise ContractHashMismatchError(
                "endpoint_contract_hash 가 없다 — 실행 거부 (fail-closed)"
            )
        actual_task = self._hasher.task_contract_hash(contract)
        if not actual_task or actual_task != declared_task:
            raise ContractHashMismatchError(
                f"task_contract_hash 불일치: declared={declared_task} actual={actual_task}"
            )
        actual_endpoint = self._hasher.endpoint_contract_hash(contract)
        if not actual_endpoint or actual_endpoint != declared_endpoint:
            raise ContractHashMismatchError(
                f"endpoint_contract_hash 불일치: declared={declared_endpoint} actual={actual_endpoint}"
            )

    # -- 조작 허용 검사 -------------------------------------------------------

    def _assert_action_allowed(self, contract: TaskContract, action: PlannedAction) -> None:
        """어휘 → 계약 금지목록 → W5G safety 순으로 본다. 하나라도 걸리면 실행하지 않는다."""
        if action.action_token not in CANONICAL_ACTION_TOKENS:
            raise ProhibitedActionError(
                f"{action.action_token} 은 04 §2 canonical token 이 아니다 — 새 조작화 금지"
            )
        if action.action_token in contract.forbidden_actions:
            raise ProhibitedActionError(
                f"{action.action_token} 은 이 계약의 forbidden_actions 다 ({contract.target_id})"
            )
        self._safety.assert_action_allowed(contract, action)

    # -- 파이프라인 ----------------------------------------------------------

    def run(
        self,
        contract: TaskContract,
        *,
        driver: SessionDriver,
        run_id: str,
        service_id: str | None = None,
        task_id: str | None = None,
    ) -> V3RunResult:
        """`00 §9` 전체 경로. scout 는 여기서 **정확히 한 번의 탐색 국면**만 갖는다."""
        key = ObservationKey(
            service_id=service_id or contract.target_id,
            task_id=task_id or contract.frozen_task,
            run_id=run_id,
        )
        base = _empty_result(key, Phase.REGISTRY, task_role=contract.task_role)

        # 1. Frozen Task Registry — 해시 검증이 먼저다. 실패하면 세션을 열지 않는다.
        self.verify_contract_hashes(contract)

        # 2. Mobile Web Eligibility
        eligibility = contract.mobile_web_eligibility
        if self._eligibility is not None:
            eligibility = self._eligibility.check(contract)
        if eligibility not in ELIGIBILITY_VALUES:
            raise RunnerError(f"03 §2 밖의 eligibility 값이다: {eligibility!r}")
        if eligibility != ELIGIBILITY_PROCEEDABLE:
            return dataclasses.replace(
                base,
                phase_reached=Phase.ELIGIBILITY,
                eligibility=eligibility,
                refusal=f"eligibility={eligibility}",
            )

        writer = EvidenceRunWriter(self._evidence_root, key).open()

        # 3. L0 / Scroll Surface Capture
        states = self._capture_surface(contract, driver=driver, writer=writer)

        # 4. Task-specific Candidate Binding — task label 은 여기서 바뀌지 않는다
        candidates: Sequence[Mapping[str, Any]] = ()
        if self._binder is not None:
            candidates = tuple(self._binder.bind(contract, states))

        # 5. Scout
        scout_steps, scout_modes, budget_exhausted = self._scout_path(
            contract, driver=driver, writer=writer, states=states, candidates=candidates
        )

        # 6. Path Freeze
        manifest = build_path_manifest(key=key, contract=contract, steps=scout_steps)
        manifest_sha = path_manifest_sha256(manifest)

        # 7. Deterministic Replay — 여기서부터 self._scout 는 참조되지 않는다
        replayed_steps, replay_modes, replay_status, failure_reason = self._replay_steps(
            contract, driver=driver, manifest=manifest, declared_sha256=manifest_sha
        )

        # 8. Flow Mart — derived 는 전부 경계 밖에서 온다
        replayed_ok = replay_status is ReplayStatus.REPLAYED
        final_steps = replayed_steps if replayed_ok else scout_steps
        final_modes = replay_modes if replayed_ok else scout_modes
        depth_records = self._depth_conditional_records(contract, final_steps, final_modes)
        if depth_records:
            writer.write_json_slot(
                OBSERVATION_SCOPE_NODE,
                EvidenceSlot.DEPTH_ATTRIBUTION,
                {"depth_conditional_tokens": [dict(item) for item in depth_records]},
            )

        seal = writer.seal(path_manifest_sha256=manifest_sha)

        return self._to_mart(
            base,
            contract=contract,
            eligibility=eligibility,
            states=states,
            steps=final_steps,
            replay_status=replay_status,
            failure_reason=failure_reason,
            manifest=manifest,
            manifest_sha=manifest_sha,
            seal_evidence_sha=seal.evidence_manifest_sha256,
            run_dir=seal.run_dir,
            budget_exhausted=budget_exhausted,
            depth_records=depth_records,
        )

    def replay(
        self,
        contract: TaskContract,
        *,
        driver: SessionDriver,
        manifest: Mapping[str, Any],
        declared_sha256: str | None,
        run_id: str,
        service_id: str | None = None,
        task_id: str | None = None,
    ) -> V3RunResult:
        """frozen path 만 재생한다.

        **이 메서드의 본문에는 `self._scout` 가 나오지 않는다.** `03 §5` 의 "깨지면 자유탐색으로
        조용히 대체하지 않는다" 를 주석이 아니라 부재로 집행한다. 실패는 `REPLAY_BROKEN` 과
        `endpoint_status=None` 으로만 나간다 (`09 D3-05` — 불능은 0/FAIL 이 아니다).
        """
        key = ObservationKey(
            service_id=service_id or contract.target_id,
            task_id=task_id or contract.frozen_task,
            run_id=run_id,
        )
        base = _empty_result(key, Phase.REGISTRY, task_role=contract.task_role)
        self.verify_contract_hashes(contract)
        actual_sha = verify_path_manifest_hash(manifest, declared_sha256)

        steps, modes, replay_status, failure_reason = self._replay_steps(
            contract, driver=driver, manifest=manifest, declared_sha256=actual_sha
        )
        return self._to_mart(
            base,
            contract=contract,
            eligibility=contract.mobile_web_eligibility,
            states=(),
            steps=steps,
            replay_status=replay_status,
            failure_reason=failure_reason,
            manifest=manifest,
            manifest_sha=actual_sha,
            seal_evidence_sha=None,
            run_dir=None,
            budget_exhausted=False,
            depth_records=self._depth_conditional_records(contract, steps, modes),
        )

    # -- 단계 구현 -----------------------------------------------------------

    def _capture_surface(
        self,
        contract: TaskContract,
        *,
        driver: SessionDriver,
        writer: EvidenceRunWriter,
    ) -> tuple[SurfaceObservation, ...]:
        """`03 §3` — S0 안정화 후 고정 scroll 정책으로 S1..Sn. scroll 은 depth 가 아니다."""
        captured: list[SurfaceObservation] = []
        for index, observed in enumerate(driver.capture_surface(contract)):
            node_id = f"s{index:03d}"
            payload = dataclasses.replace(observed.payload, node_id=node_id)
            writer.write_payload(payload)
            captured.append(dataclasses.replace(observed, payload=payload))
        return tuple(captured)

    def _scout_path(
        self,
        contract: TaskContract,
        *,
        driver: SessionDriver,
        writer: EvidenceRunWriter,
        states: Sequence[SurfaceObservation],
        candidates: Sequence[Mapping[str, Any]],
    ) -> tuple[tuple[FlowStep, ...], tuple[str | None, ...], bool]:
        """`03 §5 Scout` — 각 activation 마다 before/after evidence 를 저장한다."""
        if self._scout is None:
            return (), (), False
        steps: list[FlowStep] = []
        modes: list[str | None] = []
        exhausted = False
        while True:
            if len(steps) >= self._budget.max_activations:
                exhausted = True
                break
            action = self._scout.propose_next(contract, states, candidates, tuple(steps))
            if action is None:
                break
            self._assert_action_allowed(contract, action)
            transition = driver.activate(action)
            self._write_transition_evidence(writer, len(steps), transition)
            if not transition.ok:
                break
            steps.append(_to_flow_step(len(steps), action, transition))
            modes.append(_validated_input_mode(transition.input_mode))
            if transition.endpoint_signal_detected or transition.auth_gate_detected:
                break
        return tuple(steps), tuple(modes), exhausted

    def _replay_steps(
        self,
        contract: TaskContract,
        *,
        driver: SessionDriver,
        manifest: Mapping[str, Any],
        declared_sha256: str,
    ) -> tuple[tuple[FlowStep, ...], tuple[str | None, ...], ReplayStatus, str | None]:
        """frozen manifest 를 결정적으로 재생한다. 재탐색 경로는 이 함수에 없다."""
        verify_path_manifest_hash(manifest, declared_sha256)
        planned = manifest.get("steps", [])
        if not planned:
            return (), (), ReplayStatus.NOT_ATTEMPTED, None
        replayed: list[FlowStep] = []
        modes: list[str | None] = []
        for record in planned:
            action = PlannedAction(
                action_token=str(record["action_token"]),
                control_selector=record.get("control_selector"),
                control_role=record.get("control_role"),
                control_visible_text=record.get("control_visible_text"),
                control_accessible_name=record.get("control_accessible_name"),
            )
            self._assert_action_allowed(contract, action)
            transition = driver.activate(action)
            if not transition.ok:
                reason = transition.failure_reason or "replay step failed"
                return tuple(replayed), tuple(modes), ReplayStatus.REPLAY_BROKEN, reason
            replayed.append(_to_flow_step(len(replayed), action, transition))
            modes.append(_validated_input_mode(transition.input_mode))
        return tuple(replayed), tuple(modes), ReplayStatus.REPLAYED, None

    def _depth_conditional_records(
        self,
        contract: TaskContract,
        steps: Sequence[FlowStep],
        modes: Sequence[str | None],
    ) -> tuple[Mapping[str, Any], ...]:
        """Δ9 — 조건부 토큰의 **귀속 근거**를 raw 로 모은다. 포함/제외는 여기서 정하지 않는다.

        `included` 자리는 W5B `flow.py` 의 판정이 들어온다. 경계가 없으면 `None` 으로
        남는다 — 부재를 `False` 로 바꾸면 "제외했다"는 판정이 조용히 생겨난다.
        """
        entries: list[dict[str, Any]] = [
            {
                "action_token": step.action_token,
                "step_index": step.step_index,
                "input_mode": modes[index] if index < len(modes) else None,
                "included": None,
            }
            for index, step in enumerate(steps)
            if step.action_token in DEPTH_CONDITIONAL_TOKENS
        ]
        if not entries or self._depth_attributor is None:
            assert_depth_attribution_evidenced(entries)
            return tuple(entries)
        attributed = [
            dict(item)
            for item in self._depth_attributor.attribute_conditional_tokens(contract, entries)
        ]
        assert_depth_attribution_evidenced(attributed)
        return tuple(attributed)

    def _write_transition_evidence(
        self, writer: EvidenceRunWriter, step_index: int, transition: RawTransition
    ) -> None:
        for suffix, payload in (
            ("before", transition.payload_before),
            ("after", transition.payload_after),
        ):
            if payload is None:
                continue
            node_id = f"step{step_index:04d}_{suffix}"
            writer.write_payload(dataclasses.replace(payload, node_id=node_id))

    def _to_mart(
        self,
        base: V3RunResult,
        *,
        contract: TaskContract,
        eligibility: str | None,
        states: Sequence[SurfaceObservation],
        steps: Sequence[FlowStep],
        replay_status: ReplayStatus,
        failure_reason: str | None,
        manifest: Mapping[str, Any],
        manifest_sha: str,
        seal_evidence_sha: str | None,
        run_dir: Path | None,
        budget_exhausted: bool,
        depth_records: tuple[Mapping[str, Any], ...] = (),
    ) -> V3RunResult:
        """`00 §9 Flow Mart` — raw 는 그대로 싣고 derived 는 **전부 위임**한다.

        경계 구현이 없으면 그 자리는 `None` 이다. runner 안에 대체 계산이 없다
        (`09 D3-05` — 산출 불능을 0/FAIL 로 바꾸지 않는다).
        """
        endpoint_status: str | None = None
        if replay_status is not ReplayStatus.REPLAY_BROKEN and self._terminal is not None:
            endpoint_status = self._terminal.classify(contract, steps)
            if endpoint_status is not None and endpoint_status not in ENDPOINT_STATUS_VALUES:
                raise RunnerError(f"04 §4 밖의 endpoint_status 다: {endpoint_status!r}")

        derived_surface = (
            self._surface_measurer.measure(contract, states)
            if self._surface_measurer is not None
            else None
        )
        derived_flow = (
            self._flow_normalizer.normalize(contract, steps)
            if self._flow_normalizer is not None
            else None
        )
        derived_obstruction = (
            self._obstruction.analyze(contract, states, steps)
            if self._obstruction is not None
            else None
        )
        return dataclasses.replace(
            base,
            phase_reached=Phase.MART,
            eligibility=eligibility,
            raw_states=tuple(states),
            raw_steps=tuple(steps),
            replay_status=replay_status,
            replay_failure_reason=failure_reason,
            endpoint_status=endpoint_status,
            derived_surface=derived_surface,
            derived_flow=derived_flow,
            derived_obstruction=derived_obstruction,
            path_manifest=dict(manifest),
            path_manifest_sha256=manifest_sha,
            evidence_manifest_sha256=seal_evidence_sha,
            evidence_run_dir=run_dir,
            scout_budget_exhausted=budget_exhausted,
            task_role=contract.task_role,
            depth_conditional_tokens=depth_records,
        )


def _validated_input_mode(mode: str | None) -> str | None:
    """Δ9 어휘 밖의 입력수단은 받지 않는다. 관측 못 한 것은 `None` 그대로 둔다."""
    if mode is None:
        return None
    if mode not in INPUT_MODE_VALUES:
        raise RunnerError(f"Δ9 밖의 input_mode 다: {mode!r}")
    return mode


def _to_flow_step(index: int, action: PlannedAction, transition: RawTransition) -> FlowStep:
    return FlowStep(
        step_index=index,
        action_token=action.action_token,
        state_before_id=transition.state_before_id,
        state_after_id=transition.state_after_id,
        control_selector=action.control_selector,
        control_role=action.control_role,
        control_visible_text=action.control_visible_text,
        control_accessible_name=action.control_accessible_name,
        bbox_before=transition.bbox_before,
        url_before=transition.url_before,
        url_after=transition.url_after,
        auth_gate_detected=transition.auth_gate_detected,
        endpoint_signal_detected=transition.endpoint_signal_detected,
    )


def build_family_aggregate(
    *,
    family_id: str,
    metric: str,
    records: Sequence[Mapping[str, Any]],
    filter_expr: str = PRIMARY_TASK_FILTER_EXPR,
) -> dict[str, Any]:
    """family-level 집계 한 건 — **필터 조건 문자열과 분모 이름을 산출물에 싣는다**.

    `R3` 이 요구하는 것은 "PRIMARY 로 필터했다"는 주장이 아니라 필터 **조건 자체**가
    산출물에 남는 것이다. 주장과 증거를 구분하는 이 프로젝트의 반복 규율과 같다.
    분모는 `R2` 표에서 고른다 — 진입 flow 지표는 `AUTH_GATE` 여부와 무관하게
    evidence-bearing 을 쓴다.
    """
    if filter_expr != PRIMARY_TASK_FILTER_EXPR:
        raise RunnerError(
            f"본표본 집계 필터는 {PRIMARY_TASK_FILTER_EXPR!r} 로 고정이다 (R3): {filter_expr!r}"
        )
    denominator = denominator_for_metric(metric)
    included = [record for record in records if record.get("task_role") == TASK_ROLE_PRIMARY]
    excluded = [record for record in records if record.get("task_role") != TASK_ROLE_PRIMARY]
    aggregate = {
        "family_id": family_id,
        "metric": metric,
        "applied_filter": filter_expr,
        "denominator_name": denominator,
        "denominator_n": len(included),
        "input_row_count": len(records),
        "comparison_scope": WITHIN_FAMILY_COMPARISON,
        "cross_family_use": CROSS_FAMILY_COMPARISON,
        "preregistered_note": PREREGISTERED_DEPTH_ASYMMETRY,
        "excluded_row_count": len(excluded),
        "excluded_observation_ids": [str(record.get("observation_id")) for record in excluded],
        "included_observation_ids": [str(record.get("observation_id")) for record in included],
    }
    assert_layer_qualified(aggregate)
    return aggregate


def _empty_result(
    key: ObservationKey, phase: Phase, *, task_role: str = TASK_ROLE_PRIMARY
) -> V3RunResult:
    return V3RunResult(
        observation_id=key.observation_id(),
        service_id=key.service_id,
        task_id=key.task_id,
        run_id=key.run_id,
        phase_reached=phase,
        task_role=task_role,
    )


__all__ = [
    "AUTH_GATE_PROVENANCE",
    "CANONICAL_ACTION_TOKENS",
    "CROSS_FAMILY_COMPARISON",
    "DEPTH_CONDITIONAL_TOKENS",
    "DEPTH_IN_TOKENS",
    "DEPTH_OUT_TOKENS",
    "ELIGIBILITY_PROCEEDABLE",
    "ELIGIBILITY_VALUES",
    "ENDPOINT_STATUS_VALUES",
    "PREREGISTERED_DEPTH_ASYMMETRY",
    "PRIMARY_TASK_FILTER_EXPR",
    "TASK_ROLE_PRIMARY",
    "TASK_ROLE_VALUES",
    "WITHIN_FAMILY_COMPARISON",
    "CandidateBinder",
    "ContractHashMismatchError",
    "ContractHasher",
    "DepthAttributor",
    "EligibilityChecker",
    "FlowNormalizer",
    "FlowStep",
    "MissingDependencyError",
    "ObstructionAnalyzer",
    "PathManifestHashMismatchError",
    "Phase",
    "PlannedAction",
    "ProhibitedActionError",
    "RawTransition",
    "ReplayStatus",
    "RunnerError",
    "SafetyGuard",
    "ScoutBudget",
    "ScoutStrategy",
    "SessionDriver",
    "SurfaceMeasurer",
    "SurfaceObservation",
    "TaskContract",
    "TerminalClassifier",
    "V3RunResult",
    "V3Runner",
    "build_family_aggregate",
    "build_path_manifest",
    "path_manifest_sha256",
    "qualified_layer_text",
    "verify_path_manifest_hash",
]
