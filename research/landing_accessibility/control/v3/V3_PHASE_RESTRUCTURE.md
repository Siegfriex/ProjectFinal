# V3 Phase 재구조 — 8-phase → 3-STEP

근거 Director 지시 2026-08-28 · A `ede2413`

## 매핑

| 구 phase | 처리 |
|---|---|
| P0 `V3_CONTRACT_REFREEZE` | **완료** — `V3_CONTRACT_FROZEN` (`P0_COMPLETION_REPORT.md`) |
| P1 `Q12_METHOD_QUALIFICATION` | **취소** — 12건 미실행. `HISTORICAL_METHOD_ASSURANCE` 동결 |
| P2 `MAIN50_FRAME_FREEZE` | **STEP 1-A** 로 승계 |
| P3 `FLOW_ENGINE_QUALIFICATION` | **STEP 1-B/C** 로 승계 (B runner + C offline gate) |
| P4 `V3_MATCHED_PILOT` | **STEP 1-E** 로 축소 — pilot 10 → **5** (family 별 1) |
| P5 `MAIN50_COLLECTION` | **STEP 2** — 나머지 45 |
| P6 `MART_ANALYSIS_ASSURANCE` | **STEP 3** |
| P7 `CLAIM_PUBLICATION` | **STEP 3** |

## 실행 구조 변경

```
구  B collection → C assurance → A gate
신  E scout → B canonical replay → C assurance → A gate
```

E 는 선도정찰이며 canonical 이 아니다. `Δ6-c` 가 그대로 구속한다 — **B 는 E route 를 실행 대본으로 재생하지 않는다.**

## A 의 역할 축소

Director 명시: A 는 **Freeze · REAL scope GO · Final claim acceptance** 세 가지만. 세부 구현에 개입하지 않는다.

이에 따라 A 는 다음을 하지 않는다 — 구현 방식 지정, fixture 설계, 워커 배분, 중간 커밋 검토. `T-B-BLK-009` 같은 **권한 판단**은 계속 A 몫이다(구현 판단이 아니다).

## C 의 게이트 3회

Director 가 C 에 직접 지시(C-FINDING-023725): GATE 1 runner offline assurance · GATE 2 REAL pilot 5 · GATE 3 final50+mart+analysis. **중간 커밋마다 검산하지 않는다.**

A 는 이 축소를 수용한다. 다만 게이트 수가 줄었으므로 **각 게이트의 통과 조건이 더 엄격해야 한다** — 검산 횟수를 줄이면서 통과 기준까지 완화하면 두 번 느슨해진다.

## 유지되는 것

`same-SHA producer + assurance` · `ACK 는 completion 이 아니다` · exactly-once · fail-closed firewall · producer≠reviewer · T1~T6 · 티켓 불변 · 결과맹 사전등록 · Director interrupt 3조건.

`E001_FULL` 59 SUSPENDED 유지. **12 PASS → 59 GO 연결 폐기.**
