"""W5L — `Δ30`(Scout 경로선택 정책 승계) · `Δ32`(0-activation 은 주장이다) 이행 고정.

정본은 `research/landing_accessibility/control/v3/V3_0_1_SUCCESSOR_DELTA.md` 의
`## Δ30` · `## Δ32` 절이다. 이 파일의 주석 안 `[인용]` 은 그 원문 축자다.

이 파일이 붙드는 것 (지금까지 **아무것도 붙들고 있지 않던 것들**)
--------------------------------------------------------------------

1. **tie-break 전순서** — v3 는 `(task_binding_candidate desc, dom_order asc,
   selector asc)` 를 쓴다. `marked_primary` 를 읽지 않고 **어떤 점수도 읽지 않는다.**
   1차 키의 소스가 트리에 없다는 사실도 함께 고정한다 — 없는 binder 를 만들지 않았다.
2. **v2 를 건드리지 않았다** — `engine/l0_collector.min4_sort_key` 는 여전히
   `marked_primary` 를 1차 키로 쓴다. v3 는 자기 전순서를 `v3_runner/tiebreak.py` 에
   따로 갖는다.
3. **분기 대상 집합** — `Δ9` IN 10 + CONDITIONAL 3. `SUBMIT_QUERY` 는 v3 에서 분기
   대상이다(v2.1 과 달라지는 실질).
4. **`terminal_reason` 15값** — `Δ10-R11` 13 + `Δ30` `BUDGET_EXCEEDED` +
   `Δ32` `NO_TASK_CANDIDATE_FOUND`. 기존 13값의 판정은 회귀 대조군으로 고정한다.
5. **`Δ32` 두 갈래** — (a) binder 계약 위반은 `RunnerError`, (b) 관측된 후보 0건은
   `ABSTAIN` 과 `NO_TASK_CANDIDATE_FOUND` 조합. **둘이 같은 출력이면 이 파일은 실패한다.**
6. **`Δ32-R29`** — 후보 0건 위에서 `endpoint_status=REACHED` 를 낼 수 없다.
7. **raw 포착 순서** — surface evidence 가 binding 보다 **앞**이라 계약 위반으로
   멈춰도 그 시점까지의 raw 가 디스크에 남는다(`D-V3-FINDING-003` 의 교훈).

실사이트 접속 0. 브라우저 0. fixture/대역만 쓴다.
"""

from __future__ import annotations

import dataclasses
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any, ClassVar

import pytest

REPO = Path(__file__).resolve().parents[1]
RESEARCH = REPO / "research" / "landing_accessibility"
sys.path.insert(0, str(RESEARCH / "src"))

from landing_accessibility.engine.l0_collector import (  # noqa: E402
    Min4ProbeContractError,
    min4_sort_key,
)
from landing_accessibility.v3_runner import contracts, discovery, registry, runner  # noqa: E402
from landing_accessibility.v3_runner import terminal as terminal_module  # noqa: E402
from landing_accessibility.v3_runner.evidence import EvidencePayload  # noqa: E402
from landing_accessibility.v3_runner.runner import (  # noqa: E402
    BRANCH_ELIGIBLE_TOKENS,
    BRANCH_INELIGIBLE_TOKENS,
    DEPTH_CONDITIONAL_TOKENS,
    DEPTH_IN_TOKENS,
    DEPTH_OUT_TOKENS,
    CandidateBindingContractError,
    PlannedAction,
    RawTransition,
    RunnerError,
    SurfaceObservation,
    V3Runner,
)
from landing_accessibility.v3_runner.safety import ActivationSafetyGuard  # noqa: E402
from landing_accessibility.v3_runner.scout_strategy import (  # noqa: E402
    MinPathScoutStrategy,
    ScoutBranchSetError,
    _classify_action_token,
)
from landing_accessibility.v3_runner.terminal import (  # noqa: E402
    ALLOWED_ENDPOINT_STATUS_REASONS,
    EndpointStatus,
    TerminalReason,
    TerminalResolution,
    TerminalSignals,
    ZeroActivationClaimError,
    classify_terminal,
    validate_reached_requires_binding,
    validate_status_reason,
)
from landing_accessibility.v3_runner.tiebreak import (  # noqa: E402
    TASK_BINDING_CANDIDATE_FIELD,
    TASK_BINDING_CANDIDATE_SOURCE_ABSENT,
    V3_TIEBREAK_RETIRED_KEYS,
    V3_TIEBREAK_TOTAL_ORDER,
    task_binding_candidate_membership,
    v3_tiebreak_sort_key,
)

# `Δ10-R11` 이 선언한 원래 13값 — **회귀 대조군.** 이 목록은 늘어나지 않는다.
R11_ORIGINAL_THIRTEEN = (
    "TIMEOUT",
    "WAF_BLOCK",
    "ACTIVE_CHALLENGE",
    "NO_PUBLIC_MOBILE_WEB",
    "TASK_SURFACE_ABSENT",
    "APP_REQUIRED",
    "CONTROL_DISABLED_OR_INERT",
    "FORBIDDEN_ACTION_REQUIRED",
    "AUTH_REQUIRED",
    "EVIDENCE_DEFECT",
    "REPLAY_BROKEN",
    "AMBIGUOUS_MULTIPLE_CANDIDATES",
    "OTHER",
)

