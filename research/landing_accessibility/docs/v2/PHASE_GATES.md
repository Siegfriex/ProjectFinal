# PHASE GATES — Landing Accessibility v2

**지위** 권위문서. `EXECUTION_AUTHORITY.md` 권위서열에 편입된다.
**닫는 결함** `phase-gate-names-only-in-nonauthoritative-bootstrap` (ssot V2-C001 / P1 / blocking)

> 구체화 대상: `03_CRISP_DM_EXECUTION_PLAN_v2.0.md` 실행 Phase Gate / `00_SSOT_v2.0.md` §15
>
> 이 문서가 `00_SSOT_v2.0.md`와 충돌하면 SSOT가 우선하고, 충돌이 발견되면 그것은 이 문서의 결함이다.

---

## 0. 왜 이 문서가 필요한가

`03_CRISP_DM_EXECUTION_PLAN_v2.0.md`는 실행 Phase(`P0`, `P-A` … `P-I`)를 정의하지만
**Gate 이름을 정의하지 않는다.** `00_SSOT_v2.0.md` §15는 `READY_FOR_E001_V2` 하나만 정의한다.

나머지 Gate 이름은 `docs/v2/bootstrap/07_CLAUDE_FIRST_SESSION_PROMPT_v2.0.md`에만 존재했고,
그 파일은 `NON_AUTHORITATIVE_BOOTSTRAP_RECORD`라 **실행규칙 근거로 인용할 수 없다.**
지금 닫아야 할 `V2_SSOT_FROZEN`조차 그 상태였다.

이 문서가 Gate 이름과 통과조건의 **정본**이다.

---

## 1. Gate 목록

| Gate | Phase | 상태 |
|---|---|---|
| `V2_SSOT_FROZEN` | P0 — V2 Refreeze | 미달성 |
| `ANALYSIS_AND_TASK_CODEBOOK_FROZEN` | P-A — Analysis Foundation + Task Codebook | 미착수 |
| `TARGET_TASK_FRAME_FROZEN` | P-B — Target / Task Frame | 미착수 |
| `L0_L1_ENGINE_READY` | P-C — L0/L1 Measurement Engine | 미착수 |
| `E000_V2_VALIDATED` | P-D — E000_V2 Smoke | 미착수 |
| `READY_FOR_E001_V2` | P-E — 정지점 | 미착수 |

`E000_V2_VALIDATED`는 `03`과 `00`이 P-D에 이름을 부여하지 않아 **본 문서가 부여한 운영 라벨**이다.
연구기준이 아니라 phase 종료를 가리키는 식별자다.

---

## 2. 공통 통과조건

모든 Gate는 다음을 **동시에** 충족해야 닫힌다.

| 조건 | 근거 |
|---|---|
| exec 산출물이 커밋되어 있다 | `05 §6` |
| adversarial 감사와 ssot 감사가 **exact same target SHA**를 감사했다 | `05 §6` |
| 두 감사 모두 verdict = PASS | `05 §6` |
| 해당 Gate의 blocking finding이 0건 | `00 §15` |
| orchestrator reconciliation이 current | `05 §10` |
| `unaudited_cycle_depth <= MAX_UNAUDITED_EXEC_CYCLES (=1)` | `05 §6` |
| Pilot(`research/refcohort/**`) diff = 0 | `05 §2`, `05 §6` |
| executor self-approval 없음 | `05 §6` |
| `E001_V2_STARTED = false` (P-E까지) | `00 §15`, `EXECUTION_AUTHORITY §1` |

**부채 승계 조건.** blocking 집계는 v2 신규 finding만이 아니라
`control/state.json`의 v1 `debt_ledger` 승계분을 **합산**한 값이어야 한다.
빈 원장으로 "blocking 0"을 선언하는 것은 게이트 위반이다.
(닫는 결함: `v1-open-debt-ledger-not-adopted-by-v2-authority` / adversarial / P1)

---

## 3. Gate별 고유 통과조건

### `V2_SSOT_FROZEN` — P0

| 항목 | 조건 |
|---|---|
| v2 docs 설치 | `docs/v2/00~05` + `README.md` + `MANIFEST.json` 설치, 원본 pack과 **바이트 동일** |
| 무결성 검증 | `scripts/verify_v2_docs.py` exit 0 |
| project context | `research/landing_accessibility/CLAUDE.md` 설치, v2만 current로 라우팅 |
| 권위 선언 | `docs/v2/EXECUTION_AUTHORITY.md` — CURRENT_SSOT / SCOPE / HUMAN_FINAL_REVIEW_MAX / v1 지위 / 기준선 SHA / `E001_V2_STARTED=false` |
| Gate 정의 | 본 문서가 권위서열에 편입 |
| v1 supersede **실효** | v1 실행지침을 담은 브랜치(`control/landing-orchestrator`)의 인계문서가 실제로 v2로 라우팅 |
| 승격 가드 실효 | 승격 스크립트의 워킹트리 clean 검사가 **실제 exec 워크트리**를 대상으로 함 |
| 부채 승계 | v1 `debt_ledger` open 항목이 v2 원장에 등재되고 phase 재매핑 완료 |
| 기능개발 없음 | 이 Gate까지 측정·수집 코드를 작성하지 않는다 |

