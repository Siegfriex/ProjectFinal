"""C009/C011 — 감사 수용 시정이 코드로 강제되는지 검증한다.

이 파일이 지키는 것은 스키마의 모양이 아니라 **다시 저지르면 안 되는 실수**들이다.
각 테스트는 감사가 실제로 지적한 결함 하나에 대응한다.

C011 에서 추가된 원칙 하나:
    파생물끼리의 일치는 검증이 아니다. 원문 대조 테스트는 한쪽 끝이 반드시
    sources/wiseapp/raw/ 의 원본 파일이어야 한다.
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

import pandas as pd
import pytest

RESEARCH = Path(__file__).resolve().parents[1] / "research" / "landing_accessibility"
STATE = RESEARCH / "state"
WISEAPP = RESEARCH / "sources" / "wiseapp"
BODY_TEXT = WISEAPP / "raw" / "wiseapp933_text.txt"

EXPECTED_ROW_COUNT = 261
# C011(P1-2): SYSTEM_APP_CANDIDATE 는 A1~A4 인용 0건의 하드코딩 이름 목록이었다. 상태값에서 뺐다.
ALLOWED_ELIGIBILITY = {"NOT_ASSESSED", "EXCLUDED_INDUSTRY_AXIS"}
ALLOWED_GROUPING = {"CANDIDATE_PENDING_URL_REVIEW", "SINGLETON_PENDING_URL_REVIEW"}


def parse_index_from_body(body: str) -> list[dict]:
    """원문 본문의 'INDEX.' 블록을 파싱한다 — 대조의 한쪽 끝은 항상 원문이어야 한다."""
    lines = body.splitlines()
    start = next(i for i, ln in enumerate(lines) if ln.strip() == "INDEX.")
    out: list[dict] = []
    chapter: dict | None = None
    ch_re = re.compile(r"^Chapter\s+(\d+)\.\s*(.+)$")
    sec_re = re.compile(r"^\(\d+\)\s")
    for ln in lines[start + 1 :]:
        t = ln.strip()
        if not t:
            continue
        m = ch_re.match(t)
        if m:
            if chapter is not None and int(m.group(1)) <= chapter["chapter"]:
                break
            chapter = {"chapter": int(m.group(1)), "title": m.group(2), "sections": []}
            out.append(chapter)
        elif sec_re.match(t) and chapter is not None:
            chapter["sections"].append(t)
        else:
            break
    return out


pytestmark = pytest.mark.skipif(
    not (STATE / "service_master.parquet").exists(),
    reason="landing_accessibility state 산출물이 없다",
)


def _load(name: str) -> pd.DataFrame:
    return pd.read_parquet(STATE / f"{name}.parquet")


@pytest.fixture(scope="module")
def rows() -> pd.DataFrame:
    return _load("source_ranking_rows")


@pytest.fixture(scope="module")
def panels() -> pd.DataFrame:
    return _load("panel_registry")


@pytest.fixture(scope="module")
def service_master() -> pd.DataFrame:
    return _load("service_master")


@pytest.fixture(scope="module")
def web_target_group() -> pd.DataFrame:
    return _load("web_target_group")


@pytest.fixture(scope="module")
def authority() -> dict:
    return json.loads((WISEAPP / "authority_manifest.json").read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def source_index() -> list[dict]:
    """A1 원문 본문에서 직접 파싱한 INDEX — 파생물이 아니다."""
    return parse_index_from_body(BODY_TEXT.read_text(encoding="utf-8"))


# ── 261행 불변 ──────────────────────────────────────────────────────────────


def test_source_rows_still_261_after_c009(rows: pd.DataFrame) -> None:
    assert len(rows) == EXPECTED_ROW_COUNT
    assert rows["axis_type"].isin({"SERVICE_BRAND", "INDUSTRY_CATEGORY"}).all()
    # C009(D7): 원자료에서 직접 집계해도 업종/브랜드가 섞이지 않아야 한다.
    industry_rows = rows[rows["axis_type"] == "INDUSTRY_CATEGORY"]
    assert set(industry_rows["panel_id"]) == {"fig07_t1"}
    assert len(industry_rows) == 30


def test_every_row_carries_a_figure_source_pointer(rows: pd.DataFrame) -> None:
    """C009(D5): 행마다 어느 그림·어느 순위·어느 지표에서 왔는지 가리켜야 한다."""
    assert "figure_source_pointer" in rows.columns
    assert rows["figure_source_pointer"].notna().all()
    assert rows["figure_source_pointer"].nunique() == EXPECTED_ROW_COUNT
    rebuilt = (
        rows["figure_id"]
        + "#t"
        + rows["panel_id"].str.split("_t").str[1]
        + "/rank"
        + rows["rank"].astype(str)
        + "/"
        + rows["metric_name"]
    )
    assert (rebuilt == rows["figure_source_pointer"]).all()

    provenance = json.loads((STATE / "journal_provenance.json").read_text(encoding="utf-8"))
    assert provenance["rows_rebuilt"] == EXPECTED_ROW_COUNT
    assert provenance["cross_verifications_agreeing"] == provenance["cross_verifications"]


# ── D1: entity_kind 분리 ────────────────────────────────────────────────────


def test_entity_kind_is_gone_and_axes_are_separate(service_master: pd.DataFrame) -> None:
    """entity_kind 한 컬럼이 도메인과 축유형을 섞어 리테일 1위 쿠팡을 누락시켰다."""
    assert "entity_kind" not in service_master.columns
    assert "web_collectable" not in service_master.columns
    assert set(service_master["domain"]) == {"APP", "RETAIL"}
    assert set(service_master["axis_type"]) == {"SERVICE_BRAND", "INDUSTRY_CATEGORY"}

    # 리테일 브랜드 집합을 뽑을 때 쿠팡이 빠지지 않아야 한다 — 그것이 이 시정의 목적이다.
    retail_brands = service_master[
        (service_master["domain"] == "RETAIL") & (service_master["axis_type"] == "SERVICE_BRAND")
    ]
    assert "coupang_retail" in set(retail_brands["canonical_service_key"])
    assert not set(retail_brands["axis_type"]) & {"INDUSTRY_CATEGORY"}


# ── C: measurement_entity 축에서 도메인 교차 합산 불가 ───────────────────────


def test_measurement_entities_are_domain_pure(service_master: pd.DataFrame) -> None:
    """APP 지표와 RETAIL 지표는 다른 것을 잰다. 한 entity 가 둘 다 가질 수 없다."""
    both = service_master[
        (service_master["app_row_count"] > 0) & (service_master["retail_row_count"] > 0)
    ]
    assert both.empty, (
        f"도메인을 넘나드는 measurement_entity: {both['canonical_service_key'].tolist()}"
    )
    # 각 entity 는 정확히 한쪽에만 행을 갖는다.
    nonzero = (service_master["app_row_count"] > 0).astype(int) + (
        service_master["retail_row_count"] > 0
    ).astype(int)
    assert (nonzero == 1).all()

    # 도메인 컬럼과 행 수 컬럼이 서로 어긋나면 안 된다.
    app = service_master[service_master["domain"] == "APP"]
    retail = service_master[service_master["domain"] == "RETAIL"]
    assert (app["retail_row_count"] == 0).all()
    assert (retail["app_row_count"] == 0).all()


def test_coupang_is_split_into_two_measurement_entities(
    service_master: pd.DataFrame, rows: pd.DataFrame
) -> None:
    keys = set(service_master["canonical_service_key"])
    assert {"coupang_app", "coupang_retail"} <= keys
    assert "coupang" not in keys

    coupang = service_master[service_master["canonical_service_key"].str.startswith("coupang_")]
    coupang = coupang[coupang["service_name_canonical"] == "쿠팡"]
    assert len(coupang) == 2
    assert set(coupang["domain"]) == {"APP", "RETAIL"}
    # 원자료의 쿠팡 행이 두 entity 로 남김없이 갈렸는지 확인한다.
    raw_coupang = int((rows["entity_name_raw"] == "쿠팡").sum())
    assert int(coupang["app_row_count"].sum() + coupang["retail_row_count"].sum()) == raw_coupang


# ── D2: web_eligibility_status ──────────────────────────────────────────────


def test_web_eligibility_status_domain_is_closed(service_master: pd.DataFrame) -> None:
    values = set(service_master["web_eligibility_status"])
    assert values <= ALLOWED_ELIGIBILITY, f"허용되지 않은 상태값: {values - ALLOWED_ELIGIBILITY}"
    assert service_master["web_eligibility_basis"].notna().all()
    assert (service_master["web_eligibility_basis"].str.len() > 0).all()


def test_only_industry_axis_is_a_settled_exclusion(service_master: pd.DataFrame) -> None:
    """확정 판정은 업종 축 배제뿐이다. 나머지는 URL 증거가 없으므로 미평가로 남아야 한다."""
    excluded = service_master[service_master["web_eligibility_status"] == "EXCLUDED_INDUSTRY_AXIS"]
    assert set(excluded["axis_type"]) == {"INDUSTRY_CATEGORY"}
    assert len(excluded) == 10

    # C011(P1-2): 브랜드 축은 예외 없이 미평가다. 근거 없는 추정이 상태값을 가르면 안 된다.
    brands = service_master[service_master["axis_type"] == "SERVICE_BRAND"]
    assert set(brands["web_eligibility_status"]) == {"NOT_ASSESSED"}
    assert len(brands) == 71
    assert "SYSTEM_APP_CANDIDATE" not in set(service_master["web_eligibility_status"])


def test_unsourced_system_app_prior_is_outside_the_source_layer() -> None:
    """C011(P1-2): 선탑재 추정은 근거가 아니라 가설이다. Source Layer 밖에 있어야 한다."""
    path = STATE / "_researcher_priors" / "system_app_hypothesis.json"
    assert path.exists(), "연구자 사전판단 파일이 없다"
    priors = json.loads(path.read_text(encoding="utf-8"))

    # 파일 상단이 '연구 결과가 아니라 가설이며 Source Layer 가 아니다' 를 명시해야 한다.
    banner = priors["NOT_A_SOURCE_LAYER"]
    assert "연구 결과가 아니라 가설" in banner
    assert "Source Layer 가 아니다" in banner

    assert priors["hypothesis_count"] == 11
    assert len(priors["hypotheses"]) == 11
    for h in priors["hypotheses"]:
        assert h["status"] == "UNSOURCED_RESEARCHER_PRIOR"
        assert h["evidence_pointer"] is None
        assert h["resolves_at"] == "web_eligibility gate via URL evidence"
        assert h["hypothesis"] and h["basis"]

    # 감사가 임의성의 증거로 든 Google 포토는 여전히 가설 목록에 있고,
    # 그 가설이 service_master 상태값으로 새어나가지 않았음을 함께 고정한다.
    keys = {h["canonical_service_key"] for h in priors["hypotheses"]}
    assert "google_photos" in keys
    sm = pd.read_parquet(STATE / "service_master.parquet")
    leaked = sm[sm["canonical_service_key"].isin(keys)]
    assert set(leaked["web_eligibility_status"]) == {"NOT_ASSESSED"}


# ── C: web_target 층 ────────────────────────────────────────────────────────


def test_web_target_groups_have_no_urls_while_pending(web_target_group: pd.DataFrame) -> None:
    """URL 증거가 없다. 후보 상태에서 URL 칸이 채워지면 게이트를 건너뛴 것이다."""
    assert set(web_target_group["grouping_status"]) <= ALLOWED_GROUPING
    pending = web_target_group[
        web_target_group["grouping_status"].str.endswith("PENDING_URL_REVIEW")
    ]
    assert len(pending) == len(web_target_group), "URL 검토가 끝난 그룹이 있을 수 없다"
    assert pending["web_target_url"].isna().all(), "URL 미확정 상태에서 web_target_url 이 채워졌다"
    assert pending["url_evidence"].isna().all()


def test_web_target_candidates_are_the_three_declared_groups(
    web_target_group: pd.DataFrame, service_master: pd.DataFrame
) -> None:
    candidates = web_target_group[
        web_target_group["grouping_status"] == "CANDIDATE_PENDING_URL_REVIEW"
    ]
    assert set(candidates["web_target_key"]) == {"coupang", "naver", "gmarket"}
    assert (candidates["member_count"] == 2).all()
    # 후보 그룹은 도메인을 가로지르는 묶음이다 — 그래서 관측 1회 규칙이 필요하다.
    # C011(P1-1): member_domains 는 집합이 아니라 member_service_ids 와 위치가 대응하는
    # 배열이다. 순서는 service_id 정렬을 따르므로 문자열 자체를 단언하지 않는다.
    for row in candidates.itertuples():
        assert set(row.member_domains.split(",")) == {"APP", "RETAIL"}
        assert len(row.member_domains.split(",")) == row.member_count
    assert candidates["grouping_basis"].str.len().gt(0).all()

    # 업종 축은 web_target 층에 존재하지 않는다.
    industry = service_master[service_master["axis_type"] == "INDUSTRY_CATEGORY"]
    assert industry["web_target_group_id"].isna().all()

    # 브랜드 축 entity 는 전부 정확히 한 그룹에 속한다.
    brands = service_master[service_master["axis_type"] == "SERVICE_BRAND"]
    assert brands["web_target_group_id"].notna().all()
    member_total = int(web_target_group["member_count"].sum())
    assert member_total == len(brands)
    assert set(web_target_group["web_target_group_id"]) == set(brands["web_target_group_id"])


def test_web_target_member_arrays_are_positionally_aligned(
    web_target_group: pd.DataFrame, service_master: pd.DataFrame
) -> None:
    """C011(P1-1): 세 member_* 배열은 위치가 대응해야 한다.

    C009 판본은 member_service_ids / member_canonical_keys / member_domains 를 각각 독립
    정렬했다. wtg_6d5510a695d0a614(naver)에서 위치가 어긋나 naver_app↔RETAIL,
    naver_naverpay↔APP 으로 읽혔다. 집합 수준은 정확했지만 네이버·G마켓 2중수집을 막으려고
    만든 표가 같은 혼동을 재생산했다. 기존 테스트는 dedup 문자열만 봐서 못 잡았다.
    """
    domain_of = dict(zip(service_master["service_id"], service_master["domain"], strict=True))
    key_of = dict(
        zip(service_master["service_id"], service_master["canonical_service_key"], strict=True)
    )

    checked = 0
    for row in web_target_group.itertuples():
        ids = row.member_service_ids.split(",")
        keys = row.member_canonical_keys.split(",")
        domains = row.member_domains.split(",")
        assert len(ids) == len(keys) == len(domains) == row.member_count, (
            f"{row.web_target_group_id}: 세 배열의 길이가 다르다"
        )
        for i, sid_ in enumerate(ids):
            assert sid_ in domain_of, f"{row.web_target_group_id}[{i}]: 미등록 service_id {sid_}"
            assert domain_of[sid_] == domains[i], (
                f"{row.web_target_group_id}[{i}]: {sid_}({key_of[sid_]}) 의 도메인은 "
                f"{domain_of[sid_]} 인데 member_domains[{i}]={domains[i]} 다 — 위치 어긋남"
            )
            assert key_of[sid_] == keys[i], (
                f"{row.web_target_group_id}[{i}]: {sid_} 의 canonical key 는 {key_of[sid_]} 인데 "
                f"member_canonical_keys[{i}]={keys[i]} 다 — 위치 어긋남"
            )
            checked += 1
    assert checked == int(web_target_group["member_count"].sum())

    # 감사가 지목한 그룹을 이름으로 한 번 더 고정한다.
    naver = web_target_group[web_target_group["web_target_key"] == "naver"].iloc[0]
    pairs = dict(
        zip(
            naver["member_canonical_keys"].split(","),
            naver["member_domains"].split(","),
            strict=True,
        )
    )
    assert pairs == {"naver_app": "APP", "naver_naverpay": "RETAIL"}


# ── D4: 항상 참인 불변식을 통과로 계상하지 않는다 ───────────────────────────


def test_row_count_verification_distinguishes_declared_from_visual(panels: pd.DataFrame) -> None:
    assert set(panels["row_count_verification"]) == {"DECLARED_TOP_N", "VISUAL_COUNT_ONLY"}

    visual = panels[panels["row_count_verification"] == "VISUAL_COUNT_ONLY"]
    declared = panels[panels["row_count_verification"] == "DECLARED_TOP_N"]
    assert len(visual) == 8
    assert len(declared) == 9

    # 원문이 TOP N 을 선언하지 않은 패널은 rows_expected 가 비어 있어야 한다.
    # rows_expected 를 판독 행 수로 채우면 rows_expected == rows_extracted 가 구성상 항상 참이 되어
    # 검증력이 0 인데도 통과로 계상된다. 그 자기충족을 스키마에서 막는다.
    assert visual["rows_expected"].isna().all()
    assert visual["row_count_ok"].isna().all()
    assert declared["rows_expected"].notna().all()
    assert (declared["rows_expected"] == declared["rows_extracted"]).all()
    assert declared["row_count_ok"].fillna(False).all()

    # 어느 쪽이든 실제 판독 행 수는 남아 있어야 한다.
    assert panels["rows_extracted"].notna().all()
    assert int(panels["rows_extracted"].sum()) == 142  # 17패널의 표 행 수 합 (지표 전개 전)


def test_rows_expected_null_implies_visual_count_only(panels: pd.DataFrame) -> None:
    null_expected = panels[panels["rows_expected"].isna()]
    assert (null_expected["row_count_verification"] == "VISUAL_COUNT_ONLY").all()
    assert len(null_expected) == 8


# ── D3: chapter_guess 는 더 이상 추측이 아니다 ──────────────────────────────


def test_index_sections_are_verbatim_from_the_source_body(
    panels: pd.DataFrame, authority: dict, source_index: list[dict]
) -> None:
    """C011(P1-3): 대조의 한쪽 끝은 A1 원문 본문이어야 한다.

    C009 판본은 authority_manifest.index_from_source(파생 A)와
    panel_registry.source_section_title(파생 B)의 일치를 검사하고 그것을 '원문과의 1:1 대조가
    코드로 강제된다' 고 적었다. 파생물끼리의 일치는 검증이 아니다. 실제로 두 파생물은 원문의
    코호트 한정어 '액티브시니어+ 세대' 를 11개 절 전부에서 잃은 채 서로 일치하고 있었다.
    이 테스트는 raw/wiseapp933_text.txt 를 직접 파싱해 원문을 기준으로 삼는다.
    """
    assert "chapter_guess" not in panels.columns
    for col in ("source_chapter", "source_section", "source_section_title"):
        assert col in panels.columns
        assert panels[col].notna().all()
    assert panels["source_chapter"].between(1, 4).all()

    # 원문 본문 → (장, 절) -> 절 제목
    source_map = {
        (entry["chapter"], i): title
        for entry in source_index
        for i, title in enumerate(entry["sections"], 1)
    }
    assert len(source_map) == 11, f"원문 INDEX 절 파싱 결과가 11개가 아니다: {len(source_map)}"
    # 원문 절 제목은 전부 코호트 한정어를 갖거나 업종 축 표기다 — 한정어 삭제를 되살리지 못하게 한다.
    assert all("액티브시니어+ 세대" in t for t in source_map.values())
    assert source_map[(3, 2)] == "(2) 업종별 액티브시니어+ 세대 순 결제추정금액 TOP10"

    # (1) 파생 A — authority_manifest 는 원문 문자열 그대로여야 한다.
    manifest_map = {
        (entry["chapter"], i): title
        for entry in authority["index_from_source"]
        for i, title in enumerate(entry["sections"], 1)
    }
    assert manifest_map == source_map, "authority_manifest.index_from_source 가 원문과 다르다"
    manifest_titles = {e["chapter"]: e["title"] for e in authority["index_from_source"]}
    assert manifest_titles == {e["chapter"]: e["title"] for e in source_index}

    # (2) 파생 B — panel_registry 도 같은 원문 문자열이어야 한다.
    for panel in panels.itertuples():
        key = (int(panel.source_chapter), int(panel.source_section))
        assert key in source_map, f"{panel.panel_id}: 원문 INDEX 에 없는 (장, 절) {key}"
        assert source_map[key] == panel.source_section_title, (
            f"{panel.panel_id}: 절 제목이 원문과 다르다\n"
            f"  원문: {source_map[key]!r}\n  패널: {panel.source_section_title!r}"
        )
        # 장 제목도 원문 그대로여야 한다.
        chapter_title = next(e["title"] for e in source_index if e["chapter"] == key[0])
        assert panel.source_chapter_title == chapter_title

    # 원문 11개 절이 모두 패널로 덮여야 한다(누락 없음).
    covered = {(int(p.source_chapter), int(p.source_section)) for p in panels.itertuples()}
    assert covered == set(source_map)

    # 절 제목 문자열이 원문 본문에 실제로 존재하는지도 직접 확인한다.
    body = BODY_TEXT.read_text(encoding="utf-8")
    for title in set(panels["source_section_title"]):
        assert body.count(title) >= 1, f"원문 본문에 없는 절 제목: {title!r}"


# ── B2: fig07 기간 축 ───────────────────────────────────────────────────────


def test_period_axis_separates_single_month_panel(panels: pd.DataFrame) -> None:
    assert set(panels["period_axis"]) == {"HALF_YEAR", "SINGLE_MONTH"}
    single = panels[panels["period_axis"] == "SINGLE_MONTH"]
    assert set(single["panel_id"]) == {"fig07_t1"}
    assert len(panels[panels["period_axis"] == "HALF_YEAR"]) == 16
    # 기간 라벨도 '하반기' 프레이밍이 남아 있으면 안 된다.
    assert "하반기" not in single.iloc[0]["period_label"]
    assert "12월" in single.iloc[0]["period_label"]


# ── A / B1 / B3 / B4: authority_manifest ────────────────────────────────────


def test_legacy_xlsx_is_reframed_as_incompatible_panel_set(authority: dict) -> None:
    assert "legacy_conflict_detected" not in authority, "값 불일치 프레이밍이 되살아났다"
    assessment = authority["legacy_asset_assessment"]
    assert assessment["verdict"] == "UNSOURCED_INCOMPATIBLE_PANEL_SET"
    assert assessment["usable_as"] == "NONE"
    assert "금지" in assessment["prohibition"]

    kinds = {e["kind"] for e in assessment["evidence"]}
    assert {
        "MEMBERSHIP_MISMATCH",
        "INCONSISTENT_DRIFT",
        "NON_OVERLAPPING_PANEL",
        "ORDINAL_INVERSION",
        "PANEL_DEPTH_MISMATCH_BIDIRECTIONAL",
        "NO_PROVENANCE",
    } <= kinds


def _evidence(authority: dict, ev_id: str) -> dict:
    return next(e for e in authority["legacy_asset_assessment"]["evidence"] if e["id"] == ev_id)


def test_ev2_drift_signs_are_consistent_with_one_stated_convention(authority: dict) -> None:
    """C011(P2-1): 세 값이 전부 음수였다. 계산 규약이 없었고 카카오톡 부호가 틀렸다."""
    ev2 = _evidence(authority, "EV-2")
    assert ev2["kind"] == "INCONSISTENT_DRIFT"
    assert ev2["calculation"] == "drift_pct = (xlsx_value - source_value) / source_value * 100"

    drift = ev2["drift_pct"]
    assert drift == {"카카오톡": 0.15, "유튜브": -1.81, "네이버": -2.55}
    # 부호가 갈린다는 사실 자체가 논거다 — 한 방향으로 되돌아가면 이 테스트가 막는다.
    assert any(v > 0 for v in drift.values()) and any(v < 0 for v in drift.values())
    assert "부호가 갈린다" in ev2["detail"]

    # 규약대로 재산출했을 때 매니페스트가 인용한 값 쌍과 맞아야 한다.
    for source_v, xlsx_v, label in [(1377, 1379, "카카오톡"), (1256, 1224, "네이버")]:
        recomputed = round((xlsx_v - source_v) / source_v * 100, 2)
        assert recomputed == drift[label], f"{label}: {recomputed} != {drift[label]}"


def test_ev6_claims_only_what_the_file_actually_lacks(authority: dict) -> None:
    """C011(P2-2): '문서 속성이 전부 None' 은 과장이었다. created/modified 는 채워져 있다."""
    ev6 = _evidence(authority, "EV-6")
    assert ev6["kind"] == "NO_PROVENANCE"
    assert "전부 None" not in ev6["detail"], "실측과 어긋나는 과장 표현이 되살아났다"
    assert "openpyxl" in ev6["detail"]

    present = ev6["present_metadata"]
    assert present["created"] == "2026-08-25T15:54:10"
    assert present["modified"] == "2026-08-25T15:54:10"
    assert present["creator"] == "openpyxl"
    # 타임스탬프는 삭제하지 않고 실재하는 provenance 단서로 남는다.
    assert present["note"]


def test_methodology_is_recorded_verbatim(authority: dict) -> None:
    """'조사방법 미기재' 는 거짓이었다. 원문 표기가 그대로 실려 있어야 한다."""
    pop = authority["population_definition"]
    method = pop["methodology_verbatim"]
    assert method["APP"]["verbatim"] == "한국인 Android+iOS 스마트폰 사용자 추정."
    assert (
        "계좌이체, 현금거래, 상품권으로 결제한 금액은 포함되지 않음" in method["RETAIL"]["verbatim"]
    )
    assert "미기재" not in method["APP"]["verbatim"]

    # 원문 본문에 실제로 그 문장이 그 횟수만큼 있는지 대조한다.
    body = (RESEARCH / "sources" / "wiseapp" / "raw" / "wiseapp933_text.txt").read_text(
        encoding="utf-8"
    )
    for domain in ("APP", "RETAIL"):
        entry = method[domain]
        assert body.count(entry["verbatim"]) == entry["occurrences_in_body_text"]

    limitation = pop["study_limitation"]
    assert limitation["scope"].startswith("RETAIL")
    assert limitation["applies_to_app_domain"] is False
    assert "과소집계" in limitation["statement"]


def test_freeze_window_is_bounded_by_publisher_notice(authority: dict) -> None:
    window = authority["freeze_validity_window"]
    assert window["frozen_edition"].startswith("2026-08-26")
    notice = window["publisher_notice"]
    assert notice["nid"] == 127
    assert notice["apply_end"] is None
    assert notice["display"] == 1
    assert notice["apply_start"].startswith("2026-08-25")
    # 공지가 실제로 취득 자산 안에 있는지 대조한다.
    api = json.loads(
        (RESEARCH / "sources" / "wiseapp" / "raw" / "wiseapp933_api.json").read_text(
            encoding="utf-8"
        )
    )
    bodies = [e["body"] for e in api if "getlist.json" in e["url"]]
    assert bodies, "공지 API 응답이 취득 자산에 없다"
    notices = json.loads(bodies[0])["noticeList"]
    assert any(n["nid"] == 127 and n["applyEndDT"] is None for n in notices)


def test_image_inventory_reconciles_13_to_11(authority: dict) -> None:
    recon = authority["image_inventory_reconciliation"]
    assert recon["img_info_list_count"] == 13
    assert recon["figures_in_evidence_manifest"] == 11
    assert len(recon["excluded"]) == 2

    detail = json.loads(
        (RESEARCH / "sources" / "wiseapp" / "raw" / "wiseapp933_detail.json").read_text(
            encoding="utf-8"
        )
    )
    img_list = detail["insightInfo"]["imgInfoList"]
    assert len(img_list) == 13
    rendered = (RESEARCH / "sources" / "wiseapp" / "raw" / "wiseapp933_rendered.html").read_text(
        encoding="utf-8", errors="replace"
    )
    evidence = json.loads(
        (RESEARCH / "sources" / "wiseapp" / "source_evidence_manifest.json").read_text(
            encoding="utf-8"
        )
    )
    adopted = {f["source_url"].split("/")[-1]: f["figure_id"] for f in evidence["figures"]}

    for item in recon["excluded"]:
        name = item["img_path"].split("/")[-1]
        assert rendered.count(name) == 0, f"{name} 은 본문이 참조한다 — 제외 근거가 없다"
        assert name not in adopted
        # 후속본은 본문이 참조하고 figure 로 채택돼 있어야 한다.
        successor = item["superseded_by"]["img_path"].split("/")[-1]
        assert rendered.count(successor) >= 1
        assert adopted[successor] == item["superseded_by"]["figure_id"]
        assert item["img_size"] == item["superseded_by"]["img_size"]


# ── B7: INVALIDATED 자산 보존 ───────────────────────────────────────────────


def test_invalidated_assets_are_preserved_and_marked() -> None:
    inv = STATE / "_invalidated"
    assert inv.is_dir()
    for name in ("category_feasibility_matrix.csv", "service_certification_match_draft.csv"):
        path = inv / name
        assert path.exists(), f"폐기 산출물이 사라졌다: {name}"
        head = path.read_text(encoding="utf-8").splitlines()[:20]
        assert any("INVALIDATED" in line for line in head)
        assert any("UNSOURCED_INCOMPATIBLE_PANEL_SET" in line for line in head)
        # 데이터로 읽히면 안 된다 — 첫 줄이 주석이어야 한다.
        assert head[0].startswith("#")


# ── C011(P2-3): 판독 저널이 저장소 안에 있어야 한다 ─────────────────────────


def test_extraction_journal_is_committed_and_hashed() -> None:
    """clone 만으로 261행을 재현할 수 있어야 한다.

    C009 판본에서 build_source_rows_from_journal.py 의 유일한 입력인 저널은 세션 경로에만
    있고 미커밋이었다. Pilot 이 원증거를 gitignore 해 단일 머신에만 남긴 것과 동형 패턴이다.
    """
    evidence = json.loads((WISEAPP / "source_evidence_manifest.json").read_text(encoding="utf-8"))
    entry = evidence["extraction_journal"]
    path = RESEARCH / entry["file"]
    assert path.exists(), f"판독 저널이 저장소에 없다: {entry['file']}"

    data = path.read_bytes()
    assert len(data) == entry["bytes"]
    assert entry["sha256"] == "sha256:" + hashlib.sha256(data).hexdigest()

    # 저널이 실제로 figure 11종의 판독 결과를 담고 있는지 확인한다.
    figures = set()
    for line in data.decode("utf-8").splitlines():
        if not line.strip():
            continue
        result = json.loads(line).get("result")
        if isinstance(result, dict) and "figure_id" in result:
            figures.add(result["figure_id"])
    assert len(figures) == 11

    # 재생성 기록이 이 저장소 내부 파일을 가리켜야 한다.
    provenance = json.loads((STATE / "journal_provenance.json").read_text(encoding="utf-8"))
    assert provenance["journal_sha256"] == hashlib.sha256(data).hexdigest()
    assert provenance["journal_path_in_repo"] == "research/landing_accessibility/" + entry["file"]


# ── C011(P2-4): 재생성 일치 주장이 실제 비교여야 한다 ───────────────────────


def test_journal_rebuild_comparison_is_a_real_comparison() -> None:
    """`matches_existing_c002_output: existing.exists()` 는 통과를 위장하고 있었다."""
    provenance = json.loads((STATE / "journal_provenance.json").read_text(encoding="utf-8"))
    comparison = provenance["matches_existing_c002_output"]
    assert isinstance(comparison, dict), "파일 존재 여부를 일치로 계상하던 bool 이 되살아났다"
    assert comparison["compared"] is True
    assert comparison["result"] == "IDENTICAL"
    assert "assert_frame_equal" in comparison["method"]
    assert len(comparison["columns_compared"]) >= 14
    assert "source_row_id" in comparison["columns_compared"]

    # 실행 순서와, 단독 실행 시 이어받는 컬럼이 기록돼 있어야 한다.
    assert provenance["build_order"] == [
        "scripts/build_source_rows_from_journal.py",
        "scripts/build_canonical_entities.py",
    ]


def test_panel_scope_survives_a_standalone_journal_rebuild() -> None:
    """C011(P2-4): 저널 스크립트 단독 실행이 panel_registry 스키마를 깨면 안 된다."""
    panels = pd.read_parquet(STATE / "panel_registry.parquet")
    assert "panel_scope" in panels.columns
    assert panels["panel_scope"].notna().all()
    assert len(panels.columns) == 26

    src = (RESEARCH / "scripts" / "build_source_rows_from_journal.py").read_text(encoding="utf-8")
    assert "DOWNSTREAM_PANEL_COLUMNS" in src
    assert '"panel_scope"' in src


# ── C011(P2-5): period_axis 를 행 수준까지 전파한다 ─────────────────────────


def test_period_axis_is_propagated_to_rows(rows: pd.DataFrame, panels: pd.DataFrame) -> None:
    """'성장률' 은 HALF_YEAR 와 SINGLE_MONTH 에 걸친 유일한 metric_name 이다."""
    for col in ("period_axis", "period_label"):
        assert col in rows.columns, f"{col} 이 행 수준에 없다"
        assert rows[col].notna().all()

    assert set(rows["period_axis"]) == {"HALF_YEAR", "SINGLE_MONTH"}
    assert set(rows.loc[rows["period_axis"] == "SINGLE_MONTH", "panel_id"]) == {"fig07_t1"}

    # 패널 레지스트리와 행이 어긋나면 안 된다.
    panel_axis = dict(zip(panels["panel_id"], panels["period_axis"], strict=True))
    panel_label = dict(zip(panels["panel_id"], panels["period_label"], strict=True))
    assert (rows["panel_id"].map(panel_axis) == rows["period_axis"]).all()
    assert (rows["panel_id"].map(panel_label) == rows["period_label"]).all()

    # 이 컬럼이 필요한 이유 자체를 고정한다 — metric_name 만으로 집계하면 두 기간이 섞인다.
    growth = rows[rows["metric_name"] == "성장률"]
    assert set(growth["period_axis"]) == {"HALF_YEAR", "SINGLE_MONTH"}
    spanning = [m for m, sub in rows.groupby("metric_name") if sub["period_axis"].nunique() > 1]
    assert spanning == ["성장률"]
