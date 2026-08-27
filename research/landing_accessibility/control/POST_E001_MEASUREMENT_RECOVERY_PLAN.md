# POST-E001 MEASUREMENT RECOVERY PLAN

**ID** `LA-REC-20260827`
**권위** A0 Research Director 지시 (2026-08-27 15:1x KST)
**작성** Claude A (Authority Plane), 2026-08-27 15:30 KST
**지위** 권위 문서. **오늘의 E001 결과·계약·FINAL 을 변경하지 않는다.**

---

## 0. 이 문서가 무엇이 아닌지 — 먼저 못박는다

**새 분석을 고르는 문서가 아니다.** SSOT 가 처음부터 정의한 3축을 **실제로 산출할 수 있도록
구현 누락과 측정 연결을 복구**하는 계약이다.

```
축 A   표준적으로 보기/누르기 어려운가   →  Older-relevant KWCAG criterion
축 B   대표기능까지 구조적으로 깊은가     →  NED / IED / MPFED
축 C   처음부터 팝업·오버레이가 방해하는가 →  Obstruction / interrupt
```

**오늘 데이터 값을 보고 분석 기준을 바꾸지 않는다.** 이 문서는 **무엇이 구현되지 않았는가**에만
근거하며, 관측된 결과값(FailRate·coverage·상관 등)을 입력으로 쓰지 않는다.

---

## 1. ORIGINAL_E001 = **READ_ONLY** (동결)

```
E001_FULL              59 / 59 완료
collector_sha          222ef2c28ed5971b3c9f8b07120b7627d2617476
MART                   ACCEPTED (A · C)
grade                  PILOT / PRELIMINARY
Axis A                 NOT_EVALUATED
Axis B                 MPFED 0 / 59
Axis C                 RAW_MEASURED_CLASSIFICATION_INCOMPLETE
association            NOT_COMPUTABLE · substitute_made = false
```

**절대 사후 수정하지 않는다:** `ANALYSIS_CONTRACT`(`LA-AC-20260827`) ·
`AMENDMENT_1`(`LA-AC-AMD1-20260827`) · `ANALYSIS_FRAME_FREEZE` · `FROZEN_MART_MANIFEST` ·
mart fact 파일 · E001 evidence.

**recovery 결과는 오늘 결과를 대체하지 않는다.** 별도 코호트로 산출되며, 두 결과를 합치거나
오늘 값을 덮어쓰는 것을 금지한다.

---

## 2. 독립 확인 결과 — A 가 코드에서 직접 검증했다

### 2.1 축 A — **KWCAG evaluator 부재 확인**

| 확인 | 결과 |
|---|---|
| `evaluate_criterion` · `CriterionResult` 정의 | **0건** |
| `e001_runner` 의 criterion·kwcag 참조 | **0건** |
| criterion 평가 실행 스크립트 | **없음** |
| `ai_review.py` 머리말 | *"인터페이스와 전이 규칙만. **모델을 호출하지 않는다.**"* (명시적 skeleton) |
| `l0_collector.py:11` | *"Axis B 관측 변수이며 criterion 판정이 아니다"* |

**KWCAG subset 동결 상태:** older-relevant 태깅은 오늘 A 가 동결했다
(`OLDER_RELEVANT_KWCAG_SUBSET.md`, sha256 `da4b5208…`). **정본 기준표는 Pilot 의
`kwcag22_criteria.json`(33개 전수)이다.** 즉 **subset 은 있고 evaluator 가 없다.**

### 2.2 축 B — **판정기 부재가 아니라 입력 미연결이다. 이것이 오늘 가장 중요한 정정이다**

**`executor.py:57` `default_task_definition()` 의 docstring 이 스스로 밝힌다:**

> 실제 서비스별 `region_definition`/`endpoint_definition` 은 P-A endpoint codebook 이
> 동결하기 전에는 존재하지 않는다(`A1 §1.8`). 그래서 여기서는 `CODEBOOK_PENDING` 을
> 그대로 둔다 — **이 상태에서 Scout 를 돌리면 QUERY 를 제외한 모든 archetype 은
> area/endpoint 신호가 결코 성립하지 않고**, gate 가 없으면 예산 소진으로 `UNRESOLVED` 에
> 도달한다. 그것이 정직한 결과다 — codebook 없이 endpoint 를 만들어내지 않는다.

