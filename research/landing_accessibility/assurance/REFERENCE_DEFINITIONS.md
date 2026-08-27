# Claude C 검산 기준 정의 추출 (docs/v2 @ bc0b7a0, 2026-08-27 12:00 KST)

> 원문 규칙만 인용. 해석 추가 없음. 출처: 00_SSOT / 01_DATA_SPEC / 02 / A1 / A2 / 07.

# 독립 검산기용 정의 추출 — docs/v2 (branch `claude-c/assurance-current` @ bc0b7a0)

루트: `/home/sieg/projects-wsl/ProjectFinal/.agent_worktrees/claude_c_assurance/research/landing_accessibility`

실재 파일: `docs/v2/00_SSOT_v2.0.md`, `01_DATA_SPEC_v2.0.md`, `02_COLLECTION_MEASUREMENT_SPEC_v2.0.md`, `A1_MEASUREMENT_OPERATIONALIZATION.md`, `A2_VOCABULARY_AND_SCHEMA_BINDING.md` (+ `03`, `04_GLOSSARY`, `05`, `EXECUTION_AUTHORITY.md`, `PHASE_GATES.md`, `MANIFEST.json`, `INSTALL_MANIFEST.json`)

---

## 1. NED / IED / MPFED

**정의 (`00_SSOT` §7)**
- `NED` — Navigation Entry Depth: "랜딩에서 대표기능이 있는 영역에 도달하기까지의 최소 state-changing activation 수."
- `IED` — Interaction Entry Depth: "대표기능 영역에서 predefined endpoint까지 필요한 최소 activation 수."
- `MPFED = NED + IED`
- `ExcessDepth = MPFED - 같은 archetype의 중앙값`

**산출식 (`A1` §1.3)** — 원문 코드블록:
```
k = min{ i : s_i 에서 FUNCTION_AREA_REACHED 성립 }
m = min{ i : s_i 에서 FUNCTION_ENDPOINT_REACHED 성립 }

NED   = k
IED   = m - k
MPFED = m            ( = NED + IED, 00 §7과 항등 )
```
state 열은 `s0`(랜딩) → `a1` → `s1` → … → `an` → `sn`, `a_i`는 `02` §9가 activation으로 인정한 조작만 (`A1` §1.1).

**단위** — `A1` §2.6 규칙 MIN-1: "최소화 대상은 `02` §9가 정의한 **activation(= `fact_task_step` 행)의 개수** 하나뿐이다." 비용함수·가중치 없음. 즉 step 수.

**activation 인정/제외 (`02` §9)** — 인정 예: `button tap` / `link tap` / `menu open` / `item select`. 제외: `텍스트 한 글자씩 입력` / `passive loading` / `redirect 자체` / `server wait` / `scroll distance` / `popup dismiss`. 제외 행위는 step row를 만들지 않는다 (`A1` §1.7, `A2` §1.5.4 규칙 D-2).

**동시 성립·역전 (`A1` §1.4)**
| 상황 | 결과 |
|---|---|
| `s0`에서 영역 성립 | `NED = 0` |
| `s0`에서 endpoint까지 성립 | `NED=0, IED=0, MPFED=0` |
| 한 activation이 영역·endpoint 동시 성립 (`k=m=i`) | 그 activation은 **NED 구간에 귀속**, `IED = 0` |
| `m < k` | `k := m` 소급 확정, `IED = 0`, `area_signal_status = INFERRED_FROM_ENDPOINT` |
| 영역 성립 후 재파괴 | `k` 불변, 재출현 overlay는 `forced_dismissal_count`로 기록 |

**NULL 조건 (`A1` §1.5, `A2` §1.5.3)**
| 관측 결과 | `area_signal_status` | NED | IED | MPFED |
|---|---|---|---|---|
| 영역·endpoint 모두 관측 | `OBSERVED` | `k` | `m-k` | `m` |
| endpoint만 관측(역전) | `INFERRED_FROM_ENDPOINT` | `m` | `0` | `m` |
| 영역만 관측, endpoint 전 종료 | `OBSERVED` | `k` | `NULL` | `NULL` |
| 둘 다 미관측 | `NOT_OBSERVED` | `NULL` | `NULL` | `NULL` |

