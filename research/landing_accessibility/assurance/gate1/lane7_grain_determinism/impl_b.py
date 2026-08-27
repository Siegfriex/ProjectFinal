#!/usr/bin/env python3
"""impl_B — source axis = DOM_AX.
Reads the fixture HTML with lxml (XPath; cssselect is not installed) and derives the same fields as impl_a.py
from DOM structure, ARIA attributes and *inline* CSS only (a tiny layout resolver for position:fixed/absolute
with px or inset/100% values — the CSS subset the fixtures use). Standalone on purpose: shares no code with impl_a.
Definition: DISMISS_DEFINITION_C.md §2-§6."""
from __future__ import annotations
import json, re, sys, unicodedata, pathlib
from lxml import html as LH

VW, VH = 390, 844
ABSENT = "NAME_ABSENT"
LEX_EQ = {"닫기", "닫음", "창닫기", "팝업닫기", "레이어닫기", "close", "dismiss", "closepopup", "x", "×", "✕", "✖"}
LEX_SUB = ("닫기", "보지않", "열지않")
ATTR_RE = re.compile(r"(^|[-_ ])(close|dismiss|btn-?x)([-_ ]|$)", re.I)
COLS = ["dismiss_control_exists", "dismiss_control_visible", "dismiss_control_accessible_name",
        "dismiss_required_for_task", "task_control_occlusion", "dismiss_control_hittable_s0", "selected_selector"]


class Page:
    def __init__(self, path):
        self.path = pathlib.Path(path)
        self.root = LH.fromstring(self.path.read_bytes())
        self.order = {el: i for i, el in enumerate(self.root.iter())}

    # ---------- style / geometry ----------
    @staticmethod
    def style(el):
        d = {}
        for part in (el.get("style") or "").split(";"):
            if ":" in part:
                k, v = part.split(":", 1)
                d[k.strip().lower()] = v.strip().lower()
        return d

    @staticmethod
    def px(v, ref):
        if v is None:
            return None
        v = v.strip()
        if v.endswith("px"):
            return float(v[:-2])
        if v.endswith("%"):
            return float(v[:-1]) / 100 * ref
        if v in ("0", "auto"):
            return 0.0 if v == "0" else None
        return None

    def containing_block(self, el):
        st = self.style(el).get("position")
        if st == "fixed":
            return (0.0, 0.0, float(VW), float(VH))
        for anc in el.iterancestors():
            if self.style(anc).get("position") in ("fixed", "absolute", "relative", "sticky"):
                return self.rect(anc)
        return (0.0, 0.0, float(VW), float(VH))

    def rect(self, el):
        """Rect (x,y,w,h) in S0 viewport coords, or None if the element is not positioned with explicit values."""
        s = self.style(el)
        if s.get("position") not in ("fixed", "absolute", "sticky"):
            return None
        cb = self.containing_block(el)
        if cb is None:
            return None
        if s.get("inset") == "0":
            return cb
        left, top = self.px(s.get("left"), cb[2]), self.px(s.get("top"), cb[3])
        w, h = self.px(s.get("width"), cb[2]), self.px(s.get("height"), cb[3])
        right, bottom = self.px(s.get("right"), cb[2]), self.px(s.get("bottom"), cb[3])
        if w is None and left is not None and right is not None:
            w = cb[2] - left - right
        if h is None and top is not None and bottom is not None:
            h = cb[3] - top - bottom
        if left is None and right is not None and w is not None:
            left = cb[2] - right - w
        if top is None and bottom is not None and h is not None:
            top = cb[3] - bottom - h
        if None in (left, top, w, h):
            return None
        return (cb[0] + left, cb[1] + top, w, h)

    # ---------- visibility / exposure ----------
    def rendered(self, el):
        for e in [el] + list(el.iterancestors()):
            s = self.style(e)
            if s.get("display") == "none" or s.get("visibility") == "hidden" or e.get("hidden") is not None:
                return False
        r = self.rect(el)
        return r is not None and r[2] > 0 and r[3] > 0

    def ax_exposed(self, el):
        return self.rendered(el) and not any((e.get("aria-hidden") or "").strip() == "true" for e in [el] + list(el.iterancestors()))

    # ---------- naming ----------
    def text_of(self, el):
        parts = []
        for e in el.iter():
            if e.tag == "img" and e.get("alt"):
                parts.append(e.get("alt"))
            if e.text:
                parts.append(e.text)
            if e is not el and e.tail:
                parts.append(e.tail)
        return " ".join(" ".join(parts).split())

    def dom_name(self, el):
        if (el.get("aria-label") or "").strip():
            return " ".join(el.get("aria-label").split())
        if el.get("aria-labelledby"):
            ids = el.get("aria-labelledby").split()
            txt = " ".join(self.text_of(t) for i in ids for t in self.root.xpath(f'//*[@id="{i}"]'))
            if txt.strip():
                return txt.strip()
        t = self.text_of(el)
        if t:
            return t
        for a in ("title", "value"):
            if (el.get(a) or "").strip():
                return el.get(a).strip()
        return ""

    @staticmethod
    def norm(s):
        s = unicodedata.normalize("NFKC", s).casefold()
        return "".join(c for c in s if not c.isspace() and c not in "._-")

    def is_dismiss(self, el):
        n = self.norm(self.dom_name(el))
        if n in LEX_EQ or any(sub in n for sub in LEX_SUB):
            return True
        return bool(ATTR_RE.search(el.get("id") or "") or ATTR_RE.search(el.get("class") or ""))

    @staticmethod
    def is_control(el):
        tag = el.tag if isinstance(el.tag, str) else ""
        role = (el.get("role") or "").strip()
        return (tag == "button" or (tag == "a" and el.get("href") is not None)
                or (tag == "input" and (el.get("type") or "").lower() in ("button", "submit", "image"))
                or role in ("button", "link"))

    # ---------- containers ----------
    def task_control(self):
        els = self.root.xpath('//*[@data-c-control="task-entry"]')
        if len(els) != 1:
            raise SystemExit(f"{self.path.name}: expected exactly one task-entry control, got {len(els)}")
        return els[0]

    def containers(self):
        task = self.task_control()
        task_chain = {task} | set(task.iterancestors())
        found = []
        for el in self.root.iter():
            if not isinstance(el.tag, str):
                continue
            role = (el.get("role") or "").strip()
            pos = self.style(el).get("position")
            if not (role in ("dialog", "alertdialog") or pos in ("fixed", "sticky")):
                continue
            if el in task_chain or any(a in found for a in el.iterancestors()):
                continue
            found.append(el)
        return task, found

    def selector(self, el):
        if el.get("id"):
            return "#" + el.get("id")
        return "/" + "/".join(f"{a.tag}[{a.getparent().index(a) + 1 if a.getparent() is not None else 1}]"
                              for a in list(reversed(list(el.iterancestors()))) + [el])

    def z(self, el):
        try:
            return int(self.style(el).get("z-index", "0"))
        except ValueError:
            return 0

    # ---------- derivation ----------
    def analyse(self):
        task, conts = self.containers()
        trect = self.rect(task)
        cont_rects = [(c, self.rect(c), self.z(c), self.order[c]) for c in conts]

        def covered(pt, own):
            oz, oo = self.z(own), self.order[own]
            for c, r, cz, co in cont_rects:
                if c is own or r is None:
                    continue
                if (cz, co) > (oz, oo) and r[0] <= pt[0] <= r[0] + r[2] and r[1] <= pt[1] <= r[1] + r[3]:
                    return True
            return False

        def inter(a, b):
            if a is None or b is None:
                return 0.0
            return max(0.0, min(a[0] + a[2], b[0] + b[2]) - max(a[0], b[0])) * max(0.0, min(a[1] + a[3], b[1] + b[3]) - max(a[1], b[1]))

        V = (0.0, 0.0, float(VW), float(VH))
        facts = []
        for c, crect, cz, corder in cont_rects:
            cid = c.get("id")
            cands_el = [e for e in c.iter() if isinstance(e.tag, str) and self.is_control(e) and self.is_dismiss(e)]
            if cid:
                cands_el += [e for e in self.root.xpath(f'//*[@aria-controls="{cid}"]') if self.is_control(e) and self.is_dismiss(e) and e not in cands_el]
            cands = []
            for e in cands_el:
                r = self.rect(e)
                rendered = self.rendered(e)
                vis = rendered and inter(r, V) > 0
                ax = self.ax_exposed(e)
                hit = vis and not covered((r[0] + r[2] / 2, r[1] + r[3] / 2), c)
                nm = self.dom_name(e) if ax else ""
                cands.append(dict(sel=self.selector(e), vis=vis, ax=ax, hit=hit, name=nm or ABSENT, order=self.order[e]))
            tv = inter(trect, V)
            o = None if tv <= 0 else round(inter((max(trect[0], 0), max(trect[1], 0), min(trect[0] + trect[2], VW) - max(trect[0], 0),
                                                  min(trect[1] + trect[3], VH) - max(trect[1], 0)), crect) / tv, 3)
            required = (o or 0) > 0 or (c.get("aria-modal") or "").strip() == "true"
            cands.sort(key=lambda k: (not k["vis"], not k["ax"], not k["hit"], k["order"]))
            pick = cands[0] if cands else None
            facts.append(dict(id=self.selector(c), z=cz, order=corder, exists=bool(cands),
                              visible=(any(k["vis"] for k in cands) if cands else None),
                              name=(pick["name"] if pick else None), required=bool(required), occl=o,
                              hit=(pick["hit"] if pick else None), sel=(pick["sel"] if pick else None)))
        facts.sort(key=lambda f: (-f["z"], f["order"]))
        return facts


