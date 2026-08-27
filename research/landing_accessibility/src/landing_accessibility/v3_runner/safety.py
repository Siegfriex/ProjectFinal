"""v3 B-Safety lane — 계약 기반 forbidden action 강제 · auth 경계 · exactly-once
launch 억제 · fixture safety 회귀 하네스 (`W5G`).

## 이 모듈이 **새로 만들지 않는 것**

`e001_runner.guard`(읽기전용 재사용)가 이미 갖고 있는 것을 다시 만들지 않는다:

- `ActionCategory` / `_FORBIDDEN_TEXT_PATTERNS` — 텍스트·input type·autocomplete 기반 탐지
- `classify_candidate` / `classify_candidate_state` — 9-state 마스크, `hittable is False`
  또는 `enabled is False` → `DISABLED_OR_INERT`
- `assess_reachable_candidates` — reachable 후보 전부가 forbidden/inert 일 때의 target-level 판정
- `ActionRisk.blocking_state` — 차단 근거 provenance

이 모듈은 그 위에 **v3 계약 층**을 얹는다. v3 가 e001 과 다른 지점은 셋이다.

1. **금지 집합이 target 마다 다르다.** `01_TASK_FAMILY_TARGET_FRAME_v3.0 §2` 의 5 family
   각각이 다른 `forbidden_actions` 를 갖는다(F1 = 자격정보/이체 실행, F2 = 장바구니/구매/
   결제 control 활성화, F3 = 실사용 번호·조회 submit, F4 = 예약/전화/외부앱, F5 = 좌석선택/
   예약/결제). e001 가드는 전역 단일 사전이었다.
2. **강제 시점이 "후보 선정"이 아니라 "실제 누르기 직전"이다.** e001 가드는 Scout 를
   **만들지 말지**만 결정할 수 있었다(그 한계는 `guard.py` docstring 이 스스로 밝힌다 —
   Scout 내부 클릭에 훅이 없다). v3 는 actuation 지점(`Page.click`/`Page.fill`)을 직접
   감싼다 — `GuardedPage`.
3. **존재 관측은 유지한다.** `D-R0-06` · `00_SSOT §6` — 거래 control 은 "존재와 geometry
   만 관측 가능"하다. 그래서 `observe()` 는 절대 막지 않고 evidence 만 만들고,
   `authorize()`/`GuardedPage` 만 막는다. 이 둘을 뭉치면 v3 가 금지하는 "존재=활성화"
   혼동이 그대로 재발한다.

## CAPTCHA

**해결·우회 로직을 어떤 형태로도 만들지 않는다.** 이 모듈이 CAPTCHA 에 대해 하는 일은
(a) 존재를 evidence 로 기록하고 (b) 상호작용 시도를 `SAFETY_STOP` 으로 막는 것뿐이다.
탐지는 `guard.classify_candidate`(`ActionCategory.CAPTCHA_BYPASS`)를 그대로 쓴다.

## `SAFETY_STOP` 의 지위 — 정직하게

`SAFETY_STOP` 은 `04_FLOW_CODEBOOK_v3.0 §4` 의 `endpoint_status` 닫힌 집합
(`REACHED/AUTH_GATE/PUBLIC_WEB_UNOBSERVABLE/APP_REQUIRED/EVIDENCE_DEFECT/BLOCKED/ABSTAIN`)
에 **없다.** E lane 의 scout-status 어휘 고유값이다(`ACTION_TOKEN_COMPATIBILITY_CHECK §5`).
그래서 이 모듈은 `SAFETY_STOP` 을 **safety-layer terminal** 로만 발화하고,
`endpoint_status` 로의 승격은 하지 않는다 — `SAFETY_STOP_ENDPOINT_STATUS_HINT` 는
A 가 확정하기 전까지 **잠정 매핑 힌트**이며 이 모듈이 직접 쓰지 않는다.
새 `endpoint_status` 값을 발명하지 않는다.

## 소유권 경계

- `auth_gate_stage`(`NONE/BEFORE_TASK_DISCOVERY/AFTER_TASK_SELECT/AT_ENDPOINT`) derive 는
  **W5B** 소유다. 이 모듈은 그 값을 만들지 않고, "여기서 멈춰야 하는가 / 무엇을 눌러도
  되는가"라는 안전 질문만 답한다 — `classify_auth_boundary` 는 `auth_unavoidable` 을
  **입력으로 받는다**(자기가 판정하지 않는다).
- terminal 레코드 작성은 **W5D**(`terminal.py`) 소유다. 이 모듈은 `TerminalSink`
  Protocol 로만 내보낸다.
- `TaskContract` 정의는 **W5A**(`contracts.py`) 소유다. 이 모듈은 duck-typing 으로
  읽기만 한다(`forbidden_actions` 와 `forbidden_action_set` 둘 다 허용 —
  `02_DATA_SCHEMA §2` 가 `dim_task_family` 에는 전자, `dim_task_contract` 에는 후자를
  쓴다).
"""

from __future__ import annotations

import re
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import Any, Protocol, runtime_checkable

from ..e001_runner.batch import (
    DEFAULT_MAX_LOCK_ATTEMPTS,
    IdempotencyKey,
    LockState,
    TargetLock,
    _default_lock_dir,
)
from ..e001_runner.guard import (
    AccountActionBlockedError,
    ActionCategory,
    ActionRisk,
    CandidateAssessment,
    assess_reachable_candidates,
    classify_candidate,
    classify_candidate_state,
)

__all__ = [
    "ACTUATION_METHODS",
    "SAFETY_STOP",
    "SAFETY_STOP_ENDPOINT_STATUS_HINT",
    "UNIVERSAL_FORBIDDEN_ACTIONS",
    "ActivationDecision",
    "ActivationSafetyGuard",
    "AuthBoundary",
    "AuthBoundaryDecision",
    "ControlObservation",
    "FixtureCase",
    "FixtureMatrixMissingError",
    "FixtureSafetyReport",
    "ForbiddenAction",
    "ForbiddenActionSet",
    "GuardedPage",
    "LaunchOutcome",
    "LockState",
    "PageLike",
    "RecordingPage",
    "SafetyStop",
    "TaskContractLike",
    "TerminalSink",
    "V3TargetLaunchGuard",
    "classify_auth_boundary",
    "credential_actuation_counts",
    "load_fixture_matrix",
    "planned_action_to_candidate",
    "preflight_reachable_assessment",
    "resolve_forbidden_actions",
    "run_fixture_safety_regression",
    "task_path_requires_auth_stop",
]


# ══════════════════════════════════════════════════════════════════════════
# 1. 어휘
# ══════════════════════════════════════════════════════════════════════════

#: safety-layer terminal. `endpoint_status` 가 **아니다**(모듈 docstring 참조).
SAFETY_STOP = "SAFETY_STOP"

#: `SAFETY_STOP` 을 v3 `endpoint_status` 닫힌 집합으로 접어야 할 때의 **잠정** 후보.
#: 이 모듈은 이 값을 사용하지 않는다 — A 가 확정하기 전까지 기록용 힌트일 뿐이다.
SAFETY_STOP_ENDPOINT_STATUS_HINT = "BLOCKED"


