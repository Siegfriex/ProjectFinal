"""통계 로직 — Phase 5 (`03_CRISP_DM_EXECUTION_PLAN_v2.0.md`) 오케스트레이터 지시가
요구한 구체 항목들. `common.py`의 일반 I/O·기술통계 헬퍼와 분리해, 실제 데이터가
들어왔을 때 재사용할 통계 방법론만 여기 모은다.

**전 함수 공통 원칙** (오케스트레이터 지시):

- 모든 association 결과는 `effect` + `n` + `missing_n` + `undetermined_n`을 항상
  병기한다 — p-value 하나만 내지 않는다.
- 절대 threshold(`depth >= N = bad`)를 도입하지 않는다 (`00 §7`).
- 표본이 부족하면(아래 tier) 검정을 **아예 실행하지 않고** 그 사실 자체를 결과에
  남긴다 — 억지로 돌려서 유의성을 만들어내지 않는다.

**synthetic 데이터로만 검증됐다.**
"""

from __future__ import annotations

from typing import Any, Literal

import numpy as np
import pandas as pd
from scipy import stats as scipy_stats
from statsmodels.stats.multitest import multipletests

# ── 표본 크기 tier ──────────────────────────────────────────────────────────
#: **Claude A(governor) 확정 규칙** (LA-TB-1630-20260827, 결과를 보기 전에 고정,
#: 사후 변경 금지) — archetype별 Kruskal-Wallis 포함 기준은 완료 관측 수(n,
#: `common.excess_depth`의 `archetype_n`과 같은 정의) `n >= 5`다. 이전에 오케스트레이터
#: 지시가 참고하라고 했던 연구 전체 표본 크기 tier(Green>=36/Yellow 28-35/
#: Red-usable 20-27/<20 PILOT 격하)는 **이 archetype-그룹 포함 가드에는 더 이상
#: 쓰지 않는다** — governor가 정확한 값을 못박았으므로 그 값을 그대로 쓴다.
#: `sample_size_tier()`는 연구 전체 표본 규모를 서술할 때만(이 가드와 별개로) 남겨둔다.
SampleSizeTier = Literal["GREEN", "YELLOW", "RED_USABLE", "PILOT_DOWNGRADE"]

_TIER_THRESHOLDS: tuple[tuple[int, SampleSizeTier], ...] = (
    (36, "GREEN"),
    (28, "YELLOW"),
    (20, "RED_USABLE"),
)
#: Kruskal-Wallis 가드가 archetype 그룹을 비교에 **포함**시키는 최소 완료 관측 수.
#: Claude A(governor) 확정값 — `common.EXCESS_DEPTH_INCLUDE_MIN_N`과 반드시 같은 값이어야
#: 한다(ExcessDepth가 산출되는 archetype과 Kruskal-Wallis에 들어가는 archetype이
#: 같은 n 정의를 공유하기 때문). 이 미만인 그룹은 비교에서 뺀다.
MIN_GROUP_N_FOR_TEST = 5


def sample_size_tier(n: int) -> SampleSizeTier:
    """연구 전체 표본 규모 서술용(참고 지표) — Kruskal-Wallis archetype 가드는
    `MIN_GROUP_N_FOR_TEST`(governor 확정 n>=5)를 쓴다, 이 tier가 아니다."""
    for threshold, tier in _TIER_THRESHOLDS:
        if n >= threshold:
            return tier
    return "PILOT_DOWNGRADE"


