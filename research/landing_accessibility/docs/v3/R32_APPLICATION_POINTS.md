# R32 적용 지점 — `v3_runner` 열거

**정본**: `control/v3/V3_0_1_SUCCESSOR_DELTA.md` `Δ39`(R32 세 상태) ·
`Δ40`(R33 네 번째 상태 · 열거 단위 채택 · 대조 명칭 · R34) · `Δ42`(산출 분리 순서).
**검사기**: `src/landing_accessibility/v3_runner/r32_check.py` · `tests/test_w5p_r32_application_points.py`
**레인**: W5P (Claude B) · **이 문서는 목록이다. 코드를 고치지 않았다.**

### 정본 조회 기록

`Δ45` 가 밝힌 대로 A 의 12 커밋이 늦게 push 됐다. 이 lane 의 조회는 이렇게 갈렸다.

| 조회 | 시점 origin | 결과 |
|---|---|---|
| `Δ39` | `f695243` | **39줄** 읽음 — 원문 대조 완료 |
| `Δ40` (1차) | `f695243` | **0줄.** 절이 없었다. 이 문서 초안은 코디네이터가 전달한 인용만으로 썼다 |
| `Δ39`·`Δ40`·`Δ42` (2차) | `9cad171` (재fetch 후) | **39 / 113 / 31줄** 읽음 — 원문 대조 완료 |

2차 대조 결과: 전달된 인용은 **정확했으나 부분이었다.** `Δ40` 의 주된 판정은
**R33 — 모호는 네 번째 상태이고 raise 다** 이고, 전달분에 없던 `R34`(완전성 확인의
두 부분)가 함께 있다. 아래 §1·§8 은 원문 기준으로 다시 썼다.

`git show` 는 절이 없어도 파일을 정상 출력하고 `sed`/`awk` 가 0줄을 낸다 —
**"절이 없다" 와 "절을 못 찾았다" 가 같은 출력이다.** 그래서 줄 수를 함께 적는다.

---

## 1. 판정 단위 — 검사 가능한 술어

`Δ40` ② 가 요구한 대로 **산문이 아니라 술어**로 적는다. 아래 술어를
`r32_check.py::_judge` 가 그대로 구현한다 — 문서의 술어와 검사기의 술어는 같은 것이다.

단위는 **매개변수가 아니라 구조 입력 안의 선택적 키 접근**이다(`Δ40` 채택).
선택적 **매개변수**도 같은 술어로 잰다 — 매개변수는 "키가 하나뿐인 구조 입력"의
특수형이고, 술어를 두 벌 두면 어느 쪽에 걸리느냐가 판정을 바꾼다.

```
site        어떤 함수 F 안에서, 입력 X 의 이름 k 를 읽는 한 자리
            (X[k] · X.get(k) · "k" in X · 또는 X 가 매개변수 그 자체)

ABSENT(site)       k 를 주지 않은 호출
WRONG_SHAPE(site,v) k 를 v 로 준 호출이고, v 가 계약이 정한 형태가 아니다
OUT(site, x)       그 지점을 상태 x 로 **실제 호출**했을 때의 (값 | 예외종류)
                   ─ F 가 여러 코드 경로를 가지면 경로마다 따로 잰다

TOLERATES_ABSENCE(site)  :=  OUT(site, ABSENT) 가 예외가 아니다
CROSSES_CONTRACT(site)   :=  X 를 만드는 쪽이 F 밖이다
                            (다른 모듈 · 다른 lane · 브라우저 JS · 파일)

verdict(site) :=
  R32_VIOLATION   TOLERATES_ABSENCE ∧ ∃v: WRONG_SHAPE(v) ∧
                  OUT(site,v) = OUT(site,ABSENT)          ← 어느 한 경로에서라도
  R32_OK          TOLERATES_ABSENCE ∧ ∀v: WRONG_SHAPE(v) →
                  OUT(site,v) ≠ OUT(site,ABSENT)          ← raise 는 "다른 출력" 이다
  NOT_APPLICABLE  ¬TOLERATES_ABSENCE  ∨  ¬CROSSES_CONTRACT
```

`¬TOLERATES_ABSENCE` 가 `NOT_APPLICABLE` 인 이유: 부재를 거부하는 입력에는 R32 가
말하는 세 상태 중 **'부재' 가 없다.** 그것은 결함이 아니라 `Δ39` ② 가 정한 올바른
모양이다(`scroll_states` 빈 목록 = 계약 위반).

### 네 번째 상태 — 모호 (`Δ40` R33)

`Δ40` 이 R32 의 세 상태에 하나를 더했다: **두 형태 계약이 동시에 만족되어 어느
계약인지 결정되지 않은 상태**(모호). 처리는 형태 위반과 같다 — **raise**.
`WRONG_SHAPE` 안에 모호를 포함시켜 이 술어로 함께 잰다. 실제 사례는 하나이고
(`probe_state` 가 `scroll_states` 와 `raw_features` 를 동시에 가짐) W5N 이 이미
raise 로 구현해 두었다 — `must_not_flag` 오라클의 형태 위반 변형에 그것이 들어 있다.
선행 확인 실측은 §8.

