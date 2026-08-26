# CLAUDE CODE — FIRST SESSION BOOTSTRAP PROMPT
# ProjectFinal Landing Accessibility v2

너는 이 프로젝트의 **Main Orchestrator / Research Integrity Controller / Data Analysis Lead**다.

이번 세션의 목적은 단순 설명이 아니다.

**v2 SSOT를 저장소 실행권위로 설치하고, 독립감사 후 동결한 다음, 기존 오케스트레이션 방식으로 즉시 P-A부터 진행**한다.

사용자에게 micro-task 승인을 요청하지 않는다.

---

## 0. 가장 먼저 할 일 — 아무것도 수정하기 전

repo root:

`/home/sieg/projects-wsl/ProjectFinal`

1. root `CLAUDE.md` 읽기.
2. `git fetch --all --prune`.
3. 현재 remote branch HEAD 확인:
   - `research/landing-accessibility-main`
   - `agent/landing-exec`
   - `audit/landing-adversarial`
   - `audit/landing-ssot`
   - `control/landing-orchestrator`
   - `research/refcohort-r1`
4. 모든 worktree dirty 여부 확인.
5. E001/evidence 본수집이 실제로 시작되지 않았는지 확인.
6. Pilot 수정 여부 0인지 확인.

Prompt에 적힌 SHA를 current라고 가정하지 마라.

다만 expected closure reference는:

- main: `5a9015d1e95b15304aaf53a73efb475934610b82`
- old unverified C013 checkpoint: `87a0464e8159d5526069d5e654e648b0dae506ca`

다.

remote가 다르면 실제 remote를 우선하고 차이를 보고한다.

---

## 1. 기존 종료 인계 읽기

`origin/control/landing-orchestrator`에서 다음을 읽어라.

- `research/landing_accessibility/docs/HANDOFF_PRE_ANALYSIS_START.md`
- `research/landing_accessibility/docs/NEXT_SESSION_ENTRYPOINT.md`
- `research/landing_accessibility/docs/PHASE_EXECUTION_DIRECTIVE_v5.0.md`

이들은 **v2 피벗 이전 closure state를 이해하기 위한 역사적 인계문서**다.

그 안의 `LANDING_ONLY` 실행범위는 새 v2 SSOT가 supersede한다.

---

## 2. v2 문서 설치

사용자가 제공한 v2 docs pack을 저장소에 설치한다.

권장 경로:

`research/landing_accessibility/docs/v2/`

반드시 설치:

- `00_SSOT_v2.0.md`
- `01_DATA_SPEC_v2.0.md`
- `02_COLLECTION_MEASUREMENT_SPEC_v2.0.md`
- `03_CRISP_DM_EXECUTION_PLAN_v2.0.md`
- `04_GLOSSARY_v2.0.md`
- `05_REPO_ORCHESTRATION_PLAN_v2.0.md`

그리고:

`06_PROJECT_CLAUDE_MD_v2.0.md`

내용을 다음 위치의 프로젝트 전용 context로 설치:

`research/landing_accessibility/CLAUDE.md`

root `CLAUDE.md`는 수정하지 않는다.

---

## 3. v2 Authority 선언

새 문서:

`research/landing_accessibility/docs/v2/EXECUTION_AUTHORITY.md`

에 다음을 기계적으로 명시한다.

- CURRENT_SSOT = `00_SSOT_v2.0.md`
- SCOPE = `L0_INITIAL_LANDING + L1_SHALLOW_REPRESENTATIVE_ENTRY`
- HUMAN_FINAL_REVIEW_MAX = 5
- V1_ANALYSIS_SSOT = `SUPERSEDED_FOR_EXECUTION / PRESERVED_FOR_HISTORY`
- PHASE_EXECUTION_DIRECTIVE_v5.0 = `SUPERSEDED_FOR_SCOPE / OPERATIONAL_GUARDS_INHERITED`
- PILOT = READ_ONLY
- E001_V2_STARTED = false

v1 문서는 삭제하거나 이동하지 않는다.

---

## 4. Git Branch 정리

새 repo 생성 금지.

기존 main은 유지한다.

기존 `agent/landing-exec`에는 old C013 WIP가 있으므로 **그 branch에서 v2 개발을 계속하지 않는다.**

새 branch/worktree:

`agent/landing-v2-exec`

를 현재 verified `research/landing-accessibility-main`에서 만든다.

예:

`.agent_worktrees/landing_v2_exec`

환경은 repo의 `scripts/setup_worktree.sh` 규칙을 따른다.

기존:

- audit/landing-adversarial
- audit/landing-ssot
- control/landing-orchestrator

는 재사용한다.

`agent/landing-exec @ old checkpoint`는 삭제하지 않는다.

---

## 5. P0 — V2 REFREEZE

아직 기능개발하지 않는다.

v2 docs와 project CLAUDE context만 먼저 commit한다.

Executor 또는 별도 docs commit을 만든 뒤:

### Adversarial audit
검사:

- 새 scope가 full task로 새지 않는가
- depth가 KWCAG FAIL로 둔갑하지 않는가
- WA 인증을 gold truth로 쓰지 않는가
- human ≤5 정책이 강제분류를 유발하지 않는가
- old C013 WIP이 authoritative input으로 섞이지 않는가
- Pilot write가 없는가

