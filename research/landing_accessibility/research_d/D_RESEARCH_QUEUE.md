# D Research Queue

> **상태 어휘 (2026-08-28 정합)** — `RUNNING` 은 **실제 프로세스가 있을 때만** 쓴다.
> 없으면 넷 중 하나다: `CLOSED_WITH_FINDING`(게이트 통과 + 티켓 발행) ·
> `ARTIFACTS_PRESERVED_GATE_NOT_PASSED`(산출 보존, 완결 주장 없음) ·
> `HALTED_INCOMPLETE_GATE`(산출 있음, 게이트 미통과) · `SUPERSEDED_BY_CHILDREN`.
> 근거: `results/D_QUEUE_STATE_RECONCILIATION.json` (게이트 실행 결과 + 발행 티켓 대조).
> 이전 표기는 9행이 `RUNNING` 이었고 워커는 0개였다.


우선순위는 production critical path를 막지 않는 선에서, **분모·타당성에 영향이 큰 것**부터다.

| RQ | 질문 | 상태 | 산출 |
|---|---|---|---|
| **RQ-D1** | E001 파일럿 failure anatomy 재구성 | **DONE** | `results/RQ_D1_FINDINGS.md`, `results/RQ_D1_reconstruction.json` |
| RQ-D1b | LONG 3건의 종료 사유를 runner 로그에서 직접 확인 (timeout/WAF/navigation) | OPEN | — |
| RQ-D1c | total-failure 3 target의 서비스 정체·archetype prior → 결측 편향 크기 | OPEN | — |
| RQ-D2 | target-level guard 25건이 observability·archetype coverage를 얼마나 왜곡했는가. QUERY n=0의 원인 | OPEN | — |
| RQ-D3 | Representative Function Mapping DT feasibility (rule DT가 어디까지 닫히는가) | **SUPERSEDED_BY_CHILDREN** | RQ-D-RF-001 로 확장 |
| **RQ-D3A** | Learned DT 진단 — L0 numeric feature 가 archetype prior 를 되찾는가 | **DONE** | `results/RQ_D3A_learned_dt.json` **NOT_SUPPORTED** (logreg macroF1 0.271 vs stratified 0.235, CI 겹침) |
| **RQ-D-RF-001** | RF mapping 다방법 병렬 공격 — parent run `2bf780a9` @ LA_03_RF_MAPPING | **SUPERSEDED_BY_CHILDREN** | child A rule DT / B TF-IDF / C embedding prototype |
| RQ-D4 | URL_PATTERN / DOM_AX_ROLE / FORM_STRUCTURE endpoint signal feasibility | OPEN | — |
| RQ-D5 | Axis C raw의 즉시 재사용 범위와 task-specific occlusion의 한계 | OPEN | — |
| **RQ-D6** | partial NED 보존 미구현이 detector 결함과 독립인가 (RQ-D1 F6 파생) | OPEN | — |
| **RQ-D7** | mart의 조용한 분모 손실(59→56→31)이 계획된 association 추정에 주는 영향 상한 | **CLOSED_WITH_FINDING** | `D-V3-FINDING-002` · 노트북 22셀 error 0 · 2026-08-28 14:4x 표 정정 |
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
| RQ-D-RF-001-B | ARTIFACTS_PRESERVED_GATE_NOT_PASSED | TF-IDF (v1 코퍼스 기준) |
| **RQ-D14** | **HALTED_INCOMPLETE_GATE** | frame validity — 수집 URL 이 기능 랜딩인가 기업/앱설치 랜딩인가. parent run `12dc99cc` @ LA_01_FRAME |

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
| **RQ-D15** | **ARTIFACTS_PRESERVED_GATE_NOT_PASSED** — v3 코퍼스(D-DEF-01 인코딩 + D-DEF-04 CSS 둘 다 시정) 기준 NLP 4실험 재현. verdict 격자로 결론 유지 여부 검증 |

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
| **E** slot dependency matrix | 세 축이 공유하는 raw slot 과 correlated measurement error 위험 pair | **CLOSED_WITH_FINDING** — frozen evidence + SSOT + exact-SHA 코드만 필요 |
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
| **RQ-E-1** | dismiss detector 의 `icon_only`(l0_probe.js:402) 조건을 끄면 Axis B activation pool 이 얼마나 회복되는가 | **CLOSED_WITH_FINDING** | E-P1 HIGH, measurable_now=yes |
| RQ-E-2 | Axis A evaluator 생산 후 `dom_aria_label_n` 층별 Axis C 확정률 차이가 유지되는가 | BLOCKED — Axis A 0행 | E-P2 |
| RQ-E-3 | `hittable()` 을 중심점 1점→다점으로 바꾸면 Axis B 후보수와 Axis C `dismiss_control_visible` 이 같은 방향으로 움직이는가 | OPEN | E-P4 식별 |
| RQ-E-4 | SSOT §8.1 의 `DOM_AX_ROLE` region signal 미구현이 Axis B 의 `declared_regions` 의존(실사이트 2/54)의 원인인가 | OPEN | 구조적 사실 (2) |
| RQ-E-5 | AX tree 가 수집되지만 어느 축도 소비하지 않는다 — inert slot 의 범위 | OPEN | 구조적 사실 (2) |

| **RQ-D13b-1/2** | dismissal DOM 효과: H1_NO_EFFECT 53건에 dismiss target 이 실재했는가 / H4_PIXEL_ONLY 37건의 원인 | **CLOSED_WITH_FINDING** | RQ-D13b 파생 |

파일럿 상태: A 가 00:14 에 `MANIFEST_REFROZEN` (v1 `4d3209ca` degenerate → v2 `78f2e32a…`). **캡처 산출물은 아직 없다.**
PILOT child A / B / C-part2 / D 는 `PENDING_PILOT_FREEZE` 유지.

## 2026-08-28 00:35 — RQ-D7 착수

| RQ | 질문 | 상태 | 파생 근거 |
|---|---|---|---|
| **RQ-D7** | 분모 사슬(59→56→31)이 계획된 association 추정에 주는 영향의 상한 — Manski worst-case bound + 결측기전 진단(MCAR vs MAR) | **CLOSED_WITH_FINDING** | RQ-D1 / RQ-D11 / RQ-D13c 분모 사슬 |

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

## 2026-08-28 02:28 — V3_CONTRACT_FROZEN 접수 · Director STANDBY 지시

`T-A-V3-P0-FROZEN` ACK(접수). **D fixture 는 C 가 exact `369cbec` clone 에서 직접 실행해 `D_CONFIRMED`** 로 닫혔다 — 자기보고가 아니라 독립 실행이 근거인 것이 옳다. C 는 자기 fixture 7건을 추가 투입했다.

A 가 D 관련 3건을 판정했다:
- `ruling_11` — grain 처리 방식 수용. "숫자를 방어하기 전에 같은 것을 재고 있는지 묻는 것이 순서다." P3 요구가 **단위/모집단/원천 3축 명시 후 수렴 실증**으로 강화됐다.
- `ruling_12` — endpoint 사전관측 lock 이 **P2 provenance control 로 채택**. C 독립 재현 `D_CONFIRMED`.
- `ruling_9/10` — 경로선택은 도구 파라미터이며 B Scout 도 같은 위험을 갖는다는 일반화. D 가 올린 Axis B 오염 관측과 같은 방향.

### Director STANDBY 지시 (수신)
MAIN50 canonical collection 완료까지 STANDBY. 새 연구를 병렬로 벌리지 않는다.
`PIVOT_DEFERRED_LEGACY` freeze 는 이미 적용돼 있다(OPEN 5 + pilot child 4, 삭제 0).

**하지 않는다**: 새 classifier / task family / endpoint / threshold / composite score / target selection / replacement suggestion / REAL 직접 실행.
**허용**: D 자체 infrastructure defect 의 **최소 범위** 시정. E reconnaissance request(REAL 이면 A-authorized scope 필수 — 현재 E REAL scope 는 0 이고 E 는 실재하지 않는다).

