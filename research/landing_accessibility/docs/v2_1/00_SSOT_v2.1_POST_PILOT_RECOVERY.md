# ProjectFinal — 고령층 실사용 모바일웹 초기진입 접근성 분석 SSOT v2.1

**문서 ID**: `LA-SSOT-2.1-POST-PILOT-20260827`  
**상태**: `PROPOSED_CURRENT_AUTHORITY_AFTER_CLEAN0`  
**기준 시각**: 2026-08-27 20:20 KST  
**연구 상태**: `POST-E001 MEASUREMENT RECOVERY`  
**현재 REAL_TARGET**: `NO-GO until recovery validation + A GO`  
**기존 파일럿**: `ORIGINAL_E001 = READ_ONLY`  

## 0. 이 프로젝트가 무엇인지부터 다시 고정

이 프로젝트는 **범용 웹 접근성 자동감사 제품, 범용 AI browser agent, 모든 웹사이트를 자동 판정하는 시스템을 만드는 프로젝트가 아니다.**

연구 목적은 다음과 같다.

> 고령층이 실제 많이 사용하는 서비스 frame에서, 모바일웹의 최초 랜딩과 대표기능의 얕은 진입까지를 동일한 브라우저 조건과 동일한 측정 규칙으로 관측하여, 표준 접근성 장벽, 구조적 진입깊이, 초기 obstruction을 서비스 단위 데이터로 만들고 그 분포와 관계를 분석하는 것.

자동화는 연구 목적이 아니라 다음을 위한 수단이다.

- 동일 조건 반복 측정
- 사람의 자의적 클릭 최소화
- evidence provenance 보존
- 동일 기준의 feature extraction
- ambiguity의 명시적 abstain
- 분석 가능 데이터 생성

따라서 **범용화보다 연구 frame 안에서의 측정타당성, 재현성, 증거보존이 우선**한다.

---

## 1. 권위와 승계

본 v2.1은 기존 v2를 폐기하지 않는다.

### 그대로 승계

- 연구 질문
- L0 + L1 shallow entry 범위
- 세 독립 측정축
- NED / IED / MPFED 정의
- KWCAG PASS / FAIL / UNDETERMINED / NA 어휘
- evidence append-only 및 hash lineage
- outcome-blind target/task freeze 원칙
- Human Final 최대 5건
- 새로운 supervised DNN/XGBoost를 기본 분석으로 쓰지 않는 원칙
- 동일 archetype 내부 상대깊이 비교

### 본 v2.1이 우선하는 부분

- 2026-08-27 E001 이후 현재 상태
- ORIGINAL_E001의 지위
- 대표기능 매핑의 실제 운영 절차
- 로그인/인증/CAPTCHA guard 입도
- task definition wiring 복구
- 실웹 area/endpoint detector 요구사항
- KWCAG production evaluator 복구
- A/B/C orchestration protocol
- CLEAN-0 및 recovery gate

### 권위 해석 규칙

서로 모순할 경우 다음을 구분한다.

1. **사실 확인**은 exact SHA의 코드, raw artifact, runtime observation, 재현 가능한 계산이 우선.
2. **연구 결정**은 current SSOT와 A가 승인한 decision record가 우선.
3. docstring, 주석, 에이전트 보고문은 사실의 근거가 될 수 있으나 독립 검증 없이 구현·관측 사실로 승격하지 않는다.

즉 **권위가 사실을 만들어내지는 않는다.** A는 정책과 연구계약을 결정하지만, 실제 코드·데이터 상태는 증거로 확인한다.

---

## 2. 현재 파일럿에서 확인된 사실

ORIGINAL_E001은 다음 상태로 동결한다.

- 59 / 59 target attempted
- grade = PILOT / PRELIMINARY
- Axis A = NOT_EVALUATED
- Axis B = MPFED available 0 / 59
- Axis C = raw measured, classification incomplete
- planned association = NOT_COMPUTABLE
- substitute analysis = none
- forbidden action = 0

이 결과는 실패한 접근성 결과가 아니라 **측정 시스템 파일럿 결과**다.

### 확인된 핵심 결함

#### G1. Guard granularity

