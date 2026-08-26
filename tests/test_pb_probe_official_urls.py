"""P-B — `probe_official_urls.py` 를 서브프로세스로 실제 실행해 방화벽을 검증한다.

C013 게이트 무결성 테스트(`test_c013_gate_integrity.py`)의 교훈을 따른다: 함수를
import 해서 몰래 통과시키지 않고, **스크립트 자체를 실행**해서 exit code 로 확인한다
(빌드는 exit 0 인데 테스트만 잡는 상태를 허용하지 않는다).

이 테스트는 네트워크를 타지 않는다 — `REAL_TARGET` 요청은 requests 세션을 만들기
전에 거부되고, `FIXTURE` 모드는 로컬 JSON 만 읽는다.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
RESEARCH = REPO / "research" / "landing_accessibility"
SCRIPT = RESEARCH / "scripts" / "probe_official_urls.py"

pytestmark = pytest.mark.skipif(not SCRIPT.exists(), reason="probe_official_urls.py 없음")


def _run(args: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        cwd=cwd,
        capture_output=True,
        text=True,
        timeout=30,
    )


def test_real_target_execution_mode_hard_fails_before_any_network(tmp_path: Path) -> None:
    """`--execution-mode REAL_TARGET` 은 candidates 파일이 없어도(=아직 네트워크 전 단계)
    RealTargetFirewallError 로 즉시 죽어야 한다. candidates 파일 부재로 죽으면 이 테스트는
    방화벽이 아니라 파일 부재를 확인한 것이므로 무효 — stderr 에 방화벽 근거가 있어야 한다."""
    result = _run(["--execution-mode", "REAL_TARGET"], cwd=tmp_path)
    assert result.returncode != 0
    assert "REAL_TARGET" in result.stderr
    assert "hard FAIL" in result.stderr or "RealTargetFirewallError" in result.stderr


def test_fixture_mode_without_fixture_path_fails_fast() -> None:
    result = _run(["--execution-mode", "FIXTURE"], cwd=REPO)
    assert result.returncode != 0
    assert "fixture-path" in result.stderr or "fixture-path" in result.stdout


def test_fixture_mode_runs_end_to_end_without_network(tmp_path: Path) -> None:
    """FIXTURE 모드로 전체 파이프라인이 네트워크 없이 완결되는지 확인한다.

    `--candidates-path`/`--output-path` 로 격리된 경로만 쓴다 — 실제 저장소
    `state/url_review_candidates.json`/`url_review_probe.json` 은 건드리지 않는다.
    """
    candidates_path = tmp_path / "candidates.json"
    output_path = tmp_path / "probe_output.json"
    candidates = {
        "candidates": [
            {"canonical_service_key": "example_svc", "candidate_urls": ["https://example.com"]}
        ]
    }
    candidates_path.write_text(json.dumps(candidates, ensure_ascii=False), encoding="utf-8")

    fixture_record = {
        "example_svc\x1fhttps://example.com": {
            "target_url": "https://example.com",
            "http_status": 200,
            "final_url": "https://example.com/",
            "redirect_chain": [],
            "page_title": "Example",
            "content_language": "en",
            "error": None,
            "elapsed_ms": 0,
            "tls_compat_retry": False,
            "final_registered_domain": "example.com",
            "target_registered_domain": "example.com",
        }
    }
    fixture_path = tmp_path / "fixture.json"
    fixture_path.write_text(json.dumps(fixture_record, ensure_ascii=False), encoding="utf-8")

    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--execution-mode",
            "FIXTURE",
            "--fixture-path",
            str(fixture_path),
            "--candidates-path",
            str(candidates_path),
            "--output-path",
            str(output_path),
        ],
        cwd=REPO,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, result.stderr
    assert output_path.exists()
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["probe_count"] == 1
    assert payload["shadow_provenance"]["execution_mode"] == "FIXTURE"
    assert payload["shadow_provenance"]["authoritative"] is False
    assert payload["probes"][0]["http_status"] == 200
    assert payload["probes"][0]["final_registered_domain"] == "example.com"
