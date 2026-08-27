# RQ-D8 — l0_probe cap 절단의 archetype 편향과 ExcessDepth baseline 왜곡

- **ticket**: `T-B-RQ-D-001 Q1` (from B), base_sha `2281c85`
- **plane**: D (Independent DS/ML Research Sandbox) — 비권위·GO권한 없음
- **tool**: `research_d/tools/rq_d8_cap_bias.py` (Restart→Run All, 입력은 CSV 하나)
- **machine-readable**: `research_d/results/RQ_D8_cap_bias.json`
- **figure**: `research_d/figures/RQ_D8_cap_by_archetype.png`

---

## 1. RQ

l0_probe의 4개 cap 절단이 `prior_archetype`에 대해 편향돼 있는가.
편향이 있다면 `ExcessDepth = MPFED − same-archetype median(MPFED)`의 baseline을 어떤 방향으로 왜곡하는가.
**이 n에서 검정력이 있는지부터 판단한다.**

## 2. 왜 중요한가

ExcessDepth는 archetype 내부 median을 baseline으로 빼는 상대지표다. cap 절단은 후보 풀의
**우측 절단(right-censoring)** 이므로, 절단이 특정 archetype에 몰리면 그 archetype의 baseline만
체계적으로 오염된다. baseline이 오염되면 (a) archetype 내 상대순위, (b) archetype 간 비교가
동시에 흔들린다. 즉 이건 "측정 노이즈"가 아니라 **분모/기준선의 문제**다.

## 3. 입력

| 항목 | 값 |
|---|---|
| 파일 | `research_d/results/D_OBSERVATION_TABLE.csv` |
| 행 × 열 | 66 observations × 64 columns |
| 다른 입력 | **없음.** raw 재파싱 없음, mart 미열람, gold label 미열람 (leakage 차단) |

cap 천장값(primary 200 / accessible_name 300 / target_size 300 / contrast 400, accessible_name만
visible 필터 없음)은 B가 `l0_probe.js @2281c85`에서 확인해 전달한 값이며, **본 RQ에서는 DEFINITION으로
수용**했다(코드 원본은 본 RQ의 허용 입력 밖).

## 4. 분석단위 (grain) — 먼저 고정한다

`[OBSERVATION]` 66 observations는 59 distinct target(`wtg`)을 덮는다. **7 target이 2회 실행**됐다
(브리핑에 적힌 "4 target"은 그중 mart canonical이 존재하는 4건만 센 값이다. 나머지 3 target은
두 실행 모두 probe 결측이라 애초에 측정 불가다).

| grain | 정의 | N | 비고 |
|---|---|---|---|
| observation | cap 4개 컬럼이 모두 non-null인 행 | **58 observations** | 54 distinct target만 덮는다 (중복 4) |
| target (canonical) | 위 + `in_mart==1` | **54 targets** | 본 문서의 **기준 grain** |

- missing: 66 → 58 (8 observations 탈락). 내역: `probe_present` 결측 6, `probe_present==0` 2.
- `in_mart==1`은 56 rows지만 그중 2건(`64d30ef262d8782d`, `ef06dc942ef3ccc9`)이 probe 부재 → 54.

`[ANALYSIS]` **B·C가 쓴 `/58`은 target 비율이 아니라 observation 비율이다.** 58 중 4건은 독립 target이
아니라 재실행이다. 그 4건은 전부 non-ITEM_DETAIL이고 전부 `cap_any==0`이라, observation grain에서는
비교군에만 무-절단 단위 4개가 추가되어 대비가 실제보다 커진다(§9 민감도).

`[OBSERVATION]` 재실행 4쌍은 cap 판정이 **4/4 일치**하고 원시 카운트도 사실상 동일
(예: `13ed070478ef62c3` n_acc 50 vs 51). cap 절단은 실행 간 재현되는 결정적 현상이지 우연이 아니다.

## 5. 사용 변수

`wtg`, `in_mart`, `prior_archetype`, `n_*`/`cap_*` (primary_action_candidates, accessible_name_sources,
target_size, contrast), `cap_any`, `cap_count`, `dom_element_n`, `dom_interactive_n`,
`probe_present`, `run_ts`. **gold label 계열은 사용하지 않았다.**

## 6. 방법