현재 target-level guard는 L0의 후보 중 로그인 등 금지 패턴 하나가 존재하면 Scout 전체를 차단한다.

파일럿에서 target-level guard 25/59, LOGIN 19건이 확인됐고 QUERY 5건은 Scout 전 진입이 막혔다.

**복구 원칙**: target-level kill을 폐기하고 candidate/state-level action safety로 전환한다.

#### G2. Task-definition wiring

대표기능 region/endpoint 정의는 upstream P-B task candidate 59행에 존재했으나 실행 경계에서 일부 필드가 유실됐다.

**복구 원칙**: existing definition을 새로 만들지 않고 exact field lineage를 복원한다.

#### G3. Real-site signal detector

현재 area/endpoint detector는 synthetic fixture marker에 의존해 실제 상용 DOM에서 정의를 검출하지 못한다.

**복구 원칙**: frozen signal family인 DOM/AX role, Form Structure, URL Pattern을 실제 웹에서 구현한다.

#### G4. KWCAG production evaluator

older-relevant subset과 raw evidence는 있으나 production criterion adjudicator가 없다.

**복구 원칙**: frozen subset만 대상으로 `Applicability → Evidence → Expectation → Outcome` evaluator를 구현한다.

#### G5. Axis C semantic completion

overlay geometry는 확보됐으나 semantic classification과 task-specific primary action binding이 완결되지 않았다.

**복구 원칙**: page-level geometry는 보존하고, task binding 복구 후 primary-action occlusion을 재검증한다.

---

## 3. 연구의 세 독립 측정축

### Axis A — Standard Accessibility

질문:

> 최초 랜딩과 얕은 대표기능 진입에서, KWCAG 2.2의 older-relevant criterion에 대해 관측 가능한 장벽이 있는가?

출력:

- PASS
- FAIL
- UNDETERMINED
- NA

서비스 단위 요약:

- EligibleOlderRelevant
- FailOlderRelevant
- OlderRelevantKWCAGFailRate
- DecisionCoverage
- UNDETERMINED count/rate

`UNDETERMINED`를 PASS나 FAIL로 세탁하지 않는다.

### Axis B — Structural Entry Depth

질문:

> 동일한 대표기능 유형에서 해당 기능 영역과 첫 endpoint까지 구조적으로 얼마나 깊은가?

- NED = landing에서 representative function region까지의 최소 state-changing activation 수
- IED = region에서 predefined endpoint까지의 최소 activation 수
- MPFED = NED + IED
- endpoint 전 중단이면서 region이 관측되면 NED는 보존하고 IED/MPFED는 NULL
- scroll, text typing, redirect, passive wait, popup dismissal은 depth에 합산하지 않음

상대깊이:

`ExcessDepth = MPFED - same-archetype median(MPFED)`

절대적인 `3 click = bad` 기준은 만들지 않는다.

### Axis C — Initial Obstruction

질문:

> 최초 viewport에서 popup, modal, banner, app prompt 등이 화면 또는 대표행동을 얼마나 방해하는가?

핵심:

- OverlayCoverage
- PrimaryActionOcclusion
- body scroll lock
- dismiss control presence/visibility/actionability
- forced dismissal count
- interrupt type

세 축은 서로 합산해 단일 고령친화 점수로 만들지 않는다.

### External Reference — WA Certification

WA 인증은 gold label이 아니다.

현재 frame에서 variance가 충분하지 않으면 추론을 하지 않는다.

---

## 4. 분석 frame

Wiseapp 사용자료는 전체 한국 고령인구의 확률표본이 아니다.

이 연구는 **실사용 exposure proxy**를 기반으로 한 서비스 frame 연구다.

현 파일럿의 대표 task frame은 59개다.

interaction archetype:

- QUERY
- CONTENT_OPEN
- ITEM_DETAIL
- PLACE_LOOKUP
- COMMUNICATION_ENTRY
- FINANCIAL_ACTION_ENTRY
- UTILITY_ENTRY

같은 서비스라도 business domain과 interaction archetype은 다를 수 있다.

Depth 비교는 business domain이 아니라 interaction archetype을 기준으로 한다.

---

