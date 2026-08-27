"""W5B — `v3_runner/flow.py` normalize_flow 검증.

이 파일이 증명하려는 것은 "함수가 돌아간다"가 아니라 **각 파생 필드가 실제로
자기가 재겠다고 한 것을 재는가**다. 그래서 필드마다 양성·음성 대조 쌍을 두고,
구조가 같고 문제의 token만 다른 두 fixture에서 값이 갈리는 것을 고정한다.
대조군 없이 단일 입력만 통과시키면 상수를 반환하는 구현도 통과한다.

fixture는 `research/landing_accessibility/fixtures/w5b_flow/*.json`이고 전부
합성 입력이다(실사이트 접속·네트워크 없음). 각 파일의 `note`에 그 케이스가
04 codebook의 어느 조항을 겨냥하는지 적어 뒀다.

근거: `SSOTV3/04_FLOW_CODEBOOK_v3.0.md` §2 canonical token, §3 task vs
experienced flow, §4 measurement variables, §5 derived 규칙.
"""

from __future__ import annotations

import json
import sys
from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
RESEARCH = REPO / "research" / "landing_accessibility"
sys.path.insert(0, str(RESEARCH / "src"))

from landing_accessibility.v3_runner.flow import (  # noqa: E402
    ACTION_ABSTAIN,
    ACTION_AUTH_GATE,
    ACTIVATION_TOKENS,
    AUTH_STAGE_VALUES,
    CANONICAL_TOKENS,
    CONDITIONAL_DEPTH_TOKENS,
    KNOWN_LIMITATIONS,
    REVEAL_TOKENS,
    FlowNormalization,
    FlowStep,
    normalize_flow,
)

FIXTURES = RESEARCH / "fixtures" / "w5b_flow"


# ══════════════════════════════════════════════════════════════════════════
# fixture 로더
# ══════════════════════════════════════════════════════════════════════════
def load(case_id: str) -> list[FlowStep]:
    payload = json.loads((FIXTURES / f"{case_id}.json").read_text(encoding="utf-8"))
    return [
        FlowStep(
            step_index=row["step_index"],
            action_token=row["action_token"],
            state_before_id=row["state_before_id"],
            state_after_id=row["state_after_id"],
            control_selector=row["control_selector"],
            control_role=row["control_role"],
            control_visible_text=row["control_visible_text"],
            control_accessible_name=row["control_accessible_name"],
            bbox_before=None if row["bbox_before"] is None else tuple(row["bbox_before"]),
            url_before=row["url_before"],
            url_after=row["url_after"],
            auth_gate_detected=row["auth_gate_detected"],
            endpoint_signal_detected=row["endpoint_signal_detected"],
            input_mode=row.get("input_mode"),
        )
        for row in payload["steps"]
    ]


def norm(case_id: str) -> FlowNormalization:
    return normalize_flow(load(case_id))


def step(token: str, index: int = 0, **overrides: object) -> FlowStep:
    """계약 필드를 전부 채운 최소 step. 토큰 어휘 자체를 시험할 때 쓴다."""
    base: dict[str, object] = {
        "step_index": index,
        "action_token": token,
        "state_before_id": f"S{index}",
        "state_after_id": f"S{index + 1}",
        "control_selector": "#x",
        "control_role": "button",
        "control_visible_text": "x",
        "control_accessible_name": "x",
        "bbox_before": (0.0, 0.0, 10.0, 10.0),
        "url_before": "https://example.kr/m",
        "url_after": "https://example.kr/m",
        "auth_gate_detected": False,
        "endpoint_signal_detected": False,
        "input_mode": None,
    }
    base.update(overrides)
    return FlowStep(**base)  # type: ignore[arg-type]


