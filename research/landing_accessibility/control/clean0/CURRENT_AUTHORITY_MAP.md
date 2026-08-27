# CURRENT_AUTHORITY_MAP — CLEAN-0

**ID** `LA-AUTHMAP-2.1-20260827T2043`
**발행** Claude A (Authority Plane)
**상태** `CLEAN0_ARTIFACT`
**기준 시각** 2026-08-27 20:43 KST

> 이 문서는 **무엇이 지금 권위인지**만 고정한다. 새 분석도 새 판정도 하지 않는다.
> 삭제하지 않는다 — superseded 는 지위 표기이지 제거가 아니다.

---

## §1 단일 SSOT 선언 — DECISION

```
DECISION  D-A-2.1-001
SSOTV2/ 11개 문서팩이 이 연구의 단일 SSOT다.
설치 정본 = research/landing_accessibility/docs/v2_1/  (control/landing-orchestrator)
원본 SSOTV2/ 는 primary worktree 의 입력 사본이며, 권위 정본은 설치본이다.
```

설치본 sha256 은 `V2_1_PACK_HASHES.txt` 에 기재한다. 문서가 바뀌면 해시가 바뀌고,
해시가 바뀌면 그것은 새 SSOT 개정이며 `SUPERSEDE` 티켓 없이 발생할 수 없다.

**상태**: `PROPOSED_CURRENT_AUTHORITY_AFTER_CLEAN0` → CLEAN-0 종료 시 `CURRENT_AUTHORITY`.

---

## §2 권위 계층 — 무엇이 무엇을 이긴다

`03_ABC_ORCHESTRATION_PROTOCOL_v2.1.md §5` 를 그대로 승계한다.

| 층 | 내용 | 이 연구에서의 실체 |
|---|---|---|
| **T1** | exact byte / runtime evidence | E001 evidence 66 디렉터리, exact SHA 의 코드, BATCH_CHAIN.jsonl |
| **T2** | 독립 재현 계산 | C 가 같은 raw 에서 재계산한 값 |
| **T3** | frozen definition / codebook / schema | task definition CSV 59/59, OLDER_RELEVANT_KWCAG_SUBSET, mart schema |
| **T4** | current SSOT / accepted decision | docs/v2_1/ 설치본 + A decision log |
| **T5** | prose docs / docstring | README, 주석 — **근거가 될 수 있으나 사실을 만들지 않는다** |
| **T6** | agent narrative | 보고문·추론 |

**A 의 권위는 T4 이다.** T1~T3 을 선언으로 덮지 않는다.

이 규칙이 실제로 결함을 잡은 사례(인계 §C, T5 가 T1 에 졌다):
`default_task_definition()` docstring 이 *"codebook 없이 endpoint 를 만들어내지 않는다"* 라고
적었으나, 원천 CSV 에 정의가 **59/59 존재**했다 → docstring 이 stale 이었고 실체는 **wiring 갭**이었다.

---

## §3 CURRENT AUTHORITY — 지금 권위인 것

| 영역 | 정본 | exact SHA | 지위 |
|---|---|---|---|
| **연구 SSOT** | `docs/v2_1/00~09 + README` | 설치 대상 = control 브랜치 (본 커밋) | `CURRENT_AUTHORITY_CANDIDATE` |
| **대표기능 DT** | `docs/v2_1/01_...DT_v2.1.md` | 동상 | `CURRENT` |
| **오케스트레이션 규약** | `docs/v2_1/03_...PROTOCOL_v2.1.md` | 동상 | `CURRENT` |
| **티켓 스키마** | `docs/v2_1/07_...SCHEMA_v2.1.json` | 동상 | `CURRENT` |
| **A 인계** | `control/SESSION_HANDOFF_A_20260827.md` | `7c8facebe95ec3793756a82d809be37ca17b6b6e` | `CURRENT_HANDOFF` — §D~§H 유효 |
| **A control plane** | `control/**` | `084eff541836c2e16418b96bd230c1d58bcda663` | `CURRENT_BASE` (본 CLEAN-0 의 base) |
| **canonical 산출물** | `artifacts/e001_real_marts/` | `82f631f1e6bd3708bc8f95f0b8edcd90e22cef0d` | `FINAL_ACCEPTED (PILOT/PRELIMINARY)` — 대체 아님, 층이 얹힌다 |
| **R0 입력 감사** | `handoff/RECOVERY_DATAFLOW_AUDIT.md` | `2281c853950d0c475c5d2c1678680b971c2804f4` | `R0_INPUT — C 독립검증 대기` |
| **C assurance** | `assurance/` | `1baa865b4a673af05033e6e6289fd2713676baa5` | `CURRENT_ASSURANCE_BASE` |
| **연구 코드베이스** | `research/landing_accessibility/src` 등 | `bc0b7a087faf2328cbafdfa9b40bd426c5080d7d` | `AUTHORITATIVE_LANDING_MAIN` |
| **KWCAG frozen subset** | `control/OLDER_RELEVANT_KWCAG_SUBSET.md` | 084eff5 내 | `FROZEN — 연구 중 확대 금지 (D-13)` |
| **분석 계약** | `control/ANALYSIS_CONTRACT.md` + `AMENDMENT_1` | 084eff5 내 | `CURRENT — 계약은 유효하고, 그 계약이 지정한 분석이 계산 불가라는 것이 오늘의 산출물이다` |

