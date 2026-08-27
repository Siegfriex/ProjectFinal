# GATE 1 · Lane 3 — sequence losslessness · forced dismissal · auth gate stage (C-authored fixtures)

**Purpose.** Independent offline fixtures + pre-registered expectations for three GATE 1 checks:
(a) the runner's action sequence is lossless, (b) a forced dismissal enters `experienced_flow_sequence` only,
never `task_flow_sequence`, (c) `auth_gate_stage` is never inferred from a merely present login control.
Expectations were written by C from SSOTV3 (04 §2–§5, 03 §5–§9, 00 §6–§7, 02 §4–§5) and from the geometry C built;
**no B runner code was read or imported.** Base: `f5e3c8ea`. Nothing here is committed by this lane.

Layout: `fixtures/*.html` (390×844 single-page apps, inline JS state machine, `<body data-c-state>`, no external
resources, every path control carries `data-c-action=<TOKEN>` and `data-c-path="1"`; the task function control carries
`data-c-task-control="1"`; decoys carry `data-c-decoy`; forbidden controls carry `data-c-forbidden`),
`EXPECTATIONS.json` (per-fixture expected fields, `lossless_check` triples, pre-registered derivation rules),
`walk_fixture.py` (Playwright self-validation of the fixtures), `out/walk_result.json` (raw walk evidence).

## Fixture → expectation

| fixture | fam | role | task_flow_sequence | experienced | act_depth | flow_steps | menu_dep/ncd | auth_gate_stage | fdc/required | occl S0 | endpoint | fvss |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| seq_menu_category_function_endpoint | F5 | POSITIVE | OPEN_GLOBAL_MENU > SELECT_CATEGORY > SELECT_FUNCTION > INPUT_QUERY > SUBMIT_QUERY > SELECT_RESULT > ENDPOINT_REACHED | = task | 5 | 6 | 1/1 | NONE | 0/F | 0.0 | REACHED | NONE |
| seq_with_forced_dismissal | F5 | POSITIVE | OPEN_GLOBAL_MENU > SELECT_CATEGORY > SELECT_FUNCTION > INPUT_QUERY > SUBMIT_QUERY > SELECT_RESULT > ENDPOINT_REACHED | DISMISS > … | 5 | 6 | 1/1 | NONE | 1/T | 1.0 | REACHED | NONE |
| seq_non_blocking_banner | F5 | NEGATIVE | OPEN_GLOBAL_MENU > SELECT_CATEGORY > SELECT_FUNCTION > INPUT_QUERY > SUBMIT_QUERY > SELECT_RESULT > ENDPOINT_REACHED | = task | 5 | 6 | 1/1 | NONE | 0/F | 0.0 | REACHED | NONE |
| auth_generic_login_present_no_gate | F3 | NEGATIVE | SELECT_FUNCTION > ENDPOINT_REACHED | = task | 1 | 1 | 0/0 | NONE | 0/F | 0.0 | REACHED | S0 |
| auth_gate_after_task_select | F1 | POSITIVE | SELECT_FUNCTION > AUTH_GATE | = task | 1 | 2 | 0/0 | AFTER_TASK_SELECT | 0/F | 0.0 | AUTH_GATE | S0 |
| auth_gate_before_discovery | F1 | POSITIVE | AUTH_GATE | = task | 0 | 1 | 0/0 | BEFORE_TASK_DISCOVERY | 0/F | n/a | AUTH_GATE | NONE |
| auth_gate_at_endpoint | F5 | POSITIVE | SELECT_FUNCTION > INPUT_QUERY > SUBMIT_QUERY > SELECT_RESULT > AUTH_GATE | = task | 3 | 5 | 0/0 | AT_ENDPOINT | 0/F | 0.0 | AUTH_GATE | S0 |
| seq_typing_and_scroll_not_depth | F5 | POSITIVE | SELECT_FUNCTION > INPUT_QUERY > SUBMIT_QUERY > ENDPOINT_REACHED | = task | 2 | 3 | 0/0 | NONE | 0/F | n/a | REACHED | S1 |

Rationale per fixture is in `EXPECTATIONS.json[fixtures][*].rationale`; `lossless_check` there lists the exact
`(state_before, data-c-action, state_after)` triples (state = `body[data-c-state]`). Fixture 2's first triple
`(LANDING_MODAL, DISMISS_OBSTRUCTION, LANDING)` must be recorded but must be absent from `task_flow_sequence`.
Fixture 3 has `overlay_coverage_s0 ≈ 0.076` with occlusion 0 — a runner that reports it as obstruction fails (b).
Fixture 4 shows a visible 로그인 button and 로그인 하러가기 link but the F3 endpoint is reached — `AUTH_GATE` there fails (c).

## Definitional boundaries C fixed (to be pre-registered before comparing any runner)

