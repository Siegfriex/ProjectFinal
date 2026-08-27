"""W5H — `SessionDriver` (fixture 전용 세션 구동기).

## 이 파일이 증명하려는 것

수집기 테스트가 빠지기 쉬운 함정 셋을 각각 정면으로 겨눈다.

1. **"선언했다" 를 "적용됐다" 로 세지 않는다.** viewport·UA·locale·timezone 은
   `new_context` 에 넘긴 값이 아니라 **페이지 안에서 렌더된 값**으로 확인한다.
   선언만 보면 인자 이름을 틀리게 적어도 초록불이 켜진다.
2. **"아무것도 못 하는 코드" 와 "위험한 것만 못 하는 코드" 를 구분한다.**
   credential 필드에 `Page.fill` 이 0회인 것과 **나란히**, 안전한 검색창에는 실제로
   값이 들어가 `input.value` 로 읽히는 양성 대조를 둔다.
3. **부재를 코드로 증명한다.** "scroll 은 depth 가 아니다" 를 주석이 아니라 AST 로
   본다 — `capture_surface` 본문에 `RawTransition` 이 등장하지 않는다.

`FIXTURE_DISCRIMINATION_MATRIX.json`(W5E) 의 선언 좌표와 **실측 bbox** 를 무허용오차로
대조한다. W5E 는 자기 fixture 를 Playwright 로 렌더해 좌표를 맞췄다고 보고했고, 여기서는
그 주장을 **다른 수집 경로**(이 드라이버)로 다시 확인한다.

실사이트 접속 0 · 외부 네트워크 0 · credential 입력 0.
"""

from __future__ import annotations

import ast
import hashlib
import json
import subprocess
import sys
from collections.abc import Iterator, Mapping, Sequence
from pathlib import Path
from typing import Any

import pytest

REPO = Path(__file__).resolve().parents[1]
RESEARCH = REPO / "research" / "landing_accessibility"
sys.path.insert(0, str(RESEARCH / "src"))

from lane_ownership import (  # noqa: E402
    ENGINE_DIR,
    LANE_BASE,
    lane_changed_paths,
    lane_committed_paths,
    paths_under,
)

pytest.importorskip("playwright.sync_api")

from landing_accessibility.engine import l0_collector as _l0  # noqa: E402
from landing_accessibility.engine.firewall import NavigationBlockedError  # noqa: E402
from landing_accessibility.v3_runner import session as session_module  # noqa: E402
from landing_accessibility.v3_runner.discovery import FixtureInputMode  # noqa: E402
from landing_accessibility.v3_runner.evidence import INPUT_MODE_VALUES  # noqa: E402
from landing_accessibility.v3_runner.runner import (  # noqa: E402
    DEPTH_CONDITIONAL_TOKENS,
    ELIGIBILITY_PROCEEDABLE,
    PlannedAction,
    RawTransition,
    SessionDriver,
    SurfaceObservation,
    TaskContract,
    path_manifest_sha256,
)
from landing_accessibility.v3_runner.session import (  # noqa: E402
    AX_NODE_JOIN_STATUS,
    KNOWN_LIMITATIONS,
    SAFE_PROBE_TEXT,
    CredentialInputRefusedError,
    FixtureSessionDriver,
    ScrollPolicy,
    SessionNotOpenError,
    is_credential_field,
    observe_input_mode,
)

#: 이 lane 의 브랜치. 소유 경계는 이 브랜치가 base 이후 만든 diff 로 잰다 (W5M).
W5H_BRANCH = "claude-b/w5h-session-driver"


def _base_engine_text(name: str) -> str:
    """`LANE_BASE` 커밋 시점의 engine 파일 원문. 작업 트리를 읽지 않는다."""
    proc = subprocess.run(
        ["git", "show", f"{LANE_BASE}:{ENGINE_DIR}/{name}"],
        cwd=REPO,
        capture_output=True,
        text=True,
        check=True,
    )
    return proc.stdout


def _join_lines(text: str) -> list[str]:
    """selector 와 `backendDOMNodeId` 가 **같은 줄**에 있는 줄. 조인의 흔적이다."""
    return [line for line in text.splitlines() if "backendDOMNodeId" in line and "selector" in line]


FIXTURES_V3 = RESEARCH / "fixtures" / "v3"
MATRIX_PATH = FIXTURES_V3 / "FIXTURE_DISCRIMINATION_MATRIX.json"
SESSION_SOURCE = Path(session_module.__file__).read_text(encoding="utf-8")

MATRIX: dict[str, Any] = json.loads(MATRIX_PATH.read_text(encoding="utf-8"))
FIXTURE_ENTRIES: dict[str, dict[str, Any]] = {
    entry["fixture_id"]: entry for entry in MATRIX["fixtures"]
}
FIXTURE_IDS: tuple[str, ...] = tuple(FIXTURE_ENTRIES)


# ---------------------------------------------------------------------------
# 공통 하네스
# ---------------------------------------------------------------------------


def make_contract(target_id: str, starting_url: str | None = None, **kw: Any) -> TaskContract:
    """계약은 이 lane 의 관심사가 아니다 — 최소 형태만 만든다 (W5A 가 정본 소유)."""
    return TaskContract(
        target_id=target_id,
        family_id=kw.pop("family_id", "F0"),
        service=kw.pop("service", "fixture"),
        starting_url=starting_url or f"{target_id}.html",
        frozen_task=kw.pop("frozen_task", "T-FIXTURE"),
        task_instruction=kw.pop("task_instruction", "fixture 관측"),
        fixed_fixture=kw.pop("fixed_fixture", "없음"),
        fixture_override=kw.pop("fixture_override", None),
        endpoint_contract=kw.pop("endpoint_contract", "fixture endpoint"),
        forbidden_actions=kw.pop("forbidden_actions", ()),
        task_contract_hash=kw.pop("task_contract_hash", "a" * 64),
        endpoint_contract_hash=kw.pop("endpoint_contract_hash", "b" * 64),
        **kw,
    )


@pytest.fixture(scope="module")
def browser() -> Iterator[Any]:
    """13종을 한 브라우저로 돈다. 컨텍스트는 fixture 마다 새로 만들어진다 (`03 §1`)."""
    from playwright.sync_api import sync_playwright

    pw = sync_playwright().start()
    instance = pw.chromium.launch()
    try:
        yield instance
    finally:
        instance.close()
        pw.stop()


@pytest.fixture
def driver_factory(browser: Any) -> Iterator[Any]:
    """`FixtureSessionDriver` 를 만들고 테스트가 끝나면 반드시 닫는다."""
    created: list[FixtureSessionDriver] = []

    def _make(root: Path = FIXTURES_V3, **kw: Any) -> FixtureSessionDriver:
        driver = FixtureSessionDriver(
            fixture_root=root,
            browser=browser,
            capture_screenshots=kw.pop("screenshots", False),
            **kw,
        )
        created.append(driver)
        return driver

    yield _make
    for driver in created:
        driver.close()


def write_page(root: Path, name: str, body: str, *, head: str = "") -> str:
    """테스트 전용 임시 fixture 를 만든다.

    `fixtures/v3/` 는 W5E 소유라 건드리지 않는다. 여기서 만드는 것은 `tmp_path` 안의
    런타임 파일이며 저장소에 남지 않는다. 모바일 viewport meta 를 넣는 이유는 그것이
    없으면 Chrome 이 980px 레이아웃으로 떨어져 fixture 집합과 다른 조건이 되기 때문이다.
    """
    path = root / name
    path.write_text(
        "<!doctype html><html lang=ko><head><meta charset=utf-8>"
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        f"<style>body{{margin:0;width:390px}}</style>{head}</head>"
        f"<body>{body}</body></html>",
        encoding="utf-8",
    )
    return name


