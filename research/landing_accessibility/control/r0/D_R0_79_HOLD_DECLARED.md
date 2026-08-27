# D-R0-79 — HOLD 선언 · Director 판단 요청

**발행** Claude A · **작성** 2026-08-27T23:48:39+09:00 · **assertion_type** `DECISION`
**근거** `D-R0-74-2.C` completion (C, P1) · `C-FINDING-234523` · `T-B-HOLD-ACK-001` (B 수용)
**대상 SHA** W2 `b28aaa5cad736082a6a76c0ca6a9f6be330bbcfb` · W1 `ef7db338b58c` · C-joint `ae3dd49`

---

## §1 HOLD 선언

```
D-R0-77-3 이 정한 종결 조건이 충족됐다
HOLD 한다. Director 판단을 요청한다
REAL_TARGET  NO-GO 유지 (변경 없음)
```

`D-R0-64` HOLD 트리거 — **4번(SSOT/construct/threshold 변경 필요)**.
어떤 선택지를 택하든 계약 수준의 결정이 필요하다.

## §2 측정 결과 — C DOM replay 재채점

```
prior_only (Layer P)
   18 primary   coverage 0.538   agreement 0.571   force-map 1
   23           0.444            0.625             1
   26           0.45             0.556             1
   calibration  0.318            0.714             2
   → 전부 게이트 0.75 미만. fallback 발화 0/56

all7 (Layer O stress)
   18   coverage 0.692 (<0.75)
   26   coverage 0.75  (경계)  agreement 0.11~0.13   force-map 4
   → coverage 상승은 오매핑(PLACE_LOOKUP 25)으로 얻은 것.
     게이트의 다른 두 조건이 FAIL 이므로 통과가 아니다
```

**`all7` 의 coverage 0.75 를 통과로 읽지 않는다.** `D-R0-56` 이 정한 대로
coverage 는 abstain 규율과 함께 읽으며, 여기서는 force-map 4 와 agreement 0.11 이
그 수치가 무엇으로 만들어졌는지 보여준다.

## §3 A 가 정정할 것 — 지난 유예의 근거가 부정확했다

`D-R0-77-3` 에서 A 는 유예 근거를 이렇게 적었다.

> 0건 발화의 원인이 코퍼스 결함이다. frozen probe 는 구 `l0_probe.js` 로 수집돼
> 신규 raw feature 가 없다. 그 결함을 푸는 절차(DOM replay)가 미실행이다.

```
실제   C 의 DOM replay 는 joint5 에서 이미 신규 l0_probe.js 로 probe_v2 를 만들었다
       b28aaa5 에서 재사용한 것은 l0_probe.js 가 a7f305f 와 바이트 동일하기 때문이다
       (C 확인, B 가 git diff --quiet 로 독립 검증)
```

**즉 A 가 "아직 안 밟았다" 고 한 절차의 일부는 이미 밟혀 있었다.**
결론은 바뀌지 않는다 — 재채점이 실행됐고 FAIL 이 확인됐다. **다만 유예 근거가 부정확했다는 것을
기록한다.** 근거가 부정확한 유예는 결과가 같아도 같은 결정이 아니다.

## §4 B·C 의 처신

```
C   "C 는 새 경로를 제안하지 않는다"
B   "A 가 D-R0-77-3 에서 스스로를 묶었고 B 도 같은 구속을 받는다고 ACK 했다.
     B 는 지금 그것을 지킨다 — 추가 detector 개선안·threshold 조정·평가 방식 변경을
     제안하지 않는다"
B   세 선택지 중 어느 것도 고르지 않고 사실만 제공했다
B   C 의 probe_v2 재사용 근거를 독립 검증했다
```

**HOLD 회피 유혹이 가장 큰 지점에서 세 plane 이 모두 멈췄다.**

## §5 Director 판단 요청 — 선택지와 A 의 평가

세 선택지 모두 **REAL_TARGET 은 A 명시 GO 전까지 NO-GO** 다.

### (a) R1 — 게이트 유지 + W2 rework 계속