**MPFED 0/59 는 수집 전에 구조적으로 확정돼 있었다.**

#### 결정적 검증 — 유일한 예외인 QUERY 5건이 전부 Scout 이전에 차단됐다

```
wtg_bbdefa29  ACCOUNT_ACTION_BLOCKED   scout_invoked = False
wtg_91b95286  ACCOUNT_ACTION_BLOCKED   scout_invoked = False
wtg_6d5510a6  ACCOUNT_ACTION_BLOCKED   scout_invoked = False
wtg_9390ef32  ACCOUNT_ACTION_BLOCKED   scout_invoked = False
wtg_ff3ee504  SKIPPED_RETRY_EXHAUSTED  scout_invoked = None
```

**MPFED 0/59 에 충분원인이 둘 있었고 서로 겹치지 않는다** —
54건은 `CODEBOOK_PENDING` 으로 **구조적 불가**, 5건(QUERY)은 가드·retry 로 **Scout 이전 차단**.

#### dataflow 유실 지점 — 코드 레벨 추적

```
P-B CSV (representative_task_candidate_shadow.csv)
  task_id · region_definition · region_signal_type ·
  endpoint_definition · endpoint_signal_type          ← 5개 필드 존재
        ↓
TargetSpec  (e001_runner/plan.py:36-51)
  target_id · canonical_service_key · official_url · interaction_archetype ·
  endpoint_definition(기본 None) · service_name_canonical · fixture_override
  ← region_definition · region_signal_type · endpoint_signal_type · task_id
    **필드 자체가 없다. 경계에서 유실된다.**
        ↓
default_task_definition()  (e001_runner/executor.py:57-75)
  region_definition   = None
  endpoint_definition = None                ← TargetSpec 이 가진 값도 버린다
  region_signal_type  = CODEBOOK_PENDING
  endpoint_signal_type= CODEBOOK_PENDING
  task_id             = f"task-{target_id}" ← CSV task_id 대신 합성
        ↓
TaskDefinition (engine/l1_engine.py:94-97)
  기본값은 DOM_AX_ROLE 인데 위에서 CODEBOOK_PENDING 으로 덮인다
        ↓
detect_area_signal / detect_endpoint_signal  →  신호 성립 불가
        ↓
compute_depth  →  NED/IED/MPFED = NULL
```

**등록 결함 (신규):**

| id | 내용 |
|---|---|
| `REC-B-1` | `TargetSpec` 에 `region_definition`·`region_signal_type`·`endpoint_signal_type`·`task_id` 필드가 없어 P-B CSV 값이 경계에서 유실된다 |
| `REC-B-2` | `default_task_definition()` 이 `TargetSpec.endpoint_definition` 이 값을 가져도 무조건 `None` 으로 덮는다 |
| `REC-B-3` | `task_id` 가 CSV 값 대신 `f"task-{target_id}"` 로 합성된다 (executor.py:69 · real_executor.py:66) |
| ~~`REC-B-4`~~ | ~~P-A endpoint codebook 이 동결되지 않았다~~ → **철회. 아래 §2.2.1 참조** |

### 2.2.1 `REC-B-4` 철회 — **A 의 오류. 정의는 존재한다**

**초판에서 `REC-B-4`(codebook 미동결)를 등록했다. 틀렸다.**

C 가 반증했고 A 가 원천 CSV 에서 직접 재확인했다 (`9999857` · `mapping_status=CANDIDATE` 59행):

```
region_definition     59/59 비어있지 않음   예: "개별 상품 항목의 링크·카드가 목록 형태로 노출"
endpoint_definition   59/59 비어있지 않음   예: "상품 상세와 핵심 상품정보가 보인 순간"
task_id               59/59                예: "task_shadow_11st"
region_signal_type    DOM_AX_ROLE 53 · CODEBOOK_PENDING 6
endpoint_signal_type  URL_PATTERN 33 · DOM_AX_ROLE 17 · FORM_STRUCTURE 9   ← PENDING 0건
```

**정의가 존재한다.** `endpoint_signal_type` 은 **59건 전부 실제 값**이고 `CODEBOOK_PENDING` 이 하나도 없다.

