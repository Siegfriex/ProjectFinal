# EDA-01 — Wiseapp Source Structure

**담당** P-A A3 (Analyst) · **명세** `03_CRISP_DM_EXECUTION_PLAN_v2.0.md` Phase 2 / EDA-01
**입력** `research/landing_accessibility/state/*.parquet` (worktree **`landing_pa_shadow`, base `d5f1da5`**, READ-ONLY) `[SHADOW 재현검증]`
**재현** `d5f1da5`에서 재실행 — `eda01_console.txt` · CSV 3종 · PNG 3종 모두 **바이트 동일**
**스크립트** `eda01_source_structure.py` · **콘솔 전문** `eda01_console.txt`
**부산출물** `panel_summary.csv` · `entity_structure.csv` · `membership_normalized_rank.csv` · `figs/*.png`

> 이 문서의 모든 수치는 위 스크립트가 계산한 값이다. 문서에서 옮긴 값은 「문서값」으로 명시했다.
> 이 단계는 **구조·분포 기술통계**다. 접근성·인증 관련 해석/판정은 하지 않는다.
> 프레임·계보 무결성(orphan·hash·snapshot)은 EDA-00 담당 소관이며 여기서 다루지 않는다.

---

## 0. 한 장 요약

| 항목 | 실측 |
|---|---|
| panel | 17 |
| source row (`source_ranking_rows`) | 261 |
| **(entity, panel) membership** | **142** |
| measurement entity (`service_master`) | 81 |
| alias (`entity_alias_map`) | 82 (81 entity) |
| web target group (`web_target_group`) | 68 |
| `INDUSTRY_CATEGORY` entity (웹수집 제외) | 10 |
| **실제 매핑 대상 (SERVICE_BRAND entity)** | **71** (APP 38 / RETAIL 33) |
| P-B web target 수의 하한·상한 | **[68, 71]** |

---

## 1. 가장 중요한 구조적 사실 — `source_ranking_rows`의 grain

`261`은 **entity 행 수가 아니다.**

```
sum(panel_registry.rows_extracted)            = 142
sum(distinct entity per panel) over 17 panels = 142
sum(rows_extracted × n_metrics)               = 261
len(source_ranking_rows)                      = 261
dup(panel_id, entity_name_raw, metric_name)   = 0
```

즉 **grain(`source_ranking_rows`) = panel × entity × metric** 이다.
패널당 metric이 1~4개이므로 142개의 `(entity, panel)` membership이 261행으로 전개된다.

**함의 (P-A/P-B 모두에 해당).**
`00 §12`의 첫 시각화 `261 Source Rows → 81 Entities → …` 에서 261과 81 사이의 실제 중간 계단은
`142 (entity,panel) memberships`다. 261 → 81 을 한 화살표로 그리면 metric 전개와 패널 반복출현이라는
**두 개의 서로 다른 축소가 하나로 뭉개진다.** funnel을 그릴 때 `261 rows → 142 memberships → 81 entities
→ 71 mappable → 68~71 web targets` 로 계단을 분리할 것을 권고한다.
또한 "entity별 source row 수"(1~9)와 "entity별 패널 출현 수"(1~5)는 다른 양이므로 혼용하면 안 된다.

---

## 2. 패널별 N과 구성

`figs/fig1_panel_composition.png`

