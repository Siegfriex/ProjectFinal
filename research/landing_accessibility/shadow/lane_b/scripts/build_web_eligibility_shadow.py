"""LANE B / P-B PREWORK — web eligibility 판정 · official URL 확정 · 그룹 가설 검정.

status = SHADOW_PREPARATORY · authoritative = false

## 이 스크립트가 판정하는 것 — 그리고 판정하지 **않는** 것

```
판정한다   web_eligibility_status (A2 §1.3 6값) — "공식 모바일웹 랜딩이 존재하는가"
판정한다   web_target_url + url_evidence + url_confidence
판정한다   그룹 가설 3건의 falsifier — 등록도메인이 갈리면 SPLIT
판정 안 함 접근성 verdict. 한 건도 만들지 않는다 (PHASE_GATES §4.1 3~5항)
판정 안 함 "그 서비스의 앱 기능을 브라우저에서 할 수 있는가" — 그것은 mapping_status 다
```

## C013 이 접은 두 축을 다시 가른다

C013 은 `OFFICIAL_PRODUCT_PAGE`(16건) · `RETAIL_OFFLINE_ONLY`(14건) 를 **적격성 쪽에서**
배제했다. 그 판정문은 실제로는 "이 랜딩에서 앱의 핵심기능이 되지 않는다" 이며,
그것은 `A2 §1.3` 이 묻는 "공식 모바일웹 랜딩이 존재하는가" 가 아니라
`A2 §1.9` `mapping_status` 가 묻는 "여기서 대표 task 를 정의할 수 있는가" 다.

두 축을 접으면 랜딩이 멀쩡히 존재하는 30건이 표본에서 조용히 빠진다.
그리고 SCOPE 가 `L0_INITIAL_LANDING + L1_SHALLOW_REPRESENTATIVE_ENTRY` 로 바뀐 지금
"이 URL 에 웹앱이 없다" 는 depth-0 시험은 판정 근거로 성립하지도 않는다.

**따라서 적격성은 랜딩 존재만으로 판정하고, 기능 가용성은 task candidate 로 넘긴다.**

## 판정 규칙 (fail-closed — 기본값이 UNDETERMINED 다)

| 규칙 | 값 | 요건 |
|---|---|---|
| E-1 | `EXCLUDED_INDUSTRY_AXIS` | `axis_type = INDUSTRY_CATEGORY`. 구조적 배제이며 URL 증거를 쓰지 않는다 |
| E-2 | `ELIGIBLE_WEB` | 모바일 UA 관측에서 2xx/3xx · 최종 URL 의 PSL 등록도메인 확정 · 브랜드 동일성 보강(제목 또는 등록도메인에 브랜드 토큰) · 앱스토어 리다이렉트가 아님 |
| E-3 | `EXCLUDED_APP_ONLY` | 확인된 공식 웹 존재가 **앱스토어 등재면뿐**이고, 부재를 어떻게 확인했는지 진술(`absence_check`)이 있다. 진술이 없으면 E-5 |
| E-4 | `EXCLUDED_NO_PUBLIC_WEB_LANDING` | 웹은 응답하나 최종 URL 이 로그인 엔드포인트이고 제목도 로그인을 가리킨다 |
| E-5 | `UNDETERMINED_URL_EVIDENCE` | 그 밖의 전부 — 무응답 · 봇차단으로 제목 미획득 · 후보 간 등록도메인 상충 · 브랜드 토큰 불일치 |

E-2 의 브랜드 동일성 요건이 이 판정의 핵심 가드다. URL 이 200 을 준다는 사실만으로는
그것이 **그 서비스의** 공식 랜딩이라는 근거가 되지 않는다 (C013 06 §2-1 과 같은 취지).
"""

from __future__ import annotations

import json
import re
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
LANE = ROOT / "shadow" / "lane_b"
sys.path.insert(0, str(ROOT / "src"))

from landing_accessibility.registered_domain import (  # noqa: E402
    registered_domain,
)

