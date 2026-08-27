"""RQ-D1 — E001 pilot failure anatomy 재구성 (독립 재계산).

A/B/C의 보고문을 입력으로 쓰지 않는다.
입력은 raw evidence 디렉터리와 frozen mart JSON뿐이다.

산출:
    results/RQ_D1_reconstruction.json
"""
from __future__ import annotations

import json
import re
import statistics as st
from collections import Counter, defaultdict
from pathlib import Path

REPO = Path("/home/sieg/projects-wsl/ProjectFinal")
EVIDENCE_ROOTS = {
    f"w{n}": REPO / f".agent_worktrees/claude_b_e001_worker_{n}/artifacts/e001_w{n}/evidence"
    for n in ("01", "02", "03", "04")
}
MART = REPO / ".agent_worktrees/claude_b_analysis_current/artifacts/e001_real_marts"
RUN_DIR_RE = re.compile(r"^e001_full-wtg_(?P<wtg>[0-9a-f]+)-(?P<ts>.+)$")
TS_RE = re.compile(r"^(\d{4})-(\d{2})-(\d{2})T(\d{2})(\d{2})(\d{2})(\d{6})Z$")

# 짧은 간격 / 긴 간격을 가르는 경계. 관측된 두 군집(6~8s vs 46~47s) 사이는
# 비어 있어 어떤 값을 잡아도 같은 분할이 나온다. 중앙의 20s를 쓴다.
GAP_SPLIT_SECONDS = 20.0


def parse_ts(ts: str) -> float:
    m = TS_RE.match(ts)
    if not m:
        raise ValueError(ts)
    _, _, day, hh, mm, ss, us = m.groups()
    return int(day) * 86400 + int(hh) * 3600 + int(mm) * 60 + int(ss) + int(us) / 1e6


def scan_evidence() -> list[dict]:
    rows = []
    for worker, root in EVIDENCE_ROOTS.items():
        for d in sorted(p for p in root.iterdir() if p.is_dir()):
            m = RUN_DIR_RE.match(d.name)
            if not m:
                continue
            man = d / "manifest.jsonl"
            entries = []
            if man.exists():
                entries = [json.loads(line) for line in man.read_text().splitlines() if line.strip()]
            rows.append({
                "worker": worker,
                "wtg": m["wtg"],
                "ts_raw": m["ts"],
                "t": parse_ts(m["ts"]),
                "dir": d.name,
                "sealed": (d / "run.json").exists(),
                "artifact_count": len(entries),
                "artifact_bytes": sum(e["bytes"] for e in entries),
                "observation_ids": sorted({e["observation_id"] for e in entries}),
            })
    return rows


def classify_repeats(rows: list[dict]) -> dict:
    by_wtg = defaultdict(list)
    for r in rows:
        by_wtg[r["wtg"]].append(r)
    repeats = {}
    for wtg, group in by_wtg.items():
        if len(group) < 2:
            continue
        group = sorted(group, key=lambda r: r["t"])
        gap = group[-1]["t"] - group[0]["t"]
        sealed = [r["sealed"] for r in group]
        counts = [r["artifact_count"] for r in group]
        if all(sealed) and all(c > 0 for c in counts):
            kind = "DUPLICATE_LAUNCH_BOTH_COMPLETE"
        elif not any(sealed) and not any(counts):
            kind = "RETRY_BOTH_EMPTY"
        else:
            kind = "MIXED_PARTIAL"
        repeats[wtg] = {
            "n_attempts": len(group),
            "workers": sorted({r["worker"] for r in group}),
            "gap_seconds": round(gap, 3),
            "gap_class": "SHORT" if gap < GAP_SPLIT_SECONDS else "LONG",
            "sealed": sealed,
            "artifact_counts": counts,
            "identical_artifact_count": len(set(counts)) == 1,
            "classification": kind,
            "dirs": [r["dir"] for r in group],
        }
    return repeats


def load_mart() -> dict:
    def rd(name):
        return json.loads((MART / name).read_text())
    return {
        "landing": rd("fact_landing_observation.json"),
        "task": rd("fact_task_entry.json"),
        "interrupt": rd("fact_interrupt_element.json"),
        "criterion": rd("fact_criterion_result.json"),
    }


