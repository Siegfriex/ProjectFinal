# D_DASHBOARD — Research Director 감시판

생성 `2026-08-27T22:14:33.858282+09:00` · 재실행 `.venv/bin/python research_d/tools/d_dashboard.py`

> **MLflow 는 truth 가 아니다.** truth precedence:
> `raw artifact / exact SHA` → `독립 재현계산` → `frozen definition` → `accepted SSOT / decision` → `MLflow metadata / prose`
> 각 수치의 출처 계층을 T1~T5 로 표기한다. run 이 존재한다는 사실은 승인이 아니다.

> **없는 값을 만들지 않는다.** `NOT_AVAILABLE` / `NOT_EVALUATED` / `NONE_YET` 은 실패가 아니라 *아직 산출되지 않았음*이며, 각각 왜 없는지를 함께 적었다.

## 0. 한눈에

| 섹션 | 한 줄 |
|---|---|
| 1. 운영 상태 | phase=I1 · active MLflow runs A/B/C/D = 0/0/0/1 · open P0 8 · open P1 7 · unpushed agents 3/4 |
| 2. 데이터 | 66 observation dirs → 59 attempted targets → 56 evidence-bearing → 53 MEASURED landing rows → 31 task rows. joint-valid(A+B+C) = 0 / 56 landing rows — Axis A 0행 · Axis B NED 전량 null 이기 때문. |
| 3. RF detector | detector 성능(macro F1 · abstention · unsafe FP)은 전부 NOT_AVAILABLE — W2 detector 평가 run 이 아직 없다. 분할 크기(cal/hold)만 C 의 라벨 run 에서 읽힌다. |
| 4. KWCAG | Axis A = NOT_EVALUATED. criterion 0행 / 56 landing rows — 비율은 정의되지 않는다. |
| 5. Depth | NED/IED/MPFED 전부 0 / 31 task rows — 세 depth 지표 모두 NOT_AVAILABLE. endpoint_reached 0 / 31 task rows. UNRESOLVED 18 행은 종료 사유 미기록. |
| 6. Axis C | overlay coverage 56/56 landing rows 가용 · semantic DETERMINISTIC 125/235 interrupt rows (0.5319) · task-bound occlusion 은 NOT_AVAILABLE (page-level 값만 존재). |
| 7. D Research | OPEN RQ 9 / 16 queue rows · D runs running 1 · supported 5 / refuted 3 / inconclusive 3 (settled D verdicts 12) |
| 8. C Assurance | C MLflow runs 15 — MATCH 5 / MATCH_WITH_NONBLOCKING_DIFFERENCE 5 / result-affecting+systemic mismatch 5. C completions 13 (severity C1 1 · C0 없음). reproduced D findings: 1 (그중 D_CONFIRMED/MATCH 1) |

| tier | 의미 | 이 대시보드에서의 예 |
|---|---|---|
| **T1** | raw artifact · runtime evidence · exact code SHA | `git ls-remote` exact SHA, evidence 디렉터리 실측 |
| **T2** | 독립 재현계산 (D 가 raw 에서 직접 다시 센 값) | 분모 사슬 66→59→56, claim ledger 재계산 |
| **T3** | frozen definition · schema · hash 고정된 mart | fact_*.json 행수·null 수 |
| **T4** | accepted SSOT · decision · agent bus 기록 | heartbeat phase, 티켓 P0/P1, C completion |
| **T5** | MLflow metadata · prose · agent narrative — **가장 약함** | run_status, verdict tag, metric |


## 1. 운영 상태

**phase=I1 · active MLflow runs A/B/C/D = 0/0/0/1 · open P0 8 · open P1 7 · unpushed agents 3/4**

### active runs (T5)
| plane | RUNNING runs | 분모 |
|---|---|---|
| A | 0 | 53 total MLflow runs |
| B | 0 | 53 total MLflow runs |
| C | 0 | 53 total MLflow runs |
| D | 1 | 53 total MLflow runs |

