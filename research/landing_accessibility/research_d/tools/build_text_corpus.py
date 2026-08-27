"""D 공용 텍스트 코퍼스 빌더 — RF mapping 의 NLP 계열 실험 단일 입력.

SSOT 01 §7 의 Text representation 정의를 그대로 따른다:
title · top headings · landmark labels · accessible names of top controls ·
visible labels around representative region · form labels · repeated card
descriptors · URL path tokens.

각 method subagent 가 dom.html 을 따로 파싱하면 feature 가 갈린다. 파싱은 여기서만 한다.
read-only. 산출: results/D_TEXT_CORPUS.csv
"""
from __future__ import annotations

import csv
import json
import re
from pathlib import Path

from lxml import html as lxml_html

REPO = Path("/home/sieg/projects-wsl/ProjectFinal")
RD = Path(__file__).resolve().parents[1]
TABLE = RD / "results" / "D_OBSERVATION_TABLE.csv"
EVIDENCE_ROOTS = {
    f"w{n}": REPO / f".agent_worktrees/claude_b_e001_worker_{n}/artifacts/e001_w{n}/evidence"
    for n in ("01", "02", "03", "04")
}
WS = re.compile(r"\s+")
TOK = re.compile(r"[a-zA-Z0-9가-힣]+")


def T(s: str | None, limit: int = 200) -> str:
    return WS.sub(" ", (s or "")).strip()[:limit]


def texts(nodes, limit: int, per: int = 80) -> list[str]:
    out, seen = [], set()
    for n in nodes:
        t = T(n.text_content(), per)
        if len(t) < 2 or t in seen:
            continue
        seen.add(t)
        out.append(t)
        if len(out) >= limit:
            break
    return out


def attrs(nodes, name: str, limit: int) -> list[str]:
    out, seen = [], set()
    for n in nodes:
        v = T(n.get(name), 80)
        if len(v) < 2 or v in seen:
            continue
        seen.add(v)
        out.append(v)
        if len(out) >= limit:
            break
    return out


def url_tokens(url: str) -> list[str]:
    return [t.lower() for t in TOK.findall(url or "") if len(t) > 1][:40]


def extract(dom: Path, url: str) -> dict:
    tree = lxml_html.fromstring(dom.read_bytes())
    title_el = tree.find(".//title")
    meta = tree.xpath("//meta[@name='description']/@content")
    headings = texts(tree.xpath("//h1 | //h2 | //h3"), 25)
    landmarks = texts(tree.xpath("//nav | //header | //*[@role='navigation'] | //*[@role='banner']"), 6, 200)
    links = texts(tree.xpath("//nav//a[@href] | //header//a[@href]"), 40, 40)
    buttons = texts(tree.xpath("//button | //*[@role='button'] | //input[@type='submit']"), 30, 40)
    aria = attrs(tree.xpath("//*[@aria-label]"), "aria-label", 40)
    placeholders = attrs(tree.xpath("//input[@placeholder] | //textarea[@placeholder]"), "placeholder", 20)
    labels = texts(tree.xpath("//label"), 25, 40)
    # 반복 카드: 같은 class 를 가진 li/article/div 묶음에서 대표 텍스트
    cards = texts(tree.xpath("//li[.//a] | //article"), 25, 60)
    inputs = attrs(tree.xpath("//input[@name]"), "name", 25)
    fields = {
        "title": T(title_el.text if title_el is not None else "", 200),
        "meta_description": T(meta[0] if meta else "", 300),
        "headings": " | ".join(headings),
        "landmarks": " | ".join(landmarks),
        "nav_links": " | ".join(links),
        "buttons": " | ".join(buttons),
        "aria_labels": " | ".join(aria),
        "placeholders": " | ".join(placeholders),
        "form_labels": " | ".join(labels),
        "input_names": " | ".join(inputs),
        "card_texts": " | ".join(cards),
        "url_tokens": " ".join(url_tokens(url)),
    }
    fields["text_blob"] = " \n ".join(v for v in fields.values() if v)
    fields["blob_chars"] = len(fields["text_blob"])
    fields["blob_tokens"] = len(TOK.findall(fields["text_blob"]))
    return fields


def main() -> int:
    rows = list(csv.DictReader(TABLE.open(encoding="utf-8")))
    keep = [r for r in rows if r["in_mart"] == "1"]
    out = []
    for r in keep:
        dom = None
        for root in EVIDENCE_ROOTS.values():
            cand = root / r["run_dir"] / (r["observation_id"] or "") / "l0a" / "dom.html"
            if cand.exists():
                dom = cand
                break
        rec = {"wtg": r["wtg"], "run_dir": r["run_dir"], "observation_id": r["observation_id"],
               "prior_archetype": r["prior_archetype"], "prior_business_domain": r["prior_business_domain"],
               "prior_service": r["prior_service"], "prior_url": r["prior_url"],
               "dom_found": int(dom is not None)}
        rec.update(extract(dom, r["prior_url"]) if dom else
                   {k: "" for k in ("title", "meta_description", "headings", "landmarks",
                                    "nav_links", "buttons", "aria_labels", "placeholders",
                                    "form_labels", "input_names", "card_texts", "url_tokens",
                                    "text_blob")} | {"blob_chars": 0, "blob_tokens": 0})
        out.append(rec)

    cols = list(out[0].keys())
    dest = RD / "results" / "D_TEXT_CORPUS.csv"
    with dest.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=cols)
        w.writeheader()
        w.writerows(out)
    empty = sum(1 for r in out if r["blob_tokens"] == 0)
    import statistics as st
    toks = [r["blob_tokens"] for r in out]
    print(f"rows={len(out)} cols={len(cols)}  dom_found={sum(r['dom_found'] for r in out)}")
    print(f"blob_tokens median={st.median(toks)} min={min(toks)} max={max(toks)} empty={empty}")
    print(f"wrote {dest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
