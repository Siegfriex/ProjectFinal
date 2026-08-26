#!/usr/bin/env python3
"""C006 — A2 인증 레지스트리 Main Study 자체 스냅샷 수집 실행기.

한국디지털접근성진흥원(KWACC) 웹접근성 인증 목록을 전수 크롤해
sources/certification/ 아래에 원문·레코드·매니페스트를 남긴다.

주의: 이 실행기는 **인증 목록 페이지만** 요청한다. 목록에 실린 대상 서비스 URL에는 접속하지 않는다.

    python research/landing_accessibility/scripts/collect_certification_registry.py
    python research/landing_accessibility/scripts/collect_certification_registry.py --reparse
"""

from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path

RESEARCH_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RESEARCH_ROOT / "src"))

from landing_accessibility.registry import collect_snapshot, reparse_snapshot  # noqa: E402

AUDIT_DATE = date(2026, 8, 26)
SNAPSHOT_ID = "KWACC_WA_" + AUDIT_DATE.strftime("%Y%m%d")
OUT_DIR = RESEARCH_ROOT / "sources" / "certification"


def main(argv: list[str]) -> int:
    if "--reparse" in argv:
        # 재요청 없이 저장된 원문에서만 레코드를 다시 만든다(파서 수정 시).
        records, manifest, paths = reparse_snapshot(OUT_DIR, AUDIT_DATE)
    else:
        records, manifest, paths = collect_snapshot(
            OUT_DIR, AUDIT_DATE, snapshot_id=SNAPSHOT_ID, max_pages=400
        )
    summary = {
        k: manifest[k]
        for k in (
            "snapshot_id",
            "snapshot_status",
            "stop_reason",
            "pages_fetched",
            "pages_with_cards",
            "declared_last_page",
            "rows_raw",
            "rows_dedup",
            "status_breakdown",
            "in_period_at_audit",
            "valid_at_audit",
            "rows_with_target_url",
            "rows_with_scheme_less_target_url",
            "rows_without_period",
            "completeness_notes",
        )
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print(f"records={len(records)}")
    for key, path in paths.items():
        print(f"{key}: {path}")
    return 0 if manifest["snapshot_status"] == "COMPLETE" else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
