"""기본 FIXTURE 실행기 — P-C 엔진(`L0Collector`/`Scout`)을 호출하는 얇은 어댑터.

이 모듈은 엔진을 다시 만들지 않는다. `L0Collector.collect()`와 `Scout.scout()`을
그대로 부르고, 그 사이에 계정 행동 가드(`guard.screen_candidates`)를 끼워 넣을
뿐이다.

## 이 실행기가 `official_url`을 절대 읽지 않는 이유

`TargetSpec.fixture_override`만 읽는다. `official_url`은 로드는 되지만(계획
호환성을 위해) 이 실행기 코드 어디에도 등장하지 않는다 — 실수로 `f"file://{...}"`
조합에 섞여 들어갈 여지 자체를 없앤다. `plan.validate_no_real_navigation_fields_required`
가 배치 시작 전에 `fixture_override` 누락을 걸러내므로, 이 실행기에 도달하는
target은 전부 로컬 fixture를 가리킨다.

## L0 vs L1

- `run_l0`: `L0Collector.collect()`만 호출한다. **어떤 primary action도 클릭하지
  않는다** — L0 자체가 관측·후보 랭킹·interrupt dismiss만 하고 activation은
  하지 않기 때문에, 계정 행동 가드가 필요조차 없는 가장 안전한 경로다.
- `run_l1_if_safe`: L0로 얻은 candidate 목록을 먼저 가드에 통과시키고,
  통과한 target만 `Scout.scout()`을 호출한다. 걸리면 `Scout`를 아예 만들지도
  않는다. **이 함수의 반환 dict은 항상 `"l0"` 키에 L0 관측 전체를 담는다**
  (2026-08-27, Claude A 지시: `BatchRunner._default_fixture_executor`가 이제
  이 함수를 표준 경로로 쓰므로, L0 관측 자체를 L1 결과에서 잃어버리지 않아야
  한다 — 가드가 막았을 때도, Scout가 끝까지 돌았을 때도 마찬가지다).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from landing_accessibility.engine.evidence import EvidenceRun
from landing_accessibility.engine.firewall import ExecutionMode
from landing_accessibility.engine.l0_collector import FixtureTarget, L0Collector
from landing_accessibility.engine.l1_engine import Scout, ScoutBudget, TaskDefinition
from landing_accessibility.engine.vocabulary import InteractionArchetype, RegionSignalType

from .guard import screen_candidates
from .outcomes import TargetOutcome
from .plan import TargetSpec


class ExecutorError(RuntimeError):
    """target 실행기 계약 위반 — fixture_override 누락 등."""


def _require_fixture(target: TargetSpec) -> str:
    if not target.fixture_override:
        raise ExecutorError(
            f"target {target.target_id!r} 에 fixture_override 가 없다 — "
            "FIXTURE 실행기는 official_url 을 절대 읽지 않으므로 열 파일이 없다."
        )
    return target.fixture_override


def default_task_definition(target: TargetSpec) -> TaskDefinition:
    """target의 archetype만으로 만들 수 있는 최소 `TaskDefinition`.

    실제 서비스별 `region_definition`/`endpoint_definition`은 P-A endpoint
    codebook이 동결하기 전에는 존재하지 않는다 (`A1 §1.8`). 그래서 여기서는
    `RegionSignalType.CODEBOOK_PENDING`을 그대로 둔다 — 이 상태에서 Scout를
    돌리면 QUERY를 제외한 모든 archetype은 area/endpoint 신호가 결코 성립하지
    않고, gate가 없으면 예산 소진으로 `UNRESOLVED`에 도달한다. 그것이 **정직한
    결과**다 — codebook 없이 endpoint를 만들어내지 않는다.
    """
    archetype = InteractionArchetype(target.interaction_archetype)
    return TaskDefinition(
        task_id=f"task-{target.target_id}",
        archetype=archetype,
        region_definition=None,
        endpoint_definition=None,
        region_signal_type=RegionSignalType.CODEBOOK_PENDING,
        endpoint_signal_type=RegionSignalType.CODEBOOK_PENDING,
    )


def run_l0(target: TargetSpec, *, fixture_root: Path, run: EvidenceRun) -> dict[str, Any]:
    """L0 관측만 수행한다. activation 없음 — 가드가 필요 없는 경로."""
    fixture_name = _require_fixture(target)
    archetype = InteractionArchetype(target.interaction_archetype)
    collector = L0Collector(run, fixture_root=fixture_root, execution_mode=ExecutionMode.FIXTURE)
    observation = collector.collect(
        FixtureTarget(web_target_id=target.target_id, fixture=fixture_name, archetype=archetype)
    )
    return observation.as_dict()


def run_l1_if_safe(
    target: TargetSpec,
    *,
    fixture_root: Path,
    run: EvidenceRun,
    task: TaskDefinition | None = None,
    budget: ScoutBudget | None = None,
) -> dict[str, Any]:
    """L0로 후보를 얻어 가드를 통과한 target만 `Scout.scout()`을 호출한다.

    가드가 걸리면 반환 dict의 `"outcome"`이 `ACCOUNT_ACTION_BLOCKED`이고
    `"scout_invoked"`는 `False`다 — 이 플래그가 "Scout를 아예 부르지 않았다"는
    증거이며, 테스트가 이 플래그와 함께 click spy로 실제 클릭 0회를 확인한다.
    """
    l0 = run_l0(target, fixture_root=fixture_root, run=run)
    candidates = l0.get("primary_action_candidates") or []

    risk = screen_candidates(candidates)
    if risk is not None:
        return {
            "outcome": TargetOutcome.ACCOUNT_ACTION_BLOCKED.value,
            "scout_invoked": False,
            "blocked_category": risk.category,
            "blocked_reason": risk.reason,
            "l0_observation_id": l0.get("observation_id"),
            "l0": l0,
        }

    fixture_name = _require_fixture(target)
    resolved_task = task or default_task_definition(target)
    scout = Scout(
        fixture_root=fixture_root,
        budget=budget or ScoutBudget(),
        execution_mode=ExecutionMode.FIXTURE,
        run=run,
    )
    entry, manifest = scout.scout(
        web_target_id=target.target_id, entry_fixture=fixture_name, task=resolved_task
    )
    result = entry.as_dict()
    result["scout_invoked"] = True
    result["task_manifest"] = manifest.as_dict() if manifest is not None else None
    result["l0"] = l0
    return result


__all__ = ["ExecutorError", "default_task_definition", "run_l0", "run_l1_if_safe"]
