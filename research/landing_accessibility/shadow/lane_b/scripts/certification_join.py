"""LANE B / P-B PREWORK — 인증 join **infrastructure**.

status = SHADOW_PREPARATORY · authoritative = false

## 이 모듈이 하는 일과 하지 않는 일 (`PHASE_GATES §4.1` 7항 · `§4.6`)

```
허용   web target 하나에 KWACC 인증행을 1:1 로 붙일 수 있는지 판정하는 규칙
       그 규칙이 성립하지 않는 건을 UNDETERMINED 로 남기는 것
금지   인증 결과를 보고 target 을 고르거나 버리는 것
       인증 결과로 representative task 를 고르는 것
```

`certified_current` 는 **산출물의 한 컬럼**이지 표본 선정 입력이 아니다.
`assert_not_used_for_selection()` 이 이 경계를 코드로 못 박는다.

## 왜 `01 §8` 3요건만으로 1:1 이 성립하지 않는가 — 실측

레지스트리 전량 2283행에서 이름은 1282종, URL 은 1167종이다. 한 이름이 최대 7행,
한 URL 이 최대 11행에 걸린다. 그러나 이 fan-out 의 **대부분은 갱신 이력**이다.
요건1(유효기간)을 걸면 226행이 남고 fan-out 은 이름 최대 2 · URL 최대 2 로 줄어든다.

남는 fan-out 은 갱신이 아니라 **범위 분리**다. 실측 사례:

```
2333  맥도날드(모바일웹)  https://www.mcdonalds.co.kr  2025-12-17~2026-12-16  VALID
2332  맥도날드           https://www.mcdonalds.co.kr  2025-12-17~2026-12-16  VALID
```

같은 URL·같은 기간에 두 인증이 존재하며 구분자는 `service_name` 의 후행 괄호뿐이다.
즉 **`(모바일웹)` 접미사가 요건2(대상범위)의 실질적 판정 근거**다. 이 접미사는
전량에서 30행, 유효 226행 중 7행에 나타난다.

그리고 이것이 `SCOPE_UNDIFFERENTIATED`(접미사 없음)를 자동으로 통과시킬 수 없는 이유다.
맥도날드 패턴은 **기관이 둘을 나눠 신청할 때 접미사 없는 행은 데스크톱을 뜻함**을 보여준다.
따라서 접미사 없는 행은 같은 등록도메인·같은 기간에 `(모바일웹)` 형제행이 **없을 때만**
모바일웹을 포괄한다고 읽는다. 형제가 있으면 그 행은 `SCOPE_DESKTOP_IMPLIED` 이고 요건2 미충족이다.

## 경계 결함 처리 규칙 (EDA-00 지적 2건)

| 결함 | 실측 | 규칙 |
|---|---|---|
| `certification_status_listed = VALID` 인데 `cert_start` 가 audit_date 다음날 | 2521 국립망향의동산 (start 2026-08-27, audit 2026-08-26) | `NOT_YET_EFFECTIVE`. **계산된 기간이 게시 상태를 이긴다** — 유효후보 제외 |
| `cert_end < cert_start` | 1095 주택관리공단 (2020-12-12 ~ 2020-12-11) | `PERIOD_INVERTED`. 기간을 신뢰할 수 없으므로 유효후보 제외 |
| 기간 자체가 결측 | 1812 (`service_name` 이 `-`) | `PERIOD_MISSING`. 유효후보 제외 |

세 규칙 모두 **fail-closed** 다. 게시 상태가 계산 결과와 어긋나면 유효하다고 보지 않는다.
이 때문에 `VALID` 게시 227행 → 유효후보 **226행**이 된다.
"""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "src"))

from landing_accessibility.registered_domain import registered_domain  # noqa: E402

# ── 요건2 어휘: service_name 후행 괄호가 지시하는 대상범위 ──────────────────────
SCOPE_MOBILE_WEB = "SCOPE_MOBILE_WEB"
SCOPE_UNDIFFERENTIATED = "SCOPE_UNDIFFERENTIATED"
SCOPE_DESKTOP_IMPLIED = "SCOPE_DESKTOP_IMPLIED"
SCOPE_LANGUAGE_VARIANT = "SCOPE_LANGUAGE_VARIANT"
SCOPE_SUBSYSTEM = "SCOPE_SUBSYSTEM"

