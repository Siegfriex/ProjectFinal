"""W4 — `D-R0-42` 이중화 회귀검사: probe 단 marker 게이팅 호출부 배선.

**결함(C 발견, P3)**: `l0_collector.py` 가 `page.evaluate(PROBE_JS)` 를 인자 없이 호출해
`execution_mode === undefined` 가 되고, `l0_probe.js`(W2 소유)의 `REAL_TARGET_MODE` 분기가
`execution_mode === 'REAL_TARGET'` 를 절대 만족하지 못해 **항상 FIXTURE 취급**됐다 —
`D-R0-42` 가 요구한 이중화(engine 단 + probe 단)가 실제로는 engine 단 한 겹뿐이었다.

**시정**: `l0_collector.py:collect()` 가 `page.evaluate(PROBE_JS, self.execution_mode.value)`
로 실제 값을 전달한다. **이 테스트 파일은 `l0_probe.js` 를 수정하지 않는다** — W2 소유다.

## 두 종류의 검증을 섞지 않는다

1. `TestCallSiteWiring` — **이 worktree 의** `l0_collector.py` 가 `page.evaluate` 를 호출할 때
   두 번째 인자로 `self.execution_mode.value` 를 실제로 넘기는지 spy 로 확인한다.
   FIXTURE 모드만 쓴다(안전 — 로컬 fixture 만 열고 네트워크 없음).
2. `TestMarkerGatingBehaviorAgainstW2Probe` — **W2 worktree 의 실제 `l0_probe.js` 원문**을
   읽어(수정하지 않음, 파일로 쓰지도 않음 — 문자열로만 메모리에 로드) 로컬 fixture 위에서
   `execution_mode` 값별로 직접 `page.evaluate` 해 marker 게이팅이 양방향으로 맞는지
   확인한다. `A` 가 CAPTCHA 건에서 지적한 함정("한 방향만 보면 통과하는 구현")을 피하려고
   **REAL_TARGET(읽지 않음)과 FIXTURE(읽음) 양쪽을 다 확인**한다. **REAL_TARGET 네트워크
   접속은 없다** — `file://` fixture 위에서 `execution_mode` 문자열만 바꿔 가며 호출한다.

`W2` worktree 가 이 환경에 없으면(다른 환경에서 이 스위트를 돌리는 경우) 2번은 스킵한다 —
1번(호출부 자체의 배선)은 이 worktree 만으로 항상 검증된다.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any

import pytest

# 이 파일은 <worktree>/research/landing_accessibility/tests/ 아래에 있다.
_THIS_RESEARCH = Path(__file__).resolve().parents[1]
_WORKTREE_ROOT = _THIS_RESEARCH.parents[1]  # <worktree>
sys.path.insert(0, str(_THIS_RESEARCH / "src"))

from landing_accessibility.engine.evidence import EvidenceRun  # noqa: E402
from landing_accessibility.engine.firewall import ExecutionMode  # noqa: E402
from landing_accessibility.engine.l0_collector import (  # noqa: E402
    PROBE_JS,
    FixtureTarget,
    L0Collector,
)
from landing_accessibility.engine.vocabulary import InteractionArchetype as A  # noqa: E402

pytest.importorskip("playwright.sync_api")

FIXTURES = _THIS_RESEARCH / "fixtures"

#: `PROJECT_FINAL_ROOT` 환경변수(세션에 자동 주입됨) 기준으로 W2 worktree 를 찾는다 —
#: 없으면 이 파일 경로에서 유도한다(`.agent_worktrees/claude_b_w4/research/...` → 3단계 위).
_PROJECT_ROOT = Path(os.environ.get("PROJECT_FINAL_ROOT", str(_WORKTREE_ROOT.parents[1])))
W2_PROBE_JS_PATH = (
    _PROJECT_ROOT
    / ".agent_worktrees"
    / "claude_b_w2"
    / "research"
    / "landing_accessibility"
    / "src"
    / "landing_accessibility"
    / "engine"
    / "l0_probe.js"
)


# ══════════════════════════════════════════════════════════════════════════
# 1. 호출부 배선 — 이 worktree 의 l0_collector.py 가 execution_mode 를 실제로 넘기는가
# ══════════════════════════════════════════════════════════════════════════


class TestCallSiteWiring:
    """FIXTURE 모드만 쓴다 — 로컬 fixture 파일만 열고 네트워크 접속이 없다."""

    def test_fixture_mode_passes_its_own_execution_mode_value_to_probe(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        import playwright.sync_api as pw_sync

        calls: list[tuple[str, tuple[Any, ...]]] = []
        original_evaluate = pw_sync.Page.evaluate

        def spy_evaluate(self: Any, script: str, *args: Any, **kwargs: Any) -> Any:
            calls.append((script, args))
            return original_evaluate(self, script, *args, **kwargs)

        monkeypatch.setattr(pw_sync.Page, "evaluate", spy_evaluate)

        run = EvidenceRun.create(tmp_path, "w4-probe-wiring", execution_mode=ExecutionMode.FIXTURE)
        collector = L0Collector(run, fixture_root=FIXTURES, execution_mode=ExecutionMode.FIXTURE)
        collector.collect(
            FixtureTarget(
                web_target_id="wt-wiring-fixture",
                fixture="depth_path_0.html",
                archetype=A.CONTENT_OPEN,
            )
        )
        run.seal()

        probe_calls = [c for c in calls if c[0] == PROBE_JS]
        assert probe_calls, "PROBE_JS 를 평가하는 evaluate 호출을 찾지 못했다"
        # `D-R0-42` 시정 핵심 — 두 번째 인자로 self.execution_mode.value 가 실제로 전달된다.
        assert probe_calls[0][1] == ("FIXTURE",)

    def test_execution_mode_value_matches_l0_probe_js_comparison_string(self) -> None:
        """`ExecutionMode.REAL_TARGET.value` 가 `l0_probe.js` 의 비교 문자열
        `'REAL_TARGET'` 과 정확히 같은 리터럴인지 — 오타 하나로 게이팅이 조용히
        무력화되는 것을 막는다."""
        assert ExecutionMode.REAL_TARGET.value == "REAL_TARGET"
        assert ExecutionMode.FIXTURE.value == "FIXTURE"


# ══════════════════════════════════════════════════════════════════════════
# 2. marker 게이팅 양방향 — W2 의 실제 l0_probe.js 원문으로 직접 확인 (수정 없음)
# ══════════════════════════════════════════════════════════════════════════

_W2_PROBE_AVAILABLE = W2_PROBE_JS_PATH.exists()


def _require_w2_probe() -> str:
    if not _W2_PROBE_AVAILABLE:
        pytest.skip(
            f"W2 worktree 의 l0_probe.js 를 찾지 못했다({W2_PROBE_JS_PATH}) — "
            "이 환경 밖에서는 1번(호출부 배선) 테스트만으로 검증한다"
        )
    return W2_PROBE_JS_PATH.read_text(encoding="utf-8")


class TestMarkerGatingBehaviorAgainstW2Probe:
    """`depth_path_0.html` 은 `data-region`/`data-endpoint`/`data-endpoint-reached`
    세 marker 를 로드 시점에 정적으로 갖고 있다 — 상호작용 없이 바로 읽을 수 있다.

    **양방향을 함께 본다** — REAL_TARGET(읽지 않음) 만 보면 "아무것도 안 읽는" 무의미한
    구현도 통과한다(A 가 CAPTCHA 건에서 지적한 함정). FIXTURE(읽음) 를 함께 확인해야
    "진짜로 게이팅이지 전면 무력화가 아님"이 증명된다.
    """

    @pytest.fixture(scope="class")
    def probe_js_source(self) -> str:
        return _require_w2_probe()

    @pytest.fixture(scope="class")
    def fixture_url(self) -> str:
        path = FIXTURES / "depth_path_0.html"
        assert path.exists(), f"fixture 없음: {path}"
        return f"file://{path.resolve()}"

    def _evaluate_probe(self, fixture_url: str, probe_js_source: str, *args: Any) -> dict[str, Any]:
        from playwright.sync_api import sync_playwright

        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True)
            page = browser.new_page()
            try:
                page.goto(fixture_url, wait_until="load")
                result: dict[str, Any] = page.evaluate(probe_js_source, *args)
            finally:
                browser.close()
        return result

    def test_real_target_mode_does_not_read_any_marker(
        self, fixture_url: str, probe_js_source: str
    ) -> None:
        probe = self._evaluate_probe(fixture_url, probe_js_source, "REAL_TARGET")
        region_signals = probe["raw_features"]["region_signals"]
        endpoint_signals = probe["raw_features"]["endpoint_signals"]
        assert region_signals["declared_regions"] == []
        assert region_signals["marker_path_disabled"] is True
        assert endpoint_signals["declared_endpoints"] == []
        assert endpoint_signals["body_endpoint_reached"] is None
        assert endpoint_signals["marker_path_disabled"] is True

    def test_fixture_mode_still_reads_markers(self, fixture_url: str, probe_js_source: str) -> None:
        """양방향 대조의 반대쪽 — FIXTURE 에서는 여전히 읽는다."""
        probe = self._evaluate_probe(fixture_url, probe_js_source, "FIXTURE")
        region_signals = probe["raw_features"]["region_signals"]
        endpoint_signals = probe["raw_features"]["endpoint_signals"]
        assert region_signals["declared_regions"] != []
        assert region_signals["declared_regions"][0]["region"] == "ARTICLE_LIST_REGION"
        assert region_signals["marker_path_disabled"] is False
        assert endpoint_signals["declared_endpoints"] != []
        assert endpoint_signals["declared_endpoints"][0]["endpoint"] == "ARTICLE_BODY_OPEN"
        assert endpoint_signals["body_endpoint_reached"] == "ARTICLE_BODY_OPEN"
        assert endpoint_signals["marker_path_disabled"] is False

    def test_undefined_execution_mode_keeps_old_backward_compatible_behavior(
        self, fixture_url: str, probe_js_source: str
    ) -> None:
        """인자를 아예 안 넘기면(옛 호출부처럼) `execution_mode === undefined` 라
        FIXTURE 취급이 유지된다 — W2 주석이 명시한 후방호환 계약. 이 worktree 는 이제
        이 경로를 쓰지 않지만(항상 값을 넘긴다), 계약 자체가 살아있는지 확인해 둔다."""
        probe = self._evaluate_probe(fixture_url, probe_js_source)  # 인자 없음
        region_signals = probe["raw_features"]["region_signals"]
        assert region_signals["marker_path_disabled"] is False
        assert region_signals["declared_regions"] != []
