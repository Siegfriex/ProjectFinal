# Lane S — R7 `entry_zone` 수렴

- verdict: **CONVERGED_WITH_AMBIGUITY**
- 권위: `/home/sieg/projects-wsl/ProjectFinal/.agent_bus/landing_v2/tickets/T-A-V3-STEP1-003.json` → `R7_entry_zone_operational_definition`
- 확정 시각(KST): `2026-08-28T02:58:00+09:00` · 확정 시점 관측 수: **0건**
- 사전등록: 관측 0건 상태에서 사전등록됨 — ticket.preregistration_status: 'REAL 접속 누적 0건. 어떤 flow 도 관측되지 않았다. 따라서 이 확정들은 전부 result-blind 다.'
- 기록 위치: V3_0_1_SUCCESSOR_DELTA.md Δ8 (SSOTV3 원본은 수정하지 않는다)
- data status: **NO_REAL_DATA — REAL 접속 누적 0건; synthetic fixtures only**

## 1. 무엇이 바뀌었나

Lane S 는 `entry_zone` 유도를 **거부**하고 있었다. SSOTV3 04 §6 에 x/y 절단값이 없었기 때문이고,
그 상태를 `D-V3-FINDING-007` 로 올렸다. A 가 `T-A-V3-STEP1-003` R7 로 절단값을 확정했으므로
이제 유도한다. 확정은 **관측 0건 상태**에서 이뤄졌고, 이 수렴 작업도 실측 없이 fixture 로만 했다.

fixture 용 1/3 등분 정책(`FIXTURE_ONLY_NOT_SSOT`)은 **지우지 않았다**. 대조군으로 쓴다 —
두 정책이 같은 답을 주는지는 가정이 아니라 확인의 대상이다(§4).

전사 검증: 모듈에 박아둔 R7 원문이 티켓 파일과 **바이트 동일**한가 → `True` (ticket sha256 `ea09d3985c71a52b779253bc7c9a6336d5926038c9a83d2c2759264f46e9878d`)

## 2. 경계값 fixture (37/37)

R7 이 이름 붙인 절단값을 **정확히** 밟고, 그 양옆 `nextafter` 한 칸까지 고정했다.

