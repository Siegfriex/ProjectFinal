# MART FREEZE (14:10) — 수용 판정 기준 (A 사전 공개)

**작성** Claude A (Authority Plane), 2026-08-27 12:55 KST — **mart 도착 이전에 공개한다.**
**근거** A0 최종 지시 §13 · TIMEBOX §19 · `ANALYSIS_CONTRACT`

> 산출물을 본 뒤 기준을 만들면 그 기준이 산출물에 맞춰진다. B 와 C 는 무엇으로 판정될지
> 알고 만들 권리가 있고, 나는 14:10 에 몇 분 안에 판정해야 한다.

---

## 0. 판정의 성격

**mart 수용은 "숫자가 좋은가" 가 아니라 "숫자가 무엇인지 추적 가능한가" 의 판정이다.**
어떤 결과가 나왔는지는 이 판정의 근거가 **아니다.** N 이 작아도, FailRate 가 0 이어도,
association 이 없어도 **lineage 가 온전하면 수용한다.**

반대로 **결과가 아무리 좋아도 대조가 하나라도 어긋나면 반려한다.** 검증되지 않은 mart 로
돌린 통계는 오늘 산출물 전체를 무효로 만든다.

---

## 1. 8항 대조 — 전건 일치해야 수용

A0 §13 이 지정한 항목이다. 각 행은 **무엇과 무엇이 같아야 하는가**로 읽는다.

| # | 항목 | 통과 조건 |
|---|---|---|
| 1 | **row counts** | mart 행 수 == manifest 등재 관측 수 == 디스크 evidence run 수. **셋이 모두 같아야 한다** |
| 2 | **keys** | `observation_id` 유일 · NULL 0 · 중복 0 |
| 3 | **target coverage** | mart 의 target 집합 ⊆ frozen plan 59건. **plan 밖 target 이 1건이라도 있으면 반려** |
| 4 | **L0 coverage** | 각 관측에 L0 산출물(DOM·AX·CSS/geometry·screenshot) 존재 여부가 명시적으로 기록됨 |
| 5 | **L1 coverage** | 각 관측에 L1 종결상태 기록. **L0-only 관측이 joint-valid 로 세어지면 반려** |
| 6 | **UNDET** | `undetermined_n` / `undetermined_rate` 병기. `N/A` 와 `UNDETERMINED` 가 분리돼 있을 것 |
| 7 | **input SHA** | collector SHA · protocol SHA · plan hash · older-relevance registry sha256 이 mart provenance 에 박혀 있고 **선언값과 일치** |
| 8 | **manifest** | 해시 체인 검증 통과 · append-only 위반 0 |

---

## 2. 계약 정합 — `ANALYSIS_CONTRACT` 위반 시 반려

| 항목 | 통과 조건 |
|---|---|
| **joint-valid 계수** | J1~J4 로 세어졌고, `attempted_n` / `joint_valid_n` / `excluded_n` + **제외 사유별 분해**가 있을 것 |
| **제외 사유 분리** | `gate_reached_mpfed_null`(대상의 성질)이 `transport`/`timeout`/`l1_not_attempted`(우리 쪽 사정)와 **분리 집계** |
| **`BLOCKED` 처리** | gate 집합에서 제외되고 `ACCESS_REFUSAL` 로 따로 계수 |
| **older-relevance** | `older_relevance` 컬럼이 동결표(sha256 `da4b5208…`) 와 정확히 일치. 표 밖 criterion id 0건. **`2.4.7` 0건** |
| **FailRate 분모** | `EligibleOlderRelevant` = older-relevant 중 `final_status ∈ {PASS, FAIL}` 만. **22 를 분모로 쓰면 반려** |
| **분모 0 처리** | `EligibleOlderRelevant_i == 0` 이면 `FailRate = NULL`. **0 으로 대체돼 있으면 반려** |
| **ExcessDepth** | archetype 자기 median 만 사용. **pooled median 사용 시 반려** |
| **archetype 최소 N** | n>=5 정상 / 3~4 `LOW_N` 플래그 / <=2 `ExcessDepth = NULL`. **service row 제거 0건** |
| **execution_mode** | `{FIXTURE, SHADOW_DRY_RUN, REAL_TARGET}` 3값 밖 0건 (A2 S-3) |
| **outcome-blind** | frozen plan 순서 재정렬 흔적 0 · 결과를 본 뒤 target/task/archetype 변경 0 |

---

## 3. 연장 분기를 탄 경우 추가 (COLLECTION_WINDOW_RULE §3)

E001 개시가 13:15 를 넘겨 수집창을 연장했다면 다음이 **추가 필수**다.

- `undetermined_rate` 가 **수집 시각 구간별로 분해**돼 있을 것 (`sealed_at` 기준)
- 구간 간 차이가 유의하면 `LIMITATIONS.md` 에 "처리 순서에 기인" 명시
- `undetermined_rate` × `OlderRelevantKWCAGFailRate` **상관이 계산돼 있을 것.**
  상관되면 primary claim grade 가 **한 단계 강등**돼 있어야 한다
- archetype 편향 여부가 **확인되어 기록**돼 있을 것 (확인 없는 단정 금지)

---

## 4. C 와의 join

**B `MART_READY` + C `MART_QA_MATCH`** 두 결과를 받는다.

- **C1 mismatch 가 없으면 즉시 `MART_ACCEPTED`** → 통계 착수.
- C1 이 있으면 **해당 unit 을 quarantine 하고 나머지로 진행**한다. 전체를 세우지 않는다.
- **사소한 float 차이는 막지 않는다** — 대조 대상은 값의 마지막 자리가 아니라 계수·키·계보다.
- C timeout 시 A 가 위 §1 8항만 fallback 수행하고 진행한다. **C 부재가 single point of failure 가 되지 않는다.**

---

## 5. 반려할 때

**어느 항이 왜 깨졌는지 특정**해서 반려한다. "더 확인하면 좋을 것" 은 반려 사유가 아니다.
반려 후에도 시계는 멈추지 않으므로, **수정 가능한 최소 범위**만 지정한다.

---

## 6. 이 판정에서 하지 않는 것

- **결과의 내용을 보지 않는다.** N · rho · FailRate 값은 수용 근거가 아니다.
- **새 검사를 추가하지 않는다** (A0 §22 DO NOT DIG). 위 §1·§2 (+연장 시 §3) 가 전부다.
- **통계 결과를 미리 보지 않는다.** mart 수용 전에 결과를 보면 수용 판정이 오염된다.
