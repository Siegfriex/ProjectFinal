# Lane X-Converge — `nav_container_depth` · `menu_dependency`

**Verdict: `DIFFERENT_QUANTITIES`**  (menu_dependency: `CONVERGED` · nav_container_depth: `DIFFERENT_QUANTITIES`)

Assignment `T-A-V3-STEP1-007`. Base `ce97273129b404774736ec566603b9e2b969ecdf`. REAL access 0; synthetic fixtures only.

The duplication came from the D orchestrator's split contract (D-DEF-11), not from either worker. Neither implementation is discarded; the two independent readings are used as the material for the check.

## 1. Three-axis declaration (before any comparison)

### `menu_dependency` — axes match: **True**

| axis | Lane S | Lane F |
|---|---|---|
| 단위 (grain) | run — one boolean per observation (one token sequence). | run — one result per observation. |
| 모집단 | tokens strictly before the endpoint cut. Cut = index of the first ENDPOINT_REACHED; if absent, the whole sequence. Basis reported per row as `endpoint_cut_basis`. | tokens strictly before the first ENDPOINT_REACHED; if absent, the whole sequence. `endpoint_token_present` reported (AMB-F09). |
| 원천 필드 | ONE sequence, named by the caller. `sequence_field` is a REQUIRED argument and must be 'task_flow_sequence' or 'experienced_flow_sequence'; the harness raises rather than pick one. | BOTH sequences. Primary readings come from task_flow_sequence; the experienced-base readings are computed too and their equality is asserted as `base_invariant`. |
| emits | a single bool, always. | a single bool ONLY when the two readings agree; otherwise value=None with ambiguity_active=True. |

GRAIN identical. POPULATION identical (same endpoint-cut rule, same fallback). SOURCE FIELD reconcilable: S's `sequence_field='task_flow_sequence'` is exactly F's primary base. The lanes therefore ARE comparable — but only reading-to-reading: S's default output must be compared with F's `readings.reveal_set_explicit3`, NOT with F's emitted `value`, because the two differ in EMISSION POLICY (S closes the open set by default; F withholds a value while it is open).

### `nav_container_depth` — axes match: **False**

| axis | Lane S | Lane F |
|---|---|---|
| 단위 (grain) | run — one count per observation. | run — but no value is produced at any grain. |
| 모집단 | seq[:exposure_step_index]. NO endpoint cut is applied. Tokens after ENDPOINT_REACHED are counted if the supplied index reaches them. | prefix before the first ENDPOINT_REACHED, then further narrowed per candidate. The endpoint cut IS applied to all three candidates. |
| 원천 필드 | sequence + `exposure_step_index`, an EXTERNAL input that is not in the token stream. Never inferred; MISSING index -> value MISSING (AMB-S08). | task_flow_sequence only. F holds that the exposure step has no marker token in the canonical 18 and refuses to invent one (AMB-F06). |
| emits | an int when an exposure index is supplied, else None. `nesting_verified` is always False — the count is flat, so a sibling reveal is indistinguishable from a nested one. | value=None ALWAYS. Three illustrative candidates only: `reveal_tokens_before_first_SELECT_FUNCTION`, `leading_consecutive_reveal_run`, `all_reveal_tokens_before_endpoint`. |

TWO axes differ. (1) SOURCE FIELD: S consumes an external `exposure_step_index` that F does not accept; F's quantity is a function of the token sequence alone, S's is a function of (sequence, externally declared exposure point). (2) POPULATION: F applies the endpoint cut before counting, S does not. On top of that, F emits no scalar at all. A scalar-vs-scalar comparison is not defined. What CAN be compared is S's output under a stipulated exposure rule against F's candidate that encodes the same stipulation — that is a reading-to-reading check, and it is what this harness runs.

## 2. Fixture provenance

Neither lane's fixture is reused — using one would make that lane's reading the answer key. All 18 cases are derived from `04_FLOW_CODEBOOK_v3.0.md` §2/§3/§4/§5.

