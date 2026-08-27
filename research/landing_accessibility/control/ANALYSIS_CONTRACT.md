# ANALYSIS CONTRACT — 2026-08-27 타임박스

**ID** `LA-AC-20260827`
**권위** A0 Research Director 결정 (`LA-TB-1630-20260827` 및 그 최종 오케스트레이션 지시)
**동결 시각** 2026-08-27 11:40 KST
**동결 주체** Claude A (control plane / Analysis Governor)

---

## 0. 이 문서가 존재하는 이유

여기 적힌 정의들은 **데이터를 보기 전에** 확정됐다. 그것이 이 문서의 존재 이유 전부다.

시간에 쫓기면 결과를 보고 나서 "어떻게 셀지"를 정하고 싶어진다. 그 순간
표본·지표·검정이 결과에 의해 선택되고, 그렇게 나온 수치는 연구 결과가 아니라
선택의 산물이 된다. **이 문서에 적힌 규칙은 결과가 어떻게 나오든 바뀌지 않는다.**

바꿔야 할 진짜 이유가 생기면 — 정의에 모순이 있거나 계산이 불가능하거나 —
**바꾼 사실과 시각과 이유를 §9 변경이력에 남기고**, 그 변경이 결과를 본 뒤에
이뤄졌다면 그 사실도 함께 적는다. 조용한 수정은 금지다.

이 문서는 측정 정의를 **새로 만들지 않는다.** `00_SSOT` · `A1` · `A2` ·
`02_COLLECTION_MEASUREMENT_SPEC` 가 정의한 것을 **오늘의 집계·검정 수준에서
조작화**할 뿐이다. 충돌하면 그 문서들이 옳고, 충돌 자체가 이 문서의 결함이다.

---

## 1. `joint-valid` — 표본 계수 규칙

> 이 정의는 어느 권위문서에도 없었다. A0 §6 에 등급 기준으로만 등장했다.
> **N 을 세는 규칙이 없으면 등급도 없다.** outcome-blind 상태에서 확정한다.

**joint-valid 관측 1건 = J1~J4 를 모두 만족하는 관측.**

| | 조건 | 근거 |
|---|---|---|
| **J1** | **L0 수집 완료** — DOM · AX · computed CSS · geometry · screenshot 존재 **그리고** evidence manifest 검증 통과 | 축 A·C 의 원천 |
| **J2** | **L1 이 정당한 terminal observation 에 도달** — `FUNCTION_ENDPOINT` **또는** archetype 계약상 정당한 `AUTH_GATE`/`LOGIN_GATE` 등 stop endpoint **또는** 프로토콜이 정의한 명시적 도달불가 terminal state | 축 B 의 원천 |
| **J3** | **MPFED 계산 가능** — `NED != NULL` **그리고** `IED != NULL`, `MPFED = NED + IED` | primary 의 X 축 |
| **J4** | **older-relevant KWCAG criterion 중 최소 1개**가 `UNDETERMINED` 가 아닌 판단(`PASS`/`FAIL`)을 가짐 | Y 축의 분모가 0 이면 값이 없다 |

### 1.1 반드시 구분해야 하는 것

**로그인·인증 벽은 관측 결과다. 수집 실패가 아니다.** 이 구분은 절대적이다.

> **정정 (2026-08-27 12:15, C 가 지적).** 이 절의 초판은 *"그 이유만으로 joint-valid 에서
> 제거하지 않는다"* 고 적었다. **그 문장은 실제 계수 규칙과 어긋났다.** 아래가 사실이다.

**A2 §1.5.1 이 지배한다** (`ANALYSIS_CONTRACT §0` — 측정 의미론은 권위문서가 정한다).
`endpoint_status != FUNCTION_ENDPOINT_REACHED` 이면 `NED`/`IED`/`MPFED = NULL` 이다.
gate 가 endpoint 로 승격되는 archetype 은 `FINANCIAL_ACTION_ENTRY`(로그인+본인인증) 와
`COMMUNICATION_ENTRY`(로그인만) 뿐이다(`00_SSOT §3` · A2 E-5~E-10).

