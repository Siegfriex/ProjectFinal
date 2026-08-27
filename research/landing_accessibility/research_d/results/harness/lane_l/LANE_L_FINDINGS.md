# Lane L — Label / Accessible Name axis harness

- **verdict**: `READY_WITH_AMBIGUITY`
- **base SHA**: `7448184a811f5d7d8772f21488bb75418fde3313` (`claude-d/research-sandbox-v21`)
- **SSOT**: `SSOTV3` MANIFEST self-sha256 `1735c956d4a3461ee9eb2543c5c474942887bcbd117f5876d5486207f2f72e0a`
- **code**: `research_d/tools/v3_harness/lane_l_label_ax.py`
- **machine output**: `research_d/results/harness/lane_l/LANE_L_HARNESS.json`
- **fixtures written**: `research_d/results/harness/lane_l/fixtures/*.html`

This is outcome-independent preparation. **MAIN50 has no measured data yet.** Every number
below comes from synthetic fixtures. No real service was contacted.

---

## 1. What was implemented

Five codebook variables from `04_FLOW_CODEBOOK_v3.0.md` §4, verbatim definitions embedded in
the JSON under `codebook_definitions_verbatim`.

| Variable | Implementation |
|---|---|
| `visible_label_text` | pass-through + normalization + state classification |
| `accessible_name` | pass-through + normalization + state classification |
| `accessible_name_source` | derived, 9-member enum, evidence-first attribution |
| `label_relation` | derived, 6-member enum, normalize + **exact**, synonym-map-only semantics |
| `entry_label_modality` | derived, 5-member enum, `ICON_ONLY_AX_NAMED` vs `ICON_ONLY_UNNAMED` separated |

`entry_control_type` is an **input-only** field on `LabelObservation`, consumed opaquely by
CE-2. This lane defines no control-type taxonomy and reads/writes no other lane's file.

### The separation is enforced, not assumed

`visible_label_text` and `accessible_name` are never merged, defaulted into one another, or
back-filled. Mutation `M12_AX_FALLBACK_TO_VISIBLE` injects exactly the merge SSOT `00 §8`
forbids and is killed by 3 value fixtures plus 4 swap-symmetry cases.

### Three text states, never two

`MISSING` (`None`, never observed) / `EMPTY` (observed, normalizes to `""`) / `PRESENT`.

- Both sides `EMPTY` → `label_relation = NONE`.
- `PRESENT` / `EMPTY` → `VISIBLE_ONLY`; `EMPTY` / `PRESENT` → `AX_ONLY`.
- **Either side `MISSING` → `label_relation = null`** plus
  `label_relation_undeterminable_reason ∈ {BOTH_UNOBSERVED, VISIBLE_UNOBSERVED, AX_UNOBSERVED}`.
  The codebook enum has no member meaning "not observed", so none is manufactured.
  `NONE` is reserved for observed-and-empty on both sides (AMB-L-08).

Mutation `M5_EMPTY_IS_MISSING` collapses the distinction and is killed by 15 checks.

### The synonym map ships empty — on purpose

`SYNONYM_MAP = {}`. `SEMANTIC_EQUIV` is emitted **iff** both normalized forms appear in the map
and map to the same concept id. There is no similarity computation, no fallback, no partial
match, no edit distance, no embedding. **D did not and must not fill this map — it is A's
authority.** `load_synonym_map()` refuses any file whose `authority` field is not `"A"`.

Consequence to state plainly: until A authors a map, `SEMANTIC_EQUIV` is unreachable on real
data and every genuinely-synonymous pair lands in `DIFFERENT`. The `DIFFERENT` bucket in
`05 §2-C` will be inflated by exactly that amount. The code path is proved reachable in
`fixture_results.synonym_map_code_path` using a map explicitly tagged
`TEST_ONLY_NOT_AUTHORITATIVE`.

---

## 2. Verification

| Check | Result |
|---|---|
| Value fixtures (positive + negative, `label_relation` / `accessible_name_source` / `entry_label_modality`) | **60 / 60** |
| Swap symmetry (bidirectional: reversing the two sides must mirror the relation) | **30 / 30** |
| Counterexample-detector checks (positive + negative) | **9 / 9** |
| Korean HTML round-trip (utf-8, euc-kr, cp949, undeclared) | **4 / 4** |
| Mutations killed | **12 / 12**, 0 survivors |
| Restored to baseline after mutations | true |

Enum coverage: `accessible_name_source` 9/9 exercised, `entry_label_modality` 5/5 exercised,
`label_relation` 5/6 — `SEMANTIC_EQUIV` deliberately unexercised (see above).

### Normalization-trap fixtures, answers pinned in advance