---

## §4 READ-ONLY — 건드리지 않는 것

| 대상 | 지위 |
|---|---|
| **ORIGINAL_E001** (evidence 66 디렉터리 + mart 56행 + 판정) | `READ_ONLY` — 별도 선언문 참조 |
| `control/FINAL_CORRECTION_RECORD.md` | `IMMUTABLE_RECORD` |
| `control/AXIS_A_NOT_EVALUATED.md` | `IMMUTABLE_RECORD` |
| `control/AXIS_C_VERIFIED_RESULT.md` | `IMMUTABLE_RECORD` |
| bus tickets / completions (기존 5+6건) | `APPEND_ONLY` — 수정하지 않고 새 티켓으로 정정 |

---

## §5 SUPERSEDED — 지위는 내려가되 삭제하지 않는다

| 문서 | 승계자 | 사유 |
|---|---|---|
| `docs/v2/` 전체 (v2 문서군) | `docs/v2_1/` | v2.1 §1: 연구질문·3축·NED/IED/MPFED·evidence lineage 는 **승계**, 아래 항목만 v2.1 이 우선 |
| `control/TIMEBOX_1630_EXECUTION_SSOT.md` | — | 타임박스는 종료됨. **measurement semantics 를 override 하지 않았다**는 기록으로만 보존 |
| `control/POST_E001_MEASUREMENT_RECOVERY_PLAN.md` (개정1·2) | `docs/v2_1/02_MEASUREMENT_RECOVERY_ROADMAP_v2.1.md` | 로드맵이 v2.1 로 재발행. **단 라벨러 전용워커·라벨해시동결·모집단 56 결정은 그대로 살아 있다** |
| `E001_LAUNCH.md` (repo root, untracked) | — | E001 실행 문서. 실행 종료 → `HISTORICAL` |
| `docs/_invalidated/`, `state/_invalidated/` | — | 이미 무효화 표기됨. 그대로 둔다 |

**v2.1 이 v2 를 이기는 지점** (00 §1 재확인): E001 이후 현재상태 / ORIGINAL_E001 지위 /
대표기능 매핑 운영절차 / guard 입도 / task wiring / 실웹 detector / KWCAG production evaluator /
A·B·C 규약 / CLEAN-0·recovery gate. **그 외에는 v2 가 여전히 유효하다.**

---

## §6 권위가 아닌 것 — 명시

```
branch name                      권위 아님 (TRAP-01/02 참조)
로컬 refs/remotes 패턴 조회      권위 아님 (git ref 는 경로 컴포넌트 경계로 매칭)
docstring / 주석                 T5
agent 보고문                     T6
.agent_bus/ 내용                 orchestration transport — canonical 아님 (기존 결정, §7)
"로컬에 있다" 는 문장            인계 아님 — hash manifest 필요
```

---

## §7 미해결 — R0 에서 A 가 결정할 것

`ISSUE-A-001` **bus 가 Git 밖이다.**
`.gitignore` 마지막 줄이 `.agent_bus/` 를 제외한다. 사유는 명시돼 있다 —
*"orchestration transport, not research authority"*. 이 결정 자체는 유지 가능하다.
그러나 `03_...PROTOCOL §16 투명성 목표`는 **GitHub 만 보고 현재 phase / 열린 blocker /
누구에게 간 티켓**을 알 수 있어야 한다고 요구한다. 둘은 지금 충돌한다.

- **선택지 A**: bus 를 Git 에 편입 → transport 노이즈가 연구 이력에 섞인다
- **선택지 B (A 권고)**: bus 는 로컬 유지 + A 가 `control/clean0/PHASE_STATE.json` 과
  `BLOCKER_LEDGER` 를 Git 에 미러링 → §16 은 control plane 이 충족한다

이 선택은 **R0 티켓에서 DECISION 으로 확정한다.** CLEAN-0 에서는 관측만 등재한다.
