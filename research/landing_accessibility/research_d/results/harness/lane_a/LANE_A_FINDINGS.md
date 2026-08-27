# Lane A — Auth timing / Obstruction 하네스 결과

- **verdict**: `READY_WITH_AMBIGUITY`
- base SHA `7448184a811f5d7d8772f21488bb75418fde3313` (`claude-d/research-sandbox-v21`)
- SSOT `/home/sieg/projects-wsl/ProjectFinal/SSOTV3`, MANIFEST self-sha256 `1735c956…f2f72e0a` (실행 시점 재계산 일치)
- 산출: `tools/v3_harness/lane_a_auth_obstruction.py`, `results/harness/lane_a/LANE_A_HARNESS.json`
- **MAIN50 실측 데이터 없음.** 아래 모든 통과는 이 파일 안에서 생성된 합성 fixture 에 대한 통과다. 실측 타당성 증거가 아니다.

---

## 1. 구현한 것

### auth_gate_stage
codebook 도메인 `NONE / BEFORE_TASK_DISCOVERY / AFTER_TASK_SELECT / AT_ENDPOINT` 그대로.

판정 원천은 `fact_flow_step.auth_gate_detected`, `.action_token`, `.endpoint_signal_detected` 뿐이다.
`landing_login_control_present` 계열 필드는 `project_auth_inputs()` 가 **구조적으로 잘라내고**,
그 필드가 분류기에 도달하면 `GUARD_BREACH` defect 를 낸다.
→ 00 §6 / 03 §7 / 10 Glossary 의 "로그인 버튼 단순 존재는 AUTH_GATE 가 아니다" 를 문서 주석이 아니라 코드 경로로 강제했다.

`AUTH_GATE` token 과 step flag 가 어긋나면 한쪽을 조용히 고르지 않고 `AUTH_TOKEN_FLAG_MISMATCH` 로 판정을 보류한다.
step 증거가 없으면 `NONE` 으로 흘리지 않는다 — `NONE` 은 "인증 게이트 없음" 이라는 실측 주장이기 때문이다.
codebook 에 판정불능 값이 없어 하네스 내부 sentinel 을 쓰고 카운터 분모에서 분리했다(AMB-A4).

### fact_task_obstruction
`interrupt_type / overlay_coverage / task_control_occlusion / dismiss_control_exists / dismiss_control_visible /
dismiss_control_accessible_name / dismiss_required_for_task / dismiss_succeeded` 를 읽고,
`forced_dismissal_count` 는 run grain 으로 읽는다.

- **primary = `task_control_occlusion`**, `overlay_coverage` 는 보조 설명값으로만 pass-through 하며 어떤 판정에도 쓰지 않는다.
- geometry 로부터 occlusion/modal 을 재도출하는 경로는 `derive_occlusion_from_geometry()` 가 **명시적으로 거부**한다
  (`REFUSED_GEOMETRY_ONLY_DERIVATION`, 03 §9).

### 승계한 세 구분 (수치가 아니라 구분만)
| 상태 | 값 | 조건 |
|---|---|---|
| 닫을 대상이 없음 | `NO_DISMISS_TARGET` | `dismiss_control_exists=False` |
| 닫기를 시도했으나 실패 | `DISMISS_FAILED` | `exists=True` AND `dismiss_succeeded=False` |
| 닫기 성공 | `DISMISS_SUCCEEDED` | `exists=True` AND `dismiss_succeeded=True` |

여기에 뭉개지 않기 위한 3개를 더 분리 보존한다:
`DISMISS_OUTCOME_UNRECORDED`(exists=True, succeeded=null) / `INCONSISTENT_DISMISS_RECORD`(exists=False인데 succeeded=True) /
`DISMISS_EXISTENCE_UNKNOWN`(exists=null).
`exists=True` 인데 `visible=False` 인 경우는 "무대상" 과 별개 상태로 note 에 남긴다.

### 세 축 라벨링
모든 카운터는 `ThreeAxisCounter` 로만 만들어진다. **(1) 단위 (2) 모집단 (3) 원천 필드** 중 하나라도 없으면
`__post_init__` 이 `ThreeAxisViolation` 을 던져 객체 생성이 실패하고, 따라서 비율도 존재할 수 없다.
조건부 모집단은 population 문자열에 `conditional_on:` 으로 조건을 반드시 적어야 통과한다.

핵심: `dismiss_success_rate` 의 분모는 **전체 interrupt 가 아니라** `exists=True AND succeeded is not null` 인 조건부 모집단이다.
전체를 분모로 쓰면 "닫을 대상 없음" 이 실패로 섞인다.