def spy_on_fill(page: Any, calls: list[tuple[Any, Any]]) -> None:
    """`Page.fill` 에 spy 를 건다. 원래 호출은 그대로 통과시킨다.

    호출을 막지 않는 것이 중요하다 — 막으면 양성 대조(안전 입력에 값이 실제로
    들어간다)를 확인할 수 없고, 그러면 "아무것도 입력 못 하는 코드" 와 구분되지 않는다.
    """
    original = page.fill

    def _spy(*args: Any, **kwargs: Any) -> Any:
        calls.append((args, kwargs))
        return original(*args, **kwargs)

    page.fill = _spy


def dom_hash(payload: Any) -> str:
    return hashlib.sha256(payload.dom.encode("utf-8")).hexdigest()


def code_source() -> str:
    """docstring 을 전부 뺀 **코드 본문**.

    금지 어휘 검사는 코드에만 걸어야 한다 — 무엇을 왜 하지 않는지 적은 문단까지
    걸리면 "안전 설계를 문서화하면 테스트가 깨지는" 이상한 규칙이 된다. 문서는
    금지 조작을 **설명**하고, 코드는 그 조작을 **하지 않는다**. 검사 대상은 후자다.
    """
    tree = ast.parse(SESSION_SOURCE)
    doc_lines: set[int] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Module | ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef):
            continue
        first = node.body[0] if node.body else None
        if (
            isinstance(first, ast.Expr)
            and isinstance(first.value, ast.Constant)
            and isinstance(first.value.value, str)
        ):
            doc_lines.update(range(first.lineno, (first.end_lineno or first.lineno) + 1))
    return "\n".join(
        line
        for number, line in enumerate(SESSION_SOURCE.splitlines(), start=1)
        if number not in doc_lines
    )


def function_node(name: str) -> ast.FunctionDef:
    tree = ast.parse(SESSION_SOURCE)
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return node
    raise AssertionError(f"{name} 이 session.py 에 없다")


def attribute_calls(node: ast.AST) -> list[str]:
    return [
        child.func.attr
        for child in ast.walk(node)
        if isinstance(child, ast.Call) and isinstance(child.func, ast.Attribute)
    ]


# ═══════════════════════════════════════════════════════════════════════════
# 1. 경계 적합 — W5F Protocol 에 실제로 붙는가
# ═══════════════════════════════════════════════════════════════════════════


class TestProtocolConformance:
    def test_driver_is_a_w5f_session_driver(self) -> None:
        driver = FixtureSessionDriver(fixture_root=FIXTURES_V3)
        assert isinstance(driver, SessionDriver)

    def test_capture_surface_returns_w5f_surface_observations(self, driver_factory: Any) -> None:
        driver = driver_factory()
        states = driver.capture_surface(make_contract("direct_text_button"))
        assert states, "관측이 하나도 없다"
        assert all(isinstance(s, SurfaceObservation) for s in states)

    def test_activate_returns_a_w5f_raw_transition(self, driver_factory: Any) -> None:
        driver = driver_factory()
        driver.capture_surface(make_contract("hamburger"))
        transition = driver.activate(PlannedAction("OPEN_GLOBAL_MENU", "#open"))
        assert isinstance(transition, RawTransition)


# ═══════════════════════════════════════════════════════════════════════════
# 2. 부재의 증명 — scroll 은 activation depth 가 아니다 (`03 §3`)
# ═══════════════════════════════════════════════════════════════════════════


class TestScrollIsNotDepth:
    def test_capture_surface_body_never_mentions_raw_transition(self) -> None:
        """구조적 확인 — 주석이 아니라 AST 로 본다.

        `capture_surface` 안에서 `RawTransition` 이름이 한 번도 나오지 않고
        `activate` 를 부르지도 않는다. 그러면 scroll 국면이 flow step 을 만들 **경로가
        없다**. "만들지 않기로 했다" 와 "만들 수 없다" 는 다른 주장이다.
        """
        node = function_node("capture_surface")
        names = {n.id for n in ast.walk(node) if isinstance(n, ast.Name)}
        attrs = set(attribute_calls(node))
        assert "RawTransition" not in names
        assert "activate" not in attrs
        assert "_dispatch" not in attrs
        assert "_failed" not in attrs

    def test_capture_surface_return_annotation_is_a_surface_sequence(self) -> None:
        node = function_node("capture_surface")
        assert node.returns is not None
        assert ast.unparse(node.returns) == "Sequence[SurfaceObservation]"

    def test_scroll_states_are_indexed_s0_upward(self, driver_factory: Any, tmp_path: Path) -> None:
        name = write_page(
            tmp_path, "tall.html", "<div style='height:4000px;background:#eee'></div>"
        )
        driver = driver_factory(root=tmp_path)
        states = driver.capture_surface(make_contract("tall", name))
        assert [s.state_index for s in states] == [f"S{i}" for i in range(len(states))]
        assert len(states) > 1, "스크롤 가능한 문서인데 S1 이 만들어지지 않았다"
        assert states[0].scroll_y == 0.0
        assert [s.scroll_y for s in states] == sorted({s.scroll_y for s in states})

    def test_a_scrolling_capture_produces_zero_transitions(
        self, driver_factory: Any, tmp_path: Path
    ) -> None:
        """행동 확인 — S1..Sn 을 실제로 만들어도 action_log 에 activate 가 0건이다."""
        name = write_page(
            tmp_path, "tall2.html", "<div style='height:4000px;background:#eee'></div>"
        )
        driver = driver_factory(root=tmp_path)
        states = driver.capture_surface(make_contract("tall2", name))
        assert len(states) > 1
        kinds = [entry["kind"] for entry in driver.action_log]
        assert kinds == ["capture_surface"]
        assert driver.action_log[0]["produced_transitions"] == 0

    def test_scroll_policy_rejects_degenerate_values(self) -> None:
        with pytest.raises(ValueError):
            ScrollPolicy(step_ratio=0)
        with pytest.raises(ValueError):
            ScrollPolicy(max_states=0)


# ═══════════════════════════════════════════════════════════════════════════
# 3. `03 §1` 공통 모바일 환경 — 선언이 아니라 렌더된 값으로 본다
# ═══════════════════════════════════════════════════════════════════════════


class TestRenderedEnvironment:
    @pytest.mark.parametrize("fixture_id", FIXTURE_IDS)
    def test_declared_environment_is_actually_rendered(
        self, driver_factory: Any, fixture_id: str
    ) -> None:
        driver = driver_factory()
        driver.capture_surface(make_contract(fixture_id))
        env = driver.environment
        assert env is not None
        assert env.viewport_width_rendered == 390
        assert env.viewport_height_rendered == 844
        assert env.user_agent_rendered == _l0.MOBILE_USER_AGENT
        assert env.locale_rendered == "ko-KR"
        assert env.timezone_rendered == "Asia/Seoul"
        assert all(env.matches().values()), env.matches()

    def test_environment_record_keeps_requested_and_final_url_and_timestamp(
        self, driver_factory: Any
    ) -> None:
        driver = driver_factory()
        driver.capture_surface(make_contract("hamburger"))
        env = driver.environment
        assert env is not None
        assert env.requested_url.startswith("file://")
        assert env.requested_url.endswith("hamburger.html")
        assert env.final_url == env.requested_url
        assert env.collected_at.endswith("Z")
        assert env.execution_mode == "FIXTURE"

    def test_context_is_fresh_and_carries_no_cookie_and_no_login(self, driver_factory: Any) -> None:
        driver = driver_factory()
        driver.capture_surface(make_contract("task_first_auth"))
        env = driver.environment
        assert env is not None
        assert env.fresh_context is True
        assert env.stored_cookie_count == 0
        assert env.login_performed is False

    def test_touch_is_enabled_in_the_rendered_page(self, driver_factory: Any) -> None:
        driver = driver_factory()
        driver.capture_surface(make_contract("direct_text_button"))
        env = driver.environment
        assert env is not None
        assert env.max_touch_points is not None and env.max_touch_points > 0

    def test_environment_constants_are_reused_not_redeclared(self) -> None:
        """`l0_collector` 의 상수를 **그대로** 쓴다. 두 벌이 되면 조용히 갈라진다."""
        assert FixtureSessionDriver.VIEWPORT_WIDTH is _l0.VIEWPORT_WIDTH
        assert FixtureSessionDriver.VIEWPORT_HEIGHT is _l0.VIEWPORT_HEIGHT
        assert FixtureSessionDriver.LOCALE is _l0.LOCALE
        assert FixtureSessionDriver.TIMEZONE_ID is _l0.TIMEZONE_ID
        assert FixtureSessionDriver.USER_AGENT is _l0.MOBILE_USER_AGENT

    def test_matrix_viewport_declaration_matches_the_driver(self) -> None:
        assert MATRIX["viewport"]["width"] == FixtureSessionDriver.VIEWPORT_WIDTH
        assert MATRIX["viewport"]["height"] == FixtureSessionDriver.VIEWPORT_HEIGHT


