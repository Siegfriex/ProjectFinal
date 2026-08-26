"""EDA-03 — Landing Accessibility (`03_CRISP_DM_EXECUTION_PLAN_v2.0.md` Phase 5).

`fact_criterion_result` + `fact_landing_observation`을 소비해 KWCAG 판정 분포와
측정품질(evidence completeness, decision coverage)을 낸다. **synthetic 데이터로만
검증됐다** — 실제 서비스 접근성 결과가 아니다.
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import pandas as pd

from ..provenance import ShadowProvenance
from .common import (
    EDAOutputPaths,
    decision_coverage,
    evidence_completeness,
    savefig,
    stamp_all,
    write_markdown_note,
    write_summary_json,
    write_table,
)

NAME = "eda03_landing_accessibility"


def run_eda03(
    marts: dict[str, pd.DataFrame],
    out_dir: str | Path,
    *,
    provenance: ShadowProvenance | None = None,
) -> EDAOutputPaths:
    provenance = provenance or ShadowProvenance()
    criterion = marts.get("fact_criterion_result", pd.DataFrame())
    landing = marts.get("fact_landing_observation", pd.DataFrame())
    summary: dict[str, Any]

    if criterion.empty:
        by_criterion = pd.DataFrame(
            columns=["criterion_id", "older_relevance", "PASS", "FAIL", "UNDETERMINED", "NA"]
        )
        summary = {
            "n_criterion_rows": 0,
            "evidence_completeness": evidence_completeness(
                landing.get("measurement_status", pd.Series(dtype=object))
            ),
            "decision_coverage_overall": decision_coverage(pd.Series(dtype=object)),
            "decision_coverage_by_older_relevance": {},
        }
    else:
        by_criterion = (
            criterion.groupby(["criterion_id", "older_relevance"], dropna=False)["verdict_state"]
            .value_counts()
            .unstack(fill_value=0)
            .reindex(columns=["PASS", "FAIL", "UNDETERMINED", "NA"], fill_value=0)
            .reset_index()
        )
        summary = {
            "n_criterion_rows": len(criterion),
            "evidence_completeness": evidence_completeness(
                landing.get("measurement_status", pd.Series(dtype=object))
            ),
            "decision_coverage_overall": decision_coverage(criterion["verdict_state"]),
            "decision_coverage_by_older_relevance": {
                str(rel): decision_coverage(group["verdict_state"])
                for rel, group in criterion.groupby("older_relevance", dropna=False)
            },
            "final_status_distribution": criterion["final_status"]
            .value_counts(dropna=False)
            .to_dict(),
        }

    csv_path, parquet_path = write_table(by_criterion, out_dir, NAME)
    summary_path = write_summary_json(summary, out_dir, NAME)

    fig, ax = plt.subplots(figsize=(8, 4.5))
    if not by_criterion.empty:
        plot_df = by_criterion.set_index("criterion_id")[["PASS", "FAIL", "UNDETERMINED", "NA"]]
        plot_df.plot(kind="bar", stacked=True, ax=ax)
        ax.set_ylabel("observation count")
        ax.set_title("EDA-03 · criterion_id별 verdict_state 분포 (synthetic)")
    else:
        ax.text(0.5, 0.5, "빈 입력 — 표시할 데이터 없음", ha="center", va="center")
        ax.set_axis_off()
    fig_path = savefig(fig, out_dir, NAME)

    coverage = summary.get("decision_coverage_overall", {})
    body = [
        f"- criterion 행 수: {summary['n_criterion_rows']}",
        f"- evidence completeness rate: {summary['evidence_completeness'].get('rate')}",
        f"- decision coverage (전체, PASS/FAIL 확정 비율): {coverage.get('rate')}"
        f" (denom={coverage.get('denominator_applicable')}, undetermined={coverage.get('undetermined')})",
        "- `NA`(적용기회 없음)는 decision coverage 분모에서 제외했다 (A2 §4.2).",
        "- `NOT_ELIGIBLE_AT_COLLECTION` 관측은 evidence completeness 분모·분자 모두에서 제외했다 (A2 §4.1 주의 3).",
    ]
    md_path = write_markdown_note(
        "EDA-03 — Landing Accessibility", body, out_dir, NAME, provenance=provenance
    )
    stamp_all(out_dir, NAME, provenance)

    return EDAOutputPaths(
        name=NAME,
        csv_path=csv_path,
        parquet_path=parquet_path,
        summary_json_path=summary_path,
        figure_paths=(fig_path,),
        markdown_path=md_path,
    )


def _main() -> None:
    from ..marts.synthetic import generate_synthetic_universe

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", default="artifacts/analysis_skeleton/eda/eda03")
    parser.add_argument("--n-services", type=int, default=24)
    args = parser.parse_args()

    universe = generate_synthetic_universe(n_services=args.n_services).as_dict()
    marts = {name: pd.DataFrame(rows) for name, rows in universe.items()}
    paths = run_eda03(marts, args.out_dir)
    print(f"EDA-03 done → {paths.summary_json_path}")


if __name__ == "__main__":
    _main()
