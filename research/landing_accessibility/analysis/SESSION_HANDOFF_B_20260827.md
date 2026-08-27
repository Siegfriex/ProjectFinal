# SESSION HANDOFF — Claude B (Production / Recovery)

**작성** 2026-08-27 17:50 KST · **작성자** Claude B · **지위** `HANDOFF` (authoritative 아님)
**base** `claude-b/analysis-current@82f631f` — 이 문서 외 파일 수정 0

이 문서는 **다음 세션의 진입점**이다. 여기 적힌 SHA·수치는 전부 이 세션에서
`git ls-remote` 및 파일 실측으로 확인한 값이며, 보고서에서 옮겨 적은 값이 아니다.

---

## 1. FREEZE — immutable resume reference

아래 세 참조는 **수정 대상이 아니다.** 재개 시 읽기만 한다.

| 역할 | 브랜치 | SHA (full) |
|---|---|---|
| canonical analysis | `claude-b/analysis-current` | `82f631f1e6bd3708bc8f95f0b8edcd90e22cef0d` |
| measurement recovery audit | `claude-b/measurement-recovery` | `2281c853950d0c475c5d2c1678680b971c2804f4` |
| collector (E001 수집에 사용) | — | `222ef2c28ed5971b3c9f8b07120b7627d2617476` |

`222ef2c`는 `claude-b/e000-real` 및 4개 워커 브랜치(`claude-b/e001-worker-01..04`)가
동일하게 가리키는 tip이다. 워커 브랜치는 로컬 ref만 존재하나 **고유 커밋 0개**이므로
소실 위험이 없다(§9 참조).

---

## 2. REMOTE VERIFY — 2026-08-27 17:46 KST `git ls-remote origin`

```
82f631f1e6bd3708bc8f95f0b8edcd90e22cef0d  refs/heads/claude-b/analysis-current
2281c853950d0c475c5d2c1678680b971c2804f4  refs/heads/claude-b/measurement-recovery
1baa865b4a673af05033e6e6289fd2713676baa5  refs/heads/claude-c/assurance-current
084eff541836c2e16418b96bd230c1d58bcda663  refs/heads/control/landing-orchestrator
bc0b7a087faf2328cbafdfa9b40bd426c5080d7d  refs/heads/research/landing-accessibility-main
```

**5/5 전부 원격에 존재하며 지시받은 값과 정확히 일치한다.**

### 검증 이력 — 이 세션에서 실제로 고친 것

`17:23` 시점 점검에서 **A의 판정 5커밋이 전부 미푸시**였다:

```
origin/control/landing-orchestrator = 40f25ed (15:45)   ← 당시 원격 최신
로컬에만 존재하던 5건:
  371ca6d  FINAL 산출물 정정 기록
  09e92ef  FINAL canonical=82f631f 확정
  78899c0  복구계획 개정 1 — 갭1/갭2 단일 게이트
  b654cfa  복구계획 개정 2 — 리플레이 승인 + 게이트 미검증 병기 의무
  084eff5  개정 2 세부 — 라벨러·라벨 해시 동결·모집단 56
```

`git branch -r --contains`로 5건 모두 원격 브랜치 0개임을 확인해 A에 통보했고,
A가 push하여 `17:46` 기준 `084eff5`가 원격 tip이 됐다.
**데이터는 push됐는데 그것을 수용한 판정만 로컬에 있던 상태였다.**

---

## 3. 오늘 결과 — 확정 수치

| 항목 | 값 |
|---|---|
| E001 attempted | **59 / 59 타깃** (커버리지 100%) |
| grade | **PILOT / PRELIMINARY** |
| MPFED available | **0 / 59** (E000 6건 포함 65연속 null) |
| association | **NOT_COMPUTABLE** |
| substitute analysis | **none** (`substitute_made: false`) |
| Axis A (KWCAG) | **NOT_EVALUATED** — evaluator 부재 |
| Axis C (obstruction) | **raw observed / classification incomplete** |
| canonical | `82f631f` |
| measurement recovery audit | `2281c85` |
| C0 | **0** |
| 금지행위 | **0** |
| Pilot diff | **0** |
| final claims | **direct / descriptive only** (12건 전부 grade A) |

