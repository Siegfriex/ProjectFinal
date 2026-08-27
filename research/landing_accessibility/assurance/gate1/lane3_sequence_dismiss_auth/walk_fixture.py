#!/usr/bin/env python3
"""C Lane-3 fixture self-validation walker.

Drives every fixture in EXPECTATIONS.json through its intended path using the
data-c-action controls, records (state_before, action, state_after) triples,
bbox + hit-test occlusion of the next path control, scroll-state discovery of the
task control, decoy visibility, credential emptiness, and re-derives the depth
variables from the pre-registered rules.  It validates the FIXTURES against C's
EXPECTATIONS -- it is not a runner and touches no B code.

Offline: chromium headless, 390x844 mobile, every non-file:// request aborted.
Exit 0 only when every fixture PASSes.
"""
from __future__ import annotations
import json, sys, time, pathlib
from playwright.sync_api import sync_playwright

HERE = pathlib.Path(__file__).resolve().parent
EXP = json.loads((HERE / "EXPECTATIONS.json").read_text())
VW, VH = EXP["viewport"]["width"], EXP["viewport"]["height"]
ACT, REVEAL = set(EXP["token_sets"]["ACTIVATION_SET"]), set(EXP["token_sets"]["REVEAL_SET"])
OUT = HERE / "out"; OUT.mkdir(exist_ok=True)

JS_HELPERS = r"""
(() => {
  window.__c = {
    bbox(sel){ const e=document.querySelector(sel); if(!e) return null; const r=e.getBoundingClientRect();
               return {x:r.x,y:r.y,w:r.width,h:r.height}; },
    // hit-test occlusion: fraction of 9x9 grid points inside the bbox whose top element is not the control/descendant
    occl(sel){ const e=document.querySelector(sel); if(!e) return null; const r=e.getBoundingClientRect();
               if(r.width<=0||r.height<=0) return null; let n=0,occ=0;
               for(let i=0;i<9;i++)for(let j=0;j<9;j++){ const x=r.x+(i+0.5)*r.width/9, y=r.y+(j+0.5)*r.height/9;
                 if(x<0||y<0||x>innerWidth||y>innerHeight) continue; n++;
                 const t=document.elementFromPoint(x,y); if(!(t===e||e.contains(t))) occ++; }
               return n? occ/n : null; },
    // geometric intersection of control bbox with [data-c-overlay] elements, as a fraction of control area
    geo(sel){ const e=document.querySelector(sel); if(!e) return null; const r=e.getBoundingClientRect(); if(r.width<=0||r.bottom<=0||r.top>=innerHeight) return null;
              let best=0; document.querySelectorAll('[data-c-overlay]').forEach(o=>{ const b=o.getBoundingClientRect();
                const w=Math.max(0,Math.min(r.right,b.right)-Math.max(r.left,b.left)), h=Math.max(0,Math.min(r.bottom,b.bottom)-Math.max(r.top,b.top));
                best=Math.max(best, w*h/(r.width*r.height)); }); return best; },
    overlayCov(){ let best=0; document.querySelectorAll('[data-c-overlay]').forEach(o=>{ const b=o.getBoundingClientRect();
                const w=Math.max(0,Math.min(innerWidth,b.right)-Math.max(0,b.left)), h=Math.max(0,Math.min(innerHeight,b.bottom)-Math.max(0,b.top));
                best=Math.max(best, w*h/(innerWidth*innerHeight)); }); return best; },
    inViewport(sel){ const e=document.querySelector(sel); if(!e) return false; const r=e.getBoundingClientRect();
              return r.width>0 && r.height>0 && r.bottom>0 && r.top<innerHeight && getComputedStyle(e).visibility!=='hidden'; },
    state(){ return document.body.dataset.cState; },
    terminal(){ return document.body.dataset.cTerminal || ""; },
    forbiddenHit(){ return parseInt(document.body.dataset.cForbiddenHit||"0"); },
    forbiddenInputsNonEmpty(){ return [...document.querySelectorAll('input[data-c-forbidden]')].filter(i=>i.value!=='').map(i=>i.dataset.cForbidden); },
    transitions(){ return window.__cTransitions||[]; },
    docHeight(){ return document.documentElement.scrollHeight; },
    ariaName(sel){ const e=document.querySelector(sel); if(!e) return null; return e.getAttribute('aria-label')|| (e.labels&&e.labels[0]&&e.labels[0].textContent.trim()) || e.textContent.trim(); }
  };
})();
"""

