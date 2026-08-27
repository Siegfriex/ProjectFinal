# LANE_P_FINDINGS — Provenance / 분모 사슬 / Metric redundancy 하네스

**verdict**: `READY_WITH_AMBIGUITY`  
**base SHA**: `7448184a811f5d7d8772f21488bb75418fde3313`  
**SSOTV3 MANIFEST sha256 대조**: declared `1735c956d4a3461e…` / observed `1735c956d4a3461e…` → **MATCH**  
**생성**: 2026-08-28T02:53:08.570443+09:00 (KST)  
**routing**: to=C, cc=A (06 §4 — D 는 A 로 canonical conclusion 을 직접 우회 전달하지 않는다)

MAIN50 실측 데이터는 없다. 이 문서의 모든 수치는 **합성 fixture** 에 대한 것이며 어떤 서비스에 관한 사실도 아니다.

---

## 0. 무엇을 만들었나

| # | 컴포넌트 | 상태 |
|---|---|---|
| 1 | denominator chain | `IMPLEMENTED` |
| 2 | lineage hole detector | `IMPLEMENTED` |
| 3 | failure class decomposer | `IMPLEMENTED_WITH_AMBIGUITY` |
| 4 | metric redundancy scaffold | `SCAFFOLD_ONLY_NO_NUMBERS` |
| 5 | manski worst case bound | `IMPLEMENTED` |
| 6 | input absent guard | `IMPLEMENTED` |

## 1. 정의는 원문 그대로 옮겼다

```
05 §6  candidate 10 → eligible/frozen 10 → attempted 10 → evidence-bearing n → flow-evaluable n
P1 B   requested URL -> final URL -> L0 -> AX -> DOM -> probe -> step -> terminal -> ledger
```

> **PROVENANCE 경고.** 05 §6 · 02 · 03 · 04 는 `SSOTV3/` 파일 원문에서 직접 인용했고 MANIFEST sha256 이 일치한다. 반면 **Director P1 B/C 원문 packet 은 이 워크트리에 파일로 존재하지 않는다** — 워커 지시문에 실린 문안을 그대로 구현했다. 원문 대조는 D/A 가 해야 한다. 이것이 이 하네스에서 가장 약한 provenance 고리다.

## 2. 분모 사슬 (05 §6)

grain = `service x frozen task`. family 분모 = **10** 고정. family 내 45 pair 는 distance matrix cell 이지 독립표본 n=45 가 아니다 (05 §1). 이 하네스는 어디서도 45 를 분모로 쓰지 않는다.

모든 비율에 분자·분모·grain 을 붙였다. 단계 중첩을 강제하고, **각 단계에서 빠진 target id 를 이름으로 낸다** — 수만 세지 않는다.

합성 F2(10건) 이탈 회계:

| 단계 | STRICT | PERMISSIVE |
|---|---|---|
| candidate | 10 | 10 |
| eligible_frozen | 8 | 8 |
| attempted | 7 | 7 |
| evidence_bearing | 6 | 7 |
| flow_evaluable | 4 | 6 |

이탈 target id (STRICT):

- `eligible_frozen` — ['SYN-F2-01|T-F2-PRIMARY|RUN-SYN-F2-01-001', 'SYN-F2-02|T-F2-PRIMARY|RUN-SYN-F2-02-001']
- `attempted` — ['SYN-F2-03|T-F2-PRIMARY|']
- `evidence_bearing` — ['SYN-F2-04|T-F2-PRIMARY|RUN-SYN-F2-04-001']
- `flow_evaluable` — ['SYN-F2-05|T-F2-PRIMARY|RUN-SYN-F2-05-001', 'SYN-F2-06|T-F2-PRIMARY|RUN-SYN-F2-06-001']

**STRICT 와 PERMISSIVE 가 다른 값을 낸다.** 어느 쪽이 05 §6 의 의도인지 SSOT 가 정하지 않았으므로(AD-02/AD-03) 이 하네스는 **고르지 않고 둘 다 낸다.**

### 2.1 identity 중복과 family n 불일치는 합치지 않는다

