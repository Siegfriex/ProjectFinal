# EDA-00 — Frame & Provenance Audit

- 담당: P-A A2 (Analyst)
- 명세: `03_CRISP_DM_EXECUTION_PLAN_v2.0.md` Phase 2 / EDA-00
- 대상 스냅샷: **본 워크트리 `landing_pa_shadow`, base `d5f1da5`** `[SHADOW 재현검증]`
  (초판은 워크트리 `landing_v2_exec` / 커밋 `6fad79fa` 기준이었다. `state/*.parquet` 6종의
  sha256이 두 워크트리에서 **전건 동일**함을 확인한 뒤 입력 경로를 자기 워크트리로 돌렸다)
- 검사 스크립트: `analysis/eda/eda00_frame_provenance.py` (읽기 전용, `state/` 미변경)
- 전체 원시 출력: `analysis/out/eda00/eda00_raw_output.txt` · 실측값 JSON: `eda00_measured.json` · 발견: `eda00_findings.json`
- **재현 검증**: `d5f1da5`에서 재실행한 산출물 3종이 초판과 **바이트 동일**하다
- **이 문서의 모든 수치는 스크립트가 직접 계산한 것이다.** 문서에서 옮겨 적은 값은 "문서값" 열에만 있다.

이 단계는 **관측 기록**이다. 접근성 판정·해석은 하지 않는다.

---

## 0. 한 눈 요약

| 검사군 | 결과 |
|---|---|
| 행수·유일성 (13개 대조항목) | **전부 일치.** 문서값과 어긋난 행수 0건 |
| PK 유일성 (7개 표) | **중복 0** |
| 참조무결성 (FK 8방향) | **미매칭 0** |
| Orphan (역방향 6종 + 그룹 멤버십 3종) | **고아 0** |
| Source hash 검증 (18개 항목 직접 sha256 계산) | **불일치 0** |
| Certification raw HTML 230쪽 sha256 | **불일치 0** |
| Certification 매니페스트 ↔ parquet (10개 집계) | **전부 일치** |
| Certification raw HTML 독립 재파싱 2,283행 × 6필드 | **실질 불일치 0** (공백정규화 3건 제외) |
| 발견 | **P0 0건 · P1 9건 · P2 6건** (합 15) `[SHADOW 재현검증 시정]` |

> **재현 검증 (LANE A SHADOW, 2026-08-27).** 스크립트를 `d5f1da5`에서 재실행했다.
> `eda00_findings.json` · `eda00_measured.json` · `eda00_raw_output.txt` 전부 **바이트 동일**이다.
> 다만 **초판 요약행의 심각도 집계가 자기 F-표와 어긋나 있었다** — 요약은 `P1 8 / P2 7`,
> §12 F-표와 기계 산출은 `P1 9 / P2 6`이다. 총계 15는 같다. F-표가 옳으므로 요약행을 시정했다.
> 이 불일치는 그 자체가 발견이며 `PA-SHADOW-EDA00-SEVERITY-SUMMARY-MISMATCH`로 등재했다.

**P0는 없다.** 프레임과 계보는 건전하다. P1은 전부 **grain(입도) 함정과 인증 조인 준비**에 몰려 있으며, 데이터 손상이 아니라 **논리 스키마가 물리 grain을 잘못 가정한 지점**이다.

---

## 1. 행수·유일성 — 문서값 대조

### 1.1 표별 행수 (전부 직접 카운트)

| 물리 표 | 실측 행수 | 실측 컬럼수 | 문서값 | 판정 |
|---|---:|---:|---:|---|
| `panel_registry.parquet` | **17** | 26 | 17 | 일치 |
| `source_ranking_rows.parquet` | **261** | 16 | 261 | 일치 |
| `service_master.parquet` | **81** | 24 | 81 | 일치 |
| `entity_alias_map.parquet` | **82** | 8 | 82 | 일치 |
| `source_membership.parquet` | **142** | 7 | 142 | 일치 |
| `web_target_group.parquet` | **68** | 17 | 68 | 일치 |
| `certification_registry.parquet` | **2283** | 15 | 2283 | 일치 |

### 1.2 분할 대조

| 항목 | 실측 | 문서값 | 판정 |
|---|---:|---:|---|
| source rows · APP | **137** | 137 | 일치 |
| source rows · RETAIL | **124** | 124 | 일치 |
| panel · SERVICE_BRAND | **16** | 16 | 일치 |
| panel · INDUSTRY_CATEGORY | **1** | 1 | 일치 |
| entity · APP | **38** | 38 | 일치 |
| entity · RETAIL | **43** | 43 | 일치 |

추가 실측 (문서에 대응값 없음):

| 항목 | 실측 |
|---|---:|
| panel · domain | APP 8 / RETAIL 9 |
| source rows · axis_type | SERVICE_BRAND 231 / INDUSTRY_CATEGORY 30 |
| entity · axis_type | SERVICE_BRAND 71 / INDUSTRY_CATEGORY 10 |
| membership · domain | APP 71 / RETAIL 71 |
| alias · domain | APP 38 / RETAIL 44 |

### 1.3 PK 유일성

| 표 | 키 | 중복 |
|---|---|---:|
| `panel_registry` | `panel_id` | **0** (17/17) |
| `source_ranking_rows` | `source_row_id` | **0** (261/261) |
| `service_master` | `service_id` | **0** (81/81) |
| `entity_alias_map` | `alias_id` | **0** (82/82) |
| `source_membership` | (`service_id`,`panel_id`) | **0** (142/142) |
| `web_target_group` | `web_target_group_id` | **0** (68/68) |
| `certification_registry` | `certification_number` | **0** (2283/2283) |

