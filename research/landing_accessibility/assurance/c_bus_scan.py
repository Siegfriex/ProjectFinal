#!/usr/bin/env python3
"""C bus scanner (JSON-parsing, not grep). Returns tickets addressed to C (to or cc) that lack a C ack.
Malformed JSON is reported explicitly as PARSE_ERROR — never silently counted as 'nothing to receive'.
Usage: c_bus_scan.py [bus_dir]  -> prints JSON {pending:[...], parse_errors:[...], scanned:n}
"""
import json, glob, os, sys
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
    return {"scanned": len(files), "pending": pending, "parse_errors": errors, "status": "PARSE_ERRORS_PRESENT" if errors else "OK"}
if __name__ == "__main__":
    print(json.dumps(scan(sys.argv[1] if len(sys.argv) > 1 else "/home/sieg/projects-wsl/ProjectFinal/.agent_bus/landing_v2"), ensure_ascii=False, indent=1))