1. flag ↔ 임계값 정합성 검사 (`>=` vs `==` 차이가 존재하는지 먼저 배제)
2. 두 grain에서 cap-hit 독립 재계산 + Wilson 95% CI
3. B/C 수치 역산 재구성 (정의를 7가지 바꿔가며)
4. archetype × cap 교차표 (n 규칙: n≥5 정상 / n=3–4 LOW_N descriptive only / n≤2 해석금지)
5. **검정력 먼저**: 고정 주변도수(25 vs 29)에서 two-sided Fisher exact의 Monte-Carlo power,
   80% power MDE 곡선, archetype별 detectability floor
6. 2×2 Fisher exact (ITEM_DETAIL vs 나머지) + risk difference(Newcombe CI) + risk ratio(Katz CI)
   + conditional-MLE odds ratio CI. **p값 단독 보고 금지**
7. 7×2 전역검정은 permutation (min expected cell < 5 → 점근 χ²는 무효)
8. 교란 통제: dom_element_n 3분위 층화 + Mantel-Haenszel(RBG CI) + logistic + 크기보정 잔차검정
9. 민감도: grain, visible-필터 cap만 사용

## 7. 주요 결과

### 7.1 flag 정합성 `[OBSERVATION]`

4개 cap 모두 `flag==1 ⟺ n>=천장 ⟺ n==천장`이고 **천장 초과 행은 0건**이다
(n_gt_ceiling: 0/58 전 cap). → `>=` vs `==` 해석 차이는 어떤 수치 불일치도 설명하지 못한다.

### 7.2 cap-hit 재계산 (D의 값)

| cap | observation grain | target grain (canonical) | Wilson 95% (target) |
|---|---|---|---|
| primary_action_candidates (200) | **7/58** (12.1%) | **7/54** (13.0%) | 6.4%–24.4% |
| accessible_name_sources (300) | **13/58** (22.4%) | **13/54** (24.1%) | 14.6%–37.0% |
| target_size (300) | **6/58** (10.3%) | **6/54** (11.1%) | 5.2%–22.2% |
| contrast (400) | **8/58** (13.8%) | **8/54** (14.8%) | 7.7%–26.6% |
| `cap_any` (4-cap union) | **14/58** (24.1%) | **14/54** (25.9%) | 16.1%–38.9% |

`cap_count` 분포 (58 observations): 0→44, 1→6, 2→1, 3→2, 4→5.
**5/58 observations는 4개 cap을 전부 때렸다.**

### 7.3 B·C 수치 재구성 `[ANALYSIS]`

| 출처 | 주장 | D의 값 | 판정 |
|---|---|---|---|
| B `T-B-FINDING-002` | primary cap-hit **7/58** | **7/58** obs · **7/54** target | **재현됨.** 다만 `/58`은 target 분모가 아니다 |
| C `C-FINDING-212855` | 같은 값 **8/58** | **7/58** | **재현 안 됨** |
| C | cap-hit **15 target** 중 ITEM_DETAIL **11/15 (73%)** vs 전체 **43%** | cap-hit **14 target**, ITEM_DETAIL **11/14 (78.6%)**, 전체 **25/58 = 43.1%** | 분자·기저율은 정확히 재현, **분모만 +1** |

C의 8을 만들려고 시도한 정의: `flag==1`(7) · `n>=200`(7) · `n>200`(0) · `n==200`(7) ·
target grain(7/54) · 66행 NaN→0(7/66). **어느 것도 8이 아니다.** 정확히 8이 되는 재구성은 둘뿐이다:

- **(a) 컬럼 오독**: `cap_contrast`가 같은 grain에서 정확히 **8/58**이다.
- **(b) near-cap 임계**: `n_primary >= 180`이면 8/58 (절단되지 않은 n=188 단위 1건이 끌려들어옴).
  `n >= 190`은 다시 7이다.

C의 "15 target"도 같은 방향의 off-by-one이다. D의 14건은 **전부 `in_mart==1`이고 전부 서로 다른
target**이므로 중복계수로도 15가 나오지 않으며, motion/body_text 플래그까지 합집합에 넣어도
(`cap_any_6flag`) 여전히 **14/58**이다. C의 분자 11은 D와 일치하므로 **C의 잉여 1건은
non-ITEM_DETAIL**이고, 따라서 C의 73%는 실제(78.6%)를 **과소보고**한 값이다.

