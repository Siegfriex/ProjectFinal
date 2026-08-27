# D-R0-66 — W4 ACCEPT · W1 부분 결정 · cap 편향 사전등록

**발행** Claude A · **작성** 2026-08-27T22:19:37+09:00 · **assertion_type** `DECISION`
**권한 근거** `D-R0-64` Director unattended window

---

## §1 W4 REWORK — ACCEPT

```
B completion   T-A-W4-001-REWORK @ b27794feccc4ab07efd87aaad54bf648798fa293  (self_approved=false)
C verification W4_REWORK_C_VERIFIED_MATCH @ 615fc6850d3562993f868a36cac5b17575e69942
              verdict = ACCEPTABLE_WITH_NONBLOCKING, severity_max = P3
```

프로토콜 §14 세 정보가 같은 SHA 를 가리킨다. **`D-R0-58` HOLD 를 해제한다.**

### C 가 확인한 것

```
artifact sha256 95c66d12… / 7a1f7ac9… 일치, 63행, MEASURED 53
overlay_coverage vs canonical 82f631f   53/53 일치 — geometry 불변이 실측으로 재확인
234 interrupt 에 interrupt_form / interrupt_semantic + status 2축, 축 어휘 교차 0
classifier_version v2 + 전이표 provenance 첨부 (D-R0-58-2 충족)
```

**`축 어휘 교차 0` 이 `D-R0-58-1` 의 핵심이었다** — 두 축이 서로의 필드를 덮지 않는다.

### 22 vs 19 불일치 — 해소됨, 결과 영향 없음

```
C 22   58 probe 전체 635 후보 기준
C 20   mart 참조 56 관측 · overlap>0 192 후보 기준
B 19   mart interrupt 234 기준
잔여 1  B 의 interrupt 필터(NOT_CLASSIFIED 제외 등) 차이로 추정
```

**또 모집단 경계 문제였다.** 이번 세션에서 세 번째다 (A/B artifact 1243 vs 1265 · prior 21 vs 22 ·
지금 22 vs 19). 셋 다 계산 오류가 아니라 **경계 미명시**였고, 경계를 밝히면 즉시 닫혔다.

### D-R0-66-1 — semantic 축의 `PROMOTION_MODAL` 동명 (C 가 A 판단 요청, P3)

```
문제   form 축과 semantic 축에 같은 토큰 PROMOTION_MODAL 이 있다
결정   semantic 축은 PROMOTION 을 쓴다. PROMOTION_MODAL 은 form 축 전용으로 둔다
```

**이유**: `D-R0-58-1` 이 두 축을 **직교**로 정했다. 같은 토큰이 양쪽에 있으면
`form=PROMOTION_MODAL, semantic=PROMOTION_MODAL` 같은 무정보 조합이 생기고,
읽는 쪽이 어느 축의 값인지 문맥으로 추측하게 된다. `_MODAL` 은 **형태**를 가리키는 접미사이므로
semantic 축에 있을 자리가 아니다.

**이것은 construct 변경이 아니라 이미 정한 직교성의 표기 정리다** — HOLD 트리거 아님.

## §2 W1 — 단독 ACCEPT 하지 않는다 (C 판단 채택)

```
C verdict   W1 단독 ACCEPT 불가 (joint gate 설계상)
            W1 scope 내 항목은 PASS
            blocking 잔여 = 원장 귀속(P1) + CAPTCHA(P1, W2 파일)
```

**A 도 W1 을 단독 ACCEPT 하지 않는다.** `D-R0-18` 이 W1+W2 를 한 gate 로 묶었고,
`D-R0-65` 가 G1-c 를 그 gate 에 추가했다.

### C 가 확인한 W1 scope 내 PASS

```
exactly-once 세 줄     원시 억제 PASS(3proc×3key) · 배선 코드검토 PASS(REAL+FIXTURE,
                       EvidenceRun.create 이전) · e2e(FIXTURE) evidence 단위 PASS(3 run/3 target)
guard fixture          target-level kill 0/8 — G1-a PASS. 로그인 링크·구매 버튼이 있어도 Scout 생성
                       FINANCIAL LOGIN gate=endpoint PASS · 비금융 gate≠endpoint PASS
                       credential 입력/submit 0
```

**`D-R0-60` 이 요구한 세 줄 기재가 실제로 세 줄로 나왔다.** "exactly-once PASS" 로
뭉뚱그리지 않았다.