#### A 의 오류 원인 — **docstring 을 코드 사실로 받았다**

`default_task_definition()` docstring 은 *"P-A endpoint codebook 이 동결하기 전에는 존재하지
않는다"* 고 적는다. **그 전제가 낡았다** — P-B 레인이 이후에 정의를 산출했다.
**A 는 그 전제를 검증 없이 `REC-B-4` 로 옮겨 적었다.**

> **docstring 이 그렇게 적혀 있다는 것과 코드가 실제로 그렇게 동작한다는 것,
> 그리고 그 전제가 지금도 사실인가는 서로 다른 사실이다.** (B 지적)

**이것이 오늘 A 의 4번째 같은 축 오류다** — 문서화된 진술을 원본 확인 없이 사실로 취급했다.
§4.5 (b) 표에 **유형 3: 문서 진술을 코드 사실로 취급** 을 추가한다.

#### 정정된 원인 구조

```
정의는 존재한다 (P-B CSV 59/59)
        ↓  ← **여기서 유실된다 (REC-B-1·2·3)**
TaskDefinition 이 None / CODEBOOK_PENDING 으로 고정
        ↓
신호 성립 불가
```

**시정 방향이 완전히 달라진다.** codebook 을 **만들** 필요가 없다 — **연결만 하면 된다.**
초판대로 갔으면 다음 수행자가 이미 있는 것을 다시 만들었을 것이다.

#### C 의 관측이 이를 뒷받침한다 — **§2.2.2 에서 코드로 확정됨 (`adb63fe`)**

```
Scout 실행 31건의 task_id : 전부 `task-wtg_<id>` 합성, CSV `task_shadow_<key>` 와 일치 0/31
area_signal_status        : NOT_OBSERVED 31/31
area_signal_detected      : 0/31
endpoint_signal_detected  : 0/31
activation                : 0회 27/31
```

**모든 Scout 실행이 정의 없이 돌아 어떤 신호도 볼 수 없었다.** 이는 6종 귀속(가드·규칙·UNRESOLVED)
**아래에 깔린 공통 층위**이며 그것들과 **다른 원인**이다.

### 2.2.2 코드 확정 — `CURRENT_IMPLEMENTATION_CAUSAL_AUDIT` (C, 15:34)

**예비 사실이 코드 인용으로 확정됐다.** (`claude-c/assurance-current`
`assurance/recovery/CURRENT_IMPLEMENTATION_CAUSAL_AUDIT.md` · `DEPTH_DATAFLOW_222ef2c.md` ·
`TASK_LINEAGE_59.json`)

| # | 확정 사실 | 위치 |
|---|---|---|
| 1 | `load_e001_full_targets` 가 `region_definition`·`signal_type`·`mapping_status` 를 **읽지 않는다** | `firewall.py:692-723` |
| 2 | `default_task_definition` 이 region/endpoint=None · signal_type=CODEBOOK_PENDING 을 **무조건** 넣는다 | `executor.py:67-75` |
| 3 | `task or default_task_definition` 경로라 **항상 default 가 쓰인다** | `batch.py:258` → `real_executor.py:138` |
| 4 | `TargetSpec.endpoint_definition` 은 59/59 전달되지만 **소비처가 0이다 (dead field)** | — |
| 5 | **detector 는 정의가 None 이면 항상 False. probe 는 `data-region`/`data-endpoint` 속성만 본다 — fixture 전용이다** | — |

#### **5번이 결정적이다 — 갭이 둘이다**

`REC-B-1~3`(wiring)을 전부 고쳐도 **probe 가 실사이트에서 볼 신호가 없다.**
`data-region`/`data-endpoint` 는 우리 fixture 가 심는 속성이고 실제 상용 사이트에는 없다.

**따라서 복구는 두 단계가 모두 필요하다:**

```
REC-B-1~3   task definition wiring        (정의를 전달한다)
REC-B-5     실웹 signal detector 구현      (전달된 정의로 실제 DOM/AX/URL 에서 신호를 찾는다)
                                          ← 신규 등록. wiring 만으로는 부족하다
```

