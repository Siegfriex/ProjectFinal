"""instrument_version × target × observable_variable 매트릭스.

**22 건을 하나의 clean sample 로 다루지 않는다.** 네 계기 버전이 섞여 있고
회차마다 무엇을 관측할 수 있었는지가 다르다. 먼저 각 건이 **어느 계기로 관측됐고
어떤 변수가 실제로 살아 있는지**를 붙인다. 그 다음에야 **같은 정의로 비교 가능한
변수에 대해서만** 분석한다 — 축마다 n 이 다시 달라진다.

정의는 raw 에서 직접 읽는다. mart 파생값(B 사후 DOM 추출)을 섞으면 census 8 과
probe 14 가 다른 정의가 된다.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

A = Path("/home/sieg/projects-wsl/ProjectFinal/artifacts")

# C 검산본 union 22 (C-ASSURANCE-130648)
COHORT = {
    "census": ["F1-03", "F1-05", "F2-01", "F2-08", "F3-02", "F3-06", "F5-02", "F5-05"],
    "v2":     ["F3-01", "F3-03", "F3-07"],
    "v3":     ["F2-02", "F2-05", "F2-06", "F2-07", "F2-09", "F2-10", "F4-09", "F5-01"],
    "v4":     ["F3-04", "F4-01", "F4-10"],
}
ROOTS = {
    "census": A / "v3_census/raw/E",
    "v2":     A / "v3_probe_v2/raw",
    "v3":     A / "v3_probe_v3/raw",
    "v4":     A / "v3_probe_v4/raw",
}
AX_STUB_MAX = 200          # 60B 오류 스텁 + 여유. 실제 트리는 KB 단위다
MENU_ACTIONS = ("OPEN_GLOBAL_MENU", "OPEN_MENU", "EXPAND")


def _target_runs(version: str, tid: str) -> list:
    """그 계기에서 이 target 의 **모든 run 디렉터리**. 오래된 것부터.

    [발행 전 포착] 처음엔 최신 mtime 하나만 골랐다. census 는 R1/R2/R2B/R3 가
    공존하고 **R3 는 geometry 보충 전용 run** 이라, 최신을 고르면 census 8 건의
    geometry 가 전부 R3 에서 읽히면서 `geometry 22/22` 라는 부풀린 값이 나온다.
    R1 에는 bbox 가 없다 — 확인했다.

    **한 target 안에서 변수마다 다른 run 을 읽으면 그것이 계기 혼입이다.**
    run 을 나열하고 **변수마다 어느 run 에서 왔는지 적는다**.
    """
    root = ROOTS[version]
    if not root.exists():
        return []
    cands = [p for p in root.rglob(tid) if p.is_dir()
             and list(p.glob("E_ROUTE_CANDIDATE_*.json"))]
    return sorted(cands, key=lambda p: p.stat().st_mtime)


def _primary_run(version: str, tid: str) -> Path | None:
    """**판정 근거 run** — 그 계기에서 처음(가장 이른) 산출.

    census 8 건의 도달 판정은 R1 에서 났다. R3 는 그 뒤 geometry 를 덧붙인 것이다.
    """
    runs = _target_runs(version, tid)
    return runs[0] if runs else None


def _ax_alive(d: Path) -> dict:
    """browser-computed AX 가 **독립 관측**됐는가. 60B 스텁은 아니다."""
    out = {}
    for f in sorted(d.glob("*.ax.json")):
        n = f.stat().st_size
        nodes = None
        if n > AX_STUB_MAX:
            try:
                j = json.loads(f.read_text(encoding="utf-8"))
                nodes = len(json.dumps(j))          # 크기 대용 — 구조는 회차마다 다르다
            except Exception:
                nodes = None
        out[f.name] = {"bytes": n, "alive": n > AX_STUB_MAX}
    alive = any(v["alive"] for v in out.values())
    return {"files": out, "independently_captured": alive}


def _seq(route) -> list:
    """route 에서 **조작 스텝만** 뽑는다. terminal 은 결과이지 조작이 아니다."""
    if not isinstance(route, list):
        return []
    return [s.get("action") for s in route
            if isinstance(s, dict) and s.get("action")]


def _geometry(d: Path, tid: str) -> dict:
    """trace 에 클릭 좌표/bbox 가 남았는가."""
    tr = list(d.glob("E_SCOUT_TRACE_*.jsonl"))
    if not tr:
        return {"present": False, "why": "no trace file"}
    box = xy = None
    for line in tr[0].read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            j = json.loads(line)
        except Exception:
            continue
        s = json.dumps(j, ensure_ascii=False)
        if box is None and re.search(r'"(bbox|box)"', s):
            for k in ("bbox", "box"):
                v = j.get(k) or (j.get("selected_candidate") or {}).get(k) \
                    if isinstance(j.get("selected_candidate"), dict) else j.get(k)
                if isinstance(v, dict) and "x" in v:
                    box = v
        if xy is None:
            for k in ("click_xy", "click_used", "clicked_at"):
                v = j.get(k)
                if isinstance(v, (list, tuple)) and len(v) == 2 and v[0] is not None:
                    xy = list(v)
    return {"present": bool(box or xy), "bbox": box, "click_xy": xy}


def row(version: str, tid: str) -> dict:
    runs = _target_runs(version, tid)
    d = _primary_run(version, tid)
    if d is None:
        return {"target_id": tid, "instrument": version, "found": False,
                "note": "산출 디렉터리를 찾지 못했다"}
    rc = list(d.glob("E_ROUTE_CANDIDATE_*.json"))[0]
    j = json.loads(rc.read_text(encoding="utf-8"))
    route = j.get("route")
    seq = _seq(route)
    ax = _ax_alive(d)
    # geometry 는 **판정 근거 run 에서만** 본다. 보충 run 을 섞으면 계기가 혼입된다.
    geo = _geometry(d, tid)
    # 보충 run 에 geometry 가 따로 있으면 **별도 축으로** 기록한다 — 합치지 않는다
    geo_supp = None
    for r2 in runs[1:]:
        g2 = _geometry(r2, tid)
        if g2["present"]:
            geo_supp = {"run": str(r2.relative_to(A)), **g2}
            break
    term = None
    if isinstance(route, list):
        for s in route:
            if isinstance(s, dict) and s.get("terminal"):
                term = s["terminal"]
    labels = [s.get("label") for s in (route or [])
              if isinstance(s, dict) and s.get("label")]
    return {
        "target_id": tid,
        "instrument": version,
        "run_dir": str(d.relative_to(A)),
        "found": True,
        # ── 관측 가능 변수 ──
        "endpoint_predicate": j.get("scout_status"),
        "terminal_in_route": term,
        "sequence": seq,
        "sequence_len": len(seq),
        "sequence_present": len(seq) > 0,
        "depth_value": j.get("task_activation_depth"),
        "depth_present": j.get("task_activation_depth") is not None and len(seq) > 0,
        "menu_dependency": any(a in MENU_ACTIONS for a in seq) if seq else None,
        "menu_present": len(seq) > 0,
        "ax_independently_captured": ax["independently_captured"],
        "ax_files": ax["files"],
        "entry_labels": labels,
        "label_present": len(labels) > 0,
        "geometry_present_primary_run": geo["present"],
        "geometry": geo,
        "geometry_from_supplement_run": geo_supp,
        "geometry_any": bool(geo["present"] or geo_supp),
        "runs_available": [str(x.relative_to(A)) for x in runs],
        "n_runs": len(runs),
        "candidate_count_max": max(
            [b.get("candidate_count", 0) for b in (j.get("attempted_branches") or [])] or [0]),
        "route_diagnosis": j.get("route_diagnosis"),
        "state_count": j.get("state_count"),
        "synthetic": j.get("SYNTHETIC"),
    }


def build() -> dict:
    rows = []
    for v, ids in COHORT.items():
        for t in ids:
            rows.append(row(v, t))
    n = len(rows)
    def cov(key):
        k = sum(1 for r in rows if r.get(key) is True)
        return {"observed": k, "n": n, "state": f"{k}/{n}"}
    coverage = {
        "endpoint_predicate": {"observed": sum(1 for r in rows if r.get("endpoint_predicate")),
                               "n": n, "state": f"{sum(1 for r in rows if r.get('endpoint_predicate'))}/{n}"},
        "sequence": cov("sequence_present"),
        "depth": cov("depth_present"),
        "menu_dependency": cov("menu_present"),
        "ax_independent": cov("ax_independently_captured"),
        "entry_label": cov("label_present"),
        "geometry_in_primary_run": cov("geometry_present_primary_run"),
        "geometry_incl_supplement_run": cov("geometry_any"),
    }
    by_inst = {}
    for r in rows:
        by_inst.setdefault(r["instrument"], []).append(r["target_id"])
    multi = [r["target_id"] for r in rows if r.get("n_runs", 0) > 1]
    return {"n_targets": n, "cohort_by_instrument": by_inst,
            "coverage_same_definition": coverage,
            "targets_with_multiple_runs": multi,
            "run_policy": ("변수는 **판정 근거 run(그 계기의 첫 산출)** 에서 읽는다. "
                           "보충 run 의 값은 `*_from_supplement_run` 으로 **따로** 적고 합치지 않는다 — "
                           "한 target 안에서 변수마다 다른 run 을 읽으면 그것이 계기 혼입이다"),
            "rows": rows}


if __name__ == "__main__":
    m = build()
    print(json.dumps({k: v for k, v in m.items() if k != "rows"}, ensure_ascii=False, indent=1))
