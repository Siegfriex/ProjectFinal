"""보고서 표 4종 — 그림 4장에 대응. (A TBX-025 미충족 4항 중 `canonical tables`)

**같은 mart_pin 에서 나온다.** 표와 그림이 다른 판본을 가리키면 둘 다 정상으로 보인다
(D-DEF-34 와 같은 자리). 그래서 pin 을 표 안에 적는다.

표는 그림보다 인용되기 쉽다 — 그림의 경고 문구가 표에는 없다. 그래서 **각 표의 첫 줄에
읽는 법을 적는다.** 특히 k/50 을 접근성 성공률로 읽지 못하게.
"""
from __future__ import annotations

import csv
import json
from collections import Counter
from pathlib import Path

import d_v3_census as C
import d_v3_report as R

OUT = C.ANALYSIS / "tables"


def _write(name: str, header: list, rows: list, note: str, pin: dict) -> dict:
    OUT.mkdir(parents=True, exist_ok=True)
    csv_p = OUT / f"{name}.csv"
    with csv_p.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow([f"# {note}"])
        w.writerow([f"# mart_sha256={pin['sha256']}  rows={pin.get('bytes')}bytes"])
        w.writerow(header)
        w.writerows(rows)
    md_p = OUT / f"{name}.md"
    md = [f"> {note}", "",
          f"`mart_sha256 = {pin['sha256']}`", "",
          "| " + " | ".join(header) + " |",
          "|" + "|".join(["---"] * len(header)) + "|"]
    md += ["| " + " | ".join(str(c) for c in r) + " |" for r in rows]
    md_p.write_text("\n".join(md) + "\n", encoding="utf-8")
    return {"csv": str(csv_p), "md": str(md_p), "rows": len(rows)}


def t1_acquisition_state(df, pin):
    g = R.group_counts(df)
    fams = sorted(df["family_id"].astype(str).unique())
    rows = []
    for label, keys, _ in R.GROUPS:
        for k in keys:
            n = int(g[label].get(k, 0))
            per = {f: int(((df["family_id"].astype(str) == f) &
                           (df["terminal_reason"].astype(str) == k)).sum()) for f in fams}
            rows.append([label, k, f"{n}/50"] + [f"{per[f]}/10" for f in fams])
    rows.append(["TOTAL", "", f"{g['_total']}/50"] +
                [f"{int((df['family_id'].astype(str) == f).sum())}/10" for f in fams])
    note = ("시간제한 수집 종료 시점의 acquisition state. **서비스 접근성 결과가 아니다.** "
            "MEASUREMENT/COLLECTOR LIMITED 는 사이트에 대한 진술이 아니라 수집기에 대한 진술이며, "
            "FORBIDDEN_ACTION_BOUNDARY 는 collector 가 경계에서 멈춘 것이다.")
    return _write("T1_acquisition_state", ["group", "terminal_reason", "overall"] + fams,
                  rows, note, pin)


def t2_observable_cases(df, pin):
    cs = R._cases(df)
    cols = ["target_id", "family_id", "service", "terminal_reason", "entry_zone",
            "entry_control_type", "activation_depth", "menu_dependency",
            "auth_gate_stage", "experienced_flow_sequence"]
    rows = [[str(c.get(k, "")) for k in cols] for c in cs]
    note = ("관측 가능한 %d개 개별 사례. **분포가 아니다** — n=%d/50 이고 통계로 쓰지 않는다. "
            "이 8건이 전부 얕은 경로였던 것은 사이트가 얕아서가 아니라 수집기가 깊은 경로를 "
            "뚫지 못했기 때문일 수 있다(한계 L13). navigation container 는 E 산출 0 이라 이 표에서 뺐다."
            % (len(cs), len(cs)))
    return _write("T2_observable_cases", cols, rows, note, pin)


