# RQ-D7 — mart 분모 축소(59 → 56 → 31)가 계획된 association 추정에 주는 영향의 상한

- plane: **D (독립 연구 샌드박스, NON_CANONICAL)** · claim_kind: `ANALYSIS`
- 결과 JSON: `results/RQ_D7_denominator_bounds.json` · 코드: `tools/rq_d7_denominator_bounds.py`
- MLflow: experiment `LA_10_RESEARCH_D` · run `e15528648d6d48e0a3cb9bf5afc5139e` (39 metrics)
- seed 20260828 · permutation 20000회 · grain: **target(web_target_group), 모집단 n=59**
- SSOT 승계: 이 분모 사슬 분석은 v3 `05_ANALYSIS_PLAN_v3.0.md §6`(단계별 분모 보고)로 승계된다.
  본 문서는 v2.1 시점 산출이며 v3용 새 조작화를 만들지 않았다.

---

## 0. 먼저 — 내가 틀리게 틀 잡았다가 raw 확인으로 시정한 것

**틀린 초안 서술.** 나는 landing mart 56행 안에서 probe가 없어 covariate가 결측인 2 target을
`"UNRECORDED_COVARIATE_MISSING"` — *"원장에 사유가 기록돼 있지 않은 결측"* 으로 분류하고,
"위 두 제외층(59→56, 56→31)과 달리 사유가 없다"고 썼다. 상위 계층 결함처럼 보이는 서술이었다.

**raw를 직접 열어 확인한 것.** 보고 전에 collector 원장 `detail.l0`과 evidence 디렉터리를
직접 열었다.

| 확인한 곳 | 실제 값 |
|---|---|
| `fact_landing_observation.measurement_status` | `FAILED_EVIDENCE_INCOMPLETE` (2건 모두) |
| `fact_landing_observation.probe_path` | `null` (2건 모두) |
| collector `detail.l0.notes` | `"Error: Page.evaluate: Execution context was destroyed, most likely because of a navigation"` |
| evidence 디렉터리 `l0a/` 실물 | `ax.json`·`computed_css.json`·`dom.html`·`screen_*.png` 만 있고 `probe.json`이 실제로 없음. manifest.jsonl에도 항목 없음 |
| 원장 `outcome` | `UNRESOLVED` — 다른 16 target과 같은 값 |

**시정.** 사유는 **기록돼 있다.** 다만 기록된 위치가 원장 `outcome`이 아니라 mart의
`measurement_status`와 collector note다. 그래서 분류를
`"RECORDED_IN_MART_NOT_IN_LEDGER_OUTCOME"`으로 바꾸고, JSON에 `self_correction` 필드와
사유가 기록된 위치 표를 남겼다. **내가 "기록 없음"이라고 말할 뻔한 것은 실제로는 "원장
outcome만 보면 구별 불가"였다.**

**시정 과정에서 오히려 진짜로 나온 것 두 개.**

1. **measurement_status 실패(3건) ≠ probe 부재(2건).** 세 번째 실패 target
   `054d78ed187cdd9f`는 probe가 **있고** `max_overlay_coverage=0.1137`, interrupt 1건,
   candidate 7건이 정상 기록돼 있다. 같은 note를 가진 3건이 서로 다른 결측 상태다. 두 집합을
   하나로 뭉뚱그리면 안 된다.
2. **결측이 0.0으로 코딩된다.** probe가 없는 2행에서 `max_overlay_coverage`와
   `max_primary_action_occlusion`이 `null`이 아니라 **`0.0`** 으로 들어간다. 같은 행의
   `primary_action_visible_initial`은 `null`이다 — 한 행 안에서 결측 표현이 일관되지 않는다.
   `fact_landing_observation`만 읽는 소비자는 *"가림 0%로 측정된 target"* 과 *"측정 실패"* 를
   구별할 수 없다.
   - **내 파싱 결함 가능성 배제:** collector 원장 `detail.l0`을 직접 열었고 거기에 이미
     `max_overlay_coverage: 0.0`이 쓰여 있다. mart 빌더가 만든 값이 아니라 collector가 쓴 값이다.
   - claim_kind는 `OBSERVATION`이다. **결함 판정이 아니다** — 이 코딩이 의도된 것인지의
     판단은 D 권한이 아니다.

