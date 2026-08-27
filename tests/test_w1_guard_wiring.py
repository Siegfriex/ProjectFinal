"""E001 배치 러너 — candidate/state-level guard (`T-A-W1-001` §1, D-R0-01~06).

옛 결함: `guard.screen_candidates`가 후보 목록을 돌다 **첫 위험 후보에서
`return risk`**했고, 호출부(`real_executor.py`/`executor.py`)가 그걸 받으면
`Scout`를 아예 만들지 않았다 — target-level kill. 실측 영향(B의 CLEAN-0 조사):
59건 중 25건이 `ACCOUNT_ACTION_BLOCKED`, 그중 19건이 LOGIN, 사유 다수가 문자
그대로 `matched text: '로그인 로그인'` — 랜딩에 로그인 링크가 있다는 사실만으로
L1 전체가 삭제됐다. 클릭한 것도, 클릭 후보로 고른 것도 아니었다.

이 파일은 두 층에서 시정을 검증한다:

1. **순수 함수** — `guard.classify_candidate_state`/`assess_reachable_candidates`
   가 9-state 마스크를 올바르게 매기고, "안전한 대안이 있으면 막지 않는다"는
   규칙을 지키는가.
2. **엔진 통합** — 실제 fixture(`w1_query_login_purchase.html`·`auth_login_gate.html`)
   로 `BatchRunner`를 돌려, 옛 결함이라면 target-kill됐을 상황에서 이제 Scout가
   실제로 실행되고, 금지된 후보는 클릭되지 않는다는 것을 click/fill spy로 증명한다.

**주의 — 기존 테스트와의 관계**: `tests/test_e001_account_action_guard.py`의
`test_l1_executor_blocks_before_scout_is_ever_constructed` 등은 `auth_login_gate.html`
+ `FINANCIAL_ACTION_ENTRY`에서 "Scout가 절대 생성되지 않는다"를 검증했다 — 이건
**바로 이 티켓이 고치는 그 버그**를 검증한 것이었다(그 fixture 자신의 헤더 주석이
이미 "FINANCIAL_ACTION_ENTRY → FUNCTION_ENDPOINT_REACHED"를 기대값으로 적어
뒀다 — Scout가 생성되지 않으면 그 기대값에 영원히 도달할 수 없다). 이 파일의
`test_finance_archetype_reaches_login_page_without_entering_credentials`가 그
정확한 시나리오의 **새 기대 동작**을 검증한다. 저 옛 테스트 파일은 W1 소유가
아니라(소유권 경계, 티켓 "소유 파일" 절) 여기서 고치지 않았다 — 최종 보고서에
회귀로 명시했다.
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
    CandidateActionState,
    assess_reachable_candidates,
    classify_candidate_state,
)
from landing_accessibility.e001_runner.outcomes import TargetOutcome  # noqa: E402
from landing_accessibility.e001_runner.plan import TargetSpec  # noqa: E402
from landing_accessibility.engine.l1_engine import Scout  # noqa: E402

pytest.importorskip("playwright.sync_api")

FIXTURES = RESEARCH / "fixtures"


# ══════════════════════════════════════════════════════════════════════════
# 1. 순수 함수 — `classify_candidate_state`
# ══════════════════════════════════════════════════════════════════════════
def _cand(**kw: object) -> dict[str, object]:
    base = {"selector": "#c", "hittable": True, "dom_order": 0}
    base.update(kw)
    return base


@pytest.mark.parametrize(
    ("text", "expected_state"),
    [
        ("로그인", CandidateActionState.AUTH_ENTRY_ALLOWED_CONDITIONALLY),
        ("Sign in", CandidateActionState.AUTH_ENTRY_ALLOWED_CONDITIONALLY),
        ("결제하기", CandidateActionState.FORBIDDEN_TRANSACTION),
        ("구매확정", CandidateActionState.FORBIDDEN_TRANSACTION),
        ("예약 확정", CandidateActionState.FORBIDDEN_TRANSACTION),
        ("메시지 전송", CandidateActionState.FORBIDDEN_TRANSACTION),
        ("회원가입", CandidateActionState.FORBIDDEN_TRANSACTION),
        # `T-A-W1-P2-DECIDED` §1 — 장바구니. D-R0-06 은 존재 관측만 허용하고
        # 활성화는 금지한다 — SAFE 로 두면 Scout 가 확장 대상으로 삼을 수 있다.
        ("장바구니 담기", CandidateActionState.FORBIDDEN_TRANSACTION),
        ("담기", CandidateActionState.FORBIDDEN_TRANSACTION),
        ("Add to Cart", CandidateActionState.FORBIDDEN_TRANSACTION),
        ("검색", CandidateActionState.SAFE),
        ("상품 상세 확인", CandidateActionState.SAFE),
    ],
)
def test_classify_candidate_state_maps_text_to_nine_state_mask(text, expected_state):
    assert classify_candidate_state(_cand(accessible_name=text)) is expected_state


def test_classify_candidate_state_login_is_never_hard_forbidden():
    """`D-R0-03` — 로그인 candidate 활성화(=클릭해서 로그인 화면으로 이동)는 그
    자체로 금지 행동이 아니다. 자격증명 **입력**·**제출**만 금지다(Scout 구조상
    클릭만 하고 QUERY 검색창 외에는 아무것도 채우지 않으므로 이 둘은 애초에
    일어나지 않는다)."""
    state = classify_candidate_state(_cand(accessible_name="로그인"))
    assert state is CandidateActionState.AUTH_ENTRY_ALLOWED_CONDITIONALLY
    assert state not in (
        CandidateActionState.FORBIDDEN_CREDENTIAL_INPUT,
        CandidateActionState.FORBIDDEN_TRANSACTION,
        CandidateActionState.FORBIDDEN_PERSONAL_DATA,
        CandidateActionState.FORBIDDEN_CAPTCHA_BYPASS,
    )


def test_classify_candidate_state_credential_field_input_type():
    state = classify_candidate_state(
        _cand(input_type="password", accessible_name=None, hittable=False)
    )
    # hittable=False 가 우선한다 — 화면에 실제로 없는/눌리지 않는 필드는
    # DISABLED_OR_INERT다. hittable 인 경우만 아래에서 별도로 확인한다.
    assert state is CandidateActionState.DISABLED_OR_INERT

    state_hittable = classify_candidate_state(
        _cand(input_type="password", accessible_name=None, hittable=True)
    )
    assert state_hittable is CandidateActionState.FORBIDDEN_CREDENTIAL_INPUT


# ── D-R0-05 CAPTCHA: active(hittable) 만 terminal, passive(비-hittable)는 아니다 ──
def test_classify_candidate_state_active_captcha_is_forbidden():
    state = classify_candidate_state(_cand(accessible_name="reCAPTCHA 확인", hittable=True))
    assert state is CandidateActionState.FORBIDDEN_CAPTCHA_BYPASS


def test_classify_candidate_state_passive_captcha_mention_is_not_forbidden():
    """DOM 안에 캡차 코드/문구가 있다는 사실만으로 terminal이 아니다(`D-R0-05`) —
    이 후보가 현재 hittable하지 않으면(가려짐/비활성) `DISABLED_OR_INERT`다."""
    state = classify_candidate_state(
        _cand(accessible_name="본 서비스는 reCAPTCHA 로 보호됩니다", hittable=False)
    )
    assert state is CandidateActionState.DISABLED_OR_INERT
    assert state is not CandidateActionState.FORBIDDEN_CAPTCHA_BYPASS


def test_classify_candidate_state_unknown_when_no_identity():
    assert classify_candidate_state({"hittable": True}) is CandidateActionState.UNKNOWN
    assert classify_candidate_state("not-a-dict") is CandidateActionState.UNKNOWN  # type: ignore[arg-type]


# ── `T-A-W1-P2-DECIDED` §2 (D-R0-70 계열 여덟 번째) — hittable(occlusion) ≠ enabled ──
def test_classify_candidate_state_disabled_but_hittable_is_not_safe():
    """`enabled=False`인 candidate(HTML `disabled`/`aria-disabled`/`inert`)는
    `hittable=True`(가려지지 않고 화면에 보임)이어도 `SAFE`가 아니라
    `DISABLED_OR_INERT`다 — hittable은 occlusion 판정일 뿐 조작 가능성 판정이
    아니다."""
    state = classify_candidate_state(_cand(accessible_name="다음", hittable=True, enabled=False))
    assert state is CandidateActionState.DISABLED_OR_INERT
    assert state is not CandidateActionState.SAFE


def test_classify_candidate_state_enabled_true_is_safe():
    state = classify_candidate_state(_cand(accessible_name="다음", hittable=True, enabled=True))
    assert state is CandidateActionState.SAFE


def test_classify_candidate_state_missing_enabled_key_defaults_safe():
    """`enabled` 필드가 없으면(이 세션 이전 probe 스냅샷과의 하위호환) 결측을
    "비활성"으로 단정하지 않는다 — `l1_engine._is_enabled`의 "결측 시 True" 취급과
    일관된다."""
    state = classify_candidate_state(_cand(accessible_name="다음", hittable=True))
    assert state is CandidateActionState.SAFE


# ══════════════════════════════════════════════════════════════════════════
# 2. 순수 함수 — `assess_reachable_candidates` (target-kill 폐기 규칙)
# ══════════════════════════════════════════════════════════════════════════
def test_assess_reachable_candidates_does_not_block_when_safe_alternative_exists():
    """`D-R0-06` — 구매 control의 **존재**가 안전한 대안이 있는데도 target 전체를
    죽이지 않는다."""
    candidates = [
        _cand(selector="#search-submit", accessible_name="검색", dom_order=0, marked_primary=True),
        _cand(selector="#buy-now", accessible_name="구매하기", dom_order=1),
    ]
    assessment = assess_reachable_candidates(candidates, branching_limit=4)
    assert assessment.blocking is None
    assert assessment.reachable_considered == 2
    states = {c["selector"]: c["state"] for c in assessment.as_dict()["candidates"]}
    assert states["#buy-now"] == CandidateActionState.FORBIDDEN_TRANSACTION.value


def test_assess_reachable_candidates_blocks_only_when_every_reachable_candidate_is_forbidden():
    candidates = [
        _cand(selector="#buy-now", accessible_name="구매하기", dom_order=0),
        _cand(selector="#checkout", accessible_name="결제하기", dom_order=1),
    ]
    assessment = assess_reachable_candidates(candidates, branching_limit=4)
    assert assessment.blocking is not None
    assert "forbidden" in assessment.blocking.reason


def test_assess_reachable_candidates_ignores_non_hittable_candidates_for_blocking():
    """옛 결함의 정확한 재현 방지 — DOM에 있지만 Scout가 애초에 클릭할 수 없는
    (hittable=False) 후보는 **차단 판정**(reachable_considered · blocking)에는
    들어가지 않는다. 그래도 evidence 에서는 사라지지 않는다 — `DISABLED_OR_INERT`
    로 `candidates` 목록에 남는다(C 의 W1 completion 감사 지적: 이 상태가 batch
    detail 에 전혀 노출되지 않아 채점 불가능했다 — 아래에서 그 가시성을 확인한다).
    """
    candidates = [
        _cand(selector="#hidden-login", accessible_name="로그인", hittable=False),
    ]
    assessment = assess_reachable_candidates(candidates, branching_limit=4)
    assert assessment.reachable_considered == 0
    assert assessment.blocking is None

    states_by_selector = {c["selector"]: c["state"] for c in assessment.as_dict()["candidates"]}
    assert states_by_selector["#hidden-login"] == CandidateActionState.DISABLED_OR_INERT.value


def test_assess_reachable_candidates_respects_branching_limit_for_blocking_only():
    """branching_limit 밖의 후보는 **차단 판정**(reachable_considered · blocking)
    대상이 아니다(Scout도 그 후보를 첫 분기에서 보지 않는다) — 하지만 evidence
    가시성에서는 빠지지 않는다: 존재는 여전히 `candidates` 목록에 남는다
    (`D-R0-03` "존재와 행동을 구분" — 판정 범위를 넓히지 않으면서 가시성만
    넓힌다).
    """
    candidates = [
        _cand(selector=f"#c{i}", accessible_name="검색", dom_order=i) for i in range(2)
    ] + [_cand(selector="#late-buy", accessible_name="구매하기", dom_order=99)]
    assessment = assess_reachable_candidates(candidates, branching_limit=2)
    assert assessment.reachable_considered == 2

    states_by_selector = {c["selector"]: c["state"] for c in assessment.as_dict()["candidates"]}
    assert "#late-buy" in states_by_selector, (
        "branching_limit 밖 후보가 evidence 에서 완전히 사라졌다 — 존재 관측 자체가 안 남는다"
    )
    assert states_by_selector["#late-buy"] == CandidateActionState.FORBIDDEN_TRANSACTION.value
    # 그래도 차단 판정에는 영향을 주지 않는다 — 안전한 후보 2개가 reachable 이므로 막히지 않는다.
    assert assessment.blocking is None


# ══════════════════════════════════════════════════════════════════════════
# 2-b. 순수 함수 — `D-R0-70-3` 양방향 대조군: disabled-only vs enabled
# ══════════════════════════════════════════════════════════════════════════
def test_assess_reachable_candidates_blocks_when_every_reachable_candidate_is_disabled():
    """대조군 방향 1 — disabled control **만** 있는 랜딩은 확장 대상이 되지
    않아야 한다. `hittable=True`(가려지지 않음)이지만 `enabled=False`인 후보
    하나뿐이면, 그건 hard-forbidden이 아니라(위험한 어휘가 아니다) "조작 가능한
    대안이 없어서" 막힌다 — `D-R0-70` 계열: hittable이 enabled를 뜻하지 않는다."""
    candidates = [
        _cand(selector="#next", accessible_name="다음", dom_order=0, enabled=False),
    ]
    assessment = assess_reachable_candidates(candidates, branching_limit=4)
    assert assessment.blocking is not None
    assert assessment.blocking.category is None, "disabled 는 forbidden 어휘 카테고리가 아니다"
    assert "DISABLED_OR_INERT" in assessment.blocking.reason

    states_by_selector = {c["selector"]: c["state"] for c in assessment.as_dict()["candidates"]}
    assert states_by_selector["#next"] == CandidateActionState.DISABLED_OR_INERT.value


