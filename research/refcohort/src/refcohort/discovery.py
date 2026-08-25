"""공식 인증 목록을 전수 크롤한다.

키워드 검색은 등록명 표기에 의존해 유형 편향을 만든다(fast_collection에서 5개 유형 0건).
전수 수집 후 분류하면 '0건 = 공급 부재'인지 '0건 = 키워드 실패'인지 증거로 구분할 수 있다.
"""

from __future__ import annotations

import hashlib
import re
import time
from datetime import UTC, date, datetime
from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

BASE = "http://www.kwacc.or.kr"
LIST_URL = BASE + "/CertificationSite/WA/List"
UA = "AccessibilityResearch/1.0 (+public certification registry study; contact via repository)"
DELAY_SEC = 0.6


def _clean(x: str | None) -> str:
    return re.sub(r"\s+", " ", x or "").strip()


def _iso(x: str | None) -> str | None:
    m = re.search(r"(\d{4})\.(\d{2})\.(\d{2})", x or "")
    return f"{m.group(1)}-{m.group(2)}-{m.group(3)}" if m else None


def _sha(b: bytes) -> str:
    return "sha256:" + hashlib.sha256(b).hexdigest()


def parse_cards(html: bytes, page: int, source_url: str) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    rows = []
    for n, card in enumerate(soup.select("article.cert-list"), 1):
        text = _clean(card.get_text(" ", strip=True))
        h3 = card.select_one("h3")
        title = _clean(h3.get_text(" ", strip=True)) if h3 else ""
        links = [a.get("href") for a in card.select("a[href]") if a.get("href")]
        detail = next((x for x in links if "/CertificationSite/WA/" in x and "/Detail" in x), None)
        target = next((x for x in links if not x.startswith("/") and "kwacc.or.kr" not in x), None)
        spans = [_clean(x.get_text(" ", strip=True)) for x in card.select("span")]
        org = None
        m_org = re.search(r"기관명\s*:\s*([^인]+?)\s*인증기간", text)
        if m_org:
            org = _clean(m_org.group(1))
        elif len(spans) > 1:
            org = spans[1]
        period = re.search(r"(\d{4}\.\d{2}\.\d{2})\s*~\s*(\d{4}\.\d{2}\.\d{2})", text)
        status = (
            "VALID"
            if "상태 : 유효" in text
            else ("EXPIRED" if "상태 : 만료" in text else "UNKNOWN")
        )
        seq = re.search(r"/WA/(\d+)/Detail", detail or "")
        rows.append(
            {
                "certification_number": seq.group(1) if seq else None,
                "service_name": title,
                "organization_name": org,
                "certification_detail_url": urljoin(BASE, detail) if detail else None,
                "certified_target_url_listed": target,
                "certification_status_listed": status,
                "cert_start_date_listed": _iso(period.group(1)) if period else None,
                "cert_end_date_listed": _iso(period.group(2)) if period else None,
                "list_page": page,
                "list_index": n,
                "source_url": source_url,
                "source_excerpt": text[:400],
            }
        )
    return rows


def crawl_all(
    out_dir: Path,
    audit_date: date,
    max_pages: int = 400,
    raw_keep: bool = True,
) -> dict:
    """마지막 페이지까지 순회한다. 카드가 없거나 직전 페이지와 동일하면 종료한다."""
    raw_dir = out_dir / "raw" / "official_list"
    raw_dir.mkdir(parents=True, exist_ok=True)
    s = requests.Session()
    all_rows: list[dict] = []
    pages_meta: list[dict] = []
    seen_sig: set[str] = set()
    audit_iso = audit_date.isoformat()

    for page in range(1, max_pages + 1):
        url = LIST_URL if page == 1 else f"{LIST_URL}?page={page}"
        stamp = datetime.now(UTC).isoformat()
        try:
            r = s.get(url, headers={"User-Agent": UA}, timeout=30)
            body, status, err = r.content, r.status_code, None
        except Exception as e:
            body, status, err = b"", None, f"{type(e).__name__}:{str(e)[:200]}"

        meta = {
            "page": page,
            "url": url,
            "http_status": status,
            "error": err,
            "collected_at": stamp,
            "raw_sha256": _sha(body),
            "card_count": 0,
        }
        if status != 200 or not body:
            meta["stop_reason"] = "TRANSPORT_OR_STATUS"
            pages_meta.append(meta)
            break

        rows = parse_cards(body, page, url)
        meta["card_count"] = len(rows)
        if raw_keep:
            p = raw_dir / f"list_{page:04d}.html"
            p.write_bytes(body)
            meta["raw_path"] = str(p.relative_to(out_dir))

        if not rows:
            meta["stop_reason"] = "NO_CARDS"
            pages_meta.append(meta)
            break

        sig = "|".join(str(x["certification_number"]) for x in rows)
        if sig in seen_sig:
            meta["stop_reason"] = "DUPLICATE_PAGE"
            pages_meta.append(meta)
            break
        seen_sig.add(sig)

        for x in rows:
            x["run_collected_at"] = stamp
            x["raw_sha256"] = meta["raw_sha256"]
            st, en = x["cert_start_date_listed"], x["cert_end_date_listed"]
            x["in_period_at_audit"] = bool(st and en and st <= audit_iso <= en)
            x["cert_valid_candidate_o"] = (
                "O"
                if x["certification_status_listed"] == "VALID" and x["in_period_at_audit"]
                else "X"
            )
        all_rows.extend(rows)
        pages_meta.append(meta)
        time.sleep(DELAY_SEC)

    # 인증번호 기준 중복 제거 (같은 번호가 여러 페이지에 걸치는 경우 첫 관측 보존)
    dedup: dict[str, dict] = {}
    for x in all_rows:
        k = x["certification_number"] or f"noseq_{x['list_page']}_{x['list_index']}"
        dedup.setdefault(k, x)

    summary = {
        "crawled_at": datetime.now(UTC).isoformat(),
        "audit_date": audit_iso,
        "pages_fetched": len(pages_meta),
        "rows_raw": len(all_rows),
        "rows_dedup": len(dedup),
        "valid_at_audit": sum(1 for x in dedup.values() if x["cert_valid_candidate_o"] == "O"),
        "status_breakdown": {
            k: sum(1 for x in dedup.values() if x["certification_status_listed"] == k)
            for k in ("VALID", "EXPIRED", "UNKNOWN")
        },
        "stop_reason": pages_meta[-1].get("stop_reason") if pages_meta else None,
        "pages": pages_meta,
    }
    return {"records": list(dedup.values()), "summary": summary}