| panel | figure | domain | axis_type | sec | period_axis | rows_expected | rows_extracted | N_p(entity) | n_metrics | source rows | verification |
|---|---|---|---|---|---|---|---|---|---|---|---|
| fig01_t1 | fig01 | APP | SERVICE_BRAND | 1 | HALF_YEAR | 15 | 15 | 15 | 1 | 15 | DECLARED_TOP_N |
| fig01_t2 | fig01 | APP | SERVICE_BRAND | 1 | HALF_YEAR | 15 | 15 | 15 | 1 | 15 | DECLARED_TOP_N |
| fig02_t1 | fig02 | APP | SERVICE_BRAND | 2 | HALF_YEAR | 15 | 15 | 15 | **4** | **60** | DECLARED_TOP_N |
| fig03_t1 | fig03 | APP | SERVICE_BRAND | 3 | HALF_YEAR | 10 | 10 | 10 | 2 | 20 | DECLARED_TOP_N |
| fig04_t1 | fig04 | APP | SERVICE_BRAND | 1 | HALF_YEAR | **NULL** | 5 | 5 | 2 | 10 | VISUAL_COUNT_ONLY |
| fig04_t2 | fig04 | APP | SERVICE_BRAND | 1 | HALF_YEAR | **NULL** | 5 | 5 | 1 | 5 | VISUAL_COUNT_ONLY |
| fig05_t1 | fig05 | APP | SERVICE_BRAND | 2 | HALF_YEAR | **NULL** | 3 | 3 | 3 | 9 | VISUAL_COUNT_ONLY |
| fig05_t2 | fig05 | APP | SERVICE_BRAND | 2 | HALF_YEAR | **NULL** | 3 | 3 | 1 | 3 | VISUAL_COUNT_ONLY |
| fig06_t1 | fig06 | RETAIL | SERVICE_BRAND | 1 | HALF_YEAR | 15 | 15 | 15 | 1 | 15 | DECLARED_TOP_N |
| fig06_t2 | fig06 | RETAIL | SERVICE_BRAND | 1 | HALF_YEAR | 15 | 15 | 15 | 1 | 15 | DECLARED_TOP_N |
| **fig07_t1** | fig07 | RETAIL | **INDUSTRY_CATEGORY** | 2 | **SINGLE_MONTH** | 10 | 10 | 10 | 3 | 30 | DECLARED_TOP_N |
| fig08_t1 | fig08 | RETAIL | SERVICE_BRAND | 3 | HALF_YEAR | 10 | 10 | 10 | 3 | 30 | DECLARED_TOP_N |
| fig09_t1 | fig09 | RETAIL | SERVICE_BRAND | 4 | HALF_YEAR | 5 | 5 | 5 | 2 | 10 | DECLARED_TOP_N |
| fig10_t1 | fig10 | RETAIL | SERVICE_BRAND | 1 | HALF_YEAR | **NULL** | 5 | 5 | 2 | 10 | VISUAL_COUNT_ONLY |
| fig10_t2 | fig10 | RETAIL | SERVICE_BRAND | 1 | HALF_YEAR | **NULL** | 5 | 5 | 1 | 5 | VISUAL_COUNT_ONLY |
| fig11_t1 | fig11 | RETAIL | SERVICE_BRAND | 2 | HALF_YEAR | **NULL** | 3 | 3 | 2 | 6 | VISUAL_COUNT_ONLY |
| fig11_t2 | fig11 | RETAIL | SERVICE_BRAND | 2 | HALF_YEAR | **NULL** | 3 | 3 | 1 | 3 | VISUAL_COUNT_ONLY |
| **합계** | | | | | | **110** (9패널) | **142** | **142** | | **261** | |

- `rows_expected` **9/17 nonnull, 8행 NULL** — NULL 8개는 전부
  `fig04_t1 · fig04_t2 · fig05_t1 · fig05_t2 · fig10_t1 · fig10_t2 · fig11_t1 · fig11_t2`,
  전부 `row_count_verification = VISUAL_COUNT_ONLY`. `panel_scope`도 전부 `SUBSET:` 로 시작한다.
  **`rows_expected`와 `rows_extracted`의 불일치는 0** (둘 다 있는 9패널 기준). 0으로 치환하지 않는다.
- `row_count_verification`: `DECLARED_TOP_N` 9 / `VISUAL_COUNT_ONLY` 8. `row_count_ok`는 전자 9행만 `True`, 후자 8행은 `<NA>`.
- `extraction_confidence`: 17패널 전부 `HIGH`.
- `domain`: RETAIL 9 / APP 8. `axis_type`: SERVICE_BRAND 16 / **INDUSTRY_CATEGORY 1** (fig07_t1).
  `period_axis`: HALF_YEAR 16 / **SINGLE_MONTH 1** (fig07_t1).
- `n_metrics`: 1→8 / 2→5 / 3→3 / 4→1 패널.
- `source_section`: 1→8 / 2→6 / 3→2 / 4→1.
- `panel_scope` 접두: `SUBSET` 8 / `FULL` 4 / `THRESHOLD` 4 / `AGGREGATE` 1.
- `unreadable` 비어 있지 않은 패널 9개 — 순위 숫자 미표기(좌→우 배열로 rank 부여), 라벨 글리프 겹침,
  fig07_t1 성장률 3행만 배지 표기 등이 기록돼 있다.

### 2b. metric / unit 어휘 (행 수준)

- `metric_name` **23종**, `unit` **9종**.
- `value` / `value_label` NULL **각 7행**, 전부 `panel_id = fig07_t1` · `metric_name = 성장률` · `unit = %`.
  fig07_t1의 `unreadable` 노트가 이를 설명한다(원문에 1·5·10위만 배지 표기). **0이 아니다.**
- **관측 — unit 문자열 정규화 필요**: `만 명`(30행)과 `만명`(6행)이 별개 값으로 존재한다.
  같은 단위가 띄어쓰기로 갈렸다. `인덱스(쿠팡=100)`(15행)은 상대 인덱스라 다른 unit과 가산 불가다.
  `%`가 144/261행으로 압도적이다.