class ForbiddenAction(StrEnum):
    """v3 금지 행위 canonical 어휘.

    `guard.ActionCategory`(탐지 카테고리)와 1:1 이 아니다 — 카테고리는 "무엇을 감지했나",
    이 enum 은 "계약상 어떤 행위가 금지됐나"다. 매핑은 `_CATEGORY_TO_FORBIDDEN`.

    `MESSAGE_SEND`/`SIGNUP_SUBMIT` 은 v3 문서가 명시한 5 family 금지 목록에는 없지만
    `guard.py` 가 이미 막고 있다 — v3 층을 얹으면서 **기존 가드의 적용범위를 줄이지
    않는다**(줄이면 그게 회귀다). `SEAT_SELECT`/`EXTERNAL_APP_LAUNCH` 는 반대로 v3
    F4/F5 가 명시했는데 `guard.py` 어휘에 없어 이 모듈이 **추가로** 탐지한다
    (`_V3_GAP_TEXT_PATTERNS`) — 기존 로직 재구현이 아니라 공백 보충이다.
    """

    CREDENTIAL_INPUT = "CREDENTIAL_INPUT"
    LOGIN_SUBMIT = "LOGIN_SUBMIT"
    OTP_ENTRY = "OTP_ENTRY"
    IDENTITY_VERIFICATION = "IDENTITY_VERIFICATION"
    CAPTCHA_SOLVE = "CAPTCHA_SOLVE"
    FUNDS_TRANSFER = "FUNDS_TRANSFER"
    ADD_TO_CART = "ADD_TO_CART"
    ORDER_PLACE = "ORDER_PLACE"
    PAYMENT = "PAYMENT"
    BOOKING_CONFIRM = "BOOKING_CONFIRM"
    SEAT_SELECT = "SEAT_SELECT"
    PERSONAL_DATA_INPUT = "PERSONAL_DATA_INPUT"
    EXTERNAL_APP_LAUNCH = "EXTERNAL_APP_LAUNCH"
    MESSAGE_SEND = "MESSAGE_SEND"
    SIGNUP_SUBMIT = "SIGNUP_SUBMIT"


#: **전 target 공통 · 계약과 무관하게 금지.** 계약은 여기에 **더할** 수만 있고
#: 뺄 수 없다 — `resolve_forbidden_actions` 가 이 불변식을 강제한다. 계약 파일이
#: 잘못 작성돼도 자격정보 입력이 허용되는 경로가 존재하지 않게 하는 것이 목적이다.
UNIVERSAL_FORBIDDEN_ACTIONS: frozenset[ForbiddenAction] = frozenset(ForbiddenAction)

#: `guard.ActionCategory` → `ForbiddenAction`.
#:
#: `ActionCategory.LOGIN` 은 **여기 없다.** `guard._CATEGORY_TO_STATE` 가 LOGIN 을
#: `AUTH_ENTRY_ALLOWED_CONDITIONALLY` 로 두는 것과 같은 이유이고, `00_SSOT §6` 의
#: "generic login 존재로 중단 금지"(`D3-09`, 이 프로젝트의 `G1-b` 결함)와도 같다.
#: 로그인 **링크를 누르는 것**은 금지가 아니다 — 금지는 자격정보 **입력**과 **제출**이며
#: 그건 `CREDENTIAL_INPUT`/`LOGIN_SUBMIT` 로 따로 잡는다.
#:
#: `ActionCategory.PAYMENT` 는 `guard._FORBIDDEN_TEXT_PATTERNS` 에서 결제와 송금/이체를
#: 한 패턴으로 묶는다 — 따라서 송금 control 도 탐지되고 차단되지만 보고 카테고리는
#: `PAYMENT` 다. `FUNDS_TRANSFER` 는 계약이 명시적으로 선언할 때(F1) 쓰이는 어휘로 남긴다.
_CATEGORY_TO_FORBIDDEN: dict[str, ForbiddenAction] = {
    ActionCategory.CREDENTIAL_FIELD: ForbiddenAction.CREDENTIAL_INPUT,
    ActionCategory.OTP_ENTRY: ForbiddenAction.OTP_ENTRY,
    ActionCategory.PAYMENT: ForbiddenAction.PAYMENT,
    ActionCategory.PURCHASE: ForbiddenAction.ORDER_PLACE,
    ActionCategory.ADD_TO_CART: ForbiddenAction.ADD_TO_CART,
    ActionCategory.BOOKING_CONFIRM: ForbiddenAction.BOOKING_CONFIRM,
    ActionCategory.MESSAGE_SEND: ForbiddenAction.MESSAGE_SEND,
    ActionCategory.SIGNUP: ForbiddenAction.SIGNUP_SUBMIT,
    ActionCategory.PERSONAL_DATA_ENTRY: ForbiddenAction.PERSONAL_DATA_INPUT,
    ActionCategory.CAPTCHA_BYPASS: ForbiddenAction.CAPTCHA_SOLVE,
}

#: `guard._FORBIDDEN_TEXT_PATTERNS` 에 **없는** v3 고유 금지행위만 여기서 탐지한다.
#: 기존 사전과 겹치는 항목을 다시 쓰지 않는다 — 두 사전이 같은 문구를 다르게 인식하면
#: 그 자체가 결함이다(`guard.py` 가 `_COMMERCE_VOCAB` 와의 어휘 일치를 명시한 이유).
#: 순서: 기존 가드가 먼저 판정하고, 그것이 통과시킨 후보에만 이 패턴이 적용된다.
_V3_GAP_TEXT_PATTERNS: tuple[tuple[ForbiddenAction, re.Pattern[str]], ...] = (
    (
        # `01 §2` F5 — "좌석선택·예약·결제 금지".
        ForbiddenAction.SEAT_SELECT,
        re.compile(
            r"(좌석\s*(선택|배치|지정)|select\s*seat|seat\s*(map|selection))", re.IGNORECASE
        ),
    ),
    (
        # `01 §2` F4 — "예약·전화·외부앱 실행 금지". 텍스트 신호.
        ForbiddenAction.EXTERNAL_APP_LAUNCH,
        re.compile(
            r"(앱에서\s*(보기|열기)|앱으로\s*(보기|열기)|앱\s*설치|앱\s*다운로드|"
            r"open\s*in\s*app|install\s*app|get\s*the\s*app)",
            re.IGNORECASE,
        ),
    ),
    (
        # `01 §2` F4 — "전화" 발신도 외부앱(다이얼러) 실행이다.
        ForbiddenAction.EXTERNAL_APP_LAUNCH,
        re.compile(
            r"(전화\s*(걸기|연결|하기)|바로\s*전화|call\s*now|tap\s*to\s*call)", re.IGNORECASE
        ),
    ),
)

#: `press` 의 인자는 텍스트가 아니라 키 이름일 수 있다(`page.press(sel, "Enter")`).
#: 키 이름은 "입력한 값"이 아니므로 fixture 값 검사 대상에서 뺀다 — 단, 대상 필드가
#: 자격정보로 판정되면 키든 텍스트든 여전히 막힌다(그게 login submit 이다).
_KEYBOARD_KEYS: frozenset[str] = frozenset(
    {
        "Enter",
        "Tab",
        "Escape",
        "Space",
        "Backspace",
        "Delete",
        "ArrowUp",
        "ArrowDown",
        "ArrowLeft",
        "ArrowRight",
        "Home",
        "End",
        "PageUp",
        "PageDown",
    }
)

#: 외부앱 실행의 **구조적** 신호 — 텍스트가 없어도 걸린다. `href`/`url` 의 scheme 이
#: http(s) 가 아니면 브라우저를 떠난다. 텍스트 사전보다 훨씬 강한 근거다.
_EXTERNAL_APP_SCHEME = re.compile(
    r"^\s*(intent|market|itms-apps|itms-services|tel|sms|mailto|kakaolink|"
    r"kakaotalk|nidlogin|[a-z][a-z0-9+.-]*app[a-z0-9+.-]*)\s*:",
    re.IGNORECASE,
)

#: `GuardedPage` 가 감싸는 actuation 메서드. `kind` 는 강제 규칙을 가른다:
#: `TEXT` = 값 입력(계약이 허용한 fixture 값만 가능), `PRESS` = 활성화.
ACTUATION_METHODS: dict[str, str] = {
    "click": "PRESS",
    "dblclick": "PRESS",
    "tap": "PRESS",
    "check": "PRESS",
    "select_option": "PRESS",
    "fill": "TEXT",
    "type": "TEXT",
    "press": "TEXT",
    "set_input_files": "TEXT",
}


# ══════════════════════════════════════════════════════════════════════════
# 2. 경계 Protocol — 다른 lane 이 아직 없어도 이 모듈은 테스트 가능하다
# ══════════════════════════════════════════════════════════════════════════


