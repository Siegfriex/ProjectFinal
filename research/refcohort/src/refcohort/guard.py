"""contract-guard — 자율 실행 중 계약 드리프트를 감시한다.

무인 루프의 실질 위험은 크래시가 아니라 판정 완화 드리프트다.
각 tick 종료 시 아래 불변식을 검사하고, 하나라도 깨지면 루프를 정지시킨다.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

NULLS_PRESERVED = [
    "reference_distribution",
    "cluster_label",
    "reference_deviation_score",
    "reference_percentile",
    "commercial_distance",
]
OX = {"O", "X", "UNKNOWN", "NA"}
VERDICTS = {"PASS", "FAIL", "NA", "UNDETERMINED"}
STRICT = {"TRUE", "FALSE", "UNDETERMINED", "NA"}
SCOPE_RELATIONS = {
    "EXACT_URL",
    "SAME_ORIGIN_PATH",
    "MOBILE_SUBDOMAIN_REDIRECT",
    "EXTERNAL_PARTNER_DOMAIN",
    "UNRESOLVED",
}
GATE_TAGS = {
    "NONE",
    "LOGIN_REQUIRED",
    "IDENTITY_VERIFICATION_REQUIRED",
    "PAYMENT_REQUIRED",
    "PERSONAL_DATA_REQUIRED",
    "CAPTCHA_REQUIRED",
    "OTHER",
}
OBS_SCOPES = {"LANDING_ONLY", "TASK_ENTRY", "PRE_COMPLETION", "COMPLETION", "NOT_OBSERVED"}
MIN_REFERENCE_FOR_CLUSTER = 8  # 프로토콜 v2 §7


class Violation(dict):
    pass


def _v(rule: str, detail: str, severity: str = "ERROR", sample: Any = None) -> Violation:
    return Violation(rule=rule, detail=detail, severity=severity, sample=sample)


def check_records(records: list[dict]) -> list[Violation]:
    out: list[Violation] = []

    # 1. nulls_preserved: 산출 금지 변수가 값을 갖지 않았는가
    for r in records:
        for k in NULLS_PRESERVED:
            if r.get(k) is not None:
                out.append(_v("nulls_preserved", f"{k} 가 계산됨", sample=r.get("record_id")))

    # 2. NA / UNDETERMINED 를 PASS 나 0 으로 환산하지 않았는가
    for r in records:
        for cid, c in (r.get("criteria") or {}).items():
            st = c.get("verdict_state")
            if st not in VERDICTS:
                out.append(
                    _v("verdict_enum", f"{cid} verdict_state={st}", sample=r.get("record_id"))
                )
            if st == "NA" and (c.get("metric") is not None or c.get("pass_count")):
                out.append(
                    _v(
                        "na_not_pass",
                        f"{cid} 적용기회 없음인데 metric/pass 존재",
                        sample=r.get("record_id"),
                    )
                )
            if c.get("observed_strict_pass") not in STRICT:
                out.append(
                    _v(
                        "strict_enum",
                        f"{cid} strict={c.get('observed_strict_pass')}",
                        sample=r.get("record_id"),
                    )
                )
            if st == "UNDETERMINED" and c.get("observed_strict_pass") == "TRUE":
                out.append(
                    _v(
                        "undetermined_not_true",
                        f"{cid} UNDETERMINED가 TRUE로",
                        sample=r.get("record_id"),
                    )
                )

    # 3. enum 무결성
    for r in records:
        if r.get("scope_relation") and r["scope_relation"] not in SCOPE_RELATIONS:
            out.append(
                _v("scope_relation_enum", str(r["scope_relation"]), sample=r.get("record_id"))
            )
        if r.get("gated_boundary_tag") and r["gated_boundary_tag"] not in GATE_TAGS:
            out.append(_v("gate_tag_enum", str(r["gated_boundary_tag"]), sample=r.get("record_id")))
        if r.get("observability_scope") and r["observability_scope"] not in OBS_SCOPES:
            out.append(
                _v("obs_scope_enum", str(r["observability_scope"]), sample=r.get("record_id"))
            )

    # 4. 게이트 경계 이후를 관측했다고 주장하지 않았는가
    for r in records:
        if r.get("gated_boundary_tag") not in (None, "NONE") and r.get("observability_scope") in (
            "PRE_COMPLETION",
            "COMPLETION",
        ):
            out.append(
                _v(
                    "gate_boundary_respected",
                    f"게이트 {r['gated_boundary_tag']} 뒤 범위 {r['observability_scope']} 주장",
                    sample=r.get("record_id"),
                )
            )

    # 5. 증거 없이 판정하지 않았는가
    for r in records:
        if r.get("criteria") and not r.get("evidence_complete"):
            applicable = sum(
                1 for c in r["criteria"].values() if c.get("verdict_state") in ("PASS", "FAIL")
            )
            if applicable:
                out.append(
                    _v(
                        "no_verdict_without_evidence",
                        f"증거 불완전인데 {applicable}개 항목 판정",
                        severity="WARN",
                        sample=r.get("record_id"),
                    )
                )

    # 6. 물리 mm 를 주판정으로 쓰지 않았는가
    for r in records:
        if (
            r.get("physical_mm_estimate") is not None
            and r.get("physical_mm_estimate_method") != "MEASURED_DEVICE"
        ):
            out.append(
                _v("physical_mm_not_primary", "실측 없이 물리 mm 산출", sample=r.get("record_id"))
            )

    return out


def check_cohort(records: list[dict], cluster_declared: bool = False) -> list[Violation]:
    """표본 수 대비 주장 수준을 검사한다."""
    out: list[Violation] = []
    by_type: dict[str, int] = {}
    for r in records:
        t = r.get("primary_task_code") or r.get("service_type") or "UNKNOWN"
        by_type[t] = by_type.get(t, 0) + 1
    if cluster_declared:
        thin = {k: n for k, n in by_type.items() if n < MIN_REFERENCE_FOR_CLUSTER}
        if thin:
            out.append(
                _v(
                    "cluster_min_sample",
                    f"유형당 {MIN_REFERENCE_FOR_CLUSTER}개 미만인데 군집 선언: {thin}",
                )
            )
    return out


def check_append_only(run_dir: Path, baseline: dict[str, str] | None) -> list[Violation]:
    """이전 run 산출물이 수정되지 않았는지 해시로 대조한다."""
    out: list[Violation] = []
    if not baseline:
        return out
    for rel, expect in baseline.items():
        p = run_dir / rel
        if not p.exists():
            out.append(_v("append_only", f"이전 산출물 사라짐: {rel}"))
            continue
        import hashlib

        got = "sha256:" + hashlib.sha256(p.read_bytes()).hexdigest()
        if got != expect:
            out.append(_v("append_only", f"이전 산출물 변경됨: {rel}"))
    return out


def run_guard(records: list[dict], *, cluster_declared: bool = False) -> dict:
    v = check_records(records) + check_cohort(records, cluster_declared)
    errors = [x for x in v if x["severity"] == "ERROR"]
    return {
        "checked_records": len(records),
        "violations": v,
        "error_count": len(errors),
        "warn_count": len(v) - len(errors),
        "status": "HALT" if errors else ("WARN" if v else "OK"),
    }


def write_guard_report(result: dict, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
