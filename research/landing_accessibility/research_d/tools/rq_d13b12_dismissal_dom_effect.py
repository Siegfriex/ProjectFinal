"""RQ-D13b-1 · RQ-D13b-2 — H1_NO_EFFECT 는 무대상인가, H4_PIXEL_ONLY 의 원인은 무엇인가.

선행 RQ-D13b(`tools/rq_d13b_dismissal_effect.py`, `results/RQ_D13B_dismissal_effect.json`)가
l0c dismissal step 249건 중 248건을 4분류했다. 그 두 잔여 질문을 여기서 연다.

  RQ-D13b-1  H1_NO_EFFECT 로 분류된 step 에서 dismiss target 이 애초에 실재했는가.
  RQ-D13b-2  H4_PIXEL_ONLY(픽셀 변화 · DOM 바이트 동일)의 원인은 무엇인가.

**원 정의를 재정의하지 않는다.** 선행 코드의 판정식을 그대로 재구현해 수치를 먼저 재현하고
(재현 실패 시 그 사실을 결과에 남긴다), 그 위에 새 측정을 얹는다.

핵심 사실 (exact SHA 2281c853950d0c475c5d2c1678680b971c2804f4 의 engine/l0_collector.py 에서 읽음):
  - `interrupt_index` = `probe.raw_features.modal_overlay_candidates` 의 **enumerate 인덱스**이고
    `l0c/{interrupt_index}/` 가 그대로 step 디렉터리다. 따라서 step k ↔ probe 후보 k 가 1:1 이다.
  - dismiss 대상 control 은 `probe.raw_features.dismiss_control_candidates` 를
    `container_selector == overlay.selector` 로 조인해 얻는다.
  - method 선택 순서: visible control 클릭 → dialog.close() → (control 있으나 not hittable)
    → Escape 키. 즉 **control 이 하나도 없으면 Escape 만 눌린다.**

read-only. production/control/holdout 미접근. 산출은 results/ 아래 새 파일만.
"""
from __future__ import annotations

import hashlib
import json
import math
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
from html_decode import parse_html  # noqa: E402  (D-DEF-01: 바이트 직접 파싱 금지)

REPO = Path("/home/sieg/projects-wsl/ProjectFinal")
RD = Path(__file__).resolve().parents[1]
RESULTS = RD / "results"
FIGURES = RD / "figures"
TABLE = RESULTS / "D_OBSERVATION_TABLE_v2.csv"
PRIOR_JSON = RESULTS / "RQ_D13B_dismissal_effect.json"
MART = REPO / ".agent_worktrees/claude_b_analysis_current/artifacts/e001_real_marts/fact_interrupt_element.json"
CODE_SHA = "2281c853950d0c475c5d2c1678680b971c2804f4"

EVIDENCE_ROOTS = {
    f"w{n}": REPO / f".agent_worktrees/claude_b_e001_worker_{n}/artifacts/e001_w{n}/evidence"
    for n in ("01", "02", "03", "04")
}
WTG_RE = re.compile(r"^e001_full-wtg_([0-9a-f]+)-")
STEP_RE = re.compile(r"l0c/(\d+)/screen_(before|after)\.png$")
DOM_STEP_RE = re.compile(r"l0c/(\d+)/dom_after\.html$")
L0A_DOM_RE = re.compile(r"l0a/dom\.html$")

RNG_SEED = 20260828
PIXEL_DELTA = 8          # 채널 최대차 > 8 을 "눈에 띄는 변화" 로 본다 (임계값 민감도 병기)
INTERACTIVE_XPATH = ("//a[@href] | //button | //input | //select | //textarea | "
                     "//*[@role='button'] | //*[@role='link']")
VIS_ATTRS = ("style", "class", "hidden", "aria-hidden", "aria-modal", "open", "aria-expanded")


# ── 통계 ──────────────────────────────────────────────────────────────────────
def wilson(k: int, n: int, z: float = 1.959963985) -> tuple[float, float, float]:
    if n == 0:
        return (float("nan"), float("nan"), float("nan"))
    p = k / n
    d = 1 + z * z / n
    c = p + z * z / (2 * n)
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return (p, (c - h) / d, (c + h) / d)


def wl(k: int, n: int) -> dict:
    p, lo, hi = wilson(k, n)
    return {"k": k, "n": n, "p": None if n == 0 else round(p, 4),
            "wilson95": [None, None] if n == 0 else [round(lo, 4), round(hi, 4)]}


def phi_and_perm(a: list[int], b: list[int], iters: int = 20000) -> dict:
    """2x2 φ 와 permutation p (양측, |φ| 기준). n<4 이거나 한쪽이 상수면 NOT_TESTABLE."""
    x = np.asarray(a, dtype=np.int8)
    y = np.asarray(b, dtype=np.int8)
    n = len(x)
    if n < 4 or x.min() == x.max() or y.min() == y.max():
        return {"phi": None, "p_perm": None, "n": n, "status": "NOT_TESTABLE_CONSTANT_MARGIN",
                "table": _tab(x, y)}

    def _phi(u, v):
        n11 = int(((u == 1) & (v == 1)).sum()); n10 = int(((u == 1) & (v == 0)).sum())
        n01 = int(((u == 0) & (v == 1)).sum()); n00 = int(((u == 0) & (v == 0)).sum())
        den = math.sqrt((n11 + n10) * (n01 + n00) * (n11 + n01) * (n10 + n00))
        return 0.0 if den == 0 else (n11 * n00 - n10 * n01) / den

    obs = _phi(x, y)
    rng = np.random.default_rng(RNG_SEED)
    hit = 0
    yy = y.copy()
    for _ in range(iters):
        rng.shuffle(yy)
        if abs(_phi(x, yy)) >= abs(obs) - 1e-12:
            hit += 1
    return {"phi": round(obs, 4), "p_perm": round((hit + 1) / (iters + 1), 5),
            "n": n, "iters": iters, "status": "OK", "table": _tab(x, y)}


def _tab(x, y) -> dict:
    return {"n11": int(((x == 1) & (y == 1)).sum()), "n10": int(((x == 1) & (y == 0)).sum()),
            "n01": int(((x == 0) & (y == 1)).sum()), "n00": int(((x == 0) & (y == 0)).sum())}


def mwu(a: list[float], b: list[float], iters: int = 20000) -> dict:
    """Mann-Whitney U 의 permutation 판 (분포가정 없이). 효과크기는 공통언어효과 A."""
    a = [v for v in a if v is not None]
    b = [v for v in b if v is not None]
    if len(a) < 3 or len(b) < 3:
        return {"status": "NOT_TESTABLE_SMALL_N", "n_a": len(a), "n_b": len(b)}
    A = np.asarray(a, float); B = np.asarray(b, float)

    def _cl(u, v):
        m = (u[:, None] > v[None, :]).sum() + 0.5 * (u[:, None] == v[None, :]).sum()
        return m / (len(u) * len(v))

    obs = _cl(A, B)
    pool = np.concatenate([A, B]); na = len(A)
    rng = np.random.default_rng(RNG_SEED)
    hit = 0
    for _ in range(iters):
        rng.shuffle(pool)
        if abs(_cl(pool[:na], pool[na:]) - 0.5) >= abs(obs - 0.5) - 1e-12:
            hit += 1
    return {"status": "OK", "n_a": len(A), "n_b": len(B),
            "median_a": round(float(np.median(A)), 6), "median_b": round(float(np.median(B)), 6),
            "common_language_effect_a_gt_b": round(float(obs), 4),
            "p_perm": round((hit + 1) / (iters + 1), 5), "iters": iters}


# ── selector → XPath (probe 의 sel() 문법만 지원한다) ─────────────────────────
PART_RE = re.compile(r"^([a-zA-Z][\w-]*)(?:#(.+?))?(?::nth-of-type\((\d+)\))?$")


def sel_to_xpath(sel: str) -> str | None:
    """probe.js sel() 이 만드는 `tag#id>tag:nth-of-type(n)>…` 만 번역한다."""
    if not sel:
        return None
    steps = []
    for i, part in enumerate(sel.split(">")):
        m = PART_RE.match(part.strip())
        if not m:
            return None
        tag, ident, nth = m.group(1), m.group(2), m.group(3)
        if ident:
            ident = re.sub(r"\\(.)", r"\1", ident)
            steps.append(f'{tag}[@id="{ident}"]' if '"' not in ident else None)
            if steps[-1] is None:
                return None
        elif nth:
            steps.append(f"{tag}[{int(nth)}]")
        else:
            steps.append(tag)
        if i == 0:
            steps[0] = "//" + steps[0]
    return steps[0] + ("/" + "/".join(steps[1:]) if len(steps) > 1 else "")


def query(tree, sel: str) -> list:
    xp = sel_to_xpath(sel)
    if xp is None:
        return []
    try:
        return tree.xpath(xp)
    except Exception:
        return []


# ── DOM 특징 ─────────────────────────────────────────────────────────────────
def _h(items) -> str:
    return hashlib.sha256("␟".join(items).encode("utf-8")).hexdigest()


def dom_feat(path: Path) -> dict | None:
    try:
        raw = path.read_bytes()
        tree, enc = parse_html(path)
    except Exception:
        return None
    els = tree.xpath("//*")
    tags = [e.tag if isinstance(e.tag, str) else "#nonelem" for e in els]
    struct = []
    vis = []
    for e, t in zip(els, tags):
        depth = 0
        p = e.getparent()
        while p is not None and depth < 64:
            depth += 1
            p = p.getparent()
        struct.append(f"{depth}:{t}")
        a = e.attrib
        vis.append(f"{t}|" + "|".join(f"{k}={a.get(k, '')}" for k in VIS_ATTRS))
    body = tree.find("body")
    txt = " ".join((body.text_content() if body is not None else "").split())
    cnt = Counter(tags)
    return {
        "bytes": len(raw), "encoding": enc, "sha256": hashlib.sha256(raw).hexdigest(),
        "element_n": len(els),
        "body_element_n": len(body.xpath(".//*")) if body is not None else 0,
        "interactive_n": len(set(tree.xpath(INTERACTIVE_XPATH))),
        "body_text_len": len(txt),
        "struct_hash": _h(struct), "vis_hash": _h(vis),
        "iframe_n": cnt.get("iframe", 0), "img_n": cnt.get("img", 0),
        "canvas_n": cnt.get("canvas", 0), "video_n": cnt.get("video", 0),
        "svg_n": cnt.get("svg", 0), "template_n": cnt.get("template", 0),
        "script_n": cnt.get("script", 0), "style_n": cnt.get("style", 0),
        "_tree": tree,
    }


