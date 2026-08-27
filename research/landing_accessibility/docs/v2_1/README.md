# Landing Accessibility v2.1 — Post-Pilot Recovery Pack

이 문서팩은 2026-08-27 E001 파일럿 종료 후 확인된 결함과 결정사항을 반영해, 기존 v2 연구를 삭제·재설계하지 않고 **측정 가능성 복구 → 검증 → 실제 수집 → 분석**으로 이어가기 위한 실행권위 후보 문서팩이다.

## 핵심 전제

- 이 프로젝트의 목적은 **범용 자동 접근성 측정 제품**을 만드는 것이 아니다.
- 목적은 고령층 실사용 서비스 frame의 모바일웹 초기진입을 동일 프로토콜로 측정해 연구 데이터와 분석을 만드는 것이다.
- 자동화는 연구 측정의 재현성·일관성·증거보존을 위한 수단이다.
- ORIGINAL_E001 파일럿은 읽기 전용으로 보존한다.
- 기존 v2 문서, Pilot, evidence를 삭제하지 않는다.

## 권장 설치 위치

`research/landing_accessibility/docs/v2_1/`

## 파일

1. `00_SSOT_v2.1_POST_PILOT_RECOVERY.md` — 새 통합 SSOT
2. `01_REPRESENTATIVE_FUNCTION_MAPPING_DT_v2.1.md` — 대표기능 매핑 Decision Tree + NLP fallback
3. `02_MEASUREMENT_RECOVERY_ROADMAP_v2.1.md` — 오늘 밤 실행 로드맵과 시간창
4. `03_ABC_ORCHESTRATION_PROTOCOL_v2.1.md` — A/B/C 통신·티켓·Git·우선순위 규약
5. `04_PROMPT_A_INITIAL.md` — Claude A 새 세션 초기주입
6. `05_PROMPT_B_INITIAL.md` — Claude B 새 세션 초기주입
7. `06_PROMPT_C_FABLE_INITIAL.md` — Claude C/Fable 새 세션 초기주입
8. `07_TICKET_PROTOCOL_SCHEMA_v2.1.json` — 티켓 필드 규격
9. `08_CURRENT_STATE_BASELINE_v2.1.md` — 현 시점 SHA와 파일럿 기준선
10. `09_DECISION_LOG_SEED_v2.1.md` — 이번 재개 시 고정할 결정 로그

## 설치 후 첫 행동

A가 새 SSOT와 protocol을 current authority candidate로 설치하고 CLEAN-0을 25분 이내에 종료한 뒤, A/B/C가 동일한 exact-SHA 기준선에서 3분 heartbeat loop를 시작한다.
