# DEPTH_DATAFLOW_222ef2c — 코드 판독 (Claude C recovery audit 보조)

대상 커밋: `222ef2c28ed5971b3c9f8b07120b7627d2617476` (origin/claude-b/e000-real). 모든 인용은 `git show 222ef2c:<path>` 로 읽은 원문 기준. 경로 prefix `research/landing_accessibility/` (아래 `src/…` = `src/landing_accessibility/…`). 해석·권고 없음. 추측은 "추측" 으로 표기.

## §1 데이터플로 표

| 단계 | 원천 | 읽는 것 | 떨어지는 것 |
|---|---|---|---|
| CSV `representative_task_candidate_shadow.csv` (헤더 27열) | — | `canonical_service_key`, `web_target_id`, `interaction_archetype`, `endpoint_definition`, `task_id` (firewall.py:698-722) | **`region_definition`, `region_signal_type`, `endpoint_signal_type`, `mapping_status`, `mapping_basis`, `primary_function_name`** 등 나머지 22열 — `E001TargetRow` 에 필드 자체가 없다 (firewall.py:543-554) |
| CSV `web_eligibility_shadow.csv` | — | `canonical_service_key`, `web_eligibility_status`(검사만), `web_target_url`, `web_target_group_id`(fallback), `service_name_canonical` (firewall.py:692-720) | 나머지 열 |
| `E001TargetRow` (firewall.py:543-554) | 위 조인 | `canonical_service_key, target_id, official_url, interaction_archetype, worker_id, order_index, service_name_canonical, endpoint_definition, task_id` | — |
| `TargetSpec` (plan.py:36-51) ← `_worker_plan` (run_e001_real.py:64-77) | E001TargetRow | `target_id, canonical_service_key, official_url, interaction_archetype, endpoint_definition, service_name_canonical` | **`task_id`, `worker_id`, `order_index`** (TargetSpec 에 필드 없음 / 전달 안 함). `e000_id`, `fixture_override` 는 None |
| `TaskDefinition` (l1_engine.py:84-98) ← `default_task_definition` (executor.py:57-75) | TargetSpec | **`interaction_archetype` 과 `target_id` 만** 읽는다 (executor.py:67,69) | **`TargetSpec.endpoint_definition` 은 읽지 않는다** — `endpoint_definition=None` 상수 (executor.py:72). `region_definition=None` 상수 (:71). `region_signal_type`/`endpoint_signal_type` = `CODEBOOK_PENDING` 상수 (:73-74). `service_name_canonical` 미사용 |
| detector 입력 (l1_engine.py:201-231) | `raw`(probe `raw_features`) + `task` | `task.archetype`, `task.region_definition`, `task.endpoint_definition`, `raw.region_signals.*`, `raw.endpoint_signals.*` | **`task.region_signal_type` / `task.endpoint_signal_type` 은 어느 detector 도 읽지 않는다** (grep: l1_engine.py 내 참조는 :96-97 정의와 :103-104 `mapping_frozen_allowed` 뿐; `mapping_frozen_allowed` 호출자는 src/scripts 에 없다) |

CSV 실측(같은 커밋의 `shadow/lane_b/state/representative_task_candidate_shadow.csv`, 71행): `endpoint_definition` 71/71 non-empty(자연어 문장, 예 "상품 상세와 핵심 상품정보가 보인 순간" 34건), `region_definition` 71/71 non-empty, `region_signal_type` = DOM_AX_ROLE 63 / CODEBOOK_PENDING 8, `endpoint_signal_type` = URL_PATTERN 42 / DOM_AX_ROLE 20 / FORM_STRUCTURE 9, `mapping_status` = CANDIDATE 59 / AMBIGUOUS_UNRESOLVED 12, `task_id` 0/71 non-empty. `E001_MASTER_PLAN.json` `frozen_collection_order` = 59, 워커 15/15/15/14.

## §2 항목별 핵심 인용