> `[ANALYSIS]` 세 플레인의 차이는 데이터 차이가 아니라 **전사(transcription) 수준의 차이**다.
> 그리고 셋 다 같은 함정을 공유한다 — `/58`을 target 분모처럼 읽는 것.

### 7.4 archetype × cap 교차표 (target grain, N=54)

| prior_archetype | n | tier | cap_any | primary | acc_name | target_size | contrast | median dom_element_n |
|---|---|---|---|---|---|---|---|---|
| ITEM_DETAIL | 25 | OK | **11/25 (44%)** | 5/25 | 10/25 | 5/25 | 6/25 | 795 |
| QUERY | 4 | LOW_N | **2/4** | 2/4 | 2/4 | 1/4 | 2/4 | **2105** |
| FINANCIAL_ACTION_ENTRY | 9 | OK | 1/9 | 0/9 | 1/9 | 0/9 | 0/9 | 567 |
| UTILITY_ENTRY | 5 | OK | 0/5 | 0/5 | 0/5 | 0/5 | 0/5 | 588 |
| COMMUNICATION_ENTRY | 4 | LOW_N | 0/4 | 0/4 | 0/4 | 0/4 | 0/4 | 626 |
| PLACE_LOOKUP | 4 | LOW_N | 0/4 | 0/4 | 0/4 | 0/4 | 0/4 | 538 |
| CONTENT_OPEN | 3 | LOW_N | 0/3 | 0/3 | 0/3 | 0/3 | 0/3 | 429 |

전역 7×2 permutation 검정 (10,000 perm): target grain **p=0.052**, observation grain **p=0.036**.
점근 χ²는 min expected cell 0.78이라 **무효**이므로 보고하지 않는다.

### 7.5 검정력 — 검정 이전에 `[ANALYSIS]`

고정 주변도수 ITEM_DETAIL n=25 vs 나머지 n=29, α=0.05 two-sided Fisher exact:

| 대조군 실제율 p0 | RR 1.5 | RR 2.0 | RR 3.0 | RR 4.0 | RR 6.0 |
|---|---|---|---|---|---|
| 0.05 | 0.03 | 0.07 | 0.19 | 0.33 | 0.66 |
| 0.10 | 0.06 | 0.14 | 0.39 | **0.71** | 0.99 |
| 0.15 | 0.08 | 0.22 | 0.66 | **0.94** | 1.00 |
| 0.20 | 0.11 | 0.33 | **0.84** | 1.00 | 1.00 |

- 관측된 효과(11/25 vs 3/29)에서의 power = **0.80**. 유의가 나온 건 n이 충분해서가 아니라
  **효과가 비정상적으로 커서**다.
- 관측 대조군율 p0=0.103 기준 **80% power MDE = RR 4.35 (risk difference +34.7pp)**.
- **이 n에서 배제할 수 없는 것**: RR 4 미만의 모든 편향. 즉 "ITEM_DETAIL의 절단 위험이 다른
  archetype의 3배"라는 가설조차 이 표본으로는 기각도 확인도 불가능하다(power 0.39).
- archetype별 바닥: 0/n만 관측된 archetype의 Wilson 상한 —
  CONTENT_OPEN(n=3) **0–56%**, COMMUNICATION_ENTRY/PLACE_LOOKUP/QUERY(n=4) **0–49%**,
  UTILITY_ENTRY(n=5) **0–43%**. **"이 4개 archetype은 절단되지 않는다"는 주장은 데이터가 전혀
  지지하지 않는다** — 절반 가까운 절단률도 배제되지 않는다.

### 7.6 2×2 효과크기 (ITEM_DETAIL vs 나머지, target grain N=54)

| cap | ID | 나머지 | risk diff (Newcombe 95%) | RR (95%) | OR cond-MLE (95%) | Fisher p |
|---|---|---|---|---|---|---|
| **cap_any** | 11/25 | 3/29 | **+0.337 (+0.100, +0.538)** | **4.25 (1.33, 13.56)** | 6.56 (1.42, 42.7) | **0.011** |
| accessible_name | 10/25 | 3/29 | +0.297 (+0.066, +0.501) | 3.87 (1.20, 12.51) | 5.58 (1.19, 36.6) | 0.023 |
| contrast | 6/25 | 2/29 | +0.171 (−0.025, +0.372) | 3.48 (0.77, 15.7) | 4.15 (0.65, 46.4) | 0.125 |
| target_size | 5/25 | 1/29 | +0.166 (−0.011, +0.359) | 5.80 (0.73, 46.4) | 6.77 (0.68, 343) | 0.085 |
| primary_action | 5/25 | 2/29 | +0.131 (−0.056, +0.329) | 2.90 (0.62, 13.7) | 3.30 (0.48, 38.0) | 0.229 |