**`REC-B-5` 를 신규 등록한다.** `endpoint_signal_type` 이 이미 `URL_PATTERN` 33 ·
`DOM_AX_ROLE` 17 · `FORM_STRUCTURE` 9 로 **어떤 방식으로 탐지할지까지 명시하고 있으므로**,
detector 는 그 세 방식을 실제로 구현하면 된다. **설계를 새로 하는 게 아니다.**

### 2.2.3 원인의 4층위 — C 의 분해를 채택한다

```
C-G  가드 입도          25건 (Scout 이전 차단)
C-W  task wiring        **59건 전건** (정의가 전달되지 않음)
C-D  signal detector    **Scout 31건 전건** (전달돼도 실웹에서 탐지 불가)
C-E  endpoint 계약      gate 12건 (11 = archetype 미승격, 1 = E-6b 구속)
```

**내 6종 outcome 귀속표(`ANALYSIS_FRAME_FREEZE`)는 outcome 층위에서 정확하며 보존한다.**
C 의 4층위는 **원인 층위**다 — 서로 다른 층을 보는 것이지 어느 쪽이 틀린 게 아니다.

**`UNRESOLVED` 18건의 1차 코드 원인은 "탐지할 정의가 없었다" 다.**

### 2.2.4 반사실의 라벨 확정

`ANALYSIS_FRAME_FREEZE` 의 *"가드를 고쳐도 회복 상한 8"* 을
**`CURRENT_IMPLEMENTATION_CONDITIONAL_COUNTERFACTUAL`** 로 라벨해 보존한다.

**그 조건(정의 None · `data-*` detector) 하에서는 코드적으로도 맞다** — C 가 확인했다.
**wiring + detector 를 복구한 시스템으로 일반화하는 것은 반려한다.**

### 2.2.5 계약–코드 불일치 (C 등재)

**C1 4건:** 정의 출처 미구현 · `CODEBOOK_PENDING` 상수 부여 · `endpoint_definition` dead field ·
probe fixture 전용. **C2 1건:** E-6a/E-6b 명칭.

**이들은 recovery lane 에서 처리하며 오늘 FINAL 에 섞지 않는다.**

### 2.3 축 C — 결정론 분류만 있고 semantic 단계가 없다

`final_label` UNKNOWN **110 / 235 (46.8%)** — A·B·C 3중 검증됨.
raw 235건과 결정론 `final_label` 은 **원본으로 보존한다.**

---

## 3. 오늘 통합 문구의 교정

```
✗  수집기는 만들어졌고 판정기는 만들어지지 않았다
```

**축 A·C 에는 맞지만 축 B 에는 틀리다.** 축 B 는 판정기가 없는 게 아니라
**판정기가 쓸 입력이 연결되지 않았다.** 그리고 코드는 그것을 **정직하게 거부했다** —
codebook 없이 endpoint 를 만들어내지 않았다.

```
○  세 축이 서로 다른 단계에서 막혔다.
     축 A — 판정기 부재        (criterion evaluator 없음)
     축 B — **입력 미연결**    (task definition 이 CODEBOOK_PENDING 으로 고정)
     축 C — 판정기 미완        (semantic 단계 없이 결정론 규칙만)
```

### 3.1 반사실 결론의 범위 제한 — **확대 금지**

`ANALYSIS_FRAME_FREEZE` 의 *"가드를 고쳐도 회복 상한 8"* 은
**현재 collector/measurement 구현 하에서의 결론**이다.

> **금지:** *"올바른 task-definition wiring 과 signal detector 를 구현해도 depth 는 최대 8"*

**그 실험은 수행되지 않았다.** `CODEBOOK_PENDING` 상태에서는 6/7 archetype 이 구조적으로
불가능했으므로, 반사실이 측정한 것은 **"가드만 바꿨을 때"** 이지 **"wiring 이 정상일 때"** 가 아니다.

**frozen artifact 를 수정하지 않는다.** FINAL 서술에서 이 조건을 명시한다.

---

## 3.4 B dataflow 감사 (`RECOVERY_DATAFLOW_AUDIT.md`, `claude-b/measurement-recovery@2281c85`) — **정정 4건**

### 3.4.1 `C-E` 를 **12 → 1** 로 정정한다

