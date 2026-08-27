# lane6_stats — Claude C independent derivation & statistics library (GATE 1 / GATE 3)

Base: worktree `claude_c_assurance_v21` @ 5e05da9. Authority: SSOTV3 04 (§2/§3/§4/§5/§6), 05 (§1/§2/§3/§4/§6), 02 §4, 00 §6/§7, 13.
Pure python3 stdlib (numpy/pandas not required). No B/D code or numbers are read anywhere in this lane.

## Files
| file | purpose |
|---|---|
| `c_flow_derive.py` | library; every function's docstring cites the SSOTV3 clause it implements |
| `test_c_flow_derive.py` | pytest; all expectations hand-computed before implementation (see header comment) |
| `synthetic_family_demo.py` → `demo_output.json` | fixed synthetic family (n=10) through the full pipeline |

pytest result line (`python3 -m pytest test_c_flow_derive.py`): **`17 passed in 0.24s`**

## Functions (c_flow_derive)
- `classify_token(token, *, submit_is_activation=True, form_is_activation=False)` → `{state_changing_activation, task_intent, reveal, dismiss, auth, endpoint}`; raises on non-canonical token (04 §2).
- `derive(task_flow, experienced_flow, *, submit_is_activation, drop_noncanonical=False)` → `activation_depth` (+ `_excl_submit`, `_incl_form` alternatives), `flow_step_count`, `menu_dependency` (+ `_incl_tab`), `nav_container_depth` (+ `nav_anchor_found`), `forced_dismissal_count`, `auth_gate_stage` (+ `_alt_terminal_is_endpoint`), `endpoint_status`, `flow_evaluable`, `sequence_consistent` (experienced − DISMISS == task, 04 §3), `violations` (terminal token not last, dismissal inside task_flow). Accepts lists or `"A > B"` strings. Never raises on contract violations — it flags them.
- `auth_gate_stage_from_sequence(seq, *, terminal_auth_is_endpoint=False)`, `endpoint_status_from_sequence(seq)`.
- `label_relation(visible, accessible, synonym_map, *, casefold=False)` → MATCH / SEMANTIC_EQUIV / DIFFERENT / VISIBLE_ONLY / AX_ONLY / NONE. NFC + whitespace collapse; synonym map is an explicit `{form: canonical_key}` dict (never embeddings, 04 §5).
- `seq_distance(a, b)` → token-level `levenshtein`, `levenshtein_norm` (= lev / max len), `lcs_len`, `lcs_sim` (= LCS / max len), `lcs_sim_dice` (alt).
- `pairwise_matrix(rows)` → n×n Levenshtein-norm and LCS-sim matrices, `n_service`, `n_pairs`, guard string; `unique_signatures(rows)`.
- `family_summary(rows, numeric_vars, categorical_vars)` → numeric: n, n_missing, median, q1/q3 (type-7), iqr, min/max/range; categorical: distribution, k_observed, `entropy_bits`, `entropy_norm` (= H / log2 k_observed). Always reports `n_service`, `n_pairs` and `pseudo_replication_guard = "pairs are cells, not independent n"`. No composite score (05 §3).
- `denominator_chain(candidate, eligible, attempted, evidence_bearing, flow_evaluable, *, family_id, reasons)` → per-stage count / dropped / reasons; **raises** if any later count exceeds an earlier one or is negative (05 §6).
- `entry_zone(x_norm, y_norm, is_floating, is_drawer)` → TOP_LEFT / TOP_CENTER / TOP_RIGHT / MID / BOTTOM / FLOATING / DRAWER.
- `compare_with_mart_row(row, synonym_map=...)` → recompute from raw fields of one `fact_flow_observation` row and diff against B's stored derived values (GATE 3 helper).

## Pre-registered C choices (to be frozen before any real data is seen)
Each is a module constant or keyword flag; where it changes a number the alternative value is reported alongside.

