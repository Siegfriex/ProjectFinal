#!/usr/bin/env python3
"""c_self_approval_structural_c.py — R65 (Δ60-R65 · T-A-V3-STEP1-044) structural self-approval check, C plane.

`self_approved:false` is a producer's statement about itself and is never cited as evidence (Δ56-provenance). The verifiable
form is STRUCTURAL: does the ticket carry at least one ACK from a plane OTHER than the issuing plane? That is computed from
the bus, here, for EVERY ticket of EVERY plane (C's own tickets are the headline; A/B/D/E are an independent recount of
their own claims — A said T-A-V3-* 61/61 in STEP1-044).

Method (stated so the count can be read — R54):
  * issuing plane      = ticket JSON `from` (a ticket whose `from` is unreadable/absent is listed as TICKET_PLANE_UNKNOWN and
                         counted as an exception — fail closed)
  * ACK plane          = ACK JSON `from`, else `ack_by` — NEVER the file name (file names carry `.A.B`, `.C-1`, `.A2` forms)
  * ACK → ticket       = ACK JSON `ticket_id` exact match against the ticket's `ticket_id`
  * ACK_UNREADABLE     = ACK file that fails to parse, or has no plane / no ticket_id → does NOT count as approval, listed
  * other-plane ACK    = ACK plane != issuing plane
  * `self_approved` field presence is REPORTED per plane (observation only) and never enters the verdict.
Controls run first on a synthetic bus in a temp dir; the real bus is never written. If any control fails the main
measurement is refused (exit 2 = did not run). Exceptions are a measurement, not a verdict; the exit code does not encode them.

usage: c_self_approval_structural_c.py [--bus DIR] [--out FILE] [--no-write]
exit 0 = ran (controls PASS) · 2 = did not run (control failure / crash / bus missing)
"""
import argparse, datetime, glob, hashlib, json, os, pathlib, sys, tempfile

HERE = pathlib.Path(__file__).resolve()
DEFAULT_BUS = "/home/sieg/projects-wsl/ProjectFinal/.agent_bus/landing_v2"
DEFAULT_OUT = HERE.parent / "SELF_APPROVAL_STRUCTURAL_C.json"
KST = datetime.timezone(datetime.timedelta(hours=9))
PLANES = ("A", "B", "C", "D", "E")
METHOD = {
    "issuing_plane": "ticket JSON `from`; absent/unreadable → TICKET_PLANE_UNKNOWN, counted as exception (fail closed)",
    "ack_plane": "ACK JSON `from`, else `ack_by`; NEVER the file name",
    "ack_to_ticket": "ACK JSON `ticket_id` == ticket `ticket_id` (exact)",
    "ack_unreadable": "unparsable ACK, or ACK without plane / ticket_id → not an approval, listed",
    "structural_ok": "exists ACK with plane != issuing plane",
    "self_approved_field": "presence per plane is reported as an observation only and never enters the verdict (Δ60-R65)",
}


def now_kst():
    return datetime.datetime.now(KST).isoformat(timespec="seconds")


def _read_json(p):
    try:
        with open(p, encoding="utf-8") as f:
            return json.load(f), None
    except Exception as e:  # noqa: BLE001 — every failure mode is the same state: unreadable
        return None, f"{type(e).__name__}: {str(e)[:80]}"


