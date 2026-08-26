"""EDA-06 — Joint Profile (`03_CRISP_DM_EXECUTION_PLAN_v2.0.md` Phase 4 M4 / Phase 5).

서비스(`web_target_id`)별로 KWCAG decision coverage · MPFED · overlay/modal ·
auth gate · certification을 한 행으로 조인한다 (`mart_service_summary`의 축소판,
01_DATA_SPEC §10). 세 축(KWCAG / entry friction / certification)은 **단일
종합점수로 합치지 않는다** (`00 SSOT` 원칙) — 조인은 병기일 뿐 합산이 아니다.

부수로 MPFED ↔ overlay_coverage의 Spearman 상관(Phase 5 "통계" Association)을
예시로 계산한다. **synthetic 데이터로만 검증됐다** — 상관계수를 실제 서비스
주장으로 쓰지 않는다.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
from scipy import stats as scipy_stats

from ..provenance import ShadowProvenance
from .common import (
    EDAOutputPaths,
    auth_gate_observed,
    decision_coverage,
    savefig,
    stamp_all,
    write_markdown_note,
    write_summary_json,
    write_table,
)

NAME = "eda06_joint_profile"


def _build_joint_profile(marts: dict[str, pd.DataFrame]) -> pd.DataFrame:
    landing = marts.get("fact_landing_observation", pd.DataFrame())
    task = marts.get("fact_task_entry", pd.DataFrame()).copy()
    interrupt = marts.get("fact_interrupt_element", pd.DataFrame())
    criterion = marts.get("fact_criterion_result", pd.DataFrame())
    certification = marts.get("dim_certification", pd.DataFrame())

    if landing.empty:
        return pd.DataFrame(
            columns=[
                "web_target_id",
                "measurement_status",
                "decision_coverage_rate",
                "mpfed_max",
                "auth_gate_observed_any",
                "interrupt_count",
                "max_overlay_coverage",
                "certified_current",
            ]
        )

    obs_to_target = landing.set_index("observation_id")["web_target_id"]

    if not task.empty:
        task["auth_gate_observed"] = auth_gate_observed(task)
        task_agg = task.groupby("web_target_id").agg(
            mpfed_max=("MPFED", "max"), auth_gate_observed_any=("auth_gate_observed", "any")
        )
    else:
        task_agg = pd.DataFrame(columns=["mpfed_max", "auth_gate_observed_any"])

    if not interrupt.empty:
        interrupt = interrupt.copy()
        interrupt["web_target_id"] = interrupt["observation_id"].map(obs_to_target)
        interrupt_agg = interrupt.groupby("web_target_id").size().rename("interrupt_count")
    else:
        interrupt_agg = pd.Series(dtype=int, name="interrupt_count")

    if not criterion.empty:
        criterion = criterion.copy()
        criterion["web_target_id"] = criterion["observation_id"].map(obs_to_target)
        coverage_by_target = criterion.groupby("web_target_id")["verdict_state"].apply(
            lambda s: decision_coverage(s)["rate"]
        )
        coverage_by_target.name = "decision_coverage_rate"
    else:
        coverage_by_target = pd.Series(dtype=float, name="decision_coverage_rate")

    landing_agg = landing.groupby("web_target_id").agg(
        measurement_status=("measurement_status", "first"),
        max_overlay_coverage=("max_overlay_coverage", "max"),
    )

    joint = landing_agg.join(
        [task_agg, interrupt_agg, coverage_by_target], how="left"
    ).reset_index()
    joint["interrupt_count"] = joint["interrupt_count"].fillna(0).astype(int)

    if not certification.empty:
        joint = joint.merge(
            certification[["web_target_id", "certified_current"]], on="web_target_id", how="left"
        )
    else:
        joint["certified_current"] = pd.NA

    return joint[
        [
            "web_target_id",
            "measurement_status",
            "decision_coverage_rate",
            "mpfed_max",
            "auth_gate_observed_any",
            "interrupt_count",
            "max_overlay_coverage",
            "certified_current",
        ]
    ]


def run_eda06(
    marts: dict[str, pd.DataFrame],
    out_dir: str | Path,
    *,
    provenance: ShadowProvenance | None = None,
) -> EDAOutputPaths:
    provenance = provenance or ShadowProvenance()
    joint = _build_joint_profile(marts)

    corr_note = None
    if not joint.empty:
        pair = (
            joint[["mpfed_max", "max_overlay_coverage"]]
            .apply(pd.to_numeric, errors="coerce")
            .dropna()
        )
        if len(pair) >= 3:
            rho, pvalue = scipy_stats.spearmanr(pair["mpfed_max"], pair["max_overlay_coverage"])
            corr_note = {"n": len(pair), "spearman_rho": float(rho), "p_value": float(pvalue)}

    summary = {
        "n_services": len(joint),
        "spearman_mpfed_vs_overlay": corr_note,
        "certified_current_distribution": (
            joint["certified_current"].value_counts(dropna=False).to_dict()
            if not joint.empty
            else {}
        ),
        "note": "세 축(KWCAG/entry friction/certification)은 이 표에서 병기될 뿐 단일 점수로 합치지 않는다.",
    }

    csv_path, parquet_path = write_table(joint, out_dir, NAME)
    summary_path = write_summary_json(summary, out_dir, NAME)

    fig, ax = plt.subplots(figsize=(6, 4.5))
    if not joint.empty and joint["mpfed_max"].notna().any():
        ax.scatter(
            pd.to_numeric(joint["mpfed_max"], errors="coerce"),
            pd.to_numeric(joint["max_overlay_coverage"], errors="coerce"),
        )
        ax.set_xlabel("MPFED (max per service)")
        ax.set_ylabel("max_overlay_coverage")
        ax.set_title("EDA-06 · MPFED × overlay coverage (synthetic)")
    else:
        ax.text(0.5, 0.5, "빈 입력 또는 수치 없음", ha="center", va="center")
        ax.set_axis_off()
    fig_path = savefig(fig, out_dir, NAME)

    body = [
        f"- 서비스(web_target) 행 수: {summary['n_services']}",
        f"- MPFED × overlay coverage Spearman: {summary.get('spearman_mpfed_vs_overlay')}",
        "- 세 축을 단일 종합점수로 합치지 않는다 — 이 표는 병기 조인이다 (`00 SSOT`).",
        "- 상관계수는 synthetic 데이터에서 계산된 예시이며 실제 서비스 관계를 주장하지 않는다.",
    ]
    md_path = write_markdown_note(
        "EDA-06 — Joint Profile", body, out_dir, NAME, provenance=provenance
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
    parser.add_argument("--out-dir", default="artifacts/analysis_skeleton/eda/eda06")
    parser.add_argument("--n-services", type=int, default=24)
    args = parser.parse_args()

    universe = generate_synthetic_universe(n_services=args.n_services).as_dict()
    marts = {name: pd.DataFrame(rows) for name, rows in universe.items()}
    paths = run_eda06(marts, args.out_dir)
    print(f"EDA-06 done → {paths.summary_json_path}")


if __name__ == "__main__":
    _main()
