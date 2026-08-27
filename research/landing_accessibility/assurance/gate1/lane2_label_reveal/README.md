# GATE 1 · lane2 — visible label / accessible name separation + reveal direction (C fixtures)

**Author:** Claude C (Independent Scientific Assurance). Base `f5e3c8ea`. Authority: `SSOTV3/04 §4 §5 §6 §7`, `00 §8`, `02 §3`, `03 §3-§4`.
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

## Fixtures → expected values (all confirmed by the run below)
| fixture | ctl | visible | ax_name | src | modality (S0) | relation | ctype | nav / dir | dep/depth | zone |
|---|---|---|---|---|---|---|---|---|---|---|
| label_explicit_text | POS | 배송조회 | 배송조회 | VISIBLE_TEXT | EXPLICIT_TEXT | MATCH | TEXT_BUTTON | NONE/NONE | 0/0 | MID |
| label_icon_text | POS | 배송조회 | 배송조회 | VISIBLE_TEXT | ICON_TEXT | MATCH | ICON_TEXT | NONE/NONE | 0/0 | TOP_CENTER |
| label_icon_only_ax_named | POS | "" | 배송조회 | ARIA_LABEL | ICON_ONLY_AX_NAMED | AX_ONLY | ICON_ONLY | NONE/NONE | 0/0 | TOP_RIGHT |
| label_icon_only_unnamed | NEG | "" | "" | NONE | ICON_ONLY_UNNAMED | NONE | ICON_ONLY | NONE/NONE | 0/0 | FLOATING |
| label_aria_labelledby_differs | NEG | 조회 | 운송장 배송조회 | ARIA_LABELLEDBY | EXPLICIT_TEXT | DIFFERENT | TEXT_BUTTON | NONE/NONE | 0/0 | MID |
| label_alt_title_value (entry=img alt) | POS | "" | 배송조회 | ALT | ICON_ONLY_AX_NAMED | AX_ONLY | ICON_ONLY | NONE/NONE | 0/0 | TOP_CENTER |
| ↳ aux-title / aux-value | POS | "" / 배송조회 | 배송조회 / 배송조회 | TITLE / VALUE | ICON_ONLY_AX_NAMED / EXPLICIT_TEXT | AX_ONLY / MATCH | ICON_ONLY / TEXT_BUTTON | — | — | — |
| label_pseudo_element_text | NEG | 배송조회 (PSEUDO_ELEMENT) | 배송조회 | VISIBLE_TEXT | EXPLICIT_TEXT | MATCH | TEXT_BUTTON | NONE/NONE | 0/0 | MID |
| label_hidden_until_reveal | POS | "" → 배송조회 | "" → 배송조회 | NONE → VISIBLE_TEXT | HIDDEN_UNTIL_REVEAL | NONE → MATCH | TEXT_LINK | MODAL_MENU/CENTER (Δ≈0) | 1/1 | DRAWER |
| drawer_left | POS | "" → 배송조회 | "" → 배송조회 | NONE → VISIBLE_TEXT | HIDDEN_UNTIL_REVEAL | NONE → MATCH | TEXT_LINK | LEFT_DRAWER/LEFT (dx +312) | 1/1 | DRAWER |
| drawer_right | POS | same | same | same | HIDDEN_UNTIL_REVEAL | same | TEXT_LINK | RIGHT_DRAWER/RIGHT (dx −312) | 1/1 | DRAWER |
| drawer_mislabeled_left_class_but_right_geometry | NEG | same | same | same | HIDDEN_UNTIL_REVEAL | same | TEXT_LINK | RIGHT_DRAWER/RIGHT (dx −312); naive name guess = LEFT | 1/1 | DRAWER |
| bottom_sheet | POS | same | same | same | HIDDEN_UNTIL_REVEAL | same | TEXT_LINK | BOTTOM_SHEET/BOTTOM (dy −506) | 1/1 | DRAWER |
| top_dropdown | POS | same | same | same | HIDDEN_UNTIL_REVEAL | same | TEXT_LINK | TOP_DROPDOWN/TOP (dy +312) | 1/1 | DRAWER |
| inline_expand | POS | same | same | same | HIDDEN_UNTIL_REVEAL | same | TEXT_LINK | INLINE_EXPAND/INLINE (no box before) | 1/1 | MID |

