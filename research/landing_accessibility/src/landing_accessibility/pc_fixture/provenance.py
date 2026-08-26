"""SHADOW/PREPARATORY 산출물 provenance 블록 — ``docs/v2/PHASE_GATES.md`` §4.3.

P0 종료 전 생성되는 모든 downstream 산출물은 이 블록을 가져야 한다.
단일 생성 함수로 만들어 이 레인의 모든 기록(observation record, run-level
``provenance.json``)이 항상 같은 값을 쓰게 한다 — 필드를 여기저기서 손으로
다시 적으면 그 자체가 drift 다.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

#: 오케스트레이터 프롬프트가 지정한 이 레인의 base — Claude A 의 최신 exec 커밋.
BASE_SHA = "d5f1da5"
SHADOW_LANE = "P-C"


def build_provenance(*, extra: dict[str, Any] | None = None) -> dict[str, Any]:
    d: dict[str, Any] = {
        "base_sha": BASE_SHA,
        "created_at": datetime.now(UTC).isoformat(),
        "created_before_p0_close": True,
        "authoritative": False,
        "real_target_outcome_used": False,
        "requires_post_p0_reconciliation": True,
        "shadow_lane": SHADOW_LANE,
        "fixture_only": True,
        "real_target_measurement": False,
    }
    if extra:
        d.update(extra)
    return d
