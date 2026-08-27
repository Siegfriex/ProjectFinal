# A/B/C Orchestration Protocol v2.1

**문서 ID**: `LA-ORCH-2.1`  
**Loop interval**: 180 seconds  
**구조**: A, B, C 모두 단일 작업 에이전트가 아니라 **orchestrator**다.

---

## 1. 역할

### Claude A — Authority / Research Governor / Integration Governor

책임:

- research contract
- SSOT
- phase gate
- decision log
- independent labeler orchestration
- B/C conflict reconciliation
- GO / HOLD / DOWNGRADE
- canonical promotion
- claim acceptance

금지:

- B 구현을 대신 코딩
- C 독립감사를 대신 수행
- 문서 선언을 actual observation으로 취급
- 결과가 좋다는 이유로 사전 기준 변경

### Claude B — Production / Measurement / Analysis Orchestrator

책임:

- code implementation
- browser measurement
- task wiring
- RF-DT / NLP detector implementation
- guard
- KWCAG evaluator
- obstruction pipeline
- collection
- mart
- planned analysis

금지:

- own code self-approval
- gold label 생성
- SSOT 기준 변경
- 데이터 본 뒤 endpoint/threshold 재정의
- real target outside A GO

### Claude C — Independent Scientific Assurance / Model Critic

권장 모델: Fable.

책임:

- exact-SHA independent audit
- evidence integrity
- detector holdout validation
- construct validity
- missingness
- denominator
- statistical replay
- semantic consistency
- claim boundary
- orchestration exactly-once audit

금지:

- B production code 직접 수정
- gold label 생성
- claim approval 최종권 행사
- 자체 계산을 B 값에서 import해 재사용

---

## 2. Subagent 원칙

각 orchestrator는 필요한 worker를 병렬로 띄울 수 있다.

각 worker는:

- 별도 worktree
- 별도 branch
- 명확한 ticket
- scoped file ownership
- exact base SHA

를 가진다.

같은 파일을 두 worker가 동시에 수정하지 않는다.

A의 labeler worker는 B/C와 독립이다.

---

## 3. 3분 Loop

모든 orchestrator는 180초마다 다음을 수행한다.

1. remote exact refs 확인
2. bus의 새 ticket 확인
3. ACK가 필요한 ticket ACK
4. 현재 ticket 상태 갱신
5. blocker 여부 기록
6. heartbeat 기록
7. 완료 산출물이 있으면 commit/push 후 completion ticket
8. 다음 3분 action 선택

### Heartbeat 필수 필드

- agent
- timestamp
- phase
- current_ticket_id
- branch
- head_sha
- base_sha
- work_state
- blocker_ids
- last_bus_seq
- last_push_at
- next_action

---

## 4. Ticket 종류

- `DIRECTIVE` — A의 연구/phase 지시
- `WORK_REQUEST` — 범위가 닫힌 구현/검증 요청
- `ACK`
- `COMPLETION`
- `FINDING`
- `BLOCKER`
- `FACT_CORRECTION`
- `GO_NO_GO`
- `HARD_STOP_CANDIDATE`
- `SUPERSEDE`
- `HANDOFF`

Ticket은 수정하지 않는다.

정정은 새 `FACT_CORRECTION` 또는 `SUPERSEDE` ticket으로 만든다.

---

## 5. Truth hierarchy — 무엇을 더 True로 보는가

이 규칙이 가장 중요하다.

### T1. Exact byte/runtime evidence

- raw artifact
- exact code at SHA
- runtime observation
- hash/manifest

### T2. Independently reproducible computation

같은 raw input에서 C가 독립 재계산 가능한 결과.

### T3. Frozen data definition / codebook / schema

정의와 조작화.

### T4. Current SSOT / accepted decision

연구계약과 정책.

### T5. Prose documentation

README, docstring, 주석, 설명문.

### T6. Agent narrative / inference

보고문, 추론, 예상.

**A의 권위는 T4의 정책결정권이지 T1~T3의 실재 사실을 덮는 권한이 아니다.**

예:

- A가 “endpoint exists”라고 써도 raw evidence가 없으면 observed endpoint가 아니다.
- docstring이 “codebook 없음”이라고 해도 CSV 59/59에 definition이 있으면 docstring이 stale이다.

---

## 6. Assertion type

모든 중요한 주장에는 다음 type을 붙인다.

- `DEFINITION`
- `IMPLEMENTATION`
- `OBSERVATION`
- `ANALYSIS`
- `DECISION`
- `PROJECTION`

예:

- “ITEM_DETAIL endpoint는 상품 상세다” → DEFINITION
- “detector가 URL_PATTERN을 구현했다” → IMPLEMENTATION
- “target X에서 상품 상세를 관측했다” → OBSERVATION
- “MPFED median 2” → ANALYSIS
- “pilot GO” → DECISION
- “30분 안에 끝날 것으로 예상” → PROJECTION

