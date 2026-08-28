"""D 검사들이 **값을 보는가, 산출물의 동일성을 보는가**.

A 가 `T-A-V3-PROBE-V4-001` 에서 일반화했다:

  "우리가 만든 검사는 전부 값을 보고, 이번에 통한 검사는 산출물의 동일성을 봤다.
   값 검사(must_flag · COLUMN_SENTINEL · undermapped_columns · 4-계층)는 전부
   이 형태를 통과시켰다."

D 도구에도 참인지 **세어서** 확인한다. 손으로 분류하면 그 분류가 또 값 검사다 —
코드에서 **무엇을 읽는 호출인지**로 판정한다.

  VALUE      : 셀·필드·컬럼의 값을 읽는다 (df[...], .get(), Counter, len)
  IDENTITY   : 바이트/해시 신원을 읽는다 (sha256, read_bytes, digest)
  DELTA      : **같은 대상의 두 시점/두 상태를 비교한다** (before/after, prev/curr)

DELTA 가 이번에 통한 축이다. IDENTITY 가 있어도 **한 시점의 신원**이면
'조작이 유효했는가' 는 못 잡는다.
"""
from __future__ import annotations

import ast
import json
import re
from pathlib import Path

RD = Path(__file__).resolve().parent.parent
TOOLS = RD / "tools"

VALUE_HINT = re.compile(r"\b(Counter|len\(|\.get\(|\.items\(\)|\.values\(\)|iterrows|"
                        r"is_missing|astype|str\(|int\(|float\()")
IDENTITY_HINT = re.compile(r"\b(sha256|read_bytes|hexdigest|digest|md5)\b")
# 두 시점/두 상태 비교 — 이름에 before/after·prev/curr·전후가 들어가거나
# 같은 함수 안에서 두 신원을 서로 비교한다
DELTA_HINT = re.compile(r"\b(before|after|prev|previous|curr|current|"
                        r"recomputed|recorded|baseline|drift|_same|diff)\b", re.I)


def classify_function(node: ast.FunctionDef, src: str) -> dict:
    seg = ast.get_source_segment(src, node) or ""
    v = bool(VALUE_HINT.search(seg))
    i = bool(IDENTITY_HINT.search(seg))
    d = bool(DELTA_HINT.search(seg))
    # DELTA 로 세려면 **두 신원을 비교**해야 한다 — identity 힌트 2회 이상 또는
    # identity 1회 + 명시적 비교 어휘
    ident_n = len(IDENTITY_HINT.findall(seg))
    delta = d and (ident_n >= 2 or re.search(r"==|!=", seg) is not None) and i
    return {"value": v, "identity": i, "delta_candidate": d,
            "identity_comparisons": ident_n, "delta": delta}


def scan() -> dict:
    rows, files = [], sorted(TOOLS.glob("d_*.py"))
    for f in files:
        try:
            src = f.read_text(encoding="utf-8")
            tree = ast.parse(src)
        except Exception as e:
            rows.append({"file": f.name, "fn": "<parse error>", "error": str(e)})
            continue
        for node in ast.walk(tree):
            if not isinstance(node, ast.FunctionDef):
                continue
            name = node.name
            # 검사 함수만 — 이름이 check/control/audit/verify/scan/gate 계열
            if not re.search(r"check|control|audit|verify|gate|scan|freshness|coverage",
                             name, re.I):
                continue
            c = classify_function(node, src)
            kind = ("DELTA" if c["delta"] else
                    "IDENTITY" if c["identity"] else
                    "VALUE" if c["value"] else "OTHER")
            rows.append({"file": f.name, "fn": name, "kind": kind, **c})

    by = {}
    for r in rows:
        by[r.get("kind", "?")] = by.get(r.get("kind", "?"), 0) + 1
    return {"n_functions": len(rows), "by_kind": by, "functions": rows,
            "method": ("AST 로 검사 함수를 뽑고, 본문이 **무엇을 읽는지**로 분류했다. "
                       "손으로 분류하면 그 분류가 또 값 검사다"),
            "definitions": {
                "VALUE": "셀·필드·컬럼의 값을 읽는다",
                "IDENTITY": "바이트/해시 신원을 읽는다 — 다만 한 시점이면 조작 유효성은 못 본다",
                "DELTA": "**같은 대상의 두 신원을 비교한다** — 이번에 통한 축"},
            "limitation": ("정적 분류다. 이름과 호출 패턴으로 판정하므로 "
                           "실제 의미와 어긋날 수 있다 — 수치가 아니라 **분포의 방향**으로만 읽는다")}


if __name__ == "__main__":
    r = scan()
    print(json.dumps({k: v for k, v in r.items() if k != "functions"},
                     ensure_ascii=False, indent=1))
    print("\n--- 함수별 ---")
    for f in r["functions"]:
        print(f"  {f.get('kind','?'):<9} {f['file']:<26} {f['fn']}")
