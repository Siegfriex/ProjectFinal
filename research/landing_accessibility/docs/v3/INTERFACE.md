# `v3_runner` 호출 인터페이스 명세

작성: W5K (seam integration lane) · 브랜치 `claude-b/w5k-seam-integration`
대상: C 의 GATE 1 하네스가 **runner 의존 항목을 검사하기 위해** 필요한 호출 형태와 출력 형태.
전달 경로: **W5K → B → (A 승인) → C.** W5K 는 C 와 직접 통신하지 않는다.

**측정 트리**: W5A·W5B·W5C·W5D·W5D1·W5E·W5F·W5G·W5J 가 병합된 상태.
**W5H(session-driver)·W5I(ax-join) 는 병합돼 있지 않다** — 이 문서의 모든 판정은
그 두 lane 이 **없는** 트리의 실측이다. 두 lane 이 올라오면 §2·§7·§8 을 다시 재야 한다.

## 이 문서가 담지 않는 것

**기대값·임계값·판정 결과를 쓰지 않는다.** "이 fixture 에서 이 값이 나온다" 는 없다.
C 가 자기 fixture 로 독립 판정해야 하고, B 의 기대값이 새면 `Δ10-R14` 가 막으려는
공유 독해가 그대로 생긴다. 아래 표에 나오는 값은 전부 **어휘의 정의역**(닫힌 집합의
원소 목록)이거나 **키 이름**이지, 어떤 입력에 대한 산출값이 아니다.

## 표기 — 읽어서 아는 것과 돌려봐서 아는 것을 구분한다

| 표기 | 뜻 |
|---|---|
| **[실행]** | 실제로 `V3Runner.run()` 을 돌려 관측했다. 산출 파일·키를 눈으로 본 값이다 |
| **[내성]** | `inspect.signature` / `dataclasses.fields` / enum 열거로 런타임에서 읽었다 |
| **[독해]** | 소스를 읽어서 안다. 실행으로 확인하지 않았다 — 그대로 믿지 말고 확인해라 |

---

## 1. 진입점 — [내성]

모듈: `landing_accessibility.v3_runner.runner`

### `V3Runner`

```python
V3Runner(
    *,
    evidence_root: Path,
    contract_hasher: ContractHasher,          # 필수. None 이면 MissingDependencyError
    safety: SafetyGuard,                      # 필수. None 이면 MissingDependencyError
    eligibility: EligibilityChecker | None = None,
    binder: CandidateBinder | None = None,
    scout: ScoutStrategy | None = None,
    surface_measurer: SurfaceMeasurer | None = None,
    flow_normalizer: FlowNormalizer | None = None,
    obstruction: ObstructionAnalyzer | None = None,
    terminal: TerminalClassifier | None = None,
    depth_attributor: DepthAttributor | None = None,
    budget: ScoutBudget | None = None,        # 기본 ScoutBudget(max_activations=8)
) -> None
```

```python
V3Runner.run(
    contract: TaskContract, *, driver: SessionDriver, run_id: str,
    service_id: str | None = None, task_id: str | None = None,
) -> V3RunResult

V3Runner.replay(
    contract: TaskContract, *, driver: SessionDriver,
    manifest: Mapping[str, Any], declared_sha256: str | None, run_id: str,
    service_id: str | None = None, task_id: str | None = None,
) -> V3RunResult

V3Runner.verify_contract_hashes(contract: TaskContract) -> None
```

### 모듈 수준 함수

```python
build_path_manifest(*, key: ObservationKey, contract: TaskContract,
                    steps: Sequence[FlowStep]) -> dict[str, Any]
path_manifest_sha256(manifest: Mapping[str, Any]) -> str
verify_path_manifest_hash(manifest: Mapping[str, Any],
                          declared_sha256: str | None) -> str
build_family_aggregate(*, family_id: str, metric: str,
                       records: Sequence[Mapping[str, Any]],
                       filter_expr: str = "task_role == 'PRIMARY'") -> dict[str, Any]
denominator_for_metric(metric: str) -> str        # evidence.py 에서 재수출
```

### 호출자가 반드시 알아야 할 사전조건 — [실행]

1. **`task_id` / `service_id` 를 명시로 넘겨라.** 생략하면 각각
   `contract.frozen_task` · `contract.target_id` 로 채워진다. `frozen_task` 는
   표시명이라 공백을 갖는 경우가 있고, `evidence._validate_token` 이 그런 값을
   `EvidenceIdentityError` 로 거부한다(`02 §8` id 위생). 실측에서 실제로 걸렸다.
2. **계약 해시는 순서가 있다.** `endpoint_contract_hash` 가
   `task_contract_hash` payload 에 포함되므로, 계약을 합성할 때 endpoint 해시를
   먼저 채우고 그 다음 `registry.recompute_task_contract_hash()` 를 호출해야 한다.
   반대로 하면 `ContractHashMismatchError` 다.
3. `run()` 은 해시 검증 → eligibility → 세션 순이다. **해시가 틀리면 evidence
   디렉터리 자체가 만들어지지 않는다**(브라우저를 열기 전에 거부).