# `Δ9` 표 축자 — 이 파일이 코드에서 읽지 않고 **원문에서 옮겨 적은** 대조군이다.
# 코드의 집합을 코드로 검사하면 같은 오류를 두 번 적을 뿐이다.
DELTA9_IN_TEN = (
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
)
DELTA9_OUT_FIVE = (
    "INPUT_QUERY",
    "DISMISS_OBSTRUCTION",
    "AUTH_GATE",
    "ENDPOINT_REACHED",
    "ABSTAIN",
)
DELTA9_CONDITIONAL_THREE = ("SELECT_ORIGIN", "SELECT_DESTINATION", "SELECT_DATE")


def _cand(**kw: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "selector": "#c",
        "tag": "button",
        "role": None,
        "aria_label": None,
        "visible_text": "다음",
        "dom_order": 0,
        "hittable": True,
        "enabled": True,
    }
    base.update(kw)
    return base


# ══════════════════════════════════════════════════════════════════════════
# 1. Δ30 tie-break — 1차 키를 `task_binding_candidate` 로 대체했다
# ══════════════════════════════════════════════════════════════════════════
def test_v3_tiebreak_total_order_is_declared_verbatim_from_delta30() -> None:
    """`[Δ30-tiebreak 인용]` *"tie-break 전순서 = `task_binding_candidate desc,
    dom_order asc, selector asc`"*."""
    assert V3_TIEBREAK_TOTAL_ORDER == (
        "task_binding_candidate desc",
        "dom_order asc",
        "selector asc",
    )


def test_v3_tiebreak_primary_key_is_set_membership_not_marked_primary() -> None:
    """1차 키가 `task_binding_candidate` 다. `marked_primary` 는 **읽히지 않는다**.

    `[Δ30 인용]` *"`marked_primary` 는 대표기능 classifier 의 산물이고 v3 는 그것을
    퇴역시켰다(`D3-03`)"*.
    """
    bound = _cand(selector="#z", dom_order=9, task_binding_candidate=True)
    marked_only = _cand(selector="#a", dom_order=0, marked_primary=True)

    ordered = sorted([marked_only, bound], key=v3_tiebreak_sort_key)
    assert ordered[0]["selector"] == "#z", (
        "binder 가 지명한 후보가 1위여야 한다 — marked_primary 는 v3 에 없다"
    )

    # 같은 두 후보를 v2 전순서로 재면 반대다 — 두 정책이 실제로 다르다는 대조군.
    v2_ordered = sorted([marked_only, bound], key=min4_sort_key)
    assert v2_ordered[0]["selector"] == "#a"


def test_v3_tiebreak_never_reads_marked_primary_or_any_score() -> None:
    """`[Δ30 인용]` *"**점수를 키로 쓰지 않는다** — 집합 소속과 구조값만"* /
    *"점수는 구현이 바뀌면 순서가 바뀐다"*.

    퇴역 키를 어떤 값으로 흔들어도 전순서가 움직이지 않는다.
    """
    quiet = _cand(selector="#b", dom_order=1)
    loud = _cand(
        selector="#a",
        dom_order=2,
        marked_primary=True,
        area_css_px2=999999.0,
        similarity_score=0.99,
        score=1000,
        rank_score=1,
        viewport_score=1,
    )
    assert v3_tiebreak_sort_key(quiet) < v3_tiebreak_sort_key(loud)
    assert {"marked_primary", "area_css_px2", "similarity_score"} <= V3_TIEBREAK_RETIRED_KEYS


def test_v3_tiebreak_secondary_and_tertiary_keys_are_structural() -> None:
    """2차 `dom_order asc`, 3차 `selector asc` — `V2-C008` 취지 승계(관측값 배제)."""
    same_order = [
        _cand(selector="#b", dom_order=3),
        _cand(selector="#a", dom_order=3),
        _cand(selector="#c", dom_order=1),
    ]
    assert [c["selector"] for c in sorted(same_order, key=v3_tiebreak_sort_key)] == [
        "#c",
        "#a",
        "#b",
    ]


def test_v3_tiebreak_rejects_missing_dom_order_like_v2_does() -> None:
    """`dom_order` 결측은 관측 결측이 아니라 probe 결함이다 — v2 와 **같은 계약**."""
    with pytest.raises(Min4ProbeContractError):
        v3_tiebreak_sort_key({"selector": "#x"})


def test_task_binding_candidate_membership_separates_unobserved_from_false() -> None:
    """미관측(`None`)과 비지명(`False`)은 **기록에서 다르다** — 정렬에서만 같은 자리다."""
    assert task_binding_candidate_membership(_cand()) is None
    assert task_binding_candidate_membership(_cand(task_binding_candidate=False)) is False
    assert task_binding_candidate_membership(_cand(task_binding_candidate=True)) is True
    # 정렬 키에서는 둘 다 1 — 미관측을 지명으로도 비지명으로도 승격시키지 않는다.
    assert v3_tiebreak_sort_key(_cand(selector="#x"))[0] == 1
    assert v3_tiebreak_sort_key(_cand(selector="#x", task_binding_candidate=False))[0] == 1


