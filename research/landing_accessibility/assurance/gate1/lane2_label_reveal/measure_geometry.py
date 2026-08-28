#!/usr/bin/env python3
"""C-authored offline measurement of GATE 1 lane2 fixtures (label separation + reveal direction).

Independent of B code. Opens each fixture via file:// with every non-file request aborted,
reads the entry control through THREE channels (CDP AX tree with name sources; Playwright
aria_snapshot; DOM fallbacks), records bbox before/after the reveal toggle, infers the
reveal direction purely from geometry, and compares against EXPECTATIONS.json.
Zone derivation follows A T-A-V3-STEP1-003 R7 (terciles, [a,b), DRAWER > FLOATING > geometry);
entry_observed_state / nav_container_chain / dom_ax_divergence / null convention follow A T-A-V3-STEP1-012:
nav_container_chain is derived one container per reveal step (outermost ancestor that flips to rendered, typed from its
own geometry; innermost = nav_container_type); dom_ax_divergence compares a naive light-DOM querySelector channel with the
CDP AX node found through the element's backendNodeId (works inside open shadow roots).

Exit 0 only if every fixture PASSes.
"""
from __future__ import annotations
import json, re, sys, time, unicodedata, pathlib
from playwright.sync_api import sync_playwright

HERE = pathlib.Path(__file__).resolve().parent
FIX = HERE / "fixtures"
EXP = json.loads((HERE / "EXPECTATIONS.json").read_text(encoding="utf-8"))
VW, VH = EXP["meta"]["viewport"]["width"], EXP["meta"]["viewport"]["height"]
SYN = EXP["meta"]["synonym_map_fixed"]
OUT = HERE / "out"; OUT.mkdir(exist_ok=True)

def norm(s):  # 04 §5: Unicode normalize + whitespace normalize
    return re.sub(r"\s+", " ", unicodedata.normalize("NFC", s or "")).strip()

def label_relation(vis, ax):
    v, a = norm(vis), norm(ax)
    if not v and not a: return "NONE"
    if not v: return "AX_ONLY"
    if not a: return "VISIBLE_ONLY"
    if v == a: return "MATCH"
    for k, alts in SYN.items():
        group = {norm(k), *map(norm, alts)}
        if v in group and a in group: return "SEMANTIC_EQUIV"
    return "DIFFERENT"

# ---- DOM-side facts (C's own reader; no accessible-name synthesis here) ----
JS_INFO = r"""
(el) => {
  const cs = getComputedStyle(el);
  const r = el.getBoundingClientRect();
  const pseudo = ['::before','::after'].map(p => {
    let c = getComputedStyle(el, p).content;
    if (!c || c === 'none' || c === 'normal') return '';
    return c.replace(/^["']|["']$/g, '');
  }).join('');
  const rendered = el.checkVisibility ? el.checkVisibility({visibilityProperty:true, opacityProperty:true}) : (cs.display !== 'none');
  const inViewport = r.width > 0 && r.height > 0 && r.right > 0 && r.left < innerWidth && r.bottom > 0 && r.top < innerHeight;
  const tag = el.tagName.toLowerCase();
  const type = (el.getAttribute('type') || '').toLowerCase();
  const isInputBtn = tag === 'input' && ['submit','button','reset'].includes(type);
  const imgAlts = [...el.querySelectorAll('img')].map(i => i.getAttribute('alt') || '');
  const svgTitles = [...el.querySelectorAll('svg > title')].map(t => t.textContent || '');
  const hasIcon = !!el.querySelector('svg, img');
  const lb = el.getAttribute('aria-labelledby');
  const lbText = lb ? lb.split(/\s+/).map(id => (document.getElementById(id) || {}).textContent || '').join(' ') : null;
  // nearest ancestor (or self) with fixed/absolute position
  let cont = null, n = el;
  while (n && n !== document.body) { const p = getComputedStyle(n).position; if (p === 'fixed' || p === 'absolute') { cont = n; break; } n = n.parentElement; }
  let contInfo = null;
  if (cont) { const cr = cont.getBoundingClientRect(); contInfo = {position: getComputedStyle(cont).position, x: cr.x, y: cr.y, width: cr.width, height: cr.height, cls: cont.className, id: cont.id, dataState: cont.getAttribute('data-state'), dataSide: cont.getAttribute('data-side'), ariaLabel: cont.getAttribute('aria-label')}; }
  // R7 FLOATING: nearest self-or-ancestor whose computed position is fixed or sticky (no size cap)
  let floatAnchor = null; n = el;
  while (n && n !== document.body) { const p = getComputedStyle(n).position; if (p === 'fixed' || p === 'sticky') { const fr = n.getBoundingClientRect(); floatAnchor = {position: p, tag: n.tagName.toLowerCase(), id: n.id, cls: n.className, width: fr.width, height: fr.height, self: n === el}; break; } n = n.parentElement; }
  // GAP-05: hit-testable at this state = elementFromPoint at the bbox centre is the control or a descendant
  // (shadow-aware: hit-test from the control's own root so a control inside an open shadow root is not reported as covered by its host)
  let hitAtCentre = false;
  if (inViewport) { const root = el.getRootNode(); const hv = (root && root.elementFromPoint) ? root : document;
    const t = hv.elementFromPoint(r.x + r.width / 2, r.y + r.height / 2); hitAtCentre = !!t && (t === el || el.contains(t)); }
  const inShadow = el.getRootNode() !== document;
  return {
    tag, type, role: el.getAttribute('role'), href: el.getAttribute('href'),
    innerText: rendered ? (el.innerText || '') : '', textContent: el.textContent || '',
    pseudo, inputValue: isInputBtn ? (el.value || '') : '',
    ariaLabel: el.getAttribute('aria-label'), ariaLabelledbyText: lbText, title: el.getAttribute('title'),
    imgAlts, svgTitles, hasIcon, rendered, inViewport,
    display: cs.display, visibility: cs.visibility, opacity: cs.opacity,
    bbox: {x: r.x, y: r.y, width: r.width, height: r.height},
    container: contInfo, floatAnchor, hitAtCentre, inShadow, cls: el.className, id: el.id
  };
}
"""

