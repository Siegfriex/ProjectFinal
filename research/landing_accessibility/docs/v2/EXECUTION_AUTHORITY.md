# EXECUTION AUTHORITY — Landing Accessibility v2

**선언일** 2026-08-26
**선언 주체** Main Orchestrator (P0 `V2_REFREEZE`)
**성격** 기계적 권위 선언. 이 파일과 `00_SSOT_v2.0.md`가 충돌하면 `00_SSOT_v2.0.md`가 우선한다.

---

## 1. 기계적 상태값

```
CURRENT_SSOT                    = research/landing_accessibility/docs/v2/00_SSOT_v2.0.md
SCOPE                           = L0_INITIAL_LANDING + L1_SHALLOW_REPRESENTATIVE_ENTRY
HUMAN_FINAL_REVIEW_MAX          = 5
V1_ANALYSIS_SSOT                = SUPERSEDED_FOR_EXECUTION / PRESERVED_FOR_HISTORY
PHASE_EXECUTION_DIRECTIVE_v5.0  = SUPERSEDED_FOR_SCOPE / OPERATIONAL_GUARDS_INHERITED
PILOT                           = READ_ONLY
E001_V2_STARTED                 = false
```

---

## 2. 권위 서열

| 순위 | 문서 | 지위 |
|---|---|---|
| 1 | `docs/v2/00_SSOT_v2.0.md` | 목표·범위·단위·해석의 최상위 권위 |
| 2 | `docs/v2/01_DATA_SPEC_v2.0.md` | 데이터 표·변수 정의 |
| 3 | `docs/v2/02_COLLECTION_MEASUREMENT_SPEC_v2.0.md` | 수집·측정·정지조건 |
| 4 | `docs/v2/03_CRISP_DM_EXECUTION_PLAN_v2.0.md` | 분석 단계·Phase Gate |
| 5 | `docs/v2/04_GLOSSARY_v2.0.md` | 용어 정의 |
| 6 | `docs/v2/05_REPO_ORCHESTRATION_PLAN_v2.0.md` | Git·branch·worktree·감사 운영 |
| — | `research/landing_accessibility/CLAUDE.md` | 위 6종의 프로젝트 컨텍스트 요약. 원본과 충돌 시 원본 우선 |

하위 문서가 `00_SSOT_v2.0.md`와 충돌하면 SSOT가 우선한다.

### 비권위 자료

| 파일 | 지위 |
|---|---|
| `docs/v2/README.md` | 읽기 순서 안내. 실행권위 아님 |
| `docs/v2/MANIFEST.json` | 원본 docs pack의 바이트·sha256 기록 |
| `docs/v2/bootstrap/07_CLAUDE_FIRST_SESSION_PROMPT_v2.0.md` | `NON_AUTHORITATIVE_BOOTSTRAP_RECORD`. 이 세션의 부트스트랩 이력 보존용이며 실행규칙 근거로 인용하지 않는다 |

---

## 3. v1 자산의 지위

v1 문서와 Pilot은 **삭제하지도, 이동하지도 않는다.** 이력·회귀검증·근거 참조용으로 보존한다.

| 자산 | 위치 | 지위 |
|---|---|---|
| `ProjectFinal_Landing_Accessibility_Data_Analysis_SSOT_v1.0.md` | `control/landing-orchestrator` 브랜치 `control/handoff/preserved/` | `SUPERSEDED_FOR_EXECUTION` / `PRESERVED_FOR_HISTORY` |
| `docs/PHASE_EXECUTION_DIRECTIVE_v5.0.md` | `control/landing-orchestrator` 브랜치 | `SUPERSEDED_FOR_SCOPE` / `OPERATIONAL_GUARDS_INHERITED` |
| `docs/00_AUTHORITY_AND_DECISIONS.md` … `docs/06_ELIGIBILITY_AND_JOIN_RULES.md` | `control/landing-orchestrator` 브랜치 | 사실·계보 참조 가능. 실행범위 근거로는 인용 금지 |
| `docs/HANDOFF_PRE_ANALYSIS_START.md`, `docs/NEXT_SESSION_ENTRYPOINT.md` | `control/landing-orchestrator` 브랜치 | 역사적 인계문서. 검증된 사실(SHA·카운트)은 유효, 실행범위는 v2가 supersede |
| `docs/07_EVIDENCE_MANIFEST_CONTRACT.md` | 본 브랜치 `research/landing_accessibility/docs/` | **현행 유효.** evidence identity 계약은 v2에 그대로 상속 |
| `research/refcohort/**` (Pilot) | `research/refcohort-r1` @ `32460b8` | `READ_ONLY`. 수정 시 P0 |

### SUPERSEDED_FOR_SCOPE / OPERATIONAL_GUARDS_INHERITED 의 의미

`PHASE_EXECUTION_DIRECTIVE_v5.0`의 **실행범위**(`LANDING_ONLY`)는 무효다. v2 SCOPE가 대체한다.

반면 다음 **운영 가드는 그대로 상속**한다.

- `MAX_UNAUDITED_EXEC_CYCLES = 1`
- executor self-approval 금지
- 두 독립감사가 **exact same target SHA**를 감사해야 promotion
- Pilot 수정 = P0
- main 직접 push 금지 (승격 스크립트 경유만)
- UNDETERMINED laundering 금지
- 본수집 전 evidence 생성 = gate 위반

---

## 4. 기준선

| 역할 | ref | SHA |
|---|---|---|
| authoritative main (유일한 분석 입력) | `research/landing-accessibility-main` | `5a9015d1e95b15304aaf53a73efb475934610b82` |
| v2 executor | `agent/landing-v2-exec` | 본 커밋 |
| old C013 WIP | `agent/landing-exec` | `87a0464e8159d5526069d5e654e648b0dae506ca` — `UNVERIFIED` / 분석입력 금지 / 삭제 금지 / selective salvage 후 재감사 |
| Pilot | `research/refcohort-r1` | `32460b87334a67f6a74823ac55f85ca80a9f8980` — `READ_ONLY` |
| adversarial audit | `audit/landing-adversarial` | `510d5f21a4de3d6420a3e41eeb44972e5973c5ac` |
| ssot audit | `audit/landing-ssot` | `1bc2c71b2c48f060609fb458e2dd169086f59111` |
| orchestrator | `control/landing-orchestrator` | `bfa16624e55e15c4626e74547ed885156a8f2a9e` |

> **주의.** 이 저장소의 `origin/main`(`a835d5d8`)은 저장소 부트스트랩 브랜치이며 이 연구의
> authoritative main이 **아니다.** "main promotion"은 `research/landing-accessibility-main`
> 으로의 승격을 뜻한다.

---

## 5. 정지점

본수집(`E001_V2`) 직전 `READY_FOR_E001_V2`에서 반드시 정지하고 Research Director의 GO/HOLD를 받는다.

```
E001_V2_STARTED         = false
FULL_COLLECTION_STARTED = NO
```

---

## 6. 무결성 검증

```bash
python research/landing_accessibility/scripts/verify_v2_docs.py
```

설치본의 sha256이 `docs/v2/INSTALL_MANIFEST.json`과 일치하는지, 그리고 원본 docs pack
`MANIFEST.json`과 동일 바이트인지 검증한다.
