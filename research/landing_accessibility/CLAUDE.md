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

**권위 서열의 정본은 `docs/v2/EXECUTION_AUTHORITY.md` §2 다.**
이 파일은 그 표를 **옮겨 적지 않는다.** 사본은 원본과 drift 하고, drift 한 사본은
그 자체가 새 결함이다(§1). 서열을 알아야 하면 아래 명령으로 **원본을 읽어라.**

이 파일이 서열에 대해 말할 수 있는 전부는 다음 세 문장이다.

- 최상위(1위)는 `docs/v2/00_SSOT_v2.0.md` 다. 다른 어떤 문서도 그 위에 오지 않는다.
- `docs/v2/EXECUTION_AUTHORITY.md` 는 서열을 **선언하는** 문서이지 서열 **안에** 있는 문서가 아니다.
  그 파일과 `00_SSOT_v2.0.md` 가 충돌하면 `00_SSOT_v2.0.md` 가 우선한다 (그 파일 머리말이 그렇게 적는다).
- 서열 항목 수·순서·각 문서의 지위는 **여기 적지 않는다.** `EXECUTION_AUTHORITY.md` §2 와
  `docs/INDEX.md` 가 정본이며, 이 파일의 요약을 근거로 인용하는 것은 금지다.

Gate 이름·통과조건·판정권한의 정본은 `docs/v2/PHASE_GATES.md` 다.
`03_CRISP_DM_EXECUTION_PLAN_v2.0.md` 는 실행 Phase 를 정의하지만 **Gate 를 정의하지 않는다**
(`PHASE_GATES.md` §0). Gate 를 `03` 이나 `bootstrap/07` 에서 인용하지 마라.

`docs/v2/` 는 이 브랜치 체크아웃에 **파일로 존재하지 않는다.** 읽는 법:

```bash
R=/home/sieg/projects-wsl/ProjectFinal
git -C $R fetch origin
git -C $R show origin/research/landing-accessibility-main:research/landing_accessibility/docs/v2/EXECUTION_AUTHORITY.md
git -C $R show origin/research/landing-accessibility-main:research/landing_accessibility/docs/v2/PHASE_GATES.md
git -C $R show origin/research/landing-accessibility-main:research/landing_accessibility/docs/INDEX.md
# v2 가 아직 main 으로 승격되지 않았다면 origin/agent/landing-v2-exec 로 바꿔 읽는다.
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

**2층은 현재 설치돼 있다** (2026-08-26, 오케스트레이터가 `install_hooks.sh --symlink` 실행).
`.git/hooks/pre-push` 가 위 정본을 가리키는 심링크이고 `core.hooksPath` 는 unset 이다.
직전의 미추적 legacy 사본은 `.git/hooks/pre-push.bak.<timestamp>` 로 백업됐다
(adversarial V2-C002 `repo-canonical-pre-push-hook-is-inert-legacy-copy-in-effect` — V2-C003 adversarial 이
유효 훅에 stdin 12케이스를 직접 주입해 12/12 설계대로 동작함을 확인하고 **CLOSED** 판정했다).

상태 확인은 언제나 **실측**으로 한다 — `scripts/install_hooks.sh --check`.
선언을 믿지 마라. 훅은 `.git/` 안에 있고 `.git/` 은 추적되지 않는다.

> **잔여 위험 (`prepush-hook-symlink-depends-on-control-worktree-lifetime`).**
> 심링크 대상이 **이 control 워크트리 안**이다. 워크트리를 삭제·이동하면 심링크가 끊기고
> git 은 **오류 없이 훅을 건너뛴다** — 신뢰경계가 조용히 사라진다.
> control 워크트리를 정리하기 전에 `install_hooks.sh --check` 를 먼저 돌려라.
>
> **탐지는 붙었다 (V2-C004).** `promote_landing_main.sh` 의 **첫 검사** `[HOOK_INSTALL]` 이
> 훅 정본 존재 · 심링크 유효(dangling 아님) · 실행권한 · 정본과의 내용 동일을 확인하고
> 하나라도 아니면 승격을 차단한다. 우회 옵션은 없다.
> 설치 **방식**(심링크)은 그대로 둔다 — adversarial V2-C003 §2.3 이 `core.hooksPath` 는
> 수명 의존이 같으면서 다른 훅을 전부 무효화하고 복사 모드는 drift 한다고 실측 판정했다.
> 수명 의존 자체는 남으므로 이 부채는 계속 OPEN 이다. 탐지가 붙었을 뿐 원인은 그대로다.

**승격 검사는 번호가 아니라 이름으로 부른다** (ssot V2-C003
`control-state-and-promote-header-mislabel-verify-check-number`).
검사를 하나 삽입하면 뒤 번호가 전부 밀리고, 그때마다 문서·state 의 번호 서술이 어긋난다.
현재 순서: `[HOOK_INSTALL]` → `[SHA_RESOLVE]` → `[PILOT_IMMUTABLE]` → `[AUDIT_ANCESTRY]`
→ `[EXEC_TREE]` → `[ORCH_TREE]` → `[INSTALL_INTEGRITY]` → `[BLOCKING_DEBT]` → `[AUDIT_VERDICT]`.

> **원장은 커밋본에서만 읽는다 (V2-C004).** `[ORCH_TREE]` 가 이 control 워크트리의 dirty 를
> 검사하고, `control/state.json` 을 `git show <control HEAD>:…` 로 읽어 워킹트리 사본과
> 바이트 대조한다. 커밋하지 않은 `state.json` 편집으로는 `open_blocking_total` 을 0 으로
> 만들 수 없다 (adversarial V2-C003 `promotion-reads-uncommitted-state-json-with-no-second-source`).
> 감사 SHA 도 `audit_lag.latest_*_audit_sha` 에 핀 고정된다 — 인자로 넘긴 SHA 가 원장 기록과
> 다르면 차단이다.

**설치·변경은 오케스트레이터가 직접 수행한다** — 서브에이전트는 `.git/hooks/` 를 건드리지 않는다.

---

## 6. 부채 원장

`control/state.json`:

- `debt_ledger` / `open_p2` — v1 원장 (total 24 / open 21 / E001_BLOCKING 6). **삭제하지 않는다.**
- `v2_transition.debt_inheritance` — 위 open 21건의 v2 phase 재매핑. 근거 없이 닫지 않는다.
- `v2_transition.v2_audit_findings` — v2 감사 사이클별 등재.
  V2-C001 (adversarial 7 / ssot 13, 현재 CLOSED 18 / OPEN 2) ·
  V2-C002 (adversarial 8 / ssot 4, 현재 CLOSED 9 / OPEN 3) ·
  V2-C003 (adversarial 8 / ssot 5, 전건 OPEN) · 오케스트레이터 등재 2건.
  **감사가 확인하기 전에는 닫지 않는다.**
- `v2_transition.open_blocking_total` — `00_SSOT_v2.0.md §15` 의 `open blocking = 0` 판정에 쓰는 값.

Root `/home/sieg/projects-wsl/ProjectFinal/CLAUDE.md` 의 환경규칙(venv·경로·워크트리)은 그대로 상속한다.
