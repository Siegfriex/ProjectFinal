# PARTIAL_DEPTH_FIXTURES — partial-depth semantics 독립 검증 (Claude C recovery audit)

- 검증 대상: B 엔진 collector `222ef2c28ed5971b3c9f8b07120b7627d2617476` — `Scout.scout` 를 fixture 로 직접 호출 (FIXTURE 모드, 실제 서비스 미접속). 엔진 소스는 읽기 전용으로 두었고 한 줄도 고치지 않았다.
- 계약 정본: `A1_MEASUREMENT_OPERATIONALIZATION.md` §1.3·§1.4·§1.5, `A2_VOCABULARY_AND_SCHEMA_BINDING.md` §1.5.1·§1.5.1a·§1.9 규칙 P-2.
- 재현: `python research/landing_accessibility/assurance/recovery/fixtures/run_partial_depth_fixtures.py` (저장소 `.venv`, Playwright chromium). 기계 판독 결과: `fixtures/PARTIAL_DEPTH_RESULTS.json`.
- 여기의 PASS/FAIL 은 **synthetic fixture 에 대한 engine test** 다. 실제 서비스에 대한 research finding 이 아니다.

## 결과 표

| 케이스 | task 정의 (archetype / region_def / endpoint_def / signal_type) | fixture 경로 | 기대 NED/IED/MPFED · status · area | 실측 NED/IED/MPFED · status · area | 판정 |
|---|---|---|---|---|---|
| CASE1 | ITEM_DETAIL / `ITEM_LIST_REGION` / `ITEM_DETAIL_OPEN` / DOM_AX_ROLE | 랜딩(body `data-region`) → 후보 0개 막다른 페이지 | **0 / NULL / NULL** · UNRESOLVED(02 §7 종료값) · **OBSERVED** | **NULL / NULL / NULL** · UNRESOLVED(NO_SIGNAL) · **NOT_OBSERVED**, steps 0행 | **FAIL** — NED 소실 |
| CASE2 | ITEM_DETAIL / 同 / 同 / DOM_AX_ROLE | 랜딩 → s1 → s2(`data-region`) → LOGIN gate(password input) | 2 / NULL / NULL · AUTH_GATE_REACHED · OBSERVED | 2 / NULL / NULL · AUTH_GATE_REACHED (gate RESOLVED LOGIN) · OBSERVED, endpoint_reached=0, manifest 없음 | PASS |
| CASE3 | ITEM_DETAIL / 同 / 同 / DOM_AX_ROLE | 랜딩(+decoy) → s1 → s2(`data-region`) → endpoint(`data-endpoint-reached`) | 2 / 1 / 3 · FUNCTION_ENDPOINT_REACHED · OBSERVED | 2 / 1 / 3 · FUNCTION_ENDPOINT_REACHED · OBSERVED, segments NED,NED,IED | PASS |
| CASE4 | ITEM_DETAIL / `ITEM_LIST_REGION` / **None** / DOM_AX_ROLE | 랜딩(body `data-region`) → endpoint 마커 페이지(후보 0개) | **0** / NULL / NULL · ≠FUNCTION_ENDPOINT_REACHED · OBSERVED, endpoint_reached=0 | **NULL** / NULL / NULL · UNRESOLVED(NO_SIGNAL) · **NOT_OBSERVED**, endpoint_reached=0 | **FAIL** — NED 소실 (IED/MPFED NULL·강제 산출 0 은 충족) |
| CASE4b (진단) | CASE4 와 동일 task | 랜딩(body `data-region`) → LOGIN gate | 0 / NULL / NULL · AUTH_GATE_REACHED · OBSERVED | 0 / NULL / NULL · AUTH_GATE_REACHED · OBSERVED | PASS — NED 소실은 **UNRESOLVED 종료 경로에만** 발생함을 분리 |
| CASE5a | ITEM_DETAIL / **None** / **None** / **CODEBOOK_PENDING** (= E001 실제 구성, `executor.py:68-75`) | 랜딩(`data-region`) → endpoint 마커 페이지 | endpoint_reached=0, ≠FUNCTION_ENDPOINT_REACHED, manifest 없음 | NULL/NULL/NULL · UNRESOLVED(NO_SIGNAL) · NOT_OBSERVED, manifest 없음 | PASS (승격 0 — 단, 이유는 P-2 가드가 아니라 정의가 `None` 이라 detector 가 상수 False 인 것) |
| CASE5b | ITEM_DETAIL / `ITEM_LIST_REGION` / `ITEM_DETAIL_OPEN` / **CODEBOOK_PENDING** | 同 | endpoint_reached=0, ≠FUNCTION_ENDPOINT_REACHED, manifest 없음 | **0 / 1 / 1 · FUNCTION_ENDPOINT_REACHED · OBSERVED, endpoint_reached=1, TaskManifest 동결됨** | **FAIL** — CODEBOOK_PENDING 인 task 가 endpoint 로 승격되고 Path Freeze 까지 됨 |

