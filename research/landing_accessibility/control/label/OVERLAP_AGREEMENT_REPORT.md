# inter-labeler agreement — 겹침 16건 결과

**발행** Claude A · **작성** 2026-08-27T21:47:22+09:00 · **assertion_type** `ANALYSIS`
**근거** `D-R0-54` (C-BLOCKER-211259 해소) · 겹침 라벨 `OVERLAP_L1~L4.jsonl`

---

## §1 결과

```
전체 일치        12 / 16 = 0.750
양쪽 mapped 만   10 / 13 = 0.769
```

```
target           원 labeler / archetype              재라벨 labeler / archetype           일치
wtg_0ee385d0c9   L2 ITEM_DETAIL                      L1 ITEM_DETAIL                       O
wtg_12e3942c04   L4 CONTENT_OPEN                     L1 PLACE_LOOKUP                      X
wtg_24e6654bfd   L2 QUERY                            L1 QUERY                             O
wtg_35319a4202   L2 AMBIGUOUS_UNRESOLVED             L1 FINANCIAL_ACTION_ENTRY            X
wtg_054d78ed18   L1 AMBIGUOUS_UNRESOLVED             L2 AMBIGUOUS_UNRESOLVED              O
wtg_088809bf9b   L1 FINANCIAL_ACTION_ENTRY           L2 FINANCIAL_ACTION_ENTRY            O
wtg_0f3bdb2bd0   L3 PLACE_LOOKUP                     L2 PLACE_LOOKUP                      O
wtg_13ed070478   L1 AMBIGUOUS_UNRESOLVED             L2 AMBIGUOUS_UNRESOLVED              O
wtg_377983572b   L2 PLACE_LOOKUP                     L3 QUERY                             X
wtg_5ede567383   L2 COMMUNICATION_ENTRY              L3 COMMUNICATION_ENTRY               O
wtg_9390ef32ad   L2 UTILITY_ENTRY                    L3 UTILITY_ENTRY                     O
wtg_95967b5068   L2 FINANCIAL_ACTION_ENTRY           L3 FINANCIAL_ACTION_ENTRY            O
wtg_190b4501e4   L1 UTILITY_ENTRY                    L4 CONTENT_OPEN                      X
wtg_22ffba7a86   L1 ITEM_DETAIL                      L4 ITEM_DETAIL                       O
wtg_46e5a43370   L1 QUERY                            L4 QUERY                             O
wtg_5beeafeac2   L3 CONTENT_OPEN                     L4 CONTENT_OPEN                      O
```

교락은 해소됐다 — 원 labeler 와 재라벨 labeler 가 **전건 다르다**.

## §2 가장 중요한 결과 — slot 고정이 불일치를 실제로 해소했다

```
wtg_95967b5068 (NH)   L2 FINANCIAL   ↔   L3 FINANCIAL      일치
```

**1라운드에서는 같은 dom 바이트에 대해 L2 `FINANCIAL`(HIGH) vs L3 `AMBIGUOUS`(LOW) 였다.**
2라운드에서 slot 집합을 고정하자 L3 이 `FINANCIAL` HIGH 로 왔고, L3 은 스스로
*"`probe.json` 이 유일한 결정적 slot 이었다 — dom 은 빈 body, screenshot 은 렌더 이전 백지"* 라고 기록했다.

```
1라운드 불일치의 원인   판단 차이가 아니라 evidence slot 선택 차이
검증 방법              slot 을 고정하고 재라벨 → 일치
결론                   D-A-후보-5 / D-A-후보-6 이 실증적으로 지지된다
```

이것은 W2 detector 명세에 직접 적용된다 — **dom/ax 만 읽는 detector 는 SPA/지연렌더
사이트를 구조적으로 놓친다.**

## §3 불일치 4건 — 전부 "실재하는 두 표면 중 무엇이 대표인가"

| target | 대립 | 성격 |
|---|---|---|
| `wtg_12e3942c04` GS25 | CONTENT_OPEN ↔ PLACE_LOOKUP | 브랜드 콘텐츠 vs "매장 찾기" 버튼 |
| `wtg_35319a4202` toss.im | AMBIGUOUS ↔ FINANCIAL | 금융 어휘·링크만으로 F 를 줄 것인가 |
| `wtg_377983572b` daiso | PLACE_LOOKUP ↔ QUERY | 매장검색 vs 사이트 검색폼 |
| `wtg_190b4501e4` AhnLab | UTILITY_ENTRY ↔ CONTENT_OPEN | 앱 스킴 도구 vs 웹 뉴스카드 |

**측정 오류가 아니라 조작화 경계의 모호성이다.** 네 건 모두 두 표면이 실제로 존재하고,
RF-DT Stage 4 의 evidence precedence 를 적용하는 지점에서 갈렸다.
`AhnLab` 은 특히 명확하다 — 도구 기능이 전부 `v3mobileplus://` 커스텀 스킴이라
**Branch U 의 endpoint 가 웹에서 성립할 수 없다**는 것을 재라벨러가 짚었다.

## §4 이 수치로 말할 수 있는 것과 없는 것

```
n = 16.  이항 95% CI (12/16)  ≈  [0.476, 0.927]
```

```
말할 수 있다   labeler 간 판단이 완전히 임의적이지는 않다
              slot 고정이 재현성을 높인다 (NH 사례가 직접 증거)
              불일치가 특정 유형(다중 표면 경합)에 몰린다

말할 수 없다   prior-label 불일치(0.5238)가 label 잡음을 넘어선다는 것
              CI 하한 0.476 이 0.5238 을 포함한다. 구분되지 않는다
              archetype 별 agreement — n 이 archetype 당 1~3 이라 산출하지 않는다
```

## §5 `D-R0-55` 는 유보를 유지한다

```
D-R0-55 유보 사유였던 것   agreement 추정치가 없다
지금                        추정치는 생겼다 (0.750, CI [0.476, 0.927])
그러나                      CI 가 prior-label 일치율 0.5238 을 포함한다
                            → 두 값이 통계적으로 구분되지 않는다
결정                        analysis frame archetype 유보를 유지한다
```

**유보를 푸는 조건**을 지금 명시한다 (결과를 보고 조건을 만들지 않기 위해):

```
겹침 표본을 확대해 CI 하한이 0.5238 을 넘거나,
prior-label 불일치가 특정 archetype 에 체계적으로 몰린다는 것이
agreement 로 설명되지 않는 규모로 확인될 때 A 가 재판단한다.
확대 규모와 시점은 W1/W2 gate 이후 잔여 시간에 따라 정한다.
```

## §6 검증하지 않은 것

```
archetype 별 agreement          n 부족으로 산출하지 않음
confidence 와 일치의 관계        미분석
재라벨러가 slot 을 실제로 전부 열었는지  자기보고에 의존. C 감사 대상
원 라벨 1라운드의 slot 사용      기록되지 않았다 (evidence_slots_used 는 2라운드에만 있다)
```

**마지막 항목이 중요하다** — 1라운드 라벨에는 `evidence_slots_used` 가 없어서
**1라운드 불일치가 slot 때문이었는지 전수로는 확인할 수 없다.** NH 1건에서만 라벨러의
서술로 확인됐다. 이 한계를 agreement 해석에 명시한다.
