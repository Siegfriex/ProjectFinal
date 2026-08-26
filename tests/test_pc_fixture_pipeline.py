"""P-C FIXTURE — pipeline.run_l0_batch 엔드투엔드 smoke.

append-only 가 실제로 파이프라인에 물려 있는지(정의만 되고 안 불리는 실수가
없는지) 확인하는 자리. 배치가 끝나면 evidence_manifest.verify_run 이
VERIFIED 를 내야 한다 — manifest 가 실제 evidence 파일과 바이트까지 일치한다는 뜻이다.
"""

from __future__ import annotations

import sys
from pathlib import Path

RESEARCH = Path(__file__).resolve().parents[1] / "research" / "landing_accessibility"
sys.path.insert(0, str(RESEARCH / "src"))

from landing_accessibility.evidence_manifest import verify_run  # noqa: E402
from landing_accessibility.pc_fixture.pipeline import run_l0_batch  # noqa: E402

FIXTURES = RESEARCH / "tests" / "pc_fixture" / "fixtures"


def test_run_l0_batch_end_to_end_verified(tmp_path):
    targets = [
        {
            "fixture_path": str(FIXTURES / "clean_landing.html"),
            "service_id": "svc_clean",
            "canonical_url": "https://example.com/clean",
            "audit_date": "2026-08-27",
            "protocol_version": "v2.0",
        },
        {
            "fixture_path": str(FIXTURES / "popup_blocking.html"),
            "service_id": "svc_popup",
            "canonical_url": "https://example.com/popup",
            "audit_date": "2026-08-27",
            "protocol_version": "v2.0",
        },
    ]
    result = run_l0_batch(
        run_root=tmp_path, run_id="run_pipeline_smoke", targets=targets, execution_mode="FIXTURE"
    )
    assert len(result.observations) == 2
    assert result.finalize_report["status"] == "OK"

    report = verify_run(result.run_dir, require_files=True)
    assert report["status"] == "VERIFIED"
    # dom/ax/screen/screen_full/probe = 5 종 * 2 관측 = 10 entries
    assert report["entries"] == 10
    assert report["observations"] == 2
