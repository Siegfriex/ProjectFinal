# GATE1_RUNBOOK_C — C procedure for GATE 1 once B's COMPLETION ticket arrives

**Plane** Claude C. **Base** `claude_c_assurance_v21 @ 75614c8` (lanes 1–7 as listed in `GATE1_PREREGISTRATION_C.md` r2). **Executor** `run_gate1.py` (this dir). **Interface request to B** `gate1_adapter_spec.md`.
**Authority** T-A-V3-STEP1-FREEZE (D.C must_include 1–4), STEP1-004 (R8 procedure, R9 canonical 8, n<5 reporting floor), P0-001 (gate_rule: '검증하지 않은 것' section), STEP1-012 (GAP-02 03 §3 coverage), STEP1-007 (R11 table, R14 own fixtures), SSOTV3 03 §12 (METHOD_QUALIFIED exit), 06 §8 (completion = exact SHA + results + artifact + claim boundary + limitation).
Offline only. No REAL target. Never read `claude_b_*` / `claude_d_*` worktrees — the SUT is a scratchpad clone of the exact SHA.

## 1. Pin the SHA and clone (never a B worktree — D-R0-69)
1. Read B's COMPLETION ticket; copy `exact_sha` (40 hex). Refuse a branch name or a heartbeat self-report.
2. `git -C /home/sieg/projects-wsl/ProjectFinal fetch origin` is NOT run (no network in this procedure); the object must already be local: `git -C <C worktree> cat-file -t <sha>` → `commit`, else STOP and ask A (ticket, not chat).
3. `git clone --no-checkout /home/sieg/projects-wsl/ProjectFinal $SCRATCH/sut_<sha7> && git -C $SCRATCH/sut_<sha7> checkout --detach <sha>`
4. Record `git rev-parse HEAD`, `HEAD^{tree}`, `status --porcelain` (must be empty). `run_gate1.py` re-records these; a mismatch between `--sha` and HEAD is written as a warning and the verdict is about HEAD.
5. Also record: C worktree HEAD + `HEAD:research/landing_accessibility/assurance/gate1` tree; control ref `control/landing-orchestrator`; SSOT snapshot `cad8ad45` (0/22 mismatch verified, T-A-V3-STEP1-013.C).

## 2. Discover B's runner CLI and output schema (read the SUT tree, not B's tickets' prose)
Look for, and write down file:line for each: (a) **entry script** for FIXTURE-mode task-first runs (`scripts/run_*v3*`, `--mode FIXTURE`, `--task-id`, `--contract`); (b) **TargetSpec / contract input** — where `task_id`, `family_id`, `task_contract_sha`/`contract_sha256`, `endpoint_contract`, `fixture` URL enter (07: task_id in TargetSpec); (c) **idempotency key** shape (does task_id join it — 06 §6); (d) **output tables**: `fact_surface_state` (one row per scroll state: `state_index`, `visible_label_text`, `accessible_name`, `accessible_name_source`, `label_relation`, `entry_label_modality`, `entry_control_type`, `entry_x_norm/entry_y_norm`, `entry_zone`, `entry_observed_state`, `nav_container_type`, `nav_container_chain`, `reveal_direction`, `s0_task_control_visible`/`task_control_visible`, `dom_ax_divergence`), `fact_flow_observation` (`task_flow_sequence`, `experienced_flow_sequence`, `activation_depth`, `flow_step_count`, `menu_dependency`, `nav_container_depth`, `forced_dismissal_count`, `auth_gate_stage` incl. `UNDETERMINED`, `endpoint_status`, `terminal_reason`, `terminal_note`, `task_role`, `fixture_input_mode`/`depth_input_modes`, `first_visible_scroll_state`), `fact_flow_step` (`step_index`, `state_before_id`, `action_token`, `state_after_id`, `control_selector`, `url_before/after`, before/after bbox), `fact_task_obstruction` (`task_control_occlusion`, `dismiss_required_for_task`, `dismiss_control_accessible_name`, `overlay_coverage`); (e) **terminal_reason table** — B's declared `endpoint_status × terminal_reason` allowed set (R11: schema must reject impossible pairs); (f) **action log** (every fill/click/submit/keypress with target selector) and per-candidate state list (lane4 S4); (g) **evidence package** layout: `path_manifest.json`, `evidence_manifest.jsonl`, per-state artifacts + sha256, run/attempt ids; (h) **route policy document** (Δ6-d). Anything not found is written as `absent at <sha>` — not guessed.

