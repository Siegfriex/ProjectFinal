# Lane S — Spatial / Control-form / Menu·Reveal Harness

- verdict: **READY_WITH_AMBIGUITY**
- base SHA: `7448184a811f5d7d8772f21488bb75418fde3313`
- SSOT: `/home/sieg/projects-wsl/ProjectFinal/SSOTV3` (MANIFEST self-sha256 `1735c956d4a3461ee9eb2543c5c474942887bcbd117f5876d5486207f2f72e0a`)
- data status: **NO_REAL_DATA — MAIN50 not collected; outcome-independent preparation only**

## 1. 무엇을 했나

MAIN50 실측이 없으므로 결과 독립적으로, `04_FLOW_CODEBOOK_v3.0.md`가 이미 동결한 정의만 코드로 옮기고
합성 fixture 로 검산했다. 새 조작화·임계값·합산점수는 만들지 않았고, 정의가 없는 자리는 채우지 않고
`AMBIGUOUS_DEFINITION` 으로 올렸다.

## 2. 구현한 변수 (10)

| variable | status | caveat |
|---|---|---|
| `entry_x_norm` | IMPLEMENTED | no clamping; out-of-[0,1] preserved and flagged (AMB-S04) |
| `entry_y_norm` | IMPLEMENTED | same as entry_x_norm |
| `entry_zone` | IMPLEMENTED_POLICY_REQUIRED | derivation refuses to run without an injected ZonePolicy; SSOTV3 freezes none (AMB-S01/02/03). Collected values are validated and tabulated. |
| `entry_control_type` | IMPLEMENTED_VALIDATION_ONLY | collector-coded; Lane S does not assign control types |
| `nav_container_type` | IMPLEMENTED_VALIDATION_ONLY | — |
| `reveal_direction` | IMPLEMENTED_VALIDATION_ONLY | no type->direction mapping asserted (AMB-S09) |
| `nav_container_depth` | IMPLEMENTED_EXPLICIT_INPUT_REQUIRED | exposure step index must be supplied; nesting not verified (AMB-S08) |
| `menu_dependency` | IMPLEMENTED | closed reveal-token set of the three NAMED tokens; sequence_field explicit (AMB-S06/07) |
| `s0_task_control_visible` | IMPLEMENTED_PASSTHROUGH | no occlusion arbitration (AMB-S05) |
| `first_visible_scroll_state` | IMPLEMENTED | never-visible -> None, never 'S0' |

## 3. 기술통계

| 통계 | 함수 | 분모 |
|---|---|---|
| x/y distribution (05 §2-B) | `coordinate_summary` | family n=10 fixed; n_valid/n_missing reported |
| zone distribution + entropy (05 §2-B) | `categorical_distribution` | proportions over n_valid AND over n_declared=10 |
| service-pair spatial displacement (05 §2-B) | `pairwise_spatial_displacement` | n=10; 45 cells reported as matrix coverage only (05 §1) |
| control type distribution (05 §2-D) | `categorical_distribution` | n=10 |
| nav container type distribution (05 §2-D) | `categorical_distribution` | n=10 |
| reveal direction contingency (05 §2-D) | `reveal_contingency` | n=10 |
| nav container depth distribution (05 §2-D) | `coordinate-free count summary` | n=10 |

**분모 규율**: 05 §1/§4 — family n=10 is the fixed denominator; the 45 within-family pairs are distance-matrix cells, never n=45.

## 4. 결측·경계·동점 처리

- 결측 sentinel 은 `None` 이며 **0/0.0/False/'' 로 바꾸지 않는다**. Missing never forms a detector match, never enters a distribution's valid count, and never shrinks n_declared.
- 구간은 반열린 `[prev_cut, cut)` 이고 **정확히 경계값에 놓인 좌표는 위쪽 band 로 간다**.
  단 이는 동점 처리 규칙일 뿐이고, **경계값 자체는 SSOT 에 없다**(AMB-S01).
- 좌표는 clamp 하지 않는다. `[0,1]` 밖이면 값을 보존하고 `out_of_unit_range` 로 표시한다(AMB-S04).
- 결측은 detector 매칭을 만들지 않고, 유효 개수에 들어가지 않으며, `n_declared=10` 을 줄이지 않는다.

## 5. Fixture 결과

- positive: **35/35**
- negative: **21/21**
- mutation caught: **10/10** (원복 후 재실행 56 fixture 전부 통과: True)

### 변이 검사 상세

