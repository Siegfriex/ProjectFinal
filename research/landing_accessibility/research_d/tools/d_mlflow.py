"""D 연구 run을 MLflow에 기록한다.

왜 필요한가: D는 notebook과 script를 계속 만든다. 어떤 입력 스냅샷에서 어떤
코드 SHA로 어떤 숫자가 나왔는지가 run 단위로 남지 않으면, 나중에 "그 수치가
어느 시점 것이냐"를 다시 재구성해야 한다. MLflow는 그 lineage를 붙잡는 용도다.

MLflow는 연구 결론의 권위가 아니다. canonical 산출은 Git의 results/*.json 이고
MLflow는 그것을 가리키는 index다. run 은 idempotent 하게 기록된다
(rq_id + result 파일 sha256 이 같으면 다시 만들지 않는다).

usage:
    d_mlflow.py sync            # results/ 를 스캔해 신규/변경된 RQ만 기록
    d_mlflow.py list            # 기록된 run 요약
"""
from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

import mlflow

TRACKING_URI = "http://127.0.0.1:5000"
EXPERIMENT = "landing_accessibility_D_v21"

RD = Path(__file__).resolve().parents[1]
WT = RD.parents[2]
NB_DIR = RD.parent / "notebooks" / "d_research"
BASE_SHA = "bc0b7a087faf2328cbafdfa9b40bd426c5080d7d"
BRANCH = "claude-d/research-sandbox-v21"

VERDICTS = ("SUPPORTED", "PARTIALLY_SUPPORTED", "REFUTED", "NOT_SUPPORTED",
            "INCONCLUSIVE", "NOT_TESTABLE")
KEY_OK = re.compile(r"[^A-Za-z0-9_\-./: ]")


