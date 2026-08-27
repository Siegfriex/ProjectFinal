"""계정 행동 금지 가드 — login/signup/purchase/payment/message send/booking
confirm/OTP 입력/개인정보 입력/CAPTCHA 우회로 이어질 수 있는 activation 후보를
**클릭이 일어나기 전에** 걸러낸다.

## 왜 엔진의 gate 판별에만 기대지 않는가

`landing_accessibility.engine.l1_engine.Scout`는 이미 구조적으로 안전하다 —
`_activate()`는 검색창(QUERY archetype)만 텍스트를 채우고, 그 밖에는 오직
버튼/링크를 클릭할 뿐 어떤 자격증명·개인정보 필드도 채우지 않는다
(`engine/l1_engine.py` 규칙 E-7 참조). 그리고 gate가 관측되면 그 즉시
activation 확장을 멈춘다.

하지만 이 배치 러너는 P-C가 검증한 17개의 통제된 fixture가 아니라, E001_PLAN이
가리키는 **다양한 실제 서비스 구조**를 순회하도록 설계된다. gate_classifier의
결정적 사전(§`engine/gate_classifier.py`)이 놓친 형태 — 예를 들어 구조적
gate 신호 없이 그냥 "로그인" 버튼 하나만 있는 화면 — 를 대비해, 이 층은
**엔진의 gate 판별과 독립적으로** activation 후보 자체를 검사한다.

이 가드가 감지하면 `landing_accessibility.engine.l1_engine.Scout`를 아예
호출하지 않는다 — 즉 금지된 행동으로 이어질 수 있는 클릭이 발생하는
코드 경로 자체가 실행되지 않는다 (`batch.py`의 `run_l1_if_safe` 참조).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any


class AccountActionBlockedError(RuntimeError):
    """금지된 계정 행동으로 이어질 수 있는 activation 후보를 감지해 중단했다.

    이 예외는 재시도 대상이 아니다 (`retry.py`) — 가드가 막은 것은 transient
    실패가 아니라 **범위 위반**이므로, 재시도는 같은 위반을 다시 시도하는
    것일 뿐이다.
    """


class ActionCategory:
    LOGIN = "LOGIN"
    SIGNUP = "SIGNUP"
    PURCHASE = "PURCHASE"
    PAYMENT = "PAYMENT"
    MESSAGE_SEND = "MESSAGE_SEND"
    BOOKING_CONFIRM = "BOOKING_CONFIRM"
    OTP_ENTRY = "OTP_ENTRY"
    PERSONAL_DATA_ENTRY = "PERSONAL_DATA_ENTRY"
    CAPTCHA_BYPASS = "CAPTCHA_BYPASS"
    CREDENTIAL_FIELD = "CREDENTIAL_FIELD"


#: 텍스트(accessible_name/visible_text/aria_label) 기반 탐지 사전.
#: 결정적 키워드 매칭이며, 애매하면(패턴이 안 걸리면) 차단하지 **않는다** — 과탐으로
#: 정당한 후보를 막는 것도 결함이다 (P-C `failure_injection.py`의 MUST_PASS 사상과 동일).
_FORBIDDEN_TEXT_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    (
        ActionCategory.OTP_ENTRY,
        re.compile(r"(인증\s*번호|보안\s*코드|otp|one[- ]?time\s*(code|password))", re.IGNORECASE),
    ),
    (
        ActionCategory.PAYMENT,
        re.compile(
            r"(결제하기|결제진행|결제완료|송금하기|이체하기|간편결제|"
            r"pay\s*now|payment|checkout|transfer\s*now)",
            re.IGNORECASE,
        ),
    ),
    (
        ActionCategory.PURCHASE,
        re.compile(
            r"(구매하기|구매확정|주문하기|주문완료|바로\s*구매|buy\s*now|place\s*order)",
            re.IGNORECASE,
        ),
    ),
    (
        ActionCategory.BOOKING_CONFIRM,
        re.compile(
            r"(예약\s*확정|예약하기|예약완료|reserve\s*now|confirm\s*booking|book\s*now)",
            re.IGNORECASE,
        ),
    ),
    (
        ActionCategory.MESSAGE_SEND,
        re.compile(r"(메시지\s*전송|보내기|전송하기|send\s*message|보내다)", re.IGNORECASE),
    ),
    (
        ActionCategory.SIGNUP,
        re.compile(
            r"(회원\s*가입|가입하기|계정\s*만들기|sign\s*up|create\s*account|register)",
            re.IGNORECASE,
        ),
    ),
    (
        ActionCategory.CAPTCHA_BYPASS,
        re.compile(r"(captcha|recaptcha|hcaptcha|자동입력\s*방지)", re.IGNORECASE),
    ),
    # LOGIN은 가장 넓은 어휘를 갖는다 — 좁은 카테고리를 먼저 매칭해 오분류를 줄인다.
    (
        ActionCategory.LOGIN,
        re.compile(r"(로그인|아이디\s*로\s*로그인|log\s*in|sign\s*in)", re.IGNORECASE),
    ),
)

#: 개인정보 입력 필드의 `name`/`autocomplete`/`inputmode` 신호. 텍스트가 없어도 걸린다.
_FORBIDDEN_INPUT_TYPES: frozenset[str] = frozenset({"password"})
_FORBIDDEN_AUTOCOMPLETE: frozenset[str] = frozenset(
    {
        "current-password",
        "new-password",
        "one-time-code",
        "cc-number",
        "cc-csc",
        "cc-exp",
    }
)
_PERSONAL_DATA_FIELD_NAME = re.compile(
    r"(주민등록번호|주민번호|resident.?reg|ssn|social.?security|생년월일.*본인|passport.?no)",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class ActionRisk:
    blocked: bool
    category: str | None
    reason: str | None


def classify_candidate(candidate: dict[str, Any]) -> ActionRisk:
    """activation 후보 하나를 검사한다. 클릭하기 **전에** 호출해야 의미가 있다."""
    input_type = str(candidate.get("input_type") or candidate.get("type") or "").strip().lower()
    autocomplete = str(candidate.get("autocomplete") or "").strip().lower()
    field_name = str(candidate.get("name") or candidate.get("field_name") or "")

    if input_type in _FORBIDDEN_INPUT_TYPES:
        return ActionRisk(True, ActionCategory.CREDENTIAL_FIELD, f"input[type={input_type!r}]")
    if autocomplete in _FORBIDDEN_AUTOCOMPLETE:
        return ActionRisk(True, ActionCategory.CREDENTIAL_FIELD, f"autocomplete={autocomplete!r}")
    if field_name and _PERSONAL_DATA_FIELD_NAME.search(field_name):
        return ActionRisk(True, ActionCategory.PERSONAL_DATA_ENTRY, f"field name={field_name!r}")

    text = " ".join(
        str(v)
        for v in (
            candidate.get("accessible_name"),
            candidate.get("visible_text"),
            candidate.get("aria_label"),
        )
        if v
    ).strip()
    if text:
        for category, pattern in _FORBIDDEN_TEXT_PATTERNS:
            if pattern.search(text):
                return ActionRisk(True, category, f"matched text: {text!r}")

    return ActionRisk(False, None, None)


def assert_no_forbidden_action(candidate: dict[str, Any]) -> None:
    """`classify_candidate`가 차단이면 예외를 던진다. 통과하면 아무것도 하지 않는다."""
    risk = classify_candidate(candidate)
    if risk.blocked:
        raise AccountActionBlockedError(
            f"금지된 계정 행동 후보 감지 — category={risk.category} reason={risk.reason}. "
            "activation을 시도하지 않고 중단한다 (E001 러너 계정 행동 금지 가드)."
        )


def screen_candidates(candidates: list[dict[str, Any]]) -> ActionRisk | None:
    """후보 목록 전체를 검사한다. 하나라도 걸리면 그 위험을 돌려준다 (없으면 `None`).

    `batch.py`는 이 함수가 `None`이 아닌 값을 돌려주면 `Scout`를 아예 호출하지
    않는다 — 위험한 후보가 목록에 **존재**하기만 해도 이 target의 L1 activation
    자체를 건너뛴다. "가장 area가 큰 후보만 검사"하지 않는 이유는, Scout의
    branching_limit(기본 4)가 검사하지 않은 후보를 나중에 클릭할 수 있기 때문이다.
    """
    for candidate in candidates:
        risk = classify_candidate(candidate)
        if risk.blocked:
            return risk
    return None


__all__ = [
    "AccountActionBlockedError",
    "ActionCategory",
    "ActionRisk",
    "assert_no_forbidden_action",
    "classify_candidate",
    "screen_candidates",
]
