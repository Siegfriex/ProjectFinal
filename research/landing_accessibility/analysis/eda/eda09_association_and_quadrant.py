"""EDA-09 — Primary/Secondary Association · Kruskal-Wallis 가드 · Joint Quadrant.

TIMEBOX EXECUTION SSOT(LA-TB-1630-20260827) 목표 2 + Claude A(governor)가 결과를
보기 전에 확정한 규칙들이 요구한 구체 통계 로직:

**Research Director 확정 통계 계약(동결, LA-TB-1630-20260827)**:

0. Descriptive first — MPFED median/IQR/mode/ECDF·archetype별 분포는 EDA-05가 낸다.
1. **Primary A0**: `Spearman(MPFED, OlderRelevantKWCAGFailRate)` — joint-valid
   서비스별 평균 MPFED × `older_relevance≠OTHER` 기준 fail rate. **"raw structural
   depth ↔ barrier burden association"으로만 해석한다 — difficulty causation
   표현 금지** (`PRIMARY_A0_INTERPRETATION_CONSTRAINT`).
2. **구조보정 분석**: `Spearman(ExcessDepth, OlderRelevantKWCAGFailRate)` —
   archetype 보정된 depth로 같은 Y를 다시 본다(role=`primary_structure_adjusted`).
3. **Secondary**: `Spearman(ExcessDepth, <obstruction 변수>)`. 변수는 §4.4
   자동선택 — **결측률이 가장 낮은 후보**를 고르고, 동률이면 사전 고정 우선순위
   (`OverlayCoverage` → `PrimaryActionOcclusion` → `blocking_modal_count` →
   `forced_dismissal_count`)로 깬다. **상관계수는 선택에 입력조차 되지 않는다**
   (동률에서 상관을 보고 고르면 그 순간 p-hacking이다). 후보 4종 **전부**의
   결측률을 산출물에 기록한다 — 선택된 것만 적으면 선택이 검증 불가능해진다.
4. **Spearman 최소 N**: pairwise-complete n<`SPEARMAN_HEADLINE_MIN_N`(=10)이면
   `claim_grade="C"`(exploratory)로 강등하고 p-value를 headline으로 인용하지
   않는다. tie가 많은 이산 MPFED에도 유효한 tie-aware Spearman을 쓰고, n이
   작으면(< 30) permutation p-value로 전환한다(`p_value_method` 필드에 기록).
5. **결론의 방향 = Spearman rho 부호. 두 민감도 축에서 각각 판정** (governor
   §2.1 확정): `sample_composition`(leave-one-archetype-out — 표본 구성을
   흔든다, A0 §15) · `measurement_uncertainty`(UNDETERMINED lower=전부 PASS /
   upper=전부 FAIL bound — 측정 불확실성을 흔든다, ANALYSIS_CONTRACT §2.1).
6. **claim grade**: association은 `B`(n>=10 **및 두 축 모두** 부호 유지) 또는
   `C`(어느 한 축이라도 뒤집히거나 확인 불가) 또는 `UNSUPPORTED`(실행 불가)만
   받는다 — `A`는 정의·기술통계 전용이라 association에는 절대 부여하지 않는다.
   뒤집힌 축은 `sign_flip_axis`로 명시한다.
7. **Kruskal-Wallis**: archetype별 MPFED 비교. `statistics.kruskal_wallis_gate`가
   **joint-valid n>=5**인 archetype만 포함한다(governor 확정값). pairwise/Dunn/FDR은
   `run_eda09(..., run_optional_pairwise=True)`를 줘야만 도는 별도 옵션이다.
8. **Joint quadrant 분류**: X=ExcessDepth, Y=OlderRelevantKWCAGFailRate,
   size=OverlayCoverage, facet=InteractionArchetype. `statistics.classify_quadrant`가
   Y median=0일 때 barrier_absent/present 이분법으로 자동 전환한다. **WA
   인증(certification)은 이 joint figure의 색·모양·범례 어디에도 인코딩하지
   않는다** — `certified_current`가 관측 프레임 전체에서 무분산(governor 확인:
   CERTIFIED 0건)이라, variance 없는 축을 시각 인코딩하면 그 자체가 오도다.

**joint-valid 제한**: 이 스크립트가 다루는 표본(primary association·quadrant)은
`joint_validity.classify_joint_validity()`가 정한 joint-valid 관측으로 제한한다
— L0 완료·L1 종결·MPFED 산출가능·older-relevant KWCAG 판정 존재 4조건을 전부
충족해야 한다. **obstruction 변수(secondary)는 이 요건에 넣지 않는다** — secondary
라서 요건에 넣으면 primary 표본이 불필요하게 깎인다(governor 지시). 시도 N·
joint-valid N·제외 N을 제외 사유별로 분해해 항상 병기한다.

세 축(KWCAG/entry friction/certification)을 단일 점수로 합치지 않는 원칙은
그대로 유지한다 — 이 스크립트의 어떤 산출물도 종합점수를 만들지 않는다.

**synthetic 데이터로만 검증됐다.**
"""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import stats as scipy_stats

