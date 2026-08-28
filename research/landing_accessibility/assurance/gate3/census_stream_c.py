#!/usr/bin/env python3
"""census_stream_c.py — streaming QC bound to T-A-V3-TBX-010 paths and the T-A-V3-TBX-006 23-column canonical mart.

Root  /home/sieg/projects-wsl/ProjectFinal/artifacts/v3_census/   (fixed by A; never another path)
  raw/DISPATCH_LEDGER.jsonl        target_id, family_id, service, dispatched_at, worker_id, idempotency_key   (append-only)
  raw/EVIDENCE_MANIFEST.jsonl      target_id, evidence_hash, prev_hash, terminal_reason, attempt_status, captured_at (hash chain)
  raw/<target_id>/                 DOM/AX/CSS/geometry/action sequence
  mart/INGEST_LEDGER.jsonl · mart/snapshot_<NN>.csv · mart/CANONICAL_MART_50.csv · mart/CANONICAL_MART_50.sha256.json
Runs census_qc_c.qc() on the newest mart file with the BOUND adapter (below), then the structure checks that the 7 items imply
on the raw side: dispatch exactly-once (idempotency_key / target_id unique), evidence chain (prev_hash links; a line seen in an
earlier run that changed = evidence_overwrite), canonical-50 file hash vs its .sha256.json, blank-cell convention
(UNDETERMINED/NOT_OBSERVED + missing_reason, TBX-006), forbidden-action presence probe over raw/<target_id>/ files (rule stated).
Writes artifacts/v3_census/assurance/MAIN50_EVIDENCE_ASSURED.json (history[] appended, never overwritten in place) + a copy under
gate3/out/, and the heartbeat numbers (checker_frozen_sha, checks pass/fail, flags).
exit 0 ran · 2 did not run (controls / crash) · 3 NO_EVIDENCE_INPUT (no mart rows AND no raw lines)
"""
import csv, datetime, glob, hashlib, json, os, pathlib, re, subprocess, sys
HERE = pathlib.Path(__file__).resolve(); sys.path.insert(0, str(HERE.parent)); sys.path.insert(0, str(HERE.parents[1]))
import census_qc_c as Q  # noqa: E402

ROOT = pathlib.Path("/home/sieg/projects-wsl/ProjectFinal/artifacts/v3_census")
OUT_A = ROOT / "assurance" / "MAIN50_EVIDENCE_ASSURED.json"; OUT_C = HERE.parent / "out" / "MAIN50_EVIDENCE_ASSURED_C.json"
STATE = HERE.parent / "out" / "chain_state.json"
COLS23 = ["target_id", "family_id", "service", "attempt_status", "terminal_reason", "visible_label", "accessible_name", "label_relation", "entry_x_norm",
          "entry_y_norm", "entry_zone", "entry_control_type", "nav_container_type", "reveal_direction", "menu_dependency", "task_flow_sequence",
          "experienced_flow_sequence", "activation_depth", "auth_gate_stage", "task_control_occlusion", "collector_plane", "evidence_hash", "missing_reason"]
# BOUND adapter (TBX-010): endpoint_status has no column — 'completed' is read from attempt_status (values reported; rule below)
ADAPTER = {"target_id": {"field": "target_id", "status": "WIRED_TBX010"}, "family_id": {"field": "family_id", "status": "WIRED_TBX010"},
           "service_name": {"field": "service", "status": "WIRED_TBX010"}, "service_id": {"field": "service", "status": "WIRED_TBX010"},
           "task_id": {"field": "family_id", "status": "WIRED_TBX010(task = family frozen task)"}, "run_id": {"field": "evidence_hash", "status": "WIRED_TBX010(identity = evidence_hash)"},
           "endpoint_status": {"field": "attempt_status", "status": "WIRED_TBX010(completed iff attempt_status ∈ COMPLETED_VALUES)"},
           "terminal_reason": {"field": "terminal_reason", "status": "WIRED_TBX010"}, "evidence_pointer": {"field": "evidence_hash", "status": "WIRED_TBX010"},
           "evidence_sha256": {"field": "evidence_hash", "status": "WIRED_TBX010"}, "evidence_adequacy": {"field": None, "status": "UNBOUND(no column; adequacy = evidence_hash present in EVIDENCE_MANIFEST chain)"},
           "forbidden_action_events": {"field": None, "status": "UNBOUND(no column; raw presence probe below)"}, "forbidden_action_count": {"field": None, "status": "UNBOUND"}}
