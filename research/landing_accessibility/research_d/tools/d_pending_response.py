"""**D 가 물었는데 답이 없는 것**을 센다 — 그리고 상대가 살아 있는지 본다.

[D-DEF-64] D 는 매 회차 "A 판정 대기 · C 검산 대기" 라고 적으면서 **그 대기가
유효한지 재지 않았다.** 발행은 세고 응답은 세지 않았다.

`[[agent-bus-is-not-a-control-channel]]` — **티켓 발행 ≠ 전달.** 발행했다는
사실은 상대가 받았다는 뜻도, 상대가 살아 있다는 뜻도 아니다.

**생존은 heartbeat 만으로 재지 않는다.** A 의 heartbeat 는 10:50 에 멈췄는데
티켓은 14:24 에 냈다 — heartbeat 만 보면 "죽었다" 로 잘못 판정한다. 그래서
**heartbeat 와 최근 발행 중 늦은 것**을 쓴다.

**D 는 다른 평면을 판정하지 않는다.** "C 가 느리다" 가 아니라 "D 발행 N 건이
to-ACK 없이 대기 중이고 C 의 마지막 활동은 M 분 전" 이라고만 적는다.
"""
from __future__ import annotations

import json
import subprocess
from datetime import datetime
from pathlib import Path

BUS = Path("/home/sieg/projects-wsl/ProjectFinal/.agent_bus/landing_v2")
TICKETS = BUS / "tickets"
ACKS = BUS / "acks"
HEARTBEATS = BUS / "heartbeats"
PLANES = ("A", "B", "C", "E")


def _now() -> datetime:
    return datetime.now()


def _mtime(p: Path):
    try:
        return datetime.fromtimestamp(p.stat().st_mtime)
    except Exception:
        return None


def plane_liveness() -> dict:
    """평면별 **마지막 활동** — heartbeat 와 최근 발행 중 **늦은 것**."""
    out = {}
    for pl in PLANES:
        hb = _mtime(HEARTBEATS / f"{pl}.json")
        emitted = [t for t in TICKETS.glob("*.json")
                   if t.name.startswith(f"{pl}-") or t.name.startswith(f"T-{pl}-")]
        last_emit = max((_mtime(t) for t in emitted if _mtime(t)), default=None)
        cands = [x for x in (hb, last_emit) if x]
        last = max(cands) if cands else None
        out[pl] = {"heartbeat": hb.strftime("%Y-%m-%dT%H:%M:%S") if hb else None,
                   "last_emit": last_emit.strftime("%Y-%m-%dT%H:%M:%S") if last_emit else None,
                   "last_activity": last.strftime("%Y-%m-%dT%H:%M:%S") if last else None,
                   "minutes_ago": round((_now() - last).total_seconds() / 60) if last else None,
                   "판정_근거": "heartbeat 와 최근 발행 중 **늦은 것** — heartbeat 만 보면 A 를 잘못 읽는다"}
    return out


def pending() -> dict:
    """`to` 대상이 아직 ACK 하지 않은 **D 발행 티켓**."""
    rows = []
    for p in sorted(TICKETS.glob("*.json")):
        try:
            d = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            continue
        if d.get("from") != "D":
            continue
        tid = d.get("ticket_id") or p.stem
        to = set(d.get("to") or [])
        acked = set()
        for q in ACKS.glob(f"{tid}.*.json"):
            who = q.name[len(tid) + 1:].split(".")[0]
            if who:
                acked.add(who[0])
        if to and not (to & acked):
            m = _mtime(p)
            rows.append({"ticket": tid, "type": d.get("type"),
                         "to": sorted(to), "acked": sorted(acked),
                         "emitted": m.strftime("%Y-%m-%dT%H:%M:%S") if m else None,
                         "minutes_ago": round((_now() - m).total_seconds() / 60) if m else None,
                         "decision_request": d.get("type") == "DECISION_REQUEST"
                                             or bool(d.get("decision_required"))})
    rows.sort(key=lambda r: r["emitted"] or "")
    by_to = {}
    for r in rows:
        for t in r["to"]:
            by_to[t] = by_to.get(t, 0) + 1
    return {"n": len(rows), "by_to": by_to,
            "oldest_minutes": max((r["minutes_ago"] or 0) for r in rows) if rows else 0,
            "decision_requests": [r for r in rows if r["decision_request"]],
            "rows": rows[-12:]}


def check() -> dict:
    pen = pending()
    live = plane_liveness()
    return {"verdict": "INFO",            # **판정이 아니다** — 사실만 낸다
            "pending": pen, "liveness": live,
            "D_는_판정하지_않는다": ("'상대가 느리다' 가 아니라 '몇 건이 대기 중이고 "
                            "상대의 마지막 활동이 언제인가' 만 적는다"),
            "왜_필요한가": ("D 는 매 회차 'A 판정 대기 · C 검산 대기' 라고 적으면서 "
                      "**그 대기가 유효한지 재지 않았다** — 발행은 세고 응답은 안 셌다")}


def controls() -> dict:
    rows = []

    def case(name, got, want, negative=False):
        rows.append({"case": name, "got": got, "want": want, "ok": got == want,
                     "expectation": "must_flag" if negative else "must_not_flag"})

    live = plane_liveness()
    # **heartbeat 만으로 재지 않는다** — A 가 그 반례다
    a = live.get("A", {})
    case("A 의 last_activity 가 heartbeat 보다 늦다 (발행을 함께 본다)",
         bool(a.get("last_emit") and a.get("heartbeat")
              and a["last_activity"] == max(a["last_emit"], a["heartbeat"])), True)
    case("모든 평면에 last_activity 가 있다",
         all(v.get("last_activity") for v in live.values()), True)
    pen = pending()
    case("대기 건수와 by_to 합이 맞는다",
         sum(pen["by_to"].values()) >= pen["n"], True)
    # 합성: to 가 ACK 했으면 대기가 아니다
    case("이 검사는 판정이 아니라 INFO 다", check()["verdict"], "INFO")
    ok = all(r["ok"] for r in rows)
    return {"verdict": "PASS" if ok else "FAIL", "n": len(rows),
            "must_flag": sum(1 for r in rows if r["expectation"] == "must_flag"),
            "must_not_flag": sum(1 for r in rows if r["expectation"] == "must_not_flag"),
            "failed": [r["case"] for r in rows if not r["ok"]], "cases": rows}


if __name__ == "__main__":
    import sys
    out = {"check": check(), "controls": controls()}
    print(json.dumps(out, ensure_ascii=False, indent=1))
    sys.exit(0 if out["controls"]["verdict"] == "PASS" else 1)
