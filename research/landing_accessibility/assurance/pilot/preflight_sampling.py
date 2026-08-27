#!/usr/bin/env python3
"""C preflight (T-A-PILOT-ASSURE-001): reproduce DIAGNOSTIC_PILOT_MANIFEST selection from non-label inputs only.
Inputs: frame CSV @2281c85 (git show), E001 mart + stored dom.html (evidence class), seed. NO split file, NO LABELS_FROZEN.
"""
import csv, io, json, hashlib, subprocess, glob, pathlib, collections, sys
ROOT = "/home/sieg/projects-wsl/ProjectFinal"
FRAME_SHA = "2281c853950d0c475c5d2c1678680b971c2804f4"
CTRL_SHA = sys.argv[1] if len(sys.argv) > 1 else "9a9197ffd6"
SEED = "LA-DIAG-PILOT-2026-08-27-V2"
def gshow(sha, path): return subprocess.check_output(["git", "-C", ROOT, "show", f"{sha}:{path}"])
frame_raw = gshow(FRAME_SHA, "research/landing_accessibility/shadow/lane_b/state/representative_task_candidate_shadow.csv")
rows = list(csv.DictReader(io.StringIO(frame_raw.decode("utf-8-sig"))))
cand = [r for r in rows if r["mapping_status"] == "CANDIDATE"]
man_raw = gshow(CTRL_SHA, "research/landing_accessibility/control/pilot/DIAGNOSTIC_PILOT_MANIFEST.json")
man = json.loads(man_raw); man_sha = hashlib.sha256(man_raw).hexdigest()
# evidence class from observation facts (not labels)
mart = json.load(open(f"{ROOT}/.agent_worktrees/claude_b_analysis_current/artifacts/e001_real_marts/fact_landing_observation.json"))
obs_by_t = {c["web_target_id"]: c for c in mart}
dom_sha = collections.defaultdict(list)
for p in glob.glob(f"{ROOT}/.agent_worktrees/claude_b_e001_worker_0*/artifacts/e001_w0*/evidence/*/*/l0a/dom.html"):
    obs = p.split("/")[-3]
    if obs in {c["observation_id"] for c in mart}:
        dom_sha[hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()].append(obs)
degenerate_obs = {o for v in dom_sha.values() if len(v) > 1 for o in v}
def eclass(t):
    c = obs_by_t.get(t)
    if c is None: return "POOR", "unobserved"
    if str(c.get("measurement_status", "")).startswith("FAILED"): return "POOR", "failed_evidence_incomplete"
    if c["observation_id"] in degenerate_obs: return "POOR", "degenerate"
    return "NORMAL", None
def okey(t): return hashlib.sha256(f"{SEED}|{t}".encode()).hexdigest()[:16]
quota = man["quota"]; pools = collections.defaultdict(list)
for r in cand: pools[r["interaction_archetype"]].append(r["web_target_id"])
sel = {}; trace = []
for a, q in sorted(quota.items()):
    pool = sorted(pools[a], key=okey); poor = [t for t in pool if eclass(t)[0] == "POOR"]; normal = [t for t in pool if eclass(t)[0] == "NORMAL"]
    chosen = []
    if q >= 2 and poor: chosen.append(poor[0])
    for t in normal:
        if len(chosen) >= q: break
        if t not in chosen: chosen.append(t)
    for t in poor:
        if len(chosen) >= q: break
        if t not in chosen: chosen.append(t)
    sel[a] = chosen; trace.append({"archetype": a, "pool": len(pool), "poor_in_pool": len(poor), "quota": q, "selected": chosen})
man_sel = {t["prior_archetype"]: [] for t in man["targets"]}
for t in man["targets"]: man_sel[t["prior_archetype"]].append(t["web_target_id"])
RMAP = {"unobserved": "R1", "failed_evidence_incomplete": "R2", "degenerate": "R3", None: None}
man_class = {t["web_target_id"]: (t["evidence_class"], (t.get("poor_reason") or t.get("poor_rule") or None)) for t in man["targets"]}
mine_class = {t: list(eclass(t)) for a in sel for t in sel[a]}
okeys_match = all(okey(t["web_target_id"]) == t["order_key"] for t in man["targets"])
result = {"artifact": "C_PILOT_PREFLIGHT_SAMPLING", "control_sha": CTRL_SHA, "frame_sha": FRAME_SHA, "seed": SEED,
          "manifest_sha256_recomputed": man_sha, "manifest_sha256_claimed": "4d3209cad1a316caad117255934617097fdb96f77da67666feb42f71e2c86fc2",
          "frame_rows": len(rows), "frame_candidate": len(cand), "archetypes_in_frame": sorted(pools), "quota_sum": sum(quota.values()),
          "evidence_class_counts_frame": collections.Counter(eclass(r["web_target_id"])[1] or "NORMAL" for r in cand),
          "order_key_match_12": okeys_match, "selection_match": sel == {a: man_sel.get(a, []) for a in sel},
          "evidence_class_match": all(t in man_class and mine_class[t][0] == man_class[t][0] and (man_class[t][1] in (None, "None") or str(man_class[t][1]).startswith(RMAP[mine_class[t][1]] or "R?") or man_class[t][1] == mine_class[t][1]) for t in mine_class), "mine_class": mine_class, "man_class": man_class,
          "trace_match": trace == man["selection_trace"], "inputs_used": ["frame CSV @2281c85 (mapping_status==CANDIDATE, interaction_archetype)", "E001 mart fact_landing_observation (measurement_status, observation_id)", "stored dom.html bytes (degenerate)", "seed"],
          "inputs_NOT_used": ["split json (calibration/holdout)", "LABELS_FROZEN", "any detector output"], "trace": trace}
print(json.dumps(result, ensure_ascii=False, indent=1, default=str))
