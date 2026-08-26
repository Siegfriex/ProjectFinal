"""P-C FIXTURE — failure injection harness (§4.7 최소 목록).

이 파일이 이 레인의 핵심 산출물이다: 파이프라인에 의도적으로 결함 있는
입력·상태를 주입해서, 가드가 **실제로 차단하는지** 검증한다. 통과 기준은
"guard 가 정의돼 있다"가 아니라 "guard 가 예외를 던졌다/상태를 BROKEN 으로
남겼다"이다.

REAL-TARGET FIREWALL (``execution_mode.py``, PHASE_GATES.md §4.5) 검증이
이 파일의 최우선 섹션이다.
"""

from __future__ import annotations

import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

RESEARCH = Path(__file__).resolve().parents[1] / "research" / "landing_accessibility"
sys.path.insert(0, str(RESEARCH / "src"))

from landing_accessibility.evidence_manifest import (  # noqa: E402
    MissingRunManifestError,
    load_run_manifest,
    verify_run,
)
from landing_accessibility.pc_fixture import (  # noqa: E402
    execution_mode,
    path_freeze,
    scout,
    verdict,
)
from landing_accessibility.pc_fixture.guarded_writer import (  # noqa: E402
    AppendOnlyViolation,
    BackdatingViolation,
    DuplicateObservationError,
    GuardedEvidenceWriter,
    ObservationRecord,
    OverwriteGuardError,
)
from landing_accessibility.pc_fixture.identity import SymlinkEscapeError  # noqa: E402
from landing_accessibility.pc_fixture.l0_collector import collect_l0_fixture  # noqa: E402

FIXTURES = RESEARCH / "tests" / "pc_fixture" / "fixtures"
CORPUS = FIXTURES / "corpus"

# ---------------------------------------------------------------------------
# §4.5 REAL-TARGET FIREWALL — 이 레인의 최우선 산출물.
# ---------------------------------------------------------------------------


def test_real_target_hard_fails_at_the_firewall_directly():
    with pytest.raises(execution_mode.RealTargetForbiddenError):
        execution_mode.enforce_real_target_firewall("REAL_TARGET")


def test_unknown_execution_mode_rejected_fail_closed():
    """허용 목록에 없는 값은 무조건 거부한다 — 금지 목록 방식이었다면 오탈자나
    새 값이 조용히 통과했을 것이다."""
    with pytest.raises(ValueError):
        execution_mode.enforce_real_target_firewall("PRODUCTION")
    with pytest.raises(ValueError):
        execution_mode.enforce_real_target_firewall("")


@pytest.mark.parametrize("mode", ["FIXTURE", "SHADOW_DRY_RUN"])
def test_allowed_modes_pass_before_p0_close(mode):
    execution_mode.enforce_real_target_firewall(mode)  # 예외 없어야 한다


def test_real_target_blocks_guarded_writer_construction(tmp_path):
    with pytest.raises(execution_mode.RealTargetForbiddenError):
        GuardedEvidenceWriter(tmp_path / "run1", run_id="run1", execution_mode="REAL_TARGET")
    # 아무 부수효과도 없어야 한다 — run_dir 조차 만들어지지 않는다.
    assert not (tmp_path / "run1").exists()


def test_real_target_blocks_l0_collection_before_any_browser_io(tmp_path):
    """REAL_TARGET 이면 fixture_path 존재 확인·Playwright 기동보다 먼저 막혀야 한다.
    존재하지 않는 fixture_path 를 넘겨도 FileNotFoundError 가 아니라
    RealTargetForbiddenError 여야 한다 — 방화벽이 다른 모든 검사보다 앞선다."""
    with pytest.raises(execution_mode.RealTargetForbiddenError):
        collect_l0_fixture(
            fixture_path=Path("/nonexistent/should/never/be/checked.html"),
            service_id="svc",
            canonical_url="https://real-service.example.com/",
            audit_date="2026-08-27",
            protocol_version="v2.0",
            store=None,  # type: ignore[arg-type]  # 방화벽이 먼저 막으므로 store 는 참조되지 않는다
            execution_mode="REAL_TARGET",
        )


def test_real_target_blocks_scout_before_any_browser_io():
    with pytest.raises(execution_mode.RealTargetForbiddenError):
        scout.run_scout(
            entry_fixture=Path("/nonexistent.html"),
            endpoint_keywords=["x"],
            execution_mode="REAL_TARGET",
        )


