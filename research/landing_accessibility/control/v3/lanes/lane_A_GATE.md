# A-Gate Lane — STEP 1/2/3 게이트 통과조건 명문화 + 현재 충족 현황

지위 `A_PLANE_LANE_ARTIFACT` (판정 아님, 조건 명문화 + 실측 상태 보고)
발행 A-Gate lane · orchestrator exact HEAD `ede241321b5b8599161d95a59bc38034590283e8`
측정 시각 이 세션 실행 시점(`git status` / 파일 실측). 하트비트 자기보고 아님.

**이 문서는 게이트를 통과시키지 않는다.** 조건을 검증 가능한 술어로 쓰고, 그 술어에
현재 무엇이 얼마나 충족돼 있는지 실측한다. `current_status` 는 이 문서가 내리는 판정이
아니라 — 각 게이트의 실제 판정권자(C 또는 A 본체)가 발행한 문서·자기 실측 결과를 그대로
인용한 것이다.

---

## 0. 참조 어휘 정합 — 사전 확인

세 문서가 서로 다른 표현으로 같은 hard-stop 어휘를 쓴다. `V3_0_1_SUCCESSOR_DELTA.md` Δ7 이
정본을 지정한다: **`T-A-V3-P0-001` 의 6종이 정본**이다.

| 정본 (`T-A-V3-P0-001`) | `THREE_TURN_RUNBOOK.md` | `07_MIGRATION_EXECUTION_PLAN_v3.0.md` Stop Conditions |
|---|---|---|
| wrong scope | scope leak | (해당 없음 — manifest/hash mismatch 로 근접) |
| forbidden action | forbidden action | forbidden action attempt |
| evidence overwrite | evidence mutation | evidence identity break |
| duplicate launch | duplicate launch | (해당 없음) |
| task/outcome leakage | task contract drift | task contract change after evidence observation / silent fallback to RF classifier |
| denominator corruption | denominator corruption | denominator mismatch unexplained |
| (없음) | (없음) | manifest/hash mismatch |
| (없음) | (없음) | C hard stop |

본 lane 이 받은 지시문의 HOLD 목록(`scope leak · target outside manifest · duplicate launch ·
evidence overwrite · forbidden credential/transaction · task contract drift · endpoint drift ·
denominator corruption`, 8항목)은 이 정본 6종의 **부분집합 재서술**이지 새 범주가 아니다 —
단, `target outside manifest` 와 `endpoint drift` 두 항목은 정본 6종 중 어디로 접히는지가
문서 어디에도 명시돼 있지 않다. §4 에 A 결정 대기로 등재한다.

---

## 1. 게이트 정의

### G-STEP1-A · MAIN50_FRAME_FROZEN

| 필드 | 내용 |
|---|---|
| preconditions | P0 `V3_CONTRACT_FROZEN` (MET — `P0_COMPLETION_REPORT.md`, 4조건: B/C/D ACK 각1 + C manifest audit CONFIRMED + D negative-control 완결 + A 결정문). Δ1-a(F5 날짜 규칙 선택) · Δ1-b(F1 층 사전등록) · Δ2(replacement 명부 동결) 세 조건이 freeze 이전에 확정돼 있어야 한다(`V3_0_1_SUCCESSOR_DELTA.md` Δ1/Δ2). |
| evidence_required | `FINAL_MAIN50_MANIFEST.json`(target_count=50, task_family_count=5, pilot_5 5건, strata 2축, f5_date_rule, replacement_rule, replacement_reserve 32건, not_verified 4항목) + `FINAL_MAIN50_MANIFEST.sha256.json`(manifest_sha256=필드 제외 본문 해시 `25ce482ddb13269168a0b07c79726c9e1297afc9c7522c125d8b350b3717af1b`, file_sha256=파일 전체 해시 `6500adc38e3048e6f1b59d2d5927b7503a597872a0280126e505ecceb6943eb7`) + source_pack 참조(`SSOTV3/CROSS_SERVICE_TARGET_FRAME_50_v3.0_candidate.json` sha256 `b421988df07feca37ba127f180b2a4c61972113cab5643a6d8985208095bdaef`). |
| who_produces | A (`frozen_by: "A / Authority Plane"`) |
| who_verifies | C — `T-A-V3-STEP1-FREEZE.C` ACK: "push 되면 C 가 manifest_sha256(필드 제외 본문)·file_sha256·registry 50 대조·pilot 5·reserve 32·strata 를 독립 재계산한다." **생산자(A)와 판정자(C)가 다르다 — 정상.** 단 "freeze 할지 말지"의 **결정 자체**는 Director 가 A 전속 권한으로 지정했으므로(3-STEP 재구조: A = Freeze·REAL scope GO·Final claim acceptance) 결정권은 A 단독이고, 그 결정이 만든 **바이트가 맞는지**만 C 가 별개로 검증한다. 이 둘을 섞으면 self-approval 로 오독하기 쉬우므로 분리해 기록한다. |
| same_sha_rule | YES. C 가 재계산하는 sha256 두 값이 A 가 선언한 값과 A 가 지정한 **정확히 그 커밋 SHA**에서 일치해야 한다. |
| pass_predicate | (1) 파일 존재 + `status=FROZEN` (2) manifest_sha256 재계산 일치 (3) file_sha256 재계산 일치 (4) targets 50건이 source_pack registry 와 1:1 대조 불일치 0 (5) pilot_5 5건이 family당 정확히 1개(F1-01/F2-01/F3-01/F4-01/F5-01) (6) replacement_reserve 32건이 family·stratum·rank 스키마 충족 (7) 파일이 git commit 되어 있어 C 가 `git show <SHA>:<path>` 로 감사 가능해야 한다 (8) C 가 위 전부를 CONFIRMED 로 판정. |
| current_status | **PENDING** (자기선언은 있으나 독립검증 트리거 미충족). 근거: A 는 `T-A-V3-STEP1-FREEZE.A_MAIN50_FROZEN.verdict = "MAIN50_FRAME_FROZEN"` 을 이미 선언했고 (1)~(6) 항목의 값 자체는 파일에 전부 채워져 있다(이 세션에서 직접 실측 확인). 그러나 **(7)이 깨져 있다** — `git status --short`(이 세션, control worktree) 결과 `FINAL_MAIN50_MANIFEST.json` 과 `FINAL_MAIN50_MANIFEST.sha256.json` 이 `??`(untracked)다. `T-A-V3-STEP1-FREEZE.C` ACK 도 명시: "FINAL_MAIN50_MANIFEST.json 은 현재 origin control head `ede2413` 트리에 없음." 즉 (8) C 의 독립 재계산이 **아직 실행되지 않았다** — C 는 push 를 기다리는 중이다. |

