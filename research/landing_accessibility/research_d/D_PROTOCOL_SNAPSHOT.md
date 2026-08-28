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


---

## §16 V3 MAIN50 census 회차 (2026-08-28 10:44–12:15) — 추가분

**기존 §1~§15 는 고치지 않았다.** 이 절은 그 뒤에 붙는다. 위 절들의 결함 표는
`D-DEF-08` 까지이고 현재 대장은 `D-DEF-41` 이다 — 33건이 그 표 밖이므로
**결함 이력은 `results/D_DEFECT_LEDGER.json` 이 정본**이다(스냅샷 표는 옛 판본).

기록 시각 2026-08-28T12:16:15+09:00 · D head `74996b2dd66d15f82c2a2717a9de5d17131201d3`

### 지위 정정 (A T-A-V3-TBX-008)

`NON_CANONICAL` 은 **계산·EDA·ML·그래프를 만들면 안 된다는 뜻이 아니다.**
D 혼자 만든 수치를 최종 연구사실로 **승인**할 수 없다는 뜻이다. 분석·시각화
평면으로 적극적으로 쓰인다. claim 후보는 `to=[C] cc=[A]` 로만 올린다.

### 이번 회차에 승계한 A 판정

| 규약 | 내용 |
|---|---|
| R74/R92 | 수집기의 0(`COLLECTOR_ZERO_CANDIDATE`)과 사이트의 사실(`NO_SAFE_ROUTE_SITE`)을 **분리해 다른 색으로**. '못 셌다'(`UNVERIFIED_CANDIDATE_COUNT`)는 세 번째 값이지 0 이 아니다 |
| R78 | `completed` = `ENDPOINT_REACHED` 만 · `failed` = attempted − completed · `NOT_ATTEMPTED` 는 attempted 에 세지 않음 · **`unaccounted` 는 0 이어야 한다** · failed 는 혼자 두지 말고 terminal 분해를 붙인다 |
| R79 | streaming 파일은 **표와 sha 를 한 번의 `read_bytes` 에서** 만든다 |
| R87 | 입력 coverage 가 0 인 축은 **렌더하지 않고 `AXIS_NOT_OBSERVED`**. 빈 그림은 없음을 0 으로 보이게 한다 |
| R93 | 사후 파생 축은 **제목에 표기**한다. 각주로 숨기지 않는다 |
| R104 | 규칙의 산물을 발견으로 내지 않는다. 양쪽 관측 n 이 작으면 사이트 수준 발견으로 보고하지 않는다 |
| R106 | n 이 작으면 **분포로 그리지 않는다** — 개별 점 + 라벨 + 제목에 n/N |
| R110 | **어떤 컬럼이 100% sentinel 이면 통과가 아니라 미배선**(`WIRED:false` 의 열 단위 판정) |
| R113 | 회차별 terminal 을 **성능이 아니라 목적**으로 낸다. outcome 기반으로 대상이 선택된 rescue pass 는 성능 비교에 쓰지 않는다 |
| R122 | 같은 이름이 다른 것을 셀 때 **두 이름으로 분리**한다 (`R1 attempted` vs `R1-only surviving in mart`) |
| R125 | **sentinel 목록은 전역이 아니라 컬럼별이다.** 전역 목록으로 세면 값을 결측으로 만든다 |

### 이번 회차 D 결함의 공통 형태 — 한 줄로

**열이 채워졌다는 것과 관측됐다는 것은 다르다.** 그리고 **결측 검사와 값 읽기는
다른 행위다** — 열이 비었는지만 보면 열이 들고 있는 경고를 놓친다.
같은 자리에서 네 번 났다: `D-DEF-33`(골격 50행을 COMPLETE) ·
`D-DEF-37`(미관측 토큰을 값으로) · `D-DEF-39`(확인 가능한 상위 주장을 미확인) ·
`D-DEF-41`(채워진 열을 관측으로).

### 도구

| 파일 | 역할 |
|---|---|
| `tools/d_v3_census.py` | mart 계약(23+optional) · 결측 판정(패턴+형변환) · 분모(R78) · `axis_coverage` · `read_mart_pinned` |
| `tools/d_v3_report.py` | 보고서 그림 4장. 한글 폰트 지정 필수 |
| `tools/d_v3_tables.py` | 표 4종. **각 표 첫 줄에 읽는 법**을 적는다 — 그림의 경고가 표에는 없다 |
| `tools/d_v3_bundle_check.py` | 산출 정합성 + 대조군. 대조군 실패는 **다른 종료코드(3)** |
| `tools/d_prereg_check.py` | **사전등록을 문서에서 검사로.** 동결 mart·3집단 수치 불변 · probe 격리 · 발표물 provenance 결속 |
| `tools/d_citation_check.py` | **인용 정합성.** D 가 인용한 타평면 수치를 버스 최신 원천에서 다시 읽어 대조. 원천이 둘이면 둘 다 읽고 불일치를 먼저 flag |
| `tools/d_check_taxonomy.py` | D 검사가 값·신원·변화 중 무엇을 보는지 AST 분류 |
| `tools/d_none_passes_audit.py` | `None` 이 통과하는 자리 탐지(FALSE_ONLY · TRUTHY_GATE · BARE_GET) |
| `tools/d_presentation_eda.py` · `d_v3_tables.py` | 발표 EDA 15축 관측가능성 · 표 4종 |

