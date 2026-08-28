"""MAIN50 시간제한 전수관측 보고서 v1 — 최종 그림 4장. (A T-A-V3-TBX-022)

**규정**: 최종 mart 는 동일조건 50 census 결과표가 **아니다.** R1 → 실패기반 R2 →
성공대상 geometry 보충 R3 가 섞인 **outcome-conditioned rescue mart** 다.
따라서 run 간·family 간 성공률과 k/50 reachability 를 **서비스 특성으로 해석하지 않는다.**

기존 6장은 `d_v3_figures.py` 에 그대로 둔다(불변성). 이 파일이 보고서용 4장이다.
"""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

# 보고서 그림에 한글 제목이 들어간다. 폰트를 지정하지 않으면 **글자가 네모로 깨진 채
# 저장되고 경고만 stderr 로 나간다** — 그림은 정상으로 보인다. 이 세션 계열의 실패다.
for _f in ("NanumGothic", "NanumBarunGothic", "Noto Sans CJK KR", "Malgun Gothic"):
    if any(_f == _x.name for _x in matplotlib.font_manager.fontManager.ttflist):
        plt.rcParams["font.family"] = _f
        break
plt.rcParams["axes.unicode_minus"] = False

import d_v3_census as C

OUT = C.ANALYSIS / "figures"

# [A TBX-022] acquisition state 3집단. FORBIDDEN_ACTION_BOUNDARY 는 **measurement 쪽**이다 —
# 사이트가 금지행위를 한 것이 아니라 collector 가 경계에서 멈춘 것이다.
GROUPS = [
    ("USABLE PATH EVIDENCE", ["ENDPOINT_REACHED", "AUTH_GATE"], "#2166ac"),
    # [A R163 / RETRACTIONS.md] `NO_SAFE_ROUTE_SITE` 의 **SITE 라벨은 철회됐다**.
    # 옛 그룹명 "SITE-SIDE ROUTE NOT OBSERVED" 는 **철회된 함의를 그룹명으로
    # 재생산**하고 있었다 — 정본이 금지한 형태다("이 토큰을 사이트에 대한
    # 진술로 쓰면 안 된다"). 정본이 지정한 대체 라벨을 쓴다.
    ("ROUTE NOT REACHED BY COLLECTOR", ["NO_SAFE_ROUTE_SITE"], "#1b9e77"),
    ("MEASUREMENT / COLLECTOR LIMITED",
     ["COLLECTOR_ZERO_CANDIDATE", "TIMEOUT",
      "NO_SAFE_ROUTE_UNVERIFIED_CANDIDATE_COUNT", "FORBIDDEN_ACTION_BOUNDARY"], "#d95f02"),
]

RESCUE_SENTENCE = (
    "Collection run은 교환가능한 반복측정이 아니다. R2와 R3는 이전 관측 결과에 따라 "
    "대상이 선택된 rescue pass이므로 run별 terminal 분포를 성능 비교나 서비스 특성 "
    "비교에 사용하지 않았다.")


def _save(fig, name):
    OUT.mkdir(parents=True, exist_ok=True)
    p = OUT / name
    fig.savefig(p, dpi=140, bbox_inches="tight")
    plt.close(fig)
    return str(p)


def _foot(fig, txt, color="dimgray"):
    fig.text(0.5, 0.005, txt, ha="center", fontsize=7, color=color)


def group_counts(df) -> dict:
    tr = Counter(str(v).strip() for v in df["terminal_reason"])
    out, seen = {}, set()
    for label, keys, _ in GROUPS:
        out[label] = {k: int(tr.get(k, 0)) for k in keys}
        seen |= set(keys)
    unmapped = {k: v for k, v in tr.items() if k not in seen}
    out["_unmapped"] = unmapped          # 매핑 밖 값은 **드러낸다**. 조용히 버리지 않는다
    out["_total"] = int(sum(tr.values()))
    return out