# ═══════════════════════════════════════════════════════════════════════════
# 4. 13종 전건 capture_surface + evidence package
# ═══════════════════════════════════════════════════════════════════════════


class TestThirteenFixtures:
    def test_the_matrix_lists_thirteen_fixtures(self) -> None:
        assert len(FIXTURE_IDS) == 13

    @pytest.mark.parametrize("fixture_id", FIXTURE_IDS)
    def test_every_fixture_captures_at_least_s0(self, driver_factory: Any, fixture_id: str) -> None:
        driver = driver_factory()
        states = driver.capture_surface(make_contract(fixture_id))
        assert states, f"{fixture_id}: 관측 0건"
        assert states[0].state_index == "S0"
        assert states[0].scroll_y == 0.0
        assert states[0].viewport_width == 390
        assert states[0].viewport_height == 844
        assert states[0].url.startswith("file://")

    @pytest.mark.parametrize("fixture_id", FIXTURE_IDS)
    def test_s0_carries_a_full_evidence_package(self, driver_factory: Any, fixture_id: str) -> None:
        """`03 §10` — DOM · AX · probe/CSS geometry · URL · control facts · screenshot."""
        driver = driver_factory(screenshots=True)
        payload = driver.capture_surface(make_contract(fixture_id))[0].payload
        assert payload.dom.strip().lower().startswith("<!doctype html>")
        assert payload.ax["nodes"], "AX tree 가 비어 있다"
        assert payload.probe["l0_probe"], "l0_probe 산출이 비어 있다"
        assert payload.probe["computed_css"], "computed CSS 가 비어 있다"
        assert payload.url.startswith("file://")
        assert payload.control_facts["state_index"] == "S0"
        assert payload.control_facts["environment"]["viewport_width_rendered"] == 390
        assert payload.screenshot is not None and len(payload.screenshot) > 0

    @pytest.mark.parametrize("fixture_id", FIXTURE_IDS)
    def test_probe_runs_in_fixture_mode_with_the_marker_path_open(
        self, driver_factory: Any, fixture_id: str
    ) -> None:
        """`D-R0-42` — `l0_probe.js` 에 실제 모드 문자열을 넘긴다.

        `marker_path_disabled=False` 만 보면 인자를 안 넘겼을 때(`undefined`)와 구분되지
        않는다. 그래서 아래 `test_the_probe_actually_reads_the_mode_argument` 가 같은
        probe 를 `REAL_TARGET` 로 직접 호출해 값이 뒤집히는 것을 보인다 — 그 대조가
        있어야 이 단언이 의미를 갖는다.
        """
        driver = driver_factory()
        probe = driver.capture_surface(make_contract(fixture_id))[0].payload.probe["l0_probe"]
        assert isinstance(probe, Mapping)
        signals = probe["raw_features"]["endpoint_signals"]
        assert signals["marker_path_disabled"] is False

    def test_the_probe_actually_reads_the_mode_argument(self, driver_factory: Any) -> None:
        """대조군 — 같은 probe 를 `REAL_TARGET` 로 호출하면 marker 경로가 닫힌다.

        `l0_probe.js` 를 **읽기만** 한다 (수정 없음, 파일로 쓰지도 않는다).
        네트워크 접속은 없다 — `file://` fixture 위에서 문자열 인자만 바꾼다.
        """
        driver = driver_factory()
        driver.capture_surface(make_contract("direct_text_button"))
        page = driver._session.page
        real = page.evaluate(_l0.PROBE_JS, "REAL_TARGET")
        assert real["raw_features"]["endpoint_signals"]["marker_path_disabled"] is True


# ═══════════════════════════════════════════════════════════════════════════
# 5. W5E 선언 좌표 ↔ 이 드라이버의 실측 bbox
# ═══════════════════════════════════════════════════════════════════════════


def _reveal_and_measure(driver: FixtureSessionDriver, fixture_id: str) -> RawTransition:
    entry = FIXTURE_ENTRIES[fixture_id]
    driver.capture_surface(make_contract(fixture_id))
    for selector in entry["entry_box_observed_after"] or ():
        revealed = driver.activate(PlannedAction("OPEN_GLOBAL_MENU", selector))
        assert revealed.ok, f"{fixture_id}: reveal step {selector} 실패 {revealed.failure_reason}"
    return driver.activate(PlannedAction("SELECT_FUNCTION", "#entry"))


OBSERVABLE_ENTRY_FIXTURES = tuple(
    fid for fid, e in FIXTURE_ENTRIES.items() if e["entry_box_observed_after"] is not None
)
UNOBSERVABLE_ENTRY_FIXTURES = tuple(
    fid for fid, e in FIXTURE_ENTRIES.items() if e["entry_box_observed_after"] is None
)


class TestDeclaredCoordinatesAgreeWithMeasurement:
    def test_the_two_groups_partition_the_set(self) -> None:
        assert len(OBSERVABLE_ENTRY_FIXTURES) + len(UNOBSERVABLE_ENTRY_FIXTURES) == 13
        assert set(UNOBSERVABLE_ENTRY_FIXTURES) == {"login_first_auth", "evidence_defect"}

    @pytest.mark.parametrize("fixture_id", OBSERVABLE_ENTRY_FIXTURES)
    def test_measured_entry_bbox_equals_the_declared_bbox(
        self, driver_factory: Any, fixture_id: str
    ) -> None:
        """무허용오차 대조. 갈리면 수집 결함이거나 fixture 결함이고 둘 다 보고 대상이다."""
        driver = driver_factory()
        transition = _reveal_and_measure(driver, fixture_id)
        declared = FIXTURE_ENTRIES[fixture_id]["entry_control_box_css_px"]
        assert transition.bbox_before == (
            declared["x"],
            declared["y"],
            declared["w"],
            declared["h"],
        ), f"{fixture_id}: 선언 {declared} ≠ 실측 {transition.bbox_before}"

    @pytest.mark.parametrize("fixture_id", UNOBSERVABLE_ENTRY_FIXTURES)
    def test_fixtures_declared_unobservable_really_are_unobservable(
        self, driver_factory: Any, fixture_id: str
    ) -> None:
        """음성 대조 — 이 둘은 좌표가 나오면 **안 된다**.

        `login_first_auth` 는 `#entry` 가 `hidden` 이고, `evidence_defect` 는 closed
        shadow root 안이라 `document.querySelector` 로 닿지 않는다. 둘 다 W5E 가
        `entry_box_observed_after: null` 로 선언한 그대로다.
        """
        driver = driver_factory()
        driver.capture_surface(make_contract(fixture_id))
        transition = driver.activate(PlannedAction("SELECT_FUNCTION", "#entry"))
        assert transition.ok is False
        assert transition.failure_reason is not None

    def test_entry_boxes_actually_differ_across_the_set(self, driver_factory: Any) -> None:
        """양성 대조 — 모든 fixture 에서 같은 좌표를 내는 코드도 위 테스트를 통과할 수 있다."""
        seen: set[tuple[float, ...]] = set()
        for fixture_id in OBSERVABLE_ENTRY_FIXTURES:
            driver = driver_factory()
            box = _reveal_and_measure(driver, fixture_id).bbox_before
            assert box is not None
            seen.add(box)
        assert len(seen) > 1, "실측 좌표가 전부 같다 — 상수를 돌려주는 코드와 구분되지 않는다"