### mart 실측 행수 (`FROZEN_MART_MANIFEST.json` 기준, 이 세션에서 재확인)

```
fact_landing_observation.json    56    sha256:4ed58b66e002d25c…
fact_task_entry.json             31    sha256:61bb70510…
fact_interrupt_element.json     235    sha256:caebf1a43…
fact_criterion_result.json        0    sha256:4f53cda18…   ← 축 A 미평가의 귀결
dim_certification.json            0    sha256:4f53cda18…
```

`input_shas` 7건 기록. `batch_chain_verified_all_sources` 필드로 해시체인 검증 완료.

### MPFED 0/59 원인 분해 (A·B·C가 서로 다른 조인 경로로 3중 확인 · 상호배타 분할)

```
가드 입도                     25 (42.4%)   LOGIN 19 · PURCHASE 3 · SIGNUP 2 · PAYMENT 1
archetype-endpoint 규칙 자체   11 (18.6%)   본 연구 계약의 설계
UNRESOLVED                    18 (30.5%)   WALL_CLOCK 7 · SCOUT_ERROR 3 · NO_STATE_CHANGE 2 · 미기록 6
SKIPPED_RETRY_EXHAUSTED        3           detail={} · scout_invoked=None
CAPTCHA                        1
E-6b 구속                      1           발화 8 / 구속 1
합                            59
```

**반사실:** 비승격 archetype 중 Scout가 차단 없이 실행된 건의 endpoint 도달 = **0 / 25**.
가드는 **관측되지만 구속하지 않는다.** 복구 상한 8, 정직한 범위 **"0~8"**,
라벨 `CURRENT_IMPLEMENTATION_CONDITIONAL_COUNTERFACTUAL`. **이 반사실의 일반화는 금지된다.**

---

## 4. ROOT CAUSE — 두 갭은 독립이다

### Gap 1 — wiring

원천 P-B CSV에 **59/59 task definition 관련 정보가 존재한다.**
그러나 `E001TargetRow` → `TaskDefinition` 실행경로에서 **소실**된다.

```
executor.py:57-75  default_task_definition() 이 인자와 무관하게 4개 상수를 반환
                   region_definition=None · endpoint_definition=None
                   region_signal_type=CODEBOOK_PENDING · endpoint_signal_type=CODEBOOK_PENDING
```

이 함수의 docstring은 *"정의가 존재하지 않는다"*고 적혀 있으나 **감사가 그 전제를 반증했다** —
정의는 CSV에 실재한다. **docstring을 코드 사실로 받은 것이 A의 원래 오류였고 정정됐다.**

### Gap 2 — detector

**실사이트용 area/endpoint detector가 존재하지 않는다.** fixture marker 기반 구현만 있다.

```
l1_engine.py:201-218  detect_area_signal      분기는 region_definition is None 뿐
l1_engine.py:221-231  detect_endpoint_signal  분기는 endpoint_definition is None 뿐
                      → task.region_signal_type / endpoint_signal_type 을 읽지 않는다
```

읽는 신호는 `[data-region]` · `[data-endpoint]` · `body[data-endpoint-reached]` ·
`input[type=password]` — **합성 마커다. 실사이트 DOM에는 없다.**

### 독립성 — 한쪽만 고치면 성립하지 않는다

```
Gap 1만 수정   정의는 도달하나 detector가 실 DOM에서 신호를 못 잡는다 → 결과 동일
Gap 2만 수정   detector는 작동하나 정의가 None이라 상수 False → 결과 동일
```

