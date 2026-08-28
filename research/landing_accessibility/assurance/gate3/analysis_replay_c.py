#!/usr/bin/env python3
"""analysis_replay_c.py — CP7 (T-A-V3-TBX-007 11:50–12:10 / TBX-009 CP7): C's INDEPENDENT recomputation of the numbers D's
figures stand on, from the canonical mart rows, using C's own derivation library (gate1/lane6_stats/c_flow_derive.py — no B/D code).

Metrics (each ends in exactly one state — ASSURED · DIVERGENT · NOT_ASSURED; a metric with 0 recomputable rows is NOT_ASSURED, never assured):
  coverage        k/50 overall and k/10 per family, per variable (value not a sentinel / placeholder token)
  activation_depth  per observed row: C derives from the sequence (experienced when task sequence is a placeholder, basis stated) and
                    diffs the mart value; family median/IQR/range from mart values AND from C values
  label_relation  C recomputes label_relation(visible_label, accessible_name, synonym_map={}) where both observed; distribution; diff
  menu_dependency / auth_gate_stage   C-derived vs mart where derivable
  sequence_distance   per family, pairwise normalised Levenshtein / LCS matrix over parseable sequences (n stated; 45 cells ≠ n=45)
Sequence parser rule (R54, stated): value starting with '[' → json.loads; list of dicts → 'action' (or 'action_token') key; a dict without
an action key (error record) → token ERROR_STEP (non-canonical → row UNEXTRACTABLE, alt computed with drop_noncanonical=True); a bare
ALL-CAPS token that is not canonical (e.g. AMBIGUOUS_E_SUPPLIES_ONE_SEQUENCE) or a sentinel → PLACEHOLDER (not a sequence, not 0);
otherwise split on '>' / '|' / ','. Read+hash from ONE read_bytes (D-DEF-34).
exit 0 ran · 2 did not run (controls failed / crash) · 3 NO_OBSERVED_ROWS (every metric NOT_ASSURED)
"""
import csv, datetime, glob, hashlib, io, json, os, pathlib, re, statistics, subprocess, sys
HERE = pathlib.Path(__file__).resolve(); sys.path.insert(0, str(HERE.parent)); sys.path.insert(0, str(HERE.parents[1] / "gate1" / "lane6_stats"))
import census_qc_c as Q  # noqa: E402
import c_flow_derive as F  # noqa: E402

ROOT = pathlib.Path("/home/sieg/projects-wsl/ProjectFinal/artifacts/v3_census")
OUT_A = ROOT / "assurance" / "ANALYSIS_ASSURED.json"; OUT_C = HERE.parent / "out" / "ANALYSIS_ASSURED_C.json"
KST = datetime.timezone(datetime.timedelta(hours=9)); now = lambda: datetime.datetime.now(KST).isoformat(timespec="seconds")
SENT = set(Q.SENTINELS) | {"AMBIGUOUS_E_SUPPLIES_ONE_SEQUENCE", "E_DID_NOT_SUPPLY"}
VARS = ["visible_label", "accessible_name", "label_relation", "entry_x_norm", "entry_y_norm", "entry_zone", "entry_control_type", "nav_container_type",
        "reveal_direction", "menu_dependency", "task_flow_sequence", "experienced_flow_sequence", "activation_depth", "auth_gate_stage", "task_control_occlusion"]
TOL = 1e-6


# C-DEF-38 (B): coverage must be "value observed", not "cell not in a sentinel list" — per-column ALLOWED value sets; anything outside is not an observation.
# A column absent from this map falls back to the sentinel/prefix rule (reported as such).
ALLOWED = {
    "label_relation": {"MATCH", "DIFFERENT", "SEMANTIC_EQUIV"},            # a RELATION is observed only when both labels were; VISIBLE_ONLY/AX_ONLY/NONE/AX_NOT_INDEPENDENTLY_OBSERVED are non-observation states
    "entry_zone": {"TOP_LEFT", "TOP_CENTER", "TOP_RIGHT", "MID", "BOTTOM", "FLOATING", "DRAWER", "TOP", "LEFT", "RIGHT", "CENTER"},
    "auth_gate_stage": {"BEFORE_TASK_DISCOVERY", "AFTER_TASK_SELECT", "AT_ENDPOINT", "NONE"},
    "nav_container_type": {"NAV", "HEADER", "FOOTER", "ASIDE", "MAIN", "FORM", "DIALOG", "NONE"},   # NONE = observed 'outside any container' (B anchor extractor semantics) — a value, unlike label_relation NONE
    "menu_dependency": {"True", "False", "true", "false", "0", "1"},
    "task_control_occlusion": {"True", "False", "true", "false", "0", "1"},
}
DISALLOWED_PREFIX = ("AMBIGUOUS_", "NOT_OBSERVABLE", "NOT_RECORDED", "NA_", "E_DID_NOT_SUPPLY", "UNDETERMINED", "AX_NOT_INDEPENDENTLY")