`Δ40` 이 못 박은 것: 우선순위를 선언하고 note 를 남기는 것은 답이 아니다.
R32 의 note 는 **관측된 사실**을 적고, 우선순위 note 는 **도구가 무엇을 측정할지
스스로 고른 것**을 적는다. 뒤는 관측 대상을 바꾼다.

### 이 술어가 앞선 두 열거를 왜 폐기하는가

- 1차 "구조 입력을 받는 공개 함수" 24건 — `CROSSES_CONTRACT` 만 보고
  `TOLERATES_ABSENCE` 를 안 봤다. 내부에서 이미 검증된 값을 받는 자리가 대부분이었다.
- 2차 "선택적 매개변수" 2건 — 단위를 매개변수로 잡아 **`task_control["ax_node"]`
  자체를 놓쳤다.** `task_control` 은 필수 인자이고 선택적인 것은 그 안의 키다.

### `[추론]` B 의 단위에 대한 한 가지 보강 (R16)

B 가 준 단위("구조 입력 안의 선택적 키 접근")를 채택하되 **`OUT` 을 경로별로 잰다**
는 조건을 더한다. 근거는 이 lane 이 실제로 겪은 실패다 — 검사기의 첫 판은
`measure_surface` 를 **DOM 에서 control 을 찾은 경로**로만 재서 `ax_node` 를
`R32_OK` 로 판정했다(`must_flag` 실패). 같은 함수의 **못 찾은 경로**에서는 부재와
형태 위반의 출력이 완전히 같다. 함수 하나에 반환문이 둘이면 지점도 둘이다.

부수로 드러난 것: 찾은 경로에서 `ax_node="NOT_A_DICT"` 는 부재와 갈리기는 하는데
**`dom_ax_divergence=True` 로 갈린다**(`dom_ax_divergence = ax_declared and not
ax_observed`). 형태 위반이 "DOM 에는 있고 AX 에는 없다" 는 **관측 소견**으로
기록된다. 세 상태가 안 갈리는 것보다 나쁘다 — 없는 발견을 만든다.

---

## 2. 대조군 (`Δ40` ① — `must_flag` / `must_not_flag`)

"양성/음성" 을 쓰지 않는다. 이 프로젝트에서 그 말이 이미 두 뜻으로 쓰였다.

| 역할 | 지점 | 요구 | 결과 |
|---|---|---|---|
| **`must_flag`** | `surface.py::measure_surface::ax_node` | 반드시 `R32_VIOLATION` 으로 잡혀야 한다 | **PASS** — 오라클이 `R32_VIOLATION` (DOM 미발견 경로에서 3개 형태 위반 전부 부재와 동일 출력) |
| **`must_not_flag`** | `surface.py::_iter_states::scroll_states` | 잡히면 **안 된다** (W5N `Δ35` 가 고쳤다) | **PASS** — 오라클이 `R32_OK` (4개 형태 위반 전부 `SurfaceProbeShapeError`) |

두 대조는 `r32_check.CONTROLS` 에 있고, `check()` 가 **오라클 결과와 문서 기재를
둘 다** 확인한다. 하나라도 어긋나면 목록이 아니라 방법이 틀린 것이므로 실패시킨다.

**`must_flag` 는 처음에 실패했다.** §1 끝의 경로 문제 때문이다. `Δ40` 이 센
"출력만으로는 구분되지 않는 것을 대조군이 잡은" 사례에 이것이 하나 더해진다 —
대조군을 걸지 않았으면 이 목록은 `ax_node` 를 `R32_OK` 로 싣고 나갔을 것이고,
그것은 `Δ39` 를 낳은 바로 그 사례를 부정하는 목록이 됐을 것이다.

---

### `R34` — 이 목록의 완전성은 이 문서가 닫지 않는다

`Δ40` R34: 완전성 확인은 (a) **단위 안**의 열거 일치와 (b) **단위 밖** 반례 탐색을
둘 다 가져야 한다. 두 평면이 같은 단위를 쓰는 것은 옳지만 — 모집단이 다르면 비교가
성립하지 않는다 — **단위가 틀리면 두 평면이 같이 틀린다.**

이 lane 은 (b) 를 자기부과해 수행했고, `Δ42` 에 따라 **그 기재를 이 문서에 넣지
않았다.** C 의 (b) 가 이 문서를 읽기 전에 수행되어야 독립이기 때문이다. 기재는
저장소 밖에 있고 공개 시점은 코디네이터가 정한다.

---

## 3. 훑은 범위 — 무엇의 전수인가

**"전수" 라고 쓰지 않는다.** 훑은 것은 다음의 전수다.

| 범위 | 포함 | 방법 |
|---|---|---|
| `v3_runner/*.py` 14개 파일 | **모듈 공개 함수·메서드**(이름이 `_` 로 시작하지 않는 것)가 자기 매개변수에서 읽는 문자열 키, 그리고 그 매개변수를 **그대로 넘겨받은 같은 모듈 private 헬퍼(1-hop)** 가 읽는 키 | `r32_check.sweep_candidates()` — AST |
| 위 + 손으로 추가한 3건 | loop 변수로 읽는 키 2건, 매핑 전체 형태 1건 | 코드 읽기 |

**밖에 있는 것 (보지 않았다)**

