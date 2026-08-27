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
