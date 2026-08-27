"""P0 offline rehearsal — SYNTHETIC (가짜) 예시로 E 산출물 3종의 스키마 완결성을 검증한다.

이 스크립트는 어떤 네트워크 요청도 하지 않는다. target F1-03(신한은행)을 예시로 쓰지만
모든 DOM/AX/screenshot/bbox 값은 지어낸(SYNTHETIC) placeholder다 — 실제 신한은행 페이지를
관측한 값이 아니다. 목적은 오직 하나: 내 역할(§7 evidence 필드, §8 route output 스키마)이
자체 일관적이고 필드 누락 없이 실제로 채워질 수 있는지 사전 확인.

REAL scout 시작 후에는 이 스크립트를 재사용하지 않는다 — 그때는 실제 Playwright 관측값이
이 자리를 대체한다.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

OUT = Path(__file__).resolve().parent / "synthetic_example"

SCOUT_RUN_ID = "E-SYNTH-P0-REHEARSAL-0001"
TARGET_ID = "F1-03"
FAMILY_ID = "F1"
TASK_ID = "F1-03::개인뱅킹 계좌이체/송금 기능 진입"
ENDPOINT_CONTRACT_HASH_NOTE = "synthetic run 이라 TASK_CONTRACT_INVENTORY.json 의 F1 해시를 그대로 참조"

REQUIRED_STATE_FIELDS = [
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


def fake_hash(label: str) -> str:
    return "synthfake_" + hashlib.sha256(label.encode()).hexdigest()[:16]


def make_state(seq: int, state_id: str, action_token: str | None, terminal: str | None,
                candidates: list[dict], selected: dict | None, nav_container: str,
                reveal: str, url_before: str, url_after: str, visible_excerpt: str) -> dict:
    return {
        "scout_run_id": SCOUT_RUN_ID,
        "request_ticket_id": "SYNTHETIC-NO-REAL-REQUEST",
        "requested_by": "SELF_REHEARSAL_P0",
        "target_id": TARGET_ID,
        "family_id": FAMILY_ID,
        "task_id": TASK_ID,
        "endpoint_contract_ref": "SSOTV3/01_TASK_FAMILY_TARGET_FRAME_v3.0.md#F1",
        "endpoint_contract_hash": "SEE TASK_CONTRACT_INVENTORY.json families.F1.e_working_endpoint_contract_hash",
        "timestamp_kst": f"2026-08-28T02:{30+seq:02d}:00+09:00",
        "requested_url": "https://bank.shinhan.com/",
        "final_url": url_after,
        "viewport": {"width": 390, "height": 844, "unit": "css_px"},
        "device_profile": "mobile_ua_touch_ko-KR_Asia-Seoul",
        "state_id": state_id,
        "state_sequence_number": seq,
        "screenshot_path": f"artifacts/pathfinder_e/{SCOUT_RUN_ID}/{TARGET_ID}/{state_id}.png",
        "screenshot_sha256": fake_hash(f"{state_id}-screenshot"),
        "dom_snapshot_path": f"artifacts/pathfinder_e/{SCOUT_RUN_ID}/{TARGET_ID}/{state_id}.dom.html",
        "dom_snapshot_sha256": fake_hash(f"{state_id}-dom"),
        "ax_snapshot_path": f"artifacts/pathfinder_e/{SCOUT_RUN_ID}/{TARGET_ID}/{state_id}.ax.json",
        "ax_snapshot_sha256": fake_hash(f"{state_id}-ax"),
        "probe_path": f"artifacts/pathfinder_e/{SCOUT_RUN_ID}/{TARGET_ID}/{state_id}.probe.json",
        "probe_sha256": fake_hash(f"{state_id}-probe"),
        "visible_text_excerpt": visible_excerpt,
        "control_candidates": candidates,
        "selected_candidate": selected,
        "visible_label": selected["visible_label"] if selected else None,
        "accessible_name": selected["accessible_name"] if selected else None,
        "accessible_name_source": selected["accessible_name_source"] if selected else None,
        "role_or_tag": selected["role_or_tag"] if selected else None,
        "bbox": selected["bbox"] if selected else None,
        "normalized_xy": selected["normalized_xy"] if selected else None,
        "nav_container": nav_container,
        "reveal_direction": reveal,
        "action_token": action_token,
        "url_before": url_before,
        "url_after": url_after,
        "dom_hash_before": fake_hash(f"{state_id}-dom-before"),
        "dom_hash_after": fake_hash(f"{state_id}-dom-after"),
        "ax_hash_before": fake_hash(f"{state_id}-ax-before"),
        "ax_hash_after": fake_hash(f"{state_id}-ax-after"),
        "obstruction_evidence": {"interrupt_present": False, "dismiss_required_for_task": False},
        "guard_safety_decision": "ALLOWED_SAFE_NAVIGATION",
        "terminal_status": terminal,
    }


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)

    s0 = make_state(
        seq=0, state_id="S0", action_token=None, terminal=None,
        candidates=[
            {"visible_label": "전체메뉴", "accessible_name": "전체메뉴 열기", "accessible_name_source": "ARIA_LABEL",
             "role_or_tag": "button", "bbox": {"x": 340, "y": 20, "w": 32, "h": 32},
             "normalized_xy": {"x_norm": 0.90, "y_norm": 0.024}},
            {"visible_label": "로그인", "accessible_name": "로그인", "accessible_name_source": "VISIBLE_TEXT",
             "role_or_tag": "link", "bbox": {"x": 280, "y": 20, "w": 48, "h": 32},
             "normalized_xy": {"x_norm": 0.74, "y_norm": 0.024}},
        ],
        selected=None, nav_container="NONE", reveal="NONE",
        url_before="https://bank.shinhan.com/", url_after="https://bank.shinhan.com/",
        visible_excerpt="[SYNTHETIC] 신한은행 모바일웹 첫 화면 — 상단 우측 전체메뉴 아이콘, 로그인 링크 관측(가정)",
    )

    sel1 = {"visible_label": "전체메뉴", "accessible_name": "전체메뉴 열기", "accessible_name_source": "ARIA_LABEL",
            "role_or_tag": "button", "bbox": {"x": 340, "y": 20, "w": 32, "h": 32},
            "normalized_xy": {"x_norm": 0.90, "y_norm": 0.024}}
    s1 = make_state(
        seq=1, state_id="S1", action_token="OPEN_GLOBAL_MENU", terminal=None,
        candidates=[sel1], selected=sel1, nav_container="RIGHT_DRAWER", reveal="RIGHT",
        url_before="https://bank.shinhan.com/", url_after="https://bank.shinhan.com/",
        visible_excerpt="[SYNTHETIC] 우측 drawer 펼침 — '이체' 메뉴 항목 관측(가정)",
    )

    sel2 = {"visible_label": "이체", "accessible_name": "이체", "accessible_name_source": "VISIBLE_TEXT",
            "role_or_tag": "menuitem", "bbox": {"x": 200, "y": 180, "w": 190, "h": 44},
            "normalized_xy": {"x_norm": 0.76, "y_norm": 0.213}}
    s2 = make_state(
        seq=2, state_id="S2", action_token="SELECT_FUNCTION", terminal="AUTH_GATE",
        candidates=[sel2], selected=sel2, nav_container="RIGHT_DRAWER", reveal="RIGHT",
        url_before="https://bank.shinhan.com/", url_after="https://bank.shinhan.com/login?redirect=transfer",
        visible_excerpt="[SYNTHETIC] '이체' 선택 후 LOGIN/IDENTITY gate 도달(가정) — 이 상태에서 정지, 이후 조작 없음",
    )

    trace_path = OUT / "E_SCOUT_TRACE_SYNTHETIC-F1-03.jsonl"
    with trace_path.open("w", encoding="utf-8") as f:
        for state in (s0, s1, s2):
            missing = [k for k in REQUIRED_STATE_FIELDS if k not in state]
            assert not missing, f"missing required fields in {state['state_id']}: {missing}"
            f.write(json.dumps(state, ensure_ascii=False) + "\n")

    route_candidate = {
        "SYNTHETIC": True,
        "note": "가짜 데이터 — 실제 신한은행 관측 아님. P0 스키마 리허설 전용.",
        "target_id": TARGET_ID,
        "task_contract_hash": "SEE TASK_CONTRACT_INVENTORY.json families.F1.e_working_task_contract_hash",
        "endpoint_contract_hash": "SEE TASK_CONTRACT_INVENTORY.json families.F1.e_working_endpoint_contract_hash",
        "scout_status": "AUTH_GATE",
        "route": [
            {"action": "OPEN_GLOBAL_MENU", "label": "전체메뉴"},
            {"action": "SELECT_FUNCTION", "label": "이체"},
            {"terminal": "AUTH_GATE"},
        ],
        "task_activation_depth": 2,
        "experienced_extra_steps": 0,
        "reproducibility": "REPLAY_REQUIRED",
        "uncertainty": ["SYNTHETIC 예시이므로 실제 후보 competition 없음 — 진짜 target 은 candidate 여러 개일 수 있음"],
        "forbidden_actions_attempted": 0,
        "trace_ref": str(trace_path.relative_to(OUT.parent.parent.parent.parent)),
    }
    route_path = OUT / "E_ROUTE_CANDIDATE_SYNTHETIC-F1-03.json"
    route_path.write_text(json.dumps(route_candidate, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"OK — {len(REQUIRED_STATE_FIELDS)}/{len(REQUIRED_STATE_FIELDS)} required fields present in all 3 states")
    print(f"wrote: {trace_path}")
    print(f"wrote: {route_path}")


if __name__ == "__main__":
    main()
