"""사이드카가 적은 **두 분해**를 D 가 독립 재계산한다. [D-DEF-106]

`D-V3-FINDING-096` 의 한계 — '어느 셀이 어느 회차에서 왔는지는 재지 않았다'.
사이드카는 그 축을 이미 적어 두었다:

    파생 경로(열 그대로)   ANCHOR 23 · LEXICON 4 · AMBIGUOUS 1 = 28
    값 최종 출처(보충 반영) E_SUPPLEMENT 8 · ANCHOR 18 · LEXICON 2 = 28
    E 가 덮은 8건          ANCHOR 5 + LEXICON 2 + AMBIGUOUS 1

**새 조작화가 아니다** — 발행된 수를 다시 세는 것이다(A/B/C 수치는 hypothesis 로
받고 독립 재계산한다는 D 규약).
"""
from __future__ import annotations

import csv
import json
import sys
from collections import Counter
from pathlib import Path

REPO = Path("/home/sieg/projects-wsl/ProjectFinal")
MART = REPO / "artifacts/v3_census/mart/CANONICAL_MART_50.csv"
sys.path.insert(0, str(Path(__file__).resolve().parent))

# 사이드카가 적은 값 — **D 가 옮겨 적은 것이고 원문이 정본이다**
SIDECAR_DERIVATION = {"ANCHOR_ON_E_LABEL": 23, "B_LEXICON_MATCHER": 4,
                      "POSTHOC_AMBIGUOUS_MULTIPLE_NARROW_MATCHES": 1}
SIDECAR_FINAL = {"E_SUPPLEMENT": 8, "ANCHOR_ON_E_LABEL": 18, "B_LEXICON_MATCHER": 2}
SIDECAR_OVERWRITTEN = {"ANCHOR_ON_E_LABEL": 5, "B_LEXICON_MATCHER": 2,
                       "POSTHOC_AMBIGUOUS_MULTIPLE_NARROW_MATCHES": 1}


def _rows(path: Path | None = None) -> list:
    p = path or MART
    return list(csv.DictReader(p.open(encoding="utf-8")))


def recompute(path: Path | None = None) -> dict:
    import d_coverage as CV
    rows = _rows(path)
    obs = [r for r in rows
           if CV.is_observed("entry_control_type", r.get("entry_control_type", ""), r)]
    deriv = Counter(r["entry_observation_provenance"] for r in obs)
    sup = [r for r in obs if r.get("entry_geometry_provenance") == "E_R3_SUPPLEMENT"]
    non = [r for r in obs if r.get("entry_geometry_provenance") != "E_R3_SUPPLEMENT"]
    final = {"E_SUPPLEMENT": len(sup)}
    final.update(Counter(r["entry_observation_provenance"] for r in non))
    overwritten = dict(Counter(r["entry_observation_provenance"] for r in sup))
    # **차이의 정체를 이름으로 짚는다** — 총수 차이만 내면 원인을 못 본다.
    # 첫 판은 '사이드카 클래스에 속하고 D 가 관측 아님' 으로 잡았는데 **과대였다**:
    # `NOT_OBSERVED` 8행은 사이드카의 28 모집단도 제외한다(AMBIGUOUS 를 1 로 센다).
    # **클래스별 차이(사이드카 − D)만큼만** 고른다.
    excluded = []
    for cls, want in SIDECAR_DERIVATION.items():
        gap = want - deriv.get(cls, 0)
        if gap <= 0:
            continue
        cand = [r for r in rows
                if r.get("entry_observation_provenance") == cls
                and not CV.is_observed("entry_control_type",
                                       r.get("entry_control_type", ""), r)]
        for r in cand[:gap]:
            excluded.append({"target_id": r["target_id"],
                             "entry_control_type": r.get("entry_control_type"),
                             "provenance": cls})
    agree_ovw = overwritten == SIDECAR_OVERWRITTEN
    n_d, n_s = len(obs), sum(SIDECAR_DERIVATION.values())
    return {"verdict": "AGREE" if (n_d == n_s and agree_ovw) else "DISAGREE",
            "n_observed_D": n_d, "n_observed_sidecar": n_s,
            "derivation_D": dict(deriv), "derivation_sidecar": SIDECAR_DERIVATION,
            "final_D": final, "final_sidecar": SIDECAR_FINAL,
            "overwritten_D": overwritten, "overwritten_sidecar": SIDECAR_OVERWRITTEN,
            "overwritten_agrees": agree_ovw,
            "excluded_by_D": excluded,
            "**차이는 정의 불일치다**": (
                "총수 차이는 **D 화이트리스트가 상태 토큰을 관측으로 세지 않는 것**에서 온다. "
                "D 는 옳다고 주장하지 않는다 — **어느 정의를 쓸지는 A 소관**이고 "
                "여기서는 **차이가 어느 행에서 오는지 이름으로 짚는다**"),
            "**E 가 덮은 8건 분해는 재현된다**": (
                "그 축은 D 와 사이드카가 **정확히 같다** — 정의가 갈리는 것은 "
                "**관측 모집단**이지 보충 귀속이 아니다"),
            "새_조작화가_아니다": "발행된 수를 다시 셌다. 화이트리스트는 `D-DEF-45` 에서 이미 세운 것이다"}