### 예외 — [독해]

`RunnerError` 하위: `ContractHashMismatchError` · `PathManifestHashMismatchError` ·
`ProhibitedActionError` · `MissingDependencyError`.
**safety 계층의 차단은 이 계통이 아니라 `safety.SafetyStop`** 으로 나온다
(`AccountActionBlockedError` 하위). runner 는 둘 다 잡지 않는다 — 전부 호출자까지
올라온다(fail-closed). 두 계통이 섞여 있는 것은 측정된 현재 상태이고 통일되지 않았다.

---

## 2. 필수 주입 경계 — Protocol 11종의 실제 구현 — [실행]

`isinstance(obj, Protocol)` 로 전수 판정했다. `runtime_checkable` Protocol 의
`isinstance` 는 **메서드 이름만** 보므로, 시그니처 일치는 따로 표기한다.

| Protocol | 요구 멤버 | 실제 구현 | 적합 |
|---|---|---|---|
| `SafetyGuard` | `assert_action_allowed(contract, action)` | `safety.ActivationSafetyGuard` | **O** |
| `ScoutStrategy` | `propose_next(contract, states, candidates, taken)` | `scout_strategy.MinPathScoutStrategy` | **O** |
| `ContractHasher` | `task_contract_hash` · `endpoint_contract_hash` | 없음. `registry.recompute_task_contract_hash(contract)` 는 **함수** | X |
| `EligibilityChecker` | `check(contract)` | **없음.** `discovery.py` 에 eligibility 관련 심볼 0개 | X |
| `CandidateBinder` | `bind(contract, states)` | 없음. `discovery.discover_task_candidates(probe_state, task_contract, policy)` 는 **함수**이고 인자도 다르다 | X |
| `SurfaceMeasurer` | `measure(contract, states)` | 없음. `surface.measure_surface(probe_state, task_control, viewport)` 는 **함수** | X |
| `FlowNormalizer` | `normalize(contract, steps)` | 없음. `flow.normalize_flow(steps)` 는 **함수**이고 `contract` 를 받지 않는다 | X |
| `ObstructionAnalyzer` | `analyze(contract, states, steps)` | 없음. `obstruction.measure_task_obstruction(interrupts, task_control_bbox, viewport)` 는 **함수**이고 인자가 전부 다르다 | X |
| `TerminalClassifier` | `classify(contract, steps)` | 없음. `terminal.classify_terminal(signals)` 는 **함수**이고 `TerminalSignals` 하나를 받는다 | X |
| `DepthAttributor` | `attribute_conditional_tokens(contract, records)` | **없음.** `flow.py` 가 `normalize_flow` 안에서 처리하므로 별도 객체가 없다 | X |
| `SessionDriver` | `capture_surface(contract)` · `activate(action)` | **없음.** W5H lane 미병합 | X |

### 이것이 하네스에 뜻하는 것

- **11 중 2 만 그대로 주입된다.** 나머지 9 는 어댑터가 필요하다.
- 어댑터가 필요한 8종(SessionDriver 제외)은 **판정 로직을 새로 쓸 필요가 없다** —
  전부 해당 모듈에 실물 함수가 있고, 시그니처만 맞춰 위임하면 된다.
  단 `EligibilityChecker` 와 `DepthAttributor` 는 **위임할 함수 자체가 없다.**
- `SessionDriver` 는 **구현이 존재하지 않는다.** 브라우저를 여는 유일한 경계라
  W5H 가 올라오기 전에는 어떤 실행 경로도 대역 없이는 성립하지 않는다.
- 주입하지 않은 경계는 예외가 아니라 **`None` 산출**이다. `V3Runner._to_mart` 가
  경계가 없으면 그 자리를 `None` 으로 두고 내부 대체 계산을 하지 않는다
  (`09 D3-05`). 즉 **어댑터를 안 붙이면 조용히 결측이 늘어난다.**

---

## 3. 출력 파일 — [실행]

`V3Runner.run()` 성공 시 `evidence_root` 아래에 실제로 생긴 트리다.

```
<evidence_root>/
  <observation_id>/                      # 32 hex (evidence.OBSERVATION_ID_HEX_LEN)
    manifest.jsonl                       # evidence.MANIFEST_FILENAME
    run.json                             # evidence.RUN_RECORD_FILENAME
    s000/                                # surface state. f"s{index:03d}"
      dom.html  ax.json  probe.json  url.json  control_facts.json
    step0000_before/                     # f"step{step_index:04d}_before"
      dom.html  ax.json  probe.json  url.json  control_facts.json
    step0000_after/                      # f"step{step_index:04d}_after"
      dom.html  ax.json  probe.json  url.json  control_facts.json
    observation/                         # evidence.OBSERVATION_SCOPE_NODE
      depth_conditional_tokens.json      # CONDITIONAL 토큰이 **있을 때만** 생성
```

`screenshot.png` 은 `EvidencePayload.screenshot` 이 `None` 이 아닐 때만 생긴다.

### 슬롯 → 파일명 (`evidence.SLOT_FILENAMES`)

