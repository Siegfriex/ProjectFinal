"""RQ-D12 — D 의 발견들이 같은 target 에 몰려 있는가.

파생 근거: D 는 서로 다른 RQ 에서 각기 다른 '측정 곤란' 신호를 찾았다.
cap 절단(D8) · 구조 빈약(D9) · slot 시점 불일치(D10) · 퇴화 캡처/URL 중복(D13) ·
overlay construct 불일치(D13a) · frame 미결정(D14) · rule abstain(RF001-A).

RQ: 이 신호들이 **같은 소수 target 에 집중**되는가, 아니면 서로 다른 target 을 가리키는가?

경쟁가설
  H1 SINGLE_LATENT   하나의 '어려운 target' 잠재요인이 대부분을 설명한다 (신호들이 강하게 공기)
  H2 INDEPENDENT     신호들이 서로 다른 축이라 독립에 가깝다 (각각 별개 문제)
  H3 CLUSTERED_PAIRS 몇 쌍만 강하게 묶이고 나머지는 독립이다

이 답이 중요한 이유: H1 이면 소수 target 을 제외하는 것으로 측정 품질이 크게 오르고
missingness 를 하나의 요인으로 모델링할 수 있다. H2 면 각 문제를 따로 고쳐야 하고
어떤 제외도 나머지를 낫게 하지 않는다.

read-only. 산출: results/RQ_D12_difficulty_concentration.json
"""
from __future__ import annotations

import csv
import json
import random
from collections import Counter, defaultdict
from itertools import combinations
from pathlib import Path

RD = Path(__file__).resolve().parents[1]
RES = RD / "results"
SEED = 20260827


def load(name: str):
    p = RES / name
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None


def phi(a: list[int], b: list[int]) -> float:
    n11 = sum(1 for x, y in zip(a, b) if x and y)
    n10 = sum(1 for x, y in zip(a, b) if x and not y)
    n01 = sum(1 for x, y in zip(a, b) if not x and y)
    n00 = sum(1 for x, y in zip(a, b) if not x and not y)
    den = ((n11 + n10) * (n01 + n00) * (n11 + n01) * (n10 + n00)) ** 0.5
    return round((n11 * n00 - n10 * n01) / den, 4) if den else 0.0


def jaccard(a: list[int], b: list[int]) -> float:
    inter = sum(1 for x, y in zip(a, b) if x and y)
    union = sum(1 for x, y in zip(a, b) if x or y)
    return round(inter / union, 4) if union else 0.0


