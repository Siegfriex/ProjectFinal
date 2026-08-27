"""E001 배치 러너 — **기본 경로**가 L0와 L1을 함께 실행하는가 (2026-08-27 시정).

`_default_fixture_executor`는 원래 `executor.run_l0`만 불렀다 — L1(Scout)은
`target_executor=runner.l1_executor`를 호출부가 명시적으로 넘겨야만 실행되는
opt-in이었다. Claude A(control plane)가 그 구조를 지적했고, 확정 지시로
"모든 run에서 L0와 L1이 함께 켜져야 한다"고 답했다.

`tests/test_e001_account_action_guard.py`는 이미 "가드가 걸리면 Scout를 아예
만들지 않는다"를 증명했지만, **그 테스트는 전부 `target_executor=runner.
l1_executor`를 명시적으로 주입한 경로**였다. 이 파일은 정확히 같은 안전 계약이
**아무것도 넘기지 않은 기본 경로**(`runner.run(plan, execution_mode=...)`)에서도
성립한다는 것을 다시 증명한다 — 그것이 이번 시정이 실제로 봉인해야 하는 표면이다.

추가로, 계정 행동 가드의 텍스트 매칭에 걸리지 않는(즉 "안전해 보이는") 후보만
있는 landing에서도, 엔진 자신의 구조적 gate 판별(`l1_engine.Scout` · `depth.
gate_outcome_from_decision`)이 **어떤 클릭도 없이(k=0/m=0)** AUTH_GATE를
판정할 수 있다는 것과, 그 경로에서도 클릭이 0회라는 것을 click spy로 증명한다.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
RESEARCH = REPO / "research" / "landing_accessibility"
sys.path.insert(0, str(RESEARCH / "src"))

from landing_accessibility.e001_runner.batch import BatchRunner  # noqa: E402
from landing_accessibility.e001_runner.outcomes import TargetOutcome  # noqa: E402
from landing_accessibility.e001_runner.plan import TargetSpec  # noqa: E402
from landing_accessibility.engine.l1_engine import Scout  # noqa: E402

pytest.importorskip("playwright.sync_api")

FIXTURES = RESEARCH / "fixtures"
pytestmark = pytest.mark.slow


def _login_target() -> TargetSpec:
    """`auth_login_gate.html` — 유일한 form 제출 버튼 텍스트가 "로그인"이다.

    `guard.classify_candidate`의 텍스트 사전이 이 후보를 즉시 차단한다
    (`tests/test_e001_account_action_guard.py`와 같은 fixture를 재사용한다).
    """
    return TargetSpec(
        target_id="wt-default-guard-login",
        canonical_service_key="guard_test",
        official_url="https://example.com/never-opened",
        interaction_archetype="FINANCIAL_ACTION_ENTRY",
        fixture_override="auth_login_gate.html",
    )


def _identity_target() -> TargetSpec:
    """`auth_identity_gate.html` — 후보(간편인증 제공자 버튼 4개)는 가드의 현재
    텍스트 사전 어디에도 걸리지 않는다("PASS 앱 인증" 등은 로그인/결제/회원가입/
    OTP 패턴과 매치되지 않는다). 그런데도 이 landing 자체가 본인인증 gate이므로,
    Scout는 **활성화(activation) 0회**만에 `AUTH_GATE_REACHED`를 판정한다
    (`depth.compute_depth`의 `A1 §1.4` k=0/m=0 랜딩 판정 — `l1_engine.Scout.scout`이
    빈 prefix로 첫 BFS 항목을 평가할 때 `landing_gate`를 그대로 종료조건으로 쓴다).

    archetype은 COMMUNICATION_ENTRY — `depth.ENDPOINT_GATE_KINDS`에서 이 archetype은
    `LOGIN`만 endpoint로 인정하므로(본인인증은 아니다), IDENTITY_VERIFICATION gate는
    `AUTH_GATE_REACHED`로 남는다(엔드포인트로 승격되지 않는다).
    """
    return TargetSpec(
        target_id="wt-default-identity-gate",
        canonical_service_key="identity_test",
        official_url="https://example.com/never-opened",
        interaction_archetype="COMMUNICATION_ENTRY",
        fixture_override="auth_identity_gate.html",
    )


def _query_target() -> TargetSpec:
    """`search_dispatch.html` — 검색창 하나뿐인 QUERY archetype. 가드에 걸리지 않고,
    Scout가 실제로 검색창을 채우고 제출 버튼을 눌러 activation을 최소 1회 수행한다
    (`default_task_definition`이 `endpoint_definition=None`을 주므로 endpoint에는
    끝내 도달하지 못하고 예산 소진 후 `UNRESOLVED`로 끝난다 — `executor.
    default_task_definition`의 docstring이 명시한 정직한 결과다).
    """
    return TargetSpec(
        target_id="wt-default-query",
        canonical_service_key="query_test",
        official_url="https://example.com/never-opened",
        interaction_archetype="QUERY",
        fixture_override="search_dispatch.html",
    )


# ── 1. 기본 경로에서도 계정 행동 가드가 Scout 생성 자체를 막는다 ────────────────
def test_default_run_blocks_before_scout_is_ever_constructed(tmp_path, monkeypatch):
    """`target_executor`를 **아무것도 넘기지 않는다** — 이것이 이번 시정의 핵심
    검증 대상이다: 이전에는 이 경로가 L0만 돌아 애초에 클릭이 없었지만, 이제는
    L1이 기본으로 켜지므로 가드가 실제로 발화해야 한다.
    """
    scout_calls: list[str] = []
    original_scout = Scout.scout

    def spy_scout(self, **kwargs):
        scout_calls.append(kwargs.get("web_target_id", "?"))
        return original_scout(self, **kwargs)

    monkeypatch.setattr(Scout, "scout", spy_scout)

    runner = BatchRunner(out_dir=tmp_path / "out", fixture_root=FIXTURES, batch_size=5)
    manifests = runner.run([_login_target()], execution_mode="FIXTURE")

    assert scout_calls == [], "기본 경로인데 가드가 걸린 target에서 Scout.scout 이 호출됐다"
    result = manifests[0].results[0]
    assert result["outcome"] == TargetOutcome.ACCOUNT_ACTION_BLOCKED.value
    assert result["attempts"] == 1, "가드 위반은 재시도 대상이 아니다"


def test_default_run_does_not_click_any_forbidden_selector(tmp_path, monkeypatch):
    """더 낮은 층 — playwright `Page.click`이 이 target에 대해 기본 경로에서도
    한 번도 불리지 않았다는 것을 spy로 증명한다."""
    from playwright.sync_api import Page

    click_calls: list[str] = []
    original_click = Page.click

    def spy_click(self, selector, *args, **kwargs):
        click_calls.append(selector)
        return original_click(self, selector, *args, **kwargs)

    monkeypatch.setattr(Page, "click", spy_click)

    runner = BatchRunner(out_dir=tmp_path / "out", fixture_root=FIXTURES, batch_size=5)
    runner.run([_login_target()], execution_mode="FIXTURE")

    assert click_calls == [], f"기본 경로에서 클릭이 발생했다: {click_calls}"


# ── 2. 기본 경로가 실제로 L0 + L1을 함께 실행한다(양성 경로) ────────────────────
def test_default_run_actually_invokes_scout_for_a_benign_target(tmp_path):
    """가드에 걸리지 않는 target은 기본 경로에서 `scout_invoked=True`가 되어야 한다
    — 이전 기본값(L0-only)이었다면 이 결과 dict에 `scout_invoked` 키 자체가 없었다.
    L0 관측도 함께 보존된다는 것(`"l0"` 키)까지 확인한다.
    """
    runner = BatchRunner(out_dir=tmp_path / "out", fixture_root=FIXTURES, batch_size=5)
    manifests = runner.run([_query_target()], execution_mode="FIXTURE")

    result = manifests[0].results[0]
    detail = result["detail"]
    assert detail.get("scout_invoked") is True, (
        f"기본 경로인데 L1(Scout)이 호출되지 않았다: {detail}"
    )
    assert "l0" in detail, "L0 관측이 L1 결과에 보존되지 않았다"
    assert detail["l0"]["measurement_status"] == "MEASURED"
    # endpoint_definition 이 None 이므로 (codebook 미동결) 끝내 endpoint 에는
    # 도달하지 못한다 — 이것은 실패가 아니라 이 러너의 설계대로 정직한 결과다.
    assert result["outcome"] in (
        TargetOutcome.UNRESOLVED.value,
        TargetOutcome.MEASURED.value,
    )


def test_default_run_calls_scout_scout_directly_for_a_benign_target(tmp_path, monkeypatch):
    """`scout_invoked` 플래그(위 테스트)는 executor의 자체 보고일 뿐이다 — 이 테스트는
    한 층 더 내려가 `Scout.scout` 자체가 **기본 경로에서** 실제로 호출됐다는 것을
    spy로 직접 증명한다(독립 검증에서 지적된 정확한 회귀 표면: `_default_fixture_
    executor`가 `run_l0`만 부르고 `Scout`를 구성조차 하지 않았던 버그).
    """
    scout_calls: list[str] = []
    original_scout = Scout.scout

    def spy_scout(self, **kwargs):
        scout_calls.append(kwargs.get("web_target_id", "?"))
        return original_scout(self, **kwargs)

    monkeypatch.setattr(Scout, "scout", spy_scout)

    runner = BatchRunner(out_dir=tmp_path / "out", fixture_root=FIXTURES, batch_size=5)
    runner.run([_query_target()], execution_mode="FIXTURE")  # target_executor 미지정

    assert scout_calls == [_query_target().target_id], (
        f"기본 경로(target_executor 미지정)에서 Scout.scout 이 호출되지 않았다: {scout_calls}"
    )


# ── 3. 엔진 자체의 구조적 gate 판별 — 클릭 0회로 AUTH_GATE를 판정한다 ────────────
def test_default_run_isolates_structural_auth_gate_with_zero_clicks(tmp_path, monkeypatch):
    """`auth_identity_gate.html`의 후보 텍스트는 가드의 현재 사전에 걸리지 않는다
    (아래에서 그 전제 자체도 재확인한다) — 그런데도 Scout는 랜딩 자체에서 gate를
    판별해 **activation 0회**로 AUTH_GATE_REACHED를 낸다. 계정 행동 가드가 없어도
    안전한 이유는 애초에 클릭이 발생하지 않기 때문이라는 것을 click spy로 증명한다.
    """
    from landing_accessibility.e001_runner.guard import screen_candidates
    from landing_accessibility.engine.evidence import EvidenceRun
    from landing_accessibility.engine.firewall import ExecutionMode
    from landing_accessibility.engine.l0_collector import FixtureTarget, L0Collector
    from landing_accessibility.engine.vocabulary import InteractionArchetype
    from playwright.sync_api import Page

    # 전제 확인: 이 fixture의 L0 후보는 가드를 통과한다(그래서 Scout가 실제로 만들어진다).
    probe_run = EvidenceRun.create(
        tmp_path / "probe_evidence",
        "probe-identity-gate",
        execution_mode=ExecutionMode.FIXTURE,
    )
    collector = L0Collector(probe_run, fixture_root=FIXTURES, execution_mode=ExecutionMode.FIXTURE)
    l0 = collector.collect(
        FixtureTarget(
            web_target_id="probe",
            fixture="auth_identity_gate.html",
            archetype=InteractionArchetype.COMMUNICATION_ENTRY,
        )
    )
    probe_run.seal()
    risk = screen_candidates(l0.as_dict().get("primary_action_candidates") or [])
    assert risk is None, (
        f"이 테스트의 전제가 깨졌다 — 가드가 이미 이 후보를 막는다: {risk}. "
        "그렇다면 아래 검증은 '가드가 막았다'는 다른 이야기가 되어 이 테스트의 "
        "목적(가드 없이도 클릭 0회로 안전하다)과 어긋난다."
    )

    click_calls: list[str] = []
    original_click = Page.click

    def spy_click(self, selector, *args, **kwargs):
        click_calls.append(selector)
        return original_click(self, selector, *args, **kwargs)

    monkeypatch.setattr(Page, "click", spy_click)

    runner = BatchRunner(out_dir=tmp_path / "out", fixture_root=FIXTURES, batch_size=5)
    manifests = runner.run([_identity_target()], execution_mode="FIXTURE")

    assert click_calls == [], (
        f"구조적 gate 가 랜딩에서 이미 판별됐는데 클릭이 발생했다: {click_calls}"
    )
    result = manifests[0].results[0]
    assert result["detail"].get("scout_invoked") is True, "가드를 통과했으면 Scout는 호출돼야 한다"
    assert result["outcome"] == TargetOutcome.AUTH_GATE.value
    # `depth.gate_outcome`은 이 archetype(COMMUNICATION_ENTRY)에서 IDENTITY_VERIFICATION
    # gate를 endpoint로 승격시키지 않는다 — 개인정보(주민등록번호 등) 입력이 요구되면
    # `PERSONAL_DATA_REQUIRED`, 아니면 `AUTH_GATE_REACHED`다. 이 fixture는 주민등록번호
    # 필드를 갖고 있으므로 전자다. 둘 다 `outcomes.map_engine_result`에서 같은
    # `TargetOutcome.AUTH_GATE`로 격리된다는 것이 이 테스트가 실제로 지키는 계약이다.
    assert result["detail"]["endpoint_status"] in ("AUTH_GATE_REACHED", "PERSONAL_DATA_REQUIRED")


# ── 4. 배치 격리 — gate/guard 로 끝난 target 이 있어도 배치는 끝까지 순회한다 ────
def test_default_run_isolates_gate_and_guard_targets_without_stopping_the_batch(tmp_path):
    targets = [_login_target(), _identity_target(), _query_target()]
    runner = BatchRunner(out_dir=tmp_path / "out", fixture_root=FIXTURES, batch_size=5)
    manifests = runner.run(targets, execution_mode="FIXTURE")

    assert len(manifests) == 1
    results = {r["target_id"]: r for r in manifests[0].results}
    assert set(results) == {t.target_id for t in targets}
    assert (
        results[_login_target().target_id]["outcome"] == TargetOutcome.ACCOUNT_ACTION_BLOCKED.value
    )
    assert results[_identity_target().target_id]["outcome"] == TargetOutcome.AUTH_GATE.value

    ledger_check = runner.ledger.verify_chain()
    assert ledger_check["status"] == "OK"


# ── 5. l1_executor 별칭이 여전히 명시적으로 주입 가능하고, 기본값과 동일하다 ──────
def test_l1_executor_alias_is_identical_to_default_path(tmp_path):
    """하위 호환 — `target_executor=runner.l1_executor`를 명시하는 기존 호출부는
    여전히 동작하고, 아무것도 넘기지 않은 기본 경로와 같은 outcome 을 낸다.
    """
    runner_default = BatchRunner(out_dir=tmp_path / "default", fixture_root=FIXTURES, batch_size=5)
    manifests_default = runner_default.run([_login_target()], execution_mode="FIXTURE")

    runner_explicit = BatchRunner(
        out_dir=tmp_path / "explicit", fixture_root=FIXTURES, batch_size=5
    )
    manifests_explicit = runner_explicit.run(
        [_login_target()], execution_mode="FIXTURE", target_executor=runner_explicit.l1_executor
    )

    assert (
        manifests_default[0].results[0]["outcome"]
        == manifests_explicit[0].results[0]["outcome"]
        == TargetOutcome.ACCOUNT_ACTION_BLOCKED.value
    )
