# QA_CLAIM_LEDGER (C) — 2026-08-27T16:42:01+09:00

기준: .agent_bus/landing_v2/CLAIM_GOVERNANCE.md §2/§4 · 재계산 참조: /home/sieg/projects-wsl/ProjectFinal/.agent_worktrees/claude_c_assurance/research/landing_accessibility/assurance/out/QA_STAT_REPLAY.json, /home/sieg/projects-wsl/ProjectFinal/.agent_worktrees/claude_c_assurance/research/landing_accessibility/assurance/out/QA_MART_RECONCILIATION.json

**scan coverage: files 25/25 · sentences 4331 · retracted-phrase raw hits 4 · positive controls {"successor of '정직하게 거부' / '없는 codebook'": 13, "successor of '설계가 작동'": 19, "successor of 'wiring 고쳐도 신호 없다'": 10} · VALID**

집계: {'SUPPORTED_WITH_LIMITATION': 182, 'SUPPORTED': 6, 'UNSUPPORTED': 1}

| file | status | issues | sentence |
|---|---|---|---|
| CLAIM_REGISTRY.json | **SUPPORTED_WITH_LIMITATION** | §4-2 grade 태그 없음 | L0 산출물을 보유한 56개 관측에서 방해요소 235건이 탐지됐다. |
| CLAIM_REGISTRY.json | **SUPPORTED_WITH_LIMITATION** | §4-2 grade 태그 없음 | 56개 관측 중 22건(39.3%)에서 방해요소가 뷰포트를 완전히 덮었고, 6건은 겹침이 없었으며, 나머지 28건의 median은 0.0723이다. |
| CLAIM_REGISTRY.json | **SUPPORTED_WITH_LIMITATION** | §4-2 grade 태그 없음 | max_overlay_coverage 3구간 분해 (median 단독 인용 금지 규칙 준수) |
| CLAIM_REGISTRY.json | **SUPPORTED_WITH_LIMITATION** | §4-2 grade 태그 없음 | 닫기 컨트롤이 탐지되지 않은 상태에서 ESC/배경클릭으로 닫힌 경우 102건, 컨트롤이 탐지됐으나 닫기가 실패한 경우 38건, 컨트롤이 탐지되고 닫힌 경우 64건, 컨트롤이 탐지되지 않고 닫히지도 않은 경우 30건이다. |
| CLAIM_REGISTRY.json | **SUPPORTED_WITH_LIMITATION** | §4-2 grade 태그 없음 | 59개 서비스 전수를 시도해 대표기능 진입 깊이(MPFED)가 산출된 것은 0건이다. |
| CLAIM_REGISTRY.json | **SUPPORTED_WITH_LIMITATION** | §4-2 grade 태그 없음 | 본 연구 계약이 대표기능 endpoint로 인정하지 않는 archetype에서 gate에 도달해 진입 깊이가 정의상 산출되지 않은 경우가 11건이다. |
| CLAIM_REGISTRY.json | **SUPPORTED_WITH_LIMITATION** | §4-2 grade 태그 없음 | gate 종류 판별이 UNDETERMINED로 떨어져 fail-closed 규칙이 endpoint 승격을 거부한 발화가 8건이고, 그중 실제로 결과를 바꾼 것은 1건이다. |
| CLAIM_REGISTRY.md | **SUPPORTED_WITH_LIMITATION** | §4-2 grade 태그 없음 | L0 산출물을 보유한 56개 관측에서 방해요소 235건이 탐지됐다. |
| CLAIM_REGISTRY.md | **SUPPORTED_WITH_LIMITATION** | §4-2 grade 태그 없음 | 56개 관측 중 22건(39.3%)에서 방해요소가 뷰포트를 완전히 덮었고, 6건은 겹침이 없었으며, 나머지 28건의 median은 0.0723이다. |
| CLAIM_REGISTRY.md | **SUPPORTED_WITH_LIMITATION** | §4-2 grade 태그 없음 | metric**: max_overlay_coverage 3구간 분해 (median 단독 인용 금지 규칙 준수) |
| CLAIM_REGISTRY.md | **SUPPORTED_WITH_LIMITATION** | §4-2 grade 태그 없음 | 닫기 컨트롤이 탐지되지 않은 상태에서 ESC/배경클릭으로 닫힌 경우 102건, 컨트롤이 탐지됐으나 닫기가 실패한 경우 38건, 컨트롤이 탐지되고 닫힌 경우 64건, 컨트롤이 탐지되지 않고 닫히지도 않은 경우 30건이다. |
| CLAIM_REGISTRY.md | **SUPPORTED_WITH_LIMITATION** | §4-2 grade 태그 없음 | 59개 서비스 전수를 시도해 대표기능 진입 깊이(MPFED)가 산출된 것은 0건이다. |
| CLAIM_REGISTRY.md | **SUPPORTED_WITH_LIMITATION** | §4-2 grade 태그 없음 | 본 연구 계약이 대표기능 endpoint로 인정하지 않는 archetype에서 gate에 도달해 진입 깊이가 정의상 산출되지 않은 경우가 11건이다. |
| CLAIM_REGISTRY.md | **SUPPORTED_WITH_LIMITATION** | §4-2 grade 태그 없음 | gate 종류 판별이 UNDETERMINED로 떨어져 fail-closed 규칙이 endpoint 승격을 거부한 발화가 8건이고, 그중 실제로 결과를 바꾼 것은 1건이다. |
| FINAL_RESULTS_SUMMARY.md | **SUPPORTED_WITH_LIMITATION** | §4-2 grade 태그 없음 | 실제 거부** 1건 (E-6b 구속) — gate kind가 UNDETERMINED로 **도달**했고 fail-closed 규칙이 승격을 막았다. |
| FINAL_RESULTS_SUMMARY.md | **SUPPORTED_WITH_LIMITATION** | §4-2 grade 태그 없음 | 이 구분이 오늘 산출물 전체의 성격을 정한다. |
| FINAL_RESULTS_SUMMARY.md | **SUPPORTED_WITH_LIMITATION** | §4-2 grade 태그 없음 | 충분원인이 둘이고 서로 겹치지 않으므로** MPFED가 산출될 경로는 애초에 없었다. |
| FINAL_RESULTS_SUMMARY.md | **SUPPORTED_WITH_LIMITATION** | §4-2 grade 태그 없음 | 0** — J3(MPFED 산출)이 충족되지 않았다. |
| FINAL_RESULTS_SUMMARY.md | **SUPPORTED_WITH_LIMITATION** | §4-2 grade 태그 없음 | L0 산출물을 보유한 56개 관측에서 방해요소 235건이 탐지됐다. |
| FINAL_RESULTS_SUMMARY.md | **SUPPORTED_WITH_LIMITATION** | §4-2 grade 태그 없음 | 겹침 분포는 **양극**이다 — 완전히 덮은 관측 22건(39.3%) · 겹침 없음 6건 · 가운데 구간(0.25~0.75) 2건뿐. |
| FINAL_RESULTS_SUMMARY.md | **SUPPORTED_WITH_LIMITATION** | §4-2 grade 태그 없음 | median 단독 인용은 오도한다. |
| LIMITATIONS.md | **SUPPORTED_WITH_LIMITATION** | §4-2 grade 태그 없음 | E000_PLAN.json 의 e000_plan_hash_candidate 는 placeholder 바이트를 해싱한 뒤 덮어쓴 구조라 최종 산출물만으로 재현할 수 없다. |
| LIMITATIONS.md | **SUPPORTED_WITH_LIMITATION** | 분모 없는 '0건' — 'N건 중 0건' 으로 | 데이터 관측 이전에 동결됐다 (2026-08-27 12:25 KST, REAL TARGET evidence 0건 상태). |
| LIMITATIONS.md | **SUPPORTED_WITH_LIMITATION** | 분모 없는 '0건' — 'N건 중 0건' 으로 | E000은 고유 서비스를 0건 기여하고 측정기가 다르므로(E000 a86b4c7 / E001 222ef2c) 한 기술통계에 섞지 않는다 — 이득 0, 위험만 있다. |
| LIMITATIONS.md | **SUPPORTED_WITH_LIMITATION** | §4-2 grade 태그 없음 | E000은 측정기·evidence lineage 검증 산출물로만 보고한다. |
| LIMITATIONS.md | **SUPPORTED_WITH_LIMITATION** | §4-2 grade 태그 없음 | collector SHA가 상이하므로(E000   / E001  ) E000 6건은 **분석 표본이 아니라 측정기·evidence lineage 검증 산출물**이다. |
| LIMITATIONS.md | **SUPPORTED_WITH_LIMITATION** | §4-2 grade 태그 없음 | 유형 분포를 인용할 때 UNKNOWN을 각주로 빼면 실측 강도가 과대표시된다. |
| LIMITATIONS.md | **SUPPORTED_WITH_LIMITATION** | §4-2 grade 태그 없음 | 유형 분포를 인용할 때 이 값을 각주로 빼지 않는다. |
| LIMITATIONS.md | **SUPPORTED_WITH_LIMITATION** | §4-2 grade 태그 없음 | 오늘은 축 A가 평가되지 않아 이 축소가 실제 값으로 나타나지도 못했다 — 분모 자체가 산출되지 않았다. |
| LIMITATIONS.md | **SUPPORTED_WITH_LIMITATION** | §4-2 grade 태그 없음 | depth 축 미산출의 원인 귀속(가드 입도 · gate 판별 · archetype-endpoint 규칙)은 **현재 구현 하에서의 분해**다. |
| LIMITATIONS.md | **SUPPORTED_WITH_LIMITATION** | §4-2 grade 태그 없음 | 이 조건을 지금 적어두지 않으면, 나중에 recovery 결과가 나왔을 때 **오늘 산출물이 원인을 확정한 것처럼 읽힌다. |
| REAL_RUN_SUMMARY.json | **SUPPORTED_WITH_LIMITATION** | 분모 없는 '0건' — 'N건 중 0건' 으로 | E000은 고유 서비스를 0건 기여하고 측정기가 다르므로(E000 a86b4c7 / E001 222ef2c) 한 기술통계에 섞지 않는다 — 이득 0, 위험만 있다. |
| REAL_RUN_SUMMARY.json | **SUPPORTED_WITH_LIMITATION** | §4-2 grade 태그 없음 | E000은 측정기·evidence lineage 검증 산출물로만 보고한다. |
| REAL_RUN_SUMMARY.json | **SUPPORTED_WITH_LIMITATION** | §4-2 grade 태그 없음 | e6b_fired = detail.notes의 'gate 판별: UNDETERMINED' 마커(규칙 E-6b fail-closed). |
| REAL_RUN_SUMMARY.json | **SUPPORTED_WITH_LIMITATION** | §4-2 grade 태그 없음 | median과 q3는 규약과 무관하게 동일하다. |
| REAL_RUN_SUMMARY.json | **SUPPORTED_WITH_LIMITATION** | §4-2 grade 태그 없음 | 요점: 양극 분포라는 결론은 규약과 무관하게 성립한다** — 가운데 구간(0.25~0.75)이 2건뿐이라는 사실이 어느 규약에서도 바뀌지 않기 때문이다. |
| REAL_RUN_SUMMARY.json | **SUPPORTED_WITH_LIMITATION** | §4-2 grade 태그 없음 | median 단독 인용 금지.** min/q1/median/q3/max 전부와  (전면 가림 건수)을 함께 보고한다 — median 0.1281만 인용하면 전면 가림 건이 통째로 가려진다. |
| REAL_RUN_SUMMARY.json | **SUPPORTED_WITH_LIMITATION** | §4-2 grade 태그 없음 | 이봉 분포다** — 낮은 쪽 5건 · 가운데 0건 · 높은 쪽 51건으로 가운데가 비어 있다. |
| REAL_RUN_SUMMARY.json | **SUPPORTED_WITH_LIMITATION** | §4-2 grade 태그 없음 | median 단독 인용은 오도한다**: 중앙값은 어느 봉도 대표하지 않는다. |
| REAL_RUN_SUMMARY.json | **SUPPORTED_WITH_LIMITATION** | §4-2 grade 태그 없음 | median과 q3는 규약과 무관하게 동일하다. |
| REAL_RUN_SUMMARY.json | **SUPPORTED_WITH_LIMITATION** | §4-2 grade 태그 없음 | 요점: 양극 분포라는 결론은 규약과 무관하게 성립한다** — 가운데 구간(0.25~0.75)이 2건뿐이라는 사실이 어느 규약에서도 바뀌지 않기 때문이다. |
| REAL_RUN_SUMMARY.json | **SUPPORTED_WITH_LIMITATION** | §4-2 grade 태그 없음 | median 단독 인용 금지.** min/q1/median/q3/max 전부와  (전면 가림 건수)을 함께 보고한다 — median 0.1281만 인용하면 전면 가림 건이 통째로 가려진다. |
| REAL_RUN_SUMMARY.json | **SUPPORTED_WITH_LIMITATION** | §4-2 grade 태그 없음 | 이봉 분포다** — 낮은 쪽 32건 · 가운데 2건 · 높은 쪽 22건으로 가운데가 비어 있다. |
| REAL_RUN_SUMMARY.json | **SUPPORTED_WITH_LIMITATION** | §4-2 grade 태그 없음 | median 단독 인용은 오도한다**: 중앙값은 어느 봉도 대표하지 않는다. |
| REAL_RUN_SUMMARY.json | **SUPPORTED_WITH_LIMITATION** | §4-2 grade 태그 없음 | median과 q3는 규약과 무관하게 동일하다. |
| REAL_RUN_SUMMARY.json | **SUPPORTED_WITH_LIMITATION** | §4-2 grade 태그 없음 | 요점: 양극 분포라는 결론은 규약과 무관하게 성립한다** — 가운데 구간(0.25~0.75)이 2건뿐이라는 사실이 어느 규약에서도 바뀌지 않기 때문이다. |
| REAL_RUN_SUMMARY.json | **SUPPORTED_WITH_LIMITATION** | §4-2 grade 태그 없음 | median 단독 인용 금지.** min/q1/median/q3/max 전부와  (전면 가림 건수)을 함께 보고한다 — median 0.1281만 인용하면 전면 가림 건이 통째로 가려진다. |
| REAL_RUN_SUMMARY.json | **SUPPORTED_WITH_LIMITATION** | §4-2 grade 태그 없음 | 이봉 분포다** — 낮은 쪽 15건 · 가운데 1건 · 높은 쪽 40건으로 가운데가 비어 있다. |
| REAL_RUN_SUMMARY.json | **SUPPORTED_WITH_LIMITATION** | §4-2 grade 태그 없음 | median 단독 인용은 오도한다**: 중앙값은 어느 봉도 대표하지 않는다. |
| REAL_RUN_SUMMARY.json | **SUPPORTED_WITH_LIMITATION** | §4-2 grade 태그 없음 | median과 q3는 규약과 무관하게 동일하다. |
| REAL_RUN_SUMMARY.json | **SUPPORTED_WITH_LIMITATION** | §4-2 grade 태그 없음 | 요점: 양극 분포라는 결론은 규약과 무관하게 성립한다** — 가운데 구간(0.25~0.75)이 2건뿐이라는 사실이 어느 규약에서도 바뀌지 않기 때문이다. |
| REAL_RUN_SUMMARY.json | **SUPPORTED_WITH_LIMITATION** | §4-2 grade 태그 없음 | median 단독 인용 금지.** min/q1/median/q3/max 전부와  (전면 가림 건수)을 함께 보고한다 — median 0.1281만 인용하면 전면 가림 건이 통째로 가려진다. |
| REAL_RUN_SUMMARY.json | **SUPPORTED_WITH_LIMITATION** | §4-2 grade 태그 없음 | median과 q3는 규약과 무관하게 동일하다. |
| REAL_RUN_SUMMARY.json | **SUPPORTED_WITH_LIMITATION** | §4-2 grade 태그 없음 | 요점: 양극 분포라는 결론은 규약과 무관하게 성립한다** — 가운데 구간(0.25~0.75)이 2건뿐이라는 사실이 어느 규약에서도 바뀌지 않기 때문이다. |
| REAL_RUN_SUMMARY.json | **SUPPORTED_WITH_LIMITATION** | §4-2 grade 태그 없음 | median 단독 인용 금지.** min/q1/median/q3/max 전부와  (전면 가림 건수)을 함께 보고한다 — median 0.1281만 인용하면 전면 가림 건이 통째로 가려진다. |
| REAL_RUN_SUMMARY.json | **SUPPORTED_WITH_LIMITATION** | §4-2 grade 태그 없음 | 이봉 분포다** — 낮은 쪽 15건 · 가운데 0건 · 높은 쪽 41건으로 가운데가 비어 있다. |
| REAL_RUN_SUMMARY.json | **SUPPORTED_WITH_LIMITATION** | §4-2 grade 태그 없음 | median 단독 인용은 오도한다**: 중앙값은 어느 봉도 대표하지 않는다. |
| REAL_RUN_SUMMARY.json | **SUPPORTED_WITH_LIMITATION** | §4-2 grade 태그 없음 | 유형 분포를 인용할 때 UNKNOWN을 각주로 빼면 실측 강도가 과대표시된다. |
| REAL_RUN_SUMMARY.json | **SUPPORTED_WITH_LIMITATION** | §4-2 grade 태그 없음 | 102건만 강조하면   38건 — **닫기 컨트롤이 탐지됐는데도 해제에 실패한 경우** — 이 가려진다. |
| REAL_RUN_SUMMARY.json | **SUPPORTED_WITH_LIMITATION** | §4-2 grade 태그 없음 | 시각적 닫기 컨트롤이 탐지되지 않은 상태에서 ESC/배경클릭으로 닫힌 경우가 102건이다 |
| REAL_RUN_SUMMARY.json | **SUPPORTED_WITH_LIMITATION** | §4-2 grade 태그 없음 | 충분원인이 둘이고 서로 겹치지 않으므로** MPFED가 산출될 경로는 애초에 없었다. |
| REAL_RUN_SUMMARY.json | **SUPPORTED_WITH_LIMITATION** | §4-2 grade 태그 없음 | gate kind가 UNDETERMINED로 **도달**했고 fail-closed 규칙이 승격을 막았다. |
| REAL_RUN_SUMMARY.json | **SUPPORTED_WITH_LIMITATION** | §4-2 grade 태그 없음 | LA-AC-AMD1-20260827 §1.1 Spearman(OlderRelevantKWCAGFailRate, obstruction) |
| REAL_RUN_SUMMARY.json | **SUPPORTED_WITH_LIMITATION** | §4-2 grade 태그 없음 | 개정 1은 'X가 원리적으로 산출 불가'라는 **측정 가능성**에 근거했으나, 지금 남은 변수 중에서 새 association을 고르면 그것은 **쓸 수 있는 데이터를 보고 분석을 고르는 것**이 되어 성격이 다르다. |
| REAL_RUN_SUMMARY.json | **SUPPORTED_WITH_LIMITATION** | §4-2 grade 태그 없음 | LA-AC-AMD1-20260827 §1.3 Kruskal-Wallis(FailRate ~ InteractionArchetype) |
| REAL_RUN_SUMMARY.json | **SUPPORTED_WITH_LIMITATION** | §4-2 grade 태그 없음 | 개정 1은 'X가 원리적으로 산출 불가'라는 **측정 가능성**에 근거했으나, 지금 남은 변수 중에서 새 association을 고르면 그것은 **쓸 수 있는 데이터를 보고 분석을 고르는 것**이 되어 성격이 다르다. |
| STATISTICAL_RESULTS.json | **SUPPORTED_WITH_LIMITATION** | §4-2 grade 태그 없음 | L0 산출물을 보유한 56개 관측에서 방해요소 235건이 탐지됐다. |
| STATISTICAL_RESULTS.json | **SUPPORTED_WITH_LIMITATION** | §4-2 grade 태그 없음 | 56개 관측 중 22건(39.3%)에서 방해요소가 뷰포트를 완전히 덮었고, 6건은 겹침이 없었으며, 나머지 28건의 median은 0.0723이다. |
| STATISTICAL_RESULTS.json | **SUPPORTED_WITH_LIMITATION** | §4-2 grade 태그 없음 | max_overlay_coverage 3구간 분해 (median 단독 인용 금지 규칙 준수) |
| STATISTICAL_RESULTS.json | **SUPPORTED_WITH_LIMITATION** | §4-2 grade 태그 없음 | 닫기 컨트롤이 탐지되지 않은 상태에서 ESC/배경클릭으로 닫힌 경우 102건, 컨트롤이 탐지됐으나 닫기가 실패한 경우 38건, 컨트롤이 탐지되고 닫힌 경우 64건, 컨트롤이 탐지되지 않고 닫히지도 않은 경우 30건이다. |
| STATISTICAL_RESULTS.json | **SUPPORTED_WITH_LIMITATION** | §4-2 grade 태그 없음 | 59개 서비스 전수를 시도해 대표기능 진입 깊이(MPFED)가 산출된 것은 0건이다. |
| STATISTICAL_RESULTS.json | **SUPPORTED_WITH_LIMITATION** | §4-2 grade 태그 없음 | 본 연구 계약이 대표기능 endpoint로 인정하지 않는 archetype에서 gate에 도달해 진입 깊이가 정의상 산출되지 않은 경우가 11건이다. |
| STATISTICAL_RESULTS.json | **SUPPORTED_WITH_LIMITATION** | §4-2 grade 태그 없음 | gate 종류 판별이 UNDETERMINED로 떨어져 fail-closed 규칙이 endpoint 승격을 거부한 발화가 8건이고, 그중 실제로 결과를 바꾼 것은 1건이다. |
| STATISTICAL_RESULTS.md | **SUPPORTED_WITH_LIMITATION** | §4-2 grade 태그 없음 | 계약이 지정한 분석이 계산 불가능하다는 사실을 보고하는 것이 오늘의 통계 산출물이다. |
| STATISTICAL_RESULTS.md | **SUPPORTED_WITH_LIMITATION** | §4-2 grade 태그 없음 | 오늘 산출된 등급은 **정의·기술통계·직접 관측**뿐이며, association 기반 상위 등급은 계산 대상 자체가 없어 존재하지 않는다. |
| STATISTICAL_RESULTS.md | **SUPPORTED_WITH_LIMITATION** | §4-2 grade 태그 없음 | 이 구분이 오늘 산출물 전체의 성격을 정한다. |
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
| STATISTICAL_RESULTS.md | **SUPPORTED_WITH_LIMITATION** | §4-2 grade 태그 없음 | 충분원인이 둘이고 서로 겹치지 않으므로** MPFED가 산출될 경로는 애초에 없었다. |
| STATISTICAL_RESULTS.md | **SUPPORTED_WITH_LIMITATION** | §4-2 grade 태그 없음 | 오류를 먼저 적고, 그것이 산출물에 남지 않은 경위를 나중에 적는다. |
| STATISTICAL_RESULTS.md | **SUPPORTED_WITH_LIMITATION** | §4-2 grade 태그 없음 | "이 단계의 산출물을 만드는 코드가 실재하는가" |
| STATISTICAL_RESULTS.md | **SUPPORTED_WITH_LIMITATION** | §4-2 grade 태그 없음 | — 상류 산출물의 존재를 하류 단계의 존재로 추론하지 않는다. |
| STATISTICAL_RESULTS.md | **SUPPORTED_WITH_LIMITATION** | §4-2 grade 태그 없음 | 마지막 건은 오늘의 통계 산출물이 계산 불가능해진 직접 원인이다. |
| STATISTICAL_RESULTS.md | **SUPPORTED_WITH_LIMITATION** | §4-2 grade 태그 없음 | ／ C → A ／   판정 근거가 사실과 다름 ·   초판이 축 A 산출을 전제한 오류 ／ |
| STATISTICAL_RESULTS.md | **SUPPORTED_WITH_LIMITATION** | §4-2 grade 태그 없음 | 판별 키를   중복으로 바꿔 지시의 의도(이중 수집 탐지)는 지켰다. |
| fact_landing_observation.json | **SUPPORTED_WITH_LIMITATION** | §4-2 grade 태그 없음 | FAILED_EVIDENCE_INCOMPLETE |
| fact_landing_observation.json | **SUPPORTED_WITH_LIMITATION** | §4-2 grade 태그 없음 | FAILED_EVIDENCE_INCOMPLETE |
| fact_landing_observation.json | **SUPPORTED_WITH_LIMITATION** | §4-2 grade 태그 없음 | FAILED_EVIDENCE_INCOMPLETE |
| acquire_wiseapp_authority.py | **SUPPORTED_WITH_LIMITATION** | §4-2 grade 태그 없음 | diff      --acquire 산출물과 동결본의 sha256 을 대조해 판본 변화만 보고한다. |
| build_canonical_entities.py | **SUPPORTED_WITH_LIMITATION** | §4-2 grade 태그 없음 | state/entity_candidates.json        중간산출물 (원문 표기 인벤토리) |
| build_canonical_entities.py | **SUPPORTED_WITH_LIMITATION** | §4-2 grade 태그 없음 | D6  entity_candidates.json 이 고아 산출물이었다. |
| build_canonical_entities.py | **SUPPORTED_WITH_LIMITATION** | §4-2 grade 태그 없음 | → 이 스크립트의 중간산출물로 편입한다. |
| build_canonical_entities.py | **SUPPORTED_WITH_LIMITATION** | §4-2 grade 태그 없음 | 2) scripts/build_canonical_entities.py         (이 파일) 위 산출물 → 2층 구조 + panel_scope |
| build_canonical_entities.py | **SUPPORTED_WITH_LIMITATION** | §4-2 grade 태그 없음 | SUBSET: 액티브시니어+ 세대 앱 사용자 비율이 높은 '주요 금융 앱' 5개 (선별 기준 미공개) |
| build_canonical_entities.py | **SUPPORTED_WITH_LIMITATION** | §4-2 grade 태그 없음 | SUBSET: 액티브시니어+ 세대 앱 사용자 비율이 높은 '주요 금융 앱' 5개 (선별 기준 미공개) |
| build_canonical_entities.py | **SUPPORTED_WITH_LIMITATION** | §4-2 grade 태그 없음 | SUBSET: 순 결제추정금액 비율이 높은 '주요 홈쇼핑 리테일 브랜드' 5개 (홈쇼핑 업종 한정) |
| build_canonical_entities.py | **SUPPORTED_WITH_LIMITATION** | §4-2 grade 태그 없음 | SUBSET: 순 결제추정금액 비율이 높은 '주요 홈쇼핑 리테일 브랜드' 5개 (홈쇼핑 업종 한정) |
| build_canonical_entities.py | **SUPPORTED_WITH_LIMITATION** | §4-2 grade 태그 없음 | THRESHOLD: 월간 사용자 평균 200만 명 이상 + 액티브시니어+ 세대 비율 25% 이상인 앱 |
| build_canonical_entities.py | **SUPPORTED_WITH_LIMITATION** | §4-2 grade 태그 없음 | THRESHOLD: 순 결제추정금액 합 5천억 원 이상 + 액티브시니어+ 세대 비율 30% 이상인 리테일 브랜드 |
| build_canonical_entities.py | **SUPPORTED_WITH_LIMITATION** | 분모 없는 '0건' — 'N건 중 0건' 으로 | 원자료(source_ranking_rows.parquet) 값 시정은 누적 0건이며 261행은 그대로다. |
| build_canonical_entities.py | **SUPPORTED_WITH_LIMITATION** | §4-2 grade 태그 없음 | 25년 하반기 NS홈쇼핑, 홈앤쇼핑, 현대홈쇼핑/현대Hmall, CJ 온스타일, GS홈쇼핑/GS Shop은 액티브시니어+ 세대의 순 결제추정금액 비율이 각각 70%를 넘었음. |
| build_canonical_entities.py | **SUPPORTED_WITH_LIMITATION** | §4-2 grade 태그 없음 | 주요 홈쇼핑 리테일 브랜드 5개는 액티브시니어+ 세대 순 결제추정금액 비율이 전체의 70% 이상을 차지. |
| build_canonical_entities.py | **SUPPORTED_WITH_LIMITATION** | §4-2 grade 태그 없음 | 각주도 '리테일 브랜드를 업종별로 분류하여 각 업종별 합을 산출' 이라고 명시한다. |
| build_canonical_entities.py | **SUPPORTED_WITH_LIMITATION** | §4-2 grade 태그 없음 | 판정 분포 MERGE 1 / KEEP_SEPARATE 6 / UNRESOLVED 0. |
| build_final_and_registry.py | **SUPPORTED_WITH_LIMITATION** | §4-2 grade 태그 없음 | ·   — A0 §21 필수 산출물. |
| build_final_and_registry.py | **SUPPORTED_WITH_LIMITATION** | §4-2 grade 태그 없음 | 이미 검증된 산출물에서 값을 읽어 문서화만 한다. |
| build_final_and_registry.py | **SUPPORTED_WITH_LIMITATION** | §4-2 grade 태그 없음 | 이 구분이 오늘 산출물 전체의 성격을 정한다. |
| build_final_and_registry.py | **SUPPORTED_WITH_LIMITATION** | §4-2 grade 태그 없음 | 0** — J3(MPFED 산출)이 충족되지 않았다. |
| build_real_marts.py | **SUPPORTED_WITH_LIMITATION** | §4-2 grade 태그 없음 | E001 실측 배치에서 mart를 빌드하고 원인 귀속을 산출한다. |
| build_real_marts.py | **SUPPORTED_WITH_LIMITATION** | §4-2 grade 태그 없음 | 중대 관측**: 이 수집에는 KWCAG criterion 산출물이 **없다**(evidence는 L0 raw만 |
| build_real_marts.py | **SUPPORTED_WITH_LIMITATION** | §4-2 grade 태그 없음 | 중 1개 이상 non-UNDETERMINED)가 **어느 관측에서도 충족되지 않으므로 |
| build_real_marts.py | **SUPPORTED_WITH_LIMITATION** | §4-2 grade 태그 없음 | 충분원인이 둘이고 서로 겹치지 않으므로** MPFED가 산출될 경로는 애초에 없었다. |
| build_real_marts.py | **SUPPORTED_WITH_LIMITATION** | §4-2 grade 태그 없음 | 유형 분포를 인용할 때 UNKNOWN을 각주로 빼면 실측 강도가 과대표시된다. |
| build_real_marts.py | **SUPPORTED_WITH_LIMITATION** | §4-2 grade 태그 없음 | 개정 1은 'X가 원리적으로 산출 불가'라는 **측정 가능성**에 근거했으나, 지금 남은 변수 중에서 새 association을 고르면 그것은 **쓸 수 있는 데이터를 보고 분석을 고르는 것**이 되어 성격이 다르다. |
| build_real_marts.py | **SUPPORTED_WITH_LIMITATION** | §4-2 grade 태그 없음 | MPFED 미산출 59건의 원인을 **성격이 다른 범주로** 귀속한다. |
| build_real_marts.py | **SUPPORTED_WITH_LIMITATION** | §4-2 grade 태그 없음 | (manifest 해시 체인 검증) ·  (필수 산출물). |
| build_real_marts.py | **SUPPORTED_WITH_LIMITATION** | §4-2 grade 태그 없음 | 시각적 닫기 컨트롤이 탐지되지 않은 상태에서 ESC/배경클릭으로 닫힌 경우가 102건이다 |
| build_real_marts.py | **SUPPORTED_WITH_LIMITATION** | §4-2 grade 태그 없음 | 분포를   없이 보고하려 했다 — A 판정으로 금지된다. |
| build_real_marts.py | **SUPPORTED_WITH_LIMITATION** | §4-2 grade 태그 없음 | 분포에   행이 없으면 실패시킨다. |
| build_real_marts.py | **SUPPORTED_WITH_LIMITATION** | §4-2 grade 태그 없음 | A 판정: "  분포를 UNKNOWN 없이 보고하는 것 자체를 금지한다. |
| build_real_marts.py | **SUPPORTED_WITH_LIMITATION** | §4-2 grade 태그 없음 | median 단독 인용을 막기 위해** 항상 함께 낸다. |
| build_real_marts.py | **SUPPORTED_WITH_LIMITATION** | §4-2 grade 태그 없음 | 102건만 강조하면   38건 — **닫기 컨트롤이 탐지됐는데도 해제에 실패한 경우** — 이 가려진다. |
| build_real_marts.py | **SUPPORTED_WITH_LIMITATION** | §4-2 grade 태그 없음 | 오늘 산출물 4종 — 축 A/B/C + 방법론적 결론. |
| build_real_marts.py | **SUPPORTED_WITH_LIMITATION** | §4-2 grade 태그 없음 | gate kind가 UNDETERMINED로 **도달**했고 fail-closed 규칙이 승격을 막았다. |
| build_real_marts.py | **SUPPORTED_WITH_LIMITATION** | §4-2 grade 태그 없음 | median과 q3는 규약과 무관하게 동일하다. |
| build_real_marts.py | **SUPPORTED_WITH_LIMITATION** | §4-2 grade 태그 없음 | 요점: 양극 분포라는 결론은 규약과 무관하게 성립한다** — 가운데 구간(0.25~0.75)이 2건뿐이라는 사실이 어느 규약에서도 바뀌지 않기 때문이다. |
| build_real_marts.py | **SUPPORTED_WITH_LIMITATION** | §4-2 grade 태그 없음 | median 단독 인용 금지.** min/q1/median/q3/max 전부와  (전면 가림 건수)을 함께 보고한다 — median 0.1281만 인용하면 전면 가림 건이 통째로 가려진다. |
| build_real_marts.py | **SUPPORTED_WITH_LIMITATION** | §4-2 grade 태그 없음 | final_label 분포에 UNKNOWN 행이 없다 — UNKNOWN을 뺀 유형 분포 보고는 금지된다. |
| build_real_marts.py | **SUPPORTED_WITH_LIMITATION** | §4-2 grade 태그 없음 | 이봉 분포다** — 낮은 쪽 |
| build_real_marts.py | **SUPPORTED_WITH_LIMITATION** | §4-2 grade 태그 없음 | median 단독 인용은 오도한다**: 중앙값은 어느 봉도 대표하지 않는다. |
| build_real_marts.py | **SUPPORTED_WITH_LIMITATION** | §4-2 grade 태그 없음 | interrupts_per_obs_median |
| build_real_marts.py | **SUPPORTED_WITH_LIMITATION** | §4-2 grade 태그 없음 | max_overlay_coverage_median |
| build_real_marts.py | **SUPPORTED_WITH_LIMITATION** | §4-2 grade 태그 없음 | LA-AC-AMD1-20260827 §1.1 Spearman(OlderRelevantKWCAGFailRate, obstruction) |
| build_real_marts.py | **SUPPORTED_WITH_LIMITATION** | §4-2 grade 태그 없음 | LA-AC-AMD1-20260827 §1.3 Kruskal-Wallis(FailRate ~ InteractionArchetype) |
| build_source_rows_from_journal.py | **SUPPORTED_WITH_LIMITATION** | §4-2 grade 태그 없음 | C002 산출물( ,  )은 |
| build_source_rows_from_journal.py | **SUPPORTED_WITH_LIMITATION** | §4-2 grade 태그 없음 | figure 판독 결과만 커밋돼 있어 산출물로부터 재현이 불가능했다. |
| build_source_rows_from_journal.py | **SUPPORTED_WITH_LIMITATION** | §4-2 grade 태그 없음 | 저널이 없으면 스크립트는 실패하며, 기존 산출물을 덮어쓰지 않는다. |
| build_source_rows_from_journal.py | **SUPPORTED_WITH_LIMITATION** | §4-2 grade 태그 없음 | 2) build_canonical_entities.py         위 두 산출물 → service_master / alias / membership / |
| build_source_rows_from_journal.py | **SUPPORTED_WITH_LIMITATION** | §4-2 grade 태그 없음 | C012(D3) — 산출물에 절대경로를 적지 않는다 |
| build_source_rows_from_journal.py | **SUPPORTED_WITH_LIMITATION** | §4-2 grade 태그 없음 | 기존 C002 산출물과 동일한 식이며, 재생성 결과가 기존 id 와 어긋나면 실패한다(--check). |
| build_source_rows_from_journal.py | **SUPPORTED_WITH_LIMITATION** | §4-2 grade 태그 없음 | (1) 액티브시니어+ 세대 앱 사용자 비율이 높은 주요 금융 앱 |
| build_source_rows_from_journal.py | **SUPPORTED_WITH_LIMITATION** | §4-2 grade 태그 없음 | (1) 액티브시니어+ 세대 순 결제추정금액 비율이 높은 주요 홈쇼핑 리테일 브랜드 |
| build_source_rows_from_journal.py | **SUPPORTED_WITH_LIMITATION** | §4-2 grade 태그 없음 | 기존 산출물과 대조만 하고 쓰지 않는다 |
| build_source_rows_from_journal.py | **SUPPORTED_WITH_LIMITATION** | §4-2 grade 태그 없음 | 절대경로를 산출물에 적으면 실행 위치가 산출물의 일부가 되어 재실행 바이트 동일성이 성립하지 않는다(C011 P2 idempotency-claim-false-journal-path-absolute). |
| build_statistical_results.py | **SUPPORTED_WITH_LIMITATION** | §4-2 grade 태그 없음 | STATS 산출물 —  (2026-08-27 14:58 개정본) 기준. |
| build_statistical_results.py | **SUPPORTED_WITH_LIMITATION** | §4-2 grade 태그 없음 | 불가능하다는 사실을 보고하는 것이 오늘의 통계 산출물이다**(A 명시). |
| build_statistical_results.py | **SUPPORTED_WITH_LIMITATION** | §4-2 grade 태그 없음 | 반려 패턴이 산출물에 들어갔다. |
| build_statistical_results.py | **SUPPORTED_WITH_LIMITATION** | §4-2 grade 태그 없음 | 오류를 먼저 적고, 그것이 산출물에 남지 않은 경위를 나중에 적는다. |
| build_statistical_results.py | **SUPPORTED_WITH_LIMITATION** | §4-2 grade 태그 없음 | "이 단계의 산출물을 만드는 코드가 실재하는가" |
| build_statistical_results.py | **SUPPORTED_WITH_LIMITATION** | §4-2 grade 태그 없음 | — 상류 산출물의 존재를 하류 단계의 존재로 추론하지 않는다. |
| build_statistical_results.py | **SUPPORTED_WITH_LIMITATION** | §4-2 grade 태그 없음 | 마지막 건은 오늘의 통계 산출물이 계산 불가능해진 직접 원인이다. |
| build_statistical_results.py | **SUPPORTED_WITH_LIMITATION** | §4-2 grade 태그 없음 | ／ C → A ／   판정 근거가 사실과 다름 ·   초판이 축 A 산출을 전제한 오류 ／ |
| build_statistical_results.py | **SUPPORTED_WITH_LIMITATION** | §4-2 grade 태그 없음 | 판별 키를   중복으로 바꿔 지시의 의도(이중 수집 탐지)는 지켰다. |
| build_statistical_results.py | **SUPPORTED_WITH_LIMITATION** | §4-2 grade 태그 없음 | E000_PLAN.json 의 e000_plan_hash_candidate 는 placeholder 바이트를 해싱한 뒤 덮어쓴 구조라 최종 산출물만으로 재현할 수 없다. |
| build_statistical_results.py | **SUPPORTED_WITH_LIMITATION** | §4-2 grade 태그 없음 | collector SHA가 상이하므로(E000   / E001  ) E000 6건은 **분석 표본이 아니라 측정기·evidence lineage 검증 산출물**이다. |
| build_statistical_results.py | **SUPPORTED_WITH_LIMITATION** | §4-2 grade 태그 없음 | 오늘은 축 A가 평가되지 않아 이 축소가 실제 값으로 나타나지도 못했다 — 분모 자체가 산출되지 않았다. |
| build_statistical_results.py | **SUPPORTED_WITH_LIMITATION** | §4-2 grade 태그 없음 | depth 축 미산출의 원인 귀속(가드 입도 · gate 판별 · archetype-endpoint 규칙)은 **현재 구현 하에서의 분해**다. |
| build_statistical_results.py | **SUPPORTED_WITH_LIMITATION** | §4-2 grade 태그 없음 | 이 조건을 지금 적어두지 않으면, 나중에 recovery 결과가 나왔을 때 **오늘 산출물이 원인을 확정한 것처럼 읽힌다. |
| build_statistical_results.py | **SUPPORTED_WITH_LIMITATION** | §4-2 grade 태그 없음 | 계약이 지정한 분석이 계산 불가능하다는 사실을 보고하는 것이 오늘의 통계 산출물이다. |
| build_statistical_results.py | **SUPPORTED_WITH_LIMITATION** | §4-2 grade 태그 없음 | 오늘 산출된 등급은 **정의·기술통계·직접 관측**뿐이며, association 기반 상위 등급은 계산 대상 자체가 없어 존재하지 않는다. |
| build_statistical_results.py | **SUPPORTED_WITH_LIMITATION** | §4-2 grade 태그 없음 | 이 구분이 오늘 산출물 전체의 성격을 정한다. |
| build_statistical_results.py | **SUPPORTED_WITH_LIMITATION** | §4-2 grade 태그 없음 | max_overlay_coverage 3구간 분해 (median 단독 인용 금지 규칙 준수) |
| build_statistical_results.py | **SUPPORTED_WITH_LIMITATION** | §4-2 grade 태그 없음 | 유형 분포를 인용할 때 이 값을 각주로 빼지 않는다. |
| build_statistical_results.py | **SUPPORTED_WITH_LIMITATION** | §4-2 grade 태그 없음 | 닫기 컨트롤이 탐지되지 않은 상태에서 ESC/배경클릭으로 닫힌 경우 |
| build_statistical_results.py | **SUPPORTED_WITH_LIMITATION** | §4-2 grade 태그 없음 | 건, 컨트롤이 탐지됐으나 닫기가 실패한 경우 |
| build_statistical_results.py | **SUPPORTED_WITH_LIMITATION** | §4-2 grade 태그 없음 | 건, 컨트롤이 탐지되고 닫힌 경우 |
| build_statistical_results.py | **SUPPORTED_WITH_LIMITATION** | §4-2 grade 태그 없음 | 건, 컨트롤이 탐지되지 않고 닫히지도 않은 경우 |
| build_statistical_results.py | **SUPPORTED_WITH_LIMITATION** | 분모 없는 '0건' — 'N건 중 0건' 으로; §4-2 grade 태그 없음 | 개 서비스 전수를 시도해 대표기능 진입 깊이(MPFED)가 산출된 것은 0건이다. |
| build_statistical_results.py | **SUPPORTED_WITH_LIMITATION** | §4-2 grade 태그 없음 | 본 연구 계약이 대표기능 endpoint로 인정하지 않는 archetype에서 gate에 도달해 진입 깊이가 정의상 산출되지 않은 경우가 |
| build_statistical_results.py | **SUPPORTED_WITH_LIMITATION** | §4-2 grade 태그 없음 | gate 종류 판별이 UNDETERMINED로 떨어져 fail-closed 규칙이 endpoint 승격을 거부한 발화가 |
| build_statistical_results.py | **SUPPORTED_WITH_LIMITATION** | 분모 없는 '0건' — 'N건 중 0건' 으로 | 개 중 현행 WA 인증 join 3요건 충족은 0건이었다. |
| extract_remediation_cases.py | **UNSUPPORTED** | FORBIDDEN §2.4: 단일 종합점수/score 금지 | 세 축(KWCAG/entry friction/certification)을 단일 점수로 합치지 않는 원칙과 같은 |
| extract_remediation_cases.py | **SUPPORTED_WITH_LIMITATION** | 분모 없는 '0건' — 'N건 중 0건' 으로 | 게이트를 통과한 사례가 0건인 것은 실패가 아니라 사실이다. |
| generate_deliverable_templates.py | **SUPPORTED_WITH_LIMITATION** | §4-2 grade 태그 없음 | 산출물 템플릿 생성 CLI — 목표 3, end-to-end. |
| generate_deliverable_templates.py | **SUPPORTED_WITH_LIMITATION** | §4-2 grade 태그 없음 | marts 빌드 → EDA-03~09 실행 →   → Markdown/JSON 산출물 |
| generate_deliverable_templates.py | **SUPPORTED_WITH_LIMITATION** | §4-2 grade 태그 없음 | E000_FAST(6개 타깃) 범위 — PHASE_GATES.md의 E000_V2_VALIDATED(8~12타깃+두 독립감사)는 이 산출물로 충족되지 않는다. |
| run_fixture_engine.py | **SUPPORTED_WITH_LIMITATION** | §4-2 grade 태그 없음 | <out>/task_manifests/       Path Freeze 산출물 |
| run_fixture_engine.py | **SUPPORTED_WITH_LIMITATION** | §4-2 grade 태그 없음 | 여기서 나오는 PASS/FAIL 은 **synthetic fixture 에 대한 engine test 결과**이며 |
| verify_v2_docs.py | **SUPPORTED_WITH_LIMITATION** | §4-2 grade 태그 없음 | exit 0 = PASS, exit 1 = FAIL. |
| verify_v2_docs.py | **SUPPORTED_WITH_LIMITATION** | §4-2 grade 태그 없음 | V2_DOCS_VERIFY: FAIL |

> 최종 headline 판정은 A. C 는 §2 금지 스캔·grade 태그·N 병기·수치 일치만 판정한다. `NUMBER_NOT_IN_C_REPLAY` 는 A 가 인용하는 숫자가 C 재계산값 집합에 없다는 뜻이며, 반올림 차이일 수 있어 개별 확인 대상이다.