@runtime_checkable
class TaskContractLike(Protocol):
    """W5A `contracts.TaskContract` 의 **읽기 경계**. 속성 존재만 요구한다."""

    task_id: str
    family_id: str


class PageLike(Protocol):
    """actuation 지점만 담은 최소 Protocol — playwright `Page` 가 이걸 만족한다."""

    def click(self, selector: str, **kwargs: Any) -> Any: ...
    def fill(self, selector: str, value: str, **kwargs: Any) -> Any: ...


class TerminalSink(Protocol):
    """W5D `terminal.py` 경계. 이 모듈은 terminal **레코드를 만들지 않고** 통보만 한다."""

    def emit(self, terminal: str, payload: Mapping[str, Any]) -> None: ...


class SafetyStop(AccountActionBlockedError):
    """금지 행위 활성화 시도를 활성화 **직전에** 잡아 즉시 정지했다.

    `AccountActionBlockedError` 를 상속하는 것은 우연이 아니다 —
    `e001_runner.retry._NON_RETRYABLE_EXCEPTIONS` 가 그 타입을 이미 재시도 제외로
    다루므로, 이 예외도 자동으로 재시도되지 않는다. 재시도는 같은 위반을 다시
    시도하는 것일 뿐이다.
    """

    terminal = SAFETY_STOP

    def __init__(
        self,
        *,
        action: ForbiddenAction | str,
        selector: str | None,
        reason: str,
        method: str | None = None,
    ) -> None:
        self.action = action
        self.selector = selector
        self.reason = reason
        self.method = method
        super().__init__(
            f"{SAFETY_STOP}: 금지 행위 활성화 시도 — action={action} "
            f"method={method!r} selector={selector!r} :: {reason}"
        )

    def as_dict(self) -> dict[str, Any]:
        return {
            "terminal": SAFETY_STOP,
            "action": str(self.action),
            "selector": self.selector,
            "method": self.method,
            "reason": self.reason,
        }


# ══════════════════════════════════════════════════════════════════════════
# 3. 계약 → 금지 집합
# ══════════════════════════════════════════════════════════════════════════


@dataclass(frozen=True)
class ForbiddenActionSet:
    """target 하나에 실제로 적용되는 금지 집합.

    `unrecognized` 를 **버리지 않는다.** 계약이 이 모듈이 모르는 토큰을 선언했다면
    그건 "금지가 0건"이 아니라 "판정 불가"다 — 조용히 드롭하면 회귀 하네스의
    "위반 0건"이 무의미해진다(이 프로젝트가 대조군 없는 0건 보고로 여러 번 틀린 형태).
    """

    actions: frozenset[ForbiddenAction]
    contract_declared: frozenset[ForbiddenAction]
    unrecognized: frozenset[str]
    allowed_input_values: frozenset[str]

    def __contains__(self, action: object) -> bool:
        return action in self.actions

    def as_dict(self) -> dict[str, Any]:
        return {
            "actions": sorted(str(a) for a in self.actions),
            "contract_declared": sorted(str(a) for a in self.contract_declared),
            "unrecognized": sorted(self.unrecognized),
            "allowed_input_values": sorted(self.allowed_input_values),
        }


_CONTRACT_FORBIDDEN_KEYS = ("forbidden_actions", "forbidden_action_set")
_CONTRACT_FIXTURE_KEYS = ("fixed_fixture", "fixture_json", "allowed_input_values", "fixture")


def _read_contract_field(contract: Any, keys: Sequence[str]) -> Any:
    if contract is None:
        return None
    for key in keys:
        if isinstance(contract, Mapping):
            if key in contract:
                return contract[key]
        else:
            value = getattr(contract, key, None)
            if value is not None:
                return value
    return None


def _coerce_str_set(value: Any) -> frozenset[str]:
    """문자열/시퀀스/매핑 어느 쪽으로 와도 문자열 집합으로 접는다.

    `fixed_fixture` 는 `01 §2` 에서 자유 텍스트("검색어=생수")이기도 하고
    `02 §2` 의 `fixture_json` 에서는 구조화된 값이기도 하다 — 두 모양을 다 받는다.
    """
    if value is None:
        return frozenset()
    if isinstance(value, str):
        parts = re.split(r"[;\n]", value)
        out: set[str] = set()
        for part in parts:
            part = part.strip()
            if not part:
                continue
            out.add(part.split("=", 1)[1].strip() if "=" in part else part)
        return frozenset(out)
    if isinstance(value, Mapping):
        return frozenset(str(v).strip() for v in value.values() if str(v).strip())
    if isinstance(value, Iterable):
        return frozenset(str(v).strip() for v in value if str(v).strip())
    return frozenset({str(value).strip()})


def resolve_forbidden_actions(contract: Any = None) -> ForbiddenActionSet:
    """계약을 읽어 이 target 에 적용할 금지 집합을 만든다.

    불변식 두 개:

    1. **결과는 항상 `UNIVERSAL_FORBIDDEN_ACTIONS` 를 포함한다.** 계약은 더할 수만
       있다. 계약이 비어 있거나(`None`) 잘못 작성돼도 자격정보 입력·결제·CAPTCHA
       해결이 허용되는 경로는 존재하지 않는다.
    2. **모르는 토큰은 `unrecognized` 로 보존된다.** 드롭하지 않는다.
    """
    declared_raw = _read_contract_field(contract, _CONTRACT_FORBIDDEN_KEYS)
    declared: set[ForbiddenAction] = set()
    unrecognized: set[str] = set()
    for token in _coerce_str_set(declared_raw):
        normalized = token.strip().upper().replace(" ", "_").replace("-", "_")
        try:
            declared.add(ForbiddenAction(normalized))
        except ValueError:
            unrecognized.add(token)
    return ForbiddenActionSet(
        actions=frozenset(UNIVERSAL_FORBIDDEN_ACTIONS | declared),
        contract_declared=frozenset(declared),
        unrecognized=frozenset(unrecognized),
        allowed_input_values=_coerce_str_set(
            _read_contract_field(contract, _CONTRACT_FIXTURE_KEYS)
        ),
    )


# ══════════════════════════════════════════════════════════════════════════
# 4. 후보 판정 — 존재 관측 vs 활성화
# ══════════════════════════════════════════════════════════════════════════


@dataclass(frozen=True)
class ControlObservation:
    """control 하나의 **존재** evidence. 이 객체가 만들어졌다는 것은 차단이 아니라
    관측이다 — `00_SSOT §6` "존재와 geometry 만 관측 가능"의 그 관측이다."""

    selector: str | None
    visible_text: str | None
    accessible_name: str | None
    candidate_state: str
    forbidden_action: ForbiddenAction | None
    hittable: bool | None
    enabled: bool | None
    bbox: Any | None = None

    @property
    def is_forbidden_to_activate(self) -> bool:
        return self.forbidden_action is not None

    def as_dict(self) -> dict[str, Any]:
        return {
            "selector": self.selector,
            "visible_text": self.visible_text,
            "accessible_name": self.accessible_name,
            "candidate_state": self.candidate_state,
            "forbidden_action": (
                str(self.forbidden_action) if self.forbidden_action is not None else None
            ),
            "hittable": self.hittable,
            "enabled": self.enabled,
            "bbox": self.bbox,
            "observed_only": self.forbidden_action is not None,
        }


@dataclass(frozen=True)
class ActivationDecision:
    allowed: bool
    action: ForbiddenAction | None
    reason: str
    observation: ControlObservation

    def as_dict(self) -> dict[str, Any]:
        return {
            "allowed": self.allowed,
            "action": str(self.action) if self.action is not None else None,
            "reason": self.reason,
            "observation": self.observation.as_dict(),
        }


def _text_of(candidate: Mapping[str, Any]) -> str:
    return " ".join(
        str(v)
        for v in (
            candidate.get("accessible_name"),
            candidate.get("visible_text"),
            candidate.get("aria_label"),
            candidate.get("title"),
        )
        if v
    ).strip()


