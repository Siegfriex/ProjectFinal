"""RQ-D10 — evidence slot 간 시점 불일치의 정량화와 관측단위 지표 설계.

B `T-B-RQ-D-001 Q3`. A `F-A3.1`(라벨러 불일치의 원인 = slot 시점 불일치)은
**hypothesis로만** 취급한다. D는 label을 열지 않으므로 그 인과는 검증 대상이 아니다.
D가 답하는 것은 오직: (1) slot 간 불일치가 raw artifact에서 실재하는가,
(2) 그것을 관측단위 지표로 정의할 수 있는가, (3) 그 지표는 재현되는가.

read-only. evidence/production 경로를 수정하지 않는다.
Restart -> Run All 가능.

산출:
  results/RQ_D10_slot_mismatch.json
  figures/RQ_D10_*.png (matplotlib 있을 때만)
"""
from __future__ import annotations

import json
import math
import re
import unicodedata
from difflib import SequenceMatcher
from pathlib import Path
from urllib.parse import urlsplit

from lxml import html as lxml_html

REPO = Path("/home/sieg/projects-wsl/ProjectFinal")
HERE = Path(__file__).resolve().parents[1]
OBS_JSON = HERE / "results" / "D_OBSERVATION_TABLE.json"
OUT_JSON = HERE / "results" / "RQ_D10_slot_mismatch.json"
FIG_DIR = HERE / "figures"

EVIDENCE_ROOTS = {
    f"w{n}": REPO / f".agent_worktrees/claude_b_e001_worker_{n}/artifacts/e001_w{n}/evidence"
    for n in ("01", "02", "03", "04")
}

# ── slot 수집 순서: l0_collector.py L410-440 @876c67d (claude_b_e001_runner) ──
# goto(wait_until="load") -> wait 400ms -> [dom] -> [ax] -> [computed_css]
#   -> screen_initial -> screen_fullpage(전체 스크롤 발생) -> scrollTo(0,0)
#   -> wait 400ms -> [probe]
# 즉 dom/ax 는 probe 보다 **구조적으로 앞선다**. 그 사이에 full-page 캡처를 위한
# 문서 전체 스크롤이 끼어 있어 lazy-load / IntersectionObserver 컨텐츠가
# probe 시점에만 존재할 수 있다. 이것은 관측이 아니라 코드에서 읽은 사실이다.
SLOT_ORDER = ["dom", "ax", "computed_css", "screen_initial", "screen_fullpage", "probe"]
SLOT_FILE = {
    "dom": "dom.html", "ax": "ax.json", "computed_css": "computed_css.json",
    "screen_initial": "screen_initial.png", "screen_fullpage": "screen_fullpage.png",
    "probe": "probe.json",
}

# l0_probe.js L169 accessible_name_sources 셀렉터. **visible 필터 없음**, cap 300.
# dom.html 을 같은 셀렉터로 파싱하면 두 시점의 *동일 질의* 비교가 된다.
ANS_XPATH = ("//a[@href] | //button | //input[not(@type='hidden')] | //select | //textarea | "
             "//img | //*[@role='button'] | //*[@role='link'] | //*[@role='img'] | "
             "//*[@role='checkbox'] | //*[@role='radio'] | //*[@role='tab']")
ANS_CAP = 300

AX_INTERACTIVE_ROLES = {
    "link", "button", "textbox", "combobox", "checkbox", "radio", "tab", "option",
    "menuitem", "menuitemcheckbox", "menuitemradio", "searchbox", "switch", "slider",
    "spinbutton", "listbox", "SpinButton",
}


# ────────────────────────────── helpers ──────────────────────────────
def norm_title(s: str | None) -> str:
    if not s:
        return ""
    s = unicodedata.normalize("NFKC", s)
    s = re.sub(r"\s+", " ", s).strip().casefold()
    return s


def title_sim(a: str, b: str) -> float:
    """0=동일, 1=완전 상이. 정규화 후 문자 수준 유사도의 여집합."""
    if a == b:
        return 0.0
    if not a or not b:
        return 1.0
    return 1.0 - SequenceMatcher(None, a, b).ratio()


def url_drift_level(a: str | None, b: str | None) -> int:
    """0 동일 / 1 fragment·query만 / 2 path 변경 / 3 host 변경 / -1 판정불가."""
    if not a or not b:
        return -1
    pa, pb = urlsplit(a), urlsplit(b)
    ha, hb = pa.netloc.lower().rstrip("."), pb.netloc.lower().rstrip(".")
    if ha != hb:
        return 3
    na = pa.path.rstrip("/") or "/"
    nb = pb.path.rstrip("/") or "/"
    if na != nb:
        return 2
    if (pa.query, pa.fragment) != (pb.query, pb.fragment):
        return 1
    return 0


def log2_ratio(num: int | None, den: int | None) -> float | None:
    if num is None or den is None:
        return None
    return math.log2((num + 1) / (den + 1))


def q(xs: list[float], p: float) -> float | None:
    if not xs:
        return None
    ys = sorted(xs)
    if len(ys) == 1:
        return ys[0]
    i = p * (len(ys) - 1)
    lo, hi = int(math.floor(i)), int(math.ceil(i))
    return ys[lo] + (ys[hi] - ys[lo]) * (i - lo)


def describe(xs: list[float]) -> dict:
    xs = [x for x in xs if x is not None]
    if not xs:
        return {"n": 0}
    m = sum(xs) / len(xs)
    var = sum((x - m) ** 2 for x in xs) / (len(xs) - 1) if len(xs) > 1 else 0.0
    return {"n": len(xs), "mean": round(m, 4), "sd": round(math.sqrt(var), 4),
            "min": round(min(xs), 4), "p25": round(q(xs, .25), 4), "median": round(q(xs, .5), 4),
            "p75": round(q(xs, .75), 4), "p90": round(q(xs, .90), 4), "max": round(max(xs), 4)}


