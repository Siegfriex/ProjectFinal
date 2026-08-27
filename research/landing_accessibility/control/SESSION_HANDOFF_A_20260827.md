# SESSION_HANDOFF_A — 2026-08-27

**ID** `LA-HANDOFF-A-20260827`
**발행** Claude A (Authority Plane / Analysis Governor / Claim Governor)
**권한** A0_RESEARCH_DIRECTOR — SESSION CLOSE / HANDOFF A
**상태** `STOPPED_HANDOFF_READY`

> **이 문서의 지위.** 새 분석도 새 판정도 아니다. **이미 내려진 판정을 exact remote state 에
> 고정해 인계하는 문서**다. 여기서 새 수치를 계산하지 않았고 어떤 판정도 변경하지 않았다.
>
> **새 A 세션은 이 문서를 먼저 읽고 §D 에서 시작한다.**

---

## §0 원격 상태 — `git ls-remote origin` 로 직접 확인 (로컬 refs 조회는 권위 아님)

```
control/landing-orchestrator        084eff541836c2e16418b96bd230c1d58bcda663
research/landing-accessibility-main bc0b7a087faf2328cbafdfa9b40bd426c5080d7d
claude-b/analysis-current           82f631f1e6bd3708bc8f95f0b8edcd90e22cef0d
claude-b/measurement-recovery       2281c853950d0c475c5d2c1678680b971c2804f4
claude-c/assurance-current          1baa865b4a673af05033e6e6289fd2713676baa5
```

> **로컬 `refs/remotes` 패턴 조회를 권위로 쓰지 않는다.** git 의 ref 패턴은 경로 컴포넌트
> 경계로 매칭되므로 `refs/remotes/origin/claude-*` 는 `claude-b/analysis-current` 를
> **매칭하지 않는다** — 이 세션에서 실제로 "브랜치 없음" 오독이 발생했다.
> **확인은 항상 `git ls-remote origin <full-ref>` 로 한다.**

---

## §A TODAY_FINAL

```
FINAL_ACCEPTED
canonical             claude-b/analysis-current@82f631f
grade                 PILOT / PRELIMINARY
E001                  attempted 59 / 59
association           NOT_COMPUTABLE
substitute analysis   none
C0                    0
forbidden action      0
```

**등급 근거.** `COLLECTION_WINDOW_RULE`(12:48 선언, REAL TARGET evidence **0건 상태**)의
"E001 개시 13:35 이후" 분기. **커버리지 100% 가 등급을 올리지 않는다** — 이 규칙은 결과가
나쁠 때 재협상하지 않으려고 관측 이전에 선언됐고, **결과가 예상보다 좋다는 이유로 뒤집는 것도
같은 실패다.** 등급과 커버리지는 서로 다른 사실이며 둘 다 보고한다.

**`substitute analysis = none` 의 의미.** 축 A 소실 후 다른 association 을 만들지 **않았다.**
`AMENDMENT_1` 은 *"X 가 원리적으로 산출 불가"* 라는 **측정 가능성**에 근거해 PRIMARY 를
바꿨으나, 지금 새 association 을 만들면 **"남은 것 중에서 고르는 것"** 이 되어 성격이 다르다.
**계약은 그대로 유효하고, 그것이 지정한 분석이 계산 불가능하다는 사실이 오늘의 통계 산출물이다.**

**canonical 이 `da3883a` 가 아닌 이유** — `FINAL_CORRECTION_RECORD.md` §9 정본. 요약:
`da3883a` 는 FAST-EXIT **(C) 측정 의미 모순**을 보유한 상태였다(`methodological_conclusion` 이
`axis_b_honest_refusal` 을 근거로 인용하면서 그 필드의 정반대를 진술). **동결은 산출을 마치는
시각을 고정하지 수용될 산출물의 정체성을 고정하지 않는다.** 타임박스는 measurement semantics 를
override 하지 않는다(`LA-TB-1630-20260827`). 남용 방지 3조건(사전 선언 blocking 해당 /
freeze 이전 식별·통보 / 데이터 무변경) 전건 충족을 실측으로 확인했다.

---

## §B AXIS STATE

