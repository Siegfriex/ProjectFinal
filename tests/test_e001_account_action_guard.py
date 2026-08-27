"""E001 배치 러너 — 계정 행동 금지 가드.

`login/signup/purchase/payment/message send/booking confirm/OTP 입력/개인정보
입력/CAPTCHA 우회` 로 이어질 수 있는 activation 후보를 감지하면 그 target의
L1 activation(클릭) 코드 경로 자체가 실행되지 않는다는 것을 증명한다.

P-C의 `auth_login_gate.html` fixture를 그대로 재사용한다 — 이 fixture의
유일한 form 제출 버튼 텍스트가 정확히 "로그인"이므로, 새 fixture를 만들지
않고도 이 가드를 실전 후보 목록(L0Collector가 실제로 추출한 것)으로 검증할
수 있다.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
RESEARCH = REPO / "research" / "landing_accessibility"
sys.path.insert(0, str(RESEARCH / "src"))

from landing_accessibility.e001_runner.batch import BatchRunner  # noqa: E402
from landing_accessibility.e001_runner.guard import (  # noqa: E402
    AccountActionBlockedError,
    ActionCategory,
    classify_candidate,
    screen_candidates,
)
from landing_accessibility.e001_runner.outcomes import TargetOutcome  # noqa: E402
from landing_accessibility.e001_runner.plan import TargetSpec  # noqa: E402
from landing_accessibility.engine.l1_engine import Scout  # noqa: E402

pytest.importorskip("playwright.sync_api")

FIXTURES = RESEARCH / "fixtures"
pytestmark = pytest.mark.slow


# ── 순수 함수 단위 테스트 ────────────────────────────────────────────────────
@pytest.mark.parametrize(
    ("text", "expected_category"),
    [
        ("로그인", ActionCategory.LOGIN),
        ("Sign in", ActionCategory.LOGIN),
        ("회원가입", ActionCategory.SIGNUP),
        ("결제하기", ActionCategory.PAYMENT),
        ("구매확정", ActionCategory.PURCHASE),
        ("예약 확정", ActionCategory.BOOKING_CONFIRM),
        ("메시지 전송", ActionCategory.MESSAGE_SEND),
        ("인증번호 입력", ActionCategory.OTP_ENTRY),
    ],
)
def test_classify_candidate_blocks_forbidden_text(text, expected_category):
    risk = classify_candidate({"accessible_name": text})
    assert risk.blocked
    assert risk.category == expected_category


@pytest.mark.parametrize(
    "text",
    ["콘텐츠 열기", "검색", "장소 탐색", "상품 상세 확인", "다음", "닫기"],
)
def test_classify_candidate_does_not_over_block_benign_text(text):
    """과탐 금지 — 정당한 후보를 막는 것도 결함이다."""
    risk = classify_candidate({"accessible_name": text})
    assert not risk.blocked


def test_classify_candidate_blocks_password_input_type():
    risk = classify_candidate({"input_type": "password", "accessible_name": None})
    assert risk.blocked
    assert risk.category == ActionCategory.CREDENTIAL_FIELD


def test_screen_candidates_returns_none_when_all_safe():
    assert screen_candidates([{"accessible_name": "다음"}, {"accessible_name": "검색"}]) is None


def test_screen_candidates_flags_first_forbidden_hit():
    risk = screen_candidates([{"accessible_name": "다음"}, {"accessible_name": "로그인"}])
    assert risk is not None
    assert risk.category == ActionCategory.LOGIN


# ── 엔진 통합: 실제 L0 후보 목록에 가드를 적용 ─────────────────────────────────
def _login_target() -> TargetSpec:
    return TargetSpec(
        target_id="wt-guard-login",
        canonical_service_key="guard_test",
        official_url="https://example.com/never-opened",
        interaction_archetype="FINANCIAL_ACTION_ENTRY",
        fixture_override="auth_login_gate.html",
    )


def test_l1_executor_blocks_before_scout_is_ever_constructed(tmp_path, monkeypatch):
    """`Scout.scout`를 감시한다.

    ── 계약변경 (`T-A-W1-001` §1 · G1-a · `D-R0-01` target-level kill 폐기 ·
       `D-R0-71`로 이 파일이 W1 scope 에 편입) ────────────────────────────
    폐기된 계약: "`_login_target()`(`auth_login_gate.html` + `FINANCIAL_ACTION_
    ENTRY`)은 Scout 를 절대 만들지 않는다". 새 계약에서 `LOGIN` candidate 는
    `AUTH_ENTRY_ALLOWED_CONDITIONALLY`(안전한 대안)이므로 guard 를 통과한다 —
    이 fixture 자신의 헤더 주석이 이미 이 archetype 에서 `FUNCTION_ENDPOINT_
    REACHED`를 기대값으로 적어 뒀다. 이제는 `Scout.scout`가 **실제로 호출된다**
    는 것과, landing 자체가 gate 라 **0-activation** 으로 종료된다는 것(재시도
    없이 1회 만에 끝남)을 검증한다.
    """
    scout_calls: list[str] = []
    original_scout = Scout.scout

    def spy_scout(self, **kwargs):
        scout_calls.append(kwargs.get("web_target_id", "?"))
        return original_scout(self, **kwargs)

    monkeypatch.setattr(Scout, "scout", spy_scout)

    runner = BatchRunner(out_dir=tmp_path / "out", fixture_root=FIXTURES, batch_size=5)
    manifests = runner.run(
        [_login_target()], execution_mode="FIXTURE", target_executor=runner.l1_executor
    )

    assert scout_calls == [_login_target().target_id], (
        "guard 가 여전히 target-level kill 을 하고 있다 — Scout.scout 이 호출되지 않았다"
    )
    result = manifests[0].results[0]
    assert result["outcome"] == TargetOutcome.MEASURED.value
    assert result["attempts"] == 1, "guard 를 통과했으므로 재시도 없이 1회에 끝난다"


def test_l1_executor_does_not_click_any_forbidden_selector(tmp_path, monkeypatch):
    """더 낮은 층에서도 확인한다 — playwright의 `Page.click`이 이 target에 대해
    한 번도 불리지 않았다는 것을 spy로 증명한다.
    """
    from playwright.sync_api import Page

    click_calls: list[str] = []
    original_click = Page.click

    def spy_click(self, selector, *args, **kwargs):
        click_calls.append(selector)
        return original_click(self, selector, *args, **kwargs)

    monkeypatch.setattr(Page, "click", spy_click)

    runner = BatchRunner(out_dir=tmp_path / "out", fixture_root=FIXTURES, batch_size=5)
    runner.run([_login_target()], execution_mode="FIXTURE", target_executor=runner.l1_executor)

    assert click_calls == [], f"클릭이 발생했다: {click_calls}"


def test_guard_trip_raises_account_action_blocked_from_executor_layer():
    """`run_l1_if_safe`가 아니라 가드 자체의 예외 타입도 직접 재확인한다."""
    from landing_accessibility.e001_runner.guard import assert_no_forbidden_action

    with pytest.raises(AccountActionBlockedError):
        assert_no_forbidden_action({"accessible_name": "결제하기"})
