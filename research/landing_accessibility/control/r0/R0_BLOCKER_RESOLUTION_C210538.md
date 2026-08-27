# C-BLOCKER-210538 해소 — D-R0-45 ~ D-R0-50

**ID** `LA-R0-RESOLVE-C210538` · **발행** Claude A · **assertion_type** `DECISION`
**작성** 2026-08-27T21:13:23+09:00 (`date` 판독값)
**대상 blocker** `C-BLOCKER-210538` (C, P1, SCOPED) @ `b7d13fbe20c4f5ff28e5404b09e4e1a38ac92707`
**supersedes** `D-R0-28` (분모 부분)

> C 의 SCOPED HOLD 는 옳았다. 전체 HOLD 를 요구하지 않고 **C2·C3 두 지점만** 막았고,
> B 는 그 경계대로 W3·W4 전면 / W1 guard·wiring / W2 6 archetype 을 이미 진행 중이다.

---

## D-R0-45 — C1b 수용. `D-R0-28` 의 분모를 정정한다 · P1

### A 가 틀린 것

`D-R0-28` 과 `RECONCILE_A_B_CLEAN0.md §4` 에 쓴 **"타깃 커버리지 56/56"** 은 **순환이다.**
분자와 분모를 **같은 관측집합에서** 뽑았다. 관측된 것만 세면 커버리지는 언제나 100% 다.

### A 가 직접 재확인한 사실 — OBSERVATION

```
빈 stub 6 디렉터리  =  3 web_target_group × 2 회      (파일 0개 · 0 bytes)
   wtg_ff3ee504792f6cfc   삼성 인터넷 브라우저   QUERY
   wtg_2cd43b99c1ed87cf   삼성 노트              UTILITY_ENTRY
   wtg_dd5061eb74e2d4d4   삼성 월렛              FINANCIAL_ACTION_ENTRY
셋 다 mart 밖 · evidence 바이트 0
```

### 정정된 분모

```
attempted    59      E001 task frame
observed     56      evidence 바이트가 존재하는 web_target_group
unobserved    3      evidence 바이트 0
```

```
DECISION  이후 모든 커버리지·비율 서술의 분모는 attempted 59 다.
          "56/56" 은 폐기한다. "56 observed / 59 attempted" 로만 쓴다.
          mart 계산의 분모는 observed 56 이되, 그 사실을 항상 명시한다 (W4).
```

### informative missingness 등재

```
등재     3 unobserved 는 informative missingness 후보다
관측     3건이 서로 다른 archetype(QUERY/UTILITY/FINANCIAL)이면서 동일 사업자(삼성)다
경고     동일 사업자 집중은 무작위 결측이 아닐 가능성을 시사한다.
         원인 규명 전까지 "무작위 결측" 으로 취급하지 않는다.
금지     이 3건을 결측으로 조용히 떨어뜨리고 나머지로만 결론내지 않는다.
         분석 산출물에 3건의 존재와 archetype 을 명시한다.
```

### label 모집단과 분석 모집단은 다르다

`LABEL_SPLIT_FROZEN.json` 의 n=56 은 **label 모집단**이다 — 증거가 없는 것은 라벨할 수 없다.
이것은 정당하다. 그러나 **분석 모집단은 59 attempted 이며 label 모집단을 상속하지 않는다.**
두 프레임을 같은 n 으로 부르지 않는다.

---

## D-R0-46 — C2 수용. exactly-once key 명세 확정 · P1 · `D-R0-38` 상세화

C 의 명세를 채택한다. **B 가 부록 A.2.1 에서 독립 제기한 run_id 어휘 충돌과 같은 결론**이고,
B 가 ACK 에서 지지를 명시했다. C 와 B 가 독립적으로 같은 지점에 도달했다.

```
run_id            A 가 발행하는 회차 id — ticket 단위로 고정된 값
                  timestamp 합성(batch.py:358)을 idempotency 성분으로 쓰지 않는다
idempotency_key   ticket_id + run_id + target_id + collector_sha + protocol_sha
lock              target 단위. state ∈ {RUNNING, DONE, FAILED_RETRYABLE} + attempts
retry 허용조건    state == FAILED_RETRYABLE  AND  attempts < max
lock 삭제         하지 않는다 (삭제하면 두 번째 프로세스가 lock 부재를 본다)
억제 지점         batch.py:245 EvidenceRun.create **이전**
                  — 실사이트 접속이 일어나기 전이어야 한다
중복 시 동작      launch 하지 않고 DUPLICATE_SUPPRESSED event 기록
```

### D-R0-46b — attempt_id 계측 (B T-B-FC-002 반영)

B 의 관측: `attempt_count` 가 **4행 전건 None** 이다 → **retry 계측이 산출물에 없다.**

```
DECISION  W1 은 억제뿐 아니라 attempt_id 기록도 구현한다.
이유      계측이 없으면 duplicate 와 retry 를 사후에 구분할 수 없다.
          이번 사건에서 B 도 A 도 처음에 retry 로 오독했고, 판별은 mtime 겹침이라는
          우연히 남은 흔적으로만 가능했다. 다음에는 흔적에 기대지 않는다.
```

### 억제 테스트 (수용 기준)

```
필수  같은 worker 파티션에 대해 프로세스 2개를 동시 기동한다 — 2026-08-27 05:14 에
      실제로 일어난 실패형 그대로다. 순차 2회 호출 테스트만으로는 판별력이 없다.
음성 대조  C 가 심는 중복 발사 fixture 로 억제가 실제로 걸리는지 확인한다
```

