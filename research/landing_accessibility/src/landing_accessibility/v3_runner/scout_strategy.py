"""`ScoutStrategy` 구현 — `runner.py`(W5F) 가 정의한 Protocol 두 개(`ScoutStrategy`)
중 소유자가 없던 하나를 W5D1(discovery/Scout 담당)이 맡는다.

## 계약 (`runner.py` 원문)

```python
class ScoutStrategy(Protocol):
    def propose_next(self, contract, states, candidates, taken) -> PlannedAction | None: ...
```

`None`을 반환하면 runner 가 탐색을 끝낸다 — 이 함수가 경로의 모양을 결정한다.
runner 의 실제 호출부(`_scout_path`)를 읽으면 이 함수가 매 activation 마다
**같은 `states`/`candidates`**를 받는다는 것을 알 수 있다 — candidate 재탐색은
runner 의 다음 버전(재귀 BFS)이 할 일이고, 지금은 **하나의 고정된 candidate
목록에서 순위대로 하나씩 제안**하는 형태다.

## 재사용 — 새로 만들지 않는다

- 경로선택 랭킹: `discovery.PathSelectionPolicy`(W5D1 자신의 것, `discovery.py`
  가 이미 `min4_sort_key`를 감싸 뒀다) 그대로 받는다.
- 금지 행위 판정: `safety.ActivationSafetyGuard`(W5G)를 그대로 쓴다.
  `guard.py`(e001_runner, 내 소유)를 W5G 가 이미 읽기전용으로 재사용했으므로,
  이 파일이 다시 그 계약을 재구현하면 정본이 셋으로 늘어난다.

## known limitation — 인터페이스 이름 불일치 (내가 만든 게 아니다)

`runner.py`의 `SafetyGuard` Protocol 은 `.assert_action_allowed(contract,
action)`라는 메서드명을 선언한다(`runner.py:_assert_action_allowed`가 그
이름으로 호출한다). 그런데 W5G 가 실제로 만든 클래스는 `ActivationSafetyGuard`
이고 그 메서드는 `.authorize(candidate, *, method=...)`(예외를 던짐)와
`.evaluate(candidate) -> ActivationDecision`(예외 없음) 둘뿐이다 —
`assert_action_allowed`라는 이름의 메서드가 없다. `runner.py`를 그대로 두고
`ActivationSafetyGuard`를 넘기면 `self._safety.assert_action_allowed(...)`
호출에서 `AttributeError`가 난다.

**이건 W5F(runner.py)·W5G(safety.py) 사이의 조정 문제이지 이 파일이 고칠
자리가 아니다** — 둘 다 내 소유가 아니다. 이 파일(`ScoutStrategy` 구현)은
runner 의 이 버그와 **독립적으로** 올바르다: `propose_next` 자체가 제안
**전에** `ActivationSafetyGuard.evaluate()`로 걸러내므로, 설령 runner 의
`_assert_action_allowed`가 나중에 예외 없이 통과(버그로 인해 그 검사 자체가
깨져 있어도)하더라도 이 strategy 는 애초에 금지 후보를 내보내지 않는다.
그래도 이 이름 불일치 자체는 완료 보고에 별도로 적는다 — B 가 W5F/W5G 조정
때 고쳐야 한다.

## 정책 두 개 — 둘 다 주입 가능, 둘 다 기본값은 v2 MIN 규칙의 v3 판본

1. `PathSelectionPolicy`(`discovery.py`) — 후보 랭킹. 기본 `MIN4_POLICY`.
2. `ScoutStopPolicy`(이 파일) — 중단 조건. 기본 `default_stop_policy()`가
   MIN-3(직전 step 이 이미 terminal 신호를 냈으면 중단)·MIN-7(strategy 자체
   예산 초과) 을 흉내 낸다. **v3 승계가 확정되지 않았다** — 그래서 하드코딩하지
   않고 갈아끼울 수 있게 만들었다(`discovery.py`에서 한 것과 같은 처리).

   `runner.py`의 `_scout_path`도 **자기 예산**(`self._budget.max_activations`)
   과 **자기 terminal 감지**(`transition.endpoint_signal_detected or
   transition.auth_gate_detected`, 매 activation 직후)를 이미 갖고 있다 —
   그건 하드코딩이고 freeze 밖(runner.py, W5F 소유, 이 티켓에서 고치지 않는다)
   이라 이 파일이 손댈 수 없다. 그래서 이 정책 객체가 적용되는 자리는
   **runner 의 하드코딩된 정지 조건보다 먼저(또는 별도로) strategy 스스로
   멈추는 조건**이다 — 두 계층이 하나는 freeze, 하나는 주입 가능이라는 것
   자체가 A `ruling_10`이 걱정하는 "두 계층이 서로 다른 정책일 수 있다"의
   실례다. 아래 known limitation 에 다시 적는다.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from .contracts import TaskContract
from .discovery import DEFAULT_V3_PATH_POLICY, PathSelectionPolicy
from .runner import (
    BRANCH_ELIGIBLE_TOKENS,
    CANONICAL_ACTION_TOKENS,
    CandidateBindingContractError,
    FlowStep,
    PlannedAction,
    SurfaceObservation,
)
from .safety import ActivationSafetyGuard


# ══════════════════════════════════════════════════════════════════════════
# 중단 정책 — 주입 가능. 기본값은 MIN-3/MIN-7 의 v3 잠정판(A 승계 판정 대기)
# ══════════════════════════════════════════════════════════════════════════
@dataclass(frozen=True)
class ScoutStopPolicy:
    """`should_stop(contract, states, taken) -> bool`. `True`면 `propose_next`가
    후보를 보지도 않고 `None`을 반환한다.

    `name`은 evidence 용(어떤 정책을 썼는지 남긴다 — `discovery.PathSelectionPolicy`
    와 같은 이유)."""

    name: str
    should_stop: Callable[[TaskContract, Sequence[SurfaceObservation], Sequence[FlowStep]], bool]


def _min3_min7_should_stop(
    contract: TaskContract,
    states: Sequence[SurfaceObservation],
    taken: Sequence[FlowStep],
    *,
    max_activations: int,
) -> bool:
    """`A1 §2.6` 규칙 MIN-3(terminal 에서 종료)·MIN-7(예산 초과는 관측 없음)의
    v3 잠정판. **v2 문서라 v3 승계가 A 판정 대기다** — 그래서 하드코딩하지 않고
    이 함수를 감싼 `ScoutStopPolicy` 객체로만 노출한다(`default_stop_policy`).

    MIN-3 — `taken`의 **마지막** step 이 이미 `auth_gate_detected`나
    `endpoint_signal_detected`를 냈으면 멈춘다. `runner.py._scout_path`가 매
    activation 직후 같은 조건으로 이미 loop 를 끊는다(하드코딩, 이 파일 밖) —
    이 검사는 그 판단이 **strategy 자신에게도** 보이게 하는 중복 방어선이다.

    MIN-7 — `len(taken) >= max_activations`면 "최소가 아니라 관측 없음"으로
    멈춘다. `runner.py`도 `self._budget.max_activations`로 자기 예산을 이미
    강제한다 — 이 값은 그것과 **독립된, strategy 자체의** 예산이다(더 보수적인
    값을 넣고 싶을 때 runner 를 고치지 않고 여기서 조일 수 있다).
    """
    if taken:
        last = taken[-1]
        if last.auth_gate_detected or last.endpoint_signal_detected:
            return True
    return len(taken) >= max_activations


def default_stop_policy(*, max_activations: int = 8) -> ScoutStopPolicy:
    """기본 중단 정책 — MIN-3/MIN-7 잠정판. `max_activations`는 `ScoutBudget`
    (`l1_engine.py`, v2)의 `max_activations_per_task` 기본값(8)과 맞췄다 —
    v3 가 다른 값을 승계하면 이 인자만 바꾸면 된다(하드코딩이 아니다)."""
    return ScoutStopPolicy(
        name="MIN-3-MIN-7-provisional",
        should_stop=lambda contract, states, taken: _min3_min7_should_stop(
            contract, states, taken, max_activations=max_activations
        ),
    )


class ScoutBranchSetError(ValueError):
    """`Δ30-branch` — 분기 후보로 낼 수 없는 `action_token` 이다.

    `[Δ30 인용]` *"분기 후보 = `Δ9` 의 IN 10종 + CONDITIONAL 3종(control 활성화인 경우).
    `INPUT_QUERY` · `DISMISS_OBSTRUCTION` · `AUTH_GATE` · `ENDPOINT_REACHED` · `ABSTAIN` 은
    분기 대상이 아니다."* / *"popup 닫기를 분기 후보에 넣으면 닫기가 depth 로 세어진다."*
    """


# ══════════════════════════════════════════════════════════════════════════
# candidate → action_token — 구조 신호만 쓴다(대표기능을 추론하지 않는다)
# ══════════════════════════════════════════════════════════════════════════
def _classify_action_token(candidate: Mapping[str, Any]) -> str:
    """`04 §2` canonical action token 중 **구조적으로 확실히 가를 수 있는 것만**
    가른다. 나머지는 전부 `SELECT_FUNCTION`으로 보수적으로 묶는다.

    **known limitation** — `OPEN_GLOBAL_MENU`/`OPEN_LOCAL_MENU`/`EXPAND_ACCORDION`
    /`SELECT_CATEGORY`/`INPUT_QUERY`/`SELECT_ORIGIN`/`SELECT_DESTINATION`/
    `SELECT_DATE`/`SUBMIT_QUERY`/`OPEN_ITEM_DETAIL`/`OPEN_PLACE_DETAIL`을
    가르려면 라벨/문구 의미 해석(예: "지도"→지도 위젯, "다음"→날짜 선택)이
    필요한데, 그건 대표기능 추론과 같은 형태의 위험이다(`T-A-V3-SUPERSEDE-001`).
    `discover_task_candidates`의 candidate source(`primary_action_candidates`)
    에는 그걸 구조적으로(라벨 없이) 가를 신호(예: `aria-haspopup`, 상위
    `<nav>`/`<form>` 소속 여부)가 애초에 없다 — `l0_probe.js` 읽기전용이라
    이 함수가 신호를 지어내지 않는다. `SELECT_FUNCTION`으로 묶는 근거:
    v3 는 task 가 이미 동결돼 들어오므로("사전지정 task 기능 control을
    선택한다") 이 기본값은 허위 정밀도보다 안전하다.

    `role=tab`(ARIA 의미가 명시적)과 `in_list_container`(l0_probe.js 가 이미
    구조적으로 판정해 candidate 에 실어 주는 값, 라벨 해석이 아니다) 두 개만
    구조적으로 확실하다.
    """
    role = str(candidate.get("role") or "").strip().lower()
    if role == "tab":
        token = "SWITCH_TAB"
    elif candidate.get("in_list_container"):
        token = "SELECT_RESULT"
    else:
        token = "SELECT_FUNCTION"
    # `Δ30-branch` — **분기 대상 집합 = depth 집합**(`Δ9` IN 10 + CONDITIONAL 3).
    # 이 함수가 `DISMISS_OBSTRUCTION` 같은 OUT 토큰을 내면 그 조작이 depth 로 세어진다.
    # 지금은 셋 다 IN 집합 안이며, 그 사실을 이 자리에서 강제한다(현재 아무것도 그것을
    # 붙들고 있지 않았다).
    if token not in BRANCH_ELIGIBLE_TOKENS:
        raise ScoutBranchSetError(
            f"{token} 은 Δ30-branch 의 분기 대상 집합 밖이다 — 분기 후보로 내면 "
            "그 조작이 activation_depth 로 세어진다 (Δ9 OUT 5종은 분기 대상이 아니다)"
        )
    return token


def _to_planned_action(candidate: Mapping[str, Any]) -> PlannedAction:
    return PlannedAction(
        action_token=_classify_action_token(candidate),
        control_selector=str(candidate.get("selector") or "") or None,
        control_role=(str(candidate.get("role")) if candidate.get("role") else None)
        or (str(candidate.get("tag")) if candidate.get("tag") else None),
        control_visible_text=(
            str(candidate.get("visible_text")) if candidate.get("visible_text") else None
        ),
        control_accessible_name=(
            str(candidate.get("aria_label"))
            if candidate.get("aria_label")
            else (str(candidate.get("visible_text")) if candidate.get("visible_text") else None)
        ),
    )


# ══════════════════════════════════════════════════════════════════════════
# MinPathScoutStrategy — 기본 구현
# ══════════════════════════════════════════════════════════════════════════
class MinPathScoutStrategy:
    """`ScoutStrategy` Protocol(`runner.py`) 구현. 매 호출마다:

    1. `stop_policy.should_stop(...)`이 참이면 `None`(요구 3).
    2. `policy.sort_key`로 candidate 를 랭킹한다(요구 1, `discovery.
       PathSelectionPolicy` 재사용, 기본 MIN-4).
    3. 이미 `taken`(같은 selector)인 candidate 는 건너뛴다(요구 2 — 재제안 금지).
    4. `ActivationSafetyGuard.observe()`로 **존재를 항상 기록**(`D-R0-06`)하고,
       `.evaluate()`가 막는 candidate 는 제안하지 않는다(요구 4 — 제안 **전에**
       guard 를 통과시킨다). `hittable=False`/`enabled=False`(`DISABLED_OR_
       INERT`, W1 T-A-W1-P2-DECIDED 판정)도 같은 이유로 건너뛴다.
    5. 남은 것 중 랭킹 1위를 `PlannedAction`으로 반환한다. 하나도 없으면 `None`.
    """

    def __init__(
        self,
        *,
        policy: PathSelectionPolicy | None = None,
        stop_policy: ScoutStopPolicy | None = None,
        safety_guard_factory: Callable[[TaskContract], ActivationSafetyGuard] | None = None,
    ) -> None:
        self.policy = policy or DEFAULT_V3_PATH_POLICY
        self.stop_policy = stop_policy or default_stop_policy()
        self._safety_guard_factory = safety_guard_factory or (
            lambda contract: ActivationSafetyGuard(contract)
        )
        self._guards: dict[str, ActivationSafetyGuard] = {}
        self._observed: dict[str, set[str]] = {}

    def _contract_key(self, contract: TaskContract) -> str:
        key = getattr(contract, "task_contract_hash", None)
        return str(key) if key else str(id(contract))

    def _guard_for(self, contract: TaskContract) -> ActivationSafetyGuard:
        key = self._contract_key(contract)
        if key not in self._guards:
            self._guards[key] = self._safety_guard_factory(contract)
            self._observed[key] = set()
        return self._guards[key]

    def propose_next(
        self,
        contract: TaskContract,
        states: Sequence[SurfaceObservation],
        candidates: Sequence[Mapping[str, Any]],
        taken: Sequence[FlowStep],
    ) -> PlannedAction | None:
        if self.stop_policy.should_stop(contract, states, taken):
            return None

        # `Δ32-R30` — 형태 위반을 **조용히 건너뛰지 않는다.** 예전에는 여기서
        # `isinstance(c, Mapping)` 로 전건을 걸러 `None` 을 반환했고, runner 가 그것을
        # 정상 종료로 읽어 "깨끗한 0-activation 행"이 나왔다. 계약 위반은 관측이 아니다.
        offenders = [
            (index, type(c).__name__)
            for index, c in enumerate(candidates)
            if not isinstance(c, Mapping)
        ]
        if offenders:
            raise CandidateBindingContractError(
                f"propose_next 가 Mapping 이 아닌 후보를 받았다 (총 {len(candidates)} 건 중 "
                f"{len(offenders)} 건): {offenders[:5]}. Δ32 — 계측기 결함이지 관측이 아니다."
            )

        taken_selectors = {s.control_selector for s in taken if s.control_selector}
        guard = self._guard_for(contract)
        observed_selectors = self._observed[self._contract_key(contract)]

        ranked = sorted(
            (c for c in candidates if c.get("selector")),
            # `PathSelectionPolicy.sort_key`는 `dict[str, Any]`로 타입돼 있다
            # (`discovery.py`, `min4_sort_key`와 시그니처를 맞췄다) — `candidates`는
            # `Mapping`(Protocol 계약)이라 `dict()`로 좁혀서 넘긴다. `min4_sort_key`
            # 는 `.get()`만 쓰므로 동작은 완전히 같다.
            key=lambda c: self.policy.sort_key(dict(c)),
        )
        seen: set[str] = set()
        for c in ranked:
            selector = str(c.get("selector") or "")
            if not selector or selector in seen:
                continue
            seen.add(selector)

            # `D-R0-06` — 존재는 taken/차단 여부와 무관하게 항상 기록한다.
            # 같은 selector 를 여러 번 observe 하지 않는다(evidence 중복 방지,
            # `candidates` 가 매 호출 동일하므로 안 하면 호출마다 중복된다).
            if selector not in observed_selectors:
                guard.observe(c)
                observed_selectors.add(selector)

            if selector in taken_selectors:
                continue  # 요구 2 — 재제안 금지

            if c.get("hittable") is False or c.get("enabled") is False:
                continue  # DISABLED_OR_INERT — 존재는 위에서 이미 기록했다

            decision = guard.evaluate(c)
            if not decision.allowed:
                continue  # 요구 4 — 금지 후보는 제안 자체를 안 한다

            return _to_planned_action(c)
        return None


__all__ = [
    "BRANCH_ELIGIBLE_TOKENS",
    "CANONICAL_ACTION_TOKENS",
    "MinPathScoutStrategy",
    "ScoutBranchSetError",
    "ScoutStopPolicy",
    "default_stop_policy",
]