---

## 3. Entity 반복출현

`figs/fig2_entity_panel_appearance.png`

**panel appearance count 분포 (81 entity):**

| 출현 패널 수 | 1 | 2 | 3 | 4 | 5 |
|---|---|---|---|---|---|
| entity 수 | **45** | 17 | 15 | 2 | 2 |
| APP | 18 | 10 | 8 | 1 | 1 |
| RETAIL | 27 | 7 | 7 | 1 | 1 |
| SERVICE_BRAND | 35 | 17 | 15 | 2 | 2 |
| INDUSTRY_CATEGORY | **10** | 0 | 0 | 0 | 0 |

- 1개 패널에만 등장 **45** / 2개 이상 **36**. median 1, mean 1.753, max 5.
- **RETAIL 단일출현 27건 중 10건이 INDUSTRY_CATEGORY**다. 이를 빼면 SERVICE_BRAND 기준으로는
  단일출현 35 / 다수출현 36 으로 거의 반반이다.
- figure(도표) 단위로 세면 1→56 / 2→20 / 3→5. 같은 figure의 t1/t2 두 패널에 동시에 나오는 경우가 많아
  panel count보다 figure count가 낮다.
- entity별 **source row** 수 분포(metric 전개 후): 1→22, 2→16, 3→16, 4→6, 5→3, 6→10, 7→5, 8→2, 9→1. 최대 9행.

**5개 패널 등장 (최다):** `당근`(APP, 3 figure, 8 rows) · `농협하나로마트`(RETAIL, 3 figure, 8 rows)
**4개 패널:** `모니모`(APP, 9 rows — source row 최다) · `코스트코`(RETAIL, 6 rows)
**3개 패널 (15건):** 삼성카드 · 하나은행 · 현대카드 · 캐시워크 · NH콕뱅크 (APP) /
탑마트 · 현대홈쇼핑/현대Hmall · CJ온스타일 · 홈앤쇼핑 · NS홈쇼핑 · GS홈쇼핑/GS Shop · 쿠팡(RETAIL) /
G마켓 · 11번가 · 삼성 인터넷 브라우저 (APP)

---

## 4. Panel-normalized rank

### 정의 (본 분석에서 사용한 정의 — 명시)

패널 `p`의 distinct entity 수를 `N_p`, 원 rank를 `r ∈ 1..N_p` 라 할 때

```
norm_rank = (r − 1) / (N_p − 1)      ∈ [0, 1],  0 = 패널 최상단, 1 = 패널 최하단
rank_pct  = r / N_p                  ∈ (0, 1],  패널 내 위치의 비율
```

`N_p == 1` 이면 `norm_rank`는 **정의되지 않는다**(본 데이터에는 해당 패널 없음, 최소 `N_p = 3`).
정규화가 필요한 이유는 패널 N이 3 / 5 / 10 / 15 로 갈리므로 raw rank 3위의 의미가 패널마다 다르기 때문이다.
**이것은 기술통계이며 순위의 해석이 아니다.**

### 무결성

- **17패널 전부에서 rank 집합이 정확히 `1..N_p`** — 결번·중복·동점 없음.
- `(panel, entity)` 안에서 rank가 metric에 따라 달라지는 경우 **0건** (rank는 패널×entity 수준 값).

### membership 수준 분포 (142건)

| | count | mean | std | min | 25% | 50% | 75% | max |
|---|---|---|---|---|---|---|---|---|
| 전체 | 142 | 0.500 | 0.330 | 0 | 0.222 | 0.500 | 0.778 | 1.0 |
| APP | 71 | 0.500 | 0.329 | 0 | 0.218 | 0.500 | 0.782 | 1.0 |
| RETAIL | 71 | 0.500 | 0.333 | 0 | 0.222 | 0.500 | 0.778 | 1.0 |

**해석 주의(구조적 사실):** 모든 패널의 rank가 빠짐없이 `1..N_p`이므로 membership 수준의 `norm_rank`는
**패널마다 정의상 균등분포**다. 위 표의 평균 0.500·중앙값 0.500은 entity의 성질이 아니라
**패널 크기 구성의 산술적 귀결**이다. APP/RETAIL이 각각 71건으로 같은 것도 우연이 아니라
패널 구성(양쪽 각 71 membership)의 결과다. 이 수준의 분포로 서비스 간 비교를 하면 안 된다.

### entity 수준 (정보를 담는 축약)

entity별 `best_norm_rank = min(norm_rank over its panels)`:

| count | mean | std | min | 25% | 50% | 75% | max |
|---|---|---|---|---|---|---|---|
| 81 | 0.4639 | 0.3423 | 0 | 0.1429 | 0.5000 | 0.7778 | 1.0 |

- **어떤 패널에서든 1위를 한 entity = 13건** (`best_norm_rank == 0`):
  당근(5패널) · 코스트코(4) · 모니모(4) · G마켓(3) · 탑마트(3) · NH콕뱅크(3) · CJ온스타일(3) ·
  쿠팡RETAIL(3) · NS홈쇼핑(3) · YouTube(2) · 카카오톡(2) · 다음(1) · 인터넷 쇼핑(1, INDUSTRY_CATEGORY).
- 이 13건 중 `mean_norm_rank`는 0.000(다음)부터 0.662(당근)까지 넓게 흩어진다 —
  "1위를 했다"와 "전반적으로 상위다"는 서로 다른 양이다. 어느 쪽도 서비스의 중요도를 뜻하지 않는다.
- ECDF: `figs/fig3_best_norm_rank_ecdf.png` (APP n=38 / RETAIL n=43). 두 곡선은 거의 겹친다.

---

## 5. Source domain 교차

### 5.1 entity 수준 — 교차는 **0**

```
service_master.domain          : APP 38 / RETAIL 43
axis_type × domain             : SERVICE_BRAND  APP 38 / RETAIL 33
                                 INDUSTRY_CATEGORY  APP 0 / RETAIL 10
APP·RETAIL 양쪽에 행을 가진 entity : 0
```

`domain`은 entity 식별키 `(entity_name_raw, domain, axis_type)`의 구성요소이므로
APP 행과 RETAIL 행이 같은 `service_id`에 모일 수 **구조적으로 없다**. "양쪽 모두" 범주는
entity 수준에서 **정의상 공집합**이다. 따라서 domain 교차는 entity **위** 계층에서만 존재한다:

| 계층 | 양 domain에 걸친 건수 | 대상 |
|---|---|---|
| `service_name_canonical` (표시명) | **1** | `쿠팡` |
| `web_target_key` | **3** | `coupang`, `gmarket`, `naver` |
| `service_id` | **0** | — |

`service_name_canonical`은 81행 / **80 distinct** — 표시명은 유일키가 아니다(쿠팡 APP/RETAIL 충돌).
`canonical_service_key`는 81행 / **81 distinct** — 사람이 읽는 안정 자연키.
**조인은 반드시 `service_id` 또는 `canonical_service_key`로.**

### 5.2 저장값 재구성 대조 — **불일치 0**

`source_ranking_rows ⋈ entity_alias_map ON (entity_name_raw, domain, axis_type)`
(261행 → 261행, fan-out 0, 미매칭 0)로부터 재구성:

| `service_master` 저장 컬럼 | 재구성 정의 | 불일치 |
|---|---|---|
| `appears_in_app_panels` | APP domain에서 distinct panel 수 | **0** |
| `appears_in_retail_panels` | RETAIL domain에서 distinct panel 수 | **0** |
| `app_row_count` | APP domain의 **source row(metric 전개 후)** 수 | **0** |
| `retail_row_count` | RETAIL domain의 source row 수 | **0** |
| `alias_count` | `entity_alias_map` 내 해당 service_id 행 수 | **0** |

**컬럼 이름 주의 (P-A/P-B 실수 유발 지점).**
`*_row_count`는 **metric 전개 후 source row**를 센다. `*_panels`는 패널 수를 센다.

```
sum(app_row_count) + sum(retail_row_count)                 = 137 + 124 = 261
sum(appears_in_app_panels) + sum(appears_in_retail_panels) =  71 +  71 = 142
```

두 컬럼군은 서로 다른 grain의 합계다. `row_count`를 "몇 개 표에 나왔나"로 읽으면 안 된다.

---

## 6. Alias 구조

- alias **82행 / 81 service_id**. 한 entity만 alias 2개, 나머지 80개는 1:1.
- `match_basis`: **EXACT 81 / REVIEWED 1**.
- 다중 alias entity — `svc_353f07b932464b82` (`hyundai_homeshopping_hmall`, RETAIL):

| alias_id | entity_name_raw | panel_ids | match_basis |
|---|---|---|---|
| `als_6d3c1dd941c60431` | `현대홈쇼핑/현대Hmall` | fig08_t1, fig10_t1 | EXACT |
| `als_374ed3de3bfe9b79` | `현대홈쇼핑/현대Hmallord` | fig10_t2 | **REVIEWED** |

  reviewer_note에 따르면 fig10 하단 막대차트 라벨을 4배 확대 판독한 결과 원문 자체가
  `현대홈쇼핑/현대Hmallord`로 렌더링돼 있었고(발행물 오타), `entity_name_raw`는 보정하지 않고 별칭으로만 흡수했다.
