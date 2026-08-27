# ANALYSIS CONTRACT — 개정 1: depth 축 소실에 따른 분석 재구성

**ID** `LA-AC-AMD1-20260827`
**작성** Claude A (Analysis Governor), 2026-08-27 13:55 KST
**상태** **E001 REAL TARGET evidence 0건.** E000 6건은 관측했으나 **본 개정은 그 결과값이 아니라 측정 가능성에만 근거한다.**
**모문서** `ANALYSIS_CONTRACT.md` (`LA-AC-20260827`)

---

## 0. 왜 개정하나 — 그리고 무엇에 근거하지 **않는가**

E000 6/6 에서 `MPFED` 가 전건 NULL 이었다. 원인은 둘이고 **둘 다 시정하지 않기로 판정**했다
(가드 입도 · E-6b fail-closed — `E001_RELEASE.json` `depth_axis_finding` 참조).

따라서 모문서 §4.2 의 **PRIMARY `Spearman(MPFED, OlderRelevantKWCAGFailRate)` 는 계산 불가**이고,
§4.3 구조보정과 §4.4 SECONDARY(`ExcessDepth × OverlayCoverage`)도 함께 불가하다.
**분석 계약에 primary 가 없는 상태로 데이터를 받으면, 데이터를 본 뒤 primary 를 고르게 된다.**
그것을 막기 위해 지금 확정한다.

### 근거의 성격 — 이 구분이 이 개정의 정당성 전부다

| 근거로 삼은 것 | 근거로 삼지 **않은** 것 |
|---|---|
| `MPFED` 가 **산출되지 않는다**는 측정 가능성 사실 | 관측된 `FailRate` 값 |
| 대체 변수가 **존재한다**는 사실 | 대체 변수들의 **분포·상관** |
| E-6b 발화 2회 · 가드 차단 3건이라는 **계수** | 어느 서비스가 좋고 나쁜지 |

**나는 E000 의 `OlderRelevantKWCAGFailRate` 값도, obstruction 값도 보지 않았다.**
보지 않은 상태에서 확정한다. 이후 이 개정을 다시 고치면 §4 변경이력에
"데이터 관측 이후인가" 를 반드시 채운다.

---

## 1. 새 분석 구조

### 1.1 PRIMARY (신설)

```
Spearman( OlderRelevantKWCAGFailRate , <obstruction 변수 1개> )
```

**연구질문 대응:** 원 연구질문의 세 축 중 **(A) 표준화 접근성 장벽**과 **(C) 초기 화면 방해요소**의
동시발생을 묻는다. **(B) 진입 깊이는 오늘 관측되지 않았다.**

**해석 범위:** *"초기 화면에서 표준 접근성 장벽이 많은 서비스가 초기 방해요소도 많은가"* 의
**동시발생(co-occurrence)** 이다. **인과 아님. 어느 쪽이 원인인지 말하지 않는다.**

> 이 질문은 원래 SECONDARY 급이었다. **격상은 depth 축 소실에 따른 것이며,
> 그 사실을 `FINAL_RESULTS_SUMMARY.md` 와 `LIMITATIONS.md` 에 명시한다.**
> "원래 이걸 물으려 했다" 로 서술하면 안 된다.

### 1.2 obstruction 변수 선택 — 모문서 §4.4 규칙 그대로

**결측률 최소 기준으로 자동 선택.** 상관계수는 선택 로직에 입력되지 않는다.
후보 4종 **전부의 결측률을 기록**하고, 동률은 계약 나열 순서
(`OverlayCoverage` → `PrimaryActionOcclusion` → `blocking_modal_count` → `forced_dismissal_count`)로 깬다.

**판정 의존성 검사(모문서 §2.1 조작화)는 그대로 적용된다** —
선택된 변수가 adjudicated `UNDETERMINED` 를 포함하면 measurement-uncertainty bound 를 계산하고,
포함하지 않으면 `NOT_APPLICABLE` + 근거 기록. 근거 없는 `NOT_APPLICABLE` 은 예외를 던진다.

### 1.3 SECONDARY (신설)

```
Kruskal-Wallis( OlderRelevantKWCAGFailRate ~ InteractionArchetype )
```

모문서 §4.6 그대로 — **실제 group n >= 5 인 archetype 만** 포함, 남는 group 이 2개 미만이면
omnibus 자체를 돌리지 않는다.

### 1.4 DESCRIPTIVE (필수 — 등급과 무관하게 항상 산출)

- `OlderRelevantKWCAGFailRate` — median · IQR · ECDF · archetype 별 분포
- obstruction 4종 **전부** — median · IQR · 결측률
- `EligibleOlderRelevant` 분포 및 **`= 0` 인 서비스 수**(FailRate NULL)
- `undetermined_n` / `undetermined_rate`

---

## 2. depth 축은 **결과로** 보고한다