"`NULL`을 `0`으로 대체하거나 예산 상한값으로 대체하지 않는다" (`A1` §1.5). `A2` §1.5.1: `endpoint_status`가 `FUNCTION_ENDPOINT_REACHED` 이외 6값이면 NED/IED/MPFED = `NULL`. 규칙 N-3: `NED = 0` ≠ `NED IS NULL`. 규칙 N-2: `MPFED IS NULL` 사유는 `endpoint_status` / `endpoint_status_detail` / `area_signal_status`가 말한다.

**dom_order 2차 키 (`A1` §5.1 · §2.6 MIN-4, `A2` §1.13)**
- tie-break 정렬 키: `( marked_primary desc, dom_order asc, selector asc )` (`A1` line 366) — 1차 `marked_primary`, **2차 `dom_order`**, 3차 `selector`. `area_css_px2`는 tie-break 키에서 **제외**한다 (`A1` line 368).
- `dom_order` = "해당 state의 후보 열거 내 **문서 순서 정수 인덱스**(0-based, probe 산출)" (`A1` §5.1). 컬럼 위치: `fact_primary_action_candidate.dom_order` (`A2` §1.13). probe(`l0_probe.js`)가 열거 시점 문서 순서를 0-based 정수로 산출. 관측값이 아니라 구조값이므로 `NULL`이 없다. iframe 등 다른 문서 간에는 재-매김되므로 3차 키 `selector`가 필요.

---

## 2. L1 terminal state

**`endpoint_status` — 동결된 7값 (`02` §7 → `A2` §1.5.1)**

| 값 | `endpoint_reached` | NED/IED/MPFED | 정당한 endpoint인가 |
|---|---|---|---|
| `FUNCTION_ENDPOINT_REACHED` | 1 | 정수 | **예** |
| `AUTH_GATE_REACHED` | 0 | `NULL` | 아니오 |
| `PAYMENT_GATE_REACHED` | 0 | `NULL` | 아니오 |
| `PERSONAL_DATA_REQUIRED` | 0 | `NULL` | 아니오 |
| `CAPTCHA` | 0 | `NULL` | 아니오 |
| `BLOCKED` | 0 | `NULL` | 아니오 |
| `UNRESOLVED` | 0 | `NULL` | 아니오 |

**규칙 E-1 (집합 불확장)**: "이 7값 집합에 새 값을 추가하지 않는다." 7값은 상호배타. `endpoint_reached`는 `endpoint_status = FUNCTION_ENDPOINT_REACHED`의 동치 파생값.

**gate가 endpoint인 archetype (`A2` §1.5.1a, 규칙 E-5~E-10)** — `00 §3` L1 표가 gate절을 준 두 행뿐:
- `FINANCIAL_ACTION_ENTRY`: 로그인 gate · 인증(본인인증) gate → endpoint (`endpoint_status = FUNCTION_ENDPOINT_REACHED`, `endpoint_status_detail = ENDPOINT_VIA_AUTH_GATE`)
- `COMMUNICATION_ENTRY`: **로그인 gate만**. 본인인증 gate는 `AUTH_GATE_REACHED`(개인정보 요구 시 `PERSONAL_DATA_REQUIRED`) — 규칙 E-6a
- 규칙 E-6b: `auth_gate_kind = UNDETERMINED`인 gate는 archetype 불문 `AUTH_GATE_REACHED`
- 규칙 E-7: "어느 archetype에서도 **gate를 통과하지 않는다**"

**`endpoint_status_detail`** (`A1` §2.2, `A2` §1.5.2) — 하위 세분값 동반 컬럼. 확인된 값: `UNRESOLVED_DEPTH_BUDGET_EXCEEDED` (상위 `UNRESOLVED`), `ENDPOINT_VIA_AUTH_GATE`.

**Scout 예산 (`A1` §2.1)** — 전부 P-C `E000_V2`에서 검증 후 동결, 기본값은 착수용:
| 파라미터 | 기본값 |
|---|---|
| `MAX_ACTIVATIONS_PER_TASK` | `8` |
| `MAX_STATE_REVISITS` | `2` |
| `MAX_SCOUT_WALL_CLOCK_S` | `180` |
| `MAX_CONSECUTIVE_NO_STATE_CHANGE` | `2` |
| `BRANCHING_LIMIT` | `4` |