RQ-D1 초안이 "3 target이 조용히 사라진다"고 했다가 RQ-D13c에서 시정된 이력이 있다. 같은 종류의
실수를 한 번 더 할 뻔했고, raw를 먼저 연 것이 막았다.

---

## 1. 용어 규율 (문서 맨 앞에 박는다)

이 자료에 "손실"이라고 부를 것은 없다. 네 층은 성격이 전부 다르다.

| 층 | 크기 | 성격 | 정확한 이름 |
|---|---|---|---|
| 66 → 59 | dir 7개 | **결측층이 아니다.** 반복 실행의 관측 grain 붕괴 | `GRAIN_COLLAPSE_NOT_MISSINGNESS` |
| 59 → 56 | target 3 | 원장이 `SKIPPED_RETRY_EXHAUSTED`로 **정직하게 기록** | `LEDGER_RECORDED_EXCLUSION` |
| 56 → 31 | target 25 | 원장이 `ACCOUNT_ACTION_BLOCKED`로 **정직하게 기록** | `LEDGER_RECORDED_EXCLUSION` |
| 56 안 | target 2 | mart `measurement_status`에 기록, 원장 outcome으로는 구별 불가 | `RECORDED_IN_MART_NOT_IN_LEDGER_OUTCOME` |

**59 → 56은 조용한 소실이 아니다.** `REAL_RUN_SUMMARY.collection_markers`는 59를 알고
`fact_landing_observation`은 56이다 — 이것은 소실이 아니라 **두 산출물의 분모가 다른 것**이며,
그 차이가 문서화되지 않은 것이 문제다 (RQ-D13c 판정과 동일).

`prior_archetype` / `prior_business_domain`은 **gold label이 아니라 prior**다. 이 문서에
"accuracy"라는 말은 없다.

---

## 2. Verdict

**`PARTIALLY_SUPPORTED`**

> 결측률은 하나의 숫자가 아니다 — 결과변수가 landing mart에 있으면 실제 결측은 **5/59**,
> task mart에 있으면 **28/59**이고, worst-case RD bound 폭은 각각 **0.16~0.51**과 **0.93**이다.
> 표본오차까지 합치면 검사한 4개 association 중 0을 배제하는 것은 **0개**다. L3(25건) 제외는
> 원장 `ACCOUNT_ACTION_BLOCKED`와 결정론적으로 일치하므로 MCAR이 아니지만, BH-FDR을 붙인
> covariate 검정은 그 비무작위성을 **하나도 검출하지 못한다.**

- **지지되는 것:** 층별 bound 폭과 부호식별 여부, L3 제외가 결정론적이라는 것, 그리고
  covariate 기반 결측검정이 이 표본에서 *알려진* 비무작위성조차 검출하지 못한다는 것.
- **지지되지 않는 것:** complete-case 편향의 방향과 크기, 인과 주장, 어떤 bound 폭이
  "충분히 좁은가"라는 판단(**A 권한**), 무엇을 다시 모을지.

---

## 3. 경쟁가설별 판정

### H-D7-MCAR — "결측은 관측 공변량과 무관하다" → **REFUTED (단, 기전으로만; covariate 검정은 검출 실패)**

판정근거가 두 갈래로 갈리므로 정확히 쓴다.

- **기전 근거 (확정적):** landing mart 56 중 task row가 없는 25 target 집합이 원장
  `ACCOUNT_ACTION_BLOCKED` 집합과 **정확히 일치**한다 (대칭차 0건, 양방향 모두 공집합).
  guard가 막은 target은 scout가 돌지 않아 task detail 키가 없고 빌더가 행을 만들지 않는다.
  확률적 결측이 아니라 **결정론적 제외**다. 차단 사유 내역: LOGIN 19 · PURCHASE 3 · SIGNUP 2 ·
  PAYMENT 1 (= `collection_markers.guard_blocked_n` 25와 일치).