| fixture | 기대 | 관측 | 통과 |
|---|---|---|---|
| R7-B y=1/3 EXACT (x=0.10) | `('MID', 'OK')` | `('MID', 'OK')` | ✓ |
| R7-B y=2/3 EXACT (x=0.10) | `('BOTTOM', 'OK')` | `('BOTTOM', 'OK')` | ✓ |
| R7-B y just below 1/3 | `('TOP_LEFT', 'OK')` | `('TOP_LEFT', 'OK')` | ✓ |
| R7-B y just above 1/3 | `('MID', 'OK')` | `('MID', 'OK')` | ✓ |
| R7-B y just below 2/3 | `('MID', 'OK')` | `('MID', 'OK')` | ✓ |
| R7-B y just above 2/3 | `('BOTTOM', 'OK')` | `('BOTTOM', 'OK')` | ✓ |
| R7-B x=1/3 EXACT (y=0.10, TOP band) | `('TOP_CENTER', 'OK')` | `('TOP_CENTER', 'OK')` | ✓ |
| R7-B x=2/3 EXACT (y=0.10, TOP band) | `('TOP_RIGHT', 'OK')` | `('TOP_RIGHT', 'OK')` | ✓ |
| R7-B x just below 1/3 | `('TOP_LEFT', 'OK')` | `('TOP_LEFT', 'OK')` | ✓ |
| R7-B x just above 1/3 | `('TOP_CENTER', 'OK')` | `('TOP_CENTER', 'OK')` | ✓ |
| R7-B x just below 2/3 | `('TOP_CENTER', 'OK')` | `('TOP_CENTER', 'OK')` | ✓ |
| R7-B x just above 2/3 | `('TOP_RIGHT', 'OK')` | `('TOP_RIGHT', 'OK')` | ✓ |
| R7-B x=1/3 EXACT in MID band -> plain MID | `('MID', 'OK')` | `('MID', 'OK')` | ✓ |
| R7-B x=2/3 EXACT in BOTTOM band -> plain BOTTOM | `('BOTTOM', 'OK')` | `('BOTTOM', 'OK')` | ✓ |
| R7-B the exact point (1/3, 1/3) | `('MID', 'OK')` | `('MID', 'OK')` | ✓ |
| R7-B corner (0.0, 0.0) | `('TOP_LEFT', 'OK')` | `('TOP_LEFT', 'OK')` | ✓ |
| R7-B corner (1.0, 0.0) | `('TOP_RIGHT', 'OK')` | `('TOP_RIGHT', 'OK')` | ✓ |
| R7-B corner (0.0, 1.0) | `('BOTTOM', 'OK')` | `('BOTTOM', 'OK')` | ✓ |
| R7-B corner (1.0, 1.0) | `('BOTTOM', 'OK')` | `('BOTTOM', 'OK')` | ✓ |
| R7-B out-of-range x slightly negative, TOP band | `(None, 'AMBIGUOUS_OUT_OF_UNIT_RANGE')` | `(None, 'AMBIGUOUS_OUT_OF_UNIT_RANGE')` | ✓ |
| R7-B out-of-range x slightly >1, TOP band | `(None, 'AMBIGUOUS_OUT_OF_UNIT_RANGE')` | `(None, 'AMBIGUOUS_OUT_OF_UNIT_RANGE')` | ✓ |
| R7-B out-of-range x far negative, TOP band | `(None, 'AMBIGUOUS_OUT_OF_UNIT_RANGE')` | `(None, 'AMBIGUOUS_OUT_OF_UNIT_RANGE')` | ✓ |
| R7-B out-of-range y slightly negative | `(None, 'AMBIGUOUS_OUT_OF_UNIT_RANGE')` | `(None, 'AMBIGUOUS_OUT_OF_UNIT_RANGE')` | ✓ |
| R7-B out-of-range y slightly >1 | `(None, 'AMBIGUOUS_OUT_OF_UNIT_RANGE')` | `(None, 'AMBIGUOUS_OUT_OF_UNIT_RANGE')` | ✓ |
| R7-B out-of-range y far above 1 | `(None, 'AMBIGUOUS_OUT_OF_UNIT_RANGE')` | `(None, 'AMBIGUOUS_OUT_OF_UNIT_RANGE')` | ✓ |
| R7-B out-of-range x, MID band (x never consulted) | `('MID', 'OK_UNCONSULTED_AXIS_OUT_OF_RANGE')` | `('MID', 'OK_UNCONSULTED_AXIS_OUT_OF_RANGE')` | ✓ |
| R7-B out-of-range x, BOTTOM band (x never consulted) | `('BOTTOM', 'OK_UNCONSULTED_AXIS_OUT_OF_RANGE')` | `('BOTTOM', 'OK_UNCONSULTED_AXIS_OUT_OF_RANGE')` | ✓ |
| R7-B both coordinates MISSING | `(None, 'MISSING_COORDINATES')` | `(None, 'MISSING_COORDINATES')` | ✓ |
| R7-B x MISSING only | `(None, 'MISSING_COORDINATES')` | `(None, 'MISSING_COORDINATES')` | ✓ |
| R7-B y MISSING only | `(None, 'MISSING_COORDINATES')` | `(None, 'MISSING_COORDINATES')` | ✓ |
| R7-B record_anyway raw coords preserved (plain geometry) | `(0.1, 0.1)` | `(0.1, 0.1)` | ✓ |
| R7-B record_anyway raw coords preserved (unconsulted out-of-range) | `(1.4, 0.5)` | `(1.4, 0.5)` | ✓ |
| R7-B record_anyway raw coords preserved (ambiguous out-of-range) | `(-0.001, 0.1)` | `(-0.001, 0.1)` | ✓ |
| R7-B record_anyway raw coords preserved (missing) | `(None, None)` | `(None, None)` | ✓ |
| R7-B MID/BOTTOM never gain an x split | `['BOTTOM', 'MID', 'TOP_CENTER', 'TOP_LEFT', 'TOP_RIGHT']` | `['BOTTOM', 'MID', 'TOP_CENTER', 'TOP_LEFT', 'TOP_RIGHT']` | ✓ |
| R7-B geometry alone never emits FLOATING/DRAWER | `[]` | `[]` | ✓ |
| R7-B every emitted label is in the 04 §4 enum | `['VALID']` | `['VALID']` | ✓ |

