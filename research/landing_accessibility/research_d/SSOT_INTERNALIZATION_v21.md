# SSOT 내재화 기록 — SSOTV2 단일 권위 고정

**작성**: D (Independent Research Sandbox)
**claim_kind**: OBSERVATION (해시·SHA 부분) + DECISION (권위 고정 부분)
**입력 스냅샷**: `INPUT_SNAPSHOT_v21.json`

---

## 1. 단일 SSOT 선언

`/home/sieg/projects-wsl/ProjectFinal/SSOTV2` 의 11개 문서를 **이 세션의 유일한 SSOT**로
고정한다. 이전 `SSOT/` 디렉터리, v2 문서, 각종 handoff 문서는 **참조 이력**이며
현재 연구계약이 아니다. 충돌 시 SSOTV2가 이긴다 — 단, §5의 truth hierarchy 안에서.

### 동결 해시 (SHA256)

| 파일 | SHA256 |
|---|---|
| `00_SSOT_v2.1_POST_PILOT_RECOVERY.md` | `1a4f6e75ccf70b2eaeddcad43c27c2cb5b3c93db1520760aa1850c63524a4ea3` |
| `01_REPRESENTATIVE_FUNCTION_MAPPING_DT_v2.1.md` | `191ee182219e96398a11283bdb49b5b37a3d9e1acd5aa2d55d85946a346b37e8` |
| `02_MEASUREMENT_RECOVERY_ROADMAP_v2.1.md` | `e9ebea51fbb809bd1c9b8308e966bf30320fd9de16d899dd283a269814df7823` |
| `03_ABC_ORCHESTRATION_PROTOCOL_v2.1.md` | `3a36268068e33abc881443e1d9f606bfba6471aca5f081b2cc42d8822da75b9c` |
| `04_PROMPT_A_INITIAL.md` | `6fdd0c0c83e1d31422455317fb11ad0203c05f3e022c2f7f0a76858c246e9dd9` |
| `05_PROMPT_B_INITIAL.md` | `a770533b52ace9c1f3c546e5fd4aea8c250c04b5d3208ebf0a96e09364211cd3` |
| `06_PROMPT_C_FABLE_INITIAL.md` | `9830be9945775523a379cdbf21a33bce058b7ca7bcdd42f199120684559b3dec` |
| `07_TICKET_PROTOCOL_SCHEMA_v2.1.json` | `a25c9f7c9fae781cc959601c26fe47051b0d233fc072c94a8c178c32178c4ac2` |
| `08_CURRENT_STATE_BASELINE_v2.1.md` | `fed4010c2aba8f8288776498fbca12e973ceb76eac8accc7892cf8407d5dae78` |
| `09_DECISION_LOG_SEED_v2.1.md` | `c83cc2341b242b6b081336eaac1caa89c5c67cacc7212d322d85fa304beb5196` |
| `README.md` | `6043a3a184bb37225a846ee382efb1c3d5fe9e88f9a1ac40778b400ecff899c6` |

---

## 2. D가 구속되는 핵심 조항

### 연구 정체성 (00 §0)
범용 접근성 자동감사 제품·범용 browser agent를 만드는 프로젝트가 **아니다**.
D의 연구는 이 범위를 넓혀 범용 제품 개발로 변질시키지 않는다.

### 세 독립 측정축 (00 §3) — 합산 금지 (D-15)
- **A**: KWCAG older-relevant PASS/FAIL/UNDETERMINED/NA. UNDETERMINED 세탁 금지.
- **B**: NED / IED / MPFED = NED+IED. endpoint 미도달이어도 region 관측되면 **NED는 보존**.
  scroll·타이핑·redirect·passive wait·popup dismissal은 depth에 합산하지 않음.
  `ExcessDepth = MPFED − same-archetype median(MPFED)`. 절대 임계(3 click=bad) 금지.
- **C**: OverlayCoverage, PrimaryActionOcclusion, scroll lock, dismiss control, forced dismissal.

Depth 비교 기준은 business domain이 아니라 **interaction archetype**이다.