## 5. 실제 수집이 의미하는 것

REAL_TARGET observation은 단순 HTTP fetch가 아니다.

기본 브라우저 조건:

- fresh context
- no login / no cookie
- 390 × 844 CSS px viewport
- mobile UA
- touch enabled
- `ko-KR`
- `Asia/Seoul`
- JavaScript enabled

L0 evidence:

- rendered DOM
- Accessibility Tree via browser/CDP
- computed CSS
- geometry
- viewport screenshot
- full-page screenshot
- JS probe raw features
- manifest/hash provenance

Guard가 L1을 막더라도 L0 evidence는 먼저 보존한다.

---

## 6. Representative Function Mapping — 연구의 핵심 복구 지점

대표기능은 service name만 보고 확정하지 않는다.

### 6.1 두 단계 원칙

1. **Prior hypothesis** — source context, business identity, existing codebook으로 candidate archetype 생성
2. **Observed interaction verification** — 실제 DOM/AX/Form/URL 구조로 candidate를 검증

Business domain은 prior이며 최종 근거가 아니다.

### 6.2 최종 leaf는 다음을 반드시 가진다

- interaction_archetype
- representative_function_name
- region_definition
- region_signal_type
- endpoint_definition
- endpoint_signal_type
- mapping_basis
- evidence_refs
- mapping_confidence 또는 abstain status
- forbidden continuation

### 6.3 정의와 관측을 분리한다

- `endpoint_definition exists` = 연구계약이 존재한다는 뜻
- `endpoint_observed` = 실제 수집에서 그 상태가 관측됐다는 뜻

둘을 절대 같은 필드나 같은 문장으로 표현하지 않는다.

### 6.4 Rule DT 우선

대표기능 분류는 `01_REPRESENTATIVE_FUNCTION_MAPPING_DT_v2.1.md`를 따른다.

### 6.5 NLP fallback

Rule DT가 유일 leaf를 만들지 못할 때만 pretrained text/embedding 기반 fallback을 사용한다.

입력 후보:

- page title
- headings
- visible text
- accessible names
- AX roles
- form labels
- repeated card text
- URL segments
- nearby semantic context

출력은 일곱 archetype 밖으로 나갈 수 없다.

Threshold는 임의 고정하지 않고 independent label set의 calibration split에서 정한다.

holdout에서 불확실하거나 candidate margin이 낮으면 `AMBIGUOUS_UNRESOLVED`로 남긴다.

VLM은 DOM/AX/text만으로 의미가 닫히지 않는 소수 사례에만 쓴다.

Human Final은 최대 5건.

---

## 7. Login / Auth / CAPTCHA / Forbidden Action — 새 guard 계약

### 7.1 존재와 행동을 구분

로그인 버튼이 존재한다는 이유만으로 target 전체를 중단하지 않는다.

- login button present → raw feature / candidate annotation
- login candidate activation → archetype와 current path에 따라 조건부 허용 가능
- credential field input → 절대 금지
- login submit → 절대 금지

### 7.2 Auth gate가 endpoint가 되는 경우

- FINANCIAL_ACTION_ENTRY: LOGIN 또는 IDENTITY_VERIFICATION gate가 endpoint가 될 수 있음
- COMMUNICATION_ENTRY: LOGIN gate가 endpoint가 될 수 있음
- 나머지 archetype: auth gate는 기능 endpoint가 아님

### 7.3 Purchase / payment control

구매·결제 control의 **존재 관측**은 가능하다.

클릭·제출·확정은 금지한다.

ITEM_DETAIL에서는 거래 control의 존재가 상세 endpoint 확인의 evidence가 될 수 있다.

### 7.4 CAPTCHA

DOM 안에 CAPTCHA 코드·문구가 있다는 사실만으로 terminal 처리하지 않는다.

현재 chosen path의 다음 진행을 막는 visible/active challenge가 실제로 나타난 순간 `CAPTCHA` terminal로 기록한다.

CAPTCHA를 해결하거나 우회하지 않는다.

### 7.5 Candidate-level action mask

각 activation candidate에 최소 다음 상태를 둔다.

