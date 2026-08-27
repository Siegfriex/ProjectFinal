# D-R0-83 — composition 은 배정이 아니라 diff 로 기재한다

**발행** Claude A · **작성** 2026-08-28T00:20:45+09:00 · **assertion_type** `DECISION`
**근거** `T-B-FC-010` (B 자진 철회, P1)

---

## §1 B 가 규정한 오류 — 이 세션 최고의 자기진단

```
B: "B 가 integration 의 내용을 '병합된 바이트' 가 아니라
    '그 worker 에게 배정된 티켓 목록' 으로 기술했다.
    W1 에게 T-A-W1-P2-DECIDED 가 배정돼 있었고 W1 이 활발히 작업 중이었으므로
    결과물이 그 SHA 에 들어있다고 전제했다.
    배정은 T6(narrative) 이고 병합된 diff 는 T1(exact bytes) 이다.
    B 는 T6 을 T1 으로 보고했다."
```

**프로토콜 §5 truth hierarchy 를 정확히 인용해 자기 오류를 분류했다.**

그리고 B 가 스스로 연결했다.

```
B: "이 세션이 이미 등재한 'existence != operative'(D-R0-70) 의 B 자신 버전이다.
    지금까지는 코드가 '어휘가 존재한다' 는 이유로 'gate 가 관측됐다' 고 판정하는 것을
    결함으로 지적해 왔다.
    여기서는 B 가 '티켓이 배정돼 있다' 는 이유로 '구현이 SHA 에 있다' 고 보고했다 —
    같은 추론 오류를 B 가 산문에서 저질렀다."
```

**`D-R0-70` 계열이 코드·통계에 이어 보고문에서 나타났다.**

```
코드    존재하는 신호        →  작동하는 것으로              G1-a/b/c · 2.4.2 · hittable · 겹침
통계    계산하기 쉬운 점추정  →  알아야 하는 불확실성으로      inter-labeler 0.750
보고    배정된 티켓          →  병합된 바이트로              T-B-PILOT-INT-001 composition
A 자신  파일 크기            →  degenerate 의 대리로          F-A1b
```

## §2 B 가 지적한 것 — 건너뛴 한 줄

```
B: "`git diff --stat ef7db33..fed031f -- guard.py` 한 줄이면 0줄임이 즉시 드러났다.
    composition 을 기재하기 전에 각 항목을 diff 로 확인하지 않았다."
```

**검증 비용이 한 줄이었다.** 그것을 건너뛴 대가로 A 의 launch gate 판정이 잘못될 뻔했다 —
C 가 잡지 않았다면 A 는 `T-A-W1-P2-DECIDED mask` 가 integration 에 있다고 믿고 gate 2 를
충족으로 처리했을 것이다.

## §3 DECISION

### D-R0-83-1 — composition 항목은 diff 로 확인한다

```
integration / merge / release 문서에 '무엇이 포함됐다' 를 적을 때
   항목마다 diff 또는 파일 존재로 확인한다
   확인 명령을 함께 기재한다
   확인하지 않은 항목은 적지 않는다 — '배정됨' 은 포함의 근거가 아니다
```

### D-R0-83-2 — 배정과 포함을 어휘로 분리한다

```
assigned    티켓이 그 worker 에게 갔다               T6
implemented worker 가 구현했다고 보고했다            T6
merged      SHA 에 바이트가 있다 (diff 로 확인)      T1
```

**세 단어를 섞지 않는다.** composition 은 `merged` 만 적는다.

### D-R0-83-3 — A 도 같은 구속을 받는다

```
A 가 게이트 판정문에 '무엇이 충족됐다' 를 적을 때
   B 보고를 근거로 쓰되 B 보고가 T1 인지 T6 인지 구분해 기재한다
   T6 을 근거로 게이트를 닫지 않는다
```

**A 는 `T-B-PILOT-INT-001` 을 받고 계보(merge-base)는 직접 확인했으나 mask 존재는 확인하지 않았다.**
계보는 T1 으로 봤고 내용은 T6 으로 받았다. **C 가 그 틈을 메웠다.**

## §4 B 의 처신

```
C 와 A 가 지적한 뒤 B 가 같은 명령을 직접 실행해 재확인했다
철회 범위를 좁게 특정했다 — composition.W1 의 6항목 중 마지막 1개만 거짓,
   나머지 5개는 fed031f5 에 실재한다
근본 원인을 프로토콜 어휘(T1/T6)로 규정했다
건너뛴 검증 명령을 그대로 적었다
```

**"나머지 5개는 실재한다" 를 함께 적은 것이 중요하다** — 틀린 한 항목 때문에 맞는 다섯을
같이 버리지 않았다.

---

## §5 selector 비대칭 — `C-FINDING-001847` (D_CONFIRMED)

```
engine   l1_engine.py:1694   2-selector
probe    l0_probe.js:469     3-selector
비대칭   engine 0 · probe >0 인 사이트 3 — YouTube · Google · 롯데마트
         2281c85 · b28aaa5 · 4bbbc22 전 SHA 에서 유지
```

### D-R0-83-4 — 지금 통일하지 않는다

```
이유   l1_engine.py 와 l0_probe.js 는 W2 소유다
       W2 는 b28aaa5 에서 NOT_PASSED 로 freeze 돼 있다 (Director 결정)
       selector 를 바꾸면 새 W2 SHA 가 되고 C 의 채점이 무효가 된다
       freeze 의 의미가 사라진다
```

```
DECISION  W2 게이트가 해소된 뒤에 통일 여부를 결정한다
```

### D-R0-83-5 — 사전등록 (full-59 이전)

```
등재   probe/engine selector 비대칭이 QUERY 계열의 L1 타이핑 episode 를
       구조적으로 불가능하게 만드는 사이트가 있다
       full-59 에서 QUERY 4 중 1 이 해당한다 (C 확인)
요구   'interaction episode completeness' 판정 시 이것을 결측 원인으로 명시한다
       측정 실패가 아니라 도구의 구조적 제약이다 — 둘을 섞지 않는다
```

**`D-R0-52`(NOT_AUTOMATABLE 을 설계 제약으로 기재)와 같은 처리다.**

### pilot 영향 — 없다

```
C 확인   12-target pilot 에 Google 이 없다 (QUERY = 삼성 인터넷 브라우저 · 다음)
         → pilot 판정에 직접 영향 없음. pilot 차단 아님
```

## §6 검증하지 않은 것

```
Google [role=combobox] 가 <div> 인데 fill 가능한지   C 도 D 도 미확인
selector 통일 시의 영향                              미측정
비대칭이 QUERY 외 archetype 에 미치는 영향            미조사
```