| Fixture | Inputs | Pinned answer |
|---|---|---|
| leading/trailing space | `"  검색  "` vs `"검색"` | `MATCH` |
| internal whitespace runs | `"검색   하기"` vs `"검색 하기"` | `MATCH` |
| NBSP `U+00A0` | `"검색 하기"` vs `"검색 하기"` | `MATCH` |
| ideographic space `U+3000` | `"검색　하기"` vs `"검색 하기"` | `MATCH` |
| NFC vs NFD 한글 | `"검색"` vs decomposed jamo | `MATCH` |
| fullwidth vs ASCII | `"ＳＥＡＲＣＨ"` vs `"SEARCH"` | `DIFFERENT` (NFC primary) |
| fullwidth digits | `"１２３"` vs `"123"` | `DIFFERENT` |
| case | `"Search"` vs `"search"` | `DIFFERENT` |
| ZWSP inside | `"검​색"` vs `"검색"` | `DIFFERENT` |
| BOM prefix | `"﻿검색"` vs `"검색"` | `DIFFERENT` |
| ZWSP-only visible label | `"​"` vs `"검색"` | `DIFFERENT` (visible side is `PRESENT`) |

The last six are flagged `normalization_sensitive: true` with the diverging readings listed
per row — they change under NFKC / casefold / zero-width-strip. See §3.

### Mutation → what caught it

| Mutation | Killed by |
|---|---|
| `M1_NO_WHITESPACE_COLLAPSE` | 11 checks (all whitespace fixtures) |
| `M2_NFKC_PRIMARY` | fullwidth fixtures |
| `M3_CASEFOLD_PRIMARY` | case fixture |
| `M4_NO_UNICODE_NORMALIZE` | NFC/NFD fixtures incl. an `accessible_name_source` one |
| `M5_EMPTY_IS_MISSING` | 15 checks |
| `M6_NO_MIXED` | `SRC-09-mixed-concat` |
| `M7_STRIP_ZERO_WIDTH` | 4 zero-width fixtures |
| `M8_REVERSE_PRECEDENCE` | `SRC-08-tie-aria-label-wins` |
| `M9_MERGE_ICON_ONLY` | 2 `ICON_ONLY_UNNAMED` fixtures |
| `M10_RAW_KEYS` | `CE1-nbsp-not-a-difference` |
| `M11_ONLY_SIDE_COLLAPSE` | 1 fixture + 2 symmetry cases |
| `M12_AX_FALLBACK_TO_VISIBLE` | 3 fixtures + 4 symmetry cases |

Mutations are applied through an in-module context manager (`mutation(...)`), so the run is
reproducible and the restore is verified programmatically, not by eye.

### Encoding — and a correction to how D-DEF-01 is stated

Every HTML read goes through `research_d/tools/html_decode.parse_html`. Korean fixtures were
written in UTF-8, EUC-KR, CP949, and UTF-8-with-no-declaration, then round-tripped through the
full calculator: visible text, `aria-label`, `alt`, and resolved `aria-labelledby` text all
survive intact in all four, and `label_relation` / `accessible_name_source` /
`entry_label_modality` come out identical across encodings.

**Negative control finding.** With lxml 6.1.1, handing raw bytes to `lxml.html.fromstring`
produces mojibake **only when the document carries no in-document charset declaration**
(libxml2 then defaults to Latin-1). Declared UTF-8, EUC-KR *and* CP949 all decode correctly
even from bytes:

| fixture | bytes → lxml | via `parse_html` |
|---|---|---|
| `utf8` (declared) | correct | correct |
| `euckr` (declared) | correct | correct |
| `cp949` (declared) | correct | correct |
| `utf8_no_declaration` | **`ì¹ì°¨ê¶ ìë§¤`** | correct |

So D-DEF-01's remedy is right, but its stated mechanism — "lxml ignored the declared charset"
— does not reproduce here. The reproducing condition is an **absent** declaration. D has not
inspected the real `dom.html` files under this lane, so this is a parser-level observation on
fixtures, **not** a re-attribution of the original 6/56 incident. Someone with evidence access
should check whether those 6 files actually carried a `<meta charset>` inside libxml2's
lookahead window; if they did, there is a second cause still unaccounted for.

---

## 3. `AMBIGUOUS_DEFINITION` — needs an A ruling

Each has a primary reading implemented, the competing reading also computed, and divergence
reported per row. None of these is a threshold; all are enum-procedure gaps.

