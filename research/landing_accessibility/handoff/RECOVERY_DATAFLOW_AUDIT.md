# RECOVERY_DATAFLOW_AUDIT — P-B CSV → depth 산출까지 field-by-field 추적

- 작성: Claude B 산하 워커 (POST-E001 MEASUREMENT RECOVERY 1단계)
- 워크트리: `.agent_worktrees/claude_b_recovery` / 브랜치 `claude-b/measurement-recovery`
- 감사 대상 SHA: `222ef2c` (E001 수집기 SHA와 동일)
- **이 감사는 코드를 한 줄도 고치지 않았다.** 읽기 + 기존 산출물 재집계만 했다.
- 경로 표기: `research/landing_accessibility/` 를 `R/` 로 줄인다.

---

## 0. 요약 (먼저 읽을 것)

Director가 제시한 관찰 5건 중 **4건 확인, 1건 부분 확인**이다. 그리고 감사 중
**Director가 언급하지 않은 결함 7건**이 나왔다. 그중 F-1/F-5는 "필드 전달을 고치면
측정이 살아난다"는 전제 자체를 무효화한다.

Coordinator가 전달한 Claude C의 확정 사실과 4층위 원인 분해도 **C의 진술이 아니라
코드·실측에서 독립 재확인**했다 — §6·§7. C의 signal_type 분포(33/17/9)는 동결 59건
기준으로 정확히 재현됐고, 4층위 중 3개는 확인, C-E 1개는 규모가 12건이 아니라 1건이다.

| | 내용 | 판정 |
|---|---|---|
| O-1 | P-B CSV 에 region/endpoint 정의·signal type 존재 | **확인됨** |
| O-2 | `E001TargetRow` 가 일부 필드를 버린다 | **확인됨** (5개 버림) |
| O-3 | `TargetSpec` 에 endpoint_definition 은 전달, region 계열은 미전달 | **확인됨** |
| O-4 | `default_task_definition()` 이 None/None/CODEBOOK_PENDING/CODEBOOK_PENDING 을 만든다 | **확인됨** (하드코딩) |
| O-5 | `detect_endpoint_signal()` 은 endpoint_definition is None 이면 항상 False | **부분 확인** — 참이지만, **None 이 아니어도 실사이트에서는 항상 False** 다 |
| F-1 | area/endpoint detector 는 fixture 전용 `data-region`/`data-endpoint` 속성만 읽는다 — **실사이트용 구현이 아예 없다** | 신규 |
| F-2 | `region_signal_type`/`endpoint_signal_type` 은 **어떤 판정에서도 소비되지 않는다**. 유일한 reader `mapping_frozen_allowed()` 는 테스트에서만 호출된다 | 신규 |
| F-3 | 목표-수준 가드(`screen_candidates`)가 **QUERY archetype 5/5 전건을 삭제**했다 — codebook 없이도 area 신호가 성립하는 유일한 archetype이다 | 신규 |
| F-5 | 갭 1(wiring)과 갭 2(detector)는 **독립이다** — 어느 한쪽만 고치면 NED/MPFED 는 여전히 전건 NULL 이다 (§6) | 신규 |
| F-6 | `*_signal_type` 은 서비스별 값이 아니라 **archetype 의 1:1 함수**다 — 정보량 0, 그러나 B2 설계 범위를 3종으로 닫아 준다 (§6.2) | 신규 |
| F-7 | Claude C 의 4층위 중 **C-E(endpoint 계약)의 회수 가능 규모는 12건이 아니라 1건**이다 (§7) | 신규 |

추가 판정:

- `screen_candidates()` 는 **target-level guard 다** (확인). 위험 후보 1건만 있어도 그 target 의 L1 전체를 건너뛴다.
- `compute_depth()` 는 **complete-case 가 아니다** (Director 가정과 다름). endpoint 미도달이라도 area 가 관측됐으면 NED 를 살린다. 실측에서 NED 가 전건 NULL 인 것은 `compute_depth` 때문이 아니라 **area 신호가 애초에 한 번도 성립하지 않았기 때문**이다. 단 `assign_depth_segments()` 는 step 수준에서 complete-case 이고, 별도의 정합성 결함이 하나 있다 (§4).

---

## 1. 필드 보존 표 (8필드 × 11단계)

범례: `보존` / `소실` / `변형(→값)` / `해당없음`(그 단계가 그 필드를 다루는 지점이 아님)

단계 약칭:

| # | 단계 | 파일 |
|---|---|---|
| S1 | `representative_task_candidate_shadow.csv` | `R/shadow/lane_b/state/…csv` |
| S2 | `load_e001_full_targets()` | `R/src/landing_accessibility/engine/firewall.py:635-730` |
| S3 | `E001TargetRow` | `firewall.py:542-554` |
| S4 | `run_e001_real._worker_plan()` | `R/scripts/run_e001_real.py:64-77` |
| S5 | `TargetSpec` | `R/src/landing_accessibility/e001_runner/plan.py:35-69` |
| S6 | `real_executor.run_l1_if_safe_real()` | `…/e001_runner/real_executor.py:110-155` |
| S7 | `default_task_definition()` | `…/e001_runner/executor.py:57-75` |
| S8 | `TaskDefinition` | `…/engine/l1_engine.py:83-105` |
| S9 | `detect_area_signal()` | `l1_engine.py:201-218` |
| S10 | `detect_endpoint_signal()` | `l1_engine.py:221-231` |
| S11 | `compute_depth()` | `…/engine/depth.py:141-203` |

