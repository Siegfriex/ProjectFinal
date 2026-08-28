"""P1 — WORKER_DISPATCH_PACKETS 를 v2 manifest(A 권위 소스) + SCOUT_POLICY 로 갱신한다."""

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
    "obstruction_evidence", "guard_safety_decision", "terminal_status", "fixture_input_mode",
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

HARD_STOP_8 = ["wrong_scope", "target_outside_manifest", "forbidden_action", "evidence_overwrite",
               "duplicate_launch", "task_contract_drift", "task_or_outcome_leakage",
               "denominator_corruption"]


def main() -> None:
    manifest = json.loads((OUT / "ROUTE_WORK_MANIFEST_V2.json").read_text(encoding="utf-8"))
    policy = json.loads((OUT / "SCOUT_POLICY.json").read_text(encoding="utf-8"))

    packets = {}
    for t in manifest["targets"]:
        tid = t["target_id"]
        packets[tid] = {
            "packet_kind": "E_WORKER_DISPATCH_PACKET",
            "packet_version": "P1.1",
            "authority_status": "AUXILIARY_EXECUTION_EVIDENCE",
            "canonical": False,
            "self_approved": False,
            "note": (
                "이 packet 만으로는 REAL target 을 열 수 없다. real_authorization 블록이 A 의 release 로 "
                "채워지고 fail-closed 검증을 통과해야 실행 가능. target/task/endpoint 는 A 의 frozen "
                "FINAL_MAIN50_MANIFEST.json(v3.0.2)에서 왔다."
            ),
            "target_contract": {
                "target_id": tid,
                "collection_order": t["collection_order"],
                "family_id": t["family_id"],
                "task_family": t["task_family"],
                "service_name": t["service_name"],
                "stratum": t["stratum"],
                "starting_url": t["starting_url"],
                "frozen_task": t["frozen_task"],
                "task_instruction": t["task_instruction"],
                "fixed_fixture": t["fixed_fixture"],
                "fixture_override": t["fixture_override"],
                "endpoint_contract": t["endpoint_contract"],
                "e_working_task_contract_hash": t["e_working_task_contract_hash"],
                "e_working_endpoint_contract_hash": t["e_working_endpoint_contract_hash"],
                "is_pilot_5": t["is_pilot_5"],
            },
            "forbidden_actions_authoritative": t["forbidden_actions_authoritative"],
            "scout_policy_ref": {
                "file": "research/landing_accessibility/pathfinder_e/bootstrap/SCOUT_POLICY.json",
                "traversal": policy["traversal_policy"]["traversal"],
                "tiebreak_key": policy["traversal_policy"]["tiebreak"]["key"],
                "branching_limit": policy["collection_parameters"]["BRANCHING_LIMIT"]["value"],
                "other_collection_params_status": "PENDING_A_FREEZE — 사용 전 SCOUT_POLICY.json 재확인",
                "activation_depth_note": "18-token IN/OUT/CONDITIONAL 분류는 SCOUT_POLICY.json 참조",
                "fixture_input_mode_values": policy["fixture_input_mode"]["values"],
                "entry_zone_thresholds_summary": "y=1/3->MID, y=2/3->BOTTOM (FC-002 정정 반영됨)",
            },
            "exploration_priority": EXPLORATION_PRIORITY,
            "terminal_vocabulary": TERMINAL_VOCABULARY,
            "hard_stop_vocabulary": HARD_STOP_8,
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
                "route 를 보고 target/endpoint/task/family 교체를 제안하지 않는다.",
                "이 target 의 scout 는 E_SCOUT::<target_id>::<task_contract_hash> namespace 로 exactly-once.",
                "후보 전건 실패를 예외 없이 정상 종료로 읽지 않는다(빈 결과 != 통과).",
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

    out_path = OUT / "WORKER_DISPATCH_PACKETS_V2.json"
    out_path.write_text(
        json.dumps({"packet_count": len(packets), "targets": packets}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"wrote {len(packets)} v2 packets -> {out_path}")


if __name__ == "__main__":
    main()