주의 — run_status 는 tag 이므로 프로세스가 죽어도 RUNNING 으로 남는다. 이것은 프로세스 생존 증거가 아니라 '누가 run 을 닫지 않았는가' 다.

### phase · heartbeat (T4)
| agent | phase | work_state | hb age(s) | blockers |
|---|---|---|---|---|
| A | I1 | ALL_DECISIONS_ISSUED_AWAITING_W1_W4_COMPLETIONS | 1237 | 8 |
| B | I1 | I1_P0_CONTAMINATION_SELF_REPORTED | 56 | 0 |
| C | I1 | C2_FORENSIC_CLEAN__NEXT_C3_W1_FIXTURE_HARNESS_C4_W3 | 175 | 1 |
| D | I1 | RESEARCHING | 417 | 0 |

current phase = **I1**

### open P0/P1 — P0 **8** · P1 **7** (분모 42 P0+P1 tickets) (T4)

| ticket | prio | type | from→ | 미응답 | 요지 |
|---|---|---|---|---|---|
| T-A-LABEL-PREP-001 | P0 | DIRECTIVE | A→B,C | B | 독립 Labeler 조직 예고 — label 생산 금지 고지 |
| C-BLOCKER-215510 | P0 | BLOCKER | C→A,B | A,B | label contamination (protocol §7 P0 / §13) — SCOPED to holdout integrity; 전체 정 |
| T-B-ATTEST-001 | P0 | FACT_CORRECTION | B→A,C | A |  |
| C-FINDING-220024 | P0 | FINDING | C→A,B | A,B |  |
| T-A-HOLDOUT-SCOPE-001 | P0 | FACT_CORRECTION | A→B,C,D | D | C 가 C-FINDING-220024 에서 분모를 사전 고정했는데 그 입력이 틀렸다. 결과가 나오기 전에 정정한다. |
| C-FACT_CORRECTION-220511 | P0 | FACT_CORRECTION | C→A,B | A,B |  |
| T-A-DIRECTOR-A1-A7 | P0 | DIRECTIVE | A→B,C,D | B,D |  |
| T-A-W2-RECOVERY-001 | P0 | WORK_REQUEST | A→B | B | W2 오염 복구 attestation + diff (Director A3) |
| C-FACT_CORRECTION-210136 | P1 | FACT_CORRECTION | C→A,B | A,B |  |
| T-A-FINDING-001 | P1 | FINDING | A→B,C | B |  |
| C-FINDING-212458 | P1 | FINDING | C→A,B | B |  |
| T-A-DECISIONS-51-57 | P1 | DIRECTIVE | A→B,C | B |  |
| T-B-FINDING-003 | P1 | FINDING | B→A,C | A | D-R0-60 의 e2e 요구가 실제 결함을 잡았다 — DUPLICATE_SUPPRESSED 가 표준 파이프라인에서 MEASURED 로 접혔 |
| C-BLOCKER-220418 | P1 | BLOCKER | C→A,B | A,B | C e2e(프로세스 2개, 같은 out dir) @860e4e8: evidence run 3/3 target · lock 3 DONE · 억 |
| C-BLOCKER-221347 | P1 | BLOCKER | C→A,B | A,B | C 픽스처 SUT 실행: (1) 숨김 reCAPTCHA iframe+api.js 만 있는 상품목록 랜딩 → gate 판별 'RESOLVED  |

*open = 티켓의 to[] 수신자 중 acks/ 나 completions/ 에 <ticket_id>.<recipient>.json 이 없는 사람이 하나라도 있는 것. 내용상 해소 여부는 판단하지 않는다 — 파일 존재만 본다.*

