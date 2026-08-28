"""V3 census 최종 figure 6종 (T-A-V3-TBX-008).

모든 figure 는 **빈 데이터에서도 끝까지 돈다.** 그리고 빈 그림과 데이터 있는
그림이 **구분된다** — 그림 안에 `data_state` 를 찍는다. 그리지 못한 것을
'그렸다' 로 읽으면 이 세션 내내 나온 그 결함이다.

축소사다리(TBX-009)는 A 가 지시한다. D 가 스스로 버리지 않는다.
"""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

import d_v3_census as C

FIGDIR = C.ANALYSIS / "figures"
TABDIR = C.ANALYSIS / "tables"


def _stamp(fig, df, title, extra=""):
    st = C.data_state(df)
    fig.suptitle(title, fontsize=13, y=0.98)
    tag = f"data_state={st}   n_rows={len(df)}/{C.N_TOTAL}"
    if getattr(df, "attrs", {}).get("synthetic"):
        tag = "*** SYNTHETIC FIXTURE — NOT REAL OBSERVATION ***   " + tag
    if extra:
        tag += "   " + extra
    fig.text(0.5, 0.005, tag, ha="center", fontsize=7,
             color=("red" if (st == "NO_DATA" or df.attrs.get("synthetic")) else "dimgray"))
    return st


def _axis_absent(ax, col, cov):
    """[A R87] 입력이 0 인 축은 **그리지 않는다.** 빈 그림은 없음을 0 으로 보이게 한다."""
    ax.text(0.5, 0.55, "AXIS_NOT_OBSERVED", ha="center", va="center",
            fontsize=11, color="darkred", transform=ax.transAxes)
    ax.text(0.5, 0.38, f"{col}\n0/{cov.get(col,{}).get('n','?')} observed",
            ha="center", va="center", fontsize=7, color="dimgray",
            transform=ax.transAxes)
    ax.set_xticks([]); ax.set_yticks([])
    for sp in ax.spines.values():
        sp.set_linestyle(":"); sp.set_color("darkred")


def _nodata(ax, msg="NO DATA YET"):
    ax.text(0.5, 0.5, msg, ha="center", va="center", fontsize=14, color="red",
            transform=ax.transAxes)
    ax.set_xticks([]); ax.set_yticks([])


def _save(fig, name):
    FIGDIR.mkdir(parents=True, exist_ok=True)
    p = FIGDIR / name
    fig.savefig(p, dpi=130, bbox_inches="tight")
    plt.close(fig)
    return str(p)


def fig1_coverage_terminal(df):
    """family별 terminal_reason 분포. **k/10 · k/50 표기 필수.**"""
    fig, axes = plt.subplots(1, 2, figsize=(13, 4.6))
    den = C.denominators(df)
    if len(df) == 0:
        _nodata(axes[0]); _nodata(axes[1])
    else:
        fams = sorted(df["family_id"].astype(str).unique())
        reasons = sorted({str(r) for r in df["terminal_reason"] if str(r).strip()})
        # [A R74] 수집기의 0 과 사이트의 사실을 **다른 색으로**. 합치면 그림이 사이트 탓을 한다.
        COLORS = {C.COLLECTOR_ZERO: "#d95f02",      # 수집기 관측 — 주황
                  C.SITE_NO_ROUTE: "#1b9e77",       # 사이트 관측 — 초록
                  C.UNSPLIT_NO_ROUTE: "#999999",    # 아직 안 나뉨 — 회색. 어느 쪽인지 모른다
                  "ENDPOINT_REACHED": "#2166ac"}
        bottom = [0] * len(fams)
        for r in reasons:
            vals = [int(((df["family_id"].astype(str) == f) &
                         (df["terminal_reason"].astype(str) == r)).sum()) for f in fams]
            lab = r
            if r == C.COLLECTOR_ZERO: lab = f"{r} (collector obs.)"
            elif r == C.SITE_NO_ROUTE: lab = f"{r} (site obs.)"
            elif r == C.UNSPLIT_NO_ROUTE: lab = f"{r} (NOT YET SPLIT — unknown which)"
            axes[0].bar(fams, vals, bottom=bottom, label=lab, color=COLORS.get(r))
            bottom = [b + v for b, v in zip(bottom, vals)]
        axes[0].set_ylabel("targets"); axes[0].set_ylim(0, C.N_PER_FAMILY)
        axes[0].legend(fontsize=7, ncol=2)
        for i, f in enumerate(fams):
            b = den["by_family"].get(f, {})
            axes[0].text(i, C.N_PER_FAMILY * 0.96,
                         f"{b.get('completed',0)}/{C.N_PER_FAMILY}",
                         ha="center", fontsize=8)
            axes[0].text(i, C.N_PER_FAMILY * 0.88,
                         f"att {b.get('attempted',0)}", ha="center", fontsize=6,
                         color="dimgray")
        o = den["overall"]
        labels = ["attempted", "evidence_adequate", "completed", "failed"]
        axes[1].axvline(C.N_TOTAL, color="black", ls=":", lw=1)
        axes[1].barh(labels, [o[k] for k in labels], color="steelblue")
        for i, k in enumerate(labels):
            axes[1].text(o[k] + 0.4, i, f"{o[k]}/{C.N_TOTAL}", va="center", fontsize=9)
        axes[1].set_xlim(0, C.N_TOTAL * 1.15)
    axes[0].set_title("terminal_reason by family (k/10)", fontsize=10)
    axes[1].set_title("denominators — overall (k/50)", fontsize=10)
    if "collection_run" in df.columns and len(df):
        rc = Counter(str(v).replace("E-REAL-CENSUS-1230", "R1").replace("R1-R", "R")
                     for v in df["collection_run"])
        fig.text(0.5, 0.925, "COLLECTION RUNS MIXED: " +
                 " · ".join(f"{k} {v}" for k, v in sorted(rc.items())) +
                 "   — R1-only rows are a minority; this confounds family comparison",
                 ha="center", fontsize=8, color="darkred")
    sp = den["overall"].get("collector_vs_site", {})
    _stamp(fig, df, "1. coverage / terminal_reason",
           "R74 split: collector=%s site=%s NOT_YET_SPLIT=%s   |   denominator frozen at %d"
           % (sp.get("collector_observation"), sp.get("site_observation"),
              sp.get("NOT_YET_SPLIT"), C.N_TOTAL))
    return _save(fig, "fig1_coverage_terminal.png")


