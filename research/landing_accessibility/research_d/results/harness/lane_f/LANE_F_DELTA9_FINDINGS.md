# LANE F — Δ9 / R12 수렴 결과

- **verdict**: `CONVERGED_WITH_AMBIGUITY`
- 생성: 2026-08-27T18:18:09.079305+00:00
- 권위: `T-A-V3-STEP1-006` (Δ9) · `T-A-V3-STEP1-007` (R12) · SSOTV3 04 §2/§5, 03 §6
- base SHA: `ce97273129b404774736ec566603b9e2b969ecdf`
- 데이터: **합성 fixture 전용**. REAL 접속·MAIN50·mart/raw·gold·holdout 없음.
- 독립단위 family n=10. 45 pair 는 distance matrix cell 이며 **n=45 가 아니다**.

## 1. 회귀 — 수렴이 기존 검사를 지우지 않았는가

- 수렴 전 고정된 check 202건 중 **202건이 그대로 존재** (id·기대값 무수정), 실패 0건, 소실 0건
- 수렴이 **추가**한 check: 102건 → 현재 총 304건
- 전체 실패: 0건 / 변이 미검출: [] / 원복 증명 실패: 0
- 고정 id 목록 sha256 `8db2dbacbe2b9825e010cd49096349258d63210d14ff1b9378869073f9c33649` (기록값과 일치: True)

## 2. Δ9 — canonical 18종 전수 분류

> `activation_depth` 는 **사용자가 control 을 의도적으로 활성화해 상태 전이를 일으킨 토큰**의 수다.
> - ① 사용자의 의도적 조작인가 (수동 로드·리다이렉트·대기는 아니다)
> - ② control 활성화인가 (스크롤·타이핑은 control 활성화가 아니다)
> - ③ 상태가 전이되는가 (단순 표시 변화가 아니라 화면·경로·컨테이너 상태가 바뀌는가)