def measure(bus: str) -> dict:
    tdir, adir = os.path.join(bus, "tickets"), os.path.join(bus, "acks")
    if not os.path.isdir(tdir) or not os.path.isdir(adir):
        raise FileNotFoundError(f"bus missing tickets/ or acks/ under {bus}")
    tickets, tickets_unreadable = {}, []
    for p in sorted(glob.glob(os.path.join(tdir, "*.json"))):
        d, err = _read_json(p)
        if d is None:
            tickets_unreadable.append({"file": os.path.basename(p), "error": err}); continue
        tid = d.get("ticket_id") or os.path.basename(p)[:-5]
        tickets[tid] = {"file": os.path.basename(p), "from": d.get("from") if isinstance(d.get("from"), str) else None,
                        "created_at_kst": d.get("created_at_kst") or d.get("created_at"), "type": d.get("type"),
                        "self_approved_field_present": "self_approved" in d, "self_approved_value": d.get("self_approved")}
    acks_by_ticket, ack_unreadable, acks_dangling, n_acks = {}, [], [], 0
    for p in sorted(glob.glob(os.path.join(adir, "*"))):
        if os.path.isdir(p):
            continue
        n_acks += 1
        d, err = _read_json(p)
        plane = None
        if isinstance(d, dict):
            plane = d.get("from") if isinstance(d.get("from"), str) else (d.get("ack_by") if isinstance(d.get("ack_by"), str) else None)
        atid = d.get("ticket_id") if isinstance(d, dict) else None
        if d is None or not plane or not isinstance(atid, str):
            ack_unreadable.append({"file": os.path.basename(p), "reason": err or ("no plane field" if not plane else "no ticket_id")}); continue
        if atid not in tickets:
            acks_dangling.append({"file": os.path.basename(p), "ticket_id": atid}); continue
        acks_by_ticket.setdefault(atid, []).append({"plane": plane, "file": os.path.basename(p)})
    per_plane = {}
    for tid, t in tickets.items():
        plane = t["from"] if t["from"] in PLANES else "TICKET_PLANE_UNKNOWN"
        row = per_plane.setdefault(plane, {"tickets_n": 0, "with_other_plane_ack_n": 0, "exceptions": [], "self_approved_field_present_n": 0,
                                          "self_approved_false_n": 0, "ack_planes_seen": {}})
        row["tickets_n"] += 1
        row["self_approved_field_present_n"] += int(t["self_approved_field_present"])
        row["self_approved_false_n"] += int(t["self_approved_value"] is False)
        others = sorted({a["plane"] for a in acks_by_ticket.get(tid, []) if a["plane"] != t["from"]})
        for a in acks_by_ticket.get(tid, []):
            row["ack_planes_seen"][a["plane"]] = row["ack_planes_seen"].get(a["plane"], 0) + 1
        if others and plane != "TICKET_PLANE_UNKNOWN":
            row["with_other_plane_ack_n"] += 1
        else:
            same = sorted({a["plane"] for a in acks_by_ticket.get(tid, []) if a["plane"] == t["from"]})
            row["exceptions"].append({"ticket_id": tid, "type": t["type"], "created_at_kst": t["created_at_kst"],
                                      "state": ("TICKET_PLANE_UNKNOWN" if plane == "TICKET_PLANE_UNKNOWN" else "SELF_ACK_ONLY" if same else "NO_ACK"),
                                      "self_acks": same})
    for row in per_plane.values():
        row["exceptions_n"] = len(row["exceptions"])
    a_v3 = {tid: t for tid, t in tickets.items() if t["from"] == "A" and tid.startswith("T-A-V3-")}
    a_v3_ok = sum(1 for tid in a_v3 if any(a["plane"] != "A" for a in acks_by_ticket.get(tid, [])))
    return {"tickets_n": len(tickets), "tickets_unreadable": tickets_unreadable, "acks_n": n_acks, "acks_unreadable": ack_unreadable,
            "acks_dangling_n": len(acks_dangling), "acks_dangling": acks_dangling[:50], "per_plane": dict(sorted(per_plane.items())),
            "a_claim_recount": {"claim": "T-A-V3-STEP1-044: A 의 T-A-V3-* 61건 전부 타 평면 ACK", "T-A-V3_tickets_n": len(a_v3),
                                "with_other_plane_ack_n": a_v3_ok, "exceptions": sorted(tid for tid in a_v3 if not any(a["plane"] != "A" for a in acks_by_ticket.get(tid, [])))}}


def _w(d, name, obj):
    with open(os.path.join(d, name), "w", encoding="utf-8") as f:
        f.write(obj if isinstance(obj, str) else json.dumps(obj, ensure_ascii=False))