- **조인키 유일성**: `(entity_name_raw, domain, axis_type)` 중복 **0**.
  `entity_name_raw` 단독으로는 `쿠팡`이 2행(APP/RETAIL) → **단독 조인 시 fan-out 발생.** 3요소 키 필수.
- **세 경로 일치 확인**: `alias.panel_ids` explode(142) ≡ 조인 유도(142) ≡ `source_membership`(142) — **완전 동일**.
  `source_membership.rank` vs 유도 rank 불일치 **0**, `source_membership.n_metrics` vs `panel_registry.n_metrics` 불일치 **0**.

---

## 7. Web target group 구조

- 그룹 **68** (`web_target_group_id` distinct 68).
- `member_count`: **1 → 65 / 2 → 3**. `sum(member_count) = 71`.
- `grouping_status` (**group 수준**): `SINGLETON_PENDING_URL_REVIEW` **65** / `CANDIDATE_PENDING_URL_REVIEW` **3**.
- `service_master.web_target_grouping_status` (**entity 수준**): `SINGLETON…` **65** / `CANDIDATE…` **6** / NULL **10**.
- `service_master.web_target_group_id`: nonnull **71** / null **10**(= INDUSTRY_CATEGORY 10과 정확히 일치),
  참조하는 distinct group **68**. 양방향 고아 **0** (미참조 그룹 0 / 미정의 그룹 참조 0).
- **URL은 전량 미확정**: `web_target_url` nonnull **0**, `url_evidence` nonnull **0**,
  `expected_url_relationship_confirmed_by_url == True` **0**.
- `expected_url_relationship`: `UNKNOWN` 65 / `SAME_LANDING_EXPECTED` 3.
  `expected_url_relationship_is_hypothesis == True` **3** (컬럼 자체는 68행 전부 nonnull).
- singleton 65건의 `grouping_basis`는 전부 동일 JSON:
  `rule = NO_SHARED_SOURCE_LABEL_SIGNAL`, `shared_signal = null`, `evidence_layer = A1_SOURCE_LABEL`.

### 다중 멤버 그룹 3건 — 가설과 falsifier

| # | group_id | key | members | domains | 가설 | 근거 | falsifier | 기록된 risk |
|---|---|---|---|---|---|---|---|---|
| 1 | `wtg_5b8c59f6fd9839f7` | `coupang` | `coupang_app`, `coupang_retail` | APP, RETAIL | SAME_LANDING_EXPECTED | 원문이 APP 패널(fig01_t1 r7 / fig01_t2 r10)과 RETAIL 패널(fig06_t1 r1 / fig06_t2 r1 / fig09_t1 r5)에서 **문자 단위로 동일한** `쿠팡` 표기를 씀 | 두 entity의 `official_landing_url`이 **서로 다른 PSL 등록도메인**으로 확정되면 SPLIT | 표기 동일성은 랜딩 동일성의 증거가 아니다. 앱 소개 페이지와 커머스 랜딩이 갈릴 수 있다 |
| 2 | `wtg_f9fbd771ffcdbd42` | `gmarket` | `gmarket_app`, `gmarket_auction` | APP, RETAIL | SAME_LANDING_EXPECTED | RETAIL 표기 `G마켓/옥션`(fig06_t1 r10)이 APP 표기 `G마켓`(fig03_t1 r2 / fig05_t1 r1 / fig05_t2 r2)을 **접두로 포함** | RETAIL entity의 랜딩이 다른 등록도메인/다른 경로로 확정되면 SPLIT | **세 후보 중 가장 약함.** RETAIL 측정 단위가 두 브랜드 합산이고 `옥션`이 별도 랜딩을 가지면 하나의 URL로 귀결되지 않음. `G마켓/옥션`은 본문 텍스트 계층에 없고 figure 판독 계층에만 존재 |
| 3 | `wtg_6d5510a695d0a614` | `naver` | `naver_naverpay`, `naver_app` | RETAIL, APP | SAME_LANDING_EXPECTED | RETAIL 표기 `네이버/네이버페이`(fig06_t1 r2 / fig06_t2 r7)가 APP 표기 `네이버`(fig01_t1 r4 / fig01_t2 r3)를 **접두로 포함**. 문자열 포함관계가 유일한 신호 | RETAIL entity의 랜딩이 다른 등록도메인/다른 경로로 확정되면 SPLIT | `네이버페이`가 독립 서비스 랜딩을 가지면 그룹 해체 |

