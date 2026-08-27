# C_R0_CONTRACT_CHECK — R0_RECOVERY_CONTRACT_v2.1 (D-R0-01~32) contradiction check

**ticket** `T-A-R0-001` (DIRECTIVE, expected ACK — 본 문서는 C 의 contradiction check 산출)
**target** `control/landing-orchestrator@dad5c1f8d700e53bbf9e31eb4c8edeba8ab19c6f` `control/r0/R0_RECOVERY_CONTRACT_v2.1.md` + `control/clean0/RECONCILE_A_B_CLEAN0.md`
**producer** C (claude-fable-5, `claude-c/assurance-v21`) · production_modified false · labels 0

## §0 판정 요약

| 종류 | 건수 |
|---|---|
| D-R0-01~32 상호 **논리 모순** | **0** |
| 계약 **전제가 T1 과 다름** (FACT) | 1 (C1) |
| 계약이 **정하지 않아 데이터 본 뒤 정해질 위험** (outcome-blind 위반 경로) | 2 (C2, C3) |
| 명시 필요 gap (P2) | 3 (C4, C5, C6) |

**scoped HOLD 권고**: `W1-exactly-once key 명세`(C2) 와 `W2 UTILITY_ENTRY region 정의`(C3) 두 scope 만 A 의 DECISION 이 나올 때까지 HOLD.
그 외 (W1 guard/wiring, W2 rule-DT 나머지 6 archetype, W3, W4) 는 R0_GO 와 양립한다. 전체 R0 를 막을 이유는 없다.

---

## C1 (P1, FACT) D-R0-28 · RECONCILE §4 — "superseded retry 4" 는 duplicate launch 다

계약은 고아 4 observation 을 *superseded retry* 라 쓴다. raw 는 retry 가 아니다:
`batch_0001` 4건 `attempts=1`, run B 시작(05:14:38) < run A sealed(05:14:40), 두 사슬이 6~8초 간격으로 4 target 연속 교차, 이중 대상 = `batch_0001` 집합 전체 → **worker_02 프로세스 2개** (`C_CLEAN0_AUDIT §6.1`, `C-FACT_CORRECTION-210136`).

- 모집단 결론(n=56, mart target 56)은 **바뀌지 않는다.** 바뀌는 것은 §8 의 전제 — *"억제 경로가 실행된 적 없다"* 가 아니라 **접속 단위 억제가 없어 실사이트 접속이 4 target × 2회 발생했고 batch 원장만 2번째 commit 을 막았다.**
- 요구: D-R0-28 문구와 §8 인용문을 FACT_CORRECTION/SUPERSEDE 로 정정. D-R0-29 의 억제 테스트는 **관측된 실패 형태(같은 worker 파티션의 프로세스 2개 동시 기동)** 를 재현하는 cross-process 테스트를 포함할 것.

## C1b (P1, 분모) D-R0-28 "커버리지 56/56" 은 순환이다

E001 attempted **59**. mart 관측 **56**. **3 target 은 evidence 0 파일**(`SKIPPED_RETRY_EXHAUSTED`, 빈 stub 6 dir = 이 3 target × 2 attempt):

| target | archetype | service |
|---|---|---|
| wtg_ff3ee504792f6cfc | QUERY | samsung_internet_browser |
| wtg_2cd43b99c1ed87cf | UTILITY_ENTRY | samsung_notes |
| wtg_dd5061eb74e2d4d4 | FINANCIAL_ACTION_ENTRY | samsung_wallet |

"56/56" 은 mart 안의 target 을 mart 안의 target 으로 나눈 값이다. 계약의 모집단 표는 **59 attempted / 56 observed / 3 unobserved(이름·archetype 명기)** 로 써야 결측이 보인다.
세 건이 전부 같은 제조사 서비스라는 점은 **informative missingness** 후보(app-only/WAF)이며, QUERY 는 n=5→4 로 LOW_N 경계에 걸린다(SSOT §12 n 규칙). 분석 계약 단계에서 반드시 드러나야 한다.

## C2 (P1, 미정의) D-R0-29 idempotency key 의 `run_id` 어휘 — 계약대로면 억제가 영원히 발화하지 않거나, 정상 retry 를 죽인다

B 의 `A.2.1` 지적을 C 가 확인한다. 코드의 `run_id` 는 `batch.py:358` timestamp 합성(시도 1회 단위)이고 프로토콜 §10 의 `run_id` 는 수집 회차다. 계약은 어휘를 고정하지 않았다.

- 코드 run_id 를 key 에 넣으면 같은 target 재기동마다 새 key → `DUPLICATE_SUPPRESSED` 0 (D-R0-29 테스트 통과 불가).
- 회차 run_id 만 넣으면 **정상 retry(attempt 2)** 가 같은 key → 억제됨 → 수집 실패(과거 `batch_id 중복 판별이 정상 4워커 수집을 막는다` 사례와 동형).
- 요구 DECISION: `run_id` = A 가 발행하는 회차 id(ticket 단위 고정) · lock 은 target 단위 · lock 파일에 state(RUNNING/DONE/FAILED_RETRYABLE, attempts) 기록 · retry 는 `FAILED_RETRYABLE ∧ attempts < max` 일 때만 같은 lock 아래에서 허용 · lock 은 삭제하지 않음(B A.2 ④ 와 일치) · 억제 지점 = `batch.py:245 EvidenceRun.create` 이전(B A.2 ★ 와 일치, 네트워크 접속 이전).