- `engine/` 전부 (`l0_probe.js` · `l0_collector.py` · `l1_engine.py` · `firewall.py` …)
- `tests/` · `fixtures/`
- **2-hop 이상**: 공개 함수 → private A → private B 로 흘러가는 키
- **loop 변수·지역 변수를 거쳐 읽는 키** — sweep 이 못 잡는다. 손으로 2건 찾았고
  이것이 전부라고 주장하지 않는다
- **dataclass 필드 접근**(`interrupt.box`, `contract.forbidden_actions` …) — 형태가
  타입으로 실려 오는 자리라 단위 밖으로 두었다
- 동적으로 조립되는 매핑(`**kwargs`, `dict()` 호출)

`Δ39` 가 정한 대로 **이 목록의 완전성은 C 가 자기 경로로 독립 확인한다.** 위 표는
"B 가 무엇을 봤는가" 이지 "이것이 전부다" 가 아니다.

---

## 4. 집계

| 판정 | 건수 |
|---|---|
| `R32_VIOLATION` | **30** |
| `R32_OK` | 18 |
| `NOT_APPLICABLE` | 19 |
| **합계** | **67** |

| 판정근거 | 건수 | 뜻 |
|---|---|---|
| `BEHAVIORAL` | 35 | 검사기가 그 지점을 **부재/형태 위반으로 실제 호출**해 기계가 판정했다 |
| `READ` | 32 | offline 순수 호출이 안 되는 지점(driver·전체 manifest 필요). **사람이 코드를 읽고 적었다** |

`READ` 32건은 기계 검증을 받지 않았다. 그중 `R32_VIOLATION` 7건은 전부
`X or DEFAULT` / `and X.get(k)` 라는 **같은 패턴**이고, 그 패턴은
`discovery.py::discover_task_candidates::(PARAM:policy)` 에서 오라클로 확인했다.

---

## 5. `R32_VIOLATION` 상세

각 항목: **위치 · 입력의 출처 · 현재 동작 · 부재와 구분되는가**.

### 5.1 `surface.py` — `task_control` 의 선택적 키 4건

`task_control` 은 필수 인자이고, 그 안의 `ax_node`/`nav_container_type`/
`nav_container_chain`/`computed_position` 이 선택적 키다.

- **출처**: 모듈 경계를 넘는다. `ax_node` 는 W5I `ax_join.task_control_ax_field()`
  가 만들고, 나머지는 task-entry binding lane 이 만든다. `measure_surface` 는
  `v3_runner` 안에 in-repo 호출자가 없다 — 순수 lane 경계 함수다.
- **현재 동작·구분 여부**

| 키 | 부재 | 형태 위반 | 구분되는가 |
|---|---|---|---|
| `ax_node` | `accessible_name=None` + note `AX_NODE_ABSENT` | **DOM 미발견 경로: 완전히 같은 출력.** DOM 발견 경로: `dom_ax_divergence=True` 로 갈리는데 그것이 **없는 관측 소견**이다 | ✗ |
| `nav_container_type` | `innermost=None` | `isinstance(declared, str)` 실패 → `None` | ✗ |
| `nav_container_chain` | `chain=()` | `isinstance(raw_chain, (list, tuple))` 실패 → `()`. list 안에 str 아닌 원소가 있으면 **그 원소만 조용히 버린다** | ✗ |
| `computed_position` | `FLOATING` 판정 안 함 | `isinstance(..., str)` 실패 → 역시 판정 안 함 | ✗ |

`ax_node` 는 `Δ39` 를 낳은 사례 그대로다. 나머지 3건은 **같은 함수 안 같은 모양**이고
`Δ39` 가 "특정 함수가 아니라 모든 선택적 입력" 이라고 한 이유가 이것이다.

### 5.2 `ax_join.py` — 4건

| 지점 | 부재 | 형태 위반 | 왜 문제인가 |
|---|---|---|---|
| `probe_selectors::raw_features` | 봉투가 아니다 → `probe` 자체를 raw_features 로 본다(문서화된 이중 형태 허용) | `raw_features` 가 Mapping 이 아니면 **같은 분기로 떨어진다** | `_iter_states` 가 `Δ35` 로 고친 봉투 모호성이 **여기 그대로 남아 있다**. 같은 probe 산출물을 두 모듈이 다르게 다룬다 |
| `probe_selectors::<DEFAULT_SELECTOR_FEATURES>` | 그 feature 없음 → skip | `isinstance(rows, list)` 실패 → 역시 skip | selector 가 조인 대상에서 조용히 빠진다 |
| `selector_ax_index::entries` | `{}` | `entries` 가 list 가 아니면 키를 순회해 전부 걸러진다 → `{}` | "조인 결과가 없다" 와 "payload 형태가 틀렸다" 가 같다 |
| `selector_ax_index::ax_node` | `out[sel] = None` | `isinstance(node, Mapping)` 실패 → `None` | **이 함수의 docstring 이 스스로 밝힌 구분이 여기서 무너진다** — "조인을 시도했으나 실패한 것은 값을 `None` 으로 줘야 그 구분이 유지된다". 형태 위반도 같은 `None` 이 되어 하류 `surface.py` 의 `dom_ax_divergence` 로 흘러간다 |

### 5.3 `discovery.py` — 3건