#: login control 이 **제출 control** 임을 알리는 구조 신호. 계약이 아니라 DOM 사실이다.
_LOGIN_SUBMIT_FLAGS = ("in_credential_form", "form_has_credential_field", "is_credential_submit")
_SUBMIT_INPUT_TYPES: frozenset[str] = frozenset({"submit", "image"})


def _is_login_submit(candidate: Mapping[str, Any], *, credential_form_ids: frozenset[str]) -> bool:
    """LOGIN 어휘 control 이 "폼으로 가는 링크"인지 "폼의 제출 버튼"인지 가른다.

    이 구분이 `D3-09`(generic login 존재로 중단 금지)와 "login submit 금지"를 동시에
    지킬 수 있게 하는 유일한 지점이다. **어휘로는 갈리지 않는다** — landing 의 GNB
    "로그인" 링크와 로그인 폼의 "로그인" 제출 버튼은 문구가 같다. 그래서 구조를 본다:

    - 후보가 자격정보 필드와 **같은 form** 안에 있다(`form_id` 일치, 또는 수집기가
      명시한 `in_credential_form`/`form_has_credential_field` 플래그).
    - 또는 `input[type=submit|image]` 다.

    어느 신호도 없으면 제출로 보지 않는다 — **모르면 막지 않는다.** 여기서 과탐하면
    `G1-b`(어휘 존재로 gate 판정)를 다른 옷을 입혀 재발시키는 것이다.
    """
    for flag in _LOGIN_SUBMIT_FLAGS:
        if candidate.get(flag) is True:
            return True
    input_type = str(candidate.get("input_type") or candidate.get("type") or "").strip().lower()
    if input_type in _SUBMIT_INPUT_TYPES:
        return True
    form_id = candidate.get("form_id")
    return bool(form_id) and str(form_id) in credential_form_ids


def _detect_forbidden_action(
    candidate: Mapping[str, Any], *, credential_form_ids: frozenset[str] = frozenset()
) -> tuple[ForbiddenAction | None, str]:
    """후보 하나가 어떤 금지 행위에 해당하는지 판정한다.

    순서가 중요하다 — **기존 `guard.classify_candidate` 가 먼저**다. 그것이 통과시킨
    후보에만 v3 공백 패턴(`_V3_GAP_TEXT_PATTERNS`)과 구조적 scheme 검사를 적용한다.
    같은 문구를 두 사전이 다르게 인식할 여지를 만들지 않기 위해서다.
    """
    risk: ActionRisk = classify_candidate(dict(candidate))
    if risk.blocked and risk.category is not None:
        mapped = _CATEGORY_TO_FORBIDDEN.get(risk.category)
        if mapped is not None:
            return mapped, f"guard.classify_candidate: {risk.reason}"
        if risk.category == ActionCategory.LOGIN and _is_login_submit(
            candidate, credential_form_ids=credential_form_ids
        ):
            return (
                ForbiddenAction.LOGIN_SUBMIT,
                f"자격정보 폼의 제출 control — {risk.reason}",
            )
        # 그 밖의 LOGIN 은 금지가 아니라 조건부 auth entry 다(D3-09).
        return None, f"guard category={risk.category} (활성화 금지 아님)"

    href = str(candidate.get("href") or candidate.get("url") or "")
    if href and _EXTERNAL_APP_SCHEME.search(href):
        return ForbiddenAction.EXTERNAL_APP_LAUNCH, f"non-http scheme href={href!r}"

    text = _text_of(candidate)
    if text:
        for action, pattern in _V3_GAP_TEXT_PATTERNS:
            if pattern.search(text):
                return action, f"v3 gap pattern {action}: {text!r}"
    return None, "no forbidden signal"


#: `runner.PlannedAction` 의 필드명 → 이 모듈의 detector 가 실제로 읽는 candidate 키.
#:
#: **이 표가 SEAM 1 의 하중을 전부 진다.** `_detect_forbidden_action` /
#: `guard.classify_candidate` 는 `visible_text` · `accessible_name` · `selector` 만
#: 읽는다. `dataclasses.asdict(action)` 을 그대로 넘기면 키가 `control_visible_text`
#: 로 들어가 detector 가 **아무것도 못 읽고 전건 허용**한다 — 이름만 맞춘 배선이
#: fail-open 이 되는 정확한 경로가 이것이다. 그래서 번역표를 상수로 꺼내 두고
#: 실물-대-실물 테스트로 차단이 실제로 발화하는지 확인한다 (A 수용기준 3).
_PLANNED_ACTION_FIELD_MAP: tuple[tuple[str, str], ...] = (
    ("control_selector", "selector"),
    ("control_role", "role"),
    ("control_visible_text", "visible_text"),
    ("control_accessible_name", "accessible_name"),
)


def planned_action_to_candidate(action: Any) -> dict[str, Any]:
    """`runner.PlannedAction` 하나를 이 모듈의 candidate mapping 으로 옮긴다.

    `runner.py` 를 import 하지 않는다 — safety 가 runner 를 참조하면 순환이 된다
    (`scout_strategy` → `runner` → … ). duck typing 으로 필드만 읽는다.

    값이 `None` 인 필드는 **키 자체를 넣지 않는다.** `_observe` 가 `"hittable" in
    candidate` 처럼 키 존재를 보는 자리가 있어서, `None` 을 넣으면 "관측했고 없었다"
    로 읽힐 수 있다.
    """
    candidate: dict[str, Any] = {}
    for src, dst in _PLANNED_ACTION_FIELD_MAP:
        value = getattr(action, src, None)
        if value is not None:
            candidate[dst] = value
    token = getattr(action, "action_token", None)
    if token is not None:
        # detector 는 이 키를 읽지 않는다. evidence 추적용 provenance 다.
        candidate["action_token"] = token
    return candidate


def _observe(
    candidate: Mapping[str, Any], *, credential_form_ids: frozenset[str] = frozenset()
) -> ControlObservation:
    action, _ = _detect_forbidden_action(candidate, credential_form_ids=credential_form_ids)
    state = classify_candidate_state(dict(candidate))
    return ControlObservation(
        selector=(str(candidate["selector"]) if candidate.get("selector") else None),
        visible_text=(
            str(candidate["visible_text"]) if candidate.get("visible_text") is not None else None
        ),
        accessible_name=(
            str(candidate["accessible_name"])
            if candidate.get("accessible_name") is not None
            else None
        ),
        candidate_state=state.value,
        forbidden_action=action,
        hittable=candidate.get("hittable") if "hittable" in candidate else None,
        enabled=candidate.get("enabled") if "enabled" in candidate else None,
        bbox=candidate.get("bbox"),
    )


def preflight_reachable_assessment(
    candidates: Sequence[Mapping[str, Any]], *, branching_limit: int = 4
) -> CandidateAssessment:
    """`guard.assess_reachable_candidates` 를 그대로 위임한다 — 재구현하지 않는다.

    v3 에서 이 pre-flight 판정은 `GuardedPage` 를 **대체하지 않는다**. pre-flight 는
    랜딩 상태의 후보 집합만 보고 "탐색을 시작할 가치가 있는가"를 판정하고,
    실제 강제는 actuation 지점에서 일어난다(`guard.py` docstring 이 스스로 밝힌
    pre-flight 의 한계 — depth 2 이상 후보는 판정 밖 — 를 v3 는 `GuardedPage` 로 덮는다).
    """
    return assess_reachable_candidates(
        [dict(c) for c in candidates], branching_limit=branching_limit
    )


# ══════════════════════════════════════════════════════════════════════════
# 5. auth 경계 — `G1-b` 재발 방지
# ══════════════════════════════════════════════════════════════════════════


class AuthBoundary(StrEnum):
    #: login control 이 **존재**한다 — 기록하고 **계속 진행한다.** 중단하지 않는다.
    OBSERVE_ONLY = "OBSERVE_ONLY"
    #: 사전지정 task path 에서 인증이 불가피해진 최초 상태 — 정당한 terminal.
    AUTH_GATE_TERMINAL = "AUTH_GATE_TERMINAL"
    #: 자격정보 입력·제출·본인인증 수행 시도 — 안전 위반.
    SAFETY_STOP = "SAFETY_STOP"


