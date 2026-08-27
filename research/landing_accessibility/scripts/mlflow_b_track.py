"""B plane MLflow tracking — LA-MLFLOW-2.1 계약 구현.

MLflow 는 **production trace 이지 연구 authority 가 아니다**. Truth precedence 는 그대로:
raw artifact/runtime/SHA > 재현가능 계산 > frozen definition > SSOT decision > MLflow metadata.

run 이 존재한다는 사실만으로 결과가 승인되지 않는다. 모든 B run 은
`self_approved=false` · `authority_status=IMPLEMENTATION_CANDIDATE` 로 고정한다.
"""
from __future__ import annotations
import hashlib, json, os, subprocess, sys
from pathlib import Path

ROOT = Path("/home/sieg/projects-wsl/ProjectFinal")
# canonical store (T-A-MLFLOW-002). 네 갈래로 갈라진 store 를 서버 하나로 모았다 —
# sqlite 파일은 여러 plane 이 동시에 한 화면으로 볼 수 없다.
TRACKING = os.environ.get("MLFLOW_TRACKING_URI", "http://127.0.0.1:5000")
ARTIFACT_ROOT = None  # 서버가 관리한다
# 서버에 선 LA_01..LA_10 주제 네임스페이스에 맞춘다 (T-A-MLFLOW-002).
# A 가 worker→experiment 매핑을 명시하지 않아 B 가 주제로 배정하고 통보한다 — 되돌릴 수 있다.
EXPERIMENT_BY_SUBAGENT = {
    "B-orchestration": "LA_00_GOVERNANCE",
    "W1": "LA_02_GUARD",
    "W2": "LA_03_RF_MAPPING",
    "W3": "LA_05_KWCAG",
    "W4": "LA_06_OBSTRUCTION",
    "W4-mart": "LA_08_MART",
}
DEFAULT_EXPERIMENT = "LA_00_GOVERNANCE"
PROTOCOL_VERSION = "LA-ORCH-2.1"
#: B 가 참조할 수 있는 유일한 label snapshot. holdout 은 C 전용이다.
CALIBRATION_SHA = "140619aeba5835c08a40e43175394e94aed5725c5be58eb999f4c679709ab00e"

REQUIRED_TAGS = (
    "project plane agent_id subagent_id ticket_id phase claim_kind hypothesis_id "
    "parent_run_id git_branch base_sha result_sha input_snapshot_sha evidence_manifest_sha "
    "label_snapshot_sha split authority_status evidence_status self_approved real_target"
).split()

REQUIRED_PARAMS = ("objective method dataset_grain n_expected n_observed "
                   "model_or_rule_version protocol_version").split()

RUN_STATUS = {"RUNNING", "COMPLETED", "FAILED", "ABSTAINED", "INVALIDATED", "SUPERSEDED"}


def sha256_file(p: Path) -> str | None:
    if not p.exists():
        return None
    h = hashlib.sha256()
    with p.open("rb") as fh:
        for ch in iter(lambda: fh.read(1 << 20), b""):
            h.update(ch)
    return h.hexdigest()


def git_sha(branch: str) -> str | None:
    """원격 exact SHA. branch name 으로 상태를 주장하지 않는다 (프로토콜 §9)."""
    try:
        out = subprocess.run(["git", "-C", str(ROOT), "ls-remote", "origin",
                              f"refs/heads/{branch}"], capture_output=True, text=True, timeout=30)
        return out.stdout.split("\t")[0] or None
    except Exception:
        return None