# ────────────────────────────── slot 추출 ──────────────────────────────
def dom_slot(path: Path) -> dict:
    """dom.html 재파싱. 공용 테이블의 dom_title 은 lxml 이 raw bytes 의 meta charset 을
    믿어 mojibake 가 섞였다 — 수집기는 page.content() 를 **UTF-8로** 기록하므로
    여기서는 UTF-8 강제 디코드 후 파싱한다. 이 교정 자체가 결과 항목이다."""
    raw = path.read_bytes()
    out: dict = {"dom_bytes": len(raw)}
    try:
        tree = lxml_html.document_fromstring(raw.decode("utf-8", "replace"))
    except Exception:
        out["dom_parse_ok"] = 0
        return out
    out["dom_parse_ok"] = 1
    t = tree.find(".//title")
    out["dom_title_utf8"] = (t.text or "").strip() if t is not None and t.text else ""
    # 참고용: 공용 테이블과 같은 방식(바이트 파싱)으로도 뽑아 mojibake 여부를 대조
    try:
        t2 = lxml_html.fromstring(raw).find(".//title")
        out["dom_title_bytesparse"] = (t2.text or "").strip() if t2 is not None and t2.text else ""
    except Exception:
        out["dom_title_bytesparse"] = None
    body = tree.find("body")
    out["dom_body_element_n"] = len(body.xpath(".//*")) if body is not None else 0
    out["dom_element_n"] = len(tree.xpath("//*"))
    out["dom_script_n"] = len(tree.xpath("//script"))
    txt = " ".join((body.text_content() if body is not None else "").split())
    out["dom_body_text_len"] = len(txt)
    out["dom_ans_n"] = len(set(tree.xpath(ANS_XPATH)))  # probe ANS 와 동일 셀렉터
    out["dom_noscript_n"] = len(tree.xpath("//noscript"))
    return out


def ax_slot(path: Path) -> dict:
    nodes = json.loads(path.read_text())
    roles: dict[str, int] = {}
    focusable = 0
    root_name = root_url = None
    ignored = 0
    for n in nodes:
        r = n.get("role")
        roles[r] = roles.get(r, 0) + 1
        if n.get("ignored"):
            ignored += 1
        props = {p["name"]: p.get("value") for p in n.get("properties", [])}
        if props.get("focusable") is True:
            focusable += 1
        if r == "RootWebArea" and root_name is None:
            root_name = n.get("name")
            root_url = props.get("url")
    return {
        "ax_node_n": len(nodes),
        "ax_ignored_n": ignored,
        "ax_role_kind_n": len(roles),
        "ax_focusable_n": focusable,
        "ax_interactive_n": sum(v for k, v in roles.items() if k in AX_INTERACTIVE_ROLES),
        "ax_statictext_n": roles.get("StaticText", 0),
        "ax_link_n": roles.get("link", 0),
        "ax_button_n": roles.get("button", 0),
        "ax_image_n": roles.get("image", 0),
        "ax_root_title": root_name,
        "ax_root_url": root_url,
        "ax_roles": roles,
    }


def probe_slot(path: Path) -> dict:
    p = json.loads(path.read_text())
    rf = p.get("raw_features", {})
    vp = rf.get("viewport", {})
    ans = rf.get("accessible_name_sources", [])
    return {
        "probe_collected_at": p.get("collected_at"),
        "probe_url": p.get("url"),
        "probe_final_url": vp.get("final_url"),
        "probe_title": vp.get("title"),
        "probe_scroll_height": vp.get("document_scroll_height"),
        "probe_layout_height": vp.get("layout_height"),
        "probe_ans_n": len(ans),
        "probe_ans_capped": int(len(ans) >= ANS_CAP),
        "probe_target_size_n": len(rf.get("target_size", [])),
        "probe_pac_n": len(rf.get("primary_action_candidates", [])),
        "probe_contrast_n": len(rf.get("contrast", [])),
        "probe_body_text_len": len(rf.get("gate_signals", {}).get("visible_text") or ""),
    }


# ────────────────────────────── 수집 ──────────────────────────────
def collect() -> list[dict]:
    base = json.loads(OBS_JSON.read_text())["rows"]
    recs: list[dict] = []
    for r in base:
        if not r.get("observation_id"):
            continue  # 관측 디렉터리 없음(총실패 run) — slot 비교 자체가 불가
        l0a = (EVIDENCE_ROOTS[r["worker"]] / r["run_dir"] / r["observation_id"] / "l0a")
        rec = {k: r.get(k) for k in ("worker", "wtg", "run_dir", "run_ts", "observation_id",
                                     "in_mart", "prior_archetype", "prior_service", "prior_url")}
        # slot 별 파일 mtime (ms) — run.json 은 run 단위 시각만 갖고, probe 만
        # collected_at 을 갖는다. slot 단위 시각은 파일시스템 mtime 이 유일한 원천.
        mt: dict[str, float | None] = {}
        for s in SLOT_ORDER:
            f = l0a / SLOT_FILE[s]
            mt[s] = round(f.stat().st_mtime, 3) if f.exists() else None
        rec["slot_mtime"] = mt
        rec["slot_present"] = {s: int(mt[s] is not None) for s in SLOT_ORDER}

        dom_f, ax_f, pr_f = l0a / "dom.html", l0a / "ax.json", l0a / "probe.json"
        rec.update(dom_slot(dom_f) if dom_f.exists() else {"dom_parse_ok": None})
        rec.update(ax_slot(ax_f) if ax_f.exists() else {"ax_node_n": None})
        rec.update(probe_slot(pr_f) if pr_f.exists() else {"probe_ans_n": None})
        rec["probe_present"] = int(pr_f.exists())
        recs.append(rec)
    return recs


