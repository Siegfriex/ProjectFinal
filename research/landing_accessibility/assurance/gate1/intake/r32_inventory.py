#!/usr/bin/env python3
"""r32_inventory.py — Claude C independent R32 seam inventory (CI-19 r2..r5: Δ39/R32, Δ40-unit, Δ40-R34, Δ42).

Static AST enumeration of "optional-key access inside a structural input" at public functions of a target
package (pass (a), the in-unit inventory) plus a second pass with a DIFFERENT predicate (pass (b), the R34
out-of-unit counterexample search). Every site in (a) carries the statically observed handling of the
absent / wrong-shape case: RAISES | SILENT_DEFAULT | UNKNOWN. SILENT_DEFAULT sites are R32 candidates
(state (1) absent and state (2) wrong shape collapse to the same output).

    r32_inventory.py --target <package_root> [--out r32_inventory_C.json] [--fixtures-dir DIR]
                     [--include-private] [--label TEXT]

Controls (must_flag / must_not_flag, see CONTROLS) run on the synthetic fixtures in fixtures_py/ BEFORE the
target is scanned. If any control fails the tool prints the control table and exits 2 WITHOUT writing --out
(P-67 discipline: a failing control is a harness defect, no claim about the target is made). Exit 3 = target
unusable (not a directory / no .py files / unparsable file). Exit 0 = output written (or printed to stdout).

This tool is built and frozen without reading any B document (Δ42 ordering, step 1). It never imports the
target; it only parses it.

Δ46 declared failure behaviour (R40 / Δ46-declared) — demonstrated on a MUTATED COPY by ../control_failure_demo_c.py,
never on this file: control failure ⇒ exit 2 and the --out file is NOT written (a pre-existing file at --out is left
byte-identical); target unusable ⇒ exit 3 and nothing written; an uncaught exception ⇒ exit 2 + "did not run — read
neither as pass nor fail" and nothing written. Exit-code mapping to A's convention (Δ46-exit2: 0 pass · 1 ran-and-failed ·
2 did-not-run): r32 0 ≡ A 0; r32 2 ≡ A 2 (controls failed = the tool cannot be trusted, so it did not run); r32 3 is also
did-not-run but keeps its own code because the cause is the target, not the tool; r32 has NO exit 1 — the inventory is a
report and makes no pass/fail claim about the target. The output carries `failure_behaviour_demo.valid_for_this_commit`,
true only when the sidecar ../CONTROL_FAILURE_DEMOS_C.json recorded this file's current sha256 and all its cases PASSed.
"""
from __future__ import annotations

import argparse
import ast
import datetime as _dt
import hashlib
import json
import pathlib
import re
import subprocess
import sys
from collections.abc import Callable
from typing import Any

HERE = pathlib.Path(__file__).resolve().parent
DEFAULT_FIXTURES = HERE / "fixtures_py"
KST = _dt.timezone(_dt.timedelta(hours=9), "KST")
DEMO_SIDECAR = HERE.parent / "CONTROL_FAILURE_DEMOS_C.json"   # Δ46/R40: written by ../control_failure_demo_c.py; read-only here
TOOL_REL = "gate1/intake/r32_inventory.py"
DID_NOT_RUN_MSG = "r32_inventory: did not run — read neither as pass nor fail (exit 2)"

RAISES = "RAISES"
SILENT_DEFAULT = "SILENT_DEFAULT"
UNKNOWN = "UNKNOWN"

# ---- the two predicates, in words (copied verbatim into the output) --------------------------------------------
UNIT_PREDICATE = (
    "Pass (a), in-unit. Scope: every public function (name not starting with '_') defined at module level or as a "
    "method of a module-level class, over every *.py under --target (nested defs/lambdas are skipped and counted). "
    "Roots: the function's parameters except self/cls and except a **kwargs parameter, plus every name assigned "
    "(Assign/AnnAssign/AugAssign/walrus/for-target/with-as/comprehension-target) from an expression containing a "
    "root Name that is not the callee of a Call (fixpoint). A site is one of: "
    "(GET) a Call whose func is Attribute(value=X, attr='get') with X derived from a root; "
    "(GUARDED_SUBSCRIPT) a Load Subscript X[k] (k not a slice) with X derived from a root, where the access is "
    "wrapped by an If/IfExp/`and` whose test contains `k in X` / `k not in X` / isinstance(X, ...) / X.get(k) / "
    "X truthiness / X is not None, or by a Try whose handlers catch KeyError/LookupError/IndexError/TypeError/"
    "Exception/bare, or preceded (same function, earlier line, not an ancestor) by an If on X whose branch ends in "
    "return/raise/continue/break; "
    "(GETATTR_DEFAULT) a Call getattr(X, k, default) with three arguments and X derived from a root; "
    "(OR_DEFAULT) a BoolOp `X or D` where X is derived from a root and D is a dict/list/tuple/set display, a "
    "dict()/list()/tuple()/set() call or None; "
    "(PARAM_NONE_DEFAULT / PARAM_OPTIONAL_ANNOTATION / PARAM_STRUCT_DEFAULT) a parameter whose default is None, "
    "whose annotation is `T | None`, Optional[T], Union[..., None] (also inside a string annotation), or whose "
    "default is a dict/list/tuple/set display or constructor call. Scalar defaults (int/str/float/bool/bytes) are "
    "not structural and are excluded (counted). Handling per site: RAISES if a Raise/Assert whose test mentions "
    "the site's root names precedes the access (earlier line or the other branch of an enclosing If, or the except "
    "handler re-raises), or a Raise guarded by a test on the name the site is assigned to follows it; UNKNOWN if "
    "instead a bare call statement named like require|check|validate|assert|ensure|expect|verify receives a root "
    "before the access, or the site's value (with no explicit default) flows directly into a non-builtin call; "
    "otherwise SILENT_DEFAULT. flag = (handling == SILENT_DEFAULT)."
)
OUT_OF_UNIT_PREDICATE = (
    "Pass (b), out-of-unit (R34 counterexample search) — a different predicate from (a): "
    "(REQUIRED_POSITIONAL_UNGUARDED) a Load Subscript X[k] on a root derived from a parameter that has no default "
    "and no Optional annotation, with none of the (a) guards; "
    "(UNGUARDED_READ_ON_OPTIONAL) the same on a root derived from a defaulted/Optional parameter; "
    "(GET_ON_CALL_RETURN) a `.get(...)` whose value is a Call (or a Name assigned from a Call) that is neither a "
    "dict/list/... constructor nor a method on a root-derived object — even if a root is passed as an argument, the "
    "object read is a return value, not the structural input; "
    "(GET_CHAIN) a `.get(...)` whose value is itself a `.get(...)` call; "
    "(KWARGS_READ) any .get/.pop/subscript/`in` read of the **kwargs parameter; "
    "(POP_OR_SETDEFAULT_DEFAULT) X.pop(k, d) / X.setdefault(k, d) on a root-derived X; "
    "(GETATTR_UNGUARDED) getattr(X, k) with two arguments on a root-derived X; "
    "(HASATTR_GUARD) hasattr(X, k) on a root-derived X. Candidates are reported, never classified as R32 "
    "violations by this tool; they are the seams the (a) unit does not capture."
)

