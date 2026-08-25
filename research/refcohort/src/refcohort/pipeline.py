"""대상 목록을 받아 수집 → 판정 → 레코드로 만드는 러너.

각 대상은 서로 독립이므로 프로세스 수준에서 병렬화한다.
실패는 삭제하지 않고 분모에 남긴다(프로토콜 v2 §8, quarantine_policy).
"""

from __future__ import annotations

import json
import traceback
from concurrent.futures import ProcessPoolExecutor, as_completed
from datetime import UTC, datetime
from pathlib import Path

from .collect import collect_one, to_row
from .criteria import judge

NULLS_PRESERVED = {
    "reference_distribution": None,
    "cluster_label": None,
    "reference_deviation_score": None,
    "reference_percentile": None,
    "commercial_distance": None,
}


def measure_one(task: dict) -> dict:
    """대상 1건: 수집 + 판정. 예외는 레코드로 흡수한다."""
    run_dir = Path(task["run_dir"])
    rid = task["record_id"]
    base = {
        "record_id": rid,
        "cohort": task["cohort"],
        "service_name": task["service_name"],
        "organization_name": task.get("organization_name"),
        "primary_task_code": task["primary_task_code"],
        "certification_number": task.get("certification_number"),
        "cert_start_date": task.get("cert_start_date"),
        "cert_end_date": task.get("cert_end_date"),
        "certification_status_observed": task.get("certification_status_observed"),
        "url_status": task.get("url_status"),
        "evidence_rows": task.get("evidence_rows") or [],
        "source": task.get("source"),
        "run_id": task["run_id"],
        "audit_date": task["audit_date"],
        **NULLS_PRESERVED,
    }
    if not task.get("url"):
        return {
            **base,
            "target_url": None,
            "collection_status": "NO_URL",
            "failure_code": "URL_DISCOVERY_REQUIRED",
            "evidence_complete": False,
            "criteria": {},
            "summary": None,
        }
    try:
        res = collect_one(rid, task["url"], run_dir, task["run_id"])
        row = to_row(res)
        rec = {**base, **row}
        if res.probe and res.evidence_complete:
            j = judge(res.probe)
            rec["criteria"] = j["criteria"]
            rec["summary"] = j["summary"]
            rec["collection_status"] = "MEASURED"
            rec["failure_code"] = "NONE"
        else:
            rec["criteria"] = {}
            rec["summary"] = None
            rec["collection_status"] = (
                "COLLECTION_BLOCKED" if res.transport_error else "EVIDENCE_INSUFFICIENT"
            )
            rec["failure_code"] = "TRANSPORT_FAILURE" if res.transport_error else "EVIDENCE_THIN"
        return rec
    except Exception as e:
        return {
            **base,
            "target_url": task.get("url"),
            "collection_status": "RUNNER_ERROR",
            "failure_code": f"{type(e).__name__}",
            "failure_detail": traceback.format_exc()[-1500:],
            "evidence_complete": False,
            "criteria": {},
            "summary": None,
        }


def run_batch(
    targets: list[dict],
    run_dir: Path,
    run_id: str,
    audit_date: str,
    *,
    workers: int = 3,
    out_name: str = "records.jsonl",
    progress_every: int = 10,
) -> dict:
    run_dir.mkdir(parents=True, exist_ok=True)
    tasks = [
        {**t, "run_dir": str(run_dir), "run_id": run_id, "audit_date": audit_date} for t in targets
    ]
    out_path = run_dir / out_name
    done, ok, blocked = 0, 0, 0
    started = datetime.now(UTC).isoformat()
    with out_path.open("w", encoding="utf-8") as f, ProcessPoolExecutor(max_workers=workers) as ex:
        futs = {ex.submit(measure_one, t): t for t in tasks}
        for fut in as_completed(futs):
            rec = fut.result()
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
            f.flush()
            done += 1
            if rec["collection_status"] == "MEASURED":
                ok += 1
            else:
                blocked += 1
            if done % progress_every == 0:
                print(f"  진행 {done}/{len(tasks)}  측정 {ok}  차단 {blocked}", flush=True)
    return {
        "run_id": run_id,
        "started_at": started,
        "finished_at": datetime.now(UTC).isoformat(),
        "targets": len(tasks),
        "measured": ok,
        "blocked": blocked,
        "records_path": str(out_path),
    }


def load_records(path: Path) -> list[dict]:
    return [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines() if x.strip()]
