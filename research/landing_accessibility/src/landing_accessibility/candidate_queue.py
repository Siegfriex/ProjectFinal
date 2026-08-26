"""P-B candidate queue — 검토 대기열을 웹 적격성 판정 결과에서 파생한다.

## 왜 별도 모듈인가

오케스트레이터 지시서가 작업 항목으로 준 4개 큐:

    APP_ONLY candidate / SYSTEM_APP candidate / NOT_ELIGIBLE candidate /
    unresolved candidate queue

는 v1(`06`) 어휘(`APP_ONLY`/`SYSTEM_APP`/...)를 연상시키지만, `web_eligibility.py` 가
이미 확정한 대로 v2 `web_eligibility_status` 는 **6값으로 닫혀 있다** (A2 §1.3, 규칙 S-3).
이 4개 큐를 새 저장 상태값으로 만들면 그 결정을 뒤집는 것이 된다.

그래서 이 모듈은 **저장하지 않는 파생 뷰**만 만든다 — `service_master`/`dim_web_target`
에는 여전히 6값만 쓰고, 이 모듈은 순수하게 "검토자가 다음에 무엇부터 볼까" 를 위한
작업 큐 4개로 기존 판정 결과를 재조합한다.

## 4개 큐의 정의

| 큐 | 원천 |
|---|---|
| `app_only_queue` | `web_eligibility_status == EXCLUDED_APP_ONLY` |
| `system_app_queue` | `app_only_queue` 의 부분집합. evidence 중 `PRIOR_HYPOTHESIS` 가 `system_app_hypothesis.json` 계열 패턴(선탑재/시스템 앱)을 언급하는 것 |
| `not_eligible_queue` | `EXCLUDED_NO_PUBLIC_WEB_LANDING` + `EXCLUDED_INDUSTRY_AXIS` |
| `unresolved_queue` | `UNDETERMINED_URL_EVIDENCE` + `NOT_ASSESSED` |

각 큐 내부는 `eligibility_confidence` 오름차순(낮은 신뢰도 먼저 — 검토가 더 필요한
것부터)으로 정렬한다.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from landing_accessibility.web_eligibility import WebEligibilityDetermination

_SYSTEM_APP_PATTERN = re.compile(
    r"system_app_hypothesis|선탑재|시스템\s*앱|os\s*구성요소|preload", re.IGNORECASE
)


@dataclass(frozen=True)
class QueueItem:
    measurement_entity_id: str
    web_eligibility_status: str
    eligibility_confidence: float
    eligibility_needs_review: bool
    eligibility_basis: str


def _is_system_app_flagged(determination: WebEligibilityDetermination) -> bool:
    return any(
        e.evidence_type == "PRIOR_HYPOTHESIS" and _SYSTEM_APP_PATTERN.search(e.detail)
        for e in determination.evidence
    )


def build_candidate_queues(
    entities: list[tuple[str, WebEligibilityDetermination]],
) -> dict[str, list[QueueItem]]:
    """`(measurement_entity_id, determination)` 목록에서 4개 검토 큐를 파생한다.

    한 entity 는 정확히 하나의 큐에만 들어간다(app_only ⊇ system_app 은 예외 —
    system_app 큐는 app_only 큐의 **부분집합 뷰**이지 별도 파티션이 아니다. 그래서
    반환값에서 `system_app_queue` 원소는 `app_only_queue` 에도 함께 나타난다).
    """
    app_only: list[QueueItem] = []
    system_app: list[QueueItem] = []
    not_eligible: list[QueueItem] = []
    unresolved: list[QueueItem] = []

    for entity_id, det in entities:
        item = QueueItem(
            measurement_entity_id=entity_id,
            web_eligibility_status=det.web_eligibility_status,
            eligibility_confidence=det.eligibility_confidence,
            eligibility_needs_review=det.eligibility_needs_review,
            eligibility_basis=det.eligibility_basis,
        )
        if det.web_eligibility_status == "EXCLUDED_APP_ONLY":
            app_only.append(item)
            if _is_system_app_flagged(det):
                system_app.append(item)
        elif det.web_eligibility_status in {
            "EXCLUDED_NO_PUBLIC_WEB_LANDING",
            "EXCLUDED_INDUSTRY_AXIS",
        }:
            not_eligible.append(item)
        elif det.web_eligibility_status in {"UNDETERMINED_URL_EVIDENCE", "NOT_ASSESSED"}:
            unresolved.append(item)
        # ELIGIBLE_WEB 은 어느 검토 큐에도 들지 않는다 — 이미 확정됐다.

    def _sorted(items: list[QueueItem]) -> list[QueueItem]:
        return sorted(items, key=lambda i: (i.eligibility_confidence, i.measurement_entity_id))

    return {
        "app_only_queue": _sorted(app_only),
        "system_app_queue": _sorted(system_app),
        "not_eligible_queue": _sorted(not_eligible),
        "unresolved_queue": _sorted(unresolved),
    }
