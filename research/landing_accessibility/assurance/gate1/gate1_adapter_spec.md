# gate1_adapter_spec — minimal runner interface C needs from B for GATE 1 (request to B)

C runs its own fixtures (R14) through B's runner at B's exact COMPLETION SHA and compares against C-held expectations. B does not need to see C's fixtures or expectations; B only needs to expose the interface below. Every item C cannot bind stays `NOT_TESTABLE`, which caps the verdict at `METHOD_QUALIFIED_WITH_LIMITATIONS` — so each item here is a condition for a clean PASS, not a preference. Nothing here asks B to change a measurement rule; it asks for a stable command shape, one input file, and named output files/fields that already exist in 02 §3–§5.

## 1. Command shape (FIXTURE mode, one fixture per process, no network)
```
<entry> --mode FIXTURE --fixture <file:// or path to one .html> --contract <contract.json> --out <dir>   # exit 0 on success
```
- Must be a single non-interactive command C can template as `{fixture} {contract} {out}`; a wrapper script under `scripts/` at the SHA is fine.
- Viewport 390×844, mobile UA, `ko-KR`, fresh context per invocation (03 §1). Every non-`file://` request must be aborted and counted (a count field, see §3).
- Deterministic under identical inputs (Δ6-d): same fixture + contract ⇒ identical `task_flow_sequence`, `experienced_flow_sequence`, and ordered `control_selector` list; timestamps may differ. The route-selection policy document (candidate ranking, tie-break, shortest-path definition, stop conditions) must exist at the SHA — give its path.
- Must refuse before launching a browser when `task_id` is absent, when `contract_sha256` does not match the recomputed hash, or when the contract family is not in the frozen registry — and say so in `run_result.json` (`refusal_reason`).

## 2. Per-fixture contract input (`contract.json`, what C will pass)
```json
{"task_id": "...", "family_id": "F1..F5|null", "task_instruction": "...", "fixed_fixture": "...",
 "endpoint_contract": "...", "contract_sha256": "<sha256 of the 5 canonical fields, 01 §5 recipe>|null",
 "entry_selector": "<optional CSS selector of the task-entry control when the task is entry-only>", "forbidden_actions": [...]}
```
- The runner must **echo** `task_id`, `family_id`, `endpoint_contract`, `contract_sha256` verbatim into `fact_flow_observation` (00 §5: the task is never re-decided from page title/text/domain; no `inferred_family` / `predicted_archetype` / `representative_function` fields).
- `entry_selector` is a hint for entry-only fixtures; if the runner ignores it, say so in `run_result.json`.

## 3. Output files under `<out>/` (JSON; names are B's choice but must be listed in `run_result.json`)
`run_result.json` — `{"sha": "<runner git sha>", "exit": 0, "files": {...}, "refusal_reason": null, "non_file_requests_aborted": 0, "route_policy_doc": "<path>", "route_policy_sha256": "..."}`.
`flow.json` — the single `fact_flow_observation` row plus a `steps` array (= the `fact_flow_step` rows, each with `action_token` and `control_selector`). This one file is what C's determinism check reads three times per fixture; keep its name fixed.
- `fact_surface_state` rows (one per scroll state S0..Sn, plus `POST_REVEAL:<type>` rows): `state_index`, `visible_label_text`, `accessible_name`, `accessible_name_source`, `label_relation`, `entry_label_modality`, `entry_control_type`, `entry_x_norm`, `entry_y_norm`, `entry_zone`, `entry_observed_state`, `nav_container_type`, `nav_container_chain`, `reveal_direction`, `menu_dependency`, `nav_container_depth`, `task_control_visible` (S0 = `s0_task_control_visible`), `dom_ax_divergence`, `first_visible_scroll_state`. Unobserved numerics `null`, unobserved categoricals `NOT_OBSERVED`/`UNDETERMINED`, never `0`/`""` (GAP-04). **Scroll-only states must be emitted even when the fixture fits one viewport** — C has one fixture that needs S1 (03 §3).
- `fact_flow_step` rows ordered by `step_index`: `state_before_id`, `action_token` (04 §2 closed set), `state_after_id`, `control_selector`, `url_before`, `url_after`, `bbox_before`, `bbox_after`; DISMISS steps carry the dismissed container selector.
- `fact_flow_observation` (one row): the echo fields above + `task_flow_sequence`, `experienced_flow_sequence`, `activation_depth`, `flow_step_count`, `menu_dependency`, `nav_container_depth`, `forced_dismissal_count`, `auth_gate_stage` (incl. `UNDETERMINED`), `endpoint_status`, `terminal_reason`, `terminal_note`, `task_role`, `fixture_input_mode` / `depth_input_modes`, `endpoint_surface_rendered_before_gate`.
- `fact_task_obstruction` rows: `task_control_occlusion` (hit-test), `overlay_coverage`, `dismiss_required_for_task` (blocking proof), `dismiss_control_accessible_name`, `dismiss_control_selector`, unit/population/source axes if B records them.
- `action_log.jsonl`: **every** browser-side action (`fill|click|submit|keypress|navigate|scroll`) with `ts`, `target_selector`, `accessible_name`, `value_len` (never the value), `step_index` — including actions that were refused by the guard (`refused: true`, reason). Zero logged events must be distinguishable from zero events (a `log_active: true` marker or a heartbeat line per step).
- `candidate_states.json`: per candidate control, the guard state (`SAFE|FORBIDDEN_*|...`) and selector.
- Evidence package (03 §10): `path_manifest.json` with `runs[].evidence_manifest` + `evidence_manifest_sha256`; `evidence_manifest.jsonl` with state/step/flow records, per-artifact `sha256`, ids (`service_id`, `task_id`, `run_id`, `attempt_id`, `observation_id`, `flow_observation_id`) that are identifiers, not display names; append-only (a re-collection is a new `run_id`, 06 §6).
- Runner schema document (or JSON) declaring the allowed `endpoint_status × terminal_reason` pairs (R11) and the idempotency key shape (whether `task_id` / `contract_sha256` joins it).

## 4. What C does with it
C fills `GATE1_RUNBOOK_C.md` §3 from these names, writes `adapter_map.json`, and runs `run_gate1.py --runner-cmd '<entry> --mode FIXTURE --fixture {fixture} --contract {contract} --out {out}' --adapter-map adapter_map.json` once. Divergent C-vs-B results are reported to A as interpretation-mismatch findings with the exact field/value pair; C does not edit expectations to fit output.