def controls() -> dict:
    import tempfile as _tf
    rows_out = []

    def case(name, got, want, negative=False):
        rows_out.append({"case": name, "got": got, "want": want, "ok": got == want,
                         "expectation": "must_flag" if negative else "must_not_flag"})

    live = recompute()
    case("E 가 덮은 8건 분해가 사이드카와 같다", live["overwritten_agrees"], True)
    case("D 관측 모집단을 실제로 셌다 — 0 이면 무효다", live["n_observed_D"] > 0, True)
    case("**차이가 있으면 그 행을 이름으로 짚는다**",
         len(live["excluded_by_D"]) == abs(live["n_observed_D"] - live["n_observed_sidecar"]),
         True, negative=True)

    # 합성: 상태 토큰이 섞이면 D 는 제외한다
    with _tf.TemporaryDirectory() as t:
        p = Path(t) / "m.csv"
        cols = ["target_id", "entry_control_type", "entry_observation_provenance",
                "entry_geometry_provenance"]
        with p.open("w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=cols)
            w.writeheader()
            w.writerow({"target_id": "X1", "entry_control_type": "LINK",
                        "entry_observation_provenance": "ANCHOR_ON_E_LABEL",
                        "entry_geometry_provenance": "E_SUPPLEMENT_NO_CANDIDATE"})
            w.writerow({"target_id": "X2", "entry_control_type": "AMBIGUOUS_MULTIPLE_TYPES",
                        "entry_observation_provenance": "ANCHOR_ON_E_LABEL",
                        "entry_geometry_provenance": "E_SUPPLEMENT_NO_CANDIDATE"})
        r = recompute(p)
        case("**상태 토큰 행은 관측에서 빠진다**", r["n_observed_D"], 1, negative=True)
        case("빠진 행을 이름으로 낸다",
             [x["target_id"] for x in r["excluded_by_D"]], ["X2"], negative=True)

    ok = all(x["ok"] for x in rows_out)
    return {"verdict": "PASS" if ok else "FAIL", "n": len(rows_out),
            "must_flag": sum(1 for x in rows_out if x["expectation"] == "must_flag"),
            "must_not_flag": sum(1 for x in rows_out if x["expectation"] == "must_not_flag"),
            "failed": [x["case"] for x in rows_out if not x["ok"]], "cases": rows_out}


if __name__ == "__main__":
    c = controls()
    print(json.dumps({"recompute": recompute(), "controls": c}, ensure_ascii=False, indent=1))
    raise SystemExit(0 if c["verdict"] == "PASS" else 3)
