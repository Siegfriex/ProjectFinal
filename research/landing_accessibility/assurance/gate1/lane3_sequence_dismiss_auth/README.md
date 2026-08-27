# GATE 1 · Lane 3 — sequence losslessness · forced dismissal · auth gate stage (C-authored fixtures)

**Purpose.** Independent offline fixtures + pre-registered expectations for three GATE 1 checks:
(a) the runner's action sequence is lossless, (b) a forced dismissal enters `experienced_flow_sequence` only,
never `task_flow_sequence`, (c) `auth_gate_stage` is never inferred from a merely present login control.
Expectations were written by C from SSOTV3 (04 §2–§5, 03 §5–§9, 00 §6–§7, 02 §4–§5) and from the geometry C built;
**no B runner code was read or imported.** Base: `f5e3c8ea`; **r2** on `claude-c/assurance-v21` after `67f473b`: rule text aligned to A `T-A-V3-STEP1-011` (P-06/P-09/P-13/P-14/P-17), `T-A-V3-STEP1-012` (GAP-02/03/04/05) and C `C-DECISION_REQUEST-031138` (P-11/P-23/P-24); only `first_visible_scroll_state` values changed (see §Definitional boundaries 7). Nothing here is committed by this lane.

Layout: `fixtures/*.html` (390×844 single-page apps, inline JS state machine, `<body data-c-state>`, no external
resources, every path control carries `data-c-action=<TOKEN>` and `data-c-path="1"`; the task function control carries
`data-c-task-control="1"`; decoys carry `data-c-decoy`; forbidden controls carry `data-c-forbidden`),
`EXPECTATIONS.json` (per-fixture expected fields, `lossless_check` triples, pre-registered derivation rules),
`walk_fixture.py` (Playwright self-validation of the fixtures), `out/walk_result.json` (raw walk evidence).

## Fixture → expectation

| fixture | fam | role | task_flow_sequence | experienced | act_depth | flow_steps | menu_dep/ncd | auth_gate_stage | fdc/required | occl S0 | endpoint | fvss |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| seq_menu_category_function_endpoint | F5 | POSITIVE | OPEN_GLOBAL_MENU > SELECT_CATEGORY > SELECT_FUNCTION > INPUT_QUERY > SUBMIT_QUERY > SELECT_RESULT > ENDPOINT_REACHED | = task | 5 | 6 | 1/1 | NONE | 0/F | 0.0 | REACHED | S0 |
| seq_with_forced_dismissal | F5 | POSITIVE | OPEN_GLOBAL_MENU > SELECT_CATEGORY > SELECT_FUNCTION > INPUT_QUERY > SUBMIT_QUERY > SELECT_RESULT > ENDPOINT_REACHED | DISMISS > … | 5 | 6 | 1/1 | NONE | 1/T | 1.0 | REACHED | S0 |
| seq_non_blocking_banner | F5 | NEGATIVE | OPEN_GLOBAL_MENU > SELECT_CATEGORY > SELECT_FUNCTION > INPUT_QUERY > SUBMIT_QUERY > SELECT_RESULT > ENDPOINT_REACHED | = task | 5 | 6 | 1/1 | NONE | 0/F | 0.0 | REACHED | S0 |
| auth_generic_login_present_no_gate | F3 | NEGATIVE | SELECT_FUNCTION > ENDPOINT_REACHED | = task | 1 | 1 | 0/0 | NONE | 0/F | 0.0 | REACHED | S0 |
| auth_gate_after_task_select | F1 | POSITIVE | SELECT_FUNCTION > AUTH_GATE | = task | 1 | 2 | 0/0 | AFTER_TASK_SELECT | 0/F | 0.0 | AUTH_GATE | S0 |
| auth_gate_before_discovery | F1 | POSITIVE | AUTH_GATE | = task | 0 | 1 | 0/0 | BEFORE_TASK_DISCOVERY | 0/F | null | AUTH_GATE | null |
| auth_gate_at_endpoint | F5 | POSITIVE | SELECT_FUNCTION > INPUT_QUERY > SUBMIT_QUERY > SELECT_RESULT > AUTH_GATE | = task | 3 | 5 | 0/0 | AT_ENDPOINT | 0/F | 0.0 | AUTH_GATE | S0 |
| seq_typing_and_scroll_not_depth | F5 | POSITIVE | SELECT_FUNCTION > INPUT_QUERY > SUBMIT_QUERY > ENDPOINT_REACHED | = task | 2 | 3 | 0/0 | NONE | 0/F | null | REACHED | S1 |

