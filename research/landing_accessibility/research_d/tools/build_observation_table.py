"""D 공용 관측 테이블 빌더 — 모든 D worker의 단일 입력.

각 RQ worker가 raw를 따로 파싱하면 값이 갈린다. 이 스크립트만이 raw를 읽고
관측단위 테이블 하나를 만든다. worker는 이 CSV/JSON만 소비한다.

read-only. production 경로를 수정하지 않는다.
산출: results/D_OBSERVATION_TABLE.{csv,json}
"""
from __future__ import annotations

import csv
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from html_decode import parse_html   # D 파싱 결함 시정: 선언 charset 준수

REPO = Path("/home/sieg/projects-wsl/ProjectFinal")
EVIDENCE_ROOTS = {
    f"w{n}": REPO / f".agent_worktrees/claude_b_e001_worker_{n}/artifacts/e001_w{n}/evidence"
    for n in ("01", "02", "03", "04")
}
MART = REPO / ".agent_worktrees/claude_b_analysis_current/artifacts/e001_real_marts"
PRIOR_CSV = (REPO / ".agent_worktrees/claude_b_recovery/research/landing_accessibility"
             / "shadow/lane_b/state/representative_task_candidate_shadow.csv")
RUN_DIR_RE = re.compile(r"^e001_full-wtg_(?P<wtg>[0-9a-f]+)-(?P<ts>.+)$")

# l0_probe.js @2281c85 에서 직접 확인한 절단 지점 (코드 라인 주석 포함).
# B의 T-B-RQ-D-001은 이 중 앞 4개만 보고했다.
CAPS = {
    "primary_action_candidates": 200,   # L279 slice(0,200), visible 필터 이후
    "accessible_name_sources": 300,     # L171 slice(0,300), visible 필터 **없음**
    "target_size": 300,                 # L145 slice(0,300), visible 필터 이후
    "contrast": 400,                    # L116 while seen<400, seen++는 필터 통과 후(L136)
}
UNDISCLOSED_CAPS = {
    "motion.body_star_scan": 3000,      # L249 querySelectorAll('body *').slice(0,3000)
    "motion.animated_elements": 60,     # L262 animated.slice(0,60)
    "endpoint_signals.body_text_chars": 4000,  # L332 innerText.slice(0,4000)
}

# cssselect 미설치. 동일 집합을 XPath로 표현한다 (중복 원소는 set으로 제거).
INTERACTIVE_XPATH = ("//a[@href] | //button | //input | //select | //textarea | "
                     "//*[@role='button'] | //*[@role='link'] | //*[@role='tab'] | "
                     "//*[@role='checkbox'] | //*[@role='radio']")


def load_prior() -> dict[str, dict]:
    """web_target_id -> prior row. wtg가 2행인 경우 CANDIDATE 행을 우선한다."""
    rows = list(csv.DictReader(PRIOR_CSV.open(encoding="utf-8-sig")))
    by_wtg: dict[str, dict] = {}
    for r in rows:
        w = r["web_target_id"].replace("wtg_", "")
        prev = by_wtg.get(w)
        if prev is None or (prev["mapping_status"] != "CANDIDATE" and r["mapping_status"] == "CANDIDATE"):
            by_wtg[w] = r
    return by_wtg


def mart_kept_runs() -> set[str]:
    rows = json.loads((MART / "fact_landing_observation.json").read_text())
    return {r["evidence_run_id"] for r in rows}


def dom_features(path: Path) -> dict:
    raw = path.read_bytes()
    try:
        tree, enc = parse_html(path)
    except Exception:
        return {"dom_parse_ok": 0}
    body = tree.find("body")
    body_txt = " ".join((body.text_content() if body is not None else "").split())
    title_el = tree.find(".//title")
    return {
        "dom_parse_ok": 1,
        "dom_encoding": enc,
        "dom_bytes": len(raw),
        "dom_title": (title_el.text or "").strip() if title_el is not None else "",
        "dom_element_n": len(tree.xpath("//*")),
        "dom_body_element_n": len(body.xpath(".//*")) if body is not None else 0,
        "dom_interactive_n": len(set(tree.xpath(INTERACTIVE_XPATH))),
        "dom_a_href_n": len(tree.xpath("//a[@href]")),
        "dom_button_n": len(tree.xpath("//button")),
        "dom_input_n": len(tree.xpath("//input")),
        "dom_role_n": len(tree.xpath("//*[@role]")),
        "dom_aria_label_n": len(tree.xpath("//*[@aria-label]")),
        "dom_script_n": len(tree.xpath("//script")),
        "dom_body_text_len": len(body_txt),
        "dom_body_empty": int(len(body_txt) < 50),
    }