## measure_geometry.py output (run 2026-08-28, chromium 151, Playwright 1.62)
```
fixture                                         | ctl | visible | ax_name    | ax_src          | modality            | relation  | ctype       | s0 | dir    | dx   | dy   | zone       | x,y       | naive  | result
label_explicit_text                             | POS | '배송조회'  | '배송조회'     | VISIBLE_TEXT    | EXPLICIT_TEXT       | MATCH     | TEXT_BUTTON | T  | NONE   |      |      | MID        | 0.20,0.26 |        | PASS
label_icon_text                                 | POS | '배송조회'  | '배송조회'     | VISIBLE_TEXT    | ICON_TEXT           | MATCH     | ICON_TEXT   | T  | NONE   |      |      | TOP_CENTER | 0.49,0.03 |        | PASS
label_icon_only_ax_named                        | POS | ''      | '배송조회'     | ARIA_LABEL      | ICON_ONLY_AX_NAMED  | AX_ONLY   | ICON_ONLY   | T  | NONE   |      |      | TOP_RIGHT  | 0.91,0.03 |        | PASS
label_icon_only_unnamed                         | NEG | ''      | ''         | NONE            | ICON_ONLY_UNNAMED   | NONE      | ICON_ONLY   | T  | NONE   |      |      | FLOATING   | 0.89,0.88 |        | PASS
label_aria_labelledby_differs                   | NEG | '조회'    | '운송장 배송조회' | ARIA_LABELLEDBY | EXPLICIT_TEXT       | DIFFERENT | TEXT_BUTTON | T  | NONE   |      |      | MID        | 0.17,0.26 |        | PASS
label_alt_title_value                           | POS | ''      | '배송조회'     | ALT             | ICON_ONLY_AX_NAMED  | AX_ONLY   | ICON_ONLY   | T  | NONE   |      |      | TOP_CENTER | 0.46,0.03 |        | PASS
label_pseudo_element_text                       | NEG | '배송조회'  | '배송조회'     | VISIBLE_TEXT    | EXPLICIT_TEXT       | MATCH     | TEXT_BUTTON | T  | NONE   |      |      | MID        | 0.20,0.26 |        | PASS
label_hidden_until_reveal                       | POS | ''      | ''         | NONE            | HIDDEN_UNTIL_REVEAL | NONE      | TEXT_LINK   | F  | CENTER | +0   | +0   | DRAWER     | 0.50,0.22 | ?      | PASS
drawer_left                                     | POS | ''      | ''         | NONE            | HIDDEN_UNTIL_REVEAL | NONE      | TEXT_LINK   | F  | LEFT   | +312 | +0   | DRAWER     | 0.40,0.22 | LEFT   | PASS
drawer_right                                    | POS | ''      | ''         | NONE            | HIDDEN_UNTIL_REVEAL | NONE      | TEXT_LINK   | F  | RIGHT  | -312 | +0   | DRAWER     | 0.60,0.22 | RIGHT  | PASS
drawer_mislabeled_left_class_but_right_geometry | NEG | ''      | ''         | NONE            | HIDDEN_UNTIL_REVEAL | NONE      | TEXT_LINK   | F  | RIGHT  | -312 | +0   | DRAWER     | 0.60,0.22 | LEFT   | PASS
bottom_sheet                                    | POS | ''      | ''         | NONE            | HIDDEN_UNTIL_REVEAL | NONE      | TEXT_LINK   | F  | BOTTOM | +0   | -506 | DRAWER     | 0.50,0.62 | BOTTOM | PASS
top_dropdown                                    | POS | ''      | ''         | NONE            | HIDDEN_UNTIL_REVEAL | NONE      | TEXT_LINK   | F  | TOP    | +0   | +312 | DRAWER     | 0.50,0.22 | TOP    | PASS
inline_expand                                   | POS | ''      | ''         | NONE            | HIDDEN_UNTIL_REVEAL | NONE      | TEXT_LINK   | F  | INLINE |      |      | MID        | 0.50,0.38 | ?      | PASS
RESULT: 14/14 PASS, non-file requests aborted total=0
```
(`visible`/`ax_name` columns are the S0 row; post-reveal values are in `out/measure_result.json → s1_after_reveal`. `naive` = direction a
name-based heuristic would report; on the negative control it says LEFT while geometry says RIGHT.)