def test_task_binding_candidate_has_no_producer_in_the_tree() -> None:
    """**측정 고정** — 1차 키를 산출하는 `03 §4` binder 가 트리에 없다.

    없는 기능을 만들지 않았다는 사실 자체를 테스트로 둔다. v3 의 유일한 binder
    (`discover_task_candidates`)가 이 필드를 채우지 않는 것이 관측 대상이다.
    """
    probe = {
        "primary_action_candidates": [
            {"selector": "#go", "tag": "button", "dom_order": 0, "hittable": True, "enabled": True}
        ]
    }
    produced = discovery.discover_task_candidates(probe, {"task_id": "t"})
    assert produced, "양성 대조 — 후보 자체는 나온다"
    for candidate in produced:
        assert TASK_BINDING_CANDIDATE_FIELD not in dict(candidate), (
            "binder 가 생겼으면 이 테스트를 갱신해라 — 그때 1차 키가 발화한다"
        )
    assert "존재하지 않는다" in TASK_BINDING_CANDIDATE_SOURCE_ABSENT


def test_v3_is_the_default_policy_and_min4_is_not() -> None:
    """v3 경로선택의 기본값이 `Δ30` 전순서다. `MIN4_POLICY` 는 v2 대조용으로만 남는다."""
    assert discovery.DEFAULT_V3_PATH_POLICY is discovery.V3_TIEBREAK_POLICY
    assert discovery.DEFAULT_V3_PATH_POLICY is not discovery.MIN4_POLICY
    assert MinPathScoutStrategy().policy is discovery.V3_TIEBREAK_POLICY


def test_v2_min4_sort_key_is_untouched_by_delta30() -> None:
    """**v2 를 변형하지 않았다.** `min4_sort_key` 는 여전히 `marked_primary` 가 1차 키다.

    그 함수는 `l0_collector.rank_primary_action_candidates` 와 v2
    `l1_engine.Scout._activation_candidates` 가 **공유**한다 — 거기서 1차 키를 바꾸면
    v2 경로의 분기 순서가 같이 바뀐다. Δ30 은 v3 정책을 정한 것이지 v2 관측을 소급
    변경하라고 하지 않았다.
    """
    marked = _cand(selector="#z", dom_order=9, marked_primary=True)
    plain = _cand(selector="#a", dom_order=0, marked_primary=False)
    assert min4_sort_key(marked)[0] == 0
    assert min4_sort_key(plain)[0] == 1
    assert sorted([plain, marked], key=min4_sort_key)[0]["selector"] == "#z"


# ══════════════════════════════════════════════════════════════════════════
# 2. Δ30-branch — 분기 대상 집합 = Δ9 IN 10 + CONDITIONAL 3
# ══════════════════════════════════════════════════════════════════════════
def test_branch_eligible_set_equals_delta9_in_ten_plus_conditional_three() -> None:
    """`[Δ30-branch 인용]` *"분기 대상 집합 = `Δ9` 의 IN 10 + CONDITIONAL 3"*.

    대조군은 코드가 아니라 **`Δ9` 원문에서 옮겨 적은 목록**이다.
    """
    assert set(DEPTH_IN_TOKENS) == set(DELTA9_IN_TEN)
    assert set(DEPTH_CONDITIONAL_TOKENS) == set(DELTA9_CONDITIONAL_THREE)
    assert set(DEPTH_OUT_TOKENS) == set(DELTA9_OUT_FIVE)
    assert set(DELTA9_IN_TEN) | set(DELTA9_CONDITIONAL_THREE) == BRANCH_ELIGIBLE_TOKENS
    assert len(BRANCH_ELIGIBLE_TOKENS) == 13


def test_submit_query_is_a_branch_target_in_v3_unlike_v21() -> None:
    """`[Δ30-branch 인용]` *"**v2.1 과 달리 `SUBMIT_QUERY` 는 분기 대상이다**"*."""
    assert "SUBMIT_QUERY" in BRANCH_ELIGIBLE_TOKENS


def test_the_five_out_tokens_are_not_branch_targets() -> None:
    """`[Δ30-branch 인용]` *"`INPUT_QUERY`·`DISMISS_OBSTRUCTION`·`AUTH_GATE`·
    `ENDPOINT_REACHED`·`ABSTAIN` 은 분기 대상 아님"*.

    `[Δ30 인용]` *"popup 닫기를 분기 후보에 넣으면 닫기가 depth 로 세어진다."*
    """
    for token in DELTA9_OUT_FIVE:
        assert token not in BRANCH_ELIGIBLE_TOKENS, token
    assert set(DELTA9_OUT_FIVE) == BRANCH_INELIGIBLE_TOKENS
    assert not (BRANCH_ELIGIBLE_TOKENS & BRANCH_INELIGIBLE_TOKENS)