def sel_for(action: str) -> str:
    return f'[data-c-action="{action}"][data-c-path="1"], [data-c-action="{action}"]:not([data-c-path])'

def approx(v, exp, tol=0.02):
    if exp is None: return v is None
    if isinstance(exp, list): return v is not None and exp[0] - tol <= v <= exp[1] + tol
    return v is not None and abs(v - exp) <= tol

def derive(task):
    return dict(activation_depth=sum(t in ACT for t in task),
                flow_step_count=sum(t not in ("ENDPOINT_REACHED", "ABSTAIN") for t in task),
                menu_dependency=any(t in REVEAL for t in task if t not in EXP["token_sets"]["TERMINAL_SET"]),
                nav_container_depth=sum(t in REVEAL for t in (task[:task.index("SELECT_FUNCTION")] if "SELECT_FUNCTION" in task else task)))

def wait_state(page, want, timeout=2.0):
    t0 = time.time()
    while time.time() - t0 < timeout:
        if page.evaluate("__c.state()") == want: return True
        page.wait_for_timeout(50)
    return False

def walk_one(browser, name, f):
    fails, rec = [], {"fixture": name, "steps": [], "aborted_requests": []}
    def chk(cond, msg):
        if not cond: fails.append(msg)
    ctx = browser.new_context(viewport={"width": VW, "height": VH}, device_scale_factor=2, is_mobile=True, has_touch=True,
                              locale="ko-KR", timezone_id="Asia/Seoul",
                              user_agent="Mozilla/5.0 (Linux; Android 13; Pixel 7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Mobile Safari/537.36")
    def route(r):
        if r.request.url.startswith("file://"): r.continue_()
        else: rec["aborted_requests"].append(r.request.url); r.abort()
    ctx.route("**/*", route)
    page = ctx.new_page(); page.set_default_timeout(3000)
    url = (HERE / f["file"]).resolve().as_uri()
    page.goto(url); page.wait_for_load_state("load"); page.evaluate(JS_HELPERS)
    reload_helpers = lambda: page.evaluate(JS_HELPERS)

    # --- S0 -------------------------------------------------------------
    chk(page.evaluate("__c.state()") == f["initial_state"], f"initial state {page.evaluate('__c.state()')} != {f['initial_state']}")
    chk(page.evaluate("__c.terminal()") == f["initial_terminal"], "initial terminal mismatch")
    task_sel = '[data-c-task-control="1"]'
    s0_vis = page.evaluate(f"__c.inViewport({task_sel!r})") and (page.evaluate(f"__c.occl({task_sel!r})") or 0) < 0.5
    chk(s0_vis == f["s0_task_control_visible"], f"s0_task_control_visible observed {s0_vis} != {f['s0_task_control_visible']}")
    # scroll-only discovery of the task control (step = one viewport)
    fvss = "NONE"; h = page.evaluate("__c.docHeight()"); k = 0; scroll_states = []
    while True:
        y = k * VH
        if y > max(0, h - 1): break
        page.evaluate(f"window.scrollTo(0,{y})"); page.wait_for_timeout(30)
        scroll_states.append(f"S{k}")
        if fvss == "NONE" and page.evaluate(f"__c.inViewport({task_sel!r})"): fvss = f"S{k}"
        k += 1
        if k > 20: break
    page.evaluate("window.scrollTo(0,0)"); page.wait_for_timeout(30)
    rec["scroll_states"], rec["first_visible_scroll_state"] = scroll_states, fvss
    chk(fvss == f["first_visible_scroll_state"], f"first_visible_scroll_state {fvss} != {f['first_visible_scroll_state']}")
    if f.get("scroll_states_expected"): chk(scroll_states == f["scroll_states_expected"], f"scroll states {scroll_states}")
    # S0 path-entry control bbox / occlusion
    pec = f.get("s0_path_entry_control")
    if pec:
        s = sel_for(pec["token"])
        rec["s0_entry_bbox"] = page.evaluate(f"__c.bbox({s!r})")
        occ, geo = page.evaluate(f"__c.occl({s!r})"), page.evaluate(f"__c.geo({s!r})")
        rec["s0_occlusion_hittest"], rec["s0_occlusion_geometric"] = occ, geo
        chk(approx(occ, f["task_control_occlusion_s0"]), f"S0 occlusion(hit-test) {occ} != {f['task_control_occlusion_s0']}")
        chk(approx(geo, f["task_control_occlusion_s0"]), f"S0 occlusion(geometric) {geo} != {f['task_control_occlusion_s0']}")
        chk(page.evaluate(f"__c.ariaName({s!r})") == pec["accessible_name"], "entry control accessible name mismatch")
        chk(page.evaluate(f"__c.inViewport({s!r})") == pec["visible"], "entry control in-viewport mismatch")
    cov = page.evaluate("__c.overlayCov()"); rec["s0_overlay_coverage"] = cov
    chk(approx(cov, f["overlay_coverage_s0"]), f"S0 overlay_coverage {cov} != {f['overlay_coverage_s0']}")
    dc = f.get("dismiss_control")
    if dc:
        loc = page.get_by_role(dc["role"], name=dc["accessible_name"], exact=True)
        chk(loc.count() == 1 and loc.first.is_visible(), f"dismiss control '{dc['accessible_name']}' not uniquely visible")
    for d in f["decoys_visible_at_s0"]:
        chk(page.locator(f'[data-c-decoy="{d}"]').first.is_visible(), f"decoy {d} not visible at S0")
    bp = f.get("blocking_proof")
    if bp:
        b = page.evaluate(f"__c.bbox({sel_for(bp['click_center_of'])!r})")
        page.mouse.click(b["x"] + b["w"] / 2, b["y"] + b["h"] / 2); page.wait_for_timeout(100)
        st = page.evaluate("__c.state()"); rec["blocking_proof_state"] = st
        chk(st == bp["expect_state_after"], f"blocking_proof: state {st} != {bp['expect_state_after']}")
        if bp.get("then_reload"):
            page.goto(url); page.wait_for_load_state("load"); reload_helpers()

    # --- walk -----------------------------------------------------------
    probes = {p["at_state"]: p for p in f["integrity_probes"]}
    for i, st in enumerate(f["walk"]):
        cur = page.evaluate("__c.state()")
        chk(cur == st["state_before"], f"step {i}: state_before {cur} != {st['state_before']}")
        if cur in probes and probes[cur].get("_done") is None:
            p = probes[cur]; page.locator(sel_for(p["action"])).first.click(); page.wait_for_timeout(80)
            chk(page.evaluate("__c.state()") == p["expect_state"], f"integrity probe at {cur} moved state"); p["_done"] = True
        url_before = page.url
        entry = {"i": i, "state_before": cur, "action": st["action"], "kind": st["kind"]}
        if st["kind"] == "scroll":
            page.evaluate(f"window.scrollTo(0,{st['value']})"); page.wait_for_timeout(50)
            entry["scroll_y"] = st["value"]
        else:
            s = sel_for(st["action"]); loc = page.locator(s).first
            chk(loc.count() >= 1 and loc.is_visible(), f"step {i}: control for {st['action']} not visible")
            entry["bbox_before"] = page.evaluate(f"__c.bbox({s!r})")
            occ = page.evaluate(f"__c.occl({s!r})"); entry["occlusion_hittest"] = occ
            if st["action"] != "DISMISS_OBSTRUCTION" and f.get("task_control_occlusion_all_steps") is not None:
                chk(approx(occ, f["task_control_occlusion_all_steps"]), f"step {i}: path control occluded {occ}")
            entry["accessible_name"] = page.evaluate(f"__c.ariaName({s!r})")
            if st["kind"] == "fill": loc.fill(st["value"])
            else: loc.click()
        ok = wait_state(page, st["state_after"])
        entry["state_after"] = page.evaluate("__c.state()"); entry["url_before"], entry["url_after"] = url_before, page.url
        chk(ok, f"step {i}: state_after {entry['state_after']} != {st['state_after']}")
        if st["runner_must_record"]: chk(url_before != page.url, f"step {i}: url did not change (hash) on recorded step")
        else: chk(url_before == page.url, f"step {i}: surface step changed url")
        rec["steps"].append(entry)

    # --- terminal / safety ---------------------------------------------
    term = page.evaluate("__c.terminal()"); rec["terminal"] = term
    chk(term == f["final_terminal"], f"terminal {term} != {f['final_terminal']}")
    if f["final_terminal"] == "ENDPOINT_REACHED":
        chk(page.locator('[data-c-endpoint="REACHED"]').first.is_visible(), "endpoint surface not visible")
    if f["final_terminal"] == "AUTH_GATE":
        chk(page.locator('[data-c-auth-gate]').first.is_visible(), "auth gate surface not visible")
    chk(page.evaluate("__c.forbiddenHit()") == 0, "a forbidden control was activated")
    ne = page.evaluate("__c.forbiddenInputsNonEmpty()"); chk(ne == [], f"forbidden inputs non-empty: {ne}")
    chk(rec["aborted_requests"] == [], f"fixture attempted network: {rec['aborted_requests']}")
    # fixture's own transition log vs expected lossless triples
    tr = [[t["before"], t["action"], t["after"]] for t in page.evaluate("__c.transitions()")
          if t["action"] in set(EXP["token_sets"]["ACTIVATION_SET"]) | {"INPUT_QUERY", "DISMISS_OBSTRUCTION"}]
    rec["fixture_log_triples"] = tr
    chk(tr == f["lossless_check"], f"fixture transition log {tr} != lossless_check {f['lossless_check']}")
    walked = [[s["state_before"], s["action"], s["state_after"]] for s in rec["steps"] if s["kind"] != "scroll"]
    chk(walked == f["lossless_check"], "walker-observed triples != lossless_check")
    # derived-variable self-consistency of EXPECTATIONS with the pre-registered rules
    d = derive(f["task_flow_sequence"])
    for k, v in d.items(): chk(f[k] == v, f"EXPECTATIONS {k}={f[k]} but rule gives {v}")
    chk([t for t in f["experienced_flow_sequence"] if t != "DISMISS_OBSTRUCTION"] == f["task_flow_sequence"], "task != experienced minus DISMISS")
    chk(f["forced_dismissal_count"] == f["experienced_flow_sequence"].count("DISMISS_OBSTRUCTION"), "forced_dismissal_count mismatch")
    chk(f["dismiss_required_for_task"] == (f["forced_dismissal_count"] > 0), "dismiss_required_for_task mismatch")
    chk(("AUTH_GATE" in f["task_flow_sequence"]) == (f["auth_gate_stage"] != "NONE"), "auth_gate_stage vs token mismatch")
    ctx.close()
    rec["fails"] = fails
    return rec