def fig2_entry_spatial_map(df):
    cov = C.axis_coverage(df)
    fig, axes = plt.subplots(1, 2, figsize=(12.5, 5))
    obs = df[[C.numeric_observed(v) for v in df["entry_x_norm"]]] if len(df) else df
    # mart 에 좌표가 없으면 E 의 R3 보충을 쓴다 (A R106). 출처를 섞지 않는다.
    supp = C.load_geometry_supplement() if (len(df) and len(obs) == 0) else {}
    if supp:
        rows = [r for _, r in df.iterrows() if str(r["target_id"]) in supp]
        if rows:
            import pandas as pd
            obs = pd.DataFrame([dict(r) | supp[str(r["target_id"])] for r in rows])
            cov = dict(cov); cov["entry_x_norm"] = {"observed": len(obs), "n": len(df),
                                                    "state": f"{len(obs)}/{len(df)}"}
    if len(df) and cov["entry_x_norm"]["state"] == "AXIS_NOT_OBSERVED":
        _axis_absent(axes[0], "entry_x_norm", cov)
        _axis_absent(axes[1], "entry_zone", cov)
    elif len(obs) == 0:
        _nodata(axes[0], "NO OBSERVED COORDINATES")
        _nodata(axes[1])
    else:
        # [A R106] n 이 작으면 **분포로 그리지 않는다.** 개별 점을 라벨과 함께 찍고
        # 제목에 n/50 을 박는다. family 별 비교도 하지 않는다 — F1 은 0 이거나 1~2 다.
        small = len(obs) <= 10
        for f in sorted(obs["family_id"].astype(str).unique()):
            s = obs[obs["family_id"].astype(str) == f]
            axes[0].scatter([float(x) for x in s["entry_x_norm"]],
                            [float(y) for y in s["entry_y_norm"]],
                            label=(None if small else f), s=52, alpha=.85)
        if small:
            for _, r in obs.iterrows():
                axes[0].annotate(str(r["target_id"]),
                                 (float(r["entry_x_norm"]), float(r["entry_y_norm"])),
                                 fontsize=6, xytext=(3, 3), textcoords="offset points")
        else:
            axes[0].legend(fontsize=8)
        axes[0].set_xlim(0, 1); axes[0].set_ylim(1, 0)
        axes[0].set_xlabel("entry_x_norm"); axes[0].set_ylabel("entry_y_norm (0=top)")
        z = Counter(str(v) for v in obs["entry_zone"] if not C.is_missing(v))
        if small or not z:
            axes[1].text(0.5, 0.5,
                         "n=%d — individual points only\nNO DISTRIBUTION, NO FAMILY COMPARISON\n(A R106)"
                         % len(obs), ha="center", va="center", fontsize=9,
                         color="darkred", transform=axes[1].transAxes)
            axes[1].set_xticks([]); axes[1].set_yticks([])
        else:
            axes[1].bar(list(z.keys()), list(z.values()), color="darkseagreen")
            axes[1].set_ylabel("targets")
    src = "E_R3_SUPPLEMENT (live click geometry)" if supp else "mart"
    axes[0].set_title(f"entry point position  [source: {src}]", fontsize=9)
    axes[1].set_title("entry_zone" + ("" if len(obs) > 10 else "  (suppressed at small n)"),
                      fontsize=10)
    fig.suptitle("2. entry spatial map   n=%d / %d" % (len(obs), len(df)) if len(df) else "2. entry spatial map",
                 fontsize=13, y=0.99)
    _stamp(fig, df, "2. entry spatial map   n=%d / %d" % (len(obs), len(df)) if len(df) else "2. entry spatial map",
           (f"observed_coords={len(obs)}/{len(df)}   "
            f"(provenance: E_LIVE_SCOUT vs B_DERIVED_FROM_DOM_POSTHOC — see D_PROVENANCE)")
           if len(df) else "")
    return _save(fig, "fig2_entry_spatial_map.png")


