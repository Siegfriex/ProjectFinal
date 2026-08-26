"""L1 Scout — 최소 경로 발견 (SSOT 02 §7). 자유로운 full task 수행이 아니라
activation 단위 탐색이고, 정해진 terminal 신호가 나오면 즉시 멈춘다.

로컬 픽스처 다중 페이지 사이트(진짜 ``<a href>``/``<button>`` 로 연결된 정적
HTML 묶음)를 실제 Playwright 로 클릭해 나가며 NED/IED 를 센다. endpoint
후보 랭킹은 진짜 embedding 유사도가 아니라 결정론적 키워드 겹침으로 대체한다
— 이 fixture 레인이 검증해야 하는 것은 "탐색 메커니즘이 동작하는가"이지
실서비스 후보 순위의 정확도가 아니다. 운영 배치 시 ``_rank_candidates`` 만
embedding 기반으로 교체하면 된다 (SSOT 02 §6).
"""

from __future__ import annotations

import contextlib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from playwright.sync_api import sync_playwright

from .execution_mode import enforce_real_target_firewall
from .gate import GateEvidence, detect_gate
from .probe_eval import extract_probe

TERMINAL_SIGNALS = frozenset(
    {
        "FUNCTION_ENDPOINT_REACHED",
        "AUTH_GATE_REACHED",
        "PAYMENT_GATE_REACHED",
        "PERSONAL_DATA_REQUIRED",
        "CAPTCHA",
        "BLOCKED",
        "UNRESOLVED",
    }
)

_GATE_TO_TERMINAL = {
    "LOGIN_REQUIRED": "AUTH_GATE_REACHED",
    "IDENTITY_VERIFICATION_REQUIRED": "AUTH_GATE_REACHED",
    "PAYMENT_REQUIRED": "PAYMENT_GATE_REACHED",
    "PERSONAL_DATA_REQUIRED": "PERSONAL_DATA_REQUIRED",
    "CAPTCHA_REQUIRED": "CAPTCHA",
}

_DISMISS_SELECTOR = '[aria-label*="close" i], [aria-label*="닫기"], .close, .dismiss'
_TEXT_INPUT_TAGS = frozenset({"input", "textarea"})
_MAX_DISMISS_ATTEMPTS = 2
_MAX_TEXT_INPUT_ATTEMPTS = 1  # 같은 입력창을 무한히 다시 채우지 않는다 (무한루프 방지)


@dataclass
class Activation:
    step: int
    kind: str  # "click_link" | "click_button" — popup dismiss 는 별도 카운트한다 (02 §9)
    accessible_name: str | None
    url_before: str
    url_after: str | None


@dataclass
class ScoutTrace:
    entry_url: str
    execution_mode: str
    activations: list[Activation] = field(default_factory=list)
    forced_dismissal_count: int = 0
    text_input_episode_count: int = 0
    scroll_episode_count: int = 0
    ned: int | None = None
    ied: int | None = None
    terminal_signal: str = "UNRESOLVED"
    # detect_gate() 의 원본 tag(LOGIN_REQUIRED/IDENTITY_VERIFICATION_REQUIRED/...) —
    # terminal_signal 은 SSOT 02 §7 어휘로 뭉뚱그려지므로(둘 다 AUTH_GATE_REACHED),
    # LOGIN_GATE 와 IDENTITY/AUTH_GATE 를 구분해서 봐야 할 때는 이 필드를 쓴다.
    gate_tag: str | None = None
    endpoint_url: str | None = None
    notes: list[str] = field(default_factory=list)


def _rank_candidates(probe: dict, endpoint_keywords: list[str]) -> list[dict]:
    els = [e for e in (probe.get("interactive_elements") or []) if e.get("visible")]

    def score(e: dict) -> int:
        name = (e.get("accessible_name") or "").lower()
        return sum(1 for k in endpoint_keywords if k.lower() in name)

    ranked = sorted(els, key=score, reverse=True)
    scored = [e for e in ranked if score(e) > 0]
    return scored or ranked


def _gate_terminal(probe: dict, final_url: str, http_status: int | None) -> tuple[str | None, str]:
    ev = GateEvidence(
        final_url_path=urlparse(final_url).path,
        page_title=probe.get("page_title", ""),
        http_status=http_status,
        has_password_input=bool(probe.get("has_password_input")),
        form_actions=list(probe.get("form_actions") or []),
        landmark_text=probe.get("landmark_text", ""),
    )
    sig = detect_gate(ev)
    return _GATE_TO_TERMINAL.get(sig.tag), sig.tag


