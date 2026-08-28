"""`None` 이 통과하는 자리를 D 도구에서 전수로 찾는다.

A 가 `T-A-V3-PROBE-V4-002` R147 에서 자기 집계기 결함을 보고했다:

  `in_vp = None` 인데 `if in_vp is False:` 만 검사했다. **`None` 은 통과했다.**
  31/31 행 전부 None 이었고 조건 4 는 한 번도 적용되지 않았는데 출력은 TRUSTED 6.

  "거짓 성공을 막으려고 착수 전에 동결한 검사기가 정확히 그 형태를 냈다."

D 도구에도 있는지 **센다.** 세 종류를 찾는다:

  FALSE_ONLY   `is False` / `== False` 만 보고 None 을 흘린다
  TRUTHY_GATE  `if not x:` 로 None·False·0·""·[] 를 한 덩어리로 접는다
  BARE_GET     `.get(k)` 결과를 None 검사 없이 조건에 바로 넣는다

**셋 다 '평가 불가' 를 '통과' 나 '실패' 중 하나로 몰아넣는다** — 어느 쪽이든
세 번째 상태가 사라진다.
"""
from __future__ import annotations

import ast
import json
import re
from pathlib import Path

TOOLS = Path(__file__).resolve().parent


class Finder(ast.NodeVisitor):
    def __init__(self, src: str, fname: str):
        self.src, self.fname, self.hits = src, fname, []
        self.fn = "<module>"

    def visit_FunctionDef(self, node):
        prev, self.fn = self.fn, node.name
        self.generic_visit(node)
        self.fn = prev

    def _add(self, node, kind, snippet):
        self.hits.append({"file": self.fname, "fn": self.fn, "line": node.lineno,
                          "kind": kind, "snippet": snippet.strip()[:110]})

    def visit_Compare(self, node):
        # `x is False` / `x == False` — None 이 흘러간다
        for op, cmp_ in zip(node.ops, node.comparators):
            if isinstance(op, (ast.Is, ast.Eq)) and \
               isinstance(cmp_, ast.Constant) and cmp_.value is False:
                seg = ast.get_source_segment(self.src, node) or ""
                self._add(node, "FALSE_ONLY", seg)
        self.generic_visit(node)

    def visit_If(self, node):
        t = node.test
        # `if not x:` — None·False·0·"" 를 한 덩어리로
        if isinstance(t, ast.UnaryOp) and isinstance(t.op, ast.Not) and \
           isinstance(t.operand, ast.Name):
            seg = ast.get_source_segment(self.src, node) or ""
            self._add(node, "TRUTHY_GATE", seg.split("\n")[0])
        self.generic_visit(node)


def scan() -> dict:
    rows, files = [], sorted(TOOLS.glob("d_*.py"))
    for f in files:
        try:
            src = f.read_text(encoding="utf-8")
            tree = ast.parse(src)
        except Exception:
            continue
        v = Finder(src, f.name)
        v.visit(tree)
        rows += v.hits
        # BARE_GET — 정규식 보조 (AST 로 잡기 번거로운 형태)
        for i, line in enumerate(src.splitlines(), 1):
            if re.search(r"if\s+\w+\.get\([^)]+\)\s*[:)]", line):
                rows.append({"file": f.name, "fn": "<line>", "line": i,
                             "kind": "BARE_GET", "snippet": line.strip()[:110]})
    by = {}
    for r in rows:
        by[r["kind"]] = by.get(r["kind"], 0) + 1
    return {"n_files": len(files), "n_hits": len(rows), "by_kind": by, "hits": rows,
            "kinds": {
              "FALSE_ONLY": "`is False`/`== False` 만 본다 — None 이 통과한다 (A R147 형태)",
              "TRUTHY_GATE": "`if not x:` 로 None·False·0·\"\"·[] 를 한 덩어리로 접는다",
              "BARE_GET": "`.get()` 결과를 None 검사 없이 조건에 넣는다"},
            "limitation": ("정적 탐지다. 세 형태가 **항상 결함인 것은 아니다** — "
                           "None 이 올 수 없는 자리면 안전하다. **자리를 지목할 뿐 판정하지 않는다**")}


if __name__ == "__main__":
    r = scan()
    print(json.dumps({k: v for k, v in r.items() if k != "hits"}, ensure_ascii=False, indent=1))
    print("\n--- 자리 ---")
    for h in r["hits"]:
        print(f"  {h['kind']:<12} {h['file']}:{h['line']:<5} {h['fn']:<28} {h['snippet']}")
