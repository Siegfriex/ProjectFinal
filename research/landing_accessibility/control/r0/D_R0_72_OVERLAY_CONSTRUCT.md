# D-R0-72 — OverlayCoverage: 겹침이 아니라 방해다

**발행** Claude A · **작성** 2026-08-27T22:43:51+09:00 · **assertion_type** `DECISION`
**근거** `C-FINDING-224105` (P1, D-VRC-002 replication) · **영향** Axis C 핵심 변수

---

## §1 관측 — 이름과 재는 것이 어긋난다

```
canonical max_overlay_coverage >= 1.0   target 22 (D 와 C 일치)
raw 25 obs 내역
   MODAL 출처            5
   비모달 (fixed·high-z·sticky)  20
   그중 음수 z-index      2   Instagram −9999 · 하나은행 −999  ← 콘텐츠 뒤에 있다
```

**`z-index: −9999` 인 요소는 콘텐츠 뒤에 있고 아무것도 가리지 않는다.**
그런데 `OverlayCoverage = 1.0` 에 계수된다.

`SSOT §3 Axis C` 의 정의:

> 최초 viewport 에서 popup, modal, banner, app prompt 등이 화면 또는 대표행동을
> 얼마나 **방해**하는가

**계약은 `방해` 를 말하고 구현은 `기하학적 겹침` 을 센다.**

## §2 이것이 여섯 번째다

```
G1-a    login control 존재     →  target kill
G1-b    '로그인' 어휘 존재      →  gate_observed True
G1-c    captcha iframe 존재    →  CAPTCHA terminal
2.4.2   title 존재             →  PASS
신규5   control hittable       →  area OBSERVED       (hittable ≠ enabled)
신규6   기하학적 겹침           →  OverlayCoverage     (겹침 ≠ 방해)
```

`D-R0-70` 이 다섯 번째에서 규칙으로 올린 그 형태다. **여섯 번째가 규칙 발행 3분 뒤에 나왔다** —
훑기(`D-R0-70-2`)가 필요하다는 증거다.

## §3 HOLD 여부 판단 — 하지 않는다, 그러나 Director 에게 고지한다

`D-R0-64` 트리거 4번(SSOT/construct/threshold 변경 필요) 해당 여부를 검토했다.

```
제외 대상   z-index<0 · pointer-events:none · hittable=false
판정        SSOT §3 이 '방해' 를 요구한다. 방해할 수 없는 요소를 빼는 것은
            정의를 바꾸는 것이 아니라 정의대로 구현하는 것이다
            → HOLD 트리거 아님. 위임 범위 안이다
```

**단, 영향의 크기는 작지 않다.**

```
Axis C 핵심 변수        OverlayCoverage 값이 실질적으로 바뀐다
joint figure            SSOT §12 의 point size 가 이 값이다
D-R0-24 재사용          canonical 을 재사용하므로 W4 mart 가 같은 결함을 상속했다
                        (C 가 53/53 동일값 확인)
```

```
A 의 처리   위임 범위이므로 진행한다
            그러나 Director 복귀 시 우선 보고 항목으로 표시한다
            — 절차상 A 의 권한이지만 headline 변수를 건드리는 결정이다
```

## §4 DECISION — C 권고 채택, `D-R0-58` 과 동형으로

### D-R0-72-1 — 분자에서 제외한다

```
제외   z-index < 0
       pointer-events: none
       hittable = false
근거   셋 다 '가릴 수 없는' 요소다. 방해 정의를 충족하지 않는다
```

### D-R0-72-2 — `overlay_source` 를 분리한다

```
overlay_source   MODAL · FIXED · STICKY · BEHIND · …
```

**`D-R0-58` 의 `interrupt_form` / `interrupt_semantic` 분리와 같은 처방이다.**
하나의 숫자에 서로 다른 성질을 밀어 넣지 않는다.

```
왜 fixed·sticky 를 빼지 않는가
   sticky header 는 실제로 콘텐츠를 가린다 — 방해가 맞다
   modal 만 방해로 보는 것은 정의를 반대 방향으로 좁히는 것이다
   따라서 빼지 않고 출처를 구분해 분석에서 선택 가능하게 한다
```

### D-R0-72-3 — canonical 불변, 버전 명시

```
canonical 82f631f      불변. 재계산하지 않는다
새 mart                geometry rule version 을 명시한다
비교                   canonical 값과 새 값을 직접 비교하지 않는다.
                       규칙이 바뀌었으므로 차이는 사이트 변화가 아니라 규칙 변화다
```

**`D-R0-58-3` 과 같은 규칙이다.**

### D-R0-72-4 — 사전등록

```
Axis C 보고 시
   overlay_source 별 분포를 병기한다
   BEHIND 제외 전후 값을 둘 다 낸다
   joint figure 의 point size 가 무엇을 재는지 캡션에 명시한다
```

## §5 D 라우팅 — 두 번째 정상 작동

```
D-VRC-002  →  C replication  →  D_CONFIRMED result-affecting  →  A decision queue
```

**A 는 D 산출을 직접 읽지 않았다.** C 가 재계산해 D 와 일치를 확인했고(22 target),
result-affecting 판정만 A 에게 왔다. `A6` 이 설계대로 작동한다.

C 의 부기: *"D 결과에 사이트명이 포함되나 D 는 holdout 라벨 비열람이므로 누출이 아니다."*
**사이트명 자체는 holdout 정보가 아니다 — 라벨이 holdout 정보다.** 구분이 정확하다.

## §6 이 결정이 검증하지 않은 것

```
제외 후 실제 값 변화     미계산
fixed·sticky 의 방해 정도  기하로만 잰다. 실제 가림 여부는 primary action 과의 관계로만 판정 가능
                          → PrimaryActionOcclusion (PENDING_TASK_BINDING) 이 그 역할이다
음수 z-index 2건 외 사례  전수 스캔은 C 가 25 obs 에서만 했다
D-R0-70-2 훑기            미실시 — 이 건이 여섯 번째라는 것이 그 필요성의 증거다
```
