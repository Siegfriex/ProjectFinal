"""집계 가드 — `A2 §4` 산식과 `§6.3` 이 요구한 "산출 실패" 지점.

`A2 §6.3` 은 몇몇 규칙을 **집계 단계에서** 막으라고 요구한다. 전이 가드로는 잡히지 않는
종류다 — 값은 옳게 저장됐는데 **세는 방법이 틀린** 경우이기 때문이다 (I-6 · I-9 · I-13 ·
I-19 · I-21 · I-29). 그 지점들이 여기 있다.

이 모듈은 분석 결론을 만들지 않는다. numerator/denominator 를 코드로 고정해
`03 Phase 6` 역추적 요구를 만족시키는 것이 목적이다.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any

from .vocabulary import EndpointStatus, EndpointStatusDetail, InteractionArchetype


class ReportingError(ValueError):
    """`A2 §4` · `§6.3` 집계 가드 위반 — 산출을 실패시킨다."""


#: 규칙 E-10 — 이 두 archetype 의 `MPFED` 계열 지표는 층별 병기가 **필수**다.
STRATIFIED_ARCHETYPES: frozenset[str] = frozenset(
    {
        InteractionArchetype.FINANCIAL_ACTION_ENTRY.value,
        InteractionArchetype.COMMUNICATION_ENTRY.value,
    }
)


def auth_gate_prevalence(entries: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    """규칙 E-8 — 2항 합집합으로 센다 (주입 I-6).

    `endpoint_status = 'AUTH_GATE_REACHED'` 단독 집계는 gate 가 endpoint 인 두 archetype 에서
    **0 으로 과소집계**된다. 이 함수는 두 방식을 함께 계산하고 어긋나면 그 사실을 노출한다.
    """
    rows = list(entries)
    union = 0
    naive = 0
    for row in rows:
        detail = row.get("endpoint_status_detail")
        before = int(row.get("auth_gate_before_endpoint") or 0)
        if before or detail == EndpointStatusDetail.ENDPOINT_VIA_AUTH_GATE.value:
            union += 1
        if row.get("endpoint_status") == EndpointStatus.AUTH_GATE_REACHED.value:
            naive += 1
    return {
        "n": len(rows),
        "auth_gate_observed": union,
        "naive_endpoint_status_only": naive,
        "undercount": union - naive,
    }


def assert_auth_gate_aggregation(entries: Iterable[Mapping[str, Any]], reported: int) -> None:
    """보고된 `auth gate` 유병률이 규칙 E-8 합집합과 일치하는지 (주입 I-6)."""
    stats = auth_gate_prevalence(entries)
    if reported != stats["auth_gate_observed"]:
        raise ReportingError(
            f"E-8: auth gate 유병률이 어긋난다. 보고 {reported} / "
            f"합집합 {stats['auth_gate_observed']} (단독 집계 {stats['naive_endpoint_status_only']}). "
            "endpoint_status = 'AUTH_GATE_REACHED' 만으로 세면 두 archetype 에서 과소집계된다"
        )


def archetype_mpfed_summary(entries: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    """`mart_archetype_summary` 의 `MPFED` 계열 — 규칙 E-10 층화 (주입 I-9).

    두 archetype 에서는 `endpoint_status_detail = ENDPOINT_VIA_AUTH_GATE` 여부로 층을 갈라
    **병기**한다. 합산값만 내놓지 않는다.
    """
    by_archetype: dict[str, list[Mapping[str, Any]]] = {}
    for row in entries:
        by_archetype.setdefault(str(row.get("archetype")), []).append(row)

    out: dict[str, Any] = {}
    for archetype, rows in by_archetype.items():
        measured = [r for r in rows if r.get("mpfed") is not None]
        censored = [
            r for r in rows if str(r.get("endpoint_status_detail") or "").startswith("UNRESOLVED_")
        ]
        summary: dict[str, Any] = {
            "n": len(rows),
            "mpfed_median": _median([int(r["mpfed"]) for r in measured]),
            # 규칙 E-4 — 절단 건수를 별도 컬럼으로 노출한다. 상한값을 대입하지 않는다.
            "censored_n": len(censored),
            "endpoint_reach": len([r for r in rows if r.get("endpoint_reached")]),
        }
        if archetype in STRATIFIED_ARCHETYPES:
            via_gate = [
                r
                for r in rows
                if r.get("endpoint_status_detail")
                == EndpointStatusDetail.ENDPOINT_VIA_AUTH_GATE.value
            ]
            direct = [r for r in rows if r not in via_gate]
            summary["endpoint_via_auth_gate_rate"] = (
                round(len(via_gate) / len(rows), 4) if rows else None
            )
            summary["strata"] = {
                "ENDPOINT_VIA_AUTH_GATE": {
                    "n": len(via_gate),
                    "mpfed_median": _median(
                        [int(r["mpfed"]) for r in via_gate if r.get("mpfed") is not None]
                    ),
                },
                "DIRECT_FUNCTION_ENTRY": {
                    "n": len(direct),
                    "mpfed_median": _median(
                        [int(r["mpfed"]) for r in direct if r.get("mpfed") is not None]
                    ),
                },
            }
        out[archetype] = summary
    return out


def assert_stratified(summary: Mapping[str, Any]) -> None:
    """규칙 E-10 — 두 archetype 에 층별 값과 `endpoint_via_auth_gate_rate` 가 있는가 (I-9)."""
    for archetype in STRATIFIED_ARCHETYPES:
        if archetype not in summary:
            continue
        row = summary[archetype]
        if "strata" not in row or "endpoint_via_auth_gate_rate" not in row:
            raise ReportingError(
                f"E-10: {archetype} 의 MPFED 계열 지표를 층 구분 없이 합산값만 산출했다. "
                "층별 값과 endpoint_via_auth_gate_rate 를 병기해야 한다 (주입 I-9)"
            )


def _median(values: list[int]) -> float | None:
    if not values:
        return None
    s = sorted(values)
    mid = len(s) // 2
    return float(s[mid]) if len(s) % 2 else (s[mid - 1] + s[mid]) / 2


def abstention_rate(
    adjudications: Iterable[Mapping[str, Any]],
) -> dict[str, Any]:
    """`A2 §4.5` 규칙 B-2 — `review_task_type` 분리 없이 한 칸에 합산하지 않는다 (주입 I-19).

    정본은 `CRITERION_VERDICT` 기준이고 triage 는 **병기**한다.
    """
    rows = list(adjudications)
    buckets: dict[str, dict[str, int]] = {}
    for row in rows:
        b = buckets.setdefault(str(row.get("review_task_type")), {"n": 0, "abstain": 0})
        b["n"] += 1
        b["abstain"] += int(row.get("final_status") == "ABSTAIN")
    return {
        "by_review_task_type": {
            k: {**v, "rate": round(v["abstain"] / v["n"], 4) if v["n"] else None}
            for k, v in buckets.items()
        },
        "canonical_basis": "CRITERION_VERDICT",
    }


def assert_abstention_split(report: Mapping[str, Any]) -> None:
    if "by_review_task_type" not in report:
        raise ReportingError(
            "B-2: abstention rate 를 review_task_type 분리 없이 한 칸에 합산했다 (주입 I-19)"
        )


def phase5_measurement_quality(
    *,
    adjudications: Iterable[Mapping[str, Any]],
    not_eligible_at_collection_count: int,
    eligibility_reversal_rate: float | None,
    recollection_runs: int,
    decision_coverage_first_run: float | None,
    decision_coverage_canonical_run: float | None,
    unpreregistered_recollection_runs: int,
    over_limit_recollection_runs: int,
    stop_reason_counts: Mapping[str, int] | None = None,
) -> dict[str, Any]:
    """`03 Phase 5` 측정품질 보고. 누락이 있으면 **산출을 실패시킨다.**

    주입 I-13(W-3) · I-21(T-9) · I-29(RC-5) 가 여기서 막힌다.
    """
    rows = list(adjudications)

    pending = [r for r in rows if r.get("final_status") == "PENDING"]
    if pending:
        raise ReportingError(
            f"T-9: Phase 5 시점에 PENDING 잔여가 {len(pending)} 건이다 — 0이어야 한다 (주입 I-21)"
        )

    if not_eligible_at_collection_count > 0 and eligibility_reversal_rate is None:
        raise ReportingError(
            "W-3: NOT_ELIGIBLE_AT_COLLECTION 이 1건 이상인데 eligibility_reversal_rate 가 "
            "보고되지 않았다 (주입 I-13)"
        )

    if recollection_runs > 0 and (
        decision_coverage_first_run is None or decision_coverage_canonical_run is None
    ):
        raise ReportingError(
            "RC-5: 재수집이 1건 이상인데 decision_coverage_applicable 의 "
            "재수집 전후 병기가 누락됐다 (주입 I-29)"
        )

    if unpreregistered_recollection_runs > 0:
        raise ReportingError(
            f"RC-4: 사전선언 없는 재수집 run 이 {unpreregistered_recollection_runs} 건이다 "
            "— Phase 5 시점에 0이어야 한다"
        )

    abstention = abstention_rate(rows)
    assert_abstention_split(abstention)
    return {
        "abstention": abstention,
        "not_eligible_at_collection_count": not_eligible_at_collection_count,
        "eligibility_reversal_rate": eligibility_reversal_rate,
        "recollection_runs": recollection_runs,
        "decision_coverage_first_run": decision_coverage_first_run,
        "decision_coverage_canonical_run": decision_coverage_canonical_run,
        "over_limit_recollection_runs": over_limit_recollection_runs,
        "unpreregistered_recollection_runs": unpreregistered_recollection_runs,
        "stop_reason_counts": dict(stop_reason_counts or {}),
    }


def assert_undetermined_not_dropped(*, before: Iterable[str], after: Iterable[str]) -> None:
    """규칙 N-7 — 남은 `UNDETERMINED` 행을 삭제하거나 stress bound 에서 빼지 않는다 (I-18)."""
    lost = set(before) - set(after)
    if lost:
        raise ReportingError(
            f"N-7: UNDETERMINED 행 {sorted(lost)} 이 stress bound 대상에서 빠졌다. "
            "남은 UNDETERMINED 는 지우는 대신 영향을 잰다 (주입 I-18)"
        )
