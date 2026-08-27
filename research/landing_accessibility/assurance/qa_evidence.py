#!/usr/bin/env python3
"""Independent evidence / batch / joint-valid verifier (Claude C).

Reads Claude B's runner output WITHOUT importing B code. Definitions re-implemented from:
  - docs/07_EVIDENCE_MANIFEST_CONTRACT.md  (manifest.jsonl: observation_id/relpath/sha256/bytes, no abs/'..', no symlink)
  - A1 §6.3 / engine identity (observation_id = sha256(NFC-strip 5 fields joined by \\x1f)[:32])
  - B ledger definition (batch_hash = sha256(compact sorted JSON of manifest minus 'batch_hash'))
  - ANALYSIS_CONTRACT LA-AC-20260827 §1 (J1..J4, exclusions, §1.3 reporting)
  - A2 §1.5.1 endpoint_status 7-value set; E-7 no activation after gate
Usage:
  python qa_evidence.py --out-dir DIR --plan PLAN.json [--worker worker_01] [--label E000_FAST] [--state out/seen.json] --report out/QA_X.json
"""
from __future__ import annotations
import argparse, hashlib, json, os, pathlib, re, unicodedata, datetime
from collections import Counter, defaultdict

KST = datetime.timezone(datetime.timedelta(hours=9))
now = lambda: datetime.datetime.now(KST).strftime("%Y-%m-%dT%H:%M:%S+09:00")
HEX64 = re.compile(r"^[0-9a-f]{64}$")
ENDPOINT_7 = {"FUNCTION_ENDPOINT_REACHED", "AUTH_GATE_REACHED", "PAYMENT_GATE_REACHED", "PERSONAL_DATA_REQUIRED", "CAPTCHA", "BLOCKED", "UNRESOLVED"}
J2_TERMINAL = {"FUNCTION_ENDPOINT_REACHED", "AUTH_GATE_REACHED", "PAYMENT_GATE_REACHED", "PERSONAL_DATA_REQUIRED", "CAPTCHA", "BLOCKED"}
L0A_REQUIRED = ("l0a/dom.html", "l0a/ax.json", "l0a/computed_css.json", "l0a/screen_initial.png", "l0a/screen_fullpage.png", "l0a/probe.json")
ARCHETYPES = {"QUERY", "CONTENT_OPEN", "ITEM_DETAIL", "PLACE_LOOKUP", "COMMUNICATION_ENTRY", "FINANCIAL_ACTION_ENTRY", "UTILITY_ENTRY"}
OUTCOME_SET = {"MEASURED", "TRANSPORT_FAILURE", "TIMEOUT", "WAF_BLOCKED", "CAPTCHA", "APP_REDIRECT", "AUTH_GATE", "UNRESOLVED",
               "ACCOUNT_ACTION_BLOCKED", "SKIPPED_RETRY_EXHAUSTED", "PLANNED_NOT_EXECUTED", "TLS_FAILURE"}

class F:  # findings collector
    def __init__(self): self.items = []
    def add(self, sev, code, msg, **ctx): self.items.append({"severity": sev, "code": code, "msg": msg, **ctx})
    def worst(self):
        order = {"C0": 0, "C1": 1, "C2": 2}
        return min((i["severity"] for i in self.items), key=lambda s: order[s], default=None)

def canon(obj) -> bytes:
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")

def sha256_file(p: pathlib.Path) -> tuple[str, int]:
    h = hashlib.sha256(); n = 0
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk); n += len(chunk)
    return h.hexdigest(), n

def obs_id(web_target_id, evidence_run_id, requested_url, protocol_version, collection_started_at) -> str | None:
    vals = [web_target_id, evidence_run_id, requested_url, protocol_version, collection_started_at]
    if any(not isinstance(v, str) or not v.strip() for v in vals): return None
    s = "\x1f".join(unicodedata.normalize("NFC", v).strip() for v in vals)
    return hashlib.sha256(s.encode("utf-8")).hexdigest()[:32]

# ----------------------------------------------------------------------------- manifest / run verification (independent of B)