def test_every_token_the_strategy_can_emit_is_branch_eligible() -> None:
    """`_classify_action_token` 이 낼 수 있는 값이 전부 분기 대상 집합 안이다."""
    emitted = {
        _classify_action_token(_cand(role="tab")),
        _classify_action_token(_cand(in_list_container=True)),
        _classify_action_token(_cand()),
    }
    assert emitted <= BRANCH_ELIGIBLE_TOKENS
    assert emitted == {"SWITCH_TAB", "SELECT_RESULT", "SELECT_FUNCTION"}


def test_branch_set_violation_is_loud_not_silent(monkeypatch: pytest.MonkeyPatch) -> None:
    """분기 집합 밖 토큰을 내려 하면 **멈춘다.** 조용히 통과시키지 않는다.

    음성대조 — 강제선이 실제로 존재하는지 보려면 밖의 값을 한 번 내보게 해야 한다.
    """
    monkeypatch.setattr(
        "landing_accessibility.v3_runner.scout_strategy.BRANCH_ELIGIBLE_TOKENS",
        frozenset({"SWITCH_TAB"}),
    )
    with pytest.raises(ScoutBranchSetError):
        _classify_action_token(_cand())


# ══════════════════════════════════════════════════════════════════════════
# 3. Δ30 (4) — `terminal_reason` 에 `BUDGET_EXCEEDED` (14번째)
# ══════════════════════════════════════════════════════════════════════════
def test_budget_exceeded_is_the_fourteenth_terminal_reason() -> None:
    """`[Δ30 인용]` *"`Δ10-R11` 의 13값에 예산 소진이 없다. **`BUDGET_EXCEEDED` 를
    추가한다**(14값)"*."""
    assert TerminalReason.BUDGET_EXCEEDED.value == "BUDGET_EXCEEDED"
    assert "BUDGET_EXCEEDED" not in R11_ORIGINAL_THIRTEEN


def test_abstain_times_budget_exceeded_is_a_valid_combination() -> None:
    """`[Δ30 인용]` *"조합: `endpoint_status=ABSTAIN` 과 `terminal_reason=BUDGET_EXCEEDED`"*."""
    validate_status_reason(EndpointStatus.ABSTAIN, TerminalReason.BUDGET_EXCEEDED, None)
    assert TerminalReason.BUDGET_EXCEEDED in ALLOWED_ENDPOINT_STATUS_REASONS[EndpointStatus.ABSTAIN]


def test_budget_exceeded_is_not_allowed_under_any_other_endpoint_status() -> None:
    """음성대조 — 예산 소진은 `ABSTAIN` 밖 어디에도 붙지 않는다."""
    for status, allowed in ALLOWED_ENDPOINT_STATUS_REASONS.items():
        if status is EndpointStatus.ABSTAIN:
            continue
        assert TerminalReason.BUDGET_EXCEEDED not in allowed, status


def test_budget_exhaustion_classifies_as_absence_of_observation() -> None:
    """`MIN-7` — 예산 소진은 **최소가 아니라 관측 없음**이다.

    그래서 terminal 8종 어디에도 매달리지 않는다(`terminal=None`,
    `resolution=UNDETERMINED`). `NO_SAFE_ROUTE_FOUND`(경로를 *소진*했다) 와 다르다.
    """
    got = classify_terminal(TerminalSignals(evidence_complete=True, scout_budget_exhausted=True))
    assert got.endpoint_status is EndpointStatus.ABSTAIN
    assert got.terminal_reason is TerminalReason.BUDGET_EXCEEDED
    assert got.terminal is None
    assert got.resolution is TerminalResolution.UNDETERMINED

    exhausted_routes = classify_terminal(
        TerminalSignals(evidence_complete=True, permitted_routes_exhausted=True)
    )
    assert exhausted_routes.terminal_reason is not TerminalReason.BUDGET_EXCEEDED, (
        "'더 볼 게 없었다' 와 '더 안 봤다' 가 같은 값이 되면 안 된다"
    )


def test_budget_exhaustion_does_not_carry_the_budget_number() -> None:
    """`MIN-7` 후단 — **예산값을 대입하지 않는다.** note 에 숫자가 실리지 않는다."""
    got = classify_terminal(TerminalSignals(evidence_complete=True, scout_budget_exhausted=True))
    note = got.terminal_reason_note
    assert note is not None
    # 규범 참조(`A1 §2.6 MIN-7`)를 걷어내면 숫자가 하나도 남지 않아야 한다.
    assert not any(ch.isdigit() for ch in note.replace("A1 §2.6 MIN-7", "")), note
    # 신호 자체가 숫자를 받을 자리가 없다 — 예산값이 들어올 필드가 없다.
    names = {f.name for f in dataclasses.fields(TerminalSignals)}
    assert "scout_budget_exhausted" in names
    assert not {n for n in names if "budget" in n} - {"scout_budget_exhausted"}
    assert isinstance(TerminalSignals().scout_budget_exhausted, bool)


def test_budget_exhaustion_never_overrides_an_observed_terminal() -> None:
    """대조군 — terminal 관측이 있으면 그것이 이기고, 예산 사실은 note 로 남는다."""
    got = classify_terminal(
        TerminalSignals(
            evidence_complete=True, scout_budget_exhausted=True, auth_required_to_proceed=True
        )
    )
    assert got.terminal_reason is TerminalReason.AUTH_REQUIRED
    assert "scout_budget_exhausted_with_terminal_signal" in got.notes


