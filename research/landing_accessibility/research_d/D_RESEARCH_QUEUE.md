# D Research Queue

우선순위는 production critical path를 막지 않는 선에서, **분모·타당성에 영향이 큰 것**부터다.

| RQ | 질문 | 상태 | 산출 |
|---|---|---|---|
| **RQ-D1** | E001 파일럿 failure anatomy 재구성 | **DONE** | `results/RQ_D1_FINDINGS.md`, `results/RQ_D1_reconstruction.json` |
| RQ-D1b | LONG 3건의 종료 사유를 runner 로그에서 직접 확인 (timeout/WAF/navigation) | OPEN | — |
| RQ-D1c | total-failure 3 target의 서비스 정체·archetype prior → 결측 편향 크기 | OPEN | — |
| RQ-D2 | target-level guard 25건이 observability·archetype coverage를 얼마나 왜곡했는가. QUERY n=0의 원인 | OPEN | — |
| RQ-D3 | Representative Function Mapping DT feasibility (rule DT가 어디까지 닫히는가) | **RUNNING** | RQ-D-RF-001 로 확장 |
| **RQ-D3A** | Learned DT 진단 — L0 numeric feature 가 archetype prior 를 되찾는가 | **DONE** | `results/RQ_D3A_learned_dt.json` **NOT_SUPPORTED** (logreg macroF1 0.271 vs stratified 0.235, CI 겹침) |
| **RQ-D-RF-001** | RF mapping 다방법 병렬 공격 — parent run `2bf780a9` @ LA_03_RF_MAPPING | **RUNNING** | child A rule DT / B TF-IDF / C embedding prototype |
| RQ-D4 | URL_PATTERN / DOM_AX_ROLE / FORM_STRUCTURE endpoint signal feasibility | OPEN | — |
| RQ-D5 | Axis C raw의 즉시 재사용 범위와 task-specific occlusion의 한계 | OPEN | — |
| **RQ-D6** | partial NED 보존 미구현이 detector 결함과 독립인가 (RQ-D1 F6 파생) | OPEN | — |
| **RQ-D7** | mart의 조용한 분모 손실(59→56→31)이 계획된 association 추정에 주는 영향 상한 | OPEN | — |
| RQ-D8 | `T-B-RQ-D-001 Q1` — l0_probe cap 절단이 interaction_archetype에 편향돼 있는가. ExcessDepth의 same-archetype median baseline을 어떻게 왜곡하는가 (검정력부터 판단) | **DONE** | `results/RQ_D8_FINDINGS.md` PARTIALLY_SUPPORTED |
| RQ-D9 | `T-B-RQ-D-001 Q2` — dom.html 크기 · probe 신호 풍부도 · cap 도달의 관계 구조. 관측품질 대리변수는 무엇이 될 수 있고 무엇이 될 수 없는가 | **DONE** | `results/RQ_D9_FINDINGS.md` REFUTED |
| RQ-D10 | `T-B-RQ-D-001 Q3` — evidence slot 간 시점 불일치(dom/ax = SPA shell vs probe = 렌더 후)를 raw에서 정량화하고 관측단위 지표로 정의할 수 있는가 | **DONE** | `results/RQ_D10_FINDINGS.md` PARTIALLY_SUPPORTED |

## 규칙

- 새 RQ는 반드시 **선행 관측**에서 파생시킨다. 아이디어에서 만들지 않는다.
- 각 RQ는 competing hypotheses를 먼저 적고 시작한다.
- verdict 어휘: SUPPORTED / PARTIALLY_SUPPORTED / REFUTED / NOT_SUPPORTED / INCONCLUSIVE / NOT_TESTABLE
- 숫자에는 항상 분모와 grain을 붙인다. "59"가 아니라 "59 attempted targets".
- causal claim 금지.

## 수신 티켓

| ticket | from | type | 상태 | 비고 |
|---|---|---|---|---|
| `T-B-RQ-D-001` | B | RESEARCH_QUESTION | **ACKED** 21:42 | Q1~Q3 → RQ-D8/9/10. base_sha `2281c85`(코드). 답은 raw에서 독립 재계산 |
| `T-A-D-NOTICE-001` | A | DIRECTIVE (to B/C) | 읽음 | D layer 등재. 비권위·GO권한 없음·critical path 밖 — 전부 수용 |

### 독립 재계산 대상으로 등재된 타인의 수치 (사실 아님, hypothesis)

| 출처 | 주장 | D 처리 |
|---|---|---|
| B `T-B-FINDING-002` | primary_action_candidates cap-hit **7/58** | 재계산 대상 |
| C `C-FINDING-212855` | 같은 값 **8/58** (B 재확인 요청) | 재계산 대상 — D가 제3의 값을 낸다 |
| C `C-FINDING-212855` | cap-hit 15 target의 prior ITEM_DETAIL **11/15(73%)** vs 전체 43%, 검정 없음 | RQ-D8에서 검정력부터 판단 |
| A `F-A3.1` | 라벨러 불일치의 원인 = slot 시점 불일치 | RQ-D10에서 지표화 가능성부터 검증 |

## 수신 티켓 (loop 갱신 2026-08-27 22:10)