COMPLETED_VALUES = ("ENDPOINT_REACHED", "COMPLETED", "SUCCESS")
FORBIDDEN_RE = re.compile(r"(password|passwd|credential|login[_ -]?submit|SUBMIT_LOGIN|captcha|payment|purchase|checkout|transfer_execute|reservation_submit|결제|송금|예약확정|구매하기|장바구니 담기|본인인증 완료)", re.I)
FORBIDDEN_RULE = "presence probe: regex " + FORBIDDEN_RE.pattern + " over every text/json file under raw/<target_id>/ (case-insensitive); a hit is LISTED with file:line, not judged — a guard log that names the action it blocked also matches"
KST = datetime.timezone(datetime.timedelta(hours=9))


def now(): return datetime.datetime.now(KST).isoformat(timespec="seconds")
def sha(p): return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()


def jsonl(p):
    rows, bad = [], []
    if not os.path.exists(p): return rows, bad, "ABSENT"
    for i, ln in enumerate(open(p, encoding="utf-8"), 1):
        if not ln.strip(): continue
        try: rows.append(json.loads(ln))
        except ValueError as e: bad.append({"line": i, "error": str(e)[:60]})
    return rows, bad, "PRESENT"


def newest_mart():
    c = ROOT / "mart" / "CANONICAL_MART_50.csv"
    if c.exists(): return c, "CANONICAL_MART_50"
    snaps = sorted(glob.glob(str(ROOT / "mart" / "snapshot_*.csv")), key=lambda p: int(re.findall(r"(\d+)", os.path.basename(p))[0]) if re.findall(r"(\d+)", os.path.basename(p)) else -1)
    return (pathlib.Path(snaps[-1]), os.path.basename(snaps[-1])) if snaps else (None, None)