### 2.1 R7 이 자기 자신과 어긋나는 지점 (AMB-S14)

- 읽기 A (구현함): R7 thresholds tables + `경계값은 하한 포함·상한 배제([a, b))로 통일한다` -> a value on a cut goes UPWARD (y=1/3 -> MID). IMPLEMENTED.
- 읽기 B (구현 안 함): R7 `정확히 1/3 인 점은 TOP 이자 TOP_CENTER 다` -> y=1/3 would be TOP. NOT implemented; recorded. Applied only to the point the clause names, not generalized into a `(a, b]` convention.
- 왜 A 인가: Two of R7's three statements (the y inequality table and the general half-open rule) give MID at y=1/3; only the trailing example gives TOP, and that example contradicts the general rule it is appended to. The x axis is unaffected — both readings give TOP_CENTER at x=1/3. Note the clause is self-inconsistent even on its own terms: to make y=1/3 TOP the cut must belong DOWNWARD, but to make x=1/3 TOP_CENTER the cut must belong UPWARD.
- 두 읽기가 갈리는 probe: **3/10**

| x | y | 읽기 A | 읽기 B | 동일 |
|---|---|---|---|---|
| 0.100000 | 0.333333 | `MID` | `TOP_LEFT` | **아니오** |
| 0.333333 | 0.333333 | `MID` | `TOP_CENTER` | **아니오** |
| 0.900000 | 0.333333 | `MID` | `TOP_RIGHT` | **아니오** |
| 0.333333 | 0.100000 | `TOP_CENTER` | `TOP_CENTER` | 예 |
| 0.666667 | 0.100000 | `TOP_RIGHT` | `TOP_RIGHT` | 예 |
| 0.100000 | 0.666667 | `BOTTOM` | `BOTTOM` | 예 |
| 0.666667 | 0.666667 | `BOTTOM` | `BOTTOM` | 예 |
| 0.100000 | 0.100000 | `TOP_LEFT` | `TOP_LEFT` | 예 |
| 0.900000 | 0.900000 | `BOTTOM` | `BOTTOM` | 예 |
| 0.500000 | 0.500000 | `MID` | `MID` | 예 |

이 선택은 **내 판정이 아니다**. 어느 읽기가 A 의 의도인지는 A 가 정한다. 나는 구현한 쪽과
구현하지 않은 쪽을 둘 다 계산해서 나란히 남겼다.

## 3. Precedence fixture (39/39)

R7: `FLOATING 과 DRAWER 는 기하보다 우선한다` · `둘 다 해당하면 DRAWER 가 우선한다`.
양방향으로 봤다 — override 가 기하를 이기는지, 그리고 조건이 없을 때 override 가 **안 걸리는지**.