`[ANALYSIS]` **B가 티켓에 올린 primary_action cap이 정작 archetype 편향의 근거로는 가장 약한
cap이다** (p=0.23, CI가 1을 넉넉히 포함). 편향 신호는 `accessible_name_sources`에 있다.
모든 CI 상한이 RR 12–46 수준으로 벌어져 있다 — **효과의 크기는 전혀 정해지지 않았다.**

### 7.7 cap 종류별 구조 `[OBSERVATION]`

- φ 상관(58 obs): primary↔target_size **0.917** (사실상 같은 모집단, Jaccard 0.857),
  primary↔contrast 0.773, primary↔acc_name 0.689, acc_name↔target_size 0.632.
- **acc_name이 구속조건(binding constraint)이다**: cap-hit 14건 중 **13건이 acc_name을 때렸고**,
  그중 **5건은 acc_name만** 때렸다. acc_name을 안 때린 cap-hit은 단 1건(`0ee385d0c964e560`,
  contrast만).
- acc_name만 visible 필터가 없다는 설계 차이가 그대로 관측된다. 극단 사례:
  `49a5eca8b58f7270` (ITEM_DETAIL)는 `dom_element_n=176`, `dom_interactive_n=23`인데
  `n_accessible_name_sources=300`으로 천장을 쳤다. **정적 DOM 스냅숏 크기로는 이 cap의 발화를
  예측할 수 없다** (SPA shell vs 렌더 후 시점 불일치 — RQ-D10 영역).

## 8. 반례 — "그냥 큰 사이트일 뿐" 대안설명 검토 `[ANALYSIS]`

대안가설: cap-hit은 ITEM_DETAIL이 아니라 **대형 페이지**에 몰린 것이고, archetype은 크기의 대리변수일 뿐이다.

**대안가설을 지지하는 증거 (강함)**
- cap_any별 `dom_element_n` 중앙값: hit **2799.5** vs no-hit **549** (Mann-Whitney p=9e-6, **AUC 0.904**).
  크기는 절단을 거의 완벽히 분리한다.
- logistic에서 `log10(dom_element_n)`의 OR = **200** (7.98, 5024), p=0.0013.

**대안가설을 약화시키는 증거**
- 정작 **ITEM_DETAIL이 특별히 큰 게 아니다**: 중앙값 795 vs 나머지 567,
  Mann-Whitney **p=0.157, AUC 0.613** — 크기 차이는 유의하지 않다.
- **QUERY가 직접 반례다**: 모든 archetype 중 median dom이 최대(2105 > ITEM_DETAIL 795)인데
  n=4에 cap-hit 2/4. "ITEM_DETAIL = 큰 페이지"라는 등식이 성립하지 않는다.
- dom 3분위 층화 후에도 방향이 유지된다:
  T1(11–429) ID 1/7 vs 기타 0/11 · T2(498–873) ID 1/8 vs 기타 0/10 ·
  **T3(945–13642) ID 9/10 vs 기타 3/8 (risk diff +0.525, Fisher p=0.043)**.
  Mantel-Haenszel OR = **22.0 (1.75, 277)**.
- 크기보정 잔차검정 (log10 n ~ log10 dom OLS 후 잔차 비교): ITEM_DETAIL의 잔차 중앙값이 모든 cap에서
  양수로 더 높다 — primary +0.165 vs −0.015 (AUC 0.640, p=0.080), target_size +0.130 vs −0.042
  (AUC 0.651, p=0.059), acc_name +0.112 vs −0.019 (AUC 0.626, p=0.114), contrast +0.109 vs +0.006
  (AUC 0.567, p=0.405). 즉 **ITEM_DETAIL은 DOM 크기가 예측하는 것보다 약 1.3–1.5배 많은 probe 후보를
  갖는다.** 이 검정은 절단된 행의 잔차가 하한값이라 **귀무가설 쪽으로 보수적**이다.