def fig3_entry_implementation(df):
    # [A TBX-021 R113] `reveal_direction` 은 **100% sentinel = UNWIRED** 다.
    # 0 으로 그리면 "reveal 이 없다" 로 읽힌다 — 축을 **뺀다**. 빈 패널도 두지 않는다.
    # 값이 0 인 것과 한 건도 측정되지 않은 것은 다른 사건이다 (A R110 열 단위 WIRED).
    ALL = ["entry_control_type", "menu_dependency", "nav_container_type",
           "reveal_direction", "auth_gate_stage"]
    cov0 = C.axis_coverage(df) if len(df) else {}
    unwired = [c for c in ALL if cov0.get(c, {}).get("state") == "AXIS_NOT_OBSERVED"]
    cols = [c for c in ALL if c not in unwired] or ALL
    fig, axes = plt.subplots(1, len(cols), figsize=(17, 3.8))
    cov = C.axis_coverage(df)
    for ax, c in zip(axes, cols):
        vals = Counter(str(v) for v in df[c] if not C.is_missing(v)) if len(df) else Counter()
        if len(df) and cov.get(c, {}).get("state") == "AXIS_NOT_OBSERVED":
            _axis_absent(ax, c, cov)          # 관측 0 — 빈 막대가 아니라 부재로 표시
        elif not vals:
            _nodata(ax, "NO DATA")
        else:
            ax.bar(list(vals.keys()), list(vals.values()), color="cornflowerblue")
            ax.tick_params(axis="x", rotation=45, labelsize=7)
        ax.set_title(f"{c}\n[POST-HOC DOM DERIVED]", fontsize=8)
    _stamp(fig, df, "3. entry implementation",
           ("UNWIRED axes REMOVED (not drawn as zero): " + ", ".join(unwired))
           if unwired else "all axes observed")
    return _save(fig, "fig3_entry_implementation.png")