# ═══════════════════════════════════════════════════════════════════════════
# 6. activate — before/after 가 실제로 다르다
# ═══════════════════════════════════════════════════════════════════════════

REVEAL_CASES = tuple(
    (fid, (FIXTURE_ENTRIES[fid]["entry_box_observed_after"] or [None])[0])
    for fid in ("hamburger", "left_drawer", "right_drawer", "bottom_sheet", "nested_menu")
)


class TestTransitionBeforeAfter:
    @pytest.mark.parametrize(("fixture_id", "selector"), REVEAL_CASES)
    def test_dom_hash_changes_across_an_activation(
        self, driver_factory: Any, fixture_id: str, selector: str
    ) -> None:
        driver = driver_factory()
        driver.capture_surface(make_contract(fixture_id))
        transition = driver.activate(PlannedAction("OPEN_GLOBAL_MENU", selector))
        assert transition.ok
        assert transition.payload_before is not None
        assert transition.payload_after is not None
        assert dom_hash(transition.payload_before) != dom_hash(transition.payload_after)

    def test_url_changes_across_a_navigating_activation(
        self, driver_factory: Any, tmp_path: Path
    ) -> None:
        """URL 축의 before/after 도 확인한다 — DOM 만 보면 항해를 놓친다."""
        write_page(tmp_path, "second.html", "<p id=done>도착</p>")
        start = write_page(tmp_path, "first.html", "<a id=go href='second.html'>이동</a>")
        driver = driver_factory(root=tmp_path)
        driver.capture_surface(make_contract("nav", start))
        transition = driver.activate(PlannedAction("SELECT_FUNCTION", "#go"))
        assert transition.ok
        assert transition.url_before.endswith("first.html")
        assert transition.url_after.endswith("second.html")
        assert transition.url_before != transition.url_after

    def test_a_no_op_activation_is_reported_as_failure_not_as_success(
        self, driver_factory: Any
    ) -> None:
        """음성 대조 — 무조건 `ok=True` 를 내는 구현과 구분한다."""
        driver = driver_factory()
        driver.capture_surface(make_contract("direct_text_button"))
        transition = driver.activate(PlannedAction("SELECT_FUNCTION", "#does-not-exist"))
        assert transition.ok is False
        assert transition.failure_reason == "CONTROL_NOT_FOUND"
        assert transition.payload_before is not None

    def test_activation_without_a_selector_is_refused(self, driver_factory: Any) -> None:
        driver = driver_factory()
        driver.capture_surface(make_contract("direct_text_button"))
        transition = driver.activate(PlannedAction("SELECT_FUNCTION", None))
        assert transition.ok is False
        assert transition.failure_reason == "NO_CONTROL_SELECTOR"

    def test_activate_before_capture_surface_is_fail_closed(self) -> None:
        driver = FixtureSessionDriver(fixture_root=FIXTURES_V3)
        with pytest.raises(SessionNotOpenError):
            driver.activate(PlannedAction("SELECT_FUNCTION", "#entry"))

    def test_failed_activation_still_keeps_before_evidence(self, driver_factory: Any) -> None:
        driver = driver_factory()
        driver.capture_surface(make_contract("login_first_auth"))
        transition = driver.activate(PlannedAction("SELECT_FUNCTION", "#entry"))
        assert transition.ok is False
        assert transition.payload_before is not None
        assert transition.payload_before.dom


# ═══════════════════════════════════════════════════════════════════════════
# 7. auth / endpoint 원시 신호 — 양·음성 대조를 같이 둔다
# ═══════════════════════════════════════════════════════════════════════════


class TestRawTerminalSignals:
    def test_auth_gate_is_detected_when_a_password_field_becomes_visible(
        self, driver_factory: Any
    ) -> None:
        driver = driver_factory()
        driver.capture_surface(make_contract("task_first_auth"))
        transition = driver.activate(PlannedAction("SELECT_FUNCTION", "#entry"))
        assert transition.ok
        assert transition.auth_gate_detected is True

    def test_auth_gate_is_not_detected_on_a_plain_task_control(self, driver_factory: Any) -> None:
        driver = driver_factory()
        driver.capture_surface(make_contract("direct_text_button"))
        transition = driver.activate(PlannedAction("SELECT_FUNCTION", "#entry"))
        assert transition.ok
        assert transition.auth_gate_detected is False

    def test_endpoint_marker_is_detected_when_the_page_declares_one(
        self, driver_factory: Any, tmp_path: Path
    ) -> None:
        """v3 fixture 13종에는 endpoint marker 가 없다 (known limitation) —
        신호 경로 자체는 marker 를 가진 임시 페이지로 양성 대조한다."""
        name = write_page(tmp_path, "ep.html", "<button id=go type=button>x</button>")
        (tmp_path / name).write_text(
            (tmp_path / name)
            .read_text(encoding="utf-8")
            .replace("<body>", "<body data-endpoint-reached='true'>"),
            encoding="utf-8",
        )
        driver = driver_factory(root=tmp_path)
        driver.capture_surface(make_contract("ep", name))
        transition = driver.activate(PlannedAction("SELECT_FUNCTION", "#go"))
        assert transition.ok
        assert transition.endpoint_signal_detected is True

    def test_endpoint_marker_absent_means_no_signal(self, driver_factory: Any) -> None:
        driver = driver_factory()
        driver.capture_surface(make_contract("direct_text_button"))
        transition = driver.activate(PlannedAction("SELECT_FUNCTION", "#entry"))
        assert transition.endpoint_signal_detected is False

    def test_no_v3_fixture_declares_an_endpoint_marker(self) -> None:
        """위 음성 대조가 왜 자명하지 않은지를 기록으로 남긴다."""
        marked = [
            path.name
            for path in sorted(FIXTURES_V3.glob("*.html"))
            if "data-endpoint" in path.read_text(encoding="utf-8")
        ]
        assert marked == []


# ═══════════════════════════════════════════════════════════════════════════
# 8. 안전 — credential 0회 + 안전 입력 양성 대조
# ═══════════════════════════════════════════════════════════════════════════


