"""D 도구가 **문법적으로 유효하고 import 되는가**.

[D-DEF-50] `D-DEF-48` 커밋에서 `d_presentation_eda.py` 에 주석을 콤마 앞에
넣어 syntax error 를 만들었다. **두 회차 동안 아무도 몰랐다** — 검사 7종이
전부 exit 0 이었고, 그 파일을 실행하는 검사가 하나도 없었기 때문이다.

우연히 `constant_drift` 가 그 모듈을 import 하다 잡았고, 그마저 `same=None`
을 통과로 세어 **또 묻힐 뻔했다**.

**커밋한 코드가 import 조차 안 되는 것을 검사가 모른다면, 그 검사 묶음은
자기가 덮는 범위를 모르는 것이다.**

**이 검사는 import 하지 않는다.** 처음엔 `importlib.import_module` 로 확인했는데
D 도구 상당수가 모듈 top-level 에서 분석을 실행하기 때문에 **검사가 산출물을
덮어썼다**(RQ_D9 그림 3개). `git checkout` 으로 되돌렸다.

**검사는 대상을 바꾸지 않는다.** 그래서 `ast.parse` 로 문법만 본다. import
오류(의존 누락)는 각 도구를 실제로 실행할 때 드러나고, 여기서 필요한 것은
"커밋한 코드가 문법적으로 유효한가" 다.
"""
from __future__ import annotations

import ast
import json
import sys
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
SKIP = {"__init__.py"}


def check() -> dict:
    syntax_bad, ok = [], []
    for p in sorted(TOOLS.glob("*.py")):
        if p.name in SKIP:
            continue
        try:
            ast.parse(p.read_text(encoding="utf-8"), filename=str(p))
            ok.append(p.name)
        except SyntaxError as e:
            syntax_bad.append({"tool": p.name, "line": e.lineno, "msg": str(e.msg)})
    return {"verdict": "PASS" if not syntax_bad else "FAIL",
            "n_tools": len(ok) + len(syntax_bad),
            "syntax_error": syntax_bad, "ok": len(ok),
            "import_은_하지_않는다": ("D 도구 상당수가 top-level 에서 분석을 실행한다 — "
                                "import 로 확인하면 **검사가 산출물을 덮어쓴다**. "
                                "실제로 RQ_D9 그림 3개를 덮었고 되돌렸다")}


def controls() -> dict:
    """합성 파일로 문법 오류를 실제로 잡는지 본다."""
    import tempfile
    rows = []

    def case(name, got, want):
        rows.append({"case": name, "got": got, "want": want, "ok": got == want})

    with tempfile.TemporaryDirectory() as td:
        d = Path(td)
        (d / "good.py").write_text("X = 1\n", encoding="utf-8")
        (d / "bad.py").write_text('D = {\n "a": [1]  # 주석\n "b": 2,\n}\n', encoding="utf-8")

        def scan(dirp):
            out = []
            for f in sorted(dirp.glob("*.py")):
                try:
                    ast.parse(f.read_text(encoding="utf-8"), filename=str(f))
                except SyntaxError:
                    out.append(f.name)
            return out

        got = scan(d)
        case("콤마 앞 주석 형태의 문법 오류를 잡는다", got, ["bad.py"])
        case("정상 파일은 안 잡는다", "good.py" in got, False)
    # 실제 도구 묶음에 문법 오류가 남아 있지 않은지 — 이 검사의 존재 이유
    case("현재 D 도구에 문법 오류 0", len(check()["syntax_error"]), 0)
    ok = all(r["ok"] for r in rows)
    return {"verdict": "PASS" if ok else "FAIL", "n": len(rows),
            "failed": [r["case"] for r in rows if not r["ok"]], "cases": rows}


if __name__ == "__main__":
    out = {"check": check(), "controls": controls()}
    print(json.dumps(out, ensure_ascii=False, indent=1))
    sys.exit(0 if out["check"]["verdict"] == "PASS"
             and out["controls"]["verdict"] == "PASS" else 1)
