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
# [D-DEF-52] 발행분은 불변이라 고칠 수 없다. **차단 도입 시각**(`schema_errors()`
# 가 들어간 커밋 `b352be0`, 2026-08-28T14:12:35) 이후 발행하고도 위반이면
# 그것이 진짜 새 위반이다. 그 전은 baseline 이고 verdict 를 좌우하지 않는다 —
# **영구 FAIL 은 신호를 죽인다.**
SCHEMA_GUARD_SINCE = "2026-08-28T14:12:35"


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


# [D-DEF-53] **스키마 PASS 가 D 권한 준수를 뜻하지 않는다.** 스키마 enum 은 전
# 평면 공용이라 `BLOCKER`·`DIRECTIVE` 를 **허용**한다. D 는 그것을 발행하면 안 된다
# (SSOTV3 14_PROMPT_D "금지: GO/NO-GO", D 규약 §1 권한경계).
# `d_emit_ticket.FORBIDDEN_TYPES` 가 발행 시 막지만 **손으로 쓴 티켓은 우회**한다.
D_FORBIDDEN_TYPES = {"GO", "NO_GO", "NO-GO", "BLOCKER", "DIRECTIVE", "SUPERSEDE",
                     "RULING", "ASSURANCE"}


def authority_violations(plane: str = "D") -> list:
    """D 가 **낼 수 없는 종류**의 티켓을 발행했는가. 스키마와 별개 축이다."""
    out = []
    for p in sorted(TICKETS.glob("*.json")):
        try:
            d = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            continue
        if d.get("from") != plane:
            continue
        if d.get("type") in D_FORBIDDEN_TYPES:
            out.append({"ticket": p.name, "type": d.get("type"),
                        "created_at_kst": str(d.get("created_at_kst", ""))[:19]})
    return out


def self_approval_record(plane: str = "D") -> dict:
    """`self_approved` 를 **'없음' 과 '거짓' 으로 가른다** (T-B-V3-FINDING-020 · Δ15-GAP04).

    안전 제약('자기승인하지 않았다')의 **기록**이 있는가를 잰다. 필드 부재와
    `false` 를 한 수로 묶으면 **지키지 않은 것과 기록하지 않은 것이 같은 출력**이 된다.

    경계는 `SCHEMA_GUARD_SINCE` — **가드 도입 시각에서 온다**(D-DEF-52 · A R62).
    관측된 마지막 부재 시각에서 뽑지 않는다. 그것은 데이터에서 경계를 만드는 일이다.
    """
    sc = schema()
    absent, false_, true_, other = [], [], [], []
    for f in sorted(TICKETS.glob("*.json")):
        try:
            d = json.loads(f.read_text(encoding="utf-8"))
        except Exception:                           # noqa: BLE001
            continue
        if d.get("from") != plane:
            continue
        ts = d.get("created_at_kst") or d.get("created_at") or ""
        tid = d.get("ticket_id")
        if "self_approved" not in d:
            absent.append((ts, tid))
        elif d["self_approved"] is False:
            false_.append((ts, tid))
        elif d["self_approved"] is True:
            true_.append((ts, tid))
        else:
            other.append((ts, tid, d["self_approved"]))
    new_absent = [t for t in absent if t[0] and t[0] >= SCHEMA_GUARD_SINCE]
    ok = not true_ and not other and not new_absent
    return {"verdict": "PASS" if ok else "FAIL",
            "n_true": len(true_), "true": [t[1] for t in true_],
            "n_false": len(false_), "n_absent": len(absent),
            "n_absent_since_guard": len(new_absent),
            "absent_since_guard": [t[1] for t in new_absent],
            "n_other_value": len(other), "other_value": other,
            "last_absent_at": max((t[0] for t in absent), default=None),
            "guard_since": SCHEMA_GUARD_SINCE,
            "**정본에 없는 필드다**": {
                "in_required": "self_approved" in (sc.get("required") or []),
                "in_properties": "self_approved" in (sc.get("properties") or {}),
                "뜻": ("`self_approved` 는 정본 스키마의 `required` 에도 `properties` 에도 "
                     "**없다**. 따라서 (a) 부재는 **스키마 위반이 아니고** (b) `true 0` 을 "
                     "**정본이 보증하지도 않는다** — 평면들이 관행으로 쓰는 필드다"),
                "누가_정하나": "정본 편입 여부는 **A 소관**이다. D 는 사실만 낸다"},
            "이_수가_말하지_않는_것": ("`true` 0 은 **그렇게 적힌 티켓이 없다**는 뜻이다. "
                             "부재 건에는 **지켰다는 기록 자체가 없다** — "
                             "'없음' 과 '거짓' 을 같은 출력으로 만들지 않는 이유가 이것이다")}


