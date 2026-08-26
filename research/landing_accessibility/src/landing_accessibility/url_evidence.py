"""P-B `dim_web_target` 머티리얼라이제이션 — read-only view. 원본 parquet 를 쓰지 않는다.

## 정본

- `docs/v2/01_DATA_SPEC_v2.0.md` §3 `dim_web_target`
- `docs/v2/A2_VOCABULARY_AND_SCHEMA_BINDING.md` §5.5 (`web_target_group` ↔ `dim_web_target`
  grain 불일치), §5.7 매핑 레이어 산출 규약 (V-4~V-8)

## grain 문제 — 이 모듈이 정면으로 다루는 것

`state/web_target_group.parquet` 은 `dim_web_target` 이 **아니다.** URL 확정 이전의
**그룹 후보 표**다(A2 §5.5). 68개 그룹 중 3개(`CANDIDATE_PENDING_URL_REVIEW`)는 두
measurement_entity 가 "같은 랜딩일 것" 이라는 **가설**을 갖고 있을 뿐, 확정된 것은
0건이다(`expected_url_relationship_confirmed_by_url = True` 0건, 실측).

그래서 `web_target_id` 를 그룹에서 그대로 물려받지 않는다. `target_grouping.py` 의
falsifier 판정 결과에 따라:

- `CONFIRMED_SHARED_TARGET` → 그룹의 모든 구성원이 **하나**의 `web_target_id` 를 공유한다
- `SPLIT` 또는 애초에 singleton → 구성원마다 **독립** `web_target_id` 를 받는다
- 아직 `CANDIDATE_PENDING_URL_REVIEW` (falsifier 미검정) → `web_target_id` 를 아직
  발급하지 않는다. `web_target_status = PENDING_URL_REVIEW` 로 남긴다
  (규칙 W-1 — Frame 값은 관측이 아니라 재판정으로만 바뀐다. 여기서는 아직 재판정 자체가
  없으므로 그룹 가설 그대로 미결로 둔다)

## 이 모듈이 하지 않는 것

- `state/*.parquet` 원본을 쓰지 않는다(A2 규칙 V-4). 입력을 읽고 새 표만 만든다.
- `web_eligibility_status`/`web_target_status` 판정을 직접 내리지 않는다 —
  `web_eligibility.py`/`target_grouping.py` 가 만든 결과를 그대로 받아 조립만 한다.

## SHADOW / PREPARATORY — `PHASE_GATES.md` §4.3 / §4.5

이 표의 모든 행은 자신을 만든 `WebEligibilityDetermination.execution_mode` 를 그대로
물려받는다 — 머티리얼라이제이션 단계에서 조용히 사라지면 하류가 이 행이
FIXTURE/SHADOW_DRY_RUN 산출인지 알 길이 없어진다.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass

from landing_accessibility.shadow_provenance import require_execution_mode
from landing_accessibility.target_grouping import FalsifierVerdict
from landing_accessibility.web_eligibility import (
    WEB_ELIGIBILITY_STATUS,
    WEB_TARGET_STATUS,
    WebEligibilityDetermination,
)


class UrlEvidenceError(ValueError):
    pass


def _stable_web_target_id(*parts: str) -> str:
    """결정적 id. `service_master.service_id`(`svc_<hash>`) 명명 관례를 따른다.

    난수/시각 기반이 아니다 — 같은 입력이면 재실행해도 같은 id 가 나와야
    append-only 갱신에서 이전 `web_target_id` 참조가 깨지지 않는다.
    """
    digest = hashlib.sha256("\x1f".join(parts).encode("utf-8")).hexdigest()[:16]
    return f"wt_{digest}"


@dataclass(frozen=True)
class DimWebTargetRow:
    """`01_DATA_SPEC_v2.0.md` §3 `dim_web_target` 정본 필드 그대로."""

    web_target_id: str | None
    measurement_entity_id: str
    web_eligibility_status: str
    official_landing_url: str | None
    final_url: str | None
    registered_domain: str | None
    url_evidence: tuple[dict[str, str | None], ...]
    url_confidence: float | None
    web_target_status: str
    superseded_from_web_target_id: str | None = None
    execution_mode: str = "SHADOW_DRY_RUN"

    def __post_init__(self) -> None:
        require_execution_mode(self.execution_mode)  # §4.5 — REAL_TARGET 은 여기서 hard FAIL
        if self.web_eligibility_status not in WEB_ELIGIBILITY_STATUS:
            raise UrlEvidenceError(
                f"web_eligibility_status={self.web_eligibility_status!r} 미허용값"
            )
        if self.web_target_status not in WEB_TARGET_STATUS:
            raise UrlEvidenceError(f"web_target_status={self.web_target_status!r} 미허용값")
        if self.web_target_status == "FROZEN" and not self.web_target_id:
            raise UrlEvidenceError("FROZEN 행은 web_target_id 가 있어야 한다 (00 §15)")
        if self.url_confidence is not None and not 0.0 <= self.url_confidence <= 1.0:
            raise UrlEvidenceError(f"url_confidence={self.url_confidence!r} 은 [0,1] 밖이다")

    def as_dict(self) -> dict[str, object]:
        return {
            "web_target_id": self.web_target_id,
            "measurement_entity_id": self.measurement_entity_id,
            "web_eligibility_status": self.web_eligibility_status,
            "official_landing_url": self.official_landing_url,
            "final_url": self.final_url,
            "registered_domain": self.registered_domain,
            "url_evidence": list(self.url_evidence),
            "url_confidence": self.url_confidence,
            "web_target_status": self.web_target_status,
            "superseded_from_web_target_id": self.superseded_from_web_target_id,
            "execution_mode": self.execution_mode,
        }


@dataclass(frozen=True)
class EntityUrlInput:
    """한 measurement_entity 에 대해 이미 확정된 URL 증거. 이 모듈이 새로 만들지 않는다."""

    measurement_entity_id: str
    determination: WebEligibilityDetermination
    official_landing_url: str | None = None
    final_url: str | None = None
    registered_domain: str | None = None
    url_confidence: float | None = None


def materialize_singleton(entity: EntityUrlInput) -> DimWebTargetRow:
    """member_count = 1 그룹(현재 65/68) — 그룹 판정이 필요 없다. 1:1 로 즉시 조립."""
    status = entity.determination.web_eligibility_status
    if status == "ELIGIBLE_WEB":
        target_status = "FROZEN"
        web_target_id = _stable_web_target_id("singleton", entity.measurement_entity_id)
    elif status in {
        "EXCLUDED_INDUSTRY_AXIS",
        "EXCLUDED_APP_ONLY",
        "EXCLUDED_NO_PUBLIC_WEB_LANDING",
    }:
        target_status = "EXCLUDED"
        web_target_id = None
    elif status == "UNDETERMINED_URL_EVIDENCE":
        target_status = "PENDING_URL_REVIEW"
        web_target_id = None
    else:  # NOT_ASSESSED
        target_status = "DRAFT"
        web_target_id = None

    return DimWebTargetRow(
        web_target_id=web_target_id,
        measurement_entity_id=entity.measurement_entity_id,
        web_eligibility_status=status,
        official_landing_url=entity.official_landing_url,
        final_url=entity.final_url,
        registered_domain=entity.registered_domain,
        url_evidence=tuple(e.as_dict() for e in entity.determination.evidence),
        url_confidence=entity.url_confidence,
        web_target_status=target_status,
        execution_mode=entity.determination.execution_mode,
    )


def materialize_group(
    entities: list[EntityUrlInput],
    verdict: FalsifierVerdict,
    *,
    web_target_group_id: str,
) -> list[DimWebTargetRow]:
    """member_count >= 2 그룹 — `target_grouping.py` 의 falsifier 판정에 따라 갈라진다."""
    if len(entities) < 2:
        raise UrlEvidenceError("materialize_group 은 member_count >= 2 에만 쓴다")

    if verdict.grouping_status == "CANDIDATE_PENDING_URL_REVIEW":
        # 아직 검정 불가 — 각 구성원을 개별 미결 행으로 남긴다. web_target_id 미발급.
        return [
            DimWebTargetRow(
                web_target_id=None,
                measurement_entity_id=e.measurement_entity_id,
                web_eligibility_status=e.determination.web_eligibility_status,
                official_landing_url=e.official_landing_url,
                final_url=e.final_url,
                registered_domain=e.registered_domain,
                url_evidence=tuple(ev.as_dict() for ev in e.determination.evidence),
                url_confidence=e.url_confidence,
                web_target_status="PENDING_URL_REVIEW",
                execution_mode=e.determination.execution_mode,
            )
            for e in entities
        ]

    if verdict.grouping_status == "CONFIRMED_SHARED_TARGET":
        shared_id = _stable_web_target_id("shared", web_target_group_id)
        rows = []
        for e in entities:
            if e.determination.web_eligibility_status != "ELIGIBLE_WEB":
                raise UrlEvidenceError(
                    f"{e.measurement_entity_id}: CONFIRMED_SHARED_TARGET 인데 "
                    f"web_eligibility_status={e.determination.web_eligibility_status!r} — "
                    "공유 타겟으로 확정하려면 구성원 전원이 ELIGIBLE_WEB 이어야 한다"
                )
            rows.append(
                DimWebTargetRow(
                    web_target_id=shared_id,
                    measurement_entity_id=e.measurement_entity_id,
                    web_eligibility_status="ELIGIBLE_WEB",
                    official_landing_url=e.official_landing_url,
                    final_url=e.final_url,
                    registered_domain=e.registered_domain,
                    url_evidence=tuple(ev.as_dict() for ev in e.determination.evidence),
                    url_confidence=e.url_confidence,
                    web_target_status="FROZEN",
                    execution_mode=e.determination.execution_mode,
                )
            )
        return rows

    if verdict.grouping_status == "SPLIT":
        return [materialize_singleton(e) for e in entities]

    raise UrlEvidenceError(f"grouping_status={verdict.grouping_status!r} 은 미지원 값이다")
