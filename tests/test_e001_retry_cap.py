"""E001 배치 러너 — 자동 복구 정책이 정확히 1회만 재시도하는가.

두 가지를 증명한다.

1. **행동** — 고의로 반복 실패하는 fixture(파이썬 클로저)로 재시도 횟수가
   정확히 1(= 1회 재시도, 총 2회 시도)로 상한선인지.
2. **불가능성** — "결과를 보고 retry 횟수를 늘리는" optional stopping 경로가
   물리적으로 없는지: `run_with_retry`의 시그니처에 재시도 횟수를 넓힐 수 있는
   파라미터가 없고, 몇 번을 실패시켜도(3회·10회·무한) 시도 횟수는 항상 2에서
   멈춘다.
"""

from __future__ import annotations

import inspect
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
RESEARCH = REPO / "research" / "landing_accessibility"
sys.path.insert(0, str(RESEARCH / "src"))

from landing_accessibility.e001_runner.batch import BatchRunner  # noqa: E402
from landing_accessibility.e001_runner.outcomes import TargetOutcome  # noqa: E402
from landing_accessibility.e001_runner.plan import TargetSpec  # noqa: E402
from landing_accessibility.e001_runner.retry import (  # noqa: E402
    MAX_RETRIES_PER_TARGET,
    run_with_retry,
)


def test_max_retries_constant_is_exactly_one():
    assert MAX_RETRIES_PER_TARGET == 1


def test_run_with_retry_has_no_parameter_to_widen_retry_count():
    """optional stopping 방지 — 함수 시그니처 자체에 그 자리가 없다."""
    sig = inspect.signature(run_with_retry)
    assert list(sig.parameters) == ["fn"], (
        "run_with_retry 에 fn 외의 파라미터가 생겼다 — 재시도 횟수를 호출부가 "
        "조정할 수 있는 자리가 생기면 optional stopping 이 열린다"
    )


@pytest.mark.parametrize("always_fail_count", [2, 3, 10, 1000])
def test_always_failing_target_is_called_exactly_twice(always_fail_count):
    """몇 번을 실패시키도록 준비했든(2·3·10·1000) 실제 호출은 항상 2회에서 멈춘다."""
    calls = {"n": 0}

    def always_fails():
        calls["n"] += 1
        if calls["n"] <= always_fail_count:
            raise RuntimeError("net::ERR_CONNECTION_RESET simulated transport failure")
        return {"never": "reached"}  # always_fail_count >= 2 이므로 여기 도달하지 않는다

    outcome = run_with_retry(always_fails)

    assert calls["n"] == 1 + MAX_RETRIES_PER_TARGET == 2
    assert not outcome.succeeded
    assert outcome.attempts == 2
    assert outcome.final_outcome == TargetOutcome.SKIPPED_RETRY_EXHAUSTED
    assert outcome.same_cause_on_retry is True  # 같은 예외 문구 → 같은 원인으로 재발


def test_succeeds_on_the_retry_attempt():
    calls = {"n": 0}

    def fails_once_then_succeeds():
        calls["n"] += 1
        if calls["n"] == 1:
            raise TimeoutError("simulated timeout")
        return {"measurement_status": "MEASURED"}

    outcome = run_with_retry(fails_once_then_succeeds)
    assert calls["n"] == 2
    assert outcome.succeeded
    assert outcome.attempts == 2


def test_succeeds_on_first_attempt_no_retry_needed():
    calls = {"n": 0}

    def always_succeeds():
        calls["n"] += 1
        return {"measurement_status": "MEASURED"}

    outcome = run_with_retry(always_succeeds)
    assert calls["n"] == 1
    assert outcome.attempts == 1


def test_batch_runner_end_to_end_retry_cap(tmp_path):
    """`BatchRunner` 전체 경로에서도 재시도가 정확히 1회로 멈추는지 확인한다."""
    calls: list[str] = []

    def flaky_executor(target: TargetSpec) -> dict:
        calls.append(target.target_id)
        raise RuntimeError("simulated WAF 403 forbidden block")

    target = TargetSpec(
        target_id="wt-flaky",
        canonical_service_key="flaky",
        official_url="https://example.com/never-opened",
        interaction_archetype="CONTENT_OPEN",
        fixture_override="simple_article.html",
    )
    runner = BatchRunner(out_dir=tmp_path / "out", fixture_root=RESEARCH / "fixtures")
    manifests = runner.run([target], execution_mode="FIXTURE", target_executor=flaky_executor)

    assert len(calls) == 2, f"executor 가 {len(calls)}번 호출됐다 — 재시도 상한이 깨졌다"
    result = manifests[0].results[0]
    assert result["outcome"] == TargetOutcome.SKIPPED_RETRY_EXHAUSTED.value
    assert result["attempts"] == 2
