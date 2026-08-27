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
from enum import StrEnum
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


# ══════════════════════════════════════════════════════════════════════════
# candidate/state-level guard — `T-A-W1-001` §1 (D-R0-01~06)
# ══════════════════════════════════════════════════════════════════════════
#
# 위 `screen_candidates`는 남겨 두되(기존 호출부·테스트 호환), 실행기(`executor.py`
# `real_executor.py`)는 이제 아래 `assess_reachable_candidates`를 쓴다. 차이:
#
#   기존 screen_candidates   후보 목록 아무 데서나 하나 걸리면 그 target 전체를 죽인다
#                            (target-level kill, `D-R0-01`이 폐기하라고 명시한 그것).
#   assess_reachable_candidates  Scout가 실제로 클릭을 시도할 가능성이 있는 후보
#                            (hittable·랜딩 상태 첫 BFS 레벨 순위 안)만 판정 대상으로
#                            좁히고, 그중 안전한 대안이 하나라도 있으면 막지 않는다.
#
# 왜 이게 전부가 아닌지(정직하게 밝힌다 — `D-R0-17`):
#
#   `l1_engine.Scout`는 W1 소유가 아니다(읽기전용, W2 소유). Scout의 `_activate()`는
#   BFS로 열거한 후보를 그대로 클릭한다 — 이 모듈이 후보 하나만 골라 "이건 클릭하지
#   마라"고 Scout에게 전달할 훅이 코드에 없다. 그래서 이 모듈이 실제로 할 수 있는
#   것은 "Scout를 아예 만들지 말지"(launch 여부)뿐이고, 그 판단은 **랜딩 상태(첫 BFS
#   레벨)의 재현된 후보 집합**으로만 내려진다. depth 2 이상에서 새로 나타나는 후보는
#   이 pre-flight 판정 밖이다 — Scout 자신의 구조적 안전장치(비-QUERY 후보는 채우지
#   않고 클릭만 함, gate 관측 즉시 확장 중단)가 그 나머지를 떠받친다.


class CandidateActionState(StrEnum):
    """SSOT `§7.5` / `R0_RECOVERY_CONTRACT_v2.1.md D-R0-02`의 9-state 닫힌 집합.

    새 상태를 추가하지 않는다 — 이 집합 밖의 값이 필요해지면 그건 이 모듈이 아니라
    계약(A) 이 먼저 바뀌어야 한다는 신호다.
    """

    SAFE = "SAFE"
    AUTH_ENTRY_ALLOWED_CONDITIONALLY = "AUTH_ENTRY_ALLOWED_CONDITIONALLY"
    FORBIDDEN_CREDENTIAL_INPUT = "FORBIDDEN_CREDENTIAL_INPUT"
    FORBIDDEN_TRANSACTION = "FORBIDDEN_TRANSACTION"
    FORBIDDEN_PERSONAL_DATA = "FORBIDDEN_PERSONAL_DATA"
    FORBIDDEN_CAPTCHA_BYPASS = "FORBIDDEN_CAPTCHA_BYPASS"
    DISABLED_OR_INERT = "DISABLED_OR_INERT"
    BLOCKED_BY_OVERLAY = "BLOCKED_BY_OVERLAY"
    UNKNOWN = "UNKNOWN"


#: 클릭이 곧 금지행동 그 자체가 되는 상태 — reachable 후보가 전부 이 안에만 있으면
#: (즉 안전한 대안이 하나도 없으면) Scout를 만들지 않는다.
_HARD_FORBIDDEN_STATES: frozenset[CandidateActionState] = frozenset(
    {
        CandidateActionState.FORBIDDEN_CREDENTIAL_INPUT,
        CandidateActionState.FORBIDDEN_TRANSACTION,
        CandidateActionState.FORBIDDEN_PERSONAL_DATA,
        CandidateActionState.FORBIDDEN_CAPTCHA_BYPASS,
    }
)

