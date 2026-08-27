"""RQ-D13b — 강제 dismissal 은 실제로 무엇을 바꿨는가.

파생 근거: RQ-D13 F4 — l0c step 의 **33.1%(82/248)** 에서 screen_before 와 screen_after 의
sha256 이 같았다. 픽셀이 같다고 dismissal 이 실패한 것은 아니다. DOM 수준에서 재판정한다.

A 가 22:43 에 D-R0-72 `OverlayCoverage 겹침≠방해` 를 construct decision 으로 냈다.
dismissal 에도 같은 질문이 있다: **"화면이 안 바뀌었다" 와 "치우지 못했다" 는 같은가?**

경쟁가설
  H1 NO_EFFECT      픽셀 무변화 = DOM 도 무변화. dismissal 이 아무것도 하지 않았다
  H2 DOM_ONLY       DOM 은 바뀌었는데 픽셀이 같다 (뷰포트 밖 변화·시각적 동일)
  H3 ALREADY_GONE   dismiss 대상이 그 시점에 이미 없었다 (중복 dismissal)
  H4 CAPTURE_TIMING after 캡처가 애니메이션/전이 완료 전이다

step k 의 "before DOM" 은 step k-1 의 dom_after.html 이고, step 0 은 l0a/dom.html 이다
(l0c 에는 dom_before 슬롯이 없다). 이 가정을 결과에 명시한다.

read-only. 산출: results/RQ_D13B_dismissal_effect.json
"""
from __future__ import annotations

import csv
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from html_decode import parse_html   # 선언 charset 준수 (D-DEF-01 시정 경로)

REPO = Path("/home/sieg/projects-wsl/ProjectFinal")
RD = Path(__file__).resolve().parents[1]
TABLE = RD / "results" / "D_OBSERVATION_TABLE_v2.csv"
EVIDENCE_ROOTS = {
    f"w{n}": REPO / f".agent_worktrees/claude_b_e001_worker_{n}/artifacts/e001_w{n}/evidence"
    for n in ("01", "02", "03", "04")
}
WTG_RE = re.compile(r"^e001_full-wtg_([0-9a-f]+)-")
STEP_RE = re.compile(r"l0c/(\d+)/screen_(before|after)\.png$")
DOM_STEP_RE = re.compile(r"l0c/(\d+)/dom_after\.html$")
L0A_DOM_RE = re.compile(r"l0a/dom\.html$")


def dom_stats(path: Path) -> dict | None:
    try:
        tree, _ = parse_html(path)
    except Exception:
        return None
    body = tree.find("body")
    txt = " ".join((body.text_content() if body is not None else "").split())
    return {
        "element_n": len(tree.xpath("//*")),
        "body_element_n": len(body.xpath(".//*")) if body is not None else 0,
        "interactive_n": len(set(tree.xpath(
            "//a[@href] | //button | //input | //select | //textarea | "
            "//*[@role='button'] | //*[@role='link']"))),
        "body_text_len": len(txt),
        "fixed_hint_n": len(tree.xpath("//*[contains(@style,'fixed')]")),
        "bytes": path.stat().st_size,
    }