def t3_measurement_boundary(df, pin):
    g = R.group_counts(df)
    usable = sum(g["USABLE PATH EVIDENCE"].values())
    cs = R._cases(df)
    paired = C.independently_paired_labels(df)
    filled_both = int(sum(1 for _, r in df.iterrows()
                          if not C.is_missing(r["visible_label"], "visible_label")
                          and not C.is_missing(r["accessible_name"], "accessible_name")))
    cov = C.axis_coverage(df)
    rows = [["frozen targets", 50, "manifest v3.0.2"],
            ["attempted", int(len(df)), "전수 시도"],
            ["usable path evidence (k)", usable,
             "C 가 pre-R3 provenance 8/8 확인. **8/50 reachability 가 아니다**"],
            ["geometry-complete cases", len(cs), "E_R3_SUPPLEMENT — hash NOT_ASSURED"],
            ["independently paired visible+AX label", paired,
             "**독립 관측 쌍 0.** 두 열이 함께 채워진 행은 %d 이지만 그중 %d 이 "
             "AX_NOT_INDEPENDENTLY_OBSERVED — accessible_name 이 visible text 복사다. "
             "AX 트리 원자료 없음(오류 스텁 107/107), 재추출 불가"
             % (filled_both, filled_both - paired)]]
    for c in ("entry_zone", "entry_control_type", "activation_depth",
              "menu_dependency", "reveal_direction", "task_control_occlusion"):
        st = cov.get(c, {}).get("state", "?")
        rows.append([f"axis: {c}", st,
                     "UNWIRED — 값이 0 인 것이 아니라 한 건도 측정되지 않았다"
                     if st == "AXIS_NOT_OBSERVED" else ""])
    note = ("**측정 가능한 분모가 축마다 다르다.** 이 표의 어떤 수도 '서비스의 N%' 로 읽지 마라 — "
            "acquisition 결과이지 접근성 성공률이 아니다.")
    return _write("T3_measurement_boundary", ["stage / axis", "value", "note"], rows, note, pin)


def t4_collection_runs(df, pin):
    runs = Counter(str(v) for v in df["collection_run"])
    purpose = {"E-REAL-CENSUS-1230": "전수 1차",
               "E-REAL-CENSUS-1230-R2": "click_failed 계기결함 재측정",
               "E-REAL-CENSUS-1230-R2B": "계기결함 재측정 2차(합집합 gap)",
               "E-REAL-CENSUS-1230-R3": "이미 도달한 8건의 geometry 보충 — 선택 풀 제외"}
    rule = {"E-REAL-CENSUS-1230": "전체 50",
            "E-REAL-CENSUS-1230-R2": "route[].error 에 click_failed",
            "E-REAL-CENSUS-1230-R2B": "합집합 기준 중 R2 미실시분",
            "E-REAL-CENSUS-1230-R3": "R1/R2 에서 이미 endpoint 도달한 target"}
    rows = [[r, runs.get(r, 0), purpose.get(r, "?"), rule.get(r, "?")]
            for r in list(purpose)]
    sup = int(sum(1 for v in df["superseded_runs"]
                  if str(v).strip() not in ("", "NONE", "none", "null", "[]")))
    rows.append(["(superseded rows)", sup, "재수집으로 대체된 행", "provenance 전용"])
    rows.append(["R1 attempted", 50, "R1 에서 시도된 target 수", "mart 잔존 15 와 다른 것을 센다"])
    note = (R.RESCUE_SENTENCE + "  이 표는 **목적**을 보이기 위한 것이며 회차별 성공률로 읽으면 안 된다. "
            "`collection_run`·`superseded_runs` 는 provenance 전용이고 통계변수가 아니다.")
    return _write("T4_collection_runs", ["collection_run", "rows", "purpose", "selection rule"],
                  rows, note, pin)


ALL = [t1_acquisition_state, t2_observable_cases, t3_measurement_boundary, t4_collection_runs]


def render_all(df, pin) -> dict:
    return {fn.__name__: fn(df, pin) for fn in ALL}


if __name__ == "__main__":
    df, pin = C.read_mart_pinned(C.MART_DIR / "CANONICAL_MART_50.csv")
    print(json.dumps({"mart_pin": pin, "tables": render_all(df, pin)},
                     ensure_ascii=False, indent=1))
