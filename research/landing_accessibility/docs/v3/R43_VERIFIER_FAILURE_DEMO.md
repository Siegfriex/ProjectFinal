# R43 — 검증 함수 실패 실증 (W5R)

> **R43** (`Δ48`) — 검증 함수는 자기 실패를 실증하지 못하면 검증 함수가 아니다.
> `verify_*` · `assert_*` · `check_*` 계열 전수에 대해 각각 **실패하는 입력이 존재함을
> 실증한다. `GATE 1` 조건이다.** 실증할 수 없으면 그 함수는 **이름이 약속을 하고
> 이행하지 않는 것**이므로 시정하거나 제거한다. **이름만 남기지 않는다.**

| | |
|---|---|
| 검사기 | `src/landing_accessibility/v3_runner/r43/check.py` |
| 실증기 (`R40`) | `src/landing_accessibility/v3_runner/r43/control_failure_demo.py` |
| 산출 (`R35` 4요소) | `docs/v3/R43_CHECK_RESULT.json` |
| sidecar | `docs/v3/R43_FAILURE_DEMO.json` |
| 회귀 시험 | `tests/test_w5r_r43_check.py` |
| 실행 | `PYTHONPATH=src python -m landing_accessibility.v3_runner.r43.check` |

---

## 0. 열거 범위 — "전수" 가 **무엇의** 전수인가

`Δ48` 이 `B` 에 대해 옳다고 적은 것: *"'전수' 라고 쓰지 않았다 — `engine/` 은 0건이
아니라 **미탐색**으로 적었다."* 같은 규율을 지킨다.

| | |
|---|---|
| **열거한 것** | `src/landing_accessibility/v3_runner/**/*.py` 안의 **모든** `def` / `async def` |
| **선별 규칙** | 이름에서 선행 `_` 를 뗀 뒤 `verify_` · `assert_` · `check_` 로 시작하거나 정확히 `check` / `verify` / `assert` 인 것 |
| **방법** | `ast` 로 파싱. 클래스 메서드·중첩 함수 포함. 정규식은 데코레이터·줄바꿈 시그니처에서 새므로 쓰지 않았다 |
| **제외** | `v3_runner/r43/**` — 이 lane 의 도구 자신. 도구가 자기를 세면 목록이 자기지시가 된다 |
| **v3_runner 총 건수** | **20건** |
| **`engine/`** | **27건 열거 · 0건 실증.** `ENUMERATED_NOT_DEMONSTRATED` |

`engine/` 을 **0건이라고 쓰지 않는다.** 27건이 있고 이 lane 은 그중 **하나도 실증하지
않았다.** `engine/` 은 이 lane 의 수정 금지 대상이며 다른 평면 소관이다. 함수명 목록은
`Δ42`/`R44` 를 지켜 여기 적지 않는다 — 독립 열거를 해야 하는 평면이 있다.

접미사 없는 `verify`/`assert` 를 규칙에 넣은 이유: `engine/evidence.py::EvidenceRun.verify`
가 실제로 그 형태다. `v3_runner` 안에는 해당 사례가 없어 건수는 변하지 않지만,
**규칙이 그 형태를 놓치지 않는다는 것 자체가 이 열거의 주장**이다.

---

## 1. 무엇이 "실패" 인가 — 함수마다 다르다

이 계열은 실패를 세 형태로 낸다. **각 함수가 선언한 형태로만** 실증했다.

| 선언 | 실패의 모습 |
|---|---|
| `RAISE:<Exc>` | 선언된 예외를 던진다 |
| `DICT_OK_FALSE` | `{"ok": False}` 를 돌려준다 |
| `NONEMPTY_LIST` | 비어 있지 않은 실패 목록을 돌려준다 |
| `NEVER` | 실패를 표현할 수단이 본문에 없다 (Protocol 선언 · 기록용 fake) |

### 크래시는 실패가 아니다 (`R36`)

`DICT_OK_FALSE` 를 선언한 함수가 `TypeError` 로 죽는 것은 **실증이 아니다.** 그것은
"검증이 작동했다" 가 아니라 "입력이 함수를 깨뜨렸다" 다. 이 구분을 만든 사건이
`Δ46`/`R36` 이다 — `A` 가 데이터 변형 사례에 `positive_control_fail` 이라 이름 붙였는데
실제로는 크래시였다.