### exact SHA (T1 — branch name 으로 상태를 주장하지 않는다)
| plane | branch | origin exact SHA |
|---|---|---|
| A | `control/landing-orchestrator` | `e16779e52e65b7d5ca04d29510f619ea8391d155` |
| B | `claude-b/clean0-v21` | `31a86e378e197e88fb6dffe2a466250fbfeb6a74` |
| B | `claude-b/analysis-current` | `82f631f1e6bd3708bc8f95f0b8edcd90e22cef0d` |
| B | `claude-b/w1-guard-wiring` | `860e4e808d42a3edff055ee06e38c13082b32f64` |
| B | `claude-b/w2-rf-detector` | `f76ee8ba63f50a1f5df7785d4b5cef32a16e386f` |
| B | `claude-b/w3-kwcag` | `94cbf8b610a9386267e3cbeb3057319a57a15634` |
| B | `claude-b/w4-axisc-mart` | `b27794feccc4ab07efd87aaad54bf648798fa293` |
| C | `claude-c/assurance-v21` | `b336572ca7dede8940661465e19be5daf4871c0b` |
| C | `claude-c/assurance-current` | `1baa865b4a673af05033e6e6289fd2713676baa5` |
| D | `claude-d/research-sandbox-v21` | `31679b86a98e8811a1cfa89d5a5f61c02b25437a` |
| - | `research/landing-accessibility-main` | `bc0b7a087faf2328cbafdfa9b40bd426c5080d7d` |
| - | `agent/landing-v2-exec` | `bc0b7a087faf2328cbafdfa9b40bd426c5080d7d` |

| agent | branch | heartbeat 주장 | origin 실측 | 일치 |
|---|---|---|---|---|
| A | `control/landing-orchestrator` | `9f39acf20b8b` | `e16779e52e65` | **X** |
| B | `claude-b/clean0-v21` | `31a86e378e19` | `31a86e378e19` | O |
| C | `claude-c/assurance-v21` | `b7d13fbe20c4` | `b336572ca7de` | **X** |
| D | `claude-d/research-sandbox-v21` | `2ad18b69859e` | `31679b86a98e` | **X** |

### D subagents (T4)
| rq | status | verdict | tokens | min | files |
|---|---|---|---|---|---|
| RQ-D8 | completed | PARTIALLY_SUPPORTED | 108,682 | 13.84 | 4 |
| RQ-D10 | completed | PARTIALLY_SUPPORTED | 135,147 | 13.21 | 5 |
| RQ-D9 | completed | REFUTED | 126,190 | 20.39 | 6 |

## 2. 데이터 — 분모 사슬

**66 observation dirs → 59 attempted targets → 56 evidence-bearing → 53 MEASURED landing rows → 31 task rows. joint-valid(A+B+C) = 0 / 56 landing rows — Axis A 0행 · Axis B NED 전량 null 이기 때문.**

| 단계 | 값 | grain | tier |
|---|---|---|---|
| observation_dirs | 66 | observation dirs (raw evidence) | T2 |
| attempted | 59 | attempted targets / 66 observation dirs | T2 |
| evidence_complete | 56 | evidence-bearing targets / 59 attempted targets | T2 |
| in_landing_mart | 56 | targets with a landing mart row / 59 attempted targets | T3 |
| measured | 53 | landing rows measurement_status=MEASURED / 56 landing mart rows | T3 |
| in_task_mart | 31 | targets with a task mart row / 56 landing mart targets | T3 |

| 항목 | 값 | tier |
|---|---|---|
| silently dropped (mart 어디에도 없음) | 3 / 59 attempted targets | T2 |
| landing 있는데 task row 없음 | 25 / 56 landing mart targets | T3 |
| **joint-valid (A+B+C 동시)** | **0 / 56 landing mart rows** | T3 |
| Axis C 단독 가용 | 56 / 56 landing mart rows | T3 |

joint-valid=0 인 이유 — Axis A 는 0행이고 Axis B 의 NED 는 31 task rows 전부 null 이다. 교집합은 정의상 0 이며, 이것은 '세 축이 모두 실패했다'가 아니라 '두 축이 아직 산출되지 않았다'는 뜻이다.

누락 target(wtg): `2cd43b99c1ed87cf, dd5061eb74e2d4d4, ff3ee504792f6cfc`

### missingness (T3)
**task_mart_rows_31**
| field | missing | total | missing rate |
|---|---|---|---|
| NED | 31 | 31 | 1.0 |
| IED | 31 | 31 | 1.0 |
| MPFED | 31 | 31 | 1.0 |
| endpoint_status | 0 | 31 | 0.0 |
| interaction_archetype | 0 | 31 | 0.0 |

