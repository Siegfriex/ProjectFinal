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
import csv, datetime, glob, hashlib, io, json, os, pathlib, re, subprocess, sys
HERE = pathlib.Path(__file__).resolve(); sys.path.insert(0, str(HERE.parent)); sys.path.insert(0, str(HERE.parents[1]))
import census_qc_c as Q  # noqa: E402
Q.TERMINAL_REASONS = tuple(sorted(set(Q.TERMINAL_REASONS) | {"ENDPOINT_REACHED", "WAF", "APP_REQUIRED", "AUTH_GATE", "NO_SAFE_ROUTE", "TIMEOUT", "PUBLIC_WEB_UNOBSERVABLE", "FORBIDDEN_ACTION_BOUNDARY", "COLLECTOR_ZERO_CANDIDATE", "NO_SAFE_ROUTE_SITE", "NO_SAFE_ROUTE_UNVERIFIED_CANDIDATE_COUNT"}))  # TBX-011 ∪ R11 ∪ R74 ∪ R92

ROOT = pathlib.Path("/home/sieg/projects-wsl/ProjectFinal/artifacts/v3_census")
RUN_ROOT = ROOT / "raw" / "E" / "E-REAL-CENSUS-1230"   # R66 (TBX-012): canonical raw run root; ledgers stay at raw/
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