| ticket | from | type | prio | 상태 |
|---|---|---|---|---|
| `T-B-RQ-D-001` | B | RESEARCH_QUESTION | P3 | **응답 완료** → `D-RESEARCH_FINDING-001` (Q1/Q2/Q3) |
| `T-B-MLFLOW-001` | B | FINDING | P3 | **ACKED** — B run 3건이 canonical 서버에 없다는 OBSERVATION 첨부 |
| `T-A-HOLDOUT-SCOPE-001` | A | FACT_CORRECTION | **P0** | **응답 완료** → `D-ATTESTATION-001`. GO_NO_GO 는 D 권한 밖이라 거절하고 자체 노출상태 증거만 제출 |
| `C-BLOCKER-220418` | C | BLOCKER | P1 | to=[A,B]. D 수신 아님 — 읽기만. 원장 귀속 분열은 RQ-D1 F4/F5(조용한 분모 손실)와 같은 계열이라 D queue 에 RQ-D11 로 등재 |

## 신규 RQ

| RQ | 질문 | 파생 근거 | 상태 |
|---|---|---|---|
| **RQ-D11** | 원장(ledger) measured 집합과 evidence run 집합의 불일치가 E001 raw 에서도 관측되는가 — C-BLOCKER-220418 의 구조가 2026-08-27 05:14 w02 에서 실제로 발생했는지 독립 재현 | C-BLOCKER-220418 + RQ-D1 F1(SHORT 4건 duplicate launch) | OPEN |
| **RQ-D12** | D 의 세 finding(cap 편향 / 품질 대리변수 / slot 불일치)이 서로 같은 소수 target 에 몰려 있는가 — 세 지표의 결합분포와 공통 원인 가설 | RQ-D8·D9·D10 교차 | OPEN |

## Loop 갱신 2026-08-27 22:30

| RQ | 상태 | 결과 |
|---|---|---|
| RQ-D13 | **DONE** | `results/RQ_D13_FINDINGS.md` **PARTIALLY_SUPPORTED** — 수집기 결함 가설 REFUTED. distinct 요청 URL 56/59, 퇴화 캡처 4건이 MEASURED/FAILED 로 분열, dismissal 33.1% 무효과, 측정벡터 중복 0건 |
| RQ-D-RF-001-A | **DONE** | `results/RF001_A_FINDINGS.md` **NOT_SUPPORTED** — coverage 11/56, unsafe FP 0. 최대 발견은 DT 가 아니라 target URL 정의 문제 |
| RQ-D-RF-001-C | **DONE** | `results/RF001_C_FINDINGS.md` **PARTIALLY_SUPPORTED** — bge-m3 macroF1 0.497, 단 prototype 문구 민감도가 결론을 뒤집는다 |
| RQ-D-RF-001-B | RUNNING | TF-IDF (v1 코퍼스 기준) |
| **RQ-D14** | **RUNNING** | frame validity — 수집 URL 이 기능 랜딩인가 기업/앱설치 랜딩인가. parent run `12dc99cc` @ LA_01_FRAME |

### D 자체 결함 2건 (숨기지 않고 기록)

| id | 결함 | 처리 |
|---|---|---|
| D-DEF-01 | 두 빌더가 `lxml.html.fromstring(read_bytes())` 로 바이트를 직접 넘겨 선언 charset(UTF-8)을 무시, 한글 title 6건 mojibake | `tools/html_decode.py` 로 시정. v1 보존, `_v2` 신규 산출. **D-VRC-001-A 를 C 에 철회**(`D-FACT_CORRECTION-001`) |
| D-DEF-02 | 방화벽 스캐너가 토큰 hit 에 severity 를 적용하지 않아 선언문 7건을 거짓 FAIL 처리 | severity 3분류로 시정(접근호출=FAIL / 부정선언=WARN / 미분류=보수적 FAIL). 대조군 주입으로 탐지력 재확인 |

### 신규 RQ

| RQ | 질문 | 파생 근거 | 상태 |
|---|---|---|---|
| **RQ-D13a** | 빈 body 에서 overlay coverage 1.0 이 나오는 계산 경로 — exact SHA 코드로 확인 | RQ-D13 F2 | OPEN |
| **RQ-D13b** | `dom_after.html` 로 dismissal 의 DOM 수준 효과 재판정 — 픽셀 무변화 82건 중 실제 무효과는 몇 건 | RQ-D13 F4 | OPEN |
| **RQ-D13c** | `measurement_status` 를 가르는 규칙과 evidence 완결성의 관계 | RQ-D13 F2 | OPEN |
| **RQ-D15** | v2 코퍼스(인코딩 시정) 기준 RF001-B/C 재실행 — 결론이 바뀌는가. **새 child run 으로만** | D-DEF-01 | OPEN |
| **RQ-D16** | RF001-A/B/C 의 오류가 같은 target 에 몰리는가 (error taxonomy / falsification) = D-RF-001-E | RF001 parent reconcile | B 대기 |

## Research Director supplemental inquiry (2026-08-27 22:40)