**1. `load_e001_full_targets` / `E001TargetRow`** — `src/engine/firewall.py`
- 543-554: dataclass 필드 = `canonical_service_key, target_id, official_url, interaction_archetype, worker_id, order_index, service_name_canonical=None, endpoint_definition=None, task_id=None`.
- 567-586 `_read_key_indexed_csv`: `csv.DictReader` 전체 행을 `canonical_service_key` 로 색인 (행 dict 통째 보관, 중복 키면 예외).
- 692-696: `web_eligibility_status != "ELIGIBLE_WEB"` 이면 예외 (`E001_ELIGIBLE_STATUS`, :204).
- 697-701: `url = elig["web_target_url"]`, `target_id = task["web_target_id"] or elig["web_target_group_id"]`, `archetype = task["interaction_archetype"]`.
- 712-723: `E001TargetRow(..., service_name_canonical=elig.get("service_name_canonical"), endpoint_definition=(task.get("endpoint_definition") or "").strip() or None, task_id=(task.get("task_id") ...) or None)`.
- `region_definition` / `region_signal_type` / `endpoint_signal_type` / `mapping_status` 는 이 함수 어디에서도 `.get` 되지 않는다 (grep 결과: firewall.py 에 해당 문자열 없음). **읽지 않고 버린다.**

**2. `TargetSpec`** — `src/e001_runner/plan.py:36-51`
```
target_id, canonical_service_key, official_url, interaction_archetype,
e000_id=None, endpoint_definition=None, service_name_canonical=None, fixture_override=None
```
`endpoint_definition` 필드는 **있다**. `region_definition` / `*_signal_type` 필드는 **없다**.

**3. `_worker_plan`** — `scripts/run_e001_real.py:64-77`: `TargetSpec(target_id=row.target_id, canonical_service_key=…, official_url=…, interaction_archetype=…, endpoint_definition=row.endpoint_definition, service_name_canonical=…)` for row if `row.worker_id == worker_id`. 전달: 6개. 떨어짐: `task_id`, `worker_id`, `order_index`. `endpoint_definition` 은 **여기까지는 전달된다**.

**4. `run_l1_if_safe_real`** — `src/e001_runner/real_executor.py:110-155`
- 124: `l0 = run_l0_real(...)`; 125: `candidates = l0.get("primary_action_candidates") or []`; 127: `risk = screen_candidates(candidates)`; 128-136: risk 가 있으면 `{"outcome": ACCOUNT_ACTION_BLOCKED, "scout_invoked": False, ...}` 반환 (Scout 미생성).
- **138: `resolved_task = task or default_task_definition(target)`** — batch.py:258 이 `run_l1_if_safe_real(target, run=run, scope=scope)` 로 호출하므로 `task` 는 항상 `None` → 항상 `default_task_definition(target)`.
- 146-150: `scout.scout(web_target_id=target.target_id, entry_real_url=..., task=resolved_task)`.
- region/endpoint 정의의 출처는 오직 `default_task_definition` 이다. 이 파일은 `target.endpoint_definition` 을 읽지 않는다.

**5. `default_task_definition`** — `src/e001_runner/executor.py:57-75`
```
67  archetype = InteractionArchetype(target.interaction_archetype)
68  return TaskDefinition(
69      task_id=f"task-{target.target_id}",
70      archetype=archetype,
71      region_definition=None,
72      endpoint_definition=None,
73      region_signal_type=RegionSignalType.CODEBOOK_PENDING,
74      endpoint_signal_type=RegionSignalType.CODEBOOK_PENDING,
75  )
```
조건 없음 — **모든 target 에 무조건** `None`/`None`/`CODEBOOK_PENDING`/`CODEBOOK_PENDING`. docstring(:60-65) 원문: "P-A endpoint codebook이 동결하기 전에는 존재하지 않는다 … QUERY를 제외한 모든 archetype은 area/endpoint 신호가 결코 성립하지 않고, gate가 없으면 예산 소진으로 `UNRESOLVED`에 도달한다."

