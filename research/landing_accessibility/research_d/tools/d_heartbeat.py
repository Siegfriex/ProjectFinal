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


def _firewall_claim(head: str) -> tuple:
    """`holdout_accessed` 를 **스캐너 결과에서** 읽는다.

    D_PROTOCOL_SNAPSHOT.md:66 — "`holdout_accessed` 는 self-report 하지 않는다.
    `tools/d_input_firewall.py` 의 스캐너 결과로만 기록한다."
    `mlflow_contract.py` 는 그렇게 하고 있었는데 **heartbeat 는 상수 False 를
    쓰고 있었다.** 3분마다 다른 평면에 나가는 안전 주장이 self-tag 였다.

    스캔이 없거나 **현재 HEAD 보다 오래됐으면** `false` 가 아니라 `UNVERIFIED`
    다. 확인하지 않은 것을 확인한 것처럼 적지 않는다.
    """
    import json as _j
    fp = (WT / "research" / "landing_accessibility" / "research_d" / "results"
          / "D_INPUT_FIREWALL_VERIFICATION.json")
    if not fp.exists():
        return "UNVERIFIED_NO_SCAN", {"source": str(fp), "why": "스캔 산출이 없다"}
    try:
        d = _j.loads(fp.read_text(encoding="utf-8"))
    except Exception as e:                                  # noqa: BLE001
        return "UNVERIFIED_UNREADABLE", {"source": str(fp), "why": str(e)}
    scan_head = d.get("d_head_sha")
    fresh = scan_head == head
    ev = {"source": "results/D_INPUT_FIREWALL_VERIFICATION.json",
          "verdict": d.get("verdict"),
          "checked_at_kst": d.get("checked_at_kst"),
          "scanned_files": d.get("scanned_files"),
          "scanned_corpus_sha256": d.get("scanned_corpus_sha256"),
          "scan_head_sha": scan_head, "current_head_sha": head,
          "fresh_for_current_head": fresh,
          "rule": "D_PROTOCOL_SNAPSHOT.md:66 — self-report 금지, 스캐너 결과로만"}
    if not fresh:
        return "UNVERIFIED_STALE", ev
    if d.get("verdict") == "PASS":
        return False, ev
    return "UNVERIFIED_SCAN_NOT_PASS", ev


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
        # 이 둘은 아직 **자기선언**이다. 어느 것이 측정이고 어느 것이 선언인지
        # 읽는 쪽이 구분할 수 있어야 한다 — `claim_provenance` 에 적는다.
        "production_modified": False,
        "labels_produced": False,
        # [시정] 상수가 아니라 스캐너 결과에서 읽는다 — 아래 main 에서 채운다.
        "holdout_accessed": None,
        "loop_interval_seconds": 180,
        "worktree": str(WT),
        "artifact": artifact,
        "next_gate": next_gate,
        "decision_needed": decision_needed,
        "ssot": "SSOTV3 (MANIFEST_v3.0.json 20/20 sha256 일치, D 독립 검증)",
        "protocol_version": "v3.0",
    }
    ha, ev = _firewall_claim(hb["head_sha"])
    hb["holdout_accessed"] = ha
    hb["holdout_accessed_evidence"] = ev
    hb["claim_provenance"] = {
        "holdout_accessed": "MEASURED — d_input_firewall 스캔 결과",
        "production_modified": "SELF_DECLARED — 아직 측정으로 뒷받침되지 않는다",
        "labels_produced": "SELF_DECLARED — 아직 측정으로 뒷받침되지 않는다",
        "pushed": "MEASURED — git ls-remote 비교",
    }
    # `pushed` 도 '확인 못 했다' 와 '안 밀었다' 를 가른다. ls-remote 가 실패하면
    # remote 가 None 이 되고 예전에는 그것이 pushed=False 로 나갔다 — A 가
    # STEP1-034 에서 판정한 형태(미실행과 실패가 같은 출력)와 같다.
    if hb["remote_head_sha"] is None:
        hb["pushed"] = "UNVERIFIED_REMOTE_UNREADABLE"
        hb["claim_provenance"]["pushed"] = "UNVERIFIED — ls-remote 를 읽지 못했다"
    else:
        hb["pushed"] = hb["head_sha"] == hb["remote_head_sha"]
    (BUS / "heartbeats").mkdir(parents=True, exist_ok=True)
    (BUS / "heartbeats" / "D.json").write_text(json.dumps(hb, ensure_ascii=False, indent=2) + "\n",
                                               encoding="utf-8")
    print(json.dumps(hb, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
