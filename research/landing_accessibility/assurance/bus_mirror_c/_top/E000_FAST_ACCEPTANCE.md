# E000_FAST — 수용 판정 기준 (A 사전 공개)

**작성** Claude A (Authority Plane), 2026-08-27 12:33 KST — **E000 산출물 도착 이전에 공개한다.**
**근거** TIMEBOX `LA-TB-1630-20260827` §7 · A0 최종 지시 §13 · `PHASE_GATES` · `ANALYSIS_CONTRACT` §8

> **왜 미리 공개하나.** 산출물을 본 뒤에 기준을 정하면 그 기준이 결과에 맞춰진다.
> B 와 C 는 무엇으로 판정될지 알고 작업할 권리가 있고, 나는 도착 후 몇 분 안에 판정해야 한다.

---

## 0. 명명 계약 — 위반 시 즉시 반려

- 오늘 산출물은 **`E000_FAST`** 다. 결과 라벨은 **`E000_FAST_PASS`** / **`E000_FAST_SYSTEMIC_FAIL`** 뿐.
- **`E000_V2_VALIDATED` 문자열이 산출물·파일명·JSON 필드에 나타나면 그 자체로 반려.**
  그 Gate 는 8~12 targets + dual-audit 계약이며 **오늘 닫지 않는다. 열린 채 남는다.**

---

## 1. SYSTEMIC PASS 조건 — 9항 전건 충족

| # | 조건 | 내가 확인하는 방법 |
|---|---|---|
| 1 | **predetermined 6 targets / order 유지** | `E000_FAST_PLAN.json` 의 타깃·순서와 실제 run 대조. 결과를 보고 재정렬한 흔적 0 |
| 2 | **L0 + L1 동시 경로** | 모든 run 에 L0 산출물과 L1 종결상태가 **둘 다** 존재. L0-only run 이 1건이라도 있으면 FAIL (A0 §14) |
| 3 | **evidence identity** | observation_id 유일성 · 중복 0 |
| 4 | **append-only** | 기존 evidence 덮어쓰기·삭제 0 |
| 5 | **manifest / hash** | manifest 등재 수 == 디스크 run 수 == batch result 수. 해시 체인 검증 통과 |
| 6 | **no prohibited action** | 로그인·결제·OTP·본인인증·PII·CAPTCHA 우회 **0건.** AUTH_GATE 는 도달 기록만 하고 통과하지 않았을 것 |
| 7 | **collector / protocol SHA 동일** | 6 run 전체가 **같은** collector SHA · protocol version |
| 8 | **failure isolation** | 한 타깃 실패가 다른 타깃 run 을 오염시키지 않음 |
| 9 | **no outcome-conditioned reselection** | 접근성·인증 결과를 본 뒤 target/task/archetype 을 바꾼 흔적 0 |

**추가 (오늘 계약):**
- `execution_mode` 가 `{FIXTURE, SHADOW_DRY_RUN, REAL_TARGET}` **3값 안** (A2 S-3 닫힌 집합)
- `firewall_gate_status_commit_sha` 가 `P0_RELEASE.json` 에 바인딩된 **뒤에** 수집이 시작됐을 것
- 타깃당 wall-clock cap 360초가 실제로 작동 (초과 시 `TRANSPORT_FAILURE`, `UNDETERMINED` 세탁 금지)

---

## 2. **개별 실패로 기록하되 global FAIL 이 아닌 것**

```
WAF · CAPTCHA · AUTH_GATE · APP_REDIRECT · 단일 사이트 transport failure
```

**6건 중 몇 건이 실패해도 그 자체로는 E000 을 반려하지 않는다.** E000 의 목적은
**결과가 아니라 측정기와 evidence lineage 의 검증**이다(TIMEBOX §7 · `PHASE_GATES` P-D).

> 6/6 이 전부 WAF 로 막혀도, **가드가 정확히 작동하고 lineage 가 온전하면 `E000_FAST_PASS`** 다.
> 반대로 6/6 이 전부 성공했는데 manifest 가 어긋나면 `E000_FAST_SYSTEMIC_FAIL` 이다.

---

## 3. GLOBAL HARD STOP — 이 5종만 REAL_TARGET 전체 정지

```
canonical source corruption
systemic evidence identity corruption
outcome-conditioned target contamination
systemic append-only corruption
systemic forbidden external action
```

그 외는 **record → isolate → continue.** global stop 이 걸려도 REAL_TARGET 만 fail-closed 하고
준비·분석 lane 은 계속한다.

---

## 4. 판정 후 즉시 하는 일

**`E000_FAST_PASS` + C 의 QA MATCH (또는 C timeout 시 A fallback) + C0 = 0** 이면
**사용자 재승인을 기다리지 않고 즉시 `E001_RELEASE` 티켓 발행.**

`E000_FAST_SYSTEMIC_FAIL` 이면 실패 항목을 특정해 B 에게 반려하되, **9항 중 어느 것이
왜 깨졌는지**를 명시한다. "더 확인하면 좋을 것" 은 반려 사유가 아니다.

---

## 5. E000 → E001 재사용 조건 (TIMEBOX §7·§9)

E000 이후 다음이 **모두 불변**이면 E000 6 observations 를 **E001 batch-0 으로 canonical reuse** 한다.

```
collector SHA · protocol SHA · target frame · task frame · measurement schema
```

**하나라도 바뀌면 영향 받은 target 만** production collector 로 재수집한다.
C 가 `run.json` provenance 와 batch provenance 의 SHA/protocol_version 을 E000↔E001 간
대조해 다르면 C1 `PROVENANCE_DRIFT` 로 올린다.

> **그래서 B 는 E000 과 E001 을 정확히 같은 collector SHA 로 돌려야 한다.**
> 다르면 재사용 조항이 깨지고 6건을 다시 돌릴 시간이 없다.

---

## 6. 이 판정에서 **하지 않는** 것

- **`OlderRelevantKWCAGFailRate` 를 보지 않는다.** E000 은 측정기 검증이지 결과 산출이 아니다.
- **접근성 결과의 내용을 판정 근거로 쓰지 않는다.** 어느 사이트가 몇 개 FAIL 인지는 E000 수용과 무관하다.
- **새 검사를 추가하지 않는다.** 위 9항 + 3개 추가조건이 전부다 (A0 §22 DO NOT DIG).