## C3 (P1, 미정의) D-R0-07 + D-R0-09 + D-R0-16 ⇒ UTILITY_ENTRY 6/59 의 region 이 구조적으로 정의 없음

원천 CSV(9999857, blob `48e2492e…`)에서 UTILITY_ENTRY 6행은 **`region_signal_type = CODEBOOK_PENDING`** 이다(C_R0_QA S-10). 계약대로 lineage 를 그대로 보존(D-R0-07)하고 signal_type 을 실제 소비(D-R0-16)하면 이 6행은 region detector 입력이 없다 → area 신호 불성립 → **NED NULL by construction** → archetype 하나(n=6, ≥5 추론 후보군)가 depth 축에서 통째로 빠진다. D-R0-20 "region 관측 시 NED 보존" 과 D-R0-08 "lineage 59/59" 가 이 6행에서 만나지 않는다.

계약은 이 경우를 정하지 않았다. **데이터를 본 뒤 정하면 OBSERVATION→DEFINITION 위반**이므로 지금 DECISION 이 필요하다:
- (a) `01_DT §5 Branch U` 의 region 정의("function surface entry control 노출") + `DOM_AX_ROLE` 을 이 6행의 frozen definition 으로 채택 — 새 정의가 아니라 SSOT 에 이미 있는 정의의 적용. CSV 는 수정하지 않고 계약 문서에 override 표를 둔다.
- (b) CODEBOOK_PENDING 유지 → UTILITY_ENTRY NED 는 설계상 NULL 임을 지금 선언하고 분석 계약에 반영.
C 는 (a) 를 권고하되 선택은 A 의 것이다. **어느 쪽이든 R0 에서 닫아야 W2 착수가 outcome-blind 다.**

## C4 (P2, 명시) D-R0-15 marker 제거 ↔ 픽스처 코퍼스

`data-region/data-endpoint` 에 의존하는 파일: production tests/fixtures 6, C 회귀 픽스처 9/15. marker 경로를 제거하면 이 픽스처들은 전부 무효다. 계약은 "제거" 만 말하고 **픽스처 재작성(signal family 기반: role/form/URL)** 을 말하지 않는다. "테스트 전용 marker 경로 잔존" 은 D-R0-31 HOLD 조건 *synthetic marker 의존 잔존* 에 정확히 해당하므로 명시할 것. C 자신의 회귀 스위트도 재작성 대상 — C 가 수행한다.

## C5 (P2, 명시) D-R0-27/32 — offline holdout 이 검증할 수 있는 construct 의 범위

n=56 frozen evidence 는 **L0(랜딩) DOM 만** 있다(ORIGINAL_E001_READONLY §5). 따라서 독립 label 과 holdout 이 잴 수 있는 것은 **archetype 매핑(Layer O)** 과 **region 존재/hittable** 이다. **endpoint 는 offline label 불가** — D-R0-32 의 `unsafe endpoint false-positive = 0` 은 adversarial fixture + pilot 에서만 검증되며, PASS 문서의 "검증하지 않은 것" 절에 고정 항목으로 들어가야 한다.
또한 stratified holdout 에서 CONTENT_OPEN 3 / COMMUNICATION 4 / PLACE 4 는 holdout 에 1~2건만 남는다. `agreement ≥ 0.85` 를 pooled 로만 보면 ITEM_DETAIL(26/56=46%)이 지배한다 → **per-archetype agreement(n 병기) + macro 평균을 함께 보고**하도록 명시할 것. 숫자 자체는 engineering gate 라는 D-R0-32 단서는 적절.

## C6 (P2, 분석 예고) archetype n 이 관측 후 바뀐다

C1b 의 3건 미관측으로 주모집단 archetype n: ITEM_DETAIL 26 · FINANCIAL 10 · UTILITY 5 · QUERY 4 · COMM 4 · PLACE 4 · CONTENT 3. QUERY 는 SSOT §12 기준 n≥5 → **n=4 LOW_N** 으로 떨어진다(재수집 없으면). 분석 계약이 이를 사전 등재해야 "결과 보고 표본 고르기" 오해를 막는다.

## §7 일치 확인 (모순 없음)
D-R0-04 ↔ SSOT §7.2 ↔ DT Branch M/F · D-R0-11 7 archetype ↔ CSV 분포 · D-R0-20 ↔ `depth.py:166-186`(이미 구현) · D-R0-28 "빈 stub 6" ↔ C 재계수(파일 0) · D-R0-30 mirror ↔ 본 브랜치 `assurance/bus_mirror_c/` 로 이행 · RECONCILE §5 시각 자체정정 ↔ C P3 티켓(중복, 종결 가능).

## §8 이 검사가 확인하지 않은 것
D-R0-21~23 KWCAG frozen subset 의 실제 내용(33 criterion 표)과 evaluator 설계 정합 — W3 착수 후 · D-R0-19 BFS/Path Freeze 구현 상태 · D-R0-31 pilot 8~12 stratification 실현 가능성(archetype 7 중 CONTENT_OPEN 3 으로 가능은 함).