| id | Variable | Gap | Primary reading taken | If A rules the other way |
|---|---|---|---|---|
| **AMB-L-01** | `label_relation` | `04 §5` says "Unicode normalize", not which form | **NFC** | NFKC merges fullwidth/halfwidth, circled and ligature forms → some `DIFFERENT` become `MATCH` |
| **AMB-L-02** | `label_relation` | case-sensitivity unstated; "exact" taken literally | **case-sensitive** | casefold merges `Search`/`search` |
| **AMB-L-03** | `label_relation`, state | are zero-width chars "whitespace"? (Unicode says no) | **preserved** | a ZWSP-only label flips `PRESENT`→`EMPTY`, flipping the row `DIFFERENT`→`AX_ONLY` |
| **AMB-L-04** | `accessible_name_source` | no attribution procedure; ties unresolvable by value | value match, **W3C accname 1.2 precedence as tie-break only**, row flagged `accessible_name_source_ambiguous` | leave every tie unresolved |
| **AMB-L-05** | `accessible_name_source` | `MIXED` has no operational definition | name == space-joined concatenation of 2–3 present candidates | `MIXED` only when the collector asserts it (already supported — collector assertion always wins) |
| **AMB-L-06** | `entry_label_modality` | precedence between `HIDDEN_UNTIL_REVEAL` and the icon/text members | **reveal dominates** | icon-only rates in `05 §2-C` are currently understated for revealed controls |
| **AMB-L-07** | `entry_label_modality` | no member covers "no visible text and no icon" | emit no value + reason | extend the enum |
| **AMB-L-08** | `label_relation` | no member means "a side was never observed" | `null` + reason; `NONE` reserved for observed-empty | mapping unobserved→`NONE` would inflate `NONE` and destroy the empty/missing distinction the contract requires |
| **AMB-L-09** | `label_relation` | is NBSP / `U+3000` collapsed by "whitespace normalize"? | **collapsed** (Python `str.split()` semantics) | NBSP becomes significant |
| **AMB-L-10** | `accessible_name_source` | observed-**empty** AX name while naming candidates exist (e.g. `aria-label=""`) | unresolved, reason `EMPTY_NAME_WITH_CANDIDATES` | `NONE` — loses "computed nothing despite sources" vs "nothing available" |

`READY` is withheld solely because of these ten. The calculator runs, is self-consistent, and
its fixtures bite; the primary readings are D's literal reading of the codebook, **not an A
ruling.**

---

## 4. Counterexample detectors

Both are pure grouping. No threshold, no cutoff, no score.

**CE-1 — `detect_same_ax_name_different_visible`**: group observations whose
`accessible_name` is `PRESENT` by normalized form; flag groups holding more than one distinct
normalized `visible_label_text` (also `PRESENT`). `EMPTY` and `MISSING` sides are excluded so
an absence can never manufacture a collision. Verified: the positive pair is found with exact
membership; a pair differing only by NBSP is **not** counted as two forms; identical pairs and
empty/missing sides are not flagged.

**CE-2 — `detect_same_visible_different_control_type`**: group observations whose
`visible_label_text` is `PRESENT` by normalized form; flag groups holding more than one
distinct `entry_control_type`. Control type arrives as an opaque input string on
`LabelObservation.entry_control_type`. Verified: the positive group reports both types; rows
with `entry_control_type = None` are ignored; same-type groups are not flagged.

Why these two matter for `05 §2-C`: CE-1 means "accessible name forms" and "visible label
unique forms" cannot be counted off one column — the two counts are not interchangeable and a
collapse in one is invisible in the other. CE-2 means a visible-label count is not a control
count.

---

## 5. Limitations (read before using any output)

1. **No measured data exists.** Everything here is synthetic. Nothing is evidence about MAIN50.
2. **This module does not compute accessible names.** It consumes what the collector recorded
   (`04 §7` assigns naming computation to the browser AX tree). If the collector's AX capture is
   wrong, every derived value here is wrong in the same direction and **this harness cannot see
   it.** The harness validates the calculator, not the collector.
3. `accessible_name_source` attribution is exact string matching against the candidate values
   the collector stored. A name produced by a naming path the collector did not record
   (pseudo-element text, shadow-DOM label, implicit table/legend/fieldset name) returns
   `NAME_NOT_ATTRIBUTABLE` — deliberately unresolved rather than wrong-but-plausible.
4. With the empty synonym map, `DIFFERENT` is the disposal bucket for all semantic equivalence.
5. Whitespace normalization uses Python `str.split()` semantics (AMB-L-09).
6. `extract_label_evidence_from_html` reads one element by xpath. It is a decoding-safety and
   evidence-shape test, **not** a candidate-binding implementation.
7. Fixture expectations were authored by D from the codebook text. Where D's reading is
   contested it is registered in §3 rather than defended.

## 6. Not implemented (out of contract)

AX naming computation · `entry_control_type` classification · any threshold, similarity cutoff
or composite score · embedding/fuzzy/edit-distance label merging (forbidden by `04 §5`) ·
populating the synonym map (A's authority) · icon-only rates, unique-form counts, or any
`05 §2-C` aggregate (needs MAIN50) · gold labels, task gold, holdout access, GO/NO-GO ·
MLflow logging · git operations · REAL service access.
