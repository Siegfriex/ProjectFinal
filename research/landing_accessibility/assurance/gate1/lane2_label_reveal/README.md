# GATE 1 · lane2 — visible label / accessible name separation + reveal direction (C fixtures)

**Author:** Claude C (Independent Scientific Assurance). Base `f5e3c8ea`; r2 on `claude-c/assurance-v21` after `67f473b` (A rulings T-A-V3-STEP1-003 R7 · STEP1-011 · STEP1-012 and C decision C-DECISION_REQUEST-031138 applied). Authority: `SSOTV3/04 §4 §5 §6 §7`, `00 §8`, `02 §3`, `03 §3-§4`; A tickets above where ruled.
**Independence:** every fixture and every value in `EXPECTATIONS.json` was written by C from the SSOT text and the accname / HTML-AAM
algorithms *before* the first run. No B worktree, B code, or B test was read. Nothing here imports B.

## Purpose
Offline, deterministic evidence for two GATE 1 checks:
(a) `visible_label_text` and `accessible_name` are stored **separately** and `accessible_name_source` / `label_relation` /
`entry_label_modality` are classified per 04 §4-§5; (b) `nav_container_type` / `reveal_direction` are derived from **actual
geometry/state change**, never from class/id/data/aria naming.

## Files
- `fixtures/*.html` — 14 self-contained mobile pages (390×844, inline CSS/JS/SVG, data-URI only). Exactly one `[data-c-target=entry]`
  per page (`label_alt_title_value` adds two `aux-*` controls) plus distractors (검색/로그인/주문내역/배송정책 안내/고객센터/bottom nav).
- `EXPECTATIONS.json` — a-priori expected values + C's explicit derivation rules (`meta.*`), POSITIVE/NEGATIVE control flags, ambiguities.
- `measure_geometry.py` — Playwright chromium headless, `is_mobile`, `route("**/*")` aborts everything not `file://`. Reads the control via
  (1) CDP `Accessibility.getPartialAXTree` (name + name sources, primary), (2) Playwright `locator.aria_snapshot()` (second accname engine,
  must agree), (3) DOM fallbacks (`aria-label` / `innerText`, recorded only). Records bbox before/after the reveal toggle, waits for
  `document.getAnimations()` to finish, infers direction from the bbox delta, prints the table, exit 0 iff all PASS.
- `out/measure_result.json` — full per-fixture records (raw AX sources, both bboxes, container geometry, diffs).

Run: `source /home/sieg/projects-wsl/ProjectFinal/scripts/activate.sh && python3 measure_geometry.py`