### 1.4 자연키 후보 — 유일하지 **않은** 것들

| 후보 키 | nonnull | 고유 | 중복행 |
|---|---:|---:|---:|
| `service_master.canonical_service_key` | 81/81 | **81** | 0 |
| `service_master.service_name_canonical` | 81/81 | **80** | **1** |
| `service_master.(service_name_canonical, domain)` | 81/81 | **81** | 0 |
| `service_master.web_target_key` | 71/81 | **68** | **3** |
| `entity_alias_map.(entity_name_raw, domain, axis_type)` | 82/82 | **82** | 0 |
| `entity_alias_map.entity_name_raw` | 82/82 | **81** | **1** |
| `source_ranking_rows.(panel_id, rank, metric_name)` | 261/261 | **261** | 0 |
| `certification_registry.(list_page, list_index)` | 2283/2283 | **2283** | 0 |

중복 실체:

- `service_name_canonical = '쿠팡'` → `svc_79cd0e07c1eac5dc`(APP) / `svc_e22ebedb0e6c205f`(RETAIL)
- `entity_name_raw = '쿠팡'` → 2행, `domain`으로만 갈림
- `web_target_key` 3개가 2 entity 공유: `coupang` · `gmarket` · `naver`
- alias가 2개인 service 1건: `svc_353f07b932464b82` (현대홈쇼핑/현대Hmall + 현대Hmall**ord**)
- `match_basis` = `EXACT` 81 / `REVIEWED` 1

---

## 2. Orphan 검사

**모든 방향에서 고아 0건.**

### 2.1 정방향 FK (참조되는 PK가 실재하는가)

| FK | 좌변 nonnull | 미매칭 값 | 미매칭 행 |
|---|---:|---:|---:|
| `source_ranking_rows.panel_id` → `panel_registry` | 261 | **0** | 0 |
| `source_ranking_rows.figure_id` → `panel_registry.figure_id` | 261 | **0** | 0 |
| `source_membership.panel_id` → `panel_registry` | 142 | **0** | 0 |
| `source_membership.figure_id` → `panel_registry.figure_id` | 142 | **0** | 0 |
| `source_membership.service_id` → `service_master` | 142 | **0** | 0 |
| `entity_alias_map.service_id` → `service_master` | 82 | **0** | 0 |
| `service_master.web_target_group_id` → `web_target_group` | 71 | **0** | 0 |
| 유도 `source_row → service_id` → `service_master` | 261 | **0** | 0 |
| `entity_alias_map.panel_ids`(explode) → `panel_registry` | 142쌍 | **0** | 0 |
| `web_target_group.member_service_ids`(explode) → `service_master` | 71 | **0** | 0 |

### 2.2 역방향 (한 번도 참조되지 않은 부모 = 고아)

| 검사 | 부모 값 수 | 미참조 |
|---|---:|---:|
| `panel_registry.panel_id` ← `source_ranking_rows` | 17 | **0** |
| `panel_registry.panel_id` ← `source_membership` | 17 | **0** |
| `service_master.service_id` ← `source_membership` | 81 | **0** |
| `service_master.service_id` ← `entity_alias_map` | 81 | **0** |
| `service_master.service_id` ← 유도 source_row 조인 | 81 | **0** |
| `web_target_group.web_target_group_id` ← `service_master` | 68 | **0** |

### 2.3 entity ↔ web_target_group 양방향

| 검사 | 실측 |
|---|---:|
| `service_master.web_target_group_id`가 NULL인 entity | **10** — 전부 `axis_type=INDUSTRY_CATEGORY`, `web_eligibility_status=EXCLUDED_INDUSTRY_AXIS` |
| `member_service_ids` explode 총원 | **71** (distinct 71), `member_count` 합 71 |
| `member_count` 분포 | 1→**65**, 2→**3** |
| service_master에 없는 member | **0** |
| group_id는 있는데 그 그룹 멤버 목록에 없는 entity | **0** |
| member ↔ service_master 간 group_id 역참조 불일치 | **0** |

NULL 10건은 고아가 **아니라 의도적 제외**다 — 10건 전부 `EXCLUDED_INDUSTRY_AXIS`이고, `axis_type=INDUSTRY_CATEGORY`인 10건과 정확히 같은 집합이다.

---

## 3. 참조무결성 — 유도 경로 3중 교차검증

### 3.1 `source_ranking_rows ⋈ entity_alias_map ON (entity_name_raw, domain, axis_type)`

| 검사 | 실측 | 문서값(A2 §5.2.1) |
|---|---:|---:|
| alias 내 조인키 중복 | **0** | 0 |
| 좌변 행수 | **261** | 261 |
| 조인 결과 행수 | **261** | 261 |
| fan-out | **0** | 0 |
| 미매칭 | **0** | 0 |
| 유도 `(service_id, panel_id)` distinct | **142** | 142 |
| `source_membership` 행수 | **142** | 142 |
| 차집합 (유도−저장 / 저장−유도) | **0 / 0** | 0 |
| `alias.panel_ids` explode 쌍 | **142** | 142 |
| explode 쌍 vs 저장 membership 차집합 | **0 / 0** | 0 |

**세 경로(조인 유도 · 저장된 물리표 · alias explode)가 같은 답을 준다.** A2 §5.2.1 재검증 통과.

### 3.2 비정규화 컬럼 일관성 (전부 불일치 0)

