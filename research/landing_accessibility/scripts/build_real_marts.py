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


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--batches-dir", action="append", required=True)
    parser.add_argument("--out-dir", required=True)
    args = parser.parse_args()

    dirs: list[str] = []
    for item in args.batches_dir:
        dirs.extend(p.strip() for p in item.split(",") if p.strip())

    results, _files = load_batch_results(dirs[0])
    all_results: list[dict[str, Any]] = []
    for d in dirs:
        rs, _ = load_batch_results(d)
        all_results.extend(rs)

    markers = derive_collection_markers_multi(dirs)
    marts = build_marts(all_results)
    causes = attribute_causes(all_results)

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
