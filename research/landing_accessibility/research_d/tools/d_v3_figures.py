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
        bottom = [0] * len(fams)
        for r in reasons:
            vals = [int(((df["family_id"].astype(str) == f) &
                         (df["terminal_reason"].astype(str) == r)).sum()) for f in fams]
            axes[0].bar(fams, vals, bottom=bottom, label=r)
            bottom = [b + v for b, v in zip(bottom, vals)]
        axes[0].set_ylabel("targets"); axes[0].set_ylim(0, C.N_PER_FAMILY)
        axes[0].legend(fontsize=7, ncol=2)
        for i, f in enumerate(fams):
            k = den["by_family"].get(f, {}).get("completed", 0)
            axes[0].text(i, C.N_PER_FAMILY * 0.96, f"{k}/{C.N_PER_FAMILY}",
                         ha="center", fontsize=8)
        o = den["overall"]
        labels = ["attempted", "evidence_adequate", "completed", "failed"]
        axes[1].barh(labels, [o[k] for k in labels], color="steelblue")
        for i, k in enumerate(labels):
            axes[1].text(o[k] + 0.4, i, f"{o[k]}/{C.N_TOTAL}", va="center", fontsize=9)
        axes[1].set_xlim(0, C.N_TOTAL * 1.15)
    axes[0].set_title("terminal_reason by family (k/10)", fontsize=10)
    axes[1].set_title("denominators — overall (k/50)", fontsize=10)
    _stamp(fig, df, "1. coverage / terminal_reason")
    return _save(fig, "fig1_coverage_terminal.png")


def fig2_entry_spatial_map(df):
    fig, axes = plt.subplots(1, 2, figsize=(12.5, 5))
    obs = df[[not C.is_missing(v) for v in df["entry_x_norm"]]] if len(df) else df
    if len(obs) == 0:
        _nodata(axes[0], "NO OBSERVED COORDINATES")
        _nodata(axes[1])
    else:
        for f in sorted(obs["family_id"].astype(str).unique()):
            s = obs[obs["family_id"].astype(str) == f]
            axes[0].scatter([float(x) for x in s["entry_x_norm"]],
                            [float(y) for y in s["entry_y_norm"]], label=f, s=42, alpha=.8)
        axes[0].set_xlim(0, 1); axes[0].set_ylim(1, 0)
        axes[0].set_xlabel("entry_x_norm"); axes[0].set_ylabel("entry_y_norm (0=top)")
        axes[0].legend(fontsize=8)
        z = Counter(str(v) for v in obs["entry_zone"] if not C.is_missing(v))
        axes[1].bar(list(z.keys()), list(z.values()), color="darkseagreen")
        axes[1].set_ylabel("targets")
    axes[0].set_title("entry point position", fontsize=10)
    axes[1].set_title("entry_zone distribution", fontsize=10)
    _stamp(fig, df, "2. entry spatial map",
           f"observed_coords={len(obs)}/{len(df)}" if len(df) else "")
    return _save(fig, "fig2_entry_spatial_map.png")


def fig3_entry_implementation(df):
    cols = ["entry_control_type", "menu_dependency", "nav_container_type",
            "reveal_direction", "auth_gate_stage"]
    fig, axes = plt.subplots(1, len(cols), figsize=(17, 3.8))
    for ax, c in zip(axes, cols):
        vals = Counter(str(v) for v in df[c] if not C.is_missing(v)) if len(df) else Counter()
        if not vals:
            _nodata(ax, "NO DATA")
        else:
            ax.bar(list(vals.keys()), list(vals.values()), color="cornflowerblue")
            ax.tick_params(axis="x", rotation=45, labelsize=7)
        ax.set_title(c, fontsize=9)
    _stamp(fig, df, "3. entry implementation")
    return _save(fig, "fig3_entry_implementation.png")


def fig4_activation_depth(df):
    """scroll / typing / forced dismissal 을 **합산하지 않는다** (TBX-006)."""
    fig, ax = plt.subplots(figsize=(11, 4.6))
    obs = df[[not C.is_missing(v) for v in df["activation_depth"]]] if len(df) else df
    if len(obs) == 0:
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
    axes[0].set_title("label_relation", fontsize=10)
    axes[1].set_title("vocabulary size (visible vs AX)", fontsize=10)
    axes[2].set_title("family label diversity", fontsize=10)
    _stamp(fig, df, "5. visible label ↔ accessible name divergence")
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
    _stamp(fig, df, "6. experienced flow sequence divergence",
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