def subtree_sig(tree, sel: str) -> dict:
    els = query(tree, sel)
    if not els:
        return {"present": False, "match_n": 0, "struct_hash": None, "vis_hash": None,
                "element_n": None, "own_attrs": None}
    e = els[0]
    sub = e.xpath(".//*")
    tags = [x.tag if isinstance(x.tag, str) else "#nonelem" for x in sub]
    vis = []
    for x, t in zip(sub, tags):
        a = x.attrib
        vis.append(f"{t}|" + "|".join(f"{k}={a.get(k, '')}" for k in VIS_ATTRS))
    own = {k: e.attrib.get(k, "") for k in VIS_ATTRS}
    return {"present": True, "match_n": len(els), "struct_hash": _h(tags), "vis_hash": _h(vis),
            "element_n": len(sub), "own_attrs": own}


# ── 픽셀 ──────────────────────────────────────────────────────────────────────
def load_img(p: Path):
    try:
        im = Image.open(p).convert("RGB")
        return np.asarray(im, dtype=np.uint8)
    except Exception:
        return None


def pix_diff(a, b) -> dict | None:
    if a is None or b is None:
        return None
    if a.shape != b.shape:
        return {"status": "SHAPE_MISMATCH", "shape_a": list(a.shape), "shape_b": list(b.shape)}
    d = np.abs(a.astype(np.int16) - b.astype(np.int16)).max(axis=2)
    n = d.size
    any_ = d > 0
    strong = d > PIXEL_DELTA
    out = {"status": "OK", "h": int(a.shape[0]), "w": int(a.shape[1]),
           "frac_any": round(float(any_.mean()), 6),
           "frac_gt8": round(float(strong.mean()), 6),
           "frac_gt32": round(float((d > 32).mean()), 6),
           "mean_abs": round(float(d.mean()), 4), "max_abs": int(d.max())}
    ys, xs = np.nonzero(strong)
    if ys.size:
        out["bbox"] = [int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1]
        out["bbox_area_frac"] = round(float((xs.max() + 1 - xs.min()) * (ys.max() + 1 - ys.min())) / n * 3, 6)
        # 변화 행 분포 — 스크롤/전면재도색이면 전 구간에 퍼진다
        rows = strong.any(axis=1)
        out["changed_row_frac"] = round(float(rows.mean()), 6)
    else:
        out["bbox"] = None
        out["bbox_area_frac"] = 0.0
        out["changed_row_frac"] = 0.0
    return out


def box_overlap_frac(diff_bbox, overlay_box, dpr: float, img_w: int, img_h: int):
    """diff bbox 중 overlay 박스(CSS px) 안에 들어가는 비율. 좌표계 변환 포함."""
    if not diff_bbox or not overlay_box:
        return None
    ox = overlay_box.get("x"); oy = overlay_box.get("y")
    ow = overlay_box.get("w"); oh = overlay_box.get("h")
    if None in (ox, oy, ow, oh):
        return None
    ax0, ay0 = max(0.0, ox * dpr), max(0.0, oy * dpr)
    ax1, ay1 = min(float(img_w), (ox + ow) * dpr), min(float(img_h), (oy + oh) * dpr)
    bx0, by0, bx1, by1 = diff_bbox
    iw = max(0.0, min(ax1, bx1) - max(ax0, bx0))
    ih = max(0.0, min(ay1, by1) - max(ay0, by0))
    darea = max(1.0, (bx1 - bx0) * (by1 - by0))
    return round(iw * ih / darea, 4)


# ── engine 판정식 재구현 (l0_collector.py _build_interrupts / _dismiss_pass) ──
def engine_best(controls: list[dict]) -> dict | None:
    return next((c for c in controls if c.get("hittable")), controls[0] if controls else None)


def engine_visible_flag(best: dict | None) -> int | None:
    if not best:
        return None
    return int(
        best.get("display") != "none"
        and best.get("visibility") != "hidden"
        and float(best.get("opacity") or 1) > 0.01
        and float(best.get("viewport_overlap_css_px2") or 0) > 0
        and bool(best.get("hittable"))
    )


def engine_method(controls: list[dict], is_dialog: bool, visible_flag) -> str:
    """실제 눌린 경로. 예외(클릭 timeout)는 정적으로 알 수 없으므로 '의도된 경로' 다."""
    best = engine_best(controls)
    if visible_flag and best:
        return "CONTROL_CLICK"
    if is_dialog:
        return "DIALOG_CLOSE"
    if controls:
        return "CONTROL_CLICK_NOT_HITTABLE"
    return "ESCAPE_KEY"


def collect() -> tuple[list[dict], dict]:
    import csv
    meta_rows = {r["run_dir"]: r for r in csv.DictReader(TABLE.open(encoding="utf-8"))}
    mart = {}
    if MART.exists():
        for r in json.load(MART.open(encoding="utf-8")):
            mart[r["interrupt_id"]] = r

    steps: list[dict] = []
    denom = Counter()
    for worker, root in EVIDENCE_ROOTS.items():
        for d in sorted(p for p in root.iterdir() if p.is_dir()):
            man = d / "manifest.jsonl"
            if not man.exists():
                denom["run_dir_no_manifest"] += 1
                continue
            denom["run_dir"] += 1
            recs = [json.loads(x) for x in man.read_text().splitlines() if x.strip()]
            obs_id = recs[0]["observation_id"]
            shas: dict[int, dict] = defaultdict(dict)
            dom_sha: dict[int, str] = {}
            base_dom_sha = None
            for r in recs:
                m = STEP_RE.search(r["relpath"])
                if m:
                    shas[int(m.group(1))][m.group(2)] = r["sha256"]
                dm = DOM_STEP_RE.search(r["relpath"])
                if dm:
                    dom_sha[int(dm.group(1))] = r["sha256"]
                if L0A_DOM_RE.search(r["relpath"]):
                    base_dom_sha = r["sha256"]
            if not shas:
                denom["run_dir_without_l0c"] += 1
                continue
            denom["run_dir_with_l0c"] += 1

            obs_dir = d / obs_id
            meta = meta_rows.get(d.name, {})
            probe_path = obs_dir / "l0a" / "probe.json"
            probe = None
            if probe_path.exists():
                try:
                    probe = json.load(probe_path.open(encoding="utf-8"))
                except Exception:
                    probe = None
            raw = (probe or {}).get("raw_features", {})
            mocs = raw.get("modal_overlay_candidates", []) or []
            by_container = {x.get("container_selector"): x
                            for x in (raw.get("dismiss_control_candidates") or [])}
            vp = raw.get("viewport", {}) or {}
            dpr = float(vp.get("device_pixel_ratio") or 1)
            motion = raw.get("motion", {}) or {}
            n_anim = len(motion.get("animated_elements") or [])
            n_autoplay = len(motion.get("autoplay_media") or [])
            n_inf = int(motion.get("infinite_animation_count") or 0)
            scroll_locked = bool((raw.get("body_scroll_lock") or {}).get("locked"))

            base_dom = obs_dir / "l0a" / "dom.html"
            prev = dom_feat(base_dom) if base_dom.exists() else None
            prev_sha = base_dom_sha
            prev_after_img = None       # 직전 step 의 screen_after — 무조작 대조군용
            prev_step = None

            for order, k in enumerate(sorted(shas)):
                denom["step"] += 1
                v = shas[k]
                cur_dom_path = obs_dir / "l0c" / str(k) / "dom_after.html"
                cur = dom_feat(cur_dom_path) if cur_dom_path.exists() else None
                cur_sha = dom_sha.get(k)
                pixel_same = ("before" in v and "after" in v and v["before"] == v["after"])

                cand = mocs[k] if (probe is not None and k < len(mocs)) else None
                cont = by_container.get(cand.get("selector")) if cand else None
                controls = (cont or {}).get("dismiss_control_candidates") or []
                is_dialog = bool((cont or {}).get("is_dialog_element"))
                best = engine_best(controls)
                vflag = engine_visible_flag(best)
                method = engine_method(controls, is_dialog, vflag) if cand is not None else None

                rec = {
                    "worker": worker,
                    "run_dir": d.name,
                    "wtg": (WTG_RE.match(d.name).group(1) if WTG_RE.match(d.name) else d.name),
                    "observation_id": obs_id,
                    "service": meta.get("prior_service"),
                    "archetype": meta.get("prior_archetype"),
                    "step": k, "step_order": order, "is_first_step": order == 0,
                    "pixel_same_sha": pixel_same,
                    "probe_available": probe is not None,
                    "probe_index_in_range": cand is not None,
                    "dom_available": cur is not None and prev is not None,
                    "dom_sha_available": cur_sha is not None and prev_sha is not None,
                    # ── RQ-D13b-1 : 대상 실재 3단계 (probe = l0a 시점) ──
                    "n_dismiss_controls": len(controls),
                    "target_exists": (None if cand is None else int(bool(best))),
                    "target_visible": (None if cand is None else int(bool(vflag))),
                    "target_hittable": (None if cand is None else
                                        int(any(bool(c.get("hittable")) for c in controls))),
                    "is_dialog_element": (None if cand is None else int(is_dialog)),
                    "has_form_method_dialog": (None if cand is None else
                                               int(bool((cont or {}).get("has_form_method_dialog")))),
                    "engine_method": method,
                    "overlay_selector": (cand or {}).get("selector"),
                    "overlay_visible_at_l0a": (None if cand is None else int(bool(cand.get("visible")))),
                    "overlay_hittable_at_l0a": (None if cand is None else int(bool(cand.get("hittable")))),
                    "overlay_coverage": (cand or {}).get("viewport_coverage"),
                    "overlay_box": (cand or {}).get("box"),
                    "n_animated_elements": n_anim, "n_infinite_animation": n_inf,
                    "n_autoplay_media": n_autoplay, "body_scroll_locked": int(scroll_locked),
                    "dpr": dpr,
                }
                mrow = mart.get(f"{obs_id}-{k}")
                rec["in_mart"] = mrow is not None
                if mrow:
                    rec["mart_dismiss_control_exists"] = mrow.get("dismiss_control_exists")
                    rec["mart_dismiss_control_visible"] = mrow.get("dismiss_control_visible")
                    rec["mart_dismiss_succeeded"] = mrow.get("dismiss_succeeded")
                    rec["mart_final_label"] = mrow.get("final_label")
                    rec["mart_selector"] = mrow.get("selector")

                # ── DOM 변화: 5개 기준 ──
                if cur and prev:
                    rec["d_element_n"] = cur["element_n"] - prev["element_n"]
                    rec["d_interactive_n"] = cur["interactive_n"] - prev["interactive_n"]
                    rec["d_body_text_len"] = cur["body_text_len"] - prev["body_text_len"]
                    rec["d_bytes"] = cur["bytes"] - prev["bytes"]
                    rec["cur_element_n"] = cur["element_n"]
                    rec["iframe_n"] = cur["iframe_n"]; rec["img_n"] = cur["img_n"]
                    rec["canvas_n"] = cur["canvas_n"]; rec["video_n"] = cur["video_n"]
                    rec["svg_n"] = cur["svg_n"]; rec["script_n"] = cur["script_n"]
                    same_bytes = (cur_sha is not None and prev_sha is not None
                                  and cur_sha == prev_sha)
                    # sha 는 manifest 값. 파일 재해시로 왕복 검증한다.
                    rec["sha_roundtrip_ok"] = (cur_sha is None or cur_sha == cur["sha256"])
                    rec["dom_change"] = {
                        "C1_BYTES": int(not same_bytes),
                        "C2_SUMMARY_COUNTS": int(not (rec["d_element_n"] == 0
                                                      and rec["d_interactive_n"] == 0
                                                      and rec["d_body_text_len"] == 0
                                                      and rec["d_bytes"] == 0)),
                        "C3_STRUCT_HASH": int(cur["struct_hash"] != prev["struct_hash"]),
                        "C4_VIS_ATTRS": int(cur["vis_hash"] != prev["vis_hash"]),
                    }
                    sel = rec["overlay_selector"]
                    if sel:
                        s_cur = subtree_sig(cur["_tree"], sel)
                        s_prev = subtree_sig(prev["_tree"], sel)
                        rec["overlay_subtree"] = {
                            "present_before": s_prev["present"], "present_after": s_cur["present"],
                            "match_n_before": s_prev["match_n"], "match_n_after": s_cur["match_n"],
                            "element_n_before": s_prev["element_n"], "element_n_after": s_cur["element_n"],
                            "own_attrs_before": s_prev["own_attrs"], "own_attrs_after": s_cur["own_attrs"],
                        }
                        changed = int(s_prev["present"] != s_cur["present"]
                                      or s_prev["struct_hash"] != s_cur["struct_hash"]
                                      or s_prev["vis_hash"] != s_cur["vis_hash"])
                        rec["dom_change"]["C5_OVERLAY_SUBTREE"] = changed
                        rec["overlay_present_before_step"] = int(s_prev["present"])
                        rec["overlay_present_after_step"] = int(s_cur["present"])
                        # dismiss control 이 step 직전 DOM 에 실재했는가 (정적 재확인)
                        if best and best.get("selector"):
                            rec["control_selector"] = best["selector"]
                            rec["control_in_dom_before_step"] = int(bool(query(prev["_tree"],
                                                                              best["selector"])))
                            rec["control_in_dom_after_step"] = int(bool(query(cur["_tree"],
                                                                             best["selector"])))
                    else:
                        rec["dom_change"]["C5_OVERLAY_SUBTREE"] = None
                    # 원 분류 재현 (선행 RQ-D13b 와 동일 판정식)
                    rec["classification"] = (
                        "H1_NO_EFFECT" if pixel_same and same_bytes else
                        "H2_DOM_ONLY" if pixel_same and not same_bytes else
                        "H4_PIXEL_ONLY" if not pixel_same and same_bytes else "EFFECTIVE")
                else:
                    rec["classification"] = "DOM_UNAVAILABLE"
                    rec["dom_change"] = {}

                # ── 픽셀 ──
                bp = obs_dir / "l0c" / str(k) / "screen_before.png"
                ap = obs_dir / "l0c" / str(k) / "screen_after.png"
                before_img = load_img(bp) if bp.exists() else None
                after_img = load_img(ap) if ap.exists() else None
                rec["pix"] = pix_diff(before_img, after_img)
                if rec["pix"] and rec["pix"].get("status") == "OK":
                    rec["pix"]["overlay_overlap_frac"] = box_overlap_frac(
                        rec["pix"]["bbox"], rec["overlay_box"], dpr,
                        rec["pix"]["w"], rec["pix"]["h"])
                # 무조작 대조군: 직전 step 의 screen_after ↔ 이번 step 의 screen_before.
                # 그 사이에는 dom_after 캡처밖에 없다. 조작이 전혀 없는 구간이다.
                if prev_after_img is not None and before_img is not None:
                    rec["pix_control_gap"] = pix_diff(prev_after_img, before_img)
                    rec["pix_control_gap_from_step"] = prev_step
                prev_after_img = after_img
                prev_step = k

                steps.append(rec)
                prev = cur or prev
                prev_sha = dom_sha.get(k, prev_sha)
            # tree 참조 해제
            if prev:
                prev.pop("_tree", None)
    for s in steps:
        s.pop("_tree", None)
    return steps, dict(denom)


