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
| `results/` | 연구 산출 JSON/MD |

## Label 절대 규칙

D는 gold label producer가 **아니다**. 독립 Labeler의 frozen label 중
calibration split만 사용한다. holdout은 찾지도, 열람하지도, 그것을 보고
모델을 고치지도 않는다. holdout leakage 발견 시 해당 연구는 즉시 INVALID.