# DOM channel as a selector-based collector sees it: naive light-DOM query, no shadow piercing (STEP1-012 divergence)
JS_NAIVE = r"""
(s) => { const e = document.querySelector(s); if (!e) return {found: false, rendered: false, inViewport: false};
  const r = e.getBoundingClientRect(); const rendered = e.checkVisibility ? e.checkVisibility({visibilityProperty: true, opacityProperty: true}) : true;
  return {found: true, rendered, inViewport: r.width > 0 && r.height > 0 && r.right > 0 && r.left < innerWidth && r.bottom > 0 && r.top < innerHeight}; }
"""

# ancestor chain of the control, inner → outer (hops out of shadow roots via the host), with rendered state and bbox — GAP-06 chain derivation
JS_ANCESTORS = r"""
(el) => { const up = n => n.parentElement || ((n.getRootNode && n.getRootNode().host) || null);
  const out = []; let n = up(el);
  while (n && n !== document.body) { const cs = getComputedStyle(n); const r = n.getBoundingClientRect();
    out.push({tag: n.tagName.toLowerCase(), id: n.id, cls: typeof n.className === 'string' ? n.className : '', position: cs.position,
      rendered: n.checkVisibility ? n.checkVisibility({visibilityProperty: true, opacityProperty: true}) : cs.display !== 'none',
      bbox: {x: r.x, y: r.y, width: r.width, height: r.height}, dataSide: n.getAttribute('data-side'), ariaLabel: n.getAttribute('aria-label'), dataState: n.getAttribute('data-state')});
    n = up(n); }
  return out; }
"""

# CI-14 r2 (RUNBOOK Addendum r8): task-entry candidate enumeration in document order. dom_order = 0-based index inside the
# enumeration (A1 §5.1 structural value); marked_primary = presence of the DOM attribute data-primary-action;
# task_binding_candidate = fixture-declared membership (every element matching candidate_selector). selector = tag#id.
JS_CANDIDATES = r"""
(s) => [...document.querySelectorAll(s)].map((el, i) => ({
  selector: el.tagName.toLowerCase() + (el.id ? '#' + el.id : ''), dom_order: i,
  marked_primary: el.hasAttribute('data-primary-action'), task_binding_candidate: true,
  visible_text: el.innerText || '', tag: el.tagName.toLowerCase(), href: el.getAttribute('href')}))
"""

def delta30_order(cands):
    """Δ30 total order (RULING_INDEX Δ30-tiebreak): task_binding_candidate desc, dom_order asc, selector asc."""
    return [c["selector"] for c in sorted(cands, key=lambda c: (not c["task_binding_candidate"], c["dom_order"], c["selector"]))]

def min4_order(cands):
    """v2 min4_sort_key (A1 §5.1 line 366): marked_primary desc, dom_order asc, selector asc."""
    return [c["selector"] for c in sorted(cands, key=lambda c: (not c["marked_primary"], c["dom_order"], c["selector"]))]

def order_explaining(selected, d30, m4):
    """Which declared order explains a runner's SELECTED (first activated candidate). DELTA30 wins when both agree."""
    if d30 and selected == d30[0]: return "DELTA30"
    if m4 and selected == m4[0]: return "MIN4"
    return "NEITHER"

