# Current State Baseline — 2026-08-27 20:20 KST

## Exact remote heads

- `research/landing-accessibility-main` → `bc0b7a087faf2328cbafdfa9b40bd426c5080d7d`
- `control/landing-orchestrator` → `084eff541836c2e16418b96bd230c1d58bcda663`
- `claude-b/analysis-current` → `82f631f1e6bd3708bc8f95f0b8edcd90e22cef0d`
- `claude-b/measurement-recovery` → `2281c853950d0c475c5d2c1678680b971c2804f4`
- `claude-c/assurance-current` → `1baa865b4a673af05033e6e6289fd2713676baa5`

## Handoff heads

- A → `handoff/landing-a-20260827 @ 7c8facebe95ec3793756a82d809be37ca17b6b6e`
- B → `handoff/landing-b-20260827 @ 66aa655400f872197e64390522225823e93b5628`
- C → `handoff/landing-c-20260827 @ 3d84741656ce08991ceb06572b2b242470f1f9e3`

## Frozen pilot status

- E001 attempted: 59/59
- grade: PILOT / PRELIMINARY
- Axis A: NOT_EVALUATED
- Axis B: MPFED available 0/59
- Axis C: raw measured / classification incomplete
- planned association: NOT_COMPUTABLE
- substitute analysis: none
- REAL_TARGET next run: NO-GO until recovery validation

## Confirmed recovery facts

- target-level guard block: 25/59
- LOGIN share among guard blocks: 19
- QUERY five targets failed to reach useful Scout path under prior guard/retry behavior
- representative task definition existed upstream for 59/59
- execution wiring dropped required task fields
- actual detector depended on fixture-style markers instead of live DOM semantics
- KWCAG production evaluator absent

## Control decision already present

Control state established that detector producer B and assurance reviewer C must not create their own gold labels. Independent label worker + pre-detector label hash freeze is required.

## Important caution

GitHub does not contain all raw evidence bytes because some artifacts were local/ignored. New sessions must create or verify a Git-tracked retention manifest that hashes the local artifact set.
