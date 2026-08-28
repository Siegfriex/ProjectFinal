"""FINAL PRESENTATION MEASUREMENT EDA — read-only.

**새 연구질문을 만들지 않는다.** canonical mart 의 관측가능성·provenance 와
verified n=8 의 variation/convergence 를 기술통계로 정리한다.

규율:
  · 값이 non-null 이라고 OBSERVED 로 세지 않는다 (D-DEF-41)
  · AX 는 browser-computed 0/50. visible 복사본을 OBSERVED AX 로 세지 않는다
  · nav_container 는 E direct 와 B posthoc 을 분리한다
  · percentage 는 frozen frame 의 기술값이지 population estimate 가 아니다
  · 결측을 하나의 NA 로 합치지 않는다
"""
from __future__ import annotations

import hashlib
import io
import json
import subprocess
from collections import Counter
from pathlib import Path

RD = Path("/home/sieg/projects-wsl/ProjectFinal/.agent_worktrees/claude_d_research"
          "/research/landing_accessibility/research_d")
OUT = RD / "presentation_eda"
AUTH_SHA = "574e32880c2cd81c6b2e85c31306f768a55e274c"
BUNDLE = "research/landing_accessibility/control/v3/REPORT_BUNDLE_v1"
EXPECTED_MART = "5290e0c306ff7a11375f8da1ee0439e4a424559f18e7a6a662588e46be8f5caf"
WORKTREE = RD.parents[2]

N_TOTAL = 50

# [A TBX-022] acquisition state 3집단. FORBIDDEN 은 measurement 쪽이다.
GROUPS = {
    "USABLE_PATH_EVIDENCE": ["ENDPOINT_REACHED", "AUTH_GATE"],
    # SITE 라벨 철회 [A R163] — 옛 키는 `SITE_SIDE_ROUTE_NOT_OBSERVED`
    "ROUTE_NOT_REACHED_BY_COLLECTOR": ["NO_SAFE_ROUTE_SITE"],
    "MEASUREMENT_COLLECTOR_LIMITED": [
        "COLLECTOR_ZERO_CANDIDATE", "TIMEOUT",
        "NO_SAFE_ROUTE_UNVERIFIED_CANDIDATE_COUNT", "FORBIDDEN_ACTION_BOUNDARY"],
}

SENTINELS = ("NOT_OBSERVED", "UNDETERMINED", "NA_NUMERIC_UNOBSERVED",
             "NOT_OBSERVABLE_FROM_STATIC_DOM", "NOT_SEPARABLE_IN_THIS_CENSUS",
             "E_RAW_NOT_YET_RECEIVED", "NOT_YET_RECEIVED")


def _git_show(path: str) -> bytes:
    r = subprocess.run(["git", "-C", str(WORKTREE), "show", f"{AUTH_SHA}:{BUNDLE}/{path}"],
                       capture_output=True)
    if r.returncode != 0:
        raise RuntimeError(f"read failed: {path}")
    return r.stdout


def load():
    """바이트를 한 번 읽고 sha 를 고정한 뒤 표를 만든다 (A R79)."""
    import pandas as pd
    raw = _git_show("data/CANONICAL_MART_50.csv")
    sha = hashlib.sha256(raw).hexdigest()
    df = pd.read_csv(io.BytesIO(raw), dtype=str, keep_default_na=False)
    ev = _git_show("data/EVIDENCE_MANIFEST.jsonl")
    gs = _git_show("data/GEOMETRY_SUPPLEMENT_E.jsonl")
    pin = {"mart_path": f"{BUNDLE}/data/CANONICAL_MART_50.csv",
           "mart_sha256": sha, "mart_bytes": len(raw),
           "matches_declared": sha == EXPECTED_MART,
           "authority_head": AUTH_SHA,
           "evidence_manifest_sha256": hashlib.sha256(ev).hexdigest(),
           "geometry_supplement_sha256": hashlib.sha256(gs).hexdigest()}
    return df, pin, ev.decode("utf-8"), gs.decode("utf-8")


def is_sentinel(v) -> bool:
    t = "" if v is None else str(v).strip()
    return t == "" or t in SENTINELS


def numeric_ok(v) -> bool:
    if is_sentinel(v):
        return False
    try:
        float(str(v).strip()); return True
    except ValueError:
        return False