# ── Secondary association 변수 선택 — 사전등록(pre-registration) ─────────────
#: **Claude A(governor) 확정, 결과를 보기 전에 고정** (LA-TB-1630-20260827).
#: A0 §7이 secondary로 `Spearman(ExcessDepth, OverlayCoverage)` 또는 "더 완결된
#: obstruction 변수 1개"를 허용한다. 후보 4개 — `max_overlay_coverage` ·
#: `max_primary_action_occlusion`(둘 다 `fact_landing_observation`, L0) ·
#: `blocking_modal_count`(`fact_landing_observation`, L0) ·
#: `forced_dismissal_count`(`fact_task_entry`, **L1** — task 진입 자체가
#: 전제라 구조적으로 母집단이 더 좁다).
#:
#: **선택 기준은 결측 완결성이지 상관계수 크기가 아니다** — 상관이 큰 변수를
#: 고르면 그 자체가 p-hacking이다. 그래서 이 상수는 **데이터를 보기 전에**
#: 구조적 근거만으로 고정한다:
#:
#: 1. `forced_dismissal_count`는 `fact_task_entry`(L1) 소속이라 task 진입 자체가
#:    없으면(L1 미시도/UNRESOLVED) 존재하지 않는다 — 4개 후보 중 母집단이 가장
#:    좁아 결측이 구조적으로 가장 크다. **탈락 1순위.**
#: 2. `max_primary_action_occlusion`은 "주요 액션"이 식별 가능해야 값이 성립한다
#:    — 순수 콘텐츠형 랜딩처럼 주요 액션 자체가 없는 서비스에서는 개념적으로
#:    정의되지 않는 결측이 추가로 생긴다. **탈락 2순위.**
#: 3. `max_overlay_coverage`·`blocking_modal_count`는 둘 다 `fact_landing_observation`
#:    (L0)에 속하고, `MEASURED`인 모든 관측에 대해 무조건 계산되는 값이다
#:    (interrupt 후보가 0건이면 0으로 채워진다 — NULL이 아니다). 구조적으로
#:    결측 사유가 없는 이 둘 중, `max_overlay_coverage`는 A0 §7이 이미 이름으로
#:    지정한 변수이므로 SSOT와의 일관성을 위해 이것을 **1순위**로 확정한다.
#:    `blocking_modal_count`는 사전등록된 **fallback**이다 — 실제 E001 데이터로
#:    `max_overlay_coverage`의 결측률이 예상보다 뚜렷이 높다고 확인되면(관찰 후
#:    "재확인"만 하되, 이미 계산된 secondary 결과를 상관 크기를 보고 바꾸지 않는다,
#:    governor 지시) fallback으로 전환한다 — 이 전환 자체도 결측률 재확인의
#:    결과여야지 상관계수를 보고 정하면 안 된다.
SECONDARY_ASSOCIATION_VARIABLE = "max_overlay_coverage"
SECONDARY_ASSOCIATION_VARIABLE_FALLBACK = "blocking_modal_count"

#: **동률 시 사전 고정 우선순위** (Claude A governor 확정 §4.4 — 계약에 적힌
#: 나열 순서 그대로: `OverlayCoverage` → `PrimaryActionOcclusion` →
#: `blocking_modal_count` → `forced_dismissal_count`).
#:
#: 결측률이 같을 때 **상관계수를 보고 고르면 그 순간 p-hacking이다.** 그래서
#: tie-break는 데이터와 무관한 이 고정 순서로만 깬다. 이 튜플의 순서 자체가
#: 사전등록물이며, 결과를 본 뒤 바꾸지 않는다.
SECONDARY_ASSOCIATION_PRIORITY: tuple[str, ...] = (
    "max_overlay_coverage",
    "max_primary_action_occlusion",
    "blocking_modal_count",
    "forced_dismissal_count",
)

#: 후보 4종 전부 — **선택된 것만이 아니라 전부의 결측률을 산출물에 기록한다**
#: (governor 지시: 선택된 것만 적으면 선택 자체가 검증 불가능해진다).
SECONDARY_ASSOCIATION_CANDIDATES: tuple[str, ...] = SECONDARY_ASSOCIATION_PRIORITY


def select_secondary_association_variable(
    missing_rates: dict[str, float | None],
) -> dict[str, Any]:
    """§4.4 secondary 변수 자동선택 — **결측률 최소, 동률이면 사전 고정 우선순위**.

    상관계수는 이 함수에 입력조차 되지 않는다 — 구조적으로 p-hacking이 불가능하다.
    선택 결과와 함께 **후보 4종 전부의 결측률**과 tie-break 발동 여부를 돌려줘서,
    선택 자체가 산출물에서 재검증 가능하게 한다.

    결측률이 `None`인(=계산할 표본조차 없던) 후보는 선택 대상에서 제외한다.
    전부 `None`이면 사전등록 1순위(`SECONDARY_ASSOCIATION_VARIABLE`)로 되돌아간다.
    """
    ranked = [
        (name, missing_rates.get(name))
        for name in SECONDARY_ASSOCIATION_PRIORITY
        if missing_rates.get(name) is not None
    ]
    if not ranked:
        return {
            "selected": SECONDARY_ASSOCIATION_VARIABLE,
            "selection_rule": "no_candidate_measurable_fell_back_to_preregistered_first",
            "candidate_missing_rates": dict(missing_rates),
            "priority_order": list(SECONDARY_ASSOCIATION_PRIORITY),
            "tie_break_applied": False,
            "tied_candidates": [],
        }

    best_rate = min(rate for _, rate in ranked)  # type: ignore[type-var]
    tied = [name for name, rate in ranked if rate == best_rate]
    # 우선순위 튜플에서 먼저 나오는 것을 고른다 — `ranked`가 이미 그 순서라 첫 원소다.
    selected = tied[0]
    return {
        "selected": selected,
        "selection_rule": (
            "lowest_missing_rate_then_preregistered_priority_order "
            "(상관계수는 선택에 입력되지 않는다 — p-hacking 구조적 차단)"
        ),
        "candidate_missing_rates": dict(missing_rates),
        "priority_order": list(SECONDARY_ASSOCIATION_PRIORITY),
        "selected_missing_rate": best_rate,
        "tie_break_applied": len(tied) > 1,
        "tied_candidates": tied,
    }