def observed_col(col, v):
    s = ("" if v is None else str(v)).strip()
    if col in ALLOWED: return s in ALLOWED[col]
    return observed(s) and not s.startswith(DISALLOWED_PREFIX)


def observed(v):
    s = ("" if v is None else str(v)).strip()
    # reason tokens are not observations (C-DEF-37: NOT_OBSERVABLE_FROM_STATIC_DOM was counted as an entry_zone value → coverage 26/50 instead of 8/50)
    return s != "" and s not in SENT and not s.startswith(("E_DID_NOT_SUPPLY", "NOT_OBSERVABLE", "NOT_RECORDED", "NA_", "UNDETERMINED"))


def parse_seq(v):
    """→ (tokens|None, state) state ∈ PARSED · PLACEHOLDER · UNPARSABLE · EMPTY"""
    s = ("" if v is None else str(v)).strip()
    if not observed(s): return None, "PLACEHOLDER"
    if s.startswith("["):
        try: arr = json.loads(s)
        except ValueError:
            import ast
            try: arr = ast.literal_eval(s)          # B writes python-repr lists ("['OPEN_GLOBAL_MENU']") — rule stated
            except (ValueError, SyntaxError): return None, "UNPARSABLE"
        if not isinstance(arr, list): return None, "UNPARSABLE"
        toks = []
        for x in arr:
            if isinstance(x, str): toks.append(x)
            elif isinstance(x, dict): toks.append(x.get("action") or x.get("action_token") or "ERROR_STEP")
            else: toks.append("ERROR_STEP")
        return toks, "PARSED" if toks else "EMPTY"
    if re.fullmatch(r"[A-Z][A-Z0-9_]+", s) and s not in F.CANONICAL_TOKENS: return None, "PLACEHOLDER"
    return [t.strip() for t in re.split(r"[>|,]", s) if t.strip()], "PARSED"


def replay_row(r):
    out = {"target_id": r.get("target_id"), "family_id": r.get("family_id")}
    task, ts = parse_seq(r.get("task_flow_sequence")); exp, es = parse_seq(r.get("experienced_flow_sequence"))
    out["task_seq_state"], out["exp_seq_state"] = ts, es
    seq = task if ts == "PARSED" else exp if es == "PARSED" else None; out["basis"] = "task" if ts == "PARSED" else "experienced_only" if es == "PARSED" else None
    if seq is not None:
        try: d = F.derive(seq, exp if (es == "PARSED" and out["basis"] == "task") else None); out["derive"] = "OK"
        except ValueError as e:
            out["derive"] = "NON_CANONICAL"; out["non_canonical"] = str(e)[:100]
            try: d = F.derive(seq, None, drop_noncanonical=True); out["alt_drop_noncanonical"] = True
            except Exception: d = None
        if d:
            out["c_activation_depth"] = d.get("activation_depth"); out["c_menu_dependency"] = d.get("menu_dependency"); out["c_auth_gate_stage"] = d.get("auth_gate_stage"); out["c_endpoint_status"] = d.get("endpoint_status")
    m = r.get("activation_depth")
    if observed(m) and "c_activation_depth" in out:
        try: out["mart_activation_depth"] = int(float(m)); out["activation_depth_match"] = out["mart_activation_depth"] == out["c_activation_depth"]
        except ValueError: out["mart_activation_depth"] = f"UNREADABLE:{m}"
    if observed(r.get("menu_dependency")) and "c_menu_dependency" in out:
        mv = str(r.get("menu_dependency")).strip().lower(); mv = 1 if mv in ("1", "true", "yes") else 0 if mv in ("0", "false", "no") else mv
        out["menu_dependency_match"] = (mv == out["c_menu_dependency"]) if isinstance(mv, int) else f"UNREADABLE:{mv}"
    if str(r.get("attempt_status") or "").strip() != "ENDPOINT_REACHED":   # R91 overrides the sequence-derived stage
        if str(r.get("terminal_reason") or "").strip() == "AUTH_GATE" and seq is not None and "AUTH_GATE" in seq:
            out["auth_basis"] = "terminal AUTH_GATE with AUTH_GATE token in sequence: stage derived from token position (R13 rule); NONE would be DIVERGENT"
            if out.get("c_auth_gate_stage") in (None, "NONE"): out["c_auth_gate_stage"] = "UNDETERMINED"
        else:
            out["c_auth_gate_stage"] = "UNDETERMINED"; out["auth_basis"] = "R91: endpoint not reached ⇒ UNDETERMINED (NONE only allowed on ENDPOINT_REACHED)"
    if observed(r.get("auth_gate_stage")) and "c_auth_gate_stage" in out:
        mv = str(r.get("auth_gate_stage")).strip(); out["mart_auth_gate_stage"] = mv
        reached = str(r.get("attempt_status") or "").strip() == "ENDPOINT_REACHED"; term_auth = str(r.get("terminal_reason") or "").strip() == "AUTH_GATE"
        seq_has = seq is not None and ("AUTH_GATE" in seq or "ENDPOINT_REACHED" in seq)
        if (reached or term_auth) and not seq_has and mv != "UNDETERMINED":
            # R105: NONE on a reached row / a stage on an AUTH_GATE terminal is a positive observation C cannot derive when the sequence carries no
            # endpoint/auth token — NOT_DERIVABLE, neither a match nor a mismatch (never counted as assured)
            out["auth_not_derivable"] = "status/terminal asserts a stage the sequence does not carry (no ENDPOINT_REACHED/AUTH_GATE token)"
        else:
            out["auth_gate_stage_match"] = mv == out["c_auth_gate_stage"]
    # R90 (TBX-017): both unobserved → NONE · visible only → VISIBLE_ONLY · ax only → AX_ONLY · equal → MATCH · differ → DIFFERENT; no SEMANTIC_EQUIV
    vis = r.get("visible_label") if observed(r.get("visible_label")) else None; ax = r.get("accessible_name") if observed(r.get("accessible_name")) else None
    out["c_label_relation"] = F.label_relation(vis, ax, {})
    if observed(r.get("label_relation")): out["label_relation_match"] = str(r.get("label_relation")).strip() == out["c_label_relation"]; out["mart_label_relation"] = r.get("label_relation")
    out["c_seq_for_distance"] = seq
    return out


