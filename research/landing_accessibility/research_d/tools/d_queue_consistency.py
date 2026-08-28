"""큐 문서가 적은 RQ 상태가 **실제와 같은가**.

D_RESEARCH_QUEUE.md 상단에 마스터 표가 있고 그 아래는 시간순 로그다. 로그가
쌓이면 마스터 표가 뒤처진다 — 문서 자신이 "상태 정리 … 큐 표가 stale 했다"
섹션을 갖고 있는데(2026-08-27 23:45) **그 뒤에 또 뒤처졌다**. RQ-D7 과
RQ-D13b 는 완결 게이트를 통과하고 티켓까지 발행됐는데 마스터 표는 `OPEN` 이다.

이것은 D 가 반복해 잡아온 결함족의 문서판이다 — **적힌 것과 실제가 다르고,
적힌 쪽만 보면 통과한다**. 자기 정합성 검사로는 안 잡힌다. 마스터 표는 자기
자신과 정합하기 때문이다.

축은 **행위 유효성**에 가깝다: 상태를 적는 행위가 실제 상태를 반영했는가.

**이 검사는 문서를 고치지 않는다.** 상태 판정은 기록의 문제이고 자동으로
덮으면 이력이 사라진다. flag 만 하고 정정은 addendum 으로 남긴다.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

RD = Path(__file__).resolve().parent.parent
QUEUE = RD / "D_RESEARCH_QUEUE.md"
BUS = Path("/home/sieg/projects-wsl/ProjectFinal/.agent_bus/landing_v2")
NB_DIR = RD.parent / "notebooks/d_research"

OPEN_TOKENS = ("OPEN",)
CLOSED_TOKENS = ("CLOSED_WITH_FINDING", "DONE", "SUPERSEDED_BY_CHILDREN",
                 "CLOSED", "SUPPORTED", "NOT_SUPPORTED", "PARTIALLY_SUPPORTED")
_RQ = re.compile(r"\bRQ-[A-Z0-9][A-Za-z0-9\-]*\b")
_MASTER_END = "## 규칙"          # 마스터 표는 이 헤더 앞까지다


def _split(text: str) -> tuple:
    i = text.find(_MASTER_END)
    return (text[:i], text[i:]) if i > 0 else (text, "")


def _states(line: str) -> set:
    out = set()
    for t in CLOSED_TOKENS:
        if t in line:
            out.add("CLOSED")
    for t in OPEN_TOKENS:
        if re.search(r"\|\s*(\*\*)?OPEN(\*\*)?\s*\|", line) or re.search(r"\bOPEN\b", line):
            out.add("OPEN")
    return out


def _subject(line: str):
    """표 행의 **주어**는 첫 셀의 RQ 다.

    처음엔 한 줄에 나오는 모든 RQ 에 그 줄의 상태를 귀속시켰다. 그래서
    `| RQ-D6 | ... (RQ-D1 F6 파생) | OPEN |` 이 RQ-D1 을 OPEN 으로 만들었다 —
    RQ-D1 은 마스터 표에서 DONE 인데도 stale 로 잡혔다. **오탐이었다.**
    """
    if line.lstrip().startswith("|"):
        first = line.split("|")[1] if line.count("|") >= 2 else ""
        m = _RQ.search(first)
        return {m.group(0)} if m else set()
    return set(_RQ.findall(line))


def collect(text: str | None = None) -> dict:
    text = QUEUE.read_text(encoding="utf-8") if text is None else text
    master, log = _split(text)
    m_state, l_state = {}, {}
    for line in master.splitlines():
        for rq in _subject(line):
            s = _states(line)
            if s:
                m_state.setdefault(rq, set()).update(s)
    for line in log.splitlines():
        for rq in _subject(line):
            s = _states(line)
            if s:
                l_state.setdefault(rq, set()).update(s)
    return {"master": m_state, "log": l_state}


def _ticket_exists(tid: str) -> bool:
    return (BUS / "tickets" / f"{tid}.json").exists()


def check(text: str | None = None) -> dict:
    cases = []

    def case(name, ok, detail):
        cases.append({"case": name, "ok": bool(ok), "detail": detail})

    st = collect(text)
    # 1. 마스터 표가 OPEN 이라 하는데 로그는 닫혔다고 하는 RQ
    stale = sorted(r for r, s in st["master"].items()
                   if "OPEN" in s and "CLOSED" in st["log"].get(r, set()))
    case("마스터 표의 OPEN 이 로그의 종료와 어긋나지 않는다", not stale,
         {"stale": stale,
          "뜻": "로그는 닫혔다고 적었는데 표는 OPEN 이다 — 표만 보면 미완으로 보인다"})

    # 2. 큐가 인용한 D 발행 티켓이 버스에 실재하는가
    txt = QUEUE.read_text(encoding="utf-8") if text is None else text
    cited = sorted(set(re.findall(r"D-V3-[A-Z]+-\d+", txt)))
    missing = [t for t in cited if not _ticket_exists(t)]
    case("큐가 인용한 D 티켓이 버스에 실재한다", not missing,
         {"cited": len(cited), "missing": missing})

    # 3. 큐가 인용한 노트북이 실재하고 error 0 인가
    nbs = sorted(set(re.findall(r"[A-Za-z0-9_]+\.ipynb", txt)))
    nb_bad = []
    for n in nbs:
        p = NB_DIR / n
        if not p.exists():
            nb_bad.append({"nb": n, "why": "파일 없음"})
            continue
        try:
            d = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            nb_bad.append({"nb": n, "why": "파싱 실패"})
            continue
        cells = d.get("cells")
        if cells is None:
            nb_bad.append({"nb": n, "why": "cells 없음"})
            continue
        err = sum(1 for c in cells for o in c.get("outputs", [])
                  if o.get("output_type") == "error")
        unrun = sum(1 for c in cells
                    if c.get("cell_type") == "code" and c.get("execution_count") is None)
        if err or unrun:
            nb_bad.append({"nb": n, "why": f"err={err} unrun={unrun}"})
    case("큐가 인용한 노트북이 실재하고 error 0 · 미실행 0", not nb_bad,
         {"n": len(nbs), "bad": nb_bad})

    ok = all(c["ok"] for c in cases)
    return {"verdict": "PASS" if ok else "FAIL", "n": len(cases),
            "failed": [c["case"] for c in cases if not c["ok"]], "cases": cases,
            "이_검사가_고치지_않는_것": "문서를 자동으로 덮지 않는다 — 상태 판정은 기록이고 덮으면 이력이 사라진다"}


def controls() -> dict:
    """**합성 텍스트**로 막는지 본다.

    처음엔 실제 큐를 must_flag 대조군으로 썼다. 틀렸다 — **대조군이 현재
    상태에 묶이면 문서를 고치는 순간 대조군이 깨진다**. 검사의 성능이 대상의
    상태에 의존해선 안 된다. 합성본으로 바꿨다.
    """
    rows = []

    def run(name, text, should_fail=True):
        flagged = check(text)["verdict"] == "FAIL"
        rows.append({"case": name, "flagged": flagged,
                     "expectation": "must_flag" if should_fail else "must_not_flag",
                     "ok": flagged == should_fail})

    HEAD = "# D Research Queue\n\n"
    RULE = "\n" + _MASTER_END + "\n"
    run("한 줄에 다른 RQ 가 언급돼도 주어는 첫 셀 — 오탐 없음",
        HEAD + "| **RQ-Z8** | x | DONE | — |\n| **RQ-Z9** | (RQ-Z8 파생) | OPEN | — |\n"
        + RULE + "| RQ-Z8 | CLOSED_WITH_FINDING |\n| RQ-Z9 | 진행 중 |\n",
        should_fail=False)
    run("표 OPEN · 로그 CLOSED → 막힘",
        HEAD + "| **RQ-Z9** | x | OPEN | — |\n" + RULE + "| RQ-Z9 | CLOSED_WITH_FINDING |\n")
    run("표 OPEN · 로그도 OPEN → 통과",
        HEAD + "| **RQ-Z9** | x | OPEN | — |\n" + RULE + "| RQ-Z9 | 진행 중 |\n",
        should_fail=False)
    run("표 CLOSED · 로그 CLOSED → 통과",
        HEAD + "| **RQ-Z9** | x | DONE | — |\n" + RULE + "| RQ-Z9 | CLOSED_WITH_FINDING |\n",
        should_fail=False)
    run("없는 D 티켓을 인용하면 막힘",
        HEAD + RULE + "발행: D-V3-FINDING-999\n")
    run("없는 노트북을 인용하면 막힘",
        HEAD + RULE + "노트북: RQ_ZZZ_nonexistent.ipynb\n")
    run("빈 문서는 불일치 없음", HEAD + RULE, should_fail=False)

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
