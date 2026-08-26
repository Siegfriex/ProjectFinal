"""목표 3 검증 — `research/landing_accessibility/analysis/deliverables`.

6종 산출물(ANALYSIS_DATA_DICTIONARY.md · EDA_REPORT.md · STATISTICAL_RESULTS.md ·
ROBUSTNESS_RESULTS.md · MODEL_DIAGNOSTICS.md · DECISION_INPUT_TABLE.parquet/csv)이
전부 생성되고, `DECISION_INPUT_TABLE`에 요구된 8필드
(metric/effect/sample_n/missing_n/undetermined_n/assumption/robustness_check/
source_artifact_sha)가 실제로 존재하는지 확인한다.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import pytest

_ANALYSIS_ROOT = Path(__file__).resolve().parents[1] / "research" / "landing_accessibility"
if str(_ANALYSIS_ROOT) not in sys.path:
    sys.path.insert(0, str(_ANALYSIS_ROOT))

from analysis.deliverables import (  # noqa: E402
    build_decision_input_table,
    generate_data_dictionary,
    generate_eda_report,
    generate_model_diagnostics,
    generate_robustness_results,
    generate_statistical_results,
    write_decision_input_table,
)
from analysis.deliverables.claim_table import COLUMNS  # noqa: E402
from analysis.eda import RUNNERS  # noqa: E402
from analysis.marts.builders import BUILDERS  # noqa: E402
from analysis.marts.synthetic import generate_synthetic_universe  # noqa: E402
from analysis.provenance import file_sha256  # noqa: E402

REQUIRED_CLAIM_FIELDS = {
    "metric",
    "effect",
    "sample_n",
    "missing_n",
    "undetermined_n",
    "assumption",
    "robustness_check",
    "source_artifact_sha",
}


@pytest.fixture(scope="module")
def eda_bundle(tmp_path_factory: pytest.TempPathFactory):
    out = tmp_path_factory.mktemp("eda_bundle")
    rows_by_table = generate_synthetic_universe(n_services=24, seed=3).as_dict()
    marts = {table: BUILDERS[table](rows).frame for table, rows in rows_by_table.items()}

    summaries, md_paths, shas = {}, {}, {}
    for key, runner in RUNNERS.items():
        paths = runner(marts, out / key)
        import json

        summaries[key] = json.loads(paths.summary_json_path.read_text())
        md_paths[key] = paths.markdown_path
        shas[key] = file_sha256(paths.summary_json_path)
    return {"marts": marts, "summaries": summaries, "md_paths": md_paths, "shas": shas}


def test_required_claim_fields_present() -> None:
    assert set(COLUMNS) >= REQUIRED_CLAIM_FIELDS


def test_decision_input_table_has_rows_and_required_fields(eda_bundle) -> None:
    frame = build_decision_input_table(eda_bundle["summaries"], eda_bundle["shas"])
    assert not frame.empty
    for field in REQUIRED_CLAIM_FIELDS:
        assert field in frame.columns
    assert frame["source_artifact_sha"].apply(lambda v: isinstance(v, str) and len(v) == 64).all()


def test_decision_input_table_writes_csv_and_parquet(tmp_path: Path, eda_bundle) -> None:
    frame = build_decision_input_table(eda_bundle["summaries"], eda_bundle["shas"])
    paths = write_decision_input_table(frame, tmp_path)
    assert paths["csv"].exists()
    assert paths["parquet"].exists()
    read_back = pd.read_parquet(paths["parquet"])
    assert len(read_back) == len(frame)


def test_decision_input_table_empty_summaries_still_produces_named_claims(tmp_path: Path) -> None:
    """빈 입력에서도 claim 행 자체는 생성되고, N=0 등이 명시적으로 채워져야 한다."""
    empty_summaries = {k: {} for k in RUNNERS}
    empty_shas = dict.fromkeys(RUNNERS, "")
    frame = build_decision_input_table(empty_summaries, empty_shas)
    assert not frame.empty  # claim_id들은 항상 생성된다 — 값이 채워지지 않을 뿐
    paths = write_decision_input_table(frame, tmp_path)
    assert paths["csv"].exists()
    assert paths["parquet"].exists()


def test_all_five_markdown_templates_generate(tmp_path: Path, eda_bundle) -> None:
    frame = build_decision_input_table(eda_bundle["summaries"], eda_bundle["shas"])
    dd = generate_data_dictionary(tmp_path)
    report = generate_eda_report(eda_bundle["summaries"], eda_bundle["md_paths"], tmp_path)
    stats = generate_statistical_results(frame, tmp_path)
    robust = generate_robustness_results(eda_bundle["summaries"].get("eda08", {}), tmp_path)
    diag = generate_model_diagnostics(eda_bundle["marts"], tmp_path)

    for path, name in (
        (dd, "ANALYSIS_DATA_DICTIONARY.md"),
        (report, "EDA_REPORT.md"),
        (stats, "STATISTICAL_RESULTS.md"),
        (robust, "ROBUSTNESS_RESULTS.md"),
        (diag, "MODEL_DIAGNOSTICS.md"),
    ):
        assert path.exists()
        assert path.name == name
        text = path.read_text()
        assert len(text) > 0
        assert "synthetic" in text or "SHADOW" in text


def test_data_dictionary_documents_all_seven_tables(tmp_path: Path) -> None:
    from analysis.marts.schema import TABLE_SCHEMAS

    path = generate_data_dictionary(tmp_path)
    text = path.read_text()
    for table in TABLE_SCHEMAS:
        assert f"`{table}`" in text


def test_model_diagnostics_reports_human_budget(tmp_path: Path, eda_bundle) -> None:
    """A2 §4.6 `HUMAN_FINAL_REVIEW_MAX=5` — 진단 문서가 예산 준수 여부를 언급해야 한다."""
    path = generate_model_diagnostics(eda_bundle["marts"], tmp_path)
    text = path.read_text()
    assert "HUMAN_FINAL_REVIEW_MAX" in text


def test_markdown_outputs_carry_interpretation_discipline_notice(
    tmp_path: Path, eda_bundle
) -> None:
    from analysis.provenance import INTERPRETATION_DISCIPLINE_NOTICE

    dd = generate_data_dictionary(tmp_path)
    assert INTERPRETATION_DISCIPLINE_NOTICE in dd.read_text()
