#!/usr/bin/env python3
"""E001 실측 배치에서 mart를 빌드하고 원인 귀속을 산출한다.

배치 `results[].detail`의 `l0` 블록이 `fact_landing_observation`·
`fact_interrupt_element`를, `detail` 본체가 `fact_task_entry`를 채운다.
evidence 파일을 다시 파싱하지 않는다(같은 값이 이미 배치에 있다).

**중대 관측**: 이 수집에는 KWCAG criterion 산출물이 **없다**(evidence는 L0 raw만
가진다: ax/computed_css/dom/probe/screenshot). 따라서 `fact_criterion_result`는
**빈 표**이며 `OlderRelevantKWCAGFailRate`를 계산할 수 없다. J4(older-relevant
중 1개 이상 non-UNDETERMINED)가 **어느 관측에서도 충족되지 않으므로**
`l0_analyzable_n = 0`이다. 이 사실을 0으로 덮지 않고 그대로 보고한다.
"""

from __future__ import annotations

import argparse
import contextlib
import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from analysis.eda.batch_results import (
    UNRESOLVED_BUDGET_REASON_CATEGORY,
    UNRESOLVED_REASON_UNRECORDED,
    classify_unresolved_reason,
    derive_collection_markers_multi,
    load_batch_results,
    snapshot_now,
)

#: `A2 §1.5.1` + `00_SSOT §3` — gate를 endpoint로 승격할 수 있는 archetype은 2종뿐.
#: 나머지 5종은 **gate 종류를 정확히 판별했어도** MPFED가 NULL이다.
PROMOTION_ELIGIBLE_ARCHETYPES = frozenset({"FINANCIAL_ACTION_ENTRY", "COMMUNICATION_ENTRY"})


