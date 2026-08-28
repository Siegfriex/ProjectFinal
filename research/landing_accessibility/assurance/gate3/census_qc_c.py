#!/usr/bin/env python3
"""census_qc_c.py — C plane streaming QC for the frozen MAIN50 census (T-A-V3-TBX-007, release V3_TIMEBOX_CENSUS_1230).

FROZEN BEFORE COLLECTION. Scope is exactly the seven checks A reduced it to — nothing else is searched for
(leakage state stays NOT_ASSESSED_BEYOND_EXISTING_CONTROLS and is never written as 'no leakage'):
  1 UNIQUE_TARGETS        rows' target ids ⊆ manifest 50; unique count; reserve/unknown id → target_outside_manifest
  2 MANIFEST_HASH         body/file sha256 RECOMPUTED (never read from the declaration) vs the release's declared values
  3 DUPLICATE             duplicate target rows; duplicate (service_id, task_id, run_id) identity → duplicate_launch
  4 EVIDENCE_OR_TERMINAL  every one of the 50 has a row with an evidence pointer OR a canonical terminal_reason → k/50
  5 FORBIDDEN_ACTION      any executed forbidden action (event list / count / token) → forbidden_action; expected 0
  6 FAMILY_10x5           5 families × 10 unique targets, in the manifest AND in the rows
  7 DENOMINATORS          attempted / evidence_adequate / completed / failed per family + overall, recomputed from rows,
                          diffed against B's reported numbers when --b-denominators is given
Every check carries the number of items it ran on; a check that ran on 0 items is VACUOUS, never PASS. A canonical field
whose binding in the adapter map is UNBOUND makes the dependent check NOT_TESTABLE, never PASS (R57).
Controls run first on a synthetic bus built from the manifest itself (must_flag ×8, must_not_flag ×1, empty-input demo);
any control failure refuses the main run.
exit 0 = ran (flags are in the JSON, they never change the exit code) · 2 = did not run (controls failed / crash / bad input)
     · 3 = NO_EVIDENCE_INPUT (0 rows) — not a pass.
Flags name a systemic_candidate from the R9 canonical 8 where one applies; C flags, A rules (not_a_verdict).

usage: census_qc_c.py --rows PATH[.jsonl|.csv|dir] [--manifest FILE] [--adapter FILE] [--expect-body SHA --expect-file SHA]
                      [--b-denominators FILE] [--out FILE] [--selftest]
"""
import argparse, csv, datetime, glob, hashlib, io, json, os, pathlib, subprocess, sys, tempfile

HERE = pathlib.Path(__file__).resolve(); A_DIR = HERE.parents[1]
sys.path.insert(0, str(A_DIR / "gate1"))
from c_terminal_table import TERMINAL_REASONS  # noqa: E402  (16 canonical values)

W = "/home/sieg/projects-wsl/ProjectFinal/.agent_worktrees/claude_c_assurance_v21"
CONTROL_REF = "origin/control/landing-orchestrator"
MANIFEST_PATH = "research/landing_accessibility/control/v3/FINAL_MAIN50_MANIFEST.json"
RELEASE_PATH = "research/landing_accessibility/control/v3/V3_TIMEBOX_CENSUS_1230.json"
KST = datetime.timezone(datetime.timedelta(hours=9))
R9 = ("wrong_scope", "target_outside_manifest", "forbidden_action", "evidence_overwrite", "duplicate_launch",
      "task_contract_drift", "task_or_outcome_leakage", "denominator_corruption")
ENDPOINT_OK = ("ENDPOINT_REACHED",)          # 'completed' primary; AUTH_GATE reported separately (R2 two denominators)
CANON = ("target_id", "family_id", "service_id", "task_id", "run_id", "endpoint_status", "terminal_reason",
         "evidence_pointer", "evidence_sha256", "evidence_adequacy", "forbidden_action_events", "forbidden_action_count")
