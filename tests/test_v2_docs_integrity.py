"""v2 문서 무결성 검증을 품질 게이트에 연결한다.

`scripts/verify_v2_docs.py` 가 어디에서도 호출되지 않으면 검증이 존재하지 않는 것과
같다 (ssot V2-C001 `install-manifest-is-self-anchored`). 이 테스트가 그 연결이다.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest

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


def _forge_banner(path: Path) -> bytes:
    """설치본 최상단에 위조 배너를 삽입한 바이트를 만든다."""
    return (
        b"<!-- INSTALLED-BANNER-START -->\n> forged\n<!-- INSTALLED-BANNER-END -->\n\n"
        + path.read_bytes()
    )


@pytest.mark.parametrize(
    "rel",
    [
        "docs/v2/00_SSOT_v2.0.md",
        "docs/v2/A1_MEASUREMENT_OPERATIONALIZATION.md",
        "docs/v2/A2_VOCABULARY_AND_SCHEMA_BINDING.md",
        "docs/v2/EXECUTION_AUTHORITY.md",
        "docs/v2/PHASE_GATES.md",
    ],
)
def test_banner_injection_is_rejected(rel: str, tmp_path: Path) -> None:
    """권위문서에 배너를 넣고 매니페스트 해시까지 갱신해도 검증은 실패해야 한다.

    adversarial V2-C003 이 `00_SSOT` 로, Codex V2-C004 가 repo-authored 문서로
    각각 PASS 를 받아냈다. 두 경로 모두 회귀로 고정한다.
    """
    root = REPO / "research" / "landing_accessibility"
    target, manifest_path = root / rel, root / "docs/v2/INSTALL_MANIFEST.json"
    original, manifest_original = target.read_bytes(), manifest_path.read_bytes()
    try:
        forged = _forge_banner(target)
        target.write_bytes(forged)
        manifest = json.loads(manifest_original.decode("utf-8"))
        entry = manifest["files"][rel]
        entry["bytes"] = len(forged)
        entry["sha256"] = hashlib.sha256(forged).hexdigest()
        manifest_path.write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        proc = subprocess.run(
            [sys.executable, str(SCRIPT)], capture_output=True, text=True, cwd=str(REPO)
        )
        assert proc.returncode != 0, f"{rel} 배너 위조가 통과했다:\n{proc.stdout}"
        # returncode 만 보면 vacuous 하다 — 매니페스트를 쓰는 순간 워킹트리가 오염되어
        # git 앵커 검사가 배너와 무관하게 실패시키기 때문이다. 두 감사(V2-C005 ssot F1 /
        # adversarial banner-policy-regression-tests-pass-vacuously)가 배너 강제 블록을
        # 제거한 변형으로 5/5 여전히 통과함을 실증했다. 차단 **사유**를 확인한다.
        combined = proc.stdout + proc.stderr
        assert "BANNER" in combined, (
            f"{rel}: 차단됐으나 사유가 배너가 아니다 — 이 테스트는 배너 강제를 검증하지 못한다\n"
            f"{combined}"
        )
    finally:
        target.write_bytes(original)
        manifest_path.write_bytes(manifest_original)


def test_non_banner_mutation_does_not_report_banner(tmp_path: Path) -> None:
    """대조군 — 배너 없는 변조는 BANNER 가 아닌 사유로 잡혀야 한다.

    이 테스트가 없으면 위 회귀 테스트가 "무엇이든 BANNER 를 출력한다"는 상황을
    구별하지 못한다.
    """
    root = REPO / "research" / "landing_accessibility"
    target = root / "docs/v2/A1_MEASUREMENT_OPERATIONALIZATION.md"
    original = target.read_bytes()
    try:
        target.write_bytes(original + "\n<!-- 배너 마커 없는 꼬리 변조 -->\n".encode())
        proc = subprocess.run(
            [sys.executable, str(SCRIPT)], capture_output=True, text=True, cwd=str(REPO)
        )
        combined = proc.stdout + proc.stderr
        assert proc.returncode != 0, "본문 변조가 통과했다"
        assert "BANNER" not in combined, f"배너가 아닌데 BANNER 로 보고됐다:\n{combined}"
    finally:
        target.write_bytes(original)
