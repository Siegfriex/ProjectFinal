"""E 의 P0 bootstrap run 을 MLflow 에 기록한다 (Director MLflow 관측 계약, 2026-08-27 21:57).

C 의 `assurance/mlflow_log.py` 와 같은 tag 이름 집합을 쓴다(cross-plane 비교 가능하도록) —
코드는 재사용하지 않는다(plane 마다 자기 코드로 독립 기록). MLflow 는 truth 가 아니다:
이 run 의 존재가 P0 완료를 "승인"하지 않는다. 실제 근거는 이 커밋의 git 이력과 파일 자체다.
"""
from __future__ import annotations
import datetime
import hashlib
import json
import pathlib
import subprocess

import mlflow

TRACKING_URI = "http://127.0.0.1:5000"
EXPERIMENT = "LA_11_PATHFINDER_E"
WT = pathlib.Path("/home/sieg/projects-wsl/ProjectFinal/.agent_worktrees/claude_e_pathfinder")
BOOTSTRAP = WT / "research/landing_accessibility/pathfinder_e/bootstrap"
KST = datetime.timezone(datetime.timedelta(hours=9))

REQUIRED_TAGS = [
    "project", "plane", "agent_id", "subagent_id", "ticket_id", "phase", "claim_kind",
    "hypothesis_id", "parent_run_id", "git_branch", "base_sha", "result_sha",
    "input_snapshot_sha", "evidence_manifest_sha", "label_snapshot_sha", "split",
    "authority_status", "evidence_status", "self_approved", "real_target",
    "source_run_id", "source_plane", "source_result_sha", "assurance_input_sha",
    "independent_method", "match_status", "difference", "severity",
]
REQUIRED_PARAMS = [
    "objective", "method", "dataset_grain", "n_expected", "n_observed",
    "model_or_rule_version", "protocol_version",
]


def head_sha() -> str:
    return subprocess.run(
        ["git", "-C", str(WT), "rev-parse", "HEAD"], capture_output=True, text=True
    ).stdout.strip()


def sha_file(p: pathlib.Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main() -> None:
    mlflow.set_tracking_uri(TRACKING_URI)
    mlflow.set_experiment(EXPERIMENT)

    qa = json.loads((BOOTSTRAP / "PARSE_QA_REPORT.json").read_text(encoding="utf-8"))
    n_pass = sum(1 for c in qa["checks"] if c["ok"])
    n_total = len(qa["checks"])

    manifest_sha = "NONE"
    ssot_manifest = pathlib.Path("/home/sieg/projects-wsl/ProjectFinal/SSOTV3/MANIFEST_v3.0.json")
    if ssot_manifest.exists():
        manifest_sha = sha_file(ssot_manifest)

    tags = {
        "project": "landing_accessibility_v3",
        "plane": "E",
        "agent_id": "claude-e-sonnet5-pathfinder-v3",
        "subagent_id": "NONE",
        "ticket_id": "T-E-COMPLETION-001",
        "phase": "P0",
        "claim_kind": "OBSERVATION",
        "hypothesis_id": "NONE",
        "parent_run_id": "NONE",
        "git_branch": "claude-e/pathfinder-v3",
        "base_sha": "2e826a578caab32e2629c59b361aa37f409f36ac",
        "result_sha": head_sha(),
        "input_snapshot_sha": manifest_sha,
        "evidence_manifest_sha": "NONE",
        "label_snapshot_sha": "NONE",
        "split": "none",
        "authority_status": "AUXILIARY_EXECUTION_EVIDENCE",
        "evidence_status": "OFFLINE_BOOTSTRAP",
        "self_approved": "false",
        "real_target": "no",
        "source_run_id": "NONE",
        "source_plane": "NONE",
        "source_result_sha": "NONE",
        "assurance_input_sha": "NONE",
        "independent_method": "NONE",
        "match_status": "NONE",
        "difference": "NONE",
        "severity": "NONE",
    }
    missing = [k for k in REQUIRED_TAGS if not tags.get(k)]
    if missing:
        raise ValueError(f"missing required tags: {missing}")

    params = {
        "objective": "P0 bootstrap: SSOTV3 parsing + route-work manifest + hash inventory + "
                     "action-token gap check + evidence checklist + offline schema rehearsal + "
                     "family worker queue",
        "method": "deterministic csv/openpyxl parsing + sha256 canonical-json hashing + "
                   "code archaeology (l1_engine.py/vocabulary.py) + synthetic schema self-validation",
        "dataset_grain": "service_task (50 targets x 5 families)",
        "n_expected": 50,
        "n_observed": 50,
        "model_or_rule_version": "SSOTV3 (AUTHORITY_CANDIDATE / NO_NEW_REAL_TARGET_RELEASE)",
        "protocol_version": "LA-ORCH-3E",
    }
    missing_p = [k for k in REQUIRED_PARAMS if k not in params]
    if missing_p:
        raise ValueError(f"missing required params: {missing_p}")

    metrics = {
        "target_count": 50,
        "family_count": 5,
        "action_token_count_v3": 18,
        "action_token_code_overlap_count": 0,
        "qa_checks_pass": n_pass,
        "qa_checks_total": n_total,
        "findings_count": 4,
        "real_target_contact_count": 0,
        "synthetic_rehearsal_fields_pass": 44,
        "synthetic_rehearsal_fields_total": 44,
    }

    artifacts = sorted(BOOTSTRAP.glob("*.json")) + sorted(BOOTSTRAP.glob("*.md"))

    with mlflow.start_run(run_name="E-P0-bootstrap") as run:
        mlflow.set_tags(tags)
        mlflow.log_params(params)
        mlflow.log_metrics(metrics)
        for a in artifacts:
            mlflow.log_artifact(str(a), artifact_path="bootstrap")
        mlflow.log_dict(
            {
                "summary": "E P0 bootstrap — SSOTV3 구조화, REAL target 접촉 0건",
                "findings": ["F-E-P0-01", "F-E-P0-02", "F-E-P0-03", "F-E-P0-04"],
                "generated_at": datetime.datetime.now(KST).isoformat(timespec="seconds"),
            },
            "bootstrap/result_summary.json",
        )
        print(f"run_id={run.info.run_id}")


if __name__ == "__main__":
    main()