def probe_features(path: Path) -> dict:
    p = json.loads(path.read_text())
    rf = p.get("raw_features", {})
    vp = rf.get("viewport", {})
    out = {
        "probe_present": 1,
        "probe_bytes": path.stat().st_size,
        "probe_version": p.get("probe_version"),
        "probe_collected_at": p.get("collected_at"),
        "probe_url": p.get("url"),
        "probe_final_url": vp.get("final_url"),
        "probe_title": vp.get("title"),
        "probe_lang": vp.get("lang"),
        "probe_scroll_height": vp.get("document_scroll_height"),
        "probe_layout_width": vp.get("layout_width"),
        "body_scroll_locked": int(bool(rf.get("body_scroll_lock", {}).get("locked"))),
        "modal_overlay_n": len(rf.get("modal_overlay_candidates", [])),
        "dismiss_control_n": len(rf.get("dismiss_control_candidates", [])),
        "search_inputs_n": len(rf.get("region_signals", {}).get("search_inputs", [])),
        "declared_regions_n": len(rf.get("region_signals", {}).get("declared_regions", [])),
        "declared_endpoints_n": len(rf.get("endpoint_signals", {}).get("declared_endpoints", [])),
        "article_present": rf.get("endpoint_signals", {}).get("article_present"),
        "motion_animated_n": len(rf.get("motion", {}).get("animated_elements", [])),
        "gate_password_input_n": rf.get("gate_signals", {}).get("password_input_count"),
        "gate_captcha_iframe_n": rf.get("gate_signals", {}).get("captcha_iframe_count"),
        "gate_visible_text_len": len(rf.get("gate_signals", {}).get("visible_text") or ""),
    }
    for field, cap in CAPS.items():
        n = len(rf.get(field, []))
        out[f"n_{field}"] = n
        out[f"cap_{field}"] = int(n >= cap)
    out["cap_any"] = int(any(out[f"cap_{f}"] for f in CAPS))
    out["cap_count"] = sum(out[f"cap_{f}"] for f in CAPS)
    # 미공개 cap: 정확한 도달 여부는 원본 페이지 없이는 알 수 없으나 근접도는 관측 가능
    out["cap_motion_animated_60"] = int(out["motion_animated_n"] >= 60)
    out["cap_body_text_4000"] = int(out["gate_visible_text_len"] >= 4000)
    return out


def main() -> int:
    prior = load_prior()
    kept = mart_kept_runs()
    rows: list[dict] = []
    for worker, root in EVIDENCE_ROOTS.items():
        for d in sorted(p for p in root.iterdir() if p.is_dir()):
            m = RUN_DIR_RE.match(d.name)
            if not m:
                continue
            obs_dirs = [p for p in d.iterdir() if p.is_dir()]
            for obs in obs_dirs or [None]:
                rec = {
                    "worker": worker,
                    "wtg": m["wtg"],
                    "run_dir": d.name,
                    "run_ts": m["ts"],
                    "observation_id": obs.name if obs else None,
                    "in_mart": int(d.name in kept),
                    "sealed": int((d / "run.json").exists()),
                }
                pr = prior.get(m["wtg"], {})
                rec.update({
                    "prior_archetype": pr.get("interaction_archetype"),
                    "prior_business_domain": pr.get("business_domain"),
                    "prior_mapping_status": pr.get("mapping_status"),
                    "prior_endpoint_signal_type": pr.get("endpoint_signal_type"),
                    "prior_region_signal_type": pr.get("region_signal_type"),
                    "prior_service": pr.get("service_name_canonical"),
                    "prior_url": pr.get("web_target_url"),
                })
                if obs is not None:
                    l0a = obs / "l0a"
                    dom, probe = l0a / "dom.html", l0a / "probe.json"
                    rec["has_l0c"] = int((obs / "l0c").exists())
                    rec["ax_bytes"] = (l0a / "ax.json").stat().st_size if (l0a / "ax.json").exists() else None
                    rec["css_bytes"] = ((l0a / "computed_css.json").stat().st_size
                                        if (l0a / "computed_css.json").exists() else None)
                    rec.update(dom_features(dom) if dom.exists() else {"dom_parse_ok": None})
                    rec.update(probe_features(probe) if probe.exists() else {"probe_present": 0})
                rows.append(rec)

    cols: list[str] = []
    for r in rows:
        for k in r:
            if k not in cols:
                cols.append(k)
    out_dir = Path(__file__).resolve().parents[1] / "results"
    out_dir.mkdir(exist_ok=True)
    with (out_dir / "D_OBSERVATION_TABLE_v2.csv").open("w", newline="", encoding="utf-8") as fh:
        wcsv = csv.DictWriter(fh, fieldnames=cols)
        wcsv.writeheader()
        wcsv.writerows(rows)
    (out_dir / "D_OBSERVATION_TABLE_v2.json").write_text(
        json.dumps({"caps_verified_at_sha": "2281c853950d0c475c5d2c1678680b971c2804f4",
                    "caps": CAPS, "undisclosed_caps": UNDISCLOSED_CAPS,
                    "n_rows": len(rows), "rows": rows}, ensure_ascii=False, indent=1) + "\n",
        encoding="utf-8")
    print(f"rows={len(rows)} cols={len(cols)}")
    print("probe_present:", sum(1 for r in rows if r.get("probe_present") == 1))
    print("dom_parse_ok :", sum(1 for r in rows if r.get("dom_parse_ok") == 1))
    print("in_mart      :", sum(r["in_mart"] for r in rows))
    print("prior missing:", sum(1 for r in rows if not r.get("prior_archetype")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