BASE_SHA = "d5f1da5652953542d5c8be377026cc3293f2075a"
REVIEWED_AT = datetime.now(UTC).date().isoformat()
REVIEWER = "LANE_B shadow executor / 모바일·데스크톱 2 posture 관측 후 규칙 판정"

# ── A2 §1.3 web_eligibility_status — 닫힌 6값 ────────────────────────────────
NOT_ASSESSED = "NOT_ASSESSED"
EXCLUDED_INDUSTRY_AXIS = "EXCLUDED_INDUSTRY_AXIS"
ELIGIBLE_WEB = "ELIGIBLE_WEB"
EXCLUDED_APP_ONLY = "EXCLUDED_APP_ONLY"
EXCLUDED_NO_PUBLIC_WEB_LANDING = "EXCLUDED_NO_PUBLIC_WEB_LANDING"
UNDETERMINED_URL_EVIDENCE = "UNDETERMINED_URL_EVIDENCE"
ALLOWED_ELIGIBILITY = {
    NOT_ASSESSED,
    EXCLUDED_INDUSTRY_AXIS,
    ELIGIBLE_WEB,
    EXCLUDED_APP_ONLY,
    EXCLUDED_NO_PUBLIC_WEB_LANDING,
    UNDETERMINED_URL_EVIDENCE,
}

# ── url_confidence — C013 에 없던 닫힌집합을 반입하며 추가했다 ────────────────
CONF_HIGH, CONF_MEDIUM, CONF_LOW = "HIGH", "MEDIUM", "LOW"
ALLOWED_CONFIDENCE = {CONF_HIGH, CONF_MEDIUM, CONF_LOW}

# ── review reason — 기계가 올린다. 사람은 추가만 하고 지우지 못한다 (C013 salvage) ──
R_NO_OBSERVATION = "NO_OBSERVATION"
R_BOT_BLOCKED = "LANDING_NOT_SEEN_BOT_BLOCKED"
R_CROSS_DOMAIN = "CROSS_REGISTERED_DOMAIN_REDIRECT"
R_TITLE_NO_BRAND = "TITLE_DOES_NOT_NAME_BRAND"
R_CANDIDATE_CONFLICT = "CANDIDATE_REGISTERED_DOMAIN_CONFLICT"
R_MOBILE_DESKTOP_DIVERGE = "MOBILE_DESKTOP_FINAL_URL_DIVERGE"
R_APP_STORE_SIGNAL = "APP_STORE_INSTALL_SIGNAL_PRESENT"
R_SLASH_PAIR = "SOURCE_LABEL_IS_SLASH_PAIR"
R_UNDETERMINED = "STATUS_UNDETERMINED_URL_EVIDENCE"
R_ANCILLARY_ONLY = "ONLY_ANCILLARY_CORPORATE_SITE_CONFIRMED"
ALLOWED_REVIEW_REASON = {
    R_NO_OBSERVATION,
    R_BOT_BLOCKED,
    R_CROSS_DOMAIN,
    R_TITLE_NO_BRAND,
    R_CANDIDATE_CONFLICT,
    R_MOBILE_DESKTOP_DIVERGE,
    R_APP_STORE_SIGNAL,
    R_SLASH_PAIR,
    R_UNDETERMINED,
    R_ANCILLARY_ONLY,
}

BLOCKED_STATUSES = {401, 403, 406, 429, 500, 502, 503, 520, 521, 522, 526}  # C013 salvage

# **등록도메인이 아니라 호스트로 판정한다.** `play.google.com` 의 등록도메인은
# `google.com` 이므로 등록도메인으로 맞추면 `www.google.com` 까지 앱스토어가 된다
# (실측: google · chrome · google_photos 3건이 이 버그로 UNDETERMINED 가 됐다).
_APP_STORE_HOSTS = {
    "play.google.com",
    "apps.apple.com",
    "itunes.apple.com",
    "galaxystore.samsung.com",
    "apps.samsung.com",
    "onestore.co.kr",
    "m.onestore.co.kr",
    "onelink.me",
}
_LOGIN_PATH_RE = re.compile(r"/(login|signin|sign_in|auth|member/login|nid/login)", re.IGNORECASE)
_LOGIN_TITLE_RE = re.compile(r"(로그인|login|sign\s?in|인증)", re.IGNORECASE)

