# C P1 Assurance Harness — offline readiness (T-A-V3-P0-C-001 task 3)

원칙: B 의 expected output 을 import 하지 않는다. B 의 dedicated 12-only caller 가 push 되면 **같은 exact SHA 의 scratchpad clone** 에서 아래를 C 코드로 재실행한다. REAL 은 A 의 12 REAL GO 이전 금지 — 아래 전부 FIXTURE/오프라인.

| 항목 | 상태 | C 도구 | 비고 |
|---|---|---|---|
| fixture harness (13 픽스처, guard mask·gate·outcome) | READY | `run_e001_batch_dryrun.py --mode FIXTURE` + `c_joint2_plan.json`, 결과 비교 `pilot/C_INTEG_*_fixture_batch.json` | 288025ff/01041bc 기준선 보유 |
| allow12 / outside deny / tamper deny 3방향 | READY | `pilot/scope_threeway_test.py` | 01041bc PASS(12/12·5/5·2/2), 음성대조 2종(scope 부재·manifest 부재) NOT_PASSED 확인 |
| 음성대조(양성대조가 발화하는 상태의 0) | READY | 같은 하네스 T2(e)·T3 + `w1/positive_control_2281c85.json`(target 당 2 run) | 규율1 충족 |
| duplicate/idempotency harness | READY | `w1/dup_launch_harness.py`, `w1/lock_race_harness.py` | 01041bc tree 3/3 각 1 run, 억제 launch 이전 |
| release document binding | READY | 하네스 T4 `evaluate_execution_scope(V2_DIAGNOSTIC)` — 현재 control HEAD 에서 allowed=True(78f2e32a) | 릴리스 verdict 는 원격 control ref 런타임 판독이므로 C 는 launch 시 control SHA 를 lineage 에 기록 |
| manifest hash binding | READY | T0/T3 (`load_v2_diagnostic_allowlist` sha 검증) + `pilot/preflight_sampling.py`(12/12 재현) | |
| `--check-only` 경로 | PENDING(B 구동기 필요) | `pilot/dedicated_caller_check.py`(작성 예정, 인터페이스 도착 후) — 기대: 네트워크 0·allowlist 12·release verdict·manifest sha 출력, exit 0; manifest 밖 target 주입 시 non-zero | B 인터페이스 미정이라 introspection 방식으로 작성 |
| E001_FULL regression unchanged 확인 | READY | `pilot/e001_runner_unchanged_check.py` — `scripts/run_e001_real.py` 및 `engine/firewall.py` 의 E001 경로 blob sha 를 01041bc 대비 비교 | dedicated caller 가 full59 runner 를 건드리지 않았음을 바이트로 증명 |
| C 버스 스캐너 음성대조 fixture | DONE | `c_bus_scan.py` + `v3_C_BUS_SCANNER_NEGCTRL.json` — known_positive 4/4·known_negative 0 과탐·malformed 명시 보고 PASS | P0-D cc 약속 이행 |
