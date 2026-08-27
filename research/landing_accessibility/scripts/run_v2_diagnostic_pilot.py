#!/usr/bin/env python
"""V2_DIAGNOSTIC 12-target REAL diagnostic pilot 전용 구동기 — `T-B-BLK-008`.

    # 무엇이 열릴지만 확인하고 아무것도 열지 않는다
    python research/landing_accessibility/scripts/run_v2_diagnostic_pilot.py --check-only

    # 실제 수집 (ticket_id/run_id 는 A 가 발행한다 — exactly-once idempotency key
    # 성분, D-R0-38. 없으면 브라우저를 켜기 전에 거부된다)
    python research/landing_accessibility/scripts/run_v2_diagnostic_pilot.py \
        --out artifacts/v2_diagnostic_pilot \
        --ticket-id <A 가 발행한 티켓> --run-id <A 가 발행한 수집 회차>

## 이 스크립트가 `run_e001_real.py`와 별개 파일인 이유 (`T-B-BLK-008`, A 결정 (ii))

A 원문: "B 권고 채택. E001_FULL 경로를 한 줄도 건드리지 않아 이미 검증된 59건 경로의
회귀 위험이 0이고, 12건 전용 구동기는 사후 폐기가 쉽다." `run_e001_real.py`는 이
티켓에서 **한 글자도 바뀌지 않았다** — grep으로 확인 가능하다.

## 이 스크립트의 scope 는 코드에 박혀 있다 — 인자로 바뀌지 않는다

**`--scope` 인자가 없다. 환경변수를 읽지 않는다. 설정파일을 읽지 않는다.** 이
스크립트가 열 수 있는 `ExecutionScope`는 `V2_DIAGNOSTIC` **하나뿐**이다 — 아래
코드 어디를 봐도 `ExecutionScope.V2_DIAGNOSTIC`이 리터럴로 박혀 있고, E001 쪽
scope 값을 가리키는 코드 리터럴은(이 문장 자신을 제외하면) 이 파일에 한 번도
등장하지 않는다 — `tests/test_w1_v2_diagnostic_driver.py`가 이 사실을 grep으로
직접 확인한다(자기지시적 문장이 되지 않도록, 여기서는 클래스 접근 표현을 온전한
형태로 적지 않는다).

A 원문(강한 요구): "신규 구동기는 scope 인자를 받지 않는다.
`ExecutionScope.V2_DIAGNOSTIC`을 하드코딩한다 — 인자로 `E001_FULL`을 넘길 수
있으면 구동기 자체가 방어층이 되지 못한다." 편의를 위한 `--scope` 인자도 만들지
않는다 — 그러면 이 파일이 `run_e001_real.py`를 하나 더 만든 것과 다를 바 없어진다.

## 접속은 아래가 전부 통과했을 때만 일어난다

1. `control/V2_DIAGNOSTIC_RELEASE.json`을 `git show origin/control/landing-orchestrator:...`
   로 읽어 `status == RELEASED` · `promoted_main_sha` 채워짐 ·
   `v2_diagnostic_allowed == true` · `manifest_sha256`이 동결값과 일치함을
   확인한다(`evaluate_execution_scope`, `D-R0-82` §4 요구 4·5).
2. `DIAGNOSTIC_PILOT_MANIFEST.json` 원본 바이트의 sha256을 동결값과 대조한다
   (`load_v2_diagnostic_targets`, `D-R0-82` §4 요구 2·3). 표본이 바뀌면 다른
   표본이다 — 불일치·부재·읽기실패는 전부 거부.
3. 12 target 전건이 `V2_DIAGNOSTIC` allowlist 안이다(배치 시작 전 전건 검사).
4. 항해 직전 `assert_navigation_allowed`가 scheme과 allowlist를 **다시** 확인한다.

target 목록은 manifest의 `targets` 배열 순서 그대로다(`order_index`) — **재정렬하지
않는다**. 워커 분할이 없다 — 12건뿐이라 이 구동기 하나가 전건을 순회한다.

## `canonical_service_key` — manifest 에 없는 필드

`DIAGNOSTIC_PILOT_MANIFEST.json`에는 P-B의 `canonical_service_key`가 없다(`service`는
사람이 읽는 한국어 표기일 뿐이다). `TargetSpec.canonical_service_key`는 타입상
필수라 `web_target_id`를 그대로 채워 넣지만(레코드 식별 목적), allowlist 검사에는
**절대 쓰지 않는다** — `assert_target_allowlisted`를 `canonical_service_key` 없이
직접 호출한다(`_preflight_validate` 참조). `load_v2_diagnostic_allowlist`의
`canonical_service_keys`는 의도적으로 항상 빈 집합이므로, 여기서 그 값을 검사에
섞으면 12건 전부가 거짓으로 거부된다.

수집 자체의 안전장치는 E000_FAST/E001_FULL 경로와 **완전히 동일**하다 (같은
`BatchRunner`): target당 wall-clock cap 360초, 재시도 1회 상한, 실패 격리, 계정
행동 가드(guard.py, 입도 무변경), append-only evidence + manifest hash chain.

`--check-only`는 1~3만 수행하고 종료한다 — 항해는 하지 않는다.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

RESEARCH = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RESEARCH / "src"))

from landing_accessibility.e001_runner.batch import BatchRunner  # noqa: E402
from landing_accessibility.e001_runner.plan import TargetSpec  # noqa: E402
from landing_accessibility.engine.firewall import (  # noqa: E402
    DIAGNOSTIC_PILOT_MANIFEST_SHA256,
    ExecutionMode,
    ExecutionScope,
    TargetAllowlist,
    V2DiagnosticTargetRow,
    assert_target_allowlisted,
    evaluate_execution_scope,
    firewall_state,
    load_v2_diagnostic_allowlist,
    load_v2_diagnostic_targets,
)


def _plan_from_rows(rows: tuple[V2DiagnosticTargetRow, ...]) -> list[TargetSpec]:
    """manifest 행을 `TargetSpec`으로 옮긴다. 순서를 보존한다(`order_index`로 이미
    정렬돼 들어온다 — 여기서 재정렬하지 않는다).

    `canonical_service_key`는 `web_target_id`를 그대로 쓴다(모듈 docstring
    "canonical_service_key — manifest 에 없는 필드" 참고) — 레코드 식별용일 뿐,
    allowlist 검사에는 쓰이지 않는다(`_preflight_validate`).
    """
    return [
        TargetSpec(
            target_id=row.web_target_id,
            canonical_service_key=row.web_target_id,
            official_url=row.official_url,
            interaction_archetype=row.interaction_archetype,
            service_name_canonical=row.service_name_canonical,
        )
        for row in rows
    ]


def _preflight_validate(plan: list[TargetSpec], allowlist: TargetAllowlist) -> None:
    """배치 시작 **전에** 12 target 전건이 allowlist 안인지 확인한다 — 하나라도
    벗어나면 아무것도 열지 않고 여기서 실패한다.

    `plan.validate_real_target_scope_allowlist`를 쓰지 않는다 — 그 함수는
    `spec.canonical_service_key`를 무조건 `assert_target_allowlisted`로 넘기는데,
    이 allowlist의 `canonical_service_keys`는 의도적으로 빈 집합이라(모듈
    docstring 참고) 그러면 12건 전부가 거짓으로 거부된다. 여기서는
    `canonical_service_key`를 아예 넘기지 않는다 — target_id·url만 검사한다.
    """
    for spec in plan:
        assert_target_allowlisted(
            ExecutionScope.V2_DIAGNOSTIC,
            target_id=spec.target_id,
            url=spec.official_url,
            allowlist=allowlist,
        )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "V2_DIAGNOSTIC 12-target REAL diagnostic pilot 전용 구동기. "
            "scope 인자는 없다 — ExecutionScope.V2_DIAGNOSTIC 하드코딩(T-B-BLK-008)."
        )
    )
    parser.add_argument("--out", type=Path, default=Path("artifacts/v2_diagnostic_pilot"))
    parser.add_argument("--batch-size", type=int, default=4)
    parser.add_argument(
        "--manifest",
        type=Path,
        default=None,
        help=(
            "DIAGNOSTIC_PILOT_MANIFEST.json 경로 (기본: 저장소 안의 동결본). "
            "어느 경로를 주더라도 sha256이 동결값과 다르면 거부된다 — 표본을 "
            "바꾸는 인자가 아니라 파일 위치만 바꾸는 인자다."
        ),
    )
    parser.add_argument(
        "--check-only",
        action="store_true",
        help="게이트와 allowlist 만 확인하고 종료한다 — 어떤 항해도 하지 않는다",
    )
    parser.add_argument(
        "--ticket-id",
        default=None,
        help=(
            "exactly-once idempotency key 성분 — A 가 발행하는 티켓 id. "
            "--check-only 가 아니면 필수(없으면 BatchRunner 가 브라우저를 켜기 전에 "
            "ExactlyOnceConfigError 로 거부한다, D-R0-38)."
        ),
    )
    parser.add_argument(
        "--run-id",
        default=None,
        help="exactly-once idempotency key 성분 — A 가 발행하는 수집 회차 id.",
    )
    parser.add_argument(
        "--lock-dir",
        type=Path,
        default=None,
        help="exactly-once lock 디렉터리 override (기본: 공유 transport 정본).",
    )
    args = parser.parse_args(argv)

    # `T-B-BLK-008` 강한 요구 — scope 는 리터럴이다. 아래 두 줄에 `ExecutionScope.
    # V2_DIAGNOSTIC` 이 그대로 등장한다(변수 경유·간접 참조 없음) — `args`·환경변수·
    # 설정파일 어느 것도 이 값에 관여하지 않는다.
    verdict = evaluate_execution_scope(ExecutionScope.V2_DIAGNOSTIC)
    print("SCOPE VERDICT:", json.dumps(verdict.as_dict(), ensure_ascii=False))

    rows = load_v2_diagnostic_targets(args.manifest)
    allowlist = load_v2_diagnostic_allowlist(args.manifest)
    print("ALLOWLIST:", json.dumps(allowlist.as_dict(), ensure_ascii=False))
    print(
        "FIREWALL:",
        json.dumps(firewall_state(ExecutionScope.V2_DIAGNOSTIC), ensure_ascii=False, default=str),
    )
    print(
        "MANIFEST:",
        json.dumps(
            {
                "source": allowlist.source_path,
                "frozen_manifest_sha256_verified": DIAGNOSTIC_PILOT_MANIFEST_SHA256,
                "target_count": len(rows),
            },
            ensure_ascii=False,
        ),
    )

    plan = _plan_from_rows(rows)
    if not plan:
        print("manifest 에서 target 을 하나도 읽지 못했다.", file=sys.stderr)
        return 2
    _preflight_validate(plan, allowlist)
    print(f"PLAN OK — {len(plan)} target 전건이 V2_DIAGNOSTIC allowlist 안이다.")
    print(
        "PLAN ORDER:",
        json.dumps(
            [{"web_target_id": s.target_id, "url": s.official_url} for s in plan],
            ensure_ascii=False,
        ),
    )

    if args.check_only:
        print("--check-only — 항해하지 않고 종료한다.")
        return 0 if verdict.allowed else 1

    runner = BatchRunner(
        out_dir=args.out,
        fixture_root=RESEARCH / "fixtures",
        batch_size=args.batch_size,
        ticket_id=args.ticket_id,
        run_id=args.run_id,
        lock_dir=args.lock_dir,
    )
    manifests = runner.run(
        plan,
        execution_mode=ExecutionMode.REAL_TARGET,
        execution_scope=ExecutionScope.V2_DIAGNOSTIC,
    )
    for manifest in manifests:
        print(json.dumps(manifest.as_dict(), ensure_ascii=False, default=str))
    print("CHAIN:", json.dumps(runner.ledger.verify_chain(), ensure_ascii=False, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