F4 에 `service_id+task_id+run_id` 가 같은 레코드를 하나 더 실은 fixture: 입력 11건 / 구분되는 target key 10개 → `duplicate_target_keys` 로 드러난다. candidate 분모는 11 로 **부풀어 보인다** — 조용히 dedupe 하지 않고 부푼 사실 자체를 낸다. 05 §4 고정 분모 비율은 분모 10 를 유지하므로 값이 1 을 넘어 이상이 드러난다 (관측 1.1).

family n 불일치도 숨기지 않는다: `입력 레코드 11 건. 05 §4 는 family 분모를 10 으로 고정한다 — 불일치를 은닉하지 않는다.`

## 3. lineage hole 탐지 (P1 B)

9노드. **파일 없음 / 필드 null / 값 0 / 키 부재 / 확인불가를 서로 다른 상태로 낸다.**

| fixture | 관측 상태 |
|---|---|
| FILE_ABSENT_case | `FILE_ABSENT` |
| FIELD_NULL_case | `FIELD_NULL` |
| VALUE_ZERO_case | `VALUE_ZERO` |
| KEY_MISSING_case | `KEY_MISSING` |
| EVIDENCE_ROOT_UNKNOWN_case | `EVIDENCE_ROOT_UNKNOWN` |

양방향 대조 — 온전한 사슬은 hole 0, 9노드를 하나씩 끊으면 **정확히 그 노드만** 잡혔다:

| 끊은 노드 | 관측된 hole | 상태 | 일치 |
|---|---|---|---|
| requested_url | ['requested_url'] | `KEY_MISSING` | O |
| final_url | ['final_url'] | `KEY_MISSING` | O |
| l0 | ['l0'] | `FILE_ABSENT` | O |
| ax | ['ax'] | `FILE_ABSENT` | O |
| dom | ['dom'] | `FILE_ABSENT` | O |
| probe | ['probe'] | `FILE_ABSENT` | O |
| step | ['step'] | `VALUE_ZERO` | O |
| terminal | ['terminal'] | `FIELD_NULL` | O |
| ledger | ['ledger'] | `FIELD_NULL` | O |

상류가 끊겨도 하류 노드를 마스킹하지 않는다 — 각 노드를 독립 평가한다.

## 4. 실패 사유 분해 (P1 C 8종)

**8종을 하나로 묶지 않는다. 추정으로 채우지 않는다.**

| Director 8종 | 확정 근거 | fixture 일치 |
|---|---|---|
| PUBLIC_MOBILE_WEB_ABSENT | `SSOT_DERIVED` | O |
| WAF_CHALLENGE | `EXPLICIT_SIGNAL` | O |
| TIMEOUT | `EXPLICIT_SIGNAL` | O |
| EVIDENCE_DEFECT | `SSOT_DERIVED` | O |
| DISABLED_INERT | `EXPLICIT_SIGNAL` | O |
| FORBIDDEN_ACTION | `EXPLICIT_SIGNAL` | O |
| AUTH_GATE | `SSOT_DERIVED` | O |
| GENUINE_TASK_SURFACE_ABSENCE | `EXPLICIT_SIGNAL` | O |

구분 불가 케이스는 채우지 않았다:

| 입력 | 결과 |
|---|---|
| blocked_alone | `UNRESOLVED_FAILURE_CLASS` (NO_DISTINGUISHING_INPUT) |
| public_web_unobservable_alone | `UNRESOLVED_FAILURE_CLASS` (NO_DISTINGUISHING_INPUT) |
| no_terminal_no_signal | `UNRESOLVED_FAILURE_CLASS` (NO_DISTINGUISHING_INPUT) |
| 명시 signal 과 SSOT 파생 충돌 | `UNRESOLVED_FAILURE_CLASS` (SIGNAL_CONFLICT) |

