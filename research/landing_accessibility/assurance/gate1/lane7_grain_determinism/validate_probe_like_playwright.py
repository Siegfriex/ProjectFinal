#!/usr/bin/env python3
"""Optional third check: measure the fixtures in a real browser (Playwright, file:// only, every other request
aborted, viewport 390x844 mobile) and compare against the HAND-AUTHORED probe_like/*.json: bbox, visible
(Playwright is_visible), hittable (elementFromPoint at bbox centre), ax_exposed / accessible name (aria snapshot).
This validates the simulated probe input, not impl_a/impl_b. Output: out/playwright_validation.{txt,json}."""
import json, pathlib, re, sys
from playwright.sync_api import sync_playwright
HERE = pathlib.Path(__file__).resolve().parent
PROBE = {"f01": "f01_blocking_modal_visible_close.html", "f02": "f02_overlay_control_hidden.html",
         "f03": "f03_overlay_control_after_scroll.html", "f04": "f04_two_overlays_one_blocking.html", "f05": "f05_no_overlay.html"}

JS_BOX = """(sel) => { const e = document.querySelector(sel); if (!e) return null; const r = e.getBoundingClientRect();
  const cs = getComputedStyle(e); return {x:r.x, y:r.y, w:r.width, h:r.height, display:cs.display}; }"""
JS_HIT = """(sel) => { const e = document.querySelector(sel); const r = e.getBoundingClientRect();
  const cx = r.x + r.width/2, cy = r.y + r.height/2; if (cx<0||cy<0||cx>innerWidth||cy>innerHeight) return false;
  const t = document.elementFromPoint(cx, cy); return !!t && (t === e || e.contains(t)); }"""
JS_AXH = """(sel) => { let e = document.querySelector(sel); while (e) { if (e.getAttribute && e.getAttribute('aria-hidden')==='true') return true; e = e.parentElement; } return false; }"""

def main():
    rows, mism = [], 0
    with sync_playwright() as p:
        b = p.chromium.launch()
        ctx = b.new_context(viewport={"width": 390, "height": 844}, is_mobile=True, has_touch=True, locale="ko-KR", timezone_id="Asia/Seoul")
        ctx.route("**/*", lambda route: route.continue_() if route.request.url.startswith("file://") else route.abort())
        pg = ctx.new_page()
        for k, fx in PROBE.items():
            probe = json.loads((HERE / "probe_like" / f"{k}.json").read_text(encoding="utf-8"))
            pg.goto((HERE / "fixtures" / fx).as_uri()); pg.wait_for_load_state("load")
            checks = [("task", probe["task_control"]["selector"], probe["task_control"]["bbox"], None)]
            for c in probe["raw_features"]["dismiss_control_candidates"]:
                checks.append(("container", c["container_selector"], c["bbox"], None))
                for cand in c["dismiss_control_candidates"]:
                    checks.append(("cand", cand["selector"], cand["bbox"], cand))
            for kind, sel, bbox, cand in checks:
                m = pg.evaluate(JS_BOX, sel)
                meas = None if (m is None or m["display"] == "none") else [round(m["x"]), round(m["y"]), round(m["w"]), round(m["h"])]
                row = {"fixture": k, "kind": kind, "selector": sel, "bbox_hand": bbox, "bbox_pw": meas, "bbox_ok": meas == (list(bbox) if bbox else None)}
                if cand is not None:
                    loc = pg.locator(sel)
                    vis = loc.is_visible()
                    hit = bool(vis and meas and pg.evaluate(JS_HIT, sel))   # probe hittable := visible ∧ receives pointer (Playwright actionability order)
                    axh = pg.evaluate(JS_AXH, sel)
                    name = None
                    if vis and not axh:
                        snap = loc.aria_snapshot()
                        mm = re.search(r'-\s*\w+\s+"([^"]*)"', snap)
                        name = mm.group(1) if mm else ""
                    row.update(visible_hand=cand["visible"], visible_pw=vis, hittable_hand=cand["hittable"], hittable_pw=hit,
                               ax_exposed_hand=cand["ax_exposed"], ax_exposed_pw=(vis and not axh),
                               name_hand=cand["accessible_name"], name_pw=name or "",
                               facts_ok=(cand["visible"] == vis and cand["hittable"] == hit and cand["ax_exposed"] == (vis and not axh)
                                         and (cand["accessible_name"] or "") == (name or "")))
                else:
                    row["facts_ok"] = True
                ok = row["bbox_ok"] and row["facts_ok"]
                mism += (not ok)
                rows.append(row)
        b.close()
    lines = ["fixture | kind | selector | bbox hand | bbox playwright | vis h/pw | hit h/pw | ax h/pw | name h/pw | ok"]
    for r in rows:
        f = lambda a, b: f"{a}/{b}" if "visible_hand" in r else "-"
        lines.append(f"{r['fixture']} | {r['kind']} | {r['selector']} | {r['bbox_hand']} | {r['bbox_pw']} | "
                     f"{f(r.get('visible_hand'), r.get('visible_pw'))} | {f(r.get('hittable_hand'), r.get('hittable_pw'))} | "
                     f"{f(r.get('ax_exposed_hand'), r.get('ax_exposed_pw'))} | {f(r.get('name_hand'), r.get('name_pw'))} | "
                     f"{'ok' if r['bbox_ok'] and r['facts_ok'] else 'MISMATCH'}")
    lines.append(f"checked={len(rows)} mismatches={mism} -> {'PROBE_LIKE_VALIDATED' if mism == 0 else 'PROBE_LIKE_MISMATCH'}")
    txt = "\n".join(lines); print(txt)
    (HERE / "out" / "playwright_validation.txt").write_text(txt + "\n", encoding="utf-8")
    (HERE / "out" / "playwright_validation.json").write_text(json.dumps(rows, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    sys.exit(0 if mism == 0 else 1)

if __name__ == "__main__":
    main()