STRUCT_CTOR_NAMES = {"dict", "list", "tuple", "set", "frozenset", "OrderedDict", "defaultdict", "deque"}
BUILTIN_CALLS = {
    "len", "str", "int", "float", "bool", "list", "dict", "tuple", "set", "frozenset", "sorted", "reversed",
    "isinstance", "type", "repr", "print", "min", "max", "sum", "any", "all", "enumerate", "zip", "map", "filter",
    "abs", "round", "range", "iter", "next", "id", "hash", "format", "bytes", "getattr", "hasattr", "callable",
}
HELPER_CHECK_RE = re.compile(r"(require|check|validate|assert|ensure|expect|verify)", re.I)
LOOKUP_HANDLERS = {"KeyError", "LookupError", "IndexError", "TypeError", "AttributeError", "Exception", "BaseException"}
TERMINATORS = (ast.Return, ast.Raise, ast.Continue, ast.Break)


# ---- helpers -------------------------------------------------------------------------------------------------------
def now_kst() -> str:
    return _dt.datetime.now(KST).isoformat(timespec="seconds")


def failure_demo_binding(tool_path: pathlib.Path = pathlib.Path(__file__), sidecar: pathlib.Path = DEMO_SIDECAR, tool_rel: str = TOOL_REL) -> dict[str, Any]:
    """R40 binding: valid_for_this_commit iff the sidecar's tool sha256 (recorded at demo time) == this file's sha256 now and all demo cases PASSed."""
    now = hashlib.sha256(tool_path.read_bytes()).hexdigest()
    out: dict[str, Any] = {"rule": "Δ46/R40: failure behaviour demonstrated on a mutated copy by gate1/control_failure_demo_c.py; binding = tool sha256",
                           "sidecar": str(sidecar), "tool_sha256_now": now, "sidecar_present": sidecar.is_file(), "sidecar_tool_sha256": None,
                           "sha_match": False, "cases": [], "demo_all_pass": False, "valid_for_this_commit": False, "reason": None}
    if not sidecar.is_file():
        out["reason"] = "NO_SIDECAR: demonstration never run (or not for this checkout)"
        return out
    try:
        sc = json.loads(sidecar.read_text(encoding="utf-8"))
        cases = [c for c in sc.get("cases", []) if c.get("tool_path") == tool_rel]
    except Exception as e:
        out["reason"] = f"SIDECAR_UNREADABLE: {type(e).__name__}: {e}"[:160]
        return out
    out["sidecar_measured_at_kst"] = sc.get("measured_at_kst")
    out["sidecar_sha256"] = hashlib.sha256(sidecar.read_bytes()).hexdigest()
    out["cases"] = [{"case_name": c.get("case_name"), "result": c.get("result")} for c in cases]
    shas = sorted({c.get("tool_sha256_at_demo") for c in cases})
    if not cases:
        out["reason"] = "NO_CASES_FOR_THIS_TOOL"
        return out
    if len(shas) != 1:
        out["reason"] = f"SIDECAR_INCONSISTENT: {len(shas)} distinct tool shas for one tool"
        return out
    out["sidecar_tool_sha256"] = shas[0]
    out["sha_match"] = shas[0] == now
    out["demo_all_pass"] = all(c.get("result") == "PASS" for c in cases)
    out["valid_for_this_commit"] = out["sha_match"] and out["demo_all_pass"]
    out["reason"] = "OK" if out["valid_for_this_commit"] else ("TOOL_CHANGED_SINCE_DEMO: re-run gate1/control_failure_demo_c.py" if not out["sha_match"] else "DEMO_CASE_FAILED")
    return out


def git_info(root: pathlib.Path) -> dict[str, Any] | None:
    try:
        sha = subprocess.run(["git", "-C", str(root), "rev-parse", "HEAD"], capture_output=True, text=True, check=True).stdout.strip()
        dirty = subprocess.run(["git", "-C", str(root), "status", "--porcelain", "--", str(root)], capture_output=True, text=True, check=True).stdout
        return {"sha": sha, "dirty": bool(dirty.strip())}
    except Exception:
        return None


def attach_parents(tree: ast.AST) -> None:
    for node in ast.walk(tree):
        for child in ast.iter_child_nodes(node):
            child._parent = node  # type: ignore[attr-defined]


def parent(node: ast.AST) -> ast.AST | None:
    return getattr(node, "_parent", None)


def is_none(node: ast.AST | None) -> bool:
    return isinstance(node, ast.Constant) and node.value is None


def unparse(node: ast.AST | None) -> str:
    if node is None:
        return ""
    try:
        return ast.unparse(node)
    except Exception:
        return type(node).__name__


def is_struct_default(node: ast.AST | None) -> bool:
    if node is None:
        return False
    if isinstance(node, (ast.Dict, ast.List, ast.Tuple, ast.Set)):
        return True
    if isinstance(node, ast.Call):
        f = node.func
        name = f.id if isinstance(f, ast.Name) else (f.attr if isinstance(f, ast.Attribute) else "")
        return name in STRUCT_CTOR_NAMES
    return False


def is_scalar_default(node: ast.AST | None) -> bool:
    return isinstance(node, ast.Constant) and node.value is not None and isinstance(node.value, (int, float, str, bool, bytes))


def annotation_is_optional(ann: ast.AST | None) -> bool:
    if ann is None:
        return False
    if isinstance(ann, ast.Constant) and isinstance(ann.value, str):
        try:
            return annotation_is_optional(ast.parse(ann.value, mode="eval").body)
        except SyntaxError:
            return False
    if isinstance(ann, ast.BinOp) and isinstance(ann.op, ast.BitOr):
        return is_none(ann.left) or is_none(ann.right) or annotation_is_optional(ann.left) or annotation_is_optional(ann.right)
    if isinstance(ann, ast.Subscript):
        base = ann.value
        name = base.id if isinstance(base, ast.Name) else (base.attr if isinstance(base, ast.Attribute) else "")
        if name == "Optional":
            return True
        if name == "Union":
            elts = ann.slice.elts if isinstance(ann.slice, ast.Tuple) else [ann.slice]
            return any(is_none(e) or annotation_is_optional(e) for e in elts)
    return False