| `EvidenceSlot` | 파일명 |
|---|---|
| `DOM` | `dom.html` |
| `AX` | `ax.json` |
| `SCREENSHOT` | `screenshot.png` |
| `PROBE` | `probe.json` |
| `URL` | `url.json` |
| `CONTROL_FACTS` | `control_facts.json` |
| `DEPTH_ATTRIBUTION` | `depth_conditional_tokens.json` |

### `manifest.jsonl` — 한 줄 = 파일 한 개

키: `observation_id` · `node_id` · `slot` · `relpath` · `sha256` · `bytes`

### `run.json`

키: `observation_id` · `service_id` · `task_id` · `run_id` · `protocol_version`
(`evidence.V3_EVIDENCE_PROTOCOL_VERSION`) · `entry_count` ·
`evidence_manifest_sha256` · `path_manifest_sha256`

### path manifest — **디스크에 쓰이지 않는다**

`V3Runner.run()` 이 만든 path manifest 는 **파일로 남지 않는다.** `run.json` 에
`path_manifest_sha256` 만 들어가고, 본문은 `V3RunResult.path_manifest`(메모리)로만
나온다. 실행 후 디렉터리 전체를 훑어 `path` 이름을 가진 파일이 0개임을 확인했다.
하네스가 manifest 본문이 필요하면 **반환값에서 가져와야 한다.**

최상위 키: `path_manifest_version` · `observation_id` · `service_id` · `task_id` ·
`run_id` · `task_role` · `task_contract_hash` · `endpoint_contract_hash` · `steps`

`steps[]` 원소 키: `step_index` · `action_token` · `control_selector` ·
`control_role` · `control_visible_text` · `control_accessible_name` ·
`state_before_id` · `state_after_id` · `url_before` · `url_after`

### retention manifest — **runner 가 만들지 않는다**

`evidence.build_retention_manifest` / `verify_retention_manifest` 가 존재하지만
**`V3Runner` 의 어떤 경로도 호출하지 않는다.** 실행 후 트리에 retention 산출물이
없음을 확인했다. 별도 호출이 필요하다 — [내성]:

```python
build_retention_manifest(*, manifest_id: str, producer: str, producer_sha: str,
                         roots: Sequence[Path], base: Path,
                         read_only: bool = True) -> dict[str, Any]
verify_retention_manifest(manifest: Mapping[str, Any], *, base: Path) -> dict[str, Any]
```

---

## 4. 출력 필드명

### `V3RunResult` dataclass 필드 — [내성]

`observation_id` · `service_id` · `task_id` · `run_id` · `phase_reached` ·
`refusal` · `eligibility` · `raw_states` · `raw_steps` · `replay_status` ·
`replay_failure_reason` · `endpoint_status` · `derived_surface` · `derived_flow` ·
`derived_obstruction` · `path_manifest` · `path_manifest_sha256` ·
`evidence_manifest_sha256` · `evidence_run_dir` · `scout_budget_exhausted` ·
`task_role` · `depth_conditional_tokens`

### `V3RunResult.as_mart_record()` 최상위 키 — [실행]

```
action_sequence_raw   comparison_scope        depth_conditional_tokens
eligibility           endpoint_status         evidence_manifest_sha256
observation_id        path_manifest_sha256    phase_reached
replay_failure_reason replay_status           run_id
scout_budget_exhausted service_id             task_id
task_role
```

**주의 — mart record 는 derived 값을 담지 않는다.** `derived_surface` ·
`derived_flow` · `derived_obstruction` · `raw_states` · `raw_steps` ·
`path_manifest` · `evidence_run_dir` · `refusal` 은 `as_mart_record()` 출력에
**없다.** `V3RunResult` 객체에서 직접 읽어야 한다.

### `build_family_aggregate()` 최상위 키 — [실행]

`family_id` · `metric` · `applied_filter` · `denominator_name` · `denominator_n` ·
`input_row_count` · `comparison_scope` · `cross_family_use` · `preregistered_note` ·
`excluded_row_count` · `excluded_observation_ids` · `included_observation_ids`

`denominator_name` 의 정의역: `evidence_bearing_n` | `flow_evaluable_n`
(`evidence.DENOMINATOR_EVIDENCE_BEARING` / `DENOMINATOR_FLOW_EVALUABLE`).
어느 쪽이 붙는지는 `denominator_for_metric(metric)` 이 정하고, 그 분기는
`evidence.ENDPOINT_DEPENDENT_METRICS` (6종) 와 `ENTRY_FLOW_METRICS` (16종) 로 갈린다.

### `evidence.build_denominator_chain()` — [실행]

```python
build_denominator_chain(*, family_id: str, candidate_target_ids: Sequence[str],
                        ledger: ReplacementLedger, frozen_target_ids: Sequence[str],
                        attempted_target_ids: Sequence[str],
                        evidence_bearing_target_ids: Sequence[str],
                        flow_evaluable_target_ids: Sequence[str],
                        task_role_filter: str = "task_role == 'PRIMARY'") -> dict[str, Any]
```