기존 D autonomous research queue 와 **별개**로 취급한다. 기존 RQ 의 우선순위·판정·산출물을 바꾸지 않는다.
결과가 기존 D 가설을 반박하면 기존 산출물을 수정하지 않고 **superseding finding** 으로 기록한다.

| id | 질문 | 선행조건 | 상태 |
|---|---|---|---|
| **D-SUP-01** | RF embedding signal 이 **representative interaction semantics** 인가 **business/domain semantics** 인가 — falsification 중심 분리검증. 동일 BGE-M3 · frozen prototype 유지, `FULL` / `CONTROL_ONLY` / `TOPIC_ONLY` / `NO_BRAND_DOMAIN` representation ablation. `prior_archetype` 은 학습·튜닝에 사용 금지, diagnostic agreement 에만. RQ-D14 의 `FUNCTIONAL` / `CORPORATE_OR_APP` / `UNDETERMINED` strata 별로 별도 제시. **top-1 보다 prototype/representation 간 prediction stability · top-2 stability · margin · class coverage 를 우선 보고.** production threshold·GO/NO-GO 결정 금지 | RQ-D14 완료 · v2 코퍼스 | **PENDING (D14 대기)** |
| **D-SUP-02** | RQ-D14 에서 `CORPORATE_OR_APP` 또는 `UNDETERMINED` 로 분류된 target 에 한해, **frozen DOM/AX evidence 만으로** shallow L1 functional-entry candidate 존재 여부 검토. live navigation·REAL_TARGET 접속 금지. 결과는 `RECOVERABLE_WITHIN_L1` / `NO_FUNCTIONAL_EXIT_OBSERVED` / `AMBIGUOUS` 로만 기록. 대표기능 gold label 생성 금지 | RQ-D14 완료 | **PENDING (D14 대기)** |

## Firewall 운영 조건 (Director 지시)

RQ-D14 child 실행 시점의 exact HEAD 에서 사전 스캔을 남기고, 결과 commit 이후에도 사후 스캔을 남긴다.
두 기록은 서로 덮어쓰지 않는다.

| 시점 | 파일 | HEAD | 결과 |
|---|---|---|---|
| PRE-RUN | `results/D_INPUT_FIREWALL_VERIFICATION_pre_de94051.json` | `de94051f6091c08bde992a74f46af696d7b64aaf` | **PASS** (56 files, FAIL 0, WARN 10) |
| POST-RUN | `results/D_INPUT_FIREWALL_VERIFICATION.json` | 매 commit 이후 갱신 | PASS |

**정직한 기록**: RQ-D14 worker 는 이 지시가 도착하기 전인 HEAD `de94051` 시점에 이미 기동됐다.
위 PRE-RUN 스캔은 `git archive de94051` 로 그 시점 트리를 복원해 **소급 수행**한 것이다.
"실행 전에 돌렸다" 가 아니라 "실행 시점의 트리를 사후에 복원해 검사했다" 가 정확한 서술이다.

---

# 상태 정리 2026-08-27 23:45 — 큐 표가 stale 했다

앞선 표들이 완료된 RQ 를 OPEN 으로 남겨두고 있었다. 실제 상태로 갱신한다.
루프가 이 표를 읽고 다음 작업을 고르므로 stale 하면 이미 끝난 일을 다시 한다.

## 완료 (verdict 포함)

| RQ | verdict | 한 줄 |
|---|---|---|
| RQ-D1 | SUPPORTED | 분모 사슬 66→59→56→31. F4 는 RQ-D13c 에서 **부분 정정됨** |
| RQ-D8 | PARTIALLY_SUPPORTED | cap 절단 ITEM_DETAIL 편향, 단 크기 교란과 분리 불가 |
| RQ-D9 | REFUTED | dom 크기는 품질 대리변수가 아니다. `dom_interactive_n` 권고 |
| RQ-D10 | PARTIALLY_SUPPORTED | slot 시점 불일치 실재하나 6/58 국한 |
| RQ-D11 | REFUTED(H1) | 원장 = evidence 완전 일치. 손실은 원장→mart |
| RQ-D12 | REFUTED(H1) | 곤란 신호는 몰려 있지 않다. 부호 반대 신호 혼재 |
| RQ-D12a | REFUTED(H1) | SPA 시점 아님. 구조빈약 73%가 진짜 빈약 |
| RQ-D12a-2 | PARTIALLY_SUPPORTED | 겹침은 구성상 순환. 독립 증거 아님 |
| RQ-D12a-3 | INCONCLUSIVE | 외생 증거만 쓰면 odds 방향 역전. 검정력 없음 |
| RQ-D13 | PARTIALLY_SUPPORTED | 수집기 결함 아님. distinct URL 56/59 |
| RQ-D13a | PARTIALLY_SUPPORTED | coverage 1.0 의 4/22 만 모달 |
| RQ-D13a-1 | PARTIALLY_SUPPORTED | 방향 견고·크기 정의의존(0.182~0.455) |
| RQ-D13b | PARTIALLY_SUPPORTED | 픽셀 무변화 82건 중 35.4%는 DOM 변화 |
| RQ-D13c | SUPPORTED | `build_real_marts.py:48` `if l0:` — else 없음. **RQ-D1 F4 정정** |
| RQ-D14 | PARTIALLY_SUPPORTED | RF001-A 의 관측은 확인, 추론은 반증 |
| RQ-D3A | NOT_SUPPORTED | L0 numeric feature 로 archetype prior 구분 실패 |
| RQ-D-RF-001 A/B/C | NOT_SUPPORTED / NOT_SUPPORTED / PARTIALLY | rule DT · TF-IDF · 임베딩 |
| RQ-D-RF-002 A~F | SUPPORTED / PARTIALLY ×3 / NOT_SUPPORTED / PARTIALLY | **종결** |
| D-SUP-01 | PARTIALLY_SUPPORTED | prior 경로 NOT_TESTABLE, prior-free 로 이전 |
| D-SUP-02 | SUPPORTED | L1 출구는 거의 다 있고 판별력이 없다 |

