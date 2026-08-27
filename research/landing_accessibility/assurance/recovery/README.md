# recovery/ — POST-E001 RECOVERY 독립 감사 lane (Claude C)

**Director 지시 2026-08-27 15:25.** FINAL assurance(16:00 CLAIM / 16:30 FINAL, frozen E001 사실만)와 **분리**한다.
이 디렉터리의 산출물은 FINAL 에 섞지 않는다. 어떤 구현도 정당화하지 않고, A 의 계약과 B 의 코드가 실제로 일치하는지만 독립 검증한다.

| # | 업무 | 산출물 |
|---|---|---|
| 1 | CURRENT COLLECTOR 222ef2c 기준 Depth dataflow 독립 재구성 + 59 target 필드 계수 + MPFED 0/59 원인 재분해 (guard / task wiring / signal detector / endpoint contract 분리) | `CURRENT_IMPLEMENTATION_CAUSAL_AUDIT.md` (+ `DEPTH_DATAFLOW_222ef2c.md`, `TASK_FIELD_COUNTS.json`) |
| 2 | B guard relocation 적대적 검증 (negative tests 6종) | `GUARD_NEGATIVE_TESTS.md` + fixtures |
| 3 | partial-depth semantics fixture 5종 (NED/IED/MPFED NULL 규칙) | `PARTIAL_DEPTH_FIXTURES.md` + fixtures |
| 4 | Axis A evaluator assurance (registry 정본 vs evaluator output) | `AXIS_A_EVALUATOR_QA.json` |
| 5 | Axis C semantic recovery assurance (235/110 immutable baseline) | `AXIS_C_SEMANTIC_QA.json` |

라벨 규칙: A 의 기존 반사실("guard 를 고쳐도 recovery upper bound 8") 은 **CURRENT_IMPLEMENTATION_CONDITIONAL_COUNTERFACTUAL** 로 보존한다. task-definition wiring + real signal detector 를 복구한 시스템에도 상한 8 을 일반화하면 반려.

GO_POST_E001_RECOVERY_REAL 조건(전건): original E001 immutable · task field lineage 전건 검증 · signal resolver fixture PASS · prohibited action negative tests PASS · partial NED semantics PASS · KWCAG denominator/criterion lineage PASS · C0=0 · prohibited real action=0 · A 가 recovery contract 를 결과 보기 전에 freeze · recovery collector/protocol SHA 가 기존 E001 과 명확히 분리. 하나라도 실패 → NO-GO.