- `discover_task_candidates::primary_action_candidates` — `list(probe_state.get(...) or [])`.
  falsy 형태 위반(`{}`·`""`·`0`)이 부재와 똑같이 후보 0건이 된다.
  **`Δ39` ② 가 `scroll_states` 에 대해 판정한 것과 같은 형태다** — 후보 0건은
  "봤는데 없었다" 로 읽히지만 실제로는 "형태가 틀려 볼 수 없었다" 다.
- `discover_task_candidates::(PARAM:policy)` · `run_task_aware_scout::(PARAM:policy)` ·
  `::(PARAM:budget)` — `X or DEFAULT`. falsy 형태 위반이 기본값으로 접힌다.
  `is not None` 이면 안 접힌다(`registry.py` 가 그렇게 한다).

### 5.4 `safety.py` — 4건 · **fail-open 방향이다**

| 지점 | 무엇이 겹치는가 |
|---|---|
| `resolve_forbidden_actions::(PARAM:contract)` | 키 이름이 `_CONTRACT_FORBIDDEN_KEYS`(`forbidden_actions`/`forbidden_action_set`) 밖인 계약, 문자열 계약, 숫자 계약이 **전부 `contract=None` 과 같은 결과**를 낸다. `UNIVERSAL_FORBIDDEN_ACTIONS` 는 유지되므로 무한 fail-open 은 아니지만 **target 이 추가로 선언한 금지가 조용히 사라지고** `contract_declared=∅` 로 "계약이 아무것도 선언 안 했다" 라고 기록된다 |
| `classify_auth_boundary::(MAPPING:candidate)` | 매핑 **전체**의 형태를 검증하지 않는다. `_PLANNED_ACTION_FIELD_MAP` 번역을 빠뜨린 후보(`control_visible_text=...`)가 **빈 후보 `{}` 와 완전히 같은 판정**을 받는다. 이 결함 경로는 `_PLANNED_ACTION_FIELD_MAP` 의 주석이 이미 이름 붙여 놓은 바로 그것이다 — "이름만 맞춘 배선이 fail-open 이 되는 정확한 경로" |
| `_detect_forbidden_action::href` · `::url` | `str(candidate.get("href") or candidate.get("url") or "")`. falsy 형태 위반이 부재와 같이 `""` 가 되어 외부앱 스킴 검사가 아예 돌지 않는다 |
| `_observe::selector` | `if candidate.get("selector")` — falsy 형태 위반(`{}`·`[]`)이 부재와 같이 `selector=None`. `selector` 가 `None` 이면 `_denied_selectors` 등록도 `_known` 기록도 건너뛴다 |
| `observe::form_id` *(READ)* | falsy 형태 위반은 부재와 같이 미등록. truthy 형태 위반은 `str()` 로 접혀 **쓰레기 form id** 가 자격정보 폼 집합에 들어간다 |

### 5.5 `session.py` — 7건 · 브라우저 JS → Python 경계

`_CONTROL_FACTS_JS` 는 `found: true` 일 때 `type`·`autocomplete`·`password_scope`·
`tag`·`role`·`has_datalist` 를 **언제나** 낸다(값이 `null` 일 수는 있다).
즉 **키 부재는 계약에 없는 상태인데 `.get()` 이 그것을 만들어 낸다.**

- `is_credential_field::{type, autocomplete, password_scope}` — `str(facts.get(k) or "")`
  로 접히므로 형태 위반이 `null`(= "그 속성 없음" 이라는 **정당한 관측**)과 같은
  `False` 를 낸다. **자격정보 탐지가 fail-open 되는 방향이다.**
- `observe_input_mode::{tag, role, type, has_datalist}` — 같은 모양. 형태 위반이
  "구조 신호가 하나도 없다"(`None`)와 같아진다.

in-repo 생산자(`_CONTROL_FACTS_JS`)는 올바른 형태를 낸다. 두 함수는 `__all__` 공개
API 라 임의의 `Mapping` 을 받는 계약 경계이고, 이 판정은 그 계약에 대한 것이다.

### 5.6 `evidence.py` — 1건 · **빈 결과가 통과로 나온다**

`verify_retention_manifest::roots` — `manifest.get("roots", [])`.
`roots` 가 dict/문자열이면 순회가 0회라 부재와 **완전히 같은 결과**가 나오고,
그 결과는 `{"verified": [], "mismatched": [], "missing": [], "ok": True}` 다.
**아무것도 검증하지 않고 `ok: True` 를 낸다.**
`build_retention_manifest` 는 `roots` 를 항상 낸다 — 부재 자체가 계약 밖이다.

### 5.7 `runner.py` — 4건 *(READ)*

`run`/`replay` 의 `service_id`·`task_id` — `service_id or contract.target_id`.
falsy 형태 위반이 계약값으로 접혀 `ObservationKey` 에 실린다. 관측 identity 를
정하는 자리라 조용한 대체가 특히 나쁘다.

---

## 6. `R32_OK` 18건 — 무엇이 올바른 모양인가

세 갈래가 있다.

1. **형태 검증 후 raise** — `surface.py::_iter_states::scroll_states`
   (`_require_probe_envelope`, W5N `Δ35`). `Δ39` 가 요구한 정확한 모양이고
   이 문서의 `must_not_flag` 다.