def validate_raw_contract(raw_m, manifest):
    """TBX-011 raw record contract → (problems[], by_kind). Pure function so a synthetic control can exercise it."""
    probs = []
    if not raw_m: return probs
    TBX_TR = {"ENDPOINT_REACHED", "WAF", "APP_REQUIRED", "AUTH_GATE", "NO_SAFE_ROUTE", "TIMEOUT", "PUBLIC_WEB_UNOBSERVABLE", "FORBIDDEN_ACTION_BOUNDARY", "COLLECTOR_ZERO_CANDIDATE", "NO_SAFE_ROUTE_SITE", "NO_SAFE_ROUTE_UNVERIFIED_CANDIDATE_COUNT"}
    TBX_AS = {"ENDPOINT_REACHED", "TERMINAL_NO_ENDPOINT", "ERROR"}; TBX_LR = {"MATCH", "SEMANTIC_EQUIV", "DIFFERENT", "VISIBLE_ONLY", "AX_ONLY", "NONE", "NOT_OBSERVED"}
    TBX_ZONE = {"TOP", "BOTTOM", "LEFT", "RIGHT", "CENTER", "NOT_OBSERVED"}; TBX_AUTH = {"BEFORE_TASK_DISCOVERY", "AFTER_TASK_SELECT", "AT_ENDPOINT", "NONE", "NOT_OBSERVED", "UNDETERMINED"}  # R91
    REQ = ["target_id", "family_id", "service", "worker_id", "idempotency_key", "captured_at_kst", "evidence_dir", "evidence_hash", "prev_hash", "task_hash", "endpoint_hash",
           "attempt_status", "terminal_reason", "visible_label_text", "accessible_name", "accessible_name_source", "label_relation", "entry_x_norm", "entry_y_norm", "entry_zone",
           "entry_control_type", "nav_container_type", "reveal_direction", "menu_dependency", "task_flow_sequence", "experienced_flow_sequence", "activation_depth",
           "first_visible_scroll_state", "auth_gate_stage", "task_control_occlusion", "missing_reason"]
    NUM = ("entry_x_norm", "entry_y_norm", "activation_depth"); tf = {t["target_id"]: t["family_id"] for t in manifest["targets"]}
    expected_task_hash = {t["target_id"]: hashlib.sha256(f"{t['target_id']}|{t['frozen_task']}|{t['endpoint_contract']}".encode("utf-8")).hexdigest() for t in manifest["targets"]}
    probs = []
    for i, r in enumerate(raw_m, 1):
        miss = [k for k in REQ if k not in r]
        if miss: probs.append({"line": i, "kind": "MISSING_KEYS", "keys": miss})
        if r.get("target_id") not in tf: probs.append({"line": i, "kind": "TARGET_NOT_IN_MANIFEST", "target_id": r.get("target_id"), "systemic": "target_outside_manifest"})
        elif r.get("family_id") != tf[r["target_id"]]: probs.append({"line": i, "kind": "FAMILY_MISMATCH", "target_id": r["target_id"], "systemic": "task_contract_drift"})
        if i == 1 and r.get("prev_hash") is not None: probs.append({"line": 1, "kind": "FIRST_PREV_HASH_NOT_NULL"})
        if r.get("attempt_status") not in TBX_AS: probs.append({"line": i, "kind": "ATTEMPT_STATUS_ENUM", "value": r.get("attempt_status")})
        if r.get("terminal_reason") not in TBX_TR: probs.append({"line": i, "kind": "TERMINAL_REASON_ENUM(TBX-011)", "value": r.get("terminal_reason")})
        if r.get("label_relation") not in TBX_LR: probs.append({"line": i, "kind": "LABEL_RELATION_ENUM", "value": r.get("label_relation")})
        if r.get("entry_zone") not in TBX_ZONE: probs.append({"line": i, "kind": "ENTRY_ZONE_ENUM", "value": r.get("entry_zone")})
        if r.get("auth_gate_stage") not in TBX_AUTH: probs.append({"line": i, "kind": "AUTH_GATE_STAGE_ENUM", "value": r.get("auth_gate_stage")})
        for k in ("task_flow_sequence", "experienced_flow_sequence"):
            if k in r and not isinstance(r[k], list) and r[k] != "NOT_OBSERVED": probs.append({"line": i, "kind": "SEQUENCE_NOT_ARRAY", "key": k})
        for k in NUM:
            v = r.get(k)
            if v in ("", "NOT_OBSERVED", "NA_NUMERIC_UNOBSERVED"): probs.append({"line": i, "kind": "NUMERIC_MISSING_MUST_BE_NULL", "key": k, "value": v})
            if v is None and not (r.get("missing_reason") or ""): probs.append({"line": i, "kind": "NULL_WITHOUT_MISSING_REASON", "key": k})
        ed = r.get("evidence_dir")
        if isinstance(ed, str) and ed and not os.path.isdir(ed if os.path.isabs(ed) else os.path.join("/home/sieg/projects-wsl/ProjectFinal", ed)): probs.append({"line": i, "kind": "EVIDENCE_DIR_ABSENT", "evidence_dir": ed})
        exp = expected_task_hash.get(r.get("target_id"))
        if exp and r.get("task_hash") not in (None, "", "NOT_PROVIDED_BY_E") and r.get("task_hash") != exp:
            probs.append({"line": i, "kind": "TASK_HASH_MISMATCH", "target_id": r.get("target_id"), "got": str(r.get("task_hash"))[:16], "expected": exp[:16], "systemic": "task_contract_drift", "rule": "R68 sha256(f'{target_id}|{frozen_task}|{endpoint_contract}')"})
        if exp and r.get("task_hash") in (None, "", "NOT_PROVIDED_BY_E"): probs.append({"line": i, "kind": "TASK_HASH_NOT_PROVIDED", "target_id": r.get("target_id"), "note": "R68: task/endpoint gate runs empty — not a pass"})
    from collections import Counter
    dk = {k: n for k, n in Counter(r.get("idempotency_key") for r in raw_m).items() if n > 1}; dt = {k: n for k, n in Counter(r.get("target_id") for r in raw_m).items() if n > 1}
    for k, n in dk.items():
        dirs_k = {str(r.get("evidence_dir") or "") for r in raw_m if r.get("idempotency_key") == k}
        probs.append({"kind": "IDEMPOTENCY_KEY_DUP" if len(dirs_k) < n else "IDEMPOTENCY_KEY_REUSED_ACROSS_RUNS(R99 E defect)", "key": k, "n": n, "systemic": "duplicate_launch" if len(dirs_k) < n else None})
    # R84 (TBX-015): a re-measurement run (R2) appends a NEW line with a new run identity — exactly-once is per (target_id, run); a
    # second line per target is a REPORT unless its idempotency_key repeats (caught above) — never a duplicate_launch by target_id alone
    for k, n in dt.items(): probs.append({"kind": "TARGET_MULTI_LINE_REPORT", "target_id": k, "n": n, "systemic": None, "note": "R84: multiple runs per target are legitimate if run ids differ; duplicate_launch only on identical idempotency_key"})


    return probs