| token | activation_depth | 근거 | flow_step_count |
|---|---|---|---|
| `OPEN_GLOBAL_MENU` | **IN** | Δ9 general_criterion 3검사를 모두 통과한다: 의도적 조작 · control 활성화 · 상태 전이. 03 §6 포함목록 'link/button/tab/menu open · category/function/result select · state-chang | 미정 (AMB-F04) — Δ9 는 flow_step_count 를 확정하지 않았다 |
| `OPEN_LOCAL_MENU` | **IN** | Δ9 general_criterion 3검사를 모두 통과한다: 의도적 조작 · control 활성화 · 상태 전이. 03 §6 포함목록 'link/button/tab/menu open · category/function/result select · state-chang | 미정 (AMB-F04) — Δ9 는 flow_step_count 를 확정하지 않았다 |
| `SWITCH_TAB` | **IN** | Δ9 general_criterion 3검사를 모두 통과한다: 의도적 조작 · control 활성화 · 상태 전이. 03 §6 포함목록 'link/button/tab/menu open · category/function/result select · state-chang | 미정 (AMB-F04) — Δ9 는 flow_step_count 를 확정하지 않았다 |
| `EXPAND_ACCORDION` | **IN** | Δ9 general_criterion 3검사를 모두 통과한다: 의도적 조작 · control 활성화 · 상태 전이. 03 §6 포함목록 'link/button/tab/menu open · category/function/result select · state-chang | 미정 (AMB-F04) — Δ9 는 flow_step_count 를 확정하지 않았다 |
| `SELECT_CATEGORY` | **IN** | Δ9 general_criterion 3검사를 모두 통과한다: 의도적 조작 · control 활성화 · 상태 전이. 03 §6 포함목록 'link/button/tab/menu open · category/function/result select · state-chang | 미정 (AMB-F04) — Δ9 는 flow_step_count 를 확정하지 않았다 |
| `SELECT_FUNCTION` | **IN** | Δ9 general_criterion 3검사를 모두 통과한다: 의도적 조작 · control 활성화 · 상태 전이. 03 §6 포함목록 'link/button/tab/menu open · category/function/result select · state-chang | 미정 (AMB-F04) — Δ9 는 flow_step_count 를 확정하지 않았다 |
| `INPUT_QUERY` | **OUT** | 타이핑이다. 03·04 둘 다 명시 제외. flow_step_count 에는 포함 | 포함 (Δ9 OUT 사유문: 'flow_step_count 에는 포함'; 04 §5 'typing ... 포함') |
| `SELECT_ORIGIN` | **CONDITIONAL** | **입력수단에 따라 갈린다.** picker/dropdown/calendar 처럼 control 을 활성화해야 값이 정해지면 activation_depth 에 **포함**한다. 자유입력란에 타이핑했다면 타이핑이므로 **제외**하고 flow_step_count 에만 넣는 | 미정 (AMB-F04) — Δ9 는 flow_step_count 를 확정하지 않았다 |
| `SELECT_DESTINATION` | **CONDITIONAL** | **입력수단에 따라 갈린다.** picker/dropdown/calendar 처럼 control 을 활성화해야 값이 정해지면 activation_depth 에 **포함**한다. 자유입력란에 타이핑했다면 타이핑이므로 **제외**하고 flow_step_count 에만 넣는 | 미정 (AMB-F04) — Δ9 는 flow_step_count 를 확정하지 않았다 |
| `SELECT_DATE` | **CONDITIONAL** | **입력수단에 따라 갈린다.** picker/dropdown/calendar 처럼 control 을 활성화해야 값이 정해지면 activation_depth 에 **포함**한다. 자유입력란에 타이핑했다면 타이핑이므로 **제외**하고 flow_step_count 에만 넣는 | 미정 (AMB-F04) — Δ9 는 flow_step_count 를 확정하지 않았다 |
| `SUBMIT_QUERY` | **IN** | Δ9 general_criterion 3검사를 모두 통과한다: 의도적 조작 · control 활성화 · 상태 전이. 03 §6 포함목록 'link/button/tab/menu open · category/function/result select · state-chang | 포함 (04 §5 'typing/submit/auth encounter 포함'; 03 §6 'task-intent typing/submit 을 별도 token 으 |
| `SELECT_RESULT` | **IN** | Δ9 general_criterion 3검사를 모두 통과한다: 의도적 조작 · control 활성화 · 상태 전이. 03 §6 포함목록 'link/button/tab/menu open · category/function/result select · state-chang | 미정 (AMB-F04) — Δ9 는 flow_step_count 를 확정하지 않았다 |
| `OPEN_ITEM_DETAIL` | **IN** | Δ9 general_criterion 3검사를 모두 통과한다: 의도적 조작 · control 활성화 · 상태 전이. 03 §6 포함목록 'link/button/tab/menu open · category/function/result select · state-chang | 미정 (AMB-F04) — Δ9 는 flow_step_count 를 확정하지 않았다 |
| `OPEN_PLACE_DETAIL` | **IN** | Δ9 general_criterion 3검사를 모두 통과한다: 의도적 조작 · control 활성화 · 상태 전이. 03 §6 포함목록 'link/button/tab/menu open · category/function/result select · state-chang | 미정 (AMB-F04) — Δ9 는 flow_step_count 를 확정하지 않았다 |
| `DISMISS_OBSTRUCTION` | **OUT** | 03·04 둘 다 명시 제외. forced_dismissal_count 로 별도 집계 | 미정 — Δ9 는 'forced_dismissal_count 로 별도 집계'라고만 적었다. flow_step_count base(task/experienced)  |
| `AUTH_GATE` | **OUT** | 사용자 활성화가 아니라 **마주친 상태**다. 기준 ①에 걸린다. flow_step_count 에는 auth encounter 로 포함 | 포함 (Δ9 OUT 사유문: 'flow_step_count 에는 auth encounter 로 포함') |
| `ENDPOINT_REACHED` | **OUT** | 종결 표지이지 행위가 아니다 | 미정 (AMB-F04) — Δ9 는 flow_step_count 를 확정하지 않았다 |
| `ABSTAIN` | **OUT** | 행위가 아니라 판정 유보다 | 미정 (AMB-F04) — Δ9 는 flow_step_count 를 확정하지 않았다 |

`OPEN_RIGHT_DRAWER` 는 이 표에 **없다**. 방향은 토큰이 아니라 `nav_container_type` + `reveal_direction` 이다 (T-B-FC-013). Lane F 는 목록 밖 값을 `NOT_IN_CANONICAL_18` 스키마 오류로 보고한다 — 확인됨: True.

## 3. SUBMIT_QUERY 포함이 바꾸는 값