**6. `TaskDefinition`** — `src/engine/l1_engine.py:84-105`: `task_id: str; archetype: InteractionArchetype; region_definition: str|None; endpoint_definition: str|None; region_signal_type = DOM_AX_ROLE; endpoint_signal_type = DOM_AX_ROLE; query_text = "고령자 접근성"`. docstring(:87-89): "fixture 가 `data-region` / `data-endpoint` 로 선언한 토큰을 그 자리에 넣는다". `mapping_frozen_allowed()`(:100-105) 만 `*_signal_type` 을 읽음.

**7. `detect_area_signal(raw, task)`** — l1_engine.py:201-218
- 207: `signals = raw.get("region_signals", {})`.
- 208-212: `task.archetype is QUERY` → `search_inputs` 중 `visible and in_form and has_submit` 가 하나라도 있으면 True (region_definition 불필요).
- **213-214: `if task.region_definition is None: return False`**.
- 215-218: `declared_regions` 중 `s["region"] == task.region_definition and present and visible`.
- `region_signal_type` 분기 **없음**. `CODEBOOK_PENDING` 값에 대한 분기 **없음** — 동작 차이는 `region_definition is None` 에서만 난다.
- probe 원천 (`src/engine/l0_probe.js:309-327`): `declared_regions = document.querySelectorAll('[data-region]')`, `region = el.getAttribute('data-region')`.

**8. `detect_endpoint_signal(raw, task)`** — l1_engine.py:221-231
- **223-224: `if task.endpoint_definition is None: return False`**.
- 226-227: `signals["body_endpoint_reached"] == task.endpoint_definition` → True.
- 228-231: `declared_endpoints` 중 `e["endpoint"] == task.endpoint_definition and visible`.
- QUERY 특례 없음. `endpoint_signal_type` 분기 없음.
- probe 원천 (l0_probe.js:333-337): `declared_endpoints = querySelectorAll('[data-endpoint]')` 의 `data-endpoint` 속성값, `body_endpoint_reached = document.body.getAttribute('data-endpoint-reached')`.

**9. `compute_depth`** — `src/engine/depth.py:141-203`
- 158: `assert_detail_rollup`; 159: `reached = endpoint_status is FUNCTION_ENDPOINT_REACHED`.
- 161-165: reached 인데 `endpoint_step_index is None` → `DepthRuleError`.
- **166-186: `not reached` → `area_step_index is None` 이면 `(None, None, None, NOT_OBSERVED, status, detail, 0)`; 아니면 `(area_step_index, None, None, OBSERVED, status, detail, 0)`** — 즉 endpoint 미도달이면 IED/MPFED 는 항상 None.
- 188-199: reached, `m = endpoint_step_index`; `area_step_index is None or > m` → `(m, 0, m, INFERRED_FROM_ENDPOINT, …, 1)`.
- 200-203: `(k, m-k, m, OBSERVED, …, 1)`.
- gate 처리는 이 함수가 아니라 `gate_outcome`(:48-74)/`gate_outcome_from_decision`(:268-290)이 endpoint_status 를 정한다: PAYMENT→PAYMENT_GATE_REACHED, CAPTCHA→CAPTCHA, PERSONAL_DATA→PERSONAL_DATA_REQUIRED, `gate_kind in ENDPOINT_GATE_KINDS[archetype]`(E-5) → `FUNCTION_ENDPOINT_REACHED + ENDPOINT_VIA_AUTH_GATE`, 그 외 → `AUTH_GATE_REACHED`. `ENDPOINT_GATE_KINDS`(:35-45): FINANCIAL_ACTION_ENTRY={LOGIN, IDENTITY_VERIFICATION}, COMMUNICATION_ENTRY={LOGIN}, 나머지 5 archetype = 공집합. `decision.resolved` 가 아니면 archetype 무관 `AUTH_GATE_REACHED`(:284-290). 코드 주석의 규칙명은 E-5/E-6/E-6a 이며 문자열 "E-6b" 는 src/scripts 에 없다.