세 그룹 모두 APP×RETAIL 교차이며, 세 가설 전부 **문자열 표기**에만 근거한다. URL 증거는 아직 하나도 없다.

---

## 8. INDUSTRY_CATEGORY 축 — 제외 10건의 정체

**10건 전부 `fig07_t1` 단일 패널 출신이며, 그 패널 밖에는 나타나지 않는다.**

| canonical_service_key | 표기 | domain | appears_in_retail_panels | retail_row_count | web_eligibility_status | web_target_group_id |
|---|---|---|---|---|---|---|
| `industry_convenience_store` | 편의점 | RETAIL | 1 | 3 | EXCLUDED_INDUSTRY_AXIS | NULL |
| `industry_delivery` | 배달 | RETAIL | 1 | 3 | EXCLUDED_INDUSTRY_AXIS | NULL |
| `industry_department_store_outlet` | 백화점/아울렛 | RETAIL | 1 | 3 | EXCLUDED_INDUSTRY_AXIS | NULL |
| `industry_electronics` | 전자기기 | RETAIL | 1 | 3 | EXCLUDED_INDUSTRY_AXIS | NULL |
| `industry_food` | 식품 | RETAIL | 1 | 3 | EXCLUDED_INDUSTRY_AXIS | NULL |
| `industry_food_beverage` | 식음료 | RETAIL | 1 | 3 | EXCLUDED_INDUSTRY_AXIS | NULL |
| `industry_home_shopping` | 홈쇼핑 | RETAIL | 1 | 3 | EXCLUDED_INDUSTRY_AXIS | NULL |
| `industry_internet_shopping` | 인터넷 쇼핑 | RETAIL | 1 | 3 | EXCLUDED_INDUSTRY_AXIS | NULL |
| `industry_offline_mart` | 오프라인 마트 | RETAIL | 1 | 3 | EXCLUDED_INDUSTRY_AXIS | NULL |
| `industry_travel_transport` | 여행/교통 | RETAIL | 1 | 3 | EXCLUDED_INDUSTRY_AXIS | NULL |

**데이터가 보여주는 제외 근거 (가정 아님, 실측):**

1. `fig07_t1`은 **17패널 중 유일하게 `axis_type = INDUSTRY_CATEGORY`** 인 패널이다
   (나머지 16패널은 전부 `SERVICE_BRAND`). 유일하게 `period_axis = SINGLE_MONTH` 이기도 하다.
2. `panel_scope` = `AGGREGATE: 24~25년 12월 월간 순 결제추정금액 50억 원 초과 브랜드를 업종으로 집계 (브랜드 축 아님)`
3. `universe_definition` = `… 50억 원이 넘는 리테일 브랜드를 **업종별로 분류하여 각 업종별 리테일 브랜드의
   순 결제추정금액 합을 산출**`
4. `table_title` = `업종별 액티브시니어+ 세대 순 결제추정금액* TOP10`
5. `web_eligibility_basis`(10건 동일 문자열) = `fig07_t1 의 축은 표 헤더가 '업종' 인 업종 카테고리다.
   브랜드가 아니므로 웹 수집 대상에서 제외한다.`
6. `fig07_t1`에 `SERVICE_BRAND` entity는 **0건** — 축이 완전히 갈려 있다.
7. 10건 전부 `web_target_group_id`가 NULL이고 `web_eligibility_status = EXCLUDED_INDUSTRY_AXIS`.

즉 **이들은 서비스가 아니라 브랜드를 묶은 업종 버킷**이며, 자기 자신의 랜딩 URL이라는 개념이 성립하지 않는다.
가설(제출 프롬프트의 추정)이 데이터로 확인된다.

**부수 관측:** `홈쇼핑`·`오프라인 마트`·`인터넷 쇼핑` 같은 업종명은 `fig10`/`fig11`의 `panel_scope`
(`홈쇼핑 업종 한정` / `오프라인 마트 업종 한정`)와 어휘가 겹친다. **업종은 SERVICE_BRAND 패널의
선별기준(scope)으로도 쓰이고 fig07_t1에서는 측정단위 자체로도 쓰인다.** 이 두 역할을 구분하지 않으면
"홈쇼핑"이 entity인지 필터인지 혼동될 수 있다. 매핑 레이어에서 업종 어휘는 **entity가 아니라 속성**으로만
쓰는 것이 안전하다.

---

## 9. P-A / P-B 함의

### 9.1 실제 매핑 대상 건수

```
전체 measurement entity                     81
  − INDUSTRY_CATEGORY (EXCLUDED_INDUSTRY_AXIS)  10
= 대표기능 매핑 대상 (SERVICE_BRAND)         71      (APP 38 / RETAIL 33)
```

