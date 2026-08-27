# lane 4 — GATE 1 SAFETY adapter (C, offline design)

C-side harness plan + skeleton to verify, at B's future exact V3 SHA: (a) exactly-once, (b) forbidden actions,
(c) scope fail-closed across BOTH firewall layers, (d) E001_FULL runner path unchanged.
Nothing here touches production code, a real website, or a B worker worktree. Reads are limited to C's own
harnesses (`../../w1`, `../../w2`, `../../pilot`) and the read-only scratchpad clone `joint10 @ e02eee4`.

## Files
| file | what |
|---|---|
| `GATE1_SAFETY_PLAN.md` | per-item test / inputs / positive+negative control / pass criterion / reuse-vs-adapt; two-layer scope table (today + after T-B-BLK-009); V3-6 failure-injection map; L1-vs-L2 contradictions |
| `two_layer_scope_probe.py` | imports both firewalls, asks each "REAL_TARGET under scope S?" for known/hypothetical/unknown scopes; greps layer 2 for manifest-sha mentions; no network/browser; import errors recorded not raised |
| `two_layer_scope_probe_joint10.json` | probe record at joint10 (SUT e02eee4) — the table in the plan comes from this run |
| `forbidden_action_matrix.json` | C expectation matrix for the 13 guard fixtures (state per control + `never_activate` lists + cross-fixture invariants), derived from the HTML directly |
| `adapter_interface_stub.py` | `run_gate1_safety(sut_root, runner_cmd_template, out_dir)`: S1 dup-launch, S1b lock race, S2 probe, S2b 3-way, S3 E001 blob check; S4 forbidden-action scoring left as a TODO hook. `--dry-run` prints the plan and exits 0 |

## Run
```bash
python3 two_layer_scope_probe.py --repo-root <scratchpad clone> --out probe.json
python3 adapter_interface_stub.py --dry-run
python3 adapter_interface_stub.py --sut-root <clone> --out ./out --ref-sha <E001 baseline sha> --cand-sha <B sha>
```
The stub never collapses steps into one boolean; each step's JSON is the evidence and the plan holds the pass rules.
`score_forbidden_actions` returns SKIPPED (never PASS) until a schema exists — an empty log must not look like a pass.

## Verdict at joint10 today (S2 only; S1/S1b/S2b/S3 were run previously by C at earlier SHAs)
- Unknown / hypothetical scopes (`V3_MAIN50`, `unknown`) and scope-less REAL_TARGET: denied by both layers.
- `V2_DIAGNOSTIC`: layer 1 ALLOW, layer 2 BLOCK (T-B-BLK-009 confirmed). Layer 2 has no manifest-sha literal and no
  import of layer 1. `--check-only` on the pilot driver says GO while `BatchRunner.run` would refuse.
- `E000_FAST`: ALLOW at both layers — flagged to A against 00 §13 (only V2_DIAGNOSTIC REAL is supposed to be open).
- Layer 2's `promoted_main_sha` test is weaker than layer 1's (any 7+ char string vs hex).

## Blocked on B's V3 task-first runner interface
1. `runner_cmd_template` — how to invoke the runner in FIXTURE mode with a frozen `task_id` per target.
2. Output schema — per-candidate state list and action log (event type + target selector) so S4 can score the matrix.
3. Idempotency key shape — whether `task_id` / `task_contract_sha` joins the key (06 §6 "same service-task 재수집 = new run_id");
   C's S1b adaptation depends on it.
4. Dry-run script name/flags for S1 (today `run_e001_batch_dryrun.py --mode FIXTURE`).
5. Whether A's T-B-BLK-009 ruling changes `layer_firewall.py` (then S3's reference blob is re-baselined by ticket).

## Blocked on A
- T-B-BLK-009 ruling (layer 2 scope table + own manifest-sha literal), E000_FAST policy question, V3 main-50 manifest freeze +
  release document (S2b `MANIFEST_REL` / `EXPECTED_SHA` parametrisation waits for it).