from ..older_relevance_registry import registry_status
from ..provenance import ShadowProvenance
from .collection_window import collection_window_report
from .common import (
    EDAOutputPaths,
    excess_depth,
    savefig,
    stamp_all,
    write_markdown_note,
    write_summary_json,
    write_table,
)
from .joint_validity import classify_joint_validity, joint_validity_summary
from .statistics import (
    DIRECTION_DEFINITION,
    SECONDARY_ASSOCIATION_CANDIDATES,
    SPEARMAN_HEADLINE_MIN_N,
    assess_undetermined_confounding,
    association_result,
    classify_quadrant,
    kruskal_wallis_gate,
    kruskal_wallis_pairwise_dunn,
    older_relevant_kwcag_fail_rate,
    resolve_measurement_uncertainty_axis,
    select_secondary_association_variable,
    sign_preserved_across_bounds,
)

NAME = "eda09_association_and_quadrant"

_EMPTY_JOINT_COLUMNS = [
    "web_target_id",
    "mpfed_mean",
    "excess_depth_mean",
    "low_n_archetype",
    "fail_rate",
    "fail_rate_lower_bound",
    "fail_rate_upper_bound",
    "n_eligible",
    "n_undetermined",
    "undetermined_rate",
    "max_overlay_coverage",
    "blocking_modal_count",
    "max_primary_action_occlusion",
    "forced_dismissal_count",
    "archetype",
    "quadrant",
]

#: Research Director 확정 — primary(A0)는 "raw structural depth ↔ barrier burden
#: association"으로만 해석한다. difficulty causation 표현(예: "MPFED가 높을수록
#: 더 어렵다")을 금지한다 — 상관은 인과가 아니다.
PRIMARY_A0_INTERPRETATION_CONSTRAINT = (
    "raw structural depth ↔ barrier burden association으로만 해석한다. "
    "difficulty causation(예: '진입이 깊을수록 더 어렵다') 표현을 쓰지 않는다 — "
    "상관은 인과를 주장하지 않는다."
)


_FAIL_RATE_MU_RATIONALE = (
    "Y(OlderRelevantKWCAGFailRate)가 adjudicated final_status에 직접 의존한다 — "
    "UNDETERMINED lower(전부 PASS, FailRate 최소)/upper(전부 FAIL, 최대) bound에서 "
    "rho 부호를 대조했다."
)


