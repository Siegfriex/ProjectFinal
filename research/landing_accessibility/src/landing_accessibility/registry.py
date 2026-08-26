"""A2 권위자료 — 한국디지털접근성진흥원 웹접근성 인증 목록 Main Study 자체 스냅샷 수집기.

헌장상 "인증 목록에 없음 = 인증 0건"이라는 부정 판정은 **수집이 정상 완료됐을 때만** 허용된다.
그래서 이 모듈은 행을 모으는 것보다 "이 스냅샷을 부정 판정 근거로 써도 되는가"를 먼저 증명한다.
목록 1페이지 페이지네이터가 스스로 선언한 마지막 페이지 번호(`마지막 페이지로 이동`)를
완결성 기준선으로 삼고, 실제 카드가 있던 페이지 수와 대조해 COMPLETE/INCOMPLETE를 확정한다.

ported_from:
  branch: research/refcohort-r1
  commit: 32460b87334a67f6a74823ac55f85ca80a9f8980
  source_file: research/refcohort/src/refcohort/discovery.py
  changes: |
    - Pilot 자산(runs/r1-discovery)을 재사용하지 않고 Main Study 자체 스냅샷을 새로 수집한다.
      Pilot 코드를 import 하지 않고 이식했다(A6 자산이 A2 권위 경로에 섞이지 않게).
    - 완결성 게이트 신설: 페이지네이터의 선언 마지막 페이지(declared_last_page)를 파싱해
      pages_with_cards 와 대조한다. 정상 종료(NO_CARDS_AT_DECLARED_END)에서만
      snapshot_status="COMPLETE". TRANSPORT_OR_STATUS / EARLY_PAGE_TERMINATION /
      RAW_SNAPSHOT_MISSING / DUPLICATE_PAGE / DECLARED_LAST_PAGE_EXCEEDED /
      MAX_PAGES_EXHAUSTED 는 전부 INCOMPLETE.
      Pilot 은 "카드 없음"만으로 종료했고 그 종료가 정상인지 검증하지 않았다.
    - 원문 보존을 게이트에 포함: 저장 직후 파일을 되읽어 sha256 을 재계산하고
      불일치/누락이면 그 자리에서 수집을 중단한다(RAW_SNAPSHOT_MISSING).
    - 전송 실패 재시도(지수 백오프 3회) 추가. Pilot 은 1회 실패로 전수 크롤을 끝냈다.
    - 필드 파싱을 평문 정규식에서 sr-only 라벨(`기관명 :`/`인증기간 :`/`상태 :`) 앵커 기반으로 교체.
      Pilot 의 `기관명\\s*:\\s*([^인]+?)\\s*인증기간` 은 기관명에 '인'이 들어가면 매칭이 깨져
      span 순서 폴백에 의존했다.
    - 스키마 정렬: cert_start_date/cert_end_date, in_period_at_audit/cert_valid_candidate 는
      0/1 정수, raw_sha256 은 접두사 없는 hex. 산출물은 parquet + CSV + 매니페스트.
    - 유효 판정 계약을 코드로 강제: valid_at_audit_rows() 는 INCOMPLETE 스냅샷에서
      IncompleteSnapshotError 를 던진다.
    - certified_target_url_listed 를 '사이트 이동'(target="_blank") 앵커 기준으로 고르고
      원문 표기 그대로 보존한다. 목록에는 스킴이 빠진 href(`namdogallery.or.kr`)가 30건 섞여 있는데
      Pilot 은 이를 그대로 URL 로 실었고 스킴 판별 없이 첫 외부 링크를 잡았다.
      여기서는 값을 보존하되 스킴 결여 건수를 매니페스트에 세어 하류가 알고 정규화하게 한다.
    - reparse_snapshot(): 파서를 고쳐도 재요청 없이 저장된 원문만으로 레코드를 재생성한다
      (해시 재검증 포함). Pilot 에는 재파싱 경로가 없어 파서 수정마다 전수 재크롤이 필요했다.
    - 예의: 요청 간 지연 0.7초(하한 0.6초), 순차 요청만, User-Agent 에 연구 목적과 연락처 명시.
"""

from __future__ import annotations

import hashlib
import json
import re
import time
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup, Tag

CRAWLER_VERSION = "landing_accessibility.registry/1.0.0"