def figure1_acquisition_state(df):
    """50개 acquisition state. **'서비스 접근성 결과' 가 아니다.**"""
    g = group_counts(df)
    fig, ax = plt.subplots(figsize=(11, 4.4))
    left = 0
    for label, keys, color in GROUPS:
        n = sum(g[label].values())
        if n == 0:
            continue
        ax.barh([0], [n], left=left, color=color, edgecolor="white")
        detail = " · ".join(f"{k} {v}" for k, v in g[label].items() if v)
        ax.text(left + n / 2, 0, f"{label}\n{n}/50", ha="center", va="center",
                fontsize=9, color="white", fontweight="bold")
        ax.text(left + n / 2, -0.42, detail, ha="center", va="center", fontsize=6.5,
                color=color)
        left += n
    if g["_unmapped"]:
        ax.text(0.5, 0.85, "UNMAPPED terminal values: %s" % g["_unmapped"],
                transform=ax.transAxes, ha="center", color="red", fontsize=8)
    ax.set_xlim(0, C.N_TOTAL); ax.set_ylim(-0.75, 0.6)
    ax.set_yticks([]); ax.set_xlabel("targets (frozen denominator = 50)")
    ax.set_title("시간제한 수집 종료 시점의 acquisition state  (n=50 전수 시도)",
                 fontsize=12)
    _foot(fig, "50개 전수 시도 · 비교 가능한 evidence 확보에 큰 측정 제약.  "
               "FORBIDDEN_ACTION_BOUNDARY는 collector가 경계에서 멈춘 것이지 사이트의 금지행위가 아니다.",
          "darkred")
    return _save(fig, "report_fig1_acquisition_state.png")


def _cases(df):
    g = C.load_geometry_supplement()
    rows = []
    for _, r in df.iterrows():
        t = str(r["target_id"])
        if t in g:
            rows.append(dict(r) | g[t])
    return rows


R3_TRACE = C.REPO / "artifacts/v3_census/raw/E/E-REAL-CENSUS-1230-R3"


def label_geometry_match(target_id: str, visible_label: str) -> bool:
    """[A R152/R154] 이 행의 **라벨과 좌표가 같은 후보를 가리키는가**.

    mart 의 `visible_label` 은 R1 에서, `entry_x/y/zone` 은 R3 보충에서 왔다.
    **R1 trace 에는 `selected_candidate` 키가 아예 없어서**(R3 에서 신설) 두
    회차가 서로 다른 후보를 골랐을 수 있다. k=8 중 3건이 그랬다.

    D 가 F2-01 **1건**을 짚었고 전수 확장은 B 가 했다 —
    **한 건의 이상은 표본이지 결론이 아니다**(A method 절).
    """
    p = R3_TRACE / target_id / f"E_SCOUT_TRACE_{target_id}.jsonl"
    if not p.exists():
        return False
    sc = None
    for line in p.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            d = json.loads(line)
        except Exception:
            continue
        if isinstance(d.get("selected_candidate"), dict):
            sc = d["selected_candidate"]
    return bool(sc) and str(sc.get("visible_label", "")).strip() == str(visible_label).strip()


def label_geometry_evidence(target_id: str, visible_label: str, root=None) -> dict:
    """[D-DEF-103] `label_geometry_match` 가 **왜** 그 값을 냈는지 가른다.

    그 함수는 두 자리에서 조용히 `False` 를 낸다 —
    (a) trace 파일이 없을 때 (b) 어느 줄에도 `selected_candidate` 가 없을 때.
    둘 다 '**확인할 수 없다**' 인데 출력은 '**불일치**' 와 같다.

    **분류 로직은 바꾸지 않는다.** 그림 2 의 분류는 `A R152/R154` 의 조작화이고
    D 가 대상 지정 없이 바꾸지 않는다(`00 §13`). 이 함수는 **읽기 전용 진단**이며
    `controls()` 가 '두 자리가 지금 발현하지 않는다' 를 매 회 잰다.
    """
    base = R3_TRACE if root is None else Path(root)
    p = base / target_id / f"E_SCOUT_TRACE_{target_id}.jsonl"
    if not p.exists():
        return {"class": "NO_TRACE_FILE", "match": False,
                "왜": "파일이 없다 — **불일치가 아니라 확인 불가**다"}
    sc = None
    for line in p.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            d = json.loads(line)
        except Exception:                           # noqa: BLE001
            continue
        if isinstance(d.get("selected_candidate"), dict):
            sc = d["selected_candidate"]
    if not sc:
        return {"class": "NO_SELECTED_CANDIDATE", "match": False,
                "왜": "`selected_candidate` 가 없다 — R1 trace 에는 그 키가 아예 없었다(R3 에서 신설)"}
    same = str(sc.get("visible_label", "")).strip() == str(visible_label).strip()
    return {"class": "MATCH" if same else "MISMATCH", "match": same,
            "trace_label": sc.get("visible_label")}


