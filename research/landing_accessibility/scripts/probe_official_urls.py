"""P-B — 후보 URL 을 실제로 열어보고 **확인 결과만** 기록한다.

ported_from:
  branch: agent/landing-exec (checkpoint, UNVERIFIED WIP)
  commit: 87a0464e8159d5526069d5e654e648b0dae506ca
  source_file: research/landing_accessibility/scripts/probe_official_urls.py
  reviewed_by: claude-b/pb-prework (SHADOW_PREPARATORY)
  changes: |
    바이트 거의 그대로 포팅했다 — 이 스크립트의 관측 범위(http_status/final_url/
    redirect_chain/page_title/content_language 뿐, DOM·AX·스크린샷·본문 HTML 은 저장하지
    않음)는 v1(`06`)·v2(`02_COLLECTION_MEASUREMENT_SPEC_v2.0.md` §13, `00_SSOT_v2.0.md`
    §3 L0/L1 경계) 어느 쪽으로 봐도 "본수집(E001) 이전의 URL 식별"의 경계 안에 있다.
    아래 §6 참조를 `06 §6` → v2 근거로 교체한 것 외에는 로직을 바꾸지 않았다.
    **참고**: 이 스크립트는 네트워크로 실제 서비스에 접속한다. `claude-b/pb-prework` 는
    이 세션에서 이 스크립트를 대규모로 실행하지 않았다 — SHADOW_PREPARATORY 단계에서
    71개 서비스 전체의 URL 을 확정하는 것은 P-B exec(Claude A 소유 브랜치)의 판단
    영역이라고 보았다. `--only` 로 소수 후보에 한정한 스모크 실행은 안전하다.

## 이 스크립트가 하는 것과 하지 않는 것

```
허용   공식 URL 을 확인하기 위해 페이지를 열어보는 것 (00_SSOT §3 L0 범위 밖의
       "URL 식별" 단계 — KWCAG 측정도, MPFED 도, 접근성 verdict 도 아니다)
금지   DOM/AX/screen/probe 를 저장하는 것 (그것이 E001 본수집이다)
```

그래서 여기서 남기는 것은 `01_DATA_SPEC_v2.0.md` §3 `dim_web_target` 이 요구하는
필드(`final_url`/`url_evidence`)를 채우는 데 **필요한 최소치뿐**이다.

    http_status / final_url / redirect_chain / page_title / content_language

본문 HTML, 접근성 트리, 스크린샷은 **한 바이트도 저장하지 않는다.** 응답 본문은 title 을
뽑는 데만 쓰고 버린다. 산출물은 `state/url_review_probe.json` 하나이며 `evidence/` 아래에는
아무것도 만들지 않는다.

## 접속 예의

순차 요청, 요청 간 `DELAY_SEC` 이상 지연, 연구 목적을 밝힌 User-Agent.
A2 레지스트리 수집(`collect_certification_registry.py`)과 같은 규약이다.

## 왜 빌드와 분리했는가

네트워크 결과는 재현되지 않는다. 빌드 스크립트가 네트워크를 타면 멱등성 검사가
"같은 입력에 같은 출력" 을 확인할 수 없다. 그래서 이 스크립트가 관측을 한 번 수행해
JSON 으로 동결하고, `web_eligibility.py`/`url_evidence.py` 는 그 JSON만 읽는다.

    python scripts/probe_official_urls.py            # 후보 전건 관측 (SHADOW_DRY_RUN)
    python scripts/probe_official_urls.py --only 쉼표구분키
    python scripts/probe_official_urls.py --execution-mode FIXTURE  # 네트워크 없이 계약만 확인

## REAL-TARGET FIREWALL (`PHASE_GATES.md` §4.5)

`--execution-mode` 기본값은 `SHADOW_DRY_RUN` 이다. `REAL_TARGET` 은 P0 종료 전
`shadow_provenance.require_execution_mode()` 가 즉시 거부한다. 이 스크립트가 실제
네트워크에 접속하더라도(§4.2 "official URL research" 로 명시 허용), 그 결과는
**measurement 이 아니라 target-preparation** 이다 — `probes[i]` 어디에도 접근성
판정을 만들지 않는다(http_status/redirect_chain/title/lang 뿐).
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

ROOT = Path(__file__).resolve().parents[1]
STATE = ROOT / "state"
sys.path.insert(0, str(ROOT / "src"))

from landing_accessibility.registered_domain import (  # noqa: E402
    psl_provenance,
    registered_domain,
)
from landing_accessibility.shadow_provenance import (  # noqa: E402
    require_execution_mode,
    shadow_provenance,
)

USER_AGENT = (
    "LandingAccessibilityResearch/1.0 (academic study of Korean web accessibility; "
    "non-commercial; URL identification only, no content archiving; sequential requests, "
    ">=1.0s delay; contact: 6siegfriex@gmail.com)"
)
DELAY_SEC = 1.2
TIMEOUT_SEC = 20
MAX_REDIRECTS = 12

# 응답 본문에서 뽑는 유일한 값. 본문 자체는 저장하지 않는다.
# OpenSSL 3 은 legacy renegotiation 을 기본 차단한다. 그 설정을 요구하는 국내 사이트가
# 실제로 있어서(현대카드) 기본 요청이 SSLError 로 끝난다. 브라우저는 접속되는 사이트를
# 우리 클라이언트 설정 탓에 '확인 불가' 로 적으면 그것도 사실이 아니다.
# 그래서 기본 posture 로 한 번, 실패하면 호환 posture 로 한 번 더 시도하고 **둘 다 기록한다.**
OP_LEGACY_SERVER_CONNECT = 0x00040000
_LEGACY_TLS_MARKER = "UNSAFE_LEGACY_RENEGOTIATION_DISABLED"


class _LegacyTLSAdapter(requests.adapters.HTTPAdapter):
    def init_poolmanager(self, *args: object, **kwargs: object) -> object:  # type: ignore[override]
        context = ssl.create_default_context()
        context.options |= OP_LEGACY_SERVER_CONNECT
        kwargs["ssl_context"] = context
        return super().init_poolmanager(*args, **kwargs)  # type: ignore[arg-type]


_TITLE_RE = re.compile(r"<title[^>]*>(.*?)</title>", re.IGNORECASE | re.DOTALL)
_LANG_RE = re.compile(r"<html[^>]*\blang=[\"']([^\"']+)[\"']", re.IGNORECASE)
_TAG_RE = re.compile(r"<[^>]+>")

CANDIDATES_PATH = STATE / "url_review_candidates.json"
OUTPUT_PATH = STATE / "url_review_probe.json"


_META_CHARSET_RE = re.compile(rb"""charset=["']?([A-Za-z0-9_\-]+)""", re.IGNORECASE)