#: `classify_candidate`의 `ActionCategory` → 9-state 매핑.
#:
#: `LOGIN`은 항상 `AUTH_ENTRY_ALLOWED_CONDITIONALLY`다 — "조건부"의 조건(archetype +
#: chosen path가 실제로 도달했는가, `D-R0-04`)은 이 모듈의 책임이 아니다.
#: `engine.depth.gate_outcome_from_decision`(`ENDPOINT_GATE_KINDS`, W2 소유·읽기전용)이
#: 이미 그 조건을 구현한다 — 이 모듈이 같은 결정을 archetype 인자로 다시 내리면
#: 두 판정이 갈릴 위험만 늘어난다. 이 모듈이 답하는 질문은 딱 하나, "클릭 자체가
#: 안전한가"이며, 로그인 링크를 누르는 것은 `Scout._activate`가 어떤 필드도 채우지
#: 않으므로(QUERY 검색창 제외) 항상 안전하다 — 위험한 것은 그다음 화면에서 자격증명을
#: 입력·제출하는 것인데, 그건 Scout 구조상 애초에 일어나지 않는다(엔진 규칙 E-7).
#:
#: `SIGNUP`은 SSOT 9-state에 전용 자리가 없다. 회원가입 폼 "제출"은 여전히 금지
#: 목록에 있어야 하므로(가드가 다루는 action 리스트를 줄이지 않는다, 계약 §1 말미)
#: 결제·구매·예약확정과 같은 성격 — 클릭이 곧 계정 상태를 소비하는 종류 — 로 묶어
#: `FORBIDDEN_TRANSACTION`에 넣는다. **이건 SSOT 문서가 명시한 매핑이 아니라 이
#: 모듈의 모델링 결정이다** — A/C 검토에서 재논의될 수 있다.
_CATEGORY_TO_STATE: dict[str, CandidateActionState] = {
    ActionCategory.LOGIN: CandidateActionState.AUTH_ENTRY_ALLOWED_CONDITIONALLY,
    ActionCategory.CREDENTIAL_FIELD: CandidateActionState.FORBIDDEN_CREDENTIAL_INPUT,
    ActionCategory.OTP_ENTRY: CandidateActionState.FORBIDDEN_CREDENTIAL_INPUT,
    ActionCategory.PAYMENT: CandidateActionState.FORBIDDEN_TRANSACTION,
    ActionCategory.PURCHASE: CandidateActionState.FORBIDDEN_TRANSACTION,
    ActionCategory.BOOKING_CONFIRM: CandidateActionState.FORBIDDEN_TRANSACTION,
    ActionCategory.MESSAGE_SEND: CandidateActionState.FORBIDDEN_TRANSACTION,
    ActionCategory.SIGNUP: CandidateActionState.FORBIDDEN_TRANSACTION,
    ActionCategory.PERSONAL_DATA_ENTRY: CandidateActionState.FORBIDDEN_PERSONAL_DATA,
    ActionCategory.CAPTCHA_BYPASS: CandidateActionState.FORBIDDEN_CAPTCHA_BYPASS,
}


def classify_candidate_state(candidate: dict[str, Any]) -> CandidateActionState:
    """후보 하나를 9-state 마스크로 판정한다.

    `D-R0-05` (CAPTCHA): DOM에 코드·문구가 있다는 사실만으로 terminal이 아니다 —
    이 후보가 `hittable`(현재 상태에서 다른 요소에 가려지지 않고 실제로 눌릴 수
    있음)일 때만 "active challenge"로 본다. `primary_action_candidates`는 probe가
    이미 `visible` 요소만 담아 만들므로(`l0_probe.js`), 여기서는 `hittable`만 더
    본다 — `hittable=False`(가려짐/비활성)면 CAPTCHA든 아니든 `DISABLED_OR_INERT`다.
    """
    if not isinstance(candidate, dict):
        return CandidateActionState.UNKNOWN
    if candidate.get("hittable") is False:
        return CandidateActionState.DISABLED_OR_INERT
    if candidate.get("blocked_by_overlay") is True or candidate.get("occluded") is True:
        return CandidateActionState.BLOCKED_BY_OVERLAY

    risk = classify_candidate(candidate)
    if risk.blocked and risk.category is not None:
        return _CATEGORY_TO_STATE.get(risk.category, CandidateActionState.UNKNOWN)

    has_identity = any(
        candidate.get(k)
        for k in (
            "accessible_name",
            "visible_text",
            "aria_label",
            "selector",
            "input_type",
            "autocomplete",
        )
    )
    return CandidateActionState.SAFE if has_identity else CandidateActionState.UNKNOWN


def _reachable_candidates(
    candidates: list[dict[str, Any]], *, branching_limit: int
) -> list[dict[str, Any]]:
    """`l1_engine.Scout._activation_candidates`가 **랜딩 상태에서** 분기시킬 후보와
    같은 부분집합을 재현한다 — 같은 정렬 키(`min4_sort_key`), 같은 상한
    (`branching_limit`). Scout 자체를 부르지 않는다(브라우저가 필요하다) — 정렬·
    선별 **규칙만** 재사용한다(`l0_collector.min4_sort_key`는 공개 함수라 import는
    읽기전용 원칙을 어기지 않는다 — 그 파일을 수정하지 않는다).

    Scout의 `_activation_candidates`는 dismiss control selector도 제외하지만, 이
    함수는 L0 관측 하나(`primary_action_candidates`만)만 받으므로 그 제외를 재현하지
    않는다 — 안내문(닫기 버튼)이 텍스트 사전에 걸릴 일은 사실상 없고, 최악의 경우
    top-N 구성이 약간 달라질 뿐이다(과소하게 보수적으로 판정하는 방향으로만 어긋난다).
    """
    from landing_accessibility.engine.l0_collector import min4_sort_key

    reachable = [
        c for c in candidates if isinstance(c, dict) and c.get("hittable") and c.get("selector")
    ]
    reachable.sort(key=min4_sort_key)
    seen: set[str] = set()
    out: list[dict[str, Any]] = []
    for c in reachable:
        sel = str(c["selector"])
        if sel in seen:
            continue
        seen.add(sel)
        out.append(c)
        if len(out) >= branching_limit:
            break
    return out