# ── TASK A ────────────────────────────────────────────────────────────────
def task_a(df) -> dict:
    tr = Counter(str(v).strip() for v in df["terminal_reason"])
    states, seen = {}, set()
    for k, n in sorted(tr.items(), key=lambda x: -x[1]):
        states[k] = {"numerator": int(n), "denominator": N_TOTAL,
                     "percentage_of_50": round(100 * n / N_TOTAL, 1),
                     "source_field": "terminal_reason",
                     "provenance_status": "ASSURED_RECALCULATED"}
        seen.add(k)
    groups = {}
    for g, keys in GROUPS.items():
        n = sum(int(tr.get(k, 0)) for k in keys)
        groups[g] = {"numerator": n, "denominator": N_TOTAL,
                     "percentage_of_50": round(100 * n / N_TOTAL, 1),
                     "members": {k: int(tr.get(k, 0)) for k in keys},
                     "source_field": "terminal_reason",
                     "provenance_status": "ASSURED_RECALCULATED"}
    unmapped = {k: v for k, v in tr.items()
                if k not in {x for ks in GROUPS.values() for x in ks}}
    return {"total_target": {"numerator": int(len(df)), "denominator": N_TOTAL,
                             "source_field": "row count",
                             "provenance_status": "ASSURED_RECALCULATED"},
            "acquisition_state": states,
            "groups": groups,
            "unmapped_terminal_values": unmapped,
            "group_sum_check": {"sum": sum(g["numerator"] for g in groups.values()),
                                "equals_50": sum(g["numerator"] for g in groups.values()) == N_TOTAL},
            "percentage_note": ("percentage 는 frozen frame 50 에 대한 **기술값**이다. "
                                "population estimate 가 아니며 accessibility success rate 로 읽지 않는다")}


# ── TASK B ────────────────────────────────────────────────────────────────
# provenance 상태. **값이 non-null 이라고 OBSERVED 로 세지 않는다.**
PROV_CLASSES = ("OBSERVED_DIRECT", "OBSERVED_SUPPLEMENT", "DERIVED_POSTHOC",
                "NOT_OBSERVED", "METHOD_FAILURE", "SENTINEL", "AMBIGUOUS")


def _obs_prov_class(row, col):
    """entry_* 계열 — `entry_observation_provenance` 로 갈린다."""
    v = row[col]
    p = str(row.get("entry_observation_provenance", "")).strip()
    if is_sentinel(v):
        if p == "NO_DOM_CAPTURED_BY_E":
            return "METHOD_FAILURE"
        if p.startswith("POSTHOC_AMBIGUOUS"):
            return "AMBIGUOUS"
        return "NOT_OBSERVED"
    if str(v).strip().startswith("AMBIGUOUS"):
        return "AMBIGUOUS"
    if p in ("ANCHOR_ON_E_LABEL", "B_LEXICON_MATCHER"):
        return "DERIVED_POSTHOC"       # E 현장관측이 아니라 저장 DOM 사후 파생 (A R93)
    if p == "E_LIVE_SCOUT":
        return "OBSERVED_DIRECT"
    return "DERIVED_POSTHOC"


def _geom_prov_class(row, col):
    """좌표/zone — `entry_geometry_provenance` 로 갈린다."""
    v = row[col]
    g = str(row.get("entry_geometry_provenance", "")).strip()
    if g == "E_R3_SUPPLEMENT" and not is_sentinel(v):
        return "OBSERVED_SUPPLEMENT"   # E 가 실제 클릭한 8건의 geometry
    if g == "E_SUPPLEMENT_NO_CANDIDATE":
        return "NOT_OBSERVED"          # 후보가 없어 '위치' 라는 것이 존재하지 않는다
    return "SENTINEL" if is_sentinel(v) else "OBSERVED_SUPPLEMENT"


def _ax_class(row, col):
    """AX 계열 — **browser-computed AX 는 0/50 이다.**

    `accessible_name` 이 채워져 있어도 `label_relation ==
    AX_NOT_INDEPENDENTLY_OBSERVED` 면 visible text 복사다. OBSERVED 로 세지 않는다.
    """
    v = row[col]
    rel = str(row.get("label_relation", "")).strip()
    if is_sentinel(v):
        return "METHOD_FAILURE"        # AX 캡처가 전 상태에서 실패했다(오류 스텁 107/107)
    if rel == "AX_NOT_INDEPENDENTLY_OBSERVED":
        return "DERIVED_POSTHOC"       # visible text 복사 — AX 관측이 아니다
    return "DERIVED_POSTHOC"


