# R54_MATCHER_SWEEP_C — C's extractors: rule next to count, presence probe beside it

**Plane** C. **Ruling** `V3_0_1_SUCCESSOR_DELTA.md` Δ54 / R54 (D-V3-FINDING-025): an extractor must distinguish *absent* from *could not
extract*; a narrow matcher yields a silent 0, a wide one a silent over-count; detection = compare the empty-extraction ratio with source
presence, denominators stated, parser rule stated next to every count.
**Tool** `gate1/r54_matcher_sweep_c.py` → `gate1/R54_MATCHER_SWEEP_C.json` (tool-generated: `measured_at_kst`, control commit / delta / index shas,
bus counts, sha256 of every inspected tool, one record per matcher, `fixed[]`). Controls are evaluated against the **imported live tool code**,
so a regression in any pattern flips the sweep to exit 1. Re-run after any edit to the listed tools.

```bash
python3 research/landing_accessibility/assurance/gate1/r54_matcher_sweep_c.py          # exit 0 = all controls pass
python3 research/landing_accessibility/assurance/gate1/control_failure_demo_c.py       # re-bind the R40 sidecar after editing c_bus_scan.py / r32_inventory.py
```

## Per-matcher record (what each JSON entry carries)

`id` · `tool` · `where` · `feeds` (which judgment the value enters) · `pattern` (exact regex / rule) · `rule` (prose parser rule, the same string the tool
emits next to its count) · `direction_if_narrow` / `direction_if_wide` · `denominator` {name, n} · `extracted` · `presence_probe` (a deliberately wider
probe, report-only) · `must_not_miss[]` (wide-form positives: numbered headings, trailing text, backticks/parentheses, `Δ36-②`, hyphen chains,
`Z` timestamps …) · `must_not_over[]` (negatives a wider matcher would catch: `Δ47-fixture` inside `Δ47-fixture-limit`, `R21` inside `R210`,
`write_checkpoint` as a *check*, `구매후기` as a purchase, prose `REAL scope 0` …) · `classification` (NARROW_MISS / WIDE_OVER / OK; `NOT_A_MATCHER` for
the hand-authored RIC) · `status_before_fix` · `impact_on_current_source` · `fix_applied` / `proposed_fix`.

## Result (2026-08-28, 32 matchers, 215 controls)

| before fix | now | fixed | accepted-and-recorded (outside edit scope / safety-wide) |
|---|---|---|---|
| NARROW_MISS 6 · WIDE_OVER 4 · OK-without-denominator 2 | OK 28 · WIDE_OVER 3 · NOT_A_MATCHER 1 | 12 (c_bus_scan.py 11, r32_inventory.py 1) | M28 waybill/tracking substring · M29 `Scout` launch-line · M30 transaction-text (kept wide: fail-closed safety) |

Fixes that changed a judgment count on the live bus (orig vs v22 scanner, same bus, same control commit `053f324d`):

| matcher | before | after | why |
|---|---|---|---|
| M14 `V3_CUTOFF_EPOCH` | v3_era_checked 163, base_sha NO_FIELD 5 | 159, NO_FIELD 1 | the typed epoch literal was 2026-08-24 00:52 KST (4d01h20m early): 4 timestamp-less pre-v3 tickets (FINAL_READY / MART_READY / STATS_READY / T-E001-RELEASE-001.DRAFT, mtimes 08-27 12:37–16:18) were judged v3-era. Derived from the ISO literal now. |
| M03 `HOW_KNOWN_RE` | missing 37 | 36 | `how_A_knows` (T-A-V3-FC-005) — old `how_.*(found|surfaced|happened).*` missed it; now any `how_*`; 5 of the remaining 36 carry a wide-probe key (listed, not counted) |
| M05 `DELTA_TOKEN_RE` | resolved_by_subrows 30 | 27 | `Δ50-exit2-common` / `Δ48-runner-id` / `Δ47-fixture-limit` were truncated at the first hyphen; `Δ47-fixture-limit` resolved to the *different* row `Δ47-fixture` |
| M04 ref-lint | hits 13→16 was bus growth | denominators added | 19 lines mention the branch: 4 prefixed, 13–16 bare, 2 bare-form lines hidden by the line-wide `ls-remote` exemption (now listed) |
| M10/M11 headings | 120 ids, no denominator; numbered subsections unseen | 279 heading lines / 129 ids; 19 strict numbered subsections in 8 `## Δn` sections; shortfall 0 | Δ54 check-10 counterpart — `Δ36` ①②③④ = 4 = index rows with prefix Δ36 (A's count agrees) |

Unchanged with reasons: `pending`, `dangling` (1, genuine: `acks/T-E001-RELEASE-001.B.json`, no ticket by prefix either), `unrecorded_mentions` 2 (`Δ8-ruling`,
A's contaminated control `Δ999-R99`), `index_rows_unmentioned_in_A_tickets` 26 (Δ47-fixture is cited on its own elsewhere, so removing its false credit did not change the list),
reachability unreachable 0 / parent-anchor-only 48.

## Ambiguities recorded (not resolved by this sweep)

- **Numbered subsections**: A counts `Δ36` as 4 (①–④); `### part4 — …` is a continuation heading. C's strict rule excludes `part<n>` / `<n>.` (wide rule counts them, reported beside). Δ53 has a `판정 ③` with no ①/② — numbering gaps are not a shortfall.
- **Hyphen boundary vs A's rule**: `token_in` now treats `-` as part of the token (as `_tok_delta` / `alias_fires_in_corpus` already did). A prose mention `Δ21-based` would therefore not credit `Δ21` — no such form exists on the bus (presence probe `of_those_with_zero_tokens_extracted` = []).
- **`\w` boundary and Hangul**: `_tok_delta` blocks a token glued to a Hangul particle (`Δ21을`); 0 such tokens in the current delta (probe counted). If A starts writing them, reachability over-alarms (fail-closed), not silently passes.
- **Q8 colon form**: `endpoint_status: AUTH_GATE` in free text is flagged as unqualified (the declared form is `key=VALUE`) — over-flag, raise, fail-closed. Proposed acceptance recorded on M24.
- **Comparators (M28–M30)** are outside this sweep's edit scope; WIDE_OVER latent by control, 0 hits on C fixtures, proposed word-start bounds recorded. M30 stays wide on purpose (safety).
- **Limitation reader (M31)**: the runbook's Limitation rule r2 had no code; `limitation_status()` in the sweep is the reference implementation (numbered / trailing-text / Korean headings, fenced blocks ignored, NOT_STATED / EMPTY / STATED with the rule string). No B artifact has been read with it yet.
- **RIC (M32)** is hand-authored; its index sha is behind the live index (v49 at sweep time). Regenerate from the scanner's identity block at the next revision.
- **Source drift during the sweep**: the control tip moved three times while measuring (index v46 → v48 → v49; bus 298 → 303 tickets). Every count in the JSON carries the sha it was measured against; counts from different shas are not compared item-by-item (R38).