## Fixtures → expected values (all confirmed by the run below; zone column = A R7 primary, geometry-only band in parentheses; every reveal fixture also expects `nav_container_chain=[<type>]`, S0 geometry `null`, `dom_ax_divergence=false`)
| fixture | ctl | visible | ax_name | src | modality (S0) | relation | ctype | nav / dir | dep/depth | zone R7 (band) | observed_state |
|---|---|---|---|---|---|---|---|---|---|---|---|
| label_explicit_text | POS | 배송조회 | 배송조회 | VISIBLE_TEXT | EXPLICIT_TEXT | MATCH | TEXT_BUTTON | NONE/NONE | 0/0 | TOP_LEFT (TOP_LEFT) | S0 |
| label_icon_text | POS | 배송조회 | 배송조회 | VISIBLE_TEXT | ICON_TEXT | MATCH | ICON_TEXT | NONE/NONE | 0/0 | FLOATING (TOP_CENTER) | S0 |
| label_icon_only_ax_named | POS | "" | 배송조회 | ARIA_LABEL | ICON_ONLY_AX_NAMED | AX_ONLY | ICON_ONLY | NONE/NONE | 0/0 | FLOATING (TOP_RIGHT) | S0 |
| label_icon_only_unnamed | NEG | "" | "" | NONE | ICON_ONLY_UNNAMED | NONE | ICON_ONLY | NONE/NONE | 0/0 | FLOATING (BOTTOM) | S0 |
| label_aria_labelledby_differs | NEG | 조회 | 운송장 배송조회 | ARIA_LABELLEDBY | EXPLICIT_TEXT | DIFFERENT | TEXT_BUTTON | NONE/NONE | 0/0 | TOP_LEFT (TOP_LEFT) | S0 |
| label_alt_title_value (entry=img alt) | POS | "" | 배송조회 | ALT | ICON_ONLY_AX_NAMED | AX_ONLY | ICON_ONLY | NONE/NONE | 0/0 | FLOATING (TOP_CENTER) | S0 |
| ↳ aux-title / aux-value | POS | "" / 배송조회 | 배송조회 / 배송조회 | TITLE / VALUE | ICON_ONLY_AX_NAMED / EXPLICIT_TEXT | AX_ONLY / MATCH | ICON_ONLY / TEXT_BUTTON | — | — | — | — |
| label_pseudo_element_text | NEG | 배송조회 (PSEUDO_ELEMENT) | 배송조회 | VISIBLE_TEXT | EXPLICIT_TEXT | MATCH | TEXT_BUTTON | NONE/NONE | 0/0 | TOP_LEFT (TOP_LEFT) | S0 |
| label_hidden_until_reveal | POS | NOT_OBSERVED → 배송조회 | NOT_OBSERVED → 배송조회 | NOT_OBSERVED → VISIBLE_TEXT | HIDDEN_UNTIL_REVEAL | NOT_OBSERVED → MATCH | TEXT_LINK | MODAL_MENU/CENTER (Δ≈0) | 1/1 | DRAWER (TOP_CENTER) | POST_REVEAL:MODAL_MENU |
| drawer_left | POS | NOT_OBSERVED → 배송조회 | NOT_OBSERVED → 배송조회 | NOT_OBSERVED → VISIBLE_TEXT | HIDDEN_UNTIL_REVEAL | NOT_OBSERVED → MATCH | TEXT_LINK | LEFT_DRAWER/LEFT (dx +312) | 1/1 | DRAWER (TOP_CENTER) | POST_REVEAL:LEFT_DRAWER |
| drawer_right | POS | same | same | same | HIDDEN_UNTIL_REVEAL | same | TEXT_LINK | RIGHT_DRAWER/RIGHT (dx −312) | 1/1 | DRAWER (TOP_CENTER) | POST_REVEAL:RIGHT_DRAWER |
| drawer_mislabeled_left_class_but_right_geometry | NEG | same | same | same | HIDDEN_UNTIL_REVEAL | same | TEXT_LINK | RIGHT_DRAWER/RIGHT (dx −312); naive name guess = LEFT | 1/1 | DRAWER (TOP_CENTER) | POST_REVEAL:RIGHT_DRAWER |
| bottom_sheet | POS | same | same | same | HIDDEN_UNTIL_REVEAL | same | TEXT_LINK | BOTTOM_SHEET/BOTTOM (dy −506) | 1/1 | DRAWER (MID) | POST_REVEAL:BOTTOM_SHEET |
| top_dropdown | POS | same | same | same | HIDDEN_UNTIL_REVEAL | same | TEXT_LINK | TOP_DROPDOWN/TOP (dy +312) | 1/1 | DRAWER (TOP_CENTER) | POST_REVEAL:TOP_DROPDOWN |
| inline_expand | POS | same | same | same | HIDDEN_UNTIL_REVEAL | same | TEXT_LINK | INLINE_EXPAND/INLINE (no box before) | 1/1 | DRAWER (MID) | POST_REVEAL:INLINE_EXPAND |