def cdp_ax(cdp, loc):
    """AX node of the element behind a Playwright locator, located by backendNodeId through a temporary probe attribute
    (DOM.querySelector does not pierce shadow roots; the pierced DOM.getDocument tree does)."""
    tag = loc.evaluate("el => { const t = 'p' + Math.random().toString(36).slice(2); el.setAttribute('data-c-probe', t); return t; }")
    try:
        doc = cdp.send("DOM.getDocument", {"depth": -1, "pierce": True})
        def find(n):
            a = n.get("attributes") or []
            if dict(zip(a[0::2], a[1::2])).get("data-c-probe") == tag: return n
            for ch in (n.get("children") or []) + (n.get("shadowRoots") or []) + ([n["contentDocument"]] if n.get("contentDocument") else []):
                r = find(ch)
                if r: return r
            return None
        node = find(doc["root"])
        if node is None:
            return {"name": "", "role": None, "ignored": True, "sources": [], "error": "element not found in pierced DOM tree"}
        tree = cdp.send("Accessibility.getPartialAXTree", {"backendNodeId": node["backendNodeId"], "fetchRelatives": False})
    finally:
        loc.evaluate("el => el.removeAttribute('data-c-probe')")
    n = tree["nodes"][0]
    name = (n.get("name") or {}).get("value", "") or ""
    srcs = [(s.get("type"), s.get("attribute"), s.get("nativeSource")) for s in (n.get("name") or {}).get("sources", []) if s.get("value") is not None or s.get("attributeValue") is not None]
    return {"name": name, "role": (n.get("role") or {}).get("value"), "ignored": n.get("ignored", False), "sources": srcs}

def aria_snapshot_name(loc):
    try:
        snap = loc.aria_snapshot()
    except Exception as e:
        return None, f"err:{e.__class__.__name__}"
    first = (snap or "").strip().splitlines()[0] if snap and snap.strip() else ""
    m = re.match(r'-\s*(\w+)\s*(?:"(.*)")?', first)
    return (m.group(2) or "" if m else ""), first

def classify_source(info, ax):
    """C's accessible_name_source rule (EXPECTATIONS.meta)."""
    name = norm(ax["name"])
    if not name: return "NONE"
    if info["ariaLabelledbyText"] is not None and norm(info["ariaLabelledbyText"]): return "ARIA_LABELLEDBY"
    if norm(info["ariaLabel"] or ""): return "ARIA_LABEL"
    types = {t for t, _, _ in ax["sources"]}
    attrs = {a for _, a, _ in ax["sources"] if a}
    natives = {n for _, _, n in ax["sources"] if n}
    if natives & {"label", "labelfor", "labelwrapped"}: return "LABEL"
    if info["inputValue"] and norm(info["inputValue"]) == name and ("value" in attrs or True): return "VALUE"
    hits = []
    if norm(info["innerText"]) == name or norm(info["textContent"]) == name: hits.append("VISIBLE_TEXT")
    if norm(info["pseudo"]) == name: hits.append("VISIBLE_TEXT")
    if any(norm(a) == name for a in info["imgAlts"] + info["svgTitles"]): hits.append("ALT")
    if not hits and norm(info["title"] or "") == name: return "TITLE"
    if not hits: return "MIXED"
    return hits[0] if len(set(hits)) == 1 else "MIXED"

def visible_text(info):
    if not info["rendered"] or not info["inViewport"]: return "", "NOT_RENDERED"
    if info["inputValue"]: return norm(info["inputValue"]), "INPUT_VALUE"
    t = norm(info["innerText"]); p = norm(info["pseudo"])
    if t: return (t if not p else norm(p + " " + t) if info["pseudo"] and False else t), "DOM_TEXT"
    if p: return p, "PSEUDO_ELEMENT"
    return "", "DOM_TEXT"

def control_type(info, vis):
    if info["tag"] == "input" and info["inputValue"] != "": return "TEXT_BUTTON"
    is_link = info["tag"] == "a" and info["href"] is not None or info["role"] == "link"
    if vis and info["hasIcon"]: return "ICON_TEXT"
    if vis: return "TEXT_LINK" if is_link else "TEXT_BUTTON"
    if info["hasIcon"]: return "ICON_ONLY"
    return "OTHER"

def modality(vis, ax, info):
    if vis and info["hasIcon"]: return "ICON_TEXT"
    if vis: return "EXPLICIT_TEXT"
    return "ICON_ONLY_AX_NAMED" if norm(ax) else "ICON_ONLY_UNNAMED"

