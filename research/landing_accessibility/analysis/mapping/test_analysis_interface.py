"""매핑 레이어 불변조건 회귀검사 (A2 §5.7 규칙 V-6)."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest
from analysis_interface import (
    MappingInvariantError,
    StateFrames,
    bridge_source_membership,
    dim_measurement_entity,
    dim_panel,
    dim_panel_metric,
    fact_source_ranking,
    load_state,
    materialize_all,
    rank_anchor_metrics,
)


@pytest.fixture(scope="module")
def state() -> StateFrames:
    return load_state()


# --- 물리 기준선 (하드코딩이 아니라 원본에서 재확인) -------------------------


def test_physical_baseline(state: StateFrames) -> None:
    assert len(state.panel_registry) == state.panel_registry["panel_id"].nunique()
    assert len(state.source_ranking_rows) == state.source_ranking_rows["source_row_id"].nunique()
    assert len(state.service_master) == state.service_master["service_id"].nunique()


# --- dim_panel ---------------------------------------------------------------


def test_dim_panel_grain(state: StateFrames) -> None:
    out = dim_panel(state)
    assert len(out) == len(state.panel_registry)
    assert out["panel_id"].is_unique


def test_dim_panel_has_no_metric_scalar(state: StateFrames) -> None:
    """n_metrics>1 패널이 있으므로 panel grain에 metric_name/unit을 두지 않는다(A2 §5.1 ①안)."""
    out = dim_panel(state)
    assert "metric_name" not in out.columns
    assert "unit" not in out.columns
    assert (state.panel_registry["n_metrics"] > 1).sum() > 0


def test_dim_panel_missing_not_zero_filled(state: StateFrames) -> None:
    out = dim_panel(state)
    assert out["rows_expected"].isna().sum() == state.panel_registry["rows_expected"].isna().sum()
    assert out["rows_expected"].isna().sum() > 0
    assert str(out["rows_expected"].dtype) == "Int64"


def test_dim_panel_metric_bridge(state: StateFrames) -> None:
    out = dim_panel_metric(state)
    assert len(out) == int(state.panel_registry["n_metrics"].sum())
    assert not out.duplicated(subset=["panel_id", "metric_index"]).any()
    # metric_columns JSON과 1:1
    total = sum(len(json.loads(v)) for v in state.panel_registry["metric_columns"])
    assert len(out) == total


# --- fact_source_ranking -----------------------------------------------------


def test_fact_source_ranking_grain(state: StateFrames) -> None:
    out = fact_source_ranking(state)
    assert len(out) == len(state.source_ranking_rows)
    assert out["source_row_id"].is_unique
    assert out["measurement_entity_id"].isna().sum() == 0


def test_fact_source_ranking_no_fanout(state: StateFrames) -> None:
    keys = ["entity_name_raw", "domain", "axis_type"]
    assert not state.entity_alias_map.duplicated(subset=keys).any()
    assert len(fact_source_ranking(state)) == len(state.source_ranking_rows)


def test_fact_source_ranking_keeps_raw_name(state: StateFrames) -> None:
    out = fact_source_ranking(state)
    assert "entity_name_raw" in out.columns
    assert (
        out["entity_name_raw"].nunique() == state.source_ranking_rows["entity_name_raw"].nunique()
    )


def test_fact_source_ranking_missing_preserved(state: StateFrames) -> None:
    out = fact_source_ranking(state)
    assert out["raw_value"].isna().sum() == state.source_ranking_rows["value"].isna().sum()
    assert out["raw_value"].isna().sum() > 0
    assert (out["raw_value"] == 0).sum() == (state.source_ranking_rows["value"] == 0).sum()


def test_display_name_is_not_a_join_key(state: StateFrames) -> None:
    """표시명 조인 금지 근거 — service_name_canonical은 유일하지 않다(A2 §5.3 지적 2)."""
    sm = state.service_master
    assert sm["service_name_canonical"].nunique() < len(sm)
    assert sm["canonical_service_key"].is_unique


# --- dim_measurement_entity --------------------------------------------------


def test_dim_measurement_entity_grain(state: StateFrames) -> None:
    out = dim_measurement_entity(state)
    assert len(out) == len(state.service_master)
    assert out["measurement_entity_id"].is_unique


def test_review_status_domain_closed(state: StateFrames) -> None:
    out = dim_measurement_entity(state)
    allowed = {"NOT_IN_REVIEW_QUEUE", "KEEP_SEPARATE", "MERGE", "PENDING_HUMAN_REVIEW"}
    assert set(out["review_status"].unique()) <= allowed
    assert out["review_status"].isna().sum() == 0
    counts = out["review_status"].value_counts()
    assert counts.sum() == len(state.service_master)
    assert counts.get("KEEP_SEPARATE", 0) == int(
        (state.service_master["review_decision"] == "KEEP_SEPARATE").sum()
    )


# --- bridge_source_membership ------------------------------------------------


def test_bridge_is_source_row_grain(state: StateFrames) -> None:
    out = bridge_source_membership(state)
    assert len(out) == len(state.source_ranking_rows)
    assert len(out) != len(state.source_membership)  # 142가 아니다
    assert out["source_row_id"].is_unique


def test_bridge_aggregate_matches_physical(state: StateFrames) -> None:
    out = bridge_source_membership(state)
    derived = set(
        map(tuple, out[["measurement_entity_id", "panel_id"]].drop_duplicates().to_numpy())
    )
    stored = set(map(tuple, state.source_membership[["service_id", "panel_id"]].to_numpy()))
    assert derived == stored
    assert len(derived) == len(state.source_membership)


def test_bridge_third_path_alias_explode(state: StateFrames) -> None:
    """세 번째 경로 — entity_alias_map.panel_ids explode도 같은 집합을 준다(A2 §5.2.1)."""
    am = state.entity_alias_map.assign(panel_id=state.entity_alias_map["panel_ids"].str.split(","))
    exploded = am.explode("panel_id")
    third = set(map(tuple, exploded[["service_id", "panel_id"]].drop_duplicates().to_numpy()))
    stored = set(map(tuple, state.source_membership[["service_id", "panel_id"]].to_numpy()))
    assert third == stored


# --- 실패 경로 ---------------------------------------------------------------


def test_invariant_raises_on_broken_join(state: StateFrames) -> None:
    """미매칭이 생기면 조용히 넘어가지 않고 예외를 던진다."""
    broken = state.entity_alias_map.iloc[1:].copy()
    tampered = StateFrames(
        panel_registry=state.panel_registry,
        source_ranking_rows=state.source_ranking_rows,
        service_master=state.service_master,
        entity_alias_map=broken,
        source_membership=state.source_membership,
    )
    with pytest.raises(MappingInvariantError):
        fact_source_ranking(tampered)


def test_invariant_raises_on_fanout(state: StateFrames) -> None:
    dup = pd.concat([state.entity_alias_map, state.entity_alias_map.iloc[[0]]], ignore_index=True)
    tampered = StateFrames(
        panel_registry=state.panel_registry,
        source_ranking_rows=state.source_ranking_rows,
        service_master=state.service_master,
        entity_alias_map=dup,
        source_membership=state.source_membership,
    )
    with pytest.raises(MappingInvariantError):
        bridge_source_membership(tampered)


# --- materialization ---------------------------------------------------------


def test_materialize_all(tmp_path: Path) -> None:
    written = materialize_all(tmp_path)
    assert set(written) >= {
        "dim_panel",
        "fact_source_ranking",
        "dim_measurement_entity",
        "bridge_source_membership",
    }
    for path in written.values():
        assert path.is_file()
        assert len(pd.read_parquet(path)) > 0


def test_materialize_refuses_overwriting_state() -> None:
    from analysis_interface import DEFAULT_STATE_DIR

    with pytest.raises(MappingInvariantError):
        materialize_all(DEFAULT_STATE_DIR)


# --- EDA-00 grain 결함의 매핑 레이어 반영 -----------------------------------


def test_f01_panel_row_counts_are_grain_explicit(state: StateFrames) -> None:
    """F-01 — `rows_extracted`는 entity 수다. 논리 표는 두 grain을 이름으로 가른다."""
    panels = dim_panel(state)
    assert {"n_entities_extracted", "n_source_rows"} <= set(panels.columns)
    # 물리 rows_extracted 를 그대로 옮긴 값이며 이름만 grain을 드러낸다.
    assert (
        panels["n_entities_extracted"].tolist() == state.panel_registry["rows_extracted"].tolist()
    )
    # 사다리: source row = entity x metric, 전 패널에서 성립.
    assert (panels["n_source_rows"] == panels["n_entities_extracted"] * panels["n_metrics"]).all()
    assert int(panels["n_source_rows"].sum()) == len(state.source_ranking_rows)
    # 두 값이 실제로 갈리는 패널이 있어야 이 구분이 의미를 갖는다.
    assert int((panels["n_source_rows"] != panels["n_entities_extracted"]).sum()) > 0


def test_f09_rank_anchor_is_declared(state: StateFrames) -> None:
    """F-09 — rank가 정렬하지 않는 (panel, metric)이 실제로 있고, 표가 그것을 알린다."""
    anchors = rank_anchor_metrics(state)
    assert set(anchors["rank_monotonicity"]) <= {"DESC", "ASC", "NON_MONOTONE", "UNDETERMINED"}
    # 패널마다 anchor는 정확히 하나여야 rank의 의미가 단일하다.
    per_panel = anchors.groupby("panel_id")["is_rank_anchor"].sum()
    assert per_panel.min() >= 1
    assert per_panel.max() == 1
    # anchor가 아닌 (panel, metric)이 존재한다 = rank 복제 문제가 실재한다.
    assert int((~anchors["is_rank_anchor"]).sum()) > 0


def test_f09_fact_carries_rank_semantics(state: StateFrames) -> None:
    fact = fact_source_ranking(state)
    assert "rank_orders_this_metric" in fact.columns
    assert fact["rank_orders_this_metric"].notna().all()
    # anchor 행과 비-anchor 행이 둘 다 있어야 컬럼이 정보를 가진다.
    assert 0 < int(fact["rank_orders_this_metric"].sum()) < len(fact)


def test_f10_entity_table_mixes_two_kinds(state: StateFrames) -> None:
    """F-10 — 81 entity = 브랜드 + 업종. 매핑 분모는 81이 아니다."""
    ents = dim_measurement_entity(state)
    assert "is_web_mappable_entity" in ents.columns
    n_mappable = int(ents["is_web_mappable_entity"].sum())
    assert 0 < n_mappable < len(ents)
    assert n_mappable == int(state.service_master["axis_type"].eq("SERVICE_BRAND").sum())
    # 업종은 web target을 갖지 않는다.
    industry_ids = ents.loc[~ents["is_web_mappable_entity"], "measurement_entity_id"]
    sm = state.service_master.set_index("service_id")
    assert sm.loc[industry_ids, "web_target_group_id"].isna().all()


def test_f08_aggregation_view_loses_metric_axis(state: StateFrames) -> None:
    """F-08 — 물리 142행은 metric 축을 잃은 집계 뷰다. rank는 min이라는 요약값이다."""
    bridge = bridge_source_membership(state)
    fact = fact_source_ranking(state)
    pair_metrics = fact.groupby(["measurement_entity_id", "panel_id"])["metric_name"].nunique()
    assert int((pair_metrics > 1).sum()) > 0
    # bridge는 source row grain이라 축이 살아 있다.
    assert len(bridge) == len(state.source_ranking_rows)
    assert len(pair_metrics) == len(state.source_membership)
