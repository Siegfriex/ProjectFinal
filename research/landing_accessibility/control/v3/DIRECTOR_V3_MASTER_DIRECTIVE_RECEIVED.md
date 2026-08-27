# DIRECTOR → A · V3 Master Directive + START INJECTION (원문 접수 기록)

접수 A · 2026-08-28T02:0x KST · 전달 방식 **대화 직접 주입** (파일 아님)

Director 는 `directives/DIRECTOR_TO_A_START.md` · `00_MASTER_DIRECTIVE.md` · `phases/P0…P7` 을 지목했으나
해당 경로는 저장소에 **실재하지 않는다** (검증: `V3_CURRENT_STATE_RECONCILIATION.md` §4).
A 는 주입된 본문을 권위 원문으로 접수하고 아래에 원문 그대로 보존한다.
A 는 존재하지 않는 파일을 SSOTV3 안에 만들어 채우지 않는다 — 팩이 Director 가 준 bytes 임을 유지하기 위함이다.

---

## 원문 1 — ProjectFinal V3 Director Orchestration Master Directive

Issued for: ProjectFinal / SSOTV3 Cross-Service Task Entry Flow pivot

Director intent: 기존 A/B/C/D의 방법론·검증 규율·버스·exact-SHA·producer/reviewer separation을 보존하되,
연구 critical path를 Representative Function auto-classification에서
deterministically frozen task → observed cross-service flow로 전환한다.

### 0. 현재 exact remote heads (Director 기재)

| Plane | Branch | Exact SHA |
|---|---|---|
| A | control/landing-orchestrator | 5c22faebaeb6699049fc9af5646f8b492b6a4068 |
| B | claude-b/diag-pilot-integration | 01041bc213a2e61f6cb224e469087d9a11324349 |
| C | claude-c/assurance-v21 | 52df8a6426119ada709e11a249aa19ef8fe63b4f |
| D | claude-d/research-sandbox-v21 | 8fafa0a44d98fc1c3c9efb95997e4bd7edbda666 |
| promoted main | research/landing-accessibility-main | bc0b7a087faf2328cbafdfa9b40bd426c5080d7d |
| pilot manifest | control/pilot-manifest | 54a0c7a4149adc17c086e398be83bc7c117a66b0 |

Branch name만으로 완료를 선언하지 않는다. 매 gate는 B completion, C assurance, A authority decision이
같은 exact target SHA / manifest hash를 가리켜야 한다.

### 1. V3에서 바뀌는 것 / 안 바뀌는 것

V3 primary construct는 Cross-Service Task Entry Flow Divergence.
해석은 Structural Transfer Friction Proxy이며 actual cognitive load나 actual transfer effect가 아니다.

- Task-first: task family와 endpoint contract는 화면 관측 전에 동결한다.
- Flow-first: ordered Action Sequence가 원자료이며 NED/IED/MPFED·activation depth는 파생 scalar다.
- 기존 7 archetype은 삭제하지 않고 legacy metadata/codebook으로 보존하지만
  RF 7-way classifier는 V3 main critical path dependency가 아니다.
  W2 FAIL은 철회하지 않고 V2_RETIRED_PATH의 유효한 역사적 결과로 남긴다.

보존: A/B/C/D plane separation, T1~T6 truth hierarchy, immutable ticket, FACT_CORRECTION/SUPERSEDE,
exactly-once, fail-closed firewall, approval↔manifest hash binding, producer≠reviewer, C hard-stop,
D→C routing, result-blind preregistration, artifact retention manifest.

### 2. 큰 Phase

| Phase | 이름 | 목적 | REAL scope | Exit gate |
|---|---|---|---|---|
| P0 | V3_CONTRACT_REFREEZE | SSOTV3 candidate bytes·방법론·권위 전환을 먼저 잠금 | NO_REAL | V3_CONTRACT_FROZEN |
| P1 | Q12_METHOD_QUALIFICATION | 기존 12건 diagnostic runner를 안전하게 배선·실행해 측정기 qualification 종결 | V2_DIAGNOSTIC_12_ONLY | METHOD_QUALIFIED |
| P2 | MAIN50_FRAME_FREEZE | 50개 candidate의 mobile-web eligibility와 task/endpoint 동형성 검증 후 final frame 동결 | ELIGIBILITY_PRECHECK_ONLY | MAIN50_FRAME_FROZEN |
| P3 | FLOW_ENGINE_QUALIFICATION | Task-first Flow engine·schema·normalizer를 offline fixture에서 검증 | NO_REAL | FLOW_ENGINE_QUALIFIED_OFFLINE |
| P4 | V3_MATCHED_PILOT | family별 2개=10개 matched-task real pilot로 새 Flow 계측을 검증 | V3_FLOW_PILOT_10_ONLY | V3_FLOW_METHOD_ACCEPTED |
| P5 | MAIN50_COLLECTION | 동결된 50 service-task를 exactly-once로 수집·evidence freeze | V3_MAIN50_ONLY | MAIN50_EVIDENCE_FROZEN |
| P6 | MART_ANALYSIS_ASSURANCE | service-task grain mart·Flow/STFP 다축 분석·C 독립 replay·D 보조 EDA | NO_NEW_REAL | ANALYSIS_ACCEPTED |
| P7 | CLAIM_PUBLICATION | claim registry·evidence card·figures·최종 발표/보고서 | NO_REAL | PUBLICATION_READY |

### 3. 절대 순서

P0 → P1 → P2 → P3 → P4 → P5 → P6 → P7