### G-STEP1-B · B task-first runner offline COMPLETION

| 필드 | 내용 |
|---|---|
| preconditions | G-STEP1-A (최소한 pilot_5 대상 frozen_task/endpoint_contract 가 확정돼 있어야 runner 입력이 성립). P0 `V3_CONTRACT_FROZEN`. |
| evidence_required | B 브랜치(`claude-b/diag-pilot-integration` 계열, 현재 관측 `base_sha 7c5ae70de…`)의 exact head SHA + COMPLETION 티켓(현재 없음, `T-B-V3-STEP1-001` 은 `status: RUNNING` 뿐) + fixture 13종(direct text button·icon+text·AX-named icon-only·unnamed icon-only·hamburger·left/right drawer·bottom sheet·nested menu·task-first auth·login-first auth·modal obstruction·evidence defect) 각각의 offline pass 결과 + Δ6-d 결정론적 경로선택 정책 문서 + 그 문서의 sha256. |
| who_produces | B |
| who_verifies | C (GATE 1) |
| same_sha_rule | YES — `C-FINDING-023725.gate1_method`: "B exact SHA scratchpad clone · C 독립 fixture(B expected output 미참조) · 양방향 대조군." Autonomous transition rule 1·2 항과 동일 패턴. |
| pass_predicate | B 가 COMPLETION 티켓(status=DONE, exact head SHA 명시) 발행 + 13 fixture 카테고리 전부 offline PASS + RF classifier 호출 0 + raw/derived 분리(task_flow_sequence ≠ experienced_flow_sequence, dismissal 이 activation_depth 에 미포함) + 경로선택 정책 문서 sha256 동결 + exactly-once/forbidden-actions 테스트 그린 + `real_target_contact_count = 0`. |
| current_status | **PENDING (진행 중)**. 유일 관련 티켓 `T-B-V3-STEP1-001`(created 02:36:58, base_sha `7c5ae70de…`) 은 `status: RUNNING` 이고 COMPLETION 티켓은 아직 발행되지 않았다. `.agent_worktrees/claude_b_w5a`~`w5g`(02:40~02:44 생성) 가 활성 작업 워크트리로 관측된다. BLOCKED 아님 — 작업 자체가 막혀 있다는 근거는 없다. |

### G-STEP1-C · C GATE 1 offline assurance

