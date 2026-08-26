# research/landing_accessibility — control 브랜치 포인터

**이 파일은 권위 문서가 아니다. 포인터다.**
이 체크아웃은 `control/landing-orchestrator` 브랜치이며 **오케스트레이션 전용**이다.
연구 실행권위는 이 브랜치에 없다.

---

## 1. 이 워크트리에서 무엇을 하는가

| 하는 일 | 하지 않는 일 |
|---|---|
| phase 상태 추적 (`control/state.json`) | 데이터 수집·측정·분석 |
| directive 발행, cycle reconciliation (`control/cycles/`) | 연구 산출물 생성 |
| promotion 실행 (`scripts/promote_landing_main.sh`) | 실행권위 문서 작성 |
| v1 이력·인계문서 보존 (`docs/`, `control/handoff/preserved/`) | v2 규칙의 재선언·요약 |

**v2 규칙을 이 브랜치에 복사하지 마라.** 사본은 원본과 drift 하고, drift 한 사본은 그 자체가 새 결함이다.
(adversarial V2-C001 이 이미 "중복 권위" 축으로 감사한다.)

---

## 2. 실행권위는 어디에 있는가

```
브랜치 : research/landing-accessibility-main   (승격 전 임시로는 agent/landing-v2-exec)
경로   : research/landing_accessibility/docs/v2/
```

| 순위 | 문서 |
|---|---|
| 0 | `docs/v2/EXECUTION_AUTHORITY.md` — 기계적 상태값·권위 서열·기준선 SHA |
| 1 | `docs/v2/00_SSOT_v2.0.md` — 목표·범위·단위·해석의 최상위 권위 |
| 2 | `docs/v2/01_DATA_SPEC_v2.0.md` |
| 3 | `docs/v2/02_COLLECTION_MEASUREMENT_SPEC_v2.0.md` |
| 4 | `docs/v2/03_CRISP_DM_EXECUTION_PLAN_v2.0.md` — Phase Gate 정의 |
| 5 | `docs/v2/04_GLOSSARY_v2.0.md` |
| 6 | `docs/v2/05_REPO_ORCHESTRATION_PLAN_v2.0.md` |
| — | `research/landing_accessibility/CLAUDE.md` (**v2 exec 브랜치의 것**) — 위 6종의 요약. 충돌 시 원본 우선 |

`docs/v2/` 는 이 브랜치 체크아웃에 **파일로 존재하지 않는다.** 읽는 법:

```bash
R=/home/sieg/projects-wsl/ProjectFinal
git -C $R fetch origin
git -C $R show origin/research/landing-accessibility-main:research/landing_accessibility/docs/v2/EXECUTION_AUTHORITY.md
# v2 가 아직 main 으로 승격되지 않았다면:
git -C $R show origin/agent/landing-v2-exec:research/landing_accessibility/docs/v2/EXECUTION_AUTHORITY.md
```

세션을 열 때 **문서의 SHA 를 current 라고 가정하지 마라.** 항상 `git ls-remote --heads origin` 으로 재확인한다.

---

## 3. 기계적 상태값 (사본 아님 — 원본은 EXECUTION_AUTHORITY.md)

이 브랜치의 정본은 `control/state.json` 의 `v2_transition` 이다. 문서 값과 어긋나면
`docs/v2/EXECUTION_AUTHORITY.md` 가 우선하고, `state.json` 을 고쳐 맞춘다.

```
CURRENT_SSOT           = docs/v2/00_SSOT_v2.0.md   (research/landing-accessibility-main)
SCOPE                  = L0_INITIAL_LANDING + L1_SHALLOW_REPRESENTATIVE_ENTRY
STOP                   = READY_FOR_E001_V2
E001_V2_STARTED        = false
PILOT                  = research/refcohort-r1 @ 32460b8  READ_ONLY (수정 시 P0)
```

---

## 4. 이 브랜치의 v1 문서 지위

`docs/*.md`, `control/handoff/preserved/**` 는 **보존 자산**이다. 삭제·이동 금지.

- **유효**: 검증된 사실 — SHA, 카운트, source provenance, Hard Prohibitions.
- **무효**: 실행범위(`LANDING_ONLY`), phase 이름, 정지점 `READY_FOR_E001`.
- 각 파일 최상단에 `SUPERSEDED_*` 배너가 붙어 있다. 배너를 지우지 마라.

---

## 5. 상속된 운영 가드 (v1 `PHASE_EXECUTION_DIRECTIVE_v5.0` → v2)

- `MAX_UNAUDITED_EXEC_CYCLES = 1`
- executor self-approval 금지
- 두 독립감사가 **exact same target SHA** 를 감사해야 promotion
- Pilot(`research/refcohort/**`) 수정 = P0
- `research/landing-accessibility-main` 직접 push 금지 — `scripts/promote_landing_main.sh` 경유만
- UNDETERMINED laundering 금지
- 본수집(GO) 이전 evidence 생성 = gate 위반

강제 수단은 두 층이다.

1. `scripts/promote_landing_main.sh` — 승격 전 precheck 의 **정본**
2. `scripts/hooks/pre-push` — 보호 ref 로의 직접 push 차단.
   설치는 사용자 결정 사항이며 `scripts/install_hooks.sh` 로만 수행한다 (자동 설치하지 않는다).

---

## 6. 부채 원장

`control/state.json`:

- `debt_ledger` / `open_p2` — v1 원장 (total 24 / open 21 / E001_BLOCKING 6). **삭제하지 않는다.**
- `v2_transition.debt_inheritance` — 위 open 21건의 v2 phase 재매핑. 근거 없이 닫지 않는다.
- `v2_transition.v2_audit_findings` — V2-C001 두 감사 등재 (adversarial 7 / ssot 13).
- `v2_transition.open_blocking_total` — `00_SSOT_v2.0.md §15` 의 `open blocking = 0` 판정에 쓰는 값.

Root `/home/sieg/projects-wsl/ProjectFinal/CLAUDE.md` 의 환경규칙(venv·경로·워크트리)은 그대로 상속한다.