DEFAULT_ADAPTER = {  # canonical → {"field": B name, "status": WIRED_BY_SSOT | WIRED_BY_MANIFEST | UNBOUND}
    "target_id": {"field": "target_id", "status": "WIRED_BY_MANIFEST"}, "family_id": {"field": "family_id", "status": "WIRED_BY_MANIFEST"},
    "service_id": {"field": "service_id", "status": "WIRED_BY_SSOT"}, "task_id": {"field": "task_id", "status": "WIRED_BY_SSOT"},
    "run_id": {"field": "run_id", "status": "WIRED_BY_SSOT"}, "endpoint_status": {"field": "endpoint_status", "status": "WIRED_BY_SSOT"},
    "terminal_reason": {"field": "terminal_reason", "status": "WIRED_BY_SSOT"},
    "evidence_pointer": {"field": "path_manifest_path", "status": "WIRED_BY_SSOT"},
    "evidence_sha256": {"field": None, "status": "UNBOUND"}, "evidence_adequacy": {"field": None, "status": "UNBOUND"},
    "forbidden_action_events": {"field": None, "status": "UNBOUND"}, "forbidden_action_count": {"field": None, "status": "UNBOUND"},
    "service_name": {"field": None, "status": "UNBOUND"},
    "_note": "02_DATA_SCHEMA names are bound by the SSOT; manifest names by FINAL_MAIN50_MANIFEST; the rest stay UNBOUND until B/E publish"
             " the snapshot layout. UNBOUND ⇒ dependent check NOT_TESTABLE (R57). Never guess a name.",
}


def now_kst():
    return datetime.datetime.now(KST).isoformat(timespec="seconds")


def git_show(path):
    r = subprocess.run(["git", "-C", W, "show", f"{CONTROL_REF}:{path}"], capture_output=True)
    if r.returncode != 0:
        raise RuntimeError(f"git show failed for {path}: {r.stderr.decode()[:200]}")
    return r.stdout


def manifest_hashes(raw: bytes):
    m = json.loads(raw.decode("utf-8"))
    body = {k: v for k, v in m.items() if k != "manifest_sha256"}
    s = json.dumps(body, sort_keys=False, indent=1, separators=(",", ": "), ensure_ascii=False)
    return m, hashlib.sha256(raw).hexdigest(), hashlib.sha256(s.encode("utf-8")).hexdigest()


def load_rows(path):
    if path is None:
        return []
    files = sorted(glob.glob(os.path.join(path, "*"))) if os.path.isdir(path) else [path]
    rows = []
    for f in files:
        if f.endswith(".jsonl"):
            for ln in open(f, encoding="utf-8"):
                ln = ln.strip()
                if ln: rows.append(json.loads(ln))
        elif f.endswith(".json"):
            d = json.load(open(f, encoding="utf-8")); rows.extend(d if isinstance(d, list) else d.get("rows", [d]))
        elif f.endswith(".csv"):
            rows.extend(csv.DictReader(open(f, encoding="utf-8", newline="")))
    return rows


class Bind:
    def __init__(self, adapter):
        self.a = adapter
    def ok(self, canon):
        return self.a.get(canon, {}).get("status", "UNBOUND") != "UNBOUND" and self.a[canon].get("field")
    def get(self, row, canon):
        f = self.a.get(canon, {}).get("field")
        return row.get(f) if f else None


SENTINELS = frozenset({"", "NOT_OBSERVED", "UNDETERMINED", "NA_NUMERIC_UNOBSERVED", "NOT_ATTEMPTED", "NA", "N/A", "NULL", "None", "nan"})
HASH_RE = __import__("re").compile(r"^[0-9a-fA-F]{16,128}$")
NOT_ATTEMPTED_VALUES = frozenset({"NOT_ATTEMPTED", ""})


def _truthy(v):
    """present = a real value, never a placeholder token (snapshot_00 lesson: 'NOT_OBSERVED' read as evidence → 50/50 phantom)."""
    if v is None or isinstance(v, bool) and v is False: return False
    if isinstance(v, (list, dict)): return bool(v)
    sv = str(v).strip()
    return sv not in SENTINELS and sv not in ("0", "false", "False", "[]")