# ────────────────────────────── 지표 ──────────────────────────────
def add_indicators(recs: list[dict], gap_thr: float) -> None:
    for r in recs:
        mt = r["slot_mtime"]
        r["slot_elapsed_dom_to_probe_s"] = (
            round(mt["probe"] - mt["dom"], 3) if mt["dom"] and mt["probe"] else None)
        r["slot_elapsed_dom_to_ax_s"] = (
            round(mt["ax"] - mt["dom"], 3) if mt["dom"] and mt["ax"] else None)
        r["slot_order_as_coded"] = int(all(
            mt[a] is not None and mt[b] is not None and mt[a] <= mt[b]
            for a, b in zip(SLOT_ORDER, SLOT_ORDER[1:])))

        # ── I1 slot_dom_empty_probe_rich (연속형: dom_body_fill) ──
        r["dom_body_fill"] = (
            None if not r.get("dom_element_n")
            else round(r["dom_body_element_n"] / r["dom_element_n"], 4))
        r["slot_dom_empty_probe_rich"] = int(
            r.get("dom_body_element_n") == 0
            and (r.get("probe_ans_n") or 0) > 0)

        if not r["probe_present"]:
            # probe slot 자체가 없으면 slot 간 비교가 정의되지 않는다.
            # 없는 slot 을 빈 값으로 취급하면 허위 불일치가 난다 (신한/롯데 사례).
            for k in ("slot_title_mismatch", "slot_title_mismatch_domprobe",
                      "slot_title_mismatch_bytesparse", "slot_url_drift",
                      "slot_url_drift_interslot", "slot_name_source_gap",
                      "slot_interactive_gap_flag", "slot_disagreement_score"):
                r[k] = None
            r["title_dissim"] = {"dom_ax": None, "dom_probe": None, "ax_probe": None}
            r["title_dissim_max"] = None
            r["url_drift_levels"] = {}
            r["slot_name_source_gap_censored"] = None
            r["slot_disagreement_components"] = []
            r["slot_disagreement_evaluable_n"] = 0
            continue

        # ── I2 slot_title_mismatch (3-slot) ──
        td, ta, tp = (norm_title(r.get("dom_title_utf8")), norm_title(r.get("ax_root_title")),
                      norm_title(r.get("probe_title")))
        pairs = {"dom_ax": (td, ta), "dom_probe": (td, tp), "ax_probe": (ta, tp)}
        sims = {k: (None if not (a or b) else round(title_sim(a, b), 4))
                for k, (a, b) in pairs.items()}
        r["title_dissim"] = sims
        have = [v for v in sims.values() if v is not None]
        r["title_dissim_max"] = round(max(have), 4) if have else None
        r["slot_title_mismatch"] = int(any(
            (a or b) and a != b for a, b in pairs.values()))
        r["slot_title_mismatch_domprobe"] = int(
            bool(td or tp) and td != tp)
        # 공용 테이블 방식(mojibake 포함)으로 셌을 때의 값 — 과대계상 크기 측정용
        r["slot_title_mismatch_bytesparse"] = int(
            bool(norm_title(r.get("dom_title_bytesparse")) or tp)
            and norm_title(r.get("dom_title_bytesparse")) != tp)

        # ── I3 slot_url_drift (ordinal) ──
        lv = {
            "requested_vs_probe_final": url_drift_level(r.get("prior_url"), r.get("probe_final_url")),
            "ax_vs_probe_final": url_drift_level(r.get("ax_root_url"), r.get("probe_final_url")),
            "probe_url_vs_final": url_drift_level(r.get("probe_url"), r.get("probe_final_url")),
        }
        r["url_drift_levels"] = lv
        pos = [v for v in lv.values() if v >= 0]
        r["slot_url_drift"] = max(pos) if pos else None
        # slot 간 드리프트만 (요청 URL 은 slot 이 아니다)
        r["slot_url_drift_interslot"] = (
            lv["ax_vs_probe_final"] if lv["ax_vs_probe_final"] >= 0 else None)

        # ── I4 slot_name_source_gap (연속형이 원형) ──
        capped = bool(r.get("probe_ans_capped"))
        r["slot_name_source_gap"] = (
            None if capped else log2_ratio(r.get("probe_ans_n"), r.get("dom_ans_n")))
        if r["slot_name_source_gap"] is not None:
            r["slot_name_source_gap"] = round(r["slot_name_source_gap"], 4)
        r["slot_name_source_gap_censored"] = int(capped)
        g = r["slot_name_source_gap"]
        r["slot_interactive_gap_flag"] = (None if g is None else int(abs(g) > gap_thr))

        # ── 합성 ──
        comps = [r["slot_dom_empty_probe_rich"], r["slot_title_mismatch"],
                 int(bool(r["slot_url_drift_interslot"])) if r["slot_url_drift_interslot"] is not None else None,
                 r["slot_interactive_gap_flag"]]
        r["slot_disagreement_components"] = comps
        known = [c for c in comps if c is not None]
        r["slot_disagreement_score"] = sum(known)
        r["slot_disagreement_evaluable_n"] = len(known)


# ────────────────────────────── 분석 ──────────────────────────────
DUP_KEY = "wtg"