def callee_name(call: ast.Call) -> str:
    f = call.func
    if isinstance(f, ast.Name):
        return f.id
    if isinstance(f, ast.Attribute):
        return f.attr
    return ""


def iter_fn_nodes(fn: ast.AST):
    """All nodes of a function body, not descending into nested defs / lambdas / classes."""
    def rec(n: ast.AST):
        yield n
        for c in ast.iter_child_nodes(n):
            if isinstance(c, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda, ast.ClassDef)):
                continue
            yield from rec(c)
    for stmt in fn.body:
        yield from rec(stmt)


def names_in_target(t: ast.AST) -> list[str]:
    if isinstance(t, ast.Name):
        return [t.id]
    if isinstance(t, (ast.Tuple, ast.List)):
        return [n for e in t.elts for n in names_in_target(e)]
    if isinstance(t, ast.Starred):
        return names_in_target(t.value)
    return []


def stmt_of(node: ast.AST, fn: ast.AST) -> ast.stmt | None:
    n: ast.AST | None = node
    while n is not None and n is not fn:
        if isinstance(n, ast.stmt):
            return n
        n = parent(n)
    return None


def branch_terminates(body: list[ast.stmt]) -> str | None:
    """'raise' | 'return' | 'exit' | None for the last statement of a branch (one level, plus nested if/else agreement)."""
    if not body:
        return None
    last = body[-1]
    if isinstance(last, ast.Raise):
        return "raise"
    if isinstance(last, ast.Return):
        return "return"
    if isinstance(last, (ast.Continue, ast.Break)):
        return "exit"
    if isinstance(last, ast.If) and last.orelse:
        a, b = branch_terminates(last.body), branch_terminates(last.orelse)
        if a and b:
            return "raise" if "raise" in (a, b) else a
    return None


def branch_contains_raise(body: list[ast.stmt]) -> bool:
    return any(isinstance(n, ast.Raise) for s in body for n in ast.walk(s))