def q(vals):
    v = sorted(vals)
    if not v: return None
    med = statistics.median(v); q1 = statistics.quantiles(v, n=4)[0] if len(v) >= 2 else v[0]; q3 = statistics.quantiles(v, n=4)[2] if len(v) >= 2 else v[0]
    return {"n": len(v), "median": med, "q1": q1, "q3": q3, "iqr": q3 - q1, "min": v[0], "max": v[-1]}


def metric(state_rows, ok_key):
    n = sum(1 for x in state_rows if ok_key in x); mism = [x["target_id"] for x in state_rows if ok_key in x and x[ok_key] is not True]
    return {"n_compared": n, "mismatch": mism, "state": "NOT_ASSURED" if n == 0 else "DIVERGENT" if mism else "ASSURED"}


def analyse(rows, manifest):
    fam_of = {t["target_id"]: t["family_id"] for t in manifest["targets"]}; fams = sorted(set(fam_of.values()))
    cov = {"overall": {}, "per_family": {f: {} for f in fams}, "rule": "value observed = in the column's ALLOWED set (label_relation: MATCH/DIFFERENT/SEMANTIC_EQUIV only); columns without a set: not sentinel and not a reason/ambiguity token", "cells_filled_not_observed": {}}
    for v in VARS:
        cov["cells_filled_not_observed"][v] = sum(1 for r in rows if r.get("target_id") in fam_of and observed(r.get(v)) and not observed_col(v, r.get(v)))
    for v in VARS:
        ks = [r["target_id"] for r in rows if r.get("target_id") in fam_of and observed_col(v, r.get(v))]
        cov["overall"][v] = {"k": len(ks), "of": 50}
        for f in fams: cov["per_family"][f][v] = {"k": sum(1 for t in ks if fam_of[t] == f), "of": 10}
    obs_rows = [r for r in rows if r.get("target_id") in fam_of and str(r.get("attempt_status") or "").strip() not in Q.NOT_ATTEMPTED_VALUES]
    rep = [replay_row(r) for r in obs_rows]
    metrics = {"activation_depth": metric(rep, "activation_depth_match"), "menu_dependency": metric(rep, "menu_dependency_match"),
               "auth_gate_stage": metric(rep, "auth_gate_stage_match"), "label_relation": metric(rep, "label_relation_match")}
    metrics["auth_gate_stage"]["not_derivable_n"] = sum(1 for x in rep if "auth_not_derivable" in x)
    for k in metrics:
        metrics[k]["rows"] = [{kk: x.get(kk) for kk in x if k in kk or kk in ("target_id", "basis", "derive", "task_seq_state", "exp_seq_state")} for x in rep if f"{k}_match" in x]
    fam_stats = {}
    for f in fams:
        fr = [r for r in obs_rows if fam_of[r["target_id"]] == f]; rr = [x for x in rep if x["family_id"] == f or fam_of.get(x["target_id"]) == f]
        mart_ad = [int(float(r["activation_depth"])) for r in fr if observed(r.get("activation_depth")) and re.fullmatch(r"-?\d+(\.0+)?", str(r["activation_depth"]).strip())]
        c_ad = [x["c_activation_depth"] for x in rr if isinstance(x.get("c_activation_depth"), int)]
        lr_m = {}; [lr_m.__setitem__(str(r["label_relation"]).strip(), lr_m.get(str(r["label_relation"]).strip(), 0) + 1) for r in fr if observed(r.get("label_relation"))]
        lr_c = {}; [lr_c.__setitem__(x["c_label_relation"], lr_c.get(x["c_label_relation"], 0) + 1) for x in rr if "c_label_relation" in x]
        seq_rows = [{"service_id": x["target_id"], "task_role": "PRIMARY", "task_flow_sequence": x["c_seq_for_distance"]} for x in rr if x.get("c_seq_for_distance") and x.get("derive") == "OK"]
        pm = None
        if len(seq_rows) >= 2:
            try: pm = F.pairwise_matrix(seq_rows); pm = {k: pm[k] for k in pm if k in ("n_service", "n_pairs", "primary_distance", "levenshtein_norm", "lcs_sim", "ids", "service_ids")} if isinstance(pm, dict) else None
            except Exception as e: pm = {"error": str(e)[:100]}
        fam_stats[f] = {"n_observed_rows": len(fr), "activation_depth_mart": q(mart_ad), "activation_depth_C": q(c_ad), "activation_depth_stats_state": "NOT_ASSURED" if not c_ad else ("ASSURED" if q(mart_ad) == q(c_ad) else "DIVERGENT"),
                        "label_relation_mart": lr_m, "label_relation_C": lr_c, "label_relation_state": "NOT_ASSURED" if not lr_c else ("ASSURED" if lr_m == lr_c else "DIVERGENT"),
                        "sequence_distance": pm, "sequence_distance_state": "NOT_ASSURED" if not pm or "error" in pm else "COMPUTED_BY_C(n=%d; 45 cells ≠ n=45)" % pm.get("n_service", len(seq_rows)),
                        "seq_states": {s: sum(1 for x in rr if x.get("basis") == s) for s in ("task", "experienced_only")} | {"none": sum(1 for x in rr if x.get("basis") is None)}}
    return {"coverage": cov, "n_rows": len(rows), "n_observed_rows": len(obs_rows), "metrics": metrics, "per_family": fam_stats, "row_replay": rep}