def analyse(recs: list[dict], gap_thr: float) -> dict:
    N = len(recs)
    withp = [r for r in recs if r["probe_present"]]
    out: dict = {"N_observations_with_dir": N, "N_with_probe": len(withp),
                 "N_with_ax": sum(1 for r in recs if r.get("ax_node_n") is not None),
                 "N_with_dom": sum(1 for r in recs if r.get("dom_parse_ok") == 1),
                 "N_in_mart": sum(1 for r in recs if r["in_mart"] == 1)}

    # 1. 시점 실재성
    el = [r["slot_elapsed_dom_to_probe_s"] for r in recs if r["slot_elapsed_dom_to_probe_s"]]
    out["elapsed_dom_to_probe_s"] = describe(el)
    out["elapsed_dom_to_ax_s"] = describe(
        [r["slot_elapsed_dom_to_ax_s"] for r in recs if r["slot_elapsed_dom_to_ax_s"] is not None])
    out["slot_order_as_coded_n"] = sum(r["slot_order_as_coded"] for r in recs)
    # mtime 신뢰성 교차검증: probe mtime vs probe.collected_at
    dif = []
    for r in recs:
        ca, mt = r.get("probe_collected_at"), r["slot_mtime"]["probe"]
        if ca and mt:
            import datetime as _dt
            t = _dt.datetime.fromisoformat(ca.replace("Z", "+00:00")).timestamp()
            dif.append(round(mt - t, 3))
    out["probe_mtime_minus_collected_at_s"] = describe(dif)

    # 2. 불일치 증거별 건수
    ev: dict = {}
    ev["dom_empty_probe_rich"] = {
        "n": sum(r["slot_dom_empty_probe_rich"] for r in recs), "denom": N,
        "cases": [{"wtg": r["wtg"], "service": r["prior_service"], "dom_ans_n": r.get("dom_ans_n"),
                   "dom_body_element_n": r.get("dom_body_element_n"), "dom_script_n": r.get("dom_script_n"),
                   "probe_ans_n": r.get("probe_ans_n"), "probe_pac_n": r.get("probe_pac_n"),
                   "ax_node_n": r.get("ax_node_n"), "ax_interactive_n": r.get("ax_interactive_n"),
                   "probe_present": r["probe_present"]}
                  for r in recs if r.get("dom_body_element_n") == 0]}
    tm = [r for r in withp if r["slot_title_mismatch"]]
    ev["title_mismatch_any_pair"] = {
        "n": len(tm), "denom": len(withp),
        "n_naive_bytesparse": sum(r["slot_title_mismatch_bytesparse"] for r in withp),
        "cases": [{"wtg": r["wtg"], "service": r["prior_service"], "dom": r["dom_title_utf8"],
                   "ax": r["ax_root_title"], "probe": r["probe_title"],
                   "dissim": r["title_dissim"]} for r in tm]}
    ud = [r for r in withp if (r["slot_url_drift"] or 0) > 0]
    ev["url_drift_any_gt0"] = {
        "n": len(ud), "denom": len(withp),
        "by_level": {str(l): sum(1 for r in withp if r["slot_url_drift"] == l) for l in (0, 1, 2, 3)},
        "interslot_gt0_n": sum(1 for r in withp if (r["slot_url_drift_interslot"] or 0) > 0),
        "cases": [{"wtg": r["wtg"], "service": r["prior_service"], "requested": r["prior_url"],
                   "ax": r["ax_root_url"], "probe_final": r["probe_final_url"],
                   "levels": r["url_drift_levels"]} for r in ud]}
    gaps = [r["slot_name_source_gap"] for r in withp if r["slot_name_source_gap"] is not None]
    ev["name_source_gap_log2"] = {
        "n_evaluable": len(gaps), "denom": len(withp),
        "n_censored_by_cap300": sum(r["slot_name_source_gap_censored"] for r in withp),
        "dist": describe(gaps),
        "n_flag_at_thr": sum(1 for g in gaps if abs(g) > gap_thr),
        "threshold_log2": round(gap_thr, 4),
        "extremes": sorted(
            [{"wtg": r["wtg"], "service": r["prior_service"], "dom_ans_n": r["dom_ans_n"],
              "probe_ans_n": r["probe_ans_n"], "gap": r["slot_name_source_gap"]}
             for r in withp if r["slot_name_source_gap"] is not None],
            key=lambda d: -abs(d["gap"]))[:10]}
    out["evidence"] = ev

    # 3. AX 3자 비교
    tri = []
    for r in withp:
        if r.get("ax_node_n") is None or r.get("dom_ans_n") is None:
            continue
        tri.append({
            "wtg": r["wtg"], "dom_ans_n": r["dom_ans_n"], "ax_interactive_n": r["ax_interactive_n"],
            "probe_ans_n": r["probe_ans_n"],
            "log2_ax_over_dom": round(log2_ratio(r["ax_interactive_n"], r["dom_ans_n"]), 4),
            "log2_probe_over_ax": round(log2_ratio(r["probe_ans_n"], r["ax_interactive_n"]), 4),
            "log2_probe_over_dom": r["slot_name_source_gap"]})
    out["three_slot"] = {
        "n": len(tri),
        "log2_ax_over_dom": describe([t["log2_ax_over_dom"] for t in tri]),
        "log2_probe_over_ax": describe([t["log2_probe_over_ax"] for t in tri]),
        "log2_probe_over_dom": describe([t["log2_probe_over_dom"] for t in tri if t["log2_probe_over_dom"] is not None]),
        "title_dissim_dom_ax": describe([r["title_dissim"]["dom_ax"] for r in withp
                                         if r["title_dissim"]["dom_ax"] is not None]),
        "title_dissim_ax_probe": describe([r["title_dissim"]["ax_probe"] for r in withp
                                           if r["title_dissim"]["ax_probe"] is not None]),
        "n_ax_agrees_dom_disagrees_probe": sum(
            1 for r in withp
            if r["title_dissim"]["dom_ax"] == 0 and (r["title_dissim"]["ax_probe"] or 0) > 0),
        "n_ax_agrees_probe_disagrees_dom": sum(
            1 for r in withp
            if r["title_dissim"]["ax_probe"] == 0 and (r["title_dissim"]["dom_ax"] or 0) > 0),
    }

    # 4. 재현성 — 중복 재실행 쌍 (같은 target, 6~7s 간격)
    by = {}
    for r in recs:
        by.setdefault(r[DUP_KEY], []).append(r)
    pairs = [(k, v) for k, v in by.items() if len(v) == 2 and all(x["probe_present"] for x in v)]
    rt = []
    for k, v in pairs:
        a, b = sorted(v, key=lambda r: r["run_ts"])
        rt.append({
            "wtg": k, "service": a["prior_service"],
            "gap_between_runs_s": round((b["slot_mtime"]["dom"] or 0) - (a["slot_mtime"]["dom"] or 0), 1),
            "dom_ans_n": [a["dom_ans_n"], b["dom_ans_n"]],
            "ax_interactive_n": [a["ax_interactive_n"], b["ax_interactive_n"]],
            "probe_ans_n": [a["probe_ans_n"], b["probe_ans_n"]],
            "slot_name_source_gap": [a["slot_name_source_gap"], b["slot_name_source_gap"]],
            "abs_delta_gap": (None if None in (a["slot_name_source_gap"], b["slot_name_source_gap"])
                              else round(abs(a["slot_name_source_gap"] - b["slot_name_source_gap"]), 4)),
            "slot_title_mismatch": [a["slot_title_mismatch"], b["slot_title_mismatch"]],
            "slot_url_drift": [a["slot_url_drift"], b["slot_url_drift"]],
            "slot_dom_empty_probe_rich": [a["slot_dom_empty_probe_rich"], b["slot_dom_empty_probe_rich"]],
            "slot_disagreement_score": [a["slot_disagreement_score"], b["slot_disagreement_score"]],
            "elapsed_dom_to_probe_s": [a["slot_elapsed_dom_to_probe_s"], b["slot_elapsed_dom_to_probe_s"]],
        })
    deltas = [p["abs_delta_gap"] for p in rt if p["abs_delta_gap"] is not None]
    out["test_retest"] = {
        "n_pairs": len(rt), "pairs": rt,
        "abs_delta_name_source_gap": describe(deltas),
        "max_abs_delta": round(max(deltas), 4) if deltas else None,
        "n_pairs_flag_agree_title": sum(1 for p in rt if p["slot_title_mismatch"][0] == p["slot_title_mismatch"][1]),
        "n_pairs_flag_agree_url": sum(1 for p in rt if p["slot_url_drift"][0] == p["slot_url_drift"][1]),
        "n_pairs_score_agree": sum(1 for p in rt if p["slot_disagreement_score"][0] == p["slot_disagreement_score"][1]),
    }

    # 5. 민감도 — gap flag 임계값 격자
    grid = [0.10, 0.15, 0.20, 0.26, 0.32, 0.40, 0.50, 0.75, 1.00]
    out["sensitivity_gap_threshold"] = [
        {"thr_log2": t, "thr_ratio": round(2 ** t, 3),
         "n_flag": sum(1 for g in gaps if abs(g) > t), "denom": len(gaps),
         "n_flag_positive": sum(1 for g in gaps if g > t),
         "n_flag_negative": sum(1 for g in gaps if g < -t)} for t in grid]
    # dom_body_empty 대안 정의 민감도
    out["sensitivity_dom_empty_def"] = [
        {"rule": "dom_body_element_n == 0",
         "n": sum(1 for r in recs if r.get("dom_body_element_n") == 0)},
        {"rule": "dom_body_text_len < 50 (공용 테이블 정의)",
         "n": sum(1 for r in recs if (r.get("dom_body_text_len") or 0) < 50)},
        {"rule": "dom_ans_n == 0",
         "n": sum(1 for r in recs if r.get("dom_ans_n") == 0)},
        {"rule": "dom_ans_n == 0 AND probe_ans_n > 0",
         "n": sum(1 for r in recs if r.get("dom_ans_n") == 0 and (r.get("probe_ans_n") or 0) > 0)},
    ]

    # 6. 반례 — "dom_body_empty = SPA 가 아니라 수집 실패" 대안설명
    empt = [r for r in recs if r.get("dom_body_element_n") == 0]
    out["counterexample_dom_empty"] = {
        "n_dom_body_element_n_0": len(empt),
        "n_of_those_with_probe": sum(r["probe_present"] for r in empt),
        "n_of_those_ax_node_le2": sum(1 for r in empt if (r.get("ax_node_n") or 0) <= 2),
        "detail": [{"wtg": r["wtg"], "service": r["prior_service"], "dom_bytes": r.get("dom_bytes"),
                    "dom_script_n": r.get("dom_script_n"), "dom_noscript_n": r.get("dom_noscript_n"),
                    "ax_node_n": r.get("ax_node_n"), "ax_root_title": r.get("ax_root_title"),
                    "ax_root_url": r.get("ax_root_url"), "probe_present": r["probe_present"],
                    "probe_ans_n": r.get("probe_ans_n"), "probe_final_url": r.get("probe_final_url"),
                    "requested": r["prior_url"], "in_mart": r["in_mart"],
                    "elapsed_dom_to_probe_s": r["slot_elapsed_dom_to_probe_s"]} for r in empt]}

    # 6b. gap 분포의 형태 — 임계값이 어디서 와야 하는지의 근거
    ag = sorted(abs(g) for g in gaps)
    out["gap_shape"] = {
        "n": len(ag),
        "n_exactly_zero": sum(1 for g in ag if g == 0.0),
        "n_abs_le_0.05": sum(1 for g in ag if g <= 0.05),
        "n_abs_le_0.15": sum(1 for g in ag if g <= 0.15),
        "n_abs_ge_0.9": sum(1 for g in ag if g >= 0.9),
        "sorted_abs_top12": [round(x, 4) for x in ag[-12:]],
        "n_negative_beyond_0.05": sum(1 for g in gaps if g < -0.05),
        "note": "음수 방향 이탈이 0이면 probe >= dom 의 단방향이며, "
                "코드에서 읽은 slot 순서(dom -> probe)와 부호가 일치한다.",
    }

    # 6c. 물리적 노출창이 괴리를 예측하는가 (Spearman, 인과 아님)
    xy = [(r["slot_elapsed_dom_to_probe_s"], r["slot_name_source_gap"]) for r in withp
          if r["slot_elapsed_dom_to_probe_s"] is not None
          and r["slot_name_source_gap"] is not None]
    out["elapsed_vs_gap"] = {"n": len(xy)}
    if len(xy) > 3:
        try:
            from scipy.stats import spearmanr
            rho, pv = spearmanr([a for a, _ in xy], [b for _, b in xy])
            out["elapsed_vs_gap"].update({"spearman_rho": round(float(rho), 4),
                                          "p_value": round(float(pv), 4)})
        except Exception as e:
            out["elapsed_vs_gap"]["error"] = str(e)
    out["elapsed_vs_gap"]["interpretation_guard"] = (
        "연관만 본다. 노출창 길이가 괴리를 '일으킨다'는 주장이 아니다. "
        "노출창은 페이지 무게(스크린샷 시간)와 교락돼 있다.")

    # 6d. flag 중복 구조 — 어느 관측이 어느 flag 를 켰는가
    out["flag_overlap"] = [
        {"wtg": r["wtg"], "service": r["prior_service"], "in_mart": r["in_mart"],
         "empty_probe_rich": r["slot_dom_empty_probe_rich"],
         "title_mismatch": r["slot_title_mismatch"],
         "url_drift_interslot": r["slot_url_drift_interslot"],
         "gap_flag": r["slot_interactive_gap_flag"], "gap": r["slot_name_source_gap"],
         "score": r["slot_disagreement_score"],
         "evaluable": r["slot_disagreement_evaluable_n"],
         "probe_final_url": r["probe_final_url"]}
        for r in withp if r["slot_disagreement_score"] > 0]
    out["flag_overlap_distinct_final_urls"] = len(
        {r["probe_final_url"] for r in withp if r["slot_disagreement_score"] > 0})

    # 6e. 검열(cap 300) 이 어디에 몰려 있는가 — gap 결측의 편향
    cens = [r for r in withp if r["slot_name_source_gap_censored"]]
    out["censoring"] = {
        "n": len(cens), "denom": len(withp),
        "dom_ans_n_of_censored": describe([r["dom_ans_n"] for r in cens]),
        "dom_ans_n_of_evaluable": describe(
            [r["dom_ans_n"] for r in withp if not r["slot_name_source_gap_censored"]]),
        "note": "cap 300 검열은 큰 페이지에 몰린다. gap 지표의 결측은 MCAR 이 아니다.",
    }

    # 7. 합성 점수 분포
    out["slot_disagreement_score_dist"] = {
        str(s): sum(1 for r in withp if r["slot_disagreement_score"] == s) for s in range(0, 5)}
    out["n_any_disagreement"] = sum(1 for r in withp if r["slot_disagreement_score"] > 0)
    out["denom_any_disagreement"] = len(withp)
    return out