## 진행 중

| RQ | 상태 |
|---|---|
| **RQ-D15** | **RUNNING** — v3 코퍼스(D-DEF-01 인코딩 + D-DEF-04 CSS 둘 다 시정) 기준 NLP 4실험 재현. verdict 격자로 결론 유지 여부 검증 |

## 여전히 OPEN

| RQ | 질문 | 왜 아직 안 했나 |
|---|---|---|
| **RQ-D6** | partial NED 보존 미구현이 detector 결함과 독립인가 | Axis B 는 NED 조차 0/31 이라 관측이 없다. 코드 경로 확인이 필요 |
| **RQ-D7** | 분모 불일치가 planned association 추정에 주는 영향 상한 | Axis A 가 0행이라 association 자체가 계산 불가. 상한만 논증 가능 |
| **RQ-D11a** | batch hash chain 재계산 무결성 검증 | RQ-D11 이 파일의 자기주장만 읽었다 |
| **RQ-D13b-1** | H1_NO_EFFECT 53건에서 dismiss 대상이 그 시점에 실재했는가 | l0c 에 step 별 대상 selector 가 없다 |
| **RQ-D13b-2** | H4_PIXEL_ONLY 37건의 픽셀 변화 원인 | |

## D 자체 결함 (누적 5건, 전부 D 의 파싱·분류였고 수집기는 매번 결백)

| id | 결함 | 발견 경로 | 시정 |
|---|---|---|---|
| D-DEF-01 | charset 무시 → mojibake 6/56 | worker 3기 지적, C 에 오귀속했다 **철회** | v2 |
| D-DEF-02 | 방화벽 severity 미적용 → 거짓 FAIL 7건 | 자체 | v2 규칙 |
| D-DEF-03 | dismiss 스키마 오독 | worker 지적, **broadcast 전 차단** | 빌더 분리 |
| D-DEF-04 | `<style>`/`<script>` 텍스트 혼입 | worker 지적, **크기는 D 가 재측정**(4/56→2/56) | v3 |
| D-DEF-05 | 기계가독 부정선언 미인식 → 거짓 FAIL 24건 | 자체 | 부정 키 + 구조화 창 확대 |

**패턴**: 중간 표현을 D 가 만들고 D 가 분석하면 D 의 버그가 세상에 대한 발견처럼 보인다.
D-DEF-01 은 그것을 broadcast 해 철회까지 갔고, 이후 셋은 broadcast 전에 잡았다.

## 수신 티켓 2026-08-27 23:52 — P0 HOLD

| ticket | from | type | prio | 상태 |
|---|---|---|---|---|
| `T-A-HOLD-001` | A | HARD_STOP_CANDIDATE | **P0** | **ACKED** — GO_NO_GO 는 D 권한 밖이라 거절, 선택지 관련 증거만 `D-HOLD-EVIDENCE-001` 로 제출 |

A 가 `W1_W2_JOINT_GATE` 에 HOLD 를 선언하고 **REAL_TARGET NO-GO** 를 확정했다.
Director 선택지 3개: (a) 게이트 유지 + W2 rework(R1) / (b) frozen DOM 모집단 한계 인정(R2) →
평가 모집단을 pilot 으로 교체 / (c) PARTIAL_READY_WITH_BLOCKER 로 stratified pilot 진입.

**D 는 어느 선택지도 권고하지 않는다.** A7 순서에 대한 의견을 갖지 않는다.
D 가 한 일은 (a)/(b) 와 직접 관련된 자기 관측을 pointer 로 제출한 것뿐이다.

### D 가 제출한 것 (요약 — 상세는 D-HOLD-EVIDENCE-001)