- SAFE
- AUTH_ENTRY_ALLOWED_CONDITIONALLY
- FORBIDDEN_CREDENTIAL_INPUT
- FORBIDDEN_TRANSACTION
- FORBIDDEN_PERSONAL_DATA
- FORBIDDEN_CAPTCHA_BYPASS
- DISABLED_OR_INERT
- BLOCKED_BY_OVERLAY
- UNKNOWN

Scout는 SAFE 또는 현재 archetype에서 허용된 AUTH_ENTRY만 확장한다.

---

## 8. Depth detector 요구사항

### 8.1 Region detector

실웹에서 `data-region` synthetic marker를 요구하지 않는다.

signal type에 따라 다음을 실제 DOM/AX에서 판단한다.

- DOM_AX_ROLE
- FORM_STRUCTURE
- URL_PATTERN
- 필요 시 MEDIA_STATE / GATE_SIGNAL

### 8.2 Endpoint detector

endpoint는 codebook의 definition을 새로 발명하지 않고, 정의된 signal type을 구현해 관측한다.

### 8.3 최소경로

bounded BFS + Path Freeze + Replay를 유지한다.

`minimal`은 동결된 search space 안에서의 최소 activation 경로를 뜻한다.

### 8.4 Partial depth

endpoint 미도달이 곧 전부 결측이라는 뜻은 아니다.

대표기능 영역까지만 관측되면 NED는 보존한다.

---

## 9. KWCAG production evaluator

새 기준을 만들지 않는다.

frozen older-relevant subset을 대상으로 criterion별로 다음 네 단계를 구현한다.

1. Applicability
2. Required evidence slots
3. Expectation / official criterion condition
4. Outcome

각 criterion은 raw evidence와 exact evaluator version을 연결한다.

### 자동화 우선순위

1. browser-native / AX
2. deterministic geometry/CSS
3. semantic text/embedding
4. VLM
5. Human Final

### 금지

- measurement failure를 FAIL로 바꾸기
- evidence 없는 PASS/FAIL 생성
- AI가 기존 UNDETERMINED를 세탁하기
- service-level result를 criterion row로 복제하기

---

## 10. Obstruction detector

Page-level OverlayCoverage는 기존 evidence에서 우선 재사용한다.

Task-specific PrimaryActionOcclusion은 representative function binding이 복구된 뒤 재계산 또는 재검증한다.

interrupt semantic classification은 deterministic rule → text/NLP → VLM → abstain 순서.

---

## 11. 독립 label set

Detector 생산자와 정답 생산자를 분리한다.

- B = detector producer → label 금지
- C = assurance reviewer → gold label 생산 금지
- A가 독립 Labeler worker를 별도로 orchestrate

Labeler는 actual result/statistics를 보지 않고 DOM/AX/evidence만 사용한다.

label 파일은 detector calibration 이전 SHA256으로 동결한다.

가능하면 calibration set과 holdout set을 분리한다.

B는 calibration만 이용한다.

C가 holdout을 독립 검증한다.

---

## 12. 분석

### 기술통계

- collection / joint-valid flow
- archetype distribution
- KWCAG PASS/FAIL/UNDET/NA
- MPFED / NED / IED distribution
- ExcessDepth
- obstruction distribution
- endpoint status
- auth gate prevalence

### 통계

작은 정수·tie·비정규성을 고려해 rank/nonparametric을 기본으로 한다.

- Spearman
- Kruskal–Wallis when group n sufficient
- permutation / Dunn when justified
- Fisher exact where applicable
- leave-one-service-out
- leave-one-archetype-out
- UNDETERMINED stress bounds

### archetype n rule

- n ≥ 5: normal descriptive / planned inferential candidate
- n = 3–4: LOW_N, descriptive only
- n ≤ 2: ExcessDepth baseline을 과해석하지 않음

### 핵심 시각화

서비스 단위 joint plot:

- x = ExcessDepth
- y = OlderRelevantKWCAGFailRate
- point size = OverlayCoverage
- facet = InteractionArchetype
- WA certification은 variance가 있을 때만 보조 encoding

세 축이 하나의 scalar score로 합쳐지지 않았다는 점이 시각화에서도 유지돼야 한다.

---