def zone(info, in_reveal_container):
    """A T-A-V3-STEP1-003 R7. Returns (entry_zone, entry_zone_band_R7, x_norm, y_norm); all None when the control is
    not observed at this state (GAP-04: null, never 0)."""
    if not (info["rendered"] and info["inViewport"]):
        return None, None, None, None
    b = info["bbox"]; cx, cy = b["x"] + b["width"] / 2, b["y"] + b["height"] / 2
    xn, yn = cx / VW, cy / VH
    # geometry-only tercile band, [a, b)
    if yn < 1/3: band = "TOP_LEFT" if xn < 1/3 else ("TOP_CENTER" if xn < 2/3 else "TOP_RIGHT")
    elif yn < 2/3: band = "MID"
    else: band = "BOTTOM"
    # structural overrides: DRAWER > FLOATING > geometry
    if in_reveal_container: z = "DRAWER"                                  # inside the reveal-requiring container (any nav_container_type)
    elif info.get("floatAnchor"): z = "FLOATING"                          # self-or-ancestor computed position fixed|sticky, no size cap
    else: z = band
    return z, band, round(xn, 3), round(yn, 3)

def infer_direction(before, after_info):
    """Geometry only. before = bbox dict or None (not laid out)."""
    a = after_info["bbox"]; c = after_info["container"]
    if before and before["width"] > 0:
        dx = (a["x"] + a["width"]/2) - (before["x"] + before["width"]/2)
        dy = (a["y"] + a["height"]/2) - (before["y"] + before["height"]/2)
        if max(abs(dx), abs(dy)) <= 4:
            return ("CENTER" if c else "INLINE"), dx, dy, "no-motion"
        if abs(dx) >= abs(dy): return ("LEFT" if dx > 0 else "RIGHT"), dx, dy, "motion-x"
        return ("TOP" if dy > 0 else "BOTTOM"), dx, dy, "motion-y"
    # not rendered before
    if not c: return "INLINE", None, None, "not-rendered-before/in-flow"
    if c["width"] >= 0.9*VW and c["height"] >= 0.9*VH: return "CENTER", None, None, "not-rendered-before/covers-viewport"
    full_w = c["width"] >= 0.9*VW; full_h = c["height"] >= 0.9*VH
    if full_w and c["y"] <= 60: return "TOP", None, None, "edge-anchor"
    if full_w and c["y"] + c["height"] >= VH - 1: return "BOTTOM", None, None, "edge-anchor"
    if full_h and c["x"] <= 1: return "LEFT", None, None, "edge-anchor"
    if full_h and c["x"] + c["width"] >= VW - 1: return "RIGHT", None, None, "edge-anchor"
    return "CENTER", None, None, "edge-anchor/fallback"

def opened_container(anc_before, anc_after):
    """GAP-06: the container opened by a reveal step = the OUTERMOST ancestor of the control that flips not-rendered → rendered."""
    if len(anc_before) != len(anc_after): return None
    idx = [i for i, (b, a) in enumerate(zip(anc_before, anc_after)) if not b["rendered"] and a["rendered"]]
    if not idx: return None
    i = max(idx); a = anc_after[i]
    return {"tag": a["tag"], "id": a["id"], "cls": a["cls"], "position": a["position"], "bbox_before": anc_before[i]["bbox"], "bbox_after": a["bbox"],
            "dataSide": a["dataSide"], "ariaLabel": a["ariaLabel"]}

def step_direction(ctrl_before, after_info, cont):
    """Direction attributable to ONE reveal step. Control motion when the control was laid out before the step (r2 rule);
    otherwise the geometry of the container opened by the step: in-flow → INLINE; fixed/absolute → motion of its own box, no motion → CENTER,
    no box before → edge anchoring (r2 fallback)."""
    if ctrl_before and ctrl_before["width"] > 0:
        return infer_direction(ctrl_before, after_info)
    if cont is None:
        return infer_direction(None, after_info)
    if cont["position"] in ("static", "relative", "sticky"):
        return "INLINE", None, None, "container-in-flow"
    cb, ca = cont["bbox_before"], cont["bbox_after"]
    if cb and cb["width"] > 0 and ca["width"] > 0:
        dx = (ca["x"] + ca["width"] / 2) - (cb["x"] + cb["width"] / 2); dy = (ca["y"] + ca["height"] / 2) - (cb["y"] + cb["height"] / 2)
        if max(abs(dx), abs(dy)) <= 4: return "CENTER", dx, dy, "container-no-motion"
        if abs(dx) >= abs(dy): return ("LEFT" if dx > 0 else "RIGHT"), dx, dy, "container-motion-x"
        return ("TOP" if dy > 0 else "BOTTOM"), dx, dy, "container-motion-y"
    fake = dict(after_info); fake["container"] = {"x": ca["x"], "y": ca["y"], "width": ca["width"], "height": ca["height"]}
    return infer_direction(None, fake)

def nav_type_from(direction, after_info, steps):
    if not steps: return "NONE"
    c = after_info["container"]
    return {"LEFT": "LEFT_DRAWER", "RIGHT": "RIGHT_DRAWER", "TOP": "TOP_DROPDOWN", "BOTTOM": "BOTTOM_SHEET",
            "CENTER": "MODAL_MENU", "INLINE": "INLINE_EXPAND"}.get(direction, "HAMBURGER")

