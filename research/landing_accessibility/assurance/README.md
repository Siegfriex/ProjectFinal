# assurance/ — Claude C (Independent Evidence, Measurement & Statistical Assurance Plane)

**A decides · B produces · C verifies.** 이 디렉터리는 `claude-c/assurance-current` 에만 존재한다.

- B 분석 코드를 import 하지 않는다. raw facts(evidence run / manifest / batch chain / mart CSV)에서 독립 재계산한다.
- 계약: `control/TIMEBOX_1630_EXECUTION_SSOT.md` §6~§12, `control/ANALYSIS_CONTRACT.md` (LA-AC-20260827), `docs/v2/A1`, `A2`, `docs/07_EVIDENCE_MANIFEST_CONTRACT.md`.
- 산출물(`out/`): QA_BASE.json · QA_E000_FAST.json · QA_COLLECTION_RECONCILIATION.json · QA_FRAME_FREEZE.json · QA_AI_LEDGER.json · QA_MART_RECONCILIATION.json · QA_STAT_REPLAY.json · QA_CLAIM_LEDGER.md · ASSURANCE_HANDOFF.json
- 심각도: C0 = systemic hard-stop 후보 5종만 (A에 즉시 escalation, 최종 stop 은 A). C1 = 결과에 영향 있는 target/result 단위 mismatch. C2 = backlog.

| 모듈 | 역할 |
|---|---|
| `bus.py` | 티켓 읽기 / ACK(`acks/<id>.C.json`) / 완료(`completions/<id>.C.json`) / event_log / heartbeat 상태 |
| `stats_replay.py` | tie-aware Spearman(independent), permutation(독립 seed), KW(min n≥5), descriptive, FailRate 분모·UNDET bounds, archetype median·min-N, LOAO, 방향안정성(2축), secondary 결측률 선택 |
| `REFERENCE_DEFINITIONS.md` | 권위문서에서 뽑은 원문 정의 (검산 기준) |