# ── Association — primary/secondary, effect+N+missing_N+UNDET_N 병기 ─────────

#: **Research Director 확정** (LA-TB-1630-20260827, 동결 — 결과 보고를 이유로
#: 바꾸지 않는다). pairwise-complete n이 이 미만이면 그 계수는 exploratory
#: descriptive로만 표시하고 p-value를 headline으로 쓰지 않는다.
SPEARMAN_HEADLINE_MIN_N = 10

#: 이 n 미만이면 asymptotic(t-분포 근사) 대신 permutation 기반 p-value를 쓴다 —
#: 표본이 작을수록 근사가 부정확해지기 때문이다. `p_value_method` 필드로 어느
#: 쪽을 썼는지 항상 artifact에 남긴다.
SPEARMAN_PERMUTATION_MAX_N = 30
_PERMUTATION_RESAMPLES = 9999
_PERMUTATION_RNG_SEED = 20260827  # 결정적 — synthetic 검증 재현성.


def _spearman_with_method(x: pd.Series, y: pd.Series) -> tuple[float, float, str]:
    """tie-aware Spearman(순위 상관은 scipy가 기본으로 평균순위 tie-break를 쓴다 —
    이산값이 많은 MPFED류에도 그대로 유효하다). n이 작으면 permutation p-value로
    바꾼다 — asymptotic 근사가 작은 n에서 부정확해서다. 어느 쪽을 썼는지 세 번째
    반환값(`p_value_method`)에 남긴다.
    """
    n = len(x)
    if n < SPEARMAN_PERMUTATION_MAX_N:

        def _stat(a: np.ndarray, b: np.ndarray) -> float:
            return scipy_stats.spearmanr(a, b).statistic

        rho = float(_stat(x.to_numpy(), y.to_numpy()))
        result = scipy_stats.permutation_test(
            (x.to_numpy(),),
            lambda a: _stat(a, y.to_numpy()),
            permutation_type="pairings",
            n_resamples=_PERMUTATION_RESAMPLES,
            random_state=_PERMUTATION_RNG_SEED,
            alternative="two-sided",
        )
        return rho, float(result.pvalue), "permutation"
    rho, pvalue = scipy_stats.spearmanr(x, y)
    return float(rho), float(pvalue), "asymptotic_t"


# ── 결론의 방향 = Spearman rho 부호. 두 민감도 축에서 각각 판정 ────────────────
#: **Claude A(governor) §2.1 조작화 확정** (LA-TB-1630-20260827).
DIRECTION_DEFINITION = (
    "결론의 방향 = 해당 association의 Spearman rho 부호. "
    "두 민감도 축(표본 구성 · 측정 불확실성) 각각에서 판정."
)

#: 부호 안정성을 재는 두 축. 하나만 쓰면 "표본을 흔들어도 안 뒤집힌다"까지만
#: 말하고 "측정 불확실성(UNDETERMINED)을 흔들어도 안 뒤집힌다"는 말하지 못한다.
SIGN_STABILITY_AXES: tuple[str, ...] = ("sample_composition", "measurement_uncertainty")

#: 축별 판정값 의미:
#:   True            — bound/부분표본 전부에서 부호 유지
#:   False           — 어느 한 곳에서라도 부호가 뒤집힘
#:   None            — 적용 대상인데 평가 불가(표본 부족 등) → 확인 안 됨으로 취급, 강등
#:   "NOT_APPLICABLE"— 그 축이 이 association에 구조적으로 적용되지 않음(강등 없음).
#:                     예: secondary(ExcessDepth × obstruction)는 Y가 UNDETERMINED에
#:                     의존하지 않으므로 measurement_uncertainty 축이 없다.
SignStability = bool | None | str


def _axis_ok(value: SignStability) -> bool:
    """그 축이 GRADE B를 막지 않는가. `True`와 `NOT_APPLICABLE`만 통과다."""
    return value is True or value == "NOT_APPLICABLE"


