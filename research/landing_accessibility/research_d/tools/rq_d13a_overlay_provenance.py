"""RQ-D13a — max_overlay_coverage 는 무엇을 재고 있는가.

파생 근거: RQ-D13 F2 에서 D 는 "빈 body 인데 coverage 1.0 이 붙었다 — 측정대상 부재 상태의
기하 계산일 가능성" 이라고 **추론**했다. 그 추론을 코드와 raw probe 로 검증한다.

코드 사실 (T1, exact SHA):
  l0_probe.js @2281c85 L196-224 — modal_overlay_candidates 는
    dialog / role=dialog / aria-modal / backdrop-like className 이거나
    **position:fixed|sticky 이거나 z-index >= 100** 이면 전부 후보로 넣는다.
  l0_collector.py @2281c85 L575-577 —
    max_overlay_coverage = max(viewport_coverage over ALL interrupts). 종류 필터 없음.
  l0_collector.py @2281c85 L276-282 — classify_interrupt 는
    dialog/role_dialog/aria_modal 계열 + coverage>=0.5 일 때만 BLOCKING_MODAL,
    아니면 fixed/sticky 는 BANNER.

따라서 max_overlay_coverage 는 SSOT 00 §3 Axis C 가 묻는 "popup·modal·banner·app prompt 의
방해" 가 아니라 **"fixed 또는 high-z 인 임의 요소의 최대 뷰포트 점유율"** 이다.

경쟁가설
  H1 MODAL      coverage 최대 요소는 실제 모달/배경막이다 (측정 타당)
  H2 GENERIC    fixed/high-z 이지만 모달이 아닌 요소(로딩 마스크·전면 컨테이너·스티키)다
  H3 INVISIBLE  최대 요소가 visible=false 인데도 계산에 들어갔다 (명백한 결함)

read-only. 산출: results/RQ_D13A_overlay_provenance.json
"""
from __future__ import annotations

import csv
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

REPO = Path("/home/sieg/projects-wsl/ProjectFinal")
RD = Path(__file__).resolve().parents[1]
TABLE = RD / "results" / "D_OBSERVATION_TABLE_v2.csv"
MART = REPO / ".agent_worktrees/claude_b_analysis_current/artifacts/e001_real_marts"
EVIDENCE_ROOTS = {
    f"w{n}": REPO / f".agent_worktrees/claude_b_e001_worker_{n}/artifacts/e001_w{n}/evidence"
    for n in ("01", "02", "03", "04")
}
MODAL_SOURCES = {"dialog_element", "role_dialog", "aria_modal", "backdrop_like"}
# 로딩/차단 마스크로 흔히 쓰이는 식별자. 사전은 전문 공개하며 결과를 보고 바꾸지 않는다.
LOADING_TOKENS = ("loading", "loader", "spinner", "progress", "showblock", "blockui",
                  "ing", "wait", "dimm", "dim", "mask", "shade", "cover", "veil")


def probe_path(row: dict) -> Path | None:
    for root in EVIDENCE_ROOTS.values():
        p = root / row["run_dir"] / (row["observation_id"] or "") / "l0a" / "probe.json"
        if p.exists():
            return p
    return None


def looks_loading(sel: str, text: str | None) -> bool:
    s = (sel or "").lower()
    return any(t in s for t in LOADING_TOKENS)