**따라서:** 그 두 archetype 밖에서 gate 에 닿은 target 은 **J2 를 통과하고 J3 에서 탈락**해
joint-valid 에 들어가지 않는다. 이건 계약의 결함이 아니라 **MPFED 가 정의되지 않기 때문**이다 —
도달할 수 없는 지점까지의 깊이는 수(數)가 아니다.

**그럼에도 이들은 수집 실패가 아니다.** 다음을 반드시 지킨다:

1. **별도 제외 사유로 계수한다** — `gate_reached_mpfed_null`. 일반 `mpfed_null` 과도,
   `transport`/`timeout` 과도 **섞지 마라.** 전자는 대상의 성질이고 후자는 우리 쪽 사정이다.
2. **해당 서비스의 L0 접근성·obstruction descriptive 는 전부 보고한다.** 관측은 버려지지 않는다.
3. **이 수 자체가 결과다.** "대표기능이 인증 벽 뒤에 있는 서비스가 N 건" 은 entry friction 에 관한
   보고 가치가 있는 관측이며, `FINAL_RESULTS_SUMMARY.md` 에 **명시적으로 보고한다.**
   joint-valid 에서 빠졌다는 이유로 서술에서 사라지면 그것이 곧 은폐다.
4. `LIMITATIONS.md` 에 **primary association 의 표본이 "대표기능에 실제로 도달 가능한 서비스"
   로 한정된다**는 사실을 적는다. 이 선택편향은 결과 해석에 직접 영향을 준다.

**반대로 다음은 joint-valid 제외다:**

```
target wall-clock timeout   (360초 cap 초과)
transport failure
L1 자체를 시작하지 못함
```

이것들은 **우리 쪽 사정**이지 대상의 성질이 아니다.

> **절대 섞지 마라.** 타임아웃을 `UNDETERMINED` 로 기록하면 "판정할 수 없었다"(측정 결과)와
> "측정하지 못했다"(수집 실패)가 한 값이 된다. `00_SSOT` 의 UNDETERMINED semantics 와
> transport failure separation 을 **동시에** 위반한다.

### 1.2 joint-valid 필수조건이 **아닌** 것

`OverlayCoverage` · popup/obstruction completeness · WA certification.

이들은 secondary axis 다. 필수조건에 넣으면 **secondary 의 결측이 primary 표본을 깎는다.**
다만 결측률은 반드시 보고한다.

### 1.3 집계 시 항상 함께 보고 — 총계만 보고 금지

```
attempted_n
joint_valid_n
excluded_n
  ├─ transport                              (우리 쪽 사정)
  ├─ timeout                                (우리 쪽 사정 — 360초 cap)
  ├─ l1_not_attempted                       (우리 쪽 사정)
  ├─ gate_reached_mpfed_null                (**대상의 성질** — §1.1)
  ├─ mpfed_null                             (그 외 사유로 NED/IED 미정의)
  ├─ all_older_relevant_kwcag_undetermined
  └─ (기타 명시 상태별)
```

### 1.4 등급 (A0 §6)

| 등급 | joint_valid_n |
|---|---|
| GREEN | >= 36 |
| YELLOW | 28 ~ 35 |
| RED_USABLE | 20 ~ 27 |
| PRELIMINARY 격하 | < 20 |

**표본 크기를 결과값에 따라 선택하지 않는다.** 13:30 new-target-start-stop 은 고정이다.

---

## 2. `OlderRelevantKWCAGFailRate` — 분모·분자

service `i` 에 대해:

```
EligibleOlderRelevant_i = older-relevant 로 **사전 태깅된** criterion 중
                          해당 observation 에서 PASS 또는 FAIL 로 판정 가능한 criterion 수

FailOlderRelevant_i     = 그 중 FAIL 수

OlderRelevantKWCAGFailRate_i = FailOlderRelevant_i / EligibleOlderRelevant_i
```

**규칙:**

- `EligibleOlderRelevant_i == 0` 이면 **`FailRate = NULL`**. **0 으로 대체 금지.**
  (장벽이 없다는 뜻이 아니라 잴 수 없었다는 뜻이다.)
