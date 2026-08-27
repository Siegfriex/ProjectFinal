#!/usr/bin/env python
"""Claude C recovery audit — partial-depth semantics 독립 검증 (fixture 전용, 실제 서비스 미접속).

B 엔진(collector 222ef2c)의 Scout 를 이 디렉터리의 fixture 로 직접 호출해
A1 §1.4·§1.5 / A2 §1.5.1·§1.9 P-2 가 정한 NED/IED/MPFED NULL 규칙을 대조한다.
엔진 소스는 읽기 전용이다. 산출물은 fixtures/_out 과 PARTIAL_DEPTH_RESULTS.json 뿐이다.
"""

from __future__ import annotations

import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
ENGINE_SRC = Path(
    "/home/sieg/projects-wsl/ProjectFinal/.agent_worktrees/claude_b_e001_worker_01"
    "/research/landing_accessibility/src"
)
sys.path.insert(0, str(ENGINE_SRC))

from landing_accessibility.engine.evidence import EvidenceRun  # noqa: E402
from landing_accessibility.engine.firewall import ExecutionMode, firewall_state  # noqa: E402
from landing_accessibility.engine.l1_engine import Scout, ScoutBudget, TaskDefinition  # noqa: E402
from landing_accessibility.engine.vocabulary import InteractionArchetype as A  # noqa: E402
from landing_accessibility.engine.vocabulary import RegionSignalType as R  # noqa: E402

REGION = "ITEM_LIST_REGION"
ENDPOINT = "ITEM_DETAIL_OPEN"
PENDING = (R.CODEBOOK_PENDING, R.CODEBOOK_PENDING)

# (case_id, entry fixture, TaskDefinition, expected, contract reference)
CASES: list[tuple[str, str, TaskDefinition, dict[str, Any], str]] = [
    (
        "CASE1",
        "case1_landing_region.html",
        TaskDefinition("T-C1", A.ITEM_DETAIL, REGION, ENDPOINT),
        {"ned": 0, "ied": None, "mpfed": None, "endpoint_reached": 0,
         "area_signal_status": "OBSERVED",
         "endpoint_status_not": "FUNCTION_ENDPOINT_REACHED"},
        "A1 §1.4 행1 (k=0) · §1.5 행3 (영역만 관측 → OBSERVED, NED=k, IED/MPFED NULL)",
    ),
    (
        "CASE2",
        "case2_landing.html",
        TaskDefinition("T-C2", A.ITEM_DETAIL, REGION, ENDPOINT),
        {"ned": 2, "ied": None, "mpfed": None, "endpoint_reached": 0,
         "area_signal_status": "OBSERVED", "endpoint_status": "AUTH_GATE_REACHED"},
        "A1 §1.5 행3 · A2 §1.5.1a 표 4행 (ITEM_DETAIL 은 모든 gate 가 AUTH_GATE_REACHED, MPFED NULL)",
    ),
    (
        "CASE3",
        "case3_landing.html",
        TaskDefinition("T-C3", A.ITEM_DETAIL, REGION, ENDPOINT),
        {"ned": 2, "ied": 1, "mpfed": 3, "endpoint_reached": 1,
         "area_signal_status": "OBSERVED", "endpoint_status": "FUNCTION_ENDPOINT_REACHED"},
        "A1 §1.3 · §1.5 행1",
    ),
    (
        "CASE4",
        "case4_landing.html",
        TaskDefinition("T-C4", A.ITEM_DETAIL, REGION, None),
        {"ned": 0, "ied": None, "mpfed": None, "endpoint_reached": 0,
         "area_signal_status": "OBSERVED",
         "endpoint_status_not": "FUNCTION_ENDPOINT_REACHED"},
        "A1 §1.5 행3 — endpoint 정의 불명이어도 관측된 영역(k=0)은 보존, IED/MPFED NULL, 강제 산출 0",
    ),
    (
        "CASE4b",
        "case4b_landing.html",
        TaskDefinition("T-C4b", A.ITEM_DETAIL, REGION, None),
        {"ned": 0, "ied": None, "mpfed": None, "endpoint_reached": 0,
         "area_signal_status": "OBSERVED", "endpoint_status": "AUTH_GATE_REACHED"},
        "진단 보조 — CASE4 와 같은 task, 종료가 gate 로 확정되는 변형 (NED 소실이 UNRESOLVED 경로 한정인지 분리)",
    ),
    (
        "CASE5a",
        "case5_landing.html",
        TaskDefinition("T-C5a", A.ITEM_DETAIL, None, None, *PENDING),
        {"endpoint_reached": 0, "endpoint_status_not": "FUNCTION_ENDPOINT_REACHED",
         "manifest_frozen": False},
        "A2 §1.9 규칙 P-2 — CODEBOOK_PENDING task 는 FROZEN 전이 불가. E001 실제 구성(executor.py:68-75)",
    ),
    (
        "CASE5b",
        "case5_landing.html",
        TaskDefinition("T-C5b", A.ITEM_DETAIL, REGION, ENDPOINT, *PENDING),
        {"endpoint_reached": 0, "endpoint_status_not": "FUNCTION_ENDPOINT_REACHED",
         "manifest_frozen": False},
        "A2 §1.9 규칙 P-2 — signal_type=CODEBOOK_PENDING 인 채로 정의 문자열만 있을 때 false 승격이 막히는가",
    ),
]