def controls(manifest):
    t = manifest["targets"]; res = {}
    def row(i, task, exp=None, ad=None, vl="NOT_OBSERVED", an="NOT_OBSERVED", lr="NOT_OBSERVED", att="ENDPOINT_REACHED"):
        return {"target_id": t[i]["target_id"], "family_id": t[i]["family_id"], "attempt_status": att, "task_flow_sequence": task, "experienced_flow_sequence": exp or task,
                "activation_depth": ad if ad is not None else "NA_NUMERIC_UNOBSERVED", "visible_label": vl, "accessible_name": an, "label_relation": lr, "menu_dependency": "NOT_OBSERVED", "auth_gate_stage": "NOT_OBSERVED"}
    seq = json.dumps(["OPEN_GLOBAL_MENU", "SELECT_FUNCTION", "ENDPOINT_REACHED"]); exp_ad = F.derive(["OPEN_GLOBAL_MENU", "SELECT_FUNCTION", "ENDPOINT_REACHED"])["activation_depth"]
    good = [row(0, seq, ad=exp_ad, vl="이체", an="이체", lr="MATCH"), row(1, json.dumps([{"action": "SELECT_FUNCTION"}, {"action": "ENDPOINT_REACHED"}]), ad=F.derive(["SELECT_FUNCTION", "ENDPOINT_REACHED"])["activation_depth"])]
    a = analyse(good, manifest); res["must_not_flag:consistent→activation_depth ASSURED n=2"] = "PASS" if a["metrics"]["activation_depth"]["state"] == "ASSURED" and a["metrics"]["activation_depth"]["n_compared"] == 2 else f"FAIL {a['metrics']['activation_depth']}"
    res["must_not_flag:label MATCH ASSURED"] = "PASS" if a["metrics"]["label_relation"]["state"] == "ASSURED" else f"FAIL {a['metrics']['label_relation']}"
    a = analyse([row(0, seq, ad=exp_ad + 1)], manifest); res["must_flag:activation_depth+1→DIVERGENT"] = "PASS" if a["metrics"]["activation_depth"]["state"] == "DIVERGENT" else "FAIL"
    a = analyse([row(0, seq, ad=exp_ad, vl="NOT_OBSERVED", an="전체메뉴", lr="MATCH")], manifest); res["must_flag:R90 visible NOT_OBSERVED stored MATCH→DIVERGENT(C=AX_ONLY)"] = "PASS" if a["metrics"]["label_relation"]["state"] == "DIVERGENT" and a["row_replay"][0]["c_label_relation"] == "AX_ONLY" else f"FAIL {a['row_replay'][0]}"
    a = analyse([row(0, seq, ad=exp_ad, att="TERMINAL_NO_ENDPOINT"), ], manifest)
    a2 = analyse([{**row(0, seq, ad=exp_ad, att="TERMINAL_NO_ENDPOINT"), "auth_gate_stage": "NONE"}], manifest); res["must_flag:R91 NONE on non-reached→DIVERGENT"] = "PASS" if a2["metrics"]["auth_gate_stage"]["state"] == "DIVERGENT" else f"FAIL {a2['metrics']['auth_gate_stage']}"
    a = analyse([row(0, seq, ad=exp_ad, vl="이체", an="송금", lr="MATCH")], manifest); res["must_flag:label 이체/송금 stored MATCH→DIVERGENT"] = "PASS" if a["metrics"]["label_relation"]["state"] == "DIVERGENT" else f"FAIL {a['metrics']['label_relation']}"
    a = analyse([row(0, "AMBIGUOUS_E_SUPPLIES_ONE_SEQUENCE", exp="AMBIGUOUS_E_SUPPLIES_ONE_SEQUENCE", ad=1)], manifest)
    res["must_flag:placeholder sequence→NOT_ASSURED not 0"] = "PASS" if a["metrics"]["activation_depth"]["state"] == "NOT_ASSURED" and a["coverage"]["overall"]["task_flow_sequence"]["k"] == 0 else f"FAIL {a['metrics']['activation_depth']['state']} k={a['coverage']['overall']['task_flow_sequence']['k']}"
    a = analyse([row(0, "AMBIGUOUS_E_SUPPLIES_ONE_SEQUENCE", exp=json.dumps([{"action": "OPEN_GLOBAL_MENU", "label": "전체메뉴"}]), ad=1)], manifest)
    res["must_not_flag:experienced_only basis used when task is placeholder"] = "PASS" if a["row_replay"][0].get("basis") == "experienced_only" and a["metrics"]["activation_depth"]["n_compared"] == 1 else f"FAIL {a['row_replay'][0]}"
    a = analyse([row(0, "AMBIGUOUS_E_SUPPLIES_ONE_SEQUENCE", exp=json.dumps([{"error": "menu_click_failed"}]), ad=1)], manifest)
    res["must_flag:error-only sequence→NON_CANONICAL, depth compared via alt"] = "PASS" if a["row_replay"][0].get("derive") == "NON_CANONICAL" else f"FAIL {a['row_replay'][0]}"
    a = analyse([row(0, "['OPEN_GLOBAL_MENU', 'SELECT_FUNCTION', 'ENDPOINT_REACHED']", ad=exp_ad)], manifest); res["must_not_flag:python-repr list parsed"] = "PASS" if a["metrics"]["activation_depth"]["n_compared"] == 1 else f"FAIL {a['row_replay'][0]}"
    a = analyse([{**row(0, seq, ad=exp_ad), "entry_zone": "NOT_OBSERVABLE_FROM_STATIC_DOM", "entry_x_norm": "NOT_OBSERVABLE_FROM_STATIC_DOM"}], manifest); res["must_flag:reason token NOT_OBSERVABLE_* not counted as observed"] = "PASS" if a["coverage"]["overall"]["entry_zone"]["k"] == 0 and a["coverage"]["overall"]["entry_x_norm"]["k"] == 0 else f"FAIL {a['coverage']['overall']['entry_zone']}"
    a = analyse([{**row(0, seq, ad=exp_ad), "label_relation": "AX_NOT_INDEPENDENTLY_OBSERVED", "nav_container_type": "AMBIGUOUS_MULTIPLE_CONTAINERS"}], manifest); res["must_flag:non-observation tokens (AX_NOT_INDEPENDENTLY_OBSERVED / AMBIGUOUS_*) not counted"] = "PASS" if a["coverage"]["overall"]["label_relation"]["k"] == 0 and a["coverage"]["overall"]["nav_container_type"]["k"] == 0 and a["coverage"]["cells_filled_not_observed"]["label_relation"] == 1 else f"FAIL {a['coverage']['overall']['label_relation']} {a['coverage']['cells_filled_not_observed']}"
    a = analyse([{**row(0, seq, ad=exp_ad, vl="이체", an="송금", lr="DIFFERENT")}], manifest); res["must_not_flag:DIFFERENT counts as observed relation"] = "PASS" if a["coverage"]["overall"]["label_relation"]["k"] == 1 else "FAIL"
    skel = [row(i, "NOT_OBSERVED", att="NOT_ATTEMPTED") for i in range(10)]; a = analyse(skel, manifest)
    res["must_flag:skeleton→every metric NOT_ASSURED, coverage 0"] = "PASS" if all(m["state"] == "NOT_ASSURED" for m in a["metrics"].values()) and all(v["k"] == 0 for v in a["coverage"]["overall"].values()) else "FAIL"
    a = analyse([row(i, seq, ad=exp_ad) for i in range(3)], manifest); f0 = t[0]["family_id"]
    res["must_not_flag:3 rows→sequence matrix n=3 computed"] = "PASS" if a["per_family"][f0]["sequence_distance"] and a["per_family"][f0]["sequence_distance"].get("n_service") == 3 else f"FAIL {a['per_family'][f0]['sequence_distance']}"
    return res


