# LANE F — Flow Topology / Depth 하네스 결과

- **verdict**: `READY_WITH_AMBIGUITY`
- 생성: 2026-08-27T17:53:30.718054+00:00
- 데이터: **합성 fixture 전용**. REAL 접속·MAIN50·mart/raw evidence·gold·holdout 없음.
- 독립단위: `service × frozen task` (family n=10). **이 run 의 45 pair 는 distance matrix 의 cell 이며 n=45 가 아니다.**


## 1. 검증 요약

- fixture check: 202/202 pass
- mutation test: 7/7 개 변이가 fixture 에 잡힘, 미검출 []
- 원복 증명(restore proof) 실패 check: 0
- 미해결 정의 모호성: 11건 → verdict 상한이 `READY_WITH_AMBIGUITY`

## 2. 반례 탐지기 3종

모든 술어는 정수/토큰열에 대한 **정확한 구조적 상등·부등**이다. threshold·cut-off·composite score 없음.

### D1 — depth 는 같은데 flow 가 다르다
- tier1 술어: `activation_depth[a] == activation_depth[b] AND ordered_tokens[a] != ordered_tokens[b]`
- tier2 술어: `tier1 AND lcs_length == 0` (‘전혀 다르다’를 임계값이 아니라 LCS==0 이라는 구조 사실로 렌더)
- positive (합성 family 45 cell 기준):
  - `reading=literal_all_but_excluded|base=task` → 18
  - `reading=literal_all_but_excluded|base=experienced` → 20
  - `reading=activation_only|base=task` → 18
  - `reading=activation_only|base=experienced` → 20
- tier2 positive: 1건 (SYN02_search_item, SYN04_tab_auth_terminal)
- **negative(잡히면 안 되는 것)**: depth 는 같지만 flow 가 동일한 3건 — 모두 미검출 확인

### D2 — depth 차이는 0 인데 sequence 거리는 0 이 아니다
- 술어: `depth_diff == 0 under EVERY depth reading AND levenshtein_raw > 0`
- positive: base=task 18건, base=experienced 20건 (합 38 cell-base 조합)
- 최대 raw Levenshtein = 5 (‘큰’의 정의를 만들지 않고 순위통계로만 보고)
- negative: 52건 — 거리 0 인 동일 flow, 그리고 거리는 크지만 depth 가 다른 pair 는 모두 미검출
- 정직한 한계: levenshtein_raw == 0 iff the ordered token lists are identical, so on a fixed base this positive set is exactly D1-tier1's positive set restricted to cells where EVERY depth reading ties. No threshold was introduced to separate the two detectors; they differ in what they report (structure vs magnitude), not in what they select.

### D3 — modal 때문에 experienced flow 만 길어진다
- 술어: `task signature EQUAL AND experienced signature DIFFERS` + 귀속검사 `experienced_a minus DISMISS_OBSTRUCTION == experienced_b minus DISMISS_OBSTRUCTION`
- positive 2건: (SYN01_menu_category, SYN05_modal_then_menu) task_dist=0 exp_dist=1, (SYN05_modal_then_menu, SYN06_no_modal_twin) task_dist=0 exp_dist=1
- negative 43건 (modal 없음 / 양쪽 동일 modal / task_flow 자체가 다름) — 모두 미검출
- 귀속 불가 bucket: 0건 (directed case DC13 에서 별도 검증)
- 이 탐지기는 `activation_depth` 가 dismissal 에 불변임을 동시에 확인한다 → **depth 는 modal 부담을 보지 못한다**.

## 3. 경계 케이스 표 (정답 대조)