| 검사 | 불일치 |
|---|---:|
| `source_membership.rank` == 조인 결과 `min(rank)` | **0** |
| `source_membership.n_metrics` == `panel_registry.n_metrics` | **0** |
| `source_membership.{domain, axis_type, figure_id}` == `panel_registry` | **0 / 0 / 0** |
| `source_ranking_rows.{domain, axis_type, figure_id, table_title, panel_label, period_label, period_axis}` == `panel_registry` | **전부 0** |
| `entity_alias_map.{domain, axis_type}` == `service_master` | **0 / 0** |
| `service_master.{app_row_count, retail_row_count, appears_in_app_panels, appears_in_retail_panels, alias_count}` == source row에서 재계산 | **전부 0** |

### 3.3 panel 행 회계

| panel_id | figure | domain | axis_type | n_metrics | rows_expected | rows_extracted | 실제 source rows | row_count_verification |
|---|---|---|---|---:|---:|---:|---:|---|
| fig01_t1 | fig01 | APP | SERVICE_BRAND | 1 | 15 | 15 | 15 | DECLARED_TOP_N |
| fig01_t2 | fig01 | APP | SERVICE_BRAND | 1 | 15 | 15 | 15 | DECLARED_TOP_N |
| fig02_t1 | fig02 | APP | SERVICE_BRAND | **4** | 15 | 15 | **60** | DECLARED_TOP_N |
| fig03_t1 | fig03 | APP | SERVICE_BRAND | 2 | 10 | 10 | **20** | DECLARED_TOP_N |
| fig04_t1 | fig04 | APP | SERVICE_BRAND | 2 | `NA` | 5 | **10** | VISUAL_COUNT_ONLY |
| fig04_t2 | fig04 | APP | SERVICE_BRAND | 1 | `NA` | 5 | 5 | VISUAL_COUNT_ONLY |
| fig05_t1 | fig05 | APP | SERVICE_BRAND | 3 | `NA` | 3 | **9** | VISUAL_COUNT_ONLY |
| fig05_t2 | fig05 | APP | SERVICE_BRAND | 1 | `NA` | 3 | 3 | VISUAL_COUNT_ONLY |
| fig06_t1 | fig06 | RETAIL | SERVICE_BRAND | 1 | 15 | 15 | 15 | DECLARED_TOP_N |
| fig06_t2 | fig06 | RETAIL | SERVICE_BRAND | 1 | 15 | 15 | 15 | DECLARED_TOP_N |
| fig07_t1 | fig07 | RETAIL | **INDUSTRY_CATEGORY** | 3 | 10 | 10 | **30** | DECLARED_TOP_N |
| fig08_t1 | fig08 | RETAIL | SERVICE_BRAND | 3 | 10 | 10 | **30** | DECLARED_TOP_N |
| fig09_t1 | fig09 | RETAIL | SERVICE_BRAND | 2 | 5 | 5 | **10** | DECLARED_TOP_N |
| fig10_t1 | fig10 | RETAIL | SERVICE_BRAND | 2 | `NA` | 5 | **10** | VISUAL_COUNT_ONLY |
| fig10_t2 | fig10 | RETAIL | SERVICE_BRAND | 1 | `NA` | 5 | 5 | VISUAL_COUNT_ONLY |
| fig11_t1 | fig11 | RETAIL | SERVICE_BRAND | 2 | `NA` | 3 | **6** | VISUAL_COUNT_ONLY |
| fig11_t2 | fig11 | RETAIL | SERVICE_BRAND | 1 | `NA` | 3 | 3 | VISUAL_COUNT_ONLY |

- `sum(rows_extracted)` = **142** (= membership 행수), `sum(actual)` = **261**, `sum(rows_extracted × n_metrics)` = **261**
- **`rows_extracted × n_metrics == 실제 source rows` 가 17/17 패널 전부 성립** (불일치 0)
- `rows_expected` nonnull **9/17** — 결측 8은 `VISUAL_COUNT_ONLY` 8과 정확히 같은 집합. 0으로 채워지지 않았다 (`01 §11` 준수)
- `rows_expected != rows_extracted` (nonnull 구간) = **0**
- `row_count_verification`: `DECLARED_TOP_N` 9 / `VISUAL_COUNT_ONLY` 8
- `row_count_ok`: `True` 9 / `<NA>` 8
- `n_metrics` 분포: 1→**8**, 2→**5**, 3→**3**, 4→**1** (A2 §5.1 문서값과 일치)
- `extraction_confidence`: **HIGH 17/17**
- `period_axis`: `HALF_YEAR` 16 / `SINGLE_MONTH` 1
- `source_section`: {1:8, 2:6, 3:2, 4:1}

→ `rows_extracted`는 "패널의 source row 수"가 **아니라** "패널에 실린 entity 수"다. 이름이 grain을 잘못 시사한다 (**F-01**).

---

## 4. Source hash / Provenance — 직접 재계산

### 4.1 sha256 전량 재계산 (18개 항목)

| 항목 | 파일 | 선언 bytes | 실측 bytes | sha256 |
|---|---|---:|---:|---|
| fig01 … fig11 (11개) | `sources/wiseapp/images/figNN.png` | 473361 … 348013 | **전부 동일** | **전부 일치** |
| extraction_journal (evidence manifest 기준) | `sources/wiseapp/extraction_journal/wf_bc403111-047_journal.jsonl` | 41926 | **41926** | **일치** |
| extraction_journal (`state/journal_provenance.json` 기준) | 동일 파일 | 41926 | **41926** | **일치** |
| `raw_assets.detail_json` | `raw/wiseapp933_detail.json` | 192139 | **192139** | **일치** |
| `raw_assets.rendered_html` | `raw/wiseapp933_rendered.html` | 166288 | **166288** | **일치** |
| `raw_assets.body_text` | `raw/wiseapp933_text.txt` | 13550 | **13550** | **일치** |
| `raw_assets.full_page_screenshot` | `raw/wiseapp933_full.png` | 3832287 | **3832287** | **일치** |
| `authority_manifest` 자기해시 (self_hash_recipe 재현) | `authority_manifest.json` | — | — | **일치** |