예산 소진 시: `endpoint_status = UNRESOLVED`, `endpoint_status_detail = UNRESOLVED_DEPTH_BUDGET_EXCEEDED`, `endpoint_reached = 0`, NED/IED/MPFED = `NULL` (`A1` §2.2). §2.3: "measurement status다. KWCAG 판정으로 전환하지 않는다."

> **360초 target wall-clock timeout — 문서에 없음.** 문서 전체를 grep한 결과 wall-clock 값은 `MAX_SCOUT_WALL_CLOCK_S = 180` 하나뿐이며 `360`이라는 값은 어느 문서에도 없다.

**transport failure / L1 미시작 기록 필드** — L1 수준 전용 필드는 **문서에 없음**. transport failure는 L0 관측 수준 `fact_landing_observation.measurement_status = FAILED_ROBOTS_OR_TRANSPORT` (`A2` §1.2)로만 정의된다. L1 미시작 상태에 해당하는 값은 `dim_representative_task.mapping_status ∈ {AMBIGUOUS_UNRESOLVED, EXCLUDED}` (`A2` §1.9) 또는 `endpoint_status = UNRESOLVED`이며, "L1 미시작"을 지시하는 전용 enum은 없다.

---

## 3. L0 evidence 필수 구성요소

**`02` §11 Evidence Identity 원문**: "한 observation은 정확히 다음과 대응해야 한다. DOM / AX / screenshot / probe / manifest. Task step도 before/after evidence가 trace와 연결되어야 한다. display name을 file id로 사용하지 않는다. hash-based observation id 사용."

**`A1` §6.2 확장 판독**: identity 집합을 `DOM / AX / screenshot(initial) / screenshot(fullpage) / computed CSS / probe / manifest` 7종으로 읽는다.

**`fact_landing_observation` 경로 컬럼** (`01` §4 + `A1` §6.1 확장 제안): `screenshot_path`(→ `screenshot_initial_path`로 의미 확정), `screenshot_fullpage_path`, `computed_css_path`(probe와 별도 파일), `dom_path`, `ax_path`, `probe_path`, `manifest_path`, `evidence_run_id`, `collection_started_at`/`collection_finished_at`(UTC ISO-8601), `viewport_configured_width/_height`(`390 × 844`), `viewport_width/_height`(실측 layout viewport), `device_pixel_ratio`.

**geometry / primary action** — `fact_primary_action_candidate` (`A1` §5.1, 신규 제안 표): `bbox_x` `bbox_y` `bbox_w` `bbox_h` (CSS px, L0-a 기준), `area_css_px2 = bbox_w × bbox_h` (= `PrimaryActionOcclusion`의 분모), `viewport_visible`, `similarity_score`, `selection_basis ∈ {DETERMINISTIC_RULE, EMBEDDING_RANK, AI_REVIEW, HUMAN_FINAL}`, `selection_status ∈ {SELECTED, RUNNER_UP, REJECTED}`. `TOP_N_CANDIDATES = 5` (P-C 동결). `SELECTED` 0행이면 `primary_action_visible_initial = NULL`(0이 아니다).

**overlay/modal** — `fact_interrupt_element` (`01` §5 + `A1` §3.4 추가): `dismiss_screenshot_before` / `dismiss_screenshot_after` / `dismiss_dom_after` / `dismiss_method` / `dismiss_failure_mode` / `dismiss_persistence_hint`.

**L0 단계 순서 (`A1` §3.1)** — L0-a(조작 없음, `02 §3` 수집 전량) → L0-b(`02 §5` 1~4차 + 5차 dismiss control 검사, 조작 없음) → L0-c(6차 dismissal 실제 시도, **조작 있음**). "L0-a의 evidence가 확정된 뒤에만 L0-c를 수행한다."