- **R1** — Tokens only from the 04 §2 canonical-18 table; no invented tokens.
- **R2** — FX01 is the 04 §3 worked example, both sequences, verbatim.
- **R3** — Reveal tokens are the three §5 names; SWITCH_TAB is exercised separately because §5's '등' leaves the set open. Not resolved here.
- **R4** — The endpoint boundary is probed on both sides, plus the two degenerate terminals (endpoint-first, no-endpoint/AUTH_GATE).
- **R5** — §5 says 'nested reveal', §4 says 'expansion 수' — nested and sibling arrangements are separated because the two phrasings disagree.
- **R6** — `exposure_step_index` is a fixture stipulation (AMB-X03), recorded per row with the F candidate it corresponds to. It is a test scaffold, not a ruling.
- **R7** — §3's structural relation is exercised satisfied AND violated, because that relation is what makes the source-field axis load-bearing.

Required boundary coverage: no_reveal_token (FX02, FX07, FX16), endpoint_before_after_boundary (FX03, FX04, FX05), terminates_at_AUTH_GATE (FX01, FX06, FX07), ABSTAIN_present (FX08, FX09), nested_drawer (FX10), sibling_drawer (FX11), empty_sequence (FX12), open_reveal_set_SWITCH_TAB (FX13, FX14), source_field_probe (FX17, FX18)

## 3. Case table