**∴ `REC-B-1~3` 단독 완료는 검증 가능한 결과를 내지 않는다. 중간 재수집을 금지한다**
(A 복구계획 개정 1). 중간 재수집은 실사이트 접속 예산만 소모한다.

### 선행조건 — `REC-B-8`

```
mapping_frozen_allowed()   A2 §1.9 규칙 P-2 가드가 구현돼 있으나 테스트에서만 호출된다.
                           프로덕션 호출 0 → '배선 복구'가 아니라 '프로덕션 최초 배선'이다.
```

**근거(A가 정정한 판)**: 실사이트에서는 wiring만으로 승격이 불가하므로 오염이 안 나지만,
**회귀 스위트가 도는 환경이 곧 fixture이고 거기서 가드가 없으면 검증 자체가 오염된다.**
C의 `CASE5b`가 이를 실증했다 — `CODEBOOK_PENDING` task가 endpoint 승격 + Path Freeze까지 도달.

### 감사 신규 발견 (A 채택)

```
F-1  detector 실사이트용 구현 부재            → REC-B-5 를 P0 승격
F-2  signal_type 이 어떤 판정에서도 미소비     → REC-B-8 = 프로덕션 최초 배선
F-3  가드가 QUERY 5/5 전멸 — 유일한 가능 축     → 입도 정밀화 우선 대상 (금지집합 불변)
F-6  signal_type = archetype 1:1 함수, 정보량 0 → detector 설계 범위를 3종으로 닫아준다
F-7  C-E 회수 규모 12건 → 1건                  → C-E1(설계규칙 11) / C-E2(가드 검출 1) 분리
§4   compute_depth() 는 complete-case 아님      → NED NULL 원인은 area 신호 미성립
                                                (실 결함은 l1_engine.py:600-616 area_index 미갱신)
```

---

## 5. NEXT SESSION — 착수 순서

**B는 다음 세션에서 먼저 구현하지 않는다.**

```
첫 행동      A의 R0 GO ticket 대기
R0 input     이 세션이 만든 measurement-recovery@2281c85
```

**R0 승인 뒤에도 즉시 detector 구현을 시작하지 않는다.** 순서:

```
1  dedicated labeler 배정        detector 코드 미열람 조건
2  labels sha256 freeze          detector 착수 전. 동결 해시를 게이트 판정문에 기재
3  B가 label-free 구현 과제 수령
4  wiring + detector 구현
5  fixture / offline validation
6  frozen DOM replay
```

**B는 라벨을 생성하지 않고 사전에 읽지 않는다.**

### 근거 — 왜 이 순서인가

실DOM에 detector를 돌려 **성립률을 보면서 detector를 고치면 원하는 비율이 나올 때까지
조율하게 된다.** outcome-blind 위반이다. 그래서:

```
합격 기준   DOM별 정확도
합격 기준 아님   총 성립 건수 · 비율
```

**"56개 중 N개에서 신호가 잡혔다"를 성공 지표로 쓰지 않는다. N이 크면 좋은 게 아니라
정답과 맞아야 좋은 것이다.**

라벨러를 C가 아닌 전용 워커로 두는 이유: C가 라벨링하면 **자기 라벨을 기준으로 검증**하게 되어
"생산자와 판정자가 이름으로 구분되지 않는" 결함이 재발한다. C는 **라벨 품질을 감사**한다.

### 회귀 스위트 — 두 종류가 다른 것을 본다

```
fixture   assurance/recovery/fixtures/run_partial_depth_fixtures.py   계약 준수 (A1 §1.4/§1.5)
          5케이스 · 현재 PASS 4 / FAIL 3 (CASE1, CASE4, CASE5b) · 엔진 src 경로 인자만 교체
replay    assurance/recovery/replay/  (신규, fixtures와 분리 필수)   detector 실효성
```

**분리 이유:** 픽스처는 **합성 마커**, 리플레이는 **실물 DOM**이다. 한 디렉터리에 섞이면
다음 사람이 둘의 증거력 차이를 못 본다.

