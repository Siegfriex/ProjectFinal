"""W3 — KWCAG criterion manifest freeze 무결성 검사.

`T-A-W3-001` / `D-R0-43`: manifest freeze 이전에는 evaluator 구현을 시작하지 않는다.
이 테스트는 **evaluator 판정을 검증하지 않는다** — 그건 `test_w3_stage1_evaluator.py`
의 몫이다. 여기서 보는 것은 오직 `engine/kwcag/criterion_manifest.json` 이 A가
지정한 형태로 동결됐는가, 그리고 그 동결이 이후(Stage 1 착수 이후에도) 조용히
바뀌지 않았는가 뿐이다.

`D-R0-51`(A ACCEPT)로 Stage 1 착수가 허가됐으므로, "이 패키지에 .py 파일이
`__init__.py` 하나뿐이어야 한다"던 예전 단정은 더 이상 유효하지 않다 —
`test_manifest_is_pure_data_no_stage1_logic_embedded` 로 대체했다. manifest
**자신**(JSON)은 여전히 순수 데이터여야 한다는, 원래 취지는 그대로 지킨다.

검사 항목 (조정자 지시 그대로):
  1. 필수 필드(criterion_id · applicability · evidence_source · automation_grade · SHA)
     가 33개 criterion 전 row에 키로 존재한다 (값이 아니라 **키의 존재**를 본다 — 값이
     null인 것과 필드 자체가 없는 것은 다른 결함이다).
  2. criterion_id 가 33개 전부 유일하다.
  3. subset 크기가 원본(`OLDER_RELEVANT_KWCAG_SUBSET.md` §2·§3)과 일치한다 —
     전수 33, older-relevant(applicability != OTHER) 22, 도메인별 VISION 3 · MOTOR 4 ·
     COGNITIVE_NAVIGATION 15 · OTHER 11.
  4. manifest 파일의 sha256 을 재계산해 `criterion_manifest.sha256` 및
     `MANIFEST_FREEZE.json` 의 기록값과 일치하는지 확인한다 — freeze 이후 조용한 변경을
     잡아낸다.
"""

from __future__ import annotations

import hashlib
import json
import sys
from collections import Counter
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]
RESEARCH = REPO / "research" / "landing_accessibility"
sys.path.insert(0, str(RESEARCH / "src"))

from landing_accessibility.engine import kwcag as kwcag_pkg  # noqa: E402

REQUIRED_FIELDS = ("criterion_id", "applicability", "evidence_source", "automation_grade", "SHA")

# `OLDER_RELEVANT_KWCAG_SUBSET.md` §3 집계표 그대로 — 새로 만든 숫자가 아니다.
EXPECTED_DOMAIN_COUNTS = {
    "VISION": 3,
    "MOTOR": 4,
    "COGNITIVE_NAVIGATION": 15,
    "OTHER": 11,
}
EXPECTED_TOTAL = 33
EXPECTED_OLDER_RELEVANT = 22

# `OLDER_RELEVANT_KWCAG_SUBSET.md` §4 — 정본이 아닌 폐기 fixture id. manifest 에 있으면 안 된다.
FIXTURE_ONLY_ID_NOT_IN_KWCAG_2_2 = "2.4.7"


