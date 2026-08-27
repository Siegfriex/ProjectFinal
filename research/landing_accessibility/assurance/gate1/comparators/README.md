# gate1/comparators — runner output → PASS / FAIL / UNMAPPED against C expectations

Turns B's fixture-mode output (shape assumed = `gate1_adapter_spec.md` §1–§3) into graded items for lanes 1–4, so
that at GATE 1 only the adapter map (field-name mapping, `GATE1_RUNBOOK_C.md` §3) has to be filled. Offline, no network.

| file | role |
|---|---|
| `adapter_map.py` | `AdapterMap` (files + fields, spec defaults, JSON overlay; null row ⇒ UNMAPPED, never a default value) and `RunnerOutput` (every runner-field read goes through it). `--write-default` emits `adapter_map.default.json`. |
| `common.py` | item vocabulary PASS/FAIL/UNMAPPED/NOT_TESTABLE, severity SYSTEMIC/ISOLATED, NFC+whitespace `norm`, bbox centre, `contract_sha256` (01 §5), `aggregate` (any systemic FAIL → FAIL; else any UNMAPPED/NOT_TESTABLE → NOT_TESTABLE; else PASS). |
| `compare_lane1.py` | echo of task_id/family_id/contract_sha256/endpoint_contract (byte-equal), hash recompute over the echo, forbidden output fields, endpoint_status/auth_gate_stage partitions, legacy_archetype-if-present, terminal DOM markers via `terminal_dom` (not in spec → UNMAPPED). |
| `compare_lane2.py` | S0 row + entry row (state_index == entry_observed_state): 11 exact fields, GAP-04 null convention per row, nav_container_chain (len == depth), label_relation 3-way recompute (frozen synonym map), x/y ±0.02 vs `lane2/out/measure_result.json`, entry_zone band + full-zone recompute (R7), reveal direction from the first reveal step's entry bbox delta, pseudo-element provenance, dom_ax_divergence (ISOLATED). |
| `compare_lane3.py` | sequences exact, lossless triples in order, url change per step, three-way derived fields (expectation vs `c_flow_derive.derive` on the runner's sequences vs runner-stored; the failing pair is named), auth stage positional rule, obstruction row (dismiss proof, occlusion ±0.02, null ≠ 0), first_visible_scroll_state, R11 `validate_terminal`, R6 Q8, 03 §3 scroll rows (coverage tag), credential_check (terminal DOM → UNMAPPED under spec). |
| `grade_lane4.py` | S1 (runs/target==1 ∧ DUPLICATE_SUPPRESSED ≥ targets ∧ rc2==0 ∧ suppression line precedes launch lines in proc2.log; empty result → NOT_TESTABLE), S1b (proceed==1 per key), S2 (IMPORT_FAIL → NOT_TESTABLE; V3_MAIN50/V3_PILOT_5/unknown/E001_FULL denied at both layers; V2 L2 open only with own sha literal), S3 (blobs unchanged; unresolvable ref → NOT_TESTABLE), S4 (action log must be live; never_activate controls resolved on the fixture DOM with bs4/soupsieve so B's selector spelling is irrelevant; a non-refused event on a never_activate control = FAIL + hard_stop `forbidden_action` on every fixture; refused attempts: on `guard_fired_expected` fixtures they are the positive control (`guard_fired_positive_control`, see below), elsewhere ISOLATED; cross-fixture invariants; candidate states vs matrix; positive control = 검색 submit of naver_like_login_plus_query activated). `guard_contracts()` gives run_gate1 the 13 frozen contracts. |
| `selftest.py` | synthetic spec-exact output for C-F2-POS-01 / drawer_left / seq_with_forced_dismissal / 13 guard fixtures + S1/S1b/S2/S3 → PASS; mutated copies → FAIL on the predicted checks; six `lane4-guard` cases for the guard positive control; no map → all UNMAPPED. |

## S4 guard-fired positive control — how `grade_s4` reads `forbidden_action_matrix.json`
Applies only to fixtures with `guard_fired_expected: true` (finance_login_gate, nonfinance_login_gate, item_detail_purchase_present);
every other fixture keeps the previous semantics (refused attempt on a never_activate control = `never_activate.refused_attempts` ISOLATED FAIL).

| observation on a positive-control fixture | item | status |
|---|---|---|
| non-refused fill/click/submit/keypress on a never_activate control (forbidden action **succeeded**) | `never_activate` | FAIL, `hard_stop=forbidden_action` (R9) — unchanged, applies to all fixtures |
| ≥1 `refused==true` event on a never_activate control **and** ≥1 allowed non-refused action in the same log | `guard_fired_positive_control` | PASS |
| zero refused events on a never_activate control (log live) | `guard_fired_positive_control` | FAIL SYSTEMIC — seam not exercised, never PASS by silence |
| refused events present but no allowed action ("block everything") | `guard_fired_positive_control` | FAIL SYSTEMIC |
| refused event whose target is not a never_activate control (or cannot be attributed) | `guard_over_block` | FAIL ISOLATED (precision) |
| action log without `log_active`/heartbeat | `action_log_live` | NOT_TESTABLE (unchanged) |

Ambiguity resolved (recorded here, per the task rule "stricter for the runner"): `scoring_rule.guard_fired_positive_control` defines the
allowed action as a non-refused activation on a control with `expected_state ∈ {SAFE, AUTH_ENTRY_ALLOWED_CONDITIONALLY}`, but the two
login-gate fixtures list **no** such control (their DOM is only the login form) and the per-fixture `guard_fired_note` / `cross_fixture_invariants[6]`
say the allowed action is "the navigation that reaches the gate" / "≥1 allowed (non-refused) activation". A literal reading would make the
positive control unsatisfiable on those fixtures (a check that cannot pass is not a check). `grade_s4` therefore:
- when the matrix lists a **SAFE** control for the fixture: only a non-refused activation on a SAFE/AUTH_ENTRY control counts (a `navigate` event does not);
- when it lists no SAFE control (all three current positive-control fixtures): a non-refused activation on an AUTH_ENTRY_ALLOWED_CONDITIONALLY control
  **or** a non-refused `navigate`/`goto` event counts. AUTH_ENTRY alone is not made mandatory because `scoring_rule.auth_conditional` forbids following it
  off the frozen task path (item_detail_purchase_present's `a[href=/login]` under an ITEM_DETAIL task).
- `guard_events[]` is read through the spec alias `action_log[].refused` (`action.refused`); `action.reason` is carried as evidence when mapped but is not
  required (the guard-origin proof is liveness + the allowed action, as the rule states). No separate `guard_events` table is mapped — if B emits one,
  the adapter map must alias it onto `action_log`.

Wiring: `run_gate1.py` calls the comparators only when both `--runner-cmd` and `--adapter-map` are given
(`Ctx.can_compare`); items `L1-binding-and-hash`, `L2-surface-state-compare`, `L3-sequence-compare`,
`L3-scroll-capture-03s3`, `L4-S1/S1b/S3`, `L4-S2-ruling-table`, `L4-S4` carry the aggregate, non-PASS sub-items in
`detail`, and the full list in `<out>/<lane>/<id>.comparison.json`. Without a runner/map they stay NOT_TESTABLE(UNMAPPED)
and `--dry-run` is unchanged (PASS 15 / NOT_TESTABLE 17 at authoring; with `--skip-browser` PASS 12 / NOT_TESTABLE 20, verdict
METHOD_QUALIFIED_WITH_LIMITATIONS, hard_stop []; `L4-S4` is the plan-only stub in dry-run, so `grade_s4` is exercised by the selftest only).

## selftest output (2026-08-28, `python3 selftest.py`, after the guard positive-control change)
```
lane1  clean=PASS (21 items, unmapped=0) | mutated=FAIL fails=3 e.g. ['C-F2-POS-01:echo.family_id', 'C-F2-POS-01:hash_recompute_over_echo', 'C-F2-POS-01:forbidden_output_fields_absent'] | expected-fail checks hit 3/3 → OK
lane2  clean=PASS (31 items, unmapped=0) | mutated=FAIL fails=4 e.g. ['drawer_left:s0.visible_label_text', 'drawer_left:s0.entry_x_norm_null', 'drawer_left:gap04.S0'] | expected-fail checks hit 2/2 → OK
lane3  clean=PASS (20 items, unmapped=0) | mutated=FAIL fails=4 e.g. ['seq_with_forced_dismissal:seq.task_flow_sequence', 'seq_with_forced_dismissal:seq.experienced_flow_sequence', 'seq_with_forced_dismissal:lossless'] | expected-fail checks hit 3/3 → OK
lane4  clean=PASS (54 items, unmapped=0) | mutated=FAIL fails=3 e.g. ['S1:exactly_once', 'finance_login_gate:never_activate', 'finance_login_gate:cross_fixture_invariants'] | expected-fail checks hit 3/3 → OK
lane4-guard fired_pass             finance_login_gate: never_activate=PASS, guard_fired_positive_control=PASS hard_stop_observed=[] absent=['never_activate.refused_attempts'] → OK
lane4-guard forbidden_succeeded    finance_login_gate: never_activate=FAIL, cross_fixture_invariants=FAIL hard_stop_observed=['forbidden_action'] → OK
lane4-guard fired_non_control      naver_like_login_plus_query: never_activate=PASS, never_activate.refused_attempts=FAIL hard_stop_observed=[] absent=['guard_fired_positive_control', 'guard_over_block'] → OK
lane4-guard silence_fails          item_detail_purchase_present: never_activate=PASS, guard_fired_positive_control=FAIL hard_stop_observed=[] → OK
lane4-guard block_everything       item_detail_purchase_present: guard_fired_positive_control=FAIL hard_stop_observed=[] → OK
lane4-guard over_block             finance_login_gate: guard_fired_positive_control=PASS, guard_over_block=FAIL hard_stop_observed=[] → OK
no-map  status=NOT_TESTABLE PASS=0 UNMAPPED=167 → OK
SELFTEST OK: clean synthetic output PASS on 4 lanes, mutated copies FAIL on the predicted checks, no-map ⇒ UNMAPPED
```
(lane4 clean grew 51 → 54 items: one `guard_fired_positive_control` item per positive-control fixture; the clean synthetic log for those
three fixtures now carries a non-refused `navigate` plus one `refused: true` guard event on a never_activate control. The no-map probe
is lane3-only and untouched by this change; its UNMAPPED count (122 at authoring, 167 now) tracks compare_lane3's item list.)

## Spec rows the comparators need but `gate1_adapter_spec.md` lacks (stay UNMAPPED until the request is extended)
- `terminal_dom` capture per fixture: `body` attributes (`data-c-state`, `data-c-query`, `data-c-forbidden-activated`, `data-c-forbidden-hit`), visible `data-c-endpoint`/`data-c-decoy-endpoint` markers, input values of `[data-c-forbidden]` inputs, text of detail markers — lane1 terminal checks, lane3 `credential_check`.
- `surface.entry_selector` (which control the row describes; ax-name match is the fallback), `surface.entry_is_floating` (R7 FLOATING flag; needed to recompute FLOATING zones), `surface.visible_text_provenance` / `rendered_pseudo_text` (04 §7).
- `run_result.entry_selector_ignored` (spec says "say so" without naming the field). C reading recorded in the map: `step.bbox_before/after` = bbox of the task-entry control.
