"""W5G — v3 B-Safety lane 회귀 (`v3_runner/safety.py`).

## 이 파일의 규율 — 대조군 없는 "0건"을 만들지 않는다

이 프로젝트는 무결과를 통과로 보고해 여러 번 틀렸다(`verification-requires-control-group`).
그래서 여기의 **모든** 차단 테스트는 짝이 되는 양성 대조를 함께 낸다:

- 금지 행위가 막힌다  → **같은 구조에서 안전한 행위는 실제로 수행됐다**(spy 카운트 > 0).
  이게 없으면 "전부 막는 코드"와 구분되지 않는다.
- exactly-once 억제  → **억제가 없는 경로에서는 같은 launch_fn 이 2회 호출된다.**
  락 디렉터리 존재로 PASS 판정하지 않는다 — launch 횟수를 직접 센다.
- auth              → **login control 이 있지만 task path 가 그것을 지나지 않는**
  구성에서 진행이 중단되지 않는다(`G1-b` 재발 방지).

## 네트워크

없다. `RecordingPage` 는 spy 이고 실사이트/실브라우저에 붙지 않는다.
"""

from __future__ import annotations

import json
import multiprocessing
import os
import re
import sys
import time
from pathlib import Path
from typing import Any

import pytest

REPO = Path(__file__).resolve().parents[1]
RESEARCH = REPO / "research" / "landing_accessibility"
SRC = str(RESEARCH / "src")
if SRC not in sys.path:
    sys.path.insert(0, SRC)

from landing_accessibility.e001_runner.guard import (  # noqa: E402
    AccountActionBlockedError,
    CandidateActionState,
)
from landing_accessibility.e001_runner.retry import _NON_RETRYABLE_EXCEPTIONS  # noqa: E402
from landing_accessibility.v3_runner.safety import (  # noqa: E402
    SAFETY_STOP,
    UNIVERSAL_FORBIDDEN_ACTIONS,
    ActivationSafetyGuard,
    AuthBoundary,
    FixtureCase,
    FixtureMatrixMissingError,
    ForbiddenAction,
    LockState,
    RecordingPage,
    SafetyStop,
    V3TargetLaunchGuard,
    classify_auth_boundary,
    credential_actuation_counts,
    default_v3_fixture_root,
    load_fixture_matrix,
    preflight_reachable_assessment,
    resolve_forbidden_actions,
    run_fixture_safety_regression,
    task_path_requires_auth_stop,
)

# ══════════════════════════════════════════════════════════════════════════
# 공통 fixture 데이터 — 하나의 "F2 상품 상세" 화면을 모사한다.
# 안전 후보(검색/카테고리)와 금지 후보(장바구니/구매)가 **같은 목록에** 있다.
# ══════════════════════════════════════════════════════════════════════════
SAFE_SEARCH = {
    "selector": "#gnb-search",
    "accessible_name": "검색",
    "visible_text": "검색",
    "hittable": True,
    "enabled": True,
    "dom_order": 1,
}
SAFE_CATEGORY = {
    "selector": "#cat-water",
    "accessible_name": "생수",
    "visible_text": "생수",
    "hittable": True,
    "enabled": True,
    "dom_order": 2,
}
CART_BUTTON = {
    "selector": "#add-cart",
    "accessible_name": "장바구니 담기",
    "visible_text": "장바구니 담기",
    "hittable": True,
    "enabled": True,
    "dom_order": 3,
}
BUY_BUTTON = {
    "selector": "#buy-now",
    "accessible_name": "바로 구매",
    "visible_text": "바로 구매",
    "hittable": True,
    "enabled": True,
    "dom_order": 4,
}
PASSWORD_FIELD = {
    "selector": "#login-password",
    "input_type": "password",
    "autocomplete": "current-password",
    "hittable": True,
    "enabled": True,
    "dom_order": 5,
    "form_id": "loginForm",
}
LOGIN_LINK = {
    "selector": "#gnb-login",
    "accessible_name": "로그인",
    "visible_text": "로그인",
    "hittable": True,
    "enabled": True,
    "dom_order": 6,
}

#: 문구는 `LOGIN_LINK` 와 **똑같다**. 구조(같은 form 의 submit)만 다르다 —
#: 이 둘을 어휘로 가르려는 시도가 `G1-b` 였다.
LOGIN_SUBMIT_BUTTON = {
    "selector": "#login-submit",
    "accessible_name": "로그인",
    "visible_text": "로그인",
    "input_type": "submit",
    "form_id": "loginForm",
    "hittable": True,
    "enabled": True,
    "dom_order": 7,
}


class _ContractStub:
    """W5A `contracts.TaskContract` 가 아직 없다 — Protocol 경계에 맞춘 fake."""

    def __init__(
        self,
        *,
        task_id: str = "task_f2_01",
        family_id: str = "F2",
        forbidden_actions: Any = (),
        fixed_fixture: Any = "검색어=생수",
    ) -> None:
        self.task_id = task_id
        self.family_id = family_id
        self.forbidden_actions = forbidden_actions
        self.fixed_fixture = fixed_fixture


def _f2_guard(**kw: Any) -> ActivationSafetyGuard:
    return ActivationSafetyGuard(_ContractStub(**kw))


class _RecordingSink:
    def __init__(self) -> None:
        self.emitted: list[tuple[str, dict[str, Any]]] = []

    def emit(self, terminal: str, payload: Any) -> None:
        self.emitted.append((terminal, dict(payload)))