| case | task_flow_sequence | S md | F md (explicit3) | F md (emitted) | md match | S ncd | F ncd cand | F ncd value | ncd match | expectation |
|---|---|---|---|---|---|---|---|---|---|---|
| FX01_SSOT_S3_WORKED_EXAMPLE | `OPEN_GLOBAL_MENU > SELECT_FUNCTION > AUTH_GATE` | True | True | True | OK | 1 | 1 (reveal_tokens_before_first_SELECT_FUNCTION) | None | OK | MUST_AGREE |
| FX02_NO_REVEAL_DIRECT_ENTRY | `SELECT_FUNCTION > ENDPOINT_REACHED` | False | False | False | OK | 0 | 0 (reveal_tokens_before_first_SELECT_FUNCTION) | None | OK | MUST_AGREE |
| FX03_REVEAL_AFTER_ENDPOINT | `SELECT_FUNCTION > ENDPOINT_REACHED > OPEN_GLOBAL_MENU` | False | False | False | OK | 1 | 0 (all_reveal_tokens_before_endpoint) | None | **MISMATCH** | MUST_DIVERGE_BY_DEFINITION |
| FX04_REVEAL_IMMEDIATELY_BEFORE_ENDPOINT | `OPEN_GLOBAL_MENU > ENDPOINT_REACHED` | True | True | True | OK | 1 | 1 (all_reveal_tokens_before_endpoint) | None | OK | MUST_AGREE |
| FX05_ENDPOINT_IS_FIRST_TOKEN | `ENDPOINT_REACHED` | False | False | False | OK | 0 | 0 (all_reveal_tokens_before_endpoint) | None | OK | MUST_AGREE |
| FX06_TERMINAL_AUTH_GATE_WITH_REVEAL | `OPEN_LOCAL_MENU > SELECT_FUNCTION > AUTH_GATE` | True | True | True | OK | 1 | 1 (reveal_tokens_before_first_SELECT_FUNCTION) | None | OK | MUST_AGREE |
| FX07_TERMINAL_AUTH_GATE_NO_REVEAL | `SELECT_FUNCTION > AUTH_GATE` | False | False | False | OK | 0 | 0 (reveal_tokens_before_first_SELECT_FUNCTION) | None | OK | MUST_AGREE |
| FX08_ABSTAIN_AFTER_REVEAL | `OPEN_GLOBAL_MENU > ABSTAIN` | True | True | True | OK | 1 | 1 (all_reveal_tokens_before_endpoint) | None | OK | MUST_AGREE |
| FX09_ABSTAIN_ONLY | `ABSTAIN` | False | False | False | OK | 0 | 0 (all_reveal_tokens_before_endpoint) | None | OK | MUST_AGREE |
| FX10_NESTED_DRAWER | `OPEN_GLOBAL_MENU > OPEN_LOCAL_MENU > SELECT_FUNCTION > ENDPOINT_REACHED` | True | True | True | OK | 2 | 2 (reveal_tokens_before_first_SELECT_FUNCTION) | None | OK | MUST_AGREE |
| FX11_SIBLING_DRAWERS | `OPEN_GLOBAL_MENU > SELECT_CATEGORY > OPEN_GLOBAL_MENU > SELECT_FUNCTION > ENDPOINT_REACHED` | True | True | True | OK | 2 | 2 (reveal_tokens_before_first_SELECT_FUNCTION) | None | OK | MUST_AGREE |
| FX12_EMPTY_SEQUENCE | `(empty)` | False | False | False | OK | 0 | 0 (all_reveal_tokens_before_endpoint) | None | OK | MUST_AGREE |
| FX13_SWITCH_TAB_ONLY | `SWITCH_TAB > SELECT_FUNCTION > ENDPOINT_REACHED` | False | False | None | OK | 0 | 0 (reveal_tokens_before_first_SELECT_FUNCTION) | None | OK | MUST_DIVERGE_BY_DEFINITION |
| FX14_SWITCH_TAB_PLUS_EXPLICIT_REVEAL | `SWITCH_TAB > OPEN_LOCAL_MENU > SELECT_FUNCTION > ENDPOINT_REACHED` | True | True | True | OK | 1 | 1 (reveal_tokens_before_first_SELECT_FUNCTION) | None | OK | MUST_AGREE |
| FX15_EXPAND_ACCORDION | `EXPAND_ACCORDION > SELECT_FUNCTION > ENDPOINT_REACHED` | True | True | True | OK | 1 | 1 (reveal_tokens_before_first_SELECT_FUNCTION) | None | OK | MUST_AGREE |
| FX16_SEARCH_TASK_NO_REVEAL | `INPUT_QUERY > SUBMIT_QUERY > SELECT_RESULT > ENDPOINT_REACHED` | False | False | False | OK | 0 | 0 (reveal_tokens_before_first_SELECT_FUNCTION) | None | OK | MUST_AGREE |
| FX17_DISMISSAL_ONLY_DIFFERENCE | `SELECT_FUNCTION > ENDPOINT_REACHED` | False | False | False | OK | 0 | 0 (reveal_tokens_before_first_SELECT_FUNCTION) | None | OK | MUST_AGREE |
| FX18_REVEAL_ONLY_IN_EXPERIENCED | `SELECT_FUNCTION > ENDPOINT_REACHED` | False | False | False | OK | 0 | 0 (reveal_tokens_before_first_SELECT_FUNCTION) | None | OK | MUST_DIVERGE_BY_DEFINITION |

`F ncd value` is `None` on every row — Lane F emits no scalar for `nav_container_depth` by design (AMB-F06). The `ncd match` column compares Lane S's value against the F *candidate* named in the adjacent cell, under the exposure stipulation recorded per row. It is a reading-to-reading check, not a value check.

Summary: aligned-reading mismatches (menu_dependency) = none · emitted-value mismatches = ['FX13_SWITCH_TAB_ONLY'] · nav_container_depth reading mismatches = ['FX03_REVEAL_AFTER_ENDPOINT'] · cross-field mismatches = ['FX18_REVEAL_ONLY_IN_EXPERIENCED']

## 4. Divergences — which input, and why it split

### DIV-01 · `menu_dependency` — EMISSION_POLICY_OVER_AN_OPEN_SSOT_SET

- cases: FX13_SWITCH_TAB_ONLY
- why: 04 §5 writes 'OPEN_GLOBAL_MENU/OPEN_LOCAL_MENU/EXPAND_ACCORDION 등 reveal token' and §4 writes 'OPEN/REVEAL 계열'. Both leave the set open. S (AMB-S06) closes it at the three named tokens by default and requires any extension to be passed explicitly; F (AMB-F05) keeps both readings and withholds a value while they disagree. On this input the two readings disagree, so F emits None where S emits False. On the shared explicit3 reading the two lanes agree exactly.
- defect? No — not at present. It becomes a REAL divergence the moment A rules that SWITCH_TAB IS a reveal token: S's default would then be wrong on every tab-entry service, and 05 §2-A's menu-dependency rate would flip for that family. The divergence is contingent on an unresolved ruling, which is why it is escalated rather than merged.

