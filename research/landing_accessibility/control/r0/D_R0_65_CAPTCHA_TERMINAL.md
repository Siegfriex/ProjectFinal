# D-R0-65 — CAPTCHA terminal 판별: 존재가 아니라 차단이다

**발행** Claude A · **작성** 2026-08-27T22:16:34+09:00 · **assertion_type** `DECISION`
**근거** `C-BLOCKER-221347` (P1) · **강화** `D-R0-05` · **관련** `D-R0-59`(G1-b)

---

## §1 C 가 픽스처 SUT 로 확인한 것

```
양성 대조   숨김 reCAPTCHA iframe + api.js 만 있는 상품목록 랜딩
            → 'RESOLVED CAPTCHA (captcha_iframe)' → CAPTCHA terminal, 0-step
            → D-R0-05 위반. "DOM 내 코드·문구 존재만으로 terminal 아님" 을 정면으로 어긴다

음성 대조   보이는 active challenge (role=dialog · aria-modal ·
            "자동입력 방지 문자를 입력하세요" · captcha 입력) 인데 iframe 없음
            → 미검출, UNRESOLVED
```

**판별이 `iframe 존재` 를 키로 쓴다. 계약이 요구하는 `현재 경로를 막는 visible/active challenge` 와
정확히 반대다** — 막지 않는 것을 terminal 로 만들고, 막는 것을 놓친다.

## §2 이것은 세 번째다 — 같은 설계 형태가 반복됐다

```
G1-a   guard.py screen_candidates      login control 존재     → target 전체 kill
G1-b   gate_observed 텍스트 스캔        '로그인' 어휘 존재      → gate_observed True (0-step)
G1-c   gate_classifier CAPTCHA         captcha iframe 존재    → CAPTCHA terminal (0-step)
```

**셋 다 `존재(presence)` 를 `차단(blocking)` 으로 구현했다.**
계약은 세 곳 모두에서 반대를 말한다 — `D-R0-03`(login), `D-R0-04`(도달), `D-R0-05`(active challenge).

```
DECISION  G1-c 로 blocker ledger 에 등재한다.
          W1+W2 joint gate 는 G1-a · G1-b · G1-c 를 함께 통과해야 한다.
          하나만 고치면 나머지가 같은 0-step 종료를 만든다 — D-R0-18 과 같은 구조다.
```

## §3 DECISION

### D-R0-65-1 — CAPTCHA terminal 의 조작적 정의

```
terminal 성립 필요조건 (전부)
   현재 chosen path 의 다음 진행을 실제로 막는다
   visible / active challenge 다
      dialog / aria-modal 구조 또는 동등한 차단 표면
      captcha 입력 control 또는 challenge 이미지
      viewport 가시성

raw feature 로만 기록 (terminal 아님)
   captcha iframe 존재 · api.js 로드 · DOM 내 captcha 문구 · hidden/inactive script
```

**`iframe 단독` 은 terminal 이 아니다.** 판별은 iframe 이 아니라 **차단 상태**를 봐야 한다.

### D-R0-65-2 — 소유권

`gate_classifier` 는 W2 소유다 (`D-R0-59-2` 와 같은 파일군).
**별도 worker 로 떼지 않고 W2 scope 에 편입한다** — 프로토콜 §2, 같은 파일을 두 worker 가 만지지 않는다.

### D-R0-65-3 — 검증

```
C 의 픽스처 2종을 양·음성 대조군으로 채택한다
   양성   숨김 iframe 만  →  terminal 이 아니어야 한다
   음성   visible active challenge (iframe 없음)  →  terminal 이어야 한다
```

**두 방향을 모두 봐야 한다.** 한 방향만 보면 "아무것도 terminal 로 만들지 않는" 구현도 통과한다.

### D-R0-65-4 — 금지는 그대로

```
CAPTCHA 해결 · 우회   절대 금지 (D-R0-05 · Director unattended window §3)
```

**판별 완화가 우회 허용이 아니다.** 바뀌는 것은 *언제 terminal 로 기록하는가* 이지
*무엇을 해도 되는가* 가 아니다.

---

## §4 파일럿에 대한 함의 — 등재하되 판정은 바꾸지 않는다

C: *"파일럿 CAPTCHA 1건(wtg_13ed0704 netflix login)도 같은 경로로 판정됐을 가능성 — 재확인 대상"*

```
등재    ORIGINAL_E001_DEFECT_REGISTER 에 AUTH_GATE 건과 같은 형식으로 추가한다
주장하지 않는다   그 1건이 실제로 iframe 단독으로 판정됐다 — 개별 basis 미확인
                 A 도 C 도 확인하지 않았다
판정 불변  ORIGINAL_E001 은 READ_ONLY. 세 축 판정은 다른 원인에서 나왔다
```

**netflix 는 이미 세 장부에 올라 있다** — frame 결함(로그인 URL) · duplicate launch 4건 ·
그리고 이제 CAPTCHA 판정 후보. **한 target 이 서로 다른 결함 셋에 걸렸다.**
어느 하나로 처리해도 나머지가 남는다 (`W4-N1` 에서 B 가 지적한 것과 같은 구조).

## §5 실수집에 대한 함의 — PROJECTION

```
passive reCAPTCHA 는 커머스 랜딩에 흔하다 (C 지적)
수정하지 않고 재수집하면 그런 랜딩이 0-step terminal 로 잘려 depth 축이 또 결측된다
→ G1-b 와 같은 이유로, 이것도 재수집 전에 고쳐야 한다
```

**수정 후 CAPTCHA terminal 수가 줄어들 것으로 예상되나, 그 감소를 "사이트가 나아졌다" 로 읽지 않는다.**
측정 정의가 바뀐 것이다 (`D-R0-58-3` · ORIGINAL_E001 등재문 §5 와 같은 규칙).

## §6 이 결정이 검증하지 않은 것

```
파일럿 CAPTCHA 1건의 실제 판정 근거   미확인
실사이트 passive reCAPTCHA 유병률      미측정 — C 의 "흔하다" 는 도메인 지식이지 실측이 아니다
수정 후 음성 대조 통과 여부            구현 전
viewport 가시성 판정의 신뢰도          미검증
```
