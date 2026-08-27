"""GLOBAL MLFLOW OBSERVABILITY CONTRACT — ProjectFinal Landing Accessibility v2.1.

MLflow 는 SSOT 도 empirical truth 도 아니다. truth precedence 는 그대로다:

    raw artifact / runtime evidence / exact code SHA
    → independently reproducible computation
    → frozen definition / codebook / schema
    → current accepted SSOT / decision
    → **MLflow metadata / prose / agent narrative**

MLflow run 이 존재한다는 사실만으로 결과가 승인되지 않는다.

이 모듈은 계약을 코드로 강제한다. 필수 tag/param 이 빠지면 run 을 만들지 않고 예외를 던진다.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path

import mlflow

TRACKING_URI = "http://127.0.0.1:5000"
PROJECT = "landing_accessibility_v21"
KST = timezone(timedelta(hours=9))

RD = Path(__file__).resolve().parents[1]
WT = RD.parents[2]
REPO = Path("/home/sieg/projects-wsl/ProjectFinal")

# 주제별 experiment. 한 화면에서 D 실험 · B 구현 · C 검증 · A 결정이 계보로 보이게 한다.
EXPERIMENTS = {
    "LA_01_FRAME":       "연구 frame · target/task freeze · 모집단 정의",
    "LA_02_GUARD":       "login/auth/CAPTCHA guard · candidate-level action mask",
    "LA_03_RF_MAPPING":  "Representative Function Mapping · Rule DT · NLP fallback",
    "LA_04_ENDPOINT":    "endpoint detector · signal family · NED/IED/MPFED",
    "LA_05_KWCAG":       "KWCAG older-relevant subset evaluator",
    "LA_06_OBSTRUCTION": "Axis C overlay · occlusion · interrupt semantics",
    "LA_07_COLLECTION":  "수집 실행 · evidence 완결성 · probe 절단 · slot 정합",
    "LA_08_MART":        "mart 구축 · missingness · joint-valid",
    "LA_09_STATISTICS":  "기술통계 · planned association · robustness",
    "LA_10_RESEARCH_D":  "D 연구소 메타 — queue · cross-RQ synthesis · dashboard",
}

RUN_STATUS = ("RUNNING", "COMPLETED", "FAILED", "ABSTAINED", "INVALIDATED", "SUPERSEDED")
AUTHORITY = ("NON_CANONICAL", "ADVISORY", "C_CONFIRMED", "A_ACCEPTED",
             "ADOPTED_FOR_IMPLEMENTATION", "CANONICALIZED", "DEFERRED_NEXT_VERSION",
             "IMPLEMENTATION_CANDIDATE", "ASSURANCE_RESULT", "DECISION")
PLANE_DEFAULT_AUTHORITY = {"D": "NON_CANONICAL", "B": "IMPLEMENTATION_CANDIDATE",
                           "C": "ASSURANCE_RESULT", "A": "DECISION"}
CLAIM_KINDS = ("DEFINITION", "IMPLEMENTATION", "OBSERVATION", "ANALYSIS", "DECISION", "PROJECTION")
SPLITS = ("calibration", "holdout", "all", "none")
VERDICTS = ("SUPPORTED", "PARTIALLY_SUPPORTED", "REFUTED", "NOT_SUPPORTED",
            "INCONCLUSIVE", "NOT_TESTABLE", "PENDING")

REQUIRED_TAGS = ("project", "plane", "agent_id", "subagent_id", "ticket_id", "phase",
                 "claim_kind", "hypothesis_id", "parent_run_id", "git_branch", "base_sha",
                 "result_sha", "input_snapshot_sha", "evidence_manifest_sha",
                 "label_snapshot_sha", "split", "authority_status", "evidence_status",
                 "self_approved", "real_target", "run_status")
REQUIRED_PARAMS = ("objective", "method", "dataset_grain", "n_expected", "n_observed",
                   "model_or_rule_version", "protocol_version")

BASE_SHA = "bc0b7a087faf2328cbafdfa9b40bd426c5080d7d"
BRANCH = "claude-d/research-sandbox-v21"
PROTOCOL_VERSION = "LA-ORCH-2.1"


def sha256_file(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def git(*a: str) -> str:
    return subprocess.run(["git", *a], cwd=WT, capture_output=True, text=True).stdout.strip()


def input_snapshot_sha() -> str:
    p = RD / "INPUT_SNAPSHOT_v21.json"
    return sha256_file(p) if p.exists() else "NONE"


def evidence_manifest_sha() -> str:
    """Git 밖 대형 raw evidence 는 업로드하지 않고 manifest hash + path pointer 로 대신한다."""
    for cand in (REPO / ".agent_worktrees/claude_b_handoff/artifacts/ARTIFACT_RETENTION_MANIFEST_E001.json",
                 RD / "INPUT_SNAPSHOT_v21.json"):
        if cand.exists():
            return sha256_file(cand)
    return "NONE"


def _holdout_accessed_from_scan() -> str:
    """D amendment D1: holdout_accessed 는 self-tag 가 아니라 input manifest scan 결과다.

    스캔 결과 파일이 없거나 FAIL 이면 'UNVERIFIED' / 'true' 를 반환한다. 모르면 false 라고
    쓰지 않는다.
    """
    v = RD / "results" / "D_INPUT_FIREWALL_VERIFICATION.json"
    if not v.exists():
        return "UNVERIFIED_NO_SCAN"
    try:
        doc = json.loads(v.read_text(encoding="utf-8"))
    except Exception:
        return "UNVERIFIED_SCAN_UNREADABLE"
    return "false" if doc.get("verdict") == "PASS" else "true"


def ensure_experiments() -> dict[str, str]:
    mlflow.set_tracking_uri(TRACKING_URI)
    out = {}
    for name, desc in EXPERIMENTS.items():
        exp = mlflow.get_experiment_by_name(name)
        if exp is None:
            eid = mlflow.create_experiment(name, tags={"project": PROJECT, "mlflow.note.content": desc})
        else:
            eid = exp.experiment_id
        out[name] = eid
    return out


class ContractViolation(RuntimeError):
    pass


@contextmanager
def research_run(*, experiment: str, run_name: str, plane: str, objective: str, method: str,
                 dataset_grain: str, n_expected, n_observed, hypothesis_id: str = "NONE",
                 competing_hypothesis: str | None = None, claim_kind: str = "ANALYSIS",
                 ticket_id: str = "NONE", phase: str = "I1", agent_id: str = "D",
                 subagent_id: str = "NONE", split: str = "none", nested: bool = False,
                 parent_run_id: str = "NONE", result_path: Path | None = None,
                 model_or_rule_version: str = "NONE", label_snapshot_sha: str = "NONE",
                 evidence_status: str = "EVIDENCE_BACKED", real_target: str = "no",
                 authority_status: str | None = None, extra_tags: dict | None = None,
                 extra_params: dict | None = None, seed=None, code_path: Path | str | None = None,
                 limitation: str | None = None, notebook: str | None = None):
    """계약을 만족하는 run 을 연다. 필수 항목이 빠지면 열지 않는다."""
    if experiment not in EXPERIMENTS:
        raise ContractViolation(f"unknown experiment: {experiment}")
    if plane not in ("A", "B", "C", "D"):
        raise ContractViolation(f"plane must be A|B|C|D: {plane}")
    if claim_kind not in CLAIM_KINDS:
        raise ContractViolation(f"claim_kind: {claim_kind}")
    if split not in SPLITS:
        raise ContractViolation(f"split: {split}")
    authority = authority_status or PLANE_DEFAULT_AUTHORITY[plane]
    if authority not in AUTHORITY:
        raise ContractViolation(f"authority_status: {authority}")
    if plane != "A" and authority == "DECISION":
        raise ContractViolation("A run 만 DECISION 상태를 기록할 수 있다")

    mlflow.set_tracking_uri(TRACKING_URI)
    mlflow.set_experiment(experiment)

    tags = {
        "project": PROJECT, "plane": plane, "agent_id": agent_id, "subagent_id": subagent_id,
        "ticket_id": ticket_id, "phase": phase, "claim_kind": claim_kind,
        "hypothesis_id": hypothesis_id, "parent_run_id": parent_run_id,
        "git_branch": BRANCH, "base_sha": BASE_SHA,
        "result_sha": sha256_file(result_path) if result_path and result_path.exists() else "NONE",
        "input_snapshot_sha": input_snapshot_sha(),
        "evidence_manifest_sha": evidence_manifest_sha(),
        "label_snapshot_sha": label_snapshot_sha,
        "split": split, "authority_status": authority, "evidence_status": evidence_status,
        "self_approved": "false", "real_target": real_target, "run_status": "RUNNING",
        "head_sha": git("rev-parse", "HEAD"),
        "worktree_dirty": str(bool(git("status", "--porcelain"))),
        "started_at_kst": datetime.now(KST).isoformat(),
        "verdict": "PENDING",
        "labels_produced": "false", "production_modified": "false",
        # holdout_accessed 는 self-tag 가 아니라 방화벽 스캔 결과에서 온다.
        "holdout_accessed": _holdout_accessed_from_scan(),
        "holdout_verification": "tools/d_input_firewall.py manifest scan",
        "code_sha": (hashlib.sha256(Path(code_path).read_bytes()).hexdigest()
                     if code_path and Path(code_path).exists() else "NONE"),
        "notebook": notebook or "NONE",
    }
    if limitation:
        tags["limitation_summary"] = limitation[:480]
    if competing_hypothesis:
        tags["competing_hypothesis"] = competing_hypothesis[:480]
    if extra_tags:
        tags.update({k: str(v)[:480] for k, v in extra_tags.items()})
    missing = [t for t in REQUIRED_TAGS if not tags.get(t)]
    if missing:
        raise ContractViolation(f"필수 tag 누락: {missing}")

    params = {
        "objective": objective[:480], "method": method[:480], "dataset_grain": dataset_grain[:480],
        "n_expected": n_expected, "n_observed": n_observed,
        "model_or_rule_version": model_or_rule_version, "protocol_version": PROTOCOL_VERSION,
    }
    if seed is not None:
        params["seed"] = seed
    if extra_params:
        params.update({k: str(v)[:480] for k, v in extra_params.items()})
    missing_p = [p for p in REQUIRED_PARAMS if params.get(p) in (None, "")]
    if missing_p:
        raise ContractViolation(f"필수 param 누락: {missing_p}")

    with mlflow.start_run(run_name=run_name, nested=nested) as run:
        mlflow.set_tags(tags)
        mlflow.log_params(params)
        try:
            yield run
        except Exception as e:
            mlflow.set_tags({"run_status": "FAILED", "failure_summary": str(e)[:480]})
            mlflow.log_text(f"{type(e).__name__}: {e}", "error_summary.txt")
            raise
        else:
            if mlflow.active_run().data.tags.get("run_status") == "RUNNING":
                mlflow.set_tag("run_status", "COMPLETED")
            mlflow.set_tag("ended_at_kst", datetime.now(KST).isoformat())


def finish(*, verdict: str, limitation: str = "", run_status: str = "COMPLETED",
           authority_status: str | None = None) -> None:
    """run 종료 직전 결과 태그를 확정한다."""
    if verdict not in VERDICTS:
        raise ContractViolation(f"verdict: {verdict}")
    if run_status not in RUN_STATUS:
        raise ContractViolation(f"run_status: {run_status}")
    t = {"verdict": verdict, "run_status": run_status}
    if limitation:
        t["limitation_summary"] = limitation[:480]
        mlflow.log_text(limitation, "limitation_summary.txt")
    if authority_status:
        if authority_status not in AUTHORITY:
            raise ContractViolation(f"authority_status: {authority_status}")
        t["authority_status"] = authority_status
    mlflow.set_tags(t)


def log_pointer(name: str, path: str, sha: str, bytes_: int | None = None) -> None:
    """Git 밖 대형 raw evidence 는 업로드 대신 pointer 로 남긴다."""
    doc = {"pointer": name, "local_path": path, "sha256": sha, "bytes": bytes_,
           "uploaded": False,
           "note": "대형 raw evidence 는 MLflow 에 업로드하지 않는다. hash + local path pointer 로 대신한다."}
    mlflow.log_text(json.dumps(doc, ensure_ascii=False, indent=1), f"pointers/{name}.json")


if __name__ == "__main__":
    ids = ensure_experiments()
    for k, v in ids.items():
        print(f"{v:>3}  {k:<20} {EXPERIMENTS[k]}")