- `UNDETERMINED` 는 분모에서 제외하되 **`undetermined_n` / `undetermined_rate` 를 반드시 병기**한다.
- **`N/A` 와 `UNDETERMINED` 를 섞지 마라.** 전자는 해당 없음(적용 대상 아님), 후자는 판정 실패다.
- older-relevant 태깅은 **수집 전에 동결된 집합**을 쓴다. 결과를 보고 태깅을 바꾸지 않는다.

### 2.1 UNDETERMINED bounds (robustness 필수)

```
lower bound : 모든 UNDETERMINED 를 PASS 로 간주해 재계산  (best case)
upper bound : 모든 UNDETERMINED 를 FAIL 로 간주해 재계산  (worst case)
```

두 bound 사이에서 **결론의 방향이 뒤집히면** 그 주장은 GRADE C 이하로 강등한다.

---

## 3. `ExcessDepth` 와 archetype 최소 N

```
ExcessDepth_i = MPFED_i - median(MPFED within InteractionArchetype)
```

**전체 pooled median 을 archetype median 대신 쓰지 마라.** 프레임에서 `ITEM_DETAIL` 이
지배적(26/59, 44%)이므로 pooled 를 쓰면 `ExcessDepth` 가 사실상 "ITEM_DETAIL 대비 편차"가
되어 archetype 보정의 취지가 무너진다.

### 3.1 최소 N 계약

| archetype 별 joint-valid n | ExcessDepth | Kruskal-Wallis / pairwise | descriptive |
|---|---|---|---|
| **n >= 5** | 산출 | **포함** | 정상 |
| **n = 3~4** | 산출 + `LOW_N` 플래그 | **제외** (또는 별도 제한 표기) | median/IQR/ECDF 가능 |
| **n <= 2** | **`NULL`** — 상대깊이 추론 금지 | 제외 | descriptive 만 |

> **service row 자체는 절대 제거하지 않는다.** 제한되는 것은 파생변수와 추론 가능성이지
> 관측의 존재가 아니다. 해당 서비스의 L0 접근성·obstruction descriptive 는 전부 보고한다.

### 3.2 사전 관측된 분포 (수집 전, source-only)

`ITEM_DETAIL` 26 · `FINANCIAL_ACTION_ENTRY` 11 · `UTILITY_ENTRY` 6 · `QUERY` 5 ·
`COMMUNICATION_ENTRY` 4 · `PLACE_LOOKUP` 4 · `CONTENT_OPEN` 3 (합 59)

**`LIMITATIONS.md` 에 archetype 별 실제 joint-valid n 을 표로 명시하는 것은 필수다.**

---

## 4. 통계 계약

### 4.1 Descriptive first (필수)

`MPFED` median · IQR · mode · ECDF · archetype 별 분포.

### 4.2 PRIMARY

```
Spearman( MPFED , OlderRelevantKWCAGFailRate )
```

**해석 범위:** raw structural depth ↔ barrier burden **association** 으로만.
**difficulty causation 금지.**

### 4.3 구조보정

```
Spearman( ExcessDepth , OlderRelevantKWCAGFailRate )
```

### 4.4 SECONDARY

```
Spearman( ExcessDepth , OverlayCoverage )
```

또는 더 완결된 obstruction 변수 1개. **변수 선택은 결측률(완결성) 기준이며 상관계수 기준이 아니다.**
후보: `OverlayCoverage` · `PrimaryActionOcclusion` · `blocking_modal_count` · `forced_dismissal_count`.
**선택 근거(각 후보의 결측률)를 수집 결과 확인 시점에 기록**하고, 상관이 큰 것을 고르지 않는다.

### 4.5 최소 N 과 tie 처리 — 결과 보기 전 명시

- **pairwise-complete n < 10** 이면 coefficient 는 **exploratory descriptive only**,
  **p-value headline 금지.**
- `MPFED` 는 이산값이라 tie 가 많다 → **tie-aware Spearman** 을 쓴다.
- **exact / permutation 사용 여부를 산출물에 기록**한다.

### 4.6 Kruskal-Wallis