**landing_mart_rows_56**
| field | missing | total | missing rate |
|---|---|---|---|
| max_overlay_coverage | 0 | 56 | 0.0 |
| max_primary_action_occlusion | 0 | 56 | 0.0 |
| primary_action_visible_initial | 2 | 56 | 0.0357 |
| blocking_modal_count | 0 | 56 | 0.0 |

**interrupt_rows_235**
| field | missing | total | missing rate |
|---|---|---|---|
| overlay_coverage | 0 | 235 | 0.0 |
| primary_action_occlusion | 0 | 235 | 0.0 |
| final_label | 0 | 235 | 0.0 |

구조적 결측 — attempted 중 mart 전무 **3** targets · landing 있으나 task 없음 **25** targets

*행 안의 null 보다 '행 자체가 없는 것'이 더 크다. 3 attempted targets 는 mart 어디에도 없고, 25 landing targets 는 task mart 에 없다. mart 를 분모로 쓰면 이 결측이 보이지 않는다.*

### 스키마 함정 (T3)
문자열로 저장된 불리언 필드 **6개**: `fact_task_entry.endpoint_reached`, `fact_task_entry.auth_gate_before_endpoint`, `fact_interrupt_element.blocks_primary_action`, `fact_interrupt_element.dismiss_control_exists`, `fact_interrupt_element.dismiss_control_visible`, `fact_interrupt_element.dismiss_succeeded`

> 이 필드들은 JSON bool 이 아니라 문자열 "0"/"1" 로 저장돼 있다. 파이썬에서 "0" 은 truthy 이므로 `if row[f]:` 로 세면 **전건이 True 로 집계된다**. 이 대시보드의 첫 실행이 정확히 그 오류로 endpoint_reached 를 31/31 로 냈고, as_bool() 을 넣어 0/31 로 시정했다. 같은 mart 를 읽는 다른 소비자도 같은 함정에 빠진다.

> fact_landing_observation.primary_action_visible_initial 은 int 0/1 인데 fact_task_entry.endpoint_reached 는 str "0"/"1" 이다 — 한 mart 안에서 불리언 표현이 통일돼 있지 않다.

mart provenance (T3) — frozen at `2026-08-27T16:25:42+09:00` · declared vs actual sha256 전건 일치: **True**

## 3. RF detector

**detector 성능(macro F1 · abstention · unsafe FP)은 전부 NOT_AVAILABLE — W2 detector 평가 run 이 아직 없다. 분할 크기(cal/hold)만 C 의 라벨 run 에서 읽힌다.**

| 지표 | 값 | tier | 왜 없는가 |
|---|---|---|---|
| calibration coverage | 30 / 56 frozen labeled targets | T5 |  |
| holdout coverage | 26 / 56 frozen labeled targets | T5 |  |
| macro F1 | **NOT_AVAILABLE** | T5 | RF detector 의 macro F1 을 담은 run 이 없다. W2(claude-b/w2-rf-detector)는 RUNNING 이고 attestation 대기 중이라 아직 평가 run 을 내지 않았다. LA_03_RF_MAPPING 의 RQ-D3A macro F |
| abstention | 14 / 56 frozen labeled targets | T5 |  |
| unsafe FP | **NOT_AVAILABLE** | T5 | unsafe false positive 를 세려면 detector 예측과 gold label 을 대조해야 한다. detector 평가 run 이 없고, gold label 대조는 C 영역이다 — D 가 계산할 수 없다. |