검사기는 선언 예외가 **아닌** 예외를 `CRASH` 로 따로 세고, `CRASH` 만 나는 함수는
**`CANNOT_FAIL`** 로 판정한다. 이 규칙이 살아 있는지는 합성 대조
`SYNTHETIC::verify_crash_only` 가 매 실행마다 잰다.

---

## 2. 두 축으로 판정한다 — `can_fail` 과 `vacuous_pass`

`Δ48` 이 실제로 본 결함은 "실패 입력이 없다" 가 아니라 **"아무것도 검사하지 않고
성공을 낸다"** 였다. 이 둘은 다른 사실이다.

- **축 1 `CAN_FAIL` / `CANNOT_FAIL`** — 선언된 실패를 내는 입력이 존재하는가
- **축 2 `VACUOUS_PASS`** — 성공을 냈는데 **검사한 흔적이 0** 인 입력이 존재하는가

축 2 의 판정식: dict 반환 검증기가 `ok: True` 이면서 증거 목록(`verified` ·
`mismatched` · `missing` …)이 **전부 비어 있으면** 그 `True` 는 "대조했고 맞았다" 가
아니라 "대조할 것이 없었다" 다. 두 문장이 같은 출력으로 나오는 것은 `Δ39-R32` 와
같은 형태의 결함이다.

**축 1 만 재면 `Δ48` 이 지목한 함수를 놓친다.** 아래 §4 가 그 사례다.

---

## 3. 대조 — `must_flag` / `must_not_flag` (`Δ40` 명칭)

`must_flag` = 도구가 **결함으로 잡아야 하는** 것(기대 `CANNOT_FAIL`).
`must_not_flag` = 도구가 **잡으면 안 되는** 것(기대 `CAN_FAIL`).

| role | 대상 | 기대 | 관측 | 통과 |
|---|---|---|---|---|
| `must_flag__synthetic_always_ok` | `SYNTHETIC::verify_always_ok` | `CANNOT_FAIL` | `CANNOT_FAIL` | ✅ |
| `must_flag__synthetic_crash_only` | `SYNTHETIC::verify_crash_only` | `CANNOT_FAIL` | `CANNOT_FAIL` | ✅ |
| `must_flag__protocol_stub` | `runner.py::EligibilityChecker.check` | `CANNOT_FAIL` | `CANNOT_FAIL` | ✅ |
| `must_not_flag__synthetic_raiser` | `SYNTHETIC::assert_positive` | `CAN_FAIL` | `CAN_FAIL` | ✅ |
| `must_not_flag__repo_raiser` | `evidence.py::assert_layer_qualified` | `CAN_FAIL` | `CAN_FAIL` | ✅ |

**5/5 통과.**

### 지시받은 `must_not_flag` 를 대체한 이유

과업 지시는 `assert_search_strategy_declared` 계열을 `must_not_flag` 로 쓰라고 했다.
**그 이름의 함수는 `v3_runner` 에 존재하지 않는다** (`scout_strategy.py` 포함 전수
검색 0건). 없는 것을 대조로 적으면 대조가 있는 것처럼 읽히므로, 같은 성질의
`evidence.py::assert_layer_qualified` (선언 예외를 안정적으로 내는 실제 저장소 함수)로
대체하고 그 사실을 여기 적는다.

### 합성 대조를 함께 둔 이유

저장소 안의 함수만 대조로 쓰면, **그 함수가 고쳐지는 순간 대조가 조용히 사라진다.**
합성 대조 3건은 저장소 상태와 무관하게 **방법 자체**를 잰다. `_disable_must_flag`
변형(§6)이 깨뜨리는 것도 이 합성 대조다.

---

## 4. 지정 대조의 반증 — `verify_retention_manifest`

과업 지시는 이 함수를 `must_flag` 로 지정하며 **"실패시킬 수 없어야 한다 · 도구가
`CANNOT_FAIL` 로 잡아야 한다 · 못 잡으면 방법이 틀린 것"** 이라고 했다.

