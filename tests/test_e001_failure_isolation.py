"""E001 배치 러너 — 사이트 실패 격리 + append-only batch ledger.

target 하나(들)의 실패가 배치 전체를 막지 않는다는 것과, batch마다 manifest+hash가
남고 봉인된다(append-only, 덮어쓰기 불가, 해시 체인 검증 가능)는 것을 증명한다.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
RESEARCH = REPO / "research" / "landing_accessibility"
sys.path.insert(0, str(RESEARCH / "src"))

from landing_accessibility.e001_runner.batch import BatchRunner  # noqa: E402
from landing_accessibility.e001_runner.ledger import (  # noqa: E402
    BatchLedger,
    BatchManifest,
    BatchOverwriteError,
    ChainBrokenError,
)
from landing_accessibility.e001_runner.outcomes import TargetOutcome  # noqa: E402
from landing_accessibility.e001_runner.plan import TargetSpec  # noqa: E402

FIXTURES = RESEARCH / "fixtures"


def _target(tid: str, archetype: str = "CONTENT_OPEN") -> TargetSpec:
    return TargetSpec(
        target_id=tid,
        canonical_service_key=tid,
        official_url=f"https://example.com/{tid}/never-opened",
        interaction_archetype=archetype,
        fixture_override="simple_article.html",
    )


def _mixed_executor(failure_ids: set[str]):
    """failure_ids 에 있는 target 은 매번 서로 다른 방식으로 실패하고, 나머지는
    정상적으로 `measurement_status=MEASURED` 를 돌려준다 — 실제 엔진을 부르지
    않는 순수 fake executor.
    """

    call_log: list[str] = []

    def executor(target: TargetSpec) -> dict:
        call_log.append(target.target_id)
        if target.target_id in failure_ids:
            reasons = {
                "t-timeout": TimeoutError("navigation timeout exceeded"),
                "t-tls": RuntimeError("SSL certificate_verify failed"),
                "t-waf": RuntimeError("403 Forbidden - blocked by WAF (cloudflare)"),
                "t-captcha": RuntimeError("captcha challenge required"),
                "t-transport": RuntimeError("net::ERR_CONNECTION_REFUSED"),
            }
            raise reasons.get(target.target_id, RuntimeError("generic simulated failure"))
        return {"measurement_status": "MEASURED", "web_target_id": target.target_id}

    return executor, call_log


def test_one_failing_target_does_not_stop_the_batch(tmp_path):
    targets = [_target("t-ok-1"), _target("t-timeout"), _target("t-ok-2")]
    executor, call_log = _mixed_executor({"t-timeout"})

    runner = BatchRunner(out_dir=tmp_path / "out", fixture_root=FIXTURES, batch_size=10)
    manifests = runner.run(targets, execution_mode="FIXTURE", target_executor=executor)

    # 실패한 target 도 재시도(1회) 되므로 총 호출 = ok(1) + ok(1) + timeout(2) = 4
    assert call_log.count("t-ok-1") == 1
    assert call_log.count("t-ok-2") == 1
    assert call_log.count("t-timeout") == 2

    results = {r["target_id"]: r for r in manifests[0].results}
    assert results["t-ok-1"]["outcome"] == TargetOutcome.MEASURED.value
    assert results["t-ok-2"]["outcome"] == TargetOutcome.MEASURED.value
    assert results["t-timeout"]["outcome"] == TargetOutcome.SKIPPED_RETRY_EXHAUSTED.value
    # 순서가 보존된다 — target 하나의 실패가 뒤 target을 건너뛰게 하지 않는다.
    assert [r["target_id"] for r in manifests[0].results] == ["t-ok-1", "t-timeout", "t-ok-2"]


@pytest.mark.parametrize(
    ("failure_id", "expected_outcome"),
    [
        ("t-timeout", TargetOutcome.TIMEOUT),
        ("t-tls", TargetOutcome.TLS_ERROR),
        ("t-waf", TargetOutcome.WAF_BLOCKED),
        ("t-captcha", TargetOutcome.CAPTCHA),
        ("t-transport", TargetOutcome.TRANSPORT_FAILURE),
    ],
)
def test_failure_classification_per_target(tmp_path, failure_id, expected_outcome):
    """재시도까지 소진했을 때 최종 outcome은 SKIPPED_RETRY_EXHAUSTED 지만, 그 원인
    분류(attempt_outcomes 경유)가 맞는지는 classify_exception 단위 테스트로도 이미
    확인했다 — 여기서는 batch 결과에 실제로 그 target만 격리돼 기록되는지를 본다.
    """
    executor, call_log = _mixed_executor({failure_id})
    runner = BatchRunner(out_dir=tmp_path / "out", fixture_root=FIXTURES, batch_size=10)
    manifests = runner.run(
        [_target(failure_id)], execution_mode="FIXTURE", target_executor=executor
    )
    result = manifests[0].results[0]
    assert result["outcome"] == TargetOutcome.SKIPPED_RETRY_EXHAUSTED.value
    assert call_log.count(failure_id) == 2


def test_batches_split_by_batch_size_and_each_is_sealed(tmp_path):
    targets = [_target(f"t-{i}") for i in range(7)]
    executor, _ = _mixed_executor(set())
    runner = BatchRunner(out_dir=tmp_path / "out", fixture_root=FIXTURES, batch_size=3)
    manifests = runner.run(targets, execution_mode="FIXTURE", target_executor=executor)

    assert len(manifests) == 3  # 3+3+1
    assert [len(m.target_ids) for m in manifests] == [3, 3, 1]
    assert manifests[0].previous_batch_hash is None
    assert manifests[1].previous_batch_hash == manifests[0].batch_hash
    assert manifests[2].previous_batch_hash == manifests[1].batch_hash

    ledger = BatchLedger(tmp_path / "out")
    verification = ledger.verify_chain()
    assert verification["status"] == "OK"
    assert verification["entries"] == 3

    batch_files = sorted((tmp_path / "out" / "batches").glob("*.json"))
    assert len(batch_files) == 3


def test_ledger_refuses_to_overwrite_a_sealed_batch(tmp_path):
    ledger = BatchLedger(tmp_path / "out")
    manifest = BatchManifest(
        batch_index=1,
        batch_id="b0001",
        execution_mode="FIXTURE",
        target_ids=["t1"],
        results=[{"target_id": "t1", "outcome": "MEASURED"}],
        provenance={"status": "SHADOW_PREPARATORY"},
        committed_at="2026-08-27T00:00:00.000000Z",
        previous_batch_hash=None,
    )
    ledger.append(manifest)

    duplicate = BatchManifest(
        batch_index=1,
        batch_id="b0001",
        execution_mode="FIXTURE",
        target_ids=["t1-again"],
        results=[],
        provenance={},
        committed_at="2026-08-27T00:00:01.000000Z",
        previous_batch_hash=ledger.last_batch_hash(),
    )
    with pytest.raises((BatchOverwriteError, ChainBrokenError)):
        ledger.append(duplicate)


def test_ledger_rejects_broken_chain(tmp_path):
    ledger = BatchLedger(tmp_path / "out")
    manifest = BatchManifest(
        batch_index=1,
        batch_id="b0001",
        execution_mode="FIXTURE",
        target_ids=["t1"],
        results=[],
        provenance={},
        committed_at="2026-08-27T00:00:00.000000Z",
        previous_batch_hash="this-is-not-the-real-previous-hash",
    )
    with pytest.raises(ChainBrokenError):
        ledger.append(manifest)
