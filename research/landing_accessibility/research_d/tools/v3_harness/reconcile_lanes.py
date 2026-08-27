"""5 lane 하네스 산출 reconciliation — Director ADDENDUM §3.

worker completion 을 그대로 canonical 로 채택하지 않는다. 오케스트레이터가
source SHA · artifact version · overlap · 중복실행 · 모순 · 누락 · 완결성을
대조한 뒤에만 통합한다. 두 worker 가 같은 사실에 다른 결과를 내면 조용히
하나를 고르지 않고 RECONCILIATION_REQUIRED 로 명시한다.

**빈 결과 함정 방어**: lane 산출이 없을 때 "모순 0 / 정상" 으로 보이면 안 된다.
없는 것은 MISSING 으로 명시하고 verdict 를 NOT_READY 로 만든다.
(이 프로젝트에서 빈 출력이 통과로 읽힌 사례가 여러 번 있었다 — D-DEF-09/10.)

usage: reconcile_lanes.py [--json]
exit 0 = READY, 1 = NOT_READY 또는 RECONCILIATION_REQUIRED
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

RD = Path(__file__).resolve().parents[2]
WT = RD.parents[2]
LANES = {
    "S": ("lane_s", "spatial / control-form / menu·reveal"),
    "L": ("lane_l", "label / accessible name"),
    "F": ("lane_f", "flow topology / depth"),
    "A": ("lane_a", "auth timing / obstruction"),
    "P": ("lane_p", "provenance / denominator / metric redundancy"),
}
EXPECTED_TOP_KEYS = ("verdict", "ambiguous_definitions", "limitation")
VALID_VERDICTS = {"READY", "READY_WITH_AMBIGUITY", "NOT_READY"}


def git(*a: str) -> str:
    return subprocess.run(["git", *a], cwd=WT, capture_output=True, text=True).stdout.strip()


def load_lane(key: str) -> dict:
    ns, resp = LANES[key]
    d = RD / "results" / "harness" / ns
    js = sorted(d.glob("LANE_*_HARNESS.json"))
    md = sorted(d.glob("LANE_*_FINDINGS.md"))
    code = sorted((RD / "tools" / "v3_harness").glob(f"{ns}_*.py"))
    out = {"lane": key, "namespace": ns, "responsibility": resp,
           "json": js[0].name if js else None, "md": md[0].name if md else None,
           "code": [c.name for c in code], "status": None, "payload": None, "problems": []}
    if not js:
        out["status"] = "MISSING"
        out["problems"].append("HARNESS.json 없음")
        return out
    if len(js) > 1:
        out["problems"].append(f"HARNESS.json 이 {len(js)}개 — 어느 것이 canonical 인지 불명")
    try:
        out["payload"] = json.loads(js[0].read_text(encoding="utf-8"))
    except Exception as e:
        out["status"] = "PARSE_ERROR"
        out["problems"].append(f"{type(e).__name__}: {e}")
        return out
    p = out["payload"]
    for k in EXPECTED_TOP_KEYS:
        if k not in p:
            out["problems"].append(f"필수 키 누락: {k}")
    v = p.get("verdict")
    if v not in VALID_VERDICTS:
        out["problems"].append(f"verdict 어휘 밖: {v!r}")
    if not md:
        out["problems"].append("FINDINGS.md 없음")
    if not code:
        out["problems"].append("재현 진입점(.py) 없음")
    out["status"] = "COMPLETE" if not out["problems"] else "INCOMPLETE"
    return out


NAME_KEYS = ("name", "variable", "id", "component", "key")


def _names(container) -> list[str]:
    """[D-DEF-11] lane 마다 산출 모양이 다르다 — list[str] / list[dict] / dict(키=이름).
    이름 추출이 실패하면 겹침이 있어도 0 건으로 보인다. 실제로 menu_dependency 가
    S 와 F 양쪽에 구현됐는데 첫 판본이 놓쳤다. 세 모양을 모두 처리한다.
    모양을 못 알아보면 조용히 버리지 않고 UNPARSED: 접두로 남겨 눈에 띄게 한다."""
    out = []
    if isinstance(container, dict):
        return [str(k) for k in container]
    if not isinstance(container, list):
        return []
    for v in container:
        if isinstance(v, str):
            out.append(v)
        elif isinstance(v, dict):
            for k in NAME_KEYS:
                if isinstance(v.get(k), str):
                    out.append(v[k]); break
            else:
                out.append("UNPARSED:" + json.dumps(v, ensure_ascii=False)[:40])
        else:
            out.append("UNPARSED:" + str(v)[:40])
    return out


def cross_checks(lanes: list[dict]) -> list[dict]:
    """§3 — overlap · 중복 · 모순 · 누락."""
    issues = []
    # 1) namespace 침범: 다른 lane 의 파일을 만든 워커가 있는가
    owners = {}
    for f in (RD / "tools" / "v3_harness").glob("lane_*_*.py"):
        ns = "_".join(f.name.split("_")[:2])
        owners.setdefault(ns, []).append(f.name)
    known = {v[0] for v in LANES.values()}
    for ns in owners:
        if ns not in known:
            issues.append({"kind": "UNKNOWN_NAMESPACE", "detail": ns, "files": owners[ns]})
    # 2) 같은 변수를 둘 이상의 lane 이 구현했는가 (중복 측정 = 모순 위험)
    impl = {}
    for L in lanes:
        pay = L.get("payload") or {}
        src = pay.get("implemented_variables")
        if src is None:
            src = pay.get("implemented_components")
        for name in _names(src):
            impl.setdefault(name, []).append(L["lane"])
    for name, ls in impl.items():
        if len(set(ls)) > 1:
            issues.append({"kind": "DUPLICATE_IMPLEMENTATION", "variable": name, "lanes": sorted(set(ls))})
    # 3) 같은 정의를 두고 서로 다른 판단 (모호 vs 구현)
    amb = {}
    for L in lanes:
        for name in _names((L.get("payload") or {}).get("ambiguous_definitions")):
            amb.setdefault(name, []).append(L["lane"])
    for name, ls in amb.items():
        if name in impl and set(impl[name]) - set(ls):
            issues.append({"kind": "CONTRADICTION_AMBIGUOUS_VS_IMPLEMENTED", "variable": name,
                           "declared_ambiguous_by": sorted(set(ls)),
                           "implemented_by": sorted(set(impl[name]) - set(ls))})
    unparsed = sorted({n for n in impl if n.startswith("UNPARSED:")} |
                      {n for n in amb if n.startswith("UNPARSED:")})
    if unparsed:
        issues.append({"kind": "UNPARSED_ENTRY", "count": len(unparsed), "samples": unparsed[:5]})
    return issues


def main() -> int:
    lanes = [load_lane(k) for k in LANES]
    issues = cross_checks(lanes)
    missing = [L["lane"] for L in lanes if L["status"] == "MISSING"]
    incomplete = [L["lane"] for L in lanes if L["status"] in ("INCOMPLETE", "PARSE_ERROR")]

    if missing or incomplete:
        verdict = "NOT_READY"
    elif issues:
        verdict = "RECONCILIATION_REQUIRED"
    else:
        verdict = "READY"

    report = {
        "reconciliation_id": "D_V3_LANE_RECONCILIATION",
        "verdict": verdict,
        "orchestrator_head": git("rev-parse", "HEAD"),
        "orchestrator_dirty": bool(git("status", "--porcelain")),
        "lanes": [{k: v for k, v in L.items() if k != "payload"} for L in lanes],
        "lane_verdicts": {L["lane"]: (L.get("payload") or {}).get("verdict") for L in lanes},
        "missing_lanes": missing,
        "incomplete_lanes": incomplete,
        "cross_lane_issues": issues,
        "note": ("빈 결과를 정상으로 읽지 않는다. lane 산출이 없으면 MISSING 이고 verdict 는 NOT_READY 다. "
                 "cross_lane_issues 가 비었다는 것은 lane 이 전부 COMPLETE 일 때만 의미가 있다."),
    }
    if "--json" in sys.argv:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(f"verdict: {verdict}")
        for L in lanes:
            print(f"  {L['lane']} {L['status'] or '-':<12} verdict={(L.get('payload') or {}).get('verdict')} "
                  f"problems={len(L['problems'])} {';'.join(L['problems'][:2])}")
        print(f"  cross-lane issues: {len(issues)}")
        for i in issues[:10]:
            print(f"    - {i['kind']}: {json.dumps({k:v for k,v in i.items() if k!='kind'}, ensure_ascii=False)[:140]}")
    return 0 if verdict == "READY" else 1


if __name__ == "__main__":
    raise SystemExit(main())