def naive_name_guess(after_info):
    c = after_info["container"] or {}
    blob = " ".join(str(c.get(k) or "") for k in ("cls", "id", "dataSide", "ariaLabel")).lower()
    for w, d in (("left", "LEFT"), ("왼쪽", "LEFT"), ("right", "RIGHT"), ("오른쪽", "RIGHT"), ("bottom", "BOTTOM"), ("sheet", "BOTTOM"), ("top", "TOP"), ("dropdown", "TOP")):
        if w in blob: return d
    return "?"

def settle_bbox(loc, min_ms=260, max_ms=2500):
    # 1) let the style/transition actually start (two rAF ticks), 2) wait for all CSS transitions/animations
    #    on the page to finish, 3) then require two identical consecutive bbox samples.
    page = loc.page
    page.evaluate("() => new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r)))")
    page.evaluate("() => Promise.race([Promise.all(document.getAnimations().map(a => a.finished.catch(() => null))), new Promise(r => setTimeout(r, 2000))])")
    t0 = time.time(); last = None; stable = 0
    while (time.time() - t0) * 1000 < max_ms:
        b = loc.bounding_box()
        key = None if b is None else tuple(round(v) for v in (b["x"], b["y"], b["width"], b["height"]))
        stable = stable + 1 if key == last else 0
        last = key
        if stable >= 2 and (time.time() - t0) * 1000 >= min_ms: break
        time.sleep(0.06)
    return loc.bounding_box()

NOT_OBSERVED = "NOT_OBSERVED"

def read_control(page, cdp, sel, in_reveal):
    loc = page.locator(sel).first                                          # Playwright pierces open shadow roots
    info = loc.evaluate(JS_INFO)
    ax = cdp_ax(cdp, loc)
    naive = page.evaluate(JS_NAIVE, sel)                                   # DOM channel: naive light-DOM query
    pw_name, pw_line = aria_snapshot_name(loc)
    observed = bool(info["rendered"] and info["inViewport"])          # GAP-04: not rendered / off-viewport => nothing observed at this state
    ax_name = norm(ax["name"]) if observed else NOT_OBSERVED
    vis, prov = visible_text(info) if observed else (NOT_OBSERVED, "NOT_OBSERVED")
    src = (classify_source(info, ax) if ax_name else "NONE") if observed else NOT_OBSERVED
    rel = label_relation(vis, ax_name) if observed else NOT_OBSERVED
    z, band, xn, yn = zone(info, in_reveal)
    fallback = norm(info["ariaLabel"] or "") or norm(info["innerText"])
    dom_exists = bool(naive["found"] and naive["rendered"] and naive["inViewport"])   # DOM channel: naive light-DOM querySelector finds a rendered, in-viewport control
    ax_exists = bool(observed and not ax["ignored"] and ax["role"] is not None)      # AX channel: a non-ignored AX node with a role exists for it
    return {
        "selector": sel, "observed": observed, "visible_label_text": vis, "visible_text_provenance": prov,
        "accessible_name": ax_name, "accessible_name_channel": "CDP Accessibility.getPartialAXTree",
        "ax_role": ax["role"], "ax_ignored": ax["ignored"], "ax_raw_sources": ax["sources"],
        "pw_aria_snapshot_name": pw_name, "pw_aria_snapshot_line": pw_line,
        "dom_fallback_name(ariaLabel|innerText)": fallback,
        "accessible_name_source": src, "label_relation": rel,
        "entry_control_type": control_type(info, vis if observed else ""), "entry_label_modality_of_control": modality(vis if observed else "", ax_name if observed else "", info),
        "rendered": info["rendered"], "in_viewport": info["inViewport"], "hit_at_centre": info["hitAtCentre"], "bbox": info["bbox"] if observed else None,
        "entry_zone": z if observed else NOT_OBSERVED, "entry_zone_band_R7": band if observed else NOT_OBSERVED,
        "entry_x_norm": xn, "entry_y_norm": yn, "container": info["container"], "float_anchor": info.get("floatAnchor"),
        "dom_exists": dom_exists, "ax_exists": ax_exists, "dom_ax_divergence": dom_exists != ax_exists,
        "dom_channel_naive_light_dom": naive, "in_shadow_root": info.get("inShadow"), "_info": info,
    }

def cmp(field, got, exp, diffs):
    if got != exp: diffs.append(f"{field}: got={got!r} exp={exp!r}")

