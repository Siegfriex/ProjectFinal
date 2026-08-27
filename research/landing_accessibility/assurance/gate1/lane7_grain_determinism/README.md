# GATE 1 · lane7_grain_determinism — dismiss_control_exists 3-axis definition + route-policy determinism (C)

**Owner** Claude C. **Base** worktree `claude_c_assurance_v21` @ `3fc00a5` (= `5e05da9` + one bus ACK; lane tree identical).
**Independence** authored by C from SSOTV3 02 §5 / 03 §3,§4,§5,§9 / 04 §2,§4,§7 / 05 §2 + `REFERENCE_DEFINITIONS.md`; no B/D worktree, no B code, no
network. `probe_like/*.json` were hand-authored from the fixture HTML, then validated in a real browser (Playwright, `file://` only, other requests aborted).

## (A) dismiss_control_exists — definition and two-implementation convergence

Definition `DISMISS_DEFINITION_C.md` (pre-registered; §8 logs each ambiguity and the *text* change that resolved it). Axes always named:
**unit** target|container|step · **population** all|blocking · **source** PROBE|DOM_AX. `impl_a.py` (PROBE: `raw_features.dismiss_control_candidates`)
and `impl_b.py` (DOM_AX: lxml/XPath + inline-CSS layout resolver + ARIA) share **no code**; `converge_check.py` PASSes only if every canonical row is identical.

Fixtures (390×844, inline CSS geometry, ids on every container/control): **f01** `aria-modal` dialog + backdrop + visible 닫기 →
exists T/visible T/required T (occl 1.000); **f02** overlay covers the control, 닫기 is `display:none`, 2nd 닫기 `aria-hidden`+0×0, 확인 excluded →
exists T/visible F/`NAME_ABSENT`; **f03** full-screen layer, 닫기 at y=1300 in a scrollable panel → visible F (below fold); **f04** non-blocking
cookie banner + centre dialog covering 28/48 px → pop=all 2 rows, pop=blocking 1 row, occl 0.583; **f05** no overlay → target NULL/NULL/NULL, required F, 0 rows.

### converge_check.py output (`out/converge_check.stdout.txt`)
```
fixture | unit | pop | row | exists | visible | acc_name | required | occl | hittable | selected | A==B
f01 | target | all | TARGET | T | T | ["닫기"] | T | 1.000 | T | ["#promo-close"] | ok
f01 | target | blocking | TARGET | T | T | ["닫기"] | T | 1.000 | T | ["#promo-close"] | ok
f01 | container | all | #promo-modal | T | T | 닫기 | T | 1.000 | T | #promo-close | ok
f01 | container | blocking | #promo-modal | T | T | 닫기 | T | 1.000 | T | #promo-close | ok
f01 | step | all | step0:#promo-modal | T | T | 닫기 | T | 1.000 | T | #promo-close | ok
f01 | step | blocking | step0:#promo-modal | T | T | 닫기 | T | 1.000 | T | #promo-close | ok
f02 | target | all | TARGET | T | F | ["NAME_ABSENT"] | T | 1.000 | F | ["#ad-close-ghost"] | ok
f02 | target | blocking | TARGET | T | F | ["NAME_ABSENT"] | T | 1.000 | F | ["#ad-close-ghost"] | ok
f02 | container | all | #ad-layer | T | F | NAME_ABSENT | T | 1.000 | F | #ad-close-ghost | ok
f02 | container | blocking | #ad-layer | T | F | NAME_ABSENT | T | 1.000 | F | #ad-close-ghost | ok
f02 | step | all | step0:#ad-layer | T | F | NAME_ABSENT | T | 1.000 | F | #ad-close-ghost | ok
f02 | step | blocking | step0:#ad-layer | T | F | NAME_ABSENT | T | 1.000 | F | #ad-close-ghost | ok
f03 | target | all | TARGET | T | F | ["닫기"] | T | 1.000 | F | ["#event-close"] | ok
f03 | target | blocking | TARGET | T | F | ["닫기"] | T | 1.000 | F | ["#event-close"] | ok
f03 | container | all | #event-layer | T | F | 닫기 | T | 1.000 | F | #event-close | ok
f03 | container | blocking | #event-layer | T | F | 닫기 | T | 1.000 | F | #event-close | ok
f03 | step | all | step0:#event-layer | T | F | 닫기 | T | 1.000 | F | #event-close | ok
f03 | step | blocking | step0:#event-layer | T | F | 닫기 | T | 1.000 | F | #event-close | ok
f04 | target | all | TARGET | T | T | ["닫기", "닫기"] | T | 0.583 | T | ["#notice-close", "#cookie-close"] | ok
f04 | target | blocking | TARGET | T | T | ["닫기"] | T | 0.583 | T | ["#notice-close"] | ok
f04 | container | all | #cookie-banner | T | T | 닫기 | F | 0.000 | T | #cookie-close | ok
f04 | container | all | #notice-layer | T | T | 닫기 | T | 0.583 | T | #notice-close | ok
f04 | container | blocking | #notice-layer | T | T | 닫기 | T | 0.583 | T | #notice-close | ok
f04 | step | all | step0:#notice-layer | T | T | 닫기 | T | 0.583 | T | #notice-close | ok
f04 | step | blocking | step0:#notice-layer | T | T | 닫기 | T | 0.583 | T | #notice-close | ok
f05 | target | all | TARGET | NULL | NULL | NULL | F | 0.000 | NULL | NULL | ok
f05 | target | blocking | TARGET | NULL | NULL | NULL | F | 0.000 | NULL | NULL | ok
mode=CONVERGE rows compared=27 identical=27 differing=0 per-unit={'target': 10, 'container': 9, 'step': 8} -> PASS
```
Negative control `converge_check.py --negative-control` (3 in-memory PROBE mutations: f01 visible→F, f04 z-order flip,
f05 phantom container): `mode=NEGATIVE-CONTROL rows compared=28 identical=19 differing=9 per-unit={'target': 10, 'container': 10, 'step': 8} -> NEGCTRL_OK(check detects disagreement)` — 9 DIFF rows.
Browser validation `validate_probe_like_playwright.py` (`out/playwright_validation.txt`): `checked=16 mismatches=0 -> PROBE_LIKE_VALIDATED` (16 bbox/visible/hittable/ax/name entries).

### Ambiguities resolved (DISMISS_DEFINITION_C.md §8, A1-A7)
A1 `visible` ≠ Playwright `isVisible` — defined as rendered ∧ inside S0 viewport (f03 → F). A2 unexposed control → `exists=T`, name `NAME_ABSENT`.
A3 behaviour-based dismiss (확인) is `dismiss_succeeded` (L0-c), never `exists`. A5 population axis degenerate at unit=step. A6 empty population → NULL, not 0.
A4/A7 found only by the browser check: Chromium `elementFromPoint` hits a 0×0 button (probe `hittable` must be visible-first — definition already
requires `hittable ⊂ visible`); CSS `border` shifts geometry (impl_B's inline-CSS resolver covers only the fixture subset; real geometry comes from probe/AX).

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
Untested boundary (documented, not claimed): a fixed/sticky header that is not an ancestor of the task control (population=all row with `exists=F`).