def fig4_activation_depth(df):
    """scroll / typing / forced dismissal 을 **합산하지 않는다** (TBX-006)."""
    fig, ax = plt.subplots(figsize=(11, 4.6))
    cov = C.axis_coverage(df)
    obs = df[[C.numeric_observed(v) for v in df["activation_depth"]]] if len(df) else df
    if len(df) and cov["activation_depth"]["state"] == "AXIS_NOT_OBSERVED":
        _axis_absent(ax, "activation_depth", cov)
    elif len(obs) == 0:
        _nodata(ax, "NO OBSERVED DEPTH")
    else:
        fams = sorted(obs["family_id"].astype(str).unique())
        for i, f in enumerate(fams):
            s = [float(v) for v in obs[obs["family_id"].astype(str) == f]["activation_depth"]]
            ax.scatter([i + (j - len(s) / 2) * 0.045 for j in range(len(s))], s, s=36, alpha=.8)
            s2 = sorted(s)
            if s2:
                med = s2[len(s2) // 2]
                q1 = s2[len(s2) // 4]; q3 = s2[(3 * len(s2)) // 4]
                ax.plot([i - .3, i + .3], [med, med], color="black", lw=2)
                ax.plot([i, i], [q1, q3], color="black", lw=1)
        ax.set_xticks(range(len(fams))); ax.set_xticklabels(fams)
        ax.set_ylabel("activation_depth (scroll/typing/dismissal NOT summed)")
    ax.set_title("per-service dots + family median/IQR", fontsize=10)
    _stamp(fig, df, "4. activation depth",
           f"observed={len(obs)}/{len(df)}" if len(df) else "")
    return _save(fig, "fig4_activation_depth.png")


def fig5_label_divergence(df):
    fig, axes = plt.subplots(1, 3, figsize=(15, 4.3))
    if len(df) == 0:
        for a in axes: _nodata(a)
    else:
        rel = Counter(str(v) for v in df["label_relation"])
        order = [r for r in C.LABEL_RELATIONS if r in rel] + \
                [r for r in rel if r not in C.LABEL_RELATIONS]
        axes[0].bar(order, [rel[r] for r in order], color="indianred")
        axes[0].tick_params(axis="x", rotation=40, labelsize=7)
        vl = Counter(str(v) for v in df["visible_label"] if not C.is_missing(v))
        ax_ = Counter(str(v) for v in df["accessible_name"] if not C.is_missing(v))
        axes[1].bar(["visible_label", "accessible_name"], [len(vl), len(ax_)], color="slategray")
        axes[1].set_ylabel("distinct vocabulary size")
        fams = sorted(df["family_id"].astype(str).unique())
        div = []
        for f in fams:
            s = df[df["family_id"].astype(str) == f]
            v = {str(x) for x in s["visible_label"] if not C.is_missing(x)}
            div.append(len(v))
        axes[2].bar(fams, div, color="darkkhaki")
        axes[2].set_ylabel("distinct visible labels")
    axes[0].set_title("label_relation  [derived from stored DOM, not live]", fontsize=9)
    axes[1].set_title("vocabulary size (visible vs AX)", fontsize=10)
    axes[2].set_title("family label diversity", fontsize=10)
    both = int(sum(1 for _, r in df.iterrows()
                   if not C.is_missing(r["visible_label"])
                   and not C.is_missing(r["accessible_name"]))) if len(df) else 0
    fig.text(0.5, 0.93,
             "NOT A SITE-LEVEL FINDING (A R104): both-observed rows = %d/%d.  "
             "AX_ONLY count reflects COLLECTION ASYMMETRY (AX capture broke early), not site behaviour."
             % (both, len(df)), ha="center", fontsize=8, color="darkred")
    _stamp(fig, df, "5. visible label / accessible name — observation presence, NOT semantic comparison",
           "both-observed n=%d — too few for a distribution" % both)
    return _save(fig, "fig5_label_divergence.png")


def _norm_edit(a: list, b: list) -> float:
    if not a and not b:
        return 0.0
    prev = list(range(len(b) + 1))
    for i, x in enumerate(a, 1):
        cur = [i]
        for j, y in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (x != y)))
        prev = cur
    return prev[-1] / max(len(a), len(b))


def fig6_sequence_divergence(df):
    """family별 10×10 normalized edit-distance matrix.

    **45 cells 는 descriptive pair cell 이다 — independent n=45 가 아니다.**
    이 문구를 그림 안에 넣으라는 것이 TBX-008 의 명시 요구다.
    """
    fams = sorted(df["family_id"].astype(str).unique()) if len(df) else []
    n = max(1, len(fams))
    fig, axes = plt.subplots(1, n, figsize=(3.5 * n + 1, 4.0))
    if n == 1:
        axes = [axes]
    if not fams:
        _nodata(axes[0], "NO DATA YET")
    else:
        for ax, f in zip(axes, fams):
            s = df[df["family_id"].astype(str) == f]
            seqs = [str(v).split("|") if not C.is_missing(v) else None
                    for v in s["experienced_flow_sequence"]]
            k = len(seqs)
            M = [[float("nan")] * k for _ in range(k)]
            for i in range(k):
                for j in range(k):
                    if seqs[i] is None or seqs[j] is None:
                        continue
                    M[i][j] = _norm_edit(seqs[i], seqs[j])
            im = ax.imshow(M, vmin=0, vmax=1, cmap="magma")
            ax.set_title(f"{f}  ({k}×{k})", fontsize=9)
            ax.set_xticks([]); ax.set_yticks([])
        fig.colorbar(im, ax=axes, fraction=0.02, label="normalized edit distance")
    fig.text(0.5, 0.93,
             "SINGLE OBSERVED FLOW — task_flow is NOT_SEPARABLE_IN_THIS_CENSUS (E supplies one sequence). "
             "This is NOT a task-vs-experienced comparison.",
             ha="center", fontsize=8, color="darkred")
    _stamp(fig, df, "6. experienced flow sequence divergence (single observed flow)",
           "45 cells = descriptive pair cells, NOT independent n=45 (n=10 per family)")
    return _save(fig, "fig6_sequence_divergence.png")


ALL = [fig1_coverage_terminal, fig2_entry_spatial_map, fig3_entry_implementation,
       fig4_activation_depth, fig5_label_divergence, fig6_sequence_divergence]


def render_all(df) -> dict:
    out = {}
    for fn in ALL:
        out[fn.__name__] = fn(df)
    return out


if __name__ == "__main__":
    import sys
    mode = sys.argv[1] if len(sys.argv) > 1 else "empty"
    df = C.empty_mart() if mode == "empty" else C.synthetic_fixture()
    print(json.dumps({"mode": mode, "data_state": C.data_state(df),
                      "figures": render_all(df)}, ensure_ascii=False, indent=1))
