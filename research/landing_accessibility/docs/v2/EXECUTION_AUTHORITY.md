# EXECUTION AUTHORITY — Landing Accessibility v2

**선언일** 2026-08-26
**선언 주체** Main Orchestrator (P0 `V2_REFREEZE`)
**최근 개정** V2-C003 — 두 독립감사(V2-C002)의 blocking finding 시정 반영
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
FULL_COLLECTION_STARTED         = NO
CURRENT_GATE                    = V2_SSOT_FROZEN (미달성)
```

---

## 2. 권위 서열

| 순위 | 문서 | 지위 |
|---|---|---|
| 1 | `docs/v2/00_SSOT_v2.0.md` | 목표·범위·단위·해석의 최상위 권위 |
| 2 | `docs/v2/01_DATA_SPEC_v2.0.md` | 데이터 표·변수 정의 |
| 3 | `docs/v2/02_COLLECTION_MEASUREMENT_SPEC_v2.0.md` | 수집·측정·정지조건 |
| 4 | `docs/v2/03_CRISP_DM_EXECUTION_PLAN_v2.0.md` | 분석 단계·Phase |
| 5 | `docs/v2/04_GLOSSARY_v2.0.md` | 용어 정의 |
| 6 | `docs/v2/05_REPO_ORCHESTRATION_PLAN_v2.0.md` | Git·branch·worktree·감사 운영 |
| 7 | `docs/v2/PHASE_GATES.md` | **Gate 이름·통과조건·판정권한의 정본** |
| 8 | `docs/v2/A1_MEASUREMENT_OPERATIONALIZATION.md` | 측정 조작화 보충명세 |
| 9 | `docs/v2/A2_VOCABULARY_AND_SCHEMA_BINDING.md` | 상태값 어휘·논리↔물리 스키마 대응 보충명세 |
| 10 | `docs/07_EVIDENCE_MANIFEST_CONTRACT.md` | evidence identity / manifest 계약. **v1 산물이나 현행 유효**, v2 `02 §11~§12`와 모순 없음이 감사로 확인됨 |
| — | `research/landing_accessibility/CLAUDE.md` | `PROJECT_CONTEXT_DERIVED`. 위 문서들의 요약. 충돌 시 원본 우선 |

### 보충명세(A1/A2)의 성격

`A1`·`A2`는 **새 연구기준을 만들지 않는다.** `00_SSOT`가 이미 정의한 변수의 산출 절차와
허용값만 부여한다. 두 문서가 `00_SSOT`와 충돌하면 SSOT가 우선하며, 그 충돌은 보충명세의 결함이다.

원본 docs pack(`00~05`)의 **바이트는 수정하지 않는다.** 명세 공백은 원본 개변이 아니라
보충명세 추가로 메운다. 원본 바이트 동일성이 설치 무결성 검증의 앵커이기 때문이다.

### 비권위 자료

| 파일 | 지위 |
|---|---|
| `docs/v2/README.md` | `NON_AUTHORITATIVE_READING_GUIDE`. 읽기 순서의 정본은 `docs/INDEX.md` |
| `docs/v2/MANIFEST.json` | 원본 docs pack의 바이트·sha256 기록 |
| `docs/v2/INSTALL_MANIFEST.json` | 설치본 sha256·본문 sha256·앵커 종류 기록 |
| `docs/v2/bootstrap/07_CLAUDE_FIRST_SESSION_PROMPT_v2.0.md` | `NON_AUTHORITATIVE_BOOTSTRAP_RECORD`. 실행규칙 근거로 인용 금지 |

**배너 정책.** 비권위 파일과 `CLAUDE.md`의 설치본 상단에는
`INSTALLED-BANNER-START/END` 로 감싼 배너가 삽입돼 있다. 배너를 걷어낸 본문은 원본 pack과
바이트 동일해야 하며 `scripts/verify_v2_docs.py`가 이를 검증한다. 권위문서 `00~05`에는
배너를 넣지 않는다.

---

## 3. v1 자산의 지위

v1 문서와 Pilot은 **삭제하지도, 이동하지도 않는다.** 이력·회귀검증·근거 참조용으로 보존한다.

| 자산 | 위치 | 지위 |
|---|---|---|
| `ProjectFinal_..._Data_Analysis_SSOT_v1.0.md` | `control/landing-orchestrator` 브랜치 `control/handoff/preserved/` | `SUPERSEDED_FOR_EXECUTION` / `PRESERVED_FOR_HISTORY` |
| `docs/PHASE_EXECUTION_DIRECTIVE_v5.0.md` | `control/landing-orchestrator` 브랜치 | `SUPERSEDED_FOR_SCOPE` / `OPERATIONAL_GUARDS_INHERITED` |
| `docs/00_AUTHORITY_AND_DECISIONS.md` … `docs/06_ELIGIBILITY_AND_JOIN_RULES.md` | `control/landing-orchestrator` 브랜치 | 사실·계보 참조 가능. 실행범위 근거로는 인용 금지 |
| `docs/HANDOFF_PRE_ANALYSIS_START.md`, `docs/NEXT_SESSION_ENTRYPOINT.md` | `control/landing-orchestrator` 브랜치 | 역사적 인계문서. 검증된 사실(SHA·카운트)은 유효, 실행범위는 v2가 supersede |
| `docs/07_EVIDENCE_MANIFEST_CONTRACT.md` | 본 브랜치 | **현행 유효** (권위서열 10위) |
| `research/refcohort/**` (Pilot) | `research/refcohort-r1` @ `32460b8` | `READ_ONLY`. 수정 시 P0 |

### supersede는 선언만으로 성립하지 않는다

`SUPERSEDED_*` 표기는 **다른 브랜치의 파일을 자동으로 무력화하지 못한다.**
v1 실행지침을 담은 브랜치의 인계문서가 실제로 v2로 라우팅하도록 **그 브랜치에서 갱신**해야
supersede가 실효를 갖는다. 이 조건은 `PHASE_GATES.md` `V2_SSOT_FROZEN`의 통과조건이다.

(닫는 결함: `orchestrator-entrypoint-still-routes-to-v1-scope` / adversarial V2-C001 / P1)

### `SUPERSEDED_FOR_SCOPE / OPERATIONAL_GUARDS_INHERITED` 의 의미

`PHASE_EXECUTION_DIRECTIVE_v5.0`의 **실행범위**(`LANDING_ONLY`)는 무효다. v2 SCOPE가 대체한다.

반면 다음 **운영 가드는 그대로 상속**한다.

- `MAX_UNAUDITED_EXEC_CYCLES = 1`
- executor self-approval 금지
- 두 독립감사가 **exact same target SHA**를 감사해야 promotion
- Pilot 수정 = P0
- main 직접 push 금지 (승격 스크립트 경유만)
- UNDETERMINED laundering 금지
- 본수집 전 evidence 생성 = gate 위반

상속된 가드는 **문장이 아니라 실행 경로로 강제되어야 한다.** 승격 스크립트의 검사가
대상을 잘못 지목해 vacuous해지면 그것은 가드가 없는 것과 같다.

(닫는 결함: `promotion-clean-check-targets-wrong-worktree` / adversarial V2-C001 / P1)

---

## 4. 부채 승계

v1의 미결 부채는 **v2로 그대로 승계된다.** v2 원장을 빈 상태에서 시작하지 않는다.

| 출처 | 원장 |
|---|---|
| v1 | `control/state.json` → `debt_ledger` (total 24 / closed_pending_audit 3 / **open 21**, 그중 E001-blocking 6) |
| v2 | `control/state.json` → `v2_transition.v2_audit_findings` (V2-C001 두 감사의 finding) |

`00_SSOT §15`와 `PHASE_GATES.md`가 요구하는 `open blocking = 0` 판정은
**두 원장의 합계**로 계산한다. v1 원장을 무시하고 0을 선언하는 것은 게이트 위반이다.

v1 부채 항목의 phase 스케줄(C013·P-B·P-D 등 v1 phase 이름)은 v2 phase(P-A~P-E)로
재매핑되며, 근거 없이 닫지 않는다. 기본값은 open 유지다.

(닫는 결함: `v1-open-debt-ledger-not-adopted-by-v2-authority` / adversarial V2-C001 / P1)

---

## 5. 기준선

| 역할 | ref | SHA |
|---|---|---|
| authoritative main (유일한 분석 입력) | `research/landing-accessibility-main` | `5a9015d1e95b15304aaf53a73efb475934610b82` |
| v2 executor | `agent/landing-v2-exec` | 본 커밋 |
| old C013 WIP | `agent/landing-exec` | `87a0464e8159d5526069d5e654e648b0dae506ca` — `UNVERIFIED` / 분석입력 금지 / 삭제 금지 / selective salvage 후 재감사 |
| Pilot | `research/refcohort-r1` | `32460b87334a67f6a74823ac55f85ca80a9f8980` — `READ_ONLY` |
| adversarial audit | `audit/landing-adversarial` | V2-C002 @ `2a28ad3dae5eb385b0af373cfc950ed86468c91d` |
| ssot audit | `audit/landing-ssot` | V2-C002 @ `eb7e4e13a2075b7390d16d545b92f04d549381f1` |
| orchestrator | `control/landing-orchestrator` | `bfa16624e55e15c4626e74547ed885156a8f2a9e` 이후 V2-C002 |

> **주의.** 이 저장소의 `origin/main`(`a835d5d8`)은 저장소 부트스트랩 브랜치이며 이 연구의
> authoritative main이 **아니다.** "main promotion"은 `research/landing-accessibility-main`
> 으로의 승격을 뜻한다. (ssot V2-C001이 사실 확인)

---

## 6. 감사 이력

| 사이클 | target SHA | adversarial | ssot | 결과 |
|---|---|---|---|---|
| V2-C001 | `eb36d173182a582e8d7499f29170a83363f9d560` | FAIL — P0 0 / P1 3 / P2 4 | FAIL — P0 0 / P1 2 / P2 11 | 승격 차단, 시정 사이클 V2-C002 개시 |
| V2-C002 | `6fad79fa98e1ec7d315122d79794b4d5442bb42e` | FAIL — P0 0 / P1 1 / P2 7 | FAIL — P0 0 / P1 0 / P2 4 | V2-C001 blocking 14건 **전건 CLOSED**. 신규 blocking 은 표기 수정 계열 + UNDETERMINED laundering 1건. 시정 사이클 V2-C003 개시 |

두 감사가 **동일 target SHA**를 감사했음이 확인됐다.
문서 pack 내용 자체(scope creep · depth의 KWCAG 전환 · 인증 gold truth화 · human≤5 강제분류 ·
C013 혼입 · Pilot write · root CLAUDE.md · 설치 바이트 무결성 · 기준선 SHA · CRISP-DM 정합)는
양 감사에서 PASS했다. blocking은 전부 **선언과 강제수단 사이의 간극** 및 **명세 공백**이었다.

---

## 7. 정지점

본수집(`E001_V2`) 직전 `READY_FOR_E001_V2`에서 반드시 정지하고 Research Director의 GO/HOLD를 받는다.

통과조건 전문은 `PHASE_GATES.md` §3.

---

## 8. 무결성 검증

```bash
python research/landing_accessibility/scripts/verify_v2_docs.py
```

세 층을 검증한다.

1. pack 파생 파일 — 배너 제외 본문이 원본 `MANIFEST.json`과 바이트 동일
2. 저장소 저작 권위문서 — 외부 앵커가 없으므로 **git을 앵커로** 사용 (추적 중 + 워킹트리 clean)
3. 커버리지 — `docs/v2/` 아래 전 `.md`/`.json`이 `INSTALL_MANIFEST.json`에 등재

이 스크립트는 `PHASE_GATES.md` `V2_SSOT_FROZEN` 통과조건이며,
`control/landing-orchestrator` 의 `scripts/promote_landing_main.sh` **검사 4**가 exec 워크트리에서
실제로 실행한다. exit != 0 이면 승격이 차단되고, 스크립트가 없어도 차단된다.

> V2-C002 두 감사가 이 문장의 이전 판본(`승격 경로에서 호출된다`)을 **거짓 주장**으로 지적했다
> (`git grep verify_v2_docs` = 0건). V2-C003에서 실제 호출을 만들어 문장을 참으로 만들었다.
> 닫는 결함: `verify-script-declared-in-promotion-path-but-never-called` ·
> `execution-authority-overclaims-verify-script-invocation`

(닫는 결함: `install-manifest-is-self-anchored` · `install-integrity-coverage-gap`)
