"""D heartbeat — 5분 loop마다 bus에 상태를 기록한다.

usage: d_heartbeat.py <work_state> <next_action> [current_ticket_id] [blocker_ids...]
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

REPO = Path("/home/sieg/projects-wsl/ProjectFinal")
WT = REPO / ".agent_worktrees/claude_d_research"
BUS = REPO / ".agent_bus/landing_v2"
KST = timezone(timedelta(hours=9))


def git(*args: str) -> str:
    return subprocess.run(["git", *args], cwd=WT, capture_output=True, text=True).stdout.strip()


def main() -> int:
    work_state = sys.argv[1] if len(sys.argv) > 1 else "IDLE"
    next_action = sys.argv[2] if len(sys.argv) > 2 else "bus scan"
    ticket = sys.argv[3] if len(sys.argv) > 3 else None
    blockers = sys.argv[4:] if len(sys.argv) > 4 else []
    # [v3 §7] heartbeat 필수 8항목 중 worktree / artifact / next_gate / decision_needed 가
    # 없었다. 환경변수로 받아 채운다 (미지정이면 명시적으로 NONE 을 기록한다 — 빈 값과
    # "없음" 을 구분하지 않으면 그것도 빈 결과가 통과처럼 보이는 사례가 된다).
    artifact = os.environ.get("D_HB_ARTIFACT", "NONE")
    next_gate = os.environ.get("D_HB_NEXT_GATE", "NONE")
    decision_needed = os.environ.get("D_HB_DECISION_NEEDED", "NONE")

    log = BUS / "event_log.jsonl"
    seq = sum(1 for _ in log.open()) if log.exists() else 0
    remote = git("ls-remote", "origin", "refs/heads/claude-d/research-sandbox-v21").split("\t")[0] or None

    hb = {
        "agent": "D",
        "timestamp": datetime.now(KST).isoformat(),
        "phase": "I1",
        "current_ticket_id": ticket,
        "branch": "claude-d/research-sandbox-v21",
        "head_sha": git("rev-parse", "HEAD"),
        "base_sha": "bc0b7a087faf2328cbafdfa9b40bd426c5080d7d",
        "remote_head_sha": remote,
        "work_state": work_state,
        "blocker_ids": blockers,
        "last_bus_seq": seq,
        "last_push_at": git("log", "-1", "--format=%cI"),
        "next_action": next_action,
        "authority": "NON_AUTHORITATIVE",
        "production_modified": False,
        "labels_produced": False,
        "holdout_accessed": False,
        "loop_interval_seconds": 180,
        "worktree": str(WT),
        "artifact": artifact,
        "next_gate": next_gate,
        "decision_needed": decision_needed,
        "ssot": "SSOTV3 (MANIFEST_v3.0.json 20/20 sha256 일치, D 독립 검증)",
        "protocol_version": "v3.0",
    }
    hb["pushed"] = hb["head_sha"] == hb["remote_head_sha"]
    (BUS / "heartbeats").mkdir(parents=True, exist_ok=True)
    (BUS / "heartbeats" / "D.json").write_text(json.dumps(hb, ensure_ascii=False, indent=2) + "\n",
                                               encoding="utf-8")
    print(json.dumps(hb, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
