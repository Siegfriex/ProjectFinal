#!/usr/bin/env python3
"""기존 run의 증거(probe)로 판정만 다시 수행한다.

수집은 append-only로 보존하고 판정 로직 변경분만 새 run에 기록한다.
사이트에 다시 요청하지 않으므로 부하가 없고, 원 증거의 해시도 그대로 유지된다.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from refcohort.criteria import judge
from refcohort.guard import run_guard, write_guard_report
from refcohort.report import build

SRC = sys.argv[1] if len(sys.argv) > 1 else "r2"
DST = sys.argv[2] if len(sys.argv) > 2 else "r3"
ROOT = Path(__file__).parent
src_dir, dst_dir = ROOT / "runs" / SRC, ROOT / "runs" / DST
dst_dir.mkdir(parents=True, exist_ok=True)

rows = [
    json.loads(x)
    for x in (src_dir / "records.jsonl").read_text(encoding="utf-8").splitlines()
    if x.strip()
]
out, rejudged = [], 0
for r in rows:
    r = dict(r)
    r["run_id"] = DST
    r["rejudged_from"] = SRC
    ref = r.get("probe_ref")
    if r.get("collection_status") == "MEASURED" and ref and Path(ref).exists():
        probe = json.loads(Path(ref).read_text(encoding="utf-8"))
        j = judge(probe)
        r["criteria"], r["summary"] = j["criteria"], j["summary"]
        rejudged += 1
    out.append(r)

(dst_dir / "records.jsonl").write_text(
    "\n".join(json.dumps(x, ensure_ascii=False) for x in out), encoding="utf-8"
)
g = run_guard(out)
write_guard_report(g, dst_dir / "guard_report.json")
audit_date = out[0]["audit_date"] if out else ""
rep = build(out, DST, audit_date)
(dst_dir / "report.json").write_text(
    json.dumps(rep, ensure_ascii=False, indent=2), encoding="utf-8"
)
print(f"[{DST}] {SRC}의 증거로 재판정: {rejudged}/{len(out)}건")
print(f"[guard] {g['status']} errors={g['error_count']} warns={g['warn_count']}")
for c in rep["cohorts"]:
    print(
        f"[{c['cohort']}] 측정 {c['measured']} 미흡0={c['observed_strict_pass'].get('TRUE', 0)} "
        f"평균미흡={c['failed_criteria_per_service']['mean']}"
    )