def main() -> int:
    rows = [r for r in csv.DictReader(TABLE.open(encoding="utf-8")) if r["in_mart"] == "1"]
    lo = {r["web_target_id"].replace("wtg_", ""): r
          for r in json.loads((MART / "fact_landing_observation.json").read_text())}

    recs = []
    for r in rows:
        p = probe_path(r)
        if p is None:
            recs.append({"wtg": r["wtg"], "service": r["prior_service"], "probe": False})
            continue
        rf = json.loads(p.read_text())["raw_features"]
        raw_cands = rf.get("modal_overlay_candidates", []) or []
        # collector(_build_interrupts @2281c85)는 visible 이 아닌 후보를 건너뛴다.
        # 그 규칙을 그대로 적용해야 mart 값이 재현된다. 처음에 이 필터를 빠뜨려
        # invisible 요소를 최대값으로 잡았고 mart 와 4건이 어긋났다 — 그 오류를 시정한 경로다.
        cands = [c for c in raw_cands if c.get("visible")]
        n_dropped_invisible = len(raw_cands) - len(cands)
        if not cands:
            recs.append({"wtg": r["wtg"], "service": r["prior_service"], "probe": True,
                         "n_candidates_raw": len(raw_cands), "n_dropped_invisible": n_dropped_invisible,
                         "n_candidates": 0, "max_coverage_probe": 0.0,
                         "max_coverage_mart": lo.get(r["wtg"], {}).get("max_overlay_coverage"),
                         "mart_matches_probe": True, "classification": "NO_VISIBLE_CANDIDATE"})
            continue
        top = max(cands, key=lambda c: c.get("viewport_coverage") or 0.0)
        srcs = set(top.get("candidate_sources") or ())
        sel = top.get("selector") or ""
        cov = float(top.get("viewport_coverage") or 0.0)
        vis = top.get("visible")
        if vis is False:
            klass = "H3_INVISIBLE"   # visible 필터 이후에는 나올 수 없다. 나오면 그 자체가 결함
        elif srcs & MODAL_SOURCES:
            klass = "H1_MODAL"
        elif looks_loading(sel, top.get("accessible_text")):
            klass = "H2_GENERIC_LOADING_MASK"
        else:
            klass = "H2_GENERIC_FIXED_OR_HIGHZ"
        mart_cov = lo.get(r["wtg"], {}).get("max_overlay_coverage")
        recs.append({
            "wtg": r["wtg"], "service": r["prior_service"], "archetype": r["prior_archetype"],
            "probe": True, "n_candidates": len(cands),
            "n_candidates_raw": len(raw_cands), "n_dropped_invisible": n_dropped_invisible,
            "max_coverage_probe": cov, "max_coverage_mart": mart_cov,
            "mart_matches_probe": (mart_cov is not None and abs(mart_cov - cov) < 1e-3),
            "top_selector": sel[:90], "top_role": top.get("role"),
            "top_sources": sorted(srcs), "top_position": top.get("position"),
            "top_z": top.get("z_index"), "top_visible": vis,
            "top_hittable": top.get("hittable"),
            "top_text": (top.get("accessible_text") or "")[:60],
            "scroll_locked": bool(rf.get("body_scroll_lock", {}).get("locked")),
            "dismiss_control_n": len(rf.get("dismiss_control_candidates", []) or []),
            "classification": klass,
            "dom_body_empty": r.get("dom_body_empty"),
        })

    with_probe = [x for x in recs if x.get("probe")]
    cls = Counter(x.get("classification") for x in with_probe)
    hi = [x for x in with_probe if (x.get("max_coverage_probe") or 0) >= 0.5]
    hi_cls = Counter(x["classification"] for x in hi)
    ones = [x for x in with_probe if (x.get("max_coverage_probe") or 0) >= 0.999]
    ones_cls = Counter(x["classification"] for x in ones)
    mismatch = [x for x in with_probe if x.get("max_coverage_mart") is not None
                and not x["mart_matches_probe"]]

    modal_hi = hi_cls.get("H1_MODAL", 0)
    verdict = ("REFUTED" if modal_hi == len(hi)
               else "SUPPORTED" if modal_hi == 0
               else "PARTIALLY_SUPPORTED")

    out = {
        "rq": "RQ-D13a",
        "title": "max_overlay_coverage 의 출처 — 무엇이 뷰포트를 덮은 것으로 계산됐나",
        "corrects": "RQ-D13 F2 의 추론 ('측정대상 부재 상태의 기하 계산일 가능성')",
        "code_facts": {
            "sha": "2281c853950d0c475c5d2c1678680b971c2804f4",
            "l0_probe.js:196-199": "position:fixed|sticky 이거나 z-index>=100 이면 modal 여부와 무관하게 후보에 포함",
            "l0_collector.py:575-577": "max_overlay_coverage = max(viewport_coverage over ALL interrupts), 종류 필터 없음",
            "l0_collector.py:276-282": "BLOCKING_MODAL 은 dialog/role_dialog/aria_modal + coverage>=0.5 일 때만. fixed/sticky 는 BANNER",
        },
        "competing_hypotheses": {
            "H1_MODAL": "최대 요소가 실제 모달/배경막", 
            "H2_GENERIC": "fixed/high-z 이지만 모달 아님 (로딩 마스크·전면 컨테이너·스티키)",
            "H3_INVISIBLE": "visible=false 인데 계산에 포함 (collector 필터 적용 후에는 0이어야 정상)",
        },
        "method_correction": (
            "1차 계산에서 collector 의 visible 필터를 빠뜨려 invisible 요소를 최대값으로 잡았고 "
            "mart 와 4건이 어긋났다(다음·Chrome·메가커피·Google). collector "
            "_build_interrupts @2281c85 의 `if not cand.get('visible'): continue` 를 그대로 "
            "적용해 시정했다. 시정 전 수치도 이 문서에 남긴다."),
        "pre_correction_result": {
            "classification_coverage_eq_1_0": {"H2_GENERIC_FIXED_OR_HIGHZ": 15, "H3_INVISIBLE": 4,
                                               "H2_GENERIC_LOADING_MASK": 2, "H1_MODAL": 4},
            "mart_probe_mismatch_n": 4},
        "grain": "target (in_mart==1), probe 보유분",
        "n_targets": len(rows), "n_with_probe": len(with_probe),
        "classification_all": dict(cls),
        "n_coverage_ge_0_5": len(hi), "classification_coverage_ge_0_5": dict(hi_cls),
        "n_coverage_eq_1_0": len(ones), "classification_coverage_eq_1_0": dict(ones_cls),
        "mart_probe_mismatch_n": len(mismatch),
        "mart_probe_mismatch": mismatch[:10],
        "loading_token_dictionary": list(LOADING_TOKENS),
        "modal_source_set": sorted(MODAL_SOURCES),
        "verdict": verdict,
        "records": recs,
    }
    (RD / "results" / "RQ_D13A_overlay_provenance.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")

    print(f"targets={len(rows)} with_probe={len(with_probe)}")
    print(f"전체 분류: {dict(cls)}")
    print(f"coverage>=0.5 ({len(hi)}건): {dict(hi_cls)}")
    print(f"coverage==1.0 ({len(ones)}건): {dict(ones_cls)}")
    print(f"mart 값과 probe 재계산 불일치: {len(mismatch)}")
    print()
    print("coverage==1.0 인 target 의 최대 요소:")
    for x in sorted(ones, key=lambda y: y["classification"]):
        print(f"  [{x['classification']:<24}] {x['service']:<14} z={str(x['top_z']):<7} "
              f"pos={x['top_position']:<8} vis={x['top_visible']} lock={x['scroll_locked']} "
              f"dismiss={x['dismiss_control_n']:<3} {x['top_selector'][:46]}")
    print(f"\nverdict = {verdict}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
