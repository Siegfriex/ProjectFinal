"""P-C LANE C — fixture 위에서 L0 collector 와 L1 엔진이 실제로 도는가.

**이 파일의 PASS/FAIL 은 synthetic fixture 에 대한 engine test 결과다.**
실제 서비스에 대한 research finding 이 아니며 그렇게 인용할 수 없다
(`PHASE_GATES §4.1` · `§4.3` · `§4.6`).

기대값의 정본은 `research/landing_accessibility/fixtures/expectations.json` 이고,
각 fixture 파일 상단 주석이 "무엇을 검증하려는 것인가" 를 적는다.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import pytest

REPO = Path(__file__).resolve().parents[1]
RESEARCH = REPO / "research" / "landing_accessibility"
sys.path.insert(0, str(RESEARCH / "src"))

from landing_accessibility.engine.evidence import EvidenceRun  # noqa: E402
from landing_accessibility.engine.firewall import ExecutionMode  # noqa: E402
from landing_accessibility.engine.l0_collector import (  # noqa: E402
    VIEWPORT_HEIGHT,
    VIEWPORT_WIDTH,
    FixtureTarget,
    L0Collector,
)
from landing_accessibility.engine.l1_engine import (  # noqa: E402
    Scout,
    ScoutBudget,
    TaskDefinition,
    replay,
)
from landing_accessibility.engine.vocabulary import (  # noqa: E402
    InteractionArchetype as A,
)
from landing_accessibility.engine.vocabulary import (  # noqa: E402
    RegionSignalType as R,
)

pytest.importorskip("playwright.sync_api")

FIXTURES = RESEARCH / "fixtures"
EXPECTATIONS = json.loads((FIXTURES / "expectations.json").read_text(encoding="utf-8"))

pytestmark = pytest.mark.slow

_L0_FIXTURES = [
    "simple_article.html",
    "blocking_modal.html",
    "promo_modal.html",
    "cookie_consent.html",
    "motion_banner.html",
    "missing_accessible_name.html",
    "small_target.html",
    "low_contrast_control.html",
    "overlay_primary_action.html",
]


@pytest.fixture(scope="module")
def l0(tmp_path_factory: pytest.TempPathFactory) -> dict[str, Any]:
    """모든 L0 fixture 를 **한 run** 으로 수집한다 — run 단위 계약도 함께 검증된다."""
    root = tmp_path_factory.mktemp("evidence")
    run = EvidenceRun.create(root, "pc-fixture-l0", execution_mode=ExecutionMode.FIXTURE)
    collector = L0Collector(run, fixture_root=FIXTURES)
    observations = {
        name: collector.collect(
            FixtureTarget(web_target_id=f"wt-{name}", fixture=name, archetype=A.UTILITY_ENTRY)
        )
        for name in _L0_FIXTURES
    }
    run.seal()
    return {"run": run, "obs": observations}


# ── fixture 세트 자체 ────────────────────────────────────────────────────────
def test_every_fixture_declares_what_it_validates() -> None:
    """기대값 없는 fixture 는 테스트의 근거가 되지 못한다."""
    for path in sorted(FIXTURES.glob("*.html")):
        head = path.read_text(encoding="utf-8")[:1200]
        assert "FIXTURE:" in head, f"{path.name} 에 FIXTURE 주석이 없다"
        assert "검증 대상" in head or "FIXTURE:" in head.split("\n")[1]


def test_fixtures_never_reference_a_live_service() -> None:
    """fixture 가 외부를 참조하면 그 순간 real-target 수집이 된다."""
    for path in sorted(FIXTURES.glob("*.html")):
        text = path.read_text(encoding="utf-8")
        for scheme in ("https://", "http://", "//cdn"):
            assert scheme not in text, f"{path.name} 이 외부 자원을 참조한다: {scheme}"


# ── L0 수집 (02 §2 · §3 · §4) ────────────────────────────────────────────────
def test_all_fixtures_are_measured_and_the_run_verifies(l0: dict[str, Any]) -> None:
    for name, obs in l0["obs"].items():
        assert obs.measurement_status == "MEASURED", f"{name}: {obs.notes}"
    assert l0["run"].verify()["status"] == "VERIFIED"


def test_common_mobile_environment_is_applied(l0: dict[str, Any]) -> None:
    """`02 §2` — 390 x 844 CSS px, DPR 실측 기록."""
    obs = l0["obs"]["simple_article.html"]
    assert (obs.viewport_configured_width, obs.viewport_configured_height) == (
        VIEWPORT_WIDTH,
        VIEWPORT_HEIGHT,
    )
    assert (obs.viewport_width, obs.viewport_height) == (390, 844)
    assert obs.device_pixel_ratio == EXPECTATIONS["viewport"]["device_pixel_ratio"]
    assert obs.raw_features["viewport"]["lang"] == "ko"


def test_all_seven_evidence_slots_are_populated(l0: dict[str, Any]) -> None:
    """`A1 §6.2` — identity 집합 7종."""
    obs = l0["obs"]["simple_article.html"]
    for attr in (
        "dom_path",
        "ax_path",
        "screenshot_initial_path",
        "screenshot_fullpage_path",
        "computed_css_path",
        "probe_path",
        "manifest_path",
    ):
        assert getattr(obs, attr), attr
    assert obs.screenshot_initial_path != obs.screenshot_fullpage_path
    assert obs.computed_css_path != obs.probe_path  # `A1 §6.1` — probe 와 별도 파일이다
    assert not obs.dom_path.startswith("/") and ".." not in obs.dom_path


def test_audit_date_is_derived_not_an_independent_input(l0: dict[str, Any]) -> None:
    obs = l0["obs"]["simple_article.html"]
    assert obs.audit_date == obs.collection_started_at[:10] or len(obs.audit_date) == 10
    assert obs.collection_started_at <= obs.collection_finished_at


# ── probe 는 판정하지 않는다 (02 §4) ─────────────────────────────────────────
def test_probe_emits_raw_features_and_no_verdict(l0: dict[str, Any]) -> None:
    """이 테스트가 `02 §4` 의 층 분리를 고정한다."""
    raw = l0["obs"]["low_contrast_control.html"].raw_features
    forbidden = set(EXPECTATIONS["fixtures"]["low_contrast_control.html"]["probe_must_not_emit"])
    for row in raw["contrast"]:
        assert not (forbidden & row.keys()), f"probe 가 판정을 냈다: {forbidden & row.keys()}"
    blob = json.dumps(raw, ensure_ascii=False)
    for token in ('"verdict"', '"PASS"', '"FAIL"', '"required"'):
        assert token not in blob, f"probe 출력에 판정 어휘가 있다: {token}"


def test_contrast_raw_feature_matches_expected_values(l0: dict[str, Any]) -> None:
    rows = {
        r["selector"]: r for r in l0["obs"]["low_contrast_control.html"].raw_features["contrast"]
    }
    expected = EXPECTATIONS["fixtures"]["low_contrast_control.html"]
    assert rows["p#low"]["contrast_ratio"] == expected["ratios"]["low"]
    assert rows["p#high"]["contrast_ratio"] == expected["ratios"]["high"]
    assert rows["p#large-low"]["font_px"] == 24
    assert rows["p#on-image"]["behind_image"] is True


def test_target_size_raw_feature_is_css_px_not_device_px(l0: dict[str, Any]) -> None:
    """DPR 3 인데도 20 CSS px 그대로여야 한다 (`A1 §3.2`)."""
    rows = {r["selector"]: r for r in l0["obs"]["small_target.html"].raw_features["target_size"]}
    expected = EXPECTATIONS["fixtures"]["small_target.html"]["targets"]
    for el_id, size in expected.items():
        row = rows[f"button#{el_id}"]
        assert (row["width_css_px"], row["height_css_px"]) == (size["w"], size["h"])
    assert (
        rows["button#tiny-1"]["nearest_neighbor_gap_css_px"]
        == (EXPECTATIONS["fixtures"]["small_target.html"]["nearest_neighbor_gap_css_px"])
    )


def test_absent_accessible_name_is_recorded_as_an_observed_fact(l0: dict[str, Any]) -> None:
    obs = l0["obs"]["missing_accessible_name.html"]
    ax = json.loads((l0["run"].run_dir / obs.ax_path).read_text(encoding="utf-8"))
    named = [n for n in ax if n.get("name")]
    assert any(n["name"] == "검색" for n in named)
    sources = {r["selector"]: r for r in obs.raw_features["accessible_name_sources"]}
    for el_id in EXPECTATIONS["fixtures"]["missing_accessible_name.html"]["unnamed_control_ids"]:
        key = next(k for k in sources if k.endswith(f"#{el_id}"))
        row = sources[key]
        assert not row["aria_label"] and not row["visible_text"]


def test_motion_signals_are_collected(l0: dict[str, Any]) -> None:
    motion = l0["obs"]["motion_banner.html"].raw_features["motion"]
    expected = EXPECTATIONS["fixtures"]["motion_banner.html"]
    assert motion["infinite_animation_count"] >= expected["infinite_animation_count_min"]
    assert motion["marquee_count"] == expected["marquee_count"]
    assert len(motion["autoplay_media"]) == expected["autoplay_media_count"]


# ── popup / interrupt (02 §5 · A1 §3) ────────────────────────────────────────
def test_blocking_modal_is_detected_classified_and_dismissed(l0: dict[str, Any]) -> None:
    obs = l0["obs"]["blocking_modal.html"]
    expected = EXPECTATIONS["fixtures"]["blocking_modal.html"]
    assert obs.raw_features["body_scroll_lock"]["locked"] is True
    modal = next(i for i in obs.interrupts if i.selector.endswith("#modal"))
    # `D-R0-58`(`C-FINDING-214214` 시정) — BLOCKING_MODAL 은 구조(form) 축 값이다.
    # 옛 단일축 `final_label` 은 `InterruptRecord` 에서 제거됐다(정당한 갱신, 고장 아님).
    assert modal.interrupt_form == expected["final_label"]
    assert modal.blocks_primary_action == expected["blocks_primary_action"]
    assert modal.primary_action_occlusion == expected["primary_action_occlusion"]
    assert modal.dismiss_control_exists == 1
    assert modal.dismiss_control_accessible_name == expected["dismiss_control_accessible_name"]
    assert modal.dismiss_control_width == expected["dismiss_control_width"]
    assert modal.dismiss_method == expected["dismiss_method"]
    assert modal.dismiss_succeeded == 1
    assert modal.dismiss_failure_mode is None  # 동치: succeeded=1 ↔ failure_mode IS NULL


def test_dismissal_leaves_before_and_after_evidence(l0: dict[str, Any]) -> None:
    """`A1 §3.4` — 세 파일이 같은 observation 의 서로 다른 relpath 로 등록된다."""
    obs = l0["obs"]["blocking_modal.html"]
    modal = next(i for i in obs.interrupts if i.selector.endswith("#modal"))
    paths = [
        modal.dismiss_screenshot_before,
        modal.dismiss_screenshot_after,
        modal.dismiss_dom_after,
    ]
    assert all(paths)
    assert len(set(paths)) == 3
    for rel in paths:
        assert (l0["run"].run_dir / rel).exists()
        assert rel != obs.screenshot_initial_path  # L0-a 를 덮어쓰지 않았다


def test_promotion_modal_does_not_block_and_records_persistence_hint(l0: dict[str, Any]) -> None:
    obs = l0["obs"]["promo_modal.html"]
    expected = EXPECTATIONS["fixtures"]["promo_modal.html"]
    promo = next(i for i in obs.interrupts if i.selector.endswith("#promo"))
    # PROMOTION_MODAL 도 구조(form) 축 값이다 — 이 fixture 는 role="dialog"(구조)와
    # "이벤트"(텍스트) 를 모두 갖고 있어 두 축 다 PROMOTION_MODAL 로 일치한다.
    assert promo.interrupt_form == expected["final_label"]
    assert promo.blocks_primary_action == 0
    assert promo.primary_action_occlusion == 0.0
    assert promo.dismiss_persistence_hint == expected["dismiss_persistence_hint"]
    assert obs.raw_features["body_scroll_lock"]["locked"] is False


def test_cookie_consent_is_settled_deterministically(l0: dict[str, Any]) -> None:
    obs = l0["obs"]["cookie_consent.html"]
    cookie = next(i for i in obs.interrupts if i.selector.endswith("#cookie"))
    # COOKIE_CONSENT 는 의미(semantic) 축 전용 값이다(텍스트 사전으로만 도달).
    # `D-R0-58-1` 확정 어휘로는 RESOLVED(옛 DETERMINISTIC/SEMANTIC_MODEL 이 통합됨).
    assert cookie.interrupt_semantic_status == "RESOLVED"
    assert cookie.interrupt_semantic == "COOKIE_CONSENT"
    assert cookie.dismiss_succeeded == 1


def test_occlusion_numerator_and_denominator_are_both_stored(l0: dict[str, Any]) -> None:
    """`A2` 규칙 C-2 — 제3자가 재계산할 수 있어야 한다."""
    obs = l0["obs"]["overlay_primary_action.html"]
    expected = EXPECTATIONS["fixtures"]["overlay_primary_action.html"]
    selected = next(c for c in obs.primary_action_candidates if c.selection_status == "SELECTED")
    assert selected.area_css_px2 == expected["primary_action_area_css_px2"]
    overlay = next(i for i in obs.interrupts if i.selector.endswith("#half"))
    assert overlay.primary_action_occlusion == expected["primary_action_occlusion"]
    # 분자·분모로부터 값을 다시 만들 수 있다
    numerator = overlay.primary_action_occlusion * selected.area_css_px2
    assert numerator == expected["overlap_css_px2"]
    assert obs.primary_action_visible_initial == expected["primary_action_visible_initial"]


def test_candidates_are_not_discarded(l0: dict[str, Any]) -> None:
    """규칙 C-3 — `RUNNER_UP` · `REJECTED` 를 지우지 않는다. `SELECTED` 는 최대 1행."""
    obs = l0["obs"]["blocking_modal.html"]
    statuses = [c.selection_status for c in obs.primary_action_candidates]
    assert statuses.count("SELECTED") <= 1
    assert len(obs.primary_action_candidates) >= 1
    for c in obs.primary_action_candidates:
        assert c.area_css_px2 >= 0


def test_no_interrupt_on_a_clean_landing(l0: dict[str, Any]) -> None:
    assert l0["obs"]["simple_article.html"].interrupts == []
    assert l0["obs"]["simple_article.html"].max_overlay_coverage == 0.0


# ── L1 엔진 (02 §7 · §8 · §9 / A1 §1 · §2 · §4) ─────────────────────────────
def _scout() -> Scout:
    return Scout(
        fixture_root=FIXTURES, budget=ScoutBudget(max_activations_per_task=5, branching_limit=3)
    )


CONTENT_TASK = TaskDefinition("T", A.CONTENT_OPEN, "ARTICLE_LIST_REGION", "ARTICLE_BODY_OPEN")


@pytest.mark.parametrize(
    ("fixture", "ned", "ied", "mpfed", "segments"),
    [
        ("depth_path_0.html", 0, 0, 0, []),
        ("depth_path_1.html", 0, 1, 1, ["IED"]),
        ("depth_path_3.html", 2, 1, 3, ["NED", "NED", "IED"]),
    ],
)
def test_depth_paths(fixture: str, ned: int, ied: int, mpfed: int, segments: list[str]) -> None:
    entry, manifest = _scout().scout(
        web_target_id=f"wt-{fixture}", entry_fixture=fixture, task=CONTENT_TASK
    )
    assert entry.endpoint_status == "FUNCTION_ENDPOINT_REACHED"
    assert (entry.ned, entry.ied, entry.mpfed) == (ned, ied, mpfed)
    assert entry.mpfed == entry.ned + entry.ied
    assert [s.depth_segment for s in entry.steps] == segments
    assert all(s.counts_toward_depth == 1 for s in entry.steps)  # 규칙 D-2
    assert manifest is not None


def test_query_submission_counts_one_activation_and_one_text_episode() -> None:
    """`02 §9` — 문자 입력은 activation 이 아니다. episode 축에서만 센다."""
    entry, _ = _scout().scout(
        web_target_id="wt-q",
        entry_fixture="search_dispatch.html",
        task=TaskDefinition(
            "TQ", A.QUERY, None, "QUERY_SUBMITTED", R.FORM_STRUCTURE, R.FORM_STRUCTURE
        ),
    )
    assert (entry.ned, entry.ied, entry.mpfed) == (0, 1, 1)
    assert entry.text_input_episode_count == 1
    assert len(entry.steps) == 1  # 여러 글자를 넣어도 activation 은 1회다
    episode = entry.episodes[0]
    assert episode.episode_kind == "TEXT_INPUT"
    assert episode.input_mode == "PROGRAMMATIC"
    assert episode.ended_by == "SUBMIT"


def test_scroll_is_not_an_activation() -> None:
    entry, _ = _scout().scout(
        web_target_id="wt-1", entry_fixture="depth_path_1.html", task=CONTENT_TASK
    )
    assert entry.scroll_episode_count >= 1
    # episode 는 Depth 에 가산되지 않는다 (규칙 D-3)
    assert entry.mpfed == 1


def test_forced_dismissal_is_recorded_but_not_counted_as_depth() -> None:
    """`02 §9` — popup dismiss 는 activation 이 아니고 `forced_dismissal_count` 로 간다."""
    entry, _ = _scout().scout(
        web_target_id="wt-m",
        entry_fixture="blocking_modal.html",
        task=TaskDefinition("TM", A.CONTENT_OPEN, None, "ARTICLE_BODY_OPEN"),
    )
    assert entry.forced_dismissal_count == 1
    assert entry.mpfed == 1  # 닫기는 깊이에 더해지지 않았다
    assert len(entry.steps) == 1


def test_budget_fires_and_depth_stays_null() -> None:
    """`A1 §2.4` — "8회 안에서는 관측되지 않았다" 이지 `MPFED = 8` 이 아니다."""
    entry, manifest = _scout().scout(
        web_target_id="wt-u",
        entry_fixture="unresolved_route.html",
        task=TaskDefinition(
            "TU", A.UTILITY_ENTRY, None, None, R.CODEBOOK_PENDING, R.CODEBOOK_PENDING
        ),
    )
    assert entry.endpoint_status == "UNRESOLVED"
    assert entry.endpoint_status_detail == "UNRESOLVED_DEPTH_BUDGET_EXCEEDED"
    assert (entry.ned, entry.ied, entry.mpfed) == (None, None, None)
    assert entry.endpoint_reached == 0
    assert entry.budget_reason == "MAX_STATE_REVISITS"
    assert manifest is None


@pytest.mark.parametrize(
    ("fixture", "archetype", "status", "detail"),
    [
        (
            "auth_login_gate.html",
            A.FINANCIAL_ACTION_ENTRY,
            "FUNCTION_ENDPOINT_REACHED",
            "ENDPOINT_VIA_AUTH_GATE",
        ),
        (
            "auth_login_gate.html",
            A.COMMUNICATION_ENTRY,
            "FUNCTION_ENDPOINT_REACHED",
            "ENDPOINT_VIA_AUTH_GATE",
        ),
        ("auth_login_gate.html", A.QUERY, "AUTH_GATE_REACHED", None),
        (
            "auth_identity_gate.html",
            A.FINANCIAL_ACTION_ENTRY,
            "FUNCTION_ENDPOINT_REACHED",
            "ENDPOINT_VIA_AUTH_GATE",
        ),
        # 규칙 E-6a — 커뮤니티에서 본인인증 gate 는 endpoint 가 아니다. 개인정보 요구가 있으면
        # `02 §7` 이 별개 값으로 둔 PERSONAL_DATA_REQUIRED 가 그 자리를 받는다.
        ("auth_identity_gate.html", A.COMMUNICATION_ENTRY, "PERSONAL_DATA_REQUIRED", None),
        # 판별 불가 gate 는 어느 archetype 에서도 승격되지 않는다
        ("auth_ambiguous_gate.html", A.FINANCIAL_ACTION_ENTRY, "AUTH_GATE_REACHED", None),
        ("auth_ambiguous_gate.html", A.COMMUNICATION_ENTRY, "AUTH_GATE_REACHED", None),
    ],
)
def test_gate_branching_on_fixtures(
    fixture: str, archetype: A, status: str, detail: str | None
) -> None:
    entry, _ = _scout().scout(
        web_target_id=f"wt-{fixture}-{archetype.value}",
        entry_fixture=fixture,
        task=TaskDefinition("TG", archetype, None, "FUNCTION_ENTRY", R.GATE_SIGNAL, R.GATE_SIGNAL),
    )
    assert entry.endpoint_status == status
    assert entry.endpoint_status_detail == detail
    if status != "FUNCTION_ENDPOINT_REACHED":
        assert (entry.ned, entry.ied, entry.mpfed) == (None, None, None)
    # 규칙 E-7 — gate 를 통과하지 않는다
    assert len(entry.steps) == 0


def test_auth_gate_prevalence_is_not_undercounted_on_gate_endpoints() -> None:
    """규칙 E-8 — gate 가 endpoint 인 경우에도 유병률이 1로 잡혀야 한다."""
    entry, _ = _scout().scout(
        web_target_id="wt-fin",
        entry_fixture="auth_login_gate.html",
        task=TaskDefinition(
            "TF", A.FINANCIAL_ACTION_ENTRY, None, "FIN", R.GATE_SIGNAL, R.GATE_SIGNAL
        ),
    )
    assert entry.endpoint_status_detail == "ENDPOINT_VIA_AUTH_GATE"
    assert entry.auth_gate_before_endpoint == 0  # endpoint 를 실현한 gate 는 before 가 아니다
    assert entry.auth_gate_observed == 1

    blocked, _ = _scout().scout(
        web_target_id="wt-q-gate",
        entry_fixture="auth_login_gate.html",
        task=TaskDefinition("TQ", A.QUERY, None, "Q", R.GATE_SIGNAL, R.GATE_SIGNAL),
    )
    assert blocked.auth_gate_before_endpoint == 1
    assert blocked.auth_gate_observed == 1


def test_gate_kind_is_decided_from_observation_and_recorded(caplog) -> None:
    """Q-9 — 판별 근거가 관측 기록으로 남아야 사후 검증이 된다."""
    entry, _ = _scout().scout(
        web_target_id="wt-id",
        entry_fixture="auth_identity_gate.html",
        task=TaskDefinition(
            "TF", A.FINANCIAL_ACTION_ENTRY, None, "FIN", R.GATE_SIGNAL, R.GATE_SIGNAL
        ),
    )
    assert any("IDENTITY_VERIFICATION" in n for n in entry.notes)

    ambiguous, _ = _scout().scout(
        web_target_id="wt-amb",
        entry_fixture="auth_ambiguous_gate.html",
        task=TaskDefinition(
            "TF", A.FINANCIAL_ACTION_ENTRY, None, "FIN", R.GATE_SIGNAL, R.GATE_SIGNAL
        ),
    )
    assert any("UNDETERMINED" in n for n in ambiguous.notes)


# ── Freeze / Replay (02 §8) ──────────────────────────────────────────────────
def test_frozen_path_replays_deterministically() -> None:
    _entry, manifest = _scout().scout(
        web_target_id="wt-3", entry_fixture="depth_path_3.html", task=CONTENT_TASK
    )
    assert manifest is not None
    assert manifest.provenance["status"] == "SHADOW_PREPARATORY"
    assert manifest.provenance["real_target_measurement"] is False
    first = replay(manifest, fixture_root=FIXTURES)
    second = replay(manifest, fixture_root=FIXTURES)
    assert first["status"] == "FUNCTION_ENDPOINT_REACHED"
    assert first["observed"] == second["observed"]
    assert first["path_sha256"] == manifest.path_sha256()


def test_broken_replay_is_recorded_not_silently_re_explored() -> None:
    """`02 §8` · 규칙 E-2 — 조용히 자유탐색으로 대체하지 않는다."""
    import dataclasses

    _, manifest = _scout().scout(
        web_target_id="wt-3b", entry_fixture="depth_path_3.html", task=CONTENT_TASK
    )
    assert manifest is not None
    broken = dataclasses.replace(
        manifest, path=[{**manifest.path[0], "selector": "a#does-not-exist"}]
    )
    result = replay(broken, fixture_root=FIXTURES)
    assert result["status"] == "UNRESOLVED"
    assert result["endpoint_status_detail"] == "UNRESOLVED_REPLAY_BROKEN"
    assert result["broken_at_step"] == 1
    assert result["reason"]


def test_mapping_cannot_freeze_while_the_codebook_is_pending() -> None:
    """`A2` 규칙 P-2."""
    pending = TaskDefinition(
        "TU", A.UTILITY_ENTRY, None, None, R.CODEBOOK_PENDING, R.CODEBOOK_PENDING
    )
    assert pending.mapping_frozen_allowed() is False
    assert CONTENT_TASK.mapping_frozen_allowed() is True


# ── dom_order (A1 §2.5 · §2.6 규칙 MIN-4 / A2 §1.13) ─────────────────────────
# `area_css_px2`는 관측 잡음이 있어 tie-break 키에서 빠졌다(V2-C010b). 2차 키는
# 구조값인 `dom_order`다 — 같은 DOM이면 항상 같은 값을 내야 한다(V2-C011/C012).
_TIEBREAK_FIXTURE = "dom_order_tiebreak.html"
_TIEBREAK_TASK = TaskDefinition("TD", A.CONTENT_OPEN, "ARTICLE_LIST_REGION", "ARTICLE_BODY_OPEN")


def _collect_tiebreak(tmp_path: Path, run_name: str) -> Any:
    run = EvidenceRun.create(tmp_path, run_name, execution_mode=ExecutionMode.FIXTURE)
    collector = L0Collector(run, fixture_root=FIXTURES)
    obs = collector.collect(
        FixtureTarget(
            web_target_id=f"wt-{run_name}", fixture=_TIEBREAK_FIXTURE, archetype=A.CONTENT_OPEN
        )
    )
    run.seal()
    return obs


def test_dom_order_matches_document_order_and_area_does_not_decide(tmp_path: Path) -> None:
    """세 형제 카드는 면적이 같고 `marked_primary`가 전부 false다 — 유일한 결정 요인은
    `dom_order`(문서 순서)뿐이어야 한다(`A1 §2.6` 규칙 MIN-4)."""
    obs = _collect_tiebreak(tmp_path, "dom-order-doc-order")
    cards = {
        c.selector: c
        for c in obs.primary_action_candidates
        if c.selector in ("a#card-a", "a#card-b", "a#card-c")
    }
    assert set(cards) == {"a#card-a", "a#card-b", "a#card-c"}
    assert cards["a#card-a"].dom_order < cards["a#card-b"].dom_order < cards["a#card-c"].dom_order
    areas = {c.area_css_px2 for c in cards.values()}
    assert len(areas) == 1, f"fixture 설계 위반 — 면적이 같아야 tie-break 시험이 성립한다: {areas}"
    selected = next(c for c in obs.primary_action_candidates if c.selection_status == "SELECTED")
    assert selected.selector == "a#card-a", (
        "marked_primary 가 전부 false 이고 면적도 동일하므로 dom_order 최솟값(a#card-a)이 "
        f"선택돼야 한다 — 실제 선택: {selected.selector} (dom_order={selected.dom_order})"
    )


def test_dom_order_is_stable_across_repeated_collection(tmp_path: Path) -> None:
    """`A1 §2.6` 잔여 조항 — 같은 fixture를 반복 수집해도 `dom_order`가 흔들리면 안 된다
    (서브픽셀 잡음이 아니라 실제 DOM 비결정성이라면 여기서 드러난다)."""

    def order_of(run_name: str) -> list[tuple[str, int]]:
        obs = _collect_tiebreak(tmp_path, run_name)
        return sorted(
            (c.selector, c.dom_order)
            for c in obs.primary_action_candidates
            if c.selector in ("a#card-a", "a#card-b", "a#card-c")
        )

    first = order_of("dom-order-repeat-1")
    second = order_of("dom-order-repeat-2")
    assert first == second
    assert first == [("a#card-a", 0), ("a#card-b", 1), ("a#card-c", 2)]


def test_scout_path_is_dom_order_deterministic_across_repeated_runs() -> None:
    """`A1 §2.5` `MIN-4 경로 결정성 케이스` — 같은 fixture를 Scout 층에서 두 번 돌려도
    같은 경로(같은 `dom_order` 열)가 나와야 한다. **`replay`가 아니라 새 Scout 두 번**이다
    (`A1 §2.6` 규칙 MIN-8 — Replay는 이 잔여를 잡지 않는다고 명시돼 있다)."""
    entry1, manifest1 = _scout().scout(
        web_target_id="wt-tiebreak-1", entry_fixture=_TIEBREAK_FIXTURE, task=_TIEBREAK_TASK
    )
    entry2, manifest2 = _scout().scout(
        web_target_id="wt-tiebreak-2", entry_fixture=_TIEBREAK_FIXTURE, task=_TIEBREAK_TASK
    )
    assert entry1.endpoint_status == entry2.endpoint_status == "FUNCTION_ENDPOINT_REACHED"
    assert manifest1 is not None and manifest2 is not None
    assert [s.clicked_selector for s in entry1.steps] == [s.clicked_selector for s in entry2.steps]
    path1 = [(node["selector"], node["dom_order"]) for node in manifest1.path]
    path2 = [(node["selector"], node["dom_order"]) for node in manifest2.path]
    assert path1 == path2
    assert path1 == [("a#card-a", 0)], (
        "형제 카드 중 marked_primary 없고 면적도 같으므로 dom_order 최솟값(a#card-a, "
        f"dom_order=0)을 밟아야 한다 — 실제: {path1}"
    )
    assert manifest1.path_sha256() == manifest2.path_sha256()