최상위 키: `family_id` · `applied_filter` · `replacement_ledger` ·
`replacement_ledger_sha256` · `chain` · `denominator_assignment`

`chain[]` 원소 키: `stage` · `n` (+ `target_ids` 또는 `detail`).
`stage` 값의 정의역: `candidate` · `replaced` · `eligible_frozen` · `attempted` ·
`evidence_bearing` · `flow_evaluable`.

`registry.FamilyDenominatorChain` 은 **다른 자료형**이다 — 필드는 `family_id` ·
`candidate_count` · `replaced_count` · `replaced_reasons` · `frozen_count` ·
`reserve_count` · `reserve_remaining`. 이름이 비슷하니 섞지 마라.

---

## 5. 결측 표현 (GAP-04 적용 결과)

### `None` 인 것 — [실행 / 내성]

| 필드 | `None` 의 뜻 |
|---|---|
| `endpoint_status` | `TerminalClassifier` 미주입 또는 `REPLAY_BROKEN`. **`ABSTAIN` 과 다르다** |
| `derived_surface` · `derived_flow` · `derived_obstruction` | 그 경계가 주입되지 않았다 |
| `replay_failure_reason` | 실패하지 않았다 |
| `refusal` | 거부되지 않았다 |
| `evidence_manifest_sha256` · `evidence_run_dir` | 세션 이전 단계에서 끝났다 |
| `FlowStep.input_mode` | 입력수단 미관측 |
| `FlowNormalization.activation_depth` · `flow_step_count` · `menu_dependency` · `nav_container_depth` · `forced_dismissal_count` | 산출 불능. **0/False 로 접지 않는다** |
| `DepthConditionalRecord.included_in_activation_depth` | 판정 불능 |
| `TaskContract.fixture_input_mode` · `stratum` · `collection_order` · `fixture_override` · `legacy_archetype` | 미관측 / 해당 없음 |

### 문자열 sentinel 인 것 — [내성]

| 값 | 어디 | 뜻 |
|---|---|---|
| `UNDETERMINED` | `FlowNormalization.auth_gate_stage` | **`None` 이 아니다.** enum 에 값이 있어 판정 불능도 값으로 표현한다(Δ10). **집계 분모에서 빼지 마라 — 별도 범주다** |
| `UNDETERMINED` | `obstruction.ObstructionStatus` · `terminal.TerminalResolution` | 같은 취지 |
| `NONE` | `auth_gate_stage` | **관측했고 auth gate 가 없었다** — 적극적 주장이다. `UNDETERMINED` 와 절대 섞지 마라 |
| `ABSTAIN` | `endpoint_status` | 관측했고 terminal 조건이 안 잡혔다. `None`(미주입)과 다른 사실이다 |
| `NOT_OBSERVED` | 이 lane 의 실행 경로에서 **관측되지 않았다** | `engine.vocabulary.NAME_ABSENT` 등 인접 어휘와 혼동하지 마라 |

**같은 출력에서 `None` 과 `UNDETERMINED` 가 공존한다.** 어느 쪽인지가 사실을
가르므로 하네스가 둘을 하나로 접으면 안 된다.

### 닫힌 어휘의 정의역 — [내성]

```
runner.ENDPOINT_STATUS_VALUES  REACHED AUTH_GATE PUBLIC_WEB_UNOBSERVABLE
                               APP_REQUIRED EVIDENCE_DEFECT BLOCKED ABSTAIN
runner.ELIGIBILITY_VALUES      ELIGIBLE_PUBLIC_MOBILE_WEB APP_REQUIRED_EXCLUDE
                               ACCESS_BLOCKED_REVIEW URL_REMAP_REQUIRED
runner.Phase                   FROZEN_TASK_REGISTRY … FLOW_MART
runner.ReplayStatus            NOT_ATTEMPTED REPLAYED REPLAY_BROKEN
contracts.TASK_ROLES           PRIMARY SECONDARY_REPEATED
flow.AUTH_STAGE_VALUES         NONE UNDETERMINED BEFORE_TASK_DISCOVERY
                               AFTER_TASK_SELECT AT_ENDPOINT
```

---

## 6. 하네스가 걸려 넘어질 수 있는 실측 사실

세 건 다 **결함이라고 단정하지 않는다.** 관측한 그대로 적는다.

### 6.1 `input_mode` 어휘가 두 lane 사이에서 갈린다 — [실행]

`contracts.FIXTURE_INPUT_MODES` (W5A) = `FREE_TEXT` `DROPDOWN` `MIXED` `MAP_PAN` **`OTHER`**
`evidence.INPUT_MODE_VALUES` (W5F) = `FREE_TEXT` `DROPDOWN` `MIXED` `MAP_PAN`

`runner._validated_input_mode('OTHER')` 는 `RunnerError: Δ9 밖의 input_mode 다`
로 **예외를 던진다.** 즉 계약 어휘가 허용하는 값 하나가 실행 경로에서 거부된다.
어느 쪽이 정본인지는 A 의 어휘 결정이라 이 lane 이 바꾸지 않았다.

### 6.2 depth 귀속 기록이 두 곳에서 나오고 서로 다르다 — [실행]