### 결측 표현 불일치 탐지기
같은 행 안에서 어떤 필드는 `0.0`, 어떤 필드는 `None` 인 상태를 `MIXED_NULL_ZERO_ENCODING` 으로 탐지·보고한다
(bool 판은 `MIXED_NULL_FALSE_ENCODING`). 어느 인코딩이 옳은지는 **정하지 않는다** — 그건 새 조작화다.

---

## 2. 반례 탐지기

| ID | 구현 | 범위 제한 |
|---|---|---|
| CE-1 `AUTH_TIMING_ONLY` | 다른 축은 같은데 `auth_gate_stage` 만 다른 record 쌍을 찾는다 | "다른 축" 은 **호출자가 넘긴 `other_axis_signature`** 다. Lane A 는 spatial/label/flow 축을 계산하지 않는다 |
| CE-2 `OBSTRUCTION_INPUT_FOR_EXPERIENCED_FLOW` | `forced_dismissal_count` + `dismiss_required_for_task` + dismissal outcome 만으로 obstruction 쪽 입력을 판정 | **flow 길이를 계산하지 않는다.** `task_flow`/`experienced_flow` 길이 비교는 Lane F 소관이며 Lane F 파일을 읽지 않았다 |

CE-2 verdict 도메인: `OBSTRUCTION_SIDE_POSITIVE` / `OBSTRUCTION_SIDE_NEGATIVE` /
`OBSTRUCTION_SIDE_REQUIRED_BUT_NOT_DISMISSED` / `UNDETERMINED`.
정합성 결함도 함께 낸다: `FORCED_DISMISSAL_WITHOUT_REQUIRED_INTERRUPT`,
`REQUIRED_DISMISSAL_SUCCEEDED_BUT_FORCED_COUNT_ZERO`, `FORCED_DISMISSAL_COUNT_NULL_WITH_INTERRUPT_ROWS`.

---

## 3. Fixture 결과 — 27/27 PASS

양방향 대조 쌍: `A-F01 ↔ A-F07`(로그인 존재가 stage 를 만들지도 지우지도 않는다),
`A-F02 ↔ A-F06`(같은 step 열에서 auth flag 만 제거), `O-F07 ↔ O-F08/O-F09`(혼합 vs 일관 인코딩),
CE1 탐지쌍 ↔ 미탐지쌍(축이 다르거나 timing 이 같은 경우).

- **A-F01 (필수 오탐 fixture)**: landing 에 로그인 버튼이 있으나 task path 와 무관 → `NONE`. PASS.
- A-F02/03/04: BEFORE / AFTER_SELECT / AT_ENDPOINT 각 positive. PASS.
- A-F05 token↔flag 불일치, A-F08 증거 없음 → 판정 보류. PASS.
- O-F01/02/03: 무대상 / 실패 / 성공 세 구분. PASS.
- O-F06: `overlay_coverage=0.92` 인데 `task_control_occlusion=0.0` → primary 는 0.0 을 보고한다. PASS.
- O-F15: geometry-only 유도 거부. PASS.
- X-F01/X-F02: 세 축 없는 카운터·조건 미명시 조건부 모집단 생성 거부. PASS.
- X-F03: 안전 스캐너 자신의 변이 검사(금지 호출을 심은 합성 소스를 잡는지). PASS.

### 변이 검사 6/6 DETECTED, 원복 확인

| mutant | 내용 | 잡힌 fixture |
|---|---|---|
| M1 | landing generic login 을 AUTH_GATE 로 취급 | A-F01 (+A-F06/07/08) |
| M2 | "무대상" 과 "실패" 를 하나로 뭉갬 | O-F01, O-F08 |
| M3 | 보조 `overlay_coverage` 를 primary 로 승격 | O-F06 |
| M4 | `None` 을 0 으로 간주해 결측 불일치 은폐 | O-F07, O-F09 |
| M5 | `endpoint_signal_detected` 무시 | A-F04 |
| M6 | `dismiss_success_rate` 분모를 전체 interrupt 로 교체 | 카운터 불변식 (분모 3→9) |

원복: mutant 는 frozen policy dataclass 의 플래그다. 원본 소스를 편집하지 않으므로 원복이 구조적으로 보장되며,
mutant 실행 후 baseline 재실행이 동일함을 `revert_check` 에 기록했다.

---

## 4. AMBIGUOUS_DEFINITION (11건) — 내가 정하지 않고 올린다

