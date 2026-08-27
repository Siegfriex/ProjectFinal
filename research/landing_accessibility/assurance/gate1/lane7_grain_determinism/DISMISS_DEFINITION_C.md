# DISMISS_DEFINITION_C — `dismiss_control_exists` family, C operational definition (pre-registered)

**Owner**: Claude C (independent assurance plane). **Status**: PRE-REGISTERED before `converge_check.py` was first run.
**Authority**: SSOTV3 `02_DATA_SCHEMA` §5 (`fact_task_obstruction`), `03_COLLECTION_MEASUREMENT_SPEC` §3, §9,
`04_FLOW_CODEBOOK` §2 (`DISMISS_OBSTRUCTION`), §4 (`task_control_occlusion`, `forced_dismissal_count`), §7;
`REFERENCE_DEFINITIONS.md` (`NAME_ABSENT` sentinel, "한 interrupt 당 정확히 1회"). Nothing here derives from B code.
**Revision log**: v1 (pre-registration) → v1.1 after convergence run, see §8 → **v1.2** after C's result-blind reconciliation with lane3 (`C-DECISION_REQUEST-031138` `c_decides_itself` P-23 / P-24, confirmed by A in `T-A-V3-STEP1-011`): `task_control_occlusion` primary = hit-test on the current-state path control, `dismiss_required_for_task` primary = blocking proof; the v1.1 geometric / aria-modal rules survive only as `occlusion_geom_crosscheck` and `dismiss_required_signal` (§4, §8 A8–A9). Numbers were never edited to force convergence.

## 1. Why three axes

`dismiss_control_exists` is a boolean that can be reported at three grains, over two populations, from two sources.
A number reported without all three axes is not comparable. Every C table names `(unit, population, source)`.

| Axis | Values | Meaning |
|---|---|---|
| **unit** | `target` / `container` / `step` | row = service×task observation / one interrupt container (`interrupt_id`) / one prospective `DISMISS_OBSTRUCTION` step |
| **population** | `all` / `blocking` | all interrupt containers detected at S0 (03 §9: popup/modal/banner/fixed/sticky) / only containers with `dismiss_required_for_task = True` |
| **source** | `PROBE` / `DOM_AX` | B-probe raw field `raw_features.dismiss_control_candidates` (impl_A) / C derivation from DOM + inline CSS + ARIA (impl_B) |

## 2. Objects

