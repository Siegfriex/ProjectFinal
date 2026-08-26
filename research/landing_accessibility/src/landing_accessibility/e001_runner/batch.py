"""E001 배치 오케스트레이터 — `E001_PLAN`을 append-only batch로 순회한다.

이 모듈이 하는 일은 정확히 네 가지이며, 전부 이 파일 안에서 조립만 한다
(엔진 재구현 없음):

1. 진입점에서 **두 개의 독립된** REAL_TARGET firewall을 통과해야 한다 —
   `layer_firewall.assert_batch_execution_mode_safe`(이 층 고유)와
   `landing_accessibility.engine.firewall.assert_mode_allowed`(엔진 정본).
2. `plan`을 `batch_size`씩 잘라 순회하고, target 하나는 `executor.py`의
   FIXTURE 실행기(또는 테스트가 주입한 `target_executor`)로 실행한다.
3. target 실행은 `retry.run_with_retry`로 감싸 정확히 1회까지만 재시도한다.
4. batch 하나가 끝나면 `ledger.BatchLedger`로 봉인한다 — 실패한 target이
   있어도 batch 자체는 끝까지 순회하고 봉인한다(격리).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Protocol

from landing_accessibility.engine.firewall import (
    ExecutionMode,
    FirewallError,
    assert_mode_allowed,
)
from landing_accessibility.engine.provenance import ShadowProvenance
from landing_accessibility.engine.vocabulary import MeasurementStatus, is_measurement_failed

from .guard import AccountActionBlockedError
from .layer_firewall import BatchRealTargetBlockedError, assert_batch_execution_mode_safe
from .ledger import BatchLedger, BatchManifest
from .outcomes import TargetOutcome, is_failure_isolated, map_engine_result
from .plan import TargetSpec, validate_no_real_navigation_fields_required
from .retry import MAX_RETRIES_PER_TARGET, run_with_retry

#: 이 lane 이 갈라져 나온 base. `landing_accessibility.engine.provenance.BASE_SHA`
#: (P-C의 base, d5f1da5)와 **다르다** — 이 러너는 그 뒤 `agent/landing-v2-exec`
#: 를 base로 삼는다 (`PHASE_GATES.md §4.3` 요구대로 lane마다 자기 base_sha를 적는다).
E001_RUNNER_BASE_SHA = "2025e56"
E001_RUNNER_SHADOW_LANE = "E001_RUNNER"

DEFAULT_BATCH_SIZE = 3


class TargetExecutor(Protocol):
    def __call__(self, target: TargetSpec) -> dict[str, Any]: ...


@dataclass
class TargetResult:
    target_id: str
    outcome: str
    attempts: int
    detail: dict[str, Any] = field(default_factory=dict)
    error: str | None = None
    same_cause_on_retry: bool | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "target_id": self.target_id,
            "outcome": self.outcome,
            "attempts": self.attempts,
            "detail": self.detail,
            "error": self.error,
            "same_cause_on_retry": self.same_cause_on_retry,
        }


def _utc_now_iso() -> str:
    return datetime.now(UTC).isoformat(timespec="microseconds").replace("+00:00", "Z")


def _chunk(items: list[TargetSpec], size: int) -> list[list[TargetSpec]]:
    if size < 1:
        raise ValueError(f"batch_size 는 1 이상이어야 한다: {size}")
    return [items[i : i + size] for i in range(0, len(items), size)]


def _is_retryable_engine_failure(result: dict[str, Any]) -> bool:
    """엔진이 **내부적으로 잡아** 반환한(예외로 새지 않은) 측정 실패인가.

    `L0Collector.collect()`는 브라우저/타임아웃 오류를 스스로 catch해 `L0Observation`
    으로 돌려준다 — 예외가 아니라 `measurement_status`값으로 나타난다. 그래서 이
    검사가 없으면 그런 실패는 재시도 대상에서 조용히 빠진다. 엔진 자신의
    `is_measurement_failed` 술어를 그대로 재사용한다(재구현하지 않는다).
    """
    status = result.get("measurement_status")
    if not status:
        return False
    try:
        return is_measurement_failed(MeasurementStatus(status))
    except ValueError:
        return False


class BatchRunner:
    """`E001_PLAN`을 append-only batch로 순회하는 오케스트레이터."""

    def __init__(
        self,
        *,
        out_dir: Path | str,
        fixture_root: Path | str,
        batch_size: int = DEFAULT_BATCH_SIZE,
    ) -> None:
        self.out_dir = Path(out_dir)
        self.fixture_root = Path(fixture_root)
        self.batch_size = batch_size
        self.ledger = BatchLedger(self.out_dir)

    # ── 진입점 ───────────────────────────────────────────────────────────
    def run(
        self,
        plan: list[TargetSpec],
        *,
        execution_mode: object,
        target_executor: TargetExecutor | None = None,
    ) -> list[BatchManifest]:
        """`plan`을 batch로 나눠 순회하고 봉인된 `BatchManifest` 목록을 돌려준다.

        REAL_TARGET을 요청하면 **두 firewall 모두** 통과하지 못하고 즉시 실패한다.
        어느 한쪽만 통과시켜도 이 함수는 진행하지 않는다 — 순서와 무관하게 둘 다
        호출된다.
        """
        layer_mode = assert_batch_execution_mode_safe(execution_mode)
        engine_mode = assert_mode_allowed(execution_mode)  # 엔진 정본 firewall — 별개 재확인
        assert layer_mode == engine_mode.value  # 두 firewall이 같은 값을 봤다는 것을 명시

        if engine_mode is ExecutionMode.SHADOW_DRY_RUN:
            return [self._run_dry(plan)]

        if engine_mode is not ExecutionMode.FIXTURE:
            # assert_mode_allowed가 REAL_TARGET을 이미 막았으므로 이론상 도달 불가능하지만,
            # 새 execution_mode가 언젠가 추가돼도 이 함수가 조용히 통과시키지 않게 한다.
            raise FirewallError(f"이 배치 러너는 FIXTURE/SHADOW_DRY_RUN만 실행한다: {engine_mode}")

        validate_no_real_navigation_fields_required(plan)
        executor = target_executor or self._default_fixture_executor

        manifests: list[BatchManifest] = []
        for batch_index, batch_targets in enumerate(_chunk(plan, self.batch_size), start=1):
            target_results = [self._run_target_isolated(t, executor) for t in batch_targets]
            manifest = self._seal_batch(batch_index, batch_targets, target_results, "FIXTURE")
            manifests.append(manifest)
        return manifests

    # ── target 하나 ──────────────────────────────────────────────────────
    def _run_target_isolated(self, target: TargetSpec, executor: TargetExecutor) -> TargetResult:
        """target 하나를 실행한다. **여기서 던진 예외는 이 함수를 벗어나지 않는다**
        (firewall 예외 제외) — 그것이 "실패 격리"의 코드 형태다.
        """

        def attempt() -> dict[str, Any]:
            result = executor(target)
            if result.get("outcome") == TargetOutcome.ACCOUNT_ACTION_BLOCKED.value:
                raise AccountActionBlockedError(
                    f"target {target.target_id!r}: "
                    f"category={result.get('blocked_category')} "
                    f"reason={result.get('blocked_reason')}"
                )
            if _is_retryable_engine_failure(result):
                raise RuntimeError(
                    f"engine measurement_status={result.get('measurement_status')!r} "
                    f"(target={target.target_id!r})"
                )
            return result

        try:
            retry_outcome = run_with_retry(attempt)
        except AccountActionBlockedError as exc:
            return TargetResult(
                target_id=target.target_id,
                outcome=TargetOutcome.ACCOUNT_ACTION_BLOCKED.value,
                attempts=1,
                error=str(exc),
            )
        except (BatchRealTargetBlockedError, FirewallError):
            raise  # firewall 위반은 격리 대상이 아니다 — 배치 전체를 세운다

        if retry_outcome.succeeded:
            value = retry_outcome.value if isinstance(retry_outcome.value, dict) else {}
            outcome = map_engine_result(value)
            return TargetResult(
                target_id=target.target_id,
                outcome=outcome.value,
                attempts=retry_outcome.attempts,
                detail=value,
            )

        return TargetResult(
            target_id=target.target_id,
            outcome=TargetOutcome.SKIPPED_RETRY_EXHAUSTED.value,
            attempts=retry_outcome.attempts,
            error=retry_outcome.last_error,
            same_cause_on_retry=retry_outcome.same_cause_on_retry,
        )

    # ── 기본 실행기 ──────────────────────────────────────────────────────
    def _default_fixture_executor(self, target: TargetSpec) -> dict[str, Any]:
        from landing_accessibility.engine.evidence import EvidenceRun

        from .executor import run_l0

        run_id = f"e001-{target.target_id}-{_utc_now_iso().replace(':', '').replace('.', '')}"
        run = EvidenceRun.create(
            self.out_dir / "evidence",
            run_id,
            execution_mode=ExecutionMode.FIXTURE,
            provenance=ShadowProvenance(
                base_sha=E001_RUNNER_BASE_SHA, shadow_lane=E001_RUNNER_SHADOW_LANE
            ),
        )
        result = run_l0(target, fixture_root=self.fixture_root, run=run)
        run.seal()
        return result

    def l1_executor(self, target: TargetSpec) -> dict[str, Any]:
        """가드를 거친 L1 activation까지 수행하는 실행기. `run()`의 기본값이 아니라
        `target_executor=runner.l1_executor`로 명시적으로 주입해야 쓰인다 — L0만으로
        충분한 배치가 굳이 클릭을 시도하지 않게, 안전한 쪽을 기본값으로 둔다.
        """
        from landing_accessibility.engine.evidence import EvidenceRun

        from .executor import run_l1_if_safe

        run_id = f"e001-l1-{target.target_id}-{_utc_now_iso().replace(':', '').replace('.', '')}"
        run = EvidenceRun.create(
            self.out_dir / "evidence",
            run_id,
            execution_mode=ExecutionMode.FIXTURE,
            provenance=ShadowProvenance(
                base_sha=E001_RUNNER_BASE_SHA, shadow_lane=E001_RUNNER_SHADOW_LANE
            ),
        )
        result = run_l1_if_safe(target, fixture_root=self.fixture_root, run=run)
        run.seal()
        return result

    # ── batch 봉인 ───────────────────────────────────────────────────────
    def _seal_batch(
        self,
        batch_index: int,
        targets: list[TargetSpec],
        results: list[TargetResult],
        execution_mode: str,
    ) -> BatchManifest:
        isolated = sum(1 for r in results if is_failure_isolated(TargetOutcome(r.outcome)))
        manifest = BatchManifest(
            batch_index=batch_index,
            batch_id=f"b{batch_index:04d}",
            execution_mode=execution_mode,
            target_ids=[t.target_id for t in targets],
            results=[r.as_dict() for r in results],
            provenance={
                **ShadowProvenance(
                    base_sha=E001_RUNNER_BASE_SHA, shadow_lane=E001_RUNNER_SHADOW_LANE
                ).as_dict(),
                "isolated_failure_count": isolated,
                "target_count": len(targets),
                "max_retries_per_target": MAX_RETRIES_PER_TARGET,
            },
            committed_at=_utc_now_iso(),
            previous_batch_hash=self.ledger.last_batch_hash(),
        )
        return self.ledger.append(manifest)

    def _run_dry(self, plan: list[TargetSpec]) -> BatchManifest:
        """SHADOW_DRY_RUN — **executor를 한 번도 호출하지 않는다.** 계획 구조만 검증한다."""
        results = [
            TargetResult(
                target_id=t.target_id,
                outcome=TargetOutcome.PLANNED_NOT_EXECUTED.value,
                attempts=0,
            )
            for t in plan
        ]
        return self._seal_batch(1, plan, results, "SHADOW_DRY_RUN")


__all__ = ["BatchRunner", "TargetExecutor", "TargetResult"]
