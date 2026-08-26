<!-- INSTALLED-BANNER-START -->
> ## 현행 권위 포인터
>
> 이 파일의 지위는 `PROJECT_CONTEXT_DERIVED` 다. 아래 본문은 원본
> `06_PROJECT_CLAUDE_MD_v2.0.md` 의 **바이트 그대로**이며, 본문이 요약한 규칙의
> 정본은 항상 아래 문서들이다. 충돌하면 정본이 옳다.
>
> | 찾는 것 | 정본 |
> |---|---|
> | 목표·범위·단위·해석 | `docs/v2/00_SSOT_v2.0.md` |
> | 권위 서열 · v1 지위 · 기준선 SHA · `E001_V2_STARTED` | `docs/v2/EXECUTION_AUTHORITY.md` |
> | Gate 이름·통과조건·판정권한 | `docs/v2/PHASE_GATES.md` |
> | 측정 조작화 (NED/IED 경계, episode, dismiss 절차, scout budget) | `docs/v2/A1_MEASUREMENT_OPERATIONALIZATION.md` |
> | 상태값 어휘 · 논리↔물리 스키마 대응 | `docs/v2/A2_VOCABULARY_AND_SCHEMA_BINDING.md` |
> | evidence identity / manifest 계약 | `docs/07_EVIDENCE_MANIFEST_CONTRACT.md` (v1 산물, **현행 유효**) |
> | 문서 인덱스 | `docs/INDEX.md` |
>
> Root `/home/sieg/projects-wsl/ProjectFinal/CLAUDE.md` 의 환경규칙(venv·GPU·워크트리·품질게이트)을
> 그대로 상속한다. 이 파일은 그것을 덮어쓰지 않는다.
>
> 닫는 결함: `claude-md-and-evidence-contract-authority-framing`
<!-- INSTALLED-BANNER-END -->

# Landing Accessibility v2 — Claude Project Context

> 이 파일의 실제 설치 위치: `research/landing_accessibility/CLAUDE.md`
>
> Root `CLAUDE.md`의 환경규칙은 그대로 상속한다. 이 파일은 연구 하위프로젝트의 실행규칙만 정의한다.

## Current Authority

현재 연구의 최상위 실행권위:

`research/landing_accessibility/docs/v2/00_SSOT_v2.0.md`

하위:

1. `01_DATA_SPEC_v2.0.md`
2. `02_COLLECTION_MEASUREMENT_SPEC_v2.0.md`
3. `03_CRISP_DM_EXECUTION_PLAN_v2.0.md`
4. `04_GLOSSARY_v2.0.md`
5. `05_REPO_ORCHESTRATION_PLAN_v2.0.md`

기존 v1 문서는 역사·회귀검증용이며 v2와 충돌하면 v2가 우선한다.

## One-line Goal

고령층 실사용 서비스의 **모바일웹 첫 화면(L0)** 과 **대표기능의 첫 진입점(L1)** 에서:

- KWCAG 기반 접근성
- 대표기능 진입깊이
- popup/modal/광고/자동움직임 등 초기 방해

를 같은 프로토콜로 측정한다.

## Hard Scope

허용:

- L0 initial landing
- L1 shallow representative function entry

금지:

- 로그인 이후
- 본인인증 이후
- 결제/송금/예약 완료
- 회원가입
- full-task usability
- 실제 고령자 성공률 추정

## Three Independent Axes

1. KWCAG standard accessibility
2. entry friction
3. WA certification external reference

세 축을 단일 종합점수로 합치지 않는다.

## Depth

- NED
- IED
- MPFED = NED + IED
- ExcessDepth = MPFED - archetype median

`depth >= N = bad` 같은 임의 threshold 금지.

## Human Review

`HUMAN_FINAL_REVIEW_MAX = 5`

순서:

deterministic → semantic → VLM A → VLM B → arbiter → human ≤5.

남는 사례는 UNDETERMINED/ABSTAIN.

AI label은 human label이나 gold truth가 아니다.

## Evidence

Browser-native evidence 우선:

DOM + AX + CSS + geometry + screenshot + probe + action trace.

Screenshot-only 판단 금지.

## Reuse

- Source/entity/certification/provenance는 유지
- Pilot collector/probe는 기능 단위 selective port
- Pilot judgment 파일 단위 import 금지
- old C013 WIP `87a0464e...`는 UNVERIFIED. selective salvage 후 재감사

## Git Rules

- Pilot read-only
- main 직접 push 금지
- exact SHA independent audits before promotion
- `MAX_UNAUDITED_EXEC_CYCLES = 1`
- v2 executor branch는 `agent/landing-v2-exec`
- existing `agent/landing-exec`는 old WIP archive/checkpoint로 보존

## Current Stop

본수집 전에:

`READY_FOR_E001_V2`

에서 반드시 정지하고 Research Director에게 GO/HOLD 요청.

## Communication

micro-task마다 사용자에게 묻지 않는다.

Phase를 스스로 닫는다.

사용자 결정 요청은:

- A0 연구범위 충돌
- 해결 불가능한 P0
- READY_FOR_E001_V2

에서만 한다.