**먼저 정직하게**: 이 하네스는 수렴 전에도 SUBMIT_QUERY 를 제외하지 않았다 — 제외목록은 (INPUT_QUERY, DISMISS_OBSTRUCTION) 뿐이었다. 따라서 **Δ9 의 submit 조항 자체는 Lane F 의 계수를 바꾸지 않는다.** Lane F 에서 실제로 값을 바꾼 것은 같은 티켓의 AMB-F03 확정(AUTH_GATE/ENDPOINT_REACHED/ABSTAIN 을 OUT 으로) 이며, 그것이 '두 읽기 병기 + value 보류'를 '단일 값'으로 바꿨다. 과대주장을 피하기 위해 이 사실을 먼저 적는다.

| case | sequence | 수렴 전 두 읽기(literal/activation_only) | 수렴 전 emit | 수렴 후 Δ9 | submit 제외 반사실 |
|---|---|---|---|---|---|
| SQE01_search_then_submit | `INPUT_QUERY > SUBMIT_QUERY > SELECT_RESULT > ENDPOINT_REACHED` | 3 / 2 | 보류(None) | **2** | 1 |
| SQE02_press_directly | `SELECT_RESULT > ENDPOINT_REACHED` | 2 / 1 | 보류(None) | **1** | 1 |
| SQE03_family_SYN02 | `INPUT_QUERY > SUBMIT_QUERY > SELECT_RESULT > OPEN_ITEM_DETAIL > ENDPOINT_REACHED` | 4 / 3 | 보류(None) | **3** | 2 |
| SQE04_slot_search_SYN08 | `SELECT_ORIGIN > SELECT_DESTINATION > SELECT_DATE > SUBMIT_QUERY > SELECT_RESULT > ENDPOINT_REACHED` | 6 / 5 | 보류(None) | **5** | 4 |

- 검색 경유 `INPUT_QUERY > SUBMIT_QUERY > SELECT_RESULT > ENDPOINT_REACHED` = **2**, 직접 진입 `SELECT_RESULT > ENDPOINT_REACHED` = **1** → 구별됨: True
- submit 을 빼면 각각 1 / 1 → **붕괴됨: True**. Δ9 의 실질 근거가 fixture 에서 재현된다.
- 사전등록된 family 비대칭: 이 규칙은 검색 기반 family(F2·F3·F5)의 depth 를 F1·F4 보다 구조적으로 높인다. 그것이 사실이다. 관측 0건 시점에 이 비대칭을 예상으로 기록한다 — 나중에 '예상대로였다'고 사후 서술하지 않기 위함이다.

## 4. CONDITIONAL 3종 × fixture_input_mode

| case | fixture_input_mode | activation_depth | 미해결 CONDITIONAL | 보류 구간 |
|---|---|---|---|---|
| CD01_dropdown | DROPDOWN | 5 | 0 | — |
| CD02_free_text | FREE_TEXT | 2 | 0 | — |
| CD03_map_pan | MAP_PAN | 5 | 0 | — |
| CD04_mixed_means_unrecorded | MIXED | **보류(None)** | 3 | [2, 5] |
| CD05_mixed_means_recorded | MIXED | 4 | 0 | — |
| CD06_mode_absent | (미기록) | **보류(None)** | 3 | [2, 5] |
| CD07_mode_other | OTHER | **보류(None)** | 3 | [2, 5] |
| CD08_no_conditional_token_present | (미기록) | 3 | 0 | — |

- 같은 열 `SELECT_ORIGIN > SELECT_DESTINATION > SELECT_DATE > SUBMIT_QUERY > SELECT_RESULT > ENDPOINT_REACHED` 이 DROPDOWN 이면 **5**, FREE_TEXT 면 **2** 이다. 입력수단에 따라 depth 가 갈리는 것은 결함이 아니라 측정이다 (Δ9 why_this_is_correct)
- 미기록·`OTHER`·수단미기록 `MIXED` 는 채우지 않고 **보류**한다 → AMB-F12 로 올린다.

## 5. R12 — 거리 정규화 3종

- primary = `by_max_len`, 함께 저장 = ['by_sum_len', 'yujian_bo_2d_over_sum_plus_d']. 단일 보고에는 primary 만 쓴다. 나머지 둘은 저장되지만 스칼라로 emit 되지 않는다.