| case | a | b | lev | LCS | lev/max | lev/sum | Yujian-Bo | LCS/max | LCS/min | Dice | 정답일치 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| BND01_both_empty | `∅` | `∅` | 0 | 0 | UNDEF | UNDEF | UNDEF | UNDEF | UNDEF | UNDEF | OK |
| BND02_empty_vs_len1 | `∅` | `ENDPOINT_REACHED` | 1 | 0 | 1 | 1 | 1 | 0 | UNDEF | 0 | OK |
| BND03_len1_identical | `SELECT_FUNCTION` | `SELECT_FUNCTION` | 0 | 1 | 0 | 0 | 0 | 1 | 1 | 1 | OK |
| BND04_len1_different | `SELECT_FUNCTION` | `SELECT_RESULT` | 1 | 0 | 1 | 0.5 | 0.666667 | 0 | 0 | 0 | OK |
| BND05_fully_identical_len4 | `OPEN_GLOBAL_MENU > SELECT_CATEGORY > SELECT_FUNCTION > ENDPOINT_REACHED` | `OPEN_GLOBAL_MENU > SELECT_CATEGORY > SELECT_FUNCTION > ENDPOINT_REACHED` | 0 | 4 | 0 | 0 | 0 | 1 | 1 | 1 | OK |
| BND06_fully_disjoint_len3 | `OPEN_GLOBAL_MENU > SELECT_CATEGORY > SELECT_FUNCTION` | `INPUT_QUERY > SUBMIT_QUERY > SELECT_RESULT` | 3 | 0 | 1 | 0.5 | 0.666667 | 0 | 0 | 0 | OK |
| BND07_prefix_vs_extension | `OPEN_GLOBAL_MENU > SELECT_FUNCTION` | `OPEN_GLOBAL_MENU > SELECT_FUNCTION > ENDPOINT_REACHED` | 1 | 2 | 0.333333 | 0.2 | 0.333333 | 0.666667 | 1 | 0.8 | OK |

주: `UNDEF` 는 분모 0 이다. **0.0 으로 채우지 않았다** (AMB-F10). 0.0 으로 채우면 flow 미평가 unit 이 heatmap 에서 ‘완전 동일’로 오독된다.

## 4. 파생값 fixture 표

| fixture | task_flow | act_depth (literal / activation_only) | flow_step_count (task incl/excl · exp incl/excl) | menu_dep | 비고 |
|---|---|---|---|---|---|
| SYN01_menu_category | `OPEN_GLOBAL_MENU > SELECT_CATEGORY > SELECT_FUNCTION > ENDPOINT_REACHED` | 4 / 3 | 4/3 · 4/3 | True |  |
| SYN02_search_item | `INPUT_QUERY > SUBMIT_QUERY > SELECT_RESULT > OPEN_ITEM_DETAIL > ENDPOINT_REACHED` | 4 / 3 | 5/4 · 5/4 | False |  |
| SYN03_tab_accordion | `SWITCH_TAB > EXPAND_ACCORDION > OPEN_PLACE_DETAIL > ENDPOINT_REACHED` | 4 / 3 | 4/3 · 4/3 | True |  |
| SYN04_tab_auth_terminal | `SWITCH_TAB > SELECT_CATEGORY > SELECT_FUNCTION > AUTH_GATE` | 4 / 3 | 4/4 · 4/4 | WITHHELD | menu_dep 읽기 불일치 |
| SYN05_modal_then_menu | `OPEN_GLOBAL_MENU > SELECT_CATEGORY > SELECT_FUNCTION > ENDPOINT_REACHED` | 4 / 3 | 4/3 · 5/4 | True |  |
| SYN06_no_modal_twin | `OPEN_GLOBAL_MENU > SELECT_CATEGORY > SELECT_FUNCTION > ENDPOINT_REACHED` | 4 / 3 | 4/3 · 4/3 | True |  |
| SYN07_reordered | `SELECT_CATEGORY > OPEN_GLOBAL_MENU > SELECT_FUNCTION > ENDPOINT_REACHED` | 4 / 3 | 4/3 · 4/3 | True |  |
| SYN08_transport_slots | `SELECT_ORIGIN > SELECT_DESTINATION > SELECT_DATE > SUBMIT_QUERY > SELECT_RESULT > ENDPOINT_REACHED` | 6 / 5 | 6/5 · 6/5 | False |  |
| SYN09_abstain | `OPEN_GLOBAL_MENU > ABSTAIN` | 2 / 1 | 2/1 · 2/1 | True | ABSTAIN 포함 → 비해석 |
| SYN10_empty | `∅` | 0 / 0 | 0/0 · 0/0 | False |  |

## 5. ABSTAIN 취급

