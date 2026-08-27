# Measurement Recovery Roadmap v2.1

**기준 시각**: 2026-08-27 20:20 KST  
**목표 1**: 00:30 KST 전후 `REAL_START_READY`  
**목표 2**: 02:00~03:00 KST planned analysis + independent assurance 완료

---

## 1. 전체 판단

00:30까지 **범용 시스템 완성**은 목표가 아니며 불필요하다.

00:30까지 필요한 것은:

> 이 59-target 연구 frame에서 실제 소스를 다시 뽑아도 measurement semantics가 깨지지 않는다는 충분한 안정성과 독립 검증.

현재 결함은 이미 상당 부분 특정되어 있어, 신규 연구설계보다 **복구와 연결**이 주 업무다.

### 가장 어려운 세 지점

1. representative function / endpoint real-site detector
2. guard granularity를 안전성 훼손 없이 candidate-level로 전환
3. KWCAG frozen subset evaluator를 evidence-linked production path로 연결

---

## 2. Phase C0 — CLEAN-0

**시간**: 20:20~20:45, 최대 25분

### A

- remote exact heads 재확인
- new v2.1 SSOT current candidate 설치
- ORIGINAL_E001 read-only 재선언
- authority / supersession map 생성
- `DEFINITION / IMPLEMENTATION / OBSERVATION / ANALYSIS / DECISION` assertion type 도입
- R0 ticket 발행

### B

- 코드 변경 전 gap inventory 재확인
- 2281c85의 G1~G5를 현재 source에서 재현
- actual evidence local path와 hash/count manifest 작성
- stale/default task path 목록화

### C

- A/B의 CLEAN 산출 독립 감사
- old docstring / stale prose가 코드 사실로 소비되는 경로 탐지
- bus exactly-once / duplicate launch 위험 확인

### Exit

`CLEAN0_ACCEPTED`

새 설계 논쟁 금지. 25분이 넘어가면 polish를 이월하고 blocker만 남긴다.

---

## 3. Phase R0 — Recovery Contract Freeze

**시간**: 20:45~21:05

A가 다음을 확정한다.

- guard candidate/state-level 원칙
- RF-DT v2.1
- NLP fallback 사용 조건
- task 59 field lineage contract
- real-site signal families
- frozen KWCAG subset evaluator scope
- Axis C page-level vs task-level 구분
- label producer independence
- pilot acceptance gate

C가 contract contradiction을 즉시 검사.

B는 이 시점까지 detector tuning을 시작하지 않는다.

Exit: `R0_GO`

---

## 4. Phase L0 — Independent Label Freeze

**시간**: 21:05~21:40

A가 독립 labeler worker들을 병렬로 배치한다.

권장:

- 4~6 subworkers
- 56 frozen DOM/evidence stratified partition
- 결과값이 아니라 DOM/AX/evidence만 읽음
- 각 row에 evidence reference 필수

A가 통합 후 label file SHA256 동결.

calibration / holdout split 고정.

B와 C는 label을 생산하지 않는다.

---

## 5. Phase I1 — Parallel Implementation

**시간**: 21:05~22:30

L0와 일부 병렬 가능.

### B-W1 — Guard + Wiring

- target-level screen_candidates 제거/축소
- candidate-level action mask
- auth entry conditional rule
- task id / region / endpoint / signal type 59/59 전달
- no credential / transaction continuation 유지

### B-W2 — Representative Function Detector

- DOM_AX_ROLE
- FORM_STRUCTURE
- URL_PATTERN
- required MEDIA/GATE path
- no synthetic data-region/data-endpoint requirement

Detector semantic calibration은 label calibration 공개 이후 시작.

### B-W3 — KWCAG Evaluator

- frozen older-relevant subset only
- criterion applicability
- evidence binding
- deterministic evaluator first
- UNDETERMINED preservation

### B-W4 — Axis C / Mart Integration

- overlay raw reuse
- semantic interrupt classifier completion
- task binding 이후 primary-action occlusion 연결
- mart schema / missingness checks

### C parallel