@dataclass(frozen=True)
class AuthBoundaryDecision:
    boundary: AuthBoundary
    reason: str
    action: ForbiddenAction | None = None

    @property
    def should_stop(self) -> bool:
        return self.boundary is not AuthBoundary.OBSERVE_ONLY

    def as_dict(self) -> dict[str, Any]:
        return {
            "boundary": str(self.boundary),
            "reason": self.reason,
            "action": str(self.action) if self.action is not None else None,
            "should_stop": self.should_stop,
        }


def classify_auth_boundary(
    candidate: Mapping[str, Any],
    *,
    on_task_path: bool,
    auth_unavoidable: bool,
) -> AuthBoundaryDecision:
    """auth 관련 control 하나에 대한 **안전 경계** 판정.

    `auth_unavoidable`(사전지정 task path 를 따라가다 인증이 불가피해졌는가)은
    **입력이다** — 이 모듈이 판정하지 않는다. 그 판정과 `auth_gate_stage`
    (`NONE/BEFORE_TASK_DISCOVERY/AFTER_TASK_SELECT/AT_ENDPOINT`) derive 는 W5B 소유다.

    규칙(`00_SSOT §6` · `03 §7` · `D3-09`):

    - 자격정보/OTP/개인정보 필드 → `SAFETY_STOP`. **입력과 제출이 금지다.**
    - 그 밖의 login control 은 `on_task_path and auth_unavoidable` 일 때만
      `AUTH_GATE_TERMINAL`. 그 외에는 항상 `OBSERVE_ONLY` —
      **landing 에 로그인 버튼이 있다는 이유로 중단하지 않는다.** 이 프로젝트가
      실제로 저지른 결함(`G1-b`: 어휘 존재만으로 gate 를 발화시켜 AUTH_GATE
      유병률을 부풀렸다)의 재발 방지 지점이 정확히 이 분기다.
    - **로그인 폼 도달 자체는 gate observation 이지 금지가 아니다** — 폼에 도달한
      상태에서 아무것도 채우지 않고 관측만 하면 `OBSERVE_ONLY` 또는
      `AUTH_GATE_TERMINAL` 이지 `SAFETY_STOP` 이 아니다.
    """
    action, reason = _detect_forbidden_action(candidate)
    if action in (
        ForbiddenAction.CREDENTIAL_INPUT,
        ForbiddenAction.OTP_ENTRY,
        ForbiddenAction.PERSONAL_DATA_INPUT,
        ForbiddenAction.IDENTITY_VERIFICATION,
        ForbiddenAction.LOGIN_SUBMIT,
    ):
        return AuthBoundaryDecision(
            AuthBoundary.SAFETY_STOP,
            f"자격정보/본인인증 계열 control 상호작용 금지 — {reason}",
            action,
        )
    if on_task_path and auth_unavoidable:
        return AuthBoundaryDecision(
            AuthBoundary.AUTH_GATE_TERMINAL,
            "사전지정 task path 에서 인증이 불가피해진 최초 상태 (00_SSOT §6)",
        )
    return AuthBoundaryDecision(
        AuthBoundary.OBSERVE_ONLY,
        "login control 존재는 중단 사유가 아니다 (D3-09 / G1-b 재발 방지)",
    )


def task_path_requires_auth_stop(
    observations: Sequence[ControlObservation | Mapping[str, Any]],
    *,
    auth_unavoidable_on_task_path: bool,
) -> bool:
    """페이지 전체 관측으로부터 "여기서 멈춰야 하는가"를 답한다.

    **login control 이 몇 개 관측됐든 `auth_unavoidable_on_task_path` 가 거짓이면
    항상 `False`다.** 이 함수가 관측 개수를 세지 않는 것이 `G1-b` 방지의 전부다 —
    세는 순간 어휘 유병률이 gate 유병률로 새어 나간다.
    """
    return bool(auth_unavoidable_on_task_path)


# ══════════════════════════════════════════════════════════════════════════
# 6. 활성화 강제 — actuation 지점
# ══════════════════════════════════════════════════════════════════════════


class ActivationSafetyGuard:
    """계약 금지 집합을 **활성화 직전에** 강제한다.

    `observe*` 는 절대 막지 않는다(존재 관측 유지). `evaluate` 는 판정만 하고 예외를
    던지지 않는다. `authorize` 와 `GuardedPage` 만 `SafetyStop` 을 던진다.
    """

    def __init__(
        self,
        contract: Any = None,
        *,
        extra_forbidden: Iterable[ForbiddenAction] = (),
        terminal_sink: TerminalSink | None = None,
    ) -> None:
        base = resolve_forbidden_actions(contract)
        extras = frozenset(extra_forbidden)
        self.contract = contract
        self.forbidden = ForbiddenActionSet(
            actions=frozenset(base.actions | extras),
            contract_declared=frozenset(base.contract_declared | extras),
            unrecognized=base.unrecognized,
            allowed_input_values=base.allowed_input_values,
        )
        self.terminal_sink = terminal_sink
        #: 관측된 control 전부 — 금지·안전 구분 없이 evidence 로 남는다.
        self.observations: list[ControlObservation] = []
        #: 활성화가 실제로 시도돼 막힌 건들.
        self.violations: list[dict[str, Any]] = []
        #: 금지로 관측된 selector — 나중에 selector 만으로 들어오는 actuation 도 막는다.
        self._denied_selectors: dict[str, ForbiddenAction] = {}
        #: selector → candidate. `GuardedPage` 가 selector 를 후보로 되돌릴 때 쓴다.
        self._known: dict[str, dict[str, Any]] = {}
        #: 자격정보 필드가 관측된 form id 들 — 같은 form 의 "로그인" 버튼은 제출이다.
        self._credential_form_ids: set[str] = set()

    # ── 관측 (절대 막지 않는다) ────────────────────────────────────────────
    def observe(self, candidate: Mapping[str, Any]) -> ControlObservation:
        obs = _observe(candidate, credential_form_ids=frozenset(self._credential_form_ids))
        if obs.forbidden_action in (
            ForbiddenAction.CREDENTIAL_INPUT,
            ForbiddenAction.OTP_ENTRY,
        ) and candidate.get("form_id"):
            self._credential_form_ids.add(str(candidate["form_id"]))
        self.observations.append(obs)
        if obs.selector:
            self._known[obs.selector] = dict(candidate)
            if obs.forbidden_action is not None and obs.forbidden_action in self.forbidden:
                self._denied_selectors[obs.selector] = obs.forbidden_action
        return obs

    def observe_all(
        self, candidates: Sequence[Mapping[str, Any]]
    ) -> tuple[ControlObservation, ...]:
        return tuple(self.observe(c) for c in candidates)

    # ── 판정 ──────────────────────────────────────────────────────────────
    def evaluate(self, candidate: Mapping[str, Any]) -> ActivationDecision:
        """활성화해도 되는지 판정한다. **예외를 던지지 않는다.**"""
        form_ids = frozenset(self._credential_form_ids)
        obs = _observe(candidate, credential_form_ids=form_ids)
        action, reason = _detect_forbidden_action(candidate, credential_form_ids=form_ids)
        if action is not None and action in self.forbidden:
            return ActivationDecision(False, action, reason, obs)
        selector = obs.selector
        if selector and selector in self._denied_selectors:
            denied = self._denied_selectors[selector]
            return ActivationDecision(
                False, denied, f"이전 관측에서 {denied} 로 판정된 selector", obs
            )
        return ActivationDecision(True, None, reason, obs)

    def authorize(self, candidate: Mapping[str, Any], *, method: str = "activate") -> None:
        """활성화 직전 관문. 위반이면 `SafetyStop` 을 던지고 terminal 을 통보한다."""
        decision = self.evaluate(candidate)
        self.observations.append(decision.observation)
        if decision.allowed:
            return
        assert decision.action is not None
        self._raise_stop(
            action=decision.action,
            selector=decision.observation.selector,
            reason=decision.reason,
            method=method,
        )

    def _raise_stop(
        self, *, action: ForbiddenAction | str, selector: str | None, reason: str, method: str
    ) -> None:
        stop = SafetyStop(action=action, selector=selector, reason=reason, method=method)
        self.violations.append(stop.as_dict())
        if self.terminal_sink is not None:
            self.terminal_sink.emit(SAFETY_STOP, stop.as_dict())
        raise stop

    # ── runner 배선 (SEAM 1, W5K) ─────────────────────────────────────────
    def assert_action_allowed(self, contract: Any, action: Any) -> None:
        """`runner.SafetyGuard` Protocol 구현. `V3Runner._assert_action_allowed` 가
        activation **직전에** 호출하고, `driver.activate(action)` 은 이 호출이 돌아온
        뒤에만 실행된다.

        **rename 이 아니다.** 이 메서드는 `PlannedAction` 을 detector 가 읽는 키로
        번역해(:func:`planned_action_to_candidate`) 기존 :meth:`authorize` 에 건다 —
        새 판정 로직을 만들지 않는다. 차단은 `SafetyStop` 으로 나가며 이 모듈이
        잡지 않고 runner 도 잡지 않는다(fail-closed). `terminal_sink` 통보와
        `violations` 기록도 `authorize` 경로 그대로 남는다.

        ``contract`` 인자를 쓰지 않는 이유 — 감춘 것이 아니라 측정된 사실이다:
        :data:`UNIVERSAL_FORBIDDEN_ACTIONS` 가 ``frozenset(ForbiddenAction)`` 이라
        :func:`resolve_forbidden_actions` 의 결과는 계약과 무관하게 **항상 전 항목**을
        포함한다. 계약은 더할 수만 있고 뺄 수 없으므로, 호출 시점 계약이 생성 시점
        계약과 달라도 금지 집합이 **줄어드는 경로가 존재하지 않는다.** 계약별로
        갈리는 것은 `allowed_input_values` 뿐이고 그건 `GuardedPage` 의 텍스트 검사
        소관이다. Protocol 시그니처를 지키기 위해 인자는 받아 둔다.

        .. warning::
           **이 관문은 actuation 지점이 아니라 그 앞의 사전 관문이다.** 실제 클릭은
           `SessionDriver`(W5H) 안에서 일어나고, 그 page 가 `guard_page()` 를 통과한
           `GuardedPage` 인지는 이 메서드가 보증하지 못한다. W5G 가 자기 known
           limitation 에 적은 그 구멍은 **여전히 열려 있다** — 좁아졌을 뿐이다.
        """
        self.authorize(
            planned_action_to_candidate(action),
            method=str(getattr(action, "action_token", None) or "activate"),
        )

    # ── actuation 래핑 ────────────────────────────────────────────────────
    def guard_page(
        self,
        page: PageLike,
        *,
        resolve: Callable[[str], Mapping[str, Any] | None] | None = None,
    ) -> GuardedPage:
        return GuardedPage(page, self, resolve=resolve)

    def evidence(self) -> dict[str, Any]:
        return {
            "forbidden_action_set": self.forbidden.as_dict(),
            "observations": [o.as_dict() for o in self.observations],
            "forbidden_controls_observed": [
                o.as_dict() for o in self.observations if o.is_forbidden_to_activate
            ],
            "violations": list(self.violations),
        }


