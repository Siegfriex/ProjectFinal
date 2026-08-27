"""P0 산출물 — target 당 self-contained subagent dispatch packet.

목적: A가 REAL pilot5/main45 scope 를 열었을 때, 매번 이 세션의 대화 맥락을 새 subagent 에게
다시 설명하지 않고 이 packet 하나만 넘겨 즉시 병렬 scout worker 를 띄울 수 있게 한다
(DIRECTOR ADDENDUM — ACTIVE SUBAGENT ORCHESTRATION §1/§5 대응).

이 packet 자체는 REAL 실행 허가가 아니다. `real_authorization` 블록은 전부 null 로 비어
있으며, 실제 dispatch 직전에 오케스트레이터(나)가 A 의 release 티켓에서 다음을 채워야
worker 가 fail-closed 를 통과한다:
request_ticket_id / requested_by / execution_scope / manifest_path / manifest_sha256 /
authority_ref / release_ref / real_target_allowed.
"""

from __future__ import annotations

import json
from pathlib import Path

OUT = Path(__file__).resolve().parent

REQUIRED_EVIDENCE_FIELDS = [
    "scout_run_id", "request_ticket_id", "requested_by", "target_id", "family_id", "task_id",
    "endpoint_contract_ref", "endpoint_contract_hash", "timestamp_kst", "requested_url", "final_url",
    "viewport", "device_profile", "state_id", "state_sequence_number",
    "screenshot_path", "screenshot_sha256", "dom_snapshot_path", "dom_snapshot_sha256",
    "ax_snapshot_path", "ax_snapshot_sha256", "probe_path", "probe_sha256",
    "visible_text_excerpt", "control_candidates", "selected_candidate",
    "visible_label", "accessible_name", "accessible_name_source", "role_or_tag",
    "bbox", "normalized_xy", "nav_container", "reveal_direction", "action_token",
    "url_before", "url_after", "dom_hash_before", "dom_hash_after", "ax_hash_before", "ax_hash_after",
    "obstruction_evidence", "guard_safety_decision", "terminal_status",
]

EXPLORATION_PRIORITY = [
    "1. 화면에 명시적으로 보이는 task label",
    "2. icon + text",
    "3. accessibility name이 명확한 icon/control",
    "4. obvious navigation/menu container",
    "5. nested navigation",
    "6. text/AX semantic candidate",
]

TERMINAL_VOCABULARY = [
    "ENDPOINT_REACHED", "AUTH_GATE", "PUBLIC_WEB_UNOBSERVABLE", "APP_REQUIRED",
    "WAF_OR_CHALLENGE", "TIMEOUT", "EVIDENCE_DEFECT", "NO_SAFE_ROUTE_FOUND",
    "CONTRACT_AMBIGUITY", "SAFETY_STOP",
]

ABSOLUTE_FORBIDDEN = [
    "credential_input", "login_submit", "otp_or_identity_verification",
    "captcha_solve_or_bypass", "real_money_transfer", "cart_add",
    "purchase_or_order_or_reservation", "seat_selection", "payment",
    "phone_call_connect", "external_app_launch", "location_permission_grant",
    "real_personal_or_tracking_or_account_or_user_info_input",
    "terms_agreement_or_signup_completion", "account_creation_to_view_results",
]


def main() -> None:
    manifest = json.loads((OUT / "ROUTE_WORK_MANIFEST.json").read_text(encoding="utf-8"))

    packets = {}
    for t in manifest["targets"]:
        tid = t["target_id"]
        packets[tid] = {
            "packet_kind": "E_WORKER_DISPATCH_PACKET",
            "packet_version": "P0.1",
            "authority_status": "AUXILIARY_EXECUTION_EVIDENCE",
            "canonical": False,
            "self_approved": False,
            "note": (
                "이 packet 만으로는 REAL target 을 열 수 없다. real_authorization 블록이 "
                "A 의 release 로 채워지고 fail-closed 검증을 통과해야 실행 가능."
            ),
            "target_contract": {
                "target_id": tid,
                "family_id": t["family_id"],
                "task_family": t["task_family"],
                "service_name": t["service_name"],
                "official_entry_url": t["official_entry_url"],
                "matched_task": t["matched_task"],
                "task_instruction": t["task_instruction"],
                "fixed_fixture": t["fixed_fixture"],
                "fixture_override": t["fixture_override"],
                "endpoint_contract": t["endpoint_contract"],
                "e_working_task_contract_hash": t["e_working_task_contract_hash"],
                "e_working_endpoint_contract_hash": t["e_working_endpoint_contract_hash"],
            },
            "forbidden_actions": {
                "absolute_global": ABSOLUTE_FORBIDDEN,
                "family_specific": t["forbidden_actions"]["family_specific"],
            },
            "exploration_priority": EXPLORATION_PRIORITY,
            "terminal_vocabulary": TERMINAL_VOCABULARY,
            "required_evidence_fields_per_state": REQUIRED_EVIDENCE_FIELDS,
            "output_contract": {
                "trace": f"E_SCOUT_TRACE_{tid}.jsonl",
                "route_candidate": f"E_ROUTE_CANDIDATE_{tid}.json",
                "summary": f"E_SCOUT_SUMMARY_{tid}.md",
                "evidence_root": f"artifacts/pathfinder_e/<scout_run_id>/{tid}/",
                "append_only": True,
            },
            "hard_rules": [
                "task/endpoint/family/target 를 화면에서 추론하거나 재정의하지 않는다.",
                "candidate ranking 은 결과를 보고 바꾸지 않는다 — 모든 attempted branch 기록.",
                "endpoint 충족 최초 상태에서 정지. 이후 조작 없음.",
                "generic login 존재만으로 중단하지 않음 — task path 상 인증 불가피 시점에만 AUTH_GATE.",
                "route 를 보고 target/endpoint/task/family 교체를 제안하지 않는다 (쉽다/어렵다는 eligibility 아님).",
                "이 target 의 scout 는 E_SCOUT::<target_id>::<task_contract_hash> namespace 로 exactly-once.",
            ],
            "real_authorization": {
                "request_ticket_id": None,
                "requested_by": None,
                "execution_scope": None,
                "manifest_path": None,
                "manifest_sha256": None,
                "authority_ref": None,
                "release_ref": None,
                "real_target_allowed": False,
                "_fail_closed": "위 필드 중 하나라도 None/불일치면 browser 열기 전에 fail-closed.",
            },
        }

    out_path = OUT / "WORKER_DISPATCH_PACKETS.json"
    out_path.write_text(
        json.dumps({"packet_count": len(packets), "targets": packets}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"wrote {len(packets)} packets -> {out_path}")


if __name__ == "__main__":
    main()