def raw_contract_controls(manifest):
    t0, t1 = manifest["targets"][0], manifest["targets"][1]
    def good(t, i, prev):
        return {"target_id": t["target_id"], "family_id": t["family_id"], "service": t["service_name"], "worker_id": "w1", "idempotency_key": f"k{i}", "captured_at_kst": "2026-08-28T11:00:00+09:00",
                "evidence_dir": "/", "evidence_hash": "a" * 64, "prev_hash": prev, "task_hash": hashlib.sha256(f"{t['target_id']}|{t['frozen_task']}|{t['endpoint_contract']}".encode()).hexdigest(), "endpoint_hash": "e" * 8, "attempt_status": "ENDPOINT_REACHED", "terminal_reason": "ENDPOINT_REACHED",
                "visible_label_text": "이체", "accessible_name": "이체", "accessible_name_source": "text", "label_relation": "MATCH", "entry_x_norm": 0.5, "entry_y_norm": 0.2, "entry_zone": "TOP",
                "entry_control_type": "button", "nav_container_type": "tab", "reveal_direction": "NONE", "menu_dependency": False, "task_flow_sequence": ["SELECT_FUNCTION"], "experienced_flow_sequence": ["SELECT_FUNCTION"],
                "activation_depth": 1, "first_visible_scroll_state": "S0", "auth_gate_stage": "NONE", "task_control_occlusion": False, "missing_reason": ""}
    g = [good(t0, 0, None), good(t1, 1, "a" * 64)]
    res = {"must_not_flag:two_good_lines": "PASS" if not validate_raw_contract(g, manifest) else f"FAIL {validate_raw_contract(g, manifest)[:2]}"}
    cases = {"first_prev_hash_not_null": ([{**g[0], "prev_hash": "x"}], "FIRST_PREV_HASH_NOT_NULL"), "terminal_enum": ([{**g[0], "terminal_reason": "GAVE_UP"}], "TERMINAL_REASON_ENUM(TBX-011)"),
             "attempt_enum": ([{**g[0], "attempt_status": "OK"}], "ATTEMPT_STATUS_ENUM"), "numeric_blank": ([{**g[0], "entry_x_norm": ""}], "NUMERIC_MISSING_MUST_BE_NULL"),
             "null_without_reason": ([{**g[0], "activation_depth": None}], "NULL_WITHOUT_MISSING_REASON"), "dup_idempotency": ([g[0], {**g[1], "idempotency_key": "k0"}], "IDEMPOTENCY_KEY_DUP"),
             "target_two_lines_report": ([g[0], {**g[1], "target_id": t0["target_id"], "family_id": t0["family_id"]}], "TARGET_MULTI_LINE_REPORT"), "target_outside": ([{**g[0], "target_id": "F9-99"}], "TARGET_NOT_IN_MANIFEST"),
             "missing_key": ([{k: v for k, v in g[0].items() if k != "task_hash"}], "MISSING_KEYS"), "sequence_not_array": ([{**g[0], "task_flow_sequence": "A>B"}], "SEQUENCE_NOT_ARRAY"),
             "task_hash_mismatch": ([{**g[0], "task_hash": "0" * 64}], "TASK_HASH_MISMATCH"), "task_hash_not_provided": ([{**g[0], "task_hash": "NOT_PROVIDED_BY_E"}], "TASK_HASH_NOT_PROVIDED")}
    for name, (rows, kind) in cases.items():
        kinds = {p["kind"] for p in validate_raw_contract(rows, manifest)}
        res[f"must_flag:{name}"] = "PASS" if kind in kinds else f"FAIL got {sorted(kinds)}"
    return res


