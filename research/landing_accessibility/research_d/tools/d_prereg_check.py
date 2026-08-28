"""사전등록의 **불변 조건**을 검사로 옮긴다.

`results/D_PROBE_V4_PREREGISTRATION.json` 은 문서다. 문서는 읽히지 않으면
지켜지지 않는다. B 가 R114 에서 말하고 A 가 승인한 것 —
**"그때는 내 눈이 잡았고 지금은 검사가 잡았다. 검사로 옮긴 것이 실제로 만들어진 값이다."**

여기서 잡으려는 것:
  · probe 가 동결 census 를 건드렸는가 (격리 위반)
  · D 발표물의 수치가 mart 와 어긋났는가
  · 사전등록이 불변이라 한 것이 실제로 불변인가

**이 검사는 자기 정합성 축이다**(D-V3-FINDING-037). 행위 유효성은 못 본다 —
그것까지 본다고 적지 않는다.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import d_v3_census as C

RD = Path(__file__).resolve().parent.parent
PRE = RD / "results" / "D_PROBE_V4_PREREGISTRATION.json"
CENSUS = C.CENSUS
PROBE_V4 = C.REPO / "artifacts/v3_probe_v4"

# 사전등록이 불변이라 선언한 값 — 여기에 박아둔다. 바뀌면 검사가 운다.
FROZEN_MART_SHA = "5290e0c306ff7a11375f8da1ee0439e4a424559f18e7a6a662588e46be8f5caf"
# [발행 전 포착] 처음엔 키를 `USABLE_PATH_EVIDENCE`(언더스코어)로 적었는데 실제 산출은
# `USABLE PATH EVIDENCE`(공백)다. 값 8/16/26 은 같은데 **이름 때문에 FAIL 이 났다.**
# 선언한 상수의 키가 실제 산출의 키와 다르면, 검사는 값이 맞아도 운다 — 그리고
# 그 울음이 '수치가 바뀌었다' 로 읽힌다. 키를 실제 산출에 맞추고 **순서로도 대조**한다.
FROZEN_GROUPS = {"USABLE PATH EVIDENCE": 8,
                 "SITE-SIDE ROUTE NOT OBSERVED": 16,
                 "MEASUREMENT / COLLECTOR LIMITED": 26}
FROZEN_DENOM = 50


def _sha(p) -> str:
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def check() -> dict:
    cases = []

    def case(name, ok, detail):
        cases.append({"case": name, "ok": bool(ok), "detail": detail})

    # 1. 동결 mart 가 그대로인가 — 바뀌면 격리 위반이다
    mart = C.MART_DIR / "CANONICAL_MART_50.csv"
    live = _sha(mart) if mart.exists() else None
    case("동결 mart sha 불변", live == FROZEN_MART_SHA,
         {"frozen": FROZEN_MART_SHA[:20], "live": (live or "MISSING")[:20]})

    # 2. census 3집단 수치가 그대로인가
    try:
        df, pin = C.read_mart_pinned(mart)
        import d_v3_report as R
        g = R.group_counts(df)
        now = {k: sum(v.values()) for k, v in g.items()
               if isinstance(v, dict) and not k.startswith("_")}
        # 키 이름과 값을 **따로** 본다 — 이름이 달라 난 FAIL 을 수치 변경으로 읽지 않는다
        same_keys = set(now) == set(FROZEN_GROUPS)
        same_vals = sorted(now.values()) == sorted(FROZEN_GROUPS.values())
        case("census 3집단 수치 불변", same_keys and now == FROZEN_GROUPS,
             {"frozen": FROZEN_GROUPS, "now": now,
              "keys_match": same_keys, "values_match": same_vals,
              "note": ("값은 같고 키만 다르면 그것은 수치 변경이 아니라 **선언 오류**다"
                       if same_vals and not same_keys else "")})
        case("3집단 합 = 분모 50 · unmapped 0",
             sum(now.values()) == FROZEN_DENOM and not g["_unmapped"],
             {"sum": sum(now.values()), "unmapped": g["_unmapped"]})
    except Exception as e:
        case("census 3집단 수치 불변", False, {"error": f"{type(e).__name__}: {e}"})
        case("3집단 합 = 분모 50 · unmapped 0", False, {"error": "위 실패로 미실행"})

    # 3. probe 산출이 census 디렉터리 밖에 있는가 — 격리
    stray = []
    if PROBE_V4.exists():
        for p in PROBE_V4.rglob("*"):
            if not p.is_file():
                continue
            try:
                p.resolve().relative_to(CENSUS.resolve())
                stray.append(str(p))
            except ValueError:
                pass
    case("probe v4 산출이 census 밖에 있다", not stray, {"stray": stray[:5]})

    # 4. census 디렉터리에 probe run_id 흔적이 없는가
    leak = []
    if CENSUS.exists():
        for p in CENSUS.rglob("*"):
            if p.is_file() and "PROBE" in p.name.upper():
                leak.append(str(p.relative_to(CENSUS)))
    case("census 안에 probe 산출 없음", not leak, {"leaked": leak[:5]})

    # 5. D 발표물 provenance 가 동결 mart 를 가리키는가
    prov = C.ANALYSIS / "D_PROVENANCE.json"
    if prov.exists():
        d = json.loads(prov.read_text(encoding="utf-8"))
        rec = (d.get("mart_pin") or {}).get("sha256")
        case("D 발표물 provenance 가 동결 mart 를 가리킨다", rec == FROZEN_MART_SHA,
             {"recorded": (rec or "NONE")[:20]})
    else:
        case("D 발표물 provenance 가 동결 mart 를 가리킨다", False,
             {"error": "D_PROVENANCE.json 없음"})

    # 6. 사전등록 문서 자체가 존재하고 대상집합 대조가 통과 상태인가
    if PRE.exists():
        pr = json.loads(PRE.read_text(encoding="utf-8"))
        ok = (pr.get("결과가_나오기_전_확인") or {}).get("정합") is True
        case("사전등록 존재 + 대상집합 대조 정합", ok,
             {"prereg": str(PRE.name), "정합": ok})
    else:
        case("사전등록 존재 + 대상집합 대조 정합", False, {"error": "사전등록 없음"})

    ok = all(c["ok"] for c in cases)
    return {"verdict": "PASS" if ok else "FAIL", "n": len(cases),
            "failed": [c["case"] for c in cases if not c["ok"]], "cases": cases,
            "axis": "**자기 정합성** 검사다 (D-V3-FINDING-037 분류). 행위 유효성은 보지 않는다",
            "what_this_does_not_prove":
                "동결본이 그대로라는 것까지다. **그 동결본이 옳은지는 말하지 않는다**"}


def controls() -> dict:
    """조작본으로 실제로 막는지 본다. **원본 파일은 건드리지 않는다.**"""
    import copy
    rows = []
    global FROZEN_MART_SHA, FROZEN_GROUPS
    orig_sha, orig_groups = FROZEN_MART_SHA, dict(FROZEN_GROUPS)

    def run(name, mutate, restore, should_fail=True):
        mutate()
        v = check()["verdict"]
        restore()
        rows.append({"case": name,
                     "expectation": "must_flag" if should_fail else "must_not_flag",
                     "verdict": v, "ok": (v == "FAIL") is should_fail})

    run("현 상태는 통과", lambda: None, lambda: None, should_fail=False)

    def m1():
        globals()["FROZEN_MART_SHA"] = "0" * 64
    def r1():
        globals()["FROZEN_MART_SHA"] = orig_sha
    run("mart sha 가 어긋나면 막힘", m1, r1)

    def m2():
        globals()["FROZEN_GROUPS"] = {"USABLE PATH EVIDENCE": 9,
                                      "SITE-SIDE ROUTE NOT OBSERVED": 16,
                                      "MEASUREMENT / COLLECTOR LIMITED": 26}
    def r2():
        globals()["FROZEN_GROUPS"] = orig_groups
    run("3집단 **값**이 어긋나면 막힘", m2, r2)

    def m3():
        globals()["FROZEN_GROUPS"] = {"USABLE_PATH_EVIDENCE": 8,
                                      "SITE_SIDE_ROUTE_NOT_OBSERVED": 16,
                                      "MEASUREMENT_COLLECTOR_LIMITED": 26}
    run("3집단 **키 이름**이 어긋나도 막힘 (값은 같아도)", m3, r2)

    ok = all(r["ok"] for r in rows)
    return {"verdict": "PASS" if ok else "FAIL", "n": len(rows),
            "must_flag": sum(1 for r in rows if r["expectation"] == "must_flag"),
            "must_not_flag": sum(1 for r in rows if r["expectation"] == "must_not_flag"),
            "cases": rows}


if __name__ == "__main__":
    ctl = controls()
    if ctl["verdict"] != "PASS":
        print(json.dumps(ctl, ensure_ascii=False, indent=1))
        raise SystemExit(3)
    r = check(); r["controls"] = ctl
    print(json.dumps(r, ensure_ascii=False, indent=1))
    raise SystemExit(0 if r["verdict"] == "PASS" else 2)