### D-R0-66-2 — `intended_regressions_4` 처리 (C 가 A DECISION 요청)

C: *"옛 assertion 이 target-level kill 자체를 기대값으로 삼았으므로 계약 변경에 따른 정당한 갱신"*

```
결정   허용한다. 소유자(W1)가 4건을 갱신한다
근거   D-R0-01 이 target-level kill 을 폐기했다. 그 동작을 기대값으로 삼은 테스트는
       이제 폐기된 계약을 검사하고 있다 — 테스트가 틀린 것이지 구현이 틀린 것이 아니다
```

**조건 — 테스트 갱신은 결함을 숨기는 가장 쉬운 경로이므로 좁게 연다**

```
1  갱신 대상은 정확히 그 4건이다. diff 에 다른 assertion 변경이 섞이면 거부한다
2  각 건에 '무엇을 기대했고 계약이 어떻게 바뀌었는지' 를 주석으로 남긴다
3  C 가 diff 를 독립 확인해 다른 assertion 이 약화되지 않았음을 검증한다
4  B 가 W1 에게 이미 내린 'fixture 로 우회하지 말라' 지시(D-R0-59-3)와 충돌하지 않는다 —
   그것은 production 결함을 숨기는 우회를 금지한 것이고, 이것은 폐기된 계약을 검사하는
   테스트의 갱신이다. 둘을 구분한다
```

### D-R0-66-3 — candidate_action_states 노출 요구 (C inconclusive 해소)

```
C: DISABLED_OR_INERT / BLOCKED_BY_OVERLAY candidate state 가 batch detail 에 없어 미채점
결정: B 가 batch detail 에 candidate_action_states 를 남긴다
```

`D-R0-02` 가 9상태 mask 를 정했는데 **그중 두 상태가 산출물에서 관측 불가**하다.
정의만 있고 관측이 없으면 그 두 상태는 검증할 수 없다 — `DEFINITION` 이 `OBSERVATION` 으로
승격되지 않는 지점이다.

## §3 D-F-Q1 cap 편향 — C CONFIRMED, result-affecting (A6 경로로 도달)

C 가 D 의 finding 을 replication 해 `D_CONFIRMED` 를 냈고 result-affecting 으로 A 에게 올렸다.
**A6 경로가 처음으로 정상 작동했다** — D → C → A, A 는 D 를 직접 읽지 않았다.

```
내용   probe cap 절단이 대형 커머스에 몰린다 (cap-hit 15 중 prior ITEM_DETAIL 11/15 = 73%,
       전체 43% 대비)
영향   archetype 간 비교가 왜곡될 수 있다
```

### D-R0-66-4 — 사전등록 (결과 보기 전)

```
1  archetype 비교 산출물에 cap-hit 분포를 반드시 병기한다
2  archetype 간 비교에는 cap-hit 관측 제외 sensitivity 를 함께 낸다
3  cap 편향을 근거로 archetype 결론을 바꾸지 않는다 — 편향의 존재를 보고할 뿐이다
4  검정하지 않는다. 이것은 기술통계이며 유의성 주장이 아니다 (C 가 이미 명시한 경계)
```

**`D-R0-53` 과 정합한다** — cap 영향권 지표만 UNDETERMINED 후보로 두는 결정에
archetype 비교 축의 처리를 더한 것이다. **threshold 를 바꾸지 않으므로 HOLD 트리거가 아니다.**

## §4 C 의 A2 준수 요청 — EXPOSED_HISTORY 추가

C: 공개 레지스터 v1/v2 가 holdout target_id 를 노출했고 v3 에서 제거했다. 등재 요망.

```
등재한다. 삭제로 없던 일 처리하지 않는다 (Director A2 · D-R0-62-4).
C 의 per-target 정보는 artifacts/c_only_holdout/ (git 미추적, sha256 eb171012…) 로 이동됐다.
```

## §5 이 결정이 검증하지 않은 것

```
W2 completion               C 검증 미착수 (B 22:14 제출, C 는 C3/C4 진행 중)
원장 귀속 P1 (C-BLOCKER-220418)  B 수정 대기
semantic 정밀도             label 대비 미검증 (C not_verified)
PrimaryActionOcclusion      PENDING_TASK_BINDING 유지
intended_regressions_4 diff  갱신 전
```