| fixture | 기대 | 관측 | 통과 |
|---|---|---|---|
| R7-P no override -> geometry TOP_LEFT | `('TOP_LEFT', 'OK')` | `('TOP_LEFT', 'OK')` | ✓ |
| R7-P no override -> geometry BOTTOM | `('BOTTOM', 'OK')` | `('BOTTOM', 'OK')` | ✓ |
| R7-P geometry TOP_LEFT + FLOATING(fixed) -> FLOATING | `('FLOATING', 'OK')` | `('FLOATING', 'OK')` | ✓ |
| R7-P geometry BOTTOM + FLOATING(sticky) -> FLOATING | `('FLOATING', 'OK')` | `('FLOATING', 'OK')` | ✓ |
| R7-P geometry TOP_LEFT + DRAWER -> DRAWER | `('DRAWER', 'OK')` | `('DRAWER', 'OK')` | ✓ |
| R7-P geometry BOTTOM + DRAWER -> DRAWER | `('DRAWER', 'OK')` | `('DRAWER', 'OK')` | ✓ |
| R7-P FLOATING and DRAWER both -> DRAWER (TOP geometry) | `('DRAWER', 'OK')` | `('DRAWER', 'OK')` | ✓ |
| R7-P FLOATING and DRAWER both -> DRAWER (BOTTOM geometry) | `('DRAWER', 'OK')` | `('DRAWER', 'OK')` | ✓ |
| R7-P precedence order is literally DRAWER before FLOATING | `['DRAWER', 'FLOATING']` | `['DRAWER', 'FLOATING']` | ✓ |
| R7-P position static -> not FLOATING | `('TOP_LEFT', 'OK')` | `('TOP_LEFT', 'OK')` | ✓ |
| R7-P position relative -> not FLOATING | `('TOP_LEFT', 'OK')` | `('TOP_LEFT', 'OK')` | ✓ |
| R7-P sticky but NOT fixed to viewport -> not FLOATING | `('TOP_LEFT', 'OK')` | `('TOP_LEFT', 'OK')` | ✓ |
| R7-P container present but no reveal required -> not DRAWER | `('TOP_LEFT', 'OK')` | `('TOP_LEFT', 'OK')` | ✓ |
| R7-P sticky, flow-clause UNKNOWN -> undetermined not guessed | `(None, 'AMBIGUOUS_FLOATING_UNDETERMINED')` | `(None, 'AMBIGUOUS_FLOATING_UNDETERMINED')` | ✓ |
| R7-P fixed, flow-clause UNKNOWN -> undetermined not guessed | `(None, 'AMBIGUOUS_FLOATING_UNDETERMINED')` | `(None, 'AMBIGUOUS_FLOATING_UNDETERMINED')` | ✓ |
| R7-P in reveal container, menu_dependency UNKNOWN -> undetermined | `(None, 'AMBIGUOUS_DRAWER_UNDETERMINED')` | `(None, 'AMBIGUOUS_DRAWER_UNDETERMINED')` | ✓ |
| R7-P in reveal container but menu_dependency=0 -> inconsistent, not DRAWER | `(None, 'AMBIGUOUS_DRAWER_UNDETERMINED')` | `(None, 'AMBIGUOUS_DRAWER_UNDETERMINED')` | ✓ |
| R7-P DRAWER confirmed outranks an UNDETERMINED FLOATING | `('DRAWER', 'OK')` | `('DRAWER', 'OK')` | ✓ |
| R7-P confirmed FLOATING must NOT overtake an undetermined DRAWER | `(None, 'AMBIGUOUS_DRAWER_UNDETERMINED')` | `(None, 'AMBIGUOUS_DRAWER_UNDETERMINED')` | ✓ |
| R7-P same, with BOTTOM geometry underneath | `(None, 'AMBIGUOUS_DRAWER_UNDETERMINED')` | `(None, 'AMBIGUOUS_DRAWER_UNDETERMINED')` | ✓ |
| R7-P undetermined DRAWER is reported as blocking, not as absence | `True` | `True` | ✓ |
| R7-P DRAWER ruled OUT lets a confirmed FLOATING through | `('FLOATING', 'OK')` | `('FLOATING', 'OK')` | ✓ |
| R7-P unobserved structural fields are reported, not assumed | `{'computed_position': False, 'out_of_flow_fixed_to_viewport': False, 'in_reveal_required_nav_container': False, 'menu_dependency': False}` | `{'computed_position': False, 'out_of_flow_fixed_to_viewport': False, 'in_reveal_required_nav_container': False, 'menu_dependency': False}` | ✓ |
| R7-P DRAWER with out-of-range coordinates still DRAWER | `('DRAWER', 'OK')` | `('DRAWER', 'OK')` | ✓ |
| R7-P FLOATING with MISSING coordinates still FLOATING | `('FLOATING', 'OK')` | `('FLOATING', 'OK')` | ✓ |
| R7-P record_anyway holds under an override | `('DRAWER', 0.9, 0.9)` | `('DRAWER', 0.9, 0.9)` | ✓ |
| R7-P override basis is labelled, not silent | `STRUCTURAL_OVERRIDE` | `STRUCTURAL_OVERRIDE` | ✓ |
| R7-P geometry basis is labelled, not silent | `GEOMETRY` | `GEOMETRY` | ✓ |
| R7-P menu_dependency=1 (int) reads as the bool True | `('DRAWER', 'OK')` | `('DRAWER', 'OK')` | ✓ |
| R7-P menu_dependency=0 (int) reads as the bool False | `('TOP_LEFT', 'OK')` | `('TOP_LEFT', 'OK')` | ✓ |
| R7-P non-boolean 2 never becomes True | `('TOP_LEFT', 'OK')` | `('TOP_LEFT', 'OK')` | ✓ |
| R7-P non-boolean '1' never becomes True | `('TOP_LEFT', 'OK')` | `('TOP_LEFT', 'OK')` | ✓ |
| R7-P non-boolean 'true' never becomes True | `('TOP_LEFT', 'OK')` | `('TOP_LEFT', 'OK')` | ✓ |
| R7-P non-boolean 1.0 never becomes True | `('TOP_LEFT', 'OK')` | `('TOP_LEFT', 'OK')` | ✓ |
| R7-P non-boolean [] never becomes True | `('TOP_LEFT', 'OK')` | `('TOP_LEFT', 'OK')` | ✓ |
| R7-P truthy garbage in the FLOATING flow clause stays undetermined | `(None, 'AMBIGUOUS_FLOATING_UNDETERMINED')` | `(None, 'AMBIGUOUS_FLOATING_UNDETERMINED')` | ✓ |
| R7-P no status string is a member of the 04 §4 entry_zone enum | `[]` | `[]` | ✓ |
| R7-P r7_zone() accessor agrees with the full result | `('DRAWER', 'BOTTOM', None)` | `('DRAWER', 'BOTTOM', None)` | ✓ |
| R7-P independent re-derivation of R7 disagrees nowhere | `(0, True)` | `(0, True)` | ✓ |

