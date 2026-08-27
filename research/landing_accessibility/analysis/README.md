# `analysis/` — P-A 산출물 (LANE A SHADOW)

> **상태 `SHADOW_PREPARATORY`.** 이 디렉터리의 어떤 산출물도 **정본이 아니다**.
> 정책 정의부는 `docs/v2/PHASE_GATES.md` **§4**이며, 이 문서는 그 절을 가리킬 뿐 정책표를 복제하지 않는다.
> provenance 전량은 **`SHADOW_MANIFEST.json`** 에 있다 — `base_sha` · `shadow_lane` ·
> `source_frame_sha` · `codebook_sha` · 오염 검사 결과 · 산출물 31건의 sha256 · reconciliation 절차.

| | |
|---|---|
| base SHA | `d5f1da5652953542d5c8be377026cc3293f2075a` |
| lane / 브랜치 | `LANE_A` / `agent/landing-pa-shadow` |
| `authoritative` | **false** — `research/landing-accessibility-main` promotion **금지** |
| `real_target_outcome_used` | **false** — 실제 서비스에 연결하지 않았다 |
| Gate | `ANALYSIS_AND_TASK_CODEBOOK_FROZEN` **닫지 않았다.** freeze *candidate* 까지다 |

## 구조

```
analysis/
  SHADOW_MANIFEST.json        provenance 정본 (§4.3)
  PA_FINDINGS_REGISTRY.json   발견 통합 registry
  mapping/                    논리표 4종 + 보조 2종의 read-only materialization
    analysis_interface.py     A2 §5 대응표의 구현. state/*.parquet 은 읽기만 한다
    test_analysis_interface.py  불변조건 회귀검사 24건 (A2 규칙 V-6)
    MAPPING_REPORT.md
  eda/                        EDA-00 / EDA-01
    eda00_frame_provenance.py   Frame & Provenance Audit  → out/eda00/
    eda01_source_structure.py   Source Structure          → out/eda01/
    EDA00_REPORT.md · EDA01_REPORT.md
  codebook/                   Business Domain 8 + Interaction Archetype 7
    FUNCTIONAL_CODEBOOK.md · codebook.json · OPEN_QUESTIONS.md
  pilot/                      P-A A5 pilot mapping (source-context only)
    pilot_mapping.py · PILOT_MAPPING_REPORT.md → out/pilot/
  out/                        재실행으로 생성되는 산출물 (스크립트가 만든다)
```

## 재현

```bash
PY=/home/sieg/projects-wsl/ProjectFinal/.venv/bin/python
A=research/landing_accessibility/analysis          # 절대경로로 지정할 것
cd $A/mapping && $PY -m pytest -q                  # 24 passed
cd $A/eda     && $PY eda00_frame_provenance.py     # → ../out/eda00/
cd $A/eda     && $PY eda01_source_structure.py     # → ../out/eda01/
cd $A/pilot   && $PY pilot_mapping.py              # → ../out/pilot/  (오염 검사 CLEAN 이어야 통과)
```

세 스크립트 모두 **자기 워크트리의 `state/`** 를 읽는다 (`$LANDING_STATE_DIR` 로 재지정 가능).
다른 워크트리를 하드코딩하지 않는다 — 동시 작업 중인 lane 에 결과가 좌우되면 격리가 깨진다.

**`state/*.parquet` 은 읽기 전용이다.** rename·migrate·write 금지 (`A2` 규칙 V-1/V-4/V-5).
`materialize_all()` 은 산출 디렉터리가 원본과 같으면 거부한다.

## 교차오염 경계 (`PHASE_GATES` §4.6)

| 산출물 | 인증·KWCAG·popup·depth·accessibility outcome |
|---|---|
| `mapping/` | **입력 아님** |
| `pilot/` | **입력 아님.** `builtins.open` allowlist 로 코드 강제 + 매 run 차단 자체 시험 |
| `eda/eda00` | 인증 원자료를 **provenance·grain 감사 대상**으로만 읽는다. 매핑·task 선정 입력으로 쓰지 않는다 (§4.2 허용) |
| `eda/eda01` | `state/` 만 |

## 미결

`codebook/OPEN_QUESTIONS.md` — Q-1 **CLOSED**(`A2` §1.5.1a), Q-2~Q-8 OPEN, **Q-9 신설**.
Q-2(`UTILITY_ENTRY` endpoint)는 SHADOW lane 이 **결정하지 않았다.** 근거만 갱신했다.
