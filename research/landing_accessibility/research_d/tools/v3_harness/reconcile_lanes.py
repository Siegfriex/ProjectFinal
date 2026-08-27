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


def run_controls() -> dict:
    """이 대조기가 아직 겹침을 잡는가 — 매 실행 확인한다.

    `cross_checks` 는 D-DEF-11 을 냈다: 이름 추출이 실패해 **겹침이 있는데도
    0 건**을 냈고, 그 0 이 'READY / 교차 문제 없음' 으로 보고됐다. 시정은
    들어갔지만 **대조군은 없었다** — 다시 같은 방식으로 죽으면 출력이 지금과
    같다.

    B 가 T-B-V3-RECON-004 에서 더 강한 기준을 걸었다: 목록을 내기 전에
    **양성·음성 대조가 통과해야 하고, 통과 못 하면 목록을 내지 말고 방법을
    고친다.** 그 기준을 여기에 적용한다 — 대조군이 실패하면
    `RECONCILIATION.json` 을 쓰지 않는다.

    D-DEF-11 의 실제 형태(세 가지 산출 모양)를 그대로 fixture 로 쓴다.
    """
    def lane(key, impl, amb=None):
        return {"lane": key, "payload": {"implemented_variables": impl,
                                         "ambiguous_definitions": amb or []}}
    cases = []

    # 양성 1 — list[str] 끼리 겹침
    got = cross_checks([lane("S", ["menu_dependency"]), lane("F", ["menu_dependency"])])
    cases.append(("겹침(list[str])을 잡는가",
                  any(i["kind"] == "DUPLICATE_IMPLEMENTATION" for i in got), True))
    # 양성 2 — **모양이 서로 다른** 겹침. D-DEF-11 이 정확히 이것이었다.
    got = cross_checks([lane("S", ["nav_container_depth"]),
                        lane("F", [{"variable": "nav_container_depth"}])])
    cases.append(("모양이 다른 겹침을 잡는가 (D-DEF-11 형태)",
                  any(i["kind"] == "DUPLICATE_IMPLEMENTATION" for i in got), True))
    # 양성 3 — dict 키 형태
    got = cross_checks([lane("S", {"reveal_required": {}}), lane("L", ["reveal_required"])])
    cases.append(("dict 키 형태 겹침을 잡는가",
                  any(i["kind"] == "DUPLICATE_IMPLEMENTATION" for i in got), True))
    # 양성 4 — 모순(한쪽은 모호, 다른 쪽은 구현)
    got = cross_checks([lane("S", ["x_var"]), lane("F", [], ["x_var"])])
    cases.append(("모호 대 구현 모순을 잡는가",
                  any(i["kind"] == "CONTRADICTION_AMBIGUOUS_VS_IMPLEMENTED" for i in got), True))
    # 양성 5 — 못 알아보는 모양을 조용히 버리지 않는가
    got = cross_checks([lane("S", [12345]), lane("F", [])])
    cases.append(("미해석 항목을 드러내는가",
                  any(i["kind"] == "UNPARSED_ENTRY" for i in got), True))
    # 음성 — 겹치지 않으면 만들어내지 않는가
    got = cross_checks([lane("S", ["a_var"]), lane("F", ["b_var"])])
    cases.append(("겹치지 않으면 만들어내지 않는가",
                  any(i["kind"] in ("DUPLICATE_IMPLEMENTATION",
                                    "CONTRADICTION_AMBIGUOUS_VS_IMPLEMENTED") for i in got), False))

    rows, ok = [], True
    for name, got_v, want in cases:
        good = got_v is want
        ok &= good
        rows.append({"case": name, "got": got_v, "expected": want, "ok": good})
    return {"verdict": "PASS" if ok else "FAIL", "cases": rows,
            "why": "대조군이 실패하면 목록을 내지 않는다 — 못 잡는 대조기의 "
                   "'교차 문제 0 건' 은 0 이 아니다 (D-DEF-11)"}


def main() -> int:
    ctl = run_controls()
    if ctl["verdict"] != "PASS":
        print("!! 대조군 실패 — RECONCILIATION 을 쓰지 않는다")
        for c in ctl["cases"]:
            if not c["ok"]:
                print(f"   {c['case']}: got={c['got']} expected={c['expected']}")
        return 3
    print(f"controls={ctl['verdict']} ({len(ctl['cases'])}/{len(ctl['cases'])})")

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
        # **산출물이 자기 대조 결과를 싣는다.** 대조는 돌았는데 결과가 산출에
        # 없으면, 읽는 쪽은 그 수치가 통제된 방법에서 나왔는지 알 수 없다.
        # B 가 T-B-V3-RECON-004 에서 목록 산출의 완료 조건으로 건 것이다.
        "controls": ctl,
        "note": ("빈 결과를 정상으로 읽지 않는다. lane 산출이 없으면 MISSING 이고 verdict 는 NOT_READY 다. "
                 "cross_lane_issues 가 비었다는 것은 lane 이 전부 COMPLETE 일 때만 의미가 있다."),
    }
    # [시정] 이 도구는 지금까지 **출력만 하고 파일을 쓰지 않았다.** 그런데
    # docstring 은 "대조군이 실패하면 RECONCILIATION.json 을 쓰지 않는다" 고
    # 적었고, 디스크의 그 파일은 다른 경로로 만들어진 것이었다.
    # 즉 **산출물과 도구가 조용히 갈라질 수 있었다.** 도구가 쓴다.
    out_p = RD / "results" / "harness" / "RECONCILIATION.json"
    out_p.parent.mkdir(parents=True, exist_ok=True)
    out_p.write_text(json.dumps(report, ensure_ascii=False, indent=1) + "\n",
                     encoding="utf-8")
    print(f"wrote {out_p.relative_to(RD)}")

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