## 4. 정책 간 대조군 — fixture 1/3 정책 vs R7

- 절단값이 문자 그대로 같은가: **True**
- 비교한 입력: **1733점** · 일치 **1717** · 불일치 **16**

| 입력 부류 | 일치 | 불일치 |
|---|---|---|
| cut_neighbour | 8 | 0 |
| on_cut | 20 | 0 |
| out_of_unit_range | 8 | 16 |
| unit_grid | 1681 | 0 |

The two policies carry IDENTICAL cut values (1/3, 2/3 on both axes) and the same half-open band rule, so inside [0,1] they agree everywhere — 1709/1709 in-range points, the exact cuts and their nextafter neighbours included. They diverge only where the fixture policy answers a question R7 did not settle: out-of-unit coordinates, which the fixture policy classifies by extrapolating its inequalities and R7 leaves as AMBIGUOUS_OUT_OF_UNIT_RANGE. Where the out-of-unit axis is one R7 does not consult (x in MID/BOTTOM) the two agree again. The fixture policy also cannot express the structural overrides at all (AMB-S02), so FLOATING/DRAWER inputs are outside the comparable domain — agreement here is agreement on geometry, not on entry_zone as a whole.

갈린 지점 (전량, 16건):

| x | y | 부류 | fixture 정책 | R7 | R7 status |
|---|---|---|---|---|---|
| -5.0 | 0.1 | out_of_unit_range | `TOP_LEFT` | `None` | `AMBIGUOUS_OUT_OF_UNIT_RANGE` |
| 0.1 | -5.0 | out_of_unit_range | `TOP_LEFT` | `None` | `AMBIGUOUS_OUT_OF_UNIT_RANGE` |
| 0.5 | -5.0 | out_of_unit_range | `TOP_CENTER` | `None` | `AMBIGUOUS_OUT_OF_UNIT_RANGE` |
| 0.9 | -5.0 | out_of_unit_range | `TOP_RIGHT` | `None` | `AMBIGUOUS_OUT_OF_UNIT_RANGE` |
| -0.001 | 0.1 | out_of_unit_range | `TOP_LEFT` | `None` | `AMBIGUOUS_OUT_OF_UNIT_RANGE` |
| 0.1 | -0.001 | out_of_unit_range | `TOP_LEFT` | `None` | `AMBIGUOUS_OUT_OF_UNIT_RANGE` |
| 0.5 | -0.001 | out_of_unit_range | `TOP_CENTER` | `None` | `AMBIGUOUS_OUT_OF_UNIT_RANGE` |
| 0.9 | -0.001 | out_of_unit_range | `TOP_RIGHT` | `None` | `AMBIGUOUS_OUT_OF_UNIT_RANGE` |
| 1.001 | 0.1 | out_of_unit_range | `TOP_RIGHT` | `None` | `AMBIGUOUS_OUT_OF_UNIT_RANGE` |
| 0.1 | 1.001 | out_of_unit_range | `BOTTOM` | `None` | `AMBIGUOUS_OUT_OF_UNIT_RANGE` |
| 0.5 | 1.001 | out_of_unit_range | `BOTTOM` | `None` | `AMBIGUOUS_OUT_OF_UNIT_RANGE` |
| 0.9 | 1.001 | out_of_unit_range | `BOTTOM` | `None` | `AMBIGUOUS_OUT_OF_UNIT_RANGE` |
| 3.7 | 0.1 | out_of_unit_range | `TOP_RIGHT` | `None` | `AMBIGUOUS_OUT_OF_UNIT_RANGE` |
| 0.1 | 3.7 | out_of_unit_range | `BOTTOM` | `None` | `AMBIGUOUS_OUT_OF_UNIT_RANGE` |
| 0.5 | 3.7 | out_of_unit_range | `BOTTOM` | `None` | `AMBIGUOUS_OUT_OF_UNIT_RANGE` |
| 0.9 | 3.7 | out_of_unit_range | `BOTTOM` | `None` | `AMBIGUOUS_OUT_OF_UNIT_RANGE` |