_MOBILE_TOKENS = {"모바일웹", "모바일", "mobile"}
_LANGUAGE_TOKENS = {
    "영문",
    "국문",
    "영어",
    "일어",
    "일문",
    "중문",
    "다국어",
    "중국어-번체",
    "중국어-간체",
    "중국어",
    "en",
    "eng",
}
_SUFFIX_RE = re.compile(r"[(（]([^)）]{1,20})[)）]\s*$")

# ── join 결과 어휘 (3값, 상호배타) ────────────────────────────────────────────
CERTIFIED_CURRENT = "CERTIFIED_CURRENT"
NOT_CERTIFIED = "NOT_CERTIFIED"
UNDETERMINED = "UNDETERMINED"

# 레지스트리 행 기간 결함 어휘
PERIOD_OK = "PERIOD_OK"
PERIOD_MISSING = "PERIOD_MISSING"
PERIOD_INVERTED = "PERIOD_INVERTED"
NOT_YET_EFFECTIVE = "NOT_YET_EFFECTIVE"
PERIOD_ELAPSED = "PERIOD_ELAPSED"


def split_scope(service_name: str | None) -> tuple[str, str]:
    """`service_name` 을 (정규화 이름, 대상범위 토큰) 으로 가른다."""
    if not isinstance(service_name, str) or not service_name.strip():
        return "", SCOPE_UNDIFFERENTIATED
    name = service_name.strip()
    found = _SUFFIX_RE.search(name)
    if not found:
        return _norm_name(name), SCOPE_UNDIFFERENTIATED
    token = found.group(1).strip()
    base = _norm_name(name[: found.start()])
    low = token.lower()
    if low in _MOBILE_TOKENS or "모바일" in token:
        return base, SCOPE_MOBILE_WEB
    if low in _LANGUAGE_TOKENS:
        return base, SCOPE_LANGUAGE_VARIANT
    return base, SCOPE_SUBSYSTEM


def _norm_name(name: str) -> str:
    """공백·구분자를 지운 비교용 이름. 표기 흔들림만 흡수하고 의미는 건드리지 않는다."""
    return re.sub(r"[\s·,／/\-_()（）]+", "", str(name)).lower()


_IPV4_RE = re.compile(r"^\d{1,3}(?:\.\d{1,3}){3}$")


def rd_of(url: str | None) -> str | None:
    """PSL 등록도메인. scheme 이 없는 표기(레지스트리 실측 26행)도 받는다.

    IP 리터럴은 등록도메인이 **정의되지 않는다.** PSL 에 넣으면 `210.118.135.41` 이
    `135.41` 이라는 그럴듯한 쓰레기가 되어 나오므로 (레지스트리 실측 1건) 여기서 막는다.
    """
    if not isinstance(url, str) or not url.strip():
        return None
    candidate = url.strip()
    if "://" not in candidate:
        candidate = "http://" + candidate
    from urllib.parse import urlsplit

    host = (urlsplit(candidate).hostname or "").strip().rstrip(".")
    if not host or _IPV4_RE.match(host) or ":" in host:
        return None
    try:
        return registered_domain(candidate)
    except Exception:
        return None


def classify_period(start: Any, end: Any, audit_date: str) -> str:
    """요건1 — 유효기간. 게시 상태를 보지 않고 **날짜만으로** 판정한다 (fail-closed)."""
    if not _is_date(start) or not _is_date(end):
        return PERIOD_MISSING
    if str(end) < str(start):
        return PERIOD_INVERTED
    if str(start) > audit_date:
        return NOT_YET_EFFECTIVE
    if str(end) < audit_date:
        return PERIOD_ELAPSED
    return PERIOD_OK


def _is_date(value: Any) -> bool:
    return isinstance(value, str) and bool(re.fullmatch(r"\d{4}-\d{2}-\d{2}", value.strip()))


