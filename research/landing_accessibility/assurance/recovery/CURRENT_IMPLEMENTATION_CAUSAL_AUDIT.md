# CURRENT IMPLEMENTATION CAUSAL AUDIT — depth 축 MPFED 0/59 원인 재분해

**작성** Claude C (recovery audit lane, FINAL 과 분리) · 2026-08-27T15:33:45+09:00
**기준** collector `222ef2c28ed5971b3c9f8b07120b7627d2617476` (E001 실행 HEAD, B 수정 이전) · 원천 CSV `agent/landing-pb-prework@9999857 representative_task_candidate_shadow.csv`
**근거 파일** `DEPTH_DATAFLOW_222ef2c.md`(코드 인용) · `TASK_LINEAGE_59.json`(59건 행별 사실) · `TASK_FIELD_COUNTS.json`
**성격** 구현을 정당화하지 않는다. A 의 계약(A1/A2/00_SSOT)과 B 의 코드가 실제로 일치하는지만 본다. 이 문서의 어떤 내용도 16:00 CLAIM / 16:30 FINAL 에 섞지 않는다.

---
## 0. 한 줄 결론

**이 커밋에서 Scout 은 59 타깃 전부에 대해 region_definition=None · endpoint_definition=None · signal_type=CODEBOOK_PENDING 으로 실행됐다.** 원천 CSV 에는 59/59 정의가 존재했으나 로더→TargetSpec→TaskDefinition 경로에서 떨어졌다. 따라서 **MPFED 가 non-NULL 이 될 수 있는 코드 경로는 gate 승격 경로(FINANCIAL/COMMUNICATION 의 LOGIN gate, A2 E-5) 하나뿐**이었고, 그 경로도 gate 종류 판별 UNDETERMINED(fail-closed) 로 0 이 됐다. 가드 입도와 E-6b 는 실재하지만 **그보다 앞선 층위(task wiring · signal detector)** 가 있다.

## 1. Director 요구 계수 (모집단 = 동결 59; 전체 CSV 71행 기준은 endpoint_signal_type 42/20/9, region 63/8, mapping CANDIDATE 59 + AMBIGUOUS_UNRESOLVED 12)

| 계수 | 값 | 출처 |
|---|---|---|
| 원본 CSV region_definition 존재 n | **59 / 59** | TASK_FIELD_COUNTS |
| region_signal_type 별 n | DOM_AX_ROLE **53** · CODEBOOK_PENDING **6** | 〃 |
| endpoint_definition 존재 n | **59 / 59** | 〃 |
| endpoint_signal_type 별 n | URL_PATTERN **33** · DOM_AX_ROLE **17** · FORM_STRUCTURE **9** | 〃 |
| mapping_status 별 n | CANDIDATE **59** (전체 CSV 71행 중 AMBIGUOUS_UNRESOLVED 12 는 프레임 밖) | 〃 |
| Scout 에 실제 전달된 region_definition non-null n | **0 / 59** (Scout 실행 31건 기준 0/31) | executor.py:67-75 상수 None; TASK_LINEAGE 결과 필드 부재 |
| Scout 에 실제 전달된 endpoint_definition non-null n | **0 / 59** — TargetSpec 까지는 59/59 전달되나(plan.py:49, run_e001_real.py:64-77) **소비처 0** | DEPTH_DATAFLOW §1·§4 |
| CODEBOOK_PENDING 으로 덮인 n | **59 / 59** (region·endpoint signal_type 모두 상수) — CSV 고유 CODEBOOK_PENDING 은 6 | executor.py:67-75 |
| Scout 실행 중 area_signal_detected any | **0 / 31** | TASK_LINEAGE |
| Scout 실행 중 endpoint_signal_detected any | **0 / 31** | 〃 |
| Scout 실행 activation 0회 | **27 / 31** (1회 2 · 2회 2) | 〃 |
| area_signal_status | NOT_OBSERVED **31 / 31** | 〃 |
| 결과 task_id 가 CSV task_id 와 일치 | **0 / 31** (결과 `task-wtg_<id>` 합성; CSV task_id 는 전 행 공란) | 〃 |

## 2. 원인 4종 — 서로 다른 층위로 분리

| # | 원인 | 층위 | 코드 근거 | 확실성 | 영향 범위 |
|---|---|---|---|---|---|
| C-G | **가드 입도** — L0 후보 텍스트에 LOGIN/PURCHASE/SIGNUP/PAYMENT 패턴이 하나라도 있으면 target 전체를 Scout 이전에 중단 | Scout 이전 | guard.py:170-182 `screen_candidates` → `AccountActionBlockedError`; TaskEntry 미생성 | 코드 확정 | 25 / 59 |
| C-W | **task-definition wiring** — 로더가 region_definition·region_signal_type·endpoint_signal_type·mapping_status 를 읽지 않고(firewall.py:692-723, E001TargetRow :543-554), endpoint_definition 은 TargetSpec 까지 오지만 소비처가 없으며, `default_task_definition` 이 region/endpoint=None, signal_type=CODEBOOK_PENDING 을 **무조건** 넣는다(executor.py:67-75); batch.py:258 → real_executor.py:138 `task or default_task_definition(target)` 에서 항상 default | Scout 입력 | 위 인용 | 코드 확정 | **59 / 59** (Scout 실행 31 전건 포함) |
| C-D | **signal detector** — `detect_area_signal` 은 region_definition None 이면 False(QUERY 만 search_inputs 예외, l1_engine.py:208-214), `detect_endpoint_signal` 은 endpoint_definition None 이면 False(:223-224); 정의가 있어도 probe 는 `[data-region]`·`[data-endpoint]`·`body[data-endpoint-reached]` 속성 동등 비교만(l0_probe.js:309-337) — fixture 전용 신호. `*_signal_type` 은 어디서도 읽지 않고 CODEBOOK_PENDING 분기 없음(`mapping_frozen_allowed` 호출 0) | 신호 해석 | 위 인용 | None→False 는 코드 확정; "실제 사이트에 data-* 속성 부재" 는 **추측**(0/31 탐지·27/31 무활성으로 뒷받침) | Scout 실행 31 전건 |
| C-E | **endpoint 계약** — 두 갈래로 나뉜다: **C-E1 설계 규칙**(승격 archetype 이 FINANCIAL·COMMUNICATION 뿐 → 그 외 archetype 의 gate 도달 11 은 판별을 개선해도 endpoint 가 될 수 없음, 구현 결함 아님) / **C-E2 gate 종류 판별**(FINANCIAL 1 이 UNDETERMINED → fail-closed). gate→endpoint 승격은 FINANCIAL{LOGIN, IDENTITY_VERIFICATION}·COMMUNICATION{LOGIN} 뿐(depth.py:35-45, 66-71); 그 외 archetype 및 종류 UNDETERMINED 는 AUTH_GATE_REACHED→NULL(코드 명칭은 E-6a; 계약 문서는 E-6b) | 계약/설계 | 위 인용 | 코드 확정 | C-E1 11(설계) · C-E2 **1**(구현 층위에서 유일하게 걸리는 건) — C-G/C-W/C-D 와 자릿수가 다르다 |

