"""EDA-05 — Entry Depth (`03_CRISP_DM_EXECUTION_PLAN_v2.0.md` Phase 5, M3).

`fact_task_entry`를 소비해 archetype별 MPFED median/IQR/mode/ECDF, endpoint reach율,
auth gate 유병률(A2 규칙 E-8 합집합), ExcessDepth를 낸다. `FINANCIAL_ACTION_ENTRY`·
`COMMUNICATION_ENTRY`는 A2 규칙 E-10에 따라 `ENDPOINT_VIA_AUTH_GATE` 층을 병기한다.
UNRESOLVED 계열(censored)은 별도 컬럼으로 노출하고 상한값으로 대치하지 않는다
(규칙 E-4). **synthetic 데이터로만 검증됐다.**
"""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

from ..provenance import ShadowProvenance
from .common import (
    EXCESS_DEPTH_INCLUDE_MIN_N,
    EXCESS_DEPTH_LOW_N_MIN,
    EDAOutputPaths,
    auth_gate_observed,
    ecdf,
    excess_depth,
    median_iqr,
    mode_value,
    savefig,
    stamp_all,
    write_markdown_note,
    write_summary_json,
    write_table,
)
from .joint_validity import (
    GUARD_BLOCKED_COLUMNS,
    classify_joint_validity,
    joint_validity_summary,
)

NAME = "eda05_entry_depth"
STRATIFIED_ARCHETYPES = {"FINANCIAL_ACTION_ENTRY", "COMMUNICATION_ENTRY"}