def prepare_registry(registry: pd.DataFrame, audit_date: str) -> pd.DataFrame:
    """레지스트리 전량에 요건1·요건2 파생컬럼을 붙인다. 행을 버리지 않는다."""
    out = registry.copy()
    out["period_status"] = [
        classify_period(s, e, audit_date)
        for s, e in zip(out["cert_start_date"], out["cert_end_date"], strict=True)
    ]
    out["req1_valid"] = out["period_status"] == PERIOD_OK
    parsed = [split_scope(n) for n in out["service_name"]]
    out["name_normalized"] = [p[0] for p in parsed]
    out["scope_token"] = [p[1] for p in parsed]
    out["cert_registered_domain"] = out["certified_target_url_listed"].map(rd_of)
    out["listed_status_disagrees"] = (
        out["certification_status_listed"].eq("VALID") & ~out["req1_valid"]
    ) | (~out["certification_status_listed"].eq("VALID") & out["req1_valid"])

    # SCOPE_UNDIFFERENTIATED → 같은 등록도메인·유효기간에 (모바일웹) 형제가 있으면 데스크톱 함의
    valid = out[out["req1_valid"]]
    mobile_domains = set(
        valid.loc[valid["scope_token"] == SCOPE_MOBILE_WEB, "cert_registered_domain"].dropna()
    )
    out["scope_effective"] = [
        SCOPE_DESKTOP_IMPLIED
        if (tok == SCOPE_UNDIFFERENTIATED and valid_ and dom in mobile_domains)
        else tok
        for tok, dom, valid_ in zip(
            out["scope_token"], out["cert_registered_domain"], out["req1_valid"], strict=True
        )
    ]
    out["req2_scope_match"] = out["scope_effective"].isin(
        {SCOPE_MOBILE_WEB, SCOPE_UNDIFFERENTIATED}
    )
    return out


@dataclass
class JoinResult:
    web_target_id: str
    web_target_key: str
    web_target_url: str | None
    web_registered_domain: str | None
    certified_current: int | None
    join_outcome: str
    certification_number: str | None = None
    cert_start: str | None = None
    cert_end: str | None = None
    target_scope_match: bool | None = None
    service_identity_match: bool | None = None
    match_basis: str = ""
    domain_candidate_count: int = 0
    valid_candidate_count: int = 0
    survivor_count: int = 0
    survivor_certification_numbers: list[str] = field(default_factory=list)
    undetermined_reason: str | None = None