**해시 실패 0/18. P0급 불일치 없음.**

`authority_manifest.json`의 `self_hash_recipe`
(`sha256(json.dumps(without_self_field, ensure_ascii=False, sort_keys=True, separators=(',',':')))`)
를 그대로 실행해 `manifest_self_sha256_excluding_self_field`를 재현했다 — 판본 식별자가 실제로 동작한다.

### 4.2 저널 → 261행 재생성 주장 검증

| 주장 (`journal_provenance.json`) | 선언 | 실측 |
|---|---:|---:|
| `rows_rebuilt` | 261 | `source_ranking_rows` = **261** |
| `panels_rebuilt` | 17 | `panel_registry` = **17** |
| `figures_read` | 11 | evidence manifest figure = **11**, `panel_registry.figure_id` distinct = **11** |
| `cross_verifications` / `_agreeing` | 11 / 11 | 저널 파일 실제 라인 수 **44** (선언 44와 일치) |
| 증거는 있는데 패널이 없는 figure | — | **0** |
| `row_id_formula` = `row_ + sha256('{panel_id}\|{rank}\|{entity_name_raw}\|{metric_name}')[:16]` | — | **261/261 재현, 불일치 0** |
| `row_pointer_format` = `<figure_id>#t<table_index>/rank<rank>/<metric_name>` | — | **261/261 형식 준수, 위반 0** |

`source_row_id`를 문서에 적힌 식으로 261행 전부 직접 다시 계산해 봤고, 전부 재현됐다. **ID가 데이터에서 결정론적으로 유도된다는 주장이 참이다.**

### 4.3 해시가 선언되지 않은 파일 — **F-02 (P2)**

`sources/wiseapp` 아래 20개 파일 중 **4개가 어떤 매니페스트에도 sha256이 없다**:

- `sources/wiseapp/authority_manifest.json` (자기해시는 내부 필드로 있으나 외부 선언은 없음 — 실질적으로는 커버됨)
- `sources/wiseapp/source_evidence_manifest.json` (자기해시 필드 자체가 없음)
- `sources/wiseapp/raw/wiseapp933_api.json`
- `sources/wiseapp/raw/wiseapp933_images.json`

뒤의 두 raw 파일은 `authority_manifest.raw_assets` 4종(detail/rendered/text/screenshot)에 **포함되지 않았다.** 원자료 디렉터리 안에 있으면서 동결 대상이 아니다. `source_evidence_manifest.json`은 11개 figure의 해시를 담는 문서인데 **자기 자신은 해시가 없어**, 이 파일이 교체되면 탐지 경로가 없다.

---

## 5. Certification snapshot 완결성

### 5.1 매니페스트 ↔ parquet 재계산 (10개 집계 전부 직접 계산)

| 항목 | 매니페스트 선언 | 실측(parquet 재계산) | 판정 |
|---|---:|---:|---|
| `rows_raw` | 2283 | **2283** | 일치 |
| `rows_dedup` | 2283 | **2283** | 일치 |
| `status_breakdown.VALID` | 227 | **227** | 일치 |
| `status_breakdown.EXPIRED` | 2056 | **2056** | 일치 |
| `in_period_at_audit` | 226 | **226** | 일치 |
| `valid_at_audit` | 226 | **226** (`cert_valid_candidate` 합) | 일치 |
| `rows_with_target_url` | 2279 | **2279** | 일치 |
| `rows_without_target_url` | 4 | **4** | 일치 |
| `rows_with_scheme_less_target_url` | 26 | **26** | 일치 |
| `rows_without_period` | 1 | **1** (`certification_number=1812`, `service_name='-'`) | 일치 |
| `snapshot_status` | COMPLETE | — | — |

**`in_period_at_audit` 자체 재계산**: `audit_date=2026-08-26` 기준 `start <= audit <= end` 를 2,283행 전부 다시 판정 → **226**. 저장값과 **행 단위 불일치 0**.

### 5.2 raw HTML ↔ 파싱 행수 정합

| 검사 | 실측 |
|---|---|
| raw 디렉터리 파일 수 | **230** |
| 매니페스트 `page_hashes` 항목 수 | **230** |
| 디스크에만 있는 파일 / 매니페스트에만 있는 항목 | **0 / 0** |
| **230쪽 sha256 직접 재계산 불일치** | **0** |
| `card_count` 합 | **2283** |
| raw HTML에서 직접 센 `<article class="container cert-list …>` 총수 | **2283** |
| parquet 행수 | **2283** |
| `card_count` != parquet 페이지별 행수인 페이지 | **0** |
| raw HTML 카드수 != parquet 페이지별 행수인 페이지 | **0** |
| `list_page` 범위 | 1..229 (distinct **229**) — 230번째 페이지는 카드 0개(`stop_reason=NO_CARDS_AT_DECLARED_END`) |
| parquet 행이 0인 선언 페이지 | **0** |
| 행 단위 `raw_sha256` != 해당 `list_page`의 매니페스트 해시 | **0** |
| 페이지 배너 `전체 신청 수` 값 (230쪽 전부에서 추출) | **{2283}** 단일값, `전체 페이지` = **{229}** |

**원천 사이트가 스스로 선언한 총건수 2283 = 저장 raw 230쪽에서 센 카드수 2283 = parquet 2283.** 3중 일치.