def test_assess_reachable_candidates_does_not_block_when_enabled_candidate_exists():
    """대조군 방향 2 — enabled control이 있는 랜딩은 확장 대상이 되어야 한다.
    disabled 후보가 같은 목록에 섞여 있어도(존재 관측은 남는다) 막지 않는다."""
    candidates = [
        _cand(selector="#next", accessible_name="다음", dom_order=0, enabled=False),
        _cand(selector="#detail", accessible_name="상세보기", dom_order=1, enabled=True),
    ]
    assessment = assess_reachable_candidates(candidates, branching_limit=4)
    assert assessment.blocking is None

    states_by_selector = {c["selector"]: c["state"] for c in assessment.as_dict()["candidates"]}
    assert states_by_selector["#next"] == CandidateActionState.DISABLED_OR_INERT.value
    assert states_by_selector["#detail"] == CandidateActionState.SAFE.value


def test_assess_reachable_candidates_cart_candidate_alone_is_blocked_but_does_not_revert_to_target_kill():
    """장바구니 담기 control **하나만** reachable이면(안전한 대안이 전혀 없으면)
    막는다 — `G1-a` target-level kill이 아니라 candidate/state-level 판정이
    같은 결론에 도달한 것이다. 아래
    `test_assess_reachable_candidates_cart_present_does_not_block_other_safe_candidates`
    가 반대 방향(안전한 대안이 있으면 막지 않는다)을 확인한다."""
    candidates = [
        _cand(selector="#add-to-cart", accessible_name="장바구니 담기", dom_order=0),
    ]
    assessment = assess_reachable_candidates(candidates, branching_limit=4)
    assert assessment.blocking is not None
    assert assessment.blocking.category == "ADD_TO_CART"