**중첩 — 합산 금지:** 4층위는 서로 다른 단계의 원인이며 **상호배타 분할이 아니다**(59 ⊇ 25 + 31 + 3; C-W 59 는 전건). 합계를 만들지 마라. 상호배타 분할은 A 의 outcome 6종 표(합 59) 다.
**독립성:** C-G 는 C-W/C-D 와 무관하게 발생한다(Scout 이전). C-W 는 C-D 의 입력을 비워 C-D 를 항상 False 로 만든다. C-E 는 C-W/C-D 가 모두 복구돼도 남는 계약 층위다.

## 3. MPFED 0/59 재분해 (현재 구현 기준)

```
59 attempted
├─ 25  C-G 가드 차단 (Scout 미실행)            — 도구 제약. 가드를 고쳐도 C-W/C-D 아래로 떨어진다
├─ 31  Scout 실행 — 전건 C-W(정의 None) ⇒ C-D 항상 False ⇒ region/endpoint 신호 0/31
│    ├─ 12  gate 도달 (AUTH 11 · PAYMENT 1)   — 유일한 non-NULL 경로(C-E) 진입: 승격 불가 archetype 11, FINANCIAL 1 은 종류 UNDETERMINED → NULL
│    ├─ 18  UNRESOLVED                         — 신호가 원리적으로 없어 예산/무신호/기술오류로 종결 (7·2·6 / SCOUT_ERROR 3)
│    └─  1  CAPTCHA
└─  3  L0 없음 (retry 소진)
```
**A 의 6종 귀속표(가드 25 · archetype 규칙 11 · UNRESOLVED 18 · retry 3 · CAPTCHA 1 · E-6b 구속 1)는 outcome 층위에서 정확하다.** 본 감사는 그 아래에 C-W·C-D 라는 **공통 선행 원인**이 있음을 코드로 확정한다 — 특히 UNRESOLVED 18 은 "대상이 어려웠다" 가 아니라 "탐지할 정의가 없었다" 가 코드상 1차 원인이다.

## 4. A 의 반사실 라벨링

> A(30dfc4f): "가드를 고쳐도 depth 는 살아나지 않는다 — 회복 상한 8"

**보존하되 라벨을 붙인다: `CURRENT_IMPLEMENTATION_CONDITIONAL_COUNTERFACTUAL`.** 그 반사실은 C-W·C-D 가 그대로인 시스템(정의 None, data-* 전용 detector)에서만 성립한다 — 그 조건에서는 실제로 gate 승격 경로(FINANCIAL 6 + COMMUNICATION 2 = 8) 외에 non-NULL 경로가 없으므로 상한 8 은 코드적으로도 맞다. **task-definition wiring + 실제 signal detector 를 복구한 시스템에 대해 상한 8 을 일반화하는 서술은 반려 대상**이다 — 그 시스템에서의 상한은 오늘 데이터로 알 수 없다.

## 5. 계약 대 코드 불일치 (recovery 전 확인 항목)

| 항목 | 계약 | 코드(222ef2c) | 판정 |
|---|---|---|---|
| region/endpoint 정의의 출처 | A1 §1.2·A2 §1.9: P-A codebook / task frame 이 정의, `region_signal_type`·`endpoint_signal_type` 로 신호 해석 | 로더가 읽지 않음, default 상수 | **C1** (계약 미구현) |
| CODEBOOK_PENDING | A2 P-2: FROZEN 전이 불가, 신호 미해석 상태 | 전 59 에 상수로 부여, 분기 없음 | **C1** |
| gate 승격 규칙 명칭 | A2 E-6b(UNDETERMINED→비승격) | 코드 주석 E-6a | C2 (명칭) |
| TargetSpec.endpoint_definition | 계획→실행 전달 | 전달되나 소비 0 | C1 (dead field) |
| probe 신호원 | 02 §9·A1 §1.3 "state-changing activation / 영역·endpoint 성립" | `data-*` 속성 동등 비교만 | C1 (fixture 전용) |

## 6. 이 문서가 말하지 않는 것
- B 의 guard relocation 이나 wiring 복구안의 타당성 — 업무 2·3 에서 negative test / fixture 로 검증한다.
- 복구 후 MPFED 산출 가능 건수 — 오늘 데이터로 알 수 없다.
- FINAL(16:30) 판정 — frozen E001 사실만 다루며 본 문서와 분리된다.
