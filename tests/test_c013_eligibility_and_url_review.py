"""C013 — W3 web eligibility / W4 official landing URL / W5 web_target_group 승격·해체.

이 파일이 지키는 것은 스키마의 모양이 아니라 06 이 명시적으로 금지한 실수들이다.

    §2-1  URL 이 존재한다는 사실만으로 WEB_SERVICE 로 두지 않는다
    §2-3  SYSTEM_APP 확정은 웹 랜딩 부재를 실제 확인했을 때만이다
    §2-3  확인 불가는 UNRESOLVED 이고 제외로 바꾸지 않는다
    §3-2  추측으로 URL 을 만들지 않고 검색 1위를 자동 채택하지 않는다
    §3-3  등록도메인은 PSL 파서로 판정한다
    §3-4  URL 이 확정된 뒤에만 그룹을 승격한다
    §6    URL 확인은 수집이 아니다

대조의 한쪽 끝은 항상 판정 밖에 있다 — 확정 URL 은 **관측 기록**과, 탐색 기록은
**후보 파일**과 맞춘다. 판정표끼리 비교하지 않는다.
"""

from __future__ import annotations

import importlib.util
import json
import shutil
import subprocess
import sys
from pathlib import Path
from types import ModuleType

import pandas as pd
import pytest

REPO = Path(__file__).resolve().parents[1]
RESEARCH = REPO / "research" / "landing_accessibility"
STATE = RESEARCH / "state"
SCRIPTS = RESEARCH / "scripts"
BUILDER = SCRIPTS / "build_web_eligibility_and_url_review.py"
ENTITY_BUILDER = SCRIPTS / "build_canonical_entities.py"

sys.path.insert(0, str(RESEARCH / "src"))

from landing_accessibility import registered_domain as rd  # noqa: E402

ELIGIBILITY_VOCAB = {
    "WEB_SERVICE",
    "OFFICIAL_PRODUCT_PAGE",
    "APP_ONLY",
    "SYSTEM_APP",
    "RETAIL_OFFLINE_ONLY",
    "EXCLUDED_INDUSTRY_AXIS",
    "UNRESOLVED",
}
URL_TYPE_VOCAB = {"WEB_SERVICE_LANDING", "OFFICIAL_PRODUCT_PAGE", "APP_ONLY", "UNRESOLVED"}

pytestmark = pytest.mark.skipif(
    not (STATE / "url_review.parquet").exists(),
    reason="C013 url_review 산출물이 없다",
)


@pytest.fixture(scope="module")
def url_review() -> pd.DataFrame:
    return pd.read_parquet(STATE / "url_review.parquet")


@pytest.fixture(scope="module")
def service_master() -> pd.DataFrame:
    return pd.read_parquet(STATE / "service_master.parquet")


@pytest.fixture(scope="module")
def web_target_group() -> pd.DataFrame:
    return pd.read_parquet(STATE / "web_target_group.parquet")


@pytest.fixture(scope="module")
def probes() -> dict[tuple[str, str], dict]:
    payload = json.loads((STATE / "url_review_probe.json").read_text(encoding="utf-8"))
    return {(p["canonical_service_key"], p["target_url"]): p for p in payload["probes"]}


@pytest.fixture(scope="module")
def candidates() -> dict[str, dict]:
    payload = json.loads((STATE / "url_review_candidates.json").read_text(encoding="utf-8"))
    return {c["canonical_service_key"]: c for c in payload["candidates"]}


def _load(path: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location(f"_c013_{path.stem}", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _sandbox(tmp_path: Path) -> Path:
    root = tmp_path / "research" / "landing_accessibility"
    (root / "scripts").mkdir(parents=True)
    for script in (BUILDER, ENTITY_BUILDER):
        shutil.copy2(script, root / "scripts" / script.name)
    shutil.copytree(STATE, root / "state")
    shutil.copytree(RESEARCH / "src", root / "src")
    shutil.copytree(RESEARCH / "sources" / "wiseapp", root / "sources" / "wiseapp")
    return root


def _run(root: Path, script: str = BUILDER.name) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(root / "scripts" / script)], capture_output=True, text=True
    )


def _patch(root: Path, old: str, new: str, script: str = BUILDER.name) -> None:
    path = root / "scripts" / script
    source = path.read_text(encoding="utf-8")
    assert source.count(old) == 1, f"반례 주입 지점을 찾지 못했다: {old!r}"
    path.write_text(source.replace(old, new), encoding="utf-8")