추가 대조: classify_zone_r7() and classify_zone_geometric(policy=R7_ZONE_POLICY) agree on every in-range grid point; R7's dedicated primitives have not drifted from the generic classifier. → 검사 1681점, 어긋남 **0건**.

### 4.1 독립 재도출 대조

`_r7_independent_reference()` re-derives R7 from the ticket prose with its own hard-coded cuts and shares no primitive, policy object, or helper with `classify_zone_r7()`. Both are swept over the same inputs.

- 이유: Fixtures and mutations written alongside an implementation share its blind spots. A second derivation does not.
- 검사 입력: **7839개** · 불일치 **0건**

> **수렴 중 발견한 결함** — r7_structural_override() walked the precedence chain looking only for a TRUE flag. With in_reveal_required_nav_container=True but menu_dependency unobserved (DRAWER unresolved) and computed_position=fixed with the flow clause True (FLOATING confirmed), it returned FLOATING.
>
> 발견 경로: an independent re-derivation of R7 from the ticket prose, sharing no code with this harness, swept over 161k input combinations
>
> 왜 틀렸나: R7 ranks DRAWER above FLOATING. While DRAWER is open the answer is not yet known to be FLOATING, so returning FLOATING was this lane silently resolving R7's precedence with a guess. 20 input combinations were affected.
>
> 조치: The chain now stops at the first rung that is confirmed OR unresolvable; a confirmed lower value can only be returned once the higher one is ruled OUT.
>
> 교훈: The R7 fixtures were 60/60 green and all 8 mutations were caught while this defect was live. Mutation testing corrupts the primitives the fixtures already exercise; it cannot find a case the fixtures never thought to ask about. Only the independent re-derivation did.

