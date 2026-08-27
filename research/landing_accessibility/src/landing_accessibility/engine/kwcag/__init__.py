"""W3 — KWCAG production evaluator, Stage 0 (criterion manifest freeze) ONLY.

`T-A-W3-001` / `D-R0-43` precondition: manifest freeze 이전에는 evaluator 구현을
시작하지 않는다. 이 패키지는 현재 데이터(criterion_manifest.json)와 그 freeze
기록(MANIFEST_FREEZE.json)만 담는다.

`Applicability → Required evidence slots → Expectation → Outcome` 4단계 evaluator
(Stage 1)는 A 의 ACK 이후 별도 커밋에서 추가한다 — 이 모듈은 그 로직을 갖지 않는다.
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