## How the runner adapter compares B/D output to these
For each fixture, the adapter feeds the runner the `file://` URL + `entry_selector` (task binding is lane1's concern, not tested here) and
compares the runner's `fact_surface_state` S0 row and, where `reveal_steps` exist, its first `fact_flow_step` after-state:
- exact (after NFC + whitespace normalization): `visible_label_text`, `accessible_name`, `accessible_name_source`, `label_relation`,
  `entry_label_modality`, `entry_control_type`, `nav_container_type`, `reveal_direction`, `menu_dependency`, `nav_container_depth`,
  `s0_task_control_visible`;
- geometry: runner `bbox_before`/`bbox_after` center delta must have the sign/axis in `after_reveal.motion` (|Δ| ≥ `min_abs_delta_px`);
  `entry_x_norm`/`entry_y_norm` within ±0.02 of `out/measure_result.json`; `entry_zone` compared second, under `meta.zone_rule_C_provisional`;
- pseudo-element fixture: accept either `visible_label_text="배송조회"+provenance=PSEUDO_ELEMENT` or `""` + a separate rendered-pseudo field;
  a bare `""` with no provenance FAILS (04 §7);
- negative controls must fail in the *predicted* way if the runner is wrong (unnamed→AX_NAMED, substring→MATCH, class-name→LEFT).
Any mismatch is a GATE 1 blocker with the exact field/value pair as evidence; expectations are not edited to fit runner output.

## Ambiguities documented (see `EXPECTATIONS.json` per-fixture `ambiguity` / `meta`)
1. **Zone thresholds** are not in 04 §6 (only "keep raw center, zone is a summary"). C declares provisional thresholds (TOP <0.12, BOTTOM >0.88,
   thirds on x, FLOATING = small fixed box, DRAWER = inside an opened fixed/absolute reveal container). Raw x/y_norm is the primary comparison.
2. **Pseudo-element label**: Chromium *and* Playwright's accname engine both include `::before` content, so AX name = 배송조회 (source
   `contents`). visible text is rendered but absent from DOM text — recorded with provenance PSEUDO_ELEMENT per 04 §7. Two encodings accepted.
3. **S0 row of a hidden control**: control not rendered ⇒ not in the AX tree ⇒ C stores `""`/`NONE`/`NONE` and modality HIDDEN_UNTIL_REVEAL;
   the control's own modality/relation is reported on the post-reveal state. A runner storing `null` is equivalent; storing the post-reveal
   name in the S0 row is not.
4. **`input[type=submit]` value**: rendered caption ⇒ visible text (provenance INPUT_VALUE) *and* `accessible_name_source=VALUE`;
   `innerText` of an `<input>` is empty, so a naive reader would mis-report — hence kept as an aux control.
5. **Substring ≠ equivalence** (labelledby fixture): 04 §5 allows exact match or a fixed synonym map only; `조회` ⊂ `운송장 배송조회` is DIFFERENT.
6. **inline_expand**: menu_dependency=1 / depth=1 because EXPAND_ACCORDION is a reveal token (04 §5) although no overlay container exists.

## Corrections made during the run (rule never weakened)
- Run 1: `label_alt_title_value` FAIL — fixture bug (double quotes inside the `<img src="data:…">` SVG broke the attribute). Fixed the fixture
  (single quotes inside the data-URI); expectation unchanged.
- Run 1: `drawer_right` measured dx = −220 (fractional bbox) — the script sampled before the CSS transition had started and then read
  mid-animation. Fixed the script to wait two rAF ticks + `document.getAnimations()` completion before settling; expectation unchanged.