def main():
    raw_m, m_bad, m_state = jsonl(ROOT / "raw" / "EVIDENCE_MANIFEST.jsonl")
    disp, d_bad, d_state = jsonl(ROOT / "raw" / "DISPATCH_LEDGER.jsonl")
    ingest, i_bad, i_state = jsonl(ROOT / "mart" / "INGEST_LEDGER.jsonl")
    mart_path, mart_id = newest_mart()
    # D-DEF-34 (D-V3-FINDING-033): one read_bytes → sha AND rows from the same bytes, never two reads of a file B is rewriting
    mart_bytes = mart_path.read_bytes() if mart_path else b""; mart_sha = hashlib.sha256(mart_bytes).hexdigest() if mart_path else None
    import io as _io
    rows = list(csv.DictReader(_io.StringIO(mart_bytes.decode("utf-8")))) if mart_path else []
    raw_manifest = Q.git_show(Q.MANIFEST_PATH); manifest, fsha, bsha = Q.manifest_hashes(raw_manifest)
    rel = json.loads(Q.git_show(Q.RELEASE_PATH).decode("utf-8"))["manifest_binding"]
    ctl = Q.controls(manifest, raw_manifest, fsha, bsha); ctl.update(raw_contract_controls(manifest)); failed = {k: v for k, v in ctl.items() if v != "PASS"}
    if "--selftest" in sys.argv:
        print(f"CONTROLS {len(ctl)-len(failed)}/{len(ctl)} PASS"); [print("  ", k, v) for k, v in ctl.items() if v != "PASS"]; return 2 if failed else 0
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
        APPROVED_EXTRA = {"entry_observation_provenance", "collection_run", "superseded_runs"}   # R76 / R98 / R99 (A-approved additions)
        extra, missing_cols = sorted(set(rows[0].keys()) - set(COLS23) - APPROVED_EXTRA), sorted(set(COLS23) - set(rows[0].keys()))
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
        if "collection_run" in rows[0]:
            from collections import Counter as _Ct
            by_run = {}
            for r in rows: by_run.setdefault((r.get("collection_run") or "").strip(), _Ct())[(r.get("terminal_reason") or "").strip()] += 1
            checks["MART.COLLECTION_RUN"] = {"status": "REPORT", "n_items": len(rows), "distribution": dict(_Ct((r.get("collection_run") or "").strip() for r in rows)),
                                             "terminal_by_run": {k: dict(v) for k, v in sorted(by_run.items())}, "rows_with_superseded_runs": sum(1 for r in rows if str(r.get("superseded_runs") or "").strip() not in ("", "[]", "NOT_OBSERVED", "NONE")),
                                             "note": "R98/R110: R1-only vs re-measured targets must be visible; terminal distribution per run is a reportable value"}
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
        roots = {}
        for d_ in disp: roots.setdefault(d_.get("idempotency_key"), set()).add(str(d_.get("scout_run_id") or d_.get("run_id") or d_.get("evidence_dir") or d_.get("dispatched_at_kst") or ""))
        for k, n in dk.items():
            same_run = len(roots.get(k, set())) < n
            flag("RAW.DISPATCH", f"idempotency_key {k} dispatched {n}×" + (" within the SAME run" if same_run else " across different runs — R99: E defect (key lacks run_id); legitimate re-measurement, not duplicate_launch"), "duplicate_launch" if same_run else None, key=k, n=n)
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
            hs = {r.get("evidence_hash") for r in raw_m}; by_t = {r.get("target_id"): r.get("evidence_hash") for r in raw_m}
            miss = [{"target": r.get("target_id"), "mart_evidence_hash": r.get("evidence_hash")[:12], "E_evidence_hash": (by_t.get(r.get("target_id")) or "")[:12]} for r in rows if Q._evidence_present(r.get("evidence_hash")) and r.get("evidence_hash") not in hs]
            for t in miss: flag("MART.EVIDENCE_LINK", f"mart row {t['target']} evidence_hash not found in EVIDENCE_MANIFEST chain (B hash ≠ E hash for the same target — provenance does not link)", None, **t)
            n_real = sum(1 for r in rows if Q._evidence_present(r.get("evidence_hash")))
            checks["MART.EVIDENCE_LINK"] = {"status": ("VACUOUS" if n_real == 0 else "FLAG" if miss else "PASS"), "n_items": n_real, "unlinked": miss, "rule": "mart evidence_hash (hash-shaped only) must equal some EVIDENCE_MANIFEST.evidence_hash"}
    else: checks["RAW.CHAIN"] = {"status": "NOT_TESTABLE", "reason": f"EVIDENCE_MANIFEST {m_state} / 0 lines", "n_items": 0}
    # --- TBX-011 raw record contract (E → B schema fixed by A). Enums are A's census contract; where they differ from the
    #     R11/R7/R13 vocabularies C reports the difference as an observation and validates against the TBX-011 set.
    if raw_m:
        from collections import Counter
        probs = validate_raw_contract(raw_m, manifest)
        for x in probs: flag("RAW.CONTRACT_TBX011", x.get("kind"), x.get("systemic"), **{k: v for k, v in x.items() if k not in ("kind", "systemic")})
        checks["RAW.CONTRACT_TBX011"] = {"status": "FLAG" if probs else "PASS", "n_items": len(raw_m), "problems": len(probs), "by_kind": dict(Counter(x["kind"] for x in probs)), "control": "raw_contract_controls() PASS in this run",
                                         "vocabulary_observation": "TBX-011 terminal_reason 8 values vs R11 16 values — C validates raw against TBX-011 (A's census contract); mart terminal_reason is checked against the union; entry_zone 5 values vs R7 7 zones; auth_gate_stage NONE vs R13 UNDETERMINED — reported, not judged"}
    # --- R82 (TBX-015): every first-run target with candidate_count==0 / COLLECTOR_ZERO_CANDIDATE must appear in the R2 run — no exceptions
    if raw_m:
        def run_of(r):
            m_ = re.search(r"-R(\d+)", str(r.get("scout_run_id") or "") + " " + str(r.get("evidence_dir") or "") + " " + str(r.get("idempotency_key") or "") + " " + str(r.get("run_id") or "") + " " + str(r.get("collection_run") or ""))
            return f"R{m_.group(1)}" if m_ else "R1"
        # R1 basis for the criterion = the FIRST frozen 50-row table (mart/snapshot_50.csv, R1-only) — the current mart has been superseded by R2/R3 rows
        r1_rows = rows
        if (ROOT / "mart" / "snapshot_50.csv").exists():
            _b = (ROOT / "mart" / "snapshot_50.csv").read_bytes(); r1_rows = list(csv.DictReader(io.StringIO(_b.decode("utf-8")))); r1_basis = f"snapshot_50.csv sha {hashlib.sha256(_b).hexdigest()[:12]}"
        else: r1_basis = "current mart (no snapshot_50.csv)"
        zero = sorted({r.get("target_id") for r in raw_m if run_of(r) == "R1" and (r.get("terminal_reason") == "COLLECTOR_ZERO_CANDIDATE" or r.get("route_diagnosis") == "COLLECTOR_ZERO_CANDIDATE" or r.get("candidate_count") == 0)})
        # criterion source: raw label OR the mart relabel (TBX-013 R74 was applied in the mart); R2 evidence = manifest lines OR dirs under the -R2 run root
        zero = sorted(set(zero) | {r.get("target_id") for r in r1_rows if str(r.get("terminal_reason") or "").strip() == "COLLECTOR_ZERO_CANDIDATE"})
        # R97 (TBX-018): criterion widened AFTER partial results (recorded as such) — union with ② attempt_status ERROR whose error is click_failed / Page.goto
        err2 = sorted({r.get("target_id") for r in r1_rows if str(r.get("attempt_status") or "").strip() == "ERROR" and re.search(r"click_failed|Page\.goto|page\.goto", str(r.get("experienced_flow_sequence") or "") + str(r.get("missing_reason") or ""))})
        zero_union = sorted(set(zero) | set(err2)); zero_narrow = zero; zero = zero_union
        r2_dirs = sorted({os.path.basename(d_) for d_ in glob.glob(str(RUN_ROOT) + "-R*/*") if os.path.isdir(d_)})
        r2 = sorted({r.get("target_id") for r in raw_m if run_of(r) != "R1"} | set(r2_dirs)); r2_open = bool(r2)
        missing_r2 = [t for t in zero if t not in r2]; extra_r2 = [t for t in r2 if t not in zero]
        if r2_open and missing_r2: flag("RAW.R2_COVERAGE", f"{len(missing_r2)}/{len(zero)} criterion targets have no re-measurement — at freeze this is an outcome-based selection (R82)", None, missing=missing_r2)
        # R103 (TBX-019): E's own pre-fixed mechanical criterion (route[].error contains click_failed) was accepted by A — targets outside C's
        # reconstructed criterion are REPORTED (criterion mismatch), not a leakage candidate; leakage would need a non-mechanical selection
        for t in extra_r2: flag("RAW.R2_COVERAGE", f"re-measured {t} is outside C's reconstructed criterion (R82∪R97) — E's click_failed criterion accepted by A (R103); listed, not judged", None, target=t)
        checks["RAW.R2_COVERAGE"] = {"status": ("NOT_TESTABLE" if not zero and not r2 else "FLAG" if (r2_open and missing_r2) or extra_r2 else "PASS" if r2_open else "PENDING_R2_NOT_OPENED"),
                                    "n_items": len(zero) + len(r2), "eligible_by_criterion": len(zero), "eligible_R82_narrow": len(zero_narrow), "eligible_R97_error_branch": len(err2), "criterion_history": "R82 narrow (COLLECTOR_ZERO_CANDIDATE) → R97 union with ERROR click_failed/Page.goto, widened after partial results (TBX-018)", "re_measured": len(r2), "r2_dirs_on_disk": len(r2_dirs), "r2_manifest_lines": sum(1 for r in raw_m if run_of(r) != "R1"), "r1_basis": r1_basis, "runs_seen": sorted({run_of(r) for r in raw_m}), "missing": missing_r2, "outside_criterion": extra_r2,
                                    "rule": "criterion = R1 candidate_count==0 / COLLECTOR_ZERO_CANDIDATE (mechanical, fixed before results); run detection = '-R2' in evidence_dir/idempotency_key"}
    # --- R102 (TBX-019): collection cutoff 11:50:00 KST by the line's own captured_at_kst — later lines are outside the freeze (kept, counted, not analysed)
    CUTOFF = "2026-08-28T11:50:00"
    if raw_m:
        late = [{"line": i + 1, "target_id": r.get("target_id"), "captured_at_kst": r.get("captured_at_kst"), "run": run_of(r)} for i, r in enumerate(raw_m) if str(r.get("captured_at_kst") or "")[:19] > CUTOFF]
        no_ts = [i + 1 for i, r in enumerate(raw_m) if not r.get("captured_at_kst")]
        checks["RAW.CUTOFF_1150"] = {"status": "REPORT", "n_items": len(raw_m), "after_cutoff_lines": len(late), "after_cutoff": late[:60], "lines_without_captured_at": no_ts, "rule": f"captured_at_kst > {CUTOFF} (string compare on ISO KST) — mtime is not used"}
        if rows and "collection_run" in rows[0]:
            late_t = {x["target_id"] for x in late}; late_runs = {}
            for x in late: late_runs.setdefault(x["target_id"], set()).add(x["run"])
            used_late = [r.get("target_id") for r in rows if r.get("target_id") in late_t and str(r.get("collection_run") or "")[-2:] in {u[-2:] for u in late_runs[r.get("target_id")]}]
            for t in used_late: flag("RAW.CUTOFF_1150", f"mart row {t} carries a run whose manifest line is after the 11:50 cutoff", None, target=t)
            checks["RAW.CUTOFF_1150"]["mart_rows_using_post_cutoff_run"] = used_late
    # --- forbidden-action presence probe over raw dirs
    dirs = [d for d in glob.glob(str(RUN_ROOT / "*")) if os.path.isdir(d)]; hits = []; nfiles = 0; exec_hits = []
    EXEC_RE = re.compile(r'"(action|action_token|type|event|kind)"\s*:\s*"(click|tap|press|submit|SUBMIT_QUERY|SUBMIT|enter)"', re.I)
    for d in dirs:
        for f in glob.glob(os.path.join(d, "**", "*"), recursive=True):
            if not os.path.isfile(f) or os.path.getsize(f) > 5_000_000: continue
            if not re.search(r"\.(json|jsonl|txt|csv|log|md|html?)$", f): continue
            nfiles += 1
            try:
                for i, ln in enumerate(open(f, encoding="utf-8", errors="replace"), 1):
                    m = FORBIDDEN_RE.search(ln)
                    if m and "html" not in f[-5:]:
                        h = {"file": os.path.relpath(f, ROOT), "line": i, "match": m.group(0), "text": ln.strip()[:120], "execution_shaped": bool(EXEC_RE.search(ln))}
                        hits.append(h)
                        if h["execution_shaped"]: exec_hits.append(h)
            except OSError: pass
    for h in hits[:200]: flag("RAW.FORBIDDEN_PROBE", "forbidden-action vocabulary present in raw evidence (probe hit — read before judging)", None, **h)
    checks["RAW.FORBIDDEN_PROBE"] = {"status": ("NOT_TESTABLE" if not dirs else "FLAG" if hits else "PASS"), "n_items": nfiles, "raw_target_dirs": len(dirs), "run_root": str(RUN_ROOT), "of": 50, "rule": FORBIDDEN_RULE, "hits": len(hits), "execution_shaped_hits": len(exec_hits), "execution_rule": "same line also carries an action/event key valued click|tap|press|submit|enter (R71: vocabulary ≠ execution; both listed, neither summed into violations)",
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
           "inputs": {"mart": mart_id, "mart_sha256": mart_sha, "mart_bytes": len(mart_bytes), "mart_rows": len(rows), "evidence_manifest_lines": len(raw_m), "dispatch_lines": len(disp), "ingest_lines": len(ingest), "raw_target_dirs": len(dirs)},
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
