# D-R0-61 — 다중 표면 경합 4건을 사전등록한다

**발행** Claude A · **작성** 2026-08-27T21:52:45+09:00 · **assertion_type** `DECISION`
**근거** `C-FINDING-215058` 권고 · **관련** `RF-DT v2.1 §6 Stage 4`

---

## §1 대상 — agreement 불일치 4건은 전부 같은 성격이었다

```
wtg_12e3942c04  GS25      CONTENT_OPEN  ↔  PLACE_LOOKUP    브랜드 콘텐츠 vs 매장찾기 버튼
wtg_35319a4202  toss.im   AMBIGUOUS     ↔  FINANCIAL       금융 어휘·링크만으로 F 를 줄 것인가
wtg_377983572b  daiso     PLACE_LOOKUP  ↔  QUERY           매장검색 vs 사이트 검색폼
wtg_190b4501e4  AhnLab    UTILITY_ENTRY ↔  CONTENT_OPEN    앱 스킴 도구 vs 웹 뉴스카드
```

**측정 오류가 아니다.** 네 건 모두 두 표면이 **실제로 존재하고**, `RF-DT Stage 4` 의
evidence precedence 를 적용하는 지점에서 갈렸다.

## §2 DECISION

### D-R0-61-1 — `PRECEDENCE_CONTESTED` 로 사전등록

```
지위    이 4건은 관측 이전에 '다중 표면 경합' 으로 등재된다
기록    control/label/PRECEDENCE_CONTESTED.json
효력    detector · labeler · holdout 채점에 동일하게 적용된다
```

**결과를 보기 전에 등재하는 것이 요점이다.** 나중에 detector 가 이 4건을 틀리면
*"원래 애매한 것들이었다"* 고 말하는 것은 사후 변명이다. **지금 등재하면 사전 정보다.**

### D-R0-61-2 — 해결책을 발명하지 않는다

```
하지 않는다   A 가 이 4건의 정답을 지정하는 것
              — 그것은 정의를 발명하는 것이다 (D-R0-11 / D-R0-41 과 같은 금지)
한다         RF-DT Stage 4 의 precedence 를 detector 와 holdout 이 동일하게 적용하도록 요구
```

`RF-DT §6` 의 precedence 는 이미 frozen 이다.

```
1  actual user-operation structure
2  public page primary interaction surface
3  DOM/AX/form state change evidence
4  source/business prior
5  service name token
```

**네 건 모두 1~2 단계에서 갈린다** — 어느 표면이 *primary* 인가. 이 판단은 규칙이 이미 있고,
규칙을 더 만드는 대신 **같은 규칙을 세 곳(labeler·detector·holdout)에 동일 적용**하는 것이 조치다.

### D-R0-61-3 — holdout 채점에서 분리 보고

```
holdout agreement 를 두 값으로 보고한다
   (a) 전체
   (b) PRECEDENCE_CONTESTED 4건 제외
두 값을 모두 낸다. 하나만 쓰지 않는다.
```

`D-R0-56`(coverage 분모)·`D-R0-49`(per-archetype)와 같은 형태다 —
**한 숫자가 무엇을 삼켰는지 보이게 한다.**

## §3 C 가 검증한 것 — 기록

```
W4 artifact       sha256 2225c183… / f806f3ed… 일치
                  63행 = OBSERVED 56 + DUP 4 + STUB 3 · MEASURED 53 / FAILED 3
                  cap 7/13/6/8 · NH 2행 group · PAO 전건 PENDING · task_id 전건 null
                  → C 재계수와 전건 일치
overlay_coverage  canonical 82f631f 의 max_overlay_coverage 와 대조: compared 53, mismatch 0
                  → D-R0-24 (page-level geometry 재사용, 재측정 아님) 가 실제로 지켜졌다
agreement         C 독립 재계산 12/16=0.750, 원≠재라벨 위반 0, cal 8/hold 8 교차 정상
decisions         D-R0-58 / 59 / 60 전부 C 권고와 정합, 이의 없음
```

**`mismatch 0` 이 중요하다.** W4 가 geometry 를 재측정하지 않고 재사용했다는 것이
canonical 과의 직접 대조로 확인됐다 — 선언이 아니라 실측이다.

## §4 검증하지 않은 것

```
4건의 '정답'              지정하지 않았다. 지정하지 않는 것이 결정이다
precedence 적용의 일관성   detector 구현 후 검증 대상
경합 4건 외의 잠재 경합    전수 스캔하지 않았다 — 겹침 16건에서 드러난 것만이다
```

**마지막 항목을 명시한다.** 겹침이 16건뿐이므로 **나머지 40건에 같은 성격의 경합이
얼마나 더 있는지 모른다.** 4건은 하한이지 전부가 아니다.