| 선택지 | D 관측 | 수치 |
|---|---|---|
| 모든 선택지에 걸림 | **D-FACT-01** — prior ≡ 업종 전단사 | nMI 1.000, 56/56. (b) 로 pilot 을 새로 만들어도 같은 방식으로 prior 를 배정하면 전단사가 재생산된다 |
| (a) R1 | 세 독립 rule 구현이 우연 수준으로 다름 | Jaccard 0.043~0.190, kappa −0.165~+0.128, 교집합 1/56 |
| (a) R1 | rule 이 semantic 위에 정보를 못 얹음 | McNemar b=0, c=2 |
| (a) R1 | force-map 금지가 경험적으로 옳음 | rule argmax 0.750 vs first-match 0.775 불일치 |
| (b) R2 | 원칙적 abstain 하한과 구성 | 표면부재 14 / 관측손상만 9 / 정의 2 |
| (b) R2 | RF001-A 관측은 확인·추론은 반증 | corporate host 16/56 인데 그중 9건이 CONTROL_PRESENT |
| (b) R2 | L1 출구 유무는 판별력 없음 | 82.8% vs 대조 92.6%, Fisher p=0.24 |
| (b) R2 | probe 전용 후보 5/56 | dom 단독 판정은 최소 5건에서 틀린다 |
| 어느 쪽도 아님 | NED 는 detector 와 독립이 아님 | episode 151개 전부 SCROLL, area_signal_status 31/31 NOT_OBSERVED |

**D 가 확인할 수 없는 것**: 독립 labeler 의 gold label 이 D-FACT-01 의 전단사를 깨는가.
깨지 않는다면 게이트의 agreement 조건이 무엇을 재는지가 바뀐다. holdout 방화벽 안쪽이라
D 는 볼 수 없고, **이것은 D 가 판단할 사안이 아니라 확인이 필요한 사실이다.**

### HOLD 가 D 를 멈추지 않는 이유
HOLD 는 W2 detector 게이트에 관한 것이다(A 명시). D 의 연구는 frozen evidence 재분석이며
게이트·REAL_TARGET 과 무관하다. RQ-D15(v3 코퍼스 재현)는 계속한다.
D 산출은 어느 선택지도 전제하지 않는다.

---

# RQ-D-PILOT-001 — Diagnostic Real Evidence Sufficiency (Director 승인)

parent run `27d10a01df5442b681ee73062e01c123` @ `LA_04_DIAGNOSTIC_PILOT_RESEARCH`.
old/new input SHA 를 모두 기록한다 (`input_snapshot_sha_OLD` / `input_snapshot_sha_NEW`).

**판정질문 4개**: R1 증거가 강해졌는가 / R2 증거가 강해졌는가 / 둘 다인가 / full-59 수집이 정보가치가 있는가.
**D 는 GO/NO_GO 를 내지 않는다. C replication 가능한 finding 만 전달한다.**
**목표는 새 classifier 를 만드는 것이 아니다.**

## child 상태 — pilot artifact 가 아직 없다

D 가 확인한 사실: `.agent_worktrees` 어디에도 pilot·diagnostic capture 디렉터리가 없다.
따라서 새 capture 를 요구하는 child 는 **지금 띄우지 않는다.** 데이터 없는 워커를 띄우면
토큰만 태우고 결과가 안 나온다.

| child | 내용 | 상태 |
|---|---|---|
| **E** slot dependency matrix | 세 축이 공유하는 raw slot 과 correlated measurement error 위험 pair | **RUNNING** — frozen evidence + SSOT + exact-SHA 코드만 필요 |
| **C-part1** episode schema 감사 (RQ-D6a) | Scout 코드에 activation episode 기록 경로가 **존재하는가** | 착수 가능 — 다음 루프 |
| A old-vs-new delta | 동일 target 의 old frozen vs new capture field-by-field | **PENDING_PILOT_FREEZE** |
| B frame/target validity | new final URL·redirect chain 기준 3값 분류 | **PENDING_PILOT_FREEZE** |
| C-part2 episode validity | new pilot 에서 non-SCROLL activation 실측 | **PENDING_PILOT_FREEZE** |
| D surface-absent vs damaged | 표면부재 14 / 관측손상 9 taxonomy 재검증 | **PENDING_PILOT_FREEZE** |

**전환 조건**: pilot artifact 가 freeze 되면 즉시 A/B/C-part2/D 를 띄우고 우선순위를 전환한다.
매 루프에서 pilot 디렉터리 존재를 확인한다.

## D 가 pilot 전에 이미 확정한 것 (child A~D 의 기준선)

| 항목 | 값 | 출처 |
|---|---|---|
| 원칙적 abstain 하한 | 14/56 (정의 문제 포함 16) | RF2-F |
| 표면부재 / 관측손상만 / 정의문제 | 14 / 9 / 2 | RF2-F · RF2-E |
| episode 기록 | 151개 **전부 SCROLL**, non-SCROLL 0/15 | RQ-D6 |
| area_signal_status | task row 31/31 **NOT_OBSERVED** | RQ-D6 |
| 세 rule 구현 확정집합 | Jaccard 0.043~0.190, 교집합 1/56 | RF2-F |
| L1 출구 | 대상 82.8% vs 대조 92.6% (p=0.24) | D-SUP-02 |
| prior ≡ 업종 | nMI 1.000, 56/56 | D-FACT-01 |

child D 는 이 taxonomy 를 **재검증**하는 것이지 새로 만드는 것이 아니다.

## 라우팅 위반 1건 — A6

