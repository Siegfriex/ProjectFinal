# Migration & Execution Plan v3.0

## Phase V3-0 — Install / Authority Candidate

- v3 pack을 docs/v3_0에 설치.
- A가 v2.1과의 supersession boundary 검토.
- **새 REAL 권한 없음.**

## Phase V3-1 — Finish current 12 METHOD_QUALIFICATION

현재 A release가 허가한 `V2_DIAGNOSTIC` 12만 실행.

현재 blocker: `run_e001_real.py`가 `ExecutionScope.E001_FULL`과 `load_e001_full_*`를 hard-code. diagnostic caller 또는 scope argument 배선 필요.

C exact-SHA preflight 후 실행.

## Phase V3-2 — Qualification Verdict

12에서:
- names/geometry/control/reveal/sequence/auth/obstruction
- prohibited action 0
- evidence lineage
- exactly-once

을 검증. systemic mismatch가 있으면 method fix 후 **같은 qualification contract**로 재검증. task family/frame은 결과를 보고 조정하지 않는다.

## Phase V3-3 — Main 50 Channel Precheck

50 candidate에 mobile-web eligibility smoke.

- ELIGIBLE_PUBLIC_MOBILE_WEB
- APP_REQUIRED_EXCLUDE
- URL_REMAP_REQUIRED
- ACCESS_BLOCKED_REVIEW

부적격은 같은 family replacement로 collection 전 교체.

## Phase V3-4 — Freeze Main Manifest

A가:
- target 50
- task contracts
- fixture
- endpoint
- hash

를 freeze. C 독립 hash/referential integrity 검증.

## Phase V3-5 — Task-Aware Runner Adaptation

B:
- RF 7-way inference bypass
- frozen `task_id`를 TargetSpec으로 전달
- task-specific candidate binder
- Scout→Freeze→Replay
- flow schema/mart

기존 W1/W3/W4 instrumentation 최대 재사용.

## Phase V3-6 — Offline/Fixture Validation

실패주입:
- wrong task_id
- task contract hash mismatch
- endpoint silent change
- outside-manifest service
- app-only target
- accessible name absent/icon-only
- left/right drawer
- modal occlusion
- auth-before-task vs auth-after-select
- replay path drift

## Phase V3-7 — Matched Smoke

family당 2개, 총 10 target 정도의 작은 smoke를 별도 exact scope로 수행. 목적은 main50 효과 추정이 아니라 task-aware runner 검증.

## Phase V3-8 — Full Matched 50

A release + C assurance 후 exactly-once.

## Phase V3-9 — Mart / Analysis

Flow mart → family별 profile → pairwise descriptive matrices → sensitivity → final claims.

## Stop Conditions

- forbidden action attempt
- manifest/hash mismatch
- task contract change after evidence observation
- silent fallback to RF classifier/free exploration
- denominator mismatch unexplained
- evidence identity break
- C hard stop

## Legacy closeout

- RF001/RF002/D15 등은 “왜 RF auto-classification을 main critical path에서 내렸는가”의 audit history로 보존.
- W2 detector를 삭제하지 않음. v3 main path에서 필수 dependency만 제거.
- E001_FULL 59는 suspended/legacy robustness. 자동 재개 금지.