def _plain_class(row, col):
    v = row[col]
    if is_sentinel(v):
        return "NOT_OBSERVED"
    if str(v).strip().startswith("AMBIGUOUS"):
        return "AMBIGUOUS"
    return "DERIVED_POSTHOC"


def _seq_class(row, col):
    v = str(row[col]).strip()
    if is_sentinel(v) or v in ("[]", ""):
        return "NOT_OBSERVED"
    if v.startswith("AMBIGUOUS"):
        return "AMBIGUOUS"
    return "OBSERVED_DIRECT"


def _label_rel_class(row, col):
    """`label_relation` 은 관측이 아니라 **규칙의 산물**이다 (A R104/R120)."""
    return "DERIVED_POSTHOC"


def _seq_empty(row) -> bool:
    """관측된 조작 스텝이 없는가. `[]` 는 빈 리스트이지 결측 토큰이 아니라 sentinel 검사에 안 걸린다."""
    s = str(row.get("task_flow_sequence", "")).strip()
    e = str(row.get("experienced_flow_sequence", "")).strip()
    return s in ("[]", "") and e in ("[]", "")


def _direct_class(row, col):
    """E 가 직접 산출한 축 — depth·menu·auth·evidence.

    [발표 EDA 발견] `activation_depth == 0` 22건은 **전부 시퀀스가 비어 있고**
    terminal 이 미도달 계열이다(COLLECTOR_ZERO 17 · FORBIDDEN 1 · TIMEOUT 2 ·
    UNVERIFIED 2). 그 0 은 "깊이가 0 이었다" 가 아니라 **"관측할 시퀀스가 없었다"** 다.
    non-null 이라고 OBSERVED 로 세면 평균 depth 가 절반으로 내려간다 — D-DEF-41 계열.
    """
    v = row[col]
    if is_sentinel(v):
        return "NOT_OBSERVED"
    if col in ("activation_depth", "menu_dependency") and _seq_empty(row):
        return "NOT_OBSERVED"          # 시퀀스가 없으면 깊이·메뉴의존은 관측되지 않았다
    return "OBSERVED_DIRECT"


VAR_SPEC = [
    ("task_path_evidence", "evidence_hash", _direct_class,
     "usable path evidence 는 terminal_reason 으로 별도 집계한다"),
    ("entry_x_norm", "entry_x_norm", _geom_prov_class, ""),
    ("entry_y_norm", "entry_y_norm", _geom_prov_class, ""),
    ("entry_zone", "entry_zone", _geom_prov_class, ""),
    ("entry_control_type", "entry_control_type", _obs_prov_class, ""),
    ("task_flow_sequence", "task_flow_sequence", _seq_class,
     "빈 리스트 `[]` 22건은 결측 토큰이 아니지만 **관측된 스텝이 없다**. "
     "task 와 experienced 는 이 census 에서 분리되지 않았다"),
    ("activation_depth", "activation_depth", _direct_class, ""),
    ("menu_dependency", "menu_dependency", _direct_class, ""),
    ("nav_container_type", "nav_container_type", _obs_prov_class,
     "**E direct 0 · B 사후파생.** 이 축은 E 가 산출한 적이 없다"),
    ("visible_label_text", "visible_label", _obs_prov_class, ""),
    ("accessible_name", "accessible_name", _ax_class,
     "**browser-computed AX 0/50.** 채워진 값은 visible text 복사다"),
    ("label_relation", "label_relation", _label_rel_class,
     "관측이 아니라 규칙의 산물이다"),
    ("auth_gate_stage", "auth_gate_stage", _direct_class, ""),
    ("task_control_occlusion", "task_control_occlusion", _plain_class,
     "**UNWIRED** — 50/50 전건 sentinel"),
    ("reveal_direction", "reveal_direction", _plain_class,
     "**UNWIRED** — 50/50 전건 sentinel"),
]


def task_b(df) -> dict:
    rows = {}
    for name, col, fn, note in VAR_SPEC:
        c = Counter()
        for _, r in df.iterrows():
            c[fn(r, col)] += 1
        observed = c["OBSERVED_DIRECT"] + c["OBSERVED_SUPPLEMENT"]
        rows[name] = {
            "source_field": col,
            "counts": {k: int(c.get(k, 0)) for k in PROV_CLASSES if c.get(k)},
            "sum_check": int(sum(c.values())),
            "observed_direct_or_supplement": int(observed),
            "denominator": N_TOTAL,
            "assurance_class": ("NOT_OBSERVABLE"
                                if observed == 0 and c["DERIVED_POSTHOC"] == 0
                                else "DESCRIPTIVE_VERIFIED"),
            "note": note}
    return rows