### 5.3 raw HTML 독립 재파싱 — 필드 단위 대조 (2,283행 × 6필드)

기존 파서를 쓰지 않고 raw HTML을 처음부터 다시 파싱해 parquet과 대조했다.
`(list_page, list_index)` outer join → **both 2283 / parquet-only 0 / raw-only 0**.

| 필드 | 실질 불일치 | 공백정규화만 다른 건 |
|---|---:|---:|
| `certification_number` | **0** | 0 |
| `service_name` | **0** | **3** |
| `organization_name` | **0** | 0 |
| `cert_start_date` | **0** | 0 |
| `cert_end_date` | **0** | 0 |
| `certified_target_url_listed` | **0** | 0 |

공백정규화 3건 (**F-03 · P2**) — parquet 값이 raw보다 정규화돼 있다:

| page/idx | parquet | raw |
|---|---|---|
| 45/6 | `문화체육관광부 i-나루` | `문화체육관광부  i-나루` (공백 2개) |
| 177/2 | `누텔라 코리아 홈페이지` | `누텔라 코리아 홈페이지` (NBSP) |
| 201/3 | `이마트타운(모바일웹) 홈페이지` | `이마트타운(모바일웹)  홈페이지` (공백 2개) |

원문 상태 라벨 분포도 재계산: `만료` **2056** / `유효` **227** — `status_breakdown`과 일치.

### 5.4 `valid_on_audit_date` 는 존재하지 않는 컬럼 — **F-04 (P2)**

인계 문서는 `valid_on_audit_date = 226`이라 적었으나, `certification_registry.parquet`의 15개 컬럼에 **그런 이름은 없다.**
값 226을 갖는 것은 `in_period_at_audit`(합 226)와 `cert_valid_candidate`(합 226) 두 개이고 둘은 행 단위로 동일하다.
후속 단계가 컬럼명으로 조회하면 실패한다.

### 5.5 `VALID` 227 vs `valid_at_audit` 226 — **F-05 (P1)**

| 검사 | 실측 |
|---|---:|
| 원문 상태가 `유효`(VALID) | **227** |
| 그중 audit_date 기간 내 | **226** |
| **VALID인데 기간 밖** | **1** |
| 기간 내인데 VALID가 아닌 행 | **0** |

문제의 1건:

| certification_number | service_name | start | end | status |
|---|---|---|---|---|
| 2521 | 국립망향의동산 | **2026-08-27** | 2027-08-26 | 유효 |

**인증 시작일이 audit_date(2026-08-26)의 다음 날이다.** 사이트가 시작 전 인증을 미리 `유효`로 표시한다.
`cert_valid_candidate` 파생은 이 건을 올바르게 제외했다. 문제가 아니라 **감사일 경계 규약이 아직 문서화되지 않은 것**이며,
`01 §8`의 `certified_current` 정의가 "유효기간"을 어느 경계로 잡는지 명시해야 한다.

### 5.6 인증 레지스트리 분포·이상치

| 항목 | 실측 |
|---|---|
| `cert_start_date` 범위 | 2014-03-06 … 2026-08-27 |
| `cert_end_date` 범위 | 2015-03-05 … 2027-08-26 |
| 인증기간 일수 | mean **364.0**, median **364**, min **-1**, max **395** |
| 400일 초과 | 0 |
| 300일 미만 | **2** |
| **end < start** | **1** — `1095 / 주택관리공단 대표 홈페이지 / 2020-12-12 ~ 2020-12-11` (**F-06 · P1**) |
| `certification_number` | 전부 숫자, 범위 10..2522, 그 범위 내 결번 **230** |
| `service_name` distinct | **1282** / 2283행 |
| `organization_name` distinct | **691** |
| `(service_name, organization_name)` distinct | **1454** |
| `certified_target_url_listed` distinct | **1167** / 2279행 |
| 2건 이상 인증행을 가진 URL | **496** (최대 **11**회 — `http://www.bgnmh.go.kr`) |
| 2건 이상 인증행을 가진 service_name | **513** (최대 **7**회 — `국립재활원`) |
| **현재 유효 226행의 target url** | 226행 전부 보유, distinct **220** |

`end < start` 1건은 원천 사이트 표기 그대로이며(재파싱에서도 동일), 파이프라인 오류가 아니다.
다만 `certified_current` 판정 로직이 이런 행을 만나면 정의되지 않은 상태가 된다.

---

## 6. 결측 프로파일

### 6.1 표별 결측 요약 (컬럼 전량은 `eda00_raw_output.txt` §6)

| 표 | 결측 있는 컬럼 | null | null% |
|---|---|---:|---:|
| `panel_registry` | `subtitle` | 1 | 5.88 |
| | `rows_expected` | **8** | **47.06** |
| | `row_count_ok` | **8** | **47.06** |
| `source_ranking_rows` | `value` | **7** | 2.68 |
| | `value_label` | **7** | 2.68 |
| `service_master` | `review_decision`·`decision_rule`·`decision_basis`·`decision_evidence`·`decision_confidence`·`decided_at`·`decided_by` | **74 각각** | 91.36 |
| | `web_target_group_id`·`web_target_key`·`web_target_grouping_status` | **10 각각** | 12.35 |
| `entity_alias_map` | `reviewer_note` (빈 문자열) | 81 | 98.78 |
| `source_membership` | — | 0 | 0 |
| `web_target_group` | `expected_url_relationship_falsifier`·`_risk` | **65** | 95.59 |
| | **`web_target_url`** | **68** | **100.00** |
| | **`url_evidence`** | **68** | **100.00** |
| `certification_registry` | `certified_target_url_listed` | **4** | 0.18 |
| | `cert_start_date` / `cert_end_date` | **1 / 1** | 0.04 |

