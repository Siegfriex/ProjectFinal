"""Claude A — MLflow Decision/Gate Registry.

A 는 실험 생산자가 아니라 gate registry 다. 이 스크립트는 A 의 DECISION 만 기록한다.
MLflow 는 SSOT 가 아니다 — truth precedence 는 raw/runtime > 재현계산 > frozen 정의 >
accepted SSOT > MLflow metadata 순이며, run 의 존재가 승인을 뜻하지 않는다.
"""
from __future__ import annotations
import os, sys, json, subprocess, pathlib

# 정본 store — 21:45 부터 떠 있는 tracking server. Director 의 "한 화면에서 감시" 요구를
# 충족하는 유일한 형태이고 LA_01..LA_10 네임스페이스가 이미 서 있다.
# A 는 자기 sqlite 를 버리고 여기로 합친다 (T-A-MLFLOW-002).
TRACKING = os.environ.get("MLFLOW_TRACKING_URI") or "http://127.0.0.1:5000"
ARTIFACT_ROOT = None  # 서버가 정한다
EXPERIMENT = "LA_00_GOVERNANCE"  # A 전용 — gate/decision registry


def _sha(ref: str) -> str:
    try:
        return subprocess.run(["git", "rev-parse", ref], capture_output=True, text=True,
                              cwd="/home/sieg/projects-wsl/ProjectFinal").stdout.strip() or "UNKNOWN"
    except Exception:
        return "UNKNOWN"


def log_gate(gate: str, decision: str, reason: str, *,
             b_sha="NONE", c_sha="NONE", d_findings="NONE",
             open_blockers=(), accepted=(), deferred=(),
             params=None, metrics=None, artifacts=None, status="COMPLETED",
             authority_status="A_ACCEPTED", ticket_id="NONE", phase="I1"):
    import mlflow
    mlflow.set_tracking_uri(TRACKING)
    if mlflow.get_experiment_by_name(EXPERIMENT) is None:
        mlflow.create_experiment(EXPERIMENT, tags={
            "project": "landing_accessibility_v21", "plane": "A",
            "mlflow.note.content": "A — Decision/Gate Registry. A run 만 DECISION 상태를 기록한다. "
                                   "MLflow 는 SSOT 가 아니며 run 의 존재가 승인을 뜻하지 않는다.",
        })
    mlflow.set_experiment(EXPERIMENT)
    with mlflow.start_run(run_name=f"A::{gate}") as run:
        mlflow.set_tags({
            "project": "landing_accessibility_v21", "plane": "A",
            "agent_id": "claude-a", "subagent_id": "NONE",
            "ticket_id": ticket_id, "phase": phase, "claim_kind": "DECISION",
            "hypothesis_id": "NONE", "parent_run_id": "NONE",
            "git_branch": "control/landing-orchestrator",
            "base_sha": _sha("HEAD"), "result_sha": _sha("HEAD"),
            "input_snapshot_sha": "NONE", "evidence_manifest_sha": "NONE",
            "label_snapshot_sha": "NONE", "split": "none",
            "authority_status": authority_status, "evidence_status": "A_DECISION",
            "self_approved": "false", "real_target": "no",
            "gate": gate, "decision": decision,
            "b_candidate_sha": b_sha, "c_assurance_sha": c_sha,
            "d_finding_ids": d_findings,
        })
        mlflow.log_params({
            "objective": f"gate decision: {gate}", "method": "A authority reconciliation",
            "dataset_grain": "NA", "n_expected": "NA", "n_observed": "NA",
            "model_or_rule_version": "SSOT v2.1", "protocol_version": "LA-ORCH-2.1",
            **(params or {}),
        })
        if metrics:
            mlflow.log_metrics(metrics)
        summary = {
            "gate": gate, "decision": decision, "reason": reason,
            "authority_sha": _sha("HEAD"), "b_candidate_sha": b_sha,
            "c_assurance_sha": c_sha, "d_findings": d_findings,
            "open_blockers": list(open_blockers),
            "accepted_findings": list(accepted), "deferred_findings": list(deferred),
            "run_status": status,
            "caveat": "MLflow run 의 존재가 승인을 뜻하지 않는다. truth precedence 는 raw/runtime 이 우선.",
        }
        mlflow.log_dict(summary, "decision_summary.json")
        for a in (artifacts or []):
            if pathlib.Path(a).exists():
                mlflow.log_artifact(a)
        return run.info.run_id


if __name__ == "__main__":
    print(json.dumps({"tracking_uri": TRACKING, "artifact_root": ARTIFACT_ROOT, "experiment": EXPERIMENT}, indent=2))