def test_assess_reachable_candidates_cart_present_does_not_block_other_safe_candidates():
    """장바구니 담기 control이 있어도, 같은 랜딩에 다른 SAFE 후보가 있으면
    target 전체를 죽이지 않는다(`D-R0-06`) — 장바구니 후보만 evidence로 남고
    제외될 뿐, Scout는 나머지 SAFE 후보로 계속 진행할 수 있어야 한다."""
    candidates = [
        _cand(selector="#add-to-cart", accessible_name="장바구니 담기", dom_order=0),
        _cand(selector="#detail", accessible_name="상세보기", dom_order=1),
    ]
    assessment = assess_reachable_candidates(candidates, branching_limit=4)
    assert assessment.blocking is None

    states_by_selector = {c["selector"]: c["state"] for c in assessment.as_dict()["candidates"]}
    assert states_by_selector["#add-to-cart"] == CandidateActionState.FORBIDDEN_TRANSACTION.value
    assert states_by_selector["#detail"] == CandidateActionState.SAFE.value


# ══════════════════════════════════════════════════════════════════════════
# 3. 엔진 통합 — 실제 fixture + `BatchRunner`
# ══════════════════════════════════════════════════════════════════════════
def _query_with_purchase_only() -> TargetSpec:
    # `endpoint_definition`을 명시적으로 실어 준다(`search_dispatch.html`과 같은
    # 패턴) — 그래야 Scout가 검색 제출 1회 만에 endpoint를 찾고 종료한다. 비워
    # 두면(`executor._query_target()`처럼) endpoint가 영원히 성립하지 않아 Scout가
    # 예산을 다 쓸 때까지 검색/구매 후보를 계속 다시 시도하게 되고, 그러면 이
    # 테스트가 증명하려는 것("안전한 후보로 1회 만에 끝난다")과 다른 이야기가 된다.
    return TargetSpec(
        target_id="wt-w1-query-purchase",
        canonical_service_key="w1_query_purchase",
        official_url="https://example.com/never-opened",
        interaction_archetype="QUERY",
        fixture_override="w1_query_purchase_no_login.html",
        task_id="task_wt_w1_query_purchase",
        endpoint_definition="QUERY_SUBMITTED",
        endpoint_signal_type="URL_PATTERN",
    )


