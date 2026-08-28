"""완료된 target 의 raw route-candidate 를 읽어 DISPATCH_LEDGER.jsonl / EVIDENCE_MANIFEST.jsonl 에
append 한다. TBX-011 스키마 계약을 그대로 따른다. append-only, 해시체인.
"""
from __future__ import annotations

import hashlib
import json
import sys
import time
from pathlib import Path

RAW_ROOT = Path("/home/sieg/projects-wsl/ProjectFinal/artifacts/v3_census/raw")
DISPATCH_LEDGER = RAW_ROOT / "DISPATCH_LEDGER.jsonl"
EVIDENCE_MANIFEST = RAW_ROOT / "EVIDENCE_MANIFEST.jsonl"
PACKETS_PATH = Path(
    "/home/sieg/projects-wsl/ProjectFinal/.agent_worktrees/claude_e_pathfinder/"
    "research/landing_accessibility/pathfinder_e/bootstrap/WORKER_DISPATCH_PACKETS_V2.json"
)
E_RAW = RAW_ROOT / "E"

STATUS_MAP = {
    "ENDPOINT_REACHED": ("ENDPOINT_REACHED", "ENDPOINT_REACHED"),
    "AUTH_GATE": ("TERMINAL_NO_ENDPOINT", "AUTH_GATE"),
    "NO_SAFE_ROUTE_FOUND": ("TERMINAL_NO_ENDPOINT", "NO_SAFE_ROUTE"),
    "TIMEOUT": ("TERMINAL_NO_ENDPOINT", "TIMEOUT"),
    "WAF_OR_CHALLENGE": ("TERMINAL_NO_ENDPOINT", "WAF"),
    "APP_REQUIRED": ("TERMINAL_NO_ENDPOINT", "APP_REQUIRED"),
    "PUBLIC_WEB_UNOBSERVABLE": ("TERMINAL_NO_ENDPOINT", "PUBLIC_WEB_UNOBSERVABLE"),
    "SAFETY_STOP": ("ERROR", "FORBIDDEN_ACTION_BOUNDARY"),
    "EVIDENCE_DEFECT": ("ERROR", "NO_SAFE_ROUTE"),
}


def sha256_text(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def sha256_file(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest() if p.exists() else "MISSING"


def last_hash(path: Path) -> str | None:
    if not path.exists():
        return None
    last = None
    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                last = json.loads(line)
    return last.get("evidence_hash") if last else None


def main():
    scout_run_id = sys.argv[1]
    target_ids = sys.argv[2:]
    packets = json.loads(PACKETS_PATH.read_text(encoding="utf-8"))["targets"]

    RAW_ROOT.mkdir(parents=True, exist_ok=True)
    prev = last_hash(EVIDENCE_MANIFEST)

    with DISPATCH_LEDGER.open("a", encoding="utf-8") as dl, EVIDENCE_MANIFEST.open("a", encoding="utf-8") as em:
        for tid in target_ids:
            packet = packets.get(tid)
            if packet is None:
                print(f"SKIP {tid}: not in packets")
                continue
            tc = packet["target_contract"]
            target_dir = E_RAW / scout_run_id / tid
            rc_path = target_dir / f"E_ROUTE_CANDIDATE_{tid}.json"
            trace_path = target_dir / f"E_SCOUT_TRACE_{tid}.jsonl"
            now = time.strftime("%Y-%m-%dT%H:%M:%S+09:00", time.localtime())

            dispatch_rec = {
                "target_id": tid, "family_id": tc["family_id"], "service": tc["service_name"],
                "worker_id": "E-direct-01",
                "idempotency_key": f"E_SCOUT::{tid}::{tc['e_working_task_contract_hash']}::{scout_run_id}",
                "dispatched_at_kst": now, "scout_run_id": scout_run_id,
            }
            dl.write(json.dumps(dispatch_rec, ensure_ascii=False) + "\n")
            dl.flush()

            if not rc_path.exists():
                print(f"NO_RESULT_YET {tid} — dispatch logged, evidence pending")
                continue

            rc = json.loads(rc_path.read_text(encoding="utf-8"))
            scout_status = rc.get("scout_status") or "EVIDENCE_DEFECT"
            attempt_status, terminal_reason = STATUS_MAP.get(scout_status, ("ERROR", "NO_SAFE_ROUTE"))
            route_diagnosis = rc.get("route_diagnosis")
            error_sample = None
            for step in rc.get("route", []):
                if "error" in step:
                    error_sample = str(step["error"])[:200]

            # 라벨: route 에서 마지막 SELECT_FUNCTION 액션의 label
            visible_label = None
            for r in rc.get("route", []):
                if r.get("action"):
                    visible_label = r.get("label")

            task_hash = sha256_text(f"{tid}|{tc['frozen_task']}|{tc['endpoint_contract']}")
            endpoint_hash = sha256_text(tc["endpoint_contract"])
            evidence_hash = sha256_file(trace_path) if trace_path.exists() else sha256_text(json.dumps(rc, sort_keys=True))

            record = {
                "target_id": tid, "family_id": tc["family_id"], "service": tc["service_name"],
                "worker_id": "E-direct-01", "idempotency_key": dispatch_rec["idempotency_key"],
                "captured_at_kst": now,
                "evidence_dir": str(target_dir), "evidence_hash": evidence_hash, "prev_hash": prev,
                "task_hash": task_hash, "endpoint_hash": endpoint_hash,
                "attempt_status": attempt_status, "terminal_reason": terminal_reason,
                "scout_status_raw": scout_status, "route_diagnosis": route_diagnosis, "error_sample": error_sample,
                "visible_label_text": visible_label or "NOT_OBSERVED",
                "accessible_name": visible_label or "NOT_OBSERVED",
                "accessible_name_source": "VISIBLE_TEXT" if visible_label else "NOT_OBSERVED",
                "label_relation": "MATCH" if visible_label else "NONE",
                "entry_x_norm": None, "entry_y_norm": None, "entry_zone": "NOT_OBSERVED",
                "entry_control_type": "NOT_OBSERVED", "nav_container_type": "HAMBURGER" if any(
                    r.get("action") == "OPEN_GLOBAL_MENU" for r in rc.get("route", [])
                ) else "NOT_OBSERVED",
                "reveal_direction": "NOT_OBSERVED",
                "menu_dependency": any(r.get("action") == "OPEN_GLOBAL_MENU" for r in rc.get("route", [])),
                "task_flow_sequence": [r.get("action") for r in rc.get("route", []) if r.get("action")],
                "experienced_flow_sequence": [r.get("action") for r in rc.get("route", []) if r.get("action")],
                "activation_depth": rc.get("task_activation_depth", 0),
                "first_visible_scroll_state": "S0",
                "auth_gate_stage": "AT_ENDPOINT" if scout_status == "AUTH_GATE" else "NONE",
                "task_control_occlusion": None,
                "missing_reason": None if visible_label else f"scout_status={scout_status}; no candidate matched frozen task keywords",
                "collector_plane": "E",
            }
            em.write(json.dumps(record, ensure_ascii=False) + "\n")
            em.flush()
            prev = evidence_hash
            print(f"OK {tid}: {attempt_status}/{terminal_reason}")


if __name__ == "__main__":
    main()