## 3. Adapter mapping table (C expectation field → B output field; fill from §2)
Rule: a row left `UNMAPPED` makes its lane item `NOT_TESTABLE`; NOT_TESTABLE is never PASS. The filled table is saved as the `--adapter-map` JSON (`{"evidence_root": ..., "fields": {"<C field>": "<B table.field or path>"}}`).

| lane | C expectation field(s) | B output field | status |
|---|---|---|---|
| 1 | `task_id_out`, `family_id_out`, `contract_sha256_out`, `endpoint_contract_out_verbatim` (echo) | | UNMAPPED |
| 1 | `endpoint_status_allowed`, `auth_gate_stage_allowed`, terminal marker `body[data-c-state]`, `body[data-c-forbidden-activated]` absent, `output_fields_must_not_exist` | | UNMAPPED |
| 2 | `fact_surface_state` S0 row: 11 exact fields (README §How the runner adapter compares), `entry_x/y_norm` ±0.02, `entry_observed_state`, `nav_container_chain`, `dom_ax_divergence`, GAP-04 null convention | | UNMAPPED |
| 2 | first post-reveal `fact_flow_step` bbox_before/after (motion sign/axis, |Δ| ≥ `min_abs_delta_px`) | | UNMAPPED |
| 3 | `fact_flow_step` `(state_before_id, action_token, state_after_id)` list = `lossless_check`; `url_before≠url_after` | | UNMAPPED |
| 3 | `task_flow_sequence`, `experienced_flow_sequence`, `activation_depth`, `flow_step_count`, `menu_dependency`, `nav_container_depth`, `auth_gate_stage`, `endpoint_status`, `forced_dismissal_count`, `first_visible_scroll_state`; obstruction row; `credential_check` | | UNMAPPED |
| 3 | 03 §3: S0 **and** S1 `fact_surface_state` rows for `seq_typing_and_scroll_not_depth` | | UNMAPPED |
| 4 | action log event schema (type, target selector, fixture), candidate state list → `forbidden_action_matrix.json`; `runner_cmd_template`; idempotency key with task_id | | UNMAPPED |
| 5 | evidence root, path manifest keys, `FIELD_ALIASES`/`ARTIFACT_ALIASES`/`STEP_HASH_FIELDS` names; B's R11 table | | UNMAPPED |
| 6 | `fact_flow_observation` rows → `compare_with_mart_row` inputs; B derived columns; family report; denominator chain/replacement manifest | | UNMAPPED |
| 7 | per-run sequence JSON: `task_flow_sequence`, `experienced_flow_sequence`, `steps[].control_selector`; route policy doc path | | UNMAPPED |