### `ANALYSIS_AND_TASK_CODEBOOK_FROZEN` — P-A

| 항목 | 조건 |
|---|---|
| Mapping Layer | `01 §2` 논리표 ↔ `state/*.parquet` 대응 확립. **원본 rename/migrate 없음** |
| EDA-00 | Frame & Provenance Audit 완료 (`03` Phase 2) |
| EDA-01 | Wiseapp Source Structure 완료 |
| Functional Codebook | Business Domain과 Interaction Archetype **분리** 정의, archetype 7종 endpoint 명시 |
| Pilot Mapping | 10~15개 service를 **source context만** 보고 매핑. 인증·KWCAG outcome 차단 확인 |
| abstain 경로 | ambiguous가 강제분류되지 않고 abstain 가능함이 실증됨 |
| 동결 시점 | 매핑은 접근성 outcome·인증 여부를 보기 **전에** 동결 (`00 §6`) |

### `TARGET_TASK_FRAME_FROZEN` — P-B

| 항목 | 조건 |
|---|---|
| C013 salvage | `87a0464e`에서 **선택적** salvage만. 전체 merge 금지. salvage 결과 재감사 |
| web eligibility | 전건 판정, `NOT_ASSESSED` 잔여 0 또는 사유 기록 |
| official URL | 확정 + `url_evidence` + `url_confidence` |
| final web target | 동결 |
| representative task | Business Domain / Interaction Archetype / endpoint definition 확정 |
| certification join | `certified_current` 산출. 유효기간 + 대상범위 + 서비스 동일성 3요건 (`01 §8`) |
| v1 가정 재검토 | v1 scope-specific assumption 폐기 또는 명시적 재승인 |

### `L0_L1_ENGINE_READY` — P-C

| 항목 | 조건 |
|---|---|
| L0 collector | DOM·AX·CSS/geometry·screenshot·contrast·target size·accessible label·motion·modal/overlay·primary action visibility |
| probe 분리 | probe는 **판정하지 않고 raw feature만** 저장 (`02 §4`) |
| L1 | Scout → Path Freeze → Deterministic Replay 동작 |
| Depth | NED·IED·MPFED 산출. 경계 신호 정의됨 |
| episode | text input / scroll episode 계수 |
| popup/obstruction | candidate detector · spatial metrics · semantic class · dismissibility · primary action occlusion |
| AI review cascade | deterministic → semantic → reviewer A → reviewer B → arbiter → HUMAN_FINAL ≤5. 잔여는 UNDETERMINED |
| KWCAG subset | older-relevant + L0/L1 observable subset 동결. **33개 전수 자동화를 목표하지 않음.** threshold 무변경 |
| Pilot 재사용 | 기능 단위 selective port만. 파일 단위 import 금지 |

### `E000_V2_VALIDATED` — P-D

| 항목 | 조건 |
|---|---|
| 대상 | 8~12개 diverse target (`02 §14` 구성 충족) |
| 목적 | 결과가 아니라 **측정기와 evidence lineage 검증** |
| 실패주입 | observation id duplicate · manifest missing · evidence file swap · wrong URL · overwrite · symlink escape · AI disagreement · UNDETERMINED→PASS 시도 |
| 판정 | 모든 guard가 **실제로 차단**함을 확인 |
| 감사 | PASS 후 두 독립감사 |

### `READY_FOR_E001_V2` — P-E · **정지점**

`00 §15` 전항목에 더해 다음 SHA를 동결한다.

`TARGET_FRAME_SHA` · `TASK_CODEBOOK_SHA` · `PROTOCOL_SHA` · `COLLECTOR_SHA` · `PROBE_SHA` ·
`KWCAG_SUBSET_SHA` · `AI_REVIEW_RUBRIC_SHA` · `AUDIT_DATE`

필수:

```
open P0            = 0
blocking P1        = 0
blocking P2        = 0
audit lag          = 0
human queue policy = valid
E001_V2_STARTED    = false
```

선언:

```
READY_FOR_E001_V2
FULL_COLLECTION_STARTED = NO
```

**여기서 반드시 정지하고 Research Director의 GO / HOLD를 받는다.**
GO 없이 `P-F (E001_V2)`로 넘어가는 것은 `00 §15` 위반이다.

---

## 4. 판정 권한

| 역할 | 권한 |
|---|---|
| executor | Gate 통과를 **주장**할 수 있다. 스스로 닫을 수 없다 (`05 §6` executor self-approval 금지) |
| adversarial auditor | blocking finding으로 Gate를 **막을** 수 있다 |
| ssot auditor | 동일 |
| orchestrator | 두 감사 PASS + reconciliation 후 Gate를 **닫는다** |
| Research Director (사용자) | `READY_FOR_E001_V2` 이후 GO/HOLD. 연구범위 충돌·해결 불가 P0 |

Gate를 닫은 사이클은 `control/state.json`에 기록한다 (`05 §10`).