**evidence manifest 스키마 (`A1` §6.2, `07_EVIDENCE_MANIFEST_CONTRACT` §3 인용)**
- 경로: `evidence/<run_id>/manifest.jsonl`
- 레코드: `(observation_id, relpath, sha256, bytes)`
- 해시 알고리즘: **`sha256`** (manifest 등록 및 원장 `record_sha256` 모두)
- `(observation_id, relpath)` 중복 금지 (`07` §4)
- 모든 `*_path`는 run 디렉터리 기준 **상대경로**; 절대경로·`..` 금지
- `manifest_path`는 run 단위이며 관측마다 고유하지 않다

**observation identity 키 (`A1` §6.3)** — 원문:
```
observation_id = hash( web_target_id, evidence_run_id, requested_url,
                       protocol_version, collection_started_at )
```
"해시 함수·정규화 규칙·자릿수는 **P-C에서 동결**한다. 이 문서는 입력 집합만 확정한다. `audit_date`만으로 관측을 식별하지 않는다."

**`evidence_run_id` 유도식 (`A2` §1.11.2 규칙 RC-6)**:
```
evidence_run_id = "rc" || hex( sha256( ... ledger_record_sha256 || 0x1F || ... ) )
```
= `f(ledger_record_sha256, countersign_commit_sha, execution_index)`. 최초(E001 baseline) run에도 적용. 검사 A-6이 재계산·바이트 비교.

**append-only 규칙 정확한 문구 (`02` §12)**:
> "같은 evidence를 덮어쓰지 않는다.
> - 재수집 → 새 evidence run
> - 같은 evidence 재판정 → 새 judgment version"

부가: `A2` §5.7 규칙 V-9 — `recollection_ledger.jsonl`은 `research/landing_accessibility/collection/`에 두며 "git 추적 대상이며 **append로만** 쓴다 — 기존 줄 수정·삭제는 규칙 RC-7 체인 검사가 잡는다." 원장 해시체인: `prev_record_sha256`(첫 레코드는 `0`×64) / `record_sha256`(자신을 제외한 전 필드를 키 정렬·UTF-8·개행 없음으로 정규화한 바이트의 sha256).

---

## 4. KWCAG 판정 스키마

**decision enum (`00` §4, `A2` §1.7)** — `verdict_state`와 `final_status`가 **같은 값 도메인**을 쓰되 다른 시점:
`PASS` / `FAIL` / `UNDETERMINED` / `NA` (표기는 `NA`, `N/A` 아님). 4값 상호배타, 합집합이 전체.

- `verdict_state`: AI 검토 **이전**, 결정적 측정 파이프라인이 정함, **불변**(고치려면 새 evidence run)
- `final_status`: adjudication **이후**, §1.11 전이 규칙, judgment version 단위 append

**항등식 (`A2` §1.7)**:
```
applicable_count = pass_count + fail_count + undetermined_count
```
`NA` 행은 `applicable_count = 0`이고 나머지 셋도 0 (참인 0).

**deterministic vs AI review 경로 필드**
- `fact_criterion_result.automation_grade` — 허용값(`A2` §3.1): `A_*` … `D_EMBEDDING_TEXT`, `E_VLM`, `F_HUMAN_FINAL` (문서에서 확인된 토큰)
- `fact_criterion_result.ai_review_required` — 0/1. `verdict_state = UNDETERMINED`이거나 결정적 단계가 신뢰구간을 벗어나면 1. `automation_grade ∈ {D_EMBEDDING_TEXT, E_VLM, F_HUMAN_FINAL}`이면 반드시 1 (제약 G-2)
- `fact_ai_adjudication.review_task_type` — `CRITERION_VERDICT` / `CRITERION_UNDETERMINED_TRIAGE`
- `ai_review_status` — 공유 열거형 (`A2` §1.10)
- 전이 규칙 T-6(`NA` 고정) / T-8(`UNDETERMINED` triage는 `final_status`를 못 바꿈)
- cascade 5단계 (`A1` §1.6): DOM/AX·URL·geometry → embedding rank → VLM(JSON only) → reviewer B + arbiter → `HUMAN_FINAL` (`HUMAN_FINAL_REVIEW_MAX = 5`)

**criterion id 형식** — **문서에 없음.** `01` §7이 `criterion_id` 컬럼만 선언하고 형식(예: `5.1.1`)을 규정하지 않는다. `A2` §6.4가 명시적으로 미결로 남긴다: "KWCAG criterion subset 및 `criterion_id` 목록 | `00 §15` · P-C".

