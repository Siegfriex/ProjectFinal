"""gate(LOGIN/AUTH/PAYMENT/...) 감지 — 다중 신호 + 감사 가능한 근거 기록.

닫는 결함(Pilot 감사 gate-detection-false-negative, MEDIUM):
    ``research/refcohort/src/refcohort/probe.js:344-351`` 의 gate_signal 은
    ``input[type=password]`` 존재와 ``bodyText`` 전체에 대한 정규식뿐이었다.

    - 미탐: ``learn.scau.ac.kr`` -> ``/MobileWeb/Login`` 리다이렉트로
      ``<title>로그인</title>`` 페이지를 수집했는데 password input 이 없어
      ``gated_boundary_tag='NONE'`` 으로 기록되고 criteria_fail=5 가 그
      로그인 페이지의 결과로 계상됐다.
    - 오탐: ``payment_keyword`` 정규식이 ``bodyText`` 전체에 걸려 푸터의
      "결제 안내" 링크 텍스트만으로 ``PAYMENT_REQUIRED`` 가 됐다(r1에서 6건).

    여기서는 (a) 최종 URL 경로 패턴 (b) 페이지 제목 (c) form action
    (d) HTTP 상태 (e) landmark/form 주변으로 **한정한** 텍스트 매칭을 신호로
    쓰고, 어느 신호가 발동했는지를 ``GateSignal.fired_signals`` 에 남긴다.
    ``landmark_text`` 는 L0 collector 가 ``<main>``/``<form>``/``[role=dialog]``
    근처에서만 뽑아 채운다 — 본문 전체(footer 포함)를 절대 넣지 않는 것이
    오탐을 막는 핵심이다.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

GATE_TAGS = frozenset(
    {
        "NONE",
        "LOGIN_REQUIRED",
        "IDENTITY_VERIFICATION_REQUIRED",
        "PAYMENT_REQUIRED",
        "PERSONAL_DATA_REQUIRED",
        "CAPTCHA_REQUIRED",
        "OTHER",
    }
)

_LOGIN_PATH_RE = re.compile(r"/(login|signin|sign-in|auth)(/|$|\?)", re.IGNORECASE)
_LOGIN_TITLE_RE = re.compile(r"(로그인|login|sign\s*in)", re.IGNORECASE)
_CAPTCHA_RE = re.compile(r"(captcha|자동입력\s*방지)", re.IGNORECASE)
_PAYMENT_RE = re.compile(r"(결제하기|카드번호\s*입력|checkout|payment\s*form)", re.IGNORECASE)
_IDENTITY_RE = re.compile(
    r"(본인\s*인증|휴대폰\s*인증|아이핀|identity\s*verification)", re.IGNORECASE
)
_PERSONAL_DATA_RE = re.compile(r"(주민등록번호|개인정보\s*(수집|입력)\s*동의)", re.IGNORECASE)


@dataclass
class GateEvidence:
    """L0 collector 가 채워야 하는 최소 신호 집합.

    ``landmark_text`` 는 반드시 주요 landmark(main/form/dialog) 주변으로
    한정한다 — body 전체를 넣으면 오탐 재발이다.
    """

    final_url_path: str = ""
    page_title: str = ""
    http_status: int | None = None
    has_password_input: bool = False
    form_actions: list[str] = field(default_factory=list)
    landmark_text: str = ""


@dataclass
class GateSignal:
    tag: str
    fired_signals: list[str] = field(default_factory=list)


def detect_gate(ev: GateEvidence) -> GateSignal:
    fired: list[str] = []

    if ev.http_status in (401, 403):
        fired.append(f"http_status={ev.http_status}")
        return GateSignal(tag="LOGIN_REQUIRED", fired_signals=fired)

    if _CAPTCHA_RE.search(ev.landmark_text) or _CAPTCHA_RE.search(ev.page_title):
        fired.append("captcha_text")
        return GateSignal(tag="CAPTCHA_REQUIRED", fired_signals=fired)

    login_path = bool(_LOGIN_PATH_RE.search(ev.final_url_path))
    login_title = bool(_LOGIN_TITLE_RE.search(ev.page_title))
    login_form_action = any(_LOGIN_PATH_RE.search(a) for a in ev.form_actions)
    if login_path:
        fired.append(f"final_url_path={ev.final_url_path}")
    if login_title:
        fired.append(f"page_title={ev.page_title}")
    if login_form_action:
        fired.append("form_action_matches_login_path")
    if ev.has_password_input:
        fired.append("password_input_present")

    # URL 경로 또는 제목이 로그인을 가리키면 password input 없이도 확정한다
    # (refcohort 미탐 사례를 닫는다).
    if login_path or login_title or login_form_action:
        return GateSignal(tag="LOGIN_REQUIRED", fired_signals=fired)
    # password input 단독으로는 확정하지 않는다 (검색창 옆 로그인 위젯 오탐 방지).
    # 근처 landmark 텍스트에 '로그인'류 문구가 있어야 같이 확정한다.
    if ev.has_password_input and _LOGIN_TITLE_RE.search(ev.landmark_text):
        fired.append("password_input+landmark_login_text")
        return GateSignal(tag="LOGIN_REQUIRED", fired_signals=fired)

    if _IDENTITY_RE.search(ev.landmark_text):
        fired.append("identity_text_in_landmark")
        return GateSignal(tag="IDENTITY_VERIFICATION_REQUIRED", fired_signals=fired)
    if _PAYMENT_RE.search(ev.landmark_text):
        fired.append("payment_text_in_landmark")
        return GateSignal(tag="PAYMENT_REQUIRED", fired_signals=fired)
    if _PERSONAL_DATA_RE.search(ev.landmark_text):
        fired.append("personal_data_text_in_landmark")
        return GateSignal(tag="PERSONAL_DATA_REQUIRED", fired_signals=fired)

    return GateSignal(tag="NONE", fired_signals=fired)