### DIV-02 · `nav_container_depth` — POPULATION_AXIS_DIFFERS

- cases: FX03_REVEAL_AFTER_ENDPOINT
- why: S's recompute_nav_container_depth counts over seq[:exposure_step_index] and applies NO endpoint cut, so a reveal token occurring after ENDPOINT_REACHED is counted whenever the supplied index reaches it. All three of F's candidates first take prefix_before_endpoint(). With an exposure index at the end of the sequence, S=1 and F's corresponding candidate=0 from that rule alone.
- defect? Not decidable from the SSOT. 04 §5 says 'task control 노출 전', not 'endpoint 전' — the endpoint cut is F's import from the menu_dependency rule, and S's absence of it is a literal reading. Whether an exposure point can legitimately sit after the endpoint is exactly what AMB-S08 / AMB-F06 leave open.

### DIV-03 · `nav_container_depth` — SOURCE_FIELD_AXIS_DIFFERS — NO SCALAR TO COMPARE

- cases: FX01_SSOT_S3_WORKED_EXAMPLE, FX02_NO_REVEAL_DIRECT_ENTRY, FX03_REVEAL_AFTER_ENDPOINT, FX04_REVEAL_IMMEDIATELY_BEFORE_ENDPOINT …
- why: The two lanes resolved the same gap in opposite directions. S made the exposure point a REQUIRED PARAMETER (push the decision to the caller, then compute exactly). F declared the quantity NOT COMPUTABLE from a token sequence and published the span of plausible readings instead. Neither invented an exposure rule, which is why neither can be checked against the other as a number.
- defect? No. It is the DIFFERENT_QUANTITIES verdict itself.
- for reconciliation: F's three candidates BRACKET S's output: under the stipulation 'exposure = first SELECT_FUNCTION' S reproduces F's `reveal_tokens_before_first_SELECT_FUNCTION` on every fixture where both are defined (see ncd_reading_mismatches). So the two are the SAME function of the sequence once an exposure rule is fixed — they differ only in who is allowed to fix it. That is a ruling for A, not a merge for D.

### DIV-04 · `menu_dependency` — SOURCE_FIELD_AXIS — DEMONSTRATED LOAD-BEARING

- cases: FX18_REVEAL_ONLY_IN_EXPERIENCED
- why: When the two sequences differ by more than DISMISS_OBSTRUCTION, the field choice changes the answer. Same-field comparison agrees; cross-field comparison does not. F's `base_invariant` assertion — which holds on every well-formed fixture — is FALSE here, and F separately flags TASK_EXPERIENCED_INCONSISTENT (AMB-F11).
- defect? No — it is the reason S makes `sequence_field` a required argument and F asserts base invariance instead of assuming it. Both guards fire. It is recorded because any reconciliation that drops either guard would merge two different quantities silently.

## 5. Mutation check — can this comparator fail?