def _build_joint_frame(
    marts: dict[str, pd.DataFrame], *, source_kind: str = "SYNTHETIC"
) -> tuple[pd.DataFrame, dict]:
    """joint-valid 관측으로 제한된 서비스별 joint frame.

    obstruction 후보 4종은 **전부** aggregate하고 **전부의 결측률**을 meta에
    남긴다 — §4.4 자동선택(결측률 최소 · 동률 시 사전 고정 우선순위)의 입력이자,
    그 선택이 산출물에서 재검증 가능하게 하는 근거다. 실제 secondary 검정에
    쓰이는 것은 그중 선택된 하나뿐이지만, 선택되지 않은 3종의 결측률도 기록한다.
    """
    task = marts.get("fact_task_entry", pd.DataFrame()).copy()
    criterion = marts.get("fact_criterion_result", pd.DataFrame())
    landing = marts.get("fact_landing_observation", pd.DataFrame())

    validity = classify_joint_validity(marts)
    validity_summary = joint_validity_summary(validity)

    if task.empty or landing.empty:
        return pd.DataFrame(columns=_EMPTY_JOINT_COLUMNS), {
            "n_undetermined_total": 0,
            "joint_validity": validity_summary,
        }

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

    # primary association 표본은 joint-valid로 제한한다(governor 지시) — mpfed_mean도
    # joint-valid 관측만으로 집계해야 primary/quadrant가 같은 모집단을 쓴다.
    valid_task = task[task["is_joint_valid"]]
    task_agg = valid_task.groupby("web_target_id").agg(
        mpfed_mean=("MPFED", "mean"),
        excess_depth_mean=("excess_depth", "mean"),
        low_n_archetype=("low_n_archetype", "any"),
        archetype=(
            "interaction_archetype",
            lambda s: s.mode().iat[0] if not s.mode().empty else None,
        ),
    )

    # 정본 older_relevance 표 미동결 상태에서 실제 데이터가 오면 여기서 fail-closed로 막힌다.
    fail_df = older_relevant_kwcag_fail_rate(criterion, landing, source_kind=source_kind)
    fail_df = fail_df.set_index("web_target_id") if not fail_df.empty else fail_df

    # obstruction 후보 4종 — secondary 변수 선택 재확인용으로 전부 aggregate한다.
    landing_agg = landing.groupby("web_target_id").agg(
        max_overlay_coverage=("max_overlay_coverage", "max"),
        blocking_modal_count=("blocking_modal_count", "max"),
        max_primary_action_occlusion=("max_primary_action_occlusion", "max"),
    )
    task_dismissal = task.groupby("web_target_id").agg(
        forced_dismissal_count=("forced_dismissal_count", "max")
    )

    joint = task_agg.join([fail_df, landing_agg, task_dismissal], how="left").reset_index()
    for col in (
        "fail_rate",
        "fail_rate_lower_bound",
        "fail_rate_upper_bound",
        "n_eligible",
        "n_undetermined",
        "undetermined_rate",
        "n_fail",
        "n_na_excluded",
    ):
        if col not in joint.columns:
            joint[col] = pd.NA

    # 정본 문서 §5-5 — EligibleOlderRelevant_i = 0 이라 FailRate = NULL 인 서비스 건수.
    n_eligible_num = pd.to_numeric(joint.get("n_eligible"), errors="coerce")
    meta = {
        "n_fail_rate_null_zero_eligible": int(
            (n_eligible_num.fillna(0) == 0).sum() if not joint.empty else 0
        ),
        "n_undetermined_total": int(
            pd.to_numeric(joint["n_undetermined"], errors="coerce").fillna(0).sum()
        ),
        "joint_validity": validity_summary,
        "secondary_candidate_missing_rate": {
            col: (
                round(float(pd.to_numeric(joint[col], errors="coerce").isna().mean()), 4)
                if col in joint.columns
                else None
            )
            for col in SECONDARY_ASSOCIATION_CANDIDATES
        },
    }
    return joint, meta