def make_figures(recs: list[dict], summary: dict) -> list[str]:
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except Exception:
        return []
    FIG_DIR.mkdir(exist_ok=True)
    made = []
    withp = [r for r in recs if r["probe_present"]]

    gaps = [r["slot_name_source_gap"] for r in withp if r["slot_name_source_gap"] is not None]
    fig, ax = plt.subplots(1, 2, figsize=(11, 4))
    ax[0].hist(gaps, bins=24, color="#4477aa", edgecolor="white")
    thr = summary["evidence"]["name_source_gap_log2"]["threshold_log2"]
    for s in (-thr, thr):
        ax[0].axvline(s, color="#cc3311", ls="--", lw=1)
    ax[0].axvline(0, color="#333", lw=1)
    ax[0].set_xlabel("log2( probe_ans_n+1 / dom_ans_n+1 )")
    ax[0].set_ylabel("observations")
    ax[0].set_title(f"slot_name_source_gap  (n={len(gaps)}/{len(withp)}, cap-censored excluded)")
    sens = summary["sensitivity_gap_threshold"]
    ax[1].plot([s["thr_log2"] for s in sens], [s["n_flag"] for s in sens], "o-", color="#4477aa")
    ax[1].axvline(thr, color="#cc3311", ls="--", lw=1,
                  label=f"thr {thr:.3f} = max(retest noise 0, distribution gap)")
    ax[1].set_xlabel("|log2 gap| threshold")
    ax[1].set_ylabel("n flagged")
    ax[1].set_title("threshold sensitivity")
    ax[1].legend(fontsize=8)
    fig.tight_layout()
    p = FIG_DIR / "RQ_D10_gap_distribution.png"
    fig.savefig(p, dpi=130)
    plt.close(fig)
    made.append(str(p))

    tri = [(r["dom_ans_n"], r["ax_interactive_n"], r["probe_ans_n"],
            (r["slot_disagreement_score"] or 0) > 0) for r in withp
           if r.get("ax_node_n") is not None and r.get("dom_ans_n") is not None]
    fig, ax = plt.subplots(figsize=(7.4, 5.4))
    ax.axhspan(295, 320, color="#eee", zorder=0)
    ax.text(2.02, 301, "probe cap 300", fontsize=7, color="#777", va="center")
    for d, a, p_, flag in tri:
        ax.plot([0, 1, 2], [d + 1, a + 1, p_ + 1],
                color=("#cc3311" if flag else "#999"), lw=(1.6 if flag else .7),
                alpha=(.95 if flag else .45), marker="o", ms=(4 if flag else 3),
                zorder=(3 if flag else 2))
    ax.set_yscale("log")
    ax.set_xlim(-0.15, 2.35)
    ax.set_xticks([0, 1, 2])
    ax.set_xticklabels(["dom.html\n(t0)", "ax.json\n(t0+~0.06s)", "probe.json\n(t0+~1.8s)"])
    ax.set_ylabel("element count + 1 (log scale)")
    nflag = sum(1 for t in tri if t[3])
    ax.set_title(f"three-slot trajectory per observation (n={len(tri)})\n"
                 f"red = slot_disagreement_score >= 1 (n={nflag})", fontsize=11)
    ax.annotate("dom / probe: identical selector (l0_probe.js L169, no visible filter)\n"
                "ax: AX interactive roles - a REPRESENTATION difference, not a time difference",
                xy=(0.5, -0.20), xycoords="axes fraction", ha="center",
                fontsize=7.5, color="#555")
    fig.subplots_adjust(bottom=0.22)
    p2 = FIG_DIR / "RQ_D10_three_slot_trajectory.png"
    fig.savefig(p2, dpi=130)
    plt.close(fig)
    made.append(str(p2))
    return made