2. **`is not None` + 생성자가 raise** — `registry.py` 의 경로 매개변수 4건,
   `safety.py::load_fixture_matrix::(PARAM:root)`, `ax_join` 의
   `full_ax_backend_ids` 2건, `surface.py::normalize_label::(PARAM:text)`.
   `or` 대신 `is not None` 을 쓰면 falsy 형태 위반이 부재로 접히지 않고,
   `Path()`/`set()`/`unicodedata.normalize()` 가 형태 위반을 스스로 거부한다.
3. **형태 위반을 원문 그대로 실어 보낸다** — `safety.py::_observe` 의
   `visible_text`·`accessible_name`·`hittable`·`enabled`·`bbox`,
   `evidence.py::verify_denominator_chain::family_id`. 값이 출력에 남으므로
   부재(`None`)와 갈린다. raise 는 아니지만 **은폐는 아니다.**

`registry.py` 는 `Δ39` 를 이미 지키는 모듈이다 — `entry["forbidden_actions"]` 는
`KeyError`, `replacement_reserve` 는 `isinstance` 검사 후 `RegistryParseError`,
선택적 키는 `.get(k, default)` 로 두되 **값을 즉시 폐쇄 어휘와 대조해 raise** 한다.

---

## 7. `NOT_APPLICABLE` 19건

| 사유 | 건수 | 예 |
|---|---|---|
| 계약 경계가 아니다 — 같은 프로세스 DI·테스트 주입 이음매 | 15 | `ax_join` 의 `package_root` 7건(모듈이 `_package_root()` 로 스스로 안다), `safety` 의 callable 주입 4건, `RecordingPage` 테스트 더블 2건, `CDPLike` Protocol 선언 1건 |
| 부재를 거부한다 — 세 상태 중 '부재' 가 계약에 없다 | 4 | `surface.py::measure_surface::selector`, `runner.py::verify_path_manifest_hash::(PARAM:declared_sha256)`, `runner.py::replay::(PARAM:declared_sha256)`, `evidence.py::verify_denominator_chain::replacement_ledger_sha256`, `terminal.py::validate_status_reason::(PARAM:note)` |

---

## 8. R33 선행 확인 — `scroll_states` 와 `raw_features` 동시 보유 실측

`Δ40/R33`: 한 `probe_state` 가 두 키를 **모두** 가지면 raise(네 번째 상태 '모호').
W5N 이 이미 그렇게 구현했다(`surface.py:437-443`). 빠진 것은 선행 확인이다.
검사기 함수: `r32_check.r33_envelope_scan()`.

**방법** — `research/landing_accessibility/` 와 `tests/` 아래 모든 `.json` 의
매핑 전수 + 모든 `.py` 의 **dict 리터럴** 전수에서 두 키의 동거를 센다.

**① 두 키를 함께 넘기는 호출자·fixture·테스트 — 1건**

| 위치 | 무엇인가 |
|---|---|
| `tests/test_w5c_surface_measure.py:600` `both_forms_at_once` | `_SHAPE_VIOLATIONS` 파라미터 목록의 한 항목. **`SurfaceProbeShapeError` 가 나는 것을 단언하는 부정 테스트**다 — 그 형태로 동작하기를 기대하는 호출자가 아니다 |

**② 의도 기록 후 시정 — 해당 없음.** ① 의 유일한 건이 raise 를 기대하는 테스트이므로
깨질 호출자가 없다. **production 호출부·fixture 에서 0건이다.**

**③ '없음' 의 대조군** — 같은 검색이 한쪽 키만 가진 봉투를 잡아내는지:

| 분류 | 건수 |
|---|---|
| 두 키 동시 보유 | **1** (위 부정 테스트) |
| `scroll_states` 만 | **14** (`fixtures/w5c_surface/scroll_visibility_cases.json` 5건 + 검사기·테스트) |
| `raw_features` 만 | **116** (`fixtures/w5c_surface/*.json` 다수) |

검색은 동작한다 — 130건을 잡았다. 그 검색이 동시 보유를 1건만 찾았고 그 1건이
부정 테스트다. **범위 한계**: `.py` 는 dict **리터럴**만 본다. 런타임에 조립되는
봉투(`d = {}; d["scroll_states"] = ...`)는 잡지 못한다. REAL_TARGET 누적 0건이라
관측치 오염은 없다.

**결론**: 깨질 호출자가 없으므로 W5N 의 raise 구현은 그대로 두면 된다.
`Δ40` 이 둔 유일한 예외 — "계약이 두 키의 공존을 제3의 형태로 **명시적으로** 정의한
경우" — 는 현재 v3 계약에 없다. 이 lane 은 그것을 만들지 않았다
(`Δ40`: "필요하면 `R16` 으로 올려라 — 구현으로 만들지 마라").

---

## 9. 검사기가 하는 일

`python -m landing_accessibility.v3_runner.r32_check` (또는
`tests/test_w5p_r32_application_points.py`).

| 층 | 하는 일 | 목록이 어긋나면 |
|---|---|---|
| 1. 행동 오라클 | 35개 지점을 부재/형태 위반으로 **실제 호출**해 §1 술어를 계산 | 문서 판정 ≠ 기계 판정 → 실패 |
| 2. 구조 검사 | 67행 전부의 파일·함수·키 리터럴(또는 매개변수)이 **실재하는지** AST 로 확인 | 함수명·키가 바뀌거나 사라지면 실패 |
| 3. 표류 검사 | AST sweep 을 **문서와 무관하게 다시** 돌려 후보를 재생성 | 코드에 있는데 목록에 없으면 실패 |
| 대조군 | `must_flag`/`must_not_flag` 를 오라클 결과와 문서 기재 양쪽에서 확인 | 어긋나면 실패 (목록이 아니라 방법이 틀린 것) |