# ── TASK C ────────────────────────────────────────────────────────────────
def verified_cases(df):
    """A/C 가 usable evidence 로 확인한 8 target (ENDPOINT_REACHED 6 + AUTH_GATE 2)."""
    keys = set(GROUPS["USABLE_PATH_EVIDENCE"])
    return [r for _, r in df.iterrows() if str(r["terminal_reason"]).strip() in keys]


def task_c(df, ev_text) -> dict:
    cs = verified_cases(df)
    ids = [str(r["target_id"]) for r in cs]
    # pre-R3 확인: EVIDENCE_MANIFEST 에 R3 이전 run 줄이 있는가
    pre = {t: 0 for t in ids}
    for line in ev_text.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            j = json.loads(line)
        except Exception:
            continue
        t = str(j.get("target_id"))
        run = str(j.get("scout_run_id") or j.get("run_id") or "")
        if t in pre and "R3" not in run:
            pre[t] += 1

    def freq(col):
        return dict(Counter(str(r[col]).strip() for r in cs))

    return {"n": len(cs), "target_ids": ids,
            "pre_R3_usable_evidence": {"per_target": pre,
                                       "all_present": all(v > 0 for v in pre.values()),
                                       "assurance_class": "ASSURED_RECALCULATED"},
            "entry_zone": {"counts": freq("entry_zone"),
                           "unique_over_n": f"{len(freq('entry_zone'))}/{len(cs)}"},
            "entry_control_type": {"counts": freq("entry_control_type"),
                                   "unique_over_n": f"{len(freq('entry_control_type'))}/{len(cs)}"},
            "experienced_flow_sequence": {"counts": freq("experienced_flow_sequence"),
                                          "unique_signatures_over_n":
                                              f"{len(freq('experienced_flow_sequence'))}/{len(cs)}"},
            "activation_depth": {"counts": freq("activation_depth"),
                                 "unique_over_n": f"{len(freq('activation_depth'))}/{len(cs)}"},
            "menu_dependency": {"counts": freq("menu_dependency")},
            "nav_container_type_excluded":
                "Claim 2 와 panel 에서 제외한다 — E 산출 0 (A 정정)",
            "assurance_class": "DESCRIPTIVE_VERIFIED",
            "frame": "selected case series. random sample 이 아니다"}


# ── TASK D ────────────────────────────────────────────────────────────────
def _diversity(counts: dict) -> dict:
    import math
    n = sum(counts.values())
    if n == 0:
        return {"shannon": None, "shannon_normalized": None, "simpson": None}
    ps = [v / n for v in counts.values()]
    h = -sum(p * math.log(p) for p in ps if p > 0)
    k = len(counts)
    return {"shannon": round(h, 4),
            "shannon_normalized": round(h / math.log(k), 4) if k > 1 else 0.0,
            "simpson_diversity": round(1 - sum(p * p for p in ps), 4),
            "k_categories": k, "n": n}