def main() -> int:
    rows = [r for r in csv.DictReader((RES / "D_OBSERVATION_TABLE_v2.csv").open(encoding="utf-8"))
            if r["in_mart"] == "1"]
    tgt = {r["wtg"]: r for r in rows}
    order = sorted(tgt)

    d13 = load("RQ_D13_duplicate_vector.json") or {}
    d13a = load("RQ_D13A_overlay_provenance.json") or {}
    d14 = load("RQ_D14_frame_validity.json") or {}
    d10 = load("RQ_D10_slot_mismatch.json") or {}
    rf1a = load("RF001_A_rule_dt.json") or {}

    degenerate = {d["wtg"] for d in d13.get("degenerate_captures", [])}
    url_dup = {w for g in d13.get("url_level_duplicates", []) for w in g["wtgs"]}
    overlay_generic = {r["wtg"] for r in d13a.get("records", [])
                       if str(r.get("classification", "")).startswith("H2_GENERIC")}
    identity = {r["wtg"]: r.get("identity_class") for r in d14.get("per_target", [])}
    slot = {o["wtg"]: o for o in d10.get("observations", []) if o.get("in_mart") in (1, True, "1")}
    abstain = {l["target_id"].replace("wtg_", ""): l for l in rf1a.get("leaves", [])}

    # 곤란 신호 7종. 각 정의를 전문 공개한다. 결과를 보고 정의를 바꾸지 않는다.
    FLAG_DEFS = {
        "cap_truncated": "probe 배열이 하드 cap 에 도달 (D_OBSERVATION_TABLE_v2.cap_any==1)",
        "low_structural_richness": "dom_interactive_n 이 in_mart 표본의 하위 25% (D9 권고 proxy)",
        "slot_mismatch": "D10 의 slot_disagreement_score >= 1",
        "degenerate_or_dup": "D13 의 퇴화 캡처이거나 동일 요청 URL 중복 쌍",
        "overlay_construct_mismatch": "D13a 에서 최대 overlay 요소가 모달이 아님 (H2_GENERIC*)",
        "frame_not_functional": "D14 identity_class 가 FUNCTIONAL_LANDING 이 아님",
        "rule_abstain": "RF001-A rule DT 가 유일 leaf 를 못 만듦 (leaf != MAPPED)",
    }
    ints = sorted(int(r["dom_interactive_n"] or 0) for r in rows)
    q25 = ints[max(0, len(ints) // 4 - 1)]

    flags: dict[str, dict[str, int]] = {}
    for w in order:
        r = tgt[w]
        leaf = (abstain.get(w) or {}).get("leaf")
        flags[w] = {
            "cap_truncated": int(r.get("cap_any") == "1"),
            "low_structural_richness": int(int(r["dom_interactive_n"] or 0) <= q25),
            "slot_mismatch": int(((slot.get(w) or {}).get("slot_disagreement_score") or 0) >= 1),
            "degenerate_or_dup": int(w in degenerate or w in url_dup),
            "overlay_construct_mismatch": int(w in overlay_generic),
            "frame_not_functional": int(identity.get(w) not in (None, "FUNCTIONAL_LANDING")),
            "rule_abstain": int(bool(leaf) and (leaf.startswith("AMBIGUOUS")
                                                 or leaf.startswith("UNDETERMINED"))),
        }
    names = list(FLAG_DEFS)
    vec = {f: [flags[w][f] for w in order] for f in names}
    prevalence = {f: sum(vec[f]) for f in names}

    pair = {}
    for a, b in combinations(names, 2):
        pair[f"{a}|{b}"] = {"phi": phi(vec[a], vec[b]), "jaccard": jaccard(vec[a], vec[b]),
                            "both": sum(1 for x, y in zip(vec[a], vec[b]) if x and y)}

    counts = {w: sum(flags[w].values()) for w in order}
    dist = Counter(counts.values())

    # 집중도 검정: 각 flag 의 개수를 유지한 채 무작위 재배치했을 때
    # '3개 이상 flag 를 가진 target 수' 가 관측값만큼 나오는가
    rng = random.Random(SEED)
    obs_ge3 = sum(1 for v in counts.values() if v >= 3)
    obs_var = None
    vals = list(counts.values())
    mean = sum(vals) / len(vals)
    obs_var = sum((v - mean) ** 2 for v in vals) / len(vals)
    null_ge3, null_var = [], []
    for _ in range(5000):
        shuffled = {f: rng.sample(vec[f], len(order)) for f in names}
        c = [sum(shuffled[f][i] for f in names) for i in range(len(order))]
        null_ge3.append(sum(1 for v in c if v >= 3))
        m = sum(c) / len(c)
        null_var.append(sum((v - m) ** 2 for v in c) / len(c))
    p_ge3 = sum(1 for v in null_ge3 if v >= obs_ge3) / len(null_ge3)
    p_var = sum(1 for v in null_var if v >= obs_var) / len(null_var)

    # prevalence 가 높은 flag 는 거의 모두에게 붙어 '집중' 을 만들어낸다.
    # 60% 미만 flag 만으로 제한한 분석을 병기해 그 효과를 분리한다.
    restricted = [f for f in names if prevalence[f] / len(order) < 0.60]
    rcounts = {w: sum(flags[w][f] for f in restricted) for w in order}
    rvals = list(rcounts.values()); rmean = sum(rvals) / len(rvals)
    rvar = sum((v - rmean) ** 2 for v in rvals) / len(rvals)
    rng2 = random.Random(SEED + 1)
    rnull = []
    for _ in range(5000):
        sh = {f: rng2.sample(vec[f], len(order)) for f in restricted}
        c = [sum(sh[f][i] for f in restricted) for i in range(len(order))]
        m = sum(c) / len(c)
        rnull.append(sum((v - m) ** 2 for v in c) / len(c))
    rp = sum(1 for v in rnull if v >= rvar) / len(rnull)

    top = sorted(counts.items(), key=lambda kv: -kv[1])[:10]
    clean = [w for w, v in counts.items() if v == 0]

    strong_pairs = sorted(pair.items(), key=lambda kv: -abs(kv[1]["phi"]))[:6]
    max_phi = abs(strong_pairs[0][1]["phi"]) if strong_pairs else 0.0
    # 판정은 제한분석 기준으로 한다. 고빈도 flag 가 만든 집중은 실제 집중이 아니다.
    if 'rp' in dir() and rp < 0.05 and max_phi >= 0.5:
        verdict = "SUPPORTED"          # H1 단일 잠재요인 쪽
    elif p_var < 0.05:
        verdict = "PARTIALLY_SUPPORTED"
    else:
        verdict = "REFUTED"            # 집중 없음 = H2 독립

    out = {
        "rq": "RQ-D12",
        "title": "D 의 측정곤란 신호들이 같은 target 에 몰려 있는가",
        "competing_hypotheses": {
            "H1_SINGLE_LATENT": "하나의 '어려운 target' 요인이 대부분 설명",
            "H2_INDEPENDENT": "신호들이 서로 다른 축, 독립에 가까움",
            "H3_CLUSTERED_PAIRS": "몇 쌍만 묶이고 나머지는 독립",
        },
        "why_it_matters": ("H1 이면 소수 제외로 품질이 오르고 missingness 를 한 요인으로 모델링할 수 있다. "
                           "H2 면 각 문제를 따로 고쳐야 하고 어떤 제외도 나머지를 낫게 하지 않는다."),
        "grain": "target (in_mart==1)",
        "n": len(order),
        "seed": SEED,
        "flag_definitions": FLAG_DEFS,
        "low_richness_q25_threshold": q25,
        "prevalence": prevalence,
        "pairwise": pair,
        "strongest_pairs": [{"pair": k, **v} for k, v in strong_pairs],
        "flag_count_distribution": dict(sorted(dist.items())),
        "n_targets_ge3_flags": obs_ge3,
        "permutation_test": {
            "B": 5000,
            "observed_n_ge3": obs_ge3, "p_n_ge3": round(p_ge3, 4),
            "observed_variance_of_flag_count": round(obs_var, 4), "p_variance": round(p_var, 4),
            "null_hypothesis": "각 flag 의 개수를 유지한 채 target 에 무작위 배정",
        },
        "most_flagged_targets": [{"wtg": w, "service": tgt[w]["prior_service"],
                                  "archetype": tgt[w]["prior_archetype"], "n_flags": v,
                                  "flags": [f for f in names if flags[w][f]]} for w, v in top],
        "clean_targets_n": len(clean),
        "restricted_analysis": {
            "note": "prevalence >= 60% 인 flag 는 거의 모두에게 붙어 집중도를 부풀린다. 제외한 분석.",
            "flags_used": restricted,
            "flag_count_distribution": dict(sorted(Counter(rcounts.values()).items())),
            "observed_variance": round(rvar, 4), "p_variance": round(rp, 4),
            "clean_targets_n": sum(1 for v in rcounts.values() if v == 0),
        },
        "verdict": verdict,
        "per_target_flags": {w: flags[w] for w in order},
    }
    (RES / "RQ_D12_difficulty_concentration.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")

    print(f"n={len(order)} targets, flags={len(names)}")
    print("prevalence:", prevalence)
    print("flag 개수 분포:", dict(sorted(dist.items())))
    print(f"flag>=3 target: {obs_ge3}  (permutation p={p_ge3:.4f})")
    print(f"flag 개수 분산 {obs_var:.3f}  (permutation p={p_var:.4f})")
    print("가장 강하게 묶인 쌍:")
    for k, v in strong_pairs:
        print(f"  {k:<58} phi={v['phi']:+.3f} jaccard={v['jaccard']:.3f} both={v['both']}")
    print(f"flag 0 개인 target: {len(clean)}/{len(order)}")
    print(f"[제한분석] prevalence<60% flag {restricted}")
    print(f"[제한분석] 분포={dict(sorted(Counter(rcounts.values()).items()))} 분산={rvar:.3f} p={rp:.4f} "
          f"clean={sum(1 for v in rcounts.values() if v == 0)}/{len(order)}")
    print(f"verdict = {verdict}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