**10. Scout 루프** — l1_engine.py:372-680
- 317-331 `_observe`: 매 state 관측마다 `area=detect_area_signal(raw, task)`, `endpoint=detect_endpoint_signal(raw, task)`, `gate=detect_gate(raw)`, `gate_present=gate_observed(raw)`.
- 464-475: 각 prefix 마다 `page.goto(entry_url)` → 랜딩 관측 → `landing_area/landing_endpoint/landing_gate`.
- 477-526: prefix 의 action 을 순서대로 `_activate` → 관측 → `TaskStep(area_signal_detected=int(obs.area), endpoint_signal_detected=int(obs.endpoint), auth_gate_detected=int(obs.gate_present))`; `obs.endpoint or obs.gate_present` 면 break.
- 532-536: `area_here = _first_index(landing_area, steps, "area_signal_detected")`, `endpoint_here = _first_index(landing_endpoint, …)`, `gate_here`.
- **538-543: `endpoint_here is not None` → terminal=(FUNCTION_ENDPOINT_REACHED, None), `endpoint_index=endpoint_here`**.
- **544-566: `gate_here is not None` → `gate_outcome_from_decision(task.archetype, gate_here, personal_data_required=…)`; `endpoint_index = len(steps) if status is FUNCTION_ENDPOINT_REACHED else None`**.
- 569-575: 미종료면 `_activation_candidates(obs.raw, branching_limit)` 로 확장; `len(prefix) >= max_activations_per_task(8)` 면 `budget_reason="MAX_ACTIVATIONS_PER_TASK"`. 450-456 wall-clock(180s)/`MAX_ACTIVATIONS_PER_TASK`, 484-493 `MAX_STATE_REVISITS`/`MAX_CONSECUTIVE_NO_STATE_CHANGE`, 593-595 예외 → `SCOUT_ERROR`.
- **600-608: `terminal is None` → `status=UNRESOLVED`, `detail = UNRESOLVED_DEPTH_BUDGET_EXCEEDED if budget_reason else UNRESOLVED_NO_SIGNAL`**.
- 610-616: `compute_depth(archetype, area_index, endpoint_index, status, detail)` → 641-643 `ned/ied/mpfed`. 663: manifest 는 `depth.endpoint_reached` 일 때만.

**11. 계정행동 가드** — `src/e001_runner/guard.py`
- 시점: `run_l1_if_safe_real` 에서 L0 수집 **직후, Scout 생성 전** (real_executor.py:124-136).
- 입력: `l0["primary_action_candidates"]` — L0 가 랭킹한 **전체 후보**(SELECTED/RUNNER_UP/REJECTED 모두, l0_collector.py:335-370; probe 는 visible 후보 최대 200개, l0_probe.js:279).
- `classify_candidate`(:130-157): `input_type`/`autocomplete`/`name` 검사 후, `accessible_name + visible_text + aria_label` 텍스트에 `_FORBIDDEN_TEXT_PATTERNS`(:56-103; OTP/PAYMENT/PURCHASE/BOOKING/MESSAGE_SEND/SIGNUP/CAPTCHA/LOGIN, LOGIN 패턴 = `로그인|log in|sign in`) 순차 매칭. `PrimaryActionCandidate` 에는 `input_type/autocomplete/name` 필드가 없다(l0_collector.py:186-208) → L0 후보에서는 텍스트 분기만 실질 작동.
- **`screen_candidates`(:170-182): 후보 하나라도 blocked 면 그 risk 반환 → 호출자는 target 전체의 Scout 를 건너뛴다. 후보 제외가 아니라 target 중단이다** (docstring :173-176 원문: "위험한 후보가 목록에 존재하기만 해도 이 target의 L1 activation 자체를 건너뛴다").
- batch.py:279-284: 결과 outcome 이 `ACCOUNT_ACTION_BLOCKED` 면 `AccountActionBlockedError` → 296-305 재시도 없이 `TargetResult(outcome=ACCOUNT_ACTION_BLOCKED, detail=last_result)`.