# C013 salvage — 부재 확인 진술. **판정값이 아니라 재검증 가능한 절차 진술**로만 인용한다.
C013_ABSENCE_CHECK: dict[str, str] = {}


def load_absence_checks() -> None:
    """C013 판정표에서 `absence_check` 진술만 뽑아 온다. status 는 가져오지 않는다."""
    seed = LANE / "state" / "c013_absence_checks.json"
    if seed.exists():
        C013_ABSENCE_CHECK.update(json.loads(seed.read_text(encoding="utf-8")))


def brand_tokens(name: str, ckey: str, url: str | None) -> set[str]:
    """C013 salvage (764–784행) — 브랜드 토큰을 **기계적으로만** 만든다.

    손으로 별칭을 더하면 검사가 원하는 답 쪽으로 휘므로 금지한다.
    """
    tokens = {re.sub(r"\s+", "", str(name)).lower()}
    for piece in re.split(r"[·,／/\s]+", str(name)):
        if len(piece) >= 2:
            tokens.add(piece.lower())
    for piece in str(ckey).split("_"):
        if len(piece) >= 3:
            tokens.add(piece.lower())
    tokens.add(str(ckey).replace("_", "").lower())
    if url:
        rd = registered_domain(url)
        if rd:
            tokens.add(rd.split(".")[0].lower())
    return {t for t in tokens if t and len(t) >= 2}


def title_identifies_brand(title: str | None, tokens: set[str]) -> bool | None:
    """C013 salvage — 제목을 못 얻었으면 `False` 가 아니라 `None` 이다 (모름과 아님의 구별)."""
    if not title:
        return None
    low = re.sub(r"\s+", "", title).lower()
    return any(t in low for t in tokens)


def confidence_of(probe: dict[str, Any] | None) -> str:
    """C013 salvage (752–761행) — 관측품질에서 유도한다. 손으로 올리고 내릴 수 없다."""
    if probe is None or probe.get("error") or probe.get("http_status") is None:
        return CONF_LOW
    status = int(probe["http_status"])
    if 200 <= status < 400 and probe.get("page_title"):
        return CONF_HIGH
    if status in BLOCKED_STATUSES or 200 <= status < 400:
        return CONF_MEDIUM
    return CONF_LOW


# 소비자 서비스 랜딩이 **아닌** 호스트 라벨. 기업소개·뉴스룸·파트너·고객센터 등이다.
# 실측 근거: coupang 후보에 news.coupang.com, gmarket 후보에 corp./partner.gmarket.com 이
# 들어 있고, 이들이 200 을 주는 반면 실제 서비스 사이트(www.coupang.com·www.gmarket.co.kr)는
# WAF 로 403 을 준다. HTTP 상태만으로 고르면 **부수 사이트가 항상 이긴다.**
_ANCILLARY_HOST_LABELS = {
    "corp",
    "corporate",
    "ir",
    "about",
    "news",
    "newsroom",
    "press",
    "partner",
    "partners",
    "business",
    "biz",
    "support",
    "help",
    "helpcenter",
    "developer",
    "developers",
    "dev",
    "docs",
    "careers",
    "recruit",
    "blog",
    "company",
}
_ANCILLARY_PATH_RE = re.compile(
    r"/(company|about|ir|news|newsroom|press|partner|support|help|answer|careers|recruit)(/|$)",
    re.IGNORECASE,
)


def _host_labels(url: str | None) -> list[str]:
    from urllib.parse import urlsplit

    host = (urlsplit(url or "").hostname or "").lower()
    return host.split(".")


def is_ancillary(url: str | None) -> bool:
    """소비자 서비스 랜딩이 아니라 기업·지원·파트너 사이트인가."""
    if not url:
        return False
    labels = _host_labels(url)
    if any(lbl in _ANCILLARY_HOST_LABELS for lbl in labels):
        return True
    from urllib.parse import urlsplit

    return bool(_ANCILLARY_PATH_RE.search(urlsplit(url).path or ""))