**older-relevant 사전 태깅 criterion 집합** — **아직 동결돼 있지 않음 (문서에 없음).** 태그 값 도메인만 존재: `older_relevance ∈ {VISION, MOTOR, COGNITIVE_NAVIGATION, OTHER}` (`01` §7, `00` §4). 동결 예정 위치는 `PHASE_GATES.md` line 115: "KWCAG subset | older-relevant + L0/L1 observable subset 동결. **33개 전수 자동화를 목표하지 않음.** threshold 무변경". 실제 criterion 목록을 담은 파일·표는 리포지토리에 존재하지 않는다 (`A2` §5.6: `fact_criterion_result` 물리 대응 "없음", 산출 Phase P-C → P-F).

---

## 5. Obstruction 변수 4개

**`OverlayCoverage` (`00` §8)** — 원문:
```
OverlayCoverage = overlay가 최초 화면에서 차지하는 면적 / 최초 화면 면적
```
저장: `fact_interrupt_element.overlay_coverage`, 보조 `viewport_intersection_area`; 관측 요약 `fact_landing_observation.max_overlay_coverage` (`01` §4·§5).

**`PrimaryActionOcclusion` (`00` §8)** — 원문:
```
PrimaryActionOcclusion = 대표기능 control이 overlay에 가려진 면적 / 대표기능 control 면적
```
`A1` §5.2 구체화:
```
fact_interrupt_element.primary_action_occlusion
    = (그 interrupt가 SELECTED 후보 bbox를 가린 면적) / SELECTED 후보의 area_css_px2

fact_landing_observation.max_primary_action_occlusion
    = max over interrupts ( primary_action_occlusion )

fact_landing_observation.primary_action_visible_initial
    = SELECTED 후보의 viewport_visible
```
"세 값 모두 L0-a 상태에서 산출한다(§3.1)."

**`blocking_modal_count`** — `fact_landing_observation` 컬럼 (`01` §4). 산식은 **문서에 없음**. 근접 정의는 `fact_interrupt_element.blocks_primary_action`과 `02` §5 3차 blocking 판정("대표기능을 가리는가 / 대표기능 진입 전에 닫아야 하는가 / 화면의 큰 부분을 덮는가")뿐이며, count로 집계하는 명시적 술어는 없다.

**`forced_dismissal_count`** — `fact_task_entry` 컬럼 (`01` §6). `02` §9: "Popup dismiss는 `forced_dismissal_count`에 따로 기록." `A1` §3.3: "L1의 `forced_dismissal_count`는 L0 dismiss 측정과 별개다. 전자는 L0에서의 닫기 가능성 측정, 후자는 L1 경로에서 실제로 닫아야 했던 횟수다. 두 값을 합산하지 않는다." `A2` 규칙 D-3: NED/IED/MPFED에 더해 "총 조작 수" 같은 변수를 만들지 않는다.

**Interrupt 분류 enum (`00` §8)**: `BLOCKING_MODAL` / `PROMOTION_MODAL` / `COOKIE_CONSENT` / `ADVERTISEMENT` / `APP_INSTALL_PROMPT` / `LOGIN_PROMPT` / `CHAT_WIDGET` / `BANNER` / `TOAST` / `UNKNOWN`

**dismiss 관련 (`A1` §3.3)**: `dismiss_method ∈ {CONTROL_CLICK, DIALOG_CLOSE, ESCAPE_KEY, BACKDROP_CLICK, NONE}`; `dismiss_failure_mode ∈ {NO_CONTROL, NOT_HITTABLE, NO_STATE_CHANGE, NEW_INTERRUPT_APPEARED, NAVIGATED_AWAY}`; 시행 횟수 "한 interrupt 당 **정확히 1회**"; `dismiss_control_accessible_name`이 비면 `NAME_ABSENT` 센티널.

---

## 6. InteractionArchetype

**전체 enum (`00` §6)** — 7값:
`QUERY` / `CONTENT_OPEN` / `ITEM_DETAIL` / `PLACE_LOOKUP` / `COMMUNICATION_ENTRY` / `FINANCIAL_ACTION_ENTRY` / `UTILITY_ENTRY`