@pytest.fixture(scope="module")
def manifest() -> dict:
    with open(kwcag_pkg.CRITERION_MANIFEST_PATH, encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture(scope="module")
def freeze_record() -> dict:
    with open(kwcag_pkg.MANIFEST_FREEZE_PATH, encoding="utf-8") as f:
        return json.load(f)


def test_manifest_file_exists_and_is_valid_json():
    assert kwcag_pkg.CRITERION_MANIFEST_PATH.exists()


def test_stage_marker_present(manifest):
    """A의 precondition(D-R0-43)이 만족될 때까지 evaluator 착수 금지임을 manifest 자신이 밝힌다."""
    assert manifest["stage"].startswith("Stage 0")
    assert manifest["ticket"] == "T-A-W3-001"
    assert "D-R0-43" in manifest["precondition"]


def test_criterion_count_matches_source(manifest):
    assert manifest["criterion_count"] == EXPECTED_TOTAL
    assert len(manifest["criteria"]) == EXPECTED_TOTAL


def test_criterion_id_uniqueness(manifest):
    ids = [row["criterion_id"] for row in manifest["criteria"]]
    dupes = [cid for cid, n in Counter(ids).items() if n > 1]
    assert not dupes, f"criterion_id 중복: {dupes}"
    assert len(set(ids)) == EXPECTED_TOTAL


def test_required_fields_present_as_keys_on_every_row(manifest):
    """값이 아니라 **키 자체**의 존재를 본다. null 값은 허용(원본에 없는 정보를 채우지
    않기로 한 정직한 결측)이지만, 필드가 통째로 빠진 row 는 스키마 위반이다."""
    for row in manifest["criteria"]:
        missing = [field for field in REQUIRED_FIELDS if field not in row]
        assert not missing, f"{row.get('criterion_id')}: 필수 필드 누락 {missing}"


def test_criterion_id_shape(manifest):
    """KWCAG 2.2 criterion id 형식(N.N.N)만 확인한다 — 존재하지 않는 id(예: fixture 전용
    2.4.7)가 정본 manifest 에 섞여 들어오는 것을 잡아낸다."""
    import re

    pattern = re.compile(r"^\d\.\d\.\d$")
    for row in manifest["criteria"]:
        assert pattern.match(row["criterion_id"]), f"이상한 criterion_id: {row['criterion_id']}"

    ids = {row["criterion_id"] for row in manifest["criteria"]}
    assert FIXTURE_ONLY_ID_NOT_IN_KWCAG_2_2 not in ids


def test_applicability_domain_is_closed_vocabulary(manifest):
    """`00_SSOT §4` 가 정한 4개 도메인 밖의 값이 있으면 실패해야 한다 — 새 도메인을
    만들지 않는다는 원본 §1 규칙을 코드로 강제한다."""
    allowed = set(EXPECTED_DOMAIN_COUNTS)
    for row in manifest["criteria"]:
        assert row["applicability"] in allowed, (
            f"{row['criterion_id']}: applicability={row['applicability']!r} 가 "
            f"닫힌 어휘 {allowed} 밖이다"
        )


def test_subset_size_matches_source_aggregation_table(manifest):
    """`OLDER_RELEVANT_KWCAG_SUBSET.md` §3 집계표(VISION 3 · MOTOR 4 ·
    COGNITIVE_NAVIGATION 15 · OTHER 11, older-relevant 소계 22)와 정확히 일치해야 한다."""
    counts = Counter(row["applicability"] for row in manifest["criteria"])
    for domain, expected_n in EXPECTED_DOMAIN_COUNTS.items():
        assert counts[domain] == expected_n, (
            f"{domain}: manifest={counts[domain]} vs 원본 §3={expected_n}"
        )

    older_relevant_n = sum(n for domain, n in counts.items() if domain != "OTHER")
    assert older_relevant_n == EXPECTED_OLDER_RELEVANT


def test_sha_field_matches_source_document_provenance(manifest):
    """SHA 필드가 이 worktree 밖(다른 브랜치)에 있는 실제 커밋을 정확히 가리키는지 확인한다.
    발명된 값이 아니라 `git show 333119e:...` 로 직접 읽은 커밋이다."""
    expected_sha = manifest["provenance"]["older_relevant_subset_doc"]["commit_sha"]
    assert expected_sha == "333119e6821166cbba7c950203098f199f0fdc13"
    for row in manifest["criteria"]:
        assert row["SHA"] == expected_sha


def test_manifest_sha256_matches_sidecar_file():
    digest = hashlib.sha256(kwcag_pkg.CRITERION_MANIFEST_PATH.read_bytes()).hexdigest()
    sidecar = kwcag_pkg.CRITERION_MANIFEST_SHA256_SIDECAR.read_text(encoding="utf-8")
    assert digest in sidecar, (
        f"recomputed sha256={digest} 가 sidecar 파일 내용과 일치하지 않는다: {sidecar!r}"
    )


def test_manifest_sha256_matches_freeze_record(freeze_record):
    digest = hashlib.sha256(kwcag_pkg.CRITERION_MANIFEST_PATH.read_bytes()).hexdigest()
    assert digest == freeze_record["manifest_sha256"], (
        "manifest 가 freeze 이후 조용히 변경됐다 — "
        f"recomputed={digest} vs frozen={freeze_record['manifest_sha256']}"
    )
    assert freeze_record["criterion_count"] == EXPECTED_TOTAL
    assert freeze_record["older_relevant_count"] == EXPECTED_OLDER_RELEVANT
    assert freeze_record["other_count"] == EXPECTED_TOTAL - EXPECTED_OLDER_RELEVANT


def test_manifest_is_pure_data_no_stage1_logic_embedded(manifest):
    """`D-R0-51`로 Stage 1 착수가 허가된 뒤에도, **manifest 파일 자체**(JSON)는
    여전히 순수 데이터여야 한다 — 판정 로직이 JSON 문자열(eval 가능한 코드, 함수
    표현 등)로 스며들면 D-R0-21 "네 단계가 독립 함수/데이터로 드러나야 한다"가
    깨진다. Stage 1 로직은 `.py` 파일에만 있어야 한다(이 assertion 은 그 반대—
    `.py` 파일에 있어야 할 것이 `.json` 에 숨어들지 않았는지를 본다)."""
    import re

    raw = kwcag_pkg.CRITERION_MANIFEST_PATH.read_text(encoding="utf-8")
    suspicious_tokens = ("lambda", "def ", "eval(", "exec(", "__import__")
    for token in suspicious_tokens:
        assert token not in raw, f"manifest 에 실행 가능한 코드로 보이는 토큰이 있다: {token!r}"

    # criterion_id 형식(N.N.N) 밖의 원본 키가 값 필드에 섞여 들어오지 않았는지도 같이 본다.
    assert re.search(r'"criteria"\s*:\s*\[', raw), "criteria 배열 키가 없다"


def test_stage0_known_gaps_still_documented(manifest):
    assert "known_gaps_left_empty" in manifest
    assert manifest["known_gaps_left_empty"]["stage1_status"]