| pair | a | b | lev | **max(len) PRIMARY** | sum(len) 저장 | Yujian-Bo 저장 | 세 값 일치 |
|---|---|---|---|---|---|---|---|
| BND04_len1_different | `SELECT_FUNCTION` | `SELECT_RESULT` | 1 | **1** | 0.5 | 0.666667 | False |
| BND06_fully_disjoint_len3 | `OPEN_GLOBAL_MENU > SELECT_CATEGORY > SELECT_FUNCTION` | `INPUT_QUERY > SUBMIT_QUERY > SELECT_RESULT` | 3 | **1** | 0.5 | 0.666667 | False |
| BND07_prefix_vs_extension | `OPEN_GLOBAL_MENU > SELECT_FUNCTION` | `OPEN_GLOBAL_MENU > SELECT_FUNCTION > ENDPOINT_REACHED` | 1 | **0.333333** | 0.2 | 0.333333 | False |
| BND01_both_empty | `∅` | `∅` | 0 | **UNDEF** | UNDEF | UNDEF | True |
| FAM_SYN01_vs_SYN07 | `OPEN_GLOBAL_MENU > SELECT_CATEGORY > SELECT_FUNCTION > ENDPOINT_REACHED` | `SELECT_CATEGORY > OPEN_GLOBAL_MENU > SELECT_FUNCTION > ENDPOINT_REACHED` | 2 | **0.5** | 0.25 | 0.4 | False |

- 서로소 pair 에서 세 정규화는 **1.0 / 0.5 / 0.667** 로 갈린다. R12 가 AMB-F01 을 제기할 때 든 바로 그 값이다.
- 단일 스칼라는 `levenshtein_normalized_primary` 하나뿐이고 나머지 둘은 저장만 된다.
- **LCS similarity 는 여전히 primary 가 없다** (AMB-F02). R12 는 Levenshtein 만 확정했다.
- 0/0 은 여전히 UNDEF 다 (AMB-F10).
- 선언적 민감도: 군집·MDS 를 수행할 때는 Yujian-Bo 를 병기한다 (R12). 이 하네스는 clustering 을 구현하지 않으므로 그 조항은 미이행 상태로 남는다.

## 6. 변이 검사

