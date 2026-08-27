"""E000 실제 수집 게이트 — `REAL_TARGET` + `ExecutionScope` 경로.

이 파일이 고정하는 것은 두 방향이다:

1. **열린다** — P0_RELEASE 가 실제로 RELEASED 이고 target 이 E000_FAST allowlist 안일 때
   `REAL_TARGET` + `E000_FAST` 가 통과한다.
2. **닫힌다** — 릴리스 문서가 없거나·status 가 다르거나·`promoted_main_sha` 가 비었거나·
   `e000_allowed` 가 false 이면 차단된다. scope 없는 `REAL_TARGET` 은 어떤 경우에도 차단.
   allowlist 밖 target 도 차단. FIXTURE 는 여전히 file:// 전용.

**이 파일의 어떤 테스트도 실제 서비스에 접속하지 않는다.** 항해를 수행하는 함수는
호출하지 않고, 항해 **직전의 판정 함수**와 주입된 executor 만 검사한다.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import pytest

REPO = Path(__file__).resolve().parents[1]
RESEARCH = REPO / "research" / "landing_accessibility"
sys.path.insert(0, str(RESEARCH / "src"))

from landing_accessibility.e001_runner import layer_firewall  # noqa: E402
from landing_accessibility.e001_runner.batch import BatchRunner  # noqa: E402
from landing_accessibility.e001_runner.layer_firewall import (  # noqa: E402
    BatchRealTargetBlockedError,
    assert_batch_execution_mode_safe,
)
from landing_accessibility.e001_runner.plan import (  # noqa: E402
    TargetSpec,
    validate_real_target_scope_allowlist,
)
from landing_accessibility.engine import firewall  # noqa: E402
from landing_accessibility.engine.firewall import (  # noqa: E402
    ExecutionMode,
    ExecutionScope,
    ExecutionScopeBlockedError,
    FirewallError,
    NavigationBlockedError,
    RealTargetBlockedError,
    ReleaseDocument,
    TargetNotAllowlistedError,
    UnknownExecutionScopeError,
    assert_mode_allowed,
    assert_navigation_allowed,
    assert_real_target_scope_allowed,
    evaluate_execution_scope,
    firewall_state,
    load_e000_fast_allowlist,
)
from landing_accessibility.engine.provenance import (  # noqa: E402
    REAL_TARGET_STATUS,
    ProvenanceError,
    RealTargetProvenance,
    validate_provenance,
)

FIXTURES = RESEARCH / "fixtures"

RELEASED_DOC: dict[str, Any] = {
    "status": "RELEASED",
    "promoted_main_sha": "bc0b7a087faf2328cbafdfa9b40bd426c5080d7d",
    "e000_allowed": True,
    "e001_allowed": True,
    "real_target_allowed": True,
}


def _doc(payload: dict[str, Any] | None, error: str | None = None) -> ReleaseDocument:
    return ReleaseDocument(
        ref="test-ref", path="test-path", data=payload, sha256="0" * 64, error=error
    )


@pytest.fixture(autouse=True)
def _clear_caches() -> Any:
    firewall.reset_release_cache()
    firewall.reset_allowlist_cache()
    yield
    firewall.reset_release_cache()
    firewall.reset_allowlist_cache()


def _inject(monkeypatch: pytest.MonkeyPatch, doc: ReleaseDocument) -> None:
    monkeypatch.setattr(firewall, "read_release_document", lambda **_kw: doc)


# ── 1. 무제한 REAL_TARGET 은 여전히 hard fail ────────────────────────────────
@pytest.mark.parametrize("value", [ExecutionMode.REAL_TARGET, "REAL_TARGET"])
def test_real_target_without_scope_is_still_hard_fail(value: object) -> None:
    with pytest.raises(RealTargetBlockedError):
        assert_mode_allowed(value)


def test_real_target_without_scope_blocks_navigation_before_url_is_parsed() -> None:
    with pytest.raises(RealTargetBlockedError):
        assert_navigation_allowed("REAL_TARGET", "https" + "://www.example.co.kr/")


def test_real_target_permitted_is_permanently_false() -> None:
    """무제한 경로를 여는 스위치는 존재하지 않는다."""
    assert firewall.real_target_permitted() is False
    assert firewall_state()["real_target_permitted"] is False


def test_batch_layer_blocks_real_target_without_scope() -> None:
    with pytest.raises(BatchRealTargetBlockedError):
        assert_batch_execution_mode_safe("REAL_TARGET")


def test_batch_runner_blocks_real_target_without_scope(tmp_path: Path) -> None:
    runner = BatchRunner(out_dir=tmp_path / "out", fixture_root=FIXTURES)

    def spy(_target: TargetSpec) -> dict[str, Any]:
        raise AssertionError("scope 없는 REAL_TARGET 이 executor 까지 도달했다")

    with pytest.raises(BatchRealTargetBlockedError):
        runner.run(_allowlisted_plan()[:1], execution_mode="REAL_TARGET", target_executor=spy)


# ── 2. P0_RELEASE 런타임 검증 — 두 방향 ──────────────────────────────────────
def test_scope_blocked_when_release_document_is_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    _inject(monkeypatch, _doc(None, error="git show 실패"))
    verdict = evaluate_execution_scope(ExecutionScope.E000_FAST)
    assert verdict.allowed is False
    with pytest.raises(ExecutionScopeBlockedError):
        assert_real_target_scope_allowed(ExecutionScope.E000_FAST)


@pytest.mark.parametrize(
    "mutation",
    [
        {"status": "CANDIDATE_NOT_FROZEN"},
        {"status": None},
        {"promoted_main_sha": None},
        {"promoted_main_sha": ""},
        {"e000_allowed": False},
        {"e000_allowed": None},
        {"real_target_allowed": False},
    ],
)
def test_scope_blocked_when_release_condition_is_unmet(
    monkeypatch: pytest.MonkeyPatch, mutation: dict[str, Any]
) -> None:
    _inject(monkeypatch, _doc({**RELEASED_DOC, **mutation}))
    verdict = evaluate_execution_scope(ExecutionScope.E000_FAST)
    assert verdict.allowed is False, verdict.reason
    with pytest.raises(ExecutionScopeBlockedError):
        assert_mode_allowed("REAL_TARGET", scope=ExecutionScope.E000_FAST)


def test_scope_allowed_when_release_document_is_released(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _inject(monkeypatch, _doc(RELEASED_DOC))
    verdict = evaluate_execution_scope(ExecutionScope.E000_FAST)
    assert verdict.allowed is True
    assert verdict.promoted_main_sha == RELEASED_DOC["promoted_main_sha"]
    assert assert_mode_allowed("REAL_TARGET", scope="E000_FAST") is ExecutionMode.REAL_TARGET


def test_live_p0_release_document_is_read_from_a_git_ref_not_the_worktree() -> None:
    """실제 릴리스 문서를 `git show` 로 읽는다 — 워킹트리 파일이 아니다."""
    doc = firewall.read_release_document(use_cache=False)
    assert doc.ref == firewall.P0_RELEASE_REF
    assert doc.path == firewall.P0_RELEASE_PATH
    # 문서를 읽지 못했다면 게이트는 닫혀 있어야 한다 (fail-closed).
    if doc.data is None:
        assert evaluate_execution_scope(ExecutionScope.E000_FAST).allowed is False


def test_e001_full_scope_is_blocked_without_its_own_release_document(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """E001 전체 개방은 **자기 릴리스 문서**가 있어야만 열린다.

    2026-08-27 A 가 `E001_RELEASE.json` 을 발행해 이 scope 가 실제로 열렸다. 그래서
    이 테스트는 "지금 닫혀 있다" 가 아니라 **"문서가 없으면 닫힌다"** 를 고정한다 —
    P0_RELEASE 하나로는 E001 이 열리지 않는다는 사실이 여기 남는다.
    E001 이 열린 상태의 판정은 `tests/test_e001_full_scope_gate.py` 가 다룬다.
    """
    _inject(monkeypatch, _doc(None, error="git show 실패"))
    verdict = evaluate_execution_scope(ExecutionScope.E001_FULL)
    assert verdict.allowed is False
    with pytest.raises(ExecutionScopeBlockedError):
        assert_mode_allowed("REAL_TARGET", scope=ExecutionScope.E001_FULL)


def test_unknown_scope_is_not_absorbed() -> None:
    """`None` 은 "scope 없음"(= hard fail)이고, 그 밖의 모르는 값은 어휘 위반이다."""
    for value in ("E999", "", 7):
        with pytest.raises(UnknownExecutionScopeError):
            assert_mode_allowed("REAL_TARGET", scope=value)
    with pytest.raises(RealTargetBlockedError):
        assert_mode_allowed("REAL_TARGET", scope=None)


# ── 3. allowlist 강제 ────────────────────────────────────────────────────────
def _allowlist() -> Any:
    return load_e000_fast_allowlist()


def _allowlisted_plan() -> list[TargetSpec]:
    allowlist = _allowlist()
    target_id = sorted(allowlist.target_ids)[0]
    url = next(
        u
        for u in sorted(allowlist.official_urls)
        if u  # 첫 target 의 URL 이 아니어도 무방
    )
    return [
        TargetSpec(
            target_id=target_id,
            canonical_service_key=sorted(allowlist.canonical_service_keys)[0],
            official_url=url,
            interaction_archetype="QUERY",
        )
    ]


def test_allowlist_has_exactly_the_frozen_six_targets() -> None:
    allowlist = _allowlist()
    assert len(allowlist.target_ids) == 6
    assert len(allowlist.hosts) >= 1
    assert allowlist.plan_sha256


def test_target_outside_allowlist_is_blocked(monkeypatch: pytest.MonkeyPatch) -> None:
    _inject(monkeypatch, _doc(RELEASED_DOC))
    with pytest.raises(TargetNotAllowlistedError):
        assert_real_target_scope_allowed(ExecutionScope.E000_FAST, target_id="wtg_not_in_plan")


def test_host_outside_allowlist_is_blocked(monkeypatch: pytest.MonkeyPatch) -> None:
    _inject(monkeypatch, _doc(RELEASED_DOC))
    with pytest.raises(TargetNotAllowlistedError):
        assert_real_target_scope_allowed(
            ExecutionScope.E000_FAST, url="https" + "://evil.example.com/"
        )


def test_allowlist_check_requires_an_identifier(monkeypatch: pytest.MonkeyPatch) -> None:
    _inject(monkeypatch, _doc(RELEASED_DOC))
    with pytest.raises(TargetNotAllowlistedError):
        firewall.assert_target_allowlisted(ExecutionScope.E000_FAST)


def test_allowlisted_target_passes(monkeypatch: pytest.MonkeyPatch) -> None:
    _inject(monkeypatch, _doc(RELEASED_DOC))
    allowlist = _allowlist()
    target_id = sorted(allowlist.target_ids)[0]
    verdict = assert_real_target_scope_allowed(ExecutionScope.E000_FAST, target_id=target_id)
    assert verdict.allowed is True


def test_plan_level_allowlist_validation_rejects_a_stranger(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _inject(monkeypatch, _doc(RELEASED_DOC))
    plan = [
        *_allowlisted_plan(),
        TargetSpec(
            target_id="wtg_stranger",
            canonical_service_key="stranger",
            official_url="https" + "://stranger.example.com/",
            interaction_archetype="QUERY",
        ),
    ]
    with pytest.raises(TargetNotAllowlistedError):
        validate_real_target_scope_allowlist(plan, scope=ExecutionScope.E000_FAST)


# ── 4. 항해 판정 ─────────────────────────────────────────────────────────────
def test_real_target_navigation_allows_only_network_schemes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _inject(monkeypatch, _doc(RELEASED_DOC))
    allowlist = _allowlist()
    url = sorted(allowlist.official_urls)[0]
    target_id = next(iter(sorted(allowlist.target_ids)))
    resolved = assert_navigation_allowed("REAL_TARGET", url, scope="E000_FAST", target_id=target_id)
    assert resolved == url


def test_real_target_navigation_refuses_file_scheme(monkeypatch: pytest.MonkeyPatch) -> None:
    """실제 수집 경로가 로컬 파일을 여는 일은 없다 — 두 경로는 서로의 URL 을 못 연다."""
    _inject(monkeypatch, _doc(RELEASED_DOC))
    with pytest.raises(NavigationBlockedError):
        assert_navigation_allowed(
            "REAL_TARGET", f"file://{FIXTURES / 'simple_article.html'}", scope="E000_FAST"
        )


def test_real_target_navigation_refuses_non_allowlisted_host(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _inject(monkeypatch, _doc(RELEASED_DOC))
    with pytest.raises(TargetNotAllowlistedError):
        assert_navigation_allowed(
            "REAL_TARGET", "https" + "://evil.example.com/x", scope="E000_FAST"
        )


# ── 5. FIXTURE 회귀 방지 ─────────────────────────────────────────────────────
@pytest.mark.parametrize(
    "url",
    [
        "https" + "://www.example.co.kr/",
        "http" + "://example.com",
        "ws://example.com/socket",
        "data:text/html,<h1>x</h1>",
    ],
)
def test_fixture_mode_still_refuses_every_network_scheme(url: str) -> None:
    with pytest.raises(NavigationBlockedError):
        assert_navigation_allowed(ExecutionMode.FIXTURE, url)


def test_fixture_mode_cannot_be_widened_with_a_scope() -> None:
    """scope 는 REAL_TARGET 의 것이다 — FIXTURE 에 붙이면 실패한다."""
    with pytest.raises(FirewallError):
        assert_mode_allowed(ExecutionMode.FIXTURE, scope="E000_FAST")
    with pytest.raises(FirewallError):
        assert_navigation_allowed(
            ExecutionMode.FIXTURE, "https" + "://www.example.co.kr/", scope="E000_FAST"
        )


def test_shadow_dry_run_still_never_navigates() -> None:
    with pytest.raises(NavigationBlockedError):
        assert_navigation_allowed(
            ExecutionMode.SHADOW_DRY_RUN, f"file://{FIXTURES / 'simple_article.html'}"
        )


def test_execution_mode_vocabulary_is_still_three_values() -> None:
    """A2 규칙 S-3 — 실제 수집을 위해 네 번째 enum 값을 만들지 않았다."""
    assert sorted(m.value for m in ExecutionMode) == [
        "FIXTURE",
        "REAL_TARGET",
        "SHADOW_DRY_RUN",
    ]


# ── 6. 수집기 타입/모드 짝 ───────────────────────────────────────────────────
def test_collector_refuses_a_fixture_target_in_real_mode(tmp_path: Path) -> None:
    from landing_accessibility.engine.l0_collector import FixtureTarget, L0Collector
    from landing_accessibility.engine.vocabulary import InteractionArchetype

    collector = L0Collector.__new__(L0Collector)
    collector.execution_mode = ExecutionMode.REAL_TARGET
    with pytest.raises(ValueError, match="RealServiceTarget"):
        collector._assert_target_matches_mode(
            FixtureTarget(
                web_target_id="x",
                fixture="simple_article.html",
                archetype=InteractionArchetype.QUERY,
            )
        )


def test_collector_refuses_a_real_target_in_fixture_mode() -> None:
    from landing_accessibility.engine.l0_collector import L0Collector, RealServiceTarget
    from landing_accessibility.engine.vocabulary import InteractionArchetype

    collector = L0Collector.__new__(L0Collector)
    collector.execution_mode = ExecutionMode.FIXTURE
    with pytest.raises(ValueError, match="RealServiceTarget"):
        collector._assert_target_matches_mode(
            RealServiceTarget(
                web_target_id="x",
                official_url="https" + "://example.com/",
                archetype=InteractionArchetype.QUERY,
            )
        )


# ── 7. 계정 행동 가드가 실제 수집 경로에서도 작동하는가 ────────────────────────
def test_account_action_guard_blocks_before_scout_is_constructed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from landing_accessibility.e001_runner import real_executor
    from landing_accessibility.e001_runner.outcomes import TargetOutcome

    monkeypatch.setattr(
        real_executor,
        "run_l0_real",
        lambda target, **_kw: {
            "observation_id": "obs-1",
            "primary_action_candidates": [
                {"selector": "#a", "accessible_name": "로그인", "visible_text": "로그인"}
            ],
        },
    )

    def exploding_scout(*_a: object, **_k: object) -> None:
        raise AssertionError("가드가 막았어야 하는데 Scout 가 만들어졌다")

    monkeypatch.setattr(real_executor, "Scout", exploding_scout)

    result = real_executor.run_l1_if_safe_real(
        TargetSpec(
            target_id="wtg_x",
            canonical_service_key="x",
            official_url="https" + "://example.com/",
            interaction_archetype="QUERY",
        ),
        run=None,  # type: ignore[arg-type]
    )
    assert result["outcome"] == TargetOutcome.ACCOUNT_ACTION_BLOCKED.value
    assert result["scout_invoked"] is False
    assert result["l0"]["observation_id"] == "obs-1"


# ── 8. 실제 수집 provenance ──────────────────────────────────────────────────
def test_real_target_provenance_declares_real_measurement(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _inject(monkeypatch, _doc(RELEASED_DOC))
    block = RealTargetProvenance.for_scope(ExecutionScope.E000_FAST).as_dict()
    assert block["status"] == REAL_TARGET_STATUS
    assert block["real_target_measurement"] is True
    assert block["created_before_p0_close"] is False
    assert block["fixture_only"] is False
    assert block["promoted_main_sha"] == RELEASED_DOC["promoted_main_sha"]
    assert block["execution_scope"] == "E000_FAST"
    validate_provenance(block)


def test_real_target_provenance_rejects_a_false_measurement_flag() -> None:
    block = {
        "status": REAL_TARGET_STATUS,
        "base_sha": "abc1234",
        "created_at": "2026-08-27T00:00:00.000000Z",
        "created_before_p0_close": False,
        "authoritative": True,
        "real_target_outcome_used": True,
        "requires_post_p0_reconciliation": False,
        "protocol_version": "v2.0-pc-fixture-1",
        "execution_scope": "E000_FAST",
        "promoted_main_sha": "bc0b7a0",
        "fixture_only": False,
        "real_target_measurement": False,
    }
    with pytest.raises(ProvenanceError, match="real_target_measurement"):
        validate_provenance(block)


def test_protocol_version_is_shared_by_e000_and_e001() -> None:
    """E000 evidence 를 E001 batch-0 으로 재사용하려면 프로토콜이 같아야 한다."""
    from landing_accessibility.engine.provenance import PROTOCOL_VERSION

    assert RealTargetProvenance().protocol_version == PROTOCOL_VERSION
    from landing_accessibility.engine.provenance import ShadowProvenance

    assert ShadowProvenance().protocol_version == PROTOCOL_VERSION


# ── 9. 배치 경로 (실제 접속 없이 executor 주입) ───────────────────────────────
def test_real_batch_seals_with_real_provenance_and_keeps_the_safety_caps(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _inject(monkeypatch, _doc(RELEASED_DOC))
    monkeypatch.setattr(layer_firewall, "batch_layer_real_target_released", lambda *_a: True)

    calls: list[str] = []

    def injected(target: TargetSpec) -> dict[str, Any]:
        calls.append(target.target_id)
        return {"measurement_status": "MEASURED", "endpoint_status": "REACHED"}

    runner = BatchRunner(out_dir=tmp_path / "out", fixture_root=FIXTURES)
    manifests = runner.run(
        _allowlisted_plan(),
        execution_mode="REAL_TARGET",
        execution_scope=ExecutionScope.E000_FAST,
        target_executor=injected,
    )
    assert len(calls) == 1
    assert len(manifests) == 1
    manifest = manifests[0].as_dict()
    assert manifest["execution_mode"] == "REAL_TARGET"
    assert manifest["provenance"]["real_target_measurement"] is True
    assert manifest["provenance"]["max_retries_per_target"] == 1
    assert runner.target_wall_clock_cap_s == 360.0


def test_real_batch_refuses_a_plan_with_a_non_allowlisted_target(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _inject(monkeypatch, _doc(RELEASED_DOC))
    monkeypatch.setattr(layer_firewall, "batch_layer_real_target_released", lambda *_a: True)

    def spy(_target: TargetSpec) -> dict[str, Any]:
        raise AssertionError("allowlist 밖 target 이 executor 까지 도달했다")

    runner = BatchRunner(out_dir=tmp_path / "out", fixture_root=FIXTURES)
    plan = [
        TargetSpec(
            target_id="wtg_stranger",
            canonical_service_key="stranger",
            official_url="https" + "://stranger.example.com/",
            interaction_archetype="QUERY",
        )
    ]
    with pytest.raises(TargetNotAllowlistedError):
        runner.run(
            plan,
            execution_mode="REAL_TARGET",
            execution_scope=ExecutionScope.E000_FAST,
            target_executor=spy,
        )


# ── 10. 금지 문자열 ──────────────────────────────────────────────────────────
def test_real_batch_output_never_carries_the_forbidden_e000_label(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """오늘의 run 라벨은 `E000_FAST_*` 뿐이다 — canonical gate 이름이 **산출물에** 새면 반려다.

    금지는 산출물(라벨·파일명·JSON 필드) 차원이다. 소스 주석이 canonical gate 를
    **인용**하는 것은 금지 대상이 아니므로 여기서는 실제로 봉인된 manifest 와 run_id 만
    검사한다.
    """
    import json

    forbidden = "E000_V2" + "_VALIDATED"
    _inject(monkeypatch, _doc(RELEASED_DOC))
    monkeypatch.setattr(layer_firewall, "batch_layer_real_target_released", lambda *_a: True)

    runner = BatchRunner(out_dir=tmp_path / "out", fixture_root=FIXTURES)
    manifests = runner.run(
        _allowlisted_plan(),
        execution_mode="REAL_TARGET",
        execution_scope=ExecutionScope.E000_FAST,
        target_executor=lambda _t: {"measurement_status": "MEASURED"},
    )
    payload = json.dumps([m.as_dict() for m in manifests], ensure_ascii=False)
    assert forbidden not in payload
    ledger_files = list((tmp_path / "out").rglob("*"))
    for path in ledger_files:
        assert forbidden not in path.name
        if path.is_file():
            assert forbidden not in path.read_text(encoding="utf-8", errors="ignore")