def verify_run(run_dir: pathlib.Path, f: F, tid: str) -> dict:
    rep = {"run_dir": str(run_dir), "status": None, "entries": 0, "files_checked": 0, "observations": [], "artifacts_by_obs": defaultdict(list), "run_json": None}
    mf = run_dir / "manifest.jsonl"; rj = run_dir / "run.json"
    if not run_dir.is_dir():
        f.add("C1", "RUN_DIR_MISSING", "evidence run dir missing", target_id=tid, run_dir=str(run_dir)); rep["status"] = "FAILED"; return rep
    if not mf.is_file():
        f.add("C1", "MANIFEST_MISSING", "manifest.jsonl missing — run not sealed / invalid (07 §4)", target_id=tid, run_dir=str(run_dir)); rep["status"] = "FAILED"; return rep
    seen = set(); bad = 0
    real_root = os.path.realpath(run_dir)
    for ln, line in enumerate(mf.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip(): continue
        try: e = json.loads(line)
        except Exception: f.add("C1", "MANIFEST_MALFORMED", f"line {ln} not JSON", target_id=tid); bad += 1; continue
        rep["entries"] += 1
        oid, rel, sha, nbytes = e.get("observation_id"), e.get("relpath"), e.get("sha256"), e.get("bytes")
        if not all(isinstance(x, str) for x in (oid, rel, sha)) or not isinstance(nbytes, int):
            f.add("C1", "MANIFEST_FIELDS", f"line {ln} missing/typed fields", target_id=tid); bad += 1; continue
        if not HEX64.match(sha): f.add("C1", "MANIFEST_SHA_FORMAT", f"line {ln} sha256 not lowercase hex64", target_id=tid); bad += 1
        if rel.startswith("/") or ".." in pathlib.PurePosixPath(rel).parts: f.add("C0", "RELPATH_ESCAPE", f"relpath escape {rel}", target_id=tid); bad += 1; continue
        if (oid, rel) in seen: f.add("C1", "MANIFEST_DUP", f"duplicate (observation_id, relpath) {oid}/{rel}", target_id=tid); bad += 1
        seen.add((oid, rel)); rep["artifacts_by_obs"][oid].append(rel)
        # symlink components + realpath containment
        p = run_dir; escaped = False
        for part in pathlib.PurePosixPath(rel).parts:
            p = p / part
            if p.is_symlink(): escaped = True; break
        if escaped or not os.path.realpath(p).startswith(real_root + os.sep):
            f.add("C0", "SYMLINK_ESCAPE", f"symlink/realpath escape {rel}", target_id=tid); bad += 1; continue
        if not p.is_file():
            f.add("C1", "ARTIFACT_MISSING", f"artifact missing {rel}", target_id=tid, observation_id=oid); bad += 1; continue
        got, sz = sha256_file(p); rep["files_checked"] += 1
        if sz == 0: f.add("C1", "ARTIFACT_EMPTY", f"empty file {rel}", target_id=tid); bad += 1
        if sz != nbytes: f.add("C1", "ARTIFACT_SIZE", f"size mismatch {rel}: manifest {nbytes} vs {sz}", target_id=tid); bad += 1
        if got != sha: f.add("C1", "ARTIFACT_HASH", f"sha256 mismatch {rel}", target_id=tid, observation_id=oid); bad += 1
    rep["observations"] = sorted(rep["artifacts_by_obs"])
    if rj.is_file():
        try:
            r = json.loads(rj.read_text(encoding="utf-8")); rep["run_json"] = {k: r.get(k) for k in ("run_id", "execution_mode", "sealed_at", "artifact_count", "provenance")}
            if r.get("artifact_count") is not None and r["artifact_count"] != rep["entries"]:
                f.add("C1", "RUN_ARTIFACT_COUNT", f"run.json artifact_count {r['artifact_count']} != manifest entries {rep['entries']}", target_id=tid)
            if sorted(r.get("observations") or []) != rep["observations"]:
                f.add("C1", "RUN_OBS_SET", "run.json observations != manifest observation set", target_id=tid)
            if r.get("run_id") and r["run_id"] != run_dir.name:
                f.add("C1", "RUN_ID_DIR", f"run.json run_id {r['run_id']} != dir {run_dir.name}", target_id=tid)
        except Exception as ex:
            f.add("C1", "RUN_JSON_BAD", f"run.json unreadable: {ex}", target_id=tid)
    else:
        f.add("C1", "RUN_JSON_MISSING", "run.json missing", target_id=tid)
    rep["status"] = "FAILED" if bad else ("VERIFIED" if rep["files_checked"] == rep["entries"] and rep["entries"] > 0 else "FAILED")
    rep["artifacts_by_obs"] = dict(rep["artifacts_by_obs"])
    return rep

# ----------------------------------------------------------------------------- batch chain

def load_batches(out_dir: pathlib.Path, f: F) -> list[dict]:
    bdir = out_dir / "batches"; chain = out_dir / "BATCH_CHAIN.jsonl"
    batches = []
    for p in sorted(bdir.glob("batch_*.json")) if bdir.is_dir() else []:
        try: m = json.loads(p.read_text(encoding="utf-8"))
        except Exception as ex: f.add("C1", "BATCH_JSON_BAD", f"{p.name}: {ex}"); continue
        m["_file"] = p.name; m["_file_sha256"] = sha256_file(p)[0]
        recomputed = hashlib.sha256(canon({k: v for k, v in m.items() if k != "batch_hash" and not k.startswith("_")})).hexdigest()
        m["_hash_ok"] = (recomputed == m.get("batch_hash"))
        if not m["_hash_ok"]: f.add("C0", "BATCH_HASH_MISMATCH", f"{p.name}: recomputed batch_hash != stored (systemic evidence identity corruption candidate)", file=p.name)
        if set(m.get("target_ids") or []) != {r.get("target_id") for r in m.get("results") or []}:
            f.add("C1", "BATCH_TARGETS_VS_RESULTS", f"{p.name}: target_ids != results target set", file=p.name)
        batches.append(m)
    batches.sort(key=lambda m: m.get("batch_index", 0))
    prev = None
    for m in batches:
        if m.get("previous_batch_hash") != prev:
            f.add("C0", "CHAIN_BROKEN", f"{m['_file']}: previous_batch_hash != prior batch_hash", file=m["_file"])
        prev = m.get("batch_hash")
    if chain.is_file():
        lines = [json.loads(l) for l in chain.read_text(encoding="utf-8").splitlines() if l.strip()]
        by_idx = {m.get("batch_index"): m for m in batches}
        for l in lines:
            m = by_idx.get(l.get("batch_index"))
            if not m: f.add("C1", "CHAIN_ORPHAN", f"BATCH_CHAIN line batch_index {l.get('batch_index')} has no batch file"); continue
            if l.get("batch_hash") != m.get("batch_hash") or l.get("previous_batch_hash") != m.get("previous_batch_hash"):
                f.add("C0", "CHAIN_LINE_MISMATCH", f"BATCH_CHAIN line {l.get('batch_index')} hashes != batch file")
            if l.get("target_count") != len(m.get("target_ids") or []): f.add("C1", "CHAIN_TARGET_COUNT", f"BATCH_CHAIN line {l.get('batch_index')} target_count mismatch")
        if len(lines) != len(batches): f.add("C1", "CHAIN_LEN", f"BATCH_CHAIN has {len(lines)} lines vs {len(batches)} batch files")
    elif batches:
        f.add("C1", "CHAIN_MISSING", "BATCH_CHAIN.jsonl missing while batch files exist")
    return batches

# ----------------------------------------------------------------------------- per-target reconstruction

def _get(d, *keys, default=None):
    for k in keys:
        if isinstance(d, dict) and k in d and d[k] is not None: return d[k]
    return default

def reconstruct_target(res: dict, batch: dict, out_dir: pathlib.Path, f: F, plan_targets: dict) -> dict:
    tid = res.get("target_id"); det = res.get("detail") or {}
    l0 = det.get("l0") if isinstance(det.get("l0"), dict) else (det if "observation_id" in det else {})
    row = {"target_id": tid, "batch_index": batch.get("batch_index"), "batch_id": batch.get("batch_id"), "execution_mode": batch.get("execution_mode"),
           "outcome": res.get("outcome"), "attempts": res.get("attempts"), "error": (res.get("error") or "")[:160], "scout_invoked": det.get("scout_invoked"),
           "canonical_service_key": plan_targets.get(tid, {}).get("canonical_service_key"), "archetype_plan": plan_targets.get(tid, {}).get("interaction_archetype")}
    if row["outcome"] not in OUTCOME_SET: f.add("C1", "OUTCOME_ENUM", f"unknown outcome {row['outcome']}", target_id=tid)
    # L0
    row["observation_id"] = l0.get("observation_id"); row["evidence_run_id"] = l0.get("evidence_run_id"); row["measurement_status"] = l0.get("measurement_status")
    row["requested_url"] = l0.get("requested_url"); row["protocol_version"] = l0.get("protocol_version")
    row["max_overlay_coverage"] = l0.get("max_overlay_coverage"); row["max_primary_action_occlusion"] = l0.get("max_primary_action_occlusion")
    row["primary_action_visible_initial"] = l0.get("primary_action_visible_initial")
    row["blocking_modal_count"] = l0.get("blocking_modal_count", (sum(1 for i in (l0.get("interrupts") or []) if isinstance(i, dict) and i.get("blocks_primary_action") in (1, True, "1")) if l0.get("interrupts") is not None else None))
    row["l0_present"] = bool(l0)
    if l0:
        if l0.get("web_target_id") and l0.get("web_target_id") != tid: f.add("C1", "WEB_TARGET_ID", f"l0.web_target_id {l0.get('web_target_id')} != target_id", target_id=tid)
        if plan_targets.get(tid) and l0.get("requested_url") and plan_targets[tid].get("official_url") and l0.get("requested_url") != plan_targets[tid]["official_url"]:
            f.add("C2" if batch.get("execution_mode") == "FIXTURE" else "C1", "URL_NOT_PLAN", "requested_url != plan official_url", target_id=tid, requested=l0.get("requested_url"), plan=plan_targets[tid]["official_url"])
        run = verify_run(out_dir / "evidence" / str(l0.get("evidence_run_id")), f, tid) if l0.get("evidence_run_id") else {"status": "FAILED"}
        row["run_status"] = run.get("status"); row["run_entries"] = run.get("entries")
        arts = set((run.get("artifacts_by_obs") or {}).get(l0.get("observation_id"), []))
        missing = [a for a in L0A_REQUIRED if f"{l0.get('observation_id')}/{a}" not in arts]
        row["l0a_missing"] = missing
        if missing and row["measurement_status"] == "MEASURED": f.add("C1", "L0A_INCOMPLETE", f"MEASURED but l0a artifacts missing: {missing}", target_id=tid)
        prov = (run.get("run_json") or {}).get("provenance") or {}
        row["run_provenance"] = {k: prov.get(k) for k in ("base_sha", "shadow_lane", "collector_sha", "protocol_sha", "protocol_version", "authoritative", "real_target_measurement", "status") if k in prov}
        row["run_execution_mode"] = (run.get("run_json") or {}).get("execution_mode")
        row["protocol_version"] = l0.get("protocol_version") or prov.get("protocol_version")
        rid = obs_id(l0.get("web_target_id"), l0.get("evidence_run_id"), l0.get("requested_url"), row["protocol_version"], l0.get("collection_started_at"))
        row["observation_id_recomputed_ok"] = (rid == l0.get("observation_id")) if rid else None
        if rid and rid != l0.get("observation_id"): f.add("C0", "OBS_ID_MISMATCH", "observation_id != sha256(5 identity fields)[:32]", target_id=tid, observation_id=l0.get("observation_id"))
        if rid is None: f.add("C2", "OBS_ID_UNCHECKABLE", "identity inputs incomplete (protocol_version missing in l0 and run provenance)", target_id=tid)
        if prov.get("real_target_measurement") is False and batch.get("execution_mode") == "REAL_TARGET": f.add("C1", "PROVENANCE_REAL_FLAG", "REAL_TARGET batch but run provenance real_target_measurement=False", target_id=tid)
    # L1
    tm = det.get("task_manifest") if isinstance(det.get("task_manifest"), dict) else {}
    te = tm or {k: det.get(k) for k in ("endpoint_status", "endpoint_status_detail", "endpoint_reached", "ned", "ied", "mpfed", "archetype", "steps", "auth_gate_before_endpoint", "forced_dismissal_count", "area_signal_status") if k in det}
    row["l1_present"] = bool(te)
    row["endpoint_status"] = te.get("endpoint_status"); row["endpoint_status_detail"] = te.get("endpoint_status_detail")
    er = te.get("endpoint_reached"); row["endpoint_reached"] = (1 if str(er) in ("1", "True", "true") else (0 if er is not None else None))
    row["ned"], row["ied"], row["mpfed"] = te.get("ned"), te.get("ied"), te.get("mpfed")
    row["archetype"] = te.get("archetype") or row["archetype_plan"]; row["forced_dismissal_count"] = te.get("forced_dismissal_count"); row["area_signal_status"] = te.get("area_signal_status")
    row["path_sha256"] = tm.get("path_sha256")
    if te:
        if row["endpoint_status"] not in ENDPOINT_7: f.add("C1", "ENDPOINT_ENUM", f"endpoint_status {row['endpoint_status']} not in 7-value set (A2 E-1)", target_id=tid)
        if row["endpoint_status"] == "FUNCTION_ENDPOINT_REACHED" and row["endpoint_reached"] != 1: f.add("C1", "ENDPOINT_REACHED_FLAG", "FUNCTION_ENDPOINT_REACHED but endpoint_reached != 1", target_id=tid)
        if row["endpoint_status"] != "FUNCTION_ENDPOINT_REACHED" and any(v is not None for v in (row["ned"], row["ied"], row["mpfed"])) and not (row["endpoint_status"] is None):
            # A2 §1.5.1: non-endpoint -> NED/IED/MPFED NULL (allow NED observed w/ IED,MPFED NULL per A1 §1.5 row 3)
            if row["mpfed"] is not None or row["ied"] is not None: f.add("C1", "DEPTH_NOT_NULL", "non-endpoint terminal but IED/MPFED not NULL (A2 §1.5.1)", target_id=tid)
        if None not in (row["ned"], row["ied"], row["mpfed"]) and row["mpfed"] != row["ned"] + row["ied"]:
            f.add("C1", "MPFED_IDENTITY", f"MPFED {row['mpfed']} != NED {row['ned']} + IED {row['ied']}", target_id=tid)
        if row["archetype"] and row["archetype"] not in ARCHETYPES: f.add("C1", "ARCHETYPE_ENUM", f"archetype {row['archetype']} not in 7-value set", target_id=tid)
        if row["archetype_plan"] and row["archetype"] and row["archetype"] != row["archetype_plan"]: f.add("C1", "ARCHETYPE_VS_PLAN", f"archetype {row['archetype']} != frozen plan {row['archetype_plan']}", target_id=tid)
        steps = te.get("steps") or []
        gate_idx = [i for i, s in enumerate(steps) if isinstance(s, dict) and str(s.get("auth_gate_detected")) in ("1", "True", "true")]
        if gate_idx and gate_idx[0] < len(steps) - 1:
            f.add("C0", "ACTIVATION_AFTER_GATE", f"activation(s) recorded after auth gate step {gate_idx[0]} (E-7 forbidden action)", target_id=tid)
        row["n_steps"] = len(steps); row["gate_step_idx"] = gate_idx[:1]
        if row["mpfed"] is not None and steps and row["mpfed"] > len(steps): f.add("C1", "MPFED_GT_STEPS", f"MPFED {row['mpfed']} > recorded steps {len(steps)}", target_id=tid)
    # timeout / transport separation
    if row["outcome"] == "TRANSPORT_FAILURE" and row["error"].startswith("TIMEOUT_EXCEEDED"): row["timeout_cap_exceeded"] = True
    if row["endpoint_status"] == "UNDETERMINED" or row["measurement_status"] == "UNDETERMINED":
        f.add("C1", "UNDET_AS_FAILURE", "collection failure recorded as UNDETERMINED (contract §1.1 separation violated)", target_id=tid)
    # joint-valid J1..J3 (J4 needs KWCAG results → mart stage)
    reason = None
    if not l0 and row["outcome"] not in ("PLANNED_NOT_EXECUTED",):
        f.add("C2", "L0_DETAIL_ABSENT_IN_BATCH", f"outcome {row['outcome']}: batch result carries no L0 record (lineage from batch→evidence run broken; see orphan_runs)", target_id=tid)
    if row["outcome"] == "PLANNED_NOT_EXECUTED": reason = "NOT_EXECUTED"
    elif row["outcome"] == "ACCOUNT_ACTION_BLOCKED": reason = "L1_NOT_ATTEMPTED_OR_UNRESOLVED"
    elif row.get("timeout_cap_exceeded") or row["outcome"] == "TIMEOUT" or row["measurement_status"] == "FAILED_PAGE_TIMEOUT": reason = "TIMEOUT"
    elif row["outcome"] in ("TRANSPORT_FAILURE", "TLS_FAILURE", "SKIPPED_RETRY_EXHAUSTED", "WAF_BLOCKED", "APP_REDIRECT") or row["measurement_status"] not in ("MEASURED",): reason = "TRANSPORT_FAILURE" if row["measurement_status"] != "MEASURED" or row["outcome"] in ("TRANSPORT_FAILURE", "TLS_FAILURE", "SKIPPED_RETRY_EXHAUSTED") else "L0_NOT_MEASURED"
    elif row.get("run_status") != "VERIFIED" or row.get("l0a_missing"): reason = "L0_EVIDENCE_INCOMPLETE"
    elif not row["l1_present"] or row["endpoint_status"] not in J2_TERMINAL: reason = "L1_NOT_ATTEMPTED_OR_UNRESOLVED"
    elif None in (row["ned"], row["ied"], row["mpfed"]):
        reason = "GATE_REACHED_MPFED_NULL" if row["endpoint_status"] in ("AUTH_GATE_REACHED", "PAYMENT_GATE_REACHED", "PERSONAL_DATA_REQUIRED") else "MPFED_NULL"  # contract §1.3 (A 2026-08-27 12:10): 대상의 성질 vs 우리 쪽 사정 분리
    row["j1_j3_valid"] = reason is None; row["exclusion_reason_c"] = reason
    return row

# ----------------------------------------------------------------------------- plan / order / partition / append-only

def check_plan_order(rows: list[dict], plan: dict, worker: str | None, f: F, label: str):
    order = plan.get("frozen_collection_order") or [t.get("canonical_service_key") for t in plan.get("targets") or []]
    assign = ((plan.get("worker_partition") or {}).get("assignments") or {})
    keys = [r["canonical_service_key"] for r in rows if r.get("canonical_service_key")]
    unknown = [r["target_id"] for r in rows if not r.get("canonical_service_key")]
    if unknown: f.add("C1", "TARGET_NOT_IN_PLAN", f"{len(unknown)} result target_ids not in plan targets (outcome-conditioned reselection candidate)", target_ids=unknown[:10])
    dup = [k for k, c in Counter(r["target_id"] for r in rows).items() if c > 1]
    if dup: f.add("C1", "DUPLICATE_TARGET", f"duplicate target attempts across batches: {dup}", target_ids=dup)
    if worker and assign:
        own = assign.get(worker) or []
        foreign = [k for k in keys if k not in own]
        if foreign: f.add("C1", "PARTITION_VIOLATION", f"{worker} collected targets outside its partition: {foreign}", keys=foreign)
        ref = [k for k in own if k in set(keys)]
        # order preserved as subsequence
        it = iter(ref); ok = all(k in it for k in keys)  # keys must appear in ref order
        pos = {k: i for i, k in enumerate(own)}; seq = [pos.get(k, -1) for k in keys]
        if seq != sorted(seq): f.add("C1", "ORDER_VIOLATION", f"{worker} collection order deviates from frozen partition order", observed=keys[:20])
    elif order:
        pos = {k: i for i, k in enumerate(order)}; seq = [pos.get(k, -1) for k in keys]
        if any(s < 0 for s in seq): f.add("C1", "KEY_NOT_IN_ORDER", "target key not in frozen order", keys=[k for k, s in zip(keys, seq) if s < 0])
        if seq != sorted(seq): f.add("C1", "ORDER_VIOLATION", f"{label}: collection order deviates from frozen order", observed=keys)
    return {"frozen_order_n": len(order), "attempted_keys": keys, "partition_worker": worker}

def append_only_check(out_dir: pathlib.Path, batches: list[dict], state_path: pathlib.Path | None, f: F) -> dict:
    cur = {m["_file"]: m["_file_sha256"] for m in batches}
    runs = {}
    ev = out_dir / "evidence"
    if ev.is_dir():
        for rd in ev.iterdir():
            mf = rd / "manifest.jsonl"
            if mf.is_file(): runs[rd.name] = sha256_file(mf)[0]
    rep = {"batch_files": len(cur), "runs": len(runs), "changed_batches": [], "changed_manifests": [], "removed": []}
    if state_path and state_path.is_file():
        old = json.loads(state_path.read_text(encoding="utf-8"))
        for k, v in (old.get("batches") or {}).items():
            if k not in cur: rep["removed"].append(k)
            elif cur[k] != v: rep["changed_batches"].append(k)
        for k, v in (old.get("runs") or {}).items():
            if k not in runs: rep["removed"].append("evidence/" + k)
            elif runs[k] != v: rep["changed_manifests"].append(k)
        if rep["changed_batches"] or rep["changed_manifests"] or rep["removed"]:
            sev = "C0" if (len(rep["changed_batches"]) + len(rep["changed_manifests"]) + len(rep["removed"])) > 1 else "C1"
            f.add(sev, "APPEND_ONLY_VIOLATION", "previously sealed batch/manifest bytes changed or removed", **{k: v for k, v in rep.items() if isinstance(v, list)})
    if state_path:
        state_path.parent.mkdir(parents=True, exist_ok=True)
        state_path.write_text(json.dumps({"checked_at": now(), "batches": cur, "runs": runs}, ensure_ascii=False, indent=2), encoding="utf-8")
    return rep

# ----------------------------------------------------------------------------- main

def run_qa(out_dir: str, plan_path: str, worker: str | None, label: str, state: str | None, extra_plan_targets: str | None = None) -> dict:
    f = F(); out = pathlib.Path(out_dir); plan = json.loads(pathlib.Path(plan_path).read_text(encoding="utf-8"))
    plan_targets = {t["target_id"]: t for t in (plan.get("targets") or []) if isinstance(t, dict) and t.get("target_id")}
    if extra_plan_targets:
        ep = json.loads(pathlib.Path(extra_plan_targets).read_text(encoding="utf-8"))
        for t in ep.get("targets") or []: plan_targets.setdefault(t.get("target_id"), t)
    batches = load_batches(out, f)
    rows = []
    for b in batches:
        if b.get("execution_mode") == "SHADOW_DRY_RUN": f.add("C1", "DRY_RUN_BATCH", f"{b['_file']} is SHADOW_DRY_RUN — not real evidence", file=b["_file"])
        for r in b.get("results") or []: rows.append(reconstruct_target(r, b, out, f, plan_targets))
    plan_rep = check_plan_order(rows, plan, worker, f, label)
    referenced = {r.get("evidence_run_id") for r in rows if r.get("evidence_run_id")}
    ev = out / "evidence"; orphan = sorted(d.name for d in ev.iterdir() if d.is_dir() and d.name not in referenced) if ev.is_dir() else []
    if orphan: f.add("C2", "ORPHAN_EVIDENCE_RUNS", f"{len(orphan)} evidence runs not referenced by any batch result (guard-blocked targets drop their L0 record)", runs=orphan[:20])
    ao = append_only_check(out, batches, pathlib.Path(state) if state else None, f)
    # SHA consistency across runs
    provs = Counter(json.dumps(r.get("run_provenance"), sort_keys=True) for r in rows if r.get("run_provenance"))
    protos = Counter(r.get("protocol_version") for r in rows if r.get("protocol_version"))
    if len(provs) > 1: f.add("C1", "PROVENANCE_DRIFT", f"{len(provs)} distinct run provenance blocks across runs (collector/protocol SHA not constant)", variants=list(provs)[:4])
    if len(protos) > 1: f.add("C1", "PROTOCOL_DRIFT", f"multiple protocol_version values: {dict(protos)}")
    # L0+L1 both on: MEASURED targets must have scout invoked unless guard-blocked
    for r in rows:
        if r["outcome"] == "MEASURED" and r.get("scout_invoked") is False: f.add("C1", "L1_NOT_INVOKED", "MEASURED but scout_invoked=False (L0-only path)", target_id=r["target_id"])
    # summary (contract §1.3)
    attempted = [r for r in rows if r["outcome"] != "PLANNED_NOT_EXECUTED"]
    jv = [r for r in attempted if r["j1_j3_valid"]]
    excl = Counter(r["exclusion_reason_c"] for r in attempted if not r["j1_j3_valid"])
    by_arch = defaultdict(lambda: {"attempted": 0, "j1_j3_valid": 0})
    for r in attempted:
        a = r.get("archetype") or "UNKNOWN"; by_arch[a]["attempted"] += 1; by_arch[a]["j1_j3_valid"] += int(r["j1_j3_valid"])
    outcomes = Counter(r["outcome"] for r in rows)
    sev = f.worst()
    verdict = "MATCH" if sev in (None, "C2") else ("MISMATCH" if sev == "C1" else "SYSTEMIC_HARD_STOP_CANDIDATE")
    return {"artifact": f"QA_{label}", "generated_by": "C", "generated_at": now(), "out_dir": str(out), "plan": plan_path, "worker": worker,
            "verdict": verdict, "severity_max": sev, "n_batches": len(batches), "batch_hash_all_ok": all(b["_hash_ok"] for b in batches) if batches else None,
            "outcomes": dict(outcomes), "attempted_n": len(attempted), "joint_valid_j1_j3_n": len(jv), "j4_pending": "requires fact_criterion_result + frozen older-relevant set",
            "excluded_by_reason": dict(excl), "by_archetype": dict(by_arch), "plan": plan_rep, "append_only": ao,
            "provenance_variants": list(provs), "protocol_versions": dict(protos), "orphan_evidence_runs": orphan,
            "findings": f.items, "rows": rows}

if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--out-dir", required=True); ap.add_argument("--plan", required=True); ap.add_argument("--worker"); ap.add_argument("--label", default="EVIDENCE")
    ap.add_argument("--state"); ap.add_argument("--report"); ap.add_argument("--extra-plan-targets"); a = ap.parse_args()
    rep = run_qa(a.out_dir, a.plan, a.worker, a.label, a.state, a.extra_plan_targets)
    if a.report:
        pathlib.Path(a.report).parent.mkdir(parents=True, exist_ok=True); pathlib.Path(a.report).write_text(json.dumps(rep, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    print(json.dumps({k: rep[k] for k in ("verdict", "severity_max", "n_batches", "attempted_n", "joint_valid_j1_j3_n", "excluded_by_reason", "outcomes")}, ensure_ascii=False))
    for x in rep["findings"][:30]: print(x["severity"], x["code"], x["msg"], x.get("target_id", ""))
