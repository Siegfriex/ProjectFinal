"""대장에 항목을 넣는 **유일한 경로**. [D-DEF-95]

`발행_전_자체검출` 을 `entries` 항목의 **필드**로 쓴 것이 **세 번**이다
(`D-DEF-78` · `D-DEF-85` · `D-DEF-94`). 규칙은 그 축이 필드가 아니라
**`caught_pre_emission` 리스트**라는 것이고(A R59 — 서수가 거기서 나온다),
`d_ledger_shape` 가 매번 잡았다. **잡히는 것으로는 안 고쳐진다** —
쓰는 경로를 하나로 만들어 애초에 못 쓰게 한다.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

LEDGER = Path(__file__).resolve().parents[1] / "results" / "D_DEFECT_LEDGER.json"
_PRE = re.compile(r"(발행[_ ]?전|자체검출|caught[_ ]?pre[_ ]?emission|pre[_ ]?emission)",
                  re.IGNORECASE)


class LedgerError(ValueError):
    pass


def _load() -> dict:
    return json.loads(LEDGER.read_text(encoding="utf-8"))


def _save(d: dict) -> None:
    LEDGER.write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")


def entry_errors(entry: dict) -> list:
    """`entries` 항목으로 쓸 수 있는가."""
    errs = []
    bad = [k for k in entry if _PRE.search(str(k))]
    if bad:
        errs.append(f"`entries` 항목에 발행-전 포착 축을 필드로 쓸 수 없다: {bad} — "
                    f"`add_caught()` 로 **리스트**에 넣어라 [R59]")
    if not entry.get("id"):
        errs.append("`id` 가 없다")
    return errs


def caught_errors(item: dict) -> list:
    """`caught_pre_emission` 리스트 항목으로 쓸 수 있는가."""
    errs = []
    if not item.get("what"):
        errs.append("`what` 이 없다 — 서수가 이 리스트에서 나오므로 내용 없는 항목을 넣지 않는다")
    return errs


def add_entry(entry: dict, *, dry_run: bool = False) -> dict:
    errs = entry_errors(entry)
    if errs:
        return {"added": False, "errors": errs}
    if dry_run:
        return {"added": False, "errors": [], "dry_run": True}
    d = _load()
    if any(e.get("id") == entry.get("id") for e in d["entries"]):
        return {"added": False, "errors": [f"이미 있다: {entry.get('id')}"]}
    d["entries"].append(entry)
    _save(d)
    return {"added": True, "n_entries": len(d["entries"])}


def add_caught(item: dict, *, dry_run: bool = False) -> dict:
    errs = caught_errors(item)
    if errs:
        return {"added": False, "errors": errs}
    if dry_run:
        return {"added": False, "errors": [], "dry_run": True}
    d = _load()
    d["caught_pre_emission"].append(item)
    _save(d)
    return {"added": True, "n_caught": len(d["caught_pre_emission"])}


def controls() -> dict:
    rows = []

    def case(name, got, want, negative=False):
        rows.append({"case": name, "got": got, "want": want, "ok": got == want,
                     "expectation": "must_flag" if negative else "must_not_flag"})

    case("`발행_전_자체검출` 필드는 막힌다",
         bool(entry_errors({"id": "X", "발행_전_자체검출": "y"})), True, negative=True)
    case("영문 `caught_pre_emission` 필드도 막힌다",
         bool(entry_errors({"id": "X", "caught_pre_emission": True})), True, negative=True)
    case("`id` 없는 항목은 막힌다", bool(entry_errors({"무엇": "y"})), True, negative=True)
    case("정상 entry 는 통과", bool(entry_errors({"id": "X", "무엇": "y"})), False)
    case("`what` 없는 caught 은 막힌다", bool(caught_errors({"why": "y"})), True, negative=True)
    case("정상 caught 은 통과", bool(caught_errors({"what": "y"})), False)
    case("dry_run 은 파일을 쓰지 않는다",
         add_entry({"id": "__DRY__"}, dry_run=True)["added"], False)
    ok = all(r["ok"] for r in rows)
    return {"verdict": "PASS" if ok else "FAIL", "n": len(rows),
            "must_flag": sum(1 for r in rows if r["expectation"] == "must_flag"),
            "must_not_flag": sum(1 for r in rows if r["expectation"] == "must_not_flag"),
            "failed": [r["case"] for r in rows if not r["ok"]], "cases": rows}


if __name__ == "__main__":
    c = controls()
    print(json.dumps(c, ensure_ascii=False, indent=1))
    raise SystemExit(0 if c["verdict"] == "PASS" else 3)
