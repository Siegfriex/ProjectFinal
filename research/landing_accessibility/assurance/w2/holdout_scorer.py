#!/usr/bin/env python3
"""C independent holdout scorer for W2 (representative-function DT / detector).

Independence: imports nothing from B. Reads three frozen inputs and recomputes:
  per-archetype agreement (with n), macro-average, pooled agreement, coverage, abstain rate,
  FORCE_MAP violations (label says AMBIGUOUS_UNRESOLVED but detector mapped),
  UNSAFE_ENDPOINT false positives (detector claims endpoint on a label-negative observation),
  holdout leakage check (B output must not contain holdout ids before freeze — checked via sha/timestamps by caller).

Interchange schema (C-defined; A/B conform):
  labels.jsonl   {observation_id, web_target_id, archetype_label | "AMBIGUOUS_UNRESOLVED",
                  region_present (bool|null), endpoint_observed (bool|null), evidence_refs[], labeler_id}
  split.json     {"calibration":[observation_id...], "holdout":[observation_id...], "label_sha256": "...", "frozen_at": "..."}
  detector.jsonl {observation_id, archetype_pred | "AMBIGUOUS_UNRESOLVED" | null, region_detected (bool|null),
                  endpoint_detected (bool|null), decision_trace, producer_sha}
Usage: holdout_scorer.py labels.jsonl split.json detector.jsonl out.json
"""
from __future__ import annotations
import json, sys, hashlib, collections, pathlib, datetime

ARCHETYPES = {"QUERY","CONTENT_OPEN","ITEM_DETAIL","PLACE_LOOKUP","COMMUNICATION_ENTRY","FINANCIAL_ACTION_ENTRY","UTILITY_ENTRY"}
ABSTAIN = "AMBIGUOUS_UNRESOLVED"

def sha(p): return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
def jl(p): return [json.loads(l) for l in pathlib.Path(p).read_text(encoding="utf-8").splitlines() if l.strip()]

def main(labels_p, split_p, det_p, out_p):
    labels = {r["observation_id"]: r for r in jl(labels_p)}
    split = json.loads(pathlib.Path(split_p).read_text(encoding="utf-8"))
    det = {r["observation_id"]: r for r in jl(det_p)}
    problems = []
    if split.get("label_sha256") != sha(labels_p):
        problems.append({"kind":"LABEL_HASH_MISMATCH","expected":split.get("label_sha256"),"actual":sha(labels_p)})
    hold = list(split["holdout"]); cal = set(split["calibration"])
    if set(hold) & cal: problems.append({"kind":"SPLIT_OVERLAP","ids":sorted(set(hold)&cal)})
    missing_label = [o for o in hold if o not in labels]; missing_det = [o for o in hold if o not in det]
    per = collections.defaultdict(lambda: {"n":0,"agree":0,"abstain_pred":0,"abstain_label":0})
    force_map, unsafe_ep, region_fp, region_fn = [], [], [], []
    covered = 0; agree = 0; n_eval = 0
    for o in hold:
        if o not in labels or o not in det: continue
        L, D = labels[o], det[o]
        lab = L.get("archetype_label") or L.get("archetype"); pred = D.get("archetype_pred")
        if pred not in ARCHETYPES and pred not in (ABSTAIN, None): problems.append({"kind":"PRED_OUTSIDE_7","observation_id":o,"pred":pred})
        key = lab if lab in ARCHETYPES else ABSTAIN
        per[key]["n"] += 1
        if lab == ABSTAIN:
            per[key]["abstain_label"] += 1
            if pred in ARCHETYPES: force_map.append({"observation_id":o,"pred":pred,"trace":D.get("decision_trace")})
            continue
        n_eval += 1
        if pred in ARCHETYPES:
            covered += 1
            if pred == lab: agree += 1; per[key]["agree"] += 1
        else:
            per[key]["abstain_pred"] += 1
        if D.get("endpoint_detected") is True and L.get("endpoint_observed") is False:
            unsafe_ep.append({"observation_id":o,"label_archetype":lab})
        if D.get("region_detected") is True and L.get("region_present") is False: region_fp.append(o)
        if D.get("region_detected") is False and L.get("region_present") is True: region_fn.append(o)
    per_arch = {}
    for k, v in per.items():
        if k == ABSTAIN: per_arch[k] = v; continue
        evaluated = v["n"]; mapped = evaluated - v["abstain_pred"]
        per_arch[k] = {**v, "agreement_on_mapped": (v["agree"]/mapped) if mapped else None, "coverage": (mapped/evaluated) if evaluated else None,
                       "low_n_flag": evaluated < 5}
    macro = [x["agreement_on_mapped"] for k,x in per_arch.items() if k != ABSTAIN and x["agreement_on_mapped"] is not None]
    out = {"artifact":"C_W2_HOLDOUT_SCORE","generated_at":datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9))).isoformat(timespec="seconds"),
           "inputs":{"labels_sha256":sha(labels_p),"split_sha256":sha(split_p),"detector_sha256":sha(det_p),"detector_producer_sha":next((r.get("producer_sha") for r in det.values()),None)},
           "holdout_n":len(hold),"evaluated_n":n_eval,"missing_label":missing_label,"missing_detector_output":missing_det,
           "pooled_agreement_on_mapped": (agree/covered) if covered else None, "coverage": (covered/n_eval) if n_eval else None,
           "macro_agreement": (sum(macro)/len(macro)) if macro else None, "per_archetype": per_arch,
           "force_map_violations": force_map, "unsafe_endpoint_false_positives": unsafe_ep, "region_fp": region_fp, "region_fn": region_fn,
           "release_gate_engineering_not_research": {"unsafe_endpoint_fp_zero": len(unsafe_ep)==0, "no_force_map": len(force_map)==0,
               "pooled_agreement_ge_0.85": ((agree/covered) if covered else 0) >= 0.85, "coverage_ge_0.75": ((covered/n_eval) if n_eval else 0) >= 0.75,
               "note": "pooled 은 ITEM_DETAIL 이 지배할 수 있다 — per_archetype 와 macro 를 함께 읽는다. n<5 archetype 은 low_n_flag."},
           "problems": problems,
           "not_verified": ["endpoint_observed 는 L0 evidence 만으로는 label 불가 — offline 에서는 null 이 정상이며 unsafe_endpoint 검사는 fixture/pilot 에서 별도"]}
    pathlib.Path(out_p).write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({k: out[k] for k in ("holdout_n","evaluated_n","pooled_agreement_on_mapped","coverage","macro_agreement","release_gate_engineering_not_research","problems")}, ensure_ascii=False, indent=1))

if __name__ == "__main__":
    if len(sys.argv) != 5: print(__doc__); sys.exit(2)
    main(*sys.argv[1:])
