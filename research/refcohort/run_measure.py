#!/usr/bin/env python3
"""R1 측정 배치 — REFERENCE + COMPARISON 코호트를 동일 파이프라인으로 측정한다."""

from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from refcohort.guard import run_guard, write_guard_report
from refcohort.pipeline import load_records, run_batch
from refcohort.report import build

RUN_ID = sys.argv[1] if len(sys.argv) > 1 else "r1"
AUDIT = date(2026, 8, 26).isoformat()
ROOT = Path(__file__).parent
RUN_DIR = ROOT / "runs" / RUN_ID
LIMIT = int(sys.argv[2]) if len(sys.argv) > 2 else 0

targets: list[dict] = []
for f in ("reference_targets.json", "comparison_targets.json"):
    targets += json.loads((ROOT / "state" / f).read_text(encoding="utf-8"))
if LIMIT:
    ref = [t for t in targets if t["cohort"] == "REFERENCE"][:LIMIT]
    cmp_ = [t for t in targets if t["cohort"] == "COMPARISON"][:LIMIT]
    targets = ref + cmp_

print(
    f"[{RUN_ID}] 대상 {len(targets)}건 "
    f"(REFERENCE {sum(1 for t in targets if t['cohort'] == 'REFERENCE')}, "
    f"COMPARISON {sum(1 for t in targets if t['cohort'] == 'COMPARISON')})",
    flush=True,
)

stat = run_batch(targets, RUN_DIR, RUN_ID, AUDIT, workers=3, progress_every=10)
print(json.dumps(stat, ensure_ascii=False), flush=True)

records = load_records(RUN_DIR / "records.jsonl")
g = run_guard(records)
write_guard_report(g, RUN_DIR / "guard_report.json")
print(f"[guard] {g['status']} errors={g['error_count']} warns={g['warn_count']}", flush=True)

rep = build(records, RUN_ID, AUDIT)
(RUN_DIR / "report.json").write_text(
    json.dumps(rep, ensure_ascii=False, indent=2), encoding="utf-8"
)
for c in rep["cohorts"]:
    print(
        f"[{c['cohort']}] 대상 {c['targets']} 측정 {c['measured']} 차단 {c['blocked']} "
        f"strict_pass={c['observed_strict_pass']} 평균미흡항목={c['failed_criteria_per_service']['mean']}",
        flush=True,
    )
print("DONE_MEASURE", flush=True)
