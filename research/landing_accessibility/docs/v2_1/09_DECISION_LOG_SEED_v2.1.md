# Decision Log Seed v2.1

이 문서는 CLEAN-0에서 A가 exact evidence를 다시 확인한 뒤 ACCEPT / MODIFY / REJECT를 표시할 seed다.

## D-01 — 연구 목적

**Decision**: 범용 자동 접근성 시스템 개발을 목표로 하지 않는다.

**Reason**: 연구 frame에서 검증 가능한 관측 데이터 생산이 목적.

## D-02 — ORIGINAL_E001

**Decision**: READ_ONLY. 덮어쓰기·합치기 금지.

## D-03 — Guard granularity

**Decision**: target-level `login present => Scout kill` 폐기. candidate/state-level safety.

## D-04 — Login semantics

**Decision**: 로그인 control 존재 != endpoint. actual chosen path에서 login/auth gate 도달 시에만 gate observation.

## D-05 — Credential semantics

**Decision**: credential input 및 login submit 금지 유지.

## D-06 — CAPTCHA

**Decision**: passive presence != terminal. active visible challenge that blocks chosen path => CAPTCHA terminal. solve/bypass 금지.

## D-07 — Purchase/payment

**Decision**: control presence 관측 허용. transaction activation 금지.

## D-08 — Representative function mapping

**Decision**: business domain prior + observed DOM/AX task-shape verification의 2단계.

## D-09 — RF-DT fallback

**Decision**: Rule DT first. ambiguity만 NLP embedding/cross-encoder. 시각 ambiguity만 VLM.

## D-10 — Gold labels

**Decision**: B와 C 모두 label producer 금지. A가 independent labeler worker 조직.

## D-11 — Task definition

**Decision**: 새로 만들지 않고 existing 59/59 definitions의 wiring을 복구.

## D-12 — Real-site detector

**Decision**: synthetic data-region/data-endpoint marker requirement 제거. frozen signal family 실제 구현.

## D-13 — KWCAG

**Decision**: frozen older-relevant subset만 production evaluator 구현. 연구 중 subset 확대 금지.

## D-14 — Axis C

**Decision**: page-level overlay geometry 우선 재사용. primary-action occlusion은 task binding 후 검증.

## D-15 — Composite score

**Decision**: 세 축을 하나의 senior accessibility score로 합치지 않는다.

## D-16 — CLEAN

**Decision**: 삭제 중심 청소 금지. 25분 authority/semantic cleaning only.

## D-17 — Communication

**Decision**: 3분 heartbeat. 모든 중요 요청은 immutable ticket.

## D-18 — Truth

**Decision**: exact artifact/code/runtime > reproducible computation > frozen definition > SSOT decision > prose/docstring > agent narrative.

## D-19 — Git

**Decision**: 완료는 pushed exact SHA가 있어야 함. local artifacts는 Git-tracked hash manifest 필수.

## D-20 — Duplicate execution

**Decision**: real target launch는 idempotency key와 target lock으로 exactly-once.

## D-21 — Deadline

**Decision**: 00:30 REAL_START_READY 목표. 시간 초과 시 polish를 버리되 measurement validity는 버리지 않는다.

## D-22 — Final analysis

**Decision**: planned analysis만 수행. 계산 불가능하면 새 association으로 사후 대체하지 않는다.
