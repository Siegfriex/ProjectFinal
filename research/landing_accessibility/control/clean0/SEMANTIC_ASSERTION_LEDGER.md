# SEMANTIC_ASSERTION_LEDGER — CLEAN-0

**ID** `LA-SAL-2.1-20260827T2100` · **발행** Claude A
**규약** `docs/v2_1/03_ABC_ORCHESTRATION_PROTOCOL_v2.1.md §6`

> **타입 없는 핵심 주장은 acceptance 대상이 아니다.**
> 이 대장은 지금 유통 중인 핵심 주장에 타입을 붙여, **정의가 관측으로 승격되는 경로를 차단**한다.

---

## §1 타입 정의와 승격 규칙

| 타입 | 뜻 | 무엇으로 확정되나 |
|---|---|---|
| `DEFINITION` | 연구 조작화 — 무엇을 무엇이라 부르기로 했는가 | codebook / schema (T3) |
| `IMPLEMENTATION` | 코드가 실제로 그것을 한다 | exact SHA 의 코드 (T1) |
| `OBSERVATION` | 실제 수집에서 그 상태가 관측됐다 | raw artifact (T1) |
| `ANALYSIS` | 관측에서 계산된 값 | 독립 재현 계산 (T2) |
| `DECISION` | A 의 연구계약 | current SSOT (T4) |
| `PROJECTION` | 예측·추정 | 무엇으로도 확정되지 않는다 |

**승격 금지선 — 이 연구의 최대 위험**

```
DEFINITION  →  OBSERVATION      금지.  endpoint_definition 이 있다 ≠ endpoint_observed
IMPLEMENTATION → OBSERVATION    금지.  detector 를 구현했다 ≠ 그 신호를 관측했다
DECISION    →  OBSERVATION      금지.  A 가 GO 했다 ≠ 그것이 사실이다
PROJECTION  →  ANALYSIS         금지.  "될 것이다" ≠ "이다"
OBSERVATION →  DEFINITION       금지.  결과를 보고 정의를 바꾸는 것 = outcome-blind 위반
```

마지막 줄이 가장 자주 깨진다. **detector 성립률을 보면서 threshold 를 고치면
원하는 비율이 나올 때까지 조율하게 된다** (인계 §F-5).

---

## §2 현재 유통 중인 핵심 주장 — 타입 부여

### 2.1 파일럿 결과

| # | 주장 | 타입 | 근거층 | 비고 |
|---|---|---|---|---|
| S-01 | E001 attempted 59/59 | `OBSERVATION` | T1 | |
| S-02 | grade = PILOT / PRELIMINARY | `DECISION` | T4 | COLLECTION_WINDOW_RULE 의 사전선언 분기. **커버리지 100%가 등급을 올리지 않는다** |
| S-03 | Axis A = NOT_EVALUATED | `OBSERVATION` | T1 | 판정기 부재 = 산출 자체가 없음 |
| S-04 | Axis B mpfed_available 0/59 | `ANALYSIS` | T2 | |
| S-05 | Axis C raw measured / classification incomplete | `OBSERVATION` | T1 | A 가 mart 56행에서 직접 확인 |
| S-06 | planned association = NOT_COMPUTABLE | `ANALYSIS` | T2 | **substitute 를 만들지 않았다는 사실이 오늘의 통계 산출물이다** |
| S-07 | forbidden action 0 | `OBSERVATION` | T1 | |
| S-08 | mart 56행 ⊂ evidence 60관측, 고아 0 | `OBSERVATION` | T1 | **본 CLEAN-0 에서 A 가 신규 확인** |
| S-09 | evidence 66 dirs = 60 obs + 6 retry중복 | `OBSERVATION` | T1 | **본 CLEAN-0 에서 A 가 신규 확인** |

### 2.2 결함 진단

| # | 주장 | 타입 | 상태 |
|---|---|---|---|
| S-10 | task definition 이 원천 CSV 에 59/59 존재했다 · `granularity = archetype-level (7 distinct)` · UTILITY_ENTRY 6행은 CSV 자체가 `CODEBOOK_PENDING` | `OBSERVATION` | **C CONFIRMED_WITH_QUALIFIER** (D-R0-34) |
| S-11 | `default_task_definition()` 이 None/CODEBOOK_PENDING 을 하드코딩 | `IMPLEMENTATION` | **C CONFIRMED** |
| S-12 | area/endpoint detector 에 실사이트 구현이 없다 (F-1 P0) | `IMPLEMENTATION` | **C CONFIRMED (+probe 58/58 raw)** |
| S-13 | `*_signal_type` 이 프로덕션에서 소비되지 않는다 (F-2) | `IMPLEMENTATION` | **C CONFIRMED · 강화 (tests 호출도 0 @2281c85)** |
| S-14 | target-level guard 25/59, LOGIN 19 | `OBSERVATION` | **C CONFIRMED (25/19/QUERY 5)** |
| S-15 | 갭1·갭2 는 독립이며 한쪽만 고치면 결과가 동일하다 | `ANALYSIS` | **C CONFIRMED** |

