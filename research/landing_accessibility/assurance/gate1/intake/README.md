# gate1/intake — C's independent R32 seam inventory (CI-19 r2..r5)

Static, offline, never imports the target. Built and frozen **without opening** `docs/v3/R32_APPLICATION_POINTS.md`
or any B out-of-unit note (Δ42 step 1). Step 2 (the freeze) is the commit of `r32_inventory_C.json` + the target sha;
only after that commit may B's list be read and diffed (Δ42 steps 3–4).

| file | role |
|---|---|
| `r32_inventory.py` | the tool. `--target <package_root> [--out r32_inventory_C.json] [--fixtures-dir DIR] [--include-private] [--label TEXT]`. Runs the controls on `fixtures_py/` first; **any control FAIL ⇒ exit 2, nothing written**. Exit 3 = target unusable. Exit 0 = JSON written (or printed when `--out` is omitted). |
| `r32_selftest.py` | S1 controls in-process · S2 fixtures behave as claimed (exec'd from path) · S3 refusal path with two tampered fixture dirs (exit 2, no file) · S4 happy path (exit 0, schema keys) · S5 exit 3 on empty target · S6 smoke on `gate1/comparators` (counts only). Exit 0 only if all pass. Scratch dir: `$R32_SCRATCH` or a `tempfile` dir. |
| `fixtures_py/` | synthetic modules for the controls (see table below). Never imported by production code. |

## Output schema (`r32_inventory.py --out`)
`measured_at_kst`, `target_root`, `target_sha` (+ `target_dirty`; null if not git), `unit_predicate` and `out_of_unit_predicate`
(the exact AST predicates in words), `sites[]` (pass (a), each with `file function line col kind root_params key expr
explicit_default handling evidence flag static_verdict [guard]`), `out_of_unit_candidates[]` (pass (b), `kind expr note`),
`counts` (by kind / by handling / excluded), `per_file`, `functions`, `parse_errors`, `controls[]`, `controls_all_pass`, `ordering_record`.

Handling ∈ `RAISES | SILENT_DEFAULT | UNKNOWN`; `flag = (handling == SILENT_DEFAULT)`; `static_verdict` ∈
`R32_OK | R32_VIOLATION_CANDIDATE | R32_UNKNOWN`. A static SILENT_DEFAULT is a *candidate*: the Δ39 three-state
injection (absent / wrong shape / well-formed) at the COMPLETION SHA is what turns it into a finding.

## Unit of enumeration (pass (a)) — one sentence
An optional-key access on a value that is, or derives from, a parameter of a public function: `x.get(k[, d])`,
`x[k]` under an `in`/`isinstance`/`get`/truthiness/`is None` guard or `try/except KeyError…` or after an early-exit
check on `x`, `getattr(x, k, d)`, `x or {}`/`[]`/`()`/`dict()`/`None`, and parameters typed `| None` / `Optional[…]` /
`Union[…, None]` or defaulted to `None` or a structural literal. Full text: `UNIT_PREDICATE` in the tool (copied into the JSON).

## Out-of-unit search (pass (b)) — a different predicate
`REQUIRED_POSITIONAL_UNGUARDED` (required structural arg, inner key read with no guard), `UNGUARDED_READ_ON_OPTIONAL`,
`GET_ON_CALL_RETURN` (`.get` on a call's return value), `GET_CHAIN` (`.get(...).get(...)`), `KWARGS_READ`, `POP_OR_SETDEFAULT_DEFAULT`,
`GETATTR_UNGUARDED`, `HASATTR_GUARD`. Reported, never graded. If (b) is empty on a target the record says "none found + method", not "none".

## Controls (must_flag / must_not_flag — the words positive/negative are retired, CI-19 r4 iii)
| control | fixture | expectation |
|---|---|---|
| `must_not_flag/measure_surface_shape_raise` | `ctrl_must_not_flag_surface.py::measure_surface` | `.get("raw_features")` handling RAISES, zero flagged sites |
| `must_flag/task_control_ax_node_silent_none` | `ctrl_must_flag_ax_node.py::bind_task` | `.get("ax_node")` handling SILENT_DEFAULT |
| `must_flag/out_of_unit_required_positional_nested` | `ctrl_out_of_unit_nested.py::score` | 0 in-unit sites, ≥2 `REQUIRED_POSITIONAL_UNGUARDED` (`features["envelope"]`, `features["envelope"]["raw"]`) |
| `must_not_flag/clean_no_structural_inputs.{add,shout}` | `ctrl_clean.py` | 0 sites, 0 candidates |
| 12 predicate-coverage controls | `coverage_idioms.py` | one per idiom: getattr default, `or {}`, try/except default vs re-raise, `in` guard with/without else-raise, `Optional=None` return vs `\| None` raise, `**kwargs` → out-of-unit, `.get` on call return → out-of-unit, `.get` chain listed in both, alias derived through `x["k"]` |

Selftest additionally proves the refusal path: tampering either of the two task-fixed controls makes the tool exit 2 and write nothing.

## Ambiguities resolved (recorded so the diff against B can be read)
1. `**kwargs` reads match the (a) predicate textually but are routed to (b) `KWARGS_READ` only — a kwargs bag is a call convention, not a lane-boundary structural input.
2. `.get` on a call's return value (`_lookup(x).get(k)`, or `y = load(x); y.get(k)`) is (b) `GET_ON_CALL_RETURN` even when a root is an argument: the object read is a return value. Struct constructors (`dict(x)`) and methods on the root (`x.copy()`, `x.get()`) stay in (a).
3. `x.get(a, {}).get(b)` is listed in **both**: (a) for each `.get`, (b) `GET_CHAIN` (inner None → AttributeError is a third, unnamed state).
4. Scalar-defaulted params (`timeout=5`) are not structural → excluded and counted; struct-literal defaults (`={}`) are in (a) `PARAM_STRUCT_DEFAULT`.
5. A helper call named like `require|check|validate|assert|ensure|expect|verify` on the root before the access ⇒ `UNKNOWN` (callee not inspected), never RAISES — shape checks hidden in helpers are a known blind spot and must be re-checked dynamically.
6. `.get` with no explicit default whose value flows straight into a non-builtin call ⇒ `UNKNOWN` (callee may raise).
7. Dataflow is an over-approximation (any name assigned from an expression containing a root derives from it, fixpoint over loops); private functions and nested defs are skipped and counted (`--include-private` widens).
8. Method `self`/`cls` are not roots, so `self.x.get(k)` is not a site — instance state is not a lane-boundary input.

## Order record (Δ42)
1. build (a)+(b) at the COMPLETION SHA with this tool — B's list unopened; 2. commit `r32_inventory_C.json` + sha (freeze);
3. read B's `R32_APPLICATION_POINTS.md`; 4. diff: C-only ⇒ B incomplete; B-only ⇒ C narrow (write method); identical ⇒ not evidence
of completeness; both empty ⇒ "none found" + method. If 3 precedes 2, say so and drop the word "independent".