## 5. 변이 검사 (10/10 잡힘, 원복 후 76 fixture 재통과: True)

| id | 대상 | 고의 결함 | 잡혔나 | 실패 fixture |
|---|---|---|---|---|
| R7-M01 | `_r7_band_test` | half-open `[a, b)` flipped to `(a, b]` — a value ON a cut falls into the LOWER band (R7 reading B forced everywhere) | yes | 6 |
| R7-M02 | `_r7_x_split_applies` | x thirds applied to MID and BOTTOM too, inventing MID_LEFT-style labels R7 explicitly refuses | yes | 16 |
| R7-M03 | `_r7_precedence_order` | structural overrides ignored — geometry always answers | yes | 24 |
| R7-M04 | `_r7_precedence_order` | precedence reversed — FLOATING beats DRAWER, contradicting `둘 다 해당하면 DRAWER 가 우선한다` | yes | 9 |
| R7-M05 | `_r7_range_ok` | out-of-unit coordinates silently classified instead of left AMBIGUOUS | yes | 10 |
| R7-M06 | `_r7_pick_axes` | x and y axes swapped | yes | 16 |
| R7-M07 | `_r7_cuts` | y and x cut pairs swapped (1/3 and 2/3 exchanged between axes is invisible, so the y cuts are pushed to 0.5/0.75) | yes | 6 |
| R7-M08 | `_r7_cuts` | equal thirds replaced by halves — the classic 'looked fine on a coarse grid' error | yes | 11 |
| R7-M09 | `_r7_truth` | structural inputs read with plain Python truthiness, so unparseable values silently fire an override | yes | 9 |
| R7-M10 | `_r7_truth` | structural inputs collapsed to MISSING, so overrides never fire and geometry always answers | yes | 20 |

## 6. 기존 Lane S fixture 회귀

| 묶음 | 통과 | 총계 |
|---|---|---|
| positive | 35 | 35 |
| negative | 21 | 21 |
| mutation caught | 10 | 10 |

기준선 대비: unchanged — positive 35/35, negative 21/21, mutation 10/10, identical to the pre-R7 baseline

## 7. 남은 모호성 (4)

R7 이 정하지 않은 것들. **채우지 않았다.**

### AMB-S14 — `entry_zone (R7 boundary_rule)`

- 문제: R7 contradicts itself on the y axis. `thresholds.y_bands` says `1/3 ≤ y < 2/3 → MID` and `boundary_rule` says `경계값은 하한 포함·상한 배제([a, b))로 통일한다` — both put y=1/3 in MID. The same `boundary_rule` sentence then adds `정확히 1/3 인 점은 TOP 이자 TOP_CENTER 다`, which puts y=1/3 in TOP. The x axis is unaffected: x=1/3 is TOP_CENTER under either reading.
- Lane S 처리: Implemented the inequality table + the general half-open rule (y=1/3 → MID) because two of the three statements agree and the third contradicts the rule it is appended to. The alternative reading is computed side by side in `r7_boundary_example_contrast()` and every diverging point is listed. This lane does NOT decide which reading is A's intent.
- 소유자: A — the contradiction is inside R7 itself.

### AMB-S15 — `entry_zone = FLOATING (R7 structural_overrides.FLOATING)`

- 문제: R7 defines FLOATING as `computed position 이 fixed 또는 sticky 이고 일반 흐름에서 벗어나 viewport 에 고정된 경우`. Whether the second clause is an independent observable or a restatement of the first is unstated, and it matters: `position: sticky` stays in normal flow and is viewport-fixed only while stuck, so under the strict reading a sticky header scrolled to its unstuck state is NOT FLOATING.
- Lane S 처리: Both clauses are required inputs. When the position clause is satisfied but the flow/viewport clause is unobserved the result is AMBIGUOUS_FLOATING_UNDETERMINED — no zone, no guess. If A rules the second clause a restatement, the fix is one predicate.
- 소유자: A (ruling) / B (collector — decides whether the flow clause is even captured).