- **covariate 검정 근거 (음성):** L3에서 45개 검정 중 **BH q<0.05를 통과한 covariate가 0개**다.
  최소 q = 0.161.

  | covariate | kind | stat | p | q(BH) | 유의 |
  |---|---|---|---|---|---|
  | cap_count | continuous | 0.6662 | 0.0068 | 0.1609 | ✗ |
  | cap_any | binary | 0.3829 | 0.0072 | 0.1609 | ✗ |
  | cap_contrast | binary | 0.3446 | 0.0172 | 0.1843 | ✗ |
  | cap_accessible_name_sources | binary | 0.3459 | 0.0241 | 0.1843 | ✗ |
  | modal_overlay_n | continuous | 0.6766 | 0.0266 | 0.1843 | ✗ |
  | dismiss_control_n | continuous | 0.6766 | 0.0266 | 0.1843 | ✗ |
  | prior_archetype | categorical | 0.4722 | 0.0381 | 0.1843 | ✗ |
  | prior_business_domain | categorical | 0.4722 | 0.0383 | 0.1843 | ✗ |

  (음성 결과도 결과다 — 전체 45행은 JSON `missingness_diagnosis` 에 남겼다.)

**이것이 이 RQ의 가장 쓸모 있는 부산물이다.** 우리는 L3가 비무작위임을 *기전으로 안다*.
그런데 표준적인 covariate 기반 결측검정은 n=56·45검정·BH-FDR에서 그것을 **하나도 잡아내지
못한다.** 따라서 이 자료에서 *"유의한 covariate가 없다"를 MCAR의 증거로 읽으면 안 된다*는
구체적 반례를 RQ 내부에서 확보했다.

### H-D7-MAR_OBSERVABLE — "결측이 관측 공변량과 연관돼 complete-case가 편향된다" → **PARTIALLY_SUPPORTED**

- **지지되는 곳 (L2b, probe 부재 2건):** 20개 검정 중 10개가 BH q<0.05 통과.

  | covariate | kind | stat | p | q(BH) |
  |---|---|---|---|---|
  | dom_body_empty | binary | 0.6939 | 0.0041 | 0.0460 |
  | has_l0c | binary | −0.6146 | 0.0071 | 0.0460 |
  | dom_script_n | continuous | 0.0046 | 0.0192 | 0.0460 |
  | dom_body_element_n / dom_interactive_n | continuous | 0.0185 | 0.0230 | 0.0460 |
  | css_bytes / dom_body_text_len / dom_element_n / dom_bytes / ax_bytes | continuous | 0.0185 | 0.0230 | 0.0460 |

  방향은 "DOM이 비어 있거나 극히 작다"이며 navigation 중 execution context 파괴라는 기전과
  정합한다. **다만 flagged n=2다** — BH 통과가 취약하고, 이것을 의미 있는 규모의 MCAR 위반으로
  읽으면 안 된다.
- **지지되지 않는 곳 (L2, 3건):** 이 3 target은 DOM/probe covariate가 **정의상 결측**이라
  그 covariate들과의 연관을 검정할 수단이 **원리적으로 없다.** 항상 관측되는 prior_*/worker
  5개만 검정했고 전부 음성(최소 q=0.431)이다. 여기서는 MAR도 MCAR도 **판정 불가**다.
- **편향의 방향은 주장하지 않는다.** 연관이 있다는 것과 complete-case가 얼마나 치우쳤는지는
  다른 문제이며, 후자는 bound로만 말한다.

### H-D7-BOUND_UNINFORMATIVE — "bound가 너무 넓어 어떤 방향도 배제 못 한다" → **SUPPORTED, 단 결과변수가 task mart에 있을 때만**

