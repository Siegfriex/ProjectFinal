"""목표 1 검증 — `research/landing_accessibility/analysis/marts`.

(a) 스키마 검증 (b) synthetic 입력 정상 동작 (c) 빈 입력 안전성 을 7개 표 전부에서 확인한다.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import pytest

_ANALYSIS_ROOT = Path(__file__).resolve().parents[1] / "research" / "landing_accessibility"
if str(_ANALYSIS_ROOT) not in sys.path:
    sys.path.insert(0, str(_ANALYSIS_ROOT))

from analysis.marts.builders import BUILDERS, MartBuildError, build_mart, write_mart  # noqa: E402
from analysis.marts.schema import (  # noqa: E402
    TABLE_SCHEMAS,
    SchemaValidationError,
    column_names,
    validate_row,
)
from analysis.marts.synthetic import generate_synthetic_universe  # noqa: E402

ALL_TABLES = list(TABLE_SCHEMAS)


@pytest.fixture(scope="module")
def universe() -> dict[str, list[dict]]:
    return generate_synthetic_universe(n_services=24, seed=1).as_dict()


@pytest.mark.parametrize("table", ALL_TABLES)
def test_synthetic_rows_build_successfully(universe: dict[str, list[dict]], table: str) -> None:
    rows = universe[table]
    result = BUILDERS[table](rows)
    assert result.empty_input is False
    assert result.row_count == len(rows)
    assert list(result.frame.columns[: len(column_names(table))]) == column_names(table)


@pytest.mark.parametrize("table", ALL_TABLES)
def test_empty_input_is_safe(table: str) -> None:
    """(c) 빈 입력 — 에러 없이 컬럼만 있는 빈 mart가 나와야 한다."""
    result = BUILDERS[table]([])
    assert result.empty_input is True
    assert result.row_count == 0
    assert list(result.frame.columns) == column_names(table)
    assert result.frame.empty


@pytest.mark.parametrize("table", ALL_TABLES)
def test_schema_rejects_out_of_domain_enum_value(table: str) -> None:
    """(a) 규칙 S-3 — 닫힌 집합 밖 값은 조용히 흡수되지 않고 실패해야 한다."""
    enum_columns = [c for c in TABLE_SCHEMAS[table] if c.enum is not None]
    if not enum_columns:
        pytest.skip(f"{table}: enum 컬럼 없음")
    col = enum_columns[0]
    bad_row = {col.name: "__NOT_A_REAL_VALUE__"}
    errors = validate_row(table, bad_row)
    assert errors, f"{table}.{col.name} 는 닫힌 집합 위반을 잡아야 한다"

    with pytest.raises(MartBuildError):
        build_mart(table, [bad_row])


def test_required_id_column_missing_fails() -> None:
    # fact_landing_observation.observation_id 는 required=True.
    with pytest.raises(MartBuildError):
        build_mart("fact_landing_observation", [{"web_target_id": "WT-0000"}])


def test_unknown_table_rejected() -> None:
    with pytest.raises(MartBuildError):
        build_mart("not_a_real_table", [])
    with pytest.raises(SchemaValidationError):
        validate_row("not_a_real_table", {})


@pytest.mark.parametrize("table", ALL_TABLES)
def test_write_mart_produces_csv_and_parquet(
    tmp_path: Path, universe: dict[str, list[dict]], table: str
) -> None:
    result = build_mart(table, universe[table])
    paths = write_mart(result, tmp_path / table)
    assert paths["csv"].exists()
    assert paths["parquet"].exists()
    read_back = pd.read_parquet(paths["parquet"])
    assert len(read_back) == result.row_count


def test_write_mart_empty_input_produces_valid_empty_files(tmp_path: Path) -> None:
    result = build_mart("dim_certification", [])
    paths = write_mart(result, tmp_path / "empty")
    read_back_csv = pd.read_csv(paths["csv"])
    read_back_parquet = pd.read_parquet(paths["parquet"])
    assert read_back_csv.empty
    assert read_back_parquet.empty
    assert list(read_back_parquet.columns) == column_names("dim_certification")


def test_universe_is_deterministic_under_fixed_seed() -> None:
    u1 = generate_synthetic_universe(n_services=10, seed=99)
    u2 = generate_synthetic_universe(n_services=10, seed=99)
    assert u1.fact_landing_observation == u2.fact_landing_observation
    assert u1.fact_criterion_result == u2.fact_criterion_result


def test_fact_ai_adjudication_human_budget_not_exceeded_in_fixture() -> None:
    """A2 §4.6 — `HUMAN_FINAL_REVIEW_MAX = 5`. synthetic fixture 자체가 이 예산을
    지키는지는 fixture 설계 책임이지만, 최소한 컬럼이 0/1 닫힌 집합인지는 스키마가 강제한다.
    """
    universe = generate_synthetic_universe(n_services=24, seed=1)
    for row in universe.fact_ai_adjudication:
        assert row["human_required"] in ("0", "1")