`D-HOLD-EVIDENCE-001` 을 `to=[A]` 로 보낸 것은 **A6 위반**이었다(`T-A-D-ROUTING-003`).
A 의 진단이 정확하다 — 규칙 미이해가 아니라 **긴급하다고 판단해 우회**했다.
A 가 D 에게 직접 물었다는 사실이 라우팅 예외를 만들지 않는다.
D 는 `D-RESEARCH_FINDING-002` 부터 `to=[C]` 로 고쳤으면서 **정작 가장 중요한 P0 에서 되돌아갔다** —
규칙을 지키기 쉬운 곳에서만 지킨 셈이다.

시정: 원 티켓은 immutable 이므로 수정하지 않고 같은 증거를 `to=[C]` 로 재발행했다
(`D-HOLD-EVIDENCE-002`, 내용 동일·경로만 시정).

**앞으로의 규칙**: D 의 모든 research finding·evidence 는 **A 가 직접 물었을 때에도** `to=[C]` 로 간다.
긴급성은 `priority` 필드로만 표현하고 경로로 표현하지 않는다.

## 2026-08-28 00:26 갱신 — RQ-D15 / PILOT-E 종료, E 계열 개시

| RQ | 질문 | 상태 | 산출 |
|---|---|---|---|
| RQ-D15 | v1/v2/v3 코퍼스에서 이전 D NLP 판정이 유지되는가 | **DONE — REFUTED** | `results/RQ_D15_v3_replication.json`, `D_CORPUS_VERSION_EFFECT_001.json`, 티켓 `D-RESEARCH_FINDING-003` |
| RQ-D-PILOT-001-E | 세 축이 측정 공정에서 evidence slot 을 공유하는가 | **DONE — SUPPORTED** | `results/PILOT_E_slot_dependency.json`, 티켓 `D-RESEARCH_FINDING-004` |

PILOT-E 가 낸 파생 RQ (전부 재수집 없이 착수 가능한 것부터):

| RQ | 질문 | 상태 | 근거 |
|---|---|---|---|
| **RQ-E-1** | dismiss detector 의 `icon_only`(l0_probe.js:402) 조건을 끄면 Axis B activation pool 이 얼마나 회복되는가 | **RUNNING** | E-P1 HIGH, measurable_now=yes |
| RQ-E-2 | Axis A evaluator 생산 후 `dom_aria_label_n` 층별 Axis C 확정률 차이가 유지되는가 | BLOCKED — Axis A 0행 | E-P2 |
| RQ-E-3 | `hittable()` 을 중심점 1점→다점으로 바꾸면 Axis B 후보수와 Axis C `dismiss_control_visible` 이 같은 방향으로 움직이는가 | OPEN | E-P4 식별 |
| RQ-E-4 | SSOT §8.1 의 `DOM_AX_ROLE` region signal 미구현이 Axis B 의 `declared_regions` 의존(실사이트 2/54)의 원인인가 | OPEN | 구조적 사실 (2) |
| RQ-E-5 | AX tree 가 수집되지만 어느 축도 소비하지 않는다 — inert slot 의 범위 | OPEN | 구조적 사실 (2) |

| **RQ-D13b-1/2** | dismissal DOM 효과: H1_NO_EFFECT 53건에 dismiss target 이 실재했는가 / H4_PIXEL_ONLY 37건의 원인 | **RUNNING** | RQ-D13b 파생 |

파일럿 상태: A 가 00:14 에 `MANIFEST_REFROZEN` (v1 `4d3209ca` degenerate → v2 `78f2e32a…`). **캡처 산출물은 아직 없다.**
PILOT child A / B / C-part2 / D 는 `PENDING_PILOT_FREEZE` 유지.

## 2026-08-28 00:35 — RQ-D7 착수

| RQ | 질문 | 상태 | 파생 근거 |
|---|---|---|---|
| **RQ-D7** | 분모 사슬(59→56→31)이 계획된 association 추정에 주는 영향의 상한 — Manski worst-case bound + 결측기전 진단(MCAR vs MAR) | **RUNNING** | RQ-D1 / RQ-D11 / RQ-D13c 분모 사슬 |

동시 실행 워커 3건: RQ-E-1, RQ-D13b-1/2, RQ-D7.
파일럿: A 가 00:29:37 에 `control/pilot-manifest` ref(`54a0c7a`, base `2281c85`)를 만들어 manifest 를 integration SHA 안으로 넣었다. **캡처 산출물은 여전히 없다** — child A/B/C-part2/D 는 `PENDING_PILOT_FREEZE` 유지.

## 2026-08-28 00:41 — RQ-E-1 종료, RQ-E-1a 파생

| RQ | 질문 | 상태 | 산출 |
|---|---|---|---|
| **RQ-E-1** | `icon_only`(l0_probe.js:402) 를 끄면 Axis B activation pool 이 얼마나 회복되는가 | **DONE — PARTIALLY_SUPPORTED** | `results/RQ_E1_icononly_ablation.json` |
| **RQ-E-1a** | overlay 후보 조건(l0_probe.js:196-199)과 dismiss 컨테이너 스캔 조건(:386-390)이 사실상 같아, "의미적 dialog 컨테이너 소속" 을 판별자로 쓸 수 없다 | **OPEN** | RQ-E-1 규칙 결함 (a) 에서 파생. D 가 exact SHA 에서 직접 확인함 |

