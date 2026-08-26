"""LANE B / P-B PREWORK — 후보 URL target-preparation probe.

status = SHADOW_PREPARATORY · authoritative = false

## REAL-TARGET FIREWALL (`PHASE_GATES §4.5`)

이 스크립트는 **target-preparation** 이지 measurement 가 아니다.

```
허용   URL 존재 확인 · redirect 사슬 추적 · 최종 URL · PSL 등록도메인 · 문서 title
금지   DOM 저장 · AX 트리 · screenshot · KWCAG verdict · popup/obstruction 판정
       MPFED / NED / IED · evidence/ 아래 파일 생성
```

응답 본문은 `<title>` / `<html lang>` / 모바일 신호 헤더를 읽는 데만 쓰고 **즉시 버린다.**
`_FIREWALL_ASSERT` 가 산출물에 접근성 필드가 섞이지 않았음을 매 실행마다 검사한다.

## C013 대비 변경점 — 왜 그대로 쓰지 않았는가

C013 `scripts/probe_official_urls.py` 는 연구용 데스크톱 UA 하나로만 열었다.
그런데 P-B 가 확정해야 하는 것은 **공식 모바일웹 랜딩** 이다. 한국 사이트 상당수가
User-Agent 를 보고 `m.` 서브도메인·별도 경로로 리다이렉트하므로, 데스크톱 UA 로 관측한
`final_url` 은 모바일 랜딩의 근거가 되지 못한다. 그래서 **모바일 UA 를 1차 posture 로**
두고 데스크톱 UA 를 대조군으로 함께 관측해 둘을 모두 기록한다.

`_LegacyTLSAdapter`(OpenSSL 3 legacy renegotiation) · `_decode`(EUC-KR/CP949 폴백)
· PSL provenance 는 C013 에서 그대로 가져왔다. 근거는 `docs/C013_SALVAGE_LEDGER.md`.

    python shadow/lane_b/scripts/probe_official_urls_shadow.py
    python shadow/lane_b/scripts/probe_official_urls_shadow.py --only 쉼표구분키
"""

from __future__ import annotations

import argparse
import json
import re
import ssl
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import requests

ROOT = Path(__file__).resolve().parents[3]
LANE = ROOT / "shadow" / "lane_b"
sys.path.insert(0, str(ROOT / "src"))

from landing_accessibility.registered_domain import (  # noqa: E402
    psl_provenance,
    registered_domain,
)

BASE_SHA = "d5f1da5652953542d5c8be377026cc3293f2075a"

CONTACT = "6siegfriex@gmail.com"
UA_MOBILE = (
    "Mozilla/5.0 (Linux; Android 13; SM-S918N) AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Mobile Safari/537.36 "
    f"(+LandingAccessibilityResearch/2.0; academic; URL identification only; contact: {CONTACT})"
)
UA_DESKTOP = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36 "
    f"(+LandingAccessibilityResearch/2.0; academic; URL identification only; contact: {CONTACT})"
)
DELAY_SEC = 1.2
TIMEOUT_SEC = 20
MAX_REDIRECTS = 12

OP_LEGACY_SERVER_CONNECT = 0x00040000
_LEGACY_TLS_MARKER = "UNSAFE_LEGACY_RENEGOTIATION_DISABLED"

# 산출물에 절대로 나타나서는 안 되는 키 (PHASE_GATES §4.1 3~5항)
_FORBIDDEN_KEYS = {
    "verdict",
    "verdict_state",
    "criterion",
    "criterion_id",
    "kwcag",
    "final_status",
    "popup",
    "obstruction",
    "interrupt",
    "mpfed",
    "ned",
    "ied",
    "dom_path",
    "ax_path",
    "screenshot_path",
    "accessible_name",
    "ax_tree",
}


class _LegacyTLSAdapter(requests.adapters.HTTPAdapter):
    """C013 salvage — 국내 일부 사이트(현대카드)가 legacy renegotiation 을 요구한다."""

    def init_poolmanager(self, *args: object, **kwargs: object) -> object:  # type: ignore[override]
        context = ssl.create_default_context()
        context.options |= OP_LEGACY_SERVER_CONNECT
        kwargs["ssl_context"] = context
        return super().init_poolmanager(*args, **kwargs)  # type: ignore[arg-type]