class GuardedPage:
    """playwright `Page` 의 actuation 메서드를 감싸 **누르기 직전에** 강제한다.

    두 규칙:

    1. `PRESS` 계열(`click`/`tap`/…): 대상 control 이 금지 행위로 판정되면 막는다.
       판정 불가(해석되지 않는 selector)면 **통과시킨다** — 임의의 네비게이션 링크를
       누르는 것이 flow 측정의 본체이고, 미상 selector 를 전부 막으면 측정 자체가
       불가능해진다. 이 fail-open 을 메우는 것이 (a) `observe()` 로 채워지는
       selector deny-list 와 (b) selector 문자열 자체의 텍스트 검사다.
    2. `TEXT` 계열(`fill`/`type`/`press`/`set_input_files`): **계약이 허용한 고정
       fixture 값만** 입력할 수 있다(`01 §2` 의 `fixed_fixture`). 값이 그 집합 밖이면
       대상이 무엇이든 막는다. 이것이 "자격정보·실제 개인정보 입력 금지"를 어휘가
       아니라 **구조**로 강제하는 지점이다 — 비밀번호 필드를 못 알아봐도 채울 값이
       없다. 대상 필드가 자격정보로 판정되면 값과 무관하게 추가로 막는다.
    """

    def __init__(
        self,
        page: PageLike,
        guard: ActivationSafetyGuard,
        *,
        resolve: Callable[[str], Mapping[str, Any] | None] | None = None,
    ) -> None:
        self._page = page
        self._guard = guard
        self._resolve = resolve

    # ── 내부 ──────────────────────────────────────────────────────────────
    def _candidate_for(self, selector: str) -> dict[str, Any]:
        if self._resolve is not None:
            resolved = self._resolve(selector)
            if resolved:
                return dict(resolved)
        known = self._guard._known.get(selector)
        if known:
            return dict(known)
        # selector 문자열 자체를 텍스트 신호로 쓴다 — `text=결제하기`,
        # `button:has-text("장바구니")` 같은 selector 는 이것만으로 걸린다.
        return {"selector": selector, "visible_text": selector}

    def _check_press(self, method: str, selector: str) -> None:
        candidate = self._candidate_for(selector)
        decision = self._guard.evaluate(candidate)
        self._guard.observations.append(decision.observation)
        if not decision.allowed:
            assert decision.action is not None
            self._guard._raise_stop(
                action=decision.action,
                selector=selector,
                reason=decision.reason,
                method=method,
            )

    def _check_text(self, method: str, selector: str, value: Any) -> None:
        candidate = self._candidate_for(selector)
        action, reason = _detect_forbidden_action(
            candidate, credential_form_ids=frozenset(self._guard._credential_form_ids)
        )
        if action is not None and action in self._guard.forbidden:
            self._guard._raise_stop(action=action, selector=selector, reason=reason, method=method)
        if selector in self._guard._denied_selectors:
            denied = self._guard._denied_selectors[selector]
            self._guard._raise_stop(
                action=denied,
                selector=selector,
                reason=f"이전 관측에서 {denied} 로 판정된 selector 에 입력 시도",
                method=method,
            )
        text = "" if value is None else str(value)
        if method == "press" and text in _KEYBOARD_KEYS:
            return
        if text and text not in self._guard.forbidden.allowed_input_values:
            self._guard._raise_stop(
                action=ForbiddenAction.PERSONAL_DATA_INPUT,
                selector=selector,
                reason=(
                    f"계약이 고정한 fixture 값이 아닌 텍스트 입력 시도: {text!r} "
                    f"(허용: {sorted(self._guard.forbidden.allowed_input_values)})"
                ),
                method=method,
            )

    def _dispatch(self, method: str, selector: str, *args: Any, **kwargs: Any) -> Any:
        kind = ACTUATION_METHODS[method]
        if kind == "TEXT":
            self._check_text(method, selector, args[0] if args else kwargs.get("value"))
        else:
            self._check_press(method, selector)
        target = getattr(self._page, method, None)
        if target is None:
            raise AttributeError(f"wrapped page 에 {method!r} 가 없다")
        return target(selector, *args, **kwargs)

    # ── 래핑된 actuation ──────────────────────────────────────────────────
    def click(self, selector: str, *args: Any, **kwargs: Any) -> Any:
        return self._dispatch("click", selector, *args, **kwargs)

    def dblclick(self, selector: str, *args: Any, **kwargs: Any) -> Any:
        return self._dispatch("dblclick", selector, *args, **kwargs)

    def tap(self, selector: str, *args: Any, **kwargs: Any) -> Any:
        return self._dispatch("tap", selector, *args, **kwargs)

    def check(self, selector: str, *args: Any, **kwargs: Any) -> Any:
        return self._dispatch("check", selector, *args, **kwargs)

    def select_option(self, selector: str, *args: Any, **kwargs: Any) -> Any:
        return self._dispatch("select_option", selector, *args, **kwargs)

    def fill(self, selector: str, value: str, *args: Any, **kwargs: Any) -> Any:
        return self._dispatch("fill", selector, value, *args, **kwargs)

    def type(self, selector: str, value: str, *args: Any, **kwargs: Any) -> Any:
        return self._dispatch("type", selector, value, *args, **kwargs)

    def press(self, selector: str, value: str, *args: Any, **kwargs: Any) -> Any:
        return self._dispatch("press", selector, value, *args, **kwargs)

    def set_input_files(self, selector: str, value: Any, *args: Any, **kwargs: Any) -> Any:
        return self._dispatch("set_input_files", selector, value, *args, **kwargs)

    def __getattr__(self, name: str) -> Any:
        """감싸지 않은(=상태를 바꾸지 않는) 메서드는 그대로 위임한다.

        actuation 메서드는 위에서 명시적으로 정의돼 있으므로 여기로 오지 않는다 —
        즉 이 위임이 강제를 우회시키지 않는다.
        """
        if name in ACTUATION_METHODS:  # pragma: no cover - 위에서 이미 정의됨
            raise AttributeError(name)
        return getattr(self._page, name)