## measure_geometry.py output (run r2 2026-08-28 after R7 / STEP1-012 edits, chromium headless, Playwright, file:// only)
```
fixture                                         | ctl | visible        | ax_name        | ax_src          | modality            | relation     | ctype       | s0 | dir    | dx   | dy   | zone(R7) | band       | x,y       | observed_state            | naive  | result
----------------------------------------------- | --- | -------------- | -------------- | --------------- | ------------------- | ------------ | ----------- | -- | ------ | ---- | ---- | -------- | ---------- | --------- | ------------------------- | ------ | ------
label_explicit_text                             | POS | '배송조회'         | '배송조회'         | VISIBLE_TEXT    | EXPLICIT_TEXT       | MATCH        | TEXT_BUTTON | T  | NONE   |      |      | TOP_LEFT | TOP_LEFT   | 0.20,0.26 | S0                        |        | PASS  
label_icon_text                                 | POS | '배송조회'         | '배송조회'         | VISIBLE_TEXT    | ICON_TEXT           | MATCH        | ICON_TEXT   | T  | NONE   |      |      | FLOATING | TOP_CENTER | 0.49,0.03 | S0                        |        | PASS  
label_icon_only_ax_named                        | POS | ''             | '배송조회'         | ARIA_LABEL      | ICON_ONLY_AX_NAMED  | AX_ONLY      | ICON_ONLY   | T  | NONE   |      |      | FLOATING | TOP_RIGHT  | 0.91,0.03 | S0                        |        | PASS  
label_icon_only_unnamed                         | NEG | ''             | ''             | NONE            | ICON_ONLY_UNNAMED   | NONE         | ICON_ONLY   | T  | NONE   |      |      | FLOATING | BOTTOM     | 0.89,0.88 | S0                        |        | PASS  
label_aria_labelledby_differs                   | NEG | '조회'           | '운송장 배송조회'     | ARIA_LABELLEDBY | EXPLICIT_TEXT       | DIFFERENT    | TEXT_BUTTON | T  | NONE   |      |      | TOP_LEFT | TOP_LEFT   | 0.17,0.26 | S0                        |        | PASS  
label_alt_title_value                           | POS | ''             | '배송조회'         | ALT             | ICON_ONLY_AX_NAMED  | AX_ONLY      | ICON_ONLY   | T  | NONE   |      |      | FLOATING | TOP_CENTER | 0.46,0.03 | S0                        |        | PASS  
label_pseudo_element_text                       | NEG | '배송조회'         | '배송조회'         | VISIBLE_TEXT    | EXPLICIT_TEXT       | MATCH        | TEXT_BUTTON | T  | NONE   |      |      | TOP_LEFT | TOP_LEFT   | 0.20,0.26 | S0                        |        | PASS  
label_hidden_until_reveal                       | POS | 'NOT_OBSERVED' | 'NOT_OBSERVED' | NOT_OBSERVED    | HIDDEN_UNTIL_REVEAL | NOT_OBSERVED | TEXT_LINK   | F  | CENTER | +0   | +0   | DRAWER   | TOP_CENTER | 0.50,0.22 | POST_REVEAL:MODAL_MENU    | ?      | PASS  
drawer_left                                     | POS | 'NOT_OBSERVED' | 'NOT_OBSERVED' | NOT_OBSERVED    | HIDDEN_UNTIL_REVEAL | NOT_OBSERVED | TEXT_LINK   | F  | LEFT   | +312 | +0   | DRAWER   | TOP_CENTER | 0.40,0.22 | POST_REVEAL:LEFT_DRAWER   | LEFT   | PASS  
drawer_right                                    | POS | 'NOT_OBSERVED' | 'NOT_OBSERVED' | NOT_OBSERVED    | HIDDEN_UNTIL_REVEAL | NOT_OBSERVED | TEXT_LINK   | F  | RIGHT  | -312 | +0   | DRAWER   | TOP_CENTER | 0.60,0.22 | POST_REVEAL:RIGHT_DRAWER  | RIGHT  | PASS  
drawer_mislabeled_left_class_but_right_geometry | NEG | 'NOT_OBSERVED' | 'NOT_OBSERVED' | NOT_OBSERVED    | HIDDEN_UNTIL_REVEAL | NOT_OBSERVED | TEXT_LINK   | F  | RIGHT  | -312 | +0   | DRAWER   | TOP_CENTER | 0.60,0.22 | POST_REVEAL:RIGHT_DRAWER  | LEFT   | PASS  
bottom_sheet                                    | POS | 'NOT_OBSERVED' | 'NOT_OBSERVED' | NOT_OBSERVED    | HIDDEN_UNTIL_REVEAL | NOT_OBSERVED | TEXT_LINK   | F  | BOTTOM | +0   | -506 | DRAWER   | MID        | 0.50,0.62 | POST_REVEAL:BOTTOM_SHEET  | BOTTOM | PASS  
top_dropdown                                    | POS | 'NOT_OBSERVED' | 'NOT_OBSERVED' | NOT_OBSERVED    | HIDDEN_UNTIL_REVEAL | NOT_OBSERVED | TEXT_LINK   | F  | TOP    | +0   | +312 | DRAWER   | TOP_CENTER | 0.50,0.22 | POST_REVEAL:TOP_DROPDOWN  | TOP    | PASS  
inline_expand                                   | POS | 'NOT_OBSERVED' | 'NOT_OBSERVED' | NOT_OBSERVED    | HIDDEN_UNTIL_REVEAL | NOT_OBSERVED | TEXT_LINK   | F  | INLINE |      |      | DRAWER   | MID        | 0.50,0.38 | POST_REVEAL:INLINE_EXPAND | ?      | PASS  
RESULT: 14/14 PASS, non-file requests aborted total=0
```
(`visible`/`ax_name` columns are the S0 row — `NOT_OBSERVED` for reveal-gated controls per GAP-04; post-reveal values are in `out/measure_result.json → s1_after_reveal`. `zone(R7)` / `band` / `x,y` are taken at `observed_state`. `naive` = direction a
name-based heuristic would report; on the negative control it says LEFT while geometry says RIGHT.)

