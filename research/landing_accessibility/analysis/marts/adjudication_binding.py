"""`fact_ai_adjudication` ↔ 실제 `AdjudicationRecord` 바인딩.

목표 1 — 이전 `claude-b/analysis-skeleton`은 P-C의 `ai_review.py`가 이 워크트리에
없어 `fact_ai_adjudication` 스키마를 `01_DATA_SPEC §9` 컬럼 목록만으로 추정했다
(`OPEN_ISSUE`로 남겼다). 이제 `claude-b/integration-current`에 실제 cascade
(`src/landing_accessibility/engine/ai_review.py`)가 들어 있으므로, 이 모듈은

1. 그 실제 `AdjudicationRecord` dataclass를 **import**해서(추정이 아니라) 필드
   목록을 코드로 대조하고,
2. `ReviewCascade.run()`이 돌려주는 `CascadeResult.adjudication`을
   `fact_ai_adjudication` 행(dict)으로 변환하며,
3. `AdjudicationRecord`에 없는 `evidence_package_id`(`EvidencePackage.package_id`,
   호출자만 아는 값)를 별도 인자로 받아 채운다.

`assert_schema_bound()`가 이 바인딩이 드리프트하면(cascade에 새 필드가 생기거나
없어지면) import 시점에 실패하게 한다 — 조용히 구버전 스키마로 남지 않는다.
"""

from __future__ import annotations

from dataclasses import fields
from typing import Any

from .cascade_runtime import AdjudicationRecord
from .schema import FACT_AI_ADJUDICATION, SchemaValidationError

#: `AdjudicationRecord`의 실제 dataclass 필드명 (import된 실물에서 뽑는다 — 손으로
#: 다시 나열하지 않는다. 이 목록 자체가 드리프트 탐지 기준이다).
ADJUDICATION_RECORD_FIELDS: tuple[str, ...] = tuple(f.name for f in fields(AdjudicationRecord))

#: `fact_ai_adjudication`에서 `AdjudicationRecord`에 없는(=호출자가 별도로 채우는)
#: 유일한 컬럼. `01_DATA_SPEC §9`가 조인 키로 요구하지만 dataclass 필드가 아니다.
_CALLER_SUPPLIED_COLUMNS = frozenset({"evidence_package_id"})


def assert_schema_bound() -> None:
    """`fact_ai_adjudication` 컬럼 집합과 `AdjudicationRecord` 필드 집합을 대조한다.

    `AdjudicationRecord`의 모든 필드는 mart 컬럼에 있어야 한다(정보를 버리지
    않는다). mart 컬럼 중 `AdjudicationRecord`에 없는 것은 `_CALLER_SUPPLIED_COLUMNS`
    로 명시적으로 등재된 것만 허용한다 — 새 mart-only 컬럼을 몰래 늘리지 않는다.
    """
    mart_columns = {c.name for c in FACT_AI_ADJUDICATION}
    record_fields = set(ADJUDICATION_RECORD_FIELDS)

    missing_in_mart = record_fields - mart_columns
    if missing_in_mart:
        raise SchemaValidationError(
            f"AdjudicationRecord 필드가 fact_ai_adjudication 컬럼에 없다: {sorted(missing_in_mart)} "
            "— cascade가 실제로 채우는 정보를 mart가 버리게 된다"
        )

    mart_only = mart_columns - record_fields
    unexpected_mart_only = mart_only - _CALLER_SUPPLIED_COLUMNS
    if unexpected_mart_only:
        raise SchemaValidationError(
            f"fact_ai_adjudication에 AdjudicationRecord 밖의 미등재 컬럼이 있다: "
            f"{sorted(unexpected_mart_only)} — _CALLER_SUPPLIED_COLUMNS에 등재하거나 컬럼을 뺀다"
        )


def adjudication_record_to_mart_row(
    record: AdjudicationRecord,
    *,
    evidence_package_id: str | None = None,
) -> dict[str, Any]:
    """실제 `AdjudicationRecord` 한 건을 `fact_ai_adjudication` 행(dict)으로 변환한다.

    `notes`(`list[str]`)는 enum이 아니므로 `"; "` join 문자열로 직렬화한다 — 빈
    리스트는 `None`(값 없음)으로 둔다, 빈 문자열과 "정보 없음"을 섞지 않기 위해서다.
    """
    row: dict[str, Any] = {
        "review_item_id": record.review_item_id,
        "review_task_type": record.review_task_type,
        "evidence_package_id": evidence_package_id,
        "deterministic_label": record.deterministic_label,
        "semantic_model_label": record.semantic_model_label,
        "reviewer_a_label": record.reviewer_a_label,
        "reviewer_b_label": record.reviewer_b_label,
        # 실제 dataclass는 `int | str`(0/1/"NA")이다 — parquet(pyarrow)이 한 컬럼에
        # int와 str이 섞이면 타입 추론에서 죽는다. 마트 전역 BOOL01 관례(문자열
        # "0"/"1")와 맞춰 항상 문자열로 통일한다(값 자체는 바꾸지 않는다).
        "reviewer_agreement": str(record.reviewer_agreement),
        "arbiter_label": record.arbiter_label,
        "evidence_gap": str(record.evidence_gap),
        "impact_level": record.impact_level,
        "review_priority": record.review_priority,
        "final_status": record.final_status,
        "human_required": str(record.human_required),
        "ai_review_status": record.ai_review_status,
        "automation_grade": record.automation_grade,
        "notes": "; ".join(record.notes) if record.notes else None,
    }
    return row


# 모듈 import 시점에 바로 검증한다 — 드리프트를 CI/테스트가 아니라 import 실패로
# 즉시 드러낸다 (mypy/ruff와 별개로, 스키마 자체의 자기 증명).
assert_schema_bound()