# ══════════════════════════════════════════════════════════════════════════
# 1. forbidden action 강제 — **활성화 시점**
# ══════════════════════════════════════════════════════════════════════════


def test_forbidden_click_blocked_while_safe_click_in_same_flow_actually_happens():
    """차단(음성)과 수행(양성)을 **한 테스트 안에서** 같이 낸다.

    이 짝이 없으면 "장바구니 클릭 0회"는 "아무것도 못 누르는 코드"와 구분되지 않는다.
    """
    guard = _f2_guard()
    page = RecordingPage()
    guarded = guard.guard_page(
        page,
        resolve=lambda s: {
            c["selector"]: c for c in (SAFE_SEARCH, SAFE_CATEGORY, CART_BUTTON, BUY_BUTTON)
        }.get(s),
    )

    # 양성 대조 — 안전한 활성화는 실제로 페이지까지 도달한다.
    guarded.click(SAFE_CATEGORY["selector"])
    assert page.count("click", selector_contains="cat-water") == 1, (
        "안전한 클릭이 수행되지 않았다 — 이 코드는 '전부 막는 코드'다"
    )

    # 음성 — 금지 활성화는 페이지에 닿지 않는다.
    with pytest.raises(SafetyStop) as exc:
        guarded.click(CART_BUTTON["selector"])
    assert exc.value.action is ForbiddenAction.ADD_TO_CART
    assert page.count("click", selector_contains="add-cart") == 0
    assert len(page.calls) == 1, f"금지 클릭이 페이지에 도달했다: {page.calls}"


def test_forbidden_control_existence_is_observed_and_only_activation_is_blocked():
    """`D-R0-06` / `00_SSOT §6` — 존재와 geometry 는 관측 가능, 활성화만 금지."""
    guard = _f2_guard()
    obs = guard.observe(CART_BUTTON)  # 예외 없음 — 관측은 막지 않는다

    assert obs.forbidden_action is ForbiddenAction.ADD_TO_CART
    assert obs.candidate_state == CandidateActionState.SAFE.value or obs.candidate_state
    evidence = guard.evidence()
    assert any(
        o["selector"] == CART_BUTTON["selector"] for o in evidence["forbidden_controls_observed"]
    ), "금지 control 의 존재가 evidence 에 남지 않았다"
    assert evidence["violations"] == [], "관측만 했는데 위반으로 기록됐다"

    # 같은 control 의 **활성화**만 막힌다.
    with pytest.raises(SafetyStop):
        guard.authorize(CART_BUTTON)
    assert guard.violations and guard.violations[0]["action"] == "ADD_TO_CART"


def test_enforcement_is_at_activation_not_at_candidate_selection():
    """금지 후보가 목록에 **있다는 이유로** 탐색이 죽지 않는다.

    e001 가드의 target-level kill(`D-R0-01` 이 폐기하라고 한 그것)이 v3 에서 되살아나지
    않았음을 증명한다: 금지 후보를 포함한 목록 전체를 관측한 뒤에도 안전 활성화가
    계속 수행된다.
    """
    guard = _f2_guard()
    page = RecordingPage()
    catalogue = {c["selector"]: c for c in (SAFE_SEARCH, SAFE_CATEGORY, CART_BUTTON, BUY_BUTTON)}
    guarded = guard.guard_page(page, resolve=catalogue.get)

    guard.observe_all([SAFE_SEARCH, SAFE_CATEGORY, CART_BUTTON, BUY_BUTTON])
    guarded.click(SAFE_SEARCH["selector"])
    guarded.click(SAFE_CATEGORY["selector"])

    assert len(page.calls) == 2, (
        f"금지 후보가 목록에 있다는 이유로 안전 경로가 죽었다 (target-level kill 재발): {page.calls}"
    )
    with pytest.raises(SafetyStop):
        guarded.click(BUY_BUTTON["selector"])
    assert len(page.calls) == 2


def test_observed_forbidden_selector_is_denied_even_without_resolver():
    """resolver 가 후보를 되돌려주지 못해도, `observe()` 로 채워진 deny-list 가 막는다."""
    guard = _f2_guard()
    page = RecordingPage()
    guard.observe(CART_BUTTON)
    guarded = guard.guard_page(page)  # resolver 없음

    with pytest.raises(SafetyStop):
        guarded.click(CART_BUTTON["selector"])
    assert page.calls == []

    # 양성 대조 — 관측된 적 없는 안전 selector 는 통과한다.
    guarded.click("#some-nav-link")
    assert page.count("click", selector_contains="some-nav-link") == 1


def test_selector_text_signal_blocks_even_when_unresolved():
    guard = _f2_guard()
    page = RecordingPage()
    guarded = guard.guard_page(page)

    with pytest.raises(SafetyStop):
        guarded.click('button:has-text("결제하기")')
    assert page.calls == []
    guarded.click('a:has-text("공지사항")')  # 양성 대조
    assert len(page.calls) == 1


# ── 계약 결합 ─────────────────────────────────────────────────────────────


def test_contract_can_only_add_forbidden_actions_never_subtract():
    """계약이 빈 금지 목록을 선언해도 전역 금지는 유지된다."""
    empty = resolve_forbidden_actions(_ContractStub(forbidden_actions=()))
    assert empty.actions >= UNIVERSAL_FORBIDDEN_ACTIONS
    assert ForbiddenAction.CREDENTIAL_INPUT in empty.actions
    assert ForbiddenAction.CAPTCHA_SOLVE in empty.actions

    # 계약 없이(None) 만들어도 마찬가지.
    assert resolve_forbidden_actions(None).actions >= UNIVERSAL_FORBIDDEN_ACTIONS

    # 양성 대조 — 계약이 선언한 것은 `contract_declared` 로 구분되어 남는다.
    declared = resolve_forbidden_actions(_ContractStub(forbidden_actions=["ADD_TO_CART"]))
    assert declared.contract_declared == frozenset({ForbiddenAction.ADD_TO_CART})
    assert empty.contract_declared == frozenset()