def evidence_census(root=None) -> dict:
    """R3 대상 전부에 대해 `class` 분포를 낸다 — **확인 불가가 몇 건인가**."""
    from collections import Counter as _C
    base = R3_TRACE if root is None else Path(root)
    if not base.exists():
        return {"verdict": "NO_ROOT", "path": str(base)}
    c, rows = _C(), []
    for d in sorted(x.name for x in base.iterdir() if x.is_dir()):
        e = label_geometry_evidence(d, "", root=base)
        # **라벨을 넘기지 않았으므로 MATCH/MISMATCH 를 보고하지 않는다** — 빈 라벨로
        # 비교하면 전건이 `MISMATCH` 로 보이고 그것은 **인공물이지 관측이 아니다**.
        # 이 census 가 재는 것은 오직 **확인 가능한가**이다.
        cls = ("VERIFIABLE" if e["class"] in ("MATCH", "MISMATCH") else e["class"])
        c[cls] += 1
        rows.append({"target": d, "class": cls})
    unknown = c["NO_TRACE_FILE"] + c["NO_SELECTED_CANDIDATE"]
    return {"verdict": "PASS" if unknown == 0 else "FAIL",
            "n_targets": sum(c.values()), "by_class": dict(c),
            "n_unverifiable": unknown, "rows_evidence": rows,
            "왜_MATCH_를_안_세나": ("이 census 는 라벨을 넘기지 않는다 — 넘길 라벨이 mart 쪽에 있고 "
                          "여기서는 **확인 가능성**만 잰다. 빈 라벨로 비교하면 전건이 "
                          "`MISMATCH` 로 보이는데 그것은 **인공물이다**"),
            "**확인 불가와 불일치는 다르다**": (
                "`label_geometry_match` 는 둘을 같은 `False` 로 낸다. "
                "지금 `n_unverifiable` 이 0 이라 **그림 2 의 수치는 이 경로 때문에 틀리지 않았다** — "
                "0 이 아니게 되면 그때는 분류를 A 와 다시 봐야 한다"),
            "분류를_바꾸지_않는다": "그림 2 의 분류는 A R152/R154 의 조작화다 [00 §13]"}


def controls() -> dict:
    import tempfile as _tf
    rows = []

    def case(name, got, want, negative=False):
        rows.append({"case": name, "got": got, "want": want, "ok": got == want,
                     "expectation": "must_flag" if negative else "must_not_flag"})

    with _tf.TemporaryDirectory() as t:
        root = Path(t)
        (root / "T1").mkdir()
        (root / "T1" / "E_SCOUT_TRACE_T1.jsonl").write_text(
            json.dumps({"selected_candidate": {"visible_label": "이체"}}) + "\n",
            encoding="utf-8")
        (root / "T2").mkdir()                       # 파일 없음
        (root / "T3").mkdir()
        (root / "T3" / "E_SCOUT_TRACE_T3.jsonl").write_text(
            json.dumps({"note": "selected_candidate 없음"}) + "\n", encoding="utf-8")

        case("같은 라벨은 MATCH",
             label_geometry_evidence("T1", "이체", root=root)["class"], "MATCH")
        case("다른 라벨은 MISMATCH",
             label_geometry_evidence("T1", "조회", root=root)["class"], "MISMATCH")
        case("**파일이 없으면 확인 불가다 — 불일치가 아니다**",
             label_geometry_evidence("T2", "이체", root=root)["class"],
             "NO_TRACE_FILE", negative=True)
        case("**`selected_candidate` 가 없으면 확인 불가다**",
             label_geometry_evidence("T3", "이체", root=root)["class"],
             "NO_SELECTED_CANDIDATE", negative=True)
        case("census 가 확인 불가 2건을 센다",
             evidence_census(root=root)["n_unverifiable"], 2, negative=True)

    live = evidence_census()
    case("현재 R3 대상에 확인 불가 0", live.get("n_unverifiable"), 0)
    case("대상을 실제로 읽었다 — 0 이면 검사가 무효다", live.get("n_targets", 0) > 0, True)
    ok = all(r["ok"] for r in rows)
    return {"verdict": "PASS" if ok else "FAIL", "n": len(rows),
            "must_flag": sum(1 for r in rows if r["expectation"] == "must_flag"),
            "must_not_flag": sum(1 for r in rows if r["expectation"] == "must_not_flag"),
            "failed": [r["case"] for r in rows if not r["ok"]], "cases": rows}