- P2와 P3의 오프라인 부분만 P1 종료 후 병렬 가능하다.
- P4는 P2와 P3 둘 다 닫히기 전 REAL GO 금지.
- P5는 P4 acceptance 이전 금지.
- 12 PASS → full59 자동승격은 영구 금지. E001_FULL은 계속 SUSPENDED다.

### 4. 즉시 Director 결정

- A는 현재 SSOTV3 폴더를 candidate authority pack으로 읽고, 원본 bytes를 먼저 hash verify한다.
  원본 pack을 즉시 편집해 authority를 만드는 것이 아니라
  V3_REFREEZE_DECISION과 V3_CURRENT_STATE_RECONCILIATION을 별도 생성한다.
  수정이 필요하면 원본 candidate를 덮어쓰지 말고 v3.0.1 successor를 만든다.
- A는 기존 T-A-HOLD-001 / W2 NOT_PASSED를 삭제·철회하지 않는다.
  대신 V3 dependency graph에서 RF classifier gate를 제거하는 SUPERSEDE_FOR_V3_PATH 결정을 새 티켓으로 남긴다.
- D의 old RQ/RF 미완 큐는 PIVOT_DEFERRED_LEGACY로 동결한다.
  단 D 버스 수신 스캐너의 negative-control 부재는 orchestration reliability 결함이므로 P0에서 먼저 닫는다.

### 5. Gate 판정 규칙

- PASS는 결과가 좋아서가 아니라 measurement contract가 충족돼서만 가능.
- site-specific timeout/WAF/빈 결과는 자동 전체 FAIL이 아니다.
- wrong scope, forbidden action, evidence overwrite, duplicate launch, task/outcome leakage,
  denominator corruption은 즉시 C HARD_STOP_CANDIDATE.
- 각 PASS 문서에는 "검증하지 않은 것" 절 필수.
- 관측 후 task/endpoint/family/replacement order/analysis denominator 수정 금지.
- MAIN50 pair matrix의 45 cell은 visualization/comparison cell이지 n=45 독립표본이 아니다.

### 6. V3 핵심 데이터 구조

Raw truth는 다음을 분리한다.

- task_flow_sequence: 서비스가 요구하는 task-intent action sequence. forced dismissal은 제외.
- experienced_flow_sequence: 실제 사용자가 거쳐야 한 sequence. forced dismissal 포함.
- visible_label: 실제 화면 렌더 label.
- accessible_name: browser-computed AX name.
- menu_dependency: raw manual label이 아니라 action sequence에서 파생.
- activation_depth: scroll/passive wait/typing/dismiss를 제외한 state-changing task activation 수.
- auth_gate_stage: generic login 존재가 아니라 chosen task path에서 인증이 불가피해지는 시점.
- task_control_occlusion: page-level overlay max가 아니라 task-entry control과 실제 interrupt의 geometry overlap.

### 7. 첫 실행 지시

사용자는 A에게만 directives/DIRECTOR_TO_A_START.md를 주입한다.
A가 LA-ORCH 버스를 통해 B/C/D에 phase ticket을 발행한다.
B/C/D에 별도 직접 지시를 병행하지 않는다. 이것이 authority routing을 보존한다.

---

## 원문 2 — DIRECTOR → A : V3 START INJECTION

너는 ProjectFinal의 Authority / Research Governor / Integration Governor다.

Director가 연구 피벗을 확정한다.

새 authoritative candidate pack은: /home/sieg/projects-wsl/ProjectFinal/SSOTV3

현재 목적은 기존 v2.1을 폐기하고 새로 만드는 것이 아니다.
기존 방법론·안전·검산·A/B/C/D separation을 그대로 유지하면서 substantive critical path만 아래로 전환한다.

Representative Function auto-classification → deterministically frozen matched task → observed task entry flow

지금부터 00_MASTER_DIRECTIVE.md와 phases/P0...P7을 phase authority plan으로 사용하라.

가장 먼저 P0만 실행한다. P0가 닫히기 전 B/C/D에게 P1 이후 구현/REAL 실행을 시키지 마라.

즉시 해야 할 일:

1. remote refs를 다시 확인하고 현재 exact A/B/C/D SHA를 reconciliation에 기록.
2. SSOTV3/MANIFEST_v3.0.json을 실제 local bytes에서 재해시. 후보팩 원본을 수정하지 말 것.
3. METHODOLOGY_PRESERVED.md와 V3 pack의 모순을 C에게 독립검증 요청.
4. D에게 bus scanner negative-control fixture 완결을 P0 reliability ticket으로 지시.
5. D3-01~D3-20을 ACCEPT/MODIFY/REJECT. 수정이 필요하면 v3.0 원본 덮어쓰기 금지; v3.0.1 successor.
6. 기존 W2 FAIL/HOLD는 철회하지 말고 V2_RETIRED_PATH로 보존하되
   V3 main dependency에서 제거하는 새 decision/supersede 기록.
7. E001_FULL SUSPENDED 유지. 새 V3 main50 REAL scope는 아직 발행 금지.
8. B/C/D의 P0 ACK와 C manifest/authority audit이 same exact state를 가리킬 때 V3_CONTRACT_FROZEN 판정.

P0 completion report에는:
exact heads / verified pack manifest·hash result / accepted·modified·rejected V3 decisions /
superseded V2 dependencies / still-active safety contracts / open blockers / emitted ticket IDs / next gate
를 포함한다.

P0가 완료되면 P1 Q12_METHOD_QUALIFICATION을 시작하되,
B에게 full59 runner를 재활용해 scope switch를 넣는 방식보다 dedicated 12-only V2_DIAGNOSTIC caller를 우선 지시하라.
12 qualification은 본연구 효과 추정이 아니며 12 PASS가 full59 GO를 의미하지 않는다.
