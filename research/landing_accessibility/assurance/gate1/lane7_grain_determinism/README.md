# GATE 1 · lane7_grain_determinism — dismiss_control_exists 3-axis definition + route-policy determinism (C)

**Owner** Claude C. **Base** worktree `claude_c_assurance_v21` @ `3fc00a5` (= `5e05da9` + one bus ACK; lane tree identical); **v1.2** on `claude-c/assurance-v21` after `67f473b` — P-23/P-24 reconciliation with lane3 applied (`C-DECISION_REQUEST-031138`, A confirmed `T-A-V3-STEP1-011`), fixture f06 added for the divergent cases.
**Independence** authored by C from SSOTV3 02 §5 / 03 §3,§4,§5,§9 / 04 §2,§4,§7 / 05 §2 + `REFERENCE_DEFINITIONS.md`; no B/D worktree, no B code, no
network. `probe_like/*.json` were hand-authored from the fixture HTML, then validated in a real browser (Playwright, `file://` only, other requests aborted).

## (A) dismiss_control_exists — definition and two-implementation convergence

Definition `DISMISS_DEFINITION_C.md` (pre-registered; §8 logs each ambiguity and the *text* change that resolved it; **v1.2**: `task_control_occlusion` primary =
9×9 `elementFromPoint` hit-test on the CURRENT-STATE path control `[data-c-path-control]` / probe `path_control.hit_grid` (lane3 method), geometry on the frozen entry
control demoted to `occlusion_geom_crosscheck`; `dismiss_required_for_task` primary = blocking proof (probe `blocking_proof`: click at the path-control centre leaves the
state unchanged; DOM_AX: static stacking prediction), `aria-modal` / overlap recorded as `dismiss_required_signal`, never the verdict). Axes always named:
**unit** target|container|step · **population** all|blocking · **source** PROBE|DOM_AX. `impl_a.py` (PROBE: `raw_features.dismiss_control_candidates`)
and `impl_b.py` (DOM_AX: lxml/XPath + inline-CSS layout resolver + ARIA) share **no code**; `converge_check.py` PASSes only if every canonical row is identical.

Fixtures (390×844, inline CSS geometry, ids on every container/control): **f01** `aria-modal` dialog + backdrop + visible 닫기 →
exists T/visible T/required T (occl 1.000); **f02** overlay covers the control, 닫기 is `display:none`, 2nd 닫기 `aria-hidden`+0×0, 확인 excluded →
exists T/visible F/`NAME_ABSENT`; **f03** full-screen layer, 닫기 at y=1300 in a scrollable panel → visible F (below fold); **f04** non-blocking
cookie banner + centre dialog covering 28/48 px → pop=all 2 rows, pop=blocking 1 row, hit-test occl 0.556 (45/81 grid points) vs geometric 0.583 — the two methods differ on the same
fixture, which is why only one may be primary; **f05** no overlay → target NULL/NULL/NULL, required F, occl 0.0 (observed, unoccluded), 0 rows; **f06** (v1.2, P-24 cases)
`role=dialog aria-modal=true` panel that does not touch the control + full-viewport `pointer-events:none` glass with no dismiss control → both required F, signals
`ARIA_MODAL` / `GEOM_OVERLAP_GT0`, hit 0.000 / geom 1.000, target pop=all exists F (the previously untested `exists=F` boundary), pop=blocking NULL, 0 step rows.