# ── 회귀 대조군 — 기존 13값의 판정이 바뀌지 않았다 ──────────────────────────
def test_regression_control_the_original_thirteen_are_unchanged() -> None:
    """`Δ30`/`Δ32` 는 값을 **더했을 뿐** 기존 13값을 재정의하지 않았다."""
    values = {r.value for r in TerminalReason}
    assert set(R11_ORIGINAL_THIRTEEN) <= values
    assert values - set(R11_ORIGINAL_THIRTEEN) == {"BUDGET_EXCEEDED", "NO_TASK_CANDIDATE_FOUND"}
    assert len(values) == 15


@pytest.mark.parametrize(
    ("signals", "expected"),
    [
        (TerminalSignals(evidence_complete=False), TerminalReason.EVIDENCE_DEFECT),
        (TerminalSignals(evidence_complete=True, run_timed_out=True), TerminalReason.TIMEOUT),
        (
            TerminalSignals(
                evidence_complete=True, active_blocking_challenge=True, waf_block_observed=True
            ),
            TerminalReason.WAF_BLOCK,
        ),
        (
            TerminalSignals(evidence_complete=True, active_blocking_challenge=True),
            TerminalReason.ACTIVE_CHALLENGE,
        ),
        (TerminalSignals(evidence_complete=True, app_required=True), TerminalReason.APP_REQUIRED),
        (
            TerminalSignals(
                evidence_complete=True,
                public_web_task_observable=False,
                public_mobile_web_present=False,
            ),
            TerminalReason.NO_PUBLIC_MOBILE_WEB,
        ),
        (
            TerminalSignals(
                evidence_complete=True,
                public_web_task_observable=False,
                public_mobile_web_present=True,
            ),
            TerminalReason.TASK_SURFACE_ABSENT,
        ),
        (
            TerminalSignals(evidence_complete=True, auth_required_to_proceed=True),
            TerminalReason.AUTH_REQUIRED,
        ),
        (
            TerminalSignals(evidence_complete=True, prohibited_action_required=True),
            TerminalReason.FORBIDDEN_ACTION_REQUIRED,
        ),
        (
            TerminalSignals(evidence_complete=True, task_control_disabled_or_inert=True),
            TerminalReason.CONTROL_DISABLED_OR_INERT,
        ),
        (
            TerminalSignals(evidence_complete=True, replay_broken=True),
            TerminalReason.REPLAY_BROKEN,
        ),
        (
            TerminalSignals(evidence_complete=True, ambiguous_multiple_candidates=True),
            TerminalReason.AMBIGUOUS_MULTIPLE_CANDIDATES,
        ),
        (TerminalSignals(evidence_complete=True), TerminalReason.OTHER),
    ],
)
def test_regression_control_thirteen_determinations_survive_the_new_values(
    signals: TerminalSignals, expected: TerminalReason
) -> None:
    """새 두 값을 넣기 **전과 같은 입력**이 같은 사유를 낸다."""
    assert classify_terminal(signals).terminal_reason is expected


# ══════════════════════════════════════════════════════════════════════════
# 4. Δ32 — (a) 계약 위반과 (b) 관측된 0건은 절대 같은 출력이 아니다
# ══════════════════════════════════════════════════════════════════════════
def _contract(**overrides: Any) -> contracts.TaskContract:
    fields: dict[str, Any] = {
        "target_id": "W5L-DELTA30-01",
        "family_id": "F2",
        "service": "w5l-fixture-service",
        "starting_url": "https://fixture.invalid/entry",
        "frozen_task": "노선 조회",
        "task_instruction": "출발지·도착지·날짜를 넣고 조회한다",
        "fixed_fixture": "출발=서울역; 도착=부산역; 날짜=2026-09-01",
        "fixture_override": None,
        "endpoint_contract": "조회 결과 목록이 보이면 endpoint",
        "forbidden_actions": (),
        "task_contract_hash": "",
        "endpoint_contract_hash": "",
        "legacy_archetype": None,
        "mobile_web_eligibility": "ELIGIBLE_PUBLIC_MOBILE_WEB",
        "stratum": "ground",
        "is_pilot_5": False,
        "collection_order": 7,
        "task_role": contracts.TASK_ROLE_PRIMARY,
        "fixture_input_mode": None,
    }
    fields.update(overrides)
    draft = dataclasses.replace(
        contracts.TaskContract(**fields),
        endpoint_contract_hash=registry._sha256_text(fields["endpoint_contract"]),
    )
    return dataclasses.replace(
        draft, task_contract_hash=registry.recompute_task_contract_hash(draft)
    )


class _RegistryHasher:
    def task_contract_hash(self, contract: contracts.TaskContract) -> str | None:
        return registry.recompute_task_contract_hash(contract)

    def endpoint_contract_hash(self, contract: contracts.TaskContract) -> str | None:
        return registry._sha256_text(contract.endpoint_contract)


def _payload(node_id: str) -> EvidencePayload:
    return EvidencePayload(
        node_id=node_id,
        url="https://fixture.invalid/entry",
        dom="<html><body>surface</body></html>",
        ax={"role": "WebArea"},
        probe={},
        control_facts={},
    )