# ── 원 정의 (선행 코드에서 그대로 인용) ──────────────────────────────────────
ORIGINAL_DEFINITIONS = {
    "source_code": "research_d/tools/rq_d13b_dismissal_effect.py",
    "source_result": "research_d/results/RQ_D13B_dismissal_effect.json",
    "pixel_same": ('manifest 의 sha256 기준 `v["before"] == v["after"]` — '
                   'l0c/{k}/screen_before.png 과 screen_after.png 의 바이트 동일성'),
    "dom_same": ('`dom_same = (cur_sha is not None and prev_sha is not None and cur_sha == prev_sha)` — '
                 'step k 의 dom_after.html sha256 이 step k-1 의 dom_after.html sha256 과 같은가. '
                 'step 0 은 l0a/dom.html 의 sha256 을 prev 로 쓴다. l0c 에 dom_before 슬롯이 없어서다.'),
    "H1_NO_EFFECT": "`if pixel_same and dom_same` — 픽셀 바이트 동일 AND DOM 바이트 동일",
    "H2_DOM_ONLY": "`elif pixel_same and not dom_same` — 픽셀 동일, DOM 바이트 변화",
    "H4_PIXEL_ONLY": "`elif not pixel_same and dom_same` — 픽셀 변화, DOM 바이트 동일",
    "EFFECTIVE": "`else` — 둘 다 변화",
    "DOM_UNAVAILABLE": "cur/prev DOM 중 하나라도 파싱 불가",
    "redefined_by_this_rq": False,
    "note": ("이 RQ 는 위 정의를 재정의하지 않는다. 동일 판정식을 재구현해 수치를 재현한 뒤 "
             "(replication 블록 참조) 그 위에 새 측정을 얹는다. DOM 변화 기준을 바꾼 결과는 "
             "sensitivity 블록에 C1~C5 로 병기하며, C1_BYTES 가 원 정의다."),
}

DOM_CRITERIA_DEFS = {
    "C1_BYTES": "dom_after.html 파일 바이트 sha256 불일치 (원 정의). 가장 민감하다.",
    "C2_SUMMARY_COUNTS": "element_n·interactive_n·body_text_len·bytes 중 하나라도 변함. 요약치 기준.",
    "C3_STRUCT_HASH": "(깊이:태그) 문서순 시퀀스 해시 불일치. 속성·텍스트 무시, 구조만.",
    "C4_VIS_ATTRS": f"모든 요소의 (태그, {', '.join(VIS_ATTRS)}) 시퀀스 해시 불일치. 가시성 속성만.",
    "C5_OVERLAY_SUBTREE": "overlay selector 로 잡히는 서브트리의 존재/구조/가시성속성 변화만.",
}


def _f(v):
    if isinstance(v, (np.integer,)):
        return int(v)
    if isinstance(v, (np.floating,)):
        return float(v)
    if isinstance(v, (np.bool_,)):
        return bool(v)
    if isinstance(v, dict):
        return {k: _f(x) for k, x in v.items()}
    if isinstance(v, list):
        return [_f(x) for x in v]
    return v


def sample_dump(rows: list[dict], n: int = 12) -> list[dict]:
    keys = ("worker", "run_dir", "observation_id", "step", "step_order", "service", "archetype",
            "classification", "engine_method", "n_dismiss_controls", "target_exists",
            "target_visible", "target_hittable", "is_dialog_element",
            "overlay_selector", "control_selector", "overlay_present_before_step",
            "overlay_present_after_step", "control_in_dom_before_step",
            "mart_dismiss_control_exists", "mart_dismiss_control_visible", "mart_dismiss_succeeded",
            "n_animated_elements", "n_infinite_animation", "iframe_n", "img_n", "canvas_n",
            "video_n", "d_element_n", "d_bytes", "sha_roundtrip_ok")
    out = []
    for r in rows[:n]:
        o = {k: r.get(k) for k in keys if k in r}
        p = r.get("pix") or {}
        o["pix_frac_gt8"] = p.get("frac_gt8")
        o["pix_frac_any"] = p.get("frac_any")
        o["pix_changed_row_frac"] = p.get("changed_row_frac")
        o["pix_overlay_overlap_frac"] = p.get("overlay_overlap_frac")
        c = r.get("pix_control_gap") or {}
        o["control_gap_frac_gt8"] = c.get("frac_gt8")
        o["dom_change"] = r.get("dom_change")
        out.append(_f(o))
    return out