| 필드 \ 단계 | S1 CSV | S2 loader | S3 Row | S4 worker_plan | S5 TargetSpec | S6 real_exec | S7 default_task | S8 TaskDef | S9 area | S10 endpoint | S11 depth |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `task_id` | 보존 | 보존 | 보존(사용처 0) | **소실** | 해당없음 | 변형(→`task-{target_id}`) | 변형(→`task-{target_id}`) | 보존(변형값) | 해당없음 | 해당없음 | 해당없음 |
| `interaction_archetype` | 보존 | 보존 | 보존 | 보존 | 보존 | 보존 | 보존 | 보존 | 보존(분기에 사용) | 해당없음 | 보존(사용) |
| `primary_function_name` | 보존 | **소실** | 해당없음 | 해당없음 | 해당없음 | 해당없음 | 해당없음 | 해당없음 | 해당없음 | 해당없음 | 해당없음 |
| `region_definition` | 보존 | **소실** | 해당없음 | 해당없음 | 해당없음 | 해당없음 | **변형(→`None`)** | 보존(`None`) | 사용 → 항상 False (비-QUERY) · **비교 대상이 fixture 전용 `[data-region]`** | 해당없음 | 간접(→`area_step_index=None`) |
| `region_signal_type` | 보존 | **소실** | 해당없음 | 해당없음 | 해당없음 | 해당없음 | **변형(→`CODEBOOK_PENDING`)** | 보존(변형값) | **미소비** | **미소비** | 해당없음 |
| `endpoint_definition` | 보존 | 보존 | 보존 | 보존 | 보존 | **소실**(읽히지 않음) | **변형(→`None`)** | 보존(`None`) | 해당없음 | 사용 → 항상 False · **비교 대상이 fixture 전용 `[data-endpoint]`/`body[data-endpoint-reached]`** | 간접(→`endpoint_step_index=None`) |
| `endpoint_signal_type` | 보존 | **소실** | 해당없음 | 해당없음 | 해당없음 | 해당없음 | **변형(→`CODEBOOK_PENDING`)** | 보존(변형값) | **미소비** | **미소비** | 해당없음 |
| `mapping_status` | 보존 | **소실**(상류 소비) | 해당없음 | 해당없음 | 해당없음 | 해당없음 | 해당없음 | 해당없음 | 해당없음 | 해당없음 | 해당없음 |

### 1.1 셀별 근거

**`task_id`**
- S1 71/71 non-empty, 71개 distinct (`task_shadow_11st`, `task_shadow_adot_call` …).
- S2/S3 `firewall.py:722` `task_id=(task.get("task_id") or "").strip() or None` → `firewall.py:554` 필드로 저장. **읽는 코드가 저장소 전체에 없다** (`grep -rn "task_id"` 결과: 정의 2곳 + 합성값 2곳뿐).
- S4 `run_e001_real.py:66-74` 가 `TargetSpec(...)` 을 만들 때 `task_id` 를 넘기지 않는다. 넘길 수도 없다 — S5 `plan.py:44-51` 에 `task_id` 필드가 없다.
- S6 `real_executor.py:66` `task_id=f"task-{target.target_id}"`; S7 `executor.py:69` 동일 합성.
- **실측 확인**: frozen MART `fact_task_entry.json` 의 `task_id` 는 전건 `task-wtg_…` 형식이며 `task_shadow_*` 는 0건이다.

**`interaction_archetype`**
- S2 `firewall.py:701` `archetype = (task.get("interaction_archetype") or "").strip()`, 비면 S2에서 예외(`firewall.py:702-706`).
- S4 `run_e001_real.py:71` → S5 `plan.py:47` → S6 `real_executor.py:65` (`InteractionArchetype(...)`) 및 S7 `executor.py:67` → S8 `l1_engine.py:93`.
- S9 `l1_engine.py:208` QUERY 분기의 유일한 입력. S10 은 archetype 을 읽지 않는다.
- S11 `depth.py:143` + `ENDPOINT_GATE_KINDS` (`depth.py:35-45`).

**`primary_function_name`**
- S1 71/71 non-empty, 7개 distinct (archetype 당 1개).
- S2 `firewall.py:712-723` 의 `E001TargetRow(...)` 생성자에 없다. `grep -rn "primary_function_name" R/src R/scripts` → **0 hit**. 파이프라인 어디에도 등장하지 않는다.

**`region_definition`**
- S1 71/71 non-empty. 값은 서비스별 토큰이 아니라 **archetype 당 1개인 한국어 산문**이다 (예: `'개별 상품 항목의 링크·카드가 목록 형태로 노출'`).
- S2 미독취 (`firewall.py:712-723`), S3 필드 없음 (`firewall.py:542-554`), S5 필드 없음 (`plan.py:44-51`).
- S7 `executor.py:71` `region_definition=None` — **하드코딩**. S6 이 `target` 에서 무엇을 갖고 있든 무관하다.
- S9 `l1_engine.py:213-214` `if task.region_definition is None: return False`.

**`region_signal_type`**
- S1 71/71 non-empty; 분포 `DOM_AX_ROLE` 63 / `CODEBOOK_PENDING` 8. 동결된 59건 기준 `DOM_AX_ROLE` 53 / `CODEBOOK_PENDING` 6.
- S2 미독취. S7 `executor.py:73` `RegionSignalType.CODEBOOK_PENDING` 하드코딩.
- S9/S10 **어느 detector 도 `region_signal_type` 을 읽지 않는다** — F-2 참조.

**`endpoint_definition`**
- S1 71/71 non-empty. 역시 archetype 당 1개인 산문 (예: `'상품 상세와 핵심 상품정보가 보인 순간'`).
- S2 `firewall.py:721` → S3 `firewall.py:553` → S4 `run_e001_real.py:72` → S5 `plan.py:49`. **여기까지는 실제로 전달된다.**
- S6 `real_executor.py:138` `resolved_task = task or default_task_definition(target)`. `_real_executor` 는 `task=` 를 넘기지 않는다 (`batch.py:258` `run_l1_if_safe_real(target, run=run, scope=scope)`). 따라서 항상 S7 로 간다.
- S7 `executor.py:72` `endpoint_definition=None` — **하드코딩**. `target.endpoint_definition` 을 읽는 줄이 함수 안에 없다. → S5 까지 살아온 값이 여기서 폐기된다.
- S10 `l1_engine.py:223-224` `if task.endpoint_definition is None: return False`.

