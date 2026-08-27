"""D 연구 산출 → 계약 준수 MLflow run 동기화.

results/ 의 RQ 산출과 AGENT_RUN_REGISTRY.jsonl 을 읽어 주제 experiment 에
parent run 을 만든다. 멱등: 같은 result_sha 면 run 을 다시 만들지 않는다.
결과를 덮어쓰지 않는다 — 결과가 바뀌면 새 run 이다.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import mlflow

sys.path.insert(0, str(Path(__file__).resolve().parent))
import mlflow_contract as C  # noqa: E402

RD = C.RD
NB_DIR = RD.parent / "notebooks" / "d_research"

# RQ -> (experiment, hypothesis_id, objective, notebook, dataset_grain)
RQ_SPEC = {
    "RQ-D1": ("LA_07_COLLECTION", "H-D1-PILOT-ANATOMY",
              "E001 파일럿이 어느 지점에서 무엇을 잃었는지 raw 에서 재구성",
              "D00_pilot_forensic_reconstruction.ipynb",
              "observation dir | web_target_group | mart row"),
    "RQ-D3A": ("LA_03_RF_MAPPING", "H-D3A-L0-FEATURE-SEPARABILITY",
               "L0 numeric feature 가 archetype prior 를 어느 정도 되찾는가 (진단)",
               None, "target (in_mart==1 & probe_present==1)"),
    "RQ-D8": ("LA_07_COLLECTION", "H-D8-CAP-ARCHETYPE-BIAS",
              "l0_probe cap 절단이 archetype 에 편향돼 ExcessDepth baseline 을 왜곡하는가",
              None, "target / observation 병기"),
    "RQ-D9": ("LA_07_COLLECTION", "H-D9-QUALITY-PROXY",
              "관측품질의 대리변수는 무엇이 될 수 있고 무엇이 될 수 없는가",
              None, "observation (probe_present==1)"),
    "RQ-D10": ("LA_07_COLLECTION", "H-D10-SLOT-TIME-MISMATCH",
               "evidence slot 간 시점 불일치를 관측단위 지표로 정량화할 수 있는가",
               None, "observation (58 probe-complete)"),
}
TICKET = {"RQ-D8": "T-B-RQ-D-001", "RQ-D9": "T-B-RQ-D-001", "RQ-D10": "T-B-RQ-D-001"}
KEY_OK = re.compile(r"[^A-Za-z0-9_\-./: ]")


def flatten_numeric(obj, prefix="", out=None, depth=0):
    out = {} if out is None else out
    if depth > 6:
        return out
    if isinstance(obj, dict):
        for k, v in obj.items():
            flatten_numeric(v, f"{prefix}{k}.", out, depth + 1)
    elif isinstance(obj, bool):
        k = KEY_OK.sub("_", prefix.rstrip("."))[:240]
        if k:
            out[k] = float(obj)
    elif isinstance(obj, (int, float)):
        k = KEY_OK.sub("_", prefix.rstrip("."))[:240]
        if k:
            out[k] = float(obj)
    return out


def parse_verdict(md: Path, data: dict | None = None) -> str:
    """verdict 는 machine-readable JSON 을 먼저 믿고, 없으면 md 의 VERDICT 표기를 읽는다."""
    if data:
        v = data.get("verdict") or data.get("VERDICT")
        if isinstance(v, str) and v.strip().upper() in C.VERDICTS:
            return v.strip().upper()
    if not md.exists():
        return "PENDING"
    txt = md.read_text(encoding="utf-8")
    # "VERDICT" 라는 단어 근처의 값을 우선한다 (문서 어디에 있든).
    for m in re.finditer(r"VERDICT[^A-Za-z]{0,40}([A-Z_]{6,20})", txt):
        if m.group(1) in C.VERDICTS:
            return m.group(1)
    for v in sorted(C.VERDICTS, key=len, reverse=True):
        if v in txt:
            return v
    return "PENDING"


def parse_limitation(md: Path) -> str:
    if not md.exists():
        return ""
    txt = md.read_text(encoding="utf-8")
    m = re.search(r"^#+\s*Limitations?\b.*?$(.*?)(?=^#+\s|\Z)", txt, re.M | re.S)
    if not m:
        return ""
    body = [ln.strip(" -*#0123456789.") for ln in m.group(1).splitlines() if ln.strip()]
    return " / ".join(body[:3])[:1500]


def agent_registry() -> dict[str, dict]:
    p = RD / "AGENT_RUN_REGISTRY.jsonl"
    if not p.exists():
        return {}
    out = {}
    for line in p.read_text(encoding="utf-8").splitlines():
        if line.strip():
            r = json.loads(line)
            out[r["rq_id"]] = r
    return out


def discover() -> dict[str, dict]:
    found: dict[str, dict] = {}
    for f in sorted((RD / "results").glob("RQ_D*")):
        m = re.match(r"RQ_(D\d+A?)_", f.name)
        if not m:
            continue
        rq = f"RQ-{m.group(1)}"
        e = found.setdefault(rq, {"rq_id": rq, "md": RD / "results" / f"RQ_{m.group(1)}_FINDINGS.md",
                                  "json": None, "figures": []})
        if f.suffix == ".json" and e["json"] is None:
            e["json"] = f
    for rq, e in found.items():
        num = rq.split("-")[1]
        e["figures"] = sorted((RD / "figures").glob(f"RQ_{num}_*"))
    return found


def supersede_pending() -> int:
    """verdict 가 PENDING 인 채로 남은 D run 을 SUPERSEDED 로 닫는다.

    계약상 결과를 덮어쓰지 않는다. 파서 결함으로 잘못 열린 run 은 수정하지 않고
    SUPERSEDED 로 표시한 뒤 새 run 을 만든다.
    """
    mlflow.set_tracking_uri(C.TRACKING_URI)
    n = 0
    client = mlflow.MlflowClient()
    for name in C.EXPERIMENTS:
        exp = mlflow.get_experiment_by_name(name)
        if not exp:
            continue
        for r in mlflow.search_runs([exp.experiment_id], output_format="list"):
            t = r.data.tags
            if t.get("plane") == "D" and t.get("verdict") == "PENDING" and t.get("run_status") != "SUPERSEDED":
                client.set_tag(r.info.run_id, "run_status", "SUPERSEDED")
                client.set_tag(r.info.run_id, "superseded_reason",
                               "verdict parser defect — 결과 변경 아님. 동일 result_sha 로 새 run 재생성")
                n += 1
    print(f"superseded {n} PENDING runs")
    return n


def existing_result_shas() -> set[tuple[str, str]]:
    mlflow.set_tracking_uri(C.TRACKING_URI)
    seen = set()
    for name in C.EXPERIMENTS:
        exp = mlflow.get_experiment_by_name(name)
        if not exp:
            continue
        for r in mlflow.search_runs([exp.experiment_id], output_format="list"):
            t = r.data.tags
            if t.get("run_status") == "SUPERSEDED":
                continue
            if t.get("hypothesis_id") and t.get("result_sha"):
                seen.add((t.get("mlflow.runName", ""), t["result_sha"]))
    return seen


def main() -> int:
    C.ensure_experiments()
    if "--supersede-pending" in sys.argv:
        supersede_pending()
    seen = existing_result_shas()
    reg = agent_registry()
    logged, skipped = [], []

    for rq, item in sorted(discover().items()):
        if rq not in RQ_SPEC:
            print(f"skip {rq}: RQ_SPEC 미등록")
            continue
        exp, hyp, objective, nb, grain = RQ_SPEC[rq]
        md, js = item["md"], item["json"]
        payload = js if js and js.exists() else md
        if not payload.exists():
            continue
        rsha = C.sha256_file(payload)
        if (rq, rsha) in seen:
            skipped.append(rq)
            continue

        data = {}
        if js and js.exists():
            try:
                data = json.loads(js.read_text(encoding="utf-8"))
            except Exception:
                data = {}
        metrics = flatten_numeric(data)
        n_obs = data.get("n") or data.get("evidence", {}).get("observation_dirs") or 0
        a = reg.get(rq, {})

        with C.research_run(
            experiment=exp, run_name=rq, plane="D",
            objective=objective, method=(a.get("label") or "independent recomputation from raw"),
            dataset_grain=grain, n_expected=59, n_observed=n_obs,
            hypothesis_id=hyp, claim_kind="ANALYSIS",
            ticket_id=TICKET.get(rq, "NONE"), phase="I1",
            agent_id="D", subagent_id=(f"worker/{rq}" if rq in reg else "D-self"),
            split="none", result_path=payload,
            model_or_rule_version="D-v2.1",
            extra_params={"notebook": nb or "none",
                          "figures": len(item["figures"]),
                          "result_file": payload.name},
            extra_tags={"rq_id": rq, "topic_experiment": exp},
        ):
            if metrics:
                mlflow.log_metrics(metrics)
            if a:
                mlflow.log_metrics({
                    "subagent.tokens": float(a.get("subagent_tokens") or 0),
                    "subagent.tool_uses": float(a.get("tool_uses") or 0),
                    "subagent.duration_min": float(a.get("duration_min") or 0),
                    "subagent.owned_files": float(len(a.get("owned_files", []))),
                })
                mlflow.log_text(json.dumps(a, ensure_ascii=False, indent=1), "agent_run_record.json")
            for f in (md, js):
                if f and f.exists():
                    mlflow.log_artifact(str(f), artifact_path="result")
            for f in item["figures"]:
                mlflow.log_artifact(str(f), artifact_path="figures")
            if nb and (NB_DIR / nb).exists():
                mlflow.log_artifact(str(NB_DIR / nb), artifact_path="notebook")
            snap = RD / "INPUT_SNAPSHOT_v21.json"
            if snap.exists():
                mlflow.log_artifact(str(snap), artifact_path="manifest")
            C.log_pointer("e001_raw_evidence",
                          str(C.REPO / ".agent_worktrees/claude_b_e001_worker_0*/artifacts/e001_w0*/evidence"),
                          C.evidence_manifest_sha(), 753676839)
            C.finish(verdict=parse_verdict(md, data), limitation=parse_limitation(md),
                     authority_status="NON_CANONICAL")
            logged.append((rq, exp, len(metrics), parse_verdict(md, data)))

    for rq, exp, n, v in logged:
        print(f"logged  {rq:<8} → {exp:<18} metrics={n:<4} verdict={v}")
    for rq in skipped:
        print(f"skipped {rq:<8} (동일 result_sha 기록됨)")
    print(f"\nMLflow: {C.TRACKING_URI}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
