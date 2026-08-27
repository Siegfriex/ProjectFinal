"""W5A — TaskRegistryLoader 회귀검사.

정본은 동결 MAIN50 manifest, 대조군은 SSOTV3 registry CSV/JSON 이다.
**실사이트에 접속하지 않는다** — 전부 `tests/fixtures/w5a_v3/` 에 커밋된 바이트 사본과
`tmp_path` 에 만든 변형본만 읽는다. 운영 경로 탐색에 의존하지 않는다.

실행:
    /home/sieg/projects-wsl/ProjectFinal/.venv/bin/python -m pytest \\
        tests/test_w5a_task_registry.py -q
"""

from __future__ import annotations

import ast
import hashlib
import json
import shutil
import sys
from collections import Counter
from pathlib import Path
from typing import Any

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "research" / "landing_accessibility" / "src"))

from landing_accessibility.v3_runner import registry as reg  # noqa: E402
from landing_accessibility.v3_runner.contracts import (  # noqa: E402
    FIXTURE_INPUT_MODES,
    TASK_ROLES,
    TaskContract,
)

FIXTURE_DIR = REPO_ROOT / "tests" / "fixtures" / "w5a_v3"
MANIFEST_FIXTURE = FIXTURE_DIR / "FINAL_MAIN50_MANIFEST.json"
CONTROL_DIR = FIXTURE_DIR / "ssot_control"

# --- 고정된 사실 (B 실측 · C 독립 재계산 · A T-A-V3-STEP1-002 정정본과 일치) --------------
FROZEN_MANIFEST_FILE_SHA256 = "ef4e19ad2cf5da62dea518af932d3653759807359cec4a410788f996ecf703f0"
FROZEN_MANIFEST_BODY_SHA256 = "81d55db916866550a8e836231283357c5191c38edf762a739da9020c8687dc1d"
# superseded v3.0.1. 어떤 검증에도 쓰지 않는다 — 혼동 방지를 위해 "다르다" 는 사실만 고정한다.
SUPERSEDED_V301_BODY_SHA256 = "25ce482ddb13269168a0b07c79726c9e1297afc9c7522c125d8b350b3717af1b"
CONTROL_CSV_SHA256 = "521b65f71eea7599b693ea06ed4c1e6dc426d49b5d332247669d93aee5d4efc6"
CONTROL_JSON_SHA256 = "b421988df07feca37ba127f180b2a4c61972113cab5643a6d8985208095bdaef"
FROZEN_MANIFEST_VERSION = "3.0.2"
EXPECTED_PILOT_IDS = ("F1-01", "F2-01", "F3-01", "F4-01", "F5-01")
EXPECTED_STRATA = {"시중": 7, "지방": 3, "_": 30, "ground": 5, "air": 5}
EXPECTED_REPLACEMENT_RESERVE = 31  # A 티켓은 32 라고 했으나 실측은 31 이다


# ======================================================================================
# 헬퍼 — 픽스처 사본 만들기 / 변형하기
# ======================================================================================