---

## 10. 확신하지 못하는 것

1. **완전성.** §3 의 범위 밖(2-hop·loop 변수·`engine/`)에 지점이 더 있다.
   손으로 3건을 주웠고 그것이 그 계열의 전부라고 주장하지 않는다.
2. **`READ` 32건.** 기계 검증을 받지 않았다. 특히 `runner.py` 4건은 driver 없이
   호출할 수 없어 `or` 패턴 동형성으로만 판정했다.
3. **`Δ40` 원문 미대조** (문서 머리 참조).
4. **`session.py` 7건의 실효성.** in-repo 생산자는 올바른 형태를 낸다. 계약 경계로서
   위반이지만 현재 배선에서 실제로 발화하는 경로는 확인하지 못했다.
5. **dataclass 필드를 단위 밖에 둔 것.** 타입이 형태를 싣고 온다는 전제인데
   런타임에는 강제되지 않는다. 다른 단위를 쓰면 이 목록이 늘어난다.

---

## 부록 A — 목록 (기계 판독용)

이 표가 검사기와의 계약이다. `point_id` 는 `파일::키를 실제로 읽는 함수::키` 이고
`(PARAM:name)` 은 매개변수, `(MAPPING:name)` 은 매핑 전체, `<...>` 는 키 묶음이다.
`⟨+수동⟩` 은 AST sweep 이 못 잡아 손으로 추가한 행이다.