def figure2_spatial_cases(df):
    """관측 가능한 사례의 진입점. **'분포' 라는 말을 쓰지 않는다** (A TBX-022).

    [A R154] **섞는 것을 막을 수 없으면 보이게 만든다.** 8점을 다 그리되 두 층으로
    나눈다 — 라벨·좌표가 같은 후보인 5점은 실선 마커에 라벨을 달고, 출처가
    어긋난 3점은 속 빈 마커에 라벨을 달지 않는다. B 는 8점 무라벨을 권했으나
    A 가 채택하지 않았다: **무엇의 좌표인지 주장하지 않으면 진입점 분산도 못
    말한다.**
    """
    cs = _cases(df)
    n_ok = sum(1 for c in cs
               if label_geometry_match(c["target_id"], c.get("visible_label", "")))
    ok_cases = [c for c in cs
                if label_geometry_match(c["target_id"], c.get("visible_label", ""))]
    fig, ax = plt.subplots(figsize=(7.6, 6.6))
    fig.subplots_adjust(top=.845, bottom=.135, left=.105, right=.965)
    placed = []
    if not cs:
        ax.text(0.5, 0.5, "NO OBSERVABLE CASES", ha="center", va="center",
                color="red", fontsize=13, transform=ax.transAxes)
    else:
        for c in cs:
            x, y = float(c["entry_x_norm"]), float(c["entry_y_norm"])
            ok = label_geometry_match(c["target_id"], c.get("visible_label", ""))
            # 오른쪽 끝은 라벨을 왼쪽으로 뺀다. 이미 쓴 자리와 가까우면 아래로 내린다
            ha, dx = ("right", -8) if x > 0.86 else ("left", 7)
            dy = 4
            for px, py in placed:
                if abs(px - x) < .10 and abs(py - y) < .055:
                    dy = -13
            placed.append((x, y))
            if ok:
                ax.scatter([x], [y], s=95, color="#2166ac", alpha=.9, zorder=3)
                ax.annotate(f"{c['target_id']}  {c.get('visible_label','')}", (x, y),
                            fontsize=6.6, ha=ha, xytext=(dx, dy),
                            textcoords="offset points", zorder=4)
            else:
                # 라벨을 달지 않는다 — 이 좌표가 그 라벨의 것이 아니기 때문이다
                ax.scatter([x], [y], s=95, facecolors="none", edgecolors="#7d858f",
                           linewidths=1.4, zorder=3)
                ax.annotate(c["target_id"], (x, y), fontsize=6.2, color="#7d858f",
                            ha=ha, xytext=(dx, dy), textcoords="offset points", zorder=4)
        from matplotlib.lines import Line2D
        ax.legend(handles=[
            Line2D([], [], marker="o", linestyle="none", color="#2166ac", markersize=8,
                   label="라벨·좌표가 같은 후보 (n=%d)" % n_ok),
            Line2D([], [], marker="o", linestyle="none", markerfacecolor="none",
                   markeredgecolor="#7d858f", markersize=8,
                   label="라벨·좌표 출처 불일치 — 좌표는 R3 후보의 것 (n=%d)" % (len(cs) - n_ok)),
        ], loc="lower left", fontsize=7.4, framealpha=.92, borderpad=.6)
        # 0·1 에 붙은 점이 잘리지 않도록 여유만 준다. 눈금은 0~1 그대로다
        ax.set_xlim(-.03, 1.03); ax.set_ylim(1.03, -.03)
        ax.set_xticks([0, .2, .4, .6, .8, 1.0]); ax.set_yticks([0, .2, .4, .6, .8, 1.0])
        ax.set_xlabel("entry_x_norm (0=left)"); ax.set_ylabel("entry_y_norm (0=top)")
        ax.grid(alpha=.25, zorder=0)
    # [A R153] 수치는 **일치분 n=5 에서** 낸다. 8 로 세면 오염분이 섞인다
    zones = Counter(str(c.get("entry_zone")) for c in ok_cases)
    ctrls = Counter(str(c.get("entry_control_type")) for c in ok_cases)
    # 위에서부터 겹치지 않게 명시 배치한다 — 제목이 2줄이라 set_title 로는 부딪힌다
    fig.text(.5, .975, "라벨·좌표가 같은 후보인 사례만 셈, n=%d/%d" % (n_ok, len(df)),
             ha="center", fontsize=8.8, color="dimgray")
    fig.text(.5, .935, "관측 가능한 %d개 사례의 진입점은 같은 위치에 모이지 않았다" % n_ok,
             ha="center", fontsize=12.5, weight="bold")
    fig.text(.5, .900, "(n=%d/%d, 좌표 출처 불일치 %d건 별도 표기)"
             % (n_ok, len(df), len(cs) - n_ok), ha="center", fontsize=10)
    fig.text(.5, .868, "zone %d종/%d · control %d종/%d  (비수렴)"
             % (len(zones), n_ok, len(ctrls), n_ok),
             ha="center", fontsize=8.6, color="#2166ac")
    _foot(fig, "개별 사례다. %d개는 진입 후보 자체가 관측되지 않아 위치라는 것이 존재하지 않는다. "
               "속 빈 %d점은 라벨이 R1, 좌표가 R3 후보의 것이라 라벨을 달지 않았다 — "
               "섞는 것을 막을 수 없으면 보이게 만든다 (A R154). "
               "source: E_R3_SUPPLEMENT (live click geometry)."
               % (len(df) - len(cs), len(cs) - n_ok))
    return _save(fig, "report_fig2_spatial_cases.png")


