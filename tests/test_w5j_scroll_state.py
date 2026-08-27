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
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

from lane_ownership import (
    ENGINE_DIR,
    LaneTipUnresolvable,
    lane_changed_paths,
    lane_committed_paths,
    paths_under,
    resolve_lane_tip,
)

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

#: 이 lane 의 브랜치. 소유 경계는 이 브랜치가 base 이후 만든 diff 로 잰다.
LANE_BRANCH = "claude-b/w5j-scroll-state"

#: base SHA `7c5ae70` 의 engine 파일 sha256. A 가 `R22` 를 신설한 근거다 —
#: **engine 은 바이트 동일한데 포착 능력은 driver 에 있었다.** 지금은 이 값이 lane 소유
#: 경계의 판정 기준이 **아니다**(아래 W5M 시정 참조). 그 시점의 사실로 남겨 둔다.
BASE_ENGINE_SHA256 = {
    "l0_collector.py": "4090ada130889dc44cf933b93b09005b2b06d18cb6f0434be52bab0fe6ad0074",
    "l0_probe.js": "386932995003ad7e0b9e777250341e535f71cf8681cd674124a75f73f8fd9c03",
}


def test_this_lane_does_not_touch_the_engine() -> None:
    """이 lane 의 **자기 diff** 안에 engine 파일이 하나도 없다.

    ## W5M 시정 — 재는 대상이 틀렸었다

    원래 이 테스트는 `l0_collector.py` 의 **절대 sha256** 이 base 와 같은지를 봤다. 그래서
    12 lane 병합에서 깨졌다:

        `[인용]` ``assert '9ea010389f8a...' == '4090ada13088...'``

    그런데 W5J 는 그 파일을 건드리지 않았다. 바뀐 것은 **W5I 의 승인된 가산 수정**
    (`8fcf540` selector <-> backendDOMNodeId 조인, +37/-0)이다. 파일의 절대 상태를 재면
    다른 lane 의 승인된 변경까지 잡는다 — 지키려던 명제("이 lane 은 engine 을 고치지
    않는다")는 여전히 참인데 계기가 틀린 것을 가리켰다.

    지금은 `LANE_BRANCH` 가 base 이후 만든 diff(+ 아직 커밋 안 된 작업 트리 변경)에
    engine 경로가 있는지를 본다. 단언이 **더 강해진다**:

    - 다른 lane 이 engine 을 승인받아 고쳐도 이 테스트는 흔들리지 않는다.
    - 이 lane 이 engine 을 고치면 커밋했든 안 했든 잡힌다.
    - 파일 두 개가 아니라 `engine/` **디렉터리 전체**를 본다 — 새 파일을 끼워 넣어도 잡힌다.

    음성 대조는 `test_the_same_measurement_catches_a_lane_that_did_touch_the_engine`
    (실제로 engine 을 고친 W5I 를 같은 계기로 재면 잡힌다) 과
    `test_the_measurement_catches_an_injected_engine_edit` (합성 lane 에 engine 수정을
    심으면 잡힌다) 이다.
    """
    changed = lane_changed_paths(LANE_BRANCH)
    assert changed, "diff 가 비면 계기가 죽은 것이다 — 무엇도 잡지 못한다"
    offenders = paths_under(changed, ENGINE_DIR)
    assert offenders == (), f"이 lane 이 engine 을 고쳤다: {offenders}"


def test_the_same_measurement_catches_a_lane_that_did_touch_the_engine() -> None:
    """음성 대조 (실측) — 같은 계기를 W5I 에 대면 engine 수정이 **잡힌다**.

    W5I 는 A 승인 아래 `l0_collector.py` 에 조인을 넣었다. 그러니 이 계기가 "아무것도
    못 잡는 계기" 가 아님을 저장소 안의 실제 lane 로 보일 수 있다. 위 테스트의 초록불이
    "engine 수정을 못 보는 눈" 때문이 아님을 이 대조가 배제한다.
    """
    theirs = paths_under(lane_committed_paths("claude-b/w5i-ax-join"), ENGINE_DIR)
    assert theirs == (f"{ENGINE_DIR}/l0_collector.py",), theirs
    mine = paths_under(lane_committed_paths(LANE_BRANCH), ENGINE_DIR)
    assert mine == ()


def test_the_measurement_catches_an_injected_engine_edit(tmp_path: Path) -> None:
    """음성 대조 (주입) — 합성 lane 의 diff 에 engine 수정을 심으면 반드시 잡힌다.

    이 저장소를 건드리지 않고 임시 git 저장소에 base 커밋 + lane 커밋을 만든다. lane
    커밋이 `engine/l0_collector.py` 를 고치므로, `lane_committed_paths` 가 그 경로를
    돌려주지 않으면 계기가 고장 난 것이다.
    """
    repo = tmp_path / "synthetic"
    (repo / ENGINE_DIR).mkdir(parents=True)
    run = lambda *a: subprocess.run(  # noqa: E731
        ["git", *a], cwd=repo, check=True, capture_output=True, text=True
    )
    run("init", "-q", "-b", "main")
    run("config", "user.email", "w5m@example.invalid")
    run("config", "user.name", "w5m")
    (repo / ENGINE_DIR / "l0_collector.py").write_text("BASE\n", encoding="utf-8")
    (repo / "README.md").write_text("base\n", encoding="utf-8")
    run("add", "-A")
    run("commit", "-qm", "base")
    base = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=repo, capture_output=True, text=True, check=True
    ).stdout.strip()

    run("checkout", "-q", "-b", "claude-b/w5j-scroll-state")
    (repo / ENGINE_DIR / "l0_collector.py").write_text("BASE\n# 위반\n", encoding="utf-8")
    run("add", "-A")
    run("commit", "-qm", "lane 이 engine 을 고친다")

    caught = paths_under(lane_committed_paths(LANE_BRANCH, base=base, repo=repo), ENGINE_DIR)
    assert caught == (f"{ENGINE_DIR}/l0_collector.py",), caught


def test_the_measurement_refuses_to_pass_when_it_cannot_find_the_lane() -> None:
    """lane 을 특정하지 못하면 **조용히 통과하지 않는다** — 예외를 던진다."""
    with pytest.raises(LaneTipUnresolvable):
        lane_committed_paths("claude-b/does-not-exist-w5m-control")


def test_the_lane_tip_survives_a_deleted_branch_ref() -> None:
    """브랜치 ref 가 정리돼도 병합 커밋의 두 번째 부모로 같은 tip 을 찾는다.

    ref 이름을 일부러 존재하지 않는 것으로 주면 fallback 경로만 탄다. 그래도 브랜치
    ref 로 찾은 tip 과 같은 커밋이 나와야 한다.
    """
    by_ref = resolve_lane_tip(LANE_BRANCH)
    by_merge = resolve_lane_tip("deleted-remote/w5j-scroll-state")
    assert by_ref[0] == "branch-ref"
    assert by_merge[0].startswith("merge-commit ")
    assert by_ref[1] == by_merge[1]


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