| point_id | 판정 | 판정근거 | 근거 |
|---|---|---|---|
| `ax_join.py::build_ax_join_payload::(PARAM:full_ax_backend_ids)` | R32_OK | READ | `is not None` 으로 갈린다. 형태 위반은 `list()` 에서 `TypeError`. |
| `ax_join.py::build_ax_join_payload::(PARAM:package_root)` | NOT_APPLICABLE | READ | 계약 경계가 아니다 — 이 모듈이 `_package_root()` 로 스스로 안다. 테스트 주입 이음매. |
| `ax_join.py::capture_stack::(PARAM:package_root)` | NOT_APPLICABLE | READ | 같음 (테스트 주입 이음매). |
| `ax_join.py::capture_stack_notes::(PARAM:package_root)` | NOT_APPLICABLE | READ | 같음. |
| `ax_join.py::collect_ax_join::(PARAM:package_root)` | NOT_APPLICABLE | READ | 같음. |
| `ax_join.py::collector_provenance::(PARAM:package_root)` | NOT_APPLICABLE | READ | 같음. |
| `ax_join.py::collector_provenance_notes::(PARAM:package_root)` | NOT_APPLICABLE | READ | 같음. |
| `ax_join.py::collector_sha256::(PARAM:package_root)` | NOT_APPLICABLE | READ | 같음. |
| `ax_join.py::join_resolutions::(PARAM:full_ax_backend_ids)` | R32_OK | READ | `is not None` 으로 갈린다. 형태 위반은 `set()` 에서 `TypeError`. |
| `ax_join.py::probe_selectors::<DEFAULT_SELECTOR_FEATURES>` | R32_VIOLATION | BEHAVIORAL | [단일] m0: 부재와 **동일 출력**; [단일] m1: 부재와 **동일 출력** ⟨+수동⟩ |
| `ax_join.py::probe_selectors::raw_features` | R32_VIOLATION | BEHAVIORAL | [단일] m0: 부재와 **동일 출력**; [단일] m1: 부재와 **동일 출력** |
| `ax_join.py::selector_ax_index::ax_node` | R32_VIOLATION | BEHAVIORAL | [단일] m0: 부재와 **동일 출력**; [단일] m1: 부재와 **동일 출력** ⟨+수동⟩ |
| `ax_join.py::selector_ax_index::entries` | R32_VIOLATION | BEHAVIORAL | [단일] m0: 부재와 **동일 출력**; [단일] m1: 부재와 **동일 출력** |
| `ax_join.py::send::(PARAM:params)` | NOT_APPLICABLE | READ | `CDPLike` **Protocol 선언**이다. 구현이 아니라 Playwright `CDPSession` 시그니처의 사본. |
| `discovery.py::discover_task_candidates::(PARAM:policy)` | R32_VIOLATION | BEHAVIORAL | [단일] m0: 부재와 **동일 출력**; [단일] m1: 부재와 **동일 출력** |
| `discovery.py::discover_task_candidates::primary_action_candidates` | R32_VIOLATION | BEHAVIORAL | [단일] m0: 부재와 **동일 출력**; [단일] m1: 부재와 **동일 출력**; [단일] m2: 부재와 **동일 출력** |
| `discovery.py::run_task_aware_scout::(PARAM:budget)` | R32_VIOLATION | READ | `budget or ScoutBudget()` — falsy 형태 위반이 부재와 같이 기본값으로 접힌다. `discover_task_candidates::(PARAM:policy)` 와 **같은 패턴**이고 그쪽은 오라클이 확인했다. |
| `discovery.py::run_task_aware_scout::(PARAM:policy)` | R32_VIOLATION | READ | `policy or MIN4_POLICY` — 위와 같음. |
| `evidence.py::verify_denominator_chain::family_id` | R32_OK | READ | 읽어서 그대로 실어 보낸다. 형태 위반이 출력에 원문으로 남아 부재(`None`)와 갈린다. |
| `evidence.py::verify_denominator_chain::replacement_ledger_sha256` | NOT_APPLICABLE | READ | 부재를 거부한다 — 부재도 `DenominatorError`. 세 상태 중 '부재' 가 계약에 없다. |
| `evidence.py::verify_retention_manifest::roots` | R32_VIOLATION | BEHAVIORAL | [단일] m0: 부재와 **동일 출력**; [단일] m1: 부재와 **동일 출력** |
| `obstruction.py::measure_task_obstruction::(PARAM:task_control_bbox)` | R32_OK | BEHAVIORAL | [단일] m0: raise AttributeError; [단일] m1: raise AttributeError |
| `registry.py::load_task_registry::(PARAM:manifest_path)` | R32_OK | READ | `resolve_manifest_path` 이 `is not None` 으로 갈리고 형태 위반은 `Path()` 에서 `TypeError`. |
| `registry.py::load_task_registry::(PARAM:registry_path)` | R32_OK | READ | `resolve_ssot_dir` — 같음. |
| `registry.py::resolve_manifest_path::(PARAM:manifest_path)` | R32_OK | READ | `Path(manifest_path) if manifest_path is not None else DEFAULT_MANIFEST_PATH`. |
| `registry.py::resolve_ssot_dir::(PARAM:registry_path)` | R32_OK | READ | 같음. |
| `runner.py::replay::(PARAM:declared_sha256)` | NOT_APPLICABLE | READ | 부재를 거부한다 (`verify_path_manifest_hash` 가 `not declared_sha256` 에서 raise). |
| `runner.py::replay::(PARAM:service_id)` | R32_VIOLATION | READ | `service_id or contract.target_id` — falsy 형태 위반(`{}`·`0`·빈 문자열)이 부재와 같이 계약값으로 접힌다. |
| `runner.py::replay::(PARAM:task_id)` | R32_VIOLATION | READ | `task_id or contract.frozen_task` — 같음. |
| `runner.py::run::(PARAM:service_id)` | R32_VIOLATION | READ | 같음. |
| `runner.py::run::(PARAM:task_id)` | R32_VIOLATION | READ | 같음. |
| `runner.py::verify_path_manifest_hash::(PARAM:declared_sha256)` | NOT_APPLICABLE | BEHAVIORAL | 부재를 거부한다 — [단일] 부재 → raise PathManifestHashMismatchError |
| `safety.py::_detect_forbidden_action::href` | R32_VIOLATION | BEHAVIORAL | [단일] m0: 부재와 **동일 출력**; [단일] m1: 부재와 **동일 출력** |
| `safety.py::_detect_forbidden_action::url` | R32_VIOLATION | BEHAVIORAL | [단일] m0: 부재와 **동일 출력**; [단일] m1: 부재와 **동일 출력** |
| `safety.py::_observe::accessible_name` | R32_OK | BEHAVIORAL | [단일] m0: 다른 값; [단일] m1: 다른 값 |
| `safety.py::_observe::bbox` | R32_OK | BEHAVIORAL | [단일] m0: 다른 값; [단일] m1: 다른 값 |
| `safety.py::_observe::enabled` | R32_OK | BEHAVIORAL | [단일] m0: 다른 값; [단일] m1: 다른 값 |
| `safety.py::_observe::hittable` | R32_OK | BEHAVIORAL | [단일] m0: 다른 값; [단일] m1: 다른 값 |
| `safety.py::_observe::selector` | R32_VIOLATION | BEHAVIORAL | [단일] m0: 부재와 **동일 출력**; [단일] m1: 부재와 **동일 출력** |
| `safety.py::_observe::visible_text` | R32_OK | BEHAVIORAL | [단일] m0: 다른 값; [단일] m1: 다른 값 |
| `safety.py::classify_auth_boundary::(MAPPING:candidate)` | R32_VIOLATION | BEHAVIORAL | [단일] m0: 부재와 **동일 출력**; [단일] m1: 부재와 **동일 출력** ⟨+수동⟩ |
| `safety.py::count::(PARAM:selector_contains)` | NOT_APPLICABLE | READ | `RecordingPage` 테스트 더블의 조회 helper 다. 관측 입력이 아니다. |
| `safety.py::guard_page::(PARAM:resolve)` | NOT_APPLICABLE | READ | callable 주입(DI) 이음매다. 관측값이 아니라 동작 주입. |
| `safety.py::launch::(PARAM:launch_fn)` | NOT_APPLICABLE | READ | 같음. |
| `safety.py::load_fixture_matrix::(PARAM:root)` | R32_OK | READ | `Path(root) if root is not None else default_v3_fixture_root()`. 형태 위반은 `Path()` 에서 raise. |
| `safety.py::observe::form_id` | R32_VIOLATION | READ | `and candidate.get("form_id")` — falsy 형태 위반은 부재와 같이 미등록, truthy 형태 위반은 `str()` 로 접혀 **쓰레기 form id** 가 자격정보 폼 집합에 들어간다. |
| `safety.py::resolve_forbidden_actions::(PARAM:contract)` | R32_VIOLATION | BEHAVIORAL | [단일] m0: 부재와 **동일 출력**; [단일] m1: 부재와 **동일 출력**; [단일] m2: 부재와 **동일 출력** |
| `safety.py::run_fixture_safety_regression::(PARAM:contract_for)` | NOT_APPLICABLE | READ | 같음. |
| `safety.py::run_fixture_safety_regression::(PARAM:run_case)` | NOT_APPLICABLE | READ | 같음. |
| `safety.py::select_option::(PARAM:value)` | NOT_APPLICABLE | READ | `RecordingPage` 테스트 더블이 Playwright 시그니처를 모사한 것. |
| `session.py::is_credential_field::autocomplete` | R32_VIOLATION | BEHAVIORAL | [단일] m0: 부재와 **동일 출력** |
| `session.py::is_credential_field::password_scope` | R32_VIOLATION | BEHAVIORAL | [단일] m0: 부재와 **동일 출력**; [단일] m1: 부재와 **동일 출력** |
| `session.py::is_credential_field::type` | R32_VIOLATION | BEHAVIORAL | [단일] m0: 부재와 **동일 출력**; [단일] m1: 부재와 **동일 출력** |
| `session.py::observe_input_mode::has_datalist` | R32_VIOLATION | BEHAVIORAL | [단일] m0: 부재와 **동일 출력**; [단일] m1: 부재와 **동일 출력** |
| `session.py::observe_input_mode::role` | R32_VIOLATION | BEHAVIORAL | [단일] m0: 부재와 **동일 출력**; [단일] m1: 부재와 **동일 출력** |
| `session.py::observe_input_mode::tag` | R32_VIOLATION | BEHAVIORAL | [단일] m0: 부재와 **동일 출력**; [단일] m1: 부재와 **동일 출력** |
| `session.py::observe_input_mode::type` | R32_VIOLATION | BEHAVIORAL | [단일] m0: 부재와 **동일 출력** |
| `surface.py::_iter_states::scroll_states` | R32_OK | BEHAVIORAL | [단일] m0: raise SurfaceProbeShapeError; [단일] m1: raise SurfaceProbeShapeError; [단일] m2: raise SurfaceProbeShapeError; [단일] m3: raise SurfaceProbeShapeError |
| `surface.py::_resolve_nav_container::nav_container_chain` | R32_VIOLATION | BEHAVIORAL | [DOM 발견] m0: 부재와 **동일 출력**; [DOM 발견] m1: 부재와 **동일 출력**; [DOM 발견] m2: 부재와 **동일 출력**; [DOM 미발견] m0: 부재와 **동일 출력**; [DOM 미발견] m1: 부재와 **동일 출력**; [DOM 미발견] m2: 부재와 **동일 출력** |
| `surface.py::_resolve_nav_container::nav_container_type` | R32_VIOLATION | BEHAVIORAL | [DOM 발견] m0: 부재와 **동일 출력**; [DOM 발견] m1: 부재와 **동일 출력**; [DOM 발견] m2: 부재와 **동일 출력**; [DOM 미발견] m0: 부재와 **동일 출력**; [DOM 미발견] m1: 부재와 **동일 출력**; [DOM 미발견] m2: 부재와 **동일 출력** |
| `surface.py::measure_surface::ax_node` | R32_VIOLATION | BEHAVIORAL | [DOM 미발견] m0: 부재와 **동일 출력**; [DOM 미발견] m1: 부재와 **동일 출력**; [DOM 미발견] m2: 부재와 **동일 출력**; [DOM 발견] m0: 다른 값; [DOM 발견] m1: 다른 값; [DOM 발견] m2: 다른 값 |
| `surface.py::measure_surface::computed_position` | R32_VIOLATION | BEHAVIORAL | [DOM 발견] m0: 부재와 **동일 출력**; [DOM 발견] m1: 부재와 **동일 출력**; [DOM 발견] m2: 부재와 **동일 출력**; [DOM 미발견] m0: 부재와 **동일 출력**; [DOM 미발견] m1: 부재와 **동일 출력**; [DOM 미발견] m2: 부재와 **동일 출력** |
| `surface.py::measure_surface::selector` | NOT_APPLICABLE | READ | 필수 키다 — 부재·형태 위반 모두 `ValueError`. 세 상태 중 '부재' 가 계약에 없다. |
| `surface.py::normalize_label::(PARAM:text)` | R32_OK | BEHAVIORAL | [단일] m0: raise TypeError; [단일] m1: raise TypeError |
| `terminal.py::validate_status_reason::(PARAM:endpoint_status)` | R32_OK | BEHAVIORAL | [단일] m0: raise TypeError; [단일] m1: raise KeyError; [단일] m2: raise KeyError |
| `terminal.py::validate_status_reason::(PARAM:note)` | NOT_APPLICABLE | BEHAVIORAL | 부재를 거부한다 — [단일] 부재 → raise TerminalReasonNoteError |
| `terminal.py::validate_status_reason::(PARAM:terminal_reason)` | R32_OK | BEHAVIORAL | [단일] m0: raise AttributeError; [단일] m1: raise AttributeError |