def _decode(response: requests.Response) -> str:
    """본문을 **제목을 뽑기 위해서만** 문자열로 만든다.

    한국 사이트는 Content-Type 에 charset 을 안 실으면서 실제로는 UTF-8 또는 EUC-KR 인
    경우가 많다. requests 는 그때 ISO-8859-1 로 가정하므로 제목이 깨진 채 기록된다.
    제목이 판정 근거인데 깨진 제목을 근거로 남기면 근거가 아니다.
    """
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


def _legacy_session(base: requests.Session) -> requests.Session:
    session = requests.Session()
    session.headers.update(base.headers)
    session.max_redirects = base.max_redirects
    session.mount("https://", _LegacyTLSAdapter())
    return session


def probe(url: str, session: requests.Session, legacy_tls: bool = False) -> dict[str, Any]:
    """URL 하나를 연다. 저장하는 것은 상태·최종 URL·리다이렉트 사슬·제목뿐이다."""
    started = time.monotonic()
    record: dict[str, Any] = {
        "target_url": url,
        "http_status": None,
        "final_url": None,
        "redirect_chain": [],
        "page_title": None,
        "content_language": None,
        "error": None,
        "elapsed_ms": None,
        "tls_compat_retry": False,
    }
    try:
        response = session.get(
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
        body = _decode(response)
        title = _TITLE_RE.search(body)
        if title:
            record["page_title"] = _clean_title(title.group(1))
        lang = _LANG_RE.search(body)
        if lang:
            record["content_language"] = lang.group(1)[:20]
        # 본문은 여기서 버린다. 어떤 경로로도 디스크에 남기지 않는다.
        del body
    except requests.RequestException as exc:
        record["error"] = f"{type(exc).__name__}: {exc}"[:300]
        if _LEGACY_TLS_MARKER in str(exc) and not legacy_tls:
            retried = probe(url, _legacy_session(session), legacy_tls=True)
            retried["tls_compat_retry"] = True
            retried["tls_compat_reason"] = (
                "기본 TLS posture 에서 UNSAFE_LEGACY_RENEGOTIATION_DISABLED 로 실패했다. "
                "서버가 legacy renegotiation 을 요구한다. OP_LEGACY_SERVER_CONNECT 를 켜고 "
                "한 번 더 시도한 결과다."
            )
            retried["tls_default_posture_error"] = record["error"]
            return retried
    record["elapsed_ms"] = int((time.monotonic() - started) * 1000)
    record["final_registered_domain"] = (
        registered_domain(record["final_url"]) if record["final_url"] else None
    )
    record["target_registered_domain"] = registered_domain(url)
    return record


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--only", default=None, help="쉼표로 구분한 canonical_service_key 부분집합")
    parser.add_argument(
        "--execution-mode",
        default="SHADOW_DRY_RUN",
        choices=["FIXTURE", "SHADOW_DRY_RUN", "REAL_TARGET"],
        help="PHASE_GATES.md §4.5. REAL_TARGET 은 P0 종료 전 hard FAIL.",
    )
    parser.add_argument(
        "--fixture-path",
        default=None,
        help=(
            "execution_mode=FIXTURE 일 때 이 JSON({'canonical_service_key\\x1ftarget_url': "
            "probe_record}) 에서만 읽고 네트워크를 타지 않는다."
        ),
    )
    parser.add_argument(
        "--candidates-path",
        default=None,
        help="기본값 state/url_review_candidates.json. 테스트에서 격리된 경로로 덮어쓴다.",
    )
    parser.add_argument(
        "--output-path",
        default=None,
        help="기본값 state/url_review_probe.json. 테스트에서 격리된 경로로 덮어쓴다.",
    )
    args = parser.parse_args()

    # §4.5 REAL-TARGET FIREWALL — 나머지 로직에 도달하기 전에 즉시 검사한다.
    require_execution_mode(args.execution_mode)
    if args.execution_mode == "FIXTURE" and not args.fixture_path:
        raise SystemExit("execution_mode=FIXTURE 는 --fixture-path 가 필요하다 (네트워크 금지)")

    candidates_path = Path(args.candidates_path) if args.candidates_path else CANDIDATES_PATH
    output_path = Path(args.output_path) if args.output_path else OUTPUT_PATH

    fixture: dict[str, dict[str, Any]] = {}
    if args.execution_mode == "FIXTURE":
        fixture = json.loads(Path(args.fixture_path).read_text(encoding="utf-8"))

    candidates = json.loads(candidates_path.read_text(encoding="utf-8"))
    wanted = set(args.only.split(",")) if args.only else None

    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT})
    session.max_redirects = MAX_REDIRECTS

    previous: dict[str, dict[str, Any]] = {}
    if output_path.exists():
        for rec in json.loads(output_path.read_text(encoding="utf-8"))["probes"]:
            previous[f"{rec['canonical_service_key']}\x1f{rec['target_url']}"] = rec

    probes: list[dict[str, Any]] = []
    for entry in candidates["candidates"]:
        ckey = entry["canonical_service_key"]
        for url in entry["candidate_urls"]:
            key = f"{ckey}\x1f{url}"
            if wanted is not None and ckey not in wanted:
                if key in previous:
                    probes.append(previous[key])
                continue
            if args.execution_mode == "FIXTURE":
                if key not in fixture:
                    raise SystemExit(
                        f"FIXTURE 모드인데 fixture 에 {key!r} 가 없다 — 네트워크로 채우지 않는다"
                    )
                record = {"canonical_service_key": ckey, **fixture[key]}
            else:
                print(f"  {ckey:<30} {url}", flush=True)
                record = {"canonical_service_key": ckey, **probe(url, session)}
                time.sleep(DELAY_SEC)
            record["probed_at"] = datetime.now(UTC).isoformat()
            probes.append(record)

    payload = {
        "schema": "url_review_probe/v1",
        "generated_by": "research/landing_accessibility/scripts/probe_official_urls.py",
        "probed_at": datetime.now(UTC).isoformat(),
        "shadow_provenance": shadow_provenance(
            shadow_lane="P-B", execution_mode=args.execution_mode
        ),
        "user_agent": USER_AGENT,
        "delay_sec": DELAY_SEC,
        "parallel_requests": False,
        "psl": psl_provenance(),
        "e001_boundary": (
            "이 관측은 URL 확인이지 본수집이 아니다 (00_SSOT_v2.0.md §3 L0 범위 밖, "
            "02_COLLECTION_MEASUREMENT_SPEC_v2.0.md §13). 저장한 것은 http_status / "
            "final_url / redirect_chain / page_title / content_language 뿐이며, DOM·접근성 "
            "트리·스크린샷·본문 HTML 은 한 바이트도 저장하지 않았다. evidence/ 아래에는 "
            "어떤 파일도 만들지 않는다."
        ),
        "probe_count": len(probes),
        "probes": sorted(probes, key=lambda r: (r["canonical_service_key"], r["target_url"])),
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    ok = sum(1 for r in probes if r["http_status"] == 200)
    print(f"\n관측 {len(probes)}건 · HTTP 200 {ok}건 → {output_path}")


if __name__ == "__main__":
    main()
