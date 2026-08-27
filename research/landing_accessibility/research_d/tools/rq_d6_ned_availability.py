"""RQ-D6 — partial NED 보존 미구현이 detector 결함과 독립인가.

파생 근거: RQ-D1 F6 — mart 의 31 task row 에서 NED·IED·MPFED 가 전부 null 이다.
그때 나는 "SSOT 8.4 의 partial NED 보존 로직 자체가 미구현" 이라고 **추정**했다.

RQ: NED 가 null 인 것은 (a) 보존 로직이 없어서인가 (b) 보존할 것이 애초에 없어서인가?

경쟁가설
  H1 WIRING_GAP   depth 를 셀 재료는 있는데 보존/전달 단계가 없다 (detector 와 독립)
  H2 NO_MATERIAL  셀 재료 자체가 없다 (detector 와 같은 상류 원인)
  H3 RECORDING    활성화는 일어났는데 기록되지 않았다

read-only. 산출: results/RQ_D6_ned_availability.json
"""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

REPO = Path("/home/sieg/projects-wsl/ProjectFinal")
RD = Path(__file__).resolve().parents[1]


def main() -> int:
    rows = []
    for n in ("01", "02", "03", "04"):
        for bf in sorted((REPO / f".agent_worktrees/claude_b_e001_worker_{n}"
                          f"/artifacts/e001_w{n}/batches").glob("*.json")):
            rows += (json.load(bf.open()).get("results") or [])

    det = [r["detail"] for r in rows if isinstance(r.get("detail"), dict)]
    fields = {f: dict(Counter(str(d.get(f)) for d in det).most_common(8))
              for f in ("ned", "ied", "mpfed", "area_signal_status",
                        "endpoint_status", "endpoint_reached", "budget_reason")}

    with_ep = [(r["target_id"].replace("wtg_", ""), r["detail"]["episodes"])
               for r in rows if isinstance(r.get("detail"), dict) and r["detail"].get("episodes")]
    kinds = Counter(e.get("episode_kind") for _, eps in with_ep for e in eps)
    ended = Counter(e.get("ended_by") for _, eps in with_ep for e in eps)
    per = [{"target": t, "n_episodes": len(eps),
            "distinct_state_id": len({e.get("state_id") for e in eps}),
            "kinds": dict(Counter(e.get("episode_kind") for e in eps))} for t, eps in with_ep]

    non_scroll = sum(1 for _, eps in with_ep if any(e.get("episode_kind") != "SCROLL" for e in eps))
    verdict = "REFUTED" if non_scroll == 0 else "PARTIALLY_SUPPORTED"

    out = {
        "rq": "RQ-D6",
        "title": "NED 미산출이 detector 결함과 독립인가",
        "derived_from": "RQ-D1 F6",
        "corrects": "RQ-D1 F6 의 'partial NED 보존 로직 자체가 미구현' 이라는 추정",
        "competing_hypotheses": {
            "H1_WIRING_GAP": "재료는 있는데 보존/전달이 없다 (detector 와 독립)",
            "H2_NO_MATERIAL": "재료 자체가 없다 (detector 와 같은 상류 원인)",
            "H3_RECORDING": "활성화는 일어났는데 기록되지 않았다",
        },
        "ssot_rule": ("SSOT 00 §8.2 — scroll · text typing · redirect · passive wait · "
                      "popup dismissal 은 depth 에 합산하지 않는다. "
                      "§8.4 — endpoint 미도달이어도 **대표기능 영역이 관측되면** NED 는 보존한다."),
        "grain": "batch result (target), n=59",
        "n_results": len(rows),
        "field_distributions": fields,
        "episodes": {
            "targets_with_episodes": len(with_ep),
            "of_total": len(rows),
            "total_episodes": sum(len(e) for _, e in with_ep),
            "episode_kind_distribution": dict(kinds),
            "ended_by_distribution": dict(ended),
            "targets_with_non_scroll_episode": non_scroll,
            "targets_with_state_change": sum(1 for p in per if p["distinct_state_id"] > 1),
            "per_target": sorted(per, key=lambda p: -p["n_episodes"]),
        },
        "finding": {
            "f1": ("기록된 interaction episode 는 **151개 전부 SCROLL** 이고 ended_by 는 전부 IDLE 이다. "
                   f"non-SCROLL episode 를 가진 target 은 {non_scroll}/{len(with_ep)} — **한 건도 없다.**"),
            "f2": ("SSOT §8.2 는 scroll 을 depth 에 합산하지 않는다고 명시한다. "
                   "따라서 기록된 episode 전부가 **정의상 depth 에 세지 않는 종류**다."),
            "f3": ("area_signal_status 가 task row 31건 전부 NOT_OBSERVED 다. "
                   "§8.4 의 partial NED 보존 전제(대표기능 영역 관측)가 **한 건도 충족되지 않았다.**"),
            "f4": ("budget_reason 에 MAX_CONSECUTIVE_NO_STATE_CHANGE 2건이 있다 — Scout 가 "
                   "무언가 시도했으나 상태변화를 못 얻은 경우가 존재한다. 다만 그 시도가 "
                   "activation 이었는지 scroll 이었는지 episode 기록만으로는 알 수 없다."),
        },
        "answer": ("**독립이 아니다.** NED 가 null 인 것은 보존 로직이 빠져서가 아니라 "
                   "**보존할 partial NED 가 애초에 없었기 때문**이다. 활성화 episode 가 한 건도 없고 "
                   "region 관측이 한 건도 없다. 둘 다 같은 상류(대표기능 영역에 도달하지 못함)에서 나온다. "
                   "RQ-D1 F6 의 '보존 로직 미구현' 서술은 부정확하다."),
        "verdict": verdict,
        "limitations": [
            "Scout 코드를 읽지 않았다. non-SCROLL episode 부재가 '활성화가 없었다' 인지 "
            "'활성화가 episode 로 기록되지 않았다'(H3) 인지 이 데이터만으로는 갈리지 않는다.",
            "episode 스키마에 activation 종류가 정의돼 있는지 확인하지 않았다. "
            "episode_kind 가 SCROLL 하나뿐인 것이 스키마 제약일 수 있다.",
            "budget_reason MAX_CONSECUTIVE_NO_STATE_CHANGE 2건의 시도 내용을 확인하지 않았다.",
        ],
        "production_implication": ("P2: 'partial NED 보존을 구현하라' 는 제안은 이 증거에서 근거가 없다. "
                                   "보존할 값이 생기려면 먼저 region 이 관측돼야 하고 그것은 RF detector 의 일이다. "
                                   "두 문제를 분리해 발주하면 하나는 할 일이 없는 채로 남는다."),
        "followup": "RQ-D6a: Scout 코드에서 activation episode 가 기록되는 경로가 존재하는지 exact SHA 로 확인 (H3 배제)",
    }
    (RD / "results" / "RQ_D6_ned_availability.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"episode 총 {out['episodes']['total_episodes']}개, kind={dict(kinds)}, ended_by={dict(ended)}")
    print(f"non-SCROLL episode 가진 target: {non_scroll}/{len(with_ep)}")
    print(f"area_signal_status: {fields['area_signal_status']}")
    print(f"budget_reason: {fields['budget_reason']}")
    print(f"verdict = {verdict}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
