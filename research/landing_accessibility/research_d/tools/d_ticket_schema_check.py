"""D 가 발행한 티켓이 **SSOTV3 스키마 정본**을 지키는가.

지시는 줄곧 "v3 스키마(`15_TICKET_PROTOCOL_SCHEMA_v3.0.json`)로 발행한다" 였다.
**한 번도 검증하지 않았다.** v3-era 68건 중 55건이 위반이다 —
`status` 49 · `scope` 30 · enum 밖 `type` 10.

두 겹의 결함이다.

1. **도구가 있는데 쓰지 않았다.** `d_emit_ticket.py` 가 발행 단일 경로인데
   티켓을 손으로 써서 우회했다. 도구가 막아도 **우회 경로가 열려 있으면**
   막지 못한다.
2. **그 도구도 스키마를 읽지 않았다.** docstring 은 "발행 전에 스키마를
   강제한다" 인데 실제로는 손으로 고른 4항목(base_sha·to·claim_kind·heredoc)만
   본다. `scope` 와 `status` 는 필수인데 채우지도 검사하지도 않았다.
   **목록을 손으로 만들면 뒤처진다** — D-DEF-45 와 같은 형태다.

그래서 이 검사는 **정본 파일을 읽는다**. 스키마가 바뀌면 검사도 따라간다.

**소급 수정하지 않는다.** 발행된 티켓은 불변이다 — 사실만 보고한다.
"""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

REPO = Path("/home/sieg/projects-wsl/ProjectFinal")
SCHEMA = REPO / "SSOTV3/15_TICKET_PROTOCOL_SCHEMA_v3.0.json"
TICKETS = REPO / ".agent_bus/landing_v2/tickets"
# [Δ26 / T-A-V3-STEP1-024] v3 규약은 이 시각 이후 발행분에 적용된다.
# **그 전 것에 소급하지 않는다.**
V3_SINCE = "2026-08-28T02:12"


def schema() -> dict:
    return json.loads(SCHEMA.read_text(encoding="utf-8"))


def violations(plane: str = "D", since: str = V3_SINCE, tickets=None) -> list:
    s = schema()
    req, props = s["required"], s["properties"]
    out = []
    items = tickets if tickets is not None else [
        json.loads(p.read_text(encoding="utf-8")) | {"_file": p.name}
        for p in sorted(TICKETS.glob("*.json"))]
    for d in items:
        if d.get("from") != plane:
            continue
        ts = str(d.get("created_at_kst") or d.get("created_at") or "")
        if ts < since:
            continue                     # v3 이전 — 소급하지 않는다
        miss = [k for k in req if k not in d]
        enum_bad = []
        for k, spec in props.items():
            if k in d and "enum" in spec and d[k] not in spec["enum"]:
                enum_bad.append(f"{k}={d[k]!r}")
            if k in d and spec.get("type") == "array" and "enum" in spec.get("items", {}):
                for v in (d[k] or []):
                    if v not in spec["items"]["enum"]:
                        enum_bad.append(f"{k}[]={v!r}")
        if miss or enum_bad:
            out.append({"ticket": d.get("_file") or d.get("ticket_id"),
                        "created_at_kst": ts[:16],
                        "missing_required": miss, "enum_violation": enum_bad})
    return out


def check() -> dict:
    v = violations()
    c = Counter()
    for r in v:
        for k in r["missing_required"]:
            c["missing:" + k] += 1
        for k in r["enum_violation"]:
            c["enum:" + k] += 1
    return {"verdict": "PASS" if not v else "FAIL",
            "schema": str(SCHEMA), "v3_since": V3_SINCE,
            "n_violations": len(v), "by_field": dict(c),
            "violations": v,
            "소급하지_않는다": "v3 이전 발행분은 대상이 아니다. 발행된 티켓은 고치지 않는다 — 사실만 보고한다",
            "type_enum_은_A_소관": ("`ADDENDUM`·`STATUS` 는 스키마 enum 에 없다. "
                                "D 가 쓰지 말아야 할 어휘인지, 스키마가 넓어져야 하는지는 "
                                "**A 가 정한다**. D 는 불일치만 보고한다")}


def controls() -> dict:
    """합성 티켓으로 막는지 본다."""
    rows = []

    def run(name, t, should_fail=True):
        flagged = bool(violations(tickets=[t | {"_file": "SYNTH"}]))
        rows.append({"case": name, "flagged": flagged,
                     "expectation": "must_flag" if should_fail else "must_not_flag",
                     "ok": flagged == should_fail})

    full = {"ticket_id": "D-X-1", "from": "D", "to": ["C"], "type": "FINDING",
            "priority": "P2", "claim_kind": "OBSERVATION",
            "base_sha": "a" * 40, "scope": "x", "status": "OPEN",
            "created_at_kst": "2026-08-28T15:00:00+09:00"}
    run("필수 10항목이 다 있으면 통과", full, should_fail=False)
    run("scope 누락은 막힘", {k: v for k, v in full.items() if k != "scope"})
    run("status 누락은 막힘", {k: v for k, v in full.items() if k != "status"})
    run("enum 밖 type 은 막힘", full | {"type": "ADDENDUM"})
    run("enum 밖 to 는 막힘", full | {"to": ["Z"]})
    run("v3 이전 발행분은 대상 아님 — 소급하지 않는다",
        full | {"created_at_kst": "2026-08-27T23:00:00+09:00", "scope": None} | {},
        should_fail=False)
    # 위 케이스는 scope 가 None 이지만 키는 있다. 키 자체를 지운 판본으로 다시 본다
    old = {k: v for k, v in full.items() if k != "scope"}
    old["created_at_kst"] = "2026-08-27T23:00:00+09:00"
    run("v3 이전 + 필수 누락도 대상 아님", old, should_fail=False)
    run("다른 평면 발행분은 대상 아님",
        {k: v for k, v in full.items() if k != "scope"} | {"from": "B"},
        should_fail=False)

    ok = all(r["ok"] for r in rows)
    return {"verdict": "PASS" if ok else "FAIL", "n": len(rows),
            "must_flag": sum(1 for r in rows if r["expectation"] == "must_flag"),
            "must_not_flag": sum(1 for r in rows if r["expectation"] == "must_not_flag"),
            "cases": rows}


if __name__ == "__main__":
    import sys
    out = {"check": check(), "controls": controls()}
    print(json.dumps(out, ensure_ascii=False, indent=1))
    sys.exit(0 if out["controls"]["verdict"] == "PASS" else 1)
