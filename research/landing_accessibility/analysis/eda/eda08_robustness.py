"""EDA-08 — Robustness (`03_CRISP_DM_EXECUTION_PLAN_v2.0.md` Phase 5 통계·Robustness).

**기본 실행 경로**(`run_eda08`, robustness MVP)는 두 가지만 낸다:

1. **leave-one-archetype-out** — archetype 하나씩 제외하며 전체 MPFED 중앙값이
   얼마나 흔들리는지(delta 분포).
2. **UNDETERMINED stress** — `verdict_state=UNDETERMINED`를 FAIL로 본 경우 /
   PASS로 본 경우의 decision coverage 구간을 **병기**한다. 점추정으로 접지 않는다
   (`reporting.py assert_undetermined_not_dropped` 규칙 N-7과 같은 원칙 — 남은
   UNDETERMINED를 지우거나 stress bound에서 빼지 않는다).

**leave-one-service-out은 시간 남을 때만 실행하는 별도 옵션**이다
(`run_leave_one_service_out` — `run_eda08(..., run_optional_leave_one_service_out=True)`
로만 기본 경로에 얹힌다). 오케스트레이터 지시가 이 항을 명시적으로 optional로
분리하라고 요구했다 — 서비스 수가 늘어나면 O(n) leave-one-out 재계산 비용이
archetype(7종 고정) 쪽보다 훨씬 커진다.

**synthetic 데이터로만 검증됐다.**
"""

from __future__ import annotations

import argparse
from pathlib import Path

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

NAME = "eda08_robustness"


def _leave_one_out(frame: pd.DataFrame, group_col: str, value_col: str) -> pd.DataFrame:
    if frame.empty:
        return pd.DataFrame(columns=[group_col, "n_remaining", "median_without", "delta_from_full"])
    values = pd.to_numeric(frame[value_col], errors="coerce")
    full_median = values.median()
    rows = []
    for key in frame[group_col].dropna().unique():
        remaining = values[frame[group_col] != key].dropna()
        med = remaining.median() if not remaining.empty else None
        rows.append(
            {
                group_col: key,
                "n_remaining": int(remaining.shape[0]),
                "median_without": None if med is None else float(med),
                "delta_from_full": None
                if med is None or pd.isna(full_median)
                else float(med - full_median),
            }
        )
    return pd.DataFrame(rows)


def _undetermined_stress(criterion: pd.DataFrame) -> dict:
    if criterion.empty:
        return {"n": 0}
    s = criterion["verdict_state"].astype(str)
    applicable = s[s != "NA"]
    denom = len(applicable)
    if denom == 0:
        return {"n": 0}
    pass_n = int((applicable == "PASS").sum())
    fail_n = int((applicable == "FAIL").sum())
    undetermined_n = int((applicable == "UNDETERMINED").sum())
    # 두 경계를 병기한다 — 점추정으로 접지 않는다.
    best_case_pass_rate = round((pass_n + undetermined_n) / denom, 4)  # UNDETERMINED -> PASS
    worst_case_pass_rate = round(pass_n / denom, 4)  # UNDETERMINED -> FAIL
    excluded_rate = round(pass_n / (pass_n + fail_n), 4) if (pass_n + fail_n) else None
    return {
        "denominator_applicable": denom,
        "undetermined_n": undetermined_n,
        "pass_rate_if_undetermined_excluded": excluded_rate,
        "pass_rate_if_undetermined_treated_as_pass": best_case_pass_rate,
        "pass_rate_if_undetermined_treated_as_fail": worst_case_pass_rate,
        "bound_width": round(best_case_pass_rate - worst_case_pass_rate, 4),
    }