class TestCredentialCannotBeEntered:
    def test_page_fill_is_never_called_on_the_login_fixture(self, driver_factory: Any) -> None:
        """`login_first_auth.html` — 비밀번호 칸도, **아이디 칸도** 거부된다.

        아이디 칸(`#uid`)은 `type=text` 에 이름도 무해하다. 그것을 잡는 것은 금지어
        목록이 아니라 "password 입력을 품은 form 안" 이라는 구조 신호다.
        """
        driver = driver_factory()
        driver.capture_surface(make_contract("login_first_auth"))
        page = driver._session.page
        calls: list[tuple[Any, Any]] = []
        spy_on_fill(page, calls)

        for selector in ("#pw", "#uid"):
            with pytest.raises(CredentialInputRefusedError):
                driver.activate(PlannedAction("INPUT_QUERY", selector))
        assert calls == [], f"credential 필드에 fill 이 호출됐다: {calls}"

    def test_safe_search_input_really_receives_a_value(
        self, driver_factory: Any, tmp_path: Path
    ) -> None:
        """양성 대조 — 이것이 없으면 "아무것도 입력 못 하는 코드" 와 구분되지 않는다."""
        name = write_page(tmp_path, "search.html", "<form><input id=q name=q type=search></form>")
        driver = driver_factory(root=tmp_path)
        driver.capture_surface(make_contract("search", name))
        page = driver._session.page
        calls: list[tuple[Any, Any]] = []
        spy_on_fill(page, calls)

        transition = driver.activate(PlannedAction("INPUT_QUERY", "#q"))
        assert transition.ok
        assert len(calls) == 1
        assert calls[0][0] == ("#q", SAFE_PROBE_TEXT)
        assert page.input_value("#q") == SAFE_PROBE_TEXT

    def test_a_safe_input_inside_a_login_form_is_still_refused(
        self, driver_factory: Any, tmp_path: Path
    ) -> None:
        """구조 규칙의 경계를 직접 본다 — 같은 `type=search` 라도 로그인 폼 안이면 거부."""
        name = write_page(
            tmp_path,
            "mixed.html",
            "<form id=login><input id=inform type=search name=q>"
            "<input id=pw type=password name=pw></form>"
            "<form id=plain><input id=outform type=search name=q></form>",
        )
        driver = driver_factory(root=tmp_path)
        driver.capture_surface(make_contract("mixed", name))
        with pytest.raises(CredentialInputRefusedError):
            driver.activate(PlannedAction("INPUT_QUERY", "#inform"))
        assert driver.activate(PlannedAction("INPUT_QUERY", "#outform")).ok is True

    @pytest.mark.parametrize(
        "facts",
        [
            {"tag": "input", "type": "password"},
            {"tag": "input", "type": "text", "autocomplete": "one-time-code"},
            {"tag": "input", "type": "text", "name": "user_password"},
            {"tag": "input", "type": "text", "placeholder": "비밀번호"},
            {"tag": "input", "type": "text", "label_text": "인증번호"},
            {"tag": "input", "type": "text", "name": "uid", "password_scope": True},
            {"tag": "input", "type": "text", "name": "card_number"},
        ],
    )
    def test_credential_classifier_positive_cases(self, facts: dict[str, Any]) -> None:
        assert is_credential_field(facts) is True

    @pytest.mark.parametrize(
        "facts",
        [
            {"tag": "input", "type": "search", "name": "q"},
            {"tag": "input", "type": "text", "name": "keyword", "password_scope": False},
            {"tag": "textarea", "name": "memo"},
            {"tag": "select", "name": "origin"},
        ],
    )
    def test_credential_classifier_negative_cases(self, facts: dict[str, Any]) -> None:
        assert is_credential_field(facts) is False


class TestNoStructuralPathToForbiddenActions:
    def test_the_module_has_exactly_one_fill_call_site(self) -> None:
        tree = ast.parse(SESSION_SOURCE)
        sites = [
            node
            for node in ast.walk(tree)
            if isinstance(node, ast.FunctionDef) and "fill" in attribute_calls(node)
        ]
        assert [node.name for node in sites] == ["_fill_safe_text"]

    def test_the_only_fill_site_refuses_credentials_before_filling(self) -> None:
        node = function_node("_fill_safe_text")
        body = [stmt for stmt in node.body if not isinstance(stmt, ast.Expr)]
        guard = body[0]
        assert isinstance(guard, ast.If)
        assert "is_credential_field" in ast.unparse(guard.test)
        assert "CredentialInputRefusedError" in ast.unparse(guard)

    def test_the_filled_value_is_a_module_constant_not_a_parameter(self) -> None:
        node = function_node("_fill_safe_text")
        params = {arg.arg for arg in node.args.args}
        assert params == {"self", "session", "selector", "facts"}
        calls = [
            child
            for child in ast.walk(node)
            if isinstance(child, ast.Call)
            and isinstance(child.func, ast.Attribute)
            and child.func.attr == "fill"
        ]
        assert len(calls) == 1
        assert ast.unparse(calls[0].args[1]) == "SAFE_PROBE_TEXT"

    def test_planned_action_has_no_field_that_could_carry_a_secret(self) -> None:
        """호출자가 비밀번호를 **건네줄 자리 자체가 없다** (W5F 소유 dataclass)."""
        import dataclasses

        names = {f.name for f in dataclasses.fields(PlannedAction)}
        assert names == {
            "action_token",
            "control_selector",
            "control_role",
            "control_visible_text",
            "control_accessible_name",
        }

    @pytest.mark.parametrize(
        "banned",
        ["press_sequentially", "insert_text", "keyboard", "type", "set_input_files", "tap"],
    )
    def test_the_module_uses_no_other_input_channel(self, banned: str) -> None:
        tree = ast.parse(SESSION_SOURCE)
        assert banned not in set(attribute_calls(tree)), f"{banned} 경로가 생겼다"

    def test_the_module_never_names_real_target_mode(self) -> None:
        """코드 본문에 `REAL_TARGET` 이 없다. 모듈 docstring 의 설명 문장은 제외한다."""
        assert "REAL_TARGET" not in code_source()

    @pytest.mark.parametrize(
        "word", ["송금", "결제", "장바구니", "주문", "예약", "좌석", "CAPTCHA", "captcha"]
    )
    def test_no_forbidden_transaction_vocabulary_leaks_into_code(self, word: str) -> None:
        """금지 조작은 어휘로도 코드에 없다 — 문서(docstring/주석)는 제외한다."""
        offenders = [
            line
            for line in code_source().splitlines()
            if word in line and not line.lstrip().startswith("#")
        ]
        assert offenders == [], offenders


# ═══════════════════════════════════════════════════════════════════════════
# 9. 실사이트를 열 수 없다 — 두 겹
# ═══════════════════════════════════════════════════════════════════════════


class TestFixtureOnly:
    @pytest.mark.parametrize(
        "url",
        [
            "https://www.example.com/",
            "http://127.0.0.1:8000/",
            "ws://example.com/socket",
            "data:text/html,<p>x</p>",
        ],
    )
    def test_non_file_starting_urls_are_blocked_before_any_navigation(
        self, driver_factory: Any, url: str
    ) -> None:
        driver = driver_factory()
        with pytest.raises(NavigationBlockedError):
            driver.capture_surface(make_contract("blocked", url))

    def test_a_file_url_outside_the_fixture_root_is_blocked(
        self, driver_factory: Any, tmp_path: Path
    ) -> None:
        outside = tmp_path / "outside.html"
        outside.write_text("<html><body>x</body></html>", encoding="utf-8")
        driver = driver_factory()
        with pytest.raises(NavigationBlockedError):
            driver.capture_surface(make_contract("outside", outside.resolve().as_uri()))

    def test_context_level_route_blocks_network_requests_from_inside_a_fixture(
        self, driver_factory: Any, tmp_path: Path
    ) -> None:
        """firewall 은 **내가 여는 URL** 만 본다. 페이지가 스스로 나가는 경로는 별개다."""
        name = write_page(tmp_path, "leak.html", "<p id=x>x</p>")
        driver = driver_factory(root=tmp_path)
        driver.capture_surface(make_contract("leak", name))
        page = driver._session.page
        blocked = page.evaluate(
            "async () => { try { await fetch('https://example.com/'); return 'ALLOWED'; }"
            " catch (e) { return 'BLOCKED'; } }"
        )
        assert blocked == "BLOCKED"

    def test_the_driver_has_no_execution_mode_parameter(self) -> None:
        import inspect

        params = set(inspect.signature(FixtureSessionDriver.__init__).parameters)
        assert "execution_mode" not in params
        assert "scope" not in params
        assert "execution_scope" not in params
        assert FixtureSessionDriver.EXECUTION_MODE.value == "FIXTURE"


# ═══════════════════════════════════════════════════════════════════════════
# 10. Δ8-R5 input_mode — 관측이며 기록용 메타데이터가 아니다
# ═══════════════════════════════════════════════════════════════════════════

INPUT_MODE_MARKUP = (
    "<form>"
    "<input id=free type=text name=keyword>"
    "<select id=drop name=origin><option>가</option><option>나</option></select>"
    "<input id=mix type=text name=city list=cities>"
    "<datalist id=cities><option value=서울></datalist>"
    "<div id=map role=application style='width:200px;height:200px'></div>"
    "<button id=other type=button>조회</button>"
    "</form>"
)