질문의 전제였던 "31/59 결측률"이라는 **하나의 숫자는 association마다 성립하지 않는다.**
결과변수가 landing mart에 있으면 실제 결측은 5/59, task mart에 있으면 28/59다.

### H-D7-BOUND_INFORMATIVE — "bound가 0을 배제하는 association이 하나라도 있다" → **SUPPORTED_FOR_IDENTIFICATION_REGION_ONLY**

- 순수 식별구간에서 0을 배제하는 association: **1개** — `(a) cap_any × 커머스`,
  식별구간 [0.211, 0.371].
- **표본오차를 합치면: 0개.** `(a)`의 bound+sampling = [−0.025, 0.564]로 0을 포함한다.
- **가장 날카로운 사례:** `(a)`의 complete-case Newcombe 95% CI는 [0.100, 0.538]로 0을
  배제하고, 식별구간도 0을 배제한다. **그런데 둘을 합치면 0을 배제하지 못한다.** 이
  association을 깨는 것은 **25건이 아니라 5건**이다.

---

## 4. 분모 사슬 — 내가 재계산한 결과

D의 숫자를 가설로만 받고 filesystem·원장·mart **세 소스에서 독립 재계산**했다.

| 단계 | D 가설 | 내 재계산 | 일치 |
|---|---|---|---|
| observation dir | 66 | **66** (w01 15 · w02 20 · w03 17 · w04 14; sealed 60 / empty 6) | ✔ |
| distinct target (wtg) | 59 | **59** | ✔ |
| duplicate launch | 4 | **4** | ✔ |
| retry 실패 | 3 | **3** | ✔ |
| `fact_landing_observation` 행 | 56 | **56** (distinct wtg 56) | ✔ |
| `fact_task_entry` target | 31 | **31** (31행 / 31 target, target당 1.0행) | ✔ |
| landing에 있고 task에 없음 | 25 | **25** | ✔ |

**`agreement: IDENTICAL` — 다른 숫자는 없다.**

집합 정합성 3종도 전부 참이다: filesystem wtg 집합 = 관측표 wtg 집합 = 원장 wtg 집합이고,
관측표 `in_mart` 플래그 집합 = landing mart 집합이며, task 집합 ⊂ landing 집합이다.
`step_1`의 59는 `collection_markers.analysis_sample.unique_targets` 59와도 일치한다.

**빠진 wtg 목록**

- 59 → 56 (원장 기록 제외 3, 전부 `SKIPPED_RETRY_EXHAUSTED`):
  `2cd43b99c1ed87cf`(w03, UTILITY_OTHER/삼성 노트) · `dd5061eb74e2d4d4`(w03,
  FINANCE_PAYMENT/삼성 월렛) · `ff3ee504792f6cfc`(w02, PORTAL_SEARCH/삼성 인터넷 브라우저).
- 56 → 31 (원장 기록 제외 25): `ACCOUNT_ACTION_BLOCKED` 집합과 **정확히 일치**. 전체 목록은
  JSON `denominator_chain.step_3_task_mart_rows.excluded_wtg`.
- 56 안의 covariate 결측 2: `64d30ef262d8782d`(w01) · `ef06dc942ef3ccc9`(w02).

**D 서술에 없던 것 하나.** 56 안에서 probe 부재로 covariate가 결측인 target이 **2건 더** 있다.
RQ-D8이 observation grain으로 8행(probe 없음 6 + probe 0 2)을 보고했으나, **target grain의 이
2건은 분모 사슬 서술에 들어 있지 않았다.** 이 2건이 (a)(b)(c) 세 bound에 전부 영향을 준다.

---

## 5. Worst-case bound (Manski, 무가정 상한)

**분모 정직성:** 아래 전부 **target grain, 모집단 n=59**다. `fact_task_entry`는 target당 1행
(31행/31 target)이므로 task grain이 아니라 target grain이다 — step grain과 섞지 않았다.
추정량은 risk difference `RD = P(Y=1|X=1) − P(Y=1|X=0)`이며, bound는 결측 배치의 완전열거로
구했다.

