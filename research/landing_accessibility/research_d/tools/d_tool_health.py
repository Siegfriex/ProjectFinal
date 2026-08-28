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


# 매 루프에서 실제로 **실행**되는 검사들. 여기 없는 도구는 문법만 확인된다.
LOOP_ENTRYPOINTS = [
    "d_bus_scan", "d_tool_health", "d_coverage", "d_citation_check",
    "d_prereg_check", "d_v3_bundle_check", "d_queue_consistency",
    "d_ticket_schema_check", "d_retractions", "d_input_firewall",
    "d_input_integrity", "d_priority_availability",
    "d_heartbeat", "d_mlflow", "d_emit_ticket",
]


def _imports(path: Path) -> set:
    """그 파일이 부르는 **D 도구 모듈** 이름."""
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    except SyntaxError:
        return set()
    names = set()
    for n in ast.walk(tree):
        if isinstance(n, ast.Import):
            names |= {a.name.split(".")[0] for a in n.names}
        elif isinstance(n, ast.ImportFrom) and n.module and n.level == 0:
            names.add(n.module.split(".")[0])
    return {x for x in names if (TOOLS / f"{x}.py").exists()}


def coverage() -> dict:
    """**검사 묶음이 덮는 범위를 수치로 잰다.**

    [D-DEF-50] `d_presentation_eda.py` 가 syntax error 인 채 두 회차를 지났다.
    검사 7종이 전부 exit 0 이었고 **그 파일을 실행하는 검사가 하나도 없었다** —
    검사 묶음이 자기가 덮지 않는 범위를 몰랐다.

    그 범위를 모르면 다음에 또 같은 일이 난다. **모르는 것을 수치로 만든다.**

    `d_bus_scan.sh` 는 셸이지만 그 안의 파이썬이 D 모듈을 부르므로 함께 훑는다.
    """
    seen, frontier = set(), []
    for e in LOOP_ENTRYPOINTS:
        f = TOOLS / f"{e}.py"
        sh = TOOLS / f"{e}.sh"
        if f.exists():
            frontier.append(e)
        elif sh.exists():
            # 셸 안의 `from X import` / `import X` 도 훑는다
            txt = sh.read_text(encoding="utf-8")
            for line in txt.splitlines():
                line = line.strip()
                for pre in ("from ", "import "):
                    if line.startswith(pre):
                        mod = line[len(pre):].split()[0].split(".")[0]
                        if (TOOLS / f"{mod}.py").exists():
                            frontier.append(mod)
    while frontier:                       # 전이 폐쇄
        m = frontier.pop()
        if m in seen:
            continue
        seen.add(m)
        frontier += list(_imports(TOOLS / f"{m}.py") - seen)
    allt = {p.stem for p in TOOLS.glob("*.py") if p.name not in SKIP}
    uncovered = sorted(allt - seen)
    return {"n_tools": len(allt), "executed_in_loop": len(seen),
            "syntax_only": len(uncovered),
            "covered": sorted(seen), "syntax_only_tools": uncovered,
            "무엇을_뜻하나": ("`syntax_only` 는 **매 루프에 실행되지 않는** 도구다. "
                        "문법은 확인되지만 런타임 결함은 그 도구를 직접 돌릴 때만 드러난다"),
            "왜_재나": "D-DEF-50 은 이 범위를 **모르고 있었기 때문에** 두 회차를 갔다",
            "이_수치의_한계": ("`executed_in_loop` 는 **import 전이 폐쇄**다. 그 모듈이 "
                        "불려진다는 뜻이지 **그 안의 함수가 호출된다**는 뜻은 아니다. "
                        "실제 실행 범위는 이보다 좁을 수 있다"),
            "D-DEF-50_당시와_지금": ("`d_presentation_eda` 는 깨졌던 시점(`b0b39ac`)에 "
                        "**아무도 import 하지 않아 uncovered** 였다. 지금 covered 인 것은 "
                        "이번 회차에 만든 `constant_drift` 의 부산물이다 — **우연이다.** "
                        "재발을 막는 것은 그 우연이 아니라 64/64 문법 검사다")}