def test_contract_forbidden_set_accepts_both_schema_field_names():
    """`02 §2` — `dim_task_family.forbidden_actions` / `dim_task_contract.forbidden_action_set`."""
    a = resolve_forbidden_actions({"forbidden_actions": ["SEAT_SELECT"]})
    b = resolve_forbidden_actions({"forbidden_action_set": ["SEAT_SELECT"]})
    assert a.contract_declared == b.contract_declared == frozenset({ForbiddenAction.SEAT_SELECT})


def test_unrecognized_contract_tokens_are_surfaced_not_dropped():
    """모르는 토큰을 조용히 버리면 '위반 0건'이 무의미해진다."""
    resolved = resolve_forbidden_actions(
        {"forbidden_actions": ["ADD_TO_CART", "무언가_새로운_금지"]}
    )
    assert "무언가_새로운_금지" in resolved.unrecognized
    assert ForbiddenAction.ADD_TO_CART in resolved.contract_declared  # 양성 대조


def test_family_specific_contracts_differ_but_share_the_universal_floor():
    """`01 §2` — F1 과 F2 는 다른 금지 집합을 갖지만 전역 금지는 공통이다."""
    f1 = resolve_forbidden_actions(
        {"family_id": "F1", "forbidden_actions": ["CREDENTIAL_INPUT", "FUNDS_TRANSFER"]}
    )
    f2 = resolve_forbidden_actions(
        {"family_id": "F2", "forbidden_actions": ["ADD_TO_CART", "ORDER_PLACE", "PAYMENT"]}
    )
    assert f1.contract_declared != f2.contract_declared
    assert f1.actions >= UNIVERSAL_FORBIDDEN_ACTIONS
    assert f2.actions >= UNIVERSAL_FORBIDDEN_ACTIONS


# ── v3 고유 공백 보충 ─────────────────────────────────────────────────────


def test_seat_select_is_blocked_f5_gap_not_covered_by_e001_guard():
    guard = ActivationSafetyGuard({"family_id": "F5", "fixed_fixture": "서울;부산"})
    page = RecordingPage()
    seat = {"selector": "#seat", "visible_text": "좌석 선택", "hittable": True, "enabled": True}
    safe = {"selector": "#search-train", "visible_text": "조회", "hittable": True, "enabled": True}
    guarded = guard.guard_page(page, resolve={"#seat": seat, "#search-train": safe}.get)

    with pytest.raises(SafetyStop) as exc:
        guarded.click("#seat")
    assert exc.value.action is ForbiddenAction.SEAT_SELECT
    guarded.click("#search-train")  # 양성 대조
    assert page.count("click", selector_contains="search-train") == 1


def test_external_app_launch_blocked_by_scheme_and_by_text():
    guard = ActivationSafetyGuard({"family_id": "F4"})
    page = RecordingPage()
    controls = {
        "#app": {"selector": "#app", "href": "intent://open#Intent;scheme=hospital;end"},
        "#call": {"selector": "#call", "visible_text": "전화 걸기"},
        "#web": {"selector": "#web", "href": "https://example.org/list", "visible_text": "목록"},
    }
    guarded = guard.guard_page(page, resolve=controls.get)

    for selector, expected in (("#app", "scheme"), ("#call", "text")):
        with pytest.raises(SafetyStop) as exc:
            guarded.click(selector)
        assert exc.value.action is ForbiddenAction.EXTERNAL_APP_LAUNCH, expected

    guarded.click("#web")  # 양성 대조 — 평범한 https 링크는 눌린다
    assert page.count("click", selector_contains="web") == 1


def test_captcha_control_is_observed_and_interaction_blocked_no_solving_logic():
    """CAPTCHA: 존재 관측 + 상호작용 차단까지가 전부다. 해결/우회 경로는 없다."""
    guard = ActivationSafetyGuard(None)
    page = RecordingPage()
    captcha = {
        "selector": "#recaptcha-anchor",
        "visible_text": "reCAPTCHA",
        "hittable": True,
        "enabled": True,
    }
    guarded = guard.guard_page(page, resolve={"#recaptcha-anchor": captcha}.get)

    obs = guard.observe(captcha)
    assert obs.forbidden_action is ForbiddenAction.CAPTCHA_SOLVE  # 존재는 관측된다
    with pytest.raises(SafetyStop):
        guarded.click("#recaptcha-anchor")
    assert page.calls == []

    # 양성 대조 — CAPTCHA 가 있는 화면에서도 관계없는 안전 링크는 눌린다.
    guarded.click("#footer-help")
    assert len(page.calls) == 1

    # 이 모듈에 해결/우회를 시사하는 공개 API 가 없다는 것도 함께 못박는다.
    from landing_accessibility.v3_runner import safety as safety_module

    suspicious = re.compile(
        r"(captcha.*(solve|bypass|answer)|(solve|bypass|answer).*captcha)", re.I
    )
    assert not [n for n in dir(safety_module) if not n.startswith("_") and suspicious.search(n)]