| 필드 | 내용 |
|---|---|
| preconditions | G-STEP1-B MET(B COMPLETION, exact SHA 명시). |
| evidence_required | C 독립 fixture + EXPECTATIONS(B 것 미참조), `gate1_check_list` 10항목(RF 미재결정·frozen hash 보존·label/AX 분리·drawer 방향=실제 geometry·sequence lossless·dismissal 분리·auth stage 오판 없음·exactly-once·forbidden·2층 scope fail-closed) 각각의 통과 근거, joint10 선취실행(f9ddb7f+W4+manifest, 픽스처 13 회귀 0·dup 3/3·runner unchanged all_unchanged) 대조군 재사용 기록, 2층 manifest sha256 독립 재확인 결과(1층 결과 미재사용), route 선택 정책 결정론성(동일 fixture 2회 실행 byte-동일 sequence). |
| who_produces | C |
| who_verifies | A — 단, A 는 C 의 기술적 재계산을 다시 계산하지 않는다(T1~T6 위계상 C 가 assurance 층). A 가 확인하는 것은 "C 의 verdict 가 B 와 같은 exact SHA 를 가리키는가" 와 "systemic hard-stop 트리거가 verdict 안에 있는가" 뿐이다 — 재현이 아니라 정합성 대사(reconciliation)다. |
| same_sha_rule | YES(명시). |
| pass_predicate | GATE 1 verdict 문서/티켓 존재 + verdict ∈ {PASS, PASS_WITH_LIMITATIONS} + `gate1_check_list` 10항목 전부에 대한 근거 기재 + B 와 동일 exact SHA 인용 + "검증하지 않은 것" 절 포함(P0 판례 관례, `T-A-V3-P0-001.gate_rule` 이 "각 PASS 문서에 필수"로 못박음) + systemic hard-stop 트리거(§0 6종) 관측 0건. |
| current_status | **BLOCKED** — 대상(G-STEP1-B COMPLETION)이 아직 없다. C 는 하네스만 준비 완료 상태(`C-FINDING-023725.prep_already_in_hand`: joint10 결과 보관, B COMPLETION SHA 도착 시 대조군으로 재실행 예정). C 스스로도 "지금은 B offline runner 완료 대기 + GATE 1 harness 준비" 로 명시. |

### G-STEP1-D · A의 `V3_PILOT_5` REAL release + 명시 GO

| 필드 | 내용 |
|---|---|
| preconditions | G-STEP1-C MET(GATE 1 PASS, B/C 동일 exact SHA). |
| evidence_required | A 가 발행하는 release 문서(예: `V3_PILOT_5_RELEASE.md` 또는 동등 티켓) — `status=RELEASED`, `real_scope_id`, `target_manifest_sha256`(=G-STEP1-A 의 `25ce482d…` 와 동일해야 함), `allowlist_ref`, `task_contract_sha256`(=GATE 1 이 검증한 B exact SHA 의 계약 해시), 명시적 "GO" 문구. layer_firewall 2층에 `V3_PILOT_5` scope 추가 + 그 추가가 manifest_sha256 을 **1층 결과 재사용 없이 독립 재확인**하도록 구현됐는지(`T-A-V3-STEP1-FREEZE.C_BLK_009_ruling.③` 의 연장). |
| who_produces | A |
| who_verifies | **구조적으로 producer = A, 판정도 A.** Director 가 이 GO 를 A 전속 권한(3-STEP 재구조의 "REAL scope GO")으로 명시했으므로 이 자체는 결함이 아니다. 다만 이 게이트의 안전장치는 GO **선언** 자체가 아니라 GO 의 **전제조건**(G-STEP1-C)이 A 아닌 C 가 독립 판정한 것이라는 데 있다. **전제조건 없이(또는 전제조건 SHA 와 다른 SHA 를 바인딩해서) GO 하면 이 게이트는 self-approval 결함이 된다** — 이 경계선을 pass_predicate 에 기계적으로 못박는다. |
| same_sha_rule | YES — release 문서의 `target_manifest_sha256`/`task_contract_sha256` 이 G-STEP1-A manifest 및 G-STEP1-C 가 PASS 판정한 B exact SHA 와 동일해야 한다. |
| pass_predicate | release 문서 `status=RELEASED` + G-STEP1-C verdict 문서의 exact SHA 를 **인용**(재기술이 아니라 인용) + manifest_sha256 일치 + "GO" 라는 명시적 어휘 존재(암묵적 phase 전이로 대체 불가 — Δ7: "phase 자율전이는 REAL release 를 대체하지 않는다") + layer_firewall 2층 `V3_PILOT_5` scope + manifest sha 독립 재확인 로직 존재. |
| current_status | **BLOCKED** — G-STEP1-C 미충족. 현재 `V3_PILOT_5` 는 명시적으로 "미발행"(`FINAL_MAIN50_MANIFEST.json.real_target_allowed = false`, `real_scope_note`: "이 manifest 는 frame 을 동결할 뿐 REAL 실행을 허가하지 않는다"). |

### G-STEP1-E · pilot 5 수집 완료

