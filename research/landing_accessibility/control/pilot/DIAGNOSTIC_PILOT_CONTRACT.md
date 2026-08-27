# DIAGNOSTIC PILOT CONTRACT — 동결

**ID** `LA-DIAG-PILOT-CONTRACT-2.1` · **발행** Claude A · **작성** 2026-08-27T23:55:34+09:00
**근거** Director Phase Transition · `D-R0-80`
**run_id** `DIAG-PILOT-001` (A 발행 회차 id — `D-R0-46` 의 idempotency 성분)

---

## §1 이 pilot 이 재는 것과 재지 않는 것

```
잰다      evidence sufficiency        수집된 evidence 가 세 축 측정에 충분한가
          collector integrity          수집기가 계약대로 동작하는가
          representative-surface observability   대표 표면이 관측 가능한가
재지 않는다  detector 성능
          archetype 매핑 정확도
          W2 게이트
```

**PASS 판정에 detector score 를 넣지 않는다.** 넣으면 이 pilot 이 `D-R0-76 §4` 가 지적한
순환이 된다.

## §2 PASS / HOLD 기준

### PASS

```
C0 없음
systemic collection defect 없음 (D-R0-31)
evidence acquisition 정상 — 12 target 에서 L0 evidence 가 계약대로 생성
exactly-once 억제 정상 — 중복 발사 0
prohibited action 0
```

### 즉시 HOLD (C0)

```
exactly-once 억제 실패 — 중복 발사 발생
credential 입력 또는 login submit
CAPTCHA 해결 또는 우회
거래 control 활성화
wrong target 접속 (manifest 밖)
evidence overwrite
```

### systemic 아님 (isolate)

```
단일 사이트 timeout · WAF · 5xx · DNS 실패
단일 사이트 렌더 실패
→ 격리 기록하고 계속한다. 전체를 멈추지 않는다 (프로토콜 §8)
```

## §3 안전 규칙 — 변경 없음

```
no-login          credential 입력 · login submit 절대 금지 (D-R0-03)
                  login control 존재는 차단 사유가 아니다 (D-R0-01)
                  actual auth gate 도달은 FINANCIAL/COMMUNICATION 에서만 endpoint (D-R0-04)
no-CAPTCHA-bypass 해결·우회 금지. active blocking challenge 만 terminal (D-R0-05/65)
transaction       존재 관측만. 활성화 금지 (D-R0-06)
                  장바구니·구매 control 은 FORBIDDEN_TRANSACTION (T-A-W1-P2-DECIDED)
personal data     입력 금지
```

## §4 exactly-once — 이번이 첫 실전 검증이다

```
idempotency_key   ticket_id + run_id + target_id + collector_sha + protocol_sha
run_id            DIAG-PILOT-001  (A 발행, 고정)
lock              target 단위. state {RUNNING, DONE, FAILED_RETRYABLE} + attempts
억제 지점         batch.py EvidenceRun.create 이전
중복 시           launch 하지 않고 DUPLICATE_SUPPRESSED
attempt_id        기록한다 (D-R0-46b) — duplicate 와 retry 를 사후 구분하기 위해
```

**`2026-08-27 05:14 w02` 의 duplicate launch 4건이 이 장치의 부재에서 나왔다.**
**억제 실패는 C0 다.** 이번 pilot 이 그 재발 여부를 실측한다.

## §5 W2 NOT_PASSED 하에서의 산출 규칙

```
archetype 매핑 불가   AMBIGUOUS_UNRESOLVED → ABSTAIN. force-map 금지
MPFED 산출 불가       NULL. 추정하지 않는다
region 미관측         NED 도 NULL
region 관측·endpoint 미도달   NED 보존, IED/MPFED NULL (D-R0-20)
canonical Axis-B association   금지 — W2 acceptance 전까지
```

**detector 가 NOT_PASSED 라는 사실이 수집을 막지 않지만 주장은 막는다.**

## §6 evidence 사용 제한

```
pilot evidence 는 결과 검증 전 canonical analysis 에 사용하지 않는다
검증 주체는 C 다 (independent assurance)
A 가 pilot PASS 를 선언하기 전에는 어떤 수치도 canonical 로 인용하지 않는다
```

## §7 표본 — 동결됨

```
manifest   DIAGNOSTIC_PILOT_MANIFEST.json
sha256     4d3209cad1a316caad117255934617097fdb96f77da67666feb42f71e2c86fc2
n          12 · 7 archetype 전부 · evidence-poor 3
```

**manifest 밖 target 에 접속하면 wrong target 이며 C0 다.**

## §8 full-59 승인 조건 (A 권한)

```
pilot PASS  →  A 가 full-59 RAW COLLECTION 을 승인할 수 있다 (Director 개입 불요)
승인 시 A 가 남길 것
   C0 부재 근거 · systemic defect 부재 근거 · exactly-once 실측 결과
   A run (MLflow) 에 기록
full-59 에서도   W2 NOT_PASSED · AMBIGUOUS=ABSTAIN · MPFED 불능=NULL ·
                 canonical Axis-B association 금지
```

## §9 이 계약이 정하지 않은 것

```
수집 순서·병렬도       B 재량
사이트별 대기시간      B 재량
재시도 정책            B 재량. 단 attempt_id 기록과 exactly-once 는 계약이다
```