> **가장 중요한 발견.** Director 가 요구한 8종 중 **SSOT `endpoint_status`(7값)로 일의적으로 갈 수 있는 것은 3종뿐이다.** `BLOCKED` 하나가 WAF·challenge 와 timeout 을 함께 삼키고, `PUBLIC_WEB_UNOBSERVABLE` 하나가 public mobile web 부재와 genuine task surface absence 를 함께 삼킨다. disabled·inert 와 forbidden action 은 대응 값 자체가 없다. **수집기가 명시 signal 을 남기지 않으면 MAIN50 에서 8종 분해는 원리적으로 불가능하다.** 이것은 지금 고쳐야 하는 수집 스키마 문제지, 데이터가 온 뒤 분석으로 메울 수 있는 것이 아니다. → AD-01, to=C cc=A.

## 5. metric redundancy 스캐폴드 (05 §3)

8축 · 축쌍 28개. 상관(Spearman) · 상호정보(MI/NMI/불확실성계수) · Jaccard 함수를 구현했다.

**수치는 내지 않았다** — `NOT_COMPUTED_NO_DATA`. MAIN50 실측이 없으므로 8축 vector 가 존재하지 않는다.

**판정선을 만들지 않았다.** 이 스캐폴드에는 threshold 도 composite score 도 없고 '중복이다/아니다' 를 반환하는 경로가 없다. 함수 자체의 동작만 합성 벡터로 확인했다(monotone→1, reverse→-1, 무분산→None, 동일변수 MI=엔트로피, 독립변수 MI=0, Jaccard 0/1/undefined).

## 6. Manski worst-case bound

| 케이스 | lower | upper | width |
|---|---|---|---|
| no_missing | 0.6 | 0.6 | **0.0** |
| three_missing | 0.6 | 0.9 | **0.3** |
| all_missing | 0.0 | 1.0 | **1.0** |

두 family RD bound 폭 = 0.5, 부호 불변 = True.

**폭만 낸다.** 식별/비식별 판정, threshold, 재수집 권고를 반환하지 않는다. RQ-D7 에서 방법만 가져왔고 수치는 재사용하지 않았다.

## 7. 빈 결과 함정 방어 — INPUT_ABSENT

이 프로젝트에서 '존재하지 않는 경로에 grep 을 걸고 0건을 정상으로 읽은' 실패가 여러 번 났다. 그래서 부재를 **5개 상태로 갈라** 명시 반환하고, fixture 로 실증했다.

| 케이스 | load_status | computed | 정상처럼 보였나 |
|---|---|---|---|
| path_not_given | `INPUT_ABSENT_PATH_NOT_GIVEN` | False | **NO** |
| path_missing | `INPUT_ABSENT_PATH_MISSING` | False | **NO** |
| not_a_dir | `INPUT_ABSENT_NOT_A_DIR` | False | **NO** |
| manifest_missing | `INPUT_ABSENT_MANIFEST_MISSING` | False | **NO** |
| zero_records | `INPUT_ABSENT_ZERO_RECORDS` | False | **NO** |

## 8. 변이 검사 — 탐지기를 일부러 틀리게 만들었을 때

| 변이 | 정상 | 변이 하 | 잡았나 |
|---|---|---|---|
| M1 파일없음→PRESENT | holes=1 | holes=0 | O |
| M2 null→KEY_MISSING | `FIELD_NULL` | `KEY_MISSING` | O |
| M3 INPUT_ABSENT 가드 제거 | `INPUT_ABSENT_PATH_MISSING` | `INPUT_PRESENT` (조용한 통과 생성=True) | O |
| M4 분모 중첩 해제 | {'candidate': 10, 'eligible_frozen': 8, 'attempted': 7, 'evidence_bearing': 6, 'flow_evaluable': 4} | {'candidate': 10, 'eligible_frozen': 8, 'attempted': 9, 'evidence_bearing': 9, 'flow_evaluable': 8} | O |
| M5 실패사유 추정 채움 | `UNRESOLVED_FAILURE_CLASS` | `TIMEOUT` | O |

변이 원복 확인: `_MUTATIONS` 비었음 = True, 원복 후 intact fixture hole 수 = 0.

### 8.1 음성 대조 — 검사 스위트가 무력하지 않다

전건 통과가 '검사가 아무것도 안 잡기 때문' 이 아님을 보이려고, 각 변이를 **전역으로** 켠 채 스위트 전체를 다시 돌렸다.