@dataclass(frozen=True)
class CandidateAssessment:
    """target 하나의 reachable 후보 전체에 대한 판정 — target-kill 대신 이걸 evidence로
    남긴다(`D-R0-03` "존재와 행동을 구분": 위험 후보의 **존재**는 여기 기록되고,
    **활성화**만 막힌다)."""

    states: tuple[tuple[dict[str, Any], CandidateActionState], ...]
    reachable_considered: int
    blocking: ActionRisk | None

    def as_dict(self) -> dict[str, Any]:
        return {
            "reachable_considered": self.reachable_considered,
            "candidates": [
                {
                    "selector": c.get("selector"),
                    "text": c.get("accessible_name")
                    or c.get("visible_text")
                    or c.get("aria_label"),
                    "state": state.value,
                }
                for c, state in self.states
            ],
            "blocking": (
                {"category": self.blocking.category, "reason": self.blocking.reason}
                if self.blocking is not None
                else None
            ),
        }


def assess_reachable_candidates(
    candidates: list[dict[str, Any]], *, branching_limit: int = 4
) -> CandidateAssessment:
    """`D-R0-01` — target-level kill을 candidate/state-level 판정으로 대체한다.

    판정 규칙:

    - reachable 후보 중 하나라도 `SAFE` 이거나 `AUTH_ENTRY_ALLOWED_CONDITIONALLY`면
      (Scout가 고를 수 있는 안전한 대안이 있으면) **막지 않는다.** 위험한 후보가
      같은 목록에 있어도 evidence로만 남긴다(`D-R0-03`·`D-R0-06`: 구매/결제 control의
      "존재 관측"은 허용, "활성화"만 금지 — 안전한 대안이 있는데 목록에 위험 후보가
      섞여 있다는 이유만으로 target 전체를 죽이는 것은 D-R0-06이 금지하는 바로 그
      "존재=활성화" 혼동이다).
    - reachable 후보 **전부**가 hard-forbidden이면(안전한 대안이 전혀 없으면) 막는다
      — 이 경우 Scout를 만들어도 첫 분기에서 금지 행동만 고를 수 있기 때문이다.

    이 함수가 검증하지 못하는 것은 모듈 docstring 상단에 그대로 적어 두었다
    (`D-R0-17`).

    `states`(evidence로 남는 전체 판정)는 **reachable 부분집합에 한정하지
    않는다** — `DISABLED_OR_INERT`(hittable=False라 reachable 필터에서 애초에
    빠지는 후보)·branching_limit 밖 후보도 여기 포함된다(C 의 W1 completion
    감사 지적: 이 두 상태가 batch detail 에 전혀 노출되지 않아 채점 불가능했다).
    **판정(blocking) 자체는 여전히 reachable 부분집합만 쓴다** — 가시성을
    넓히는 것과 차단 범위를 넓히는 것은 다른 일이다.
    """
    reachable = _reachable_candidates(candidates, branching_limit=branching_limit)
    reachable_selectors = {str(c.get("selector")) for c in reachable}

    seen: set[str] = set()
    states: list[tuple[dict[str, Any], CandidateActionState]] = []
    for c in candidates:
        if not isinstance(c, dict):
            continue
        sel = str(c.get("selector") or "")
        if not sel or sel in seen:
            continue
        seen.add(sel)
        states.append((c, classify_candidate_state(c)))

    reachable_states = [(c, s) for c, s in states if str(c.get("selector")) in reachable_selectors]

    has_safe_alternative = any(
        s in (CandidateActionState.SAFE, CandidateActionState.AUTH_ENTRY_ALLOWED_CONDITIONALLY)
        for _, s in reachable_states
    )
    blocking: ActionRisk | None = None
    if not has_safe_alternative:
        forbidden = [(c, s) for c, s in reachable_states if s in _HARD_FORBIDDEN_STATES]
        if forbidden:
            c, s = forbidden[0]
            risk = classify_candidate(c)
            blocking = ActionRisk(
                True,
                risk.category,
                f"reachable 후보 {len(reachable)}개 전부가 forbidden 이다 "
                f"(state={s.value}) — 안전한 대안 없음: {risk.reason}",
            )
    return CandidateAssessment(
        states=tuple(states), reachable_considered=len(reachable), blocking=blocking
    )


__all__ = [
    "AccountActionBlockedError",
    "ActionCategory",
    "ActionRisk",
    "CandidateActionState",
    "CandidateAssessment",
    "assert_no_forbidden_action",
    "assess_reachable_candidates",
    "classify_candidate",
    "classify_candidate_state",
    "screen_candidates",
]
