"""C003/C009 원자료 무결성 검증 — research/landing_accessibility/state.

원자료(source_ranking_rows) 261행이 canonical 레이어를 거치며 한 행도 유실되거나
중복 매핑되지 않았는지, 그리고 service_id 가 Pilot 실패 원인이었던 한글 키를
재도입하지 않았는지 검증한다.

C009 이후 measurement_entity 의 키는 (entity_name_raw, domain) 이다. 같은 원문 표기라도
도메인이 다르면 다른 것을 잰 것이므로 별개 entity 이고, 별칭 유일성도 그 쌍을 기준으로 본다.
"""

from __future__ import annotations

import re
from pathlib import Path

import pandas as pd
import pytest

STATE = Path(__file__).resolve().parents[1] / "research" / "landing_accessibility" / "state"

EXPECTED_ROW_COUNT = 261
HANGUL = re.compile(r"[ᄀ-ᇿ㄰-㆏ꥠ-꥿가-퟿]")

pytestmark = pytest.mark.skipif(
    not (STATE / "source_ranking_rows.parquet").exists(),
    reason="landing_accessibility state 산출물이 없다",
)


def _load(name: str) -> pd.DataFrame:
    path = STATE / f"{name}.parquet"
    assert path.exists(), f"산출물 누락: {path}"
    return pd.read_parquet(path)


@pytest.fixture(scope="module")
def rows() -> pd.DataFrame:
    return _load("source_ranking_rows")


@pytest.fixture(scope="module")
def alias_map() -> pd.DataFrame:
    return _load("entity_alias_map")


@pytest.fixture(scope="module")
def service_master() -> pd.DataFrame:
    return _load("service_master")


@pytest.fixture(scope="module")
def membership() -> pd.DataFrame:
    return _load("source_membership")


def test_source_row_count_is_261(rows: pd.DataFrame) -> None:
    assert len(rows) == EXPECTED_ROW_COUNT


def test_source_row_ids_unique(rows: pd.DataFrame) -> None:
    dupes = rows.loc[rows["source_row_id"].duplicated(keep=False), "source_row_id"].tolist()
    assert not dupes, f"중복 source_row_id: {sorted(set(dupes))}"
    assert rows["source_row_id"].notna().all()


def test_every_entity_key_maps_to_exactly_one_alias(
    rows: pd.DataFrame, alias_map: pd.DataFrame
) -> None:
    """C009: 별칭 키는 (entity_name_raw, domain) 쌍이다."""
    key_cols = ["entity_name_raw", "domain"]
    dupes = alias_map[alias_map.duplicated(key_cols, keep=False)]
    assert dupes.empty, f"별칭이 둘 이상인 (표기, 도메인): {dupes[key_cols].to_dict('records')}"

    raw_keys = set(map(tuple, rows[key_cols].drop_duplicates().to_numpy()))
    alias_keys = set(map(tuple, alias_map[key_cols].to_numpy()))
    assert not (raw_keys - alias_keys), f"별칭 미등록: {sorted(raw_keys - alias_keys)}"
    assert not (alias_keys - raw_keys), f"원자료에 없는 별칭: {sorted(alias_keys - raw_keys)}"

    # 261행이 정확히 261행으로 조인되어야 한다 (행 손실/증식 금지)
    joined = rows.merge(
        alias_map[[*key_cols, "alias_id", "service_id"]],
        on=key_cols,
        how="left",
        validate="many_to_one",
    )
    assert len(joined) == EXPECTED_ROW_COUNT
    assert joined["alias_id"].notna().all()


def test_alias_service_ids_exist_in_service_master(
    alias_map: pd.DataFrame, service_master: pd.DataFrame
) -> None:
    known = set(service_master["service_id"])
    orphans = sorted(set(alias_map["service_id"]) - known)
    assert not orphans, f"service_master 에 없는 service_id: {orphans}"
    assert not service_master["service_id"].duplicated().any()

    # service_master 집계값이 실제 별칭 수와 일치해야 한다
    actual = alias_map.groupby("service_id").size()
    declared = service_master.set_index("service_id")["alias_count"]
    mismatch = declared[declared.ne(actual.reindex(declared.index, fill_value=0))]
    assert mismatch.empty, f"alias_count 불일치: {mismatch.to_dict()}"