| id | 대상 primitive | 고의 결함 | 잡혔나 | 실패 fixture 수 |
|---|---|---|---|---|
| M01 | `_below_cut` | boundary comparison < becomes <= (cut falls into the LOWER band) | yes | 4 |
| M02 | `_coord_or_none` | missing coordinate silently coerced to 0.0 | yes | 2 |
| M03 | `_distance` | Euclidean displacement replaced by Manhattan | yes | 1 |
| M04 | `_log_p` | entropy logarithm base 2 replaced by natural log | yes | 1 |
| M05 | `_pick_first_state` | first visible scroll state uses max instead of min | yes | 2 |
| M06 | `_hierarchy_key` | nav_container_depth dropped from the hierarchy key | yes | 1 |
| M07 | `_label_groupable` | missing/empty labels allowed to form collision groups | yes | 2 |
| M08 | `_endpoint_cut` | menu_dependency scans the whole sequence, ignoring the endpoint cut | yes | 2 |
| M09 | `_family_denominator` | fixed family n=10 replaced by observed n | yes | 2 |
| M10 | `_pick_axes` | x and y axes swapped in zone classification | yes | 10 |

통과만 본 게 아니라, 계산기를 한 군데씩 고의로 틀리게 바꾼 뒤 fixture 가 그걸 잡는지 확인하고 원복했다.

> First run of the suite reported positive 35/35, negative 21/21 but mutation 9/10: M02 ('missing coordinate coerced to 0.0') ESCAPED. Cause was a defect in this harness, not in the fixtures — normalize_center() guarded missing inputs with early `return`s, so the primitive `_coord_or_none` never saw a None and the corruption was unreachable. normalize_center() was restructured to route every exit path, missing ones included, through `_coord_or_none`; M02 is now caught. This is the concrete payoff of mutation testing here: the pass-only view (56/56 fixtures green) would have shipped a dead guard.


## 6. AMBIGUOUS_DEFINITION (13)

SSOTV3 가 정하지 않아 **내가 채우지 않은** 것들. 소유자가 결정해야 한다.

### AMB-S01 — `entry_zone`

- 문제: 04 §6 fixes NO numeric boundary for the zone bands. No x cut (LEFT|CENTER|RIGHT) and no y cut (TOP|MID|BOTTOM) appears anywhere in SSOTV3 (grep over 00-15 returns nothing). entry_zone therefore cannot be derived from (x_norm, y_norm) without new operationalization.
- Lane S 처리: classify_zone_geometric() REQUIRES an injected ZonePolicy and ships NO default. Fixtures use FIXTURE_ONLY_ZONE_POLICY, which the code refuses to apply to non-fixture data. Collected entry_zone values are validated + tabulated, never recomputed.
- 소유자: A (SSOT) — must freeze boundaries or declare entry_zone collector-coded only.

### AMB-S02 — `entry_zone`

- 문제: FLOATING and DRAWER are in the same enum as five viewport-region labels but are containment/positioning STATES, not regions. A control can simultaneously be inside a drawer and at the top-right of the viewport. No precedence rule is given.
- Lane S 처리: Geometry emits only the 5-region subset. State categories are pass-through only, and zone-vs-geometry cross-checks are skipped (reported as SKIPPED_STATE_ZONE) for them.
- 소유자: A (SSOT).

### AMB-S03 — `entry_zone`

- 문제: Taxonomy is asymmetric: the TOP band is split three ways on x, MID and BOTTOM are not. Whether MID/BOTTOM ignore x, or whether TOP_* also covers non-top controls, is unstated.
- Lane S 처리: Implemented as: x is consulted only inside the TOP band. This follows the enum literally but is an inference, so it is registered here rather than presented as settled.
- 소유자: A (SSOT).

### AMB-S04 — `entry_x_norm / entry_y_norm`

- 문제: 'viewport로 정규화' does not say whether values may fall outside [0,1] (control partially off-screen, or below the fold in state Sn), nor whether clamping is allowed, nor which state's viewport is the denominator when the control is first seen at S2.
- Lane S 처리: No clamping. Out-of-range values are preserved and flagged (`out_of_unit_range=True`); the per-state viewport on the same row is used.
- 소유자: A (SSOT) / B (collector).

### AMB-S05 — `s0_task_control_visible`

- 문제: '직접 보이는가' vs `task_control_occlusion` (02 §5): whether a control rendered at S0 but covered by an overlay counts as visible is unstated.
- Lane S 처리: Pass-through of the collected boolean only. No occlusion arbitration performed.
- 소유자: A (SSOT).

