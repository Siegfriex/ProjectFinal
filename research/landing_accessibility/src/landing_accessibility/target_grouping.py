"""P-B target grouping — `web_target_group` 의 3개 후보 그룹을 URL 증거로 검정한다.

## 배경

`state/web_target_group.parquet` (68행, C012 산물) 은 이미 3건의 `CANDIDATE_PENDING_URL_REVIEW`
그룹을 갖고 있다 (coupang / gmarket / naver — 원문 표기가 우연히 같거나 접두 관계라는
**가설**). 각 행에 `expected_url_relationship_falsifier` 가 자연어로 이미 적혀 있다:

    coupang: "두 measurement_entity 의 official_landing_url 이 서로 다른 PSL 등록도메인으로
              확정되면 SPLIT 한다."
    gmarket: "RETAIL entity 의 랜딩이 APP entity 와 다른 등록도메인 또는 다른 경로로
              확정되면 SPLIT 한다."
    naver:   "RETAIL entity 의 랜딩이 APP entity 와 다른 등록도메인 또는 다른 경로로
              확정되면 SPLIT 한다."

이 모듈은 그 자연어 falsifier 를 **코드로 검정 가능한 함수**로 바꾼다. 검정 자체는
`official_landing_url` 이 확정돼야 실행 가능하므로(현재 nonnull 0, A2 §5.5 실측),
지금은 인프라만 제공하고 실제 검정은 URL 확정 이후로 남는다.

## 정본

- `docs/v2/A2_VOCABULARY_AND_SCHEMA_BINDING.md` §5.5 "grouping 은 URL 확정 시 SPLIT 될 수 있다"
- `state/web_target_group.parquet` 의 `expected_url_relationship_*` 컬럼 (C012 산물, 그대로 유지)

## 이 모듈이 하지 않는 것

- 그룹을 실제로 SPLIT/CONFIRM 하지 않는다 (그건 URL 이 확정된 뒤 P-B exec 의 몫이다).
- `web_target_group.parquet` 을 쓰지 않는다 — read-only 로만 참조한다
  (A2 §5.7 V-4 "state/*.parquet 원본을 읽기만 하고 쓰지 않는다").

## SHADOW / PREPARATORY — `PHASE_GATES.md` §4.5

이 falsifier 검정은 URL 구조(등록도메인) 비교이지 접근성 verdict 가 아니다 — §4.5의
target-preparation 범주다. `execution_mode` 를 요구하며 REAL_TARGET 은 hard FAIL 이다.
"""

from __future__ import annotations

from dataclasses import dataclass

from landing_accessibility.registered_domain import (
    RegisteredDomainError,
    registered_domain,
)
from landing_accessibility.shadow_provenance import require_execution_mode

GROUPING_STATUS: frozenset[str] = frozenset(
    {
        "CANDIDATE_PENDING_URL_REVIEW",
        "SINGLETON_PENDING_URL_REVIEW",
        "CONFIRMED_SHARED_TARGET",
        "SPLIT",
        "SINGLETON_CONFIRMED",
    }
)


class TargetGroupingError(ValueError):
    pass


@dataclass(frozen=True)
class MemberUrlEvidence:
    """그룹 구성원 measurement_entity 하나의 URL 확정 결과."""

    measurement_entity_id: str
    official_landing_url: str | None
    url_confidence: float | None


@dataclass(frozen=True)
class FalsifierVerdict:
    """falsifier 검정 결과. **CONFIRMED_SHARED_TARGET 판정이 아니다** — SPLIT 여부만 말한다."""

    grouping_status: str  # "SPLIT" | "CONFIRMED_SHARED_TARGET" | "CANDIDATE_PENDING_URL_REVIEW"
    reason: str
    member_registered_domains: dict[str, str | None]
    execution_mode: str = "SHADOW_DRY_RUN"

    def __post_init__(self) -> None:
        require_execution_mode(self.execution_mode)  # §4.5 — REAL_TARGET 은 여기서 hard FAIL