**실제 group n >= 5 인 archetype 만** 포함. 그렇게 남는 group 이 2개 미만이면 omnibus 자체를
돌리지 않는다. pairwise / Dunn / FDR 은 시간이 남고 omnibus 가 의미 있을 때만.

### 4.7 금지

**인과표현 금지.** 단일 종합점수(composite score) 금지. joint profile 을 "score" 로 부르지 않는다.

---

## 5. WA certification 축

source-only prework 실측: `certified_current` **variance = 0** (68행 중 `0.0` 55 / 빈값 13,
`certification_number` 68건 전부 공백). 프레임 안에 **현행 인증 보유 타깃 0건.**

**post-P0 reconciliation 에서도 variance = 0 이면:**

- **inferential comparison 금지.** Mann–Whitney 금지. Fisher "인증 효과" 주장 금지.
- joint figure 에서 **인증 encoding 제외** (A0 §9 — 실제 variance 있을 때만 encoding).
  상수를 시각적으로 인코딩하면 독자가 없는 대비를 읽는다.
- 기술 결과로만: *"frozen 실사용 frame 에서 현행 인증과의 비교가능한 overlap 이 없거나 극히 제한적"*

**이건 데이터 결함이 아니라 comparative-axis feasibility result 다.**

### 5.1 `LIMITATIONS.md` 필수 기재

`NOT_CERTIFIED` 55 vs `UNDETERMINED` 13 (URL 미해결 10 + 이름 불일치 3) 을 **구분해서** 적는다.
그리고 **우리 데이터로는 다음 셋을 구분할 수 없다**는 사실을 명시한다 —
인증이 만료된 것인지 · 애초에 받지 않은 것인지 · 우리 join 3요건이 엄격해 탈락한 것인지.

**"인증제도가 놓쳤다" 류의 직접 결론 금지.**

---

## 6. Joint profile figure

```
X     = ExcessDepth
Y     = OlderRelevantKWCAGFailRate
size  = OverlayCoverage
facet = InteractionArchetype
```

**score 가 아니다. score 로 부르지 않는다.**

### 6.1 사분면 해석

| | 상태 | remediation 방향 |
|---|---|---|
| A | 얕고 표준 장벽 적음 | 본 관측범위 내 참조 설계 후보 |
| B | 얕지만 표준 장벽 큼 | UI / frontend |
| C | 표준 장벽 적으나 진입 깊음 | IA / representative-function exposure |
| D | 두 축 모두 큼 | 복합 |

**`Y median = 0` 이면 artificial median split 금지** → `barrier absent` / `barrier present` 로 기술.

---

## 7. Claim grade

모든 결과 문장에 등급을 붙인다.

| 등급 | 조건 |
|---|---|
| **A** | 정의 / 기술통계 / 직접 관측 + evidence lineage complete |
| **B** | association / inferential result + 최소 N 충족 + robustness 방향 유지 |
| **C** | exploratory / low-N / sensitivity-dependent |
| **UNSUPPORTED** | 표본·측정으로 말할 수 없음 |

**최종 발표 headline 은 A 또는 robust B 만 허용.** C 는 exploratory 로 명시.

### 7.1 금지 표현

```
인과표현 일반
"고령자 사용성이 향상됐다"
"인증제도가 놓쳤다"
실제 고령자 실패율·포기율·lostness 추정
joint profile 을 "점수"로 지칭
```

### 7.2 이 연구가 말할 수 있는 것의 경계

> **"이 서비스의 입구가 이렇게 생겼다는 것까지가 우리가 말할 수 있는 전부다."**

본 연구는 실제 고령자의 행동실패·포기·lostness·학습효과·AI intervention 효과를
**직접 관측하지 않는다.**

---

## 8. E000 명칭 계약

오늘의 6-target smoke 는 **`E000_FAST`** 다.

- 허용 산출 라벨: **`E000_FAST_PASS`** / **`E000_FAST_SYSTEMIC_FAIL`**
- **`E000_V2_VALIDATED` 문자열 사용 금지.**