`ENDPOINT_GATE_KINDS`(`depth.py:35-45`)가 **공집합이 아닌 archetype 은 2개뿐**이다.
gate 종료 13건 중 **승격 계약이 실제로 걸리는 것은 `FINANCIAL_ACTION_ENTRY` 1건**이고
그마저 gate 판별이 `UNDETERMINED` 다.

**나머지 12건은 판별을 개선해도 설계상 endpoint 가 될 수 없다.**

```
정정 전   C-G 25 · C-W 59 · C-D 31 · C-E 12
정정 후   C-G 25 · C-W 59 · C-D 31 · C-E1 11 · C-E2 1
```

**자릿수가 다르다.** 동급 우선순위로 두면 자원 배분이 왜곡된다.

#### C 의 `C-E1`/`C-E2` 분리를 채택한다 — **성격이 다르다**

내 초판 정정은 *"12 가 아니라 1"* 이라고만 했다. **C 의 분리가 더 정확하다:**

| | n | 성격 | 처리 |
|---|---|---|---|
| **`C-E1`** | 11 | **설계 규칙.** archetype 이 gate 를 endpoint 로 인정하지 않는다 | **구현 결함이 아니다. 고칠 대상이 아니라 계약을 다시 볼 대상이다** |
| **`C-E2`** | 1 | gate 판별 실패 (E-6b) | 구현 개선 대상 |

**11건을 "결함" 으로 분류하면 다음 수행자가 고치려 든다.** 그건 `A2 §1.5.1` + `00_SSOT §3` 이
정한 것이고, 바꾸려면 **measurement 계약 개정과 독립감사**를 거쳐야 한다.
`§4-4`(region 도달 시 NED 보존 검토)와 같은 층위의 일이다.

### 3.4.2 4층위는 **중첩**이고 6종 outcome 표는 **분할**이다 — 합계가 다른 이유를 명시한다

```
4층위 (원인)      C-W 59 ⊇ {C-G 25, C-D 31, C-E 1}   중첩. 합산 불가
6종 (outcome)     상호배타 분할. 합 = 59
```

**두 표를 함께 실을 때 합계가 다른 이유를 반드시 적는다.** 안 적으면 독자가 불일치로 읽는다.

### 3.4.3 `REC-B-8` (C1) — **가드가 존재하는데 배선이 없다. 오늘 가장 무거운 발견이다**

`A2` 규칙 **P-2 를 구현한 `mapping_frozen_allowed()`(`l1_engine.py:100-105`)의
호출부가 `tests/test_pc_fixture_engine.py:491-492` 뿐이다.** 프로덕션 경로에서 아무도 부르지 않는다.

**결과: 전건 `CODEBOOK_PENDING` task 로 본수집이 아무 저항 없이 진행됐다.**

> **"codebook 없이 수집하면 막는다" 는 계약이 코드에 있었는데 연결되지 않았다.**
>
> 오늘 세 번 본 "있다고 가정했으나 없었던" 것의 **네 번째이자 다른 변종**이다 —
> 앞의 셋은 **없었고**, 이번은 **있는데 배선이 없다.** 후자가 더 위험하다:
> 코드를 읽으면 가드가 보이므로 **있다고 믿게 된다.**

`REC-B-7` 과 같은 뿌리다. `REC-B-7`(승격 시점 가드 부재)과 `REC-B-8`(수집 시작 시점 가드 미배선)을
함께 시정한다.

### 3.4.4 `compute_depth()` 는 결함이 아니다 — 호출부다

**Director 가정 정정:** `compute_depth()` 는 complete-case 가 **아니다.**
`depth.py:178-186` 이 endpoint 미도달이라도 area 관측 시 NED 를 살린다.

**따라서 MART 31/31 NULL 의 원인은 depth 로직이 아니라 area 신호가 한 번도 성립하지 않은 것이다.**
`REC-B-6`(C 가 `l1_engine.py:532/540/558/600-616` 에서 찾은 호출부 결함)과 **정합한다** —
C 는 호출부에서 결함을 찾았고 B 는 `compute_depth` 자체가 계약대로임을 확인했다. **두 판정이 일치한다.**

**함의: "부분 depth 보존" 을 `compute_depth` 개선 과제로 두면 대상이 틀린다.**

