"""RQ-D13a-1 — 다차원 모달 판정이 H1/H2 경계를 얼마나 바꾸는가.

파생 근거: RQ-D13a 는 collector 자신의 MODAL_SOURCES(dialog_element·role_dialog·aria_modal·
backdrop_like) **하나만** 으로 분류했고, limitation 에 "scroll_lock·dismiss_control 을 판정에
쓰지 않았다" 를 적었다. 그 한계를 검사한다.

RQ: 신호를 더 넣으면 "coverage 1.0 의 4/22 만 모달" 이라는 결론이 바뀌는가?

경쟁가설
  H1 ROBUST     다차원으로 봐도 모달은 소수다 (RQ-D13a 결론 유지)
  H2 UNDERCOUNT 단일신호가 모달을 과소계수했다 (경계가 크게 이동)
  H3 UNSTABLE   신호 조합에 따라 결과가 흔들려 어느 값도 못 믿는다

**중요**: 정답이 없다. 어느 정의가 옳은지는 A 의 construct 결정이다. D 는 정의를 바꿨을 때
숫자가 얼마나 움직이는지만 잰다 — 그것이 이 RQ 의 전부다.

read-only. 산출: results/RQ_D13A1_multisignal_modality.json
"""
from __future__ import annotations

import csv
import json
from collections import Counter
from pathlib import Path

REPO = Path("/home/sieg/projects-wsl/ProjectFinal")
RD = Path(__file__).resolve().parents[1]
TABLE = RD / "results" / "D_OBSERVATION_TABLE_v2.csv"
EVIDENCE_ROOTS = {f"w{n}": REPO / f".agent_worktrees/claude_b_e001_worker_{n}/artifacts/e001_w{n}/evidence"
                  for n in ("01", "02", "03", "04")}
MODAL_SOURCES = {"dialog_element", "role_dialog", "aria_modal", "backdrop_like"}


def probe_of(row: dict) -> dict | None:
    for root in EVIDENCE_ROOTS.values():
        p = root / row["run_dir"] / (row["observation_id"] or "") / "l0a" / "probe.json"
        if p.exists():
            return json.loads(p.read_text())["raw_features"]
    return None