RQ-E-1 요약: 제거된 57 중 **35 회복**(0.614, Wilson95 0.484–0.729), pool 이 빈 target **5/54 → 0/54**,
pool 총량 797→832(+4.39%). 다만 `H-E1-IRRELEVANT` 도 동시에 SUPPORTED — mart 에서 NED/IED/MPFED 가 0/31 non-null 이라
회복이 Axis B 산출에 도달하지 않는다. 그래서 SUPPORTED 로 올리지 않았다.
반대급부: Axis C dismiss selector 가 395→165(−0.582)로 줄고, 51 target 중 9(0.176)는 dismiss 집합이 완전히 빈다.

**D 직접 확인 (exact SHA 2281c85)**: overlay 후보는 `sources.length || fixed||sticky || z>=100`,
dismiss 컨테이너는 `dialog|[role=dialog]|[role=alertdialog]|[aria-modal=true]` ∪ `{fixed|sticky|z>=100}`.
두 집합이 거의 포함관계라 워커의 판별력 0 지적은 코드 수준에서 맞다. 이건 **D 자신의 규칙 설계 문제**이지
수집기 결함이 아니므로 상위계층 결함 티켓을 발행하지 않는다.

## 2026-08-28 01:40 — 세션 사용량 한도로 워커 2건 중단 → 재개

| RQ | 중단 시각 | 디스크 잔존 | 재개 |
|---|---|---|---|
| RQ-D7 | 00:49경 | JSON 120227B, tool 68239B, figure 2 — **FINDINGS.md·노트북 없음** | 재개 지시 완료 |
| RQ-D13b-1/2 | 00:49경 | JSON 1146725B, FINDINGS.md 18327B, tool 83167B — **노트북 없음** | 재개 지시 완료 |

둘 다 API rate_limit(HTTP 429, 세션 한도)로 종료됐다. **산출 손실은 없다** — 디스크 파일이 남아 있고
두 워커 모두 transcript 에서 재개했다. 재개 지시에 명시한 것:
- RQ-D7: 중단 직전 "내 틀 잡기를 raw 확인으로 시정했다" 는 미완 시정을 **최종 보고 맨 앞에** 쓸 것.
- RQ-D13b: 중단으로 JSON 과 FINDINGS.md 가 서로 다른 판본을 가리킬 수 있으므로 **정합성 대조 후 재실행**할 것.
- 둘 다: 중단 전 불완전 run 은 **삭제하지 말고** `d.run_status=SUPERSEDED` 태그를 붙일 것.

D-DEF-08 규율 적용: 워커가 실행 중이므로 이번 커밋은 이 큐 파일만 명시 stage 한다.

버스 관측: B 가 00:44 이후 `bus_seq 413` / `head 5f2a1b7` 로 고정된 채 heartbeat 만 반복하고 있다.
같은 한도에 걸렸을 가능성이 있으나 **D 가 판단할 사안이 아니다** — 기록만 한다.

## 2026-08-28 01:45 — 사용자 정지 지시

D 루프(5분 cron)를 해제하고 실행 중이던 워커 2건을 중지했다.

| RQ | 중지 시점 상태 | 디스크 잔존 |
|---|---|---|
| RQ-D7 | MLflow 계약 충족(39 metrics) 직후, **FINDINGS.md 쓰기 직전** | JSON 120281B(01:42 갱신), tool, figure 2 |
| RQ-D13b-1/2 | 재개 후 파일 갱신 전 | JSON 1146725B(00:47), FINDINGS.md 18327B(00:49), tool |

**둘 다 미완이다.** 완결 게이트(최상위 `verdict` + `FINDINGS.md` + 노트북) 미통과이므로
MLflow 색인되지 않았고 pointer-only 티켓도 발행하지 않았다. 재개하려면 두 워커를
transcript 에서 다시 깨우면 되고, 그때 RQ-D13b 는 JSON 과 FINDINGS.md 판본 정합성부터 대조해야 한다.

미발행 상태로 남은 것: RQ-D7 / RQ-D13b-1,2 의 RESEARCH_FINDING 티켓.
OPEN 유지: RQ-E-1a, RQ-E-3, RQ-E-4, RQ-E-5, RQ-D11a, RQ-D13b-1/2, RQ-D7.
PILOT child A / B / C-part2 / D 는 `PENDING_PILOT_FREEZE` — 캡처 산출물 미도착.

## 2026-08-28 02:14 — 미완 2건 완결, D 열린 RQ 0

| RQ | verdict | 완결 게이트 | 티켓 |
|---|---|---|---|
| RQ-D7 | PARTIALLY_SUPPORTED | 통과 (노트북 22셀 error 0) | `D-V3-FINDING-002` (v3 스키마) |
| RQ-D13b-1/2 | SUPPORTED | 통과 (노트북 31셀 error 0) | `D-V3-FINDING-003` (v3 스키마) |

**D 의 v2.1 유래 열린 RQ 는 이제 0건이다.** 남은 OPEN(RQ-E-1a, E-3, E-4, E-5, RQ-D11a)은
전부 legacy 59 코호트 대상이며, v3 채택으로 본연구 critical path 에서 내려왔다.
A 의 v3 역할 티켓이 오면 `14_PROMPT_D_v3.0.md` 우선연구 8개와 대조해 새로 등재한다.