### 6.2 `01 §11` "결측 0 치환 금지" 위반 흔적 조사

| 프로브 | 실측 | 판정 |
|---|---:|---|
| `source_ranking_rows.value` 가 NULL | **7** | 결측이 결측으로 남아 있음 |
| `source_ranking_rows.value == 0` | **0** | **0 치환 흔적 없음** |
| `value`는 NULL인데 `value_label`은 존재 | **0** | 정합 |
| `value`는 존재하는데 `value_label`이 NULL | **0** | 정합 |
| `panel_registry.rows_expected` 결측 8건이 0으로 채워졌는가 | **아니오** (`Int64` NA) | 준수 |
| `app_row_count==0 AND retail_row_count==0` 인 entity | **0** | 유령 entity 없음 |

NULL 7행의 실체 — **전부 같은 자리다**:

- `panel_id = fig07_t1` 7행, `metric_name = 성장률` 7행, `unit = %` 7행
- 해당 패널의 `unreadable` 각주 원문: *"성장률(%) 컬럼은 이미지에 1위(인터넷 쇼핑, +10.1%), 5위(여행/교통, +15.9%), 10위(배달, +19.5%) 세 행에만 배지로 표기되어 있고 나머지 7개 행에는 표기가 없어 null 처리함"*

**미측정을 0으로 넣은 흔적은 발견되지 않았다.**

### 6.3 다만 — 구조적 0 (**F-07 · P2**)

`service_master`의 도메인별 카운터는 **해당 도메인에 존재하지 않아서 0**인 값을 갖는다:

| 컬럼 | 0인 행 | 그중 해당 도메인이 아예 아닌 entity |
|---|---:|---:|
| `appears_in_app_panels` | 43 | **43** (전부 RETAIL entity) |
| `app_row_count` | 43 | **43** |
| `appears_in_retail_panels` | 38 | **38** (전부 APP entity) |
| `retail_row_count` | 38 | **38** |

`01 §11`의 원칙("적용기회 없음 = NA")을 따르면 이들은 0이 아니라 NA다.
값 자체는 정확하지만(§3.2에서 재계산 불일치 0), **이 컬럼들에 평균·합계를 걸면 분모가 오염된다.**

### 6.4 상태값 분포 (A2 §1 재검증)

| 컬럼 | 실측 분포 |
|---|---|
| `service_master.review_decision` | NULL **74** / `KEEP_SEPARATE` **6** / `MERGE` **1** |
| `service_master.needs_human_review` | `False` **81** (True 0) |
| `service_master.decision_confidence` | NULL 74 / `HIGH` **7** |
| `service_master.web_eligibility_status` | `NOT_ASSESSED` **71** / `EXCLUDED_INDUSTRY_AXIS` **10** |
| `service_master.web_target_grouping_status` | `SINGLETON_PENDING_URL_REVIEW` **65** / NULL **10** / `CANDIDATE_PENDING_URL_REVIEW` **6** |
| `web_target_group.grouping_status` | `SINGLETON_PENDING_URL_REVIEW` **65** / `CANDIDATE_PENDING_URL_REVIEW` **3** |
| `web_target_group.expected_url_relationship_is_hypothesis` | `False` **65** / `True` **3** |
| `web_target_group.expected_url_relationship_confirmed_by_url` | `False` **68** (True **0**) |
| `web_target_group.expected_url_relationship_falsifier` 기재 | **3** |
| `entity_alias_map.match_basis` | `EXACT` **81** / `REVIEWED` **1** |

A2 §1.1이 실측했다는 `NOT_IN_REVIEW_QUEUE 74 / KEEP_SEPARATE 6 / MERGE 1 / PENDING_HUMAN_REVIEW 0`을
`review_decision × needs_human_review` 교차표로 재현했다 — **일치**.

**URL이 확정된 web target은 0개다.** 68개 그룹 전부 `web_target_url` NULL, `url_evidence` NULL, `confirmed_by_url=False`.

---

## 7. 분포·이상치

### 7.1 `rank`

| 항목 | 실측 |
|---|---|
| 범위 | 1 … **15** (mean 5.98, median 5) |
| `(panel, metric)` 그룹 중 rank가 1..n 연속이 아닌 것 | **0** |
| `(panel, metric, rank)` 중복 | **0** |
| `(panel, metric, entity_name_raw)` 중복 | **0** |

**정렬 위반·중복 없음.**

### 7.2 `metric_name` / `unit`

- `metric_name` distinct **23**, `unit` distinct **9** (A2 §5.1 문서값과 일치)
- `unit`별 행수: `%` **144**, `만 명` 30, `십억 원` 20, `인덱스(쿠팡=100)` 15, `백만 분` 15, `백만 회` 15, `회` 8, `만 원` 8, `만명` **6**
- **`만 명`(30행)과 `만명`(6행)이 공백 유무로 갈린 별개 값이다** — NFKC+공백제거 시 충돌하는 유일한 쌍이다 (**F-15 · P2**). 원문 표기 보존 원칙과는 충돌하지 않으나, `unit`으로 group by 하면 같은 단위가 둘로 갈린다
- `value` 극단값: `백만 분` 단위 max **33,272** (mean 4,613, std 8,183) — 유튜브 사용시간으로 보이는 단일 극단값. 이상치가 아니라 실제 분포의 꼬리
- `panel_registry.metric_columns` 길이 != `n_metrics` 인 패널 **0**
- `metric_columns`의 metric 이름 집합 != 실제 `source_ranking_rows.metric_name` 집합인 패널 **0**