```
사실   W2 는 rule DT + NLP fallback 을 계약대로 밟았다. fallback 은 0건 발화했다
       B 도 C 도 구체적 개선 경로를 제시하지 않는다 — 제시하면 HOLD 회피가 되기 때문
A 평가  경로 없이 계속하는 것은 계획이 아니다.
       다만 D-R0-67-2(list-family 판별 신호)가 아직 완료되지 않았고,
       PLACE_LOOKUP 가짜-tie 시정이 그 계열의 첫 사례였다는 점은 남는다
```

### (b) R2 — frozen DOM 모집단의 한계를 인정하고 평가 모집단 교체

```
문제   A7 게이트 순서를 뒤집는다 — pilot 을 막는 조건을 pilot 으로 검증한다
       A 가 D-R0-76 §4 에서 이미 Director 항목으로 올렸다
장점   이것이 유일하게 진짜 blind set 을 만드는 길이다
       D-R0-62 에서 확인했듯 frozen 56 은 전부 노출됐다 — 청정 holdout 이 0 이다
       pilot 신규 관측은 라벨된 적이 없으므로 원리적으로 blind 다
```

### (c) PARTIAL_READY_WITH_BLOCKER 로 stratified pilot 진입

```
근거   SSOT §18 이 명시적으로 제공하는 경로다
성격   "detector 미달을 기재하고 제한적으로 진행한다"
```

### A 가 제시하는 (b)+(c) 결합안 — 채택을 권하지 않고 선택지로만 제시한다

```
구조   PARTIAL_READY_WITH_BLOCKER 로 stratified pilot 진입
       pilot 신규 관측을 독립 labeler 가 라벨 (B 는 열람하지 않는다)
       그것을 진짜 blind holdout 으로 삼아 detector 를 재평가
해결하는 것   게이트 미달과 holdout 오염(D-R0-62)을 동시에
필요조건      pilot 진입 자체가 A7 순서 변경이므로 Director 승인
              labeler 재조직 (A 소관)
              pilot 규모가 8~12 이므로 archetype 당 1~2 — 통계적으로 약하다
위험          pilot evidence 를 평가에 쓰면 '측정 대상' 과 '평가 대상' 이 같은 수집에서 나온다.
              단 라벨은 독립이므로 순환은 아니다
```

**A 는 이 결합안을 권고하지 않는다.** `A7` 순서는 Director 가 정했고, 그것을 바꾸는 판단에
A 가 선호를 얹으면 **자기 게이트 실패를 자기 설계 변경으로 푸는 모양**이 된다.

## §6 HOLD 가 멈추지 않는 것

```
W1   T-A-W1-P2-DECIDED — 장바구니 FORBIDDEN_TRANSACTION(P1 안전) · disabled DISABLED_OR_INERT
     안전 항목이므로 게이트와 무관하게 마친다
W3   C-BLOCKER-234221 1.4.3 rework — D-R0-78 로 결정 발행됨. ratio 근거 제시는 즉시 가능
W4   A_ACCEPTED. PrimaryActionOcclusion 은 PENDING_TASK_BINDING 유지
D-R0-70-2 훑기   미실시 — expect_* 포함
```

**HOLD 는 W2 detector 게이트에 관한 것이다.** 다른 작업을 멈추지 않는다 (`D-R0-64` A4).

## §7 Director 에게 함께 올리는 기존 항목

```
1  A7 게이트 순서 — 평가 모집단을 REAL pilot 으로 교체할지 (D-R0-76 §4)   ← 본 HOLD 와 직결
2  D-R0-72 OverlayCoverage construct — joint figure 의 point size (headline 변수)
3  blind set 존재 여부 — E000 6 을 쓸지 (D-R0-62-6)                       ← 본 HOLD 와 직결
```

**1 과 3 은 본 HOLD 의 선택지와 같은 질문이다.** 따로 결정하면 서로 모순할 수 있다.

## §8 검증하지 않은 것

```
D-R0-67-2 완료 후의 값       미측정 — (a) 를 택하면 이것이 남은 유일한 미지수다
pilot 라벨의 신뢰도           pilot 규모에서 겹침 이중라벨이 가능한지 미검토
(b) 의 순환 여부              라벨이 독립이면 순환이 아니라고 판단했으나 C 검증을 받지 않았다
```
