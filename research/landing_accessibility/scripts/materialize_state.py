#!/usr/bin/env python3
"""v4.0 §6 A0 — control/state.json 의 derived field 를 promoted artifact 에서 계산한다.

state summary 와 실제 artifact 가 다르면 **state summary 를 수정한다.**
artifact 를 summary 에 맞추지 않는다.
"""
from __future__ import annotations
import json, subprocess, sys, tempfile, pathlib

REPO = "/home/sieg/projects-wsl/ProjectFinal"
CTRL = pathlib.Path(REPO) / ".agent_worktrees/landing_orchestrator/research/landing_accessibility"


def _sh(cmd: str) -> str:
    return subprocess.run(cmd, shell=True, capture_output=True, text=True).stdout.strip()


def extract(sha: str) -> pathlib.Path:
    """promoted SHA 의 트리를 임시 디렉터리로 추출한다."""
    t = pathlib.Path(tempfile.mkdtemp())
    subprocess.run(
        f"git -C {REPO} archive {sha} research/landing_accessibility | tar -x -C {t}",
        shell=True, capture_output=True,
    )
    return t / "research/landing_accessibility"


def derive(root: pathlib.Path) -> dict:
    import pandas as pd
    d: dict = {}
    st = root / "state"

    def pq(name):
        p = st / f"{name}.parquet"
        return pd.read_parquet(p) if p.exists() else None

    rows, panels = pq("source_ranking_rows"), pq("panel_registry")
    svc, alias = pq("service_master"), pq("entity_alias_map")
    memb, wtg = pq("source_membership"), pq("web_target_group")

    if rows is not None:
        d["source_rows"] = len(rows)
        d["source_row_ids_unique"] = int(rows["source_row_id"].nunique())
        if "domain" in rows:
            d["rows_by_domain"] = rows["domain"].value_counts().to_dict()
    if panels is not None:
        d["panels"] = len(panels)
        if "axis_type" in panels:
            d["panels_by_axis"] = panels["axis_type"].value_counts().to_dict()
    if svc is not None:
        d["measurement_entities"] = len(svc)
        for col in ("domain", "axis_type", "web_eligibility_status", "review_decision"):
            if col in svc:
                d[f"entities_by_{col}"] = svc[col].value_counts(dropna=False).to_dict()
        for col in ("needs_human_review", "eligibility_needs_human_review", "eligibility_needs_review"):
            if col in svc:
                d[col] = int(svc[col].fillna(False).astype(bool).sum())
    if alias is not None:
        d["entity_aliases"] = len(alias)
    if memb is not None:
        d["source_membership"] = len(memb)
    if wtg is not None:
        d["web_target_groups"] = len(wtg)
        if "grouping_status" in wtg:
            d["web_targets_by_status"] = wtg["grouping_status"].value_counts().to_dict()
        for col in ("web_target_url", "official_landing_url"):
            if col in wtg:
                d[f"{col}_null"] = int(wtg[col].isna().sum())

    cert = root / "sources/certification/certification_registry.parquet"
    if cert.exists():
        c = pd.read_parquet(cert)
        d["certification_rows"] = len(c)
        if "cert_valid_candidate" in c:
            d["certification_valid_at_audit"] = int((c["cert_valid_candidate"] == 1).sum())

    d["evidence_dir_present"] = (root / "evidence").exists()
    return d


def main() -> int:
    s = json.loads((CTRL / "control/state.json").read_text(encoding="utf-8"))
    promoted = s.get("promotion_policy", {}).get("promoted_sha")
    if not promoted:
        print("promoted_sha 없음", file=sys.stderr)
        return 1

    root = extract(promoted)
    derived = derive(root)

    derived["latest_promoted_sha"] = promoted
    derived["latest_exec_sha"] = _sh(f"git -C {REPO} rev-parse agent/landing-exec")
    derived["latest_adversarial_sha"] = _sh(f"git -C {REPO} rev-parse audit/landing-adversarial")
    derived["latest_ssot_sha"] = _sh(f"git -C {REPO} rev-parse audit/landing-ssot")
    al = s.get("audit_lag", {})
    fully = (al.get("latest_adversarial_target_sha") == derived["latest_exec_sha"]
             and al.get("latest_ssot_target_sha") == derived["latest_exec_sha"])
    derived["unaudited_cycle_depth"] = 0 if fully else 1
    derived["open_p0"] = len(s.get("open_p0", []))
    derived["open_p1"] = len(s.get("open_p1", []))
    p2 = s.get("open_p2", [])
    derived["open_p2_total"] = len(p2)
    derived["open_p2_by_state"] = {}
    for x in p2:
        k = x.get("state", "OPEN")
        derived["open_p2_by_state"][k] = derived["open_p2_by_state"].get(k, 0) + 1
    derived["open_p2_by_class"] = {}
    for x in p2:
        k = x.get("debt_class", "UNCLASSIFIED")
        derived["open_p2_by_class"][k] = derived["open_p2_by_class"].get(k, 0) + 1

    prev = s.get("derived_from_artifacts", {})
    drift = {k: {"was": prev.get(k), "now": v} for k, v in derived.items()
             if k in prev and prev[k] != v}

    s["derived_from_artifacts"] = derived
    s["derived_source_sha"] = promoted
    s["derived_at"] = _sh("date -Iseconds")
    if drift:
        s.setdefault("state_drift_corrections", []).append(
            {"at": s["derived_at"], "source_sha": promoted, "drift": drift,
             "policy": "state summary 를 artifact 에 맞춰 수정했다. 역방향 금지."}
        )
    (CTRL / "control/state.json").write_text(
        json.dumps(s, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps({"promoted_sha": promoted[:12], "drift_count": len(drift),
                      "derived": derived}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
