"""대장의 **두 분류**가 서로 맞는가.

[D-DEF-69] 대장은 `two_classes` 로 둘을 나눈다 —
`entries`(escaped, 정정이 필요했던 것)와 `caught_pre_emission`(발행 전에 잡아
나가지 않은 것). 그런데 D 는 최근 회차의 발행-전 포착을 **`entries` 안의
필드**(`발행_전_자체검출`)로만 적고 리스트에 넣지 않았다 — **6건**.

`ordinal_provenance` 는 "서수 주장은 대장에서 나온다. 손으로 세지 않는다"
인데 **그 대장이 실제보다 적었다.**

D-DEF-66(결정을 `decision_required` 가 아니라 본문에)·D-DEF-67(`status` 가
자기신고)과 같은 형태의 세 번째다 — **기계가 읽는 자리가 아니라 본문에 적었다.**
"""
from __future__ import annotations

import json
import re
from pathlib import Path

LEDGER = Path(__file__).resolve().parent.parent / "results" / "D_DEFECT_LEDGER.json"
# [D-DEF-78] 패턴이 한국어 표기만 잡았고 **축 자신의 정본 이름**을 안 잡았다 —
# `caught_pre_emission: true` 를 entry 필드로 쓴 것이 그대로 통과했다.
_PRE = re.compile(r"(발행[_ ]?전|자체검출|caught[_ ]?pre[_ ]?emission|pre[_ ]?emission)",
                  re.IGNORECASE)


def check() -> dict:
    if not LEDGER.exists():
        return {"verdict": "NO_LEDGER", "why": str(LEDGER)}
    d = json.loads(LEDGER.read_text(encoding="utf-8"))
    cpe = d.get("caught_pre_emission") or []
    entries = d.get("entries") or []

    # entries 안에 발행-전 포착을 적은 것
    inner = []
    for e in entries:
        ks = [k for k in e if _PRE.search(str(k))]
        if ks:
            inner.append({"id": e.get("id"), "keys": ks})

    # 그 항목들이 리스트에 반영됐는가 — `from_entry` 로 역참조
    covered = {str(c.get("from_entry")) for c in cpe if c.get("from_entry")}
    missing = [x for x in inner if x["id"] not in covered]

    # 서수 근거: 리스트 항목은 모두 `what` 을 가져야 한다 (entry_shape_control)
    noshape = [i for i, c in enumerate(cpe) if not c.get("what")]

    ok = not missing and not noshape
    return {"verdict": "PASS" if ok else "FAIL",
            "n_entries": len(entries), "n_caught_pre_emission": len(cpe),
            "inner_records": len(inner),
            "not_in_list": missing, "items_without_what": noshape,
            "규칙": ("발행 전에 잡은 것은 `entries` 필드가 아니라 "
                  "**`caught_pre_emission` 리스트**에 들어간다 — 서수가 거기서 나온다(R59)"),
            "escaped_는_왜_안_보나": ("`entries` 는 정의상 escaped 다. `escaped: True` 가 "
                             "전건이고 **정보가 없다** — 판정에 쓰지 않는다")}


def controls() -> dict:
    rows = []

    def case(name, got, want, negative=False):
        rows.append({"case": name, "got": got, "want": want, "ok": got == want,
                     "expectation": "must_flag" if negative else "must_not_flag"})

    def probe(doc):
        cpe = doc.get("caught_pre_emission") or []
        covered = {str(c.get("from_entry")) for c in cpe if c.get("from_entry")}
        inner = [e for e in (doc.get("entries") or [])
                 if any(_PRE.search(str(k)) for k in e)]
        return [e.get("id") for e in inner if e.get("id") not in covered]

    # [D-DEF-78] 축 자신의 정본 이름을 패턴이 잡아야 한다
    case("정본 이름 `caught_pre_emission` 을 잡는다",
         probe({"entries": [{"id": "X", "caught_pre_emission": True}],
                "caught_pre_emission": []}), ["X"], negative=True)
    case("한국어 표기도 그대로 잡는다",
         probe({"entries": [{"id": "X", "발행_전_자체검출": "y"}],
                "caught_pre_emission": []}), ["X"], negative=True)
    case("무관한 필드는 안 잡는다",
         probe({"entries": [{"id": "X", "상태": "FIXED", "시정": "z"}],
                "caught_pre_emission": []}), [])

    case("리스트에 반영된 포착은 안 걸린다",
         probe({"entries": [{"id": "X", "발행_전_자체검출": "y"}],
                "caught_pre_emission": [{"what": "w", "from_entry": "X"}]}), [])
    case("리스트에 없으면 걸린다",
         probe({"entries": [{"id": "X", "발행_전_자체검출": "y"}],
                "caught_pre_emission": []}), ["X"], negative=True)
    case("포착 기록이 없으면 걸리지 않는다",
         probe({"entries": [{"id": "X", "what": "y"}], "caught_pre_emission": []}), [])
    c = check()
    case("현재 대장이 통과한다", c["verdict"], "PASS")
    case("`what` 없는 항목은 서수를 깬다 — 0 이어야 한다",
         len(c.get("items_without_what") or []), 0)

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