def test_real_target_blocks_replay_before_any_browser_io():
    fake_manifest = path_freeze.TaskManifest(
        entry_url="file:///nonexistent.html",
        steps=[],
        expected_terminal_signal="FUNCTION_ENDPOINT_REACHED",
        expected_endpoint_url=None,
        protocol_sha="deadbeef",
    )
    with pytest.raises(execution_mode.RealTargetForbiddenError):
        path_freeze.replay_path(fake_manifest, execution_mode="REAL_TARGET")


# ---------------------------------------------------------------------------
# evidence identity / append-only — 파일 시스템 수준 (Playwright 불필요, tmp_path)
# ---------------------------------------------------------------------------


def _writer(tmp_path, run_id="run1"):
    return GuardedEvidenceWriter(tmp_path / run_id, run_id=run_id, execution_mode="FIXTURE")


def _obs_record(oid="obs_test1", collected_at=None):
    return ObservationRecord(
        observation_id=oid,
        service_id="svc",
        canonical_url="https://example.com/",
        requested_url="file:///x.html",
        audit_date="2026-08-27",
        protocol_version="v2.0",
        collected_at=collected_at or datetime.now(UTC).isoformat(),
    )


def test_overwrite_same_relpath_rejected(tmp_path):
    store = _writer(tmp_path)
    store.write_evidence_file("obs_a", "dom", "obs_a.html", b"<html>1</html>")
    with pytest.raises(OverwriteGuardError):
        store.write_evidence_file("obs_a", "dom", "obs_a.html", b"<html>2</html>")


def test_duplicate_observation_id_rejected(tmp_path):
    store = _writer(tmp_path)
    store.append_observation(_obs_record("obs_dup"))
    with pytest.raises(DuplicateObservationError):
        store.append_observation(_obs_record("obs_dup"))


def test_missing_manifest_rejected(tmp_path):
    run_dir = tmp_path / "run_no_manifest"
    run_dir.mkdir()
    with pytest.raises(MissingRunManifestError):
        load_run_manifest(run_dir)
    with pytest.raises(MissingRunManifestError):
        verify_run(run_dir)


def test_evidence_file_swap_detected_on_finalize(tmp_path):
    store = _writer(tmp_path)
    store.write_evidence_file("obs_a", "dom", "obs_a.html", b"original bytes")
    store.finalize()

    # 같은 run_dir 을 대상으로 하는 새 writer(예: 재시작된 프로세스)로도 swap 이 잡혀야 한다.
    (tmp_path / "run1" / "dom" / "obs_a.html").write_bytes(b"SWAPPED CONTENT")
    store2 = GuardedEvidenceWriter(tmp_path / "run1", run_id="run1", execution_mode="FIXTURE")
    with pytest.raises(AppendOnlyViolation, match="swap"):
        store2.finalize()


def test_evidence_file_deleted_detected_on_finalize(tmp_path):
    store = _writer(tmp_path)
    store.write_evidence_file("obs_a", "dom", "obs_a.html", b"original bytes")
    store.finalize()
    (tmp_path / "run1" / "dom" / "obs_a.html").unlink()
    store2 = GuardedEvidenceWriter(tmp_path / "run1", run_id="run1", execution_mode="FIXTURE")
    with pytest.raises(AppendOnlyViolation, match="사라짐"):
        store2.finalize()


def test_symlink_escape_rejected(tmp_path):
    outside = tmp_path / "outside"
    outside.mkdir()
    run_dir = tmp_path / "run_symlink"
    run_dir.mkdir()
    (run_dir / "dom").symlink_to(outside, target_is_directory=True)
    store = GuardedEvidenceWriter(run_dir, run_id="run_symlink", execution_mode="FIXTURE")
    with pytest.raises(SymlinkEscapeError):
        store.write_evidence_file("obs_a", "dom", "escaped.html", b"data")
    assert not (outside / "escaped.html").exists()


def test_hidden_retry_does_not_silently_overwrite(tmp_path):
    """같은 observation 을 "재시도" 로 두 번 쓰면(예: 실패 후 프로세스가 조용히
    재시도) 두 번째 시도가 첫 시도를 덮어쓰지 않고 명시적으로 실패해야 한다."""
    store = _writer(tmp_path)
    store.write_evidence_file("obs_retry", "dom", "obs_retry.html", b"first attempt bytes")
    with pytest.raises(OverwriteGuardError):
        store.write_evidence_file(
            "obs_retry", "dom", "obs_retry.html", b"second silent retry bytes"
        )
    # 첫 시도의 내용이 그대로 남아 있어야 한다.
    assert (tmp_path / "run1" / "dom" / "obs_retry.html").read_bytes() == b"first attempt bytes"


