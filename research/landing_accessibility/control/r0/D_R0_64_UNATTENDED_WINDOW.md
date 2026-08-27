# D-R0-64 — Director Unattended Window

**발행** Claude A · **작성** 2026-08-27T22:14:52+09:00 (`date` 판독값) · **assertion_type** `DECISION`
**권한** Research Director · **효력** 본 문서 시각부터 HOLD 발생 또는 Director 복귀까지

---

## §1 위임된 것과 위임되지 않은 것

**위임된 것 — A 가 Director 복귀를 기다리지 않고 진행한다**

```
P0 holdout recovery
  → W1 / W2 / W3 / W4  C-acceptance
  → offline validation
  → stratified REAL pilot
  → pilot PASS 시 full 59 collection
  → mart / planned statistics
```

**위임되지 않은 것 — 게이트 자체는 그대로다**

```
Director 는 A7 의 전건 7종을 면제하지 않았다.
위임된 것은 "게이트를 통과했다는 판정을 A 가 내린다" 이지
"게이트를 건너뛴다" 가 아니다.
```

**조건**: `현재 frozen 연구계약을 변경하지 않는 한`.

## §2 HOLD 트리거 — 넷 중 하나라도 발생하면 정지하고 Director decision 요청

```
1  C0
2  result-affecting unresolved C1
3  holdout 독립성 붕괴
4  SSOT / construct / threshold 변경 필요
```

### 각 트리거의 조작적 정의 — 판단이 갈리지 않게 지금 못박는다

```
C0                      프로토콜 §7 Priority 0 — safety violation · evidence overwrite/corruption ·
                        wrong target · forbidden action · label leakage · 현 연구계약 모순
result-affecting C1     측정 타당성 blocker 중 "이미 산출된 값 또는 앞으로 산출될 값을 바꾸는" 것.
                        구현 편의·성능·가독성 문제는 해당하지 않는다
holdout 독립성 붕괴      D-R0-63 A1 의 clean 18 이 더 줄어드는 새 노출.
                        이미 등재된 26/23/18 구조 자체는 붕괴가 아니라 현재 상태다
SSOT/construct/threshold 새 archetype · 새 endpoint 정의 · KWCAG subset 확대 ·
변경 필요                detector threshold 를 계약 밖 근거로 정하는 것 · 분모 정의 변경
```

**애매하면 HOLD 한다.** 위임의 취지는 속도이지 판단 완화가 아니며,
**잘못된 진행보다 불필요한 HOLD 가 싸다.**

## §3 변경되지 않는 안전 규칙 — Director 명시

```
exactly-once                      그대로 적용 (D-R0-38 · 46 · 46b · 60)
no-login                          credential 입력 · login submit 절대 금지 (D-R0-03)
no-CAPTCHA-bypass                 해결·우회 금지. active blocking challenge 만 terminal (D-R0-05)
prohibited action set             완화하지 않는다 — guard 입도만 정밀화 (D-R0-01~06)
ORIGINAL_E001                     READ_ONLY
```

**REAL pilot 과 full run 에 기존 safety 규칙이 그대로 적용된다.** 무인 진행이
안전 규칙을 느슨하게 만들지 않는다 — 오히려 감시자가 없으므로 규칙이 유일한 방어다.

## §4 A 가 이 창에서 지킬 것

```
1  게이트 판정마다 A run 을 남긴다 (A5) — 무인이므로 사후 검증 가능성이 유일한 통제다
2  B completion 을 C 검증 없이 ACCEPT 하지 않는다 (§14) — 위임되지 않았다
3  결과가 좋아 보인다는 이유로 사전 기준을 바꾸지 않는다
4  계산 불가능한 분석을 다른 것으로 대체하지 않는다 (D-22)
5  새 governance 산출물을 만들지 않는다 (A7 · D-R0-44)
6  HOLD 시 무엇을 왜 멈췄는지와 Director 가 결정할 선택지를 함께 제시한다
```

**3번이 이 창에서 가장 위험하다.** 무인 진행 중에는 기준을 바꾸는 것을 지적할 사람이 없다.
그래서 **사전등록이 이미 되어 있는 것들**(D-R0-50 QUERY LOW_N · D-R0-52 DecisionCoverage 상한 ·
D-R0-56 coverage 분모 · D-R0-61 PRECEDENCE_CONTESTED · D-R0-63 A1 채점 3종)이 방어선이다.
**그것들을 이 창에서 수정하지 않는다.**

## §5 현재 위치

```
완료   R0_GO · LABEL_FROZEN · HOLDOUT_RECOVERY_DECISION · W2_CONTAMINATION_CLEARANCE
       W3 Stage 0 ACCEPT
진행   W1(guard·wiring·exactly-once) · W2(detector) · W3 Stage 1 · W4 rework
대기   W1_W2_JOINT_GATE · W3_ACCEPTANCE · W4_ACCEPTANCE · OFFLINE_VALIDATION_GATE
       · REAL_PILOT_GO_NO_GO
현재   REAL_TARGET = NO-GO (A7 전건 미충족)
```

## §6 이 결정이 검증하지 않은 것

```
A 의 무인 판정 품질        사후 검증 대상. A run 과 커밋 이력이 그 근거다
pilot PASS 기준의 적용     아직 적용해본 적 없다 (D-R0-31 systemic mismatch 기준)
full 59 의 실행 안정성     exactly-once e2e 는 FIXTURE 에서만 확인됐다 (C-FINDING-215734)
```
