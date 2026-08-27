# ProjectFinal — SSOT v3.0 Cross-Service Task Entry Flow Pack

**버전**: v3.0  
**상태**: `AUTHORITY_CANDIDATE / NO_NEW_REAL_TARGET_RELEASE`  
**작성 기준시점**: 2026-08-28 00:49 KST 전후  
**목적**: v2.1 post-pilot recovery에서 드러난 대표기능 자동추론 병목을 제거하고, 동일 생활과업의 **교차서비스 Task Entry Flow 변이**를 본연구의 중심 construct로 재고정.

## 한 줄

> 페이지를 보고 대표기능을 추론하지 않는다. 수집 전에 생활과업을 동결하고, 서로 다른 모바일웹 서비스가 같은 과업을 **어디에, 어떤 이름과 control로, 어떤 reveal/조작순서와 깊이로 제공하는지** 측정한다.

## 설치 권장 위치

`research/landing_accessibility/docs/v3_0/`

## 권위 경계

- 이 pack은 **연구설계/측정계약 v3 권위 후보**다.
- 현재 A가 발행한 `V2_DIAGNOSTIC` 12-target release를 취소하거나 확장하지 않는다.
- `E001_FULL 59`를 자동 재개하지 않는다.
- v3 50-target main frame은 `mobile_web_eligibility` precheck와 A의 target-manifest freeze 전에는 REAL 수집 금지.

## 파일

1. `00_SSOT_v3.0_CROSS_SERVICE_FLOW.md` — 통합 연구권위
2. `01_TASK_FAMILY_TARGET_FRAME_v3.0.md` — 5 matched task family와 표본계약
3. `02_DATA_SCHEMA_v3.0.md` — v3 data lineage와 tables
4. `03_COLLECTION_MEASUREMENT_SPEC_v3.0.md` — L0/scroll/task-aware Scout/Replay
5. `04_FLOW_CODEBOOK_v3.0.md` — Flow token과 관측변수 codebook
6. `05_ANALYSIS_PLAN_v3.0.md` — CSEC/STFP 분석계획
7. `06_ABCD_ORCHESTRATION_PROTOCOL_v3.0.md` — A/B/C/D 역할·티켓·Git
8. `07_MIGRATION_EXECUTION_PLAN_v3.0.md` — 12 qualification → 50 main 전환
9. `08_CURRENT_STATE_BASELINE_v3.0.md` — 현 SHA/게이트/블로커
10. `09_DECISION_LOG_v3.0.md` — v3 결정문
11. `10_GLOSSARY_v3.0.md` — 용어집
12. `11_PROMPT_A_v3.0.md` / `12_PROMPT_B_v3.0.md` / `13_PROMPT_C_v3.0.md` / `14_PROMPT_D_v3.0.md`
13. `15_TICKET_PROTOCOL_SCHEMA_v3.0.json`
14. `CROSS_SERVICE_TASK_REGISTRY_50_v3.0.csv`
15. `CROSS_SERVICE_FLOW_PIVOT_v3.0.xlsx`
16. `MANIFEST_v3.0.json`

## v2.1에서 무엇을 보존하고 무엇을 바꾸는가

**보존**: 안전가드, REAL firewall, append-only evidence, DOM/AX/CSS/geometry, L0/L1 evidence, Scout→Freeze→Replay, KWCAG 독립축, obstruction 독립축, Human Final 상한, C 독립검증, D 비권위 연구 sandbox.

**변경**: Representative Function 자동분류를 critical path에서 제거. `Flow`가 primary construct, Depth는 derived scalar. 기존 59는 본표본이 아니라 robustness/usage benchmark. 12는 method qualification. 새 본표본은 5 matched task families × 10 services = 50 service-task units.
