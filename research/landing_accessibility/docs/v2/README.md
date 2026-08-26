# ProjectFinal Landing Accessibility v2 — DOCS Pack

이 묶음은 **고령층 실사용 모바일웹 초기진입 접근성 분석 v2**의 실행 기준 문서다.

핵심 피벗:

> `LANDING_ONLY`에서 `L0 최초 랜딩 + L1 대표기능의 얕은 진입경로`로 확장.

단, 범위는 깊어지지 않는다. 로그인 이후, 본인인증 이후, 결제·송금·예약 완료, 회원가입, full task completion은 제외한다.

읽는 순서:

1. `00_SSOT_v2.0.md` — 무엇을 왜 측정하는지. 가장 높은 실행 권위.
2. `01_DATA_SPEC_v2.0.md` — 데이터 표와 변수 정의.
3. `02_COLLECTION_MEASUREMENT_SPEC_v2.0.md` — 웹에서 무엇을 어떻게 수집·측정하는지.
4. `03_CRISP_DM_EXECUTION_PLAN_v2.0.md` — 실제 분석 단계.
5. `04_GLOSSARY_v2.0.md` — 쉬운 용어집.
6. `05_REPO_ORCHESTRATION_PLAN_v2.0.md` — Git/branch/worktree/감사 운영.
7. `06_PROJECT_CLAUDE_MD_v2.0.md` — `research/landing_accessibility/CLAUDE.md`에 넣을 프로젝트 전용 지침.
8. `07_CLAUDE_FIRST_SESSION_PROMPT_v2.0.md` — 다음 Claude Code 첫 세션에 그대로 넣을 프롬프트.

## 문서 권위

`00_SSOT_v2.0.md`가 분석 목표·범위·단위·핵심 해석에 대한 최상위 문서다.

하위 문서가 SSOT와 충돌하면 SSOT가 우선한다.

기존 v1 문서와 Pilot은 삭제하지 않는다. 이들은 이력·회귀검증·근거 참조용이다. **v2 실행에는 v2 문서만 사용한다.**

## 현재 시작점

- authoritative verified baseline: `research/landing-accessibility-main @ 5a9015d1e95b15304aaf53a73efb475934610b82`
- preserved unverified WIP: `agent/landing-exec @ 87a0464e8159d5526069d5e654e648b0dae506ca`
- E001 / 본수집: 시작하지 않음
- Pilot: read-only
