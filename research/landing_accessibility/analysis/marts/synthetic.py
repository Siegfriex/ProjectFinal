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
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Any

from .schema import (
    AUTOMATION_GRADE,
    ENDPOINT_STATUS_DETAIL,
    INTERACTION_ARCHETYPE,
    INTERRUPT_LABEL,
    OLDER_RELEVANCE,
)

#: `00 §9` KWCAG criterion id 표본 (실제 codebook 전체가 아니라 fixture용 축소 집합).
CRITERION_IDS: tuple[str, ...] = (
    "1.1.1",
    "1.3.1",
    "2.1.1",
    "2.4.7",
    "2.5.1",
    "3.2.2",
)

_CRITERION_RELEVANCE: dict[str, str] = {
    "1.1.1": "VISION",
    "1.3.1": "VISION",
    "2.1.1": "MOTOR",
    "2.4.7": "COGNITIVE_NAVIGATION",
    "2.5.1": "MOTOR",
    "3.2.2": "COGNITIVE_NAVIGATION",
}
assert set(_CRITERION_RELEVANCE.values()) <= set(OLDER_RELEVANCE)


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
            certification_rows.append(_certification_row(web_target_id))
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

            automation_grade = rng.choice(AUTOMATION_GRADE[:-1])  # UNGRADED 제외
            ai_review_required = "1" if automation_grade in ("D_EMBEDDING_TEXT", "E_VLM") else "0"

            review_item_id = f"REVIEW-{observation_id}-{criterion_id}"
            if verdict_state == "UNDETERMINED":
                final_status = "UNDETERMINED"
                # triage로 review 행을 하나 만든다 (A2 §1.8).
                adjudication_rows.append(_triage_adjudication_row(review_item_id, rng))
            elif ai_review_required == "1":
                final_status, adj_row = _reviewed_criterion(review_item_id, verdict_state, rng)
                adjudication_rows.append(adj_row)
            else:
                final_status = verdict_state if verdict_state != "NA" else "NA"

            criterion_rows.append(
                {
                    "observation_id": observation_id,
                    "criterion_id": criterion_id,
                    "older_relevance": _CRITERION_RELEVANCE[criterion_id],
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

        certification_rows.append(_certification_row(web_target_id))

    return SyntheticUniverse(
        fact_landing_observation=landing_rows,
        fact_task_entry=task_entry_rows,
        fact_task_step=task_step_rows,
        fact_interrupt_element=interrupt_rows,
        fact_criterion_result=criterion_rows,
        fact_ai_adjudication=adjudication_rows,
        dim_certification=certification_rows,
    )


def _certification_row(web_target_id: str) -> dict[str, Any]:
    # A2 §1.3 실측 — `ELIGIBLE_WEB` 0건, 유효 인증 0건이 현재 기준선의 알려진 이슈다.
    # EDA-07이 이 무분산을 감지해 descriptive-only로 전환해야 한다 — 여기서 미리 재현한다.
    return {
        "web_target_id": web_target_id,
        "certified_current": "0",
        "certification_number": None,
        "cert_start": None,
        "cert_end": None,
        "target_scope_match": "0",
        "service_identity_match": "0",
        "match_basis": "NOT_ASSESSED_SYNTHETIC",
    }


def _triage_adjudication_row(review_item_id: str, rng: random.Random) -> dict[str, Any]:
    label = rng.choice(["EVIDENCE_INSUFFICIENT_CONFIRMED", "RECOLLECT_RECOMMENDED"])
    return {
        "review_item_id": review_item_id,
        "review_task_type": "CRITERION_UNDETERMINED_TRIAGE",
        "evidence_package_id": f"PKG-{review_item_id}",
        "deterministic_label": None,
        "semantic_model_label": None,
        "reviewer_a_label": label,
        "reviewer_b_label": label,
        "reviewer_agreement": "1",
        "arbiter_label": None,
        "evidence_gap": "1" if label == "EVIDENCE_INSUFFICIENT_CONFIRMED" else "0",
        "impact_level": rng.choice(["HIGH", "MEDIUM", "LOW"]),
        "review_priority": rng.randint(1, 5),
        "final_status": "RESOLVED",
        "human_required": "0",
    }


def _reviewed_criterion(
    review_item_id: str, verdict_state: str, rng: random.Random
) -> tuple[str, dict[str, Any]]:
    """PASS/FAIL 확정을 요구하는 review — 5%는 인간 예산 소진(ABSTAIN)까지 모사한다."""
    agree = rng.random() < 0.8
    if agree:
        reviewer_a_label = reviewer_b_label = verdict_state
        arbiter_label = None
        reviewer_agreement = "1"
        final_status = "RESOLVED"
        human_required = "0"
    else:
        reviewer_a_label = verdict_state
        reviewer_b_label = "FAIL" if verdict_state == "PASS" else "PASS"
        reviewer_agreement = "0"
        if rng.random() < 0.5:
            arbiter_label = verdict_state
            final_status = "RESOLVED"
            human_required = "0"
        else:
            arbiter_label = None
            final_status = "ABSTAIN"
            human_required = "0"

    adj_row = {
        "review_item_id": review_item_id,
        "review_task_type": "CRITERION_VERDICT",
        "evidence_package_id": f"PKG-{review_item_id}",
        "deterministic_label": None,
        "semantic_model_label": None,
        "reviewer_a_label": reviewer_a_label,
        "reviewer_b_label": reviewer_b_label,
        "reviewer_agreement": reviewer_agreement,
        "arbiter_label": arbiter_label,
        "evidence_gap": "0",
        "impact_level": rng.choice(["HIGH", "MEDIUM", "LOW"]),
        "review_priority": rng.randint(1, 5),
        "final_status": final_status,
        "human_required": human_required,
    }
    criterion_final = verdict_state if final_status == "RESOLVED" else "UNDETERMINED"
    return criterion_final, adj_row