# 이름을 **손으로 열거하지 않는다** — `d_bus_lib.cross_plane_ack_controls` 가
# 목록에 없어 NO_CONTROLS 로 잘못 나왔다. 손 목록은 뒤처진다(D-DEF-45).
_CONTROL_NAME = __import__("re").compile(r"(controls?|self_?test)$")


def control_coverage() -> dict:
    """루프에서 도는 도구가 **실행되는 대조군**을 갖는가.

    [D-DEF-54] `d_heartbeat._production_touch` 는 R41 의 must_flag/must_not_flag 를
    **문자열 서술**로만 갖고 있었다 — 말은 맞지만 아무것도 실행되지 않았다.
    안전 주장을 내는 측정기가 자기 판정을 검증하지 않은 것이다.

    **부정 케이스 수를 자동으로 세려다 두 번 오분류했다.** 대조군의 표기 형태가
    제각각이라(`must_flag` 필드 / `want=False` / `should_fail`) 형태에 걸렸다.
    그래서 이 도구는 **확실한 것만 단정**한다 — 대조군 함수의 존재, 실행 가능
    여부, verdict. 부정 케이스 수는 **추정치**이고 형태를 못 읽으면 `null` 이다.
    """
    import importlib
    import sys as _sys
    if str(TOOLS) not in _sys.path:
        _sys.path.insert(0, str(TOOLS))
    rows = []
    for m in sorted(coverage()["covered"]):
        row = {"module": m, "fn": None, "verdict": None,
               "negative_cases": None, "state": ""}
        try:
            mod = importlib.import_module(m)
        except Exception as e:
            row["state"] = f"IMPORT_FAIL: {type(e).__name__}"
            rows.append(row)
            continue
        fn = next((f for f in sorted(dir(mod))
                   if _CONTROL_NAME.search(f) and callable(getattr(mod, f, None))
                   and getattr(getattr(mod, f), "__module__", "") == m), None)
        row["fn"] = fn
        if not fn:
            row["state"] = "NO_CONTROLS"
            rows.append(row)
            continue
        try:
            c = getattr(mod, fn)()
        except TypeError:
            row["state"] = "NEEDS_ARGS"     # 인자가 필요 — 없다고 셀 수 없다
            rows.append(row)
            continue
        except Exception as e:
            row["state"] = f"RUN_FAIL: {type(e).__name__}"
            rows.append(row)
            continue
        if not isinstance(c, dict):
            row["state"] = "NON_DICT"
            rows.append(row)
            continue
        row["verdict"] = c.get("verdict")
        cs = c.get("cases") or c.get("rows") or []
        neg = sum(1 for x in cs if isinstance(x, dict) and (
            x.get("expectation") == "must_flag" or x.get("should_fail") is True
            or ("want" in x and x["want"] in (False, "FAIL", 0))))
        if not neg and isinstance(c.get("must_flag"), int):
            neg = c["must_flag"]
        row["negative_cases"] = neg if (cs or c.get("must_flag") is not None) else None
        row["state"] = "OK"
        rows.append(row)
    no_ctrl = [r["module"] for r in rows if r["state"] == "NO_CONTROLS"]
    unread = [r["module"] for r in rows
              if r["state"] in ("NEEDS_ARGS", "NON_DICT") or
              (r["state"] == "OK" and r["negative_cases"] is None)]
    zero = [r["module"] for r in rows
            if r["state"] == "OK" and r["negative_cases"] == 0]
    return {"n": len(rows), "rows": rows,
            "no_controls": no_ctrl, "unreadable_shape": unread,
            "negative_zero_suspect": zero,
            "확실한_것": "대조군 함수의 **존재 여부**와 실행 가능 여부, verdict",
            "추정인_것": ("부정 케이스 수. 표기 형태가 제각각이라 못 읽으면 "
                     "`unreadable_shape` 로 둔다 — **0 으로 세지 않는다**"),
            "왜_0_으로_세지_않나": "실제로 두 번 오분류했다. **읽지 못한 것을 없다고 세지 않는다**"}


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
    out = {"check": check(), "controls": controls(), "coverage": coverage(),
           "control_coverage": control_coverage()}
    print(json.dumps(out, ensure_ascii=False, indent=1))
    sys.exit(0 if out["check"]["verdict"] == "PASS"
             and out["controls"]["verdict"] == "PASS" else 1)