### 보류 결정 — MLflow tracing 계측
`instrumenting-with-mlflow-tracing` 을 열었으나 **착수하지 않는다.** 그것은 결함 시정이 아니라 새 관측 계층 추가이며 STANDBY 범위 밖이다.
기존 `tools/mlflow_contract.py::research_run()` 이 run/tag/param/metric 을 이미 강제하고 있어 지금 부족한 것이 없다.
Step 3(adversarial 분석) 활성화 시 노트북·워커에 span 계측을 넣는 것이 자연스러우므로 그때 재개한다.

### Step 3 활성화 신호
**B canonical MAIN50 mart/evidence freeze + C 의 analysis-ready 확인.** 그 신호가 오면 8축(Spatial/Label/Control/Menu·Reveal/Flow Topology/Depth/Auth/Obstruction) 적대적 분석을 **한 번에** 시작한다. family n=10, 45 pair 를 n=45 로 쓰지 않고, 단일 composite 점수를 만들지 않는다.

## 2026-08-28 02:30 — Director ADDENDUM: 오케스트레이터 전환 · 5 lane 병렬 투입

Director 가 D 를 단독 실행자에서 **ORCHESTRATOR** 로 전환했다. §5 가 명시한다 —
다른 plane 을 기다리는 동안 **outcome-independent 준비는 병렬 수행**한다("B가 mart 생성 중 → D는 analysis harness / counterexample code 준비").
이것이 STANDBY 와 충돌하지 않는 지점이다: 새 *연구* 는 없고, 하네스 *준비* 만 한다.

| Lane | 좁은 책임 | isolated namespace |
|---|---|---|
| **S** | Spatial · Control-form · Menu/Reveal | `tools/v3_harness/lane_s_*.py` · `results/harness/lane_s/` |
| **L** | Label · Accessible Name | `lane_l_*` · `results/harness/lane_l/` |
| **F** | Flow Topology · Depth (**primary outcome 축**) | `lane_f_*` · `results/harness/lane_f/` |
| **A** | Auth timing · Obstruction | `lane_a_*` · `results/harness/lane_a/` |
| **P** | Provenance · 분모 사슬 · Metric redundancy | `lane_p_*` · `results/harness/lane_p/` |

전 lane 공통 계약: base SHA `7448184`, SSOTV3 manifest `1735c956…`, **정의는 codebook 원문 그대로 구현**,
모호하면 채우지 말고 `AMBIGUOUS_DEFINITION` 으로 올림, **threshold·cut-off·composite 금지**,
**45 pair 를 n=45 로 금지**, 합성 fixture **양방향 대조 + 변이 검사**, REAL 접속 0, git 금지, lane 간 파일 접근 금지.

Director 지정 반례 8종을 lane 에 배분했다 — depth 동일/flow 상이·distance 크고 depth 차 0·modal 로 experienced 만 김(F),
visible label 다른데 AX 같음·label 같은데 control type 다름(L, control_type 판정은 S),
위치 같은데 hierarchy 다름(S), auth timing 만 다름(A), 지표 중복(P).

**reconciliation 규칙**: worker completion 을 그대로 canonical 로 채택하지 않는다. source SHA·중복·모순·누락·완결성을
대조한 뒤 통합하고, 두 worker 가 같은 사실에 다른 결과를 내면 조용히 고르지 않고 `RECONCILIATION_REQUIRED` 로 명시한다.

## 2026-08-28 02:43 — STEP 3 worker 로스터 확정 (Director D SUBAGENT MODE)

Director 가 STEP 3 adversarial analysis 의 worker 를 **8개**로 지정했다.
현재 실행 중인 **5 lane 은 하네스 준비**(outcome-independent)이고 STEP 3 분석 worker 와 다른 층이다.
5 lane 을 중간에 쪼개지 않는다 — namespace 를 나눠 exactly-once 로 돌리는 중이라 지금 분할하면 중복 실행이 된다.

### 하네스 lane → STEP 3 worker 매핑

| 현재 하네스 lane | STEP 3 worker | 분할 |
|---|---|---|
| Lane **S** | `D-Spatial` + `D-Control` | **분할** — 좌표/zone 과 control form/menu/reveal/nesting 을 나눈다 |
| Lane **L** | `D-Label` | 1:1 |
| Lane **F** | `D-Flow` | 1:1 (primary outcome 축) |
| Lane **A** | `D-Auth` + `D-Obstruction` | **분할** — auth timing 과 modal/dismissal/occlusion 을 나눈다 |
| Lane **P** | `D-Provenance` + `D-Stats` | **분할** — lineage/분모 감사와 지표중복/불확실성/pseudoreplication 을 나눈다 |

즉 STEP 3 에서 5 → **8 worker** 로 늘린다. 하네스 lane 산출이 각 worker 의 계산기 입력이 된다.

### 고정 규칙 (Director)
- worker 가 찾은 finding 을 **A/B 로 직접 보내지 않는다.** worker → D 본체 → `to=[C]`.
- **하나의 worker 분석을 전체 결론으로 일반화하지 않는다.** D 본체가 construct-level interpretation 을 만든다.
- `D-Stats` 는 pseudoreplication 을 전담한다 — **45 pair 를 n=45 로 쓰지 않는 것**을 코드 수준에서 강제한다.

### reconciliation 하네스
`tools/v3_harness/reconcile_lanes.py` 작성. Director ADDENDUM §3 의 검사를 코드로 고정했다 —
source SHA · namespace 침범 · 필수키/verdict 어휘 · 완결성 · **DUPLICATE_IMPLEMENTATION** · **CONTRADICTION_AMBIGUOUS_VS_IMPLEMENTED**.

빈 상태에서 `NOT_READY`(exit 1)를 내는 것을 확인했고, 탐지기는 **양방향 대조**로 검증했다:
겹침 없는 대조군 0건 / 같은 변수 2 lane 구현 → `DUPLICATE_IMPLEMENTATION` 1건 /
한 lane 모호선언 + 다른 lane 구현 → `CONTRADICTION_AMBIGUOUS_VS_IMPLEMENTED` 1건.
**빈 결과를 정상으로 읽지 않는다** — lane 산출이 없으면 MISSING 이고, cross-lane 0건은 전 lane COMPLETE 일 때만 의미가 있다.

## 2026-08-28 02:45 — MAIN50_FRAME_FROZEN 접수 · D 배정 확인

`T-A-V3-STEP1-FREEZE` (P0) ACK — 역할은 **접수**. A 가 8-phase 를 3-STEP 으로 축약했고 12건 실행은 취소됐다.

**A 의 D 배정**: "STEP 3 적대분석이 본업. **그때까지 C 요청분만.**"
`may_prepare` = analysis harness · counterexample code 를 outcome-independent 하게 준비.
금지 4항: target 선정·교체 관여 / precheck 결과 보고 표본 제안 / REAL 독자 실행 / GO-NO-GO.

→ **Director packet §3 의 P2 family audit 워커를 띄우지 않았다.** frame 이 동결됐다고 D 가 자동으로 감사에 들어가는 것이 아니다. A 배정이 우선이고, 현재 D 는 `may_prepare` 범위의 5 lane 하네스만 돌린다.

MAIN50 해시 2종을 구분해 기록한다 — `manifest_sha256 25ce482d…`(해당 필드 제외 본문) vs `file_sha256 6500adc3…`(파일 전체). 인용 시 어느 쪽인지 명시한다.

12건은 실행 없이 `HISTORICAL_METHOD_ASSURANCE` 로 종결됐다. **실패나 미완으로 서술하지 않는다** — REAL 접속 누적 0건이고 경로가 바뀐 것이다.

### 접근 제약 — `D-V3-FINDING-006` (P2)
D 방화벽이 `control/**` 전체를 denied 로 두므로 **동결 `FINAL_MAIN50_MANIFEST.json` 을 D 가 열 수 없다.**
SSOT 기준 감사는 가능하고(SSOTV3 01 §4·§2 는 allowlist 안), 동결 manifest 기준 감사는 불가능하다.
STEP 3 이나 C 요청 시점에 발견하면 그때 막히므로 지금 올렸다. 선택지 (a) SSOT 기준만 / (b) C 매개 추출 / (c) 파일 단위 예외 —
**D 는 자기 방화벽을 스스로 완화하지 않는다.** 셋 중 무엇을 고를지는 A 권한이고 D 는 선택지만 냈다.