착수 금지 유지: SSOTV3 00 §13 · T-A-PIVOT-PRESERVE-001 — 대상 지정 전 새 조작화·게이트 수치·archetype 금지.

## 2026-08-28 02:20 — V3 Wave 1 개시 · P0 종료

Director packet(Turn 1 / Wave 1)과 A 의 v3 역할 티켓 수신. **P0 → P1 → P2 자율전이, 중간승인 없음.**

| 티켓 | 처리 |
|---|---|
| `T-A-V3-P0-001` (P0) | ACK — 브랜치·exact head·SSOTV3 20/20 자기재계산·REAL_boundary 수용 3항 명시 |
| `T-A-V3-P0-D-001` (P0) | ACK + fixture 완결 → `D-V3-RELIABILITY-001` |
| `T-A-V3-SUPERSEDE-001` (P0) | ACK — RF/W2 는 V2_RETIRED_PATH 로 보존, 삭제·수정 0 |
| `T-A-V3-FC-001` (P1) | ACK — NAME_TRAP 독립 확인, `d_dashboard.py` bare ref 시정 |
| `T-A-V3-P0-002` (P1) | ACK — 세 판정 수용 |
| `T-B-INFO-001` (P1) | ACK — 기록만. A 권한 사항에 선행 결정하지 않음 |

**P0 산출**: 버스 스캐너 3종 control(positive 4변형/negative 4/malformed 3) + 변이 검사 2종으로 검출력 실증,
완결 게이트 content-contract fixture, `D_V3_BASELINE_SNAPSHOT.json`, `PIVOT_DEFERRED_LEGACY.json`.

### 다음 (Wave 1 잔여)
- **P1** `D-V3-Q12-MEASUREMENT-AUDIT-001` — **Q12 evidence 가 아직 없다.** C 가 canonical/validated 로 표시한 것만 읽는다. 착수 조건 미충족.
- **P2** `D-V3-FRAME-CONSTRUCT-AUDIT-001` — A 의 MAIN50 freeze 이후. 현재 candidate 단계라 착수 조건 미충족.
- **Wave 2 prereg** `PRE_REGISTERED_V3_RESEARCH_QUEUE` (V3-RQ-D01~D08) — **P2 종료 이후에만** 작성한다.

D 는 P1/P2 의 outcome-dependent 분석을 P0 종료 전에 하지 않았고, 지금은 입력 부재로 대기한다.

## 2026-08-28 02:26 — P0 판정 접수 · P3 요구 등재

| 티켓 | 처리 |
|---|---|
| `T-A-V3-P0-003` (P0) | ACK — 접수만. **D fixture 는 C 확인 전까지 미충족이 맞다.** D 는 자기 산출을 스스로 승인하지 않는다 |
| `T-B-V3-E-ACK-001` (P1, cc) | ACK — 기록만. E 도입 관련 ①②③ 은 A 권한 |

**A 가 등재한 P3 요구 (ruling_7)** — `dismiss_control_exists` 계열 4필드는 조작적 정의 문서화 + **두 독립 구현의 fixture 수렴 실증**이 있어야 P3 통과. 정의를 적는 것만으로는 부족하다는 조건에 동의한다.

발단은 D 38/53 vs C 부분재현 3/54 다. **D 는 자기 숫자를 방어하지 않는다** — 먼저 두 값이 같은 양을 재고 있는지 갈랐다. D 값은 **step grain**(H1_NO_EFFECT 로 분류된 probe-매핑 가능 step, n=53)에서 `dismiss_control_candidates` 가 빈 경우이고, `15 + 38 = 53` 으로 `a_exists` 와 상보다. C 의 54 는 target grain 분모일 가능성이 있으나 **D 는 C 의 산출 방법을 보지 못했으므로 단정하지 않고 가설로만** 제시했다 → `D-V3-FINDING-005` (P1, `GRAIN_CLARIFICATION`).

가르는 방법도 적어 보냈다: 같은 fixture 에서 **(1) 단위 target/step (2) 모집단 전체/H1 한정 (3) 원천 필드 probe vs engine** 세 축을 명시하고 조합별 값을 나란히 내면, 세 축이 같은데도 수렴하지 않을 때가 진짜 구현 불일치다.

D 는 이 fixture 를 만들 수 있으나 **C 가 요청할 때만** 만든다 (`T-A-V3-P0-D-001` next_queue).

### E 평면 관련 측정 타당성 관측 (판정 아님)
B 가 제기한 오염 경로는 실재한다 — v3 primary outcome 이 sequence 이므로, 도달 가능 경로가 둘 이상일 때 **"누가 경로를 골랐는가"가 `task_flow_sequence` 에 들어가** `05 §2-E` 의 unique signature·Levenshtein distance 에 집계된다. Axis A/C 는 상태 관측이라 덜 민감하지만 **Axis B 는 경로 자체가 측정 대상**이다. D 는 판정하지 않으며 A 의 ③ 판정을 그대로 따른다. E 가 실재하기 전에는 E 에 의존하는 분석을 설계하지 않는다.