# ---- per-function scanner -----------------------------------------------------------------------------------------
class FunctionScan:
    def __init__(self, fn: ast.FunctionDef | ast.AsyncFunctionDef, qualname: str, rel: str):
        self.fn = fn
        self.qualname = qualname
        self.rel = rel
        self.nodes = list(iter_fn_nodes(fn))
        self.sites: list[dict[str, Any]] = []
        self.oou: list[dict[str, Any]] = []
        self.excluded: dict[str, int] = {"scalar_default_params": 0, "self_cls_params": 0}
        self.params: dict[str, dict[str, Any]] = {}
        self.kwargs_name: str | None = None
        self._collect_params()
        self.origin: dict[str, set[str]] = {p: {p} for p in self.params if not self.params[p]["excluded"]}
        self._derive()
        self.checks = self._collect_checks()
        self.helper_checks = self._collect_helper_checks()

    # -- parameters
    def _collect_params(self) -> None:
        a = self.fn.args
        positional = list(a.posonlyargs) + list(a.args)
        defaults = [None] * (len(positional) - len(a.defaults)) + list(a.defaults)
        entries: list[tuple[ast.arg, ast.AST | None, str]] = [(p, d, "positional") for p, d in zip(positional, defaults, strict=True)]
        entries += [(p, d, "keyword_only") for p, d in zip(a.kwonlyargs, a.kw_defaults, strict=True)]
        if a.vararg:
            entries.append((a.vararg, None, "vararg"))
        if a.kwarg:
            entries.append((a.kwarg, None, "kwargs"))
            self.kwargs_name = a.kwarg.arg
        for i, (p, d, kind) in enumerate(entries):
            excluded = False
            if i == 0 and kind == "positional" and p.arg in ("self", "cls") and self.qualname.count(".") >= 1:
                excluded = True
                self.excluded["self_cls_params"] += 1
            if kind == "kwargs":
                excluded = True  # read through pass (b) KWARGS_READ only
            self.params[p.arg] = {
                "kind": kind, "default": d, "annotation": p.annotation, "excluded": excluded,
                "optional_annotation": annotation_is_optional(p.annotation),
                "required": d is None and kind in ("positional", "keyword_only") and not annotation_is_optional(p.annotation),
            }

    # -- dataflow: names derived from roots
    def derives(self, e: ast.AST | None) -> set[str]:
        """Root parameters an expression derives from (empty set = not derived)."""
        if e is None:
            return set()
        out: set[str] = set()
        for n in ast.walk(e):
            if isinstance(n, ast.Name) and n.id in self.origin:
                p = parent(n)
                if isinstance(p, ast.Call) and p.func is n:
                    continue
                out |= self.origin[n.id]
        return out

    def _derive(self) -> None:
        changed = True
        while changed:
            changed = False
            for n in self.nodes:
                src: ast.AST | None = None
                targets: list[ast.AST] = []
                if isinstance(n, ast.Assign):
                    src, targets = n.value, list(n.targets)
                elif (isinstance(n, ast.AnnAssign) and n.value is not None) or isinstance(n, (ast.AugAssign, ast.NamedExpr)):
                    src, targets = n.value, [n.target]
                elif isinstance(n, (ast.For, ast.AsyncFor, ast.comprehension)):
                    src, targets = n.iter, [n.target]
                elif isinstance(n, ast.withitem) and n.optional_vars is not None:
                    src, targets = n.context_expr, [n.optional_vars]
                if src is None:
                    continue
                roots = self.derives(src)
                if not roots:
                    continue
                for name in (nm for t in targets for nm in names_in_target(t)):
                    if name in self.params and self.params[name]["excluded"]:
                        continue
                    if name not in self.origin or not roots <= self.origin[name]:
                        self.origin.setdefault(name, set()).update(roots)
                        changed = True

    # -- shape checks: If nodes whose test mentions derived names and whose branch terminates
    def _collect_checks(self) -> list[dict[str, Any]]:
        checks = []
        for n in self.nodes:
            if isinstance(n, ast.If):
                names = self.derives(n.test)
                test_names = {x.id for x in ast.walk(n.test) if isinstance(x, ast.Name)}
                if not names and not test_names:
                    continue
                for branch, body in (("body", n.body), ("orelse", n.orelse)):
                    term = branch_terminates(body)
                    if term == "return" and branch_contains_raise(body):
                        term = "raise"
                    if term:
                        checks.append({"node": n, "branch": branch, "term": term, "roots": names, "names": test_names, "line": n.lineno})
            elif isinstance(n, ast.Assert):
                names = self.derives(n.test)
                test_names = {x.id for x in ast.walk(n.test) if isinstance(x, ast.Name)}
                if names or test_names:
                    checks.append({"node": n, "branch": "assert", "term": "raise", "roots": names, "names": test_names, "line": n.lineno})
        return checks

    def _collect_helper_checks(self) -> list[dict[str, Any]]:
        out = []
        for n in self.nodes:
            if isinstance(n, ast.Expr) and isinstance(n.value, ast.Call) and HELPER_CHECK_RE.search(callee_name(n.value) or ""):
                roots = set()
                for a in list(n.value.args) + [k.value for k in n.value.keywords]:
                    roots |= self.derives(a)
                if roots:
                    out.append({"line": n.lineno, "roots": roots, "callee": callee_name(n.value)})
        return out

    # -- guards around a subscript
    def _guard_kind(self, test: ast.AST, value_roots: set[str], value_names: set[str]) -> str | None:
        for n in ast.walk(test):
            if isinstance(n, ast.Compare) and len(n.ops) == 1:
                op = n.ops[0]
                if isinstance(op, (ast.In, ast.NotIn)) and (self.derives(n.comparators[0]) & value_roots):
                    return "membership"
                if isinstance(op, (ast.Is, ast.IsNot)) and is_none(n.comparators[0]) and (self.derives(n.left) & value_roots):
                    return "none_check"
            if isinstance(n, ast.Call):
                cn = callee_name(n)
                if cn == "isinstance" and n.args and (self.derives(n.args[0]) & value_roots):
                    return "isinstance"
                if cn == "get" and isinstance(n.func, ast.Attribute) and (self.derives(n.func.value) & value_roots):
                    return "get_truthy"
            if isinstance(n, ast.Name) and n.id in value_names and n.id in self.origin:
                return "truthy"
        return None

    def _polarity(self, test: ast.AST) -> bool:
        """True if the *body* branch is the safe one (test asserts presence)."""
        neg = False
        t = test
        while isinstance(t, ast.UnaryOp) and isinstance(t.op, ast.Not):
            neg = not neg
            t = t.operand
        for n in ast.walk(t):
            if isinstance(n, ast.Compare) and len(n.ops) == 1 and isinstance(n.ops[0], (ast.NotIn, ast.Is)):
                if isinstance(n.ops[0], ast.Is) and not is_none(n.comparators[0]):
                    continue
                return neg
            if isinstance(n, ast.UnaryOp) and isinstance(n.op, ast.Not):
                return neg  # `k in x and not y` — keep simple
        return not neg

    def enclosing_guard(self, node: ast.AST) -> dict[str, Any] | None:
        value_roots = self.derives(node.value) if isinstance(node, ast.Subscript) else self.derives(node)
        value_names = {x.id for x in ast.walk(node) if isinstance(x, ast.Name)}
        child: ast.AST = node
        p = parent(node)
        while p is not None and p is not self.fn:
            if isinstance(p, ast.If):
                in_body = any(child is s for s in p.body)
                in_else = any(child is s for s in p.orelse)
                if in_body or in_else:
                    gk = self._guard_kind(p.test, value_roots, value_names)
                    if gk:
                        safe_in_body = self._polarity(p.test)
                        if (safe_in_body and in_body) or (not safe_in_body and in_else):
                            other = p.orelse if in_body else p.body
                            return {"guard": gk, "line": p.lineno, "other_branch": branch_terminates(other) or ("absent" if not other else "falls_through")}
            elif isinstance(p, ast.IfExp):
                gk = self._guard_kind(p.test, value_roots, value_names)
                if gk and (child is p.body or child is p.orelse):
                    safe_in_body = self._polarity(p.test)
                    if (safe_in_body and child is p.body) or (not safe_in_body and child is p.orelse):
                        return {"guard": gk, "line": p.lineno, "other_branch": "expression"}
            elif isinstance(p, ast.BoolOp) and isinstance(p.op, ast.And):
                idx = next((i for i, v in enumerate(p.values) if v is child), None)
                if idx:
                    for earlier in p.values[:idx]:
                        gk = self._guard_kind(earlier, value_roots, value_names)
                        if gk and self._polarity(earlier):
                            return {"guard": gk, "line": p.lineno, "other_branch": "expression"}
            elif isinstance(p, ast.Try):
                if any(child is s for s in p.body):
                    names = set()
                    for h in p.handlers:
                        if h.type is None:
                            names.add("bare")
                        else:
                            for t in (h.type.elts if isinstance(h.type, ast.Tuple) else [h.type]):
                                names.add(t.id if isinstance(t, ast.Name) else (t.attr if isinstance(t, ast.Attribute) else ""))
                    if names & (LOOKUP_HANDLERS | {"bare"}):
                        handler_raises = any(branch_contains_raise(h.body) for h in p.handlers)
                        return {"guard": "try_except", "line": p.lineno, "handlers": sorted(names),
                                "other_branch": "raise" if handler_raises else "handled"}
            child, p = p, parent(p)
        return None

    def preceding_check(self, node: ast.AST, roots: set[str]) -> dict[str, Any] | None:
        """Nearest earlier If/Assert on the same roots that is not an ancestor of node (early exit)."""
        best = None
        for c in self.checks:
            if c["line"] >= getattr(node, "lineno", 0) or not (c["roots"] & roots):
                continue
            if any(a is c["node"] for a in self._ancestors(node)):
                continue
            if c["branch"] == "orelse" and c["node"].orelse and c["node"].orelse[-1].lineno >= getattr(node, "lineno", 0):
                continue
            if best is None or c["term"] == "raise":
                best = c
        return best

    def post_check(self, node: ast.AST) -> dict[str, Any] | None:
        """If the site's value is assigned to a name, a later If on that name that terminates."""
        st = stmt_of(node, self.fn)
        if not isinstance(st, (ast.Assign, ast.AnnAssign, ast.NamedExpr)) and not isinstance(parent(node), ast.NamedExpr):
            return None
        if isinstance(st, ast.Assign):
            targets = [nm for t in st.targets for nm in names_in_target(t)]
        elif isinstance(st, ast.AnnAssign):
            targets = names_in_target(st.target)
        else:
            p = parent(node)
            targets = [p.target.id] if isinstance(p, ast.NamedExpr) and isinstance(p.target, ast.Name) else []
        if not targets:
            return None
        for c in self.checks:
            if c["line"] > node.lineno and (set(targets) & c["names"]):
                return c
        return None

    def _ancestors(self, node: ast.AST):
        p = parent(node)
        while p is not None and p is not self.fn:
            yield p
            p = parent(p)

    def flows_into_call(self, node: ast.AST) -> str | None:
        p = parent(node)
        if isinstance(p, ast.Call) and p.func is not node and (node in p.args or any(k.value is node for k in p.keywords)):
            cn = callee_name(p)
            if cn not in BUILTIN_CALLS and not (isinstance(p.func, ast.Attribute) and self.derives(p.func.value)):
                return cn
        return None

    # -- classification
    def classify(self, node: ast.AST, roots: set[str], has_default: bool, guard: dict[str, Any] | None) -> tuple[str, str]:
        if guard:
            ob = guard.get("other_branch")
            if ob == "raise":
                return RAISES, f"guard {guard['guard']} at line {guard['line']}, other branch raises"
            if ob in ("return", "exit", "handled", "absent", "falls_through", "expression"):
                pre = self.preceding_check(node, roots)
                if pre and pre["term"] == "raise":
                    return RAISES, f"shape check {pre['branch']} at line {pre['line']} raises before access"
                return SILENT_DEFAULT, f"guard {guard['guard']} at line {guard['line']}, other branch {ob}"
        pre = self.preceding_check(node, roots)
        if pre and pre["term"] == "raise":
            return RAISES, f"shape check {pre['branch']} at line {pre['line']} raises before access"
        post = self.post_check(node)
        if post and post["term"] == "raise":
            return RAISES, f"result checked at line {post['line']} and raised"
        helpers = [h for h in self.helper_checks if h["line"] < getattr(node, "lineno", 0) and (h["roots"] & roots)]
        if helpers:
            return UNKNOWN, f"helper check {helpers[0]['callee']}() at line {helpers[0]['line']} on root; callee not inspected"
        if pre and pre["term"] in ("return", "exit"):
            return SILENT_DEFAULT, f"early exit {pre['term']} at line {pre['line']} before access"
        if post and post["term"] in ("return", "exit"):
            return SILENT_DEFAULT, f"result checked at line {post['line']} then {post['term']}"
        if not has_default:
            callee = self.flows_into_call(node)
            if callee:
                return UNKNOWN, f"value flows into {callee}() without explicit default; callee not inspected"
        return SILENT_DEFAULT, "default/None used, no raise reachable on the wrong-shape path"

    def _site(self, node: ast.AST, kind: str, roots: set[str], key: str | None, has_default: bool, default: str | None,
              guard: dict[str, Any] | None = None) -> dict[str, Any]:
        handling, evidence = self.classify(node, roots, has_default, guard)
        expr = unparse(node)
        line = getattr(node, "lineno", self.fn.lineno)
        col = getattr(node, "col_offset", 0)
        sid = hashlib.sha1(f"{self.rel}:{self.qualname}:{kind}:{line}:{col}:{expr}".encode()).hexdigest()[:12]
        d = {
            "id": sid, "file": self.rel, "function": self.qualname, "line": line, "col": col, "kind": kind,
            "root_params": sorted(roots), "key": key, "expr": expr, "explicit_default": default, "handling": handling,
            "evidence": evidence, "flag": handling == SILENT_DEFAULT,
            "static_verdict": {RAISES: "R32_OK", SILENT_DEFAULT: "R32_VIOLATION_CANDIDATE", UNKNOWN: "R32_UNKNOWN"}[handling],
        }
        if guard:
            d["guard"] = dict(guard)
        return d

    def _oou(self, node: ast.AST, kind: str, roots: set[str], note: str) -> dict[str, Any]:
        expr = unparse(node)
        line = getattr(node, "lineno", self.fn.lineno)
        col = getattr(node, "col_offset", 0)
        sid = hashlib.sha1(f"oou:{self.rel}:{self.qualname}:{kind}:{line}:{col}:{expr}".encode()).hexdigest()[:12]
        return {"id": sid, "file": self.rel, "function": self.qualname, "line": line, "col": col, "kind": kind,
                "root_params": sorted(roots), "expr": expr, "note": note}

    def run(self) -> None:
        self._param_sites()
        for n in self.nodes:
            if isinstance(n, ast.Call):
                self._call(n)
            elif isinstance(n, ast.Subscript) and isinstance(n.ctx, ast.Load) and not isinstance(n.slice, ast.Slice):
                self._subscript(n)
            elif isinstance(n, ast.BoolOp) and isinstance(n.op, ast.Or):
                self._or_default(n)
            elif (isinstance(n, ast.Compare) and self.kwargs_name and len(n.ops) == 1 and isinstance(n.ops[0], (ast.In, ast.NotIn))
                  and isinstance(n.comparators[0], ast.Name) and n.comparators[0].id == self.kwargs_name):
                self.oou.append(self._oou(n, "KWARGS_READ", set(), "membership test on **kwargs"))

    def _param_sites(self) -> None:
        for name, p in self.params.items():
            if p["excluded"]:
                continue
            d = p["default"]
            if is_none(d):
                kind = "PARAM_NONE_DEFAULT"
            elif p["optional_annotation"]:
                kind = "PARAM_OPTIONAL_ANNOTATION"
            elif is_struct_default(d):
                kind = "PARAM_STRUCT_DEFAULT"
            elif d is not None:
                if is_scalar_default(d):
                    self.excluded["scalar_default_params"] += 1
                continue
            else:
                continue
            arg_node = next(a for a in ast.walk(self.fn.args) if isinstance(a, ast.arg) and a.arg == name)
            handling, evidence = self._param_handling(name)
            sid = hashlib.sha1(f"{self.rel}:{self.qualname}:{kind}:{name}".encode()).hexdigest()[:12]
            self.sites.append({
                "id": sid, "file": self.rel, "function": self.qualname, "line": arg_node.lineno, "col": arg_node.col_offset,
                "kind": kind, "root_params": [name], "key": name, "expr": f"{name}: {unparse(p['annotation']) or '?'} = {unparse(d) or '<required>'}",
                "explicit_default": unparse(d) or None, "handling": handling, "evidence": evidence, "flag": handling == SILENT_DEFAULT,
                "static_verdict": {RAISES: "R32_OK", SILENT_DEFAULT: "R32_VIOLATION_CANDIDATE", UNKNOWN: "R32_UNKNOWN"}[handling],
            })

    def _param_handling(self, name: str) -> tuple[str, str]:
        mine = [c for c in self.checks if name in c["roots"] or name in c["names"]]
        raises = [c for c in mine if c["term"] == "raise"]
        if raises:
            return RAISES, f"check on {name} at line {raises[0]['line']} raises"
        exits = [c for c in mine if c["term"] in ("return", "exit")]
        if exits:
            return SILENT_DEFAULT, f"check on {name} at line {exits[0]['line']} returns/exits without raising"
        for n in self.nodes:
            if isinstance(n, ast.BoolOp) and isinstance(n.op, ast.Or) and isinstance(n.values[0], ast.Name) and n.values[0].id == name:
                return SILENT_DEFAULT, f"`{name} or ...` default at line {n.lineno}"
        used = any(isinstance(n, ast.Name) and n.id == name for n in self.nodes)
        if not used:
            return UNKNOWN, f"{name} never read in the body"
        return UNKNOWN, f"{name} used without a None/shape check"

    def _call(self, n: ast.Call) -> None:
        cn = callee_name(n)
        f = n.func
        if isinstance(f, ast.Attribute) and cn in ("get", "pop", "setdefault"):
            value = f.value
            if self.kwargs_name and isinstance(value, ast.Name) and value.id == self.kwargs_name:
                self.oou.append(self._oou(n, "KWARGS_READ", set(), f"**{self.kwargs_name}.{cn}()"))
                return
            roots = self.derives(value)
            if cn == "get":
                if isinstance(value, ast.Call) and callee_name(value) == "get" and self.derives(value.func.value if isinstance(value.func, ast.Attribute) else value):
                    self.oou.append(self._oou(n, "GET_CHAIN", roots, "outer .get on the result of an inner .get; inner None → AttributeError, not a shape error"))
                ret = self._call_return_source(value)
                if ret:
                    self.oou.append(self._oou(n, "GET_ON_CALL_RETURN", roots, f".get on the return value of {ret}() — the object read is a call result, not the structural input"))
                    return
                if roots:
                    key = unparse(n.args[0]) if n.args else None
                    default = unparse(n.args[1]) if len(n.args) > 1 else None
                    self.sites.append(self._site(n, "GET", roots, key, len(n.args) > 1, default))
            elif roots and len(n.args) > 1:
                self.oou.append(self._oou(n, "POP_OR_SETDEFAULT_DEFAULT", roots, f".{cn}(k, default) — optional-key idiom outside the (a) unit"))
        elif cn == "getattr" and n.args:
            roots = self.derives(n.args[0])
            if not roots:
                return
            key = unparse(n.args[1]) if len(n.args) > 1 else None
            if len(n.args) >= 3:
                self.sites.append(self._site(n, "GETATTR_DEFAULT", roots, key, True, unparse(n.args[2])))
            else:
                self.oou.append(self._oou(n, "GETATTR_UNGUARDED", roots, "two-argument getattr on a root: AttributeError, no shape distinction"))
        elif cn == "hasattr" and n.args and self.derives(n.args[0]):
            self.oou.append(self._oou(n, "HASATTR_GUARD", self.derives(n.args[0]), "hasattr guard on a root"))

    def _is_foreign_call(self, c: ast.AST) -> str | None:
        """Callee name if `c` is a Call that is neither a struct constructor nor a method on a root-derived object."""
        if not isinstance(c, ast.Call):
            return None
        cn = callee_name(c)
        if cn in STRUCT_CTOR_NAMES:
            return None
        if isinstance(c.func, ast.Attribute) and self.derives(c.func.value):
            return None  # x.copy(), x.get(...) — still the structural input
        return cn or "<call>"

    def _call_return_source(self, value: ast.AST) -> str | None:
        f = self._is_foreign_call(value)
        if f:
            return f
        if isinstance(value, ast.Name):
            for n in self.nodes:
                if isinstance(n, ast.Assign) and any(value.id in names_in_target(t) for t in n.targets):
                    f = self._is_foreign_call(n.value)
                    if f:
                        return f
        return None

    def _subscript(self, n: ast.Subscript) -> None:
        if self.kwargs_name and isinstance(n.value, ast.Name) and n.value.id == self.kwargs_name:
            self.oou.append(self._oou(n, "KWARGS_READ", set(), f"**{self.kwargs_name}[k]"))
            return
        roots = self.derives(n.value)
        if not roots:
            return
        if isinstance(parent(n), (ast.Delete,)):
            return
        guard = self.enclosing_guard(n)
        key = unparse(n.slice)
        if guard:
            self.sites.append(self._site(n, "GUARDED_SUBSCRIPT", roots, key, False, None, guard))
            return
        pre = self.preceding_check(n, roots)
        if pre and pre["term"] in ("return", "exit", "raise") and self._check_is_membership_or_shape(pre["node"]):
            guard = {"guard": f"preceding_{pre['term']}", "line": pre["line"], "other_branch": pre["term"]}
            self.sites.append(self._site(n, "GUARDED_SUBSCRIPT", roots, key, False, None, guard))
            return
        required = any(self.params.get(r, {}).get("required") for r in roots)
        kind = "REQUIRED_POSITIONAL_UNGUARDED" if required else "UNGUARDED_READ_ON_OPTIONAL"
        self.oou.append(self._oou(n, kind, roots, "subscript read with no in/try/isinstance guard and no preceding shape check"))

    def _check_is_membership_or_shape(self, if_node: ast.AST) -> bool:
        test = if_node.test if isinstance(if_node, ast.If) else getattr(if_node, "test", None)
        if test is None:
            return False
        for x in ast.walk(test):
            if isinstance(x, ast.Compare) and len(x.ops) == 1 and isinstance(x.ops[0], (ast.In, ast.NotIn, ast.Is, ast.IsNot)):
                return True
            if isinstance(x, ast.Call) and callee_name(x) in ("isinstance", "get", "hasattr"):
                return True
            if isinstance(x, ast.Name) and x.id in self.origin:
                return True
        return False

    def _or_default(self, n: ast.BoolOp) -> None:
        first = n.values[0]
        roots = self.derives(first)
        if not roots:
            return
        rest = n.values[1:]
        if any(is_struct_default(v) or is_none(v) for v in rest):
            self.sites.append(self._site(n, "OR_DEFAULT", roots, None, True, unparse(rest[-1])))