| mutation | target | channel | newly flagged | verdict |
|---|---|---|---|---|
| MUT00_NULL | control | (baseline) | — | BASELINE_STABLE |
| MUT01_MD_ALWAYS_TRUE | menu_dependency | md_aligned_reading_mismatches | FX02_NO_REVEAL_DIRECT_ENTRY, FX03_REVEAL_AFTER_ENDPOINT, FX05_ENDPOINT_IS_FIRST_TOKEN, FX07_TERMINAL_AUTH_GATE_NO_REVEAL, FX09_ABSTAIN_ONLY, FX12_EMPTY_SEQUENCE, FX13_SWITCH_TAB_ONLY, FX16_SEARCH_TASK_NO_REVEAL, FX17_DISMISSAL_ONLY_DIFFERENCE, FX18_REVEAL_ONLY_IN_EXPERIENCED | CAUGHT |
| MUT02_MD_NO_ENDPOINT_CUT | menu_dependency | md_aligned_reading_mismatches | FX03_REVEAL_AFTER_ENDPOINT | CAUGHT |
| MUT03_MD_OPEN_REVEAL_SET | menu_dependency | md_aligned_reading_mismatches | FX13_SWITCH_TAB_ONLY | CAUGHT |
| MUT04_NCD_OFF_BY_ONE | nav_container_depth | ncd_reading_mismatches | FX01_SSOT_S3_WORKED_EXAMPLE, FX02_NO_REVEAL_DIRECT_ENTRY, FX04_REVEAL_IMMEDIATELY_BEFORE_ENDPOINT, FX05_ENDPOINT_IS_FIRST_TOKEN, FX06_TERMINAL_AUTH_GATE_WITH_REVEAL, FX07_TERMINAL_AUTH_GATE_NO_REVEAL, FX08_ABSTAIN_AFTER_REVEAL, FX09_ABSTAIN_ONLY, FX10_NESTED_DRAWER, FX11_SIBLING_DRAWERS, FX12_EMPTY_SEQUENCE, FX13_SWITCH_TAB_ONLY, FX14_SWITCH_TAB_PLUS_EXPLICIT_REVEAL, FX15_EXPAND_ACCORDION, FX16_SEARCH_TASK_NO_REVEAL, FX17_DISMISSAL_ONLY_DIFFERENCE, FX18_REVEAL_ONLY_IN_EXPERIENCED | CAUGHT |

All mutations detected: **True**. No lane module was ever modified. Mutations are wrappers around injected callables; the baseline run above and the reported case_table both use the unwrapped lane functions. Nothing to restore.

`MUT02` is deliberately localized — it is visible only in `FX03`, which shows the comparator flags the specific broken case rather than collapsing everything. `MUT03` is the mutation that matters for reconciliation: it simulates Lane S quietly adopting the open reveal set, exactly the merge a careless reconciliation would make.

## 6. Remaining ambiguity — raised, not filled

### AMB-X01 · `menu_dependency`

- **question**: Is SWITCH_TAB a reveal token?
- **SSOT**: 04 §5 '... EXPAND_ACCORDION 등 reveal token'; 04 §4 'OPEN/REVEAL 계열 token'.
- **state**: OPEN. T-A-V3-STEP1-006 does not touch it — 006 rules on activation_depth membership and on encoding drawer direction as a variable, neither of which closes the menu_dependency reveal set.
- **why it matters**: S returns False and F returns None on tab-entry paths. 05 §2-A's menu-dependency rate for tab-first services depends entirely on this.
- **owner**: A (SSOT)

### AMB-X02 · `nav_container_depth`

- **question**: Does the endpoint cut apply to nav_container_depth, or only to menu_dependency?
- **SSOT**: 04 §5 nav rule says 'task control 노출 전' and never mentions the endpoint. The endpoint appears only in the menu_dependency rule.
- **state**: OPEN, and newly surfaced by this convergence check — neither lane registered it, because neither had the other's population rule to compare against.
- **why it matters**: Changes the count whenever a reveal token follows ENDPOINT_REACHED.
- **owner**: A (SSOT)

### AMB-X03 · `nav_container_depth`

- **question**: Which step is 'task control 노출'? Is the exposure point an input the collector supplies, or a rule derivable from the token sequence?
- **SSOT**: 04 §5 'task control 노출 전 nested reveal 수' / 04 §4 'task control 노출 전 menu/drawer expansion 수'. No canonical-18 token marks exposure.
- **state**: OPEN. AMB-S08 and AMB-F06 are the same gap, registered independently by two lanes that never spoke — which is corroborating evidence that the gap is in the SSOT and not in either implementation.
- **why it matters**: Without a ruling, nav_container_depth has no value: F emits none, and S's value is only as defined as the caller's exposure index.
- **owner**: A (SSOT) / B (collector — whether fact_flow_step can carry an exposure marker)