### 발행 결함 1건 (자기검사로 포착)
`D-V3-FINDING-006` 첫 판본에서 heredoc 이 **백틱을 셸 치환**해 경로 문자열 2개가 빈 채로 나갔다.
커밋 메시지에서 같은 함정을 겪고 `git commit -F` 로 바꿨는데 **JSON heredoc 에서 재발**했다.
발행 직후 자기검사로 잡아 같은 `ticket_id` 안에서 정정했다 — 아직 ACK 이 없었고 내용을 채우는 정정이지 판정 변경이 아니다.
**앞으로 티켓 본문은 heredoc 이 아니라 python 으로 쓴다.**

## 2026-08-28 03:02 — R7 확정 · D-V3-FINDING-007 종결 · lane S 수렴 착수

`T-A-V3-STEP1-003` (P0) — A 가 **관측 0건 상태에서 조작적 정의 7건을 사전등록 확정**했다.
그중 `R7 entry_zone` 이 D 가 올린 `D-V3-FINDING-007` 에 대한 판정이다.

| | |
|---|---|
| y 밴드 | `y<1/3 TOP` · `1/3≤y<2/3 MID` · `y≥2/3 BOTTOM` |
| x 삼등분 | **TOP 내부에만** 적용 (codebook 에 `MID_LEFT` 류가 없으므로) |
| 좌표 기준 | bbox 중심 / viewport 390×844, **그 state 기준**(scroll 무관) |
| 구조 override | `FLOATING`·`DRAWER` 가 **기하보다 우선** |

A 의 판정 근거에 동의한다 — **수집에는 blocking 이 아니다.** `04 §6` 이 원좌표 보존을 이미 정했으므로
zone 은 언제든 재도출 가능하고 재수집이 필요 없다. D 의 원 티켓도 blocking 대상을 분석 축으로 한정했지
수집 중단을 요구하지 않았다.

**D 과제 = "lane S 를 R7 정의로 수렴"** → 전담 워커 투입. 요구사항:
기존 `FIXTURE_ONLY_NOT_SSOT` 정책을 **삭제하지 않고** 남겨 두 정책이 갈리는 지점을 대조군으로 확인,
경계값(`y=1/3`·`2/3`, `x=1/3`·`2/3`)과 범위 밖 값 fixture 고정, precedence 양방향 검증,
변이 검사(부등호 뒤집기·MID 에 x 분할·precedence 무시), 기존 fixture 66건 회귀 확인.
R7 이 정하지 않은 것은 채우지 말고 `AMBIGUOUS_DEFINITION` 으로 올리게 했다.

`T-A-V3-STEP1-004` (P0) 접수 — **R8 이 개수 임계값을 만들지 않고 "원인이 우리 쪽에 있는가" 로 가른다.**
"판정이 수를 세는 일이 되면 판정자가 세는 사람이 된다" 는 진술이 D 의 분모 규율과 같은 취지다.
**R9 hard-stop 어휘 8종을 D 도 채택**한다. 특히 `task_contract_drift`(endpoint drift 포함)는
D 가 관측 전에 동결한 endpoint 해시 lock 이 검출하려는 바로 그 실패 양식이다.

`T-A-V3-STEP1-005` · `T-B-V3-DR-001` · `T-B-FC-013` 접수(기록만) — 전부 A 권한 사항.

## 2026-08-28 03:05 — D-V3-FINDING-008 의 blocking 3건 전부 확정 · 워커 3기 병렬

`T-A-V3-STEP1-007` (P0) — A 가 D 가 올린 3건을 **관측 0건 시점에** 전부 닫았다.

| D 가 올린 것 | A 확정 |
|---|---|
| `AD-01` 실패사유 8종 분해 불가 | **R11** — `endpoint_status` enum 은 그대로 두고 동반 필드 `terminal_reason` 추가. "수집 스키마 문제이지 분석 문제가 아니다" 를 A 가 인정 |
| `AMB-F01` 정규화 분모 부재 | **R12** — primary `max(len)`, `sum(len)`·Yujian-Bo 함께 저장. "primary outcome 이 sequence 거리라 이 값 하나가 결과를 바꾼다" |
| `AMB-A4` auth 판정불능 값 없음 | **R13** — `UNDETERMINED` 추가. `NONE` 은 "관측했고 없었다" 는 **적극적 주장**으로 재정의 |

**R13 이 이 세션의 중심 결함군을 한 문장으로 정리했다** — *증거의 부재를 부재의 증거로 적는 것*.
A 가 이를 전 변수로 확장했다: **"어떤 변수든 '없음'을 적으려면 관측했다는 증거가 있어야 한다. 판정불능 값이 없는 변수가 또 있으면 발견 즉시 올려라."**

**R14** — Lane A 가 자기 한계로 적은 "fixture 는 워커가 정의를 읽고 만든 것이라 정의를 오독했으면 fixture 도 같이 틀린다"를
A 가 **구속 조건으로 채택**하고 B 에게도 적용했다. GATE 1 통과 조건: **C 는 B·D 의 fixture 를 쓰지 않고 SSOT 원문에서 자기 fixture 를 파생한다.**

### 병렬 워커 3기
| 워커 | 과제 | 근거 |
|---|---|---|
| Lane S-R7 | `entry_zone` 을 R7 정의로 수렴 | `T-A-V3-STEP1-003` D 배정 |
| Lane X-Converge | **중복 2변수 수렴검사** (`nav_container_depth`·`menu_dependency`) | `T-A-V3-STEP1-007` D 배정 |
| Lane F-Δ9 | `activation_depth` 18종 분류 + 거리 3종을 Δ9·R12 로 수렴 | Δ9 가 Lane F 의 AMB-F01/F03 을 닫음 |

수렴검사에 R14 원칙을 그대로 걸었다 — **두 lane 중 어느 쪽 fixture 도 쓰지 않고 SSOT 원문에서 새로 파생**한다.
한 쪽 fixture 를 쓰면 그 쪽 해석이 정답이 된다. 판정은 `CONVERGED` / `DIVERGED_SAME_AXES` / `DIFFERENT_QUANTITIES` 셋 중 하나이고,
3축(단위·모집단·원천)이 다르면 값이 달라도 불일치가 아니다.

## 2026-08-28 03:14 — R16 접수 · '근거 없는 철회' 를 D 규율에 추가

`T-A-V3-STEP1-009` (P1, Δ12) — **R16: A 판정에 대한 SSOT 독해 반론은 `FACT_CORRECTION` 으로 발행한다.**
근거는 "판정이 마음에 들지 않는다" 가 아니라 **"같은 원문을 읽으면 다른 결론이 나온다"** 여야 한다.

A 가 자기에게도 같은 결함이 더 나쁜 형태로 걸린다고 적었다 — *"B 가 오독하면 C 의 독립 fixture 가 갈리지만,
A 가 오독하면 그것이 정의가 되어 아무것도 갈리지 않는다."* 그래서 **R15: A 판정에 근거 원문 축자 인용 필수.**
Δ9 가 03 §6·04 §5 목록을 그대로 옮겨 "두 제외 목록 어디에도 submit 이 없다" 를 보인 형태가 표준이 됐다 —
**그 인용이 있어야 D 가 대조할 수 있다.**

지금 D 워커 3기가 R7·Δ9·R12 를 각각 SSOT 원문과 대조하며 수렴 중이다. 지시문에 이미
*"아래 요약은 참고일 뿐이고 원문이 다르면 원문을 따른다"* 를 박아 뒀고, 갈리면 R16 경로로 올린다.

A 가 남긴 한계에 동의한다: **"A 와 네 평면이 모두 같은 구절을 같게 오독하는 경우는 이 구조 안에서 잡을 수 없다."**
덮인다고 말하지 않는 것이 맞다.

### D 규율 추가 — 자기철회도 검증한다
`T-B-V3-FINDING-003` (P2) — B 의 worker 가 **하지 않은 잘못을 자기신고**했다. B 가 받아들였다면 정상 작업을 되돌릴 뻔했다.

