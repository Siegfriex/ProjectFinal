"""D 가 **인용한 타평면 수치**가 그 평면의 최신 산출과 일치하는가.

`D-DEF-42` 가 두 회차 연속으로 났다 — 남이 만든 분류·수치를 판정 근거 검사 없이
그대로 축으로 썼다. 두 번째는 A 의 `V4_TALLY.json` 을 인용했는데 C 재검산이
다른 수를 냈다(TRUSTED 2 vs 3, 누적 21 vs 22, 그리고 21 = 18+3 합산).

**규칙을 적는 것이 준수를 보장하지 않는다.** 그래서 검사로 옮긴다.

방법: D 산출이 인용한 수치를 `CITED` 표에 명시적으로 적고, **버스의 최신 원천에서
같은 값을 다시 읽어 대조**한다. 원천이 여럿이면(A tally vs C assurance) **둘 다
읽고 서로 다르면 그것부터 flag** 한다 — 어느 쪽이 옳은지는 D 가 정하지 않는다.

축은 **자기 정합성**이 아니라 **인용 정합성**이다. D 검사에 없던 축이다
(D-V3-FINDING-037: VALUE 17 · IDENTITY 4 · DELTA 4, 전부 자기 정합성).
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import d_v3_census as C

BUS = Path("/home/sieg/projects-wsl/ProjectFinal/.agent_bus/landing_v2")
PROBE_V4 = C.REPO / "artifacts/v3_probe_v4"


def _latest_c_assurance() -> tuple:
    """가장 최근 C ASSURANCE 티켓. **파일 mtime 이 정본 시각이다**(A TBX-011)."""
    cands = sorted(BUS.glob("tickets/C-ASSURANCE-*.json"),
                   key=lambda p: p.stat().st_mtime, reverse=True)
    for p in cands:
        try:
            d = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            continue
        if "cumulative" in d or "dist31" in d:
            return p.name, d
    return (cands[0].name, json.loads(cands[0].read_text(encoding="utf-8"))) if cands else (None, {})


def _a_tally() -> dict:
    f = PROBE_V4 / "V4_TALLY.json"
    return json.loads(f.read_text(encoding="utf-8")) if f.exists() else {}


def cited() -> dict:
    """D 산출이 **실제로 인용하고 있는** 수치. 여기에 적지 않으면 대조되지 않는다."""
    prov = json.loads((C.ANALYSIS / "D_PROVENANCE.json").read_text(encoding="utf-8"))
    st = (prov.get("visual_deliverables") or {}).get("post_census_probe_state") or {}
    vis = (C.RD if hasattr(C, "RD") else Path(".")) 
    html = Path("presentation_eda/visual/MEASUREMENT_AUDIT.html")
    txt = html.read_text(encoding="utf-8") if html.exists() else ""
    m = re.search(r'<div class="pv">(\d+)<small> / 50', txt[::-1])
    # 마지막 누적 값은 정방향으로 다시 찾는다
    vals = re.findall(r'<div class="pv">(\d+)<small> / 50</small></div>', txt)
    return {"provenance_cumulative": st.get("cumulative"),
            "provenance_v4_trusted": st.get("v4_trusted"),
            "provenance_dist31": st.get("dist31"),
            "visual_progression_values": vals,
            "visual_last_cumulative": (int(vals[-1]) if vals else None)}


def check() -> dict:
    cases = []

    def case(name, ok, detail):
        cases.append({"case": name, "ok": bool(ok), "detail": detail})

    cname, cdoc = _latest_c_assurance()
    a = _a_tally()
    cit = cited()

    c_cum = ((cdoc.get("cumulative") or {}).get("n"))
    c_tr = (cdoc.get("cumulative") or {}).get("v4")
    c_dist = cdoc.get("dist31")
    a_cum = a.get("cumulative_n")
    a_tr = a.get("v4_trusted")

    # 0. 두 원천이 서로 다르면 그것부터 드러낸다 — 어느 쪽이 옳은지는 D 가 정하지 않는다
    src_agree = (c_cum == a_cum) and (sorted(c_tr or []) == sorted(a_tr or []))
    case("원천 두 곳(A tally · C assurance)이 같은 수를 말한다", src_agree,
         {"A": {"cumulative": a_cum, "trusted": a_tr},
          "C": {"cumulative": c_cum, "trusted": c_tr},
          "source_of_truth": ("불일치 시 D 는 판정하지 않는다 — **검산본(C)을 인용하고 "
                              "불일치 사실을 함께 적는다**")})

    # 1. D 가 인용한 누적이 C 검산본과 같은가
    case("D 인용 누적 == C 검산본",
         cit["provenance_cumulative"] and str(c_cum) in str(cit["provenance_cumulative"]),
         {"D": cit["provenance_cumulative"], "C": c_cum})

    # 2. 시각물의 마지막 누적 값이 C 와 같은가
    case("시각물 마지막 누적 == C 검산본", cit["visual_last_cumulative"] == c_cum,
         {"visual": cit["visual_last_cumulative"], "C": c_cum})

    # 3. D 가 인용한 TRUSTED 집합이 C 와 같은가
    case("D 인용 TRUSTED == C 검산본",
         sorted(cit["provenance_v4_trusted"] or []) == sorted(c_tr or []),
         {"D": cit["provenance_v4_trusted"], "C": c_tr})

    # 4. D 가 인용한 분포가 C dist31 과 같은가
    case("D 인용 dist31 == C 검산본", cit["provenance_dist31"] == c_dist,
         {"D": cit["provenance_dist31"], "C": c_dist})

    # 5. 분포 합이 시도 수와 같은가 — **합산 중복을 잡는 자리**
    tot = sum((c_dist or {}).values())
    case("dist31 합 == 31 (합산 중복 없음)", tot == 31,
         {"sum": tot, "note": "D 는 앞서 18+3 을 합친 21 을 인용하고 3 을 또 셌다"})

    ok = all(c["ok"] for c in cases)
    return {"verdict": "PASS" if ok else "FAIL", "n": len(cases),
            "failed": [c["case"] for c in cases if not c["ok"]], "cases": cases,
            "source_ticket": cname,
            "axis": "**인용 정합성** — D 검사에 없던 축이다(기존은 전부 자기 정합성)",
            "what_this_does_not_prove":
                "D 가 인용한 값이 원천과 같다는 것까지다. **원천이 옳은지는 말하지 않는다**"}


def controls() -> dict:
    """조작본으로 막는지 본다. 원본은 건드리지 않는다."""
    import copy
    rows = []
    real = cited
    def run(name, fake, should_fail=True):
        globals()["cited"] = fake
        v = check()["verdict"]
        globals()["cited"] = real
        rows.append({"case": name,
                     "expectation": "must_flag" if should_fail else "must_not_flag",
                     "verdict": v, "ok": (v == "FAIL") is should_fail})

    run("현 상태는 통과", real, should_fail=False)

    base = real()
    def f1():
        d = copy.deepcopy(base); d["visual_last_cumulative"] = 21; return d
    run("시각물 누적이 검산본과 다르면 막힘", f1)

    def f2():
        d = copy.deepcopy(base); d["provenance_v4_trusted"] = ["F4-01", "F4-10"]; return d
    run("TRUSTED 집합이 다르면 막힘", f2)

    def f3():
        d = copy.deepcopy(base)
        d["provenance_dist31"] = {"NO_CANDIDATE": 21, "ENDPOINT_REACHED": 6,
                                  "EVIDENCE_DEFECT": 2, "SAFETY_STOP": 1, "TIMEOUT": 1}
        return d
    run("합산된 분포(18+3=21)를 인용하면 막힘", f3)

    ok = all(r["ok"] for r in rows)
    return {"verdict": "PASS" if ok else "FAIL", "n": len(rows),
            "must_flag": sum(1 for r in rows if r["expectation"] == "must_flag"),
            "must_not_flag": sum(1 for r in rows if r["expectation"] == "must_not_flag"),
            "cases": rows}


if __name__ == "__main__":
    ctl = controls()
    if ctl["verdict"] != "PASS":
        print(json.dumps(ctl, ensure_ascii=False, indent=1)); raise SystemExit(3)
    r = check(); r["controls"] = ctl
    print(json.dumps(r, ensure_ascii=False, indent=1))
    raise SystemExit(0 if r["verdict"] == "PASS" else 2)