def task_d(df, gs_text) -> dict:
    cs = verified_cases(df)
    zc = Counter(str(r["entry_zone"]).strip() for r in cs)
    cc = Counter(str(r["entry_control_type"]).strip() for r in cs)
    out = {"appendix_only": True, "assurance_class": "EXPLORATORY",
           "no_inference": "p-value 를 만들지 않는다. uniform null 을 세우지 않는다. population inference 를 하지 않는다",
           "entry_zone": _diversity(dict(zc)),
           "entry_control_type": _diversity(dict(cc))}
    xs = [(float(r["entry_x_norm"]), float(r["entry_y_norm"])) for r in cs
          if numeric_ok(r["entry_x_norm"]) and numeric_ok(r["entry_y_norm"])]
    if len(xs) == len(cs) and len(xs) >= 2:
        import math, statistics
        d = [math.dist(xs[i], xs[j]) / math.sqrt(2)
             for i in range(len(xs)) for j in range(i + 1, len(xs))]
        d.sort()
        q1 = d[len(d) // 4]; q3 = d[(3 * len(d)) // 4]
        out["pairwise_normalized_euclidean"] = {
            "n_pairs": len(d), "median": round(statistics.median(d), 4),
            "IQR": [round(q1, 4), round(q3, 4)],
            "min": round(d[0], 4), "max": round(d[-1], 4),
            "assurance_class": "NOT_ASSURED",
            "limitation": "GEOMETRY_SUPPLEMENT 의 evidence_hash 결속이 NOT_ASSURED 다. "
                          "descriptive pair cell 이며 independent n 이 아니다"}
    else:
        out["pairwise_normalized_euclidean"] = {
            "state": "NOT_COMPUTED", "reason": f"좌표 유효 {len(xs)}/{len(cs)}"}
    return out


# ── TASK F ────────────────────────────────────────────────────────────────
MECH = {
    "COLLECTOR_ZERO_CANDIDATE": "COLLECTOR_LIMITATION",
    "NO_SAFE_ROUTE_SITE": "SITE_ROUTE_NOT_OBSERVED",
    "NO_SAFE_ROUTE_UNVERIFIED_CANDIDATE_COUNT": "UNKNOWN",
    "TIMEOUT": "TIMEOUT",
    "FORBIDDEN_ACTION_BOUNDARY": "SAFETY_BOUNDARY",
    "ENDPOINT_REACHED": "(not missing)",
    "AUTH_GATE": "(not missing)",
}


def task_f(df) -> dict:
    by = Counter()
    for _, r in df.iterrows():
        by[MECH.get(str(r["terminal_reason"]).strip(), "UNKNOWN")] += 1
    ax = int(sum(1 for _, r in df.iterrows() if is_sentinel(r["accessible_name"])))
    unwired = {c: int(sum(1 for _, r in df.iterrows() if is_sentinel(r[c])))
               for c in ("reveal_direction", "task_control_occlusion")}
    # 검증 대상 문장
    supported = (by["COLLECTOR_LIMITATION"] > 0 and by["SITE_ROUTE_NOT_OBSERVED"] > 0)
    return {"mechanism_counts": dict(by),
            "api_method_failure": {"accessible_name_sentinel": ax,
                                   "cause": "AX 캡처가 전 상태에서 실패(오류 스텁 107/107). 원자료 없음",
                                   "class": "API_METHOD_FAILURE"},
            "unwired_columns": unwired,
            "statement_under_test":
                "이번 데이터의 결측은 MCAR 라고 볼 근거가 없으며, 수집과정과 과업구조에 "
                "연결된 process-induced informative missingness 다",
            "verdict": "SUPPORTED_AS_WEAKER_FORM" if supported else "NOT_SUPPORTED",
            "supported_form":
                "결측이 원인별로 갈리고(COLLECTOR_LIMITATION %d · SITE_ROUTE_NOT_OBSERVED %d · "
                "TIMEOUT %d · SAFETY_BOUNDARY %d), AX 축은 전건이 API 실패라 **결측이 무작위로 "
                "흩어져 있지 않다**. 다만 MCAR 를 **검정으로 기각한 것이 아니라** 원인 라벨이 "
                "구조적으로 갈린다는 기술적 관찰이다 — '근거가 없다' 까지가 이 데이터가 말하는 것이고 "
                "'informative 임을 보였다' 로 쓰지 않는다"
                % (by["COLLECTOR_LIMITATION"], by["SITE_ROUTE_NOT_OBSERVED"],
                   by["TIMEOUT"], by["SAFETY_BOUNDARY"]),
            "no_imputation": "imputation 하지 않았다",
            "assurance_class": "DESCRIPTIVE_VERIFIED"}


if __name__ == "__main__":
    df, pin, ev, gs = load()
    print(json.dumps({"pin": pin, "A": task_a(df), "B": task_b(df),
                      "C": task_c(df, ev), "D": task_d(df, gs), "F": task_f(df)},
                     ensure_ascii=False, indent=1))


# ── FIGURES ───────────────────────────────────────────────────────────────
def _mpl():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    for f in ("NanumGothic", "NanumBarunGothic", "Noto Sans CJK KR"):
        if any(f == x.name for x in matplotlib.font_manager.fontManager.ttflist):
            plt.rcParams["font.family"] = f
            break
    plt.rcParams["axes.unicode_minus"] = False
    return plt


CLASS_COLOR = {"OBSERVED_DIRECT": "#1b6ca8", "OBSERVED_SUPPLEMENT": "#4a9fd8",
               "DERIVED_POSTHOC": "#f0a04b", "AMBIGUOUS": "#c7b198",
               "METHOD_FAILURE": "#b23a48", "NOT_OBSERVED": "#d9d9d9",
               "SENTINEL": "#bdbdbd"}


def fig5_observability(b: dict) -> str:
    plt = _mpl()
    order = [n for n, _, _, _ in VAR_SPEC][::-1]
    fig, ax = plt.subplots(figsize=(11.5, 6.4))
    for i, name in enumerate(order):
        left = 0
        for cls in ("OBSERVED_DIRECT", "OBSERVED_SUPPLEMENT", "DERIVED_POSTHOC",
                    "AMBIGUOUS", "METHOD_FAILURE", "NOT_OBSERVED", "SENTINEL"):
            n = b[name]["counts"].get(cls, 0)
            if not n:
                continue
            ax.barh([i], [n], left=left, color=CLASS_COLOR[cls], edgecolor="white",
                    label=cls if i == len(order) - 1 else None)
            left += n
        obs = b[name]["observed_direct_or_supplement"]
        ax.text(N_TOTAL + 0.6, i, f"관측 {obs}/50", va="center", fontsize=7.5,
                color=("#1b6ca8" if obs else "#b23a48"))
    ax.set_yticks(range(len(order))); ax.set_yticklabels(order, fontsize=8)
    ax.set_xlim(0, N_TOTAL + 7); ax.set_xlabel("targets (frozen denominator = 50)")
    ax.set_title("변수별 관측가능성 — 어떤 변수가 얼마나 측정됐는가", fontsize=13)
    handles, labels = ax.get_legend_handles_labels()
    ax.legend(handles, labels, fontsize=7, ncol=4, loc="lower right")
    fig.text(0.5, 0.005,
             "이 그림은 **측정이 얼마나 됐는가**이지 사이트가 얼마나 나쁜가가 아니다.   "
             "값이 채워져 있어도 관측이 아니면 OBSERVED로 세지 않았다 "
             "(accessible_name: browser-computed AX 0/50 — 채워진 값은 visible text 복사).",
             ha="center", fontsize=7.5, color="darkred")
    OUT.mkdir(parents=True, exist_ok=True)
    p = OUT / "FIG5_OBSERVABILITY.png"
    fig.savefig(p, dpi=140, bbox_inches="tight"); plt.close(fig)
    return str(p)


def fig6_variation_convergence(c: dict) -> str:
    plt = _mpl()
    fig, axes = plt.subplots(1, 2, figsize=(12.5, 5.2))
    zc = c["entry_zone"]["counts"]; cc = c["entry_control_type"]["counts"]
    ax = axes[0]
    ys = list(zc) + [""] + list(cc)
    vs = list(zc.values()) + [0] + list(cc.values())
    cols = ["#1b6ca8"] * len(zc) + ["white"] + ["#4a9fd8"] * len(cc)
    ax.barh(range(len(ys))[::-1], vs, color=cols)
    ax.set_yticks(range(len(ys))[::-1]); ax.set_yticklabels(ys, fontsize=8)
    ax.set_xlim(0, 8.6); ax.set_xlabel("cases (n=8)")
    ax.set_title("달랐던 것", fontsize=13, color="#1b6ca8")
    ax.text(0.98, 0.06, f"entry_zone {len(zc)} categories / 8\n"
                        f"entry_control_type {len(cc)} categories / 8",
            transform=ax.transAxes, ha="right", fontsize=8.5)
    ax = axes[1]
    rows = [("task_flow_sequence", "SELECT_FUNCTION", "8/8"),
            ("activation_depth", "1", "8/8"),
            ("menu_dependency", "False", "8/8")]
    for i, (k, v, n) in enumerate(rows):
        ax.barh([2 - i], [8], color="#6a994e", edgecolor="white")
        ax.text(4, 2 - i, f"{k} = {v}   ({n})", ha="center", va="center",
                color="white", fontsize=10, fontweight="bold")
    ax.set_xlim(0, 8.6); ax.set_ylim(-0.6, 2.6)
    ax.set_yticks([]); ax.set_xlabel("cases (n=8)")
    ax.set_title("같았던 것", fontsize=13, color="#6a994e")
    fig.suptitle("관측된 8개 사례에서는 절차보다 진입 위치와 표현 형태가 달랐다",
                 fontsize=14, y=1.02)
    fig.text(0.5, -0.03,
             "selected case series n=8. 수집기가 깊은 경로를 관측하지 못한 선택편향 가능성. "
             "전체 서비스 분포로 일반화하지 않음.   navigation container는 이 panel에서 제외했다(E 산출 0).",
             ha="center", fontsize=8, color="darkred")
    OUT.mkdir(parents=True, exist_ok=True)
    p = OUT / "FIG6_VARIATION_VS_CONVERGENCE.png"
    fig.savefig(p, dpi=140, bbox_inches="tight"); plt.close(fig)
    return str(p)