def figure3_flow_cases(df):
    """사례별 흐름 small multiples. 관측된 스텝만 그린다 — 없는 단계를 그리지 않는다."""
    cs = _cases(df)
    n = max(1, len(cs))
    ncol = 4
    nrow = (n + ncol - 1) // ncol
    fig, axes = plt.subplots(nrow, ncol, figsize=(3.4 * ncol, 2.1 * nrow))
    axes = [axes] if n == 1 and nrow == 1 and ncol == 1 else list(
        axes.flat if hasattr(axes, "flat") else [axes])
    depths, menus = set(), set()
    for i, ax in enumerate(axes):
        if i >= len(cs):
            ax.axis("off"); continue
        c = cs[i]
        seq = str(c.get("experienced_flow_sequence") or "")
        try:
            steps = json.loads(seq.replace("'", '"')) if seq.strip().startswith("[") else []
        except Exception:
            steps = []
        term = str(c.get("terminal_reason"))
        nodes = ["T0"] + [str(s) for s in steps] + [term]
        depths.add(str(c.get("activation_depth")))
        menus.add(str(c.get("menu_dependency")))
        for j, nd in enumerate(nodes):
            col = ("#2166ac" if j == len(nodes) - 1 and term == "ENDPOINT_REACHED"
                   else "#d95f02" if j == len(nodes) - 1 else "#777777")
            ax.text(j / max(1, len(nodes) - 1), 0.5, nd, ha="center", va="center",
                    fontsize=6.5, color="white", zorder=3,
                    bbox=dict(boxstyle="round,pad=0.28", fc=col, ec="none"))
            if j:
                ax.annotate("", xy=(j / max(1, len(nodes) - 1) - 0.06, 0.5),
                            xytext=((j - 1) / max(1, len(nodes) - 1) + 0.06, 0.5),
                            arrowprops=dict(arrowstyle="->", color="#999999", lw=.9))
        ax.set_title(f"{c['target_id']}  {str(c.get('service',''))[:16]}   "
                     f"depth={c.get('activation_depth')} menu={c.get('menu_dependency')}",
                     fontsize=7.5)
        ax.set_xlim(-0.12, 1.12); ax.set_ylim(0, 1); ax.axis("off")
    fig.suptitle("관측 가능한 %d개 사례의 과업 진입 흐름" % len(cs), fontsize=12, y=1.0)
    # [A 정정] `nav_container_type` 은 **E 가 산출한 적이 없는 변수**다(GEOMETRY_SUPPLEMENT 키에 없음).
    # 7/8 은 전부 B 사후 파생이고 인용 가능한 것은 5, 그중 1 은 AMBIGUOUS → 실질 4.
    # 따라서 "비수렴" 도 "미관측 8/8" 도 아니고 **이 주장에서 제외**한다.
    fig.text(0.5, 0.945,
             "수렴: SELECT_FUNCTION ×8 · activation_depth=1 ×8 · menu_dependency=False ×8      "
             "비수렴: entry_zone 4종/5 · entry_control_type 2종/5   (라벨·좌표 일치분. 출처 불일치 3건 제외 — A R153)",
             ha="center", fontsize=8.5, color="#2166ac")
    fig.text(0.5, 0.915,
             "navigation container는 이 주장에 포함하지 않는다 — E 산출 0 · B 사후파생 7 · 인용가능 5(실질 4).",
             ha="center", fontsize=7.5, color="dimgray")
    _foot(fig, "관측된 스텝만 그렸다 — 없는 단계를 채우지 않았다. 이 %d개 사례는 모두 메뉴를 거치지 않는 단일 스텝이었다.\n"
               "[한계 L13] 관측된 8건이 전부 얕은 경로였던 것은 사이트가 얕아서가 아니라 수집기가 깊은 경로를 뚫지 못했기 때문일 수 있다 — "
               "COLLECTOR_ZERO_CANDIDATE 21의 계통적 한계와 같은 방향의 선택편향이다. '사이트가 얕다'로 해석하지 않는다."
               % len(cs), "darkred")
    return _save(fig, "report_fig3_flow_cases.png")