**직접 반례 목록**
- 절단 안 된 최대 DOM: `12e3942c0495b9a4` (ITEM_DETAIL, dom 2617, n_acc 251) — 큰 ITEM_DETAIL인데 무절단.
- 절단된 최소 DOM: `49a5eca8b58f7270` (ITEM_DETAIL, dom **176**, n_acc 300) — 작은데 절단.
- **ITEM_DETAIL 중 무절단이 14/25 (56%)** 로 여전히 다수다.

`[ANALYSIS]` **결론: 대안설명은 기각되지 않지만 충분하지도 않다.** 크기가 절단의 지배적 예측인자인 건
확실하고(AUC 0.90), archetype 효과는 크기 통제 후에도 남되 **그 잔여 신호는 전적으로 최대 3분위
1개 층(ID 9/10 vs 기타 3/8, 즉 18 targets)에서 나온다.** T1·T2 층은 사건이 각 1건이라 정보가 없다.
MH OR 22와 logistic OR 8.25는 같은 18건을 다르게 요약한 값이며, EPV = 14 events / 2 predictors = **7**
(통상 하한 10 미만)이므로 **조정 효과 추정치로 인용해서는 안 된다.** 서술적 증거로만 쓴다.

## 9. 민감도 분석

| 민감도 | cap_any 결과 | 판정 |
|---|---|---|
| **grain** (target 54 → observation 58) | RR 4.25 → 4.84, p 0.011 → **0.004** | 방향·크기 불변, **p는 불변 아님**. 추가된 4행은 전부 non-ITEM_DETAIL·전부 무절단 재실행 → 유사반복(pseudo-replication)이 대비를 부풀린다. **target grain을 canonical로 채택** |
| **visible 필터 cap만** (acc_name 제외) | 7/25 vs 2/29, RD +0.211 (+0.007, +0.413), RR 4.06 (0.93, 17.8), **p=0.065** | 방향 유지, 크기 유지, **유의성은 0.05 밖으로 나간다.** 신호가 acc_name 단독 산물은 아니지만 유의성은 그 cap에 의존한다 |
| **6-flag union** (motion·body_text 포함) | 14/58 (변화 없음) | cap 정의 확장에 강건 |
| **재실행 신뢰도** | 4/4 쌍이 cap_any 일치 | 측정 자체는 재현적 |
| **전역검정 grain** | permutation p 0.052 (target) / 0.036 (obs) | 두 grain에서 **결론이 0.05를 사이에 두고 갈린다** |

`[ANALYSIS]` **두 grain에서 결론이 바뀌는가?** 효과의 방향과 크기는 바뀌지 않는다. 유의성 이분법은
바뀐다(전역검정 0.036 ↔ 0.052). 이 RQ가 p값 단독 보고를 금지한 이유가 여기서 그대로 드러난다.

## 10. ExcessDepth baseline 왜곡 논증 `[PROJECTION]`

`[DEFINITION]` `ExcessDepth(u) = MPFED(u) − median(MPFED | prior_archetype(u))`

`[OBSERVATION]` **지금은 실측 불가다.** MPFED는 본 RQ 입력 테이블의 컬럼이 아니고,
frozen mart에서 **0/31 non-null**로 보고돼 있다(외부 사실로 수용). 따라서 아래는 전부
"MPFED가 가용해졌을 때의 왜곡 방향"에 대한 **PROJECTION이며, 관측된 ExcessDepth 값은 존재하지 않는다.**

**메커니즘**
1. cap은 후보 풀의 고정 천장 우측절단이다. 절단 이후의 모든 통계는 페이지가 아니라 **부분집합**에서 계산된다.
2. MPFED는 진입 후보 집합에서 도달 가능한 경로에 대한 **max형 통계**다. 절단은 후보를 제거만 하므로
   측정된 최대값은 참값의 **하한**이다 → **하향 편향이거나 불변, 상향은 불가능**.
3. 따라서 절단률이 높은 archetype의 same-archetype median MPFED는 참값 대비 **아래로 눌린다**.

**archetype 내부 방향**: ITEM_DETAIL은 11/25 (44%)가 절단됐다. baseline median이 눌리면
 (a) **무절단 단위**는 너무 낮은 baseline에 대해 채점되어 ExcessDepth가 **과대**해지고,
 (b) **절단 단위**는 눌린 MPFED를 눌린 median에서 빼므로 ExcessDepth가 **0쪽으로 압축**된다.