(별도 축인 Business Domain 8값: `PORTAL_SEARCH` / `CONTENT_VIDEO` / `NEWS_CONTENT` / `SHOPPING_COMMERCE` / `MAP_MOBILITY` / `FINANCE_PAYMENT` / `SOCIAL_COMMUNICATION` / `UTILITY_OTHER`)

**서비스별 archetype 동결 위치** — **아직 동결돼 있지 않음. 파일이 존재하지 않는다.**
- 논리 표: `dim_representative_task.interaction_archetype` (`01` §3)
- `A2` §5.6: `dim_representative_task` → "산출 Phase **P-A**(codebook·pilot 매핑) → **P-B**(동결) / 현재 물리 대응 **없음**"
- 동결 상태 필드: `mapping_status ∈ {DRAFT, CANDIDATE, FROZEN, AMBIGUOUS_UNRESOLVED, EXCLUDED}`, 단방향 `DRAFT → CANDIDATE → {FROZEN, AMBIGUOUS_UNRESOLVED, EXCLUDED}` (`A2` §1.9)
- 규칙 P-1: "`FROZEN` 전이는 KWCAG 결과·`certified_current`를 **읽기 전에** 일어나야 한다. 동결 시각과 접근성 산출물 생성 시각의 순서를 artifact로 남긴다."
- 규칙 P-2: `region_signal_type = CODEBOOK_PENDING`인 task는 `FROZEN` 전이 불가. `UTILITY_ENTRY`는 `00 §3` 대응 행이 없어 P-A codebook 동결까지 미동결 유지 (`A1` §1.2)
- `PHASE_GATES.md` line 87: "Functional Codebook | Business Domain과 Interaction Archetype **분리** 정의, archetype 7종 endpoint 명시"

---

## 7. Forbidden external action

**`00` §3 「절대 제외」 원문 목록** (10항):
로그인 이후 / 본인인증 이후 / 결제 완료 / 송금 완료 / 예약 완료 / 회원가입 / 오류복구 전체 과정 / full task usability / 사용자별 실제 성공률 / 사이트 전체 KWCAG 인증 재평가

**`02` §7 즉시 종료 상태 + 금지 문구**: `FUNCTION_ENDPOINT_REACHED` / `AUTH_GATE_REACHED` / `PAYMENT_GATE_REACHED` / `PERSONAL_DATA_REQUIRED` / `CAPTCHA` / `BLOCKED` / `UNRESOLVED` 도달 시 즉시 종료. 원문: **"결제·본인인증을 우회하지 않는다."**

**`A2` §1.5.1a 규칙 E-7**: "어느 archetype에서도 **gate를 통과하지 않는다**. gate를 통과하거나 자격증명을 입력하지 않는다. `00 §3 절대 제외`의 `로그인 이후`·`본인인증 이후`는 그대로 유효하고, `02 §7` `결제·본인인증을 우회하지 않는다`도 그대로다."

**evidence에 기록되는 필드**
- `fact_task_entry.endpoint_status` — 위 7값 중 해당 종료값 (`PAYMENT_GATE_REACHED` / `PERSONAL_DATA_REQUIRED` / `CAPTCHA` / `AUTH_GATE_REACHED` / `BLOCKED`)
- `fact_task_step.auth_gate_detected` — 0/1. gate 종류 불문(종류 미확정 `auth_gate_kind = UNDETERMINED`여도 `1`) (`A2` §1.5.1a 규칙 E-6b ⑦)
- `fact_task_step.auth_gate_kind` — 값 `UNDETERMINED` 확인됨 (전체 도메인은 문서에서 열거되지 않음)
- `fact_task_entry.auth_gate_before_endpoint` — `A2` §1.5.1a 산식:
```
auth_gate_before_endpoint =
  1  if EXISTS step ∈ fact_task_step(그 task):
         auth_gate_detected = 1  AND  그 step 이 "endpoint 를 실현한 gate step" 이 아니다
  0  otherwise
```
- 유병률 집계 (규칙 E-8):
```
auth_gate_observed = (auth_gate_before_endpoint = 1)
                  OR (endpoint_status_detail = 'ENDPOINT_VIA_AUTH_GATE')
```
- **검사 I-5** (`A2` §6.3.1): "두 archetype에서 gate 관측 **이후** activation이 더 발생한 궤적 주입 (자격증명 입력·gate 통과) → **차단** (E-7 · `02 §7` 즉시종료 · `00 §3 절대 제외`)"