## 13. ORIGINAL_E001의 사용법

ORIGINAL_E001을 지우거나 덮어쓰지 않는다.

사용 가능한 것:

- L0 raw evidence
- guard failure distribution
- wiring defect evidence
- detector gap evidence
- Axis C raw geometry
- provenance / duplicate-launch lessons

주 연구결과로 사용할 수 없는 것:

- MPFED 0/59을 서비스 특성으로 해석
- Axis A 결과라고 주장
- guard 차단을 접근성 실패로 해석
- pilot에서 계산 불가능했던 association을 사후 대체

---

## 14. CLEAN-0 — 짧은 클리닝

삭제·대규모 refactor가 아니다.

목적은 **현재 무엇이 권위이고, 무엇이 과거이며, 무엇이 observation이고, 무엇이 definition인지 다시 타입을 붙이는 것**이다.

최대 25분.

필수 산출:

- `CURRENT_AUTHORITY_MAP`
- `CURRENT_REMOTE_HEADS`
- `ORIGINAL_E001_READONLY_DECLARATION`
- `SEMANTIC_ASSERTION_LEDGER`
- stale/superseded doc list
- local evidence `ARTIFACT_RETENTION_MANIFEST`
- known blocker ledger G1~G5
- agent bus health / exactly-once check

삭제 금지.

---

## 15. REAL_START_READY의 뜻

`REAL_START_READY`는 범용 시스템 완성을 뜻하지 않는다.

다음이 충족되면 연구용 실제 소스 수집을 시작할 수 있다.

1. guard가 candidate/state-level로 작동
2. task definition 59/59 lineage 보존
3. real-site representative function DT가 offline evidence에서 검증
4. endpoint detector가 synthetic marker 없이 작동
5. KWCAG frozen subset evaluator 최소 production path 확보
6. obstruction raw + semantic path 확보
7. evidence manifest 및 exactly-once launch 검증
8. independent holdout / C assurance PASS
9. A explicit GO

이 지점에서 8–12개 stratified REAL_TARGET pilot을 먼저 돌릴 수 있다.

pilot이 systemic mismatch 없이 통과하면 full 59 run을 시작한다.

---

## 16. Claim boundary

허용:

- 이 실사용 서비스 frame에서 관측된 표준 접근성 장벽의 분포
- 동일 archetype 안에서 상대적으로 깊은 서비스
- 초기 overlay의 면적과 대표기능 가림 정도
- 세 측정축 사이의 연관성

금지:

- 고령자가 실제로 실패했다는 인과 주장
- 모든 한국 고령자 또는 모든 웹서비스 모집단으로의 무조건 일반화
- MPFED를 cognitive load 직접 측정치로 표현
- 단일 composite senior accessibility score
- 인증 효과 인과해석

---

## 17. 현재 exact remote baseline

- authoritative main: `bc0b7a087faf2328cbafdfa9b40bd426c5080d7d`
- control: `084eff541836c2e16418b96bd230c1d58bcda663`
- B analysis: `82f631f1e6bd3708bc8f95f0b8edcd90e22cef0d`
- B recovery audit: `2281c853950d0c475c5d2c1678680b971c2804f4`
- C assurance: `1baa865b4a673af05033e6e6289fd2713676baa5`
- A handoff: `7c8facebe95ec3793756a82d809be37ca17b6b6e`
- B handoff: `66aa655400f872197e64390522225823e93b5628`
- C handoff: `3d84741656ce08991ceb06572b2b242470f1f9e3`

branch name만으로 상태를 주장하지 않는다. 모든 완료·승인·감사는 exact SHA를 포함한다.

---

## 18. 오늘 밤 목표

20:20 KST 기준 목표:

- 00:30 이전: `REAL_START_READY` 또는 명시적 `PARTIAL_READY_WITH_BLOCKER`
- 00:30 전후: stratified real pilot 완료 또는 full collection 시작
- 01:00~02:00: full collection + mart build 병렬
- 02:00~03:00: planned statistical analysis + C independent replay + A claim acceptance

시간 때문에 연구정의를 바꾸지 않는다.

다만 non-blocking polish는 과감히 이월한다.