def log_run(*, ticket_id, subagent_id, branch, result_sha, objective, method,
            dataset_grain, n_expected, n_observed, model_or_rule_version,
            metrics=None, artifacts=None, limitations=None, failures=None,
            status="COMPLETED", phase="I1", claim_kind="IMPLEMENTATION",
            hypothesis_id="NONE", parent_run_id="NONE", split="none",
            label_snapshot_sha="NONE", real_target="no", extra_tags=None,
            extra_params=None, nested=False):
    import mlflow

    if status not in RUN_STATUS:
        raise ValueError(f"status must be one of {RUN_STATUS}")

    # B2 (EXECUTION AMENDMENT) — B 는 holdout 을 읽지 않는다. split tag 로도 소비하지 않는다.
    # holdout-tagged artifact 가 input lineage 에 있으면 run 은 INVALIDATED 다.
    if split == "holdout":
        raise PermissionError(
            "B plane must not consume holdout. split='holdout' is C-only "
            "(C-BLOCKER-215510 / T-A-HOLDOUT-SCOPE-001)."
        )
    if label_snapshot_sha not in ("NONE", CALIBRATION_SHA):
        raise PermissionError(
            f"unexpected label_snapshot_sha={label_snapshot_sha!r}; "
            f"B may only reference CALIBRATION_FOR_B ({CALIBRATION_SHA[:12]}…)"
        )

    mlflow.set_tracking_uri(TRACKING)
    mlflow.set_experiment(EXPERIMENT_BY_SUBAGENT.get(subagent_id, DEFAULT_EXPERIMENT))

    manifest = ROOT / ".agent_worktrees/claude_b_clean0/research/landing_accessibility/handoff/ARTIFACT_RETENTION_MANIFEST_E001.json"
    tags = {
        "project": "landing_accessibility_v21",
        "plane": "B",
        "agent_id": "claude-b",
        "subagent_id": subagent_id,
        "ticket_id": ticket_id,
        "phase": phase,
        "claim_kind": claim_kind,
        "hypothesis_id": hypothesis_id,
        "parent_run_id": parent_run_id,
        "git_branch": branch,
        "base_sha": "2281c853950d0c475c5d2c1678680b971c2804f4",
        "result_sha": result_sha,
        "input_snapshot_sha": "2281c853950d0c475c5d2c1678680b971c2804f4",
        "evidence_manifest_sha": sha256_file(manifest) or "NONE",
        "label_snapshot_sha": label_snapshot_sha,
        "split": split,
        # B 는 자기 run 을 승인하지 않는다. C validation 전까지 고정.
        "authority_status": "IMPLEMENTATION_CANDIDATE",
        "evidence_status": "OFFLINE_REPLAY" if real_target == "no" else "REAL_TARGET",
        "self_approved": "false",
        "real_target": real_target,
        "run_status": status,
        "remote_verified_sha": git_sha(branch) or "UNVERIFIED",
    }
    tags.update(extra_tags or {})
    missing = [t for t in REQUIRED_TAGS if t not in tags]
    if missing:
        raise ValueError(f"required tags missing: {missing}")

    params = {
        "objective": objective, "method": method, "dataset_grain": dataset_grain,
        "n_expected": n_expected, "n_observed": n_observed,
        "model_or_rule_version": model_or_rule_version,
        "protocol_version": PROTOCOL_VERSION,
    }
    params.update(extra_params or {})
    missing_p = [p for p in REQUIRED_PARAMS if p not in params]
    if missing_p:
        raise ValueError(f"required params missing: {missing_p}")

    with mlflow.start_run(run_name=f"{subagent_id}:{ticket_id}", nested=nested) as run:
        mlflow.set_tags(tags)
        mlflow.log_params(params)
        for k, v in (metrics or {}).items():
            mlflow.log_metric(k, v)
        for name, obj in (artifacts or {}).items():
            mlflow.log_dict(obj, name) if isinstance(obj, (dict, list)) else mlflow.log_text(str(obj), name)
        if limitations:
            mlflow.log_dict({"limitations": limitations}, "limitation_summary.json")
        if failures:
            mlflow.log_dict({"failures": failures}, "error_failure_summary.json")
        # 원격 SHA 대조 결과를 명시적으로 남긴다 — branch name 은 상태 주장이 아니다
        if tags["remote_verified_sha"] not in (result_sha, "UNVERIFIED"):
            mlflow.set_tag("sha_mismatch_warning",
                           f"remote={tags['remote_verified_sha']} != logged={result_sha}")
        return run.info.run_id


if __name__ == "__main__":
    print(f"tracking = {TRACKING}\nexperiments = {EXPERIMENT_BY_SUBAGENT}")
