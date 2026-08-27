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

## Δ46 — declared failure behaviour, demonstrated on a mutated copy and bound to the tool sha (R40 / Δ46-declared / Δ46-exit2 / Δ46-casename)
`../control_failure_demo_c.py` (never touches the live tools) copies `r32_inventory.py` + `fixtures_py/` and `../../c_bus_scan.py` into isolated
temp dirs, applies one mutation per case, runs the copy as a subprocess and measures the **declared** behaviour — for r32 the sha256 of a
pre-seeded `--out` sentinel before/after (R40: exit codes do not survive in files), for the scanner its stdout JSON block. Results go to the
sidecar `../CONTROL_FAILURE_DEMOS_C.json` together with the sha256 of the **live** tool at demo time. Both tools read the sidecar and emit
`failure_behaviour_demo.valid_for_this_commit` = (sidecar tool sha == own sha now) AND (all own cases PASS); any edit to a tool flips it to
`false` (`reason: TOOL_CHANGED_SINCE_DEMO`) until the demonstrator is re-run. Case names say what they demonstrate (Δ46-casename):

| case | tool | mutation | declared behaviour measured |
|---|---|---|---|
| `r32_writes_file_when_controls_pass` | r32 | none (baseline / must_not_flag) | exit 0, sentinel sha changes, written doc carries `failure_behaviour_demo` |
| `r32_writes_no_file_when_control_fails` | r32 | `ctrl_must_flag_ax_node.py` made to raise → `must_flag/task_control_ax_node_silent_none` FAILs | exit 2, sentinel sha unchanged |
| `r32_exits_3_and_writes_no_file_when_target_unusable` | r32 | empty `--target` | exit 3, sentinel sha unchanged |
| `r32_exits_2_did_not_run_on_crash` | r32 | exception injected after the controls | exit 2 + "did not run — read neither as pass nor fail", sentinel unchanged |
| `scanner_emits_index_numbers_when_controls_pass` | scanner | none (baseline) | exit 0, `ruling_record_gaps.status=OK`, all `MAIN_CHECK_KEYS` present, summary counters numeric |
| `scanner_refuses_index_numbers_when_control_fails` | scanner | `R21` appended to the Δ33 control corpus → `positive R21→Δ21` and `Δ33 negative` FAIL | exit 2, status `CONTROLS_FAILED_MAIN_CHECK_REFUSED`, no `MAIN_CHECK_KEYS`, summary counters `n/a` (never 0) |
| `scanner_exits_2_did_not_run_on_crash` | scanner | exception injected in `main` | exit 2 + did-not-run message, no JSON on stdout |

The demonstrator carries its own controls (`demonstrator_controls` in the sidecar, run on a scratch copy of the layout): no sidecar ⇒ both tools
`false/NO_SIDECAR` (must_flag); after the demo ⇒ `true` (must_not_flag); one comment line appended to each tool ⇒ `false/TOOL_CHANGED_SINCE_DEMO`
(must_flag); demo re-run ⇒ `true` (must_not_flag). Limitation: the mutations are the ones C imagined; PASS means the declared behaviour held under
these mutations, not under every defect.

### Exit codes — mapping to A's convention (Δ46-exit2: `0` pass · `1` ran and failed · `2` did not run)
| r32 exit | meaning | A-convention class |
|---|---|---|
| 0 | controls passed, inventory written / printed | 0 |
| 2 | a control FAILed **or** an uncaught exception — nothing written; "did not run — read neither as pass nor fail" | 2 |
| 3 | target unusable (not a dir / no `.py` / unparsable) — nothing written; kept distinct from 2 because the cause is the target, not the tool | 2 (did not run) |
| — | r32 has **no exit 1**: the inventory is a report and makes no pass/fail claim about the target, so "ran and failed" has no referent | 1 unused |

`c_bus_scan.py`: `0` ran, controls passed (findings are report-only, in the JSON) · `1` ran and FAILED (`PARSE_ERRORS_PRESENT`: malformed bus JSON; `selftest` failure) ·
`2` did not run (ruling-index controls failed / index unavailable → main check refused, or uncaught exception) · `3` usage error. Before Δ46 an uncaught
exception in either tool produced Python's default exit 1 — the same code A's convention reads as "ran and failed"; both now wrap `main` and exit 2 with the message.

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