def run_eda05(
    marts: dict[str, pd.DataFrame],
    out_dir: str | Path,
    *,
    provenance: ShadowProvenance | None = None,
) -> EDAOutputPaths:
    provenance = provenance or ShadowProvenance()
    task = marts.get("fact_task_entry", pd.DataFrame()).copy()

    if task.empty:
        by_archetype = pd.DataFrame(
            columns=["archetype", "n", "median", "q1", "q3", "iqr", "mode", "endpoint_reach_rate"]
        )
        summary: dict = {"n_tasks": 0, "by_archetype": {}, "auth_gate": {}, "joint_validity": {}}
    else:
        validity = classify_joint_validity(marts)
        # web_target_id 기준 1:1(대표 task 1건) — joint_validity.py의 archetype 귀속과
        # 동일 근거로 merge한다.
        valid_by_target = (
            validity.set_index("web_target_id")["is_joint_valid"]
            if not validity.empty
            else pd.Series(dtype=bool)
        )
        task["is_joint_valid"] = task["web_target_id"].map(valid_by_target).fillna(False)

        excess = excess_depth(
            task["MPFED"], task["interaction_archetype"], valid=task["is_joint_valid"]
        )
        task["excess_depth"] = excess.excess_depth
        task["low_n_archetype"] = excess.low_n_archetype
        task["archetype_status"] = excess.archetype_status
        task["auth_gate_observed"] = auth_gate_observed(task)
        task["censored"] = (
            task.get("endpoint_status", pd.Series(dtype=object)).astype(str) == "UNRESOLVED"
        )

        rows = []
        by_archetype_json: dict = {}
        for archetype, group in task.groupby("interaction_archetype"):
            stats = median_iqr(group["MPFED"])
            reach_rate = round(float((group["endpoint_reached"].astype(str) == "1").mean()), 4)
            joint_valid_n = int(group["is_joint_valid"].sum())
            archetype_status = (
                group["archetype_status"].iloc[0]
                if not group["archetype_status"].empty
                else "TOO_LOW_NULL"
            )
            row = {
                "archetype": archetype,
                "n": stats["n"],
                "median": stats["median"],
                "q1": stats["q1"],
                "q3": stats["q3"],
                "iqr": stats["iqr"],
                "mode": mode_value(group["MPFED"]),
                "endpoint_reach_rate": reach_rate,
                "censored_n": int(group["censored"].sum()),
                # Claude A(governor) 확정 — n은 joint-valid 관측 수다(단순 non-null MPFED 아님).
                "joint_valid_n": joint_valid_n,
                "archetype_status": archetype_status,
                "excess_depth_included": archetype_status != "TOO_LOW_NULL",
                "kruskal_wallis_included": archetype_status == "INCLUDED",
            }
            entry: dict = dict(row)
            if archetype in STRATIFIED_ARCHETYPES:
                # 규칙 E-10 — 합산값만 내지 않는다. via-gate / direct 층을 병기한다.
                via_gate = group[group.get("endpoint_status_detail") == "ENDPOINT_VIA_AUTH_GATE"]
                direct = group.loc[group.index.difference(via_gate.index)]
                entry["strata"] = {
                    "ENDPOINT_VIA_AUTH_GATE": median_iqr(via_gate["MPFED"]),
                    "DIRECT_FUNCTION_ENTRY": median_iqr(direct["MPFED"]),
                }
                entry["endpoint_via_auth_gate_rate"] = (
                    round(len(via_gate) / len(group), 4) if len(group) else None
                )
            by_archetype_json[str(archetype)] = entry
            rows.append(row)
        by_archetype = pd.DataFrame(rows)

        summary = {
            "n_tasks": len(task),
            "by_archetype": by_archetype_json,
            "auth_gate": {
                "observed_rate_overall": round(float(task["auth_gate_observed"].mean()), 4),
                "observed_n": int(task["auth_gate_observed"].sum()),
                "naive_endpoint_status_only_n": int(
                    (task["endpoint_status"].astype(str) == "AUTH_GATE_REACHED").sum()
                ),
            },
            "excess_depth": median_iqr(task["excess_depth"]),
            "censored_total": int(task["censored"].sum()),
            # 시도 N · joint-valid N · 제외 N을 제외 사유별로 분해(governor 지시) —
            # 총계만 주지 않는다.
            "joint_validity": joint_validity_summary(
                validity,
                guard_cols_present=any(
                    c in marts.get("fact_task_entry", pd.DataFrame()).columns
                    for c in GUARD_BLOCKED_COLUMNS
                ),
            ),
        }

    csv_path, parquet_path = write_table(by_archetype, out_dir, NAME)
    summary_path = write_summary_json(summary, out_dir, NAME)

    fig, axes = plt.subplots(1, 2, figsize=(11, 4.5))
    if not task.empty:
        for archetype, group in task.groupby("interaction_archetype"):
            curve = ecdf(group["MPFED"])
            if not curve.empty:
                axes[0].step(curve["value"], curve["ecdf"], where="post", label=str(archetype))
        axes[0].set_title("archetype별 MPFED ECDF")
        axes[0].set_xlabel("MPFED")
        axes[0].set_ylabel("F(x)")
        axes[0].legend(fontsize=6)

        task.boxplot(column="MPFED", by="interaction_archetype", ax=axes[1], rot=45)
        axes[1].set_title("archetype별 MPFED 분포")
        plt.suptitle("")
    else:
        for ax in axes:
            ax.text(0.5, 0.5, "빈 입력", ha="center", va="center")
            ax.set_axis_off()
    fig_path = savefig(fig, out_dir, NAME)

    body = [
        f"- task 행 수: {summary['n_tasks']}",
        f"- auth gate 유병률(A2 규칙 E-8 합집합): {summary.get('auth_gate', {}).get('observed_rate_overall')}"
        f" (단독 집계였다면: {summary.get('auth_gate', {}).get('naive_endpoint_status_only_n')}건"
        " — 과소집계 재현, A2 §1.5.1a)",
        f"- ExcessDepth(= MPFED - archetype median, joint-valid 행만) 분포: {summary.get('excess_depth')}",
        f"- censored(UNRESOLVED 계열) 총 {summary.get('censored_total')}건 — 상한값으로 대치하지 않고 별도 노출했다 (규칙 E-4).",
        "- `FINANCIAL_ACTION_ENTRY`·`COMMUNICATION_ENTRY`는 `ENDPOINT_VIA_AUTH_GATE` 층을 병기했다 (규칙 E-10)"
        " — 합산 중앙값만 보면 '로그인 벽을 앞에 세웠는가'가 섞여 들어간다.",
        "- 절대 threshold(`depth >= N = bad`)를 쓰지 않는다 (`00 §7`).",
        f"- joint-valid: 시도 {summary.get('joint_validity', {}).get('n_attempted')}건 중 "
        f"{summary.get('joint_validity', {}).get('n_joint_valid')}건 (제외 사유별: "
        f"{summary.get('joint_validity', {}).get('excluded_by_reason')}).",
        f"- archetype 최소 N 규칙(Claude A governor 확정, n>={EXCESS_DEPTH_INCLUDE_MIN_N} 포함/"
        f"{EXCESS_DEPTH_LOW_N_MIN}~{EXCESS_DEPTH_INCLUDE_MIN_N - 1} ExcessDepth만 산출/"
        f"<{EXCESS_DEPTH_LOW_N_MIN} ExcessDepth=NULL)을 archetype별 `joint_valid_n`으로 판정했다"
        " — `LIMITATIONS.md`에 archetype별 표로 다시 명시한다.",
    ]
    md_path = write_markdown_note(
        "EDA-05 — Entry Depth", body, out_dir, NAME, provenance=provenance
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
    parser.add_argument("--out-dir", default="artifacts/analysis_current/eda/eda05")
    parser.add_argument("--n-services", type=int, default=24)
    args = parser.parse_args()

    universe = generate_synthetic_universe(n_services=args.n_services).as_dict()
    marts = {name: pd.DataFrame(rows) for name, rows in universe.items()}
    paths = run_eda05(marts, args.out_dir)
    print(f"EDA-05 done → {paths.summary_json_path}")


if __name__ == "__main__":
    _main()
