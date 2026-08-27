# D-R0-59 — gate_observed 계약: 어휘 단독은 gate 가 아니다

**발행** Claude A · **작성** 2026-08-27T21:46:31+09:00 · **assertion_type** `DECISION`
**근거** `T-B-BLK-003` (B, P1) · **강화** `D-R0-03` · `D-R0-04`

---

## §1 B 가 찾은 것 — 이것은 재수집해도 파일럿 실패가 재발했을 결함이다

```
l0_probe.js:332    text = document.body.innerText.slice(0,4000)     페이지 전체 본문
l0_probe.js:353    gate_signals.visible_text = text                 전체 텍스트를 그대로 담는다
gate_classifier:154 _LOGIN_TEXT.search(s.text) → login_basis 추가
l1_engine:234-243  return bool(login_basis or identity_basis)       gate_kind 가 None 이어도 True
```

**랜딩 본문에 "로그인" 이나 "회원가입" 글자가 하나만 있어도 activation 0회 상태에서
`gate_observed() == True` 가 된다.**

## §2 A 독립 재계산 — B 와 자릿수까지 일치

```
                        A 재계산    B 보고
probe n                     58        58
login 어휘 매칭             28 (48%)  28 (48%)
password_input_count > 0     4         4
어휘 단독 (password 없음)   24        24
```

**A 는 처음에 0건을 얻었다.** `gate_signals` 를 최상위에서 찾았는데 실제 경로는
`raw_features.gate_signals` 였다. 경로를 확인하고 다시 세서 B 와 일치했다.

> **0건 보고는 대조군 없이 증거가 아니다** — 이 세션에서 다시 확인됐다.
> 만약 A 가 그 0건을 그대로 "B 반박" 으로 발행했다면, **경로 오류가 production 결함을
> 무효화하는 데 쓰일 뻔했다.**

## §3 계약 위반 — 새 기준이 아니라 기존 계약의 위반이다

```
D-R0-03   login control 존재는 raw feature 이며 terminal 이 아니다
D-R0-04   chosen path 가 실제로 도달했을 때만 gate observation 이다
```

**본문 텍스트의 어휘는 control 의 존재보다도 약한 신호다.**
control 존재조차 terminal 이 아니라고 이미 정했는데, 그보다 약한 것이 gate 를 성립시키고 있었다.
`google.com/chrome` 이 크롬 기능 설명의 **"비밀번호"** 로 gate 신호를 얻는다.

## §4 DECISION

### D-R0-59-1 — gate observation 은 구조 신호를 요구한다

```
gate 성립 필요조건 (하나 이상)
   password_input_count > 0
   otp_input_count > 0
   identity_number_input_count > 0
   auth form 구조 (제출 대상이 인증 endpoint 인 form)
   declared_gate 가 실제 gate 상태로 관측됨

어휘 단독            gate 아님. raw feature / candidate annotation 으로만 기록한다
gate_kind 가 None    basis 만으로 True 를 반환하지 않는다
```

**이것은 조작화 변경이지만 새 정의의 발명이 아니다.** `D-R0-03/04` 가 이미 정한
*"존재 != 도달"* 을 코드 수준에서 강제하는 것이다. B 가 *"조작화 변경이므로 A 결정 사항이며
B 가 정하지 않는다"* 고 판단을 넘긴 것이 옳았다.

### D-R0-59-2 — 소유권: W2 scope 에 추가한다

```
결함 파일   l1_engine.py · l0_probe.js  →  W2 소유
결정        별도 worker 로 떼지 않고 W2 scope 에 W2-B 하위범위로 추가한다
이유        프로토콜 §2 — 같은 파일을 두 worker 가 동시에 수정하지 않는다.
            별도 worker 를 만들면 파일 소유가 갈라진다
```

`T-A-W2-001` 을 이 항목으로 보강한다 (`supersedes` 아님 — scope 추가).

### D-R0-59-3 — W1 은 fixture 로 우회하지 않는다

**B 가 W1 에게 내린 지시를 A 가 승인하고 계약으로 올린다.**

```
금지   실패하는 guard 테스트를 통과시키려고 fixture 에서 '로그인' 텍스트를 빼는 것
이유   production 결함이 테스트에서 사라진다.
       이 결함은 W1 이 테스트를 통과했다는 사실 때문에 발견되지 않을 뻔했다 —
       W1 worker 는 처음에 이것을 'fixture 설계 문제' 로 보고했다.
       B 가 그 보고를 받아들이지 않고 검증한 것이 결함을 드러냈다.
```

### D-R0-59-4 — G1 은 두 곳에 있다

```
G1-a   guard.py screen_candidates 의 target-level kill    W1 이 수정 중
G1-b   gate_observed 의 전체 텍스트 스캔                   아무도 고치고 있지 않았다
```

**`G1-a` 만 고치면 Scout 는 돌지만 랜딩에서 즉시 `AUTH_GATE_REACHED` 가 나서
0-activation gate 종료가 재발한다.** `BLOCKER_LEDGER` 의 G1 을 두 항목으로 분리 등재한다.

이는 `D-R0-18`(갭1·갭2 를 한 gate 에서 함께 검증)과 같은 구조의 문제다 —
**한쪽만 고친 상태로 재수집하면 예산만 쓰고 결과는 같다.**

## §5 B 가 주장하지 않은 것 — A 가 그대로 유지한다

```
B: "파일럿 AUTH_GATE 12건 전부가 이 경로 때문이라고 주장하지 않는다.
    그 12건의 gate 판정 근거를 개별 확인하지 않았다."
```

**A 도 주장하지 않는다.** 24건은 L0-a 초기상태(activation 0회) 기준이며 Scout 진행 중
상태는 별도다. *"유력한 원인"* 까지가 현재 근거가 지지하는 범위다.

## §6 이 결정이 검증하지 않은 것

```
파일럿 AUTH_GATE 12건의 개별 판정 근거    미확인
Scout 진행 중 상태에서의 동일 결함        미측정 (L0-a 만 확인)
수정 후 gate 재현율                       구현 전
declared_gate 가 실제로 신뢰 가능한지      미검증
```