BASE = "http://www.kwacc.or.kr"
LIST_URL = BASE + "/CertificationSite/WA/List"
UA = (
    "LandingAccessibilityResearch/1.0 "
    "(academic study of Korean web accessibility certification; "
    "non-commercial; sequential requests, >=0.6s delay; "
    "contact: 6siegfriex@gmail.com)"
)
MIN_DELAY_SEC = 0.6
DELAY_SEC = 0.7
REQUEST_TIMEOUT = 30
MAX_RETRIES = 3

RECORD_COLUMNS = [
    "certification_number",
    "service_name",
    "organization_name",
    "certification_detail_url",
    "certified_target_url_listed",
    "certification_status_listed",
    "cert_start_date",
    "cert_end_date",
    "list_page",
    "list_index",
    "source_url",
    "raw_sha256",
    "collected_at",
    "in_period_at_audit",
    "cert_valid_candidate",
]

#: 정상 종료. 이 사유일 때만 snapshot_status="COMPLETE" 가 될 수 있다.
STOP_OK = "NO_CARDS_AT_DECLARED_END"

#: 비정상 종료 사유 — 전부 INCOMPLETE.
STOP_INCOMPLETE = (
    "TRANSPORT_OR_STATUS",  # 전송 실패 / 200 아님
    "EARLY_PAGE_TERMINATION",  # 선언된 마지막 페이지 전에 카드가 끊겼다
    "RAW_SNAPSHOT_MISSING",  # 원문 저장 실패 또는 되읽기 해시 불일치
    "DUPLICATE_PAGE",  # 직전 페이지와 동일한 카드 구성 (페이지네이션 이상)
    "DECLARED_LAST_PAGE_EXCEEDED",  # 선언 마지막 페이지를 넘어서도 카드가 나왔다
    "UNKNOWN_LAST_PAGE",  # 페이지네이터에서 마지막 페이지를 못 읽었다
    "MAX_PAGES_EXHAUSTED",  # 안전 상한에 걸렸다
)


class IncompleteSnapshotError(RuntimeError):
    """INCOMPLETE 스냅샷을 유효 판정 근거로 쓰려 할 때 발생한다."""


# ── 파싱 ────────────────────────────────────────────────────────────────────


def _clean(x: str | None) -> str:
    return re.sub(r"\s+", " ", x or "").strip()


def _iso_date(x: str | None) -> str | None:
    m = re.search(r"(\d{4})\.(\d{1,2})\.(\d{1,2})", x or "")
    if not m:
        return None
    return f"{m.group(1)}-{int(m.group(2)):02d}-{int(m.group(3)):02d}"