**`endpoint_signal_type`**
- S1 71/71 non-empty; `URL_PATTERN` 42 / `DOM_AX_ROLE` 20 / `FORM_STRUCTURE` 9.
- S2 미독취. S7 `executor.py:74` `CODEBOOK_PENDING` 하드코딩. S9/S10 미소비 (F-2).

**`mapping_status`**
- S1 71/71 non-empty; `CANDIDATE` 59 / `AMBIGUOUS_UNRESOLVED` 12.
- S2 미독취. 다만 **상류에서 이미 소비됐다**: `R/shadow/e001_plan/E001_MASTER_PLAN.json` 의 `source.candidate_task_n = 59`, `joined_n = 59` 이고, 동결된 59개 key 는 전건 `mapping_status == CANDIDATE` 임을 재집계로 확인했다. 즉 `AMBIGUOUS_UNRESOLVED` 12건 배제는 계획 구성 시점에 끝났고, 이 dataflow 는 그 결과만 받는다.
- `engine/transitions.py:225` 의 `mapping_status` 는 Frame 컬럼 보호 목록(규칙 W-1)일 뿐 이 경로와 무관하다.

---

## 2. Director 관찰 5건 판정

### O-1 "P-B CSV 에는 region/endpoint 정의와 signal type 이 존재한다" — **확인됨**

71행 전건에서 `region_definition`·`region_signal_type`·`endpoint_definition`·`endpoint_signal_type` 이 모두 비어 있지 않다.
분포는 §1.1 참조.

**단, 관찰이 함의하는 것보다 약하다.** 네 값 모두 **archetype 당 1개**로만 distinct 하다
(distinct = 7 / 2 / 7 / 3). 서비스별 값이 아니다. 정의문은 `'기사 본문이 열린 순간'`
같은 **자연어 산문**이며, `detect_*_signal` 이 요구하는 형태(§F-1)와 타입이 다르다.
"CSV 에 값이 있으니 전달만 하면 판정이 성립한다" 는 추론은 성립하지 않는다.

### O-2 "`E001TargetRow` 가 일부 필드를 버린다" — **확인됨**

`firewall.py:542-554` 의 필드는 9개다: `canonical_service_key`, `target_id`,
`official_url`, `interaction_archetype`, `worker_id`, `order_index`,
`service_name_canonical`, `endpoint_definition`, `task_id`.

P-B CSV 27열 중 이 감사가 추적하는 8필드 기준으로 **버려지는 것은 5개**다:
`primary_function_name`, `region_definition`, `region_signal_type`,
`endpoint_signal_type`, `mapping_status`. (`mapping_status` 는 상류에서 이미 소비됨.)

추가: 살아남은 `task_id` 는 **읽는 코드가 없는 dead field** 다 (§1.1).

### O-3 "`TargetSpec` 에는 endpoint_definition 은 일부 전달되지만 region definition/signal type 은 충분히 전달되지 않는다" — **확인됨**

`plan.py:44-51` 의 `TargetSpec` 필드 8개에 `region_definition`·`region_signal_type`·
`endpoint_signal_type`·`task_id` 는 **아예 없다**. "충분히 전달되지 않는다" 가 아니라
**전혀 전달되지 않는다** — 필드가 존재하지 않으므로 부분 전달의 여지도 없다.

`endpoint_definition` 은 `plan.py:49` 에 필드가 있고 `run_e001_real.py:72` 가 실제로
채운다. 확인.

**다만 그 전달은 무의미하다** — §O-4 가 그 값을 읽지 않고 `None` 을 하드코딩한다.
즉 `TargetSpec.endpoint_definition` 은 S5 이후 **소비자가 0명**이다
(`grep -rn "\.endpoint_definition" R/src` 결과: `run_e001_real.py:72` 대입 1건뿐, 독취 0건).

### O-4 "`default_task_definition()` 이 최종적으로 region_definition=None, endpoint_definition=None, region_signal_type=CODEBOOK_PENDING, endpoint_signal_type=CODEBOOK_PENDING 을 만든다" — **확인됨**

`executor.py:68-75` 그대로다. 네 값 모두 **인자 무관 상수**다. `target` 에서 읽는 것은
`target.interaction_archetype`(:67)과 `target.target_id`(:69) 두 개뿐이다.

그리고 **이 함수가 REAL_TARGET 경로의 실제 기본값이다**:
`batch.py:258` → `real_executor.py:138` (`task` 인자 미전달) → `executor.py:118`/`:138`.
E001_FULL 본수집에서 `task=` 를 넘기는 호출부는 없다.

docstring(`executor.py:57-66`)이 서술한 결과와 코드 동작이 일치한다는 것도 확인했다 —
docstring 은 출발점이었지만, 위 근거는 docstring 이 아니라 코드에서 나왔다.

### O-5 "`detect_endpoint_signal()` 은 endpoint_definition is None 이면 항상 False 다" — **부분 확인**

명제 자체는 참이다: `l1_engine.py:223-224` 가 무조건 `return False`.

**부분 확인으로 내리는 이유** — 이 진술은 "None 이 문제이고, None 만 아니면 성립할 수
있다" 는 함의를 갖는데, 그 함의가 **실측으로 거짓**이다. `endpoint_definition` 이 어떤
값이든, `detect_endpoint_signal` 이 비교하는 대상은 `endpoint_signals.declared_endpoints[].endpoint`
(= DOM 의 `[data-endpoint]` 속성값)와 `body_endpoint_reached` (= `body[data-endpoint-reached]`)
뿐이다 (`l1_engine.py:225-231`, `engine/l0_probe.js:333-337`).