**관측은 지시와 다르다. 그리고 방법이 틀린 것이 아니다.**

| | |
|---|---|
| 지시된 기대 | `CANNOT_FAIL` |
| 관측 (축 1) | **`CAN_FAIL`** — 실패시킨 입력 3종 |
| 관측 (축 2) | **`VACUOUS_PASS` 참** |
| 게이트 | **아니다** (아래 근거) |

실패시킨 입력 3종 (전부 선언 형태 `{"ok": False}` 로 관측):

1. 파일 `sha256` 을 `0*64` 로 변조 → `mismatched` 비지 않음
2. manifest 에만 있고 디스크에 없는 `path` → `missing` 비지 않음
3. `aggregate_sha256` 을 `0*64` 로 변조 → `aggregate_mismatched` 비지 않음

`evidence.py:625-652` 는 실제로 `sha256_of_file` 을 **재계산해** manifest 값과 비교한다.
`git log -L625,655` 상 이 함수는 도입 커밋(`e8d8829`) 이후 **한 번도 바뀌지 않았다** —
즉 `Δ48` 이 관찰하던 시점의 소스도 이것과 같다.

### 그러면 `Δ48` 은 무엇을 본 것인가

`Δ48` 의 문장은 이랬다: *"`verify_retention_manifest` 가 **아무것도 검증하지 않고**
`ok: True` 를 내므로 이 단언은 깨질 수 없다."*

이 문장은 **입력 하나에 대해서는 참이고, 함수 전체에 대해서는 참이 아니다.**

```
verify_retention_manifest({}, base=...)
→ {"verified": [], "mismatched": [], "missing": [],
   "aggregate_mismatched": [], "ok": true}
```

`roots` 키가 없으면 `manifest.get("roots", [])` 의 순회가 **0회**이고, 무엇도 대조하지
않은 채 `ok: True` 가 나온다. `test_w5f_runner_core.py:752` 의 단언이 깨질 수 없었던
이유는 **함수가 검증을 안 해서가 아니라 그 호출이 공허한 경로를 탔기 때문**이다.

정정된 진술은 이렇다:

> `verify_retention_manifest` 는 실패할 수 있다. 다만 **공허 통과 경로가 있고**,
> 문제의 단언이 정확히 그 경로를 탔다. 시정 대상은 함수의 전부가 아니라 **그 경로**다.

`B` 의 지적("그 테스트가 이 함수가 검증을 안 한다는 사실을 가렸다")의 **핵심은
그대로 유효하다** — 테스트가 결함을 가렸다는 것. 틀린 것은 가려진 결함의 **이름**이다.
`R17`/`Δ48` 의 규율대로, 헤드라인의 진술만 정정하고 판정(시정 필요)은 유지한다.

### 왜 게이트에 걸지 않았나

이 대조는 **방법이 아니라 저장소 상태에 대한 주장**이다. 관측이 지시와 다르면
"내 방법이 틀렸다" 가 아니라 "지시의 전제가 틀렸다" 일 수 있고, 실제로 소스와 git
이력이 후자를 가리킨다. 그래서 게이트가 아니라 **반증 기록**으로 낸다
(`R43_CHECK_RESULT.json` 의 `briefed_control.status = "FALSIFIED"`).
방법 검증은 §3 의 합성 대조 3건이 담당하며, 그것들은 저장소가 어떻게 바뀌어도 산다.

**"못 잡으면 방법이 틀린 것" 이라는 조건이 성립하려면 도구가 `CANNOT_FAIL` 을 잡을
수 있어야 한다.** 그 능력은 `must_flag__synthetic_always_ok` 로 별도 실증했다 —
구조적으로 실패할 수 없는 함수를 넣으면 도구가 `CANNOT_FAIL` 로 잡는다.

---

## 5. 판정 — 20건

CAN_FAIL 실증 = 선언된 실패 형태를 실제로 낸 입력의 건수.