def evaluate_registered_domain_falsifier(
    members: list[MemberUrlEvidence],
    *,
    min_confidence: float = 0.5,
    execution_mode: str = "SHADOW_DRY_RUN",
) -> FalsifierVerdict:
    """ "서로 다른 PSL 등록도메인으로 확정되면 SPLIT" falsifier 를 검정한다.

    이 함수는 `web_target_group.parquet` 의 세 후보(coupang/gmarket/naver) 가 공통으로
    쓰는 falsifier 형태를 일반화한 것이다 — "RETAIL entity 랜딩이 APP entity 와 **다른
    경로**로 확정되면" 부분(gmarket/naver)의 경로 비교는 이 함수의 범위 밖이며
    (`registered_domain` 은 경로를 보지 않는다), 별도로 사람이 검토해야 한다는 사실을
    `reason` 에 명시한다.

    셋 이상 멤버는 아직 실재하지 않지만(현재 그룹은 전부 member_count in {1,2}),
    함수는 `member_count >= 2` 일반형으로 만든다 — 미래에 3+ 멤버 그룹이 생겨도
    코드를 다시 쓰지 않게 한다.
    """
    if len(members) < 2:
        raise TargetGroupingError(
            f"falsifier 검정은 member_count >= 2 그룹에만 의미가 있다 (받은 수: {len(members)})"
        )

    undetermined = [m for m in members if not m.official_landing_url]
    if undetermined:
        ids = ", ".join(m.measurement_entity_id for m in undetermined)
        return FalsifierVerdict(
            grouping_status="CANDIDATE_PENDING_URL_REVIEW",
            reason=f"official_landing_url 미확정 구성원이 있다: {ids}. URL 확정 전에는 검정할 수 없다.",
            member_registered_domains={m.measurement_entity_id: None for m in members},
            execution_mode=execution_mode,
        )

    low_confidence = [m for m in members if (m.url_confidence or 0.0) < min_confidence]
    if low_confidence:
        ids = ", ".join(m.measurement_entity_id for m in low_confidence)
        return FalsifierVerdict(
            grouping_status="CANDIDATE_PENDING_URL_REVIEW",
            reason=(
                f"url_confidence < {min_confidence} 인 구성원이 있다: {ids}. "
                "낮은 신뢰도의 URL 로 SPLIT/CONFIRM 을 확정하지 않는다."
            ),
            member_registered_domains={m.measurement_entity_id: None for m in members},
            execution_mode=execution_mode,
        )

    domains: dict[str, str | None] = {}
    for m in members:
        url = m.official_landing_url
        assert url is not None  # undetermined 필터를 이미 통과했다
        domains[m.measurement_entity_id] = _try_registered_domain(url)

    distinct = {d for d in domains.values() if d is not None}
    unresolved = [k for k, v in domains.items() if v is None]
    if unresolved:
        return FalsifierVerdict(
            grouping_status="CANDIDATE_PENDING_URL_REVIEW",
            reason=f"등록도메인을 판정할 수 없는 URL 이 있다: {unresolved}",
            member_registered_domains=domains,
            execution_mode=execution_mode,
        )

    if len(distinct) > 1:
        return FalsifierVerdict(
            grouping_status="SPLIT",
            reason=(
                f"구성원 등록도메인이 서로 다르다: {sorted(distinct)}. "
                "falsifier 성립 — 그룹을 SPLIT 한다."
            ),
            member_registered_domains=domains,
            execution_mode=execution_mode,
        )

    return FalsifierVerdict(
        grouping_status="CONFIRMED_SHARED_TARGET",
        reason=(
            f"구성원 전원이 같은 등록도메인({next(iter(distinct))})을 확정했다. "
            "다만 falsifier 원문에 '또는 다른 경로' 가 포함된 그룹(gmarket/naver)은 "
            "경로 수준 동일성을 이 함수가 검정하지 않았으므로 사람 검토가 추가로 필요하다."
        ),
        member_registered_domains=domains,
        execution_mode=execution_mode,
    )


def _try_registered_domain(url: str) -> str | None:
    try:
        return registered_domain(url)
    except RegisteredDomainError:
        return None