def main() -> int:
    rows = scan_evidence()
    repeats = classify_repeats(rows)
    mart = load_mart()

    raw_wtg = {r["wtg"] for r in rows}
    empty_wtg = {w for w in raw_wtg if all(r["artifact_count"] == 0 for r in rows if r["wtg"] == w)}
    mart_wtg = {re.sub(r"^e001_full-wtg_([0-9a-f]+)-.*", r"\1", r["evidence_run_id"])
                for r in mart["landing"]}

    land_targets = {r["web_target_id"] for r in mart["landing"]}
    task_targets = {r["web_target_id"] for r in mart["task"]}
    mart_obs = {r["observation_id"] for r in mart["landing"]}
    interrupt_obs = {r["observation_id"] for r in mart["interrupt"]}

    cov = [r["max_overlay_coverage"] for r in mart["landing"] if r["max_overlay_coverage"] is not None]
    occ = [r["max_primary_action_occlusion"] for r in mart["landing"]
           if r.get("max_primary_action_occlusion") is not None]

    out = {
        "rq": "RQ-D1",
        "title": "E001 pilot failure anatomy — 독립 재구성",
        "grain": "observation_dir | web_target_group(wtg) | mart row",
        "evidence": {
            "observation_dirs": len(rows),
            "distinct_wtg": len(raw_wtg),
            "repeat_wtg": len(repeats),
            "empty_dirs": sum(1 for r in rows if r["artifact_count"] == 0),
            "sealed_dirs": sum(1 for r in rows if r["sealed"]),
            "total_artifact_bytes": sum(r["artifact_bytes"] for r in rows),
            "per_worker": {w: sum(1 for r in rows if r["worker"] == w) for w in EVIDENCE_ROOTS},
        },
        "repeat_classification": {
            "by_kind": Counter(v["classification"] for v in repeats.values()),
            "by_gap_class": Counter(v["gap_class"] for v in repeats.values()),
            "detail": repeats,
        },
        "total_failure_targets": {
            "n": len(empty_wtg),
            "wtg": sorted(empty_wtg),
            "note": "두 시도 모두 run.json/manifest 없음. mart에 행이 존재하지 않음.",
        },
        "denominator_chain": {
            "observation_dirs": len(rows),
            "distinct_targets_attempted": len(raw_wtg),
            "targets_with_any_evidence": len(raw_wtg - empty_wtg),
            "targets_in_landing_mart": len(land_targets),
            "targets_in_task_mart": len(task_targets),
            "targets_dropped_silently": sorted(raw_wtg - mart_wtg),
            "landing_targets_without_task_row": len(land_targets - task_targets),
        },
        "mart_integrity": {
            "landing_rows": len(mart["landing"]),
            "landing_distinct_observation_id": len(mart_obs),
            "duplicate_observation_rows": len(mart["landing"]) - len(mart_obs),
            "interrupt_rows": len(mart["interrupt"]),
            "interrupt_orphan_observations": len(interrupt_obs - mart_obs),
            "criterion_rows": len(mart["criterion"]),
        },
        "axis_availability": {
            "axis_a_criterion_rows": len(mart["criterion"]),
            "axis_b_NED_non_null": sum(1 for r in mart["task"] if r["NED"] is not None),
            "axis_b_IED_non_null": sum(1 for r in mart["task"] if r["IED"] is not None),
            "axis_b_MPFED_non_null": sum(1 for r in mart["task"] if r["MPFED"] is not None),
            "axis_b_task_rows": len(mart["task"]),
            "axis_c_overlay_coverage_non_null": len(cov),
            "axis_c_overlay_coverage_median": round(st.median(cov), 4) if cov else None,
            "axis_c_overlay_coverage_max": max(cov) if cov else None,
            "axis_c_primary_action_occlusion_non_null": len(occ),
        },
        "archetype_coverage": {
            "in_task_mart": Counter(r["interaction_archetype"] for r in mart["task"]),
            "frozen_archetypes": ["QUERY", "CONTENT_OPEN", "ITEM_DETAIL", "PLACE_LOOKUP",
                                  "COMMUNICATION_ENTRY", "FINANCIAL_ACTION_ENTRY", "UTILITY_ENTRY"],
        },
        "endpoint_status": Counter(r["endpoint_status"] for r in mart["task"]),
        "measurement_status": Counter(r["measurement_status"] for r in mart["landing"]),
    }
    out["archetype_coverage"]["absent_archetypes"] = sorted(
        set(out["archetype_coverage"]["frozen_archetypes"])
        - set(out["archetype_coverage"]["in_task_mart"])
    )

    res = Path(__file__).resolve().parents[1] / "results"
    res.mkdir(exist_ok=True)
    (res / "RQ_D1_reconstruction.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=2, default=dict) + "\n", encoding="utf-8")
    print(json.dumps(out, ensure_ascii=False, indent=2, default=dict))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