- **Viewport** V = (0,0,390,844) CSS px, state S0 (03 §1, §3). All geometry is S0 unless stated.
- **Task control** T = the frozen task-entry control (03 §4). Fixtures mark it `data-c-control="task-entry"`; the probe carries `task_control.bbox`. Used only for the geometric cross-check.
- **Path control** P = the control the frozen path activates next in the CURRENT state (lane3: the hamburger at S0 when the function is menu-hidden; here T itself, since every fixture's entry control is visible at S0). Fixtures mark it `data-c-path-control="S0"`; the probe carries `path_control.{bbox, hit_grid}` where `hit_grid` is the 9×9 `elementFromPoint` emission on P (lane3 sampling `x = bx + (i+0.5)·bw/9`, `y = by + (j+0.5)·bh/9`; out-of-viewport points dropped from the denominator). When no path control is defined the hit-test primary is `NULL` and only the geometric cross-check is reported.
- **Interrupt container** = an element that is (a) `role=dialog|alertdialog`, or (b) positioned `fixed`/`sticky`, and is **not** an ancestor-or-self of T, and is not nested inside another container (outermost wins). Its rect = the element's own rect (a full-viewport backdrop root gives the full viewport). Document order defines `dom_order`.
- **Dismiss control candidate** of a container = an element inside the container subtree (or outside with `aria-controls` = container id) whose tag/role is `button`, `a[href]`, `input[type=button|submit|image]`, `[role=button|link]`, **and** whose DOM naming string (first non-empty of `aria-label` → `aria-labelledby` text → subtree text incl. `img[alt]` → `title` → `value`), NFKC-normalised, case-folded, whitespace/`.`/`_`/`-` stripped, satisfies the **dismiss lexicon**:
  equals one of `닫기 닫음 창닫기 팝업닫기 레이어닫기 close dismiss closepopup x × ✕ ✖`, or contains `닫기`, `보지않`, `열지않`; **or** whose `id`/`class` matches `/(^|[-_ ])(close|dismiss|btn-?x)([-_ ]|$)/i`.
  Identification uses DOM naming **regardless of visibility/exposure** (a `display:none` 닫기 is still a candidate — that is what `exists ≠ visible` measures).
  **Excluded by pre-registration**: consent/decision words (`확인 동의 취소 아니오 예 로그인`) — behaviour-based identification ("this button happens to close the layer") requires activation (L0-c) and is recorded as `dismiss_succeeded`, never as `exists`.

## 3. Candidate-level facts (both sources must yield these)

| fact | rule |
|---|---|
| `rendered` | not (`display:none` / `visibility:hidden` on self or ancestor, `hidden` attr, zero-area box) |
| `visible_s0` | `rendered` ∧ area(bbox ∩ V) > 0 — CSS-rendered **and** inside the S0 viewport. Off-fold (needs scroll) ⇒ False |
| `ax_exposed` | `rendered` ∧ no `aria-hidden="true"` on self or ancestor |
| `hittable_s0` | `visible_s0` ∧ the bbox centre is not covered by another container whose stacking order is higher (`z-index` desc, then later `dom_order`) |
| `accessible_name` | if `ax_exposed`: AX-computed name (`aria-label` → `aria-labelledby` → subtree text/alt → `title` → `value`), whitespace-collapsed; empty ⇒ `NAME_ABSENT`. If not `ax_exposed` ⇒ `NAME_ABSENT` (04 §7: the name is an AX computation; an unexposed node has none). PROBE source: candidate `accessible_name` null/empty ⇒ `NAME_ABSENT` |

`PROBE` mapping: `visible` = Playwright-style CSS visibility (not viewport-clipped) so `visible_s0 = visible ∧ bbox∩V>0`; `hittable` is taken as measured; `ax_exposed` as reported.

## 4. Container-level fields (`unit=container`, one row per interrupt container)

| field | rule |
|---|---|
| `task_control_occlusion` | **primary (P-23, lane3-compatible)**: fraction of the 9×9 grid points on the path control P whose topmost element (`elementFromPoint`; PROBE = the probe's `hit_grid`, DOM_AX = static stacking: highest `(z-index, dom_order)` pointer-receiving container containing the point, `pointer-events:none` containers fall through) lies in this container, 3 dp. `NULL` when P is undefined or outside V (04 §4 'actual overlap'; 03 §9). `0.0` = observed and unoccluded (GAP-04) |
| `occlusion_geom_crosscheck` (aux) | the v1.1 geometry: area(T ∩ container rect ∩ V) / area(T ∩ V), 3 dp, on the frozen entry control T. Cross-check only — it is blind to `pointer-events:none` and to a P ≠ T |
| `dismiss_required_for_task` | **primary (P-24, lane3-compatible)**: the **blocking proof** — a click at the centre of P while this container is present (higher-stacked containers already dismissed) leaves the state unchanged. PROBE = the executed proof (`blocking_proof`); DOM_AX = static prediction (centre of P inside the container rect ∧ container receives pointer events ∧ stacked above P). `NULL` when P is undefined. 03 §9: geometry alone does not decide modal meaning — and neither does `aria-modal`: presence ≠ operative (A STEP1-011) |
| `dismiss_required_signal` (aux) | `+`-joined sorted set of the signals that are **recorded, never the verdict**: `ARIA_MODAL` (container has `aria-modal="true"`), `OCCLUSION_GT0` (hit-test primary > 0), `GEOM_OVERLAP_GT0` (geometric cross-check > 0); `NONE` if empty |
| `dismiss_control_exists` | ≥ 1 candidate (any visibility) |
| `dismiss_control_visible` | ≥ 1 candidate with `visible_s0`; `NULL` if `exists = False` |
| `dismiss_control_accessible_name` | name of the **selected** candidate; `NULL` if `exists = False` |
| `dismiss_control_hittable_s0` (aux) | selected candidate's `hittable_s0`; `NULL` if `exists = False` |
| `selected_selector` (aux) | canonical selector of the selected candidate (`#id`; fixtures guarantee ids) |

**Null convention** (A T-A-V3-STEP1-012 GAP-04): `NULL` = not observed (no path control, P outside V, empty population for `exists`/`visible`/`name`); `0.0` = observed and unoccluded; a row never mixes the two.

**Selection rule** (deterministic): order candidates by (`visible_s0` desc, `ax_exposed` desc, `hittable_s0` desc, `dom_order` asc); take the first.
**Dismissal order** of containers: `z-index` desc (missing = 0), then `dom_order` asc.

## 5. `unit=target` (one row per observation), population P ∈ {all, blocking}

| field | aggregate over containers in P |
|---|---|
| `dismiss_control_exists` | ALL(exists) ; **`NULL` if P is empty** (no denominator — empty is not 0) |
| `dismiss_control_visible` | `NULL` if P empty; `False` if any container in P has `exists=False` or `visible=False`; else `True` |
| `dismiss_control_accessible_name` | JSON list of per-container names in dismissal order (`NULL` entries for `exists=False`); `NULL` if P empty |
| `dismiss_required_for_task` | ANY(required); **`False` (not NULL) if P empty** — equals `forced_dismissal_count > 0` for P=all |
| `dismiss_required_signal` (aux) | union over P; `NONE` if P empty |
| `task_control_occlusion` (aux) | fraction of grid points on P whose topmost element lies in ANY container of P (= lane3's per-state number for P=all; each point hits at most one container, so this is the sum of the container rows); `0.0` if P empty (observed, unoccluded); `NULL` if no path control |
| `occlusion_geom_crosscheck` (aux) | MAX over P of the geometric cross-check; `0.0` if P empty |
| `dismiss_control_hittable_s0` (aux) | same rule as `visible` (NULL / False if any container lacks a control or has a non-hittable selected control / True) |
| `selected_selector` (aux) | JSON list of per-container selected selectors in dismissal order; `NULL` if P empty |

## 6. `unit=step` (one row per prospective `DISMISS_OBSTRUCTION` step)

Rows = containers with `dismiss_required_for_task = True`, in dismissal order, `step_index = 0..k-1`; fields copied from the
container row. **The population axis is degenerate at step unit**: 04 §2 defines `DISMISS_OBSTRUCTION` only for
obstructions "task path 진행에 필수인", so `all` and `blocking` yield identical step rows. No blocking container ⇒ zero
rows (reported as `n=0`, never as a row with `exists=False`).

## 7. Reporting rule

A `dismiss_control_exists` rate is written as `rate@unit/population/source`, e.g. `0.80@container/blocking/PROBE`.
Rates across different axes are never pooled. `NULL` rows are excluded from the numerator **and** denominator and their
count is reported alongside.

## 8. Ambiguities found by the convergence run and how the DEFINITION was fixed

(filled in after `converge_check.py`; see README §"Ambiguities resolved")

| # | Ambiguity surfaced | Where | Resolution (definition text, not numbers) |
|---|---|---|---|
| A1 | "visible" for a control that exists but sits below the fold of a scrollable overlay (f03): CSS-rendered says True, a human says False | pre-run, while authoring f03 | §3: `visible_s0 := rendered ∧ bbox∩V>0`. PROBE `visible` (Playwright `isVisible`, not viewport-clipped) is therefore **not** `dismiss_control_visible`; impl_A must AND it with the viewport. Recorded as the PROBE mapping line in §3 |
| A2 | Name of an unexposed control: DOM naming gives 닫기, AX tree has no node (f02 `display:none`, `aria-hidden` + 0×0) | pre-run, f02 | §3: identification uses DOM naming (so `exists=True`), but `accessible_name` is AX-computed ⇒ `NAME_ABSENT` when not `ax_exposed`. The pair (`exists=T`, `name=NAME_ABSENT`) is a legitimate, informative state |
| A3 | Behaviour-based dismiss (확인 button that happens to remove the layer, f02) | pre-run, f02 | §2 exclusion list; behaviour needs activation (L0-c) ⇒ `dismiss_succeeded`, never `exists` |
| A4 | `hittable` from a raw probe: Chromium `elementFromPoint` returns a 0×0 button at its origin (f02 ghost), so a probe reporting elementFromPoint alone says hittable=True for a non-visible control | Playwright validation run 1 (`out/playwright_validation.txt` mismatch #1) | §3: `hittable_s0 := visible_s0 ∧ …` — the conjunction is part of the definition; a PROBE `hittable` must be Playwright-actionability-ordered (visible first). impl_A applies the AND defensively (`hittable ∧ visible_s0`) |
| A5 | Population axis at `unit=step` | pre-run, while writing §6 | declared degenerate (`all` ≡ `blocking`), because `DISMISS_OBSTRUCTION` exists only for required obstructions (04 §2) |
| A6 | Empty population at `unit=target` (f05): 0 vs NULL | pre-run, §5 | `exists/visible/name = NULL`, `required = False`, `occlusion = 0.0`; NULL rows leave numerator and denominator; the negative control (`--negative-control`, phantom container) shows the check distinguishes NULL from False |
| A7 | Container geometry with CSS borders (f04 `border:1px`) — content-box adds 2px, shifts children by 1px; C's inline-CSS resolver ignores borders | Playwright validation run 1 (mismatches #2, #3) | not a definition issue: fixture hygiene (border → outline). Limitation of impl_B's layout subset is documented in README; on real DOMs geometry comes from the probe/AX, never from impl_B's resolver |

| A8 | Which control and which method for `task_control_occlusion` (v1.1 geometry on the frozen entry control T vs lane3 hit-test on the current-state path control P): lane3 fixture `seq_with_forced_dismissal` at S0 has T inside the closed drawer (area(T∩V)=0 → v1.1 undefined) while the hamburger is fully covered (lane3 → 1.0); a `pointer-events:none` overlay gives v1.1 > 0 and lane3 0 | GATE1_PREREGISTRATION_C P-23 (pre-run for f06) | §2 adds P; §4 makes the hit-test on P the primary and demotes geometry to `occlusion_geom_crosscheck`. Decided by C result-blind in `C-DECISION_REQUEST-031138` (measurement-method choice, C's authority; A confirmed STEP1-011). f06 `#glass` shows the split: hit 0.000 / geom 1.000 |
| A9 | `dismiss_required_for_task` from `occlusion > 0 ∨ aria-modal` (v1.1) vs a blocking proof (lane3): an `aria-modal` dialog that neither overlaps nor intercepts P, or a backdrop that overlaps but has `pointer-events:none`, is "required" under v1.1 and not under the proof | GATE1_PREREGISTRATION_C P-24 (pre-run for f06) | §4 makes the blocking proof the primary and moves `aria-modal` / overlap into `dismiss_required_signal`. f06 `#tip-dialog` (signal `ARIA_MODAL`, required F) and `#glass` (signal `GEOM_OVERLAP_GT0`, required F) are the two divergent cases; the negative-control mutation "report `aria-modal` as the proof" is caught as DIFF |

Convergence verdict was PASS on the first run (27/27 rows) and again after v1.2 (31/31 rows incl. f06); A4 and A7 were found by the *third* (browser) check, not by the two-impl convergence — a reminder that two independent implementations sharing one author's assumptions converge on those assumptions too. v1.2's `hit_grid` and `blocking_proof` probe inputs are therefore also browser-validated (`validate_probe_like_playwright.py`: real `elementFromPoint` grid and a real click at the centre of P per container in dismissal order).
