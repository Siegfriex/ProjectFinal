"""목표 2 검증 — `research/landing_accessibility/analysis/eda` (EDA-03~08).

각 스크립트가 synthetic 데이터로 end-to-end 실행되고(CSV/Parquet + summary JSON +
그림 + Markdown note를 낸다), 빈 입력에도 안전한지 확인한다. EDA-07의 무분산
자동전환, EDA-05의 auth gate 합집합 집계, EDA-08의 UNDETERMINED 경계 병기처럼
오케스트레이터가 명시적으로 지시한 동작은 별도로 검증한다.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd
import pytest

_ANALYSIS_ROOT = Path(__file__).resolve().parents[1] / "research" / "landing_accessibility"
if str(_ANALYSIS_ROOT) not in sys.path:
    sys.path.insert(0, str(_ANALYSIS_ROOT))

from analysis.eda import RUNNERS  # noqa: E402
from analysis.marts.builders import BUILDERS  # noqa: E402
from analysis.marts.synthetic import generate_synthetic_universe  # noqa: E402


@pytest.fixture(scope="module")
def marts() -> dict[str, pd.DataFrame]:
    rows_by_table = generate_synthetic_universe(n_services=24, seed=7).as_dict()
    return {table: BUILDERS[table](rows).frame for table, rows in rows_by_table.items()}


@pytest.fixture()
def empty_marts() -> dict[str, pd.DataFrame]:
    return {table: BUILDERS[table]([]).frame for table in BUILDERS}


@pytest.mark.parametrize("key", list(RUNNERS))
def test_eda_runs_end_to_end_on_synthetic_data(
    tmp_path: Path, marts: dict[str, pd.DataFrame], key: str
) -> None:
    paths = RUNNERS[key](marts, tmp_path / key)
    assert paths.csv_path.exists()
    assert paths.parquet_path.exists()
    assert paths.summary_json_path.exists()
    assert paths.markdown_path.exists()
    assert len(paths.figure_paths) >= 1
    for fig_path in paths.figure_paths:
        assert fig_path.exists()
        assert fig_path.stat().st_size > 0
    summary = json.loads(paths.summary_json_path.read_text())
    assert isinstance(summary, dict)
    markdown = paths.markdown_path.read_text()
    assert "synthetic" in markdown or "SHADOW" in markdown or "synthetic" in markdown.lower()


@pytest.mark.parametrize("key", list(RUNNERS))
def test_eda_runs_end_to_end_on_empty_input(
    tmp_path: Path, empty_marts: dict[str, pd.DataFrame], key: str
) -> None:
    """(c) 빈 입력 — 예외 없이 산출물을 낸다 (내용이 비어 있을 뿐)."""
    paths = RUNNERS[key](empty_marts, tmp_path / f"{key}_empty")
    assert paths.summary_json_path.exists()
    assert paths.markdown_path.exists()
    summary = json.loads(paths.summary_json_path.read_text())
    assert isinstance(summary, dict)


def test_eda07_switches_to_descriptive_only_when_no_variance(
    tmp_path: Path, marts: dict[str, pd.DataFrame]
) -> None:
    """certified_current 전량 0(현재 알려진 기준선)이면 비교축을 강제로 살리지 않는다."""
    from analysis.eda.eda07_certification_descriptive import run_eda07

    assert marts["dim_certification"]["certified_current"].nunique() <= 1
    paths = run_eda07(marts, tmp_path / "eda07")
    summary = json.loads(paths.summary_json_path.read_text())
    assert summary["mode"] == "DESCRIPTIVE_ONLY"
    assert "comparison_decision_coverage_by_certified_current" not in summary


def test_eda07_never_runs_inferential_comparison_even_with_variance(
    tmp_path: Path, marts: dict[str, pd.DataFrame]
) -> None:
    """Claude A(governor) 확정 — 인증 관련 inferential/비교 경로는 분산 유무와
    무관하게 이 모듈에 아예 없다(LA-TB-1630-20260827). 이전에는 분산이 있으면
    `COMPARISON_ELIGIBLE`로 전환해 `comparison_decision_coverage_by_certified_current`
    를 냈지만, 그 경로 자체를 제거했다 — 인증 축은 항상 descriptive-only다.
    """
    from analysis.eda.eda07_certification_descriptive import run_eda07

    varied = dict(marts)
    cert = marts["dim_certification"].copy()
    cert.loc[cert.index[:5], "certified_current"] = "1"
    varied["dim_certification"] = cert

    paths = run_eda07(varied, tmp_path / "eda07_variance")
    summary = json.loads(paths.summary_json_path.read_text())
    assert summary["mode"] == "DESCRIPTIVE_ONLY"
    assert summary["has_variance"] is True
    assert "comparison_decision_coverage_by_certified_current" not in summary
    assert summary["claim_grade"] == "SUPPORTED_WITH_LIMITATION"


def test_eda05_auth_gate_union_not_undercounted(
    tmp_path: Path, marts: dict[str, pd.DataFrame]
) -> None:
    """A2 규칙 E-8 — 합집합 집계가 단독 집계보다 작아서는 안 된다 (과소집계 재발 방지)."""
    from analysis.eda.eda05_entry_depth import run_eda05

    paths = run_eda05(marts, tmp_path / "eda05")
    summary = json.loads(paths.summary_json_path.read_text())
    auth = summary["auth_gate"]
    assert auth["observed_n"] >= auth["naive_endpoint_status_only_n"]


def test_eda08_undetermined_stress_reports_both_bounds(
    tmp_path: Path, marts: dict[str, pd.DataFrame]
) -> None:
    """규칙 N-7 — UNDETERMINED를 점추정 하나로 접지 않고 두 경계를 병기한다."""
    from analysis.eda.eda08_robustness import run_eda08

    paths = run_eda08(marts, tmp_path / "eda08")
    summary = json.loads(paths.summary_json_path.read_text())
    stress = summary["undetermined_stress"]
    assert "pass_rate_if_undetermined_treated_as_fail" in stress
    assert "pass_rate_if_undetermined_treated_as_pass" in stress
    worst = stress["pass_rate_if_undetermined_treated_as_fail"]
    best = stress["pass_rate_if_undetermined_treated_as_pass"]
    assert worst <= best


def test_eda05_stratifies_gate_endpoint_archetypes(
    tmp_path: Path, marts: dict[str, pd.DataFrame]
) -> None:
    """A2 규칙 E-10 — FINANCIAL_ACTION_ENTRY/COMMUNICATION_ENTRY는 합산값만 내면 안 된다."""
    from analysis.eda.eda05_entry_depth import run_eda05

    paths = run_eda05(marts, tmp_path / "eda05_strata")
    summary = json.loads(paths.summary_json_path.read_text())
    by_archetype = summary["by_archetype"]
    for archetype in ("FINANCIAL_ACTION_ENTRY", "COMMUNICATION_ENTRY"):
        if archetype in by_archetype and by_archetype[archetype]["n"]:
            assert "strata" in by_archetype[archetype]
            assert "endpoint_via_auth_gate_rate" in by_archetype[archetype]


def test_no_arbitrary_depth_threshold_language_in_markdown(
    tmp_path: Path, marts: dict[str, pd.DataFrame]
) -> None:
    """해석 절제 — `depth >= N = bad` 류 임의 임계값을 산출물에 넣지 않는다."""
    from analysis.eda.eda05_entry_depth import run_eda05

    paths = run_eda05(marts, tmp_path / "eda05_threshold")
    markdown = paths.markdown_path.read_text()
    assert ">= N" not in markdown or "쓰지 않는다" in markdown


# ── governor §2.1 — 결론의 방향 = Spearman rho 부호, 두 축에서 각각 판정 ────────


def test_sign_preserved_across_bounds_detects_measurement_uncertainty_flip() -> None:
    """측정 불확실성 축 — UNDETERMINED bound 사이에서 부호가 뒤집히면 False."""
    from analysis.eda.statistics import sign_preserved_across_bounds

    x = pd.Series([1, 2, 3, 4, 5])
    # 점추정에서는 양의 상관, upper bound(전부 FAIL)에서는 음의 상관으로 뒤집힌다.
    y_point = pd.Series([0.1, 0.2, 0.3, 0.4, 0.5])
    y_lower = pd.Series([0.1, 0.2, 0.3, 0.4, 0.5])
    y_upper = pd.Series([0.9, 0.7, 0.5, 0.3, 0.1])
    assert sign_preserved_across_bounds(x, y_point, y_lower, y_upper) is False

    # 두 bound 모두 부호가 유지되면 True.
    stable_upper = pd.Series([0.2, 0.3, 0.4, 0.5, 0.6])
    assert sign_preserved_across_bounds(x, y_point, y_lower, stable_upper) is True


def test_claim_grade_downgrades_when_either_axis_flips() -> None:
    """두 축 모두 유지 → B. 어느 한 축이라도 뒤집히면 → C (governor 강등 규칙)."""
    from analysis.eda.statistics import assign_association_claim_grade

    common = {"n": 20, "executed": True}
    assert (
        assign_association_claim_grade(
            **common, sample_composition=True, measurement_uncertainty=True
        )
        == "B"
    )
    assert (
        assign_association_claim_grade(
            **common, sample_composition=False, measurement_uncertainty=True
        )
        == "C"
    )
    assert (
        assign_association_claim_grade(
            **common, sample_composition=True, measurement_uncertainty=False
        )
        == "C"
    )
    # 평가 불가(None)도 "확인 안 됨"이므로 강등한다.
    assert (
        assign_association_claim_grade(
            **common, sample_composition=True, measurement_uncertainty=None
        )
        == "C"
    )
    # 구조적으로 적용되지 않는 축은 강등 사유가 아니다.
    assert (
        assign_association_claim_grade(
            **common, sample_composition=True, measurement_uncertainty="NOT_APPLICABLE"
        )
        == "B"
    )


def test_sign_flip_axis_names_the_axis_that_flipped() -> None:
    """산출물이 '어느 축에서 뒤집혔는지'를 명시해야 한다 (governor 지시 3항)."""
    from analysis.eda.statistics import resolve_sign_flip_axis

    assert (
        resolve_sign_flip_axis(sample_composition=True, measurement_uncertainty=True)[
            "sign_flip_axis"
        ]
        is None
    )
    assert (
        resolve_sign_flip_axis(sample_composition=False, measurement_uncertainty=True)[
            "sign_flip_axis"
        ]
        == "sample_composition"
    )
    assert (
        resolve_sign_flip_axis(sample_composition=True, measurement_uncertainty=False)[
            "sign_flip_axis"
        ]
        == "measurement_uncertainty"
    )
    both = resolve_sign_flip_axis(sample_composition=False, measurement_uncertainty=False)
    assert both["sign_flip_axis"] == "measurement_uncertainty"
    assert set(both["sign_flip_axes"]) == {"sample_composition", "measurement_uncertainty"}


def test_secondary_variable_tie_break_uses_preregistered_priority_not_correlation() -> None:
    """§4.4 — 결측률 동률이면 사전 고정 우선순위로 깬다(상관 크기로 고르지 않는다)."""
    from analysis.eda.statistics import (
        SECONDARY_ASSOCIATION_PRIORITY,
        select_secondary_association_variable,
    )

    assert SECONDARY_ASSOCIATION_PRIORITY == (
        "max_overlay_coverage",
        "max_primary_action_occlusion",
        "blocking_modal_count",
        "forced_dismissal_count",
    )

    # 전부 동률 → 우선순위 1위.
    tied = dict.fromkeys(SECONDARY_ASSOCIATION_PRIORITY, 0.1)
    result = select_secondary_association_variable(tied)
    assert result["selected"] == "max_overlay_coverage"
    assert result["tie_break_applied"] is True

    # 결측률이 낮은 쪽이 우선순위보다 강하다.
    uneven = {
        "max_overlay_coverage": 0.4,
        "max_primary_action_occlusion": 0.4,
        "blocking_modal_count": 0.0,
        "forced_dismissal_count": 0.9,
    }
    result2 = select_secondary_association_variable(uneven)
    assert result2["selected"] == "blocking_modal_count"
    assert result2["tie_break_applied"] is False

    # 2·3위가 동률이면 우선순위상 앞선 PrimaryActionOcclusion.
    partial_tie = {
        "max_overlay_coverage": 0.5,
        "max_primary_action_occlusion": 0.2,
        "blocking_modal_count": 0.2,
        "forced_dismissal_count": 0.9,
    }
    result3 = select_secondary_association_variable(partial_tie)
    assert result3["selected"] == "max_primary_action_occlusion"


def test_eda09_reports_both_axes_and_all_candidate_missing_rates(
    tmp_path: Path, marts: dict[str, pd.DataFrame]
) -> None:
    """산출물이 두 축 판정 + 후보 4종 전부의 결측률을 담아야 한다."""
    from analysis.eda.eda09_association_and_quadrant import run_eda09
    from analysis.eda.statistics import SECONDARY_ASSOCIATION_PRIORITY

    paths = run_eda09(marts, tmp_path / "eda09_axes")
    summary = json.loads(paths.summary_json_path.read_text())

    assert "Spearman rho 부호" in summary["direction_definition"]
    # 후보 4종 전부 기록 — 선택된 것만 적으면 선택이 검증 불가능해진다.
    assert set(summary["secondary_candidate_missing_rate"]) == set(SECONDARY_ASSOCIATION_PRIORITY)

    for key in (
        "primary_association",
        "primary_structure_adjusted_association",
        "secondary_association",
    ):
        assoc = summary[key]
        axes = assoc["sign_stability"]["by_axis"]
        assert set(axes) == {"sample_composition", "measurement_uncertainty"}
        assert "sign_flip_axis" in assoc
        assert assoc["sign_flip_axis"] in (None, "sample_composition", "measurement_uncertainty")
        # association은 절대 GRADE A를 받지 않는다.
        assert assoc["claim_grade"] in ("B", "C", "UNSUPPORTED")

    # secondary는 Y가 UNDETERMINED에 의존하지 않으므로 측정 불확실성 축이 미적용이다.
    assert (
        summary["secondary_association"]["sign_stability"]["by_axis"]["measurement_uncertainty"]
        == "NOT_APPLICABLE"
    )


def test_headline_eligibility_follows_grade_not_just_sample_size() -> None:
    """headline은 A 또는 robust B만 — 축이 뒤집혀 C로 강등되면 headline 자격도 사라진다."""
    import pandas as pd
    from analysis.eda.statistics import association_result

    x = pd.Series(range(1, 21))
    y = pd.Series([i * 0.05 for i in range(1, 21)])

    robust = association_result(
        x,
        y,
        x_name="X",
        y_name="Y",
        role="primary",
        assumption="t",
        sample_composition=True,
        measurement_uncertainty=True,
    )
    assert robust["claim_grade"] == "B"
    assert robust["headline_eligible"] is True

    # n은 충분(20)하지만 측정 불확실성 축에서 부호가 뒤집힌 경우.
    flipped = association_result(
        x,
        y,
        x_name="X",
        y_name="Y",
        role="primary",
        assumption="t",
        sample_composition=True,
        measurement_uncertainty=False,
    )
    assert flipped["n"] >= 10
    assert flipped["claim_grade"] == "C"
    assert flipped["headline_eligible"] is False
    assert flipped["sign_flip_axis"] == "measurement_uncertainty"