### converge_check.py output (`out/converge_check.stdout.txt`, v1.2 run)
```
fixture | unit | pop | row | exists | visible | acc_name | required | signal | occl_hit | occl_geom | hittable | selected | A==B
f01 | target | all | TARGET | T | T | ["닫기"] | T | ARIA_MODAL+GEOM_OVERLAP_GT0+OCCLUSION_GT0 | 1.000 | 1.000 | T | ["#promo-close"] | ok
f01 | target | blocking | TARGET | T | T | ["닫기"] | T | ARIA_MODAL+GEOM_OVERLAP_GT0+OCCLUSION_GT0 | 1.000 | 1.000 | T | ["#promo-close"] | ok
f01 | container | all | #promo-modal | T | T | 닫기 | T | ARIA_MODAL+GEOM_OVERLAP_GT0+OCCLUSION_GT0 | 1.000 | 1.000 | T | #promo-close | ok
f01 | container | blocking | #promo-modal | T | T | 닫기 | T | ARIA_MODAL+GEOM_OVERLAP_GT0+OCCLUSION_GT0 | 1.000 | 1.000 | T | #promo-close | ok
f01 | step | all | step0:#promo-modal | T | T | 닫기 | T | ARIA_MODAL+GEOM_OVERLAP_GT0+OCCLUSION_GT0 | 1.000 | 1.000 | T | #promo-close | ok
f01 | step | blocking | step0:#promo-modal | T | T | 닫기 | T | ARIA_MODAL+GEOM_OVERLAP_GT0+OCCLUSION_GT0 | 1.000 | 1.000 | T | #promo-close | ok
f02 | target | all | TARGET | T | F | ["NAME_ABSENT"] | T | GEOM_OVERLAP_GT0+OCCLUSION_GT0 | 1.000 | 1.000 | F | ["#ad-close-ghost"] | ok
f02 | target | blocking | TARGET | T | F | ["NAME_ABSENT"] | T | GEOM_OVERLAP_GT0+OCCLUSION_GT0 | 1.000 | 1.000 | F | ["#ad-close-ghost"] | ok
f02 | container | all | #ad-layer | T | F | NAME_ABSENT | T | GEOM_OVERLAP_GT0+OCCLUSION_GT0 | 1.000 | 1.000 | F | #ad-close-ghost | ok
f02 | container | blocking | #ad-layer | T | F | NAME_ABSENT | T | GEOM_OVERLAP_GT0+OCCLUSION_GT0 | 1.000 | 1.000 | F | #ad-close-ghost | ok
f02 | step | all | step0:#ad-layer | T | F | NAME_ABSENT | T | GEOM_OVERLAP_GT0+OCCLUSION_GT0 | 1.000 | 1.000 | F | #ad-close-ghost | ok
f02 | step | blocking | step0:#ad-layer | T | F | NAME_ABSENT | T | GEOM_OVERLAP_GT0+OCCLUSION_GT0 | 1.000 | 1.000 | F | #ad-close-ghost | ok
f03 | target | all | TARGET | T | F | ["닫기"] | T | GEOM_OVERLAP_GT0+OCCLUSION_GT0 | 1.000 | 1.000 | F | ["#event-close"] | ok
f03 | target | blocking | TARGET | T | F | ["닫기"] | T | GEOM_OVERLAP_GT0+OCCLUSION_GT0 | 1.000 | 1.000 | F | ["#event-close"] | ok
f03 | container | all | #event-layer | T | F | 닫기 | T | GEOM_OVERLAP_GT0+OCCLUSION_GT0 | 1.000 | 1.000 | F | #event-close | ok
f03 | container | blocking | #event-layer | T | F | 닫기 | T | GEOM_OVERLAP_GT0+OCCLUSION_GT0 | 1.000 | 1.000 | F | #event-close | ok
f03 | step | all | step0:#event-layer | T | F | 닫기 | T | GEOM_OVERLAP_GT0+OCCLUSION_GT0 | 1.000 | 1.000 | F | #event-close | ok
f03 | step | blocking | step0:#event-layer | T | F | 닫기 | T | GEOM_OVERLAP_GT0+OCCLUSION_GT0 | 1.000 | 1.000 | F | #event-close | ok
f04 | target | all | TARGET | T | T | ["닫기", "닫기"] | T | GEOM_OVERLAP_GT0+OCCLUSION_GT0 | 0.556 | 0.583 | T | ["#notice-close", "#cookie-close"] | ok
f04 | target | blocking | TARGET | T | T | ["닫기"] | T | GEOM_OVERLAP_GT0+OCCLUSION_GT0 | 0.556 | 0.583 | T | ["#notice-close"] | ok
f04 | container | all | #cookie-banner | T | T | 닫기 | F | NONE | 0.000 | 0.000 | T | #cookie-close | ok
f04 | container | all | #notice-layer | T | T | 닫기 | T | GEOM_OVERLAP_GT0+OCCLUSION_GT0 | 0.556 | 0.583 | T | #notice-close | ok
f04 | container | blocking | #notice-layer | T | T | 닫기 | T | GEOM_OVERLAP_GT0+OCCLUSION_GT0 | 0.556 | 0.583 | T | #notice-close | ok
f04 | step | all | step0:#notice-layer | T | T | 닫기 | T | GEOM_OVERLAP_GT0+OCCLUSION_GT0 | 0.556 | 0.583 | T | #notice-close | ok
f04 | step | blocking | step0:#notice-layer | T | T | 닫기 | T | GEOM_OVERLAP_GT0+OCCLUSION_GT0 | 0.556 | 0.583 | T | #notice-close | ok
f05 | target | all | TARGET | NULL | NULL | NULL | F | NONE | 0.000 | 0.000 | NULL | NULL | ok
f05 | target | blocking | TARGET | NULL | NULL | NULL | F | NONE | 0.000 | 0.000 | NULL | NULL | ok
f06 | target | all | TARGET | F | F | ["닫기", null] | F | ARIA_MODAL+GEOM_OVERLAP_GT0 | 0.000 | 1.000 | F | ["#tip-close", null] | ok
f06 | target | blocking | TARGET | NULL | NULL | NULL | F | NONE | 0.000 | 0.000 | NULL | NULL | ok
f06 | container | all | #glass | F | NULL | NULL | F | GEOM_OVERLAP_GT0 | 0.000 | 1.000 | NULL | NULL | ok
f06 | container | all | #tip-dialog | T | T | 닫기 | F | ARIA_MODAL | 0.000 | 0.000 | T | #tip-close | ok

mode=CONVERGE rows compared=31 identical=31 differing=0 per-unit={'target': 12, 'container': 11, 'step': 8} -> PASS
```
Negative control `converge_check.py --negative-control` (6 in-memory PROBE mutations: f01 visible→F, f04 z-order flip, f05 phantom container,
f02 `blocking_proof`→F (probe claims the click got through), f03 one hit-grid row → control, f06 `blocking_proof`→T on the aria-modal dialog (a probe that reports the
attribute as the proof — the v1.1 rule)): `mode=NEGATIVE-CONTROL rows compared=35 identical=8 differing=27 per-unit={'target': 12, 'container': 13, 'step': 10} -> NEGCTRL_OK(check detects disagreement)` — every mutated fixture shows ≥1 DIFF row.
Browser validation `validate_probe_like_playwright.py` (`out/playwright_validation.txt`): `checked=39 mismatches=0 -> PROBE_LIKE_VALIDATED` (bbox/visible/hittable/ax/name entries + the 6 hit grids
against real `elementFromPoint` + 8 blocking proofs by a real click at the path-control centre, containers removed in dismissal order between proofs).

