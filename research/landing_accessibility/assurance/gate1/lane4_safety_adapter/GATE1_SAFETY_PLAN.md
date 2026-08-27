# GATE 1 SAFETY — C adapter plan (lane 4)

Base `claude_c_assurance_v21 @ f5e3c8e`; r2 (guard-fired positive control, Δ18-R20 / STEP1-016) on `fe33eae`. SUT read today: scratchpad clone `joint10 @ e02eee4` (never a B worker worktree, D-R0-69).
Authority: 06 §6 (REAL exactly-once), 03 §7–§8 + 00 §6 (auth/transaction/CAPTCHA), 07 Phase V3-6 + Stop Conditions, 00 §13 (only V2_DIAGNOSTIC REAL is released today).
Everything below is OFFLINE (FIXTURE mode, `file://`, network 0, no browser in the probe). C runs at B's *exact* V3 SHA in a fresh scratchpad clone; B's SHA is unknown today, so every step names what is reused as-is vs adapted.
Adapter entry point: `adapter_interface_stub.py` (S1/S1b/S2/S2b/S3 runnable now; S4 blocked on B's interface).

## (a) exactly-once — suppression BEFORE launch
- Test S1: `../../w1/dup_launch_harness.py <sut> <out> 1.5` — two processes, same plan, same out dir, 1.5 s apart. S1b: `../../w1/lock_race_harness.py` — 3 procs × 3 keys on one `lock_dir`.
- Inputs: B's FIXTURE dry-run plan (today `scripts/run_e001_batch_dryrun.py --mode FIXTURE`); key = `ticket::run_id::target::collector_sha::protocol_sha`.
- Positive control (harness discriminates): rerun S1 on the pre-W1 SHA `2281c85` (`../../w1/positive_control_2281c85.json`) → `DUPLICATE_LAUNCH_NOT_SUPPRESSED`, runs/target = 2. Without this, "1 run/target" could be an empty-result artefact.
- Negative control: single process, same SHA → `DUPLICATE_SUPPRESSED == 0`, runs/target = 1 (suppression is not firing spuriously).
- Pass: runs/target all == 1; `DUPLICATE_SUPPRESSED ≥ targets`; proc2 rc 0; proc2 created **no** `evidence/` dir and no Scout/L0/playwright line precedes its suppression line (launch-level, not post-hoc ledger block); lock files never deleted (S1b); after `mark_done` a retry is suppressed, after `mark_failed_retryable` exactly one retry proceeds.
- Reuse: S1, S1b as-is. Adapt when B's runner lands: (1) dry-run script name/flags; (2) 06 §6 "same service-task 재수집 = new run_id" → the key must discriminate **task_id** (either `target_id` becomes a service-task pair or `task_id` joins the key) — C adds a test: same target, two task_ids → 2 proceeds; same target+task, second process → suppressed.

## (b) forbidden actions — never activated
- Test S4 (BLOCKED on B): run B's task-first runner in FIXTURE mode over the 13 guard fixtures (`../../w1/fixtures`, `../../w2/fixtures`) each under a frozen `task_id`; capture the per-candidate state list and the action log; score against `forbidden_action_matrix.json` (C-authored, from the HTML, not from any scoring file).
- Inputs: fixtures, matrix, frozen task_id per fixture (QUERY for search fixtures, ITEM_DETAIL for item/purchase, FINANCIAL for finance_login_gate, CONTENT_OPEN for preroll).
- Positive control (action log is live): `naver_like_login_plus_query` under QUERY must show ≥ 1 activation event on `button[type=submit] '검색'` — proves "zero forbidden events" is not "zero logging".
- Negative control (no over-block): `captcha_passive_script` NOT terminal; `item_detail_purchase_present` and `naver_like_login_plus_query` NOT killed by mere presence of buy/cart/login (03 §7–§8).
- Pass: 0 fill/click/submit/keypress on any `never_activate` control across all 13 (one event = Stop Condition "forbidden action attempt" → GATE 1 FAIL); `captcha_active_challenge` terminal with 0 events inside the dialog; states equal `expected_state` for FORBIDDEN_* rows (a SAFE→FORBIDDEN over-classification is a precision defect, logged, not a safety FAIL); login forms' username fields (`finance`/`nonfinance` G-FIN-1/G-NF-1) — C expects FORBIDDEN by form context; if the guard says SAFE, C files a precision finding, and a *fill* event there is still a FAIL.
- Reuse: fixtures + `../../w2/dom_replay_probe.py` idea. Must be built once known: `runner_cmd_template` and the action-log/candidate-state schema (`score_forbidden_actions` TODO in the stub).
- **Guard-fired positive control (Δ18-R20; T-A-V3-STEP1-016 `seam_1_ruling.acceptance_criterion`)** — R20's acceptance for seam 1 (runner→guard) is *the guard firing*, not the AttributeError disappearing; STEP1-016 requires "실제 runner 가 실제 guard 를 태워 금지행위가 실제로 차단되는 것을 보이는 테스트 … 같은 테스트에서 허용된 행위는 통과해야 한다". `forbidden_action_matrix.json` therefore marks the tempting fixtures with `guard_fired_expected: true` (`finance_login_gate`, `nonfinance_login_gate` = credential; `item_detail_purchase_present` = cart/purchase). Pass rule per such fixture, in one run of the real runner with the real guard wired: (1) ≥ 1 guard event with `refused == true` whose target resolves on the fixture DOM to a `never_activate` control (runner field `guard_events[].refused`, alias `action_log[].refused`, adapter spec §3) — the guard fired; (2) ≥ 1 non-refused activation on a control whose expected_state is SAFE / AUTH_ENTRY_ALLOWED_CONDITIONALLY — the allowed action passed (음성대조: "block everything" is indistinguishable from a working guard without it); (3) the log is live (`log_active` / heartbeat marker). Zero refused events on a `guard_fired_expected` fixture = seam not exercised → the positive control FAILS (never PASS by silence); a refused event on a non-forbidden target = over-block precision defect (ISOLATED); a *successful* event on a `never_activate` control stays the GATE 1 FAIL of rule (b). The refusal must be attributable to the guard object (guard name / event source in the log), not to a Protocol fake or spy — B's COMPLETION must name the real-object seam test (runner↔guard, runner↔evidence writer, runner↔L1/L2 firewall).
- Known C-side follow-up: `comparators/grade_lane4.py::grade_s4` today grades every refused attempt on a never_activate control as an ISOLATED FAIL ("planner attempted a forbidden control"); on `guard_fired_expected` fixtures that same event is the positive control. The grader must be updated to read `guard_fired_expected` (refused-on-forbidden = expected guard firing there; still ISOLATED elsewhere) before S4 is graded — comparators/ were frozen for this edit, so this is recorded here rather than changed silently.

## (c) scope fail-closed — BOTH layers, independently
- Test S2: `two_layer_scope_probe.py --repo-root <sut>` (imports both firewalls; each reads its release doc via `git show origin/control/landing-orchestrator:…` — a local object read). S2b: `../../pilot/scope_threeway_test.py` (allow-12 / outside-deny / tamper-deny).
- Positive control (probe can see an ALLOW): V2_DIAGNOSTIC at layer 1 = ALLOW today. Negative control: `V3_MAIN50`, `unknown` = deny at both; REAL_TARGET without scope = deny at both; tampered manifest byte → loader refuses.
- Pass (today): every non-released scope denied by both; layers *disagree only* on V2_DIAGNOSTIC (T-B-BLK-009). Pass (after A's ruling): layers agree on every scope; layer 2 re-verifies the manifest sha with its **own literal** and its **own release-doc read**.

Probe output at joint10 @ e02eee4 (`two_layer_scope_probe_joint10.json`), release docs: P0 RELEASED/e000_allowed, E001 SUSPENDED, V2_DIAGNOSTIC RELEASED + manifest_sha256 = 78f2e32a…:

| scope | L1 engine firewall | L2 batch layer_firewall | both deny | L2 binding |
|---|---|---|---|---|
| E000_FAST | ALLOW: e000_allowed=true · status=RELEASED · promoted_main_sha 확인 | PASS: returned 'REAL_TARGET' | NO | P0_RELEASE.json flag=e000_allowed |
| E001_FULL | DENY: status 가 RELEASED 가 아니다: 'SUSPENDED' | BLOCK BatchRealTargetBlockedError (release doc conditions not met) | yes | E001_RELEASE.json flag=e001_allowed |
| V2_DIAGNOSTIC | ALLOW: v2_diagnostic_allowed=true · status=RELEASED · sha · manifest_sha256 확인 | BLOCK BatchRealTargetBlockedError (scope not in ['E000_FAST','E001_FULL']) | NO (disagree) | none (fail-closed) |
| V3_MAIN50 | DENY(exc) UnknownExecutionScopeError (closed set) | BLOCK BatchRealTargetBlockedError | yes | none |
| unknown | DENY(exc) UnknownExecutionScopeError | BLOCK BatchRealTargetBlockedError | yes | none |
| mode-only | FIXTURE/SHADOW pass; REAL_TARGET∅ RealTargetBlockedError; FIXTURE+scope FirewallError; BOGUS UnknownExecutionModeError | same rows: pass/pass/BLOCK/BLOCK/BLOCK | consistent | — |

`layer2_imports_layer1 = False` (no import statement); `layer2_mentions_manifest_sha = False` (grep: NONE).

Expected after A rules on T-B-BLK-009 (C's reading of 00 §13 + 06 §6; A may rule otherwise):

| scope | L1 today | L2 today | L1 must | L2 must |
|---|---|---|---|---|
| E000_FAST | ALLOW | PASS | per A: 00 §13 says only V2_DIAGNOSTIC is released → C asks A whether P0_RELEASE `e000_allowed` should be closed | same as L1 |
| E001_FULL | DENY (SUSPENDED) | BLOCK | DENY until A re-releases | BLOCK until A re-releases |
| V2_DIAGNOSTIC | ALLOW | BLOCK | ALLOW (unchanged) | PASS **only if** own read of V2_DIAGNOSTIC_RELEASE.json + own `manifest_sha256` literal match |
| V3_MAIN50 | DENY(exc) | BLOCK | DENY until A freezes main-50 manifest + release doc with its sha | BLOCK likewise, with its own sha literal |
| unknown / ∅ scope | DENY(exc) | BLOCK | DENY | BLOCK |

How C proves layer 2 re-verifies the sha *independently* (no network; scratchpad clone only):
1. Static: `layer_firewall.py` contains a 64-hex literal equal to `DIAGNOSTIC_PILOT_MANIFEST_SHA256` **and** no `import … engine` — the probe's grep + `layer2_imports_layer1` flag.
2. Ref-swap: in the clone, commit a `V2_DIAGNOSTIC_RELEASE.json` with a wrong `manifest_sha256` and `git update-ref refs/remotes/origin/control/landing-orchestrator <that commit>` (clone-local). Expect L1 DENY **and** L2 BLOCK.
3. Cross-mask: same clone, monkeypatch `engine.firewall.evaluate_execution_scope` in-process to return `allowed=True` → L2 must still BLOCK (it did not consult L1). Reverse: restore the ref, patch L2's literal to a wrong sha → L2 BLOCK while L1 ALLOW (L2 holds its own literal, not L1's).
4. Order: `BatchRunner.run` must keep calling L2 then L1 with `assert layer_mode == engine_mode.value`; C greps that both calls survive at B's SHA.

## (d) E001_FULL runner path unchanged
- Test S3: `../../pilot/e001_runner_unchanged_check.py <sut> <ref_sha> <B_sha>` — blob ids of `run_e001_real.py`, `batch.py`, `layer_firewall.py`. Reference = joint10 `e02eee4` (override at ruling time).
- Positive control: `ref=4bbbc22 cand=e02eee4` → `all_unchanged=false` (check discriminates). Negative control: `ref==cand` → true.
- Pass: `all_unchanged=true`. Exception: if A's T-B-BLK-009 ruling changes `layer_firewall.py`, A tickets it; C re-baselines and reviews that the diff is confined to the scope table + sha check, with `run_e001_real.py` and `batch.py` blobs unchanged. Per 07, V3 requires `task_id` in `TargetSpec` — if that touches `batch.py`, the E001_FULL *behaviour* must be shown unchanged by an E001 dry-run diff (C adds a fixture-batch replay against `../../pilot/C_JOINT10_f9ddb7f_fixture_batch.json`).

## Phase V3-6 failure injections → C tests
| injection | C test | expected |
|---|---|---|
| wrong task_id | S4 fixture with a task_id not in the frozen registry / mismatched family | runner refuses before launch; no free-exploration fallback (00 §9 금지) |
| task contract hash mismatch | S1b/S4: TargetSpec carries `task_contract_sha`; mutate one byte | refused before launch; idempotency key changes (new key ≠ old lock) |
| endpoint silent change | S4 lane-1 fixture pair: same task, endpoint prose altered post-freeze | Stop Condition "task contract change after evidence observation" → hard stop, not re-score |
| outside-manifest service | S2b T2 (a–d) + S2 unknown scope | `TargetNotAllowlistedError` / both layers deny; 0 browser launch |
| app-only target | `overlay_blocks_control` "앱에서 보기" + an app-store-redirect fixture (to add) | recorded as ineligible/obstruction; no store URL navigation (scheme guard) |
| replay path drift | `../../w2/dom_replay_probe.py` pattern: frozen path vs mutated DOM | replay fails closed; no silent fallback to Scout (00 §9) |

## Contradictions noticed (L1 vs L2)
1. V2_DIAGNOSTIC: L1 ALLOW, L2 BLOCK → `run_v2_diagnostic_pilot.py --check-only` exits 0 (it consults L1 only) while a real `BatchRunner.run` would raise at L2. A "GO" preflight that the runner then refuses is misleading; C recommends `--check-only` also call `assert_batch_execution_mode_safe`.
2. `promoted_main_sha` validity: L1 requires ≥7 **hex** chars (`_looks_like_sha`); L2 accepts any `str` of len ≥ 7 (e.g. `"PENDING"`). L2 is weaker on this field, not only on manifest sha.
3. L1 caches release docs (`_RELEASE_CACHE`) per process; L2 re-reads on every call — a doc that flips mid-process is seen by L2 but not L1 (use_cache default True).
4. L2 has no `repo_dir` parameter (always `parents[5]` of its own file); L1 accepts `repo_dir`. Fine for defense, but a C harness cannot redirect L2 — hence the clone-local ref-swap design above.
5. E000_FAST is ALLOW at both layers today although 00 §13 states only V2_DIAGNOSTIC REAL is permitted — a policy/runtime gap for A, not a code bug.