# ---- module / package walk ----------------------------------------------------------------------------------------
def public_functions(tree: ast.Module, include_private: bool):
    skipped = 0
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if include_private or not node.name.startswith("_"):
                yield node, node.name
            else:
                skipped += 1
        elif isinstance(node, ast.ClassDef):
            for m in node.body:
                if isinstance(m, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    if include_private or not m.name.startswith("_"):
                        yield m, f"{node.name}.{m.name}"
                    else:
                        skipped += 1
    yield None, skipped  # sentinel carrying the skip count


def scan_tree(root: pathlib.Path, include_private: bool = False) -> dict[str, Any]:
    if not root.is_dir():
        raise SystemExit(f"target is not a directory: {root}")
    files = sorted(p for p in root.rglob("*.py") if "__pycache__" not in p.parts and not any(part.startswith(".") for part in p.relative_to(root).parts))
    if not files:
        raise SystemExit(f"no .py files under {root}")
    sites: list[dict[str, Any]] = []
    oou: list[dict[str, Any]] = []
    per_file: dict[str, dict[str, int]] = {}
    functions: list[dict[str, Any]] = []
    excluded = {"private_functions": 0, "nested_defs": 0, "scalar_default_params": 0, "self_cls_params": 0}
    parse_errors: list[dict[str, str]] = []
    for f in files:
        rel = str(f.relative_to(root))
        try:
            tree = ast.parse(f.read_text(encoding="utf-8"), filename=rel)
        except (SyntaxError, UnicodeDecodeError) as e:
            parse_errors.append({"file": rel, "error": f"{type(e).__name__}: {e}"})
            continue
        attach_parents(tree)
        per_file[rel] = {"functions": 0, "sites": 0, "flagged": 0, "out_of_unit": 0}
        for fn, name in public_functions(tree, include_private):
            if fn is None:
                excluded["private_functions"] += name
                continue
            excluded["nested_defs"] += sum(1 for n in ast.walk(fn) if n is not fn and isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)))
            sc = FunctionScan(fn, name, rel)
            sc.run()
            for k in ("scalar_default_params", "self_cls_params"):
                excluded[k] += sc.excluded[k]
            sites.extend(sc.sites)
            oou.extend(sc.oou)
            per_file[rel]["functions"] += 1
            per_file[rel]["sites"] += len(sc.sites)
            per_file[rel]["flagged"] += sum(1 for s in sc.sites if s["flag"])
            per_file[rel]["out_of_unit"] += len(sc.oou)
            functions.append({"file": rel, "function": name, "line": fn.lineno, "sites": len(sc.sites),
                              "flagged": sum(1 for s in sc.sites if s["flag"]), "out_of_unit": len(sc.oou),
                              "roots": sorted(p for p, v in sc.params.items() if not v["excluded"])})
    key = lambda s: (s["file"], s["line"], s["col"], s["kind"])  # noqa: E731
    sites.sort(key=key)
    oou.sort(key=key)
    by = lambda rows, k: dict(sorted({v: sum(1 for r in rows if r[k] == v) for v in {r[k] for r in rows}}.items()))  # noqa: E731
    counts = {
        "files": len(files), "files_parsed": len(files) - len(parse_errors), "functions_scanned": len(functions),
        "sites": len(sites), "sites_flagged": sum(1 for s in sites if s["flag"]),
        "sites_by_kind": by(sites, "kind"), "sites_by_handling": by(sites, "handling"),
        "out_of_unit_candidates": len(oou), "out_of_unit_by_kind": by(oou, "kind"),
        "excluded": excluded,
    }
    return {"sites": sites, "out_of_unit_candidates": oou, "counts": counts, "per_file": per_file, "functions": functions,
            "parse_errors": parse_errors}