def main() -> int:
    recs = collect()
    # 1) 임계값 없이 계산 → 2) 재실행 쌍의 노이즈 바닥에서 임계값 도출 → 3) 재계산.
    add_indicators(recs, gap_thr=float("inf"))
    prelim = analyse(recs, gap_thr=float("inf"))
    noise = prelim["test_retest"]["max_abs_delta"]
    # 재실행 쌍의 |Δgap| 최댓값이 0.0 이면 "노이즈 바닥이 0" 이라는 결과지, 결측이 아니다.
    # 다만 쌍이 4개뿐이라 0 을 그대로 임계값으로 쓰면 과신이다. 관측된 바닥과
    # 분포의 자연 절단(gap 히스토그램의 빈 구간) 중 큰 값을 쓴다.
    obs_gaps = sorted(abs(g) for g in
                      (r["slot_name_source_gap"] for r in recs)
                      if g is not None)
    natural_break = 0.0
    for a, b in zip(obs_gaps, obs_gaps[1:]):
        if b - a > 0.3 and a < 1.0:      # 0 근방 덩어리와 대규모 괴리 사이의 첫 큰 빈틈
            natural_break = (a + b) / 2
            break
    gap_thr = max(noise if noise is not None else 0.0, natural_break)
    add_indicators(recs, gap_thr=gap_thr)
    summary = analyse(recs, gap_thr=gap_thr)
    summary["gap_threshold_provenance"] = {
        "value_log2": round(gap_thr, 4), "value_as_ratio": round(2 ** gap_thr, 3),
        "source": "4개 재실행 쌍의 |Δ slot_name_source_gap| 최댓값 (측정 재현 노이즈 바닥)",
        "n_pairs": prelim["test_retest"]["n_pairs"],
        "observed_retest_noise_floor_log2": noise,
        "natural_break_log2": round(natural_break, 4),
        "rule": "max(재실행 노이즈 바닥, gap 분포의 첫 큰 빈틈 중점)",
        "note": "임의 상수가 아니다. 표본 4쌍에서 나온 값이므로 영구 기준이 아니라 "
                "현 데이터의 잠정 바닥이며, 재실행 쌍이 늘면 재추정해야 한다.",
    }
    figs = make_figures(recs, summary)

    per_obs = []
    for r in recs:
        per_obs.append({k: r[k] for k in (
            "worker", "wtg", "run_dir", "observation_id", "in_mart", "prior_archetype",
            "prior_service", "probe_present", "dom_ans_n", "ax_node_n", "ax_interactive_n",
            "probe_ans_n", "probe_ans_capped", "dom_body_element_n", "dom_body_text_len",
            "dom_title_utf8", "ax_root_title", "probe_title", "prior_url", "ax_root_url",
            "probe_final_url", "slot_elapsed_dom_to_probe_s", "slot_elapsed_dom_to_ax_s",
            "slot_order_as_coded", "dom_body_fill", "slot_dom_empty_probe_rich",
            "title_dissim_max", "slot_title_mismatch", "slot_title_mismatch_bytesparse",
            "url_drift_levels", "slot_url_drift", "slot_url_drift_interslot",
            "slot_name_source_gap", "slot_name_source_gap_censored", "slot_interactive_gap_flag",
            "slot_disagreement_score", "slot_disagreement_evaluable_n") if k in r})

    doc = {
        "rq": "RQ-D10",
        "question": ("evidence slot 간 시점 불일치(dom/ax=렌더 이전 SPA shell vs probe=렌더 후)를 "
                     "raw artifact에서 정량화하고 관측단위 지표로 정의할 수 있는가"),
        "ticket": "T-B-RQ-D-001 Q3",
        "label_boundary": ("D는 label 파일을 열지 않았다. A의 F-A3.1(라벨러 불일치의 원인=slot 불일치)은 "
                           "hypothesis로만 기록하며 D는 그 인과를 검증하지 않는다. D가 답한 범위는 "
                           "'slot 불일치가 실재하고 정량화 가능하며, 어느 slot을 읽었는지에 따라 "
                           "서로 다른 페이지를 본 셈이 되는 관측이 N개'까지다."),
        "grain": "observation (run_dir x observation_id). target(wtg)이 아니다.",
        "inputs": {
            "observation_table": str(OBS_JSON),
            "evidence_roots": {k: str(v) for k, v in EVIDENCE_ROOTS.items()},
            "collector_source": ("claude_b_e001_runner @876c67d323e0a02b455d841effb6f6876a253fb8 : "
                                 "research/landing_accessibility/src/landing_accessibility/engine/"
                                 "l0_collector.py L410-440"),
            "probe_source": ".../engine/l0_probe.js L143-171,L277-299",
        },
        "slot_order_from_source": SLOT_ORDER,
        "settle_ms": 400,
        "indicator_definitions": INDICATOR_DEFS,
        "summary": summary,
        "observations": per_obs,
        "figures": figs,
    }
    OUT_JSON.write_text(json.dumps(doc, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")

    s = summary
    print(f"N obs(dir)={s['N_observations_with_dir']} dom={s['N_with_dom']} "
          f"ax={s['N_with_ax']} probe={s['N_with_probe']} mart={s['N_in_mart']}")
    print("elapsed dom->probe s:", s["elapsed_dom_to_probe_s"])
    print("order as coded:", s["slot_order_as_coded_n"], "/", s["N_observations_with_dir"])
    print("mtime vs collected_at:", s["probe_mtime_minus_collected_at_s"])
    for k, v in s["evidence"].items():
        print(f"  {k}: n={v.get('n', v.get('n_evaluable'))}/{v['denom']}")
    print("gap thr(log2) =", s["gap_threshold_provenance"]["value_log2"],
          "ratio", s["gap_threshold_provenance"]["value_as_ratio"])
    print("gap dist:", s["evidence"]["name_source_gap_log2"]["dist"])
    print("retest pairs:", s["test_retest"]["n_pairs"],
          "max|Δgap|:", s["test_retest"]["max_abs_delta"])
    print("score dist:", s["slot_disagreement_score_dist"])
    print("any disagreement:", s["n_any_disagreement"], "/", s["denom_any_disagreement"])
    print("gap shape:", s["gap_shape"])
    print("elapsed vs gap:", s["elapsed_vs_gap"])
    print("censoring:", s["censoring"]["n"], "/", s["censoring"]["denom"],
          "dom_ans median censored", s["censoring"]["dom_ans_n_of_censored"].get("median"),
          "vs evaluable", s["censoring"]["dom_ans_n_of_evaluable"].get("median"))
    print("flag overlap rows:", len(s["flag_overlap"]),
          "distinct final urls:", s["flag_overlap_distinct_final_urls"])
    for r in s["flag_overlap"]:
        print("   ", r)
    print("three slot:", json.dumps(s["three_slot"], ensure_ascii=False)[:900])
    print("figures:", figs)
    return 0


INDICATOR_DEFS = [
    {
        "name": "slot_elapsed_dom_to_probe_s",
        "type": "continuous, seconds",
        "definition": "mtime(probe.json) - mtime(dom.html). slot 사이에 실제로 흐른 노출 창.",
        "why": "두 slot이 같은 시점의 페이지가 아니라는 것을 파일에서 직접 보이는 유일한 양.",
        "threshold": "없음. 원형이 연속형이다.",
        "caveat": "파일시스템 mtime 이 원천이다. 아카이브/복사로 mtime 이 재설정되면 무효. "
                  "probe.collected_at 과의 차이로 검증한다.",
    },
    {
        "name": "slot_dom_empty_probe_rich",
        "type": "binary flag",
        "definition": "dom_body_element_n == 0 AND probe_ans_n > 0.",
        "continuous_form": "dom_body_fill = dom_body_element_n / dom_element_n (0이면 shell).",
        "threshold": "0 은 임계값이 아니라 경계 자체(빈 body). 임의 상수 없음.",
        "caveat": "'shell' 과 '수집 실패' 를 구별하지 못한다. AX·probe 동반 관측으로만 갈린다.",
    },
    {
        "name": "slot_title_mismatch",
        "type": "binary flag (+ 연속형 title_dissim_max)",
        "definition": "NFKC·공백정규화·casefold 후 dom/ax/probe 세 제목 중 한 쌍이라도 불일치.",
        "continuous_form": "title_dissim_max = 세 쌍 중 최대 (1 - SequenceMatcher.ratio).",
        "threshold": "flag 는 정확일치 기준(임계값 없음). 연속형은 임계값 없이 쓸 수 있다.",
        "caveat": "dom.html 을 바이트로 파싱하면 meta charset 오해로 mojibake 가 나 "
                  "허위 불일치가 생긴다. UTF-8 강제 디코드가 필수다.",
    },
    {
        "name": "slot_url_drift",
        "type": "ordinal 0-3",
        "definition": "0 동일 / 1 query·fragment만 / 2 path 변경 / 3 host 변경. "
                      "requested(prior_url), ax RootWebArea url, probe final_url 세 쌍의 최댓값.",
        "continuous_form": "ordinal 자체가 임계값 없는 형태. 필요시 성분별로 분해해 쓴다.",
        "threshold": "없음 (URL 성분 위계에서 유도).",
        "caveat": "requested URL 은 slot 이 아니다. slot 간 드리프트만 보려면 "
                  "slot_url_drift_interslot(ax vs probe_final)을 쓴다.",
    },
    {
        "name": "slot_name_source_gap",
        "type": "continuous, log2 ratio",
        "definition": "log2((probe_ans_n+1)/(dom_ans_n+1)). 양쪽 모두 l0_probe.js L169 의 "
                      "accessible_name_sources 셀렉터로 센 수 — probe 는 런타임, dom 은 dom.html "
                      "재파싱. 두 slot이 **같은 질의**를 서로 다른 시점에 실행한 결과다. "
                      "이 셀렉터는 probe 쪽에도 visible 필터가 없어 가시성 차이가 섞이지 않는다.",
        "flag_form": "slot_interactive_gap_flag = |gap| > thr. thr 은 재실행 쌍의 "
                     "|Δgap| 최댓값(측정 노이즈 바닥)에서 유도한다.",
        "threshold": "데이터 유래. 임의 상수 아님. 쌍 수가 4뿐이므로 잠정값이다.",
        "caveat": "probe 쪽 cap 300 에 걸린 관측은 비율이 절단되므로 결측 처리한다 "
                  "(slot_name_source_gap_censored=1). 이 검열은 큰 페이지에 편중된다.",
    },
    {
        "name": "slot_disagreement_score",
        "type": "count 0-4",
        "definition": "위 flag 4종(empty_probe_rich, title_mismatch, url_drift_interslot>0, "
                      "interactive_gap_flag) 중 참인 개수. 평가 불가 성분은 분모에서 뺀다"
                      "(slot_disagreement_evaluable_n 동반 필수).",
        "threshold": "단순 개수. 가중합은 성분 간 교환비 근거가 없어 **권장하지 않는다**.",
        "caveat": "단일 스칼라로 뭉개면 어느 slot이 어긋났는지 사라진다. 성분 flag 를 항상 함께 저장한다.",
    },
]

if __name__ == "__main__":
    raise SystemExit(main())
