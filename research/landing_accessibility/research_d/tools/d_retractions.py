"""철회된 라벨을 **정본에서 읽는다**.

[A R163 / T-A-V3-K8-003] B 의 관측: "내 검사들은 CSV 의 값을 보지 그 값이
사람에게 어떻게 읽히는지를 안 본다. `NO_SAFE_ROUTE_SITE` 가 CSV 에 남아 있어도
검사는 통과하고 읽는 사람만 오해한다. 그래서 `RETRACTIONS.md` 를 CSV 옆에
뒀는데 **그것도 검사가 아니라 문서다**."

**D 도 같은 형태를 냈다.** `d_coverage.py` 는 `NO_SAFE_ROUTE_SITE` 를 관측값
whitelist 에 넣으면서 "SITE 라벨은 R132/R137 로 철회됐다" 를 **주석에만** 적었다.
그리고 `d_v3_report.GROUPS` 는 그 토큰을 **"SITE-SIDE ROUTE NOT OBSERVED"**
라는 그룹명으로 묶었다 — RETRACTIONS.md 가 금지한 바로 그 형태다:
"이 토큰을 사이트에 대한 진술로 쓰면 안 된다."

주석은 검사가 아니다. 그래서 여기서 **정본을 읽는다.**

파싱 규칙은 보수적이다 — `— **철회됨**` 이 붙은 절만 철회로 본다.
같은 문서에 `**철회 아님. 유지**` 절(`COLLECTOR_ZERO_CANDIDATE`)이 있고
**그것을 철회로 잡으면 반대 방향의 오류**가 된다.
"""
from __future__ import annotations

import re
from pathlib import Path

REPO = Path("/home/sieg/projects-wsl/ProjectFinal")
RETRACTIONS = REPO / "artifacts/v3_census/mart/CANONICAL_MART_50.RETRACTIONS.md"

# `## \`TOKEN\` (16행) — **철회됨**`  /  `## \`TOKEN\` (21행) — **철회 아님. 유지**`
_SEC = re.compile(r"^##\s+`([A-Z0-9_]+)`.*?—\s*\*\*(.+?)\*\*", re.M)
_RETRACTED = "철회됨"

MARK = "RETRACTED"
# JSON 산출물에서 토큰이 **키**로 쓰이면 표시를 키에 붙일 수 없다 — 붙이면
# 그 파일을 읽는 도구가 키를 못 찾는다. 대신 파일이 이 필드로 **인용 사실을
# 명시**하면 인정한다. 값을 오염시키지 않으면서 읽는 사람에게 보이게 하는 자리다.
DECLARE_FIELD = "retracted_labels_cited"


def parse(text: str | None = None) -> dict:
    t = RETRACTIONS.read_text(encoding="utf-8") if text is None else text
    out = {}
    for m in _SEC.finditer(t):
        token, verdict = m.group(1), m.group(2).strip()
        out[token] = {"retracted": verdict.startswith(_RETRACTED),
                      "verdict_text": verdict}
    # 대체 라벨과 정확한 진술은 인용하는 쪽이 함께 실어야 한다.
    # **절 경계로 자른다** — 처음엔 첫 등장 이후 전체를 봤고, 그러면
    # `COLLECTOR_ZERO_CANDIDATE`(철회 아님)가 앞 절의 대체 라벨을 주워왔다.
    # 철회 아닌 토큰에 대체 라벨이 붙는 것은 **없는 사실을 만드는 것**이다.
    spans = [(m.group(1), m.start()) for m in _SEC.finditer(t)]
    for i, (token, start) in enumerate(spans):
        end = spans[i + 1][1] if i + 1 < len(spans) else len(t)
        seg = t[start:end]
        alt = re.search(r"\*\*대체 라벨\*\*:\s*`([A-Z0-9_]+)`", seg)
        say = re.search(r"\*\*정확한 진술\*\*:\s*(.+)", seg)
        out[token]["replacement"] = alt.group(1) if alt else None
        out[token]["accurate_statement"] = say.group(1).strip() if say else None
    return out


def retracted_tokens() -> set:
    return {k for k, v in parse().items() if v["retracted"]}


def cite(token: str) -> str:
    """철회된 토큰은 **표시를 달아서만** 문자열로 나간다."""
    return f"{token} [{MARK}]" if token in retracted_tokens() else token


def audit_text(text: str, source: str = "") -> list:
    """어떤 산출물 텍스트가 철회 토큰을 **표시 없이** 인용하는가."""
    bad = []
    for tok in sorted(retracted_tokens()):
        for m in re.finditer(re.escape(tok), text):
            tail = text[m.end():m.end() + 40]
            head = text[max(0, m.start() - 40):m.start()]
            if MARK in tail or MARK in head:
                continue
            bad.append({"source": source, "token": tok,
                        "context": text[max(0, m.start() - 45):m.end() + 45]
                        .replace("\n", " ")})
    return bad


ANALYSIS = REPO / "artifacts/v3_census/analysis"