B 의 진단: 이 세션이 반복해 다룬 결함은 *"증거 없이 주장하는 것"* 이었고 이것은 그 **거울상** 이다.

**D 에게 특히 위험하다.** D 워커들은 자기신고를 자주 하고 D 는 그것을 신뢰도 높은 신호로 받아 왔다 —
Lane S 의 변이 9/10 자기적발, Lane P 의 "중간 판단이 오판이었다" 자기정정. 둘 다 실제로 옳았지만,
**옳았다는 것을 D 가 따로 확인하지 않았다.**

→ 앞으로 D 는 워커의 **자기신고와 자기철회를 같은 강도로 검증**한다. **철회도 주장이고 근거가 필요하다.**
B 가 기억이 아니라 worker 산출물에 박힌 `w5d1` 문자열의 유일성(T1)을 근거로 삼은 것이 옳은 형태다.

## 2026-08-28 03:17 — R17 접수 (철회도 주장이다)

`T-A-V3-STEP1-010` (P1) — A 가 B 의 `T-B-V3-FINDING-003` 을 **R17** 로 규약화했다.

> **철회는 주장과 같은 수준의 근거를 요구한다.** "내가 틀렸다" 는 "내가 맞다" 와 같은 검증을 거친다.
> 자기정정을 낼 때 **어떻게 알았는지**를 함께 낸다 — 기억·인상·재구성은 근거가 아니다.
> 받는 쪽은 자기신고를 **액면가로 수용하지 않는다.** 원 기록과 대조한 뒤 수용한다.

D 는 직전 사이클에 같은 규율을 자기 대장에 이미 넣었다. R17 이 그것을 전 평면 규약으로 만들었다.

**D 의 과거 자기정정을 R17 형식으로 되짚으면** — `D-FACT_CORRECTION-001`(mojibake 를 수집기 결함으로
오귀속했다가 철회)의 "어떻게 알았는가" 는 왕복 검증 `title.encode("latin-1").decode("utf-8")` 이 한국어를
복원한 것이었고 **T1** 이다. 근거가 있었다.

반면 **`D-DEF-01` 의 메커니즘 서술**은 그 왕복 검증이 뒷받침하지 않는 부분까지 단정했다.
Lane L 이 반례를 냈고 D 가 실물 60건으로 재검사해 **UNCONFIRMED** 로 내려갔다
(`D_DEF_01_charset_mechanism_reexamination.json`). **조치는 유효하고 서술만 미확인이다.**
R17 의 형식이 처음부터 있었으면 그 구분이 남았을 것이다 —
"조치의 근거" 와 "메커니즘 설명의 근거" 는 같은 증거로 뒷받침되지 않는다.

## 2026-08-28 03:20 — 수렴검사 모호성 5건 중 3건이 A 판정으로 닫혔다

`D-V3-FINDING-009` 가 올린 `AMB-X01~X05` 를 A 의 두 판정과 대조했다.

| D 모호성 | A 판정 | 상태 |
|---|---|---|
| `AMB-X01` SWITCH_TAB 이 reveal 토큰인가 | **STEP1-011 P-06** — 아니다. `menu_dependency 0` | **닫힘** |
| `AMB-X03` 'task control 노출' 시점 식별 규칙 부재 | **STEP1-012 GAP-07** — 행이 자기 시점을 선언한다(`entry_observed_state`) | **닫힘** |
| `AMB-X04` 형제 reveal 계수 (양쪽 flat count) | **GAP-06** — innermost + `nav_container_chain` 저장 | **닫힘**(chain 이 있으면 nested/sibling 을 사후에 가른다) |
| `AMB-X05` 빈 sequence·ABSTAIN 에서 확정 False/0 | **GAP-04** — 수치 미관측은 `null`, 범주는 `UNDETERMINED`/`NOT_OBSERVED` | 닫히는 **방향** |
| `AMB-X02` nav depth 에 endpoint cut 적용 여부 | — | **열림** |

**`AMB-X02` 는 닫히지 않았다. 닫혔다고 적지 않는다.**

`AMB-X01` 이 닫힌 방식이 특히 눈에 띈다 — D 의 FX13 갈림이 정확히 그 질문이었고, D 는 **어느 구현도 canonical 로
선언하지 않은 채** 두 값을 나란히 올렸다. A 가 C 독해를 축자 인용과 함께 채택하자 두 구현의 **정렬된 읽기가
이미 그 답(False)** 이었음이 드러났다. D 의 변이검사 `MUT03` 이 "어느 쪽이 SWITCH_TAB 을 채택하면 잡히는가" 를
미리 확인해 둔 지점이기도 하다 — reconciliation 이 실수로 병합할 수 있었던 곳이 정의로 닫혔다.

### `T-B-BLK-011` — SSOTV3 가 git 에 전혀 없다
B 가 대조군과 함께 확인했다. **MANIFEST 20/20 은 지금 이 순간의 무결성을 주지만 버전 신원을 주지 않는다.**
네 평면의 독립 0/20 일치와 "어제도 같은 바이트였는가" 는 다른 질문이다.
B 가 *"변조됐다고 주장하지 않는다. 변조되지 않았음을 증명할 구조가 없다고 말한다"* 로 가른 것이 정확하다.

D 가 낼 수 있는 것은 **부분 완화 하나의 사실 보고**뿐이다 — `D_V3_ENDPOINT_PREOBSERVATION_LOCK.json` 이
관측 전에 endpoint 원문 바이트를 sha256 으로 고정해 D 브랜치에 커밋돼 있다. **endpoint 문구에 한해서는**
시점 있는 신원이 있다. SSOTV3 전체의 provenance 를 대신하지 못한다. 커밋 위치는 A 결정이며 D 는 의견을 내지 않는다.

### 전달 경로가 결함원이 되는 형태가 두 평면에서 같이 나왔다
B 가 R7 을 W5C 에만 전달하고 W5E 에는 누락한 것을 자진 신고했다(R17 형식).
D 도 같은 실패를 냈다 — `D-DEF-12`, 워커 간 **입력 모듈 의존성**을 분할 계약에 넣지 않았다.
출력 namespace 분리만으로는 부족하다는 것이 두 번 확인됐다.

## 2026-08-28 03:25 — 워커 3기 전부 완결 · BLK-011 재대조 · R16 첫 FACT_CORRECTION

| 워커 | verdict | 요지 |
|---|---|---|
| Lane S-R7 | `CONVERGED_WITH_AMBIGUITY` | 경계 37/37 · precedence 39/39 · 변이 10/10 · 기존 66건 무손상. **AMB-S14 = R7 자기모순** |
| Lane F-Δ9 | `CONVERGED_WITH_AMBIGUITY` | 회귀 202/202 무손상(+102 = 304/304) · 변이 11/11. AMB-F01·F03 닫힘 |
| Lane X-Converge | `DIFFERENT_QUANTITIES` | `menu_dependency` CONVERGED, `nav_container_depth` 축 불일치 |

### `D-V3-FACT_CORRECTION-001` — R16 하에 D 의 첫 반론
`thresholds.y_bands`(`1/3 ≤ y < 2/3 → MID`)와 `boundary_rule`("정확히 1/3 인 점은 TOP")이 **y=1/3 에서 다르다.**
x 축은 두 진술이 일치한다. **D 가 티켓 원문을 직접 열어 확인했고 어느 쪽도 canonical 로 선언하지 않았다.**
boundary_rule 이 x 만 말하려던 것일 수 있으나 문면은 축을 한정하지 않는다 — **의도를 추정하지 않는다.**
라우팅은 A6 대로 `to=[C] cc=[A]`.

### 변이검사가 못 잡은 결함을 독립 재도출이 잡았다 — R14 실증
Lane S 에서 precedence 결함(DRAWER 미결 + FLOATING 확정 → FLOATING 반환, 20 입력조합)이
**fixture 60/60 green · 변이 8/8 검출 상태에서 살아 있었다.**
잡은 것은 티켓 원문에서 코드 공유 없이 두 번째로 구현한 대조뿐이다.
**변이검사는 fixture 가 이미 묻는 것만 건드린다.** D 의 5 lane 전체가 같은 한계를 갖는다.