def resolve_sign_flip_axis(
    *, sample_composition: SignStability, measurement_uncertainty: SignStability
) -> dict[str, Any]:
    """어느 축에서 부호가 뒤집혔는지 판정한다 (governor 지시 3항).

    `sign_flip_axis`는 계약이 명명한 3값(`"sample_composition"` ·
    `"measurement_uncertainty"` · `null`)만 갖는다. 두 축이 동시에 뒤집힌 경우엔
    측정 불확실성 쪽을 대표값으로 올리고(더 근본적인 결손이다), 전체 목록은
    `sign_flip_axes`에 남긴다 — 정보를 잃지 않기 위해서다.
    """
    flipped = []
    if sample_composition is False:
        flipped.append("sample_composition")
    if measurement_uncertainty is False:
        flipped.append("measurement_uncertainty")

    if "measurement_uncertainty" in flipped:
        primary_axis: str | None = "measurement_uncertainty"
    elif "sample_composition" in flipped:
        primary_axis = "sample_composition"
    else:
        primary_axis = None

    unevaluated = [
        axis
        for axis, value in (
            ("sample_composition", sample_composition),
            ("measurement_uncertainty", measurement_uncertainty),
        )
        if value is None
    ]

    return {
        "definition": DIRECTION_DEFINITION,
        "by_axis": {
            "sample_composition": sample_composition,
            "measurement_uncertainty": measurement_uncertainty,
        },
        "sign_flip_axis": primary_axis,
        "sign_flip_axes": flipped,
        "unevaluated_axes": unevaluated,
        "both_axes_preserved": _axis_ok(sample_composition) and _axis_ok(measurement_uncertainty),
    }


def assign_association_claim_grade(
    *,
    n: int,
    executed: bool,
    sample_composition: SignStability,
    measurement_uncertainty: SignStability,
) -> str:
    """**Research Director 확정 claim grade + Claude A §2.1 두 축 강등 규칙**
    (LA-TB-1630-20260827).

    association/inferential 결과는 절대 `GRADE A`를 받지 않는다(A는 정의·
    기술통계·직접 관측 전용) — association은 `B`(robust) 또는 `C`(exploratory)
    또는 `UNSUPPORTED`뿐이다. headline은 A 또는 robust B만 허용, C는 반드시
    exploratory로 명시한다(이 등급 문자열 자체가 그 명시다).

    - `UNSUPPORTED`: 실행 자체가 안 됐다(표본 부족으로 상관 계산 불가).
    - `C`: `n < SPEARMAN_HEADLINE_MIN_N`(=10)이거나, **두 민감도 축(표본 구성 ·
      측정 불확실성) 중 어느 하나라도** 부호가 뒤집혔거나 확인되지 않았다.
    - `B`: `n >= 10`이고 **두 축 모두** 부호가 유지됐다(또는 그 축이 구조적으로
      적용되지 않는다).
    """
    if not executed:
        return "UNSUPPORTED"
    if n < SPEARMAN_HEADLINE_MIN_N:
        return "C"
    if not (_axis_ok(sample_composition) and _axis_ok(measurement_uncertainty)):
        return "C"
    return "B"


def sign_preserved_across_bounds(
    x: pd.Series,
    y_point: pd.Series,
    y_lower: pd.Series,
    y_upper: pd.Series,
) -> SignStability:
    """**측정 불확실성 축** — UNDETERMINED lower/upper bound 각각에서 Spearman rho
    부호가 점추정과 같은지 판정한다 (ANALYSIS_CONTRACT §2.1).

    `y_lower` = UNDETERMINED를 전부 PASS로 본 FailRate(최소),
    `y_upper` = 전부 FAIL로 본 FailRate(최대). 두 bound 모두에서 부호가 유지돼야
    `True`다 — 한쪽이라도 뒤집히면 "측정 불확실성 안에서 결론의 방향이 바뀐다"는
    뜻이므로 `False`다.

    점추정 rho가 0이거나 유한하지 않으면 부호 자체가 정의되지 않아 `None`(확인 불가).
    """
    frame = pd.DataFrame(
        {
            "x": pd.to_numeric(x, errors="coerce"),
            "point": pd.to_numeric(y_point, errors="coerce"),
            "lower": pd.to_numeric(y_lower, errors="coerce"),
            "upper": pd.to_numeric(y_upper, errors="coerce"),
        }
    ).dropna()
    if len(frame) < 3:
        return None

    point_rho = scipy_stats.spearmanr(frame["x"], frame["point"]).statistic
    if not np.isfinite(point_rho) or point_rho == 0:
        return None
    point_sign = point_rho > 0

    for bound in ("lower", "upper"):
        rho = scipy_stats.spearmanr(frame["x"], frame[bound]).statistic
        if not np.isfinite(rho):
            return None
        # bound에서 rho=0이면 부호가 사라진 것이므로 "유지됐다"고 말할 수 없다.
        if rho == 0 or (rho > 0) != point_sign:
            return False
    return True


