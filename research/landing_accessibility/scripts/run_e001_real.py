#!/usr/bin/env python
"""E001_FULL 본수집 구동기 — `REAL_TARGET` + `ExecutionScope.E001_FULL`, 워커 분할 실행.

    # 무엇이 열릴지만 확인하고 아무것도 열지 않는다
    python research/landing_accessibility/scripts/run_e001_real.py --worker 01 --check-only

    # 실제 수집 (워커마다 서로 다른 --out 을 준다)
    python research/landing_accessibility/scripts/run_e001_real.py \
        --worker 01 --out artifacts/e001_full_real/worker_01

**이 스크립트는 실제 서비스에 접속한다.** 접속은 아래가 전부 통과했을 때만 일어난다 —
하나라도 어긋나면 브라우저를 한 번도 켜지 않고 종료한다:

1. `control/E001_RELEASE.json` 을 `git show origin/control/landing-orchestrator:...` 로 읽어
   `status == RELEASED` · `promoted_main_sha` 채워짐 · `e001_allowed == true` 를 확인한다.
   **엔진 층과 배치 층이 각자 따로 읽는다** — 한 층의 버그가 두 층을 동시에 뚫지 않는다.
2. `E001_MASTER_PLAN.json` 의 `frozen_plan_hash_candidate` 를 **재계산해 대조**한다.
   동결 계획이 바뀌었으면 실행하지 않는다.
3. 계획의 모든 target 이 `E001_FULL` allowlist 안이다 (배치 시작 전 전건 검사).
4. 항해 직전 `assert_navigation_allowed` 가 scheme 과 allowlist 를 **다시** 확인한다.

target 목록은 `E001_MASTER_PLAN.json` 의 `frozen_collection_order` 순서 그대로이며,
`--worker` 로 지정한 워커에 배정된 key 만 남긴다. **재정렬하지 않는다** — 결과를 보고
순서를 바꾸지 않는다는 outcome-blind 계약이 이 순서에 걸려 있다.

수집 자체의 안전장치는 E000_FAST 경로와 **완전히 동일**하다 (같은 `BatchRunner`):
target 당 wall-clock cap 360초, 재시도 1회 상한, 실패 격리, 계정 행동 가드(입도 무변경),
append-only evidence + manifest hash chain.

`--check-only` 는 1~3 만 수행하고 종료한다 — 항해는 하지 않는다.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

RESEARCH = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RESEARCH / "src"))

from landing_accessibility.e001_runner.batch import BatchRunner  # noqa: E402
from landing_accessibility.e001_runner.plan import (  # noqa: E402
    TargetSpec,
    validate_real_target_scope_allowlist,
)
from landing_accessibility.engine.firewall import (  # noqa: E402
    E001_FROZEN_PLAN_HASH,
    E001_MASTER_PLAN_CANDIDATES,
    E001_WORKER_IDS,
    E001TargetRow,
    ExecutionMode,
    ExecutionScope,
    evaluate_execution_scope,
    firewall_state,
    load_e001_full_allowlist,
    load_e001_full_targets,
)

WORKER_CHOICES = tuple(w.removeprefix("worker_") for w in E001_WORKER_IDS)


def _worker_plan(rows: tuple[E001TargetRow, ...], worker_id: str) -> list[TargetSpec]:
    """frozen 순서를 유지한 채 이 워커에 배정된 target 만 남긴다.

    `T-A-W1-001` §2 시정: 이전에는 `endpoint_definition`만 옮기고 `task_id`·
    `region_definition`·`region_signal_type`·`endpoint_signal_type`을 여기서
    떨어뜨렸다 — `E001TargetRow`(firewall.py)가 CSV에서 다섯 필드를 전부 읽어도,
    `TargetSpec` 생성이 그중 넷을 버리면 lineage가 여기서 끊긴다. 이제 다섯 필드
    전부를 옮긴다.
    """
    return [
        TargetSpec(
            target_id=row.target_id,
            canonical_service_key=row.canonical_service_key,
            official_url=row.official_url,
            interaction_archetype=row.interaction_archetype,
            endpoint_definition=row.endpoint_definition,
            service_name_canonical=row.service_name_canonical,
            task_id=row.task_id,
            region_definition=row.region_definition,
            region_signal_type=row.region_signal_type,
            endpoint_signal_type=row.endpoint_signal_type,
        )
        for row in rows
        if row.worker_id == worker_id
    ]


def main() -> int:
    parser = argparse.ArgumentParser(description="E001_FULL 본수집 (REAL_TARGET + E001_FULL)")
    parser.add_argument(
        "--worker",
        required=True,
        choices=WORKER_CHOICES,
        help="worker_partition.assignments 의 워커 번호 — 이 워커에 배정된 target 만 돈다",
    )
    parser.add_argument(
        "--plan",
        type=Path,
        default=None,
        help="E001_MASTER_PLAN.json 경로 (기본: 저장소 안의 동결본)",
    )
    parser.add_argument("--out", type=Path, default=None)
    parser.add_argument("--batch-size", type=int, default=4)
    parser.add_argument(
        "--check-only",
        action="store_true",
        help="게이트와 allowlist 만 확인하고 종료한다 — 어떤 항해도 하지 않는다",
    )
    args = parser.parse_args()

    worker_id = f"worker_{args.worker}"
    out_dir = args.out or Path("artifacts/e001_full_real") / worker_id

    verdict = evaluate_execution_scope(ExecutionScope.E001_FULL)
    print("WORKER:", worker_id)
    print("SCOPE VERDICT:", json.dumps(verdict.as_dict(), ensure_ascii=False))

    # 동결 계획 → P-B 조인. 해시 재계산 대조가 이 안에서 일어난다 (불일치면 예외).
    rows = load_e001_full_targets(args.plan)
    allowlist = load_e001_full_allowlist(args.plan)
    print("ALLOWLIST:", json.dumps(allowlist.as_dict(), ensure_ascii=False))
    print(
        "FIREWALL:",
        json.dumps(firewall_state(ExecutionScope.E001_FULL), ensure_ascii=False, default=str),
    )
    print(
        "FROZEN PLAN:",
        json.dumps(
            {
                "source": str(
                    args.plan or next((p for p in E001_MASTER_PLAN_CANDIDATES if p.is_file()), None)
                ),
                "frozen_plan_hash_verified": E001_FROZEN_PLAN_HASH,
                "frozen_order_n": len(rows),
            },
            ensure_ascii=False,
        ),
    )

    plan = _worker_plan(rows, worker_id)
    if not plan:
        print(f"{worker_id} 에 배정된 target 이 없다.", file=sys.stderr)
        return 2
    validate_real_target_scope_allowlist(plan, scope=ExecutionScope.E001_FULL, allowlist=allowlist)
    print(f"PLAN OK — {worker_id} {len(plan)} target 전건이 E001_FULL allowlist 안이다.")
    print(
        "WORKER PLAN ORDER:",
        json.dumps([s.canonical_service_key for s in plan], ensure_ascii=False),
    )

    if args.check_only:
        print("--check-only — 항해하지 않고 종료한다.")
        return 0 if verdict.allowed else 1

    runner = BatchRunner(
        out_dir=out_dir, fixture_root=RESEARCH / "fixtures", batch_size=args.batch_size
    )
    manifests = runner.run(
        plan,
        execution_mode=ExecutionMode.REAL_TARGET,
        execution_scope=ExecutionScope.E001_FULL,
    )
    for manifest in manifests:
        print(json.dumps(manifest.as_dict(), ensure_ascii=False, default=str))
    print("CHAIN:", json.dumps(runner.ledger.verify_chain(), ensure_ascii=False, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