Rationale per fixture is in `EXPECTATIONS.json[fixtures][*].rationale`; `lossless_check` there lists the exact
`(state_before, data-c-action, state_after)` triples (state = `body[data-c-state]`). Fixture 2's first triple
`(LANDING_MODAL, DISMISS_OBSTRUCTION, LANDING)` must be recorded but must be absent from `task_flow_sequence`.
Fixture 3 has `overlay_coverage_s0 ≈ 0.076` with occlusion 0 — a runner that reports it as obstruction fails (b).
Fixture 4 shows a visible 로그인 button and 로그인 하러가기 link but the F3 endpoint is reached — `AUTH_GATE` there fails (c).

## Definitional boundaries C fixed (to be pre-registered before comparing any runner)

1. **activation_depth counts SUBMIT_QUERY** (button activation; 03 §6 excludes only scroll/passive/typing/dismiss). Excluded: INPUT_QUERY, DISMISS_OBSTRUCTION, AUTH_GATE, ENDPOINT_REACHED, scroll.
2. **flow_step_count** = tokens of task_flow_sequence minus pure terminal markers (ENDPOINT_REACHED/ABSTAIN); **AUTH_GATE is counted** (04 §4 "auth encounter 포함"). A `T-A-V3-STEP1-012` GAP-03 rules exactly this; all 8 fixture values comply (re-derived by the walker).
3. **nav_container_depth** counts only REVEAL tokens (OPEN_GLOBAL_MENU/OPEN_LOCAL_MENU/EXPAND_ACCORDION) before the anchor = first SELECT_FUNCTION or, when absent, the first task-body token (C-decided `C-DECISION_REQUEST-031138` P-11, lane6 rule adopted); a SELECT_CATEGORY that navigates to a category page is not a container reveal (fixture 1 → 1, not 2 — unchanged under the anchor rule). **SWITCH_TAB is not a reveal token** (A `T-A-V3-STEP1-011` P-06; `menu_dependency_incl_tab` is the declared sensitivity); menu_dependency is sequence-based (P-09).
4. **task_control_occlusion** is hit-test based (9×9 grid, `elementFromPoint` not control/descendant), measured on the path control of the *current* state (hamburger at S0 when the function is menu-hidden); geometric bbox∩overlay is a cross-check only. Undefined (`null`) when the control is outside the viewport.
5. **dismiss_required_for_task** needs a blocking proof: a click at the path control's centre must leave the state unchanged while the interrupt is present; overlap alone is insufficient.
6. **auth_gate_stage** — A `T-A-V3-STEP1-011` single positional rule (r1 wording withdrawn, values unchanged): BEFORE_TASK_DISCOVERY = no task-specific token precedes AUTH_GATE (only general navigation OPEN_GLOBAL_MENU / OPEN_LOCAL_MENU / SWITCH_TAB / EXPAND_ACCORDION / DISMISS_OBSTRUCTION, or nothing — so `OPEN_GLOBAL_MENU > AUTH_GATE` is BEFORE); AFTER_TASK_SELECT = ≥1 task-specific token (SELECT_CATEGORY / SELECT_FUNCTION / INPUT_QUERY / SELECT_ORIGIN / SELECT_DESTINATION / SELECT_DATE / SUBMIT_QUERY / SELECT_RESULT / OPEN_ITEM_DETAIL / OPEN_PLACE_DETAIL) precedes the gate but the endpoint contract is not satisfied (F3 form-as-endpoint and submit-straight-to-login both land here); **AT_ENDPOINT** = the endpoint surface was rendered without auth and the gate hits on accessing its content (fixture `auth_gate_at_endpoint`: route list rendered, time/price gated — flag `endpoint_surface_rendered_before_gate`). The walker derives the stage from the sequence with this rule and requires equality: 8/8 (login wall → BEFORE, F1 select → AFTER, F5 result → AT_ENDPOINT, others NONE).
7. **first_visible_scroll_state** refers to the SELECT_FUNCTION control only. A `T-A-V3-STEP1-012` GAP-02: for a control exposed by a reveal it is the scroll state at which the reveal happened — S0 in fixtures 1–3 (r1 said NONE); `null` only when the control was never observed (fixture 6 login wall; r1 said NONE), the reason then lives in endpoint_status × terminal_reason. Fixture 8 is S1 for any scroll step in [120, 844] px. The walker now records the scroll state of the first step after which the control is in the viewport.
8. **s0_task_control_visible** (GAP-05) = bbox intersects the S0 viewport AND hit-testable at S0 (`elementFromPoint` at the centre is the control or a descendant) — the r1 walker used an occlusion < 0.5 threshold, replaced by the centre hit-test; no value changed. Independent of task_control_occlusion.
9. **Null convention** (GAP-04): `task_control_occlusion_s0` / `overlay` are `null` when the path control is not observed at S0 (fixtures 6, 8 — already so in r1), `0.0` when observed and unoccluded; occlusion primary and `dismiss_required_for_task` blocking proof are now the C-wide primaries (`C-DECISION_REQUEST-031138` P-23/P-24; lane7 aligned).
8. **F5 SELECT_RESULT before endpoint**: a route list without time/price does not satisfy the F5 contract, so selecting a route is pre-endpoint (fixture 1 & 7).