`web_eligibility_status`: `NOT_ASSESSED` **71** / `EXCLUDED_INDUSTRY_AXIS` **10** — 71건은 아직 판정 전이다.
`needs_human_review`는 81건 전부 `False`.

`00 §6`이 "한 measurement entity당 원칙적으로 대표 task 1개"라 했으므로 **P-A A4/A5의 매핑 부하는 71건**이다.
`03`의 P-A는 "10~15건 pilot mapping"을 요구하므로 71건 중 10~15건이 파일럿, 나머지가 본매핑이 된다.

### 9.2 web target 수의 상·하한 (P-B 입력)

```
현재 group                              68
3개 SAME_LANDING 가설이 전부 성립       → web target 68
3개 가설이 전부 falsify(SPLIT)          → web target 71
                        ⇒ 최종 web target ∈ [68, 71]
```

`confirmed_by_url`이 **0건**인 현재, 68을 확정 수치로 쓰는 어떤 집계도 근거가 없다.
분모를 적을 때는 68/71 중 어느 쪽인지 명시하거나 구간으로 적어야 한다.

### 9.3 다중 패널 등장 entity(36건)를 어떻게 다룰 것인가

- 한 entity가 최대 5패널·9 source row에 걸쳐 있으므로 **source row를 단위로 집계하면 특정 서비스가
  최대 9배까지 중복 계수된다.** 기술통계·비교의 분석단위는 `00 §5`대로 **measurement entity / web target**이며,
  service-equal weighting(`00 §11` robustness)이 이를 전제한다.
- entity 수준으로 접을 때 rank를 어떻게 요약할지는 **선택**이며 결과가 달라진다.
  본 EDA는 `best_norm_rank`(min)와 `mean_norm_rank` 둘 다 산출해 `entity_structure.csv`에 남겼다.
  **P-A는 어느 쪽을 쓸지 명시적으로 동결해야 한다.** (본 문서는 선택하지 않는다.)
- 다중 패널 등장은 **metric 종류가 다른 패널**에 걸치는 경우가 대부분이다(예: 모니모 4패널 9행).
  패널을 가로질러 값을 합산·평균하면 단위가 섞인다(`%`·`만 명`·`백만 분`·`인덱스(쿠팡=100)` 등 9종).
  **패널 간 값 비교는 금지, rank 정규화만 비교 가능**하다.

### 9.4 매핑 레이어(`A2 §5.7` V-4~V-8)에 대한 실무 제약

- `dim_panel`의 `metric_name`/`unit` grain 문제(`A2 §5.1` 지적 1)는 실측상 **9개 패널에서 값이 하나로 정해지지 않는다**
  (`n_metrics > 1` 패널 = 5+3+1 = 9). 본 EDA는 `panel × entity × metric` grain이 실제 저장 grain임을 확인했으므로
  **② `dim_panel_metric`(panel × metric) 브리지 신설**이 데이터 구조와 자연스럽게 맞는다. 결정은 P-A 소관.
- `bridge_source_membership` view(261행)의 회귀검사 3종(행수 261 / fan-out 0 / 집합 동일 142)은
  본 EDA에서 **전부 통과**했고, 여기에 alias `panel_ids` explode 경로까지 더한 **세 경로 일치**도 확인했다.
- 조인 시 반드시 3요소 키 `(entity_name_raw, domain, axis_type)`. 표시명(`service_name_canonical`) 조인 금지.
- `entity_name_raw`는 매핑 후에도 **유지**해야 한다(`현대홈쇼핑/현대Hmallord` 사례처럼 원문 오타 계보가 여기에만 남는다).

### 9.5 슬래시 묶음 표기 — 대표기능 매핑의 실질 난점

`canonicalization_basis` 실측에서 `원문이 한 셀에 슬래시로 묶어 표기한 단일 측정 단위 — 분해하지 않고
그대로 1개 entity 로 둔다.` 가 **3건**이다. 여기에 `G마켓/옥션`·`네이버/네이버페이`·`현대홈쇼핑/현대Hmall`·
`GS홈쇼핑/GS Shop`·`백화점/아울렛`·`여행/교통` 같은 표기가 실제로 존재한다.
**한 entity가 둘 이상의 브랜드/서비스를 합산한 측정단위인 경우**, 대표기능(Interaction Archetype) 1개를
붙이는 것이 자명하지 않다. P-A codebook은 이 케이스의 처리 규칙을 명시해야 한다.

---

## 10. 문서값과 어긋난 항목 / 보완이 필요한 표기