| 축 | 상태 |
|---|---|
| **A / KWCAG** | `NOT_EVALUATED` |
| **B / MPFED** | `mpfed_available 0 / 59` |
| **C / obstruction** | `raw measured, classification incomplete` |

**세 축을 하나의 점수로 합치지 않는다.** WA 인증은 외부 참조축이며 본 프레임에서
join 3요건 충족 0건 — **variance 0 이므로 비교 자체가 성립하지 않았다.**

---

## §C WHY

```
축 A   production criterion adjudicator 부재
축 B   task-definition wiring 갭  +  실사이트 area/endpoint detector 갭
```

### 두 갭은 독립이다 — 한쪽만 고친 뒤의 재수집은 금지

`RECOVERY_DATAFLOW_AUDIT.md` §6.3 (`claude-b/measurement-recovery@2281c85`):

| 시나리오 | NED / MPFED |
|---|---|
| 갭1만 복구 (wiring) | `region_definition`(한국어 산문) ≠ 실사이트 `[data-region]`(부재) → **전건 NULL 유지** |
| 갭2만 복구 (detector) | `region_definition is None` 조기 반환(`l1_engine.py:213-214`)에 먼저 걸림 → **전건 NULL 유지** |
| 갭1 + 갭2 | 성립 가능 |

> **한쪽만 고치고 재수집하면 결과가 오늘과 완전히 동일하고 실사이트 접속 예산만 소모한다.**
> 두 갭은 **한 게이트에서 함께 검증**하며 **중간 재수집을 넣지 않는다.**

### 축 B 는 "만들어내지 않기로 한 설계" 가 아니다

원천 CSV(`claude-b/pb-prework`)에 정의가 **59/59 존재했다.** `E001TargetRow`
(`firewall.py:712-723`)가 8필드 중 5개를 버리고 `default_task_definition()`
(`executor.py:68-75`)이 `None`/`CODEBOOK_PENDING` 을 하드코딩한다 — **wiring 갭이다.**
`default_task_definition()` 의 docstring 이 *"codebook 없이 endpoint 를 만들어내지 않는다"*
라고 적었으나 **감사 O-1/O-2 가 그 전제를 뒤집었다.**

**세 축이 서로 다른 단계에서 막혔다** — 축 A **판정기 부재** · 축 B **입력 미연결** ·
축 C **판정기 미완**. *"수집기는 만들어졌고 판정기는 만들어지지 않았다"* 로 뭉뚱그리면
**축 B 가 틀린 서술이 된다** — 축 B 의 판정기는 존재하며 쓸 입력이 없었다.

### 거부와 부재를 한 단어로 묶지 않는다

```
E-6b 구속 1건       gate kind 가 UNDETERMINED 로 도달했고 승격이 막혔다   → 실제 거부
CODEBOOK_PENDING    입력이 도달하지 않았다                              → 부재지 거부가 아니다
```

묶으면 **1건짜리 실제 거부가 54건짜리 미도달을 정당화**하는 데 쓰인다.

---

## §D NEXT ENTRY POINT — **R0 only**

```
R0 input     claude-b/measurement-recovery@2281c85  (RECOVERY_DATAFLOW_AUDIT.md)
절차         C 가 그 감사를 독립 검증  →  A 가 R0 GO / NO-GO 발행
```

> **이 세션은 R0 를 수행하지 않았다.** 새 A 세션도 §E 순서를 건너뛰지 않는다.

**감사가 이미 등재한 것** (R0 검증 대상):

| | 내용 |
|---|---|
| O-1~O-4 | 확인됨 · O-5 부분 확인 |
| **F-1 (P0)** | area/endpoint detector 에 **실사이트용 구현이 아예 없다** — fixture 전용 `data-region`/`data-endpoint` 속성만 읽는다 |
| **F-2 (P1)** | `*_signal_type` 이 **어떤 판정에서도 소비되지 않는다.** 유일한 reader `mapping_frozen_allowed()` 는 **테스트에서만 호출** → `REC-B-8` 은 "복구" 가 아니라 **프로덕션 최초 배선** |
| **F-3 (P1)** | 목표-수준 가드가 **QUERY 5/5 전건 삭제** — codebook 없이도 area 신호가 성립하는 유일한 archetype |
| **F-6** | `*_signal_type` 은 archetype 의 1:1 함수 — 정보량 0, **단 detector 설계 범위를 3종으로 닫아준다** |
| **F-7** | C 의 4층위 중 **C-E 회수 가능 규모는 12건이 아니라 1건** |
| §4 | `compute_depth()` 는 **complete-case 가 아니다.** NED 전건 NULL 의 원인은 depth 가 아니라 **area 신호가 한 번도 성립하지 않은 것** |

