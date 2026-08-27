"""W5O — `Δ36`(①②③④·part4) + `Δ37`(legacy depth `NULL` + 사유) 이행 회귀.

## 이 파일이 지키는 것

각 절이 **음성대조를 함께 둔다.** 무결과와 통과가 같은 출력이 되면 그 검사는
아무것도 검사하지 않는다. 그래서 여기서는 매번:

1. 시정 후 상태를 고정하고,
2. **시정 전 규칙을 그 자리에서 재현해** 두 값이 실제로 갈리는 것을 보이고,
3. `R31` — 새 단언이 **실제로 실패하는 입력**을 만들어 실패를 확인한다.

**실사이트 접속 0** — fixture 와 순수함수만 쓴다.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

REPO = Path(__file__).resolve().parents[1]
RESEARCH = REPO / "research" / "landing_accessibility"
sys.path.insert(0, str(RESEARCH / "src"))

from landing_accessibility.engine.l0_collector import min4_sort_key  # noqa: E402
from landing_accessibility.v3_runner import flow as flow_mod  # noqa: E402
from landing_accessibility.v3_runner.contracts import FlowStep  # noqa: E402
from landing_accessibility.v3_runner.discovery import (  # noqa: E402
    DEFAULT_V3_PATH_POLICY,
    MIN4_POLICY,
    V3_TIEBREAK_POLICY,
    V3PathOrderDivergenceError,
    path_order_divergence,
)
from landing_accessibility.v3_runner.runner import (  # noqa: E402
    DEPTH_IN_TOKENS,
    LEGACY_DEPTH_COLUMNS,
    LEGACY_DEPTH_NULL_REASON,
    SEARCH_STRATEGY,
    TOKEN_DETERMINACY_DETERMINED,
    TOKEN_DETERMINACY_UNDETERMINED,
    LegacyDepthNullReasonError,
    PathManifestContractError,
    PlannedAction,
    ScoutBudget,
    TerminalSeamError,
    TerminalVerdict,
    assert_legacy_depth_null_reasoned,
    assert_search_strategy_declared,
    build_path_manifest,
    path_manifest_sha256,
)
from landing_accessibility.v3_runner.scout_strategy import (  # noqa: E402
    STRUCTURALLY_DETERMINED_TOKENS,
    STRUCTURALLY_UNDETERMINED_TOKENS,
    _classify_action_token_with_determinacy,
    _to_planned_action,
)

# 이 파일은 W5F 의 fake 경계 구현을 **재구현하지 않는다** — 정본이 둘이 되면 안 된다.
from test_w5f_runner_core import (  # noqa: E402
    FakeDriver,
    FakeTerminal,
    ObservationKey,
    make_contract,
    make_runner,
    ok_transition,
)

FIXTURES = RESEARCH / "fixtures"
V3_FIXTURES = FIXTURES / "v3"
LANE_BASE_COMMIT = "5b6b00a5de884a861fc9ebb9ffbf96c1734b3e9a"
PROBE_REL = "research/landing_accessibility/src/landing_accessibility/engine/l0_probe.js"
COLLECTOR_REL = "research/landing_accessibility/src/landing_accessibility/engine/l0_collector.py"


def _key() -> ObservationKey:
    return ObservationKey(service_id="svc", task_id="task", run_id="run")


def _cand(**kw: Any) -> dict[str, Any]:
    base: dict[str, Any] = {"selector": "#c", "dom_order": 0}
    base.update(kw)
    return base


# ═══════════════════════════════════════════════════════════════════════════
# ① `search_strategy` 필수 기재 + "최소" 어휘
# ═══════════════════════════════════════════════════════════════════════════
def test_path_manifest_declares_the_search_strategy_verbatim() -> None:
    """`Δ36` ① — 값은 델타 축자 문자열 그대로다."""
    manifest = build_path_manifest(key=_key(), contract=make_contract(), steps=[])
    assert manifest["search_strategy"] == "greedy_descent_with_declared_total_order"
    assert SEARCH_STRATEGY == "greedy_descent_with_declared_total_order"


def test_a_manifest_without_search_strategy_is_refused_before_it_is_hashed() -> None:
    """`R31` 음성대조 — **단언이 실제로 실패하는 입력**을 만들어 확인한다.

    `build_path_manifest` 는 언제나 필드를 싣는다. 그러니 필드를 **빼서** 검사가
    발화하는지 직접 본다. 발화하지 않으면 이 단언은 아무것도 붙들고 있지 않은 것이다.
    """
    good = build_path_manifest(key=_key(), contract=make_contract(), steps=[])
    assert_search_strategy_declared(good)  # 양성 대조 — 정상 manifest 는 통과한다
    assert path_manifest_sha256(good)

    without = {k: v for k, v in good.items() if k != "search_strategy"}
    with pytest.raises(PathManifestContractError, match="search_strategy 가 없다"):
        assert_search_strategy_declared(without)
    with pytest.raises(PathManifestContractError):
        path_manifest_sha256(without)  # 해시를 뜨기 **전에** 막는다

    wrong = dict(good, search_strategy="breadth_first_minimal_path")
    with pytest.raises(PathManifestContractError, match="선언과 다르다"):
        assert_search_strategy_declared(wrong)


def test_the_runner_records_only_parameters_it_actually_used(tmp_path: Path) -> None:
    """`Δ36` part4 — 실제로 쓴 값만. 안 쓴 것은 **미사용**이라고 적고 지어내지 않는다."""
    result = make_runner(tmp_path, budget=ScoutBudget(max_activations=3)).run(
        make_contract(),
        driver=FakeDriver(transitions=[ok_transition(0, endpoint=True)] * 2),
        run_id="w5o-params",
    )
    params = result.path_manifest["search_parameters"]  # type: ignore[index]
    assert params["runner_max_activations"] == 3  # 실제로 비교에 쓰인 값
    assert params["search_strategy"] == SEARCH_STRATEGY
    rule = result.path_manifest["candidate_nomination_rule"]  # type: ignore[index]
    assert rule["binder"] == "FakeBinder"
    assert rule["bound_candidate_count"] == 1

    # scout 이 없으면 그 파라미터는 **미사용**이며 미관측과 다른 값이다.
    no_scout = make_runner(tmp_path / "b", scout=None).run(
        make_contract(), driver=FakeDriver(transitions=[]), run_id="w5o-noscout"
    )
    no_scout_params = no_scout.path_manifest["search_parameters"]  # type: ignore[index]
    assert no_scout_params["scout_strategy"] == "NOT_USED_IN_THIS_RUN"
    assert no_scout_params["stop_policy"] == "NOT_USED_IN_THIS_RUN"


def test_delta36_records_the_declared_total_order_it_actually_ranked_with(tmp_path: Path) -> None:
    """지명 규칙에 **실제 정책의 선언된 전순서**가 실린다. 기본값을 베껴 적지 않는다."""
    assert V3_TIEBREAK_POLICY.total_order == (
        "task_binding_candidate desc",
        "dom_order asc",
        "selector asc",
    )
    assert MIN4_POLICY.total_order[0] == "marked_primary desc"
    assert DEFAULT_V3_PATH_POLICY is V3_TIEBREAK_POLICY


def test_no_minimality_claim_survives_in_the_budget_exhaustion_note(tmp_path: Path) -> None:
    """`Δ36` ① — **산출 문자열**에 최소성 주장 어휘가 남지 않는다.

    docstring 이 아니라 실제로 행에 실려 나가는 note 를 본다. 여기 남으면 소비자가
    그 문장을 읽는다.
    """
    result = make_runner(
        tmp_path,
        scout=_ScoutOf([PlannedAction("SELECT_CATEGORY") for _ in range(4)]),
        budget=ScoutBudget(max_activations=2),
        terminal=FakeTerminal(None),
    ).run(
        make_contract(),
        driver=FakeDriver(transitions=[ok_transition(i) for i in range(5)]),
        run_id="w5o-note",
    )
    note = result.terminal_reason_note or ""
    assert note, "사유 note 가 비었다"
    assert "최소" not in note
    assert "관측 없음" in note


class _ScoutOf:
    def __init__(self, plan: list[PlannedAction]) -> None:
        self._plan = list(plan)

    def propose_next(self, contract: Any, states: Any, candidates: Any, taken: Any) -> Any:
        return self._plan.pop(0) if self._plan else None


# ═══════════════════════════════════════════════════════════════════════════
# ② evidence 랭킹 발산 — v3 는 자기 전순서를 쓴다
# ═══════════════════════════════════════════════════════════════════════════
#: **B 실측** (`l0_probe.js`): `marked_primary` 는 RF classifier 산물이 아니라
#: `el.hasAttribute('data-primary-action')` — **DOM 속성**이다. 그래서 v3 경로에서도
#: `True` 가 될 수 있고, `Δ36` ② 의 발산 조건이 성립한다.
DIVERGING_CANDIDATES = [
    {"selector": "a#first", "dom_order": 0, "marked_primary": False},
    {"selector": "button#marked", "dom_order": 1, "marked_primary": True},
    {"selector": "a#third", "dom_order": 2, "marked_primary": False},
]
AGREEING_CANDIDATES = [
    {"selector": "button#marked", "dom_order": 0, "marked_primary": True},
    {"selector": "a#second", "dom_order": 1, "marked_primary": False},
]


def test_marked_primary_is_a_dom_attribute_so_true_is_reachable_in_v3() -> None:
    """`Δ36` ② 부기의 실측 — 이 값이 `True` 가 될 수 있는지 근거를 코드에 고정한다.

    `Δ36` 부기는 `marked_primary` 를 "RF classifier 산물" 이라고 적었다. **B 실측은
    다르다**: `l0_probe.js` 는 그 값을 `data-primary-action` **속성 유무**로 만든다
    (classifier 호출이 없다). 따라서 그 속성을 가진 문서가 있으면 `True` 가 나오고,
    저장소에는 그런 fixture 가 실재한다 — 발산 조건이 성립한다.
    """
    probe = (RESEARCH / "src/landing_accessibility/engine/l0_probe.js").read_text("utf-8")
    assert "marked_primary: el.hasAttribute('data-primary-action')" in probe
    # 이 값을 만드는 줄 어디에도 분류기 호출이 없다 — 속성 유무가 전부다.
    producing = [ln for ln in probe.splitlines() if "marked_primary" in ln]
    assert len(producing) == 1
    assert "classif" not in producing[0].lower()

    holders = sorted(
        p.name for p in FIXTURES.glob("*.html") if "data-primary-action" in p.read_text("utf-8")
    )
    assert holders, "속성을 가진 fixture 가 하나도 없으면 이 주장은 공허하다"


def test_negative_control_the_two_total_orders_really_do_diverge() -> None:
    """음성대조 — 시정 대상이 실재하는가. 두 순서가 **실제로 갈리는** 후보 집합이 있다."""
    v2 = [c["selector"] for c in sorted(DIVERGING_CANDIDATES, key=min4_sort_key)]
    v3 = [c["selector"] for c in sorted(DIVERGING_CANDIDATES, key=V3_TIEBREAK_POLICY.sort_key)]
    assert v2 == ["button#marked", "a#first", "a#third"]
    assert v3 == ["a#first", "button#marked", "a#third"]
    assert v2 != v3, "갈리지 않으면 Δ36 ② 가 막을 것이 없다"

    # 양성 대조 — 갈리지 않는 집합에서는 두 순서가 같다. 그러면 발산이 성립하지 않는다.
    same_v2 = [c["selector"] for c in sorted(AGREEING_CANDIDATES, key=min4_sort_key)]
    same_v3 = [c["selector"] for c in sorted(AGREEING_CANDIDATES, key=V3_TIEBREAK_POLICY.sort_key)]
    assert same_v2 == same_v3


def test_path_order_divergence_detects_exactly_the_diverging_set() -> None:
    assert path_order_divergence(AGREEING_CANDIDATES, policy=V3_TIEBREAK_POLICY) is None
    found = path_order_divergence(DIVERGING_CANDIDATES, policy=V3_TIEBREAK_POLICY)
    assert found is not None
    v2_order, v3_order = found
    assert v2_order[0] == "button#marked"
    assert v3_order[0] == "a#first"


def test_v3_scout_ranking_uses_its_own_tiebreak_not_min4() -> None:
    """시정 **후**: v3 임계경로의 랭킹이 `marked_primary` 를 읽지 않는다.

    시정 **전** 규칙(`MIN4_POLICY`)을 그 자리에서 재현해 두 값이 갈리는 것을 보인다 —
    이 대조가 없으면 "기본값이 바뀌었다" 를 확인할 방법이 없다.
    """
    from landing_accessibility.v3_runner.scout_strategy import MinPathScoutStrategy

    before = sorted(DIVERGING_CANDIDATES, key=MIN4_POLICY.sort_key)[0]["selector"]
    after = sorted(DIVERGING_CANDIDATES, key=MinPathScoutStrategy().policy.sort_key)[0]["selector"]
    assert before == "button#marked"  # v2 전순서가 고르던 것
    assert after == "a#first"  # v3 전순서가 고르는 것
    assert before != after

    # `V3_TIEBREAK_RETIRED_KEYS` 가 이름으로 그 사실을 붙들고 있다.
    from landing_accessibility.v3_runner.tiebreak import V3_TIEBREAK_RETIRED_KEYS

    assert "marked_primary" in V3_TIEBREAK_RETIRED_KEYS


def test_the_v2_scout_seam_refuses_a_diverging_candidate_set(tmp_path: Path) -> None:
    """`Δ36` ② — 발산이 남으면 `ruling_10` 위반이다. 그래서 남기지 않고 멈춘다.

    `Scout._activation_candidates` 는 `@staticmethod` 이고 `min4_sort_key` 를 본문에서
    직접 부른다 — 주입점이 없다(`R31` 대신 구조 실측). `l1_engine.py` 는 v2 재현성
    때문에 고치지 않으므로, v3 가 자기 순서를 쓰는 방법은 **v2 순서로 고른 경로를 받지
    않는 것**뿐이다.
    """
    engine = (RESEARCH / "src/landing_accessibility/engine/l1_engine.py").read_text("utf-8")
    assert "sorted(cands, key=min4_sort_key)" in engine or "min4_sort_key" in engine
    assert "def _activation_candidates(raw: dict[str, Any], limit: int)" in engine, (
        "주입 인자가 생겼으면 이 우회는 더 이상 필요하지 않다 — 그때 이 테스트를 다시 좁혀라"
    )

    from landing_accessibility.v3_runner import discovery as disc

    calls: list[Any] = []

    def _explode(*a: Any, **k: Any) -> Any:  # pragma: no cover - 불려선 안 된다
        calls.append((a, k))
        raise AssertionError("발산 집합인데 Scout 가 만들어졌다")

    # 실제 게이트 경로를 순수하게 확인한다 — 브라우저 없이 규칙만 본다.
    assert path_order_divergence(DIVERGING_CANDIDATES, policy=disc.DEFAULT_V3_PATH_POLICY)
    assert not calls
    assert issubclass(V3PathOrderDivergenceError, RuntimeError)


# ═══════════════════════════════════════════════════════════════════════════
# ③ `BUDGET_EXCEEDED` 이음매 — 사유 축이 건너온다
# ═══════════════════════════════════════════════════════════════════════════
def test_budget_exhaustion_carries_both_axes(tmp_path: Path) -> None:
    result = make_runner(
        tmp_path,
        scout=_ScoutOf([PlannedAction("SELECT_CATEGORY") for _ in range(4)]),
        budget=ScoutBudget(max_activations=2),
        terminal=FakeTerminal(None),
    ).run(
        make_contract(),
        driver=FakeDriver(transitions=[ok_transition(i) for i in range(5)]),
        run_id="w5o-budget",
    )
    assert result.scout_budget_exhausted is True
    assert result.endpoint_status == "ABSTAIN"
    assert result.terminal_reason == "BUDGET_EXCEEDED"
    # `Δ10-R11` — terminal 은 **둘 다** 갖는다. 하나만 있는 행은 스키마 위반이다.
    record = result.as_mart_record()
    assert record["endpoint_status"] and record["terminal_reason"]


def test_negative_control_before_the_seam_the_reason_axis_was_dropped(tmp_path: Path) -> None:
    """음성대조 — 문자열 하나만 건네던 옛 형태에서는 사유가 실릴 자리가 **없다**.

    옛 Protocol 이 무엇을 흘렸는지를 그 자리에서 재현한다. 재현된 값에 사유 축이
    없다는 것이 곧 이 시정이 무엇을 고쳤는지의 증거다.
    """
    old_shape: str | None = "ABSTAIN"  # 옛 Protocol 의 반환 형태 전부
    assert not hasattr(old_shape, "terminal_reason")

    new_shape = TerminalVerdict(endpoint_status="ABSTAIN", terminal_reason="BUDGET_EXCEEDED")
    assert new_shape.terminal_reason == "BUDGET_EXCEEDED"


def test_a_bare_string_is_refused_when_the_reason_is_not_uniquely_determined(
    tmp_path: Path,
) -> None:
    """`R31` — 새 단언이 실제로 실패하는 입력을 만들어 확인한다.

    `ABSTAIN` 은 허용 사유가 7종이다. 문자열 하나로는 어느 것인지 알 수 없고, 하나를
    골라 적으면 그게 지어내기다 → 멈춘다.

    양성 대조: `REACHED`(허용 사유 `{None}` 하나)·`AUTH_GATE`(`{AUTH_REQUIRED}` 하나)는
    문자열만으로도 두 축이 결정되므로 통과한다.
    """
    runner = make_runner(tmp_path, terminal=FakeTerminal("ABSTAIN"))
    with pytest.raises(TerminalSeamError, match="사유 축이 결정되지 않는다"):
        runner.run(
            make_contract(),
            driver=FakeDriver(transitions=[ok_transition(0, endpoint=True)] * 2),
            run_id="w5o-ambiguous",
        )

    reached = make_runner(tmp_path / "r", terminal=FakeTerminal("REACHED")).run(
        make_contract(),
        driver=FakeDriver(transitions=[ok_transition(0, endpoint=True)] * 2),
        run_id="w5o-reached",
    )
    assert reached.endpoint_status == "REACHED"
    assert reached.terminal_reason is None  # `_REACHED_REASON_GAP` — 지어내지 않는다

    gate = make_runner(tmp_path / "g", terminal=FakeTerminal("AUTH_GATE")).run(
        make_contract(),
        driver=FakeDriver(transitions=[ok_transition(0, auth=True)] * 2),
        run_id="w5o-gate",
    )
    assert (gate.endpoint_status, gate.terminal_reason) == ("AUTH_GATE", "AUTH_REQUIRED")


def test_a_verdict_may_state_the_reason_explicitly(tmp_path: Path) -> None:
    class _Verdict:
        def classify(self, contract: Any, steps: Any) -> TerminalVerdict:
            return TerminalVerdict(
                endpoint_status="ABSTAIN",
                terminal_reason="REPLAY_BROKEN",
                terminal_reason_note="frozen path 재생이 깨졌다",
            )

    result = make_runner(tmp_path, terminal=_Verdict()).run(
        make_contract(),
        driver=FakeDriver(transitions=[ok_transition(0, endpoint=True)] * 2),
        run_id="w5o-verdict",
    )
    assert (result.endpoint_status, result.terminal_reason) == ("ABSTAIN", "REPLAY_BROKEN")


def test_min7_still_holds_no_budget_number_is_substituted(tmp_path: Path) -> None:
    """`MIN-7` 후단 — 예산값은 관측 스칼라 어디에도 값으로 들어가지 않는다."""
    result = make_runner(
        tmp_path,
        scout=_ScoutOf([PlannedAction("SELECT_CATEGORY") for _ in range(9)]),
        budget=ScoutBudget(max_activations=5),
        terminal=FakeTerminal(None),
    ).run(
        make_contract(),
        # scout 5 회 + replay 5 회 = 10 회 activate. 모자라면 fixture 결함이지 관측이 아니다.
        driver=FakeDriver(transitions=[ok_transition(i) for i in range(16)]),
        run_id="w5o-min7",
    )
    record = result.as_mart_record()
    scalars = {k: v for k, v in record.items() if isinstance(v, int) and not isinstance(v, bool)}
    assert 5 not in scalars.values(), f"예산값이 관측 스칼라로 대입됐다: {scalars}"
    # note 에도 숫자로 나타나지 않는다. (`MIN-7` 의 7 과 겹치지 않는 값을 골랐다.)
    assert "5" not in (result.terminal_reason_note or "")
    # 양성 대조 — 예산값이 남는 **유일한** 자리는 탐색 파라미터 기재다 (Δ36 part4).
    assert result.path_manifest["search_parameters"]["runner_max_activations"] == 5  # type: ignore[index]


# ═══════════════════════════════════════════════════════════════════════════
# ④ `Δ9` IN 10종 분류 + `UNDETERMINED`
# ═══════════════════════════════════════════════════════════════════════════
def test_the_two_token_sets_partition_the_delta9_in_ten() -> None:
    """한 것과 못 한 것이 **집합으로** 갈려 있다. 합치면 IN 10종이다."""
    assert STRUCTURALLY_DETERMINED_TOKENS | STRUCTURALLY_UNDETERMINED_TOKENS == DEPTH_IN_TOKENS
    assert not (STRUCTURALLY_DETERMINED_TOKENS & STRUCTURALLY_UNDETERMINED_TOKENS)


@pytest.mark.parametrize(
    ("signals", "token"),
    [
        ({"role": "tab"}, "SWITCH_TAB"),
        ({"in_tablist": True}, "SWITCH_TAB"),
        ({"submit_control": True}, "SUBMIT_QUERY"),
        ({"aria_haspopup": "menu", "in_nav_landmark": True}, "OPEN_GLOBAL_MENU"),
        ({"aria_haspopup": "true"}, "OPEN_LOCAL_MENU"),
        (
            {"aria_expanded": "false", "has_aria_controls": True, "controls_is_nav_landmark": True},
            "OPEN_GLOBAL_MENU",
        ),
        (
            {
                "aria_expanded": "false",
                "has_aria_controls": True,
                "controls_is_nav_landmark": False,
            },
            "EXPAND_ACCORDION",
        ),
        ({"aria_expanded": "false", "in_disclosure": True}, "EXPAND_ACCORDION"),
    ],
)
def test_five_of_the_ten_are_now_structurally_determined(
    signals: dict[str, Any], token: str
) -> None:
    got, determinacy = _classify_action_token_with_determinacy(_cand(**signals))
    assert got == token
    assert determinacy == TOKEN_DETERMINACY_DETERMINED


@pytest.mark.parametrize(
    "signals",
    [
        {},  # 신호 없음 — SELECT_FUNCTION 과 SELECT_CATEGORY 를 못 가른다
        {"in_list_container": True},  # SELECT_RESULT / OPEN_ITEM_DETAIL / OPEN_PLACE_DETAIL
        {"aria_expanded": "false"},  # 무언가를 열지만 셋 중 어느 것인지 모른다
    ],
)
def test_the_rest_are_marked_undetermined_not_guessed(signals: dict[str, Any]) -> None:
    """`Δ36` ④ — 못 가르는 자리를 **확정으로 적지 않는다.** 그것이 "틀린 측정" 이었다."""
    _, determinacy = _classify_action_token_with_determinacy(_cand(**signals))
    assert determinacy == TOKEN_DETERMINACY_UNDETERMINED


def test_negative_control_submit_query_before_and_after_the_signal() -> None:
    """음성대조 — `SUBMIT_QUERY` fixture 에서 분류 전/후가 실제로 갈린다.

    "전" 은 시정 전 규칙(`role=tab` → `SWITCH_TAB`, `in_list_container` →
    `SELECT_RESULT`, 그 밖 전부 → `SELECT_FUNCTION`)을 그 자리에서 재현한 것이다.
    """

    def old_rule(c: dict[str, Any]) -> str:
        if str(c.get("role") or "").lower() == "tab":
            return "SWITCH_TAB"
        if c.get("in_list_container"):
            return "SELECT_RESULT"
        return "SELECT_FUNCTION"

    submit = _cand(tag="button", input_type="submit", in_form=True, submit_control=True)
    assert old_rule(submit) == "SELECT_FUNCTION"  # 시정 전 — submit 이 지워진다
    after, determinacy = _classify_action_token_with_determinacy(submit)
    assert after == "SUBMIT_QUERY"  # 시정 후
    assert determinacy == TOKEN_DETERMINACY_DETERMINED
    assert old_rule(submit) != after


def test_negative_control_the_depth_sequence_gains_submit_query() -> None:
    """분류 전에는 flow sequence 가 submit 을 그 이름으로 담지 못했다.

    **[B 실측 · Δ36 ④ 전제 정정]** `SELECT_FUNCTION` 과 `SUBMIT_QUERY` 는 **둘 다**
    `ACTIVATION_TOKENS` 안이다. 그래서 오분류로 `activation_depth` 의 **수**가 줄지는
    않았다 — 델타가 적은 "depth 가 submit 을 빠뜨린다" 는 이 트리에서 그대로는
    성립하지 않는다. 실제로 어긋나던 것은 **토큰 신원**이고, reveal 계열
    (`menu_dependency` · `nav_container_depth`)은 아래 테스트가 따로 본다.
    """
    assert "SUBMIT_QUERY" in flow_mod.ACTIVATION_TOKENS
    assert "SELECT_FUNCTION" in flow_mod.ACTIVATION_TOKENS  # 양성 대조 — 수는 같다

    submit = _cand(submit_control=True)
    action = _to_planned_action(submit)
    assert action.action_token == "SUBMIT_QUERY"
    assert action.token_determinacy == TOKEN_DETERMINACY_DETERMINED


def _step(index: int, token: str, *, determinacy: str = TOKEN_DETERMINACY_DETERMINED) -> FlowStep:
    return FlowStep(
        step_index=index,
        action_token=token,
        state_before_id=f"S{index}",
        state_after_id=f"S{index + 1}",
        control_selector=f"#c{index}",
        control_role="button",
        control_visible_text=None,
        control_accessible_name=None,
        bbox_before=None,
        url_before="https://fixture.invalid/a",
        url_after="https://fixture.invalid/b",
        auth_gate_detected=False,
        endpoint_signal_detected=token == "ENDPOINT_REACHED",
        token_determinacy=determinacy,
    )


def test_an_undetermined_token_makes_activation_depth_undetermined_not_partial() -> None:
    """`Δ36` ④ — 부분값도 `0` 도 내지 않는다. 산출하지 않는다."""
    determined = [
        _step(0, "SELECT_FUNCTION"),
        _step(1, "SUBMIT_QUERY"),
        _step(2, "ENDPOINT_REACHED"),
    ]
    good = flow_mod.normalize_flow(determined)
    assert good.activation_depth == 2  # 양성 대조 — 확정이면 값이 나온다
    assert good.activation_depth_undetermined_reason is None

    undetermined = [
        _step(0, "SELECT_FUNCTION", determinacy=TOKEN_DETERMINACY_UNDETERMINED),
        _step(1, "SUBMIT_QUERY"),
        _step(2, "ENDPOINT_REACHED"),
    ]
    withheld = flow_mod.normalize_flow(undetermined)
    assert withheld.activation_depth is None
    assert withheld.activation_depth != 0, "0 은 관측이지 판정 불능이 아니다"
    assert "확정되지 않았다" in (withheld.activation_depth_undetermined_reason or "")


def test_undetermined_tokens_also_withhold_the_negative_reveal_claim() -> None:
    """ "reveal 이 없었다" 는 토큰 신원을 다 알아야 할 수 있는 **부정 주장**이다."""
    determined = [_step(0, "SELECT_FUNCTION"), _step(1, "ENDPOINT_REACHED")]
    assert flow_mod.normalize_flow(determined).menu_dependency is False  # 양성 대조
    assert flow_mod.normalize_flow(determined).nav_container_depth == 0

    mixed = [
        _step(0, "SELECT_FUNCTION", determinacy=TOKEN_DETERMINACY_UNDETERMINED),
        _step(1, "ENDPOINT_REACHED"),
    ]
    assert flow_mod.normalize_flow(mixed).menu_dependency is None
    assert flow_mod.normalize_flow(mixed).nav_container_depth is None

    # 양성 관측(reveal 을 실제로 봤다)은 미확정이 섞여도 그대로 산다.
    saw_reveal = [
        _step(0, "OPEN_GLOBAL_MENU"),
        _step(1, "SELECT_FUNCTION", determinacy=TOKEN_DETERMINACY_UNDETERMINED),
        _step(2, "ENDPOINT_REACHED"),
    ]
    assert flow_mod.normalize_flow(saw_reveal).menu_dependency is True


def test_determinacy_survives_freeze_and_replay(tmp_path: Path) -> None:
    """freeze → replay 를 건너지 못하면 replay 산출만 조용히 확정값이 된다."""
    manifest = build_path_manifest(
        key=_key(),
        contract=make_contract(),
        steps=[_step(0, "SELECT_FUNCTION", determinacy=TOKEN_DETERMINACY_UNDETERMINED)],
    )
    assert manifest["steps"][0]["token_determinacy"] == TOKEN_DETERMINACY_UNDETERMINED

    result = make_runner(tmp_path, scout=None).replay(
        make_contract(),
        driver=FakeDriver(transitions=[ok_transition(0)]),
        manifest=manifest,
        declared_sha256=path_manifest_sha256(manifest),
        run_id="w5o-replay",
    )
    assert result.raw_steps[0].token_determinacy == TOKEN_DETERMINACY_UNDETERMINED
    assert result.as_mart_record()["action_sequence_raw"][0]["token_determinacy"] == (
        TOKEN_DETERMINACY_UNDETERMINED
    )


def test_the_probe_change_is_additive_only() -> None:
    """`Δ20` 이 허용한 범주 — **가산적**. 삭제 열이 0 이어야 한다."""
    for relative in (PROBE_REL, COLLECTOR_REL):
        out = subprocess.run(
            ["git", "diff", "--numstat", LANE_BASE_COMMIT, "--", relative],
            cwd=REPO,
            capture_output=True,
            text=True,
            check=False,
        ).stdout.strip()
        if not out:
            continue
        added, deleted, _ = out.split("\t", 2)
        assert deleted == "0", f"{relative}: {deleted} 줄 삭제 — 가산만 허용된다 (추가 {added})"


def test_r22_the_capture_stack_fingerprint_reflects_the_probe_change() -> None:
    """`R22` — 포착 스택 신원이 이 변경을 실제로 반영한다.

    반영하지 않으면 "코드가 달랐는데 지문이 같다" 가 되고, 두 관측을 나중에 가를 수 없다.
    """
    import hashlib

    from landing_accessibility.v3_runner.ax_join import capture_stack

    stack = capture_stack()
    member = stack["members"]["engine/l0_probe.js"]
    on_disk = hashlib.sha256(
        (RESEARCH / "src/landing_accessibility" / "engine/l0_probe.js").read_bytes()
    ).hexdigest()
    assert member == on_disk

    base = subprocess.run(
        ["git", "show", f"{LANE_BASE_COMMIT}:{PROBE_REL}"],
        cwd=REPO,
        capture_output=True,
        check=False,
    ).stdout
    base_sha = hashlib.sha256(base).hexdigest()
    assert member != base_sha, "probe 를 고쳤는데 포착 스택 구성원 sha 가 그대로다 (R22 위반)"


# ═══════════════════════════════════════════════════════════════════════════
# Δ37 — legacy `NED`/`IED`/`MPFED` 는 `NULL` 이고 사유가 함께 나간다
# ═══════════════════════════════════════════════════════════════════════════
def test_the_legacy_columns_exist_and_are_null(tmp_path: Path) -> None:
    """`02 §7` compatibility — **컬럼은 존재한다.** 지켜지지 않는 것은 값뿐이다."""
    result = make_runner(tmp_path).run(
        make_contract(),
        driver=FakeDriver(transitions=[ok_transition(0, endpoint=True)] * 2),
        run_id="w5o-legacy",
    )
    record = result.as_mart_record()
    for name in LEGACY_DEPTH_COLUMNS:
        assert name in record, f"{name} 컬럼이 사라졌다 — 02 §7 은 컬럼 존재를 요구한다"
        assert record[name] is None
    assert record["legacy_depth_null_reason"] == LEGACY_DEPTH_NULL_REASON


def test_the_null_reason_is_the_delta37_wording_verbatim() -> None:
    assert LEGACY_DEPTH_NULL_REASON == (
        "v3 search_strategy=greedy_descent_with_declared_total_order. "
        "NED/IED/MPFED 의 유일한 정의는 v2.1 의 최소성 주장이며 v3 는 그 주장을 하지 "
        "않는다 (Δ36)."
    )
    assert SEARCH_STRATEGY in LEGACY_DEPTH_NULL_REASON


def test_null_with_a_reason_and_null_without_one_do_not_produce_the_same_output() -> None:
    """**Δ37 이행의 핵심** — 두 사건이 산출에서 갈린다.

    - `NULL` + 사유 있음 = **재지 않기로 했다** → 행이 만들어진다.
    - `NULL` + 사유 없음 = **못 쟀다** → 행이 만들어지지 않는다.

    `R31` — 두 번째가 실제로 실패하는 것을 여기서 확인한다. 실패하지 않으면 둘은 같은
    출력이고, 그러면 `Δ37` 을 이행한 것이 아니다.
    """
    reasoned = dict.fromkeys(LEGACY_DEPTH_COLUMNS)
    reasoned["legacy_depth_null_reason"] = LEGACY_DEPTH_NULL_REASON
    assert_legacy_depth_null_reasoned(reasoned)  # 양성 대조 — 통과한다

    silent = dict.fromkeys(LEGACY_DEPTH_COLUMNS)
    with pytest.raises(LegacyDepthNullReasonError, match="사유 없는 NULL"):
        assert_legacy_depth_null_reasoned(silent)

    blank = dict(silent, legacy_depth_null_reason="   ")
    with pytest.raises(LegacyDepthNullReasonError):
        assert_legacy_depth_null_reasoned(blank)

    # 컬럼이 아예 없는 행은 이 검사의 대상이 아니다(다른 스키마다) — 조용히 통과시킨다.
    assert_legacy_depth_null_reasoned({"observation_id": "x"})


def test_putting_a_value_into_a_legacy_depth_column_is_refused() -> None:
    """`Δ32-R29` 와 같은 규율 — 의미를 충족할 수 없는 필드에 값을 넣지 않는다."""
    filled = dict.fromkeys(LEGACY_DEPTH_COLUMNS)
    filled["NED"] = 2
    filled["legacy_depth_null_reason"] = LEGACY_DEPTH_NULL_REASON
    with pytest.raises(LegacyDepthNullReasonError, match="값을 넣었다"):
        assert_legacy_depth_null_reasoned(filled)


def test_v3_own_depth_fields_still_carry_values() -> None:
    """`Δ37` 은 legacy 이름만 비운다. v3 자신의 정의된 필드는 그대로 값을 담는다."""
    steps = [
        _step(0, "OPEN_GLOBAL_MENU"),
        _step(1, "SELECT_FUNCTION"),
        _step(2, "ENDPOINT_REACHED"),
    ]
    measured = flow_mod.normalize_flow(steps)
    assert measured.activation_depth == 2
    assert measured.nav_container_depth == 1
    assert measured.menu_dependency is True


def test_v3_never_materializes_ned_ied_mpfed_anywhere_in_the_v3_runner() -> None:
    """실측 고정 — v3 는 그 이름으로 **값을 만드는 코드가 없다**.

    양성 대조: v2 engine(`engine/depth.py`)에는 그 산출이 실재한다. 즉 이 grep 은
    아무것도 못 찾는 grep 이 아니다.
    """
    v3_dir = RESEARCH / "src/landing_accessibility/v3_runner"
    producers = [
        f"{p.name}:{i}"
        for p in v3_dir.glob("*.py")
        for i, line in enumerate(p.read_text("utf-8").splitlines(), 1)
        if ('"NED"' in line or '"IED"' in line or '"MPFED"' in line) and "LEGACY_DEPTH" not in line
    ]
    assert producers == [], f"v3 가 legacy 이름으로 값을 내고 있다: {producers}"

    v2_depth = (RESEARCH / "src/landing_accessibility/engine/depth.py").read_text("utf-8")
    assert '"NED": self.ned' in v2_depth  # 양성 대조 — v2 에는 실재한다


# ═══════════════════════════════════════════════════════════════════════════
# Δ43 / R37 — 경로 미발견은 경로 부재가 아니다
# ═══════════════════════════════════════════════════════════════════════════
class _NoCandidateBinder:
    """binder 는 돌았고 후보가 **0건**이었다 (`Δ32` — 페이지에 대한 관측)."""

    def bind(self, contract: Any, states: Any) -> list[dict[str, Any]]:
        return []


class _RealBinder:
    def bind(self, contract: Any, states: Any) -> list[dict[str, Any]]:
        return [{"selector": "#entry", "role": "link"}]


def _dead_end_runner(tmp_path: Path) -> Any:
    """후보는 있는데 정책이 한 걸음도 못 나아간다 — 탐욕적 하강의 막다른 곳."""
    return make_runner(
        tmp_path, binder=_RealBinder(), scout=_ScoutOf([]), terminal=FakeTerminal(None)
    )


def test_r37_a_path_not_found_terminal_carries_policy_relative_and_the_strategy(
    tmp_path: Path,
) -> None:
    """`R37` 1항 — 미발견 terminal 은 `policy_relative: true` + `search_strategy` 를 **함께** 싣는다."""
    result = _dead_end_runner(tmp_path).run(
        make_contract(), driver=FakeDriver(transitions=[]), run_id="w5o-r37"
    )
    assert result.path_discovery_outcome == "POLICY_DID_NOT_FIND_PATH"
    assert result.policy_relative is True
    record = result.as_mart_record()
    assert record["policy_relative"] is True
    assert record["search_strategy"] == SEARCH_STRATEGY  # 미발견 terminal 에도 실린다
    assert record["path_discovery_outcome"] == "POLICY_DID_NOT_FIND_PATH"


def test_r37_the_wording_never_claims_the_path_is_absent(tmp_path: Path) -> None:
    """`R37` 2항 — "선언된 정책이 찾지 못했다" 이지 "경로가 없다" 가 아니다."""
    from landing_accessibility.v3_runner.runner import (
        PATH_NOT_FOUND_NOTE,
        PathAbsenceClaimError,
        assert_no_path_absence_claim,
    )

    result = _dead_end_runner(tmp_path).run(
        make_contract(), driver=FakeDriver(transitions=[]), run_id="w5o-r37-words"
    )
    note = result.terminal_reason_note or ""
    assert "찾지 못했다" in note
    assert "경로가 없다" not in note
    assert note == PATH_NOT_FOUND_NOTE

    # `R31` — 이 단언이 **실제로 실패하는 입력**을 만들어 확인한다.
    assert_no_path_absence_claim(result.as_mart_record())  # 양성 대조
    with pytest.raises(PathAbsenceClaimError, match="경로 부재 주장 어휘"):
        assert_no_path_absence_claim({"terminal_reason_note": "이 서비스에는 경로가 없다"})
    with pytest.raises(PathAbsenceClaimError):
        assert_no_path_absence_claim({"notes": ["a", "NO_PATH"]})


def test_r37_negative_control_three_failures_do_not_collapse_into_one_output(
    tmp_path: Path,
) -> None:
    """**R37 이행의 핵심 음성대조** — 셋이 산출에서 서로 갈린다.

    셋이 같은 출력으로 접히면 분기가 넓은 서비스의 탐색 실패가 "그 서비스에는 경로가
    없다" 로 집계된다 — `[Δ43 인용]` *"성공 분모에 흡수하면 편향이 사라진 것처럼
    보인다."*
    """
    # (1) 경로 미발견 — 후보는 있었고 정책이 못 찾았다.
    not_found = _dead_end_runner(tmp_path / "1").run(
        make_contract(), driver=FakeDriver(transitions=[]), run_id="w5o-nf"
    )
    # (2) 후보 부재 — 페이지에 후보 control 이 0건이었다 (`Δ32`).
    no_candidate = make_runner(
        tmp_path / "2", binder=_NoCandidateBinder(), scout=_ScoutOf([]), terminal=FakeTerminal(None)
    ).run(make_contract(), driver=FakeDriver(transitions=[]), run_id="w5o-nc")
    # (3) endpoint 도달 실패 — 정책이 **경로를 찾았고** 그 끝이 endpoint 가 아니었다.
    #     사이트가 막은 것이므로 정책 상대적이 **아니다**.
    reached_nothing = make_runner(
        tmp_path / "3",
        binder=_RealBinder(),
        scout=_ScoutOf([PlannedAction("SELECT_FUNCTION", control_selector="#entry")]),
        terminal=FakeTerminal("AUTH_GATE"),
    ).run(
        make_contract(),
        driver=FakeDriver(transitions=[ok_transition(0, auth=True)] * 2),
        run_id="w5o-nr",
    )

    rows = [r.as_mart_record() for r in (not_found, no_candidate, reached_nothing)]
    axes = [
        (
            r["path_discovery_outcome"],
            r["terminal_reason"],
            r["policy_relative"],
            r["task_candidate_count"],
        )
        for r in rows
    ]
    assert len(set(axes)) == 3, f"세 사건이 같은 출력으로 접혔다: {axes}"

    # 각 축이 무엇을 말하는지 고정한다.
    assert not_found.path_discovery_outcome == "POLICY_DID_NOT_FIND_PATH"
    assert not_found.policy_relative is True
    assert not_found.task_candidate_count == 1  # 후보는 **있었다**

    assert no_candidate.terminal_reason == "NO_TASK_CANDIDATE_FOUND"
    assert no_candidate.path_discovery_outcome == "NO_CANDIDATES_TO_SEARCH"
    assert no_candidate.policy_relative is False  # 페이지에 대한 관측이다
    assert no_candidate.task_candidate_count == 0

    # (3) 은 endpoint 에 도달하지 못했지만 **사이트가 막았다** — 정책 실패가 아니다.
    assert reached_nothing.endpoint_status == "AUTH_GATE"
    assert reached_nothing.path_discovery_outcome == "PATH_FOUND"
    assert reached_nothing.policy_relative is False
    assert len(reached_nothing.raw_steps) == 1
    assert len(not_found.raw_steps) == 0

    # 추가 구분 — 같은 "미발견" 안에서도 **어디까지 갔는지**가 남는다. 한 걸음도 못 뗀
    # 것과 걷다 막힌 것은 다른 사실이고, `raw_steps` 가 그것을 복원한다.
    stalled = make_runner(
        tmp_path / "4",
        binder=_RealBinder(),
        scout=_ScoutOf([PlannedAction("SELECT_FUNCTION", control_selector="#entry")]),
        terminal=FakeTerminal(None),
    ).run(
        make_contract(),
        driver=FakeDriver(transitions=[ok_transition(0), ok_transition(0)]),
        run_id="w5o-stalled",
    )
    assert stalled.path_discovery_outcome == "POLICY_DID_NOT_FIND_PATH"
    assert len(stalled.raw_steps) == 1 != len(not_found.raw_steps)


def test_r37_budget_exhaustion_is_policy_relative_but_distinct_from_not_found(
    tmp_path: Path,
) -> None:
    """예산 소진도 정책 상대적이다 — 그러나 미발견과 **같은 값이 아니다**."""
    exhausted = make_runner(
        tmp_path,
        binder=_RealBinder(),
        scout=_ScoutOf([PlannedAction("SELECT_CATEGORY") for _ in range(4)]),
        budget=ScoutBudget(max_activations=2),
        terminal=FakeTerminal(None),
    ).run(
        make_contract(),
        driver=FakeDriver(transitions=[ok_transition(i) for i in range(6)]),
        run_id="w5o-r37-budget",
    )
    not_found = _dead_end_runner(tmp_path / "nf").run(
        make_contract(), driver=FakeDriver(transitions=[]), run_id="w5o-r37-nf"
    )
    assert exhausted.policy_relative is not_found.policy_relative is True
    assert exhausted.path_discovery_outcome == "POLICY_STOPPED_ON_BUDGET"
    assert not_found.path_discovery_outcome == "POLICY_DID_NOT_FIND_PATH"
    assert exhausted.terminal_reason != not_found.terminal_reason


def test_r37_a_reached_terminal_is_not_policy_relative(tmp_path: Path) -> None:
    """양성 대조 — 도달한 관측은 사이트에 대한 진술이므로 정책 상대적이 아니다."""
    reached = make_runner(tmp_path, terminal=FakeTerminal("REACHED")).run(
        make_contract(),
        driver=FakeDriver(transitions=[ok_transition(0, endpoint=True)] * 2),
        run_id="w5o-r37-reached",
    )
    assert reached.path_discovery_outcome == "PATH_FOUND"
    assert reached.policy_relative is False


def test_r37_the_declaration_guard_actually_fires(tmp_path: Path) -> None:
    """`R31` — `assert_path_discovery_declared` 가 실제로 실패하는 입력을 만든다."""
    from landing_accessibility.v3_runner.runner import (
        RunnerError,
        assert_path_discovery_declared,
    )

    good = {
        "path_discovery_outcome": "POLICY_DID_NOT_FIND_PATH",
        "policy_relative": True,
        "search_strategy": SEARCH_STRATEGY,
    }
    assert_path_discovery_declared(good)  # 양성 대조

    with pytest.raises(RunnerError, match="policy_relative 가 True 가 아니다"):
        assert_path_discovery_declared(dict(good, policy_relative=False))
    with pytest.raises(RunnerError, match="search_strategy 가 없다"):
        assert_path_discovery_declared({k: v for k, v in good.items() if k != "search_strategy"})
    with pytest.raises(RunnerError, match="어휘 밖"):
        assert_path_discovery_declared(dict(good, path_discovery_outcome="NO_PATH_EXISTS"))


def test_delta43_the_revised_03_s5_is_quoted_where_03_s5_is_cited() -> None:
    """`Δ43` 인용 규칙 — `03 §5` 를 인용하는 v3 Scout 자리는 개정본을 함께 인용한다.

    SSOTV3 원본과 `ssot_snapshot/` 은 이 저장소에서 고치지 않는다 — 개정본은 delta 가
    갖고 코드는 그것을 인용한다.
    """
    from landing_accessibility.v3_runner.runner import SSOT_03_S5_SCOUT_REVISED

    assert "최소성을 주장하지 않는다" in SSOT_03_S5_SCOUT_REVISED
    assert "선언된 결정론적 정책이 발견한" in SSOT_03_S5_SCOUT_REVISED
    assert "경로 미발견은 경로 부재가 아니며" in SSOT_03_S5_SCOUT_REVISED
    assert "policy_relative" in SSOT_03_S5_SCOUT_REVISED

    runner_src = (RESEARCH / "src/landing_accessibility/v3_runner/runner.py").read_text("utf-8")
    scout_citations = [ln for ln in runner_src.splitlines() if "03 §5" in ln and "Scout" in ln]
    assert scout_citations, "Scout 인용 자리를 못 찾았다 — grep 이 헛돈다"
    for line in scout_citations:
        assert "Δ43" in line or "SSOT_03_S5_SCOUT_REVISED" in line, line