# ══════════════════════════════════════════════════════════════════════════
# 7. exactly-once — target launch 이전 억제
# ══════════════════════════════════════════════════════════════════════════


@dataclass(frozen=True)
class LaunchOutcome:
    launched: bool
    idempotency_key: str
    lock_path: Path
    attempt_id: str | None = None
    reason: str | None = None
    prior_state: str | None = None
    prior_attempts: int = 0
    result: Any = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "launched": self.launched,
            "idempotency_key": self.idempotency_key,
            "lock_path": str(self.lock_path),
            "attempt_id": self.attempt_id,
            "reason": self.reason,
            "prior_state": self.prior_state,
            "prior_attempts": self.prior_attempts,
        }


class V3TargetLaunchGuard:
    """`e001_runner.batch.TargetLock` 을 v3 target launch 앞에 배선한다.

    락 자체를 다시 만들지 않는다 — `os.open(O_CREAT|O_EXCL)` + `fcntl.flock` 구현과
    `IdempotencyKey`(ticket_id + run_id + target_id + collector_sha + protocol_sha)를
    그대로 재사용한다. 이 클래스가 더하는 것은 **호출 순서의 불변식** 하나다:

        launch_fn 은 lock 획득에 성공했을 때만 호출된다.

    즉 억제는 사후 차단이 아니라 **실제 launch 이전**이다(`00_SSOT §6` · `v3 06 §6`).
    lock 을 삭제하는 코드 경로는 이 클래스에 없다.

    락 디렉터리 기본값은 `e001_runner.batch._default_lock_dir()` 아래 `v3/` 다 —
    private 이름을 일부러 재사용한다. 여기서 경로 계산을 새로 하면(워크트리 보정 포함)
    한 글자만 어긋나도 상호배제가 **조용히** 성립하지 않는다.
    """

    def __init__(
        self,
        *,
        ticket_id: str,
        run_id: str,
        collector_sha: str,
        protocol_sha: str = "v3",
        lock_dir: Path | str | None = None,
        max_attempts: int = DEFAULT_MAX_LOCK_ATTEMPTS,
    ) -> None:
        if not ticket_id or not run_id:
            raise ValueError(
                "ticket_id 와 run_id(수집 회차) 없이는 idempotency key 를 만들 수 없다 — "
                "키 성분이 없는 채로 launch 하지 않는다"
            )
        self.ticket_id = ticket_id
        self.run_id = run_id
        self.collector_sha = collector_sha
        self.protocol_sha = protocol_sha
        self.max_attempts = max_attempts
        resolved = Path(lock_dir) if lock_dir is not None else (_default_lock_dir() / "v3")
        self.lock = TargetLock(resolved)

    def key_for(self, target_id: str) -> IdempotencyKey:
        return IdempotencyKey(
            ticket_id=self.ticket_id,
            run_id=self.run_id,
            target_id=target_id,
            collector_sha=self.collector_sha,
            protocol_sha=self.protocol_sha,
        )

    def launch(
        self, target_id: str, launch_fn: Callable[[str], Any] | None = None
    ) -> LaunchOutcome:
        """lock 을 **먼저** 잡고, 이긴 경우에만 `launch_fn` 을 호출한다."""
        key = self.key_for(target_id)
        decision = self.lock.acquire(key, max_attempts=self.max_attempts)
        if not decision.proceed:
            return LaunchOutcome(
                launched=False,
                idempotency_key=key.canonical(),
                lock_path=decision.lock_path,
                reason=decision.reason,
                prior_state=decision.prior_state,
                prior_attempts=decision.prior_attempts,
            )
        try:
            result = launch_fn(target_id) if launch_fn is not None else None
        except BaseException:
            self.lock.mark_failed_retryable(key)
            raise
        self.lock.mark_done(key)
        return LaunchOutcome(
            launched=True,
            idempotency_key=key.canonical(),
            lock_path=decision.lock_path,
            attempt_id=decision.attempt_id,
            prior_state=decision.prior_state,
            prior_attempts=decision.prior_attempts,
            result=result,
        )

    def mark_failed_retryable(self, target_id: str) -> None:
        self.lock.mark_failed_retryable(self.key_for(target_id))

    def state_of(self, target_id: str) -> str | None:
        import json

        path = self.lock._path(self.key_for(target_id))
        if not path.is_file():
            return None
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):  # pragma: no cover - 방어적
            return None
        state = payload.get("state")
        return str(state) if state is not None else None


# ══════════════════════════════════════════════════════════════════════════
# 8. fixture safety 회귀 하네스
# ══════════════════════════════════════════════════════════════════════════

FIXTURE_MATRIX_FILENAME = "FIXTURE_DISCRIMINATION_MATRIX.json"


def default_v3_fixture_root() -> Path:
    """`research/landing_accessibility/fixtures/v3/` (W5E 소유). 없을 수 있다."""
    return Path(__file__).resolve().parents[3] / "fixtures" / "v3"


class FixtureMatrixMissingError(FileNotFoundError):
    """W5E 의 discrimination matrix 가 아직 없다.

    **이 예외를 삼켜 "위반 0건"으로 보고하지 않는다.** 빈 결과와 통과가 같은 출력으로
    나오면 회귀 하네스는 아무것도 증명하지 않는다.
    """


@dataclass(frozen=True)
class FixtureCase:
    fixture_id: str
    path: Path
    spec: Mapping[str, Any] = field(default_factory=dict)

    @property
    def exists(self) -> bool:
        return self.path.is_file()


_FIXTURE_ID_KEYS = ("fixture_id", "id", "name", "fixture")
_FIXTURE_FILE_KEYS = ("file", "path", "html", "fixture_file", "fixture_path", "fixture")


def _case_from_entry(entry: Mapping[str, Any], root: Path, fallback_id: str | None) -> FixtureCase:
    fixture_id = fallback_id or ""
    for key in _FIXTURE_ID_KEYS:
        value = entry.get(key)
        if isinstance(value, str) and value.strip() and not value.strip().endswith(".html"):
            fixture_id = value.strip()
            break
    filename: str | None = None
    for key in _FIXTURE_FILE_KEYS:
        value = entry.get(key)
        if isinstance(value, str) and value.strip().endswith(".html"):
            filename = value.strip()
            break
    if filename is None:
        filename = f"{fixture_id}.html"
    return FixtureCase(fixture_id=fixture_id or filename[:-5], path=root / filename, spec=entry)