def _query_with_login_and_purchase() -> TargetSpec:
    return TargetSpec(
        target_id="wt-w1-query-login-purchase",
        canonical_service_key="w1_query_login_purchase",
        official_url="https://example.com/never-opened",
        interaction_archetype="QUERY",
        fixture_override="w1_query_login_purchase.html",
        task_id="task_wt_w1_query_login_purchase",
        endpoint_definition="QUERY_SUBMITTED",
        endpoint_signal_type="URL_PATTERN",
    )


def test_purchase_candidate_present_does_not_kill_target_and_is_never_clicked(
    tmp_path, monkeypatch
):
    """수용기준 4 — 구매 control이 **존재**해도 target 전체가 죽지 않고, Scout는
    실제로 안전한 검색 후보만 클릭해 endpoint에 도달한다. "구매하기" 버튼은
    reachable 후보 집합 안에 있어도 클릭되지 않는다 — click spy로 직접 증명한다
    (`D-R0-06`: 존재 관측은 허용, 활성화는 금지).
    """
    from playwright.sync_api import Page

    click_calls: list[str] = []
    original_click = Page.click

    def spy_click(self, selector, *args, **kwargs):
        click_calls.append(selector)
        return original_click(self, selector, *args, **kwargs)

    monkeypatch.setattr(Page, "click", spy_click)

    runner = BatchRunner(out_dir=tmp_path / "out", fixture_root=FIXTURES, batch_size=5)
    manifests = runner.run([_query_with_purchase_only()], execution_mode="FIXTURE")

    result = manifests[0].results[0]
    assert result["outcome"] != TargetOutcome.ACCOUNT_ACTION_BLOCKED.value, (
        f"구매 버튼 존재만으로 target 이 죽었다(D-R0-06 위반): {result}"
    )
    detail = result["detail"]
    assert detail.get("scout_invoked") is True, "Scout 가 아예 호출되지 않았다"
    assert detail["endpoint_status"] == "FUNCTION_ENDPOINT_REACHED", (
        f"안전한 검색 경로가 실제로 도달하지 못했다: {detail}"
    )

    # 후보 판정 evidence가 남는다(D-R0-03: 존재는 annotation, 활성화만 막힌다).
    mask = detail.get("candidate_action_mask")
    assert mask is not None
    states_by_text = {c["text"]: c["state"] for c in mask["candidates"]}
    assert states_by_text.get("구매하기") == "FORBIDDEN_TRANSACTION"

    assert len(click_calls) >= 1, "검색 제출조차 클릭되지 않았다"
    assert not any("buy-now" in sel for sel in click_calls), (
        f"구매 버튼이 실제로 클릭됐다: {click_calls}"
    )