**잠복 결함:** `assign_depth_segments` 는 step 수준 complete-case 이고
`m = ... else step_count` 대체(`depth.py:215`)로 **IED 가 NULL 인데 step 이 IED 로 라벨링**될 수 있다.
현 MART 는 미오염이나 **복구 후 발현한다.** → `REC-B-9` 로 등록.

### 3.4.5 갭 1·2 는 **독립이다** — 중간 재수집을 넣으면 안 된다

B 가 (c) 질문에 코드로 답했다:

```
B1(wiring) 만 고치면   산문 정의가 존재하지 않는 [data-region] 토큰과 비교돼 여전히 False
B2(detector) 만 고치면 `is None` 조기 반환(:213, :223)에 먼저 걸려 resolver 도달 불가
```

**∴ `REC-B-1~3` 단독 완료는 검증 가능한 결과를 내지 않는다. 중간 재수집을 금지한다.**

### 3.4.6 정의의 성격 — **archetype 수준 산문이지 서비스별 selector 가 아니다**

O-1 부분 확인: CSV 정의는 71/71 non-empty 이지만 **서비스별이 아니라 archetype 당 1개인 한국어 산문**이다
(distinct 7 / 2 / 7 / 3).

> **`REC-B-4` 철회는 유지된다** — 정의는 존재한다. **다만 그 정의를 detector 가 직접 쓸 수 있는
> 형태가 아니다.** `"개별 상품 항목의 링크·카드가 목록 형태로 노출"` 은 사람이 읽는 서술이지
> DOM 질의가 아니다. **`REC-B-5`(detector 구현)에 "산문 → 질의" 변환 설계가 포함돼야 한다.**

### 3.4.7 모집단 명시 의무

`endpoint_signal_type` 분포는 **동결 59 기준 `URL_PATTERN` 33 · `DOM_AX_ROLE` 17 · `FORM_STRUCTURE` 9**,
**전체 71행 기준은 42 / 20 / 9** 다. `region_signal_type` 은 동결 59 에서 `DOM_AX_ROLE` 53 · `CODEBOOK_PENDING` 6.

**인용할 때 모집단을 반드시 명시한다.**

---

## 3.5 R4 fixture 검증 결과 — **naive wiring 복구는 안전하지 않다**

C 가 엔진 `222ef2c` 를 fixture 신호로 직접 돌렸다(`assurance/recovery/PARTIAL_DEPTH_FIXTURES.md`,
15 html + 실행 스크립트 + 결과 JSON). **fixture 를 엔진에 맞춰 조정하지 않았다.**

7케이스 중 **3 FAIL**. 두 결함을 등록한다.

### `REC-B-6` (C1) — **wiring 을 고치는 순간 NED 가 다시 사라진다**

```
l1_engine.py:532   area_here 를 계산한다
           :540    endpoint 종료 분기에서만 area_index 대입
           :558    gate 종료 분기에서만 area_index 대입
           :600-616 UNRESOLVED 경로 → area_index = None 을 compute_depth 에 넘긴다
```

**`A1 §1.5` 표 3행 위반** — *"영역만 관측, endpoint 전 종료 → NED=k, IED NULL"* 이 동작하지 않는다.
케이스 1·4 에서 `NED NULL` 로 실측됐다(기대 `NED 0` / `NED 보존`).

**`compute_depth` 자체는 계약대로 동작한다**(케이스 2·4b 가 증거). 결함은 호출부다.

> **E001 에서는 발현하지 않았다** — region 정의가 전부 `None` 이라 애초에 도달하지 못했다.
> **`REC-B-1~3`(wiring)을 고치는 즉시 발현한다.**
>
> **따라서 `REC-B-6` 은 wiring 과 *동시에* 고쳐야 한다. 나중에 고칠 항목이 아니다.**
> 이것을 모르고 wiring 만 복구하면 **NED 가 또 NULL 로 나오고, 원인을 다시 찾게 된다.**

### `REC-B-7` (C1) — **PENDING 정의로 endpoint 승격이 일어난다**

```
TaskDefinition.mapping_frozen_allowed()  (:100-105)   호출자 0
detector                                              signal_type 을 읽지 않는다
승격 (:538-543) · Path Freeze (:662-680)              P-2 가드 없음
```

**케이스 5b 실증:** 정의 문자열 + `CODEBOOK_PENDING` 상태에서
**`FUNCTION_ENDPOINT_REACHED` 0/1/1 산출 + TaskManifest 동결**이 일어났다.