| # | X (노출) | Y (결과) | 결측 | CC 점추정 | CC Newcombe 95% (폭) | **식별구간 (폭)** | 부호식별 | +표본오차 (폭) |
|---|---|---|---|---|---|---|---|---|
| **(a)** | prior domain = `SHOPPING_COMMERCE` | `cap_any = 1` | **5** | 0.337 | [0.100, 0.538] (0.437) | **[0.211, 0.371] (0.160)** | **예** | [−0.025, 0.564] (0.588) |
| **(b)** | `dom_aria_label_n = 0` | `modal_overlay_n > 0` | **5** | 0.000 | [−0.176, 0.096] (0.272) | **[−0.217, 0.077] (0.294)** | 아니오 | [−0.419, 0.203] (0.622) |
| **(c)** | `gate_password_input_n > 0` | `fact_task_entry` 행 존재 | **5** | 0.137 | [−0.340, 0.440] (0.780) | **[−0.214, 0.300] (0.514)** | 아니오 | [−0.482, 0.508] (0.990) |
| **(d)** | prior domain = `SHOPPING_COMMERCE` | `auth_gate_before_endpoint = 1` | **28** | 0.033 | [−0.287, 0.344] (0.630) | **[−0.450, 0.480] (0.930)** | 아니오 | [−0.633, 0.658] (1.290) |

(a)(b)(c)는 지정된 후보다. **(d)는 내가 추가했다** — (a)(b)(c)가 전부 L2/L2b만 결측이라
3~5건 문제로 끝나기 때문에, 56→31의 25건이 실제로 무는 곳을 보려면 결과가 task mart에 있는
association이 하나 필요했다. (d)가 그 대표다.

**결측 내역**
- (a): X 전부 관측(prior는 59 전수 보유). Y 결측 5 = L2 3 + L2b 2. 배치는 X=1쪽 1 · X=0쪽 4.
- (b): X·Y 둘 다 결측 3(L2) + Y만 결측 2(L2b). "둘 다 결측" 3건이 bound를 가장 크게 벌린다.
- (c): **결측 자체가 결과변수**다. Y(=task row 존재)는 59 전부 관측되고 X만 5건 결측이다.
  따라서 **L3는 이 추정치에서 결측층이 아니라 결과의 분포**다. CC의 φ는 0.063으로 사실상 무연관.
- (d): X 전부 관측, Y 결측 28 = L2 3 + L3 25 (X=1쪽 10 · X=0쪽 18).

**민감도 2종** (JSON `bounds`에 전부 수록)
- `measurement_status = FAILED_EVIDENCE_INCOMPLETE` 3건을 전부 결측 취급: (a) 폭 0.160→0.198,
  (b) 0.294→0.396, (c) 0.514→0.557. **(a)의 부호식별은 유지된다.**
- 커머스 광의 정의(`SHOPPING_COMMERCE ∪ FINANCE_PAYMENT`): (a) 식별구간 [0.143, 0.315],
  폭 0.172, 부호식별 유지.

> **폭을 직접 비교하지 마라.** 식별구간이 complete-case CI보다 좁게 나오는 경우가 있다((a):
> 0.160 vs 0.437, 비 0.365). 이는 모순이 아니라 **서로 다른 종류의 불확실성**이기 때문이다 —
> 식별구간에는 표본오차가 없다. 둘을 함께 담은 값이 "+표본오차" 열이다.

---

## 6. 층별 기여 분해 — "3건만 복구하면 되는가, 25건이 문제인가"

**둘 다 답이 아니다. association이 어느 mart를 결과로 쓰는지에 달렸다.**

RD bound 폭 (한 층씩만 채웠을 때):