class TestInputModeObservation:
    @pytest.mark.parametrize(
        ("facts", "expected"),
        [
            ({"tag": "input", "type": "text"}, FixtureInputMode.FREE_TEXT),
            ({"tag": "textarea"}, FixtureInputMode.FREE_TEXT),
            ({"tag": "select"}, FixtureInputMode.DROPDOWN),
            ({"tag": "ul", "role": "listbox"}, FixtureInputMode.DROPDOWN),
            ({"tag": "input", "type": "text", "has_datalist": True}, FixtureInputMode.MIXED),
            ({"tag": "div", "role": "combobox"}, FixtureInputMode.MIXED),
            ({"tag": "div", "role": "application"}, FixtureInputMode.MAP_PAN),
            ({"tag": "button"}, FixtureInputMode.OTHER),
            ({"tag": "a", "role": "link"}, FixtureInputMode.OTHER),
            ({"tag": "p"}, None),
            ({"tag": "input", "type": "hidden"}, None),
        ],
    )
    def test_structural_signals_decide_the_mode(
        self, facts: dict[str, Any], expected: FixtureInputMode | None
    ) -> None:
        """라벨/문구는 보지 않는다 — A 규칙 "수집자가 고르지 않는다"."""
        assert observe_input_mode(facts) is expected

    def test_label_text_never_changes_the_observed_mode(self) -> None:
        """음성 대조 — "지도로 선택" 같은 문구가 MAP_PAN 을 만들어내지 않는다."""
        assert observe_input_mode({"tag": "button", "visible_text": "지도에서 출발지 선택"}) is (
            FixtureInputMode.OTHER
        )
        assert observe_input_mode({"tag": "input", "type": "text", "placeholder": "지도"}) is (
            FixtureInputMode.FREE_TEXT
        )

    @pytest.mark.parametrize(
        ("selector", "expected"),
        [
            ("#free", "FREE_TEXT"),
            ("#drop", "DROPDOWN"),
            ("#mix", "MIXED"),
            ("#map", "MAP_PAN"),
            ("#other", "OTHER"),
        ],
    )
    def test_all_five_vocabulary_values_are_observed_from_a_rendered_page(
        self, driver_factory: Any, tmp_path: Path, selector: str, expected: str
    ) -> None:
        """5값 전부를 **렌더된 DOM 에서** 관측한다 (표 단위 단위테스트와 별개)."""
        name = write_page(tmp_path, "modes.html", INPUT_MODE_MARKUP)
        driver = driver_factory(root=tmp_path)
        driver.capture_surface(make_contract("modes", name))
        transition = driver.activate(PlannedAction("SELECT_ORIGIN", selector))
        payload = transition.payload_after or transition.payload_before
        assert payload is not None
        assert payload.control_facts["observed_input_mode"] == expected

    def test_conditional_tokens_carry_the_actual_means_used(
        self, driver_factory: Any, tmp_path: Path
    ) -> None:
        name = write_page(tmp_path, "modes2.html", INPUT_MODE_MARKUP)
        driver = driver_factory(root=tmp_path)
        driver.capture_surface(make_contract("modes2", name))
        assert driver.activate(PlannedAction("SELECT_ORIGIN", "#free")).input_mode == "FREE_TEXT"
        assert driver.activate(PlannedAction("SELECT_DATE", "#drop")).input_mode == "DROPDOWN"
        # MIXED control 에서 실제로 쓰인 수단은 자유입력이었다 — Δ9 는 실사용 수단을 묻는다.
        mixed = driver.activate(PlannedAction("SELECT_DESTINATION", "#mix"))
        assert mixed.input_mode == "FREE_TEXT"
        payload = mixed.payload_after
        assert payload is not None
        assert payload.control_facts["observed_input_mode"] == "MIXED"
        assert payload.control_facts["used_input_mode"] == "FREE_TEXT"

    def test_non_conditional_tokens_record_no_input_mode(
        self, driver_factory: Any, tmp_path: Path
    ) -> None:
        """Δ9 는 세 토큰에만 묻는다. 다른 step 에 수단을 실으면 근거가 아니라 잡음이다."""
        name = write_page(tmp_path, "modes3.html", INPUT_MODE_MARKUP)
        driver = driver_factory(root=tmp_path)
        driver.capture_surface(make_contract("modes3", name))
        transition = driver.activate(PlannedAction("SELECT_FUNCTION", "#other"))
        assert transition.ok
        assert transition.input_mode is None

    def test_recorded_modes_are_always_inside_the_w5f_vocabulary(
        self, driver_factory: Any, tmp_path: Path
    ) -> None:
        """`OTHER` 는 Δ8-R5 어휘지만 W5F `INPUT_MODE_VALUES` 밖이다 — 실리면 runner 가 터진다."""
        assert "OTHER" not in INPUT_MODE_VALUES
        name = write_page(tmp_path, "modes4.html", INPUT_MODE_MARKUP)
        driver = driver_factory(root=tmp_path)
        driver.capture_surface(make_contract("modes4", name))
        for token in sorted(DEPTH_CONDITIONAL_TOKENS):
            for selector in ("#free", "#drop", "#mix", "#other"):
                transition = driver.activate(PlannedAction(token, selector))
                assert transition.input_mode is None or transition.input_mode in INPUT_MODE_VALUES

    def test_map_pan_is_observed_but_not_driven(self, driver_factory: Any, tmp_path: Path) -> None:
        """known limitation 을 테스트로 고정한다 — pan/zoom 구동 경로를 만들지 않았다."""
        name = write_page(tmp_path, "modes5.html", INPUT_MODE_MARKUP)
        driver = driver_factory(root=tmp_path)
        driver.capture_surface(make_contract("modes5", name))
        transition = driver.activate(PlannedAction("SELECT_ORIGIN", "#map"))
        assert transition.ok is False
        assert transition.failure_reason == "MAP_PAN_NOT_DRIVABLE"
        payload = transition.payload_before
        assert payload is not None
        assert payload.control_facts["observed_input_mode"] == "MAP_PAN"

    def test_the_driver_reuses_the_w5d1_vocabulary_object(self) -> None:
        assert session_module.FixtureInputMode is FixtureInputMode
        assert {m.value for m in FixtureInputMode} == {
            "FREE_TEXT",
            "DROPDOWN",
            "MIXED",
            "MAP_PAN",
            "OTHER",
        }


# ═══════════════════════════════════════════════════════════════════════════
# 11. runner 통합 — 이 드라이버로 `V3Runner.run()` 이 실제로 돈다
# ═══════════════════════════════════════════════════════════════════════════


class _FakeHasher:
    def task_contract_hash(self, contract: TaskContract) -> str:
        return contract.task_contract_hash

    def endpoint_contract_hash(self, contract: TaskContract) -> str:
        return contract.endpoint_contract_hash


class _RecordingSafety:
    def __init__(self) -> None:
        self.seen: list[str] = []

    def assert_action_allowed(self, contract: TaskContract, action: PlannedAction) -> None:
        self.seen.append(action.action_token)


class _ScriptedScout:
    def __init__(self, plan: Sequence[PlannedAction]) -> None:
        self._plan = tuple(plan)

    def propose_next(
        self,
        contract: TaskContract,
        states: Sequence[SurfaceObservation],
        candidates: Sequence[Mapping[str, Any]],
        taken: Sequence[Any],
    ) -> PlannedAction | None:
        return self._plan[len(taken)] if len(taken) < len(self._plan) else None


