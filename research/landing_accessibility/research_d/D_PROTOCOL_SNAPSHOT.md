# D 플레인 프로토콜·방법론 스냅샷

**목적**: 피벗 이후에도 지금의 오케스트레이션 방식·검증 규율·방법론을 그대로 승계한다.
이 문서는 **보존용**이며 새 지침이 오기 전까지 D 는 이 규약을 바꾸지 않는다.

작성 시각 2026-08-28 01:47 KST · D HEAD `3d7a547` · 브랜치 `claude-d/research-sandbox-v21`

---

## 1. 역할과 권한 경계

- A = Research Governor (DECISION 권한), B = Production & Measurement Orchestrator,
  C = Independent Scientific Assurance, **D = Independent DS/ML Research Sandbox**.
- D 는 `GO` / `BLOCKER` / `DIRECTIVE` / `SUPERSEDE` 를 **발행하지 않는다.**
  construct 정의·threshold·재수집 판단은 A 권한이다.
- D 산출의 기본 authority 는 `NON_CANONICAL`. plane 별 기본값:
  `D=NON_CANONICAL`, `B=IMPLEMENTATION_CANDIDATE`, `C=ASSURANCE_RESULT`, `A=DECISION`.
  A 가 아닌 plane 이 `DECISION` 을 기록하려 하면 계약 모듈이 `ContractViolation` 을 던진다.

## 2. 라우팅 (T-A-D-ROUTING-003)

D 의 모든 research finding·evidence 는 **A 가 직접 물었을 때에도** `to=[C]` 로 간다.
긴급성은 `priority` 필드로만 표현하고 **경로로 표현하지 않는다.**
이 규칙은 한 번 위반한 적이 있다(`D-HOLD-EVIDENCE-001`, P0 상황에서 우회). 원 티켓은 남기고
`D-HOLD-EVIDENCE-002` 로 재발행했다 — **잘못 보낸 티켓도 지우지 않는다.**

## 3. 진리 위계 (T1–T6)

1. exact byte / runtime evidence
2. 독립 재현 가능한 계산
3. frozen 정의 / codebook
4. 현행 SSOT / 결정
5. 산문 문서
6. 에이전트 서술

**MLflow 메타데이터는 5–6 수준이다.** MLflow 는 SSOT 도 실증 진리도 아니고 **index** 다.

## 4. 주장 유형과 판정 어휘

- 주장 유형: `DEFINITION` / `IMPLEMENTATION` / `OBSERVATION` / `ANALYSIS` / `DECISION` / `PROJECTION`
- 판정: `SUPPORTED` / `PARTIALLY_SUPPORTED` / `REFUTED` / `NOT_SUPPORTED` / `INCONCLUSIVE` / `NOT_TESTABLE`

`NOT_TESTABLE` 은 좁게 쓴다. **"Scout 이 안 돌아서 못 본다" 와 "정적으로도 못 본다" 는 다른 문장이다** —
RQ-D6b 에서 이 둘을 섞어 판정을 너무 넓게 닫았고 RQ-D6b-1 이 정정했다.

## 5. 측정축 규약

세 축은 **독립 측정축**이며 단일 composite 로 합산하지 않는다 (SSOT §3 · §15/§16).
- Axis A: KWCAG 고령자 관련 criterion — **현재 `fact_criterion_result` 0행, evaluator 모듈 부재.**
  Axis A 수치는 전부 `proxy` 표기를 붙인다.
- Axis B: NED / IED / MPFED — **현재 59/59 전부 None.** 결과변수로 쓸 수 없다.
- Axis C: overlay / obstruction.

정의 수준의 독립은 유지되지만 **측정 공정 수준에서는 slot 이 공유된다** (PILOT-E, slot 15 중 8).

## 6. prior 취급

`prior_archetype` 은 **gold label 이 아니라 prior** 다. "accuracy" 라는 말을 쓰지 않고
`prior_agreement` 로만 부른다. `prior_archetype` ↔ `prior_business_domain` 은 **완전 전단사**
(7↔7, nMI 1.000, 56/56 — `D-FACT-01`)이므로 모든 일치 지표는 실질적으로 **업종 배정 재현율**이다.

## 7. 방화벽 (D1)

- 금지: gold label 생산, holdout 열람, REAL_TARGET 접속, production/control/engine/mart/raw evidence 수정.
- 허용 입력은 `D_INPUT_ALLOWLIST.json` 이 정의한다. denied 목록은 그 파일이 단일 출처다.
- **`holdout_accessed` 는 self-report 하지 않는다.** `tools/d_input_firewall.py` 의 스캐너 결과로만 기록한다.
  스캔 결과 파일이 없으면 `UNVERIFIED_NO_SCAN`, PASS 일 때만 `false`.
- 스캐너는 3단 severity: 같은 줄에 파일 접근 호출이 있으면 `FAIL`, 부정 선언 문맥이면 `WARN`,
  설명 없는 참조는 보수적으로 `FAIL`.
- **예외를 하나 더 붙이면 그만큼 눈이 먼다** — 3차 오탐이 났을 때 스캐너가 아니라 문서를 고쳤다.

## 8. 서브에이전트 오케스트레이션

- 워커 프롬프트에 반드시 넣는 것: 절대 규칙(방화벽·git 금지·기존 산출물 수정 금지),
  작업 루트 절대경로, **경쟁가설 전부 열거**, 반드시 잴 것, 하지 말 것(GO/NO_GO·인과주장 금지),
  MLflow 계약 인자, 산출물 목록, 최종 보고 형식.
