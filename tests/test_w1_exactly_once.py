"""E001 배치 러너 — exactly-once (`T-A-W1-001` §3, D-R0-38 · D-R0-46 · D-R0-46b).

**REAL_TARGET blocking acceptance criterion — 이월 불가.** `self_approved=false`다:
이 테스트가 여기서 통과한다고 해서 W1이 통과 판정을 내리는 게 아니다 — Claude C가
같은 SHA에서 독립적으로 재현·검증해야 한다.

## 근거 — 가설이 아니라 실측

2026-08-27 05:14, worker_02 에서 프로세스 2개가 `batch_0001`의 target 4건을
**동시에** 실사이트로 두 번 발사했다(`C_CLEAN0_AUDIT §6.1`). 원인은 batch 원장의
check-then-act — "존재를 먼저 확인하고 나중에 만든다" — 였다. 그 확인과 생성
사이의 창에서 두 번째 프로세스가 "아직 없다"를 본다.

## 왜 순차 2회 호출만으로는 부족한가

check-then-act 는 **순차** 테스트를 통과하면서 **동시** 테스트에서 무너진다 —
그게 정확히 이번에 일어난 일이다. 그래서 이 파일은 순차 테스트(판별력 낮음)에
그치지 않고 스레드 동시 진입 + **진짜 별도 OS 프로세스 2개** 동시 진입까지
검증한다. 브라우저 기동 지점(`real_executor.run_l1_if_safe_real`)은 spy로
대체한다 — 실사이트에는 붙지 않는다.
"""

from __future__ import annotations

import json
import multiprocessing
import os
import sys
import threading
import time
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
RESEARCH = REPO / "research" / "landing_accessibility"
SRC = str(RESEARCH / "src")
sys.path.insert(0, SRC)

from landing_accessibility.e001_runner.batch import (  # noqa: E402
    DUPLICATE_SUPPRESSED_OUTCOME,
    BatchRunner,
    ExactlyOnceConfigError,
    IdempotencyKey,
    LockState,
    TargetLock,
)
from landing_accessibility.e001_runner.plan import TargetSpec  # noqa: E402
from landing_accessibility.engine.firewall import ExecutionScope  # noqa: E402


def _key(**overrides: str) -> IdempotencyKey:
    base = {
        "ticket_id": "T-TEST",
        "run_id": "ROUND-1",
        "target_id": "wt-lock",
        "collector_sha": "csha",
        "protocol_sha": "psha",
    }
    base.update(overrides)
    return IdempotencyKey(**base)


# ══════════════════════════════════════════════════════════════════════════
# 1. `TargetLock` 순수 단위 테스트 — atomic acquire, state, retry 조건
# ══════════════════════════════════════════════════════════════════════════
def test_acquire_is_atomic_second_sequential_request_is_suppressed(tmp_path):
    """같은 key 로 2회 요청 → 1회만 `proceed=True`, 2회차는 `DUPLICATE_SUPPRESSED`."""
    lock = TargetLock(tmp_path)
    key = _key()

    first = lock.acquire(key)
    second = lock.acquire(key)

    assert first.proceed is True
    assert first.attempt_id is not None
    assert second.proceed is False
    assert second.attempt_id is None
    assert "DUPLICATE_SUPPRESSED" in (second.reason or "")


def test_lock_file_is_never_deleted_and_records_state(tmp_path):
    lock = TargetLock(tmp_path)
    key = _key(target_id="wt-persist")

    decision = lock.acquire(key)
    assert decision.lock_path.is_file()

    lock.mark_done(key)
    assert decision.lock_path.is_file(), "lock 을 삭제하면 두 번째 프로세스가 lock 부재를 본다(D-R0-46)"
    payload = json.loads(decision.lock_path.read_text(encoding="utf-8"))
    assert payload["state"] == LockState.DONE
    assert payload["attempts"] == 1
    assert payload["idempotency_key"] == key.canonical()


def test_failed_retryable_allows_retry_under_max_attempts(tmp_path):
    lock = TargetLock(tmp_path)
    key = _key(target_id="wt-retry-ok")

    lock.acquire(key, max_attempts=3)
    lock.mark_failed_retryable(key)

    retry = lock.acquire(key, max_attempts=3)
    assert retry.proceed is True
    assert retry.prior_state == LockState.FAILED_RETRYABLE
    assert retry.prior_attempts == 2


