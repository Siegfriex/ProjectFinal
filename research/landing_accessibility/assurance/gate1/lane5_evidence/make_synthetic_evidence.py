#!/usr/bin/env python3
"""Generate three SYNTHETIC V3 evidence trees for GATE 1 (offline) checker validation.

  good/           1 service-task, 3 states (S0..S2), 2 steps, all hashes consistent, path manifest bound
  bad_overwrite/  same, but S1/screenshot.png rewritten AFTER the manifest was sealed
  bad_lineage/    step 1 references state S9 (absent), S2 screenshot missing,
                  service_id is a display name ("Coupang Mobile App") instead of an id

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
ATTEMPT_ID = "a1"
COLLECTOR_SHA = "c0ffee00" * 5          # 40 hex
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


def build(root: Path, *, service_id: str = SERVICE_ID, n_states: int = 3, base_time: datetime | None = None) -> tuple[Path, list[dict], list[dict]]:
    """Write states + steps + manifest. Returns (manifest_path, state_records, step_records)."""
    base_time = base_time or datetime(2026, 8, 28, 0, 0, 0, tzinfo=timezone.utc)
    run_dir = root / service_id / TASK_ID / RUN_ID
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
            "observation_id": f"{service_id}.{TASK_ID}.{RUN_ID}.{ATTEMPT_ID}.S{k}",
            "service_id": service_id,
            "task_id": TASK_ID,
            "run_id": RUN_ID,
            "attempt_id": ATTEMPT_ID,
            "state_index": f"S{k}",
            "url": URLS[k % len(URLS)],
            "captured_at": (base_time + timedelta(seconds=5 * k)).isoformat(),
            "collector_sha": COLLECTOR_SHA,
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
            "flow_observation_id": f"{service_id}.{TASK_ID}.{RUN_ID}.{ATTEMPT_ID}.flow",
            "service_id": service_id, "task_id": TASK_ID, "run_id": RUN_ID, "attempt_id": ATTEMPT_ID,
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
            "collector_sha": COLLECTOR_SHA, "protocol_sha": PROTOCOL_SHA,
            "task_contract_sha256": TASK_CONTRACT_SHA, "endpoint_contract_sha256": ENDPOINT_CONTRACT_SHA,
        })
    return run_dir / "evidence_manifest.jsonl", states, steps


def write_manifest(mpath: Path, states: list[dict], steps: list[dict]) -> None:
    with mpath.open("w", encoding="utf-8") as f:
        for r in states + steps:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


def write_path_manifest(root: Path, mpath: Path, service_id: str) -> None:
    pm = {
        "path_manifest_version": "C-v3-prereg",
        "frozen": True,
        "runs": [{
            "service_id": service_id, "task_id": TASK_ID, "run_id": RUN_ID,
            "evidence_manifest": str(mpath.relative_to(root)),
            "evidence_manifest_sha256": sha256_file(mpath),
        }],
    }
    (root / "path_manifest.json").write_text(json.dumps(pm, indent=2, ensure_ascii=False) + "\n")


def set_mtime(p: Path, when: float) -> None:
    os.utime(p, (when, when))


def main() -> int:
    if FIXTURES.exists():
        shutil.rmtree(FIXTURES)
    now = time.time()

    # (a) good
    root = FIXTURES / "good"
    mpath, states, steps = build(root)
    write_manifest(mpath, states, steps)
    write_path_manifest(root, mpath, SERVICE_ID)
    for p in root.rglob("*"):
        if p.is_file() and p.name not in ("evidence_manifest.jsonl", "path_manifest.json"):
            set_mtime(p, now - 120)
    set_mtime(mpath, now - 60)

    # (b) bad_overwrite: manifest sealed, then S1/screenshot.png rewritten (later mtime, new bytes)
    root = FIXTURES / "bad_overwrite"
    mpath, states, steps = build(root)
    write_manifest(mpath, states, steps)
    write_path_manifest(root, mpath, SERVICE_ID)
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
    write_manifest(mpath, states, steps)
    write_path_manifest(root, mpath, display_name)
    (root / display_name / TASK_ID / RUN_ID / "S2" / "screenshot.png").unlink()
    for p in root.rglob("*"):
        if p.is_file() and p.name not in ("evidence_manifest.jsonl", "path_manifest.json"):
            set_mtime(p, now - 120)
    set_mtime(mpath, now - 60)

    print(f"fixtures written under {FIXTURES}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
