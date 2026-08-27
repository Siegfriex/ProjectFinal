# P-A A1 · Mapping Layer 구현 보고

| 항목 | 값 |
|---|---|
| 상태 | **`SHADOW_PREPARATORY`** · lane `LANE_A` · base `d5f1da5` (`PHASE_GATES` §4.3) |
| 산출 위치 | `research/landing_accessibility/analysis/mapping/` |
| 입력 | **본 워크트리**의 `research/landing_accessibility/state/*.parquet` — **읽기 전용** |
| 근거 문서 | `A2_VOCABULARY_AND_SCHEMA_BINDING.md` §5 (논리↔물리 대응표) · §1.1 · §5.7 규칙 V-1~V-8 · `01_DATA_SPEC` §2 · §11 |
| 실행 파이썬 | `/home/sieg/projects-wsl/ProjectFinal/.venv/bin/python` |

## 1. 산출물

| 파일 | 내용 |
|---|---|
| `analysis_interface.py` | 논리표 4종 + 보조 브리지 1종의 read-only materialization |
| `test_analysis_interface.py` | 불변조건 19개 회귀검사 (pytest) |
| `REPORT.md` | 이 문서 |

공개 API — `load_state()` → `StateFrames` (물리 5종) → `dim_panel` / `fact_source_ranking` /
`dim_measurement_entity` / `bridge_source_membership` / `dim_panel_metric` / `materialize_all(out_dir)`.
기본은 **in-memory view**이며 `materialize_all`만 parquet을 떨군다.
`materialize_all`은 `out_dir`가 원본 `state/`와 같으면 **거부**한다 (규칙 V-4/V-5).

## 2. 실측 수치 (모듈 실행 결과)

| 논리표 | grain | 행수 | 컬럼 |
|---|---|---|---|
| `dim_panel` | panel | **17** | `panel_id, domain, axis_type, source_section, period_axis, rows_expected, n_metrics` |
| `fact_source_ranking` | source row | **261** | `source_row_id, panel_id, measurement_entity_id, rank, raw_label, raw_value, raw_unit, entity_name_raw, metric_name` |
| `dim_measurement_entity` | entity | **81** | `measurement_entity_id, canonical_name, canonical_service_key, source_domain, entity_type, review_status` |
| `bridge_source_membership` | source row | **261** | `measurement_entity_id, panel_id, source_row_id` |
| `dim_panel_metric` (보조) | panel x metric | **31** | `panel_id, metric_index, metric_name, unit` |

파생 검증치:

| 검사 | 결과 |
|---|---|
| 조인 `source_ranking_rows ⋈ entity_alias_map ON (entity_name_raw, domain, axis_type)` | 261 → **261행**, fan-out **0**, 미매칭 **0** |
| distinct `(measurement_entity_id, panel_id)` | **142**, 물리 `source_membership`(142행)과 **집합 동일** |
| `source_membership.rank` == 유도 `min(rank)` | 불일치 **0** |
| 세 번째 경로 `entity_alias_map.panel_ids` explode | **동일 142쌍** (테스트로 고정) |
| `review_status` 유도 | `NOT_IN_REVIEW_QUEUE` **74** / `KEEP_SEPARATE` **6** / `MERGE` **1** / `PENDING_HUMAN_REVIEW` **0** (합 81) |
| `rows_expected` 결측 | **8행** 유지 (`Int64` nullable, 0 치환 없음) |
| `raw_value` / `raw_label` 결측 | 각 **7행** 유지 (0 치환 없음) |
| `service_name_canonical` 고유값 | **80 / 81** — 표시명 조인 금지 근거, 테스트로 고정 |
| `dim_panel_metric` 행수 | `sum(n_metrics)` = **31** 과 일치 |

모든 수치는 실행 시점에 parquet에서 유도된다. **하드코딩된 상수·매핑은 없다** —
코드의 상수는 조인 키 3요소와 `review_status` 열거형(A2가 정본으로 고정한 닫힌 집합) 뿐이다.
행수 단언은 전부 물리 프레임의 `len()`과 비교하는 형태다.

## 3. 불변조건 (전부 통과, 위반 시 `MappingInvariantError`)

