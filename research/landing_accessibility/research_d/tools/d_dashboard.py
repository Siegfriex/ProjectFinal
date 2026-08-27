"""D_DASHBOARD — Research Director 감시 대시보드.

한 화면에서 A/B/C/D 네 plane의 운영 상태 · 데이터 분모 사슬 · 세 축(A/B/C)의 가용성 ·
D 연구 큐 · C 검증 결과를 본다.

핵심 설계 원칙 세 가지:

1. **없는 값을 만들지 않는다.** 계산 불가는 NOT_AVAILABLE / NOT_EVALUATED / NONE_YET 로
   명시하고 왜 없는지 한 줄을 붙인다. 이 대시보드의 가치는 "무엇이 아직 없는지"를
   정직하게 보여주는 데 있다. 0행을 "0% 실패"로 읽히게 두지 않는다.
2. **모든 수에 grain과 분모를 붙인다.** "59"가 아니라 "59 attempted targets".
3. **MLflow는 truth가 아니다.** 각 수치에 출처 계층(T1~T5)을 붙인다.

    T1 raw artifact / runtime evidence / exact code SHA
    T2 독립 재현계산 (D가 raw에서 직접 다시 센 값)
    T3 frozen definition / codebook / schema / frozen mart (hash 고정)
    T4 accepted SSOT / decision / agent bus 기록
    T5 MLflow metadata / prose / agent narrative   ← 가장 약함

usage:  .venv/bin/python research_d/tools/d_dashboard.py
        (인자 없음, 재실행 가능. 실행할 때마다 최신 상태로 갱신된다.)

산출: results/D_DASHBOARD.json (기계용) · results/D_DASHBOARD.md (사람용)
      + MLflow LA_10_RESEARCH_D 에 스냅샷 run
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
import traceback
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path

RD = Path(__file__).resolve().parents[1]
WT = RD.parents[2]
REPO = Path("/home/sieg/projects-wsl/ProjectFinal")
BUS = REPO / ".agent_bus/landing_v2"
MART = REPO / ".agent_worktrees/claude_b_analysis_current/artifacts/e001_real_marts"
RESULTS = RD / "results"
KST = timezone(timedelta(hours=9))

TRACKING_URI = "http://127.0.0.1:5000"

# 대시보드가 exact SHA 로 추적하는 브랜치. branch name 으로 상태를 주장하지 않는다.
TRACKED_BRANCHES = [
    ("A", "control/landing-orchestrator"),
    ("B", "claude-b/clean0-v21"),
    ("B", "claude-b/analysis-current"),
    ("B", "claude-b/w1-guard-wiring"),
    ("B", "claude-b/w2-rf-detector"),
    ("B", "claude-b/w3-kwcag"),
    ("B", "claude-b/w4-axisc-mart"),
    ("C", "claude-c/assurance-v21"),
    ("C", "claude-c/assurance-current"),
    ("D", "claude-d/research-sandbox-v21"),
    ("-", "research/landing-accessibility-main"),
    ("-", "agent/landing-v2-exec"),
]

NA = "NOT_AVAILABLE"


# ─────────────────────────────────────────────────────────────── helpers ──

def sha256_file(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def load_json(p: Path):
    return json.loads(p.read_text(encoding="utf-8"))


def read_only_git(*args: str, timeout: int = 60) -> str:
    """읽기 전용 git 만 실행한다. 저장소 상태를 바꾸는 명령은 이 함수를 통과하지 못한다."""
    allowed = {"ls-remote", "rev-parse", "log", "status", "show"}
    if args[0] not in allowed:
        raise RuntimeError(f"read-only git only, got: {args[0]}")
    r = subprocess.run(["git", *args], cwd=WT, capture_output=True, text=True, timeout=timeout)
    return r.stdout.strip()


def section(fn):
    """섹션 하나가 실패해도 대시보드 전체는 산출된다."""
    def wrapped(*a, **kw):
        try:
            out = fn(*a, **kw)
            out.setdefault("section_status", "OK")
            return out
        except Exception as e:                       # noqa: BLE001 — 의도적 광역 포획
            return {"section_status": f"ERROR: {type(e).__name__}: {e}",
                    "traceback": traceback.format_exc()[-1200:]}
    wrapped.__name__ = fn.__name__
    return wrapped


def n(value, grain: str, denom=None, denom_grain: str | None = None, tier: str = "T2"):
    """모든 수에 grain·분모·출처계층을 붙여 담는다."""
    d = {"value": value, "grain": grain, "tier": tier}
    if denom is not None:
        d["denominator"] = denom
        d["denominator_grain"] = denom_grain or grain
    return d


def fmt(x) -> str:
    """n() 딕셔너리를 표 셀 하나로 만든다."""
    if not isinstance(x, dict) or "value" not in x:
        return str(x)
    v = x["value"]
    if isinstance(v, float):
        v = f"{v:.4g}"
    s = f"{v} {x['grain']}"
    if "denominator" in x:
        s = f"{v} / {x['denominator']} {x['denominator_grain']}"
    return s


def unavailable(kind: str, why: str, tier: str = "T1") -> dict:
    return {"value": kind, "grain": "-", "tier": tier, "why_absent": why}


# frozen mart 의 불리언 필드는 JSON bool 이 아니라 **문자열 "0"/"1"** 로 저장돼 있다.
# 파이썬에서 "0" 은 truthy 이므로 `if row["endpoint_reached"]` 로 세면 31/31 이 나온다.
# 그 오류가 실제로 이 대시보드 첫 실행에서 발생했다. 모든 불리언 판정은 이 함수를 통과한다.
_TRUE = {"1", "true", "True", "TRUE", "yes", "Y", 1, True}
_FALSE = {"0", "false", "False", "FALSE", "no", "N", 0, False}


def as_bool(v):
    """mart 의 문자열 불리언을 안전하게 해석한다. 해석 불가는 None."""
    if v is None:
        return None
    if v in _TRUE:
        return True
    if v in _FALSE:
        return False
    return None


def count_true(rows, field) -> int:
    return sum(1 for r in rows if as_bool(r.get(field)) is True)


# ─────────────────────────────────────────────────── MLflow (읽기 전용) ──

def mlflow_runs() -> tuple[list, dict]:
    import mlflow
    from mlflow.tracking import MlflowClient
    mlflow.set_tracking_uri(TRACKING_URI)
    c = MlflowClient()
    exps = {e.experiment_id: e.name for e in c.search_experiments()}
    runs = mlflow.search_runs(list(exps), output_format="list", max_results=5000)
    return runs, exps


# ────────────────────────────────────────────────────── 1. 운영 상태 ──

@section
def sec_ops(runs, exps) -> dict:
    out: dict = {"summary": ""}

    # --- A/B/C/D active runs (T5: MLflow metadata) ---
    active_tag = Counter()
    active_lifecycle = Counter()
    running_detail = []
    for r in runs:
        t = r.data.tags
        plane = t.get("plane") or "UNTAGGED"
        if t.get("run_status") == "RUNNING":
            active_tag[plane] += 1
        if r.info.status == "RUNNING":
            active_lifecycle[plane] += 1
        if t.get("run_status") == "RUNNING" or r.info.status == "RUNNING":
            running_detail.append({
                "experiment": exps.get(r.info.experiment_id),
                "run_name": r.info.run_name, "run_id": r.info.run_id,
                "plane": plane, "tag_run_status": t.get("run_status"),
                "lifecycle_status": r.info.status,
                "rq_id": t.get("rq_id"), "agent": f"{t.get('agent_id')}/{t.get('subagent_id')}",
            })
    out["active_runs_by_plane"] = {
        p: n(active_tag.get(p, 0), "MLflow runs with tag run_status=RUNNING",
             denom=len(runs), denom_grain="total MLflow runs", tier="T5")
        for p in ("A", "B", "C", "D")}
    out["active_runs_untagged_plane"] = n(
        active_tag.get("UNTAGGED", 0) + sum(v for k, v in active_lifecycle.items() if k == "UNTAGGED"),
        "runs with no plane tag (계약 미적용 run)", tier="T5")
    out["active_runs_detail"] = running_detail
    out["active_runs_caveat"] = ("run_status 는 tag 이므로 프로세스가 죽어도 RUNNING 으로 남는다. "
                                 "이것은 프로세스 생존 증거가 아니라 '누가 run 을 닫지 않았는가' 다.")

    # --- current phase (T4: bus heartbeat) ---
    phases = {}
    hb_dir = BUS / "heartbeats"
    for hb in sorted(hb_dir.glob("*.json")):
        agent = hb.stem
        try:
            d = load_json(hb)
        except Exception as e:                       # noqa: BLE001
            phases[agent] = {"phase": f"ERROR: {e}", "tier": "T4"}
            continue
        age_s = round((datetime.now(KST) - datetime.fromtimestamp(hb.stat().st_mtime, KST)).total_seconds())
        phases[agent] = {
            "phase": d.get("phase", NA),
            "work_state": d.get("work_state", NA),
            "claimed_head_sha": d.get("head_sha", NA),
            "branch": d.get("branch", NA),
            "blocker_ids": d.get("blocker_ids", []),
            "heartbeat_age_seconds": age_s,
            "timestamp": d.get("timestamp"),
            "tier": "T4",
        }
    out["phase_by_agent"] = phases
    distinct_phases = {v.get("phase") for v in phases.values() if isinstance(v.get("phase"), str)}
    out["current_phase"] = (sorted(distinct_phases)[0] if len(distinct_phases) == 1
                            else f"DIVERGENT: {sorted(distinct_phases)}")

    # --- open P0/P1 tickets (T4: bus) ---
    acks = {p.name for p in (BUS / "acks").glob("*.json")}
    comps = {p.name for p in (BUS / "completions").glob("*.json")}
    open_tickets, resolved_p01 = [], 0
    parse_errors = []
    for tp in sorted((BUS / "tickets").glob("*.json")):
        tid = tp.name[:-5]
        try:
            d = load_json(tp)
        except Exception as e:                       # noqa: BLE001
            parse_errors.append(f"{tid}: {e}")
            continue
        prio = d.get("priority") or d.get("severity")
        if prio not in ("P0", "P1"):
            continue
        to = d.get("to") or []
        to = [to] if isinstance(to, str) else list(to)
        pending = [rcp for rcp in to
                   if f"{tid}.{rcp}.json" not in acks and f"{tid}.{rcp}.json" not in comps]
        if pending:
            open_tickets.append({
                "ticket_id": tid, "priority": prio, "type": d.get("type"),
                "from": d.get("from"), "to": to, "awaiting_response_from": pending,
                "created_at": d.get("created_at"),
                "expected_response": d.get("expected_response"),
                "headline": (d.get("title") or d.get("category") or d.get("urgent")
                             or d.get("finding") or d.get("what") or "")[:200],
            })
        else:
            resolved_p01 += 1
    open_tickets.sort(key=lambda x: (x["priority"], x.get("created_at") or ""))
    out["open_p0"] = n(sum(1 for t in open_tickets if t["priority"] == "P0"),
                       "P0 tickets with >=1 recipient not ACKed/completed",
                       denom=len(open_tickets) + resolved_p01,
                       denom_grain="P0+P1 tickets on bus", tier="T4")
    out["open_p1"] = n(sum(1 for t in open_tickets if t["priority"] == "P1"),
                       "P1 tickets with >=1 recipient not ACKed/completed",
                       denom=len(open_tickets) + resolved_p01,
                       denom_grain="P0+P1 tickets on bus", tier="T4")
    out["open_tickets"] = open_tickets
    out["ticket_parse_errors"] = parse_errors
    out["open_definition"] = ("open = 티켓의 to[] 수신자 중 acks/ 나 completions/ 에 "
                              "<ticket_id>.<recipient>.json 이 없는 사람이 하나라도 있는 것. "
                              "내용상 해소 여부는 판단하지 않는다 — 파일 존재만 본다.")

    # --- latest exact SHAs (T1: git ls-remote) ---
    remote = {}
    try:
        raw = read_only_git("ls-remote", "--heads", "origin")
        for line in raw.splitlines():
            sha, ref = line.split("\t")
            remote[ref.replace("refs/heads/", "")] = sha
        sha_status = "OK"
    except Exception as e:                           # noqa: BLE001
        sha_status = f"ERROR: {e}"
    shas = []
    for plane, br in TRACKED_BRANCHES:
        shas.append({"plane": plane, "branch": br,
                     "exact_sha": remote.get(br, "REF_ABSENT_ON_ORIGIN"), "tier": "T1"})
    out["remote_exact_shas"] = shas
    out["remote_sha_probe_status"] = sha_status
    out["sha_note"] = ("branch name 은 상태가 아니다. 여기 있는 것은 git ls-remote 로 읽은 "
                       "origin 의 exact SHA 이며, heartbeat 가 주장하는 head_sha 와 다를 수 있다.")

    # heartbeat 주장 SHA vs origin exact SHA 대조
    drift = []
    for agent, hb in phases.items():
        br, claimed = hb.get("branch"), hb.get("claimed_head_sha")
        if not isinstance(br, str) or br not in remote:
            continue
        drift.append({"agent": agent, "branch": br, "claimed_head_sha": claimed,
                      "origin_exact_sha": remote[br],
                      "matches_origin": claimed == remote[br]})
    out["heartbeat_vs_origin"] = drift
    out["unpushed_agents"] = n(sum(1 for d in drift if not d["matches_origin"]),
                               "agents whose heartbeat head_sha != origin exact SHA",
                               denom=len(drift), denom_grain="agents comparable", tier="T1")

    # --- active subagents (T4: D registry) ---
    reg_path = RD / "AGENT_RUN_REGISTRY.jsonl"
    if reg_path.exists():
        recs = [json.loads(ln) for ln in reg_path.read_text(encoding="utf-8").splitlines() if ln.strip()]
        by_status = Counter(r.get("status", "unknown") for r in recs)
        out["subagents_by_status"] = {k: n(v, "D subagent runs", denom=len(recs),
                                           denom_grain="registry records", tier="T4")
                                      for k, v in sorted(by_status.items())}
        out["subagents_detail"] = [{"rq_id": r.get("rq_id"), "status": r.get("status"),
                                    "verdict": r.get("verdict"), "tokens": r.get("subagent_tokens"),
                                    "duration_min": r.get("duration_min"),
                                    "files": len(r.get("owned_files", []))} for r in recs]
        out["subagent_total_tokens"] = n(sum(r.get("subagent_tokens") or 0 for r in recs),
                                         "tokens spent by D subagents", tier="T4")
    else:
        out["subagents_by_status"] = unavailable(
            NA, "AGENT_RUN_REGISTRY.jsonl 이 없다 — D 가 아직 subagent 를 기록하지 않았다.", "T4")

    a = out["active_runs_by_plane"]
    out["summary"] = (
        f"phase={out['current_phase']} · "
        f"active MLflow runs A/B/C/D = {a['A']['value']}/{a['B']['value']}/{a['C']['value']}/{a['D']['value']} · "
        f"open P0 {out['open_p0']['value']} · open P1 {out['open_p1']['value']} · "
        f"unpushed agents {out['unpushed_agents']['value']}/{out['unpushed_agents']['denominator']}")
    return out


# ────────────────────────────────────────────────────────── 2. 데이터 ──

@section
def sec_data() -> dict:
    out: dict = {}
    rq1 = load_json(RESULTS / "RQ_D1_reconstruction.json")
    chain = rq1["denominator_chain"]

    lo = load_json(MART / "fact_landing_observation.json")
    te = load_json(MART / "fact_task_entry.json")
    ie = load_json(MART / "fact_interrupt_element.json")
    cr = load_json(MART / "fact_criterion_result.json")

    measured = sum(1 for r in lo if r.get("measurement_status") == "MEASURED")

    out["denominator_chain"] = {
        "observation_dirs": n(chain["observation_dirs"], "observation dirs (raw evidence)", tier="T2"),
        "attempted": n(chain["distinct_targets_attempted"], "attempted targets",
                       denom=chain["observation_dirs"], denom_grain="observation dirs", tier="T2"),
        "evidence_complete": n(chain["targets_with_any_evidence"], "evidence-bearing targets",
                               denom=chain["distinct_targets_attempted"],
                               denom_grain="attempted targets", tier="T2"),
        "in_landing_mart": n(chain["targets_in_landing_mart"], "targets with a landing mart row",
                             denom=chain["distinct_targets_attempted"],
                             denom_grain="attempted targets", tier="T3"),
        "measured": n(measured, "landing rows measurement_status=MEASURED",
                      denom=len(lo), denom_grain="landing mart rows", tier="T3"),
        "in_task_mart": n(chain["targets_in_task_mart"], "targets with a task mart row",
                          denom=chain["targets_in_landing_mart"],
                          denom_grain="landing mart targets", tier="T3"),
    }
    out["silently_dropped"] = n(len(chain["targets_dropped_silently"]),
                                "attempted targets with zero mart presence",
                                denom=chain["distinct_targets_attempted"],
                                denom_grain="attempted targets", tier="T2")
    out["silently_dropped_wtg"] = chain["targets_dropped_silently"]
    out["landing_without_task_row"] = n(chain["landing_targets_without_task_row"],
                                        "landing targets with no task row (target-level guard block)",
                                        denom=chain["targets_in_landing_mart"],
                                        denom_grain="landing mart targets", tier="T3")

    # joint-valid: 세 축이 동시에 값을 가진 관측
    axis_c_ok = {r["observation_id"] for r in lo if r.get("max_overlay_coverage") is not None}
    axis_b_ok = {r["task_observation_id"] for r in te if r.get("NED") is not None}
    axis_a_obs = {r.get("observation_id") for r in cr} if cr else set()
    joint = axis_c_ok & axis_b_ok & axis_a_obs
    out["joint_valid"] = n(len(joint), "observations with Axis A + Axis B(NED) + Axis C all non-null",
                           denom=len(lo), denom_grain="landing mart rows", tier="T3")
    out["joint_valid_why_zero"] = ("Axis A 는 0행이고 Axis B 의 NED 는 31 task rows 전부 null 이다. "
                                   "교집합은 정의상 0 이며, 이것은 '세 축이 모두 실패했다'가 아니라 "
                                   "'두 축이 아직 산출되지 않았다'는 뜻이다.")
    out["joint_valid_axis_c_only"] = n(len(axis_c_ok), "observations with Axis C only",
                                       denom=len(lo), denom_grain="landing mart rows", tier="T3")

    # missingness — 축별·필드별
    def miss(rows, field):
        tot = len(rows)
        m = sum(1 for r in rows if r.get(field) is None)
        return {"missing": m, "total": tot,
                "missing_rate": round(m / tot, 4) if tot else None}

    out["missingness"] = {
        "landing_mart_rows_56": {f: miss(lo, f) for f in
                                 ("max_overlay_coverage", "max_primary_action_occlusion",
                                  "primary_action_visible_initial", "blocking_modal_count")},
        "task_mart_rows_31": {f: miss(te, f) for f in
                              ("NED", "IED", "MPFED", "endpoint_status", "interaction_archetype")},
        "interrupt_rows_235": {f: miss(ie, f) for f in
                               ("overlay_coverage", "primary_action_occlusion", "final_label")},
        "structural_missingness": {
            "attempted_targets_absent_from_all_marts": len(chain["targets_dropped_silently"]),
            "landing_targets_absent_from_task_mart": chain["landing_targets_without_task_row"],
            "note": ("행 안의 null 보다 '행 자체가 없는 것'이 더 크다. "
                     "3 attempted targets 는 mart 어디에도 없고, 25 landing targets 는 task mart 에 없다. "
                     "mart 를 분모로 쓰면 이 결측이 보이지 않는다."),
        },
        "tier": "T3",
    }

    out["mart_provenance"] = mart_provenance()
    out["summary"] = (
        f"66 observation dirs → 59 attempted targets → 56 evidence-bearing → "
        f"{measured} MEASURED landing rows → 31 task rows. "
        f"joint-valid(A+B+C) = 0 / 56 landing rows — Axis A 0행 · Axis B NED 전량 null 이기 때문.")
    return out


def mart_provenance() -> dict:
    """frozen mart 의 선언 해시와 실측 해시를 대조한다. 대시보드가 어느 mart 를 읽었는지 증명."""
    man = load_json(MART / "FROZEN_MART_MANIFEST.json")
    rows = []
    for f in man["mart_files"]:
        p = MART / f["file"]
        actual = sha256_file(p) if p.exists() else None
        declared = f["sha256"].replace("sha256:", "")
        rows.append({"file": f["file"], "declared_row_count": f["row_count"],
                     "actual_row_count": len(load_json(p)) if p.exists() else None,
                     "declared_sha256": declared, "actual_sha256": actual,
                     "hash_match": actual == declared})
    return {"snapshot_at": man["snapshot_at"], "files": rows,
            "all_hashes_match": all(r["hash_match"] for r in rows), "tier": "T3"}


# ─────────────────────────────────────────────────────── 3. RF detector ──

@section
def sec_rf(runs, exps) -> dict:
    """LA_03_RF_MAPPING 의 run metric 에서 detector 성능을 읽는다.

    detector 자체의 성능 metric 은 아직 어떤 run 에도 없다. 추정하지 않고 NOT_AVAILABLE 로 둔다.
    """
    out: dict = {}
    rf = [r for r in runs if exps.get(r.info.experiment_id) == "LA_03_RF_MAPPING"]
    out["runs_in_LA_03_RF_MAPPING"] = n(len(rf), "MLflow runs in LA_03_RF_MAPPING", tier="T5")
    out["run_index"] = [{"run_name": r.info.run_name, "run_id": r.info.run_id,
                         "plane": r.data.tags.get("plane"),
                         "run_status": r.data.tags.get("run_status") or r.info.status,
                         "verdict": r.data.tags.get("verdict"),
                         "metric_keys": sorted(r.data.metrics)} for r in rf]

    def find_metric(*keys):
        for r in rf:
            for k in keys:
                if k in r.data.metrics:
                    return r.data.metrics[k], r.info.run_name, r.info.run_id
        return None, None, None

    # calibration / holdout coverage — C 의 LABEL freeze run 이 라벨 분할 크기를 남겼다.
    cal, cal_run, cal_id = find_metric("cal", "calibration_n")
    hold, hold_run, hold_id = find_metric("hold", "holdout_n")
    frozen, _, _ = find_metric("frozen_rows")
    abstain, ab_run, _ = find_metric("abstain")

    if cal is not None:
        out["calibration_coverage"] = n(int(cal), "calibration-split labeled targets",
                                        denom=int(frozen) if frozen else None,
                                        denom_grain="frozen labeled targets", tier="T5")
        out["calibration_coverage_source"] = f"MLflow run {cal_run} ({cal_id}) — plane C, 라벨 분할 크기"
    else:
        out["calibration_coverage"] = unavailable(
            NA, "LA_03_RF_MAPPING 의 어떤 run 도 calibration coverage metric 을 남기지 않았다.", "T5")

    if hold is not None:
        out["holdout_coverage"] = n(int(hold), "holdout-split labeled targets",
                                    denom=int(frozen) if frozen else None,
                                    denom_grain="frozen labeled targets", tier="T5")
        out["holdout_coverage_source"] = (f"MLflow run {hold_run} ({hold_id}) — plane C. "
                                          "**분할 크기만** 읽었다. D 는 holdout 라벨 내용을 열지 않는다.")
    else:
        out["holdout_coverage"] = unavailable(NA, "holdout split 크기 metric 이 없다.", "T5")

    out["holdout_scope_boundary"] = (
        "holdout 은 C 영역이다. D 는 LABEL_SPLIT_FROZEN.json 과 control/label/** 를 열지 않는다. "
        "여기 있는 값은 C 가 MLflow 에 남긴 요약 metric 이며, D 가 라벨을 읽어 센 값이 아니다.")

    # detector 성능 — 없다
    out["macro_f1"] = unavailable(
        NA,
        "RF detector 의 macro F1 을 담은 run 이 없다. W2(claude-b/w2-rf-detector)는 RUNNING 이고 "
        "attestation 대기 중이라 아직 평가 run 을 내지 않았다. "
        "LA_03_RF_MAPPING 의 RQ-D3A macro F1 은 detector 가 아니라 L0 feature 분리가능성 baseline 이므로 "
        "detector 성능으로 전용하지 않는다.", "T5")
    out["abstention"] = (
        n(int(abstain), "abstained label rows (labeler abstention, not detector abstention)",
          denom=int(frozen) if frozen else None, denom_grain="frozen labeled targets", tier="T5")
        if abstain is not None else
        unavailable(NA, "detector abstention rate metric 이 없다.", "T5"))
    if abstain is not None:
        out["abstention_caveat"] = (
            f"이 값은 **라벨러**의 abstain 이다(run {ab_run}). detector 의 abstention rate 가 아니다. "
            "둘을 같은 칸에 놓으면 안 되므로 grain 에 명시했다.")
    out["unsafe_fp"] = unavailable(
        NA, "unsafe false positive 를 세려면 detector 예측과 gold label 을 대조해야 한다. "
            "detector 평가 run 이 없고, gold label 대조는 C 영역이다 — D 가 계산할 수 없다.", "T5")

    # 참고: D 가 낸 RF 관련 run
    d_rf = [r for r in rf if r.data.tags.get("plane") == "D"]
    out["d_rf_runs"] = [{"run_name": r.info.run_name, "rq_id": r.data.tags.get("rq_id"),
                         "verdict": r.data.tags.get("verdict"),
                         "run_status": r.data.tags.get("run_status"),
                         "macro_f1_baselines": {k: v for k, v in r.data.metrics.items()
                                                if "macro_f1" in k}} for r in d_rf]
    out["summary"] = ("detector 성능(macro F1 · abstention · unsafe FP)은 전부 NOT_AVAILABLE — "
                      "W2 detector 평가 run 이 아직 없다. 분할 크기(cal/hold)만 C 의 라벨 run 에서 읽힌다.")
    return out


# ────────────────────────────────────────────────────────── 4. KWCAG ──

@section
def sec_kwcag() -> dict:
    cr = load_json(MART / "fact_criterion_result.json")
    out: dict = {"criterion_rows": n(len(cr), "criterion result rows in frozen mart", tier="T3")}
    if len(cr) == 0:
        why = ("fact_criterion_result.json 이 0행이다(파일 2 bytes = []). "
               "평가기가 돌아서 '위반 없음'을 낸 것이 아니라 **평가가 실행되지 않았다**. "
               "W3(claude-b/w3-kwcag) Stage 1 evaluator 가 아직 산출 전이다.")
        out["decidable_count"] = unavailable("NOT_EVALUATED", why, "T3")
        out["decision_coverage"] = unavailable("NOT_EVALUATED", why, "T3")
        out["undet"] = unavailable("NOT_EVALUATED", why, "T3")
        out["criterion_level_failures"] = unavailable("NOT_EVALUATED", why, "T3")
        out["misreading_guard"] = ("0행을 '0% 실패' 또는 '전부 통과'로 읽으면 안 된다. "
                                   "분자도 분모도 존재하지 않는다. 비율은 정의되지 않는다.")
        out["dim_certification_rows"] = n(len(load_json(MART / "dim_certification.json")),
                                          "certification dimension rows", tier="T3")
        out["summary"] = "Axis A = NOT_EVALUATED. criterion 0행 / 56 landing rows — 비율은 정의되지 않는다."
        return out
    # 0행이 아니게 되는 날을 위한 경로 (지금은 도달하지 않는다)
    st = Counter(r.get("result") or r.get("status") for r in cr)
    dec = sum(v for k, v in st.items() if k not in ("UNDETERMINED", "UNDET", None))
    out["decidable_count"] = n(dec, "decidable criterion results", denom=len(cr),
                               denom_grain="criterion result rows", tier="T3")
    out["decision_coverage"] = n(round(dec / len(cr), 4), "DecisionCoverage ratio", tier="T3")
    out["undet"] = n(len(cr) - dec, "UNDETERMINED criterion results", denom=len(cr),
                     denom_grain="criterion result rows", tier="T3")
    out["criterion_level_failures"] = dict(st)
    out["summary"] = f"decidable {dec} / {len(cr)} criterion result rows."
    return out


# ─────────────────────────────────────────────────────────── 5. Depth ──

@section
def sec_depth() -> dict:
    te = load_json(MART / "fact_task_entry.json")
    tot = len(te)
    out: dict = {"task_rows": n(tot, "task entry rows in frozen mart", tier="T3")}

    for field in ("NED", "IED", "MPFED"):
        avail = sum(1 for r in te if r.get(field) is not None)
        if avail == 0:
            out[f"{field.lower()}_available"] = unavailable(
                NA,
                f"{field} 는 {tot} task rows 전부 null 이다. "
                "값이 '깊이 0'인 것이 아니라 필드가 채워진 적이 없다 — endpoint detector 미배선.",
                "T3")
        else:
            out[f"{field.lower()}_available"] = n(avail, f"task rows with non-null {field}",
                                                  denom=tot, denom_grain="task rows", tier="T3")

    reached = count_true(te, "endpoint_reached")
    out["endpoint_reach"] = n(reached, "task rows with endpoint_reached=true",
                              denom=tot, denom_grain="task rows", tier="T3")
    out["endpoint_status_distribution"] = {
        k: n(v, "task rows", denom=tot, denom_grain="task rows", tier="T3")
        for k, v in sorted(Counter(str(r.get("endpoint_status")) for r in te).items(),
                           key=lambda kv: -kv[1])}
    out["auth_gate_before_endpoint"] = n(
        count_true(te, "auth_gate_before_endpoint"),
        "task rows where an auth gate was met before any endpoint",
        denom=tot, denom_grain="task rows", tier="T3")
    out["budget_reason_distribution"] = dict(
        Counter(str(r.get("budget_reason")) for r in te).most_common())
    out["archetype_distribution"] = dict(
        Counter(r.get("interaction_archetype") for r in te).most_common())
    out["absent_archetype"] = {
        "value": ["QUERY"],
        "why": "frozen archetype 7종 중 QUERY 만 task mart 에 0행이다. archetype coverage 6/7.",
        "tier": "T2"}
    out["endpoint_reach_reading"] = (
        "endpoint_reached=0/31 은 '도달 실패 관측 31건'이 아니라 '31 task rows 중 도달을 기록한 행이 없다'다. "
        "UNRESOLVED 18 은 왜 끝났는지가 기록되지 않은 행이라 실패 사유로 셀 수 없다.")
    out["summary"] = (f"NED/IED/MPFED 전부 0 / {tot} task rows — 세 depth 지표 모두 NOT_AVAILABLE. "
                      f"endpoint_reached {reached} / {tot} task rows. "
                      f"UNRESOLVED {sum(1 for r in te if r.get('endpoint_status') == 'UNRESOLVED')} 행은 종료 사유 미기록.")
    return out


# ────────────────────────────────────────────────────────── 6. Axis C ──

@section
def sec_axis_c() -> dict:
    lo = load_json(MART / "fact_landing_observation.json")
    ie = load_json(MART / "fact_interrupt_element.json")
    nlo, nie = len(lo), len(ie)
    out: dict = {}

    out["overlay_coverage_available"] = n(
        sum(1 for r in lo if r.get("max_overlay_coverage") is not None),
        "landing rows with non-null max_overlay_coverage",
        denom=nlo, denom_grain="landing mart rows", tier="T3")
    vals = sorted(r["max_overlay_coverage"] for r in lo if r.get("max_overlay_coverage") is not None)
    if vals:
        out["overlay_coverage_median"] = n(round(vals[len(vals) // 2], 4),
                                           "median of max_overlay_coverage over landing rows",
                                           tier="T3")
        out["overlay_coverage_max"] = n(round(vals[-1], 4), "max of max_overlay_coverage", tier="T3")

    cls = Counter(r.get("classification_status") for r in ie)
    classified = cls.get("DETERMINISTIC", 0)
    out["semantic_classified_rate"] = n(
        round(classified / nie, 4) if nie else None,
        "share of interrupt elements with classification_status=DETERMINISTIC",
        denom=nie, denom_grain="interrupt element rows", tier="T3")
    out["semantic_classification_status"] = {
        k: n(v, "interrupt element rows", denom=nie, denom_grain="interrupt element rows", tier="T3")
        for k, v in cls.most_common()}
    lab = Counter(str(r.get("final_label")) for r in ie)
    out["final_label_distribution"] = dict(lab.most_common())
    out["unknown_label_share"] = n(
        round(lab.get("UNKNOWN", 0) / nie, 4) if nie else None,
        "share of interrupt elements labeled UNKNOWN",
        denom=nie, denom_grain="interrupt element rows", tier="T3")

    out["task_bound_occlusion_available"] = unavailable(
        NA,
        "max_primary_action_occlusion 은 56/56 landing rows 에 값이 있으나 **task binding 없이** "
        "계산됐다. task 가 정한 primary action 이 아니라 page 휴리스틱으로 고른 요소를 가린 비율이므로, "
        "task-bound occlusion 으로는 쓸 수 없다.", "T3")
    out["page_level_occlusion_available"] = n(
        sum(1 for r in lo if r.get("max_primary_action_occlusion") is not None),
        "landing rows with non-null max_primary_action_occlusion (PAGE-LEVEL ONLY)",
        denom=nlo, denom_grain="landing mart rows", tier="T3")
    out["occlusion_validity_scope"] = (
        "primary_action_occlusion 은 **page-level 로만 유효하다**. task 별 primary action 이 결정되기 전에 "
        "계산된 값이므로 task-bound 해석을 붙이면 안 된다.")

    out["interrupt_rows"] = n(nie, "interrupt element rows", tier="T3")
    out["observations_with_interrupts"] = n(
        len({r["observation_id"] for r in ie}), "distinct observations appearing in interrupt mart",
        denom=nlo, denom_grain="landing mart rows", tier="T3")
    out["blocks_primary_action"] = n(
        count_true(ie, "blocks_primary_action"),
        "interrupt rows flagged blocks_primary_action (page-level)",
        denom=nie, denom_grain="interrupt element rows", tier="T3")
    out["dismiss_control_exists"] = n(
        count_true(ie, "dismiss_control_exists"),
        "interrupt rows with a dismiss control detected",
        denom=nie, denom_grain="interrupt element rows", tier="T3")

    out["summary"] = (
        f"overlay coverage {out['overlay_coverage_available']['value']}/{nlo} landing rows 가용 · "
        f"semantic DETERMINISTIC {classified}/{nie} interrupt rows "
        f"({out['semantic_classified_rate']['value']}) · "
        f"task-bound occlusion 은 NOT_AVAILABLE (page-level 값만 존재).")
    return out


# ─────────────────────────────────────────────────────── 7. D Research ──

@section
def sec_d_research(runs, exps) -> dict:
    out: dict = {}

    # queue (T5: D 문서)
    q = (RD / "D_RESEARCH_QUEUE.md").read_text(encoding="utf-8")
    rows = re.findall(
        r"^\|\s*\*{0,2}(RQ-D[0-9A-Za-z-]*[0-9A-Za-z])\*{0,2}\s*\|(.+?)\|\s*\*{0,2}([A-Z_]+)\*{0,2}\s*\|",
        q, flags=re.M)
    by_state = Counter(s for _, _, s in rows)
    out["queue_states"] = {k: n(v, "research questions", denom=len(rows),
                                denom_grain="RQs in D_RESEARCH_QUEUE.md", tier="T5")
                           for k, v in sorted(by_state.items())}
    out["open_research_questions"] = n(by_state.get("OPEN", 0), "OPEN research questions",
                                       denom=len(rows), denom_grain="RQs in queue", tier="T5")
    out["queue_rows"] = [{"rq_id": a, "state": c, "question": b.strip()[:110]} for a, b, c in rows]

    # experiments running (T5: MLflow)
    d_runs = [r for r in runs if r.data.tags.get("plane") == "D"]
    live = [r for r in d_runs if r.data.tags.get("run_status") == "RUNNING"]
    out["experiments_running"] = n(len(live), "D-plane MLflow runs with run_status=RUNNING",
                                   denom=len(d_runs), denom_grain="D-plane runs", tier="T5")
    out["experiments_running_detail"] = [{"run_name": r.info.run_name, "run_id": r.info.run_id,
                                          "rq_id": r.data.tags.get("rq_id"),
                                          "hypothesis_id": r.data.tags.get("hypothesis_id")}
                                         for r in live]

    # verdict 집계 — 전체 experiment (superseded 제외)
    def tally(pool):
        return Counter(r.data.tags.get("verdict") for r in pool
                       if r.data.tags.get("verdict")
                       and r.data.tags.get("run_status") != "SUPERSEDED")
    all_v, d_v = tally(runs), tally(d_runs)
    out["verdicts_all_planes"] = dict(all_v.most_common())
    out["verdicts_d_plane"] = dict(d_v.most_common())
    supported = d_v.get("SUPPORTED", 0) + d_v.get("PARTIALLY_SUPPORTED", 0)
    refuted = d_v.get("REFUTED", 0) + d_v.get("NOT_SUPPORTED", 0)
    inconclusive = d_v.get("INCONCLUSIVE", 0) + d_v.get("NOT_TESTABLE", 0)
    den = sum(d_v.values())
    out["supported"] = n(supported, "D runs with SUPPORTED or PARTIALLY_SUPPORTED",
                         denom=den, denom_grain="D runs with a settled verdict", tier="T5")
    out["refuted"] = n(refuted, "D runs with REFUTED or NOT_SUPPORTED",
                       denom=den, denom_grain="D runs with a settled verdict", tier="T5")
    out["inconclusive"] = n(inconclusive, "D runs with INCONCLUSIVE or NOT_TESTABLE",
                            denom=den, denom_grain="D runs with a settled verdict", tier="T5")
    out["pending"] = n(d_v.get("PENDING", 0), "D runs still PENDING",
                       denom=den, denom_grain="D runs with a settled verdict", tier="T5")
    out["verdict_note"] = ("verdict 는 D 자신이 붙인 tag 다(T5). C 검증을 통과했다는 뜻이 아니다. "
                           "D run 의 authority_status 는 전부 NON_CANONICAL 이다.")

    # latest high-impact finding — 데이터에서 고른다 (손으로 쓰지 않는다)
    settled = [r for r in d_runs
               if r.data.tags.get("run_status") == "COMPLETED"
               and r.data.tags.get("verdict") not in (None, "PENDING")]
    if settled:
        latest = max(settled, key=lambda r: r.info.start_time)
        t = latest.data.tags
        out["latest_high_impact_finding"] = {
            "rq_id": t.get("rq_id"), "run_name": latest.info.run_name,
            "run_id": latest.info.run_id, "verdict": t.get("verdict"),
            "hypothesis_id": t.get("hypothesis_id"),
            "started_at_kst": t.get("started_at_kst"),
            "limitation": t.get("limitation_summary", ""),
            "selection_rule": "plane=D · run_status=COMPLETED · verdict!=PENDING 중 start_time 최대",
            "tier": "T5",
        }
    else:
        out["latest_high_impact_finding"] = unavailable(
            "NONE_YET", "verdict 가 확정된 D-plane MLflow run 이 없다.", "T5")

    # claim ledger (T5: D 문서)
    led = RD / "CLAIM_RESEARCH_LEDGER.csv"
    if led.exists():
        import csv
        with led.open(encoding="utf-8") as fh:
            lrows = list(csv.DictReader(fh))
        lv = Counter(r["verdict"] for r in lrows)
        out["claim_ledger"] = {
            "total": n(len(lrows), "claims audited by D (다른 plane 의 주장을 D 가 재계산한 것)",
                       tier="T2"),
            "by_verdict": {k: n(v, "audited claims", denom=len(lrows),
                                denom_grain="audited claims", tier="T2") for k, v in lv.most_common()},
            "refuted_claims": [{"claim_id": r["claim_id"], "source": r["source"],
                                "claim": r["claim_text"], "d_result": r["result"],
                                "verdict": r["verdict"]}
                               for r in lrows if r["verdict"] in ("REFUTED", "NOT_SUPPORTED")],
        }
    else:
        out["claim_ledger"] = unavailable(NA, "CLAIM_RESEARCH_LEDGER.csv 이 없다.", "T2")

    out["summary"] = (
        f"OPEN RQ {out['open_research_questions']['value']} / {len(rows)} queue rows · "
        f"D runs running {len(live)} · "
        f"supported {supported} / refuted {refuted} / inconclusive {inconclusive} "
        f"(settled D verdicts {den})")
    return out


# ─────────────────────────────────────────────────────── 8. C Assurance ──

@section
def sec_c_assurance(runs, exps) -> dict:
    out: dict = {}
    acks = sorted((BUS / "acks").glob("*.json"))
    comps = sorted((BUS / "completions").glob("*.json"))
    c_tickets = sorted((BUS / "tickets").glob("C-*.json"))

    # MLflow C runs 의 match_status (T5)
    c_runs = [r for r in runs if r.data.tags.get("plane") == "C"]
    ms = Counter(r.data.tags.get("match_status", "UNTAGGED") for r in c_runs)
    out["match_status_mlflow"] = {k: n(v, "C-plane MLflow runs", denom=len(c_runs),
                                       denom_grain="C-plane runs", tier="T5")
                                  for k, v in ms.most_common()}
    out["match"] = n(ms.get("MATCH", 0), "C runs with match_status=MATCH",
                     denom=len(c_runs), denom_grain="C-plane runs", tier="T5")
    out["mismatch"] = n(ms.get("RESULT_AFFECTING_MISMATCH", 0) + ms.get("SYSTEMIC_MISMATCH", 0),
                        "C runs with a result-affecting or systemic mismatch",
                        denom=len(c_runs), denom_grain="C-plane runs", tier="T5")
    out["c_run_index"] = [{"run_name": r.info.run_name, "run_id": r.info.run_id,
                           "match_status": r.data.tags.get("match_status"),
                           "severity": r.data.tags.get("severity"),
                           "difference": (r.data.tags.get("difference") or "")[:140]}
                          for r in c_runs]

    # C completion 의 severity 어휘 (C0/C1/C2 · P0~P4) (T4)
    sev = Counter()
    c_comps = []
    for p in comps:
        try:
            d = load_json(p)
        except Exception:                            # noqa: BLE001
            continue
        if d.get("from") != "C":
            continue
        s = d.get("severity_max")
        sev[str(s)] += 1
        c_comps.append({"ticket_id": d.get("ticket_id"), "result_type": d.get("result_type"),
                        "verdict": d.get("verdict"), "severity_max": s,
                        "completed_at": d.get("completed_at")})
    out["c_completions"] = n(len(c_comps), "completion records authored by C", tier="T4")
    out["c_severity_max_distribution"] = {k: n(v, "C completions", denom=len(c_comps),
                                               denom_grain="C completions", tier="T4")
                                          for k, v in sev.most_common()}
    out["c1"] = n(sev.get("C1", 0), "C completions with severity_max=C1",
                  denom=len(c_comps), denom_grain="C completions", tier="T4")
    out["c0"] = (n(sev.get("C0", 0), "C completions with severity_max=C0",
                   denom=len(c_comps), denom_grain="C completions", tier="T4")
                 if "C0" in sev else
                 unavailable("NONE_YET", "severity_max=C0 인 C completion 이 아직 없다. "
                                         "관측된 어휘는 C1/C2 와 P0~P4 다.", "T4"))
    out["c_completion_index"] = c_comps
    out["c_tickets_open_by_priority"] = dict(
        Counter((load_json(p).get("priority") or "NONE") for p in c_tickets).most_common())
    out["c_tickets_total"] = n(len(c_tickets), "tickets authored by C on the bus", tier="T4")

    # C 가 D finding 을 재현했는가 (T4: bus 전수 스캔)
    hits = []
    for p in list(acks) + list(comps) + c_tickets:
        try:
            txt = p.read_text(encoding="utf-8")
        except Exception:                            # noqa: BLE001
            continue
        if re.search(r"RQ-D\d", txt) and (".C." in p.name or p.name.startswith("C-")):
            hits.append(p.name)
    if hits:
        out["reproduced_d_findings"] = n(len(hits), "C-authored bus files referencing an RQ-D finding",
                                         tier="T4")
        out["reproduced_d_findings_files"] = hits
    else:
        out["reproduced_d_findings"] = unavailable(
            "NONE_YET",
            "bus 전체(acks/completions/C 티켓)에서 C 가 작성한 파일 중 RQ-D 를 언급한 것이 0건이다. "
            "D 는 D-RESEARCH_FINDING 을 방금 발행했고 C 는 W1/W2/W4 acceptance 검증 중이다 — "
            "재현 요청이 C 큐에 도달했지만 아직 처리되지 않았다는 뜻이다.", "T4")

    out["asymmetry_note"] = (
        "C 가 D 를 재현하지 않았다는 것은 D 결과가 틀렸다는 뜻도, 맞다는 뜻도 아니다. "
        "D run 은 전부 authority_status=NON_CANONICAL 이며 C 검증 없이는 그대로 남는다.")
    out["summary"] = (
        f"C MLflow runs {len(c_runs)} — MATCH {ms.get('MATCH', 0)} / "
        f"MATCH_WITH_NONBLOCKING_DIFFERENCE {ms.get('MATCH_WITH_NONBLOCKING_DIFFERENCE', 0)} / "
        f"result-affecting+systemic mismatch {out['mismatch']['value']}. "
        f"C completions {len(c_comps)} (severity C1 {sev.get('C1', 0)} · C0 없음). "
        f"reproduced D findings: {out['reproduced_d_findings'].get('value')}")
    return out


# ────────────────────────────────────────────────────────── markdown ──

TIER_LEGEND = """| tier | 의미 | 이 대시보드에서의 예 |
|---|---|---|
| **T1** | raw artifact · runtime evidence · exact code SHA | `git ls-remote` exact SHA, evidence 디렉터리 실측 |
| **T2** | 독립 재현계산 (D 가 raw 에서 직접 다시 센 값) | 분모 사슬 66→59→56, claim ledger 재계산 |
| **T3** | frozen definition · schema · hash 고정된 mart | fact_*.json 행수·null 수 |
| **T4** | accepted SSOT · decision · agent bus 기록 | heartbeat phase, 티켓 P0/P1, C completion |
| **T5** | MLflow metadata · prose · agent narrative — **가장 약함** | run_status, verdict tag, metric |
"""


def md_table(headers, rows) -> str:
    out = ["| " + " | ".join(headers) + " |",
           "|" + "|".join(["---"] * len(headers)) + "|"]
    for r in rows:
        out.append("| " + " | ".join("" if c is None else str(c) for c in r) + " |")
    return "\n".join(out)


def cell(x) -> str:
    """NOT_AVAILABLE 계열은 이유까지 한 줄로 보여준다."""
    if isinstance(x, dict) and x.get("value") in (NA, "NOT_EVALUATED", "NONE_YET"):
        return f"**{x['value']}**"
    return fmt(x)


def why(x) -> str:
    return x.get("why_absent", "") if isinstance(x, dict) else ""


def render_md(d: dict) -> str:
    L: list[str] = []
    A = L.append
    A("# D_DASHBOARD — Research Director 감시판")
    A("")
    A(f"생성 `{d['generated_at_kst']}` · 재실행 `{d['reproduce']}`")
    A("")
    A("> **MLflow 는 truth 가 아니다.** truth precedence:")
    A("> `raw artifact / exact SHA` → `독립 재현계산` → `frozen definition` → "
      "`accepted SSOT / decision` → `MLflow metadata / prose`")
    A("> 각 수치의 출처 계층을 T1~T5 로 표기한다. run 이 존재한다는 사실은 승인이 아니다.")
    A("")
    A("> **없는 값을 만들지 않는다.** `NOT_AVAILABLE` / `NOT_EVALUATED` / `NONE_YET` 은 "
      "실패가 아니라 *아직 산출되지 않았음*이며, 각각 왜 없는지를 함께 적었다.")
    A("")

    # ── 헤드라인 ──
    A("## 0. 한눈에")
    A("")
    A(md_table(["섹션", "한 줄"],
               [[f"{i}. {t}", d["sections"][k].get("summary", d["sections"][k].get("section_status"))]
                for i, (k, t) in enumerate(SECTION_TITLES.items(), start=1)]))
    A("")
    A(TIER_LEGEND)
    A("")

    s = d["sections"]

    # ── 1 운영 ──
    A("## 1. 운영 상태")
    A("")
    o = s["ops"]
    if o.get("section_status") != "OK":
        A(f"`{o['section_status']}`")
    else:
        A(f"**{o['summary']}**")
        A("")
        A("### active runs (T5)")
        A(md_table(["plane", "RUNNING runs", "분모"],
                   [[p, o["active_runs_by_plane"][p]["value"],
                     f"{o['active_runs_by_plane'][p]['denominator']} total MLflow runs"]
                    for p in ("A", "B", "C", "D")]))
        A("")
        A(f"주의 — {o['active_runs_caveat']}")
        A("")
        A("### phase · heartbeat (T4)")
        A(md_table(["agent", "phase", "work_state", "hb age(s)", "blockers"],
                   [[a, v.get("phase"), str(v.get("work_state"))[:52],
                     v.get("heartbeat_age_seconds"), len(v.get("blocker_ids") or [])]
                    for a, v in o["phase_by_agent"].items()]))
        A("")
        A(f"current phase = **{o['current_phase']}**")
        A("")
        A(f"### open P0/P1 — P0 **{o['open_p0']['value']}** · P1 **{o['open_p1']['value']}** "
          f"(분모 {o['open_p0']['denominator']} P0+P1 tickets) (T4)")
        A("")
        A(md_table(["ticket", "prio", "type", "from→", "미응답", "요지"],
                   [[t["ticket_id"], t["priority"], t["type"],
                     f"{t['from']}→{','.join(t['to'])}", ",".join(t["awaiting_response_from"]),
                     t["headline"][:78]] for t in o["open_tickets"]]))
        A("")
        A(f"*{o['open_definition']}*")
        A("")
        A("### exact SHA (T1 — branch name 으로 상태를 주장하지 않는다)")
        A(md_table(["plane", "branch", "origin exact SHA"],
                   [[r["plane"], f"`{r['branch']}`", f"`{r['exact_sha']}`"]
                    for r in o["remote_exact_shas"]]))
        A("")
        A(md_table(["agent", "branch", "heartbeat 주장", "origin 실측", "일치"],
                   [[r["agent"], f"`{r['branch']}`", f"`{str(r['claimed_head_sha'])[:12]}`",
                     f"`{r['origin_exact_sha'][:12]}`", "O" if r["matches_origin"] else "**X**"]
                    for r in o["heartbeat_vs_origin"]]))
        A("")
        A("### D subagents (T4)")
        A(md_table(["rq", "status", "verdict", "tokens", "min", "files"],
                   [[r["rq_id"], r["status"], r["verdict"], f"{r['tokens']:,}" if r["tokens"] else "-",
                     r["duration_min"], r["files"]] for r in o.get("subagents_detail", [])]))
    A("")

    # ── 2 데이터 ──
    A("## 2. 데이터 — 분모 사슬")
    A("")
    dd = s["data"]
    if dd.get("section_status") != "OK":
        A(f"`{dd['section_status']}`")
    else:
        A(f"**{dd['summary']}**")
        A("")
        ch = dd["denominator_chain"]
        A(md_table(["단계", "값", "grain", "tier"],
                   [[k, v["value"],
                     f"{v['grain']}" + (f" / {v['denominator']} {v['denominator_grain']}"
                                        if "denominator" in v else ""), v["tier"]]
                    for k, v in ch.items()]))
        A("")
        A(md_table(["항목", "값", "tier"],
                   [["silently dropped (mart 어디에도 없음)", fmt(dd["silently_dropped"]),
                     dd["silently_dropped"]["tier"]],
                    ["landing 있는데 task row 없음", fmt(dd["landing_without_task_row"]),
                     dd["landing_without_task_row"]["tier"]],
                    ["**joint-valid (A+B+C 동시)**", f"**{fmt(dd['joint_valid'])}**",
                     dd["joint_valid"]["tier"]],
                    ["Axis C 단독 가용", fmt(dd["joint_valid_axis_c_only"]),
                     dd["joint_valid_axis_c_only"]["tier"]]]))
        A("")
        A(f"joint-valid=0 인 이유 — {dd['joint_valid_why_zero']}")
        A("")
        A(f"누락 target(wtg): `{', '.join(dd['silently_dropped_wtg'])}`")
        A("")
        A("### missingness (T3)")
        for tbl, fields in (("task_mart_rows_31", None), ("landing_mart_rows_56", None),
                            ("interrupt_rows_235", None)):
            A(f"**{tbl}**")
            A(md_table(["field", "missing", "total", "missing rate"],
                       [[f, v["missing"], v["total"], v["missing_rate"]]
                        for f, v in dd["missingness"][tbl].items()]))
            A("")
        sm = dd["missingness"]["structural_missingness"]
        A(f"구조적 결측 — attempted 중 mart 전무 **{sm['attempted_targets_absent_from_all_marts']}** targets · "
          f"landing 있으나 task 없음 **{sm['landing_targets_absent_from_task_mart']}** targets")
        A("")
        A(f"*{sm['note']}*")
        A("")
        mp = dd["mart_provenance"]
        A(f"mart provenance (T3) — frozen at `{mp['snapshot_at']}` · "
          f"declared vs actual sha256 전건 일치: **{mp['all_hashes_match']}**")
    A("")

    # ── 3 RF ──
    A("## 3. RF detector")
    A("")
    r3 = s["rf_detector"]
    if r3.get("section_status") != "OK":
        A(f"`{r3['section_status']}`")
    else:
        A(f"**{r3['summary']}**")
        A("")
        rows = []
        for key, label in (("calibration_coverage", "calibration coverage"),
                           ("holdout_coverage", "holdout coverage"),
                           ("macro_f1", "macro F1"),
                           ("abstention", "abstention"),
                           ("unsafe_fp", "unsafe FP")):
            v = r3[key]
            rows.append([label, cell(v), v.get("tier"), why(v)[:150]])
        A(md_table(["지표", "값", "tier", "왜 없는가"], rows))
        A("")
        A(f"> **holdout 경계** — {r3['holdout_scope_boundary']}")
        if "abstention_caveat" in r3:
            A("")
            A(f"> **abstention grain** — {r3['abstention_caveat']}")
        A("")
        A("### LA_03_RF_MAPPING run index (T5)")
        A(md_table(["run", "plane", "status", "verdict", "metric 수"],
                   [[x["run_name"], x["plane"], x["run_status"], x["verdict"], len(x["metric_keys"])]
                    for x in r3["run_index"]]))
    A("")

    # ── 4 KWCAG ──
    A("## 4. KWCAG (Axis A)")
    A("")
    r4 = s["kwcag"]
    if r4.get("section_status") != "OK":
        A(f"`{r4['section_status']}`")
    else:
        A(f"**{r4['summary']}**")
        A("")
        A(md_table(["지표", "값", "tier", "왜 없는가"],
                   [[lab, cell(r4[k]), r4[k].get("tier"), why(r4[k])[:170]]
                    for k, lab in (("decidable_count", "decidable count"),
                                   ("decision_coverage", "DecisionCoverage"),
                                   ("undet", "UNDET"),
                                   ("criterion_level_failures", "criterion-level failures"))]))
        A("")
        A(f"> **오독 방지** — {r4.get('misreading_guard', '')}")
        A("")
        A(f"criterion result rows = {fmt(r4['criterion_rows'])} · "
          f"dim_certification rows = {fmt(r4.get('dim_certification_rows', {}))}")
    A("")

    # ── 5 Depth ──
    A("## 5. Depth (Axis B)")
    A("")
    r5 = s["depth"]
    if r5.get("section_status") != "OK":
        A(f"`{r5['section_status']}`")
    else:
        A(f"**{r5['summary']}**")
        A("")
        A(md_table(["지표", "값", "tier", "왜 없는가"],
                   [[lab, cell(r5[k]), r5[k].get("tier"), why(r5[k])[:150]]
                    for k, lab in (("ned_available", "NED available"),
                                   ("mpfed_available", "MPFED available"),
                                   ("ied_available", "IED available"),
                                   ("endpoint_reach", "endpoint reach"))]))
        A("")
        A("### endpoint_status 분포 (T3, 분모 31 task rows)")
        A(md_table(["endpoint_status", "task rows"],
                   [[k, v["value"]] for k, v in r5["endpoint_status_distribution"].items()]))
        A("")
        A(f"auth gate before endpoint: {fmt(r5['auth_gate_before_endpoint'])}")
        A("")
        A(f"archetype coverage 6/7 — 부재: `{r5['absent_archetype']['value']}` "
          f"({r5['absent_archetype']['why']})")
        A("")
        A(f"> **읽는 법** — {r5['endpoint_reach_reading']}")
    A("")

    # ── 6 Axis C ──
    A("## 6. Axis C — overlay · occlusion · interrupt")
    A("")
    r6 = s["axis_c"]
    if r6.get("section_status") != "OK":
        A(f"`{r6['section_status']}`")
    else:
        A(f"**{r6['summary']}**")
        A("")
        A(md_table(["지표", "값", "tier", "비고"],
                   [["overlay coverage available", fmt(r6["overlay_coverage_available"]), "T3",
                     f"median {r6['overlay_coverage_median']['value']} · max {r6['overlay_coverage_max']['value']}"],
                    ["semantic classified rate", fmt(r6["semantic_classified_rate"]), "T3",
                     "classification_status=DETERMINISTIC"],
                    ["UNKNOWN label share", fmt(r6["unknown_label_share"]), "T3",
                     "final_label=UNKNOWN"],
                    ["**task-bound occlusion**", cell(r6["task_bound_occlusion_available"]), "T3",
                     why(r6["task_bound_occlusion_available"])[:120]],
                    ["page-level occlusion", fmt(r6["page_level_occlusion_available"]), "T3",
                     "PAGE-LEVEL ONLY"],
                    ["observations with interrupts", fmt(r6["observations_with_interrupts"]), "T3", ""],
                    ["blocks_primary_action", fmt(r6["blocks_primary_action"]), "T3", "page-level"],
                    ["dismiss control exists", fmt(r6["dismiss_control_exists"]), "T3", ""]]))
        A("")
        A(f"> **유효 범위** — {r6['occlusion_validity_scope']}")
        A("")
        A(md_table(["classification_status", "rows", "분모"],
                   [[k, v["value"], f"{v['denominator']} interrupt rows"]
                    for k, v in r6["semantic_classification_status"].items()]))
    A("")

    # ── 7 D Research ──
    A("## 7. D Research")
    A("")
    r7 = s["d_research"]
    if r7.get("section_status") != "OK":
        A(f"`{r7['section_status']}`")
    else:
        A(f"**{r7['summary']}**")
        A("")
        A(md_table(["항목", "값", "tier"],
                   [["open research questions", fmt(r7["open_research_questions"]), "T5"],
                    ["experiments running", fmt(r7["experiments_running"]), "T5"],
                    ["supported (+partially)", fmt(r7["supported"]), "T5"],
                    ["refuted (+not supported)", fmt(r7["refuted"]), "T5"],
                    ["inconclusive (+not testable)", fmt(r7["inconclusive"]), "T5"]]))
        A("")
        A(f"> {r7['verdict_note']}")
        A("")
        lf = r7["latest_high_impact_finding"]
        if lf.get("value") in ("NONE_YET", NA):
            A(f"latest high-impact finding: **{lf['value']}** — {why(lf)}")
        else:
            A(f"**latest high-impact finding** — `{lf['rq_id']}` verdict **{lf['verdict']}** "
              f"(run `{lf['run_id'][:12]}`, {lf['started_at_kst']})")
            if lf.get("limitation"):
                A("")
                A(f"> limitation: {lf['limitation'][:300]}")
        A("")
        A("### queue (T5)")
        A(md_table(["RQ", "state", "질문"],
                   [[x["rq_id"], x["state"], x["question"]] for x in r7["queue_rows"]]))
        A("")
        cl = r7.get("claim_ledger", {})
        if "total" in cl:
            A(f"### claim ledger — D 가 재계산한 타 plane 주장 {cl['total']['value']}건 (T2)")
            A(md_table(["verdict", "claims"],
                       [[k, v["value"]] for k, v in cl["by_verdict"].items()]))
            if cl["refuted_claims"]:
                A("")
                A("**REFUTED / NOT_SUPPORTED 된 타 plane 주장**")
                A(md_table(["claim", "출처", "주장", "D 재계산"],
                           [[c["claim_id"], c["source"], c["claim"][:46], c["d_result"][:60]]
                            for c in cl["refuted_claims"]]))
    A("")

    # ── 8 C Assurance ──
    A("## 8. C Assurance")
    A("")
    r8 = s["c_assurance"]
    if r8.get("section_status") != "OK":
        A(f"`{r8['section_status']}`")
    else:
        A(f"**{r8['summary']}**")
        A("")
        A(md_table(["항목", "값", "tier"],
                   [["MATCH", fmt(r8["match"]), "T5"],
                    ["result-affecting + systemic mismatch", fmt(r8["mismatch"]), "T5"],
                    ["C completions severity C1", fmt(r8["c1"]), "T4"],
                    ["C completions severity C0", cell(r8["c0"]), "T4"],
                    ["**reproduced D findings**", cell(r8["reproduced_d_findings"]), "T4"]]))
        A("")
        if why(r8["reproduced_d_findings"]):
            A(f"> reproduced D findings 가 없는 이유 — {why(r8['reproduced_d_findings'])}")
            A("")
        A(f"> {r8['asymmetry_note']}")
        A("")
        A(md_table(["match_status (MLflow)", "C runs"],
                   [[k, v["value"]] for k, v in r8["match_status_mlflow"].items()]))
        A("")
        A(md_table(["C run", "match_status", "severity", "difference"],
                   [[x["run_name"][:38], x["match_status"], x["severity"], x["difference"][:70]]
                    for x in r8["c_run_index"]]))
    A("")
    A("---")
    A("")
    A(f"이 대시보드는 **NON_CANONICAL** 이다. D plane 산출물이며 GO 권한이 없다. "
      f"MLflow run: `{d.get('mlflow_run_id', 'PENDING')}`")
    A("")
    return "\n".join(L)


SECTION_TITLES = {
    "ops": "운영 상태",
    "data": "데이터",
    "rf_detector": "RF detector",
    "kwcag": "KWCAG",
    "depth": "Depth",
    "axis_c": "Axis C",
    "d_research": "D Research",
    "c_assurance": "C Assurance",
}


# ─────────────────────────────────────────────────────────── metrics ──

def collect_metrics(d: dict) -> dict:
    """MLflow 에 올릴 숫자 지표. 키는 영문·숫자·_-./: 만."""
    m: dict[str, float] = {}
    s = d["sections"]

    def put(k, v):
        if isinstance(v, bool):
            m[k] = float(v)
        elif isinstance(v, (int, float)):
            m[k] = float(v)

    o = s.get("ops", {})
    if o.get("section_status") == "OK":
        for p in ("A", "B", "C", "D"):
            put(f"ops.active_runs.{p}", o["active_runs_by_plane"][p]["value"])
        put("ops.open_p0", o["open_p0"]["value"])
        put("ops.open_p1", o["open_p1"]["value"])
        put("ops.p0p1_total", o["open_p0"]["denominator"])
        put("ops.unpushed_agents", o["unpushed_agents"]["value"])
        put("ops.branches_tracked", len(o["remote_exact_shas"]))
        for k, v in (o.get("subagents_by_status") or {}).items():
            if isinstance(v, dict) and isinstance(v.get("value"), int):
                put(f"ops.subagents.{k}", v["value"])
        if isinstance(o.get("subagent_total_tokens"), dict):
            put("ops.subagent_tokens_total", o["subagent_total_tokens"]["value"])

    dd = s.get("data", {})
    if dd.get("section_status") == "OK":
        ch = dd["denominator_chain"]
        for k, v in ch.items():
            put(f"data.{k}", v["value"])
        put("data.silently_dropped", dd["silently_dropped"]["value"])
        put("data.landing_without_task_row", dd["landing_without_task_row"]["value"])
        put("data.joint_valid", dd["joint_valid"]["value"])
        put("data.axis_c_only", dd["joint_valid_axis_c_only"]["value"])
        put("data.mart_hashes_all_match", dd["mart_provenance"]["all_hashes_match"])
        for tbl in ("task_mart_rows_31", "landing_mart_rows_56", "interrupt_rows_235"):
            for f, v in dd["missingness"][tbl].items():
                if v["missing_rate"] is not None:
                    put(f"missing.{tbl}.{f}", v["missing_rate"])

    r3 = s.get("rf_detector", {})
    if r3.get("section_status") == "OK":
        for k in ("calibration_coverage", "holdout_coverage", "abstention"):
            v = r3[k].get("value")
            if isinstance(v, (int, float)):
                put(f"rf.{k}", v)
        put("rf.runs_in_experiment", r3["runs_in_LA_03_RF_MAPPING"]["value"])
        # 없는 것도 수로 남긴다 — Director 가 "몇 개가 비어 있는가"를 추적할 수 있게
        put("rf.metrics_not_available",
            sum(1 for k in ("macro_f1", "unsafe_fp") if r3[k].get("value") == NA))

    r4 = s.get("kwcag", {})
    if r4.get("section_status") == "OK":
        put("kwcag.criterion_rows", r4["criterion_rows"]["value"])
        put("kwcag.not_evaluated", float(r4["decidable_count"].get("value") == "NOT_EVALUATED"))

    r5 = s.get("depth", {})
    if r5.get("section_status") == "OK":
        put("depth.task_rows", r5["task_rows"]["value"])
        for f in ("ned", "mpfed", "ied"):
            v = r5[f"{f}_available"].get("value")
            put(f"depth.{f}_available", v if isinstance(v, int) else 0)
        put("depth.endpoint_reach", r5["endpoint_reach"]["value"])
        for k, v in r5["endpoint_status_distribution"].items():
            put(f"depth.endpoint_status.{k}", v["value"])
        put("depth.auth_gate_before_endpoint", r5["auth_gate_before_endpoint"]["value"])

    r6 = s.get("axis_c", {})
    if r6.get("section_status") == "OK":
        put("axisc.overlay_available", r6["overlay_coverage_available"]["value"])
        put("axisc.overlay_median", r6["overlay_coverage_median"]["value"])
        put("axisc.semantic_classified_rate", r6["semantic_classified_rate"]["value"])
        put("axisc.unknown_label_share", r6["unknown_label_share"]["value"])
        put("axisc.page_level_occlusion_available", r6["page_level_occlusion_available"]["value"])
        put("axisc.task_bound_occlusion_available", 0)
        put("axisc.interrupt_rows", r6["interrupt_rows"]["value"])
        put("axisc.observations_with_interrupts", r6["observations_with_interrupts"]["value"])

    r7 = s.get("d_research", {})
    if r7.get("section_status") == "OK":
        put("dres.open_rq", r7["open_research_questions"]["value"])
        put("dres.experiments_running", r7["experiments_running"]["value"])
        put("dres.supported", r7["supported"]["value"])
        put("dres.refuted", r7["refuted"]["value"])
        put("dres.inconclusive", r7["inconclusive"]["value"])
        put("dres.pending", r7["pending"]["value"])
        cl = r7.get("claim_ledger", {})
        if "total" in cl:
            put("dres.claims_audited", cl["total"]["value"])
            put("dres.claims_refuted", len(cl["refuted_claims"]))

    r8 = s.get("c_assurance", {})
    if r8.get("section_status") == "OK":
        put("cassure.match", r8["match"]["value"])
        put("cassure.mismatch", r8["mismatch"]["value"])
        put("cassure.completions", r8["c_completions"]["value"])
        put("cassure.severity_c1", r8["c1"]["value"])
        v = r8["reproduced_d_findings"].get("value")
        put("cassure.reproduced_d_findings", v if isinstance(v, int) else 0)

    m["dashboard.sections_ok"] = float(sum(
        1 for v in s.values() if v.get("section_status") == "OK"))
    m["dashboard.sections_total"] = float(len(s))
    return m


# ────────────────────────────────────────────────────────────── main ──

def main() -> int:
    RESULTS.mkdir(parents=True, exist_ok=True)

    try:
        runs, exps = mlflow_runs()
        mlflow_status = "OK"
    except Exception as e:                           # noqa: BLE001
        runs, exps, mlflow_status = [], {}, f"ERROR: {type(e).__name__}: {e}"

    d = {
        "document_type": "D_DASHBOARD",
        "version": "DASHBOARD_v1",
        "authority": "NON_CANONICAL — D plane 산출물. GO 권한 없음.",
        "generated_at_kst": datetime.now(KST).isoformat(),
        "reproduce": ".venv/bin/python research_d/tools/d_dashboard.py",
        "truth_precedence": [
            "T1 raw artifact / runtime evidence / exact code SHA",
            "T2 독립 재현계산",
            "T3 frozen definition / codebook / schema / frozen mart",
            "T4 accepted SSOT / decision / agent bus 기록",
            "T5 MLflow metadata / prose / agent narrative (가장 약함)",
        ],
        "truth_precedence_note": ("MLflow run 이 존재한다는 사실만으로 결과가 승인되지 않는다. "
                                  "표의 tier 열이 그 수치를 얼마나 믿어도 되는지를 말한다."),
        "absence_vocabulary": {
            "NOT_AVAILABLE": "계산에 필요한 입력이 아직 산출되지 않았다.",
            "NOT_EVALUATED": "평가기가 실행되지 않았다. 0을 '0% 실패'로 읽으면 안 된다.",
            "NONE_YET": "일어날 수 있는 일이지만 아직 일어나지 않았다.",
        },
        "inputs": {
            "mlflow_tracking_uri": TRACKING_URI,
            "mlflow_probe_status": mlflow_status,
            "agent_bus": str(BUS),
            "frozen_mart": str(MART),
            "d_results": str(RESULTS),
        },
        "sections": {},
    }

    d["sections"]["ops"] = sec_ops(runs, exps)
    d["sections"]["data"] = sec_data()
    d["sections"]["rf_detector"] = sec_rf(runs, exps)
    d["sections"]["kwcag"] = sec_kwcag()
    d["sections"]["depth"] = sec_depth()
    d["sections"]["axis_c"] = sec_axis_c()
    d["sections"]["d_research"] = sec_d_research(runs, exps)
    d["sections"]["c_assurance"] = sec_c_assurance(runs, exps)

    metrics = collect_metrics(d)
    d["metrics_logged_to_mlflow"] = metrics

    json_path = RESULTS / "D_DASHBOARD.json"
    md_path = RESULTS / "D_DASHBOARD.md"
    json_path.write_text(json.dumps(d, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    md_path.write_text(render_md(d), encoding="utf-8")

    # ── MLflow 스냅샷 (결과 파일을 먼저 쓴 뒤 run 을 연다 → result_sha 가 실제 산출물을 가리킨다) ──
    run_id = "NOT_LOGGED"
    try:
        sys.path.insert(0, str(RD / "tools"))
        import mlflow
        import mlflow_contract as C

        with C.research_run(
                experiment="LA_10_RESEARCH_D", run_name="D_DASHBOARD snapshot",
                plane="D", agent_id="D", subagent_id="worker/dashboard",
                objective="Research Director 가 전체 상태를 한 화면에서 감시할 수 있는 스냅샷",
                method="MLflow + agent bus + frozen mart + D results 집계",
                dataset_grain="mixed — 섹션별 grain 명시",
                n_expected=59, n_observed=56,
                hypothesis_id="NONE", claim_kind="OBSERVATION",
                ticket_id="NONE", phase="I1", split="none",
                parent_run_id="NONE",
                result_path=json_path,
                model_or_rule_version="DASHBOARD_v1",
                extra_tags={"rq_id": "D-DASHBOARD"}) as run:
            run_id = run.info.run_id
            mlflow.log_metrics(metrics)
            mlflow.log_artifact(str(md_path), artifact_path="result")
            mlflow.log_artifact(str(json_path), artifact_path="result")
            C.finish(
                verdict="NOT_TESTABLE",
                limitation=(
                    "대시보드는 가설을 검정하지 않는다 — 상태 스냅샷이므로 verdict 는 NOT_TESTABLE 이다. "
                    "한계: (1) open P0/P1 은 ack/completion **파일 존재**로만 판정하며 내용상 해소 여부는 "
                    "보지 않는다. (2) active runs 는 MLflow tag 이므로 프로세스가 죽어도 RUNNING 으로 남는다 "
                    "— 생존 증거가 아니다. (3) RF detector 의 macro F1·unsafe FP 와 KWCAG 전 지표는 "
                    "입력이 없어 NOT_AVAILABLE/NOT_EVALUATED 이며 추정하지 않았다. (4) holdout 은 C 영역이라 "
                    "분할 크기만 MLflow 요약에서 읽었고 라벨 내용은 열지 않았다. (5) 이 스냅샷은 실행 시점의 "
                    "bus/mart/MLflow 상태이며 bus 는 라이브다 — 재실행하면 값이 달라진다."))
    except Exception as e:                           # noqa: BLE001
        run_id = f"ERROR: {type(e).__name__}: {e}"

    d["mlflow_run_id"] = run_id
    json_path.write_text(json.dumps(d, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    md_path.write_text(render_md(d), encoding="utf-8")

    print(f"[D_DASHBOARD] {d['generated_at_kst']}")
    for k, v in d["sections"].items():
        print(f"  {k:<14} {v.get('section_status')}")
    print(f"  metrics        {len(metrics)}")
    print(f"  mlflow run_id  {run_id}")
    print(f"  wrote          {json_path}")
    print(f"  wrote          {md_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
