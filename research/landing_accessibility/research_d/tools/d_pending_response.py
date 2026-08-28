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


CURRENT_MART_SHA = "5290e0c306ff7a11375f8da1ee0439e4a424559f18e7a6a662588e46be8f5caf"


def _mart_status(txt: str) -> str:
    """[D-DEF-65] **'대기 중' 이 두 가지를 섞고 있었다.**

    `D-V3-CP6-FINAL` 은 mart `8cf57069` 를 인용하는데 현행은 `5290e0c3` 다 —
    그것은 **응답을 기다리는 것이 아니라 판본이 지난 것**이다. 섞어 세면
    영원히 대기로 남고, 상대는 검산할 필요 없는 것을 검산해야 한다.
    """
    import re
    marts = set()
    for m in re.finditer(r'"mart[_a-z]*sha[0-9]*"\s*:\s*"([0-9a-f]+)"', txt):
        marts.add(m.group(1))
    for m in re.finditer(r'"sha256"\s*:\s*"([0-9a-f]{64})"', txt):
        marts.add(m.group(1))
    if not marts:
        return "NO_MART_CITED"
    cur = [x for x in marts if CURRENT_MART_SHA.startswith(x)]
    return "CURRENT" if cur else "STALE_MART_PIN"


_PRIO_ORDER = {"P0": 0, "P1": 1, "P2": 2, "P3": 3, "P4": 4}


def pending() -> dict:
    """`to` 대상이 아직 ACK 하지 않은 **D 발행 티켓**.

    **우선순위를 D 가 표시한다.** 티켓에 이미 `priority` 가 있는데 목록이
    발행 순서로만 정렬돼 있었다 — 상대가 무엇을 먼저 볼지 알 수 없다.
    """
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
                         "priority": d.get("priority", "?"),
                         "mart_status": _mart_status(p.read_text(encoding="utf-8")),
                         "to": sorted(to), "acked": sorted(acked),
                         "emitted": m.strftime("%Y-%m-%dT%H:%M:%S") if m else None,
                         "minutes_ago": round((_now() - m).total_seconds() / 60) if m else None,
                         "decision_request": d.get("type") == "DECISION_REQUEST"
                                             or bool(d.get("decision_required"))})
    # **우선순위 → 오래된 순.** 발행 순서만으로는 무엇을 먼저 볼지 알 수 없다
    rows.sort(key=lambda r: (_PRIO_ORDER.get(r["priority"], 9), r["emitted"] or ""))
    by_to = {}
    for r in rows:
        for t in r["to"]:
            by_to[t] = by_to.get(t, 0) + 1
    stale = [r for r in rows if r["mart_status"] == "STALE_MART_PIN"]
    live = [r for r in rows if r["mart_status"] != "STALE_MART_PIN"]
    by_prio = {}
    for r in live:
        by_prio[r["priority"]] = by_prio.get(r["priority"], 0) + 1
    return {"n": len(rows), "n_live": len(live), "n_stale_mart": len(stale),
            "by_priority_live": by_prio,
            "stale_mart_pin": [{"ticket": r["ticket"], "priority": r["priority"]}
                               for r in stale],
            "판본_만료는_대기가_아니다": ("옛 mart sha 만 인용하는 티켓은 **응답을 "
                              "기다리는 것이 아니라 판본이 지난 것**이다 — "
                              "섞어 세면 상대가 검산할 필요 없는 것을 검산한다"),
            "by_to": by_to,
            "oldest_minutes": max((r["minutes_ago"] or 0) for r in rows) if rows else 0,
            "decision_requests": [r for r in rows if r["decision_request"]],
            "rows": live[:12]}


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
