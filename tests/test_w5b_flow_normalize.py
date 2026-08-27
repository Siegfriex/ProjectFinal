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
    ACTIVATION_TOKENS,
    CANONICAL_TOKENS,
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


def test_reveal_set_is_only_the_three_named_in_section_5() -> None:
    """04 §5가 이름으로 지목한 3종만. '등'을 임의 확장하지 않았다(KL-02)."""
    named_in_section_5 = {"OPEN_GLOBAL_MENU", "OPEN_LOCAL_MENU", "EXPAND_ACCORDION"}
    assert named_in_section_5 == REVEAL_TOKENS


def test_known_limitations_are_declared() -> None:
    """04에 규정이 없어 W5B가 판단한 지점이 코드에 남아 있어야 한다."""
    assert len(KNOWN_LIMITATIONS) >= 10
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
    assert r.auth_gate_stage == "NONE"


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
    """endpoint 신호가 없으면 sequence 전체가 'endpoint 전'이다."""
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


def test_nav_container_depth_counts_whole_prefix_when_never_engaged() -> None:
    """engagement token이 없는 flow — KL-10의 조작화를 고정한다."""
    r = norm("endpoint_not_reached")
    assert r.nav_container_depth == 2


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


def test_auth_flag_absent_gives_none_stage() -> None:
    """대조군: 같은 sequence에서 flag만 끄면 NONE."""
    steps = [step("SELECT_FUNCTION", 0), step("SELECT_RESULT", 1)]
    assert normalize_flow(steps).auth_gate_stage == "NONE"


# ══════════════════════════════════════════════════════════════════════════
# 5. activation_depth / flow_step_count — typing 분리 (04 §5)
# ══════════════════════════════════════════════════════════════════════════
def test_typing_counts_in_flow_step_count_but_not_activation_depth() -> None:
    with_typing = norm("typing_submit_result")
    without = norm("submit_result_no_typing")
    assert with_typing.activation_depth == without.activation_depth == 2
    assert without.flow_step_count == 3
    assert with_typing.flow_step_count == 4


def test_state_markers_do_not_count_as_activation() -> None:
    """AUTH_GATE·ENDPOINT_REACHED는 도달한 상태이지 activation이 아니다."""
    r = norm("menu_dependency_negative")
    assert r.experienced_flow_sequence == ("SELECT_FUNCTION", "ENDPOINT_REACHED")
    assert r.activation_depth == 1
    assert r.flow_step_count == 2


def test_long_mixed_path_full_profile() -> None:
    """복합 경로 하나를 전 필드로 고정한다 (회귀 앵커)."""
    r = norm("long_mixed_path")
    assert r.forced_dismissal_count == 2
    assert r.experienced_flow_sequence.count("DISMISS_OBSTRUCTION") == 2
    assert "DISMISS_OBSTRUCTION" not in r.task_flow_sequence
    assert len(r.experienced_flow_sequence) == 14
    assert r.flow_step_count == 12
    # activation: OPEN_GLOBAL_MENU, EXPAND_ACCORDION, SELECT_CATEGORY,
    # SELECT_FUNCTION, SELECT_ORIGIN, SELECT_DESTINATION, SELECT_DATE,
    # SUBMIT_QUERY, SELECT_RESULT, OPEN_ITEM_DETAIL = 10
    # (INPUT_QUERY=typing, DISMISS 2회, ENDPOINT_REACHED 제외)
    assert r.activation_depth == 10
    assert r.menu_dependency is True
    assert r.nav_container_depth == 2
    assert r.auth_gate_stage == "NONE"


# ══════════════════════════════════════════════════════════════════════════
# 6. 산출 불능 — None이지 0/FAIL이 아니다
# ══════════════════════════════════════════════════════════════════════════
DERIVED_SCALARS = (
    "activation_depth",
    "flow_step_count",
    "menu_dependency",
    "nav_container_depth",
    "forced_dismissal_count",
    "auth_gate_stage",
)


def test_empty_sequence_yields_none_not_zero() -> None:
    r = norm("empty")
    assert r.task_flow_sequence == ()
    assert r.experienced_flow_sequence == ()
    for field in DERIVED_SCALARS:
        assert getattr(r, field) is None, field
    # 'NONE' 문자열(관측된 부재)과 None(판정 안 함)은 다른 사실이다.
    assert r.auth_gate_stage != "NONE"


def test_abstain_nulls_all_derived_scalars() -> None:
    r = norm("abstain_mixed")
    assert "ABSTAIN" in r.experienced_flow_sequence
    assert "ABSTAIN" in r.task_flow_sequence  # raw 투영이므로 남긴다
    for field in DERIVED_SCALARS:
        assert getattr(r, field) is None, field


def test_abstain_twin_control_group_does_derive() -> None:
    """대조군. ABSTAIN token만 뺀 같은 앞부분에서는 파생값이 나온다.

    이게 없으면 None이 구조 탓인지 ABSTAIN 탓인지 구분되지 않는다.
    """
    r = norm("abstain_free_twin")
    assert r.experienced_flow_sequence == ("DISMISS_OBSTRUCTION", "OPEN_GLOBAL_MENU")
    for field in DERIVED_SCALARS:
        assert getattr(r, field) is not None, field
    assert r.activation_depth == 1
    assert r.forced_dismissal_count == 1
    assert r.menu_dependency is True
    assert r.auth_gate_stage == "NONE"


def test_abstain_alone() -> None:
    r = normalize_flow([step("ABSTAIN", 0)])
    assert r.experienced_flow_sequence == ("ABSTAIN",)
    assert all(getattr(r, f) is None for f in DERIVED_SCALARS)


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
    assert r.flow_step_count == 2


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
