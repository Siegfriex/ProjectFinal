"""Presentation EDA 산출의 **내부 정합성** 검사.

C 가 `C-DEF-34` 를 자기 티켓 안의 모순으로 잡았다 — 같은 산출에 `scout_status
ENDPOINT_REACHED 3` 이 찍혀 있는데 다른 필드만 보고 0 을 냈다. D 가 ACK 에
"**한 산출 안의 두 수치를 대조하는 것이 가장 싼 검사다**" 라고 적었으므로
D 자신의 산출에도 적용한다.

잡으려는 것: REPORT.md 의 표 · METRICS.json · CSV 가 **서로 다른 수를 말하는데
셋 다 정상으로 보이는** 상태.
"""
from __future__ import annotations

import csv
import hashlib
import json
import re
from pathlib import Path

import d_presentation_eda as P

OUT = P.OUT


def _sha(p) -> str:
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def check() -> dict:
    m = json.loads((OUT / "PRESENTATION_EDA_METRICS.json").read_text(encoding="utf-8"))
    pr = json.loads((OUT / "PRESENTATION_EDA_PROVENANCE.json").read_text(encoding="utf-8"))
    rep = (OUT / "PRESENTATION_EDA_REPORT.md").read_text(encoding="utf-8")
    word = (OUT / "PRESENTATION_CLAIM_SAFE_WORDING.md").read_text(encoding="utf-8")
    A, B, C = m["A_final_numbers"], m["B_observability"], m["C_verified_case_series"]
    cases = []

    def case(name, ok, detail):
        cases.append({"case": name, "ok": bool(ok), "detail": detail})

    # 1. 3집단 합 = 50, unmapped 0
    tot = sum(g["numerator"] for g in A["groups"].values())
    case("3집단 합 = 50", tot == 50 and not A["unmapped_terminal_values"],
         {"sum": tot, "unmapped": A["unmapped_terminal_values"]})

    # 2. 각 변수의 provenance 분류 합 = 50 — 하나라도 어긋나면 분류가 샜다
    bad = {k: v["sum_check"] for k, v in B.items() if v["sum_check"] != 50}
    case("변수별 분류 합 = 50 (전 변수)", not bad, {"mismatched": bad})

    # 3. REPORT 본문의 숫자가 METRICS 와 같은가 — **서로 다른 수를 말하면 둘 다 정상으로 보인다**
    claims = {
        "USABLE 8": ("USABLE_PATH_EVIDENCE", 8),
        "SITE 16": ("SITE_SIDE_ROUTE_NOT_OBSERVED", 16),
        "MEASUREMENT 26": ("MEASUREMENT_COLLECTOR_LIMITED", 26),
    }
    mism = {k: (A["groups"][g]["numerator"], n)
            for k, (g, n) in claims.items() if A["groups"][g]["numerator"] != n}
    case("REPORT 서술 수치 == METRICS", not mism, {"mismatched": mism})

    # 4. depth 분모 주장 — 본문이 28 을 말하는가 (50 이면 오독 자리 그대로)
    depth_obs = B["activation_depth"]["observed_direct_or_supplement"]
    case("activation_depth 분모 = 28 이고 본문도 28 을 말한다",
         depth_obs == 28 and "분모는 **28**" in rep,
         {"metrics": depth_obs, "report_mentions_28": "분모는 **28**" in rep})

    # 5. AX 는 0 이고 본문이 0/50 을 말하는가
    ax = B["accessible_name"]["observed_direct_or_supplement"]
    case("accessible_name 관측 0 이고 본문도 0/50",
         ax == 0 and "0/50" in rep, {"metrics": ax})

    # 6. n=8 축 수치가 REPORT 표와 같은가
    z = C["entry_zone"]["unique_over_n"]; ct = C["entry_control_type"]["unique_over_n"]
    case("n=8 zone/control 표기 일치", z == "5/8" and ct == "2/8" and z in rep and ct in rep,
         {"zone": z, "control": ct})

    # 7. CSV 행수 = 변수 수, 그리고 CSV 의 observed 가 METRICS 와 같은가
    rows = list(csv.DictReader(
        [l for l in (OUT / "PRESENTATION_OBSERVABILITY_TABLE.csv")
         .read_text(encoding="utf-8").splitlines() if not l.startswith("#")]))
    csv_bad = {r["variable"]: (r["observed_n"], B[r["variable"]]["observed_direct_or_supplement"])
               for r in rows
               if r["variable"] in B
               and int(r["observed_n"]) != B[r["variable"]]["observed_direct_or_supplement"]}
    case("CSV observed == METRICS", len(rows) == len(B) and not csv_bad,
         {"csv_rows": len(rows), "metrics_vars": len(B), "mismatched": csv_bad})

    # 8. provenance 에 기록된 산출 sha 가 실제 파일과 같은가
    sbad = {k: v for k, v in pr["outputs"].items()
            if not (OUT / k).exists() or _sha(OUT / k) != v}
    case("산출 sha 기록 == 실제 파일", not sbad, {"mismatched": list(sbad)})

    # 9. mart sha 가 선언값과 같고 REPORT 에도 그 값이 적혀 있는가
    ms = pr["inputs"]["mart_sha256"]
    case("mart sha 선언 일치 + REPORT 기재",
         ms == P.EXPECTED_MART and ms in rep, {"sha": ms[:20]})

    # 10. 금지 문장이 WORDING 에 실제로 들어 있는가 — 없으면 그 방어가 없는 것이다
    must = ["접근성 성공률", "평균 활성화 깊이", "라벨 일치율", "원리적으로 못 얻는다"]
    miss = [x for x in must if x not in word]
    case("금지 문장 4종이 WORDING 에 존재", not miss, {"missing": miss})

    ok = all(c["ok"] for c in cases)
    return {"verdict": "PASS" if ok else "FAIL", "n": len(cases),
            "failed": [c["case"] for c in cases if not c["ok"]], "cases": cases,
            "what_this_does_not_prove":
                "산출들이 **서로 같은 말을 한다**는 것까지다. 그 말이 옳은지는 말하지 않는다"}