| 필드 | 내용 |
|---|---|
| preconditions | G-STEP1-D MET(REAL release + 명시 GO). |
| evidence_required | pilot 5 target(F1-01/F2-01/F3-01/F4-01/F5-01) 각각의 raw evidence(22종 측정치: state·candidate controls·selected control·action·URL/DOM/AX before-after·screenshot·bbox·visible_label·accessible_name·obstruction·terminal·endpoint_status 등) + evidence retention manifest + hash chain 항목(각 evidence 파일의 sha256, 수집순서). |
| who_produces | **B** (canonical replay). E 는 producer 가 아니다 — Δ6-c: "E 산출은 endpoint reachability 사전확인·auth gate 위치 사전인지·drawer/reveal 존재확인·obstruction 사전인지로만 한정되고, `E_ROUTE_ID` lineage hint 로만 기록된다. E 의 selector/action sequence 를 B 의 task_flow_sequence 로 기록하는 것은 금지." |
| who_verifies | C |
| same_sha_rule | YES — B 의 pilot 5 COMPLETION exact SHA 와 C 검증이 동일해야 한다. |
| pass_predicate | 5/5 target 에 대해 (a) raw evidence 22종 필드 완전 존재, 또는 (b) endpoint/사이트 사유로 인한 terminal/missing 이 명시적 사유와 함께 보존(표본 교체 아님) + forbidden_actions 위반 0 + retention manifest 에 5건 등재 + exactly-once 위반 0(dup 0) + E route 와 B route 가 갈릴 경우 divergence 가 별도 finding 으로 기록되고 B 것이 `task_flow_sequence` 로 채택됨(Δ6-c ⑤). |
| current_status | **BLOCKED** — 선행 게이트 전부 미충족, REAL 접속 0건. E 는 pilot 5 용 `FAMILY_WORKER_QUEUES.json`(E-F1~E-F5 worker 배정)까지 **준비**를 마쳤으나(`T-E-COMPLETION-001`), `real_target_contact_count = 0` 이고 `next_automatic_action`: "A 의 pilot5 SCOUT_REQUEST 대기" 로 스스로 REAL 미개시를 명시한다. |

### G-STEP1-F · C GATE 2 pilot assurance → STEP 2 자동전이 조건

| 필드 | 내용 |
|---|---|
| preconditions | G-STEP1-E MET. |
| evidence_required | C 의 GATE 2 verdict(같은 exact SHA), pilot 5 각각의 measurement contract 충족 여부 판정, §2 절차에 따른 HOLD/비-HOLD 분류 결과, "검증하지 않은 것" 절. |
| who_produces | C |
| who_verifies | A — `THREE_TURN_RUNBOOK.md` Autonomous transition rule 4조건: (1) B completion 이 exact SHA 명시 (2) C assurance 가 같은 exact SHA 독립검증 (3) A 가 SSOT/contract 일치 확인 (4) hard-stop 없음. |
| same_sha_rule | YES(명시, runbook 조건 1·2). |
| pass_predicate | GATE 2 verdict ∈ {PASS, PASS_WITH_LIMITATIONS} + family 5개 전부 최소 1 evidence 확보(또는 명시적 missing 사유) + systemic hard-stop 트리거(§0) 0건 + A 의 SSOT 일치 확인 + **자동전이가 성립하더라도 이것이 G-STEP2-A(REAL release)를 대체하지 않는다**(Δ7 "phase 자율전이는 REAL release 를 대체하지 않는다" — 이 문구를 pass_predicate 에 직접 새긴다, 자동전이=phase 라벨 전이일 뿐 REAL 개시 아님). |
| current_status | **BLOCKED**. |

### G-STEP2-A · A의 `V3_MAIN50` REAL release

| 필드 | 내용 |
|---|---|
| preconditions | G-STEP1-F MET. **또한** Δ7 규정상 STEP1→STEP2 phase 자동전이가 일어나도 이 게이트는 **A 의 별도 명시 행위**로 남아야 한다 — 자동전이가 이 게이트를 대신 통과시키지 않는다. |
| evidence_required | release 문서(`status=RELEASED`), `target_manifest_sha256`(=G-STEP1-A 의 `25ce482d…`, 50 target 프레임은 이미 동결돼 재사용), `task_contract_sha256`, `allowlist_ref`, layer_firewall 2층에 `V3_MAIN50` scope + manifest sha 독립 재확인 바인딩. |
| who_produces | A |
| who_verifies | G-STEP1-D 와 동일한 self-authority 구조. 안전장치는 전제조건(G-STEP1-F)의 독립성. |
| same_sha_rule | YES — release 가 바인딩하는 manifest_sha256 이 STEP1 에서 동결된 값과 동일해야 한다(재동결 아님). |
| pass_predicate | release 문서 `status=RELEASED` + `real_scope_id = V3_MAIN50` + GATE 2 verdict exact SHA 인용 + "GO" 명시 문구 + replacement_reserve 사용 시 reserve_rank 순서 준수 규칙이 release 문서에 재확인됨. |
| current_status | **BLOCKED**. |

### G-STEP2-B · 45건 수집 완료 + evidence/ledger/retention/hash chain freeze

