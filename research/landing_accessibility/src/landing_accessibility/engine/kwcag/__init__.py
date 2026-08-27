"""W3 — KWCAG production evaluator.

Stage 0(criterion manifest freeze)은 `T-A-W3-001`/`D-R0-43` 하에 완료돼 A 가
`D-R0-51` 로 ACCEPT 했다. Stage 1(evaluator: Applicability → Required evidence
slots → Expectation → Outcome)은 그 ACK 이후 착수가 허가됐다(`D-R0-52` 경계 —
구현 대상은 `applicability != OTHER` 인 22개뿐, `OTHER` 11개는 절대 건드리지
않는다).

- Stage 0 산출물: `criterion_manifest.json` · `criterion_manifest.sha256` ·
  `MANIFEST_FREEZE.json` (데이터, 로직 없음).
- Stage 1 산출물: `stage1_types.py`(공용 타입) · `stage1_evidence.py`
  (Applicability + Required evidence slots) · `stage1_expectations.py`
  (Expectation — 5개 criterion 만 실제 구현) · `stage1_pipeline.py`
  (Outcome + 조립, `evaluate_criterion` 이 유일한 공개 진입점).
"""

from __future__ import annotations

import pathlib

#: 이 패키지 디렉터리 — manifest·freeze 파일 위치를 상대경로로 되찾을 때 쓴다.
PACKAGE_DIR = pathlib.Path(__file__).resolve().parent

#: 동결된 criterion manifest (33개 전수, 5개 필수 필드 + 원본 유래 부가 필드).
CRITERION_MANIFEST_PATH = PACKAGE_DIR / "criterion_manifest.json"

#: manifest 파일의 sha256 sidecar.
CRITERION_MANIFEST_SHA256_SIDECAR = PACKAGE_DIR / "criterion_manifest.sha256"

#: freeze 기록 — sha256·criterion 개수·provenance 요약.
MANIFEST_FREEZE_PATH = PACKAGE_DIR / "MANIFEST_FREEZE.json"
