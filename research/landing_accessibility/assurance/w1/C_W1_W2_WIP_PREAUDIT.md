# C_W1_W2_WIP_PREAUDIT — claude-b/w1-guard-wiring @67d7d8a · claude-b/w2-rf-detector @1de537c (wip, completion 전 read-only)

**producer** C · production_modified false · 21:47 KST

## W1 @67d7d8a
- **TargetLock 원시 race PASS** (`lock_race_harness.py`, B TargetLock 을 SUT 로 3 프로세스 동시 기동 × 3 key, 1.5s barrier): 키당 proceed 정확히 1, 나머지 2 는 `DUPLICATE_SUPPRESSED` (O_EXCL 패배 1 + RUNNING 상태 1). lock 파일 3 개 잔존(미삭제) ✓. 결과 `lock_race_w1_67d7d8a.json`.
- 억제 지점: `batch.py _real_executor` 에서 `IdempotencyKey → acquire → (suppressed) return` 이 `EvidenceRun.create` **이전** ✓ (D-R0-38/46). run_id 는 A 발행 회차(ticket 단위) 요구 — `IdempotencyKeyMissing` 예외 ✓.
- **주의 (P2, 테스트 경로)**: lock 은 REAL_TARGET 경로에만 배선. FIXTURE 경로(`_run_l0_and_l1`)는 그대로라 C 의 offline 중복 발사 하네스(같은 out dir 프로세스 2개)는 여전히 **6 run / 3 target, proc2 BatchOverwriteError** (`fixture_path_w1_67d7d8a.json`). 즉 "같은 worker 파티션 프로세스 2개 동시 기동"(D-R0-46 억제 테스트)을 **실사이트 접속 없이 end-to-end 로 증명할 경로가 없다**. 요구: FIXTURE/SHADOW 에도 lock 을 배선하거나(권고: 배선 — 수집 안전성 동일), 최소한 `_real_executor` 의 lock 구간을 network 없이 구동하는 offline 테스트 훅.
- guard/wiring/task lineage 는 completion 시 C 픽스처 8종으로 채점.

## W2 @1de537c
- marker 게이팅 이중화: `l0_probe.js` 가 `REAL_TARGET_MODE` 면 `[data-region]` 수집 자체를 [] 로, `l1_engine.detect_*` 는 `execution_mode is REAL_TARGET` 에서 marker 함수 호출을 단락 생략 ✓ (D-R0-42).
- `region_signal_type/endpoint_signal_type` 이 `_real_region_by_signal_type/_real_endpoint_by_signal_type` 에서 실제 소비 ✓ (D-R0-16, 프로덕션 최초 배선). URL_PATTERN 의 region 용 신호 미정의는 문서화된 gap(CSV 에서 region URL_PATTERN 0행이므로 무해).
- Branch U: region=endpoint = primary control(button/input/select/textarea/role=button) present∧hittable ✓ (D-R0-41/47).
- `depth.py assign_depth_segments`: MPFED NULL 시 step_count 대체 제거 → UNASSIGNED ✓ (B 감사 §4.1 결함 시정, C NOT_VERIFIED 항목 해소 예정).
- `observation_truncation_caveats` 로 cap 절단을 판정 caveat 로 전파 ✓ (D-R0-53).
- 미확인: `_content_endpoint_real` 의 pre-roll 광고 구분(C fixture `content_open_preroll_ad`), quick-view 가격 부재(`endpoint_fp_quickview_no_price`), force-map 방지(`ambiguous_query_plus_items`) — completion 시 채점.