def main() -> int:
    rows = [r for r in csv.DictReader(TABLE.open(encoding="utf-8")) if r["in_mart"] == "1"]
    recs = []
    for r in rows:
        rf = probe_of(r)
        if rf is None:
            continue
        cands = [c for c in (rf.get("modal_overlay_candidates") or []) if c.get("visible")]
        if not cands:
            continue
        top = max(cands, key=lambda c: c.get("viewport_coverage") or 0.0)
        cov = float(top.get("viewport_coverage") or 0.0)
        srcs = set(top.get("candidate_sources") or ())
        # D-DEF-03 에서 확인한 구조: dismiss_control_candidates 는 컨테이너당 래퍼다.
        dc_map = {c.get("container_selector"): c for c in (rf.get("dismiss_control_candidates") or [])}
        own = dc_map.get(top.get("selector")) or {}
        own_dismiss_n = len(own.get("dismiss_control_candidates") or [])
        sig = {
            "src_modal": bool(srcs & MODAL_SOURCES),
            "scroll_locked": bool(rf.get("body_scroll_lock", {}).get("locked")),
            "has_own_dismiss": own_dismiss_n > 0,
            "is_dialog_element": bool(own.get("is_dialog_element")),
            "hittable": bool(top.get("hittable")),
            "contains_focus": bool(top.get("contains_focus")),
            "positive_z": (top.get("z_index") is not None and top.get("z_index") > 0),
        }
        score = sum(1 for v in sig.values() if v)
        recs.append({"wtg": r["wtg"], "service": r["prior_service"], "coverage": cov,
                     "selector": (top.get("selector") or "")[:70], "z": top.get("z_index"),
                     "position": top.get("position"), "own_dismiss_n": own_dismiss_n,
                     **sig, "signal_score": score,
                     "single_signal_class": "H1_MODAL" if sig["src_modal"] else "H2_GENERIC"})

    def classify(rec, rule):
        if rule == "single":
            return "MODAL" if rec["src_modal"] else "GENERIC"
        if rule == "src_or_lock_and_dismiss":
            return "MODAL" if rec["src_modal"] or (rec["scroll_locked"] and rec["has_own_dismiss"]) else "GENERIC"
        if rule == "score_ge_3":
            return "MODAL" if rec["signal_score"] >= 3 else "GENERIC"
        if rule == "score_ge_4":
            return "MODAL" if rec["signal_score"] >= 4 else "GENERIC"
        if rule == "lock_required":
            return "MODAL" if rec["scroll_locked"] else "GENERIC"
        raise ValueError(rule)

    RULES = ["single", "src_or_lock_and_dismiss", "score_ge_3", "score_ge_4", "lock_required"]
    hi = [r for r in recs if r["coverage"] >= 0.999]
    table = {}
    for rule in RULES:
        allc = Counter(classify(r, rule) for r in recs)
        hic = Counter(classify(r, rule) for r in hi)
        table[rule] = {"all": dict(allc), "coverage_1_0": dict(hic),
                       "modal_share_at_cov1": round(hic.get("MODAL", 0) / len(hi), 4) if hi else None}

    shares = [v["modal_share_at_cov1"] for v in table.values() if v["modal_share_at_cov1"] is not None]
    spread = round(max(shares) - min(shares), 4) if shares else None
    single = table["single"]["modal_share_at_cov1"]
    if spread is not None and spread <= 0.20:
        verdict = "SUPPORTED"        # H1 robust
    elif spread is not None and spread >= 0.50:
        verdict = "REFUTED"          # H3 unstable
    else:
        verdict = "PARTIALLY_SUPPORTED"

    out = {
        "rq": "RQ-D13a-1",
        "title": "다차원 모달 판정이 RQ-D13a 의 H1/H2 경계를 얼마나 바꾸는가",
        "derived_from": "RQ-D13a limitation 1 (scroll_lock·dismiss_control 미사용)",
        "no_ground_truth_note": ("정답이 없다. 어느 정의가 옳은지는 A 의 construct 결정이다. "
                                 "D 는 정의를 바꿨을 때 숫자가 얼마나 움직이는지만 잰다."),
        "competing_hypotheses": {"H1_ROBUST": "다차원으로도 모달은 소수", 
                                 "H2_UNDERCOUNT": "단일신호가 과소계수",
                                 "H3_UNSTABLE": "조합에 따라 흔들려 못 믿는다"},
        "signals": ["src_modal", "scroll_locked", "has_own_dismiss", "is_dialog_element",
                    "hittable", "contains_focus", "positive_z"],
        "rules": {
            "single": "collector MODAL_SOURCES 만 (RQ-D13a 원래 규칙)",
            "src_or_lock_and_dismiss": "MODAL_SOURCES 이거나 (scroll lock AND 자기 dismiss 컨트롤 보유)",
            "score_ge_3": "7 신호 중 3개 이상",
            "score_ge_4": "7 신호 중 4개 이상",
            "lock_required": "scroll lock 만",
        },
        "grain": "target (in_mart==1, probe 보유, visible 후보 존재)",
        "n": len(recs), "n_coverage_1_0": len(hi),
        "by_rule": table,
        "modal_share_spread_at_cov1": spread,
        "single_rule_share": single,
        "signal_prevalence_at_cov1": {s: sum(1 for r in hi if r[s]) for s in
                                      ["src_modal", "scroll_locked", "has_own_dismiss",
                                       "is_dialog_element", "hittable", "contains_focus", "positive_z"]},
        "signal_score_distribution_at_cov1": dict(sorted(Counter(r["signal_score"] for r in hi).items())),
        "verdict": verdict,
        "records": recs,
    }
    (RD / "results" / "RQ_D13A1_multisignal_modality.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")

    print(f"n={len(recs)} (coverage 1.0: {len(hi)})")
    print(f"{'rule':<26}{'MODAL@cov1':>12}{'share':>9}   전체")
    for rule, v in table.items():
        print(f"{rule:<26}{v['coverage_1_0'].get('MODAL',0):>12}{v['modal_share_at_cov1']:>9.3f}   {v['all']}")
    print(f"\ncoverage 1.0 에서 modal share 범위 = {spread}  (단일신호 규칙 {single})")
    print("신호 prevalence @cov1:", out["signal_prevalence_at_cov1"])
    print("signal_score 분포 @cov1:", out["signal_score_distribution_at_cov1"])
    print(f"verdict = {verdict}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
