# TIMEBOX 16:30 EXECUTION SSOT

**ID** `LA-TB-1630-20260827`
**AUTHORITY** `A0_RESEARCH_DIRECTOR_DECISION` — Research Director가 2026-08-27 직접 발령
**DEADLINE** 2026-08-27 16:30 KST
**STATUS** `FROZEN_FOR_TODAYS_EXECUTION`
**채택** Claude A (control plane, projectfinal-64), 2026-08-27 11:00 KST

---

## 0. 이 문서의 지위 — 무엇을 override 하고 무엇을 하지 않는가

이 문서는 **execution priority overlay** 다. 연구 SSOT를 **대체하지 않는다.**

### override 하는 것 (오늘 한정)

- 오늘의 실행 우선순위
- time budget
- collection completion target
- statistical MVP 범위
- stop / degradation rule
- A/B orchestration responsibility

### override 하지 않는 것 — 변경 금지

`00_SSOT_v2.0.md` 이하 권위서열, measurement semantics, evidence lineage,
target/task outcome-blindness, KWCAG semantics, NED/IED/MPFED 정의,
`PHASE_GATES.md` 의 Gate 통과조건.

**이 문서가 위 문서들과 충돌하면 위 문서들이 옳고, 충돌 자체가 이 문서의 결함이다.**
이 문서는 *언제 무엇을 할 것인가* 만 말하며 *무엇을 어떻게 측정하는가* 는 말하지 않는다.

`PHASE_GATES.md §4` (A0 SHADOW 정책)와 같은 층위의 A0 결정이며, 그 절을 대체하지 않고
그 뒤를 잇는다 — SHADOW 단계가 끝나고 REAL TARGET 이 열리는 조건을 이 문서가 정한다.

---

## 1. 오늘의 단일 목표

2026-08-27 16:30 KST 까지:

```
REAL TARGET evidence → analytic mart → core EDA → core statistical results
→ joint profile → claim-limited findings
```

**"더 완벽한 연구 harness" 는 오늘의 목표가 아니다.**

---

## 2. 최종 연구질문 (변경 없음)

고령층이 실제 사용하는 서비스의 초기 모바일웹 환경에서 (A) 표준화 접근성 장벽,
(B) 대표기능 진입 깊이, (C) 초기 화면 방해요소가 어떻게 관측되고, 이들이 서비스
단위에서 어떤 조합으로 함께 나타나는가.

**본 연구는 실제 고령자의 행동실패·포기·lostness·학습효과·AI intervention 효과를
직접 관측하지 않는다.**

## 3. 불변 측정범위

`L0_INITIAL_LANDING + L1_SHALLOW_REPRESENTATIVE_ENTRY` 유지.
로그인·결제·OTP·PII·CAPTCHA 우회 **금지.**

## 4. 필수 데이터 축

Service / Domain / InteractionArchetype.
L0: DOM · AX · computed style · geometry · screenshot · primary action · overlay/modal.
L1: Scout · Freeze · Replay · endpoint · NED · IED · MPFED.
KWCAG: PASS / FAIL / UNDETERMINED.
Obstruction: OverlayCoverage · PrimaryActionOcclusion · blocking_modal_count · forced_dismissal_count.

## 5. 핵심 파생변수

```
ExcessDepth_i = MPFED_i - median(MPFED within InteractionArchetype)
```

archetype 보정 없이 서로 다른 task 의 raw MPFED 를 직접 난이도 비교하지 않는다.

---

## 6. 표본 전략

전체 frozen eligible frame 을 향해 계속 수집한다. **13:30 KST 에 새 target 시작을 중단**하고,
그 시점까지 outcome-blind rule 로 완료된 관측을 오늘의 analytic frame 으로 freeze 한다.

| 등급 | joint-valid N |
|---|---|
| GREEN | >= 36 |
| YELLOW | 28 ~ 35 |
| RED_USABLE | 20 ~ 27 |
| PRELIMINARY 격하 | < 20 |

**표본 크기를 결과값에 따라 선택하지 않는다.**

## 7. E000 PIVOT

기존 outcome-blind E000 FAST 6개(`claude-b/e000-fast` @ `8197f11`)를 사용한다.
E000 이후 `collector SHA` · `protocol SHA` · `task frame` · `target frame` ·
`measurement schema` 가 **모두 불변**이면 E000 evidence 를 E001 batch-0 으로 canonical
reuse 할 수 있다. 하나라도 바뀌면 **영향 받은 target 만** production collector 로 재수집한다.