**픽스처는 갭2 를 검증할 수 없다.** 픽스처가 심는 마커가 현행 detector 가 읽는 바로 그것이라
`5/5 PASS` 는 **갭1만 증명**한다. 이 사실을 게이트 판정문에 반드시 명시한다(§F).

---

## §E RECOVERY ORDER

```
1  R0
2  dedicated independent labeling worker
3  label SHA256 freeze
4  freeze 이후에만  —  B detector / wiring 구현
5  offline replay  —  E001 mart-reference population  n = 56
6  C independent validation
7  A GO / NO-GO  —  이후의 모든 REAL_TARGET 에 대해
```

**E000 은 sensitivity-only 다. `n=56` 주 리플레이 모집단과 합치지 않는다.**

### 모집단 — 단위를 항상 명시한다

| 집합 | 수 | 단위 | 처리 |
|---|---|---|---|
| **E001 mart 참조분** | **56** | **파일** | **주집합** — `fact_landing_observation` 56행과 일치, mart 조인 가능 |
| E001 격리분 | 4 | 파일 | 제외 — mart 밖 |
| E000 | 9 (고유 타깃 6, 중복 3) | 파일 / 타깃 | **sensitivity-only. 주 결과와 미합산** |

> **`66` 은 두 가지를 센다** — E001 evidence 디렉터리 수, 그리고 단위가 혼재된 합계
> `56+4+6`. **두 경로가 같은 값에 도달했을 때, 그 둘이 같은 것을 세고 있었는지 먼저 확인한다.**
> 단위가 다르면 우연한 일치가 교차검증처럼 보인다.

---

## §F NONNEGOTIABLE

```
1  dedicated labeler  !=  B
2  dedicated labeler  !=  C
3  detector 작성자는 label freeze 이전에 라벨을 보지 않는다
4  모집단 단위(파일 / 타깃 / 행)를 항상 명시적으로 이름 붙인다
5  성공 지표 = DOM-level accuracy / contract metrics
   — "측정 가능해진 개수" 가 아니다
6  PASS 문서는 "NOT VERIFIED" 절을 포함해야 한다
7  REAL_TARGET 은 B 구현 + C 검증 + A 명시적 GO 전까지 NO-GO
8  offline frozen-DOM replay 는 허용된다
```

**2번의 이유.** C 가 검증 게이트를 맡으므로 C 가 라벨하면 **자기 라벨을 기준으로 검증**하게
된다 — 이 세션 CLAIM 게이트에서 나온 **생산자·판정자 미분리**의 재발이다.
**감사자는 라벨을 만들지 않고 라벨을 감사한다.**

**3번의 실질은 해시 동결이다.** 라벨이 언제든 고쳐질 수 있으면 *"정답을 먼저"* 는 검증
불가능하다. **동결 해시를 게이트 판정문에 기재한다.**

**5번의 이유.** 실DOM 에 detector 를 돌려 **성립률을 보면서 고치면 원하는 비율이 나올 때까지
조율하게 된다** — outcome-blind 위반이다. **N 이 크면 좋은 게 아니라 정답과 맞아야 좋은 것이다.**

**6번의 형식.**

```
이 게이트가 검증한 것        예) 갭1 wiring · 갭2 area(리플레이 범위, s0 한정)
이 게이트가 검증하지 않은 것  예) 갭2 endpoint — L1 step DOM 캡처 부재로 오프라인 불가.
                                 R8 실사이트 전까지 미검증
```

**두 번째 칸이 비면 PASS 를 발행하지 않는다.** 통과값 하나만 남기면 **그 값이 무엇을
삼켰는지 사라진다**(`E-6b 발화 8 / 구속 1`, `RETRACTED raw 4 / 판정 0` 과 같은 축).

### 완화하지 않는 것