class TestRunnerIntegration:
    def test_v3runner_runs_end_to_end_on_a_fixture(
        self, driver_factory: Any, tmp_path: Path
    ) -> None:
        from landing_accessibility.v3_runner.runner import Phase, ReplayStatus, V3Runner

        safety = _RecordingSafety()
        runner = V3Runner(
            evidence_root=tmp_path / "evidence",
            contract_hasher=_FakeHasher(),
            safety=safety,
            scout=_ScriptedScout(
                [
                    PlannedAction("OPEN_GLOBAL_MENU", "#open"),
                    PlannedAction("SELECT_FUNCTION", "#entry"),
                ]
            ),
        )
        driver = driver_factory()
        result = runner.run(
            make_contract("hamburger", mobile_web_eligibility=ELIGIBILITY_PROCEEDABLE),
            driver=driver,
            run_id="w5h-integration-1",
        )

        assert result.phase_reached is Phase.MART
        assert [s.state_index for s in result.raw_states] == ["S0"]
        assert [s.action_token for s in result.raw_steps] == [
            "OPEN_GLOBAL_MENU",
            "SELECT_FUNCTION",
        ]
        assert result.replay_status is ReplayStatus.REPLAYED
        assert safety.seen  # runner 가 activate 전에 safety 를 통과시킨다
        assert result.evidence_manifest_sha256
        assert result.evidence_run_dir is not None and result.evidence_run_dir.exists()

    def test_evidence_files_land_on_disk_for_every_state_and_step(
        self, driver_factory: Any, tmp_path: Path
    ) -> None:
        from landing_accessibility.v3_runner.runner import V3Runner

        runner = V3Runner(
            evidence_root=tmp_path / "evidence",
            contract_hasher=_FakeHasher(),
            safety=_RecordingSafety(),
            scout=_ScriptedScout([PlannedAction("OPEN_GLOBAL_MENU", "#open")]),
        )
        driver = driver_factory(screenshots=True)
        result = runner.run(
            make_contract("left_drawer", mobile_web_eligibility=ELIGIBILITY_PROCEEDABLE),
            driver=driver,
            run_id="w5h-evidence-1",
        )
        run_dir = result.evidence_run_dir
        assert run_dir is not None
        assert (run_dir / "s000" / "dom.html").exists()
        assert (run_dir / "s000" / "ax.json").exists()
        assert (run_dir / "s000" / "screenshot.png").exists()
        assert (run_dir / "step0000_before" / "control_facts.json").exists()
        assert (run_dir / "step0000_after" / "control_facts.json").exists()
        assert (run_dir / "manifest.jsonl").exists()

    def test_a_broken_selector_is_reported_as_replay_broken_not_as_a_crash(
        self, driver_factory: Any, tmp_path: Path
    ) -> None:
        """`03 §5` — 깨진 path 는 기록으로 남아야 한다. 예외로 터지면 그 기록이 없다."""
        from landing_accessibility.v3_runner.runner import V3Runner

        runner = V3Runner(
            evidence_root=tmp_path / "evidence",
            contract_hasher=_FakeHasher(),
            safety=_RecordingSafety(),
        )
        driver = driver_factory()
        driver.capture_surface(make_contract("hamburger"))
        manifest = {
            "steps": [{"action_token": "SELECT_FUNCTION", "control_selector": "#nope"}],
        }
        result = runner.replay(
            make_contract("hamburger"),
            driver=driver,
            manifest=manifest,
            declared_sha256=path_manifest_sha256(manifest),
            run_id="w5h-broken-1",
        )
        assert result.replay_failure_reason == "CONTROL_NOT_FOUND"
        assert result.endpoint_status is None


# ═══════════════════════════════════════════════════════════════════════════
# 12. 코디네이터가 지적한 두 공백 — 없는 것을 없다고 고정한다
# ═══════════════════════════════════════════════════════════════════════════

ENGINE = RESEARCH / "src" / "landing_accessibility" / "engine"


