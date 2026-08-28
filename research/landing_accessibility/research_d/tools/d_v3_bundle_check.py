"""D 산출 정합성 검사 — 그림·표·provenance·claim 이 **같은 판본**을 가리키는가.

A 가 closeout 에서 `publication bundle 미구성 — 산출물이 세 디렉터리에 흩어져 있다`
를 미충족으로 꼽았다. 번들을 만드는 것은 A 영역이지만, **D 산출끼리 어긋나지 않았는지**
는 D 가 기계적으로 확인할 수 있다.

이 검사가 잡으려는 것은 이 세션에서 반복된 형태다:
  · 그림과 표가 다른 mart 를 읽었는데 둘 다 정상으로 보인다 (D-DEF-34)
  · 폐기된 산출이 최종본과 같은 자리에 있다 (D-DEF-40)
  · 산출에 적힌 sha 가 실제 파일과 다르다
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import d_v3_census as C

FIG = C.ANALYSIS / "figures"
TAB = C.ANALYSIS / "tables"
SUPERSEDED = FIG / "_superseded_do_not_cite"
FINAL_FIGS = ("report_fig1_acquisition_state.png", "report_fig2_spatial_cases.png",
              "report_fig3_flow_cases.png", "report_fig4_measurement_boundary.png")


def _sha(p) -> str:
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def check(prov=None, claims=None) -> dict:
    """인자를 주면 그것으로 검사한다 — 대조군이 조작본을 넣을 수 있어야 한다."""
    if prov is None:
        prov = json.loads((C.ANALYSIS / "D_PROVENANCE.json").read_text(encoding="utf-8"))
    if claims is None:
        claims = json.loads((C.ANALYSIS / "CLAIM_CANDIDATES.json").read_text(encoding="utf-8"))
    cases, mart = [], C.MART_DIR / "CANONICAL_MART_50.csv"

    def case(name, ok, detail, must_flag=False):
        cases.append({"case": name, "ok": bool(ok), "detail": detail,
                      "expectation": "must_flag" if must_flag else "must_not_flag"})

    # 1. provenance 의 mart sha 가 실제 mart 와 같은가
    live = _sha(mart)
    rec = prov.get("mart_pin", {}).get("sha256")
    case("provenance mart_sha == 실제 mart", rec == live,
         {"recorded": rec, "live": live})

    # 2. claim 이 같은 pin 을 가리키는가 — 그림·표와 다른 판본이면 조용히 어긋난다
    cp = (claims.get("mart_pin") or {}).get("sha256")
    case("claim mart_pin == provenance mart_pin", cp == rec, {"claim": cp, "prov": rec})

    # 3. 기록된 그림 sha 가 실제 파일과 같은가
    bad = {k: v["sha256"] for k, v in prov.get("figures", {}).items()
           if not Path(v["path"]).exists() or _sha(v["path"]) != v["sha256"]}
    case("figure sha 기록 == 실제 파일", not bad, {"mismatched": bad})

    # 4. 표도 마찬가지
    tbad = {k: v for k, v in prov.get("tables", {}).items()
            if not Path(v["csv"]).exists() or _sha(v["csv"]) != v["csv_sha256"]}
    case("table sha 기록 == 실제 파일", not tbad, {"mismatched": list(tbad)})

    # 5. 최종 figures 디렉터리에 **최종 4장만** 있는가 (폐기분 격리 확인)
    top = sorted(p.name for p in FIG.iterdir() if p.is_file())
    case("figures/ 최상위에 최종 4장만", set(top) == set(FINAL_FIGS),
         {"found": top, "expected": list(FINAL_FIGS)})

    # 6. 격리 디렉터리에 README 가 있는가 — 왜 폐기됐는지 없으면 다시 인용된다
    case("격리 디렉터리에 README 존재",
         (SUPERSEDED / "README.txt").exists() if SUPERSEDED.exists() else False,
         {"path": str(SUPERSEDED)})

    # 7. 폐기분과 최종분의 파일명이 겹치지 않는가
    if SUPERSEDED.exists():
        overlap = set(p.name for p in SUPERSEDED.iterdir()) & set(FINAL_FIGS)
    else:
        overlap = set()
    case("폐기분 파일명이 최종분과 겹치지 않음", not overlap, {"overlap": sorted(overlap)})

    # 8. 도구 sha 가 기록과 같은가 — 코드가 바뀌었는데 산출이 그대로면 재현이 깨진다
    cbad = {k: v for k, v in prov.get("d_code_sha256", {}).items()
            if not Path(k).exists() or _sha(k) != v}
    case("D code sha 기록 == 실제 파일", not cbad, {"mismatched": list(cbad)})

    # 10. mlflow run id 가 기록돼 있는가 (provenance 4종 중 lineage)
    rid = prov.get("mlflow_run_id")
    case("mlflow_run_id 기록됨", bool(rid) and rid != "PENDING", {"run_id": rid})

    ok = all(c["ok"] for c in cases)
    return {"verdict": "PASS" if ok else "FAIL",
            "n": len(cases), "failed": [c["case"] for c in cases if not c["ok"]],
            "cases": cases,
            "what_this_does_not_prove": (
                "산출이 서로 같은 판본을 가리킨다는 것까지다. **그 판본이 옳은지는 말하지 않는다** — "
                "전부 같은 잘못된 mart 를 가리켜도 이 검사는 통과한다")}


def controls() -> dict:
    """**검사가 실제로 어긋남을 막는가.** 조작본을 넣어 FAIL 이 나는지 본다.

    [R52] 전건 PASS 인데 must_flag 가 0 이면 그것은 통과가 아니라 공허통과다.
    이 파일 첫 판본이 정확히 그 상태였고(10/10 PASS · must_flag 0),
    합성 케이스라고 넣었던 것은 `sha != "0"*64` 라는 **자명한 참**이었다.
    """
    import copy
    base_p = json.loads((C.ANALYSIS / "D_PROVENANCE.json").read_text(encoding="utf-8"))
    base_c = json.loads((C.ANALYSIS / "CLAIM_CANDIDATES.json").read_text(encoding="utf-8"))
    rows = []

    def run(name, mutate_p=None, mutate_c=None, should_fail=True):
        p2, c2 = copy.deepcopy(base_p), copy.deepcopy(base_c)
        if mutate_p:
            mutate_p(p2)
        if mutate_c:
            mutate_c(c2)
        v = check(p2, c2)["verdict"]
        rows.append({"case": name, "expectation": "must_flag" if should_fail else "must_not_flag",
                     "verdict": v, "ok": (v == "FAIL") is should_fail})

    run("원본은 통과", should_fail=False)
    run("mart sha 가 어긋나면 막힘",
        lambda p: p["mart_pin"].__setitem__("sha256", "0" * 64))
    run("claim 이 다른 판본을 가리키면 막힘",
        None, lambda c: c.__setitem__("mart_pin", {"sha256": "1" * 64}))
    run("figure sha 기록이 실제와 다르면 막힘",
        lambda p: list(p["figures"].values())[0].__setitem__("sha256", "2" * 64))
    run("table sha 기록이 실제와 다르면 막힘",
        lambda p: list(p["tables"].values())[0].__setitem__("csv_sha256", "3" * 64))
    run("code sha 기록이 실제와 다르면 막힘",
        lambda p: p["d_code_sha256"].__setitem__("tools/d_v3_census.py", "4" * 64))
    run("mlflow_run_id 가 PENDING 이면 막힘",
        lambda p: p.__setitem__("mlflow_run_id", "PENDING"))

    ok = all(r["ok"] for r in rows)
    return {"verdict": "PASS" if ok else "FAIL", "n": len(rows),
            "must_flag": sum(1 for r in rows if r["expectation"] == "must_flag"),
            "must_not_flag": sum(1 for r in rows if r["expectation"] == "must_not_flag"),
            "cases": rows}


if __name__ == "__main__":
    ctl = controls()
    if ctl["verdict"] != "PASS":
        print(json.dumps(ctl, ensure_ascii=False, indent=1))
        raise SystemExit(3)          # 대조군 실패는 검사 실패와 **다른** 종료코드
    r = check()
    r["controls"] = ctl
    print(json.dumps(r, ensure_ascii=False, indent=1))
    raise SystemExit(0 if r["verdict"] == "PASS" else 2)