def run_fixture(browser, fx):
    name = fx["fixture"]; exp = fx["expected"]; sel = fx["entry_selector"]
    ctx = browser.new_context(viewport={"width": VW, "height": VH}, is_mobile=True, has_touch=True,
                              device_scale_factor=1, locale="ko-KR", timezone_id="Asia/Seoul")
    aborted = []
    def guard(route):
        u = route.request.url
        if u.startswith("file://"): route.continue_()
        else: aborted.append(u); route.abort()
    ctx.route("**/*", guard)
    page = ctx.new_page()
    page.goto((FIX / f"{name}.html").as_uri(), wait_until="load")
    page.wait_for_timeout(150)
    cdp = ctx.new_cdp_session(page); cdp.send("Accessibility.enable")
    diffs = []; rec = {"fixture": name, "control_role": fx["control_role"]}
    steps = fx.get("reveal_steps", [])
    s0 = read_control(page, cdp, sel, in_reveal=False)
    s0_visible = bool(s0["rendered"] and s0["in_viewport"] and s0["hit_at_centre"])   # GAP-05: bbox in S0 viewport AND hit-testable
    rec["s0"] = {k: v for k, v in s0.items() if k != "_info"}
    cmp("s0_task_control_visible", s0_visible, exp["s0_task_control_visible"], diffs)
    if "s0_entry_x_norm" in exp:                                           # GAP-04: unobserved geometry is null, never 0
        cmp("s0_entry_x_norm", s0["entry_x_norm"], exp["s0_entry_x_norm"], diffs)
        cmp("s0_entry_y_norm", s0["entry_y_norm"], exp["s0_entry_y_norm"], diffs)
    if not s0["observed"]:
        for f in ("visible_label_text", "accessible_name", "accessible_name_source", "label_relation", "entry_zone"):
            if s0[f] != NOT_OBSERVED: diffs.append(f"S0 null convention: {f}={s0[f]!r} for an unobserved control")
    cmp("visible_label_text", s0["visible_label_text"], exp["visible_label_text"], diffs)
    cmp("accessible_name", s0["accessible_name"], exp["accessible_name"], diffs)
    cmp("accessible_name_source", s0["accessible_name_source"], exp["accessible_name_source"], diffs)
    cmp("label_relation", s0["label_relation"], exp["label_relation"], diffs)
    mod = "HIDDEN_UNTIL_REVEAL" if (not s0_visible and steps) else s0["entry_label_modality_of_control"]
    cmp("entry_label_modality", mod, exp["entry_label_modality"], diffs)
    if exp.get("visible_text_provenance"): cmp("visible_text_provenance", s0["visible_text_provenance"], exp["visible_text_provenance"], diffs)
    # cross-channel consistency: Playwright's own accname engine must agree with CDP when exposed
    if s0_visible and s0["pw_aria_snapshot_name"] is not None:
        cmp("pw_aria_snapshot_name==cdp", norm(s0["pw_aria_snapshot_name"]), s0["accessible_name"], diffs)
    for aux in fx.get("aux", []):
        a = read_control(page, cdp, aux["selector"], in_reveal=False)
        rec.setdefault("aux", []).append({k: v for k, v in a.items() if k != "_info"})
        for f, g in (("visible_label_text", a["visible_label_text"]), ("accessible_name", a["accessible_name"]),
                     ("accessible_name_source", a["accessible_name_source"]), ("label_relation", a["label_relation"]),
                     ("entry_label_modality", a["entry_label_modality_of_control"]), ("entry_control_type", a["entry_control_type"])):
            cmp(f"aux[{aux['selector']}].{f}", g, aux[f], diffs)
        if aux.get("visible_text_provenance"): cmp(f"aux[{aux['selector']}].visible_text_provenance", a["visible_text_provenance"], aux["visible_text_provenance"], diffs)
        cmp(f"aux[{aux['selector']}].pw==cdp", norm(a["pw_aria_snapshot_name"] or ""), a["accessible_name"], diffs)
    # ---- reveal ----
    direction, dx, dy, method, naive = "NONE", None, None, "n/a", None
    chain, step_log = [], []
    if steps:
        before = page.locator(sel).first.bounding_box()
        for i, st in enumerate(steps):
            ctrl_before = page.locator(sel).first.bounding_box()
            anc_before = page.locator(sel).first.evaluate(JS_ANCESTORS)
            page.locator(st).first.click()
            settle_bbox(page.locator(sel).first)
            anc_after = page.locator(sel).first.evaluate(JS_ANCESTORS)
            mid = read_control(page, cdp, sel, in_reveal=True)
            if i < len(steps) - 1 and mid["rendered"] and mid["in_viewport"]:
                diffs.append(f"control visible after {i+1} of {len(steps)} steps (depth over-stated)")
            cont = opened_container(anc_before, anc_after)                      # GAP-06: one container per step
            d_i, dx_i, dy_i, m_i = step_direction(ctrl_before, mid["_info"], cont)
            chain.append(nav_type_from(d_i, mid["_info"], steps))
            step_log.append({"step": i, "toggle": st, "direction": d_i, "dx": dx_i, "dy": dy_i, "method": m_i, "container": cont,
                             "control_laid_out_before": bool(ctrl_before and ctrl_before["width"] > 0)})
            direction, dx, dy, method = d_i, dx_i, dy_i, m_i                   # innermost = last step
        s1 = read_control(page, cdp, sel, in_reveal=True)
        rec["s1_after_reveal"] = {k: v for k, v in s1.items() if k != "_info"}
        rec["bbox_before"] = before; rec["reveal_steps_observed"] = step_log
        if not (s1["rendered"] and s1["in_viewport"]): diffs.append("control not visible after reveal steps")
        naive = naive_name_guess(s1["_info"])
        ar = fx.get("after_reveal", {})
        for f in ("visible_label_text", "accessible_name", "accessible_name_source", "label_relation"):
            cmp(f"after_reveal.{f}", s1[f], ar[f], diffs)
        cmp("after_reveal.entry_label_modality", s1["entry_label_modality_of_control"], ar["entry_label_modality"], diffs)
        cmp("after_reveal.pw==cdp", norm(s1["pw_aria_snapshot_name"] or ""), s1["accessible_name"], diffs)
        m = ar.get("motion", {})
        if m.get("axis") == "x":
            if dx is None or (m["sign"] == "+" and dx <= 0) or (m["sign"] == "-" and dx >= 0) or abs(dx) < m["min_abs_delta_px"]:
                diffs.append(f"motion: dx={dx} expected sign {m['sign']} |dx|>={m['min_abs_delta_px']}")
        elif m.get("axis") == "y":
            if dy is None or (m["sign"] == "+" and dy <= 0) or (m["sign"] == "-" and dy >= 0) or abs(dy) < m["min_abs_delta_px"]:
                diffs.append(f"motion: dy={dy} expected sign {m['sign']} |dy|>={m['min_abs_delta_px']}")
        elif m.get("axis") == "none" and m.get("before_rendered", True):
            if dx is None or max(abs(dx), abs(dy)) > m.get("max_abs_delta_px", 4): diffs.append(f"motion: expected none, got dx={dx} dy={dy}")
        elif m.get("before_rendered") is False and before is not None:
            diffs.append(f"expected not laid out before reveal, got bbox {before}")
        zone_src = s1
    else:
        zone_src = s0
    menu_dep = 0 if s0_visible else (1 if steps else None)
    nav_type = chain[-1] if chain else "NONE"                                    # GAP-06: innermost container
    cmp("reveal_direction", direction, exp["reveal_direction"], diffs)
    cmp("nav_container_type", nav_type, exp["nav_container_type"], diffs)
    cmp("menu_dependency", menu_dep, exp["menu_dependency"], diffs)
    cmp("nav_container_depth", len(steps) if menu_dep else 0, exp["nav_container_depth"], diffs)
    cmp("entry_control_type", zone_src["entry_control_type"], exp["entry_control_type"], diffs)
    cmp("entry_zone", zone_src["entry_zone"], exp["entry_zone"], diffs)
    cmp("entry_zone_band_R7", zone_src["entry_zone_band_R7"], exp["entry_zone_band_R7"], diffs)
    # GAP-07: the row declares the state its entry_* facts come from
    observed_state = "S0" if s0["observed"] else (f"POST_REVEAL:{nav_type}" if (steps and zone_src["observed"]) else "NOT_OBSERVED")
    cmp("entry_observed_state", observed_state, exp["entry_observed_state"], diffs)
    # GAP-06: innermost container type + outer->inner chain (one container per reveal step, typed from its own geometry)
    chain = chain if (menu_dep and steps) else []
    cmp("nav_container_chain", chain, exp["nav_container_chain"], diffs)
    if len(chain) != (len(steps) if menu_dep else 0): diffs.append("nav_container_chain length != nav_container_depth")
    cmp("dom_ax_divergence", zone_src["dom_ax_divergence"], exp["dom_ax_divergence"], diffs)
    rec["entry_observed_state"] = observed_state; rec["nav_container_chain"] = chain
    if fx.get("naive_name_guess"):
        rec["naive_name_guess_observed"] = naive
        cmp("naive_name_guess(negative control must disagree with geometry)", naive, fx["naive_name_guess"], diffs)
        if naive == direction: diffs.append("negative control ineffective: naive guess equals geometry")
    # ---- CI-14 r2: candidate order (Δ30 vs min4) recomputed from the observed candidate list ----
    order_str = ""
    if fx.get("candidate_selector"):
        oc = fx["order_controls"]
        cands = page.evaluate(JS_CANDIDATES, fx["candidate_selector"])
        d30, m4 = delta30_order(cands), min4_order(cands)
        cmp("candidates.dom_order", [c["selector"] for c in cands], oc["expected_candidates_dom_order"], diffs)
        cmp("candidates.marked_primary", {c["selector"]: c["marked_primary"] for c in cands}, oc["expected_marked_primary"], diffs)
        cmp("candidates.task_binding_candidate", {c["selector"]: c["task_binding_candidate"] for c in cands}, oc["expected_task_binding_candidate"], diffs)
        cmp("delta30_order", d30, oc["expected_delta30_order"], diffs)
        cmp("min4_order", m4, oc["expected_min4_order"], diffs)
        cmp("first_under_delta30_order", d30[0] if d30 else None, oc["expected_first_under_delta30_order"], diffs)
        cmp("first_under_min4_order", m4[0] if m4 else None, oc["expected_first_under_min4_order"], diffs)
        if d30 and m4 and d30[0] == m4[0]: diffs.append("order divergence not live: Δ30 first == min4 first (fixture cannot test CI-14 r2)")
        # mutation controls (comparator must be able to fail): a min4-walked SELECTED must be flagged, the Δ30 first must not
        flag_sel = oc["expected_first_under_min4_order"]; flag_verdict = order_explaining(flag_sel, d30, m4)
        ok_sel = d30[0] if d30 else None; ok_verdict = order_explaining(ok_sel, d30, m4)
        must_flag = flag_verdict != "DELTA30"; must_not_flag = ok_verdict == "DELTA30" and ok_sel == oc["expected_first_under_delta30_order"]
        if not must_flag: diffs.append(f"must_flag control ineffective: SELECTED={flag_sel} explained as {flag_verdict}")
        if not must_not_flag: diffs.append(f"must_not_flag control failed: SELECTED={ok_sel} explained as {ok_verdict}")
        rec["candidates"] = cands
        rec["order"] = {"delta30_order": d30, "min4_order": m4, "first_under_delta30_order": d30[0] if d30 else None,
                        "first_under_min4_order": m4[0] if m4 else None, "divergence_live": bool(d30 and m4 and d30[0] != m4[0]),
                        "controls": {"must_flag": {"fake_runner_selected": flag_sel, "order_explaining": flag_verdict, "flagged": must_flag},
                                     "must_not_flag": {"observed_selected": ok_sel, "order_explaining": ok_verdict, "passed": must_not_flag}}}
        order_str = f"Δ30={d30[0] if d30 else '-'}|min4={m4[0] if m4 else '-'}"
    if aborted: diffs.append(f"non-file requests attempted: {aborted}")
    rec.update({"observed_direction": direction, "direction_method": method, "dx": dx, "dy": dy,
                "non_file_requests_aborted": len(aborted), "diffs": diffs, "result": "PASS" if not diffs else "FAIL"})
    ctx.close()
    return rec, zone_src, mod, menu_dep, direction, naive, order_str

