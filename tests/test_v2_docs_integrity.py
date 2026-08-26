"""v2 문서 무결성 검증을 품질 게이트에 연결한다.

`scripts/verify_v2_docs.py` 가 어디에서도 호출되지 않으면 검증이 존재하지 않는 것과
같다 (ssot V2-C001 `install-manifest-is-self-anchored`). 이 테스트가 그 연결이다.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SCRIPT = REPO / "research" / "landing_accessibility" / "scripts" / "verify_v2_docs.py"


def test_v2_docs_integrity() -> None:
    assert SCRIPT.exists(), f"검증 스크립트가 없다: {SCRIPT}"
    proc = subprocess.run(
        [sys.executable, str(SCRIPT)], capture_output=True, text=True, cwd=str(REPO)
    )
    assert proc.returncode == 0, (
        f"V2_DOCS_VERIFY 실패\n--- stdout ---\n{proc.stdout}\n--- stderr ---\n{proc.stderr}"
    )


def test_execution_authority_declares_stop_point() -> None:
    """E001_V2 가 시작되지 않았음을 권위 선언이 유지하는지."""
    doc = (REPO / "research/landing_accessibility/docs/v2/EXECUTION_AUTHORITY.md").read_text(
        encoding="utf-8"
    )
    assert "E001_V2_STARTED                 = false" in doc
    assert "FULL_COLLECTION_STARTED         = NO" in doc