def join_one(
    *,
    web_target_id: str,
    web_target_key: str,
    web_target_url: str | None,
    service_names: list[str],
    prepared: pd.DataFrame,
) -> JoinResult:
    """web target 하나에 인증행을 붙인다. 1:1 이 성립하지 않으면 `UNDETERMINED` 다."""
    wrd = rd_of(web_target_url)
    base = JoinResult(
        web_target_id=web_target_id,
        web_target_key=web_target_key,
        web_target_url=web_target_url,
        web_registered_domain=wrd,
        certified_current=None,
        join_outcome=UNDETERMINED,
    )

    # URL 이 확정되지 않으면 요건2 를 **시험할 수 없다**. 없음(0)이 아니라 모름이다.
    if not wrd:
        base.undetermined_reason = "WEB_TARGET_URL_UNRESOLVED — 요건2를 시험할 입력이 없다"
        base.match_basis = "URL 미확정. 인증 부재를 주장할 근거도 없다."
        return base

    domain_rows = prepared[prepared["cert_registered_domain"] == wrd]
    base.domain_candidate_count = len(domain_rows)

    # 부재의 증거: 스냅샷 전량(2283행, snapshot_status=COMPLETE)에 그 등록도메인이 없다.
    if domain_rows.empty:
        base.certified_current = 0
        base.join_outcome = NOT_CERTIFIED
        base.target_scope_match = False
        base.service_identity_match = False
        base.match_basis = (
            f"등록도메인 {wrd} 이 KWACC 스냅샷 전량 {len(prepared)}행에 존재하지 않는다. "
            "미매칭이 아니라 **부재의 실측**이다 (snapshot_status=COMPLETE)."
        )
        return base

    valid_rows = domain_rows[domain_rows["req1_valid"]]
    base.valid_candidate_count = len(valid_rows)
    if valid_rows.empty:
        base.certified_current = 0
        base.join_outcome = NOT_CERTIFIED
        base.target_scope_match = False
        base.service_identity_match = False
        base.match_basis = (
            f"등록도메인 {wrd} 의 인증 {len(domain_rows)}건은 모두 요건1(유효기간) 미충족이다 "
            f"({sorted(set(domain_rows['period_status']))}). 과거 인증은 현재 인증이 아니다."
        )
        return base

    # 요건2 — 대상범위
    scoped = valid_rows[valid_rows["req2_scope_match"]]
    if scoped.empty:
        base.target_scope_match = False
        base.undetermined_reason = "REQ2_SCOPE_NO_MOBILE_WEB"
        base.match_basis = (
            f"유효 인증 {len(valid_rows)}건이 있으나 대상범위가 모두 모바일웹 밖이다 "
            f"({sorted(set(valid_rows['scope_effective']))}). "
            "인증이 없다고도, 있다고도 말할 수 없다."
        )
        base.survivor_certification_numbers = [str(x) for x in valid_rows["certification_number"]]
        return base

    # 요건3 — 서비스 동일성. 등록도메인이 1차 근거, 이름이 보강 근거다.
    wanted = {_norm_name(n) for n in service_names if n}
    named = scoped[
        [any(nn and (nn in w or w in nn) for w in wanted) for nn in scoped["name_normalized"]]
    ]
    if named.empty:
        # **도메인 단독으로 동일성을 주장하지 않는다.** 한 등록도메인이 서로 다른 서비스
        # 여럿을 담기 때문이다. 실측: samsung.com 의 유일한 유효인증은 '삼성전자승마단'
        # 이고, 이것을 '삼성 브라우저'·'삼성 노트'·'삼성 월렛' 에 붙이면 세 건이 한꺼번에
        # 거짓양성이 된다. spectrummap.kr 은 한 도메인에 서로 다른 시스템 4종을 담는다.
        base.target_scope_match = True
        base.service_identity_match = False
        base.survivor_count = len(scoped)
        base.survivor_certification_numbers = [str(x) for x in scoped["certification_number"]]
        base.undetermined_reason = "REQ3_IDENTITY_NO_NAME_MATCH"
        base.match_basis = (
            f"등록도메인 {wrd} 에 요건1·2 를 통과한 인증이 {len(scoped)}건 있으나 "
            f"서비스 이름이 어느 것과도 대응하지 않는다 "
            f"(레지스트리 {sorted(set(scoped['service_name']))[:4]} ↔ 타겟 {web_target_key}). "
            "등록도메인 일치는 동일성의 필요조건이지 충분조건이 아니다. "
            "**인증이 없다고도 말하지 않는다** — 그 도메인에 유효 인증이 실재하기 때문이다."
        )
        return base
    survivors, identity_basis = named, "REGISTERED_DOMAIN_AND_NAME"

    base.survivor_count = len(survivors)
    base.survivor_certification_numbers = [str(x) for x in survivors["certification_number"]]
    if len(survivors) > 1:
        base.target_scope_match = True
        base.service_identity_match = True
        base.undetermined_reason = "MULTI_SURVIVOR_NOT_1_TO_1"
        base.match_basis = (
            f"요건1·2·3 을 모두 통과한 인증이 {len(survivors)}건이다. "
            "3요건은 이 건에서 1:1 을 만들지 못한다. 임의로 하나를 고르지 않는다."
        )
        return base

    row = survivors.iloc[0]
    base.certified_current = 1
    base.join_outcome = CERTIFIED_CURRENT
    base.certification_number = str(row["certification_number"])
    base.cert_start = str(row["cert_start_date"])
    base.cert_end = str(row["cert_end_date"])
    base.target_scope_match = True
    base.service_identity_match = True
    base.match_basis = (
        f"요건1 기간 {row['cert_start_date']}~{row['cert_end_date']} · "
        f"요건2 범위 {row['scope_effective']} · 요건3 {identity_basis} "
        f"(레지스트리 '{row['service_name']}' ↔ 타겟 {web_target_key}) · "
        f"등록도메인 {wrd} PSL 판정"
    )
    return base


def assert_not_used_for_selection(before: list[str], after: list[str]) -> None:
    """인증 결과가 target 집합을 바꾸지 않았음을 못 박는다 (`PHASE_GATES §4.1` 7항 · `§4.6`)."""
    if sorted(before) != sorted(after):
        raise SystemExit(
            "PHASE_GATES §4.6 위반 — 인증 join 전후로 web target 집합이 달라졌다. "
            "인증 결과로 target 을 고르는 것은 금지다."
        )
