"""방화벽 WARN 이 **늘어났는지** 본다.

[D-DEF-59] WARN 396 이 매 스캔 같은 숫자로 뜬다. D 는 그것을 "산문 경계선" 으로
흘려왔고 **한 번도 열어보지 않았다**(D-DEF-58). 총수가 고정돼 보이면 **늘어나도
모른다** — 영구 FAIL 이 신호를 죽인 것과 같은 형태다(D-DEF-52).

**총수는 신호가 아니다.** D 가 산출물을 하나 만들 때마다 그 안의 firewall
선언문이 WARN 을 7건씩 더한다. 총수로 재면 매 회차 "새 WARN 7건" 이 뜨고 그것도
곧 배경음이 된다.

**신호는 새 종류다:**

  - 새 `reference` 토큰 — 지금까지 7종이었다. 여덟 번째가 나오면 그것은
    **새 금지 대상을 건드렸다**는 뜻이다
  - 새 최상위 경로 — WARN 이 나던 곳 밖에서 나면 새 자리다

**대상을 바꾸지 않는다**(D-DEF-50). 산출을 읽기만 한다.
"""
from __future__ import annotations

import json
import subprocess
from collections import Counter
from pathlib import Path

RD = Path(__file__).resolve().parent.parent
SCAN = RD / "results" / "D_INPUT_FIREWALL_VERIFICATION.json"
BASELINE = RD / "results" / "D_WARN_BASELINE.json"


def _top(path: str) -> str:
    return path.split("/", 1)[0] if "/" in path else path


def shape(doc=None) -> dict:
    """WARN 의 **종류**를 뽑는다 — 총수가 아니라 토큰 집합과 경로 집합."""
    if doc is None:
        if not SCAN.exists():
            return {"_missing": True}
        doc = json.loads(SCAN.read_text(encoding="utf-8"))
    ws = [v for v in (doc.get("violations") or []) if v.get("severity") == "WARN"]
    return {"n": len(ws),
            "references": sorted({str(v.get("reference")) for v in ws}),
            "top_paths": sorted({_top(str(v.get("file", ""))) for v in ws}),
            "by_reference": dict(Counter(str(v.get("reference")) for v in ws))}


def check() -> dict:
    now = shape()
    if now.get("_missing"):
        return {"verdict": "NO_SCAN", "why": f"스캔 산출이 없다: {SCAN}"}
    if not BASELINE.exists():
        return {"verdict": "NO_BASELINE", "n": now["n"],
                "무엇을_해야_하나": "`write_baseline()` 으로 기준을 한 번 기록한다"}
    base = json.loads(BASELINE.read_text(encoding="utf-8"))["shape"]
    new_refs = sorted(set(now["references"]) - set(base["references"]))
    gone_refs = sorted(set(base["references"]) - set(now["references"]))
    new_paths = sorted(set(now["top_paths"]) - set(base["top_paths"]))
    ok = not (new_refs or new_paths)
    return {"verdict": "PASS" if ok else "FAIL",
            "n_now": now["n"], "n_base": base["n"], "delta": now["n"] - base["n"],
            "new_references": new_refs, "gone_references": gone_refs,
            "new_top_paths": new_paths,
            "총수는_신호가_아니다": ("D 가 산출물을 만들 때마다 그 안의 firewall 선언문이 "
                            "WARN 을 더한다. **새 종류**만 본다"),
            "무엇이_신호인가": ("새 `reference` 토큰 = 새 금지 대상을 건드렸다. "
                        "새 최상위 경로 = WARN 이 나던 곳 밖에서 났다")}


def write_baseline(note: str = "") -> dict:
    s = shape()
    doc = {"measured_at_kst": subprocess.run(
        ["date", "-Iseconds"], capture_output=True, text=True).stdout.strip(),
        "note": note, "source": str(SCAN), "shape": s}
    BASELINE.write_text(json.dumps(doc, ensure_ascii=False, indent=1) + "\n",
                        encoding="utf-8")
    return {"written": str(BASELINE), "n": s["n"],
            "references": len(s["references"]), "top_paths": s["top_paths"]}


def controls() -> dict:
    """합성 문서로 **새 종류**를 잡는지 본다. 실제 산출은 건드리지 않는다."""
    rows = []

    def case(name, got, want, negative=False):
        rows.append({"case": name, "got": got, "want": want, "ok": got == want,
                     "expectation": "must_flag" if negative else "must_not_flag"})

    def doc(refs, files):
        return {"violations": [{"severity": "WARN", "reference": r, "file": f}
                               for r, f in zip(refs, files)]}

    base = shape(doc(["A", "B"], ["x/1.py", "x/2.py"]))
    def diff(now):
        nr = sorted(set(now["references"]) - set(base["references"]))
        np_ = sorted(set(now["top_paths"]) - set(base["top_paths"]))
        return nr, np_

    case("같은 종류면 통과", diff(shape(doc(["A", "B"], ["x/3.py", "x/4.py"]))), ([], []))
    case("**총수가 늘어도** 종류가 같으면 통과",
         diff(shape(doc(["A", "B", "A", "B"], ["x/1.py"] * 4))), ([], []))
    case("새 토큰이 나오면 잡는다",
         diff(shape(doc(["A", "C"], ["x/1.py", "x/2.py"]))), (["C"], []), negative=True)
    case("새 최상위 경로가 나오면 잡는다",
         diff(shape(doc(["A", "B"], ["x/1.py", "y/2.py"]))), ([], ["y"]), negative=True)
    # 검사가 대상을 바꾸지 않는지
    a, b = shape(), shape()
    case("검사 자체가 산출을 바꾸지 않는다", a == b, True)

    ok = all(r["ok"] for r in rows)
    return {"verdict": "PASS" if ok else "FAIL", "n": len(rows),
            "must_flag": sum(1 for r in rows if r["expectation"] == "must_flag"),
            "must_not_flag": sum(1 for r in rows if r["expectation"] == "must_not_flag"),
            "failed": [r["case"] for r in rows if not r["ok"]], "cases": rows}


if __name__ == "__main__":
    import sys
    out = {"check": check(), "controls": controls()}
    print(json.dumps(out, ensure_ascii=False, indent=1))
    v = out["check"]["verdict"]
    sys.exit(0 if out["controls"]["verdict"] == "PASS"
             and v in ("PASS", "NO_BASELINE", "NO_SCAN") else 1)
