# QA_CLAIM_LEDGER (C) — 2026-08-27T16:26:18+09:00

기준: .agent_bus/landing_v2/CLAIM_GOVERNANCE.md §2/§4 · 재계산 참조: /home/sieg/projects-wsl/ProjectFinal/.agent_worktrees/claude_c_assurance/research/landing_accessibility/assurance/out/QA_STAT_REPLAY.json, /home/sieg/projects-wsl/ProjectFinal/.agent_worktrees/claude_c_assurance/research/landing_accessibility/assurance/out/QA_MART_RECONCILIATION.json

집계: {'SUPPORTED_WITH_LIMITATION': 13, 'MISMATCH': 1}

| file | status | issues | sentence |
|---|---|---|---|
| FINAL_RESULTS_SUMMARY.md | **SUPPORTED_WITH_LIMITATION** | §4-2 grade 태그 없음 | 실제 거부** 1건 (E-6b 구속) — gate kind가 UNDETERMINED로 **도달**했고 fail-closed 규칙이 승격을 막았다. |
| FINAL_RESULTS_SUMMARY.md | **SUPPORTED_WITH_LIMITATION** | §4-2 grade 태그 없음 | 이 구분이 오늘 산출물 전체의 성격을 정한다 — 빈 자리는 실패의 흔적이 아니라 측정되지 않은 것을 측정된 것처럼 만들지 않은 결과다. |
| FINAL_RESULTS_SUMMARY.md | **SUPPORTED_WITH_LIMITATION** | §4-2 grade 태그 없음 | 충분원인이 둘이고 서로 겹치지 않으므로** MPFED가 산출될 경로는 애초에 없었다. |
| FINAL_RESULTS_SUMMARY.md | **SUPPORTED_WITH_LIMITATION** | §4-2 grade 태그 없음 | 0** — J3(MPFED 산출)이 충족되지 않았다. |
| FINAL_RESULTS_SUMMARY.md | **SUPPORTED_WITH_LIMITATION** | §4-2 grade 태그 없음 | L0 산출물을 보유한 56개 관측에서 방해요소 235건이 탐지됐다. |
| FINAL_RESULTS_SUMMARY.md | **MISMATCH** | NUMBER_NOT_IN_C_REPLAY: ['0.25', '0.75']; §4-2 grade 태그 없음 | 겹침 분포는 **양극**이다 — 완전히 덮은 관측 22건(39.3%) · 겹침 없음 6건 · 가운데 구간(0.25~0.75) 2건뿐. |
| FINAL_RESULTS_SUMMARY.md | **SUPPORTED_WITH_LIMITATION** | §4-2 grade 태그 없음 | median 단독 인용은 오도한다. |
| CLAIM_REGISTRY.md | **SUPPORTED_WITH_LIMITATION** | §4-2 grade 태그 없음 | L0 산출물을 보유한 56개 관측에서 방해요소 235건이 탐지됐다. |
| CLAIM_REGISTRY.md | **SUPPORTED_WITH_LIMITATION** | §4-2 grade 태그 없음 | 56개 관측 중 22건(39.3%)에서 방해요소가 뷰포트를 완전히 덮었고, 6건은 겹침이 없었으며, 나머지 28건의 median은 0.0723이다. |
| CLAIM_REGISTRY.md | **SUPPORTED_WITH_LIMITATION** | §4-2 grade 태그 없음 | metric**: max_overlay_coverage 3구간 분해 (median 단독 인용 금지 규칙 준수) |
| CLAIM_REGISTRY.md | **SUPPORTED_WITH_LIMITATION** | §4-2 grade 태그 없음 | 닫기 컨트롤이 탐지되지 않은 상태에서 ESC/배경클릭으로 닫힌 경우 102건, 컨트롤이 탐지됐으나 닫기가 실패한 경우 38건, 컨트롤이 탐지되고 닫힌 경우 64건, 컨트롤이 탐지되지 않고 닫히지도 않은 경우 30건이다. |
| CLAIM_REGISTRY.md | **SUPPORTED_WITH_LIMITATION** | §4-2 grade 태그 없음 | 59개 서비스 전수를 시도해 대표기능 진입 깊이(MPFED)가 산출된 것은 0건이다. |
| CLAIM_REGISTRY.md | **SUPPORTED_WITH_LIMITATION** | §4-2 grade 태그 없음 | 본 연구 계약이 대표기능 endpoint로 인정하지 않는 archetype에서 gate에 도달해 진입 깊이가 정의상 산출되지 않은 경우가 11건이다. |
| CLAIM_REGISTRY.md | **SUPPORTED_WITH_LIMITATION** | §4-2 grade 태그 없음 | gate 종류 판별이 UNDETERMINED로 떨어져 fail-closed 규칙이 endpoint 승격을 거부한 발화가 8건이고, 그중 실제로 결과를 바꾼 것은 1건이다. |

> 최종 headline 판정은 A. C 는 §2 금지 스캔·grade 태그·N 병기·수치 일치만 판정한다. `NUMBER_NOT_IN_C_REPLAY` 는 A 가 인용하는 숫자가 C 재계산값 집합에 없다는 뜻이며, 반올림 차이일 수 있어 개별 확인 대상이다.