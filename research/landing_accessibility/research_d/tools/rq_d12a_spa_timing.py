"""RQ-D12a — 구조빈약·slot불일치·퇴화 세 신호가 정말 하나의 원인(SPA 렌더 시점)인가.

파생 근거: RQ-D12 F2 — 이 세 flag 만 서로 묶였다
(low_structural_richness ↔ degenerate_or_dup phi +0.459, ↔ slot_mismatch +0.442).
그때 나는 "셋 다 SPA 렌더 시점 문제와 방향이 같다" 고 **추측**했다. 그 추측을 가른다.

경쟁가설
  H1 SPA_TIMING   셋 다 'DOM slot 이 렌더 전에 캡처됨' 의 하위현상이다
  H2 DISTINCT     서로 다른 원인이다 (구조빈약은 진짜 빈약한 페이지, 퇴화는 수집 실패)
  H3 MIXED        일부는 SPA 시점, 일부는 진짜 빈약

**판별 증거**: SPA 시점 문제라면 DOM 은 빈약한데 **probe(렌더 후)는 풍부**해야 한다.
진짜 빈약한 페이지라면 DOM 도 probe 도 둘 다 빈약하다. 이 두 갈래를 나눈다.

    signature_SPA      = DOM 빈약 AND probe 풍부
    signature_SPARSE   = DOM 빈약 AND probe 빈약

read-only. 산출: results/RQ_D12A_spa_timing.json
"""
from __future__ import annotations

import csv
import json
import statistics as st
from collections import Counter
from pathlib import Path

RD = Path(__file__).resolve().parents[1]
RES = RD / "results"


