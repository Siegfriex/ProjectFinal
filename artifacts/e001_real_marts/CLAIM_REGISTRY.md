# CLAIM_REGISTRY — E001

**스냅샷** 2026-08-27T16:30:39+09:00 (Asia/Seoul)

오늘 등재 가능한 등급은 **A**(정의·기술통계·직접 관측 + lineage 완전)뿐이다. association이 계산되지 않았으므로 그에 기반한 상위 등급은 **존재할 수 없고**, exploratory 등급도 **만들지 않았다** — 만들면 `substitute_made: false` 판정을 뒤집는 것이 된다.

등재 claim **12건**, 전부 등급 A. 새 claim을 만들지 않았다 — `STATISTICAL_RESULTS.md`에 이미 검증된 문장을 근거와 함께 옮겼다.

## `axis_c_descriptive-01` — GRADE A

> L0 산출물을 보유한 56개 관측에서 방해요소 235건이 탐지됐다.

- **metric**: fact_landing_observation · fact_interrupt_element 행수
- **effect**: 기술통계/직접 관측 — 효과크기 없음
- **sample_n**: 59 · **missing_n**: 0 · **undetermined_n**: 0
- **assumption**: 축 A 미평가로 판정 기반 지표 없음. 계수는 관측 outcome 층위.
- **robustness**: C 독립 재계산 전건 일치 (다른 조인 경로)
- **source_artifact_sha**: `sha256:caebf1a4344a0b96d793b2f14418c14ece7c3ebef788e8eb7033eb678093dbf6`

## `axis_c_descriptive-02` — GRADE A

> 그 235건 중 `final_label`이 `UNKNOWN`인 것이 110건(46.8%)으로 최대 범주다.

- **metric**: fact_interrupt_element.final_label 집계
- **effect**: 기술통계/직접 관측 — 효과크기 없음
- **sample_n**: 59 · **missing_n**: 0 · **undetermined_n**: 0
- **assumption**: 축 A 미평가로 판정 기반 지표 없음. 계수는 관측 outcome 층위.
- **robustness**: C 독립 재계산 전건 일치 (다른 조인 경로)
- **source_artifact_sha**: `sha256:caebf1a4344a0b96d793b2f14418c14ece7c3ebef788e8eb7033eb678093dbf6`

## `axis_c_descriptive-03` — GRADE A

> 56개 관측 중 22건(39.3%)에서 방해요소가 뷰포트를 완전히 덮었고, 6건은 겹침이 없었으며, 나머지 28건의 median은 0.0723이다.

- **metric**: max_overlay_coverage 3구간 분해 (median 단독 인용 금지 규칙 준수)
- **effect**: 기술통계/직접 관측 — 효과크기 없음
- **sample_n**: 59 · **missing_n**: 0 · **undetermined_n**: 0
- **assumption**: 축 A 미평가로 판정 기반 지표 없음. 계수는 관측 outcome 층위.
- **robustness**: C 독립 재계산 전건 일치 (다른 조인 경로)
- **source_artifact_sha**: `sha256:caebf1a4344a0b96d793b2f14418c14ece7c3ebef788e8eb7033eb678093dbf6`

## `axis_c_descriptive-04` — GRADE A

> 닫기 컨트롤이 탐지되지 않은 상태에서 ESC/배경클릭으로 닫힌 경우 102건, 컨트롤이 탐지됐으나 닫기가 실패한 경우 38건, 컨트롤이 탐지되고 닫힌 경우 64건, 컨트롤이 탐지되지 않고 닫히지도 않은 경우 30건이다.

- **metric**: dismiss_control_exists x dismiss_succeeded 4조합 동등 비중
- **effect**: 기술통계/직접 관측 — 효과크기 없음
- **sample_n**: 59 · **missing_n**: 0 · **undetermined_n**: 0
- **assumption**: 축 A 미평가로 판정 기반 지표 없음. 계수는 관측 outcome 층위.
- **robustness**: C 독립 재계산 전건 일치 (다른 조인 경로)
- **source_artifact_sha**: `sha256:caebf1a4344a0b96d793b2f14418c14ece7c3ebef788e8eb7033eb678093dbf6`

## `axis_b_cause_attribution-01` — GRADE A

> 59개 서비스 전수를 시도해 대표기능 진입 깊이(MPFED)가 산출된 것은 0건이다.

- **metric**: fact_task_entry.MPFED 전건 NULL
- **effect**: 기술통계/직접 관측 — 효과크기 없음
- **sample_n**: 59 · **missing_n**: 28 · **undetermined_n**: 0
- **assumption**: 축 A 미평가로 판정 기반 지표 없음. 계수는 관측 outcome 층위.
- **robustness**: C 독립 재계산 전건 일치 (다른 조인 경로)
- **source_artifact_sha**: `sha256:61bb7051045ab27ddc5b8105728b64c3f0df1c69c3f278d14087789fbcad0064`

## `axis_b_cause_attribution-02` — GRADE A

> 관측된 초기 화면 중 25개에 로그인/구매/가입 관련 텍스트 후보가 존재했고, 계정행동 가드가 그 지점에서 탐색을 중단시켰다(LOGIN — 등).

