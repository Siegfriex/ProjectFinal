"""C006 A2 인증 레지스트리 스냅샷 검증 — research/landing_accessibility/sources/certification.

이 스냅샷은 "인증 목록에 없음 = 인증 0건"이라는 부정 판정의 근거로 쓰인다.
그래서 검증의 핵심은 행 수가 아니라 (a) 원문이 남아 있고 레코드가 그 원문에서 나왔다는 것,
(b) 수집이 정상 완료됐다는 것, (c) 완료되지 않았다면 유효 판정 자체가 코드에서 막힌다는 것이다.
"""

from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path

import pandas as pd
import pytest

REPO = Path(__file__).resolve().parents[1]
RESEARCH = REPO / "research" / "landing_accessibility"
SOURCE_DIR = RESEARCH / "sources" / "certification"
RAW_DIR = SOURCE_DIR / "raw"

sys.path.insert(0, str(RESEARCH / "src"))

from landing_accessibility.registry import (  # noqa: E402
    RECORD_COLUMNS,
    STOP_OK,
    CrawlOutcome,
    IncompleteSnapshotError,
    PageResult,
    dedup_records,
    evaluate_completeness,
    sha256_hex,
    valid_at_audit_rows,
)

AUDIT_DATE = date(2026, 8, 26)
SNAPSHOT_ID = "KWACC_WA_20260826"