def analyse(steps: list[dict], denom: dict) -> dict:
    ev = [r for r in steps if r["classification"] != "DOM_UNAVAILABLE"]
    cls = Counter(r["classification"] for r in ev)
    H1 = [r for r in ev if r["classification"] == "H1_NO_EFFECT"]
    H2 = [r for r in ev if r["classification"] == "H2_DOM_ONLY"]
    H4 = [r for r in ev if r["classification"] == "H4_PIXEL_ONLY"]
    EFF = [r for r in ev if r["classification"] == "EFFECTIVE"]

    prior = json.loads(PRIOR_JSON.read_text(encoding="utf-8")) if PRIOR_JSON.exists() else {}
    prior_cls = prior.get("classification_all", {})
    replication = {
        "prior_file": str(PRIOR_JSON.relative_to(RD.parent)),
        "prior_n_steps_total": prior.get("n_steps_total"),
        "prior_n_steps_evaluable": prior.get("n_steps_evaluable"),
        "prior_classification_all": prior_cls,
        "this_n_steps_total": len(steps),
        "this_n_steps_evaluable": len(ev),
        "this_classification_all": dict(cls),
        "exact_match": (prior_cls == dict(cls)
                        and prior.get("n_steps_total") == len(steps)
                        and prior.get("n_steps_evaluable") == len(ev)),
    }

    # ── 분모 체인 ──
    mappable = [r for r in ev if r["probe_index_in_range"]]
    chain = {
        "0_run_dirs_scanned": denom.get("run_dir", 0),
        "1_run_dirs_with_l0c": denom.get("run_dir_with_l0c", 0),
        "2_dismissal_attempt_steps": len(steps),
        "3_classifiable_dom_available": len(ev),
        "3_lost": len(steps) - len(ev),
        "3_lost_reason": "dom_after.html 부재 또는 파싱 실패",
        "4_probe_mappable_for_RQ1": len(mappable),
        "4_lost": len(ev) - len(mappable),
        "4_lost_reason": "l0a/probe.json 부재(관측 2건) 또는 step index 가 후보 배열 밖",
        "by_class": dict(cls),
        "H1_probe_mappable": sum(1 for r in H1 if r["probe_index_in_range"]),
        "H4_probe_mappable": sum(1 for r in H4 if r["probe_index_in_range"]),
    }

    # ── RQ-D13b-1 : 대상 실재 3단계 funnel ──
    def funnel(rows):
        m = [r for r in rows if r["probe_index_in_range"]]
        n = len(m)
        return {
            "n_mappable": n,
            "a_exists": wl(sum(r["target_exists"] for r in m), n),
            "b_visible": wl(sum(r["target_visible"] for r in m), n),
            "c_hittable": wl(sum(r["target_hittable"] for r in m), n),
            "no_control_at_all": wl(sum(1 for r in m if r["n_dismiss_controls"] == 0), n),
            "is_dialog_element": wl(sum(r["is_dialog_element"] for r in m), n),
            "actionable_any": wl(sum(1 for r in m
                                     if r["target_visible"] or r["is_dialog_element"]), n),
            "engine_method": dict(Counter(r["engine_method"] for r in m)),
            "n_controls_hist": dict(Counter(min(r["n_dismiss_controls"], 5) for r in m)),
        }

    rq1 = {
        "question": "H1_NO_EFFECT 로 분류된 step 에서 dismiss target 이 애초에 실재했는가",
        "measurement_source": ("l0a/probe.json 의 raw_features.dismiss_control_candidates 를 "
                               "overlay 후보 selector 로 조인. engine 의 _build_interrupts / "
                               "_dismiss_pass 판정식을 그대로 재구현했다."),
        "stage_definitions": {
            "a_exists": "container 의 dismiss_control_candidates 리스트가 비어있지 않다 (engine 의 dismiss_control_exists 와 동일식)",
            "b_visible": ("engine 의 dismiss_control_visible: display!=none AND visibility!=hidden "
                          "AND opacity>0.01 AND viewport_overlap_css_px2>0 AND hittable"),
            "c_hittable": "controls 중 hittable=true 가 하나라도 있다",
        },
        "funnel_H1_NO_EFFECT": funnel(H1),
        "funnel_H4_PIXEL_ONLY": funnel(H4),
        "funnel_H2_DOM_ONLY": funnel(H2),
        "funnel_EFFECTIVE": funnel(EFF),
        "funnel_ALL_EVALUABLE": funnel(ev),
    }

    # overlay 가 step 직전 DOM 에 실재했는가 (정적 DOM 재확인 · probe 시점 의존 없음)
    def overlay_presence(rows):
        m = [r for r in rows if r.get("overlay_present_before_step") is not None]
        n = len(m)
        return {
            "n_checked": n,
            "present_before_step": wl(sum(r["overlay_present_before_step"] for r in m), n),
            "present_after_step": wl(sum(r["overlay_present_after_step"] for r in m), n),
            "removed_by_step": wl(sum(1 for r in m if r["overlay_present_before_step"]
                                      and not r["overlay_present_after_step"]), n),
        }
    rq1["overlay_presence_H1"] = overlay_presence(H1)
    rq1["overlay_presence_H4"] = overlay_presence(H4)
    rq1["overlay_presence_EFFECTIVE"] = overlay_presence(EFF)
    rq1["overlay_presence_ALL"] = overlay_presence(ev)

    def ctrl_presence(rows):
        m = [r for r in rows if r.get("control_in_dom_before_step") is not None]
        n = len(m)
        return {"n_checked": n,
                "control_in_dom_before_step": wl(sum(r["control_in_dom_before_step"] for r in m), n),
                "control_in_dom_after_step": wl(sum(r["control_in_dom_after_step"] for r in m), n)}
    rq1["control_dom_presence_H1"] = ctrl_presence(H1)
    rq1["control_dom_presence_ALL"] = ctrl_presence(ev)

    # mart 교차검증 (내 재구현 vs engine 산출)
    xchk = Counter()
    disagree = []
    for r in ev:
        if not r.get("in_mart") or not r["probe_index_in_range"]:
            continue
        me = r["target_exists"]
        them = r.get("mart_dismiss_control_exists")
        them = None if them in (None, "None") else int(them)
        xchk["compared"] += 1
        if them is None:
            xchk["mart_null"] += 1
        elif me == them:
            xchk["agree_exists"] += 1
        else:
            xchk["disagree_exists"] += 1
            disagree.append(r)
        mv = r.get("mart_dismiss_control_visible")
        mv = None if mv in (None, "None") else int(mv)
        myv = r["target_visible"] if r["target_exists"] else None
        if mv is None and myv is None:
            xchk["agree_visible_bothnull"] += 1
        elif mv == myv:
            xchk["agree_visible"] += 1
        else:
            xchk["disagree_visible"] += 1
    rq1["mart_cross_validation"] = {
        "purpose": ("상위계층 결함 보고 전 내 파싱 오류를 배제하기 위한 왕복검증. "
                    "frozen mart fact_interrupt_element.json 의 engine 산출 dismiss_control_exists/"
                    "visible 와 내가 probe 에서 독립 재계산한 값을 interrupt_id=obs-idx 로 조인 비교."),
        "counts": dict(xchk),
        "agreement_exists": wl(xchk["agree_exists"], xchk["agree_exists"] + xchk["disagree_exists"]),
        "disagreement_samples": sample_dump(disagree, 10),
    }
    # mart 의 dismiss_succeeded 분포 (ALREADY_GONE 의 직접 지표)
    def succ(rows):
        m = [r for r in rows if r.get("mart_dismiss_succeeded") not in (None, "None")]
        n = len(m)
        return {"n_in_mart": n,
                "succeeded": wl(sum(1 for r in m if int(r["mart_dismiss_succeeded"]) == 1), n)}
    rq1["mart_dismiss_succeeded_H1"] = succ(H1)
    rq1["mart_dismiss_succeeded_H4"] = succ(H4)
    rq1["mart_dismiss_succeeded_EFFECTIVE"] = succ(EFF)
    rq1["mart_dismiss_succeeded_ALL"] = succ(ev)

    return {"ev": ev, "H1": H1, "H2": H2, "H4": H4, "EFF": EFF,
            "cls": dict(cls), "replication": replication, "chain": chain, "rq1": rq1}


