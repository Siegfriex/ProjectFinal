"""E001 배치 러너 — SHADOW_DRY_RUN 은 어떤 항해도, executor 호출도 하지 않는다."""

from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
RESEARCH = REPO / "research" / "landing_accessibility"
sys.path.insert(0, str(RESEARCH / "src"))

from landing_accessibility.e001_runner.batch import BatchRunner  # noqa: E402
from landing_accessibility.e001_runner.outcomes import TargetOutcome  # noqa: E402
from landing_accessibility.e001_runner.plan import TargetSpec  # noqa: E402


def _targets() -> list[TargetSpec]:
    return [
        TargetSpec(
            target_id=f"t-{i}",
            canonical_service_key=f"svc{i}",
            official_url=f"https://example.com/{i}",
            interaction_archetype="CONTENT_OPEN",
        )
        for i in range(4)
    ]


def test_shadow_dry_run_never_calls_executor(tmp_path):
    def exploding_executor(target):
        raise AssertionError("SHADOW_DRY_RUN 인데 executor 가 호출됐다")

    runner = BatchRunner(out_dir=tmp_path / "out", fixture_root=RESEARCH / "fixtures")
    manifests = runner.run(
        _targets(), execution_mode="SHADOW_DRY_RUN", target_executor=exploding_executor
    )

    assert len(manifests) == 1
    outcomes = {r["outcome"] for r in manifests[0].results}
    assert outcomes == {TargetOutcome.PLANNED_NOT_EXECUTED.value}
    assert not (tmp_path / "out" / "evidence").exists(), "dry-run 인데 evidence run 이 생겼다"


def test_shadow_dry_run_does_not_require_fixture_override(tmp_path):
    """FIXTURE 모드와 달리, SHADOW_DRY_RUN 은 fixture_override 가 없어도 계획 검증만 한다."""
    runner = BatchRunner(out_dir=tmp_path / "out", fixture_root=RESEARCH / "fixtures")
    manifests = runner.run(_targets(), execution_mode="SHADOW_DRY_RUN")
    assert len(manifests[0].results) == 4