def main() -> int:
    rows = [r for r in csv.DictReader((RES / "D_OBSERVATION_TABLE_v2.csv").open(encoding="utf-8"))
            if r["in_mart"] == "1"]
    d12 = json.loads((RES / "RQ_D12_difficulty_concentration.json").read_text())
    d10 = json.loads((RES / "RQ_D10_slot_mismatch.json").read_text())
    flags = d12["per_target_flags"]
    slot = {o["wtg"]: o for o in d10["observations"]}

    def num(r, k, default=0.0):
        v = r.get(k)
        try:
            return float(v)
        except (TypeError, ValueError):
            return default

    # 빈약/풍부 절단점은 in_mart 표본의 중앙값. RQ-D12 의 q25 와 다른 기준을 쓰는 이유는
    # 여기서는 '어느 쪽이 더 풍부한가' 의 상대 비교이지 곤란도 flag 재현이 아니기 때문이다.
    dom_vals = sorted(num(r, "dom_interactive_n") for r in rows)
    probe_vals = sorted(num(r, "n_primary_action_candidates") for r in rows if r["probe_present"] == "1")
    dom_med = st.median(dom_vals)
    probe_med = st.median(probe_vals)

    recs = []
    for r in rows:
        w = r["wtg"]
        s = slot.get(w, {})
        dom_i = num(r, "dom_interactive_n")
        probe_p = num(r, "n_primary_action_candidates") if r["probe_present"] == "1" else None
        dom_poor = dom_i <= dom_med
        probe_rich = probe_p is not None and probe_p > probe_med
        probe_poor = probe_p is not None and probe_p <= probe_med
        if probe_p is None:
            sig = "NO_PROBE"
        elif dom_poor and probe_rich:
            sig = "SIGNATURE_SPA"
        elif dom_poor and probe_poor:
            sig = "SIGNATURE_SPARSE"
        elif not dom_poor and probe_rich:
            sig = "BOTH_RICH"
        else:
            sig = "DOM_RICH_PROBE_POOR"
        recs.append({
            "wtg": w, "service": r["prior_service"], "archetype": r["prior_archetype"],
            "dom_interactive_n": dom_i, "probe_primary_n": probe_p,
            "dom_body_fill": s.get("dom_body_fill"),
            "elapsed_dom_to_probe_s": s.get("slot_elapsed_dom_to_probe_s"),
            "probe_ans_n": s.get("probe_ans_n"), "dom_ans_n": s.get("dom_ans_n"),
            "signature": sig,
            "f_low_richness": flags.get(w, {}).get("low_structural_richness"),
            "f_slot_mismatch": flags.get(w, {}).get("slot_mismatch"),
            "f_degenerate": flags.get(w, {}).get("degenerate_or_dup"),
        })

    sig_all = Counter(x["signature"] for x in recs)
    # 세 flag 각각이 어떤 signature 에 몰리는가
    per_flag = {}
    for f in ("f_low_richness", "f_slot_mismatch", "f_degenerate"):
        sel = [x for x in recs if x[f]]
        per_flag[f] = {"n": len(sel), "by_signature": dict(Counter(x["signature"] for x in sel)),
                       "wtgs": [x["wtg"] for x in sel]}

    low = [x for x in recs if x["f_low_richness"]]
    low_spa = [x for x in low if x["signature"] == "SIGNATURE_SPA"]
    low_sparse = [x for x in low if x["signature"] == "SIGNATURE_SPARSE"]

    # 판정: 구조빈약 flag 안에서 SPA signature 가 지배하면 H1, SPARSE 가 지배하면 H2
    if low and len(low_spa) / len(low) >= 0.7:
        verdict = "SUPPORTED"      # H1
    elif low and len(low_sparse) / len(low) >= 0.7:
        verdict = "REFUTED"        # H2
    else:
        verdict = "PARTIALLY_SUPPORTED"   # H3

    elapsed_by_sig = {}
    for s_ in sorted(sig_all):
        vals = [x["elapsed_dom_to_probe_s"] for x in recs
                if x["signature"] == s_ and isinstance(x["elapsed_dom_to_probe_s"], (int, float))]
        elapsed_by_sig[s_] = {"n": len(vals),
                              "median_s": round(st.median(vals), 3) if vals else None}

    out = {
        "rq": "RQ-D12a",
        "title": "구조빈약·slot불일치·퇴화가 하나의 원인(SPA 렌더 시점)인가",
        "derived_from": "RQ-D12 F2 의 추측",
        "competing_hypotheses": {
            "H1_SPA_TIMING": "셋 다 DOM slot 이 렌더 전에 캡처된 결과",
            "H2_DISTINCT": "서로 다른 원인",
            "H3_MIXED": "일부만 SPA 시점",
        },
        "discriminating_evidence": ("SPA 시점 문제면 DOM 빈약 + probe 풍부. 진짜 빈약한 페이지면 "
                                    "DOM 도 probe 도 빈약. 이 두 서명을 나눈다."),
        "thresholds": {"dom_interactive_n_median": dom_med,
                       "probe_primary_n_median": probe_med,
                       "note": "in_mart 표본 중앙값. RQ-D12 의 q25 와 다른 기준인 이유는 여기서는 상대 비교이기 때문."},
        "grain": "target (in_mart==1)", "n": len(recs),
        "signature_distribution": dict(sig_all),
        "per_flag_signature": per_flag,
        "low_richness_breakdown": {
            "n": len(low),
            "SIGNATURE_SPA": len(low_spa),
            "SIGNATURE_SPARSE": len(low_sparse),
            "other": len(low) - len(low_spa) - len(low_sparse),
            "spa_share": round(len(low_spa) / len(low), 4) if low else None,
        },
        "elapsed_dom_to_probe_by_signature": elapsed_by_sig,
        "verdict": verdict,
        "records": recs,
    }
    (RES / "RQ_D12A_spa_timing.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")

    print(f"n={len(recs)}  dom_median={dom_med}  probe_median={probe_med}")
    print("signature 분포:", dict(sig_all))
    print()
    for f, v in per_flag.items():
        print(f"{f:<18} n={v['n']:<3} {v['by_signature']}")
    print()
    print(f"구조빈약 {len(low)}건 내역: SPA={len(low_spa)} SPARSE={len(low_sparse)} "
          f"other={len(low)-len(low_spa)-len(low_sparse)}  spa_share={out['low_richness_breakdown']['spa_share']}")
    print("signature 별 dom->probe 경과:", {k: v["median_s"] for k, v in elapsed_by_sig.items()})
    print(f"verdict = {verdict}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