`PHASE_GATES.md` 의 canonical `E000_V2_VALIDATED` 는 **8~12 targets + dual-audit** 계약이며,
오늘 것은 A0 timebox 예외라 **그 Gate 를 닫지 않는다 — Gate 는 열린 채 남는다.**

**`LIMITATIONS.md` 필수 문장:**

> 오늘의 6-target `E000_FAST` 는 production collector/evidence-chain smoke validation 이며
> `PHASE_GATES` 의 canonical `E000_V2_VALIDATED` 를 대체하지 않는다.

### 8.1 E000_FAST systemic PASS 조건

```
predetermined 6 targets / order 유지
L0 + L1 동시 경로
evidence identity
append-only
manifest / hash
no prohibited action (로그인·결제·OTP·PII·CAPTCHA 우회)
collector / protocol SHA 동일
failure isolation
no outcome-conditioned reselection
```

**개별 실패로 기록하되 global FAIL 이 아닌 것:** `WAF` · `CAPTCHA` · `AUTH_GATE` ·
`APP_REDIRECT` · single-site transport failure.

---

## 9. 변경이력

| 시각 | 변경 | 데이터 관측 이후인가 | 사유 |
|---|---|---|---|
| 2026-08-27 11:40 | 최초 동결 | **아니오 — REAL TARGET 수집 0건 상태** | A0 지시에 따른 사전 동결 |
| 2026-08-27 13:55 | **개정 1 — PRIMARY/SECONDARY 재구성.** `MPFED` 전건 NULL 로 원 PRIMARY `Spearman(MPFED, FailRate)` 계산 불가. 새 PRIMARY = `Spearman(FailRate, obstruction 1종)`, SECONDARY = `KW(FailRate ~ archetype)`. 제외 사유 제3범주 `l1_not_attempted_guard` 신설. `l0_analyzable_n`(J1∧J4) 신설 — **J3 는 완화하지 않았고 `joint_valid_n` 도 그대로 보고한다.** **전문은 `ANALYSIS_CONTRACT_AMENDMENT_1.md` (`LA-AC-AMD1-20260827`).** 이 표만 읽는 사람도 PRIMARY 가 바뀐 사실을 알 수 있도록 여기 등재한다. | **부분적으로 예 — 정직하게 적는다.** E000 6건은 **관측했다.** 다만 개정의 근거는 결과값이 아니라 "`MPFED` 가 산출되지 않는다" 는 **측정 가능성** 사실이다. A 는 `FailRate`·obstruction 값을 열람하지 않았다고 **주장**하나 **이는 검증 불가능한 진술이며, 그 값들은 E000 batch result 에 열람 가능한 상태로 존재했다**(C 기록). 구조적 반증 근거는 §0 참조. | 계약에 PRIMARY 가 없는 상태로 E001 데이터를 받으면 데이터를 본 뒤 PRIMARY 를 고르게 된다. |
| 2026-08-27 12:15 | **§1.1 정정** — "로그인 벽이라는 이유만으로 joint-valid 에서 제거하지 않는다" 는 초판 문장이 실제 계수 규칙과 어긋났다. A2 §1.5.1(endpoint 미도달 → MPFED NULL → J3 탈락)이 지배함을 명시하고, 별도 제외 사유 `gate_reached_mpfed_null` 신설 + 그 수를 결과로 보고할 의무 + 선택편향의 `LIMITATIONS` 기재 의무를 추가했다. §1.3 제외 사유 목록에 해당 항목과 "우리 쪽 사정 / 대상의 성질" 구분을 표기했다. | **아니오 — REAL TARGET 수집 0건 상태** | 독립 검산자(C, `projectfinal-ba`)가 결과 이전에 계약 내부 모순을 지적했다. **joint-valid 판정 규칙 자체는 바꾸지 않았다** — A2 가 원래 정하던 것을 계약이 잘못 서술했던 것이고, 서술을 사실에 맞췄다. 계수 결과는 정정 전후가 동일하다. |

> 이후 어떤 변경도 이 표에 한 줄을 남긴다. **"데이터 관측 이후인가" 열을 반드시 채운다.**
> 관측 이후의 변경은 그 자체로 결과 해석에 영향을 주며, 숨기면 조작이 된다.
