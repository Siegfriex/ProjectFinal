"""P-C LANE C — evidence identity · append-only · manifest 계약.

`02 §11` · `§12` / `A1 §6` / `07_EVIDENCE_MANIFEST_CONTRACT`.

여기서 지키는 것은 "재현은 못 해도 위조는 잡힌다" 는 계약이다.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
RESEARCH = REPO / "research" / "landing_accessibility"
sys.path.insert(0, str(RESEARCH / "src"))

from landing_accessibility.engine.evidence import (  # noqa: E402
    MAX_RECOLLECTION_RUNS_PER_WEB_TARGET,
    DuplicateObservationError,
    EvidenceError,
    EvidenceOverwriteError,
    EvidenceRun,
    PreregistrationError,
    RecollectionPreregistration,
    RunSealedError,
    SymlinkEscapeError,
    select_canonical_run,
)
from landing_accessibility.engine.firewall import ExecutionMode  # noqa: E402
from landing_accessibility.engine.identity import (  # noqa: E402
    EVIDENCE_SLOTS,
    OBSERVATION_ID_HEX_LEN,
    IdentityError,
    missing_slots,
    observation_id,
)
from landing_accessibility.engine.provenance import validate_provenance  # noqa: E402
from landing_accessibility.evidence_manifest import (  # noqa: E402
    MissingRunManifestError,
    load_run_manifest,
    verify_run,
)

_ID_KW = {
    "web_target_id": "wt-001",
    "evidence_run_id": "run-a",
    "requested_url": "file:///fixtures/simple_article.html",
    "protocol_version": "v2.0-pc-fixture-1",
    "collection_started_at": "2026-08-27T01:02:03.000004Z",
}


# ── observation_id (A1 §6.3) ─────────────────────────────────────────────────
def test_observation_id_is_deterministic_and_fixed_width() -> None:
    a = observation_id(**_ID_KW)
    assert a == observation_id(**_ID_KW)
    assert len(a) == OBSERVATION_ID_HEX_LEN
    assert all(c in "0123456789abcdef" for c in a)


@pytest.mark.parametrize("field", sorted(_ID_KW))
def test_every_hash_input_changes_the_id(field: str) -> None:
    """`A1 §6.3` 이 확정한 5개 입력이 **전부** id 에 반영돼야 한다."""
    changed = {**_ID_KW, field: _ID_KW[field] + "-x"}
    assert observation_id(**changed) != observation_id(**_ID_KW)


def test_same_day_recollection_gets_a_different_id() -> None:
    """`audit_date` 만으로 관측을 식별하지 않는다 (`A1 §6.3`)."""
    later = {**_ID_KW, "collection_started_at": "2026-08-27T23:59:59.999999Z"}
    assert observation_id(**later) != observation_id(**_ID_KW)


def test_identical_korean_display_names_cannot_collide() -> None:
    """`02 §14` 의 `같은 길이의 한글 이름 ID collision` — display name 은 입력이 아니다."""
    a = observation_id(**{**_ID_KW, "web_target_id": "wt-001"})
    b = observation_id(**{**_ID_KW, "web_target_id": "wt-002"})
    assert a != b


def test_empty_hash_input_is_rejected() -> None:
    with pytest.raises(IdentityError):
        observation_id(**{**_ID_KW, "web_target_id": "  "})


def test_evidence_slot_set_matches_a1_section_6_2() -> None:
    assert EVIDENCE_SLOTS == (
        "dom",
        "ax",
        "screenshot_initial",
        "screenshot_fullpage",
        "computed_css",
        "probe",
        "manifest",
    )


def test_missing_slots_reports_what_blocks_measured() -> None:
    assert missing_slots(dict.fromkeys(EVIDENCE_SLOTS, "p")) == []
    assert "probe" in missing_slots({**dict.fromkeys(EVIDENCE_SLOTS, "p"), "probe": None})


# ── run 계약 ─────────────────────────────────────────────────────────────────
def _run(tmp_path: Path, name: str = "run-a") -> EvidenceRun:
    run = EvidenceRun.create(tmp_path, name, execution_mode=ExecutionMode.FIXTURE)
    run.open_observation("obs-1")
    run.write_artifact("obs-1", "obs-1/l0a/dom.html", b"<html></html>")
    return run


def test_sealed_run_verifies_against_its_own_manifest(tmp_path: Path) -> None:
    run = _run(tmp_path)
    run.seal()
    report = run.verify()
    assert report["status"] == "VERIFIED"
    assert report["observations"] == 1
    validate_provenance(
        __import__("json").loads((run.run_dir / "run.json").read_text(encoding="utf-8"))[
            "provenance"
        ]
    )


def test_duplicate_observation_id_is_refused(tmp_path: Path) -> None:
    run = _run(tmp_path)
    with pytest.raises(DuplicateObservationError):
        run.open_observation("obs-1")


def test_overwriting_evidence_is_refused(tmp_path: Path) -> None:
    """`02 §12` — 재수집은 새 run 이고, 재판정은 새 judgment version 이다."""
    run = _run(tmp_path)
    with pytest.raises(EvidenceOverwriteError):
        run.write_artifact("obs-1", "obs-1/l0a/dom.html", b"<html>2</html>")


def test_two_screenshots_need_distinct_relpaths(tmp_path: Path) -> None:
    """`A1 §6.2` — `(observation_id, relpath)` 중복 금지가 두 screenshot 을 가른다."""
    run = _run(tmp_path)
    run.write_artifact("obs-1", "obs-1/l0a/screen_initial.png", b"a")
    run.write_artifact("obs-1", "obs-1/l0a/screen_fullpage.png", b"b")
    with pytest.raises(EvidenceOverwriteError):
        run.write_artifact("obs-1", "obs-1/l0a/screen_initial.png", b"c")


def test_symlink_escape_is_refused(tmp_path: Path) -> None:
    outside = tmp_path / "outside"
    outside.mkdir()
    run = _run(tmp_path)
    (run.run_dir / "obs-1" / "l0a" / "escape").symlink_to(outside, target_is_directory=True)
    with pytest.raises(SymlinkEscapeError):
        run.write_artifact("obs-1", "obs-1/l0a/escape/leak.json", b"{}")


@pytest.mark.parametrize("relpath", ["/etc/passwd", "../escape.json", "a/../../b.json"])
def test_absolute_and_parent_relpaths_are_refused(tmp_path: Path, relpath: str) -> None:
    run = _run(tmp_path)
    with pytest.raises(EvidenceError):
        run.write_artifact("obs-1", relpath, b"{}")


def test_run_cannot_be_sealed_twice(tmp_path: Path) -> None:
    run = _run(tmp_path)
    run.seal()
    with pytest.raises(RunSealedError):
        run.seal()
    with pytest.raises(RunSealedError):
        run.write_artifact("obs-1", "obs-1/late.json", b"{}")


def test_run_directory_cannot_be_reused(tmp_path: Path) -> None:
    _run(tmp_path).seal()
    with pytest.raises(EvidenceOverwriteError):
        EvidenceRun.create(tmp_path, "run-a", execution_mode=ExecutionMode.FIXTURE)


def test_missing_manifest_invalidates_the_run(tmp_path: Path) -> None:
    empty = tmp_path / "no-manifest"
    empty.mkdir()
    with pytest.raises(MissingRunManifestError):
        load_run_manifest(empty)


def test_tampering_is_detected_even_though_raw_is_gitignored(tmp_path: Path) -> None:
    run = _run(tmp_path)
    run.seal()
    (run.run_dir / "obs-1" / "l0a" / "dom.html").write_bytes(b"<html>tampered</html>")
    report = verify_run(run.run_dir)
    assert report["status"] == "FAILED"
    assert report["hash_mismatch"]


def test_structure_only_verification_is_not_counted_as_verified(tmp_path: Path) -> None:
    """검사하지 않은 것을 통과로 세지 않는다 (`07 §4`).

    `evidence_manifest.verify_run`(bc0b7a0, `verify-run-mislabels-mode-and-symlink-
    bypasses-relpath-guard` 시정)은 `status`를 `require_files` 플래그가 아니라
    **실제로 몇 건을 바이트 대조했는지**에서 유도한다. 그래서 raw 파일이 실제로
    존재하면 `require_files=False`로 불러도 `VERIFIED`가 맞다 — "검사하지 않은 것을
    통과로 세지 않는다"의 반례가 아니라 정확히 그 원칙이 요구하는 반대쪽 결과다.
    이 케이스가 실제로 시험해야 하는 것은 **raw가 없는(manifest-only clone) 상황**이다 —
    거기서만 `files_checked < entries`가 성립해 구조검증 라벨이 나온다.
    """
    run = _run(tmp_path)
    run.seal()
    raw_path = run.run_dir / "obs-1" / "l0a" / "dom.html"
    assert raw_path.exists()
    raw_path.unlink()

    structure_only = verify_run(run.run_dir, require_files=False)
    assert structure_only["status"] == "MANIFEST_WELL_FORMED_FILES_NOT_CHECKED"
    assert structure_only["files_checked"] == 0

    strict = verify_run(run.run_dir, require_files=True)
    assert strict["status"] == "FAILED"
    assert raw_path.relative_to(run.run_dir).as_posix() in strict["missing_files"]


def test_empty_run_cannot_be_sealed(tmp_path: Path) -> None:
    run = EvidenceRun.create(tmp_path, "empty", execution_mode=ExecutionMode.FIXTURE)
    with pytest.raises(EvidenceError):
        run.seal()


def test_run_creation_goes_through_the_firewall(tmp_path: Path) -> None:
    from landing_accessibility.engine.firewall import RealTargetBlockedError

    with pytest.raises(RealTargetBlockedError):
        EvidenceRun.create(tmp_path, "real", execution_mode="REAL_TARGET")


# ── 재수집 사전선언 (A2 §1.11.2 RC-1 ~ RC-4) ─────────────────────────────────
def _prereg(**kw: object) -> RecollectionPreregistration:
    base: dict = {
        "target_criterion_observation_ids": ["c1"],
        "reason_evidence_gap": 1,
        "reason_impact_level": "HIGH",
        "expected_evidence": ["probe"],
        "attempt_index": 1,
        "preregistered_at": "2026-08-27T08:00:00.000000Z",
    }
    return RecollectionPreregistration(**{**base, **kw})  # type: ignore[arg-type]


def test_preregistration_must_precede_collection() -> None:
    _prereg().validate(collection_started_at="2026-08-27T09:00:00.000000Z")
    with pytest.raises(PreregistrationError):
        _prereg(preregistered_at="2026-08-27T10:00:00.000000Z").validate(
            collection_started_at="2026-08-27T09:00:00.000000Z"
        )


def test_preregistration_cannot_name_an_always_produced_artifact() -> None:
    """`manifest` 는 늘 산출되므로 RC-3 교체조건을 자동 충족시킨다 — 금지 전이 X-14."""
    with pytest.raises(PreregistrationError):
        _prereg(expected_evidence=["manifest"]).validate(
            collection_started_at="2026-08-27T09:00:00.000000Z"
        )


def test_preregistration_requires_expected_evidence() -> None:
    with pytest.raises(PreregistrationError):
        _prereg(expected_evidence=[]).validate(collection_started_at="2026-08-27T09:00:00.000000Z")


# ── 정본 run 선택 (RC-3) ─────────────────────────────────────────────────────
def test_canonical_run_defaults_to_the_first_measured_run() -> None:
    chosen = select_canonical_run(
        [
            {"evidence_run_id": "r2", "measurement_status": "MEASURED"},
            {"evidence_run_id": "r1", "measurement_status": "MEASURED"},
        ]
    )
    assert chosen["evidence_run_id"] == "r1"


def test_recollection_replaces_canonical_only_when_expected_evidence_appeared() -> None:
    runs = [
        {"evidence_run_id": "r1", "measurement_status": "MEASURED"},
        {
            "evidence_run_id": "r2",
            "measurement_status": "MEASURED",
            "attempt_index": 1,
            "preregistration": {"expected_evidence": ["probe"]},
            "produced_evidence": ["probe", "dom"],
        },
    ]
    assert select_canonical_run(runs)["evidence_run_id"] == "r2"

    runs[1]["produced_evidence"] = ["dom"]
    assert select_canonical_run(runs)["evidence_run_id"] == "r1"


def test_canonical_selection_cannot_see_verdicts() -> None:
    """결과를 보고 run 을 고르는 경로를 **타입 수준에서** 닫는다 (금지 전이 X-14)."""
    with pytest.raises(EvidenceError):
        select_canonical_run(
            [
                {
                    "evidence_run_id": "r1",
                    "measurement_status": "MEASURED",
                    "verdict_state": "PASS",
                }
            ]
        )


def test_over_limit_recollection_is_never_canonical() -> None:
    assert MAX_RECOLLECTION_RUNS_PER_WEB_TARGET == 1
    chosen = select_canonical_run(
        [
            {"evidence_run_id": "r1", "measurement_status": "MEASURED"},
            {
                "evidence_run_id": "r2",
                "measurement_status": "MEASURED",
                "attempt_index": 2,
                "preregistration": {"expected_evidence": ["probe"]},
                "produced_evidence": ["probe"],
            },
        ]
    )
    assert chosen["evidence_run_id"] == "r1"