def _robust_direction_preserved(joint: pd.DataFrame, x_col: str, y_col: str) -> bool | None:
    """**표본 구성 축(sample_composition)** — leave-one-archetype-out으로 Spearman
    부호가 안정적인지 확인한다 (A0 §15 robustness).

    전체표본 rho의 부호를, archetype 하나씩 빼고 다시 계산한 rho들이 전부
    유지하면 `True`. 부호가 하나라도 뒤집히면 `False`. archetype 열이 없거나
    비교할 archetype이 2개 미만이면(뺄 게 없으면) `None`(확인 불가) — `None`은
    `assign_association_claim_grade`에서 "robust 확인 안 됨"으로 취급돼 `C`로
    내려간다(억지로 B를 주지 않는다).
    """
    if "archetype" not in joint.columns:
        return None
    pair = joint[[x_col, y_col, "archetype"]].apply(
        lambda s: s if s.name == "archetype" else pd.to_numeric(s, errors="coerce")
    )
    pair = pair.dropna(subset=[x_col, y_col])
    if len(pair) < SPEARMAN_HEADLINE_MIN_N:
        return None
    archetypes = pair["archetype"].dropna().unique().tolist()
    if len(archetypes) < 2:
        return None
    full_rho = scipy_stats.spearmanr(pair[x_col], pair[y_col]).statistic
    if not np.isfinite(full_rho) or full_rho == 0:
        return None
    full_sign = full_rho > 0
    for archetype in archetypes:
        remaining = pair[pair["archetype"] != archetype]
        if len(remaining) < 3:
            continue
        rho = scipy_stats.spearmanr(remaining[x_col], remaining[y_col]).statistic
        if not np.isfinite(rho):
            continue
        if (rho > 0) != full_sign:
            return False
    return True