def figure4_measurement_boundary(df):
    """**측정 가능한 분모가 축마다 다르다**는 것을 보인다. 이번 연구의 방법론적 결과."""
    g = group_counts(df)
    usable = sum(g["USABLE PATH EVIDENCE"].values())
    cs = _cases(df)
    # [D-DEF-41] 채워짐이 아니라 독립 관측으로 센다
    paired = C.independently_paired_labels(df)
    # [C-ASSURANCE-114653] k=8 CONFIRMED — pre-R3 provenance 8/8 독립 확인.
    # 의미는 '전체 acquisition history 에서 8 고유 target 에 usable evidence ≥1회' 이며
    # **8/50 reachability 가 아니다**.
    stages = [("frozen targets", C.N_TOTAL), ("attempted", int(len(df))),
              ("usable path evidence  k=%d (CONFIRMED)" % usable, usable),
              ("geometry-complete cases", len(cs)),
              ("independently observed label pairs", paired)]
    # [A] 0 만 보이면 "라벨이 하나도 없었다" 로 읽힌다. **채워진 28 을 함께 보인다** —
    # 두 수의 차이가 곧 "mart 가 경고를 값으로 들고 있었다" 는 사실이다.
    filled_both = int(sum(1 for _, r in df.iterrows()
                          if not C.is_missing(r["visible_label"], "visible_label")
                          and not C.is_missing(r["accessible_name"], "accessible_name")))
    fig, ax = plt.subplots(figsize=(10.5, 4.6))
    for i, (label, v) in enumerate(stages):
        w = v / C.N_TOTAL
        ax.barh([-i], [w], height=.62, color=plt.cm.viridis(1 - i / len(stages)),
                edgecolor="white")
        ax.text(w + .012, -i, f"{v}", va="center", fontsize=11, fontweight="bold")
        ax.text(-0.012, -i, label, va="center", ha="right", fontsize=9)
    ax.set_xlim(-0.42, 1.12); ax.set_ylim(-len(stages) + .4, .6)
    ax.set_xticks([]); ax.set_yticks([])
    for s in ax.spines.values():
        s.set_visible(False)
    ax.set_title("Measurement boundary — 측정 가능한 분모가 축마다 다르다", fontsize=12)
    _foot(fig, "k=8은 '전체 acquisition history에서 8개 고유 target에 usable task-path evidence가 최소 1회 확보됐다'는 뜻이다. "
               "'50개 중 8개 서비스가 접근 가능했다'가 아니다 — 8/50 reachability로 읽지 마라.\n"
               "independently observed label pairs %d · 두 열이 함께 채워진 행 %d — 그 %d 전부가 AX_NOT_INDEPENDENTLY_OBSERVED다"
               "(accessible_name이 visible text 복사).   R1 attempted 50 / R1-only surviving in mart 15."
               % (paired, filled_both, filled_both), "darkred")
    return _save(fig, "report_fig4_measurement_boundary.png")


ALL = [figure1_acquisition_state, figure2_spatial_cases,
       figure3_flow_cases, figure4_measurement_boundary]


def render_all(df) -> dict:
    return {fn.__name__: fn(df) for fn in ALL}


if __name__ == "__main__":
    df, pin = C.read_mart_pinned(C.MART_DIR / "CANONICAL_MART_50.csv")
    print(json.dumps({"mart_pin": pin, "figures": render_all(df),
                      "groups": group_counts(df)}, ensure_ascii=False, indent=1))