def test_login_candidate_present_does_not_trigger_target_level_kill(tmp_path, monkeypatch):
    """수용기준 1 — 로그인 control이 **존재**한다는 사실만으로 target 전체가
    `ACCOUNT_ACTION_BLOCKED` 되지 않는다(옛 결함의 정확한 재현: guard.py:170-182
    가 후보 목록 아무 데서나 "로그인" 텍스트를 만나면 그 즉시 target 전체를 죽였다).

    이 테스트는 **guard 층만** 증명한다 — L0가 관측한 후보에 guard가 어떤 판정을
    내렸는지(`candidate_action_mask`)는 Scout를 만들기 **전에** 이미 확정되므로,
    아래에서 발견된 별개의 엔진 결함(gate 오판, `T-B-BLK-003`)과 무관하게 유효하다.
    fixture는 실제 한국 서비스 랜딩의 전형(검색+로그인+구매가 한 화면)을 그대로
    유지한다 — 로그인 어휘를 빼서 "깨끗한" fixture로 바꾸면 아래에서 발견한
    production 결함이 테스트에서 보이지 않게 된다.
    """
    from playwright.sync_api import Page

    click_calls: list[str] = []
    original_click = Page.click

    def spy_click(self, selector, *args, **kwargs):
        click_calls.append(selector)
        return original_click(self, selector, *args, **kwargs)

    monkeypatch.setattr(Page, "click", spy_click)

    runner = BatchRunner(out_dir=tmp_path / "out", fixture_root=FIXTURES, batch_size=5)
    manifests = runner.run([_query_with_login_and_purchase()], execution_mode="FIXTURE")

    result = manifests[0].results[0]
    assert result["outcome"] != TargetOutcome.ACCOUNT_ACTION_BLOCKED.value, (
        f"로그인 후보 존재만으로 target 이 죽었다 — 옛 결함이 재현됐다: {result}"
    )
    detail = result["detail"]
    assert detail.get("scout_invoked") is True, "guard 가 Scout 생성 자체를 막았다"

    # guard가 실제로 후보를 통과시켰다는 것을 evidence(`candidate_action_mask`)로
    # 직접 확인한다 — 이 판정은 Scout 생성 이전에 `assess_reachable_candidates`가
    # L0 관측만으로 내린 것이라, 아래에서 발견된 엔진의 gate 오판과 완전히 분리된다.
    mask = detail.get("candidate_action_mask")
    assert mask is not None
    assert mask["blocking"] is None, f"guard가 여전히 target-level kill을 냈다: {mask}"
    states_by_text = {c["text"]: c["state"] for c in mask["candidates"]}
    assert states_by_text.get("로그인") == "AUTH_ENTRY_ALLOWED_CONDITIONALLY", (
        "로그인 candidate가 hard-forbidden으로 오분류됐다"
    )
    assert states_by_text.get("구매하기") == "FORBIDDEN_TRANSACTION"

    # guard는 금지 후보를 클릭하지 않았다 — "구매하기"/로그인 gate 페이지가
    # 클릭된 적은 없다(아래 테스트가 검색 후보는 실제로 클릭됨을 별도로 증명한다).
    assert not any("buy-now" in sel for sel in click_calls)
    assert not any("auth_login_gate" in sel for sel in click_calls)


def test_query_search_candidate_actually_gets_clicked_despite_login_text_present(
    tmp_path, monkeypatch
):
    """**guard가 아니라 엔진의 정직한 최종 동작**을 검증한다 — 안전한 검색 후보가
    존재하고 guard가 막지 않았다면, Scout는 실제로 그 후보를 시도해서 endpoint에
    도달**해야 한다**.

    `T-B-BLK-003` 갱신(`fed031f`, `origin/claude-b/w2-rf-detector@b28aaa5` 병합) —
    이전에는 `xfail`이었다: `engine.l1_engine.gate_observed()`가 구조 신호 없이
    로그인/회원가입 **어휘만으로도** gate=True를 냈다(`landing 본문 전체 innerText`
    스캔, `login_basis` 비어있지 않으면 충분). 그래서 이 fixture(검색+로그인+구매)는
    QUERY archetype인데도 검색 후보를 한 번도 클릭하지 못하고 랜딩에서
    `AUTH_GATE_REACHED`로 끝났다 — `D-R0-03`·`D-R0-04` 위반.

    W2가 `D-R0-59-1`(`gate_observed 어휘단독 위양성 시정`)로 `_gate_structural_signal_present`
    를 추가해 **구조 신호(password_input/otp_input/captcha_challenge_active 등)가
    최소 하나 없으면 어휘만으로는 gate가 성립하지 않게** 고쳤다(`l1_engine.py`,
    W2 소유·읽기전용). 이 fixture는 구조 신호가 전혀 없는 순수 어휘 케이스라 이제
    XPASS로 전환됐다 — `xfail` 마커를 남겨 두면 그 자체가 오래된 정보가 된다.
    """
    from playwright.sync_api import Page

    click_calls: list[str] = []
    original_click = Page.click

    def spy_click(self, selector, *args, **kwargs):
        click_calls.append(selector)
        return original_click(self, selector, *args, **kwargs)

    monkeypatch.setattr(Page, "click", spy_click)

    runner = BatchRunner(out_dir=tmp_path / "out", fixture_root=FIXTURES, batch_size=5)
    manifests = runner.run([_query_with_login_and_purchase()], execution_mode="FIXTURE")

    result = manifests[0].results[0]
    detail = result["detail"]
    assert any("search" in sel or "#q" in sel or "button" in sel for sel in click_calls), (
        f"검색 후보가 한 번도 클릭되지 않았다(T-B-BLK-003 이 고쳐지지 않았다): {click_calls}"
    )
    assert detail["endpoint_status"] == "FUNCTION_ENDPOINT_REACHED"