def run_scout(
    *,
    entry_fixture: Path,
    endpoint_keywords: list[str],
    region_marker_keywords: list[str] | None = None,
    max_steps: int = 8,
    execution_mode: str = "FIXTURE",
) -> ScoutTrace:
    # REAL-TARGET FIREWALL — 다른 어떤 副수효과보다 먼저 검사한다.
    enforce_real_target_firewall(execution_mode)

    entry_url = entry_fixture.resolve().as_uri()
    trace = ScoutTrace(entry_url=entry_url, execution_mode=execution_mode)
    region_marker_keywords = region_marker_keywords or []

    with sync_playwright() as p:
        browser = p.chromium.launch(args=["--no-sandbox", "--disable-dev-shm-usage"])
        context = browser.new_context(viewport={"width": 390, "height": 844}, locale="ko-KR")
        page = context.new_page()
        try:
            resp = page.goto(entry_url, wait_until="load", timeout=15000)
            entered_region = False
            dismiss_attempts = 0
            text_input_attempts = 0
            scrolled_once_without_progress = False
            step = 0
            while step < max_steps:
                step += 1
                probe: dict[str, Any] = extract_probe(page)
                http_status = resp.status if resp else None

                terminal, gate_tag = _gate_terminal(probe, page.url, http_status)
                if terminal:
                    trace.terminal_signal = terminal
                    trace.gate_tag = gate_tag
                    trace.endpoint_url = page.url
                    break

                if not entered_region and region_marker_keywords:
                    hay = f"{probe.get('page_title', '')} {probe.get('landmark_text', '')}".lower()
                    if any(k.lower() in hay for k in region_marker_keywords):
                        entered_region = True
                        trace.ned = len(trace.activations)

                overlay = probe.get("overlay_candidates") or []
                if any(ov.get("dismiss_control_present") for ov in overlay):
                    if dismiss_attempts >= _MAX_DISMISS_ATTEMPTS:
                        # "modal dismissal failure" 실패주입: 계속 닫히지 않는 overlay 를
                        # 무한 재시도하지 않는다 — BLOCKED 로 상태를 남기고 멈춘다.
                        trace.terminal_signal = "BLOCKED"
                        trace.notes.append(
                            f"step={step}: dismiss_attempts={dismiss_attempts} 초과 — "
                            "MODAL_DISMISSAL_FAILURE"
                        )
                        break
                    dismiss_attempts += 1
                    with contextlib.suppress(Exception):
                        page.locator(_DISMISS_SELECTOR).first.click(timeout=2000)
                    with contextlib.suppress(Exception):
                        page.wait_for_timeout(200)
                    # dismiss_success 는 실제로 재확인한다 — 클릭이 "성공했다"고
                    # 가정하지 않는다 (Pilot 류 결함: 시도=성공 취급).
                    reprobe = extract_probe(page)
                    still_present = any(
                        ov.get("dismiss_control_present")
                        for ov in (reprobe.get("overlay_candidates") or [])
                    )
                    if still_present:
                        trace.notes.append(f"step={step}: dismiss 시도 {dismiss_attempts} 실패")
                        continue  # 재시도 — step 예산에서는 면제(아래서 되돌림)
                    trace.forced_dismissal_count += 1
                    step -= 1  # popup dismiss 는 activation 이 아니다 (02 §9) — step 예산에서 면제
                    continue

                if probe.get("is_function_endpoint"):
                    trace.terminal_signal = "FUNCTION_ENDPOINT_REACHED"
                    trace.endpoint_url = page.url
                    if trace.ned is None:
                        trace.ned = len(trace.activations)
                    trace.ied = len(trace.activations) - trace.ned
                    break

                candidates = _rank_candidates(probe, endpoint_keywords)

                # 텍스트 입력 episode: 후보가 text input 이면 채우기만 하고
                # activation 으로 세지 않는다 (02 §9 제외 목록) — 별도 카운터로만 남긴다.
                # 같은 입력창을 무한히 다시 채우지 않도록 시도 횟수를 상한한다.
                if (
                    candidates
                    and candidates[0].get("tag") in _TEXT_INPUT_TAGS
                    and text_input_attempts < _MAX_TEXT_INPUT_ATTEMPTS
                ):
                    text_input_attempts += 1
                    filled = False
                    with contextlib.suppress(Exception):
                        page.locator("input:not([type=password]), textarea").first.fill(
                            "합성 테스트 검색어"
                        )
                        filled = True
                    if filled:
                        trace.text_input_episode_count += 1
                        step -= 1  # 텍스트 입력 자체는 activation 이 아니다
                        continue

                # 입력창 채우기 시도가 끝났다면(또는 애초에 대상이 아니라면) 클릭 후보에서는
                # text input 을 제외한다 — 채워진 입력창을 클릭해도 activation 으로서
                # 의미가 없다(제출 컨트롤을 대신 찾아야 한다).
                clickable = [c for c in candidates if c.get("tag") not in _TEXT_INPUT_TAGS]
                candidates = clickable if clickable else candidates

                if not candidates:
                    page_h = probe.get("page_scroll_height") or 0
                    viewport_h = (probe.get("viewport") or {}).get("height") or 0
                    if (
                        not scrolled_once_without_progress
                        and viewport_h
                        and page_h > viewport_h * 1.2
                    ):
                        with contextlib.suppress(Exception):
                            page.mouse.wheel(0, viewport_h)
                        trace.scroll_episode_count += 1
                        scrolled_once_without_progress = True
                        step -= 1  # scroll 은 activation 이 아니다 (02 §9)
                        continue
                    trace.terminal_signal = "UNRESOLVED"
                    trace.notes.append(f"step={step}: 클릭 가능한 후보 없음")
                    break

                target = candidates[0]
                url_before = page.url
                name = target.get("accessible_name")
                clicked = False
                if name:
                    with contextlib.suppress(Exception):
                        page.locator(f"text={name}").first.click(timeout=3000)
                        clicked = True
                if not clicked:
                    trace.terminal_signal = "BLOCKED"
                    trace.notes.append(f"step={step}: 후보 클릭 실패 {target}")
                    break
                with contextlib.suppress(Exception):
                    page.wait_for_load_state("load", timeout=5000)
                scrolled_once_without_progress = False
                trace.activations.append(
                    Activation(
                        step=step,
                        kind="click_link" if target.get("tag") == "a" else "click_button",
                        accessible_name=name,
                        url_before=url_before,
                        url_after=page.url,
                    )
                )
            else:
                trace.terminal_signal = "UNRESOLVED"
                trace.notes.append("max_steps 도달")
        finally:
            with contextlib.suppress(Exception):
                context.close()
                browser.close()

    if trace.ned is None:
        trace.ned = len(trace.activations)
    if trace.ied is None:
        trace.ied = 0
    return trace
