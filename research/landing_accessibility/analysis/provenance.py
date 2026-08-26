"""SHADOW provenance 블록 — `PHASE_GATES.md §4.3`.

P0(`V2_SSOT_FROZEN`) 종료 전에 생성되는 모든 downstream 산출물은 이 절이 요구하는
provenance를 가져야 한다. 이 모듈은 그 블록을 한 곳에서 만든다 — 산출물마다
필드를 다시 나열하면서 드리프트가 생기는 것을 막기 위해서다.

이 lane의 provenance (오케스트레이터 지시 원문):

```
base_sha=2025e56.., created_before_p0_close=true, authoritative=false,
real_target_outcome_used=false, requires_post_p0_reconciliation=true,
shadow_lane="ANALYSIS_SKELETON"
```
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

#: 이 워크트리의 base SHA — `claude-b/analysis-skeleton` (base = `agent/landing-v2-exec` @ 2025e56).
BASE_SHA = "2025e56"
SHADOW_LANE = "ANALYSIS_SKELETON"


@dataclass(frozen=True)
class ShadowProvenance:
    """`PHASE_GATES.md §4.3` 이 요구하는 필드 + 권장 필드."""

    base_sha: str = BASE_SHA
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    created_before_p0_close: bool = True
    authoritative: bool = False
    real_target_outcome_used: bool = False
    requires_post_p0_reconciliation: bool = True
    shadow_lane: str = SHADOW_LANE
    fixture_only: bool = True
    real_target_measurement: bool = False
    source_kind: str = "SYNTHETIC"  # SYNTHETIC | EMPTY | (실제 데이터는 이 lane에서 만들지 않는다)

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


#: 모든 EDA/deliverable 산출물 하단에 붙이는 해석 절제 문구.
#: 목표 3 지시 — "해석을 과장하지 않는 문구 원칙".
INTERPRETATION_DISCIPLINE_NOTICE = (
    "이 산출물은 synthetic/fixture 데이터로만 검증됐다. 실제 서비스 접근성 결과가 "
    "아니며, 여기 담긴 수치·차트로 실제 서비스의 접근성·사용성을 주장하지 않는다. "
    "P0(`V2_SSOT_FROZEN`) 종료 후 실제 E001 데이터로 재실행·재조정(`§4.7 SHADOW "
    "RECONCILIATION`)이 필요하다. 임의 임계값(`depth >= N = bad` 류)을 도입하지 않는다."
)


def file_sha256(path: str | Path) -> str:
    """산출물 SHA — `source artifact SHA` 필드용."""
    p = Path(path)
    h = hashlib.sha256()
    h.update(p.read_bytes())
    return h.hexdigest()


def write_provenance_sidecar(out_path: str | Path, provenance: ShadowProvenance) -> Path:
    """산출물 `<name>.provenance.json` sidecar를 쓰고 경로를 돌려준다."""
    out_path = Path(out_path)
    sidecar = out_path.with_suffix(out_path.suffix + ".provenance.json")
    sidecar.write_text(
        json.dumps(provenance.as_dict(), ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return sidecar
