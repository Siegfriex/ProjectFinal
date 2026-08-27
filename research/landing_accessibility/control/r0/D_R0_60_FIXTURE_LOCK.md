# D-R0-60 — exactly-once 는 오프라인에서 증명 가능해야 한다

**발행** Claude A · **작성** 2026-08-27T21:48:38+09:00 · **assertion_type** `DECISION`
**근거** `C-FINDING-214553` (P2) · **강화** `D-R0-46` · `D-R0-38`

---

## §1 C 가 확인한 것 — 원시 억제는 성립한다

C 가 자체 하네스로 B 의 `TargetLock` 을 SUT 실행했다 (3 프로세스 동시 × 3 key):

```
키당 proceed 1 / DUPLICATE_SUPPRESSED 2
lock 미삭제
억제 지점이 EvidenceRun.create 이전임을 확인
```

**`D-R0-46` 의 원시 요구는 충족됐다.**

## §2 C 가 찾은 구멍 — 그리고 그것은 A 의 수용 기준의 구멍이다

```
lock 이 REAL_TARGET 경로에만 배선됐다
FIXTURE 경로는 여전히 중복 생성한다 (6 run / 3 target, proc2 가 사후 BatchOverwriteError)
→ '같은 worker 파티션 프로세스 2개 동시 기동' 을 네트워크 없이 end-to-end 증명할 경로가 없다
```

A 는 `D-R0-46` 에서 그 시나리오를 **수용 기준으로 지정**했다. 그런데 지금 구조로는
**그 기준을 실사이트 접속 없이는 실행할 수 없다.**

## §3 DECISION — FIXTURE/SHADOW 경로에도 lock 을 배선한다

```
요구   exactly-once lock 을 REAL_TARGET 뿐 아니라 FIXTURE / SHADOW 실행 경로에도 배선한다
대안   동등한 오프라인 테스트 훅 (lock 경로를 실제로 통과시키는)
```

### 이유 — 이 논증이 결정의 핵심이다

```
exactly-once 는 REAL_TARGET blocking acceptance criterion 이다 (D-R0-38)
그런데 그것을 real launch 로 검증할 수는 없다 —
   real launch 야말로 이 장치가 막으려는 대상이다
따라서 이 기준은 반드시 오프라인에서 증명 가능해야 한다
증명할 수 없는 blocking criterion 은 blocking 이 아니다
```

`2026-08-27 05:14 w02` 의 재발을 막겠다면서, **그 재발 시나리오를 실제로 재현하지 않고는
검증할 수 없는 구조**로 두는 것은 앞뒤가 맞지 않는다.

### 배선하지 않을 경우의 기재 — C 안 채택

배선이 이번 gate 안에 들어오지 못하면 W1 acceptance 의 exactly-once 항목은 **정확히 이렇게만**
기재한다.

```
원시 억제        PASS   (C 하네스 3×3, lock 미삭제, 억제 지점 확인)
배선 코드검토     PASS
e2e 증명         미증명  (FIXTURE 경로에 lock 미배선, 오프라인 재현 경로 없음)
```

**"exactly-once PASS" 로 뭉뚱그리지 않는다.** 세 줄을 다 적는다.
이 세션에서 반복된 규칙이다 — 통과값 하나만 남기면 그 값이 무엇을 삼켰는지 사라진다.

## §4 W2 wip — C 가 계약 정합으로 본 항목 (완료 판정 아님)

```
marker 게이팅 이중화 (probe [] + engine 단락)
signal_type 실소비
Branch U 적용
depth NULL 시정
truncation caveat
```

**fixture 채점은 completion 시점에 한다** — C 가 명시한 대로 이것은 wip 사전감사이지
acceptance 가 아니다. A 도 이 단계에서 W2 를 ACCEPT 하지 않는다.

## §5 검증하지 않은 것

```
FIXTURE 경로 배선 후의 동작        구현 전
W2 fixture 채점                    completion 시
'같은 파티션 2 프로세스' e2e        현재 구조에서 미증명 — 본 결정의 대상
```
