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
    # [시정 2] 경로 접두사 + **파일명 제외목록**으로 신선도를 재던 것이 틀렸다.
    # 제외목록은 휴리스틱이라 새 산출이 생길 때마다 뒤처지고, 실제로
    # D_EMITTED_TICKET_INTEGRITY.json 을 커밋한 직후 **정상 상태가 STALE** 로 났다.
    # 안전 주장 필드가 멀쩡한 상태에서 UNVERIFIED 를 내면 읽는 쪽이 무시하게 된다.
    # 신선도는 **스캔이 잰 코퍼스의 바이트 신원을 재계산해 기록값과 비교**한다 (R38/R56).
    # 정의상 참이라 제외할 파일 목록이 필요 없다.
    recorded = d.get("freshness_corpus_sha256")
    recomputed, recompute_err = None, None
    try:
        import sys as _s
        _s.path.insert(0, str(Path(__file__).resolve().parent))
        import d_input_firewall as _fw
        recomputed = _fw.freshness_sha()
    except Exception as e:                                  # noqa: BLE001
        recompute_err = f"{type(e).__name__}: {e}"
    if recorded is None or recomputed is None:
        fresh = None                       # 판정 불가 — false 로 적지 않는다
    else:
        fresh = (recorded == recomputed)
    ev = {"source": "results/D_INPUT_FIREWALL_VERIFICATION.json",
          "verdict": d.get("verdict"),
          "checked_at_kst": d.get("checked_at_kst"),
          "scanned_files": d.get("scanned_files"),
          "scanned_corpus_sha256": d.get("scanned_corpus_sha256"),
          "scan_head_sha": scan_head, "current_head_sha": head,
          "recorded_freshness_sha256": recorded,
          "recomputed_freshness_sha256": recomputed,
          "recompute_error": recompute_err,
          "fresh_for_current_head": fresh,
          "freshness_rule": ("스캔이 기록한 코퍼스 sha 를 **재계산해 일치하면** 신선하다. "
                             "HEAD 동일성은 스캔 산출을 커밋하는 순간 거짓 STALE 을 내고, "
                             "파일명 제외목록은 새 산출이 생길 때마다 뒤처진다."),
          "freshness_method": "d_input_firewall.freshness_sha() 재계산 — 코퍼스에서 스캔 자신의 산출만 제외 (자기참조)",
          "rule": "D_PROTOCOL_SNAPSHOT.md:66 — self-report 금지, 스캐너 결과로만"}
    if fresh is None:
        return "UNVERIFIED_CORPUS_UNCOMPARABLE", ev
    if not fresh:
        return "UNVERIFIED_STALE", ev
    if d.get("verdict") == "PASS":
        return False, ev
    return "UNVERIFIED_SCAN_NOT_PASS", ev


def _production_touch(base: str, head: str) -> tuple:
    """`production_modified` 를 **git 에서 잰다.**

    A 의 R41 — "안전·상태 주장 필드는 상수일 수 없다. 측정기가 내고
    must_flag/must_not_flag 를 가지며 **측정 가능한 범위를 함께 적는다**."

    D 가 잴 수 있는 것은 **D 브랜치의 커밋이 production 경로를 건드렸는가**
    이지 '아무도 production 을 고치지 않았다' 가 아니다. A 가 자기 어휘를
    `REAL_TARGET 누적 0건` → `A_발행_REAL_허가: 없음` 으로 바꾼 것과 같다.
    """
    PROD = ("research/landing_accessibility/src/",  # FIREWALL_GUARD_DEFINITION
            "research/landing_accessibility/control/",  # FIREWALL_GUARD_DEFINITION
            "research/landing_accessibility/engine/",  # FIREWALL_GUARD_DEFINITION
            "engine/", "v3_runner/",
            "research/landing_accessibility/shadow/")  # FIREWALL_GUARD_DEFINITION
    files = git("diff", "--name-only", f"{base}..{head}").splitlines()
    hits = sorted({f for f in files if any(f.startswith(x) or ("/" + x) in f for x in PROD)})
    return bool(hits), {
        "measured": "git diff --name-only base..head 의 경로 접두 검사",
        "scope": "**D 브랜치 커밋이 production 경로를 건드렸는가.** "
                 "'아무도 production 을 고치지 않았다' 는 D 가 잴 수 없다 (R41)",
        "base_sha": base, "head_sha": head,
        "changed_files": len(files), "production_hits": hits[:10],
        "must_flag": "production 경로 접두를 가진 파일이 있으면 true 여야 한다",
        "must_not_flag": "research_d/ · notebooks/d_research/ 만 바뀌면 false",
    }


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
    pm, pm_ev = _production_touch(hb["base_sha"], hb["head_sha"])
    hb["production_modified"] = pm
    hb["production_modified_evidence"] = pm_ev
    hb["claim_provenance"] = {
        "holdout_accessed": "MEASURED — d_input_firewall 스캔 결과",
        "production_modified": "MEASURED — git diff 경로 접두 (R41: 측정 범위는 D 브랜치 커밋)",
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