- `ABSTAIN` 은 canonical 18 에 있으므로 **invalid token 이 아니다**. 그러나 derived count·distance 에서의 취급을 codebook 이 정하지 않았다 (AMB-F07).
- 하네스 동작: `abstain_present=true` 표시 → 해당 observation 의 `derived_values_interpretable=false` → 그 observation 이 들어간 모든 pair cell 의 `interpretable=false`.
- 값 자체는 두 읽기(포함/제외)로 계산해 두되 **확정값으로 승격하지 않는다**. 임의 판단하지 않았다.

## 6. AMBIGUOUS_DEFINITION (채우지 않고 올림)

| id | 변수 | 미결 쟁점 | severity |
|---|---|---|---|
| AMB-F01 | `normalized Levenshtein distance` | 정규화 분모가 정의되지 않았다. max(len(a),len(b)) 인가, len(a)+len(b) 인가, 아니면 Yujian-Bo 2d/(|a|+|b|+d) 인가? | HIGH |
| AMB-F02 | `LCS similarity` | LCS 길이를 무엇으로 나눠 similarity 로 만드는지 정의되지 않았다. L/max(len), L/min(len), 2L/(|a|+|b|) 중 어느 것인가? | HIGH |
| AMB-F03 | `activation_depth` | AUTH_GATE / ENDPOINT_REACHED / ABSTAIN 이 'state-changing activation token' 에 포함되는가? 제외 목록(scroll/typing/passive/dismiss)에 없으므로 문자 그대로 읽으면 포함이고, '도달한다/충족된다/판정하지 않는다' 라는 토큰 정의상 사용자의 activation 이 아니므로 의미상 읽으면 제외다. | HIGH |
| AMB-F04 | `flow_step_count` | (a) 어느 sequence 위에서 세는가 — task_flow_sequence 인가 experienced_flow_sequence 인가? DISMISS_OBSTRUCTION 은 포함/제외 어느 목록에도 없다. (b) ENDPOINT_REACHED / ABSTAIN 이 'task-intent action token' 인가? | HIGH |
| AMB-F05 | `menu_dependency` | reveal token 집합이 열려 있다('등', '계열'). SWITCH_TAB 이 reveal token 인가? nav_container_type 에는 TOP_DROPDOWN/INLINE_EXPAND 가 있어 tab 전환이 container reveal 로 읽힐 여지가 있다. | HIGH |
| AMB-F06 | `nav_container_depth` | token sequence 만으로는 계산 불가능하다. 'task control 노출' 시점을 표시하는 token 이 canonical 18 에 없다. 또한 §5 는 'nested reveal', §4 는 'menu/drawer expansion' 이라 두 문구가 nesting 요구 여부에서 어긋난다. | HIGH |
| AMB-F07 | `ABSTAIN token 취급` | ABSTAIN 이 sequence 안에 들어왔을 때 (a) derived count 에 세는가, (b) 그 sequence 를 distance/ signature 모집단에 넣는가, (c) 넣는다면 ABSTAIN 을 하나의 심볼로 취급하는가 wildcard 로 취급하는가? | HIGH |
| AMB-F08 | `distance base sequence` | sequence signature / Levenshtein / LCS 를 task_flow_sequence 위에서 계산하는가 experienced_flow_sequence 위에서 계산하는가? §2-E 는 base 를 말하지 않는다. | MEDIUM |
| AMB-F09 | `menu_dependency 'endpoint 전' 경계` | ENDPOINT_REACHED 가 없는 terminal(AUTH_GATE / ABSTAIN / BLOCKED)에서 'endpoint 전' prefix 는 어디까지인가? | LOW |
| AMB-F10 | `빈 sequence 의 normalized distance` | 두 sequence 가 모두 빈 경우 분모가 0 이다. 0.0(완전 동일)으로 볼 것인가 undefined 로 볼 것인가? | LOW |
| AMB-F11 | `task_flow vs experienced_flow 의 구조적 관계` | §3 예시는 experienced = task + dismissal 삽입 관계를 보이지만, 'DISMISS_OBSTRUCTION 을 제거하면 반드시 task_flow 와 같아야 한다'를 규범으로 명시하지 않았다. | MEDIUM |

가장 중요한 것은 **AMB-F01 정규화 분모**다. codebook·analysis plan 어디에도 분모가 없다. 하네스는 `max(len)` / `sum(len)` / Yujian-Bo 세 후보값을 병기만 하며 단일 스칼라를 emit 하지 않는다. 같은 pair 가 1.0 / 0.5 / 0.667 로 갈린다(BND04·BND06).

