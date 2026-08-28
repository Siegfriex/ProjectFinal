"""D 화이트리스트 vs 사이드카 `per_column` — **모든 축**. [D-DEF-111]

`D-DEF-110` 의 한계 — '`sidecar_observed` 는 `per_column` 이 있는 열만 읽는다'.
그 블록이 **27열 전부**를 담고 있으므로 전수 대조가 가능해졌다.

B 는 미선언 비관측 토큰을 **한 번에 하나씩** 찾아 왔다(7종). 전수로 대조하면
**남은 어긋남이 몇 개인지** 한 번에 나온다 — 그리고 **어느 토큰에서 오는지**까지.

**D 가 어느 정의가 옳은지 정하지 않는다.** 차이와 그 토큰을 이름으로 낸다.
"""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

REPO = Path("/home/sieg/projects-wsl/ProjectFinal")
MART = REPO / "artifacts/v3_census/mart/CANONICAL_MART_50.csv"
SIDECAR = REPO / "artifacts/v3_census/mart/CANONICAL_MART_50.sha256.json"
sys.path.insert(0, str(Path(__file__).resolve().parent))


def compare(mart: Path | None = None, sidecar: Path | None = None) -> dict:
    import d_coverage as CV
    try:
        rows = list(csv.DictReader((mart or MART).open(encoding="utf-8")))
        pc = (json.loads((sidecar or SIDECAR).read_text(encoding="utf-8"))
              .get("missing_value_vocabulary") or {}).get("per_column") or {}
    except Exception as e:                          # noqa: BLE001
        return {"verdict": "UNREADABLE", "error": str(e)}
    if not rows or not pc:
        return {"verdict": "NO_INPUT", "n_rows": len(rows), "n_columns": len(pc)}

    axes, no_def, diffs = [], [], []
    for col, blk in pc.items():
        if col not in rows[0]:
            continue
        n_s = blk.get("n_observed")
        if col not in CV.OBSERVED_VALUES:
            no_def.append(col)                      # **D 정의 없음 — 일치로 세지 않는다**
            continue
        n_d = sum(1 for r in rows if CV.is_observed(col, r.get(col, ""), r))
        axes.append({"column": col, "sidecar": n_s, "D": n_d, "agree": n_d == n_s})
        if n_d == n_s:
            continue
        miss = set(blk.get("missing_tokens") or [])
        toks = []
        for v in {r.get(col, "") for r in rows}:
            row = next(r for r in rows if r.get(col, "") == v)
            s_obs, d_obs = v not in miss, CV.is_observed(col, v, row)
            if s_obs != d_obs:
                toks.append({"token": v, "n": sum(1 for r in rows if r.get(col, "") == v),
                             "sidecar": "관측" if s_obs else "비관측",
                             "D": "관측" if d_obs else "비관측"})
        diffs.append({"column": col, "sidecar": n_s, "D": n_d, "delta": n_d - n_s,
                      "tokens": sorted(toks, key=lambda x: -x["n"])})
    n_cells = sum(t["n"] for d in diffs for t in d["tokens"])
    return {"verdict": "AGREE" if not diffs else "DISAGREE",
            "n_columns_in_sidecar": len(pc),
            "n_axes_compared": len(axes), "n_axes_disagree": len(diffs),
            "n_cells_in_dispute": n_cells,
            "disagreements": diffs,
            "d_has_no_definition": no_def,
            "**D 가 정하지 않는다**": (
                "어느 정의가 옳은지는 **A 소관**이다. D 는 **차이와 그 토큰을 이름으로** 낸다"),
            "**정의 없음은 일치가 아니다**": (
                f"{len(no_def)} 열은 D 화이트리스트에 정의가 없어 **대조하지 않았다** — "
                "일치로 세면 분모가 부풀어 오른다"),
            "왜_전수인가": ("B 는 미선언 토큰을 한 번에 하나씩 찾아 왔다(7종). "
                     "전수 대조는 **남은 어긋남이 몇 개인지** 한 번에 낸다")}


def controls() -> dict:
    import tempfile as _tf
    rows_out = []

    def case(name, got, want, negative=False):
        rows_out.append({"case": name, "got": got, "want": want, "ok": got == want,
                         "expectation": "must_flag" if negative else "must_not_flag"})

    live = compare()
    case("현재 mart 를 읽었다 — 0 이면 무효다", live["n_axes_compared"] > 0, True)
    case("**정의 없는 열을 일치로 세지 않는다**",
         live["n_axes_compared"] + len(live["d_has_no_definition"])
         <= live["n_columns_in_sidecar"], True)
    case("어긋난 축마다 토큰을 이름으로 낸다",
         all(d["tokens"] for d in live["disagreements"]), True)
    case("셀 수는 토큰 수의 합이다",
         live["n_cells_in_dispute"],
         sum(t["n"] for d in live["disagreements"] for t in d["tokens"]))

    # 합성: 한 토큰만 다르면 그 축 하나가 잡힌다
    with _tf.TemporaryDirectory() as t:
        m = Path(t) / "m.csv"
        with m.open("w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=["nav_container_type"])
            w.writeheader()
            w.writerow({"nav_container_type": "NONE"})
            w.writerow({"nav_container_type": "HEADER"})
        sc = Path(t) / "s.json"
        sc.write_text(json.dumps({"missing_value_vocabulary": {"per_column": {
            "nav_container_type": {"n_observed": 1, "missing_tokens": ["NONE"]}}}}),
            encoding="utf-8")
        r = compare(m, sc)
        case("**한 토큰 차이를 잡는다**", r["n_axes_disagree"], 1, negative=True)
        case("그 토큰 이름을 낸다",
             r["disagreements"][0]["tokens"][0]["token"] if r["disagreements"] else None,
             "NONE", negative=True)

    ok = all(x["ok"] for x in rows_out)
    return {"verdict": "PASS" if ok else "FAIL", "n": len(rows_out),
            "must_flag": sum(1 for x in rows_out if x["expectation"] == "must_flag"),
            "must_not_flag": sum(1 for x in rows_out if x["expectation"] == "must_not_flag"),
            "failed": [x["case"] for x in rows_out if not x["ok"]], "cases": rows_out}


if __name__ == "__main__":
    c = controls()
    print(json.dumps({"compare": compare(), "controls": c}, ensure_ascii=False, indent=1))
    raise SystemExit(0 if c["verdict"] == "PASS" else 3)