def test_failed_retryable_blocks_retry_at_max_attempts(tmp_path):
    lock = TargetLock(tmp_path)
    key = _key(target_id="wt-retry-exhausted")

    lock.acquire(key, max_attempts=2)  # attempts=1 (RUNNING)
    lock.mark_failed_retryable(key)  # attempts=1 (FAILED_RETRYABLE)
    second = lock.acquire(key, max_attempts=2)  # 1 < 2 → 허용, attempts=2 (RUNNING)
    assert second.proceed is True
    lock.mark_failed_retryable(key)  # attempts=2 (FAILED_RETRYABLE)
    third = lock.acquire(key, max_attempts=2)  # 2 < 2 는 거짓 → 억제
    assert third.proceed is False, "재실행 상한(max_attempts)에 도달했는데 통과시켰다"


def test_different_run_id_is_a_different_key_not_suppressed(tmp_path):
    """`run_id`(수집 회차)가 다르면 다른 key 다 — 여기서 억제되면 안 된다.
    (`run_id` 어휘 오용 회귀 방지 — 이게 옛 버그의 정확한 형태였다: target 1회
    시도 식별자를 `run_id`라고 부르면 매번 값이 달라져 억제가 영원히 발화하지
    않는다. 지금은 반대 방향 회귀 — 진짜 다른 회차를 같은 key 로 오판하는 것 —
    도 없다는 것을 함께 확인한다.)"""
    lock = TargetLock(tmp_path)
    d1 = lock.acquire(_key(target_id="wt-round", run_id="ROUND-1"))
    d2 = lock.acquire(_key(target_id="wt-round", run_id="ROUND-2"))
    assert d1.proceed is True
    assert d2.proceed is True


