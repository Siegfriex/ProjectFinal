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
    "LA_04_DIAGNOSTIC_PILOT_RESEARCH":
        "RQ-D-PILOT-001 — diagnostic real evidence sufficiency. old/new input SHA 병기 필수",
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
    return holdout_value_from_scan(doc)


def holdout_value_from_scan(doc: dict) -> str:
    """[D-DEF-86] `verdict != PASS` 를 곧장 `"true"` 로 쓰던 것을 가른다.

    현재 FAIL 3 건은 전부 **control 축의 경로 참조**다(원문 경로는 적지 않는다,
    `D-DEF-60`) —
    **holdout 과 다른 축**이다. 그것을 `holdout_accessed=true` 로 쓰면
    **다른 축의 실패가 holdout 접근으로 보고된다.**

    그리고 이 스캐너는 **정적 산출물 스캔**이다(문서의 `residual_risk` 가 그렇게
    적는다) — **참조를 볼 수 있지 접근을 볼 수 없다.** 그래서 가장 강한 정직한
    값은 `"true"` 가 아니라 `SCAN_FLAGGED_HOLDOUT_REFERENCE` 다.
    """
    if doc.get("verdict") == "PASS":
        return "false"
    hits = [x for x in (doc.get("violations") or [])
            if x.get("severity") == "FAIL"
            and "HOLDOUT" in (f"{x.get('reference','')} {x.get('denied_pattern','')} "
                              f"{x.get('file','')}").upper()]
    if hits:
        return "SCAN_FLAGGED_HOLDOUT_REFERENCE"
    # 스캔이 돌았고 PASS 가 아니지만 **holdout 축의 FAIL 은 없다**
    return "UNVERIFIED_SCAN_NOT_PASS"


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


# [D-DEF-86] 호출자가 덮으면 안 되는 tag — **측정기가 내는 값**이다(R41).
PROTECTED_TAGS = frozenset({
    "project", "plane", "authority_status",
    "holdout_accessed", "holdout_verification",
    "self_approved", "production_modified", "labels_produced",
    "head_sha", "base_sha", "git_branch", "worktree_dirty",
    "input_snapshot_sha", "evidence_manifest_sha", "result_sha", "code_sha",
    "started_at_kst",
})


class ContractViolation(RuntimeError):
    pass


def validate_args(*, experiment: str, plane: str, claim_kind: str, split: str,
                  authority_status: str | None) -> str:
    """`research_run` 의 진입 검증 — **MLflow 를 건드리지 않는다.**

    [D-DEF-85] 이 계약 모듈에는 대조군이 없었다. 검증부가 `research_run` 안에
    박혀 있어 **run 을 열지 않고는 시험할 수 없었고**, 대조군을 만들려면 서버에
    쓰레기 run 을 남겨야 했다. 순수 함수로 떼면 둘 다 피한다.
    반환값은 확정된 `authority` 다.
    """
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
    return authority


# [D-DEF-89] 종료 시 `run_status` 를 무엇으로 둘지 — **순수 함수라 run 없이 시험된다.**
# 이전 판정은 `== "RUNNING"` 하나였고, tag 를 못 읽으면(`None`) 갱신을 건너뛰어
# **끝난 run 이 RUNNING 으로 남았다.** 미확정(`None`)도 갱신 대상이다.
_TERMINAL_STATUS = ("COMPLETED", "FAILED", "ABSTAINED", "INVALIDATED", "SUPERSEDED")


def closing_status(current: str | None) -> str | None:
    """정상 종료 시 새로 쓸 `run_status`. 덮지 말아야 하면 `None`."""
    if current in _TERMINAL_STATUS:
        return None                 # 호출자가 명시한 종결 상태는 덮지 않는다
    return "COMPLETED"              # `RUNNING` 도, **읽지 못한 `None` 도** 갱신한다


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
    authority = validate_args(experiment=experiment, plane=plane, claim_kind=claim_kind,
                              split=split, authority_status=authority_status)

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
        # [D-DEF-86] `update` 는 **필수 tag 를 덮어쓸 수 있었다.** 특히
        # `holdout_accessed` 는 "self-tag 가 아니라 방화벽 결과" 라고 적혀 있는데
        # 호출자가 덮어쓸 수 있었다 — **보장이 강제되지 않았다.**
        clash = sorted(set(extra_tags) & PROTECTED_TAGS)
        if clash:
            raise ContractViolation(
                f"extra_tags 가 기계 유래 tag 를 덮으려 한다: {clash} — "
                f"이 값들은 측정기가 낸다(R41)")
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
            # [D-DEF-89] 조건이 `active_run().data.tags` — **클라이언트 스냅샷**을 읽어서
            # 열 때 건 tag 가 안 보이면 갱신을 건너뛴다. 그런데 `ended_at_kst` 는
            # **무조건** 찍히므로 "끝났는데 `run_status=RUNNING`" 인 run 이 남는다 —
            # 실측 4건이 그렇다. 서버에서 다시 읽고, 판단은 순수 함수로 뗀다.
            try:
                cur = mlflow.get_run(run.info.run_id).data.tags.get("run_status")
            except Exception:                       # noqa: BLE001
                cur = None                          # 못 읽으면 미확정으로 본다
            nxt = closing_status(cur)
            if nxt:
                mlflow.set_tag("run_status", nxt)
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




