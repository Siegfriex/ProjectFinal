# CRISP-DM 실행계획 v2.0

---

## Phase 1 — Business Understanding

완료조건:

- 문제정의 확정
- L0/L1 범위 확정
- 분석축 A/B/C 확정
- 금지 주장 확정

현재: **동결 가능**

---

## Phase 2 — Data Understanding

### EDA-00

Frame & Provenance Audit.

확인:

- source 261
- APP/RETAIL
- panel 17
- entity/alias/membership
- orphan
- source hash
- certification snapshot

### EDA-01

Wiseapp Source Structure.

- panel별 N
- entity 반복출현
- source domain
- panel-normalized rank
- panel appearance count

### EDA-02

Domain / Task Mapping.

- Business Domain
- Interaction Archetype
- representative endpoint
- ambiguous mapping

---

## Phase 3 — Data Preparation

1. C013에서 web eligibility/URL 작업 선택 salvage
2. final web target
3. representative task mapping
4. certification join
5. L0/L1 feature schema
6. evidence identity
7. mapping/materialization layer

기존 `state/*.parquet`는 그대로 둔다.

---

## Phase 4 — Modeling

### M0 — Target/Task Mapping

rule + source context + embedding + AI review.

### M1 — KWCAG Measurement

raw browser feature → criterion opportunity → verdict.

### M2 — Popup/Obstruction

DOM/CSS/geometry/text/visual → interrupt type + blocking.

### M3 — Entry Path

landing → activation trace → endpoint.

### M4 — Joint Profile

서비스별:

- KWCAG
- MPFED
- overlay/modal
- auth
- certification

### Optional M5

표본이 충분하면 비지도 군집탐색.

주 분석 아님.

---

## Phase 5 — Evaluation

### 측정 품질

- evidence completeness
- decision coverage
- AI review rate
- reviewer agreement
- abstention rate
- human escalation ≤5

### 통계

Depth:

- median/IQR/mode/ECDF

Archetype:

- Kruskal–Wallis 또는 permutation

Association:

- Spearman

Binary:

- Fisher exact

Robustness:

- leave-one-service-out
- leave-one-archetype-out
- UNDETERMINED stress

---

## Phase 6 — Deployment

최종 산출:

- analysis marts
- figures
- evidence cards
- publication claim registry
- 기사/보고서 지원

모든 주요 문장은 numerator/denominator와 artifact에 역추적 가능해야 한다.

---

# 실행 Phase Gate

## P0 — V2 Refreeze

- v2 docs 설치
- project CLAUDE.md 설치
- v1 실행지침 superseded 표시
- audit
- promotion

## P-A — Analysis Foundation + Task Codebook

- EDA-00/01
- mapping layer
- Business Domain / Interaction Archetype
- endpoint codebook
- 10~15건 pilot mapping

## P-B — Target / Task Frame

- C013 selective salvage
- web eligibility
- URL
- final target
- task mapping
- certification join 준비

## P-C — L0/L1 Engine

- Pilot feature selective port
- popup detector
- motion
- primary action
- scout/replay
- KWCAG subset
- AI review cascade

## P-D — E000_V2

- smoke
- failure injection

## P-E — READY_FOR_E001_V2

- exact SHA freeze
- two independent audits
- blocking debt 0
- STOP

사용자 GO 이후:

## P-F — E001_V2

Main collection.

## P-G — Adjudication

deterministic → AI A/B → arbiter → HUMAN_FINAL ≤5.

## P-H — EDA / Statistics

EDA-03 onward.

## P-I — Publication

claim registry, charts, evidence case cards.