E001 실증거 14건의 `probe.json` 을 재집계한 결과:

| 신호 | 분포 (n=14 L0 probe) |
|---|---|
| `declared_endpoints` 길이 | 0: 14건 |
| `body_endpoint_reached` | `null`: 14건 |
| `declared_regions` 길이 | 0: 13건, 1: 1건 |
| `search_inputs` 길이 | 0: 12건, 2: 1건, 1: 1건 |

즉 **실제 서비스는 `data-endpoint` 를 내보내지 않는다.** `endpoint_definition` 을
제대로 전달하더라도 `detect_endpoint_signal` 은 여전히 전건 False 다. → F-1.

---

## 3. `screen_candidates()` 입도 판정 — **target-level guard 다**

`guard.py:170-182`:

```python
def screen_candidates(candidates):
    for candidate in candidates:
        risk = classify_candidate(candidate)
        if risk.blocked:
            return risk          # 첫 위험 후보에서 즉시 반환
    return None
```

호출부 `real_executor.py:127-136` / `executor.py:106-115`:

```python
risk = screen_candidates(candidates)
if risk is not None:
    return {"outcome": ACCOUNT_ACTION_BLOCKED, "scout_invoked": False, ...}
```

`Scout` 객체 자체가 생성되지 않는다. **위험 후보를 목록에서 제외하고 나머지로 진행하는
경로가 없다** — candidate-level 필터가 아니다. 이것은 의도된 설계다
(`guard.py:175-176` docstring: branching_limit 이 미검사 후보를 나중에 클릭할 수 있으므로
"가장 area 가 큰 후보만 검사"하지 않는다).

### 3.1 실측 영향

E001_FULL 59건 배치 결과 재집계 (`.agent_worktrees/claude_b_e001_worker_*/artifacts/*/batches/*.json`):

| outcome | n |
|---|---|
| `ACCOUNT_ACTION_BLOCKED` | **25** (42.4%) |
| `UNRESOLVED` | 18 |
| `AUTH_GATE` | 12 |
| `SKIPPED_RETRY_EXHAUSTED` | 3 |
| `CAPTCHA` | 1 |

차단 사유 분포: `LOGIN` 19 / `PURCHASE` 3 / `SIGNUP` 2 / `PAYMENT` 1.
19건 중 대부분의 `blocked_reason` 은 문자 그대로 `matched text: '로그인 로그인'` 이다 —
**랜딩 화면에 로그인 링크가 존재한다는 사실만으로** 그 target 의 L1 전체가 삭제됐다.
클릭은 하지 않았고, 클릭할 후보로 선택된 것도 아니다.

archetype × outcome (동결계획 59건 전건 조인, 미매칭 0):

| archetype | n | 결과 |
|---|---|---|
| ITEM_DETAIL | 26 | BLOCKED 10 / UNRESOLVED 9 / AUTH_GATE 7 |
| FINANCIAL_ACTION_ENTRY | 11 | BLOCKED 6 / UNRESOLVED 3 / AUTH_GATE 1 / RETRY_EXHAUSTED 1 |
| UTILITY_ENTRY | 6 | BLOCKED 3 / AUTH_GATE 1 / UNRESOLVED 1 / RETRY_EXHAUSTED 1 |
| **QUERY** | **5** | **BLOCKED 4 / RETRY_EXHAUSTED 1 — Scout 도달 0건** |
| COMMUNICATION_ENTRY | 4 | UNRESOLVED 2 / BLOCKED 2 |
| PLACE_LOOKUP | 4 | UNRESOLVED 2 / AUTH_GATE 2 |
| CONTENT_OPEN | 3 | UNRESOLVED 1 / AUTH_GATE 1 / CAPTCHA 1 |

→ F-3 참조. QUERY 는 codebook 없이도 area 신호가 성립하는 **유일한** archetype
(`l1_engine.py:208-212`)인데, 5건 전부가 가드/재시도소진으로 Scout 에 도달하지 못했다.

---

## 4. `compute_depth()` complete-case 여부 판정 — **complete-case 가 아니다** (Director 가정과 다름)

`depth.py:166-186`:

```python
if not reached:
    if area_step_index is None:
        return DepthResult(None, None, None, NOT_OBSERVED, ...)   # 셋 다 NULL
    return DepthResult(area_step_index, None, None, OBSERVED, ...) # NED 는 살린다
```

**endpoint 미도달이라도 area 가 관측됐으면 NED 는 보존된다.** NED/IED/MPFED 가 하나의
complete-case 로 묶여 있지 않다. 모듈 docstring(`depth.py:7`)도 `NULL` 을 `0`/상한값으로
대체하지 않는다는 규칙만 명시하고, NED 를 함께 버리라고 하지 않는다.

따라서 **실측에서 NED 가 전건 NULL 인 원인은 `compute_depth` 가 아니다.**
frozen MART `fact_task_entry.json` (n=31, Scout 가 실제로 돈 관측):

| 컬럼 | 분포 |
|---|---|
| `NED` | `null` 31/31 |
| `IED` | `null` 31/31 |
| `MPFED` | `null` 31/31 |
| `endpoint_reached` | `"0"` 31/31 |
| `endpoint_status` | UNRESOLVED 18 / AUTH_GATE_REACHED 11 / CAPTCHA 1 / PAYMENT_GATE_REACHED 1 |

`area_step_index` 는 `l1_engine.py:532` `_first_index(landing_area, steps, "area_signal_detected")`
로 만들어지고, 그 입력 `obs.area` 는 `detect_area_signal` (`l1_engine.py:326`) 이다.
비-QUERY 에서 `region_definition is None` → 항상 False → `area_step_index=None` →
`compute_depth` 가 규칙대로 `NOT_OBSERVED` + 전부 NULL 을 낸다.
**즉 depth 산출은 정직하게 동작했고, 굶주린 것은 그 입력이다.**

