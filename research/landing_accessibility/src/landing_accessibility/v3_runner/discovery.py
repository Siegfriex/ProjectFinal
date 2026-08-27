"""V3 task-specific candidate discovery + Scout 바인딩 — `T-B-V3-STEP1-001` → W5D1.

## 범위 (Director 오케스트레이션 지침 — worker 당 narrow responsibility 하나)

이 파일 **하나만** W5D1 소유다. 병렬로 도는 다른 lane(W5A 계약 로더, W5B flow 정규화,
W5C surface 측정, W5D obstruction/terminal, W5E fixture 13종)의 파일은 여기서
만들지도 참조하지도 않는다 — `v3_runner/contracts.py`가 아직 없으므로 `task_contract`
파라미터는 **구조적 타입(duck typing)** 으로만 받는다(`TaskContractLike` 참고).
W5A 의 실제 dataclass 가 이 shape 을 만족하면 import 없이 그대로 맞물린다.

## 대표기능을 추론하지 않는다

`T-A-V3-SUPERSEDE-001` — RF 7-way classifier 는 v3 main critical path 에서
퇴역했다. 이 모듈의 어떤 함수도 candidate 의 "task label"을 추론·부여하지
않는다. 입력에 이미 `frozen_task`/`endpoint_contract`가 동결돼 들어오고,
`discover_task_candidates`는 구조적으로 관측 가능한 candidate 를 **열거·랭킹**
할 뿐이다 — 어떤 candidate가 "그 task 의 진짜 버튼인가"를 판정하지 않는다.
그 판정은 Scout 의 BFS 가 endpoint_contract 를 실제로 만족하는 경로를 찾는가로
사후에 결정된다(`03 §5` Scout → Freeze → Replay).

## Scout 바인딩 — freeze 를 건드리지 않는다

`engine/l1_engine.py`(Scout·Path Freeze·`replay()`)는 **W2 소유·`b28aaa5`
NOT_PASSED freeze** 다. `T-A-V3-SUPERSEDE-001`이 W2 코드 삭제 금지·freeze
유지를 명시했으므로 이 파일은 그 파일을 **한 글자도 고치지 않고** import 로만
읽는다. `run_task_aware_scout()`가 그 바인딩이다 — `TaskDefinition`을
`task_contract`로부터 만들어 **기존 `Scout`를 그대로** 호출한다(`e001_runner.
executor.default_task_definition`/`run_l1_if_safe`와 같은 패턴, V2 TargetSpec
대신 V3 task_contract 를 쓴다는 것만 다르다).

**한계 — 문서로 남긴다(설계 제약, "불가능하면 왜 불가능한지 적고 멈춰라")**:
`Scout._activation_candidates`(BFS 내부 tie-break)는 `l0_collector.min4_sort_key`
를 **하드코딩**해 호출한다(l1_engine.py 안에서 직접, 인자로 주입받지 않는다).
그 파일을 고치지 않는 한 Scout 내부의 실제 분기 순서를 이 모듈이 갈아끼울 수
없다 — **불가능하다.** 그래서 이 모듈의 `policy` 인자는 (1) `discover_task_
candidates`가 돌려주는 evidence용 랭킹에 적용되고, (2) Scout 자신의 BFS 에는
적용되지 않는다. 오늘은 두 랭킹이 항상 같다 — `policy` 기본값이 `min4_sort_key`
그 자체를 감싼 것이고 Scout 도 같은 함수를 쓰기 때문이다. A 가 `ruling_10`으로
"경로선택 규칙이 전 target 에 균일해야 한다"를 요구했는데, 지금 상태(Scout 가
하드코딩된 MIN-4 만 씀)가 이미 그 요구를 만족한다 — 모든 target 이 예외 없이
같은 규칙을 강제로 쓴다. `policy` 인터페이스는 (a) A 가 MIN 승계를 확정하지
않고 다른 규칙을 정할 경우를 위한 자리, (b) 언젠가 task-aware Scout 가 freeze
파일을 대체하며 실제로 주입 가능해질 때의 어댑터 경계로 남겨 둔다.

## 안전 — guard 를 그대로 쓴다

`e001_runner.guard`(내 소유)의 `ActionCategory`·`CandidateActionState`·
`blocking_state`·`DISABLED_OR_INERT`·`assess_reachable_candidates`를 새로
만들지 않고 그대로 재사용한다. 금지 행위 후보(credential·transaction·CAPTCHA
등)는 **존재는 evidence 로 남기고 활성화만 차단**한다(`D-R0-06`). 이 경계를
넘는 새 판정 로직을 여기서 만들지 않는다 — guard.py 가 유일한 정본이다.
"""