### SSOT audit
검사:

- v2 문서끼리 용어·단위·상태가 일치하는가
- Data Spec과 Collection Spec의 필드가 연결되는가
- CRISP-DM phase가 SSOT와 일치하는가
- `research/landing_accessibility/CLAUDE.md`가 v2만 current로 읽게 하는가
- v1/v2 authority가 모호하지 않은가

두 auditor 모두 exact same target SHA를 감사해야 한다.

PASS 후 orchestrator reconcile → main promotion.

Gate:

`V2_SSOT_FROZEN`

---

## 6. P-A — ANALYSIS FOUNDATION + TASK CODEBOOK

v2 SSOT가 main에 promotion된 뒤 바로 진행한다.

### A1. Mapping Layer

기존 `state/*.parquet` rename/migrate 금지.

v2 analysis interface를 mapping/materialization으로 제공.

### A2. EDA-00

Frame & Provenance Audit.

### A3. EDA-01

Wiseapp Source Structure.

### A4. Functional Codebook

Business Domain과 Interaction Archetype을 분리.

Archetype:

- QUERY
- CONTENT_OPEN
- ITEM_DETAIL
- PLACE_LOOKUP
- COMMUNICATION_ENTRY
- FINANCIAL_ACTION_ENTRY
- UTILITY_ENTRY

각 archetype의 endpoint를 codebook으로 명시.

### A5. Pilot Mapping

10~15개의 다양한 service를 source context만 보고 mapping.

인증/KWCAG outcome은 숨긴다.

rule → embedding → AI reviewer 구조 시험.

ambiguous는 abstain 가능.

### A6. Audit / Promotion

Gate:

`ANALYSIS_AND_TASK_CODEBOOK_FROZEN`

완료 후 사용자에게 묻지 말고 P-B 진행.

---

## 7. P-B — TARGET + TASK FRAME

여기서만 old C013 checkpoint를 selective salvage한다.

절대 전체 merge하지 않는다.

검토 대상으로:

- web eligibility
- official URL
- PSL/registered domain handling
- group split/promote logic

v1 scope-specific assumption은 폐기/재검토.

완료:

- final web targets
- official URL
- representative task
- Business Domain
- Interaction Archetype
- endpoint definition

그리고 certification join.

Gate:

`TARGET_TASK_FRAME_FROZEN`

Audit → promotion → P-C.

---

## 8. P-C — L0/L1 MEASUREMENT ENGINE

Pilot `research/refcohort`는 read-only reference.

직접 import하지 말고 기능 단위 selective port.

### L0

- DOM
- AX
- CSS/geometry
- screenshot
- contrast
- target size
- accessible labels
- motion
- modal/overlay
- primary action visibility

### L1

`Scout → Path Freeze → Deterministic Replay`

- NED
- IED
- MPFED
- text input episode
- scroll episode
- forced dismissal
- auth gate
- endpoint status

### Popup / Obstruction

- candidate detector
- spatial metrics
- semantic class
- dismissibility
- primary action occlusion

### AI Review

deterministic
→ semantic
→ multimodal reviewer A
→ independent reviewer B
→ arbiter
→ HUMAN_FINAL ≤5

남으면 UNDETERMINED.

### KWCAG

전체 33개 완전자동화를 목표로 하지 않는다.

older-relevant + L0/L1 observable subset을 freeze.

KWCAG threshold 자체는 변경하지 않는다.

Gate:

`L0_L1_ENGINE_READY`

---

## 9. P-D — E000_V2

8~12개 diverse target.

failure injection 포함.

목표는 결과가 아니라 **측정기와 evidence lineage 검증**.

PASS 후 audit.

---

## 10. P-E — READY_FOR_E001_V2

동결:

- TARGET_FRAME_SHA
- TASK_CODEBOOK_SHA
- PROTOCOL_SHA
- COLLECTOR_SHA
- PROBE_SHA
- KWCAG_SUBSET_SHA
- AI_REVIEW_RUBRIC_SHA
- AUDIT_DATE

필수:

- open P0 = 0
- blocking P1 = 0
- blocking P2 = 0
- audit lag = 0
- human queue policy valid
- E001_V2 not started

선언:

`READY_FOR_E001_V2`
`FULL_COLLECTION_STARTED = NO`

여기서 반드시 정지한다.

Research Director에게 GO / HOLD 요청.

---

## 11. 운영 방식

기존 loop 유지:

`directive → executor → adversarial ∥ ssot → reconcile → promote → next phase`

`MAX_UNAUDITED_EXEC_CYCLES = 1`

micro-task 질문 금지.

다음만 사용자에게 질문:

- 연구범위 충돌
- 해결 불가능한 P0
- READY_FOR_E001_V2

---

## 12. 최초 보고 형식

v2 설치와 첫 audit/promotion을 완료한 뒤 한 번만 다음을 보고한다.

```
V2 BOOTSTRAP:
V2 SSOT:
PROJECT CLAUDE:
AUTHORITATIVE MAIN:
NEW EXEC BRANCH:
OLD C013:
PILOT:
E001_V2:

ADVERSARIAL:
SSOT AUDIT:
OPEN P0/P1/P2:

CURRENT PHASE:
NEXT GATE:
```

그 뒤 autonomous하게 P-A를 진행한다.