- `fact_source_ranking`: 261행 = 물리 행수 · `source_row_id` 유일 · fan-out 0(`validate="many_to_one"` + 행수 비교) · `measurement_entity_id` 미매칭 0 · 결측수 물리와 동일
- `bridge_source_membership`: 261행 · `source_row_id` 유일 · distinct `(entity, panel)` = 물리 `source_membership` 행수 · **양방향 집합 동일** · `rank` 교차검증
- `dim_measurement_entity`: 81행 · `measurement_entity_id` 유일 · `canonical_service_key` 유일 · `review_status` 닫힌 집합 · 결측 0
- `dim_panel`: 17행 · `panel_id` 유일 · `metric_name`/`unit` 부재 단언 · `rows_expected` dtype `Int64` 유지
- `entity_alias_map` 조인 키 유일성 사전 검사 (`쿠팡` fan-out 방지)

pytest 19개 전부 통과. 실패 경로 2건(별칭 삭제 → 미매칭, 별칭 중복 → fan-out)도
예외가 실제로 던져지는지 테스트한다.

## 4. A2 §5.1 지적 1 — `metric_name` / `unit` grain 결정

A2는 결론을 내리지 않고 **①/② 중 택1을 P-A로 미뤘다** (§5.1 지적 1 · §6.1 "선택").
임의로 첫 metric을 고르는 것은 A2가 명시적으로 배제한 경로이므로 하지 않았다.

**채택: ①안 + ②안 병행.**

- `dim_panel`에서 `metric_name`·`unit`을 **제거**했다. panel당 metric 1~4개(`n_metrics` 1→8/2→5/3→3/4→1,
  다중 패널 9개)라 panel grain에서 단일값이 성립하지 않는다. 대신 `n_metrics`를 남겨
  "스칼라가 아니다"는 사실을 표에서 읽히게 했다 (규칙 V-7: grain을 이름/컬럼에 드러낸다).
- 스칼라 metric은 `fact_source_ranking.metric_name` / `raw_unit`(source row 261행 수준)에 있다.
- ②안은 손실 없이 보존하기 위해 **`dim_panel_metric`(31행) 보조 브리지**로 함께 제공한다.
  `panel_registry.metric_columns` JSON을 explode하며 `sum(n_metrics)`와 행수 일치를 단언한다.

즉 `01 §2`의 `dim_panel.metric_name`·`unit` 두 필드는 **논리표에서 그대로 재현할 수 없다**는
A2의 판정을 그대로 따랐고, 정보는 다른 두 표에 온전히 남겼다.

## 5. 구현 불가 / 논리표와 어긋난 항목

| 항목 | 처리 | 이유 |
|---|---|---|
| `dim_panel.metric_name` · `dim_panel.unit` (`01 §2`) | **미구현(의도적)** | grain 불일치. §4 참조. A2 §5.1이 "논리가 가정한 panel당 단일 `metric_name`은 성립하지 않는다"고 확정 |
| `dim_measurement_entity.entity_type` (`01 §2`) | `axis_type`로 바인딩 | `01`에 `entity_type` 정의 없음. A2 §5.3이 `SERVICE_BRAND`/`INDUSTRY_CATEGORY` 2값으로 바인딩하도록 확정 |
| `dim_measurement_entity.review_status` | 유도 | 물리 컬럼 없음. A2 §1.1 결정식(`review_decision` → `needs_human_review` → `NOT_IN_REVIEW_QUEUE`)으로 유도. `PENDING_HUMAN_REVIEW`는 현재 0건이며 이는 `needs_human_review`가 전 행 `False`이기 때문 |
| `fact_source_ranking.measurement_entity_id` | 유도 | 물리 컬럼 없음. A2 §5.2.1 3요소 조인 |
| `bridge_source_membership` 261행 vs 물리 142행 | 논리표 = 261행 유도, 물리 142행은 회귀검사 대상 | A2 §5.4 판정. 물리 `source_membership`을 논리 이름으로 노출하지 않았다 (규칙 V-7) |
| 논리에 자리 없는 물리 컬럼 `entity_name_raw` · `canonical_service_key` | **추가 보존** | A2 §5.2 · §5.3이 유지를 요구(계보 추적 · ID collision 검사 근거). 논리 스키마를 좁게 지키면 정보가 소실된다 |
| `dim_web_target` 외 나머지 논리표 | 범위 밖 | A2 §5.5·§5.6 — 전부 (c) ABSENT, 산출 Phase는 P-B/P-C/P-F |

**A2 대응표와 어긋난 지점: 없다.** 위 항목은 전부 A2가 미리 명시한 grain 불일치·DERIVED·보존요구를
그대로 구현한 것이며, A2가 P-A로 위임한 결정(§4의 ①/②)만 이 레이어에서 확정했다.

## 5a. 이관과 재현 검증 `[LANE A SHADOW · 2026-08-27]`

