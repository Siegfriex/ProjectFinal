# gate3 — C streaming QC for the frozen MAIN50 census (T-A-V3-TBX-007 · release V3_TIMEBOX_CENSUS_1230)

**Frozen before collection** (analysis pre-registration side effect). Scope = exactly A's seven reduced checks; nothing else is searched
(leakage: `NOT_ASSESSED_BEYOND_EXISTING_CONTROLS`, never "no leakage").

| file | role |
|---|---|
| `census_qc_c.py` | the seven checks (UNIQUE_TARGETS · MANIFEST_HASH · DUPLICATE · EVIDENCE_OR_TERMINAL · FORBIDDEN_ACTION · FAMILY_10x5 · DENOMINATORS), 14 controls run first on every invocation |
| `ADAPTER_MAP_C.json` | canonical field → B/E field name with status `WIRED_BY_SSOT` / `WIRED_BY_MANIFEST` / `UNBOUND`. UNBOUND ⇒ dependent check `NOT_TESTABLE`, never PASS (R57). Bound once B/E publish the snapshot layout; the binding edit is recorded as a new commit (tool sha changes) |
| `out/CENSUS_QC_C*.json` | tool-generated runs (`measured_at_kst`, tool sha, recomputed manifest hashes, per-check status + n_items, flags with `systemic_candidate` ∈ R9 canonical 8) |

Run: `python3 census_qc_c.py --selftest` · `python3 census_qc_c.py --rows <jsonl|csv|dir> [--adapter ADAPTER_MAP_C.json] [--b-denominators B.json]`
Exit: **0 ran** (flags in JSON, never in the exit code) · **2 did not run** (controls failed / crash) · **3 NO_EVIDENCE_INPUT** (0 rows — not a pass).
Manifest hashes are recomputed from bytes (`git show origin/control/…`), expected values read from the release file — the declaration inside the manifest is displayed, never used.
`completed` = `endpoint_status == ENDPOINT_REACHED`; `AUTH_GATE` terminal is reported separately (R2 two denominators). Derived-metric replay (activation_depth / label_relation / sequence distance, 11:50–12:10 role) uses `gate1/lane6_stats/c_flow_derive.py` (`compare_with_mart_row`, `family_summary`, `pairwise_matrix`) — 30 tests.
C flags; A rules. Whole-census stop only for the release's three conditions.