### Ambiguities resolved (DISMISS_DEFINITION_C.md §8, A1-A7)
A1 `visible` ≠ Playwright `isVisible` — defined as rendered ∧ inside S0 viewport (f03 → F). A2 unexposed control → `exists=T`, name `NAME_ABSENT`.
A3 behaviour-based dismiss (확인) is `dismiss_succeeded` (L0-c), never `exists`. A5 population axis degenerate at unit=step. A6 empty population → NULL, not 0.
A4/A7 found only by the browser check: Chromium `elementFromPoint` hits a 0×0 button (probe `hittable` must be visible-first — definition already
requires `hittable ⊂ visible`); CSS `border` shifts geometry (impl_B's inline-CSS resolver covers only the fixture subset; real geometry comes from probe/AX).
A8/A9 (v1.2): occlusion method + measured control, and blocking proof vs `aria-modal`/overlap — reconciled with lane3 result-blind (`C-DECISION_REQUEST-031138` P-23/P-24), f06 exercises both divergent cases.

## (B) route-policy determinism

Spec + 12-item policy-document checklist: `ROUTE_POLICY_DETERMINISM_SPEC.md` (sha256 `1711a55d…0e3e`, printed by the check).
`determinism_check.py --cmd "<runner> {fixture} {out}" --fixture F --n 3` runs the runner 3× on the same fixture and PASSes only
if `task_flow_sequence`, `experienced_flow_sequence` and the ordered `control_selector` list are byte-identical (canonical JSON);
raw-file identity is informational (timestamps may differ). Exit 2 (runner wrote nothing) is neither PASS nor FAIL.

### Positive control — `fake_runner_det.py` on f04 (`out/determinism_det.stdout.txt`)
```
run | task_flow sha8 | experienced_flow sha8 | selectors sha8 | raw file sha8 | experienced_flow
0 | b7be9696 | 22627a5e | 0c4199aa | 72e8d905 | DISMISS_OBSTRUCTION > DISMISS_OBSTRUCTION > SELECT_FUNCTION > ENDPOINT_REACHED
1 | b7be9696 | 22627a5e | 0c4199aa | 5e09eb59 | DISMISS_OBSTRUCTION > DISMISS_OBSTRUCTION > SELECT_FUNCTION > ENDPOINT_REACHED
2 | b7be9696 | 22627a5e | 0c4199aa | 89b6f12d | DISMISS_OBSTRUCTION > DISMISS_OBSTRUCTION > SELECT_FUNCTION > ENDPOINT_REACHED
label=det_f04 n=3 distinct-per-field={'task_flow_sequence': 1, 'experienced_flow_sequence': 1, 'selected_control_selectors': 1} raw-file-distinct=3 (informational) -> PASS
policy_doc=ROUTE_POLICY_DETERMINISM_SPEC.md sha256=1711a55d8a97d7d09ac6182c759847d61dc18df2b1e567799bede7a154cd0e3e
```
### Negative control — `fake_runner_rand.py` on f04 (`out/determinism_rand.stdout.txt`)
```
run | task_flow sha8 | experienced_flow sha8 | selectors sha8 | raw file sha8 | experienced_flow
0 | db5f9e06 | 2ca9f58d | 86281fdd | e1bd9d07 | DISMISS_OBSTRUCTION > DISMISS_OBSTRUCTION > OPEN_GLOBAL_MENU > SELECT_FUNCTION > ENDPOINT_REACHED
1 | db5f9e06 | 2ca9f58d | 75a8daec | b75a7bd2 | DISMISS_OBSTRUCTION > DISMISS_OBSTRUCTION > OPEN_GLOBAL_MENU > SELECT_FUNCTION > ENDPOINT_REACHED
2 | b7be9696 | 22627a5e | e40f7550 | b938d810 | DISMISS_OBSTRUCTION > DISMISS_OBSTRUCTION > SELECT_FUNCTION > ENDPOINT_REACHED
label=rand_f04 n=3 distinct-per-field={'task_flow_sequence': 2, 'experienced_flow_sequence': 2, 'selected_control_selectors': 3} raw-file-distinct=3 (informational) -> FAIL
```
Runs 0/1 of the random runner share token sequences and differ only in selector form: the selector-level assertion is what makes
the check sensitive to unstated tie-breaks (RP-03). The negative control is probabilistic (P[3 identical] < 1/1000 on f04).
## Files
`DISMISS_DEFINITION_C.md` · `fixtures/` · `probe_like/` · `impl_a.py` · `impl_b.py` · `converge_check.py` · `validate_probe_like_playwright.py` (optional 3rd check)
· `ROUTE_POLICY_DETERMINISM_SPEC.md` · `determinism_check.py` · `fake_runner_det.py` · `fake_runner_rand.py` · `out/` (all run outputs, `*_result.json`, `det_*/seq_*.json`).
v1.1 untested boundary (population=all row with `exists=F`) is now covered by f06 `#glass`. Still untested: a path control P ≠ T (menu-hidden entry; lane3 covers it with `seq_with_forced_dismissal`), and a probe emission with `path_control` absent (impl_a/impl_b then report `task_control_occlusion=NULL`, `dismiss_required_for_task=NULL`, geometry only in `occlusion_geom_crosscheck` — exercised ad hoc, not by a fixture).