def audit_artifacts(root=None) -> dict:
    """**산출물**이 철회 토큰을 표시 없이 인용하는가.

    도구 소스는 대상이 아니다 — 거기서는 상수를 정의하고 이 모듈이 표시를
    붙인다. 사람이 읽는 것은 산출물이고, B 가 말한 "읽는 사람만 오해한다" 의
    그 자리다.
    """
    root = ANALYSIS if root is None else Path(root)
    bad = []
    for p in sorted(list(root.rglob("*.csv")) + list(root.rglob("*.md"))
                    + list(root.rglob("*.json"))):
        try:
            txt = p.read_text(encoding="utf-8")
        except Exception:
            continue
        if p.suffix == ".json":
            declared = set()
            try:
                import json as _j
                declared = set((_j.loads(txt).get(DECLARE_FIELD) or {}).keys()
                               if isinstance(_j.loads(txt).get(DECLARE_FIELD), dict)
                               else (_j.loads(txt).get(DECLARE_FIELD) or []))
            except Exception:
                declared = set()
            hits = [h for h in audit_text(txt, str(p.relative_to(root)))
                    if h["token"] not in declared]
            bad += hits
            continue
        bad += audit_text(txt, str(p.relative_to(root)))
    return {"verdict": "PASS" if not bad else "FAIL", "n": len(bad),
            "files": sorted({b["source"] for b in bad}), "hits": bad[:20],
            "대상": "산출물만 — 도구 소스는 정의하는 곳이고 표시는 cite() 가 붙인다"}


def controls() -> dict:
    """파싱과 감사가 **양방향으로** 맞는지 본다."""
    rows = []

    def case(name, got, want):
        rows.append({"case": name, "got": got, "want": want, "ok": got == want})

    p = parse()
    case("NO_SAFE_ROUTE_SITE 는 철회됨", p.get("NO_SAFE_ROUTE_SITE", {}).get("retracted"), True)
    # **반대 방향** — 같은 문서의 '철회 아님' 절을 철회로 잡으면 안 된다
    case("COLLECTOR_ZERO_CANDIDATE 는 철회 아님",
         p.get("COLLECTOR_ZERO_CANDIDATE", {}).get("retracted"), False)
    case("대체 라벨을 읽는다",
         p.get("NO_SAFE_ROUTE_SITE", {}).get("replacement"), "ROUTE_NOT_REACHED_BY_COLLECTOR")
    # **반대 방향** — 철회 아닌 토큰에 대체 라벨이 붙으면 없는 사실을 만든 것이다.
    # 처음 판에서 실제로 그랬다(절 경계 없이 첫 등장 이후 전체를 봤다)
    case("철회 아닌 토큰에는 대체 라벨이 없다",
         p.get("COLLECTOR_ZERO_CANDIDATE", {}).get("replacement"), None)
    case("표시 없는 인용은 걸린다",
         len(audit_text("terminal_reason=NO_SAFE_ROUTE_SITE 16/50")), 1)
    case("표시 있는 인용은 안 걸린다",
         len(audit_text("NO_SAFE_ROUTE_SITE [RETRACTED] 16/50")), 0)
    case("철회 아닌 토큰은 안 걸린다",
         len(audit_text("COLLECTOR_ZERO_CANDIDATE 21/50")), 0)
    case("cite() 가 표시를 붙인다", cite("NO_SAFE_ROUTE_SITE"),
         "NO_SAFE_ROUTE_SITE [RETRACTED]")
    case("cite() 가 아무 데나 붙이지 않는다", cite("COLLECTOR_ZERO_CANDIDATE"),
         "COLLECTOR_ZERO_CANDIDATE")
    # 정본을 읽지 못하면 통과가 아니어야 한다 — 빈 문서에서 철회 집합이 비면 감사가 무력해진다
    case("빈 정본이면 철회 집합이 비고, 그 사실이 보인다", len(parse("")), 0)
    # 산출물 감사가 실제로 무언가를 세는지 — 합성 디렉터리로 양방향 확인
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        d = Path(td)
        (d / "a.csv").write_text("x,NO_SAFE_ROUTE_SITE,16\n", encoding="utf-8")
        case("산출물 감사가 표시 없는 인용을 잡는다",
             audit_artifacts(d)["verdict"], "FAIL")
        (d / "a.csv").write_text("x,NO_SAFE_ROUTE_SITE [RETRACTED],16\n", encoding="utf-8")
        case("표시가 있으면 통과", audit_artifacts(d)["verdict"], "PASS")
        # JSON 은 키를 오염시키지 않고 선언 필드로 인정한다 — 양방향
        (d / "b.json").write_text('{"dist": {"NO_SAFE_ROUTE_SITE": 16}}', encoding="utf-8")
        case("JSON 이 선언 없이 인용하면 막힘", audit_artifacts(d)["verdict"], "FAIL")
        (d / "b.json").write_text(
            '{"dist": {"NO_SAFE_ROUTE_SITE": 16},'
            ' "retracted_labels_cited": {"NO_SAFE_ROUTE_SITE": "SITE 라벨 철회 — R137"}}',
            encoding="utf-8")
        case("JSON 이 선언하면 통과", audit_artifacts(d)["verdict"], "PASS")

    ok = all(r["ok"] for r in rows)
    return {"verdict": "PASS" if ok else "FAIL", "n": len(rows),
            "failed": [r["case"] for r in rows if not r["ok"]], "cases": rows}


if __name__ == "__main__":
    import json
    import sys
    print(json.dumps({"parsed": parse(), "retracted": sorted(retracted_tokens()),
                      "controls": controls()}, ensure_ascii=False, indent=1))
    sys.exit(0 if controls()["verdict"] == "PASS" else 1)