# ── 텍스트 입력 강제 ──────────────────────────────────────────────────────


def test_fill_allows_only_frozen_fixture_value():
    """`01 §2` 의 `fixed_fixture` 만 입력 가능 — 어휘가 아니라 구조로 강제한다."""
    guard = _f2_guard(fixed_fixture="검색어=생수")
    page = RecordingPage()
    guarded = guard.guard_page(page, resolve={"#gnb-search": SAFE_SEARCH}.get)

    guarded.fill("#gnb-search", "생수")  # 양성 대조 — 고정 fixture 값은 입력된다
    assert page.count("fill", selector_contains="gnb-search") == 1

    with pytest.raises(SafetyStop) as exc:
        guarded.fill("#gnb-search", "hunter2")
    assert exc.value.action is ForbiddenAction.PERSONAL_DATA_INPUT
    assert page.count("fill") == 1


def test_fill_into_credential_field_is_blocked_even_with_allowed_value():
    guard = _f2_guard(fixed_fixture="생수")
    page = RecordingPage()
    guarded = guard.guard_page(page, resolve={"#login-password": PASSWORD_FIELD}.get)

    with pytest.raises(SafetyStop) as exc:
        guarded.fill("#login-password", "생수")
    assert exc.value.action is ForbiddenAction.CREDENTIAL_INPUT
    assert page.calls == []


def test_press_enter_is_allowed_on_safe_field_but_not_on_credential_field():
    guard = _f2_guard(fixed_fixture="생수")
    page = RecordingPage()
    guarded = guard.guard_page(
        page, resolve={"#gnb-search": SAFE_SEARCH, "#login-password": PASSWORD_FIELD}.get
    )

    guarded.press("#gnb-search", "Enter")  # 양성 대조
    assert page.count("press") == 1
    with pytest.raises(SafetyStop):
        guarded.press("#login-password", "Enter")
    assert page.count("press") == 1


def test_set_input_files_is_blocked():
    guard = _f2_guard()
    page = RecordingPage()
    guarded = guard.guard_page(page)
    with pytest.raises(SafetyStop):
        guarded.set_input_files("#upload", "/etc/passwd")
    assert page.calls == []


# ── terminal / 재시도 ────────────────────────────────────────────────────


def test_safety_stop_emits_terminal_to_sink_and_is_non_retryable():
    sink = _RecordingSink()
    guard = ActivationSafetyGuard(_ContractStub(), terminal_sink=sink)
    with pytest.raises(SafetyStop):
        guard.authorize(CART_BUTTON)

    assert sink.emitted and sink.emitted[0][0] == SAFETY_STOP
    assert sink.emitted[0][1]["action"] == "ADD_TO_CART"
    assert issubclass(SafetyStop, AccountActionBlockedError)
    assert any(issubclass(SafetyStop, t) for t in _NON_RETRYABLE_EXCEPTIONS), (
        "SafetyStop 이 재시도 대상이면 위반을 다시 시도하게 된다"
    )

    # 양성 대조 — 안전 후보에는 terminal 이 발화하지 않는다.
    sink2 = _RecordingSink()
    guard2 = ActivationSafetyGuard(_ContractStub(), terminal_sink=sink2)
    guard2.authorize(SAFE_CATEGORY)
    assert sink2.emitted == []


def test_preflight_delegates_to_existing_guard_and_is_not_reimplemented():
    """`assess_reachable_candidates` 재사용 확인 — 두 판정이 갈리지 않아야 한다."""
    from landing_accessibility.e001_runner import guard as e001_guard

    candidates = [CART_BUTTON, BUY_BUTTON]
    mine = preflight_reachable_assessment(candidates)
    theirs = e001_guard.assess_reachable_candidates([dict(c) for c in candidates])
    assert mine.as_dict() == theirs.as_dict()
    assert mine.blocking is not None  # 안전한 대안이 하나도 없다

    # 양성 대조 — 안전한 대안이 섞이면 막지 않는다.
    mixed = preflight_reachable_assessment([CART_BUTTON, SAFE_CATEGORY])
    assert mixed.blocking is None


# ══════════════════════════════════════════════════════════════════════════
# 2. auth 경계 — `G1-b` 재발 방지
# ══════════════════════════════════════════════════════════════════════════


def test_login_control_present_but_task_path_does_not_pass_it_does_not_stop():
    """`D3-09` / `G1-b` — landing 에 로그인이 **존재**한다는 이유로 중단하지 않는다."""
    decision = classify_auth_boundary(LOGIN_LINK, on_task_path=False, auth_unavoidable=False)
    assert decision.boundary is AuthBoundary.OBSERVE_ONLY
    assert decision.should_stop is False

    # login control 을 여러 개 관측해도 결론이 바뀌지 않는다 — 개수를 세지 않는다.
    guard = _f2_guard()
    observations = guard.observe_all([LOGIN_LINK, LOGIN_LINK, LOGIN_LINK, SAFE_CATEGORY])
    assert task_path_requires_auth_stop(observations, auth_unavoidable_on_task_path=False) is False

    # 그리고 실제로 진행이 계속된다(양성 대조: 흐름이 죽지 않았다).
    page = RecordingPage()
    guarded = guard.guard_page(
        page, resolve={"#gnb-login": LOGIN_LINK, "#cat-water": SAFE_CATEGORY}.get
    )
    guarded.click("#gnb-login")
    guarded.click("#cat-water")
    assert len(page.calls) == 2, "로그인 링크 존재만으로 task path 가 중단됐다 (G1-b 재발)"