class _ScriptedDriver:
    def __init__(self) -> None:
        self.activated: list[PlannedAction] = []

    def capture_surface(self, contract: contracts.TaskContract) -> Sequence[SurfaceObservation]:
        return (
            SurfaceObservation(
                state_index="S0",
                scroll_y=0.0,
                viewport_width=390,
                viewport_height=844,
                url=contract.starting_url,
                payload=_payload("s000"),
            ),
        )

    def activate(self, action: PlannedAction) -> RawTransition:
        self.activated.append(action)
        return RawTransition(
            ok=True,
            state_before_id="S0",
            state_after_id="S1",
            url_before="https://fixture.invalid/entry",
            url_after="https://fixture.invalid/next",
            payload_before=_payload("b"),
            payload_after=_payload("a"),
        )


class _NaiveBinder:
    """`Δ32` 가 측정한 그 대역 — Protocol 은 만족하고 **계약은 어긴다**."""

    PROBE: ClassVar[dict[str, Any]] = {
        "primary_action_candidates": [
            {
                "selector": "#go",
                "tag": "button",
                "role": "button",
                "visible_text": "조회",
                "dom_order": 1,
                "hittable": True,
                "enabled": True,
            }
        ]
    }

    def bind(self, contract: contracts.TaskContract, states: Sequence[Any]) -> Sequence[Any]:
        # dataclass 가 아니라 **명시적으로 Mapping 이 아닌** 객체를 낸다.
        return [object()]


class _EmptyBinder:
    """형태는 멀쩡하다. 그 페이지에 후보가 **실제로** 없었다 — 관측이다."""

    def bind(
        self, contract: contracts.TaskContract, states: Sequence[Any]
    ) -> Sequence[Mapping[str, Any]]:
        return []


class _RealBinder:
    """`discovery` 실물 위임 — 양성 대조군."""

    def bind(
        self, contract: contracts.TaskContract, states: Sequence[Any]
    ) -> Sequence[Mapping[str, Any]]:
        return discovery.discover_task_candidates(_NaiveBinder.PROBE, contract)


class _FixedTerminal:
    def __init__(self, verdict: str | None) -> None:
        self.verdict = verdict

    def classify(self, contract: contracts.TaskContract, steps: Any) -> str | None:
        return self.verdict


def _runner(tmp_path: Path, **kwargs: Any) -> V3Runner:
    contract = _contract()
    return V3Runner(
        evidence_root=tmp_path / "evidence",
        contract_hasher=_RegistryHasher(),
        safety=ActivationSafetyGuard(contract),
        scout=MinPathScoutStrategy(),
        **kwargs,
    )


def test_delta32_a_contract_violation_stops_with_a_runner_error(tmp_path: Path) -> None:
    """(a) **계약 위반은 관측이 아니다.** `RunnerError` 로 멈춘다.

    `[Δ32 인용]` *"구성요소 간 계약 위반은 **결코 관측이 아니다.** 사이트에 대해
    아무것도 말해주지 않는다."*
    """
    r = _runner(tmp_path, binder=_NaiveBinder())
    with pytest.raises(CandidateBindingContractError) as excinfo:
        r.run(_contract(), driver=_ScriptedDriver(), task_id="W5L-A", run_id="w5l-a")
    assert issubclass(type(excinfo.value), RunnerError)


def test_delta32_r30_protocol_isinstance_passes_a_contract_violator() -> None:
    """`[Δ32-R30 인용]` *"Protocol 은 메서드 **이름**만 본다. **계약 위반이 타입 검사를
    통과한다.**"*

    이건 고치는 게 아니라 **알려진 한계로 고정**하는 것이다 — 그리고 그래서 런타임
    형태 검증이 따로 필요하다는 근거다(위 테스트가 그 검증을 고정한다).
    """
    naive = _NaiveBinder()
    assert isinstance(naive, runner.CandidateBinder), "isinstance 는 True 를 낸다"
    produced = naive.bind(_contract(), ())
    assert not all(isinstance(c, Mapping) for c in produced), "그런데 계약은 어긴다"


def test_delta32_b_observed_zero_candidates_is_recorded_as_an_observation(
    tmp_path: Path,
) -> None:
    """(b) **관측된 0건**은 기록한다 — `ABSTAIN` 과 `NO_TASK_CANDIDATE_FOUND` 조합.

    `[Δ32 인용]` 판정표: *"페이지에 후보 control 이 실제로 없다 → **관측** →
    `endpoint_status=ABSTAIN` 과 `terminal_reason=NO_TASK_CANDIDATE_FOUND` (15번째 값)"*
    """
    r = _runner(tmp_path, binder=_EmptyBinder())
    result = r.run(_contract(), driver=_ScriptedDriver(), task_id="W5L-B", run_id="w5l-b")
    assert result.task_candidate_count == 0
    assert result.endpoint_status == "ABSTAIN"
    assert result.terminal_reason == "NO_TASK_CANDIDATE_FOUND"
    assert result.raw_steps == ()