> **[2026-08-27 21:00 갱신] C 가 `C_R0_QA.json @ 77d4b50` 에서 S-10~S-15 를 6/6 CONFIRMED 했다** (S-10 은 §D-R0-34 qualifier 포함). 아래 원문은 발행 시점의 상태로 보존한다.
>
> **S-10~S-15 는 아직 A 가 독립 확인하지 않았다.** 문서에 적혀 있다는 것은 T5/T6 이다.
> R0 GO 의 근거로 쓰려면 C 가 exact SHA 에서 재현해야 한다. **A 는 이것을 선언으로 덮지 않는다.**

### 2.3 현재 계약

| # | 주장 | 타입 |
|---|---|---|
| S-16 | ORIGINAL_E001 = READ_ONLY | `DECISION` |
| S-17 | REAL_TARGET = NO-GO until B구현 + C검증 + A명시GO | `DECISION` |
| S-18 | gold label producer ≠ B, ≠ C | `DECISION` |
| S-19 | 세 축을 단일 점수로 합치지 않는다 | `DECISION` |
| S-20 | KWCAG frozen subset 확대 금지 | `DECISION` |
| S-21 | offline frozen-DOM replay 는 허용 | `DECISION` |
| S-22 | 주 리플레이 모집단 n=56 (파일), E000 은 sensitivity-only | `DECISION` |

### 2.4 시간 — 전부 PROJECTION

| # | 주장 | 타입 |
|---|---|---|
| S-23 | 21:05 R0 GO / 21:40 label freeze / 22:30 integration / 23:15 offline / 23:50 pilot / 00:30 READY | `PROJECTION` |
| S-24 | minimum path 2h50m~3h20m · expected 3h40m~4h10m · blocker path 5~6h | `PROJECTION` |

**PROJECTION 은 게이트 통과 근거가 될 수 없다.** 시간이 밀리면 polish 를 버리고
measurement validity 는 버리지 않는다 (D-21).

---

## §3 이 세션에서 이미 작동한 타입 규율

`OBSERVATION` 이 `PROJECTION` 을 이긴 사례 — 본 CLEAN-0:

```
문서 baseline(T4/T5):  authoritative main = bc0b7a08
로컬 브랜치명 조회:     research/landing-accessibility-main = 32460b87
실제 원격(T1):         bc0b7a08

→ 브랜치 이름이 같아도 가리키는 커밋이 다르다. 이름은 권위가 아니다.
→ baseline 8개 SHA 는 원격과 전건 일치했다. 그러나 그것은 확인해서 알게 된 것이지,
  문서에 적혀 있어서 참인 것이 아니다.
```

## §3b 쉬운 대리물이 어려운 실체를 대신하는 형태 — 두 축에서 나타난다

`D-R0-70` 이 코드 축에서 이름 붙인 형태가 통계 축에서도 나타났다 (`D-R0-76 §1`).

```
코드 축   존재하는 신호        →  작동하는 것으로 대체     G1-a/b/c · 2.4.2 · hittable · 겹침
통계 축   계산하기 쉬운 점추정  →  알아야 하는 불확실성으로 대체   inter-labeler 0.750
A 자신    파일 크기            →  degenerate capture 의 대리   F-A1b
```

**세 plane 이 모두 이 형태로 틀렸다.** 특정 plane 의 습관이 아니라 작업의 성질이다.

## §4 운영 규칙

1. 모든 티켓의 `claim_kind` 필드에 타입을 넣는다 (스키마 필수 필드).
2. PASS 문서는 **"이 게이트가 검증하지 않은 것"** 절을 반드시 포함한다. 비면 PASS 를 발행하지 않는다.
3. **규율 1** 0건 보고는 대조군 없이 증거가 아니다 — 필요조건(스캔 대상 존재) · 충분조건(대조군 non-zero) · 음성대조(심은 위반 재검출).
3b. **규율 2** 비율은 n 과 구간 없이 근거가 아니다 (`D-R0-76-1`). 기준과 비교할 때 구간이 기준을 포함하는가·겹치는가·떨어져 있는가를 명시한다.
4. 철회한 주장은 "추가 확인"이 아니라 **"제거 확인"** 으로 검사한다.
5. 교정은 산출물만 고치면 되살아난다 — **스캔 대상에 생성 스크립트를 포함한다.**
