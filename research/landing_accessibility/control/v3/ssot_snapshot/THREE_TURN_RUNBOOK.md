# ProjectFinal V3 — 3-Turn Orchestration Runbook

## Goal
사용자 개입을 3턴으로 제한한다. 각 턴에서 사용자는 A에게 한 번의 Director packet만 전달하고, A가 내부 버스로 B/C/D를 fan-out하여 해당 Wave를 gate-to-gate로 자율 수행한다.

## Wave 1 — Authority / Qualification / Frame
P0 `V3_CONTRACT_REFREEZE` → P1 `Q12_METHOD_QUALIFICATION` → P2 `MAIN50_FRAME_FREEZE`

종료 산출:
- V3 authority/refreeze decision
- Q12 method qualification verdict
- final matched-task MAIN50 manifest + replacement reserve order
- exact SHA/hash reconciliation
- Wave 2 시작 가능 여부

## Wave 2 — Engine / Pilot / Main Collection
P3 `FLOW_ENGINE_QUALIFICATION` → P4 `V3_MATCHED_PILOT` → P5 `MAIN50_COLLECTION`

종료 산출:
- qualified task-first Flow engine
- 10 matched-task pilot assurance
- frozen main50 raw evidence + retention/hash chain
- C post-run assurance
- Wave 3 시작 가능 여부

## Wave 3 — Mart / Analysis / Claim / Publication
P6 `MART_ANALYSIS_ASSURANCE` → P7 `CLAIM_PUBLICATION`

종료 산출:
- canonical service-task mart
- multidimensional STFP analysis
- C independent replay
- D adversarial robustness synthesis
- A claim registry
- publication-ready figures/tables/evidence cards

## Autonomous transition rule
A는 같은 Wave 내부의 phase 사이에서 Director의 추가 승인을 기다리지 않는다.
다음 조건이 모두 충족될 때 자동으로 다음 phase로 전이한다.
1. B completion이 exact target SHA/hash를 명시.
2. C assurance가 같은 exact target SHA/hash를 독립 검증.
3. A가 SSOT/contract와 일치함을 확인.
4. hard-stop condition이 없음.

## Director interrupt condition
다음 세 경우만 사용자에게 중간 결정을 요구한다.
1. SSOTV3의 substantive construct/task family/endpoint를 바꿔야만 진행 가능한 경우.
2. REAL scope를 사전등록 범위 밖으로 확대해야 하는 경우.
3. evidence overwrite/history rewrite/credential·transaction 등 비가역·금지 행동이 필요한 경우.

그 외 구현 선택, branch/worktree 구성, fixture 추가, replacement reserve 적용, family-level evidence defect 처리, retry prohibition 등은 A가 기존 권위·계약 안에서 결정한다.

## Partial failure policy
- 한 target의 WAF/timeout/evidence defect는 전 프로젝트 hard stop이 아님.
- predeclared replacement reserve가 있으면 P2에서만 deterministic replacement.
- P5 실행 중 실패한 target은 표본 교체 금지. 실패/결측 사유로 보존.
- 한 family의 non-systemic failure는 다른 family 실행을 막지 않음.
- scope leak, duplicate launch, forbidden action, task contract drift, evidence mutation, denominator corruption은 systemic hard stop candidate.

## User interaction
Turn 1: `TURN1_WAVE1_DIRECTOR_TO_A.md`를 A에 전달.
Turn 2: 사용자 메시지는 “2턴 진행” 정도만 필요. ChatGPT가 remote A/B/C/D branches를 다시 읽고 Wave 1을 reconcile한 뒤 Wave 2 packet을 작성.
Turn 3: 사용자 메시지는 “3턴 진행” 정도만 필요. 다시 branches/evidence를 읽고 Wave 3 packet을 작성·최종 종료.