| association | S0 (무복구) | +L2만 (3건) | +L2b만 (2건) | +L3만 (25건) | 전부 (30건) | 지배 층 |
|---|---|---|---|---|---|---|
| (a) cap_any × 커머스 | 0.160 | **0.069** | 0.091 | **0.160 (변화 없음)** | 0.000 | L2 (−0.091) |
| (b) modal × aria 없음 | 0.294 | **0.087** | 0.207 | **0.294 (변화 없음)** | 0.000 | L2 (−0.207) |
| (c) task row × password gate | 0.514 | **0.184** (부호식별 획득) | 0.329 | **0.514 (변화 없음)** | 0.000 | L2 (−0.329) |
| (d) auth gate × 커머스 | 0.930 | 0.839 | 0.930 | **0.091** | 0.000 | **L3 (−0.839)** |

읽는 법:

- **결과가 landing mart인 association ((a)(b)(c))**: 결측은 **5건뿐**이고, **25건을 복구해도
  bound가 전혀 좁아지지 않는다** (폭 변화 0.000). 여기서 문제는 3건(+2건)이다.
  (c)는 L2 3건만 채우면 부호식별을 얻는다.
- **결과가 task mart인 association ((d))**: 25건이 결측의 **89% (25/28)** 를 차지한다.
  3건만 복구하면 폭이 0.930 → 0.839로 거의 그대로다. 여기서 문제는 25건이다.

**66 → 59 층의 기여는 0이다.** 중복발사 4 target에서 canonical dir을 반대쪽으로 바꿔봤을 때,
이 RQ의 bound 변수 4개(`cap_any`, `aria_label=0`, `modal>0`, `password>0`) 중 **어느 것도
뒤집히지 않는다 (0/4 target).** 연속값은 흔들린다 — 예: `13ed070478ef62c3`의
`modal_overlay_n`이 6 vs 7 — 그러나 이진화 후 값은 동일하다. **66→59는 분모 문제가 아니다.**

---

## 7. 반례 (내 결론에 불리한 것들)

1. **"bound가 항상 무정보"에 대한 반례:** (a)는 결측 5건에서 worst-case여도 **식별구간이 0을
   배제한다** ([0.211, 0.371]). 결측률이 높다는 것만으로 bound가 무정보라고 말할 수 없다.
2. **그러나 그 반례에 대한 반례:** 표본오차를 합치면 (a)도 0을 배제하지 못한다
   ([−0.025, 0.564]). **내 H-D7-BOUND_INFORMATIVE 지지는 식별구간에 한정된다.**
3. **"MCAR 검정 가능"에 대한 반례:** L2의 3 target은 DOM/probe covariate가 정의상 결측이라
   그 covariate들과의 연관을 검정할 방법이 **없다.** 검정 결과가 음성인 것이 MCAR의 증거가 아니다.
4. **"covariate 검정이 비무작위성을 잡는다"에 대한 반례:** L3는 기전상 100% 결정론적으로
   비무작위인데 45개 covariate 검정 중 BH 통과가 **0개**다.
5. **"66→59가 분모 손실"에 대한 반례:** canonical dir 선택이 bound 변수를 뒤집는 target이 0건이다.
6. **"probe 실패 = measurement 실패"에 대한 반례:** `054d78ed187cdd9f`는
   `measurement_status=FAILED_EVIDENCE_INCOMPLETE`이면서 probe가 정상이고 값이 다 들어 있다.

---

## 8. 이 RQ가 답하지 않는 것

> 이 bound 폭이 계획된 분석에 충분한지, 무엇을 다시 모을지, 어떤 분모를 공식 분모로 삼을지는
> 답하지 않는다 — **construct와 결정은 A 권한이다.** 이 문서에 GO/NO_GO도 threshold도 재수집
> 권고도 없다.

---

## 9. Limitation (무거운 순서)

1. **가장 무거운 것 — 층별 "복구"는 반사실이다.** 분해표에서 "복구"란 해당 층의 결측을
   complete-case 조건부 비율로 결정론적으로 채운 것이다. bound **폭**은 남은 결측 수에 지배돼
   채움값에 사실상 무관하지만, bound **중심**은 채움값에 의존한다. **폭만 해석하라.** 실제로
   그 30 target을 다시 측정하면 어떤 값이 나올지 이 분석은 모른다.