- `<observation_id>/observation/depth_conditional_tokens.json` — runner 가 쓴다.
  `DepthAttributor` 가 미주입이면 `"included": null` 로 남는다.
- `V3RunResult.derived_flow.depth_conditional_tokens` — `FlowNormalizer` 가 낸다.
  `included_in_activation_depth` 에 실제 판정이 들어간다.

**FlowNormalizer 만 주입하면 evidence 파일은 `null`, 반환값은 판정값**이 된다.
둘을 같은 것으로 읽으면 안 된다. `DepthAttributor` 구현이 없는 것이 원인이고,
그 Protocol 은 §2 표에서 미구현으로 잡혀 있다.

### 6.3 safety 관문은 actuation 지점이 아니다 — [독해 + 실행]

`V3Runner._assert_action_allowed` 가 `driver.activate()` **직전에** 호출되는 것은
실행으로 확인했다(차단 시 `activate` 호출 0회). 그러나 **실제 클릭은
`SessionDriver` 안에서 일어나고**, 그 page 가 `guard.guard_page()` 를 통과한
`GuardedPage` 인지는 runner 가 보증하지 못한다. W5G 가 자기 known limitation 에
적은 구멍은 좁아졌을 뿐 닫히지 않았다. `SessionDriver`(W5H)가 올라올 때 그쪽에서
닫아야 한다.

---

## 7. C 인터페이스 요청 대조 — Addendum v2 7종

대조 대상: `gate1_adapter_spec.md` 의 **Addendum v2 (04:15 KST)** 7항.
대조 트리: 이 문서가 속한 커밋의 병합 트리(W5A·W5B·W5C·W5D·W5D1·W5E·W5F·W5G·W5J).
**W5H(SessionDriver)·W5I(ax-join) 는 이 트리에 병합돼 있지 않다** — 아래 판정은
그 두 lane 을 포함하지 않은 상태의 실측이다.

판정 어휘: **PRESENT** = 요청한 이름·의미의 필드가 산출물에 실재한다 /
**PARTIAL** = 일부만 있다(무엇이 있고 무엇이 없는지 한 줄로 갈라 쓴다) /
**ABSENT** = 없다.

**없는 것을 만들지 않았다.** 이 절은 요청을 충족시킨 기록이 아니라 현재 상태의 측정이다.

| # | C 요청 | 판정 | 근거 |
|---|---|---|---|
| ① | `terminal_dom` 캡처 (body dataset · visible marker 요소 · form input value) | **ABSENT** | 트리 전체에 `terminal_dom` 심볼 0개. `terminal.py` 는 `TerminalSignals` 21필드(전부 bool/str 판정 입력)만 받고 DOM 을 보지 않는다 |
| ② | `surface.entry_selector` | **ABSENT** | `surface.SurfaceMeasurement` 24필드에 selector 계열 필드가 없다. 행이 **어느 control 을 서술하는지** 산출물만으로는 특정 불가 |
| ③ | `surface.entry_is_floating` | **PARTIAL** | **있는 것**: FLOATING 판정 자체 — `_FLOATING_POSITIONS={fixed,sticky}` 로 `entry_zone == "FLOATING"` 을 낸다. **없는 것**: 독립 bool 필드가 없고, `entry_zone` 은 DRAWER>FLOATING>기하 우선순위로 **덮어쓰기**되므로 `DRAWER` 인 행이 동시에 floating 인지 복원할 수 없다 |
| ④ | `surface.visible_text_provenance` / `rendered_pseudo_text` | **ABSENT** | 두 심볼 모두 0개. 인접한 `accessible_name_source`(9값)는 **accessible name** 의 출처이지 visible text 의 출처가 아니다. `surface._resolve_name_source` 가 자기 KNOWN LIMITATION 에 "pseudo-element `::before` content 는 enum 에 '미상' 값이 없어 `NONE` 을 낸다"고 적어 뒀다 — 즉 C 가 요청한 그 경우가 현재 구분 불가로 알려져 있다 |
| ⑤ | `run_result.entry_selector_ignored: bool` | **ABSENT** | `run.json` 키는 `protocol_version` · `observation_id` · `service_id` · `task_id` · `run_id` · `entry_count` · `evidence_manifest_sha256` · `path_manifest_sha256` 8개뿐(`evidence.EvidenceRunWriter.seal`). 애초에 `TaskContract` 에 `entry_selector` 필드가 없어 hint 를 받는 경로 자체가 없다 |
| ⑥ | `fact_flow_step` bbox = task-entry 통제 + state id→marker | **PARTIAL** | **있는 것**: `FlowStep.bbox_before` (driver 의 `RawTransition.bbox_before` 를 그대로 싣는다). **없는 것 3개**: (a) `bbox_after` 필드가 없다, (b) 그 bbox 가 **task-entry control 의 것**이라는 제약이 코드에 없다 — driver 가 주는 값을 검사 없이 통과시킨다, (c) `state_before_id`/`state_after_id` 는 driver 문자열 그대로이며 marker 로 가는 map 이 어디에도 없다. 덧붙여 `build_path_manifest` 의 `steps[]` 는 bbox 를 아예 싣지 않는다 |
| ⑦ | contract 4필드 축자 echo (`task_instruction`·`fixed_fixture`·`task_family`·`endpoint_contract`) in `run_result.contract_echo` | **ABSENT** | `contract_echo` 심볼 0개. `run.json` 에 4필드 중 **0개**. path manifest 는 `task_contract_hash`·`endpoint_contract_hash` 만 싣는다 — 해시는 축자 원문이 아니므로 C 가 축자 대조를 할 수 없다. (`as_mart_record()` 도 4필드를 담지 않는다) |

