"""D 티켓 발행 단일 경로 — 발행 전에 스키마를 강제한다.

D 는 `D-V3-FINDING-012` 를 `base_sha` 없이 발행했다. v3 Δ26 은 v3 이후 발행분에
해석 가능한 `base_sha` 를 요구한다. 그 누락은 **A 의 전수감사(STEP1-024)에 걸리고
나서야** 보였다 — 발행 시점에 아무것도 막지 않았기 때문이다.

여기서 막는다. 검사에 걸리면 파일을 쓰지 않는다.

  base_sha       실재하는 커밋이어야 한다 (`git cat-file -e <sha>^{commit}`)
  to             D 의 substantive finding 은 `to=[C]` 다 (A6/v3 §4)
  claim_kind     판정어가 아니어야 한다 — D 는 GO/NO-GO/BLOCKER/SUPERSEDE 를 내지 않는다
  heredoc 금지    이 모듈은 dict 를 받는다. 셸 heredoc 은 backtick 을 삼킨다(실제로 겪었다)
"""
from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

BUS = Path("/home/sieg/projects-wsl/ProjectFinal/.agent_bus/landing_v2")
FORBIDDEN_TYPES = {"GO", "NO_GO", "NO-GO", "BLOCKER", "DIRECTIVE", "SUPERSEDE"}


def _sh(*a: str) -> str:
    return subprocess.run(a, capture_output=True, text=True).stdout.strip()


def check(t: dict) -> list[str]:
    errs: list[str] = []
    tid = t.get("ticket_id", "")
    if not tid.startswith("D-"):
        errs.append(f"ticket_id 는 D- 로 시작해야 한다: {tid!r}")
    if t.get("from") != "D":
        errs.append(f"from 은 'D' 여야 한다: {t.get('from')!r}")

    bs = t.get("base_sha")
    if not bs:
        errs.append("base_sha 누락 — Δ26")
    elif subprocess.run(["git", "cat-file", "-e", f"{bs}^{{commit}}"],
                        capture_output=True).returncode != 0:
        errs.append(f"base_sha 가 실재 커밋이 아니다: {bs}")

    if t.get("type") in FORBIDDEN_TYPES:
        errs.append(f"D 는 {t['type']} 를 발행하지 않는다 (NON_CANONICAL)")
    to = t.get("to")
    if t.get("type") in {"FINDING", "RESEARCH_FINDING", "VALIDITY_RISK_CANDIDATE"} \
            and to != ["C"]:
        errs.append(f"D 의 substantive finding 은 to=[C] 다 (A6/v3 §4): to={to!r}")
    if "claim_kind" not in t:
        errs.append("claim_kind 누락")
    if not t.get("limitation") and not t.get("known_limitation"):
        errs.append("limitation 누락 — 한계 없는 보고는 발행하지 않는다")
    return errs


def emit(t: dict, *, dry_run: bool = False) -> dict:
    """검사를 통과하면 티켓을 쓰고 event_log 에 append 한다."""
    t = dict(t)
    t.setdefault("from", "D")
    t.setdefault("base_sha", _sh("git", "rev-parse", "HEAD"))
    t.setdefault("created_at_kst", _sh("date", "-Iseconds"))
    t.setdefault("expected_response", "ACK")
    t.setdefault("not_a_verdict", "D 는 NON_CANONICAL. 조치·판정은 A 소관이다.")

    errs = check(t)
    if errs:
        return {"emitted": False, "errors": errs}
    if dry_run:
        return {"emitted": False, "errors": [], "dry_run": True}

    p = BUS / "tickets" / f"{t['ticket_id']}.json"
    if p.exists():
        return {"emitted": False,
                "errors": [f"이미 존재한다. 발행분은 덮어쓰지 않는다: {p.name}"]}
    p.write_text(json.dumps(t, ensure_ascii=False, indent=1), encoding="utf-8")
    sha = hashlib.sha256(p.read_bytes()).hexdigest()
    (BUS / "event_log.jsonl").open("a").write(json.dumps(
        {"ts": t["created_at_kst"], "actor": "D", "event": "EMIT",
         "ticket_id": t["ticket_id"], "to": t.get("to"), "cc": t.get("cc"),
         "ticket_sha256": sha, "base_sha": t["base_sha"]}, ensure_ascii=False) + "\n")
    return {"emitted": True, "path": str(p), "ticket_sha256": sha}


def audit_emitted(v3_since: str = "2026-08-28T02:12") -> dict:
    """D 발행분 전수 — v3 이후 base_sha 해석 여부. 스캐너가 매 회 호출한다."""
    rows = []
    for p in sorted((BUS / "tickets").glob("D-*.json")):
        try:
            d = json.loads(p.read_text(encoding="utf-8"))
        except Exception as e:                      # noqa: BLE001
            rows.append({"file": p.name, "state": "UNPARSED", "error": str(e)})
            continue
        if d.get("from") != "D":
            continue
        ts = d.get("created_at_kst") or d.get("created_at") or ""
        bs = d.get("base_sha")
        if bs is None:
            st = "NO_FIELD"
        elif subprocess.run(["git", "cat-file", "-e", f"{bs}^{{commit}}"],
                            capture_output=True).returncode == 0:
            st = "OK"
        else:
            st = "MISSING"
        rows.append({"file": p.name, "created": ts, "state": st,
                     "v3_era": ts >= v3_since})
    bad = [r for r in rows if r.get("v3_era") and r.get("state") not in ("OK", None)]
    return {"n": len(rows), "v3_era": sum(1 for r in rows if r.get("v3_era")),
            "v3_era_non_resolving": bad,
            "verdict": "PASS" if not bad else "FAIL",
            "pre_v3_not_amended": "소급 개정하지 않는다 (STEP1-024)"}


if __name__ == "__main__":
    print(json.dumps(audit_emitted(), ensure_ascii=False, indent=1))