### 게이트 판정문 의무 항목

```
이 게이트가 검증한 것        갭1 wiring · 갭2 area (리플레이 범위, s0 한정)
이 게이트가 검증하지 않은 것  갭2 endpoint — L1 step DOM 캡처 부재로 오프라인 검증 불가.
                            R8 실사이트 전까지 미검증
```

**두 번째 칸이 비면 PASS를 발행하지 않는다.**

---

## 6. REPLAY POPULATION — 단위를 반드시 붙인다

### 주 모집단

```
E001 mart reference = 56 FILES (dom.html) / 56 corresponding mart observations
```

`fact_landing_observation.json` 56행과 정확히 일치하므로 **리플레이 결과를 mart 행에 조인할 수 있다.**

### 제외

```
E001 quarantined     4 FILES        mart 밖. 넣으면 '어느 집합인지'가 흐려진다
E000                 9 FILES / 6 TARGETS (중복발사 3)
                     sensitivity auxiliary only — 주 결과 n=56 에 합치지 않는다
```

### 실측 근거 (이 세션에서 `find -name dom.html` 로 직접 계수)

```
E001  evidence 디렉터리   66 DIRS    w01 15 · w02 20 · w03 17 · w04 14
E001  dom.html           60 FILES   전부 l0a. 6개 디렉터리는 dom.html 없음(캡처 전 종료)
                                    60 = mart 참조 56 + 격리 4
E000  dom.html            9 FILES   전부 l0a. 고유 타깃 6, 중복발사분 3
```

### ⚠ `66`이 두 가지를 센다 — 단위 의무화의 계기

```
66   E001 evidence 디렉터리 수
66   C의 초기 집계 56 + 4 + 6  (E001은 FILE 단위, E000은 TARGET 단위로 섞임)
```

**다른 것을 세는 두 값이 우연히 같았고, 그 일치가 검증처럼 보였다.**
우리는 하루 종일 *"서로 다른 경로로 같은 값에 도달"* 을 3중 검증의 근거로 썼다.
**여기서는 우연이었다.**

> **두 경로가 같은 값을 냈을 때, 그 둘이 같은 것을 세고 있었는지 먼저 확인한다.**
> 모집단·계수 표기에는 항상 단위(FILE / TARGET / ROW / DIR)를 붙인다.

### 오프라인 리플레이 범위

```
검증 가능   s0(랜딩)에서의 area 신호 검출 — CASE1/CASE4 의 k=0 자리가 정확히 여기다
검증 불가   endpoint 검출 — L1 step DOM 캡처가 없다(l0a/l0c 만 존재)
```

**갭2를 반쯤 연다. 전부는 아니다.**

리플레이 산출의 지위: **detector 개발 신호이며 측정 결과가 아니다.**
mart에 들어가지 않고, claim registry에 등재되지 않고, 등급을 받지 않는다.
**이 지위를 산출 파일에 기계 판독 필드로 박는다**(`association_claims: 0` 형식).

---

## 7. REAL TARGET

```
REAL_TARGET = NO-GO
```

허용: **이미 동결된 DOM/evidence의 오프라인 리플레이만.** 네트워크 접속 0 · 신규 수집 0 ·
동결 evidence는 **원본 경로 참조만**(복사·이동·수정 금지, `ORIGINAL_E001 = READ_ONLY`).

향후 REAL_TARGET 조건 — **세 가지 전부** 필요:

```
1  B implementation
2  C independent validation
3  A explicit GO
```

금지집합(코드 레벨 차단, 불변): 로그인 · 회원가입 · 결제 · 구매 · 송금 · 예약확정 ·
메시지 발송 · OTP · 개인정보 입력 · CAPTCHA 우회.

---

## 8. LOCAL_UNPUSHED — 원격에 없는 의미 있는 작업

**워크트리 dirty: 없음.** `claude_b_*` 워크트리 20개 전부 uncommitted 0건.

