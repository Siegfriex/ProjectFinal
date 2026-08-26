# CR-001 — SHADOW_MANIFEST.json artifact_sha256 mismatch (1 of 27)

- 제기자: Claude B — P-A-QA (lane `claude-b/pa-qa`, base `agent/landing-pa-shadow` @ `0f46203`)
- 대상: `agent/landing-pa-shadow` @ `0f46203` — 이 CR은 그 브랜치를 직접 수정하지 않는다
- 심각도(제안): **P2** — provenance 정합성 결함. real-target 오염이나 판정 오류는 아니지만
  `SHADOW_MANIFEST.json`이 자기 자신의 핵심 약속(§4.3 hash 검증)에서 실패한다
- 판정 권한: P-A 감사 (adversarial + ssot)

## 재현

```bash
cd <worktree>/research/landing_accessibility
python3 - <<'EOF'
import json, hashlib, os
m = json.load(open("analysis/SHADOW_MANIFEST.json"))
for rel, expected in m["artifact_sha256"].items():
    actual = hashlib.sha256(open(rel, "rb").read()).hexdigest()
    if actual != expected:
        print(rel, "expected", expected, "actual", actual)
EOF
```

출력:

```
analysis/out/pilot/mapping_run_manifest.json expected daf9ee21afcbe307d7bad87e2f029ba901cc0721dc5b283fe27d9cca4579e2e3 actual 6f0f384ac33ac390644a78659c97ee67767dbcb20facef064fb435d47c983ba8
```

## 검증한 것

- 이것은 워크트리 로컬 변경 때문이 아니다. `git status --porcelain`은 비어 있고,
  `git show 0f46203:research/landing_accessibility/analysis/out/pilot/mapping_run_manifest.json | sha256sum`이
  워킹트리 파일과 동일한 `6f0f384a...`를 낸다 — 즉 **커밋된 blob 자체가 자신의 manifest 항목과 불일치**한다.
- 재실행(`pilot_mapping.py`)으로 만든 새 `mapping_run_manifest.json`도 커밋본과 다르다.
  다만 그 차이는 예상된 것이다 — `run_started_at`/`run_finished_at` 타임스탬프와
  실행 워크트리 절대경로(`guard_selftest`/`contamination_check` 안의 `.../landing_pa_shadow/...` vs
  `.../claude_b_pa_qa/...`)가 실행마다 달라지므로 이 파일은 원천적으로 바이트 재현 불가능하다.
  → **이 파일의 hash를 "고정값"으로 manifest에 박아두는 설계 자체가 이 파일의 성격과 맞지 않는다.**
- `pilot_mapping.jsonl`(실제 매핑 결과, 27건 중 이 파일 제외 나머지 26건 포함)은 재실행해도
  **바이트 동일**했다. 매핑 로직 자체의 결정성은 문제없다.

## 원인 추정 (확정 아님)

`SHADOW_MANIFEST.json`의 `artifact_sha256` 테이블이 계산된 시점과, 최종 커밋된
`mapping_run_manifest.json`이 마지막으로 다시 쓰인 시점이 어긋난 것으로 보인다
(예: manifest 표를 만든 뒤 pilot을 한 번 더 돌려 타임스탬프가 바뀐 새 파일을 커밋하면서
표를 재계산하지 않았을 가능성).

## 권고

1. `mapping_run_manifest.json`처럼 실행마다 타임스탬프/절대경로가 바뀌는 파일은
   `artifact_sha256` 고정-해시 목록에서 제외하거나, 별도 카테고리
   (`non_reproducible_but_present` 등)로 분리해 "이 파일은 존재를 확인하되 바이트 동일성은 검증 대상이 아니다"를
   명시한다.
2. 위 방침을 정하기 전까지는 현재 값을 재계산해 커밋된 blob과 일치시킨다 — 최소한 "manifest가 자기 자신과
   불일치하는 상태"는 남기지 않는다.
3. (사소) `analysis/README.md`가 "산출물 31건"이라 적었으나 실제 `artifact_sha256` 엔트리 수와 커밋 메시지는
   **27건**이다. 문서 오탈자로 보이며 함께 정정을 권한다.

## 영향받지 않는 것

- `source_frame_sha`(state/*.parquet 6종) — 전건 일치 확인함.
- 나머지 26개 `artifact_sha256` 엔트리 — 전건 일치 확인함.
- EDA-00/EDA-01 재현성 — 10개 산출물(PNG 3종 포함) 바이트 동일 재확인함.
- pytest 24 passed, ruff/ruff-format/mypy 전부 통과 재확인함.