## Runner-adapter comparison plan (what C will diff)

| runner output (02 §4–§5) | expectation field | check |
|---|---|---|
| `fact_flow_step` rows ordered by `step_index`, token-bearing only → `(state_before_id, action_token, state_after_id)` | `lossless_check` | exact list equality; state ids mapped via `body[data-c-state]` captured in before/after DOM hashes; `url_before≠url_after` on every recorded step |
| `fact_flow_observation.task_flow_sequence` / `experienced_flow_sequence` | same names | exact; `experienced − DISMISS == task` |
| `activation_depth`, `flow_step_count`, `menu_dependency`, `nav_container_depth` | same names | equality after C recomputes from the runner's own sequence with the rules above (catches rule drift separately from sequence drift) |
| `auth_gate_stage`, `endpoint_status` | same names | exact; fixture 4 must be NONE/REACHED |
| `forced_dismissal_count`, `fact_task_obstruction.{task_control_occlusion, dismiss_required_for_task, dismiss_control_accessible_name}` | `forced_dismissal_count`, `task_control_occlusion_s0`, `dismiss_required_for_task`, `dismiss_control` | numeric ±0.02; fixture 3 must produce no obstruction row with required=true |
| `fact_surface_state.{task_control_visible, state_index}` | `s0_task_control_visible`, `first_visible_scroll_state` | exact; `null` fvss only for a never-observed control (GAP-02) |
| prohibited-action log / credential inputs | `credential_check` | zero `data-c-forbidden` activations, all such inputs empty |

## walk_fixture.py result (r2 run 2026-08-28 after STEP1-011/012 + P-11/P-23/P-24 edits, chromium headless 390×844, non-file requests aborted)

| fixture | role | recorded steps | S0 occl (hit/geo) | S0 overlay cov | fvss | terminal | result |
|---|---|---|---|---|---|---|---|
| seq_menu_category_function_endpoint | POSITIVE | 6/6 | 0.00/0.00 | 0.000 | S0 | ENDPOINT_REACHED | PASS |
| seq_with_forced_dismissal | POSITIVE | 7/7 | 1.00/1.00 | 1.000 | S0 | ENDPOINT_REACHED | PASS |
| seq_non_blocking_banner | NEGATIVE | 6/6 | 0.00/0.00 | 0.076 | S0 | ENDPOINT_REACHED | PASS |
| auth_generic_login_present_no_gate | NEGATIVE | 1/1 | 0.00/0.00 | 0.000 | S0 | ENDPOINT_REACHED | PASS |
| auth_gate_after_task_select | POSITIVE | 1/1 | 0.00/0.00 | 0.000 | S0 | AUTH_GATE | PASS |
| auth_gate_before_discovery | POSITIVE | 0/0 | n/a | 0.000 | null | AUTH_GATE | PASS |
| auth_gate_at_endpoint | POSITIVE | 4/4 | 0.00/0.00 | 0.000 | S0 | AUTH_GATE | PASS |
| seq_typing_and_scroll_not_depth | POSITIVE | 3/3 | n/a | 0.000 | S1 | ENDPOINT_REACHED | PASS |

RESULT: ALL PASS (8/8 fixtures) -> out/walk_result.json

Mutation control: with five planted errors in a scratch copy of EXPECTATIONS (drop INPUT_QUERY, put DISMISS in task flow,
claim banner occlusion 0.5, claim fixture 4 AFTER_TASK_SELECT, count scroll in depth) the walker reports FAIL on every mutated fixture (3/8 pass, exit 1).