# ══════════════════════════════════════════════════════════════════════════
# 0. 어휘 — 04 §2를 넘어서지 않았는가
# ══════════════════════════════════════════════════════════════════════════
def test_canonical_token_set_is_exactly_the_codebook_eighteen() -> None:
    """04 §2 표에 있는 18종. 새 토큰을 만들지 않았다는 고정."""
    codebook_eighteen = {
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
    assert codebook_eighteen == CANONICAL_TOKENS
    assert len(codebook_eighteen) == 18


def test_activation_set_excludes_typing_dismiss_and_state_markers() -> None:
    """04 §5 activation_depth 제외 목록이 집합 정의에 실제로 반영돼 있다."""
    assert "INPUT_QUERY" not in ACTIVATION_TOKENS
    assert "DISMISS_OBSTRUCTION" not in ACTIVATION_TOKENS
    assert "AUTH_GATE" not in ACTIVATION_TOKENS
    assert "ENDPOINT_REACHED" not in ACTIVATION_TOKENS
    assert "ABSTAIN" not in ACTIVATION_TOKENS
    assert REVEAL_TOKENS <= ACTIVATION_TOKENS  # reveal은 state-changing activation


def test_activation_attribution_matches_a_delta9_table() -> None:
    """A Δ9 확정 귀속표. IN 10 / OUT 5 / CONDITIONAL 3."""
    assert {
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
    } == ACTIVATION_TOKENS
    assert {
        "SELECT_ORIGIN",
        "SELECT_DESTINATION",
        "SELECT_DATE",
    } == CONDITIONAL_DEPTH_TOKENS
    assert len(ACTIVATION_TOKENS) == 10
    assert ACTIVATION_TOKENS.isdisjoint(CONDITIONAL_DEPTH_TOKENS)


def test_switch_tab_is_activation_but_not_reveal() -> None:
    """A Δ9 ②의 두 축. activation 귀속과 reveal 집합은 별개 질문이다.

    A는 activation_depth 귀속만 확정했고(IN), REVEAL_TOKENS 축에서는 W5B의
    근거(04 §4 nav_container_type 열거에 tab 없음)가 유효하다고 확인했다.
    """
    assert "SWITCH_TAB" in ACTIVATION_TOKENS
    assert "SWITCH_TAB" not in REVEAL_TOKENS
    r = norm("switch_tab_flow")
    assert r.activation_depth == 2  # SWITCH_TAB + SELECT_FUNCTION
    assert r.menu_dependency is False  # tab 전환은 reveal이 아니다
    assert r.nav_container_depth == 0


def test_submit_query_stays_in_activation_depth() -> None:
    """A Δ9 ①이 W5B 판단을 유지했다. 검색·조회형과 직접 진입형이 같은
    activation_depth를 갖게 되면 실재하는 구조 차이가 지워진다."""
    assert "SUBMIT_QUERY" in ACTIVATION_TOKENS
    assert norm("submit_result_no_typing").activation_depth == 2


def test_reveal_set_is_only_the_three_named_in_section_5() -> None:
    """04 §5가 이름으로 지목한 3종만. '등'을 임의 확장하지 않았다(KL-02)."""
    named_in_section_5 = {"OPEN_GLOBAL_MENU", "OPEN_LOCAL_MENU", "EXPAND_ACCORDION"}
    assert named_in_section_5 == REVEAL_TOKENS


def test_known_limitations_are_declared() -> None:
    """04에 규정이 없어 W5B가 판단한 지점이 코드에 남아 있어야 한다."""
    assert len(KNOWN_LIMITATIONS) >= 18
    assert all(item.startswith("KL-") for item in KNOWN_LIMITATIONS)


# ══════════════════════════════════════════════════════════════════════════
# 1. task_flow vs experienced_flow — 이 모듈의 핵심 분기 (04 §3)
# ══════════════════════════════════════════════════════════════════════════
def test_dismissal_splits_the_two_sequences() -> None:
    """04 §3 예시 그대로. 같은 입력에서 두 sequence가 갈린다."""
    r = norm("dismissal_then_menu_auth")
    assert r.task_flow_sequence == ("OPEN_GLOBAL_MENU", "SELECT_FUNCTION", "AUTH_GATE")
    assert r.experienced_flow_sequence == (
        "DISMISS_OBSTRUCTION",
        "OPEN_GLOBAL_MENU",
        "SELECT_FUNCTION",
        "AUTH_GATE",
    )
    assert r.task_flow_sequence != r.experienced_flow_sequence


def test_without_dismissal_the_two_sequences_coincide() -> None:
    """음성 대조군: dismissal이 없으면 두 sequence가 같다."""
    r = norm("no_dismissal_menu_auth")
    assert r.task_flow_sequence == r.experienced_flow_sequence
    assert r.forced_dismissal_count == 0


def test_dismissal_does_not_raise_activation_depth() -> None:
    """대조 쌍의 핵심. DISMISS만 다른 두 입력에서 activation_depth가 같다."""
    with_dismiss = norm("dismissal_then_menu_auth")
    without = norm("no_dismissal_menu_auth")
    assert with_dismiss.activation_depth == without.activation_depth == 2
    # 갈리는 것은 dismissal 카운트와 experienced sequence 길이뿐이다.
    assert with_dismiss.forced_dismissal_count == 1
    assert without.forced_dismissal_count == 0
    assert len(with_dismiss.experienced_flow_sequence) == len(without.experienced_flow_sequence) + 1
    assert with_dismiss.task_flow_sequence == without.task_flow_sequence


def test_dismissal_does_not_enter_flow_step_count() -> None:
    """flow_step_count는 task-intent token 수다. dismissal은 서비스 task가 아니다."""
    assert norm("dismissal_then_menu_auth").flow_step_count == 3
    assert norm("no_dismissal_menu_auth").flow_step_count == 3


def test_dismissal_only_gives_zero_activation_not_none() -> None:
    """dismissal만 있고 activation 0. 관측된 0이지 산출 불능이 아니다."""
    r = norm("dismissal_only_no_activation")
    assert r.activation_depth == 0
    assert r.flow_step_count == 0
    assert r.forced_dismissal_count == 2
    assert r.task_flow_sequence == ()
    assert r.experienced_flow_sequence == ("DISMISS_OBSTRUCTION", "DISMISS_OBSTRUCTION")
    # Δ10: terminal에 닿지 않았으므로 "auth가 없었다"고 주장할 수 없다.
    assert r.auth_gate_stage == "UNDETERMINED"


# ══════════════════════════════════════════════════════════════════════════
# 2. menu_dependency — 양성/음성 대조 (04 §5)
# ══════════════════════════════════════════════════════════════════════════
def test_menu_dependency_positive_negative_pair() -> None:
    """구조 동일, reveal token만 있고 없다. 값이 갈려야 그 필드가 그것을 잰다."""
    positive = norm("menu_dependency_positive")
    negative = norm("menu_dependency_negative")
    assert positive.menu_dependency is True
    assert negative.menu_dependency is False
    assert positive.task_flow_sequence[1:] == negative.task_flow_sequence


def test_menu_dependency_ignores_reveal_after_endpoint() -> None:
    """04 §5는 'endpoint 전' reveal만 센다. endpoint 뒤 reveal은 세지 않는다."""
    r = norm("reveal_after_endpoint_only")
    assert "OPEN_LOCAL_MENU" in r.experienced_flow_sequence
    assert r.menu_dependency is False


def test_menu_dependency_true_when_endpoint_never_reached() -> None:
    """endpoint 신호가 없으면 관측된 sequence 전체가 'endpoint 전'이다.

    reveal을 실제로 봤으므로 True는 양성 관측이고 terminal 없이도 확정된다.
    """
    r = norm("endpoint_not_reached")
    assert r.menu_dependency is True


# ══════════════════════════════════════════════════════════════════════════
# 3. nav_container_depth — menu_dependency와 다른 것을 잰다
# ══════════════════════════════════════════════════════════════════════════
def test_nested_reveal_depth_three() -> None:
    r = norm("nested_reveal_three")
    assert r.nav_container_depth == 3
    assert r.menu_dependency is True
    assert r.activation_depth == 4  # reveal 3 + SELECT_FUNCTION


def test_nav_container_depth_zero_when_reveal_comes_after_engagement() -> None:
    """menu_dependency=True인데 nav_container_depth=0.

    두 필드가 같은 것을 재고 있었다면 이 케이스에서 값이 갈리지 않는다.
    """
    r = norm("reveal_after_engagement")
    assert r.menu_dependency is True
    assert r.nav_container_depth == 0


def test_nav_container_depth_pair_differs_only_by_reveal() -> None:
    assert norm("menu_dependency_positive").nav_container_depth == 1
    assert norm("menu_dependency_negative").nav_container_depth == 0


def test_nav_container_depth_undetermined_when_never_engaged_and_no_terminal() -> None:
    """engagement도 terminal도 없으면 값이 정의되지 않는다 (Δ10, KL-10 개정).

    이전 구현은 prefix 전체 reveal 수(2)를 냈다. 그것은 하한이지 값이 아니다 —
    사용자가 task control에 닿기까지 reveal이 더 필요했을 수 있다.
    """
    r = norm("endpoint_not_reached")
    assert r.nav_container_depth is None


def test_nav_container_depth_determined_at_gate_without_engagement() -> None:
    """engagement가 없어도 terminal(gate)에 닿으면 확정된다 (R2).

    위 테스트와 대조 쌍이다 — 구조는 같고 terminal 유무만 다르다.
    """
    r = norm("auth_before_discovery_after_reveal")
    assert r.nav_container_depth == 1


# ══════════════════════════════════════════════════════════════════════════
# 4. auth_gate_stage — '있었는가'가 아니라 '언제였는가' (04 §4, 03 §7)
# ══════════════════════════════════════════════════════════════════════════
@pytest.mark.parametrize(
    ("case_id", "expected"),
    [
        ("auth_none", "NONE"),
        ("auth_before_task_discovery", "BEFORE_TASK_DISCOVERY"),
        ("auth_before_discovery_after_reveal", "BEFORE_TASK_DISCOVERY"),
        ("auth_after_task_select", "AFTER_TASK_SELECT"),
        ("auth_at_endpoint", "AT_ENDPOINT"),
    ],
)
def test_auth_gate_stage_three_values_actually_split(case_id: str, expected: str) -> None:
    assert norm(case_id).auth_gate_stage == expected


def test_auth_stage_pair_same_prefix_different_stage() -> None:
    """AT_ENDPOINT와 AFTER_TASK_SELECT는 auth의 '위치'로만 갈린다.

    두 입력 모두 SELECT_FUNCTION 이후에 auth가 걸렸다. 다른 것은 그 step에
    endpoint 신호가 있었느냐뿐이고, 그것만으로 값이 갈려야 한다.
    """
    at_endpoint = norm("auth_at_endpoint")
    after_select = norm("auth_after_task_select")
    assert at_endpoint.auth_gate_stage == "AT_ENDPOINT"
    assert after_select.auth_gate_stage == "AFTER_TASK_SELECT"
    assert "SELECT_FUNCTION" in at_endpoint.task_flow_sequence
    assert "SELECT_FUNCTION" in after_select.task_flow_sequence


def test_auth_first_step_is_before_task_discovery() -> None:
    """auth가 첫 step. 과업 control을 고를 기회 자체가 없었다."""
    r = norm("auth_before_task_discovery")
    assert r.auth_gate_stage == "BEFORE_TASK_DISCOVERY"
    assert r.activation_depth == 0
    assert r.flow_step_count == 1
    assert r.nav_container_depth == 0


def test_auth_last_step_after_task_select() -> None:
    """auth가 마지막 step. reveal은 discovery이지 selection이 아니다."""
    r = norm("auth_after_task_select")
    assert r.experienced_flow_sequence[-1] == "AUTH_GATE"
    assert r.auth_gate_stage == "AFTER_TASK_SELECT"


def test_reveal_and_dismiss_alone_do_not_count_as_task_select() -> None:
    """양성/음성 대조: 같은 auth 위치인데 앞에 reveal만 있느냐 SELECT가 있느냐."""
    reveal_only = norm("auth_before_discovery_after_reveal")
    with_select = norm("auth_after_task_select")
    assert reveal_only.auth_gate_stage == "BEFORE_TASK_DISCOVERY"
    assert with_select.auth_gate_stage == "AFTER_TASK_SELECT"


def test_auth_flag_without_token_is_honoured() -> None:
    """02 §4 fact_flow_step의 auth_gate_detected도 auth 신호다(KL-08)."""
    r = norm("auth_flag_without_token")
    assert "AUTH_GATE" not in r.experienced_flow_sequence
    assert r.auth_gate_stage == "AFTER_TASK_SELECT"


def test_auth_flag_absent_without_terminal_is_undetermined() -> None:
    """대조군: 같은 sequence에서 flag만 끄면 UNDETERMINED (NONE이 아니다).

    Δ10 — 경로가 terminal에 닿지 않았으므로 'auth가 없었다'는 주장을 할 수
    없다. 이 자리에 NONE을 적는 것이 auth 발생률 과소추정의 경로다.
    """
    steps = [step("SELECT_FUNCTION", 0), step("SELECT_RESULT", 1)]
    assert normalize_flow(steps).auth_gate_stage == "UNDETERMINED"


# ══════════════════════════════════════════════════════════════════════════
# 5. activation_depth / flow_step_count — typing 분리 (04 §5)
# ══════════════════════════════════════════════════════════════════════════
def test_typing_counts_in_flow_step_count_but_not_activation_depth() -> None:
    with_typing = norm("typing_submit_result")
    without = norm("submit_result_no_typing")
    assert with_typing.activation_depth == without.activation_depth == 2
    # Δ15: ENDPOINT_REACHED는 flow_step_count에서도 빠진다.
    assert without.flow_step_count == 2
    assert with_typing.flow_step_count == 3


def test_state_markers_do_not_count_as_activation() -> None:
    """AUTH_GATE·ENDPOINT_REACHED는 도달한 상태이지 activation이 아니다."""
    r = norm("menu_dependency_negative")
    assert r.experienced_flow_sequence == ("SELECT_FUNCTION", "ENDPOINT_REACHED")
    assert r.activation_depth == 1
    # Δ15: 도달 표지는 task-intent가 아니라 flow_step_count에서도 빠진다.
    assert r.flow_step_count == 1
    assert len(r.task_flow_sequence) == 2  # 등식이 깨진 지점(KL-05)


def test_long_mixed_path_full_profile() -> None:
    """복합 경로 하나를 전 필드로 고정한다 (회귀 앵커)."""
    r = norm("long_mixed_path")
    assert r.forced_dismissal_count == 2
    assert r.experienced_flow_sequence.count("DISMISS_OBSTRUCTION") == 2
    assert "DISMISS_OBSTRUCTION" not in r.task_flow_sequence
    assert len(r.experienced_flow_sequence) == 14
    assert len(r.task_flow_sequence) == 12
    assert r.flow_step_count == 11  # Δ15: ENDPOINT_REACHED 제외
    # activation: OPEN_GLOBAL_MENU, EXPAND_ACCORDION, SELECT_CATEGORY,
    # SELECT_FUNCTION, SELECT_ORIGIN, SELECT_DESTINATION, SELECT_DATE,
    # SUBMIT_QUERY, SELECT_RESULT, OPEN_ITEM_DETAIL = 10
    # (INPUT_QUERY=typing, DISMISS 2회, ENDPOINT_REACHED 제외)
    # activation: reveal 2 + SELECT_CATEGORY + SELECT_FUNCTION + SUBMIT_QUERY
    # + SELECT_RESULT + OPEN_ITEM_DETAIL = 7, CONDITIONAL 3종(dropdown) = 3
    assert r.activation_depth == 10
    assert len(r.depth_conditional_tokens) == 3
    assert all(rec.included_in_activation_depth for rec in r.depth_conditional_tokens)
    assert r.menu_dependency is True
    assert r.nav_container_depth == 2
    assert r.auth_gate_stage == "NONE"


# ══════════════════════════════════════════════════════════════════════════
# 6. 산출 불능 — None이지 0/FAIL이 아니다
# ══════════════════════════════════════════════════════════════════════════
#: `auth_gate_stage`는 제외한다 — Δ10 이후 그 필드는 None이 아니라
#: UNDETERMINED를 낸다. 아래 NULLABLE 목록만 None이 될 수 있다.
DERIVED_SCALARS = (
    "activation_depth",
    "flow_step_count",
    "menu_dependency",
    "nav_container_depth",
    "forced_dismissal_count",
)


def test_empty_sequence_yields_none_not_zero() -> None:
    r = norm("empty")
    assert r.task_flow_sequence == ()
    assert r.experienced_flow_sequence == ()
    for field in DERIVED_SCALARS:
        assert getattr(r, field) is None, field
    # 'NONE' 문자열(관측된 부재)과 UNDETERMINED(판정 못 함)는 다른 사실이다.
    assert r.auth_gate_stage == "UNDETERMINED"


def test_abstain_nulls_all_derived_scalars() -> None:
    r = norm("abstain_mixed")
    assert "ABSTAIN" in r.experienced_flow_sequence
    assert "ABSTAIN" in r.task_flow_sequence  # raw 투영이므로 남긴다
    for field in DERIVED_SCALARS:
        assert getattr(r, field) is None, field
    assert r.auth_gate_stage == "UNDETERMINED"


def test_abstain_twin_control_group_does_derive() -> None:
    """대조군. action_token=ABSTAIN만 뺀 같은 앞부분에서는 파생값이 나온다.

    이게 없으면 None이 구조 탓인지 불확정 토큰 탓인지 구분되지 않는다.
    """
    r = norm("abstain_free_twin")
    for field in DERIVED_SCALARS:
        assert getattr(r, field) is not None, field
    assert r.activation_depth == 2
    assert r.forced_dismissal_count == 1
    assert r.menu_dependency is True
    assert r.auth_gate_stage == "NONE"


def test_abstain_alone() -> None:
    r = normalize_flow([step("ABSTAIN", 0)])
    assert r.experienced_flow_sequence == ("ABSTAIN",)
    assert all(getattr(r, f) is None for f in DERIVED_SCALARS)
    assert r.auth_gate_stage == "UNDETERMINED"


# ══════════════════════════════════════════════════════════════════════════
# 7. 계약 위반은 조용히 정규화하지 않는다
# ══════════════════════════════════════════════════════════════════════════
def test_non_canonical_token_raises() -> None:
    """04 §2 밖 token. 무시하면 없는 step이 depth에서 사라진다(KL-06)."""
    with pytest.raises(ValueError, match="non-canonical"):
        normalize_flow([step("OPEN_RIGHT_DRAWER", 0)])


def test_out_of_order_step_index_raises() -> None:
    """flow는 ordered sequence가 primary(04 §1). 재정렬하지 않는다(KL-07)."""
    with pytest.raises(ValueError, match="strictly increase"):
        normalize_flow([step("SELECT_FUNCTION", 5), step("SUBMIT_QUERY", 2)])


def test_duplicate_step_index_raises() -> None:
    with pytest.raises(ValueError, match="strictly increase"):
        normalize_flow([step("SELECT_FUNCTION", 1), step("SUBMIT_QUERY", 1)])


def test_non_contiguous_but_increasing_index_is_accepted() -> None:
    """증가하기만 하면 된다 — step_index는 순서 표지이지 offset이 아니다."""
    r = normalize_flow([step("SELECT_FUNCTION", 0), step("ENDPOINT_REACHED", 7)])
    assert r.flow_step_count == 1


def test_result_is_frozen_and_sequences_are_tuples() -> None:
    r = norm("menu_dependency_positive")
    assert isinstance(r.task_flow_sequence, tuple)
    assert isinstance(r.experienced_flow_sequence, tuple)
    with pytest.raises(FrozenInstanceError):
        r.activation_depth = 99  # type: ignore[misc]


def test_no_hand_labels_in_signature() -> None:
    """09 D3-11 — derived 값은 raw step에서만 나온다. 라벨 인자를 받지 않는다."""
    import inspect

    params = list(inspect.signature(normalize_flow).parameters)
    assert params == ["steps"]


# ══════════════════════════════════════════════════════════════════════════
# 8. fixture 자체 위생
# ══════════════════════════════════════════════════════════════════════════
def test_every_fixture_uses_only_canonical_tokens_and_normalizes() -> None:
    files = sorted(FIXTURES.glob("*.json"))
    assert len(files) >= 18
    for path in files:
        payload = json.loads(path.read_text(encoding="utf-8"))
        assert payload["synthetic"] is True, path.name
        assert payload["note"], path.name
        for row in payload["steps"]:
            assert row["action_token"] in CANONICAL_TOKENS, (path.name, row["action_token"])
        result = normalize_flow(load(path.stem))
        assert isinstance(result, FlowNormalization)


# ══════════════════════════════════════════════════════════════════════════
# 9. R2 — 진입 flow 지표는 auth gate 여부와 무관하게 산출된다
#    (A 사전등록 T-A-V3-STEP1-003)
# ══════════════════════════════════════════════════════════════════════════
GATE_CASES = (
    "auth_before_task_discovery",
    "auth_before_discovery_after_reveal",
    "auth_after_task_select",
    "auth_at_endpoint",
    "auth_flag_without_token",
    "dismissal_then_menu_auth",
    "no_dismissal_menu_auth",
)


@pytest.mark.parametrize("case_id", GATE_CASES)
def test_gate_terminal_never_nulls_a_derived_field(case_id: str) -> None:
    """gate에 걸린 run도 8개 필드를 전부 값으로 낸다.

    A R2: 이 지표들의 분모에서 gate target을 빼면 '인증이 일찍 걸리는
    서비스'가 진입구조 분석에서 조용히 사라진다. 모듈 층에서 그 삭제가
    일어나는 첫 경로가 파생값을 None으로 접는 것이므로 여기서 막는다.
    """
    r = norm(case_id)
    for field in DERIVED_SCALARS:
        assert getattr(r, field) is not None, (case_id, field)
    assert r.experienced_flow_sequence != ()


def test_gate_terminal_and_endpoint_twin_both_derive() -> None:
    """구조가 같고 terminal token만 다른 쌍. 둘 다 파생값이 나온다.

    endpoint 도달 run만 값이 나오고 gate run은 None이 되는 비대칭이 없다는
    증거다.
    """
    gate = norm("auth_after_task_select")
    reached = norm("menu_dependency_positive")
    for field in DERIVED_SCALARS:
        assert getattr(gate, field) is not None, field
        assert getattr(reached, field) is not None, field
    # gate 이전 진입구조가 그대로 관측된다 — reveal 1단, 과업 control 선택.
    assert gate.menu_dependency is True
    assert gate.nav_container_depth == 1
    assert gate.activation_depth == 2


def test_gate_before_discovery_still_reports_entry_structure() -> None:
    """가장 이른 gate(첫 step)에서도 진입구조 지표가 값으로 나온다."""
    r = norm("auth_before_task_discovery")
    assert r.menu_dependency is False
    assert r.nav_container_depth == 0
    assert r.activation_depth == 0
    assert r.forced_dismissal_count == 0
    assert r.auth_gate_stage == "BEFORE_TASK_DISCOVERY"
    assert r.depth_conditional_tokens == ()
    # Δ15: auth encounter는 flow_step_count에 포함된다(04 §5가 이름 붙였다).
    assert r.flow_step_count == 1


def test_menu_dependency_sees_reveal_before_gate_without_endpoint() -> None:
    """endpoint 신호가 없는 gate terminal에서도 gate 이전 reveal이 잡힌다.

    'endpoint 전'을 endpoint 신호가 있을 때만 평가했다면 gate run의
    menu_dependency가 통째로 사라졌을 것이다.
    """
    r = norm("auth_before_discovery_after_reveal")
    assert "ENDPOINT_REACHED" not in r.experienced_flow_sequence
    assert r.menu_dependency is True


def test_only_two_none_paths_exist_and_neither_is_the_gate() -> None:
    """산출 불능 경로는 빈 sequence와 경로 불확정 둘뿐이다(KL-13)."""
    assert all(getattr(norm("empty"), f) is None for f in DERIVED_SCALARS)
    assert all(getattr(norm("abstain_mixed"), f) is None for f in DERIVED_SCALARS)
    assert norm("empty").auth_gate_stage == "UNDETERMINED"
    for case_id in GATE_CASES:
        assert all(getattr(norm(case_id), f) is not None for f in DERIVED_SCALARS), case_id


# ══════════════════════════════════════════════════════════════════════════
# 10. R6-Q8 — 층 한정. 값을 단독으로 쓰지 않는다
# ══════════════════════════════════════════════════════════════════════════
AMBIGUOUS_VALUES = ("AUTH_GATE", "ABSTAIN")

#: 허용 문맥. (a) ACTION_ 접두 식별자, (b) 문자열 리터럴(= canonical 값 자체),
#: (c) action_token= / endpoint_status= 로 층을 한정한 산문.
ALLOWED_PREFIXES = ("ACTION_", '"', "'", "action_token=", "endpoint_status=")


def _unqualified_uses(text: str) -> list[str]:
    hits: list[str] = []
    for value in AMBIGUOUS_VALUES:
        start = 0
        while (i := text.find(value, start)) != -1:
            start = i + 1
            before = text[:i]
            if any(before.endswith(prefix) for prefix in ALLOWED_PREFIXES):
                continue
            line_no = before.count("\n") + 1
            line = text.splitlines()[line_no - 1].strip()
            hits.append(f"line {line_no}: {line}")
    return hits


def test_module_source_never_uses_ambiguous_value_bare() -> None:
    """action_token 층과 endpoint_status 층이 같은 문자열을 공유한다(A R6-Q8).

    C가 GATE 3에서 단독 등장을 finding으로 낸다. 소스에서 미리 막는다.
    """
    src = (RESEARCH / "src" / "landing_accessibility" / "v3_runner" / "flow.py").read_text(
        encoding="utf-8"
    )
    assert _unqualified_uses(src) == []


def test_this_test_module_never_uses_ambiguous_value_bare() -> None:
    assert _unqualified_uses(Path(__file__).read_text(encoding="utf-8")) == []


def test_fixtures_never_use_ambiguous_value_bare() -> None:
    for path in sorted(FIXTURES.glob("*.json")):
        assert _unqualified_uses(path.read_text(encoding="utf-8")) == [], path.name


def test_qualified_constants_carry_the_layer_in_their_name() -> None:
    """상수 이름만 봐도 action_token 층임이 읽혀야 한다."""
    assert ACTION_AUTH_GATE == "AUTH_GATE"
    assert ACTION_ABSTAIN == "ABSTAIN"


def test_stage_vocabulary_does_not_collide_with_action_tokens() -> None:
    """auth_gate_stage 어휘는 action_token 층과 문자열이 겹치지 않는다.

    겹치는 두 값(R6-Q8)이 stage 층으로 새어 들어오면 한정으로도 못 막는다.
    """
    assert AUTH_STAGE_VALUES.isdisjoint(CANONICAL_TOKENS)


def test_every_stage_output_is_in_the_stage_vocabulary() -> None:
    for path in sorted(FIXTURES.glob("*.json")):
        stage = normalize_flow(load(path.stem)).auth_gate_stage
        assert stage is None or stage in AUTH_STAGE_VALUES, path.name


def test_endpoint_status_layer_is_not_produced_here() -> None:
    """이 모듈은 endpoint_status 층의 값을 만들지 않는다(KL-12)."""
    assert not hasattr(norm("menu_dependency_positive"), "endpoint_status")


def test_layer_guard_is_not_vacuous() -> None:
    """가드 자신의 대조군.

    위 세 검사는 '위반이 없다'와 '가드가 아무것도 못 잡는다'가 똑같이
    빈 리스트로 나온다. 양성 입력에서 실제로 잡히는지 확인해야 통과가
    의미를 갖는다.
    """
    # 양성 — 층 없이 값만 단독으로 쓴 산문.
    # 대조 입력은 상수에서 조립한다. 여기에 리터럴을 그대로 적으면 이 파일
    # 자신이 위 test_this_test_module_never_uses_ambiguous_value_bare 를
    # 위반한다 — 실제로 한 번 위반해서 가드가 잡았다.
    assert _unqualified_uses(f"이 run 은 {ACTION_AUTH_GATE} 로 끝났다") != []
    assert _unqualified_uses(f"증거 부족이면 {ACTION_ABSTAIN} 이다") != []
    assert _unqualified_uses(f"`{ACTION_AUTH_GATE}` 로 표기") != []
    # 음성 — 허용된 세 문맥
    assert _unqualified_uses("action_token=AUTH_GATE 로 한정한다") == []
    assert _unqualified_uses("endpoint_status=ABSTAIN 로 한정한다") == []
    assert _unqualified_uses('if token == "AUTH_GATE":') == []
    assert _unqualified_uses("ACTION_ABSTAIN = 'ABSTAIN'") == []


# ══════════════════════════════════════════════════════════════════════════
# 11. Δ9 CONDITIONAL 3종 — 입력수단이 depth 귀속을 가른다
#     (A T-A-V3-STEP1-006)
# ══════════════════════════════════════════════════════════════════════════
def test_conditional_dropdown_vs_free_text_pair() -> None:
    """대조 쌍의 핵심. 구조가 완전히 같고 input_mode만 다르다.

    control을 활성화해 값을 정했으면 activation이고, 자유입력란에 쳤으면
    타이핑이라 activation이 아니다. flow_step_count는 양쪽 같다 — 두 경우
    모두 task-intent 조작인 것은 변함없기 때문이다.
    """
    picker = norm("conditional_dropdown")
    typed = norm("conditional_free_text")
    assert picker.experienced_flow_sequence == typed.experienced_flow_sequence
    assert picker.activation_depth == 5  # SELECT_FUNCTION+SUBMIT+3 picker
    assert typed.activation_depth == 2  # SELECT_FUNCTION+SUBMIT
    assert picker.flow_step_count == typed.flow_step_count == 5


def test_conditional_records_carry_the_basis() -> None:
    """A Δ9 요구: 어느 토큰이 어떤 근거로 포함/제외됐는지 관측에 남긴다."""
    picker = norm("conditional_dropdown")
    assert len(picker.depth_conditional_tokens) == 3
    for rec in picker.depth_conditional_tokens:
        assert rec.action_token in CONDITIONAL_DEPTH_TOKENS
        assert rec.input_mode == "DROPDOWN"
        assert rec.included_in_activation_depth is True
        assert "DROPDOWN" in rec.basis

    typed = norm("conditional_free_text")
    for rec in typed.depth_conditional_tokens:
        assert rec.included_in_activation_depth is False
        assert "FREE_TEXT" in rec.basis


def test_conditional_mixed_modes_within_one_flow() -> None:
    """출발지는 map pan, 도착지는 dropdown, 날짜는 자유입력.

    관측 단위 스칼라 하나로는 표현할 수 없는 경우다 — `input_mode`를 step
    단위로 받은 이유이며, 그 선택이 실제로 필요하다는 증거다.
    """
    r = norm("conditional_mixed_modes")
    verdicts = {
        rec.action_token: rec.included_in_activation_depth for rec in r.depth_conditional_tokens
    }
    assert verdicts == {
        "SELECT_ORIGIN": True,
        "SELECT_DESTINATION": True,
        "SELECT_DATE": False,
    }
    assert r.activation_depth == 4  # SELECT_FUNCTION + SUBMIT + 2 picker


@pytest.mark.parametrize(
    "case_id",
    ["conditional_mode_missing", "conditional_unrecognised_mode", "conditional_step_level_mixed"],
)
def test_undeterminable_input_mode_nulls_activation_depth_only(case_id: str) -> None:
    """모르는 것을 0으로 세지 않는다. 다만 다른 필드까지 접지는 않는다.

    input_mode를 몰라도 sequence·dismissal·reveal 구조는 그대로 관측됐다.
    판정 불능을 필요 이상으로 번지게 하면 그것도 정보 손실이다.
    """
    r = norm(case_id)
    assert r.activation_depth is None
    assert r.flow_step_count is not None
    assert r.menu_dependency is not None
    assert r.nav_container_depth is not None
    assert r.forced_dismissal_count is not None
    assert r.auth_gate_stage == "NONE"
    assert any(rec.included_in_activation_depth is None for rec in r.depth_conditional_tokens)


def test_unrecognised_mode_is_not_silently_treated_as_picker() -> None:
    """'DROPDOWN/MAP_PAN 계열'의 '계열'을 임의 확장하지 않았다 (KL-16).

    CALENDAR는 A가 산문에서 picker 예시로 들었지만 Δ8-R5 열거값으로 이름을
    준 것은 아니다. 지어내지 않고 불능으로 접은 뒤 KL-16으로 올린다.
    """
    r = norm("conditional_unrecognised_mode")
    (rec,) = r.depth_conditional_tokens
    assert rec.input_mode == "CALENDAR"
    assert rec.included_in_activation_depth is None
    assert "KL-16" in rec.basis


def test_flows_without_conditional_tokens_have_empty_record() -> None:
    assert norm("menu_dependency_positive").depth_conditional_tokens == ()


# ══════════════════════════════════════════════════════════════════════════
# 12. Δ10 — 증거의 부재는 부재의 증거가 아니다 (A T-A-V3-STEP1-007 R13)
# ══════════════════════════════════════════════════════════════════════════
def test_stage_none_requires_terminal_evidence() -> None:
    """NONE vs UNDETERMINED 대조 쌍. 같은 'auth 신호 없음'인데 갈린다.

    이 구분이 없으면 관측하지 못한 것이 '인증 없음'으로 집계되고 auth
    발생률이 체계적으로 과소추정된다.
    """
    reached = norm("auth_none")
    abandoned = norm("no_terminal_no_auth")
    assert "AUTH_GATE" not in reached.experienced_flow_sequence
    assert "AUTH_GATE" not in abandoned.experienced_flow_sequence
    assert reached.auth_gate_stage == "NONE"
    assert abandoned.auth_gate_stage == "UNDETERMINED"


def test_gate_terminal_also_licenses_determination() -> None:
    """terminal은 endpoint뿐 아니라 gate도 포함한다 (R2와 Δ10의 접합).

    gate에 닿은 run을 UNDETERMINED로 접으면 R2가 금지한 삭제가 일어난다.
    """
    for case_id in ("auth_before_task_discovery", "auth_after_task_select"):
        assert norm(case_id).auth_gate_stage != "UNDETERMINED", case_id


def test_menu_dependency_false_requires_terminal() -> None:
    """False("reveal 없이 도달했다")는 적극적 주장이라 terminal을 요구한다."""
    assert norm("menu_dependency_negative").menu_dependency is False
    assert norm("dismissal_only_no_activation").menu_dependency is None


def test_menu_dependency_true_needs_no_terminal() -> None:
    """반대로 True는 양성 관측이라 terminal 없이도 확정된다.

    위 테스트와의 비대칭이 의도된 것임을 고정한다 — reveal을 봤다는 사실은
    경로가 중단돼도 사라지지 않는다.
    """
    r = norm("endpoint_not_reached")
    assert r.menu_dependency is True
    assert r.nav_container_depth is None


def test_counts_stay_determined_without_terminal() -> None:
    """count 3종은 milestone을 참조하지 않아 관측만 있으면 확정된다 (KL-18).

    menu_dependency/nav_container_depth와 다르게 처리한 지점이므로 명시적으로
    고정한다. A 재정이 필요하다고 KL-18에 올려 뒀다.
    """
    r = norm("dismissal_only_no_activation")
    assert r.activation_depth == 0
    assert r.flow_step_count == 0
    assert r.forced_dismissal_count == 2
    assert r.menu_dependency is None  # 같은 관측에서 이쪽은 불능


def test_stage_is_never_none_now_that_enum_has_undetermined() -> None:
    """판정불능 값이 생겼으므로 None으로 접을 이유가 없다 (Δ10)."""
    for path in sorted(FIXTURES.glob("*.json")):
        stage = normalize_flow(load(path.stem)).auth_gate_stage
        assert stage is not None, path.name
        assert stage in AUTH_STAGE_VALUES, path.name


def test_undetermined_is_a_reported_category_not_a_dropped_row() -> None:
    """UNDETERMINED가 실제로 산출된다 — 조용히 사라지지 않는다.

    분모에서 빼는 것은 mart의 실수가 될 수 있고 그건 docstring으로 경고했다.
    모듈 층에서 할 수 있는 것은 그 범주를 값으로 내보내는 것이다.
    """
    stages = {normalize_flow(load(path.stem)).auth_gate_stage for path in FIXTURES.glob("*.json")}
    assert "UNDETERMINED" in stages
    assert "NONE" in stages


# ══════════════════════════════════════════════════════════════════════════
# 13. Δ15 — 두 지표의 의도된 비대칭 (A T-A-V3-STEP1-012, GAP-03)
# ══════════════════════════════════════════════════════════════════════════
def test_auth_encounter_asymmetry_between_the_two_metrics() -> None:
    """같은 토큰이 한 지표엔 들어가고 다른 지표엔 안 들어간다 — 의도된 것이다.

    04 §5가 `flow_step_count`에만 'auth encounter'를 이름 붙여 포함시켰다.
    Δ9의 3항 기준으로는 auth는 마주친 상태이지 control 활성화가 아니라
    `activation_depth`에서 빠진다. 두 지표가 다른 질문을 한다.

    이 테스트가 없으면 다음 사람이 비대칭을 버그로 보고 '맞춰서' SSOT 문면과
    어긋나게 만든다.
    """
    with_auth = norm("auth_after_task_select")
    assert with_auth.experienced_flow_sequence == (
        "OPEN_GLOBAL_MENU",
        "SELECT_FUNCTION",
        "AUTH_GATE",
    )
    assert with_auth.activation_depth == 2  # auth 미포함
    assert with_auth.flow_step_count == 3  # auth 포함


def test_endpoint_marker_excluded_from_both_metrics() -> None:
    """도달 표지는 사용자가 한 일이 아니다 — 두 지표 모두에서 빠진다."""
    r = norm("menu_dependency_positive")
    assert r.experienced_flow_sequence[-1] == "ENDPOINT_REACHED"
    assert r.activation_depth == 2
    assert r.flow_step_count == 2  # ENDPOINT_REACHED 미포함


def test_flow_step_count_equation_is_broken_and_that_is_information() -> None:
    """`flow_step_count == len(task_flow_sequence)` 는 더 이상 성립하지 않는다.

    endpoint 도달 flow에서는 정확히 1 작고(task_flow에는 도달 표지가 남아
    있으므로), gate terminal flow에서는 같다(auth는 양쪽 다 포함). 두 산출이
    다른 질문에 답한다는 사실이 이 차이로 드러난다(KL-05).
    """
    reached = norm("menu_dependency_positive")
    assert reached.flow_step_count == len(reached.task_flow_sequence) - 1

    gated = norm("auth_after_task_select")
    assert gated.flow_step_count == len(gated.task_flow_sequence)


# ══════════════════════════════════════════════════════════════════════════
# 14. GAP-04 — 결측 표현 규약
# ══════════════════════════════════════════════════════════════════════════
COUNT_FIELDS = ("activation_depth", "flow_step_count", "nav_container_depth")
ALL_COUNT_FIELDS = (*COUNT_FIELDS, "forced_dismissal_count")


def test_zero_always_means_counted_never_unobserved() -> None:
    """이 모듈의 불변식. 0은 언제나 '세었고 0'이다.

    이게 깨지면 '장애물이 없었다'와 '장애물을 관측하지 못했다'가 같은 값이
    된다 — Δ10이 막으려는 결함의 count 판이다.
    """
    empty = norm("empty")
    for field in ALL_COUNT_FIELDS:
        assert getattr(empty, field) is None, field  # 0이 아니다

    counted = norm("dismissal_only_no_activation")
    assert counted.activation_depth == 0  # 세었고 0
    assert counted.forced_dismissal_count == 2
    assert counted.nav_container_depth is None  # 못 셌으므로 0이 아니라 None


def test_missing_representation_is_uniform_within_one_row() -> None:
    """한 행 안에서 결측 표현이 섞이지 않는다 (A GAP-04).

    수치/bool 결측은 전부 `None`, 범주 결측은 `UNDETERMINED`뿐이다. 센티널
    정수(-1)나 빈 문자열을 결측으로 쓰지 않는다.
    """
    for path in sorted(FIXTURES.glob("*.json")):
        r = normalize_flow(load(path.stem))
        for field in ALL_COUNT_FIELDS:
            value = getattr(r, field)
            assert value is None or (isinstance(value, int) and value >= 0), (
                path.name,
                field,
            )
        assert r.menu_dependency is None or isinstance(r.menu_dependency, bool)
        assert r.auth_gate_stage in AUTH_STAGE_VALUES, path.name
        assert r.auth_gate_stage != "", path.name


def test_conditional_record_missing_verdict_is_none_not_false() -> None:
    """판정 불능을 False로 접으면 '제외됐다'는 적극적 주장이 돼 버린다."""
    r = norm("conditional_mode_missing")
    for rec in r.depth_conditional_tokens:
        assert rec.included_in_activation_depth is None
        assert rec.included_in_activation_depth is not False
