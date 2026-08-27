"""synthetic/fixture 데이터 생성기 — **실제 서비스 데이터가 아니다.**

`PHASE_GATES.md §4.2`가 허용하는 "local/synthetic fixture 기반" 산출물이다.
결정적(seed 고정)으로 생성해 테스트가 재현 가능하게 한다.

한 번 호출로 7개 표가 서로 `web_target_id`/`observation_id`/`task_observation_id`/
`review_item_id`로 조인 가능한 **하나의 synthetic universe**를 만든다 — EDA-06
(Joint Profile)처럼 표 사이 조인이 필요한 스크립트를 검증하려면 표들이 따로 놀면
안 되기 때문이다.

`certified_current`는 의도적으로 **전부 0**으로 고정한다. 이것이 EDA-07이 다뤄야
하는 "알려진 이슈"(현재 실측 기준선에 유효 인증이 0건)를 fixture 단계에서부터
재현하기 위해서다 — 오케스트레이터 지시 원문.

**`fact_ai_adjudication` 행은 손으로 지어낸 dict가 아니라 실제 `ReviewCascade`
(`src/landing_accessibility/engine/ai_review.py`)를 `StubReviewer`/`StubArbiter`로
돌려서 만든다** (`_run_cascade_for_criterion`). `claude-b/analysis-skeleton` 시점엔
그 cascade가 이 워크트리에 없어 손으로 스키마를 추정했지만, 이제는 실제 코드
경로를 태워야 목표 1이 요구한 "실제 출력 스키마와 정확히 대조"가 fixture 단계
에서도 증명된다. `HumanFinalQueue`도 전 universe가 **하나만** 공유해
`HUMAN_FINAL_REVIEW_MAX=5` 예산이 실제 운영과 같은 방식으로 소진된다.
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Any

from .adjudication_binding import adjudication_record_to_mart_row
from .cascade_runtime import (
    EvidencePackage,
    HumanFinalQueue,
    ReviewCascade,
    ReviewTaskType,
    StubArbiter,
    StubReviewer,
    TriageLabel,
    VerdictState,
    triage_allowed_labels,
    verdict_allowed_labels,
)
from .schema import (
    AUTOMATION_GRADE,
    ENDPOINT_STATUS_DETAIL,
    INTERACTION_ARCHETYPE,
    INTERRUPT_LABEL,
    OLDER_RELEVANCE,
)

#: fixture용 축소 집합 — **정본 배정표(`LA-ORS-20260827`)에서 그대로 복사한 값**이다.
#:
#: 정본이 동결된 뒤(2026-08-27 12:25 KST) 이 픽스처를 정본에 **정렬**했다. 이전
#: 픽스처(1.1.1/1.3.1/2.1.1/2.4.7/2.5.1/3.2.2 + 임의 도메인 배정)는 정본과
#: 모순됐고 존재하지 않는 id(`2.4.7`)까지 들고 있었다 — 정본 문서 §4가 그 목록을
#: "폐기된 목록, 분모로 쓸 수 없음"으로 명시했다.
#:
#: 구성: Pilot r4에서 적용기회가 확인된 older-relevant 12개 전부 + `OTHER` 4개.
#: older-relevant 12개를 그대로 넣은 이유는 synthetic이 **실제 분모 크기(12 근방)를
#: 재현**해야 분모 로직이 의미 있게 검증되기 때문이다.
#:
#: **그래도 이것은 여전히 픽스처다** — 33개 전수가 아니라 16개 부분집합이며,
#: 실제 데이터의 분모를 정의하지 않는다. 실제 데이터 경로는
#: `analysis/older_relevance_registry.py`가 정본 문서를 sha256 대조해 연다.
CRITERION_IDS: tuple[str, ...] = (
    # older-relevant · pilot_applied ✓ (12개 — 정본 §3의 실증 적용기회 집합)
    "1.3.2",
    "1.4.2",
    "1.4.3",
    "2.1.3",
    "2.4.1",
    "2.4.2",
    "2.4.3",
    "3.2.1",
    "3.2.2",
    "3.3.2",
    "3.3.3",
    "3.3.4",
    # OTHER (4개 — 분모에서 제외되는 축이 실제로 제외되는지 확인하기 위해 섞는다)
    "1.1.1",
    "1.3.1",
    "2.1.1",
    "4.1.1",
)

#: **픽스처용 부분집합이며 정본이 아니다.** 다만 **값은 정본과 일치한다** —
#: 정본 배정표에서 복사했고, `assert_no_mart_drift()`가 이를 기계적으로 검증한다.
#: 정본 전체(33개)는 `older_relevance_registry.load_frozen_canonical()`이 문서에서
#: 직접 파싱한다 — 이 상수를 정본 대용으로 쓰지 않는다.
SYNTHETIC_ONLY_OLDER_RELEVANT_FIXTURE: dict[str, str] = {
    "1.3.2": "COGNITIVE_NAVIGATION",
    "1.4.2": "COGNITIVE_NAVIGATION",
    "1.4.3": "VISION",
    "2.1.3": "MOTOR",
    "2.4.1": "COGNITIVE_NAVIGATION",
    "2.4.2": "COGNITIVE_NAVIGATION",
    "2.4.3": "COGNITIVE_NAVIGATION",
    "3.2.1": "COGNITIVE_NAVIGATION",
    "3.2.2": "COGNITIVE_NAVIGATION",
    "3.3.2": "COGNITIVE_NAVIGATION",
    "3.3.3": "COGNITIVE_NAVIGATION",
    "3.3.4": "COGNITIVE_NAVIGATION",
    "1.1.1": "OTHER",
    "1.3.1": "OTHER",
    "2.1.1": "OTHER",
    "4.1.1": "OTHER",
}
#: 정본 문서 §4가 폐기 선언한 이전 픽스처 목록 — 되살아나지 않게 이름으로 남긴다.
RETIRED_PRE_CANONICAL_FIXTURE_IDS: tuple[str, ...] = (
    "2.4.7",  # KWCAG 2.2에 존재하지 않는 id (WCAG Focus Visible)
    "2.5.1",  # NOT_AUTOMATABLE — 적용기회가 항상 0이라 분모에 기여하지 못한다
)

assert set(SYNTHETIC_ONLY_OLDER_RELEVANT_FIXTURE.values()) <= set(OLDER_RELEVANCE)


@dataclass(frozen=True)
class SyntheticUniverse:
    fact_landing_observation: list[dict[str, Any]]
    fact_task_entry: list[dict[str, Any]]
    fact_task_step: list[dict[str, Any]]
    fact_interrupt_element: list[dict[str, Any]]
    fact_criterion_result: list[dict[str, Any]]
    fact_ai_adjudication: list[dict[str, Any]]
    dim_certification: list[dict[str, Any]]

    def as_dict(self) -> dict[str, list[dict[str, Any]]]:
        return {
            "fact_landing_observation": self.fact_landing_observation,
            "fact_task_entry": self.fact_task_entry,
            "fact_task_step": self.fact_task_step,
            "fact_interrupt_element": self.fact_interrupt_element,
            "fact_criterion_result": self.fact_criterion_result,
            "fact_ai_adjudication": self.fact_ai_adjudication,
            "dim_certification": self.dim_certification,
        }


def generate_synthetic_universe(n_services: int = 24, *, seed: int = 20260827) -> SyntheticUniverse:
    """서로 조인 가능한 7개 표 synthetic 행을 만든다. 결정적(seed 고정)이다."""
    rng = random.Random(seed)
    # 전 universe가 예산 하나를 공유한다 — 실제 운영과 같은 방식 (`HUMAN_FINAL_REVIEW_MAX=5`).
    human_queue = HumanFinalQueue()

    landing_rows: list[dict[str, Any]] = []
    task_entry_rows: list[dict[str, Any]] = []
    task_step_rows: list[dict[str, Any]] = []
    interrupt_rows: list[dict[str, Any]] = []
    criterion_rows: list[dict[str, Any]] = []
    adjudication_rows: list[dict[str, Any]] = []
    certification_rows: list[dict[str, Any]] = []

    for i in range(n_services):
        web_target_id = f"WT-{i:04d}"
        observation_id = f"OBS-{i:04d}"
        archetype = INTERACTION_ARCHETYPE[i % len(INTERACTION_ARCHETYPE)]

        # 약 10%는 수집 실패로 두어 §4.1 evidence completeness 분모/분자 분리를 검증한다.
        measured = rng.random() > 0.1
        measurement_status = (
            "MEASURED" if measured else rng.choice(["FAILED_ACCESS_BLOCKED", "FAILED_PAGE_TIMEOUT"])
        )

        landing_rows.append(
            {
                "observation_id": observation_id,
                "web_target_id": web_target_id,
                "audit_date": "2026-08-27",
                "protocol_version": "v2.0-synthetic",
                "requested_url": None,
                "final_url": None,
                "redirect_count": rng.randint(0, 2),
                "measurement_status": measurement_status,
                "viewport_width": 390,
                "viewport_height": 844,
                "screenshot_path": None,
                "dom_path": None,
                "ax_path": None,
                "probe_path": None,
                "manifest_path": None,
                "primary_action_visible_initial": rng.choice(["0", "1"]),
                "interactive_element_count": rng.randint(5, 60),
                "visible_link_count": rng.randint(3, 40),
                "visible_button_count": rng.randint(1, 15),
                "moving_element_count": rng.randint(0, 3),
                "modal_candidate_count": rng.randint(0, 2),
                "blocking_modal_count": rng.randint(0, 1),
                "max_overlay_coverage": round(rng.uniform(0.0, 0.9), 3),
                "max_primary_action_occlusion": round(rng.uniform(0.0, 0.5), 3),
            }
        )

        # M-1 (A2 §1.2) — 수집 실패 관측은 criterion/task 행을 만들지 않는다.
        if not measured:
            certification_rows.append(_certification_row(web_target_id, rng))
            continue

        # ── fact_task_entry / fact_task_step ──────────────────────────
        task_id = f"TASK-{i:04d}"
        task_observation_id = f"TOBS-{i:04d}"
        via_gate_archetype = archetype in ("FINANCIAL_ACTION_ENTRY", "COMMUNICATION_ENTRY")
        roll = rng.random()
        ned: int | None
        ied: int | None
        mpfed: int | None
        if roll < 0.6:
            endpoint_status = "FUNCTION_ENDPOINT_REACHED"
            endpoint_status_detail = None
            ned, ied = rng.randint(0, 3), rng.randint(0, 4)
            mpfed = ned + ied
            endpoint_reached = "1"
        elif roll < 0.75 and via_gate_archetype:
            # A2 §1.5.1a — 이 두 archetype에서는 gate 자체가 endpoint다.
            endpoint_status = "FUNCTION_ENDPOINT_REACHED"
            endpoint_status_detail = "ENDPOINT_VIA_AUTH_GATE"
            ned, ied = rng.randint(0, 2), rng.randint(0, 2)
            mpfed = ned + ied
            endpoint_reached = "1"
        elif roll < 0.85:
            endpoint_status = "AUTH_GATE_REACHED"
            endpoint_status_detail = None
            ned = ied = mpfed = None
            endpoint_reached = "0"
        else:
            endpoint_status = "UNRESOLVED"
            endpoint_status_detail = rng.choice(
                [d for d in ENDPOINT_STATUS_DETAIL if d != "ENDPOINT_VIA_AUTH_GATE"]
            )
            ned = ied = mpfed = None
            endpoint_reached = "0"

        auth_gate_before_endpoint = (
            "1"
            if (endpoint_status == "AUTH_GATE_REACHED")
            else ("1" if rng.random() < 0.15 else "0")
        )

        task_entry_row = {
            "task_observation_id": task_observation_id,
            "task_id": task_id,
            "web_target_id": web_target_id,
            "interaction_archetype": archetype,
            "endpoint_definition": f"{archetype}-endpoint-def-synthetic",
            "endpoint_status": endpoint_status,
            "NED": ned,
            "IED": ied,
            "MPFED": mpfed,
            "text_input_episode_count": rng.randint(0, 2),
            "scroll_episode_count": rng.randint(0, 3),
            "forced_dismissal_count": rng.randint(0, 1),
            "auth_gate_before_endpoint": auth_gate_before_endpoint,
            "redirect_count": rng.randint(0, 2),
            "endpoint_reached": endpoint_reached,
            "path_manifest_path": None,
            "endpoint_status_detail": endpoint_status_detail,
        }
        task_entry_rows.append(task_entry_row)

        n_steps = rng.randint(1, 4)
        for step_idx in range(n_steps):
            task_step_rows.append(
                {
                    "task_observation_id": task_observation_id,
                    "step_index": step_idx,
                    "state_before_id": f"state-{step_idx}",
                    "control_selector": f"#ctl-{step_idx}",
                    "control_role": rng.choice(["button", "link", "textbox"]),
                    "control_accessible_name": f"synthetic control {step_idx}",
                    "control_visual_text": None,
                    "control_bbox": None,
                    "action_type": rng.choice(["CLICK", "TAP", "TYPE"]),
                    "url_before": None,
                    "url_after": None,
                    "screenshot_before": None,
                    "screenshot_after": None,
                    "modal_encountered": "1" if rng.random() < 0.1 else "0",
                    "auth_gate_detected": "1"
                    if auth_gate_before_endpoint == "1" and step_idx == n_steps - 1
                    else "0",
                    "endpoint_signal_detected": "1"
                    if step_idx == n_steps - 1 and endpoint_reached == "1"
                    else "0",
                }
            )

        # ── fact_interrupt_element (0~2건) ────────────────────────────
        for k in range(rng.randint(0, 2)):
            interrupt_id = f"INT-{i:04d}-{k}"
            classification_status = rng.choice(
                ["DETERMINISTIC", "SEMANTIC_MODEL", "VLM_REVIEWED", "AMBIGUOUS"]
            )
            final_label = (
                None if classification_status == "AMBIGUOUS" else rng.choice(INTERRUPT_LABEL)
            )
            interrupt_rows.append(
                {
                    "observation_id": observation_id,
                    "interrupt_id": interrupt_id,
                    "selector": f"#popup-{k}",
                    "candidate_source": "DOM_HEURISTIC",
                    "interrupt_type": "MODAL",
                    "bbox_x": 0,
                    "bbox_y": 0,
                    "bbox_w": 390,
                    "bbox_h": rng.randint(100, 800),
                    "viewport_intersection_area": round(rng.uniform(0.1, 1.0), 3),
                    "overlay_coverage": round(rng.uniform(0.1, 1.0), 3),
                    "z_index": rng.randint(1, 9999),
                    "position_type": "fixed",
                    "aria_modal": rng.choice(["0", "1"]),
                    "role_dialog": rng.choice(["0", "1"]),
                    "backdrop_detected": rng.choice(["0", "1"]),
                    "body_scroll_lock": rng.choice(["0", "1"]),
                    "blocks_primary_action": rng.choice(["0", "1"]),
                    "primary_action_occlusion": round(rng.uniform(0.0, 1.0), 3),
                    "dismiss_control_exists": rng.choice(["0", "1"]),
                    "dismiss_control_visible": rng.choice(["0", "1"]),
                    "dismiss_control_accessible_name": None,
                    "dismiss_control_width": rng.randint(0, 48),
                    "dismiss_control_height": rng.randint(0, 48),
                    "dismiss_succeeded": rng.choice(["0", "1"]),
                    "classification_status": classification_status,
                    "ai_review_status": "NOT_REQUIRED"
                    if classification_status == "DETERMINISTIC"
                    else rng.choice(["QUEUED", "COMPLETED_AGREED", "COMPLETED_ARBITRATED"]),
                    "final_label": final_label,
                }
            )

        # ── fact_criterion_result (CRITERION_IDS 전부) ────────────────
        for criterion_id in CRITERION_IDS:
            verdict_roll = rng.random()
            if verdict_roll < 0.55:
                verdict_state = "PASS"
            elif verdict_roll < 0.8:
                verdict_state = "FAIL"
            elif verdict_roll < 0.92:
                verdict_state = "UNDETERMINED"
            else:
                verdict_state = "NA"

            applicable = 0 if verdict_state == "NA" else 1
            pass_count = 1 if verdict_state == "PASS" else 0
            fail_count = 1 if verdict_state == "FAIL" else 0
            undetermined_count = 1 if verdict_state == "UNDETERMINED" else 0

            review_item_id = f"REVIEW-{observation_id}-{criterion_id}"
            if verdict_state == "UNDETERMINED":
                # A2 §1.7 — verdict_state=UNDETERMINED은 ai_review_required=1을 강제한다.
                # G-5(automation_grade=UNGRADED ⟺ final_status∈{UNDETERMINED,NA})도 따른다.
                ai_review_required = "1"
                automation_grade = "UNGRADED"
                # 실제 ReviewCascade를 CRITERION_UNDETERMINED_TRIAGE로 돌린다 (A2 §1.8) —
                # T-8이 강제하므로 cascade의 어떤 출력도 final_status를 바꾸지 못한다.
                final_status, adj_row = _run_cascade_for_criterion(
                    review_item_id=review_item_id,
                    observation_id=observation_id,
                    verdict_state=verdict_state,
                    rng=rng,
                    human_queue=human_queue,
                )
                adjudication_rows.append(adj_row)
            elif verdict_state == "NA":
                ai_review_required = "0"
                automation_grade = "UNGRADED"
                final_status = "NA"
            else:
                automation_grade = rng.choice([g for g in AUTOMATION_GRADE if g != "UNGRADED"])
                ai_review_required = (
                    "1" if automation_grade in ("D_EMBEDDING_TEXT", "E_VLM") else "0"
                )
                if ai_review_required == "1":
                    # 실제 ReviewCascade를 CRITERION_VERDICT로 돌린다 — RESOLVED/ABSTAIN/
                    # ESCALATED_HUMAN_FINAL 전부 여기서 나올 수 있다 (00 §9 6단계).
                    final_status, adj_row = _run_cascade_for_criterion(
                        review_item_id=review_item_id,
                        observation_id=observation_id,
                        verdict_state=verdict_state,
                        rng=rng,
                        human_queue=human_queue,
                    )
                    adjudication_rows.append(adj_row)
                else:
                    final_status = verdict_state

            criterion_rows.append(
                {
                    "observation_id": observation_id,
                    "criterion_id": criterion_id,
                    "older_relevance": SYNTHETIC_ONLY_OLDER_RELEVANT_FIXTURE[criterion_id],
                    "applicable_count": applicable,
                    "pass_count": pass_count,
                    "fail_count": fail_count,
                    "undetermined_count": undetermined_count,
                    "verdict_state": verdict_state,
                    "automation_grade": automation_grade,
                    "ai_review_required": ai_review_required,
                    "final_status": final_status,
                }
            )

        certification_rows.append(_certification_row(web_target_id, rng))

    return SyntheticUniverse(
        fact_landing_observation=landing_rows,
        fact_task_entry=task_entry_rows,
        fact_task_step=task_step_rows,
        fact_interrupt_element=interrupt_rows,
        fact_criterion_result=criterion_rows,
        fact_ai_adjudication=adjudication_rows,
        dim_certification=certification_rows,
    )


def _certification_row(web_target_id: str, rng: random.Random) -> dict[str, Any]:
    # A2 §1.3 실측 + Claude A(governor) 확정 — 관측 프레임 실측은 CERTIFIED 0건,
    # NOT_CERTIFIED 55건, UNDETERMINED 13건(총 68건)이다. `certified_current`는
    # 항상 "0"으로 고정한다(무분산 재현, EDA-07이 이를 감지해 descriptive-only로
    # 자동 전환한다) — CERTIFIED가 하나도 없으므로 `certified_current="1"`인 행을
    # synthetic에서도 만들지 않는다(실측을 거짓으로 낙관하지 않는다).
    #
    # NOT_CERTIFIED와 UNDETERMINED는 서로 다른 사실이다(governor 지시) — 대략
    # 55:13 비율(≈81%:19%, UNDETERMINED 중 요건2 불가 10 : 동일성 미해소 3 ≈ 77%:23%)을
    # 결정적으로 재현한다. **원인(만료/애초 미보유/join 기준이 엄격해서 탈락)은
    # 데이터로 구분하지 못한다** — synthetic에서도 그 구분을 만들어내지 않는다.
    if rng.random() < 0.81:
        match_status = "NOT_CERTIFIED"
        undetermined_reason = None
        target_scope_match = "0"
        service_identity_match = "0"
        match_basis = "NOT_CERTIFIED_SYNTHETIC"
    else:
        match_status = "UNDETERMINED"
        if rng.random() < 0.77:
            undetermined_reason = "NO_URL_FOR_REQUIREMENT_2"
            target_scope_match = None  # 요건2 자체를 시험할 URL이 없다 — 0이 아니라 NULL.
            service_identity_match = "0"
        else:
            undetermined_reason = "IDENTITY_UNRESOLVED_DOMAIN_MATCH_NAME_MISMATCH"
            target_scope_match = "1"  # 도메인은 일치(요건2 통과)
            service_identity_match = None  # 서비스명 불일치로 동일성만 미해소.
        match_basis = "UNDETERMINED_SYNTHETIC"

    return {
        "web_target_id": web_target_id,
        "certified_current": "0",
        "certification_number": None,
        "cert_start": None,
        "cert_end": None,
        "target_scope_match": target_scope_match,
        "service_identity_match": service_identity_match,
        "match_basis": match_basis,
        "certification_match_status": match_status,
        "certification_undetermined_reason": undetermined_reason,
    }


def _run_cascade_for_criterion(
    *,
    review_item_id: str,
    observation_id: str,
    verdict_state: str,
    rng: random.Random,
    human_queue: HumanFinalQueue,
) -> tuple[str, dict[str, Any]]:
    """실제 `ReviewCascade`(`StubReviewer`/`StubArbiter`)를 돌려 `fact_ai_adjudication`
    행 하나와 `fact_criterion_result.final_status`를 만든다.

    `verdict_state=UNDETERMINED`면 `CRITERION_UNDETERMINED_TRIAGE`로, 아니면
    `CRITERION_VERDICT`로 돌린다 — cascade 자체의 T-8/G-4 강제(00 §9, A2 §1.11)를
    그대로 태우므로, "UNDETERMINED가 PASS/FAIL로 세탁되는" 경로나
    "사람 예산(HUMAN_FINAL_REVIEW_MAX=5) 초과"는 여기서도 물리적으로 불가능하다
    (`ReviewCascade`/`HumanFinalQueue`가 그 자체로 강제한다).
    """
    is_triage = verdict_state == "UNDETERMINED"
    task_type = (
        ReviewTaskType.CRITERION_UNDETERMINED_TRIAGE
        if is_triage
        else ReviewTaskType.CRITERION_VERDICT
    )
    allowed_labels = triage_allowed_labels() if is_triage else verdict_allowed_labels()
    package = EvidencePackage(
        package_id=f"PKG-{review_item_id}",
        observation_id=observation_id,
        screenshot_crop_relpath=None,
        surrounding_screenshot_relpath=None,
        dom_facts={"synthetic": True},
        ax_facts={"synthetic": True},
        bbox=None,
        relevant_text=None,
        allowed_labels=allowed_labels,
    )

    if is_triage:
        label_a = rng.choice([t.value for t in TriageLabel])
        label_b = (
            label_a
            if rng.random() < 0.8
            else next((t.value for t in TriageLabel if t.value != label_a), label_a)
        )
    else:
        label_a = verdict_state
        label_b = (
            verdict_state if rng.random() < 0.8 else ("FAIL" if verdict_state == "PASS" else "PASS")
        )

    # 소수 사례는 reviewer 자체가 ABSTAIN한다 (evidence gap 재현).
    abstain_a = rng.random() < 0.03
    abstain_b = rng.random() < 0.03
    reviewer_a = StubReviewer(
        reviewer_id="synthetic-A", label=None if abstain_a else label_a, abstain=abstain_a
    )
    reviewer_b = StubReviewer(
        reviewer_id="synthetic-B", label=None if abstain_b else label_b, abstain=abstain_b
    )

    # 불일치 시 절반은 arbiter가 확정하고, 절반은 사람 최종검토로 올린다
    # (예산 5건이 소진되면 `HumanFinalQueue`가 그 자체로 거부한다 — `try_escalate`).
    disagree_escalates = rng.random() < 0.5
    arbiter = StubArbiter(
        arbiter_id="synthetic-arbiter",
        label=None if disagree_escalates else label_a,
        abstain=disagree_escalates,
        escalate_to_human=disagree_escalates,
    )

    cascade = ReviewCascade(
        reviewer_a=reviewer_a, reviewer_b=reviewer_b, arbiter=arbiter, human_queue=human_queue
    )
    result = cascade.run(
        review_item_id=review_item_id,
        review_task_type=task_type,
        verdict_state=VerdictState(verdict_state),
        package=package,
        ai_review_required=1,
    )
    row = adjudication_record_to_mart_row(
        result.adjudication, evidence_package_id=package.package_id
    )
    return result.criterion_final_status, row
