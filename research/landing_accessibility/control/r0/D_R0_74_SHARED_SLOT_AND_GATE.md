# D-R0-74 — 축 간 evidence slot 공유 · 게이트 미달의 남은 계약 경로

**발행** Claude A · **작성** 2026-08-27T23:18:29+09:00 · **assertion_type** `DECISION`
**근거** `C-FINDING-231704` (P1, D-VRC-003 replication, 둘 다 result-affecting)

---

## §1 A — accessible text 가 두 축에 동시에 쓰인다

```
C 코드 확인   production W2 의 _commerce_control_present 가
              accessible_name_sources(aria_label · visible_text · title) + _COMMERCE_VOCAB 으로
              ITEM_DETAIL region 을 판정한다
함의          접근성 텍스트가 Axis B(archetype/region) 의 feature 로 실제 사용된다
              Axis A 의 accessible-name 계열 criterion 과 evidence slot 을 공유한다
```

**이 연구의 headline 은 축 사이의 연관이다.** 그런데 두 축이 같은 evidence slot 을 쓰면
**측정오차가 상관**할 수 있다.

```
접근성 이름이 부실한 사이트
   Axis A   accessible-name criterion 에서 FAIL
   Axis B   detector 가 commerce control 을 못 찾음 → archetype/depth 가 달라짐
→ '접근성 실패' 와 '깊이' 사이에 인공적 상관이 생긴다
```

**이것은 사이트의 성질이 아니라 측정 도구의 성질이다.** 구분하지 않으면
`SSOT §16` 이 금지한 인과 주장에 도달하기 전에 이미 상관 자체가 오염된다.

### D-R0-74-1 — 사전등록 (결과 보기 전)

```
1  두 축이 공유하는 evidence slot 목록을 등재한다
   최소 accessible_name_sources(aria_label · visible_text · title) · dom_title
2  planned association 에 'accessible-name 기반 criterion 제외' 감도분석을 추가한다
3  연관이 관측되면 그 감도분석 결과를 반드시 함께 보고한다.
   감도분석에서 연관이 사라지면 도구 인공물일 가능성을 명시한다
4  이것을 근거로 detector 설계를 지금 바꾸지 않는다
```

**4번의 이유**: accessible text 를 쓰지 않는 detector 를 지금 설계하는 것은 **새 조작화의 발명**이다.
`RF-DT §4` 는 accessible name 을 signal 로 명시하고 있다 — 계약이 허용한 것을 빼는 것도 계약 변경이다.
**공유를 없애는 대신 공유를 드러내고 감도분석으로 다룬다.**

## §2 B — 게이트 미달. HOLD 인가

```
C production 채점 (W2 a7f305f, prior_only)
   coverage 0.45~0.54 · force-map 1 · agreement 0.57
게이트 (D-R0-32)
   agreement >= 0.85 · coverage >= 0.75
```

C 의 정리:

> gate 유지 시 W2 는 `NOT_PASSED` 로 남고, 완화는 `D-R0-12`/`D-R0-56` 과 충돌한다.
> **C 는 기준을 바꾸지 않는다** — A/Director 판단.

**C 가 기준을 바꾸지 않은 것이 옳다.** 그리고 A 도 바꾸지 않는다.

### 그러나 지금은 HOLD 가 아니다 — 시도되지 않은 계약 경로가 남아 있다

```
D-R0-13 / SSOT §6.5 / RF-DT §7
   Rule DT 가 유일 leaf 를 만들지 못할 때만 NLP fallback 을 쓴다
   threshold 는 independent label 의 calibration split 에서 정한다
```

```
현재   W2 는 rule DT 만으로 채점되고 있다
       NLP fallback 은 label freeze 이후로 유보돼 있었고, freeze 는 22:27 에 끝났다
       calibration 30 은 이미 B 에게 공개됐다 (140619ae…)
```

**계약이 이미 허용한 2단계가 아직 밟히지 않았다.**
`rule-only 로 0.85 에 도달할 수 없다` 는 것은 **rule-only 가 계약의 전부일 때만** 게이트 미달의 결론이 된다.

```
DECISION  지금 HOLD 하지 않는다. D-R0-13 경로를 먼저 밟는다
```

### D-R0-74-2 — W2 에 요구

```
1  NLP fallback 의 구현·시도 여부를 회신한다. 미시도면 D-R0-13 경로를 밟는다
2  threshold 는 calibration split 에서만 정한다. holdout 을 보지 않는다
3  fallback 은 deterministic ambiguity 이후에만 작동한다 —
   rule 이 유일 leaf 를 만든 경우를 덮어쓰지 않는다
4  출력은 일곱 archetype 밖으로 나가지 않는다. 불확실하면 abstain
5  force-map 금지는 fallback 에도 그대로 적용된다 (D-R0-12 · D-R0-67-3)
```

**5번이 중요하다.** fallback 은 coverage 를 올리는 장치가 아니라 **ambiguity 를 푸는 장치**다.
fallback 으로 abstain 을 줄이면 그것은 `D-R0-67-3` 위반이지 개선이 아니다.

### D-R0-74-3 — HOLD 조건을 다시 좁혀 선언한다

`D-R0-67 §4` 의 조건부 HOLD 를 이 시점 정보로 갱신한다.

```
HOLD 한다   D-R0-13 NLP fallback 을 계약대로 밟은 뒤에도
            agreement 가 게이트에 도달하지 못할 때
그때의 성격  '계약이 허용한 모든 경로를 밟았으나 사전 게이트에 도달하지 못했다'
            → construct 또는 게이트 수준의 결정이 필요하다 → Director
그때의 선택지 (A 가 미리 적어둔다. 그때 만들지 않는다)
   (a) SSOT §18 PARTIAL_READY_WITH_BLOCKER 경로 — detector 미달을 명시하고
       Axis B 를 제한적으로만 사용
   (b) 게이트를 낮춘다 — D-R0-12/56 과 충돌하므로 그 충돌을 명시적으로 해소해야 한다
   (c) Axis B 의 archetype 의존 분석을 축소하고 depth 를 archetype 무관하게 보고
   (d) Human Final 5건을 detector 보정이 아니라 라벨 확정에 쓴다
```

**지금 적어두는 이유**: 그때 가서 선택지를 만들면 **결과를 본 뒤 만든 선택지**가 된다.

## §3 A 가 이 판단에서 스스로 점검한 것

**"HOLD 를 피하려고 이유를 찾는 것인가"** 를 물었다.

```
검토   D-R0-64 트리거 4번은 'SSOT/construct/threshold 변경 필요' 다
       NLP fallback 은 SSOT §6.5 와 RF-DT §7 에 이미 있다 — 변경이 아니라 미실행이다
       따라서 트리거에 해당하지 않는다
반증   만약 fallback 이 이미 시도됐고 그래도 미달이라면 그때는 트리거에 해당한다
       그래서 §D-R0-74-2 의 1번이 '시도 여부 회신' 이다 — A 가 가정하지 않는다
```

**A 는 fallback 이 미시도라고 단정하지 않는다.** B 의 회신으로 확인한다.
미시도가 아니라면 이 결정의 전제가 무너지고, 그때 HOLD 한다.

## §4 이 결정이 검증하지 않은 것

```
NLP fallback 시도 여부       B 회신 대기 — A 는 코드를 확인하지 않았다
fallback 후 도달 가능성       미측정. 도달한다고 주장하지 않는다
공유 slot 의 실제 상관 크기   미측정 — 감도분석이 그것을 잰다
D 의 rule 0.232              D 조작화이며 C 가 production 채점과 구분했다. A 는 D 값을 쓰지 않는다
```