→ 순효과: **probe가 완전히 측정한 단위가 벌을 받고, 측정에 실패한 단위가 보상을 받는** 방향으로
archetype 내 순위가 뒤틀린다. 이는 노이즈가 아니라 **부호가 정해진 계통오차**다.

**archetype 간 방향**: 절단률 스펙트럼이 0/4 ~ 11/25로 완전히 벌어져 있다. archetype별 median MPFED를
직접 비교하면 "진짜 깊이 차이"와 "관측 완전성 차이"가 분리 불가능하다 —
"ITEM_DETAIL이 X보다 얕다"는 결과는 "ITEM_DETAIL이 X보다 덜 완전하게 측정됐다"와 구별되지 않는다.
ExcessDepth는 archetype **내부**에서 빼기 때문에 이 교란에 **부분적으로 면역**이지만,
**ExcessDepth 분포를 archetype 간에 비교하는 순간 교란이 그대로 재유입된다** —
각 baseline이 서로 다른 절단 수준에서 차감됐기 때문이다.

**크기 한계**: **추정 불가.** probe는 절단 전 총량 카운터를 내보내지 않는다. 몇 개가 버려졌는지
데이터에 없으므로 MPFED 하향 편향의 크기는 자료만으로 **상한조차 잡히지 않는다**.

**요구사항** `[IMPLEMENTATION]`: ExcessDepth를 비교 가능하게 만들려면 단위별로
(1) 절단 여부 플래그(이미 `cap_*`로 존재) **와** (2) **절단 전 총 개수 카운터**(부재)가 둘 다 필요하다.
(2)가 없으면 절단 단위는 **보정이 불가능하고 배제만 가능**하다.

## 11. VERDICT

> ## **PARTIALLY_SUPPORTED**

`[ANALYSIS]`
- **지지됨**: cap 절단은 `prior_archetype`에 대해 균일하지 않다. ITEM_DETAIL의 절단률은
  **11/25 (44%)** 로 나머지 **3/29 (10%)** 보다 높고 (risk difference **+33.7pp**,
  95% CI **+10.0pp ~ +53.8pp**, RR 4.25, Fisher p=0.011), 이 대비는 grain·cap 정의·크기 층화에
  대해 방향이 유지된다. 따라서 **ExcessDepth의 same-archetype median baseline이 archetype마다 다른
  수준으로 검열될 것**이라는 명제는 지지된다.
- **지지되지 않음**:
  (a) 절단을 추동하는 것이 페이지 크기가 아니라 archetype이라는 명제 —
      크기가 절단을 AUC 0.904로 분리하는 반면 archetype-크기 차이는 유의하지 않고(p=0.157),
      크기 보정 후 잔여 신호는 18 targets 한 층에만 존재한다.
  (b) 왜곡의 **크기**에 대한 어떤 주장도 — MPFED가 0/31 non-null이라 실측 ExcessDepth가 없고,
      절단 전 카운터가 없어 편향 크기의 상한이 잡히지 않는다.
- 4개 archetype(n=3–5)에 대해서는 **검정 자체가 성립하지 않는다(NOT_TESTABLE)**.
  0/n 관측의 Wilson 상한이 43–56%라, 이들이 "절단되지 않는다"고 말할 근거가 없다.

## 12. Limitations

1. **검정력.** 80% power MDE = RR 4.35. **RR 4 미만의 편향은 전부 배제 불가.** 유의가 나온 이유는
   n이 충분해서가 아니라 관측 효과가 RR 4.25로 MDE 근처까지 컸기 때문이다. 이건 *winner's curse*
   구간이며 관측 효과크기는 **상향 편향된 추정치일 가능성이 높다**.
2. **prior_archetype은 정답이 아니다.** `prior_mapping_status`는 CANDIDATE/AMBIGUOUS_UNRESOLVED이며
   gold label이 아니다. 라벨 오분류는 일반적으로 대비를 **희석**하므로 관측 효과는 하한일 수도 있으나,
   오분류가 크기와 상관되면 방향은 보장되지 않는다.
3. **교란 통제 변수 자체가 잘못된 슬롯이다.** `dom_element_n`은 정적 dom.html 스냅숏에서 나오고
   probe는 렌더 후를 본다. `49a5eca8b58f7270`(dom 176, name sources 300)이 그 증거다.
   **즉 §8의 크기 통제는 실제 노출 크기를 과소 통제했을 가능성이 있고, 그렇다면 남은 archetype 효과
   중 일부는 여전히 크기다.** (RQ-D10과 연결)
