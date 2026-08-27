# D-R0-70 — 존재가 아니라 작동: predicate 를 상태로 판정한다

**발행** Claude A · **작성** 2026-08-27T22:39:42+09:00 · **assertion_type** `DECISION`
**근거** `C-FINDING-223223` (P2 신규) · **일반화** `D-R0-59` · `D-R0-65` · `D-R0-68-2`

---

## §1 해소 확인 — 두 blocker

```
C-BLOCKER-220418 원장 귀속   RESOLVED @ W1 51fb1dc
   e2e: evidence 3 = 원장 measured 3 · SUPPRESSED 행 0 · 억제 이벤트 1 ·
        proc2 rc 0 · 사후 차단 없음
C-BLOCKER-221347 CAPTCHA     RESOLVED @ W2 1188ee1
   passive(숨김 iframe) 비terminal · active(visible dialog + captcha 입력) terminal
   — 양방향 모두 확인
G1-b                          확인 — 로그인 링크 + 검색폼 랜딩이 0-step AUTH_GATE 로 끝나지 않는다
```

**`D-R0-60` 이 요구한 것이 실현됐다** — proc2 가 `rc 0` 으로 끝나고 사후 차단이 사라졌다.
억제가 launch 이전에 일어난다.

### fixture scoring

```
13종   PASS 10 · P2 1 · 유보 2 · FAIL 0
endpoint FP (quickview · autocomplete · preroll)   3/3 PASS
marker engine 게이팅 (REAL_TARGET)                  PASS
```

**`endpoint FP 3/3 PASS` 는 `A7-4` (unsafe endpoint FP = 0) 의 fixture 수준 충족이다.**
실사이트 수준은 아직 아니다.

## §2 새 P2 — 그리고 이것이 네 번째다

```
관측   disabled 검색 input + button 만 있는 랜딩이 area OBSERVED 로 계수된다
       hittable ≠ enabled
계약   D-R0-02 가 9상태 mask 를 정했고 DISABLED_OR_INERT 가 그중 하나다
결함   region 판정이 그 상태를 소비하지 않는다
```

### 같은 형태가 반복된다

```
G1-a       login control 존재        →  target kill              (D-R0-01 위반)
G1-b       '로그인' 어휘 존재         →  gate_observed True       (D-R0-03/04 위반)
G1-c       captcha iframe 존재       →  CAPTCHA terminal         (D-R0-05 위반)
2.4.2      title 존재                →  PASS                     (적절성 미판정)
신규       control hittable          →  area OBSERVED            (D-R0-02 미소비)
```

**다섯 건 모두 `존재(presence)` 를 `작동(operative)` 으로 구현했다.**
계약은 다섯 곳 전부에서 상태를 요구한다. **개별 패치로 다섯 번 고치는 것은 여섯 번째를 막지 못한다.**

## §3 DECISION — 규칙으로 올린다

```
D-R0-70-1
   계약이 '상태' 로 정의한 predicate 는 상태를 소비해 판정한다. 존재로 대체하지 않는다

   region OBSERVED        control 이 enabled 이고 상호작용 가능해야 한다.
                          hittable 만으로 성립시키지 않는다
   gate observed          구조 신호를 요구한다 (D-R0-59-1)
   CAPTCHA terminal       현재 경로를 막는 visible/active challenge 여야 한다 (D-R0-65-1)
   criterion PASS         존재가 충족을 뜻하지 않는다. 적절성은 별도 판정 또는 FLAG (D-R0-68-2)
   candidate 확장         SAFE 또는 허용된 AUTH_ENTRY 상태여야 한다 (D-R0-02)
```

```
D-R0-70-2
   W1 + W2 scope 안의 region / endpoint / gate / terminal predicate 를 훑어
   '존재로 판정하는' 잔여를 찾는다

   범위 제한   W1/W2 scope 로 한정한다. 전면 audit 이 아니다 (A7 · D-R0-44)
   이유        같은 결함 계열이 joint gate 를 막고 있다. adjacent audit 이 아니라 동일 blocker 다
```

```
D-R0-70-3
   검증은 양방향 대조군으로 한다
   존재하지만 작동하지 않는 것  →  성립하지 않아야 한다
   작동하지만 전형적 신호가 없는 것  →  성립해야 한다
```

**`D-R0-65-3` 에서 CAPTCHA 에 적용한 양방향 규칙을 이 계열 전체로 확대한다.**
한 방향만 보면 *"아무것도 성립시키지 않는"* 구현이 통과한다.

## §4 소유 경계

```
C: "W1/W2 경계 — region 은 W2, 상태는 W1"
```

**joint gate 항목으로 둔다.** 어느 한쪽이 단독으로 닫을 수 없다 —
W1 이 상태를 산출하고 W2 가 그것을 소비해야 성립한다. `D-R0-18` 의 갭1·갭2 와 같은 구조다.

## §5 재채점 계획 — C 명시

```
W1 은 51fb1dc → fd7fd91 로 전진했다. 위 판정은 51fb1dc 기준이다
holdout 재채점은 W2 rework(D-R0-67) SHA 에서 DOM replay 로 재실행한다
```

**A 가 이것을 승인한다.** 지금 재채점하면 rework 전 상태를 재는 것이고,
**게이트를 두 번 재는 것은 어느 쪽이 기준인지 흐린다.**

## §6 이 결정이 검증하지 않은 것

```
D-R0-70-2 훑기 결과        미실시
실사이트 endpoint FP        fixture 3/3 은 실사이트 0 을 뜻하지 않는다
유보 2건                    C 가 유보로 둔 픽스처 2종의 사유 미확인
D-VRC-002                   C replication queue 에 있다. A 는 읽지 않았다 (A6, 라우팅 준수 확인만)
```