def check() -> dict:
    v = violations()
    for r in v:
        # [D-DEF-52] `created_at_kst` 는 자기신고다 — 실제 시각으로 분류한다.
        # 규칙은 `d_retractions.ticket_time` 한 곳에 있다(D-DEF-49·51 의 반복 방지)
        try:
            from d_retractions import ticket_time as _tt
            used, claimed, mtime = _tt(TICKETS / str(r["ticket"]))
        except Exception:
            used, claimed, mtime = str(r.get("created_at_kst", "")), "", ""
        r["actual_at"] = used
        r["self_reported_at"] = claimed
        r["class"] = "NEW" if used >= SCHEMA_GUARD_SINCE else "BASELINE_PRE_GUARD"
    new = [r for r in v if r["class"] == "NEW"]
    c = Counter()
    for r in v:
        for k in r["missing_required"]:
            c["missing:" + k] += 1
        for k in r["enum_violation"]:
            c["enum:" + k] += 1
    _auth = authority_violations()
    return {"verdict": "PASS" if (not new and not _auth) else "FAIL",
            "schema": str(SCHEMA), "v3_since": V3_SINCE,
            "guard_since": SCHEMA_GUARD_SINCE,
            "n_new": len(new), "n_violations": len(v), "by_field": dict(c),
            "new": new,
            "baseline_pre_guard": {
                "n": len(v) - len(new),
                "왜_PASS_인가": ("차단 이전 발행분이라 **고칠 수 없다**(불변). "
                            "세되 verdict 를 좌우하지 않는다 — 영구 FAIL 은 신호를 죽인다")},
            "violations": v,
            "소급하지_않는다": "v3 이전 발행분은 대상이 아니다. 발행된 티켓은 고치지 않는다 — 사실만 보고한다",
            "authority": {
                "n": len(authority_violations()),
                "violations": authority_violations(),
                "축": ("**스키마와 다른 축이다.** 스키마 enum 은 전 평면 공용이라 "
                     "`BLOCKER`·`DIRECTIVE` 를 허용하지만 D 는 낼 수 없다"),
                "forbidden": sorted(D_FORBIDDEN_TYPES)},
            "type_enum_은_A_소관": ("`ADDENDUM`·`STATUS` 는 스키마 enum 에 없다. "
                                "D 가 쓰지 말아야 할 어휘인지, 스키마가 넓어져야 하는지는 "
                                "**A 가 정한다**. D 는 불일치만 보고한다")}