| mutant | 대상 | 깨뜨리는 규범 | 잡힘 | 실패 check |
|---|---|---|---|---|
| MUT01_depth_counts_dismissal | `activation_depth` | 04 §5 / 03 §6 — popup dismiss must be excluded from depth | 예 | 2 |
| MUT02_menu_dependency_always_true | `menu_dependency` | 04 §5 — reveal token must actually be present | 예 | 8 |
| MUT03_levenshtein_length_only | `levenshtein` | 05 §2-E — edit distance must be order/content sensitive | 예 | 17 |
| MUT04_flow_step_count_drops_typing | `flow_step_count` | 04 §5 — typing/submit/auth are INCLUDED in flow_step_count (this is exactly where it differs from activation_d | 예 | 1 |
| MUT05_zero_denominator_as_zero | `_div` | AMB-F10 — 0/0 must not be reported as 0.0 (would read as 'identical flows') | 예 | 9 |
| MUT06_signature_collapse | `_sig` | 04 §3 — task_flow and experienced_flow must stay separate | 예 | 7 |
| MUT07_lcs_length_blind | `lcs_length` | 05 §2-E — LCS must reflect shared content; tier2 (LCS==0) depends on it | 예 | 12 |
| MUT08_depth_excludes_submit_query | `activation_depth` | Δ9 (T-A-V3-STEP1-006) — SUBMIT_QUERY 는 activation_depth 에 포함된다. 빼면 검색을 거쳐야 진입하는 서비스와 바로 누르는 서비스가 같은 depth 를 갖는 | 예 | 15 |
| MUT09_conditional_always_included | `activation_depth` | Δ9 CONDITIONAL — SELECT_ORIGIN/DESTINATION/DATE 는 fixture_input_mode 에 따라 갈린다. 무조건 포함하면 FREE_TEXT 로 타이핑한 값이 ac | 예 | 19 |
| MUT10_auth_gate_counts_as_activation | `activation_depth` | Δ9 — AUTH_GATE 는 '사용자 활성화가 아니라 마주친 상태'다 (기준 ①) | 예 | 4 |
| MUT11_distance_primary_is_sum_len | `R12_PRIMARY_NORMALIZATION` | R12 (T-A-V3-STEP1-007) — primary 는 max(len) 정규화다. sum(len) 은 비어 있지 않은 두 열에서 결코 1 에 도달하지 못해 차이를 과소보고한다 | 예 | 5 |

원복 증명: 모든 변이를 되돌린 뒤 실패 check 0건.

## 7. 닫힌 모호성

- **AMB-F01** (`normalized Levenshtein distance`) — T-A-V3-STEP1-007 .R12_sequence_distance_normalization 로 닫힘. 판정: primary = max(len(a), len(b)) 정규화. sum(len) 과 Yujian-Bo 는 함께 저장하되 단일 보고에는 primary 만 쓴다.
  - 하네스 이전: 세 후보를 병기하고 단일 'normalized' 스칼라를 emit 하지 않았다.
  - 하네스 이후: 세 후보를 여전히 전부 저장하고, `levenshtein_normalized_primary` 단일 스칼라를 by_max_len 으로 emit 한다.
  - 잔여: 군집·MDS 를 수행할 때 Yujian-Bo 를 병기하라는 R12 의 선언적 민감도 조항은 clustering 을 구현하지 않은 이 하네스의 범위 밖이다 (NOT_IMPLEMENTED 에 그대로 남는다).
- **AMB-F03** (`activation_depth`) — T-A-V3-STEP1-006 .general_criterion + .canonical_18_classification 로 닫힘. 판정: 셋 다 OUT. AUTH_GATE 는 '사용자 활성화가 아니라 마주친 상태'라 기준 ①에 걸리고, ENDPOINT_REACHED 는 '종결 표지이지 행위가 아니'며, ABSTAIN 은 '행위가 아니라 판정 유보'다. 즉 Δ9 는 기존 두 읽기 중 `activation_only` 쪽을 확정했다.
  - 하네스 이전: literal_all_but_excluded / activation_only 두 읽기를 병기하고, 둘이 갈리면 value=None 으로 보류했다.
  - 하네스 이후: Δ9 분류표로 단일 값을 emit 한다. 두 읽기 기록은 `readings` 에 감사 추적용으로만 남는다.
  - 잔여: AUTH_GATE 가 flow_step_count 에 auth encounter 로 포함된다는 것은 Δ9 가 재확인했다. `auth_gate_stage`(NONE/BEFORE_TASK_DISCOVERY/... + R13 UNDETERMINED) 판정은 Lane A 소관이며 여기서 구현하지 않는다.

## 8. 여전히 열린 모호성

| id | 변수 | 미결 쟁점 | severity |
|---|---|---|---|
| AMB-F02 | `LCS similarity` | LCS 길이를 무엇으로 나눠 similarity 로 만드는지 정의되지 않았다. L/max(len), L/min(len), 2L/(/a/+/b/) 중 어느 것인가? | HIGH |
| AMB-F04 | `flow_step_count` | (a) 어느 sequence 위에서 세는가 — task_flow_sequence 인가 experienced_flow_sequence 인가? DISMISS_OBSTRUCTION 은 포함/제외 어느 목록에도 없다. (b) ENDPOINT_REACHED / ABSTAIN 이 'task-intent action token' 인가? | HIGH |
| AMB-F05 | `menu_dependency` | reveal token 집합이 열려 있다('등', '계열'). SWITCH_TAB 이 reveal token 인가? nav_container_type 에는 TOP_DROPDOWN/INLINE_EXPAND 가 있어 tab 전환이 container reveal 로 읽힐 여지가 있다. | HIGH |
| AMB-F06 | `nav_container_depth` | token sequence 만으로는 계산 불가능하다. 'task control 노출' 시점을 표시하는 token 이 canonical 18 에 없다. 또한 §5 는 'nested reveal', §4 는 'menu/drawer expansion' 이라 두 문구가 nesting 요구 여부에서 어긋난다. | HIGH |
| AMB-F07 | `ABSTAIN token 취급` | ABSTAIN 이 sequence 안에 들어왔을 때 (a) derived count 에 세는가, (b) 그 sequence 를 distance/ signature 모집단에 넣는가, (c) 넣는다면 ABSTAIN 을 하나의 심볼로 취급하는가 wildcard 로 취급하는가? | HIGH |
| AMB-F08 | `distance base sequence` | sequence signature / Levenshtein / LCS 를 task_flow_sequence 위에서 계산하는가 experienced_flow_sequence 위에서 계산하는가? §2-E 는 base 를 말하지 않는다. | MEDIUM |
| AMB-F09 | `menu_dependency 'endpoint 전' 경계` | ENDPOINT_REACHED 가 없는 terminal(AUTH_GATE / ABSTAIN / BLOCKED)에서 'endpoint 전' prefix 는 어디까지인가? | LOW |
| AMB-F10 | `빈 sequence 의 normalized distance` | 두 sequence 가 모두 빈 경우 분모가 0 이다. 0.0(완전 동일)으로 볼 것인가 undefined 로 볼 것인가? | LOW |
| AMB-F11 | `task_flow vs experienced_flow 의 구조적 관계` | §3 예시는 experienced = task + dismissal 삽입 관계를 보이지만, 'DISMISS_OBSTRUCTION 을 제거하면 반드시 task_flow 와 같아야 한다'를 규범으로 명시하지 않았다. | MEDIUM |
| AMB-F12 | `activation_depth CONDITIONAL 3종 × fixture_input_mode` | Δ9 는 DROPDOWN/MAP_PAN→포함, FREE_TEXT→제외, MIXED→'실제로 사용한 수단 기준' 만 정했다. (a) `OTHER` 는 어느 쪽인가? (b) MIXED 에서 '실제로 사용한 수단'을 토큰 단위로 기록하는 필드가 R5 스키마(`fixture_input_mode` 단일 값)에 없다. (c) fixture_input_mode 가 아예 기록되지 않은 관측의 CONDITI | HIGH |

**AMB-F12 는 이 수렴에서 새로 드러난 것이다.** Δ9 가 CONDITIONAL 규칙을 세우면서 `OTHER`·미기록·수단미기록 `MIXED` 를 남겼다. 채우지 않고 올린다.

## 9. 여기서 하지 않은 것

- **R13 auth_gate_stage UNDETERMINED** (소관: Lane A) — R13 은 auth_gate_stage enum 확장이다. Lane F 는 token 열만 다루며 auth_gate_stage 를 산출하지 않는다(NOT_IMPLEMENTED 에 기존 등재). **Lane F 소관은 AUTH_GATE 토큰의 depth 귀속뿐이고, 그것은 Δ9 가 OUT 으로 확정했다.**
- **nav_container_type / reveal_direction** (소관: Lane S) — T-B-FC-013 이 방향을 별도 변수로 확정했으나 그 변수들은 Lane F 의 산출물이 아니다.
- **cross-lane 중복 변수 수렴검사 (nav_container_depth · menu_dependency)** (소관: 다른 워커) — converge_dup_vars.py 는 이 작업의 수정 대상이 아니다. 읽지도 쓰지도 않았다.

## 10. 한계

- REAL 접속 0건. MAIN50 미수집. 여기의 모든 수치는 합성 fixture 산출물이며 어떤 서비스에 대한 관측도 아니다.
- **Δ9 의 submit 조항은 Lane F 의 계수를 바꾸지 않았다.** Lane F 는 수렴 전에도 SUBMIT_QUERY 를 제외하지 않았기 때문이다. 값을 바꾼 것은 같은 티켓의 AMB-F03 확정이다. submit_query_effect 표의 '수렴 전' 열은 그 사실을 드러내기 위한 것이지 Lane F 가 submit 을 빼고 있었다는 뜻이 아니다.
- fixture 는 워커가 티켓을 읽고 만든 것이다. 티켓을 오독했다면 fixture 도 같이 틀린다. 변이 검사는 구현 오류만 잡고 해석 오류는 못 잡는다 (R14 weakest-link, A 가 구속력 있는 한계로 채택).
- AMB-F12 는 이 수렴 과정에서 **새로 드러난** 모호성이다. Δ9 가 CONDITIONAL 규칙을 세우면서 OTHER·미기록·수단미기록 MIXED 를 남겼다. 채우지 않고 올린다.
- AMB-F02(LCS similarity 분모)·F04(flow_step_count base/terminal)·F05(reveal token 집합)·F06(nav_container_depth)·F07(b)(c)·F08(distance base)·F09·F10·F11 은 Δ9·R12 가 다루지 않았다. 닫히지 않았다.
- R12 의 '군집·MDS 시 Yujian-Bo 병기' 조항은 clustering 미구현이라 이 하네스에서 이행되지 않는다.
- family n=10 이 독립단위다. 이 run 의 45 pair 는 distance matrix 의 cell 이며 n=45 가 아니다.
- 본 하네스는 GO/NO-GO 를 내지 않는다. verdict 는 계산기가 Δ9·R12 로 수렴했는지에 대한 것이지 연구 결론이 아니다.

## 11. 재현

```bash
/home/sieg/projects-wsl/ProjectFinal/.venv/bin/python \
  /home/sieg/projects-wsl/ProjectFinal/.agent_worktrees/claude_d_research/research/landing_accessibility/research_d/tools/v3_harness/lane_f_flow_depth.py
```