def association_result(
    x: pd.Series,
    y: pd.Series,
    *,
    x_name: str,
    y_name: str,
    role: str,
    assumption: str,
    undetermined_n: int = 0,
    interpretation_constraint: str | None = None,
    sample_composition: SignStability = None,
    measurement_uncertainty: SignStability = None,
) -> dict[str, Any]:
    """Spearman association 결과를 `effect`+`n`+`missing_n`+`undetermined_n`+
    `claim_grade`+`sign_stability` 구조로 낸다.

    p-value만 내지 않는다 — `effect`에 rho·p_value·`p_value_method`를 함께 담고,
    `n`(짝 지어 쓸 수 있었던 표본)과 `missing_n`(둘 중 하나라도 결측이라 뺀 표본)을
    구분해 명시한다. `undetermined_n`은 호출자가 넘긴다 — 이 값이 association의
    입력 자체(예: OlderRelevantKWCAGFailRate 분자·분모)에서 이미 제외된
    UNDETERMINED 건수이며, association 함수 스스로는 verdict_state를 모르기 때문이다.

    `sample_composition` / `measurement_uncertainty` — **결론의 방향(= Spearman rho
    부호)을 두 민감도 축에서 각각 판정한 결과** (Claude A governor §2.1 확정).
    전자는 leave-one-archetype-out(표본 구성), 후자는 UNDETERMINED lower/upper
    bound(측정 불확실성)다. **어느 한 축이라도 뒤집히면 `claim_grade`가 C로
    강등된다** — 뒤집힌 축은 `sign_stability.sign_flip_axis`에 명시된다.

    `n < SPEARMAN_HEADLINE_MIN_N`(=10, Research Director 확정)이면 `headline_eligible
    =False`이고 `claim_grade="C"`(exploratory) — p-value를 headline으로 인용하지 않는다.
    """
    x_num = pd.to_numeric(x, errors="coerce")
    y_num = pd.to_numeric(y, errors="coerce")
    frame = pd.DataFrame({"x": x_num, "y": y_num})
    total = len(frame)
    paired = frame.dropna()
    n = len(paired)
    missing_n = total - n

    effect: dict[str, float | str | None] = {
        "spearman_rho": None,
        "p_value": None,
        "p_value_method": None,
    }
    executed = n >= 3
    if executed:
        rho, pvalue, method = _spearman_with_method(paired["x"], paired["y"])
        effect = {"spearman_rho": rho, "p_value": pvalue, "p_value_method": method}

    claim_grade = assign_association_claim_grade(
        n=n,
        executed=executed,
        sample_composition=sample_composition,
        measurement_uncertainty=measurement_uncertainty,
    )
    sign_stability = resolve_sign_flip_axis(
        sample_composition=sample_composition, measurement_uncertainty=measurement_uncertainty
    )

    return {
        "role": role,  # "primary" | "primary_structure_adjusted" | "secondary"
        "metric": f"Spearman({x_name}, {y_name})",
        "effect": effect,
        "n": n,
        "missing_n": missing_n,
        "undetermined_n": undetermined_n,
        "assumption": assumption,
        "executed": executed,
        "reason_not_executed": None
        if executed
        else f"짝지어진 표본 n={n} < 3 — 상관을 계산할 수 없다",
        # headline은 A 또는 **robust B**만 허용한다 — association은 A를 못 받으므로
        # 사실상 grade B일 때만 headline이다. n>=10만으로는 부족하다: 두 민감도 축
        # 중 하나라도 뒤집히면 grade가 C로 내려가고 headline 자격도 함께 사라진다.
        "headline_eligible": claim_grade == "B",
        "claim_grade": claim_grade,
        "interpretation_constraint": interpretation_constraint,
        # governor §2.1 — 두 축 각각의 판정 + 어느 축에서 뒤집혔는지.
        "sign_stability": sign_stability,
        "sign_flip_axis": sign_stability["sign_flip_axis"],
    }