### 이번 회차에 배운 것 — 검사 축의 세 층

D 검사 27개를 AST 로 분류하니 **전부 자기 정합성**이었다(`D-V3-FINDING-037`).
그 뒤 두 축을 더 만들었다. 세 층을 구분해서 쓴다:

| 축 | 묻는 것 | 놓치는 것 |
|---|---|---|
| **자기 정합성** | 내 기록이 현재와 같은가 | **아무 일도 일어나지 않았을 때도 통과한다** |
| **인용 정합성** | 내가 인용한 남의 수가 그 남의 최신본과 같은가 | 원천이 옳은지는 모른다 |
| **행위 유효성** | 내 행위가 대상을 바꿨는가 | **D 에는 아직 0개다** |

probe v3 에서 통한 검사가 세 번째 축이었다(클릭 전후 산출물 바이트 비교).
A 가 `T-A-V3-PROBE-V4-001` 에서 일반화했다 — **"우리가 만든 검사는 전부 값을 보고,
이번에 통한 검사는 산출물의 동일성을 봤다."**

### 다음 실행에 반드시 할 것

1. 결함 등재 **시점에** `caught_by` / `caught_how` 를 적는다 — 사후 복원 불가(`D-V3-FINDING-036`)
2. 검사를 만들면 **must_flag 대조군을 같이** 만든다. 전건 PASS 인데 must_flag 0 이면 공허통과다
3. 판본 간 열별 관측수 diff 검사 — `unwired`(전건 sentinel)와 `undermapped`(원본 대비 손실)
   사이의 구멍. **A 가 `control/v3/checks/column_regression_check.py` 로 구현했다(대조군 4/4).**
   그 성질을 먼저 승계할 것: **회귀 flag 는 '값이 사라졌다' 와 '거짓 관측이 정직한 미관측으로
   바뀌었다' 를 구분하지 못한다. 검사는 flag 만 내고 판정하지 않는다** — 자동 실패로 다루면
   정직한 시정이 회귀로 잡혀 검사가 무시된다. 역으로 회귀 목록은 **'무엇을 거짓 관측에서
   정직한 미관측으로 바꿨는가' 의 목록**이기도 하다. D 의 `axis_coverage` 를 판본 간으로
   확장할 때 이 구분을 먼저 넣는다
4. 미충족을 **닫았다고 적지 않는다**. 부분 완료는 부분 완료다
5. **남이 만든 분류를 표본 경계나 분석 축으로 쓸 때는 그 분류의 판정 근거를 먼저 검사한다**
   (A R140 · D-DEF-42). 경계가 틀렸으면 그 경계로 만든 표본도 틀린다
6. **조작 전후 산출물이 바이트 동일이면 그 조작은 무효다** — 검사에 넣는다 (A R146).
   probe v3 에서 클릭이 화면 밖을 찍었는데 예외가 없어 `ENDPOINT_REACHED` 가 나갔고,
   그것을 잡은 축은 값이 아니라 **스크린샷 바이트 동일성**이었다.
   D 의 `bundle_check` 는 sha 대조 축을 갖고 있으나 **조작 전후 축은 없다**

### 미충족으로 남긴 것

`D ML / robustness` — Gower 는 A 승인 하에 폐기, leave-one-service-out ·
missingness sensitivity 미실행. **closeout 이후 착수 금지(A 지시).**


### §16 추가 — 규칙을 적는 것이 준수를 보장하지 않는다

`D-DEF-42`("남이 만든 분류·수치를 판정 근거 검사 없이 축으로 씀")가 **두 회차
연속** 났다. 등재하고도 다음 회차에 같은 자리를 밟았다. 그래서 규칙을 검사로
옮겼다(`d_citation_check`). **결함을 대장에 적는 것과 그것이 다시 안 나게 하는
것은 다른 일이다.**

같은 이유로 사전등록도 검사로 옮겼다(`d_prereg_check`). A 가 R133 에서 B 를
평한 말이 기준이다 — **"결과를 보기 전에 철회 조건을 적어두면 결과가 판정을
바꾸지 못한다."** D 는 EDA 에서 그것을 하지 않아 SITE 16 철회 때 사후에 문구를
고쳤고, probe v4 에는 결과 전에 다섯 조건을 고정했다.

**A·B·C 도 같은 형태를 냈다.** C-DEF-29(placeholder 를 evidence 로 세어 관측 0 에서
만점) · B collection_run(전건 sentinel 이 모든 검사 통과) · A tally(`None` 이 통과해
조건 4 가 31/31 에서 한 번도 적용되지 않음). D 의 넷(33·37·39·41)도 같은 족이다.
**산출물이 있다는 사실을 관측이 있다는 사실로 세는 것** — 이 실행의 중심 결함족이다.