### BLK-011 재대조
A 가 SSOTV3 를 `control/v3/ssot_snapshot/` 에 커밋(`cad8ad45`)해 해소했고 전 평면에 재대조를 지시했다.
D 독립 재계산: **스냅샷 22 파일 vs 원본 바이트 불일치 0 · 매니페스트 20/20 · self-sha `1735c956…` 일치 · lapse CLEAN.**
방화벽 예외는 **A 지시를 granted_by 로** 확장했고(스스로 넓힌 것이 아니다), 스캐너의 디렉터리 예외 매칭을
`/**` 항목에 한해 슬래시 경계로 정확히 비교하도록 고쳐 **위장 형제 디렉터리(`ssot_snapshot_evil`)는 계속 막히는 것**을 대조군으로 확인했다.

A 의 honest_limit 에 동의한다 — **지금부터의 provenance 이지 01:52 이후 불변의 증명이 아니다.**
파일과 매니페스트를 함께 바꾸면 이 검사들은 전부 통과한다. **변조 창을 좁히는 정황이지 증명이 아니다.**

**열린 결정 2건**: `AMB-S14`(y=1/3) · `AMB-X02`(nav depth 에 endpoint cut 적용 여부).

## 2026-08-28 03:30 — AMB-S14 닫힘 · D-DEF-13 이 B 로 전파됨

**A 가 `D-V3-FACT_CORRECTION-001` 을 수용했다** — *"D 가 옳다. A 의 판정 두 문장이 서로 달랐다. y=1/3 은 MID 다."*
밴드 표가 정본이고 `[a,b)` 를 두 축에 균일 적용한다. 절단값 자체는 안 바뀌고 경계 귀속만 명확해졌다.
**Lane S 가 이미 그 읽기를 구현하고 있어 재수렴 없이 `AMB-S14` 가 닫힌다.**
구현하지 않은 읽기(TOP)도 나란히 남겨 뒀으므로 대조는 그대로 재현 가능하다.

B 도 `T-B-FC-014` 로 같은 모순을 독립 발행했다 — **두 평면이 서로의 티켓을 보지 않고 같은 문장 쌍에 도달했다.**
R16 이 의도한 검출 구조가 작동한 사례다.

### `D-DEF-13` 이 B 로 전파됐다
`T-B-V3-FINDING-004` — B 가 D 의 결함 보고를 읽고 **자기 ACK 116건을 세어봤다. 전부 티켓 해시가 없다.**
같은 결함이 두 평면에 있었고, D 가 자기 것을 먼저 찾아 올린 것이 B 의 점검을 촉발했다.

D 쪽 처리는 그대로다 — **소급 기입 거부**(거짓 증명이 되고 교체 사실이 지워진다),
옛 ACK 은 `ACKED_SHA_UNRECORDED` 로 정직하게 남기고, 신규 ACK 부터 `ticket_sha256` 을 싣는다.

### 열린 것
- `AMB-X02` — nav depth 에 endpoint cut 적용 여부 (유일하게 남은 수렴검사 모호성)
- `T-A-V3-FC-001` 교체 처리 (`D-V3-FACT_CORRECTION-002` 로 올림, A 판정 대기)

## 2026-08-28 03:35 — D-DEF-13 이 R18 로 규약화 · 탐지기가 실제 발화

`T-A-V3-STEP1-014` (P0) — A 가 `error_class: SELF_ERROR` 로 ticket_id 재사용을 인정하고 복구했다.
v1 을 미러본에서 복원해 `T-A-V3-FC-001` 로 되돌리고, v2 를 `T-A-V3-FC-002` 로 재발행했다.

**그리고 `D-DEF-13` 을 `R18` 로 전 평면 규약화했다** — *"id 재사용을 안 하기로 다짐하는 것은 통제가 아니다.
ACK 이 티켓 해시를 들고 있으면 교체가 자동으로 드러난다 — 결함을 막는 것이 아니라 검출 가능하게 만든다."*

**이번 사이클에 그 탐지기가 실제로 발화했다.** 스캔에서 `T-A-V3-FC-001` 이
`** 내용변경 재ACK필요 **` 로 떴다 — D 의 03:28 재ACK 이후 A 가 v1 을 복원하면서 또 바뀐 것이다.
만들고 10분 만에 production 에서 두 번째 교체를 잡았다.

D 가 관측한 이 ticket_id 의 판본 이력을 ACK 에 남겼다:
`v1`(02:12) → D ACK 02:19:59 → `v2`(03:23 교체) → D 재ACK 03:28 → `v1 복원`(현재) → D ACK.
**어느 판본의 ACK 도 지우지 않았다.** 03:28 재ACK 은 무효가 된 것이 아니라 **다른 판본에 대한 것**이었다.

D 노출 집계도 A 에게 그대로 냈다 — 수신 52건 중 sha 기록 3 · 미기록 49 · 불일치 0.
**49건은 "대조 불가"이지 "변조 없음"이 아니다.** B 의 116건과 같은 성질이고 D 도 소급 기입하지 않는다.

### `T-B-BLK-012` — 수집기 구조 공백 2건이 D 하네스의 전제와 맞물린다
- **gap_1 AX 조인 부재** → Lane L 은 `accessible_name` 을 pass-through 로만 다루고 **AX naming computation 을 구현하지 않았다**고 명시했다.
  그 이름을 누가 계산하느냐가 비어 있으면 Lane L 의 `label_relation`·`entry_label_modality` 는 입력을 받지 못한다.
- **gap_2 scroll state 부재** → Lane S 의 `first_visible_scroll_state` 와 GAP-02 판정에 같은 방식으로 걸린다.

D 는 소유·배정에 관여하지 않는다(A 판정 사항). **측정 타당성 관점의 관측만** 남겼다.

### 열린 것
`AMB-X02`(nav depth endpoint cut) — 유일하게 남은 수렴검사 모호성.

## 2026-08-28 03:38 — "lane 별 green ≠ 통합 정확성" 이 세 번째로 관측됐다

`T-B-V3-RECON-002` (cc) — B 가 8 lane 병합에서 인터페이스 불일치 3건을 찾았다.
병합 자체는 충돌 0 · import 전건 성공인데 **Protocol 이름 불일치가 실행 시점 `AttributeError`** 를 낸다.

> *"각 lane 은 자기 Protocol 경계를 fake 로 테스트했고 전부 통과했다. **통과가 겹친다고 연결이 되는 것이 아니다.**"*

이 형태를 D 가 이미 두 번 관측했다. 세 사례를 나란히 둔다 — Wave 1 handoff 의 known limitation 재료다.

| # | 평면 | 무엇이 green 이었나 | 무엇이 안 잡혔나 | 무엇이 잡았나 |
|---|---|---|---|---|
| 1 | D | Lane S fixture 60/60 · 변이 8/8 | precedence 결함(20 입력조합) | **독립 재도출**(코드 미공유 2차 구현) |
| 2 | D | 5 lane 각각 `READY_WITH_AMBIGUITY` | `nav_container_depth` 중복·축 불일치 | **cross-lane reconcile** |
| 3 | B | 8 lane 전건 통과 · 병합 충돌 0 | Protocol 이름 불일치 → 실행 시 AttributeError | **통합 후 실측** |

공통 구조: **검사의 범위가 곧 보증의 범위다.** fixture 가 묻지 않은 것은 변이도 흔들지 못하고,
lane 안에서 닫힌 것은 lane 경계를 넘지 못하며, fake 로 만족된 Protocol 은 실물 연결을 보장하지 않는다.

세 사례 모두 **worker 완료를 그대로 canonical 로 채택했으면 드러나지 않았다.**
Director ADDENDUM §3 의 reconciliation 이 요구한 것이 정확히 이 층이다.

D 는 이것을 별도 티켓으로 발행하지 않는다 — cc 로 받은 B 산출에서 파생한 종합이고,
Wave 1 handoff 의 `unresolved risks` / `what D explicitly did NOT test` 에 넣는다.

## 2026-08-28 03:46 — R12 소유자 부재 · D 에 참조 구현이 있다