def sha256_hex(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def parse_declared_last_page(soup: BeautifulSoup) -> int | None:
    """페이지네이터가 선언한 마지막 페이지 번호.

    `title="마지막 페이지로 이동"` 링크를 우선하고, 없으면 노출된 페이지 번호의 최댓값을 쓴다.
    (마지막 5페이지 구간에서는 '마지막으로' 링크가 사라진다.)
    """
    nums: list[int] = []
    last_link: int | None = None
    for a in soup.select("ul.pagination a[href]"):
        href = str(a.get("href") or "")
        m = re.search(r"[?&][Pp]age=(\d+)", href)
        if not m:
            continue
        n = int(m.group(1))
        nums.append(n)
        if "마지막" in str(a.get("title") or ""):
            last_link = n
    if last_link is not None:
        return last_link
    return max(nums) if nums else None


def _labelled_value(card: Tag, label: str) -> str | None:
    """`<span class="sr-only">기관명 : </span><span>값</span>` 구조에서 값을 뽑는다."""
    for sr in card.select("span.sr-only"):
        if label in _clean(sr.get_text(" ", strip=True)):
            nxt = sr.find_next_sibling("span")
            if isinstance(nxt, Tag):
                return _clean(nxt.get_text(" ", strip=True))
    return None


_STATUS_MAP = {"유효": "VALID", "만료": "EXPIRED"}


def parse_cards(html: bytes, page: int, source_url: str) -> list[dict[str, Any]]:
    soup = BeautifulSoup(html, "html.parser")
    rows: list[dict[str, Any]] = []
    for idx, card in enumerate(soup.select("article.cert-list"), 1):
        h3 = card.select_one("h3")
        service_name = _clean(h3.get_text(" ", strip=True)) if h3 else ""

        hrefs = [str(a.get("href")) for a in card.select("a[href]") if a.get("href")]
        detail = next((h for h in hrefs if re.search(r"/CertificationSite/WA/\d+/Detail", h)), None)
        # '사이트 이동' 버튼은 target="_blank" 로 나가는 외부 링크다.
        # 목록에는 스킴이 빠진 href(`namdogallery.or.kr`)가 섞여 있으므로 스킴 유무로 거르지 않고
        # 앵커 역할로 고르고 값은 **원문 그대로** 보존한다(정규화는 하류 단계의 몫).
        target = None
        for a in card.select('a[href][target="_blank"]'):
            href = str(a.get("href")).strip()
            if not href or href == detail or href.startswith("/") or "kwacc.or.kr" in href:
                continue
            target = href
            break

        org = _labelled_value(card, "기관명")
        period_raw = _labelled_value(card, "인증기간") or ""
        status_raw = _labelled_value(card, "상태") or ""
        period = re.search(r"(\d{4}\.\d{1,2}\.\d{1,2})\s*~\s*(\d{4}\.\d{1,2}\.\d{1,2})", period_raw)

        seq = re.search(r"/CertificationSite/WA/(\d+)/Detail", detail or "")
        rows.append(
            {
                # 목록에 노출되는 유일 식별자는 상세 URL의 등록 일련번호다.
                "certification_number": seq.group(1) if seq else None,
                "service_name": service_name,
                "organization_name": org,
                "certification_detail_url": urljoin(BASE, detail) if detail else None,
                "certified_target_url_listed": target,
                "certification_status_listed": _STATUS_MAP.get(status_raw, "UNKNOWN"),
                "cert_start_date": _iso_date(period.group(1)) if period else None,
                "cert_end_date": _iso_date(period.group(2)) if period else None,
                "list_page": page,
                "list_index": idx,
                "source_url": source_url,
            }
        )
    return rows


# ── 수집 ────────────────────────────────────────────────────────────────────


@dataclass
class PageResult:
    page: int
    url: str
    http_status: int | None
    error: str | None
    attempts: int
    collected_at: str
    raw_sha256: str | None = None
    raw_path: str | None = None
    card_count: int = 0

    def as_manifest_entry(self) -> dict[str, Any]:
        return {
            "page": self.page,
            "url": self.url,
            "http_status": self.http_status,
            "error": self.error,
            "attempts": self.attempts,
            "collected_at": self.collected_at,
            "raw_path": self.raw_path,
            "raw_sha256": self.raw_sha256,
            "card_count": self.card_count,
        }


@dataclass
class CrawlOutcome:
    records: list[dict[str, Any]] = field(default_factory=list)
    pages: list[PageResult] = field(default_factory=list)
    declared_last_page: int | None = None
    stop_reason: str = "MAX_PAGES_EXHAUSTED"
    notes: list[str] = field(default_factory=list)


def _page_url(page: int) -> str:
    return LIST_URL if page == 1 else f"{LIST_URL}?page={page}"


def _fetch(session: requests.Session, url: str) -> tuple[bytes, int | None, str | None, int]:
    """순차 요청 + 지수 백오프 재시도. 반환: (body, status, error, attempts)."""
    err: str | None = None
    status: int | None = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            r = session.get(url, headers={"User-Agent": UA}, timeout=REQUEST_TIMEOUT)
            if r.status_code == 200 and r.content:
                return r.content, r.status_code, None, attempt
            err = f"HTTP_{r.status_code}" if r.status_code != 200 else "EMPTY_BODY"
            status = r.status_code
        except Exception as exc:  # 전송 실패 사유를 그대로 기록한다
            err = f"{type(exc).__name__}:{str(exc)[:200]}"
            status = None
        if attempt < MAX_RETRIES:
            time.sleep(DELAY_SEC * (2 ** (attempt - 1)))
    return b"", status, err, MAX_RETRIES


def crawl(
    out_dir: Path,
    *,
    max_pages: int = 400,
    delay_sec: float = DELAY_SEC,
    session: requests.Session | None = None,
) -> CrawlOutcome:
    """1페이지부터 카드가 끊길 때까지 순차 크롤한다. 원문은 페이지마다 즉시 저장·검증한다."""
    if delay_sec < MIN_DELAY_SEC:
        raise ValueError(f"요청 지연은 {MIN_DELAY_SEC}초 이상이어야 한다 (요청값 {delay_sec})")

    raw_dir = out_dir / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    sess = session or requests.Session()
    outcome = CrawlOutcome()
    seen_signatures: dict[str, int] = {}

    for page in range(1, max_pages + 1):
        url = _page_url(page)
        stamp = datetime.now(UTC).isoformat()
        body, status, err, attempts = _fetch(sess, url)
        result = PageResult(
            page=page,
            url=url,
            http_status=status,
            error=err,
            attempts=attempts,
            collected_at=stamp,
        )

        if err or not body:
            outcome.pages.append(result)
            outcome.stop_reason = "TRANSPORT_OR_STATUS"
            outcome.notes.append(f"page {page}: 전송/상태 실패 ({err})")
            break

        digest = sha256_hex(body)
        result.raw_sha256 = digest
        path = raw_dir / f"list_{page:04d}.html"
        path.write_bytes(body)
        # 저장 직후 되읽어 검증한다. 원문이 남지 않으면 이 스냅샷은 재현 불가다.
        if not path.exists() or sha256_hex(path.read_bytes()) != digest:
            outcome.pages.append(result)
            outcome.stop_reason = "RAW_SNAPSHOT_MISSING"
            outcome.notes.append(f"page {page}: 원문 저장 검증 실패 ({path})")
            break
        result.raw_path = str(path.relative_to(out_dir))

        soup = BeautifulSoup(body, "html.parser")
        if page == 1:
            outcome.declared_last_page = parse_declared_last_page(soup)

        rows = parse_cards(body, page, url)
        result.card_count = len(rows)
        outcome.pages.append(result)

        if not rows:
            outcome.stop_reason = STOP_OK
            break

        signature = "|".join(str(r["certification_number"]) for r in rows)
        if signature in seen_signatures:
            outcome.stop_reason = "DUPLICATE_PAGE"
            outcome.notes.append(
                f"page {page}: 카드 구성이 page {seen_signatures[signature]} 와 동일하다"
            )
            break
        seen_signatures[signature] = page

        for row in rows:
            row["raw_sha256"] = digest
            row["collected_at"] = stamp
        outcome.records.extend(rows)

        time.sleep(delay_sec)

    return outcome


# ── 완결성 게이트 ────────────────────────────────────────────────────────────


def evaluate_completeness(outcome: CrawlOutcome) -> tuple[str, str, list[str]]:
    """(stop_reason, snapshot_status, notes) 를 확정한다."""
    notes = list(outcome.notes)
    pages_with_cards = sum(1 for p in outcome.pages if p.card_count > 0)
    declared = outcome.declared_last_page
    stop = outcome.stop_reason

    if stop != STOP_OK:
        return stop, "INCOMPLETE", notes

    if declared is None:
        notes.append("1페이지 페이지네이터에서 마지막 페이지 번호를 읽지 못했다")
        return "UNKNOWN_LAST_PAGE", "INCOMPLETE", notes

    if pages_with_cards < declared:
        notes.append(
            f"선언된 마지막 페이지 {declared} 보다 이르게 종료 "
            f"(카드가 있던 페이지 {pages_with_cards})"
        )
        return "EARLY_PAGE_TERMINATION", "INCOMPLETE", notes

    if pages_with_cards > declared:
        notes.append(
            f"선언된 마지막 페이지 {declared} 를 넘어서도 카드가 나왔다 "
            f"(카드가 있던 페이지 {pages_with_cards})"
        )
        return "DECLARED_LAST_PAGE_EXCEEDED", "INCOMPLETE", notes

    if any(p.error for p in outcome.pages):
        notes.append("일부 페이지에서 전송 오류가 기록됐다")
        return "TRANSPORT_OR_STATUS", "INCOMPLETE", notes

    if any(p.card_count > 0 and not p.raw_path for p in outcome.pages):
        notes.append("원문 스냅샷이 없는 페이지가 있다")
        return "RAW_SNAPSHOT_MISSING", "INCOMPLETE", notes

    return STOP_OK, "COMPLETE", notes


def dedup_records(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """certification_number 기준 첫 관측 보존."""
    seen: dict[str, dict[str, Any]] = {}
    for r in records:
        key = r["certification_number"] or f"noseq_{r['list_page']}_{r['list_index']}"
        seen.setdefault(key, r)
    return list(seen.values())


def annotate_validity(records: list[dict[str, Any]], audit_date: date) -> None:
    """감사일 기준 기간 내 여부 + 유효 후보 플래그를 붙인다(제자리 수정)."""
    audit_iso = audit_date.isoformat()
    for r in records:
        start, end = r.get("cert_start_date"), r.get("cert_end_date")
        in_period = bool(start and end and start <= audit_iso <= end)
        r["in_period_at_audit"] = int(in_period)
        r["cert_valid_candidate"] = int(
            in_period and r.get("certification_status_listed") == "VALID"
        )


def valid_at_audit_rows(
    records: list[dict[str, Any]], manifest: dict[str, Any]
) -> list[dict[str, Any]]:
    """감사일 기준 유효 후보 행. **COMPLETE 스냅샷에서만** 반환한다.

    헌장의 "목록에 없음 = 인증 0건"은 전수 수집이 정상 종료했을 때만 성립한다.
    INCOMPLETE 스냅샷으로 유효/무효를 판정하면 미수집을 미인증으로 오독하게 되므로 막는다.
    """
    status = manifest.get("snapshot_status")
    if status != "COMPLETE":
        raise IncompleteSnapshotError(
            f"snapshot_status={status!r} — INCOMPLETE 스냅샷은 유효 판정 근거로 쓸 수 없다 "
            f"(stop_reason={manifest.get('stop_reason')!r})"
        )
    return [r for r in records if r.get("cert_valid_candidate") == 1]


# ── 스냅샷 조립 ──────────────────────────────────────────────────────────────


def build_manifest(
    outcome: CrawlOutcome,
    records: list[dict[str, Any]],
    *,
    snapshot_id: str,
    audit_date: date,
    rows_raw: int,
    delay_sec: float = DELAY_SEC,
    collected_at: str | None = None,
    reparsed_at: str | None = None,
) -> dict[str, Any]:
    stop_reason, snapshot_status, notes = evaluate_completeness(outcome)
    breakdown = {
        key: sum(1 for r in records if r["certification_status_listed"] == key)
        for key in ("VALID", "EXPIRED", "UNKNOWN")
    }
    valid_at_audit = sum(1 for r in records if r["cert_valid_candidate"] == 1)
    return {
        "snapshot_id": snapshot_id,
        "authority_rank": "A2",
        "authority_source": "한국디지털접근성진흥원(KWACC) 웹접근성 인증 목록",
        "list_url": LIST_URL,
        "audit_date": audit_date.isoformat(),
        "collected_at": collected_at or datetime.now(UTC).isoformat(),
        "reparsed_at": reparsed_at,
        "crawler_version": CRAWLER_VERSION,
        "user_agent": UA,
        "delay_sec": delay_sec,
        "parallel_requests": False,
        "pages_fetched": len(outcome.pages),
        "pages_with_cards": sum(1 for p in outcome.pages if p.card_count > 0),
        "declared_last_page": outcome.declared_last_page,
        "rows_raw": rows_raw,
        "rows_dedup": len(records),
        "status_breakdown": breakdown,
        "in_period_at_audit": sum(1 for r in records if r["in_period_at_audit"] == 1),
        "valid_at_audit": valid_at_audit,
        "rows_with_target_url": sum(1 for r in records if r["certified_target_url_listed"]),
        "rows_with_scheme_less_target_url": sum(
            1
            for r in records
            if r["certified_target_url_listed"]
            and not str(r["certified_target_url_listed"]).startswith(("http://", "https://"))
        ),
        "rows_without_target_url": sum(1 for r in records if not r["certified_target_url_listed"]),
        "rows_without_period": sum(
            1 for r in records if not (r["cert_start_date"] and r["cert_end_date"])
        ),
        "stop_reason": stop_reason,
        "snapshot_status": snapshot_status,
        "completeness_notes": notes,
        "page_hashes": [p.as_manifest_entry() for p in outcome.pages],
    }


def write_snapshot(
    out_dir: Path,
    records: list[dict[str, Any]],
    manifest: dict[str, Any],
) -> dict[str, Path]:
    import pandas as pd

    out_dir.mkdir(parents=True, exist_ok=True)
    df = pd.DataFrame(records, columns=RECORD_COLUMNS)
    df = df.sort_values(["list_page", "list_index"], kind="stable").reset_index(drop=True)

    parquet_path = out_dir / "certification_registry.parquet"
    csv_path = out_dir / "certification_registry.csv"
    manifest_path = out_dir / "registry_snapshot_manifest.json"

    df.to_parquet(parquet_path, index=False)
    df.to_csv(csv_path, index=False, encoding="utf-8-sig")
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return {"parquet": parquet_path, "csv": csv_path, "manifest": manifest_path}


def reparse_snapshot(
    out_dir: Path,
    audit_date: date,
) -> tuple[list[dict[str, Any]], dict[str, Any], dict[str, Path]]:
    """재수집 없이 **저장된 원문에서만** 레코드를 재생성한다.

    파서를 고쳤을 때 같은 스냅샷을 다시 요청하지 않기 위한 경로다(서버 부담 회피).
    각 페이지 원문의 sha256 을 기존 매니페스트 값과 대조하고, 하나라도 어긋나면
    RAW_SNAPSHOT_MISSING 으로 INCOMPLETE 처리한다. 페이지 수집 시각·HTTP 상태는
    원 수집 기록을 그대로 승계하며 새로 만들지 않는다.
    """
    manifest_path = out_dir / "registry_snapshot_manifest.json"
    prev = json.loads(manifest_path.read_text(encoding="utf-8"))

    outcome = CrawlOutcome()
    outcome.stop_reason = STOP_OK
    for entry in prev["page_hashes"]:
        result = PageResult(
            page=entry["page"],
            url=entry["url"],
            http_status=entry["http_status"],
            error=entry["error"],
            attempts=entry.get("attempts", 1),
            collected_at=entry["collected_at"],
            raw_sha256=entry["raw_sha256"],
            raw_path=entry["raw_path"],
        )
        path = out_dir / str(entry["raw_path"] or "")
        if not entry["raw_path"] or not path.exists():
            outcome.pages.append(result)
            outcome.stop_reason = "RAW_SNAPSHOT_MISSING"
            outcome.notes.append(f"page {entry['page']}: 원문 파일이 없다 ({entry['raw_path']})")
            break
        body = path.read_bytes()
        if sha256_hex(body) != entry["raw_sha256"]:
            outcome.pages.append(result)
            outcome.stop_reason = "RAW_SNAPSHOT_MISSING"
            outcome.notes.append(f"page {entry['page']}: 원문 해시가 매니페스트와 다르다")
            break

        if entry["page"] == 1:
            outcome.declared_last_page = parse_declared_last_page(
                BeautifulSoup(body, "html.parser")
            )
        rows = parse_cards(body, entry["page"], entry["url"])
        result.card_count = len(rows)
        outcome.pages.append(result)
        for row in rows:
            row["raw_sha256"] = entry["raw_sha256"]
            row["collected_at"] = entry["collected_at"]
        outcome.records.extend(rows)

    rows_raw = len(outcome.records)
    records = dedup_records(outcome.records)
    annotate_validity(records, audit_date)
    manifest = build_manifest(
        outcome,
        records,
        snapshot_id=prev["snapshot_id"],
        audit_date=audit_date,
        rows_raw=rows_raw,
        delay_sec=prev.get("delay_sec", DELAY_SEC),
        collected_at=prev["collected_at"],
        reparsed_at=datetime.now(UTC).isoformat(),
    )
    paths = write_snapshot(out_dir, records, manifest)
    return records, manifest, paths


def collect_snapshot(
    out_dir: Path,
    audit_date: date,
    *,
    snapshot_id: str,
    max_pages: int = 400,
    delay_sec: float = DELAY_SEC,
    session: requests.Session | None = None,
) -> tuple[list[dict[str, Any]], dict[str, Any], dict[str, Path]]:
    outcome = crawl(out_dir, max_pages=max_pages, delay_sec=delay_sec, session=session)
    rows_raw = len(outcome.records)
    records = dedup_records(outcome.records)
    annotate_validity(records, audit_date)
    manifest = build_manifest(
        outcome,
        records,
        snapshot_id=snapshot_id,
        audit_date=audit_date,
        rows_raw=rows_raw,
        delay_sec=delay_sec,
    )
    paths = write_snapshot(out_dir, records, manifest)
    return records, manifest, paths