def analyse_rq2(A: dict) -> dict:
    ev, H1, H4, EFF, H2 = A["ev"], A["H1"], A["H4"], A["EFF"], A["H2"]
    px = lambda r, f="frac_gt8": ((r.get("pix") or {}).get(f)
                                  if (r.get("pix") or {}).get("status") == "OK" else None)
    cg = lambda r, f="frac_gt8": ((r.get("pix_control_gap") or {}).get(f)
                                  if (r.get("pix_control_gap") or {}).get("status") == "OK" else None)

    # dom 이 바이트 동일한 step 만 놓고 (H1 ∪ H4) "픽셀이 왜 바뀌었나" 를 본다.
    dom_same_rows = [r for r in ev if r["dom_change"].get("C1_BYTES") == 0]
    y = [0 if r["classification"] == "H1_NO_EFFECT" else 1 for r in dom_same_rows]

    def assoc(pred, name, rows=None, yy=None):
        rows = rows if rows is not None else dom_same_rows
        yy = yy if yy is not None else y
        x = [int(bool(pred(r))) for r in rows]
        d = phi_and_perm(x, yy)
        d["predictor"] = name
        return d

    rq2 = {
        "question": "H4_PIXEL_ONLY(픽셀 변화 · DOM 바이트 동일)의 원인은 무엇인가",
        "design": ("DOM 바이트가 동일한 step 만 남기면 그 안의 대비는 정확히 H1(픽셀도 동일) vs "
                   "H4(픽셀만 변함) 이다. 이 부분모집단에서 '무엇이 픽셀 변화를 예측하는가' 를 잰다. "
                   "y=1 이 H4."),
        "n_dom_same": len(dom_same_rows),
        "n_H1": len(H1), "n_H4": len(H4),
        "sanity_partition": (len(H1) + len(H4)) == len(dom_same_rows),
    }

    # ── 무조작 대조군: 직전 step 의 after ↔ 이번 step 의 before (그 사이 조작 없음) ──
    ctrl_vals = [cg(r) for r in ev if cg(r) is not None]
    h4_vals = [px(r) for r in H4 if px(r) is not None]
    eff_vals = [px(r) for r in EFF if px(r) is not None]
    h1_vals = [px(r) for r in H1 if px(r) is not None]
    rq2["passive_drift_control"] = {
        "definition": ("screen_after[k-1] ↔ screen_before[k]. 코드상 그 사이에는 dom_after 캡처밖에 "
                       "없고 어떤 조작도 없다. 따라서 이 쌍의 픽셀 변화는 페이지 자체 변화(애니메이션·"
                       "지연렌더·광고교체)의 하한 추정치다."),
        "n": len(ctrl_vals),
        "frac_gt8_median": round(float(np.median(ctrl_vals)), 6) if ctrl_vals else None,
        "frac_gt8_mean": round(float(np.mean(ctrl_vals)), 6) if ctrl_vals else None,
        "share_with_any_change": wl(sum(1 for v in ctrl_vals if v > 0), len(ctrl_vals)),
        "share_gt_1pct": wl(sum(1 for v in ctrl_vals if v > 0.01), len(ctrl_vals)),
    }
    rq2["pixel_change_magnitude"] = {
        "H1_NO_EFFECT": {"n": len(h1_vals), "median": round(float(np.median(h1_vals)), 6) if h1_vals else None},
        "H4_PIXEL_ONLY": {"n": len(h4_vals),
                          "median": round(float(np.median(h4_vals)), 6) if h4_vals else None,
                          "mean": round(float(np.mean(h4_vals)), 6) if h4_vals else None,
                          "share_gt_1pct": wl(sum(1 for v in h4_vals if v > 0.01), len(h4_vals)),
                          "share_gt_10pct": wl(sum(1 for v in h4_vals if v > 0.10), len(h4_vals))},
        "EFFECTIVE": {"n": len(eff_vals),
                      "median": round(float(np.median(eff_vals)), 6) if eff_vals else None,
                      "share_gt_10pct": wl(sum(1 for v in eff_vals if v > 0.10), len(eff_vals))},
        "H4_vs_EFFECTIVE": mwu(h4_vals, eff_vals),
        "H4_vs_passive_drift_control": mwu(h4_vals, ctrl_vals),
    }
    # paired: 같은 step 에서 (조작구간 변화) vs (무조작구간 변화)
    paired = [(px(r), cg(r)) for r in H4 if px(r) is not None and cg(r) is not None]
    if len(paired) >= 3:
        a = np.array([p[0] for p in paired]); b = np.array([p[1] for p in paired])
        rng = np.random.default_rng(RNG_SEED)
        obs = float(np.median(a - b))
        cnt = 0
        for _ in range(20000):
            s = rng.integers(0, 2, size=len(a)) * 2 - 1
            if abs(float(np.median((a - b) * s))) >= abs(obs) - 1e-15:
                cnt += 1
        rq2["paired_action_vs_gap_within_H4"] = {
            "n_pairs": len(paired), "median_action": round(float(np.median(a)), 6),
            "median_gap": round(float(np.median(b)), 6),
            "median_difference": round(obs, 6),
            "p_perm_sign_flip": round((cnt + 1) / 20001, 5),
            "note": ("조작구간과 무조작구간의 픽셀 변화가 비슷하면 H4 의 픽셀 변화는 "
                     "dismissal 때문이 아니라 페이지 자체 변화라는 뜻이다."),
        }
    else:
        rq2["paired_action_vs_gap_within_H4"] = {"status": "NOT_TESTABLE_SMALL_N",
                                                 "n_pairs": len(paired)}

    # ── 경쟁가설별 예측자 ──
    rq2["predictors_within_dom_same"] = {
        "H-13b2-ANIMATION": [
            assoc(lambda r: r.get("n_animated_elements", 0) > 0, "n_animated_elements>0"),
            assoc(lambda r: r.get("n_infinite_animation", 0) > 0, "n_infinite_animation>0"),
            assoc(lambda r: r.get("n_autoplay_media", 0) > 0, "n_autoplay_media>0"),
        ],
        "H-13b2-LAZY_RENDER": [
            assoc(lambda r: (r.get("iframe_n") or 0) > 0, "iframe_n>0"),
            assoc(lambda r: (r.get("img_n") or 0) >= 20, "img_n>=20"),
            assoc(lambda r: (r.get("script_n") or 0) >= 20, "script_n>=20"),
        ],
        "H-13b2-DOM_INSENSITIVE": [
            assoc(lambda r: (r.get("canvas_n") or 0) > 0 or (r.get("video_n") or 0) > 0,
                  "canvas_n>0 or video_n>0"),
        ],
        "H-13b2-REAL_PIXEL_ONLY": [
            assoc(lambda r: r.get("engine_method") == "CONTROL_CLICK", "engine_method==CONTROL_CLICK"),
            assoc(lambda r: bool(r.get("target_visible")), "target_visible==1"),
            assoc(lambda r: r.get("engine_method") == "ESCAPE_KEY", "engine_method==ESCAPE_KEY"),
        ],
    }

    # DOM_INSENSITIVE 의 직접 검사 — 더 둔감/민감한 기준으로 H4 가 뒤집히는가
    flips = Counter()
    for r in H4:
        for c, v in r["dom_change"].items():
            if v == 1:
                flips[c] += 1
    rq2["dom_insensitivity_direct_check"] = {
        "n_H4": len(H4),
        "H4_steps_flagged_changed_by_criterion": dict(flips),
        "note": ("C1_BYTES 가 가장 민감한 기준이므로 C2~C4 가 H4 를 '변화' 로 뒤집는 일은 "
                 "구조적으로 불가능하다. C5 는 부분집합 기준이라 역시 뒤집지 못한다. "
                 "따라서 DOM_INSENSITIVE 가 성립하려면 page.content() 직렬화가 보지 못하는 "
                 "내용(iframe 내부 문서·shadow DOM·canvas 픽셀·video 프레임)이 있어야 한다."),
        "H4_with_iframe": wl(sum(1 for r in H4 if (r.get("iframe_n") or 0) > 0), len(H4)),
        "H4_with_canvas_or_video": wl(sum(1 for r in H4 if (r.get("canvas_n") or 0) > 0
                                          or (r.get("video_n") or 0) > 0), len(H4)),
        "ALL_with_iframe": wl(sum(1 for r in ev if (r.get("iframe_n") or 0) > 0), len(ev)),
        "sha_roundtrip_failures": sum(1 for r in ev if r.get("sha_roundtrip_ok") is False),
        "sha_roundtrip_checked": sum(1 for r in ev if "sha_roundtrip_ok" in r),
        "roundtrip_note": ("manifest 의 sha256 과 내가 파일에서 직접 계산한 sha256 을 전 step 비교했다. "
                           "불일치 0 이면 '내 해싱/경로 매핑이 틀렸다' 는 가능성이 배제된다."),
    }

    # 변화 위치: overlay 위인가 바깥인가
    def loc(rows):
        v = [(r.get("pix") or {}).get("overlay_overlap_frac") for r in rows]
        v = [x for x in v if x is not None]
        rowfrac = [(r.get("pix") or {}).get("changed_row_frac") for r in rows]
        rowfrac = [x for x in rowfrac if x is not None]
        return {"n": len(v),
                "median_overlay_overlap_frac": round(float(np.median(v)), 4) if v else None,
                "share_mostly_on_overlay_ge_0.5": wl(sum(1 for x in v if x >= 0.5), len(v)),
                "median_changed_row_frac": round(float(np.median(rowfrac)), 4) if rowfrac else None,
                "share_full_repaint_rowfrac_ge_0.9": wl(sum(1 for x in rowfrac if x >= 0.9),
                                                        len(rowfrac))}
    rq2["change_localisation"] = {"H4_PIXEL_ONLY": loc(H4), "EFFECTIVE": loc(EFF),
                                 "note": ("diff bbox 가 overlay 박스 안에 얼마나 들어가는가. "
                                          "overlay 위가 아니면 dismissal 이 만든 변화로 보기 어렵다. "
                                          "changed_row_frac 가 1 에 가까우면 스크롤/전면재도색이다.")}
    return rq2


def sensitivity(A: dict) -> dict:
    ev = A["ev"]
    out = {"criteria": DOM_CRITERIA_DEFS, "classification_by_criterion": {}, "agreement_with_C1": {}}
    for c in ("C1_BYTES", "C2_SUMMARY_COUNTS", "C3_STRUCT_HASH", "C4_VIS_ATTRS", "C5_OVERLAY_SUBTREE"):
        cnt = Counter()
        n_def = 0
        agree = 0
        for r in ev:
            v = r["dom_change"].get(c)
            if v is None:
                cnt["UNDEFINED"] += 1
                continue
            n_def += 1
            ps = r["pixel_same_sha"]
            cnt["H1_NO_EFFECT" if ps and v == 0 else
                "H2_DOM_ONLY" if ps and v == 1 else
                "H4_PIXEL_ONLY" if (not ps) and v == 0 else "EFFECTIVE"] += 1
            if r["dom_change"].get("C1_BYTES") == v:
                agree += 1
        out["classification_by_criterion"][c] = dict(cnt)
        out["agreement_with_C1"][c] = wl(agree, n_def)
    # 픽셀 임계값 민감도
    px_sens = {}
    for f, thr in (("frac_any", 0.0), ("frac_gt8", 0.0), ("frac_gt8", 0.001),
                   ("frac_gt8", 0.01), ("frac_gt32", 0.0)):
        cnt = Counter()
        for r in ev:
            p = r.get("pix") or {}
            if p.get("status") != "OK":
                cnt["UNDEFINED"] += 1
                continue
            changed = (p.get(f) or 0) > thr
            v = r["dom_change"].get("C1_BYTES")
            cnt["H1_NO_EFFECT" if (not changed) and v == 0 else
                "H2_DOM_ONLY" if (not changed) and v == 1 else
                "H4_PIXEL_ONLY" if changed and v == 0 else "EFFECTIVE"] += 1
        px_sens[f"{f}>{thr}"] = dict(cnt)
    out["pixel_criterion_sensitivity"] = px_sens
    out["pixel_criterion_note"] = ("원 정의는 PNG 바이트 sha256 동일성이다. 아래는 실제 픽셀값으로 "
                                   "다시 잰 것이다. sha 는 같은데 픽셀도 같아야 정상이며, "
                                   "sha 가 다른데 픽셀 차이가 0 이면 PNG 인코딩 차이다.")
    # sha 동일성 vs 실제 픽셀 동일성 불일치 (원 정의의 타당성 검사)
    mism = [r for r in ev if (r.get("pix") or {}).get("status") == "OK"
            and r["pixel_same_sha"] != ((r["pix"]["frac_any"] or 0) == 0)]
    out["png_sha_vs_pixel_mismatch"] = {"n": len(mism), "samples": sample_dump(mism, 10)}
    # 교차표 + φ
    for c in ("C1_BYTES", "C3_STRUCT_HASH", "C4_VIS_ATTRS", "C5_OVERLAY_SUBTREE"):
        rows = [r for r in ev if r["dom_change"].get(c) is not None
                and (r.get("pix") or {}).get("status") == "OK"]
        x = [int((r["pix"]["frac_gt8"] or 0) > 0) for r in rows]
        yv = [int(r["dom_change"][c]) for r in rows]
        out.setdefault("crosstab_pixel_vs_dom", {})[c] = phi_and_perm(x, yv)
    return out


def _rule_share(k: int, n: int) -> str:
    """공유 판정규칙: Wilson 하한이 0.5 를 넘으면 SUPPORTED, 점추정만 넘으면 PARTIALLY."""
    if n == 0:
        return "NOT_TESTABLE"
    p, lo, hi = wilson(k, n)
    if lo > 0.5:
        return "SUPPORTED"
    if p > 0.5:
        return "PARTIALLY_SUPPORTED"
    if hi < 0.5:
        return "REFUTED"
    return "NOT_SUPPORTED"


def _rule_assoc(tests: list[dict]) -> tuple[str, dict]:
    ok = [t for t in tests if t.get("status") == "OK"]
    if not ok:
        return "NOT_TESTABLE", {}
    best = max(ok, key=lambda t: (t["phi"] or 0))
    if (best["phi"] or 0) > 0 and (best["p_perm"] or 1) < 0.05:
        return "SUPPORTED", best
    if (best["phi"] or 0) > 0:
        return "PARTIALLY_SUPPORTED", best
    return "NOT_SUPPORTED", best


