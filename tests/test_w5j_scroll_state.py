"""W5J — 커밋된 스크롤 fixture (`Δ22-scrollfix`).

## 이 lane 이 남긴 것과 버린 것

**버렸다 — 스크롤 상태 열거 구현.** 이 lane 은 "base 에 scroll 열거 코드가 없다" 는
전제로 열렸고 그 전제가 틀렸다. W5H
`v3_runner/session.py::FixtureSessionDriver.capture_surface` 가 engine 을 고치지 않고
`page.evaluate(window.scrollTo)` 로 이미 `S0..Sn` 을 낸다. B 확정 판정 —
**열거 모듈은 폐기, 커밋 fixture 는 존치.** 같은 일을 하는 두 구현을 두면 관측이 어느
쪽에서 나왔는지 `R22` 로도 구분되지 않는다.

**남겼다 — 커밋된 스크롤 fixture.** A 판정(`T-A-V3-STEP1-021`):

    W5H 는 런타임 임시 파일로 대조했다. 커밋된 것이 아니다. GATE 1 에서 S1..Sn 을
    재현 가능하게 검증하려면 커밋된 fixture 가 필요하다. v3 fixture 13/13 이
    `body{overflow:hidden}` 이라 그 집합으로는 scroll 경로가 영원히 검증되지 않는다
    — 코드가 있어도.

## 이 파일이 검증하는 것 — 기하뿐이다

`ScrollPolicy` · `capture_surface`(W5H)와 `measure_surface`(W5C)는 **다른 브랜치에
있고 이 워크트리에 없다.** import 하지 않는다. 있는 척하지 않는다.

그래서 여기서는 Playwright 로 fixture 를 직접 열어 브라우저가 그대로 돌려주는 값만
읽는다 — `document.documentElement.scrollHeight`, `window.innerHeight`,
`window.scrollTo` 뒤의 `window.scrollY`, control 의 `getBoundingClientRect`.
**판정 임계값을 새로 만들지 않는다.** `first_observed_state` 판정은 W5C 소유이고,
그 기대값은 `expectations.json` 에 적혀 병합 시점 B 의 통합 테스트가 집행한다
(`fixtures/w5j/README.md` 참조).

| fixture | 대조 | `scrollHeight` | 기대 state |
|---|---|---|---|
| `scroll_reveal_control.html` | 양성 | 2616 | `S0 S1 S2 S3` |
| `scroll_single_state.html` | 음성 | 844 | `S0` |

음성 대조군이 짝으로 있어야 "S1 이 났다" 가 "무조건 S1 을 만든다" 와 구분된다.
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from typing import Any

import pytest

REPO = Path(__file__).resolve().parents[1]
RESEARCH = REPO / "research" / "landing_accessibility"
sys.path.insert(0, str(RESEARCH / "src"))

FIXTURES = RESEARCH / "fixtures"
W5J_FIXTURES = FIXTURES / "w5j"
EXPECTATIONS = json.loads((W5J_FIXTURES / "expectations.json").read_text(encoding="utf-8"))

REVEAL = "scroll_reveal_control.html"
SINGLE = "scroll_single_state.html"

#: W5H `ScrollPolicy` 기본값과 같다. 이 파일은 정책 수치를 **정하지 않는다** — 정본은
#: `session.py` 다. 여기 값은 그 기본값을 따라 쓴 것이고, 그렇다는 사실을 적어 둔다.
STEP_RATIO = 1.0
MAX_STATES = 8


# ══════════════════════════════════════════════════════════════════════════════
# 1. 이 lane 은 engine 을 고치지 않고, 두 번째 열거기를 내놓지 않는다.
# ══════════════════════════════════════════════════════════════════════════════

#: base SHA `7c5ae70` 의 engine 파일 sha256. A 가 `R22` 를 신설한 근거이기도 하다 —
#: **engine 은 바이트 동일한데 포착 능력은 driver 에 있었다.**
BASE_ENGINE_SHA256 = {
    "l0_collector.py": "4090ada130889dc44cf933b93b09005b2b06d18cb6f0434be52bab0fe6ad0074",
    "l0_probe.js": "386932995003ad7e0b9e777250341e535f71cf8681cd674124a75f73f8fd9c03",
}


#: `BASE_ENGINE_SHA256` 의 기준 커밋. sha 동등성 검사가 가산 검사로 좁혀진 뒤에도
#: **비교 기준이 어디인지**는 남아야 한다. `HEAD` 를 쓰면 커밋 뒤에 diff 가 비어
#: 조용히 통과한다.
ENGINE_SHA_BASE_COMMIT = "7c5ae70"


def test_this_lane_does_not_touch_the_engine() -> None:
    """engine 변경은 **가산만** 허용된다 (`Δ36` ④ 로 다시 좁힘 — 지운 것이 아니다).

    ## 무엇이 바뀌었나

    원래 주장은 *"기존 수집기가 **바이트 동일**이다"* 였고 근거는 sha256 이었다.
    `Δ36` ④ 가 **다른 lane(W5O)에** `l0_probe.js` 가산을 명시적으로 허용했다 —
    `[Δ36 인용]` *"`l0_probe.js` 에 구조 신호를 추가하는 것은 `Δ20` 이 이미 허용한
    범주다(가산적·회귀 전건 통과·포착 스택 신원 기록)."*

    그래서 sha 동등성은 더 이상 참이 아니다. 하지만 이 테스트가 **실제로 지키려던 것**
    — *"입력이 그대로면 기존 출력도 그대로다"* — 는 그대로 지킬 수 있다:
    `git diff --numstat` 의 **삭제 열이 0** 이면 기존 줄이 하나도 지워지거나 바뀌지
    않았다는 뜻이고, 그러면 기존 키의 출력은 정의상 같다.

    `l0_collector.py` 는 **여전히 바이트 동일**을 요구한다 — W5O 가 그 파일은 고치지
    않았고(가산조차 필요 없었다: `raw_features` 가 probe 산출을 키 필터 없이 그대로
    통과시킨다), 그 사실이 여기서 회귀로 고정된다.
    """
    import subprocess

    engine = RESEARCH / "src" / "landing_accessibility" / "engine"
    for name, base_sha in BASE_ENGINE_SHA256.items():
        relative = f"research/landing_accessibility/src/landing_accessibility/engine/{name}"
        proc = subprocess.run(
            ["git", "diff", "--numstat", ENGINE_SHA_BASE_COMMIT, "--", relative],
            cwd=REPO,
            capture_output=True,
            text=True,
            check=False,
        )
        out = proc.stdout.strip()
        if not out:
            # 변경이 아예 없다 — 가장 강한 형태. sha 도 그 값이어야 한다(양성 대조).
            actual = hashlib.sha256((engine / name).read_bytes()).hexdigest()
            assert actual == base_sha, f"{name}: git 은 무변경인데 sha 가 다르다"
            continue
        added, deleted, _ = out.split("\t", 2)
        assert deleted == "0", (
            f"{name} 에서 {deleted} 줄이 삭제/변경됐다 — engine 변경은 **가산만** "
            f"허용된다 (Δ20 · Δ36 ④). 추가: {added}"
        )


def test_this_lane_ships_no_second_enumerator() -> None:
    """열거 정본은 W5H `session.py` 하나다. 같은 일을 두 곳에서 하지 않는다."""
    src = RESEARCH / "src" / "landing_accessibility"
    assert not list(src.rglob("scroll_states.py"))
    assert not list(src.rglob("scroll_state*.py"))


def test_this_lane_only_adds_its_own_fixture_directory() -> None:
    """다른 lane 의 fixture 를 건드리지 않는다 — `fixtures/v3/` 는 이 lane 소유가 아니다."""
    assert W5J_FIXTURES.is_dir()
    assert sorted(p.name for p in W5J_FIXTURES.iterdir() if p.is_file()) == [
        "README.md",
        "expectations.json",
        REVEAL,
        SINGLE,
    ]


# ══════════════════════════════════════════════════════════════════════════════
# 2. 매니페스트 — fixture 는 커밋된 것이어야 GATE 1 이 재현한다.
# ══════════════════════════════════════════════════════════════════════════════


def test_fixtures_declare_what_they_validate_and_reference_no_live_service() -> None:
    paths = sorted(W5J_FIXTURES.glob("*.html"))
    assert [p.name for p in paths] == [REVEAL, SINGLE]
    for path in paths:
        text = path.read_text(encoding="utf-8")
        assert "FIXTURE:" in text, f"{path.name} 에 FIXTURE 주석이 없다"
        assert "검증 대상" in text
        assert "http://" not in text and "https://" not in text


def test_manifest_covers_every_fixture_with_a_one_line_purpose() -> None:
    """기대값 없는 fixture 는 검증의 근거가 되지 못한다."""
    declared = set(EXPECTATIONS["fixtures"])
    on_disk = {p.name for p in W5J_FIXTURES.glob("*.html")}
    assert declared == on_disk
    for name, spec in EXPECTATIONS["fixtures"].items():
        assert spec["validates"].strip(), f"{name} 에 한 줄 설명이 없다"
        for key in (
            "sha256",
            "scrolls",
            "document_scroll_height_css_px",
            "expected_scroll_states",
            "expected_state_indices",
        ):
            assert key in spec, f"{name} 매니페스트에 {key} 가 없다"


def test_manifest_sha256_matches_the_committed_bytes() -> None:
    """매니페스트가 **지금 트리에 있는 그 파일**을 가리키는지 고정한다."""
    for name, spec in EXPECTATIONS["fixtures"].items():
        actual = hashlib.sha256((W5J_FIXTURES / name).read_bytes()).hexdigest()
        assert actual == spec["sha256"], f"{name} 이 매니페스트 sha256 과 다르다 — drift"


def test_manifest_declares_a_positive_and_a_negative_control() -> None:
    """양성만 두면 검사가 동작하는지 알 수 없다."""
    scrolls = {n: s["scrolls"] for n, s in EXPECTATIONS["fixtures"].items()}
    assert scrolls == {REVEAL: True, SINGLE: False}
    assert EXPECTATIONS["fixtures"][REVEAL]["expected_scroll_states"] >= 4
    assert EXPECTATIONS["fixtures"][SINGLE]["expected_scroll_states"] == 1


def test_expectations_declare_all_three_outcomes() -> None:
    """`S0` / `S1+` / `NULL` 이 **각각 다른 값**으로 선언돼 있어야 한다."""
    controls = EXPECTATIONS["fixtures"][REVEAL]["controls"]
    values = [c["first_observed_state"] for c in controls.values()]
    assert values == ["S0", "S1", None]
    assert len({str(v) for v in values}) == 3


def test_the_three_controls_are_structurally_identical() -> None:
    """마크업이 같아야 결과 차이의 원인을 scroll 로 귀속할 수 있다."""
    text = (W5J_FIXTURES / REVEAL).read_text(encoding="utf-8")
    for sel in ("ctl-s0", "ctl-s1", "ctl-never"):
        assert f'<button class="cta" id="{sel}" data-role="cta">지금 신청하기</button>' in text


def test_the_reveal_fixture_is_not_the_overflow_hidden_kind() -> None:
    """v3 13종이 `body{overflow:hidden}` 이라 못 하는 일이 이것이다."""
    text = (W5J_FIXTURES / REVEAL).read_text(encoding="utf-8")
    assert "overflow: hidden" not in text and "overflow:hidden" not in text


def test_readme_hands_the_integration_test_to_the_merge() -> None:
    """`ScrollPolicy` 통합은 이 브랜치 의무가 아니다 — 그 사실이 문서에 남아야 한다."""
    readme = (W5J_FIXTURES / "README.md").read_text(encoding="utf-8")
    assert "W5H `ScrollPolicy` 와 병합된 뒤에야 `S1..Sn` 경로를 실행한다" in readme
    assert "B (병합 시점)" in readme


# ══════════════════════════════════════════════════════════════════════════════
# 3. 실제 브라우저 — 여기서만 fixture 의 주장이 실측이 된다.
#    브라우저가 그대로 돌려주는 값만 읽는다. 새 판정 임계값이 없다.
# ══════════════════════════════════════════════════════════════════════════════

pytest.importorskip("playwright.sync_api")

SELECTORS = ("button#ctl-s0", "button#ctl-s1", "button#ctl-never")

_GEOMETRY_JS = """
(selectors) => {
  const out = {};
  for (const sel of selectors) {
    const el = document.querySelector(sel);
    if (!el) { out[sel] = null; continue; }
    const r = el.getBoundingClientRect();
    const rendered = !!(el.offsetParent || r.width || r.height);
    out[sel] = {
      rendered,
      top: r.top, bottom: r.bottom, width: r.width, height: r.height,
      intersects_viewport: rendered && r.bottom > 0 && r.top < window.innerHeight,
    };
  }
  return out;
}
"""


def _walk(fixture: str) -> dict[str, Any]:
    """fixture 를 열어 브라우저 기하를 offset 별로 읽는다.

    **열거 구현이 아니다.** 여기서 나오는 것은 판정이 아니라 브라우저가 그대로 돌려준
    수치(`scrollY` / `innerHeight` / `scrollHeight` / `getBoundingClientRect`)뿐이다.
    `S0..Sn` 을 정책으로 여는 일은 W5H `capture_surface` 소유이고, 그 통합은 병합
    시점 B 의 의무다.
    """
    from landing_accessibility.engine.firewall import ExecutionMode, assert_navigation_allowed
    from landing_accessibility.engine.l0_collector import SETTLE_MS, L0Collector
    from playwright.sync_api import sync_playwright

    url = assert_navigation_allowed(
        ExecutionMode.FIXTURE,
        f"file://{(W5J_FIXTURES / fixture).resolve()}",
        fixture_root=FIXTURES,
    )
    shell = L0Collector.__new__(L0Collector)  # `03 §1` 공통 모바일 환경을 그대로 쓴다
    offsets: list[float] = []
    geometry: list[dict[str, Any]] = []
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        context = shell._new_context(browser)
        page = context.new_page()
        try:
            page.goto(url, wait_until="load", timeout=15_000)
            page.wait_for_timeout(SETTLE_MS)
            inner_height = float(page.evaluate("() => window.innerHeight"))
            scroll_height = float(page.evaluate("() => document.documentElement.scrollHeight"))
            step = max(1.0, inner_height * STEP_RATIO)
            for _ in range(MAX_STATES):
                y = float(page.evaluate("() => window.scrollY"))
                offsets.append(y)
                geometry.append(page.evaluate(_GEOMETRY_JS, list(SELECTORS)))
                if y + inner_height >= scroll_height - 0.5:
                    break
                new_y = float(
                    page.evaluate(
                        "(t) => { window.scrollTo(0, t); return window.scrollY; }", y + step
                    )
                )
                page.wait_for_timeout(SETTLE_MS)
                if new_y <= y + 0.5:
                    break
        finally:
            context.close()
            browser.close()
    return {
        "inner_height": inner_height,
        "scroll_height": scroll_height,
        "offsets": offsets,
        "states": [f"S{i}" for i in range(len(offsets))],
        "geometry": geometry,
    }


@pytest.mark.slow
def test_reveal_fixture_actually_scrolls_and_yields_four_states() -> None:
    """양성 대조군 — v3 13종에서는 원리적으로 못 보는 것이다."""
    spec = EXPECTATIONS["fixtures"][REVEAL]
    walk = _walk(REVEAL)

    assert walk["inner_height"] == spec["viewport_inner_height_css_px"]
    assert walk["scroll_height"] == spec["document_scroll_height_css_px"]
    assert walk["scroll_height"] > walk["inner_height"], (
        "스크롤 여지가 없으면 fixture 가 무의미하다"
    )
    assert walk["scroll_height"] - walk["inner_height"] == spec["max_scroll_y_css_px"]

    assert walk["offsets"] == spec["expected_scroll_offsets_css_px"]
    assert walk["states"] == spec["expected_state_indices"]
    assert len(walk["states"]) == spec["expected_scroll_states"] >= 4
    assert max(walk["offsets"]) > 0, "window.scrollTo 가 실제로 문서를 옮겨야 한다"


@pytest.mark.slow
def test_single_state_fixture_makes_no_state_beyond_s0() -> None:
    """음성 대조군 — 걷기가 무조건 `S1` 을 만들어내는 것이 아님을 보인다."""
    spec = EXPECTATIONS["fixtures"][SINGLE]
    walk = _walk(SINGLE)

    assert walk["scroll_height"] == spec["document_scroll_height_css_px"]
    assert walk["scroll_height"] == walk["inner_height"], "한 화면에 들어가야 음성 대조군이다"
    assert walk["offsets"] == [0]
    assert walk["states"] == ["S0"]
    assert len(walk["states"]) == spec["expected_scroll_states"] == 1


@pytest.mark.slow
def test_scroll_to_is_a_no_op_on_the_negative_control() -> None:
    """음성 대조군에서는 `scrollTo` 를 불러도 `scrollY` 가 0 에 머문다."""
    from landing_accessibility.engine.firewall import ExecutionMode, assert_navigation_allowed
    from landing_accessibility.engine.l0_collector import SETTLE_MS, L0Collector
    from playwright.sync_api import sync_playwright

    url = assert_navigation_allowed(
        ExecutionMode.FIXTURE,
        f"file://{(W5J_FIXTURES / SINGLE).resolve()}",
        fixture_root=FIXTURES,
    )
    shell = L0Collector.__new__(L0Collector)
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        context = shell._new_context(browser)
        page = context.new_page()
        try:
            page.goto(url, wait_until="load", timeout=15_000)
            page.wait_for_timeout(SETTLE_MS)
            moved = page.evaluate("() => { window.scrollTo(0, 5000); return window.scrollY; }")
        finally:
            context.close()
            browser.close()
    assert moved == 0, "이 fixture 가 스크롤되면 음성 대조군이 아니다"


@pytest.mark.slow
def test_the_three_controls_sit_at_different_document_positions() -> None:
    """마크업이 같은 세 control 이 **기하**로 갈린다.

    `first_observed_state` 판정 자체는 W5C 소유다. 여기서 고정하는 것은 그 판정이
    `S0`/`S1`/`None` 으로 갈릴 **근거가 fixture 안에 실재한다**는 사실이다 —
    `#ctl-s1` 은 offset 0 에서 viewport 밖이고 offset 844 에서 안이며,
    `#ctl-never` 는 어느 offset 에서도 렌더되지 않는다.
    """
    walk = _walk(REVEAL)
    first, second = walk["geometry"][0], walk["geometry"][1]

    assert first["button#ctl-s0"]["intersects_viewport"] is True
    assert first["button#ctl-s1"]["intersects_viewport"] is False
    assert second["button#ctl-s1"]["intersects_viewport"] is True

    for frame in walk["geometry"]:
        assert frame["button#ctl-never"]["rendered"] is False
        assert frame["button#ctl-never"]["intersects_viewport"] is False

    # S0 만 찍으면 뒤 둘이 구분되지 않는다 — 그것이 이 fixture 가 존재하는 이유다.
    assert (
        first["button#ctl-s1"]["intersects_viewport"]
        == first["button#ctl-never"]["intersects_viewport"]
    )


@pytest.mark.slow
def test_walk_is_deterministic_across_two_runs() -> None:
    """같은 fixture 를 두 번 걸으면 같은 offset 열과 같은 기하가 나온다."""

    def signature() -> str:
        walk = _walk(REVEAL)
        return json.dumps(
            {"offsets": walk["offsets"], "states": walk["states"], "geometry": walk["geometry"]},
            sort_keys=True,
        )

    assert signature() == signature()