| 필드 | 내용 |
|---|---|
| preconditions | G-STEP2-A MET. |
| evidence_required | 나머지 45 target(50 − pilot 5) 각각의 raw evidence, retention manifest(pilot 5 포함 전체 50 건 등재), hash chain 무결성, replacement 발생 시 사유+reserve_rank 순서 준수 기록(C 검증), F1 시중7/지방3·F5 ground5/air5 층 기록, f5_date_rule 에 따른 `collection_date_kst`/`query_date`/`dow`/`is_holiday` 기록. |
| who_produces | B |
| who_verifies | C |
| same_sha_rule | YES. |
| pass_predicate | 45개 target 각각 (a) raw evidence 완전 수집 또는 (b) terminal/missing 사유로 명시적 보존(**표본 교체 금지** — runbook partial failure policy: "P5 실행 중 실패한 target 은 표본 교체 금지. 실패/결측 사유로 보존") + retention manifest 전체 50건 등재 + hash chain 불일치 0 + systemic hard-stop 트리거 0건(있으면 freeze 불가, HOLD 로 전환) + freeze 시점 이후 evidence 파일 불변(사후 수정 시 evidence overwrite 로 즉시 hard-stop). |
| current_status | **BLOCKED**. |

### G-STEP3-A · B mart/analysis · D 적대분석 · C GATE 3

| 필드 | 내용 |
|---|---|
| preconditions | G-STEP2-B MET(evidence freeze). |
| evidence_required | B 의 canonical service×frozen-task grain mart(exact SHA, family n=10 유지, 45 pairwise 를 n=45 로 세지 않음) + D 의 적대분석(outcome-independent 로 사전 준비된 5-lane 하네스 실행 결과, exact SHA) + C GATE 3 verdict(final50+mart+analysis 통합) + P0 에서 미해결로 남은 `C↔D 수치 불일치`(`dismiss_control_exists` 단위·모집단·원천필드) 정의 수렴 실증. |
| who_produces | B(mart) / D(적대분석) — 둘 다 producer |
| who_verifies | C — `V3_0_1_SUCCESSOR_DELTA.md` Δ6-e: "D 분석 → C replication → A authority" 구조. D 결과를 C 가 독립 재현하지 않은 채 A 로 직접 broadcast 하지 않는다. |
| same_sha_rule | YES — B mart exact SHA, D 분석 exact SHA 각각에 대해 C 가 같은 SHA 에서 독립 재실행/재현. |
| pass_predicate | GATE 3 verdict = PASS + family n=10 분모 오염 없음 확인(D3-07: 금융 secondary 가 main n 을 늘리지 않음) + P0 open blocker "C↔D 수치 불일치"(`D_INCONCLUSIVE`) 가 GATE 3 이전에 정의 문서화 + 두 독립 구현 수렴으로 해소되거나, 해소되지 않았다면 claim 에서 명시적으로 배제 + D 의 mutation 검출력 주장 등 P0 "미재현 항목"이 재현되었거나 claim 범위에서 제외됨 + D 적대분석이 결과를 가정한 threshold/task/endpoint 변경 없이 수행됐음이 확인(may_prepare 범위 준수). |
| current_status | **BLOCKED**. D 는 현재 outcome-independent 5-lane 하네스만 준비 중(`T-B-V3-STEP1-001.D` ACK: "5 lane 병렬로 준비 중이며 B 의 산출을 기다리지 않는다"). |

### G-STEP3-B · A claim freeze

| 필드 | 내용 |
|---|---|
| preconditions | G-STEP3-A MET(GATE 3 PASS). |
| evidence_required | A 의 claim registry 문서(참고: 다른 lane 이 `lane3_claim_registry_skeleton.json` 을 이미 준비 중 — 본 lane 의 범위 밖이므로 내용은 대조하지 않았다) + 각 claim 의 evidence lineage(어떤 target·어떤 exact SHA) + "검증하지 않은 것"/한계 절. |
| who_produces | A |
| who_verifies | G-STEP1-D/G-STEP2-A 와 동일한 self-authority 구조. 안전장치는 전제조건(GATE 3 PASS)의 독립성. |
| same_sha_rule | YES — claim 이 인용하는 모든 수치가 GATE 3 에서 C 가 검증한 것과 **정확히 같은** exact SHA 의 mart/analysis 에서 나와야 한다. GATE 3 이후 재계산된 수치를 claim 이 쓰면 위반. |
| pass_predicate | claim registry 존재 + 모든 claim 에 evidence lineage(SHA) 명시 + GATE 3 verdict SHA 와 일치 + 한계 절 포함(50 frame 이 7 archetype 중 4개만 커버 · family n=10 이 작음 · F1 endpoint 가 AUTH_GATE 로 끝날 개연성 — `V3_REFREEZE_DECISION.md` §6 세 항목을 최소한 반영) + D3-16 준수(cross-provider 차이를 WCAG 위반으로 판정하지 않음) + A 의 명시적 "FREEZE" 선언. |
| current_status | **BLOCKED**. |

---

## 2. HOLD 판정 절차