def _login_gate_target(archetype: str) -> TargetSpec:
    return TargetSpec(
        target_id=f"wt-w1-login-gate-{archetype.lower()}",
        canonical_service_key="w1_login_gate",
        official_url="https://example.com/never-opened",
        interaction_archetype=archetype,
        fixture_override="auth_login_gate.html",
    )


def test_finance_archetype_reaches_login_page_without_entering_credentials(tmp_path, monkeypatch):
    """수용기준 2·3(전반) — `FINANCIAL_ACTION_ENTRY`에서 로그인 gate는 실제로
    endpoint가 된다. `Scout`가 실제로 로그인 화면(=이 fixture 자체가 landing이자
    gate)에 **도달**하지만, 자격증명은 채우지 않는다는 것을 `Page.fill` spy로
    직접 증명한다(`Page.click`도 0회 — 이 fixture는 landing 자체가 gate라
    activation 없이 k=0/m=0으로 판정된다).
    """
    from playwright.sync_api import Page

    click_calls: list[str] = []
    fill_calls: list[str] = []
    original_click = Page.click
    original_fill = Page.fill

    def spy_click(self, selector, *args, **kwargs):
        click_calls.append(selector)
        return original_click(self, selector, *args, **kwargs)

    def spy_fill(self, selector, *args, **kwargs):
        fill_calls.append(selector)
        return original_fill(self, selector, *args, **kwargs)

    monkeypatch.setattr(Page, "click", spy_click)
    monkeypatch.setattr(Page, "fill", spy_fill)

    runner = BatchRunner(out_dir=tmp_path / "out", fixture_root=FIXTURES, batch_size=5)
    manifests = runner.run([_login_gate_target("FINANCIAL_ACTION_ENTRY")], execution_mode="FIXTURE")

    result = manifests[0].results[0]
    assert result["outcome"] != TargetOutcome.ACCOUNT_ACTION_BLOCKED.value, (
        "옛 결함 — 로그인 후보 존재만으로 target 이 죽었다면 여기서 재현된다"
    )
    detail = result["detail"]
    assert detail.get("scout_invoked") is True, (
        "Scout 가 로그인 페이지에 도달하지 못했다(생성조차 안 됨)"
    )
    assert detail["endpoint_status"] == "FUNCTION_ENDPOINT_REACHED"
    assert detail["endpoint_status_detail"] == "ENDPOINT_VIA_AUTH_GATE"

    assert fill_calls == [], f"자격증명 필드가 채워졌다(절대 금지 위반): {fill_calls}"
    assert click_calls == [], (
        f"이 fixture는 landing 자체가 gate라 0-activation 이어야 하는데 클릭이 발생했다: "
        f"{click_calls}"
    )


@pytest.mark.parametrize("archetype", ["ITEM_DETAIL", "QUERY", "CONTENT_OPEN"])
def test_non_finance_non_communication_archetype_gate_does_not_become_endpoint(tmp_path, archetype):
    """수용기준 3(반대편) — 같은 로그인 gate라도 `FINANCIAL_ACTION_ENTRY`/
    `COMMUNICATION_ENTRY`가 **아닌** archetype에서는 endpoint로 승격되지 않는다
    (`ENDPOINT_GATE_KINDS`, 엔진 소유·읽기전용 — 이 테스트는 guard가 그 판정을
    방해하지 않는다는 것만 확인한다: guard 가 target 을 죽이지 않아야 Scout 가
    애초에 이 판정에 도달한다).
    """
    runner = BatchRunner(out_dir=tmp_path / "out", fixture_root=FIXTURES, batch_size=5)
    manifests = runner.run([_login_gate_target(archetype)], execution_mode="FIXTURE")

    result = manifests[0].results[0]
    assert result["outcome"] != TargetOutcome.ACCOUNT_ACTION_BLOCKED.value
    detail = result["detail"]
    assert detail.get("scout_invoked") is True
    assert detail["endpoint_status"] == "AUTH_GATE_REACHED", (
        f"{archetype} 에서 로그인 gate가 endpoint로 승격됐다(규칙 E-6a 위반): {detail}"
    )


