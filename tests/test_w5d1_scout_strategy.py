"""`v3_runner/scout_strategy.py` — `ScoutStrategy` Protocol(`runner.py`, W5F) 구현
(소유자 미지정 Protocol 을 W5D1 이 맡았다. `discovery.py`는 그대로 두고 새 파일).

## 이 파일이 고정하는 것

1. **경로선택 정책 주입** — `discovery.PathSelectionPolicy`를 그대로 받아 쓰고,
   정책을 바꾸면 실제로 다른 candidate 가 선택된다.
2. **`taken` 재제안 0** — 이미 밟은 selector 는 다시 제안되지 않는다.
3. **중단 정책 주입** — MIN-3(직전 step 이 이미 terminal)·MIN-7(예산 초과) 둘 다
   하드코딩이 아니라 `ScoutStopPolicy` 객체로 갈아끼울 수 있다.
4. **금지 후보는 제안 전에 걸러진다** — `ActivationSafetyGuard`(W5G)를 재사용해서
   제안 **전에** 판정한다(제안 후 runner 가 막는 구조가 아니다). 존재는 차단
   여부와 무관하게 항상 evidence 로 남는다(`D-R0-06`).
5. **`action_token`은 항상 `CANONICAL_ACTION_TOKENS` 안이다** — runner.py 가
   그 밖의 값을 받으면 `ProhibitedActionError`를 던진다.

이 파일의 어떤 테스트도 브라우저/네트워크를 쓰지 않는다 — `propose_next`는 순수
함수에 가깝다(guard 상태만 인스턴스에 누적된다).
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[1]
RESEARCH = REPO / "research" / "landing_accessibility"
sys.path.insert(0, str(RESEARCH / "src"))

from landing_accessibility.v3_runner.contracts import TaskContract  # noqa: E402
from landing_accessibility.v3_runner.discovery import PathSelectionPolicy  # noqa: E402
from landing_accessibility.v3_runner.runner import CANONICAL_ACTION_TOKENS, FlowStep  # noqa: E402
from landing_accessibility.v3_runner.scout_strategy import (  # noqa: E402
    MinPathScoutStrategy,
    ScoutStopPolicy,
    _classify_action_token,
    default_stop_policy,
)


def _contract(**overrides: Any) -> TaskContract:
    base: dict[str, Any] = {
        "target_id": "t-w5d1",
        "family_id": "f1",
        "service": "svc",
        "starting_url": "https://example.com/",
        "frozen_task": "TASK",
        "task_instruction": "instr",
        "fixed_fixture": "없음",
        "fixture_override": None,
        "endpoint_contract": "ENDPOINT",
        "forbidden_actions": (),
        "task_contract_hash": "hash-t-w5d1",
        "endpoint_contract_hash": "hash-endpoint",
    }
    base.update(overrides)
    return TaskContract(**base)


def _cand(**kw: Any) -> dict[str, Any]:
    base = {
        "selector": "#c",
        "tag": "button",
        "role": None,
        "aria_label": None,
        "visible_text": "다음",
        "dom_order": 0,
        "marked_primary": False,
        "hittable": True,
        "enabled": True,
    }
    base.update(kw)
    return base


def _step(selector: str, *, auth_gate=False, endpoint=False) -> FlowStep:
    return FlowStep(
        step_index=0,
        action_token="SELECT_FUNCTION",
        state_before_id="s0",
        state_after_id="s1",
        control_selector=selector,
        control_role="button",
        control_visible_text=None,
        control_accessible_name=None,
        bbox_before=None,
        url_before="u0",
        url_after="u1",
        auth_gate_detected=auth_gate,
        endpoint_signal_detected=endpoint,
    )


# ══════════════════════════════════════════════════════════════════════════
# 1. 정책 주입 — 경로선택
# ══════════════════════════════════════════════════════════════════════════
def test_propose_next_uses_min4_by_default():
    candidates = [_cand(selector="#b", dom_order=1), _cand(selector="#a", dom_order=0)]
    strategy = MinPathScoutStrategy()
    action = strategy.propose_next(_contract(), [], candidates, ())
    assert action is not None
    assert action.control_selector == "#a"


def test_propose_next_policy_is_actually_injectable():
    """정책을 바꾸면 실제로 다른 candidate 가 선택된다 — 장식적 인터페이스가 아니다."""
    candidates = [_cand(selector="#zzz", dom_order=0), _cand(selector="#aaa", dom_order=1)]
    default_pick = MinPathScoutStrategy().propose_next(_contract(), [], candidates, ())
    alpha_policy = PathSelectionPolicy(
        name="ALPHA", sort_key=lambda c: (str(c.get("selector") or ""),)
    )
    alpha_pick = MinPathScoutStrategy(policy=alpha_policy).propose_next(
        _contract(), [], candidates, ()
    )
    assert default_pick.control_selector == "#zzz"
    assert alpha_pick.control_selector == "#aaa"
    assert default_pick.control_selector != alpha_pick.control_selector


# ══════════════════════════════════════════════════════════════════════════
# 2. taken — 재제안 0
# ══════════════════════════════════════════════════════════════════════════
def test_taken_candidate_is_never_reproposed():
    candidates = [_cand(selector="#a", dom_order=0), _cand(selector="#b", dom_order=1)]
    strategy = MinPathScoutStrategy()

    first = strategy.propose_next(_contract(), [], candidates, ())
    assert first.control_selector == "#a"

    taken = (_step("#a"),)
    second = strategy.propose_next(_contract(), [], candidates, taken)
    assert second is not None
    assert second.control_selector == "#b"
    assert second.control_selector != first.control_selector

    taken2 = (_step("#a"), _step("#b"))
    third = strategy.propose_next(_contract(), [], candidates, taken2)
    assert third is None, "후보가 전부 taken 인데 재제안됐다"


def test_full_walk_never_reproposes_and_terminates(monkeypatch):
    """`propose_next`를 runner 처럼 반복 호출해도(같은 `candidates`, `taken`이
    매번 누적) 각 selector 가 정확히 한 번씩만 제안되고, 유한 스텝에서
    `None`으로 끝난다 — 무한루프 0."""
    candidates = [_cand(selector=f"#c{i}", dom_order=i) for i in range(5)]
    strategy = MinPathScoutStrategy(stop_policy=default_stop_policy(max_activations=10))
    contract = _contract()
    taken: tuple[FlowStep, ...] = ()
    proposed_selectors: list[str] = []
    for _ in range(10):  # 충분히 큰 상한 — 무한루프면 여기서 안전히 끊긴다
        action = strategy.propose_next(contract, [], candidates, taken)
        if action is None:
            break
        assert action.control_selector not in proposed_selectors, (
            f"같은 selector 가 두 번 제안됐다: {action.control_selector}"
        )
        proposed_selectors.append(action.control_selector)
        taken = (*taken, _step(action.control_selector))
    assert proposed_selectors == ["#c0", "#c1", "#c2", "#c3", "#c4"]
    assert strategy.propose_next(contract, [], candidates, taken) is None


# ══════════════════════════════════════════════════════════════════════════
# 3. 중단 정책 — MIN-3 / MIN-7, 둘 다 주입 가능
# ══════════════════════════════════════════════════════════════════════════
def test_stops_when_last_taken_step_already_signaled_terminal():
    """MIN-3 잠정판 — 직전 step 이 이미 endpoint/gate 를 냈으면 더 제안하지 않는다."""
    candidates = [_cand(selector="#a")]
    strategy = MinPathScoutStrategy()
    taken = (_step("#z", endpoint=True),)
    assert strategy.propose_next(_contract(), [], candidates, taken) is None

    strategy2 = MinPathScoutStrategy()
    taken_gate = (_step("#z", auth_gate=True),)
    assert strategy2.propose_next(_contract(), [], candidates, taken_gate) is None


def test_stops_when_strategy_budget_exceeded():
    """MIN-7 잠정판 — strategy 자체 예산(`default_stop_policy(max_activations=N)`)
    을 넘으면 멈춘다. `runner.py`의 `ScoutBudget`과 독립된 값이다."""
    candidates = [_cand(selector="#a")]
    strategy = MinPathScoutStrategy(stop_policy=default_stop_policy(max_activations=1))
    taken = (_step("#z"),)  # 이미 1개 — 예산 1 도달
    assert strategy.propose_next(_contract(), [], candidates, taken) is None


def test_stop_policy_is_actually_injectable():
    """항상 멈추는 정책을 넣으면 후보가 있어도 즉시 `None`이다."""
    candidates = [_cand(selector="#a")]
    always_stop = ScoutStopPolicy(name="ALWAYS_STOP", should_stop=lambda c, s, t: True)
    strategy = MinPathScoutStrategy(stop_policy=always_stop)
    assert strategy.propose_next(_contract(), [], candidates, ()) is None

    never_stop = ScoutStopPolicy(name="NEVER_STOP", should_stop=lambda c, s, t: False)
    strategy2 = MinPathScoutStrategy(stop_policy=never_stop)
    action = strategy2.propose_next(_contract(), [], candidates, ())
    assert action is not None  # 정책이 안 막으면 정상 제안된다


# ══════════════════════════════════════════════════════════════════════════
# 4. 금지 후보 — 제안 전에 걸러진다 (guard 재사용)
# ══════════════════════════════════════════════════════════════════════════
def test_forbidden_candidate_is_never_proposed_but_is_observed_as_existing():
    """`ADD_TO_CART`(W5G `ForbiddenAction`, `e001_runner.guard` 어휘 재사용)가
    유일한 후보면 제안되지 않는다 — 그러나 guard 의 evidence(observations)에는
    존재가 기록된다(`D-R0-06`)."""
    candidates = [_cand(selector="#cart", visible_text="장바구니 담기")]
    strategy = MinPathScoutStrategy()
    action = strategy.propose_next(_contract(), [], candidates, ())
    assert action is None

    guard = strategy._guard_for(_contract())
    # 주의: `_contract()`는 매번 새 TaskContract 를 만들지만 `task_contract_hash`
    # 가 고정값("hash-t-w5d1")이라 같은 guard 인스턴스가 재사용된다(캐시 키).
    observed_selectors = {o.selector for o in guard.observations}
    assert "#cart" in observed_selectors, "차단된 후보라도 존재 evidence 는 남아야 한다"


def test_safe_candidate_alongside_forbidden_one_is_proposed_and_cart_is_skipped():
    candidates = [
        _cand(selector="#cart", visible_text="장바구니 담기", dom_order=0),
        _cand(selector="#detail", visible_text="상세보기", dom_order=1),
    ]
    strategy = MinPathScoutStrategy()
    action = strategy.propose_next(_contract(), [], candidates, ())
    assert action is not None
    assert action.control_selector == "#detail"


def test_disabled_candidate_is_never_proposed():
    """`hittable=False`/`enabled=False`(`DISABLED_OR_INERT`, T-A-W1-P2-DECIDED)도
    guard 의 forbidden-action 판정과 별개로 제안 대상에서 제외된다."""
    candidates = [_cand(selector="#d", enabled=False)]
    strategy = MinPathScoutStrategy()
    assert strategy.propose_next(_contract(), [], candidates, ()) is None


def test_candidates_are_not_observed_twice_across_repeated_calls():
    """같은 `candidates`로 `propose_next`를 여러 번 불러도(runner 의 실제 호출
    패턴) 같은 selector 를 두 번 observe 하지 않는다 — evidence 중복 방지."""
    candidates = [_cand(selector="#a", dom_order=0), _cand(selector="#b", dom_order=1)]
    strategy = MinPathScoutStrategy()
    contract = _contract()

    strategy.propose_next(contract, [], candidates, ())
    strategy.propose_next(contract, [], candidates, (_step("#a"),))

    guard = strategy._guard_for(contract)
    selectors_observed = [o.selector for o in guard.observations]
    assert selectors_observed.count("#a") == 1
    assert selectors_observed.count("#b") == 1


# ══════════════════════════════════════════════════════════════════════════
# 5. action_token — 항상 CANONICAL_ACTION_TOKENS 안, 구조 신호만 쓴다
# ══════════════════════════════════════════════════════════════════════════
def test_classify_action_token_tab_role_maps_to_switch_tab():
    assert _classify_action_token(_cand(role="tab")) == "SWITCH_TAB"


def test_classify_action_token_list_container_maps_to_select_result():
    assert _classify_action_token(_cand(in_list_container=True)) == "SELECT_RESULT"


def test_classify_action_token_default_is_select_function():
    """구조 신호가 없으면(순수 button/link) `SELECT_FUNCTION`으로 보수적으로
    묶는다 — 라벨 문구로 더 세분화하지 않는다(대표기능 비추론)."""
    assert _classify_action_token(_cand(visible_text="송금하기")) == "SELECT_FUNCTION"
    assert _classify_action_token(_cand(visible_text="지도 보기")) == "SELECT_FUNCTION"


def test_classify_action_token_always_in_canonical_set():
    for kwargs in ({"role": "tab"}, {"in_list_container": True}, {}):
        token = _classify_action_token(_cand(**kwargs))
        assert token in CANONICAL_ACTION_TOKENS, (
            f"{token} 이 CANONICAL_ACTION_TOKENS 밖이다 — runner.py 가 "
            "ProhibitedActionError 로 거부한다"
        )


def test_propose_next_returns_action_with_canonical_token():
    candidates = [_cand(selector="#tab1", role="tab")]
    strategy = MinPathScoutStrategy()
    action = strategy.propose_next(_contract(), [], candidates, ())
    assert action is not None
    assert action.action_token in CANONICAL_ACTION_TOKENS
    assert action.action_token == "SWITCH_TAB"


# ══════════════════════════════════════════════════════════════════════════
# 6. Protocol 적합성 — runner.py 가 실제로 이 클래스를 `ScoutStrategy` 로 인정한다
# ══════════════════════════════════════════════════════════════════════════
def test_min_path_scout_strategy_satisfies_the_runner_protocol():
    from landing_accessibility.v3_runner.runner import ScoutStrategy

    strategy = MinPathScoutStrategy()
    assert isinstance(strategy, ScoutStrategy), (
        "MinPathScoutStrategy 가 runner.py 의 ScoutStrategy Protocol 을 구조적으로 "
        "만족하지 못한다 — propose_next 시그니처가 어긋났을 가능성이 크다"
    )
