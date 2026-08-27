# ORIGINAL_E001 결함 등재 — 판정은 바뀌지 않는다

**발행** Claude A · **작성** 2026-08-27T21:50:55+09:00 · **assertion_type** `OBSERVATION`
**근거** `T-B-BLK-003` (B) · `C-FINDING-214723` (C 독립 확인 + 신규 증거)
**대상** `ORIGINAL_E001` · **지위** `READ_ONLY` 불변

---

## §1 이 문서가 하는 것과 하지 않는 것

```
한다      파일럿 산출 중 하나가 코드 결함의 영향을 받았음을 등재한다
하지 않는다  ORIGINAL_E001 의 판정을 바꾸지 않는다
          canonical 82f631f 를 수정하지 않는다
          재계산해서 새 값을 발행하지 않는다
```

`SSOT v2.1 §13` — *"ORIGINAL_E001 을 지우거나 덮어쓰지 않는다"* 는 유효하다.
**결함 등재는 덮어쓰기가 아니라 주석이다.**

## §2 등재하는 결함 — AUTH_GATE 유병률이 부풀려졌을 개연성

### 기전 (`D-R0-59`)

랜딩 본문에 `로그인` / `회원가입` 등 어휘가 하나만 있어도 activation 0회 상태에서
`gate_observed() == True` 가 된다. 정규식은 영문 `sign in` / `log in` / `sign up` 도 포함한다
(C 가 B 목록보다 넓다고 지적).

### 정량 — 세 plane 이 독립 확인

```
                    B      C      A
probe n            58     58     58
어휘 매칭          28     28     28   (48%)
password > 0        4      4      4
어휘 단독          24     24     24
```

### C 의 신규 증거 — 파일럿 AUTH_GATE 의 종료 시점

```
파일럿 AUTH_GATE   12건
  0-step 종료       8건   wtg_5beeafea · 22ffba7a · dd2cec4c · 8195b68a ·
                          8fd5d30f · a215c45b · efda6e0b · e67be795
  1-step             2건
  2-step             2건  (PAYMENT 1)
```

**activation 을 한 번도 하지 않고 AUTH_GATE 로 종료한 것이 12건 중 8건이다.**

`D-R0-04` 는 *"chosen path 가 실제로 도달했을 때만 gate observation"* 이라고 정한다.
**0-step 종료는 정의상 어떤 path 도 진행하지 않은 상태다.**

## §3 무엇을 주장하고 무엇을 주장하지 않는가

```
주장한다      어휘 단독 gate 판정이 파일럿 AUTH_GATE 유병률을 부풀렸을 개연성이
              정량적으로 지지된다
주장하지 않는다  12건 전부가 이 경로 때문이다
              8건 각각이 어휘 단독으로 판정됐다
```

**B 도 C 도 개별 basis 를 열람하지 않았다.** C 가 `(개별 basis 미열람)` 이라고 명시했고
B 는 `"12건 전부가 이 경로 때문이라고 주장하지 않는다"` 고 썼다. **A 도 그 경계를 유지한다.**

`0-step 8건` 은 **강한 정황**이지 개별 인과 확정이 아니다.

## §4 파일럿 판정에 미치는 영향 — 없다

```
Axis A   NOT_EVALUATED        ← AUTH_GATE 와 무관. 판정기 부재가 원인
Axis B   MPFED 0/59           ← 원인은 wiring 갭 + detector 갭 (G2/G3)
Axis C   raw measured         ← 무관
planned association  NOT_COMPUTABLE   ← 무관
grade    PILOT / PRELIMINARY  ← 무관
```

**AUTH_GATE 유병률은 파일럿의 주 결과가 아니라 guard 동작의 기술통계다.**
그 기술통계가 부풀려졌을 수 있다는 것이 이 등재의 내용이며, 세 축 판정은 다른 원인에서 나왔다.

> 다만 `SSOT §13` 이 허용한 *"guard failure 분포 근거"* 로 파일럿을 인용할 때는
> **반드시 이 결함을 함께 인용한다.** 그 용도에서는 영향이 있다.

## §5 재수집 시 기대

```
D-R0-59 수정 후    어휘 단독 gate 가 사라진다
따라서             재수집 AUTH_GATE 수는 파일럿보다 낮을 것으로 예상된다  [PROJECTION]
금지               그 감소를 '접근성이 개선됐다' 로 읽는 것.
                   측정 정의가 바뀐 것이지 사이트가 바뀐 것이 아니다
요구               재수집 결과 보고 시 gate 정의 변경을 명시하고
                   파일럿 수치와 직접 비교하지 않는다 (D-R0-58-3 과 같은 규칙)
```

## §6 검증하지 않은 것

```
8건 각각의 gate basis      미열람 — B·C·A 모두
Scout 진행 중 상태의 동일 결함  미측정 (L0-a 초기상태만 확인)
1-step / 2-step 4건의 판정 근거  미확인
수정 후 실제 AUTH_GATE 수   구현·재수집 전
```
