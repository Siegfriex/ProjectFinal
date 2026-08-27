# Current State Baseline v3.0 — 2026-08-28 00:49 KST 전후

이 문서는 v3 pack 생성 시점의 GitHub remote와 사용자 제공 operational snapshot을 결합한 설치 기준선이다.

## Exact remote heads

| plane / branch | SHA | 의미 |
|---|---|---|
| A `control/landing-orchestrator` | `8f413527a5ca1ab6a01120487ea826dab432cf21` | `V2_DIAGNOSTIC_RELEASE.json` 12-target scope RELEASED |
| promoted research main `research/landing-accessibility-main` | `bc0b7a087faf2328cbafdfa9b40bd426c5080d7d` | A release가 참조하는 promoted main |
| B `claude-b/diag-pilot-integration` | `01041bc213a2e61f6cb224e469087d9a11324349` | V2_DIAGNOSTIC firewall/scope integration |
| B W2 frozen `claude-b/w2-rf-detector` | `b28aaa5cad736082a6a76c0ca6a9f6be330bbcfb` | RF detector NOT_PASSED freeze |
| C `claude-c/assurance-current` | `1baa865b4a673af05033e6e6289fd2713676baa5` | current assurance branch |
| D `claude-d/research-sandbox-v21` | `bcaa634b1b408ece6cfc733e7dc08530f40d6fa3` | measurement research sandbox; latest recorded D-DEF-08 |
| pilot manifest `control/pilot-manifest` | `54a0c7a4149adc17c086e398be83bc7c117a66b0` | DIAG-PILOT-001 manifest lineage |

## Current REAL authority

- `V2_DIAGNOSTIC`: 12 target scope RELEASED by A.
- `E001_FULL 59`: SUSPENDED / v3 main이 아님.
- canonical W2 acceptance: NOT_PASSED.
- v3 50: **candidate only, no release**.

## Current executable blocker

B branch의 `research/landing_accessibility/scripts/run_e001_real.py`는 현재 문서/코드상 `E001_FULL`을 hard-code한다.

- `ExecutionScope.E001_FULL`
- `load_e001_full_targets`
- `load_e001_full_allowlist`

따라서 A가 release한 V2_DIAGNOSTIC 12를 실제 caller가 소비하도록 별도 wiring이 아직 필요하다.

## Why v3 pivot now

v2.1/D 연구에서 누적된 핵심 교훈:
- 대표기능 prior와 business domain이 결합되어 RF 성능을 representative-function correctness로 읽기 어려움.
- 규칙은 다중 후보를 자주 내고, semantic signal은 control보다 title/topic identity에 끌릴 수 있음.
- Depth null은 저장기능 부족만이 아니라 상류 task/region 관측부재와 guard에 묶여 있음.
- 기존 DOM/AX/geometry/obstruction instrumentation 자체는 재사용 가치가 높음.

따라서 v3은 “더 좋은 classifier”보다 “task를 수집 전에 고정”하는 방향으로 병목을 제거한다.

## Installation caution

이 baseline은 v3 design authority candidate의 기준선이지 release document가 아니다. v3 채택 후 branch heads가 바뀌면 `08_CURRENT_STATE_BASELINE`만 새 버전으로 갱신하되 SSOT의 과업/claim 경계를 묵시적으로 바꾸지 않는다.