def rank_key(probe: dict[str, Any], tokens: set[str]) -> tuple:
    """후보 URL 정렬키. **브랜드 동일성이 HTTP 상태보다 앞선다.**

    C013 은 후보를 손으로 골랐으므로 이 문제가 없었다. 기계 판정으로 바꾸면서
    `(제목획득, 리다이렉트수)` 로만 정렬했더니 WAF 로 403 을 주는 실제 서비스 사이트가
    200 을 주는 뉴스룸·기업사이트에 밀렸다 (coupang·gmarket·naver 3건 전부).

    봇차단 403 이어도 **응답 제목이 브랜드를 말하면** 그 URL 이 그 브랜드의 것이라는
    증거다. 실측: `https://www.gmarket.co.kr/` 403 · 제목 'G마켓 - 쇼핑을 바꾸는 쇼핑'.
    따라서 정렬은 (부수사이트 아님) → (브랜드 제목) → (경로 얕음) → (응답 성공) 순이다.
    """
    final = probe.get("final_url") or probe["target_url"]
    from urllib.parse import urlsplit

    brand_title = title_identifies_brand(probe.get("page_title"), tokens) is True
    status = probe.get("http_status")
    depth = len([x for x in (urlsplit(final).path or "/").split("/") if x])
    sub = len(_host_labels(final)) - len(_host_labels(f"http://{registered_domain(final) or ''}"))
    return (
        1 if is_ancillary(final) else 0,
        0 if brand_title else 1,
        max(sub, 0),
        depth,
        0 if (status and 200 <= int(status) < 400) else 1,
        probe.get("redirect_hops", 0) or 0,
    )


def _normalize_landing(url: str | None) -> str | None:
    """랜딩 비교용 정규화 — scheme·후행 슬래시만 흡수하고 host·path 는 보존한다."""
    if not url:
        return None
    from urllib.parse import urlsplit

    parts = urlsplit(url)
    host = (parts.hostname or "").lower()
    path = (parts.path or "/").rstrip("/") or "/"
    return f"{host}{path}"


def is_app_store(url: str | None) -> bool:
    from urllib.parse import urlsplit

    host = (urlsplit(url or "").hostname or "").lower()
    return host in _APP_STORE_HOSTS


def looks_like_login_endpoint(probe: dict[str, Any]) -> bool:
    final = probe.get("final_url") or ""
    title = probe.get("page_title") or ""
    return bool(_LOGIN_PATH_RE.search(final) and _LOGIN_TITLE_RE.search(title))


def evidence_of(probe: dict[str, Any] | None, url: str) -> str:
    """C013 salvage (805–825행) — 무엇을 근거로 그 URL 을 공식이라 판단했는가."""
    if probe is None:
        return f"{url} — 관측 기록 없음."
    if probe.get("error"):
        return f"{url} — 접속 실패: {probe['error']}"
    parts = [f"[{probe['ua_posture']} UA] {url} → HTTP {probe['http_status']}"]
    if probe.get("final_url") and probe["final_url"] != url:
        parts.append(f"최종 URL {probe['final_url']}")
    if probe.get("redirect_hops"):
        parts.append(f"리다이렉트 {probe['redirect_hops']}회")
    parts.append(
        f"페이지 제목 '{probe['page_title']}'"
        if probe.get("page_title")
        else "페이지 제목 미획득(봇 차단 또는 JS 렌더링)"
    )
    if probe.get("final_registered_domain"):
        parts.append(f"등록도메인(PSL) {probe['final_registered_domain']}")
    if probe.get("has_viewport_meta") is not None:
        parts.append("viewport meta 있음" if probe["has_viewport_meta"] else "viewport meta 없음")
    if probe.get("app_store_signal"):
        parts.append(f"앱스토어 신호 '{probe['app_store_signal']}'")
    return " · ".join(parts)


