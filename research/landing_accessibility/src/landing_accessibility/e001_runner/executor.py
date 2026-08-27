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

from .guard import assess_reachable_candidates
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


def _resolve_signal_type(raw: str | None) -> RegionSignalType:
    """CSV/JSON에서 온 signal type 문자열을 엔진 enum으로 옮긴다.

    **값을 지어내지 않는다** — 비어 있거나(`None`/`""`) 이 엔진이 모르는 문자열이면
    `CODEBOOK_PENDING`이다. `CODEBOOK_PENDING`은 **부재(미도달)**를 뜻하지 **거부**를
    뜻하지 않는다(`D-R0-09`) — 상류 데이터가 실제로 아직 이 값을 정하지 못한
    것이므로, 이 함수가 임의의 signal type을 골라 채워 넣으면 그게 오히려 조작이다.
    """
    if not raw:
        return RegionSignalType.CODEBOOK_PENDING
    try:
        return RegionSignalType(raw)
    except ValueError:
        return RegionSignalType.CODEBOOK_PENDING


def default_task_definition(target: TargetSpec) -> TaskDefinition:
    """`target`에 실려 온 upstream task 필드로 `TaskDefinition`을 만든다.

    `T-A-W1-001` §2 (D-R0-07~09) 시정 전에는 이 함수가 `region_definition=None`·
    `endpoint_definition=None`·양쪽 signal_type=`CODEBOOK_PENDING`을 **인자와 무관한
    상수**로 반환했다 — `target`이 실제로 무엇을 실어 왔는지 한 번도 보지 않았다.
    그 결과 `representative_task_candidate_shadow.csv` 71행 전건이 다섯 필드를 갖고
    있었는데도(상류에서는 안 끊겼다) 여기서 lineage가 끊겼다.

    이제는 `target.task_id`/`region_definition`/`endpoint_definition`/
    `region_signal_type`/`endpoint_signal_type`을 **있는 그대로** 옮긴다. 서비스별
    정의가 실제로 아직 없는 target(P-A codebook 미동결)만 여전히
    `CODEBOOK_PENDING`/`None`이다 — 그건 이 함수가 지어낸 게 아니라 `target` 자체가
    그 값을 실어 온 것이다(`plan.py`→`firewall.py` 로더가 그대로 옮긴 CSV 원본값).
    """
    archetype = InteractionArchetype(target.interaction_archetype)
    return TaskDefinition(
        task_id=target.task_id or f"task-{target.target_id}",
        archetype=archetype,
        region_definition=target.region_definition,
        endpoint_definition=target.endpoint_definition,
        region_signal_type=_resolve_signal_type(target.region_signal_type),
        endpoint_signal_type=_resolve_signal_type(target.endpoint_signal_type),
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

    `T-A-W1-001` §1 시정: 판정은 이제 target-level이 아니라 candidate/state-level
    이다(`guard.assess_reachable_candidates`) — Scout가 실제로 클릭을 시도할 가능성이
    있는 후보(랜딩 상태에서 hittable하고 순위 안인 것)만 보고, 그중 안전한 대안이
    하나라도 있으면 막지 않는다. 판정에 쓴 후보 전체는 `"candidate_action_mask"`에
    evidence로 남는다(막혔든 안 막혔든).
    """
    l0 = run_l0(target, fixture_root=fixture_root, run=run)
    resolved_budget = budget or ScoutBudget()
    # `l0["primary_action_candidates"]`(저장용 curated 목록)에는 `hittable`이 없다
    # (`l0_collector.PrimaryActionCandidate`는 랭킹 필드만 갖는다) — Scout가 실제로
    # 보는 것과 같은 원본(raw probe) 후보 목록은 `raw_features`에 있다.
    raw_candidates = (l0.get("raw_features") or {}).get("primary_action_candidates") or []
    assessment = assess_reachable_candidates(
        raw_candidates, branching_limit=resolved_budget.branching_limit
    )
    if assessment.blocking is not None:
        risk = assessment.blocking
        return {
            "outcome": TargetOutcome.ACCOUNT_ACTION_BLOCKED.value,
            "scout_invoked": False,
            "blocked_category": risk.category,
            "blocked_reason": risk.reason,
            "candidate_action_mask": assessment.as_dict(),
            "l0_observation_id": l0.get("observation_id"),
            "l0": l0,
        }

    fixture_name = _require_fixture(target)
    resolved_task = task or default_task_definition(target)
    scout = Scout(
        fixture_root=fixture_root,
        budget=resolved_budget,
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
    result["candidate_action_mask"] = assessment.as_dict()
    # `T-A-W1-001` §2 — `l1_engine.TaskDefinition.mapping_frozen_allowed()`(W2 소유,
    # 읽기전용)를 실행 경로에 배선한다(`D-R0-09` 게이트 요구). **막지 않는다** —
    # `CODEBOOK_PENDING`은 부재이지 거부가 아니므로, 이 값은 evidence에 그대로
    # 기록되는 신호일 뿐이다. 지금까지는 이 함수가 `tests/test_pc_fixture_engine.py`
    # 밖에서 한 번도 불리지 않아 본수집 59건 전체가 `mapping_frozen_allowed=False`
    # 인 채로 아무 저항 없이 진행됐다 — 그 사실을 이제 evidence에서 볼 수 있다.
    result["mapping_frozen_allowed"] = resolved_task.mapping_frozen_allowed()
    return result


__all__ = ["ExecutorError", "default_task_definition", "run_l0", "run_l1_if_safe"]
