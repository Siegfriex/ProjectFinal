#!/usr/bin/env python3
"""산출물 템플릿 생성 CLI — 목표 3, end-to-end.

marts 빌드 → EDA-03~09 실행 → `DECISION_INPUT_TABLE` → Markdown/JSON 산출물
전부(`FROZEN_MART_MANIFEST.json` · `COLLECTION_COVERAGE.json` ·
`STATISTICAL_RESULTS.json` · `EDA_REPORT.md` · `ROBUSTNESS_RESULTS.md` ·
`LIMITATIONS.md` · `ANALYSIS_HANDOFF.json` + 부가 문서). 전부 synthetic
데이터로 실행된다. `--empty`로 빈 입력 경로도 확인할 수 있다.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # research/landing_accessibility

from analysis.deliverables import (
    build_analysis_handoff,
    build_collection_coverage,
    build_decision_input_table,
    build_frozen_mart_manifest,
    build_statistical_results_json,
    generate_data_dictionary,
    generate_eda_report,
    generate_final_results_summary,
    generate_limitations,
    generate_model_diagnostics,
    generate_robustness_results,
    generate_statistical_results,
    write_decision_input_table,
)
from analysis.eda import RUNNERS
from analysis.marts.builders import BUILDERS, write_mart
from analysis.marts.synthetic import generate_synthetic_universe
from analysis.older_relevance_registry import ensure_frozen
from analysis.provenance import ShadowProvenance, file_sha256


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", default="artifacts/analysis_current/deliverables")
    parser.add_argument("--n-services", type=int, default=24)
    parser.add_argument("--empty", action="store_true")
    parser.add_argument("--branch", default="claude-b/analysis-current")
    parser.add_argument("--base-sha", default="397a10d")
    parser.add_argument("--commit-sha", default=None)
    args = parser.parse_args()

    out_dir = Path(args.out_dir)
    # 정본 older_relevance 표를 로드해 둔다 — 산출물이 동결 상태(SHA·집계)를
    # 기록하고, 픽스처가 정본과 어긋나면 드리프트 검사가 잡아낼 수 있게 한다.
    ensure_frozen()
    provenance = ShadowProvenance(source_kind="EMPTY" if args.empty else "SYNTHETIC")

    if args.empty:
        rows_by_table = {name: [] for name in BUILDERS}
    else:
        rows_by_table = generate_synthetic_universe(n_services=args.n_services).as_dict()
    mart_results = {table: BUILDERS[table](rows) for table, rows in rows_by_table.items()}
    marts = {table: result.frame for table, result in mart_results.items()}
    mart_out_dir = out_dir / "marts"
    mart_paths = {table: write_mart(result, mart_out_dir) for table, result in mart_results.items()}

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
    stats_md_path = generate_statistical_results(claim_table, out_dir, provenance=provenance)
    robust_path = generate_robustness_results(
        eda_summaries.get("eda08", {}), out_dir, provenance=provenance
    )
    diag_path = generate_model_diagnostics(marts, out_dir, provenance=provenance)
    final_summary_path = generate_final_results_summary(
        eda_summaries.get("eda05", {}),
        eda_summaries.get("eda07", {}),
        eda_summaries.get("eda09", {}),
        out_dir,
        provenance=provenance,
    )
    limitations_path = generate_limitations(
        eda_summaries.get("eda05", {}),
        eda_summaries.get("eda07", {}),
        out_dir,
        eda09_summary=eda_summaries.get("eda09", {}),
        provenance=provenance,
    )

    # 목표 3 — 6개 확정 산출물.
    frozen_manifest = build_frozen_mart_manifest(mart_results, mart_paths, provenance=provenance)
    frozen_manifest_path = out_dir / "FROZEN_MART_MANIFEST.json"
    frozen_manifest_path.parent.mkdir(parents=True, exist_ok=True)
    frozen_manifest_path.write_text(
        json.dumps(frozen_manifest, ensure_ascii=False, indent=2, default=str), encoding="utf-8"
    )

    coverage = build_collection_coverage(marts, provenance=provenance)
    coverage_path = out_dir / "COLLECTION_COVERAGE.json"
    coverage_path.write_text(
        json.dumps(coverage, ensure_ascii=False, indent=2, default=str), encoding="utf-8"
    )

    stats_json = build_statistical_results_json(eda_summaries, provenance=provenance)
    stats_json_path = out_dir / "STATISTICAL_RESULTS.json"
    stats_json_path.write_text(
        json.dumps(stats_json, ensure_ascii=False, indent=2, default=str), encoding="utf-8"
    )

    handoff = build_analysis_handoff(
        branch=args.branch,
        commit_sha=args.commit_sha,
        base_sha=args.base_sha,
        artifact_paths={
            "FROZEN_MART_MANIFEST.json": frozen_manifest_path,
            "COLLECTION_COVERAGE.json": coverage_path,
            "STATISTICAL_RESULTS.json": stats_json_path,
            "EDA_REPORT.md": report_path,
            "ROBUSTNESS_RESULTS.md": robust_path,
            "LIMITATIONS.md": limitations_path,
            "FINAL_RESULTS_SUMMARY.md": final_summary_path,
            "DECISION_INPUT_TABLE.csv": table_paths["csv"],
        },
        adjudication_schema_bound=True,
        open_issues=[
            "REAL_TARGET_MEASUREMENT=false — 전부 synthetic/fixture. 실제 E001 데이터 도착 시 "
            "이 파이프라인을 그대로 재실행해야 한다(스키마/함수 시그니처는 이미 실제 데이터를 받도록 짜여 있다).",
            "E000_FAST(6개 타깃) 범위 — PHASE_GATES.md의 E000_V2_VALIDATED(8~12타깃+두 독립감사)는 "
            "이 산출물로 충족되지 않는다.",
        ],
        provenance=provenance,
    )
    handoff_path = out_dir / "ANALYSIS_HANDOFF.json"
    handoff_path.write_text(
        json.dumps(handoff, ensure_ascii=False, indent=2, default=str), encoding="utf-8"
    )

    for p in (
        table_paths["csv"],
        table_paths["parquet"],
        dd_path,
        report_path,
        stats_md_path,
        robust_path,
        diag_path,
        limitations_path,
        final_summary_path,
        frozen_manifest_path,
        coverage_path,
        stats_json_path,
        handoff_path,
    ):
        print(f"wrote {p}")


if __name__ == "__main__":
    main()
