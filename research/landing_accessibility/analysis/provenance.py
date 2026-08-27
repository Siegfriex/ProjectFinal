"""SHADOW provenance 블록 — `PHASE_GATES.md §4.3`.

P0(`V2_SSOT_FROZEN`) 종료 전에 생성되는 모든 downstream 산출물은 이 절이 요구하는
provenance를 가져야 한다. 이 모듈은 그 블록을 한 곳에서 만든다 — 산출물마다
필드를 다시 나열하면서 드리프트가 생기는 것을 막기 위해서다.

이 lane의 provenance (오케스트레이터 지시 원문, `PHASE_GATES.md §4.3`):

```
base_sha=397a10d.., created_before_p0_close=true, authoritative=false,
real_target_outcome_used=false, requires_post_p0_reconciliation=true,
shadow_lane="ANALYSIS_CURRENT"
```

이 lane은 `claude-b/analysis-skeleton`(base=`agent/landing-v2-exec`@2025e56)의
후속이다 — base가 `claude-b/integration-current`@397a10d(P-C AI review cascade
merge 포함)로 갱신됐고, `fact_ai_adjudication` 빌더가 `ai_review.py`의 실제
`AdjudicationRecord`에 바인딩됐다(`marts/adjudication_binding.py`).
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

#: 이 워크트리의 base SHA — `claude-b/analysis-current` (base = `claude-b/integration-current` @ 397a10d).
BASE_SHA = "397a10d"
SHADOW_LANE = "ANALYSIS_CURRENT"


@dataclass(frozen=True)
class ShadowProvenance:
    """`PHASE_GATES.md §4.3` 이 요구하는 필드 + 권장 필드."""

    base_sha: str = BASE_SHA
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    created_before_p0_close: bool = True
    authoritative: bool = False
    #: 분석의 종속·독립 변수값(접근성 판정 결과)을 쓰지 않았다. 유지된다.
    real_target_outcome_used: bool = False
    #: **신설** — 실제 REAL TARGET 산출물을 **읽기는 했다**. "읽지 않았다"와
    #: "읽었으나 결과값은 쓰지 않았다"는 다른 진술이고, 후자가 사실이므로 후자를
    #: 적는다. 아무것도 적지 않으면 독자는 전자를 추론한다 (Claude A 판정).
    real_target_artifacts_read: bool = True
    #: 무엇을 읽었고 **무엇을 읽지 않았는지**를 함께 적는다 — "읽었다"만 적으면
    #: 이번엔 반대로 과대 경고가 된다.
    real_target_artifacts_read_detail: dict[str, Any] = field(
        default_factory=lambda: {
            "what": "<out_dir>/batches/batch_*.json 의 results[].detail",
            "fields": [
                "blocked_category",
                "blocked_reason",
                "scout_invoked",
                "endpoint_status",
                "endpoint_status_detail",
                "auth_gate_observed",
                "notes",
            ],
            "not_read_for_analysis_input": (
                "KWCAG verdict · OlderRelevantKWCAGFailRate · obstruction 측정값 — "
                "즉 분석의 종속·독립 변수값은 이 경로로 읽지 않았다"
            ),
            "purpose": "가드 차단·E-6b 발화 계수 파생 (수집 역학 정보)",
        }
    )
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