### AMB-S16 — `entry_zone = DRAWER (R7 structural_overrides.DRAWER)`

- 문제: R7 identifies the DRAWER container as `menu_dependency=1 을 만든 그 container`. It does not say what to do when a control is observed inside a reveal-requiring container while menu_dependency=0 — the two observations cannot both hold under R7's own wording, and R7 gives no precedence between them.
- Lane S 처리: Reported as AMBIGUOUS_DRAWER_UNDETERMINED with the inconsistency named. Neither input is trusted over the other and no zone is emitted. Because DRAWER outranks FLOATING, an unresolved DRAWER also blocks a confirmed FLOATING from being returned.
- 소유자: A (ruling) / B (collector — may be a collection defect rather than a definition gap).

### AMB-S17 — `entry_x_norm / entry_y_norm outside [0,1] under R7`

- 문제: R7 freezes cut values but does not regulate coordinates outside the unit interval, which AMB-S04 already showed are reachable (control partially off-screen, or below the fold in state Sn). `y ≥ 2/3 → BOTTOM` read literally would swallow y=9.9 into BOTTOM; whether that is intended, or whether such a row should be excluded, is unstated.
- Lane S 처리: Coordinates are still never clamped (AMB-S04 behaviour preserved). When an out-of-unit coordinate is one R7 actually CONSULTS in that band, the result is AMBIGUOUS_OUT_OF_UNIT_RANGE and no zone is emitted. When the out-of-unit axis is one R7 does not consult (x in MID/BOTTOM), the zone stands and the fact is flagged as OK_UNCONSULTED_AXIS_OUT_OF_RANGE rather than dropped.
- 소유자: A (SSOT) / B (collector).

### R7 이 닫은 것

- **AMB-S01** — RESOLVED by T-A-V3-STEP1-003 R7 (successor delta Δ8). Cuts frozen at 1/3 and 2/3 on both axes, half-open bands. SSOTV3 04 §6 itself is still silent — the authority is the ticket, not the SSOT original.
- **AMB-S02** — RESOLVED by R7 `structural_overrides`: FLOATING/DRAWER outrank geometry and DRAWER outranks FLOATING. Geometry still never emits them; `classify_zone_r7` applies the precedence from separately collected structural inputs.
- **AMB-S03** — RESOLVED by R7 `thresholds.MID_BOTTOM`: the x thirds apply inside the TOP band only. Lane S's earlier inference was correct, but it was an inference until R7.

## 8. Limitation

R7 was frozen with REAL observations at zero, and this convergence was built the same way: no MAIN50 coordinate has ever been measured, so every number here comes from synthetic fixtures with answers planted by construction. That makes the boundary and precedence behaviour verifiable and the DISTRIBUTIONAL behaviour entirely unknown — nothing here says how often real controls land on or near a cut, how often FLOATING/DRAWER fire, or how often coordinates leave [0,1]. Three of R7's inputs (computed_position, the out-of-flow/viewport-fixed clause, in_reveal_required_nav_container) are collector-supplied and this lane cannot verify that B will emit them; if they arrive missing, entry_zone will be AMBIGUOUS rather than wrong, which is the intended failure mode but is still a gap. The fixture-only equal-thirds policy is retained purely as a control and must never code a real observation. Mutation coverage is ten single-primitive corruptions of the R7 path, and a second independent derivation of R7 agrees on every one of ~7.8k swept inputs — but both are still checks of ONE reading of R7's text. If AMB-S14 is resolved the other way, every green result above is green against the wrong reading, and the agreement of the two derivations would not have caught it: they were written from the same reading.

## 9. 재현

```bash
/home/sieg/projects-wsl/ProjectFinal/.venv/bin/python \
  /home/sieg/projects-wsl/ProjectFinal/.agent_worktrees/claude_d_research/research/landing_accessibility/research_d/tools/v3_harness/lane_s_spatial_control_reveal.py
```