E000 은 L0 와 L1 이 **둘 다** 있어야 한다. systemic evidence/collector defect 가 없으면 PASS 다.
**WAF / CAPTCHA / site failure 는 systemic FAIL 이 아니다.**

## 8. 통계 계약 (필수분만)

- **Primary** `Spearman(MPFED, OlderRelevantKWCAGFailRate)`
- **Secondary** `Spearman(ExcessDepth, OverlayCoverage)` 또는 더 완결된 obstruction 변수 1개
- **Descriptive** InteractionArchetype 별 median / IQR / ECDF **필수**
- **Kruskal-Wallis** 실제 group N 이 충분할 때만
- **pairwise / Dunn / FDR** 시간이 남고 omnibus 가 의미 있을 때만

**인과표현 금지.**

## 9. Joint profile figure

X = `ExcessDepth` · Y = `OlderRelevantKWCAGFailRate` · point size = `OverlayCoverage` ·
facet = `InteractionArchetype`. WA certification 은 실제 variance 가 있을 때만 encoding.

**이 그림은 score 가 아니다.** score 로 부르지 않는다.

### 사분면 해석

| | 해석 | remediation 방향 |
|---|---|---|
| A | 얕고 표준 장벽 적음 | 본 관측범위 내 참조 설계 후보 |
| B | 얕지만 표준 장벽 큼 | UI / frontend |
| C | 표준 장벽 적으나 진입 깊음 | IA / representative-function exposure |
| D | 두 축 모두 큼 | 복합 |

**Y median = 0 이면 artificial median split 금지** — `barrier absent / barrier present` 로 기술한다.

## 10. Robustness MVP

필수: UNDETERMINED lower/upper bound · leave-one-archetype-out.
시간이 남으면: leave-one-service-out. 그 외는 backlog.

## 11. 인증(certification)

`CERTIFIED_CURRENT` variance 가 없거나 매우 작으면 **inferential test 금지**,
descriptive overlap 만 보고한다. **"인증제도가 놓쳤다" 라는 직접 결론 금지.**

## 12. AI 판정

deterministic first. AI 는 ambiguity 만. Reviewer A → Reviewer B → disagreement 만 Arbiter.
**14:00 까지 unresolved 이면 UNDETERMINED 로 freeze.**
human review 는 오늘 statistical pipeline 을 block 하지 않는다.

## 13. Remediation case

가능하면 최종 3개 실제 서비스. 원칙: evidence completeness 높음 · B/C/D 또는 서로 다른
mechanism · screenshot 으로 설명 가능 · remediation mechanism 이 서로 다름.

After 는 **validated outcome 이 아니라 evidence-based remediation prototype** 이다.
**"고령자 사용성이 향상됐다" 금지.**

---

## 14. 절대 축소 금지 (NON-NEGOTIABLE INTEGRITY)

```
outcome-blind target/task rule
manifest / hash
append-only
L0 + L1 (둘 다)
transport failure separation
UNDETERMINED semantics
forbidden external actions
```

이 7항은 time pressure 를 이유로 완화하지 않는다.

## 15. CUT LIST — 오늘 제거

open-ended governance hardening · **C014 closure 이후 신규 취약점 연구** ·
full mutation expansion · exploratory clustering · predictive ML · composite score ·
certification inferential comparison · all-pair subgroup analysis · full article ·
full deck design · human-final completion wait.

## 16. P0 STOP RULE

**C014 focused closure 이후 open-ended adversarial search 금지.**

C014 검증 범위는 다음 5개**만** 이다.

1. C013 dangling-grant exploit 차단
2. legitimate grant regression 없음
3. 기존 H-1~H-5 regression 없음
4. exec `bc0b7a0` unchanged
5. authority delta consistency

**새 exploratory attack generation 금지.** 단 focused 검사 중 **우연히** 실제
Category A/B/C systemic blocker 가 **직접 재현된** 경우에만 기록한다.

C014 exit condition: focused ADV PASS/blocking 0 **그리고** focused SSOT PASS/blocking 0.
**새 nonblocking recommendation 수와 무관하게 즉시 종료**하며, 새 control hardening
cycle 을 만들지 않는다.

## 17. GLOBAL HARD STOP — REAL_TARGET 전체 정지 사유

```
canonical source corruption
systemic evidence identity corruption
outcome-conditioned target contamination
systemic append-only corruption
forbidden external action occurring systemically
```

**이 5개만이다.** 그 외는 `record → isolate → continue`.
global systemic hard stop 이 걸려도 REAL_TARGET 만 fail-closed 하고 나머지 준비·분석은
계속한 뒤 artifact 에 기록한다.

