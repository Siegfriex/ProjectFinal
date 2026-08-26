"""Path Freeze / Deterministic Replay — SSOT 02 §8.

``Scout -> Freeze -> Replay``. 본수집은 VLM 이 매번 사이트를 다시 탐색하지
않고 frozen task manifest 를 결정론적으로 재실행한다. **replay 가 깨지면
상태를 기록하고, 조용히 자유탐색으로 대체하지 않는다** — 그 대체 자체가
하나의 결함 유형이다(감사 불가능한 경로 전환).
"""

from __future__ import annotations

import contextlib
import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path

from playwright.sync_api import sync_playwright

from .execution_mode import enforce_real_target_firewall
from .probe_eval import extract_probe
from .scout import ScoutTrace


@dataclass
class FrozenStep:
    step: int
    kind: str
    accessible_name: str | None


@dataclass
class TaskManifest:
    entry_url: str
    steps: list[FrozenStep]
    expected_terminal_signal: str
    expected_endpoint_url: str | None
    protocol_sha: str

    def to_json(self) -> dict:
        return {
            "entry_url": self.entry_url,
            "steps": [asdict(s) for s in self.steps],
            "expected_terminal_signal": self.expected_terminal_signal,
            "expected_endpoint_url": self.expected_endpoint_url,
            "protocol_sha": self.protocol_sha,
        }


FREEZABLE_TERMINALS = frozenset({"FUNCTION_ENDPOINT_REACHED"})


def freeze_path(trace: ScoutTrace) -> TaskManifest:
    if trace.terminal_signal not in FREEZABLE_TERMINALS:
        raise ValueError(
            f"terminal_signal={trace.terminal_signal!r} 인 경로는 freeze 하지 않는다 "
            f"(freeze 대상: {sorted(FREEZABLE_TERMINALS)})"
        )
    steps = [
        FrozenStep(step=a.step, kind=a.kind, accessible_name=a.accessible_name)
        for a in trace.activations
    ]
    basis = json.dumps(
        {"entry": trace.entry_url, "steps": [asdict(s) for s in steps]},
        sort_keys=True,
        ensure_ascii=False,
    )
    protocol_sha = hashlib.sha256(basis.encode("utf-8")).hexdigest()
    return TaskManifest(
        entry_url=trace.entry_url,
        steps=steps,
        expected_terminal_signal=trace.terminal_signal,
        expected_endpoint_url=trace.endpoint_url,
        protocol_sha=protocol_sha,
    )


@dataclass
class ReplayResult:
    status: str  # "REPLAY_OK" | "REPLAY_BROKEN"
    reached_terminal_signal: str | None
    final_url: str | None
    broken_at_step: int | None = None
    detail: str | None = None


def replay_path(
    manifest: TaskManifest,
    *,
    entry_fixture: Path | None = None,
    execution_mode: str = "FIXTURE",
) -> ReplayResult:
    """frozen manifest 를 결정론적으로 재실행한다.

    실패하면 ``REPLAY_BROKEN`` 을 반환한다 — 예외를 삼키고 자유탐색으로
    조용히 대체하지 않는다. 이것이 SSOT 02 §8 의 핵심 요구다.
    """
    # REAL-TARGET FIREWALL — 다른 어떤 副수효과보다 먼저 검사한다.
    enforce_real_target_firewall(execution_mode)

    entry_url = entry_fixture.resolve().as_uri() if entry_fixture else manifest.entry_url

    with sync_playwright() as p:
        browser = p.chromium.launch(args=["--no-sandbox", "--disable-dev-shm-usage"])
        context = browser.new_context(viewport={"width": 390, "height": 844}, locale="ko-KR")
        page = context.new_page()
        try:
            page.goto(entry_url, wait_until="load", timeout=15000)
            for s in manifest.steps:
                if not s.accessible_name:
                    return ReplayResult(
                        status="REPLAY_BROKEN",
                        reached_terminal_signal=None,
                        final_url=page.url,
                        broken_at_step=s.step,
                        detail="frozen step 에 accessible_name 없음 — replay selector 불가",
                    )
                try:
                    page.locator(f"text={s.accessible_name}").first.click(timeout=3000)
                    page.wait_for_load_state("load", timeout=5000)
                except Exception as e:
                    return ReplayResult(
                        status="REPLAY_BROKEN",
                        reached_terminal_signal=None,
                        final_url=page.url,
                        broken_at_step=s.step,
                        detail=f"{type(e).__name__}: {e}",
                    )

            probe = extract_probe(page)
            reached = "FUNCTION_ENDPOINT_REACHED" if probe.get("is_function_endpoint") else None
            final_url = page.url
        finally:
            with contextlib.suppress(Exception):
                context.close()
                browser.close()

    if reached != manifest.expected_terminal_signal:
        return ReplayResult(
            status="REPLAY_BROKEN",
            reached_terminal_signal=reached,
            final_url=final_url,
            detail="replay 종점이 freeze 시점과 다르다",
        )
    return ReplayResult(status="REPLAY_OK", reached_terminal_signal=reached, final_url=final_url)