# ══ W3 — 판정 어휘와 근거 필드 ═════════════════════════════════════════════


def test_every_brand_entity_is_assessed_with_06_vocabulary(service_master: pd.DataFrame) -> None:
    brand = service_master[service_master["axis_type"] == "SERVICE_BRAND"]
    assert len(brand) == 71
    assert set(brand["web_eligibility_status"]) <= ELIGIBILITY_VOCAB - {"EXCLUDED_INDUSTRY_AXIS"}
    assert "NOT_ASSESSED" not in set(service_master["web_eligibility_status"])
    assert set(service_master["web_eligibility_status"]) <= ELIGIBILITY_VOCAB


def test_eligibility_basis_fields_are_all_present(service_master: pd.DataFrame) -> None:
    """06 §2-2 가 요구한 칸이 전부 있고 비어 있지 않다.

    debt: eligibility-basis-fields-narrower-than-06-still-carried — C012 판본은
    `web_eligibility_basis` 한 칸뿐이었고, 71건을 판정하면 근거 없이 상태값만 쌓였다.
    """
    required = [
        "web_eligibility_status",
        "eligibility_basis",
        "eligibility_reviewer",
        "eligibility_confidence",
        "eligibility_reviewed_at",
        "eligibility_needs_review",
    ]
    for column in required:
        assert column in service_master.columns, f"근거 필드 누락: {column}"
    assert "web_eligibility_basis" not in service_master.columns
    for row in service_master.itertuples():
        assert row.eligibility_basis and len(row.eligibility_basis) > 30
        assert row.eligibility_reviewer
        assert row.eligibility_confidence in {"HIGH", "MEDIUM", "LOW"}
        assert row.eligibility_reviewed_at


def test_the_two_layers_do_not_share_one_review_flag(service_master: pd.DataFrame) -> None:
    """measurement 층과 web 층의 미결 플래그는 별도 컬럼이다 (ssot C012 지적).

    한 칸을 공유하면 '표기 병합이 미결' 과 'URL 판정이 미결' 이 구별되지 않는다.
    두 컬럼의 값이 실제로 갈린다는 사실로 분리를 확인한다 — 이름만 다르고 값이 같으면
    분리한 것이 아니다.
    """
    assert "needs_human_review" in service_master.columns
    assert "eligibility_needs_review" in service_master.columns
    measurement = service_master["needs_human_review"].astype(bool)
    web = service_master["eligibility_needs_review"].astype(bool)
    assert not measurement.equals(web), "두 층의 미결 플래그가 같은 값이다 — 분리되지 않았다"
    assert web.any(), "web 층 미결이 하나도 없다면 이 검사는 아무것도 지키지 않는다"


def test_unresolved_is_never_turned_into_an_exclusion(
    service_master: pd.DataFrame, url_review: pd.DataFrame
) -> None:
    """06 §2-3 — 확인 불가를 제외로 바꾸지 않는다."""
    brand = service_master[service_master["axis_type"] == "SERVICE_BRAND"]
    assert "EXCLUDED_INDUSTRY_AXIS" not in set(brand["web_eligibility_status"])

    unresolved = url_review[url_review["web_eligibility_status"] == "UNRESOLVED"]
    assert len(unresolved) > 0, "UNRESOLVED 가 0건이면 이 검사는 아무것도 지키지 않는다"
    assert unresolved["official_landing_url"].isna().all(), "UNRESOLVED 인데 URL 이 확정됐다"
    assert (unresolved["url_type"] == "UNRESOLVED").all()
    assert (unresolved["review_status"] == "NEEDS_HUMAN_REVIEW").all()
    assert (unresolved["url_confidence"] == "LOW").all()