from __future__ import annotations

import sys
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol, runtime_checkable

_RESEARCH_ROOT = Path(__file__).resolve().parents[3]
if str(_RESEARCH_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(_RESEARCH_ROOT / "src"))

from landing_accessibility.e001_runner.guard import (  # noqa: E402
    ActionRisk,
    CandidateActionState,
    assess_reachable_candidates,
    classify_candidate_state,
)
from landing_accessibility.engine.evidence import EvidenceRun  # noqa: E402
from landing_accessibility.engine.firewall import ExecutionMode  # noqa: E402
from landing_accessibility.engine.l0_collector import (  # noqa: E402
    FixtureTarget,
    L0Collector,
    min4_sort_key,
)
from landing_accessibility.engine.l1_engine import (  # noqa: E402
    Scout,
    ScoutBudget,
    TaskDefinition,
    TaskEntry,
    TaskManifest,
)
from landing_accessibility.engine.vocabulary import (  # noqa: E402
    InteractionArchetype,
    RegionSignalType,
)


# ══════════════════════════════════════════════════════════════════════════
# task_contract — duck-typed. W5A 의 `contracts.py` 가 아직 없다.
# ══════════════════════════════════════════════════════════════════════════
@runtime_checkable
class TaskContractLike(Protocol):
    """`SSOTV3/02_DATA_SCHEMA_v3.0.md` `dim_task_contract`와 같은 필드 이름을
    쓴다 — W5A 의 실제 dataclass 가 이 이름을 쓰면 import 없이 구조적으로
    맞물린다(structural typing). 이 모듈은 이 Protocol 을 **강제하지 않는다**
    (아래 함수들은 `Mapping`도 받는다) — 최소 계약을 문서화하는 용도다.
    """

    task_id: str
    endpoint_contract: Any
    fixture_json: str
    #: `dim_task_family.legacy_archetype` — v3 는 archetype 을 추론하지 않고
    #: 동결된 값을 그대로 옮긴다(RF 7-way 미사용, `T-A-V3-SUPERSEDE-001`).
    legacy_archetype: str


TaskContract = TaskContractLike | Mapping[str, Any]


def _tc_get(task_contract: TaskContract, key: str, default: Any = None) -> Any:
    """`task_contract`가 dataclass 든 dict 든 같은 방식으로 읽는다."""
    if isinstance(task_contract, Mapping):
        return task_contract.get(key, default)
    return getattr(task_contract, key, default)


def _resolve_endpoint_contract(
    raw: Any,
) -> tuple[str | None, RegionSignalType]:
    """`endpoint_contract`는 SSOT 어디에도 내부 shape 이 분해돼 있지 않다
    (`02_DATA_SCHEMA_v3.0.md`·`03_COLLECTION_MEASUREMENT_SPEC_v3.0.md` 둘 다
    opaque blob 으로만 쓴다) — 그래서 이 함수가 **관대하게** 두 형태를 받는다:

    - 문자열 — 그대로 `endpoint_definition`, `signal_type`은 `TaskDefinition`
      기본값(`DOM_AX_ROLE`)을 쓴다.
    - `{"definition": ..., "signal_type": ...}` 매핑 — 둘 다 명시적으로 읽는다.

    W5A 의 `contracts.py`가 실제 shape 을 확정하면 이 함수만 바뀌면 된다 —
    나머지 파이프라인은 `TaskDefinition`만 보고 그 앞단을 모른다.
    """
    if raw is None:
        return None, RegionSignalType.CODEBOOK_PENDING
    if isinstance(raw, Mapping):
        definition = raw.get("definition")
        signal_raw = raw.get("signal_type")
        try:
            signal_type = (
                RegionSignalType(signal_raw) if signal_raw else RegionSignalType.DOM_AX_ROLE
            )
        except ValueError:
            signal_type = RegionSignalType.CODEBOOK_PENDING
        return (str(definition) if definition else None), signal_type
    return str(raw), RegionSignalType.DOM_AX_ROLE


