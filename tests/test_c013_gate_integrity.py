"""C013 — 게이트 무결성 3건. **반례를 주입해서** 게이트가 실제로 잡는지 확인한다.

C012 승격 노트가 남긴 경고를 그대로 받는다:

    감사관이 반례 3종을 주입했을 때 pytest 는 잡았으나 빌드 스크립트는 셋 다 exit 0 으로
    통과시켰다. 잡은 것도 구조 규칙이 아니라 EXPECTED_QUEUE_SIZE=7 같은 하드코딩 리터럴이다.

그래서 이 파일의 검사는 두 가지를 지킨다.

1. **하드코딩 리터럴로 세지 않는다.** 큐 크기 7 을 상수로 비교하는 대신, 큐가 구조 규칙에서
   나오는지, 그리고 그 규칙이 C012 손입력 큐를 재현하는지를 본다.
2. **빌드 스크립트 자체에 반례를 넣고 돌린다.** 테스트만 잡고 빌드는 통과하는 상태를
   허용하지 않는다 — 빌드가 exit 0 이면 그 게이트는 우회 가능하다.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import shutil
import subprocess
import sys
from pathlib import Path
from types import ModuleType

import pytest

REPO = Path(__file__).resolve().parents[1]
RESEARCH = REPO / "research" / "landing_accessibility"
STATE = RESEARCH / "state"
WISEAPP = RESEARCH / "sources" / "wiseapp"
BUILDER = RESEARCH / "scripts" / "build_canonical_entities.py"
AUTHORITY = WISEAPP / "authority_manifest.json"

sys.path.insert(0, str(RESEARCH / "src"))

from landing_accessibility import authority_manifest as am  # noqa: E402
from landing_accessibility import registered_domain as rd  # noqa: E402

pytestmark = pytest.mark.skipif(
    not (STATE / "service_master.parquet").exists(),
    reason="landing_accessibility state 산출물이 없다",
)


def _load_builder() -> ModuleType:
    spec = importlib.util.spec_from_file_location("_c013_builder", BUILDER)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def builder() -> ModuleType:
    return _load_builder()


def _sandbox(tmp_path: Path) -> Path:
    """빌드에 필요한 최소 트리를 복제한다. 원본은 건드리지 않는다."""
    root = tmp_path / "research" / "landing_accessibility"
    (root / "scripts").mkdir(parents=True)
    shutil.copy2(BUILDER, root / "scripts" / BUILDER.name)
    shutil.copytree(STATE, root / "state")
    shutil.copytree(WISEAPP, root / "sources" / "wiseapp")
    return root


def _run_builder(root: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(root / "scripts" / BUILDER.name)],
        capture_output=True,
        text=True,
    )


def _patch_builder(root: Path, old: str, new: str) -> None:
    path = root / "scripts" / BUILDER.name
    source = path.read_text(encoding="utf-8")
    assert source.count(old) == 1, f"반례 주입 지점을 찾지 못했다: {old!r}"
    path.write_text(source.replace(old, new), encoding="utf-8")


# ══ G1 — 큐 멤버십이 구조에서 나오는가 ══════════════════════════════════════


def test_entity_spec_no_longer_carries_a_hand_set_queue_flag(builder: ModuleType) -> None:
    """ENTITY_SPEC 세 번째 원소(손입력 bool)가 사라졌는지 본다.

    그 bool 이 살아 있으면 '큐에 오르는가' 와 '어떤 판정인가' 가 같은 손에서 나오고,
    둘을 함께 내리면 빌드가 조용히 통과한다.
    """
    assert builder.ENTITY_SPEC, "ENTITY_SPEC 이 비었다"
    for key, value in builder.ENTITY_SPEC.items():
        assert len(value) == 2, (
            f"{key}: ENTITY_SPEC 값이 2-튜플이 아니다 — 손입력 플래그가 살아 있다"
        )
        assert isinstance(value[0], str) and isinstance(value[1], str)
        assert not any(isinstance(v, bool) for v in value), f"{key}: bool 플래그가 남아 있다"


def test_queue_is_reproduced_by_structural_rules_alone(builder: ModuleType) -> None:
    """큐를 이름 목록이 아니라 표기 구조에서 다시 만들어 본다.

    비교 대상은 '7' 이라는 숫자가 아니라 C012 가 손으로 켰던 **집합** 이다.
    숫자만 맞고 구성이 다르면 통과하지 못한다.
    """
    import pandas as pd

    rows = pd.read_parquet(STATE / "source_ranking_rows.parquet")
    industry_keys = {
        builder.ENTITY_SPEC[(raw, domain)][0]
        for raw, domain, axis in zip(
            rows["entity_name_raw"], rows["domain"], rows["axis_type"], strict=True
        )
        if axis == "INDUSTRY_CATEGORY"
    }
    derived = builder.derive_review_queue(builder.ENTITY_SPEC, industry_keys)

    assert set(derived) == set(builder.C012_HAND_SET_QUEUE), (
        f"구조 규칙이 C012 큐를 재현하지 못했다\n"
        f"  규칙에만: {sorted(set(derived) - set(builder.C012_HAND_SET_QUEUE))}\n"
        f"  손입력에만: {sorted(set(builder.C012_HAND_SET_QUEUE) - set(derived))}"
    )
    # 모든 큐 항목이 '왜 큐에 올랐는지' 를 기계 판독 가능한 규칙명으로 갖는다.
    allowed = {
        builder.QUEUE_RULE_CROSS_DOMAIN_LABEL,
        builder.QUEUE_RULE_SLASH_SEGMENT,
        builder.QUEUE_RULE_MULTI_ALIAS,
    }
    for ckey, entries in derived.items():
        assert entries, f"{ckey}: 큐에 올랐는데 규칙이 없다"
        for entry in entries:
            assert entry["rule"] in allowed, f"{ckey}: 알 수 없는 큐 규칙 {entry['rule']}"
            assert entry["detail"]


def test_queue_membership_survives_deleting_a_name_from_the_spec(builder: ModuleType) -> None:
    """이름 목록을 지워도 큐는 그대로다 — 큐가 목록이 아니라 구조에서 나오기 때문이다.

    C012 판본에서는 손입력 bool 하나만 내리면 그 entity 가 큐에서 사라졌다.
    """
    industry_keys = {v[0] for k, v in builder.ENTITY_SPEC.items() if v[1] == builder.INDUSTRY}
    derived = builder.derive_review_queue(builder.ENTITY_SPEC, industry_keys)
    assert "coupang_app" in derived
    assert derived["coupang_app"][0]["rule"] == builder.QUEUE_RULE_CROSS_DOMAIN_LABEL

    # 표기 구조를 실제로 깨면(=RETAIL 쪽 '쿠팡' 표기를 없애면) 그때 비로소 큐에서 빠진다.
    spec = {k: v for k, v in builder.ENTITY_SPEC.items() if k != ("쿠팡", "RETAIL")}
    assert "coupang_app" not in builder.derive_review_queue(spec, industry_keys)


def test_build_fails_when_a_queued_entity_loses_its_decision(tmp_path: Path) -> None:
    """반례 주입 1 — 큐에서 항목을 빼려고 판정만 지운다. 빌드가 멈춰야 한다."""
    root = _sandbox(tmp_path)
    _patch_builder(
        root,
        '    "coupang_retail": {\n        "review_decision": REVIEW_KEEP_SEPARATE,',
        '    "_removed_coupang_retail": {\n        "review_decision": REVIEW_KEEP_SEPARATE,',
    )
    proc = _run_builder(root)
    assert proc.returncode != 0, "큐 항목의 판정을 지웠는데 빌드가 통과했다"
    assert "review queue" in (proc.stdout + proc.stderr)


# ══ G2 — MERGE / KEEP_SEPARATE 가 데이터에 연결돼 있는가 ═══════════════════


def test_merge_actually_absorbed_at_least_two_source_labels() -> None:
    """MERGE 는 서술 라벨이 아니라 '표기 2개 이상을 흡수했다' 는 데이터 주장이다."""
    import pandas as pd

    service_master = pd.read_parquet(STATE / "service_master.parquet")
    alias_map = pd.read_parquet(STATE / "entity_alias_map.parquet")
    counts = alias_map.groupby("service_id")["alias_id"].nunique()

    merged = service_master[service_master["review_decision"] == "MERGE"]
    assert not merged.empty, "MERGE 판정이 하나도 없다면 이 검사는 아무것도 지키지 않는다"
    for row in merged.itertuples():
        assert counts.get(row.service_id, 0) >= 2, (
            f"{row.canonical_service_key}: MERGE 인데 흡수한 표기가 2개 미만이다"
        )
        raws = set(alias_map.loc[alias_map["service_id"] == row.service_id, "entity_name_raw"])
        assert len(raws) >= 2, f"{row.canonical_service_key}: 서로 다른 원문 표기가 2개 미만"


def test_keep_separate_shares_no_alias_with_its_queue_peer() -> None:
    """KEEP_SEPARATE 는 '흡수하지 않았다' 는 주장이다. 상대편이 데이터에 남아 있어야 한다."""
    import pandas as pd

    service_master = pd.read_parquet(STATE / "service_master.parquet")
    alias_map = pd.read_parquet(STATE / "entity_alias_map.parquet")
    ids = dict(
        zip(service_master["canonical_service_key"], service_master["service_id"], strict=True)
    )
    alias_of: dict[str, set[str]] = {}
    for rec in alias_map.itertuples():
        alias_of.setdefault(rec.service_id, set()).add(rec.alias_id)

    kept = service_master[service_master["review_decision"] == "KEEP_SEPARATE"]
    assert not kept.empty
    for row in kept.itertuples():
        assert len(alias_of[row.service_id]) == 1, (
            f"{row.canonical_service_key}: 분리 판정인데 표기를 흡수했다"
        )
        peers = [k for k in (row.review_queue_peers or "").split(",") if k]
        assert peers, f"{row.canonical_service_key}: 무엇으로부터 분리했는지가 데이터에 없다"
        for peer in peers:
            assert peer in ids and ids[peer] != row.service_id
            assert not (alias_of[row.service_id] & alias_of[ids[peer]])


def test_build_fails_when_merge_merges_nothing(tmp_path: Path) -> None:
    """반례 주입 2 — coupang_app 을 MERGE 로 바꾸되 별칭은 그대로 둔다.

    C012 판본에서는 이 변경으로도 entity 81 이 유지되고 빌드가 exit 0 이었다.
    """
    root = _sandbox(tmp_path)
    _patch_builder(
        root,
        '    "coupang_app": {\n        "review_decision": REVIEW_KEEP_SEPARATE,',
        '    "coupang_app": {\n        "review_decision": REVIEW_MERGE,',
    )
    proc = _run_builder(root)
    assert proc.returncode != 0, "아무것도 병합하지 않는 MERGE 인데 빌드가 통과했다"
    assert "MERGE" in (proc.stdout + proc.stderr)


def test_build_fails_when_keep_separate_loses_its_peer(tmp_path: Path) -> None:
    """반례 주입 3 — 분리 판정은 그대로 두고 큐 상대편 관계만 지운다."""
    root = _sandbox(tmp_path)
    _patch_builder(
        root,
        "        queue_peers = sorted(\n",
        '        queue_rules = [{**r, "peer_canonical_service_key": ""} for r in queue_rules]\n'
        "        queue_peers = sorted(\n",
    )
    proc = _run_builder(root)
    assert proc.returncode != 0, "상대편 없는 KEEP_SEPARATE 인데 빌드가 통과했다"


# ══ G3 — A1 원문 파일이 전수 해시 등록돼 있는가 ═════════════════════════════


def test_every_a1_raw_file_is_hash_registered(authority: dict) -> None:
    """`decision_evidence` 가 지목한 파일을 포함해 raw 디렉터리 전수가 등록돼야 한다.

    대조의 한쪽 끝은 디스크의 파일이다 — 매니페스트끼리 비교하지 않는다.
    """
    report = am.verify_raw_assets(AUTHORITY)
    on_disk = sorted(p.name for p in (WISEAPP / "raw").iterdir() if p.is_file())
    assert report["registered"] == len(on_disk)

    declared = {Path(v["file"]).name: v for v in authority["raw_assets"].values()}
    assert sorted(declared) == on_disk
    for name, entry in declared.items():
        data = (WISEAPP / "raw" / name).read_bytes()
        assert entry["bytes"] == len(data)
        assert entry["sha256"] == "sha256:" + hashlib.sha256(data).hexdigest()


def test_decision_evidence_absence_files_are_all_registered(authority: dict) -> None:
    """ABSENCE 층이 근거로 지목한 A1 파일이 전부 동결돼 있는가.

    이 검사가 없으면 '그 파일에 그 문자열이 0회' 라는 판정의 한쪽 끝이 열려 있다.
    """
    import pandas as pd

    service_master = pd.read_parquet(STATE / "service_master.parquet")
    registered = {v["file"] for v in authority["raw_assets"].values()}
    pointed: set[str] = set()
    for blob in service_master["decision_evidence"].dropna():
        for item in json.loads(blob):
            if item.get("layer") != "ABSENCE":
                continue
            pointed.update(p for p in item["source"].split(";") if p)
    assert pointed, "ABSENCE 층이 하나도 없다면 이 검사는 아무것도 지키지 않는다"
    missing = sorted(pointed - registered)
    assert not missing, f"판정 근거로 지목됐는데 authority_manifest 에 해시가 없다: {missing}"


def test_authority_manifest_rejects_an_unregistered_raw_file(tmp_path: Path) -> None:
    """반례 주입 4 — raw 디렉터리에 파일을 하나 더 두면 등록 없이는 통과하지 못한다."""
    sandbox = tmp_path / "wiseapp"
    shutil.copytree(WISEAPP, sandbox)
    assert am.verify_raw_assets(sandbox / "authority_manifest.json")["registered"] == 6

    (sandbox / "raw" / "wiseapp933_extra.json").write_text("{}", encoding="utf-8")
    with pytest.raises(am.AuthorityManifestError, match="등록되지 않은"):
        am.verify_raw_assets(sandbox / "authority_manifest.json")


def test_authority_manifest_detects_a_tampered_raw_file(tmp_path: Path) -> None:
    sandbox = tmp_path / "wiseapp"
    shutil.copytree(WISEAPP, sandbox)
    target = sandbox / "raw" / "wiseapp933_images.json"
    target.write_bytes(target.read_bytes() + b" ")
    with pytest.raises(am.AuthorityManifestError, match=r"bytes 불일치|sha256 불일치"):
        am.verify_raw_assets(sandbox / "authority_manifest.json")


def test_manifest_revision_records_the_registry_extension(authority: dict) -> None:
    """등록 목록이 늘어난 사실을 'raw_assets 불변' 으로 뭉개지 않았는지 본다."""
    assert authority["manifest_revision"] >= 5
    rev5 = next(e for e in authority["revision_log"] if e["revision"] == 5)
    assert rev5["cycle"] == "C013"
    assert set(rev5["raw_assets_registry_extended"]) == {"api_json", "images_json"}
    assert rev5["raw_assets_unchanged"] is True
    assert am.compute_self_sha256(authority) == authority[am.SELF_HASH_FIELD]


@pytest.fixture(scope="module")
def authority() -> dict:
    return json.loads(AUTHORITY.read_text(encoding="utf-8"))


# ══ PSL — 마지막 두 라벨 비교 금지 ══════════════════════════════════════════


def test_registered_domain_uses_public_suffix_list_not_last_two_labels() -> None:
    """Pilot 이 무관한 두 사이트를 같은 등록도메인으로 오판한 그 케이스를 그대로 넣는다."""
    assert rd.registered_domain("https://www.gmarket.co.kr/") == "gmarket.co.kr"
    assert rd.registered_domain("https://www.auction.co.kr/") == "auction.co.kr"
    assert not rd.same_registered_domain(
        "https://www.gmarket.co.kr/", "https://www.auction.co.kr/"
    ), "마지막 두 라벨('co.kr')만 보면 같다고 나온다 — PSL 을 쓰지 않고 있다"

    # 2단계 국가도메인 전반
    for host, expected in [
        ("https://www.korea.go.kr/", "korea.go.kr"),
        ("https://www.kwacc.or.kr/x", "kwacc.or.kr"),
        ("https://a.b.c.hanabank.com/", "hanabank.com"),
        ("https://shopping.naver.com/", "naver.com"),
    ]:
        assert rd.registered_domain(host) == expected

    # public suffix 그 자체는 등록도메인이 아니다 — 모르는 것을 같다고 하지 않는다.
    assert rd.registered_domain("http://co.kr/") is None
    assert not rd.same_registered_domain("http://co.kr/", "http://co.kr/")


def test_psl_provenance_is_pinned_and_offline() -> None:
    """어느 PSL 판본으로 판정했는지 기록되지 않으면 재현되지 않는다."""
    prov = rd.psl_provenance()
    assert prov["network_fetch"] is False
    assert prov["list_sha256"].startswith("sha256:")
    assert prov["library_version"] != "unknown"
