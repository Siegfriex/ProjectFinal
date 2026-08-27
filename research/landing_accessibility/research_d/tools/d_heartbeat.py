"""D heartbeat — 5분 loop마다 bus에 상태를 기록한다.

usage: d_heartbeat.py <work_state> <next_action> [current_ticket_id] [blocker_ids...]
"""
from __future__ import annotations

import json
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
        "loop_interval_seconds": 300,
    }
    hb["pushed"] = hb["head_sha"] == hb["remote_head_sha"]
    (BUS / "heartbeats").mkdir(parents=True, exist_ok=True)
    (BUS / "heartbeats" / "D.json").write_text(json.dumps(hb, ensure_ascii=False, indent=2) + "\n",
                                               encoding="utf-8")
    print(json.dumps(hb, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