`T-B-V3-SCOPE-001` 에서 B 가 병합본 `v3_runner` 에 **R12 언급 0파일**을 실측했다
(양성대조: R2 4 · R3 4 · R5 5 · R7 3 · R11 1 · R13 1 · R14 1 발화 — 검색은 정상이고 0 은 실제 부재).
**D 는 B 워크트리를 읽지 않으므로 이 수치를 재계산하지 않았다. B 가 확인한 사실이다.**

D 의 Lane F 하네스는 R12 를 이미 구현했다 — primary `max(len)` 단일 스칼라, `sum(len)`·Yujian-Bo 는 저장만.
fixture 로 세 정규화가 실제로 갈리는 것을 고정했다(서로소 pair 에서 **1.0 / 0.5 / 0.667**).

**다만 B 가 D 코드를 가져다 쓰는 것이 최선이 아닐 수 있다.**
R14·R20 이 세운 것 — 같은 독해에서 나온 두 산출의 일치는 정확성의 증거가 아니다.
B 가 복사하면 **D 의 R12 독해가 그대로 production 에 들어가고 그것을 가를 대조가 사라진다.**
대안은 B 가 티켓 원문에서 독립 구현하고 두 구현을 같은 fixture 에서 수렴시키는 것 —
`ruling_11` 이 `dismiss_control_exists` 에 요구했고 D 가 `nav_container_depth`·`menu_dependency` 에
실제로 적용해 본 절차다(`D-V3-FINDING-009`).

D 는 fixture 입력과 기대값을 제공할 수 있으나 **B 가 그것을 보면 독립성이 소멸한다** —
B 가 자기 fixture 를 먼저 만든 뒤 대조하는 순서여야 하고, 순서 결정은 A/C 몫이다.
→ `D-V3-FINDING-010` (P2, `to=[C] cc=[A,B]`)

D 는 소유를 배정하지 않고, D 구현이 정본이라 주장하지 않는다(하네스는 `NON_CANONICAL`).

## 2026-08-28 03:50 — R21 판정 색인이 나왔으나 D allowlist 밖이다

`T-A-V3-STEP1-018` 로 A 가 `V3_RULING_INDEX.json` 을 발행했다.
B 가 낸 구조적 문제를 A 가 자기 결함으로 받은 결과다 —
*"A 가 판정을 티켓으로만 흘려보내고 **정본 목록을 두지 않았다.**
그래서 '무엇이 반영돼야 하는가' 의 단일 출처가 없었고 B 의 전달이 단일 실패점이 됐다."*

**이 문제는 D 에게도 그대로 걸린다.** 지금 D 는 lane 별 `ambiguities_closed` 로만 추적하고 있어
**전체 커버리지를 말하지 못한다** — 어느 ruling 이 D 하네스에 반영됐고 어느 것이 안 됐는지를
단일 목록으로 대조할 수단이 없다. `D-DEF-11/12`(전달 경로 결함)와 같은 계열이다.

파일은 `control/v3/V3_RULING_INDEX.json` 에 있고 **D allowlist 밖이다**
(현재 control 예외는 `FINAL_MAIN50_MANIFEST.json` 2종과 `ssot_snapshot/**` 뿐).

**지금 티켓을 내지 않는다.** A 가 D 에게 색인 사용을 지시하지 않았고(`C: GATE 검증 기준을 색인으로 전환`),
D 의 현재 배정은 "C 요청분만" 이라 **아직 필요가 발생하지 않았다.**
필요가 생기기 전에 예외를 요청하면 그것은 방화벽을 미리 넓히는 것이다.
D 가 커버리지 대조를 요구받는 시점에 `D-V3-FINDING-006` 과 같은 세 선택지
— (a) SSOT 기준만 + limitation 명시 / (b) C 매개 추출 / (c) 파일 단위 예외 — 를 올린다.

이 gap 자체는 `T-A-V3-STEP1-018` ACK 본문에 이미 적어 A 가 읽을 수 있게 해 뒀다.

## RQ-D042 — R60 event_log 읽기 규약 (T-A-V3-STEP1-042)
- 상태: DONE (같은 회차 처리)
- 구현: `tools/d_bus_lib.py` normalize_event / read_event_log / read_event_log_controls
- 통제: must_not_flag 4/4 · must_flag 3/3 · 실측 989행 UNPARSED 0
- 부수 발견: D heartbeat 행이 공유 로그에 0건(색인 공백, 선언함) · 대장 서수 도출 결함(값은 상쇄로 우연히 일치)

## RQ-D043 — D 표지의 거짓 양성 측정 (T-A-V3-STEP1-043 / R61)
- 상태: DONE — 11종 전부 측정 (7종 AST 상수성 / 4종 관측 분포)
- 잔여 4종 결과: firewall verdict PASS 113·FAIL 4(상수 아님) · WIRED True/False 둘 다 관측 ·
  claim_provenance 현 단면 2라벨 · ACK_UNREADABLE 실전 발화 0(합성 대조로 원리 작동 확인)
- **정밀도 산출됨**: 차단(FAIL) 등급 4회 발화 **4회 다 거짓 양성** — 참 양성 0. 분모 = git 117 판본
- 앞 회차 한계진술 정정: '분모를 만들 수 없다' 는 firewall 계열에 대해 거짓이었다(D-DEF-31).
  산출 파일은 덮어써지지만 git 이 판본을 보존한다
- 구조적 분모 부재 2종: claim_provenance(heartbeats/D.json 덮어쓰기 + .agent_bus gitignore) ·
  ACK_UNREADABLE(bus 도구가 산출을 안 남김) — **못 잰 것이 아니라 기록되지 않는다**
- 산출: results/D_FLAG_HISTORY_AUDIT.json
- 남은 축: 표지의 **범위 미표기**(아래 RQ-D044 항목) — 미시정
- (원 등재) 상태: OPEN — 다음 회차
- 질문: D 표지 11종 각각에 must_flag/must_not_flag 가 **실증돼** 있는가, 거짓 양성 이력이 있는가
- 선언 집합(손 선언, 매처 아님): holdout_accessed · production_modified · pushed ·
  denied_paths_not_opened · labels_produced · WIRED · verdict_source · claim_provenance ·
  comparable/changed · ACK_UNREADABLE · firewall verdict
- 주의: 이 중 차단은 firewall verdict 하나뿐이고 나머지는 전부 표지다
- 왜 이번 회차에 안 냈나: 도구를 읽어야 나오는 값이다. 기억으로 표를 채우지 않는다

## RQ-D044 — R65 구조 검사 (T-A-V3-STEP1-044)
- 상태: DONE (같은 회차)
- 결과: D 발행 54건 전건 타평면 ACK 보유 **54/54 · 예외 0** · 두 방법 불일치 0
- 통제: must_flag/must_not_flag PASS · 재ACK 변종 19건 포착 · VACUOUS 아님(54건)
- 산출: results/D_CROSS_PLANE_ACK_AUDIT.json · 도구: d_bus_lib.cross_plane_ack_audit
- RQ-D043 추가 축: 표지가 **범위 없이** 나가는 문제 — `holdout_accessed: False` 는
  정적 스캔 결과인데 그 범위(`접속하는 코드가 없다` ≠ `접속하지 않았다`)를 달고 있지 않다.
  B 의 NO-GO 범위 표현(T-B-V3-HALT-002)이 참고 형식이다.

## 2026-08-28 10:5x — 완결 게이트 셋째 조건 시정 (D-DEF-32)

A 의 v3 역할 티켓이 없어 새 연구를 착수하지 않았다. 허용 항목인 **완결 게이트 마무리**를 했다.

| 축 | 결과 |
|---|---|
| 게이트가 셋째 조건을 재는가 | **아니오** — 노트북 파일 존재만 확인했다 |
| 합성 대조 (시정 전) | 에러 셀 노트북 · 미실행 노트북 · 정상 노트북 **셋 다 gate=True** |
| 실측 14 노트북 | error 0 · 미실행 0 · execution_count 1..N 순차 **14/14** |
| 시정 후 대조군 | 9/9 PASS (must_flag 8 · must_not_flag 1) |
| 회귀 | 새 검사로 막힌 RQ **0건** — 과거 판정 안 뒤집힘 |

