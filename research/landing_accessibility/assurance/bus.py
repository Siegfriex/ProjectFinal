#!/usr/bin/env python3
"""Ticket bus helpers for Claude C (read tickets, write ACK/completions, heartbeat state).

Ticket files are never modified. ACK and results go to completions/ as separate files.
"""
from __future__ import annotations
import json, hashlib, sys, datetime, pathlib

BUS = pathlib.Path("/home/sieg/projects-wsl/ProjectFinal/.agent_bus/landing_v2")
TICKETS = BUS / "tickets"
COMPLETIONS = BUS / "completions"
ACKS = BUS / "acks"
EVENT_LOG = BUS / "event_log.jsonl"
HB_STATE = pathlib.Path("/tmp/claude-1000/-home-sieg-projects-wsl-ProjectFinal/9025a829-6001-41cc-967e-a7eebf607234/scratchpad/hb_state.json")
KST = datetime.timezone(datetime.timedelta(hours=9))

def now() -> str:
    return datetime.datetime.now(KST).strftime("%Y-%m-%dT%H:%M:%S+09:00")

def load_ticket(name: str) -> dict:
    p = TICKETS / name
    d = json.loads(p.read_text(encoding="utf-8"))
    d["_file"] = name
    return d

def is_for_c(t: dict) -> bool:
    to = t.get("to") or t.get("recipients") or []
    if isinstance(to, str):
        to = [to]
    return any(str(x).upper().strip() in ("C", "CLAUDE_C", "CLAUDE-C") for x in to)

def _log(event: str, **kw) -> None:
    try:
        with EVENT_LOG.open("a", encoding="utf-8") as f:
            f.write(json.dumps({"ts": now(), "actor": "C", "event": event, **kw}, ensure_ascii=False) + "\n")
    except Exception:
        pass

def _write(path: pathlib.Path, obj: dict) -> pathlib.Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(path)
    return path

def ack(ticket: dict, note: str = "") -> pathlib.Path:
    tid = ticket.get("ticket_id") or ticket.get("id") or pathlib.Path(ticket["_file"]).stem
    _tf = TICKETS / ticket["_file"].split("/")[-1] if not str(ticket["_file"]).startswith("acks/") and not str(ticket["_file"]).startswith("completions/") else BUS / ticket["_file"]
    _sha = hashlib.sha256(_tf.read_bytes()).hexdigest() if _tf.exists() else None
    obj = {"kind": "ACK", "from": "C", "ticket_id": tid, "ticket_file": ticket["_file"], "ticket_sha256": _sha,
           "ticket_type": ticket.get("type") or ticket.get("kind"), "acked_at": now(), "note": note}
    _ap = ACKS / f"{tid}.C.json"; _seq = 0
    while _ap.exists():
        _seq += 1; _ap = ACKS / f"{tid}.C-{_seq}.json"  # immutable: re-ACK creates a new file, never overwrites
    p = _write(_ap, obj); _log("ACK", ticket_id=tid); return p

def complete(ticket: dict, result_type: str, payload: dict, to=("A", "B")) -> pathlib.Path:
    tid = ticket.get("ticket_id") or ticket.get("id") or pathlib.Path(ticket["_file"]).stem
    obj = {"kind": "COMPLETION", "from": "C", "to": list(to), "ticket_id": tid, "ticket_file": ticket["_file"],
           "result_type": result_type, "completed_at": now(), **payload}
    p = _write(COMPLETIONS / f"{tid}.C.json", obj); _log("COMPLETION", ticket_id=tid, result_type=result_type, severity_max=payload.get("severity_max")); return p

def emit(kind: str, payload: dict, to=("A", "B")) -> pathlib.Path:
    """Unsolicited C→A/B ticket (e.g. SYSTEMIC_HARD_STOP_CANDIDATE)."""
    TICKETS.mkdir(parents=True, exist_ok=True)
    stamp = datetime.datetime.now(KST).strftime("%H%M%S")
    # ticket files are immutable: never overwrite — add a sequence suffix on same-second collisions
    seq = 0
    while True:
        tid = f"C-{kind}-{stamp}" + (f"-{seq}" if seq else "")
        path = TICKETS / f"{tid}.json"
        if not path.exists():
            break
        seq += 1
    # SSOTV3 15_TICKET_PROTOCOL_SCHEMA — required: ticket_id/from/to[]/type/priority/claim_kind/base_sha/scope/status/created_at_kst
    v3_type = {"FINDING": "FINDING", "BLOCKER": "BLOCKER", "FACT_CORRECTION": "FACT_CORRECTION", "COMPLETION": "COMPLETION",
               "ASSURANCE": "ASSURANCE", "DECISION_REQUEST": "DECISION_REQUEST", "HARD_STOP_CANDIDATE": "BLOCKER"}.get(kind, kind)
    obj = {"ticket_id": tid, "type": v3_type, "from": "C", "to": list(to), "created_at": now(), "created_at_kst": now(),
           "priority": payload.get("priority", "P2"), "claim_kind": payload.get("claim_kind", "ASSURANCE"),
           "scope": payload.get("scope", "UNSCOPED"), "status": payload.get("status", "OPEN"),
           "task_family_id": payload.get("task_family_id"), "target_manifest_sha256": payload.get("target_manifest_sha256"),
           "ssot": "SSOTV3", **payload}
    if kind != v3_type:
        obj["legacy_type"] = kind
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")
    import os
    os.link(tmp, path)  # fails if path appeared meanwhile — exclusive create
    tmp.unlink()
    _log("TICKET_EMIT", ticket_id=tid, type=kind); return path

def hb(**fields) -> None:
    st = json.loads(HB_STATE.read_text(encoding="utf-8")) if HB_STATE.exists() else {"agent": "C"}
    st.update(fields)
    HB_STATE.write_text(json.dumps(st, ensure_ascii=False, indent=2), encoding="utf-8")

if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd == "ack":
        t = load_ticket(sys.argv[2]); print(ack(t, " ".join(sys.argv[3:])))
    elif cmd == "hb":
        hb(**json.loads(sys.argv[2])); print("hb updated")
    elif cmd == "list":
        for p in sorted(TICKETS.glob("*.json")):
            t = load_ticket(p.name); print(p.name, "FOR_C" if is_for_c(t) else "-", t.get("type") or t.get("kind"))