def controls() -> dict:
    """[D-DEF-85] 계약 가드가 아직 막고 있는가 — **run 을 열지 않고** 잰다.

    `validate_args` 만 부른다. MLflow 서버에 아무것도 쓰지 않는다 —
    대조군이 쓰레기 run 을 남기면 그 자체가 회계를 오염시킨다.
    """
    rows = []
    ok_args = dict(experiment=next(iter(EXPERIMENTS)), plane="D",
                   claim_kind="ANALYSIS", split="none", authority_status=None)

    def case(name, args, should_raise=True):
        try:
            validate_args(**args)
            raised = False
        except ContractViolation:
            raised = True
        rows.append({"case": name, "raised": raised,
                     "expectation": "must_flag" if should_raise else "must_not_flag",
                     "ok": raised == should_raise})

    case("정상 인자는 통과한다", ok_args, should_raise=False)
    case("모르는 experiment 는 막힌다", ok_args | {"experiment": "__no_such__"})
    case("plane 은 A|B|C|D 만", ok_args | {"plane": "Z"})
    case("claim_kind enum 밖은 막힌다", ok_args | {"claim_kind": "GUESS"})
    case("split enum 밖은 막힌다", ok_args | {"split": "train"})
    case("authority_status enum 밖은 막힌다", ok_args | {"authority_status": "TRUSTED"})
    case("**A 아닌 평면은 DECISION 을 못 쓴다**",
         ok_args | {"plane": "D", "authority_status": "DECISION"})
    case("A 는 DECISION 을 쓸 수 있다",
         ok_args | {"plane": "A", "authority_status": "DECISION"}, should_raise=False)

    # [D-DEF-89] 종료 상태 판정
    def ccase(name, cur, want):
        got = closing_status(cur)
        rows.append({"case": f"[종료] {name}", "got": got, "want": want,
                     "expectation": "must_flag" if want else "must_not_flag",
                     "ok": got == want})

    ccase("RUNNING 은 COMPLETED 로 닫힌다", "RUNNING", "COMPLETED")
    ccase("**읽지 못한 None 도 닫힌다** — 이것이 빠져서 4건이 RUNNING 으로 남았다",
          None, "COMPLETED")
    ccase("ABSTAINED 는 덮지 않는다", "ABSTAINED", None)
    ccase("SUPERSEDED 는 덮지 않는다", "SUPERSEDED", None)
    ccase("FAILED 는 덮지 않는다", "FAILED", None)
    rows.append({"case": "[종료] 종결 상태 목록이 계약 enum 안에 있다",
                 "expectation": "must_not_flag",
                 "ok": set(_TERMINAL_STATUS).issubset(set(RUN_STATUS))})

    # [D-DEF-86] holdout 값 매핑 — **다른 축의 FAIL 을 holdout 접근으로 쓰지 않는다**
    def hcase(name, doc, want):
        got = holdout_value_from_scan(doc)
        rows.append({"case": f"[holdout] {name}", "got": got, "want": want,
                     "expectation": "must_flag" if want != "false" else "must_not_flag",
                     "ok": got == want})

    hcase("PASS 면 false", {"verdict": "PASS"}, "false")
    # [D-DEF-87] **대조군이 실제 금지 경로를 쓸 필요가 없다.** 처음엔 진짜 경로
    # 문자열을 넣었고 방화벽이 그것을 새 WARN 토큰으로 잡았다 — `D-DEF-60` 재발
    # (감시 도구가 대상 이름을 원문으로 기록하면 스스로 위반이 된다).
    # 이 분기가 보는 것은 "reference 에 HOLDOUT 이 없다" 뿐이므로 중립 문자열로 족하다.
    hcase("**holdout 이 아닌 축의 FAIL 은 holdout 이 아니다**",
          {"verdict": "FAIL", "violations": [
              {"severity": "FAIL", "reference": "OTHER_AXIS/some/path.py",
               "file": "tools/some_tool.py"}]},
          "UNVERIFIED_SCAN_NOT_PASS")
    # [D-DEF-87] 이 분기는 `reference` 에 `HOLDOUT` 이 들어 있는지만 본다 —
    # **실제 보호 산출물의 파일명을 fixture 에 쓸 이유가 없다.** 처음엔 그 이름을
    # 그대로 썼고 방화벽이 금지 토큰으로 잡았다(`D-DEF-60`: 감시 도구가 대상 이름을
    # 원문으로 기록하면 스스로 위반이 된다). 쪼개서 회피하지 않고 **다른 이름**을 쓴다.
    hcase("holdout 참조 FAIL 은 그렇게 적는다",
          {"verdict": "FAIL", "violations": [
              {"severity": "FAIL", "reference": "artifacts/holdout_sample.csv", "file": "x.py"}]},
          "SCAN_FLAGGED_HOLDOUT_REFERENCE")
    hcase("**WARN 등급 holdout 언급은 FAIL 로 올리지 않는다**",
          {"verdict": "FAIL", "violations": [
              {"severity": "WARN", "reference": "holdout_sample", "file": "nb.ipynb"},
              {"severity": "FAIL", "reference": "OTHER_AXIS/x", "file": "y.py"}]},
          "UNVERIFIED_SCAN_NOT_PASS")
    rows.append({"case": "[holdout] **`true` 는 이제 나오지 않는다** — 정적 스캔은 접근을 못 본다",
                 "expectation": "must_not_flag",
                 "ok": all(holdout_value_from_scan(d) != "true" for d in (
                     {"verdict": "PASS"},
                     {"verdict": "FAIL", "violations": []},
                     {"verdict": "FAIL", "violations": [
                         {"severity": "FAIL", "reference": "holdout_sample"}]}))})

    # [D-DEF-86] extra_tags 가 기계 유래 tag 를 덮지 못하는가
    rows.append({"case": "[보호] `holdout_accessed` 를 extra_tags 로 덮으면 막힌다",
                 "expectation": "must_flag",
                 "ok": "holdout_accessed" in PROTECTED_TAGS})
    rows.append({"case": "[보호] 보호 목록이 비어 있지 않다 — 빈 목록은 아무것도 막지 않는다",
                 "expectation": "must_not_flag", "ok": len(PROTECTED_TAGS) > 0})
    rows.append({"case": "[보호] 보호 목록이 필수 tag 를 벗어나지 않는다",
                 "expectation": "must_not_flag",
                 "ok": PROTECTED_TAGS.issuperset({"holdout_accessed", "self_approved",
                                                  "production_modified", "labels_produced"})})

    # 계약 상수가 비면 검사가 통째로 무의미해진다 — 빈 enum 은 통과가 아니다
    rows.append({"case": "enum 상수가 비어 있지 않다 — 빈 enum 은 모든 값을 막거나 통과시킨다",
                 "expectation": "must_not_flag",
                 "ok": all(len(x) > 0 for x in (CLAIM_KINDS, SPLITS, AUTHORITY,
                                                EXPERIMENTS, RUN_STATUS, VERDICTS))})
    ok = all(r["ok"] for r in rows)
    return {"verdict": "PASS" if ok else "FAIL", "n": len(rows),
            "must_flag": sum(1 for r in rows if r["expectation"] == "must_flag"),
            "must_not_flag": sum(1 for r in rows if r["expectation"] == "must_not_flag"),
            "failed": [r["case"] for r in rows if not r["ok"]],
            "MLflow_를_건드리지_않는다": "run 을 열지 않는다 — 대조군이 회계를 오염시키면 안 된다",
            "cases": rows}


if __name__ == "__main__":
    # [D-DEF-85] `__main__` 이 둘이었다. 뒤엣것을 붙이자 **대조군을 돌릴 때마다
    # `ensure_experiments()` 가 같이 돌아 MLflow 에 쓰기 경로를 열었다.**
    # 기본은 대조군(쓰지 않는다). 실험 보장은 `--ensure` 로 **명시할 때만** 한다.
    import json as _j
    import sys as _sys
    if "--ensure" in _sys.argv:
        _ids = ensure_experiments()
        for _k, _v in _ids.items():
            print(f"{_v:>3}  {_k:<20} {EXPERIMENTS[_k]}")
        raise SystemExit(0)
    _c = controls()
    print(_j.dumps(_c, ensure_ascii=False, indent=1))
    raise SystemExit(0 if _c["verdict"] == "PASS" else 3)