| id | choice | flip / alt |
|---|---|---|
| C-1 | `SUBMIT_QUERY` **is** a state-changing activation (executes a control, changes page state) | `submit_is_activation=False`; `activation_depth_excl_submit` always reported |
| C-2 | `INPUT_QUERY`, `SELECT_ORIGIN`, `SELECT_DESTINATION`, `SELECT_DATE` are typing / form-intent → **not** activation depth (04 §5 "typing 제외") but **are** flow steps | `activation_depth_incl_form` always reported |
| C-3 | reveal tokens = `OPEN_GLOBAL_MENU`, `OPEN_LOCAL_MENU`, `EXPAND_ACCORDION` (the three named in 04 §5); `SWITCH_TAB` is a view switch, not a reveal | `menu_dependency_incl_tab` always reported |
| C-4 | task-intent (flow_step_count) = all canonical tokens except `DISMISS_OBSTRUCTION`, `ENDPOINT_REACHED` (state marker), `ABSTAIN`; `AUTH_GATE` counts ("auth encounter 포함") | — |
| C-5 | `nav_container_depth` anchor = first `SELECT_FUNCTION` or task-body token (form/submit/result/detail); reveals before it are counted; `SELECT_CATEGORY` is not an anchor; no anchor → count reveals before terminal, `nav_anchor_found=False` | — |
| C-6 | auth stage: `BEFORE_TASK_DISCOVERY` if no `SELECT_FUNCTION`/`SELECT_CATEGORY` precedes AUTH_GATE (a bare `OPEN_GLOBAL_MENU` is not discovery); `AT_ENDPOINT` if AUTH_GATE immediately precedes `ENDPOINT_REACHED` **or** is terminal after a task-body token (query submitted / result chosen); else `AFTER_TASK_SELECT`. The 04 §3 example (`OPEN_GLOBAL_MENU > SELECT_FUNCTION > AUTH_GATE`) is therefore `AFTER_TASK_SELECT` | `terminal_auth_is_endpoint=True` (literal reading: any terminal AUTH_GATE = AT_ENDPOINT) → `auth_gate_stage_alt_terminal_is_endpoint` always reported; example becomes `AT_ENDPOINT` |
| C-7 | zone thresholds: `y < 0.15` → TOP band split by x thirds (`x < 1/3` LEFT, `1/3 ≤ x ≤ 2/3` CENTER, `x > 2/3` RIGHT); `y ≥ 0.85` → BOTTOM; else MID. Precedence DRAWER > FLOATING > band. Coordinates outside [0,1] or missing → error (04 §6: raw (x,y) are primary) | constants `ZONE_TOP_Y`, `ZONE_BOTTOM_Y`, `ZONE_X_LEFT`, `ZONE_X_RIGHT` |
| C-8 | `label_relation`: MATCH is case-strict after NFC + whitespace normalisation (04 §5 "exact"); synonym-map lookup is casefold-insensitive | `casefold=True` makes MATCH case-insensitive too |
| C-9 | `ABSTAIN` sequence → `flow_evaluable=False`; all flow-derived fields are `None` (missing), never 0, so family denominators shrink instead of being diluted (05 §6); `forced_dismissal_count` still counted | — |
| C-10 | `menu_dependency` "endpoint 전" = before `ENDPOINT_REACHED`; if endpoint never reached, the whole observed path counts | — |
| C-11 | statistics: median standard; Q1/Q3 = Hyndman–Fan type 7 (numpy default); entropy in bits, `entropy_norm` divides by log2(k **observed**) | `lcs_sim_dice` alt normalisation reported |
| C-12 | `endpoint_status` from a sequence can only resolve REACHED / AUTH_GATE / ABSTAIN; other statuses are evidence-level → `UNRESOLVED_FROM_SEQUENCE`, and C compares only when resolvable | — |

Codebook example (04 §3) under these choices: activation_depth 2, flow_step_count 3, menu_dependency 1, nav_container_depth 1, forced_dismissal_count 1, auth_gate_stage AFTER_TASK_SELECT (alt AT_ENDPOINT), endpoint_status AUTH_GATE.

## Synthetic demo (demo_output.json)
10 fixed rows with varied sequences/labels/zones; all 10 signatures unique; denominator chain
`candidate 10 → eligible_frozen 10 → attempted 10 → evidence_bearing 10 → flow_evaluable 9` (S10 ABSTAIN).
`family_summary` shows `activation_depth` n=9 / n_missing=1, `n_service=10`, `n_pairs=45`, guard string present.

## GATE 3 procedure (recompute-and-compare)
1. Load B's promoted `fact_flow_observation` rows (02 §4) for the final 50; per row call `compare_with_mart_row(row, synonym_map=FROZEN_MAP)` — it reads only `task_flow_sequence`, `experienced_flow_sequence`, `visible_label_text`, `accessible_name`, `entry_x_norm/entry_y_norm`, `nav_container_type`; B's derived columns are used only in the `diffs` output. Where a `fact_flow_step` table exists, rebuild the two sequences from `action_token` ordered by `step_index` first and diff them against B's stored sequences (raw-of-raw check).
2. Per family (5 × n=10): `family_summary`, `pairwise_matrix`, `unique_signatures` on C's recomputed columns; compare medians/IQR/entropy/matrices cell-by-cell against B's family report.
3. `denominator_chain` per family from A's freeze manifest (candidate/eligible) + B's attempt log + C's own `flow_evaluable`/evidence flags; any non-monotonic chain is a hard blocker.
4. Any `violations` or `sequence_consistent=False` row, any `diffs` non-empty row, and any choice-sensitive result (primary vs alt disagree on a conclusion) go to A as exact-evidence blockers. Pairwise results are reported as 45 cells per family, never as n=45.