| 변이 | 결과 | 실패 검사 수 |
|---|---|---|
| M1_FILE_ABSENT_AS_PRESENT | `CHECKS_FAILED` | 6 |
| M2_NULL_AS_KEY_MISSING | `CHECKS_FAILED` | 3 |
| M3_NO_INPUT_ABSENT_GUARD | `SUITE_RAISED` | KeyError: 'F1' |
| M4_DENOMINATOR_NOT_NESTED | `CHECKS_FAILED` | 2 |
| M5_GUESS_FAILURE_CLASS | `CHECKS_FAILED` | 4 |

모든 변이가 탐지됨 = **True**, 원복 = True.

## 9. fixture 총계 — 70건 중 실패 0건

전건 통과.

## 10. AMBIGUOUS_DEFINITION — 채우지 않고 올린다

### AD-01 — Director P1 C 8종  vs  04_FLOW_CODEBOOK §4 endpoint_status (7값)

Director 가 요구한 8종 중 TIMEOUT / DISABLED_INERT / FORBIDDEN_ACTION / GENUINE_TASK_SURFACE_ABSENCE 는 대응하는 SSOT endpoint_status 값이 없다. BLOCKED 하나가 WAF·challenge 와 timeout 을 함께 삼키고, PUBLIC_WEB_UNOBSERVABLE 하나가 'public mobile web 부재' 와 'genuine task surface absence' 를 함께 삼킨다.

- 하네스 동작: 명시 signal 이 없으면 UNRESOLVED_FAILURE_CLASS. 추정하지 않는다.
- 필요한 판단 주체: **A (codebook 값 추가 또는 수집기 필수 signal 필드 지정)**

### AD-02 — 05_ANALYSIS_PLAN §6 'evidence-bearing n'

03 §10 이 evidence package 구성요소를 열거하지만, target 하나가 evidence-bearing 이려면 구성요소 '전부'가 필요한지 '하나라도'면 되는지 SSOT 가 정하지 않는다.

- 하네스 동작: STRICT/PERMISSIVE 두 분모를 나란히 낸다. 고르지 않는다.
- 필요한 판단 주체: **A**

### AD-03 — 05_ANALYSIS_PLAN §6 'flow-evaluable n'

task_flow_sequence 만 있으면 되는지, endpoint_status 가 REACHED/AUTH_GATE 여야 하는지 정의가 없다. ABSTAIN·BLOCKED 로 끝난 관측이 sequence 분석 분모에 들어가는지가 05 §2-E 의 unique signature·Levenshtein 분모를 바꾼다.

- 하네스 동작: STRICT/PERMISSIVE 두 분모를 나란히 낸다.
- 필요한 판단 주체: **A**

### AD-04 — Director P1 C 목록에 AUTH_GATE 가 실패사유로 포함  vs  01 §1 포함조건

01 §1 은 'legitimate AUTH_GATE로 종료 가능'을 frame 포함조건으로 둔다. AUTH_GATE 를 실패사유로 세면 정당 종료가 손실로 계상돼 분모가 바뀐다.

- 하네스 동작: class 는 그대로 내되 is_ssot_legitimate_terminal=true 플래그를 함께 낸다. 어느 쪽으로도 합산하지 않는다.
- 필요한 판단 주체: **A**

### AD-05 — Director P1 B 사슬의 'ledger' 노드

ledger(원장) 레코드의 스키마가 SSOTV3 에 정의돼 있지 않다. 02 §8 은 observation identity 만 규정한다. 무엇이 있어야 ledger 노드가 PRESENT 인지 확정 기준이 없다.

- 하네스 동작: 비어있지 않은 record 이면 PRESENT. 내용 검증은 하지 않는다.
- 필요한 판단 주체: **A 또는 C (C-BLOCKER-220418 원장 귀속 계열)**

### AD-06 — Director P1 B 'L0' 노드  vs  03 §3 S0..Sn

L0 는 03 §3 의 S0 최초 안정화 capture 를 뜻하는 것으로 보이나 표기가 다르다. S1..Sn scroll state 의 결손을 L0 노드가 대표하는지 여부가 불명확하다.

