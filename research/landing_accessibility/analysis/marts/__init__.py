"""목표 1 — fact/dim mart 스키마 + 빌드 스크립트.

7개 표: `fact_landing_observation` · `fact_task_entry` · `fact_task_step` ·
`fact_interrupt_element` · `fact_criterion_result` · `fact_ai_adjudication` ·
`dim_certification`. 컬럼 출처는 `01_DATA_SPEC_v2.0.md` §4~§9, 허용값 도메인은
`A2_VOCABULARY_AND_SCHEMA_BINDING.md` §1.
"""

from .adjudication_binding import adjudication_record_to_mart_row, assert_schema_bound
from .builders import (
    BUILDERS,
    MartBuildError,
    MartBuildResult,
    build_dim_certification,
    build_fact_ai_adjudication,
    build_fact_criterion_result,
    build_fact_interrupt_element,
    build_fact_landing_observation,
    build_fact_task_entry,
    build_fact_task_step,
    build_mart,
    write_mart,
)
from .schema import TABLE_SCHEMAS, SchemaValidationError, column_names, validate_row, validate_rows
from .synthetic import SyntheticUniverse, generate_synthetic_universe

__all__ = [
    "BUILDERS",
    "TABLE_SCHEMAS",
    "MartBuildError",
    "MartBuildResult",
    "SchemaValidationError",
    "SyntheticUniverse",
    "adjudication_record_to_mart_row",
    "assert_schema_bound",
    "build_dim_certification",
    "build_fact_ai_adjudication",
    "build_fact_criterion_result",
    "build_fact_interrupt_element",
    "build_fact_landing_observation",
    "build_fact_task_entry",
    "build_fact_task_step",
    "build_mart",
    "column_names",
    "generate_synthetic_universe",
    "validate_row",
    "validate_rows",
    "write_mart",
]