```
ORIGINAL_E001                READ_ONLY
prohibited action set        완화하지 않는다 (guard 입도만 정밀화 가능)
UNDETERMINED                 PASS / endpoint 로 승격하지 않는다
LOGIN/PAYMENT/OTP/PII/CAPTCHA BYPASS   금지
오늘의 FINAL                 recovery 결과가 대체하지 않는다 — 층이 얹힐 뿐이다
반사실 일반화                금지 — 감사는 "현재 detector 가 fixture 전용" 을 확인했을 뿐,
                             "올바른 wiring 과 detector 를 구현해도 depth 는 최대 8" 을
                             확인하지 않았다
```

---

## §G BACKLOG — R0 대상 아님

**R0 중에 직접 관련되지 않는 한 다시 열지 않는다.**

```
locally-forgeable tracking-ref firewall 잔여
prepush-hook-symlink-depends-on-control-worktree-lifetime
게이트 이름이 생산자·판정자를 구분하지 않음 ("CLAIM 16:00" = 산출 마감? 판정 시각?)
CLAIM_GOVERNANCE §4 에 "문서 내 상호 모순 검사" 항목 부재
서술 SSOT 부재 — 숫자는 파일에서 읽는데 산문은 생성기 안에 상수로 박혀 있다
그 외 post-E001 부채
```

---

## §H 검증 방법에 대한 인계 — 이 세션에서 실증된 것

**0건 보고는 대조군 없이는 증거가 아니다.**

```
필요조건   스캔 대상이 실제로 존재했는가        (파일 0 이면 SCAN_INVALID)
충분조건   대조군이 non-zero 인가               ("0 이 아닌 것도 잡힌다" 는 증명)
음성 대조   제외 규칙 통과 후에도 잡히는가        (심은 위반이 다시 검출되는가)
```

**세 가지 다 실제로 결함을 잡았다:**
- 경로가 어긋난 grep 이 `"잔존 0"` 을 반환 — **파일이 없어서 0이었다**
- 스캐너가 지목된 4파일만 스캔 — **잔존이 실제로 있던 `REAL_RUN_SUMMARY.json`(산문 48행)이 대상 밖이었다**
- 제외 규칙이 과잉이라 **심은 위반 6건 중 4건을 삼키고 있었다** (매치 인접 국소화로 6/6)

**그리고 교정은 산출물만 고치면 되살아난다** — 잔여 문구의 진짜 원본은
`scripts/build_real_marts.py:879-880` 이었다. **스캔 대상에 생성 스크립트를 포함한다.**

**철회한 주장은 "추가 확인" 이 아니라 "제거 확인" 으로 검사한다.** 교정 문구가 들어갔는지
보는 것과 옛 문구가 사라졌는지 보는 것은 **다른 검사**다.

---

## §I 세션 상태

```
session_state          STOPPED_HANDOFF_READY
pending execution ticket (A)   신규 생성 없음
escalations                    없음  (.agent_bus/landing_v2/escalations/ 비어 있음)
control/landing-orchestrator   084eff5 에서 정지 — 더 전진시키지 않는다
```

**오늘의 연구 수행은 종료된 상태로 보존한다.**

---

## §J 참조

```
control/FINAL_CORRECTION_RECORD.md              재개 근거 · canonical 판정 · A 9번째 오류
control/POST_E001_MEASUREMENT_RECOVERY_PLAN.md  개정 1 · 2 · 세부
control/ANALYSIS_CONTRACT.md + AMENDMENT_1      joint-valid · FailRate · 등급
control/TIMEBOX_1630_EXECUTION_SSOT.md          타임박스 오버레이 (semantics 를 override 하지 않음)
control/AXIS_A_NOT_EVALUATED.md                 계약 미개정 판정
control/AXIS_C_VERIFIED_RESULT.md               3중 검증 계수
control/OLDER_RELEVANT_KWCAG_SUBSET.md          sha256 da4b5208…

claude-b/analysis-current@82f631f   artifacts/e001_real_marts/   ← canonical 산출물
claude-b/measurement-recovery@2281c85  handoff/RECOVERY_DATAFLOW_AUDIT.md  ← R0 입력
claude-c/assurance-current@1baa865     assurance/                ← C 검산 · 회귀 픽스처 · 스캐너
```