def main():
    rows = []; records = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        for fx in EXP["fixtures"]:
            rec, zs, mod, dep, d, naive, order_str = run_fixture(browser, fx)
            records.append(rec)
            rows.append([fx["fixture"], fx["control_role"][:3], repr(rec["s0"]["visible_label_text"]), repr(rec["s0"]["accessible_name"]),
                         rec["s0"]["accessible_name_source"], mod, rec["s0"]["label_relation"], zs["entry_control_type"],
                         "T" if rec["s0"]["rendered"] and rec["s0"]["in_viewport"] else "F", d,
                         "" if rec["dx"] is None else f"{rec['dx']:+.0f}", "" if rec["dy"] is None else f"{rec['dy']:+.0f}",
                         zs["entry_zone"], zs["entry_zone_band_R7"], f"{zs['entry_x_norm']:.2f},{zs['entry_y_norm']:.2f}", rec["entry_observed_state"], ">".join(rec["nav_container_chain"]) or "-",
                         "T" if rec["s0"]["dom_ax_divergence"] or (rec.get("s1_after_reveal") or {}).get("dom_ax_divergence") else "F", naive or "", order_str, rec["result"]])
        browser.close()
    hdr = ["fixture", "ctl", "visible", "ax_name", "ax_src", "modality", "relation", "ctype", "s0", "dir", "dx", "dy", "zone(R7)", "band", "x,y", "observed_state", "chain", "domax", "naive", "order", "result"]
    widths = [max(len(str(r[i])) for r in [hdr] + rows) for i in range(len(hdr))]
    lines = [" | ".join(str(c).ljust(w) for c, w in zip(r, widths)) for r in [hdr, ["-" * w for w in widths]] + rows]
    print("\n".join(lines))
    for r in records:
        for d in r["diffs"]: print(f"  !! {r['fixture']}: {d}")
    n_pass = sum(r["result"] == "PASS" for r in records)
    line = f"RESULT: {n_pass}/{len(records)} PASS, non-file requests aborted total={sum(r['non_file_requests_aborted'] for r in records)}"
    print(line)
    (OUT / "measure_result.json").write_text(json.dumps({"summary": line, "table": lines, "records": records}, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
    sys.exit(0 if n_pass == len(records) else 1)

if __name__ == "__main__":
    main()
