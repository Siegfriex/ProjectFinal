#!/usr/bin/env python3
"""Generate three SYNTHETIC V3 evidence trees for GATE 1 (offline) checker validation.

  good/           1 service-task: run 01 = 3 states (S0..S2), 2 steps, REACHED; run 02 = legitimate re-collection under a new
                  run_id, ABSTAIN x terminal_reason=OTHER (+note) x auth_gate_stage=UNDETERMINED, collector hash written as
                  collector_sha256 (T-A-V3-STEP1-015 exact name) and driver hash as session_sha256 (R22 alias). Every row
                  carries engine + driver/session sha (T-A-V3-STEP1-021 R22). Hashes consistent, path manifest bound
  bad_overwrite/  run 01 only, S1/screenshot.png rewritten AFTER the manifest was sealed; flow record REACHED x OTHER (no note)
  bad_lineage/    step 1 references state S9 (absent), S2 screenshot missing,
                  service_id is a display name ("Coupang Mobile App") instead of an id; flow record EVIDENCE_DEFECT with
                  terminal_reason absent and auth_gate_stage=NONE, and WITHOUT driver_sha256 (R22 negative control)

No real service data. Layout follows C's EVIDENCE_CONTRACT_C.md (pre-registered layout):
  <root>/<service_id>/<task_id>/<run_id>/evidence_manifest.jsonl
  <root>/<service_id>/<task_id>/<run_id>/S<k>/{dom.html,ax.json,screenshot.png,probe.json,control_facts.json}
  <root>/path_manifest.json  -> binds evidence_manifest.jsonl by sha256
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
FIXTURES = HERE / "fixtures"

SERVICE_ID = "svc_coupang_m"
TASK_ID = "T07_search_product"
RUN_ID = "run_20260828T000000Z_01"
RUN_ID_2 = "run_20260828T001000Z_02"   # re-collection of the same service-task = NEW run id (06 §6)
ATTEMPT_ID = "a1"
COLLECTOR_SHA = "c0ffee00" * 5          # 40 hex  (engine)
DRIVER_SHA = "d21ae500" * 5            # 40 hex  (driver/session — T-A-V3-STEP1-021 R22: engine sha + driver sha on every row)
PROTOCOL_SHA = "5e05da9" + "0" * 33     # 40 hex
TASK_CONTRACT_SHA = hashlib.sha256(b"task_contract:T07").hexdigest()
ENDPOINT_CONTRACT_SHA = hashlib.sha256(b"endpoint_contract:T07").hexdigest()
URLS = ["https://m.example.test/", "https://m.example.test/?menu=open", "https://m.example.test/search?q=x"]
ARTIFACTS = {
    "dom": "dom.html",
    "ax": "ax.json",
    "screenshot": "screenshot.png",
    "probe": "probe.json",
    "control_facts": "control_facts.json",
}
PNG_HEADER = b"\x89PNG\r\n\x1a\n"


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def artifact_bytes(kind: str, k: int) -> bytes:
    if kind == "dom":
        return f"<html><body data-state='S{k}'><button aria-label='search'>검색</button></body></html>".encode()
    if kind == "ax":
        return json.dumps({"role": "WebArea", "state": f"S{k}", "children": [{"role": "button", "name": "search"}]}).encode()
    if kind == "screenshot":
        return PNG_HEADER + f"synthetic-frame-S{k}".encode() * 8
    if kind == "probe":
        return json.dumps({"state": f"S{k}", "bbox": [12, 40 + 10 * k, 120, 44], "css": {"position": "fixed"}}).encode()
    if kind == "control_facts":
        return json.dumps({"state": f"S{k}", "selector": "button[aria-label=search]", "role": "button",
                           "visible_text": "검색", "accessible_name": "search"}).encode()
    raise KeyError(kind)


def flow_record(service_id: str, run_id: str, n_steps: int, *, endpoint_status: str, terminal_reason,
                auth_gate_stage: str, terminal_note: str | None = None, omit_terminal_reason: bool = False,
                collector_field: str = "collector_sha", driver_field: str | None = "driver_sha256") -> dict:
    """fact_flow_observation (02 §4) + R11/R13 fields. One per run.
    collector_field: source name of the collector hash — "collector_sha" (C canonical) or "collector_sha256"
    (exact name in T-A-V3-STEP1-015; accepted through FIELD_ALIASES)."""
    r = {
        "record_kind": "flow",
        "flow_observation_id": f"{service_id}.{TASK_ID}.{run_id}.{ATTEMPT_ID}.flow",
        "service_id": service_id, "task_id": TASK_ID, "run_id": run_id, "attempt_id": ATTEMPT_ID,
        "endpoint_status": endpoint_status, "terminal_reason": terminal_reason, "auth_gate_stage": auth_gate_stage,
        "flow_step_count": n_steps, "activation_depth": n_steps, "forced_dismissal_count": 0,
        "path_manifest_path": "path_manifest.json",
        "captured_at": datetime(2026, 8, 28, 0, 0, 30, tzinfo=timezone.utc).isoformat(),
        collector_field: COLLECTOR_SHA, "protocol_sha": PROTOCOL_SHA,
        "task_contract_sha256": TASK_CONTRACT_SHA, "endpoint_contract_sha256": ENDPOINT_CONTRACT_SHA,
    }
    if driver_field:                       # None = R22 negative control (flow record without the driver/session sha)
        r[driver_field] = DRIVER_SHA
    if terminal_note is not None:
        r["terminal_note"] = terminal_note
    if omit_terminal_reason:
        del r["terminal_reason"]
    return r


def build(root: Path, *, service_id: str = SERVICE_ID, run_id: str = RUN_ID, n_states: int = 3,
          base_time: datetime | None = None, collector_field: str = "collector_sha",
          driver_field: str = "driver_sha256") -> tuple[Path, list[dict], list[dict]]:
    """Write states + steps + manifest. Returns (manifest_path, state_records, step_records)."""
    base_time = base_time or datetime(2026, 8, 28, 0, 0, 0, tzinfo=timezone.utc)
    run_dir = root / service_id / TASK_ID / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    states: list[dict] = []
    for k in range(n_states):
        sdir = run_dir / f"S{k}"
        sdir.mkdir(exist_ok=True)
        arts = {}
        for kind, fname in ARTIFACTS.items():
            data = artifact_bytes(kind, k)
            (sdir / fname).write_bytes(data)
            arts[kind] = {"path": f"S{k}/{fname}", "sha256": sha256_bytes(data), "bytes": len(data)}
        states.append({
            "record_kind": "state",
            "observation_id": f"{service_id}.{TASK_ID}.{run_id}.{ATTEMPT_ID}.S{k}",
            "service_id": service_id,
            "task_id": TASK_ID,
            "run_id": run_id,
            "attempt_id": ATTEMPT_ID,
            "state_index": f"S{k}",
            "url": URLS[k % len(URLS)],
            "captured_at": (base_time + timedelta(seconds=5 * k)).isoformat(),
            collector_field: COLLECTOR_SHA,
            driver_field: DRIVER_SHA,
            "protocol_sha": PROTOCOL_SHA,
            "task_contract_sha256": TASK_CONTRACT_SHA,
            "endpoint_contract_sha256": ENDPOINT_CONTRACT_SHA,
            "scroll_y": 0 if k == 0 else 320 * k,
            "viewport_width": 390, "viewport_height": 844,
            "artifacts": arts,
        })
    steps: list[dict] = []
    for i in range(n_states - 1):
        b, a = states[i], states[i + 1]
        steps.append({
            "record_kind": "step",
            "flow_observation_id": f"{service_id}.{TASK_ID}.{run_id}.{ATTEMPT_ID}.flow",
            "service_id": service_id, "task_id": TASK_ID, "run_id": run_id, "attempt_id": ATTEMPT_ID,
            "step_index": i,
            "action_token": "TAP" if i == 0 else "TYPE",
            "state_before_id": b["observation_id"],
            "state_after_id": a["observation_id"],
            "control_selector": "button[aria-label=search]", "control_role": "button",
            "control_visible_text": "검색", "control_accessible_name": "search",
            "bbox_before": [12, 40 + 10 * i, 120, 44],
            "url_before": b["url"], "url_after": a["url"],
            "auth_gate_detected": False, "endpoint_signal_detected": i == n_states - 2,
            "dom_sha256_before": b["artifacts"]["dom"]["sha256"], "dom_sha256_after": a["artifacts"]["dom"]["sha256"],
            "ax_sha256_before": b["artifacts"]["ax"]["sha256"], "ax_sha256_after": a["artifacts"]["ax"]["sha256"],
            "screenshot_sha256_before": b["artifacts"]["screenshot"]["sha256"],
            "screenshot_sha256_after": a["artifacts"]["screenshot"]["sha256"],
            "captured_at": (base_time + timedelta(seconds=5 * i + 3)).isoformat(),
            collector_field: COLLECTOR_SHA, driver_field: DRIVER_SHA, "protocol_sha": PROTOCOL_SHA,
            "task_contract_sha256": TASK_CONTRACT_SHA, "endpoint_contract_sha256": ENDPOINT_CONTRACT_SHA,
        })
    return run_dir / "evidence_manifest.jsonl", states, steps


def write_manifest(mpath: Path, states: list[dict], steps: list[dict], flow: dict | None = None) -> None:
    with mpath.open("w", encoding="utf-8") as f:
        for r in states + steps + ([flow] if flow else []):
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


def write_path_manifest(root: Path, entries: list[tuple[Path, str, str]]) -> None:
    pm = {
        "path_manifest_version": "C-v3-prereg",
        "frozen": True,
        "runs": [{
            "service_id": service_id, "task_id": TASK_ID, "run_id": run_id,
            "evidence_manifest": str(mpath.relative_to(root)),
            "evidence_manifest_sha256": sha256_file(mpath),
        } for mpath, service_id, run_id in entries],
    }
    (root / "path_manifest.json").write_text(json.dumps(pm, indent=2, ensure_ascii=False) + "\n")


def set_mtime(p: Path, when: float) -> None:
    os.utime(p, (when, when))


def main() -> int:
    if FIXTURES.exists():
        shutil.rmtree(FIXTURES)
    now = time.time()

    # (a) good: run 01 REACHED (terminal_reason null, auth NONE observed); run 02 = legitimate re-collection under a NEW
    #     run_id, ABSTAIN x OTHER + note x auth UNDETERMINED (R11/R13 positive cases)
    root = FIXTURES / "good"
    mpath, states, steps = build(root)
    write_manifest(mpath, states, steps, flow_record(SERVICE_ID, RUN_ID, len(steps), endpoint_status="REACHED",
                                                     terminal_reason=None, auth_gate_stage="NONE"))
    # run 02 writes the collector hash under the T-A-V3-STEP1-015 exact name collector_sha256 (FIELD_ALIASES positive control:
    # a checker lacking the alias would report MISSING_FIELD collector_sha on every run-02 record)
    # run 02 also writes the driver/session hash under the alias session_sha256 (R22 alias positive control)
    mpath2, states2, steps2 = build(root, run_id=RUN_ID_2, n_states=1, collector_field="collector_sha256", driver_field="session_sha256")
    write_manifest(mpath2, states2, steps2, flow_record(
        SERVICE_ID, RUN_ID_2, 0, endpoint_status="ABSTAIN", terminal_reason="OTHER", auth_gate_stage="UNDETERMINED",
        terminal_note="two equally plausible search entry controls; replay not attempted", collector_field="collector_sha256",
        driver_field="session_sha256"))
    write_path_manifest(root, [(mpath, SERVICE_ID, RUN_ID), (mpath2, SERVICE_ID, RUN_ID_2)])
    for p in root.rglob("*"):
        if p.is_file() and p.name not in ("evidence_manifest.jsonl", "path_manifest.json"):
            set_mtime(p, now - 120)
    set_mtime(mpath, now - 60); set_mtime(mpath2, now - 60)

    # (b) bad_overwrite: manifest sealed, then S1/screenshot.png rewritten (later mtime, new bytes)
    root = FIXTURES / "bad_overwrite"
    mpath, states, steps = build(root)
    # R11 negatives: REACHED x non-null terminal_reason (impossible) and OTHER without note
    write_manifest(mpath, states, steps, flow_record(SERVICE_ID, RUN_ID, len(steps), endpoint_status="REACHED",
                                                     terminal_reason="OTHER", auth_gate_stage="NONE"))
    write_path_manifest(root, [(mpath, SERVICE_ID, RUN_ID)])
    for p in root.rglob("*"):
        if p.is_file() and p.name not in ("evidence_manifest.jsonl", "path_manifest.json"):
            set_mtime(p, now - 120)
    set_mtime(mpath, now - 60)
    victim = root / SERVICE_ID / TASK_ID / RUN_ID / "S1" / "screenshot.png"
    victim.write_bytes(PNG_HEADER + b"RE-COLLECTED-IN-PLACE" * 8)
    set_mtime(victim, now - 10)  # after manifest seal

    # (c) bad_lineage: display name as service_id, step 1 -> missing state S9, S2 screenshot missing
    root = FIXTURES / "bad_lineage"
    display_name = "Coupang Mobile App"
    mpath, states, steps = build(root, service_id=display_name)
    steps[1]["state_after_id"] = f"{display_name}.{TASK_ID}.{RUN_ID}.{ATTEMPT_ID}.S9"
    # R11/R13 negatives: EVIDENCE_DEFECT without terminal_reason; auth_gate_stage=NONE asserted without evidence;
    # R22 negative: flow record carries collector_sha but NO driver/session sha (driver_field=None) → MISSING_FIELD driver_sha256
    write_manifest(mpath, states, steps, flow_record(display_name, RUN_ID, len(steps), endpoint_status="EVIDENCE_DEFECT",
                                                     terminal_reason=None, auth_gate_stage="NONE", omit_terminal_reason=True,
                                                     driver_field=None))
    write_path_manifest(root, [(mpath, display_name, RUN_ID)])
    (root / display_name / TASK_ID / RUN_ID / "S2" / "screenshot.png").unlink()
    for p in root.rglob("*"):
        if p.is_file() and p.name not in ("evidence_manifest.jsonl", "path_manifest.json"):
            set_mtime(p, now - 120)
    set_mtime(mpath, now - 60)

    print(f"fixtures written under {FIXTURES}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