### 7.3 entity 반복 출현 (유도)

| 등장 패널 수 | entity 수 |
|---:|---:|
| 5 | **2** (당근·농협하나로마트) |
| 4 | **2** (코스트코·모니모) |
| 3 | **15** |
| 2 | **17** |
| 1 | **45** |

패널별 source row 수 / membership 행 수:
`fig02_t1` 60 rows / 15 members, `fig07_t1`·`fig08_t1` 각 30 / 10, `fig01_t1`·`fig01_t2`·`fig06_t1`·`fig06_t2` 각 15 / 15.

---

## 8. Grain 함정

### 8.1 문서가 이미 지목한 3건 — 재확인

| # | 함정 | 실측 |
|---|---|---|
| T1 | `service_name_canonical`은 키가 아니다 | **80 고유 / 81행**, 중복 `쿠팡` 1쌍 (APP/RETAIL) |
| T2 | `entity_name_raw` 단독 조인은 fan-out | `쿠팡`이 2 도메인에 걸침. `axis_type`을 넘나드는 이름은 **0** |
| T3 | `dim_panel.metric_name`은 다중metric 패널에서 정의 불가 | `n_metrics>1` 패널 **9개** |

전부 문서값 그대로 재현됐다.

### 8.2 추가로 발견한 함정

**T4 — `source_membership`이 metric 축을 잃는다 (F-08 · P1).**
142행은 `(service_id, panel_id)` grain인데, 그 뒤에 있는 source row는 **261행**이다.
`(service, panel)` 쌍 **142개 중 66개가 2개 이상의 metric에 걸쳐 있다.**
`rank` 컬럼은 그 metric들에 걸친 `min(rank)`이다 (§3.2에서 불일치 0으로 확인).
다행히 **metric에 따라 rank가 달라지는 쌍은 0개**여서 현재 데이터에서는 정보 손실이 없다 —
그러나 그것은 §8.3의 사실(패널당 rank는 하나의 anchor metric이 정한다)의 결과이지, 표 구조가 보장하는 게 아니다.

**T5 — `rank`가 모든 metric 행에 복제돼 있다 (F-09 · P1).**
17개 패널 **전부** 정확히 하나의 metric만 rank에 대해 단조감소한다:

| panel | n_metrics | rank를 정하는 anchor metric | rank가 값을 정렬하지 **못하는** metric |
|---|---:|---|---|
| fig02_t1 | 4 | `점유율 합계` | `사용자`, `점유율 - 50대`, `점유율 - 60대 이상` |
| fig03_t1 | 2 | `성장률*` | `사용자 비율*` |
| fig07_t1 | 3 | `25년 12월 합산 순 결제추정금액` | `24년 12월 합산 순 결제추정금액` |
| fig08_t1 | 3 | `점유율 합계 (50대 이상)` | `점유율 - 50대`, `점유율 - 60대 이상` |
| fig09_t1 | 2 | `순 결제추정금액 성장률*` | `세대 비율*` |
| (나머지 12개 패널) | 1~3 | 각 1개 | 없음 |

anchor가 없는 패널 **0개**, rank가 정렬하지 못하는 `(panel, metric)` 쌍 **8개**.
→ `rank`는 `(panel, entity)` 1개짜리 값인데 metric 행마다 복제돼 있다.
8개 metric에 대해서는 rank에 **정렬 의미가 없고**, `source_membership.rank`도 같은 모호성을 물려받는다.
`fig04/10/11_t1`처럼 원문에 순위 숫자가 없어 "좌→우 배열 순서"로 부여한 rank도 섞여 있다 (`unreadable` 각주 실측).

**T6 — 업종 카테고리가 서비스 entity 표 안에 있다 (F-10 · P1).**
`service_master` 81행 = `SERVICE_BRAND` **71** + `INDUSTRY_CATEGORY` **10**.
후자 10건은 `편의점 · 배달 · 백화점/아울렛 · 전자기기 · 식품 · 식음료 · 홈쇼핑 · 인터넷 쇼핑 · 오프라인 마트 · 여행/교통`이고,
전부 `web_target_group_id` NULL · `EXCLUDED_INDUSTRY_AXIS`다. 측정 가능한 웹 대상이 아니다.
"entity 81"을 분모로 쓰는 어떤 비율도 10건만큼 틀린다. 실제 웹 대상 후보는 **71**이다.

**T7 — 같은 상태 라벨이 두 grain에서 다른 수를 센다 (F-11 · P2).**
`CANDIDATE_PENDING_URL_REVIEW` = `service_master`에서 **6** (entity grain), `web_target_group`에서 **3** (group grain).
`service_master`를 읽어 그룹을 세면 2배로 센다.

**T8 — 인증 조인은 이름으로도 URL로도 fan-out한다 (F-12 · F-13 · P1).**
`01 §8`의 `dim_certification`은 `web_target_id` grain을 가정하지만, 물리 레지스트리는 **인증 발급 이력 grain**이다.

| 조인 키 | distinct | 행 | 2건 이상 보유 키 | 최대 |
|---|---:|---:|---:|---:|
| `service_name` | 1282 | 2283 | **513** | **7** (국립재활원) |
| `certified_target_url_listed` | 1167 | 2279 | **496** | **11** (bgnmh.go.kr) |

현재 유효한 226행으로 좁혀도 URL은 **220 distinct** — 여전히 1:1이 아니다.
`certified_current` 판정은 반드시 **기간 필터를 조인 전에** 걸어야 하고, 그 뒤에도 중복 6건이 남는다.