def bind_task_definition(task_contract: TaskContract) -> TaskDefinition:
    """`task_contract`(V3, 동결)로 `TaskDefinition`(l1_engine.py, W2 소유·읽기전용)을
    만든다 — Scout 가 이해하는 유일한 입력 형태이므로, V3 계약을 Scout 에
    맞물리려면 이 변환이 있어야 한다.

    `region_definition`은 V3 계약에 대응 개념이 없다(V3 는 endpoint_contract
    만 갖는다, `03 §4`) — `None`으로 둔다. `TaskDefinition.mapping_frozen_
    allowed()`는 그래서 `region_signal_type`이 채워지지 않는 한 `False`이고,
    NED(영역 도달 최소 activation 수)는 이 경로에서 항상 `NULL`이 된다 —
    지어내지 않는다(`D-R0-09`와 같은 원칙). endpoint_contract 는 존재하므로
    IED/MPFED 산출 경로(`detect_endpoint_signal`)는 그대로 동작한다.
    """
    archetype_raw = _tc_get(task_contract, "legacy_archetype") or _tc_get(
        task_contract, "archetype"
    )
    if not archetype_raw:
        raise ValueError(
            "task_contract 에 legacy_archetype(또는 archetype)이 없다 — Scout 는 "
            "TaskDefinition.archetype 없이 gate 종류를 archetype 별로 가를 수 없다 "
            "(A2 §1.5.1a 규칙 E-6a). v3 도 이 값을 추론하지 않고 동결값을 그대로 옮긴다."
        )
    archetype = InteractionArchetype(archetype_raw)

    endpoint_definition, endpoint_signal_type = _resolve_endpoint_contract(
        _tc_get(task_contract, "endpoint_contract")
    )

    return TaskDefinition(
        task_id=str(_tc_get(task_contract, "task_id") or ""),
        archetype=archetype,
        region_definition=None,
        endpoint_definition=endpoint_definition,
        region_signal_type=RegionSignalType.CODEBOOK_PENDING,
        endpoint_signal_type=endpoint_signal_type,
    )


# ══════════════════════════════════════════════════════════════════════════
# 경로선택 정책 — 주입 가능. 기본값은 MIN-4(`min4_sort_key`, 읽기전용 재사용)
# ══════════════════════════════════════════════════════════════════════════
@dataclass(frozen=True)
class PathSelectionPolicy:
    """`A1 §2.6` 규칙 MIN-4(전순서 tie-break)를 갈아끼울 수 있게 감싼 것.

    `name`은 evidence 에 어떤 정책을 썼는지 남기기 위한 것이다(A `ruling_10`
    — 경로선택 규칙이 전 target 에 균일해야 matched comparison 이 성립한다).
    `sort_key`는 `l0_collector.min4_sort_key`와 같은 시그니처
    (`dict[str, Any] -> tuple`, 오름차순 정렬 키)여야 한다.

    이 정책은 **`discover_task_candidates`의 랭킹에만** 적용된다. `Scout` 내부
    BFS 는 여전히 `min4_sort_key`를 하드코딩해서 쓴다(모듈 docstring "Scout
    바인딩 — 설계 제약" 참고) — 오늘은 두 값이 항상 같으므로 실제 동작에는
    차이가 없다.
    """

    name: str
    sort_key: Callable[[dict[str, Any]], tuple[Any, ...]]


#: 기본 정책 — `min4_sort_key`를 그대로 감싼다(재구현하지 않는다).
MIN4_POLICY = PathSelectionPolicy(name="MIN-4", sort_key=min4_sort_key)