def verdicts(A: dict, rq2: dict, sens: dict) -> tuple[str, dict, dict]:
    H1, H4, EFF, ev = A["H1"], A["H4"], A["EFF"], A["ev"]
    m1 = [r for r in H1 if r["probe_index_in_range"]]
    n1 = len(m1)
    absent = [r for r in m1 if not (r["target_visible"] or r["is_dialog_element"])]
    present = [r for r in m1 if (r["target_visible"] or r["is_dialog_element"])]
    no_ctrl = [r for r in m1 if r["n_dismiss_controls"] == 0 and not r["is_dialog_element"]]

    hv: dict = {}
    hv["H-13b1-ABSENT"] = {
        "statement": ("H1_NO_EFFECT 의 상당수는 dismiss control 이 애초에 없었거나 hittable 하지 "
                      "않았다 — 무효과가 아니라 무대상이다"),
        "decision_rule": ("m = H1 중 probe 매핑 가능한 step. '무대상' = engine 이 클릭할 수 있는 "
                          "대상이 없음(target_visible=0 이고 dialog 요소도 아님). "
                          "Wilson95 하한 > 0.5 면 SUPPORTED."),
        "k": len(absent), "n": n1, **{"share": wl(len(absent), n1)},
        "of_which_zero_controls_at_all": wl(len(no_ctrl), n1),
        "verdict": _rule_share(len(absent), n1),
    }
    hv["H-13b1-PRESENT_INEFFECTIVE"] = {
        "statement": "대상은 있었는데 눌러도 안 닫혔다 — 진짜 무효과",
        "decision_rule": "위의 여집합. Wilson95 하한 > 0.5 면 SUPPORTED.",
        "k": len(present), "n": n1, "share": wl(len(present), n1),
        "verdict": _rule_share(len(present), n1),
    }
    mixed = (n1 > 0 and len(absent) / n1 >= 0.2 and len(present) / n1 >= 0.2)
    hv["H-13b1-MIXED"] = {
        "statement": "둘이 섞여 있고 비율로만 말할 수 있다",
        "decision_rule": "두 부류 모두 점추정 20% 이상이면 SUPPORTED.",
        "share_absent": wl(len(absent), n1), "share_present": wl(len(present), n1),
        "verdict": "SUPPORTED" if mixed else ("NOT_SUPPORTED" if n1 else "NOT_TESTABLE"),
    }

    P = rq2["predictors_within_dom_same"]
    va, ba = _rule_assoc(P["H-13b2-ANIMATION"])
    vl, bl = _rule_assoc(P["H-13b2-LAZY_RENDER"])
    drift = rq2["pixel_change_magnitude"]["H4_vs_passive_drift_control"]
    paired = rq2["paired_action_vs_gap_within_H4"]
    drift_indistinguishable = (drift.get("status") == "OK" and (drift.get("p_perm") or 0) >= 0.05)
    hv["H-13b2-ANIMATION"] = {
        "statement": "스크린샷 시점이 전환 애니메이션 중이라 픽셀만 흔들렸다",
        "decision_rule": ("DOM 바이트 동일 step 부분모집단에서 애니메이션 지표(animated_elements / "
                          "infinite_animation / autoplay_media)와 픽셀변화의 φ>0 이고 "
                          "permutation p<0.05 면 SUPPORTED."),
        "tests": P["H-13b2-ANIMATION"], "best_test": ba, "verdict": va,
        "corroborating_passive_drift": {
            "H4_vs_no_action_gap": drift, "paired_within_H4": paired,
            "reading": ("무조작 구간에서도 같은 크기의 픽셀 변화가 나오면 H4 는 dismissal 의 결과가 "
                        "아니라 페이지 자체 변화다. 이 증거는 ANIMATION 과 LAZY_RENDER 를 함께 "
                        "지지하며 둘을 서로 가르지는 못한다."),
            "indistinguishable_from_passive_drift": drift_indistinguishable,
        },
    }
    hv["H-13b2-LAZY_RENDER"] = {
        "statement": "지연 렌더/광고 슬롯 교체가 dismissal 과 무관하게 픽셀을 바꿨다",
        "decision_rule": "위와 같은 형식. 예측자는 iframe_n>0 / img_n>=20 / script_n>=20.",
        "tests": P["H-13b2-LAZY_RENDER"], "best_test": bl, "verdict": vl,
        "change_localisation": rq2["change_localisation"]["H4_PIXEL_ONLY"],
    }
    di = rq2["dom_insensitivity_direct_check"]
    flips = sum(v for k, v in di["H4_steps_flagged_changed_by_criterion"].items())
    hv["H-13b2-DOM_INSENSITIVE"] = {
        "statement": "DOM 비교 기준이 둔감해서 실제 변화를 못 잡았다",
        "decision_rule": ("(i) C1_BYTES 보다 민감한 기준으로 H4 가 '변화' 로 뒤집히면 SUPPORTED. "
                          "(ii) 뒤집힘이 0 이면, page.content() 가 못 보는 내용(iframe/canvas/video)이 "
                          "H4 다수에 있을 때만 PARTIALLY_SUPPORTED."),
        "criterion_flips_within_H4": di["H4_steps_flagged_changed_by_criterion"],
        "n_flips_total": flips,
        "H4_with_iframe": di["H4_with_iframe"], "H4_with_canvas_or_video": di["H4_with_canvas_or_video"],
        "sha_roundtrip_failures": di["sha_roundtrip_failures"],
        "verdict": ("SUPPORTED" if flips > 0 else
                    "PARTIALLY_SUPPORTED" if (di["H4_with_iframe"]["p"] or 0) > 0.5 else
                    "NOT_SUPPORTED"),
        "note": ("C1_BYTES 는 직렬화된 DOM 에 대해 가장 민감한 기준이다. 이 기준이 둔감할 수 있는 "
                 "영역은 오직 직렬화가 도달하지 못하는 곳(iframe 내부 문서·shadow DOM·canvas·video)이다."),
    }
    real = [r for r in H4
            if r.get("engine_method") in ("CONTROL_CLICK", "DIALOG_CLOSE")
            and ((r.get("pix") or {}).get("overlay_overlap_frac") or 0) >= 0.5]
    hv["H-13b2-REAL_PIXEL_ONLY"] = {
        "statement": "CSS visibility/opacity 만 바뀌어 DOM 구조는 동일한 진짜 케이스",
        "decision_rule": ("실제로 클릭 가능한 대상을 눌렀고(CONTROL_CLICK/DIALOG_CLOSE) 픽셀 변화가 "
                          "overlay 박스 위에 집중(diff bbox 의 50% 이상)된 step 의 비율. "
                          "Wilson95 하한 > 0.5 면 SUPPORTED."),
        "k": len(real), "n": len(H4), "share": wl(len(real), len(H4)),
        "verdict": _rule_share(len(real), len(H4)),
        "structural_caveat": ("C1_BYTES 동일은 inline style·class 속성까지 한 글자도 안 바뀌었다는 "
                              "뜻이다. 따라서 '요소 속성으로 표현되는 CSS 토글'은 정의상 배제된다. "
                              "남는 경로는 스타일시트 주도(:hover/:focus/:target/keyframes)·"
                              "스크롤 위치·미디어 프레임뿐이다."),
        "tests": P["H-13b2-REAL_PIXEL_ONLY"],
    }

    top = ("RQ-D13b-1: " + hv["H-13b1-ABSENT"]["verdict"] +
           " for H-13b1-ABSENT / RQ-D13b-2: " + hv["H-13b2-ANIMATION"]["verdict"] +
           " for ANIMATION, " + hv["H-13b2-LAZY_RENDER"]["verdict"] + " for LAZY_RENDER")
    # 최상위 verdict 는 계약 어휘를 쓴다.
    if hv["H-13b1-ABSENT"]["verdict"] in ("SUPPORTED",) and hv["H-13b1-MIXED"]["verdict"] == "SUPPORTED":
        v = "PARTIALLY_SUPPORTED"
    elif hv["H-13b1-ABSENT"]["verdict"] == "SUPPORTED":
        v = "SUPPORTED"
    elif hv["H-13b1-MIXED"]["verdict"] == "SUPPORTED":
        v = "PARTIALLY_SUPPORTED"
    else:
        v = "NOT_SUPPORTED"
    return v, hv, {"absent": absent, "present": present, "no_ctrl": no_ctrl, "real_pixel": real,
                   "verdict_prose": top}


def build_samples(A: dict, parts: dict) -> dict:
    H1, H4, EFF, ev = A["H1"], A["H4"], A["EFF"], A["ev"]
    dom_same = [r for r in ev if r["dom_change"].get("C1_BYTES") == 0]
    anim_yes = [r for r in H4 if r.get("n_animated_elements", 0) > 0]
    anim_no = [r for r in H4 if r.get("n_animated_elements", 0) == 0]
    iframe_yes = [r for r in H4 if (r.get("iframe_n") or 0) > 0]
    iframe_no = [r for r in H4 if (r.get("iframe_n") or 0) == 0]
    esc = [r for r in H4 if r.get("engine_method") == "ESCAPE_KEY"]
    clk = [r for r in H4 if r.get("engine_method") in ("CONTROL_CLICK", "DIALOG_CLOSE")]
    big_drift = [r for r in H4
                 if ((r.get("pix_control_gap") or {}).get("frac_gt8") or 0) > 0]
    off_overlay = [r for r in H4 if ((r.get("pix") or {}).get("overlay_overlap_frac") or 0) < 0.5]
    return {
        "H-13b1-ABSENT": {
            "supporting": sample_dump(parts["absent"], 15),
            "refuting": sample_dump(parts["present"], 15),
            "supporting_n": len(parts["absent"]), "refuting_n": len(parts["present"]),
            "how_to_verify": ("supporting 행의 run_dir/observation_id/step 으로 "
                              "evidence/<run_dir>/<observation_id>/l0a/probe.json 을 열어 "
                              "raw_features.dismiss_control_candidates 에서 overlay_selector 와 같은 "
                              "container_selector 를 찾으면 dismiss_control_candidates 가 비어 있다."),
        },
        "H-13b1-PRESENT_INEFFECTIVE": {
            "supporting": sample_dump(parts["present"], 15),
            "refuting": sample_dump(parts["absent"], 15),
            "supporting_n": len(parts["present"]), "refuting_n": len(parts["absent"]),
        },
        "H-13b1-MIXED": {
            "supporting": sample_dump(parts["absent"][:8] + parts["present"][:8], 16),
            "refuting": [], "note": "두 부류가 모두 비어있지 않다는 것 자체가 증거다.",
        },
        "H-13b2-ANIMATION": {
            "supporting": sample_dump(anim_yes, 15), "refuting": sample_dump(anim_no, 15),
            "supporting_n": len(anim_yes), "refuting_n": len(anim_no),
            "passive_drift_positive_examples": sample_dump(big_drift, 12),
        },
        "H-13b2-LAZY_RENDER": {
            "supporting": sample_dump(iframe_yes + off_overlay, 15),
            "refuting": sample_dump(iframe_no, 15),
            "supporting_n": len(iframe_yes), "refuting_n": len(iframe_no),
            "off_overlay_n": len(off_overlay),
        },
        "H-13b2-DOM_INSENSITIVE": {
            "supporting": sample_dump([r for r in H4 if (r.get("iframe_n") or 0) > 0
                                       or (r.get("canvas_n") or 0) > 0], 15),
            "refuting": sample_dump([r for r in H4 if (r.get("iframe_n") or 0) == 0
                                     and (r.get("canvas_n") or 0) == 0
                                     and (r.get("video_n") or 0) == 0], 15),
        },
        "H-13b2-REAL_PIXEL_ONLY": {
            "supporting": sample_dump(parts["real_pixel"], 15),
            "refuting": sample_dump(esc, 15),
            "supporting_n": len(parts["real_pixel"]), "refuting_n": len(esc),
        },
        "H1_all_steps": sample_dump(H1, 60),
        "H4_all_steps": sample_dump(H4, 40),
    }


