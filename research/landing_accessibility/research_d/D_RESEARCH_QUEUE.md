# D Research Queue

우선순위는 production critical path를 막지 않는 선에서, **분모·타당성에 영향이 큰 것**부터다.

| RQ | 질문 | 상태 | 산출 |
|---|---|---|---|
| **RQ-D1** | E001 파일럿 failure anatomy 재구성 | **DONE** | `results/RQ_D1_FINDINGS.md`, `results/RQ_D1_reconstruction.json` |
| RQ-D1b | LONG 3건의 종료 사유를 runner 로그에서 직접 확인 (timeout/WAF/navigation) | OPEN | — |
| RQ-D1c | total-failure 3 target의 서비스 정체·archetype prior → 결측 편향 크기 | OPEN | — |
| RQ-D2 | target-level guard 25건이 observability·archetype coverage를 얼마나 왜곡했는가. QUERY n=0의 원인 | OPEN | — |
| RQ-D3 | Representative Function Mapping DT feasibility (rule DT가 어디까지 닫히는가) | OPEN | — |
| RQ-D4 | URL_PATTERN / DOM_AX_ROLE / FORM_STRUCTURE endpoint signal feasibility | OPEN | — |
| RQ-D5 | Axis C raw의 즉시 재사용 범위와 task-specific occlusion의 한계 | OPEN | — |
| **RQ-D6** | partial NED 보존 미구현이 detector 결함과 독립인가 (RQ-D1 F6 파생) | OPEN | — |
| **RQ-D7** | mart의 조용한 분모 손실(59→56→31)이 계획된 association 추정에 주는 영향 상한 | OPEN | — |
| **RQ-D8** | `T-B-RQ-D-001 Q1` — l0_probe cap 절단이 interaction_archetype에 편향돼 있는가. ExcessDepth의 same-archetype median baseline을 어떻게 왜곡하는가 (검정력부터 판단) | **ACKED** | — |
| **RQ-D9** | `T-B-RQ-D-001 Q2` — dom.html 크기 · probe 신호 풍부도 · cap 도달의 관계 구조. 관측품질 대리변수는 무엇이 될 수 있고 무엇이 될 수 없는가 | **ACKED** | — |
| **RQ-D10** | `T-B-RQ-D-001 Q3` — evidence slot 간 시점 불일치(dom/ax = SPA shell vs probe = 렌더 후)를 raw에서 정량화하고 관측단위 지표로 정의할 수 있는가 | **ACKED** | — |

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