### AMB-X04 · `nav_container_depth`

- **question**: Does a SIBLING reveal count toward depth? §5 says 'nested reveal'; §4 says 'menu/drawer expansion 수'.
- **SSOT**: 04 §5 vs 04 §4, quoted above.
- **state**: OPEN — and a CONVERGENT BLIND SPOT. Both lanes count flat occurrences (S sets nesting_verified=False; F counts token occurrences), so on FX11 they agree on 2 while §5's 'nested' would arguably give 1. Agreement here is NOT evidence of correctness: it is two implementations sharing the same unimplemented qualifier.
- **why it matters**: A hamburger reopened after a category selection is not a 2-deep container hierarchy. Counting it as one inflates depth for services with shallow, repetitive navigation.
- **owner**: A (SSOT)

### AMB-X05 · `menu_dependency / nav_container_depth`

- **question**: What is the value for an EMPTY sequence, or for a path that is only ABSTAIN?
- **SSOT**: 04 §2 defines ABSTAIN as '경로 불확정으로 억지 판정하지 않는다'. §5 gives no empty-sequence case.
- **state**: OPEN — second CONVERGENT BLIND SPOT. On FX09/FX12 both lanes emit a determinate False/0 for a path that is either undetermined or absent. They agree, and the agreement may be jointly wrong: MISSING would also be defensible. F at least marks derived_values_interpretable=False on ABSTAIN; S carries no such flag.
- **why it matters**: A determinate False for an undetermined path enters §2-A rates as a real negative and is indistinguishable from an observed absence of menus.
- **owner**: A (SSOT)

Two of these (`AMB-X04`, `AMB-X05`) are **convergent blind spots**: the lanes agree because both left the same qualifier unimplemented. Agreement there is not evidence of correctness, and this report does not count it as convergence in favour of either implementation.

## 7. Source stability

The two lane modules are being edited concurrently by other Lane workers in this worktree. This harness copies both files out, hashes the copy, imports the copy, and re-hashes the originals afterwards. Everything above was computed against the snapshot hashes.

| module | sha256 at snapshot | sha256 after run | changed during run |
|---|---|---|---|
| lane_s | `1ab63cc4a350fb61` | `1ab63cc4a350fb61` | False |
| lane_f | `8985dd413f3869d2` | `8985dd413f3869d2` | False |

Live lane files were byte-identical to the imported snapshot before and after the run.

## 8. Limitation

- This is a definitional convergence check on synthetic fixtures. It says nothing about whether either implementation produces correct values on real observations — REAL access is 0 and MAIN50 measurement data does not exist.
- The fixture is 18 hand-derived cases chosen to sit on definitional boundaries. It is a boundary probe, not a sample. No rate, proportion, or statistic is computed from it, and it must never be treated as one.
- `exposure_step_index` is stipulated by this fixture (AMB-X03). Every nav_container_depth comparison is therefore conditional on a scaffold the SSOT has not ratified.
- Convergence on a case is not correctness on that case. FX09/FX11/FX12 are documented as convergent blind spots where both lanes share the same unimplemented qualifier.
- Only the two duplicated variables were compared. Both lane modules compute much else; nothing here validates any of it.
- No canonical implementation is designated and no lane file was read as anything but read-only. Reconciliation, and any GO/NO-GO, sit outside this worker's scope.
- The lane modules were being rewritten by concurrent workers while this ran. The result is pinned to the snapshot hashes recorded in provenance.source_stability; if `any_drift` is true, re-run before using this for reconciliation.
- 45 same-family pairs are cells of a distance matrix, not n=45. No pair-level statistic appears here, and none should be derived from this artefact.

This harness does not name either implementation as correct. S is not 'more complete' for emitting a nav_container_depth value — it emits one because it demands an input F refuses to invent. F is not 'more rigorous' for withholding menu_dependency — it withholds because it kept a set open that S closed by documented default. Choosing between them is a reconciliation decision for D, and it needs A's rulings first.