## 7. 구현하지 않은 것

- **nav_container_depth (single value)** — AMB-F06 — token sequence 만으로 'task control 노출' 시점을 알 수 없다. candidate 3종만 병기.
- **auth_gate_stage** — BEFORE_TASK_DISCOVERY/AFTER_TASK_SELECT/AT_ENDPOINT 판정은 fact_flow_step 의 endpoint_signal/discovery evidence 를 요구한다. token 열만으로 확정 불가 — Lane F 범위 밖으로 두고 조작화하지 않음.
- **NED / IED / MPFED legacy compatibility fields** — 02 §7 의 legacy materialization 규칙이며 v3 codebook 이 재정의하지 않았다. v2.1 정의를 여기서 재구성하면 새 조작화가 된다.
- **sequence cluster / heatmap (05 §2-E 4번째 항목)** — clustering 은 linkage·거리 선택이 필요하고 그 선택이 AMB-F01/F02 미해결에 종속된다. 거리행렬만 산출.
- **family-level median/IQR/range (05 §2-F, §4)** — MAIN50 미수집. 합성 fixture 로 기술통계를 내면 실측처럼 오독될 수 있어 산출하지 않음.
- **any threshold / cut-off / composite score** — Director 금지 + 05 §3 가중합 단일 score 금지. detector 는 전부 정확한 구조적 상등/부등 술어만 사용.
- **REAL target access, gold label, holdout, GO/NO-GO verdict** — Lane F 계약상 금지.

## 8. 한계

- MAIN50 미수집. 여기의 모든 수치는 합성 fixture 산출물이며 어떤 서비스에 대한 관측도 아니다.
- fixture 는 계산기가 정의를 지키는지만 보인다. 실제 MAIN50 sequence 의 token 분포·길이·terminal 구성이 fixture 와 다르면 detector 의 산출 규모는 달라진다. fixture 는 대표성 주장이 아니다.
- detector 는 존재증명이다. '동일 depth 에서 flow 가 갈리는 pair 가 존재한다'는 구조적 사실을 보일 뿐, 그 빈도·효과크기·모집단 일반화를 말하지 않는다.
- AMB-F01/F02 가 미해결인 한 normalized distance heatmap(05 §8)은 단일 그림으로 확정 발행할 수 없다. 분모 선택이 pair 순위를 바꾼다(BND07: 0.667 vs 1.0 vs 0.8).
- AMB-F03/F04 가 미해결인 한 activation depth 의 median/IQR(05 §2-F) 절대값은 확정할 수 없다. 단, depth '차이'는 두 읽기에서 동일하게 나오는 경우가 많아 D1/D2 는 robust 하게 판정된다(본 run 에서 18=18).
- AMB-F06 때문에 nav_container_depth 는 산출하지 못했다. token 열이 아니라 fact_flow_step 의 nav_container_type/reveal evidence 가 있어야 계산 가능하다.
- Levenshtein 은 모든 token 치환 비용을 1 로 둔다. token 간 의미거리(예: OPEN_GLOBAL_MENU↔OPEN_LOCAL_MENU 가 OPEN_GLOBAL_MENU↔INPUT_QUERY 보다 가깝다)를 codebook 이 정의하지 않았으므로 가중치를 만들지 않았다.
- D1-tier1 과 D2 는 임계값 없이는 동일 술어다. 이를 다르게 보이게 하려면 'large' 컷오프가 필요하고, 그것은 금지 사항이라 만들지 않았다.
- 본 하네스는 GO/NO-GO 를 내지 않는다. verdict 는 계산기 준비 상태에 대한 것이지 연구 결론이 아니다.

## 9. 재현

```bash
/home/sieg/projects-wsl/ProjectFinal/.venv/bin/python \
  /home/sieg/projects-wsl/ProjectFinal/.agent_worktrees/claude_d_research/research/landing_accessibility/research_d/tools/v3_harness/lane_f_flow_depth.py
```

SSOT sha256 대조: MANIFEST = `1735c956d4a3461ee9eb2543c5c474942887bcbd117f5876d5486207f2f72e0a` (계약값 `1735c956d4a3461ee9eb2543c5c474942887bcbd117f5876d5486207f2f72e0a`)
