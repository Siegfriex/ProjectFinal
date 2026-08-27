# C_R0_QA — R0 입력 감사(2281c85) 독립 재현

**ticket** `T-A-R0-C-001` · **producer** C (claude-fable-5, `claude-c/assurance-v21`)
**정본** `C_R0_QA.json` (이 파일은 색인이다) · **audit target** `claude-b/measurement-recovery@2281c853950d0c475c5d2c1678680b971c2804f4`
**production_modified** false · **labels_produced** 0 · **B 함수 import** 0 · **REAL_TARGET** 0

| # | 주장 | 판정 | 핵심 근거 (exact 파일:행) |
|---|---|---|---|
| S-10 | CSV 에 task definition 59/59 | **CONFIRMED** + qualifier | CSV blob `48e2492e…` @9999857, frozen 59 조인 59/59 non-empty; **distinct 7/2/7/3 (archetype-level)**; UTILITY_ENTRY 6행 `region_signal_type=CODEBOOK_PENDING` |
| S-11 | E001TargetRow 5필드 유실 · default_task_definition 하드코딩 | **CONFIRMED** | `firewall.py:543-554` 9필드 · `executor.py:68-75` 상수 4개 |
| S-12 | detector 실사이트 구현 부재 (F-1) | **CONFIRMED** | `l0_probe.js:309/:334/:337` marker 생산 · `l1_engine.py:213-218/:223-231` marker 비교 · probe 58/58 재집계 `body_endpoint_reached` null; declared_regions 3건·declared_endpoints 1건 관측 |
| S-13 | `*_signal_type` 프로덕션 reader 0 (F-2) | **CONFIRMED** | 프로덕션 호출부 0 @2281c85; 테스트 호출 repo-root `tests/test_pc_fixture_engine.py:491-492` 2건 실재 (C 첫 판의 '테스트도 0' 은 스캔 범위 오류로 철회) |
| S-14 | guard 25/59 · LOGIN 19 · QUERY 5 | **CONFIRMED** | batches 16 파일 재집계: BLOCKED 25 (LOGIN 19/PURCHASE 3/SIGNUP 2/PAYMENT 1), QUERY 5 = BLOCKED 4 + RETRY_EXHAUSTED 1, scout 31 |
| S-15 | 갭1·갭2 독립 | **CONFIRMED** | `l1_engine.py:213-214`, `:223-224` 조기반환; B1-only 비교대상 null/'1','2' → False; B2-only 조기반환 |
| F-6 | signal_type = archetype 1:1 | CONFIRMED | 59행 재집계 |
| F-7 | C-E 회수 1건 | NOT_INDEPENDENTLY_RECOUNTED | R0 GO 근거에서 제외 |
| §4.1 | depth segment NULL→step_count | NOT_VERIFIED | mart 영향 없음, W1/W2 후 회귀 |

**R0 GO 에 반하는 T1 모순: 0건.** contract freeze 에서 A 가 닫을 것 3건 — UTILITY_ENTRY 6행 정의 출처 · 정의 입도(archetype-level 7) 표기 · marker 경로 실사이트 비활성화.

**대조군**: 양성 `grep 'exclusive create'`→1, `grep KWCAG src`→2 · 음성 C 자체 오류 2건(BOM, AMBIGUOUS 조인) 검출·정정.

**이 검증이 확인하지 않은 것**: F-7 · §4.1 · P-A codebook 존재 · 어떤 detector 의 runtime 실행 · E000.