@pytest.fixture(scope="module")
def manifest() -> dict:
    path = SOURCE_DIR / "registry_snapshot_manifest.json"
    assert path.exists(), f"매니페스트 누락: {path}"
    return json.loads(path.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def registry() -> pd.DataFrame:
    path = SOURCE_DIR / "certification_registry.parquet"
    assert path.exists(), f"레지스트리 누락: {path}"
    return pd.read_parquet(path)


# ── 1. 식별자 유일성 ─────────────────────────────────────────────────────────


def test_certification_number_is_unique(registry: pd.DataFrame) -> None:
    assert registry["certification_number"].notna().all(), "certification_number 결측 행이 있다"
    dupes = registry.loc[
        registry["certification_number"].duplicated(keep=False), "certification_number"
    ].tolist()
    assert not dupes, f"중복 certification_number: {sorted(set(dupes))}"


def test_schema_matches_declared_columns(registry: pd.DataFrame) -> None:
    assert list(registry.columns) == RECORD_COLUMNS


def test_dedup_keeps_first_observation() -> None:
    rows = [
        {"certification_number": "1", "list_page": 1, "list_index": 1, "service_name": "first"},
        {"certification_number": "1", "list_page": 9, "list_index": 3, "service_name": "later"},
        {"certification_number": None, "list_page": 2, "list_index": 4, "service_name": "noseq"},
    ]
    out = dedup_records(rows)
    assert len(out) == 2
    assert out[0]["service_name"] == "first"


# ── 2. 원문 대조 ─────────────────────────────────────────────────────────────


def test_row_hashes_match_stored_raw_html(registry: pd.DataFrame, manifest: dict) -> None:
    """모든 행의 raw_sha256 이 실제 저장된 그 페이지 원문의 해시와 같아야 한다."""
    file_digest = {
        int(path.stem.split("_")[1]): sha256_hex(path.read_bytes())
        for path in sorted(RAW_DIR.glob("list_*.html"))
    }
    assert file_digest, "원문 스냅샷이 하나도 없다"

    mismatched: list[tuple[int, str]] = []
    for page, digest in registry.groupby("list_page")["raw_sha256"].unique().items():
        assert len(digest) == 1, f"page {page}: 한 페이지 안에서 raw_sha256 이 여럿이다"
        page_i = int(page)  # type: ignore[arg-type]
        if file_digest.get(page_i) != digest[0]:
            mismatched.append((page_i, str(digest[0])))
    assert not mismatched, f"원문 해시 불일치 페이지: {mismatched}"

    # 매니페스트의 페이지 해시도 실제 파일과 일치해야 한다.
    for entry in manifest["page_hashes"]:
        if not entry["raw_path"]:
            continue
        path = SOURCE_DIR / entry["raw_path"]
        assert path.exists(), f"원문 누락: {path}"
        assert sha256_hex(path.read_bytes()) == entry["raw_sha256"], (
            f"page {entry['page']} 원문 해시가 매니페스트와 다르다"
        )


# ── 3. 유효 후보 판정 ────────────────────────────────────────────────────────


def test_valid_candidates_are_in_period_at_audit(registry: pd.DataFrame, manifest: dict) -> None:
    audit_iso = AUDIT_DATE.isoformat()
    assert manifest["audit_date"] == audit_iso

    valid = registry[registry["cert_valid_candidate"] == 1]
    assert len(valid) > 0
    bad = valid[
        valid["cert_start_date"].isna()
        | valid["cert_end_date"].isna()
        | (valid["cert_start_date"] > audit_iso)
        | (valid["cert_end_date"] < audit_iso)
    ]
    assert bad.empty, (
        "감사일 기간을 벗어난 유효 후보: "
        f"{bad[['certification_number', 'cert_start_date', 'cert_end_date']].to_dict('records')}"
    )
    # 유효 후보는 목록 상태도 VALID 여야 한다.
    assert set(valid["certification_status_listed"]) == {"VALID"}
    assert (valid["in_period_at_audit"] == 1).all()

    # 기간 밖인데 유효 후보로 남은 행이 없어야 한다(역방향).
    in_period = registry["in_period_at_audit"] == 1
    listed_valid = registry["certification_status_listed"] == "VALID"
    assert int((in_period & listed_valid).sum()) == len(valid)
    assert manifest["valid_at_audit"] == len(valid)


def test_status_breakdown_matches_records(registry: pd.DataFrame, manifest: dict) -> None:
    actual = registry["certification_status_listed"].value_counts().to_dict()
    declared = manifest["status_breakdown"]
    for key in ("VALID", "EXPIRED", "UNKNOWN"):
        assert declared[key] == int(actual.get(key, 0)), f"{key} 집계 불일치"
    assert manifest["rows_dedup"] == len(registry)


# ── 4. 완결성 계약 (코드 강제) ───────────────────────────────────────────────


def test_snapshot_is_complete(manifest: dict) -> None:
    assert manifest["snapshot_id"] == SNAPSHOT_ID
    assert manifest["authority_rank"] == "A2"
    assert manifest["snapshot_status"] == "COMPLETE"
    assert manifest["stop_reason"] == STOP_OK
    assert manifest["completeness_notes"] == []
    assert manifest["declared_last_page"] == manifest["pages_with_cards"]
    assert manifest["crawler_version"]


def test_valid_judgement_requires_complete_snapshot(registry: pd.DataFrame, manifest: dict) -> None:
    """INCOMPLETE 스냅샷으로 유효 판정을 시도하면 코드가 막아야 한다."""
    records = registry.to_dict("records")

    ok = valid_at_audit_rows(records, manifest)
    assert len(ok) == manifest["valid_at_audit"]

    for bad_status, stop in [
        ("INCOMPLETE", "TRANSPORT_OR_STATUS"),
        ("INCOMPLETE", "EARLY_PAGE_TERMINATION"),
        ("INCOMPLETE", "RAW_SNAPSHOT_MISSING"),
        ("INCOMPLETE", "DUPLICATE_PAGE"),
        (None, None),
    ]:
        broken = {**manifest, "snapshot_status": bad_status, "stop_reason": stop}
        with pytest.raises(IncompleteSnapshotError):
            valid_at_audit_rows(records, broken)


def _page(page: int, cards: int, *, error: str | None = None, raw: bool = True) -> PageResult:
    return PageResult(
        page=page,
        url=f"u{page}",
        http_status=None if error else 200,
        error=error,
        attempts=1,
        collected_at="2026-08-26T00:00:00+00:00",
        raw_sha256=None if error else "0" * 64,
        raw_path=f"raw/list_{page:04d}.html" if raw and not error else None,
        card_count=cards,
    )


@pytest.mark.parametrize(
    ("stop_reason", "declared", "pages", "expected_stop", "expected_status"),
    [
        (
            "TRANSPORT_OR_STATUS",
            3,
            [_page(1, 10), _page(2, 0, error="Timeout")],
            "TRANSPORT_OR_STATUS",
            "INCOMPLETE",
        ),
        ("DUPLICATE_PAGE", 3, [_page(1, 10), _page(2, 10)], "DUPLICATE_PAGE", "INCOMPLETE"),
        (STOP_OK, 3, [_page(1, 10), _page(2, 0)], "EARLY_PAGE_TERMINATION", "INCOMPLETE"),
        (STOP_OK, None, [_page(1, 10), _page(2, 0)], "UNKNOWN_LAST_PAGE", "INCOMPLETE"),
        (
            STOP_OK,
            1,
            [_page(1, 10), _page(2, 10), _page(3, 0)],
            "DECLARED_LAST_PAGE_EXCEEDED",
            "INCOMPLETE",
        ),
        (STOP_OK, 2, [_page(1, 10), _page(2, 3), _page(3, 0)], STOP_OK, "COMPLETE"),
    ],
)
def test_completeness_gate_classifies_stop_reasons(
    stop_reason: str,
    declared: int | None,
    pages: list[PageResult],
    expected_stop: str,
    expected_status: str,
) -> None:
    outcome = CrawlOutcome(pages=list(pages), declared_last_page=declared, stop_reason=stop_reason)
    got_stop, got_status, _ = evaluate_completeness(outcome)
    assert (got_stop, got_status) == (expected_stop, expected_status)


# ── 5. 페이지 수 ↔ 원문 파일 수 ──────────────────────────────────────────────


def test_page_count_matches_stored_html_files(registry: pd.DataFrame, manifest: dict) -> None:
    files = sorted(RAW_DIR.glob("list_*.html"))
    assert len(files) == manifest["pages_fetched"], (
        f"원문 파일 {len(files)}개 ≠ pages_fetched {manifest['pages_fetched']}"
    )
    assert len(manifest["page_hashes"]) == manifest["pages_fetched"]

    numbers = [int(p.stem.split("_")[1]) for p in files]
    assert numbers == list(range(1, len(files) + 1)), f"페이지 번호가 연속이지 않다: {numbers}"

    # 레코드가 존재하는 페이지는 카드가 있던 페이지와 정확히 같아야 한다.
    pages_with_cards = {e["page"] for e in manifest["page_hashes"] if e["card_count"] > 0}
    assert set(registry["list_page"].astype(int)) == pages_with_cards
    assert len(pages_with_cards) == manifest["pages_with_cards"]

    # 페이지별 카드 수와 레코드 수가 일치해야 한다(중복 제거로 사라진 행이 없다).
    per_page = registry.groupby("list_page").size().to_dict()
    for entry in manifest["page_hashes"]:
        if entry["card_count"]:
            assert per_page.get(entry["page"]) == entry["card_count"], (
                f"page {entry['page']}: 카드 {entry['card_count']} ≠ 레코드 {per_page.get(entry['page'])}"
            )
    assert manifest["rows_raw"] == manifest["rows_dedup"] == len(registry)