### AMB-S06 — `menu_dependency`

- 문제: 04 §5 lists three reveal tokens then writes '등' (etc.), leaving the token set open. SWITCH_TAB is a canonical token (04 §2) and is arguably a reveal, but is not named.
- Lane S 처리: Closed set = the three NAMED tokens. Any extension must be passed explicitly via `extra_reveal_tokens`; the default is empty and SWITCH_TAB is NOT counted.
- 소유자: A (SSOT).

### AMB-S07 — `menu_dependency`

- 문제: 'endpoint 전' is undefined when the run terminates at AUTH_GATE / BLOCKED / ABSTAIN and no ENDPOINT_REACHED token exists. Also, 04 §4 says 'action_sequence' but 02 §4 stores two sequences (task_flow_sequence, experienced_flow_sequence) and no field named action_sequence.
- Lane S 처리: Prefix = up to ENDPOINT_REACHED if present, else the whole sequence; the choice is reported per row as `endpoint_cut_basis`. `sequence_field` is a REQUIRED argument — the harness will not silently pick one of the two sequences.
- 소유자: A (SSOT).

### AMB-S08 — `nav_container_depth`

- 문제: 'task control 노출 전 nested reveal 수' presupposes an identifiable exposure step, but no rule defines which step index constitutes exposure, nor whether sibling (non-nested) reveals count.
- Lane S 처리: recompute_nav_container_depth() requires an explicit `exposure_step_index`; it is never inferred. With no index supplied the stored collector value is validated, not recomputed.
- 소유자: A (SSOT) / B (collector).

### AMB-S09 — `reveal_direction`

- 문제: No mapping between nav_container_type and reveal_direction is fixed (e.g. whether LEFT_DRAWER must imply LEFT, or INLINE_EXPAND must imply INLINE).
- Lane S 처리: Contingency table only (type x direction). No combination is scored, flagged as invalid, or corrected.
- 소유자: A (SSOT).

### AMB-S10 — `zone entropy (05 §2-B)`

- 문제: Logarithm base is unspecified, and it is unspecified whether the support k is the full enum cardinality (7) or the observed support, and whether missing rows enter the denominator given 05 §4's fixed n=10.
- Lane S 처리: Shannon entropy reported in BITS with the base recorded; both max_entropy_enum (log2 7) and max_entropy_observed (log2 k_obs) reported; proportions computed over n_valid with n_declared=10 and n_missing reported alongside. No single figure is presented as the entropy.
- 소유자: A (SSOT) / C (report convention).

### AMB-S11 — `service-pair spatial displacement (05 §2-B)`

- 문제: 'displacement' names no metric (Euclidean vs Manhattan vs component-wise) and no aspect-ratio handling — normalized x and y come from a 390x844 viewport, so one normalized unit of x is not one normalized unit of y in physical terms.
- Lane S 처리: Raw dx and dy components are reported for every cell alongside the Euclidean value; `metric` is an explicit parameter. No physical rescaling is applied or implied.
- 소유자: A (SSOT).

### AMB-S12 — `counterexample detector: 'same position, different hierarchy'`

- 문제: 'same position' has no tolerance defined. A coordinate-epsilon comparison would require a threshold that SSOTV3 does not contain.
- Lane S 처리: Default mode is `zone` — exact equality of the collected categorical entry_zone, which introduces no threshold. A `coordinate_epsilon` mode exists but has NO default epsilon and raises UnresolvedDefinition unless the caller passes one explicitly.
- 소유자: A (SSOT).

### AMB-S13 — `counterexample detector: 'same visible label, different control type'`

- 문제: Label equivalence (unicode/whitespace normalization, synonym map) is defined in 04 §5 for `label_relation` and is Lane L's deliverable, not Lane S's.
- Lane S 처리: The detector takes a REQUIRED `label_key_fn` injected by the caller. Lane S ships only `identity_label_key` (raw byte-exact, no normalization) so that Lane L's normalizer can be plugged in unchanged. Lane S reports the control_type divergence side only.
- 소유자: L (label normalization).