def main():
    raw_m, m_bad, m_state = jsonl(ROOT / "raw" / "EVIDENCE_MANIFEST.jsonl")
    disp, d_bad, d_state = jsonl(ROOT / "raw" / "DISPATCH_LEDGER.jsonl")
    ingest, i_bad, i_state = jsonl(ROOT / "mart" / "INGEST_LEDGER.jsonl")
    mart_path, mart_id = newest_mart()
    rows = list(csv.DictReader(open(mart_path, encoding="utf-8", newline=""))) if mart_path else []
    raw_manifest = Q.git_show(Q.MANIFEST_PATH); manifest, fsha, bsha = Q.manifest_hashes(raw_manifest)
    rel = json.loads(Q.git_show(Q.RELEASE_PATH).decode("utf-8"))["manifest_binding"]
    ctl = Q.controls(manifest, raw_manifest, fsha, bsha); failed = {k: v for k, v in ctl.items() if v != "PASS"}
    if failed: print("controls failed", failed, file=sys.stderr); return 2
    if not rows and not raw_m and not disp:
        rec = {"schema": "C_MAIN50_EVIDENCE_ASSURED", "measured_at_kst": now(), "state": "NO_EVIDENCE_INPUT", "inputs": {"mart": mart_id, "evidence_manifest": m_state, "dispatch_ledger": d_state}, "exit": 3}
        _write(rec); print("NO_EVIDENCE_INPUT (exit 3)"); return 3
    flags = []; checks = {}
    def flag(check, msg, sysc=None, **ev): flags.append({"check": check, "message": msg, "systemic_candidate": sysc, **ev})
    # --- mart 7 checks
    qc = Q.qc(rows, manifest, fsha, bsha, rel["file_sha256"], rel["body_sha256"], ADAPTER) if rows else {"checks": {}, "flags": [], "n_rows": 0}
    if mart_id == "CANONICAL_MART_50":
        for f_ in qc["flags"]:
            if f_["check"] == "EVIDENCE_OR_TERMINAL" and "missing" in f_: f_["systemic_candidate"] = "denominator_corruption"
    checks.update({f"MART.{k}": v for k, v in qc["checks"].items()}); flags.extend(qc["flags"])
    if rows:
        extra, missing_cols = sorted(set(rows[0].keys()) - set(COLS23)), sorted(set(COLS23) - set(rows[0].keys()))
        if missing_cols or extra: flag("MART.COLUMNS", f"mart columns differ from the 23 fixed by TBX-006: missing {missing_cols} extra {extra}", None)
        checks["MART.COLUMNS"] = {"status": "FLAG" if (missing_cols or extra) else "PASS", "n_items": len(rows[0]), "missing": missing_cols, "extra": extra}
        blank = {}
        for r in rows:
            for c in COLS23:
                v = (r.get(c) or "").strip()
                if v == "" and c not in ("missing_reason",):
                    blank.setdefault(c, []).append(r.get("target_id"))
        no_reason = [r.get("target_id") for r in rows if any((r.get(c) or "").strip() in ("UNDETERMINED", "NOT_OBSERVED") for c in COLS23) and not (r.get("missing_reason") or "").strip()]
        for c, t in blank.items(): flag("MART.BLANKS", f"column {c} blank in {len(t)} rows — TBX-006: blank and 0 must not be the same output (use UNDETERMINED/NOT_OBSERVED + missing_reason)", None, column=c, targets=t[:10])
        if no_reason: flag("MART.BLANKS", f"{len(no_reason)} rows carry UNDETERMINED/NOT_OBSERVED without missing_reason", None, targets=no_reason[:10])
        checks["MART.BLANKS"] = {"status": "FLAG" if (blank or no_reason) else "PASS", "n_items": len(rows) * len(COLS23), "blank_columns": {c: len(t) for c, t in blank.items()}, "undetermined_without_reason": len(no_reason)}
        checks["MART.ATTEMPT_STATUS_VALUES"] = {"status": "REPORT", "n_items": len(rows), "distribution": dict(sorted(__import__("collections").Counter((r.get("attempt_status") or "").strip() for r in rows).items())), "completed_rule": f"attempt_status ∈ {COMPLETED_VALUES}"}
        c50 = ROOT / "mart" / "CANONICAL_MART_50.csv"; s50 = ROOT / "mart" / "CANONICAL_MART_50.sha256.json"
        if c50.exists():
            decl = json.load(open(s50)) if s50.exists() else {}
            fs = sha(c50); ok = decl.get("file_sha256") == fs and decl.get("row_count") == len(rows) == 50
            if not ok: flag("MART.CANONICAL_50", f"CANONICAL_MART_50: recomputed sha {fs[:12]} / rows {len(rows)} vs declared {str(decl.get('file_sha256'))[:12]} / {decl.get('row_count')}", "denominator_corruption" if len(rows) != 50 else None)
            checks["MART.CANONICAL_50"] = {"status": "PASS" if ok else "FLAG", "n_items": 1, "file_sha256_recomputed": fs, "declared": decl, "rows": len(rows)}
    # --- dispatch exactly-once
    if disp:
        from collections import Counter
        dk = {k: n for k, n in Counter(d.get("idempotency_key") for d in disp).items() if n > 1}; dt = {k: n for k, n in Counter(d.get("target_id") for d in disp).items() if n > 1}
        out = sorted({d.get("target_id") for d in disp} - {t["target_id"] for t in manifest["targets"]})
        for k, n in dk.items(): flag("RAW.DISPATCH", f"idempotency_key {k} dispatched {n}×", "duplicate_launch", key=k, n=n)
        for k, n in dt.items(): flag("RAW.DISPATCH", f"target {k} dispatched {n}× (retry must be ledgered)", None, target=k, n=n)
        for t in out: flag("RAW.DISPATCH", f"dispatched target {t} outside the frozen 50", "target_outside_manifest", target=t)
        checks["RAW.DISPATCH"] = {"status": "FLAG" if (dk or dt or out) else "PASS", "n_items": len(disp), "dispatched_unique": len({d.get("target_id") for d in disp}), "of": 50, "dup_keys": dk, "dup_targets": dt, "outside": out, "unparsable_lines": d_bad}
    else: checks["RAW.DISPATCH"] = {"status": "NOT_TESTABLE", "reason": f"DISPATCH_LEDGER {d_state} / 0 lines", "n_items": 0}
    # --- evidence chain + append-only
    if raw_m:
        breaks = [{"line": i + 1, "prev_hash": r.get("prev_hash"), "expected": raw_m[i - 1].get("evidence_hash")} for i, r in enumerate(raw_m) if i > 0 and r.get("prev_hash") != raw_m[i - 1].get("evidence_hash")]
        for b_ in breaks: flag("RAW.CHAIN", f"hash chain broken at line {b_['line']}", "evidence_overwrite", **b_)
        st = json.load(open(STATE)) if STATE.exists() else {"lines": []}
        cur = [hashlib.sha256(json.dumps(r, sort_keys=True, ensure_ascii=False).encode()).hexdigest() for r in raw_m]
        changed = [i + 1 for i, (a, b_) in enumerate(zip(st["lines"], cur)) if a != b_]; shrunk = len(cur) < len(st["lines"])
        for i in changed: flag("RAW.CHAIN", f"EVIDENCE_MANIFEST line {i} changed since the previous C run — append-only violated", "evidence_overwrite", line=i)
        if shrunk: flag("RAW.CHAIN", f"EVIDENCE_MANIFEST shrank {len(st['lines'])}→{len(cur)}", "evidence_overwrite")
        bad_tr = [{"line": i + 1, "terminal_reason": r.get("terminal_reason")} for i, r in enumerate(raw_m) if r.get("terminal_reason") not in (None, "") and r.get("terminal_reason") not in Q.TERMINAL_REASONS]
        for x in bad_tr: flag("RAW.CHAIN", f"non-canonical terminal_reason {x['terminal_reason']!r} in EVIDENCE_MANIFEST", None, **x)
        STATE.parent.mkdir(parents=True, exist_ok=True); json.dump({"lines": cur, "updated_at_kst": now()}, open(STATE, "w"))
        checks["RAW.CHAIN"] = {"status": "FLAG" if (breaks or changed or shrunk or bad_tr) else "PASS", "n_items": len(raw_m), "targets_with_evidence": len({r.get("target_id") for r in raw_m}), "of": 50,
                               "chain_breaks": len(breaks), "changed_lines_vs_previous_run": changed, "previous_run_lines": len(st["lines"]), "unparsable_lines": m_bad, "non_canonical_terminal": bad_tr}
        if rows:  # mart evidence_hash must exist in the chain
            hs = {r.get("evidence_hash") for r in raw_m}; miss = [r.get("target_id") for r in rows if (r.get("evidence_hash") or "").strip() and r.get("evidence_hash") not in hs]
            for t in miss: flag("MART.EVIDENCE_LINK", f"mart row {t} evidence_hash not found in EVIDENCE_MANIFEST chain", None, target=t)
            checks["MART.EVIDENCE_LINK"] = {"status": "FLAG" if miss else "PASS", "n_items": len(rows), "unlinked": miss}
    else: checks["RAW.CHAIN"] = {"status": "NOT_TESTABLE", "reason": f"EVIDENCE_MANIFEST {m_state} / 0 lines", "n_items": 0}
    # --- forbidden-action presence probe over raw dirs
    dirs = [d for d in glob.glob(str(ROOT / "raw" / "*")) if os.path.isdir(d)]; hits = []; nfiles = 0
    for d in dirs:
        for f in glob.glob(os.path.join(d, "**", "*"), recursive=True):
            if not os.path.isfile(f) or os.path.getsize(f) > 5_000_000: continue
            if not re.search(r"\.(json|jsonl|txt|csv|log|md|html?)$", f): continue
            nfiles += 1
            try:
                for i, ln in enumerate(open(f, encoding="utf-8", errors="replace"), 1):
                    m = FORBIDDEN_RE.search(ln)
                    if m and "html" not in f[-5:]: hits.append({"file": os.path.relpath(f, ROOT), "line": i, "match": m.group(0), "text": ln.strip()[:120]})
            except OSError: pass
    for h in hits[:200]: flag("RAW.FORBIDDEN_PROBE", "forbidden-action vocabulary present in raw evidence (probe hit — read before judging)", None, **h)
    checks["RAW.FORBIDDEN_PROBE"] = {"status": ("NOT_TESTABLE" if not dirs else "FLAG" if hits else "PASS"), "n_items": nfiles, "raw_target_dirs": len(dirs), "of": 50, "rule": FORBIDDEN_RULE, "hits": len(hits),
                                     "note": "html bodies excluded from the probe (page text names payments legitimately); this is a presence probe, not proof of execution — 0 hits ≠ 'no forbidden action'"}
    # --- ingest ledger
    if ingest:
        rej = [x for x in ingest if not x.get("promoted")]; checks["MART.INGEST"] = {"status": "REPORT", "n_items": len(ingest), "promoted": len(ingest) - len(rej), "rejected": len(rej), "reject_reasons": dict(__import__("collections").Counter(x.get("reject_reason") for x in rej)), "unparsable_lines": i_bad}
    for c in checks.values():
        if c.get("status") == "PASS" and c.get("n_items", 0) == 0: c["status"] = "VACUOUS"
    n_pass = sum(1 for c in checks.values() if c["status"] == "PASS"); n_flag = sum(1 for c in checks.values() if c["status"] == "FLAG")
    n_nt = sum(1 for c in checks.values() if c["status"] in ("NOT_TESTABLE", "VACUOUS"))
    head = subprocess.run(["git", "-C", Q.W, "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
    rec = {"schema": "C_MAIN50_EVIDENCE_ASSURED", "measured_at_kst": now(), "state": "STREAMING" if mart_id != "CANONICAL_MART_50" else "CANONICAL_50_SEEN",
           "checker": {"commit": head, "census_qc_c_sha256": sha(Q.HERE), "census_stream_c_sha256": sha(HERE), "checker_frozen": json.load(open(ROOT / "assurance" / "CHECKER_FROZEN.json")).get("checker", {}).get("commit_sha") if (ROOT / "assurance" / "CHECKER_FROZEN.json").exists() else None},
           "inputs": {"mart": mart_id, "mart_sha256": sha(mart_path) if mart_path else None, "mart_rows": len(rows), "evidence_manifest_lines": len(raw_m), "dispatch_lines": len(disp), "ingest_lines": len(ingest), "raw_target_dirs": len(dirs)},
           "manifest": {"file_sha256_recomputed": fsha, "body_sha256_recomputed": bsha, "matches_release": fsha == rel["file_sha256"] and bsha == rel["body_sha256"]},
           "controls": {"n": len(ctl), "pass": len(ctl)}, "adapter": ADAPTER, "summary": {"checks_pass": n_pass, "checks_flag": n_flag, "checks_not_testable_or_vacuous": n_nt, "flags": len(flags),
           "systemic_candidates": sorted({f["systemic_candidate"] for f in flags if f["systemic_candidate"]})}, "checks": checks, "flags": flags,
           "leakage_state": "NOT_ASSESSED_BEYOND_EXISTING_CONTROLS", "not_a_verdict": True, "exit": 0}
    _write(rec)
    print(json.dumps({"mart": mart_id, "rows": len(rows), "evidence_lines": len(raw_m), "dispatch": len(disp), **rec["summary"]}, ensure_ascii=False))
    for k, c in checks.items(): print(f"  {k:28s} {c['status']:12s} n={c.get('n_items')}" + (f" k={c['k']}/{c['of']}" if 'k' in c else ""))
    return 0


def _write(rec):
    OUT_C.parent.mkdir(parents=True, exist_ok=True); OUT_A.parent.mkdir(parents=True, exist_ok=True)
    hist = []
    if OUT_A.exists():
        try: old = json.load(open(OUT_A, encoding="utf-8")); hist = old.get("history", []) + [{k: old.get(k) for k in ("measured_at_kst", "state", "summary", "inputs")}]
        except ValueError: hist = [{"note": "previous file unreadable"}]
    rec["history"] = hist[-40:]
    for p in (OUT_A, OUT_C): p.write_text(json.dumps(rec, ensure_ascii=False, indent=1), encoding="utf-8")
    try:
        import bus; bus.hb(checker_frozen_sha=rec.get("checker", {}).get("commit"), census_qc=rec.get("summary") or rec.get("state"), census_qc_at=rec["measured_at_kst"])
    except Exception as e: print("hb update failed:", e, file=sys.stderr)


if __name__ == "__main__":
    try: sys.exit(main())
    except SystemExit: raise
    except Exception:
        import traceback; traceback.print_exc(); print("census_stream_c: did not run (exit 2)", file=sys.stderr); sys.exit(2)
