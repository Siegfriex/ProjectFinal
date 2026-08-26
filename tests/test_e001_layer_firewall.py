"""E001 배치 러너 — REAL_TARGET firewall이 **이 층에서 독립적으로** 재확인되는가.

`landing_accessibility.engine.firewall`의 가드는 P-C 자체 테스트
(`tests/test_pc_firewall.py`)가 이미 증명했다. 이 파일은 그것과 별개로,
`e001_runner.layer_firewall`이 엔진 모듈을 **import조차 하지 않고도**
독립적으로 REAL_TARGET을 막는다는 것과, `BatchRunner.run()`이 두 firewall을
모두 통과시켜야만 진행한다는 것을 증명한다.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
RESEARCH = REPO / "research" / "landing_accessibility"
sys.path.insert(0, str(RESEARCH / "src"))

from landing_accessibility.e001_runner import layer_firewall  # noqa: E402
from landing_accessibility.e001_runner.batch import BatchRunner  # noqa: E402
from landing_accessibility.e001_runner.plan import TargetSpec  # noqa: E402
from landing_accessibility.engine.firewall import (  # noqa: E402
    ExecutionMode,
    RealTargetBlockedError,
)


def test_layer_firewall_module_does_not_import_engine_firewall():
    """독립성의 구조적 증거 — 이 모듈의 소스에 엔진 firewall import 문이 없다.

    (docstring 안에서 엔진 모듈을 산문으로 *언급*하는 것은 무방하다 — 여기서 막는
    것은 실제 `import`/`from ... import` 의존이다.)
    """
    src = Path(layer_firewall.__file__).read_text(encoding="utf-8")
    import_lines = [
        line.strip() for line in src.splitlines() if line.strip().startswith(("import ", "from "))
    ]
    assert not any("landing_accessibility.engine" in line for line in import_lines)
    assert not any(".firewall" in line for line in import_lines)


@pytest.mark.parametrize("mode", ["REAL_TARGET", ExecutionMode.REAL_TARGET])
def test_layer_firewall_blocks_real_target_standalone(mode):
    """엔진 모듈을 전혀 거치지 않고, 이 층의 함수 하나만 직접 불러 REAL_TARGET을 막는다."""
    with pytest.raises(layer_firewall.BatchRealTargetBlockedError):
        layer_firewall.assert_batch_execution_mode_safe(mode)


def test_layer_firewall_blocks_unknown_mode():
    with pytest.raises(layer_firewall.BatchRealTargetBlockedError):
        layer_firewall.assert_batch_execution_mode_safe("SOMETHING_MADE_UP")


@pytest.mark.parametrize("mode", ["FIXTURE", "SHADOW_DRY_RUN"])
def test_layer_firewall_allows_fixture_and_dry_run(mode):
    assert layer_firewall.assert_batch_execution_mode_safe(mode) == mode


def _one_target() -> list[TargetSpec]:
    return [
        TargetSpec(
            target_id="t1",
            canonical_service_key="svc1",
            official_url="https://example.com/should-never-be-opened",
            interaction_archetype="CONTENT_OPEN",
            fixture_override="simple_article.html",
        )
    ]


def test_batch_runner_blocks_real_target_end_to_end(tmp_path):
    """`BatchRunner.run()`은 두 firewall을 모두 거친다 — REAL_TARGET을 요청하면
    엔진의 `RealTargetBlockedError` 또는 이 층의 `BatchRealTargetBlockedError`
    중 하나가 (구현상 엔진 것이 먼저 발화하지만) 반드시 나며, 어느 target도
    실행되지 않는다.
    """
    runner = BatchRunner(out_dir=tmp_path / "out", fixture_root=RESEARCH / "fixtures", batch_size=5)
    called = []

    def spy_executor(target):
        called.append(target.target_id)
        raise AssertionError("REAL_TARGET 이 차단되지 않고 executor 까지 도달했다")

    with pytest.raises((RealTargetBlockedError, layer_firewall.BatchRealTargetBlockedError)):
        runner.run(_one_target(), execution_mode="REAL_TARGET", target_executor=spy_executor)

    assert called == [], "firewall 을 통과하지 못했는데 target executor 가 호출됐다"
    sealed_batches = list((tmp_path / "out" / "batches").glob("*.json"))
    assert sealed_batches == [], "차단됐는데 봉인된 batch 파일이 만들어졌다"


def test_batch_runner_blocks_real_target_enum_form(tmp_path):
    runner = BatchRunner(out_dir=tmp_path / "out", fixture_root=RESEARCH / "fixtures")
    with pytest.raises((RealTargetBlockedError, layer_firewall.BatchRealTargetBlockedError)):
        runner.run(_one_target(), execution_mode=ExecutionMode.REAL_TARGET)