# ══════════════════════════════════════════════════════════════════════════
# TaskCandidate — discovery 결과 한 건
# ══════════════════════════════════════════════════════════════════════════
@dataclass(frozen=True)
class TaskCandidate:
    """`discover_task_candidates`가 돌려주는 후보 하나. `raw`는 probe 원본을
    그대로 보존한다(존재 evidence, `D-R0-03`) — 이 dataclass 의 다른 필드는
    그 원본에서 뽑은 것일 뿐 새 관측이 아니다.
    """

    selector: str
    tag: str | None
    role: str | None
    aria_label: str | None
    visible_text: str | None
    dom_order: int
    marked_primary: bool
    hittable: bool | None
    enabled: bool | None
    #: `guard.classify_candidate_state`의 9-state 판정 — 존재는 항상 기록되고
    #: (`D-R0-03`), 활성화 차단 여부는 `usable`로 별도 표시한다.
    guard_state: CandidateActionState
    #: `guard_state`가 SAFE·AUTH_ENTRY_ALLOWED_CONDITIONALLY 일 때만 True —
    #: Scout 가 실제로 클릭을 시도해도 안전한 후보라는 뜻이다.
    usable: bool
    #: `policy.sort_key` 적용 후 순위(0-based). `BRANCHING_LIMIT` 절단선이
    #: 이 순서를 본다(Scout 자신의 순서와, 정책이 MIN-4 인 한 일치한다).
    rank: int
    raw: dict[str, Any] = field(repr=False)


_USABLE_STATES = frozenset(
    {CandidateActionState.SAFE, CandidateActionState.AUTH_ENTRY_ALLOWED_CONDITIONALLY}
)


def discover_task_candidates(
    probe_state: Mapping[str, Any],
    task_contract: TaskContract,
    policy: PathSelectionPolicy | None = None,
) -> list[TaskCandidate]:
    """`probe_state`(L0 raw_features, `L0Observation.raw_features`) 에서 task
    candidate 를 열거·guard 판정·랭킹한다. **대표기능을 추론하지 않는다** — 이
    함수는 candidate 의 "task label"을 정하지 않는다(모듈 docstring 참고).

    후보 source(`03 §4`): `primary_action_candidates`(l0_probe.js) 하나만
    쓴다 — 그 소스가 `dom_order`(MIN-4 tie-break 의 필수 구조값,
    `Min4ProbeContractError`)를 갖는 **유일한** raw feature 군이고, `Scout.
    _activation_candidates`가 실제로 분기하는 후보 집합과 정확히 같다.

    **known limitation** — `03 §4`가 나열한 candidate source(button/link/tab
    /**menuitem**/input/**searchbox**/card)는 `primary_action_candidates`
    쿼리(`a[href],button,input[type=submit|button],[role=button|link|tab],
    nav a`)보다 넓다. `menuitem`/`searchbox`/일반 텍스트 `input`은 `l0_probe.js`
    의 다른 raw feature 군(`utility_input_widgets`·`region_signals.search_
    inputs`)에 있지만 그것들은 `dom_order`를 갖지 않는다 — `l0_probe.js`는
    W2 소유·읽기전용이라 이 함수가 그 결측을 채워 넣지 않는다(값을 지어내면
    그게 조작이다). 그래서 이 함수의 candidate universe 는 `primary_action_
    candidates`로 좁다 — 그런데 이건 타협이 아니라 **Scout 와의 일치를
    보장하는 선택**이다: Scout 자신도 그 두 raw feature 군을 전혀 보지 않으므로,
    거기 있는 요소를 후보로 냈어도 Scout 는 절대 클릭할 수 없다.
    """
    resolved_policy = policy or MIN4_POLICY
    raw_candidates = list(probe_state.get("primary_action_candidates") or [])

    ranked = sorted(raw_candidates, key=resolved_policy.sort_key)
    seen: set[str] = set()
    out: list[TaskCandidate] = []
    for rank, c in enumerate(ranked):
        if not isinstance(c, dict):
            continue
        sel = str(c.get("selector") or "")
        if not sel or sel in seen:
            continue
        seen.add(sel)
        state = classify_candidate_state(c)
        out.append(
            TaskCandidate(
                selector=sel,
                tag=c.get("tag"),
                role=c.get("role"),
                aria_label=c.get("aria_label"),
                visible_text=c.get("visible_text"),
                dom_order=int(c["dom_order"]),
                marked_primary=bool(c.get("marked_primary")),
                hittable=c.get("hittable"),
                enabled=c.get("enabled"),
                guard_state=state,
                usable=state in _USABLE_STATES,
                rank=rank,
                raw=c,
            )
        )
    return out


