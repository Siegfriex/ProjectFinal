# Claude D — Independent DS/ML Research Sandbox

**Plane**: D (A=Governor, B=Production, C=Assurance, **D=Independent Research Sandbox**)
**Branch**: `claude-d/research-sandbox-v21`
**Base SHA**: `bc0b7a087faf2328cbafdfa9b40bd426c5080d7d` (= remote `research/landing-accessibility-main`)
**주 독자**: Research Director, 외부 watcher

## 이 디렉터리가 무엇인가

D는 A/B/C의 작업을 대신하지 않는다. A/B/C가 만든 **주장·이상현상·측정실패를
독립적인 데이터사이언스 연구질문으로 바꾸어** raw evidence에서 직접 재검증한다.

티켓은 명령이 아니라 research trigger다. 누가 말했는지는 evidence weight가 아니다.

## 직접 확인 우선순위 (Truth hierarchy)

1. raw evidence / runtime artifact
2. exact Git SHA의 source code
3. independently reconstructed data
4. frozen measurement definition
5. A/B/C의 자연어 보고 ← **여기서부터는 hypothesis일 뿐**

A/B/C 보고와 직접 관측이 충돌하면 보고를 따르지 않고 **충돌 자체를 연구결과로 기록**한다.

## Write scope

```
research/landing_accessibility/research_d/**
research/landing_accessibility/notebooks/d_research/**
```

그 외 전부 READ ONLY. 특히 `control/**`, `src/landing_accessibility/engine/**`,
`e001_runner/**`, canonical mart, A/B/C branch, raw evidence, frozen label,
authoritative SSOT는 수정 금지.

D discovers → Research Director evaluates → A formalizes → B implements → C validates.

## 파일

| 파일 | 내용 |
|---|---|
| `SSOT_INTERNALIZATION_v21.md` | SSOTV2 = 단일 SSOT 내재화 기록 + 문서 대 사실 불일치 대장 |
| `INPUT_SNAPSHOT_v21.json` | 입력 동결: SSOT 해시 · remote heads · evidence/mart 해시 |
| `D_RESEARCH_QUEUE.md` | 연구질문 큐 (RQ-D1~) |
| `CLAIM_RESEARCH_LEDGER.csv` | A/B/C 주장 → 연구질문 → verdict 추적 |
| `tools/build_input_snapshot.py` | 입력 스냅샷 동결기 (read-only) |
| `tools/rq_d1_reconstruct.py` | RQ-D1 독립 재구성 |
| `tools/build_observation_table.py` | 관측단위 공용 테이블 (모든 RQ worker의 단일 입력) |
| `tools/d_mlflow.py` | MLflow run 기록 · 목록 · 보존 매니페스트 |
| `tools/d_heartbeat.py` | 5분 loop heartbeat |
| `tools/d_bus_scan.sh` | D 수신 티켓 스캔 |
| `MLFLOW_RETENTION_MANIFEST.json` | Git 밖 MLflow store의 hash 매니페스트 (03 §9) |
| `results/` | 연구 산출 JSON/MD — **canonical** |

## Label 절대 규칙

D는 gold label producer가 **아니다**. 독립 Labeler의 frozen label 중
calibration split만 사용한다. holdout은 찾지도, 열람하지도, 그것을 보고
모델을 고치지도 않는다. holdout leakage 발견 시 해당 연구는 즉시 INVALID.

## MLflow

D는 notebook과 script를 계속 만든다. 어떤 입력 스냅샷에서 어떤 코드 SHA로 어떤
숫자가 나왔는지가 run 단위로 남지 않으면 나중에 "그 수치가 어느 시점 것이냐"를
다시 재구성해야 한다. MLflow는 그 lineage를 잡는 용도다.

```
tracking URI : http://127.0.0.1:5000
experiment   : landing_accessibility_D_v21
backend      : sqlite:///artifacts/mlflow_d/mlflow.db
artifact root: artifacts/mlflow_d/mlartifacts   (git-ignored)
```

기동:

```bash
.venv/bin/mlflow server \
  --backend-store-uri sqlite:////home/sieg/projects-wsl/ProjectFinal/artifacts/mlflow_d/mlflow.db \
  --default-artifact-root file:///home/sieg/projects-wsl/ProjectFinal/artifacts/mlflow_d/mlartifacts \
  --host 127.0.0.1 --port 5000
```

기록:

```bash
.venv/bin/python .../research_d/tools/d_mlflow.py sync      # results/ 스캔 → 신규/변경 RQ만 기록 (멱등)
.venv/bin/python .../research_d/tools/d_mlflow.py list      # run 요약
.venv/bin/python .../research_d/tools/d_mlflow.py manifest  # Git 밖 store의 hash 매니페스트 갱신
```

`sync`는 5분 loop가 자동 실행한다. 멱등성은 `d.rq_id + d.result_sha256` 태그로
보장한다 — 같은 결과 파일이면 run을 다시 만들지 않는다.

각 run에 자동으로 붙는 태그:

`d.rq_id` · `d.verdict` · `d.plane` · `d.authority=NON_AUTHORITATIVE` · `d.branch` ·
`d.head_sha` · `d.base_sha` · `d.worktree_dirty` · `d.input_snapshot_sha256` ·
`d.result_sha256` · `d.production_modified=false` · `d.labels_produced=false` ·
`d.holdout_accessed=false` · `d.limitation`

artifact로 `result/`(FINDINGS.md · results JSON · INPUT_SNAPSHOT), `notebook/`, `code/`(tools 전량)를 첨부한다.

### MLflow는 권위가 아니다

canonical 산출은 **Git의 `results/*.json`** 이고 MLflow는 그것을 가리키는 index다.
MLflow에만 있는 숫자는 연구결과가 아니다. store가 Git 밖에 있으므로
`MLFLOW_RETENTION_MANIFEST.json`으로 노출한다 (03 §9 — "로컬에 있다"는 문장만으로
인계하지 않는다).