def _sha256_bytes(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _load_manifest_doc() -> dict[str, Any]:
    return json.loads(MANIFEST_FIXTURE.read_text(encoding="utf-8"))


def _freeze_manifest(document: dict[str, Any]) -> dict[str, Any]:
    """``manifest_sha256`` 를 문서에 맞게 다시 계산해 넣는다 (A 의 동결 레시피와 동일)."""
    body = {k: v for k, v in document.items() if k != reg.MANIFEST_HASH_FIELD}
    document[reg.MANIFEST_HASH_FIELD] = hashlib.sha256(
        json.dumps(body, ensure_ascii=False, indent=1).encode("utf-8")
    ).hexdigest()
    return document


def _materialize(
    tmp_path: Path,
    *,
    manifest: dict[str, Any] | None = None,
    refreeze: bool = True,
) -> tuple[Path, Path]:
    """픽스처를 ``tmp_path`` 로 복사하고 (선택적으로 변형한) manifest 경로/대조군 경로를 준다."""
    control = tmp_path / "ssot_control"
    shutil.copytree(CONTROL_DIR, control)
    manifest_path = tmp_path / "FINAL_MAIN50_MANIFEST.json"
    if manifest is None:
        shutil.copyfile(MANIFEST_FIXTURE, manifest_path)
    else:
        if refreeze:
            _freeze_manifest(manifest)
        manifest_path.write_text(
            json.dumps(manifest, ensure_ascii=False, indent=1), encoding="utf-8"
        )
    return manifest_path, control


def _load(tmp_path: Path, **kwargs: Any) -> reg.TaskRegistry:
    manifest_path, control = _materialize(tmp_path, **kwargs)
    return reg.load_task_registry(manifest_path, registry_path=control)


def _patch_control_csv(control_dir: Path, target_id: str, column: str, value: str) -> None:
    path = control_dir / reg.TASK_REGISTRY_CSV_NAME
    text = path.read_text(encoding="utf-8-sig")
    import csv as _csv
    import io

    reader = _csv.DictReader(io.StringIO(text))
    fieldnames = [n.lstrip("﻿") for n in (reader.fieldnames or [])]
    rows = []
    for row in reader:
        clean = {k.lstrip("﻿"): (v or "") for k, v in row.items()}
        if clean["target_id"] == target_id:
            clean[column] = value
        rows.append(clean)
    buffer = io.StringIO()
    writer = _csv.DictWriter(buffer, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(rows)
    path.write_text("﻿" + buffer.getvalue(), encoding="utf-8")


def _patch_control_json(control_dir: Path, target_id: str, key: str, value: Any) -> None:
    path = control_dir / reg.TARGET_FRAME_JSON_NAME
    document = json.loads(path.read_text(encoding="utf-8"))
    for entry in document["targets"]:
        if entry["target_id"] == target_id:
            entry[key] = value
    path.write_text(json.dumps(document, ensure_ascii=False, indent=1), encoding="utf-8")


def _manifest_target(document: dict[str, Any], target_id: str) -> dict[str, Any]:
    for entry in document["targets"]:
        if entry["target_id"] == target_id:
            return entry
    raise AssertionError(f"픽스처에 {target_id} 가 없다")


# ======================================================================================
# 0. 픽스처 자체의 신원 — 이후 모든 주장의 전제
# ======================================================================================


def test_fixture_is_the_frozen_manifest_bytes() -> None:
    """커밋된 픽스처가 origin/control 691926f8 의 동결 manifest 와 byte-identical 하다."""
    assert _sha256_bytes(MANIFEST_FIXTURE.read_bytes()) == FROZEN_MANIFEST_FILE_SHA256
    assert (
        _sha256_bytes((CONTROL_DIR / reg.TASK_REGISTRY_CSV_NAME).read_bytes()) == CONTROL_CSV_SHA256
    )
    assert (
        _sha256_bytes((CONTROL_DIR / reg.TARGET_FRAME_JSON_NAME).read_bytes())
        == CONTROL_JSON_SHA256
    )


def test_manifest_body_hash_and_file_hash_are_different_and_both_pinned() -> None:
    """A 가 명시적으로 경고한 지점: body 해시와 파일 해시는 서로 다른 값이 정상이다."""
    raw = MANIFEST_FIXTURE.read_bytes()
    document = _load_manifest_doc()

    file_hash = reg.compute_manifest_file_sha256(raw)
    body_hash = reg.compute_manifest_body_sha256(document)

    assert file_hash == FROZEN_MANIFEST_FILE_SHA256
    assert body_hash == FROZEN_MANIFEST_BODY_SHA256
    assert file_hash != body_hash
    # 파일이 스스로 선언한 값 == body 해시
    assert document[reg.MANIFEST_HASH_FIELD] == body_hash
    # superseded v3.0.1 해시와는 다르다 (그 값을 쓰면 안 된다는 사실의 고정)
    assert body_hash != SUPERSEDED_V301_BODY_SHA256


def test_manifest_body_hash_recipe_is_indent1_no_sort_keys() -> None:
    """정규화 방식 고정: ``indent=1 · ensure_ascii=False · sort_keys 없음`` 만 일치한다."""
    document = _load_manifest_doc()
    body = {k: v for k, v in document.items() if k != reg.MANIFEST_HASH_FIELD}

    def digest(text: str) -> str:
        return hashlib.sha256(text.encode("utf-8")).hexdigest()

    correct = digest(json.dumps(body, ensure_ascii=False, indent=1))
    assert correct == FROZEN_MANIFEST_BODY_SHA256

    # 양성 대조에 대한 음성 대조 — 다른 후보는 전부 다른 값을 낸다.
    for wrong in (
        json.dumps(body, ensure_ascii=False, indent=2),
        json.dumps(body, ensure_ascii=False, indent=1, sort_keys=True),
        json.dumps(body, ensure_ascii=True, indent=1),
        json.dumps(body, ensure_ascii=False, separators=(",", ":")),
    ):
        assert digest(wrong) != FROZEN_MANIFEST_BODY_SHA256


def test_manifest_source_pack_points_at_the_control_json() -> None:
    """manifest 가 선언한 source_pack sha256 이 실제 대조군 JSON 바이트와 같다."""
    document = _load_manifest_doc()
    assert document["source_pack"]["sha256"] == CONTROL_JSON_SHA256


# ======================================================================================
# 1. 양성 대조 — 정상 입력은 통과한다
# ======================================================================================


def test_positive_control_loads_fifty_contracts(tmp_path: Path) -> None:
    registry = _load(tmp_path)
    assert isinstance(registry, reg.TaskRegistry)
    assert len(registry.all()) == reg.EXPECTED_TARGET_COUNT == 50
    assert all(isinstance(c, TaskContract) for c in registry.all())
    assert registry.manifest_version == FROZEN_MANIFEST_VERSION
    assert registry.manifest_status == "FROZEN"
    assert registry.control_verified() is True
    assert registry.control_csv_sha256 == CONTROL_CSV_SHA256
    assert registry.control_json_sha256 == CONTROL_JSON_SHA256
    assert registry.manifest_file_sha256 == FROZEN_MANIFEST_FILE_SHA256
    assert registry.manifest_body_sha256 == FROZEN_MANIFEST_BODY_SHA256


def test_positive_control_ten_targets_per_family(tmp_path: Path) -> None:
    registry = _load(tmp_path)
    per_family = Counter(c.family_id for c in registry.all())
    assert dict(per_family) == {"F1": 10, "F2": 10, "F3": 10, "F4": 10, "F5": 10}
    assert registry.family_ids() == ("F1", "F2", "F3", "F4", "F5")
    for family_id in registry.family_ids():
        assert len(registry.by_family(family_id)) == reg.EXPECTED_TARGETS_PER_FAMILY


def test_positive_control_target_ids_unique(tmp_path: Path) -> None:
    ids = [c.target_id for c in _load(tmp_path).all()]
    assert len(ids) == len(set(ids)) == 50


def test_collection_order_is_preserved_not_resorted(tmp_path: Path) -> None:
    """정렬은 그 자체로 자유도다. 로더는 manifest 배열 순서를 그대로 둔다."""
    registry = _load(tmp_path)
    assert [c.collection_order for c in registry.all()] == list(range(1, 51))
    manifest_order = [t["target_id"] for t in _load_manifest_doc()["targets"]]
    assert [c.target_id for c in registry.all()] == manifest_order


def test_pilot_5_flags_match_manifest_declaration(tmp_path: Path) -> None:
    registry = _load(tmp_path)
    assert tuple(c.target_id for c in registry.pilot_5()) == EXPECTED_PILOT_IDS
    assert len(registry.pilot_5()) == reg.EXPECTED_PILOT_COUNT


def test_stratum_is_preserved_verbatim_including_underscore(tmp_path: Path) -> None:
    """F1·F5 만 층이 있고 나머지는 문자열 ``"_"`` 다. ``None`` 으로 바꾸지 않는다."""
    registry = _load(tmp_path)
    assert Counter(c.stratum for c in registry.all()) == Counter(EXPECTED_STRATA)
    assert all(c.stratum == "_" for c in registry.by_family("F2"))


def test_forbidden_actions_come_from_the_manifest_and_are_never_empty(tmp_path: Path) -> None:
    registry = _load(tmp_path)
    for contract in registry.all():
        assert contract.forbidden_actions, f"{contract.target_id}: forbidden_actions 가 비었다"
        assert all(isinstance(a, str) for a in contract.forbidden_actions)
    f1 = registry.by_target_id("F1-01")
    assert "credential 입력" in f1.forbidden_actions
    assert "이체 실행" in f1.forbidden_actions


def test_real_target_allowed_is_preserved_false(tmp_path: Path) -> None:
    """이 manifest 는 frame 동결이지 수집 허가가 아니다."""
    assert _load(tmp_path).real_target_allowed is False


def test_fixture_fields_preserve_source_strings(tmp_path: Path) -> None:
    registry = _load(tmp_path)
    f1 = registry.by_target_id("F1-01")
    assert f1.fixed_fixture == "없음"  # 해석하지 않고 문자열 그대로 보존
    assert f1.fixture_override is None  # manifest 의 "" 는 override 없음
    f5 = registry.by_target_id("F5-01")
    assert f5.fixture_override == "출발=서울역; 도착=부산역; 날짜=T+1; 성인=1"
    assert f1.service == "NH농협은행"
    assert f1.starting_url == "https://bank.nonghyup.com/"
    assert f1.frozen_task == "개인뱅킹 계좌이체/송금 기능 진입"


def test_lookup_api(tmp_path: Path) -> None:
    registry = _load(tmp_path)
    assert registry.by_target_id("F3-07").target_id == "F3-07"
    assert len(registry.by_family("F4")) == 10
    assert registry.all() is registry.contracts
    assert len(registry) == 50
    assert [c.target_id for c in registry][:2] == ["F1-01", "F1-02"]
    with pytest.raises(reg.RegistryLookupError):
        registry.by_target_id("F9-99")
    with pytest.raises(reg.RegistryLookupError):
        registry.by_family("F9")


# ======================================================================================
# 2. 두 소스 대조 — 일치를 고정하고, 불일치는 검출한다
# ======================================================================================


def test_manifest_and_control_agree_on_every_shared_field(tmp_path: Path) -> None:
    """현재 정본과 대조군은 겹치는 모든 필드에서 byte-exact 로 일치한다 (실측)."""
    registry = _load(tmp_path)  # 대조 실패 시 여기서 이미 예외
    assert registry.control_verified()

    import csv as _csv

    csv_rows = {
        r["target_id"].lstrip("﻿"): r
        for r in _csv.DictReader(
            (CONTROL_DIR / reg.TASK_REGISTRY_CSV_NAME).read_text(encoding="utf-8-sig").splitlines()
        )
    }
    checked = 0
    for contract in registry.all():
        row = csv_rows[contract.target_id]
        assert contract.family_id == row["family_id"]
        assert contract.service == row["service_name"]
        assert contract.starting_url == row["official_entry_url"]
        assert contract.frozen_task == row["matched_task"]
        assert contract.task_instruction == row["task_instruction"]
        assert contract.fixed_fixture == row["fixed_fixture"]
        assert contract.fixture_override == (row["fixture_override"] or None)
        assert contract.endpoint_contract == row["endpoint_contract"]
        assert contract.mobile_web_eligibility == row["mobile_web_eligibility"]
        checked += 1
    assert checked == 50


def test_control_uncovered_fields_are_declared() -> None:
    """대조군이 검증하지 **못하는** 필드가 명시되어 있어야 한다."""
    assert set(reg.CONTROL_UNCOVERED_FIELDS) == {
        "collection_order",
        "stratum",
        "is_pilot_5",
        "forbidden_actions",
    }


@pytest.mark.parametrize(
    ("column", "json_key", "value"),
    [
        ("service_name", "service_name", "다른 은행"),
        ("official_entry_url", "official_entry_url", "https://example.invalid/"),
        ("endpoint_contract", "endpoint_contract", "완전히 다른 endpoint 정의"),
    ],
)
def test_control_divergence_raises_conflict(
    tmp_path: Path, column: str, json_key: str, value: str
) -> None:
    """대조군만 바뀌면 조용히 하나를 고르지 않고 RegistryConflictError 를 던진다."""
    manifest_path, control = _materialize(tmp_path)
    _patch_control_csv(control, "F2-03", column, value)
    _patch_control_json(control, "F2-03", json_key, value)

    with pytest.raises(reg.RegistryConflictError) as excinfo:
        reg.load_task_registry(manifest_path, registry_path=control)
    message = str(excinfo.value)
    assert "F2-03" in message
    assert column in message or json_key in message


def test_conflict_message_names_every_diverging_field(tmp_path: Path) -> None:
    manifest_path, control = _materialize(tmp_path)
    _patch_control_csv(control, "F1-05", "service_name", "X")
    _patch_control_csv(control, "F3-02", "official_entry_url", "https://x.invalid/")
    with pytest.raises(reg.RegistryConflictError) as excinfo:
        reg.load_task_registry(manifest_path, registry_path=control)
    message = str(excinfo.value)
    assert "F1-05" in message and "F3-02" in message


# ======================================================================================
# 3. 해시 결정성
# ======================================================================================


def test_hashes_are_deterministic_across_loads(tmp_path: Path) -> None:
    first = _load(tmp_path / "a")
    second = _load(tmp_path / "b")
    assert [c.task_contract_hash for c in first.all()] == [
        c.task_contract_hash for c in second.all()
    ]
    assert [c.endpoint_contract_hash for c in first.all()] == [
        c.endpoint_contract_hash for c in second.all()
    ]
    assert len({c.task_contract_hash for c in first.all()}) == 50  # 50건 전부 서로 다름


def test_task_contract_hash_matches_the_documented_recipe(tmp_path: Path) -> None:
    """docstring 의 정규화 절차를 테스트가 **독립적으로** 재현한다 (C 의 재계산 리허설)."""
    registry = _load(tmp_path)
    payload_fields = list(reg.CONTRACT_HASH_PAYLOAD_FIELDS)
    assert "task_contract_hash" not in payload_fields
    assert "endpoint_contract_hash" in payload_fields

    for contract in registry.all():
        payload = {name: getattr(contract, name) for name in payload_fields}
        payload["forbidden_actions"] = list(payload["forbidden_actions"])
        serialized = json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
        expected = hashlib.sha256(serialized.encode("utf-8")).hexdigest()
        assert contract.task_contract_hash == expected
        assert contract.endpoint_contract_hash == (
            hashlib.sha256(contract.endpoint_contract.encode("utf-8")).hexdigest()
        )
        assert reg.recompute_task_contract_hash(contract) == expected


def test_one_character_change_in_endpoint_contract_changes_both_hashes(tmp_path: Path) -> None:
    baseline = _load(tmp_path / "base")
    before = baseline.by_target_id("F1-01")

    document = _load_manifest_doc()
    target = _manifest_target(document, "F1-01")
    mutated_endpoint = target["endpoint_contract"] + "."  # 딱 한 글자
    target["endpoint_contract"] = mutated_endpoint

    tmp = tmp_path / "mut"
    manifest_path, control = _materialize(tmp, manifest=document)
    _patch_control_csv(control, "F1-01", "endpoint_contract", mutated_endpoint)
    _patch_control_json(control, "F1-01", "endpoint_contract", mutated_endpoint)
    after = reg.load_task_registry(manifest_path, registry_path=control).by_target_id("F1-01")

    assert after.endpoint_contract_hash != before.endpoint_contract_hash
    assert after.task_contract_hash != before.task_contract_hash
    # 다른 target 은 영향을 받지 않는다
    other_before = baseline.by_target_id("F2-01").task_contract_hash
    other_after = (
        reg.load_task_registry(manifest_path, registry_path=control)
        .by_target_id("F2-01")
        .task_contract_hash
    )
    assert other_before == other_after


def test_non_endpoint_change_moves_only_the_contract_hash(tmp_path: Path) -> None:
    before = _load(tmp_path / "base").by_target_id("F2-04")

    document = _load_manifest_doc()
    _manifest_target(document, "F2-04")["service_name"] = "변경된 서비스명"
    tmp = tmp_path / "mut"
    manifest_path, control = _materialize(tmp, manifest=document)
    _patch_control_csv(control, "F2-04", "service_name", "변경된 서비스명")
    _patch_control_json(control, "F2-04", "service_name", "변경된 서비스명")
    after = reg.load_task_registry(manifest_path, registry_path=control).by_target_id("F2-04")

    assert after.endpoint_contract_hash == before.endpoint_contract_hash
    assert after.task_contract_hash != before.task_contract_hash


# ======================================================================================
# 4. fail-closed 5종 (+ 정본 특유의 불변조건)
# ======================================================================================


def test_failclosed_1_missing_manifest_does_not_fall_back_to_ssotv3(tmp_path: Path) -> None:
    """가장 위험한 실패 양식: manifest 부재 시 candidate frame 으로 조용히 대체하는 것."""
    _, control = _materialize(tmp_path)
    assert (control / reg.TASK_REGISTRY_CSV_NAME).is_file()  # 대조군은 멀쩡히 있다
    missing = tmp_path / "does_not_exist" / "FINAL_MAIN50_MANIFEST.json"

    with pytest.raises(reg.RegistrySourceMissingError) as excinfo:
        reg.load_task_registry(missing, registry_path=control)
    assert "FINAL_MAIN50_MANIFEST" in str(excinfo.value)


def test_failclosed_1b_missing_control_directory(tmp_path: Path) -> None:
    manifest_path, _ = _materialize(tmp_path)
    with pytest.raises(reg.RegistrySourceMissingError):
        reg.load_task_registry(manifest_path, registry_path=tmp_path / "no_such_dir")


def test_failclosed_1c_control_dir_present_but_files_missing(tmp_path: Path) -> None:
    manifest_path, control = _materialize(tmp_path)
    (control / reg.TASK_REGISTRY_CSV_NAME).unlink()
    with pytest.raises(reg.RegistrySourceMissingError):
        reg.load_task_registry(manifest_path, registry_path=control)


def test_failclosed_2_manifest_parse_failure(tmp_path: Path) -> None:
    _, control = _materialize(tmp_path)
    broken = tmp_path / "broken.json"
    broken.write_text('{"frame_id": "x", "targets": [', encoding="utf-8")
    with pytest.raises(reg.RegistryParseError):
        reg.load_task_registry(broken, registry_path=control)


def test_failclosed_2b_control_csv_parse_failure(tmp_path: Path) -> None:
    manifest_path, control = _materialize(tmp_path)
    (control / reg.TASK_REGISTRY_CSV_NAME).write_text(
        "target_id,family_id\nF1-01,F1\n", encoding="utf-8"
    )
    with pytest.raises(reg.RegistryParseError) as excinfo:
        reg.load_task_registry(manifest_path, registry_path=control)
    assert "필수 컬럼" in str(excinfo.value)


def test_failclosed_2c_manifest_missing_required_target_key(tmp_path: Path) -> None:
    document = _load_manifest_doc()
    del document["targets"][7]["forbidden_actions"]
    manifest_path, control = _materialize(tmp_path, manifest=document)
    with pytest.raises(reg.RegistryParseError) as excinfo:
        reg.load_task_registry(manifest_path, registry_path=control)
    assert "forbidden_actions" in str(excinfo.value)


def test_failclosed_3_target_count_not_fifty(tmp_path: Path) -> None:
    document = _load_manifest_doc()
    document["targets"] = document["targets"][:49]
    document["target_count"] = 49  # 선언까지 맞춰도 50 이 아니면 거부한다
    for index, entry in enumerate(document["targets"], start=1):
        entry["collection_order"] = index
    manifest_path, control = _materialize(tmp_path, manifest=document)
    with pytest.raises(reg.RegistryIntegrityError) as excinfo:
        reg.load_task_registry(manifest_path, registry_path=control)
    assert "50" in str(excinfo.value)


def test_failclosed_3b_declared_count_disagrees_with_array(tmp_path: Path) -> None:
    document = _load_manifest_doc()
    document["target_count"] = 49
    manifest_path, control = _materialize(tmp_path, manifest=document)
    with pytest.raises(reg.RegistryIntegrityError) as excinfo:
        reg.load_task_registry(manifest_path, registry_path=control)
    assert "target_count" in str(excinfo.value)


def test_failclosed_4_family_imbalance(tmp_path: Path) -> None:
    document = _load_manifest_doc()
    _manifest_target(document, "F2-10")["family_id"] = "F1"  # 11 / 9
    manifest_path, control = _materialize(tmp_path, manifest=document)
    with pytest.raises(reg.RegistryIntegrityError) as excinfo:
        reg.load_task_registry(manifest_path, registry_path=control)
    message = str(excinfo.value)
    assert "F1" in message and "11" in message


def test_failclosed_5_duplicate_target_id(tmp_path: Path) -> None:
    document = _load_manifest_doc()
    _manifest_target(document, "F3-05")["target_id"] = "F3-04"
    manifest_path, control = _materialize(tmp_path, manifest=document)
    with pytest.raises(reg.RegistryIntegrityError) as excinfo:
        reg.load_task_registry(manifest_path, registry_path=control)
    assert "F3-04" in str(excinfo.value)


def test_failclosed_manifest_body_hash_mismatch(tmp_path: Path) -> None:
    """동결 후 본문이 손대어졌는데 해시 필드는 그대로인 경우."""
    document = _load_manifest_doc()
    _manifest_target(document, "F4-01")["service_name"] = "몰래 바꾼 서비스명"
    manifest_path, control = _materialize(tmp_path, manifest=document, refreeze=False)
    with pytest.raises(reg.RegistryIntegrityError) as excinfo:
        reg.load_task_registry(manifest_path, registry_path=control)
    assert reg.MANIFEST_HASH_FIELD in str(excinfo.value)


def test_failclosed_status_not_frozen(tmp_path: Path) -> None:
    document = _load_manifest_doc()
    document["status"] = "CANDIDATE"
    manifest_path, control = _materialize(tmp_path, manifest=document)
    with pytest.raises(reg.RegistryIntegrityError) as excinfo:
        reg.load_task_registry(manifest_path, registry_path=control)
    assert "FROZEN" in str(excinfo.value)


def test_failclosed_empty_forbidden_actions(tmp_path: Path) -> None:
    """빈 forbidden_actions 는 guard 를 fail-open 시키므로 거부한다."""
    document = _load_manifest_doc()
    _manifest_target(document, "F5-03")["forbidden_actions"] = []
    manifest_path, control = _materialize(tmp_path, manifest=document)
    with pytest.raises(reg.RegistryParseError) as excinfo:
        reg.load_task_registry(manifest_path, registry_path=control)
    assert "F5-03" in str(excinfo.value)


def test_failclosed_collection_order_resorted(tmp_path: Path) -> None:
    document = _load_manifest_doc()
    document["targets"] = list(reversed(document["targets"]))
    manifest_path, control = _materialize(tmp_path, manifest=document)
    with pytest.raises(reg.RegistryIntegrityError) as excinfo:
        reg.load_task_registry(manifest_path, registry_path=control)
    assert "collection_order" in str(excinfo.value)


def test_failclosed_pilot_flag_disagrees_with_declaration(tmp_path: Path) -> None:
    document = _load_manifest_doc()
    _manifest_target(document, "F1-02")["is_pilot_5"] = True  # 6건이 된다
    manifest_path, control = _materialize(tmp_path, manifest=document)
    with pytest.raises(reg.RegistryIntegrityError) as excinfo:
        reg.load_task_registry(manifest_path, registry_path=control)
    assert "pilot_5" in str(excinfo.value)


def test_failclosed_target_set_disagrees_with_control(tmp_path: Path) -> None:
    document = _load_manifest_doc()
    _manifest_target(document, "F4-09")["target_id"] = "F4-99"
    manifest_path, control = _materialize(tmp_path, manifest=document)
    with pytest.raises(reg.RegistryIntegrityError) as excinfo:
        reg.load_task_registry(manifest_path, registry_path=control)
    assert "F4-99" in str(excinfo.value)


def test_positive_control_after_every_failclosed_case(tmp_path: Path) -> None:
    """음성 대조들 바로 옆의 양성 대조 — 손대지 않은 픽스처는 여전히 통과한다.

    무결과와 통과가 같은 출력으로 나오지 않는다는 것을 같은 파일 안에서 보인다.
    """
    registry = _load(tmp_path)
    assert len(registry) == 50
    assert registry.manifest_status == "FROZEN"


# ======================================================================================
# 5. 운영 기본 경로 — 이 트리에서는 아직 부재이며, 그 사실이 fail-closed 로 드러난다
# ======================================================================================


def test_default_manifest_path_is_the_frozen_control_path() -> None:
    assert reg.MANIFEST_RELPATH == "control/v3/FINAL_MAIN50_MANIFEST.json"
    assert reg.DEFAULT_MANIFEST_PATH.as_posix().endswith(
        "research/landing_accessibility/" + reg.MANIFEST_RELPATH
    )


def test_default_path_either_matches_the_pinned_bytes_or_fails_closed() -> None:
    """실물이 이 트리에 들어오면 픽스처와 byte-대조하고, 없으면 부재가 예외로 드러난다.

    조용한 skip 을 두지 않는다 — 두 갈래 모두 단언한다.
    """
    if reg.DEFAULT_MANIFEST_PATH.is_file():
        assert (
            _sha256_bytes(reg.DEFAULT_MANIFEST_PATH.read_bytes()) == FROZEN_MANIFEST_FILE_SHA256
        ), "트리의 동결 manifest 가 픽스처와 다르다 — 재동결이 있었는지 확인하고 픽스처를 갱신하라"
    else:
        with pytest.raises(reg.RegistrySourceMissingError):
            reg.resolve_manifest_path(None)


def test_replacement_reserve_is_thirty_one_not_thirty_two() -> None:
    """A 티켓 기재(32)와 실측(31)이 다르다. 실측값을 고정한다."""
    document = _load_manifest_doc()
    assert len(document["replacement_reserve"]) == EXPECTED_REPLACEMENT_RESERVE == 31


# ======================================================================================
# 6. legacy_archetype 은 어떤 판정에도 쓰이지 않는다 — 구조적 증명
# ======================================================================================


def test_legacy_archetype_never_appears_in_any_branch_condition() -> None:
    """registry.py 의 어떤 조건·분기·비교에도 ``legacy_archetype`` 이 등장하지 않는다.

    행동 테스트는 "이번 입력에서 안 쓰였다" 만 보이지만, AST 검사는 "쓸 수 있는 자리가
    코드에 없다" 를 보인다.
    """
    source = Path(reg.__file__).read_text(encoding="utf-8")
    tree = ast.parse(source)
    decision_nodes = (
        ast.If,
        ast.IfExp,
        ast.Compare,
        ast.While,
        ast.Match,
        ast.BoolOp,
        ast.Assert,
    )
    offenders: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, decision_nodes):
            rendered = ast.unparse(node)
            if "legacy_archetype" in rendered:
                offenders.append(f"line {getattr(node, 'lineno', '?')}: {rendered[:160]}")
    assert not offenders, "legacy_archetype 이 판정 위치에 쓰였다:\n" + "\n".join(offenders)


def test_legacy_archetype_is_metadata_only_behaviourally(tmp_path: Path) -> None:
    """두 소스에서 일관되게 값을 바꿔도 선택·분류·그룹핑이 전혀 바뀌지 않는다."""
    baseline = _load(tmp_path / "base")

    document = _load_manifest_doc()
    for family in document["task_families"]:
        family["legacy_archetype"] = "ARCHETYPE_NONSENSE"

    tmp = tmp_path / "mut"
    manifest_path, control = _materialize(tmp, manifest=document)
    control_json = control / reg.TARGET_FRAME_JSON_NAME
    payload = json.loads(control_json.read_text(encoding="utf-8"))
    for family in payload["task_families"]:
        family["legacy_archetype"] = "ARCHETYPE_NONSENSE"
    control_json.write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")
    csv_path = control / reg.TASK_REGISTRY_CSV_NAME
    csv_text = csv_path.read_text(encoding="utf-8-sig")
    for original in ("FINANCIAL_ACTION_ENTRY", "ITEM_DETAIL", "UTILITY_ENTRY", "PLACE_LOOKUP"):
        csv_text = csv_text.replace("," + original + ",", ",ARCHETYPE_NONSENSE,")
    csv_path.write_text("﻿" + csv_text, encoding="utf-8")

    mutated = reg.load_task_registry(manifest_path, registry_path=control)

    # 동일한 표본 · 동일한 순서 · 동일한 family 그룹핑 · 동일한 pilot 선택
    assert [c.target_id for c in mutated.all()] == [c.target_id for c in baseline.all()]
    assert [c.family_id for c in mutated.all()] == [c.family_id for c in baseline.all()]
    assert [c.collection_order for c in mutated.all()] == [
        c.collection_order for c in baseline.all()
    ]
    assert [c.target_id for c in mutated.pilot_5()] == [c.target_id for c in baseline.pilot_5()]

    # 판정에 쓰이는 모든 필드가 그대로다. 바뀐 것은 metadata 와 그 identity digest 뿐이다.
    decision_fields = [f for f in reg.CONTRACT_HASH_PAYLOAD_FIELDS if f != "legacy_archetype"]
    for new, old in zip(mutated.all(), baseline.all(), strict=True):
        for field_name in decision_fields:
            assert getattr(new, field_name) == getattr(old, field_name), field_name
        assert new.endpoint_contract_hash == old.endpoint_contract_hash
        assert new.legacy_archetype == "ARCHETYPE_NONSENSE"
        assert old.legacy_archetype != "ARCHETYPE_NONSENSE"
        # task_contract_hash 는 계약 전체의 identity digest 이므로 metadata 변경도 반영한다.
        # 이것은 "판정" 이 아니라 "신원" 이다.
        assert new.task_contract_hash != old.task_contract_hash


def test_contract_dataclass_shape_is_the_shared_definition() -> None:
    """다른 worker 들이 같은 정의를 쓴다. 필드 구성이 바뀌면 여기서 잡힌다."""
    import dataclasses

    names = [f.name for f in dataclasses.fields(TaskContract)]
    assert names == [
        "target_id",
        "family_id",
        "service",
        "starting_url",
        "frozen_task",
        "task_instruction",
        "fixed_fixture",
        "fixture_override",
        "endpoint_contract",
        "forbidden_actions",
        "task_contract_hash",
        "endpoint_contract_hash",
        "legacy_archetype",
        "mobile_web_eligibility",
        "stratum",
        "is_pilot_5",
        "collection_order",
        "task_role",
        "fixture_input_mode",
    ]
    contract = TaskContract(
        target_id="X",
        family_id="F1",
        service="s",
        starting_url="u",
        frozen_task="t",
        task_instruction="i",
        fixed_fixture="없음",
        fixture_override=None,
        endpoint_contract="e",
        forbidden_actions=(),
        task_contract_hash="h",
        endpoint_contract_hash="h2",
    )
    assert contract.task_role == "PRIMARY"  # 기본값이 본표본이다
    assert contract.fixture_input_mode is None
    # 동결 계약은 적재 후 변경되지 않는다 (frozen dataclass)
    mutated_field = "target_id"
    with pytest.raises(dataclasses.FrozenInstanceError):
        setattr(contract, mutated_field, "Y")


def test_copy_of_registry_is_pure_no_source_mutation(tmp_path: Path) -> None:
    """로더는 SSOTV3/manifest 파일을 절대 쓰지 않는다 (읽기 전용)."""
    manifest_path, control = _materialize(tmp_path)
    before = {
        p: _sha256_bytes(p.read_bytes())
        for p in [manifest_path, *sorted(control.iterdir())]
        if p.is_file()
    }
    reg.load_task_registry(manifest_path, registry_path=control)
    after = {p: _sha256_bytes(p.read_bytes()) for p in before}
    assert after == before


# ======================================================================================
# 7. R3 task_role — 본표본 n 의 기계적 집행
# ======================================================================================


def test_r3_all_frozen_targets_are_primary(tmp_path: Path) -> None:
    registry = _load(tmp_path)
    assert all(c.task_role == "PRIMARY" for c in registry.all())
    assert len(registry.primary()) == 50
    assert TASK_ROLES == ("PRIMARY", "SECONDARY_REPEATED")


def test_r3_primary_filter_string_is_exposed_verbatim(tmp_path: Path) -> None:
    """집계 산출물은 "적용했다" 가 아니라 **필터 조건 문자열** 자체를 기록한다."""
    registry = _load(tmp_path)
    assert reg.PRIMARY_SAMPLE_FILTER == "task_role == 'PRIMARY'"
    assert registry.primary_sample_filter() == reg.PRIMARY_SAMPLE_FILTER


def test_r3_secondary_repeated_does_not_enter_the_primary_sample(tmp_path: Path) -> None:
    """SECONDARY_REPEATED 행은 본표본 n 을 늘리지 않는다 — 필터가 실제로 걸러낸다."""
    registry = _load(tmp_path)
    base = registry.by_target_id("F1-01")
    import dataclasses

    secondary = dataclasses.replace(
        base, target_id="F1-01__balance", task_role="SECONDARY_REPEATED"
    )
    widened = dataclasses.replace(registry, contracts=(*registry.all(), secondary))

    assert len(widened.all()) == 51  # 모든 관측 행은 남아 있고
    assert len(widened.primary()) == 50  # 본표본 n 은 늘지 않는다
    assert len([c for c in widened.by_family("F1") if c.task_role == "PRIMARY"]) == 10


def test_r3_unknown_task_role_is_rejected(tmp_path: Path) -> None:
    document = _load_manifest_doc()
    _manifest_target(document, "F1-03")["task_role"] = "TERTIARY"
    manifest_path, control = _materialize(tmp_path, manifest=document)
    with pytest.raises(reg.RegistryParseError) as excinfo:
        reg.load_task_registry(manifest_path, registry_path=control)
    assert "task_role" in str(excinfo.value)


# ======================================================================================
# 8. R5 fixture_input_mode — 관측값이지 계약이 아니다
# ======================================================================================


def test_r5_fixture_input_mode_is_none_at_freeze_time(tmp_path: Path) -> None:
    registry = _load(tmp_path)
    assert all(c.fixture_input_mode is None for c in registry.all())
    assert set(FIXTURE_INPUT_MODES) == {"FREE_TEXT", "DROPDOWN", "MIXED", "MAP_PAN", "OTHER"}


def test_r5_is_excluded_from_the_contract_identity_hash(tmp_path: Path) -> None:
    """관측이 계약의 신원을 바꾸면 동결의 의미가 사라진다."""
    assert "fixture_input_mode" in reg.CONTRACT_HASH_EXCLUDED_FIELDS
    assert "fixture_input_mode" not in reg.CONTRACT_HASH_PAYLOAD_FIELDS
    assert "task_role" in reg.CONTRACT_HASH_PAYLOAD_FIELDS

    import dataclasses

    contract = _load(tmp_path).by_target_id("F4-01")
    observed = dataclasses.replace(contract, fixture_input_mode="DROPDOWN")
    assert reg.recompute_task_contract_hash(observed) == contract.task_contract_hash

    # 대조: 계약 필드를 바꾸면 신원이 바뀐다
    changed = dataclasses.replace(contract, task_role="SECONDARY_REPEATED")
    assert reg.recompute_task_contract_hash(changed) != contract.task_contract_hash


def test_r5_manifest_must_not_carry_an_observed_value(tmp_path: Path) -> None:
    """계약 동결본에 관측값이 들어 있으면 그 자체가 결함이다."""
    document = _load_manifest_doc()
    _manifest_target(document, "F4-02")["fixture_input_mode"] = "MAP_PAN"
    manifest_path, control = _materialize(tmp_path, manifest=document)
    with pytest.raises(reg.RegistryParseError) as excinfo:
        reg.load_task_registry(manifest_path, registry_path=control)
    assert "fixture_input_mode" in str(excinfo.value)


# ======================================================================================
# 9. R4 분모 사슬 앞단 + 예비 명부
# ======================================================================================


def test_r4_replacement_log_states_zero_explicitly(tmp_path: Path) -> None:
    """k=0 이어도 0 을 명시한다 — 필드 부재와 0 이 같아 보이면 안 된다."""
    log = _load(tmp_path).replacement_log()
    assert log.total_replaced == 0
    assert log.replacements_source == "ABSENT_TREATED_AS_ZERO"
    assert len(log.per_family) == 5
    for chain in log.per_family:
        assert chain.candidate_count == 10
        assert chain.replaced_count == 0  # 부재가 아니라 명시된 0
        assert chain.replaced_reasons == ()
        assert chain.frozen_count == 10
        assert chain.reserve_remaining == chain.reserve_count


def test_r4_reserve_is_thirty_one_with_uneven_family_lengths(tmp_path: Path) -> None:
    log = _load(tmp_path).replacement_log()
    assert len(log.reserve) == EXPECTED_REPLACEMENT_RESERVE == 31
    assert {c.family_id: c.reserve_count for c in log.per_family} == {
        "F1": 7,
        "F2": 8,
        "F3": 5,
        "F4": 4,
        "F5": 7,
    }
    assert [e.reserve_rank for e in log.reserve_for("F2")] == [1, 2, 3, 4, 5, 6, 7, 8]


def test_r4_no_reserve_duplicates_a_primary_url(tmp_path: Path) -> None:
    """A 가 v3.0.1 → v3.0.2 에서 시정한 결함의 회귀검사."""
    registry = _load(tmp_path)
    primary = {(c.family_id, c.starting_url) for c in registry.all()}
    for entry in registry.replacement_reserve:
        assert (entry.family_id, entry.starting_url) not in primary


def test_r4_reserve_colliding_with_primary_url_is_rejected(tmp_path: Path) -> None:
    document = _load_manifest_doc()
    primary = _manifest_target(document, "F4-02")
    document["replacement_reserve"].append(
        {
            "family_id": "F4",
            "stratum": "_",
            "reserve_rank": 5,
            "service_name": "primary 와 같은 대상",
            "starting_url": primary["starting_url"],
            "mobile_web_eligibility": "PRECHECK_REQUIRED",
            "inherits": "동일 family",
        }
    )
    manifest_path, control = _materialize(tmp_path, manifest=document)
    with pytest.raises(reg.RegistryIntegrityError) as excinfo:
        reg.load_task_registry(manifest_path, registry_path=control)
    assert "primary" in str(excinfo.value)


def test_r4_reserve_rank_gap_is_rejected(tmp_path: Path) -> None:
    document = _load_manifest_doc()
    for entry in document["replacement_reserve"]:
        if entry["family_id"] == "F3" and entry["reserve_rank"] == 2:
            entry["reserve_rank"] = 9
    manifest_path, control = _materialize(tmp_path, manifest=document)
    with pytest.raises(reg.RegistryIntegrityError) as excinfo:
        reg.load_task_registry(manifest_path, registry_path=control)
    assert "reserve_rank" in str(excinfo.value)


def test_r4_applied_replacements_when_present_are_counted(tmp_path: Path) -> None:
    """교체가 실제로 기록되면 사슬이 그것을 드러낸다 (양성 대조의 반대편)."""
    document = _load_manifest_doc()
    document[reg.APPLIED_REPLACEMENTS_KEY] = [
        {
            "family_id": "F3",
            "replaced_target_id": "F3-09",
            "reason": "APP_REQUIRED_EXCLUDE",
            "reserve_rank": 1,
        }
    ]
    manifest_path, control = _materialize(tmp_path, manifest=document)
    log = reg.load_task_registry(manifest_path, registry_path=control).replacement_log()
    assert log.total_replaced == 1
    assert log.replacements_source == "MANIFEST_KEY"
    f3 = log.by_family("F3")
    assert f3.replaced_count == 1
    assert f3.replaced_reasons == ("APP_REQUIRED_EXCLUDE",)
    assert f3.reserve_remaining == f3.reserve_count - 1
    assert log.by_family("F1").replaced_count == 0  # 다른 family 는 여전히 명시적 0


def test_r4_replacement_rule_is_preserved(tmp_path: Path) -> None:
    rule = _load(tmp_path).replacement_log().rule
    assert "APP_REQUIRED_EXCLUDE" in rule["allowed_reasons"]
    assert any("dispersion" in r for r in rule["forbidden_reasons"])


def test_r5_semantics_are_recorded_in_the_shared_contract_docstring() -> None:
    """R5 의 파생값 역할이 문서에서 사라지지 않도록 고정한다.

    이 필드를 "그냥 참고값" 으로 읽고 결측 처리하면 ``activation_depth`` 가 조용히 틀린다.
    다른 worker 가 같은 정의를 읽으므로 문구가 지워지면 여기서 잡힌다.
    """
    from landing_accessibility.v3_runner import contracts

    doc = contracts.__doc__ or ""
    for phrase in (
        "activation_depth",
        "SELECT_ORIGIN",
        "SELECT_DESTINATION",
        "SELECT_DATE",
        "CONDITIONAL",
        "FlowStep.input_mode",
        "W5B",
        "파생값 계산의 입력",
    ):
        assert phrase in doc, f"contracts docstring 에서 {phrase!r} 가 사라졌다"
    # MIXED 는 "애매하다" 가 아니라 "한 관측 안에 수단이 섞였다" 이다.
    assert "한 관측 안에 서로 다른 수단이 섞였다" in doc