**이 항목은 REAL_TARGET blocking acceptance criterion 이다** (`D-R0-38`). 이월 불가.

---

## D-R0-47 — C3 결정. UTILITY_ENTRY region = 옵션 (a) · P1

C 가 제시한 두 갈래 중 **(a) 를 채택한다.** 이는 Research Director 결정 D5 의 적용이다.

```
frozen override   RF-DT v2.1 Branch U 의 region 정의
region_definition function surface entry control
region_signal_type DOM_AX_ROLE
적용 대상          UTILITY_ENTRY 6행 (CSV 의 region_signal_type = CODEBOOK_PENDING 을 대체)
```

### 왜 (b) 가 아닌가

(b) 는 `UTILITY NED 설계상 NULL` 을 지금 선언하는 길이다. 그러면 **UTILITY_ENTRY 는 Axis B 에서
구조적으로 사라진다** — 결측이 아니라 정의상 부재가 되고, ExcessDepth 비교에서 archetype 하나가
통째로 빠진다. 측정 가능한데 정의를 안 줘서 못 재는 것과 원리적으로 못 재는 것은 다르다.

**(a) 는 정의의 발명이 아니다.** Branch U 는 이미 RF-DT v2.1 에 frozen 돼 있고, CSV 의
`CODEBOOK_PENDING` 은 그 DT 가 만들어지기 전 상태다. 이미 있는 frozen 정의를 적용하는 것이다.

```
구속  서비스 outcome 을 보고 서비스별 새 정의를 만드는 것은 금지된다 (D-R0-41).
      6행 전체가 동일한 Branch U 정의를 공유한다.
      개별 사례가 닫히지 않으면 AMBIGUOUS_UNRESOLVED 로 남긴다.
기록  이 override 는 CSV 를 수정하지 않는다. override 사실과 근거를 산출물 provenance 에 남긴다.
```

---

## D-R0-48 — C4 수용. 픽스처 재작성 · P2

`D-R0-42`(marker 삭제 금지 · FIXTURE 전용 · REAL_TARGET disabled)로 인해 **기존 픽스처의 지위가 바뀐다.**

```
기존 픽스처   detector 가 읽는 marker 를 스스로 심는다 → 갭1만 증명하고 갭2 를 증명하지 못한다
필요한 것     REAL_TARGET 모드에서 marker 경로가 호출되지 않음을 증명하는 음성 대조 픽스처
             + marker 없이 DOM_AX_ROLE / FORM_STRUCTURE / URL_PATTERN 만으로 region 이
               성립하는지 보는 실사이트 유사 픽스처
소유          C (adversarial fixture). B 는 자기 detector 를 자기 픽스처로 승인하지 않는다.
```

## D-R0-49 — C5 수용. holdout 이 잴 수 있는 것의 범위를 미리 못박는다 · P2

```
holdout 이 재는 것       label 과 detector 출력의 archetype 일치 / coverage / abstention
holdout 이 재지 못하는 것 endpoint 도달의 정확성 (L1 step DOM 캡처 부재 — 오프라인 불가)
                         실사이트 drift
                         guard 의 실제 안전성 (fixture 로만 검증)
보고 형식                per-archetype 으로 보고한다. 전체 평균 하나로 보고하지 않는다.
이유                     ITEM_DETAIL 26/56 이 전체 평균을 지배한다. 평균 0.85 가
                         소수 archetype 의 0.4 를 삼킬 수 있다.
```

`D-R0-32` 의 목표치(agreement ≥ 0.85, coverage ≥ 0.75)는 **per-archetype 으로도 보고**하되,
소수 archetype 의 미달이 곧 전체 HOLD 는 아니다 — n 이 작으면 추정 자체가 불안정하다.
판정은 A 가 per-archetype 표를 보고 한다.

## D-R0-50 — C6 수용. QUERY LOW_N 사전 등재 · P2

```
QUERY  frame 5 → observed 4 (1건 unobserved: 삼성 인터넷 브라우저)
지위   SSOT §12 archetype n rule 상 n=3~4 는 LOW_N — descriptive only
```

**지금 등재하는 이유**: 결과를 본 뒤에 "n 이 작아서" 라고 말하면 사후 변명이 된다.
**관측 전에 선언해두면 그것은 사전 등록이다.**

QUERY 실사이트 경로가 W1·W2 로 살아나도 이 지위는 바뀌지 않는다. n 은 detector 성능이 아니라
frame 이 정한다.

---

## §최종 — HOLD 해제 범위

```
해제  W1 exactly-once (D-R0-46 · 46b 명세로)
해제  W2 UTILITY_ENTRY region (D-R0-47 옵션 a)
유지  REAL_TARGET NO-GO
```

C 의 acceptance_criteria 를 충족했다 — C1 채택 + C2/C3 DECISION 발행.
C 는 이후 CLEAN-0/R0 broad audit 을 종료하고 **W1~W4 acceptance 독립 검증만** 수행한다 (`D-R0-44`).

## §이 결정이 검증하지 않은 것

```
3 unobserved 의 실제 실패 원인      미규명 (WAF? app-only? 동일 호스트?) — W1 재수집 시 관측
Branch U override 가 실사이트에서 성립하는지   W2 구현 전
억제 명세가 batch.py 에 실제로 붙는지          W1 구현 전
attempt_id 계측의 소급 적용 불가                기존 E001 evidence 에는 없다 — 이후 수집분만
```