아래는 **커밋되지 않은 변경이 아니라, git 추적 밖에 있는 산출물**이다.
`artifacts/`가 `.gitignore` 대상이라 발생한 구조적 항목이며, **커밋하지 않았다**(§3 수정금지 준수).

### 8.1 mart 데이터 파일 5종 — canonical에 포함되지 않음 ★

```
경로   .agent_worktrees/claude_b_analysis_current/artifacts/e001_real_marts/
파일   fact_landing_observation.json (56행) · fact_task_entry.json (31행)
       fact_interrupt_element.json (235행) · fact_criterion_result.json (0행)
       dim_certification.json (0행)
사유   82f631f 가 추적하는 것은 리포트·매니페스트 8개 파일뿐이다.
       → 82f631f 를 다른 곳에 체크아웃하면 리포트는 얻지만 데이터는 얻지 못한다.
완화   FROZEN_MART_MANIFEST.json 이 5파일의 sha256 과 row_count 를 보유하므로
       무결성 검증은 가능하다. 그러나 파일 자체는 이 워크트리에만 있다.
조치   다음 세션에서 A 판정 필요 — 추적 대상에 넣을지, 별도 보존 경로를 둘지.
       임의로 커밋하지 않았다.
```

### 8.2 raw evidence — 전량 git 추적 밖

```
E001  .agent_worktrees/claude_b_e001_worker_0{1..4}/artifacts/e001_w0{1..4}/
      1,243 files (w01 320 · w02 370 · w03 277 · w04 276)
E000  .agent_worktrees/claude_b_e000_real/artifacts/e000_fast_real/   180 files
사유   .gitignore 정책. 원본 evidence 는 애초에 저장소 밖 자산으로 설계됐다.
영향   리플레이 코퍼스(§6)의 입력이 바로 이 자산이다. 소실되면 오프라인 리플레이가 불가능해진다.
조치   삭제·이동 금지. 백업 정책은 A 판단 사항.
```

### 8.3 `claude-b/pa-shadow@b9433d5` — 원격에 없는 유일한 고유 커밋

```
커밋   exec(P-A-SHADOW): mapping layer + task codebook + source-only pilot mapping
내용   analysis/mapping_layer/ 6파일 · analysis/eda00,eda01/ 5파일 · pilot_mapping/ 1파일
사유   P-A는 우선순위 재조정(P-C > P-B > P-A QA only)으로 SHADOW 상태에서 정지했다.
       authoritative 아님. push 시 A 평면의 P-A 산출물과 혼동될 수 있어 보류했다.
조치   경로만 기록. 필요 시 A 지시로 push.
```

### 8.4 `E001_LAUNCH.md` — 메인 저장소 루트, 미추적

```
경로   /home/sieg/projects-wsl/ProjectFinal/E001_LAUNCH.md
내용   E001 4워커 발사 runbook (디렉터 요청으로 .md 화)
사유   운영 문서이며 연구 산출물이 아니다. refcohort-r1 브랜치를 오염시키지 않으려 미추적 유지.
```

### 8.5 소실 위험 없음으로 확인된 항목

```
claude-b/e001-worker-01..04   로컬 ref only. 고유 커밋 0 — 전부 222ef2c(push됨)를 가리킨다.
메인 저장소 refcohort-r1 dirty 10건   .gitignore·CLAUDE.md·tsconfig.json·SSOT/·manus/·ts/ 등
                                      세션 시작 시점부터 존재. B의 작업이 아니다. Pilot READ_ONLY 준수.
```

---

## 9. 이 세션에서 확립된 검증 규율 (다음 세션 인수인계)

오늘 검증 실수 7건이 나왔고 **두 유형**으로 압축됐다. 역할과 도구가 다른 세 행위자에게서
같은 형태가 나왔다 — 개인의 부주의가 아니라 **빠르게 판단할 때 무엇을 생략하는가**의 구조다.