# ── 입력 목록 + sha256 ────────────────────────────────────────────────────────
def build_inputs() -> dict:
    import subprocess
    inputs = {"evidence_manifests": [], "derived": [], "code_read_at_sha": []}
    for worker, root in EVIDENCE_ROOTS.items():
        for d in sorted(p for p in root.iterdir() if p.is_dir()):
            man = d / "manifest.jsonl"
            if man.exists():
                inputs["evidence_manifests"].append({
                    "path": str(man), "sha256": hashlib.sha256(man.read_bytes()).hexdigest(),
                    "bytes": man.stat().st_size})
    for p in (TABLE, PRIOR_JSON, MART, Path(__file__).resolve(),
              Path(__file__).resolve().parent / "html_decode.py"):
        if p.exists():
            inputs["derived"].append({"path": str(p),
                                      "sha256": hashlib.sha256(p.read_bytes()).hexdigest(),
                                      "bytes": p.stat().st_size})
    wt = Path("/home/sieg/projects-wsl/ProjectFinal/.agent_worktrees/claude_d_research")
    for rel in ("research/landing_accessibility/src/landing_accessibility/engine/l0_collector.py",
                "research/landing_accessibility/src/landing_accessibility/engine/l0_probe.js"):
        try:
            blob = subprocess.run(["git", "rev-parse", f"{CODE_SHA}:{rel}"], cwd=wt,
                                  capture_output=True, text=True).stdout.strip()
            body = subprocess.run(["git", "show", f"{CODE_SHA}:{rel}"], cwd=wt,
                                  capture_output=True).stdout
            inputs["code_read_at_sha"].append({
                "path": rel, "commit": CODE_SHA, "blob_sha1": blob,
                "content_sha256": hashlib.sha256(body).hexdigest(), "bytes": len(body)})
        except Exception as e:
            inputs["code_read_at_sha"].append({"path": rel, "error": str(e)})
    inputs["n_evidence_manifests"] = len(inputs["evidence_manifests"])
    inputs["note"] = ("대형 raw evidence(png/html/json 수천 건)는 개별 해시 대신 각 run_dir 의 "
                      "manifest.jsonl 해시로 대신한다. manifest 안에 모든 산출물의 sha256 이 들어 있다.")
    return inputs


def make_figures(A: dict, rq2: dict, hv: dict) -> list[str]:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    FIGURES.mkdir(parents=True, exist_ok=True)
    out = []

    # 1) RQ-D13b-1 funnel
    f = hv["H-13b1-ABSENT"]
    n = f["n"]
    m = [r for r in A["H1"] if r["probe_index_in_range"]]
    stages = [("mapped\nH1 steps", n),
              ("control\nexists", sum(r["target_exists"] for r in m)),
              ("control\nhittable", sum(r["target_hittable"] for r in m)),
              ("control\nvisible+hittable\n(engine)", sum(r["target_visible"] for r in m))]
    fig, ax = plt.subplots(figsize=(7, 4.2))
    ax.bar([s[0] for s in stages], [s[1] for s in stages], color="#3b6ea5")
    for i, (lab, v) in enumerate(stages):
        p, lo, hi = wilson(v, n)
        ax.text(i, v + 0.8, f"{v}\n{p:.0%}\n[{lo:.0%},{hi:.0%}]", ha="center", fontsize=8)
    ax.set_ylabel("steps")
    ax.set_title(f"RQ-D13b-1  dismiss target presence funnel within H1_NO_EFFECT (n={n})")
    ax.set_ylim(0, n * 1.35)
    fig.tight_layout()
    p1 = FIGURES / "RQ_D13b12_rq1_funnel.png"
    fig.savefig(p1, dpi=140); plt.close(fig); out.append(str(p1))

    # 2) pixel change distributions
    px = lambda r: ((r.get("pix") or {}).get("frac_gt8")
                    if (r.get("pix") or {}).get("status") == "OK" else None)
    cg = lambda r: ((r.get("pix_control_gap") or {}).get("frac_gt8")
                    if (r.get("pix_control_gap") or {}).get("status") == "OK" else None)
    series = [("H4_PIXEL_ONLY\n(action)", [px(r) for r in A["H4"] if px(r) is not None]),
              ("EFFECTIVE\n(action)", [px(r) for r in A["EFF"] if px(r) is not None]),
              ("no-action gap\n(control)", [cg(r) for r in A["ev"] if cg(r) is not None])]
    fig, ax = plt.subplots(figsize=(7, 4.2))
    ax.boxplot([np.log10(np.array(v) + 1e-6) for _, v in series],
               tick_labels=[f"{k}\nn={len(v)}" for k, v in series], showfliers=True)
    ax.set_ylabel("log10(fraction of pixels changed >8/255)")
    ax.set_title("RQ-D13b-2  pixel change: action steps vs no-action control gap")
    fig.tight_layout()
    p2 = FIGURES / "RQ_D13b12_pixel_vs_control.png"
    fig.savefig(p2, dpi=140); plt.close(fig); out.append(str(p2))

    # 3) sensitivity across DOM criteria
    sens = rq2["_sens"]["classification_by_criterion"]
    labels = list(sens.keys())
    classes = ["H1_NO_EFFECT", "H2_DOM_ONLY", "H4_PIXEL_ONLY", "EFFECTIVE"]
    fig, ax = plt.subplots(figsize=(8, 4.2))
    bottom = np.zeros(len(labels))
    for c in classes:
        vals = np.array([sens[l].get(c, 0) for l in labels], dtype=float)
        ax.bar(labels, vals, bottom=bottom, label=c)
        bottom += vals
    ax.legend(fontsize=8); ax.set_ylabel("steps")
    ax.set_title("Sensitivity: classification under 5 DOM-change criteria")
    plt.xticks(rotation=15, fontsize=8)
    fig.tight_layout()
    p3 = FIGURES / "RQ_D13b12_dom_criteria_sensitivity.png"
    fig.savefig(p3, dpi=140); plt.close(fig); out.append(str(p3))
    return out


