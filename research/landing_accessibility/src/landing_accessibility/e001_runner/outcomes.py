"""사이트 실패 격리 — target 하나의 실패를 닫힌 상태값으로 분류한다.

배치 안에서 target 하나가 어떤 이유로 실패하든 (전송 실패·타임아웃·TLS 오류·
WAF 차단·CAPTCHA·인증 gate·앱 리다이렉트) **그 target 만** 그 상태값을 받고
다음 target으로 넘어간다. 예외를 삼키지 않고 항상 닫힌 어휘로 좁힌다 —
`landing_accessibility.engine.vocabulary`가 KWCAG 판정 어휘를 닫힌 집합으로
유지하는 것과 같은 이유다: 열린 집합은 "무엇이 있었는지"를 나중에 복원할 수
없게 만든다.

이 어휘는 엔진의 `MeasurementStatus`/`EndpointStatus`(콘텐츠 레벨 판정)와
**다른 층**이다 — 여기는 "그 target에 도달을 시도하는 과정 자체가 어떻게
끝났는가"를 기록하는 배치 오케스트레이션 레벨 어휘다. 엔진이 성공적으로
관측을 끝낸 뒤에 내는 `MeasurementStatus`/`EndpointStatus`는 `map_engine_result`
로 이 어휘에 편입한다.
"""

from __future__ import annotations

import re
from enum import StrEnum
from typing import Any


class TargetOutcome(StrEnum):
    """닫힌 집합. 새 값을 추가하려면 이 모듈을 고쳐야 한다 — 호출부 임의 문자열 금지."""

    #: 엔진이 측정을 끝까지 완료했다 (콘텐츠 판정 자체의 PASS/FAIL과는 별개 축).
    MEASURED = "MEASURED"
    TRANSPORT_FAILURE = "TRANSPORT_FAILURE"
    TIMEOUT = "TIMEOUT"
    TLS_ERROR = "TLS_ERROR"
    WAF_BLOCKED = "WAF_BLOCKED"
    CAPTCHA = "CAPTCHA"
    AUTH_GATE = "AUTH_GATE"
    APP_REDIRECT = "APP_REDIRECT"
    UNRESOLVED = "UNRESOLVED"
    #: 계정 행동 금지 가드가 발화해 그 target의 activation을 물리적으로 중단했다.
    ACCOUNT_ACTION_BLOCKED = "ACCOUNT_ACTION_BLOCKED"
    #: 1회 재시도까지 모두 실패해 그 target을 skip했다 (retry.py MAX_RETRIES_PER_TARGET).
    SKIPPED_RETRY_EXHAUSTED = "SKIPPED_RETRY_EXHAUSTED"
    #: SHADOW_DRY_RUN — 계획 검증만 했고 어떤 항해도 하지 않았다.
    PLANNED_NOT_EXECUTED = "PLANNED_NOT_EXECUTED"


#: `is_failure_isolated`가 참을 반환하는 값 — 배치를 막지 않고 다음 target으로 넘어간 실패.
ISOLATED_FAILURE_OUTCOMES: frozenset[TargetOutcome] = frozenset(
    {
        TargetOutcome.TRANSPORT_FAILURE,
        TargetOutcome.TIMEOUT,
        TargetOutcome.TLS_ERROR,
        TargetOutcome.WAF_BLOCKED,
        TargetOutcome.CAPTCHA,
        TargetOutcome.AUTH_GATE,
        TargetOutcome.APP_REDIRECT,
        TargetOutcome.UNRESOLVED,
        TargetOutcome.ACCOUNT_ACTION_BLOCKED,
        TargetOutcome.SKIPPED_RETRY_EXHAUSTED,
    }
)


def is_failure_isolated(outcome: TargetOutcome) -> bool:
    return outcome in ISOLATED_FAILURE_OUTCOMES


