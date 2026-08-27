"""E001 배치 러너 — target 하나 전체(재시도 포함)에 대한 wall-clock 상한.

`wall_clock.run_with_wall_clock_cap`이 `retry.run_with_retry(attempt)` 호출
전체를 감싼다는 것과, 상한을 넘기면 그 target이 `TargetOutcome.TRANSPORT_FAILURE`
로 기록되고(**`UNDETERMINED`로 세탁되지 않는다** — Claude A 지시, 2026-08-27)
배치는 멈추지 않고 다음 target으로 넘어간다는 것을 증명한다.

"고의로 느린 fixture"는 여기서 **fake `target_executor`가 `time.sleep(...)`을
직접 주입하는 방식**으로 구현한다 — FIXTURE 모드는 `file://` 로컬 파일이라
네트워크 지연을 재현할 수 없고, 실제 브라우저 hang(예: 무한루프 스크립트)을
결정적으로 몇 초 안에 재현하는 것도 이 테스트 스위트의 실행 시간 예산에 맞지
않는다. `tests/test_e001_failure_isolation.py`가 이미 같은 방식(fake executor로
transport 실패를 시뮬레이션)을 orchestration 레이어 테스트에 쓰고 있다 — 이
파일은 그 패턴을 그대로 따른다. wall-clock cap 래퍼 자체(`wall_clock.py`)는
스레드/실제 시간을 그대로 쓰므로, executor가 무엇을 하든(fake든 real engine
호출이든) 동일하게 작동한다.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
RESEARCH = REPO / "research" / "landing_accessibility"
sys.path.insert(0, str(RESEARCH / "src"))

from landing_accessibility.e001_runner.batch import BatchRunner  # noqa: E402
from landing_accessibility.e001_runner.outcomes import TargetOutcome  # noqa: E402
from landing_accessibility.e001_runner.plan import TargetSpec  # noqa: E402
from landing_accessibility.e001_runner.wall_clock import (  # noqa: E402
    DEFAULT_TARGET_WALL_CLOCK_CAP_S,
    TargetWallClockExceededError,
    run_with_wall_clock_cap,
)

FIXTURES = RESEARCH / "fixtures"


def _target(tid: str) -> TargetSpec:
    return TargetSpec(
        target_id=tid,
        canonical_service_key=tid,
        official_url=f"https://example.com/{tid}/never-opened",
        interaction_archetype="CONTENT_OPEN",
        fixture_override="simple_article.html",
    )


def test_default_cap_is_exactly_six_minutes():
    """Claude A 확정값(2026-08-27) — 5~8분 범위 논의를 무시하고 정확히 360초로 고정."""
    assert DEFAULT_TARGET_WALL_CLOCK_CAP_S == 360.0


# ── wall_clock.py 단위 테스트 — 스레드/시간 메커니즘 자체 ────────────────────────
def test_run_with_wall_clock_cap_returns_value_when_fast_enough():
    assert run_with_wall_clock_cap(lambda: 42, cap_s=5.0) == 42


def test_run_with_wall_clock_cap_raises_when_too_slow():
    def slow():
        time.sleep(2.0)
        return "never seen"

    import pytest

    with pytest.raises(TargetWallClockExceededError):
        run_with_wall_clock_cap(slow, cap_s=0.2)


def test_run_with_wall_clock_cap_preserves_exception_identity():
    """`fn()`이 던진 예외 타입이 스레드 경계를 넘으며 뭉개지지 않는다 — 상위 계층
    (`batch.py`)이 `AccountActionBlockedError` 등을 `isinstance`로 구분해야 한다.
    """

    class _Marker(RuntimeError):
        pass

    def boom():
        raise _Marker("distinct type must survive")

    import pytest

    with pytest.raises(_Marker):
        run_with_wall_clock_cap(boom, cap_s=5.0)


# ── BatchRunner 통합 — cap 초과가 TRANSPORT_FAILURE 로 정확히 기록되는가 ─────────
def test_batch_runner_records_wall_clock_cap_exceeded_as_transport_failure(tmp_path):
    """cap을 아주 짧게(0.2s) 준다. fake executor가 그보다 오래 걸리는(2s) 작업을
    시도하면, 재시도 정책과 무관하게 target 전체가 TRANSPORT_FAILURE로 끝나야
    한다 — `UNDETERMINED`(콘텐츠 판정 축)로 흡수되면 안 된다.
    """

    def slow_executor(target: TargetSpec) -> dict:
        time.sleep(2.0)
        return {"measurement_status": "MEASURED"}  # 실제로는 절대 도달하지 않는다

    runner = BatchRunner(
        out_dir=tmp_path / "out",
        fixture_root=FIXTURES,
        batch_size=5,
        target_wall_clock_cap_s=0.2,
    )
    manifests = runner.run(
        [_target("t-slow")], execution_mode="FIXTURE", target_executor=slow_executor
    )

    result = manifests[0].results[0]
    assert result["outcome"] == TargetOutcome.TRANSPORT_FAILURE.value
    assert result["outcome"] != "UNDETERMINED"
    assert "TIMEOUT_EXCEEDED" in (result["error"] or "")


def test_batch_does_not_stop_when_one_target_exceeds_wall_clock_cap(tmp_path):
    """cap을 넘긴 target이 있어도 배치는 끝까지 순회하고 봉인된다 — 실패 격리와
    같은 계약이 wall-clock cap 초과에도 그대로 적용된다는 것을 증명한다.
    """

    def maybe_slow_executor(target: TargetSpec) -> dict:
        if target.target_id == "t-slow":
            time.sleep(2.0)
        return {"measurement_status": "MEASURED", "web_target_id": target.target_id}

    targets = [_target("t-ok-1"), _target("t-slow"), _target("t-ok-2")]
    runner = BatchRunner(
        out_dir=tmp_path / "out",
        fixture_root=FIXTURES,
        batch_size=10,
        target_wall_clock_cap_s=0.2,
    )
    manifests = runner.run(targets, execution_mode="FIXTURE", target_executor=maybe_slow_executor)

    assert len(manifests) == 1
    results = {r["target_id"]: r for r in manifests[0].results}
    assert set(results) == {"t-ok-1", "t-slow", "t-ok-2"}
    assert results["t-ok-1"]["outcome"] == TargetOutcome.MEASURED.value
    assert results["t-ok-2"]["outcome"] == TargetOutcome.MEASURED.value
    assert results["t-slow"]["outcome"] == TargetOutcome.TRANSPORT_FAILURE.value
    # 순서 보존 — 느린 target 하나가 뒤 target을 건너뛰게 하지 않는다.
    assert [r["target_id"] for r in manifests[0].results] == ["t-ok-1", "t-slow", "t-ok-2"]

    ledger_check = runner.ledger.verify_chain()
    assert ledger_check["status"] == "OK"


def test_wall_clock_cap_does_not_multiply_by_retry_count(tmp_path):
    """ "재시도 1회 x cap" 이 아니라 "target 전체에 쓸 수 있는 시간"이 상한이다.

    cap=0.5s인데 executor가 매번 0.3s씩 걸리면, 1회 시도(0.3s)는 cap 안에
    들어오지만 재시도까지 하면(0.3s+0.3s=0.6s) cap을 넘는다 — 이 테스트는
    cap이 "시도 1회당"이 아니라 "전체 시도(재시도 포함)"에 적용된다는 것을
    확인한다: 항상 실패하는 executor가 0.3s씩 걸릴 때, cap=0.5s면 2번째
    시도 도중에 cap이 발화해 TRANSPORT_FAILURE로 끝나야 한다(정상적인
    SKIPPED_RETRY_EXHAUSTED로 끝나면 안 된다 — 그건 재시도가 끝까지 갔다는
    뜻인데, 전체 소요시간이 이미 cap을 넘었어야 한다).
    """

    def always_fails_slowly(target: TargetSpec) -> dict:
        time.sleep(0.3)
        raise RuntimeError("net::ERR_CONNECTION_RESET simulated")

    runner = BatchRunner(
        out_dir=tmp_path / "out",
        fixture_root=FIXTURES,
        batch_size=5,
        target_wall_clock_cap_s=0.5,
    )
    manifests = runner.run(
        [_target("t-flaky-slow")], execution_mode="FIXTURE", target_executor=always_fails_slowly
    )

    result = manifests[0].results[0]
    assert result["outcome"] == TargetOutcome.TRANSPORT_FAILURE.value
    assert "TIMEOUT_EXCEEDED" in (result["error"] or "")