## §3 MPFED 가 NULL 이 되는 코드 경로

**(a) 가드가 Scout 전에 target 중단** — real_executor.py:127-136. `screen_candidates` 가 non-None 이면 반환 dict 에 `ned/ied/mpfed` 키 자체가 없다(`TaskEntry` 미생성). `Scout` 인스턴스가 만들어지지 않으므로 `compute_depth` 도 호출되지 않는다. 트리거는 L0 전체 후보 중 텍스트 패턴(예 "로그인", "회원가입", "보내기") 1건 존재. 코드 근거 확정.

**(b) TaskDefinition 에 정의 없음 / CODEBOOK_PENDING** — executor.py:71-74 가 조건 없이 `region_definition=None, endpoint_definition=None` 을 넣고, real_executor.py:138 이 항상 이것을 쓴다(batch.py:258 은 `task` 를 넘기지 않음). 그 결과 l1_engine.py:223-224 에서 `detect_endpoint_signal` 은 **모든 state 에서 False** 를 반환 → `landing_endpoint=False`, 모든 `TaskStep.endpoint_signal_detected=0` → `endpoint_here=None` (:533-535) → :538 분기 진입 불가. `CODEBOOK_PENDING` 값 자체는 어떤 detector 도 읽지 않으므로(§1 표) 그 값이 직접 NULL 을 만드는 것은 아니고, 같은 함수가 함께 넣는 `None` 이 원인이다. 코드 근거 확정. 비-QUERY archetype 은 `region_definition=None` 으로 :213-214 에서 area 도 항상 False → `area_index=None` → NED 도 NULL. QUERY 는 :208-212 로 area 만 성립 가능.

**(c) detector 가 실제 신호를 볼 수 없음** — 가정적으로 `endpoint_definition` 이 non-None 으로 도달했더라도, `detect_endpoint_signal` 이 비교하는 raw 값은 `document.body.getAttribute('data-endpoint-reached')` 와 `[data-endpoint]` 요소의 속성값(l0_probe.js:334-337) 뿐이다. `detect_area_signal` 의 비교 대상도 `[data-region]` 속성값(l0_probe.js:309-315) 뿐이다(QUERY 의 `search_inputs` 제외). CSV 의 `endpoint_definition` 은 자연어 문장("상품 상세와 핵심 상품정보가 보인 순간" 등)이며 `endpoint_signal_type` 에 URL_PATTERN/FORM_STRUCTURE/DOM_AX_ROLE 이 적혀 있으나, URL·form·role 기반 endpoint 판정 코드는 l1_engine.py 에 존재하지 않는다(:221-231 이 전부). 실제 서비스 DOM 에 `data-endpoint-reached`/`data-endpoint`/`data-region` 속성이 있는지는 코드로 알 수 없다 — **그 속성이 없다는 것은 추측**(단, TaskDefinition docstring :88-89 과 detect_gate docstring :253-254 는 이 속성을 "fixture 가 선언한 토큰"으로 기술한다). 따라서 (b) 가 제거되어도 (c) 로 endpoint 신호는 `data-*` 속성 일치가 아닌 한 성립하지 않는다 — 이 부분은 코드 근거 확정, "실제 서비스에 그 속성이 없다" 는 추측.