# ---- controls -----------------------------------------------------------------------------------------------------
def _fn(rows: list[dict[str, Any]], file: str, function: str) -> list[dict[str, Any]]:
    return [r for r in rows if r["file"] == file and r["function"] == function]


def _ctrl(name: str, file: str, function: str, expect: Callable[[list[dict[str, Any]], list[dict[str, Any]]], tuple[bool, str]]) -> dict[str, Any]:
    return {"name": name, "file": file, "function": function, "expect": expect}


def _must_flag_kind(kind: str, key: str | None = None, handling: str = SILENT_DEFAULT):
    def f(sites, oou):
        hit = [s for s in sites if s["kind"] == kind and (key is None or s["key"] == key)]
        ok = any(s["handling"] == handling for s in hit)
        return ok, f"{kind}{'[' + key + ']' if key else ''} handling={[s['handling'] for s in hit]} (need {handling})"
    return f


def _must_not_flag_fn(require_kind: str | None = None, require_key: str | None = None):
    def f(sites, oou):
        flagged = [s for s in sites if s["flag"]]
        if require_kind:
            hit = [s for s in sites if s["kind"] == require_kind and (require_key is None or s["key"] == require_key)]
            if not any(s["handling"] == RAISES for s in hit):
                return False, f"expected a {require_kind}{'[' + require_key + ']' if require_key else ''} site with handling RAISES; got {[s['handling'] for s in hit]}"
        return not flagged, f"flagged={[(s['kind'], s['key'], s['handling']) for s in flagged]} (need none)"
    return f