def older_relevant_kwcag_fail_rate(criterion: pd.DataFrame, landing: pd.DataFrame) -> pd.DataFrame:
    """`web_target_id`별 OlderRelevantKWCAGFailRate — **Research Director 확정
    정의** (LA-TB-1630-20260827, 동결):

    ```
    EligibleOlderRelevant_i = older-relevant criterion 중 해당 observation에서
                               final_status ∈ {PASS, FAIL}인 것의 수
    FailOlderRelevant_i     = 그 중 FAIL 수
    OlderRelevantKWCAGFailRate_i = FailOlderRelevant_i / EligibleOlderRelevant_i
    ```

    `older_relevance ∈ {VISION, MOTOR, COGNITIVE_NAVIGATION}`(= `OTHER`가 아닌 기준)
    만 분자·분모에 넣는다 — "고령층과 무관한 기준"까지 섞으면 metric의 이름이
    거짓이 된다.

    **`EligibleOlderRelevant_i = 0`이면 `fail_rate = NULL`이다 — 0으로 대체하지
    않는다**(0건을 0%로 읽으면 "전부 통과"와 "잴 수 있는 게 없었다"이 같아진다).
    `UNDETERMINED`는 분모(`EligibleOlderRelevant`)에서 **제외**하되(이전 skeleton
    설계와 달리 더는 분모에 남기지 않는다 — Director가 이 버전으로 동결했다)
    `n_undetermined`·`undetermined_rate`를 **항상 별도 병기**한다. `NA`(적용기회
    없음)와 `UNDETERMINED`(판정 불가)는 서로 다른 사실이라 섞지 않는다.

    `fail_rate_lower_bound`/`fail_rate_upper_bound` — robustness bound. lower는
    UNDETERMINED를 전부 PASS로(best case, fail이 적어지는 방향), upper는 전부
    FAIL로(worst case) 가정해 재계산한다. **점추정 하나로 접지 않는다** —
    UNDETERMINED가 있는 서비스는 이 두 경계를 항상 함께 본다.
    """
    empty_columns = [
        "web_target_id",
        "fail_rate",
        "fail_rate_lower_bound",
        "fail_rate_upper_bound",
        "n_eligible",
        "n_fail",
        "n_undetermined",
        "undetermined_rate",
        "n_na_excluded",
    ]
    if criterion.empty or landing.empty:
        return pd.DataFrame(columns=empty_columns)

    obs_to_target = landing.set_index("observation_id")["web_target_id"]
    crit = criterion.copy()
    crit["web_target_id"] = crit["observation_id"].map(obs_to_target)
    older_relevant = crit[crit["older_relevance"].astype(str) != "OTHER"].copy()

    rows: list[dict[str, Any]] = []
    for web_target_id, group in older_relevant.groupby("web_target_id"):
        final = group["final_status"].astype(str)
        eligible = final[final.isin(["PASS", "FAIL"])]
        n_eligible = len(eligible)
        n_fail = int((eligible == "FAIL").sum())
        n_undetermined = int((final == "UNDETERMINED").sum())
        n_na_excluded = int((final == "NA").sum())
        # NA는 분모(applicable) 밖이다 — applicable = eligible(PASS/FAIL) + UNDETERMINED.
        n_applicable_excl_na = n_eligible + n_undetermined

        fail_rate = round(n_fail / n_eligible, 4) if n_eligible else None  # 0으로 대체하지 않는다.
        undetermined_rate = (
            round(n_undetermined / n_applicable_excl_na, 4) if n_applicable_excl_na else None
        )
        # robustness bound — best/worst case로 UNDETERMINED를 재배정.
        lower_denom = n_eligible + n_undetermined  # PASS로 가정해도 분모에는 들어간다.
        fail_rate_lower = round(n_fail / lower_denom, 4) if lower_denom else None
        fail_rate_upper = round((n_fail + n_undetermined) / lower_denom, 4) if lower_denom else None

        rows.append(
            {
                "web_target_id": web_target_id,
                "fail_rate": fail_rate,
                "fail_rate_lower_bound": fail_rate_lower,
                "fail_rate_upper_bound": fail_rate_upper,
                "n_eligible": n_eligible,
                "n_fail": n_fail,
                "n_undetermined": n_undetermined,
                "undetermined_rate": undetermined_rate,
                "n_na_excluded": n_na_excluded,
            }
        )
    return pd.DataFrame(rows)


# ── Kruskal-Wallis — 표본 크기 가드 ────────────────────────────────────────