def test_delta32_the_two_branches_never_produce_the_same_output(tmp_path: Path) -> None:
    """**음성대조 — 이 파일의 핵심.** (a) 와 (b) 가 같은 출력이면 결함을 안 고친 것이다.

    C 의 표현: *"두 사건이 같은 값으로 합쳐지면 C 는 분모를 복원할 수 없다."*
    """
    # (a) — 예외. 관측 행 자체가 없다.
    with pytest.raises(CandidateBindingContractError):
        _runner(tmp_path / "a", binder=_NaiveBinder()).run(
            _contract(), driver=_ScriptedDriver(), task_id="W5L-A2", run_id="w5l-a2"
        )

    # (b) — 관측 행이 나온다. 사유가 붙어 있다.
    observed = _runner(tmp_path / "b", binder=_EmptyBinder()).run(
        _contract(), driver=_ScriptedDriver(), task_id="W5L-B2", run_id="w5l-b2"
    )
    assert observed.terminal_reason == "NO_TASK_CANDIDATE_FOUND"
    assert observed.task_candidate_count == 0

    # (양성대조) — 후보가 실제로 있으면 activation 이 일어난다.
    driver = _ScriptedDriver()
    healthy = _runner(tmp_path / "c", binder=_RealBinder()).run(
        _contract(), driver=driver, task_id="W5L-C", run_id="w5l-c"
    )
    assert healthy.task_candidate_count == 1
    # `Δ43`/`R37` 로 **다시 좁힌다** — 지운 것이 아니다.
    #
    # 이 줄은 `terminal_reason is None` 을 핀했다. 그 값이 여기서 지키려던 것은
    # "(b) 의 `NO_TASK_CANDIDATE_FOUND` 와 같은 출력이 아니다" 였다. `R37` 이후
    # 이 run 은 사유를 갖는다 — 선언된 정책이 endpoint 까지 가지 못했기 때문이다.
    # 그것은 **후보 부재와 다른 사건**이고, 그 구분이 이 테스트의 주장이다.
    assert healthy.terminal_reason != "NO_TASK_CANDIDATE_FOUND"
    assert healthy.path_discovery_outcome == "POLICY_DID_NOT_FIND_PATH"
    assert healthy.policy_relative is True  # 사이트가 아니라 우리 정책에 대한 진술
    assert observed.policy_relative is False  # 후보 0건은 페이지에 대한 관측이다
    assert [a.control_selector for a in driver.activated] == ["#go", "#go"]
    assert len(healthy.raw_steps) == 1


def test_delta32_unobserved_candidate_count_is_not_zero(tmp_path: Path) -> None:
    """binder 미주입(미관측)은 관측된 0건과 **다른 값**이다 — `None` ≠ `0`."""
    result = _runner(tmp_path).run(
        _contract(), driver=_ScriptedDriver(), task_id="W5L-N", run_id="w5l-n"
    )
    assert result.task_candidate_count is None
    # `Δ43`/`R37` 로 다시 좁힘 — 사유가 붙되 **후보 부재가 아니다**. 이 테스트의 주장은
    # `None`(미관측) ≠ `0`(관측된 0건) 이고 그것은 그대로 참이다.
    assert result.terminal_reason != "NO_TASK_CANDIDATE_FOUND"


def test_delta32_no_task_candidate_found_is_distinct_from_its_neighbours() -> None:
    """`NO_TASK_CANDIDATE_FOUND` 는 `AMBIGUOUS_MULTIPLE_CANDIDATES`(다수) ·
    `TASK_SURFACE_ABSENT`(surface 부재) 와 **다른 사건**이다."""
    zero = classify_terminal(TerminalSignals(evidence_complete=True, task_candidate_count=0))
    many = classify_terminal(
        TerminalSignals(evidence_complete=True, ambiguous_multiple_candidates=True)
    )
    absent = classify_terminal(
        TerminalSignals(
            evidence_complete=True,
            public_web_task_observable=False,
            public_mobile_web_present=True,
        )
    )
    reasons = {zero.terminal_reason, many.terminal_reason, absent.terminal_reason}
    assert len(reasons) == 3, reasons


# ══════════════════════════════════════════════════════════════════════════
# 5. Δ32-R29 — 0 은 관측이 아니라 주장이다
# ══════════════════════════════════════════════════════════════════════════
def test_r29_reached_with_zero_bound_candidates_is_rejected_by_the_schema() -> None:
    """`[Δ32-R29 인용]` *"**후보 0건은 어떤 경우에도 `endpoint_status=REACHED` 를 낼 수
    없다.** 스키마가 그 조합을 거부한다."*"""
    with pytest.raises(ZeroActivationClaimError):
        validate_reached_requires_binding(EndpointStatus.REACHED, task_candidate_count=0)
    with pytest.raises(ZeroActivationClaimError):
        classify_terminal(
            TerminalSignals(evidence_complete=True, endpoint_reached=True, task_candidate_count=0)
        )


def test_r29_positive_control_one_bound_candidate_allows_reached() -> None:
    """**음성대조** — 후보가 1건 이상이면 `REACHED` 가 통과한다. 거부가 전면적이지 않다."""
    validate_reached_requires_binding(EndpointStatus.REACHED, task_candidate_count=1)
    got = classify_terminal(
        TerminalSignals(evidence_complete=True, endpoint_reached=True, task_candidate_count=1)
    )
    assert got.endpoint_status is EndpointStatus.REACHED
    assert got.resolution is TerminalResolution.NOT_TERMINAL_ENDPOINT_REACHED