### 4.1 `assign_depth_segments()` — step 수준에서는 complete-case 이고, 정합성 결함이 하나 있다

`depth.py:212-213`:

```python
if depth.area_signal_status is AreaSignalStatus.NOT_OBSERVED:
    return [DepthSegment.UNASSIGNED] * step_count
```

area 미관측이면 **관측된 step 이 있어도 전부 `UNASSIGNED`** 다. 다만 `NOT_OBSERVED` 는
`compute_depth` 에서 endpoint 미도달 ∧ area 미관측일 때만 나오므로(도달했는데 area 가
없으면 `INFERRED_FROM_ENDPOINT`), NED/IED 중 하나라도 정의된 상태를 버리지는 않는다.

**정합성 결함 (신규):** `depth.py:214-215`

```python
k = depth.ned if depth.ned is not None else 0
m = depth.mpfed if depth.mpfed is not None else step_count
```

endpoint 미도달 + area 관측 케이스에서 `MPFED` 는 정의상 NULL 인데, 여기서 `m` 이
`step_count` 로 대체된다. 그 결과 `k` 이후의 step 들이 **`DepthSegment.IED` 로 라벨링된다
— `IED` 값 자체는 NULL 인데도.** step 라벨과 집계 컬럼이 서로 다른 사실을 주장하게 된다.
`depth.py:7` 이 금지한 "NULL 을 상한값으로 대체" 와 형태가 같다.
E001 실측에서는 area 가 한 번도 관측되지 않아 이 분기가 발화하지 않았으므로 **현재
frozen MART 는 오염되지 않았다.** 측정 복구로 area 신호가 살아나면 즉시 노출된다.

---

## 5. Director 가 언급하지 않은 발견

### F-1 (P0) area/endpoint detector 에 실사이트용 구현이 없다

`detect_area_signal` / `detect_endpoint_signal` 이 읽는 신호의 **유일한 생산자**는
`engine/l0_probe.js:309-337` 이고, 거기서 나오는 것은:

- `declared_regions` ← `document.querySelectorAll('[data-region]')`
- `declared_endpoints` ← `document.querySelectorAll('[data-endpoint]')`
- `body_endpoint_reached` ← `document.body.getAttribute('data-endpoint-reached')`

이 세 속성은 **P-C fixture 가 스스로 선언하는 합성 마크업**이다
(`l1_engine.py:88-89` docstring 이 그렇게 명시한다). 실제 서비스가 내보낼 이유가 없다.

실증거 재집계(§O-5 표)로 확인: `declared_endpoints` 0건/14, `body_endpoint_reached`
null 14/14. `declared_regions` 가 1건 나온 것은 해당 사이트가 우연히 `data-region` 속성을
쓴 경우이며, 그 값이 우리 codebook 토큰과 일치할 이유는 없다 — 오히려 **우연 일치가
생기면 위양성 area 신호**가 된다.

`endpoint_signal_type` 이 선언한 `URL_PATTERN`(42건) / `FORM_STRUCTURE`(9건) 에 대응하는
판정 코드는 저장소에 **존재하지 않는다** (§F-2).

**함의:** "필드를 제대로 전달하면 측정이 살아난다" 는 복구 가설은 성립하지 않는다.
전달을 고쳐도 `detect_*_signal` 은 여전히 전건 False 다. 복구는 **detector 를 실사이트
관측(URL 패턴 / DOM·AX role / form 구조)에서 성립하도록 조작화하는 작업**을 반드시
포함해야 한다. 필드 배관만 고치면 결과는 바뀌지 않고 "고쳤다" 는 착각만 남는다.
→ 갭 독립성의 형식 판정과 B1/B2 순서 함의는 **§6.3**.

### F-2 (P1) `*_signal_type` 은 어떤 판정에서도 소비되지 않는다

`grep -rn "region_signal_type\|endpoint_signal_type" R/src` 전수:

| 위치 | 성격 |
|---|---|
| `l1_engine.py:96-97` | dataclass 필드 정의 |
| `l1_engine.py:100-105` `mapping_frozen_allowed()` | 유일한 reader |
| `executor.py:73-74` | 상수 대입 |
| `vocabulary.py:335` | 스키마 바인딩 표 |

`detect_area_signal`/`detect_endpoint_signal`/`compute_depth` 중 어느 것도 signal_type 을
읽지 않는다. 즉 `DOM_AX_ROLE` 이든 `URL_PATTERN` 이든 `FORM_STRUCTURE` 든 **판정 경로가
동일하다** — signal_type 은 현재 선언적 메타데이터일 뿐이다.

그리고 `mapping_frozen_allowed()` 의 호출부는 `tests/test_pc_fixture_engine.py:491-492`
**뿐이다.** A2 규칙 P-2(`CODEBOOK_PENDING` 인 task 는 FROZEN 으로 전이 불가)를 코드로
구현해 놓고 **실행 경로에 배선하지 않았다.** 그래서 E001_FULL 본수집이 전건
`CODEBOOK_PENDING` task 로 아무 저항 없이 진행됐다. 이 감사가 지금 찾아낸 상태를
**실행 직전에 자동으로 막았어야 할 게이트가 있었고, 그것이 꺼져 있었다.**

### F-3 (P1) 목표-수준 가드가 유일하게 측정 가능했던 archetype 을 전멸시켰다

`detect_area_signal` 의 QUERY 분기(`l1_engine.py:208-212`)는 `region_definition` 을
읽지 않는다 — `search_inputs` 의 `visible ∧ in_form ∧ has_submit` 만 본다. 즉
**codebook 이 없어도 area 신호가 성립할 수 있는 유일한 archetype 이 QUERY 다.**

