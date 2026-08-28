#!/usr/bin/env python3
"""Ticket bus helpers for Claude C (read tickets, write ACK/completions, heartbeat state).

Ticket files are never modified. ACK and results go to completions/ as separate files.

emit() refuses to write a schema-invalid ticket: SSOTV3 15_TICKET_PROTOCOL_SCHEMA requires base_sha (Δ5) and delta Δ26
requires it to be a REAL object: the written value is always a 40-char lowercase hex commit id that resolves via
`git -C <repo> cat-file -e <sha>^{commit}`; a short hex input is expanded with `git rev-parse --verify <sha>^{commit}` before
writing (never zero-padded — the T-B-V3-FINDING-007-SHANOTE case), and a missing / non-hex / non-resolving value raises
ValueError BEFORE any file is created. Selftest that shows the refusals without touching the real bus:
    python3 bus.py selftest      # temp dir; expects ValueError for missing, short-fake, 40-hex-fake; short real sha expands; full real sha passes
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

def ack(ticket: dict, note: str = "", retracted_labels_cited=None) -> pathlib.Path:
    tid = ticket.get("ticket_id") or ticket.get("id") or pathlib.Path(ticket["_file"]).stem
    _tf = TICKETS / ticket["_file"].split("/")[-1] if not str(ticket["_file"]).startswith("acks/") and not str(ticket["_file"]).startswith("completions/") else BUS / ticket["_file"]
    _sha = hashlib.sha256(_tf.read_bytes()).hexdigest() if _tf.exists() else None
    obj = {"kind": "ACK", "from": "C", "ticket_id": tid, "ticket_file": ticket["_file"], "ticket_sha256": _sha,
           "ticket_type": ticket.get("type") or ticket.get("kind"), "acked_at": now(), "note": note}
    if retracted_labels_cited: obj["retracted_labels_cited"] = retracted_labels_cited
    obj = enforce_retraction_citation(obj, "ack")   # R137: refuse before writing

    _ap = ACKS / f"{tid}.C.json"; _seq = 0
    while _ap.exists():
        _seq += 1; _ap = ACKS / f"{tid}.C-{_seq}.json"  # immutable: re-ACK creates a new file, never overwrites
    p = _write(_ap, obj); _log("ACK", ticket_id=tid); return p

def complete(ticket: dict, result_type: str, payload: dict, to=("A", "B")) -> pathlib.Path:
    tid = ticket.get("ticket_id") or ticket.get("id") or pathlib.Path(ticket["_file"]).stem
    obj = {"kind": "COMPLETION", "from": "C", "to": list(to), "ticket_id": tid, "ticket_file": ticket["_file"],
           "result_type": result_type, "completed_at": now(), **payload}
    p = _write(COMPLETIONS / f"{tid}.C.json", obj); _log("COMPLETION", ticket_id=tid, result_type=result_type, severity_max=payload.get("severity_max")); return p

BASE_SHA_RE = __import__("re").compile(r"^[0-9a-f]{7,40}$")
REPO = pathlib.Path("/home/sieg/projects-wsl/ProjectFinal")     # object store shared by every worktree

def resolve_base_sha(bs, repo: pathlib.Path = REPO) -> str:
    """Δ26 guard: return the 40-char lowercase commit id for `bs`, or raise ValueError. Short hex is expanded via
    git rev-parse --verify (no zero padding); a 40-hex value must exist (git cat-file -e)."""
    import subprocess
    if not (isinstance(bs, str) and BASE_SHA_RE.match(bs.strip().lower())):
        raise ValueError(f"emit refused: base_sha is mandatory (15 schema / Δ5) and must be a 7-40 hex git sha; got {bs!r}")
    bs = bs.strip().lower()
    if len(bs) == 40:
        if subprocess.run(["git", "-C", str(repo), "cat-file", "-e", f"{bs}^{{commit}}"], capture_output=True).returncode != 0:
            raise ValueError(f"emit refused: base_sha {bs} does not resolve to a commit (Δ26: base_sha must be a real object)")
        return bs
    r = subprocess.run(["git", "-C", str(repo), "rev-parse", "--verify", "--quiet", f"{bs}^{{commit}}"], capture_output=True, text=True)
    full = r.stdout.strip()
    if r.returncode != 0 or not BASE_SHA_RE.match(full) or len(full) != 40:
        raise ValueError(f"emit refused: short base_sha {bs} does not resolve to a unique commit (Δ26; never zero-pad an abbreviation)")
    return full

RETRACTIONS_MD = pathlib.Path("/home/sieg/projects-wsl/ProjectFinal/artifacts/v3_census/mart/CANONICAL_MART_50.RETRACTIONS.md")


def retracted_tokens(path: pathlib.Path = None) -> dict:
    """{token: replacement_label} from the b_retractions/v1 block; {} if the file/block is absent (state reported by the caller)."""
    import re as _re
    path = path or RETRACTIONS_MD
    if not path.exists(): return {}
    m = _re.search(r"```json\s*(\{.*?\})\s*```", path.read_text(encoding="utf-8"), _re.S)
    if not m: return {}
    try: b = json.loads(m.group(1))
    except ValueError: return {}
    return {x["token"]: x.get("replacement_label") for x in b.get("retracted", []) if x.get("token")}


def enforce_retraction_citation(obj: dict, kind: str) -> dict:
    """R137 / C-PEND-03: a retracted token in the body (use OR mention) requires an explicit `retracted_labels_cited` declaration.
    Refuses (ValueError) instead of publishing; never edits the body silently."""
    toks = retracted_tokens()
    if not toks:
        obj["retraction_block"] = "ABSENT"; return obj
    body = json.dumps({k: v for k, v in obj.items() if k != "retracted_labels_cited"}, ensure_ascii=False)
    hit = sorted(t for t in toks if t in body)
    if hit and not obj.get("retracted_labels_cited"):
        raise ValueError(f"{kind} refused (R137): body cites retracted token(s) {hit} without `retracted_labels_cited` — declare e.g. "
                         + json.dumps({"retracted_labels_cited": [{"token": t, "replacement_label": toks[t], "marker": "[RETRACTED]", "use_or_mention": "mention"} for t in hit]}, ensure_ascii=False))
    if hit: obj["retraction_marker"] = "[RETRACTED] " + ", ".join(f"{t} → {toks[t]}" for t in hit)
    return obj


def emit(kind: str, payload: dict, to=("A", "B")) -> pathlib.Path:
    """Unsolicited C→A/B ticket (e.g. SYSTEMIC_HARD_STOP_CANDIDATE). Raises ValueError if payload lacks a base_sha that
    resolves to a real commit (Δ5 + Δ26); a short sha is expanded to 40 chars before writing (base_sha_as_given kept)."""
    given = payload.get("base_sha")
    full = resolve_base_sha(given)
    payload = {**payload, "base_sha": full}
    if isinstance(given, str) and given.strip().lower() != full:
        payload["base_sha_as_given"] = given
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
           "ssot": "SSOTV3",
           # Δ60-R65: intent declaration at issue time — a self-report, never cited as evidence; the verifiable form is the
           # structural check (ACK from a non-issuing plane, gate1/c_self_approval_structural_c.py)
           "self_approved": False,
           "self_approved_note": "자기신고(발행 시점 의도 선언). 증거로 인용하지 않는다 — 보증은 발행 평면 외 ACK ≥ 1 구조 검사(Δ60-R65)",
           **payload}
    if kind != v3_type:
        obj["legacy_type"] = kind
    obj = enforce_retraction_citation(obj, "emit")   # refuses BEFORE any file is created
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
    try:
        cmd = sys.argv[1]
        if cmd == "ack":
            args = sys.argv[3:]; decl = None
            if args and args[0].startswith("--cite="): decl = json.loads(args[0][7:]); args = args[1:]
            t = load_ticket(sys.argv[2]); print(ack(t, " ".join(args), retracted_labels_cited=decl))
        elif cmd == "hb":
            hb(**json.loads(sys.argv[2])); print("hb updated")
        elif cmd == "list":
            for p in sorted(TICKETS.glob("*.json")):
                t = load_ticket(p.name); print(p.name, "FOR_C" if is_for_c(t) else "-", t.get("type") or t.get("kind"))
        elif cmd == "selftest":
            # base_sha refusal, demonstrated against a temp dir — the real bus is never written
            import tempfile
            with tempfile.TemporaryDirectory(prefix="bus_selftest_") as td:
                TICKETS = pathlib.Path(td) / "tickets"; EVENT_LOG = pathlib.Path(td) / "event_log.jsonl"
                try:
                    emit("FINDING", {"headline": "no base_sha"}); print("FAIL: emit wrote a ticket without base_sha"); sys.exit(1)
                except ValueError as e:
                    print("refused as expected:", e)
                assert not list(TICKETS.glob("*.json")) if TICKETS.exists() else True, "a file was created despite refusal"
                import subprocess
                head = subprocess.run(["git", "-C", str(REPO), "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
                for bad, why in (("0123abcd", "short sha that resolves to nothing"), ("deadbeef" * 5, "40-hex fake sha"), ("zz1234567", "non-hex")):
                    try:
                        emit("FINDING", {"headline": "bad", "base_sha": bad}); print(f"FAIL: emit accepted {why} {bad}"); sys.exit(1)
                    except ValueError as e:
                        print("refused as expected:", str(e)[:90])
                assert not list(TICKETS.glob("*.json")) if TICKETS.exists() else True, "a file was created despite refusal"
                p = emit("FINDING", {"headline": "ok short", "base_sha": head[:10]}); d = json.loads(p.read_text(encoding="utf-8"))
                assert d["base_sha"] == head and d.get("base_sha_as_given") == head[:10] and p.parent == TICKETS, "short real sha was not expanded to 40 chars"
                p2 = emit("FINDING", {"headline": "ok full", "base_sha": head}); d2 = json.loads(p2.read_text(encoding="utf-8"))
                assert d2["base_sha"] == head and "base_sha_as_given" not in d2, "full sha changed"
                # R137 pre-publish refusal: retracted token in body without declaration → refused, no file; with declaration → written + marker
                import bus as _self
                _rt = retracted_tokens()
                if _rt:
                    _tok = next(iter(_rt)); _n0 = len(list(TICKETS.glob("*.json")))
                    try:
                        emit("FINDING", {"headline": f"mentions {_tok} as a bad name", "base_sha": head}); print("FAIL: emit accepted a retracted token without declaration"); sys.exit(1)
                    except ValueError as e: print("refused as expected (R137):", str(e)[:80])
                    assert len(list(TICKETS.glob("*.json"))) == _n0, "a file was created despite R137 refusal"
                    p3 = emit("FINDING", {"headline": f"mentions {_tok}", "base_sha": head, "retracted_labels_cited": [{"token": _tok, "use_or_mention": "mention"}]}); d3 = json.loads(p3.read_text(encoding="utf-8"))
                    assert d3.get("retraction_marker", "").startswith("[RETRACTED]"), "marker missing on declared citation"
                else: print("NOTE: retraction block absent — R137 control not exercised (reported, not passed)")
                assert d2.get("self_approved") is False and "self_approved_note" in d2, "Δ60-R65 fields missing from emitted ticket"
                print("valid emits wrote", p.name, p2.name, "in temp dir only (short sha expanded to", head[:12] + "…); selftest OK")
    except AssertionError as _e:  # selftest assertion = the control ran and FAILED
        print(f"FAIL: {_e}", file=sys.stderr); sys.exit(1)
    except Exception:  # Δ46-exit2 / Δ50-exit2-common: crash / missing ticket / missing argv = did not run
        import traceback
        traceback.print_exc()
        print("bus: did not run — read neither as pass nor fail (exit 2)", file=sys.stderr); sys.exit(2)
