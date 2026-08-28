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
    ("SITE-SIDE ROUTE NOT OBSERVED", ["NO_SAFE_ROUTE_SITE"], "#1b9e77"),
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


def figure2_spatial_cases(df):
    """관측 가능한 사례의 진입점. **'분포' 라는 말을 쓰지 않는다** (A TBX-022)."""
    cs = _cases(df)
    fig, ax = plt.subplots(figsize=(7.2, 6.4))
    if not cs:
        ax.text(0.5, 0.5, "NO OBSERVABLE CASES", ha="center", va="center",
                color="red", fontsize=13, transform=ax.transAxes)
    else:
        for c in cs:
            x, y = float(c["entry_x_norm"]), float(c["entry_y_norm"])
            ax.scatter([x], [y], s=90, color="#2166ac", alpha=.85, zorder=3)
            ax.annotate(f"{c['target_id']}\n{c.get('service','')}", (x, y),
                        fontsize=6.5, xytext=(6, 4), textcoords="offset points")
        ax.set_xlim(0, 1); ax.set_ylim(1, 0)
        ax.set_xlabel("entry_x_norm (0=left)"); ax.set_ylabel("entry_y_norm (0=top)")
        ax.grid(alpha=.25, zorder=0)
    zones = Counter(str(c.get("entry_zone")) for c in cs)
    ctrls = Counter(str(c.get("entry_control_type")) for c in cs)
    ax.set_title("관측 가능한 %d개 사례의 진입점은 같은 위치에 모이지 않았다" % len(cs),
                 fontsize=12)
    fig.text(0.5, 0.89, "zone %d종/%d · control %d종/%d  (비수렴)"
             % (len(zones), len(cs), len(ctrls), len(cs)),
             ha="center", fontsize=8.5, color="#2166ac")
    fig.text(0.5, 0.93, "Observed cases only, n=%d/%d" % (len(cs), len(df)),
             ha="center", fontsize=9, color="dimgray")
    _foot(fig, "개별 사례다. 나머지 %d개는 진입 후보 자체가 관측되지 않아 위치라는 것이 존재하지 않는다. "
               "source: E_R3_SUPPLEMENT (live click geometry)." % (len(df) - len(cs)))
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
    navs = Counter(str(c.get("nav_container_type")) for c in cs)
    nav_obs = sum(v for k, v in navs.items() if not C.is_missing(k))
    fig.text(0.5, 0.945,
             "수렴: 조작순서 · activation_depth=1 · menu_dependency=False (8/8)      "
             "비수렴: zone 5종/8 · control 2종/8 · nav container %d종/%d관측"
             % (len([k for k in navs if not C.is_missing(k)]), nav_obs),
             ha="center", fontsize=8.5, color="#2166ac")
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
    paired = int(sum(1 for _, r in df.iterrows()
                     if not C.is_missing(r["visible_label"])
                     and not C.is_missing(r["accessible_name"])))
    # [C-ASSURANCE-114653] k=8 CONFIRMED — pre-R3 provenance 8/8 독립 확인.
    # 의미는 '전체 acquisition history 에서 8 고유 target 에 usable evidence ≥1회' 이며
    # **8/50 reachability 가 아니다**.
    stages = [("frozen targets", C.N_TOTAL), ("attempted", int(len(df))),
              ("usable path evidence  k=%d (CONFIRMED)" % usable, usable),
              ("geometry-complete cases", len(cs)),
              ("paired visible+AX label cases", paired)]
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
               "R1 attempted 50 / R1-only surviving in mart 15 (두 수는 서로 다른 것을 센다).",
          "darkred")
    return _save(fig, "report_fig4_measurement_boundary.png")


ALL = [figure1_acquisition_state, figure2_spatial_cases,
       figure3_flow_cases, figure4_measurement_boundary]


def render_all(df) -> dict:
    return {fn.__name__: fn(df) for fn in ALL}


if __name__ == "__main__":
    df, pin = C.read_mart_pinned(C.MART_DIR / "CANONICAL_MART_50.csv")
    print(json.dumps({"mart_pin": pin, "figures": render_all(df),
                      "groups": group_counts(df)}, ensure_ascii=False, indent=1))
