# lane5_evidence — C's independent evidence completeness & lineage checker (GATE 1, runs unchanged at GATE 2/3)

**Purpose.** Verify from raw files only (never from B's summary/mart) that every V3 evidence package is complete per state
(S0..Sn) and per step, that every hash matches, and that identity is append-only and never overwritten. Rules are fixed in
`EVIDENCE_CONTRACT_C.md`; this directory is the whole lane. Base worktree `claude-c/assurance-v21 @ 5e05da9`.

## Files
| file | role |
|---|---|
| `EVIDENCE_CONTRACT_C.md` | contract: required files/fields, hash chain, append-only rule, defect catalogue + severities, pre-registered ambiguity resolutions |
| `evidence_lineage_check.py` | runner-agnostic checker (stdlib only). Discovery heuristics D1–D6 in its docstring |
| `make_synthetic_evidence.py` | regenerates the three synthetic fixtures (sets mtimes; re-run after a fresh checkout) |
| `fixtures/{good,bad_overwrite,bad_lineage}/` | synthetic trees, 1 service-task × 3 states × 2 steps each; `fixtures/report_*.json` = checker output |

## How to run
```bash
cd research/landing_accessibility/assurance/gate1/lane5_evidence
python3 make_synthetic_evidence.py                       # rebuild fixtures (mtimes matter for overwrite detection)
python3 evidence_lineage_check.py fixtures/good --path-manifest fixtures/good/path_manifest.json --out r.json
python3 evidence_lineage_check.py <REAL_EVIDENCE_ROOT> [--path-manifest <path_manifest.json>] --out report.json
```
Exit 0 ⇔ no systemic defect (`COMPLETE` or `COMPLETE_WITH_ISOLATED_DEFECTS`); 2 ⇔ `SYSTEMIC_DEFECT`; 3 usage error.
`ROOT/path_manifest.json` is auto-detected when the flag is omitted; without any path manifest a `<manifest>.sha256` sidecar is required.

## Results (fixtures, regenerated then checked)
| fixture | injected condition | verdict | exit | defects |
|---|---|---|---|---|
| `good` | none | COMPLETE | 0 | — |
| `bad_overwrite` | `S1/screenshot.png` rewritten after manifest seal | SYSTEMIC_DEFECT | 2 | HASH_MISMATCH 1, OVERWRITE_DETECTED 1 (systemic) |
| `bad_lineage` | step 1 → state `S9` (absent); `S2/screenshot.png` deleted; `service_id` = "Coupang Mobile App" | SYSTEMIC_DEFECT | 2 | DISPLAY_NAME_AS_ID 10 (5 systemic on spine, 5 isolated), LINEAGE_BREAK 1, MISSING_ARTIFACT 1 |

Negative controls run outside fixtures (scratchpad) so that a pass is not an empty result: good tree with no path manifest ⇒
MANIFEST_SHA_UNBOUND; manifest edited after freeze ⇒ MANIFEST_SHA_UNBOUND (+LINEAGE_BREAK on url); same state identity re-declared with
new hashes in a second manifest ⇒ OVERWRITE_DETECTED; step hash edited ⇒ HASH_MISMATCH (isolated, exit 0); run dir duplicated ⇒ IDENTITY_COLLISION.

### `good` → **COMPLETE**
```json
{"checker": "evidence_lineage_check.py", "contract": "EVIDENCE_CONTRACT_C.md", "root": "/home/sieg/projects-wsl/ProjectFinal/.agent_worktrees/claude_c_assurance_v21/research/landing_accessibility/assurance/gate1/lane5_evidence/fixtures/good", "path_manifest": "/home/sieg/projects-wsl/ProjectFinal/.agent_worktrees/claude_c_assurance_v21/research/landing_accessibility/assurance/gate1/lane5_evidence/fixtures/good/path_manifest.json", "n_manifests": 1, "n_states": 3, "n_steps": 2, "n_unknown_records": 0, "n_artifacts_checked": 15, "counts_by_kind": {}, "systemic": false, "verdict": "COMPLETE", "path_manifest_autodetected": false, "defects": [
]}
```

### `bad_overwrite` → **SYSTEMIC_DEFECT**
```json
{"checker": "evidence_lineage_check.py", "contract": "EVIDENCE_CONTRACT_C.md", "root": "/home/sieg/projects-wsl/ProjectFinal/.agent_worktrees/claude_c_assurance_v21/research/landing_accessibility/assurance/gate1/lane5_evidence/fixtures/bad_overwrite", "path_manifest": "/home/sieg/projects-wsl/ProjectFinal/.agent_worktrees/claude_c_assurance_v21/research/landing_accessibility/assurance/gate1/lane5_evidence/fixtures/bad_overwrite/path_manifest.json", "n_manifests": 1, "n_states": 3, "n_steps": 2, "n_unknown_records": 0, "n_artifacts_checked": 15, "counts_by_kind": {"HASH_MISMATCH": 1, "OVERWRITE_DETECTED": 1}, "systemic": true, "verdict": "SYSTEMIC_DEFECT", "path_manifest_autodetected": false, "defects": [
  {"kind": "HASH_MISMATCH", "severity": "isolated", "path": "svc_coupang_m/T07_search_product/run_20260828T000000Z_01/S1/screenshot.png", "detail": "screenshot: manifest=315ad8df2d79.. actual=a02aa6665eb9.."},
  {"kind": "OVERWRITE_DETECTED", "severity": "systemic", "path": "svc_coupang_m/T07_search_product/run_20260828T000000Z_01/S1/screenshot.png", "detail": "screenshot rewritten after manifest seal (artifact mtime 1787852908 > manifest mtime 1787852858)"}
]}
```

### `bad_lineage` → **SYSTEMIC_DEFECT**
```json
{"checker": "evidence_lineage_check.py", "contract": "EVIDENCE_CONTRACT_C.md", "root": "/home/sieg/projects-wsl/ProjectFinal/.agent_worktrees/claude_c_assurance_v21/research/landing_accessibility/assurance/gate1/lane5_evidence/fixtures/bad_lineage", "path_manifest": "/home/sieg/projects-wsl/ProjectFinal/.agent_worktrees/claude_c_assurance_v21/research/landing_accessibility/assurance/gate1/lane5_evidence/fixtures/bad_lineage/path_manifest.json", "n_manifests": 1, "n_states": 3, "n_steps": 2, "n_unknown_records": 0, "n_artifacts_checked": 14, "counts_by_kind": {"DISPLAY_NAME_AS_ID": 10, "LINEAGE_BREAK": 1, "MISSING_ARTIFACT": 1}, "systemic": true, "verdict": "SYSTEMIC_DEFECT", "path_manifest_autodetected": false, "defects": [
  {"kind": "DISPLAY_NAME_AS_ID", "severity": "systemic", "path": "Coupang Mobile App/T07_search_product/run_20260828T000000Z_01/evidence_manifest.jsonl#0", "detail": "service_id='Coupang Mobile App' is not an identifier (whitespace/non-ASCII/equals display_name)"},
  {"kind": "DISPLAY_NAME_AS_ID", "severity": "isolated", "path": "Coupang Mobile App/T07_search_product/run_20260828T000000Z_01/evidence_manifest.jsonl#0", "detail": "observation_id='Coupang Mobile App.T07_search_product.run_20260828T000000Z_01.a1.S0' is not an identifier (whitespace/non-ASCII/equals display_name)"},
  {"kind": "DISPLAY_NAME_AS_ID", "severity": "systemic", "path": "Coupang Mobile App/T07_search_product/run_20260828T000000Z_01/evidence_manifest.jsonl#1", "detail": "service_id='Coupang Mobile App' is not an identifier (whitespace/non-ASCII/equals display_name)"},
  {"kind": "DISPLAY_NAME_AS_ID", "severity": "isolated", "path": "Coupang Mobile App/T07_search_product/run_20260828T000000Z_01/evidence_manifest.jsonl#1", "detail": "observation_id='Coupang Mobile App.T07_search_product.run_20260828T000000Z_01.a1.S1' is not an identifier (whitespace/non-ASCII/equals display_name)"},
  {"kind": "DISPLAY_NAME_AS_ID", "severity": "systemic", "path": "Coupang Mobile App/T07_search_product/run_20260828T000000Z_01/evidence_manifest.jsonl#2", "detail": "service_id='Coupang Mobile App' is not an identifier (whitespace/non-ASCII/equals display_name)"},
  {"kind": "DISPLAY_NAME_AS_ID", "severity": "isolated", "path": "Coupang Mobile App/T07_search_product/run_20260828T000000Z_01/evidence_manifest.jsonl#2", "detail": "observation_id='Coupang Mobile App.T07_search_product.run_20260828T000000Z_01.a1.S2' is not an identifier (whitespace/non-ASCII/equals display_name)"},
  {"kind": "MISSING_ARTIFACT", "severity": "isolated", "path": "Coupang Mobile App/T07_search_product/run_20260828T000000Z_01/evidence_manifest.jsonl#2 -> S2/screenshot.png", "detail": "screenshot file not found on disk"},
  {"kind": "DISPLAY_NAME_AS_ID", "severity": "systemic", "path": "Coupang Mobile App/T07_search_product/run_20260828T000000Z_01/evidence_manifest.jsonl#3", "detail": "service_id='Coupang Mobile App' is not an identifier (whitespace/non-ASCII/equals display_name)"},
  {"kind": "DISPLAY_NAME_AS_ID", "severity": "isolated", "path": "Coupang Mobile App/T07_search_product/run_20260828T000000Z_01/evidence_manifest.jsonl#3", "detail": "flow_observation_id='Coupang Mobile App.T07_search_product.run_20260828T000000Z_01.a1.flow' is not an identifier (whitespace/non-ASCII/equals display_name)"},
  {"kind": "DISPLAY_NAME_AS_ID", "severity": "systemic", "path": "Coupang Mobile App/T07_search_product/run_20260828T000000Z_01/evidence_manifest.jsonl#4", "detail": "service_id='Coupang Mobile App' is not an identifier (whitespace/non-ASCII/equals display_name)"},
  {"kind": "DISPLAY_NAME_AS_ID", "severity": "isolated", "path": "Coupang Mobile App/T07_search_product/run_20260828T000000Z_01/evidence_manifest.jsonl#4", "detail": "flow_observation_id='Coupang Mobile App.T07_search_product.run_20260828T000000Z_01.a1.flow' is not an identifier (whitespace/non-ASCII/equals display_name)"},
  {"kind": "LINEAGE_BREAK", "severity": "isolated", "path": "Coupang Mobile App/T07_search_product/run_20260828T000000Z_01/evidence_manifest.jsonl#4", "detail": "state_after_id='Coupang Mobile App.T07_search_product.run_20260828T000000Z_01.a1.S9' does not resolve to any state record"}
]}
```

## What remains once B's real layout is known (field-name mapping only — rules do not change)
- Extend `FIELD_ALIASES` / `ARTIFACT_ALIASES` / `STEP_HASH_FIELDS` at the top of the checker with B's actual names.
- If B's path manifest uses other keys than `runs[].evidence_manifest` / `evidence_manifest_sha256`, add them in `load_path_manifest`.
- If B stores states and steps in separate files, nothing changes (records are classified by shape, D3). If artifact paths are absolute
  or rooted elsewhere, add one resolution rule in D4. Severity table, hash chain, append-only and identity rules stay as contracted.