_TITLE_RE = re.compile(r"<title[^>]*>(.*?)</title>", re.IGNORECASE | re.DOTALL)
_LANG_RE = re.compile(r"<html[^>]*\blang=[\"']([^\"']+)[\"']", re.IGNORECASE)
_TAG_RE = re.compile(r"<[^>]+>")
_META_CHARSET_RE = re.compile(rb"""charset=["']?([A-Za-z0-9_\-]+)""", re.IGNORECASE)
_VIEWPORT_RE = re.compile(
    r"<meta[^>]+name=[\"']viewport[\"'][^>]*content=[\"']([^\"']{0,200})", re.IGNORECASE
)
# 앱 설치 유도 신호 — EXCLUDED_APP_ONLY 후보 식별용. **판정이 아니라 신호 수집이다.**
_APP_SIGNAL_RE = re.compile(
    r"(play\.google\.com/store/apps|itunes\.apple\.com|apps\.apple\.com|market://|"
    r"itms-apps://|onelink\.me|app\.link|<meta[^>]+name=[\"']apple-itunes-app[\"'])",
    re.IGNORECASE,
)


def _decode(response: requests.Response) -> str:
    """C013 salvage — 본문을 **제목·신호를 뽑기 위해서만** 문자열로 만든다."""
    content_type = response.headers.get("Content-Type", "")
    if "text" not in content_type and "html" not in content_type:
        return ""
    raw = response.content[:200_000]
    declared = None
    if "charset=" in content_type.lower():
        declared = content_type.lower().split("charset=", 1)[1].split(";")[0].strip()
    else:
        found = _META_CHARSET_RE.search(raw[:4096])
        if found:
            declared = found.group(1).decode("ascii", "ignore").lower()
    order = [declared] if declared else []
    order += ["utf-8", "euc-kr", "cp949"]
    for encoding in order:
        if not encoding:
            continue
        try:
            return raw.decode(encoding)
        except (UnicodeDecodeError, LookupError):
            continue
    return raw.decode("utf-8", "replace")


def _clean_title(raw: str) -> str:
    text = _TAG_RE.sub(" ", raw)
    for entity, char in (
        ("&amp;", "&"),
        ("&lt;", "<"),
        ("&gt;", ">"),
        ("&nbsp;", " "),
        ("&quot;", '"'),
        ("&#39;", "'"),
    ):
        text = text.replace(entity, char)
    return " ".join(text.split())[:300]


def _session(user_agent: str, legacy_tls: bool = False) -> requests.Session:
    session = requests.Session()
    session.headers.update({"User-Agent": user_agent})
    session.max_redirects = MAX_REDIRECTS
    if legacy_tls:
        session.mount("https://", _LegacyTLSAdapter())
    return session


def probe(url: str, user_agent: str, posture: str, legacy_tls: bool = False) -> dict[str, Any]:
    """URL 하나를 연다. 저장하는 것은 전송·식별 사실뿐이다."""
    started = time.monotonic()
    record: dict[str, Any] = {
        "target_url": url,
        "ua_posture": posture,
        "http_status": None,
        "final_url": None,
        "redirect_chain": [],
        "redirect_hops": 0,
        "page_title": None,
        "content_language": None,
        "has_viewport_meta": None,
        "app_store_signal": None,
        "content_length_bytes": None,
        "error": None,
        "elapsed_ms": None,
        "tls_compat_retry": legacy_tls,
    }
    try:
        response = _session(user_agent, legacy_tls).get(
            url,
            timeout=TIMEOUT_SEC,
            allow_redirects=True,
            headers={"Accept-Language": "ko-KR,ko;q=0.9,en;q=0.5"},
        )
        record["http_status"] = response.status_code
        record["final_url"] = response.url
        record["redirect_chain"] = [
            {"status": hop.status_code, "from": hop.url, "to": hop.headers.get("Location")}
            for hop in response.history
        ]
        record["redirect_hops"] = len(response.history)
        record["content_length_bytes"] = len(response.content)
        body = _decode(response)
        title = _TITLE_RE.search(body)
        if title:
            record["page_title"] = _clean_title(title.group(1))
        lang = _LANG_RE.search(body)
        if lang:
            record["content_language"] = lang.group(1)[:20]
        if body:
            record["has_viewport_meta"] = bool(_VIEWPORT_RE.search(body))
            hit = _APP_SIGNAL_RE.search(body)
            record["app_store_signal"] = hit.group(1)[:80] if hit else None
        del body  # 본문은 여기서 버린다. 어떤 경로로도 디스크에 남기지 않는다.
    except requests.RequestException as exc:
        record["error"] = f"{type(exc).__name__}: {exc}"[:300]
        if _LEGACY_TLS_MARKER in str(exc) and not legacy_tls:
            retried = probe(url, user_agent, posture, legacy_tls=True)
            retried["tls_default_posture_error"] = record["error"]
            retried["tls_compat_reason"] = (
                "기본 TLS posture 에서 UNSAFE_LEGACY_RENEGOTIATION_DISABLED 로 실패했다. "
                "서버가 legacy renegotiation 을 요구한다."
            )
            return retried
    record["elapsed_ms"] = int((time.monotonic() - started) * 1000)
    record["final_registered_domain"] = (
        registered_domain(record["final_url"]) if record["final_url"] else None
    )
    record["target_registered_domain"] = registered_domain(url)
    record["registered_domain_changed"] = bool(
        record["final_registered_domain"]
        and record["target_registered_domain"]
        and record["final_registered_domain"] != record["target_registered_domain"]
    )
    return record


