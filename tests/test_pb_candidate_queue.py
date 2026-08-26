"""P-B — `candidate_queue.py`. 저장 상태값을 늘리지 않으면서 검토 큐 4종을 파생하는지 검증."""

from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
RESEARCH = REPO / "research" / "landing_accessibility"
sys.path.insert(0, str(RESEARCH / "src"))

from landing_accessibility.candidate_queue import build_candidate_queues  # noqa: E402
from landing_accessibility.web_eligibility import (  # noqa: E402
    UrlEvidenceItem,
    determine_web_eligibility,
)

NOW = "2026-08-27T00:00:00+00:00"


def _det(status: str, evidence: list[UrlEvidenceItem], confidence: float):
    return determine_web_eligibility(
        status=status, basis="test", evidence=evidence, confidence=confidence, reviewer="t"
    )


def test_app_only_goes_to_app_only_queue() -> None:
    det = _det(
        "EXCLUDED_APP_ONLY",
        [UrlEvidenceItem("DOM_INSPECTION", "앱스토어 리다이렉트만 존재", NOW)],
        0.8,
    )
    queues = build_candidate_queues([("svc_a", det)])
    assert [i.measurement_entity_id for i in queues["app_only_queue"]] == ["svc_a"]
    assert queues["system_app_queue"] == []
    assert queues["not_eligible_queue"] == []
    assert queues["unresolved_queue"] == []


def test_system_app_is_subset_of_app_only() -> None:
    det = _det(
        "EXCLUDED_APP_ONLY",
        [
            UrlEvidenceItem("PRIOR_HYPOTHESIS", "system_app_hypothesis.json 선탑재 후보", NOW),
            UrlEvidenceItem("DOM_INSPECTION", "웹 랜딩 없음 확인", NOW),
        ],
        0.7,
    )
    queues = build_candidate_queues([("svc_sys", det)])
    assert [i.measurement_entity_id for i in queues["app_only_queue"]] == ["svc_sys"]
    assert [i.measurement_entity_id for i in queues["system_app_queue"]] == ["svc_sys"]


def test_app_only_without_system_app_marker_not_in_system_queue() -> None:
    det = _det(
        "EXCLUDED_APP_ONLY",
        [UrlEvidenceItem("DOM_INSPECTION", "일반 앱 전용 서비스", NOW)],
        0.7,
    )
    queues = build_candidate_queues([("svc_normal_app", det)])
    assert queues["system_app_queue"] == []


def test_not_eligible_queue_combines_two_statuses() -> None:
    det1 = _det(
        "EXCLUDED_NO_PUBLIC_WEB_LANDING",
        [UrlEvidenceItem("HTTP_PROBE", "접속 확인, 공개 랜딩 없음", NOW)],
        0.6,
    )
    det2 = _det(
        "EXCLUDED_INDUSTRY_AXIS", [UrlEvidenceItem("MANUAL_REVIEW_NOTE", "업종 축", NOW)], 1.0
    )
    queues = build_candidate_queues([("svc_b", det1), ("svc_c", det2)])
    ids = {i.measurement_entity_id for i in queues["not_eligible_queue"]}
    assert ids == {"svc_b", "svc_c"}


def test_unresolved_queue_combines_two_statuses() -> None:
    det1 = _det("UNDETERMINED_URL_EVIDENCE", [UrlEvidenceItem("HTTP_PROBE", "timeout", NOW)], 0.2)
    det2 = _det("NOT_ASSESSED", [], 0.0)
    queues = build_candidate_queues([("svc_d", det1), ("svc_e", det2)])
    ids = {i.measurement_entity_id for i in queues["unresolved_queue"]}
    assert ids == {"svc_d", "svc_e"}


def test_eligible_web_appears_in_no_queue() -> None:
    det = _det(
        "ELIGIBLE_WEB",
        [
            UrlEvidenceItem("HTTP_PROBE", "200", NOW),
            UrlEvidenceItem("SOURCE_LABEL_MATCH", "일치", NOW),
        ],
        0.95,
    )
    queues = build_candidate_queues([("svc_f", det)])
    assert all(len(v) == 0 for v in queues.values())


def test_queues_sorted_by_ascending_confidence() -> None:
    low = _det("NOT_ASSESSED", [], 0.0)
    mid = _det("UNDETERMINED_URL_EVIDENCE", [UrlEvidenceItem("HTTP_PROBE", "x", NOW)], 0.4)
    queues = build_candidate_queues([("svc_high_conf", mid), ("svc_low_conf", low)])
    confidences = [i.eligibility_confidence for i in queues["unresolved_queue"]]
    assert confidences == sorted(confidences)
    assert queues["unresolved_queue"][0].measurement_entity_id == "svc_low_conf"