**(d) endpoint 계약(gate 규칙 E-5/E-6a)** — (a)(b) 를 통과한 Scout 에서 `terminal` 이 정해지는 경로는 :538(endpoint 신호, (b)(c) 로 봉쇄)과 :544(gate) 뿐이다. gate 경로에서 MPFED 가 non-NULL 이 되려면 `gate_outcome_from_decision` 이 `FUNCTION_ENDPOINT_REACHED` 를 돌려줘야 하고(:559-563), 그것은 depth.py:66-71 에 의해 `decision.resolved` 이면서 `gate_kind ∈ ENDPOINT_GATE_KINDS[archetype]` 일 때만이다 — 즉 FINANCIAL_ACTION_ENTRY(LOGIN/IDENTITY_VERIFICATION) 또는 COMMUNICATION_ENTRY(LOGIN). QUERY/CONTENT_OPEN/ITEM_DETAIL/PLACE_LOOKUP/UTILITY_ENTRY 는 공집합(:40-44) → gate 가 관측돼도 `AUTH_GATE_REACHED`/`PAYMENT_GATE_REACHED`/`CAPTCHA`/`PERSONAL_DATA_REQUIRED` → `endpoint_index=None` → compute_depth :166-186 → MPFED NULL. 판별 미확정(`UNDETERMINED`)도 archetype 무관 `AUTH_GATE_REACHED`(:284-290) → NULL. gate 도 없고 endpoint 도 없으면 예산 소진/큐 고갈로 `terminal=None` → `UNRESOLVED` (:600-606) → NULL. 코드 근거 확정. 단, 가드 (a) 의 LOGIN 텍스트 패턴(guard.py:99-102)이 "로그인" 후보를 가진 target 을 Scout 전에 중단시키므로, gate 경로가 실제로 실행되려면 L0 후보 텍스트에 패턴이 없으면서 Scout 관측에서 `gate_classifier` 가 gate 를 확정해야 한다 — 그 교집합이 59 타깃에서 비어 있는지는 코드만으로 확정 불가(추측 영역).

## §4 사실 확인

**질문: 59 타깃 실행 시 Scout 에 전달되는 `region_definition` / `endpoint_definition` 이 non-null 일 수 있는 조건이 코드상 존재하는가?**

**아니오.** 근거:
1. 실행 경로는 `run_e001_real.main` → `BatchRunner.run(...)` → `_run_real` → `_real_executor` (batch.py:237-260) → `run_l1_if_safe_real(target, run=run, scope=scope)` (batch.py:258) 로 고정되며 `task=` 인자를 넘기지 않는다. `main()` 은 `target_executor` 를 지정하지 않는다 (run_e001_real.py:147-154).
2. real_executor.py:138 `resolved_task = task or default_task_definition(target)` → `task is None` 이므로 항상 `default_task_definition`.
3. executor.py:71-72 는 인자와 무관한 상수 `None, None` 을 넣는다. `target.endpoint_definition` 을 읽는 코드는 src/scripts 전체에서 run_e001_real.py:72 (TargetSpec 생성) 한 곳뿐이며, 그 값을 소비하는 곳은 없다 (grep `\.endpoint_definition`: run_e001_real.py:72, l1_engine.py:223,226,229 — 후자 3건은 `task.` 즉 TaskDefinition 의 필드).
4. `region_definition` 은 CSV → E001TargetRow 단계에서 이미 읽히지 않는다 (firewall.py:712-723 에 없음, TargetSpec 에 필드 없음).

따라서 이 커밋에서 59 타깃 전건은 `TaskDefinition(region_definition=None, endpoint_definition=None, region_signal_type=CODEBOOK_PENDING, endpoint_signal_type=CODEBOOK_PENDING)` 으로 Scout 에 들어간다. 해당 상태에서 `detect_endpoint_signal` 은 :223-224 에 의해 상수 False 이며, MPFED 가 non-NULL 이 될 수 있는 유일한 코드 경로는 §3(d) 의 gate→E-5 경로(FINANCIAL_ACTION_ENTRY / COMMUNICATION_ENTRY 에서 resolved LOGIN 또는 IDENTITY_VERIFICATION gate)이다.