Director 가 준 두 목록(즉시 HOLD / HOLD 아님)은 항목 나열이지 **판정 절차**가 아니다.
아래는 그 둘을 구별하는 절차이며, **수치 임계값을 만들지 않는다** — 만들 곳은 §4 에
"A 결정 필요"로 남긴다.

### 2.1 구별의 핵심 질문 — count 가 아니라 "무엇이 깨졌는가"

Director 의 두 목록을 다시 보면 분류축은 **"몇 건이냐"가 아니라 "무엇을 건드렸느냐"** 다.

- **즉시 HOLD(systemic)** 목록 — scope leak · target outside manifest · duplicate launch ·
  evidence overwrite · forbidden credential/transaction · task contract drift · endpoint drift ·
  denominator corruption — 전부 **frozen contract 그 자체**(target manifest 멤버십·task 정의·
  endpoint 정의·evidence 파일 정체성·exactly-once 카운터·금지행동 경계·분모 정의)를 건드린다.
- **HOLD 아님(site-level)** 목록 — timeout · WAF · challenge · public web defect ·
  one-target evidence failure — 전부 **frozen contract 는 그대로 따랐는데 그 사이트가
  무엇을 돌려줬는가**의 문제다.

**Q1 (contract touch test)**: 관측된 이상이 frozen task_id / endpoint_contract / target
manifest 항목 / forbidden_actions 목록 / evidence 파일명·해시 / exactly-once 카운터 중
하나라도 **변경·우회·재해석**했는가?
→ YES 면 systemic HOLD 후보. **건수는 무관하다 — 1건이어도 HOLD 후보다.** matched-comparison
설계는 "50 target 전체가 동일 계약을 따랐다"는 전제 위에 서 있으므로, 계약 위반은 그 target
하나만이 아니라 전체 비교의 타당성을 건드린다.