- 하네스 동작: L0 를 단일 manifest 포인터로만 본다. scroll state 결손은 보지 않는다.
- 필요한 판단 주체: **A**

### AD-07 — 05 §6 'attempted 10'  vs  03 §5 REPLAY_BROKEN

replay 가 깨져 REPLAY_BROKEN 인 run 이 attempted 에 계상되는지, 재수집 run 이 attempted 를 2 로 만드는지(02 §8 은 재수집을 새 run 으로 둔다) 정의가 없다. attempted 를 run 수로 세면 target 수와 grain 이 갈린다.

- 하네스 동작: target grain 으로만 센다(run_id 존재 여부). run grain 은 내지 않는다.
- 필요한 판단 주체: **A / C (ruling_11 단위·모집단·원천 3축 명시 요구와 같은 계열)**

### AD-08 — 'metric redundancy' 의 대상 단위

05 §3 은 8축을 profile 로 분리 보고하라고만 한다. 두 축이 '같은 construct 를 중복 측정한다'의 조작적 정의가 SSOT 에 없다. 관측단위(target 8축 vector) 와 축쌍 28 을 혼동하면 45-pair 오류와 같은 계열의 오류가 난다.

- 하네스 동작: 상관·상호정보·Jaccard 값만 내는 함수를 두고, 판정선을 만들지 않는다. 데이터가 없으므로 수치도 내지 않는다.
- 필요한 판단 주체: **A (D 는 조작화를 발명하지 않는다)**

## 11. 하지 않은 것

- 8축 중복 수치 산출 — MAIN50 실측 없음. NOT_COMPUTED_NO_DATA 로만 반환한다.
- 중복 판정선 / threshold / cut-off / composite score — 금지 범위.
- 실패 사유를 evidence 로부터 추론하는 규칙 — 새 조작화 금지. 명시 signal 과 SSOT 일의적 파생만 쓴다.
- REAL 접속·수집·replay — 금지.
- gold label / task gold / holdout 접근 — 금지.
- GO/NO-GO, 재수집 권고, target replacement 제안 — A 권한.
- 45 pair 를 관측단위로 쓰는 어떤 집계도 넣지 않았다.
- ledger 레코드 내용 검증 (AD-05 미정의).
- S1..Sn scroll state 결손 탐지 (AD-06 미정의).
- run grain 분모 (AD-07 미정의; target grain 만).
- MLflow 기록 — STANDBY 범위 밖(D queue 2026-08-28 02:28 보류 결정).

## 12. 한계

- MAIN50 실측이 없다. 여기의 모든 수치는 합성 fixture 에 대한 것이며 어떤 서비스에 관한 사실도 아니다.
- 이 하네스는 입력이 SSOT v3 필드명을 따른다고 가정한다. B 의 실제 mart 필드명이 다르면 전부 KEY_MISSING 으로 떨어진다 — 그것이 조용한 통과보다 낫지만, 첫 실행 시 필드명 매핑 대조가 반드시 선행돼야 한다.
- evidence_root 가 주어지지 않으면 포인터 노드는 FILE_ABSENT 가 아니라 EVIDENCE_ROOT_UNKNOWN 이다. 이 둘을 같게 읽으면 결손을 과대계상한다.
- Manski bound 는 폭만 낸다. RQ-D7 의 수치는 재사용하지 않았고 방법만 가져왔다.
- 실패 사유 8종 중 4종은 SSOT 대응 필드가 없어(AD-01) 실입력에서 대량 UNRESOLVED_FAILURE_CLASS 가 날 수 있다. 이것은 하네스의 결함이 아니라 수집 스키마의 미정의를 드러낸 것이다.
- 변이 검사는 5개 변이만 덮는다. 탐지기의 다른 오류 양식은 덮지 못한다.

---

이 하네스는 GO/NO-GO 를 내지 않는다. `verdict` 는 **하네스 자체의 준비 상태** 표시이며 연구 판정이 아니다. 실입력 실행 전에 B 의 실제 mart 필드명과 이 하네스의 입력 계약을 먼저 대조해야 한다 — 필드명이 다르면 전부 `KEY_MISSING` 으로 떨어진다.