def test_prereg_backdating_rejected(tmp_path):
    store = _writer(tmp_path)
    backdated = _obs_record(
        "obs_backdated", collected_at=(store.created_at - timedelta(hours=1)).isoformat()
    )
    with pytest.raises(BackdatingViolation):
        store.append_observation(backdated)


def test_discarded_attempt_is_recorded_not_omitted(tmp_path):
    store = _writer(tmp_path)
    store.record_discarded_attempt(
        observation_id="obs_failed", reason="L0_COLLECTION_EXCEPTION", detail="TimeoutError: ..."
    )
    attempts = store.discarded_attempts()
    assert len(attempts) == 1
    assert attempts[0]["observation_id"] == "obs_failed"
    # append-only: 두 번째 실패도 사라지지 않고 누적된다.
    store.record_discarded_attempt(observation_id="obs_failed", reason="RETRY_ALSO_FAILED")
    assert len(store.discarded_attempts()) == 2


def test_wrong_url_real_l0_collection_flags_file_family_mismatch(tmp_path):
    store = _writer(tmp_path)
    obs = collect_l0_fixture(
        fixture_path=CORPUS / "wrong_url_redirect.html",
        service_id="svc_wrong_url",
        canonical_url="https://example.com/wrong-url",
        audit_date="2026-08-27",
        protocol_version="v2.0",
        store=store,
    )
    assert any("WRONG_URL_SUSPECTED" in n for n in obs.record.notes)


def test_malformed_ax_and_thin_evidence_flagged_not_called_complete(tmp_path):
    store = _writer(tmp_path)
    obs = collect_l0_fixture(
        fixture_path=FIXTURES / "broken_dom.html",
        service_id="svc_broken_dom",
        canonical_url="https://example.com/broken",
        audit_date="2026-08-27",
        protocol_version="v2.0",
        store=store,
    )
    assert obs.static_evidence_complete is False
    assert any("STATIC_EVIDENCE_THIN" in n for n in obs.record.notes)


# ---------------------------------------------------------------------------
# replay: endpoint mismatch / auth-gate mismatch (selector 는 살아있지만
# 종점이 달라진 경우 — corpus_and_engine.py 의 selector 자체가 사라진 경우와 대응)
# ---------------------------------------------------------------------------


def test_endpoint_mismatch_after_deploy_change_is_replay_broken():
    entry = CORPUS / "endpoint_mismatch" / "entry.html"
    gate_variant = CORPUS / "endpoint_mismatch" / "entry_gate_variant.html"

    trace = scout.run_scout(
        entry_fixture=entry, endpoint_keywords=["확인"], max_steps=4, execution_mode="FIXTURE"
    )
    assert trace.terminal_signal == "FUNCTION_ENDPOINT_REACHED"
    manifest = path_freeze.freeze_path(trace)

    result = path_freeze.replay_path(manifest, entry_fixture=gate_variant, execution_mode="FIXTURE")
    assert result.status == "REPLAY_BROKEN"
    assert result.reached_terminal_signal is None  # 로그인 페이지엔 endpoint 마커가 없다
    assert result.detail is not None


# ---------------------------------------------------------------------------
# judgment semantics — UNDETERMINED->NA / UNDETERMINED->PASS 세탁 시도
# ---------------------------------------------------------------------------


def test_undetermined_to_na_laundering_rejected():
    """SSOT 02 §14 실패주입 목록의 또 다른 축: 증거 불충분(UNDETERMINED)을
    "적용기회 자체가 없었다"(NA) 로 위장하는 경로."""
    with pytest.raises(verdict.VerdictSemanticError):
        verdict.CriterionObservation(
            criterion_id="c_z",
            applicable_count=4,
            pass_count=0,
            fail_count=0,
            undetermined_count=4,
            verdict_state="NA",
        )


def test_undetermined_to_pass_laundering_rejected_again_via_factory_bypass_attempt():
    """make_criterion_observation 은애초에 verdict_state 를 호출자가 고를 수
    없게 만든다 — 우회 시도 자체가 TypeError 로 막힌다는 것도 확인한다."""
    with pytest.raises(TypeError):
        verdict.make_criterion_observation(  # type: ignore[call-arg]
            "c_y", pass_count=1, fail_count=0, undetermined_count=3, verdict_state="PASS"
        )