> **holdout 경계** — holdout 은 C 영역이다. D 는 LABEL_SPLIT_FROZEN.json 과 control/label/** 를 열지 않는다. 여기 있는 값은 C 가 MLflow 에 남긴 요약 metric 이며, D 가 라벨을 읽어 센 값이 아니다.

> **abstention grain** — 이 값은 **라벨러**의 abstain 이다(run C_LABEL_freeze_and_overlap_verification). detector 의 abstention rate 가 아니다. 둘을 같은 칸에 놓으면 안 되므로 grain 에 명시했다.

### LA_03_RF_MAPPING run index (T5)
| run | plane | status | verdict | metric 수 |
|---|---|---|---|---|
| D-RF-001-C embedding_prototype | D | COMPLETED | PARTIALLY_SUPPORTED | 118 |
| C_W2_contamination_forensic_f76ee8b | C | FINISHED |  | 5 |
| C_holdout_contamination_register_v2_full_exposure | C | FINISHED |  | 6 |
| C_holdout_contamination_register | C | FINISHED |  | 5 |
| C_LABEL_freeze_and_overlap_verification | C | FINISHED |  | 13 |
| RQ-D-RF-001 | D | RUNNING | PENDING | 0 |
| RQ-D3A | D | COMPLETED | NOT_SUPPORTED | 16 |
| RQ-D3A | D | SUPERSEDED | PENDING | 16 |

## 4. KWCAG (Axis A)

**Axis A = NOT_EVALUATED. criterion 0행 / 56 landing rows — 비율은 정의되지 않는다.**

| 지표 | 값 | tier | 왜 없는가 |
|---|---|---|---|
| decidable count | **NOT_EVALUATED** | T3 | fact_criterion_result.json 이 0행이다(파일 2 bytes = []). 평가기가 돌아서 '위반 없음'을 낸 것이 아니라 **평가가 실행되지 않았다**. W3(claude-b/w3-kwcag) Stage 1 evaluator 가 아직 산출 전이다. |
| DecisionCoverage | **NOT_EVALUATED** | T3 | fact_criterion_result.json 이 0행이다(파일 2 bytes = []). 평가기가 돌아서 '위반 없음'을 낸 것이 아니라 **평가가 실행되지 않았다**. W3(claude-b/w3-kwcag) Stage 1 evaluator 가 아직 산출 전이다. |
| UNDET | **NOT_EVALUATED** | T3 | fact_criterion_result.json 이 0행이다(파일 2 bytes = []). 평가기가 돌아서 '위반 없음'을 낸 것이 아니라 **평가가 실행되지 않았다**. W3(claude-b/w3-kwcag) Stage 1 evaluator 가 아직 산출 전이다. |
| criterion-level failures | **NOT_EVALUATED** | T3 | fact_criterion_result.json 이 0행이다(파일 2 bytes = []). 평가기가 돌아서 '위반 없음'을 낸 것이 아니라 **평가가 실행되지 않았다**. W3(claude-b/w3-kwcag) Stage 1 evaluator 가 아직 산출 전이다. |

> **오독 방지** — 0행을 '0% 실패' 또는 '전부 통과'로 읽으면 안 된다. 분자도 분모도 존재하지 않는다. 비율은 정의되지 않는다.

criterion result rows = **0** · dim_certification rows = **0** (frozen mart, T3)

## 5. Depth (Axis B)

**NED/IED/MPFED 전부 0 / 31 task rows — 세 depth 지표 모두 NOT_AVAILABLE. endpoint_reached 0 / 31 task rows. UNRESOLVED 18 행은 종료 사유 미기록.**

| 지표 | 값 | tier | 왜 없는가 |
|---|---|---|---|
| NED available | **NOT_AVAILABLE** | T3 | NED 는 31 task rows 전부 null 이다. 값이 '깊이 0'인 것이 아니라 필드가 채워진 적이 없다 — endpoint detector 미배선. |
| MPFED available | **NOT_AVAILABLE** | T3 | MPFED 는 31 task rows 전부 null 이다. 값이 '깊이 0'인 것이 아니라 필드가 채워진 적이 없다 — endpoint detector 미배선. |
| IED available | **NOT_AVAILABLE** | T3 | IED 는 31 task rows 전부 null 이다. 값이 '깊이 0'인 것이 아니라 필드가 채워진 적이 없다 — endpoint detector 미배선. |
| endpoint reach | 0 / 31 task rows | T3 |  |

### endpoint_status 분포 (T3, 분모 31 task rows)
| endpoint_status | task rows |
|---|---|
| UNRESOLVED | 18 |
| AUTH_GATE_REACHED | 11 |
| CAPTCHA | 1 |
| PAYMENT_GATE_REACHED | 1 |

auth gate before endpoint: 15 / 31 task rows

archetype coverage 6/7 — 부재: `['QUERY']` (frozen archetype 7종 중 QUERY 만 task mart 에 0행이다. archetype coverage 6/7.)

> **읽는 법** — endpoint_reached=0/31 은 '도달 실패 관측 31건'이 아니라 '31 task rows 중 도달을 기록한 행이 없다'다. UNRESOLVED 18 은 왜 끝났는지가 기록되지 않은 행이라 실패 사유로 셀 수 없다.

## 6. Axis C — overlay · occlusion · interrupt

**overlay coverage 56/56 landing rows 가용 · semantic DETERMINISTIC 125/235 interrupt rows (0.5319) · task-bound occlusion 은 NOT_AVAILABLE (page-level 값만 존재).**

| 지표 | 값 | tier | 비고 |
|---|---|---|---|
| overlay coverage available | 56 / 56 landing mart rows | T3 | median 0.1318 · max 1.0 |
| semantic classified rate | 0.5319 (125/235 interrupt element rows) | T3 | classification_status=DETERMINISTIC |
| UNKNOWN label share | 0.4681 (110/235 interrupt element rows) | T3 | final_label=UNKNOWN |
| **task-bound occlusion** | **NOT_AVAILABLE** | T3 | max_primary_action_occlusion 은 56/56 landing rows 에 값이 있으나 **task binding 없이** 계산됐다. task 가 정한 primary action 이 아니라 page |
| page-level occlusion | 56 / 56 landing mart rows | T3 | PAGE-LEVEL ONLY |
| observations with interrupts | 51 / 56 landing mart rows | T3 |  |
| blocks_primary_action | 74 / 235 interrupt element rows | T3 | page-level |
| dismiss control exists | 103 / 235 interrupt element rows | T3 |  |

> **유효 범위** — primary_action_occlusion 은 **page-level 로만 유효하다**. task 별 primary action 이 결정되기 전에 계산된 값이므로 task-bound 해석을 붙이면 안 된다.

| classification_status | rows | 분모 |
|---|---|---|
| DETERMINISTIC | 125 | 235 interrupt rows |
| NOT_CLASSIFIED | 69 | 235 interrupt rows |
| AMBIGUOUS | 41 | 235 interrupt rows |

## 7. D Research

**OPEN RQ 9 / 16 queue rows · D runs running 1 · supported 5 / refuted 3 / inconclusive 3 (settled D verdicts 12)**

| 항목 | 값 | tier |
|---|---|---|
| open research questions | 9 / 16 RQs in queue | T5 |
| experiments running | 1 / 15 D-plane runs | T5 |
| supported (+partially) | 5 / 12 D runs with a settled verdict | T5 |
| refuted (+not supported) | 3 / 12 D runs with a settled verdict | T5 |
| inconclusive (+not testable) | 3 / 12 D runs with a settled verdict | T5 |

> verdict 는 D 자신이 붙인 tag 다(T5). C 검증을 통과했다는 뜻이 아니다. D run 의 authority_status 는 전부 NON_CANONICAL 이다.

**latest high-impact finding** — `D-DASHBOARD` verdict **NOT_TESTABLE** (run `c2beeb9d5f23`, 2026-08-27T22:14:09.408088+09:00)

> limitation: 대시보드는 가설을 검정하지 않는다 — 상태 스냅샷이므로 verdict 는 NOT_TESTABLE 이다. 한계: (1) open P0/P1 은 ack/completion **파일 존재**로만 판정하며 내용상 해소 여부는 보지 않는다. (2) active runs 는 MLflow tag 이므로 프로세스가 죽어도 RUNNING 으로 남는다 — 생존 증거가 아니다. (3) RF detector 의 macro F1·unsafe FP 와 KWCAG 전 지표는 입력이 없어 NOT_AVAILABLE/NOT_EVALUATED 이며 추정하지 않았다.

### queue (T5)
| RQ | state | 질문 |
|---|---|---|
| RQ-D1 | DONE | E001 파일럿 failure anatomy 재구성 |
| RQ-D1b | OPEN | LONG 3건의 종료 사유를 runner 로그에서 직접 확인 (timeout/WAF/navigation) |
| RQ-D1c | OPEN | total-failure 3 target의 서비스 정체·archetype prior → 결측 편향 크기 |
| RQ-D2 | OPEN | target-level guard 25건이 observability·archetype coverage를 얼마나 왜곡했는가. QUERY n=0의 원인 |
| RQ-D3 | RUNNING | Representative Function Mapping DT feasibility (rule DT가 어디까지 닫히는가) |
| RQ-D3A | DONE | Learned DT 진단 — L0 numeric feature 가 archetype prior 를 되찾는가 |
| RQ-D-RF-001 | RUNNING | RF mapping 다방법 병렬 공격 — parent run `2bf780a9` @ LA_03_RF_MAPPING |
| RQ-D4 | OPEN | URL_PATTERN / DOM_AX_ROLE / FORM_STRUCTURE endpoint signal feasibility |
| RQ-D5 | OPEN | Axis C raw의 즉시 재사용 범위와 task-specific occlusion의 한계 |
| RQ-D6 | OPEN | partial NED 보존 미구현이 detector 결함과 독립인가 (RQ-D1 F6 파생) |
| RQ-D7 | OPEN | mart의 조용한 분모 손실(59→56→31)이 계획된 association 추정에 주는 영향 상한 |
| RQ-D8 | DONE | `T-B-RQ-D-001 Q1` — l0_probe cap 절단이 interaction_archetype에 편향돼 있는가. ExcessDepth의 same-archetype median baseli |
| RQ-D9 | DONE | `T-B-RQ-D-001 Q2` — dom.html 크기 · probe 신호 풍부도 · cap 도달의 관계 구조. 관측품질 대리변수는 무엇이 될 수 있고 무엇이 될 수 없는가 |
| RQ-D10 | DONE | `T-B-RQ-D-001 Q3` — evidence slot 간 시점 불일치(dom/ax = SPA shell vs probe = 렌더 후)를 raw에서 정량화하고 관측단위 지표로 정의할 수 있는가 |
| RQ-D11 | OPEN | 원장(ledger) measured 집합과 evidence run 집합의 불일치가 E001 raw 에서도 관측되는가 — C-BLOCKER-220418 의 구조가 2026-08-27 05:14 w02 |
| RQ-D12 | OPEN | D 의 세 finding(cap 편향 / 품질 대리변수 / slot 불일치)이 서로 같은 소수 target 에 몰려 있는가 — 세 지표의 결합분포와 공통 원인 가설 \| RQ-D8·D9·D10 교차 |

### claim ledger — D 가 재계산한 타 plane 주장 10건 (T2)
| verdict | claims |
|---|---|
| SUPPORTED | 4 |
| PARTIALLY_SUPPORTED | 3 |
| REFUTED | 2 |
| NOT_SUPPORTED | 1 |

**REFUTED / NOT_SUPPORTED 된 타 plane 주장**
| claim | 출처 | 주장 | D 재계산 |
|---|---|---|---|
| CL-008 | SSOTV2/02 §6 | replay 모집단 = mart referenced 56 | 누락 3건 = LONG 재시도실패 3건과 동일 집합 |
| CL-009 | SSOTV2/08 | control/landing-orchestrator = 084eff54 | 실측 d8f8595c |
| CL-010 | Research Director | SSOTV2가 단일 SSOT | 전부 untracked (?? SSOTV2/) |

## 8. C Assurance

**C MLflow runs 15 — MATCH 5 / MATCH_WITH_NONBLOCKING_DIFFERENCE 5 / result-affecting+systemic mismatch 5. C completions 13 (severity C1 1 · C0 없음). reproduced D findings: 1 (그중 D_CONFIRMED/MATCH 1)**

| 항목 | 값 | tier |
|---|---|---|
| MATCH | 5 / 15 C-plane runs | T5 |
| result-affecting + systemic mismatch | 5 / 15 C-plane runs | T5 |
| C completions severity C1 | 1 / 13 C completions | T4 |
| C completions severity C0 | **NONE_YET** | T4 |
| **reproduced D findings** | 1 C-plane MLflow runs that independently recomputed a D finding | T5 |

**C 가 독립 재계산한 D finding** (T5)
| C run | D hypothesis | C 방법 | match | d_verdict | 차이 |
|---|---|---|---|---|---|
| C_D_F_Q1_cap_bias_replication | D-F-Q1 | own recount + scipy fisher (no D code) | MATCH | D_CONFIRMED | none |

> C 의 재현은 D 코드를 쓰지 않은 독립 재계산(evidence_status=INDEPENDENT_RECOMPUTATION)이다. 그래도 이것은 T5 근거(MLflow tag)이며, D run 의 authority_status 를 바꾸지는 않는다 — 승격은 A 의 A_ACCEPTED 결정이 필요하다.

| match_status (MLflow) | C runs |
|---|---|
| MATCH | 5 |
| MATCH_WITH_NONBLOCKING_DIFFERENCE | 5 |
| RESULT_AFFECTING_MISMATCH | 3 |
| SYSTEMIC_MISMATCH | 2 |

| C run | match_status | severity | difference |
|---|---|---|---|
| C_W1_guard_fixture_scoring_860e4e8 | RESULT_AFFECTING_MISMATCH | P1 | CAPTCHA semantics inverted vs D-R0-05; vocab gate pending W2 |
| C_W2_contamination_forensic_f76ee8b | MATCH | P0 | none |
| C_W4_rework_final_replay_b27794f | MATCH_WITH_NONBLOCKING_DIFFERENCE | P3 | transition table population: C 22/635(all candidates) · C 20/192(mart  |
| C_D_F_Q1_cap_bias_replication | MATCH | P3 | none |
| C_holdout_contamination_register_v2_fu | SYSTEMIC_MISMATCH | P0 | holdout independence unrecoverable; C prior 18-primary withdrawn |
| C_W1_e2e_ledger_attribution_split | RESULT_AFFECTING_MISMATCH | P1 | loser-process ledger seal crashes; winner-measured targets recorded as |
| C_W4_rework_form_semantic_precheck | MATCH_WITH_NONBLOCKING_DIFFERENCE | P3 | semantic vocab reuses PROMOTION_MODAL name (P3) |
| C_holdout_contamination_register | SYSTEMIC_MISMATCH | P0 | holdout independence assumption violated for 8 (3 reached detector pro |
| C_gate_observed_vocab_fp_verification | MATCH | P1 | regex also includes english terms; 8/12 zero-step new |
| C_W1_exactly_once_race_and_e2e | MATCH_WITH_NONBLOCKING_DIFFERENCE | P3 | proc2 post-hoc BatchOverwriteError rc=1 (P3) |
| C_W4_axisc_artifact_and_classifier_dif | RESULT_AFFECTING_MISMATCH | P2 | semantic labels 22/635 collapsed to BANNER (D-R0-58 rework) |
| C_LABEL_freeze_and_overlap_verificatio | MATCH_WITH_NONBLOCKING_DIFFERENCE | P0 | L2 decision_trace empty 3; holdout exposure P0 raised separately |
| C_W3_stage0_manifest_verification | MATCH | P2 | SHA field is commit sha not content sha (P3) |
| C_R0_QA_recovery_audit_replay | MATCH | P2 | S-10 qualifier archetype-level 7 distinct; S-13 self-correction |
| C_CLEAN0_retention_manifest_rehash | MATCH_WITH_NONBLOCKING_DIFFERENCE | P4 | total_files unit: A excludes manifest.jsonl/run.json |

---

이 대시보드는 **NON_CANONICAL** 이다. D plane 산출물이며 GO 권한이 없다. MLflow run: `eb3f5704646d41948c9bc0fd23576deb`