합계: PASS 4 / FAIL 3 (CASE1, CASE4, CASE5b). UNVERIFIABLE 없음 — 엔진은 fixture 의 `[data-region]`·`[data-endpoint]`·`body[data-endpoint-reached]`·`input[type=password]` 신호를 전부 읽었고(step 추적으로 확인), fixture 를 엔진에 맞춰 조정한 곳은 없다.

## FAIL 의 코드 원인 (파일:줄, `src/landing_accessibility/engine/`)

### F-1. CASE1·CASE4 — 영역이 관측됐는데 UNRESOLVED 로 끝나면 NED 가 NULL 로 떨어진다

계약: A1 §1.5 표 3행 "영역만 관측, endpoint 전 종료 → `area_signal_status=OBSERVED`, `NED=k`, `IED=NULL`, `MPFED=NULL`, `endpoint_status` = 02 §7 의 해당 종료값". `UNRESOLVED` 는 02 §7 / A2 §1.5.1 의 7값 중 하나이므로 이 행의 적용 대상이다. A1 §1.5 마지막 줄 "NULL 을 0 으로 대체하지 않는다"의 역방향 — 관측된 0/정수를 NULL 로 바꾸는 것 — 도 §1.4 행1 (`s0` 영역 성립 → `k=0`) 과 어긋난다.

엔진:
- `l1_engine.py:433-434` — `area_index = None`, `endpoint_index = None` 으로 초기화.
- `l1_engine.py:532` — 매 prefix 평가마다 `area_here = _first_index(landing_area, steps, "area_signal_detected")` 로 k 를 **계산은 한다** (CASE1/4 에서 0).
- `l1_engine.py:540` (endpoint 종료) 와 `:558` (gate 종료) 에서만 `area_index = area_here` 를 대입한다. 두 분기 다 `break` 로 끝난다.
- 종료 없이 큐가 고갈되거나 예산이 발화하면 `:600-608` 에서 `status = UNRESOLVED` 를 정하지만 `area_index` 는 `:433` 의 `None` 그대로다.
- `:610-616` `compute_depth(area_step_index=area_index=None, …)` → `depth.py:166-176` 의 `area_step_index is None` 분기 → `(None, None, None, NOT_OBSERVED, …)`.
- 같은 이유로 `best_steps` 도 빈 리스트로 남아(`:432`, `:541`, `:564` 에서만 대입) UNRESOLVED 관측은 `fact_task_step` 행이 0개다 — 관측된 `area_signal_detected=1` step 이 저장되지 않으므로 A1 §1.8 "저장된 step 신호만으로 재계산 가능" (규칙 D-1) 도 이 경로에서는 성립하지 않는다.

즉 `depth.py:141-186` 의 `compute_depth` 자체는 계약대로 (`area_step_index=k` 를 주면 `(k, None, None, OBSERVED)` 를 낸다 — CASE2/CASE4b 가 그 증거) 이고, 결함은 **Scout 가 UNRESOLVED 경로에서 `area_here` 를 `area_index` 로 넘기지 않는 것**(`l1_engine.py:600-616` 에 `area_index` 갱신 없음) 이다.

B 자체 fixture `unresolved_route.html` 이 이것을 잡지 못한 이유: 그 케이스의 task 는 `region_definition=None` (`scripts/run_fixture_engine.py:112-116`) 이라 영역이 애초에 성립하지 않아 NED=NULL 이 정답이었다. "영역 관측 + UNRESOLVED" 조합은 B fixture 세트에 없다.

E001 실제 실행에의 함의: `DEPTH_DATAFLOW_222ef2c.md` §4 대로 59 타깃 전건이 `region_definition=None` 으로 들어가므로 F-1 은 현재 산출물에서 **발현되지 않는다** (NED 는 어차피 NULL). 하지만 region 정의가 주입되는 순간(codebook 동결 후) UNRESOLVED 로 끝나는 모든 타깃에서 NED 가 소실된다 — A1 §2.4 우측절단 집계("8회 안에서 endpoint 는 못 봤지만 영역은 k 에서 봤다")가 불가능해진다.

