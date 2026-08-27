#!/usr/bin/env python3
"""C bus scanner (JSON-parsing, not grep). Returns tickets addressed to C (to or cc) that lack a C ack.
Malformed JSON is reported explicitly as PARSE_ERROR — never silently counted as 'nothing to receive'.
Usage: c_bus_scan.py [bus_dir]  -> prints JSON {pending:[...], parse_errors:[...], scanned:n}
"""
import json, glob, os, sys
V3_CUTOFF_EPOCH = 1787500320  # 2026-08-28T02:12:00+09:00 (T-A-V3-P0-001 adoption)
def scan(bus_dir: str, plane: str = "C") -> dict:
    tdir = os.path.join(bus_dir, "tickets"); adir = os.path.join(bus_dir, "acks")
    acked = {os.path.basename(p)[: -len(f".{plane}.json")] for p in glob.glob(os.path.join(adir, f"*.{plane}.json"))}
    files = sorted(glob.glob(os.path.join(tdir, "*.json")))
    pending, errors = [], []
    for p in files:
        tid = os.path.basename(p)[:-5]
        try:
            d = json.load(open(p, encoding="utf-8"))
        except Exception as e:
            errors.append({"file": os.path.basename(p), "error": f"{type(e).__name__}: {e}"[:120]}); continue
        to = d.get("to"); to = [to] if isinstance(to, str) else (to or [])
        cc = d.get("cc"); cc = [cc] if isinstance(cc, str) else (cc or [])
        if (plane in to or plane in cc) and d.get("from") != plane and tid not in acked:
            pending.append({"ticket_id": tid, "from": d.get("from"), "type": d.get("type"), "priority": d.get("priority"), "via": "to" if plane in to else "cc"})
    # T-A-V3-STEP1-008 forward rule: no ACK/completion without a ticket file (v3-era only, checked by mtime >= cutoff)
    import time
    ticket_ids = {os.path.basename(f)[:-5] for f in files}
    dangling = []
    for sub in ("acks", "completions"):
        for p2 in glob.glob(os.path.join(bus_dir, sub, "*.json")):
            base = os.path.basename(p2)[:-5]
            tid = base.rsplit(".", 1)[0] if sub == "acks" else base.rsplit(".", 1)[0]
            if tid not in ticket_ids and os.path.getmtime(p2) >= V3_CUTOFF_EPOCH:
                dangling.append({"file": f"{sub}/{os.path.basename(p2)}", "missing_ticket": tid})
    return {"scanned": len(files), "pending": pending, "parse_errors": errors, "dangling_refs_v3_era": dangling, "status": "PARSE_ERRORS_PRESENT" if errors else "OK"}
if __name__ == "__main__":
    print(json.dumps(scan(sys.argv[1] if len(sys.argv) > 1 else "/home/sieg/projects-wsl/ProjectFinal/.agent_bus/landing_v2"), ensure_ascii=False, indent=1))
