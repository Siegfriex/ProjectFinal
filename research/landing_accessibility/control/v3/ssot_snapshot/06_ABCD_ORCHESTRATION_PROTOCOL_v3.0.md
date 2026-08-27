# A/B/C/D Orchestration Protocol v3.0

## 1. 역할

### A — Authority / Research Governor
- v3 SSOT 채택·수정 권한
- task-family/endpoint/target-frame freeze
- REAL scope release/revoke
- 최종 claim 승인
- 결과를 보고 task/endpoint/frame을 바꾸는 행위 차단

### B — Production / Collection / Mart Orchestrator
- current 12 diagnostic caller wiring 및 실행
- task-aware collector/scout/replay 구현
- frozen task registry 소비
- evidence/mart 생성
- RF 7-way classifier 개선은 v3 critical path가 아님

### C — Independent Scientific Assurance
- target eligibility/task comparability 독립검증
- exact-SHA firewall/replay/recompute
- evidence lineage, denominator, metric 재계산
- main release 전 hard-stop 판정

### D — Independent Measurement Research Sandbox
- Cross-Service Flow 측정방법 EDA
- spatial/label/control/sequence/depth/auth/obstruction sensitivity 연구
- non-canonical, production 수정 금지
- task gold 생성 금지, REAL target 독자 실행 금지
- finding은 원칙적으로 `to=C, cc=A`로 전달

## 2. Truth hierarchy

1. exact bytes/runtime/evidence
2. independently reproducible computation
3. frozen task/target/schema/codebook
4. accepted SSOT/decision
5. prose documentation
6. agent narrative

## 3. Ticket types

`DIRECTIVE / IMPLEMENTATION / BLOCKER / FINDING / ASSURANCE / FACT_CORRECTION / DECISION_REQUEST / COMPLETION`

Priority: P0 safety/authority > P1 measurement validity > P2 execution blocker > P3 research/optimization > P4 documentation.

## 4. v3-specific routing

- A→B: implementation/release directive
- B→C: validation request + exact SHA/artifacts
- C→A: assurance verdict / hard stop
- D→C, cc A: research finding
- D가 A로 직접 canonical conclusion을 우회 전달하지 않음 (A explicit request 예외)

## 5. Git

- branch/worktree exact SHA를 모든 ticket에 기록.
- worker 실행 중 `git add -A` 금지. 확정 파일만 명시 stage.
- 완결 게이트: top-level verdict/result + FINDINGS/manifest 존재 후 commit.
- commit 직후 `git show --stat`으로 message와 포함파일 대조.
- history rewrite로 결함 은폐 금지; superseding finding으로 시정.

## 6. REAL exactly-once

- frozen manifest hash + release document + allowlist + final navigation guard.
- outside-manifest target 0 허용.
- same service-task 재수집은 새 run id, 기존 evidence overwrite 금지.

## 7. 3분 heartbeat

각 plane은 최소:
- timestamp KST
- branch/worktree
- exact HEAD
- current task/ticket
- artifact/result
- blocker
- next gate
- decision needed

## 8. Completion

“코드가 있다”가 완료가 아니다. exact SHA + 실행/검증 결과 + artifact + claim boundary + known limitation이 필요하다.