class TestAxNodeJoinIsAbsent:
    """`l0_probe.js` 는 accessible name 을 **계산하지 않는다** — 출처만 낸다.

    계산된 이름은 CDP slim node 에만 있고 그 노드는 `backendDOMNodeId` 로 키잉된다.
    selector ↔ backendDOMNodeId 조인이 **이 lane 이 갈라져 나온 base 에** 없었으므로
    W5C 가 요구하는 `ax_node` 를 이 드라이버는 채울 수 없다. **추정으로 채우지 않는다**
    — 그러면 W5C 가 피한 결함을 도로 만든다.

    W5M 주: 그 조인은 그 뒤 W5I 가 engine 에 만들었다(`8fcf540`). 그래도 **이 드라이버는**
    여전히 조인을 하지 않으며 슬롯은 `None` 이다. 이 클래스가 고정하는 것은 "조인이
    세상에 없다" 가 아니라 "이 드라이버가 조인 없이 슬롯을 비워 두는 근거" 다.
    """

    def test_the_ax_node_slot_exists_and_is_empty_with_a_reason(self, driver_factory: Any) -> None:
        driver = driver_factory()
        payload = driver.capture_surface(make_contract("icon_only_ax_named"))[0].payload
        assert "ax_node" in payload.control_facts
        assert payload.control_facts["ax_node"] is None
        assert payload.control_facts["ax_node_join_status"] == AX_NODE_JOIN_STATUS

    def test_transition_payloads_carry_the_same_empty_slot(self, driver_factory: Any) -> None:
        driver = driver_factory()
        driver.capture_surface(make_contract("hamburger"))
        transition = driver.activate(PlannedAction("OPEN_GLOBAL_MENU", "#open"))
        for payload in (transition.payload_before, transition.payload_after):
            assert payload is not None
            assert payload.control_facts["ax_node"] is None

    def test_the_driver_never_synthesises_an_accessible_name(self) -> None:
        """구조적 확인 — 이름을 계산하는 이름 자체가 이 모듈에 없다."""
        for banned in ("accessible_name", "compute_name", "accname"):
            assert banned not in SESSION_SOURCE, f"{banned} 가 session.py 에 생겼다"

    def test_the_join_was_absent_at_the_base_this_lane_forked_from(self) -> None:
        """W5H 가 슬롯을 비워 둔 **근거**를 base 커밋에서 고정한다.

        ## W5M 시정 — 이 단언은 이제 승인된 산출물의 부정을 주장하고 있었다

        원래 이 테스트는 **작업 트리의** `l0_collector.py` 에 selector 와
        `backendDOMNodeId` 가 같은 줄에 있는 줄이 없다고 주장했고, 병합에서 깨졌다:

            `[인용]` ``AssertionError: ['                # ── W5I: selector <->
            backendDOMNodeId <-> AX slim node ────']``

        매치된 것은 코드가 아니라 W5I 의 주석 한 줄이었다. **그렇다고 주석을 걸러내는
        것은 답이 아니다.** 걸러내면 이 테스트는 초록불이 되지만 그때 주장하는 명제가
        거짓이다 — 조인은 실재한다:

            `[인용]` `engine/l0_collector.py`: ``payload = collect_ax_join(cdp,
            probe=probe, ax_nodes=ax)``

        W5I 의 과업이 그 조인을 만드는 것이었고(`8fcf540`, +37/-0) A 가 승인했다. 주석
        필터는 "조인이 없다" 라는 **거짓 명제를 조용히 통과**시키는 장치일 뿐이다.

        소유를 W5I 로 넘기는 것도 답이 아니다. W5I 는 "조인이 있다" 를 자기 테스트에서
        이미 증명한다(`test_w5i_ax_join.py`). 여기서 필요한 것은 그 반대 명제가 아니라
        **W5H 가 슬롯을 비워 둔 판단의 근거** — 즉 *W5H 가 갈라져 나온 시점의 base 에는*
        조인이 없었다는 사실이다. 그것은 지금도 참이고, 앞으로 어떤 lane 이 engine 을
        고쳐도 참으로 남는다. 그래서 작업 트리가 아니라 base 커밋을 읽는다.
        """
        collector = _base_engine_text("l0_collector.py")
        probe = _base_engine_text("l0_probe.js")
        assert "backendDOMNodeId" in collector  # 양성 대조 — 못 찾는 grep 이 아니다
        assert "backendDOMNodeId" not in probe  # probe 쪽에는 키가 아예 없다
        assert _join_lines(collector) == [], _join_lines(collector)

    def test_the_join_detector_is_not_a_grep_that_finds_nothing(self) -> None:
        """음성 대조 — 조인이 있으면 위 계기가 **반드시 잡는다**.

        base 에서 빈 결과가 나온 것이 "조인이 없어서" 인지 "계기가 고장 나서" 인지
        구분하려면 이 대조가 있어야 한다. 저장소 상태에 의존하지 않도록 합성 문자열로
        건다 — 어느 lane 이 engine 을 어떻게 고치든 이 대조는 흔들리지 않는다.
        """
        injected = "\n".join(
            [
                "def join(probe, ax):",
                "    return {selector: backendDOMNodeId for selector, backendDOMNodeId in rows}",
            ]
        )
        assert _join_lines(injected) != []
        assert _join_lines("selector 만 있는 줄") == []
        assert _join_lines("backendDOMNodeId 만 있는 줄") == []

    def test_this_driver_still_does_not_do_the_join_itself(self) -> None:
        """W5I 가 engine 에 조인을 만든 뒤에도 **이 드라이버는** 조인을 하지 않는다.

        W5H 의 선언된 한계(`W5H-L1-AX-JOIN-ABSENT`)가 살아 있다는 뜻이다. 이 lane 이
        조용히 조인을 끌어다 쓰기 시작하면 여기서 잡힌다.

        줄 단위 grep 을 쓰지 않는다 — `session.py` 자신의 docstring 이 selector 와
        `backendDOMNodeId` 를 한 줄에 적고 있어(한계를 설명하는 산문) 같은 함정에 걸린다.
        A-1 과 같은 실수를 여기서 반복하지 않으려고 **AST 로 import 와 호출만** 본다.
        """
        tree = ast.parse(SESSION_SOURCE)
        imported: list[str] = []
        called: list[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported += [a.name for a in node.names]
            elif isinstance(node, ast.ImportFrom):
                imported += [f"{node.module or ''}.{a.name}" for a in node.names]
            elif isinstance(node, ast.Call):
                func = node.func
                if isinstance(func, ast.Name):
                    called.append(func.id)
                elif isinstance(func, ast.Attribute):
                    called.append(func.attr)
        assert not [n for n in imported if "ax_join" in n], imported
        assert "collect_ax_join" not in called, called
        assert AX_NODE_JOIN_STATUS == "AX_NODE_ABSENT_NO_SELECTOR_TO_BACKEND_NODE_JOIN"

    def test_the_ast_check_would_notice_the_driver_taking_the_join_up(self) -> None:
        """음성 대조 — 위 AST 계기가 조인 도입을 실제로 잡는다.

        `session.py` 에 조인이 들어온 형태를 합성해 같은 계기에 건다. 잡히지 않으면 위
        테스트의 초록불은 "안 한다" 가 아니라 "못 본다" 다.
        """
        injected = ast.parse(
            "from ..v3_runner.ax_join import collect_ax_join\n"
            "def f(cdp, probe, ax):\n"
            "    return collect_ax_join(cdp, probe=probe, ax_nodes=ax)\n"
        )
        imported: list[str] = []
        called: list[str] = []
        for node in ast.walk(injected):
            if isinstance(node, ast.ImportFrom):
                imported += [f"{node.module or ''}.{a.name}" for a in node.names]
            elif isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                called.append(node.func.id)
        assert [n for n in imported if "ax_join" in n]
        assert "collect_ax_join" in called


class TestScrollEnumerationIsMineNotTheEngines:
    """scroll 열거는 이 드라이버 안에 있다 — 소유 밖 파일을 고치지 않았다."""

    def test_this_lane_does_not_touch_the_engine(self) -> None:
        """이 lane 의 **자기 diff** 안에 engine 파일이 하나도 없다.

        W5M 시정. 원래는 ``git diff --name-only HEAD`` — **작업 트리 vs HEAD** 를 쟀다.
        커밋하고 나면 무조건 빈 문자열이라 병합 뒤에는 무엇도 잡지 못한다. 시끄럽게
        깨지지는 않았지만 이미 조용한 통과였다.

        지금은 W5H 브랜치가 base 이후 만든 diff(+ 미커밋 작업 트리 변경)를 본다.
        음성 대조는 `test_the_same_measurement_catches_w5i_which_did_touch_the_engine`.
        """
        changed = lane_changed_paths(W5H_BRANCH)
        assert changed, "diff 가 비면 계기가 죽은 것이다"
        offenders = paths_under(changed, ENGINE_DIR)
        assert offenders == (), f"이 lane 이 engine 을 고쳤다: {offenders}"

    def test_the_same_measurement_catches_w5i_which_did_touch_the_engine(self) -> None:
        """음성 대조 — engine 을 실제로 고친 lane 을 같은 계기로 재면 잡힌다."""
        theirs = paths_under(lane_committed_paths("claude-b/w5i-ax-join"), ENGINE_DIR)
        assert theirs == (f"{ENGINE_DIR}/l0_collector.py",), theirs
        assert paths_under(lane_committed_paths(W5H_BRANCH), ENGINE_DIR) == ()

    def test_scroll_enumeration_lives_in_the_driver(self) -> None:
        node = function_node("capture_surface")
        source = ast.unparse(node)
        assert "_SCROLL_TO_JS" in source
        assert "L0Collector" not in source, "engine 수집기에 scroll 열거를 위임하지 않는다"

    def test_every_v3_fixture_is_unscrollable_so_only_s0_exists(self, driver_factory: Any) -> None:
        """측정 근거 — 13/13 이 스크롤되지 않는다. 그래서 이 집합의 S0-only 는 결함이 아니다."""
        for fixture_id in FIXTURE_IDS:
            driver = driver_factory()
            states = driver.capture_surface(make_contract(fixture_id))
            scroll = states[0].payload.probe["scroll"]
            assert scroll["scroll_height"] == scroll["client_height"] == 844, fixture_id
            assert [s.state_index for s in states] == ["S0"], fixture_id

    def test_the_same_code_path_yields_s1_upward_on_a_scrollable_document(
        self, driver_factory: Any, tmp_path: Path
    ) -> None:
        """양성 대조 — 위 테스트가 "항상 S0 하나만 내는 코드" 와 구분되게 한다."""
        name = write_page(
            tmp_path, "scrollable.html", "<div style='height:3000px;background:#eee'></div>"
        )
        driver = driver_factory(root=tmp_path)
        states = driver.capture_surface(make_contract("scrollable", name))
        assert len(states) >= 3
        assert states[1].scroll_y > states[0].scroll_y

    def test_the_policy_can_be_pinned_to_s0_only_without_a_code_change(
        self, driver_factory: Any, tmp_path: Path
    ) -> None:
        """B 가 S0-only 로 동결하기로 하면 생성자 인자 하나로 끝난다."""
        name = write_page(
            tmp_path, "scrollable2.html", "<div style='height:3000px;background:#eee'></div>"
        )
        driver = driver_factory(root=tmp_path, scroll_policy=ScrollPolicy(max_states=1))
        states = driver.capture_surface(make_contract("scrollable2", name))
        assert [s.state_index for s in states] == ["S0"]


class TestKnownLimitationsAreDeclared:
    def test_each_limitation_separates_measurement_from_judgement(self) -> None:
        assert {item["basis"] for item in KNOWN_LIMITATIONS} == {"MEASURED", "JUDGEMENT"}
        ids = [item["id"] for item in KNOWN_LIMITATIONS]
        assert len(ids) == len(set(ids))
        assert "W5H-L1-AX-JOIN-ABSENT" in ids
        assert "W5H-L2-V3-FIXTURES-DO-NOT-SCROLL" in ids

    def test_the_map_pan_limitation_is_marked_as_a_judgement_not_a_measurement(self) -> None:
        by_id = {item["id"]: item for item in KNOWN_LIMITATIONS}
        assert by_id["W5H-L4-MAP-PAN-NOT-DRIVEN"]["basis"] == "JUDGEMENT"
        assert by_id["W5H-L3-OTHER-OUTSIDE-W5F-VOCABULARY"]["basis"] == "MEASURED"