**이는 §4-5 「`UNDETERMINED` 를 `PASS`/endpoint 로 승격하지 않는다」의 직접 위반이다.**

> **E001 에서 발현하지 않은 이유가 우연이다** — 케이스 5a(정의 `None` + `PENDING`, E001 실제 구성)는
> 승격 0 이었으나, C 판정대로 그것은 **detector 가 상수 False 를 반환한 부수효과**이지
> 가드가 작동한 것이 아니다. **정의가 채워지는 순간 가드 없는 승격 경로가 열린다.**

### 복구 순서 — **`REC-B-8` 을 선행조건으로 격상한다 (정정)**

> **이 절을 처음에는 "한 묶음으로 시정" 이라고 썼다. 부족하다. 순서가 있어야 한다.**

**핵심은 이것이다 — 이건 "측정이 안 된다" 가 아니라 "틀린 측정이 나온다" 다.**

```
오늘        default_task_definition() 이 정의를 None 으로 만들어 승격 경로에 도달하지 못했다
            → 결과가 0 이었지만 **오염되지는 않았다**

naive B1    정의 문자열이 들어오고 mapping_status 는 여전히 CODEBOOK_PENDING 인데
            가드가 꺼져 있어 승격이 일어난다
            → **오늘의 "정직한 0" 이 "근거 없는 값" 으로 바뀐다**
```

**복구가 오늘의 산출물보다 나쁜 것을 만들 수 있다.** 이것이 순서를 강제하는 이유다.

```
선행   REC-B-8   mapping_frozen_allowed() 프로덕션 배선     ← 없으면 B1 이 오염을 만든다
  ↓
B1     REC-B-1~3 task definition wiring
       REC-B-6   l1_engine area_index 대입 분기 (동시)
  ↓
B2     REC-B-5   실웹 signal detector          (B1 과 독립. 둘 다 필요)
       REC-B-7   승격·Path Freeze 가드
       REC-B-9   assign_depth_segments IED 라벨링
```

**Director 지시에 이미 있었다** — *"`mapping_status` 가 `CANDIDATE`/`AMBIGUOUS`/`CODEBOOK_PENDING`
인 상태를 임의로 `FROZEN` 으로 승격하지 않는다."*
**그 규칙을 강제할 게이트가 꺼져 있다는 것이 지금 확인된 것이다.**

### `PHASE B4`(부분 depth 보존)의 대상 정정

```
✗  compute_depth()          — complete-case 가 아니다. 계약대로 동작한다 (B 확인)
○  l1_engine 대입 분기      — REC-B-6. area_here 를 계산하고도 UNRESOLVED 경로에서 버린다
```

**Director 가정과 다르다.** 진짜 손실 지점은 `compute_depth` 위 단계다.

**`R4`(partial-depth semantics)는 현재 `FAIL` 이다.** `GO_POST_E001_RECOVERY_REAL` 조건 미충족.

> **E001 의 "모든 정의가 None" 상태가 이 두 결함을 가리고 있었다.**
> 오늘 관측이 0 이었던 것이 **결함을 숨긴 대가**이기도 하다 — 값이 나왔다면 두 결함이
> 조용히 잘못된 값을 만들었을 것이다.

---

## 4. 복구 원칙 — 동결

1. **prohibited action set 을 절대 완화하지 않는다** — 로그인·결제·OTP·본인인증·PII·CAPTCHA 우회
2. **가드 입도만 정밀화 가능** — target 중단 → 후보 제외 후 나머지 경로 탐색. **클릭 금지는 그대로**
3. **`NED`/`IED`/`MPFED` 는 각각 별도 observability/denominator 를 가진다**
4. **endpoint 미도달이어도 region 도달이 검증되면 `NED` 를 보존할 수 있도록 계약을 검토한다**
   — 검토 대상이지 확정이 아니다. `A1`/`A2` 개정과 독립감사를 거친다
5. **`UNDETERMINED` 를 `PASS`/endpoint 로 승격하지 않는다** — E-6b fail-closed 유지
6. **KWCAG raw evidence 만으로 판정 불가능한 criterion 은 `UNDETERMINED`/`NA`**
7. **축 C `UNKNOWN` 을 임의 label 로 강제 치환하지 않는다.** `final_label` overwrite 금지 —
   semantic adjudication 은 **별도 recovery layer** 로 쌓는다