def _oou_only(kind: str, min_n: int = 1):
    def f(sites, oou):
        hit = [o for o in oou if o["kind"] == kind]
        return (len(sites) == 0 and len(hit) >= min_n), f"in-unit sites={len(sites)} (need 0), out_of_unit[{kind}]={len(hit)} (need ≥{min_n})"
    return f


def _clean():
    def f(sites, oou):
        return (len(sites) == 0 and len(oou) == 0), f"sites={len(sites)} out_of_unit={len(oou)} (need 0/0)"
    return f


CONTROLS: list[dict[str, Any]] = [
    # the four fixed by the task
    _ctrl("must_not_flag/measure_surface_shape_raise", "ctrl_must_not_flag_surface.py", "measure_surface", _must_not_flag_fn("GET", "'raw_features'")),
    _ctrl("must_flag/task_control_ax_node_silent_none", "ctrl_must_flag_ax_node.py", "bind_task", _must_flag_kind("GET", "'ax_node'")),
    _ctrl("must_flag/out_of_unit_required_positional_nested", "ctrl_out_of_unit_nested.py", "score", _oou_only("REQUIRED_POSITIONAL_UNGUARDED", 2)),
    _ctrl("must_not_flag/clean_no_structural_inputs.add", "ctrl_clean.py", "add", _clean()),
    _ctrl("must_not_flag/clean_no_structural_inputs.shout", "ctrl_clean.py", "shout", _clean()),
    # predicate coverage, one per idiom named in CI-19 r3 / r4
    _ctrl("must_flag/getattr_default_silent", "coverage_idioms.py", "getattr_default_silent", _must_flag_kind("GETATTR_DEFAULT", "'target_selector'")),
    _ctrl("must_flag/or_empty_dict_default", "coverage_idioms.py", "or_empty_dict_default", _must_flag_kind("OR_DEFAULT")),
    _ctrl("must_flag/try_keyerror_default", "coverage_idioms.py", "try_keyerror_default", _must_flag_kind("GUARDED_SUBSCRIPT", "'family_id'")),
    _ctrl("must_not_flag/try_keyerror_reraise", "coverage_idioms.py", "try_keyerror_reraise", _must_not_flag_fn("GUARDED_SUBSCRIPT", "'family_id'")),
    _ctrl("must_not_flag/in_guard_else_raise", "coverage_idioms.py", "in_guard_else_raise", _must_not_flag_fn("GUARDED_SUBSCRIPT", "'status'")),
    _ctrl("must_flag/in_guard_no_else", "coverage_idioms.py", "in_guard_no_else", _must_flag_kind("GUARDED_SUBSCRIPT", "'status'")),
    _ctrl("must_flag/optional_param_none_return", "coverage_idioms.py", "optional_param_none_return", _must_flag_kind("PARAM_NONE_DEFAULT", "ax_node")),
    _ctrl("must_not_flag/pipe_none_param_raises", "coverage_idioms.py", "pipe_none_param_raises", _must_not_flag_fn("PARAM_OPTIONAL_ANNOTATION", "ax_node")),
    _ctrl("must_flag/kwargs_read_is_out_of_unit", "coverage_idioms.py", "kwargs_read", _oou_only("KWARGS_READ")),
    _ctrl("must_flag/get_on_call_return_is_out_of_unit", "coverage_idioms.py", "get_on_call_return", _oou_only("GET_ON_CALL_RETURN")),
    _ctrl("must_flag/get_chain_listed_in_both", "coverage_idioms.py", "get_chain",
          lambda s, o: (any(x["kind"] == "GET" and x["flag"] for x in s) and any(x["kind"] == "GET_CHAIN" for x in o),
                        f"in-unit GET flagged={[x['key'] for x in s if x['flag']]}, out_of_unit GET_CHAIN={sum(1 for x in o if x['kind'] == 'GET_CHAIN')}")),
    _ctrl("must_flag/derived_alias_get", "coverage_idioms.py", "derived_alias", _must_flag_kind("GET", "'scroll_states'")),
]


