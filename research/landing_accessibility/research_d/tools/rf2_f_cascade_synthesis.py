"""D-RF2-F — Hybrid cascade candidate synthesis.

목적
----
`RQ-D-RF-002` 의 child A~E 를 **종합**해 2~3개의 candidate measurement architecture 를
제시한다. production 모델을 만드는 것이 아니고, best model 을 고르는 것도 아니다.
산출은 `RECOMMENDED_EXPERIMENTAL_CANDIDATES` 까지이며, 각 후보는 **순위 없이 조건과 대가**를
병기한다.

절대 프레이밍 — D-FACT-01
-------------------------
이 56 target 표본에서 `prior_archetype` 과 `prior_business_domain` 은 **완전 전단사**다
(7↔7, MI = H = 2.311 bits, 정규화 MI = 1.000, 56/56).
따라서 A~E 가 보고한 모든 `prior_agreement` 는 **"업종 배정 재현율"** 이지 대표기능 정확도가
아니다. 이 코드는 어떤 지표도 accuracy 로 부르지 않는다.
근거: `results/D_FACT_01_prior_domain_bijection.md`.

방화벽
------
holdout label · `LABEL_SPLIT_FROZEN*` · `HOLDOUT_FOR_C*` · `RAW_L1~L4*` · `PACKET_L*` ·
`*_OVERLAP*` · `PRECEDENCE_CONTESTED*` · `CALIBRATION_FOR_B*` · `**/control/**` ·
B/C 의 target-level holdout error report — **하나도 열지 않았다.**
입력은 아래 INPUTS 목록이 전부다. 네트워크 없음. gold label 생성 없음.
A~E 의 산출물을 수정하지 않는다 (읽기 전용). production threshold 를 선언하지 않는다.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import itertools
import json
import math
import statistics as st
import sys
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

matplotlib.rcParams["font.family"] = ["DejaVu Sans"]
matplotlib.rcParams["axes.unicode_minus"] = False

RD = Path("/home/sieg/projects-wsl/ProjectFinal/.agent_worktrees/claude_d_research/"
          "research/landing_accessibility/research_d")
RES = RD / "results"
FIG = RD / "figures"
KST = timezone(timedelta(hours=9))
SEED = 20260827
RNG = np.random.default_rng(SEED)

CHILD_ID = "D-RF2-F"
RQ_ID = "RQ-D-RF-002"
HYP = "H-RF2-F-CASCADE-SYNTHESIS"
VERSION = "RF2F_SYNTHESIS_v1"
PARENT_RUN = "ae754858ba3a4be391e5f811640d3fd8"

ARCHETYPES = ["QUERY", "CONTENT_OPEN", "ITEM_DETAIL", "PLACE_LOOKUP",
              "COMMUNICATION_ENTRY", "FINANCIAL_ACTION_ENTRY", "UTILITY_ENTRY"]

# E 의 taxonomy family. E 의 결론 — 표면부재와 관측손상을 같은 leaf 로 묶지 말 것.
SURFACE_ABSENT = {"T05_GENERIC_BRAND_LANDING", "T06_APP_INSTALL_SURFACE",
                  "T07_REPRESENTATIVE_SURFACE_ABSENT"}
CAPTURE_DEFECT = {"T09_CLIENT_RENDER_SPARSE", "T10A_TEXT_ENCODING_CORRUPTION",
                  "T10B_TEXT_CAP_TRUNCATION", "T11_OVERLAY_OBSTRUCTED",
                  "T12_DEGENERATE_OR_DUPLICATE_CAPTURE"}
DEFINITION_AMBIG = {"T02_WEAK_ONE_SIDED_EVIDENCE", "T03_MULTI_STRONG_CANDIDATE",
                    "T04_SHARED_LIST_SIGNAL"}
PRIOR_CONFLICT = {"T13_PRIOR_CONTRADICTS_STRUCTURE"}

INPUTS = [
    "D_OBSERVATION_TABLE_v2.csv", "D_TEXT_CORPUS_v2.csv",
    "RF2_A_rule_firing.json", "RF2_B_feature_discriminability.json",
    "RF2_C_field_ablation.json", "RF2_D_hierarchical.json",
    "RF2_E_abstention_taxonomy.json",
]


def sha256_file(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def wilson(k: int, n: int, z: float = 1.96) -> list[float]:
    if n == 0:
        return [float("nan"), float("nan")]
    p = k / n
    d = 1 + z * z / n
    c = p + z * z / (2 * n)
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return [round((c - h) / d, 4), round((c + h) / d, 4)]


def phi_coef(x, y) -> float:
    x = np.asarray(x, float)
    y = np.asarray(y, float)
    if x.std() == 0 or y.std() == 0:
        return float("nan")
    return float(np.corrcoef(x, y)[0, 1])


def phi_perm_p(x, y, b: int = 20000) -> float:
    """라벨(y)만 셔플하는 permutation null. x 의 주변분포는 보존된다."""
    obsv = abs(phi_coef(x, y))
    if math.isnan(obsv):
        return float("nan")
    y = np.asarray(y, float)
    cnt = 0
    for _ in range(b):
        if abs(phi_coef(x, RNG.permutation(y))) >= obsv:
            cnt += 1
    return (1 + cnt) / (b + 1)


def cohen_kappa(a: list[bool], b: list[bool]) -> float:
    n = len(a)
    po = sum(int(x == y) for x, y in zip(a, b)) / n
    pa, pb = sum(a) / n, sum(b) / n
    pe = pa * pb + (1 - pa) * (1 - pb)
    return float("nan") if pe >= 1 else round((po - pe) / (1 - pe), 4)


# --------------------------------------------------------------------------- load
def load():
    obs = {r["wtg"]: r for r in csv.DictReader((RES / "D_OBSERVATION_TABLE_v2.csv").open(encoding="utf-8"))
           if r["in_mart"] == "1"}
    cor = {r["wtg"]: r for r in csv.DictReader((RES / "D_TEXT_CORPUS_v2.csv").open(encoding="utf-8"))}
    j = {n: json.loads((RES / f"RF2_{n}_{f}.json").read_text(encoding="utf-8"))
         for n, f in [("A", "rule_firing"), ("B", "feature_discriminability"),
                      ("C", "field_ablation"), ("D", "hierarchical"),
                      ("E", "abstention_taxonomy")]}
    return obs, cor, j


def build_frame(obs, cor, j):
    """target 당 통합 결정 프레임. 각 child 의 **자기 결정규칙**을 그대로 적용한다."""
    A, B, C, D, E = (j["A"], j["B"], j["C"], j["D"], j["E"])
    wtgs = list(obs)
    Drows = {r["wtg"]: r for r in D["rows"]}
    Erows = {r["wtg"]: r for r in E["per_target"]}
    # C 는 target-level 결정규칙이 없다. C 가 per-target 으로 실제 기록한 유일한 것은
    # blob 예측 vs control-surface 예측이 갈린 25건이다.
    C_split = {c["wtg"]: c["type"] for c in C["counterexamples"]}

    rows = []
    for w in wtgs:
        o, t = obs[w], cor[w]
        strong = sorted(a for a, v in A["firing_matrix"][w].items() if v == "STRONG")
        weakplus = sorted(a for a, v in A["firing_matrix"][w].items() if v in ("STRONG", "WEAK"))
        dr, er = Drows[w], Erows[w]
        types = set(er["types"])
        e_mapped = not er["leaf"].startswith(("AMBIG", "UNDET"))
        rows.append({
            "wtg": w,
            "service": o["prior_service"],
            "prior_archetype": o["prior_archetype"],
            "prior_business_domain": o["prior_business_domain"],
            # --- A: SSOT §6 resolver on RF2A_FIRING_v1
            "A_strong": strong, "A_weakplus": weakplus,
            "A_det": len(strong) == 1,
            "A_pred": strong[0] if len(strong) == 1 else None,
            # --- D: flat / hierarchical rule (RF2D_HIER_v1, 독립 lexicon)
            "D_flat_det": dr["flat_outcome"] == "MAPPED", "D_flat_pred": dr["flat_pred"],
            "D_hier_det": dr["hier_rule_outcome"] == "MAPPED", "D_hier_pred": dr["hier_rule_pred"],
            "D_flat_outcome": dr["flat_outcome"],
            "D_flat_sem_pred": dr.get("flat_sem_pred"),
            # --- E: RF001-A rule DT leaf (제3의 독립 lexicon) + taxonomy
            "E_det": e_mapped, "E_pred": er["leaf"] if e_mapped else None,
            "E_n_fired": er["n_fired"], "E_rule_conf": er["rule_conf"],
            "E_sem_top1": er["sem_top1"], "E_sem_margin": er["sem_margin"],
            "E_sem_top1_debranded": er["sem_top1_debranded"],
            "E_sem_margin_debranded": er["sem_margin_debranded"],
            "E_types": sorted(types), "E_primary_type": er["primary_type"],
            "E_resolvability": er["resolvability_bucket"],
            "surface_absent": bool(types & SURFACE_ABSENT),
            "capture_defect": bool(types & CAPTURE_DEFECT),
            "definition_ambiguous": bool(types & DEFINITION_AMBIG),
            "prior_conflict": bool(types & PRIOR_CONFLICT),
            # --- C: per-target 로 남은 유일한 기록 (blob vs control-surface 분기)
            "C_blob_vs_controls": C_split.get(w),
            "C_control_surface_empty": all(t[k].strip() == "" for k in
                                           ("buttons", "aria_labels", "form_labels",
                                            "placeholders", "input_names")),
            "C_aria_empty": t["aria_labels"].strip() == "",
            "blob_tokens": float(t["blob_tokens"]),
            "n_accessible_name_sources": (float(o["n_accessible_name_sources"])
                                          if o["n_accessible_name_sources"] not in ("", "nan") else None),
            "ssot7_components_present": er["type_evidence"].get("ssot7_components_present"),
        })
    for r in rows:
        r["n_rule_impl_determining"] = int(r["A_det"]) + int(r["D_flat_det"]) + int(r["E_det"])
    return rows


# --------------------------------------------------------------- cross-child matrix
def decision_columns(rows, sem_gate):
    """agreement matrix 에 들어가는 target-level 결정 컬럼.

    B 와 C_blob 은 **퇴화 컬럼**이라 kappa 에 넣지 않는다 (아래 degenerate_columns 참조).
    """
    cols = {
        "A_rule": [r["A_det"] for r in rows],
        "D_flat": [r["D_flat_det"] for r in rows],
        "D_hier": [r["D_hier_det"] for r in rows],
        "E_ruleDT": [r["E_det"] for r in rows],
        "E_admissible": [not (r["surface_absent"] or r["capture_defect"]) for r in rows],
        "SEM_margin": [r["E_sem_margin"] >= sem_gate for r in rows],
    }
    return cols


def agreement_matrix(cols, rows):
    names = list(cols)
    out = {"columns": names, "n": len(rows), "pairs": [], "kappa_matrix": {},
           "jaccard_of_determined_sets": {}}
    for a, b in itertools.combinations(names, 2):
        x, y = cols[a], cols[b]
        dd = sum(1 for i in range(len(x)) if x[i] and y[i])
        aa = sum(1 for i in range(len(x)) if not x[i] and not y[i])
        da = sum(1 for i in range(len(x)) if x[i] and not y[i])
        ad = sum(1 for i in range(len(x)) if not x[i] and y[i])
        union = dd + da + ad
        out["pairs"].append({
            "a": a, "b": b, "both_determined": dd, "both_abstain": aa,
            "a_only": da, "b_only": ad,
            "raw_agreement": round((dd + aa) / len(x), 4),
            "cohen_kappa": cohen_kappa(x, y),
            "jaccard_determined": round(dd / union, 4) if union else None,
        })
    for a in names:
        out["kappa_matrix"][a] = {b: (1.0 if a == b else cohen_kappa(cols[a], cols[b])) for b in names}
        sa = {i for i, v in enumerate(cols[a]) if v}
        out["jaccard_of_determined_sets"][a] = {}
        for b in names:
            sb = {i for i, v in enumerate(cols[b]) if v}
            u = len(sa | sb)
            out["jaccard_of_determined_sets"][a][b] = round(len(sa & sb) / u, 4) if u else None
    return out


def multiplicity_analysis(rows):
    """세 독립 rule 구현(A / D_flat / E_ruleDT)이 같은 target 을 확정하는가."""
    mult = Counter(r["n_rule_impl_determining"] for r in rows)
    both = []
    for r in rows:
        preds = {k: v for k, v in (("A", r["A_pred"]), ("D", r["D_flat_pred"]), ("E", r["E_pred"])) if v}
        if len(preds) >= 2:
            both.append({"wtg": r["wtg"], "service": r["service"], "prior_archetype": r["prior_archetype"],
                         "preds": preds, "same_leaf": len(set(preds.values())) == 1})
    union = [r for r in rows if r["n_rule_impl_determining"] > 0]
    triple = [r for r in rows if r["n_rule_impl_determining"] == 3]
    per_impl = {}
    for key, det, pred in (("A_rule", "A_det", "A_pred"), ("D_flat", "D_flat_det", "D_flat_pred"),
                           ("E_ruleDT", "E_det", "E_pred")):
        s = [r for r in rows if r[det]]
        k = sum(1 for r in s if r[pred] == r["prior_archetype"])
        per_impl[key] = {"n_determined": len(s), "n_prior_agree": k,
                         "prior_agreement": round(k / len(s), 4) if s else None,
                         "prior_agreement_wilson95": wilson(k, len(s)),
                         "prior_agreement_of_56": round(k / len(rows), 4)}
    return {
        "note": ("A / D_flat / E_ruleDT 는 SSOT 01 §5·§6 의 **같은 규칙**을 서로 다른 lexicon 으로 "
                 "독립 조작화한 세 구현이다. 아래 수치는 '어느 target 이 결정 가능한가' 가 "
                 "target 의 성질인지 lexicon 의 성질인지를 가른다."),
        "n_implementations_determining_distribution": {str(k): v for k, v in sorted(mult.items())},
        "union_determined_by_at_least_one": len(union),
        "determined_by_all_three": len(triple),
        "determined_by_all_three_detail": [{"wtg": r["wtg"], "service": r["service"],
                                            "prior_archetype": r["prior_archetype"],
                                            "A": r["A_pred"], "D": r["D_flat_pred"], "E": r["E_pred"]}
                                           for r in triple],
        "multi_implementation_cases": both,
        "n_multi_impl_same_leaf": sum(1 for b in both if b["same_leaf"]),
        "per_implementation_prior_agreement": per_impl,
    }


def split_targets(rows, cols):
    """child 간 판정이 갈리는 target 과 그 이유."""
    names = list(cols)
    out = []
    for i, r in enumerate(rows):
        v = {n: cols[n][i] for n in names}
        if len(set(v.values())) == 1:
            continue
        det = [n for n in names if v[n]]
        abst = [n for n in names if not v[n]]
        # 갈림의 이유를 관측 가능한 조건으로 귀속한다.
        why = []
        if r["A_det"] != r["D_flat_det"] or r["A_det"] != r["E_det"]:
            why.append("rule lexicon 조작화 차이 (같은 SSOT §5, 다른 어휘·임계)")
        if r["D_hier_det"] and not r["D_flat_det"]:
            why.append("계층 L1 이 flat 이 못 닫은 것을 닫음 (D-RF2-D §11.1: 2건, 둘 다 prior 불일치)")
        if not r["D_hier_det"] and r["D_flat_det"]:
            why.append("archetype 이 primitive 2개 소속이라 L1 다중후보 (D-RF2-D §11.1)")
        if cols["SEM_margin"][i] and not (r["A_det"] or r["D_flat_det"] or r["E_det"]):
            why.append("semantic margin 은 높은데 어떤 rule 구현도 발화하지 않음")
        if not cols["SEM_margin"][i] and (r["A_det"] or r["D_flat_det"] or r["E_det"]):
            why.append("rule 은 유일 후보를 냈으나 semantic top1-top2 가 붙어 있음")
        if r["surface_absent"]:
            why.append("E: 표면부재 계열 유형 보유 " + str(sorted(set(r["E_types"]) & SURFACE_ABSENT)))
        if r["capture_defect"]:
            why.append("E: 관측손상 계열 유형 보유 " + str(sorted(set(r["E_types"]) & CAPTURE_DEFECT)))
        out.append({"wtg": r["wtg"], "service": r["service"], "prior_archetype": r["prior_archetype"],
                    "determined_by": det, "abstained_by": abst,
                    "n_rule_impl_determining": r["n_rule_impl_determining"],
                    "E_sem_margin": round(r["E_sem_margin"], 5),
                    "reasons": why})
    return out


# ------------------------------------------------------------ cascade vs semantic
def matched_coverage_curves(rows):
    """같은 coverage 에서 rule-first cascade 와 semantic-only 를 나란히 놓는다.

    **prior_agreement 는 업종 배정 재현율이다 (D-FACT-01). 정확도가 아니다.**
    threshold 를 선언하지 않는다 — 곡선만 낸다.
    """
    n = len(rows)
    margins = sorted(r["E_sem_margin"] for r in rows)
    margins_d = sorted(r["E_sem_margin_debranded"] for r in rows)
    rule_mapped = [r for r in rows if r["E_det"]]
    rule_rest = sorted([r for r in rows if not r["E_det"]], key=lambda r: -r["E_sem_margin"])
    curve = []
    for k in range(n, 3, -2):
        t = margins[n - k]
        sem = [r for r in rows if r["E_sem_margin"] >= t]
        a_sem = sum(1 for r in sem if r["E_sem_top1"] == r["prior_archetype"])
        td = margins_d[n - k]
        semd = [r for r in rows if r["E_sem_margin_debranded"] >= td]
        a_semd = sum(1 for r in semd if r["E_sem_top1_debranded"] == r["prior_archetype"])
        sel = rule_mapped + rule_rest[:max(0, k - len(rule_mapped))]
        a_cas = sum(1 for r in sel if (r["E_pred"] or r["E_sem_top1"]) == r["prior_archetype"])
        curve.append({
            "coverage_n": k, "coverage": round(k / n, 4),
            "semantic_only_prior_agreement": round(a_sem / len(sem), 4),
            "semantic_only_wilson95": wilson(a_sem, len(sem)),
            "semantic_only_debranded_prior_agreement": round(a_semd / len(semd), 4),
            "rule_first_cascade_prior_agreement": round(a_cas / len(sel), 4),
            "rule_first_cascade_wilson95": wilson(a_cas, len(sel)),
            "delta_cascade_minus_semantic_only": round(a_cas / len(sel) - a_sem / len(sem), 4),
        })
    # rule 이 실제로 확정한 11건에서 rule 과 semantic 을 짝지어 본다 (McNemar)
    b = sum(1 for r in rule_mapped if r["E_pred"] == r["prior_archetype"]
            and r["E_sem_top1"] != r["prior_archetype"])
    c = sum(1 for r in rule_mapped if r["E_pred"] != r["prior_archetype"]
            and r["E_sem_top1"] == r["prior_archetype"])
    mcn_p = 1.0 if b + c == 0 else round(
        sum(math.comb(b + c, i) for i in range(0, min(b, c) + 1)) * 2 / (2 ** (b + c)), 4)
    return {
        "note": ("모든 prior_agreement 는 D-FACT-01 에 따라 **업종 배정 재현율**이다. "
                 "이 표는 threshold 를 선언하지 않는다. coverage 를 맞춘 대조일 뿐이다."),
        "curve": curve,
        "cascade_never_beats_semantic_only_at_matched_coverage":
            all(c["delta_cascade_minus_semantic_only"] <= 0 for c in curve),
        "paired_on_rule_mapped_11": {
            "n": len(rule_mapped),
            "rule_agrees_with_prior": sum(1 for r in rule_mapped if r["E_pred"] == r["prior_archetype"]),
            "semantic_agrees_with_prior": sum(1 for r in rule_mapped
                                              if r["E_sem_top1"] == r["prior_archetype"]),
            "rule_only_right_b": b, "semantic_only_right_c": c,
            "mcnemar_exact_p_two_sided": mcn_p,
            "reading": ("b=0 은 '규칙이 맞고 semantic 이 틀린 target 이 하나도 없다'는 뜻이다. "
                        "즉 이 표본에서 rule stage 는 semantic 이 이미 되찾는 업종 배정 위에 "
                        "아무것도 얹지 못한다. n=11 이라 유의하지 않다."),
        },
    }


# ------------------------------------------------------------------ leakage risk
def leakage_exposure(rows, sem_gate, n_perm=20000):
    """C 가 지적한 위험: 접근성 텍스트를 분류 feature 로 쓰면 접근성 나쁜 페이지에서
    Axis A 와 RF detector 가 **함께** 무너진다 → SSOT 의 '세 축 독립'이 통계적으로 깨진다.

    각 후보의 확정 여부와 '접근성 표면 빈곤' 지표의 의존성을 잰다. 0 에 가까울수록 좋다.
    """
    aria_empty = [r["C_aria_empty"] for r in rows]
    ctrl_empty = [r["C_control_surface_empty"] for r in rows]
    acc = [r["n_accessible_name_sources"] for r in rows]
    cand = {
        "H1_rule_only_unique_strong": [r["A_det"] for r in rows],
        "H1_alt_ruleDT_leaf": [r["E_det"] for r in rows],
        "H2_rule_then_semantic_margin": [r["A_det"] or (r["E_sem_margin"] >= sem_gate) for r in rows],
        "H2_semantic_only_margin": [r["E_sem_margin"] >= sem_gate for r in rows],
        "H3_hierarchical_rule": [r["D_hier_det"] for r in rows],
    }
    out = {}
    for name, dec in cand.items():
        pairs = [(d, a) for d, a in zip(dec, acc) if a is not None]
        det_v = [a for d, a in pairs if d]
        abs_v = [a for d, a in pairs if not d]
        n_ae = sum(aria_empty)
        out[name] = {
            "n_determined": sum(dec),
            "phi_determined_vs_aria_labels_empty": round(phi_coef(dec, aria_empty), 4),
            "perm_p_aria": round(phi_perm_p(dec, aria_empty, n_perm), 4),
            "phi_determined_vs_control_surface_empty": round(phi_coef(dec, ctrl_empty), 4),
            "perm_p_control_surface": round(phi_perm_p(dec, ctrl_empty, n_perm), 4),
            "determination_rate_when_aria_empty":
                [sum(1 for d, r in zip(dec, rows) if d and r["C_aria_empty"]), n_ae],
            "determination_rate_when_aria_present":
                [sum(1 for d, r in zip(dec, rows) if d and not r["C_aria_empty"]), len(rows) - n_ae],
            "median_n_accessible_name_sources_determined": (st.median(det_v) if det_v else None),
            "median_n_accessible_name_sources_abstained": (st.median(abs_v) if abs_v else None),
        }
    out["_reading"] = (
        "phi < 0 = 접근성 표면이 빈곤할수록 detector 가 abstain 한다 = 두 축이 함께 무너진다. "
        "n=56 에서 |phi| 의 잡음 규모는 대략 1/sqrt(56) = 0.134 다. perm_p 와 함께만 읽어라. "
        "절대값이 아니라 **후보 간 상대 노출도**로만 쓴다.")
    return out


# ------------------------------------------------------------------- Q2/Q3/Q4 sets
def target_property_sets(rows):
    und = [r for r in rows if r["n_rule_impl_determining"] == 0]
    det_any = [r for r in rows if r["n_rule_impl_determining"] > 0]
    principled = [r for r in und if r["surface_absent"]]
    capture_only = [r for r in und if r["capture_defect"] and not r["surface_absent"]]
    neither = [r for r in und if not (r["capture_defect"] or r["surface_absent"])]

    def med(rs, k):
        v = [r[k] for r in rs if r[k] is not None]
        return round(st.median(v), 4) if v else None

    def describe(rs, label):
        return {
            "label": label, "n": len(rs),
            "share_of_56": round(len(rs) / len(rows), 4),
            "wilson95": wilson(len(rs), len(rows)),
            "prior_archetype_distribution": dict(Counter(r["prior_archetype"] for r in rs)),
            "median_blob_tokens": med(rs, "blob_tokens"),
            "median_E_n_fired": med(rs, "E_n_fired"),
            "median_E_sem_margin": med(rs, "E_sem_margin"),
            "median_ssot7_components_present": med(rs, "ssot7_components_present"),
            "share_surface_absent": round(sum(r["surface_absent"] for r in rs) / len(rs), 4) if rs else None,
            "share_capture_defect": round(sum(r["capture_defect"] for r in rs) / len(rs), 4) if rs else None,
            "share_prior_conflict": round(sum(r["prior_conflict"] for r in rs) / len(rs), 4) if rs else None,
            "services": [r["service"] for r in rs],
        }

    sem_high = [r for r in und if r["E_sem_margin"] >= sorted(x["E_sem_margin"] for x in rows)[22]]
    # E 의 함정: semantic 이 가장 확신하는 미확정 target 이 곧 표면부재 target 인가?
    sh = {r["wtg"] for r in sem_high}
    pa = {r["wtg"] for r in principled}
    co = {r["wtg"] for r in capture_only}
    trap = {
        "question": ("rule 이 전부 실패했는데 semantic margin 이 높은 target 은 "
                     "semantic 을 더해야 하는 target 인가, 아니면 브랜드면인가?"),
        "n_semantic_confident_but_no_rule_fires": len(sh),
        "of_which_surface_absent": len(sh & pa),
        "of_which_capture_defect_only": len(sh & co),
        "of_which_genuinely_definition_ambiguous": len(sh - pa - co),
        "surface_absent_services": sorted(rows[i]["service"] for i in range(len(rows))
                                          if rows[i]["wtg"] in (sh & pa)),
        "genuine_services": sorted(rows[i]["service"] for i in range(len(rows))
                                   if rows[i]["wtg"] in (sh - pa - co)),
        "reading": ("**이것이 이 종합에서 가장 불편한 관측이다.** semantic 이 가장 확신하는 미확정 target 의 "
                    "대다수가 표면부재(브랜드면·앱설치면·미렌더) target 이다. E 가 이미 경고한 것과 같다 — "
                    "브랜드면의 텍스트는 그 서비스의 **업종**을 강하게 말해 주므로 semantic 이 잘 맞는데, "
                    "그것은 대표기능을 식별한 것이 아니다(D-FACT-01). "
                    "따라서 '규칙이 실패한 곳에 semantic 을 붙이면 coverage 가 는다' 는 처방은 "
                    "**정확히 붙이면 안 되는 곳에 붙는다.**"),
    }
    return {
        "semantic_confidence_trap": trap,
        "deterministically_identifiable_union": describe(det_any, "적어도 한 rule 구현이 유일 후보를 낸 target"),
        "undetermined_by_every_rule_implementation": describe(und, "세 rule 구현 모두 확정 실패"),
        "needs_semantic_evidence": describe(
            sem_high, "rule 이 전부 실패했으나 semantic margin 이 상위 60% 안에 드는 target"),
        "principled_abstain_surface_absent": describe(
            principled, "rule 전부 실패 + 표면부재 계열 — 이 URL 에서 더 모아도 안 된다"),
        "wrong_kind_of_abstain_capture_defect_only": describe(
            capture_only, "rule 전부 실패 + 관측손상만 — 재수집 대상이지 미결정이 아니다"),
        "residual_definition_ambiguity": describe(
            neither, "rule 전부 실패 + 표면부재도 관측손상도 아님 — 정의 문제"),
    }


# ------------------------------------------------------------------- candidates
def build_candidates(rows, agg, curves, leak, sem_gate):
    """RECOMMENDED_EXPERIMENTAL_CANDIDATES.

    **순위를 매기지 않는다.** 각 후보는 조건과 대가를 병기하며, 반증된 후보도 지우지 않고
    반증 사실과 함께 남긴다 — 그것이 이 문서의 가치다.
    """
    n = len(rows)
    A_det = sum(r["A_det"] for r in rows)
    E_det = sum(r["E_det"] for r in rows)
    D_hier = sum(r["D_hier_det"] for r in rows)
    sem_det = sum(r["E_sem_margin"] >= sem_gate for r in rows)
    casc_det = sum((r["A_det"] or r["E_sem_margin"] >= sem_gate) for r in rows)

    abstention_semantics = {
        "principle": ("E-RF2-E 의 결론을 그대로 받는다 — **표면부재(SURFACE_NOT_REPRESENTATIVE)와 "
                      "관측손상(EVIDENCE_DEFECT)을 같은 leaf 로 묶지 않는다.** 처방이 정반대이기 "
                      "때문이다: 전자는 target URL 재정의, 후자는 재수집."),
        "required_leaves": [
            {"leaf": "SURFACE_NOT_REPRESENTATIVE",
             "meaning": "관측된 표면이 대표기능면이 아니다 (E: T05 브랜드면 / T06 앱설치면 / T07 미렌더·error).",
             "prescription": "target URL 감사. detector 개선이 아니다.",
             "n_in_this_cohort_of_56": sum(r["surface_absent"] for r in rows)},
            {"leaf": "EVIDENCE_DEFECT",
             "meaning": "관측 자체가 손상됐다 (E: T09 렌더희소 / T10A 인코딩 / T10B 절단 / T11 오버레이 / T12 퇴화캡처).",
             "prescription": "재수집 큐. 이 상태의 abstain 은 '미결정'이 아니라 '아직 안 봤다'다.",
             "n_in_this_cohort_of_56": sum(r["capture_defect"] for r in rows)},
            {"leaf": "GENUINELY_AMBIGUOUS",
             "meaning": "표면은 관측됐고 손상도 없는데 정의상 후보가 갈린다 (E: T02/T03/T04).",
             "prescription": "SSOT §5 술어 상호배타화 또는 §6 precedence 명문화. 수집 문제가 아니다.",
             "n_in_this_cohort_of_56": sum(r["definition_ambiguous"] for r in rows)},
            {"leaf": "PRIOR_CONFLICT_UNRESOLVABLE_WITHOUT_LABEL",
             "meaning": "관측 구조와 business prior 가 어긋난다 (E: T13). D 는 label 을 열지 않아 어느 쪽이 틀렸는지 못 가른다.",
             "prescription": "독립 gold label. D 의 권한 밖이다.",
             "n_in_this_cohort_of_56": sum(r["prior_conflict"] for r in rows)},
        ],
        "forbidden": ("`AMBIGUOUS_UNRESOLVED` 단일 leaf. E-RF2-E 는 무발화 12건 중 11건이 "
                      "표면부재 또는 관측손상으로 설명된다고 보고했다 — 단일 leaf 는 원인을 감춘다."),
    }

    common_calibration = [
        "gold label 이 붙은 독립 calibration split — D 는 열지 않았고, 이것 없이는 어떤 threshold 도 정할 수 없다 (SSOT 01 §7).",
        ("평가 지표를 prior_agreement 로 두면 안 된다 — D-FACT-01 에 따라 그것은 업종 배정 재현율이다. "
         "prior 로 detector 를 튜닝하면 업종 분류기가 만들어진다."),
        "abstention leaf 4종(위)의 판정식 — 어휘사전·경로마커·구성요소 임계는 현재 전부 D 의 조작화다.",
        "재수집 반사실 검증 — E 의 RESOLVABLE 판정은 가설이지 결과가 아니다 (E limitation 4번).",
    ]

    cands = []

    # ---------------------------------------------------------------- H1
    cands.append({
        "candidate_id": "H1",
        "name": "High-precision Rule → unresolved = ABSTAIN",
        "status": "RETAINED_WITH_KNOWN_REFUTING_EVIDENCE",
        "one_line": "결정적 규칙만 쓰고 유일 후보가 아니면 전부 abstain 한다. semantic 단계 없음.",
        "deterministic_portion": ("전부. SSOT 01 §5 Stage-3 branch 의 REGION∧ENDPOINT 술어와 "
                                  "§6 resolver(유일 후보만 확정)."),
        "semantic_portion": "없음.",
        "required_evidence": {
            "slots": ["L0 landing snapshot (DOM + AX)"],
            "fields": ["buttons", "aria_labels", "nav_links", "form_labels", "placeholders",
                       "input_names", "card_texts", "landmarks", "title", "headings", "url_tokens"],
            "structural_counters": ["search_inputs_n", "article_present", "gate_password_input_n",
                                    "n_primary_action_candidates", "dom_body_text_len"],
            "note": "endpoint 는 상태전이가 아니라 'endpoint-enabling control 의 존재'로 강등된 상태다 (A·D 공통).",
        },
        "supported_by": [
            {"child": "D-RF2-E", "evidence": ("force-map 비용이 이 후보의 존재이유다. abstain 40건에 "
                                              "rule argmax 를 강제하면 prior 불일치 0.750, SSOT §6 이 금지한 "
                                              "first-match 는 0.775. 규칙이 침묵할 때 강제선택은 기저율 0.46 보다 나쁘다.")},
            {"child": "D-RF2-E", "evidence": ("rule_conf = 0 인 17건의 구간별 prior_agreement 는 **0.000** 이다. "
                                              "규칙이 아무것도 못 본 target 을 끌어들이면 한 건도 안 맞는다 — abstain 이 옳다.")},
            {"child": "D-RF2-A", "evidence": ("증거 부재는 지배적 실패가 아니다(STRONG 13/56, WEAK+ 4/56) — "
                                              "즉 규칙이 '아무것도 못 본다'가 문제는 아니다. H-A3 REFUTED.")},
        ],
        "refuted_by": [
            {"child": "D-RF2-A", "evidence": ("유일 STRONG 후보가 나오는 target 은 13/56 = 0.232 뿐이고 "
                                              "STRONG multi 30/56 이 압도한다. exclusivity 는 7개 중 6개가 0.000 — "
                                              "WEAK+ 수준에서 어떤 archetype 도 혼자 켜지지 못한다. "
                                              "즉 '유일 후보' 조건 자체가 이 증거에서 거의 성립하지 않는다.")},
            {"child": "D-RF2-A", "evidence": ("유일 STRONG 후보가 prior 와 일치한 것은 56건 중 **1건**이다. "
                                              "유일성이 타당성을 뜻하지 않는다.")},
            {"child": "D-RF2-B", "evidence": ("규칙이 딛고 선 16개 조작화 feature 중 BH-FDR(q<0.10)을 "
                                              "통과하는 것이 **0개**다. 8개는 permutation null 평균에도 못 미친다. "
                                              "규칙 술어의 근거는 이 데이터가 아니라 도메인 지식이다.")},
            {"child": "D-RF2-F", "evidence": (f"세 독립 rule 구현(A / D_flat / E_ruleDT)이 "
                                              f"모두 확정한 target 은 56건 중 **1건**이다. Jaccard 0.043~0.190, "
                                              f"pairwise kappa 는 −0.16~+0.13 으로 우연 수준이다. "
                                              f"'결정 가능한 target' 은 target 의 성질이 아니라 lexicon 의 성질이다.")},
        ],
        "observed_coverage_in_this_cohort": {
            "A_operationalization": {"n": A_det, "coverage": round(A_det / n, 4), "wilson95": wilson(A_det, n)},
            "E_operationalization": {"n": E_det, "coverage": round(E_det / n, 4), "wilson95": wilson(E_det, n)},
            "note": "두 수치의 차이가 곧 이 후보의 최대 취약점이다 — 같은 규칙, 다른 어휘, 다른 집합.",
        },
        "expected_failure_modes": [
            {"E_type": "T03_MULTI_STRONG_CANDIDATE", "why": "다중 강후보에서 확정 불가. SSOT §6 이 §7 로 보내라고 한 분기를 이 후보는 받을 곳이 없다."},
            {"E_type": "T02_WEAK_ONE_SIDED_EVIDENCE", "why": "abstain 40 중 최대 유형(22). region 만 또는 endpoint 만 붙은 상태."},
            {"E_type": "T01_NO_PREDICATE_FIRED", "why": "무발화 12건. 단 E 는 이것이 증상이며 11건이 표면부재/관측손상으로 설명된다고 보고했다."},
            {"E_type": "T10A_TEXT_ENCODING_CORRUPTION", "why": "어휘 술어가 무력화된다. force-map 불일치율 1.00."},
        ],
        "abstention_semantics": abstention_semantics,
        "calibration_requirements": common_calibration + [
            "lexicon 을 SSOT 에 명문화해야 한다 — 현재 A/D/E 세 구현의 어휘가 다르고 그 차이가 확정집합을 지배한다.",
            "endpoint 강등(control presence)을 유지할지 상호작용 1스텝 수집으로 풀지의 결정.",
            "UTILITY_ENTRY 의 endpoint(`n_primary_action_candidates>=1`)는 56건 중 52건에서 참이다 — 재정의 없이는 residual 로 남는다.",
        ],
        "operational_complexity": "LOW — 학습 없음, 모델 없음, 결정론적, 전 단계 provenance 추적 가능.",
        "leakage_risk": {
            "level": "MEDIUM",
            "mechanism": ("규칙의 CTRL() 술어가 buttons·aria_labels·form_labels 를 직접 읽는다. "
                          "aria-label 이 없는 페이지는 곧 KWCAG 접근성 축에서 나쁜 페이지다."),
            "measured": leak["H1_rule_only_unique_strong"],
        },
        "explainability": ("HIGH. 어느 술어가 어느 field 의 어느 어휘로 발화했는지 target 마다 남는다 "
                           "(A 의 per_target.firing 이 그 형식이다)."),
        "cost": "coverage 0.20~0.25. SSOT §10 의 holdout coverage >= 0.75 에 도달 불가.",
    })

    # ---------------------------------------------------------------- H2
    cands.append({
        "candidate_id": "H2",
        "name": "High-precision Rule → Semantic prototype ranking → margin low = ABSTAIN",
        "status": "RETAINED_WITH_PARTIAL_REFUTATION_OF_ITS_RULE_STAGE",
        "one_line": "규칙이 유일 후보를 내면 확정, 아니면 frozen prototype 유사도 순위로 넘기고 margin 이 낮으면 abstain.",
        "deterministic_portion": "1단계 규칙(H1 과 동일) + Stage-0 게이트 + abstention leaf 배정.",
        "semantic_portion": ("2단계 — 하나의 텍스트 representation 을 7개 frozen prototype 과 코사인 비교, "
                             "top1−top2 margin 으로 게이트. 학습 없음(zero-shot)."),
        "required_evidence": {
            "slots": ["L0 landing snapshot (DOM + AX)"],
            "fields_rule_stage": "H1 과 동일",
            "fields_semantic_stage": ("C 가 상위군으로 잰 것은 `text_blob`(12 field 전체) 과 "
                                      "`identity`(title+meta_description+url_tokens) 다. "
                                      "브랜드 마스킹 후에는 `text_blob` 이 1위(0.478)로 남고 `title` 은 0.559→0.357 로 무너진다."),
            "must_not_use_as_primary": ("primary_controls / accessibility_text 계열. C: 0.254 / 0.224 vs "
                                        "text_blob 0.509 — 절반 이하이고 stratified p95(0.222)에 붙어 있다."),
        },
        "supported_by": [
            {"child": "D-RF2-E", "evidence": ("margin 5분위에서 하위 2분위(0.364 / 0.455)와 상위 3분위"
                                              "(0.727 / 0.909 / 0.917) 사이가 꺾인다. margin 은 이 코호트에서 "
                                              "실제로 확정 가능성과 단조 관계를 갖는다.")},
            {"child": "D-RF2-E", "evidence": ("force-map 을 semantic 으로 하면 불일치 0.375 로 rule argmax 0.750 의 절반이다. "
                                              "규칙이 침묵하는 구간에서 semantic 은 규칙보다 낫다.")},
            {"child": "D-RF2-C", "evidence": ("field 간 정보량 차이가 prototype 문구 노이즈의 3.3~4.9배다(bge-m3, MiniLM). "
                                              "즉 semantic 단계의 입력 선택은 실재하는 설계 결정이다.")},
            {"child": "D-RF2-E", "evidence": ("debranded 대조군에서도 곡선이 거의 움직이지 않는다"
                                              "(coverage 1.00: 0.679 → 0.696). semantic 신호가 브랜드 문자열만은 아니다.")},
        ],
        "refuted_by": [
            {"child": "D-RF2-F", "evidence": (
                "**이 후보의 1단계가 반증된다.** 같은 coverage 로 맞추면 rule-first cascade 가 "
                "semantic-only 를 **한 번도 이기지 못한다**(모든 대조점에서 Δ ≤ 0). "
                f"rule 이 실제로 확정한 11건에서 McNemar b=0, c=2 — 규칙이 맞고 semantic 이 틀린 target이 "
                f"하나도 없다. 규칙 단계는 이 표본에서 순수 비용이다. "
                f"단 지표가 업종 배정 재현율이므로 '규칙이 대표기능에 대해 무가치하다'는 뜻은 아니다.")},
            {"child": "D-RF2-C", "evidence": ("margin 은 field 를 가르지 못한다 — 22개 representation 전부 "
                                              "margin 중앙값이 0.016~0.036 의 좁은 띠다. 게다가 "
                                              "`form_labels` 는 39/56 이 비었는데 margin 은 평균보다 높다 — "
                                              "**정보가 없을수록 margin 이 커지는 역전**이 있다. "
                                              "margin 을 abstention 게이트로 쓰면 이 역전을 그대로 산다.")},
            {"child": "D-RF2-E", "evidence": ("SSOT §6 이 §7 로 보내라고 한 T03 다중강후보 6건에서 "
                                              "semantic 불일치율(0.67)이 rule(0.50)보다 **높다**. "
                                              "즉 이 후보의 2단계가 1단계의 실패 유형을 실제로 가른다는 증거가 없다.")},
            {"child": "D-RF2-B", "evidence": ("prior 를 되찾는 신호의 상당 부분이 페이지 규모 축일 수 있다 — "
                                              "16 feature 의 제1성분(33% 분산)이 규모이고 상위 feature "
                                              "`accessible_name_richness`(MI 0.264)는 domain 의미가 없는 구조량이다.")},
            {"child": "D-RF2-F", "evidence": (
                "**semantic confidence trap.** 규칙이 전부 실패했는데 semantic margin 이 높은 14건 중 "
                "10건이 표면부재(브랜드면·앱설치면·미렌더) target 이다. 즉 이 후보의 2단계가 열어 주는 "
                "coverage 는 **정확히 열면 안 되는 곳에서** 열린다 — 브랜드면 텍스트가 업종을 강하게 "
                "말해 주기 때문이지 대표기능을 드러내기 때문이 아니다.")},
        ],
        "observed_coverage_in_this_cohort": {
            "rule_stage_only": {"n": A_det, "coverage": round(A_det / n, 4)},
            "cascade_at_declared_gate": {"n": casc_det, "coverage": round(casc_det / n, 4),
                                         "gate_note": "이 gate 는 40% 분위수로 잡은 **기술적 절단점**이지 운영 threshold 가 아니다."},
            "semantic_only_at_same_gate": {"n": sem_det, "coverage": round(sem_det / n, 4)},
            "matched_coverage_comparison": curves["curve"][:8],
        },
        "expected_failure_modes": [
            {"E_type": "T05_GENERIC_BRAND_LANDING", "why": ("E 의 가장 불편한 관측 — 브랜드면에서 semantic 이 "
                                                            "오히려 prior 와 잘 맞는다. 대표기능을 읽은 것이 아니라 업종을 맞힌 것이다. "
                                                            "coverage 를 올리는 근거로 쓰면 안 된다.")},
            {"E_type": "T03_MULTI_STRONG_CANDIDATE", "why": "semantic 이 rule 보다 더 못 가른다(0.67 vs 0.50)."},
            {"E_type": "T10A_TEXT_ENCODING_CORRUPTION", "why": "semantic force-map 불일치 0.57 — 깨진 텍스트는 임베딩도 못 살린다."},
            {"E_type": "T06_APP_INSTALL_SURFACE", "why": "semantic 불일치 0.55. 웹 표면의 대표행동이 '앱으로 나가기'다."},
        ],
        "abstention_semantics": dict(abstention_semantics, extra=(
            "margin 이 낮아서 abstain 한 것과 표면이 없어서 abstain 한 것을 같은 leaf 로 묶으면 안 된다. "
            "전자는 LOW_CONFIDENCE_SEMANTIC, 후자는 SURFACE_NOT_REPRESENTATIVE 다.")),
        "calibration_requirements": common_calibration + [
            "margin threshold — **D 는 정하지 않는다.** independent calibration split 이 필요하다(SSOT §7).",
            "prototype 세트 동결과 그 provenance — C 는 SSOT §5·§7 에서만 유도했고 코퍼스를 보고 맞추지 않았다. 이 규율이 유지돼야 한다.",
            "embedding 모델 고정. C: e5-small 에서는 field 효과가 prototype 문구 노이즈에 묻힌다(0.098 vs 0.103).",
            "representation 선택 — brand-masked 조건에서 다시 재야 한다. C 의 1위 `title` 은 마스킹에서 무너진다.",
            "인코딩 검증을 파이프라인 게이트로. C §10: mojibake 8/56 이 짧은 field 의 macro F1 을 12.5%p 떨어뜨렸는데 blob 지표로는 1.2%p 로만 보였다.",
        ],
        "operational_complexity": "MEDIUM — 임베딩 모델 1개 + prototype 7문장 + 게이트 1개. 학습은 여전히 없음.",
        "leakage_risk": {
            "level": "LOW_TO_MEDIUM",
            "mechanism": ("semantic 단계가 `text_blob`/`identity` 를 쓰면 접근성 텍스트 의존도가 낮다 — "
                          "C 의 LOO ablation 에서 `aria_labels` 의 기여는 Δ+0.035, `form_labels` Δ+0.030 에 "
                          "불과하고 `input_names`·`placeholders` 는 blob 안에서 오히려 노이즈다. "
                          "대신 브랜드/업종 어휘 순환이라는 **다른 종류의 누출**이 남는다."),
            "measured": leak["H2_rule_then_semantic_margin"],
            "measured_semantic_only": leak["H2_semantic_only_margin"],
        },
        "explainability": ("MEDIUM. 1단계는 술어 provenance 가 남지만 2단계는 코사인 순위라 "
                           "'왜 이 archetype 인가'를 field 수준으로 되짚을 수 없다. "
                           "C 의 LOO ablation 이 사후 해부의 유일한 경로다."),
        "cost": ("coverage 를 얻는 대신 '무엇을 관측했는가'가 흐려진다. 그리고 D-FACT-01 때문에 "
                 "이 후보의 관측된 이득은 **업종 배정 재현율의 이득**으로만 확인됐다."),
    })

    # ---------------------------------------------------------------- H3
    cands.append({
        "candidate_id": "H3",
        "name": "Hierarchical Interaction Rule → field-specific semantic ranking → conflict = ABSTAIN",
        "status": "RETAINED_BUT_ALREADY_PARTIALLY_REFUTED — 목록에서 지우지 않는다",
        "retention_rationale": ("반증된 후보를 지우면 다음 사람이 같은 설계를 다시 제안한다. "
                                "반증 사실과 함께 남기는 것이 이 문서의 산출물이다."),
        "one_line": ("interaction primitive 를 먼저 가르고(L1), primitive 안에서 field 별 semantic 순위로 "
                     "archetype 을 정하고, 충돌하면 abstain 한다."),
        "deterministic_portion": "L1 primitive 판정 + L2 후보 제한 + 충돌 게이트.",
        "semantic_portion": "L2 — primitive member 로 제한된 후보 위의 field-specific 유사도 순위.",
        "required_evidence": {
            "slots": ["L0 landing snapshot (DOM + AX)"],
            "fields": ("L1 은 20개 atomic predicate(SEARCH_INPUT / ITEM_CARDS / PRICE / TXN_CTRL / "
                       "LOGIN_GATE / FIN_HEAD / TOOL_PRIMARY …), L2 는 field 별로 분리된 텍스트 표면."),
            "note": "field-specific 이라는 요구가 곧 이 후보의 최대 약점이다 — 아래 refuted_by 참조.",
        },
        "supported_by": [
            {"child": "D-RF2-D", "evidence": ("L2 에서 손실이 **0** 이다(16/16). 일단 L1 이 닫히면 "
                                              "그 안에서는 후보가 갈리지 않는다 — 계층 아이디어의 유일한 관측된 장점.")},
            {"child": "D-RF2-D", "evidence": ("계층이 flat 을 잃지 않고 감싼다(S2): 두 구조가 같이 매핑한 14건에서 "
                                              "예측이 100% 동일하고, flat 만 매핑한 건이 0 이다. coverage 는 14→16.")},
            {"child": "D-RF2-C", "evidence": ("field 마다 정보량이 실제로 다르다(macro F1 0.030~0.559, "
                                              "between-field sd 가 prototype 노이즈 sd 의 3.3배) — "
                                              "field-specific 이라는 발상 자체는 근거가 있다.")},
        ],
        "refuted_by": [
            {"child": "D-RF2-D", "evidence": ("**핵심 반증.** 계층 이득이 0 이다. flat 과 hier 의 prior 일치 여부가 "
                                              "target 단위로 완전히 같다 — McNemar b=0, c=0. 늘어난 coverage 2건은 "
                                              "둘 다 prior 불일치라 prior_agreement 는 5/56 → 5/56 으로 불변이다.")},
            {"child": "D-RF2-D", "evidence": ("병목은 L1 이다. Stage0 6 / L1 무후보 19 / L1 다중후보 15 로 40건을 "
                                              "L1 에서 잃고 L2 에서는 0건을 잃는다. 계층을 넣어도 손실 구조가 바뀌지 않는다.")},
            {"child": "D-RF2-D", "evidence": ("L1 은 쉽지 않다. L1 이 닫은 16건의 prior primitive 일치 9/16=0.5625 는 "
                                              "같은 16건의 다수결 기준선 13/16=0.8125 **보다 낮다**.")},
            {"child": "D-RF2-D", "evidence": ("L1 의 후보 제한이 semantic arm 에서 정보를 **뺀다**: 동일 16건에서 "
                                              "제한 없는 7-way argmax 9/16 → 제한 후 6/16 (McNemar p=0.375, 방향은 음).")},
            {"child": "D-RF2-D", "evidence": ("SSOT §5 branch tree 는 primitive 위의 분할이 아니다 — PLACE_LOOKUP 과 "
                                              "COMMUNICATION_ENTRY 가 primitive 2개에 걸친다. 계층을 엄격히 강제하면(S2s) "
                                              "flat 이 확정하던 3건을 그 이유만으로 잃는다.")},
            {"child": "D-RF2-C", "evidence": ("**field-specific semantic 이 반증된다.** primary_controls 0.254 · "
                                              "first_screen_interaction 0.257 · accessibility_text 0.224 로 "
                                              "text_blob 0.509 의 절반 이하이며, 세 모델 모두에서 하위권이다. "
                                              "blob 예측과 controls 예측이 갈린 25건 중 blob 이 맞은 것이 23, controls 가 맞은 것이 2다.")},
            {"child": "D-RF2-A", "evidence": ("L1 이 겨냥한 list-family 얽힘은 국소 문제가 아니다 — family 6쌍의 "
                                              "평균 Jaccard(STRONG 0.145 / WEAK+ 0.548)가 나머지 15쌍"
                                              "(0.213 / 0.581)보다 오히려 **낮다**. 최강 얽힘 쌍은 F–U, Q–U 로 family 를 가로지른다.")},
        ],
        "observed_coverage_in_this_cohort": {
            "hier_rule": {"n": D_hier, "coverage": round(D_hier / n, 4), "wilson95": wilson(D_hier, n)},
            "flat_reference": {"n": sum(r["D_flat_det"] for r in rows),
                               "coverage": round(sum(r["D_flat_det"] for r in rows) / n, 4)},
            "prior_agreement_unchanged": "flat 5/56 = hier 5/56 (D-RF2-D §12)",
        },
        "expected_failure_modes": [
            {"E_type": "T04_SHARED_LIST_SIGNAL", "why": "L1 이 없애려던 바로 그 유형인데 primitive 층이 그대로 재생산한다."},
            {"E_type": "T03_MULTI_STRONG_CANDIDATE", "why": "L1 다중후보 15건의 최빈 충돌이 '검색창 + 반복 카드'로 SSOT §6 이 든 그 사례다."},
            {"E_type": "T02_WEAK_ONE_SIDED_EVIDENCE", "why": "primitive 수준 R/E 도 결국 한쪽만 붙는다."},
            {"E_type": "T09_CLIENT_RENDER_SPARSE", "why": "field 를 쪼갤수록 빈 field 가 늘고, C 규약상 빈 representation 은 abstain 이다."},
        ],
        "abstention_semantics": dict(abstention_semantics, extra=(
            "이 후보에는 **L1 abstain 과 L2 abstain 을 구분하는 leaf 가 추가로 필요하다.** "
            "D 의 관측에서 L1_MULTI 와 L1_NONE 은 원인이 다르고(전자는 정의, 후자는 증거), "
            "L2 손실은 0 이라 사실상 발생하지 않는다.")),
        "calibration_requirements": common_calibration + [
            "**선행조건**: SSOT §5 를 primitive 분할이 되도록 재정의해야 한다 — 7 archetype 변경이므로 A 결정 사항이다. D 는 제안만 한다.",
            "field 별 prototype 을 따로 둘지 — C 는 field 별로 문구를 바꾸면 field 비교가 무너진다고 보고 동일 세트를 강제했다. field-specific 을 하려면 이 규약부터 다시 세워야 한다.",
            "primitive 경계의 독립 검증 — D 의 L1 정의는 SSOT §5 endpoint 절에서 유도한 `DEFINITION` 이며 검증받지 않았다.",
        ],
        "operational_complexity": "HIGH — 2층 규칙 + field 별 임베딩 + 충돌 게이트. 세 후보 중 가장 비싸다.",
        "leakage_risk": {
            "level": "HIGH — 세 후보 중 최대",
            "mechanism": ("field-specific semantic 의 '좋은 field' 후보가 정확히 접근성 표면"
                          "(aria_labels / form_labels / placeholders / input_names)이다. "
                          "C 가 지적한 위험이 이 후보에서 최대가 된다: 접근성이 나쁜 페이지에서 "
                          "Axis A 와 RF detector 가 **함께** 무너져 SSOT 의 세 축 독립이 통계적으로 깨진다."),
            "measured": leak["H3_hierarchical_rule"],
            "measured_reading": ("이 코호트에서 H3 의 확정률은 aria_labels 가 빈 20건에서 "
                                 f"{leak['H3_hierarchical_rule']['determination_rate_when_aria_empty'][0]}/20, "
                                 f"있는 36건에서 {leak['H3_hierarchical_rule']['determination_rate_when_aria_present'][0]}/36 이다. "
                                 "phi 는 세 후보 중 가장 음수다. n=56 이라 잡음 규모(±0.13)와 겹치므로 "
                                 "**후보 간 상대 비교로만** 읽어야 한다."),
        },
        "explainability": ("MEDIUM-HIGH for L1 (술어 추적 가능), LOW for L2 (field 별 코사인). "
                           "단 두 층으로 나뉘어 실패 지점을 특정하기는 쉽다 — D 가 '병목은 L1' 이라고 "
                           "말할 수 있었던 것이 이 구조 덕이다."),
        "cost": ("가장 비싼 구조에 대해 **관측된 이득이 정확히 0** 이다. 그리고 그 구조를 "
                 "제대로 만들려면 SSOT 의 archetype 정의를 먼저 손대야 한다."),
    })

    # ---------------------------------------------------------------- H4 (추가)
    cands.append({
        "candidate_id": "H4",
        "name": "Evidence-admissibility gate → single semantic ranking → margin low = ABSTAIN (rule 단계 없음)",
        "status": "NEW_CANDIDATE_ADDED_BY_SYNTHESIS",
        "addition_rationale": ("최소 후보 3개는 전부 '규칙 먼저'를 공유한다. A~E 를 합치면 그 공유 전제 자체가 "
                               "이 표본에서 지지되지 않는다 — 그래서 그 전제를 뺀 대조 후보를 하나 세운다. "
                               "이것은 추천이 아니라 **대조군**이다."),
        "one_line": ("규칙으로 archetype 을 고르지 않는다. 규칙은 오직 '이 관측이 판정 가능한가'를 게이트하고"
                     "(Stage-0 + 표면부재/관측손상 판정), 통과한 것만 하나의 semantic 순위에 넘긴다."),
        "deterministic_portion": ("evidence admissibility 만 — Stage-0, E 의 표면부재/관측손상 유형 판정, "
                                  "인코딩 검증. archetype 선택에는 규칙을 쓰지 않는다."),
        "semantic_portion": "단일 representation × 7 frozen prototype × margin 게이트.",
        "required_evidence": {
            "slots": ["L0 landing snapshot (DOM + AX)"],
            "fields": "admissibility 판정용 구조 신호 + semantic 용 `text_blob` 또는 `identity` 1개.",
        },
        "supported_by": [
            {"child": "D-RF2-F", "evidence": ("같은 coverage 에서 semantic-only 가 rule-first cascade 를 "
                                              "모든 대조점에서 이긴다(Δ ≤ 0 전부). 규칙 단계를 빼는 것이 이 표본에서 손해가 아니다.")},
            {"child": "D-RF2-D", "evidence": ("계층 없는 7-way semantic argmax 를 전부 강제매핑하면 29/56 = 0.518 인데 "
                                              "어떤 규칙 구조도 overall 6/56 = 0.107 를 넘지 못한다. "
                                              "이 격차가 flat-대-계층 격차보다 훨씬 크다.")},
            {"child": "D-RF2-E", "evidence": ("표면부재/관측손상을 별도 leaf 로 올리라는 E 의 처방을 "
                                              "구조의 1단계로 승격한 형태다. 무발화 12건 중 11건이 이 두 계열로 설명된다.")},
        ],
        "refuted_by": [
            {"child": "D-RF2-E", "evidence": ("**가장 무거운 반증.** 표면부재 유형을 먼저 abstain 시킨 캐스케이드는 "
                                              "같은 coverage 에서 prior_agreement 가 오히려 **낮다**. "
                                              "브랜드/앱 랜딩면에서는 semantic 이 잘 맞는데, 그건 대표기능을 읽어서가 아니라 "
                                              "**업종을 맞혀서**다. 즉 이 후보의 게이트는 지표를 떨어뜨리는데 그것이 오히려 옳을 수 있다 — "
                                              "지표가 D-FACT-01 때문에 잘못된 것을 재고 있기 때문이다. 이 후보는 "
                                              "**현재 지표로는 평가 자체가 불가능하다.**")},
            {"child": "D-RF2-C", "evidence": ("semantic 단독의 신호는 identity 순환에 취약하다. "
                                              "`title` 0.559 → 브랜드 마스킹 0.357, `url_tokens` 0.361 → 0.138. "
                                              "규칙을 빼면 이 순환을 견제할 구조가 하나도 남지 않는다.")},
            {"child": "D-RF2-A", "evidence": ("규칙 단계를 빼면 '어떤 관측 때문에 이렇게 판정했는가'의 "
                                              "provenance 가 사라진다. A 의 per-target signal provenance 가 "
                                              "가능했던 것은 규칙이 있었기 때문이다.")},
            {"child": "D-RF2-B", "evidence": "구조 feature 가 판정에 전혀 들어가지 않으므로, 텍스트가 손상된 target 에서 대안이 없다."},
        ],
        "observed_coverage_in_this_cohort": {
            "semantic_only_at_declared_gate": {"n": sem_det, "coverage": round(sem_det / n, 4)},
            "matched_coverage_comparison": curves["curve"][:8],
            "caveat": "이 수치는 업종 배정 재현율이다. 대표기능 성능이 아니다 (D-FACT-01).",
        },
        "expected_failure_modes": [
            {"E_type": "T05_GENERIC_BRAND_LANDING", "why": "게이트가 잡아내지만, 잡아낸 뒤 지표가 나빠진다 — 위 반증 참조."},
            {"E_type": "T13_PRIOR_CONTRADICTS_STRUCTURE", "why": "구조 증거를 안 쓰므로 prior 와 구조의 불일치를 관측할 수단이 없다."},
            {"E_type": "T10A_TEXT_ENCODING_CORRUPTION", "why": "텍스트에 전량 의존하므로 인코딩 손상이 치명적이다. 게이트가 반드시 앞서야 한다."},
        ],
        "abstention_semantics": dict(abstention_semantics, extra=(
            "이 후보에서 abstain 은 두 곳에서만 나온다 — admissibility 게이트(SURFACE_NOT_REPRESENTATIVE / "
            "EVIDENCE_DEFECT)와 margin 게이트(LOW_CONFIDENCE_SEMANTIC). "
            "GENUINELY_AMBIGUOUS 를 관측할 수단이 없다는 것이 이 구조의 구조적 맹점이다.")),
        "calibration_requirements": common_calibration + [
            "admissibility 판정식의 독립 검증 — 현재 E 의 유형 판정식은 전부 D 의 조작화다.",
            "brand/domain-vocabulary ablation — 브랜드 문자열만이 아니라 업종 어휘까지 지운 조건에서 신호가 남는지. C 의 최우선 후속질문이다.",
            "margin threshold — D 는 정하지 않는다.",
        ],
        "operational_complexity": "LOW-MEDIUM — 규칙 트리가 없고 게이트 + 임베딩 1개.",
        "leakage_risk": {
            "level": "LOW for accessibility-axis coupling, HIGH for identity circularity",
            "mechanism": ("접근성 표면을 분류 feature 로 쓰지 않으므로 C 가 경고한 축 결합은 가장 약하다. "
                          "대신 '업종을 맞히고 대표기능을 맞혔다고 말하는' 순환이 견제 없이 남는다."),
            "measured": leak["H2_semantic_only_margin"],
        },
        "explainability": "LOW. 게이트는 설명되지만 archetype 선택은 코사인 순위 하나다.",
        "cost": "provenance 와 구조 증거를 통째로 포기한다. 그 대가로 이 표본에서 가장 높은 업종 재현율을 얻는다.",
    })
    return cands


# ------------------------------------------------------------------------ figures
def fig_decision_matrix(rows, cols, path):
    names = list(cols)
    order = sorted(range(len(rows)),
                   key=lambda i: (-sum(cols[nm][i] for nm in names), rows[i]["prior_archetype"]))
    M = np.array([[1 if cols[nm][i] else 0 for nm in names] for i in order], float)
    fig, ax = plt.subplots(figsize=(7.6, 12))
    ax.imshow(M, aspect="auto", cmap="RdYlGn", vmin=0, vmax=1)
    ax.set_xticks(range(len(names)))
    ax.set_xticklabels(names, rotation=45, ha="right", fontsize=8)
    ax.set_yticks(range(len(order)))
    ax.set_yticklabels([f"{rows[i]['prior_archetype'][:12]:<12} {rows[i]['wtg'][:8]}" for i in order],
                       fontsize=5.5, family="monospace")
    ax.set_title("RF2-F  per-target DETERMINED (green) vs ABSTAIN (red)\n"
                 "each column = that child's own decision rule; n=56", fontsize=9)
    for k in range(1, len(names)):
        ax.axvline(k - .5, color="white", lw=.6)
    fig.tight_layout()
    fig.savefig(path, dpi=140)
    plt.close(fig)


def fig_agreement(am, mult, path):
    names = am["columns"]
    K = np.array([[am["kappa_matrix"][a][b] for b in names] for a in names], float)
    J = np.array([[am["jaccard_of_determined_sets"][a][b] for b in names] for a in names], float)
    dist = mult["n_implementations_determining_distribution"]
    fig, axes = plt.subplots(1, 3, figsize=(16, 5.2))
    for ax, M, ttl, vlo in ((axes[0], K, "Cohen's kappa (determined/abstain)", -1),
                            (axes[1], J, "Jaccard of DETERMINED sets", 0)):
        im = ax.imshow(M, cmap="coolwarm" if vlo < 0 else "viridis", vmin=vlo, vmax=1)
        ax.set_xticks(range(len(names)))
        ax.set_xticklabels(names, rotation=45, ha="right", fontsize=7)
        ax.set_yticks(range(len(names)))
        ax.set_yticklabels(names, fontsize=7)
        for i in range(len(names)):
            for jj in range(len(names)):
                if not math.isnan(M[i, jj]):
                    ax.text(jj, i, f"{M[i, jj]:.2f}", ha="center", va="center", fontsize=6.5,
                            color="black")
        ax.set_title(ttl, fontsize=9)
        fig.colorbar(im, ax=ax, fraction=.046)
    ax = axes[2]
    ks = [0, 1, 2, 3]
    vs = [dist.get(str(k), 0) for k in ks]
    ax.bar([str(k) for k in ks], vs, color=["#b2182b", "#ef8a62", "#67a9cf", "#2166ac"])
    for i, v in enumerate(vs):
        ax.text(i, v + .4, str(v), ha="center", fontsize=9)
    ax.set_xlabel("# independent rule impls determining the target", fontsize=8)
    ax.set_ylabel("targets")
    ax.set_title(f"A / D_flat / E_ruleDT agreement\nunion={mult['union_determined_by_at_least_one']}, "
                 f"all three={mult['determined_by_all_three']}", fontsize=9)
    fig.suptitle("RF2-F  cross-child decision agreement — same SSOT rule, three lexicons", fontsize=11)
    fig.tight_layout()
    fig.savefig(path, dpi=140)
    plt.close(fig)


def fig_candidate_evidence(cands, path):
    children = ["D-RF2-A", "D-RF2-B", "D-RF2-C", "D-RF2-D", "D-RF2-E", "D-RF2-F"]
    ids = [c["candidate_id"] for c in cands]
    S = np.zeros((len(ids), len(children)))
    R = np.zeros((len(ids), len(children)))
    for i, c in enumerate(cands):
        for s in c["supported_by"]:
            S[i, children.index(s["child"])] += 1
        for s in c["refuted_by"]:
            R[i, children.index(s["child"])] += 1
    M = S - R
    fig, ax = plt.subplots(figsize=(10.0, 4.4))
    im = ax.imshow(M, cmap="RdBu", vmin=-4, vmax=4)
    ax.set_xticks(range(len(children)))
    ax.set_xticklabels(children, rotation=30, ha="right", fontsize=8)
    ax.set_yticks(range(len(ids)))
    ax.set_yticklabels([f"{c['candidate_id']}  {c['name'][:46]}" for c in cands], fontsize=7)
    for i in range(len(ids)):
        for j in range(len(children)):
            if S[i, j] or R[i, j]:
                ax.text(j, i, f"+{int(S[i, j])} / -{int(R[i, j])}", ha="center", va="center",
                        fontsize=8.5, color="white" if abs(M[i, j]) > 2 else "black")
    fig.colorbar(im, ax=ax, fraction=.03, label="(+) supporting  /  (-) refuting findings")
    ax.set_title("RF2-F  which child supports or refutes which candidate\n"
                 "cell = +supporting / -refuting findings (colour = net); NO ranking implied", fontsize=9)
    fig.tight_layout()
    fig.savefig(path, dpi=140)
    plt.close(fig)


def fig_coverage(curves, rows, path):
    c = curves["curve"]
    x = [r["coverage"] for r in c]
    fig, ax = plt.subplots(figsize=(8.6, 5.4))
    ax.plot(x, [r["semantic_only_prior_agreement"] for r in c], "o-", label="semantic only (margin gate)")
    ax.plot(x, [r["semantic_only_debranded_prior_agreement"] for r in c], "s--",
            label="semantic only, debranded control")
    ax.plot(x, [r["rule_first_cascade_prior_agreement"] for r in c], "^-",
            label="rule first -> semantic cascade")
    rm = [r for r in rows if r["E_det"]]
    ax.scatter([len(rm) / len(rows)],
               [sum(1 for r in rm if r["E_pred"] == r["prior_archetype"]) / len(rm)],
               marker="*", s=260, color="crimson", zorder=5, label="rule only (SSOT §6 resolver)")
    ax.axhline(0.4643, color="grey", ls=":", label="prior majority base rate 0.464")
    ax.set_xlabel("coverage (denominator = 56)")
    ax.set_ylabel("prior_agreement = business-domain assignment recall\n(D-FACT-01: NOT accuracy)", fontsize=9)
    ax.set_ylim(0, 1)
    ax.legend(fontsize=8, loc="lower left")
    ax.set_title("RF2-F  matched-coverage comparison — NO threshold is declared\n"
                 "the y axis is NOT accuracy: prior_archetype is bijective with prior_business_domain",
                 fontsize=9)
    fig.tight_layout()
    fig.savefig(path, dpi=140)
    plt.close(fig)


def fig_leakage(leak, path):
    names = [k for k in leak if not k.startswith("_")]
    phi_a = [leak[k]["phi_determined_vs_aria_labels_empty"] for k in names]
    phi_c = [leak[k]["phi_determined_vs_control_surface_empty"] for k in names]
    xs = np.arange(len(names))
    fig, ax = plt.subplots(figsize=(9.6, 5.0))
    ax.bar(xs - .18, phi_a, .34, label="phi(determined, aria_labels EMPTY)")
    ax.bar(xs + .18, phi_c, .34, label="phi(determined, control surface EMPTY)")
    ax.axhspan(-0.134, 0.134, color="grey", alpha=.18, label="noise band ~ 1/sqrt(56)")
    ax.axhline(0, color="black", lw=.8)
    ax.set_xticks(xs)
    ax.set_xticklabels(names, rotation=18, ha="right", fontsize=7.5)
    ax.set_ylabel("phi   (negative = abstains where a11y surface is poor)", fontsize=8)
    ax.legend(fontsize=8)
    ax.set_title("RF2-F  three-axis independence exposure (C's warning, quantified)\n"
                 "relative comparison only; n=56", fontsize=9)
    fig.tight_layout()
    fig.savefig(path, dpi=140)
    plt.close(fig)


def fig_abstain_partition(props, path):
    keys = ["deterministically_identifiable_union", "wrong_kind_of_abstain_capture_defect_only",
            "principled_abstain_surface_absent", "residual_definition_ambiguity"]
    labels = ["determined by >=1 rule impl", "abstain: capture defect only\n(re-collect)",
              "abstain: surface not representative\n(re-define target URL)",
              "abstain: definition ambiguity\n(fix SSOT)"]
    vals = [props[k]["n"] for k in keys]
    fig, ax = plt.subplots(figsize=(10.4, 3.6))
    left = 0
    colors = ["#2166ac", "#f4a582", "#b2182b", "#7b3294"]
    for v, lb, cl in zip(vals, labels, colors):
        ax.barh([0], [v], left=left, color=cl, edgecolor="white", label=lb)
        ax.text(left + v / 2, 0, f"n={v}", ha="center", va="center", fontsize=10,
                color="white", fontweight="bold")
        left += v
    ax.set_xlim(0, 56)
    ax.set_ylim(-1.4, 0.6)
    ax.set_yticks([])
    ax.legend(fontsize=7.5, loc="lower center", ncol=4, frameon=False)
    ax.set_xlabel("targets (n=56)")
    ax.set_title("RF2-F  what kind of ABSTAIN — the three prescriptions are opposites\n"
                 "(E-RF2-E: never put these in one leaf)", fontsize=9)
    fig.tight_layout()
    fig.savefig(path, dpi=140)
    plt.close(fig)


# --------------------------------------------------------------------------- main
def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-mlflow", action="store_true")
    ap.add_argument("--perm", type=int, default=20000)
    args = ap.parse_args(argv)

    obs, cor, j = load()
    rows = build_frame(obs, cor, j)
    n = len(rows)
    assert n == 56, n

    # semantic gate: 이 코호트 margin 분포의 40% 분위수. **운영 threshold 가 아니다.**
    margins = sorted(r["E_sem_margin"] for r in rows)
    sem_gate = margins[int(0.4 * n)]

    cols = decision_columns(rows, sem_gate)
    am = agreement_matrix(cols, rows)
    mult = multiplicity_analysis(rows)
    splits = split_targets(rows, cols)
    curves = matched_coverage_curves(rows)
    leak = leakage_exposure(rows, sem_gate, n_perm=args.perm)
    props = target_property_sets(rows)
    cands = build_candidates(rows, mult, curves, leak, sem_gate)

    inputs = [{"path": f"results/{f}", "sha256": sha256_file(RES / f)} for f in INPUTS]
    child_verdicts = {
        "D-RF2-A": {"verdict": j["A"]["verdict"], "headline": (
            "STRONG multi 30/56 > single 13/56, WEAK+ multi 50/56. exclusivity 7개 중 6개가 0.000, "
            "WEAK+ Jaccard 가 0.364 아래인 쌍이 하나도 없다. 유일 STRONG = prior 는 1/56.")},
        "D-RF2-B": {"verdict": j["B"]["verdict"], "headline": (
            "16 feature 중 BH-FDR(q<0.10) 통과 0개, 8개는 permutation null 평균 미달. "
            "실효차원 6.37(독립 null 12.51). 상위는 구조량 accessible_name_richness MI 0.264.")},
        "D-RF2-C": {"verdict": j["C"]["verdict"], "headline": (
            "primary_controls 0.254 / accessibility_text 0.224 vs text_blob 0.509 — 절반 이하. "
            "브랜드 마스킹 후 title 0.559→0.357, text_blob 0.478 로 1위.")},
        "D-RF2-D": {"verdict": j["D"]["verdict"], "headline": (
            "계층 이득 0. McNemar b=0, c=0. 병목은 L1(40건 손실), L2 손실 0.")},
        "D-RF2-E": {"verdict": j["E"]["verdict"], "headline": (
            "NO_STRONG_CANDIDATE 는 증상 — 무발화 12 중 11 설명됨. force-map 불일치 rule 0.750 / "
            "first-match 0.775 / semantic 0.375. margin 2~3분위 사이 꺾임.")},
    }

    doc = {
        "schema": "RF2_F_cascade_synthesis/1",
        "child_id": CHILD_ID, "rq_id": RQ_ID, "hypothesis_id": HYP,
        "model_or_rule_version": VERSION, "seed": SEED,
        "parent_run_id": PARENT_RUN,
        "generated_at_kst": datetime.now(KST).isoformat(),
        "plane": "D", "authority": "NON_CANONICAL", "claim_kind": "ANALYSIS", "split": "none",
        "output_kind": "RECOMMENDED_EXPERIMENTAL_CANDIDATES",
        "best_model_selected": False,
        "production_threshold_declared": False,
        "go_nogo_decision": "NOT_IN_SCOPE — D 는 GO/NO-GO 를 내지 않는다",
        "analysis_unit": "target (wtg, in_mart==1)",
        "n_expected": 56, "n_observed": n,
        "inputs": inputs,
        "firewall": {
            "not_opened": ["holdout label", "LABEL_SPLIT_FROZEN*", "HOLDOUT_FOR_C*", "RAW_L1~L4*",
                           "PACKET_L*", "*_OVERLAP*", "PRECEDENCE_CONTESTED*", "CALIBRATION_FOR_B*",
                           "**/control/**", "B/C target-level holdout error report"],
            "note": ("위 목록의 어떤 파일도 **열지 않았다.** 입력은 inputs[] 가 전부다. "
                     "네트워크 없음, gold label 생성 없음, A~E 산출물 수정 없음."),
        },
        "D_FACT_01_framing": {
            "statement": ("이 56 target 표본에서 prior_archetype 과 prior_business_domain 은 완전 전단사다 "
                          "(7↔7, MI = H = 2.311 bits, 정규화 MI = 1.000, 56/56)."),
            "consequence": ("A~E 와 이 문서가 보고하는 모든 prior_agreement 는 **업종 배정 재현율**이지 "
                            "대표기능 정확도가 아니다. 이 문서는 어떤 후보의 기대성능도 '정확도'로 서술하지 않는다."),
            "source": "results/D_FACT_01_prior_domain_bijection.md",
        },
        "child_verdicts": child_verdicts,
        "semantic_gate_used_for_illustration": {
            "value": round(sem_gate, 6),
            "provenance": "이 코호트 margin 분포의 40% 분위수",
            "warning": "**운영 threshold 가 아니다.** SSOT 01 §7 은 independent calibration split 을 요구한다.",
        },
        "decision_agreement_matrix": am,
        "degenerate_columns": {
            "D-RF2-B": ("B 는 target-level 결정을 내지 않는다. B 의 결론(16 feature 중 FDR 통과 0개)을 "
                        "결정규칙으로 옮기면 '어떤 target 도 이 feature 집합만으로는 확정 불가' 가 되어 "
                        "56/56 ABSTAIN 인 퇴화 컬럼이 된다. kappa 를 계산할 수 없어 행렬에서 제외했다."),
            "D-RF2-C_text_blob": ("C 의 사전등록 규약은 '빈 representation = ABSTAIN' 이다. "
                                  "text_blob 은 56/56 이 비어있지 않아 역시 퇴화 컬럼이다. "
                                  "C 가 per-target 으로 남긴 유일한 판정은 blob 예측과 control 표면 예측이 갈린 "
                                  "25건(blob 맞음 23 : controls 맞음 2)이며, 그것은 결정 컬럼이 아니라 "
                                  "**representation 선택의 대가**를 재는 관측이다."),
        },
        "rule_implementation_multiplicity": mult,
        "split_targets": splits,
        "matched_coverage_comparison": curves,
        "three_axis_independence_exposure": leak,
        "target_property_sets": props,
        "master_rq_answer": master_rq_answer(rows, mult, props, curves),
        "synthesis_questions": synthesis_answers(rows, mult, props, curves, leak),
        "smallest_sufficient_structure": smallest_sufficient(rows, curves, props),
        "recommended_experimental_candidates": cands,
        "counterexamples": counterexamples(rows, mult),
        "per_target": [{k: v for k, v in r.items()} for r in rows],
        "verdict": "PARTIALLY_SUPPORTED",
        "verdict_note": (
            "A~E 를 합치면 '무엇을 관측하면 무엇을 안다고 말할 수 있는가' 에 부분적으로만 답할 수 있다. "
            "확실히 답할 수 있는 것: (1) 현재 L0 landing 증거로 **업종 배정**은 상당 부분 되찾을 수 있고, "
            "(2) **대표기능**을 안다고 말할 근거는 이 표본 안에 없다 — 두 라벨이 전단사라 구분이 원리적으로 불가능하다. "
            "후보 architecture 3개는 모두 제출 가능하지만 셋 다 각각 다른 child 에게 반증당했고, "
            "셋이 공유하는 '규칙 먼저' 전제는 이 표본에서 지지되지 않는다."),
        "limitation": limitations(),
        "next_research_questions": next_questions(),
    }
    (RES / "RF2_F_cascade_candidates.json").write_text(
        json.dumps(doc, ensure_ascii=False, indent=1), encoding="utf-8")

    fig_decision_matrix(rows, cols, FIG / "RF2_F_decision_matrix.png")
    fig_agreement(am, mult, FIG / "RF2_F_agreement_matrix.png")
    fig_candidate_evidence(cands, FIG / "RF2_F_candidate_evidence.png")
    fig_coverage(curves, rows, FIG / "RF2_F_coverage_tradeoff.png")
    fig_leakage(leak, FIG / "RF2_F_leakage_exposure.png")
    fig_abstain_partition(props, FIG / "RF2_F_abstain_partition.png")

    print(json.dumps({
        "n": n,
        "union_determined": mult["union_determined_by_at_least_one"],
        "all_three": mult["determined_by_all_three"],
        "principled_abstain": props["principled_abstain_surface_absent"]["n"],
        "capture_only": props["wrong_kind_of_abstain_capture_defect_only"]["n"],
        "cascade_never_beats_sem_only": curves["cascade_never_beats_semantic_only_at_matched_coverage"],
        "candidates": [c["candidate_id"] for c in cands],
    }, ensure_ascii=False, indent=1))

    if not args.no_mlflow:
        log_mlflow(doc, rows, am, mult, curves, leak, props)
    return doc


def master_rq_answer(rows, mult, props, curves):
    n = len(rows)
    return {
        "question": "A~E 를 합치면 '무엇을 관측하면 무엇을 안다고 말할 수 있는가' 의 답은 무엇인가",
        "answer_in_one_paragraph": (
            "L0 landing snapshot 하나를 관측하면 **그 페이지가 지금 무엇을 하게 해 주는지에 대한 약한 증거**와 "
            "**그 서비스가 어느 업종인지에 대한 비교적 강한 증거**를 얻는다. 대표기능은 얻지 못한다. "
            "이 구분이 가능한 이유는 세 가지 관측이 같은 방향을 가리키기 때문이다 — "
            "(1) D-RF2-D 의 L1 이 확정한 7건 중 6건이 QUERY 로 흡수됐고 prior 가 QUERY 인 것은 1건뿐이다"
            "(랜딩에서 가장 완결된 affordance 가 검색창이기 때문이다), "
            "(2) D-RF2-A 에서 유일 STRONG 후보 = prior 인 target 이 56건 중 1건뿐이다, "
            "(3) D-RF2-C 에서 브랜드 문자열을 지우면 title 의 우위가 0.559→0.357 로 무너진다. "
            "그리고 D-FACT-01 때문에 (2)(3)의 '맞았다/틀렸다'는 전부 **업종 배정**에 대한 것이다. "
            "따라서 정직한 답은: **관측하면 업종을 알 수 있고, 랜딩이 제공하는 affordance 를 부분적으로 알 수 있으며, "
            "대표기능은 이 증거만으로는 알 수 없다.**"),
        "what_can_be_claimed": [
            "이 URL 이 렌더된 공개 web surface 를 갖는가 — Stage-0 로 결정적으로 판정 가능(56 중 5건이 NO).",
            "이 관측이 손상됐는가 — 인코딩·절단·오버레이·렌더희소는 결정적으로 관측된다(E 의 CAPTURE_QUALITY 계열).",
            "이 페이지가 어느 업종의 서비스인가 — semantic 순위로 상당 부분 되찾을 수 있다(단 그것이 전부다).",
            "이 페이지가 어떤 affordance 를 지금 제공하는가 — 부분적으로. 규칙 술어가 발화한 것만.",
        ],
        "what_cannot_be_claimed": [
            "이 서비스의 대표기능이 무엇인가 — prior 가 업종과 전단사라 이 표본으로는 원리적으로 검증 불가(D-FACT-01).",
            "어느 detector 가 더 나은가 — 세 rule 구현의 확정집합 Jaccard 가 0.043~0.190 이다. 비교의 기준선이 없다.",
            "어떤 threshold 가 옳은가 — calibration split 이 방화벽 밖이다.",
        ],
        "quantitative_anchor": {
            "targets_determined_by_at_least_one_rule_implementation": mult["union_determined_by_at_least_one"],
            "targets_determined_by_all_three": mult["determined_by_all_three"],
            "principled_abstain_n": props["principled_abstain_surface_absent"]["n"],
            "of_56": n,
        },
    }


def synthesis_answers(rows, mult, props, curves, leak):
    n = len(rows)
    det_any = props["deterministically_identifiable_union"]
    und = props["undetermined_by_every_rule_implementation"]
    return {
        "Q1_master": "master_rq_answer 참조.",
        "Q2_properties_of_deterministically_identifiable_targets": {
            "n": det_any["n"], "of": n,
            "answer": (
                "**결정적 증거만으로 식별 가능한 target 의 가장 두드러진 성질은 '그 성질이 target 이 아니라 "
                "lexicon 에 있다' 는 것이다.** 세 독립 rule 구현(A 13건 / D_flat 14건 / E_ruleDT 11건)의 "
                f"합집합은 {mult['union_determined_by_at_least_one']}건인데 교집합은 **{mult['determined_by_all_three']}건**이다. "
                f"Jaccard 는 0.043~0.190, pairwise kappa 는 −0.16~+0.13 으로 우연 수준이다. "
                "같은 SSOT §5·§6 를 어휘만 바꿔 구현하면 다른 target 집합이 열린다. "
                "그 위에서 관측되는 부차적 성질은: 텍스트가 충분히 있고(blob 토큰 중앙값 "
                f"{det_any['median_blob_tokens']} vs 미확정 {und['median_blob_tokens']}), "
                f"술어가 하나 이상 발화하며(E n_fired 중앙값 {det_any['median_E_n_fired']} vs {und['median_E_n_fired']}), "
                f"semantic margin 도 이미 높다(중앙값 {det_any['median_E_sem_margin']} vs {und['median_E_sem_margin']}). "
                "**즉 규칙이 닫는 target 은 semantic 도 이미 닫는 target 이다** — 이것이 Q5 의 답으로 이어진다."),
            "cross_check_A_D_E": {
                "A_unique_strong_matching_prior": "1/56 (D-RF2-A §14)",
                "D_flat_mapped": "14/56, prior 일치 5 (D-RF2-D §7)",
                "E_rule_mapped": "11/56, prior 일치 6 (D-RF2-E)",
                "multi_impl_cases": mult["multi_implementation_cases"],
                "reading": ("2개 이상이 확정한 6건 중 5건이 같은 leaf 를 낸다. 그런데 그 5건 중 4건이 "
                            "QUERY 이고 prior 는 ITEM_DETAIL/CONTENT_OPEN 이다 — D-RF2-D §11.2 의 "
                            "'랜딩에서 가장 완결된 affordance 는 검색창' 현상이 세 구현에서 독립적으로 재현된다."),
            },
            "prior_class_distribution": det_any["prior_archetype_distribution"],
        },
        "Q3_properties_of_targets_needing_semantic_evidence": {
            "n": props["needs_semantic_evidence"]["n"],
            "answer": (
                "semantic 을 더해야 하는 target 은 **표면이 관측됐고 손상도 없는데 술어가 배타적으로 발화하지 "
                "못한 target** 이다. E 의 유형으로 말하면 T02(한쪽 신호만, abstain 40 중 22 — 최대 유형)와 "
                "T03(다중 강후보 6)이다. 이들에서 semantic force-map 불일치는 T02 0.23 으로 rule 0.68 의 "
                "1/3 이다 — semantic 이 실제로 보탠다. "
                "**반대로 semantic 을 더해도 안 되는 것이 T03 이다**: rule 0.50 vs semantic 0.67 로 "
                "semantic 이 더 나쁘다. SSOT §6 이 다중후보를 §7 로 보내라고 규정했는데, "
                "이 표본에서 §7 이 그 6건을 더 못 가른다. n=6 이라 결론은 아니지만 "
                "**'semantic 이 ambiguity 를 푼다'는 전제가 검증되지 않았다는 사실 자체가 결과다.**"),
            "where_semantic_helps": "T02_WEAK_ONE_SIDED_EVIDENCE (n=22 in abstain 40): rule 0.68 → semantic 0.23 불일치",
            "where_semantic_does_not_help": "T03_MULTI_STRONG_CANDIDATE (n=6): rule 0.50 → semantic 0.67 불일치 (악화)",
            "where_semantic_is_misleading": ("T05_GENERIC_BRAND_LANDING — semantic 이 잘 맞지만 그건 업종을 맞힌 것이다. "
                                             "E: 표면부재 유형을 먼저 abstain 시키면 같은 coverage 에서 지표가 오히려 낮아진다."),
            "semantic_confidence_trap": props["semantic_confidence_trap"],
            "corrected_answer": (
                "위 trap 을 반영하면 Q3 의 답은 좁아진다. rule 이 전부 실패했는데 semantic margin 이 높은 "
                f"{props['semantic_confidence_trap']['n_semantic_confident_but_no_rule_fires']}건 중 "
                f"{props['semantic_confidence_trap']['of_which_surface_absent']}건이 **표면부재 target** 이고 "
                f"진짜로 정의상 애매해서 semantic 이 필요한 것은 "
                f"{props['semantic_confidence_trap']['of_which_genuinely_definition_ambiguous']}건뿐이다"
                f"({props['semantic_confidence_trap']['genuine_services']}). "
                "**즉 'semantic evidence 를 더해야 하는 target' 은 이 코호트에서 극소수다.** "
                "semantic 이 열어 주는 coverage 의 대부분은 대표기능이 아니라 업종을 읽어서 열린다."),
        },
        "Q4_principled_abstain": {
            "count_lower_bound": props["principled_abstain_surface_absent"]["n"],
            "count_including_definition_ambiguity": (props["principled_abstain_surface_absent"]["n"]
                                                     + props["residual_definition_ambiguity"]["n"]),
            "answer": (
                f"세 rule 구현이 모두 확정에 실패한 {und['n']}건을 원인으로 가르면: "
                f"**표면부재 {props['principled_abstain_surface_absent']['n']}건** "
                f"(그 중 T07 미렌더·error 5건, 그리고 {props['principled_abstain_surface_absent']['n']}건 중 10건은 "
                "관측손상까지 겹쳐 재수집해도 없는 표면이 생기지 않는다), "
                f"**관측손상만 {props['wrong_kind_of_abstain_capture_defect_only']['n']}건** (재수집 대상 — "
                "이것은 '미결정'이 아니라 '아직 안 봤다'이며 지금의 abstain 은 잘못된 종류다), "
                f"**둘 다 아닌 정의 문제 {props['residual_definition_ambiguity']['n']}건**. "
                f"따라서 **현재 evidence 로 원칙적으로 식별 불가능해서 ABSTAIN 이 정직한 target 은 "
                f"{props['principled_abstain_surface_absent']['n']}건(하한)** 이고, "
                "SSOT 정의를 고치지 않는 한 못 푸는 것까지 포함하면 "
                f"{props['principled_abstain_surface_absent']['n'] + props['residual_definition_ambiguity']['n']}건이다. "
                "이유는 detector 결함이 아니라 **target URL 이 그 서비스의 기능면이 아니라 그것을 설명하는 면**이기 "
                "때문이다 — E 의 처방은 detector 개선이 아니라 target URL 감사다."),
            "why_not_a_detector_problem": (
                "E 의 관측: 탑마트→seowon.com, 카카오T→kakaomobility.com/service-kakaot 처럼 요청 URL 이 "
                "브랜드 소개면으로 해석된 사례가 반복된다. 같은 URL 에서 더 정교하게 관측해도 없는 표면은 생기지 않는다."),
            "caveat": ("E limitation 4번 — 해결가능성 판정은 반사실 주장이다. 재수집 실험 없이는 "
                       "'관측손상 9건이 풀린다'도 '표면부재 14건이 안 풀린다'도 검증되지 않았다."),
            "sets": {
                "principled_abstain_services": props["principled_abstain_surface_absent"]["services"],
                "capture_defect_only_services": props["wrong_kind_of_abstain_capture_defect_only"]["services"],
                "definition_ambiguity_services": props["residual_definition_ambiguity"]["services"],
            },
        },
        "Q5_smallest_sufficient_structure": "smallest_sufficient_structure 참조.",
    }


def smallest_sufficient(rows, curves, props):
    n = len(rows)
    rm = [r for r in rows if r["E_det"]]
    return {
        "question": "최소한의 evidence · 최소한의 단계로 어디까지 갈 수 있는가",
        "answer": (
            "**두 단계면 된다: (1) evidence admissibility 게이트, (2) 하나의 텍스트 representation 위의 "
            "7-prototype 유사도 + margin 게이트.** archetype 을 고르는 규칙 트리는 이 표본에서 "
            "그 위에 아무것도 얹지 못한다 — 같은 coverage 로 맞추면 rule-first cascade 가 semantic-only 를 "
            "한 번도 이기지 못하고(모든 대조점에서 Δ ≤ 0), rule 이 실제로 확정한 11건에서 "
            "McNemar b=0 (규칙이 맞고 semantic 이 틀린 target 이 0건), c=2 다. "
            "evidence 쪽 최소치도 작다 — C 에 따르면 `identity`(title + meta_description + url_tokens, "
            "중앙값 29토큰)가 `text_blob`(498토큰)과 같은 prior_agreement 38/56 를 내고 macro F1 은 더 높다. "
            "**토큰을 17배 줄여도 손해가 없다.**"),
        "the_catch": (
            "이 '최소 충분구조'가 충분한 것은 **업종 배정 재현율**에 대해서다(D-FACT-01). "
            "그리고 identity 로 좁힐수록 C 가 경고한 순환 — title/url 이 브랜드를 읽고 브랜드→업종→archetype 을 "
            "되짚는 경로 — 이 강해진다. C 의 브랜드 마스킹에서 `url_tokens` 0.361→0.138, `title` 0.559→0.357 이다. "
            "**따라서 최소 충분구조는 '가장 작다'와 '가장 순환적이다'가 같은 방향이다.** "
            "독립 label 없이 이 구조를 채택하면 업종 분류기를 대표기능 detector 라고 부르게 된다. "
            "더 구체적으로: 규칙이 전부 실패했는데 semantic 이 확신하는 14건 중 10건이 표면부재 target 이다"
            "(`synthesis_questions.Q3...semantic_confidence_trap`). semantic 단계가 벌어들이는 coverage 의 "
            "상당 부분이 **대표 기능면이 아닌 페이지에서** 나온다."),
        "minimum_viable_stack": [
            {"stage": 1, "name": "Stage-0 renderability", "kind": "deterministic",
             "why": "SSOT §2 가 이미 확정을 금지한다. 이 코호트 56 중 5건이 여기서 걸린다.",
             "cost": "거의 0"},
            {"stage": 2, "name": "evidence-defect gate (인코딩 · cap · 오버레이 · 렌더희소)", "kind": "deterministic",
             "why": ("E: 강제선택 불일치율이 인코딩 손상에서 1.00 이다. 이 게이트가 없으면 "
                     "수집 결함이 연구결과로 세탁된다."),
             "cost": "관측표 플래그 4개. 이미 전부 관측되고 있다."},
            {"stage": 3, "name": "one text representation × 7 frozen prototypes × margin gate", "kind": "semantic",
             "why": "coverage 를 얻는 유일한 단계. 학습 없음, 모델 1개.",
             "cost": "provenance 상실. threshold 는 calibration split 없이는 못 정한다."},
        ],
        "what_the_rule_tree_is_still_for": (
            "**버리라는 말이 아니다.** 규칙은 이 표본에서 archetype 선택에는 기여하지 않았지만 "
            "(a) provenance — 어느 field 의 어느 어휘가 발화했는지, (b) 반증 가능성 — D-RF2-D 가 "
            "'병목은 L1' 이라고 말할 수 있었던 것은 규칙이 있었기 때문, (c) prior 와 구조의 불일치 관측"
            "(E 의 T13 17건)을 제공한다. semantic-only 구조에는 이 세 가지가 전부 없다."),
        "observed_numbers": {
            "rule_only_coverage": [len(rm), n],
            "rule_only_prior_agreement": round(sum(1 for r in rm if r["E_pred"] == r["prior_archetype"]) / len(rm), 4),
            "semantic_only_curve_first_8": curves["curve"][:8],
            "cascade_never_wins": curves["cascade_never_beats_semantic_only_at_matched_coverage"],
        },
    }


def counterexamples(rows, mult):
    out = []
    tri = mult["determined_by_all_three_detail"]
    if tri:
        t = tri[0]
        out.append({
            "kind": "세 구현이 모두 확정한 유일한 target — 그런데 prior 와 불일치",
            "detail": t,
            "reading": ("'세 구현이 합의하면 믿을 만하다'는 직관의 반례다. 세 독립 lexicon 이 모두 "
                        "QUERY 로 닫았는데 prior 는 ITEM_DETAIL 이다. 합의는 타당성이 아니라 "
                        "'랜딩에서 검색창이 가장 완결된 affordance' 라는 같은 편향의 공유일 수 있다."),
        })
    out.append({
        "kind": "이 종합 자신의 결론에 대한 반례 — semantic-only 가 이기는 이유가 나쁜 이유다",
        "detail": ("D-RF2-F: 규칙이 전부 실패했는데 semantic margin 이 높은 14건 중 10건이 표면부재 target"
                   "(Chrome · GS25 · NH스마트뱅킹 · NH콕뱅크 · emart24 · 디바이스 케어 · 롯데하이마트 · "
                   "마켓컬리 · 신한 SOL뱅크 · 캐시워크)이다."),
        "reading": ("§'가장 작은 충분구조' 가 semantic-only 로 기운 근거는 coverage×prior_agreement 곡선인데, "
                    "그 곡선이 좋아지는 구간의 상당 부분이 브랜드면이다. "
                    "**이 반례는 이 문서가 semantic-only 를 추천하지 않는 이유이기도 하다** — "
                    "D 는 후보를 제시하고 대가를 적을 뿐 순위를 매기지 않는다."),
    })
    out.append({
        "kind": "semantic 이 규칙보다 항상 나은 것은 아니다",
        "detail": "D-RF2-E: T03_MULTI_STRONG_CANDIDATE 6건에서 semantic 불일치 0.67 > rule 0.50",
        "reading": "SSOT §6 → §7 캐스케이드의 핵심 전제(§7 이 다중후보를 가른다)가 이 표본에서 반증 방향이다.",
    })
    out.append({
        "kind": "표면부재를 먼저 걸러내면 지표가 나빠진다",
        "detail": "D-RF2-E: T05/T06/T07 을 먼저 abstain 시킨 캐스케이드는 같은 coverage 에서 prior_agreement 가 낮다",
        "reading": ("올바른 처방이 지표를 떨어뜨린다. 지표가 대표기능이 아니라 업종을 재고 있기 때문이다"
                    "(D-FACT-01). **이 반례는 지표 자체를 반증한다.**"),
    })
    out.append({
        "kind": "control 표면이 이기는 2건",
        "detail": ("D-RF2-C §11: TikTok(prior CONTENT_OPEN — blob 은 COMMUNICATION_ENTRY, "
                   "controls 는 CONTENT_OPEN), 네이버(prior QUERY — blob 은 ITEM_DETAIL, controls 는 QUERY)"),
        "reading": ("H3 의 field-specific 발상이 23:2 로 졌지만 0:25 는 아니다. "
                    "네이버 첫 화면 전체 텍스트는 쇼핑·뉴스 카드로 덮여 ITEM_DETAIL 로 끌려가는데 "
                    "검색 버튼의 aria-label 은 QUERY 를 정확히 가리킨다. "
                    "'controls 가 무의미하다'는 반대 극단도 틀렸다."),
    })
    out.append({
        "kind": "어떤 유형으로도 설명되지 않는 잔여",
        "detail": "D-RF2-E: 컴포즈커피 1건 — blob 19토큰, dom_body_empty=0, 인코딩 정상인데 아무 유형에도 안 걸린다",
        "reading": "abstention taxonomy 의 완결성 상한. REAL_TARGET 규모에서 이 잔여가 몇 %인지는 미지수다.",
    })
    return out


def limitations():
    return [
        ("**가장 무겁다 — 이 종합의 모든 정량 대조가 prior 를 기준으로 한다.** D-FACT-01 에 따라 "
         "prior_archetype 은 prior_business_domain 과 전단사이므로 모든 수치는 업종 배정 재현율이다. "
         "'semantic-only 가 cascade 를 이긴다'는 **업종을 더 잘 되찾는다**는 뜻이며, 대표기능에 대해서는 "
         "어느 후보가 나은지 이 표본으로 **원리적으로** 말할 수 없다. 후보 선택은 gold label 없이 닫히지 않는다."),
        ("이 문서는 새 실험을 하지 않았다. A~E 의 산출물을 교차 종합한 2차 분석이며, "
         "각 child 의 조작화(어휘사전·임계·prototype·유형 판정식)를 그대로 상속한다. "
         "그 조작화가 틀렸다면 이 종합도 같이 틀린다."),
        ("세 rule 구현의 낮은 일치도(kappa −0.16~+0.13)는 '규칙이 나쁘다'가 아니라 "
         "'세 구현이 서로 다르다'는 관측이다. 어느 구현이 SSOT §5 를 더 충실히 조작화했는지 "
         "D 는 판정할 수 없다 — 판정하려면 SSOT 해석의 권위가 필요하고 그것은 A 에 있다."),
        ("n=56, 7 class 중 5개가 n≤5. 모든 하위집합 수치의 Wilson CI 가 넓다. "
         "후보 간 coverage 차이는 대부분 CI 가 겹친다."),
        ("semantic 축 수치는 E 가 독립 재계산한 bge-m3 × A_SSOT_DEF × text_blob 하나에 의존한다. "
         "C 는 e5-small 에서 field 효과가 prototype 노이즈에 묻힌다고 보고했다 — 모델을 바꾸면 결론이 흔들린다."),
        ("leakage 노출 phi 는 n=56 에서 잡음 규모 ±0.13 과 겹친다. **후보 간 상대 비교로만** 읽어야 하고, "
         "'H3 가 위험하다'는 정량 확증이 아니라 C 의 정성 경고에 방향이 일치한다는 관측이다."),
        ("E 의 해결가능성 판정(RESOLVABLE / UNDECIDABLE)은 반사실 주장이며 재수집 실험 전에는 가설이다. "
         "Q4 의 '원칙적 ABSTAIN 14건' 은 그 가설 위에 서 있다."),
        ("endpoint 를 정적 presence 로 강등한 것이 A·D·E 세 구현에 공통으로 들어 있다. "
         "이 강등은 coverage 를 낙관적으로 올리는 방향이며, 상호작용 기반 endpoint 로는 "
         "세 구현 모두 coverage 가 줄고 no-evidence 가 는다."),
        "이 문서는 production threshold 를 정하지 않았고 GO/NO-GO 를 내지 않았으며 best model 을 고르지 않았다.",
    ]


def next_questions():
    return [
        {"id": "RQ-D-RF-002-f1",
         "q": ("세 rule 구현의 확정집합이 거의 겹치지 않는다(J 0.043~0.190). 이 불일치를 lexicon 축으로 "
               "분해할 수 있는가 — 세 구현의 어휘 교집합만으로 규칙을 다시 세우면 확정집합은 어떻게 되는가?"),
         "why": "'결정 가능한 target' 이 lexicon 의 성질인지 target 의 성질인지를 가르는 직접 실험."},
        {"id": "RQ-D-RF-002-f2",
         "q": ("prior 가 아닌 기준으로 후보를 비교할 수 있는가 — representation·모델·prototype 을 바꿔도 "
               "예측이 안 바뀌는 target 집합(stability)을 기준으로 삼으면 D-FACT-01 을 우회할 수 있는가?"),
         "why": "D-SUP-01 이 이미 이 방향으로 갔다. 후보 비교의 유일한 prior-free 경로일 수 있다."},
        {"id": "RQ-D-RF-002-f3",
         "q": "규칙 단계를 뺐을 때 실제로 잃는 것(provenance · 반증가능성 · prior-구조 불일치 관측)을 정량화할 수 있는가?",
         "why": "Q5 의 '최소 충분구조' 는 지표상 손해가 없지만 관측력에서는 손해다. 그 손해가 얼마인지는 안 쟀다."},
        {"id": "RQ-D-RF-002-f4",
         "q": ("업종 어휘까지 마스킹한 조건에서 semantic 이 남기는 신호는 무엇인가? "
               "(C 의 최우선 후속질문. 브랜드 문자열만 지운 절제는 조악하다.)"),
         "why": "'semantic 인가 identity 인가' 를 닫는 유일한 D-내부 경로."},
        {"id": "RQ-D-RF-002-f5",
         "q": "표면부재 14건의 target URL 을 재정의하면 몇 건이 확정 가능해지는가? (E 의 target URL 감사)",
         "why": "coverage 를 올리는 첫 시도가 detector 개선이 아니라 모집단 정의라는 주장의 검증."},
        {"id": "RQ-D-RF-002-f6",
         "q": ("접근성 표면을 분류 feature 에서 완전히 배제한 detector 와 포함한 detector 를 같은 코호트에서 "
               "돌렸을 때, KWCAG 축 점수와 detector abstention 의 상관이 실제로 갈리는가?"),
         "why": "세 축 독립 위반은 현재 phi 관측(잡음 규모와 겹침)뿐이다. 설계된 대조가 필요하다."},
    ]


def log_mlflow(doc, rows, am, mult, curves, leak, props):
    sys.path.insert(0, str(RD / "tools"))
    import mlflow
    import mlflow_contract as C

    res = RES / "RF2_F_cascade_candidates.json"
    lim = doc["limitation"][0]
    with C.research_run(
            experiment="LA_03_RF_MAPPING", run_name="D-RF2-F cascade candidate synthesis",
            plane="D", agent_id="D", subagent_id="worker/D-RF2-F",
            objective="A~E 를 종합해 2~3개 candidate measurement architecture 를 조건과 대가와 함께 제시",
            method="child 결과 교차 종합 + 후보별 지지/반증 증거 매핑 + 판정 일치행렬",
            dataset_grain="target (in_mart==1), n=56",
            n_expected=56, n_observed=56,
            hypothesis_id=HYP,
            competing_hypothesis="H1 rule-only / H2 rule+semantic+margin abstain / H3 hierarchical+field-specific",
            claim_kind="ANALYSIS", ticket_id="NONE", phase="I1", split="none",
            parent_run_id=PARENT_RUN,
            result_path=res,
            model_or_rule_version=VERSION, seed=SEED,
            code_path=Path(__file__),
            notebook="RF2_F_cascade_synthesis.ipynb",
            extra_tags={"mlflow.parentRunId": PARENT_RUN, "rq_id": RQ_ID, "child_id": CHILD_ID,
                        "best_model_selected": "false",
                        "output_kind": "RECOMMENDED_EXPERIMENTAL_CANDIDATES"}) as run:
        m = {
            "n_targets": len(rows),
            "union_determined_by_any_rule_impl": mult["union_determined_by_at_least_one"],
            "determined_by_all_three_rule_impls": mult["determined_by_all_three"],
            "n_candidates_emitted": len(doc["recommended_experimental_candidates"]),
            "principled_abstain_n": props["principled_abstain_surface_absent"]["n"],
            "capture_defect_only_abstain_n": props["wrong_kind_of_abstain_capture_defect_only"]["n"],
            "definition_ambiguity_abstain_n": props["residual_definition_ambiguity"]["n"],
            "n_split_targets": len(doc["split_targets"]),
        }
        for p in am["pairs"]:
            k = p["cohen_kappa"]
            if k is not None and not (isinstance(k, float) and math.isnan(k)):
                m[f"kappa {p['a']} vs {p['b']}"] = k
            if p["jaccard_determined"] is not None:
                m[f"jaccard {p['a']} vs {p['b']}"] = p["jaccard_determined"]
        for k, v in mult["per_implementation_prior_agreement"].items():
            m[f"domain_recall {k}"] = v["prior_agreement"] or 0.0
            m[f"coverage {k}"] = v["n_determined"] / len(rows)
        for c in curves["curve"]:
            if c["coverage_n"] in (56, 44, 36, 28, 20):
                m[f"domain_recall semantic_only cov{c['coverage_n']}"] = c["semantic_only_prior_agreement"]
                m[f"domain_recall cascade cov{c['coverage_n']}"] = c["rule_first_cascade_prior_agreement"]
        for name, v in leak.items():
            if name.startswith("_"):
                continue
            m[f"leak phi_aria {name}"] = v["phi_determined_vs_aria_labels_empty"]
        mlflow.log_metrics({k: float(v) for k, v in m.items()})
        mlflow.log_param("d_fact_01", "prior_archetype == prior_business_domain (nMI=1.000, 56/56)")
        mlflow.log_param("metric_semantics", "prior_agreement = business-domain assignment recall, NOT accuracy")
        mlflow.log_artifact(str(res))
        for f in sorted(FIG.glob("RF2_F_*.png")):
            mlflow.log_artifact(str(f), artifact_path="figures")
        mlflow.log_text(json.dumps(doc["recommended_experimental_candidates"], ensure_ascii=False, indent=1),
                        "recommended_experimental_candidates.json")
        mlflow.log_text("\n".join(f"- {x}" for x in doc["limitation"]), "limitation_full.md")
        C.finish(verdict=doc["verdict"], limitation=lim)
        # 결과 파일은 내가 쓸 파일 목록 밖으로 늘리지 않는다. run_id 는 stdout 과
        # FINDINGS / notebook 에만 남긴다.
        print("mlflow run_id:", run.info.run_id)


if __name__ == "__main__":
    main()
