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
| `REC-B-4` | P-A endpoint codebook 이 동결되지 않았다 — `PHASE_GATES` P-A 미수행 항목 |

> **`REC-B-4` 가 상류이고 `REC-B-1~3` 이 하류다.** codebook 이 있어도 wiring 이 없으면
> 값이 도달하지 않고, wiring 이 있어도 codebook 이 없으면 채울 값이 없다. **둘 다 필요하다.**

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