def test_scout_scout_is_actually_invoked_for_the_login_and_purchase_fixture(tmp_path, monkeypatch):
    """더 낮은 층 — `Scout.scout` 자체가 호출됐다는 것을 spy로 직접 증명한다
    (기존 회귀 테스트들과 같은 패턴, `tests/test_e001_default_executor_l0_l1.py` 참고)."""
    scout_calls: list[str] = []
    original_scout = Scout.scout

    def spy_scout(self, **kwargs):
        scout_calls.append(kwargs.get("web_target_id", "?"))
        return original_scout(self, **kwargs)

    monkeypatch.setattr(Scout, "scout", spy_scout)

    runner = BatchRunner(out_dir=tmp_path / "out", fixture_root=FIXTURES, batch_size=5)
    target = _query_with_login_and_purchase()
    runner.run([target], execution_mode="FIXTURE")

    assert scout_calls == [target.target_id], (
        f"옛 결함이면 이 target 은 target-kill 되어 Scout.scout 이 호출되지 않았다: {scout_calls}"
    )


# ══════════════════════════════════════════════════════════════════════════
# 4. 엔진 통합 — `T-A-W1-P2-DECIDED` 양방향 대조군 (D-R0-06 장바구니 · D-R0-70-3 disabled)
# ══════════════════════════════════════════════════════════════════════════
def _cart_only_target() -> TargetSpec:
    return TargetSpec(
        target_id="wt-w1-cart-only",
        canonical_service_key="w1_cart_only",
        official_url="https://example.com/never-opened",
        interaction_archetype="ITEM_DETAIL",
        fixture_override="w1_cart_only.html",
    )


def _cart_with_safe_alt_target() -> TargetSpec:
    return TargetSpec(
        target_id="wt-w1-cart-with-safe-alt",
        canonical_service_key="w1_cart_with_safe_alt",
        official_url="https://example.com/never-opened",
        interaction_archetype="QUERY",
        fixture_override="w1_cart_with_safe_alt.html",
        task_id="task_wt_w1_cart_with_safe_alt",
        endpoint_definition="QUERY_SUBMITTED",
        endpoint_signal_type="URL_PATTERN",
    )


def _disabled_only_target() -> TargetSpec:
    return TargetSpec(
        target_id="wt-w1-disabled-only",
        canonical_service_key="w1_disabled_only",
        official_url="https://example.com/never-opened",
        interaction_archetype="UTILITY_ENTRY",
        fixture_override="w1_disabled_only.html",
        task_id="task_wt_w1_disabled_only",
        endpoint_definition="NEXT_REACHED",
        endpoint_signal_type="DOM_AX_ROLE",
    )


def _enabled_only_target() -> TargetSpec:
    return TargetSpec(
        target_id="wt-w1-enabled-only",
        canonical_service_key="w1_enabled_only",
        official_url="https://example.com/never-opened",
        interaction_archetype="UTILITY_ENTRY",
        fixture_override="w1_enabled_only.html",
        task_id="task_wt_w1_enabled_only",
        endpoint_definition="NEXT_REACHED",
        endpoint_signal_type="DOM_AX_ROLE",
    )


def test_cart_only_landing_is_blocked_before_scout_is_constructed(tmp_path, monkeypatch):
    """`D-R0-06` 대조군 방향 1 — 장바구니 담기 control **만** 있는 랜딩(안전한
    대안 없음)은 guard가 막는다. `Scout.scout`가 아예 호출되지 않는다는 것을
    spy로 직접 증명한다 — `G1-a`의 target-level kill로 되돌아간 게 아니라(판정은
    여전히 candidate-level이다), 이 특정 랜딩에서는 그 판정이 "안전한 대안 없음"
    으로 귀결됐을 뿐이다.
    """
    scout_calls: list[str] = []
    original_scout = Scout.scout

    def spy_scout(self, **kwargs):
        scout_calls.append(kwargs.get("web_target_id", "?"))
        return original_scout(self, **kwargs)

    monkeypatch.setattr(Scout, "scout", spy_scout)

    runner = BatchRunner(out_dir=tmp_path / "out", fixture_root=FIXTURES, batch_size=5)
    manifests = runner.run([_cart_only_target()], execution_mode="FIXTURE")

    result = manifests[0].results[0]
    assert result["outcome"] == TargetOutcome.ACCOUNT_ACTION_BLOCKED.value
    detail = result["detail"]
    assert detail.get("scout_invoked") is False
    assert detail.get("blocked_category") == "ADD_TO_CART"
    assert scout_calls == [], (
        f"Scout 가 생성됐다 — 안전한 대안이 없는데도 막히지 않았다: {scout_calls}"
    )

    # `D-R0-06` — 존재 관측은 evidence 로 남는다(막는 건 활성화뿐).
    mask = detail.get("candidate_action_mask")
    assert mask is not None
    states_by_text = {c["text"]: c["state"] for c in mask["candidates"]}
    assert states_by_text.get("장바구니 담기") == "FORBIDDEN_TRANSACTION"


