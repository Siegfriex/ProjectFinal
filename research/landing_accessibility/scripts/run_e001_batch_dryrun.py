#!/usr/bin/env python
"""E001 배치 러너 구동기 — **FIXTURE/SHADOW_DRY_RUN 전용. 실제 서비스에 접속하지 않는다.**

    python research/landing_accessibility/scripts/run_e001_batch_dryrun.py \
        --plan tests/fixtures/e000_plan_snapshot.json \
        --mode SHADOW_DRY_RUN \
        --out artifacts/e001_batch_dryrun

    python research/landing_accessibility/scripts/run_e001_batch_dryrun.py \
        --mode FIXTURE \
        --out artifacts/e001_batch_dryrun

`--mode SHADOW_DRY_RUN`은 `--plan`으로 준 실제 `E001_PLAN`(Worker E의
`E000_PLAN.json` 호환 형식)을 그대로 읽어 구조만 검증한다 — 어떤 target도
실행하지 않는다.

`--mode FIXTURE`는 `--plan`을 주지 않으면 이 배치 러너 자신의 fixture 목록
(로컬 synthetic HTML)으로 만든 합성 `E001_PLAN`을 사용한다 — 실제
`E001_PLAN`을 FIXTURE 모드로 돌리려면 모든 target에 `fixture_override`가
있어야 하는데(실제 official_url을 여는 것은 이 스크립트가 존재하는 목적이
아니다), 그런 필드를 가진 실제 계획은 아직 없기 때문이다.

여기서 나오는 결과는 **synthetic fixture/계획 구조에 대한 러너 자체 테스트**이며
실제 서비스에 대한 research finding이 아니다 (`PHASE_GATES.md §4.1` · `§4.3`).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

RESEARCH = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RESEARCH / "src"))

from landing_accessibility.e001_runner.batch import BatchRunner  # noqa: E402
from landing_accessibility.e001_runner.layer_firewall import (  # noqa: E402
    BATCH_LAYER_ALLOWED_MODES,
)
from landing_accessibility.e001_runner.ledger import BatchManifest  # noqa: E402
from landing_accessibility.e001_runner.plan import load_plan  # noqa: E402
from landing_accessibility.engine.firewall import firewall_state  # noqa: E402

FIXTURES = RESEARCH / "fixtures"

#: `--plan` 을 안 줬을 때 쓰는 합성 계획. P-C 가 이미 검증한 fixture 를 그대로 가리킨다
#: (새 fixture 를 만들지 않는다 — 재사용).
_SYNTHETIC_PLAN: dict[str, Any] = {
    "plan_kind": "E001_PLAN",
    "targets": [
        {
            "target_id": "wt-synthetic-content",
            "canonical_service_key": "synthetic_content",
            "official_url": "https://example.invalid/never-opened",
            "interaction_archetype": "CONTENT_OPEN",
            "fixture_override": "simple_article.html",
        },
        {
            "target_id": "wt-synthetic-query",
            "canonical_service_key": "synthetic_query",
            "official_url": "https://example.invalid/never-opened",
            "interaction_archetype": "QUERY",
            "fixture_override": "search_dispatch.html",
        },
        {
            "target_id": "wt-synthetic-unresolved",
            "canonical_service_key": "synthetic_unresolved",
            "official_url": "https://example.invalid/never-opened",
            "interaction_archetype": "UTILITY_ENTRY",
            "fixture_override": "unresolved_route.html",
        },
    ],
}


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--plan", type=Path, default=None, help="E001_PLAN/E000_PLAN JSON 경로")
    parser.add_argument(
        "--mode", choices=sorted(BATCH_LAYER_ALLOWED_MODES), default="SHADOW_DRY_RUN"
    )
    parser.add_argument("--out", type=Path, default=Path("artifacts/e001_batch_dryrun"))
    parser.add_argument("--batch-size", type=int, default=3)
    args = parser.parse_args()

    print("REAL-TARGET FIREWALL (엔진):", json.dumps(firewall_state(), ensure_ascii=False))
    assert firewall_state()["real_target_permitted"] is False

    from landing_accessibility.e001_runner.plan import load_plan_dict

    if args.plan is not None:
        plan = load_plan(args.plan)
    elif args.mode == "SHADOW_DRY_RUN":
        # dry-run 은 항해하지 않으므로 실제 E001_PLAN 스냅샷으로 계획 구조만 검증할 수 있다.
        snapshot = RESEARCH.parents[1] / "tests" / "fixtures" / "e000_plan_snapshot.json"
        plan = load_plan(snapshot) if snapshot.exists() else load_plan_dict(_SYNTHETIC_PLAN)
    else:
        plan = load_plan_dict(_SYNTHETIC_PLAN)

    runner = BatchRunner(out_dir=args.out, fixture_root=FIXTURES, batch_size=args.batch_size)
    manifests: list[BatchManifest] = runner.run(plan, execution_mode=args.mode)

    total = sum(len(m.target_ids) for m in manifests)
    print(f"batches={len(manifests)} targets={total} mode={args.mode}")
    for m in manifests:
        outcomes = [r["outcome"] for r in m.results]
        print(f"  batch {m.batch_index} ({m.batch_id}): {outcomes} hash={m.batch_hash[:12]}…")

    verification = runner.ledger.verify_chain()
    print("ledger verify_chain:", json.dumps(verification, ensure_ascii=False))

    print(
        "\n주의: 위 결과는 synthetic fixture/계획 구조에 대한 러너 자체 테스트다. "
        "실제 서비스에 대한 research finding 이 아니다 (PHASE_GATES.md §4.1 · §4.3)."
    )
    return 0 if verification.get("status") == "OK" else 1


if __name__ == "__main__":
    raise SystemExit(main())