def test_system_app_is_only_declared_after_checking_for_absence(
    service_master: pd.DataFrame,
) -> None:
    """06 §2-3 — 선탑재 여부 자체는 판정 근거가 아니다."""
    system_apps = service_master[service_master["web_eligibility_status"] == "SYSTEM_APP"]
    assert len(system_apps) > 0
    for row in system_apps.itertuples():
        assert "[부재확인]" in row.eligibility_basis, (
            f"{row.canonical_service_key}: 웹 랜딩 부재를 어떻게 확인했는지가 근거에 없다"
        )
    # 연구자 가설 11건이 그대로 상태값이 되지 않았다.
    priors = json.loads(
        (STATE / "_researcher_priors" / "system_app_hypothesis.json").read_text(encoding="utf-8")
    )
    hypothesised = {h["canonical_service_key"] for h in priors["hypotheses"]}
    assert len(hypothesised) == 11
    confirmed = set(system_apps["canonical_service_key"])
    assert confirmed < hypothesised, (
        "가설 11건이 전부 SYSTEM_APP 으로 확정됐다 — 가설을 상태값으로 옮겨 적은 것이다"
    )


def test_build_rejects_a_system_app_without_an_absence_check(tmp_path: Path) -> None:
    """반례 주입 — 부재 확인을 지우면 SYSTEM_APP 판정이 통과하지 못한다."""
    root = _sandbox(tmp_path)
    _patch(
        root,
        '        "absence_check": (\n            "탐색 단계에서 삼성전자 공식 앱 소개 색인(samsung.com/sec/apps/)을 열어 등재된 앱 "',
        '        "_removed_absence_check": (\n            "탐색 단계에서 삼성전자 공식 앱 소개 색인(samsung.com/sec/apps/)을 열어 등재된 앱 "',
    )
    proc = _run(root)
    assert proc.returncode != 0, "부재 확인 없는 SYSTEM_APP 인데 빌드가 통과했다"
    assert "SYSTEM_APP" in (proc.stdout + proc.stderr)


def test_build_rejects_an_unresolved_that_carries_a_url(tmp_path: Path) -> None:
    """반례 주입 — 확인 불가에 URL 을 붙이면 빌드가 멈춘다."""
    root = _sandbox(tmp_path)
    _patch(
        root,
        '    "korean_air": {\n        "status": UNRESOLVED,\n        "evidence_url": "https://www.koreanair.com/",',
        '    "korean_air": {\n        "status": UNRESOLVED,\n        "url": "https://www.koreanair.com/",',
    )
    proc = _run(root)
    assert proc.returncode != 0, "UNRESOLVED 인데 URL 이 붙었는데 빌드가 통과했다"


def test_build_rejects_a_web_service_without_a_confirmed_url(tmp_path: Path) -> None:
    """반례 주입 — URL 없는 WEB_SERVICE 는 성립하지 않는다."""
    root = _sandbox(tmp_path)
    _patch(
        root,
        '    "youtube": {\n        "status": WEB_SERVICE,\n        "url": "https://www.youtube.com/",',
        '    "youtube": {\n        "status": WEB_SERVICE,\n        "_url": "https://www.youtube.com/",',
    )
    proc = _run(root)
    assert proc.returncode != 0, "확정 URL 없는 WEB_SERVICE 인데 빌드가 통과했다"


# ══ W4 — URL 확정의 근거 ═══════════════════════════════════════════════════


def test_url_review_covers_every_brand_entity(
    url_review: pd.DataFrame, service_master: pd.DataFrame
) -> None:
    brand = service_master[service_master["axis_type"] == "SERVICE_BRAND"]
    assert len(url_review) == len(brand) == 71
    assert set(url_review["canonical_service_key"]) == set(brand["canonical_service_key"])
    assert set(url_review["url_type"]) <= URL_TYPE_VOCAB
    for column in (
        "official_landing_url",
        "resolved_final_url",
        "redirect_chain",
        "registered_domain",
        "url_type",
        "url_discovery_method",
        "url_evidence",
        "url_reviewer",
        "url_confidence",
        "reviewed_at",
        "review_status",
    ):
        assert column in url_review.columns, f"06 §3-1 필드 누락: {column}"


def test_no_url_was_invented(
    url_review: pd.DataFrame, candidates: dict[str, dict], probes: dict[tuple[str, str], dict]
) -> None:
    """06 §3-2 — 추측 URL 금지. 확정 URL 은 **탐색 기록과 관측 기록 양쪽에** 있어야 한다.

    브랜드명으로 도메인을 지어내면 후보 파일에 없고, 열어보지 않고 적으면 관측 기록에 없다.
    둘 다 통과해야 URL 이 데이터에 들어온다.
    """
    for row in url_review.itertuples():
        if not row.official_landing_url:
            continue
        discovered = candidates[row.canonical_service_key]["candidate_urls"]
        assert row.official_landing_url in discovered, (
            f"{row.canonical_service_key}: 탐색 기록에 없는 URL 이 확정됐다"
        )
        key = (row.canonical_service_key, row.official_landing_url)
        assert key in probes, f"{row.canonical_service_key}: 열어보지 않은 URL 이 확정됐다"
        assert row.resolved_final_url == probes[key]["final_url"]
        assert row.page_title == probes[key]["page_title"]
        assert row.http_status == probes[key]["http_status"]