**왜 안 보였나**: 조건이 이미 만족돼 있었다. 검사의 부재와 조건의 충족이 같은 출력을 낸다.
R61 의 이면 — 거짓이 된 적 없는 조건은 검사가 없어도 표시가 나지 않는다.

큐 02:14 의 손 기록(RQ-D7 22셀·RQ-D13b12 31셀 error 0)은 실측과 일치했다.
정확했지만 **도구가 강제한 정확성이 아니었다.**

산출: `results/D_COMPLETION_GATE_AUDIT.json` · 티켓 `D-V3-FINDING-032`

## 2026-08-28 11:5x — V3 MAIN50 census 분석 평면 (T-A-V3-TBX-008/022)

A 가 D 를 분석·시각화 평면으로 재배치했다. `NON_CANONICAL` 은 계산·ML·그래프 금지가
아니라 **자기 수치를 최종사실로 승인할 수 없다**는 뜻이라는 지위 정정을 받았다.

| 축 | 결과 |
|---|---|
| 산출 | MAIN50 시간제한 전수관측 보고서 v1 — 그림 4장 |
| mart_pin | `5290e0c306ff…` (C 최종 sha 와 바이트 일치) |
| 분모 | attempted 50 · completed 6 · failed 44 · **unaccounted 0** |
| acquisition 3집단 | USABLE 8 · SITE-SIDE 16 · MEASUREMENT 26 (합 50 · unmapped 0) |
| k | **8 CONFIRMED** (C pre-R3 provenance 8/8) — 8/50 reachability 아님 |
| claim 후보 | 8건 → C |
| MLflow | run `239ed324fae54776840d0c508e8973c7` (LA_07_COLLECTION) |

**D 자기결함 6건** (D-DEF-33~38): data_state 가 골격 50행을 COMPLETE 로 · 표와 sha
비원자적 읽기 · 상태 토큰 목록 뒤처짐 · 대조군 출처 독립성 오판 · 미관측 토큰이
값으로 샘 · 한글 폰트 깨짐이 정상 산출로 보임.

**A 가 채택한 D 관측 3건**: 회차 수치 불일치(A R118 자기정정) · `superseded_runs` 의
`NONE` 이 값이라는 지적(→ R125 'sentinel 목록은 전역이 아니라 컬럼별') · 허용문장
'메뉴의존형도 관측됐다' 가 실측과 반대(→ 선택편향 한계 L13).

우선연구 8개 대조: `spatial dispersion 조작화`(fig2 n=8) · `visible label vs AX`(D02 —
이번 census 산출 불가로 확정) · `action sequence normalization`(단일 스텝이라 미산출) ·
`auth-gate stage variation`(AT_ENDPOINT 2 관측) 네 축이 닿았고, 나머지 넷은 관측 부재.

---

## 2026-08-28 14:45 — 마스터 표 상태 정정 (검사로 잡음)

문서 상단 마스터 표가 **또 뒤처졌다.** 이 문서는 이미 `상태 정리 2026-08-27 23:45
— 큐 표가 stale 했다` 섹션을 갖고 있다. **한 번 고쳤는데 재발했다** — 로그는
계속 쌓이고 표는 손으로 갱신해야 하므로, 고치는 것으로는 재발을 막지 못한다.

그래서 검사로 옮겼다: `tools/d_queue_consistency.py`.

| RQ | 표에 적혀 있던 것 | 실제 | 근거 |
|---|---|---|---|
| **RQ-D7** | `OPEN` | **CLOSED_WITH_FINDING** | `D-V3-FINDING-002` 버스 실재 · `RQ_D7_denominator_bounds.ipynb` 22셀 **error 0 · 미실행 0** |
| **RQ-D13b-1/2** | 로그 292행에 이미 `CLOSED_WITH_FINDING` | 동일 | `D-V3-FINDING-003` 버스 실재 · `RQ_D13b12_dismissal_dom_effect.ipynb` 31셀 **error 0 · 미실행 0** |

노트북 14개 전수 재검 결과 **error 0 · 미실행 0**. 완결 게이트는 실제로 충족돼
있었고 **표기만 뒤처져 있었다** — 이것이 D 가 반복해 잡아온 결함족의 문서판이다.
적힌 것과 실제가 다르고, **적힌 쪽만 보면 통과한다.**

### 검사가 스스로 낸 결함 2건 (발행 전 자체 검출)

1. **대조군이 현재 상태에 묶여 있었다.** 처음엔 "지금 큐가 stale 하다" 를
   must_flag 대조군으로 썼다. 그러면 **문서를 고치는 순간 대조군이 깨진다.**
   검사의 성능이 대상의 상태에 의존해선 안 된다 — 합성 텍스트로 바꿨다.
2. **한 줄의 모든 RQ 에 그 줄의 상태를 귀속시켰다.** `| RQ-D6 | … (RQ-D1 F6
   파생) | OPEN |` 이 RQ-D1 을 OPEN 으로 만들어 **오탐**이 났다(RQ-D1 은 표에서
   `DONE`). 표 행의 주어는 **첫 셀의 RQ** 다.

대조군 7건 PASS (must_flag 3 · must_not_flag 4). 이 검사는 **문서를 자동으로
고치지 않는다** — 상태 판정은 기록이고 덮으면 이력이 사라진다.

---

## 2026-08-28 16:50 — SSOTV3 우선연구 8개 가용성 (등재 아님 · 착수 아님)

`14_PROMPT_D_v3.0.md` 의 우선 연구 8항목이 **현재 census 로 관측되는가**만
대조했다. **A 의 v3 역할 티켓이 없으므로 RQ 로 등재하지 않고 착수하지도 않는다**
(SSOTV3 00 §13 · `T-A-PIVOT-PRESERVE-001`). 새 수치도 새 조작화도 만들지 않았고
이미 계산된 coverage 를 8축에 매핑만 했다.

| 우선연구 | 상태 | 최소 n | 축 |
|---|---|---|---|
| spatial dispersion 조작화 | OBSERVED | **8** | x/y/zone 8/50 |
| visible label vs accessible name 변이 | **PARTIAL** | 0 | visible 29 · **accessible_name 0** · **label_relation 0** |
| icon-only/control-type/reveal-direction taxonomy | **PARTIAL** | 0 | control 27 · **reveal_direction 0** |
| action sequence normalization · edit distance | OBSERVED | 50 | task/experienced flow 50/50 |
| Depth와 sequence divergence 비동일성 | OBSERVED | 50 | depth 50 · sequence 50 |
| auth-gate stage variation | OBSERVED | **8** | auth_gate_stage 8/50 |
| task-specific obstruction | **NOT_OBSERVED_AT_ALL** | 0 | task_control_occlusion **0/50** |
| missingness/slot dependency | OBSERVED | 50 | 전 축 coverage 자체 |

**A 가 알아야 할 것 셋.**

1. **한 항목은 축이 0/50 이라 착수 자체가 불가능하다** — `task-specific
   obstruction`. 데이터가 없지 계기가 없는 것이 아니다.
2. **두 항목은 핵심 축이 0 이다** — `accessible_name` 독립관측 0(C-DEF-39 확정),
   `reveal_direction` 0(UNWIRED). 남은 축만으로는 그 항목이 묻는 **변이**를 볼 수 없다.
3. **`OBSERVED` 는 충분하다는 뜻이 아니다.** spatial 과 auth-gate 는 **n=8** 이다
   — A R106 대로 개별점이지 분포가 아니다. **착수 가능 여부는 A 가 정한다.**

`d_priority_availability.py` · 대조군 6건 · 산출 `analysis/D_PRIORITY_AVAILABILITY.json`

---

## RQ-D-BUS-019/020 — B 티켓 수신 (2026-08-28 17:10 ACK)

| RQ | 출처 | 지위 | 상태 |
|---|---|---|---|
| RQ-D-BUS-019 | `T-B-V3-FINDING-019` (to=D) | B 가 D-071 의 '라벨≠수치' 를 자기 출력에 적용 | **ACK_AND_ANSWER 완료** |
| RQ-D-BUS-020 | `T-B-V3-FINDING-020` (cc=D, to=A) | B 발행분 87건 스키마 전수 감사 | **ACK 완료 — 판정은 A** |