4. **층화 후 정보는 사실상 1개 층에 있다.** T3의 18 targets가 전부다. MH OR 22 (CI 1.75–277)와
   logistic OR 8.25 (EPV 7)는 서술적 값이지 조정 추정치가 아니다.
5. **cap 천장값은 D가 직접 검증하지 않았다** — B의 코드 판독을 DEFINITION으로 수용했다.
   다만 관측 데이터가 이와 정합적이다(천장 초과 0건, 정확히 천장에서만 flag).
6. **MPFED 실측 부재.** §10 전체가 PROJECTION이다.
7. **다중비교 미보정.** cap 5종 × 2 grain × 다수 민감도를 돌렸다. cap_any p=0.011은
   family-wise 보정 시 살아남지 못할 수 있다.
8. causal claim 없음. 전부 연관 서술이다.

## 13. Production implication `[IMPLEMENTATION]`

1. **`cap_any`(또는 `cap_count`)를 관측품질 플래그로 승격하고, 절단 단위를 baseline 산출에서 배제하라.**
   현재 ITEM_DETAIL median MPFED는 11/25가 검열된 집합에서 계산되게 된다. 배제하면 ITEM_DETAIL의
   baseline 표본은 14 targets로 줄지만 **검열되지 않은 baseline**이 된다. 이건 분모 손실이지 정보 손실이 아니다.
2. **archetype 간 ExcessDepth 비교를 금지하거나, 최소한 archetype별 절단률을 병기하라.**
   0/4 ~ 11/25 스펙트럼 위에서의 비교는 깊이와 관측 완전성을 섞는다.
3. **probe에 절단 전 총량 카운터를 추가하라** (`n_*_total_before_cap`). 이게 없으면 검열 단위는
   보정 불가·배제만 가능이다. 4개 카운터 추가는 저비용이고 절단 편향을 추정 가능한 문제로 바꾼다.
4. **`accessible_name_sources`의 visible 필터 부재를 설계 결함으로 등록하라.** 이 cap이
   14 cap-hit 중 13건의 구속조건이고 유일하게 렌더 크기와 정합하지 않는다. 다른 세 cap과 정책이
   다르면 `cap_any`는 이질적 사건의 합집합이 된다.
5. **B/C에 회신할 것**: primary cap-hit = **7/58 observations = 7/54 targets** (B 재현, C 미재현),
   cap-hit target = **14**(C의 15 아님), ITEM_DETAIL 비중 = **11/14 = 78.6%**(C의 73% 아님).
   그리고 **`/58`은 target 분모가 아니다** — 58 observations는 54 distinct targets를 덮는다.
   이 분모 오류는 세 플레인이 공유하고 있다.
6. **primary_action cap을 편향 근거로 쓰지 말 것.** 4개 cap 중 archetype 편향 증거가 가장 약하다
   (p=0.229). 티켓 본문이 이 cap을 지목했지만 신호는 accessible_name에 있다.

## 14. 추가 연구질문

- **RQ-D8a**: 절단 전 총량 카운터를 추가한 재수집에서, MPFED 하향 편향의 실제 크기는 얼마인가.
  (현재는 상한조차 없음)
- **RQ-D8b**: `dom_element_n`(정적)과 probe 후보 수(렌더 후)의 괴리를 관측단위 지표로 정의하면
  §8의 크기 통제를 제대로 할 수 있는가. → **RQ-D9/RQ-D10과 직접 결합**되는 선행조건이다.
- **RQ-D8c**: `prior_archetype`이 gold label로 확정된 뒤 같은 2×2를 재계산하면 효과크기가
  커지는가(오분류 희석 가설) 작아지는가(winner's curse 가설). **본 RQ의 재현 시험으로 사전등록 가치가 있다.**
- **RQ-D8d**: cap-hit 14 target을 배제했을 때 남는 40 targets에서 archetype coverage가 어떻게
  무너지는가. ITEM_DETAIL이 25→14로 줄면 계획된 association 추정의 분모가 또 깎인다. → **RQ-D7과 결합.**
- **RQ-D8e**: `accessible_name_sources`에 visible 필터를 적용하면 절단률이 13/54에서 얼마로
  떨어지는가. raw ax/dom에서 반사실 추정이 가능한가.