def fields(f):
    return dict(zip(COLS, (f["exists"], f["visible"], f["name"], f["required"], f["occl"], f["hit"], f["sel"])))


def target(P):
    if not P:
        return dict(zip(COLS, (None, None, None, False, 0.0, None, None)))
    missing = any(not f["exists"] for f in P)
    return dict(zip(COLS, (
        not missing,
        False if (missing or any(f["visible"] is False for f in P)) else True,
        json.dumps([f["name"] for f in P], ensure_ascii=False),
        any(f["required"] for f in P),
        max((f["occl"] or 0.0) for f in P),
        False if (missing or any(f["hit"] is False for f in P)) else True,
        json.dumps([f["sel"] for f in P], ensure_ascii=False))))


def run(path):
    pg = Page(path)
    facts = pg.analyse()
    fx = pg.path.name
    rows = []
    for pop in ("all", "blocking"):
        P = [f for f in facts if pop == "all" or f["required"]]
        rows += [dict(fixture=fx, unit="container", population=pop, row_id=f["id"], **fields(f)) for f in P]
        rows.append(dict(fixture=fx, unit="target", population=pop, row_id="TARGET", **target(P)))
        rows += [dict(fixture=fx, unit="step", population=pop, row_id=f"step{i}:{f['id']}", **fields(f))
                 for i, f in enumerate(f for f in facts if f["required"])]
    return rows


if __name__ == "__main__":
    for a in sys.argv[1:]:
        for r in run(a):
            print(json.dumps(r, ensure_ascii=False))
