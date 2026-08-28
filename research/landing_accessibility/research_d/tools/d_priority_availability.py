"""SSOTV3 `14_PROMPT_D_v3.0.md` 의 **우선연구 8개**가 현재 데이터로 착수 가능한가.

**이것은 연구가 아니다.** 새 수치도 새 조작화도 만들지 않는다 — 이미 계산된
census coverage 를 8개 축에 **매핑만** 한다. A 의 v3 역할 티켓이 오면 즉시
대조할 수 있게 표를 준비해 두는 것이고, 그 티켓 없이 착수하지 않는다
(SSOTV3 00 §13 · `T-A-PIVOT-PRESERVE-001`).

매핑 근거는 SSOTV3 문구와 census 컬럼 이름뿐이다. **어느 축이 "중요한가" 는
판정하지 않는다** — 관측이 있는가만 말한다.
"""
from __future__ import annotations

import json
from pathlib import Path

import d_coverage as COV
import d_v3_census as C

# SSOTV3 14_PROMPT_D_v3.0.md "우선 연구" 8항목 — 문구 그대로
PRIORITIES = [
    ("spatial dispersion 조작화",
     ["entry_x_norm", "entry_y_norm", "entry_zone"]),
    ("visible label vs accessible name 변이",
     ["visible_label", "accessible_name", "label_relation"]),
    ("icon-only/control-type/reveal-direction taxonomy",
     ["entry_control_type", "reveal_direction"]),
    ("action sequence normalization과 edit distance sensitivity",
     ["task_flow_sequence", "experienced_flow_sequence"]),
    ("Depth와 sequence divergence의 비동일성",
     ["activation_depth", "task_flow_sequence", "experienced_flow_sequence"]),
    ("auth-gate stage variation", ["auth_gate_stage"]),
    ("task-specific obstruction", ["task_control_occlusion"]),
    ("missingness/slot dependency", None),          # 전 축 coverage 자체가 대상
]


def availability() -> dict:
    df, pin = C.read_mart_pinned(C.MART_DIR / "CANONICAL_MART_50.csv")
    n = len(df)
    cov = COV.coverage(df, [c for c in C.COLUMNS])
    rows = []
    for name, cols in PRIORITIES:
        if cols is None:
            rows.append({"priority": name, "axes": "(전 축 coverage 자체)",
                         "state": "OBSERVED", "min_n": n,
                         "note": "결측 구조는 다른 축이 0 이어도 볼 수 있다"})
            continue
        per = {c: f"{cov.get(c, 0)}/{n}" for c in cols}
        zero = [c for c in cols if cov.get(c, 0) == 0]
        if not zero:
            st = "OBSERVED"
        elif len(zero) == len(cols):
            st = "NOT_OBSERVED_AT_ALL"
        else:
            st = "PARTIAL"
        mn = min(cov.get(c, 0) for c in cols)
        rows.append({"priority": name, "axes": per, "state": st,
                     "min_n": mn, "zero_axes": zero,
                     "주의": ("**관측이 있다는 뜻이지 충분하다는 뜻이 아니다.** "
                            f"이 항목의 최소 관측은 {mn}/{n} 이고 착수 가능 여부는 A 가 정한다")
                     if 0 < mn < 20 else None})
    counts = {}
    for r in rows:
        counts[r["state"]] = counts.get(r["state"], 0) + 1
    return {"mart_sha256": pin["sha256"][:8], "n": n,
            "rows": rows, "state_counts": counts,
            "이것은_연구가_아니다": ("이미 계산된 coverage 를 SSOTV3 우선연구 8축에 "
                            "**매핑만** 한다. 새 수치·새 조작화 없음. A 의 v3 역할 "
                            "티켓 없이 착수하지 않는다"),
            "판정하지_않는_것": ("어느 축이 더 중요한가, 그리고 **착수 가능한가** — "
                          "D 는 관측이 있는가만 말한다. `OBSERVED` 는 관측의 존재이지 "
                          "충분성이 아니다"),
            "작은_n_경고": [r["priority"] for r in rows
                        if isinstance(r.get("min_n"), int) and 0 < r["min_n"] < 20]}


def controls() -> dict:
    rows = []

    def case(name, got, want, negative=False):
        rows.append({"case": name, "got": got, "want": want, "ok": got == want,
                     "expectation": "must_flag" if negative else "must_not_flag"})

    a = availability()
    case("8개 항목을 모두 훑는다", len(a["rows"]), 8)
    # 축이 하나도 관측되지 않은 항목은 착수 불가로 나와야 한다
    tco = [r for r in a["rows"] if r["priority"] == "task-specific obstruction"][0]
    case("task_control_occlusion 0/50 → NOT_OBSERVED_AT_ALL",
         tco["state"], "NOT_OBSERVED_AT_ALL", negative=True)
    seq = [r for r in a["rows"]
           if r["priority"].startswith("action sequence")][0]
    case("sequence 50/50 → OBSERVED", seq["state"], "OBSERVED")
    # **관측 존재와 충분성을 가르는지** — n=8 짜리가 경고를 달아야 한다
    sp = [r for r in a["rows"] if r["priority"].startswith("spatial")][0]
    case("spatial n=8 은 상태가 OBSERVED 이되 min_n 이 8", (sp["state"], sp["min_n"]),
         ("OBSERVED", 8))
    case("n=8 항목은 작은_n_경고에 들어간다",
         "spatial dispersion 조작화" in a["작은_n_경고"], True, negative=True)
    lab = [r for r in a["rows"] if r["priority"].startswith("visible label")][0]
    case("label 축은 일부만 관측 → PARTIAL", lab["state"], "PARTIAL", negative=True)
    ok = all(r["ok"] for r in rows)
    return {"verdict": "PASS" if ok else "FAIL", "n": len(rows),
            "must_flag": sum(1 for r in rows if r["expectation"] == "must_flag"),
            "must_not_flag": sum(1 for r in rows if r["expectation"] == "must_not_flag"),
            "failed": [r["case"] for r in rows if not r["ok"]], "cases": rows}


if __name__ == "__main__":
    import sys
    out = {"availability": availability(), "controls": controls()}
    print(json.dumps(out, ensure_ascii=False, indent=1))
    sys.exit(0 if out["controls"]["verdict"] == "PASS" else 1)
