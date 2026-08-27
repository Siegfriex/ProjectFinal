"""EDA-04 — Popup / Obstruction (`03_CRISP_DM_EXECUTION_PLAN_v2.0.md` Phase 5, M2).

`fact_interrupt_element`를 소비해 방해요소 라벨 유병률, primary action 폐색률,
overlay coverage 분포, dismiss 성공률을 낸다. **synthetic 데이터로만 검증됐다.**
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
    median_iqr,
    savefig,
    stamp_all,
    write_markdown_note,
    write_summary_json,
    write_table,
)

NAME = "eda04_popup_obstruction"


def run_eda04(
    marts: dict[str, pd.DataFrame],
    out_dir: str | Path,
    *,
    provenance: ShadowProvenance | None = None,
) -> EDAOutputPaths:
    provenance = provenance or ShadowProvenance()
    interrupt = marts.get("fact_interrupt_element", pd.DataFrame())
    summary: dict[str, Any]

    if interrupt.empty:
        label_counts = pd.DataFrame(columns=["final_label", "n"])
        summary = {"n_interrupts": 0, "n_observations_with_interrupt": 0}
    else:
        label_counts = (
            interrupt["final_label"]
            .value_counts(dropna=False)
            .rename_axis("final_label")
            .reset_index(name="n")
        )
        blocks = interrupt["blocks_primary_action"].astype(str)
        dismiss_exists = interrupt["dismiss_control_exists"].astype(str) == "1"
        dismiss_ok = interrupt["dismiss_succeeded"].astype(str) == "1"
        summary = {
            "n_interrupts": len(interrupt),
            "n_observations_with_interrupt": int(interrupt["observation_id"].nunique()),
            "blocks_primary_action_rate": round(float((blocks == "1").mean()), 4),
            "overlay_coverage": median_iqr(interrupt["overlay_coverage"]),
            "primary_action_occlusion": median_iqr(interrupt["primary_action_occlusion"]),
            "dismiss_success_rate_given_control_exists": (
                round(float(dismiss_ok[dismiss_exists].mean()), 4) if dismiss_exists.any() else None
            ),
            "classification_status_distribution": interrupt["classification_status"]
            .value_counts(dropna=False)
            .to_dict(),
        }

    csv_path, parquet_path = write_table(label_counts, out_dir, NAME)
    summary_path = write_summary_json(summary, out_dir, NAME)

    fig, axes = plt.subplots(1, 2, figsize=(10, 4.5))
    if not interrupt.empty:
        label_counts.set_index("final_label")["n"].plot(kind="bar", ax=axes[0])
        axes[0].set_title("final_label 유병률")
        axes[0].set_ylabel("interrupt count")
        interrupt["overlay_coverage"].astype(float).dropna().plot(kind="hist", bins=10, ax=axes[1])
        axes[1].set_title("overlay_coverage 분포")
    else:
        for ax in axes:
            ax.text(0.5, 0.5, "빈 입력", ha="center", va="center")
            ax.set_axis_off()
    fig_path = savefig(fig, out_dir, NAME)

    body = [
        f"- interrupt 행 수: {summary['n_interrupts']}",
        f"- primary action 폐색 비율(blocks_primary_action=1): {summary.get('blocks_primary_action_rate')}",
        f"- overlay_coverage median/IQR: {summary.get('overlay_coverage')}",
        f"- dismiss 성공률(닫기 컨트롤이 있는 경우만): {summary.get('dismiss_success_rate_given_control_exists')}",
        "- `classification_status=AMBIGUOUS`인 행은 `final_label`이 NULL일 수 있다 — AI review 미해결.",
    ]
    md_path = write_markdown_note(
        "EDA-04 — Popup / Obstruction", body, out_dir, NAME, provenance=provenance
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
    parser.add_argument("--out-dir", default="artifacts/analysis_current/eda/eda04")
    parser.add_argument("--n-services", type=int, default=24)
    args = parser.parse_args()

    universe = generate_synthetic_universe(n_services=args.n_services).as_dict()
    marts = {name: pd.DataFrame(rows) for name, rows in universe.items()}
    paths = run_eda04(marts, args.out_dir)
    print(f"EDA-04 done → {paths.summary_json_path}")


if __name__ == "__main__":
    _main()