집계: **PRESENT 0 · PARTIAL 2 (③⑥) · ABSENT 5 (①②④⑤⑦)**.

`gate1_adapter_spec.md` 서두가 "each item here is a condition for a clean PASS" 라고
적었으므로, 이 표대로면 GATE 1 에서 5–7 항목이 `NOT_TESTABLE` 이 된다. **그 사실을
숨기지 않기 위해 표기 그대로 낸다.** 어느 항목을 누가 채울지는 A 의 배정 사항이고
이 lane 은 배정하지 않는다.

---

## 8. R22 — capture-stack sha 계약 (문서화만, 구현은 W5I 소관)

**계약**: v3 의 **모든 관측 행**은 그 행을 만든 캡처 스택의 sha 를 함께 갖는다.
한 개가 아니라 **둘 이상**이다 —

| 성분 | 무엇의 sha 인가 | 왜 나눠야 하는가 |
|---|---|---|
| `engine_sha` | 판정 로직(engine/derive 계층)의 git sha | 같은 원자료를 다시 돌려도 판정이 달라질 수 있는 유일한 이유 |
| `driver_sha` | `SessionDriver`(W5H) 구현의 git sha | 같은 fixture 에서 무엇을 캡처했는지가 여기서 갈린다 |
| `session_sha` | 세션 구성(뷰포트·UA·locale·차단정책·probe 스크립트)의 sha | driver 코드가 같아도 세션 설정이 다르면 다른 관측이다 |

**하나로 접으면 안 되는 이유**: engine 만 바뀐 재판정과 driver 가 바뀐 재수집은
증거로서 지위가 다르다. 단일 `capture_sha` 로 접으면 "재판정인지 재수집인지"를
행에서 복원할 수 없고, `06 §6`(재수집은 새 `run_id`)의 판별 근거가 사라진다.

**실측 — 현재 상태**: 트리에 `capture_stack` · `engine_sha` · `driver_sha` ·
`session_sha` 심볼이 **0개**다(`grep` 전수). `run.json` 이 갖는 것은
`protocol_version`(= `evidence.V3_EVIDENCE_PROTOCOL_VERSION`, 프로토콜 판번호이지
코드 sha 가 아니다) 하나뿐이고, `build_retention_manifest` 가 받는 `producer_sha` 는
**runner 가 호출하지 않는 함수의 인자**다(§3 참조).
→ **R22 는 현재 계약으로만 존재하고 구현 0 이다.** W5I 가 채운다. 이 lane 은
계약만 적었고 필드를 만들지 않았다.

---

## 9. Δ8-R3a · Δ10-R13a 실측

### Δ8-R3a (GATE 1) — `task_role` 필드 존재 + 관측 행 적재 → **PRESENT (한 곳 예외)**

| 지점 | 상태 |
|---|---|
| `contracts.TaskContract.task_role` | **있다** (기본 `PRIMARY`, 어휘 `contracts.TASK_ROLES`) |
| `runner.V3Runner.run` 어휘 검사 | **있다** — 어휘 밖이면 `RunnerError` 로 **실행 거부**(fail-closed, `runner.py:590`) |
| `V3RunResult.task_role` | **있다** |
| `V3RunResult.as_mart_record()` | **있다** — 관측 행에 실제로 적재된다 |
| path manifest 최상위 | **있다** |
| `evidence.build_family_aggregate` / `build_denominator_chain` | **있다** — `applied_filter="task_role == 'PRIMARY'"` 를 산출물에 싣고, 다른 필터를 주면 `RunnerError` |
| `run.json` | **없다** — 8키에 `task_role` 이 없다 |

즉 **분모 판정 경로(mart·aggregate)는 전부 갖췄고, evidence 봉인 레코드만 없다.**
C 가 `run.json` 만 읽어 `task_role` 을 찾으면 못 찾는다.

### Δ10-R13a (GATE 1) — 판정 불능 값 → **PRESENT (표현이 두 갈래인 점을 명시한다)**

1. **`auth_gate_stage` 에 `UNDETERMINED` 존재** — **PRESENT.**
   `flow.AUTH_STAGE_VALUES = {NONE, UNDETERMINED, BEFORE_TASK_DISCOVERY, AFTER_TASK_SELECT, AT_ENDPOINT}`.
   타입이 `str`(not `str | None`)이라 **`None` 이 될 수 없다** — 판정 불능이 값으로 강제된다.
