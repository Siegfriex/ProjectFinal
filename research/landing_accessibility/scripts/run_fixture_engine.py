#!/usr/bin/env python
"""P-C fixture 엔진 구동기 — **fixture 전용. 실제 서비스에 접속하지 않는다.**

    python research/landing_accessibility/scripts/run_fixture_engine.py \
        --out artifacts/pc_fixture

산출:
    <out>/evidence/<run_id>/    L0 evidence run (manifest + run.json)
    <out>/l0_observations.json  관측 요약
    <out>/l1_task_entries.json  task 종료상태 · Depth · episode
    <out>/task_manifests/       Path Freeze 산출물
    <out>/failure_injection.json 실패주입 보고서

여기서 나오는 PASS/FAIL 은 **synthetic fixture 에 대한 engine test 결과**이며
실제 서비스에 대한 research finding 이 아니다 (`PHASE_GATES §4.1` · `§4.3` · `§4.6`).
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

RESEARCH = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RESEARCH / "src"))

from landing_accessibility.engine import failure_injection as fi  # noqa: E402
from landing_accessibility.engine.evidence import EvidenceRun  # noqa: E402
from landing_accessibility.engine.firewall import ExecutionMode, firewall_state  # noqa: E402
from landing_accessibility.engine.l0_collector import FixtureTarget, L0Collector  # noqa: E402
from landing_accessibility.engine.l1_engine import (  # noqa: E402
    Scout,
    ScoutBudget,
    TaskDefinition,
    replay,
)
from landing_accessibility.engine.provenance import ShadowProvenance  # noqa: E402
from landing_accessibility.engine.reporting import archetype_mpfed_summary  # noqa: E402
from landing_accessibility.engine.vocabulary import InteractionArchetype as A  # noqa: E402
from landing_accessibility.engine.vocabulary import RegionSignalType as R  # noqa: E402

FIXTURES = RESEARCH / "fixtures"

L0_TARGETS = [
    "simple_article.html",
    "search_dispatch.html",
    "auth_login_gate.html",
    "auth_identity_gate.html",
    "auth_ambiguous_gate.html",
    "blocking_modal.html",
    "promo_modal.html",
    "cookie_consent.html",
    "motion_banner.html",
    "missing_accessible_name.html",
    "small_target.html",
    "low_contrast_control.html",
    "overlay_primary_action.html",
    "depth_path_0.html",
    "depth_path_1.html",
    "depth_path_3.html",
    "unresolved_route.html",
]

_CONTENT = TaskDefinition("T-CONTENT", A.CONTENT_OPEN, "ARTICLE_LIST_REGION", "ARTICLE_BODY_OPEN")
_GATE = (R.GATE_SIGNAL, R.GATE_SIGNAL)

L1_CASES: list[tuple[str, TaskDefinition]] = [
    ("depth_path_0.html", _CONTENT),
    ("depth_path_1.html", _CONTENT),
    ("depth_path_3.html", _CONTENT),
    ("blocking_modal.html", TaskDefinition("T-MODAL", A.CONTENT_OPEN, None, "ARTICLE_BODY_OPEN")),
    ("promo_modal.html", TaskDefinition("T-PROMO", A.CONTENT_OPEN, None, "ARTICLE_BODY_OPEN")),
    (
        "search_dispatch.html",
        TaskDefinition(
            "T-QUERY", A.QUERY, None, "QUERY_SUBMITTED", R.FORM_STRUCTURE, R.FORM_STRUCTURE
        ),
    ),
    (
        "auth_login_gate.html",
        TaskDefinition("T-FIN-LOGIN", A.FINANCIAL_ACTION_ENTRY, None, "FIN", *_GATE),
    ),
    (
        "auth_login_gate.html",
        TaskDefinition("T-COM-LOGIN", A.COMMUNICATION_ENTRY, None, "THREAD", *_GATE),
    ),
    (
        "auth_login_gate.html",
        TaskDefinition("T-QRY-GATE", A.QUERY, None, "QUERY_SUBMITTED", *_GATE),
    ),
    (
        "auth_identity_gate.html",
        TaskDefinition("T-FIN-ID", A.FINANCIAL_ACTION_ENTRY, None, "FIN", *_GATE),
    ),
    (
        "auth_identity_gate.html",
        TaskDefinition("T-COM-ID", A.COMMUNICATION_ENTRY, None, "THREAD", *_GATE),
    ),
    (
        "auth_ambiguous_gate.html",
        TaskDefinition("T-FIN-AMB", A.FINANCIAL_ACTION_ENTRY, None, "FIN", *_GATE),
    ),
    (
        "unresolved_route.html",
        TaskDefinition(
            "T-UNRES", A.UTILITY_ENTRY, None, None, R.CODEBOOK_PENDING, R.CODEBOOK_PENDING
        ),
    ),
]


def _write(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", default="artifacts/pc_fixture", type=Path)
    parser.add_argument("--skip-l0", action="store_true")
    parser.add_argument("--skip-l1", action="store_true")
    args = parser.parse_args()

    out = Path(args.out).resolve()
    provenance = ShadowProvenance().as_dict()
    run_id = "pc-fixture-" + datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")

    print("REAL-TARGET FIREWALL:", json.dumps(firewall_state(), ensure_ascii=False))
    assert firewall_state()["real_target_permitted"] is False

    header = {"provenance": provenance, "firewall": firewall_state(), "run_id": run_id}

    if not args.skip_l0:
        run = EvidenceRun.create(out / "evidence", run_id, execution_mode=ExecutionMode.FIXTURE)
        collector = L0Collector(run, fixture_root=FIXTURES)
        rows = []
        for name in L0_TARGETS:
            obs = collector.collect(
                FixtureTarget(web_target_id=f"wt-{name}", fixture=name, archetype=A.UTILITY_ENTRY)
            )
            print(f"L0 {name:32s} {obs.measurement_status:28s} interrupts={len(obs.interrupts)}")
            rows.append(obs.as_dict())
        run.seal()
        verification = run.verify()
        print("evidence run:", verification["status"], verification["entries"], "artifacts")
        _write(
            out / "l0_observations.json",
            {**header, "verification": verification, "observations": rows},
        )

    if not args.skip_l1:
        scout = Scout(fixture_root=FIXTURES, budget=ScoutBudget())
        entries, replays = [], []
        for fixture, task in L1_CASES:
            entry, manifest = scout.scout(
                web_target_id=f"wt-{fixture}-{task.task_id}", entry_fixture=fixture, task=task
            )
            print(
                f"L1 {fixture:26s} {task.archetype.value:23s} {entry.endpoint_status:26s} "
                f"detail={entry.endpoint_status_detail} "
                f"NED={entry.ned} IED={entry.ied} MPFED={entry.mpfed} "
                f"fd={entry.forced_dismissal_count} budget={entry.budget_reason}"
            )
            entries.append(entry.as_dict())
            if manifest is not None:
                _write(
                    out / "task_manifests" / f"{task.task_id}_{fixture}.json", manifest.as_dict()
                )
                replays.append({"task_id": task.task_id, **replay(manifest, fixture_root=FIXTURES)})
        _write(
            out / "l1_task_entries.json",
            {
                **header,
                "entries": entries,
                "replays": replays,
                "archetype_summary": archetype_mpfed_summary(entries),
            },
        )

    report = fi.run_all(out / "injection_work")
    _write(out / "failure_injection.json", report)
    print(
        f"failure injection: {report['as_expected']}/{report['total']} as expected "
        f"(blocked={report['blocked_cases']} must_pass={report['must_pass_cases']})"
    )
    print(
        "\n주의: 위 결과는 synthetic fixture 에 대한 engine test 다. "
        "실제 서비스에 대한 research finding 이 아니다."
    )
    return 0 if not report["failures"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