# ══════════════════════════════════════════════════════════════════════════
# 2. 동시성 — 스레드
# ══════════════════════════════════════════════════════════════════════════
def test_concurrent_threads_only_one_acquire_proceeds(tmp_path):
    """완전히 동시에 여러 스레드가 같은 key 로 들어와도 정확히 1개만 통과한다.
    `os.open`은 GIL 이 풀리는 블로킹 syscall이라 진짜 경쟁이 일어난다."""
    lock = TargetLock(tmp_path)
    key = _key(target_id="wt-threads")
    n = 12
    barrier = threading.Barrier(n)
    results: list[bool] = []
    results_lock = threading.Lock()

    def worker() -> None:
        barrier.wait()
        decision = lock.acquire(key)
        with results_lock:
            results.append(decision.proceed)

    threads = [threading.Thread(target=worker) for _ in range(n)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert sum(results) == 1, f"동시 진입 {n}개 중 {sum(results)}개가 통과했다: {results}"


# ══════════════════════════════════════════════════════════════════════════
# 3. 동시성 — 진짜 프로세스 2개 (2026-08-27 05:14 사고 재현)
# ══════════════════════════════════════════════════════════════════════════
def _lock_only_process_worker(
    lock_dir: str, barrier_path: str, marker_dir: str, idx: int
) -> None:
    sys.path.insert(0, SRC)
    from landing_accessibility.e001_runner.batch import IdempotencyKey, TargetLock

    lock = TargetLock(lock_dir)
    key = IdempotencyKey("T-TEST", "ROUND-1", "wt-procs", "csha", "psha")
    while not os.path.exists(barrier_path):
        time.sleep(0.001)
    decision = lock.acquire(key)
    if decision.proceed:
        Path(marker_dir, f"launched_{idx}_{os.getpid()}.marker").write_text("1")


def test_concurrent_os_processes_only_one_launches(tmp_path):
    """`TargetLock` 만 떼어 **진짜 별도 OS 프로세스 2개**가 동시에 같은 key 로
    들어와도 launch(=lock 획득) 총합이 1이어야 한다."""
    lock_dir = tmp_path / "locks"
    marker_dir = tmp_path / "markers"
    lock_dir.mkdir()
    marker_dir.mkdir()
    barrier_path = tmp_path / "GO"

    procs = [
        multiprocessing.Process(
            target=_lock_only_process_worker,
            args=(str(lock_dir), str(barrier_path), str(marker_dir), i),
        )
        for i in range(2)
    ]
    for p in procs:
        p.start()
    barrier_path.write_text("go")
    for p in procs:
        p.join(timeout=30)

    markers = list(marker_dir.iterdir())
    assert len(markers) == 1, f"프로세스 2개 동시 기동인데 launch 가 {len(markers)}회: {markers}"


# ══════════════════════════════════════════════════════════════════════════
# 4. `BatchRunner._real_executor` 통합 — 브라우저 launch 지점을 spy로 계측
# ══════════════════════════════════════════════════════════════════════════
def _target() -> TargetSpec:
    return TargetSpec(
        target_id="wt-exactly-once",
        canonical_service_key="eo_test",
        official_url="https://example.com/never-opened",
        interaction_archetype="QUERY",
    )


def _fake_run_l1_if_safe_real(target, *, run, scope, task=None, budget=None):
    """`run_l1_if_safe_real`(playwright 기동 → `Scout`/`L0Collector` → 실사이트
    접속으로 이어지는 진입점, `real_executor.py`)을 통째로 대체하는 spy다.
    **실사이트에 붙지 않는다** — 여기서 하는 일은 launch 호출 카운트를 늘리고
    `EvidenceRun.seal()`이 요구하는 최소 산출물 1건을 남기는 것뿐이다.
    """
    run.open_observation("fake-obs")
    run.write_artifact("fake-obs", "fake/marker.txt", b"1")
    return {
        "outcome": "MEASURED",
        "scout_invoked": True,
        "measurement_status": "MEASURED",
        "l0": {},
    }


def test_real_executor_second_sequential_call_launches_zero_times(tmp_path, monkeypatch):
    """`D-R0-38` 수용기준 핵심 — 브라우저 기동 지점을 spy로 감싸 호출 횟수를 센다.
    **1회차: launch 카운트 1. 2회차(같은 key): launch 카운트 0**, 그리고
    `DUPLICATE_SUPPRESSED` 이벤트가 event_log 에 남는다. 두 요청 사이에 lock 을
    지우지 않는다(`BatchRunner`가 lock 을 지우는 코드 경로 자체가 없다).
    """
    from landing_accessibility.e001_runner import real_executor as real_executor_module

    launch_calls: list[str] = []

    def spy(target, *, run, scope, task=None, budget=None):
        launch_calls.append(target.target_id)
        return _fake_run_l1_if_safe_real(target, run=run, scope=scope, task=task, budget=budget)

    monkeypatch.setattr(real_executor_module, "run_l1_if_safe_real", spy)

    lock_dir = tmp_path / "locks"
    event_log = lock_dir.parent / "event_log.jsonl"
    runner = BatchRunner(
        out_dir=tmp_path / "out",
        fixture_root=RESEARCH / "fixtures",
        ticket_id="T-TEST",
        run_id="ROUND-1",
        lock_dir=lock_dir,
    )
    runner._real_scope = ExecutionScope.E000_FAST
    target = _target()

    first = runner._real_executor(target)
    assert len(launch_calls) == 1, f"1회차 launch 카운트가 1이 아니다: {launch_calls}"
    assert first["outcome"] != DUPLICATE_SUPPRESSED_OUTCOME
    assert first["attempt_id"], "attempt_id 가 산출물에 기록되지 않았다(D-R0-46b)"

    second = runner._real_executor(target)
    assert len(launch_calls) == 1, (
        f"2회차 이후에도 launch 카운트는 1이어야 하는데 {len(launch_calls)} "
        f"— 2회차에서 브라우저가 다시 기동됐다: {launch_calls}"
    )
    assert second["outcome"] == DUPLICATE_SUPPRESSED_OUTCOME
    assert second.get("prior_lock_state") == LockState.DONE

    assert event_log.is_file(), "DUPLICATE_SUPPRESSED 이벤트가 event_log 에 기록되지 않았다"
    events = [json.loads(line) for line in event_log.read_text(encoding="utf-8").splitlines()]
    duplicate_events = [e for e in events if e.get("event") == DUPLICATE_SUPPRESSED_OUTCOME]
    assert len(duplicate_events) == 1
    assert duplicate_events[0]["target_id"] == target.target_id
    assert duplicate_events[0]["idempotency_key"] == first["idempotency_key"]


def test_real_executor_missing_ticket_or_run_id_fails_closed_before_any_launch(tmp_path):
    """`ticket_id`/`run_id`(수집 회차) 없이 REAL_TARGET 배치를 시작하면 브라우저를
    한 번도 켜지 않고 즉시 실패한다 — idempotency key 성분이 없는 채로 진행하지
    않는다."""
    runner = BatchRunner(out_dir=tmp_path / "out", fixture_root=RESEARCH / "fixtures")
    with pytest.raises(ExactlyOnceConfigError):
        runner.run(
            [_target()],
            execution_mode="REAL_TARGET",
            execution_scope=ExecutionScope.E000_FAST,
        )


def _real_executor_process_worker(
    lock_dir: str, out_root: str, barrier_path: str, marker_dir: str, idx: int
) -> None:
    sys.path.insert(0, SRC)
    from landing_accessibility.e001_runner import real_executor as real_executor_module
    from landing_accessibility.e001_runner.batch import BatchRunner
    from landing_accessibility.e001_runner.plan import TargetSpec
    from landing_accessibility.engine.firewall import ExecutionScope

    def fake(target, *, run, scope, task=None, budget=None):
        run.open_observation("fake-obs")
        run.write_artifact("fake-obs", "fake/marker.txt", b"1")
        Path(marker_dir, f"launched_{idx}_{os.getpid()}.marker").write_text("1")
        return {
            "outcome": "MEASURED",
            "scout_invoked": True,
            "measurement_status": "MEASURED",
            "l0": {},
        }

    real_executor_module.run_l1_if_safe_real = fake

    runner = BatchRunner(
        out_dir=Path(out_root) / f"worker_{idx}",
        fixture_root=RESEARCH / "fixtures",
        ticket_id="T-TEST",
        run_id="ROUND-1",
        lock_dir=lock_dir,
    )
    runner._real_scope = ExecutionScope.E000_FAST
    target = TargetSpec(
        target_id="wt-exactly-once-mp",
        canonical_service_key="eo_test_mp",
        official_url="https://example.com/never-opened",
        interaction_archetype="QUERY",
    )
    while not os.path.exists(barrier_path):
        time.sleep(0.001)
    runner._real_executor(target)


def _fixture_path_process_worker(
    lock_dir: str, out_root: str, barrier_path: str, results_dir: str, idx: int
) -> None:
    """`C-FINDING-214553` — FIXTURE 경로에도 REAL_TARGET과 **같은** lock이
    배선됐다는 것을 네트워크 없이 증명하는 worker. 실제 `_run_l0_and_l1`(=
    `_default_fixture_executor`/`l1_executor`가 수렴하는 그 메서드, mock 없음)을
    그대로 부른다 — playwright는 로컬 fixture 파일만 연다(네트워크 접속 없음).
    """
    sys.path.insert(0, SRC)
    from landing_accessibility.e001_runner.batch import BatchRunner
    from landing_accessibility.e001_runner.plan import TargetSpec

    lock = None
    try:
        runner = BatchRunner(
            out_dir=Path(out_root),
            fixture_root=RESEARCH / "fixtures",
            lock_dir=lock_dir,
        )
        target = TargetSpec(
            target_id="wt-fixture-exactly-once",
            canonical_service_key="fixture_eo_test",
            official_url="https://example.com/never-opened",
            interaction_archetype="QUERY",
            fixture_override="search_dispatch.html",
            # endpoint_definition을 실어 줘야 Scout가 검색 제출 1회 만에 끝난다
            # (없으면 예산을 다 쓸 때까지 재시도해 이 테스트가 느려진다).
            task_id="task_wt_fixture_exactly_once",
            endpoint_definition="QUERY_SUBMITTED",
            endpoint_signal_type="URL_PATTERN",
        )
        while not os.path.exists(barrier_path):
            time.sleep(0.001)
        result = runner._run_l0_and_l1(target)
        Path(results_dir, f"result_{idx}.json").write_text(
            json.dumps({"outcome": result.get("outcome"), "idx": idx}), encoding="utf-8"
        )
    except BaseException as exc:  # pragma: no cover - 진단용, 테스트가 직접 판독
        Path(results_dir, f"error_{idx}.txt").write_text(f"{type(exc).__name__}: {exc}")
        raise


def test_concurrent_os_processes_fixture_path_launch_total_is_one(tmp_path):
    """`C-FINDING-214553`(C의 독립 감사) — lock이 REAL_TARGET 경로에만 배선돼
    있으면 REAL_TARGET은 접속 금지라 e2e로 못 돌리고 FIXTURE는 lock을 안 타서
    증명이 안 됐다. 이제 FIXTURE 경로(`_run_l0_and_l1`)도 REAL과 같은
    `_acquire_launch_lock`을 타므로, **네트워크 전혀 없이** "같은 worker 파티션
    프로세스 2개 동시 기동 → evidence run 디렉터리 1개 / `DUPLICATE_SUPPRESSED`
    1건"을 end-to-end로 증명할 수 있다.
    """
    pytest.importorskip("playwright.sync_api")

    lock_dir = tmp_path / "locks"
    out_root = tmp_path / "out"
    results_dir = tmp_path / "results"
    lock_dir.mkdir()
    out_root.mkdir()
    results_dir.mkdir()
    barrier_path = tmp_path / "GO"

    procs = [
        multiprocessing.Process(
            target=_fixture_path_process_worker,
            args=(str(lock_dir), str(out_root), str(barrier_path), str(results_dir), i),
        )
        for i in range(2)
    ]
    for p in procs:
        p.start()
    barrier_path.write_text("go")
    for p in procs:
        p.join(timeout=60)

    errors = list(results_dir.glob("error_*.txt"))
    assert not errors, f"worker 프로세스가 죽었다: {[e.read_text() for e in errors]}"

    outcomes = [
        json.loads(p.read_text())["outcome"] for p in sorted(results_dir.glob("result_*.json"))
    ]
    assert len(outcomes) == 2, f"프로세스 2개 중 일부가 결과를 남기지 못했다: {outcomes}"
    suppressed_count = sum(1 for o in outcomes if o == DUPLICATE_SUPPRESSED_OUTCOME)
    launched_count = sum(1 for o in outcomes if o != DUPLICATE_SUPPRESSED_OUTCOME)
    assert launched_count == 1 and suppressed_count == 1, (
        f"FIXTURE 경로 동시 기동인데 launch/suppress 분포가 1/1 이 아니다: {outcomes}"
    )

    # evidence run 디렉터리도 실제로 1개만 생겼다 — "코드는 맞는데 산출물은 2개"
    # 같은 residual 이 없는지까지 확인한다.
    evidence_root = out_root / "evidence"
    if evidence_root.is_dir():
        run_dirs = [d for d in evidence_root.iterdir() if d.is_dir()]
        assert len(run_dirs) == 1, f"evidence run 디렉터리가 1개가 아니다: {run_dirs}"


def test_concurrent_os_processes_real_executor_launch_total_is_one(tmp_path):
    """`_real_executor` 전체(lock 획득 → `EvidenceRun.create` → launch)를 프로세스
    2개가 동시에 두드려도 **launch 총합이 1**이어야 한다 — 이게 2026-08-27 05:14
    사고를 가장 가깝게 재현하는 테스트다: 같은 worker 파티션(같은 lock_dir/
    ticket_id/run_id)에서 별도 프로세스 2개가 `batch.py`의 실제 진입점을 동시에
    부른다.
    """
    lock_dir = tmp_path / "locks"
    marker_dir = tmp_path / "markers"
    out_root = tmp_path / "out"
    lock_dir.mkdir()
    marker_dir.mkdir()
    barrier_path = tmp_path / "GO"

    procs = [
        multiprocessing.Process(
            target=_real_executor_process_worker,
            args=(str(lock_dir), str(out_root), str(barrier_path), str(marker_dir), i),
        )
        for i in range(2)
    ]
    for p in procs:
        p.start()
    barrier_path.write_text("go")
    for p in procs:
        p.join(timeout=60)

    markers = list(marker_dir.iterdir())
    assert len(markers) == 1, (
        f"실제 사건(worker_02, 2026-08-27 05:14)과 같은 조건인데 launch 가 "
        f"{len(markers)}회 발생했다: {markers}"
    )