CAPTCHA 우회 금지는 별도 문구 없이 `CAPTCHA` 종료값("사람 검증이 요구됐다")으로 즉시종료 처리된다. OTP·PII는 `PERSONAL_DATA_REQUIRED`("개인정보 입력이 요구됐다")에 흡수된다. "OTP"라는 용어 자체는 문서에 없음.

---

## 8. Frozen target frame (59 타깃)

**"59 타깃"의 frozen target frame은 문서·리포지토리에 존재하지 않음.**

- `59`가 등장하는 유일한 자리는 `A2` §1.3.1 line 378: `eligibility_confidence | url_confidence / observation_confidence (HIGH **59** · MEDIUM 1 · LOW 11 · 결측 10) [실측]` — 이는 target frame 행수가 아니라 신뢰도 분포다.
- `A2` §1.3: `web_eligibility_status = ELIGIBLE_WEB` 건수 **0** `[미측정]`. §6.2: "`web_eligibility_status` 4값 — `ELIGIBLE_WEB` · `EXCLUDED_APP_ONLY` · `EXCLUDED_NO_PUBLIC_WEB_LANDING` · `UNDETERMINED_URL_EVIDENCE` — 현재 전부 0건 `[실측]`".
- `A2` §5.6: `dim_web_target`의 확정 산출은 **P-B**이며 현재 물리 대응 없음.

**현재 존재하는 선행(pre-freeze) 파일** — `A2` §5.5: "**`web_target_group`은 `dim_web_target`이 아니다.** URL 확정 **이전의 그룹 후보 표**다."

| 파일 | 실측 |
|---|---|
| `state/web_target_group.parquet` (+ `.csv`) | **68행** (`member_count` 1→65, 2→3). `official_landing_url` 대응 `web_target_url` **nonnull 0**, `url_evidence` **nonnull 0** |
| `state/service_master.parquet` (+ `.csv`) | entity 81행 (`web_target_group_id` nonnull 71 / null 10, distinct group 68) |
| `state/source_ranking_rows.parquet` | 261행 |
| `sources/certification/certification_registry.parquet` | 인증 원장 |

**키 컬럼 (파일 헤더 실측)**
- `web_target_group.csv`: `web_target_group_id`, `web_target_key`, `member_service_ids`, `member_canonical_keys`, `member_count`, `member_domains`, `member_review_decisions`, `grouping_status`, `grouping_basis`, `expected_url_relationship`, `expected_url_relationship_basis`, `expected_url_relationship_is_hypothesis`, `expected_url_relationship_confirmed_by_url`, `expected_url_relationship_falsifier`, `expected_url_relationship_risk`, `web_target_url`, `url_evidence`
- `service_master.csv`: `service_id`, `canonical_service_key`, `service_name_canonical`, `domain`, `axis_type`, `appears_in_app_panels`, `appears_in_retail_panels`, `app_row_count`, `retail_row_count`, `alias_count`, `canonicalization_basis`, `review_decision`, `decision_rule`, `decision_basis`, `decision_evidence`, `decision_confidence`, `decided_at`, `decided_by`, `needs_human_review`, `web_eligibility_status`, `web_eligibility_basis`, `web_target_group_id`, `web_target_key`, `web_target_grouping_status`

`A2` §5.5 경고 원문: "`expected_url_relationship_confirmed_by_url`이 전부 `False` `[실측]` 인 지금, 그룹을 web target으로 간주한 어떤 집계도 근거가 없다." 그룹 층 `hypothesis_outcome` 분포: `NOT_APPLICABLE_SINGLETON` 65 · `FALSIFIED_SPLIT_SAME_DOMAIN_DIFFERENT_PATH` 2(gmarket · naver) · `NOT_TESTABLE_MEMBER_URL_UNRESOLVED` 1(coupang).

또한 `state/_invalidated/service_certification_match_draft.csv`는 "**무효화 보관물**이며 대응이 아니다. **인용 금지**" (`A2` §5.6).