def test_r29_unobserved_count_is_not_rejected() -> None:
    """미관측(`None`)을 `0` 으로 접지 않는다 — 거부 대상은 **관측된 0** 뿐이다."""
    validate_reached_requires_binding(EndpointStatus.REACHED, task_candidate_count=None)


def test_r29_is_enforced_by_the_runner_not_only_by_the_schema(tmp_path: Path) -> None:
    """runner 도 같은 검사를 통과해야 한다 — classifier 가 REACHED 를 우겨도 막힌다."""
    r = _runner(tmp_path, binder=_EmptyBinder(), terminal=_FixedTerminal("REACHED"))
    with pytest.raises(ZeroActivationClaimError):
        r.run(_contract(), driver=_ScriptedDriver(), task_id="W5L-R29", run_id="w5l-r29")


# ══════════════════════════════════════════════════════════════════════════
# 6. raw 포착 순서 — binding 보다 **앞**이라 되짚을 수 있다
# ══════════════════════════════════════════════════════════════════════════
def test_surface_evidence_is_captured_before_candidate_binding(tmp_path: Path) -> None:
    """`D-V3-FINDING-003` 의 교훈 — binder 가 후보를 떨어뜨려도 raw 가 남아야 한다.

    `V3Runner.run` 의 단계 순서는 `3. L0/Scroll Surface Capture` → `4. Candidate
    Binding` 이다. 계약 위반으로 멈춘 뒤에도 그 시점까지 디스크에 쓴 surface payload
    가 **그대로 남는다** — 예외를 던지느라 이미 잡은 evidence 를 버리지 않는다.
    """
    root = tmp_path / "evidence"
    r = _runner(tmp_path, binder=_NaiveBinder())
    with pytest.raises(CandidateBindingContractError):
        r.run(_contract(), driver=_ScriptedDriver(), task_id="W5L-RAW", run_id="w5l-raw")

    written = sorted(str(f.relative_to(root)) for f in root.rglob("*") if f.is_file())
    assert written, "계약 위반으로 멈췄는데 raw evidence 가 하나도 남지 않았다"
    assert any("s000" in name for name in written), (
        f"binding 앞에서 잡은 S0 surface payload 가 없다: {written}"
    )
    assert any(name.endswith("dom.html") for name in written), written


def test_surface_evidence_also_survives_the_observed_zero_branch(tmp_path: Path) -> None:
    """(b) 갈래에서도 raw 가 남는다 — 두 갈래 모두 되짚을 근거를 갖는다."""
    root = tmp_path / "evidence"
    _runner(tmp_path, binder=_EmptyBinder()).run(
        _contract(), driver=_ScriptedDriver(), task_id="W5L-RAW2", run_id="w5l-raw2"
    )
    written = sorted(str(f.relative_to(root)) for f in root.rglob("*") if f.is_file())
    assert any("s000" in name for name in written), written


# ══════════════════════════════════════════════════════════════════════════
# 7. 소비자 쪽 방어 — 전건 탈락이 조용한 `None` 이 되지 않는다
# ══════════════════════════════════════════════════════════════════════════
def test_propose_next_raises_instead_of_silently_dropping_non_mapping_candidates() -> None:
    """예전 코드는 `isinstance(c, Mapping)` 으로 **조용히** 걸러 `None` 을 반환했다."""
    strategy = MinPathScoutStrategy()
    with pytest.raises(CandidateBindingContractError):
        strategy.propose_next(_contract(), [], [object()], ())


def test_propose_next_returns_none_for_a_genuinely_empty_candidate_list() -> None:
    """음성대조 — 후보가 **원래 0건**이면 예외가 아니라 `None` 이다(탐색할 것이 없었다).

    두 경우가 같은 출력이면 형태 결함과 관측을 가를 수 없다.
    """
    assert MinPathScoutStrategy().propose_next(_contract(), [], [], ()) is None


def test_task_candidate_satisfies_the_declared_binder_contract() -> None:
    """`Δ32` 시정 — `discover_task_candidates` 산출물이 `Sequence[Mapping]` 을 만족한다.

    dataclass 접근(`c.selector`)도 그대로 살아 있다 — 어느 소비자도 잃는 것이 없다.
    """
    produced = discovery.discover_task_candidates(_NaiveBinder.PROBE, _contract())
    assert produced
    for candidate in produced:
        assert isinstance(candidate, Mapping)
        assert isinstance(candidate, discovery.TaskCandidate)
        assert candidate.get("selector") == candidate.selector
        # probe 원본의 비-dataclass 신호도 view 에서 읽힌다.
        assert "dom_order" in candidate


def test_terminal_module_declares_fifteen_reasons() -> None:
    """모듈 문서와 코드가 같은 수를 말한다 — 문서만 13 으로 남지 않았다."""
    doc = terminal_module.__doc__ or ""
    assert "15값" in doc
    assert len(set(TerminalReason)) == 15