def kruskal_wallis_gate(groups: dict[str, pd.Series]) -> dict[str, Any]:
    """archetype별 그룹을 비교하되, **N이 실제로 충분할 때만** 검정을 실행한다.

    규칙: `MIN_GROUP_N_FOR_TEST=20`(Red-usable 하한) 미만인 그룹은 비교에서
    아예 뺀다(그 그룹만 표본 부족이라고 전체 검정을 죽이지 않는다). 남은 그룹이
    2개 미만이면 검정을 실행하지 않는다. tier는 **실제로 검정에 쓰인 그룹들 중
    최소 N**을 기준으로 매긴다. `PILOT_DOWNGRADE`면 그 사실을 결과에 남기고
    검정을 실행하지 않는다 — 억지로 돌리지 않는다.
    """
    sizes = {
        str(k): int(pd.to_numeric(v, errors="coerce").dropna().shape[0]) for k, v in groups.items()
    }
    qualifying = {k: v for k, v in groups.items() if sizes[str(k)] >= MIN_GROUP_N_FOR_TEST}
    dropped = {k: n for k, n in sizes.items() if n < MIN_GROUP_N_FOR_TEST}

    result: dict[str, Any] = {
        "group_sizes": sizes,
        "dropped_groups_below_min_n": dropped,
        "min_group_n_for_test": MIN_GROUP_N_FOR_TEST,
        "groups_used": list(qualifying.keys()),
        "tier": "PILOT_DOWNGRADE",
        "executed": False,
        "statistic": None,
        "p_value": None,
        "reason_not_executed": None,
    }

    if len(qualifying) < 2:
        result["reason_not_executed"] = (
            f"N>={MIN_GROUP_N_FOR_TEST}인 그룹이 {len(qualifying)}개뿐이다 (2개 이상 필요) — "
            "PILOT 격하, 검정을 실행하지 않는다"
        )
        return result

    used_min_n = min(sizes[str(k)] for k in qualifying)
    result["tier"] = sample_size_tier(used_min_n)

    values = [pd.to_numeric(v, errors="coerce").dropna() for v in qualifying.values()]
    stat, pvalue = scipy_stats.kruskal(*values)
    result["executed"] = True
    result["statistic"] = float(stat)
    result["p_value"] = float(pvalue)
    return result


def kruskal_wallis_pairwise_dunn(
    groups: dict[str, pd.Series], *, alpha: float = 0.05
) -> dict[str, Any]:
    """**시간 남을 때만** — pairwise Dunn's test + Benjamini-Hochberg FDR.

    기본 실행 경로(`kruskal_wallis_gate`)와 분리된 별도 함수다. `00 §14`가
    금지하는 결론 유도를 피하려면, 사후검정은 Kruskal-Wallis 자체가 유의했을
    때만(호출자가 그 판단을 한 뒤) 불러야 한다 — 이 함수는 그 판단을 강제하지
    않는다(호출자 책임), 다만 최소 N 가드는 `kruskal_wallis_gate`와 동일하게 적용한다.
    """
    sizes = {
        str(k): int(pd.to_numeric(v, errors="coerce").dropna().shape[0]) for k, v in groups.items()
    }
    qualifying = {
        str(k): pd.to_numeric(v, errors="coerce").dropna()
        for k, v in groups.items()
        if sizes[str(k)] >= MIN_GROUP_N_FOR_TEST
    }
    keys = list(qualifying.keys())
    if len(keys) < 2:
        return {
            "executed": False,
            "reason_not_executed": f"N>={MIN_GROUP_N_FOR_TEST}인 그룹이 {len(keys)}개뿐이다",
            "pairs": [],
        }

    # 전체 풀링 순위 (Dunn's test 표준 절차) — 동순위는 평균 순위로 처리.
    pooled = pd.concat(qualifying.values())
    ranks = pd.Series(scipy_stats.rankdata(pooled), index=pooled.index)
    n_total = len(pooled)
    # 동순위 보정항.
    _, counts = np.unique(pooled.to_numpy(), return_counts=True)
    tie_correction = float(np.sum(counts**3 - counts))

    mean_ranks: dict[str, float] = {}
    offset = 0
    for key, series in qualifying.items():
        chunk = ranks.iloc[offset : offset + len(series)]
        mean_ranks[key] = float(chunk.mean())
        offset += len(series)

    pairs: list[dict[str, Any]] = []
    raw_pvalues: list[float] = []
    for i in range(len(keys)):
        for j in range(i + 1, len(keys)):
            a, b = keys[i], keys[j]
            n_a, n_b = sizes[a], sizes[b]
            sigma2 = (n_total * (n_total + 1) / 12 - tie_correction / (12 * (n_total - 1))) * (
                1 / n_a + 1 / n_b
            )
            se = float(np.sqrt(sigma2)) if sigma2 > 0 else 0.0
            z = (mean_ranks[a] - mean_ranks[b]) / se if se > 0 else 0.0
            pvalue = float(2 * (1 - scipy_stats.norm.cdf(abs(z))))
            pairs.append(
                {
                    "group_a": a,
                    "group_b": b,
                    "n_a": n_a,
                    "n_b": n_b,
                    "z": float(z),
                    "p_value_raw": pvalue,
                }
            )
            raw_pvalues.append(pvalue)

    if raw_pvalues:
        rejected, fdr_pvalues, _, _ = multipletests(raw_pvalues, alpha=alpha, method="fdr_bh")
        for pair, rej, p_fdr in zip(pairs, rejected, fdr_pvalues, strict=True):
            pair["p_value_fdr_bh"] = float(p_fdr)
            pair["significant_at_alpha"] = bool(rej)

    return {"executed": True, "alpha": alpha, "mean_ranks": mean_ranks, "pairs": pairs}


