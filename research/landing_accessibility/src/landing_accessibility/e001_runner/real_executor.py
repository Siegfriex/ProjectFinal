"""실제 서비스 실행기 — `REAL_TARGET` + 승인된 `ExecutionScope` 전용.

`executor.py`(FIXTURE 실행기)와 **파일이 분리되어 있다.** 그 분리가 이 층의 안전
장치다: fixture 실행기는 `official_url` 이라는 문자열을 자기 파일 안에서 한 번도
읽지 않고, 이 파일은 `fixture_override` 를 한 번도 읽지 않는다. 그래서 어느 한쪽의
버그가 다른 쪽의 URL 을 여는 일이 **코드 상 성립하지 않는다.**

## 이 실행기가 하는 세 가지 확인 (순서가 의미를 갖는다)

1. `firewall.assert_real_target_scope_allowed` — scope 의 릴리스 문서를 런타임에 읽고
   (`P0_RELEASE.json`), target 이 그 scope 의 동결된 allowlist 안인지 확인한다.
   **브라우저를 켜기 전에** 끝난다.
2. `L0Collector.collect()` — 그 안에서 `assert_navigation_allowed` 가 같은 검사를
   **다시** 수행한다(항해 직전). 1이 통과했다고 2를 건너뛰지 않는다.
3. `guard.screen_candidates` — L0 후보에 금지된 계정 행동이 하나라도 있으면 `Scout`
   객체를 아예 만들지 않는다. FIXTURE 경로와 **완전히 같은 가드**를 쓴다.

## L0-only run 을 만들지 않는다

`run_l1_if_safe_real` 의 반환 dict 은 항상 `"l0"` 키에 L0 관측 전체를 담는다 —
가드가 막았을 때도, Scout 가 끝까지 돌았을 때도 마찬가지다. L0 만 있고 L1 종결
상태가 없는 run 은 이 경로에서 나오지 않는다(가드 차단도 `ACCOUNT_ACTION_BLOCKED`
라는 L1 종결 상태다).
"""

from __future__ import annotations

from typing import Any

from landing_accessibility.engine.evidence import EvidenceRun
from landing_accessibility.engine.firewall import (
    ExecutionMode,
    ExecutionScope,
    TargetAllowlist,
    assert_real_target_scope_allowed,
)
from landing_accessibility.engine.l0_collector import L0Collector, RealServiceTarget
from landing_accessibility.engine.l1_engine import Scout, ScoutBudget, TaskDefinition
from landing_accessibility.engine.vocabulary import InteractionArchetype

from .executor import default_task_definition
from .guard import screen_candidates
from .outcomes import TargetOutcome
from .plan import TargetSpec


class RealExecutorError(RuntimeError):
    """실제 수집 실행기 계약 위반."""


def _require_official_url(target: TargetSpec) -> str:
    url = (target.official_url or "").strip()
    if not url:
        raise RealExecutorError(
            f"target {target.target_id!r} 에 official_url 이 없다 — 실제 수집 실행기는 "
            "fixture_override 를 읽지 않으므로 열 URL 이 없다."
        )
    return url


def _real_target(target: TargetSpec) -> RealServiceTarget:
    return RealServiceTarget(
        web_target_id=target.target_id,
        official_url=_require_official_url(target),
        archetype=InteractionArchetype(target.interaction_archetype),
        task_id=f"task-{target.target_id}",
        canonical_service_key=target.canonical_service_key,
    )


def assert_target_executable(
    target: TargetSpec,
    *,
    scope: object = ExecutionScope.E000_FAST,
    allowlist: TargetAllowlist | None = None,
) -> None:
    """브라우저를 켜기 전에 scope 릴리스 + allowlist 를 확인한다."""
    assert_real_target_scope_allowed(
        scope,
        target_id=target.target_id,
        url=_require_official_url(target),
        canonical_service_key=target.canonical_service_key,
        allowlist=allowlist,
    )


def run_l0_real(
    target: TargetSpec,
    *,
    run: EvidenceRun,
    scope: object = ExecutionScope.E000_FAST,
    allowlist: TargetAllowlist | None = None,
) -> dict[str, Any]:
    """L0 관측만 수행한다. activation 없음.

    **이 함수를 단독으로 batch 경로에 쓰지 않는다** — L0-only run 이 되기 때문이다.
    `run_l1_if_safe_real` 이 이것을 감싼다.
    """
    assert_target_executable(target, scope=scope, allowlist=allowlist)
    collector = L0Collector(
        run,
        fixture_root=None,
        execution_mode=ExecutionMode.REAL_TARGET,
        execution_scope=scope,
    )
    observation = collector.collect(_real_target(target))
    return observation.as_dict()


def run_l1_if_safe_real(
    target: TargetSpec,
    *,
    run: EvidenceRun,
    scope: object = ExecutionScope.E000_FAST,
    allowlist: TargetAllowlist | None = None,
    task: TaskDefinition | None = None,
    budget: ScoutBudget | None = None,
) -> dict[str, Any]:
    """L0 → 계정 행동 가드 → (통과한 경우에만) L1 Scout.

    가드가 걸리면 `"outcome"` 이 `ACCOUNT_ACTION_BLOCKED` 이고 `"scout_invoked"` 는
    `False` 다 — `Scout` 객체 자체가 만들어지지 않았다는 증거다.
    """
    l0 = run_l0_real(target, run=run, scope=scope, allowlist=allowlist)
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

    resolved_task = task or default_task_definition(target)
    scout = Scout(
        fixture_root=None,
        budget=budget or ScoutBudget(),
        execution_mode=ExecutionMode.REAL_TARGET,
        execution_scope=scope,
        run=run,
    )
    entry, manifest = scout.scout(
        web_target_id=target.target_id,
        entry_real_url=_require_official_url(target),
        task=resolved_task,
    )
    result = entry.as_dict()
    result["scout_invoked"] = True
    result["task_manifest"] = manifest.as_dict() if manifest is not None else None
    result["l0"] = l0
    return result


__all__ = [
    "RealExecutorError",
    "assert_target_executable",
    "run_l0_real",
    "run_l1_if_safe_real",
]
