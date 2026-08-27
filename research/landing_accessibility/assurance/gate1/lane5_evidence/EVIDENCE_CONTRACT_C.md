# EVIDENCE_CONTRACT_C — C's independent evidence completeness & lineage contract (V3, GATE 1 → 2/3)

Authority: SSOTV3 `03_COLLECTION_MEASUREMENT_SPEC_v3.0.md` §10, `02_DATA_SCHEMA_v3.0.md` §3–§4 and §8,
`06_ABCD_ORCHESTRATION_PROTOCOL_v3.0.md` §6; ticket `T-A-V3-STEP1-007` R11 (terminal_reason) / R13 (auth_gate_stage UNDETERMINED);
`04_FLOW_CODEBOOK_v3.0.md` for the `endpoint_status` enum. Derived by C from those texts only; B's code/marts were not read.
Checked from raw files only by `evidence_lineage_check.py`. Base: `5e05da9`.

## 1. Identity (02 §8, 06 §6)
- Observation identity = `service_id + task_id + run_id` (the **identity spine**). State identity = spine + `attempt_id` + `state_index`.
- `observation_id` (state) and `flow_observation_id` (flow) are globally unique opaque ids.
- Ids are identifiers, not display names: ASCII `[A-Za-z0-9][A-Za-z0-9_.-:]*`, no whitespace, never equal to a `display_name` field.
- Re-collection of the same service×task = **new `run_id`** (new directory). Existing evidence is never rewritten.

## 2. Per-STATE package (03 §10; 02 §3 "manifest pointers")  — states `S0..Sn`
Required artifact files, each referenced from the manifest with `path` + `sha256`:

| kind | content (03 §10) |
|---|---|
| `dom` | DOM snapshot |
| `ax` | accessibility tree |
| `screenshot` | viewport screenshot |
| `probe` | probe / CSS geometry |
| `control_facts` | selected control facts |

Required manifest fields per state record: `observation_id, service_id, task_id, run_id, attempt_id, state_index (S<n>),
url, captured_at (ISO-8601), collector_sha (accepted source names: collector_sha, collector_sha256 [T-A-V3-STEP1-015 exact name], collector_git_sha, collector_version_sha), protocol_sha, task_contract_sha256, endpoint_contract_sha256, artifacts{kind:{path,sha256}}`.

## 3. Per-STEP record (02 §4 `fact_flow_step`)
Required fields: `flow_observation_id, service_id, task_id, run_id, attempt_id, step_index, action_token,
state_before_id, state_after_id, url_before, url_after, captured_at, collector_sha, protocol_sha,
task_contract_sha256, endpoint_contract_sha256, {dom,ax,screenshot}_sha256_{before,after}`.
Lineage: `state_before_id`/`state_after_id` MUST resolve to state records of the same spine; `url_before/after`
MUST equal the referenced state's `url`; the six step hashes MUST equal the referenced states' manifest hashes.

## 3b. Per-RUN flow observation = terminal record (02 §4 `fact_flow_observation`; R11/R13) — exactly one per run×attempt
Required: `flow_observation_id, service_id, task_id, run_id, attempt_id, endpoint_status, terminal_reason, auth_gate_stage,
captured_at, collector_sha, protocol_sha, task_contract_sha256, endpoint_contract_sha256`; `terminal_note` required iff `terminal_reason=OTHER`.
`endpoint_status` ∈ {REACHED, AUTH_GATE, PUBLIC_WEB_UNOBSERVABLE, APP_REQUIRED, EVIDENCE_DEFECT, BLOCKED, ABSTAIN} (unchanged, R11); `terminal_reason` ∈ 13 values {TIMEOUT, WAF_BLOCK, ACTIVE_CHALLENGE, NO_PUBLIC_MOBILE_WEB, TASK_SURFACE_ABSENT, APP_REQUIRED,
CONTROL_DISABLED_OR_INERT, FORBIDDEN_ACTION_REQUIRED, AUTH_REQUIRED, EVIDENCE_DEFECT, REPLAY_BROKEN, AMBIGUOUS_MULTIPLE_CANDIDATES, OTHER}.
`auth_gate_stage` ∈ {NONE, BEFORE_TASK_DISCOVERY, AFTER_TASK_SELECT, AT_ENDPOINT, UNDETERMINED}; NONE = "observed, no gate" (affirmative).
Allowed `endpoint_status × terminal_reason` (C's pre-registered table, single source `gate1/c_terminal_table.py` shared with lane6; **OTHER allowed with
any non-REACHED status and always requires a non-empty `terminal_note`** — unified across lane5/lane6 on 2026-08-28):
REACHED→∅ (must be null; REACHED×OTHER impossible) · AUTH_GATE→AUTH_REQUIRED|OTHER · PUBLIC_WEB_UNOBSERVABLE→NO_PUBLIC_MOBILE_WEB|TASK_SURFACE_ABSENT|OTHER ·
APP_REQUIRED→APP_REQUIRED|OTHER · EVIDENCE_DEFECT→EVIDENCE_DEFECT|REPLAY_BROKEN|OTHER · BLOCKED→WAF_BLOCK|ACTIVE_CHALLENGE|TIMEOUT|CONTROL_DISABLED_OR_INERT|FORBIDDEN_ACTION_REQUIRED|OTHER ·
ABSTAIN→AMBIGUOUS_MULTIPLE_CANDIDATES|OTHER. The table is a C proposal to be compared with B's runner schema at GATE 1 (R11); a differing B table is a finding, not a C edit.
Consistency: `AUTH_GATE` requires `auth_gate_stage` ∉ {NONE, UNDETERMINED}; `EVIDENCE_DEFECT`/`ABSTAIN` with `auth_gate_stage=NONE` is an affirmative claim without evidence.