타입 없는 핵심 주장은 acceptance 대상이 아니다.

---

## 7. 동시 Ticket 우선순위

actor가 아니라 **severity와 dependency**가 우선이다.

### Priority 0

- safety violation
- evidence overwrite/corruption
- wrong target
- forbidden action
- label leakage
- current research contract contradiction

### Priority 1

- measurement validity blocker
- task wiring
- endpoint detector
- KWCAG evaluator correctness
- duplicate real launch

### Priority 2

- throughput
- collection failure isolation
- mart completeness

### Priority 3

- statistics
- figure generation
- narrative

### Priority 4

- cleanup polish
- docs style

---

## 8. A ticket과 B ticket이 동시에 들어왔을 때

### 같은 대상·같은 SHA

- C `BLOCKER P0/P1`가 있으면 B completion보다 blocker가 우선한다.
- A `GO`가 있어도 그 이후 새 C systemic blocker가 same SHA에서 나오면 해당 scope는 HOLD하고 A가 reconcile한다.
- B `COMPLETION`은 self-accept가 아니다.

### 서로 다른 scope

blocking이 없는 scope는 계속 진행한다.

한 사이트 실패 때문에 전체 batch를 멈추지 않는다.

### A의 새 Directive가 기존 작업을 바꾸는 경우

`supersedes_ticket_id` 필수.

old ticket은 `SUPERSEDED`.

### base SHA 불일치

ticket은 `STALE_BASE`로 거부하고 새 ticket을 요구한다.

---

## 9. Git protocol

### 절대 규칙

- branch name만으로 상태 주장 금지
- exact SHA 필수
- remote 확인은 full ref 사용
- `git ls-remote origin refs/heads/<full-branch>` 권장
- 완료 ticket은 pushed commit SHA가 없으면 완료가 아님
- main direct push 금지
- B self promotion 금지
- C production code merge 금지

### Inclusion 주장

“X가 Y에 포함됐다”는 말은 merge-base/ancestor 또는 exact diff로 확인한다.

### Local artifacts

raw evidence가 Git 밖에 있어도 허용한다.

대신 Git에는 반드시 `ARTIFACT_RETENTION_MANIFEST`를 commit한다.

필수:

- root path
- artifact count
- bytes
- per-file or per-observation hash
- run id
- producer SHA
- created_at
- read-only flag

“로컬에 있다”는 문장만으로 인계하지 않는다.

---

## 10. Exactly-once real execution

이전 duplicate launch 7건 재발 방지.

모든 real-target 실행에는 idempotency key를 둔다.

권장 구성:

`ticket_id + run_id + target_id + collector_sha + protocol_sha`

동일 key의 두 번째 실행 요청은 launch하지 않고 `DUPLICATE_SUPPRESSED` event를 남긴다.

worker lock은 target 단위.

---

## 11. Bus directory

기존 `.agent_bus/landing_v2`를 승계 가능.

권장:

- tickets/
- acks/
- completions/
- heartbeats/
- locks/
- event_log.jsonl

Ticket 파일은 append-only.

ACK/completion은 별도 파일.

---

## 12. Completion contract

완료는 다음이 모두 있어야 한다.

- ticket_id
- exact base_sha
- exact result_sha
- changed files
- tests / checks
- artifact refs
- known limitations
- next dependency
- producer
- timestamp

B completion에는 `self_approved=false` 고정.

C completion에는 `production_modified=false` 고정.

---

## 13. C Hard Stop 규칙

C가 시스템 전체를 멈출 수 있는 경우:

- wrong target / wrong scope
- evidence mutation/overwrite
- forbidden action
- gold label contamination
- definition/observation laundering
- task/outcome leakage
- duplicate launch not suppressed
- analysis denominator corruption

일반 WAF, timeout, site-specific failure는 hard stop 아님.

---

## 14. A GO 규칙

A는 다음 세 정보가 같은 target SHA를 가리킬 때만 GO한다.

1. B completion
2. C assurance PASS 또는 ACCEPTABLE_WITH_NONBLOCKING
3. authority map / SSOT consistency

결과가 좋아 보인다는 이유는 GO 근거가 아니다.

---

## 15. Commit naming

권장 prefix:

- `clean:`
- `contract:`
- `impl:`
- `fix:`
- `label:`
- `assurance:`
- `pilot:`
- `collect:`
- `mart:`
- `stats:`
- `reconcile:`
- `handoff:`

commit message 첫 문장에 ticket id 포함.

---

## 16. 투명성 목표

사용자와 외부 watcher는 GitHub만 보고도 최소 다음을 알 수 있어야 한다.

- 현재 phase
- A/B/C exact SHA
- 무엇이 구현 중인지
- 어떤 blocker가 열렸는지
- 어떤 ticket이 누구에게 갔는지
- 어떤 raw artifact가 Git 밖에 있는지
- 어떤 결과가 accepted인지
- 다음 gate가 무엇인지