**019 처리.** B 의 자기 지적(`n_keys` 가 '해시 대상 수' 인데 이름은 '키 수')은 수용한다.
다만 **한 문장은 과하다**: '두 평면이 같은 이름으로 다른 수를 보고 있었다'.
D 는 사이드카를 직접 열어 최상위 키를 세고(**34**), B 의 `n_keys` 를 소비하지 않는다.
`D-V3-FINDING-069` 의 `33→34` 는 **블록 추가 전후의 D 자체 계수**이고 B 의 `33` 은
**지금의 34 에서 자기 블록 1 을 뺀 수**다 — 같은 수지만 다른 양이며, 하필 추가된 키가
곧 자기제외 대상이라 겹쳤다. **독립이었으므로 B 의 라벨 결함이 D 수치를 오염시키지 않았다.**

**020 에서 D 가 가져갈 것.** `self_approved` 부재 49건 — '없음' 과 '거짓' 을 같은 출력으로
만들지 말라(Δ15-GAP04). D 발행분에도 같은 축이 있는지 **아직 따로 세지 않았다**.
`d_ticket_schema_check` 는 정본 스키마 대비 필드 부재를 세지만 `self_approved` 만 갈라
보지는 않는다. → **다음 회차 점검 대상** (새 조작화가 아니라 기존 발행분 정합성 점검).

## RQ-D-BUS-021 — `T-B-V3-FINDING-021` (cc=D, to=A) · 2026-08-28 17:22 ACK

B 가 자기 모집단 결함을 정정했다(파일명 glob → `from`). **같은 결함이 D 에 있는지 즉시 쟀다.**

| 축 | D 측정 | 판정 |
|---|---|---|
| 모집단 정의 | `audit_emitted()` 만 `glob("D-*.json")` — 나머지 4개 도구는 `*.json`+`from` | **잠재 결함, 누출 0** (`from==D` 114 = 파일명 `D-*` 114, 차집합 0) |
| 발행기록 | `actor:D` 의 `EMIT`/`TICKET_ISSUED` 대조 → 114 중 **84** | 없는 30건 전부 `06:43:33` 이전, 있는 84건 전부 `07:08:22` 이후 |
| 로그 부재 여부 | `event_log` 최초 `2026-08-27T12:22:35` — 모든 티켓보다 이르다 | **로그가 짧아 생긴 것이 아니다** |
| `created_at` 부재 | **0** | 첫 probe 가 16건으로 셌으나 `created_at` 을 안 본 내 오류였다 |

**D 는 '기록 없음 = 우회 발행' 이라고 말하지 않는다.** 잰 것은 해당 event 줄이 없다는 사실이다.
baseline 경계는 손 목록이 아니라 시각(`EMIT_LOG_SINCE`)이다 — 영구 FAIL 로 신호를 죽이지 않는다(D-DEF-52).

## RQ-D-SELFAPPROVED — `self_approved` 축 (2026-08-28 17:36, `D-V3-FINDING-074`)

앞 회차 등재분 수행. `T-B-V3-FINDING-020` 의 Δ15-GAP04('없음'과 '거짓'을 같은 출력으로
만들지 말라)를 D 발행분에 적용했다.

| 값 | 수 |
|---|---|
| `true` | **0** |
| `false` | 72 |
| **부재** | **43** (전부 `10:02:22` 이전, 가드 이후 0) |
| 이상값 | 0 |

**더 큰 사실**: `self_approved` 는 정본 스키마의 `required` 에도 `properties` 에도 **없다**.
부재는 위반이 아니고, `true 0` 을 정본이 보증하지도 않는다. **정본 편입은 A 소관.**

경계는 **가드 도입 시각**에서 온다 — 관측된 마지막 부재(10:02:22)는 보고하는 관측치이지
판정 기준이 아니다(D-DEF-52).

## RQ-D-LIMITS — 적어 둔 한계를 계수 (2026-08-28 17:46, `D-V3-FINDING-075`)

앞 세 티켓의 limitation 에 "세지 않았다" 고 적은 셋을 **실제로 셌다**. 셋 다 누락 **0**.

| 한계 (출처) | 계수 결과 |
|---|---|
| `emission_record()` 가 `actor:D` 줄만 본다 (073) | D 이외 actor 의 D 티켓 발행기록 **0** |
| `from == D` 인 티켓만 본다 (074) | `tickets/` 파일명 `D-*` 116 = `from==D` 116, 차집합 0 |
| `derive_targets()` 가 import 문만 읽는다 (072) | 스캔에 `subprocess`·`exec`·`bash` **0건** |

**세 원천이 전부 D 자신의 기록**이라(D-DEF-71) A/B/C 의 ACK·로그로 한 번 더 봤다 — 오탐 1건을
빼면 누락 0.

**부수 발견**: `D-` 접두사는 D 평면 전용이 아니다. `acks/`·`completions/` 에 A 발행
`D-R0-74-2`(`GO_NO_GO`, 8/27) 1건이 있다. `tickets/` 안에서는 116=116 으로 일치한다.
→ `T-B-V3-FINDING-021` 의 실제 사례. **검사는 만들지 않았다** — n=1 이고 규율("모집단은
`from` 으로")은 이미 도구에 있다.

**발행 전 자체검출**: 이 계수의 첫 probe 가 `startswith("D-")` 로 D 티켓을 판정했다 —
**그 결함을 찾는 probe 안에서 그 결함을 저질렀다.**

## RQ-D-CLOCK — 시각도 측정치다 (`D-V3-FINDING-076`, P1)

B 가 `D-V3-FINDING-075` 를 **17:32:07** 에 ACK 했는데 D 가 기록한 발행 시각은 **17:46:00** —
ACK 가 발행보다 앞선다. **D 가 시각을 손으로 적어 왔다.**

| 측정 | 값 |
|---|---|
| D 작성 버스 파일 | 131건 |
| 선언시각이 mtime 과 60초 초과 어긋남 | **37건** (부호 **전부 +**) |
| 최대 격차 | **+5267초 (88분)** |
| 최근 5회차 격차 추이 | +66 → +163 → +478 → +684 → **+944초** |

**판정은 하나도 안 바뀐다.** `SCHEMA_GUARD_SINCE` 는 커밋 `b352be0` 시각(기계 측정)이고,
가드 전/후가 뒤집히는 3건(044/045/046)에는 위반이 없다. `self_approved` 부재 판정 뒤집힘 0.
어긋남이 전부 **앞선 방향**이라 검사는 스스로를 더 엄하게 분류해 왔다.

**남는 피해**: 버스에 인과 역전이 남았다. 발행분은 불변이라 고치지 않는다.

**시정**: `clock_errors()` 가 120초 초과 어긋난 시각을 **발행에서 막는다**. 대조군 5건 추가
(모듈 controls 8→13, must_flag 9).

**미결(다음 회차)**: ACK 파일은 `emit()` 을 거치지 않아 **아직 막히지 않는다**.

## RQ-D-BUS-CLOCKTEST — `T-B-CLOCKTEST-002` (to=D, P3) · 2026-08-28 17:41

B 가 `scope: 시각 가드 대조군` 으로 D 앞에 낸 시험 티켓. **ACK 하지 못했다 — 파일이 사라졌다.**
`event_log` 에는 `TICKET_ISSUED` 가 남아 있고 `tickets/` 에 파일이 없다. **왜 없는지는 D 가
단정하지 않는다**(가드에 막힘·시험 후 삭제·기타).

- B 의 선언시각 `17:41:42.585566` vs 파일 mtime `17:41:42.606001` — 차 **0.02초**. B 의 스탬프는 측정치다.
- `T-B-CLOCKTEST-001` 은 버스 어디에도 없다(`CLOCKTEST` 일치 1건뿐).
- D 의 새 `emit_ack()` 이 "없는 티켓에는 ACK 하지 않는다" 로 **실사용에서 막았다.**

이 건으로 `emission_record()` 의 **반대 방향**(로그에만 있고 파일 없음)을 추가했다 — `D-DEF-82`.
