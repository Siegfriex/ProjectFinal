"""C009 — 감사 수용 시정이 코드로 강제되는지 검증한다.

이 파일이 지키는 것은 스키마의 모양이 아니라 **다시 저지르면 안 되는 실수**들이다.
각 테스트는 감사가 실제로 지적한 결함 하나에 대응한다.
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

RESEARCH = Path(__file__).resolve().parents[1] / "research" / "landing_accessibility"
STATE = RESEARCH / "state"
WISEAPP = RESEARCH / "sources" / "wiseapp"

EXPECTED_ROW_COUNT = 261
ALLOWED_ELIGIBILITY = {"NOT_ASSESSED", "EXCLUDED_INDUSTRY_AXIS", "SYSTEM_APP_CANDIDATE"}
ALLOWED_GROUPING = {"CANDIDATE_PENDING_URL_REVIEW", "SINGLETON_PENDING_URL_REVIEW"}

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

    # 선탑재 의심 앱은 표시일 뿐 배제가 아니다 — 전부 APP 도메인 브랜드 축에 있어야 한다.
    system_apps = service_master[service_master["web_eligibility_status"] == "SYSTEM_APP_CANDIDATE"]
    assert len(system_apps) > 0
    assert set(system_apps["domain"]) == {"APP"}
    assert set(system_apps["axis_type"]) == {"SERVICE_BRAND"}
    # 감사가 지목한 세 앱은 반드시 표시돼 있어야 한다.
    flagged = set(system_apps["service_name_canonical"])
    assert {"삼성 계산기", "내 파일", "디바이스 케어"} <= flagged


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
    assert set(candidates["member_domains"]) == {"APP,RETAIL"}
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


def test_chapter_is_normalized_not_guessed(panels: pd.DataFrame, authority: dict) -> None:
    assert "chapter_guess" not in panels.columns
    for col in ("source_chapter", "source_section", "source_section_title"):
        assert col in panels.columns
        assert panels[col].notna().all()
    assert panels["source_chapter"].between(1, 4).all()

    # 원문 index 와 1:1 로 맞아야 한다 — 이것이 '추측이 아니다' 의 내용이다.
    index_map = {
        (entry["chapter"], i): title
        for entry in authority["index_from_source"]
        for i, title in enumerate(entry["sections"], 1)
    }
    for panel in panels.itertuples():
        key = (int(panel.source_chapter), int(panel.source_section))
        assert key in index_map, f"{panel.panel_id}: 원문 index 에 없는 (장, 절) {key}"
        assert index_map[key] == panel.source_section_title, (
            f"{panel.panel_id}: 절 제목이 원문 index 와 다르다"
        )
    # 원문 11개 절이 모두 패널로 덮여야 한다(누락 없음).
    covered = {(int(p.source_chapter), int(p.source_section)) for p in panels.itertuples()}
    assert covered == set(index_map)


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
