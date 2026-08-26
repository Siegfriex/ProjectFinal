"""목표 3 — 산출물 템플릿 생성기.

`ANALYSIS_DATA_DICTIONARY.md` · `EDA_REPORT.md` · `STATISTICAL_RESULTS.md` ·
`ROBUSTNESS_RESULTS.md` · `MODEL_DIAGNOSTICS.md` · `DECISION_INPUT_TABLE.parquet/csv`.
"""

from .claim_table import ClaimRecord, build_decision_input_table, write_decision_input_table
from .markdown_templates import (
    generate_data_dictionary,
    generate_eda_report,
    generate_model_diagnostics,
    generate_robustness_results,
    generate_statistical_results,
)

__all__ = [
    "ClaimRecord",
    "build_decision_input_table",
    "generate_data_dictionary",
    "generate_eda_report",
    "generate_model_diagnostics",
    "generate_robustness_results",
    "generate_statistical_results",
    "write_decision_input_table",
]