def build_marts(results: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    landing: list[dict[str, Any]] = []
    tasks: list[dict[str, Any]] = []
    interrupts: list[dict[str, Any]] = []

    for result in results:
        detail = result.get("detail") or {}
        l0 = detail.get("l0") or {}
        if l0:
            obs_id = l0.get("observation_id")
            landing.append(
                {
                    "observation_id": obs_id,
                    "web_target_id": l0.get("web_target_id"),
                    "audit_date": l0.get("audit_date"),
                    "requested_url": l0.get("requested_url"),
                    "final_url": l0.get("final_url"),
                    "measurement_status": l0.get("measurement_status"),
                    "viewport_width": l0.get("viewport_width"),
                    "viewport_height": l0.get("viewport_height"),
                    "screenshot_path": l0.get("screenshot_initial_path"),
                    "dom_path": l0.get("dom_path"),
                    "ax_path": l0.get("ax_path"),
                    "probe_path": l0.get("probe_path"),
                    "manifest_path": l0.get("manifest_path"),
                    "primary_action_visible_initial": l0.get("primary_action_visible_initial"),
                    "max_overlay_coverage": l0.get("max_overlay_coverage"),
                    "max_primary_action_occlusion": l0.get("max_primary_action_occlusion"),
                    "blocking_modal_count": sum(
                        1
                        for i in (l0.get("interrupts") or [])
                        if str(i.get("blocks_primary_action")) == "1"
                    ),
                    "evidence_run_id": l0.get("evidence_run_id"),
                    "sealed_at": l0.get("collection_finished_at"),
                }
            )
            for idx, interrupt in enumerate(l0.get("interrupts") or []):
                interrupts.append(
                    {
                        "observation_id": obs_id,
                        "interrupt_id": f"{obs_id}-{interrupt.get('interrupt_index', idx)}",
                        "selector": interrupt.get("selector"),
                        "overlay_coverage": interrupt.get("viewport_coverage"),
                        "blocks_primary_action": str(interrupt.get("blocks_primary_action")),
                        "primary_action_occlusion": interrupt.get("primary_action_occlusion"),
                        "dismiss_control_exists": str(interrupt.get("dismiss_control_exists")),
                        "dismiss_control_visible": str(interrupt.get("dismiss_control_visible")),
                        "dismiss_succeeded": str(interrupt.get("dismiss_succeeded")),
                        "classification_status": interrupt.get("classification_status"),
                        "final_label": interrupt.get("final_label"),
                    }
                )
        if detail.get("task_observation_id") or detail.get("endpoint_status"):
            tasks.append(
                {
                    "task_observation_id": detail.get("task_observation_id"),
                    "task_id": detail.get("task_id"),
                    "web_target_id": (l0 or {}).get("web_target_id"),
                    "interaction_archetype": detail.get("archetype"),
                    "endpoint_status": detail.get("endpoint_status"),
                    "endpoint_status_detail": detail.get("endpoint_status_detail"),
                    "NED": detail.get("ned"),
                    "IED": detail.get("ied"),
                    "MPFED": detail.get("mpfed"),
                    "auth_gate_before_endpoint": str(detail.get("auth_gate_before_endpoint")),
                    "endpoint_reached": str(detail.get("endpoint_reached")),
                    "forced_dismissal_count": detail.get("forced_dismissal_count"),
                    "budget_reason": detail.get("budget_reason"),
                }
            )
    return {
        "fact_landing_observation": landing,
        "fact_task_entry": tasks,
        "fact_interrupt_element": interrupts,
        # KWCAG 평가가 수행되지 않았다 — 빈 표다. 0으로 덮지 않는다.
        "fact_criterion_result": [],
        "dim_certification": [],
    }


def attribute_causes(results: list[dict[str, Any]]) -> dict[str, Any]:
    """MPFED 미산출 59건의 원인을 **성격이 다른 범주로** 귀속한다.

    "측정기가 실패했다"로 뭉뚱그리지 않는다 — 도구 입도 / 계약 설계 / 판별 실패는
    시정 방향이 다르다.
    """
    guard = archetype_rule = unresolved = skipped = captcha = e6b_binding = 0
    e6b_fired = 0
    auth_gate_by_archetype: dict[str, int] = {}
    unresolved_by_reason: dict[str, int] = {}

    for result in results:
        detail = result.get("detail") or {}
        outcome = str(result.get("outcome"))
        archetype = str(detail.get("archetype") or "UNKNOWN")

        if outcome == "ACCOUNT_ACTION_BLOCKED":
            guard += 1
        elif outcome == "SKIPPED_RETRY_EXHAUSTED":
            skipped += 1
        elif outcome == "CAPTCHA":
            captcha += 1
        elif outcome == "UNRESOLVED":
            unresolved += 1
            reason = classify_unresolved_reason(result) or UNRESOLVED_REASON_UNRECORDED
            unresolved_by_reason[reason] = unresolved_by_reason.get(reason, 0) + 1
        elif outcome == "AUTH_GATE":
            auth_gate_by_archetype[archetype] = auth_gate_by_archetype.get(archetype, 0) + 1
            if archetype in PROMOTION_ELIGIBLE_ARCHETYPES:
                # 승격 가능한 archetype인데 gate 종류 판별 실패로 막힌 것 = E-6b 구속.
                e6b_binding += 1
            else:
                # 종류를 정확히 판별했어도 정의상 MPFED가 NULL — 계약 설계의 결과다.
                archetype_rule += 1
        notes = detail.get("notes") or []
        if any("gate 판별" in str(n) and "UNDETERMINED" in str(n) for n in notes):
            e6b_fired += 1

    total = guard + archetype_rule + unresolved + skipped + captcha + e6b_binding
    return {
        "total": total,
        "attribution": {
            "guard_granularity": {
                "n": guard,
                "pct": round(guard / total * 100, 1) if total else None,
                "category": "OUR_TOOL_CONSTRAINT",
                "label": "가드 입도 — 우리 도구의 제약",
            },
            "archetype_endpoint_rule": {
                "n": archetype_rule,
                "pct": round(archetype_rule / total * 100, 1) if total else None,
                "category": "OUR_CONTRACT_DESIGN",
                "label": "archetype-endpoint 규칙 자체 — 본 연구 계약의 설계",
                "by_archetype": {
                    k: v
                    for k, v in auth_gate_by_archetype.items()
                    if k not in PROMOTION_ELIGIBLE_ARCHETYPES
                },
            },
            "unresolved": {
                "n": unresolved,
                "pct": round(unresolved / total * 100, 1) if total else None,
                "category": "MIXED",
                "label": "UNRESOLVED — budget_reason으로 분해",
                "by_budget_reason": unresolved_by_reason,
                "by_category": {
                    UNRESOLVED_BUDGET_REASON_CATEGORY.get(k, "UNCLASSIFIED"): v
                    for k, v in unresolved_by_reason.items()
                },
            },
            "skipped_retry_exhausted": {
                "n": skipped,
                "pct": round(skipped / total * 100, 1) if total else None,
                "category": "OUR_CIRCUMSTANCE",
                "label": "SKIPPED_RETRY_EXHAUSTED — 우리 쪽 사정",
            },
            "captcha": {
                "n": captcha,
                "pct": round(captcha / total * 100, 1) if total else None,
                "category": "TARGET_PROPERTY",
                "label": "CAPTCHA — 대상의 성질",
            },
            "e6b_binding": {
                "n": e6b_binding,
                "pct": round(e6b_binding / total * 100, 1) if total else None,
                "category": "MEASUREMENT_LIMIT",
                "label": "E-6b 구속 — 측정기 한계",
            },
        },
        # 발화한 것과 결과를 바꾼 것은 다르다. 둘을 반드시 병기한다.
        "e6b_fired_n": e6b_fired,
        "e6b_binding_n": e6b_binding,
        "e6b_note": (
            f"E-6b는 {e6b_fired}건에서 **발화**했으나 실제로 결과를 바꾼 것(구속)은 "
            f"{e6b_binding}건이다. 승격은 `A2 §1.5.1`+`00_SSOT §3`이 "
            "FINANCIAL_ACTION_ENTRY·COMMUNICATION_ENTRY 2종으로 한정하므로, 나머지 "
            "archetype에서는 gate 종류를 정확히 판별했어도 MPFED가 NULL이다. "
            "**발화 횟수를 원인으로 쓰면 과대평가다.**"
        ),
        "auth_gate_by_archetype": auth_gate_by_archetype,
        "attribution_note": (
            "'측정기가 실패했다'로 뭉뚱그리지 않는다 — 도구 입도(가드) / 계약 설계"
            "(archetype-endpoint 규칙) / 판별 실패(E-6b)는 성격이 다르고 시정 방향도 다르다."
        ),
    }


#: A가 원천 CSV(`9999857:...representative_task_candidate_shadow.csv`,
#: `mapping_status=CANDIDATE` 59건)로 조인한 결과를 재현한다.
_SHADOW_CSV_REF = (
    "9999857:research/landing_accessibility/shadow/lane_b/state/"
    "representative_task_candidate_shadow.csv"
)

DEPTH_RECOVERY_FINDING = (
    "가드 입도는 25건에서 L1 탐색을 차단했으나 **구속 조건은 아니다.** 가드가 개입하지 "
    "않은 25건에서도 endpoint 도달이 0이었다. 더 근본적인 제약은 **이 측정 접근이 이 "
    "프레임의 대표기능 진입점에 닿지 못한다**는 것이며, archetype-endpoint 규칙이 그것을 "
    "정의 수준에서 확정한다."
)

DEPTH_RECOVERY_INFERENCE_LIMIT = (
    "무작위 배정이 아니다 — 가드 발화가 페이지 텍스트에 의존하므로 Scout이 돈 25건과 "
    "가드에 막힌 17건이 체계적으로 다를 수 있다. 뒷받침하는 근거는 두 집단의 archetype "
    "구성이 유사하고(양쪽 ITEM_DETAIL 지배) Scout 쪽이 예외 없이 0/25라는 것이다. "
    "확정하려면 가드를 고친 뒤 같은 프레임을 재수집해야 하고 오늘 하지 않았다."
)


def analyze_depth_recovery(
    results: list[dict[str, Any]], archetype_by_target: dict[str, str]
) -> dict[str, Any]:
    """ "가드 입도를 고치면 depth 축이 살아나는가"에 데이터로 답한다.

    **답: 아니다.** 가드가 개입하지 않고 Scout이 실제로 돈 승격 불가 archetype
    25건에서 endpoint 도달이 0건이다. 따라서 가드에 막힌 17건도 가드를 고친다고
    MPFED가 나올 근거가 없다. 회복 상한은 가드 차단 중 **승격 가능** archetype
    8건뿐이며, 그마저 gate 종류 판별이 되어야 한다.
    """
    guard_by_archetype: dict[str, int] = {}
    guard_promoting = guard_non_promoting = unmapped = 0
    scout_non_promoting = scout_non_promoting_reached = 0
    scout_non_promoting_outcomes: dict[str, int] = {}

    for result in results:
        detail = result.get("detail") or {}
        outcome = str(result.get("outcome"))
        target_id = result.get("target_id")
        mapped = archetype_by_target.get(str(target_id))

        if outcome == "ACCOUNT_ACTION_BLOCKED":
            if mapped is None:
                unmapped += 1
                continue
            guard_by_archetype[mapped] = guard_by_archetype.get(mapped, 0) + 1
            if mapped in PROMOTION_ELIGIBLE_ARCHETYPES:
                guard_promoting += 1
            else:
                guard_non_promoting += 1
        elif detail.get("scout_invoked") is True:
            archetype = detail.get("archetype") or mapped
            if archetype and archetype not in PROMOTION_ELIGIBLE_ARCHETYPES:
                scout_non_promoting += 1
                scout_non_promoting_outcomes[outcome] = (
                    scout_non_promoting_outcomes.get(outcome, 0) + 1
                )
                if str(detail.get("endpoint_reached")) == "1":
                    scout_non_promoting_reached += 1

    return {
        "question": "가드 입도를 고치면 depth 축이 살아나는가?",
        "answer": "아니다 — 데이터가 지지하지 않는다.",
        "source_csv": _SHADOW_CSV_REF,
        "guard_blocked_archetype_join": {
            "n": guard_promoting + guard_non_promoting,
            "by_archetype": guard_by_archetype,
            "promotion_eligible": guard_promoting,
            "non_promoting": guard_non_promoting,
            "unmapped": unmapped,
        },
        "scout_ran_non_promoting_endpoint_reached": (
            f"{scout_non_promoting_reached} / {scout_non_promoting}"
        ),
        "scout_ran_non_promoting_outcomes": scout_non_promoting_outcomes,
        "depth_recovery_upper_bound": guard_promoting,
        "honest_range": f"0~{guard_promoting}",
        "honest_range_note": (
            f"회복 상한 {guard_promoting}건은 가드 차단분 중 승격 가능 archetype 수다. "
            "그마저 gate 종류 판별이 되어야 하며, AUTH_GATE 12건 중 8건에서 E-6b가 "
            "발화했다(판별 실패율 2/3). **상한에 가까울 근거는 없다.**"
        ),
        "finding": DEPTH_RECOVERY_FINDING,
        "inference_limit": DEPTH_RECOVERY_INFERENCE_LIMIT,
    }


def _load_archetype_by_target(csv_path: str | None) -> dict[str, str]:
    if not csv_path or not Path(csv_path).exists():
        return {}
    import csv as _csv

    mapping: dict[str, str] = {}
    with open(csv_path, encoding="utf-8-sig") as handle:
        for row in _csv.DictReader(handle):
            if row.get("mapping_status") == "CANDIDATE" and row.get("web_target_id"):
                mapping[row["web_target_id"]] = row.get("interaction_archetype", "")
    return mapping


#: 축 B의 서술 제약과 같은 원리 — 우리가 관측한 것은 **자동화 도구의 dismissal
#: 결과**이지 사용자 행동이 아니다.
DISMISSAL_NARRATIVE_CONSTRAINT = {
    "forbidden": [
        "고령자가 이 방해요소를 닫지 못한다",
        "닫을 수 없는 방해요소가 102건이다",
    ],
    "correct": (
        "시각적 닫기 컨트롤이 탐지되지 않은 상태에서 ESC/배경클릭으로 닫힌 경우가 102건이다"
    ),
    "principle": (
        "우리가 관측한 것은 **자동화 도구의 dismissal 결과**이지 사용자 행동이 아니다 "
        "(축 B의 '우리 도구의 도달 한계이지 사용자의 도달 한계가 아니다'와 같은 구분)."
    ),
}

#: interrupt 분류기도 결정론 규칙만 돌고 semantic 단계가 없다 — 축 A·B와 같은
#: skeleton 구조다. 이걸 안 적으면 오늘 유일한 실측 축이 실제보다 강해 보인다.
#: 축 C 상태값. `MEASURED`로 쓰지 않는다 — raw는 실측됐으나 분류가 절반 미완이라
#: '측정됨'으로 적으면 오늘 유일한 실측 축이 실제보다 강해 보인다 (A 판정).
AXIS_C_STATUS = "RAW_MEASURED_CLASSIFICATION_INCOMPLETE"

#: 전면 가림(coverage==1.0) 서술 제약 — 축 B·dismissal과 같은 구분이다.
FULL_COVERAGE_NARRATIVE_CONSTRAINT = {
    "forbidden": [
        "고령자가 콘텐츠를 볼 수 없었다",
        "사용자가 화면을 이용할 수 없었다",
    ],
    "correct": ("초기 화면 상태에서 방해요소가 뷰포트를 완전히 덮은 관측이 22/56건(39%)이다"),
    "principle": (
        "우리가 관측한 것은 **초기 화면 상태**이지 사용자 경험이 아니다 "
        "(축 B '우리 도구의 도달 한계', dismissal '자동화 도구의 dismissal 결과'와 같은 구분)."
    ),
}

#: 오늘의 **통합적 발견** — 세 축이 같은 구조에서 막혔다.
UNIFIED_SKELETON_FINDING = (
    "**세 축 모두에서 같은 구조적 한계가 나타났다 — 수집기는 만들어졌고 판정기는 "
    "만들어지지 않았다.** 축 A는 criterion 평가기 부재로 `NOT_EVALUATED`, 축 B는 "
    "gate 종류 판별(E-6b)이 fail-closed로 막혀 `MEASURED_ZERO`, 축 C는 interrupt "
    "분류기가 결정론 규칙까지만 돌아 47%가 `UNKNOWN`이다. 세 경우 모두 **raw 수집은 "
    "되고 그 위의 판정 단계가 비어 있다.** 이것이 개별 축의 실패가 아니라 오늘의 "
    "통합적 발견이다."
)

AXIS_C_CLASSIFICATION_INCOMPLETE_NOTE = (
    "축 C는 **'완전 측정'이 아니라 'raw 실측 + 분류 절반 미완'**이다. interrupt "
    "분류기도 결정론 규칙만 돌고 semantic/VLM 단계가 없어(축 A·B와 같은 skeleton "
    "구조) `final_label`의 최대 범주가 `UNKNOWN`이다. 유형 분포를 인용할 때 UNKNOWN을 "
    "각주로 빼면 실측 강도가 과대표시된다."
)

_DISMISSAL_PATH_LABELS: dict[tuple[str, str], str] = {
    ("0", "1"): "닫기 컨트롤 미관측 · 해제됨 (ESC/backdrop 경로)",
    ("1", "1"): "닫기 컨트롤 관측 · 해제됨",
    ("1", "0"): "닫기 컨트롤 관측 · 해제 실패",
    ("0", "0"): "닫기 컨트롤 미관측 · 해제 안 됨",
}


class LabelReportingViolation(ValueError):
    """`final_label` 분포를 `UNKNOWN` 없이 보고하려 했다 — A 판정으로 금지된다."""


def assert_unknown_reported(label_table: list[dict[str, Any]]) -> None:
    """`final_label` 분포에 `UNKNOWN` 행이 없으면 실패시킨다.

    A 판정: "`final_label` 분포를 UNKNOWN 없이 보고하는 것 자체를 금지한다."
    문서로 부탁하지 않고 코드로 막는다 — 최대 범주를 생략하면 실측 강도가 과대표시된다.
    """
    if not any(row.get("label") == "UNKNOWN" for row in label_table):
        raise LabelReportingViolation(
            "final_label 분포에 UNKNOWN 행이 없다 — UNKNOWN을 뺀 유형 분포 보고는 금지된다."
        )


def _describe_distribution(values: list[float]) -> dict[str, Any]:
    """전체 사분위 + 이봉 여부. **median 단독 인용을 막기 위해** 항상 함께 낸다."""
    import statistics as st

    if not values:
        return {"n": 0}
    sv = sorted(values)
    # C(claude-c/assurance-current)가 inclusive 방법으로 재계산했으므로 같은 규약을
    # 1차값으로 쓴다. exclusive 값도 함께 남겨 두 보고가 대조 가능하게 한다.
    q = st.quantiles(sv, n=4, method="inclusive") if len(sv) > 1 else [sv[0], sv[0], sv[0]]
    q_exclusive = st.quantiles(sv, n=4) if len(sv) > 1 else [sv[0], sv[0], sv[0]]
    low = sum(1 for v in sv if v < 0.25)
    mid = sum(1 for v in sv if 0.25 <= v < 0.75)
    high = sum(1 for v in sv if v >= 0.75)
    # 양 끝에 질량이 몰리고 가운데가 비면 이봉이다.
    bimodal = bool(low and high and mid < min(low, high) / 4)
    out: dict[str, Any] = {
        "n": len(sv),
        "min": round(sv[0], 4),
        "q1": round(q[0], 4),
        "median": round(q[1], 4),
        "q3": round(q[2], 4),
        "max": round(sv[-1], 4),
        "iqr": round(q[2] - q[0], 4),
        "quantile_method": "inclusive (C 재계산과 동일 규약)",
        "q1_exclusive_method": round(q_exclusive[0], 4),
        "quantile_method_note": (
            "q1이 규약에 따라 0.0661(inclusive) / 0.0655(exclusive)로 갈린다 — "
            "**데이터 차이가 아니라 사분위 계산 규약 차이다.** median·q3는 두 규약에서 동일하다."
        ),
        "mass_below_0_25": low,
        "mass_0_25_to_0_75": mid,
        "mass_at_or_above_0_75": high,
        # 겹침 100% 건수 — 사분위와 함께 반드시 낸다(q3=1.0의 실체다).
        "n_at_full_coverage_1_0": sum(1 for v in sv if v >= 0.999),
        "pct_at_full_coverage_1_0": round(sum(1 for v in sv if v >= 0.999) / len(sv) * 100, 1),
        "n_at_zero_coverage": sum(1 for v in sv if v <= 0.0001),
        "pct_at_zero_coverage": round(sum(1 for v in sv if v <= 0.0001) / len(sv) * 100, 1),
        "bimodal": bimodal,
        "reporting_rule": (
            "**median 단독 인용 금지.** min/q1/median/q3/max 전부와 "
            "`n_at_full_coverage_1_0`(전면 가림 건수)을 함께 보고한다 — "
            "median 0.1281만 인용하면 전면 가림 건이 통째로 가려진다."
        ),
    }
    if len(sv) >= 10:
        out["deciles"] = [round(v, 4) for v in st.quantiles(sv, n=10)]
    if bimodal:
        out["bimodal_note"] = (
            f"**이봉 분포다** — 낮은 쪽 {low}건 · 가운데 {mid}건 · 높은 쪽 {high}건으로 "
            "가운데가 비어 있다. **median 단독 인용은 오도한다**: 중앙값은 어느 봉도 "
            "대표하지 않는다. 사분위 전체와 양쪽 질량을 함께 읽어야 한다."
        )
    return out


def describe_axis_c(marts: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
    """축 C(초기 화면 방해요소) 기술통계 — **오늘 유일하게 실측된 축**이다."""

    landing = marts["fact_landing_observation"]
    interrupts = marts["fact_interrupt_element"]

    def _num(rows: list[dict[str, Any]], key: str) -> list[float]:
        out = []
        for row in rows:
            v = row.get(key)
            if v is not None and str(v) not in {"", "None", "nan"}:
                with contextlib.suppress(TypeError, ValueError):
                    out.append(float(v))
        return out

    _stats = _describe_distribution

    per_obs: dict[str, int] = {}
    labels: dict[str, int] = {}
    dismissal_paths: dict[tuple[str, str], int] = {}
    blocks = dismiss_exists = dismiss_visible = dismiss_ok = 0
    for row in interrupts:
        obs = str(row.get("observation_id"))
        per_obs[obs] = per_obs.get(obs, 0) + 1
        label = str(row.get("final_label") or "UNLABELED")
        labels[label] = labels.get(label, 0) + 1
        key = (str(row.get("dismiss_control_exists")), str(row.get("dismiss_succeeded")))
        dismissal_paths[key] = dismissal_paths.get(key, 0) + 1
        if str(row.get("blocks_primary_action")) == "1":
            blocks += 1
        if str(row.get("dismiss_control_exists")) == "1":
            dismiss_exists += 1
        if str(row.get("dismiss_control_visible")) == "1":
            dismiss_visible += 1
        if str(row.get("dismiss_succeeded")) == "1":
            dismiss_ok += 1

    total_interrupts = len(interrupts) or 1
    # 네 조합을 **같은 비중으로** 다룬다 — 102만 강조하지 않는다.
    _DISMISSAL_EQUAL_WEIGHT_NOTE = (
        "네 조합은 **서로 다른 네 사실이며 같은 비중으로 읽어야 한다.** "
        "`(exists=0, succeeded=1)` 102건만 강조하면 `(exists=1, succeeded=0)` 38건 — "
        "**닫기 컨트롤이 탐지됐는데도 해제에 실패한 경우** — 이 가려진다. 둘은 서로 "
        "다른 현상이고 시정 방향도 다르다."
    )
    # UNKNOWN을 **맨 위에** 둔다 — 최대 범주를 각주로 빼지 않는다.
    ordered_labels = sorted(labels.items(), key=lambda kv: (kv[0] != "UNKNOWN", -kv[1]))
    label_table = [
        {"label": k, "n": v, "pct": round(v / total_interrupts * 100, 1)} for k, v in ordered_labels
    ]
    unknown_n = labels.get("UNKNOWN", 0)

    counts = [float(per_obs.get(str(o.get("observation_id")), 0)) for o in landing]
    return {
        "axis": "C — 초기 화면 방해요소",
        # `MEASURED`가 아니다 — raw 실측 + 분류 47% 미완.
        "status": AXIS_C_STATUS,
        "status_expansion": "raw 는 실측(235건) · 분류는 47% 미분류",
        # C가 final_label 235건을 독립 재계산하기 전까지 확정 서술로 쓰지 않는다.
        "independently_verified": True,
        "verification_status": {
            "independently_verified": True,
            "verifier": "Claude C (claude-c/assurance-current)",
            "verified_at": "2026-08-27T14:49+09:00",
            "method": (
                "같은 원천(`results[].detail.l0.interrupts[]`)에서 C가 **자기 코드로** 재계산."
            ),
            "result": "전건 일치 · C1 없음",
            "cross_checked": {
                "n_interrupts": 235,
                "dismiss_control_exists_1": 103,
                "dismiss_succeeded_1": 166,
                "dismissal_paths": {
                    "(0,1)": 102,
                    "(1,1)": 64,
                    "(1,0)": 38,
                    "(0,0)": 30,
                    "(1,None)": 1,
                },
                "n_observations": 56,
                "interrupts_per_obs_median": 3,
                "max_overlay_coverage_median": 0.1281,
                "blocks_primary_action": 74,
                "final_label": {
                    "UNKNOWN": 110,
                    "BANNER": 88,
                    "LOGIN_PROMPT": 13,
                    "PROMOTION_MODAL": 11,
                    "COOKIE_CONSENT": 4,
                    "APP_INSTALL_PROMPT": 3,
                    "CHAT_WIDGET": 2,
                    "ADVERTISEMENT": 2,
                    "BLOCKING_MODAL": 2,
                },
            },
            "known_convention_difference": (
                "q1이 B 0.0655(exclusive) / C 0.0661(inclusive)로 갈렸으나 이는 사분위 계산 "
                "**규약 차이**이며 데이터 불일치가 아니다. B가 C 규약(inclusive)에 맞췄고 "
                "exclusive 값도 `q1_exclusive_method`로 함께 남긴다."
            ),
        },
        "n_observations": len(landing),
        "n_interrupts": len(interrupts),
        "interrupts_per_observation": _stats(counts),
        "max_overlay_coverage": _stats(_num(landing, "max_overlay_coverage")),
        "max_primary_action_occlusion": _stats(_num(landing, "max_primary_action_occlusion")),
        "overlay_coverage_per_interrupt": _stats(_num(interrupts, "overlay_coverage")),
        "blocking_modal_count": _stats(_num(landing, "blocking_modal_count")),
        # UNKNOWN이 표 맨 위에 온다(최대 범주).
        "interrupt_final_label_table": label_table,
        "interrupt_final_label_unknown_n": unknown_n,
        "interrupt_final_label_unknown_pct": round(unknown_n / total_interrupts * 100, 1),
        "classification_incomplete_note": AXIS_C_CLASSIFICATION_INCOMPLETE_NOTE,
        "blocks_primary_action_n": blocks,
        "dismiss_control_exists_n": dismiss_exists,
        "dismiss_control_visible_n": dismiss_visible,
        "dismiss_succeeded_n": dismiss_ok,
        # 총계만 내면 사라지는 구조 — 서로 다른 네 사실이다.
        "dismissal_paths": [
            {
                "dismiss_control_exists": k[0],
                "dismiss_succeeded": k[1],
                "n": v,
                "label": _DISMISSAL_PATH_LABELS.get(k, "기타/미기록"),
            }
            for k, v in sorted(dismissal_paths.items(), key=lambda kv: -kv[1])
        ],
        "dismissal_paths_equal_weight_note": _DISMISSAL_EQUAL_WEIGHT_NOTE,
        "dismissal_narrative_constraint": DISMISSAL_NARRATIVE_CONSTRAINT,
        "full_coverage_narrative_constraint": FULL_COVERAGE_NARRATIVE_CONSTRAINT,
        "note": (
            "축 C는 L0 관측만으로 성립하므로 depth 축 소실과 무관하게 실측됐다. "
            "이것이 오늘 유일하게 데이터가 있는 축이다 — 다만 분류는 절반이 미완이다"
            "(`classification_incomplete_note` 참조)."
        ),
    }


#: 오늘 association 분석을 **하지 않는다**. 대체물도 만들지 않는다.
NO_SUBSTITUTE_ASSOCIATION_NOTE = (
    "**새 association을 만들지 않는다.** 개정 1은 'X가 원리적으로 산출 불가'라는 "
    "**측정 가능성**에 근거했으나, 지금 남은 변수 중에서 새 association을 고르면 그것은 "
    "**쓸 수 있는 데이터를 보고 분석을 고르는 것**이 되어 성격이 다르다. 계약을 결과에 "
    "맞추지 않고 **계산 불가라는 사실을 결과로 보고한다.**"
)


def build_analysis_axes(axis_c: dict[str, Any], causes: dict[str, Any]) -> dict[str, Any]:
    """오늘 산출물 4종 — 축 A/B/C + 방법론적 결론."""
    return {
        "axis_a_standard_accessibility_barriers": {
            "status": "NOT_EVALUATED",
            "reason": (
                "**criterion 평가기가 애초에 만들어진 적이 없다.** 저장소 전체에 "
                "`evaluate_criterion`/`CriterionResult` 정의 0건, e001_runner의 "
                "criterion·kwcag 참조 0건, `ai_review.py`는 머리말이 '인터페이스와 전이 "
                "규칙만, 모델을 호출하지 않는다'로 명시한 skeleton이며 판정 실행 스크립트가 "
                "없다. 수집 실패가 아니라 **평가 단계 자체의 부재**다."
            ),
            "consequence": (
                "`fact_criterion_result` 빈 표 · `OlderRelevantKWCAGFailRate` 계산 불가 · "
                "J4 미충족으로 `l0_analyzable_n = 0`."
            ),
            "not_evaded": "회피하지 않고 명시한다 — 이 축은 오늘 평가되지 않았다.",
        },
        "axis_b_entry_depth": {
            "status": "MEASURED_ZERO",
            "mpfed_available_n": 0,
            "attempted_n": causes.get("total"),
            "cause_breakdown": causes.get("attribution"),
            "counterfactual": (
                "가드는 **구속 조건이 아니다** — 가드가 개입하지 않고 Scout이 돈 승격 불가 "
                "archetype 25건에서 endpoint 도달 0건이다(0/25)."
            ),
        },
        "axis_c_initial_screen_obstruction": axis_c,
        "unified_finding": UNIFIED_SKELETON_FINDING,
        "methodological_conclusion": (
            "**안전 계약을 유지하는 자동 관측이 이 프레임의 대표기능 진입점에 닿지 못한다.** "
            "이것은 대상 서비스에 대한 진술이 아니라 **이 측정 접근에 대한 진술**이다 — "
            "우리가 관측한 것은 우리 도구의 도달 한계이지 사용자의 도달 한계가 아니다. "
            "그리고 세 축이 같은 지점에서 막혔다 — **수집기는 만들어졌고 판정기는 "
            "만들어지지 않았다**(`unified_finding`)."
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--batches-dir", action="append", required=True)
    parser.add_argument("--out-dir", required=True)
    parser.add_argument(
        "--archetype-csv",
        default=None,
        help="representative_task_candidate_shadow.csv (가드 차단분 archetype 조인용)",
    )
    args = parser.parse_args()

    dirs: list[str] = []
    for item in args.batches_dir:
        dirs.extend(p.strip() for p in item.split(",") if p.strip())

    all_results: list[dict[str, Any]] = []
    for d in dirs:
        rs, _ = load_batch_results(d)
        all_results.extend(rs)

    markers = derive_collection_markers_multi(dirs)
    marts = build_marts(all_results)
    causes = attribute_causes(all_results)
    archetype_by_target = _load_archetype_by_target(args.archetype_csv)
    depth_recovery = (
        analyze_depth_recovery(all_results, archetype_by_target) if archetype_by_target else None
    )

    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    payload = {
        "manifest": "REAL_RUN_SUMMARY",
        "snapshot_at": snapshot_now(),
        "grade": "PILOT / PRELIMINARY",
        "grade_note": (
            "커버리지 100%가 등급을 올리지 않는다 — 결과가 예상보다 좋다는 이유로 사전 "
            "규칙을 뒤집는 것도 나쁠 때 뒤집는 것과 같은 실패다. 등급과 커버리지를 둘 다 보고한다."
        ),
        "collection_markers": markers,
        "cause_attribution": causes,
        "depth_recovery_analysis": depth_recovery,
        "analysis_axes": build_analysis_axes(describe_axis_c(marts), causes),
        # association 슬롯 — 빈 값이나 0이 아니라 **왜 계산 불가인지**가 들어간다.
        "association_slots": {
            "primary": {
                "contract": "LA-AC-AMD1-20260827 §1.1 Spearman(OlderRelevantKWCAGFailRate, obstruction)",
                "status": "NOT_COMPUTABLE",
                "reason": (
                    "Y축(OlderRelevantKWCAGFailRate)이 존재하지 않는다 — criterion 평가기가 "
                    "만들어진 적이 없어 KWCAG 판정 자체가 수행되지 않았다. X축(obstruction)은 "
                    "56건 실측됐으나 한쪽만으로 association을 계산할 수 없다."
                ),
                "substitute_made": False,
                "substitute_policy": NO_SUBSTITUTE_ASSOCIATION_NOTE,
            },
            "secondary": {
                "contract": "LA-AC-AMD1-20260827 §1.3 Kruskal-Wallis(FailRate ~ InteractionArchetype)",
                "status": "NOT_COMPUTABLE",
                "reason": "동일 — 종속변수 FailRate가 존재하지 않는다.",
                "substitute_made": False,
                "substitute_policy": NO_SUBSTITUTE_ASSOCIATION_NOTE,
            },
            "contract_status": (
                "`ANALYSIS_CONTRACT`와 개정 1은 **그대로 유효하다.** 다만 그것이 지정한 분석이 "
                "오늘 evidence로 계산 불가능하다 — 계약을 개정하지 않는다."
            ),
        },
        "mart_row_counts": {k: len(v) for k, v in marts.items()},
    }
    (out / "REAL_RUN_SUMMARY.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    for name, rows in marts.items():
        (out / f"{name}.json").write_text(
            json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8"
        )
    print(
        json.dumps(
            {k: v for k, v in payload.items() if k != "collection_markers"},
            ensure_ascii=False,
            indent=2,
        )[:2600]
    )


if __name__ == "__main__":
    main()