그런데 QUERY 5건 전부가 Scout 에 도달하지 못했다 (BLOCKED 4 + RETRY_EXHAUSTED 1, §3.1).
검색 중심 서비스의 랜딩은 거의 예외 없이 헤더에 "로그인" 링크를 갖고, 그것이
`guard.py:101` 의 LOGIN 패턴에 걸리며, 가드가 target-level 이라 L1 전체가 삭제된다.

**두 결함이 독립이 아니라 곱해졌다.** codebook 미동결로 6개 archetype 이 신호를 잃고,
가드 입도로 남은 1개 archetype 이 표본에서 사라졌다. 그 결과가 NED 31/31 NULL 이다.
가드 입도를 그대로 둔 채 codebook 만 채우면 QUERY 는 여전히 0건이고, 가드만 완화하면
비-QUERY 는 여전히 신호가 없다.

### F-4 (P2) 정합성·위생 지적 (측정 결과에 현재 영향 없음)

1. `E001TargetRow.task_id` 는 CSV 에서 읽어 저장되지만 reader 가 0명이다
   (`firewall.py:554`, `:722`). P-B 의 `task_id` 는 최종 산출물 어디에도 남지 않고,
   MART 의 `task_id` 는 `task-{web_target_id}` 합성값이다 — **P-B 대표과제 정의와
   측정 결과를 join 할 키가 산출물에 없다.**
2. `TargetSpec.endpoint_definition` 은 채워지지만 독취가 0건이다 (§O-3). 현재는
   "전달되는 것처럼 보이는데 소비되지 않는" 상태라 감사에서 오독을 유발한다.
3. `assign_depth_segments` 의 `m = ... else step_count` 대체 (§4.1).
4. `TaskDefinition.query_text` 기본값 `"고령자 접근성"` (`l1_engine.py:98`)은 QUERY
   archetype 의 실측 입력인데 `default_task_definition` 이 이를 명시하지 않아
   dataclass 기본값에 의존한다. QUERY 가 복구되면 이 문자열이 **모든 서비스에서 동일한
   검색어**로 쓰인다는 사실이 결과 해석에 들어가야 한다.

---

## 6. 갭 1(wiring) vs 갭 2(detector) — **독립이다. 종속이 아니다.**

Coordinator 가 전달한 Claude C 확정 사실을 **C 의 진술이 아니라 코드에서** 재확인했다.

### 6.1 detector 가 실제로 읽는 것 (코드 전문)

`l1_engine.py:201-218` / `:221-231` 본문에서 `task` 로부터 오는 값과 관측에서 오는 값을
분리하면:

| detector | task 측 입력 | 관측 측 비교 대상 | 관측 대상의 생산자 |
|---|---|---|---|
| `detect_area_signal` (QUERY 분기, `:208-212`) | `task.archetype` 만 | `region_signals.search_inputs[].{visible,in_form,has_submit}` | `l0_probe.js:316-326` — `input[type=search]`,`[role=searchbox]`,`[role=combobox]` **일반 DOM 질의** |
| `detect_area_signal` (비-QUERY, `:213-218`) | `task.region_definition` | `region_signals.declared_regions[].region` | `l0_probe.js:309-315` — **`document.querySelectorAll('[data-region]')`** |
| `detect_endpoint_signal` (`:223-231`) | `task.endpoint_definition` | `endpoint_signals.body_endpoint_reached`, `declared_endpoints[].endpoint` | `l0_probe.js:334-337` — **`[data-endpoint]`, `body[data-endpoint-reached]`** |

→ **C 의 진술은 확인됨.** `data-region`/`data-endpoint`/`data-endpoint-reached` 는
P-C fixture 가 자신의 정답을 선언하기 위해 심는 속성이며(`l1_engine.py:88-89` docstring 이
"fixture 가 `data-region` / `data-endpoint` 로 선언한 토큰을 그 자리에 넣는다" 고 명시),
상용 사이트가 내보낼 이유가 없다. **§O-5 의 실증거 재집계가 이를 뒷받침한다**
(`declared_endpoints` 0/14, `body_endpoint_reached` null 14/14).

**단 하나의 예외**: QUERY 분기는 `data-*` 에 의존하지 않는 **유일한 실사이트 동작 경로**다.
그리고 그 유일한 경로의 대상 5건이 전부 가드에 삭제됐다 (F-3).

### 6.2 `*_signal_type` 분포 — 독립 재계산

Coordinator 가 전달한 C 의 값: `URL_PATTERN` 33 · `DOM_AX_ROLE` 17 · `FORM_STRUCTURE` 9.

독립 재계산 결과 (`E001_MASTER_PLAN.frozen_collection_order` 59 key 로 CSV 를 조인):

| `endpoint_signal_type` | 동결 59 | 전체 71 |
|---|---|---|
| `URL_PATTERN` | **33** | 42 |
| `DOM_AX_ROLE` | **17** | 20 |
| `FORM_STRUCTURE` | **9** | 9 |

| `region_signal_type` | 동결 59 | 전체 71 |
|---|---|---|
| `DOM_AX_ROLE` | **53** | 63 |
| `CODEBOOK_PENDING` | **6** | 8 |

→ **C 의 33/17/9 는 동결 59 기준으로 정확히 일치한다. 확인됨.**
(전체 71행 기준은 42/20/9 이므로, 인용 시 어느 모집단인지 반드시 명시해야 한다.)

**신규 관찰 F-6 — signal_type 은 archetype 의 1:1 함수다:**

