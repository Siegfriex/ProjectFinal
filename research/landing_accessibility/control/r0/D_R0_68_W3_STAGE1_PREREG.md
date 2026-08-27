# D-R0-68 — W3 Stage 1 결과 · 실효 coverage · Axis A 사전등록

**발행** Claude A · **작성** 2026-08-27T22:28:34+09:00 · **assertion_type** `DECISION`
**근거** `C-FINDING-222649` (P2) @ W3 `94cbf8b610a9386267e3cbeb3057319a57a15634`

---

## §1 불변식 전건 PASS — C 독립 replay

```
scope 22                   OTHER 11 거부 확인            (D-R0-51 W3-D2 경계 준수)
NOT_AUTOMATABLE 7 → UNDET  100%                          (D-R0-52 구조적 하한 실현)
AUTO_FLAG_ONLY 6           UNDET/NA 만, PASS/FAIL 0건     (D-R0-52 DECISION-1 준수)
schema gap 4 → UNDET       100%
cap ∧ PASS                 0건
FAIL 80 중 cap 영향        0건                            (D-R0-53 절단이 판정을 오염시키지 않음)
criterion 별 독립 호출     확인
```

**`D-R0-52` 에서 사전등록한 규율이 실제로 지켜졌다.** 특히 `AUTO_FLAG_ONLY` 가
`PASS/FAIL` 을 한 건도 내지 않은 것 — flag 를 확정으로 쓰지 않겠다는 결정이 코드에서 성립했다.

## §2 실효 decision coverage 0.159 — 상한을 낮추지 않는다

```
decision coverage = (PASS+FAIL) / (22 × 54) = 0.159
실효 결정 criterion   5 / 22   (1.4.2 · 1.4.3 · 2.1.3 · 2.4.2 · 3.3.2)
D-R0-52 구조적 상한   9 / 22
차이 4                schema gap — evidence schema 가 필요한 필드를 담지 않는다
```

C 는 *"실효 상한 5/22 = 0.227 사전등록"* 을 권고했다. **A 는 그렇게 하지 않는다.**

```
DECISION
   D-R0-52 의 구조적 상한 9/22 = 0.409 는 그대로 둔다
   5/22 는 '현 SHA 에서 실현된 값' 으로 등재하고 상한으로 부르지 않는다
   차이 4건(schema gap)은 결함으로 명명한다
```

**이유**: 상한과 실현값은 다른 개념이다. schema gap 이 **고칠 수 있는 것이면 결함**이고,
**고칠 수 없는 것이면 그때 상한이 내려간다.** 지금 5/22 를 상한으로 등재하면
**고칠 수 있는 결함을 설계 제약으로 세탁**하는 것이 된다.

```
요구   B 가 schema gap 4건 각각에 대해 '현 evidence schema 로 채울 수 있는가' 를 판정한다
       채울 수 있다 → 결함. 채울 수 없다 → 그 근거와 함께 상한 하향을 A 가 재판단
```

## §3 Axis A 사전등록 — `1.4.3` 지배 (construct P2)

```
관측   1.4.3 대비 FAIL 45/54 = 83%
규칙   'any item 미달' — 한 항목이라도 미달이면 criterion FAIL
실측   artifact-only FAIL 1건 (실패항목 1,174 중 alpha0 17 · 1px 50)
함의   OlderRelevantKWCAGFailRate 가 단일 criterion 에 지배된다
```

**`FailRate` 라는 이름이 암시하는 것과 실제로 재는 것이 어긋난다.** 지금 그대로 두면
*"고령 관련 KWCAG 실패율"* 이 사실상 *"대비(contrast) 실패율"* 이 된다.

### D-R0-68-1 — 결과 보기 전에 등록한다

```
1  Axis A 는 반드시 per-criterion 으로 보고한다. 단일 FailRate 만 제시하지 않는다
2  criterion 가중을 두지 않는다 — 1.4.3 을 낮추지도 올리지도 않는다
3  FailRate 를 인용할 때마다 지배 criterion 과 그 비중을 병기한다
4  1.4.3 을 제외한 sensitivity 를 함께 낸다
5  이 구조를 '측정 결함' 으로 서술하지 않는다 — 'any item 미달' 은 KWCAG 규칙 자체다
```

**5번이 중요하다.** 규칙이 그렇게 생겼다는 것과 우리 측정이 틀렸다는 것은 다르다.
**보고 방식을 바꾸지 규칙을 바꾸지 않는다.**

### D-R0-68-2 — P3 두 건

```
1.4.3 항목 필터   alpha0 / 1px / bg 미해결 항목의 처리를 B 가 명시한다.
                  현재 실패항목에 섞여 있어 '진짜 대비 실패' 와 구분되지 않는다
2.4.2             title 존재 = PASS 54/54. '적절성' 은 FLAG 로 분리한다 —
                  존재를 적절성으로 읽으면 그것도 presence≠quality 계열이다
```

`2.4.2` 는 **G1-a/b/c 와 같은 형태**다 — 존재를 충족으로 구현했다. 다만 이쪽은
`PASS` 방향이라 덜 눈에 띈다. **존재로 PASS 를 주는 것은 존재로 terminal 을 주는 것만큼 위험하다.**

---

## §4 D 자기 철회 — `D-FACT_CORRECTION-001` ACK

```
D 의 원 주장   dom_title 6/54 가 Latin-1 로만 구성 — 수집기 인코딩 결함 후보
D 의 철회      RETRACTED_WRONG_ATTRIBUTION. 수집기 결함이 아니라 D 자신의 파싱 결함이다
               (lxml.html.fromstring 을 바이트에 인코딩 지정 없이 적용)
C 의 독립 판정 D_REFUTED — 같은 결론에 먼저 도달했다
```

**D 가 요구받지 않고 스스로 철회했고, 영향 처리도 규약대로 했다.**

```
v1 을 덮어쓰지 않는다
v2 를 별도 파일로 만든다
v2 기반 재실행은 새 child run 으로 만든다
기존 run 의 metric 을 수정하지 않는다
```

**이것이 Director MLflow 계약의 immutability 조항 그대로다.** 기록한다.

### D 가 정정한 byte-identical 의 원인 — A 의 F-A2 와 수렴

```
D: 원인은 수집기가 아니라 동일 요청 URL 등록이다
   NH스마트뱅킹 · NH콕뱅크 가 https://banking.nonghyup.com/nhbank.html 로 동일
```

**A 의 `F-A2` 와 같은 결론이다** — frame 의 관측 단위 문제이지 수집기 결함이 아니다.
A · C · D 가 서로 다른 경로로 같은 지점에 도달했다.

```
DECISION  D-VRC-001-A 를 'D 자체 결함으로 철회됨' 으로 종결한다.
          B 에게 인코딩 수정을 요구할 근거가 없다.
          D-VRC-001-B 는 유지하되 원인은 frame 으로 정정한다 (이미 D-R0-54 / F-A2 로 등재됨)
```

## §5 이 결정이 검증하지 않은 것

```
schema gap 4 의 수정 가능성   B 판정 대기
1.4.3 실패항목의 내용 타당성   A 는 항목 수준을 열람하지 않았다
2.4.2 적절성 판정의 방법       미정 — FLAG 분리만 결정했다
D 의 v2 corpus                 A 는 D 산출을 직접 읽지 않는다 (A6)
```
