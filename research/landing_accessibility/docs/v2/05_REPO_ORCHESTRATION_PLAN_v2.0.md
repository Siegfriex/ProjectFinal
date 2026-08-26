# Repository / Branch / Orchestration Plan v2.0

## 1. 새 저장소는 만들지 않는다

현재 `ProjectFinal` 안에서 계속 간다.

새 repo를 만들면 기존 source provenance, Pilot, audit history, handoff와 연결이 끊어져 오히려 불리하다.

---

## 2. 삭제 중심 청소는 하지 않는다

현재 repo는 세션동결 상태이며 기존 main과 Pilot은 보존가치가 높다.

따라서:

- 기존 v1 docs 삭제 금지
- `research/refcohort/**` 수정 금지
- `agent/landing-exec @ 87a0464e` 삭제 금지
- 기존 state parquet rename 금지

대신 **실행권위만 v2로 이동**한다.

---

## 3. 권장 Branch

### 유지

- `research/landing-accessibility-main`
  - 유일한 promoted 연구 기준선

- `control/landing-orchestrator`
  - phase 상태·directive·handoff

- `audit/landing-adversarial`
  - 적대적 감사

- `audit/landing-ssot`
  - SSOT/권위 감사

- `research/refcohort-r1`
  - Pilot read-only

### 새로 1개만 생성

- `agent/landing-v2-exec`

기준:

`origin/research/landing-accessibility-main`

이유:

기존 `agent/landing-exec`에는 old-scope C013 UNVERIFIED WIP가 들어 있으므로 그대로 이어서 개발하면 v1/v2가 섞일 위험이 있다.

기존 WIP는 `87a0464e`에서 필요한 파일/아이디어만 **선택적으로 salvage**한다.

---

## 4. v2 문서 위치

권장:

```text
research/landing_accessibility/
├── CLAUDE.md
├── docs/
│   ├── v2/
│   │   ├── 00_SSOT_v2.0.md
│   │   ├── 01_DATA_SPEC_v2.0.md
│   │   ├── 02_COLLECTION_MEASUREMENT_SPEC_v2.0.md
│   │   ├── 03_CRISP_DM_EXECUTION_PLAN_v2.0.md
│   │   ├── 04_GLOSSARY_v2.0.md
│   │   └── 05_REPO_ORCHESTRATION_PLAN_v2.0.md
│   └── ... 기존 v1 문서
```

기존 v1 문서를 `legacy/`로 물리 이동할 필요는 없다.

문서 index와 `CLAUDE.md`에서 v2만 current로 선언하면 충분하다.

---

## 5. Root CLAUDE.md는 건드리지 않는다

현재 root `CLAUDE.md`는 repo 전체 환경·GPU·Python·worktree 규칙을 담고 있다.

이를 프로젝트 연구지침으로 덮어쓰지 않는다.

대신:

`research/landing_accessibility/CLAUDE.md`

를 새로 두어 이 하위 프로젝트의 연구권위와 운영규칙만 넣는다.

---

## 6. 오케스트레이션

기존 구조 유지:

`orchestrator directive → executor → adversarial ∥ ssot → reconciliation → promotion`

규칙:

- `MAX_UNAUDITED_EXEC_CYCLES = 1`
- executor self-approval 금지
- exact target SHA가 같은 두 감사가 있어야 promotion
- Pilot 수정 = P0
- v1 old WIP을 분석입력으로 사용 = P0
- 본수집 전 evidence 생성 = gate 위반
- main 직접 push 금지
- non-blocking debt 때문에 critical path를 멈추지 않음

---

## 7. v2 첫 Promotion

P0 `V2_REFREEZE`에서:

1. v2 docs 설치
2. nested `CLAUDE.md` 설치
3. v2 execution directive 생성
4. v1 실행지침은 `SUPERSEDED_FOR_EXECUTION`으로 표기하되 삭제하지 않음
5. adversarial + ssot audit
6. orchestrator reconcile
7. main promotion

그 이후 v2만 current execution authority.

---

## 8. C013 Salvage

`87a0464e` 전체 merge 금지.

파일/기능별 검토:

- web eligibility: 높은 재사용 가능성
- official URL: 높은 재사용 가능성
- PSL/domain: 높은 재사용 가능성
- v1 landing-only gate assumptions: v2에 맞춰 재검토
- old protocol claims: 자동 승계 금지

salvage 결과는 새 v2 executor commit으로 만들고 다시 감사한다.

---

## 9. 새로운 Run 이름

혼동 방지를 위해:

- `E000_V2`: smoke
- `E001_V2`: main L0+L1 collection

을 권장한다.

v1에서 E001이 실제 시작되지 않았더라도 protocol lineage가 명확해진다.

---

## 10. 추적 State

각 phase 종료 시 반드시:

- current_phase
- authoritative_main_sha
- latest_exec_sha
- adversarial_target_sha
- ssot_target_sha
- input_manifest_sha
- output_manifest_sha
- open_p0
- open_blocking_p1
- open_blocking_p2
- human_final_queue_n
- E001_V2_started
- next_phase

를 남긴다.

상태값은 가능하면 artifact에서 자동 계산한다.