**Q2 (site response test)**: 이상이 frozen contract 를 정확히 그대로 따른 상태에서
**대상 사이트가 반환한 내용/상태**(응답 없음·차단·인증장벽·공개적 결함)에 국한되는가?
→ YES 면 site-level. 그 target 에 terminal/missing 사유를 기록하고 **표본을 교체하지 않은
채** 계속한다(`THREE_TURN_RUNBOOK.md` partial failure policy: "한 target 의 WAF/timeout/
evidence defect 는 전 프로젝트 hard stop 이 아니다", "한 family 의 non-systemic failure 는
다른 family 실행을 막지 않는다").

### 2.2 누적 건수는 승격 기준이 아니다 — 이미 다른 규칙이 그 자리를 차지한다

"한 target 의 evidence 결손이 몇 건 이상이면 systemic 으로 승격되는가"라는 질문에 대해
Director 는 수치를 주지 않았고, 본 lane 은 수치를 만들지 않는다. 대신 이미 동결된 규칙이
같은 문제를 다른 방식으로 처리한다는 점을 기록한다.

- family 별 replacement 명부가 소진되면 **`n<10` 으로 보고하고 임의 보충하지 않는다**
  (`FINAL_MAIN50_MANIFEST.json.replacement_rule.exhaustion`). 즉 site-level 실패가 아무리
  누적돼도(명부 소진까지) 그 자체는 systemic HOLD 트리거가 **아니다** — 결과는 표본이
  작아지는 것이지 project-wide 정지가 아니다.
- 따라서 "누적 건수"는 승격 신호가 아니라 **"동일한 원인이 몇 개의 독립 target 에
  반복되는가"** 를 봐야 한다. N 개의 서로 다른 벤더 인프라가 각자 독립적으로 WAF 를
  발동하면 그것은 N 건의 site-level 사건이다. 반면 **B/E 의 runner·수집기 코드 한 곳**이
  변경돼 여러 target 에서 동일 증상이 나타나면, 그것은 target 수와 무관하게 **1건의
  systemic contract drift**다 — 원인의 위치(사이트 쪽이냐 수집기 쪽이냐)가 분류축이지
  증상의 개수가 아니다.
- "같은 원인인지"를 확인하는 것은 그 자체로 forensic 작업이며 C(또는 D 지원)의 몫이다.
  본 lane 은 그 확인에 필요한 **판정 절차**만 명시할 뿐, "몇 건이면 같은 원인으로 추정한다"
  같은 수치 지름길은 만들지 않는다.

### 2.3 에스컬레이션 사다리 — 3단

1. **site-level (Q2=YES)**: 관측자(B 또는 E)가 terminal/missing 사유와 함께 기록하고 계속
   진행한다. HOLD 아님. C 에게는 정보성으로만 전달(per-target FINDING 발행 불필요 —
   `C-FINDING-023725.effect_on_P1`: "systemic hard-stop 트리거 관측 시에는 즉시 발행 —
   이것은 gate 와 무관"의 반대해석).
2. **systemic HOLD 후보 (Q1=YES)**: C 가 분류하고 즉시 A 에게 HOLD 티켓을 올린다. 해당
   scope(해당 target 만이 아니라 계약이 걸린 범위 전체)의 실행이 A 판정까지 정지한다.
   판정자는 B(생산자)가 아니라 C — producer≠reviewer 원칙 그대로.
3. **분류 불능 (Q1/Q2 모두 애매)**: 예 — "frozen route 가 실패해서 runner 가 다른 경로를
   시도했다. 이것이 endpoint drift(계약 우회)인가 아니면 그 사이트의 정상적 다중경로
   구조를 반영한 것인가?" 같은 경계 사례. 이 경우 **C 는 스스로 systemic 도 site-level 도
   선언하지 않는다.** `UNRESOLVED_CLASSIFICATION` 으로 A 에 에스컬레이션하되, 기본 자세는
   "해당 target 만 일시정지, 나머지 target 계속"(partial failure policy 의 기본값 방향과
   동일 — 분류가 안 된다고 project 전체를 세우지 않는다). A 가 분류를 확정한 뒤 계속 여부를
   정한다.

### 2.4 Director interrupt 와의 관계 — 별개 층

systemic HOLD(2단)와 `THREE_TURN_RUNBOOK.md` 의 Director interrupt 3조건(construct/family/
endpoint 실체 변경 필요 · REAL scope 사전등록 범위 밖 확대 · evidence overwrite/history
rewrite/credential·transaction 등 비가역·금지 행동 필요)은 **다른 층**이다. HOLD 는 A 선에서
판정·해소 가능한 사건이고, Director interrupt 는 A 권한 밖의 사건이다. systemic HOLD 가
발생했다고 자동으로 Director 에게 올라가지 않는다 — HOLD 해소가 A 권한 안(예: replacement
명부 순서 재확인, 사유 기록)에서 가능하면 A 선에서 닫는다. HOLD 해소 자체가 construct 변경이나
사전등록 범위 밖 확대를 요구할 때만 Director interrupt 로 올라간다.

---

## 3. 의존 DAG

```
P0 V3_CONTRACT_FROZEN  ── MET (P0_COMPLETION_REPORT.md)
        │
        ▼
G-STEP1-A  MAIN50_FRAME_FROZEN ─────────────── PENDING (커밋 대기, §1 참조)
        │
        ▼
G-STEP1-B  B runner offline COMPLETION ─────── PENDING (RUNNING, 진행 중)
        │
        ▼
G-STEP1-C  C GATE 1 offline assurance ──────── BLOCKED
        │
        ▼
G-STEP1-D  A V3_PILOT_5 REAL release + GO ──── BLOCKED  (self-authority, §1 경계 참조)
        │
        ▼
G-STEP1-E  pilot 5 수집 완료 ────────────────── BLOCKED
        │
        ▼
G-STEP1-F  C GATE 2 pilot assurance ─────────── BLOCKED  → (충족 시) STEP 2 phase 자동전이
        │                                                   (자동전이 ≠ REAL 개시, Δ7)
        ▼
G-STEP2-A  A V3_MAIN50 REAL release ────────── BLOCKED  (자동전이와 별개로 A 의 명시 행위)
        │
        ▼
G-STEP2-B  45건 수집 + evidence freeze ──────── BLOCKED
        │
        ▼
G-STEP3-A  B mart/analysis · D 적대분석 · C GATE 3 ── BLOCKED
        │
        ▼
G-STEP3-B  A claim freeze ───────────────────── BLOCKED
```

### E 평면 부재 허용 경로 — 위 DAG 와 분리해서 본다

E 는 위 어떤 화살표에도 **하드 전제조건으로 걸려 있지 않다.** E 의 산출(`ROUTE_WORK_
MANIFEST.json`, `FAMILY_WORKER_QUEUES.json` 등, `T-E-COMPLETION-001`)은 다음 경로로만
소비된다 — 전부 점선(비차단) 관계다.

```
(점선, 비차단)
E bootstrap 산출 ┄┄┄▶ G-STEP1-E 의 "E_ROUTE_ID lineage hint" 로만 참조 가능
                       (Δ6-c: B 는 E route 를 실행 대본으로 재생하지 않는다.
                        B 는 자기 Scout→Freeze→Replay 를 처음부터 수행한다)
```

즉 G-STEP1-B(B runner)·G-STEP1-C(GATE 1)·G-STEP1-D(REAL GO)·G-STEP1-E(pilot 수집) 전부
**E 가 지금 이 순간 사라져도** 그대로 진행 가능하다 — B 의 입력은 frozen `task_id` +
`endpoint_contract` 뿐이고 E 산출은 선택적 사전 힌트일 뿐이다. `T-A-V3-STEP1-FREEZE.D_
STEP1_assignments.E.existence`: "이 티켓이 E 에 닿지 않으면 B/C/D 는 E 없이 진행 가능한
항목을 계속한다 — E 부재가 STEP 1 을 막지 않는다."

**갱신 사실**: 이 lane 조사 시점(이 세션)에 `claude_e_pathfinder` 워크트리와 `claude-e/
pathfinder-v3` 브랜치가 실재하며 `T-E-COMPLETION-001`(P0 bootstrap 완료, `real_target_
contact_count: 0`)을 발행했다 — 티켓 작성 시점(02:42)에 "E 세션 실재 미확인"이었던 상태가
이후(02:44) E 산출물 도착으로 갱신됐다. 다만 이것이 E 를 위 DAG 의 하드 전제조건으로
바꾸지는 않는다 — 여전히 점선이다.

D 도 비슷하게 STEP1/STEP2 critical path 에 하드 전제조건으로 걸려 있지 않다. D 는
outcome-independent 하네스를 지금부터 병렬 준비할 수 있으나(`may_prepare`), D 의 실제
투입은 G-STEP3-A 에서 시작한다 — 그 이전 D 노드는 전부 점선 병렬이다.

---

## 4. A 결정 대기 목록

1. **HOLD 승격 수치 임계값 미정** — "site-level 결손이 몇 건/어떤 패턴이면 systemic 으로
   승격되는가"에 대해 Director 가 수치를 주지 않았고 본 lane 도 만들지 않았다(§2.2). 절차는
   "원인의 위치"로 판정하도록 썼으나, 이것으로 부족하다고 A 가 판단하면 수치 기준을
   A 가 직접 정해야 한다.
2. **`target outside manifest`·`endpoint drift` 두 항목의 정본 매핑 공백** — Δ7 이 준
   대응표(scope leak↔wrong scope · task contract drift↔task/outcome leakage · evidence
   mutation↔evidence overwrite)에 이 둘이 없다(§0). `target outside manifest` 는 `wrong
   scope` 의 특수사례로 접어도 되는지, `endpoint drift` 는 `task/outcome leakage` 로
   접는지 아니면 정본 6종에 7번째로 추가하는지 A 판정 필요.
3. **G-STEP1-A 커밋 공백** — `FINAL_MAIN50_MANIFEST.json`/`.sha256.json` 이 control
   worktree 에 untracked 상태로 남아 있다(이 세션 실측). A 가 커밋·push 하지 않는 한
   C 의 "push 되면 독립 재계산한다"는 조건이 영구히 트리거되지 않고, G-STEP1-A 는
   구조상 PENDING 에서 벗어날 수 없다 — 판정이 아니라 사실 보고다.
4. **self-authority 게이트(G-STEP1-D·G-STEP2-A·G-STEP3-B)의 release 문서 템플릿 강제
   여부** — 세 게이트 모두 "전제조건 게이트의 exact SHA 를 인용해야 한다"는 원칙은 있으나,
   이를 release 문서의 **필수 필드**로 템플릿화해 기계적으로 검사할지(예: 필드 누락 시
   release 자체가 무효)는 A 가 정할 운영 사안이다.
5. **`T-E-FACT_CORRECTION-001` 미결** — E 가 관측: `research/landing-accessibility-main`
   의 실제 tip 이 `32460b87…`(refcohort pilot 커밋)이며 `SSOTV3/08_CURRENT_STATE_BASELINE_
   v3.0.md` 가 기재한 `bc0b7a08…` 와 다르다. "promoted main" 개념을 v3 체제에서 재정의할지,
   포인터를 전진시킬지는 A 판단 필요 — 위 10개 게이트 어디에도 직접 걸려 있지 않지만
   `08 baseline` 문서를 근거로 인용하는 어떤 향후 판정도 이 불일치를 상속한다.

---

## 5. 현재 충족 현황 표

| 게이트 | current_status | 근거 요약 |
|---|---|---|
| G-STEP1-A | PENDING | 값 전부 존재·자기검증 완료. 파일 untracked → C 독립검증 미트리거 |
| G-STEP1-B | PENDING | `T-B-V3-STEP1-001` RUNNING, COMPLETION 미발행 |
| G-STEP1-C | BLOCKED | 대상(B COMPLETION) 부재. 하네스만 준비 |
| G-STEP1-D | BLOCKED | 전제조건(GATE 1) 미충족. `V3_PILOT_5` 미발행 |
| G-STEP1-E | BLOCKED | REAL 접속 누적 0. E 준비만 완료, SCOUT_REQUEST 대기 |
| G-STEP1-F | BLOCKED | 전제조건(pilot 5 수집) 미충족 |
| G-STEP2-A | BLOCKED | 전제조건(GATE 2) 미충족. `V3_MAIN50` 미발행 |
| G-STEP2-B | BLOCKED | 전제조건(REAL release) 미충족 |
| G-STEP3-A | BLOCKED | 전제조건(evidence freeze) 미충족. D 는 하네스 준비만 |
| G-STEP3-B | BLOCKED | 전제조건(GATE 3) 미충족 |

**MET = 0 / 10.** PENDING 2(G-STEP1-A, G-STEP1-B) · BLOCKED 8.