# ══════════════════════════════════════════════════════════════════════════
# Scout 바인딩 — freeze(l1_engine.py) 를 읽기전용으로 호출한다
# ══════════════════════════════════════════════════════════════════════════
@dataclass(frozen=True)
class TaskDiscoveryResult:
    """`run_task_aware_scout`의 반환값. `blocking`이 `None`이 아니면 `Scout`가
    **아예 만들어지지 않았다** — `entry`/`manifest`도 `None`이다(`D-R0-01`
    candidate/state-level 판정, `T-A-W1-001`과 같은 계약)."""

    task_id: str
    candidates: tuple[TaskCandidate, ...]
    blocking: ActionRisk | None
    entry: TaskEntry | None
    manifest: TaskManifest | None

    @property
    def scout_invoked(self) -> bool:
        return self.blocking is None


def run_task_aware_scout(
    task_contract: TaskContract,
    *,
    fixture_root: Path,
    run: EvidenceRun,
    budget: ScoutBudget | None = None,
    policy: PathSelectionPolicy | None = None,
) -> TaskDiscoveryResult:
    """L0 관측 → `discover_task_candidates` → guard 사전검사 → (통과 시) `Scout.
    scout()`. FIXTURE 전용이다 — `execution_mode`를 인자로 받지 않는다(이 lane
    은 offline 만, `T-B-V3-STEP1-001` 범위 축소: "실사이트 접속 0 유지").

    `guard.assess_reachable_candidates`(`T-A-W1-P2-DECIDED`와 완전히 같은
    함수)가 reachable 후보 전부가 forbidden/DISABLED_OR_INERT 면 **Scout를
    만들지 않는다** — `e001_runner.executor.run_l1_if_safe`와 정확히 같은
    안전 계약이다(그 함수를 재구현하지 않고 같은 guard 함수를 그대로 쓴다).
    """
    resolved_budget = budget or ScoutBudget()
    resolved_policy = policy or MIN4_POLICY
    task_id = str(_tc_get(task_contract, "task_id") or "")
    fixture_name = str(
        _tc_get(task_contract, "fixture_json") or _tc_get(task_contract, "fixed_fixture") or ""
    )
    if not fixture_name:
        raise ValueError(
            f"task_contract(task_id={task_id!r}) 에 fixture_json(또는 fixed_fixture)이 "
            "없다 — 이 lane 은 FIXTURE 전용이라 열 파일이 없으면 진행할 수 없다."
        )

    task_definition = bind_task_definition(task_contract)

    collector = L0Collector(run, fixture_root=fixture_root, execution_mode=ExecutionMode.FIXTURE)
    observation = collector.collect(
        FixtureTarget(
            web_target_id=task_id, fixture=fixture_name, archetype=task_definition.archetype
        )
    )
    probe_state = observation.raw_features
    candidates = discover_task_candidates(probe_state, task_contract, resolved_policy)

    raw_candidates = list(probe_state.get("primary_action_candidates") or [])
    assessment = assess_reachable_candidates(
        raw_candidates, branching_limit=resolved_budget.branching_limit
    )
    if assessment.blocking is not None:
        return TaskDiscoveryResult(
            task_id=task_id,
            candidates=tuple(candidates),
            blocking=assessment.blocking,
            entry=None,
            manifest=None,
        )

    scout = Scout(
        fixture_root=fixture_root,
        budget=resolved_budget,
        execution_mode=ExecutionMode.FIXTURE,
        run=run,
    )
    entry, manifest = scout.scout(
        web_target_id=task_id, entry_fixture=fixture_name, task=task_definition
    )
    return TaskDiscoveryResult(
        task_id=task_id,
        candidates=tuple(candidates),
        blocking=None,
        entry=entry,
        manifest=manifest,
    )


__all__ = [
    "MIN4_POLICY",
    "PathSelectionPolicy",
    "TaskCandidate",
    "TaskContract",
    "TaskContractLike",
    "TaskDiscoveryResult",
    "bind_task_definition",
    "discover_task_candidates",
    "run_task_aware_scout",
]
