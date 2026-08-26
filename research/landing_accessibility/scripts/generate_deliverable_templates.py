#!/usr/bin/env python3
"""산출물 템플릿 생성 CLI — 목표 3, end-to-end.

marts 빌드 → EDA-03~08 실행 → `DECISION_INPUT_TABLE` → 5개 Markdown 산출물.
전부 synthetic 데이터로 실행된다. `--empty`로 빈 입력 경로도 확인할 수 있다.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # research/landing_accessibility

from analysis.deliverables import (
    build_decision_input_table,
    generate_data_dictionary,
    generate_eda_report,
    generate_model_diagnostics,
    generate_robustness_results,
    generate_statistical_results,
    write_decision_input_table,
)
from analysis.eda import RUNNERS
from analysis.marts.builders import BUILDERS
from analysis.marts.synthetic import generate_synthetic_universe
from analysis.provenance import ShadowProvenance, file_sha256


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", default="artifacts/analysis_skeleton/deliverables")
    parser.add_argument("--n-services", type=int, default=24)
    parser.add_argument("--empty", action="store_true")
    args = parser.parse_args()

    out_dir = Path(args.out_dir)
    provenance = ShadowProvenance(source_kind="EMPTY" if args.empty else "SYNTHETIC")

    if args.empty:
        rows_by_table = {name: [] for name in BUILDERS}
    else:
        rows_by_table = generate_synthetic_universe(n_services=args.n_services).as_dict()
    marts = {table: BUILDERS[table](rows).frame for table, rows in rows_by_table.items()}

    eda_summaries: dict[str, dict] = {}
    eda_markdown_paths: dict[str, Path] = {}
    source_shas: dict[str, str] = {}
    for key, runner in RUNNERS.items():
        eda_out = out_dir / "eda" / key
        paths = runner(marts, eda_out, provenance=provenance)
        eda_summaries[key] = json.loads(paths.summary_json_path.read_text())
        eda_markdown_paths[key] = paths.markdown_path
        source_shas[key] = file_sha256(paths.summary_json_path)

    claim_table = build_decision_input_table(eda_summaries, source_shas)
    table_paths = write_decision_input_table(claim_table, out_dir, provenance=provenance)

    dd_path = generate_data_dictionary(out_dir, provenance=provenance)
    report_path = generate_eda_report(
        eda_summaries, eda_markdown_paths, out_dir, provenance=provenance
    )
    stats_path = generate_statistical_results(claim_table, out_dir, provenance=provenance)
    robust_path = generate_robustness_results(
        eda_summaries.get("eda08", {}), out_dir, provenance=provenance
    )
    diag_path = generate_model_diagnostics(marts, out_dir, provenance=provenance)

    for p in (
        table_paths["csv"],
        table_paths["parquet"],
        dd_path,
        report_path,
        stats_path,
        robust_path,
        diag_path,
    ):
        print(f"wrote {p}")


if __name__ == "__main__":
    main()