## 4. Execution order and commands (one invocation does all of it)
```bash
SUT=$SCRATCH/sut_<sha7>; OUT=$SCRATCH/gate1_<sha7>
python3 run_gate1.py --sut $SUT --sha <sha> --out $OUT \
    --runner-cmd '<B entry> --mode FIXTURE --fixture {fixture} --contract {contract} --out {out}' \
    --adapter-map $OUT/adapter_map.json --ref-sha <E001 baseline sha>      # omit the last three ⇒ NOT_TESTABLE rows
python3 run_gate1.py --dry-run                                              # rehearsal without a SUT (C worktree as sut)
```
Order inside the run (safety first): **lane4** — S2 two-layer scope probe (`two_layer_scope_probe.py --repo-root $SUT`, import-only; FAIL if `V3_MAIN50`/`V3_PILOT_5`/`unknown` is allowed at any layer; layer-2 own manifest-sha literal required when a V3 scope is open — FREEZE ③), then the stub battery S1 dup-launch (`w1/dup_launch_harness.py`), S1b lock race, S2b 3-way allowlist, S3 E001 blobs unchanged, S4 forbidden matrix via runner action log (positive control: ≥1 activation on the 검색 submit of `naver_like_login_plus_query` — zero logging ≠ zero events) → **lane1** selfcheck, then runner on 4 binding fixtures → **lane2** `measure_geometry.py`, runner on 14 fixtures → **lane3** `walk_fixture.py`, runner on 8 fixtures (+ 03 §3 item) → **lane7** converge + negctrl + probe-like validation + determinism pos/neg controls, then `determinism_check.py --cmd '<runner template>'` ×3 on f01–f06 → **lane5** regenerate + 3 synthetic controls, then `evidence_lineage_check.py` on the runner output tree (`evidence_root` from the map) → **lane6** pytest + demo, then recompute-and-compare on runner-produced rows and denominator chain.
Every item is a subprocess of an existing lane script; a missing script is recorded `MISSING_SCRIPT`, a crash `ERROR`; nothing raises past the driver. Logs: `$OUT/<lane>/<item>.log`; raw runner captures: `$OUT/<lane>/runner/<fixture>/`; contracts C fed: `$OUT/contracts/`.