def load_fixture_matrix(root: Path | str | None = None) -> tuple[FixtureCase, ...]:
    """W5E 의 `FIXTURE_DISCRIMINATION_MATRIX.json` 을 읽어 case 목록을 만든다.

    **파일 목록을 하드코딩하지 않는다** — matrix 가 진실이다. matrix 의 정확한 스키마는
    W5E 소유라 아직 확정되지 않았으므로, 흔한 세 모양을 모두 받는다:
    top-level list / `{"fixtures"|"cases"|"matrix": [...]}` / fixture_id 를 키로 갖는 dict.
    """
    import json

    base = Path(root) if root is not None else default_v3_fixture_root()
    matrix_path = base / FIXTURE_MATRIX_FILENAME
    if not matrix_path.is_file():
        raise FixtureMatrixMissingError(
            f"{matrix_path} 가 없다 — W5E 의 fixture matrix 가 아직 도착하지 않았다. "
            "이 상태를 '위반 0건'으로 보고하지 않는다."
        )
    payload = json.loads(matrix_path.read_text(encoding="utf-8"))

    entries: list[tuple[Mapping[str, Any], str | None]] = []
    if isinstance(payload, list):
        entries = [(e, None) for e in payload if isinstance(e, Mapping)]
    elif isinstance(payload, Mapping):
        for container_key in ("fixtures", "cases", "matrix", "rows"):
            container = payload.get(container_key)
            if isinstance(container, list):
                entries = [(e, None) for e in container if isinstance(e, Mapping)]
                break
            if isinstance(container, Mapping):
                entries = [(v, k) for k, v in container.items() if isinstance(v, Mapping)]
                break
        else:
            entries = [
                (v, k)
                for k, v in payload.items()
                if isinstance(v, Mapping) and not k.startswith("_")
            ]
    if not entries:
        raise FixtureMatrixMissingError(
            f"{matrix_path} 를 읽었지만 fixture 항목을 하나도 해석하지 못했다 — "
            "스키마가 예상과 다르다. 조용히 0건으로 넘기지 않는다."
        )
    return tuple(_case_from_entry(e, base, k) for e, k in entries)


class RecordingPage:
    """`PageLike` spy. **실제 브라우저가 아니다** — 네트워크에 붙지 않는다.

    `GuardedPage` 아래에 두면 "실제로 페이지까지 도달한 actuation"만 여기 기록된다.
    금지 행위가 막히면 이 객체의 카운트는 늘지 않는다 — 그것이 증명 대상이다.
    """

    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    def _record(self, method: str, selector: str, value: Any = None) -> None:
        self.calls.append({"method": method, "selector": selector, "value": value})

    def click(self, selector: str, **kwargs: Any) -> None:
        self._record("click", selector)

    def dblclick(self, selector: str, **kwargs: Any) -> None:
        self._record("dblclick", selector)

    def tap(self, selector: str, **kwargs: Any) -> None:
        self._record("tap", selector)

    def check(self, selector: str, **kwargs: Any) -> None:
        self._record("check", selector)

    def select_option(self, selector: str, value: Any = None, **kwargs: Any) -> None:
        self._record("select_option", selector, value)

    def fill(self, selector: str, value: str, **kwargs: Any) -> None:
        self._record("fill", selector, value)

    def type(self, selector: str, value: str, **kwargs: Any) -> None:
        self._record("type", selector, value)

    def press(self, selector: str, value: str, **kwargs: Any) -> None:
        self._record("press", selector, value)

    def set_input_files(self, selector: str, value: Any, **kwargs: Any) -> None:
        self._record("set_input_files", selector, value)

    def count(self, method: str, *, selector_contains: str | None = None) -> int:
        return sum(
            1
            for c in self.calls
            if c["method"] == method
            and (selector_contains is None or selector_contains in str(c["selector"]))
        )


@dataclass(frozen=True)
class FixtureSafetyReport:
    fixture_id: str
    fixture_exists: bool
    forbidden_controls_observed: tuple[dict[str, Any], ...]
    blocked_activations: tuple[dict[str, Any], ...]
    page_calls: tuple[dict[str, Any], ...]
    error: str | None = None

    @property
    def forbidden_actuations_reaching_page(self) -> tuple[dict[str, Any], ...]:
        """**페이지까지 실제로 도달한** 금지 actuation. 여기가 0 이어야 한다."""
        out: list[dict[str, Any]] = []
        for call in self.page_calls:
            candidate = {"selector": call["selector"], "visible_text": call["selector"]}
            action, _ = _detect_forbidden_action(candidate)
            if action is not None:
                out.append({**call, "action": str(action)})
        return tuple(out)

    def as_dict(self) -> dict[str, Any]:
        return {
            "fixture_id": self.fixture_id,
            "fixture_exists": self.fixture_exists,
            "forbidden_controls_observed": list(self.forbidden_controls_observed),
            "blocked_activations": list(self.blocked_activations),
            "page_call_count": len(self.page_calls),
            "forbidden_actuations_reaching_page": list(self.forbidden_actuations_reaching_page),
            "error": self.error,
        }


#: `RecordingPage` 호출 하나가 자격정보 대상인지 판정할 때 쓰는 selector 신호.
_CREDENTIAL_SELECTOR_HINT = re.compile(
    r"(password|passwd|pwd|credential|otp|one[-_]?time|"
    r"login[-_]?(id|user|submit)|userid|user[-_]?id|아이디|비밀번호)",
    re.IGNORECASE,
)


def credential_actuation_counts(page: RecordingPage) -> dict[str, int]:
    """자격정보 대상 `fill`/`click` 이 **페이지까지 도달한 횟수**.

    `login_first_auth` 계열 fixture 에서 이 값이 전부 0 이어야 한다. 0 만 보고하면
    "아무것도 안 한 것"과 구분되지 않으므로 `total_calls` 를 함께 돌려준다 —
    대조군이 되는 값이다(파이프라인이 실제로 무언가는 했다는 증거).
    """
    creds = [c for c in page.calls if _CREDENTIAL_SELECTOR_HINT.search(str(c["selector"]))]
    return {
        "credential_fill": sum(1 for c in creds if c["method"] in ("fill", "type")),
        "credential_click": sum(1 for c in creds if c["method"] in ("click", "tap", "dblclick")),
        "credential_any": len(creds),
        "total_calls": len(page.calls),
    }


def run_fixture_safety_regression(
    cases: Sequence[FixtureCase],
    run_case: Callable[[FixtureCase, ActivationSafetyGuard, GuardedPage, RecordingPage], None],
    *,
    contract_for: Callable[[FixtureCase], Any] | None = None,
) -> tuple[FixtureSafetyReport, ...]:
    """fixture 전건을 안전 파이프라인에 통과시키고 case 별 보고를 만든다.

    `run_case` 가 `SafetyStop` 을 던지면 그건 **정상 동작**이다 — 잡아서
    `blocked_activations` 에 기록하고 다음 case 로 간다. 그 밖의 예외는 `error` 로
    남긴다(삼키지 않는다).
    """
    reports: list[FixtureSafetyReport] = []
    for case in cases:
        guard = ActivationSafetyGuard(contract_for(case) if contract_for else None)
        recorder = RecordingPage()
        guarded = guard.guard_page(recorder)
        error: str | None = None
        try:
            run_case(case, guard, guarded, recorder)
        except SafetyStop:
            pass
        except Exception as exc:  # 삼키지 않고 보고에 남긴다
            error = f"{type(exc).__name__}: {exc}"
        reports.append(
            FixtureSafetyReport(
                fixture_id=case.fixture_id,
                fixture_exists=case.exists,
                forbidden_controls_observed=tuple(
                    o.as_dict() for o in guard.observations if o.is_forbidden_to_activate
                ),
                blocked_activations=tuple(guard.violations),
                page_calls=tuple(recorder.calls),
                error=error,
            )
        )
    return tuple(reports)


# `LockState` 는 `__all__` 로 재수출한다 — 호출부가 lock 상태를 판독할 때 batch 를 다시
# import 하지 않도록. 값 정의는 여전히 `e001_runner.batch` 소유다(이 모듈은 안 만든다).