def _check(expected: dict[str, Any], actual: dict[str, Any]) -> list[str]:
    fails: list[str] = []
    for key, want in expected.items():
        if key == "endpoint_status_not":
            if actual["endpoint_status"] == want:
                fails.append(f"endpoint_status == {want} (금지)")
            continue
        got = actual.get(key)
        if got != want:
            fails.append(f"{key}: expected={want!r} actual={got!r}")
    return fails


def main() -> int:
    assert firewall_state()["real_target_permitted"] is False
    out_dir = HERE / "_out"
    run_id = "partial-depth-" + datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    run = EvidenceRun.create(out_dir / "evidence", run_id, execution_mode=ExecutionMode.FIXTURE)
    scout = Scout(
        fixture_root=HERE, budget=ScoutBudget(), execution_mode=ExecutionMode.FIXTURE, run=run
    )

    results: list[dict[str, Any]] = []
    for case_id, fixture, task, expected, ref in CASES:
        entry, manifest = scout.scout(
            web_target_id=f"wt-{case_id}", entry_fixture=fixture, task=task
        )
        actual = {
            "ned": entry.ned,
            "ied": entry.ied,
            "mpfed": entry.mpfed,
            "endpoint_status": entry.endpoint_status,
            "endpoint_status_detail": entry.endpoint_status_detail,
            "endpoint_reached": entry.endpoint_reached,
            "area_signal_status": entry.area_signal_status,
            "budget_reason": entry.budget_reason,
            "manifest_frozen": manifest is not None,
            "steps": [
                {
                    "step_index": s.step_index,
                    "url_tail": s.url.rsplit("/", 1)[-1],
                    "area": s.area_signal_detected,
                    "endpoint": s.endpoint_signal_detected,
                    "gate": s.auth_gate_detected,
                    "depth_segment": s.depth_segment,
                }
                for s in entry.steps
            ],
            "notes": entry.notes,
        }
        fails = _check(expected, actual)
        verdict = "PASS" if not fails else "FAIL"
        print(
            f"{case_id:7s} {verdict:4s} NED={actual['ned']} IED={actual['ied']} "
            f"MPFED={actual['mpfed']} status={actual['endpoint_status']} "
            f"area={actual['area_signal_status']} budget={actual['budget_reason']} "
            f"manifest={actual['manifest_frozen']}"
            + (f"  <- {'; '.join(fails)}" if fails else "")
        )
        results.append(
            {
                "case": case_id,
                "fixture": fixture,
                "task": {
                    "archetype": task.archetype.value,
                    "region_definition": task.region_definition,
                    "endpoint_definition": task.endpoint_definition,
                    "region_signal_type": task.region_signal_type.value,
                    "endpoint_signal_type": task.endpoint_signal_type.value,
                    "mapping_frozen_allowed": task.mapping_frozen_allowed(),
                },
                "contract": ref,
                "expected": expected,
                "actual": actual,
                "verdict": verdict,
                "failures": fails,
            }
        )

    payload = {
        "note": "synthetic fixture 에 대한 engine test 결과다. 실제 서비스에 대한 research finding 이 아니다.",
        "engine_src": str(ENGINE_SRC),
        "engine_commit": "222ef2c28ed5971b3c9f8b07120b7627d2617476",
        "fixture_root": str(HERE),
        "run_id": run_id,
        "firewall": firewall_state(),
        "summary": {
            "pass": sum(r["verdict"] == "PASS" for r in results),
            "fail": sum(r["verdict"] == "FAIL" for r in results),
        },
        "results": results,
    }
    (HERE / "PARTIAL_DEPTH_RESULTS.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"\n{payload['summary']}  -> {HERE / 'PARTIAL_DEPTH_RESULTS.json'}")
    return 0 if payload["summary"]["fail"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