def run_leave_one_service_out(marts: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """**옵션** — 서비스(`web_target_id`) 하나씩 제외하며 MPFED 중앙값 흔들림을 본다.

    기본 실행 경로(`run_eda08`)에 없다. 시간이 남을 때 호출자가 명시적으로 부른다.
    """
    task = marts.get("fact_task_entry", pd.DataFrame())
    if task.empty:
        return pd.DataFrame(
            columns=["web_target_id", "n_remaining", "median_without", "delta_from_full"]
        )
    return _leave_one_out(task, "web_target_id", "MPFED")


def run_eda08(
    marts: dict[str, pd.DataFrame],
    out_dir: str | Path,
    *,
    provenance: ShadowProvenance | None = None,
    run_optional_leave_one_service_out: bool = False,
) -> EDAOutputPaths:
    provenance = provenance or ShadowProvenance()
    task = marts.get("fact_task_entry", pd.DataFrame())
    criterion = marts.get("fact_criterion_result", pd.DataFrame())

    loao = (
        _leave_one_out(task, "interaction_archetype", "MPFED")
        if not task.empty
        else pd.DataFrame(
            columns=["interaction_archetype", "n_remaining", "median_without", "delta_from_full"]
        )
    )
    stress = _undetermined_stress(criterion)

    combined = loao.assign(perturbation="leave_one_archetype_out")
    loso: pd.DataFrame | None = None
    if run_optional_leave_one_service_out:
        loso = run_leave_one_service_out(marts)
        combined = pd.concat(
            [combined, loso.assign(perturbation="leave_one_service_out")], ignore_index=True
        )

    summary = {
        "n_tasks": len(task),
        "n_criterion_rows": len(criterion),
        "leave_one_archetype_out_delta": median_iqr(loao["delta_from_full"])
        if not loao.empty
        else None,
        "leave_one_service_out_delta": (
            median_iqr(loso["delta_from_full"]) if loso is not None and not loso.empty else None
        ),
        "leave_one_service_out_ran": run_optional_leave_one_service_out,
        "undetermined_stress": stress,
    }

    csv_path, parquet_path = write_table(combined, out_dir, NAME)
    summary_path = write_summary_json(summary, out_dir, NAME)

    fig, axes = plt.subplots(1, 2, figsize=(10, 4.5))
    if not loao.empty:
        axes[0].bar(loao["interaction_archetype"].astype(str), loao["delta_from_full"].fillna(0))
        axes[0].set_title("leave-one-archetype-out Δmedian(MPFED)")
        axes[0].tick_params(axis="x", labelrotation=45, labelsize=6)
    else:
        axes[0].text(0.5, 0.5, "빈 입력", ha="center", va="center")
        axes[0].set_axis_off()

    bounds = stress
    if bounds.get("n", 1) != 0 and "pass_rate_if_undetermined_treated_as_fail" in bounds:
        axes[1].bar(
            ["worst(FAIL)", "excluded", "best(PASS)"],
            [
                bounds["pass_rate_if_undetermined_treated_as_fail"],
                bounds["pass_rate_if_undetermined_excluded"] or 0,
                bounds["pass_rate_if_undetermined_treated_as_pass"],
            ],
        )
        axes[1].set_title("UNDETERMINED stress bound (pass rate)")
        axes[1].set_ylim(0, 1)
    else:
        axes[1].text(0.5, 0.5, "빈 입력", ha="center", va="center")
        axes[1].set_axis_off()
    fig_path = savefig(fig, out_dir, NAME)

    body = [
        f"- leave-one-archetype-out Δmedian(MPFED) [기본 경로 MVP]: {summary.get('leave_one_archetype_out_delta')}",
        f"- leave-one-service-out Δmedian(MPFED) [옵션, ran={summary.get('leave_one_service_out_ran')}]: "
        f"{summary.get('leave_one_service_out_delta')}",
        f"- UNDETERMINED stress bound: {stress}",
        "- 두 경계(UNDETERMINED→FAIL / UNDETERMINED→PASS)를 병기했다. 점추정 하나로 접지 않는다"
        " (`reporting.py` 규칙 N-7과 같은 원칙 — 남은 UNDETERMINED를 지우거나 빼지 않는다).",
        "- leave-one-service-out은 기본 실행 경로가 아니다 — `run_optional_leave_one_service_out=True`로만 돈다.",
    ]
    md_path = write_markdown_note("EDA-08 — Robustness", body, out_dir, NAME, provenance=provenance)
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
    parser.add_argument("--out-dir", default="artifacts/analysis_current/eda/eda08")
    parser.add_argument("--n-services", type=int, default=24)
    parser.add_argument(
        "--run-optional-leave-one-service-out",
        action="store_true",
        help="시간 남을 때만 — 기본 경로에 없다",
    )
    args = parser.parse_args()

    universe = generate_synthetic_universe(n_services=args.n_services).as_dict()
    marts = {name: pd.DataFrame(rows) for name, rows in universe.items()}
    paths = run_eda08(
        marts,
        args.out_dir,
        run_optional_leave_one_service_out=args.run_optional_leave_one_service_out,
    )
    print(f"EDA-08 done → {paths.summary_json_path}")


if __name__ == "__main__":
    _main()