| ID | 쟁점 |
|---|---|
| AMB-A1 | `AFTER_TASK_SELECT` 경계의 "task select" 에 해당하는 token 집합이 열거돼 있지 않다. 기본값을 `SELECT_FUNCTION` 하나로만 잡았고 SELECT_CATEGORY/SWITCH_TAB/INPUT_QUERY/OPEN_ITEM_DETAIL 등은 미결 |
| AMB-A2 | `AT_ENDPOINT` 의 판정 원천 미명시. 게다가 00 §4 의 F1 endpoint contract 는 "LOGIN/IDENTITY gate 가 불가피해지는 최초 상태" 자체를 endpoint 로 정의하므로 family 에 따라 AUTH_GATE 와 ENDPOINT 가 같은 상태다 |
| AMB-A3 | `auth_gate_stage` 는 run 단위인데 분석단위는 `service × frozen task`. run→unit 집계 규칙 없음 |
| AMB-A4 | `auth_gate_stage` 도메인에 판정불능 값이 없다. 증거 없는 run 을 `NONE` 으로 적으면 허위 실측 주장이 된다 |
| AMB-O1 | `task_control_occlusion` 정의의 "blocking obstruction" 에서 blocking 판정 기준 없음 |
| AMB-O2 | `dismiss_succeeded` 의 null/false 의미 미규정. 특히 `exists=False & succeeded=False` 가 "false 기본값 채움" 인지 "시도했다 실패" 인지 구분 불가 — 이게 무너지면 세 구분이 뭉개진다 |
| AMB-O3 | `task_control_occlusion` 이 run(02 §4)과 interrupt(02 §5) 양쪽에 있는데 집계 규칙 없음. §5 는 max 대표를 금지하면서 대체 집계자를 주지 않는다 |
| AMB-O4 | `dismiss_required_for_task` 의 판정 기준 없음. "필요했다" 는 dismissal 없이 진행 가능했는지의 반사실을 요구하는데 그 대조는 관측되지 않는다 |
| AMB-O5 | `forced_dismissal_count` grain 이 문서 간 불일치(02 §4 는 run 필드, Lane A 지시문의 obstruction 필드 목록에는 포함). interrupt 행과의 대응 규칙도 없음 |
| AMB-O6 | `overlay_coverage` 의 분모(viewport/document/가시영역) 미규정 |
| AMB-O7 | "허용된 닫기 control"(04 §2)의 범위 미열거. X 버튼만인지 배경탭/ESC/"오늘 그만보기" 포함인지 불명 |

---

## 5. 한계

- 합성 fixture 는 이 파일의 저자가 정의를 읽고 만든 것이다. **정의를 오독했다면 fixture 도 같이 틀린다.**
  변이 검사는 구현 오류를 잡지 정의 오독을 잡지 못한다.
- `auth_gate_detected`, `task_control_occlusion`, `dismiss_required_for_task`, `dismiss_succeeded` 는 전부 pass-through 다.
  upstream 판정이 틀리면 Lane A 산출도 같이 틀린다. 이 플래그들 자체의 타당성은 검증하지 않았다.
- CE-1 은 호출자가 넘기는 signature 품질에 전적으로 의존한다. signature 가 부실하면 오탐이 난다.
- CE-2 는 flow 길이를 계산하지 않으므로 "experienced flow 만 길어졌다" 를 **확정하지 못한다**. 입력 조건만 판정한다.
- run→service_task_unit 집계를 하지 않았으므로 05 §1 의 분석단위로 곧바로 쓸 수 없다.
- JSON 의 카운터 수치는 합성 fixture 를 통과시킨 실행 증거일 뿐 어떤 실측 주장도 아니다.

## 6. 하지 않은 것

flow 길이·차이 계산(Lane F) / activation_depth·flow_step_count·menu_dependency·nav_container_depth /
occlusion 구간화·blocking 판정선·dismissal 임계 / composite score·weighted index·threshold·cut-off /
geometry 로부터의 occlusion 재도출(명시적 거부) / interrupt→run occlusion 집계자 / run→unit auth 집계자 /
REAL 접속·수집 / production·mart·raw evidence 접근·수정 / gold label·task gold 생성 / holdout 접근 / GO-NO/GO 판단 / git 조작.

안전: 이 모듈은 dict 위의 순수 함수다. 네트워크·브라우저 의존성 0, credential 입력·login submit·CAPTCHA·거래 activation 경로 없음.
정적 self-check(`safety_selfcheck`)가 자기 소스를 금지 패턴으로 스캔하며, 스캐너 자체도 X-F03 으로 변이 검사했다.