2. **`NONE` 은 적극적 주장** — **PRESENT.** `flow.py:326` 이 축자로
   "`auth_gate_stage` 의 `NONE`(auth 신호를 관측했고 없었다)과 `None`" 을 구분해 적어 뒀다.
   `terminal.AuthGateStage` 에도 같은 어휘가 있다.
3. **전 변수에 판정 불능 값** — **PRESENT, 단 표현이 두 갈래다.**

   | 변수군 | 판정 불능 표현 |
   |---|---|
   | `FlowNormalization.activation_depth` · `flow_step_count` · `menu_dependency` · `nav_container_depth` · `forced_dismissal_count` | `None` (0/False 로 접지 않는다) |
   | `DepthConditionalRecord.included_in_activation_depth` | `None` |
   | `FlowNormalization.auth_gate_stage` | 문자열 `UNDETERMINED` |
   | `obstruction.ObstructionStatus` · `BlockingBasis` · `DismissalState` | 문자열 `UNDETERMINED` |
   | `terminal.TerminalResolution` · `AuthGateStage` | 문자열 `UNDETERMINED` |
   | `surface.SurfaceMeasurement.entry_observed_state` 등 categorical | 문자열 `NOT_OBSERVED` |

   **한 산출물 안에 `None` · `UNDETERMINED` · `NOT_OBSERVED` 세 표현이 공존한다.**
   숫자형은 `None`, 닫힌 어휘형은 sentinel 문자열이라는 규칙성은 있으나 어디에도
   그 규칙이 명문화돼 있지 않다. 하네스가 셋을 하나로 접으면 Δ10 이 막으려는 손실이
   그대로 발생한다.

---

## 10. Protocol 일제 `isinstance` 점검 — 실측 11종

의뢰 문면은 "Protocol 7종"이었으나 **트리에 선언된 `runtime_checkable` Protocol 은
11종**이다(`runner.py` 이름공간 전수). 문면이 아니라 측정값을 따른다.
결과 표는 **§2** 에 있고, 회귀로 고정한 것은
`tests/test_w5k_seam_integration.py::test_protocol_sweep_covers_every_runner_protocol`
(전수성) + `test_protocol_conformance_positive` / `test_protocol_conformance_open_seams`
(각 경계의 적합/부적합)다.

요약: **적합 2 (`SafetyGuard` · `ScoutStrategy`) · 부적합 8 · 구현부재 1 (`SessionDriver`)**.

`SafetyGuard` 는 이 lane 이 SEAM 1 에서 닫았다. 나머지는 열려 있다.

---

## 11. SEAM 3 실측 — `CandidateBinder` / `EligibilityChecker` (보고만, 고치지 않았다)

이 절은 **측정 결과이고 수정 제안이 아니다.** 이 lane 은 두 경계를 건드리지 않았다.

### 11.1 `EligibilityChecker` — 구현이 없고, 없으면 기본계약이 실행을 막는다

- `discovery.py` · `registry.py` 에 `eligib` 를 포함하는 공개 심볼 **0개**
  (`registry` 쪽 `mobile_web_eligibility` 는 manifest **필드명**이지 checker 가 아니다).
- 미주입 시 `runner.run` 은 `contract.mobile_web_eligibility` 를 그대로 쓴다.
- 그런데 `TaskContract.mobile_web_eligibility` 의 **기본값은 `PRECHECK_REQUIRED`** 이고,
  `runner.ELIGIBILITY_VALUES` = {`ELIGIBLE_PUBLIC_MOBILE_WEB`, `APP_REQUIRED_EXCLUDE`,
  `ACCESS_BLOCKED_REVIEW`, `URL_REMAP_REQUIRED`} 에 **`PRECHECK_REQUIRED` 가 없다.**
- 결과: **동결 manifest 값 그대로의 계약을 `EligibilityChecker` 없이 `run()` 에 넣으면
  `RunnerError` 로 거부된다.** 조용히 넘어가지 않는다 — 이건 시끄러운 실패이므로
  결함이라 단정하지 않고 그대로 보고한다. 다만 GATE 1 하네스는 checker 를 붙이거나
  계약값을 `ELIGIBLE_PUBLIC_MOBILE_WEB` 로 확정해 넣어야 한다.

### 11.2 `CandidateBinder` — 형태는 맞는데 **조용히 0건**이 된다 (실행으로 확인)

측정 절차: 실물 `V3Runner` + 실물 `MinPathScoutStrategy` + 실물
`discovery.discover_task_candidates` 를 그대로 위임하는 최소 어댑터.

```
isinstance(naive_binder, runner.CandidateBinder)  → True      # Protocol 은 메서드 이름만 본다
naive_binder.bind(...)                            → [TaskCandidate]  (1건)
issubclass(discovery.TaskCandidate, Mapping)      → False
──────────────────────────────────────────────────────────────
driver.activate 호출 횟수                          → 0
V3RunResult.raw_steps                             → 0
V3RunResult.phase_reached                         → Phase.MART (값 "FLOW_MART")
V3RunResult.refusal                               → None
```

같은 배선에서 `TaskCandidate` 를 `dict` 로만 감싸면:

```
driver.activate 호출 횟수                          → 2
V3RunResult.raw_steps                             → 1
```

**원인**(코드 위치까지):
`runner.CandidateBinder.bind` 의 반환 계약은 `Sequence[Mapping[str, Any]]` 인데
`discovery.discover_task_candidates` 는 `list[TaskCandidate]`(frozen dataclass)를 낸다.
`scout_strategy.MinPathScoutStrategy.propose_next` 는 후보를 고를 때
`if isinstance(c, Mapping) and c.get("selector")` 로 거른다 — dataclass 는 전부
탈락하고, 남는 후보가 없으니 `propose_next` 가 `None` 을 반환하며, runner 는 그것을
**정상 종료 신호**로 읽는다.

**측정된 성질**: 결과는 예외도 refusal 도 아니고 `phase_reached=Phase.MART` 의
**성공 형태를 한 0건 관측**이다. "후보를 못 찾았다"와 "형이 안 맞아 전건 탈락했다"가
산출물에서 구분되지 않는다.

**두 경계는 어긋난다 — 어긋난다고 보고한다.** 어느 쪽(Protocol 을 dataclass 로
넓히기 / binder 어댑터가 변환 / scout 의 `isinstance` 완화)이 정본인지는 이 lane 의
권한이 아니고, `discovery.py` 도 `scout_strategy.py` 도 이 lane 소유가 아니다.
고치지 않았다.

---

## 12. SEAM 1 실측 — 금지 행동 12종 중 이 관문이 실제로 막는 것 (9/12)

`runner.SafetyGuard` ↔ `safety.ActivationSafetyGuard` 를 이었다. 이름을 맞춘 것이
아니라 `PlannedAction` 을 detector 가 읽는 candidate 키로 번역해
(`safety.planned_action_to_candidate`) 기존 `authorize()` 에 건다 — 새 판정 로직은
만들지 않았다.

**실측**: 실물 `V3Runner` × 실물 `ActivationSafetyGuard` 로 12종을 훑었다.
판정은 `SafetyStop` 발생 여부가 아니라 **`driver.activate` 호출 0회**로 확인한다.

| SSOTV3 금지 행동 | 발화 | 나오는 `ForbiddenAction` |
|---|---|---|
| OTP | **차단** | `OTP_ENTRY` |
| CAPTCHA solve/bypass | **차단** | `CAPTCHA_SOLVE` |
| 송금 | **차단** | `PAYMENT` ← `FUNDS_TRANSFER` 가 아니다 |
| 장바구니 | **차단** | `ADD_TO_CART` |
| 주문 | **차단** | `ORDER_PLACE` |
| 결제 | **차단** | `PAYMENT` |
| 예약 | **차단** | `BOOKING_CONFIRM` |
| 좌석선택 | **차단** | `SEAT_SELECT` |
| 외부앱 실행 | **차단** | `EXTERNAL_APP_LAUNCH` |
| credential | **막지 못한다** | — |
| login submit | **막지 않는다(설계)** | — |
| 실제 개인정보 | **막지 못한다** | — |

### 막지 못하는 2종의 원인 — 구조적이다

`guard` 는 credential 을 `input[type=password]`·`autocomplete` 로, 개인정보를
**field name**(`주민등록번호|ssn|passport_no` …)으로 판정한다. 그런데
`runner.PlannedAction` 의 필드는 `action_token` · `control_selector` ·
`control_role` · `control_visible_text` · `control_accessible_name` **다섯뿐**이다.
그 신호가 seam 을 건너오지 못한다.

→ **이 관문은 텍스트로 드러나는 금지 행동만 막는다.** 나머지는 actuation 지점
(`ActivationSafetyGuard.guard_page()` → `GuardedPage.fill`)이 막아야 하고, 그 경로는
`SessionDriver`(W5H)가 올라와야 검증 가능하다 — §6.3 의 구멍과 같은 구멍이다.

`login submit` 은 결함이 아니라 의도다: `guard._CATEGORY_TO_FORBIDDEN` 이 `LOGIN` 을
**뺐다**(`00_SSOT §6` `D3-09` — generic login 존재로 중단 금지). 금지는 로그인 링크
클릭이 아니라 자격정보 **입력·제출**이며 그건 위 두 항목과 같은 이유로 seam 밖이다.

### 탐지 문구의 한계 (실측)

`보안문자` 단독 · `본인인증` · `이체`(`이체하기` 는 잡힌다)는 현재 어휘로 **탐지되지
않는다**. 어휘 확장은 A 의 결정이라 이 lane 이 바꾸지 않았다.

### 회귀 위치

`tests/test_w5k_seam_integration.py` —
`test_seam1_forbidden_sweep_guard_fires`(9종 양성) ·
`test_seam1_forbidden_sweep_known_non_firing`(3종 미발화 고정) ·
`test_seam1_negative_control_sweep`(허용 4종 음성대조) ·
`test_seam1_translation_table_is_the_load_bearing_part`(순진한 `asdict` 배선이
**전건 허용**으로 접히는 fail-open 경로를 명시 관측).