def test_auth_gate_terminal_only_when_auth_is_unavoidable_on_task_path():
    """양성 대조 축 — 진짜 gate 는 실제로 terminal 을 낸다."""
    gate = classify_auth_boundary(LOGIN_LINK, on_task_path=True, auth_unavoidable=True)
    assert gate.boundary is AuthBoundary.AUTH_GATE_TERMINAL
    assert gate.should_stop is True
    assert task_path_requires_auth_stop([], auth_unavoidable_on_task_path=True) is True

    # task path 위이긴 하나 인증이 불가피하지 않으면 여전히 진행한다.
    partial = classify_auth_boundary(LOGIN_LINK, on_task_path=True, auth_unavoidable=False)
    assert partial.boundary is AuthBoundary.OBSERVE_ONLY


def test_auth_gate_terminal_is_not_a_safety_violation():
    gate = classify_auth_boundary(LOGIN_LINK, on_task_path=True, auth_unavoidable=True)
    assert gate.boundary is not AuthBoundary.SAFETY_STOP
    assert gate.action is None


def test_reaching_login_form_is_observation_but_input_and_submit_are_forbidden():
    """로그인 폼 도달 자체는 gate observation 이지 금지가 아니라는 것을 세 갈래로 못박는다."""
    guard = _f2_guard()
    page = RecordingPage()
    submit = {
        "selector": "#login-submit",
        "visible_text": "로그인",
        "hittable": True,
        "enabled": True,
    }
    resolve = {
        "#login-password": PASSWORD_FIELD,
        "#login-submit": submit,
        "#gnb-login": LOGIN_LINK,
    }.get
    guarded = guard.guard_page(page, resolve=resolve)

    # (1) 폼에 도달하는 것(로그인 링크 클릭)은 허용된다 — 양성 대조.
    guarded.click("#gnb-login")
    assert len(page.calls) == 1

    # (2) 폼을 관측하는 것도 허용된다 — 예외 없음, evidence 로 남는다.
    obs = guard.observe(PASSWORD_FIELD)
    assert obs.forbidden_action is ForbiddenAction.CREDENTIAL_INPUT

    # (3) 자격정보 입력은 금지다.
    with pytest.raises(SafetyStop):
        guarded.fill("#login-password", "anything")
    assert page.count("fill") == 0

    boundary = classify_auth_boundary(PASSWORD_FIELD, on_task_path=True, auth_unavoidable=True)
    assert boundary.boundary is AuthBoundary.SAFETY_STOP
    assert boundary.action is ForbiddenAction.CREDENTIAL_INPUT


def test_identical_login_text_link_is_allowed_but_form_submit_is_blocked():
    """이 lane 에서 가장 날카로운 경계 — **문구가 같다.**

    `LOGIN_LINK` 와 `LOGIN_SUBMIT_BUTTON` 은 accessible_name/visible_text 가 둘 다
    "로그인" 이다. 어휘로는 갈 수 없다. 갈리는 것은 구조뿐이다: 후자는
    `input[type=submit]` 이고 자격정보 필드와 같은 `form_id` 를 갖는다.

    - 어휘로 둘 다 막으면 → `G1-b` 재발(로그인 링크 존재만으로 진행 중단).
    - 어휘로 둘 다 허용하면 → login submit 금지 위반.
    """
    guard = _f2_guard()
    page = RecordingPage()
    resolve = {
        "#gnb-login": LOGIN_LINK,
        "#login-submit": LOGIN_SUBMIT_BUTTON,
        "#login-password": PASSWORD_FIELD,
    }.get
    guarded = guard.guard_page(page, resolve=resolve)

    # 양성 — 로그인 폼으로 가는 링크는 눌린다.
    guarded.click("#gnb-login")
    assert page.count("click", selector_contains="gnb-login") == 1

    # 음성 — 같은 문구의 제출 버튼은 막힌다.
    with pytest.raises(SafetyStop) as exc:
        guarded.click("#login-submit")
    assert exc.value.action is ForbiddenAction.LOGIN_SUBMIT
    assert page.count("click", selector_contains="login-submit") == 0


def test_login_button_becomes_submit_once_credential_field_in_same_form_is_observed():
    """구조 신호가 후보에 실려 있지 않아도, 같은 form 의 자격정보 필드를 **관측**하면
    그 form 의 로그인 버튼은 제출로 재판정된다(상태 기반 보강)."""
    bare_submit = {
        "selector": "#form-login-btn",
        "visible_text": "로그인",
        "form_id": "loginForm",
        "hittable": True,
        "enabled": True,
        "dom_order": 9,
    }
    # (a) 자격정보 필드를 관측하기 **전** — 제출 신호가 없으므로 막지 않는다(과탐 금지).
    fresh = _f2_guard()
    assert fresh.evaluate(bare_submit).allowed is True

    # (b) 같은 form 의 password 필드를 관측한 **뒤** — 제출로 재판정되어 막힌다.
    fresh.observe(PASSWORD_FIELD)
    decision = fresh.evaluate(bare_submit)
    assert decision.allowed is False
    assert decision.action is ForbiddenAction.LOGIN_SUBMIT

    # 양성 대조 — 다른 form 의 로그인 버튼은 여전히 허용된다.
    other = dict(bare_submit, selector="#other-login", form_id="searchForm")
    assert fresh.evaluate(other).allowed is True


