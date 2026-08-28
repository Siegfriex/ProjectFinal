#!/usr/bin/env python3
"""Optional third check: measure the fixtures in a real browser (Playwright, file:// only, every other request
aborted, viewport 390x844 mobile) and compare against the HAND-AUTHORED probe_like/*.json: bbox, visible
(Playwright is_visible), hittable (elementFromPoint at bbox centre), ax_exposed / accessible name (aria snapshot);
v1.2 also the path_control 9x9 elementFromPoint hit grid and every container's blocking_proof (a real click at the path
control centre must leave location.hash unchanged; containers are removed in dismissal order between proofs).
This validates the simulated probe input, not impl_a/impl_b. Output: out/playwright_validation.{txt,json}."""
import json, pathlib, re, sys
try:
    from playwright.sync_api import sync_playwright
except ImportError as _e:  # Δ46-exit2: a probe that cannot import its browser driver did not run
    if __name__ != "__main__":
        raise
    print(f"validate_probe_like_playwright: did not run — read neither as pass nor fail (exit 2): {_e!r}", file=sys.stderr); sys.exit(2)
HERE = pathlib.Path(__file__).resolve().parent
PROBE = {"f01": "f01_blocking_modal_visible_close.html", "f02": "f02_overlay_control_hidden.html",
         "f03": "f03_overlay_control_after_scroll.html", "f04": "f04_two_overlays_one_blocking.html", "f05": "f05_no_overlay.html",
         "f06": "f06_aria_modal_not_blocking_glass_no_pointer.html"}

JS_BOX = """(sel) => { const e = document.querySelector(sel); if (!e) return null; const r = e.getBoundingClientRect();
  const cs = getComputedStyle(e); return {x:r.x, y:r.y, w:r.width, h:r.height, display:cs.display}; }"""
JS_HIT = """(sel) => { const e = document.querySelector(sel); const r = e.getBoundingClientRect();
  const cx = r.x + r.width/2, cy = r.y + r.height/2; if (cx<0||cy<0||cx>innerWidth||cy>innerHeight) return false;
  const t = document.elementFromPoint(cx, cy); return !!t && (t === e || e.contains(t)); }"""
JS_GRID = """([sel, conts]) => { const e = document.querySelector(sel); const r = e.getBoundingClientRect(); const rows = [];
  for (let j = 0; j < 9; j++) { let row = ''; for (let i = 0; i < 9; i++) { const x = r.x + (i + 0.5) * r.width / 9, y = r.y + (j + 0.5) * r.height / 9;
    if (x < 0 || y < 0 || x > innerWidth || y > innerHeight) { row += '-'; continue; }
    const t = document.elementFromPoint(x, y); if (t === e || e.contains(t)) { row += '.'; continue; }
    let hit = '?'; for (const [letter, csel] of Object.entries(conts)) { const c = document.querySelector(csel); if (c && (c === t || c.contains(t))) { hit = letter; break; } }
    row += hit; } rows.push(row); } return rows; }"""
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
            pc = probe.get("path_control")
            if pc:
                checks.append(("path", pc["selector"], pc["bbox"], None))
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
            if pc:
                grid_pw = pg.evaluate(JS_GRID, [pc["selector"], pc["hit_grid"]["legend"]])
                ok = grid_pw == pc["hit_grid"]["rows"]
                mism += (not ok)
                rows.append({"fixture": k, "kind": "hit_grid", "selector": pc["selector"], "bbox_hand": None, "bbox_pw": None, "bbox_ok": True,
                             "grid_hand": pc["hit_grid"]["rows"], "grid_pw": grid_pw, "facts_ok": ok})
                # blocking proof, dismissal order (z desc, dom_order asc): click the path-control centre; hash unchanged ⇒ blocked
                order = sorted(probe["raw_features"]["dismiss_control_candidates"], key=lambda c: (-(c.get("z_index") or 0), c["dom_order"]))
                cx, cy = pc["bbox"][0] + pc["bbox"][2] / 2, pc["bbox"][1] + pc["bbox"][3] / 2
                for c in order:
                    pg.evaluate("() => history.replaceState(null, '', location.pathname)")
                    before = pg.evaluate("() => location.hash")
                    pg.mouse.click(cx, cy); pg.wait_for_timeout(50)
                    blocked = pg.evaluate("() => location.hash") == before
                    ok = blocked == bool(c.get("blocking_proof"))
                    mism += (not ok)
                    rows.append({"fixture": k, "kind": "blocking_proof", "selector": c["container_selector"], "bbox_hand": None, "bbox_pw": None, "bbox_ok": True,
                                 "blocking_hand": bool(c.get("blocking_proof")), "blocking_pw": blocked, "facts_ok": ok})
                    pg.evaluate("(s) => { const e = document.querySelector(s); if (e) e.remove(); }", c["container_selector"])   # simulated dismissal
        b.close()
    lines = ["fixture | kind | selector | bbox hand | bbox playwright | vis h/pw | hit h/pw | ax h/pw | name h/pw | ok"]
    for r in rows:
        if r["kind"] == "hit_grid":
            lines.append(f"{r['fixture']} | hit_grid | {r['selector']} | hand={''.join(r['grid_hand'])} | pw={''.join(r['grid_pw'])} | {'ok' if r['facts_ok'] else 'MISMATCH'}")
            continue
        if r["kind"] == "blocking_proof":
            lines.append(f"{r['fixture']} | blocking_proof | {r['selector']} | hand={r['blocking_hand']} | click-at-centre blocked={r['blocking_pw']} | {'ok' if r['facts_ok'] else 'MISMATCH'}")
            continue
        f = lambda a, b: f"{a}/{b}" if "visible_hand" in r else "-"
        lines.append(f"{r['fixture']} | {r['kind']} | {r['selector']} | {r['bbox_hand']} | {r['bbox_pw']} | "
                     f"{f(r.get('visible_hand'), r.get('visible_pw'))} | {f(r.get('hittable_hand'), r.get('hittable_pw'))} | "
                     f"{f(r.get('ax_exposed_hand'), r.get('ax_exposed_pw'))} | {f(r.get('name_hand'), r.get('name_pw'))} | "
                     f"{'ok' if r['bbox_ok'] and r['facts_ok'] else 'MISMATCH'}")
    if not rows:  # R43 / T-B-V3-FC-005: zero checks is not PROBE_LIKE_VALIDATED
        print("validate_probe_like_playwright: did not run — zero checks (checks_performed=0) — read neither as pass nor fail (exit 2)", file=sys.stderr); sys.exit(2)
    lines.append(f"checked={len(rows)} mismatches={mism} -> {'PROBE_LIKE_VALIDATED' if mism == 0 else 'PROBE_LIKE_MISMATCH'}")
    txt = "\n".join(lines); print(txt)
    (HERE / "out" / "playwright_validation.txt").write_text(txt + "\n", encoding="utf-8")
    (HERE / "out" / "playwright_validation.json").write_text(json.dumps(rows, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    sys.exit(0 if mism == 0 else 1)

if __name__ == "__main__":
    try:
        _rc = main()
    except Exception:  # Δ46-exit2 / Δ50-exit2-common: crash or missing input = did not run, never exit 1 (ran and failed)
        import traceback
        traceback.print_exc()
        print("validate_probe_like_playwright: did not run — read neither as pass nor fail (exit 2)", file=sys.stderr)
        _rc = 2
    sys.exit(_rc)
