"""EDA-07 — Certification Descriptive (`03_CRISP_DM_EXECUTION_PLAN_v2.0.md` Phase 4/5).

`dim_certification`을 소비한다. **알려진 이슈** — 현재 실측 기준선(A2 §1.3)은
`ELIGIBLE_WEB` 0건, 유효 인증 0건이다. `certified_current`에 분산이 없으면(전부 0
또는 전부 1) 비교축(인증 여부에 따른 접근성 비교 같은)을 **강제로 살리지 않는다.**
이 스크립트는 무분산을 감지해 자동으로 descriptive-only 모드로 전환한다.

이 자동전환 로직 자체가 오케스트레이터 지시의 핵심이다 — 무분산 상태에서 비교
결과를 만들어내는 것은 그 자체로 결론 유도(`00 §14` 금지)가 된다.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

from ..provenance import ShadowProvenance
from .common import (
    EDAOutputPaths,
    has_variance,
    savefig,
    stamp_all,
    write_markdown_note,
    write_summary_json,
    write_table,
)

NAME = "eda07_certification_descriptive"


def run_eda07(
    marts: dict[str, pd.DataFrame],
    out_dir: str | Path,
    *,
    provenance: ShadowProvenance | None = None,
    comparison_marts: dict[str, pd.DataFrame] | None = None,
) -> EDAOutputPaths:
    """`comparison_marts`가 주어지고 `certified_current`에 분산이 있으면(테스트 전용
    경로) 인증 여부에 따른 decision coverage 비교를 **추가로** 낸다. 기본 경로는
    항상 descriptive-only다 — 현재 기준선처럼 무분산이면 비교축을 만들지 않는다.
    """
    provenance = provenance or ShadowProvenance()
    certification = marts.get("dim_certification", pd.DataFrame())

    if certification.empty:
        distribution = pd.DataFrame(columns=["certified_current", "n"])
        summary = {"n": 0, "mode": "DESCRIPTIVE_ONLY", "reason": "빈 입력"}
    else:
        distribution = (
            certification["certified_current"]
            .value_counts(dropna=False)
            .rename_axis("certified_current")
            .reset_index(name="n")
        )
        variance = has_variance(certification["certified_current"])
        summary = {
            "n": len(certification),
            "certified_current_distribution": certification["certified_current"]
            .value_counts(dropna=False)
            .to_dict(),
            "has_variance": bool(variance),
            "mode": "COMPARISON_ELIGIBLE" if variance else "DESCRIPTIVE_ONLY",
        }
        if not variance:
            only_value = (certification["certified_current"].dropna().unique().tolist() or [None])[
                0
            ]
            summary["reason"] = (
                f"certified_current 전량이 {only_value!r} — 비교축을 강제로 살리지 않는다"
                " (이미 알려진 이슈, A2 §1.3 실측: ELIGIBLE_WEB 0건)"
            )
        else:
            summary["reason"] = "분산이 관측됐다 — 비교축 사용 가능 (여전히 synthetic)"

    comparison_result = None
    target = comparison_marts or (marts if summary.get("has_variance") else None)
    if target is not None:
        criterion = target.get("fact_criterion_result", pd.DataFrame())
        cert = target.get("dim_certification", pd.DataFrame())
        if not criterion.empty and not cert.empty and has_variance(cert["certified_current"]):
            from .common import decision_coverage

            landing = target.get("fact_landing_observation", pd.DataFrame())
            obs_to_target = (
                landing.set_index("observation_id")["web_target_id"]
                if not landing.empty
                else pd.Series(dtype=object)
            )
            crit = criterion.copy()
            crit["web_target_id"] = crit["observation_id"].map(obs_to_target)
            merged = crit.merge(
                cert[["web_target_id", "certified_current"]], on="web_target_id", how="left"
            )
            comparison_result = {
                str(cert_value): decision_coverage(group["verdict_state"])
                for cert_value, group in merged.groupby("certified_current", dropna=False)
            }
            summary["comparison_decision_coverage_by_certified_current"] = comparison_result

    csv_path, parquet_path = write_table(distribution, out_dir, NAME)
    summary_path = write_summary_json(summary, out_dir, NAME)

    fig, ax = plt.subplots(figsize=(5, 4))
    if not distribution.empty:
        distribution.set_index("certified_current")["n"].plot(kind="bar", ax=ax)
        ax.set_title(f"certified_current 분포 ({summary['mode']})")
        ax.set_ylabel("web_target count")
    else:
        ax.text(0.5, 0.5, "빈 입력", ha="center", va="center")
        ax.set_axis_off()
    fig_path = savefig(fig, out_dir, NAME)

    body = [
        f"- 표본: {summary['n']}건",
        f"- 모드: **{summary['mode']}**",
        f"- 사유: {summary.get('reason')}",
    ]
    if comparison_result is not None:
        body.append(f"- 비교(참고용, synthetic): {comparison_result}")
    else:
        body.append(
            "- 비교축 미생성 — descriptive-only. 비교를 원하면 실제 데이터로 재실행해야 한다."
        )
    md_path = write_markdown_note(
        "EDA-07 — Certification Descriptive", body, out_dir, NAME, provenance=provenance
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
    parser.add_argument("--out-dir", default="artifacts/analysis_skeleton/eda/eda07")
    parser.add_argument("--n-services", type=int, default=24)
    args = parser.parse_args()

    universe = generate_synthetic_universe(n_services=args.n_services).as_dict()
    marts = {name: pd.DataFrame(rows) for name, rows in universe.items()}
    paths = run_eda07(marts, args.out_dir)
    print(f"EDA-07 done → {paths.summary_json_path}")


if __name__ == "__main__":
    _main()
