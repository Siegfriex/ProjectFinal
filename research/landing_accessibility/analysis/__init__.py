"""P-H — EDA/Statistics 산출 스켈레톤 (`03_CRISP_DM_EXECUTION_PLAN_v2.0.md` Phase 5/6).

이 패키지는 **SHADOW_PREPARATORY** 산출물이다 (`PHASE_GATES.md §4.3`).
실제 서비스 접근성 결과를 만들지 않는다 — synthetic/fixture 데이터로만 스키마와
파이프라인을 검증한다. P-C `agent/landing-pc-fixture`의 AI review cascade
(`ai_review.py` — 이 워크트리에는 아직 merge되지 않았다)가 산출할 `fact_ai_adjudication`
행 스키마를 **입력 계약**으로 소비할 뿐, cascade 자체를 재구현하지 않는다.

- `marts/`  — fact/dim 테이블 스키마 + 빌드 스크립트 (목표 1)
- `eda/`    — EDA-03~08 스크립트 (목표 2)
- `deliverables/` — 산출물 템플릿 생성기 (목표 3)

`provenance.py`가 모든 산출물에 공통으로 찍는 SHADOW provenance 블록을 만든다.
"""