| 함수 | 분류 | 선언 실패 형태 | 판정 | 실증 입력 | 공허통과 |
|---|---|---|---|---|---|
| `evidence.py::_assert_no_inlined_binary` | VERIFIER | `RAISE:InlinedBinaryError` | **CAN_FAIL** | 3 | — |
| `evidence.py::EvidenceRunWriter._assert_writable` | VERIFIER | `RAISE:EvidenceError\|RunSealedError` | **CAN_FAIL** | 2 | — |
| `evidence.py::verify_manifest_linkage` | VERIFIER | `RAISE:ManifestLinkageError` | **CAN_FAIL** | 2 | — |
| `evidence.py::verify_evidence_run` | VERIFIER | `DICT_OK_FALSE` | **CAN_FAIL** | 1 | **예** |
| `evidence.py::verify_retention_manifest` | VERIFIER | `DICT_OK_FALSE` | **CAN_FAIL** | 3 | **예** |
| `evidence.py::assert_layer_qualified` | VERIFIER | `RAISE:LayerQualificationError` | **CAN_FAIL** | 3 | — |
| `evidence.py::assert_coordinates_preserved` | VERIFIER | `RAISE:CoordinateDropError` | **CAN_FAIL** | 3 | — |
| `evidence.py::verify_denominator_chain` | VERIFIER | `RAISE:DenominatorError` | **CAN_FAIL** | 2 | — |
| `evidence.py::assert_depth_attribution_evidenced` | VERIFIER | `RAISE:DepthAttributionEvidenceError` | **CAN_FAIL** | 3 | — |
| `r32_check.py::check` | VERIFIER | `NONEMPTY_LIST` | **CAN_FAIL** | 1 | — |
| `runner.py::EligibilityChecker.check` | PROTOCOL_DECLARATION | `NEVER` | **CANNOT_FAIL** | 0 | — |
| `runner.py::SafetyGuard.assert_action_allowed` | PROTOCOL_DECLARATION | `NEVER` | **CANNOT_FAIL** | 0 | — |
| `runner.py::verify_path_manifest_hash` | VERIFIER | `RAISE:PathManifestHashMismatchError` | **CAN_FAIL** | 3 | — |
| `runner.py::V3Runner.verify_contract_hashes` | VERIFIER | `RAISE:ContractHashMismatchError` | **CAN_FAIL** | 4 | — |
| `runner.py::V3Runner._assert_action_allowed` | VERIFIER | `RAISE:ProhibitedActionError` | **CAN_FAIL** | 2 | — |
| `safety.py::ActivationSafetyGuard.assert_action_allowed` | VERIFIER | `RAISE:SafetyStop` | **CAN_FAIL** | 1 | — |
| `safety.py::GuardedPage._check_press` | VERIFIER | `RAISE:SafetyStop` | **CAN_FAIL** | 1 | — |
| `safety.py::GuardedPage._check_text` | VERIFIER | `RAISE:SafetyStop` | **CAN_FAIL** | 1 | — |
| `safety.py::GuardedPage.check` | ACTUATION_NAME_COLLISION | `RAISE:SafetyStop` | **CAN_FAIL** | 1 | — |
| `safety.py::RecordingPage.check` | TEST_DOUBLE | `NEVER` | **CANNOT_FAIL** | 0 | — |

합성 대조(저장소 함수 아님, 건수에 포함하지 않는다):

| 대상 | 선언 | 판정 | 실증 입력 |
|---|---|---|---|
| `SYNTHETIC::verify_always_ok` | `DICT_OK_FALSE` | **CANNOT_FAIL** | 0 |
| `SYNTHETIC::verify_crash_only` | `DICT_OK_FALSE` | **CANNOT_FAIL** | 0 (크래시 2) |
| `SYNTHETIC::assert_positive` | `RAISE:ValueError` | **CAN_FAIL** | 2 |

### 집계

| | 건수 |
|---|---|
| 계열 총 (v3_runner) | **20** |
| `CAN_FAIL` | **17** |
| `CANNOT_FAIL` | **3** |
| `VACUOUS_PASS` | **2** |
| `engine/` | 27 열거 · **0 실증** |

`CANNOT_FAIL` 3건의 내역:

| 함수 | 분류 | R43 시정 대상인가 |
|---|---|---|
| `runner.py::EligibilityChecker.check` | `Protocol` 선언 (본문 `...`) | **아니다** — 선언이지 구현이 아니다 |
| `runner.py::SafetyGuard.assert_action_allowed` | `Protocol` 선언 (본문 `...`) | **아니다** — 집행은 `safety.ActivationSafetyGuard` 가 하고 그쪽은 `CAN_FAIL` |
| `safety.py::RecordingPage.check` | 기록용 test double | **아니다** — 검증하지 않는다고 선언한 fake |

> **구현체이면서 `CANNOT_FAIL` 인 함수는 0건이다.**
> R43 이 겨냥한 "이름이 약속하고 이행하지 않는 함수" 는 이 범위에서 나오지 않았다.

### 시정 대상 — 공허 통과 2건 (`P1`)

`CANNOT_FAIL` 은 아니지만 **`Δ48` 이 실제로 지목한 결함 형태**다. 이름이 검증을
약속하는데 **검사 0회로 성공을 반환하는 경로**가 있다.

| 함수 | 공허 통과 입력 | 반환 |
|---|---|---|
| `evidence.py::verify_retention_manifest` | `manifest={}` (`roots` 키 자체가 없다) | `ok: true`, 모든 증거 목록 빈 상태 |
| `evidence.py::verify_evidence_run` | slot 0개로 봉인된 run (manifest 가 비어 있다) | `ok: true`, `entry_count: 0` |

**이 lane 은 고치지 않는다** — 과업이 목록을 내는 것이고, `v3_runner` 소스는 다른
워커가 쓰는 중이다. 시정 방향만 적는다: "대조할 것이 0개였다" 를 `ok: True` 와 같은
출력으로 내지 않는다. `ok` 를 `None`(판정 불능)으로 내거나 `checked_count` 를 함께
싣고 호출부가 그것을 보게 한다. `Δ39-R32` 의 "부재와 통과가 같은 출력이 되면 안
된다" 가 그대로 적용된다.

### 분류 주기 — 이름 충돌 2건

`safety.py::GuardedPage.check` 와 `safety.py::RecordingPage.check` 는 **검증 함수가
아니다.** playwright `Page.check`(체크박스 켜기)를 감싼 actuation 메서드이며 규칙의
`check` 항목에 이름으로 걸려 들어왔다. **열거에서 빼지 않았다** — 규칙이 잡은 것을
조용히 지우면 규칙과 목록이 어긋난다. 대신 `kind` 로 갈라 적었다.

---

## 6. `R35` 4요소 · `R40` 결속 · `exit` 규약

### `R35` 4요소 — `docs/v3/R43_CHECK_RESULT.json`

| 요소 | 필드 |
|---|---|
| ① 대조 목록 | `controls[].role` · `point_id` · `expected` (+ `briefed_control`) |
| ② 결과 | `controls[].observed` · `passed` · `counts` · `probes[]` |
| ③ 도구 경로 | `tool.module` · `tool.path` · `tool.sha256` · `tool.exit_codes` |
| ④ 선언한 실패 동작의 실증 | `failure_demonstration` → sidecar `docs/v3/R43_FAILURE_DEMO.json` |

산출에는 **시각·난수를 넣지 않는다.** sha 비교가 측정 수단이기 때문이다.

### `exit` 규약 — 격리 사본에서 세 갈래를 전부 관측했다

| exit | 뜻 | 산출 |
|---|---|---|
| `0` | 통과 | **쓴다** (`status=PASS`) |
| `1` | 검사가 돌았고 실패했다 | **쓴다** (감사 흔적) |
| `2` | **검사가 돌지 않았다** | **쓰지 않는다** — 통과로도 실패로도 읽지 마라 |

`exit 1` 과 `exit 2` 를 가르는 이유는 이 세션의 중심 결함이다 — 미실행이 실패와 같은
코드를 쓰면 두 상태가 같은 출력이 된다.

### 실증 사례 5건 — 전부 선언과 일치, 전부 이름 검증 통과