## 4. Hash chain (02 §8 "path manifest ↔ evidence manifest linked by hash"; 03 §10 "manifest SHA")
- Evidence manifest lists sha256 of **every** artifact it references (level 1).
- Path manifest (`path_manifest.json`, `runs[]`) references each evidence manifest by `evidence_manifest` path +
  `evidence_manifest_sha256` (level 2). Without a path manifest, a sidecar `<manifest>.sha256` is required.
- Step hashes re-state the state hashes (level 1′), so a step cannot silently point to a different capture.

## 5. Append-only rule (02 §8, 06 §6)
- Identical artifact paths are never rewritten. Detection: manifest sha256 ≠ recomputed sha256 **and** artifact mtime is later
  than the manifest mtime or than the record's `captured_at` (+1 s tolerance) ⇒ overwrite.
- Same state identity declared twice with different hashes ⇒ overwrite (in-place re-collection). Same spine under two directories, or the
  same `observation_id`/state/step/flow identity twice ⇒ identity collision.

## 6. Defect catalogue (fixed; severities are part of the contract)

| kind | meaning | severity |
|---|---|---|
| `OVERWRITE_DETECTED` | artifact or identity rewritten after seal (§5) | **systemic** (hard-stop) |
| `IDENTITY_COLLISION` | identity declared twice / spine in two dirs | **systemic** (hard-stop) |
| `MANIFEST_SHA_UNBOUND` | evidence manifest not bound by hash (level 2), or bound hash ≠ actual | **systemic** (hard-stop); per-artifact missing sha ⇒ isolated |
| `DISPLAY_NAME_AS_ID` | display name / non-identifier used as an id | **systemic** when in `service_id/task_id/run_id` (whole run's identity is not an id); isolated in `observation_id/attempt_id/flow_observation_id` |
| `HASH_MISMATCH` | artifact sha ≠ manifest sha (no seal-after evidence), or step hash ≠ state hash | isolated |
| `MISSING_ARTIFACT` | required artifact not referenced or not on disk; no manifest found | isolated |
| `LINEAGE_BREAK` | step references a non-existent state / other spine / url discontinuity | isolated |
| `MISSING_FIELD` | required field absent (incl. terminal record without `terminal_reason`, run without flow record), malformed digest/timestamp/state_index | isolated (C addition, see §7) |
| `SCHEMA_VIOLATION` | value outside enum; `OTHER` without note; combination outside §3b table (e.g. REACHED×non-null); AUTH_GATE×NONE/UNDETERMINED | isolated (R11) |
| `AFFIRMATIVE_WITHOUT_EVIDENCE` | `auth_gate_stage=NONE` on `endpoint_status` ∈ {EVIDENCE_DEFECT, ABSTAIN} — absence of evidence recorded as evidence of absence | isolated (R13) |

Verdict: no defects ⇒ `COMPLETE`; only isolated ⇒ `COMPLETE_WITH_ISOLATED_DEFECTS`; any systemic ⇒ `SYSTEMIC_DEFECT`. Exit 0 only when no
systemic defect; isolated defects are still reported for per-observation exclusion at GATE 2/3.

## 7. Ambiguities in SSOTV3 resolved by C (pre-registered)
1. 03 §10 lists artifacts but not manifest fields. `attempt_id, collector_sha, protocol_sha, task_contract_sha256,
   endpoint_contract_sha256, captured_at` are required by C's lane brief; C treats them as required (lineage cannot be
   audited without them). `attempt_id` is added to state identity (02 §8 names only the spine).
2. "manifest SHA" (03 §10) is read as: the evidence manifest is itself hashed and that hash is bound by the path manifest
   (02 §8). No sha inside the manifest of itself (circular). Sidecar `.sha256` is the fallback binding.
3. `DISPLAY_NAME_AS_ID` on a spine field is classified systemic although the brief listed it as isolated: a display name
   in `service_id/task_id/run_id` invalidates the identity of every record of that run, which is a run-level failure.
4. `MISSING_FIELD` is added as an eighth kind; folding missing fields into `MISSING_ARTIFACT` would hide the distinction.
5. Overwrite needs both hash mismatch and a later mtime/captured_at; hash mismatch alone (e.g. wrong manifest) stays isolated.
6. URL continuity (`url_before == state.url`) is enforced exactly (no normalisation); relax only by explicit decision.
7. R11 says B specifies the combination table and C verifies it; B's table is not yet published, so §3b is C's table, pre-registered.
   If B's table differs, the diff is a finding, not a silent merge. "Terminal record" = the flow record of every run, REACHED included
   (REACHED carries `terminal_reason: null`). `terminal_reason` missing is MISSING_FIELD only for non-REACHED statuses.