산출 실패를 서술에서 지우지 않는다. **다음을 `FINAL_RESULTS_SUMMARY.md` 에 독립 절로 보고한다.**

| 계수 | 의미 |
|---|---|
| `mpfed_available_n` / `attempted_n` | depth 축 산출률 |
| `guard_blocked_pre_scout` | 계정행동 가드가 Scout 이전에 차단 — **우리 도구의 제약** |
| `gate_kind_undetermined` | gate 종류 판별 실패 → E-6b fail-closed |
| `scout_no_signal` | Scout 예산 소진 |
| `endpoint_not_reached` | 그 외 |
| `l1_not_attempted_guard` | 제외 사유 제3범주 (§3) |
| E-6b 발화 횟수 | fail-closed 작동 정량 |

**서술 제약 (재확인):**

> ○ 대표기능은 **본 연구의 자동 관측 프로토콜 범위에서** 초기 화면으로부터 도달 가능한
> 경로로 관측되지 않았다.
>
> ✗ 고령자가 대표기능에 도달할 수 없다
> ✗ 대표기능이 로그인 뒤에 있다

**우리가 관측한 것은 우리 도구의 도달 한계이지 사용자의 도달 한계가 아니다.**

---

## 3. 제외 사유 제3범주 신설 — 모문서 §1.3 개정

```
attempted_n
joint_valid_n
excluded_n
  ├─ [우리 쪽 사정]   transport · timeout · l1_not_attempted
  ├─ [대상의 성질]    gate_reached_mpfed_null
  ├─ [우리 도구의 제약] l1_not_attempted_guard        ← 신설
  ├─ mpfed_null (그 외)
  ├─ all_older_relevant_kwcag_undetermined
  └─ (기타 명시 상태별)
```

**`l1_not_attempted_guard`** 는 대상의 성질도 아니고 일시적 실패도 아니다.
**안전 계약이 측정을 제약한 경우**이며, 이 연구 설계의 구조적 한계다. 셋을 섞으면 셋 다 흐려진다.

(독립 검산자 C 제기, A 판정. 근거: `E001_RELEASE.json` `acceptance_checklist.2_l0_l1_both_detail`)

---

## 4. joint-valid 정의 — 모문서 §1 J3 의 취급

모문서 J3 는 `MPFED` 산출을 요구한다. **그 정의를 바꾸지 않는다.**

따라서 `joint_valid_n` 은 **depth 축 기준 계수로 그대로 보고**되며, 오늘은 0 에 가까울 것이다.
**그 숫자를 살리려고 J3 를 완화하지 않는다** — 그것이야말로 결과에 맞춰 정의를 바꾸는 것이다.

대신 새 PRIMARY 의 표본은 **별도 계수**를 쓴다:

```
l0_analyzable_n = J1(L0 완료) ∧ J4(older-relevant 최소 1건 판정 가능) 를 만족하는 관측 수
```

**두 숫자를 모두 보고한다.** `joint_valid_n`(원 설계 기준, 낮음)과 `l0_analyzable_n`(실제 분석 표본).
어느 하나만 보고하면 오독이 생긴다.

**A0 §6 등급(GREEN 36 / YELLOW 28 / RED_USABLE 20 / PRELIMINARY <20)은 `joint_valid_n` 에 대해
정의된 것이다.** `l0_analyzable_n` 에 그 임계를 그대로 적용하지 않는다 — 다른 것을 세는 값이다.
오늘 등급은 어차피 `PILOT / PRELIMINARY` 로 이미 확정돼 있다(개시 시각 규칙).

---

## 5. claim grade — 모문서 §7 적용

새 PRIMARY 에도 동일하게 적용한다. 특히:

- `pairwise-complete n < 10` → **exploratory descriptive only, p-value headline 금지**
- 두 민감도 축(표본 구성 LOAO · 측정 불확실성 bound) 중 **어느 하나라도 부호가 뒤집히면 GRADE C 강등**
- **최종 headline 은 GRADE A 또는 robust B 만**

**오늘 산출물 전체가 `PILOT / PRELIMINARY` 이므로, 어떤 claim 도 확정적 서술로 쓰지 않는다.**

---

## 6. 변경이력

| 시각 | 변경 | 데이터 관측 이후인가 | 사유 |
|---|---|---|---|
| 2026-08-27 13:55 | PRIMARY/SECONDARY 재구성 · 제외 제3범주 신설 · `l0_analyzable_n` 신설 | **E001 evidence 0건. E000 6건은 관측했으나 본 개정은 결과값이 아니라 측정 가능성에만 근거한다 (§0 표 참조).** | `MPFED` 전건 NULL 로 원 PRIMARY 계산 불가. 계약에 primary 가 없는 상태로 데이터를 받으면 데이터를 본 뒤 primary 를 고르게 된다. |