8. **새 association 을 현재 데이터 결과를 보고 선택하지 않는다**
9. **REAL_TARGET recovery 는 B 구현 + C 독립검증 + A GO 승인 전 금지**

---

## 5. Recovery Gates

| Gate | 내용 | 판정 |
|---|---|---|
| **R0** | 현재 E001 freeze 검증 — SHA·해시·행수가 오늘 값과 동일함을 재확인 | C 검증 → A |
| **R1** | task-definition lineage 복구 — `REC-B-1~3` 시정, P-B CSV 5필드가 `TaskDefinition` 까지 도달 | B → C |
| **R2** | 실 signal detector fixture 검증 — `detect_area_signal`/`detect_endpoint_signal` 이 실제 값으로 동작 | B → C |
| **R3** | candidate-level 안전 가드 검증 — 후보 제외 방식이 **클릭 0** 을 유지하는지 실증 | B → **C 필수** |
| **R4** | partial-depth 의미론 검증 — region 도달 시 `NED` 보존 가능 여부. **`A1`/`A2` 개정 필요 여부 판정** | A + 독립감사 |
| **R5** | KWCAG evaluator 검증 — raw 만으로 판정 가능/불가능 criterion 분리, 불가능은 `UNDETERMINED`/`NA` | B → C |
| **R6** | obstruction semantic adjudication 검증 — 원본 `final_label` 무변경, 별도 layer | B → C |
| **R7** | 독립 C 감사 — R1~R6 전체 | C |
| **R8** | recovery REAL_TARGET **GO / NO-GO** | **A 단독** |

**R4 는 measurement 계약에 닿는다.** `A1`/`A2` 개정이 필요하면 **독립감사를 거치며,
오늘의 계약을 소급 적용하지 않는다.**

### 5.1 축 A criterion 분리 (R5 입력)

Pilot 코드북 33개를 **재판정 가능성**으로 가른다:

| 구분 | 근거 |
|---|---|
| **기존 L0 evidence 만으로 재판정 가능** | DOM · AX · computed CSS · geometry · screenshot 으로 결정 가능한 것 (예: 대비, 레이블 존재, lang 속성, 마크업 오류) |
| **추가 live observation 필요** | 상호작용·시간·상태변화가 필요한 것 (예: 응답시간 조절, 정지 기능, 초점 이동) |
| **`NOT_AUTOMATABLE`** | 코드북이 이미 그렇게 표시한 8건 — `UNDETERMINED`/`NA` |

**이 분리는 R5 에서 수행하며, 오늘 하지 않는다.** 분리 자체가 measurement 판단이므로
**결과를 보기 전에** 확정하고 독립감사를 받는다.

---

## 6. 오늘 FINAL 과의 관계

**16:30 FINAL 경로를 중단하거나 수정하지 않는다.** 이 문서 때문에 오늘 산출을 지연하지 않는다.

**FINAL 에서 세 문장을 명확히 구분한다:**

```
①  오늘 관측된 사실
    E001 59/59 · MPFED 0/59 · interrupt 235 · UNKNOWN 110 · 전면 덮음 22 …

②  오늘 구현 때문에 계산할 수 없었던 것
    축 A criterion 판정 · 축 B endpoint/region 신호 · 축 C semantic 분류 ·
    association(PRIMARY·SECONDARY)

③  post-E001 에서 복구해야 할 measurement implementation
    REC-B-1~4 · KWCAG evaluator · obstruction semantic layer
```

**②와 ③을 ①에 섞지 않는다.** ①은 관측이고 ②는 도구의 상태이며 ③은 계획이다.

---

## 7. 변경이력

| 시각 | 내용 | 데이터 관측 이후인가 |
|---|---|---|
| 2026-08-27 15:30 | 최초 개설 | **예 — E001 완료 후.** 다만 이 문서의 근거는 **결과값이 아니라 코드 사실**이다(`default_task_definition()` docstring · `TargetSpec` 필드 목록 · evaluator 부재). 관측된 FailRate·coverage·상관은 입력으로 쓰이지 않았다. |