| archetype | n(59) | `region_signal_type` | `endpoint_signal_type` |
|---|---|---|---|
| ITEM_DETAIL | 26 | DOM_AX_ROLE | URL_PATTERN |
| FINANCIAL_ACTION_ENTRY | 11 | DOM_AX_ROLE | DOM_AX_ROLE |
| UTILITY_ENTRY | 6 | **CODEBOOK_PENDING** | DOM_AX_ROLE |
| QUERY | 5 | DOM_AX_ROLE | FORM_STRUCTURE |
| COMMUNICATION_ENTRY | 4 | DOM_AX_ROLE | URL_PATTERN |
| PLACE_LOOKUP | 4 | DOM_AX_ROLE | FORM_STRUCTURE |
| CONTENT_OPEN | 3 | DOM_AX_ROLE | URL_PATTERN |

archetype 당 값이 정확히 하나다 — **서비스별 정보량이 0**이다. 이것은 두 가지를 뜻한다:

1. (부정) signal_type 은 "이 서비스의 endpoint 를 어떻게 잡는가" 를 말해 주지 않는다.
   서비스별 판정 규칙은 여전히 P-A codebook 이 공급해야 한다.
2. (긍정, **B2 범위 확정 근거**) 그러나 **B2 가 구현해야 할 resolver 는 정확히 3종**이며
   (`URL_PATTERN`·`DOM_AX_ROLE`·`FORM_STRUCTURE`) 그 3종이 동결 59건 전건과
   7개 archetype 전부를 덮는다. 네 번째 종류를 새로 설계할 필요가 없다.
   `region` 측은 `DOM_AX_ROLE` 1종이 53/59 를 덮고, 나머지 6건(UTILITY_ENTRY)은
   **P-B 자신이 이미 `CODEBOOK_PENDING` 으로 선언**했으므로 B2 로 해결되지 않고
   P-A codebook 이 필요하다 — 이 6건은 B2 완료 후에도 area 신호가 성립하지 않는다.

### 6.3 독립성 판정 — **독립이다**

| 시나리오 | `detect_area_signal` | `detect_endpoint_signal` | NED/MPFED |
|---|---|---|---|
| 현행 (B1·B2 둘 다 미시행) | 비-QUERY: `region_definition is None` → False (`:213`) | `endpoint_definition is None` → False (`:223`) | 전건 NULL |
| **B1 만 시행** (wiring 복구, detector 불변) | `region_definition` = `'개별 상품 항목의 링크·카드가 목록 형태로 노출'` ≠ 실사이트 `[data-region]` 토큰(=존재하지 않음) → **여전히 False** | `endpoint_definition` ≠ `body[data-endpoint-reached]`(=`null`) → **여전히 False** | **전건 NULL 유지** |
| **B2 만 시행** (resolver 구현, wiring 불변) | `region_definition is None` 조기 반환(`:213-214`)에 먼저 걸려 resolver 에 도달하지 못한다 | `endpoint_definition is None` 조기 반환(`:223-224`)에 먼저 걸린다 | **전건 NULL 유지** |
| B1 + B2 | resolver 가 정의를 실관측으로 해석 | 동 | 성립 가능 |

**두 갭은 직렬로 연결된 서로 다른 실패이며, 어느 한쪽도 다른 쪽을 자동으로 해소하지 않는다.**
근거는 위 표의 두 조기 반환 지점(`l1_engine.py:213-214`, `:223-224`)과 비교 대상의 생산자
(`l0_probe.js:309-315`, `:334-337`)가 **서로 다른 파일의 서로 다른 결함**이라는 사실이다.

- 갭 1 은 **값이 도달하지 않는 문제** — 고칠 자리는 `firewall.py:712-723` · `plan.py:44-51` · `executor.py:68-75`.
- 갭 2 는 **도달한 값을 해석할 술어가 없는 문제** — 고칠 자리는 `l1_engine.py:201-231` 과 `l0_probe.js:307-340`.

복구 순서에 대한 함의: **B1 은 B2 의 전제이지만 B1 단독 완료는 검증 가능한 결과를 내지
않는다.** B1 만 머지하고 재수집하면 결과가 현행과 완전히 동일해서 "고쳤는데 왜 그대로냐"
가 되고, 그 시점의 재수집은 실사이트 접속 예산만 소모한다. **B1 과 B2 는 한 게이트에서
함께 검증되어야 하며, 중간 재수집을 넣지 않는 것이 옳다.**

---

## 7. Claude C 의 원인 4층위 — 코드·실측 검증

Coordinator 전달값과 이 감사의 독립 재집계 대조:

| 층위 | C 보고 | 이 감사 재집계 | 판정 |
|---|---|---|---|
| C-G 가드 입도 (Scout 이전 차단) | 25건 | `ACCOUNT_ACTION_BLOCKED` **25** (LOGIN 19 / PURCHASE 3 / SIGNUP 2 / PAYMENT 1) | **확인됨** |
| C-W task wiring | 59건 전건 | `batch.py:258` 이 `task=` 를 넘기지 않으므로 59건 전부 `default_task_definition` 경유. 코드상 예외 경로 없음 | **확인됨** |
| C-D signal detector | Scout 돈 31건 전건 | `detail.scout_invoked is True` **31**; MART `fact_task_entry.json` n=**31**, NED/IED/MPFED null **31/31** | **확인됨** |
| C-E endpoint 계약 | gate 12건 (11+1) | gate 로 종료한 관측은 **13건**(UNDETERMINED 8 + RESOLVED 5). outcome 어휘로는 `AUTH_GATE` 12(= `AUTH_GATE_REACHED` 11 + `PAYMENT_GATE_REACHED` 1) + `CAPTCHA` 1 | **부분 확인 — 아래 참조** |

### 7.1 C-E 의 규모 정정 (F-7)

"12건(11+1)" 이라는 **산술은 맞다** — `outcomes.map_engine_result` (`outcomes.py:153-154`)
가 `AUTH_GATE_REACHED`/`PAYMENT_GATE_REACHED`/`PERSONAL_DATA_REQUIRED` 를 하나의
`AUTH_GATE` outcome 으로 접기 때문이다. 다만 이 12 를 "endpoint 계약을 고치면 회수되는
표본" 으로 읽으면 **과대평가**다.

