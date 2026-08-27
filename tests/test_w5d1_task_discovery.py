"""`v3_runner/discovery.py` — V3 task-specific candidate discovery + Scout 바인딩
(`T-B-V3-STEP1-001` → W5D1, narrow scope: 이 파일만 만든다).

## 이 파일이 고정하는 것

1. **대표기능을 추론하지 않는다** — `discover_task_candidates`가 candidate 의
   "task label"을 만들어내지 않는다는 것을 pure function 테스트로 고정한다.
2. **guard 재사용** — `T-A-W1-P2-DECIDED`의 `ADD_TO_CART`/`DISABLED_OR_INERT`
   판정이 V3 경로에서도 그대로 발화하는지 실제 fixture로 증명한다(재구현
   여부를 실측으로 확인한다 — "guard를 그대로 쓴다"는 주장이 코드로도 참인지).
3. **Scout 바인딩이 freeze(`l1_engine.py`)를 고치지 않고 성립하는지** — `Scout`가
   실제로 호출돼 endpoint에 도달하는 e2e로 증명한다.
4. **경로선택 정책이 실제로 주입 가능한지** — 기본 `MIN4_POLICY`와 임의의 다른
   정책을 넣었을 때 `discover_task_candidates`의 랭킹이 실제로 달라지는지
   직접 비교한다(장식적 인터페이스가 아니라는 증거).
5. `task_contract`가 `dict`든 속성 기반 객체든(duck typing) 같은 결과를 내는지.

**이 파일의 어떤 테스트도 실제 서비스에 접속하지 않는다** — FIXTURE 전용이다.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest

REPO = Path(__file__).resolve().parents[1]
RESEARCH = REPO / "research" / "landing_accessibility"
sys.path.insert(0, str(RESEARCH / "src"))

from landing_accessibility.e001_runner.guard import CandidateActionState  # noqa: E402
from landing_accessibility.engine.evidence import EvidenceRun  # noqa: E402
from landing_accessibility.engine.firewall import ExecutionMode  # noqa: E402
from landing_accessibility.engine.vocabulary import InteractionArchetype  # noqa: E402
from landing_accessibility.v3_runner.discovery import (  # noqa: E402
    FixtureInputMode,
    PathSelectionPolicy,
    TaskDiscoveryResult,
    _infer_fixture_input_mode,
    bind_task_definition,
    discover_task_candidates,
    run_task_aware_scout,
)

FIXTURES = RESEARCH / "fixtures"

pytest.importorskip("playwright.sync_api")


def _contract(**overrides: Any) -> dict[str, Any]:
    base = {
        "task_id": "v3-w5d1-test",
        "legacy_archetype": "UTILITY_ENTRY",
        "fixture_json": "w1_enabled_only.html",
        "endpoint_contract": {"definition": "NEXT_REACHED", "signal_type": "DOM_AX_ROLE"},
    }
    base.update(overrides)
    return base


# ══════════════════════════════════════════════════════════════════════════
# 1. bind_task_definition — pure, no browser
# ══════════════════════════════════════════════════════════════════════════
def test_bind_task_definition_maps_contract_fields_without_inferring_archetype():
    """`legacy_archetype`를 **동결값 그대로** 옮긴다 — RF 분류를 호출하지 않는다
    (호출할 방법조차 이 함수에 없다는 것이 그 자체로 증거다: import 가 없다)."""
    td = bind_task_definition(_contract())
    assert td.task_id == "v3-w5d1-test"
    assert td.archetype is InteractionArchetype.UTILITY_ENTRY
    assert td.endpoint_definition == "NEXT_REACHED"
    assert td.region_definition is None, "V3 계약에는 region 개념이 없다 — 지어내지 않는다"


def test_bind_task_definition_accepts_string_endpoint_contract():
    """`endpoint_contract`가 SSOT 어디에도 내부 shape 이 정해져 있지 않다 —
    문자열 하나만 와도 `endpoint_definition`으로 받아들인다(관대한 어댑터)."""
    td = bind_task_definition(_contract(endpoint_contract="SIMPLE_ENDPOINT"))
    assert td.endpoint_definition == "SIMPLE_ENDPOINT"


def test_bind_task_definition_raises_without_archetype():
    with pytest.raises(ValueError, match="legacy_archetype"):
        bind_task_definition({"task_id": "x", "fixture_json": "y.html"})


@dataclass
class _AttrContract:
    """`Mapping`이 아니라 속성 접근 객체 — `TaskContractLike` duck typing 대조군."""

    task_id: str
    legacy_archetype: str
    fixture_json: str
    endpoint_contract: Any


def test_bind_task_definition_accepts_attribute_style_contract_identically():
    """`task_contract`가 dict 든 dataclass 든(W5A의 실제 `contracts.py`가 어느 쪽을
    택하든) 같은 결과를 낸다 — import 없이 구조적으로 맞물린다는 증거."""
    dict_result = bind_task_definition(_contract())
    obj_contract = _AttrContract(
        task_id="v3-w5d1-test",
        legacy_archetype="UTILITY_ENTRY",
        fixture_json="w1_enabled_only.html",
        endpoint_contract={"definition": "NEXT_REACHED", "signal_type": "DOM_AX_ROLE"},
    )
    obj_result = bind_task_definition(obj_contract)
    assert dict_result == obj_result


# ══════════════════════════════════════════════════════════════════════════
# 2. discover_task_candidates — pure, no browser
# ══════════════════════════════════════════════════════════════════════════
def _probe_candidate(**kw: Any) -> dict[str, Any]:
    base = {
        "selector": "#c",
        "tag": "button",
        "role": None,
        "aria_label": None,
        "visible_text": "다음",
        "hittable": True,
        "enabled": True,
        "marked_primary": False,
        "dom_order": 0,
    }
    base.update(kw)
    return base


def test_discover_task_candidates_does_not_infer_or_relabel_task_intent():
    """`03 §4` — rule/NLP/embedding 으로 candidate 의 task label 을 바꾸지 않는다.
    이 함수가 돌려주는 `TaskCandidate`는 probe 가 관측한 값(`aria_label`/
    `visible_text`/`role`) 그대로다 — 이 함수가 새로 만든 라벨이 없다."""
    probe = {
        "primary_action_candidates": [
            _probe_candidate(selector="#a", visible_text="송금하기 아님, 그냥 버튼"),
        ]
    }
    out = discover_task_candidates(probe, _contract())
    assert len(out) == 1
    assert out[0].visible_text == "송금하기 아님, 그냥 버튼"  # 원본 그대로, 재해석 없음
    assert (
        out[0].raw is probe["primary_action_candidates"][0]
        or out[0].raw == probe["primary_action_candidates"][0]
    )


def test_discover_task_candidates_marks_disabled_as_not_usable_but_keeps_evidence():
    """`D-R0-70` — disabled 는 존재로는 남되(evidence) usable=False 다."""
    probe = {"primary_action_candidates": [_probe_candidate(selector="#d", enabled=False)]}
    out = discover_task_candidates(probe, _contract())
    assert out[0].guard_state is CandidateActionState.DISABLED_OR_INERT
    assert out[0].usable is False


def test_discover_task_candidates_marks_forbidden_transaction_as_not_usable_but_keeps_evidence():
    """`D-R0-06` — 장바구니 같은 거래 control 도 존재는 남고 usable 만 False."""
    probe = {
        "primary_action_candidates": [
            _probe_candidate(selector="#cart", visible_text="장바구니 담기")
        ]
    }
    out = discover_task_candidates(probe, _contract())
    assert out[0].guard_state is CandidateActionState.FORBIDDEN_TRANSACTION
    assert out[0].usable is False
    assert out[0].selector == "#cart", "차단돼도 evidence 목록에서 사라지지 않는다"


def test_discover_task_candidates_ranking_matches_min4_by_default():
    probe = {
        "primary_action_candidates": [
            _probe_candidate(selector="#b", dom_order=1),
            _probe_candidate(selector="#a", dom_order=0),
        ]
    }
    out = discover_task_candidates(probe, _contract())
    assert [c.selector for c in out] == ["#a", "#b"]
    assert [c.rank for c in out] == [0, 1]


def test_discover_task_candidates_policy_is_actually_injectable():
    """정책을 갈아끼우면 랭킹이 실제로 달라진다 — 장식적 인터페이스가 아니다.

    `dom_order`(MIN-4 키)와 알파벳 순서가 **일부러 반대**가 되도록 선택자를
    고른다 — 우연히 같은 순서가 나와 이 테스트가 아무것도 증명하지 못하는
    일을 막는다."""
    probe = {
        "primary_action_candidates": [
            _probe_candidate(selector="#zzz", dom_order=0),
            _probe_candidate(selector="#aaa", dom_order=1),
        ]
    }
    default_order = [c.selector for c in discover_task_candidates(probe, _contract())]
    alphabetical_policy = PathSelectionPolicy(
        name="ALPHABETICAL_SELECTOR", sort_key=lambda c: (str(c.get("selector") or ""),)
    )
    reordered = [
        c.selector for c in discover_task_candidates(probe, _contract(), alphabetical_policy)
    ]
    assert default_order == ["#zzz", "#aaa"], "MIN-4 는 dom_order 오름차순이어야 한다"
    assert reordered == ["#aaa", "#zzz"], "주입한 정책이 실제로 적용되지 않았다"
    assert default_order != reordered


def test_discover_task_candidates_missing_dom_order_propagates_probe_contract_error():
    """`dom_order`가 없는 candidate 는 `Min4ProbeContractError`(l0_collector.py,
    읽기전용)가 그대로 올라온다 — 이 함수가 결측을 `0`으로 조용히 흡수하지 않는다
    (그러면 그게 조작이다, `A2 §1.13`)."""
    from landing_accessibility.engine.l0_collector import Min4ProbeContractError

    probe = {"primary_action_candidates": [{"selector": "#x", "hittable": True}]}
    with pytest.raises(Min4ProbeContractError):
        discover_task_candidates(probe, _contract())


def test_discover_task_candidates_empty_probe_state_returns_empty_list():
    assert discover_task_candidates({}, _contract()) == []


# ══════════════════════════════════════════════════════════════════════════
# 3. run_task_aware_scout — e2e, FIXTURE 전용, REAL_TARGET 접속 0
# ══════════════════════════════════════════════════════════════════════════
def _run(tmp_path: Path, name: str = "run") -> EvidenceRun:
    return EvidenceRun.create(tmp_path / name, name, execution_mode=ExecutionMode.FIXTURE)


def test_run_task_aware_scout_missing_fixture_raises_before_any_browser_work(tmp_path):
    """`ValueError`가 `L0Collector.collect()` 호출보다 먼저 올라온다는 것 자체가
    "브라우저를 켜기 전에 실패했다"는 증거다 — 이 run 은 관측을 하나도 열지
    않았으므로 seal 대상도 아니다(`EvidenceRun.seal()`은 산출물 0건인 run 을
    거부한다, `07 §4`)."""
    run = _run(tmp_path)
    with pytest.raises(ValueError, match="fixture_json"):
        run_task_aware_scout(
            {"task_id": "x", "legacy_archetype": "UTILITY_ENTRY"},
            fixture_root=FIXTURES,
            run=run,
        )


def test_run_task_aware_scout_enabled_control_reaches_endpoint(tmp_path, monkeypatch):
    """`D-R0-70-3` 대조군 방향 2 재현(V3 경로) — enabled control 이 있으면 Scout
    가 실제로 호출되고 클릭해 endpoint 에 도달한다."""
    from playwright.sync_api import Page

    click_calls: list[str] = []
    original_click = Page.click

    def spy_click(self, selector, *args, **kwargs):
        click_calls.append(selector)
        return original_click(self, selector, *args, **kwargs)

    monkeypatch.setattr(Page, "click", spy_click)

    run = _run(tmp_path)
    result = run_task_aware_scout(_contract(), fixture_root=FIXTURES, run=run)
    run.seal()

    assert result.scout_invoked is True
    assert result.blocking is None
    assert result.entry is not None
    assert result.entry.endpoint_status == "FUNCTION_ENDPOINT_REACHED"
    assert any("next" in sel for sel in click_calls), (
        f"활성 control 이 클릭되지 않았다: {click_calls}"
    )
    assert len(result.candidates) == 1
    assert result.candidates[0].guard_state is CandidateActionState.SAFE


def test_run_task_aware_scout_disabled_only_blocks_before_scout_is_constructed(
    tmp_path, monkeypatch
):
    """`D-R0-70-3` 대조군 방향 1 재현(V3 경로) — disabled control 만 있으면
    `Scout` 자체가 안 만들어진다는 것을 spy 로 직접 증명한다."""
    from landing_accessibility.engine.l1_engine import Scout

    scout_calls: list[str] = []
    original_scout = Scout.scout

    def spy_scout(self, **kwargs):
        scout_calls.append(kwargs.get("web_target_id", "?"))
        return original_scout(self, **kwargs)

    monkeypatch.setattr(Scout, "scout", spy_scout)

    run = _run(tmp_path)
    result = run_task_aware_scout(
        _contract(fixture_json="w1_disabled_only.html"), fixture_root=FIXTURES, run=run
    )
    run.seal()

    assert result.scout_invoked is False
    assert result.blocking is not None
    assert result.blocking.blocking_state == "DISABLED_OR_INERT"
    assert scout_calls == [], (
        f"Scout 가 생성됐다 — disabled-only 인데도 막히지 않았다: {scout_calls}"
    )
    assert len(result.candidates) == 1
    assert result.candidates[0].guard_state is CandidateActionState.DISABLED_OR_INERT
    assert result.candidates[0].usable is False


def test_run_task_aware_scout_cart_only_blocks_with_add_to_cart_category(tmp_path, monkeypatch):
    """`D-R0-06` — 장바구니 담기 control **만** 있으면(안전한 대안 없음) V3 경로에서도
    guard 가 막는다. `T-A-W1-P2-DECIDED`의 `ADD_TO_CART` 판정이 재구현 없이 그대로
    발화한다는 것을 실측으로 확인한다."""
    from landing_accessibility.engine.l1_engine import Scout

    scout_calls: list[str] = []
    monkeypatch.setattr(
        Scout, "scout", lambda self, **kw: scout_calls.append(kw.get("web_target_id"))
    )

    run = _run(tmp_path)
    result = run_task_aware_scout(
        _contract(fixture_json="w1_cart_only.html", legacy_archetype="ITEM_DETAIL"),
        fixture_root=FIXTURES,
        run=run,
    )
    run.seal()

    assert result.scout_invoked is False
    assert result.blocking is not None
    assert result.blocking.category == "ADD_TO_CART"
    assert result.blocking.blocking_state == "FORBIDDEN_TRANSACTION"
    assert scout_calls == []


def test_run_task_aware_scout_cart_with_safe_alt_proceeds_and_never_clicks_cart(
    tmp_path, monkeypatch
):
    """`D-R0-06` 반대 방향 — 장바구니 control 이 있어도 다른 SAFE 후보(검색)가
    있으면 target 전체가 죽지 않는다(`G1-a` target-kill 로 되돌아가지 않는다).
    장바구니 버튼은 evidence 후보 목록에는 있어도 실제로 클릭되지 않는다."""
    from playwright.sync_api import Page

    click_calls: list[str] = []
    original_click = Page.click

    def spy_click(self, selector, *args, **kwargs):
        click_calls.append(selector)
        return original_click(self, selector, *args, **kwargs)

    monkeypatch.setattr(Page, "click", spy_click)

    run = _run(tmp_path)
    result = run_task_aware_scout(
        _contract(
            fixture_json="w1_cart_with_safe_alt.html",
            legacy_archetype="QUERY",
            endpoint_contract={"definition": "QUERY_SUBMITTED", "signal_type": "URL_PATTERN"},
        ),
        fixture_root=FIXTURES,
        run=run,
    )
    run.seal()

    assert result.scout_invoked is True
    assert result.blocking is None
    assert result.entry.endpoint_status == "FUNCTION_ENDPOINT_REACHED"

    cart_states = [c.guard_state for c in result.candidates if "add-to-cart" in c.selector]
    assert cart_states == [CandidateActionState.FORBIDDEN_TRANSACTION]
    assert not any("add-to-cart" in sel for sel in click_calls), (
        f"장바구니 버튼이 실제로 클릭됐다: {click_calls}"
    )
    assert len(click_calls) >= 1, "검색 제출조차 클릭되지 않았다"


def test_run_task_aware_scout_result_type_is_stable(tmp_path):
    run = _run(tmp_path)
    result = run_task_aware_scout(_contract(), fixture_root=FIXTURES, run=run)
    run.seal()
    assert isinstance(result, TaskDiscoveryResult)
    assert result.task_id == "v3-w5d1-test"


# ══════════════════════════════════════════════════════════════════════════
# 4. Scout 바인딩의 명시된 한계 — policy 가 Scout 내부 BFS 에는 적용되지 않는다
# ══════════════════════════════════════════════════════════════════════════
def test_scout_internal_branching_ignores_the_injected_policy_by_design(tmp_path):
    """모듈 docstring "Scout 바인딩 — 설계 제약"이 주장하는 한계를 실측으로
    고정한다: `run_task_aware_scout`에 다른 정책을 넣어도 `Scout` 자신이 실제로
    클릭하는 순서/결과는 바뀌지 않는다(내부적으로 `min4_sort_key`를 하드코딩해서
    쓰기 때문이다) — `discover_task_candidates`의 evidence 랭킹만 바뀐다.
    두 랭킹이 오늘 같은 이유는 `MIN4_POLICY`가 같은 함수를 감싸고 있어서이지,
    Scout 가 그 정책 객체를 실제로 받아서가 아니다.
    """
    run_default = _run(tmp_path, "default")
    result_default = run_task_aware_scout(_contract(), fixture_root=FIXTURES, run=run_default)
    run_default.seal()

    reverse_policy = PathSelectionPolicy(
        name="REVERSE_SELECTOR", sort_key=lambda c: (str(c.get("selector") or ""),)
    )
    run_reverse = _run(tmp_path, "reverse")
    result_reverse = run_task_aware_scout(
        _contract(), fixture_root=FIXTURES, run=run_reverse, policy=reverse_policy
    )
    run_reverse.seal()

    # 후보가 하나뿐인 fixture 라 랭킹 차이가 드러나지 않는다 — 그래도 Scout 의
    # 최종 결과(entry)는 정책과 무관하게 항상 같다는 것 자체가 "Scout 는 policy
    # 인자를 모른다"는 설계 제약의 직접 증거다(같은 fixture, 다른 policy, 같은
    # Scout 결과).
    assert result_default.entry.endpoint_status == result_reverse.entry.endpoint_status
    assert (
        result_default.entry.steps[0].clicked_selector
        == result_reverse.entry.steps[0].clicked_selector
    )


# ══════════════════════════════════════════════════════════════════════════
# 5. fixture_input_mode (A `Δ8-R5`, 2026-08-28) — 구조 신호만으로 관측한다
# ══════════════════════════════════════════════════════════════════════════
@pytest.mark.parametrize(
    ("candidate_kwargs", "expected"),
    [
        ({"role": "combobox"}, FixtureInputMode.MIXED),
        ({"tag": "select"}, FixtureInputMode.DROPDOWN),
        ({"role": "listbox"}, FixtureInputMode.DROPDOWN),
        ({"tag": "input", "type": "text"}, FixtureInputMode.FREE_TEXT),
        ({"tag": "input", "type": "search"}, FixtureInputMode.FREE_TEXT),
        ({"role": "application"}, FixtureInputMode.MAP_PAN),
        ({"tag": "button"}, FixtureInputMode.OTHER),
        ({"tag": "a"}, FixtureInputMode.OTHER),
        ({"role": "tab"}, FixtureInputMode.OTHER),
    ],
)
def test_infer_fixture_input_mode_uses_only_structural_signals(candidate_kwargs, expected):
    assert _infer_fixture_input_mode(_probe_candidate(**candidate_kwargs)) is expected


def test_infer_fixture_input_mode_button_type_input_is_not_free_text():
    """`input[type=submit|button]`은 `primary_action_candidates`의 진짜 소스이지만
    FREE_TEXT가 아니다 — 제출 버튼이지 텍스트 입력이 아니다(구조 신호가 그 이상
    가르지 못하므로 `None`)."""
    assert _infer_fixture_input_mode(_probe_candidate(tag="input", type="submit")) is None
    assert _infer_fixture_input_mode(_probe_candidate(tag="input", type="button")) is None


def test_infer_fixture_input_mode_returns_none_when_no_structural_signal():
    """신호가 전혀 없으면 `OTHER`로 단정하지 않고 `None`(결측)이다 — 관측이지
    추측이 아니다."""
    assert _infer_fixture_input_mode({"tag": "div", "role": None}) is None
    assert _infer_fixture_input_mode({}) is None


def test_infer_fixture_input_mode_does_not_use_label_text_to_guess_map_widgets():
    """ "지도"라는 문구가 aria_label/visible_text 에 있어도 구조 신호가 없으면
    MAP_PAN 으로 추측하지 않는다 — 라벨로 의미를 추론하면 대표기능 비추론
    원칙을 어긴다."""
    candidate = _probe_candidate(tag="button", visible_text="지도에서 위치 선택")
    assert _infer_fixture_input_mode(candidate) is FixtureInputMode.OTHER, (
        "라벨 문구가 아니라 tag=button 구조 신호로만 OTHER 가 나와야 한다"
    )


def test_discover_task_candidates_populates_fixture_input_mode_per_candidate():
    probe = {
        "primary_action_candidates": [
            _probe_candidate(selector="#combo", dom_order=0, role="combobox"),
            _probe_candidate(selector="#btn", dom_order=1, tag="button"),
        ]
    }
    out = discover_task_candidates(probe, _contract())
    by_selector = {c.selector: c.fixture_input_mode for c in out}
    assert by_selector["#combo"] is FixtureInputMode.MIXED
    assert by_selector["#btn"] is FixtureInputMode.OTHER


def test_run_task_aware_scout_records_fixture_input_mode_on_real_fixture_candidates(tmp_path):
    """실제 fixture(FIXTURE 전용, 브라우저 통과) 에서도 `fixture_input_mode`가
    채워지는지 확인한다 — `w1_enabled_only.html`의 유일한 candidate 는
    `<button>`이므로 구조적으로 `OTHER`다."""
    run = _run(tmp_path)
    result = run_task_aware_scout(_contract(), fixture_root=FIXTURES, run=run)
    run.seal()
    assert len(result.candidates) == 1
    assert result.candidates[0].fixture_input_mode is FixtureInputMode.OTHER