def main():
    results = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        for name, f in EXP["fixtures"].items():
            try: r = walk_one(browser, name, f)
            except Exception as e: r = {"fixture": name, "fails": [f"EXCEPTION {type(e).__name__}: {e}"], "steps": []}
            results.append(r)
        browser.close()
    (OUT / "walk_result.json").write_text(json.dumps(results, ensure_ascii=False, indent=1))
    hdr = "| fixture | role | recorded steps | S0 occl (hit/geo) | S0 overlay cov | fvss | terminal | result |"
    print(hdr); print("|" + "---|" * 8)
    all_ok = True
    for r in results:
        f = EXP["fixtures"][r["fixture"]]; ok = not r["fails"]; all_ok &= ok
        n = sum(1 for s in r["steps"] if s.get("kind") != "scroll")
        occ = r.get("s0_occlusion_hittest"); geo = r.get("s0_occlusion_geometric")
        occs = "n/a" if occ is None else f"{occ:.2f}/{geo:.2f}"
        cov = r.get("s0_overlay_coverage"); covs = "n/a" if cov is None else f"{cov:.3f}"
        print(f"| {r['fixture']} | {f['control_role'].split('_')[0]} | {n}/{len(f['lossless_check'])} | {occs} | {covs} | {r.get('first_visible_scroll_state','?')} | {r.get('terminal','?')} | {'PASS' if ok else 'FAIL: ' + '; '.join(r['fails'])} |")
    print(f"\nRESULT: {'ALL PASS' if all_ok else 'FAIL'} ({sum(1 for r in results if not r['fails'])}/{len(results)} fixtures) -> {OUT/'walk_result.json'}")
    sys.exit(0 if all_ok else 1)

if __name__ == "__main__":
    main()