- **metric**: batch outcome=ACCOUNT_ACTION_BLOCKED · blocked_category
- **effect**: 기술통계/직접 관측 — 효과크기 없음
- **sample_n**: 59 · **missing_n**: 28 · **undetermined_n**: 0
- **assumption**: 축 A 미평가로 판정 기반 지표 없음. 계수는 관측 outcome 층위.
- **robustness**: C 독립 재계산 전건 일치 (다른 조인 경로)
- **source_artifact_sha**: `sha256:61bb7051045ab27ddc5b8105728b64c3f0df1c69c3f278d14087789fbcad0064`

## `axis_b_cause_attribution-03` — GRADE A

> 본 연구 계약이 대표기능 endpoint로 인정하지 않는 archetype에서 gate에 도달해 진입 깊이가 정의상 산출되지 않은 경우가 11건이다.

- **metric**: archetype-endpoint 규칙 (계약 설계)
- **effect**: 기술통계/직접 관측 — 효과크기 없음
- **sample_n**: 59 · **missing_n**: 28 · **undetermined_n**: 0
- **assumption**: 축 A 미평가로 판정 기반 지표 없음. 계수는 관측 outcome 층위.
- **robustness**: C 독립 재계산 전건 일치 (다른 조인 경로)
- **source_artifact_sha**: `sha256:61bb7051045ab27ddc5b8105728b64c3f0df1c69c3f278d14087789fbcad0064`

## `axis_b_cause_attribution-04` — GRADE A

> 탐색이 종결 상태에 이르지 못한 경우가 18건이며, 사유별로 {'MAX_SCOUT_WALL_CLOCK_S': 7, 'SCOUT_ERROR': 3, 'unresolved_reason_unrecorded': 6, 'MAX_CONSECUTIVE_NO_STATE_CHANGE': 2}로 분해된다. 사유가 기록되지 않은 6건은 다른 사유로 배정하지 않고 미기록으로 남겼다.

- **metric**: budget_reason 기준 분해 (endpoint_status_detail 단독 근거 사용 안 함)
- **effect**: 기술통계/직접 관측 — 효과크기 없음
- **sample_n**: 59 · **missing_n**: 28 · **undetermined_n**: 0
- **assumption**: 축 A 미평가로 판정 기반 지표 없음. 계수는 관측 outcome 층위.
- **robustness**: C 독립 재계산 전건 일치 (다른 조인 경로)
- **source_artifact_sha**: `sha256:61bb7051045ab27ddc5b8105728b64c3f0df1c69c3f278d14087789fbcad0064`

## `axis_b_cause_attribution-05` — GRADE A

> gate 종류 판별이 UNDETERMINED로 떨어져 fail-closed 규칙이 endpoint 승격을 거부한 발화가 8건이고, 그중 실제로 결과를 바꾼 것은 1건이다.

- **metric**: 발화와 구속의 구분 — 발화 횟수를 원인으로 쓰면 과대평가된다
- **effect**: 기술통계/직접 관측 — 효과크기 없음
- **sample_n**: 59 · **missing_n**: 28 · **undetermined_n**: 0
- **assumption**: 축 A 미평가로 판정 기반 지표 없음. 계수는 관측 outcome 층위.
- **robustness**: C 독립 재계산 전건 일치 (다른 조인 경로)
- **source_artifact_sha**: `sha256:61bb7051045ab27ddc5b8105728b64c3f0df1c69c3f278d14087789fbcad0064`

## `axis_b_cause_attribution-06` — GRADE A

> 가드가 개입하지 않고 탐색이 실제로 수행된, 계약상 승격 불가 archetype 25건에서 endpoint 도달은 0건이다.

- **metric**: 반사실 대조 — 가드가 구속 조건인지 확인
- **effect**: 기술통계/직접 관측 — 효과크기 없음
- **sample_n**: 59 · **missing_n**: 28 · **undetermined_n**: 0
- **assumption**: 축 A 미평가로 판정 기반 지표 없음. 계수는 관측 outcome 층위.
- **robustness**: C 독립 재계산 전건 일치 (다른 조인 경로)
- **source_artifact_sha**: `sha256:61bb7051045ab27ddc5b8105728b64c3f0df1c69c3f278d14087789fbcad0064`

## `axis_a_not_evaluated-01` — GRADE A

> 본 수집에서 KWCAG criterion 판정은 수행되지 않았다 — 판정기가 구현돼 있지 않다.

- **metric**: 저장소 전체에 criterion 평가 실행 경로 부재 · fact_criterion_result 0행
- **effect**: 기술통계/직접 관측 — 효과크기 없음
- **sample_n**: 59 · **missing_n**: 0 · **undetermined_n**: 0
- **assumption**: 축 A 미평가로 판정 기반 지표 없음. 계수는 관측 outcome 층위.
- **robustness**: C 독립 재계산 전건 일치 (다른 조인 경로)
- **source_artifact_sha**: `sha256:4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945`

## `axis_a_not_evaluated-02` — GRADE A

> 프레임 59개 중 현행 WA 인증 join 3요건 충족은 0건이었다.

- **metric**: dim_certification 0행
- **effect**: 기술통계/직접 관측 — 효과크기 없음
- **sample_n**: 59 · **missing_n**: 0 · **undetermined_n**: 0
- **assumption**: 축 A 미평가로 판정 기반 지표 없음. 계수는 관측 outcome 층위.
- **robustness**: C 독립 재계산 전건 일치 (다른 조인 경로)
- **source_artifact_sha**: `sha256:4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945`

---

계약이 지정한 통계 분석은 `NOT_COMPUTABLE`이며 대체물을 만들지 않았다(`STATISTICAL_RESULTS.json` `contract_specified_analysis`).