def run_eda09(
    marts: dict[str, pd.DataFrame],
    out_dir: str | Path,
    *,
    provenance: ShadowProvenance | None = None,
    run_optional_pairwise: bool = False,
) -> EDAOutputPaths:
    provenance = provenance or ShadowProvenance()
    joint, meta = _build_joint_frame(marts, source_kind=provenance.source_kind)
    task = marts.get("fact_task_entry", pd.DataFrame())
    validity_summary = meta.get("joint_validity", {})

    # §4.4 — secondary 변수 자동선택(결측률 최소, 동률이면 사전 고정 우선순위).
    # 상관계수는 이 선택에 입력되지 않는다.
    secondary_selection = select_secondary_association_variable(
        meta.get("secondary_candidate_missing_rate", {})
    )
    secondary_variable = secondary_selection["selected"]

    if joint.empty:
        primary = association_result(
            pd.Series(dtype=float),
            pd.Series(dtype=float),
            x_name="MPFED",
            y_name="OlderRelevantKWCAGFailRate",
            role="primary",
            assumption="빈 입력",
            interpretation_constraint=PRIMARY_A0_INTERPRETATION_CONSTRAINT,
        )
        structure_adjusted = association_result(
            pd.Series(dtype=float),
            pd.Series(dtype=float),
            x_name="ExcessDepth",
            y_name="OlderRelevantKWCAGFailRate",
            role="primary_structure_adjusted",
            assumption="빈 입력",
        )
        empty_mu, empty_mu_rationale = resolve_measurement_uncertainty_axis(
            pd.DataFrame(columns=[secondary_variable]),
            x_col="excess_depth_mean",
            variable=secondary_variable,
        )
        secondary = association_result(
            pd.Series(dtype=float),
            pd.Series(dtype=float),
            x_name="ExcessDepth",
            y_name=secondary_variable,
            role="secondary",
            assumption="빈 입력",
            measurement_uncertainty=empty_mu,
            measurement_uncertainty_rationale=empty_mu_rationale,
        )
        kw_result = {"executed": False, "reason_not_executed": "빈 입력", "group_sizes": {}}
        classification_rule: dict = {"n_classified": 0, "reason": "빈 입력"}
    else:
        # 의무 3 — undetermined_rate ↔ FailRate 교란 확인. 상관이 임계를 넘으면
        # primary/구조보정 claim grade가 한 단계 강등된다(사유는 downgrade_reasons에).
        confounding = assess_undetermined_confounding(
            joint.get("undetermined_rate", pd.Series(dtype=float)), joint["fail_rate"]
        )
        # 축 1 — 표본 구성(leave-one-archetype-out). 축 2 — 측정 불확실성
        # (UNDETERMINED lower/upper bound FailRate에서 rho 부호 유지 여부).
        primary = association_result(
            joint["mpfed_mean"],
            joint["fail_rate"],
            x_name="MPFED(joint-valid 서비스 평균)",
            y_name="OlderRelevantKWCAGFailRate",
            role="primary",
            assumption=(
                "joint-valid 서비스(web_target_id)별 task 평균 MPFED × older_relevance≠OTHER 기준의 "
                "fail rate(EligibleOlderRelevant=PASS/FAIL 판정된 것만 분모, NA 제외, UNDETERMINED는 "
                "분모에서 제외하되 undetermined_rate로 별도 병기). 표본은 joint-valid로 제한된다."
            ),
            undetermined_n=meta["n_undetermined_total"],
            interpretation_constraint=PRIMARY_A0_INTERPRETATION_CONSTRAINT,
            sample_composition=_robust_direction_preserved(joint, "mpfed_mean", "fail_rate"),
            measurement_uncertainty=sign_preserved_across_bounds(
                joint["mpfed_mean"],
                joint["fail_rate"],
                joint["fail_rate_lower_bound"],
                joint["fail_rate_upper_bound"],
            ),
            measurement_uncertainty_rationale=_FAIL_RATE_MU_RATIONALE,
            undetermined_confounding=confounding,
        )
        structure_adjusted = association_result(
            joint["excess_depth_mean"],
            joint["fail_rate"],
            x_name="ExcessDepth(joint-valid 서비스 평균)",
            y_name="OlderRelevantKWCAGFailRate",
            role="primary_structure_adjusted",
            assumption=(
                "primary(A0)와 같은 Y를, archetype 보정된 ExcessDepth로 다시 본다 — raw MPFED가 "
                "archetype 구성에 끌려가는지 확인하는 구조보정 분석이다."
            ),
            undetermined_n=meta["n_undetermined_total"],
            sample_composition=_robust_direction_preserved(joint, "excess_depth_mean", "fail_rate"),
            measurement_uncertainty=sign_preserved_across_bounds(
                joint["excess_depth_mean"],
                joint["fail_rate"],
                joint["fail_rate_lower_bound"],
                joint["fail_rate_upper_bound"],
            ),
            measurement_uncertainty_rationale=_FAIL_RATE_MU_RATIONALE,
            undetermined_confounding=confounding,
        )
        secondary_mu, secondary_mu_rationale = resolve_measurement_uncertainty_axis(
            joint, x_col="excess_depth_mean", variable=secondary_variable
        )
        secondary = association_result(
            joint["excess_depth_mean"],
            joint[secondary_variable],
            x_name="ExcessDepth(joint-valid 서비스 평균)",
            y_name=f"{secondary_variable}(자동선택: 결측률 최소 · 동률 시 사전 고정 우선순위)",
            role="secondary",
            assumption=(
                "ExcessDepth = MPFED - archetype median (00 §7) — archetype 보정 없는 raw MPFED로 "
                "task를 직접 비교하지 않는다는 원칙을 여기서도 지킨다. obstruction 변수는 "
                "joint-valid 요건에 넣지 않는다(secondary라서 요건에 넣으면 primary 표본이 깎인다) — "
                "대신 후보 4종 전부의 결측률을 candidate_missing_rate로 항상 병기한다."
            ),
            sample_composition=_robust_direction_preserved(
                joint, "excess_depth_mean", secondary_variable
            ),
            # 측정 불확실성 축은 변수 **이름**이 아니라 **산출 경로 성질**로 건다:
            # 판정 비의존이면 근거와 함께 NOT_APPLICABLE, 판정 의존이면 bound 계산,
            # 미분류면 fail-closed로 None(강등). 실제 데이터에서 tie-break 결과가
            # 달라져 다른 변수가 뽑혀도 자동으로 옳게 동작한다.
            measurement_uncertainty=secondary_mu,
            measurement_uncertainty_rationale=secondary_mu_rationale,
        )

        if not task.empty:
            validity = classify_joint_validity(marts)
            valid_by_target = (
                validity.set_index("web_target_id")["is_joint_valid"]
                if not validity.empty
                else pd.Series(dtype=bool)
            )
            task_kw = task.copy()
            task_kw["is_joint_valid"] = task_kw["web_target_id"].map(valid_by_target).fillna(False)
            # Kruskal-Wallis 그룹은 joint-valid 행만 쓴다 — archetype n 정의를 ExcessDepth와 통일한다.
            groups = {
                str(name): group["MPFED"]
                for name, group in task_kw[task_kw["is_joint_valid"]].groupby(
                    "interaction_archetype"
                )
            }
            kw_result = kruskal_wallis_gate(groups)
            if run_optional_pairwise:
                kw_result["pairwise_dunn_fdr"] = kruskal_wallis_pairwise_dunn(groups)
        else:
            kw_result = {
                "executed": False,
                "reason_not_executed": "fact_task_entry 없음",
                "group_sizes": {},
            }

        joint, classification_rule = classify_quadrant(
            joint, x_col="excess_depth_mean", y_col="fail_rate"
        )
        # facet(archetype)별 quadrant 분포도 병기한다 — 단일 집계로 archetype 차이를 지우지 않는다.
        if "archetype" in joint.columns:
            facet_counts = (
                joint.dropna(subset=["quadrant"])
                .groupby(["archetype", "quadrant"])
                .size()
                .rename("n")
                .reset_index()
            )
            classification_rule["facet_by_archetype"] = facet_counts.to_dict(orient="records")

    summary = {
        "n_services": len(joint),
        "joint_validity": validity_summary,
        "older_relevance_registry": registry_status(),
        # 정본 §5-5 — EligibleOlderRelevant_i = 0 이라 FailRate = NULL 인 서비스 건수.
        "n_fail_rate_null_zero_eligible": meta.get("n_fail_rate_null_zero_eligible", 0),
        # 연장분기 의무 1·2·4 — 수집 시각 구간별 undetermined_rate 분해 + archetype 편향 확인.
        "collection_window": collection_window_report(marts),
        # 연장분기 의무 3 — undetermined_rate ↔ FailRate 교란 확인.
        "undetermined_confounding": (
            primary.get("undetermined_confounding") if isinstance(primary, dict) else None
        ),
        # 후보 4종 **전부**의 결측률 — 선택된 것만 적으면 선택 자체가 검증 불가능해진다.
        "secondary_candidate_missing_rate": meta.get("secondary_candidate_missing_rate", {}),
        "secondary_association_variable_selected": secondary_variable,
        "secondary_variable_selection": secondary_selection,
        "direction_definition": DIRECTION_DEFINITION,
        "primary_association": primary,
        "primary_structure_adjusted_association": structure_adjusted,
        "secondary_association": secondary,
        "kruskal_wallis_mpfed_by_archetype": kw_result,
        "quadrant_classification_rule": classification_rule,
        "three_axes_not_combined_note": "KWCAG/entry friction/certification은 이 산출물에서도 단일 점수로 합치지 않는다.",
        "certification_encoding_note": "WA 인증은 이 joint figure의 색·모양·범례 어디에도 인코딩하지 않는다(무분산 축이라서).",
    }

    csv_path, parquet_path = write_table(joint, out_dir, NAME)
    summary_path = write_summary_json(summary, out_dir, NAME)

    fig, axes = plt.subplots(1, 2, figsize=(11, 4.5))
    if not joint.empty and joint["excess_depth_mean"].notna().any():
        colors = {
            "A_low_depth_low_fail": "tab:blue",
            "B_high_depth_low_fail": "tab:orange",
            "C_low_depth_high_fail": "tab:green",
            "D_high_depth_high_fail": "tab:red",
        }
        plotted = joint.dropna(subset=["excess_depth_mean", "fail_rate"]).copy()
        plotted["_size"] = (
            pd.to_numeric(plotted["max_overlay_coverage"], errors="coerce").fillna(0.1) * 300
        ) + 20
        if "low_n_archetype" not in plotted.columns:
            plotted["low_n_archetype"] = False
        plotted["low_n_archetype"] = (
            plotted["low_n_archetype"].infer_objects(copy=False).fillna(False).astype(bool)
        )

        for q, group in plotted.groupby("quadrant"):
            color = colors.get(str(q), "gray")
            # 3<=archetype joint-valid n<=4(low_n_archetype)인 행은 반투명 + x 마커로
            # 시각적으로 구분한다(governor 확정 joint figure 표시 규칙). n<=2는
            # ExcessDepth=NULL이라 dropna에서 이미 빠져 여기 나타나지 않는다.
            low = group[group["low_n_archetype"]]
            high = group[~group["low_n_archetype"]]
            if not low.empty:
                axes[0].scatter(
                    low["excess_depth_mean"],
                    low["fail_rate"],
                    s=low["_size"],
                    label=f"{q} (low-n archetype)",
                    color=color,
                    alpha=0.25,
                    marker="x",
                )
            if not high.empty:
                axes[0].scatter(
                    high["excess_depth_mean"],
                    high["fail_rate"],
                    s=high["_size"],
                    label=str(q),
                    color=color,
                    alpha=0.65,
                    marker="o",
                )
        axes[0].set_xlabel("ExcessDepth (joint-valid service mean)")
        axes[0].set_ylabel("OlderRelevantKWCAGFailRate")
        axes[0].set_title("EDA-09 · quadrant (size=overlay coverage, WA인증 미인코딩)")
        axes[0].legend(fontsize=5)

        kw_sizes = dict(kw_result.get("group_sizes") or {})  # type: ignore[call-overload]
        if kw_sizes:
            axes[1].bar(list(kw_sizes.keys()), list(kw_sizes.values()))
            axes[1].axhline(
                5, color="red", linestyle="--", linewidth=1, label="min N (governor 확정, n=5)"
            )
            axes[1].set_title(
                f"archetype별 joint-valid group N (executed={kw_result.get('executed')})"
            )
            axes[1].tick_params(axis="x", labelrotation=45, labelsize=6)
            axes[1].legend(fontsize=6)
        else:
            axes[1].set_axis_off()
    else:
        for ax in axes:
            ax.text(0.5, 0.5, "빈 입력 또는 수치 없음", ha="center", va="center")
            ax.set_axis_off()
    fig_path = savefig(fig, out_dir, NAME)

    body = [
        f"- 서비스(web_target) 행 수(joint-valid 기준): {summary['n_services']}",
        f"- joint-valid: 시도 {validity_summary.get('n_attempted')}건 중 "
        f"{validity_summary.get('n_joint_valid')}건 (제외 사유별: {validity_summary.get('excluded_by_reason')}).",
        f"- **{DIRECTION_DEFINITION}**",
        f"- Primary A0: Spearman(MPFED, OlderRelevantKWCAGFailRate) = {primary['effect']} "
        f"(n={primary['n']}, missing_n={primary['missing_n']}, undetermined_n={primary['undetermined_n']}, "
        f"claim_grade={primary['claim_grade']}, headline_eligible={primary['headline_eligible']})",
        f"  - 해석 제약: {primary['interpretation_constraint']}",
        f"  - 부호 안정성 두 축: {primary['sign_stability']['by_axis']} "
        f"→ sign_flip_axis={primary['sign_flip_axis']}",
        f"- 구조보정: Spearman(ExcessDepth, OlderRelevantKWCAGFailRate) = {structure_adjusted['effect']} "
        f"(n={structure_adjusted['n']}, claim_grade={structure_adjusted['claim_grade']}, "
        f"headline_eligible={structure_adjusted['headline_eligible']})",
        f"  - 부호 안정성 두 축: {structure_adjusted['sign_stability']['by_axis']} "
        f"→ sign_flip_axis={structure_adjusted['sign_flip_axis']}",
        f"- Secondary 변수 자동선택: `{secondary_variable}` "
        f"(tie_break_applied={secondary_selection['tie_break_applied']}, "
        f"동률후보={secondary_selection['tied_candidates']})",
        f"  - 후보 4종 **전부**의 결측률: {summary.get('secondary_candidate_missing_rate')}",
        f"  - 동률 시 사전 고정 우선순위: {secondary_selection['priority_order']} "
        "(상관계수는 선택에 입력되지 않는다 — p-hacking 구조적 차단)",
        f"- Secondary: Spearman(ExcessDepth, {secondary_variable}) = {secondary['effect']} "
        f"(n={secondary['n']}, missing_n={secondary['missing_n']}, undetermined_n={secondary['undetermined_n']}, "
        f"claim_grade={secondary['claim_grade']}, headline_eligible={secondary['headline_eligible']})",
        f"  - 부호 안정성 두 축: {secondary['sign_stability']['by_axis']} "
        f"→ sign_flip_axis={secondary['sign_flip_axis']} "
        "(Y가 UNDETERMINED에 의존하지 않아 측정 불확실성 축은 구조적으로 미적용)",
        "- claim grade 규칙(Research Director + governor §2.1 확정): "
        "B=n>=10 & **두 축(표본 구성 · 측정 불확실성) 모두** 부호 유지, "
        "C=그 외(어느 한 축이라도 뒤집히거나 확인 불가 — exploratory, p-value headline 금지), "
        "UNSUPPORTED=실행 불가. association은 A를 받지 않는다.",
        f"- Kruskal-Wallis(archetype별 MPFED, joint-valid n>=5만 포함): "
        f"executed={kw_result.get('executed')}, statistic={kw_result.get('statistic')}, "
        f"p_value={kw_result.get('p_value')}",
        f"  - dropped(joint-valid n<5): {kw_result.get('dropped_groups_below_min_n')}",
        f"- Quadrant 분류 규칙: {classification_rule.get('x_split')} / {classification_rule.get('y_split')}"
        f" (y_median={classification_rule.get('y_median')}, "
        f"median_zero_fallback={classification_rule.get('y_median_is_zero_fallback_triggered')})",
        f"  - quadrant counts: {classification_rule.get('quadrant_counts')}",
        "- pairwise/Dunn/FDR은 기본 실행 경로에 없다 — `run_optional_pairwise=True`로만 돈다.",
        "- 세 축(KWCAG/entry friction/certification)을 단일 점수로 합치지 않는다.",
        "- WA 인증은 이 joint figure에 색·모양·범례 어디로도 인코딩하지 않았다(무분산).",
    ]
    md_path = write_markdown_note(
        "EDA-09 — Association & Quadrant", body, out_dir, NAME, provenance=provenance
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
    parser.add_argument("--out-dir", default="artifacts/analysis_current/eda/eda09")
    parser.add_argument("--n-services", type=int, default=24)
    parser.add_argument("--run-optional-pairwise", action="store_true")
    args = parser.parse_args()

    universe = generate_synthetic_universe(n_services=args.n_services).as_dict()
    marts = {name: pd.DataFrame(rows) for name, rows in universe.items()}
    paths = run_eda09(marts, args.out_dir, run_optional_pairwise=args.run_optional_pairwise)
    print(f"EDA-09 done → {paths.summary_json_path}")


if __name__ == "__main__":
    _main()