def _evidence_present(v):
    """an evidence pointer counts only if it looks like a hash (hex ≥16) or a path that exists — a token never does."""
    if not _truthy(v): return False
    sv = str(v).strip()
    return bool(HASH_RE.match(sv)) or os.path.exists(sv)


def qc(rows, manifest, file_sha, body_sha, expect_file, expect_body, adapter, b_denoms=None):
    b = Bind(adapter); flags = []; checks = {}
    def flag(check, msg, systemic=None, **ev):
        assert systemic in (None,) + R9
        flags.append({"check": check, "message": msg, "systemic_candidate": systemic, **ev})
    targets = {t["target_id"]: t for t in manifest["targets"]}
    # reserve entries carry no target_id (identity = family_id/reserve_rank/service_name): a reserve is detected by service_name
    reserve = {t.get("service_name") for t in manifest.get("replacement_reserve", []) if isinstance(t, dict)} - {None}
    fam_of = {tid: t["family_id"] for tid, t in targets.items()}
    # ---- 2 MANIFEST_HASH (independent of rows)
    hm = {"file_recomputed": file_sha, "body_recomputed": body_sha, "file_expected": expect_file, "body_expected": expect_body,
          "declared_in_manifest": manifest.get("manifest_sha256")}
    st = "PASS" if (file_sha == expect_file and body_sha == expect_body) else "FLAG"
    if st == "FLAG": flag("MANIFEST_HASH", "recomputed manifest hash differs from the release's declared value", "wrong_scope", **hm)
    checks["MANIFEST_HASH"] = {"status": st, "n_items": 2, **hm}
    # ---- 6a FAMILY_10x5 on the manifest
    fam_m = {}
    for tid, f in fam_of.items(): fam_m.setdefault(f, set()).add(tid)
    fam_m_ok = len(fam_m) == 5 and all(len(v) == 10 for v in fam_m.values())
    if not fam_m_ok: flag("FAMILY_10x5", "manifest is not 5 families × 10 targets", "wrong_scope", families={k: len(v) for k, v in fam_m.items()})
    if not rows:
        checks["FAMILY_10x5"] = {"status": "PASS" if fam_m_ok else "FLAG", "n_items": len(fam_of), "manifest_families": {k: len(v) for k, v in sorted(fam_m.items())}, "rows": "NO_ROWS"}
        return {"checks": checks, "flags": flags, "n_rows": 0}
    if not b.ok("target_id"):
        for c in ("UNIQUE_TARGETS", "DUPLICATE", "EVIDENCE_OR_TERMINAL", "FAMILY_10x5", "DENOMINATORS"):
            checks[c] = {"status": "NOT_TESTABLE", "reason": "target_id UNBOUND in adapter (R57)", "n_items": 0}
        checks["FORBIDDEN_ACTION"] = {"status": "NOT_TESTABLE", "reason": "target_id UNBOUND", "n_items": 0}
        return {"checks": checks, "flags": flags, "n_rows": len(rows)}
    tids = [b.get(r, "target_id") for r in rows]
    # ---- 1 UNIQUE_TARGETS
    outside = sorted({t for t in tids if t not in targets})
    svc_of = {b.get(r, "target_id"): b.get(r, "service_name") for r in rows} if b.ok("service_name") else {}
    for t in outside:
        is_res = svc_of.get(t) in reserve
        flag("UNIQUE_TARGETS", f"row target {t!r} is not one of the 50 frozen targets" + (" (service_name is a RESERVE entry — replacement after start is forbidden)" if is_res else ""),
             "target_outside_manifest", target=t, is_reserve=is_res, reserve_check="RAN" if svc_of else "NOT_TESTABLE (service_name UNBOUND)")
    uniq = sorted({t for t in tids if t in targets})
    checks["UNIQUE_TARGETS"] = {"status": "FLAG" if outside else "PASS", "n_items": len(tids), "unique_in_manifest": len(uniq), "of": 50, "outside": outside}
    # ---- 3 DUPLICATE
    from collections import Counter
    dup_t = {t: n for t, n in Counter(tids).items() if n > 1}
    ident_bound = all(b.ok(k) for k in ("service_id", "task_id", "run_id"))
    dup_id = {}
    if ident_bound:
        idents = Counter((b.get(r, "service_id"), b.get(r, "task_id"), b.get(r, "run_id")) for r in rows)
        dup_id = {"|".join(map(str, k)): n for k, n in idents.items() if n > 1}
        for k, n in dup_id.items(): flag("DUPLICATE", f"identity {k} appears {n}× — exactly-once violated", "duplicate_launch", identity=k, n=n)
    for t, n in dup_t.items():
        flag("DUPLICATE", f"target {t} has {n} rows (one attempted row per frozen unit expected; a retry must carry a distinct run_id AND a ledger entry)",
             "duplicate_launch" if not ident_bound else None, target=t, n=n)
    checks["DUPLICATE"] = {"status": "FLAG" if (dup_t or dup_id) else "PASS", "n_items": len(rows), "duplicate_targets": dup_t, "duplicate_identities": dup_id,
                           "identity_check": "RAN" if ident_bound else "NOT_TESTABLE (service_id/task_id/run_id UNBOUND)"}
    # ---- 4 EVIDENCE_OR_TERMINAL
    ev_bound, tr_bound = b.ok("evidence_pointer"), b.ok("terminal_reason")
    if not (ev_bound or tr_bound):
        checks["EVIDENCE_OR_TERMINAL"] = {"status": "NOT_TESTABLE", "reason": "neither evidence_pointer nor terminal_reason bound", "n_items": 0}
    else:
        have = {}; bad_tr = []
        for r in rows:
            t = b.get(r, "target_id")
            if t not in targets: continue
            ev = _evidence_present(b.get(r, "evidence_pointer")) if ev_bound else False
            tr = b.get(r, "terminal_reason") if tr_bound else None
            tr_ok = tr in TERMINAL_REASONS
            not_att = b.ok("endpoint_status") and str(b.get(r, "endpoint_status") or "").strip() in NOT_ATTEMPTED_VALUES
            if tr not in (None, "") and not tr_ok and not (not_att and str(tr).strip() in SENTINELS): bad_tr.append({"target": t, "terminal_reason": tr})
            have[t] = have.get(t, False) or ev or tr_ok
        k = sum(1 for t in targets if have.get(t))
        missing = sorted(t for t in targets if not have.get(t))
        for x in bad_tr: flag("EVIDENCE_OR_TERMINAL", f"non-canonical terminal_reason {x['terminal_reason']!r} (16 values, R11/Δ30/Δ32/Δ47)", None, **x)
        if missing: flag("EVIDENCE_OR_TERMINAL", f"{len(missing)}/50 frozen units have neither evidence nor a canonical terminal_reason (streaming: pending; at CANONICAL_MART_50 freeze this is denominator corruption)", None, missing=missing)
        checks["EVIDENCE_OR_TERMINAL"] = {"status": "FLAG" if (missing or bad_tr) else "PASS", "k": k, "of": 50, "n_items": len(rows), "missing": missing, "non_canonical_terminal": bad_tr}
    # ---- 5 FORBIDDEN_ACTION
    fb_e, fb_c = b.ok("forbidden_action_events"), b.ok("forbidden_action_count")
    if not (fb_e or fb_c):
        checks["FORBIDDEN_ACTION"] = {"status": "NOT_TESTABLE", "reason": "forbidden_action_events/count UNBOUND — 0 is NOT claimed", "n_items": 0}
    else:
        hits = []
        for r in rows:
            ev = b.get(r, "forbidden_action_events") if fb_e else None
            if isinstance(ev, str):
                try: ev = json.loads(ev)
                except ValueError: ev = [ev] if ev.strip() else []
            n = len(ev) if isinstance(ev, list) else 0
            c = b.get(r, "forbidden_action_count") if fb_c else None
            try: n = max(n, int(c)) if c not in (None, "") else n
            except ValueError: flag("FORBIDDEN_ACTION", f"unreadable forbidden_action_count {c!r}", None, target=b.get(r, "target_id"))
            if n: hits.append({"target": b.get(r, "target_id"), "n": n, "events": ev if isinstance(ev, list) else None})
        for h in hits: flag("FORBIDDEN_ACTION", f"forbidden action executed on {h['target']} ({h['n']})", "forbidden_action", **h)
        checks["FORBIDDEN_ACTION"] = {"status": "FLAG" if hits else "PASS", "n_items": len(rows), "hits": len(hits)}
    # ---- 6b FAMILY_10x5 on rows
    fam_r = {}
    for r in rows:
        t = b.get(r, "target_id")
        if t in targets: fam_r.setdefault(fam_of[t], set()).add(t)
    fam_r_ok = len(fam_r) == 5 and all(len(v) == 10 for v in fam_r.values())
    if not fam_r_ok: flag("FAMILY_10x5", "rows do not cover 5 families × 10 unique frozen targets", "denominator_corruption", families={k: len(v) for k, v in sorted(fam_r.items())})
    if b.ok("family_id"):
        mism = [{"target": b.get(r, "target_id"), "row_family": b.get(r, "family_id"), "manifest_family": fam_of.get(b.get(r, "target_id"))}
                for r in rows if b.get(r, "target_id") in targets and b.get(r, "family_id") not in (None, "", fam_of[b.get(r, "target_id")])]
        for x in mism: flag("FAMILY_10x5", "row family_id differs from the manifest", "task_contract_drift", **x)
    else: mism = "NOT_TESTABLE (family_id UNBOUND)"
    checks["FAMILY_10x5"] = {"status": "FLAG" if not (fam_m_ok and fam_r_ok) or (isinstance(mism, list) and mism) else "PASS", "n_items": len(rows),
                             "manifest_families": {k: len(v) for k, v in sorted(fam_m.items())}, "row_families": {k: len(v) for k, v in sorted(fam_r.items())}, "family_mismatch": mism}
    # ---- 7 DENOMINATORS
    den = {}
    for f in sorted(fam_m):
        fr = [r for r in rows if b.get(r, "target_id") in fam_m[f]]
        att = {b.get(r, "target_id") for r in fr}
        att_obs = {b.get(r, "target_id") for r in fr if not (b.ok("endpoint_status") and str(b.get(r, "endpoint_status") or "").strip() in NOT_ATTEMPTED_VALUES)}
        ev_ok = {b.get(r, "target_id") for r in fr if (ev_bound and _evidence_present(b.get(r, "evidence_pointer"))) or (b.ok("evidence_adequacy") and _truthy(b.get(r, "evidence_adequacy")))}
        comp = {b.get(r, "target_id") for r in fr if b.ok("endpoint_status") and b.get(r, "endpoint_status") in ENDPOINT_OK}
        auth = {b.get(r, "target_id") for r in fr if b.ok("endpoint_status") and b.get(r, "endpoint_status") == "AUTH_GATE"}
        failed = att_obs - comp   # R78 (TBX-014): failed = attempted but endpoint not reached (TERMINAL_NO_ENDPOINT included); unaccounted must be 0
        from collections import Counter as _C
        tb = dict(sorted(_C(str(b.get(r, "terminal_reason") or "").strip() for r in fr if b.get(r, "target_id") in failed).items())) if tr_bound else "NOT_TESTABLE"
        den[f] = {"frozen": len(fam_m[f]), "attempted": len(att), "attempted_observed": len(att_obs), "evidence_adequate": len(ev_ok), "completed_endpoint_reached": len(comp), "auth_gate_terminal": len(auth), "failed": len(failed),
                  "unaccounted": len(att_obs) - len(comp) - len(failed), "failed_by_terminal_reason": tb}
        if not (len(att) <= 10 and len(att_obs) <= len(att) and len(ev_ok) <= len(att_obs) and len(comp) <= len(ev_ok) + len(auth) and len(comp) + len(failed) <= len(att_obs)):
            flag("DENOMINATORS", f"family {f} denominators are not monotonic (frozen ≥ attempted ≥ evidence_adequate; completed+failed ≤ attempted)", "denominator_corruption", family=f, **den[f])
    den["overall"] = {k: sum(den[f][k] for f in fam_m) for k in ("frozen", "attempted", "attempted_observed", "evidence_adequate", "completed_endpoint_reached", "auth_gate_terminal", "failed")}
    diff = None
    if b_denoms:
        diff = {}
        for f, d in b_denoms.items():
            for k, v in (d or {}).items():
                mine = den.get(f, {}).get(k)
                if mine is not None and mine != v:
                    diff[f"{f}.{k}"] = {"B": v, "C": mine}; flag("DENOMINATORS", f"B-reported {f}.{k}={v} ≠ C-recomputed {mine}", "denominator_corruption", key=f"{f}.{k}", B=v, C=mine)
    checks["DENOMINATORS"] = {"status": "FLAG" if any(x["check"] == "DENOMINATORS" for x in flags) else "PASS", "n_items": len(rows), "per_family": den,
                              "evidence_adequate_basis": ("evidence_pointer" if ev_bound else "") + ("+evidence_adequacy" if b.ok("evidence_adequacy") else ""),
                              "completed_rule": "endpoint_status == ENDPOINT_REACHED (AUTH_GATE counted separately — R2 two denominators)",
                              "r78_rule": "completed = ENDPOINT_REACHED only; failed = attempted_observed − completed (TERMINAL_NO_ENDPOINT ∈ failed); COLLECTOR_ZERO_CANDIDATE (collector's zero) and NO_SAFE_ROUTE_SITE (site fact) are listed separately in failed_by_terminal_reason, never merged", "attempted_rule": "attempted = rows present for the frozen unit (A: always 10/50); attempted_observed = attempt/endpoint status not in NOT_ATTEMPTED/blank; evidence_adequate = pointer is a hash/existing path (placeholder tokens never count)", "diff_vs_B": diff}
    for c in checks.values():
        if c.get("status") == "PASS" and c.get("n_items", 0) == 0: c["status"] = "VACUOUS"
    return {"checks": checks, "flags": flags, "n_rows": len(rows)}


