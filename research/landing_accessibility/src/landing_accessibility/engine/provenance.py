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

from .firewall import SHADOW_LANE, ExecutionScope, evaluate_execution_scope, p0_closed

#: `PHASE_GATES §4.4` LANE C 의 base SHA. 이 브랜치가 갈라져 나온 지점.
BASE_SHA = "d5f1da5652953542d5c8be377026cc3293f2075a"

#: 이 lane 이 구현하는 수집 프로토콜의 버전. `observation_id` 해시 입력에 들어간다.
#:
#: **E000 과 E001 이 같은 값으로 돌아야 한다.** 값이 갈리면 E000 evidence 를 E001 의
#: batch-0 으로 재사용할 수 없고 provenance drift 가 된다 — 실제 수집을 위해 이 상수를
#: 새로 만들지 않고 그대로 쓴다 (수집기 코드가 같으므로 프로토콜도 같다).
PROTOCOL_VERSION = "v2.0-pc-fixture-1"

SHADOW_STATUS = "SHADOW_PREPARATORY"

#: P0 승격 후 실제 서비스 수집 run 의 status. SHADOW 산출물과 **다른 값**이어야
#: 하류가 둘을 섞지 않는다.
REAL_TARGET_STATUS = "REAL_TARGET_COLLECTION"


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
            "created_before_p0_close": not p0_closed(),
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


@dataclass(frozen=True)
class RealTargetProvenance(ShadowProvenance):
    """P0 승격 후 **실제 서비스 수집** run 의 provenance.

    `ShadowProvenance` 를 상속하되 `as_dict()` 를 완전히 대체한다 — 필드 이름은 같지만
    값의 의미가 정반대다:

    | 필드 | SHADOW | REAL |
    |---|---|---|
    | `status` | `SHADOW_PREPARATORY` | `REAL_TARGET_COLLECTION` |
    | `created_before_p0_close` | `true` | `false` (P0 는 이미 닫혔다) |
    | `real_target_measurement` | `false` | **`true`** |
    | `fixture_only` | `true` | `false` |
    | `authoritative` | `false` | `true` |

    `real_target_measurement` 를 `false` 로 둔 채 실제 수집을 하면 하류가 그 산출물을
    fixture 산물로 오인한다 — 그래서 이 dataclass 는 그 값을 **하드코딩으로 true** 로
    두고, 대신 어느 scope 의 승인으로 열렸는지(`execution_scope` · `promoted_main_sha`)를
    함께 싣는다.
    """

    execution_scope: str = ExecutionScope.E000_FAST.value
    promoted_main_sha: str | None = None
    release_document_ref: str | None = None
    release_document_sha256: str | None = None

    @classmethod
    def for_scope(
        cls,
        scope: object = ExecutionScope.E000_FAST,
        *,
        base_sha: str = BASE_SHA,
        execution_lane: str = SHADOW_LANE,
        protocol_version: str = PROTOCOL_VERSION,
        input_authority_sha: str | None = None,
        source_frame_sha: str | None = None,
        codebook_sha: str | None = None,
    ) -> RealTargetProvenance:
        """릴리스 문서를 런타임에 읽어 승인 근거를 provenance 에 박아 넣는다."""
        verdict = evaluate_execution_scope(scope)
        return cls(
            base_sha=base_sha,
            shadow_lane=execution_lane,
            protocol_version=protocol_version,
            input_authority_sha=input_authority_sha,
            source_frame_sha=source_frame_sha,
            codebook_sha=codebook_sha,
            execution_scope=verdict.scope,
            promoted_main_sha=verdict.promoted_main_sha,
            release_document_ref=verdict.document_ref,
            release_document_sha256=verdict.document_sha256,
        )

    def as_dict(self) -> dict[str, Any]:
        block: dict[str, Any] = {
            "status": REAL_TARGET_STATUS,
            "base_sha": self.base_sha,
            "created_at": self.created_at,
            "created_before_p0_close": False,
            "authoritative": True,
            "real_target_outcome_used": True,
            "requires_post_p0_reconciliation": False,
            "shadow_lane": self.shadow_lane,
            "execution_lane": self.shadow_lane,
            "protocol_version": self.protocol_version,
            "fixture_only": False,
            "real_target_measurement": True,
            "execution_scope": self.execution_scope,
            "promoted_main_sha": self.promoted_main_sha,
            "release_document_ref": self.release_document_ref,
            "release_document_sha256": self.release_document_sha256,
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
    if block["status"] == REAL_TARGET_STATUS:
        validate_real_target_provenance(block)
        return
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


#: 실제 수집 provenance 가 반드시 갖춰야 하는 추가 필드.
REQUIRED_REAL_TARGET_FIELDS: frozenset[str] = frozenset(
    {"real_target_measurement", "execution_scope", "promoted_main_sha", "protocol_version"}
)


def validate_real_target_provenance(block: dict[str, Any]) -> None:
    """실제 서비스 수집 run 의 provenance 계약 (`REAL_TARGET_COLLECTION`).

    SHADOW 계약의 거울상이다 — 여기서 `real_target_measurement = false` 는
    **거짓 신고**이며, 하류가 실제 수집 산출물을 fixture 산물로 오인하게 만든다.
    그래서 그 값이 `true` 가 아니면 실패시킨다.
    """
    missing = REQUIRED_REAL_TARGET_FIELDS - block.keys()
    if missing:
        raise ProvenanceError(f"REAL_TARGET provenance 필수 필드 누락: {sorted(missing)}")
    if block["status"] != REAL_TARGET_STATUS:
        raise ProvenanceError(f"status 는 {REAL_TARGET_STATUS} 여야 한다: {block['status']!r}")
    if block["real_target_measurement"] is not True:
        raise ProvenanceError(
            "실제 수집 run 인데 real_target_measurement 가 true 가 아니다 — "
            "이 값이 거짓이면 하류가 실제 수집 산출물을 fixture 산물로 오인한다."
        )
    if block.get("fixture_only", False) is not False:
        raise ProvenanceError("실제 수집 run 은 fixture_only = false 다")
    if block["created_before_p0_close"] is not False:
        raise ProvenanceError(
            "실제 수집은 P0 종료 후에만 일어난다 — created_before_p0_close 는 false 여야 한다"
        )
    if block["real_target_outcome_used"] is not True:
        raise ProvenanceError("실제 수집 run 은 real_target_outcome_used = true 다")
    if not block.get("execution_scope"):
        raise ProvenanceError("execution_scope 가 비어 있다 — 어느 승인 범위인지 알 수 없다")
    if not block.get("promoted_main_sha"):
        raise ProvenanceError(
            "promoted_main_sha 가 비어 있다 — 어느 승격 위에서 수집했는지 증명할 수 없다"
        )