def judge(
    *, ckey: str, name: str, mobile: list[dict[str, Any]], desktop: list[dict[str, Any]]
) -> dict[str, Any]:
    """한 entity 의 적격성·URL 을 판정한다. 기본값은 `UNDETERMINED_URL_EVIDENCE` 다."""
    reasons: list[str] = []
    if re.search(r"[/／]", str(name)):
        reasons.append(R_SLASH_PAIR)

    live = [p for p in mobile if p.get("http_status") and 200 <= int(p["http_status"]) < 400]
    blocked = [p for p in mobile if p.get("http_status") in BLOCKED_STATUSES]
    reachable = [p for p in mobile if p.get("http_status")]
    if blocked:
        reasons.append(R_BOT_BLOCKED)
    if not any(p.get("http_status") for p in mobile):
        reasons.append(R_NO_OBSERVATION)

    result: dict[str, Any] = {
        "canonical_service_key": ckey,
        "web_eligibility_status": UNDETERMINED_URL_EVIDENCE,
        "web_target_url": None,
        "url_evidence": None,
        "url_confidence": CONF_LOW,
        "observation_confidence": CONF_LOW,
        "final_registered_domain": None,
        "redirect_hops": None,
        "mobile_candidates_live": len(live),
        "candidate_landings": None,
        "eligibility_rule": "E-5",
    }

    non_store = [p for p in live if not is_app_store(p.get("final_url"))]

    # ── E-3 앱스토어 등재면뿐인가 ────────────────────────────────────────────
    tokens0 = brand_tokens(name, ckey, None)
    # 봇차단이어도 제목이 브랜드를 말하면 그 URL 이 그 브랜드의 것이라는 증거다.
    brand_blocked = [
        p for p in blocked if title_identifies_brand(p.get("page_title"), tokens0) is True
    ]
    if live and not non_store:
        absence = C013_ABSENCE_CHECK.get(ckey)
        if absence:
            result.update(
                web_eligibility_status=EXCLUDED_APP_ONLY,
                eligibility_rule="E-3",
                url_evidence=(
                    f"확인된 공식 웹 존재가 앱스토어 등재면뿐이다. 부재 확인 절차: {absence}"
                ),
            )
            return result | {"review_reasons": reasons}
        reasons.append(R_APP_STORE_SIGNAL)
        result["url_evidence"] = (
            "살아있는 후보가 앱스토어 등재면뿐이나 공식 웹 랜딩 부재를 "
            "어떻게 확인했는지에 대한 진술이 없다. 부재를 주장하지 않는다."
        )
        return result | {"review_reasons": reasons}

    # 살아있는 후보가 전부 부수 사이트인데 브랜드 제목을 준 봇차단 후보가 있으면
    # **그쪽이 실제 서비스 랜딩**이다. 부수 사이트를 랜딩으로 확정하지 않는다.
    if brand_blocked and all(is_ancillary(p.get("final_url")) for p in non_store):
        non_store = brand_blocked + non_store
    elif brand_blocked:
        non_store = non_store + brand_blocked

    if not non_store:
        if reachable:
            result["url_evidence"] = (
                "모바일 UA 관측에서 2xx/3xx 로 응답한 비(非)스토어 후보가 없다. "
                f"관측된 상태코드: {sorted({p['http_status'] for p in reachable})}"
            )
        else:
            result["url_evidence"] = "모바일 UA 관측에서 어떤 후보도 응답하지 않았다."
        if R_UNDETERMINED not in reasons:
            reasons.append(R_UNDETERMINED)
        return result | {"review_reasons": reasons}

    if (
        len(
            {
                p.get("final_registered_domain")
                for p in non_store
                if p.get("final_registered_domain")
            }
        )
        > 1
    ):
        reasons.append(R_CANDIDATE_CONFLICT)

    # slash pair entity 는 두 브랜드를 합산한 측정단위다. 후보 랜딩이 서로 다른
    # 브랜드로 갈리면 **어느 쪽을 이 entity 의 랜딩이라 할 근거가 없다.**
    # 제목이 우연히 한쪽 토큰과 맞는다는 이유로 고르면 나머지 절반이 조용히 사라진다.
    if R_SLASH_PAIR in reasons:
        distinct_landings = {
            _normalize_landing(p.get("final_url") or p["target_url"]) or ""
            for p in non_store
            if not is_ancillary(p.get("final_url") or p["target_url"])
        }
        if len(distinct_landings) > 1:
            reasons.append(R_CANDIDATE_CONFLICT)
            if R_UNDETERMINED not in reasons:
                reasons.append(R_UNDETERMINED)
            result["url_evidence"] = (
                f"slash pair entity 의 후보 랜딩이 {sorted(distinct_landings)} 로 갈린다. "
                "두 브랜드 중 어느 쪽을 이 measurement entity 의 랜딩이라 할 근거가 없다. "
                "확정하지 않는다."
            )
            result["candidate_landings"] = ",".join(sorted(distinct_landings))
            return result | {"review_reasons": reasons}

    best = sorted(non_store, key=lambda p: rank_key(p, tokens0))[0]
    if is_ancillary(best.get("final_url") or best["target_url"]):
        reasons.append(R_ANCILLARY_ONLY)
        result["url_evidence"] = (
            f"확인된 후보가 기업·지원·파트너 사이트뿐이다 "
            f"({best.get('final_url') or best['target_url']}). "
            "소비자 서비스 랜딩을 확정하지 못했다."
        )
        if R_UNDETERMINED not in reasons:
            reasons.append(R_UNDETERMINED)
        return result | {"review_reasons": reasons}
    probe_conf = confidence_of(best)
    result["observation_confidence"] = probe_conf
    result["final_registered_domain"] = best.get("final_registered_domain")
    result["redirect_hops"] = best.get("redirect_hops")
    result["url_evidence"] = evidence_of(best, best["target_url"])

    if best.get("registered_domain_changed"):
        reasons.append(R_CROSS_DOMAIN)

    # 모바일·데스크톱 최종 URL 분기 — 사실로 기록하되 배제 사유는 아니다.
    dmatch = next((d for d in desktop if d["target_url"] == best["target_url"]), None)
    if dmatch and dmatch.get("final_url") and best.get("final_url") != dmatch.get("final_url"):
        reasons.append(R_MOBILE_DESKTOP_DIVERGE)

    # ── E-4 로그인 이전 공개 랜딩이 없는가 ──────────────────────────────────
    if looks_like_login_endpoint(best):
        result.update(
            web_eligibility_status=EXCLUDED_NO_PUBLIC_WEB_LANDING,
            eligibility_rule="E-4",
            web_target_url=None,
            url_confidence=probe_conf,
        )
        return result | {"review_reasons": reasons}

    # ── E-2 브랜드 동일성 보강 ──────────────────────────────────────────────
    tokens = brand_tokens(name, ckey, best.get("final_url"))
    brand_ok = title_identifies_brand(best.get("page_title"), tokens)
    rd = best.get("final_registered_domain") or ""
    domain_ok = any(t in rd.replace(".", "") for t in tokens if len(t) >= 3)

    if brand_ok is False and not domain_ok:
        reasons.append(R_TITLE_NO_BRAND)
        if R_UNDETERMINED not in reasons:
            reasons.append(R_UNDETERMINED)
        return result | {"review_reasons": reasons}
    if brand_ok is None and not domain_ok:
        reasons.append(R_TITLE_NO_BRAND)
        if R_UNDETERMINED not in reasons:
            reasons.append(R_UNDETERMINED)
        return result | {"review_reasons": reasons}

    result["candidate_landings"] = ",".join(
        sorted(
            {
                _normalize_landing(p.get("final_url") or p["target_url"]) or ""
                for p in non_store
                if not is_ancillary(p.get("final_url") or p["target_url"])
            }
        )
    )
    result.update(
        web_eligibility_status=ELIGIBLE_WEB,
        eligibility_rule="E-2",
        web_target_url=best.get("final_url") or best["target_url"],
        url_confidence=probe_conf,
    )
    return result | {"review_reasons": reasons}