## 5. Verdict rules (implemented in `run_gate1.py::evaluate`)
- **systemic** = (i) any R9 canonical-8 trigger — `wrong_scope`, `target_outside_manifest`, `forbidden_action`, `evidence_overwrite`, `duplicate_launch`, `task_contract_drift` (endpoint drift included), `task_or_outcome_leakage`, `denominator_corruption` — or (ii) a **fixture-reproducible defect** (R8 ②): any FAIL on a C fixture is by construction reproduced under C's control, hence systemic; lane5 severities follow `EVIDENCE_CONTRACT_C.md`. No count threshold exists (R8).
- **site-level / isolated** defects (R8 ③, lane5 isolated kinds) are listed in §6 of the report and do not block. If reproduction cannot be attempted → recorded `ABSTAIN` for that target (R8 ④), never silently dropped.
- Ladder: `HARD_STOP` (≥1 R9 trigger observed) > `C_HARNESS_DEFECT` (a C-internal/positive control FAIL/ERROR/MISSING — no claim about B, P-67) > `FAIL_SYSTEMIC` > `METHOD_QUALIFIED_WITH_LIMITATIONS` (0 systemic but ≥1 NOT_TESTABLE/UNMAPPED item **or** 03 §3 not verified) > `PASS`.
- **GATE 1 PASS iff** hard-stop 0 ∧ C-harness defect 0 ∧ systemic 0 ∧ NOT_TESTABLE 0 ∧ 03 §3 scroll capture VERIFIED (= 03 §12 all six conditions met on C's own fixtures, R14). Exit code 0 only then. PASS-by-silence is impossible: an empty runner output or an unmapped field is NOT_TESTABLE.
- Reporting floor (STEP1-004): applies to REAL families later, not to fixtures; the report template carries the rule so GATE 2/3 inherit it.
- Positive control failing ⇒ negatives uninterpretable; expectations are never edited to fit runner output (P-67). A C-vs-B fixture divergence is an interpretation-mismatch finding to A (R14), not a reconciliation done by C.

## 6. Mandatory report sections (pre-filled by `run_gate1.py` → `GATE1_REPORT_C.md`; `<<fill>>` marks free text)
1 exact SHAs (B claimed + clone HEAD/tree/dirty, C HEAD + gate1 tree, control ref, SSOT snapshot `cad8ad45`, E001 baseline, runner template, adapter map) · 2 per-lane results table with the **independence statement** (C fixtures only, R14) · 3 reconciliation of lane contradictions (new ones → RECONCILIATION_REQUIRED to A) · 4 **검증하지 않은 것** (every NOT_TESTABLE item + the 03 §3 scroll statement + real-site behaviour) · 5 known limitations (R14 shared-reading risk; 03 §3 coverage statement; snapshot honest_limit; lane5 mtime basis; lane7 probabilistic negative control; lane4 pre-W1 positive control citation) · 6 hard-stop triggers observed (must be `[]`) + systemic / isolated / C-harness lists · 7 next automatic action (PASS → C-GATE1-VERDICT ticket to A; limitations → adapter request to B and re-run at the same SHA; systemic → P0 HOLD; hard-stop → P0 HOLD to A + DIRECTOR).

## 7. Dry-run result at authoring time (C worktree as SUT, no runner; `python3 run_gate1.py --dry-run`, 16 s)
```json
{"verdict": "METHOD_QUALIFIED_WITH_LIMITATIONS", "exit_code": 1,
 "counts": {"PASS": 15, "FAIL": 0, "NOT_TESTABLE": 17, "ERROR": 0, "MISSING_SCRIPT": 0}, "n_items": 32,
 "hard_stop_triggers_observed": [], "systemic_defects": [], "c_harness_defects": [],
 "not_testable_items": ["L4-S2-two-layer-scope-probe", "L4-S2-layer2-manifest-sha-independent", "L4-S1", "L4-S1b", "L4-S2b", "L4-S3", "L4-S4",
   "L1-binding-and-hash", "L2-surface-state-compare", "L3-sequence-compare", "L3-scroll-capture-03s3", "L7-determinism-runner",
   "L7-route-policy-doc", "L5-runner-evidence-tree", "L5-terminal-reason-table", "L6-recompute-compare", "L6-denominator-chain"],
 "coverage": {"scroll_capture_03_s3": "NOT_VERIFIED_DECLARED"}}
```
The 15 PASS are all C-internal controls (lane1 selfcheck 4/4; lane2 14/14; lane3 8/8; lane7 converge 31/31 + NEGCTRL_OK + probe-like 39/39 + determinism pos PASS/neg FAIL-as-expected; lane5 good=0 / bad_overwrite=2 / bad_lineage=2; lane6 pytest 30 passed + demo Q8-clean). The lane4 S2 probe against the C worktree records `IMPORT_FAIL` at both layers and is graded NOT_TESTABLE — not "denied at both layers" — which is the empty-result guard working. Verdict is not PASS and the exit code is 1, as designed: nothing runner-dependent was tested.
Runner-path rehearsal (scratchpad stand-in runner honouring `gate1_adapter_spec.md` §1–§3, still no `--adapter-map`): 40 items, 24 PASS (adds 3 raw captures + determinism ×3 on f01–f06), 16 NOT_TESTABLE all tagged `UNMAPPED`, verdict unchanged — the comparison items cannot turn PASS without the filled §3 table. Default dry-run output lands in `gate1/out/dry_run/` (untracked, regenerable; removed after authoring).

## Addendum r3 — COMPLETION intake checks added from T-B-V3-FINDING-008 (2026-08-28 07:30 KST, before any B COMPLETION)

B reported 3 seam failures in its unpushed 12-lane merge (`d4e9e09f`, not a submission SHA). C does not audit that intermediate state (3-Gate mode). C pre-registers what it *will* check at COMPLETION intake, so the checks are fixed before the outcome is seen:

| # | Check | Pass condition | Source |
|---|---|---|---|
| CI-1 | Test evidence recount | C re-runs the suite at the exact COMPLETION SHA and parses `--junitxml` itself; terminal summary is not evidence. `-q`/`-qq` addopts collision noted — empty output ≠ pass | FINDING-008 measurement note; [[verification-requires-control-group]] |
| CI-2 | Skips enumerated | every skipped test listed with reason; **no seam test (cross-lane) may be skipped** at the merge SHA — a skip on a seam test is NOT_TESTABLE for that seam, not PASS | FINDING-008 형태B (skip masked the seam) |
| CI-3 | Form-A rewrites narrow, not loosen | the two isolation assertions (`w5h` join-absent, `w5j` engine sha) must be rewritten to measure the lane's **own diff** (e.g. `git diff <lane-base>..<lane-tip> -- l0_collector.py`), not deleted or turned into absolute-hash-of-merged-file; C diffs old vs new assertion and confirms a lane-local violation still fails | FINDING-008 형태A; A rule "시끄러운 실패를 조용한 통과로 바꾸지 마라" |
| CI-4 | Form-B resolved by ruling, not by edit | `test_w5c_splits_the_pair_when_it_is_available` (expected `ICON_ONLY_AX_NAMED`, got `NOT_OBSERVED`) must be closed by an A ruling (which side is right) referenced in COMPLETION; C independently reproduces the pair on a lane2 icon-only fixture through the adapter | FINDING-008 형태B; R16 |
| CI-5 | Δ30 reflected | tie-break key `task_binding_candidate desc, dom_order asc, selector asc`, `BUDGET_EXCEEDED` (14 values), branch set = Δ9 IN10+COND3 present at the COMPLETION SHA — otherwise Δ30 rows stay NOT_TESTABLE and the verdict is at most METHOD_QUALIFIED_WITH_LIMITATIONS | T-A-V3-STEP1-027 |
| CI-6 | Failures = 0 at submission | any non-zero `failures`/`errors` in C's own junit recount at the COMPLETION SHA ⇒ C_HARNESS_DEFECT check first (env), then FAIL_SYSTEMIC candidate | runbook ladder |

## Addendum r4 — empty-pipeline controls added from T-B-V3-BLK-014 (2026-08-28 07:32 KST, before any B COMPLETION)

| # | Check | Pass condition | Source |
|---|---|---|---|
| CI-7 | Silent-zero control (positive control for "the pipeline actually acts") | C runs the runner at the COMPLETION SHA on lane1/lane3 fixtures whose expectation requires ≥1 activation (decoy F2→F3, menu→category→function). A row with `activations=0` that carries no loud failure (exception / refusal / non-null terminal_reason) is **FAIL_SYSTEMIC** and a `denominator_corruption` hard-stop candidate (R9): 0-activation "clean" rows are indistinguishable from real observations and corrupt every denominator. v2 Day-1 MPFED 0/59 was this layer | BLK-014; [[landing-v2-day1-outcome]]; [[verification-requires-control-group]] |
| CI-8 | Contract violation ≠ observation | an internal seam/type-contract failure (binder returns non-Mapping, eligibility value outside enum) must surface as a runner error, never as a terminal_reason row — C greps the raw for rows whose terminal_reason was produced by an exception path (engine log ↔ row cross-check). Whether a *genuine* "0 candidates on a real page" gets its own terminal_reason value is A's decision (BLK-014 decision_required); until ruled, such rows are NOT_TESTABLE, not PASS | BLK-014 decision_required; R11 |
| CI-9 | Eligibility distribution recomputed | C recomputes `mobile_web_eligibility` over the frozen MAIN50 manifest itself (see ACK) and confirms the runner's accepted-value set covers every value that appears; a manifest value outside the enum ⇒ runner cannot start on those targets ⇒ NOT_TESTABLE for them, and the GATE 1 verdict says so explicitly | BLK-014 second defect |
| CI-10 | Credential guard signal crosses the seam | lane4 `forbidden_action_matrix` credential/personal-data fixtures expect the guard to fire; if `PlannedAction` (5 fields) drops `input[type=password]`/field-name signals, `guard_fired_positive_control` grades SYSTEMIC FAIL by silence (already pre-registered, P-74). No REAL_TARGET GO recommendation from C while this is open | BLK-014 safety finding |