### 7개 frozen archetype (00 §4)
QUERY · CONTENT_OPEN · ITEM_DETAIL · PLACE_LOOKUP · COMMUNICATION_ENTRY ·
FINANCIAL_ACTION_ENTRY · UTILITY_ENTRY. 이 밖의 label 생성 금지.

### DEFINITION ≠ OBSERVATION (00 §6.3)
`endpoint_definition exists`(연구계약 존재)와 `endpoint_observed`(실제 관측)를
**같은 필드·같은 문장에 담지 않는다**. 이 혼동을 laundering으로 보고 감시한다.

### Truth hierarchy (03 §5)
T1 exact byte/runtime evidence → T2 독립 재계산 → T3 frozen definition →
T4 SSOT/decision → T5 prose/docstring → T6 agent narrative.
**A의 권위는 T4의 정책결정권이지 T1~T3의 사실을 덮는 권한이 아니다.**

### Assertion type (03 §6)
DEFINITION / IMPLEMENTATION / OBSERVATION / ANALYSIS / DECISION / PROJECTION.
타입 없는 핵심 주장은 acceptance 대상이 아니다. D의 모든 verdict에도 타입을 붙인다.

### archetype n 규칙 (00 §12)
n≥5 정상 · n=3–4 LOW_N descriptive only · n≤2 ExcessDepth baseline 과해석 금지.

### Claim boundary (00 §16)
금지: 고령자 실패 인과주장 · 전체 모집단 무조건 일반화 ·
MPFED를 cognitive load 직접측정으로 표현 · 단일 composite senior score · 인증 효과 인과해석.

### Git (03 §9)
branch name만으로 상태 주장 금지. exact SHA 필수. 완료는 pushed SHA가 있어야 완료.
Git 밖 raw evidence는 `ARTIFACT_RETENTION_MANIFEST`로 노출.

---

## 3. 문서 대 사실 불일치 대장 (T5 vs T1)

D가 SSOTV2를 읽은 직후 `git ls-remote --heads origin`으로 직접 확인한 결과다.
아래는 SSOTV2를 부정하는 것이 아니라, **문서의 baseline 절이 이미 stale**임을 기록한 것이다.

| ID | 문서 주장 (T5) | 직접 관측 (T1) | 판정 |
|---|---|---|---|
| DF-01 | `08 §Exact remote heads`: control/landing-orchestrator = `084eff54…` | remote 실측 `d8f8595c01d20cde8a01e749bffafa8c1c697ef5` | **STALE_DOC** — A control plane이 문서 작성 후 전진 |
| DF-02 | `00 §17` remote baseline 목록 8개 | remote에 `claude-b/clean0-v21@196563f`, `claude-c/assurance-v21@e8277af`, `claude-b/w3-kwcag@4e60aba` 추가 존재 | **DOC_INCOMPLETE** — CLEAN0/I1이 이미 진행 중 |
| DF-03 | (B W1/W2/W4 작업 진행 서술) | `claude-b/w1-guard-wiring`, `w2-rf-detector`, `w4-axisc-mart` = **local only, 모두 `2281c85`에 정지**, origin에 없음 | **NOT_PUSHED** — 03 §9에 따라 완료 주장 불가 |
| DF-04 | SSOTV2 = 단일 SSOT (Research Director 지시) | `git status`: `?? SSOTV2/` — **Git 미추적** | **UNTRACKED_AUTHORITY** — 03 §16 투명성 목표 미달. Git 설치는 A의 권한행위 |
| DF-05 | 로컬 브랜치 `research/landing-accessibility-main` | 로컬 `32460b8`(refcohort) ≠ remote `bc0b7a0` | **NAME_TRAP** — 로컬 브랜치명을 믿으면 다른 트리를 읽는다 |

DF-04는 D가 고칠 수 없다(authoritative SSOT 경로는 D의 write scope 밖).
Research Director/A에게 보고만 한다.

---

## 4. D의 base 고정

- D branch: `claude-d/research-sandbox-v21`
- base SHA: `bc0b7a087faf2328cbafdfa9b40bd426c5080d7d`
- worktree: `.agent_worktrees/claude_d_research`
- 이후 모든 D notebook 첫 셀은 이 base SHA와 `INPUT_SNAPSHOT_v21.json` 해시를 기록한다.