| 사례 | 변형 | 종류 | exit | 산출 |
|---|---|---|---|---|
| `clean` | 없음 | — | 0 | 씀 |
| `data_mutation_leaves_controls_intact` | 산출 JSON 을 손으로 조작 | **데이터** | 0 | 씀 |
| `must_flag_control_disabled_by_source_edit` | `_classify` 의 `CRASH` 분기를 `DECLARED_FAIL` 로 | **소스** | 1 | 씀 |
| `probe_target_renamed_in_source` | `assert_layer_qualified` 의 `def` 이름 변경 + 별칭 유지 | **소스** | 1 | 씀 |
| `target_module_unimportable` | `evidence.py` 문법 파괴 | **소스** | 2 | **안 씀** |

### 사례 이름 검증 (`R36`) — 이름이 실증한 것과 같은가

각 사례는 `asserts` 필드에 **이름이 주장하는 것**을 적고, `name_verified` 가 그 술어를
관측으로 확인한다. **5/5 통과.**

`R36` 이 실제로 걸린 자리가 있다. 첫 판의 사례 이름은
`probe_target_removed_from_source` 였고 함수를 통째로 잘라냈는데, **뒤따르는 상수
블록까지 함께 사라져 모듈이 import 되지 않았다** — 관측된 것은 `exit 2`(미실행)였고
이름이 주장한 `[표류]` 는 **일어나지 않았다.** `name_verified` 가 거짓으로 나왔고
그래서 변형을 `def` 이름만 바꾸는 것으로 좁히고 이름도
`probe_target_renamed_in_source` 로 고쳤다. **`A` 가 저지른 것과 같은 형태를 도구가
자기에게서 잡았다.**

`data_mutation_leaves_controls_intact` 도 이름 그대로다 — **데이터만으로는 대조군을
깰 수 없다.** 산출 JSON 을 어떻게 조작해도 다음 실행이 그것을 덮고 대조는 통과한다.
대조군이 실제로 깨지는 사례는 **검사기 소스를 고치는** 한 건뿐이다.

### `R40` — 결속이 **실제로 무효화하는가**

sidecar 는 실증 당시의 `tool_sha256` 을 싣고, `r43.check` 는 매 실행마다 현재 sha 와
비교해 `valid_for_this_commit` 을 낸다. **항상 참인 필드는 아무것도 말하지 않으므로**
거짓이 되는 것도 실측했다 (`control_failure_demo --binding-only`):

| 사본 | `tool_sha256_at_demo` vs `now` | `valid_for_this_commit` |
|---|---|---|
| `sha_matches` (변형 없음) | 같음 | **`true`** |
| `sha_mutated` (검사기에 주석 한 줄 추가) | 다름 | **`false`** |

→ `binding_is_informative: true`. 두 값이 다 관측되므로 이 필드는 정보를 담는다.

### 격리

실증기는 저장소 밖 임시 디렉터리로 `src/` + `docs/` 를 복사해 **그 사본 안에서만**
변형한다. 저장소의 `v3_runner` 소스는 이 lane 이 한 줄도 고치지 않았다.

---

## 7. 이 lane 이 하지 않은 것

- **`v3_runner` 기존 모듈을 고치지 않았다.** 신규 파일만 추가했다
  (`v3_runner/r43/**`, `tests/test_w5r_r43_check.py`, `docs/v3/R43_*`).
- **`CANNOT_FAIL` / 공허 통과로 나온 함수를 고치지 않았다.** 목록을 내는 것이 과업이다.
- **`engine/` 을 실증하지 않았다.** 27건 열거만. 0건이 아니다.
- **실사이트에 접속하지 않았다.** 모든 probe 는 임시 디렉터리 · fake page · 메모리
  객체만 쓴다. 브라우저를 열지 않는다.

### 배치 상의 주의

도구를 `v3_runner/` 바로 아래가 아니라 `v3_runner/r43/` 하위 패키지에 둔 이유:
`r32_check.sweep_candidates` 가 `v3_runner/*.py` 를 **비재귀**로 훑어
`W5P_TOOLING` 밖의 파일을 전부 R32 후보로 쓸어 담는다. 첫 배치에서 실제로
`r32_check` 가 **내 도구의 매개변수를 R32 미등재 후보로 잡아 실패했다.**
`r32_check.py` 수정은 이 lane 의 금지사항(다른 워커 사용 중)이므로 이쪽이 비켰다.
현재 `r32_check` 는 이 브랜치에서 `status=PASS` · 실패 0건이다.