def main() -> int:
    steps, denom = collect()
    A = analyse(steps, denom)
    rq2 = analyse_rq2(A)
    sens = sensitivity(A)
    rq2["_sens"] = sens
    verdict, hv, parts = verdicts(A, rq2, sens)
    samples = build_samples(A, parts)
    figs = make_figures(A, rq2, hv)
    rq2.pop("_sens", None)

    H1, H4, EFF, ev = A["H1"], A["H4"], A["EFF"], A["ev"]
    m1 = [r for r in H1 if r["probe_index_in_range"]]

    out = {
        "rq": "RQ-D13b-1 + RQ-D13b-2",
        "title": ("H1_NO_EFFECT 는 무효과인가 무대상인가 · H4_PIXEL_ONLY 의 픽셀 변화는 무엇이 만들었나"),
        "plane": "D", "claim_kind": "ANALYSIS", "authority_status": "NON_CANONICAL",
        "verdict": verdict,
        "verdict_prose": parts["verdict_prose"],
        "original_definitions_verbatim": ORIGINAL_DEFINITIONS,
        "dom_criteria_definitions": DOM_CRITERIA_DEFS,
        "replication_of_prior_rq": A["replication"],
        "denominator_chain": A["chain"],
        "rq_d13b_1": A["rq1"],
        "rq_d13b_2": rq2,
        "sensitivity": sens,
        "hypothesis_verdicts": hv,
        "samples_for_human_verification": samples,
        "firewall": {
            "denied_paths_not_opened": True,
            "note": ("D_INPUT_ALLOWLIST.json 의 denied 목록을 하나도 열지 않았다. "
                     "입력은 allowlist 의 RAW_EVIDENCE_E001 · FROZEN_MART_E001 · "
                     "CODE_AT_EXACT_SHA · D_OWN_SCOPE 뿐이다."),
            "labels_produced": False, "production_modified": False, "network_access": False,
        },
        "upstream_defect_exclusion": {
            "claim": ("H1 의 다수가 무대상이라는 관측은 상위계층(수집기) 결함처럼 보일 수 있다. "
                      "보고 전에 내 파싱 오류 가능성을 먼저 배제했다."),
            "checks": [
                {"check": "step index ↔ probe 후보 index 대응",
                 "method": "l0c/{k} 의 k 집합과 modal_overlay_candidates 중 visible=true 인 index 집합 비교",
                 "result": "전 60 관측에서 불일치 0, index out-of-range 0, container 조인 실패 0"},
                {"check": "manifest sha256 왕복",
                 "method": "manifest 의 dom_after sha256 과 파일에서 직접 계산한 sha256 비교",
                 "result_field": "rq_d13b_2.dom_insensitivity_direct_check.sha_roundtrip_failures"},
                {"check": "engine 산출과의 역산 대조",
                 "method": "frozen mart 의 dismiss_control_exists/visible 와 probe 재계산값 조인 비교",
                 "result_field": "rq_d13b_1.mart_cross_validation"},
                {"check": "선행 RQ 수치 재현",
                 "method": "선행 판정식 재구현 후 분류 카운트 비교",
                 "result_field": "replication_of_prior_rq.exact_match"},
            ],
        },
        "limitation": [
            "L1 probe 시점 불일치 — dismiss control 의 존재/가시성/hittable 은 l0a(조작 전) 시점 "
            "probe 로만 잴 수 있다. step k 가 실행될 때의 실시간 상태가 아니다. "
            "다만 engine 자신이 바로 그 l0a probe 로 클릭 대상을 골랐으므로, "
            "'engine 이 누를 대상을 가지고 있었는가' 라는 질문에는 정확히 맞는 측정이다.",
            "L2 before-DOM 대용 — l0c 에 dom_before 슬롯이 없다. step k 의 before DOM 을 "
            "step k-1 의 dom_after.html(첫 step 은 l0a/dom.html)로 대용했다. 첫 step 은 "
            "l0a 캡처와 사이에 ax/css/screenshot/probe 가 끼어 시간 간격이 크다.",
            "L3 정적 DOM 에서는 layout 을 계산할 수 없다 — overlay/control 의 존재는 selector "
            "질의로 재확인했지만 visible/hittable 은 재확인하지 못했다.",
            "L4 selector 재질의의 모호성 — probe 의 selector 는 최대 8단계 상대경로라 "
            "문서 내 여러 곳에 매칭될 수 있다(match_n 을 병기했다).",
            "L5 iframe 내부 문서·shadow DOM·canvas·video 프레임은 page.content() 에 담기지 않는다. "
            "이 영역의 변화는 어떤 DOM 기준으로도 볼 수 없다.",
            "L6 dismissal 시도의 예외(클릭 timeout 등)는 정적으로 알 수 없다. engine_method 는 "
            "'의도된 경로' 이며 실제 실행 결과가 아니다.",
            "L7 n=60 관측 · 50 target 규모다. 비율의 정밀도가 낮고 target 단위 결론은 특히 약하다.",
        ],
        "heaviest_limitation": "L1",
        "not_answered_by_this_rq": (
            "이 RQ 는 dismissal 이 **접근성 관점에서 성공이어야 했는가** 를 답하지 않는다 — "
            "무대상이 결함인지 정상인지는 construct 판단이며 A 의 권한이다."),
        "further_research_questions": [
            "RQ-D13b-1a: 무대상 step 의 overlay 들은 어떤 종류인가(header/sticky/광고). "
            "modal_overlay_candidates 의 candidate_sources 별로 무대상 비율이 다른가.",
            "RQ-D13b-1b: dismiss control 탐지 어휘(CLOSE_WORDS/CLOSE_GLYPH, icon_only)가 "
            "무대상을 만들고 있는가 — 어휘를 넓히면 대상이 생기는 overlay 가 몇 건인가.",
            "RQ-D13b-2a: 무조작 구간의 픽셀 변화를 관측 단위 노이즈 기준선으로 삼아 "
            "step 별 픽셀 변화의 신호대잡음비를 정의할 수 있는가.",
            "RQ-D13b-2c: l0c 에 dom_before 슬롯을 추가하면 H2_DOM_ONLY 29건 중 몇 건이 "
            "대용가정의 산물인지 직접 가를 수 있는가(수집 재실행 필요, D 권한 밖).",
        ],
        "inputs": build_inputs(),
        "code_read": [
            {"path": "research/landing_accessibility/src/landing_accessibility/engine/l0_collector.py",
             "commit": CODE_SHA,
             "what": "_build_interrupts / _dismiss_pass / collect 순서 · _DISMISS_STATE_JS"},
            {"path": "research/landing_accessibility/src/landing_accessibility/engine/l0_probe.js",
             "commit": CODE_SHA,
             "what": "sel() 문법 · hittable() · dismiss_control_candidates 생성 규칙(CLOSE_WORDS/icon_only)"},
            {"path": "research_d/tools/rq_d13b_dismissal_effect.py", "commit": "working tree",
             "what": "선행 RQ-D13b 의 H1~H4 판정식 원문"},
            {"path": "research_d/tools/html_decode.py", "commit": "working tree",
             "what": "D-DEF-01 시정 경로 — 선언 charset 준수 디코드"},
        ],
        "figures": figs,
        "steps": [_f({k: v for k, v in r.items() if k != "_tree"}) for r in steps],
    }
    res_path = RESULTS / "RQ_D13b12_dismissal_dom_effect.json"
    res_path.write_text(json.dumps(_f(out), ensure_ascii=False, indent=1) + "\n", encoding="utf-8")

    # ── 콘솔 요약 ──
    print(f"steps={len(steps)} evaluable={len(ev)} cls={A['cls']}")
    print(f"replication exact_match={A['replication']['exact_match']}")
    print(f"H1 mappable n={len(m1)}  exists={sum(r['target_exists'] for r in m1)} "
          f"hittable={sum(r['target_hittable'] for r in m1)} visible={sum(r['target_visible'] for r in m1)}")
    for k, v in hv.items():
        print(f"  {k:<28} {v['verdict']}")
    print(f"verdict={verdict}")

    # ── MLflow ──
    try:
        from mlflow_contract import research_run, finish, log_pointer
        import mlflow
        parent = RESULTS / "D14_PARENT_RUN.json"
        parent_id = "NONE"
        if parent.exists():
            try:
                parent_id = json.loads(parent.read_text()).get("run_id", "NONE") or "NONE"
            except Exception:
                pass
        drift = rq2["pixel_change_magnitude"]["H4_vs_passive_drift_control"]
        c1 = sens["crosstab_pixel_vs_dom"]["C1_BYTES"]
        anim = hv["H-13b2-ANIMATION"].get("best_test") or {}
        lazy = hv["H-13b2-LAZY_RENDER"].get("best_test") or {}
        with research_run(
            experiment="LA_10_RESEARCH_D",
            run_name="RQ-D13b-1_2_dismissal_dom_effect",
            plane="D", hypothesis_id="H-13b1-ABSENT",
            competing_hypothesis=("H-13b1-PRESENT_INEFFECTIVE, H-13b1-MIXED, H-13b2-ANIMATION, "
                                  "H-13b2-LAZY_RENDER, H-13b2-DOM_INSENSITIVE, H-13b2-REAL_PIXEL_ONLY"),
            claim_kind="ANALYSIS", nested=True, parent_run_id=parent_id,
            subagent_id="D-SUB-RQ-D13b12",
            objective=("H1_NO_EFFECT 로 분류된 dismissal step 에 애초에 대상이 있었는지, "
                       "그리고 H4_PIXEL_ONLY 의 픽셀 변화가 무엇에서 왔는지 가른다"),
            method=("probe 의 dismiss_control_candidates 를 engine 판정식으로 재계산해 "
                    "존재/가시/hittable 3단계 funnel + Wilson95; DOM 변화 기준 5종 민감도; "
                    "무조작 구간(screen_after[k-1]↔screen_before[k])을 대조군으로 한 픽셀 변화 비교; "
                    "φ + permutation test"),
            dataset_grain="l0c dismissal step (observation × interrupt_index)",
            n_expected=249, n_observed=len(steps),
            code_path=Path(__file__).resolve(),
            limitation=out["limitation"][0],
            notebook=("research/landing_accessibility/notebooks/d_research/"
                      "RQ_D13b12_dismissal_dom_effect.ipynb"),
            result_path=res_path,
            extra_params={"pixel_delta_threshold": PIXEL_DELTA, "perm_iters": 20000,
                          "code_sha_read": CODE_SHA},
            seed=RNG_SEED,
        ):
            M = {
                "n_steps_total": len(steps),
                "n_steps_evaluable": len(ev),
                "n_H1_NO_EFFECT": len(H1), "n_H2_DOM_ONLY": len(A["H2"]),
                "n_H4_PIXEL_ONLY": len(H4), "n_EFFECTIVE": len(EFF),
                "n_H1_probe_mappable": len(m1),
                "H1_share_no_actionable_target": hv["H-13b1-ABSENT"]["share"]["p"] or 0.0,
                "H1_share_no_actionable_lo95": hv["H-13b1-ABSENT"]["share"]["wilson95"][0] or 0.0,
                "H1_share_zero_controls": hv["H-13b1-ABSENT"]["of_which_zero_controls_at_all"]["p"] or 0.0,
                "H1_share_control_exists": A["rq1"]["funnel_H1_NO_EFFECT"]["a_exists"]["p"] or 0.0,
                "H1_share_control_hittable": A["rq1"]["funnel_H1_NO_EFFECT"]["c_hittable"]["p"] or 0.0,
                "EFF_share_control_visible": A["rq1"]["funnel_EFFECTIVE"]["b_visible"]["p"] or 0.0,
                "H4_median_pixel_frac_gt8": rq2["pixel_change_magnitude"]["H4_PIXEL_ONLY"]["median"] or 0.0,
                "control_gap_median_frac_gt8": rq2["passive_drift_control"]["frac_gt8_median"] or 0.0,
                "control_gap_share_any_change": rq2["passive_drift_control"]["share_with_any_change"]["p"] or 0.0,
                "H4_vs_drift_p_perm": drift.get("p_perm") if drift.get("status") == "OK" else -1.0,
                "phi_pixel_vs_domC1": c1.get("phi") if c1.get("status") == "OK" else 0.0,
                "p_perm_pixel_vs_domC1": c1.get("p_perm") if c1.get("status") == "OK" else -1.0,
                "anim_best_phi": anim.get("phi") or 0.0,
                "anim_best_p_perm": anim.get("p_perm") if anim.get("p_perm") is not None else -1.0,
                "lazy_best_phi": lazy.get("phi") or 0.0,
                "H4_share_iframe": hv["H-13b2-DOM_INSENSITIVE"]["H4_with_iframe"]["p"] or 0.0,
                "H4_share_change_on_overlay": (rq2["change_localisation"]["H4_PIXEL_ONLY"]
                                               ["share_mostly_on_overlay_ge_0.5"]["p"] or 0.0),
                "n_mart_disagree_exists": A["rq1"]["mart_cross_validation"]["counts"].get("disagree_exists", 0),
                "sha_roundtrip_failures": rq2["dom_insensitivity_direct_check"]["sha_roundtrip_failures"],
                "replication_exact_match": int(bool(A["replication"]["exact_match"])),
                "n_dom_criteria_tested": 5,
            }
            mlflow.log_metrics({k: float(v) for k, v in M.items()})
            for k, v in hv.items():
                mlflow.set_tag(f"verdict_{k}", v["verdict"])
            mlflow.log_artifact(str(res_path))
            for f in figs:
                mlflow.log_artifact(f)
            log_pointer("e001_evidence_manifests", str(EVIDENCE_ROOTS["w01"].parent),
                        hashlib.sha256(json.dumps(out["inputs"]["evidence_manifests"],
                                                  sort_keys=True).encode()).hexdigest())
            finish(verdict=verdict, limitation=out["limitation"][0])
            rid = mlflow.active_run().info.run_id
        print(f"MLFLOW_RUN_ID={rid}")
        (RESULTS / "RQ_D13b12_MLFLOW_RUN.json").write_text(
            json.dumps({"run_id": rid, "experiment": "LA_10_RESEARCH_D",
                        "run_name": "RQ-D13b-1_2_dismissal_dom_effect"}, indent=1) + "\n",
            encoding="utf-8")
    except Exception as e:
        print(f"MLFLOW_FAILED: {type(e).__name__}: {e}")
        raise
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
