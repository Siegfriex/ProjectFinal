#!/usr/bin/env python
"""E000_FAST 실제 수집 구동기 — `REAL_TARGET` + `ExecutionScope.E000_FAST`.

    python research/landing_accessibility/scripts/run_e000_fast_real.py \
        --out artifacts/e000_fast_real

    # 무엇이 열릴지만 확인하고 아무것도 열지 않는다
    python research/landing_accessibility/scripts/run_e000_fast_real.py --check-only

**이 스크립트는 실제 서비스에 접속한다.** 그것이 존재 이유다. 다만 접속은 아래 조건이
전부 통과했을 때만 일어난다 — 하나라도 어긋나면 브라우저를 한 번도 켜지 않고 종료한다:

1. `control/P0_RELEASE.json` 을 `git show origin/control/landing-orchestrator:...` 로 읽어
   `status == RELEASED` · `promoted_main_sha` 채워짐 · `e000_allowed == true` 를 확인한다.
   (엔진 층과 배치 층이 **각자** 확인한다.)
2. 계획의 모든 target 이 `E000_FAST_PLAN.json` 의 동결된 목록 안에 있다.
3. 항해 직전 `assert_navigation_allowed` 가 scheme 과 allowlist 를 **다시** 확인한다.

수집 자체의 안전장치는 FIXTURE 경로와 동일하다: target 당 wall-clock cap 360초,
재시도 1회 상한, 실패 격리(한 target 이 실패해도 배치는 계속), 계정 행동 가드
(로그인/결제/OTP/개인정보/CAPTCHA 우회 후보가 있으면 L1 activation 자체를 건너뛴다),
append-only evidence + manifest hash chain.

`--check-only` 는 1·2 만 수행하고 종료한다 — 항해는 하지 않는다.
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
    load_plan,
    validate_real_target_scope_allowlist,
)
from landing_accessibility.engine.firewall import (  # noqa: E402
    E000_FAST_PLAN_CANDIDATES,
    ExecutionMode,
    ExecutionScope,
    evaluate_execution_scope,
    firewall_state,
    load_e000_fast_allowlist,
)

DEFAULT_PLAN = next((p for p in E000_FAST_PLAN_CANDIDATES if p.is_file()), None)


def main() -> int:
    parser = argparse.ArgumentParser(description="E000_FAST 실제 수집 (REAL_TARGET + E000_FAST)")
    parser.add_argument(
        "--plan",
        type=Path,
        default=DEFAULT_PLAN,
        help="E000_FAST_PLAN.json 경로 (기본: 저장소 안의 동결본)",
    )
    parser.add_argument("--out", type=Path, default=Path("artifacts/e000_fast_real"))
    parser.add_argument("--batch-size", type=int, default=3)
    parser.add_argument(
        "--check-only",
        action="store_true",
        help="게이트와 allowlist 만 확인하고 종료한다 — 어떤 항해도 하지 않는다",
    )
    args = parser.parse_args()

    if args.plan is None or not Path(args.plan).is_file():
        print("E000_FAST_PLAN.json 을 찾지 못했다 — --plan 으로 경로를 준다.", file=sys.stderr)
        return 2

    verdict = evaluate_execution_scope(ExecutionScope.E000_FAST)
    allowlist = load_e000_fast_allowlist()
    print("SCOPE VERDICT:", json.dumps(verdict.as_dict(), ensure_ascii=False))
    print("ALLOWLIST:", json.dumps(allowlist.as_dict(), ensure_ascii=False))
    print(
        "FIREWALL:",
        json.dumps(firewall_state(ExecutionScope.E000_FAST), ensure_ascii=False, default=str),
    )

    plan = load_plan(args.plan)
    validate_real_target_scope_allowlist(plan, scope=ExecutionScope.E000_FAST)
    print(f"PLAN OK — {len(plan)} target 전건이 E000_FAST allowlist 안이다.")

    if args.check_only:
        print("--check-only — 항해하지 않고 종료한다.")
        return 0 if verdict.allowed else 1

    runner = BatchRunner(
        out_dir=args.out, fixture_root=RESEARCH / "fixtures", batch_size=args.batch_size
    )
    manifests = runner.run(
        plan,
        execution_mode=ExecutionMode.REAL_TARGET,
        execution_scope=ExecutionScope.E000_FAST,
    )
    for manifest in manifests:
        print(json.dumps(manifest.as_dict(), ensure_ascii=False, default=str))
    print("CHAIN:", json.dumps(runner.ledger.verify_chain(), ensure_ascii=False, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