def _firewall_assert(payload: dict[str, Any]) -> None:
    """산출물에 접근성 결과 필드가 한 개도 없음을 확인한다 (PHASE_GATES §4.1 · §4.5)."""
    blob = json.dumps(payload, ensure_ascii=False).lower()
    hits = sorted(k for k in _FORBIDDEN_KEYS if f'"{k}"' in blob)
    if hits:
        raise SystemExit(f"REAL-TARGET FIREWALL 위반 — 금지 필드 {hits}")


def main() -> None:
    parser = argparse.ArgumentParser(description="LANE B target-preparation probe")
    parser.add_argument("--only", default=None, help="쉼표로 구분한 canonical_service_key 부분집합")
    parser.add_argument(
        "--candidates",
        default=str(LANE / "state" / "c013_candidate_seed_UNVERIFIED.json"),
        help="후보 URL 입력. C013 seed 는 **가설**이며 판정 근거가 아니다.",
    )
    parser.add_argument("--out", default=str(LANE / "state" / "url_probe_shadow.json"))
    args = parser.parse_args()

    candidates = json.loads(Path(args.candidates).read_text(encoding="utf-8"))
    wanted = set(args.only.split(",")) if args.only else None
    out_path = Path(args.out)

    previous: dict[str, dict[str, Any]] = {}
    if out_path.exists():
        for rec in json.loads(out_path.read_text(encoding="utf-8"))["probes"]:
            previous[
                f"{rec['canonical_service_key']}\x1f{rec['target_url']}\x1f{rec['ua_posture']}"
            ] = rec

    probes: list[dict[str, Any]] = []
    for entry in candidates["candidates"]:
        ckey = entry["canonical_service_key"]
        for url in entry["candidate_urls"]:
            for posture, ua in (("MOBILE", UA_MOBILE), ("DESKTOP", UA_DESKTOP)):
                key = f"{ckey}\x1f{url}\x1f{posture}"
                if wanted is not None and ckey not in wanted:
                    if key in previous:
                        probes.append(previous[key])
                    continue
                print(f"  [{posture:7s}] {ckey:<30} {url}", flush=True)
                record = {"canonical_service_key": ckey, **probe(url, ua, posture)}
                record["probed_at"] = datetime.now(UTC).isoformat()
                probes.append(record)
                time.sleep(DELAY_SEC)

    payload = {
        "schema": "url_probe_shadow/v1",
        "status": "SHADOW_PREPARATORY",
        "shadow_lane": "LANE_B",
        "base_sha": BASE_SHA,
        "authoritative": False,
        "created_before_p0_close": True,
        "real_target_outcome_used": False,
        "real_target_measurement": False,
        "requires_post_p0_reconciliation": True,
        "generated_by": "shadow/lane_b/scripts/probe_official_urls_shadow.py",
        "generated_at": datetime.now(UTC).isoformat(),
        "candidate_input": Path(args.candidates).name,
        "candidate_input_status": "UNVERIFIED_C013_WIP — 후보 가설일 뿐 판정 근거가 아니다",
        "user_agents": {"MOBILE": UA_MOBILE, "DESKTOP": UA_DESKTOP},
        "delay_sec": DELAY_SEC,
        "parallel_requests": False,
        "psl": psl_provenance(),
        "firewall": (
            "target-preparation probe 다 (PHASE_GATES §4.5). 저장한 것은 http_status / "
            "final_url / redirect_chain / page_title / content_language / viewport 유무 / "
            "app store 신호 유무 / PSL 등록도메인 뿐이다. DOM·AX 트리·스크린샷·본문 HTML 은 "
            "한 바이트도 저장하지 않았고 접근성 verdict 는 한 건도 생성하지 않았다."
        ),
        "probe_count": len(probes),
        "probes": sorted(
            probes, key=lambda r: (r["canonical_service_key"], r["target_url"], r["ua_posture"])
        ),
    }
    _firewall_assert(payload)
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    ok = sum(1 for r in probes if r["http_status"] == 200)
    print(f"\n관측 {len(probes)}건 · HTTP 200 {ok}건 → {out_path}")


if __name__ == "__main__":
    main()