# ------------------------------------------------------------------------------------------------ controls
def synth_rows(manifest, evidence=True):
    rows = []
    for i, t in enumerate(manifest["targets"]):
        rows.append({"target_id": t["target_id"], "family_id": t["family_id"], "service_id": f"svc{i}", "task_id": t["family_id"], "run_id": f"run{i}",
                     "endpoint_status": "ENDPOINT_REACHED" if i % 3 else "AUTH_GATE", "terminal_reason": "" if i % 3 else "OTHER",
                     "path_manifest_path": hashlib.sha256(t['target_id'].encode()).hexdigest() if evidence else "", "forbidden_events": "[]", "forbidden_n": 0, "svc_name": t["service_name"]})
    return rows


CTL_ADAPTER = {**{k: dict(v) for k, v in DEFAULT_ADAPTER.items() if k != "_note"},
               "forbidden_action_events": {"field": "forbidden_events", "status": "WIRED_CONTROL"}, "forbidden_action_count": {"field": "forbidden_n", "status": "WIRED_CONTROL"},
               "service_name": {"field": "svc_name", "status": "WIRED_CONTROL"}}


def controls(manifest, raw, file_sha, body_sha):
    res = {}
    base = synth_rows(manifest)
    def run(rows, fs=file_sha, bs=body_sha, adapter=CTL_ADAPTER, bd=None):
        return qc(rows, manifest, fs, bs, file_sha, body_sha, adapter, bd)
    def has(out, check, sysc=None):
        return any(f["check"] == check and (sysc is None or f["systemic_candidate"] == sysc) for f in out["flags"])
    o = run(base)
    res["must_not_flag:consistent_50→0_flags"] = "PASS" if not o["flags"] and all(c["status"] == "PASS" for c in o["checks"].values()) else f"FAIL {[(k, c['status']) for k, c in o['checks'].items()]} {o['flags'][:2]}"
    res["must_not_flag:all_7_checks_ran"] = "PASS" if len(o["checks"]) == 7 and all(c.get("n_items", 0) > 0 for c in o["checks"].values()) else f"FAIL {len(o['checks'])}"
    o = run(base + [{**base[0], "target_id": "F9-99", "run_id": "rx"}]); res["must_flag:extra_target→target_outside_manifest"] = "PASS" if has(o, "UNIQUE_TARGETS", "target_outside_manifest") else "FAIL"
    rsvc = manifest["replacement_reserve"][0]["service_name"]
    o = run(base + [{**base[0], "target_id": "F1-R1", "run_id": "rr", "svc_name": rsvc}]); res["must_flag:reserve_service_used→is_reserve"] = "PASS" if any(f.get("is_reserve") for f in o["flags"]) else "FAIL"
    o = run(base + [dict(base[3])]); res["must_flag:duplicate_identity→duplicate_launch"] = "PASS" if has(o, "DUPLICATE", "duplicate_launch") else "FAIL"
    o = run(base[:-1]); res["must_flag:49_rows→EVIDENCE_OR_TERMINAL 49/50 + FAMILY"] = "PASS" if o["checks"]["EVIDENCE_OR_TERMINAL"]["k"] == 49 and has(o, "EVIDENCE_OR_TERMINAL") and has(o, "FAMILY_10x5") else "FAIL"
    o = run([{**r, "path_manifest_path": "", "terminal_reason": ""} if i == 7 else r for i, r in enumerate(base)]); res["must_flag:row_without_evidence_or_terminal"] = "PASS" if o["checks"]["EVIDENCE_OR_TERMINAL"]["k"] == 49 else "FAIL"
    o = run([{**r, "terminal_reason": "GAVE_UP"} if i == 2 else r for i, r in enumerate(base)]); res["must_flag:non_canonical_terminal_reason"] = "PASS" if o["checks"]["EVIDENCE_OR_TERMINAL"]["non_canonical_terminal"] else "FAIL"
    o = run([{**r, "forbidden_events": '["login submit"]'} if i == 5 else r for i, r in enumerate(base)]); res["must_flag:forbidden_event→forbidden_action"] = "PASS" if has(o, "FORBIDDEN_ACTION", "forbidden_action") else "FAIL"
    o = run(base, fs="0" * 64); res["must_flag:manifest_hash_mismatch→wrong_scope"] = "PASS" if has(o, "MANIFEST_HASH", "wrong_scope") else "FAIL"
    o = run([{**r, "family_id": "F1"} if r["family_id"] == "F2" and i % 5 == 0 else r for i, r in enumerate(base)]); res["must_flag:family_id_drift"] = "PASS" if has(o, "FAMILY_10x5", "task_contract_drift") else "FAIL"
    skel = [{**r, "endpoint_status": "NOT_ATTEMPTED", "terminal_reason": "UNDETERMINED", "path_manifest_path": "NOT_OBSERVED"} for r in base]
    o = run(skel); d0 = o["checks"]["DENOMINATORS"]["per_family"]["overall"]
    res["must_flag:skeleton_50_placeholders→attempted_observed 0·evidence 0·k 0/50"] = "PASS" if (d0["attempted_observed"] == 0 and d0["evidence_adequate"] == 0 and o["checks"]["EVIDENCE_OR_TERMINAL"]["k"] == 0 and has(o, "EVIDENCE_OR_TERMINAL") and not o["checks"]["EVIDENCE_OR_TERMINAL"]["non_canonical_terminal"]) else f"FAIL {d0} k={o['checks']['EVIDENCE_OR_TERMINAL']['k']}"
    o = run([{**r, "path_manifest_path": "NOT_OBSERVED"} if i == 4 else r for i, r in enumerate(base)]); res["must_flag:token_as_evidence_pointer_not_counted"] = "PASS" if o["checks"]["DENOMINATORS"]["per_family"]["overall"]["evidence_adequate"] == 49 else "FAIL"
    o = run(base, bd={"overall": {"attempted": 49}}); res["must_flag:B_denominator_49_vs_C_50"] = "PASS" if has(o, "DENOMINATORS", "denominator_corruption") else "FAIL"
    o = run(base, adapter={**CTL_ADAPTER, "forbidden_action_events": {"field": None, "status": "UNBOUND"}, "forbidden_action_count": {"field": None, "status": "UNBOUND"}})
    res["unbound:forbidden→NOT_TESTABLE_not_PASS"] = "PASS" if o["checks"]["FORBIDDEN_ACTION"]["status"] == "NOT_TESTABLE" else "FAIL"
    o = run([]); res["empty_input:no_row_checks_claim_PASS"] = "PASS" if o["n_rows"] == 0 and not any(c.get("status") == "PASS" for k, c in o["checks"].items() if k not in ("MANIFEST_HASH", "FAMILY_10x5")) else "FAIL"
    return res


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("--rows"); ap.add_argument("--manifest"); ap.add_argument("--adapter"); ap.add_argument("--expect-body"); ap.add_argument("--expect-file")
    ap.add_argument("--b-denominators"); ap.add_argument("--out", default=str(HERE.parent / "out" / "CENSUS_QC_C.json")); ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args(argv)
    raw = open(a.manifest, "rb").read() if a.manifest else git_show(MANIFEST_PATH)
    manifest, file_sha, body_sha = manifest_hashes(raw)
    if a.expect_body and a.expect_file:
        exp_b, exp_f, exp_src = a.expect_body, a.expect_file, "argv"
    else:
        rel = json.loads(git_show(RELEASE_PATH).decode("utf-8")); mb = rel["manifest_binding"]; exp_b, exp_f, exp_src = mb["body_sha256"], mb["file_sha256"], f"{CONTROL_REF}:{RELEASE_PATH}"
    ctl = controls(manifest, raw, file_sha, body_sha)
    failed = {k: v for k, v in ctl.items() if v != "PASS"}
    print(f"CONTROLS {len(ctl) - len(failed)}/{len(ctl)} PASS"); [print("  ", k, v) for k, v in ctl.items()]
    if failed:
        print("controls failed — main run refused (exit 2)", file=sys.stderr); return 2
    if a.selftest:
        return 0
    adapter = json.load(open(a.adapter, encoding="utf-8")) if a.adapter else DEFAULT_ADAPTER
    rows = load_rows(a.rows)
    bd = json.load(open(a.b_denominators, encoding="utf-8")) if a.b_denominators else None
    out = qc(rows, manifest, file_sha, body_sha, exp_f, exp_b, adapter, bd)
    rec = {"schema": "C_CENSUS_QC", "ruling": "T-A-V3-TBX-007 / V3_TIMEBOX_CENSUS_1230", "measured_at_kst": now_kst(), "tool_sha256": hashlib.sha256(HERE.read_bytes()).hexdigest(),
           "rows_input": a.rows, "n_rows": out["n_rows"], "manifest": {"version": manifest.get("version"), "file_sha256_recomputed": file_sha, "body_sha256_recomputed": body_sha, "expected_from": exp_src},
           "adapter": {k: v for k, v in adapter.items() if k != "_note"}, "controls": ctl, "checks": out["checks"], "flags": out["flags"], "n_flags": len(out["flags"]),
           "systemic_candidates": sorted({f["systemic_candidate"] for f in out["flags"] if f["systemic_candidate"]}),
           "leakage_state": "NOT_ASSESSED_BEYOND_EXISTING_CONTROLS", "not_a_verdict": True, "exit": 3 if out["n_rows"] == 0 else 0}
    pathlib.Path(a.out).parent.mkdir(parents=True, exist_ok=True); pathlib.Path(a.out).write_text(json.dumps(rec, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps({k: (v.get("status"), {kk: vv for kk, vv in v.items() if kk in ("k", "of", "unique_in_manifest", "hits", "n_items")}) for k, v in out["checks"].items()}, ensure_ascii=False, indent=1))
    print("flags", len(out["flags"]), "systemic_candidates", rec["systemic_candidates"], "→", a.out)
    if out["n_rows"] == 0:
        print("NO_EVIDENCE_INPUT — 0 rows: not a pass (exit 3)", file=sys.stderr); return 3
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main(sys.argv[1:]))
    except SystemExit:
        raise
    except Exception:
        import traceback; traceback.print_exc(); print("census_qc_c: did not run (exit 2)", file=sys.stderr); sys.exit(2)