def run_controls(fixtures_dir: pathlib.Path) -> tuple[bool, list[dict[str, Any]], dict[str, Any]]:
    scan = scan_tree(fixtures_dir, include_private=False)
    results = []
    all_ok = True
    for c in CONTROLS:
        sites = _fn(scan["sites"], c["file"], c["function"])
        oou = _fn(scan["out_of_unit_candidates"], c["file"], c["function"])
        present = any(f["file"] == c["file"] and f["function"] == c["function"] for f in scan["functions"])
        if not present:
            ok, detail = False, "fixture function not found (fixture missing or private)"
        else:
            ok, detail = c["expect"](sites, oou)
        all_ok &= ok
        results.append({"name": c["name"], "fixture": f"{c['file']}::{c['function']}", "result": "PASS" if ok else "FAIL",
                        "sites": len(sites), "flagged": sum(1 for s in sites if s["flag"]), "out_of_unit": len(oou), "detail": detail})
    return all_ok, results, scan


def build(target: pathlib.Path, fixtures_dir: pathlib.Path, include_private: bool, label: str | None) -> tuple[int, dict[str, Any] | None, list[dict[str, Any]]]:
    ok, controls, _ = run_controls(fixtures_dir)
    if not ok:
        return 2, None, controls
    scan = scan_tree(target, include_private)
    git = git_info(target)
    out = {
        "tool": "r32_inventory.py", "plane": "C", "ruling_refs": ["CI-19 r2 Δ39/R32", "CI-19 r3 Δ40-unit", "CI-19 r4 Δ40-R34", "CI-19 r5 Δ42"],
        "measured_at_kst": now_kst(), "label": label,
        "target_root": str(target), "target_sha": git["sha"] if git else None, "target_dirty": git["dirty"] if git else None,
        "unit_predicate": UNIT_PREDICATE, "out_of_unit_predicate": OUT_OF_UNIT_PREDICATE,
        "include_private": include_private,
        "sites": scan["sites"], "out_of_unit_candidates": scan["out_of_unit_candidates"],
        "counts": scan["counts"], "per_file": scan["per_file"], "functions": scan["functions"], "parse_errors": scan["parse_errors"],
        "controls": controls, "controls_all_pass": True, "fixtures_dir": str(fixtures_dir),
        "ordering_record": "built without reading docs/v3/R32_APPLICATION_POINTS.md or any B out-of-unit note (Δ42 step 1)",
        "failure_behaviour_demo": failure_demo_binding(),
    }
    return 0, out, controls


def print_controls(controls: list[dict[str, Any]], stream=sys.stderr) -> None:
    w = max(len(c["name"]) for c in controls)
    for c in controls:
        print(f"  {c['result']:4} {c['name']:<{w}} sites={c['sites']} flagged={c['flagged']} oou={c['out_of_unit']}  {c['detail']}", file=stream)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--target", required=True, type=pathlib.Path, help="package root to inventory (never imported, only parsed)")
    ap.add_argument("--out", type=pathlib.Path, help="output JSON path; omitted = print JSON to stdout")
    ap.add_argument("--fixtures-dir", type=pathlib.Path, default=DEFAULT_FIXTURES, help="control fixtures (default: fixtures_py/)")
    ap.add_argument("--include-private", action="store_true", help="also scan functions whose name starts with '_'")
    ap.add_argument("--label", help="free-text label stored in the output (e.g. COMPLETION sha tag)")
    a = ap.parse_args(argv)
    try:
        code, out, controls = build(a.target.resolve(), a.fixtures_dir.resolve(), a.include_private, a.label)
    except SystemExit as e:
        print(f"r32_inventory: target error: {e}", file=sys.stderr)
        return 3
    print(f"r32_inventory controls ({sum(1 for c in controls if c['result'] == 'PASS')}/{len(controls)} PASS):", file=sys.stderr)
    print_controls(controls)
    if code != 0:
        print("r32_inventory: CONTROL FAILURE — inventory not reported, nothing written (exit 2)", file=sys.stderr)
        return code
    text = json.dumps(out, ensure_ascii=False, indent=1, sort_keys=False)
    if a.out:
        a.out.parent.mkdir(parents=True, exist_ok=True)
        a.out.write_text(text + "\n", encoding="utf-8")
        c = out["counts"]
        print(f"r32_inventory: wrote {a.out} — target_sha={out['target_sha']} functions={c['functions_scanned']} sites={c['sites']} "
              f"flagged={c['sites_flagged']} out_of_unit={c['out_of_unit_candidates']}", file=sys.stderr)
    else:
        print(text)
    return 0


if __name__ == "__main__":
    try:
        _rc = main()
    except Exception:  # Δ46-exit2: an uncaught exception is "did not run", never exit 1 (which A's convention reads as "ran and failed")
        import traceback
        traceback.print_exc()
        print(DID_NOT_RUN_MSG, file=sys.stderr)
        _rc = 2
    sys.exit(_rc)