def test_cart_candidate_present_but_other_safe_candidate_lets_scout_proceed(tmp_path, monkeypatch):
    """`D-R0-06` 대조군 방향 2 — 장바구니 담기 control이 있어도 다른 SAFE 후보
    (검색)가 있으면 target 전체가 죽지 않고, Scout가 실제로 그 안전한 후보만
    클릭해 endpoint에 도달한다. 장바구니 버튼은 클릭 후보 집합 안에 있어도
    실제로 클릭되지 않는다 — click spy로 증명한다.
    """
    from playwright.sync_api import Page

    click_calls: list[str] = []
    original_click = Page.click

    def spy_click(self, selector, *args, **kwargs):
        click_calls.append(selector)
        return original_click(self, selector, *args, **kwargs)

    monkeypatch.setattr(Page, "click", spy_click)

    runner = BatchRunner(out_dir=tmp_path / "out", fixture_root=FIXTURES, batch_size=5)
    manifests = runner.run([_cart_with_safe_alt_target()], execution_mode="FIXTURE")

    result = manifests[0].results[0]
    assert result["outcome"] != TargetOutcome.ACCOUNT_ACTION_BLOCKED.value, (
        f"장바구니 버튼 존재만으로 target 이 죽었다(D-R0-06 위반): {result}"
    )
    detail = result["detail"]
    assert detail.get("scout_invoked") is True, "Scout 가 아예 호출되지 않았다"
    assert detail["endpoint_status"] == "FUNCTION_ENDPOINT_REACHED", (
        f"안전한 검색 경로가 실제로 도달하지 못했다: {detail}"
    )

    mask = detail.get("candidate_action_mask")
    assert mask is not None
    states_by_text = {c["text"]: c["state"] for c in mask["candidates"]}
    assert states_by_text.get("장바구니 담기") == "FORBIDDEN_TRANSACTION"

    assert len(click_calls) >= 1, "검색 제출조차 클릭되지 않았다"
    assert not any("add-to-cart" in sel for sel in click_calls), (
        f"장바구니 버튼이 실제로 클릭됐다: {click_calls}"
    )


def test_disabled_only_landing_does_not_become_expansion_target(tmp_path, monkeypatch):
    """`D-R0-70-3` 대조군 방향 1 — disabled control **만** 있는 랜딩은 확장
    대상이 되지 않아야 한다. `Scout.scout`가 아예 호출되지 않는다는 것을 spy로
    직접 증명한다."""
    scout_calls: list[str] = []
    original_scout = Scout.scout

    def spy_scout(self, **kwargs):
        scout_calls.append(kwargs.get("web_target_id", "?"))
        return original_scout(self, **kwargs)

    monkeypatch.setattr(Scout, "scout", spy_scout)

    runner = BatchRunner(out_dir=tmp_path / "out", fixture_root=FIXTURES, batch_size=5)
    manifests = runner.run([_disabled_only_target()], execution_mode="FIXTURE")

    result = manifests[0].results[0]
    assert result["outcome"] == TargetOutcome.ACCOUNT_ACTION_BLOCKED.value
    detail = result["detail"]
    assert detail.get("scout_invoked") is False
    assert scout_calls == [], (
        f"Scout 가 생성됐다 — disabled control 만 있는데도 확장 대상이 됐다: {scout_calls}"
    )

    mask = detail.get("candidate_action_mask")
    assert mask is not None
    states_by_text = {c["text"]: c["state"] for c in mask["candidates"]}
    assert states_by_text.get("다음") == "DISABLED_OR_INERT"


def test_enabled_only_landing_becomes_expansion_target(tmp_path, monkeypatch):
    """`D-R0-70-3` 대조군 방향 2 — `w1_disabled_only.html`과 구조가 완전히 같고
    `disabled` 속성만 없는 랜딩은 실제로 확장 대상이 된다: Scout가 생성되고,
    그 control을 실제로 클릭해 endpoint에 도달한다."""
    from playwright.sync_api import Page

    click_calls: list[str] = []
    original_click = Page.click

    def spy_click(self, selector, *args, **kwargs):
        click_calls.append(selector)
        return original_click(self, selector, *args, **kwargs)

    monkeypatch.setattr(Page, "click", spy_click)

    runner = BatchRunner(out_dir=tmp_path / "out", fixture_root=FIXTURES, batch_size=5)
    manifests = runner.run([_enabled_only_target()], execution_mode="FIXTURE")

    result = manifests[0].results[0]
    assert result["outcome"] != TargetOutcome.ACCOUNT_ACTION_BLOCKED.value
    detail = result["detail"]
    assert detail.get("scout_invoked") is True, "Scout 가 아예 호출되지 않았다"
    assert detail["endpoint_status"] == "FUNCTION_ENDPOINT_REACHED", (
        f"활성 control 이 실제로 클릭되어 endpoint 에 도달하지 못했다: {detail}"
    )
    assert any("next" in sel for sel in click_calls), (
        f"활성 control 이 실제로 클릭되지 않았다: {click_calls}"
    )

    mask = detail.get("candidate_action_mask")
    assert mask is not None
    states_by_text = {c["text"]: c["state"] for c in mask["candidates"]}
    assert states_by_text.get("다음") == "SAFE"