### F-2. CASE5b — `CODEBOOK_PENDING` 이 endpoint 승격·Path Freeze 를 막지 못한다

계약: A2 §1.9 규칙 P-2 "`region_signal_type = CODEBOOK_PENDING` 인 task 는 `mapping_status = FROZEN` 으로 전이할 수 없다"; A2 §1.5.1 `FUNCTION_ENDPOINT_REACHED` = "`dim_representative_task.endpoint_definition` 이 정의한 상태에 도달" 이며 그 정의는 P-A codebook 이 동결한다 (§1.5.1a E-5, §1.9 P-1). codebook 이 pending 이면 정의가 동결되지 않았으므로 충족 판정의 근거가 없다.

엔진:
- `l1_engine.py:100-105` `TaskDefinition.mapping_frozen_allowed()` 가 P-2 를 구현하지만 **호출자가 없다** (src/scripts grep 0건 — `DEPTH_DATAFLOW_222ef2c.md` §1 표와 일치).
- `l1_engine.py:201-218` `detect_area_signal`, `:221-231` `detect_endpoint_signal` — `task.region_signal_type` / `task.endpoint_signal_type` 을 읽지 않는다. 분기는 `region_definition is None` (:213) / `endpoint_definition is None` (:223) 뿐이다.
- `l1_engine.py:538-543` — endpoint 신호가 잡히면 signal_type 과 무관하게 `FUNCTION_ENDPOINT_REACHED`.
- `l1_engine.py:662-680` — `depth.endpoint_reached` 이면 `TaskManifest` (Path Freeze) 를 만든다. `mapping_frozen_allowed()` 검사 없음.

해석 주의: P-2 의 문면은 `dim_representative_task.mapping_status` 전이 규칙이다. Scout 의 `TaskManifest` 는 그 컬럼을 직접 쓰지는 않는다. 그러나 (i) `FUNCTION_ENDPOINT_REACHED` 의 정의가 동결된 `endpoint_definition` 을 전제하고, (ii) 엔진이 P-2 가드를 두고도 어디서도 호출하지 않으므로, "CODEBOOK_PENDING 인 task 에 대해 false endpoint 승격 0" 이라는 검증 목표에 대해서는 FAIL 로 기록한다. 실제 E001 구성(CASE5a) 에서는 정의가 `None` 이라 결과적으로 승격이 0 이지만, 그것은 가드의 효과가 아니라 detector 가 상수 False 인 부수효과다 — 정의 문자열이 채워지는 즉시(CASE5b) 가드 부재가 드러난다.

## PASS 케이스가 확인해 준 것

- CASE2: 승격 불가 archetype(ITEM_DETAIL) 에서 RESOLVED LOGIN gate 가 `AUTH_GATE_REACHED` 로 가고 (`depth.py:35-45` `ENDPOINT_GATE_KINDS[ITEM_DETAIL] = ∅`, `:66-74`), 영역 k=2 는 보존되며 IED/MPFED 는 NULL — A1 §1.5 행3 · A2 §1.5.1a 표 4행 그대로. gate 종료 경로(`l1_engine.py:544-566`) 는 `area_index` 를 넘긴다.
- CASE3: k=2, m=3 → (2, 1, 3), segment NED/NED/IED — A1 §1.3 · §1.8.
- CASE4b: `endpoint_definition=None` 이어도 영역 관측은 살아남는다 — 단 종료가 gate 로 확정될 때만. F-1 이 UNRESOLVED 경로에 국한된 결함임을 분리한다.
- CASE5a: E001 실제 TaskDefinition 구성은 어떤 fixture 신호에도 반응하지 않는다 (NED/IED/MPFED 전부 NULL, NOT_OBSERVED, UNRESOLVED_NO_SIGNAL) — `DEPTH_DATAFLOW_222ef2c.md` §3(b) 의 실측 확인.

## 산출물

- fixtures: `assurance/recovery/fixtures/case{1,2,3,4,4b,5}_*.html` (15 파일, 외부 자원 참조 0 — `grep http` 0건)
- 실행기: `assurance/recovery/fixtures/run_partial_depth_fixtures.py`
- 결과: `assurance/recovery/fixtures/PARTIAL_DEPTH_RESULTS.json` (task 정의·기대·실측·step 추적·gate 판별 note 포함)
- evidence run: `assurance/recovery/fixtures/_out/evidence/partial-depth-<ts>/` (Scout 가 `EvidenceRun` 을 context 생성에만 쓰므로 manifest 항목은 없다; seal 하지 않음)