1. **activation_depth counts SUBMIT_QUERY** (button activation; 03 §6 excludes only scroll/passive/typing/dismiss). Excluded: INPUT_QUERY, DISMISS_OBSTRUCTION, AUTH_GATE, ENDPOINT_REACHED, scroll.
2. **flow_step_count** = tokens of task_flow_sequence minus pure terminal markers (ENDPOINT_REACHED/ABSTAIN); **AUTH_GATE is counted** (04 §4 "auth encounter 포함").
3. **nav_container_depth** counts only REVEAL tokens (OPEN_GLOBAL_MENU/OPEN_LOCAL_MENU/EXPAND_ACCORDION) before SELECT_FUNCTION; a SELECT_CATEGORY that navigates to a category page is not a container reveal (fixture 1 → 1, not 2). SWITCH_TAB left undecided.
4. **task_control_occlusion** is hit-test based (9×9 grid, `elementFromPoint` not control/descendant), measured on the path control of the *current* state (hamburger at S0 when the function is menu-hidden); geometric bbox∩overlay is a cross-check only. Undefined (`null`) when the control is outside the viewport.
5. **dismiss_required_for_task** needs a blocking proof: a click at the path control's centre must leave the state unchanged while the interrupt is present; overlap alone is insufficient.
6. **auth_gate_stage**: BEFORE_TASK_DISCOVERY = AUTH_GATE with no SELECT_FUNCTION possible at any scroll state and no reveal container; AFTER_TASK_SELECT = gate at/after SELECT_FUNCTION and before any result-level token or results surface (position rule wins even if the gated action would have been the endpoint, e.g. F3); **AT_ENDPOINT** = gate on a result-level activation after a results surface rendered without auth, or endpoint surface rendered with contract content withheld.
7. **first_visible_scroll_state** refers to the SELECT_FUNCTION control only; "NONE" when scroll never exposes it (menu-hidden, login wall). Fixture 8 is S1 for any scroll step in [120, 844] px.
8. **F5 SELECT_RESULT before endpoint**: a route list without time/price does not satisfy the F5 contract, so selecting a route is pre-endpoint (fixture 1 & 7).

## Runner-adapter comparison plan (what C will diff)

| runner output (02 §4–§5) | expectation field | check |
|---|---|---|
| `fact_flow_step` rows ordered by `step_index`, token-bearing only → `(state_before_id, action_token, state_after_id)` | `lossless_check` | exact list equality; state ids mapped via `body[data-c-state]` captured in before/after DOM hashes; `url_before≠url_after` on every recorded step |
| `fact_flow_observation.task_flow_sequence` / `experienced_flow_sequence` | same names | exact; `experienced − DISMISS == task` |
| `activation_depth`, `flow_step_count`, `menu_dependency`, `nav_container_depth` | same names | equality after C recomputes from the runner's own sequence with the rules above (catches rule drift separately from sequence drift) |
| `auth_gate_stage`, `endpoint_status` | same names | exact; fixture 4 must be NONE/REACHED |
| `forced_dismissal_count`, `fact_task_obstruction.{task_control_occlusion, dismiss_required_for_task, dismiss_control_accessible_name}` | `forced_dismissal_count`, `task_control_occlusion_s0`, `dismiss_required_for_task`, `dismiss_control` | numeric ±0.02; fixture 3 must produce no obstruction row with required=true |
| `fact_surface_state.{task_control_visible, state_index}` | `s0_task_control_visible`, `first_visible_scroll_state` | exact |
| prohibited-action log / credential inputs | `credential_check` | zero `data-c-forbidden` activations, all such inputs empty |

## walk_fixture.py result (run 2026-08-27T17:51Z, chromium headless 390×844, non-file requests aborted)

| fixture | role | recorded steps | S0 occl (hit/geo) | S0 overlay cov | fvss | terminal | result |
|---|---|---|---|---|---|---|---|
| seq_menu_category_function_endpoint | POSITIVE | 6/6 | 0.00/0.00 | 0.000 | NONE | ENDPOINT_REACHED | PASS |
| seq_with_forced_dismissal | POSITIVE | 7/7 | 1.00/1.00 | 1.000 | NONE | ENDPOINT_REACHED | PASS |
| seq_non_blocking_banner | NEGATIVE | 6/6 | 0.00/0.00 | 0.076 | NONE | ENDPOINT_REACHED | PASS |
| auth_generic_login_present_no_gate | NEGATIVE | 1/1 | 0.00/0.00 | 0.000 | S0 | ENDPOINT_REACHED | PASS |
| auth_gate_after_task_select | POSITIVE | 1/1 | 0.00/0.00 | 0.000 | S0 | AUTH_GATE | PASS |
| auth_gate_before_discovery | POSITIVE | 0/0 | n/a | 0.000 | NONE | AUTH_GATE | PASS |
| auth_gate_at_endpoint | POSITIVE | 4/4 | 0.00/0.00 | 0.000 | S0 | AUTH_GATE | PASS |
| seq_typing_and_scroll_not_depth | POSITIVE | 3/3 | n/a | 0.000 | S1 | ENDPOINT_REACHED | PASS |

RESULT: ALL PASS (8/8 fixtures) -> /home/sieg/projects-wsl/ProjectFinal/.agent_worktrees/claude_c_assurance_v21/research/landing_accessibility/assurance/gate1/lane3_sequence_dismiss_auth/out/walk_result.json

Mutation control: with five planted errors in a scratch copy of EXPECTATIONS (drop INPUT_QUERY, put DISMISS in task flow,
claim banner occlusion 0.5, claim fixture 4 AFTER_TASK_SELECT, count scroll in depth) the walker reports FAIL on every mutated fixture (3/8 pass, exit 1).