| 항목 | 결과 |
|---|---|
| 입력 경로 | `landing_v2_exec` 하드코딩 → **자기 워크트리 `state/`** 로 변경. 재지정은 `$LANDING_STATE_DIR` |
| 근거 | 두 워크트리의 `state/*.parquet` **6종 sha256 전건 동일**. 동시 작업 중인 다른 워크트리에 결과가 좌우되면 lane 격리가 깨진다 (`PHASE_GATES` §4.4) |
| 재실행 | `d5f1da5`에서 pytest **24 passed** (초판 19 + 신규 5) |
| 수치 일치 | §2 표의 **전 항목이 초판과 동일**하다 — 17 / 261 / 81 / 261 / 31, 142쌍, 결측 8·7·7, 고유명 80/81 |

## 5b. EDA-00 grain 결함의 매핑 레이어 반영 `[LANE A SHADOW]`

EDA-00이 P1로 올린 grain 결함 중 **매핑 레이어가 막을 수 있는 4건**을 코드로 반영했다.
문서 주석이 아니라 **컬럼과 불변조건**으로 넣었다 — 주석은 잘못된 조인을 막지 못한다.

| 발견 | 반영 | 실측 |
|---|---|---|
| **F-01** `rows_extracted`가 source row 수가 아니라 **entity 수**다 | `dim_panel`에 `n_entities_extracted`(= 물리 `rows_extracted`)와 `n_source_rows`(유도)를 **grain을 이름에 드러내** 분리 (규칙 V-7). 불변조건: `n_source_rows == n_entities_extracted × n_metrics` 전 패널 성립 + 총합 = 261 | 두 값이 갈리는 패널 **9/17** |
| **F-09** `rank`가 (panel, entity) 값인데 **모든 metric 행에 복제**돼 있다 | 신규 `rank_anchor_metrics(panel × metric)` 표 + `fact_source_ranking.rank_orders_this_metric` 컬럼. 불변조건: 패널마다 anchor metric이 **정확히 1개** | anchor `DESC` **17** / `ASC` 6 / `NON_MONOTONE` **8**. rank가 정렬하지 않는 fact 행 **119/261** |
| **F-10** entity 81은 **브랜드 + 업종 카테고리** 혼합이며 분모가 81이 아니다 | `dim_measurement_entity.is_web_mappable_entity`. 불변조건: 업종은 `web_target_group_id`가 전부 NULL, 브랜드는 전부 non-NULL | 매핑 대상 **71 / 81** |
| **F-08** 물리 142행이 **metric 축을 잃는다** | `bridge_source_membership`은 이미 261 grain. 추가로 "다중 metric 쌍이 실재한다"를 불변조건화 — 그것이 물리 `rank = min(rank)`가 **선택된 요약**임을 보증한다 | 142쌍 중 다중 metric **66쌍** |

**반영하지 않은 것과 이유.**

| 발견 | 처리 |
|---|---|
| F-11 grouping status의 두 grain | `web_target_group`은 T2(target identity)이며 **P-B 소관**이다. 이 레이어의 4표에 없다 |
| F-12 · F-13 인증 이름·URL fan-out | **인증은 이 레이어의 입력이 아니다** (`PHASE_GATES` §4.6 교차오염 금지). P-B join 인프라 소관 |
| F-14 표시명이 키가 아니다 | 초판이 이미 강제 중 — `canonical_service_key` 유일성 단언 + 조인은 id로만 |
| F-07 구조적 0 · F-15 `unit` 공백 변이 | grain이 아니라 결측·정규화 사안. 원본 불변 원칙상 매핑 레이어에서 **뷰로** 다룰 일이며 소비자가 생기는 시점(P-H)에 붙인다 |

## 6. 품질 게이트

| 도구 | 결과 |
|---|---|
| `ruff check` | All checks passed |
| `ruff format --check` | 2 files already formatted |
| `mypy --ignore-missing-imports` | Success: no issues found in 2 source files |
| `pytest -q` | **24 passed** (초판 19 + F-01/F-08/F-09/F-10 회귀검사 5) |

## 7. 규율 준수

- `state/*.parquet` **0건 수정**. 산출물은 `analysis/` 아래에만 쓴다.
- 브랜치 `agent/landing-pa-shadow`에만 커밋한다. `research/landing-accessibility-main` promotion **없음**.
- `state/*.parquet`은 `pd.read_parquet`만 사용. rename/migrate/write 없음.
- `research/refcohort/**` 접근 없음.
- 모든 경로 절대경로, `cd` 의존 없음.
