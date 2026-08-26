"""P-C 픽스처 파이프라인 진입점 — L0 수집 + append-only 강제 + 무결성 검증을
한 호출 순서 안에서 실행한다.

닫는 결함(Pilot 감사 append-only-not-enforced, MEDIUM): append-only 가드를
"정의는 있지만 아무도 안 부르는 함수"로 남기지 않는다. ``run_l0_batch`` 는
매 관측 뒤에 ``GuardedEvidenceWriter.finalize()`` 를 호출하고, 실패하면
그 자리에서 예외를 던져 배치를 멈춘다 — 호출 누락이 구조적으로 불가능하다.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .execution_mode import enforce_real_target_firewall
from .guarded_writer import GuardedEvidenceWriter
from .l0_collector import L0Observation, collect_l0_fixture


@dataclass
class L0BatchResult:
    run_dir: Path
    execution_mode: str
    observations: list[L0Observation] = field(default_factory=list)
    finalize_report: dict[str, Any] | None = None


def run_l0_batch(
    *,
    run_root: Path,
    run_id: str,
    targets: list[dict[str, str]],
    execution_mode: str = "FIXTURE",
) -> L0BatchResult:
    """targets: 각각
    ``{"fixture_path", "service_id", "canonical_url", "audit_date", "protocol_version"}``.
    """
    # REAL-TARGET FIREWALL — 배치 전체를 막는 가장 바깥쪽 검사.
    enforce_real_target_firewall(execution_mode)

    run_dir = run_root / run_id
    store = GuardedEvidenceWriter(run_dir, run_id=run_id, execution_mode=execution_mode)
    result = L0BatchResult(run_dir=run_dir, execution_mode=execution_mode)

    for t in targets:
        obs = collect_l0_fixture(
            fixture_path=Path(t["fixture_path"]),
            service_id=t["service_id"],
            canonical_url=t["canonical_url"],
            audit_date=t["audit_date"],
            protocol_version=t["protocol_version"],
            store=store,
            execution_mode=execution_mode,
        )
        result.observations.append(obs)
        # append-only 를 여기서 실제로 호출한다 — 정의만 하고 안 부르는 실수를
        # 이 진입점 하나로 구조적으로 막는다. 실패 시 배치를 멈춘다(fail-closed).
        result.finalize_report = store.finalize()

    return result
