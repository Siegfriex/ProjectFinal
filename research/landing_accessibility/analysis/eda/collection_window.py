"""수집 시각 구간 분해 — **연장분기 의무 1·2·4** (Claude A 확정).

## 왜 필요한가

E001 수집이 늦게 시작되면 새 target 중단이 14:00까지 연장된다. 그런데
**14:00 AI cutoff 이후에 수집된 관측은 대상의 성질 때문이 아니라 처리 순서
때문에 AI 판정을 덜 받는다** — cutoff 뒤에는 AI review cascade가 돌지 못해
`UNDETERMINED`가 남을 확률이 구조적으로 높아진다. 이것은 **이질적 측정**이며
숨기면 안 된다.

그래서 이 모듈은 관측을 `sealed_at`(evidence run이 봉인된 시각) 기준으로
cutoff 전/후 구간으로 나누고:

- **의무 1** — 구간별 `undetermined_rate`를 분해한다.
- **의무 2** — 구간 간 차이가 유의하면 그 차이를 **"처리 순서에 기인"**으로
  명시한다(대상의 성질로 읽히지 않게).
- **의무 4** — 구간별 `InteractionArchetype` 분포를 **실제로 계산**한다.
  interleave 순서 때문에 archetype 편향은 없을 것으로 **예상**되지만,
  **확인하지 않고 단정하지 않는다.** 표본이 부족하면 "없다"가 아니라
  `NOT_ENOUGH_DATA`를 낸다.

## 시각 원천

`sealed_at`은 `EvidenceRun.run_record()`가 run마다 기록해 `run.json`에 들어간다
(`engine/evidence.py:254`). grain은 run이며 target 1건에 대응한다. `started_at`은
없으므로 `sealed_at` 기준으로 구간을 나눈다.

**synthetic 데이터로만 검증됐다.**
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

import pandas as pd
from scipy import stats as scipy_stats

#: AI cutoff — 이 시각 **이후** 봉인된 run은 AI 판정을 덜 받는다.
#: `LA-TB-1630-20260827` 타임박스가 고정한 값(14:00 KST). 결과를 보고 바꾸지 않는다.
AI_CUTOFF_ISO = "2026-08-27T14:00:00+09:00"

WINDOW_PRE = "PRE_AI_CUTOFF"
WINDOW_POST = "POST_AI_CUTOFF"
WINDOW_UNKNOWN = "SEALED_AT_MISSING"

#: 구간 비교를 실행할 최소 표본 — 이 미만이면 검정하지 않고 `NOT_ENOUGH_DATA`.
#: 결과를 보기 전에 고정한다.
MIN_PER_WINDOW_FOR_TEST = 5
WINDOW_TEST_ALPHA = 0.05

#: archetype 편향 카이제곱을 실행할 최소 기대빈도. 이 미만이면 근사가 무너지므로
#: 검정하지 않는다 — 그때 "편향 없음"이라고 쓰지 않는다.
MIN_EXPECTED_CELL = 5


def _parse_iso(value: Any) -> datetime | None:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    text = str(value).strip()
    if not text or text.lower() in {"nan", "none", "nat"}:
        return None
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None


def sealed_at_by_observation(run_records: list[dict[str, Any]]) -> dict[str, str]:
    """`run.json` 레코드들에서 `observation_id → sealed_at` 매핑을 만든다.

    run grain이 target 1건에 대응하므로, run의 `observations` 목록에 있는 모든
    관측이 그 run의 `sealed_at`을 물려받는다.
    """
    mapping: dict[str, str] = {}
    for record in run_records:
        sealed = record.get("sealed_at")
        if not sealed:
            continue
        for obs_id in record.get("observations", []) or []:
            mapping[str(obs_id)] = str(sealed)
    return mapping


def assign_window(sealed_at: Any, *, cutoff_iso: str = AI_CUTOFF_ISO) -> str:
    """`sealed_at`을 cutoff 전/후 구간으로 배정한다. 없으면 `SEALED_AT_MISSING`."""
    ts = _parse_iso(sealed_at)
    if ts is None:
        return WINDOW_UNKNOWN
    cutoff = _parse_iso(cutoff_iso)
    if cutoff is None:  # pragma: no cover - 상수라 실패하지 않는다
        return WINDOW_UNKNOWN
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=cutoff.tzinfo)
    return WINDOW_POST if ts >= cutoff else WINDOW_PRE


def attach_windows(
    landing: pd.DataFrame,
    *,
    sealed_at_map: dict[str, str] | None = None,
    cutoff_iso: str = AI_CUTOFF_ISO,
) -> pd.DataFrame:
    """`fact_landing_observation`에 `sealed_at`·`collection_window`를 붙인다.

    `sealed_at`이 이미 컬럼으로 있으면 그것을 쓰고, 없으면 `sealed_at_map`
    (`run.json` 유래)에서 관측 id로 찾는다.
    """
    if landing.empty:
        out = landing.copy()
        out["sealed_at"] = pd.Series(dtype=object)
        out["collection_window"] = pd.Series(dtype=object)
        return out

    out = landing.copy()
    if "sealed_at" not in out.columns:
        out["sealed_at"] = None
    if sealed_at_map:
        filled = out["observation_id"].astype(str).map(sealed_at_map)
        out["sealed_at"] = out["sealed_at"].where(out["sealed_at"].notna(), filled)
    out["collection_window"] = out["sealed_at"].map(
        lambda v: assign_window(v, cutoff_iso=cutoff_iso)
    )
    return out


# ── 의무 1·2 — 구간별 undetermined_rate 분해 + 차이의 귀속 ─────────────────


def undetermined_rate_by_window(
    criterion: pd.DataFrame,
    landing_with_window: pd.DataFrame,
) -> dict[str, Any]:
    """구간별 `undetermined_rate`를 분해하고, 유의하게 다르면 **처리 순서 기인**으로 명시한다.

    `undetermined_rate` = older-relevant 적용 가능분(`NA` 제외) 중 `UNDETERMINED`
    비율. 관측 단위로 계산한 뒤 구간별로 모아 Mann-Whitney U로 비교한다
    (정규성 가정 없이 순위로 비교 — 비율 분포가 치우쳐 있어도 유효하다).

    구간 어느 한쪽이라도 `MIN_PER_WINDOW_FOR_TEST` 미만이면 검정하지 않고
    `NOT_ENOUGH_DATA`를 낸다 — 표본이 없다는 것을 "차이가 없다"로 쓰지 않는다.
    """
    empty_result: dict[str, Any] = {
        "by_window": {},
        "tested": False,
        "verdict": "NOT_ENOUGH_DATA",
        "attribution": None,
        "p_value": None,
        "alpha": WINDOW_TEST_ALPHA,
    }
    if criterion.empty or landing_with_window.empty:
        return empty_result

    obs_window = landing_with_window.set_index("observation_id")["collection_window"]
    crit = criterion.copy()
    crit["collection_window"] = crit["observation_id"].map(obs_window)
    older = crit[crit["older_relevance"].astype(str) != "OTHER"]
    if older.empty:
        return empty_result

    rows: list[dict[str, Any]] = []
    for (obs_id, window), group in older.groupby(["observation_id", "collection_window"]):
        final = group["final_status"].astype(str)
        applicable = final[final != "NA"]
        if applicable.empty:
            continue
        rows.append(
            {
                "observation_id": obs_id,
                "collection_window": window,
                "undetermined_rate": float((applicable == "UNDETERMINED").mean()),
                "n_applicable": len(applicable),
            }
        )
    per_obs = pd.DataFrame(rows)
    if per_obs.empty:
        return empty_result

    by_window: dict[str, Any] = {}
    for window, group in per_obs.groupby("collection_window"):
        rates = group["undetermined_rate"]
        by_window[str(window)] = {
            "n_observations": len(group),
            "undetermined_rate_mean": round(float(rates.mean()), 4),
            "undetermined_rate_median": round(float(rates.median()), 4),
            "n_applicable_total": int(group["n_applicable"].sum()),
        }

    pre = per_obs.loc[per_obs["collection_window"] == WINDOW_PRE, "undetermined_rate"]
    post = per_obs.loc[per_obs["collection_window"] == WINDOW_POST, "undetermined_rate"]

    result: dict[str, Any] = {
        "by_window": by_window,
        "tested": False,
        "verdict": "NOT_ENOUGH_DATA",
        "attribution": None,
        "p_value": None,
        "alpha": WINDOW_TEST_ALPHA,
        "min_per_window_for_test": MIN_PER_WINDOW_FOR_TEST,
        "cutoff": AI_CUTOFF_ISO,
    }
    if len(pre) < MIN_PER_WINDOW_FOR_TEST or len(post) < MIN_PER_WINDOW_FOR_TEST:
        result["reason_not_tested"] = (
            f"구간별 관측이 {len(pre)}/{len(post)}건으로 최소 {MIN_PER_WINDOW_FOR_TEST}건 미만이다 "
            "— 검정하지 않는다. **차이가 없다는 뜻이 아니다.**"
        )
        return result

    stat, pvalue = scipy_stats.mannwhitneyu(pre, post, alternative="two-sided")
    differs = bool(pvalue < WINDOW_TEST_ALPHA)
    result.update(
        {
            "tested": True,
            "statistic": float(stat),
            "p_value": float(pvalue),
            "verdict": "DIFFERS_BY_WINDOW" if differs else "NO_SIGNIFICANT_DIFFERENCE",
        }
    )
    if differs:
        result["attribution"] = (
            "**처리 순서에 기인한다.** 14:00 AI cutoff 이후 봉인된 관측은 AI review cascade를 "
            "덜 거쳐 UNDETERMINED가 구조적으로 더 남는다 — 이 구간 차이는 **대상 서비스의 "
            "접근성 성질이 아니라 우리 처리 순서의 산물**이다. 이 차이를 서비스 간 비교로 "
            "읽으면 안 된다."
        )
    else:
        result["attribution"] = (
            "구간 간 유의한 차이가 관측되지 않았다(alpha=0.05). 처리 순서 교란의 증거가 "
            "이 표본에서는 나타나지 않았다 — 교란이 없음을 증명한 것은 아니다."
        )
    return result


# ── 의무 4 — 구간별 archetype 분포 (단정 금지) ────────────────────────────


def archetype_distribution_by_window(
    task: pd.DataFrame,
    landing_with_window: pd.DataFrame,
) -> dict[str, Any]:
    """구간별 `InteractionArchetype` 분포를 **실제로 계산**한다.

    interleave 순서 때문에 편향이 없을 것으로 예상되지만 **확인하지 않고 단정하지
    않는다.** 카이제곱 독립성 검정을 쓰되 기대빈도가 `MIN_EXPECTED_CELL` 미만이면
    근사가 무너지므로 검정하지 않고 `NOT_ENOUGH_DATA`를 낸다 — 그 경우
    "편향 없음"이라고 쓰지 않는다.
    """
    result: dict[str, Any] = {
        "by_window": {},
        "tested": False,
        "verdict": "NOT_ENOUGH_DATA",
        "p_value": None,
        "alpha": WINDOW_TEST_ALPHA,
        "min_expected_cell": MIN_EXPECTED_CELL,
    }
    if task.empty or landing_with_window.empty:
        result["reason_not_tested"] = "빈 입력"
        return result

    target_window = landing_with_window.set_index("web_target_id")["collection_window"]
    t = task.copy()
    t["collection_window"] = t["web_target_id"].map(target_window)
    t = t.dropna(subset=["collection_window", "interaction_archetype"])
    if t.empty:
        result["reason_not_tested"] = "구간을 배정할 수 있는 task 행이 없다"
        return result

    table = pd.crosstab(t["collection_window"], t["interaction_archetype"])
    result["by_window"] = {
        str(window): {str(k): int(v) for k, v in row.items()} for window, row in table.iterrows()
    }

    if table.shape[0] < 2 or table.shape[1] < 2:
        result["reason_not_tested"] = (
            f"교차표가 {table.shape}라 독립성 검정을 할 수 없다 — 구간이 하나뿐이거나 "
            "archetype이 하나뿐이다. **편향이 없다는 뜻이 아니다.**"
        )
        return result

    chi2, pvalue, _dof, expected = scipy_stats.chi2_contingency(table)
    if (expected < MIN_EXPECTED_CELL).any():
        result["reason_not_tested"] = (
            f"기대빈도가 {MIN_EXPECTED_CELL} 미만인 칸이 있어 카이제곱 근사가 유효하지 않다 "
            "— 검정하지 않는다. **편향이 없다는 뜻이 아니다.**"
        )
        result["min_expected_observed"] = round(float(expected.min()), 3)
        return result

    biased = bool(pvalue < WINDOW_TEST_ALPHA)
    result.update(
        {
            "tested": True,
            "statistic": float(chi2),
            "p_value": float(pvalue),
            "verdict": "BIAS_DETECTED" if biased else "CHECKED_NO_BIAS_DETECTED",
        }
    )
    result["note"] = (
        (
            "**구간별 archetype 분포가 유의하게 다르다.** interleave 순서가 archetype 편향을 "
            "막을 것이라는 예상이 이 표본에서는 성립하지 않았다 — 구간 간 비교에 archetype "
            "구성 차이가 섞여 들어간다."
        )
        if biased
        else (
            "구간별 archetype 분포를 **확인했고** 유의한 차이가 없었다(alpha=0.05). "
            "확인 없이 단정하지 않기 위해 실제로 계산한 결과다."
        )
    )
    return result


def collection_window_report(
    marts: dict[str, pd.DataFrame],
    *,
    sealed_at_map: dict[str, str] | None = None,
    cutoff_iso: str = AI_CUTOFF_ISO,
) -> dict[str, Any]:
    """의무 1·2·4를 한 번에 낸다 — 산출물에 그대로 실을 수 있는 블록."""
    landing = marts.get("fact_landing_observation", pd.DataFrame())
    criterion = marts.get("fact_criterion_result", pd.DataFrame())
    task = marts.get("fact_task_entry", pd.DataFrame())

    landing_w = attach_windows(landing, sealed_at_map=sealed_at_map, cutoff_iso=cutoff_iso)
    window_counts = (
        landing_w["collection_window"].value_counts(dropna=False).to_dict()
        if not landing_w.empty
        else {}
    )
    return {
        "cutoff": cutoff_iso,
        "sealed_at_source": "EvidenceRun.run_record()['sealed_at'] (run grain, run.json)",
        "observations_by_window": {str(k): int(v) for k, v in window_counts.items()},
        "undetermined_rate_by_window": undetermined_rate_by_window(criterion, landing_w),
        "archetype_distribution_by_window": archetype_distribution_by_window(task, landing_w),
    }
