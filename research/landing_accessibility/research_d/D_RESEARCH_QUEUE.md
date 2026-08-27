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