# ── 예외 → outcome 분류 ──────────────────────────────────────────────────────
# 순서가 판정 우선순위다: 위에서부터 먼저 맞는 패턴이 이긴다.
_CLASSIFICATION_RULES: tuple[tuple[TargetOutcome, re.Pattern[str]], ...] = (
    (
        TargetOutcome.TLS_ERROR,
        re.compile(r"(ssl|tls|certificate[_ ]?verify|cert[_ ]?error|handshake)", re.IGNORECASE),
    ),
    (
        TargetOutcome.WAF_BLOCKED,
        re.compile(
            r"(waf|cloudflare|akamai|403\s*forbidden|blocked\s*by\s*(waf|firewall)|"
            r"access\s*denied|bot\s*detection)",
            re.IGNORECASE,
        ),
    ),
    (TargetOutcome.CAPTCHA, re.compile(r"captcha|recaptcha|hcaptcha", re.IGNORECASE)),
    (
        TargetOutcome.TIMEOUT,
        re.compile(r"timeout|timed\s*out|deadline\s*exceeded", re.IGNORECASE),
    ),
    (
        TargetOutcome.APP_REDIRECT,
        re.compile(
            r"(app[_ ]?only[_ ]?at[_ ]?collection|intent://|market://|"
            r"app\s*store\s*redirect|deep\s*link)",
            re.IGNORECASE,
        ),
    ),
    (
        TargetOutcome.TRANSPORT_FAILURE,
        re.compile(
            r"(net::|dns|econnrefused|econnreset|connection\s*(refused|reset)|"
            r"name\s*or\s*service\s*not\s*known|no_public_web_landing)",
            re.IGNORECASE,
        ),
    ),
)


class TargetIsolationError(RuntimeError):
    """이 예외를 던지면 그 target만 실패하고 배치는 계속된다는 것을 코드로 표시한다.

    구분 목적: `TargetIsolationError`가 아닌 예외(가드 위반·firewall 위반 등)는
    격리 대상이 아니라 배치 전체를 세워야 하는 신호일 수 있다 — `batch.py`가
    그 구분으로 "삼켜도 되는 실패"와 "삼키면 안 되는 실패"를 가른다.
    """


def classify_exception(exc: BaseException) -> TargetOutcome:
    """예외 하나를 닫힌 `TargetOutcome` 하나로 좁힌다.

    어떤 패턴에도 안 걸리면 `UNRESOLVED` 다 — 임의의 새 상태값을 만들어내지 않는다
    (엔진의 `A2` 규칙 S-3과 같은 태도: 모르면 UNKNOWN/UNRESOLVED로 흡수하되
    새 열린 값을 지어내지 않는다).
    """
    text = f"{type(exc).__name__}: {exc}"
    for outcome, pattern in _CLASSIFICATION_RULES:
        if pattern.search(text):
            return outcome
    return TargetOutcome.UNRESOLVED


def map_engine_result(result: dict[str, Any]) -> TargetOutcome:
    """엔진이 끝까지 돈 뒤의 `measurement_status`/`endpoint_status`를 이 어휘로 편입한다.

    엔진 자체가 실패를 삼키지 않고 `FAILED_*`/`UNRESOLVED`/`*_GATE_REACHED`로
    이미 분류해 두므로, 여기서는 그 값을 재해석하지 않고 **그대로 좁혀 옮긴다.**
    """
    measurement_status = str(result.get("measurement_status") or "")
    endpoint_status = str(result.get("endpoint_status") or "")
    measurement_detail = str(result.get("measurement_status_detail") or "")

    if measurement_status == "FAILED_PAGE_TIMEOUT":
        return TargetOutcome.TIMEOUT
    if measurement_status == "FAILED_BROWSER_CRASH":
        return TargetOutcome.TRANSPORT_FAILURE
    if measurement_status == "FAILED_ROBOTS_OR_TRANSPORT":
        return TargetOutcome.TRANSPORT_FAILURE
    if measurement_status == "FAILED_ACCESS_BLOCKED":
        return TargetOutcome.WAF_BLOCKED
    if measurement_status == "FAILED_EVIDENCE_INCOMPLETE":
        return TargetOutcome.UNRESOLVED
    if measurement_detail == "APP_ONLY_AT_COLLECTION":
        return TargetOutcome.APP_REDIRECT
    if measurement_detail == "NO_PUBLIC_WEB_LANDING_AT_COLLECTION":
        return TargetOutcome.APP_REDIRECT

    if endpoint_status in ("AUTH_GATE_REACHED", "PAYMENT_GATE_REACHED", "PERSONAL_DATA_REQUIRED"):
        return TargetOutcome.AUTH_GATE
    if endpoint_status == "CAPTCHA":
        return TargetOutcome.CAPTCHA
    if endpoint_status == "BLOCKED":
        return TargetOutcome.WAF_BLOCKED
    if endpoint_status == "UNRESOLVED":
        return TargetOutcome.UNRESOLVED

    return TargetOutcome.MEASURED


__all__ = [
    "ISOLATED_FAILURE_OUTCOMES",
    "TargetIsolationError",
    "TargetOutcome",
    "classify_exception",
    "is_failure_isolated",
    "map_engine_result",
]