gate 가 endpoint 로 승격될 수 있는 archetype 은 `depth.py:35-45` `ENDPOINT_GATE_KINDS` 가
정한 **2개뿐**이다:

```python
FINANCIAL_ACTION_ENTRY: {LOGIN, IDENTITY_VERIFICATION}
COMMUNICATION_ENTRY:    {LOGIN}
나머지 5 archetype:      frozenset()   # 공집합
```

실측에서 gate 로 종료한 13건의 archetype 분포 (`detail.notes` 의 `gate 판별:` 항목 재집계):

| archetype | UNDETERMINED | RESOLVED | 승격 가능 archetype 인가 |
|---|---|---|---|
| ITEM_DETAIL | 5 | IDENTITY_VERIFICATION 1 · PAYMENT 1 | 아니오 (공집합) |
| PLACE_LOOKUP | 1 | IDENTITY_VERIFICATION 1 | 아니오 |
| CONTENT_OPEN | 0 | LOGIN 1 · CAPTCHA 1 | 아니오 |
| UTILITY_ENTRY | 1 | 0 | 아니오 |
| **FINANCIAL_ACTION_ENTRY** | **1** | 0 | **예** |
| COMMUNICATION_ENTRY | 0 | 0 | 예 (해당 관측 없음) |

→ **13건 중 gate 승격 계약이 걸리는 것은 FINANCIAL_ACTION_ENTRY 1건뿐이고, 그 1건은
gate 종류 판별이 `UNDETERMINED` 여서 `depth.py:284-290` 에 따라 `AUTH_GATE_REACHED` 로
떨어졌다.** 나머지 12건은 gate 판별을 아무리 개선해도 `ENDPOINT_GATE_KINDS` 가 공집합이라
endpoint 가 될 수 없다 — 그것은 결함이 아니라 `00 §3` 이 정한 설계다(`depth.py:32-34`,
규칙 E-6 확대 금지).

**따라서 C-E 층위의 회수 가능 규모는 현행 59건 표본에서 최대 1건이다.**
C-G(25건)·C-W(59건)·C-D(31건)와 **자릿수가 다르다.** 복구 우선순위에서 C-E 를
C-G/C-W/C-D 와 동급으로 두면 자원 배분이 왜곡된다.

### 7.2 4층위는 분할(partition)이 아니라 중첩이다

- C-W(59)는 C-G(25)와 C-D(31)를 **포함**한다 — 59건 전부가 잘못된 task 로 출발했고,
  그중 25건은 detector 에 도달하기 전에 가드로 잘렸고 31건이 detector 까지 갔다.
  (59 = 25 blocked + 31 scout + 3 retry-exhausted.)
- 따라서 25 + 59 + 31 + 12 를 더하는 해석은 성립하지 않는다. 각 층은 "이 결함이 없었다면
  그 단계를 통과했을 관측 수" 이며 서로 겹친다.
- **이 감사의 6종 outcome 귀속표(§3.1)는 상호배타적 분할이고, C 의 4층위는 중첩된 원인
  층위다.** 둘은 서로 다른 축이며 어느 쪽도 틀리지 않았다 — Coordinator 의 판단에 동의한다.
  단, 보고서에 함께 실을 때는 **합계가 다르다는 것을 명시**해야 오독을 막는다.

---

## 8. 이 감사가 확인하지 않은 것 (범위 밖 명시)

- `REAL_TARGET` 실행을 하지 않았다. 실사이트 접속 0건.
- E001 59/59 결과물과 frozen MART 를 수정하지 않았다. 읽기 전용 재집계만 했다
  (`fact_task_entry.json`, `REAL_RUN_SUMMARY.json`, `batches/*.json`, `evidence/*/l0a/probe.json`).
- `research/refcohort/**` 및 Claude A 소유 브랜치를 열거나 쓰지 않았다.
- L0 축(KWCAG 접근성·interrupt)은 이 감사 범위가 아니다 — 여기서 다룬 것은 L1 depth 축뿐이다.
- P-A endpoint codebook 자체의 존재 여부·내용은 확인하지 않았다 (Claude A 소관).

## 9. 근거 파일 목록

| 파일 | 용도 |
|---|---|
| `R/shadow/lane_b/state/representative_task_candidate_shadow.csv` | S1 필드 실재·분포 |
| `R/shadow/e001_plan/E001_MASTER_PLAN.json` | 동결 59건, mapping_status 상류 소비 |
| `R/src/landing_accessibility/engine/firewall.py:542-730` | S2·S3 |
| `R/scripts/run_e001_real.py:64-77` | S4 |
| `R/src/landing_accessibility/e001_runner/plan.py:35-69` | S5 |
| `R/src/landing_accessibility/e001_runner/real_executor.py:61-155` | S6 |
| `R/src/landing_accessibility/e001_runner/executor.py:57-132` | S7 |
| `R/src/landing_accessibility/e001_runner/batch.py:237-260` | task= 미전달 확인 |
| `R/src/landing_accessibility/e001_runner/guard.py:130-182` | 가드 입도 |
| `R/src/landing_accessibility/engine/l1_engine.py:83-105, 201-231, 427-680` | S8·S9·S10·Scout |
| `R/src/landing_accessibility/engine/l0_probe.js:307-340` | 신호 생산자 (F-1) |
| `R/src/landing_accessibility/engine/depth.py:141-227` | S11·§4 |
| `.agent_worktrees/claude_b_analysis_current/artifacts/e001_real_marts/` | frozen MART 재집계 |
| `.agent_worktrees/claude_b_e001_worker_0*/artifacts/*/batches/`, `…/evidence/*/l0a/probe.json` | 실측 재집계 |