- 프롬프트 말미 고정 문구: **"네 가설을 방어하지 마라. 네 가설이 틀렸으면 틀렸다고 먼저 써라."**
- 워커에게 방화벽 서술 시 금지 파일명 토큰을 한 줄에 나열하지 말라고 명시한다 (D-DEF-05 재발 방지).
- 워커는 `git add/commit/push` 를 하지 않는다. `git show <sha>:<path>` 읽기 전용 열람만.
- 코드는 항상 **exact SHA** 에서 읽는다. 현재 integration SHA = `2281c853950d0c475c5d2c1678680b971c2804f4`.
  probe 경로는 `research/landing_accessibility/src/landing_accessibility/engine/l0_probe.js`.

## 9. 워커 산출 검증 규율

**워커가 상위계층(수집기·engine·mart) 결함을 보고하면 broadcast 전에 raw 스키마와 원본 바이트를 D 가 직접 연다.**
두 번 연속 내 파싱 결함이 상위계층 결함처럼 보였다 (D-DEF-01 charset, D-DEF-03 dismiss 래퍼 리스트).
왕복/역산 검증을 만들어 내 코드가 원인일 가능성을 먼저 배제한 뒤에만 티켓을 발행한다.

## 10. 완결 게이트 (D-DEF-07)

산출이 확정됐다고 취급하는 조건은 **셋 다**:
1. 결과 JSON 최상위에 `verdict`
2. `<prefix>_FINDINGS.md` 존재
3. 노트북 Restart → Run All 에러 0

이 게이트를 통과하기 전에는 **MLflow 색인도, git commit 도, 티켓 발행도 하지 않는다.**

## 11. 불변성 규율

- **MLflow run 은 삭제하지 않는다.** 잘못 만든 run 도 남기고 `d.run_status=SUPERSEDED` +
  `d.superseded_reason` 태그를 붙인다. run 삭제는 덮어쓰기와 같은 종류의 조작이다.
- **git 히스토리를 고쳐 쓰지 않는다.** 잘못 담긴 커밋도 남기고 결함 기록으로 표시한다 (D-DEF-08).
- **발행한 티켓은 수정하지 않는다.** 보강은 `ADDENDUM` 으로, 철회는 `FACT_CORRECTION` 으로 한다.
- **기존 산출물을 소급 수정하지 않는다.** 결론이 뒤집히면 조건부여 기록을 새로 쓴다
  (`D_CORPUS_VERSION_EFFECT_001.json` 이 그 사례).

## 12. 커밋 위생 (D-DEF-08)

워커 실행 중에는 `git add -A` 를 쓰지 않는다. 확정 파일 경로만 명시적으로 stage 하고,
커밋 직후 `git show --stat` 으로 메시지와 내용이 맞는지 확인한다.
커밋 메시지에 백틱을 쓰지 않는다(셸 치환) — `git commit -F <file>` 를 쓴다.
커밋은 **반드시 워크트리 cwd 에서** 한다 (레포 루트에서 하면 pathspec 이 안 맞아 조용히 누락된다).

## 13. 통계 규약

- 비율에는 항상 **분자 / 분모 / grain** 을 붙인다. target grain 과 candidate/step grain 을 섞지 않는다.
- 이항 비율은 Wilson 95%, 연관은 φ + permutation, 짝지은 비교는 McNemar / 부호검정.
- 다중비교에는 **BH-FDR**. `p<0.05` 를 발견으로 포장하지 않는다.
- 정의 의존적인 양은 **최소 3개 규칙으로 민감도 분석**하고 방향이 유지되는지를 본다
  (크기가 아니라 방향의 강건성이 판단 대상).
- **동어반복 검정을 발견으로 취급하지 않는다** (RQ-E-1 의 T3 사례).
- **무결과 검증에는 대조군이 필요하다** — 빈 결과와 통과가 같은 출력으로 나온다.
  방화벽 스캐너 검증에 대조군 주입을 쓴 이유가 이것이다.

## 14. 결함 대장 (D 자신의 결함)

| ID | 무엇 | 상태 |
|---|---|---|
| D-DEF-01 | 선언 charset 무시 → mojibake. 상위계층 결함으로 오인해 발행했다가 철회 | 시정·철회 완료 |
| D-DEF-02 | 방화벽 severity 가 토큰 히트에 미적용 → 오탐 7 | 시정 |
| D-DEF-03 | dismiss 래퍼 리스트 길이를 컨트롤 수로 셈 | broadcast 전 포착 |
| D-DEF-04 | CSS 혼입 제거 누락 | 시정 (코퍼스 v3) |
| D-DEF-05 | 기계가독 부정선언을 스캐너가 참조로 오독 → 오탐 30 | 시정 (줄 성격 판정) |
| D-DEF-06 | MLflow 색인이 D 산출의 30% 만 담음 | 시정 (10→33) |
| D-DEF-07 | 미완 산출 색인 + RQ-E 계열 누락 | 시정 (완결 게이트) |
| D-DEF-08 | 워커 실행 중 `git add -A` 가 중간본을 커밋에 담음 | 기록·관행 변경 |

## 15. 현재 미완 상태 (피벗 시점)

- **RQ-D7**: JSON·tool·figure 있음, FINDINGS.md·노트북 없음. MLflow 39 metrics 기록됨. **미발행.**
- **RQ-D13b-1/2**: JSON·FINDINGS.md·tool 있음, 노트북 없음, **두 파일 판본 정합성 미확인.** 미발행.
- OPEN: RQ-E-1a, RQ-E-3, RQ-E-4, RQ-E-5, RQ-D11a, RQ-D7, RQ-D13b-1/2.
- PILOT child A / B / C-part2 / D: `PENDING_PILOT_FREEZE` — 캡처 산출물 미도착.
- 발행 완료: `D-RESEARCH_FINDING-003/004/005`, `D-ADDENDUM-002` (C ACK 완료).
