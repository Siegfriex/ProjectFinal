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
