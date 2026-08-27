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

    retired = summary["retired_depth_associations"]
    for assoc in (
        summary["primary_association"],
        retired["mpfed_x_fail_rate"],
        retired["excess_depth_x_obstruction"],
    ):
        axes = assoc["sign_stability"]["by_axis"]
        assert set(axes) == {"sample_composition", "measurement_uncertainty"}
        assert "sign_flip_axis" in assoc
        assert assoc["sign_flip_axis"] in (None, "sample_composition", "measurement_uncertainty")
        # association은 절대 GRADE A를 받지 않는다.
        assert assoc["claim_grade"] in ("B", "C", "UNSUPPORTED")

    # 원 설계 secondary(ExcessDepth x obstruction)는 Y가 UNDETERMINED에 의존하지
    # 않으므로 측정 불확실성 축이 구조적으로 미적용이다.
    assert (
        summary["retired_depth_associations"]["excess_depth_x_obstruction"]["sign_stability"][
            "by_axis"
        ]["measurement_uncertainty"]
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


# ── governor 추가 판정 3건 ────────────────────────────────────────────────


def test_measurement_uncertainty_exemption_is_by_property_not_by_name() -> None:
    """면제는 변수 이름이 아니라 산출 경로 성질로 건다 — 판정 의존 변수는 면제되지 않는다."""
    import pandas as pd
    from analysis.eda.statistics import (
        OBSTRUCTION_VARIABLE_PROPERTIES,
        resolve_measurement_uncertainty_axis,
    )

    frame = pd.DataFrame({"x": [1.0, 2.0, 3.0], "max_overlay_coverage": [0.1, 0.2, 0.3]})

    # 판정 비의존 → NOT_APPLICABLE + 근거 문자열이 반드시 함께.
    verdict, rationale = resolve_measurement_uncertainty_axis(
        frame, x_col="x", variable="max_overlay_coverage"
    )
    assert verdict == "NOT_APPLICABLE"
    assert rationale and "adjudicated UNDETERMINED를 일절 포함하지 않는다" in rationale

    # 판정 의존 변수는 bound 없이 면제되지 않는다 — fail-closed로 None(강등).
    dep = pd.DataFrame({"x": [1.0, 2.0, 3.0], "max_primary_action_occlusion": [0.1, 0.2, 0.3]})
    verdict2, rationale2 = resolve_measurement_uncertainty_axis(
        dep, x_col="x", variable="max_primary_action_occlusion"
    )
    assert verdict2 is None
    assert "FAIL_CLOSED" in rationale2

    # 미분류 변수 → fail-closed. "몰라서 면제"는 금지.
    unknown = pd.DataFrame({"x": [1.0, 2.0, 3.0], "made_up_var": [0.1, 0.2, 0.3]})
    verdict3, rationale3 = resolve_measurement_uncertainty_axis(
        unknown, x_col="x", variable="made_up_var"
    )
    assert verdict3 is None
    assert "FAIL_CLOSED" in rationale3

    # 후보 4종은 전부 성질이 등재돼 있어야 한다(근거 문자열 포함).
    for prop in OBSTRUCTION_VARIABLE_PROPERTIES.values():
        assert prop.rationale and prop.evidence_path


def test_not_applicable_without_rationale_is_rejected() -> None:
    """근거 없는 NOT_APPLICABLE은 None과 구별되지 않으므로 실패시킨다."""
    import pytest as _pytest
    from analysis.eda.statistics import MissingExemptionRationale, resolve_sign_flip_axis

    with _pytest.raises(MissingExemptionRationale):
        resolve_sign_flip_axis(sample_composition=True, measurement_uncertainty="NOT_APPLICABLE")


def test_gate_reached_mpfed_null_is_separated_from_our_side_failures(
    marts: dict[str, pd.DataFrame],
) -> None:
    """gate 도달로 인한 탈락은 대상의 성질 — transport/timeout/mpfed_null과 섞지 않는다."""
    from analysis.eda.joint_validity import (
        EXCLUSION_REASON_IS_TARGET_PROPERTY,
        classify_joint_validity,
        joint_validity_summary,
    )

    validity = classify_joint_validity(marts)
    summary = joint_validity_summary(validity)

    assert "GATE_REACHED_MPFED_NULL" in summary["excluded_by_reason"]
    assert EXCLUSION_REASON_IS_TARGET_PROPERTY["GATE_REACHED_MPFED_NULL"] is True
    assert EXCLUSION_REASON_IS_TARGET_PROPERTY["MPFED_NULL"] is False
    assert EXCLUSION_REASON_IS_TARGET_PROPERTY["TIMEOUT"] is False

    behind = summary["behind_gate"]
    assert behind["n_services"] == summary["excluded_by_reason"]["GATE_REACHED_MPFED_NULL"]
    # gate에 막힌 행은 gate 계열 endpoint_status로만 라벨된다.
    gate_rows = validity[validity["exclusion_reason"] == "GATE_REACHED_MPFED_NULL"]
    assert set(gate_rows["endpoint_status"]) <= {
        "AUTH_GATE_REACHED",
        "PAYMENT_GATE_REACHED",
        "PERSONAL_DATA_REQUIRED",
        "CAPTCHA",
    }


def test_canonical_older_relevance_document_verifies_and_parses() -> None:
    """정본 문서(LA-ORS-20260827)를 sha256 대조 후 파싱하고, 문서 §3 집계와 맞는지 본다."""
    from analysis.older_relevance_registry import (
        CANONICAL_DOC_SHA256,
        EXPECTED_DOMAIN_COUNTS,
        EXPECTED_OLDER_RELEVANT_PILOT_APPLIED,
        EXPECTED_OLDER_RELEVANT_SUBTOTAL,
        EXPECTED_TOTAL,
        clear_canonical_older_relevance,
        load_frozen_canonical,
    )

    clear_canonical_older_relevance()
    canonical = load_frozen_canonical()  # sha256 불일치면 여기서 실패한다
    try:
        assert canonical.source_sha256 == CANONICAL_DOC_SHA256
        assert canonical.doc_id == "LA-ORS-20260827"
        assert len(canonical.tags) == EXPECTED_TOTAL == 33
        assert len(canonical.older_relevant_ids()) == EXPECTED_OLDER_RELEVANT_SUBTOTAL == 22
        assert (
            len(canonical.pilot_applied_older_relevant_ids())
            == EXPECTED_OLDER_RELEVANT_PILOT_APPLIED
            == 12
        )
        counts: dict[str, int] = {}
        for tag in canonical.tags.values():
            counts[tag.older_relevance] = counts.get(tag.older_relevance, 0) + 1
        assert counts == EXPECTED_DOMAIN_COUNTS
        # 데이터 관측 이전 동결(outcome-blind)이라는 사실이 보존된다.
        assert canonical.frozen_before_any_real_evidence is True
        # 폐기된 픽스처 id는 정본에 없다.
        assert canonical.relevance_of("2.4.7") is None
    finally:
        clear_canonical_older_relevance()


def test_fail_rate_opens_for_real_data_once_canonical_is_frozen(
    marts: dict[str, pd.DataFrame],
) -> None:
    """주입 후 non-synthetic source로 FailRate 계산이 **실제로 열린다**.

    (지금까지는 차단만 테스트했다 — coordinator 지시로 개방 경로를 검증한다.)
    """
    from analysis.eda.statistics import older_relevant_kwcag_fail_rate
    from analysis.older_relevance_registry import (
        clear_canonical_older_relevance,
        is_frozen,
        load_frozen_canonical,
    )

    criterion = marts["fact_criterion_result"]
    landing = marts["fact_landing_observation"]

    clear_canonical_older_relevance()
    try:
        load_frozen_canonical()
        assert is_frozen() is True
        result = older_relevant_kwcag_fail_rate(criterion, landing, source_kind="REAL_E001")
        assert not result.empty
        # 분모는 태깅 소계 22가 아니라 "판정된 것"이다 — 계약 §2 정합.
        assert (result["n_eligible"] <= 12).all()
        assert set(result.columns) >= {
            "fail_rate",
            "fail_rate_lower_bound",
            "fail_rate_upper_bound",
            "n_eligible",
            "n_undetermined",
            "undetermined_rate",
        }
    finally:
        clear_canonical_older_relevance()


def test_fail_rate_blocked_when_canonical_document_unavailable(
    marts: dict[str, pd.DataFrame], monkeypatch
) -> None:
    """정본을 확보하지 못하면 실제 데이터 경로는 여전히 fail-closed로 막힌다."""
    import analysis.older_relevance_registry as reg
    import pytest as _pytest
    from analysis.eda import statistics as stats_mod
    from analysis.older_relevance_registry import (
        OlderRelevanceNotFrozenError,
        clear_canonical_older_relevance,
    )

    clear_canonical_older_relevance()

    def _boom(**kwargs):
        raise OlderRelevanceNotFrozenError("정본 문서를 읽을 수 없다(test)")

    monkeypatch.setattr(reg, "load_frozen_canonical", _boom)
    try:
        with _pytest.raises(OlderRelevanceNotFrozenError):
            stats_mod.older_relevant_kwcag_fail_rate(
                marts["fact_criterion_result"],
                marts["fact_landing_observation"],
                source_kind="REAL_E001",
            )
        # synthetic 경로는 그대로 돈다.
        assert not stats_mod.older_relevant_kwcag_fail_rate(
            marts["fact_criterion_result"],
            marts["fact_landing_observation"],
            source_kind="SYNTHETIC",
        ).empty
    finally:
        clear_canonical_older_relevance()


def test_mart_drift_against_canonical_is_detected() -> None:
    """C1 — mart의 older_relevance가 정본과 다르거나 표에 없는 id면 검출된다."""
    from analysis.older_relevance_registry import (
        check_mart_older_relevance_drift,
        clear_canonical_older_relevance,
        load_frozen_canonical,
    )

    clear_canonical_older_relevance()
    try:
        load_frozen_canonical()
        # 1.1.1은 정본에서 OTHER다 — VISION으로 오면 OLDER_TAG_DRIFT.
        findings = check_mart_older_relevance_drift(["1.1.1"], ["VISION"])
        assert findings and findings[0]["code"] == "OLDER_TAG_DRIFT"
        assert findings[0]["expected"] == "OTHER"

        # 표에 없는 id는 SUSPECT_CRITERION_ID.
        findings2 = check_mart_older_relevance_drift(["2.4.7"], ["COGNITIVE_NAVIGATION"])
        assert findings2 and findings2[0]["code"] == "SUSPECT_CRITERION_ID"

        # 정본과 일치하면 findings 없음.
        assert check_mart_older_relevance_drift(["1.4.3"], ["VISION"]) == []
    finally:
        clear_canonical_older_relevance()


def test_synthetic_fixture_matches_canonical_assignments() -> None:
    """픽스처 배정값이 정본과 어긋나지 않는다 — 어긋나면 synthetic이 정본을 반증하게 된다."""
    from analysis.marts.synthetic import SYNTHETIC_ONLY_OLDER_RELEVANT_FIXTURE
    from analysis.older_relevance_registry import (
        check_mart_older_relevance_drift,
        clear_canonical_older_relevance,
        load_frozen_canonical,
    )

    clear_canonical_older_relevance()
    try:
        load_frozen_canonical()
        ids = list(SYNTHETIC_ONLY_OLDER_RELEVANT_FIXTURE)
        vals = [SYNTHETIC_ONLY_OLDER_RELEVANT_FIXTURE[i] for i in ids]
        assert check_mart_older_relevance_drift(ids, vals) == []
    finally:
        clear_canonical_older_relevance()


def test_synthetic_fixture_has_no_nonexistent_kwcag_id() -> None:
    """2.4.7은 KWCAG 2.2에 없는 id다 — 픽스처에서도 제거돼야 한다."""
    from analysis.marts.synthetic import (
        CRITERION_IDS,
        RETIRED_PRE_CANONICAL_FIXTURE_IDS,
        SYNTHETIC_ONLY_OLDER_RELEVANT_FIXTURE,
    )

    assert "2.4.7" in RETIRED_PRE_CANONICAL_FIXTURE_IDS
    for retired in RETIRED_PRE_CANONICAL_FIXTURE_IDS:
        assert retired not in CRITERION_IDS
        assert retired not in SYNTHETIC_ONLY_OLDER_RELEVANT_FIXTURE
    # 픽스처 목록과 criterion id 목록이 어긋나지 않는다.
    assert set(SYNTHETIC_ONLY_OLDER_RELEVANT_FIXTURE) == set(CRITERION_IDS)


# ── 연장분기 의무 1·2·3·4 ─────────────────────────────────────────────────


def test_undetermined_confounding_downgrades_primary_one_step() -> None:
    """의무 3 — 교란이 확인되면 claim grade가 한 단계 강등되고 사유가 기록된다."""
    import pandas as pd
    from analysis.eda.statistics import (
        CONFOUND_RHO_THRESHOLD,
        assess_undetermined_confounding,
        association_result,
        downgrade_one_step,
    )

    assert downgrade_one_step("B") == "C"
    assert downgrade_one_step("C") == "UNSUPPORTED"
    assert downgrade_one_step("UNSUPPORTED") == "UNSUPPORTED"

    # 완전 상관 → 교란.
    u = pd.Series([i * 0.05 for i in range(20)])
    f = pd.Series([i * 0.04 for i in range(20)])
    confound = assess_undetermined_confounding(u, f)
    assert confound["tested"] is True
    assert abs(confound["spearman_rho"]) >= CONFOUND_RHO_THRESHOLD
    assert confound["confounded"] is True

    x = pd.Series(range(1, 21))
    y = pd.Series([i * 0.05 for i in range(1, 21)])
    res = association_result(
        x,
        y,
        x_name="X",
        y_name="Y",
        role="primary",
        assumption="t",
        sample_composition=True,
        measurement_uncertainty=True,
        undetermined_confounding=confound,
    )
    assert res["claim_grade_before_confound_downgrade"] == "B"
    assert res["claim_grade"] == "C"  # 한 단계 강등
    codes = [r["code"] for r in res["downgrade_reasons"]]
    assert "UNDETERMINED_RATE_CONFOUNDING" in codes

    # 교란이 없으면 강등하지 않는다.
    clean = assess_undetermined_confounding(pd.Series([1, 2, 3] * 7), pd.Series([3, 1, 2] * 7))
    res2 = association_result(
        x,
        y,
        x_name="X",
        y_name="Y",
        role="primary",
        assumption="t",
        sample_composition=True,
        measurement_uncertainty=True,
        undetermined_confounding=clean,
    )
    if not clean["confounded"]:
        assert res2["claim_grade"] == "B"
        assert "UNDETERMINED_RATE_CONFOUNDING" not in [r["code"] for r in res2["downgrade_reasons"]]


def test_collection_window_splits_on_sealed_at_and_reports(
    marts: dict[str, pd.DataFrame],
) -> None:
    """의무 1·2 — sealed_at 기준 구간별 undetermined_rate 분해."""
    from analysis.eda.collection_window import (
        AI_CUTOFF_ISO,
        WINDOW_POST,
        WINDOW_PRE,
        assign_window,
        collection_window_report,
    )

    assert assign_window("2026-08-27T13:30:00+09:00") == WINDOW_PRE
    assert assign_window("2026-08-27T14:30:00+09:00") == WINDOW_POST
    assert assign_window(None) == "SEALED_AT_MISSING"

    report = collection_window_report(marts)
    assert report["cutoff"] == AI_CUTOFF_ISO
    assert "sealed_at" in report["sealed_at_source"]
    assert report["observations_by_window"]

    undet = report["undetermined_rate_by_window"]
    assert set(undet["by_window"]) <= {WINDOW_PRE, WINDOW_POST, "SEALED_AT_MISSING"}
    assert undet["verdict"] in {
        "DIFFERS_BY_WINDOW",
        "NO_SIGNIFICANT_DIFFERENCE",
        "NOT_ENOUGH_DATA",
    }
    # 유의하게 다르면 반드시 "처리 순서에 기인"으로 귀속한다.
    if undet["verdict"] == "DIFFERS_BY_WINDOW":
        assert "처리 순서에 기인" in undet["attribution"]


def test_archetype_bias_is_checked_never_asserted_without_data(
    marts: dict[str, pd.DataFrame],
) -> None:
    """의무 4 — 확인하지 않고 '편향 없음'이라고 쓰지 않는다."""
    from analysis.eda.collection_window import collection_window_report

    arche = collection_window_report(marts)["archetype_distribution_by_window"]
    assert arche["verdict"] in {"BIAS_DETECTED", "CHECKED_NO_BIAS_DETECTED", "NOT_ENOUGH_DATA"}
    # 분포는 실제로 계산돼 기록된다.
    assert isinstance(arche["by_window"], dict)
    if arche["verdict"] == "NOT_ENOUGH_DATA":
        # 표본 부족을 "편향 없음"으로 쓰지 않는다.
        assert "편향이 없다는 뜻이 아니다" in arche.get("reason_not_tested", "")
        assert arche["tested"] is False
    else:
        assert arche["tested"] is True


def test_eda09_summary_carries_extension_obligations(
    marts: dict[str, pd.DataFrame], tmp_path: Path
) -> None:
    """산출물이 의무 1·2·3·4 결과를 전부 담는다."""
    from analysis.eda.eda09_association_and_quadrant import run_eda09

    summary = json.loads(run_eda09(marts, tmp_path / "eda09_ext").summary_json_path.read_text())
    assert "collection_window" in summary
    assert "undetermined_rate_by_window" in summary["collection_window"]
    assert "archetype_distribution_by_window" in summary["collection_window"]
    assert "undetermined_confounding" in summary
    assert "downgrade_reasons" in summary["primary_association"]
    assert "claim_grade_before_confound_downgrade" in summary["primary_association"]


# ── 계약 개정 1 (LA-AC-AMD1-20260827) ────────────────────────────────────


def test_amendment1_primary_is_failrate_x_obstruction_with_escalation_note(
    marts: dict[str, pd.DataFrame], tmp_path: Path
) -> None:
    """개정 1 §1.1 — PRIMARY는 FailRate x obstruction 동시발생이며 격상 사유를 명시한다."""
    from analysis.eda.eda09_association_and_quadrant import run_eda09

    summary = json.loads(run_eda09(marts, tmp_path / "amd1").summary_json_path.read_text())
    assert summary["contract_amendment"] == "LA-AC-AMD1-20260827"

    primary = summary["primary_association"]
    assert primary["role"] == "primary_cooccurrence"
    assert "OlderRelevantKWCAGFailRate" in primary["metric"]
    assert "MPFED" not in primary["metric"]
    # 동시발생이며 인과가 아니라고 명시한다.
    assert "동시발생" in primary["interpretation_constraint"]
    assert "인과가 아니" in primary["interpretation_constraint"]
    # 격상 사유 — "원래 이걸 물으려 했다"로 쓰지 않는다.
    note = summary["primary_escalation_note"]
    assert "원래 SECONDARY급" in note
    assert "depth 축 소실" in note

    # 원 설계 depth 분석은 계약 PRIMARY가 아님이 명시된다.
    assert summary["retired_depth_associations"]["status"] == (
        "NOT_CONTRACT_PRIMARY_SINCE_AMENDMENT_1"
    )


def test_amendment1_secondary_is_kruskal_wallis_on_failrate(
    marts: dict[str, pd.DataFrame], tmp_path: Path
) -> None:
    """개정 1 §1.3 — SECONDARY는 KW(FailRate ~ archetype), group n>=5만."""
    from analysis.eda.eda09_association_and_quadrant import run_eda09
    from analysis.eda.statistics import MIN_GROUP_N_FOR_TEST

    summary = json.loads(run_eda09(marts, tmp_path / "amd1kw").summary_json_path.read_text())
    kw = summary["secondary_kruskal_wallis"]
    assert "OlderRelevantKWCAGFailRate ~ InteractionArchetype" in kw["metric"]
    assert kw["min_group_n_for_test"] == MIN_GROUP_N_FOR_TEST == 5
    # 남는 group이 2개 미만이면 omnibus를 돌리지 않는다.
    if len(kw["groups_used"]) < 2:
        assert kw["executed"] is False


def test_amendment1_reports_both_counts_and_third_exclusion_category(
    marts: dict[str, pd.DataFrame],
) -> None:
    """개정 1 §3·§4 — l0_analyzable_n 별도 계수 + 제외 3범주."""
    from analysis.eda.joint_validity import (
        EXCLUSION_CATEGORY,
        classify_joint_validity,
        joint_validity_summary,
    )

    summary = joint_validity_summary(classify_joint_validity(marts))

    # 두 계수 모두 보고되고, 서로 다른 것을 센다.
    assert "n_joint_valid" in summary
    assert "l0_analyzable_n" in summary
    assert "다른 것을 센다" in summary["counts_note"]

    # J3를 완화하지 않았으므로 l0_analyzable_n >= joint_valid_n 이다.
    assert summary["l0_analyzable_n"] >= summary["n_joint_valid"]

    # 제3범주가 신설되고 3범주로 분해된다.
    assert EXCLUSION_CATEGORY["L1_NOT_ATTEMPTED_GUARD"] == "OUR_TOOL_CONSTRAINT"
    assert EXCLUSION_CATEGORY["GATE_REACHED_MPFED_NULL"] == "TARGET_PROPERTY"
    assert EXCLUSION_CATEGORY["TRANSPORT_FAILURE"] == "OUR_CIRCUMSTANCE"
    assert set(summary["excluded_by_category"]) == {
        "OUR_CIRCUMSTANCE",
        "TARGET_PROPERTY",
        "OUR_TOOL_CONSTRAINT",
    }
    # 가드 표시가 없으면 0건이 "가드가 없었다"로 읽히지 않게 경고한다.
    if not summary["guard_marker_columns_present"]:
        assert "산출되지 않았다" in summary["guard_marker_note"]


def test_amendment1_depth_axis_reported_as_result(marts: dict[str, pd.DataFrame]) -> None:
    """개정 1 §2 — depth 축 산출 실패를 결과로 보고하고 서술 제약을 싣는다."""
    from analysis.eda.depth_axis import depth_axis_report

    report = depth_axis_report(marts)
    assert "mpfed_available_n" in report
    assert set(report["by_reason"]) == {
        "guard_blocked_pre_scout",
        "gate_kind_undetermined",
        "scout_no_signal",
        "endpoint_not_reached",
    }
    assert "e6b_fired_count" in report
    # 우리 도구의 도달 한계이지 사용자의 도달 한계가 아니다.
    assert "우리 도구의 도달 한계" in report["narrative_constraint"]
    assert "고령자가 대표기능에 도달할 수 없다" in report["narrative_constraint"]


# ── 배치 결과에서 수집 마커 파생 (수집기 무변경) ─────────────────────────

E000_BATCHES = (
    "/home/sieg/projects-wsl/ProjectFinal/.agent_worktrees/"
    "claude_b_e000_real/artifacts/e000_fast_real/batches"
)


def test_batch_markers_reproduce_e000_actuals() -> None:
    """E000 실측 재현 — 이 경로가 작동한다는 유일한 증거다.

    기대: guard_blocked 3(LOGIN/PURCHASE/SIGNUP) · AUTH_GATE 2(E-6b 발화) · UNRESOLVED 1.
    """
    import pytest as _pytest
    from analysis.eda.batch_results import derive_collection_markers

    if not Path(E000_BATCHES).is_dir():
        _pytest.skip("E000 배치 디렉터리가 이 환경에 없다")

    m = derive_collection_markers(E000_BATCHES)
    assert m["batches_found"] is True
    assert m["n_results"] == 6
    assert m["guard_blocked_n"] == 3
    assert m["guard_blocked_by_category"] == {"LOGIN": 1, "PURCHASE": 1, "SIGNUP": 1}
    assert m["e6b_fired_n"] == 2
    assert m["e6b_value_corroborated_n"] == 2
    assert m["outcome_counts"] == {
        "ACCOUNT_ACTION_BLOCKED": 3,
        "AUTH_GATE": 2,
        "UNRESOLVED": 1,
    }


def test_batch_not_found_is_unknown_not_zero(tmp_path: Path) -> None:
    """배치 미발견은 '확인 불가'이지 0건이 아니다."""
    import pandas as pd
    from analysis.eda.batch_results import derive_collection_markers
    from analysis.eda.depth_axis import depth_axis_report

    m = derive_collection_markers(tmp_path / "nope")
    assert m["batches_found"] is False
    assert m["guard_blocked_n"] is None
    assert m["e6b_fired_n"] is None
    assert "확인 불가" in m["note"]

    marts = {
        "fact_landing_observation": pd.DataFrame(),
        "fact_task_entry": pd.DataFrame([{"MPFED": None, "endpoint_status": "X"}]),
    }
    report = depth_axis_report(marts)
    assert report["by_reason"]["guard_blocked_pre_scout"] is None
    assert report["e6b_fired_count"] is None
    assert report["marker_source"] == "UNAVAILABLE"


def test_depth_axis_uses_batch_markers_when_available() -> None:
    """배치가 있으면 그 계수를 쓰고 출처를 명시한다."""
    import pandas as pd
    import pytest as _pytest
    from analysis.eda.depth_axis import depth_axis_report

    if not Path(E000_BATCHES).is_dir():
        _pytest.skip("E000 배치 디렉터리가 이 환경에 없다")

    marts = {
        "fact_landing_observation": pd.DataFrame(),
        "fact_task_entry": pd.DataFrame([{"MPFED": None, "endpoint_status": "AUTH_GATE_REACHED"}]),
    }
    report = depth_axis_report(marts, batches_dir=E000_BATCHES)
    assert report["marker_source"] == "BATCH_RESULTS"
    assert report["by_reason"]["guard_blocked_pre_scout"] == 3
    assert report["by_reason"]["gate_kind_undetermined"] == 2
    assert report["e6b_fired_count"] == 2


# ── 다중 배치 디렉터리(워커) 합산 ────────────────────────────────────────

E001_WORKER_BATCHES = [
    f"/home/sieg/projects-wsl/ProjectFinal/.agent_worktrees/"
    f"claude_b_e001_worker_{w}/artifacts/e001_w{w}/batches"
    for w in ("01", "02", "03", "04")
]


def test_multi_source_keeps_per_worker_provenance() -> None:
    """합산해도 워커별 출처를 잃지 않는다 — '특정 워커만 이상'을 볼 수 있어야 한다."""
    import pytest as _pytest
    from analysis.eda.batch_results import derive_collection_markers_multi

    present = [d for d in E001_WORKER_BATCHES if Path(d).is_dir()]
    if not present:
        _pytest.skip("E001 워커 배치 디렉터리가 이 환경에 없다")

    m = derive_collection_markers_multi(present)
    assert m["n_sources"] == len(present)
    by_source = {s["worker_id"]: s for s in m["by_source"]}
    # 워커 id가 경로에서 복원되고 소스별 계수가 따로 남는다.
    for worker_id, source in by_source.items():
        assert worker_id.startswith("e001_w")
        assert "guard_blocked_n" in source
        assert "chain_ok" in source
        assert source["batches_dir"].endswith("batches")
    # 합산은 소스별 합과 일치한다.
    if m["batches_found"]:
        assert m["guard_blocked_n"] == sum(s["guard_blocked_n"] for s in m["by_source"])


def test_hash_chains_verified_per_source_not_concatenated() -> None:
    """각 워커의 체인은 독립이다 — 이어붙이지 않고 소스별로 검증한다."""
    import pytest as _pytest
    from analysis.eda.batch_results import derive_collection_markers_multi

    present = [d for d in E001_WORKER_BATCHES if Path(d).is_dir()]
    if not present:
        _pytest.skip("E001 워커 배치 디렉터리가 이 환경에 없다")

    m = derive_collection_markers_multi(present)
    assert "chain_verified_all_sources" in m
    assert "소스(워커)별로 독립 검증" in m["chain_note"]
    # 워커가 각자 b0001부터 매기므로 체인이 이어붙여졌다면 전부 깨졌을 것이다.
    assert m["chain_verified_all_sources"] is True
    assert m["chain_errors"] == {}


def test_e000_and_e001_not_auto_merged() -> None:
    """collector가 다르므로 코호트 자동 합산은 거부된다 — 명시 플래그로만."""
    import pytest as _pytest
    from analysis.eda.batch_results import (
        BatchCollectionError,
        derive_collection_markers_multi,
    )

    present = [d for d in E001_WORKER_BATCHES if Path(d).is_dir()]
    if not present or not Path(E000_BATCHES).is_dir():
        _pytest.skip("E000/E001 배치 디렉터리가 이 환경에 없다")

    with _pytest.raises(BatchCollectionError, match="execution_scope"):
        derive_collection_markers_multi([*present, E000_BATCHES])

    merged = derive_collection_markers_multi([*present, E000_BATCHES], allow_cross_cohort=True)
    assert merged["cross_cohort_merged"] is True
    assert set(merged["cohorts"]) == {"E000_FAST", "E001_FULL"}
    # 코호트 간 재측정 target이 합산에 두 번 들어간다는 사실을 드러낸다.
    assert merged["cross_cohort_repeated_n"] >= 1
    assert "두 번" in merged["cross_cohort_note"]


def test_double_collection_within_cohort_is_an_error(tmp_path: Path) -> None:
    """같은 코호트에서 같은 target이 두 소스에 나오면 오류로 드러낸다."""
    import pytest as _pytest
    from analysis.eda.batch_results import (
        BatchCollectionError,
        derive_collection_markers_multi,
    )

    def _write(dirname: str, batch_id: str, targets: list[str]) -> Path:
        d = tmp_path / dirname / "batches"
        d.mkdir(parents=True)
        (d / f"batch_0001_{batch_id}.json").write_text(
            json.dumps(
                {
                    "batch_id": batch_id,
                    "batch_index": 1,
                    "batch_hash": "h1",
                    "previous_batch_hash": None,
                    "target_ids": targets,
                    "results": [],
                    "provenance": {"execution_scope": "E001_FULL"},
                }
            ),
            encoding="utf-8",
        )
        return d

    a = _write("wa", "b0001", ["tgt_1", "tgt_2"])
    b = _write("wb", "b0001", ["tgt_2", "tgt_3"])  # tgt_2 중복 = 이중 수집

    with _pytest.raises(BatchCollectionError, match="이중 수집"):
        derive_collection_markers_multi([a, b])

    # batch_id가 같은 것 자체는 정상이다(워커가 각자 b0001부터 매긴다).
    c = _write("wc", "b0001", ["tgt_4"])
    ok = derive_collection_markers_multi([a, c])
    assert ok["n_sources"] == 2