2. L2(3)·L2b(2)의 결측 기전은 n이 작아 어떤 검정도 검정력이 없다. 음성 결과를 MCAR의 증거로
   읽으면 안 된다.
3. L3에서 BH-FDR 유의 covariate가 0인 것은 MCAR의 증거가 아니라 **검정력 부족**이다 — 같은
   층의 기전(원장 outcome)은 결정론적 비무작위임을 보여준다.
4. `bound_with_sampling_uncertainty`는 모든 결측 배치의 Newcombe 95% CI **합집합**이다.
   Imbens–Manski 구간보다 보수적이므로 실제 95% 구간은 이보다 좁다. 이 구간이 0을 배제하지
   못한다는 것은 "배제된다"보다 **약한** 진술로 읽어야 한다.
5. worst-case bound는 **어떤 가정도 없는 상한**이다. 그럴듯한 가정(예: 단조 결측)을 넣으면
   좁아지지만, 어떤 가정이 정당한지는 D가 정하지 않는다.
6. `prior_business_domain`은 gold label이 아니라 **prior**다. (a)(d)의 X가 prior이므로
   prior 자체의 오분류는 bound에 반영돼 있지 않다.
7. permutation p는 20000회 기준이며 최소 달성 가능 p는 1/20001이다.
8. `fact_criterion_result`는 **0행**이라 KWCAG 축 association은 bound 계산 자체가 불가능하다 —
   이 RQ의 분모 사슬에 그 축은 아예 없다.

---

## 10. 후속 연구질문

1. L2b(probe 부재 2건)에서 결측이 `0.0`으로 코딩되는 경로는 collector 어디인가 — 그리고
   같은 코딩이 다른 필드에도 있는가.
2. 단조 결측(monotone MAR) 가정 아래의 축소 bound가 (d)의 부호를 식별하는가.
3. `fact_task_entry` 결측을 결과로 두는 association에서 IPW/selection model이 worst-case 대비
   얼마나 좁은 구간을 주는가, 그리고 그 가정이 L3 기전(결정론적 guard 차단)과 양립하는가.
4. `ACCOUNT_ACTION_BLOCKED` 25건에 대해 landing mart만으로 정의 가능한 대리 결과를 쓰면
   분모가 56으로 회복되는가.

---

## 11. 입력과 재현

`python tools/rq_d7_denominator_bounds.py` (seed 20260828, 결정론적).

| 입력 | sha256 (앞 16) |
|---|---|
| `results/D_OBSERVATION_TABLE_v2.csv` (66×65) | `c39c10f09f7a6a76` |
| `fact_landing_observation.json` (56행) | `4ed58b66e002d25c` |
| `fact_task_entry.json` (31행) | `61bb7051045ab27d` |
| `fact_interrupt_element.json` (235행) | `caebf1a4344a0b96` |
| `REAL_RUN_SUMMARY.json` | `ac454f8f99796dc9` |
| `FROZEN_MART_MANIFEST.json` | `656b5ac3e077579c` |
| worker batch 원장 16파일 | JSON `inputs.worker_batch_ledgers` |
| 선행 D 산출 (가설로만 수용, 전부 독립 재계산) | RQ-D1 `b8897e82…` · RQ-D11 `587695b9…` · RQ-D13c `5c1388a7…` · RQ-D8 `cb288f06…` |

**방화벽:** `denied_paths_not_opened: true` — `D_INPUT_ALLOWLIST.json`의 denied 목록을 하나도
열지 않았다. gold label을 생산하지 않았고, REAL_TARGET에 접속하지 않았으며(네트워크 사용 없음),
production/control/engine/mart/raw evidence를 수정하지 않았다(읽기 전용).
`holdout_accessed`는 self-report가 아니라 계약 모듈이 방화벽 스캔 결과에서 채웠다(`false`).

**그림:** `figures/RQ_D7_bounds_vs_cc.png` · `figures/RQ_D7_layer_decomposition.png`
