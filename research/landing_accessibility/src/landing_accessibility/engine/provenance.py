"""SHADOW provenance 블록 — `PHASE_GATES.md §4.3`.

P0 종료 전 생성된 downstream 산출물은 **전부** `status = SHADOW_PREPARATORY` 를 갖고
아래 provenance 를 기록한다. 이 lane 이 만드는 evidence run, task manifest, 엔진 리포트가
그 대상이다.

이 블록이 없는 산출물은 나중에 "P0 전 것인지 후 것인지" 구분할 수 없고,
`§4.7` reconciliation 이 성립하지 않는다. **그래서 산출물마다 붙인다.**
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from .firewall import SHADOW_LANE, real_target_permitted

#: `PHASE_GATES §4.4` LANE C 의 base SHA. 이 브랜치가 갈라져 나온 지점.
BASE_SHA = "d5f1da5652953542d5c8be377026cc3293f2075a"

#: 이 lane 이 구현하는 수집 프로토콜의 버전. `observation_id` 해시 입력에 들어간다.
PROTOCOL_VERSION = "v2.0-pc-fixture-1"

SHADOW_STATUS = "SHADOW_PREPARATORY"


def utc_now_iso() -> str:
    """`A1 §6.1` — UTC ISO-8601. 마이크로초까지 남긴다(같은 날 재수집 구분, `A1 §6.3`)."""
    return datetime.now(UTC).isoformat(timespec="microseconds").replace("+00:00", "Z")


@dataclass(frozen=True)
class ShadowProvenance:
    """`PHASE_GATES §4.3` 필수 5필드 + 권장 6필드."""

    created_at: str = field(default_factory=utc_now_iso)
    base_sha: str = BASE_SHA
    shadow_lane: str = SHADOW_LANE
    protocol_version: str = PROTOCOL_VERSION
    input_authority_sha: str | None = None
    source_frame_sha: str | None = None
    codebook_sha: str | None = None

    def as_dict(self) -> dict[str, Any]:
        block: dict[str, Any] = {
            "status": SHADOW_STATUS,
            "base_sha": self.base_sha,
            "created_at": self.created_at,
            "created_before_p0_close": not real_target_permitted(),
            "authoritative": False,
            "real_target_outcome_used": False,
            "requires_post_p0_reconciliation": True,
            "shadow_lane": self.shadow_lane,
            "protocol_version": self.protocol_version,
            "fixture_only": True,
            "real_target_measurement": False,
        }
        for key, value in (
            ("input_authority_sha", self.input_authority_sha),
            ("source_frame_sha", self.source_frame_sha),
            ("codebook_sha", self.codebook_sha),
        ):
            if value is not None:
                block[key] = value
        return block


class ProvenanceError(ValueError):
    """SHADOW provenance 계약 위반."""


REQUIRED_PROVENANCE_FIELDS: frozenset[str] = frozenset(
    {
        "status",
        "base_sha",
        "created_at",
        "created_before_p0_close",
        "authoritative",
        "real_target_outcome_used",
        "requires_post_p0_reconciliation",
    }
)


def validate_provenance(block: dict[str, Any]) -> None:
    """산출물에 붙은 provenance 블록이 `§4.3` 계약을 만족하는지 검사한다.

    `authoritative = True` 나 `real_target_outcome_used = True` 가 섞여 들어오면
    그 산출물은 이 lane 의 것이 아니다 — 조용히 고치지 않고 실패시킨다.
    """
    missing = REQUIRED_PROVENANCE_FIELDS - block.keys()
    if missing:
        raise ProvenanceError(f"SHADOW provenance 필수 필드 누락: {sorted(missing)}")
    if block["status"] != SHADOW_STATUS:
        raise ProvenanceError(f"status 는 {SHADOW_STATUS} 여야 한다: {block['status']!r}")
    if block["authoritative"] is not False:
        raise ProvenanceError("P0 종료 전 산출물은 authoritative = false 다 (PHASE_GATES §4.3)")
    if block["real_target_outcome_used"] is not False:
        raise ProvenanceError(
            "real_target_outcome_used = true — real-target outcome 을 썼다면 "
            "PHASE_GATES §4.1 위반이며 P0 finding 이다 (§4.6)"
        )
    if block["requires_post_p0_reconciliation"] is not True:
        raise ProvenanceError("requires_post_p0_reconciliation 은 true 여야 한다")
    if block.get("real_target_measurement", False) is not False:
        raise ProvenanceError("real_target_measurement = true 는 이 lane 에서 존재할 수 없다")