def test_otp_field_interaction_is_safety_stop_not_auth_gate():
    otp = {"selector": "#otp", "visible_text": "인증번호", "hittable": True, "enabled": True}
    decision = classify_auth_boundary(otp, on_task_path=True, auth_unavoidable=True)
    assert decision.boundary is AuthBoundary.SAFETY_STOP
    assert decision.action is ForbiddenAction.OTP_ENTRY


# ══════════════════════════════════════════════════════════════════════════
# 3. exactly-once — launch 횟수를 직접 센다
# ══════════════════════════════════════════════════════════════════════════


def _guard_for(tmp_path: Path, *, run_id: str = "V3-ROUND-1") -> V3TargetLaunchGuard:
    return V3TargetLaunchGuard(
        ticket_id="T-B-W5G",
        run_id=run_id,
        collector_sha="csha",
        lock_dir=tmp_path / "locks",
    )


def test_second_request_launches_zero_times_and_control_path_launches_twice(tmp_path):
    """억제본 1회 + **양성 대조로 억제 없는 경로 2회**를 같이 낸다."""
    calls: list[str] = []

    def launch(target_id: str) -> str:
        calls.append(target_id)
        return "launched"

    guard = _guard_for(tmp_path)
    first = guard.launch("F2-03", launch)
    assert first.launched is True
    assert len(calls) == 1

    second = guard.launch("F2-03", launch)
    assert second.launched is False
    assert "DUPLICATE_SUPPRESSED" in (second.reason or "")
    assert len(calls) == 1, f"2회차에서 launch 가 다시 일어났다: {calls}"

    # 양성 대조 — 억제가 없는 경로(같은 launch_fn 직접 호출)는 2회 호출된다.
    control: list[str] = []

    def control_launch(target_id: str) -> str:
        control.append(target_id)
        return "launched"

    control_launch("F2-03")
    control_launch("F2-03")
    assert len(control) == 2, "양성 대조가 성립하지 않는다 — 이 테스트는 아무것도 증명 못 한다"


def test_launch_fn_is_never_called_when_suppressed(tmp_path):
    """억제는 **실제 launch 이전**이다 — 사후 차단이 아니다."""
    guard = _guard_for(tmp_path)
    guard.launch("F1-01", lambda t: None)

    def must_not_run(target_id: str) -> None:  # pragma: no cover - 호출되면 실패
        raise AssertionError("억제됐어야 할 요청에서 launch_fn 이 호출됐다")

    outcome = guard.launch("F1-01", must_not_run)
    assert outcome.launched is False


def test_lock_is_not_deleted_and_state_is_recorded(tmp_path):
    guard = _guard_for(tmp_path)
    outcome = guard.launch("F3-05", lambda t: None)
    assert outcome.lock_path.is_file()
    assert guard.state_of("F3-05") == LockState.DONE

    guard.launch("F3-05", lambda t: None)
    assert outcome.lock_path.is_file(), "lock 을 삭제하면 다음 프로세스가 부재를 다시 본다"


def test_new_run_id_is_a_new_run_and_does_not_overwrite_prior_evidence(tmp_path):
    """같은 service-task 재수집은 **새 run id** 이고 기존 lock/evidence 를 덮지 않는다."""
    calls: list[str] = []
    r1 = _guard_for(tmp_path, run_id="V3-ROUND-1")
    r2 = _guard_for(tmp_path, run_id="V3-ROUND-2")

    a = r1.launch("F4-02", lambda t: calls.append("r1"))
    b = r2.launch("F4-02", lambda t: calls.append("r2"))

    assert a.launched is True and b.launched is True
    assert len(calls) == 2
    assert a.lock_path != b.lock_path, "run 이 다른데 같은 lock 파일을 덮어썼다"
    assert a.lock_path.is_file() and b.lock_path.is_file()
    assert a.idempotency_key != b.idempotency_key

    # 음성 대조 — 같은 run_id 안에서는 여전히 억제된다.
    assert r1.launch("F4-02", lambda t: calls.append("r1b")).launched is False
    assert len(calls) == 2


def test_missing_ticket_or_run_id_fails_closed_before_any_lock(tmp_path):
    for kwargs in ({"ticket_id": ""}, {"run_id": ""}):
        base: dict[str, Any] = {
            "ticket_id": "T",
            "run_id": "R",
            "collector_sha": "c",
            "lock_dir": tmp_path / "locks",
        }
        base.update(kwargs)
        with pytest.raises(ValueError):
            V3TargetLaunchGuard(**base)


def test_failed_launch_marks_retryable_and_reraises(tmp_path):
    guard = _guard_for(tmp_path)

    def boom(target_id: str) -> None:
        raise RuntimeError("collector 실패")

    with pytest.raises(RuntimeError):
        guard.launch("F5-01", boom)
    assert guard.state_of("F5-01") == LockState.FAILED_RETRYABLE

    # 양성 대조 — FAILED_RETRYABLE 은 재실행이 허용된다(영구 봉인이 아니다).
    calls: list[str] = []
    retry = guard.launch("F5-01", lambda t: calls.append(t))
    assert retry.launched is True and len(calls) == 1


# ── 진짜 OS 프로세스 2개 ─────────────────────────────────────────────────


def _same_target_worker(lock_dir: str, barrier: str, marker_dir: str, idx: int) -> None:
    sys.path.insert(0, SRC)
    from landing_accessibility.v3_runner.safety import V3TargetLaunchGuard

    guard = V3TargetLaunchGuard(
        ticket_id="T-B-W5G", run_id="V3-ROUND-1", collector_sha="csha", lock_dir=lock_dir
    )
    while not os.path.exists(barrier):
        time.sleep(0.001)
    guard.launch(
        "F2-03",
        lambda t: Path(marker_dir, f"launch_{idx}_{os.getpid()}.marker").write_text("1"),
    )