def test_registered_domain_is_psl_derived(url_review: pd.DataFrame) -> None:
    """06 §3-3 — 등록도메인은 PSL 파서 결과와 일치하고, public suffix 자체일 수 없다."""
    for row in url_review.itertuples():
        if not row.resolved_final_url:
            assert row.registered_domain is None
            continue
        assert row.registered_domain == rd.registered_domain(row.resolved_final_url)
        assert row.registered_domain is not None
        # 마지막 두 라벨 비교였다면 .co.kr 같은 값이 등록도메인 자리에 앉는다.
        assert rd.public_suffix(row.registered_domain) != row.registered_domain

    # 실제로 2단계 국가도메인이 표본에 있어야 이 검사가 의미를 갖는다.
    assert any(
        (row.registered_domain or "").endswith((".co.kr", ".or.kr", ".go.kr"))
        for row in url_review.itertuples()
    ), "2단계 국가도메인이 표본에 없으면 PSL 검사가 아무것도 지키지 않는다"


def test_cross_domain_redirects_are_queued_not_assumed(url_review: pd.DataFrame) -> None:
    """06 §3-3 — 외부 도메인으로 이동하면 같은 서비스라 가정하지 않고 QA 큐로 보낸다."""
    crossed = url_review[url_review["cross_registered_domain_redirect"]]
    for row in crossed.itertuples():
        assert row.review_status == "NEEDS_HUMAN_REVIEW"
        assert "CROSS_REGISTERED_DOMAIN_REDIRECT" in row.review_reasons


def test_confidence_and_review_flags_are_derived_from_the_observation(
    url_review: pd.DataFrame, probes: dict[tuple[str, str], dict]
) -> None:
    """신뢰도는 손입력이 아니다. 관측 기록에서 같은 값이 다시 나와야 한다."""
    builder = _load(BUILDER)
    for row in url_review.itertuples():
        probe = probes.get((row.canonical_service_key, row.observed_url))
        assert row.observation_confidence == builder.confidence_of(probe)
        expected = (
            "LOW" if row.web_eligibility_status == "UNRESOLVED" else row.observation_confidence
        )
        assert row.url_confidence == expected
        assert bool(row.review_reasons) == (row.review_status == "NEEDS_HUMAN_REVIEW")


# ══ W5 — 그룹 승격·해체와 가설 검정 ════════════════════════════════════════


def test_group_count_is_unchanged_and_membership_is_intact(
    web_target_group: pd.DataFrame, service_master: pd.DataFrame
) -> None:
    """W3/W4/W5 는 entity 수도 그룹 수도 바꾸지 않는다. 상태만 바꾼다."""
    assert len(web_target_group) == 68
    brand = service_master[service_master["axis_type"] == "SERVICE_BRAND"]
    assert int(web_target_group["member_count"].sum()) == len(brand) == 71
    assert len(service_master) == 81


def test_promotion_requires_a_confirmed_url(web_target_group: pd.DataFrame) -> None:
    """06 §3-4 — URL 이 확정된 뒤에만 승격한다."""
    for row in web_target_group.itertuples():
        if row.grouping_status in {"CONFIRMED_SHARED_TARGET", "SINGLETON_CONFIRMED"}:
            assert row.web_target_url, f"{row.web_target_key}: 승격됐는데 URL 이 없다"
            assert row.url_evidence
        else:
            assert not row.web_target_url, f"{row.web_target_key}: 미승격인데 URL 이 있다"


def test_confirmed_shared_target_members_really_share_one_url(
    web_target_group: pd.DataFrame, url_review: pd.DataFrame
) -> None:
    landing = dict(
        zip(url_review["canonical_service_key"], url_review["official_landing_url"], strict=True)
    )
    shared = web_target_group[web_target_group["grouping_status"] == "CONFIRMED_SHARED_TARGET"]
    assert len(shared) > 0
    for row in shared.itertuples():
        urls = {landing[m] for m in row.member_canonical_keys.split(",")}
        assert len(urls) == 1, f"{row.web_target_key}: 같은 URL 이 아닌데 승격됐다"
        assert row.web_target_url in urls