**T9 — `figure_id`는 패널 식별자가 아니다 (P2).**
`fig01·fig04·fig05·fig06·fig10·fig11` 6개 figure가 각각 2개 패널을 담는다 (11 figure → 17 panel).

**T10 — grain 사다리 실측.**

```
source rows 261
  → (service, panel) 142
    → measurement entity 81   (그중 web 대상 후보 71 / 업종 10 제외)
      → web target group 68
        → URL이 확정된 group 0
```

`웹 대상`을 논할 수 있는 최대치는 **68 그룹 / 71 entity**이고, **URL이 확정된 것은 0**이다.
`expected_url_relationship_confirmed_by_url`이 68/68 `False`인 상태에서 그룹을 web target으로 간주한 어떤 집계도 근거가 없다.
검정 대기 중인 가설 3건:

| group | key | members | 관계 | falsifier |
|---|---|---|---|---|
| `wtg_5b8c59f6fd9839f7` | coupang | APP+RETAIL | SAME_LANDING_EXPECTED | 두 entity의 official_landing_url이 서로 다른 PSL 등록도메인이면 SPLIT |
| `wtg_f9fbd771ffcdbd42` | gmarket | APP+RETAIL | SAME_LANDING_EXPECTED | RETAIL 랜딩이 APP과 다른 등록도메인/경로면 SPLIT |
| `wtg_6d5510a695d0a614` | naver | RETAIL+APP | SAME_LANDING_EXPECTED | 동상 |

---

## 9. 발견 목록

| # | ID | 심각도 | 영역 | 한 줄 |
|---|---|---|---|---|
| F-01 | `EDA00-PANEL-ROWS-EXTRACTED-GRAIN` | **P1** | grain | `rows_extracted`는 source row 수가 아니라 entity 수다 — 9/17 패널에서 실제 행수와 다르고, `× n_metrics`를 해야 261이 된다 |
| F-02 | `EDA00-PROV-UNDECLARED-FILES` | P2 | provenance | `sources/wiseapp` 4개 파일에 sha256 선언이 없다 (`source_evidence_manifest.json` 자기해시 포함) |
| F-03 | `EDA00-CERT-REPARSE-WS-SERVICE_NAME` | P2 | provenance | parquet `service_name` 3건이 raw 대비 공백/NBSP 정규화돼 있다 (선언 없음) |
| F-04 | `EDA00-CERT-COLUMN-NAME` | P2 | schema | `valid_on_audit_date` 컬럼은 존재하지 않는다 — 실제는 `in_period_at_audit` / `cert_valid_candidate` |
| F-05 | `EDA00-CERT-VALID-NOT-IN-PERIOD` | **P1** | distribution | 원문 `유효` 227 중 1건(2521 국립망향의동산)은 시작일이 audit_date 다음 날 — 경계 규약 미문서화 |
| F-06 | `EDA00-CERT-DATE-ORDER` | **P1** | distribution | 인증 1건(1095)의 `end < start` (2020-12-12 ~ 2020-12-11), 원문 그대로 |
| F-07 | `EDA00-STRUCTURAL-ZERO-COUNTERS` | P2 | missingness | `service_master`의 도메인별 카운터 0은 미측정이 아니라 구조적 NA (`01 §11` 관점) |
| F-08 | `EDA00-GRAIN-MEMBERSHIP-METRIC` | **P1** | grain | `source_membership` 142행은 metric 축을 잃는다; 142쌍 중 66쌍이 다중 metric, `rank`는 min |
| F-09 | `EDA00-RANK-DENORMALIZED-ACROSS-METRICS` | **P1** | grain | `rank`는 패널당 1개 anchor metric이 정하는데 모든 metric 행에 복제돼 있다 — 8쌍은 rank에 정렬 의미 없음 |
| F-10 | `EDA00-GRAIN-INDUSTRY-IN-ENTITY-TABLE` | **P1** | grain | entity 81 = 브랜드 71 + 업종 10; 업종 10은 웹 대상이 아님 (`web_target_group_id` 전부 NULL) |
| F-11 | `EDA00-GRAIN-GROUPING-STATUS` | P2 | grain | `CANDIDATE_PENDING_URL_REVIEW`가 entity grain 6 / group grain 3 — 중복 계수 위험 |
| F-12 | `EDA00-GRAIN-CERT-NAME-FANOUT` | **P1** | grain | 인증 2283행 / 이름 1282종; 513개 이름이 다중 인증 (최대 7) |
| F-13 | `EDA00-CERT-URL-FANOUT` | **P1** | grain | 인증 URL 1167종 / 2279행; 496개 URL이 다중 인증 (최대 11). 유효 226행도 URL 220종 |
| F-14 | `EDA00-GRAIN-NAME-NOT-KEY` | **P1** | grain | `service_name_canonical` 80 고유 / 81행 — 표시명 조인 금지 (문서 지적 재확인) |
| F-15 | `EDA00-UNIT-NOT-NORMALIZED` | P2 | distribution | `unit`에 `만 명`(30행)과 `만명`(6행)이 공백만 다른 별개 값으로 공존 |

**P0 0건.** 해시·참조무결성·행수 전부 통과했다.

---

## 10. 재현

```bash
/home/sieg/projects-wsl/ProjectFinal/.venv/bin/python \
  /tmp/claude-1000/-home-sieg-projects-wsl-ProjectFinal/048877c5-056b-4469-96c5-f5e8a86875f5/scratchpad/pa/eda00/eda00_frame_provenance.py
```

산출: `eda00_raw_output.txt` (전체 로그) · `eda00_findings.json` · `eda00_measured.json`.
스크립트는 `state/` · `sources/` · `research/refcohort/**` 를 **읽기만** 한다.