def _distinct_target_worker(lock_dir: str, barrier: str, marker_dir: str, idx: int) -> None:
    sys.path.insert(0, SRC)
    from landing_accessibility.v3_runner.safety import V3TargetLaunchGuard

    guard = V3TargetLaunchGuard(
        ticket_id="T-B-W5G", run_id="V3-ROUND-1", collector_sha="csha", lock_dir=lock_dir
    )
    while not os.path.exists(barrier):
        time.sleep(0.001)
    guard.launch(
        f"F2-0{idx}",
        lambda t: Path(marker_dir, f"launch_{idx}_{os.getpid()}.marker").write_text("1"),
    )


def _run_two_workers(tmp_path: Path, worker: Any) -> int:
    lock_dir = tmp_path / "locks"
    marker_dir = tmp_path / "markers"
    lock_dir.mkdir(parents=True)
    marker_dir.mkdir(parents=True)
    barrier = tmp_path / "GO"
    procs = [
        multiprocessing.Process(
            target=worker, args=(str(lock_dir), str(barrier), str(marker_dir), i)
        )
        for i in range(2)
    ]
    for p in procs:
        p.start()
    barrier.write_text("go")
    for p in procs:
        p.join(timeout=60)
    return len(list(marker_dir.iterdir()))


def test_two_workers_same_target_concurrently_launch_exactly_once(tmp_path):
    """Director 요구 — 같은 target 을 두 worker 가 **동시에** 실행하는 것을 막는다.

    락 디렉터리 존재로 PASS 처리하지 않는다. **launch 횟수(marker 파일 수)를 센다.**
    """
    assert _run_two_workers(tmp_path / "same", _same_target_worker) == 1


def test_two_workers_distinct_targets_both_launch_positive_control(tmp_path):
    """양성 대조 — 같은 하네스가 서로 다른 target 에는 2회 launch 를 낸다.

    이게 없으면 위 테스트의 '1'은 '프로세스가 아무것도 못 했다'와 구분되지 않는다.
    """
    assert _run_two_workers(tmp_path / "distinct", _distinct_target_worker) == 2


# ══════════════════════════════════════════════════════════════════════════
# 4. fixture safety 회귀 하네스
# ══════════════════════════════════════════════════════════════════════════

_SYNTHETIC_FIXTURES: dict[str, list[dict[str, Any]]] = {
    "login_first_auth": [LOGIN_LINK, PASSWORD_FIELD, LOGIN_SUBMIT_BUTTON, SAFE_CATEGORY],
    "cart_present_detail": [SAFE_SEARCH, CART_BUTTON, BUY_BUTTON, SAFE_CATEGORY],
    "captcha_active": [
        {
            "selector": "#recaptcha",
            "visible_text": "reCAPTCHA",
            "hittable": True,
            "enabled": True,
            "dom_order": 1,
        },
        SAFE_CATEGORY,
    ],
    "plain_landing": [SAFE_SEARCH, SAFE_CATEGORY],
}


def _write_matrix(root: Path, shape: str = "list") -> Path:
    root.mkdir(parents=True, exist_ok=True)
    rows = [
        {"fixture_id": fid, "file": f"{fid}.html", "discriminates": ["safety"]}
        for fid in _SYNTHETIC_FIXTURES
    ]
    for fid in _SYNTHETIC_FIXTURES:
        (root / f"{fid}.html").write_text("<html><body>fixture</body></html>", encoding="utf-8")
    if shape == "list":
        payload: Any = rows
    elif shape == "wrapped":
        payload = {"schema_version": "1", "fixtures": rows}
    else:
        payload = {r["fixture_id"]: {"file": r["file"]} for r in rows}
    path = root / "FIXTURE_DISCRIMINATION_MATRIX.json"
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    return path


def _safe_pipeline(case, guard, guarded, recorder) -> None:
    """계약을 지키는 파이프라인 — 후보 전건을 **관측**하고 안전한 것만 활성화한다."""
    for candidate in _SYNTHETIC_FIXTURES[case.fixture_id]:
        guard.observe(candidate)
    for candidate in _SYNTHETIC_FIXTURES[case.fixture_id]:
        decision = guard.evaluate(candidate)
        if decision.allowed and candidate.get("selector"):
            guarded.click(str(candidate["selector"]))


def _unsafe_pipeline(case, guard, guarded, recorder) -> None:
    """양성 대조용 — 가드를 우회해 후보 전건을 그냥 누르고 채운다.

    하네스가 위반을 **실제로 검출할 수 있는지** 확인하기 위한 것이다. 여기서
    `recorder`(가드 아래의 spy)를 직접 쓴다 — 실브라우저가 아니다.
    """
    for candidate in _SYNTHETIC_FIXTURES[case.fixture_id]:
        selector = str(candidate.get("selector") or "")
        if not selector:
            continue
        if candidate.get("input_type") == "password":
            recorder.fill(selector, "hunter2")
        else:
            recorder.click(selector)


def test_matrix_missing_raises_instead_of_reporting_zero_violations(tmp_path):
    """빈 결과와 통과가 같은 출력으로 나오지 않게 한다."""
    with pytest.raises(FixtureMatrixMissingError):
        load_fixture_matrix(tmp_path / "nonexistent")


