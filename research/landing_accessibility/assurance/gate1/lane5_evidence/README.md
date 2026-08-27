# lane5_evidence — C's independent evidence completeness & lineage checker (GATE 1, runs unchanged at GATE 2/3)

**Purpose.** Verify from raw files only (never from B's summary/mart) that every V3 evidence package is complete per state (S0..Sn),
per step and per run (terminal flow record, T-A-V3-STEP1-007 R11/R13), that every hash matches, and that identity is append-only and
never overwritten. Rules are fixed in `EVIDENCE_CONTRACT_C.md`; this directory is the whole lane. Base `claude-c/assurance-v21 @ 5e05da9`.

## Files
| file | role |
|---|---|
| `EVIDENCE_CONTRACT_C.md` | contract: required files/fields (state, step, flow), hash chain, append-only rule, defect catalogue + severities, R11 combination table (source: `../c_terminal_table.py`), pre-registered ambiguity resolutions |
| `evidence_lineage_check.py` | runner-agnostic checker (stdlib only). Discovery heuristics D1–D7 in its docstring |
| `make_synthetic_evidence.py` | regenerates the three synthetic fixtures (sets mtimes; re-run after a fresh checkout) |
| `fixtures/{good,bad_overwrite,bad_lineage}/` | synthetic trees, 1 service-task, 3 states × 2 steps × 1 flow record per run; `fixtures/report_*.json` = checker output |

## How to run
```bash
cd research/landing_accessibility/assurance/gate1/lane5_evidence
python3 make_synthetic_evidence.py                       # rebuild fixtures (mtimes matter for overwrite detection)
python3 evidence_lineage_check.py fixtures/good --path-manifest fixtures/good/path_manifest.json --out r.json
python3 evidence_lineage_check.py <REAL_EVIDENCE_ROOT> [--path-manifest <path_manifest.json>] --out report.json
```
Exit 0 ⇔ no systemic defect (`COMPLETE` or `COMPLETE_WITH_ISOLATED_DEFECTS`); 2 ⇔ `SYSTEMIC_DEFECT`; 3 usage error.
`ROOT/path_manifest.json` is auto-detected when the flag is omitted; without any path manifest a `<manifest>.sha256` sidecar is required.

## Results (fixtures regenerated, then checked — re-run 2026-08-28 after the R11 table unification (`gate1/c_terminal_table.py`) and the `collector_sha256` alias; verdicts and counts unchanged)
| fixture | injected condition | verdict | exit | defects |
|---|---|---|---|---|
| `good` | none. Run 01 REACHED×null×auth NONE; run 02 = re-collection under a NEW run_id, ABSTAIN×OTHER+note×UNDETERMINED (R11/R13 positives), collector hash written as `collector_sha256` (T-A-V3-STEP1-015 exact name; alias positive control — with the alias removed from `FIELD_ALIASES` the same tree gives COMPLETE_WITH_ISOLATED_DEFECTS, MISSING_FIELD 2) | COMPLETE | 0 | — |
| `bad_overwrite` | `S1/screenshot.png` rewritten after manifest seal; flow REACHED×OTHER without note | SYSTEMIC_DEFECT | 2 | HASH_MISMATCH 1, OVERWRITE_DETECTED 1 (systemic), SCHEMA_VIOLATION 2 |
| `bad_lineage` | step 1 → `S9` (absent); `S2/screenshot.png` deleted; `service_id`="Coupang Mobile App"; flow EVIDENCE_DEFECT without terminal_reason, auth NONE | SYSTEMIC_DEFECT | 2 | DISPLAY_NAME_AS_ID 12 (6 systemic on spine), LINEAGE_BREAK 1, MISSING_ARTIFACT 1, MISSING_FIELD 1, AFFIRMATIVE_WITHOUT_EVIDENCE 1 |

Negative controls run in scratchpad (so a pass is not an empty result): no path manifest ⇒ MANIFEST_SHA_UNBOUND; manifest edited after
freeze ⇒ MANIFEST_SHA_UNBOUND; same state identity re-declared with new hashes ⇒ OVERWRITE_DETECTED; step hash edited ⇒ HASH_MISMATCH
(isolated, exit 0); run dir duplicated ⇒ IDENTITY_COLLISION; BLOCKED×AUTH_REQUIRED / AUTH_GATE×NONE / out-of-enum value ⇒ SCHEMA_VIOLATION.

### `good` → **COMPLETE**
```json
{"checker": "evidence_lineage_check.py", "contract": "EVIDENCE_CONTRACT_C.md", "root": "/home/sieg/projects-wsl/ProjectFinal/.agent_worktrees/claude_c_assurance_v21/research/landing_accessibility/assurance/gate1/lane5_evidence/fixtures/good", "path_manifest": "/home/sieg/projects-wsl/ProjectFinal/.agent_worktrees/claude_c_assurance_v21/research/landing_accessibility/assurance/gate1/lane5_evidence/fixtures/good/path_manifest.json", "n_manifests": 2, "n_states": 4, "n_steps": 2, "n_flows": 2, "n_unknown_records": 0, "n_artifacts_checked": 20, "counts_by_kind": {}, "systemic": false, "verdict": "COMPLETE", "path_manifest_autodetected": false, "defects": [
]}
```

### `bad_overwrite` → **SYSTEMIC_DEFECT**
```json
{"checker": "evidence_lineage_check.py", "contract": "EVIDENCE_CONTRACT_C.md", "root": "/home/sieg/projects-wsl/ProjectFinal/.agent_worktrees/claude_c_assurance_v21/research/landing_accessibility/assurance/gate1/lane5_evidence/fixtures/bad_overwrite", "path_manifest": "/home/sieg/projects-wsl/ProjectFinal/.agent_worktrees/claude_c_assurance_v21/research/landing_accessibility/assurance/gate1/lane5_evidence/fixtures/bad_overwrite/path_manifest.json", "n_manifests": 1, "n_states": 3, "n_steps": 2, "n_flows": 1, "n_unknown_records": 0, "n_artifacts_checked": 15, "counts_by_kind": {"HASH_MISMATCH": 1, "OVERWRITE_DETECTED": 1, "SCHEMA_VIOLATION": 2}, "systemic": true, "verdict": "SYSTEMIC_DEFECT", "path_manifest_autodetected": false, "defects": [
  {"kind": "HASH_MISMATCH", "severity": "isolated", "path": "svc_coupang_m/T07_search_product/run_20260828T000000Z_01/S1/screenshot.png", "detail": "screenshot: manifest=315ad8df2d79.. actual=a02aa6665eb9.."},
  {"kind": "OVERWRITE_DETECTED", "severity": "systemic", "path": "svc_coupang_m/T07_search_product/run_20260828T000000Z_01/S1/screenshot.png", "detail": "screenshot rewritten after manifest seal (artifact mtime 1787857828 > manifest mtime 1787857778)"},
  {"kind": "SCHEMA_VIOLATION", "severity": "isolated", "path": "svc_coupang_m/T07_search_product/run_20260828T000000Z_01/evidence_manifest.jsonl#5", "detail": "impossible combination REACHED × terminal_reason=OTHER (REACHED admits null only)"},
  {"kind": "SCHEMA_VIOLATION", "severity": "isolated", "path": "svc_coupang_m/T07_search_product/run_20260828T000000Z_01/evidence_manifest.jsonl#5", "detail": "terminal_reason=OTHER requires a non-empty note (R11)"}
]}
```

### `bad_lineage` → **SYSTEMIC_DEFECT**
```json
{"checker": "evidence_lineage_check.py", "contract": "EVIDENCE_CONTRACT_C.md", "root": "/home/sieg/projects-wsl/ProjectFinal/.agent_worktrees/claude_c_assurance_v21/research/landing_accessibility/assurance/gate1/lane5_evidence/fixtures/bad_lineage", "path_manifest": "/home/sieg/projects-wsl/ProjectFinal/.agent_worktrees/claude_c_assurance_v21/research/landing_accessibility/assurance/gate1/lane5_evidence/fixtures/bad_lineage/path_manifest.json", "n_manifests": 1, "n_states": 3, "n_steps": 2, "n_flows": 1, "n_unknown_records": 0, "n_artifacts_checked": 14, "counts_by_kind": {"AFFIRMATIVE_WITHOUT_EVIDENCE": 1, "DISPLAY_NAME_AS_ID": 12, "LINEAGE_BREAK": 1, "MISSING_ARTIFACT": 1, "MISSING_FIELD": 1}, "systemic": true, "verdict": "SYSTEMIC_DEFECT", "path_manifest_autodetected": false, "defects": [
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
  {"kind": "DISPLAY_NAME_AS_ID", "severity": "systemic", "path": "Coupang Mobile App/T07_search_product/run_20260828T000000Z_01/evidence_manifest.jsonl#5", "detail": "service_id='Coupang Mobile App' is not an identifier (whitespace/non-ASCII/equals display_name)"},
  {"kind": "DISPLAY_NAME_AS_ID", "severity": "isolated", "path": "Coupang Mobile App/T07_search_product/run_20260828T000000Z_01/evidence_manifest.jsonl#5", "detail": "flow_observation_id='Coupang Mobile App.T07_search_product.run_20260828T000000Z_01.a1.flow' is not an identifier (whitespace/non-ASCII/equals display_name)"},
  {"kind": "MISSING_FIELD", "severity": "isolated", "path": "Coupang Mobile App/T07_search_product/run_20260828T000000Z_01/evidence_manifest.jsonl#5", "detail": "terminal record (endpoint_status=EVIDENCE_DEFECT) lacks terminal_reason (R11)"},
  {"kind": "AFFIRMATIVE_WITHOUT_EVIDENCE", "severity": "isolated", "path": "Coupang Mobile App/T07_search_product/run_20260828T000000Z_01/evidence_manifest.jsonl#5", "detail": "auth_gate_stage=NONE asserted on endpoint_status=EVIDENCE_DEFECT; must be UNDETERMINED (R13)"},
  {"kind": "LINEAGE_BREAK", "severity": "isolated", "path": "Coupang Mobile App/T07_search_product/run_20260828T000000Z_01/evidence_manifest.jsonl#4", "detail": "state_after_id='Coupang Mobile App.T07_search_product.run_20260828T000000Z_01.a1.S9' does not resolve to any state record"}
]}
```

## What remains once B's real layout is known (field-name mapping only — rules do not change)
- Extend `FIELD_ALIASES` / `ARTIFACT_ALIASES` / `STEP_HASH_FIELDS` at the top of the checker with B's actual names; if B's path manifest
  uses other keys than `runs[].evidence_manifest` / `evidence_manifest_sha256`, add them in `load_path_manifest`.
- Separate state/step/flow files need nothing (records are classified by shape, D3); absolute artifact paths need one rule in D4.
- R11 combination table: B has not published its table; `ALLOWED_TERMINAL` is C's pre-registered one — the single object `gate1/c_terminal_table.py::TERMINAL_ALLOWED` shared with lane6 (OTHER allowed with any non-REACHED status, note mandatory). A differing B table is a finding.
- `FIELD_ALIASES.collector_sha` already accepts `collector_sha256` (T-A-V3-STEP1-015 exact name), `collector_git_sha`, `collector_version_sha`.