## 18. 자동 degradation

| 시점 / 조건 | 조치 |
|---|---|
| 13:00 joint-valid 예상 < 28 | subgroup inference 제거 |
| 13:30 joint-valid 20~27 | 전체 association + descriptive 중심 |
| joint-valid < 20 | PILOT / PRELIMINARY 자동 격하 |
| 14:00 AI queue 잔존 | UNDETERMINED freeze |
| 15:10 pairwise 미완 | 제거 |
| 15:35 robustness 미완 | UNDET bounds 만 유지 |
| 16:00 remediation mockup 미완 | change specification + before evidence 만 보존 |

**통계 결과를 기다리게 만들지 않는다.**

---

## 19. TIME GATES

| 시각 (KST) | 게이트 |
|---|---|
| 11:10 | `P0_RELEASE` 목표 · `P0_STATUS.json` |
| 11:15 | integration-ready 목표 |
| 11:40 | E000 complete 목표 · `E000_STATUS.json` |
| 11:40~13:30 | E001 full-speed collection ⚠️ **13:50 으로 조정 — §19.1** |
| 12:15 | first collection checkpoint · `COLLECTION_CHECKPOINT.json` |
| 13:00 | minimum-N checkpoint · `COLLECTION_CHECKPOINT.json` |
| **13:30** | **NEW TARGET START STOP** · analytic collection frame freeze · `ANALYSIS_FRAME_FREEZE.json` |
| 14:00 | AI ambiguity cutoff — 잔여 UNDETERMINED |
| 14:10 | FROZEN MART · `MART_APPROVAL.json` |
| 15:10 | core EDA / statistics complete · `STATISTICS_STATUS.json` |
| 15:35 | robustness + joint classification complete |
| 16:00 | claim registry + remediation case inputs complete · `CLAIM_STATUS.json` |
| 16:20 | final result package complete |
| 16:25 | all analysis stop · `FINAL_FREEZE_PRECHECK.json` |
| **16:30** | **final freeze** |

## 20. 역할 분담

**Claude A (control plane)** — P0_RELEASE 이후 P0 engineering 을 종료하고 즉시
`E000 RELEASE OWNER` / `E001 INTEGRITY GOVERNOR` / `MART APPROVER` /
`STATISTICAL GOVERNOR` / `CLAIM GOVERNOR` 로 전환한다.
**collector code 구현 금지 · EDA code 구현 금지** — B 에게 맡긴다.

**Claude B (delivery plane)** — 수집·AI 판정·mart·EDA·통계 실행.

B 의 integration 이 오면 A 는 재구현하지 않고 다음만 확인한다:
exact SHA · tests · CR-002 · CR-003 · dom_order · document scope · L0+L1 enabled · contamination.

> P2 `document` 컬럼 문제는 **오늘 top-level-document MVP scope 로 정합 처리**하는 것을
> 허용한다. **iframe feature expansion 을 요구하지 않는다.**

## 21. 사용자 개입

Research Director 는 16:30 까지 자동 continuation 을 승인했다. **중간 승인 질문 금지.**

다음을 이유로 사용자 응답을 기다리지 않는다: site-level failure · CAPTCHA · WAF ·
UNDETERMINED · AI disagreement · sample shortfall · certification zero variance · nonblocking debt.

## 22. DO NOT DIG

C014 closure 이후 다음을 만들지 않는다:
new governance architecture · new attack taxonomy · new mutation suite ·
new proof obligation · new measurement definition.

**오늘의 KPI: real evidence · joint-valid N · mart · statistics · claims.**

---

## 23. 최종 산출물

**필수**

```
FROZEN_MART_MANIFEST.json
COLLECTION_COVERAGE.json
STATISTICAL_RESULTS.json / .csv
EDA_REPORT.md
JOINT_PROFILE figure
CLAIM_REGISTRY.md
LIMITATIONS.md
FINAL_RESULTS_SUMMARY.md
```

**가능하면** `REMEDIATION_CASES.md` + 3개 Before/After prototype asset.

## 24. Claim governance

15:35 부터 B 결과를 받아 `SUPPORTED` / `SUPPORTED_WITH_LIMITATION` / `EXPLORATORY` /
`NOT_SUPPORTED` 로 분류한다.

핵심 문장:

> **"이 서비스의 입구가 이렇게 생겼다는 것까지가 우리가 말할 수 있는 전부다."**

**actual elderly failure claim 금지.**