def test_matrix_with_unparseable_schema_also_raises(tmp_path):
    root = tmp_path / "v3"
    root.mkdir()
    (root / "FIXTURE_DISCRIMINATION_MATRIX.json").write_text("{}", encoding="utf-8")
    with pytest.raises(FixtureMatrixMissingError):
        load_fixture_matrix(root)


@pytest.mark.parametrize("shape", ["list", "wrapped", "keyed"])
def test_harness_reads_matrix_not_a_hardcoded_file_list(tmp_path, shape):
    root = tmp_path / shape
    _write_matrix(root, shape)
    cases = load_fixture_matrix(root)
    assert {c.fixture_id for c in cases} == set(_SYNTHETIC_FIXTURES)
    assert all(c.exists for c in cases)


def test_full_matrix_sweep_yields_zero_forbidden_activation_with_positive_control(tmp_path):
    root = tmp_path / "v3"
    _write_matrix(root)
    cases = load_fixture_matrix(root)
    assert len(cases) == len(_SYNTHETIC_FIXTURES) > 0, "전건이 로드되지 않았다"

    safe_reports = run_fixture_safety_regression(cases, _safe_pipeline)
    assert all(r.error is None for r in safe_reports), [r.error for r in safe_reports]
    assert all(r.forbidden_actuations_reaching_page == () for r in safe_reports), [
        r.as_dict() for r in safe_reports if r.forbidden_actuations_reaching_page
    ]
    # 양성 대조 (i) — 파이프라인이 실제로 무언가는 했다.
    assert sum(len(r.page_calls) for r in safe_reports) > 0, (
        "actuation 이 0 이면 '위반 0건'은 아무것도 증명하지 않는다"
    )
    # 양성 대조 (ii) — 금지 control 의 **존재**는 관측돼 evidence 에 남았다.
    assert any(r.forbidden_controls_observed for r in safe_reports)

    # 양성 대조 (iii) — 같은 하네스가 위반을 실제로 검출한다.
    unsafe_reports = run_fixture_safety_regression(cases, _unsafe_pipeline)
    assert any(r.forbidden_actuations_reaching_page for r in unsafe_reports), (
        "하네스가 위반을 검출하지 못한다 — '0건'이 무의미하다"
    )


def test_login_first_auth_fixture_has_zero_credential_fill_and_click(tmp_path):
    """`login_first_auth` 에서 `Page.fill`/`Page.click` 이 credential 대상에 **0회**."""
    root = tmp_path / "v3"
    _write_matrix(root)
    case = next(c for c in load_fixture_matrix(root) if c.fixture_id == "login_first_auth")

    guard = ActivationSafetyGuard(_ContractStub(family_id="F1", fixed_fixture=""))
    recorder = RecordingPage()
    guarded = guard.guard_page(recorder)
    _safe_pipeline(case, guard, guarded, recorder)

    counts = credential_actuation_counts(recorder)
    assert counts["credential_fill"] == 0, recorder.calls
    assert counts["credential_click"] == 0, recorder.calls
    assert counts["credential_any"] == 0, recorder.calls
    # 양성 대조 — 파이프라인은 죽지 않았다. 안전한 control 은 실제로 눌렸다.
    assert counts["total_calls"] > 0, "아무 actuation 도 없었다 — 0 은 증명이 아니다"
    assert any("cat-water" in str(c["selector"]) for c in recorder.calls)


def test_login_first_auth_unguarded_control_does_fill_and_click_credentials(tmp_path):
    """양성 대조 — 가드가 없으면 같은 fixture 에서 credential fill/click 이 실제로 발생한다.

    이게 없으면 위 테스트의 '0회'는 spy 가 잘못 배선돼 아무것도 못 세는 경우와
    구분되지 않는다.
    """
    root = tmp_path / "v3"
    _write_matrix(root)
    case = next(c for c in load_fixture_matrix(root) if c.fixture_id == "login_first_auth")

    guard = ActivationSafetyGuard(None)
    recorder = RecordingPage()
    _unsafe_pipeline(case, guard, guard.guard_page(recorder), recorder)

    counts = credential_actuation_counts(recorder)
    assert counts["credential_fill"] >= 1
    assert counts["credential_click"] >= 1


def test_attaches_to_real_w5e_matrix_when_it_arrives():
    """W5E 의 실제 matrix 가 도착하면 자동으로 붙는다 — 파일 목록 하드코딩 없음.

    아직 없으면 skip 한다. **skip 은 PASS 가 아니다** — 위의 합성 matrix 테스트가
    하네스 자체의 판별력을 이미 증명하고, 여기는 배선만 확인한다.
    """
    root = default_v3_fixture_root()
    if not (root / "FIXTURE_DISCRIMINATION_MATRIX.json").is_file():
        pytest.skip(f"W5E fixture matrix 미도착: {root} (하네스는 합성 matrix 로 검증됨)")
    cases = load_fixture_matrix(root)
    assert cases, "matrix 는 있는데 case 가 0건이다"
    missing = [c.fixture_id for c in cases if not c.exists]
    assert not missing, f"matrix 가 가리키는 fixture 파일이 없다: {missing}"


def test_fixture_case_reports_missing_file_instead_of_silently_passing(tmp_path):
    case = FixtureCase(fixture_id="ghost", path=tmp_path / "ghost.html")
    reports = run_fixture_safety_regression([case], lambda c, g, gp, r: None)
    assert reports[0].fixture_exists is False, (
        "존재하지 않는 fixture 가 '위반 0건'으로 조용히 통과했다"
    )