def test_ranks_are_contiguous_and_unique_per_panel(rows: pd.DataFrame) -> None:
    for panel_id, sub in rows.groupby("panel_id"):
        ranks = sorted(sub["rank"].unique())
        assert ranks == list(range(1, len(ranks) + 1)), f"{panel_id}: rank 불연속 {ranks}"
        dupes = sub[sub.duplicated(["metric_name", "rank"], keep=False)]
        assert dupes.empty, f"{panel_id}: (metric, rank) 중복 {len(dupes)}건"
        # 한 패널 안에서 한 entity 는 하나의 rank 만 가진다
        multi = sub.groupby("entity_name_raw")["rank"].nunique()
        assert (multi == 1).all(), (
            f"{panel_id}: entity 당 rank 가 여럿 {multi[multi > 1].to_dict()}"
        )


def test_service_ids_contain_no_hangul(
    service_master: pd.DataFrame, alias_map: pd.DataFrame, membership: pd.DataFrame
) -> None:
    for label, series in [
        ("service_master.service_id", service_master["service_id"]),
        ("service_master.canonical_service_key", service_master["canonical_service_key"]),
        ("entity_alias_map.service_id", alias_map["service_id"]),
        ("entity_alias_map.alias_id", alias_map["alias_id"]),
        ("source_membership.service_id", membership["service_id"]),
    ]:
        bad = [v for v in series if HANGUL.search(str(v))]
        assert not bad, f"{label} 에 한글 포함: {bad}"
        assert all(str(v).isascii() for v in series), f"{label} 에 비 ASCII 포함"


def test_membership_service_panel_pairs_unique(
    membership: pd.DataFrame, rows: pd.DataFrame, alias_map: pd.DataFrame
) -> None:
    dupes = membership[membership.duplicated(["service_id", "panel_id"], keep=False)]
    assert dupes.empty, f"(service_id, panel_id) 중복 {len(dupes)}건"

    expected = (
        rows.merge(
            alias_map[["entity_name_raw", "domain", "service_id"]],
            on=["entity_name_raw", "domain"],
            how="left",
        )
        .groupby(["service_id", "panel_id"])
        .size()
    )
    assert len(membership) == len(expected), (
        "membership 행 수가 원자료 (service, panel) 조합과 다르다"
    )
    assert set(zip(membership["service_id"], membership["panel_id"], strict=True)) == set(
        expected.index
    )


def test_axis_type_separates_industry_categories(service_master: pd.DataFrame) -> None:
    panels = _load("panel_registry")
    assert "axis_type" in panels.columns and "panel_scope" in panels.columns
    assert set(panels.loc[panels["axis_type"] == "INDUSTRY_CATEGORY", "panel_id"]) == {"fig07_t1"}
    assert panels["panel_scope"].notna().all()

    industry = service_master[service_master["axis_type"] == "INDUSTRY_CATEGORY"]
    assert len(industry) == 10
    assert set(industry["web_eligibility_status"]) == {"EXCLUDED_INDUSTRY_AXIS"}
    # 업종 축은 RETAIL 도메인 안에 있다 — domain 만으로는 걸러지지 않는다는 사실 자체를 고정한다.
    assert set(industry["domain"]) == {"RETAIL"}

    brands = service_master[service_master["axis_type"] == "SERVICE_BRAND"]
    assert "EXCLUDED_INDUSTRY_AXIS" not in set(brands["web_eligibility_status"])


def test_source_row_count_preserved_end_to_end(
    rows: pd.DataFrame, service_master: pd.DataFrame
) -> None:
    """C009: source_row_count 는 도메인별로 쪼개졌다. 합계는 여전히 261 이어야 한다."""
    assert "source_row_count" not in service_master.columns, (
        "도메인 교차 합산이 가능한 source_row_count 가 되살아났다"
    )
    total = int(service_master["app_row_count"].sum() + service_master["retail_row_count"].sum())
    assert total == EXPECTED_ROW_COUNT
    assert int(service_master["app_row_count"].sum()) == int((rows["domain"] == "APP").sum())
    assert int(service_master["retail_row_count"].sum()) == int((rows["domain"] == "RETAIL").sum())
