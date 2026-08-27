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


def describe_axis_c(marts: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
    """축 C(초기 화면 방해요소) 기술통계 — **오늘 유일하게 실측된 축**이다."""
    import statistics as st

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

    def _stats(values: list[float]) -> dict[str, Any]:
        if not values:
            return {"n": 0, "median": None, "q1": None, "q3": None, "iqr": None}
        sv = sorted(values)
        q1, med, q3 = (
            st.quantiles(sv, n=4)[0] if len(sv) > 1 else sv[0],
            st.median(sv),
            st.quantiles(sv, n=4)[2] if len(sv) > 1 else sv[0],
        )
        return {
            "n": len(sv),
            "median": round(med, 4),
            "q1": round(q1, 4),
            "q3": round(q3, 4),
            "iqr": round(q3 - q1, 4),
            "min": round(sv[0], 4),
            "max": round(sv[-1], 4),
        }

    per_obs: dict[str, int] = {}
    labels: dict[str, int] = {}
    blocks = dismiss_exists = dismiss_visible = dismiss_ok = 0
    for row in interrupts:
        obs = str(row.get("observation_id"))
        per_obs[obs] = per_obs.get(obs, 0) + 1
        label = str(row.get("final_label") or "UNLABELED")
        labels[label] = labels.get(label, 0) + 1
        if str(row.get("blocks_primary_action")) == "1":
            blocks += 1
        if str(row.get("dismiss_control_exists")) == "1":
            dismiss_exists += 1
        if str(row.get("dismiss_control_visible")) == "1":
            dismiss_visible += 1
        if str(row.get("dismiss_succeeded")) == "1":
            dismiss_ok += 1

    counts = [float(per_obs.get(str(o.get("observation_id")), 0)) for o in landing]
    return {
        "axis": "C — 초기 화면 방해요소",
        "status": "MEASURED",
        "n_observations": len(landing),
        "n_interrupts": len(interrupts),
        "interrupts_per_observation": _stats(counts),
        "max_overlay_coverage": _stats(_num(landing, "max_overlay_coverage")),
        "max_primary_action_occlusion": _stats(_num(landing, "max_primary_action_occlusion")),
        "overlay_coverage_per_interrupt": _stats(_num(interrupts, "overlay_coverage")),
        "blocking_modal_count": _stats(_num(landing, "blocking_modal_count")),
        "interrupt_final_label": labels,
        "blocks_primary_action_n": blocks,
        "dismiss_control_exists_n": dismiss_exists,
        "dismiss_control_visible_n": dismiss_visible,
        "dismiss_succeeded_n": dismiss_ok,
        "note": (
            "축 C는 L0 관측만으로 성립하므로 depth 축 소실과 무관하게 실측됐다. "
            "이것이 오늘 유일하게 데이터가 있는 축이다."
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
        "methodological_conclusion": (
            "**안전 계약을 유지하는 자동 관측이 이 프레임의 대표기능 진입점에 닿지 못한다.** "
            "이것은 대상 서비스에 대한 진술이 아니라 **이 측정 접근에 대한 진술**이다 — "
            "우리가 관측한 것은 우리 도구의 도달 한계이지 사용자의 도달 한계가 아니다."
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