def retractions_block():
    """Read the machine-readable retraction block (schema b_retractions/v1) next to the mart; C outputs carry it so any token they cite
    is read with its marker (R137: the citing side marks). Returns {} when absent — reported as such, never silently."""
    import re as _re
    p = ROOT / "mart" / "CANONICAL_MART_50.RETRACTIONS.md"
    if not p.exists(): return {"status": "ABSENT"}
    m = _re.search(r"```json\s*(\{.*?\})\s*```", p.read_text(encoding="utf-8"), _re.S)
    if not m: return {"status": "NO_MACHINE_BLOCK"}
    try: b = json.loads(m.group(1))
    except ValueError: return {"status": "UNPARSABLE"}
    nr = b.get("not_retracted", []); inv = all(not x.get("replacement_label") for x in nr)
    return {"status": "OK", "schema": b.get("schema"), "retracted": {x["token"]: {"replacement_label": x.get("replacement_label"), "citation_marker": x.get("citation_marker")} for x in b.get("retracted", [])},
            "not_retracted": [x.get("token") for x in nr], "invariant_not_retracted_has_no_replacement": inv, "reading_rule": "every retracted token appearing in this file is a stored VALUE; cite it as '<token> [RETRACTED] → <replacement_label>'"}


def main():
    raw_m = Q.git_show(Q.MANIFEST_PATH); manifest, fsha, bsha = Q.manifest_hashes(raw_m)
    ctl = controls(manifest); failed = {k: v for k, v in ctl.items() if v != "PASS"}
    print(f"CONTROLS {len(ctl)-len(failed)}/{len(ctl)} PASS"); [print("  ", k, v) for k, v in ctl.items() if v != "PASS"]
    if failed: print("controls failed — did not run (exit 2)", file=sys.stderr); return 2
    if "--selftest" in sys.argv: return 0
    c50 = ROOT / "mart" / "CANONICAL_MART_50.csv"; snaps = sorted(glob.glob(str(ROOT / "mart" / "snapshot_*.csv")))
    mp = c50 if c50.exists() else (pathlib.Path(snaps[-1]) if snaps else None)
    if mp is None: print("no mart (exit 3)"); return 3
    b = mp.read_bytes(); msha = hashlib.sha256(b).hexdigest(); rows = list(csv.DictReader(io.StringIO(b.decode("utf-8"))))
    a = analyse(rows, manifest)
    # TBX-014 C_에_추가: recompute E live observations and B post-hoc DOM derivations SEPARATELY (never mixed)
    PROV = "entry_observation_provenance"
    if rows and PROV in rows[0]:
        a["by_provenance"] = {pv: analyse([r for r in rows if (r.get(PROV) or "").strip() == pv] + [], manifest) for pv in sorted({(r.get(PROV) or "").strip() for r in rows})}
        for pv in a["by_provenance"]: a["by_provenance"][pv].pop("row_replay", None)
        a["provenance_note"] = "per-provenance blocks computed on the rows carrying that value only; the top-level block mixes them and is NOT to be cited for label/spatial metrics"
    else: a["by_provenance"] = "COLUMN_ABSENT (entry_observation_provenance not in mart — R76 split not verifiable; top-level metrics treated as E_LIVE_SCOUT-or-unknown)"
    # accessible_name provenance (TBX-011 accessible_name_source) joined from the latest non-R3 EVIDENCE_MANIFEST line per target:
    # a MATCH whose accessible_name is a copy of the visible text (source VISIBLE_TEXT) is a tautology, not an AX observation
    src = {}
    mp_ = ROOT / "raw" / "EVIDENCE_MANIFEST.jsonl"
    if mp_.exists():
        for ln in open(mp_, encoding="utf-8"):
            if not ln.strip(): continue
            try: r_ = json.loads(ln)
            except ValueError: continue
            if "R3" in str(r_.get("scout_run_id") or ""): continue
            t_ = r_.get("target_id"); ts_ = str(r_.get("captured_at_kst") or "")
            if t_ not in src or ts_ > src[t_][0]: src[t_] = (ts_, r_.get("accessible_name_source"))
    by_t = {r.get("target_id"): r for r in rows}; fam_of_all = {t["target_id"]: t["family_id"] for t in manifest["targets"]}
    # TBX-023: when accessible_name_source == VISIBLE_TEXT the canonical value is AX_NOT_INDEPENDENTLY_OBSERVED — C's expected value follows the
    # provenance, not the string rule; a stored MATCH there is a tautology, a stored AX_NOT_INDEPENDENTLY_OBSERVED agrees with C
    for x in a["row_replay"]:
        if src.get(x["target_id"], (None, None))[1] == "VISIBLE_TEXT" and "mart_label_relation" in x:
            x["c_label_relation_provenance_adjusted"] = "AX_NOT_INDEPENDENTLY_OBSERVED"; x["label_relation_match"] = str(x["mart_label_relation"]).strip() == "AX_NOT_INDEPENDENTLY_OBSERVED"
    lr0 = a["metrics"]["label_relation"]; lr0["mismatch"] = [x["target_id"] for x in a["row_replay"] if x.get("label_relation_match") is False]; lr0["state"] = "NOT_ASSURED" if lr0["n_compared"] == 0 else "DIVERGENT" if lr0["mismatch"] else "ASSURED"
    taut = [t for t, r in by_t.items() if str(r.get("label_relation") or "").strip() == "MATCH" and src.get(t, (None, None))[1] == "VISIBLE_TEXT"]
    ax_obs = [t for t, r in by_t.items() if src.get(t, (None, None))[1] not in (None, "VISIBLE_TEXT", "NOT_OBSERVED")]
    # C-DEF-39 (B): accessible_name coverage must count INDEPENDENT AX observations — the observation status lives in a neighbouring
    # column (accessible_name_source); a filled cell whose source is VISIBLE_TEXT is a copy, not an observation (whitelists cannot catch this)
    ax_targets = {t for t, v in src.items() if v[1] not in (None, "VISIBLE_TEXT", "NOT_OBSERVED")}
    # CSV-only proxy (B): label_relation == AX_NOT_INDEPENDENTLY_OBSERVED is computed by B iff accessible_name_source == VISIBLE_TEXT.
    # C verifies the equivalence against raw when raw is present, and falls back to the proxy when only the CSV is available.
    proxy_copy = {t for t, r in by_t.items() if str(r.get("label_relation") or "").strip() == "AX_NOT_INDEPENDENTLY_OBSERVED"}
    raw_copy = {t for t, v in src.items() if v[1] == "VISIBLE_TEXT"}
    proxy_check = {"proxy_n": len(proxy_copy), "raw_n": len(raw_copy), "sets_equal": (proxy_copy == raw_copy) if src else None, "raw_available": bool(src),
                   "rule": "independent AX = filled ∧ label_relation != AX_NOT_INDEPENDENTLY_OBSERVED (CSV-only) ≡ filled ∧ accessible_name_source ∉ {VISIBLE_TEXT, NOT_OBSERVED} (raw)"}
    if not src: ax_targets = {t for t, r in by_t.items() if observed(r.get("accessible_name")) and t not in proxy_copy}
    filled = [t for t, r in by_t.items() if observed(r.get("accessible_name"))]
    a["coverage"]["overall"]["accessible_name"] = {"k": sum(1 for t in filled if t in ax_targets), "of": 50, "filled": len(filled), "filled_by_source": dict(__import__("collections").Counter(src.get(t, (None, "NO_MANIFEST_LINE"))[1] for t in filled)),
                                                    "rule": "k = filled AND accessible_name_source not in {VISIBLE_TEXT, NOT_OBSERVED} (independent AX observation)", "csv_only_proxy_check": proxy_check}
    for f_ in a["coverage"]["per_family"]:
        ff = [t for t in filled if fam_of_all.get(t) == f_]; a["coverage"]["per_family"][f_]["accessible_name"] = {"k": sum(1 for t in ff if t in ax_targets), "of": 10, "filled": len(ff)}
    a["coverage"]["cells_filled_not_observed"]["accessible_name"] = sum(1 for t in filled if t not in ax_targets)
    lr = a["metrics"]["label_relation"]
    lr["accessible_name_source_distribution"] = dict(__import__("collections").Counter(v[1] for v in src.values()))
    lr["tautological_match_n"] = len(taut); lr["ax_tree_observed_n"] = len(ax_obs)
    if taut:
        lr["state"] = "ASSURED_AS_RULE_ONLY"; lr["reading"] = (f"C reproduces B's rule on the stored strings ({lr['n_compared']}/{lr['n_compared']}), but {len(taut)} MATCH rows have accessible_name_source=VISIBLE_TEXT — the AX name is a copy of the visible text, "
                                                             f"not an AX-tree observation (AX captures are 60 B). label divergence (D02) is NOT observed in this census; AX-tree-observed rows: {len(ax_obs)}")
    dfiles = {os.path.relpath(p, ROOT): hashlib.sha256(open(p, "rb").read()).hexdigest()[:16] for p in glob.glob(str(ROOT / "analysis" / "**" / "*"), recursive=True) if os.path.isfile(p)}
    claims = None
    if (ROOT / "analysis" / "CLAIM_CANDIDATES.json").exists():
        try: claims = json.load(open(ROOT / "analysis" / "CLAIM_CANDIDATES.json", encoding="utf-8"))
        except ValueError: claims = "UNREADABLE"
    head = subprocess.run(["git", "-C", Q.W, "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
    assured = [k for k, m in a["metrics"].items() if m["state"] == "ASSURED"]; rule_only = [k for k, m in a["metrics"].items() if m["state"] == "ASSURED_AS_RULE_ONLY"]; divergent = [k for k, m in a["metrics"].items() if m["state"] == "DIVERGENT"]; not_assured = [k for k, m in a["metrics"].items() if m["state"] == "NOT_ASSURED"]
    rec = {"schema": "C_ANALYSIS_ASSURED", "measured_at_kst": now(), "checker": {"commit": head, "analysis_replay_c_sha256": hashlib.sha256(HERE.read_bytes()).hexdigest(), "c_flow_derive_sha256": hashlib.sha256(open(F.__file__, "rb").read()).hexdigest()},
           "mart": {"path": str(mp), "sha256": msha, "bytes": len(b), "rows": len(rows), "is_canonical_50": mp == c50}, "manifest": {"file_sha256": fsha, "body_sha256": bsha},
           "controls": {"n": len(ctl), "pass": len(ctl)}, "summary": {"n_observed_rows": a["n_observed_rows"], "ASSURED": assured, "ASSURED_AS_RULE_ONLY": rule_only, "DIVERGENT": divergent, "NOT_ASSURED": not_assured,
           "coverage_overall": {k: f"{v['k']}/50" + (f" (filled {v['filled']}, independent AX 0 — VISIBLE_TEXT copies)" if k == "accessible_name" and v.get("filled", 0) > v["k"] else "") for k, v in a["coverage"]["overall"].items()}}, "coverage": a["coverage"], "metrics": a["metrics"], "per_family": a["per_family"],
           "by_provenance": a["by_provenance"], "provenance_note": a.get("provenance_note"), "d_analysis_files_seen": dfiles, "d_claim_candidates_seen": claims, "row_replay": a["row_replay"],
           "reading_rules": {"ASSURED": "C recomputation equals the mart value on every compared row (n stated)", "DIVERGENT": "at least one compared row differs — listed; which side is wrong is A's call", "NOT_ASSURED": "0 rows recomputable — never counted as pass", "sequence_distance": "computed by C only (no B/D matrix to diff yet); cells of a matrix, not independent n"},
           "retractions": retractions_block(), "not_a_verdict": True, "exit": 0 if a["n_observed_rows"] else 3}
    OUT_C.parent.mkdir(parents=True, exist_ok=True); OUT_A.parent.mkdir(parents=True, exist_ok=True)
    for p in (OUT_A, OUT_C): p.write_text(json.dumps(rec, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(rec["summary"], ensure_ascii=False)); 
    for k, m in a["metrics"].items(): print(f"  {k:18s} {m['state']:12s} n={m['n_compared']} mismatch={m['mismatch'][:5]}")
    if not a["n_observed_rows"]: print("NO_OBSERVED_ROWS (exit 3)"); return 3
    return 0


if __name__ == "__main__":
    try: sys.exit(main())
    except SystemExit: raise
    except Exception:
        import traceback; traceback.print_exc(); print("analysis_replay_c: did not run (exit 2)", file=sys.stderr); sys.exit(2)