def main() -> int:
    rows = {r["run_dir"]: r for r in csv.DictReader(TABLE.open(encoding="utf-8"))}
    per_step = []
    for worker, root in EVIDENCE_ROOTS.items():
        for d in sorted(p for p in root.iterdir() if p.is_dir()):
            man = d / "manifest.jsonl"
            if not man.exists():
                continue
            meta = rows.get(d.name, {})
            shas = defaultdict(dict)
            dom_sha: dict[int, str] = {}
            base_dom_sha = None
            obs_id = None
            for line in man.read_text().splitlines():
                if not line.strip():
                    continue
                r = json.loads(line)
                obs_id = obs_id or r["observation_id"]
                m = STEP_RE.search(r["relpath"])
                if m:
                    shas[int(m.group(1))][m.group(2)] = r["sha256"]
                dm = DOM_STEP_RE.search(r["relpath"])
                if dm:
                    dom_sha[int(dm.group(1))] = r["sha256"]
                if L0A_DOM_RE.search(r["relpath"]):
                    base_dom_sha = r["sha256"]
            if not shas:
                continue
            obs_dir = d / obs_id
            base_dom = obs_dir / "l0a" / "dom.html"
            prev = dom_stats(base_dom) if base_dom.exists() else None
            prev_sha = base_dom_sha
            for k in sorted(shas):
                cur_path = obs_dir / "l0c" / str(k) / "dom_after.html"
                cur = dom_stats(cur_path) if cur_path.exists() else None
                v = shas[k]
                pixel_same = ("before" in v and "after" in v and v["before"] == v["after"])
                rec = {
                    "worker": worker, "wtg": WTG_RE.match(d.name).group(1) if WTG_RE.match(d.name) else d.name,
                    "service": meta.get("prior_service"), "archetype": meta.get("prior_archetype"),
                    "step": k, "pixel_same": pixel_same,
                    "dom_available": cur is not None and prev is not None,
                }
                if cur and prev:
                    d_el = cur["element_n"] - prev["element_n"]
                    d_int = cur["interactive_n"] - prev["interactive_n"]
                    d_txt = cur["body_text_len"] - prev["body_text_len"]
                    d_by = cur["bytes"] - prev["bytes"]
                    cur_sha = dom_sha.get(k)
                    # **바이트 동일성**이 판정 기준이다. element_n 같은 요약치는 CSS/class 토글을
                    # 못 본다. sha 가 같으면 inline style·class 까지 하나도 안 바뀐 것이다.
                    dom_same = (cur_sha is not None and prev_sha is not None
                                and cur_sha == prev_sha)
                    dom_same_by_summary = (d_el == 0 and d_int == 0 and d_txt == 0 and d_by == 0)
                    rec.update({"d_element_n": d_el, "d_interactive_n": d_int,
                                "d_body_text_len": d_txt, "d_bytes": d_by,
                                "dom_same": dom_same,
                                "dom_same_by_summary": dom_same_by_summary,
                                "dom_sha_available": cur_sha is not None and prev_sha is not None,
                                "prev_element_n": prev["element_n"], "cur_element_n": cur["element_n"]})
                    if pixel_same and dom_same:
                        rec["classification"] = "H1_NO_EFFECT"
                    elif pixel_same and not dom_same:
                        rec["classification"] = "H2_DOM_ONLY"
                    elif not pixel_same and dom_same:
                        rec["classification"] = "H4_PIXEL_ONLY"
                    else:
                        rec["classification"] = "EFFECTIVE"
                else:
                    rec["classification"] = "DOM_UNAVAILABLE"
                per_step.append(rec)
                prev = cur or prev
                prev_sha = dom_sha.get(k, prev_sha)

    evaluable = [r for r in per_step if r["classification"] != "DOM_UNAVAILABLE"]
    px_same = [r for r in evaluable if r["pixel_same"]]
    cls_all = Counter(r["classification"] for r in evaluable)
    cls_px_same = Counter(r["classification"] for r in px_same)

    by_target = defaultdict(lambda: Counter())
    for r in evaluable:
        by_target[r["wtg"]][r["classification"]] += 1
    all_noeffect = [w for w, c in by_target.items()
                    if c.get("H1_NO_EFFECT", 0) == sum(c.values()) and sum(c.values()) > 0]

    n_px_same = len(px_same)
    h2 = cls_px_same.get("H2_DOM_ONLY", 0)
    verdict = ("REFUTED" if n_px_same and h2 / n_px_same > 0.5      # 픽셀무변화 대부분이 DOM 변화 있음
               else "SUPPORTED" if n_px_same and h2 / n_px_same < 0.2
               else "PARTIALLY_SUPPORTED")

    out = {
        "rq": "RQ-D13b",
        "title": "강제 dismissal 의 DOM 수준 효과 — 픽셀 무변화 82건의 정체",
        "derived_from": "RQ-D13 F4 (before==after 82/248 steps)",
        "hypothesis_under_test": "H1_NO_EFFECT: 픽셀 무변화는 dismissal 무효과를 뜻한다",
        "competing_hypotheses": {
            "H1_NO_EFFECT": "픽셀·DOM 모두 무변화",
            "H2_DOM_ONLY": "DOM 은 바뀌었는데 픽셀이 같다",
            "H4_PIXEL_ONLY": "픽셀은 바뀌었는데 DOM 지표는 같다",
            "EFFECTIVE": "둘 다 바뀌었다",
        },
        "method_assumption": ("l0c 에 dom_before 슬롯이 없다. step k 의 before DOM 을 "
                              "step k-1 의 dom_after.html(또는 step 0 은 l0a/dom.html)로 대용했다. "
                              "이 대용이 틀리면 delta 해석이 바뀐다."),
        "dom_metrics": ["element_n", "interactive_n", "body_text_len", "bytes"],
        "dom_identity_criterion": ("dom_after.html 의 sha256 바이트 동일성. 요약치(element_n 등)는 "
                                   "CSS/class 토글을 보지 못하므로 판정 기준으로 쓰지 않는다. "
                                   "요약치 기준 결과는 dom_same_by_summary 로 병기한다."),
        "grain": "l0c step",
        "n_steps_total": len(per_step),
        "n_steps_evaluable": len(evaluable),
        "n_dom_unavailable": len(per_step) - len(evaluable),
        "classification_all": dict(cls_all),
        "n_pixel_same": n_px_same,
        "classification_among_pixel_same": dict(cls_px_same),
        "targets_all_no_effect": sorted(all_noeffect),
        "n_targets_all_no_effect": len(all_noeffect),
        "n_targets_with_l0c": len(by_target),
        "verdict": verdict,
        "steps": per_step,
    }
    (RD / "results" / "RQ_D13B_dismissal_effect.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")

    print(f"steps total={len(per_step)} evaluable={len(evaluable)} dom_unavailable={len(per_step)-len(evaluable)}")
    print(f"전체 분류: {dict(cls_all)}")
    print(f"픽셀 무변화 {n_px_same}건의 내역: {dict(cls_px_same)}")
    if n_px_same:
        print(f"  -> 그중 DOM 은 바뀐 것(H2_DOM_ONLY): {h2}/{n_px_same} = {h2/n_px_same:.1%}")
    summ = Counter()
    for r in evaluable:
        if r.get("dom_same") != r.get("dom_same_by_summary"):
            summ["sha_vs_summary_disagree"] += 1
    print(f"sha 기준과 요약치 기준이 갈리는 step: {summ['sha_vs_summary_disagree']}/{len(evaluable)}")
    print(f"모든 step 이 H1_NO_EFFECT 인 target: {len(all_noeffect)}/{len(by_target)}")
    print(f"verdict = {verdict}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