def sha256(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def git(*args: str) -> str:
    return subprocess.run(["git", *args], cwd=WT, capture_output=True, text=True).stdout.strip()


def flatten_numeric(obj, prefix: str = "", out: dict | None = None) -> dict:
    """중첩 JSON에서 숫자 leaf만 dotted key 로 뽑는다. bool 은 0/1 로."""
    out = {} if out is None else out
    if isinstance(obj, dict):
        for k, v in obj.items():
            flatten_numeric(v, f"{prefix}{k}." if not prefix else f"{prefix}{k}.", out)
    elif isinstance(obj, (int, float)) and not isinstance(obj, bool):
        key = KEY_OK.sub("_", prefix.rstrip("."))[:240]
        if key:
            out[key] = float(obj)
    elif isinstance(obj, bool):
        key = KEY_OK.sub("_", prefix.rstrip("."))[:240]
        if key:
            out[key] = float(obj)
    return out


def parse_verdict(md: Path) -> str:
    if not md.exists():
        return "UNKNOWN"
    head = md.read_text(encoding="utf-8")[:4000]
    for v in sorted(VERDICTS, key=len, reverse=True):
        if v in head:
            return v
    return "UNKNOWN"


def parse_limitation(md: Path) -> str:
    if not md.exists():
        return ""
    txt = md.read_text(encoding="utf-8")
    m = re.search(r"^##+\s*Limitations?\b.*?$(.*?)(?=^##\s|\Z)", txt, re.M | re.S)
    if not m:
        return ""
    body = [ln.strip(" -*0123456789.") for ln in m.group(1).splitlines() if ln.strip()]
    return (body[0] if body else "")[:480]


# RQ -> notebook 매핑. 번호가 1:1이 아니므로 추론하지 않고 명시한다.
NOTEBOOK_MAP = {
    "RQ-D1": "D00_pilot_forensic_reconstruction.ipynb",
}


def discover() -> list[dict]:
    """results/ 에서 RQ 단위 산출을 찾는다. rq_id 는 파일명에서만 뽑는다.

    [D-DEF-06 시정] 이전 정규식 `RQ_(D\\d+)_` 는 숫자 뒤에 `_` 를 요구해
    하위 RQ(RQ_D13A, RQ_D12A, RQ_D6B1 …)와 RF001/RF2/DSUP/PILOT 계열을 전부 놓쳤다.
    36개 산출 중 10개만 색인되고 있었다. prefix 규칙(`<prefix>_FINDINGS.md`)으로 바꾼다.
    """
    import re as _re

    # RQ 산출이 아닌 것 — 관측 테이블·결함기록·방화벽·부모런·사전등록
    SKIP = _re.compile(
        r"^(D_OBSERVATION_TABLE|D_DEF_|D_INPUT_|D_CORPUS_|D_DASHBOARD|D_FACT_"
        r"|PILOT_PREREGISTRATION)|_PARENT_RUN\.json$"
    )

    def rq_id_of(prefix: str) -> str | None:
        if m := _re.fullmatch(r"RQ_(D[0-9A-Za-z]+)", prefix):
            return f"RQ-{m.group(1)}"
        if m := _re.fullmatch(r"RQ_E(\d+[a-z]?)", prefix):
            return f"RQ-E-{m.group(1)}"
        if m := _re.fullmatch(r"(RF001|RF2)_([A-Z])", prefix):
            return f"{m.group(1)}-{m.group(2)}"
        if m := _re.fullmatch(r"DSUP(\d+)", prefix):
            return f"D-SUP-{m.group(1)}"
        if prefix == "PILOT_E":
            return "RQ-D-PILOT-001-E"
        return None

    def prefix_of(name: str) -> str | None:
        stem = name.rsplit(".", 1)[0]
        parts = stem.split("_")
        # 가장 긴 것부터 시도해 `<prefix>_FINDINGS.md` 규칙과 맞는 지점을 찾는다
        for k in range(min(3, len(parts)), 0, -1):
            cand = "_".join(parts[:k])
            if rq_id_of(cand):
                return cand
        return None

    found: dict[str, dict] = {}
    for f in sorted((RD / "results").glob("*.json")):
        if SKIP.search(f.name):
            continue
        prefix = prefix_of(f.name)
        if not prefix:
            continue
        rq = rq_id_of(prefix)
        e = found.setdefault(rq, {
            "rq_id": rq,
            "md": RD / "results" / f"{prefix}_FINDINGS.md",
            "json": None,
        })
        if e["json"] is None:
            e["json"] = f
    return list(found.values())


def sync() -> int:
    mlflow.set_tracking_uri(TRACKING_URI)
    mlflow.set_experiment(EXPERIMENT)
    snap = RD / "INPUT_SNAPSHOT_v21.json"
    snap_sha = sha256(snap) if snap.exists() else "MISSING"
    head = git("rev-parse", "HEAD")
    dirty = bool(git("status", "--porcelain"))

    existing = {}
    exp = mlflow.get_experiment_by_name(EXPERIMENT)
    if exp:
        for r in mlflow.search_runs([exp.experiment_id], output_format="list"):
            existing[(r.data.tags.get("d.rq_id"), r.data.tags.get("d.result_sha256"))] = r.info.run_id

    logged, skipped = [], []
    for item in discover():
        rq, md, js = item["rq_id"], item["md"], item["json"]
        payload = js if js and js.exists() else md
        if not payload.exists():
            continue
        # [D-DEF-07 시정] 완결 게이트. run 은 지울 수 없으므로(덮어쓰기 금지 규약)
        # 아직 쓰이는 중인 산출을 색인하면 빈 run 이 영구히 남는다.
        # D 의 산출 규약은 JSON(최상위 verdict) + FINDINGS.md 둘 다이므로 둘 다 요구한다.
        if js and js.exists():
            try:
                if "verdict" not in json.loads(js.read_text()):
                    skipped.append(f"{rq}(미완: verdict 없음)")
                    continue
            except Exception:
                skipped.append(f"{rq}(미완: JSON 파싱 실패)")
                continue
            if not md.exists():
                skipped.append(f"{rq}(미완: FINDINGS.md 없음)")
                continue
        rsha = sha256(payload)
        if (rq, rsha) in existing:
            skipped.append(rq)
            continue
        metrics = {}
        if js and js.exists():
            try:
                metrics = flatten_numeric(json.loads(js.read_text(encoding="utf-8")))
            except Exception:
                metrics = {}
        nb_name = NOTEBOOK_MAP.get(rq)
        nb = (NB_DIR / nb_name) if nb_name and (NB_DIR / nb_name).exists() else None
        with mlflow.start_run(run_name=f"{rq}") as run:
            mlflow.set_tags({
                "d.rq_id": rq,
                "d.result_sha256": rsha,
                "d.plane": "D_INDEPENDENT_RESEARCH_SANDBOX",
                "d.authority": "NON_AUTHORITATIVE",
                "d.branch": BRANCH,
                "d.head_sha": head,
                "d.base_sha": BASE_SHA,
                "d.worktree_dirty": str(dirty),
                "d.input_snapshot_sha256": snap_sha,
                "d.verdict": parse_verdict(md),
                "d.production_modified": "false",
                "d.labels_produced": "false",
                "d.holdout_accessed": "false",
                "d.limitation": parse_limitation(md),
            })
            mlflow.log_params({
                "rq_id": rq,
                "base_sha": BASE_SHA[:12],
                "head_sha": head[:12],
                "input_snapshot_sha256": snap_sha[:16],
                "verdict": parse_verdict(md),
                "notebook": nb.name if nb else "none",
            })
            if metrics:
                mlflow.log_metrics(metrics)
            for f in (md, js, snap):
                if f and f.exists():
                    mlflow.log_artifact(str(f), artifact_path="result")
            if nb:
                mlflow.log_artifact(str(nb), artifact_path="notebook")
            for tool in (RD / "tools").glob("*.py"):
                mlflow.log_artifact(str(tool), artifact_path="code")
            logged.append((rq, run.info.run_id, len(metrics)))

    for rq, rid, n in logged:
        print(f"logged  {rq}  run={rid}  metrics={n}")
    for rq in skipped:
        print(f"skipped {rq}  (동일 result sha 이미 기록됨)")
    print(f"\nMLflow UI: {TRACKING_URI}  experiment={EXPERIMENT}")
    return 0


def list_runs() -> int:
    mlflow.set_tracking_uri(TRACKING_URI)
    exp = mlflow.get_experiment_by_name(EXPERIMENT)
    if not exp:
        print("experiment 없음")
        return 1
    for r in mlflow.search_runs([exp.experiment_id], output_format="list"):
        t = r.data.tags
        print(f"{t.get('d.rq_id','?'):<8} {t.get('d.verdict','?'):<22} "
              f"metrics={len(r.data.metrics):<4} head={t.get('d.head_sha','')[:8]} run={r.info.run_id}")
    return 0


MLFLOW_STORE = Path("/home/sieg/projects-wsl/ProjectFinal/artifacts/mlflow_d")


def manifest() -> int:
    """03 §9 — Git 밖 artifact 는 Git 안 manifest 로 노출한다.

    MLflow store 는 .gitignore 된 artifacts/ 아래에 있으므로, 여기서 파일 단위
    hash 목록을 만들어 D branch 에 commit 한다. "로컬에 있다"는 문장만으로
    인계하지 않는다.
    """
    mlflow.set_tracking_uri(TRACKING_URI)
    exp = mlflow.get_experiment_by_name(EXPERIMENT)
    runs = []
    if exp:
        for r in mlflow.search_runs([exp.experiment_id], output_format="list"):
            runs.append({
                "run_id": r.info.run_id,
                "rq_id": r.data.tags.get("d.rq_id"),
                "verdict": r.data.tags.get("d.verdict"),
                "head_sha": r.data.tags.get("d.head_sha"),
                "input_snapshot_sha256": r.data.tags.get("d.input_snapshot_sha256"),
                "result_sha256": r.data.tags.get("d.result_sha256"),
                "metric_count": len(r.data.metrics),
                "start_time": r.info.start_time,
            })
    files = [f for f in MLFLOW_STORE.rglob("*") if f.is_file()]
    doc = {
        "manifest_id": "D-MLFLOW-RETENTION-MANIFEST",
        "root_path": str(MLFLOW_STORE),
        "git_tracked": False,
        "read_only": False,
        "note": "MLflow 는 D 연구의 index 이지 권위가 아니다. canonical 산출은 Git 의 results/*.json 이다.",
        "tracking_uri": TRACKING_URI,
        "experiment": EXPERIMENT,
        "producer_sha": git("rev-parse", "HEAD"),
        "created_at_kst": subprocess.run(["date", "-Iseconds"], env={"TZ": "Asia/Seoul", "PATH": "/usr/bin:/bin"},
                                         capture_output=True, text=True).stdout.strip(),
        "artifact_count": len(files),
        "bytes": sum(f.stat().st_size for f in files),
        "runs": runs,
        "files": {str(f.relative_to(MLFLOW_STORE)): {"sha256": sha256(f), "bytes": f.stat().st_size}
                  for f in sorted(files) if f.stat().st_size < 50_000_000},
    }
    out = RD / "MLFLOW_RETENTION_MANIFEST.json"
    out.write_text(json.dumps(doc, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"wrote {out}")
    print(f"runs={len(runs)} files={len(files)} bytes={doc['bytes']:,}")
    return 0


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "sync"
    raise SystemExit({"sync": sync, "list": list_runs, "manifest": manifest}.get(cmd, sync)())
