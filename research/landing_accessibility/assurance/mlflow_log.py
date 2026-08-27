#!/usr/bin/env python3
"""C assurance registry on MLflow (Director contract 2026-08-27 21:57 KST).

MLflow is NOT truth. Truth precedence: raw/runtime/exact SHA → independent computation → frozen definition
→ accepted SSOT decision → MLflow metadata/prose. A run's existence approves nothing.
C runs: authority_status=ASSURANCE_RESULT, self_approved=false, real_target=no, never import B/D metrics.
Holdout: split=holdout runs log SUMMARY metrics only — no raw holdout labels/artifacts are uploaded.
"""
from __future__ import annotations
import json, os, hashlib, pathlib, subprocess, datetime
import mlflow

TRACKING_URI = os.environ.get("MLFLOW_TRACKING_URI", "http://127.0.0.1:5000")
EXPERIMENT = "LA_00_ASSURANCE_C"
PLANE = "C"; AGENT = "claude-c-fable-9025a829"
WT = pathlib.Path("/home/sieg/projects-wsl/ProjectFinal/.agent_worktrees/claude_c_assurance_v21")
KST = datetime.timezone(datetime.timedelta(hours=9))
REQUIRED_TAGS = ["project","plane","agent_id","subagent_id","ticket_id","phase","claim_kind","hypothesis_id","parent_run_id","git_branch","base_sha","result_sha","input_snapshot_sha","evidence_manifest_sha","label_snapshot_sha","split","authority_status","evidence_status","self_approved","real_target",
                 "source_run_id","source_plane","source_result_sha","assurance_input_sha","independent_method","match_status","difference","severity"]
REQUIRED_PARAMS = ["objective","method","dataset_grain","n_expected","n_observed","model_or_rule_version","protocol_version"]
HOLDOUT_FORBIDDEN_ARTIFACT_HINTS = ("HOLDOUT_FOR_C", "OVERLAP_L", "LABELS_FROZEN", "holdout_labels")

def _sha_file(p: str | pathlib.Path) -> str:
    h = hashlib.sha256(); h.update(pathlib.Path(p).read_bytes()); return h.hexdigest()

def head_sha() -> str:
    return subprocess.run(["git", "-C", str(WT), "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()

def log_assurance_run(*, name: str, experiment: str = EXPERIMENT, ticket_id: str, phase: str, claim_kind: str, params: dict, metrics: dict, tags: dict,
                      artifacts: list[str | pathlib.Path] = (), status: str = "COMPLETED", split: str = "none",
                      summary_text: str = "", limitations: str = "", notes_json: dict | None = None) -> str:
    mlflow.set_tracking_uri(TRACKING_URI); mlflow.set_experiment(experiment)
    base = {"project": "landing_accessibility_v21", "plane": PLANE, "agent_id": AGENT, "subagent_id": "NONE", "ticket_id": ticket_id,
            "phase": phase, "claim_kind": claim_kind, "hypothesis_id": "NONE", "parent_run_id": "NONE", "git_branch": "claude-c/assurance-v21",
            "base_sha": "1baa865b4a673af05033e6e6289fd2713676baa5", "result_sha": head_sha(), "input_snapshot_sha": "NONE", "evidence_manifest_sha": "NONE",
            "label_snapshot_sha": "NONE", "split": split, "authority_status": "ASSURANCE_RESULT", "evidence_status": "INDEPENDENT_RECOMPUTATION",
            "self_approved": "false", "real_target": "no", "source_run_id": "NONE", "source_plane": "NONE", "source_result_sha": "NONE",
            "assurance_input_sha": "NONE", "independent_method": "", "match_status": "", "difference": "", "severity": "", "run_status_vocab": status,
            "labels_produced": "0", "production_modified": "false"}
    base.update({k: str(v) for k, v in tags.items()})
    missing = [k for k in REQUIRED_TAGS if not base.get(k)]
    if missing: raise ValueError(f"missing required tags: {missing}")
    pm = {k: params.get(k, "NONE") for k in REQUIRED_PARAMS}; pm.update({k: v for k, v in params.items() if k not in pm})
    if split == "holdout":
        for a in artifacts:
            if any(h in str(a) for h in HOLDOUT_FORBIDDEN_ARTIFACT_HINTS): raise ValueError(f"refusing to upload holdout raw artifact: {a}")
    with mlflow.start_run(run_name=name) as run:
        mlflow.set_tags(base); mlflow.log_params({k: str(v)[:500] for k, v in pm.items()})
        if metrics: mlflow.log_metrics({k: float(v) for k, v in metrics.items() if v is not None})
        for a in artifacts:
            a = pathlib.Path(a)
            if a.exists(): mlflow.log_artifact(str(a), artifact_path="assurance")
        doc = {"summary": summary_text, "limitations": limitations, "generated_at": datetime.datetime.now(KST).isoformat(timespec="seconds"),
               "artifact_manifest": [{"path": str(a), "sha256": _sha_file(a)} for a in artifacts if pathlib.Path(a).exists()], **(notes_json or {})}
        mlflow.log_dict(doc, "assurance/result_summary.json")
        mlflow.set_tag("run_status_vocab", status)
        return run.info.run_id

if __name__ == "__main__":
    print(TRACKING_URI, EXPERIMENT)