# ── Quadrant 분류 — median-zero fallback ──────────────────────────────────


def classify_quadrant(
    frame: pd.DataFrame,
    *,
    x_col: str,
    y_col: str,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """X(ExcessDepth) × Y(OlderRelevantKWCAGFailRate) quadrant 분류.

    **핵심 요구사항**: Y의 median이 0이면(= 서비스 절반 이상이 fail 0건이면)
    median split을 강제하지 않는다. `median(Y)=0`인 상태에서 median split을
    쓰면 "median보다 큼"이 곧 "fail이 1건이라도 있음"과 같아져 quadrant가 사실상
    `barrier_present`/`barrier_absent` 이분법으로 붕괴하면서도 median split이라고
    주장하게 된다 — 그 자체가 은폐다. 대신 **명시적으로** binary 모드로 전환한다.

    Y median split 조건: `median(Y) > 0`. 그 외에는 barrier_absent(Y==0) /
    barrier_present(Y>0) 이분법. X(ExcessDepth)는 항상 median split이다(음수가
    자연스러운 척도라 0-fallback이 적용되지 않는다).

    Quadrant 정의(둘 다 median split일 때 기준, `00 §7` 절대 threshold 없이
    표본 내부 상대 위치로만 나눈다):

    - A = low X · low Y  (진입깊이 낮음 · 접근성 실패 낮음)
    - B = high X · low Y (진입깊이 높음 · 접근성 실패 낮음)
    - C = low X · high Y (진입깊이 낮음 · 접근성 실패 높음)
    - D = high X · high Y (둘 다 높음 — 이중 부담)

    돌려주는 두 번째 값(`classification_rule`)을 artifact에 그대로 기록한다 —
    "이번 실행이 median split이었는지 barrier binary였는지"가 나중에 반드시
    재구성 가능해야 한다.
    """
    work = frame.copy()
    x = pd.to_numeric(work[x_col], errors="coerce")
    y = pd.to_numeric(work[y_col], errors="coerce")
    work["_x"] = x
    work["_y"] = y
    valid = work.dropna(subset=["_x", "_y"])

    x_median = float(valid["_x"].median()) if not valid.empty else None
    y_median = float(valid["_y"].median()) if not valid.empty else None

    y_mode: str
    if y_median is not None and y_median > 0:
        y_mode = "median_split"
        y_high = valid["_y"] > y_median
    else:
        # median-zero fallback — 강제 median split 금지.
        y_mode = "barrier_binary"
        y_high = valid["_y"] > 0

    x_high = valid["_x"] > x_median if x_median is not None else pd.Series(dtype=bool)

    quadrant = pd.Series(index=valid.index, dtype=object)
    quadrant[(~x_high) & (~y_high)] = "A_low_depth_low_fail"
    quadrant[(x_high) & (~y_high)] = "B_high_depth_low_fail"
    quadrant[(~x_high) & (y_high)] = "C_low_depth_high_fail"
    quadrant[(x_high) & (y_high)] = "D_high_depth_high_fail"

    work["quadrant"] = None
    work.loc[valid.index, "quadrant"] = quadrant

    counts = quadrant.value_counts(dropna=False).to_dict()
    classification_rule = {
        "x_col": x_col,
        "y_col": y_col,
        "x_split": "median_split",
        "x_median": x_median,
        "y_split": y_mode,
        "y_median": y_median,
        "y_median_is_zero_fallback_triggered": y_mode == "barrier_binary",
        "n_classified": len(valid),
        "n_excluded_missing": int(len(work) - len(valid)),
        "quadrant_counts": {str(k): int(v) for k, v in counts.items()},
    }
    return work, classification_rule