- implementation diff read-only audit
- guard safety adversarial cases
- endpoint false-positive tests
- criterion semantics audit
- no output-based threshold tuning check

---

## 6. Phase V1 — Offline Replay Validation

**시간**: 22:30~23:15

주 모집단:

- E001 mart referenced frozen DOM/evidence 56

별도 sensitivity:

- E000 6 targets

검증:

- task definition lineage completeness
- mapping coverage / abstention
- holdout agreement
- endpoint detection
- partial NED preservation
- login/CAPTCHA guard behavior
- KWCAG evaluator decision coverage
- obstruction consistency

C가 holdout 및 adversarial replay.

### Stop conditions

- unsafe action path 가능
- synthetic marker 의존 잔존
- endpoint definition과 observed endpoint 혼동
- label leakage
- evidence identity mismatch
- duplicate real launch risk

---

## 7. Phase P1 — REAL_TARGET Stratified Pilot

**시간 목표**: 23:15~23:50

8~12 targets.

가능하면 일곱 archetype을 모두 포함.

목적:

- 실제 live DOM drift 확인
- guard 실제 behavior
- detector real-site signal
- KWCAG evaluator runtime
- evidence completeness
- task manifest / replay

파일럿 결과가 좋고 나쁨은 release 기준이 아니다.

systemic measurement mismatch가 있는지가 기준이다.

---

## 8. Phase G1 — Acceptance / Minimal Fix

**시간**: 23:50~00:15

A가 B completion + C assurance를 reconcile.

새 연구설계 금지.

blocking만 수정.

Exit:

- `REAL_START_READY`
- 또는 `PARTIAL_READY_WITH_BLOCKER`

---

## 9. 00:15~00:30 — Start Window

`REAL_START_READY`이면 full 59 run 발사.

4 worker 병렬.

exactly-once ticket / target lock 사용.

C는 streaming QA.

A는 measurement semantics를 바꾸지 않는다.

---

## 10. 00:30~01:30 — Full Collection

Expected 30~60분.

수집되는 즉시 mart incremental staging은 가능하나 final mart freeze 전 분석 claim 금지.

C는 worker별 failure/UNDET/guard skew를 감시.

---

## 11. 01:00~02:15 — Mart + Statistics

B:

- service-level summary
- KWCAG rates
- NED/IED/MPFED
- ExcessDepth
- Axis C variables
- joint-valid
- descriptive statistics
- planned association
- robustness

C:

- independent recomputation
- denominator check
- archetype imbalance
- missingness
- holdout detector quality
- claim-boundary audit

---

## 12. 02:00~03:00 — Final Scientific Synthesis

A:

- ACCEPT / DOWNGRADE / NOT_COMPUTABLE
- headline claim grade
- presentation-ready figures list
- limitations

B:

- reproducible tables/figures

C/Fable:

- scientific critic final memo
- strongest supportable claim
- claims to prohibit

---

## 13. 시간 추정

### Minimum path

약 2시간 50분~3시간 20분.

CLEAN이 짧고 detector가 기존 정의에 바로 붙으면 23:20~23:45에 REAL_START_READY 가능.

### Expected

약 3시간 40분~4시간 10분.

00:00~00:30 READY가 가장 현실적.

### Max / blocker path

5~6시간.

대표기능 detector holdout 성능이 낮거나 KWCAG evaluator가 criterion semantics 문제를 내면 00:30을 넘길 수 있다.

이 경우 full run을 강행하지 않고 stratified pilot + offline validated subset으로 멈춘다.

---

## 14. 가장 중요한 관리 원칙

- 현재는 새 아이디어를 만드는 시간이 아니라 measurement contract를 실제 코드에 붙이는 시간
- CLEAN은 25분 이상 쓰지 않음
- 한 blocker를 두 agent가 중복 구현하지 않음
- B가 만든 것을 B가 승인하지 않음
- C가 gold label을 만들지 않음
- A가 empirical fact를 선언으로 덮지 않음
- branch name 대신 exact SHA
- local artifacts는 Git manifest로 투명하게 노출