가장 무거운 것은 **AMB-S01** 이다. `entry_zone` 은 04 §4 에서 Geometry categorical 로 선언돼 있지만
04 §6 은 좌표를 보존하라고만 하고 **x/y 절단값을 하나도 주지 않는다**. SSOTV3 00~15 전체 grep 에서도
절단값은 나오지 않는다. 따라서 좌표에서 zone 을 유도하는 것은 현재 불가능하고, 이 하네스는 유도를
거부한다(`UnresolvedDefinition`). fixture 에서 쓴 1/3 등분 정책은 기계 동작 확인용이며 제안이 아니다 —
`FIXTURE_ONLY_NOT_SSOT` 로 태그돼 있고 fixture 밖에서 쓰면 예외를 던진다.

## 7. 반례 탐지기

### CE-A `same_position_different_hierarchy`

- 질문: 위치는 같은데 menu hierarchy 가 다른 경우
- position_equivalence: default mode 'zone' = exact equality of the collected categorical entry_zone (introduces no threshold). mode 'coordinate_epsilon' exists but has no default epsilon and refuses to run without one (AMB-S12).
- hierarchy_key: `nav_container_type`, `reveal_direction`, `nav_container_depth`, `menu_dependency`
- output: pair list of counterexamples AND the same-position/same-hierarchy pairs, so the negative side is inspectable; no severity or score attached
- 양방향 검증: `P-DETA same zone, different hierarchy`, `P-DETA depth-only difference still detected`, `N-DETA same zone, identical hierarchy -> no hit`, `N-DETA different zone -> no hit even though hierarchy differs`, `N-DETA missing zone never matches missing zone`, `N-DETA epsilon mode has no default tolerance`, `mutation M06`

### CE-B `same_label_different_control_type`

- 질문: visible label 은 같은데 control type 이 다른 경우
- interface: detect_same_label_different_control_type(observations, label_key_fn) — label_key_fn is REQUIRED and injected. Lane S ships only identity_label_key (byte-exact, no normalization). Lane L's normalizer plugs in unchanged.
- lane_s_scope: control_type divergence side only; Lane S makes no label-equivalence judgement (04 §5 belongs to Lane L, AMB-S13)
- output: group list of counterexamples AND same-label/same-type groups; count of rows dropped for missing/empty labels
- 양방향 검증: `P-DETB same label, different control type`, `N-DETB same label, same control type -> no hit`, `N-DETB different labels -> no hit`, `N-DETB missing labels never group`, `N-DETB empty-string labels never group`, `mutation M07`

두 탐지기 모두 **탐지돼야 할 것이 탐지되는지**와 **탐지되면 안 되는 것이 안 되는지**를 같이 본다.
어느 쪽도 심각도·점수·순위를 붙이지 않는다.

## 8. 하지 않은 것

- entry_zone boundary values — SSOTV3 freezes none; Lane S must not invent them (AMB-S01).
- FLOATING / DRAWER derivation — state categories with no geometric rule (AMB-S02).
- Any threshold, cut-off, or composite/weighted 'friction' score (05 §3 prohibits it).
- Label normalization, synonym mapping, label_relation — Lane L owns 04 §5 (AMB-S13).
- Gower / mixed-type distance — 05 §3 allows it only as secondary visualization; not needed pre-freeze.
- Any inferential test, effect size, or significance claim — 05 §4 is descriptive.
- Any REAL target access, URL fetch, or candidate-list read.
- Occlusion arbitration for s0_task_control_visible (AMB-S05).
- Nesting verification inside nav_container_depth (AMB-S08).
- GO/NO-GO judgement, gold labels, holdout access.

## 9. Limitation

MAIN50 measurement data does not exist yet (A freeze pending, REAL unpublished). Every result in this file comes from synthetic fixtures with pre-planted answers; nothing here is an empirical finding about any service. The harness has never been executed against a real observation row, so schema-drift between this implementation and B's emitted columns is unverified. The single largest blocker is AMB-S01: entry_zone is listed as a Geometry variable but SSOTV3 defines no boundary, so zone derivation is inoperable until A freezes one or declares entry_zone collector-coded only; the fixture-only equal-thirds policy exercises mechanics and is not a proposal. Fixture coverage is structural, not distributional: fixtures confirm the calculators recover planted answers and reject planted non-cases, but say nothing about behaviour on real coordinate distributions, real Korean label strings, or real sequence lengths. Mutation testing covers ten single-primitive corruptions; a mutation the fixtures do not cover would go unnoticed.

## 10. 재현

```bash
/home/sieg/projects-wsl/ProjectFinal/.venv/bin/python \
  /home/sieg/projects-wsl/ProjectFinal/.agent_worktrees/claude_d_research/research/landing_accessibility/research_d/tools/v3_harness/lane_s_spatial_control_reveal.py
```