def controls() -> dict:
    """조작본을 넣어 실제로 막는지 본다 (R52). 원본 파일은 건드리지 않는다."""
    import copy, tempfile, shutil
    rows = []
    orig = {p.name: p.read_bytes() for p in OUT.iterdir() if p.is_file()}
    tmp = Path(tempfile.mkdtemp(prefix="d_eda_ctl_"))
    try:
        def run(name, mutate, should_fail=True):
            for n, b in orig.items():
                (OUT / n).write_bytes(b)
            mutate()
            v = check()["verdict"]
            rows.append({"case": name,
                         "expectation": "must_flag" if should_fail else "must_not_flag",
                         "verdict": v, "ok": (v == "FAIL") is should_fail})

        run("원본은 통과", lambda: None, should_fail=False)

        def bump_metrics():
            p = OUT / "PRESENTATION_EDA_METRICS.json"
            d = json.loads(p.read_text(encoding="utf-8"))
            d["A_final_numbers"]["groups"]["USABLE_PATH_EVIDENCE"]["numerator"] = 9
            p.write_text(json.dumps(d, ensure_ascii=False), encoding="utf-8")
        run("METRICS 를 바꾸면 REPORT 와 어긋나 막힘", bump_metrics)

        def break_depth():
            p = OUT / "PRESENTATION_EDA_METRICS.json"
            d = json.loads(p.read_text(encoding="utf-8"))
            d["B_observability"]["activation_depth"]["observed_direct_or_supplement"] = 50
            p.write_text(json.dumps(d, ensure_ascii=False), encoding="utf-8")
        run("depth 분모가 50 이 되면 막힘", break_depth)

        def break_ax():
            p = OUT / "PRESENTATION_EDA_METRICS.json"
            d = json.loads(p.read_text(encoding="utf-8"))
            d["B_observability"]["accessible_name"]["observed_direct_or_supplement"] = 28
            p.write_text(json.dumps(d, ensure_ascii=False), encoding="utf-8")
        run("AX 관측이 0 이 아니게 되면 막힘", break_ax)

        def strip_wording():
            p = OUT / "PRESENTATION_CLAIM_SAFE_WORDING.md"
            p.write_text(p.read_text(encoding="utf-8").replace("접근성 성공률", "___"),
                         encoding="utf-8")
        run("금지 문장이 빠지면 막힘", strip_wording)
    finally:
        for n, b in orig.items():
            (OUT / n).write_bytes(b)
        shutil.rmtree(tmp, ignore_errors=True)
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