| # | 위치 | 문서값 | 본 EDA 실측 | 성격 |
|---|---|---|---|---|
| 1 | `A2 §5.5` 표 — `web_target_status` 행 | "두 물리 값(`SINGLETON_PENDING_URL_REVIEW` 65 / `CANDIDATE_PENDING_URL_REVIEW` 3)" 을 `web_target_group.grouping_status` **와** `service_master.web_target_grouping_status` 양쪽에 붙여 서술 | **group 수준은 65/3**, **entity 수준(`service_master`)은 65/6/NULL 10**. 두 grain의 값이 다르다 | **grain 혼동 유발.** 3개 후보그룹이 각 2 member이므로 entity 수준 CANDIDATE는 6이다. 문서 표기 보정 권고 |
| 2 | `A2 §5.3` 표 — `review_status` | 실측 `NOT_IN_REVIEW_QUEUE` 74 / `KEEP_SEPARATE` 6 / `MERGE` 1 | 물리 `service_master.review_decision` 원값은 **NULL 74** / `KEEP_SEPARATE` 6 / `MERGE` 1. `NOT_IN_REVIEW_QUEUE`는 **NULL의 유도 라벨**이며 저장돼 있지 않다 | 문서가 `(b) DERIVED`로 명시하고 있어 모순은 아니나, 74가 **NULL**임을 읽는 쪽이 알아야 오조인을 피한다 |
| 3 | `A2 §5.2` 표 — `entity_alias_map` 관련 | "2개 별칭을 가진 유일한 service는 `현대홈쇼핑/현대Hmall` ↔ `현대홈쇼핑/현대Hmallord`(… `match_basis = REVIEWED`)" | 실측 일치. 단 **`match_basis = REVIEWED`인 것은 `Hmallord` alias 1건**이고 `Hmall` alias는 `EXACT`다(전체 EXACT 81 / REVIEWED 1) | 표기 정밀화 권고. 수치 불일치는 아님 |
| 4 | `00 §12` 시각화 1 | `261 Source Rows → 81 Entities → Web Target → Eligible → Measured` | 261과 81 사이에 **142 (entity,panel) membership** 계단이 빠져 있다. 261은 metric 전개 후 행수다 | funnel 계단 추가 권고 (§1) |
| 5 | `state` 데이터 자체 | — | `unit` 값에 `만 명`(30)과 `만명`(6)이 공존 | 정규화 대상. 원본은 불변이므로 매핑 레이어에서 처리 |

**나머지는 전부 문서값과 일치했다** — 261 / 142 / 81 / 82 / 68 / 17, fan-out 0, 미매칭 0,
세 경로 집합 동일, `rows_expected` 9/17 nonnull, `value` 결측 7행(fig07_t1 성장률),
`service_name_canonical` 81행/80고유, `canonical_service_key` 81고유,
`confirmed_by_url` 0 / `web_target_url` 0 / `url_evidence` 0, `member_count` 1→65 · 2→3,
`n_metrics` 1→8 · 2→5 · 3→3 · 4→1, `metric_name` 23종, `unit` 9종.

---

## 11. Figures

| 파일 | 내용 |
|---|---|
| `figs/fig1_panel_composition.png` | 패널별 distinct entity(N_p) vs source row(= N_p × n_metrics). metric 전개 배수 표기. APP/RETAIL 색 구분 |
| `figs/fig2_entity_panel_appearance.png` | entity의 panel appearance count 분포(1~5), APP/RETAIL grouped bar |
| `figs/fig3_best_norm_rank_ecdf.png` | entity별 `best_norm_rank` ECDF, APP(n=38) / RETAIL(n=43) |

- 색: `dataviz` 스킬 기준 팔레트 슬롯 1~2 (`#2a78d6` blue = APP, `#eb6834` orange = RETAIL).
  `validate_palette.js --mode light` 6검사 **전부 PASS** (CVD ΔE 24.7, normal ΔE 33.6, 대비 ≥3:1).
- 축·범례는 로마자/영문. **한글 라벨은 `NanumGothic`(`/usr/share/fonts/truetype/nanum/NanumGothic.ttf`)을
  matplotlib에 명시 등록해 렌더**했으므로 깨진 글자는 없다(기본 폰트 목록에는 CJK가 없어 명시 등록이 필요했다).
- 이중축 없음. 각 그림 1축.

---

## 12. 범위 밖으로 남긴 것

- frame/provenance 무결성(orphan · source hash · certification snapshot) → **EDA-00 담당**.
- Business Domain / Interaction Archetype 매핑 → **EDA-02 / P-A A4·A5**.
- web eligibility 판정, URL 확정 → **P-B**.
- 접근성·인증 관련 어떠한 해석도 하지 않았다. `00 §14` 금지 주장은 본 문서에 등장하지 않는다.
