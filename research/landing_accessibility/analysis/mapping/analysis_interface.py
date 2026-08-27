"""P-A 매핑/머티리얼라이제이션 레이어 — 논리표 4종 read-only 제공.

권위: ``docs/v2/A2_VOCABULARY_AND_SCHEMA_BINDING.md`` §5 논리↔물리 대응표.
규칙 V-1/V-4/V-5 — ``state/*.parquet`` 원본은 **읽기만** 하고 쓰지 않으며,
산출물은 원본과 다른 디렉터리에 둔다.

논리표 ↔ 물리파일:

======================== ============================ ===========
논리표                    물리 근거                     grain
======================== ============================ ===========
``dim_panel``            ``panel_registry``           panel 17
``fact_source_ranking``  ``source_ranking_rows``      source row 261
                         ⋈ ``entity_alias_map``
``dim_measurement_entity`` ``service_master``         entity 81
``bridge_source_membership`` 위 조인의 투영            source row 261
======================== ============================ ===========

물리 ``source_membership``(142행)은 논리 bridge가 **아니라** 그 집계 뷰다(A2 §5.4).
여기서는 회귀검사 대상으로만 쓴다.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Final

import pandas as pd

__all__ = [
    "DEFAULT_STATE_DIR",
    "RESEARCH_ROOT",
    "MappingInvariantError",
    "StateFrames",
    "bridge_source_membership",
    "dim_measurement_entity",
    "dim_panel",
    "dim_panel_metric",
    "fact_source_ranking",
    "load_state",
    "materialize_all",
    "rank_anchor_metrics",
]

# `analysis/mapping/analysis_interface.py` → `research/landing_accessibility/`
RESEARCH_ROOT: Final[Path] = Path(__file__).resolve().parents[2]

# 이 파일이 사는 워크트리의 `state/`를 읽는다. 다른 워크트리 경로를 하드코딩하면
# 동시 작업 중인 다른 주체의 상태에 결과가 좌우된다(SHADOW lane 격리 위반).
# 재지정은 환경변수 `LANDING_STATE_DIR` 로만 한다.
DEFAULT_STATE_DIR: Final[Path] = Path(
    os.environ.get("LANDING_STATE_DIR", str(RESEARCH_ROOT / "state"))
)

# A2 §5.2.1 — 조인 키 3요소. `entity_name_raw` 단독은 '쿠팡'에서 fan-out을 일으킨다.
_JOIN_KEYS: Final[list[str]] = ["entity_name_raw", "domain", "axis_type"]

# A2 §1.1 review_status 열거형 (닫힌 집합, 규칙 S-3).
_REVIEW_STATUS_DOMAIN: Final[frozenset[str]] = frozenset(
    {"NOT_IN_REVIEW_QUEUE", "KEEP_SEPARATE", "MERGE", "PENDING_HUMAN_REVIEW"}
)


class MappingInvariantError(AssertionError):
    """불변조건 위반. 조용히 넘기지 않고 반드시 던진다(요구 4)."""


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise MappingInvariantError(message)


def _require_unique(frame: pd.DataFrame, keys: list[str], label: str) -> None:
    dup = int(frame.duplicated(subset=keys).sum())
    _require(dup == 0, f"{label}: {keys} 중복 {dup}행")


@dataclass(frozen=True)
class StateFrames:
    """물리 parquet 원본. 읽기 전용으로만 다룬다."""

    panel_registry: pd.DataFrame
    source_ranking_rows: pd.DataFrame
    service_master: pd.DataFrame
    entity_alias_map: pd.DataFrame
    source_membership: pd.DataFrame


def load_state(state_dir: Path | str = DEFAULT_STATE_DIR) -> StateFrames:
    """물리 parquet 5종을 읽는다. 수치·매핑은 전부 여기서만 유도된다(하드코딩 금지)."""
    base = Path(state_dir)
    _require(base.is_dir(), f"state 디렉터리 없음: {base}")

    def _read(name: str) -> pd.DataFrame:
        path = base / f"{name}.parquet"
        _require(path.is_file(), f"물리 파일 없음: {path}")
        return pd.read_parquet(path)

    return StateFrames(
        panel_registry=_read("panel_registry"),
        source_ranking_rows=_read("source_ranking_rows"),
        service_master=_read("service_master"),
        entity_alias_map=_read("entity_alias_map"),
        source_membership=_read("source_membership"),
    )


def _joined_source_rows(state: StateFrames) -> pd.DataFrame:
    """A2 §5.2.1 — ``source_ranking_rows ⋈ entity_alias_map`` 1:1 조인.

    fan-out 0 / 미매칭 0을 스스로 단언한다. 다른 함수들의 공통 기반.
    """
    left = state.source_ranking_rows
    right = state.entity_alias_map[[*_JOIN_KEYS, "service_id"]]

    _require_unique(right, _JOIN_KEYS, "entity_alias_map 조인 키")

    n_left = len(left)
    merged = left.merge(right, on=_JOIN_KEYS, how="left", validate="many_to_one")

    _require(
        len(merged) == n_left,
        f"fan-out 발생: {n_left}행 → {len(merged)}행",
    )
    unmatched = int(merged["service_id"].isna().sum())
    _require(unmatched == 0, f"measurement_entity_id 미매칭 {unmatched}행")
    return merged.rename(columns={"service_id": "measurement_entity_id"})


def dim_panel(state: StateFrames) -> pd.DataFrame:
    """논리 ``dim_panel`` (panel 17행). A2 §5.1.

    **grain 결정(A2 §5.1 지적 1의 ①안).** ``metric_name``/``unit``은 panel당 1~4개라
    panel grain에서 단일값이 성립하지 않는다(n_metrics>1 패널 9개). 임의로 첫 값을 고르는 대신
    두 컬럼을 ``dim_panel``에서 **빼고** ``fact_source_ranking`` 수준에서만 다룬다.
    ②안(panel x metric 브리지)은 :func:`dim_panel_metric` 로 별도 제공한다.

    ``rows_expected`` 결측은 0으로 채우지 않는다(01 §11 · A2 §7-2).
    """
    src = state.panel_registry
    out = src[
        [
            "panel_id",
            "domain",
            "axis_type",
            "source_section",
            "period_axis",
            "rows_expected",
            # 계보 유지: metric은 스칼라가 아님을 드러내는 개수 컬럼만 남긴다(규칙 V-7).
            "n_metrics",
        ]
    ].copy()

    # EDA-00 F-01 시정 — 물리 `rows_extracted`는 **source row 수가 아니라 entity 수**다.
    # 이름이 그 사실을 숨기므로 논리 표에서는 grain을 이름에 드러내 두 개로 분리한다(규칙 V-7).
    out["n_entities_extracted"] = src["rows_extracted"].to_numpy()
    n_rows_by_panel = state.source_ranking_rows.groupby("panel_id").size()
    out["n_source_rows"] = out["panel_id"].map(n_rows_by_panel).astype("int64")

    _require_unique(out, ["panel_id"], "dim_panel")
    _require(len(out) == len(src), f"dim_panel 행수 {len(out)} != panel_registry {len(src)}")
    _require(
        "metric_name" not in out.columns and "unit" not in out.columns,
        "dim_panel에 panel grain이 아닌 metric_name/unit이 섞였다",
    )
    # 결측 보존 확인 — Int64 nullable 유지, 0 치환 금지.
    _require(
        str(out["rows_expected"].dtype) == "Int64",
        f"rows_expected dtype이 nullable 정수가 아니다: {out['rows_expected'].dtype}",
    )
    multi = int((out["n_metrics"] > 1).sum())
    _require(
        multi > 0,
        "n_metrics>1 패널이 0개다 — A2 §5.1 실측(9개)과 어긋난다. 입력 데이터를 확인하라",
    )
    # EDA-00 F-01 — `n_source_rows == n_entities_extracted x n_metrics` 가 전 패널에서 성립해야
    # 261 = 142 x metric 전개라는 grain 사다리가 유지된다. 깨지면 물리 추출이 어긋난 것이다.
    bad = out.loc[
        out["n_source_rows"] != out["n_entities_extracted"] * out["n_metrics"], "panel_id"
    ]
    _require(
        len(bad) == 0,
        f"n_source_rows != n_entities_extracted x n_metrics 인 패널: {bad.tolist()}",
    )
    _require(
        int(out["n_source_rows"].sum()) == len(state.source_ranking_rows),
        "패널별 source row 합이 물리 source_ranking_rows 행수와 다르다",
    )
    return out.reset_index(drop=True)


def dim_panel_metric(state: StateFrames) -> pd.DataFrame:
    """보조 브리지 (panel x metric). A2 §5.1 지적 1의 ②안 — 선택 산출물(A2 §6.1).

    ``panel_registry.metric_columns``(JSON 배열)를 explode해 metric grain을 명시적으로 만든다.
    행수는 ``sum(n_metrics)``와 일치해야 한다.
    """
    rows: list[dict[str, object]] = []
    for record in state.panel_registry.itertuples(index=False):
        raw = record.metric_columns
        metrics = json.loads(raw) if isinstance(raw, str) else list(raw or [])
        for idx, metric in enumerate(metrics):
            rows.append(
                {
                    "panel_id": record.panel_id,
                    "metric_index": idx,
                    "metric_name": metric.get("name"),
                    "unit": metric.get("unit"),
                }
            )
    out = pd.DataFrame(rows, columns=["panel_id", "metric_index", "metric_name", "unit"])

    expected = int(state.panel_registry["n_metrics"].sum())
    _require(
        len(out) == expected,
        f"dim_panel_metric 행수 {len(out)} != sum(n_metrics) {expected}",
    )
    _require_unique(out, ["panel_id", "metric_index"], "dim_panel_metric")
    return out


def rank_anchor_metrics(state: StateFrames) -> pd.DataFrame:
    """panel x metric 별로 ``rank``가 그 metric의 값을 실제로 정렬하는가. **EDA-00 F-09 시정.**

    물리 ``rank``는 `(panel, entity)` 하나의 값인데 **모든 metric 행에 복제돼** 있다.
    패널마다 rank를 정하는 metric(anchor)은 하나뿐이고, 나머지 metric 행의 rank는
    그 metric에 대해서는 **정렬 의미가 없다.** 이 사실을 표로 드러내
    ``fact_source_ranking.rank_orders_this_metric``의 근거로 쓴다.

    판정은 EDA-00 §7과 같은 절차다 — `value` 결측을 뺀 뒤 rank 오름차순으로 정렬해
    값이 단조감소하면 ``DESC``(anchor), 단조증가면 ``ASC``, 아니면 ``NON_MONOTONE``,
    비교할 값이 2개 미만이면 ``UNDETERMINED``.
    """
    records: list[dict[str, object]] = []
    for panel_id, group in state.source_ranking_rows.groupby("panel_id"):
        for metric_name, sub in group.groupby("metric_name"):
            values = sub.dropna(subset=["value"]).sort_values("rank")["value"].tolist()
            if len(values) < 2:
                kind = "UNDETERMINED"
            elif all(values[i] >= values[i + 1] for i in range(len(values) - 1)):
                kind = "DESC"
            elif all(values[i] <= values[i + 1] for i in range(len(values) - 1)):
                kind = "ASC"
            else:
                kind = "NON_MONOTONE"
            records.append(
                {
                    "panel_id": panel_id,
                    "metric_name": metric_name,
                    "rank_monotonicity": kind,
                    "is_rank_anchor": kind == "DESC",
                }
            )
    out = pd.DataFrame(
        records, columns=["panel_id", "metric_name", "rank_monotonicity", "is_rank_anchor"]
    )
    _require_unique(out, ["panel_id", "metric_name"], "rank_anchor_metrics")

    anchors = out.groupby("panel_id")["is_rank_anchor"].sum()
    missing = anchors[anchors == 0].index.tolist()
    _require(
        not missing,
        f"rank를 정렬하는 anchor metric이 없는 패널: {missing} — `rank`의 의미가 불명이다",
    )
    return out


def fact_source_ranking(state: StateFrames) -> pd.DataFrame:
    """논리 ``fact_source_ranking`` (source row 261행). A2 §5.2.

    ``measurement_entity_id``는 물리에 없으므로 §5.2.1 조인으로 유도한다.
    ``entity_name_raw``는 계보 추적·ID collision 검사 근거이므로 **유지**한다(A2 §5.2).
    ``raw_label``/``raw_value`` 결측 7행은 0으로 치환하지 않는다.
    """
    merged = _joined_source_rows(state)
    out = merged.rename(
        columns={
            "value_label": "raw_label",
            "value": "raw_value",
            "unit": "raw_unit",
        }
    )[
        [
            "source_row_id",
            "panel_id",
            "measurement_entity_id",
            "rank",
            "raw_label",
            "raw_value",
            "raw_unit",
            # 논리표에 자리가 없으나 A2 §5.2가 유지를 요구한 컬럼.
            "entity_name_raw",
            # ①안 결과: 스칼라 metric은 source row 수준에 산다.
            "metric_name",
        ]
    ].copy()

    # EDA-00 F-09 시정 — `rank`는 (panel, entity) 값이 모든 metric 행에 복제된 것이다.
    # 그 행의 metric에 대해 rank가 정렬 의미를 갖는지 여기서 명시한다.
    # 이 컬럼 없이 `ORDER BY rank`를 metric별로 걸면 anchor가 아닌 metric에서 조용히 틀린다.
    anchors = rank_anchor_metrics(state)
    out = out.merge(
        anchors.rename(columns={"is_rank_anchor": "rank_orders_this_metric"})[
            ["panel_id", "metric_name", "rank_orders_this_metric"]
        ],
        on=["panel_id", "metric_name"],
        how="left",
        validate="many_to_one",
    )
    _require(
        int(out["rank_orders_this_metric"].isna().sum()) == 0,
        "rank_orders_this_metric 미매칭 — anchor 표가 전 (panel, metric)을 덮지 못했다",
    )

    n_physical = len(state.source_ranking_rows)
    _require(
        len(out) == n_physical,
        f"fact_source_ranking 행수 {len(out)} != source_ranking_rows {n_physical}",
    )
    _require_unique(out, ["source_row_id"], "fact_source_ranking")
    _require(
        int(out["measurement_entity_id"].isna().sum()) == 0,
        "fact_source_ranking: measurement_entity_id 미매칭 존재",
    )
    # 결측 보존 — 물리 결측 수와 동일해야 한다(0 치환 금지, 01 §11).
    for logical, physical in (("raw_value", "value"), ("raw_label", "value_label")):
        got = int(out[logical].isna().sum())
        want = int(state.source_ranking_rows[physical].isna().sum())
        _require(got == want, f"{logical} 결측 {got} != 물리 {physical} 결측 {want}")
    return out.reset_index(drop=True)


def dim_measurement_entity(state: StateFrames) -> pd.DataFrame:
    """논리 ``dim_measurement_entity`` (entity 81행). A2 §5.3.

    키 이름이 다르다: 물리 ``service_id`` → 논리 ``measurement_entity_id``.
    ``canonical_name``(= ``service_name_canonical``)은 **유일키가 아니다**(81행/80고유, '쿠팡').
    조인은 반드시 id 또는 ``canonical_service_key``로 한다(A2 §5.3 지적 2).
    ``review_status``는 §1.1 결정식으로 유도한다.
    """
    src = state.service_master
    review_status = src["review_decision"].where(
        src["review_decision"].notna(),
        src["needs_human_review"].map(
            lambda flag: "PENDING_HUMAN_REVIEW" if bool(flag) else "NOT_IN_REVIEW_QUEUE"
        ),
    )

    out = pd.DataFrame(
        {
            "measurement_entity_id": src["service_id"],
            "canonical_name": src["service_name_canonical"],
            # 사실상의 자연키. 논리표에 자리가 없으나 A2 §5.3이 유지를 요구한다.
            "canonical_service_key": src["canonical_service_key"],
            "source_domain": src["domain"],
            "entity_type": src["axis_type"],
            "review_status": review_status,
            # EDA-00 F-10 시정 — 81 entity는 **동질집단이 아니다.** 브랜드 71 + 업종 카테고리 10이며
            # 업종은 측정 대상 웹 서비스가 아니다. 분모를 81로 잡으면 매핑률이 조용히 틀린다.
            "is_web_mappable_entity": src["axis_type"].eq("SERVICE_BRAND"),
        }
    )

    _require(
        len(out) == len(src), f"dim_measurement_entity 행수 {len(out)} != service_master {len(src)}"
    )
    _require_unique(out, ["measurement_entity_id"], "dim_measurement_entity")
    _require_unique(out, ["canonical_service_key"], "dim_measurement_entity canonical_service_key")
    unknown = set(out["review_status"].dropna().unique()) - _REVIEW_STATUS_DOMAIN
    _require(not unknown, f"review_status 미등재 값: {sorted(unknown)}")
    _require(
        int(out["review_status"].isna().sum()) == 0,
        "review_status 결측 — 유도식이 전 행을 덮지 못했다",
    )
    _require(
        set(out["entity_type"].unique()) <= {"SERVICE_BRAND", "INDUSTRY_CATEGORY"},
        f"entity_type 미등재 값: {sorted(set(out['entity_type'].unique()))}",
    )
    # EDA-00 F-10 — 업종 카테고리는 web target을 갖지 않는다. 이 대응이 깨지면
    # `is_web_mappable_entity`가 근거를 잃으므로 물리와 상시 대조한다.
    industry = ~out["is_web_mappable_entity"]
    _require(
        bool(src.loc[industry.to_numpy(), "web_target_group_id"].isna().all()),
        "INDUSTRY_CATEGORY 인데 web_target_group_id가 있다 — F-10 전제가 깨졌다",
    )
    _require(
        int(src.loc[~industry.to_numpy(), "web_target_group_id"].isna().sum()) == 0,
        "SERVICE_BRAND 인데 web_target_group_id가 없다 — F-10 전제가 깨졌다",
    )
    return out.reset_index(drop=True)


def bridge_source_membership(state: StateFrames) -> pd.DataFrame:
    """논리 ``bridge_source_membership`` (**source row 261행**). A2 §5.4.

    물리 ``source_membership``(142행)은 이 표가 아니라 그 **집계 뷰**다.
    여기서는 §5.2.1 조인 결과의 투영으로 261행 bridge를 만들고,
    distinct ``(measurement_entity_id, panel_id)``가 물리 142행과 **집합 동일**임을
    회귀검사(규칙 V-6)로 상시 확인한다.
    """
    merged = _joined_source_rows(state)
    out = merged[["measurement_entity_id", "panel_id", "source_row_id"]].copy()

    n_physical_rows = len(state.source_ranking_rows)
    _require(
        len(out) == n_physical_rows,
        f"bridge_source_membership 행수 {len(out)} != source row {n_physical_rows}",
    )
    _require_unique(out, ["source_row_id"], "bridge_source_membership")

    derived = set(
        map(tuple, out[["measurement_entity_id", "panel_id"]].drop_duplicates().to_numpy())
    )
    stored = set(
        map(tuple, state.source_membership[["service_id", "panel_id"]].drop_duplicates().to_numpy())
    )
    _require(
        len(stored) == len(state.source_membership),
        "물리 source_membership에 (service_id, panel_id) 중복이 있다",
    )
    _require(
        len(derived) == len(stored),
        f"distinct (entity, panel) {len(derived)} != source_membership {len(stored)}",
    )
    _require(
        derived == stored,
        "유도 bridge와 물리 source_membership이 집합 동일하지 않다 "
        f"(유도만 {len(derived - stored)}쌍 / 물리만 {len(stored - derived)}쌍)",
    )

    # 교차검증(A2 §5.2.1) — 물리 rank == 유도 min(rank).
    min_rank = (
        merged.groupby(["measurement_entity_id", "panel_id"], as_index=False)["rank"]
        .min()
        .rename(columns={"measurement_entity_id": "service_id", "rank": "rank_derived"})
    )
    check = state.source_membership.merge(min_rank, on=["service_id", "panel_id"], how="left")
    mismatch = int((check["rank"] != check["rank_derived"]).sum())
    _require(mismatch == 0, f"source_membership.rank != 유도 min(rank) {mismatch}행")

    # EDA-00 F-08 — 물리 142행이 **metric 축을 잃는다**는 것이 이 집계 뷰의 성질이다.
    # 한 쌍이 여러 metric에 걸치는 경우가 실제로 존재해야 그 성질이 성립하며,
    # 그때 물리 `rank`는 min(rank)라는 **선택된 요약**이지 원값이 아니다(F-09와 연결).
    per_pair_metrics = merged.groupby(["measurement_entity_id", "panel_id"])[
        "metric_name"
    ].nunique()
    _require(
        int((per_pair_metrics > 1).sum()) > 0,
        "다중 metric (entity, panel) 쌍이 0개다 — 142 집계 뷰의 metric 축 상실 전제가 깨졌다",
    )
    return out.reset_index(drop=True)


def materialize_all(
    out_dir: Path | str,
    state_dir: Path | str = DEFAULT_STATE_DIR,
    *,
    include_panel_metric: bool = True,
) -> dict[str, Path]:
    """논리표를 parquet으로 떨군다(부수 기능). 기본 사용은 in-memory view다.

    규칙 V-4/V-5 — 원본과 **다른 디렉터리**에만 쓴다. ``out_dir``이 state 원본이면 거부한다.
    """
    target = Path(out_dir).resolve()
    source = Path(state_dir).resolve()
    _require(target != source, f"산출 디렉터리가 원본과 같다: {target}")
    target.mkdir(parents=True, exist_ok=True)

    state = load_state(state_dir)
    tables: dict[str, pd.DataFrame] = {
        "dim_panel": dim_panel(state),
        "fact_source_ranking": fact_source_ranking(state),
        "dim_measurement_entity": dim_measurement_entity(state),
        "bridge_source_membership": bridge_source_membership(state),
    }
    if include_panel_metric:
        tables["dim_panel_metric"] = dim_panel_metric(state)
        tables["rank_anchor_metrics"] = rank_anchor_metrics(state)

    written: dict[str, Path] = {}
    for name, frame in tables.items():
        path = target / f"{name}.parquet"
        frame.to_parquet(path, index=False)
        written[name] = path
    return written