```
유형 1  형식 미확인   값을 보고 형식을 확인하지 않고 비교·해석
유형 2  범위 확장     확인한 것을 확인하지 않은 것으로 일반화
```

### 교정 하나가 살아남은 4겹

```
1겹  교정이 지목된 자리에만 들어간다                       A 발견
2겹  지목된 자리를 다 고쳐도 생성 스크립트가 되살린다       B 발견 ★
3겹  검사가 '교정문 추가'만 보고 '원문 제거'를 안 본다      A 지적 · C 자진 등재
4겹  검사기가 '대상 부재'와 '위반 부재'를 같은 값으로 낸다   워커 자진 신고
```

**2겹이 핵심이다** — 숫자는 파일에서 읽게 만들어 손 타이핑을 없앴는데
**산문은 생성기 안에 상수로 박혀 있었다. 숫자에는 SSOT가 있고 서술에는 없었다.**

### 검사기 자신에 대한 규율

```
0건 보고에는 '0이 아닌 것도 잡을 수 있었다'는 증명이 붙어야 한다 — 대조군이 필요하다.
스캔 대상 파일 수만으로는 부족하다(대상 존재만 증명).
제외 규칙에도 대조군이 필요하다 — 제외는 검출력을 줄이는 방향으로만 작동한다.
```

**실증:** C의 스캐너 제외 규칙에 진짜 위반 6문장을 심었더니 **2/6만 검출**됐다.
문장 단위 메타 키워드가 문맥째 삼켰다. 매치 부위 국소 조건으로 바꿔 **6/6** 회복.
**결론(위반 0)은 불변, 증거력이 변경됐다 — 1/3 감도의 0 → 6/6 감도의 0.**

### 결론과 근거를 분리해 적는다

`REC-B-8`의 선행 지위는 유지됐으나 **근거는 교체됐다.**
**결론이 맞다고 근거도 맞은 것은 아니고, 근거를 고쳐도 결론은 유지될 수 있다.**
근거가 틀린 채로 맞는 결론은 다음번에 틀린 결론을 낸다.

### 가드는 발동시켜 검증한다

```
가드를 넣었다    선언
가드가 발동했다   검증
```

`mapping_frozen_allowed()`가 테스트에만 있던 것(F-2), 대조군 없는 0건,
제외 규칙의 1/3 감도 — **전부 앞의 것을 뒤의 것으로 읽은 결과다.**

---

## 10. 통신 · 평면

```
A  projectfinal-64   Authority / gates / 판정        control/landing-orchestrator
B  (이 세션)          Production / delivery           claude-b/*
C  projectfinal-ba   Independent Assurance / 검산    claude-c/assurance-current
```

- B는 `claude-b/*` 외 브랜치에 쓰지 않는다. A-writer 브랜치 쓰기 금지 유지.
- A↔B↔C 통신은 **git artifact로 남긴다.** 말로만 '완료'하지 않는다.
- 파일 버스: `.agent_bus/landing_v2/` (gitignored, idempotency_key dedup, 티켓 immutable)

---

## FINAL

```
B_HANDOFF_READY
handoff_branch:            handoff/landing-b-20260827
handoff_sha:               (이 커밋 — push 후 §2 형식으로 기록)
canonical_sha:             82f631f1e6bd3708bc8f95f0b8edcd90e22cef0d
recovery_audit_sha:        2281c853950d0c475c5d2c1678680b971c2804f4
collector_sha:             222ef2c28ed5971b3c9f8b07120b7627d2617476
remote_verified:           5/5 (17:46 KST, git ls-remote)
unpushed_meaningful_work:  4건 — §8.1 mart 데이터 5파일 ★ · §8.2 raw evidence 1,423파일
                                  · §8.3 pa-shadow@b9433d5 · §8.4 E001_LAUNCH.md
                           워크트리 uncommitted: 0
next_wait:                 R0_GO
REAL_TARGET:               NO-GO
```