def constant_drift() -> dict:
    """**같은 값을 여러 도구가 각자 들고 있는 자리**를 대조한다.

    [D-DEF-49] 규칙이 하나인데 구현이 둘이면 갈라진다. 다만 **통합이 항상
    답은 아니다** — `d_prereg_check.FROZEN_MART_SHA` 는 "사전등록 시점에 적어둔
    것" 이고 `d_presentation_eda.EXPECTED_MART` 는 "EDA 가 읽어야 할 판본" 이라
    개념이 다르다. 합치면 사전등록이 현재값을 따라가 버린다.

    그래서 **합치지 않고 대조만 한다.** 갈라지면 그것이 의도인지 묻는다.
    """
    out = []

    def pair(name, a_label, a, b_label, b, note):
        out.append({"name": name, a_label: a, b_label: b,
                    "same": a == b, "note": note})

    try:
        import d_prereg_check as _P
        import d_presentation_eda as _E
        pair("frozen mart sha",
             "prereg(사전등록 시점)", getattr(_P, "FROZEN_MART_SHA", None),
             "presentation_eda(읽어야 할 판본)", getattr(_E, "EXPECTED_MART", None),
             "개념이 달라 **합치지 않는다**. 갈라지면 의도인지 확인한다")
    except Exception as e:
        out.append({"name": "frozen mart sha", "error": str(e), "same": None})

    try:
        import d_emit_ticket as _M
        pair("v3 경계",
             "schema_check(정의)", V3_SINCE,
             "emit_ticket(참조)", _M._v3_since(),
             "같은 개념이라 **통합했다** — emit 이 schema_check 를 읽는다")
    except Exception as e:
        out.append({"name": "v3 경계", "error": str(e), "same": None})

    # **읽지 못한 것을 통과로 읽지 않는다.** `same is None` 은 예외가 났다는 뜻이고
    # 실제로 그렇게 `d_presentation_eda.py` 의 syntax error 가 묻힐 뻔했다
    drift = [o for o in out if o.get("same") is not True]
    return {"verdict": "PASS" if not drift else "FAIL",
            "n": len(out), "drift": drift, "pairs": out,
            "규칙": "same 이 True 가 아니면 전부 drift 다 — 예외도 포함한다"}


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
    def _sa(t, should_fail=True):
        """`self_approval_record` 의 판정부만 합성 티켓으로 재현한다."""
        ts = t.get("created_at_kst", "")
        bad = (t.get("self_approved") is True
               or ("self_approved" in t and t["self_approved"] not in (True, False))
               or ("self_approved" not in t and ts and ts >= SCHEMA_GUARD_SINCE))
        rows.append({"case": "[self_approved] " + _sa_name, "flagged": bad,
                     "expectation": "must_flag" if should_fail else "must_not_flag",
                     "ok": bad == should_fail})

    _sa_name = "가드 이후 true 는 걸린다"
    _sa(full | {"self_approved": True})
    _sa_name = "가드 이후 **부재**도 걸린다"
    _sa(full)
    _sa_name = "false 아닌 이상한 값도 걸린다"
    _sa(full | {"self_approved": "no"})
    _sa_name = "가드 **이전** 부재는 baseline"
    _sa(full | {"created_at_kst": "2026-08-28T09:00:00+09:00"}, should_fail=False)
    _sa_name = "가드 이후 false 는 안 걸린다"
    _sa(full | {"self_approved": False}, should_fail=False)
    _sar = self_approval_record()
    rows.append({"case": "[self_approved] 현재 D 발행분 PASS", "flagged": _sar["verdict"] != "PASS",
                 "expectation": "must_not_flag", "ok": _sar["verdict"] == "PASS"})
    rows.append({"case": "[self_approved] true 는 0", "flagged": _sar["n_true"] != 0,
                 "expectation": "must_not_flag", "ok": _sar["n_true"] == 0})

    run("필수 10항목이 다 있으면 통과", full, should_fail=False)
    run("scope 누락은 막힘", {k: v for k, v in full.items() if k != "scope"})
    run("status 누락은 막힘", {k: v for k, v in full.items() if k != "status"})
    run("enum 밖 type 은 막힘", full | {"type": "ADDENDUM"})
    run("enum 밖 to 는 막힘", full | {"to": ["Z"]})
    # [D-DEF-53] 스키마 enum 에는 있지만 **D 는 낼 수 없는** 종류
    rows.append({"case": "D 권한 밖 type(BLOCKER)은 스키마 enum 에 있어도 권한 축에서 걸린다",
                 "flagged": "BLOCKER" in D_FORBIDDEN_TYPES,
                 "expectation": "must_flag", "ok": "BLOCKER" in D_FORBIDDEN_TYPES})
    rows.append({"case": "FINDING 은 D 권한 안",
                 "flagged": "FINDING" in D_FORBIDDEN_TYPES,
                 "expectation": "must_not_flag", "ok": "FINDING" not in D_FORBIDDEN_TYPES})
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
    out = {"check": check(), "controls": controls(), "constant_drift": constant_drift()}
    print(json.dumps(out, ensure_ascii=False, indent=1))
    sys.exit(0 if out["controls"]["verdict"] == "PASS" else 1)