def test_falsified_hypotheses_are_recorded_not_deleted(
    web_target_group: pd.DataFrame,
) -> None:
    """**틀린 가설을 조용히 지우지 마라.** 선언과 결과가 같은 행에 있어야 한다.

    후보 3건은 전부 SAME_LANDING_EXPECTED 를 선언했다. 그중 몇 개가 틀렸는지는
    이 검사가 정하지 않는다 — 정하는 것은 '무엇을 예상했는지가 남아 있는가' 다.
    """
    cand = web_target_group[web_target_group["expected_url_relationship_is_hypothesis"]]
    assert set(cand["web_target_key"]) == {"coupang", "naver", "gmarket"}
    for row in cand.itertuples():
        assert row.expected_url_relationship == "SAME_LANDING_EXPECTED"
        assert row.expected_url_relationship_falsifier, "반증 조건이 지워졌다"
        assert row.expected_url_relationship_risk, "선언해 둔 위험이 지워졌다"
        assert row.hypothesis_outcome in {
            "CONFIRMED_SAME_LANDING",
            "FALSIFIED_DIFFERENT_LANDING",
            "FALSIFIED_NO_SINGLE_LANDING_FOR_MEMBER",
        }
        assert len(row.hypothesis_outcome_basis) > 40

    falsified = cand[cand["hypothesis_outcome"].str.startswith("FALSIFIED")]
    assert len(falsified) > 0, "틀린 가설이 하나도 없다면 이 검사는 아무것도 지키지 않는다"
    assert (falsified["grouping_status"] == "SPLIT").all()
    assert falsified["web_target_url"].isna().all()

    ledger = json.loads((STATE / "url_review_ledger.json").read_text(encoding="utf-8"))
    outcomes = {h["web_target_key"]: h for h in ledger["hypothesis_outcomes"]}
    assert set(outcomes) == {"coupang", "naver", "gmarket"}
    for key, entry in outcomes.items():
        assert entry["declared_falsifier"], f"{key}: 원장에서 반증 조건이 사라졌다"
        assert entry["outcome"] and entry["outcome_basis"]


# ══ §6 — URL 확인은 수집이 아니다 ══════════════════════════════════════════


def test_no_evidence_directory_was_created() -> None:
    assert not (RESEARCH / "evidence").exists(), "E001 본수집은 금지 상태다"


def test_probe_record_stores_no_page_content() -> None:
    """저장한 것은 06 §3-1/§3-3 이 요구한 필드뿐이다. 본문·DOM·스크린샷은 없다."""
    payload = json.loads((STATE / "url_review_probe.json").read_text(encoding="utf-8"))
    allowed = {
        "canonical_service_key",
        "target_url",
        "http_status",
        "final_url",
        "redirect_chain",
        "page_title",
        "content_language",
        "error",
        "elapsed_ms",
        "probed_at",
        "final_registered_domain",
        "target_registered_domain",
        "tls_compat_retry",
        "tls_compat_reason",
        "tls_default_posture_error",
    }
    for probe in payload["probes"]:
        extra = set(probe) - allowed
        assert not extra, f"관측 기록에 허용되지 않은 필드가 있다: {sorted(extra)}"
        assert len(probe.get("page_title") or "") <= 300
    assert payload["parallel_requests"] is False
    assert payload["delay_sec"] >= 1.0
    assert "6siegfriex@gmail.com" in payload["user_agent"]
    assert "academic" in payload["user_agent"]


# ══ 멱등성 ═════════════════════════════════════════════════════════════════


def test_eligibility_build_is_idempotent(tmp_path: Path) -> None:
    """네트워크는 (3)단계에서 끝났다. (4)단계는 같은 입력에 같은 출력을 낸다."""
    root = _sandbox(tmp_path)
    outputs = ["service_master.parquet", "url_review.parquet", "web_target_group.parquet"]
    assert _run(root).returncode == 0
    first = {name: (root / "state" / name).read_bytes() for name in outputs}
    assert _run(root).returncode == 0
    for name in outputs:
        assert (root / "state" / name).read_bytes() == first[name], f"{name} 이 재실행에서 달라졌다"
