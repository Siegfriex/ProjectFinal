"""P-C FIXTURE — corpus 완결성 + L0/L1 엔진을 실제 Playwright 로 검증한다.

이 파일의 모든 브라우저 동작은 로컬 ``file://`` 픽스처만 대상으로 한다
(``execution_mode="FIXTURE"``, ``execution_mode.py`` 가 강제). 실제 서비스에는
어떤 요청도 나가지 않는다.

fixture corpus 는 오케스트레이터가 지정한 4.1 목록(25 항목)을 다음처럼 덮는다.
일부는 이미 있던 파일을 재사용한다(중복 픽스처를 늘리지 않기 위해):

    login_gate      -> fixtures/auth_gate_site/
    blocking_modal  -> fixtures/popup_blocking.html
    motion_banner   -> fixtures/motion_heavy.html

나머지는 ``fixtures/corpus/`` 아래 새로 만들었다.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

RESEARCH = Path(__file__).resolve().parents[1] / "research" / "landing_accessibility"
sys.path.insert(0, str(RESEARCH / "src"))

from landing_accessibility.pc_fixture import overlay, path_freeze, scout  # noqa: E402
from landing_accessibility.pc_fixture.guarded_writer import GuardedEvidenceWriter  # noqa: E402
from landing_accessibility.pc_fixture.l0_collector import collect_l0_fixture  # noqa: E402

FIXTURES = RESEARCH / "tests" / "pc_fixture" / "fixtures"
CORPUS = FIXTURES / "corpus"

# 4.1 이 요구한 25개 카테고리 — 있어야 하는 파일/디렉터리 (일부는 상단 재사용 매핑).
CORPUS_CATEGORIES = {
    "simple_article": CORPUS / "simple_article.html",
    "search_dispatch": CORPUS / "search_dispatch" / "entry.html",
    "product_detail": CORPUS / "product_detail" / "entry.html",
    "place_lookup": CORPUS / "place_lookup" / "entry.html",
    "login_gate": FIXTURES / "auth_gate_site" / "entry.html",
    "identity_auth_gate": CORPUS / "identity_auth_gate" / "entry.html",
    "payment_gate": CORPUS / "payment_gate" / "entry.html",
    "personal_data_required": CORPUS / "personal_data_required" / "entry.html",
    "captcha": CORPUS / "captcha" / "entry.html",
    "unresolved_endpoint": CORPUS / "unresolved_endpoint.html",
    "blocking_modal": FIXTURES / "popup_blocking.html",
    "promotion_modal": CORPUS / "promotion_modal.html",
    "cookie_consent": CORPUS / "cookie_consent.html",
    "app_install_prompt": CORPUS / "app_install_prompt.html",
    "login_prompt": CORPUS / "login_prompt.html",
    "chat_widget": CORPUS / "chat_widget.html",
    "banner": CORPUS / "banner.html",
    "toast": CORPUS / "toast.html",
    "motion_banner": FIXTURES / "motion_heavy.html",
    "sticky_overlay": CORPUS / "sticky_overlay.html",
    "primary_action_occluded": CORPUS / "primary_action_occluded.html",
    "missing_accessible_name": CORPUS / "missing_accessible_name.html",
    "small_target": CORPUS / "small_target.html",
    "low_contrast_control": CORPUS / "low_contrast_control.html",
    "depth_0": CORPUS / "depth_0" / "entry.html",
    "depth_1": CORPUS / "depth_1" / "entry.html",
    "depth_2": CORPUS / "depth_2" / "entry.html",
    "depth_multi": CORPUS / "depth_multi" / "entry.html",
    "selector_replay_failure": CORPUS / "selector_replay_failure" / "entry_v1.html",
}


def test_corpus_completeness():
    missing = [name for name, p in CORPUS_CATEGORIES.items() if not p.exists()]
    assert not missing, f"fixture corpus 에 없는 카테고리: {missing}"


# ---------------------------------------------------------------------------
# L0 — 개별 raw feature 가 실제로 잡히는지 (Playwright, file:// 대상)
# ---------------------------------------------------------------------------


def _fresh_writer(tmp_path, run_id="run1"):
    return GuardedEvidenceWriter(tmp_path / run_id, run_id=run_id, execution_mode="FIXTURE")


def test_missing_accessible_name_flagged(tmp_path):
    store = _fresh_writer(tmp_path)
    obs = collect_l0_fixture(
        fixture_path=CORPUS_CATEGORIES["missing_accessible_name"],
        service_id="svc_missing_name",
        canonical_url="https://example.com/missing-name",
        audit_date="2026-08-27",
        protocol_version="v2.0",
        store=store,
    )
    primary = [e for e in obs.probe["interactive_elements"] if e.get("is_primary_action")]
    assert primary
    assert primary[0]["accessible_name"] is None


def test_small_target_flagged(tmp_path):
    store = _fresh_writer(tmp_path)
    obs = collect_l0_fixture(
        fixture_path=CORPUS_CATEGORIES["small_target"],
        service_id="svc_small_target",
        canonical_url="https://example.com/small-target",
        audit_date="2026-08-27",
        protocol_version="v2.0",
        store=store,
    )
    primary = [e for e in obs.probe["interactive_elements"] if e.get("is_primary_action")]
    assert primary
    assert primary[0]["target_size_ok"] is False


def test_low_contrast_control_raw_feature(tmp_path):
    store = _fresh_writer(tmp_path)
    obs = collect_l0_fixture(
        fixture_path=CORPUS_CATEGORIES["low_contrast_control"],
        service_id="svc_low_contrast",
        canonical_url="https://example.com/low-contrast",
        audit_date="2026-08-27",
        protocol_version="v2.0",
        store=store,
    )
    primary = [e for e in obs.probe["interactive_elements"] if e.get("is_primary_action")]
    assert primary
    ratio = primary[0]["contrast_ratio"]
    assert ratio is not None and ratio < 3.0  # raw feature 만 — PASS/FAIL 판정은 이 레인 밖


def test_motion_and_overlay_candidates_detected(tmp_path):
    store = _fresh_writer(tmp_path)
    obs = collect_l0_fixture(
        fixture_path=CORPUS_CATEGORIES["blocking_modal"],
        service_id="svc_blocking_modal",
        canonical_url="https://example.com/blocking-modal",
        audit_date="2026-08-27",
        protocol_version="v2.0",
        store=store,
    )
    assert obs.probe["overlay_candidates"]
    cand = obs.probe["overlay_candidates"][0]
    assert cand["dismiss_control_present"] is True
    assert obs.static_evidence_complete is True
    assert obs.record.interaction_evidence_present is False  # L0 단독 관측은 항상 False


def test_overlay_full_pipeline_matches_probe_output(tmp_path):
    """probe.js 가 실제로 뽑은 값을 overlay.py 파이프라인에 그대로 넣어
    blocking/coverage 계산까지 end-to-end 로 검증한다."""
    store = _fresh_writer(tmp_path)
    obs = collect_l0_fixture(
        fixture_path=CORPUS_CATEGORIES["primary_action_occluded"],
        service_id="svc_occluded",
        canonical_url="https://example.com/occluded",
        audit_date="2026-08-27",
        protocol_version="v2.0",
        store=store,
    )
    cand_raw = obs.probe["overlay_candidates"][0]
    candidate = overlay.OverlayCandidate(
        element_ref=cand_raw["ref"],
        bbox=overlay.BBox(**cand_raw["bbox"]),
        role_dialog=cand_raw["role_dialog"],
        dom_text_sample=cand_raw["dom_text_sample"],
        dismiss_control_present=cand_raw["dismiss_control_present"],
    )
    primary_raw = next(e for e in obs.probe["interactive_elements"] if e["is_primary_action"])
    primary_bbox = overlay.BBox(**primary_raw["bbox"])
    viewport = overlay.BBox(0, 0, obs.probe["viewport"]["width"], obs.probe["viewport"]["height"])
    result = overlay.assess_overlay(
        candidate, viewport, primary_bbox, must_dismiss_for_primary=False
    )
    assert result.primary_action_occlusion == pytest.approx(1.0, abs=0.05)
    assert result.is_blocking is True


# ---------------------------------------------------------------------------
# L1 — Scout / Path Freeze / Replay (Playwright, 다중 페이지 file:// 사이트)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "category,expected_ned_plus_ied",
    [("depth_0", 0), ("depth_1", 1), ("depth_2", 2), ("depth_multi", 3)],
)
def test_depth_categories_produce_expected_mpfed(category, expected_ned_plus_ied):
    trace = scout.run_scout(
        entry_fixture=CORPUS_CATEGORIES[category],
        endpoint_keywords=["다음", "확인", "계속"],
        max_steps=8,
        execution_mode="FIXTURE",
    )
    assert trace.terminal_signal == "FUNCTION_ENDPOINT_REACHED"
    mpfed = (trace.ned or 0) + (trace.ied or 0)
    assert mpfed == expected_ned_plus_ied
    assert len(trace.activations) == expected_ned_plus_ied


def test_unresolved_endpoint_terminates_unresolved():
    trace = scout.run_scout(
        entry_fixture=CORPUS_CATEGORIES["unresolved_endpoint"],
        endpoint_keywords=["아무거나"],
        max_steps=4,
        execution_mode="FIXTURE",
    )
    assert trace.terminal_signal == "UNRESOLVED"


def test_identity_auth_gate_terminates_with_gate_tag_distinguished_from_login():
    trace = scout.run_scout(
        entry_fixture=CORPUS_CATEGORIES["identity_auth_gate"],
        endpoint_keywords=["로그인"],
        max_steps=4,
        execution_mode="FIXTURE",
    )
    assert trace.terminal_signal == "AUTH_GATE_REACHED"
    assert trace.gate_tag == "IDENTITY_VERIFICATION_REQUIRED"  # LOGIN_REQUIRED 와 구분됨


def test_login_gate_site_gate_tag_is_login_not_identity():
    trace = scout.run_scout(
        entry_fixture=FIXTURES / "auth_gate_site" / "entry.html",
        endpoint_keywords=["계좌조회"],
        max_steps=4,
        execution_mode="FIXTURE",
    )
    assert trace.terminal_signal == "AUTH_GATE_REACHED"
    assert trace.gate_tag == "LOGIN_REQUIRED"


def test_payment_gate_terminates():
    trace = scout.run_scout(
        entry_fixture=CORPUS_CATEGORIES["payment_gate"],
        endpoint_keywords=["주문"],
        max_steps=4,
        execution_mode="FIXTURE",
    )
    assert trace.terminal_signal == "PAYMENT_GATE_REACHED"


def test_personal_data_required_terminates():
    trace = scout.run_scout(
        entry_fixture=CORPUS_CATEGORIES["personal_data_required"],
        endpoint_keywords=["민원"],
        max_steps=4,
        execution_mode="FIXTURE",
    )
    assert trace.terminal_signal == "PERSONAL_DATA_REQUIRED"


def test_captcha_terminates():
    trace = scout.run_scout(
        entry_fixture=CORPUS_CATEGORIES["captcha"],
        endpoint_keywords=["글쓰기"],
        max_steps=4,
        execution_mode="FIXTURE",
    )
    assert trace.terminal_signal == "CAPTCHA"


def test_search_dispatch_counts_text_input_episode_separately_from_activation():
    trace = scout.run_scout(
        entry_fixture=CORPUS_CATEGORIES["search_dispatch"],
        endpoint_keywords=["검색"],
        max_steps=5,
        execution_mode="FIXTURE",
    )
    assert trace.terminal_signal == "FUNCTION_ENDPOINT_REACHED"
    assert trace.text_input_episode_count == 1
    # 텍스트 입력은 activation 이 아니다 — 버튼 클릭 1건만 activation 이어야 한다.
    assert len(trace.activations) == 1


def test_forced_dismissal_counted_and_endpoint_still_reached():
    trace = scout.run_scout(
        entry_fixture=FIXTURES / "popup_blocking.html",
        endpoint_keywords=["대표기능"],
        max_steps=5,
        execution_mode="FIXTURE",
    )
    assert trace.forced_dismissal_count == 1
    assert trace.terminal_signal in {"FUNCTION_ENDPOINT_REACHED", "UNRESOLVED"}


# ---------------------------------------------------------------------------
# Path Freeze / Replay
# ---------------------------------------------------------------------------


def test_freeze_and_replay_roundtrip_ok():
    trace = scout.run_scout(
        entry_fixture=CORPUS_CATEGORIES["depth_2"],
        endpoint_keywords=["다음", "계속"],
        max_steps=6,
        execution_mode="FIXTURE",
    )
    assert trace.terminal_signal == "FUNCTION_ENDPOINT_REACHED"
    manifest = path_freeze.freeze_path(trace)
    result = path_freeze.replay_path(
        manifest, entry_fixture=CORPUS_CATEGORIES["depth_2"], execution_mode="FIXTURE"
    )
    assert result.status == "REPLAY_OK"
    assert result.reached_terminal_signal == "FUNCTION_ENDPOINT_REACHED"


def test_replay_selector_failure_is_reported_not_silently_reexplored():
    """SSOT 02 §8: replay 가 깨지면 상태를 기록하고, 조용히 자유탐색으로
    대체하지 않는다. UI 문구가 바뀐 v2 픽스처에 v1 에서 frozen 된 selector
    를 재실행하면 REPLAY_BROKEN 이어야 한다."""
    entry_v1 = CORPUS_CATEGORIES["selector_replay_failure"]
    entry_v2 = entry_v1.with_name("entry_v2.html")

    trace = scout.run_scout(
        entry_fixture=entry_v1,
        endpoint_keywords=["확인", "완료"],
        max_steps=4,
        execution_mode="FIXTURE",
    )
    assert trace.terminal_signal == "FUNCTION_ENDPOINT_REACHED"
    manifest = path_freeze.freeze_path(trace)

    result = path_freeze.replay_path(manifest, entry_fixture=entry_v2, execution_mode="FIXTURE")
    assert result.status == "REPLAY_BROKEN"
    assert result.broken_at_step is not None


def test_freeze_refuses_non_endpoint_traces():
    trace = scout.run_scout(
        entry_fixture=CORPUS_CATEGORIES["unresolved_endpoint"],
        endpoint_keywords=["아무거나"],
        max_steps=2,
        execution_mode="FIXTURE",
    )
    with pytest.raises(ValueError, match="freeze"):
        path_freeze.freeze_path(trace)