r1 → r2 zone changes (expected values re-derived before the r2 run, from r1 raw x/y): label_explicit_text · label_aria_labelledby_differs · label_pseudo_element_text MID→TOP_LEFT (y=0.26 < 1/3); label_icon_text · label_icon_only_ax_named · label_alt_title_value TOP_*→FLOATING (control inside the `position:fixed` header — C's self-or-ancestor reading of R7 FLOATING, band kept as `entry_zone_band_R7`); inline_expand MID→DRAWER (R7 DRAWER = the container that made menu_dependency=1, INLINE_EXPAND included). No raw x/y changed.

## How the runner adapter compares B/D output to these
For each fixture, the adapter feeds the runner the `file://` URL + `entry_selector` (task binding is lane1's concern, not tested here) and
compares the runner's `fact_surface_state` S0 row and, where `reveal_steps` exist, its first `fact_flow_step` after-state:
- exact (after NFC + whitespace normalization): `visible_label_text`, `accessible_name`, `accessible_name_source`, `label_relation`,
  `entry_label_modality`, `entry_control_type`, `nav_container_type`, `reveal_direction`, `menu_dependency`, `nav_container_depth`,
  `s0_task_control_visible`;
- geometry: runner `bbox_before`/`bbox_after` center delta must have the sign/axis in `after_reveal.motion` (|Δ| ≥ `min_abs_delta_px`);
  `entry_x_norm`/`entry_y_norm` within ±0.02 of `out/measure_result.json` at the row's `entry_observed_state`; `entry_zone` compared second, under `meta.zone_rule_A_R7` (and `entry_zone_band_R7` as the declared sensitivity);
- STEP1-012 fields: `entry_observed_state` exact (`S0` or `POST_REVEAL:<nav_container_type>`); `nav_container_chain` exact list (len == `nav_container_depth`); `dom_ax_divergence` must be `false` on every fixture (both channels agree here) — a runner reporting `true` is itself a finding to inspect, not an automatic FAIL; S0 row of a reveal-gated control: numeric geometry `null` (never 0), text/categorical `NOT_OBSERVED` (never `''`), and no mixing inside the row (GAP-04);
- pseudo-element fixture: accept either `visible_label_text="배송조회"+provenance=PSEUDO_ELEMENT` or `""` + a separate rendered-pseudo field;
  a bare `""` with no provenance FAILS (04 §7);
- negative controls must fail in the *predicted* way if the runner is wrong (unnamed→AX_NAMED, substring→MATCH, class-name→LEFT).
Any mismatch is a GATE 1 blocker with the exact field/value pair as evidence; expectations are not edited to fit runner output.

## Ambiguities documented (see `EXPECTATIONS.json` per-fixture `ambiguity` / `meta`)
1. **Zone thresholds** are not in 04 §6 (only "keep raw center, zone is a summary"). C's provisional thresholds (r1: TOP <0.12, BOTTOM >0.88, FLOATING size cap) are
   **withdrawn**; A T-A-V3-STEP1-003 R7 fixes y terciles, x terciles inside TOP, `[a,b)` boundaries, DRAWER > FLOATING > geometry, no FLOATING size cap. One reading C had to
   make: R7's FLOATING ("computed position fixed|sticky, pinned to the viewport") is applied self-OR-ancestor, so controls inside the fixed header are FLOATING; the self-only
   reading is kept visible as `entry_zone_band_R7`. Raw x/y_norm stays the primary comparison.
2. **Pseudo-element label**: Chromium *and* Playwright's accname engine both include `::before` content, so AX name = 배송조회 (source
   `contents`). visible text is rendered but absent from DOM text — recorded with provenance PSEUDO_ELEMENT per 04 §7. Two encodings accepted.
3. **S0 row of a hidden control**: control not rendered ⇒ not in the AX tree ⇒ C stores `""`/`NONE`/`NONE` and modality HIDDEN_UNTIL_REVEAL;
   the control's own modality/relation is reported on the post-reveal state. A runner storing `null` is equivalent; storing the post-reveal
   name in the S0 row is not.
4. **`input[type=submit]` value**: rendered caption ⇒ visible text (provenance INPUT_VALUE) *and* `accessible_name_source=VALUE`;
   `innerText` of an `<input>` is empty, so a naive reader would mis-report — hence kept as an aux control.
5. **Substring ≠ equivalence** (labelledby fixture): 04 §5 allows exact match or a fixed synonym map only; `조회` ⊂ `운송장 배송조회` is DIFFERENT.
6. **inline_expand**: menu_dependency=1 / depth=1 because EXPAND_ACCORDION is a reveal token (04 §5) although no overlay container exists; under R7 its zone is DRAWER (the in-flow accordion panel is the reveal-requiring container), band MID.
7. **Synonym map shape (P-30, C-decided in C-DECISION_REQUEST-031138, A confirmed T-A-V3-STEP1-011)**: the frozen shape is `canonical → [forms]` with identity implicit — exactly `meta.synonym_map_fixed` as it stands; lane6's lookup is made bidirectional, lane2 expectations are unchanged.
8. **A T-A-V3-STEP1-012 folded in (r2)**: GAP-07 `entry_observed_state` (reveal fixtures → `POST_REVEAL:<type>`, `s0_task_control_visible` stays an S0 fact = false); GAP-06 `nav_container_type` = innermost container + `nav_container_chain` (all fixtures single-level); GAP-04 null convention on the S0 row of hidden controls; GAP-05 `s0_task_control_visible` = bbox ∩ S0 viewport ∧ hit-testable at centre (no occlusion threshold; script now hit-tests); DOM/AX divergence flag recorded (false on all 14: DOM and AX agree on existence at the observed state). Values other than zones did not change.

## Corrections made during the run (rule never weakened)
- Run 1: `label_alt_title_value` FAIL — fixture bug (double quotes inside the `<img src="data:…">` SVG broke the attribute). Fixed the fixture
  (single quotes inside the data-URI); expectation unchanged.
- Run 1: `drawer_right` measured dx = −220 (fractional bbox) — the script sampled before the CSS transition had started and then read
  mid-animation. Fixed the script to wait two rAF ticks + `document.getAnimations()` completion before settling; expectation unchanged.
