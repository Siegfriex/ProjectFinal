"""gate **종류** 판별 — Q-9 (오케스트레이터 P1) 대응.

## 왜 필요한가

`A2 §1.5.1a` 는 `00 §3` 원문대로 gate 를 갈랐다.

| archetype | endpoint 인 gate | endpoint 가 **아닌** gate |
|---|---|---|
| `FINANCIAL_ACTION_ENTRY` | 로그인 · 본인인증 | 결제 · CAPTCHA · 차단 |
| `COMMUNICATION_ENTRY` | **로그인만** | **본인인증** · 결제 · CAPTCHA · 차단 |
| 나머지 5종 | 없음 | 전부 |

그런데 관측된 gate 가 로그인인지 본인인증인지 **판별하는 규칙이 어디에도 없었다.**
규칙이 없으면 커뮤니티 gate 가 전부 미승격이 되어 `A2` 가 풀려던 문제가 되살아난다.
이 모듈이 그 공백을 **fixture 기반으로** 메운다.

## 이 모듈이 하지 않는 것

- **새 상태값을 만들지 않는다.** 산출은 `GateKind`(A2 §1.5.1a 가 전제하는 종류) 와
  판별 상태 `RESOLVED` / `UNDETERMINED` 뿐이며, 후자는 `verdict_state` 의 `UNDETERMINED`
  와 같은 뜻 — *이 자료로는 확정할 수 없다* — 을 gate 판별 축에 적용한 것이다.
- **강제분류를 하지 않는다.** 신호가 양쪽에 걸리거나 어느 쪽에도 안 걸리면 `UNDETERMINED` 다.
  억지로 한쪽에 넣지 않는다 (`00 §6` abstain 경로 · `02 §10` 자유 라벨 생성 금지).
- **`endpoint_status` 를 정하지 않는다.** 그 매핑의 정본은 `A2 §1.5.1a` 규칙 E-5~E-10 이며
  `depth.gate_outcome` 이 그 표를 그대로 구현한다.
- **실제 서비스를 관찰하지 않는다.** 신호 사전은 fixture 안에서만 검증된다
  (`PHASE_GATES §4.5` — 실제 로그인/인증 화면 접속은 P0 finding 이다).

## 판별 불가일 때 endpoint 로 올리지 않는 이유

`A2 §1.5.1a`: *codebook 이 가르지 못한 gate 는 `endpoint_definition` 미충족으로 보아
endpoint 로 승격시키지 않는다 — 모호할 때 endpoint 로 올리는 방향의 기본값을 두지 않는다.*
그 방향이 `00 §3` 확대이기 때문이다. `FINANCIAL_ACTION_ENTRY` 에서는 두 종류가 **모두**
endpoint 이므로 "둘 중 하나임이 확실하면 승격해도 안전하다"는 반론이 가능하지만,
`UNDETERMINED` 는 *둘 중 하나임이 확실하다*는 뜻이 아니라 *무엇인지 모른다*는 뜻이다.
그래서 archetype 을 가리지 않고 보수적으로 비-endpoint(`AUTH_GATE_REACHED`) 로 남긴다.

## 신호 사전의 지위

아래 어휘·필드 조합은 한국 모바일웹에서 **일반적으로 알려진 구성**을 옮긴 것이며
특정 서비스의 실측이 아니다. `[추정]` 표시가 붙은 항목은 실관측 대조가 필요한 가설이다.
**신호 사전의 서비스별 적용은 P-A endpoint codebook 이 동결한다** (`A2 §1.9` 규칙 P-1) —
이 모듈은 그 codebook 이 들어올 자리와 검증 경로를 먼저 만들어 둔 것이다.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from .vocabulary import GateKind


class GateClassificationStatus(StrEnum):
    """판별의 상태. `A2` 어휘의 `UNDETERMINED` 의미를 gate 판별 축에 적용한 것이다."""

    RESOLVED = "RESOLVED"
    UNDETERMINED = "UNDETERMINED"


class GateEvidenceError(ValueError):
    """기록된 gate 종류가 관측 신호와 모순된다 — 오판 기록 시도."""


# ── 로그인 gate 신호 ──────────────────────────────────────────────────────────
#: 자격증명 입력. `<input type=password>` 는 브라우저가 직접 알려주는 결정적 신호다.
_LOGIN_STRUCTURAL = ("password_input_count", "username_autocomplete_count")
_LOGIN_TEXT = re.compile(
    r"(로그인|아이디\s*찾기|비밀번호\s*찾기|비밀번호|회원가입|자동\s*로그인|"
    r"sign\s?in|log\s?in|sign\s?up)",
    re.IGNORECASE,
)

# ── 본인인증 gate 신호 ────────────────────────────────────────────────────────
#: 통신사 선택. 한국 휴대폰 본인확인의 표준 단계다.
_CARRIER_TEXT = re.compile(r"(SKT|KT\b|LG\s?U\+?|LGU\+|알뜰폰|통신사)", re.IGNORECASE)
#: 간편인증 제공자. `[추정]` — 제공자 목록은 서비스마다 다르므로 P-A codebook 이 동결한다.
_SIMPLE_AUTH_TEXT = re.compile(
    r"(PASS\s*앱|카카오\s*인증|네이버\s*인증|토스\s*인증|삼성\s*패스|KB\s*모바일|페이코\s*인증|간편\s*인증)",
    re.IGNORECASE,
)
_IDENTITY_TEXT = re.compile(
    r"(본인\s*인증|본인\s*확인|휴대폰\s*인증|휴대폰\s*본인확인|실명\s*확인|"
    r"주민등록번호|인증번호|내국인|외국인|생년월일)",
    re.IGNORECASE,
)
_IDENTITY_STRUCTURAL = ("tel_autocomplete_count", "identity_number_input_count", "otp_input_count")


@dataclass(frozen=True)
class GateSignals:
    """판별에 쓰이는 관측 신호. **전부 DOM/AX 에서 결정적으로 얻는다.**"""

    text: str = ""
    password_input_count: int = 0
    username_autocomplete_count: int = 0
    tel_autocomplete_count: int = 0
    identity_number_input_count: int = 0
    otp_input_count: int = 0
    carrier_option_count: int = 0
    simple_auth_provider_count: int = 0
    #: 존재 카운트일 뿐이다 — **terminal 판정에 쓰지 않는다** (`D-R0-05`, `C-BLOCKER-221347`
    #: 시정). raw feature 로만 남긴다. 아래 `captcha_challenge_active` 가 실제 판정을 한다.
    captcha_iframe_count: int = 0
    payment_input_count: int = 0
    #: `C-BLOCKER-221347`(P1) · `D-R0-65` 확정 — dialog/aria-modal 소속 + captcha 입력 또는
    #: 이미지 + viewport 가시성을 **전부** 만족하는 candidate 가 있는가. `D-R0-05` 원문의
    #: "visible/active challenge 가 실제로 나타난 순간"을 구조 신호로 옮긴 것이다.
    #: 숨겨진 iframe 만 있는 경우(`captcha_iframe_count>0` 이어도)는 여기 포함되지 않는다.
    captcha_challenge_active: bool = False

    @classmethod
    def from_raw(cls, raw: dict[str, Any]) -> GateSignals:
        gate = raw.get("gate_signals", {}) or {}
        challenge_candidates = raw.get("captcha_challenge_candidates", []) or []
        challenge_active = any(
            c.get("visible") and (c.get("viewport_overlap_css_px2") or 0) > 0
            for c in challenge_candidates
        )
        return cls(
            text=str(gate.get("visible_text") or ""),
            password_input_count=int(gate.get("password_input_count") or 0),
            username_autocomplete_count=int(gate.get("username_autocomplete_count") or 0),
            tel_autocomplete_count=int(gate.get("tel_autocomplete_count") or 0),
            identity_number_input_count=int(gate.get("identity_number_input_count") or 0),
            otp_input_count=int(gate.get("otp_input_count") or 0),
            carrier_option_count=int(gate.get("carrier_option_count") or 0),
            simple_auth_provider_count=int(gate.get("simple_auth_provider_count") or 0),
            captcha_iframe_count=int(gate.get("captcha_iframe_count") or 0),
            payment_input_count=int(gate.get("payment_input_count") or 0),
            captcha_challenge_active=bool(challenge_active),
        )


@dataclass(frozen=True)
class GateKindDecision:
    """판별 결과. `basis` 에 **무엇을 근거로 갈랐는지**를 남긴다 — 사후 검증이 가능해야 한다."""

    status: GateClassificationStatus
    gate_kind: GateKind | None
    login_basis: list[str] = field(default_factory=list)
    identity_basis: list[str] = field(default_factory=list)
    reason: str = ""

    @property
    def resolved(self) -> bool:
        return self.status is GateClassificationStatus.RESOLVED

    def as_dict(self) -> dict[str, Any]:
        return {
            "gate_kind_status": self.status.value,
            "gate_kind": self.gate_kind.value if self.gate_kind else None,
            "login_basis": list(self.login_basis),
            "identity_basis": list(self.identity_basis),
            "reason": self.reason,
        }


def _login_basis(s: GateSignals) -> list[str]:
    basis: list[str] = []
    if s.password_input_count:
        basis.append(f"password_input×{s.password_input_count}")
    if s.username_autocomplete_count:
        basis.append(f"autocomplete=username×{s.username_autocomplete_count}")
    if _LOGIN_TEXT.search(s.text):
        basis.append("login_vocabulary")
    return basis


def _identity_basis(s: GateSignals) -> list[str]:
    basis: list[str] = []
    if s.carrier_option_count:
        basis.append(f"carrier_option×{s.carrier_option_count}")
    if s.simple_auth_provider_count:
        basis.append(f"simple_auth_provider×{s.simple_auth_provider_count}")
    if s.identity_number_input_count:
        basis.append(f"identity_number_input×{s.identity_number_input_count}")
    if s.otp_input_count:
        basis.append(f"otp_input×{s.otp_input_count}")
    if s.tel_autocomplete_count:
        basis.append(f"autocomplete=tel×{s.tel_autocomplete_count}")
    if _CARRIER_TEXT.search(s.text):
        basis.append("carrier_vocabulary")
    if _SIMPLE_AUTH_TEXT.search(s.text):
        basis.append("simple_auth_vocabulary")
    if _IDENTITY_TEXT.search(s.text):
        basis.append("identity_vocabulary")
    return basis


#: 판별을 확정하기 위해 요구하는 최소 근거 수.
#: 어휘 하나만으로 가르지 않는다 — 로그인 화면에도 `본인확인` 링크가 있을 수 있다.
MIN_BASIS_FOR_RESOLVE = 2


def classify_gate_kind(signals: GateSignals) -> GateKindDecision:
    """관측 신호만으로 gate 종류를 가른다. **모호하면 `UNDETERMINED` 다.**

    판별 순서는 결정적 신호 → 어휘 신호이며 (`02 §1` 수집 우선순위),
    어느 단계에서도 `00 §3` 에 없는 새 gate 종류를 만들지 않는다.
    """
    # `C-BLOCKER-221347`(P1) · `D-R0-65`(`T-A-W2-CAPTCHA-001`) 확정 시정 — `captcha_iframe_count`(존재 카운트)
    # 단독으로는 더 이상 RESOLVED 를 내지 않는다. 숨겨진/비활성 iframe 이 있다는 사실만으로
    # terminal 로 승격하면 `D-R0-05`("DOM 내 코드·문구 존재만으로 terminal 아님")를 위반한다
    # — 커머스 랜딩에 흔한 passive reCAPTCHA 가 0-step CAPTCHA terminal 로 오판되고, 반대로
    # iframe 없이 visible dialog 로만 뜨는 실제 challenge 는 미검출로 빠졌다(C 의 양·음성
    # 대조 픽스처로 확인). `captcha_challenge_active`(dialog/aria-modal + captcha 입력 또는
    # 이미지 + viewport 가시성)가 실제 관측 근거다.
    if signals.captcha_challenge_active:
        return GateKindDecision(
            GateClassificationStatus.RESOLVED,
            GateKind.CAPTCHA,
            reason="visible_active_challenge(dialog_or_aria_modal+captcha_input_or_image+viewport_visible)",
        )
    if signals.payment_input_count:
        return GateKindDecision(
            GateClassificationStatus.RESOLVED, GateKind.PAYMENT, reason="payment_input"
        )

    login = _login_basis(signals)
    identity = _identity_basis(signals)

    # 비밀번호 입력은 본인인증 화면에 나타나지 않는 결정적 로그인 신호다.
    # 다만 본인인증 신호가 **동시에** 강하면 한 화면에 두 절차가 섞인 것이므로 확정하지 않는다.
    if signals.password_input_count and len(identity) < MIN_BASIS_FOR_RESOLVE:
        return GateKindDecision(
            GateClassificationStatus.RESOLVED,
            GateKind.LOGIN,
            login_basis=login,
            identity_basis=identity,
            reason="password_input 은 로그인 gate 의 결정적 신호다",
        )

    strong_identity = len(identity) >= MIN_BASIS_FOR_RESOLVE
    strong_login = len(login) >= MIN_BASIS_FOR_RESOLVE

    if strong_identity and not strong_login:
        return GateKindDecision(
            GateClassificationStatus.RESOLVED,
            GateKind.IDENTITY_VERIFICATION,
            login_basis=login,
            identity_basis=identity,
            reason=f"본인인증 신호 {len(identity)}종, 로그인 신호 {len(login)}종",
        )
    if strong_login and not strong_identity:
        return GateKindDecision(
            GateClassificationStatus.RESOLVED,
            GateKind.LOGIN,
            login_basis=login,
            identity_basis=identity,
            reason=f"로그인 신호 {len(login)}종, 본인인증 신호 {len(identity)}종",
        )
    if not login and not identity:
        return GateKindDecision(
            GateClassificationStatus.UNDETERMINED,
            None,
            reason="gate 로 볼 신호가 없다",
        )
    return GateKindDecision(
        GateClassificationStatus.UNDETERMINED,
        None,
        login_basis=login,
        identity_basis=identity,
        reason=(
            "두 종류의 신호가 함께 관측되거나 어느 쪽도 충분하지 않다 — "
            "강제분류하지 않는다. 이 gate 는 endpoint 로 승격되지 않으며 "
            "판별기준의 서비스별 적용은 P-A endpoint codebook 이 동결한다 (A2 §1.5.1a)"
        ),
    )


def assert_gate_kind_evidence(recorded: GateKind, signals: GateSignals) -> None:
    """기록된 gate 종류가 관측 신호와 **모순되지 않는지** 확인한다.

    Q-9 가 지목한 오판의 결과는 조용하다 — 커뮤니티의 본인인증 gate 를 로그인으로 오판하면
    `A2` 의 규칙 E-6a 는 그 값을 **정당한 것으로 통과시킨다.** 규칙만으로는 잡히지 않으므로
    "그 종류라고 부를 근거가 실제로 관측됐는가" 를 따로 검사한다.
    `fact_task_step.auth_gate_detected` 와 evidence 로 사후 검증 가능해야 한다는
    `A2 §1.5.1a` 의 요구를 이 함수가 이행한다.
    """
    decision = classify_gate_kind(signals)
    if decision.resolved and decision.gate_kind is not recorded:
        raise GateEvidenceError(
            f"gate 종류 오판: 기록 {recorded.value} / 관측 신호가 가리키는 값 "
            f"{decision.gate_kind.value if decision.gate_kind else None}. "
            f"로그인 근거={decision.login_basis} 본인인증 근거={decision.identity_basis}. "
            "커뮤니티에서 본인인증 gate 를 로그인으로 오판하면 없어야 할 "
            "ENDPOINT_VIA_AUTH_GATE 가 생긴다 (A2 §1.5.1a 규칙 E-6a)"
        )
    if not decision.resolved and recorded in (GateKind.LOGIN, GateKind.IDENTITY_VERIFICATION):
        raise GateEvidenceError(
            f"gate 종류를 확정하지 못했는데 {recorded.value} 로 기록했다. "
            f"사유: {decision.reason}. 모호할 때 한쪽으로 넣는 기본값을 두지 않는다"
        )