def controls() -> dict:
    """Synthetic bus. Every must_flag case must land in exceptions; every must_not_flag case must not. Returns {name: PASS/FAIL}."""
    res = {}
    with tempfile.TemporaryDirectory(prefix="c_self_approval_ctl_") as td:
        t, a = os.path.join(td, "tickets"), os.path.join(td, "acks")
        os.makedirs(t); os.makedirs(a)
        _w(t, "C-NOACK.json", {"ticket_id": "C-NOACK", "from": "C"})
        _w(t, "C-SELFONLY.json", {"ticket_id": "C-SELFONLY", "from": "C"}); _w(a, "C-SELFONLY.C.json", {"from": "C", "ticket_id": "C-SELFONLY"})
        _w(t, "C-UNREADONLY.json", {"ticket_id": "C-UNREADONLY", "from": "C"}); _w(a, "C-UNREADONLY.A.json", "{not json")
        _w(t, "C-NOPLANE.json", {"ticket_id": "C-NOPLANE", "from": "C"}); _w(a, "C-NOPLANE.A.json", {"ticket_id": "C-NOPLANE"})
        _w(t, "C-WRONGID.json", {"ticket_id": "C-WRONGID", "from": "C"}); _w(a, "C-WRONGID.A.json", {"from": "A", "ticket_id": "C-OTHER"})
        _w(t, "C-FILENAMELIE.json", {"ticket_id": "C-FILENAMELIE", "from": "C"}); _w(a, "C-FILENAMELIE.A.json", {"from": "C", "ticket_id": "C-FILENAMELIE"})
        _w(t, "X-NOFROM.json", {"ticket_id": "X-NOFROM"}); _w(a, "X-NOFROM.A.json", {"from": "A", "ticket_id": "X-NOFROM"})
        _w(t, "C-OK.json", {"ticket_id": "C-OK", "from": "C"}); _w(a, "C-OK.A.json", {"from": "A", "ticket_id": "C-OK"})
        _w(t, "C-REACK.json", {"ticket_id": "C-REACK", "from": "C"}); _w(a, "C-REACK.B-1.json", {"from": "B", "ticket_id": "C-REACK"})
        _w(t, "C-ACKBY.json", {"ticket_id": "C-ACKBY", "from": "C"}); _w(a, "C-ACKBY.D.json", {"ack_by": "D", "ticket_id": "C-ACKBY"})
        _w(t, "C-MIXED.json", {"ticket_id": "C-MIXED", "from": "C"}); _w(a, "C-MIXED.C.json", {"from": "C", "ticket_id": "C-MIXED"}); _w(a, "C-MIXED.A.json", {"from": "A", "ticket_id": "C-MIXED"})
        _w(t, "C-FILENAMEOK.json", {"ticket_id": "C-FILENAMEOK", "from": "C"}); _w(a, "C-FILENAMEOK.C.json", {"from": "A", "ticket_id": "C-FILENAMEOK"})
        m = measure(td)
        c_exc = {e["ticket_id"]: e["state"] for e in m["per_plane"].get("C", {}).get("exceptions", [])}
        u_exc = {e["ticket_id"]: e["state"] for e in m["per_plane"].get("TICKET_PLANE_UNKNOWN", {}).get("exceptions", [])}
        must_flag = {"C-NOACK": "NO_ACK", "C-SELFONLY": "SELF_ACK_ONLY", "C-UNREADONLY": "NO_ACK", "C-NOPLANE": "NO_ACK", "C-WRONGID": "NO_ACK",
                     "C-FILENAMELIE": "SELF_ACK_ONLY"}
        for tid, st in must_flag.items():
            res[f"must_flag:{tid}"] = "PASS" if c_exc.get(tid) == st else f"FAIL (got {c_exc.get(tid)})"
        res["must_flag:X-NOFROM"] = "PASS" if u_exc.get("X-NOFROM") == "TICKET_PLANE_UNKNOWN" else f"FAIL (got {u_exc.get('X-NOFROM')})"
        for tid in ("C-OK", "C-REACK", "C-ACKBY", "C-MIXED", "C-FILENAMEOK"):
            res[f"must_not_flag:{tid}"] = "PASS" if tid not in c_exc else f"FAIL (flagged {c_exc[tid]})"
        res["count:C.with_other_plane_ack_n==5"] = "PASS" if m["per_plane"]["C"]["with_other_plane_ack_n"] == 5 else f"FAIL ({m['per_plane']['C']['with_other_plane_ack_n']})"
        res["count:acks_unreadable==2"] = "PASS" if len(m["acks_unreadable"]) == 2 else f"FAIL ({len(m['acks_unreadable'])})"
        res["count:acks_dangling==1"] = "PASS" if m["acks_dangling_n"] == 1 else f"FAIL ({m['acks_dangling_n']})"
        # mutation control (R31/R43): the check must be able to fail — delete the only other-plane ACK of C-OK and expect a flag
        os.remove(os.path.join(a, "C-OK.A.json"))
        m2 = measure(td)
        res["mutation:remove_ack→flag"] = "PASS" if any(e["ticket_id"] == "C-OK" for e in m2["per_plane"]["C"]["exceptions"]) else "FAIL"
    return res


def main(argv) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--bus", default=DEFAULT_BUS); ap.add_argument("--out", default=str(DEFAULT_OUT)); ap.add_argument("--no-write", action="store_true")
    a = ap.parse_args(argv)
    ctl = controls()
    failed = {k: v for k, v in ctl.items() if v != "PASS"}
    if failed:
        print("CONTROLS FAILED — main measurement refused (exit 2):", json.dumps(failed, ensure_ascii=False), file=sys.stderr); return 2
    m = measure(a.bus)
    out = {"schema": "C_SELF_APPROVAL_STRUCTURAL", "ruling": "Δ60-R65 (T-A-V3-STEP1-044)", "measured_at_kst": now_kst(), "bus": a.bus,
           "tool_sha256": hashlib.sha256(HERE.read_bytes()).hexdigest(), "method": METHOD,
           "controls": {"n": len(ctl), "all_pass": True, "cases": ctl}, "result": m,
           "reading": {p: f"{r['with_other_plane_ack_n']}/{r['tickets_n']} 타 평면 ACK 보유 · 예외 {r['exceptions_n']}" for p, r in m["per_plane"].items()},
           "not_a_verdict": "measurement; exceptions are listed, not judged (a just-issued ticket legitimately has no ACK yet — read created_at_kst)"}
    if not a.no_write:
        pathlib.Path(a.out).write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print("CONTROLS", len(ctl), "PASS"); print(json.dumps(out["reading"], ensure_ascii=False, indent=1))
    print("A claim recount:", json.dumps(m["a_claim_recount"], ensure_ascii=False))
    for p, r in m["per_plane"].items():
        for e in r["exceptions"]:
            print(f"  EXC {p} {e['ticket_id']} {e['state']} {e['created_at_kst']}")
    print("acks_unreadable", len(m["acks_unreadable"]), "acks_dangling", m["acks_dangling_n"], "tickets_unreadable", len(m["tickets_unreadable"]))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main(sys.argv[1:]))
    except SystemExit:
        raise
    except Exception:  # Δ46-exit2: crash = did not run
        import traceback; traceback.print_exc()
        print("c_self_approval_structural_c: did not run (exit 2)", file=sys.stderr); sys.exit(2)
