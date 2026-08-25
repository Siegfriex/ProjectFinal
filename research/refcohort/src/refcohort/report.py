"""기사 §5 실증 검증용 집계.

네 산출 변수를 하나의 '접근성 점수'로 합산하지 않는다(프로토콜 v2 §9).
  observed_accessibility_failure_count / task_coverage_difference /
  certification_status / reference_deviation_score(미산출)
"""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path

CODEBOOK = json.loads(
    (Path(__file__).parents[2] / "codebook" / "kwcag22_criteria.json").read_text(encoding="utf-8")
)
CRITERIA_META = {c["id"]: c for c in CODEBOOK["criteria"]}


def _measured(records: list[dict]) -> list[dict]:
    return [r for r in records if r.get("collection_status") == "MEASURED" and r.get("criteria")]


def criterion_table(records: list[dict]) -> list[dict]:
    """검사항목별 통과/미흡 집계 — 기사 §5의 '항목별 정리'."""
    m = _measured(records)
    rows = []
    for cid, meta in CRITERIA_META.items():
        states = Counter()
        opp_total = opp_pass = opp_fail = 0
        services_fail = []
        for r in m:
            c = (r.get("criteria") or {}).get(cid)
            if not c:
                continue
            states[c["verdict_state"]] += 1
            opp_total += c["applicable_count"]
            opp_pass += c["pass_count"]
            opp_fail += c["fail_count"]
            if c["verdict_state"] == "FAIL":
                services_fail.append(r["service_name"])
        applicable_services = states["PASS"] + states["FAIL"]
        rows.append(
            {
                "criterion_id": cid,
                "criterion_name": meta["name"],
                "principle": meta["principle"],
                "guideline": meta["guideline"],
                "automation": meta["automation"],
                "services_applicable": applicable_services,
                "services_pass": states["PASS"],
                "services_fail": states["FAIL"],
                "services_na": states["NA"],
                "services_undetermined": states["UNDETERMINED"],
                "service_fail_rate": round(states["FAIL"] / applicable_services, 4)
                if applicable_services
                else None,
                "opportunities_total": opp_total,
                "opportunities_pass": opp_pass,
                "opportunities_fail": opp_fail,
                "opportunity_pass_rate": round(opp_pass / opp_total, 4) if opp_total else None,
                "failing_services_sample": services_fail[:12],
            }
        )
    rows.sort(key=lambda r: (-(r["service_fail_rate"] or -1), r["criterion_id"]))
    return rows


def cohort_summary(records: list[dict], cohort: str) -> dict:
    rs = [r for r in records if r.get("cohort") == cohort]
    m = _measured(rs)
    fails = [r["summary"]["criteria_fail"] for r in m]
    strict = Counter(r["summary"]["observed_strict_pass"] for r in m)
    return {
        "cohort": cohort,
        "targets": len(rs),
        "measured": len(m),
        "blocked": len(rs) - len(m),
        "blocked_reasons": dict(Counter(r.get("failure_code") for r in rs if r not in m)),
        "observed_strict_pass": dict(strict),
        "strict_pass_rate": round(strict["TRUE"] / len(m), 4) if m else None,
        "failed_criteria_per_service": {
            "mean": round(sum(fails) / len(fails), 2) if fails else None,
            "min": min(fails) if fails else None,
            "max": max(fails) if fails else None,
            "distribution": dict(sorted(Counter(fails).items())),
        },
        "observed_accessibility_failure_count_total": sum(
            r["summary"]["observed_accessibility_failure_count"] for r in m
        ),
        "opportunities_total": sum(r["summary"]["total_opportunities"] for r in m),
    }


def by_task_code(records: list[dict]) -> list[dict]:
    m = _measured(records)
    g = defaultdict(list)
    for r in m:
        g[(r["cohort"], r["primary_task_code"])].append(r)
    out = []
    for (cohort, code), rs in sorted(g.items()):
        fails = [r["summary"]["criteria_fail"] for r in rs]
        out.append(
            {
                "cohort": cohort,
                "primary_task_code": code,
                "measured": len(rs),
                "mean_failed_criteria": round(sum(fails) / len(fails), 2),
                "strict_pass": sum(1 for r in rs if r["summary"]["observed_strict_pass"] == "TRUE"),
            }
        )
    return out


def coverage_gaps(records: list[dict]) -> dict:
    """task_coverage_difference — 관측 범위 차이. 결함의 대리변수가 아니다."""
    m = _measured(records)
    g = defaultdict(Counter)
    for r in m:
        g[r["cohort"]][r.get("observability_scope") or "NOT_OBSERVED"] += 1
    gates = defaultdict(Counter)
    for r in m:
        gates[r["cohort"]][r.get("gated_boundary_tag") or "NONE"] += 1
    return {
        "observability_scope": {k: dict(v) for k, v in g.items()},
        "gated_boundary_tag": {k: dict(v) for k, v in gates.items()},
    }


def build(records: list[dict], run_id: str, audit_date: str) -> dict:
    m = _measured(records)
    return {
        "run_id": run_id,
        "audit_date": audit_date,
        "codebook_version": CODEBOOK["codebook_version"],
        "records_total": len(records),
        "records_measured": len(m),
        "cohorts": [cohort_summary(records, c) for c in ("REFERENCE", "COMPARISON")],
        "criterion_table": criterion_table(records),
        "by_task_code": by_task_code(records),
        "coverage": coverage_gaps(records),
        "nulls_preserved": dict.fromkeys(
            (
                "reference_distribution",
                "cluster_label",
                "reference_deviation_score",
                "reference_percentile",
                "commercial_distance",
            )
        ),
        "interpretation_limits": [
            "검사항목별 결과는 각 서비스의 관측된 모바일 공개 화면 1개에 대한 것이며 사이트 전체 적합성이 아니다.",
            "AUTO_FLAG_ONLY 항목의 FAIL은 사람 검토 전 자동 신호이며 최종 판정이 아니다.",
            "NA는 적용기회 부재이고 PASS가 아니다. UNDETERMINED는 관측 한계이며 무결점이 아니다.",
            "인증 보유 여부는 후보 자격 근거일 뿐, 관측 FAIL 수와 결합해 인증 적부를 주장하지 않는다.",
        ],
    }
