# QA_CLAIM_LEDGER (C) — 2026-08-27T15:22:36+09:00

기준: .agent_bus/landing_v2/CLAIM_GOVERNANCE.md §2/§4 · 재계산 참조: /home/sieg/projects-wsl/ProjectFinal/.agent_worktrees/claude_c_assurance/research/landing_accessibility/assurance/out/QA_STAT_REPLAY.json, /home/sieg/projects-wsl/ProjectFinal/.agent_worktrees/claude_c_assurance/research/landing_accessibility/assurance/out/QA_MART_RECONCILIATION.json

집계: {'SUPPORTED_WITH_LIMITATION': 13, 'SUPPORTED': 6}

| file | status | issues | sentence |
|---|---|---|---|
| STATISTICAL_RESULTS.md | **SUPPORTED_WITH_LIMITATION** | §4-2 grade 태그 없음 | 계약이 지정한 분석이 계산 불가능하다는 사실을 보고하는 것이 오늘의 통계 산출물이다. |
| STATISTICAL_RESULTS.md | **SUPPORTED_WITH_LIMITATION** | §4-2 grade 태그 없음 | 오늘 산출된 등급은 **정의·기술통계·직접 관측**뿐이며, association 기반 상위 등급은 계산 대상 자체가 없어 존재하지 않는다. |
| STATISTICAL_RESULTS.md | **SUPPORTED** | - | [A]** L0 산출물을 보유한 56개 관측에서 방해요소 235건이 탐지됐다. |
| STATISTICAL_RESULTS.md | **SUPPORTED** | - | [A]** 56개 관측 중 22건(39.3%)에서 방해요소가 뷰포트를 완전히 덮었고, 6건은 겹침이 없었으며, 나머지 28건의 median은 0.0723이다. |
| STATISTICAL_RESULTS.md | **SUPPORTED_WITH_LIMITATION** | §4-2 grade 태그 없음 | 근거: max_overlay_coverage 3구간 분해 (median 단독 인용 금지 규칙 준수) |
| STATISTICAL_RESULTS.md | **SUPPORTED** | - | [A]** 닫기 컨트롤이 탐지되지 않은 상태에서 ESC/배경클릭으로 닫힌 경우 102건, 컨트롤이 탐지됐으나 닫기가 실패한 경우 38건, 컨트롤이 탐지되고 닫힌 경우 64건, 컨트롤이 탐지되지 않고 닫히지도 않은 경우 30건이다. |
| STATISTICAL_RESULTS.md | **SUPPORTED_WITH_LIMITATION** | §4-2 grade 태그 없음 | 분포 형태: **이봉 분포다** — 낮은 쪽 32건 · 가운데 2건 · 높은 쪽 22건으로 가운데가 비어 있다. |
| STATISTICAL_RESULTS.md | **SUPPORTED_WITH_LIMITATION** | §4-2 grade 태그 없음 | median 단독 인용은 오도한다**: 중앙값은 어느 봉도 대표하지 않는다. |
| STATISTICAL_RESULTS.md | **SUPPORTED_WITH_LIMITATION** | §4-2 grade 태그 없음 | 유형 분포를 인용할 때 UNKNOWN을 각주로 빼면 실측 강도가 과대표시된다. |
| STATISTICAL_RESULTS.md | **SUPPORTED_WITH_LIMITATION** | §4-2 grade 태그 없음 | ○ 시각적 닫기 컨트롤이 탐지되지 않은 상태에서 ESC/배경클릭으로 닫힌 경우가 102건이다 |
| STATISTICAL_RESULTS.md | **SUPPORTED** | - | [A]** 59개 서비스 전수를 시도해 대표기능 진입 깊이(MPFED)가 산출된 것은 0건이다. |
| STATISTICAL_RESULTS.md | **SUPPORTED** | - | [A]** 본 연구 계약이 대표기능 endpoint로 인정하지 않는 archetype에서 gate에 도달해 진입 깊이가 정의상 산출되지 않은 경우가 11건이다. |
| STATISTICAL_RESULTS.md | **SUPPORTED** | - | [A]** gate 종류 판별이 UNDETERMINED로 떨어져 fail-closed 규칙이 endpoint 승격을 거부한 발화가 8건이고, 그중 실제로 결과를 바꾼 것은 1건이다. |
| STATISTICAL_RESULTS.md | **SUPPORTED_WITH_LIMITATION** | §4-2 grade 태그 없음 | 오류를 먼저 적고, 그것이 산출물에 남지 않은 경위를 나중에 적는다. |
| STATISTICAL_RESULTS.md | **SUPPORTED_WITH_LIMITATION** | §4-2 grade 태그 없음 | "이 단계의 산출물을 만드는 코드가 실재하는가" |
| STATISTICAL_RESULTS.md | **SUPPORTED_WITH_LIMITATION** | §4-2 grade 태그 없음 | — 상류 산출물의 존재를 하류 단계의 존재로 추론하지 않는다. |
| STATISTICAL_RESULTS.md | **SUPPORTED_WITH_LIMITATION** | §4-2 grade 태그 없음 | 마지막 건은 오늘의 통계 산출물이 계산 불가능해진 직접 원인이다. |
| STATISTICAL_RESULTS.md | **SUPPORTED_WITH_LIMITATION** | §4-2 grade 태그 없음 | ／ C → A ／   판정 근거가 사실과 다름 ·   초판이 축 A 산출을 전제한 오류 ／ |
| STATISTICAL_RESULTS.md | **SUPPORTED_WITH_LIMITATION** | §4-2 grade 태그 없음 | 판별 키를   중복으로 바꿔 지시의 의도(이중 수집 탐지)는 지켰다. |

> 최종 headline 판정은 A. C 는 §2 금지 스캔·grade 태그·N 병기·수치 일치만 판정한다. `NUMBER_NOT_IN_C_REPLAY` 는 A 가 인용하는 숫자가 C 재계산값 집합에 없다는 뜻이며, 반올림 차이일 수 있어 개별 확인 대상이다.