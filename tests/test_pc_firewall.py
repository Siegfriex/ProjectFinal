"""P-C LANE C — REAL-TARGET FIREWALL (`PHASE_GATES.md §4.5`).

이 파일이 지키는 것은 스키마의 모양이 아니라 **한 번 뚫리면 연구 전체가 무효가 되는 경계**다.

P0(`V2_SSOT_FROZEN`)가 닫히기 전에 실제 서비스에 접속해 접근성 결과를 만들면
`PHASE_GATES §4.1` 2~5항 위반이고 `§4.6` 에 따라 P0 finding 이 된다.
그래서 "REAL_TARGET 은 실패한다" 를 문서가 아니라 테스트가 고정한다.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
RESEARCH = REPO / "research" / "landing_accessibility"
sys.path.insert(0, str(RESEARCH / "src"))

from landing_accessibility.engine.firewall import (  # noqa: E402
    MODES_ALLOWED_BEFORE_P0,
    ExecutionMode,
    NavigationBlockedError,
    RealTargetBlockedError,
    UnknownExecutionModeError,
    assert_mode_allowed,
    assert_navigation_allowed,
    firewall_state,
    p0_closed,
    real_target_permitted,
)

FIXTURES = RESEARCH / "fixtures"


def test_unlimited_real_target_is_never_permitted_even_after_the_gate_closed() -> None:
    """P0 게이트 상수가 CLOSED 로 전이돼도 **무제한** REAL_TARGET 은 열리지 않는다.

    2026-08-27 승격으로 `P0_GATE_STATUS` 는 `CLOSED` 다. 그럼에도
    `real_target_permitted()` 는 영구히 `False` 다 — 실제 수집은 승인된
    `ExecutionScope` 를 통해 범위가 좁혀진 상태로만 일어나고, 그 판정은 이 상수가
    아니라 런타임 릴리스 문서가 내린다 (`test_e000_real_target_scope_gate.py`).
    """
    assert p0_closed() is True
    assert real_target_permitted() is False


@pytest.mark.parametrize("value", [ExecutionMode.REAL_TARGET, "REAL_TARGET"])
def test_real_target_is_hard_fail(value: object) -> None:
    with pytest.raises(RealTargetBlockedError):
        assert_mode_allowed(value)


def test_real_target_navigation_is_blocked_before_url_is_even_parsed() -> None:
    with pytest.raises(RealTargetBlockedError):
        assert_navigation_allowed("REAL_TARGET", "https://www.example.co.kr/")


@pytest.mark.parametrize(
    "url",
    [
        "https://www.example.co.kr/",
        "http://example.com",
        "ws://example.com/socket",
        "data:text/html,<h1>x</h1>",
        "//example.com",
    ],
)
def test_fixture_mode_refuses_every_non_file_scheme(url: str) -> None:
    """네트워크로 나가는 scheme 은 전부 차단이다 — 이 목록이 방화벽의 실제 표면이다."""
    with pytest.raises(NavigationBlockedError):
        assert_navigation_allowed(ExecutionMode.FIXTURE, url)


def test_shadow_dry_run_never_navigates() -> None:
    """dry-run 이 조용히 수집기가 되는 경로를 막는다."""
    target = FIXTURES / "simple_article.html"
    with pytest.raises(NavigationBlockedError):
        assert_navigation_allowed(ExecutionMode.SHADOW_DRY_RUN, f"file://{target}")


def test_unknown_mode_fails_instead_of_defaulting() -> None:
    """A2 규칙 S-3 — 모르는 값을 UNKNOWN 으로 흡수하지 않는다."""
    for value in ("LIVE", "", None, 3):
        with pytest.raises(UnknownExecutionModeError):
            assert_mode_allowed(value)


def test_fixture_mode_allows_files_inside_the_fixture_root() -> None:
    target = FIXTURES / "simple_article.html"
    resolved = assert_navigation_allowed(
        ExecutionMode.FIXTURE, f"file://{target}", fixture_root=FIXTURES
    )
    assert resolved.startswith("file://")
    assert resolved.endswith("simple_article.html")


def test_fixture_mode_refuses_files_outside_the_fixture_root() -> None:
    with pytest.raises(NavigationBlockedError):
        assert_navigation_allowed(
            ExecutionMode.FIXTURE, "file:///etc/passwd", fixture_root=FIXTURES
        )


def test_allowed_mode_set_matches_phase_gates_table() -> None:
    assert {ExecutionMode.FIXTURE, ExecutionMode.SHADOW_DRY_RUN} == MODES_ALLOWED_BEFORE_P0
    assert ExecutionMode.REAL_TARGET not in MODES_ALLOWED_BEFORE_P0


def test_firewall_state_reports_no_real_target_measurement() -> None:
    state = firewall_state()
    assert state["real_target_permitted"] is False
    assert state["real_target_measurement"] is False
    assert state["fixture_only"] is True
    # scope 를 주지 않은 스냅샷은 언제나 fixture-only 다. 게이트 상수는 2026-08-27
    # 승격으로 CLOSED 이며, 그 전이가 이 스냅샷의 다른 값을 바꾸지 않는다는 것이 요점이다.
    assert state["p0_gate_status"] == "CLOSED"


def test_engine_source_contains_no_network_scheme_literals() -> None:
    """엔진 어디에도 실제 서비스로 나가는 URL 리터럴이 없어야 한다.

    방화벽은 호출 경로를 막지만, 코드 안에 타겟 URL 이 박혀 있다는 것 자체가
    real-target 수집을 준비했다는 신호다. 그런 흔적이 남지 않게 고정한다.
    """
    engine = RESEARCH / "src" / "landing_accessibility" / "engine"
    offenders: list[str] = []
    for path in sorted(engine.rglob("*.py")):
        for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if "https://" in line or "http://" in line:
                # scheme 을 **거부 목록으로** 나열하는 줄은 허용한다 — 그것이 방화벽 자신이다.
                # 금지되는 것은 특정 서비스를 가리키는 URL 이 코드에 박히는 것이다.
                if any(k in line for k in ("scheme", "example", "차단", "금지")):
                    continue
                offenders.append(f"{path.name}:{lineno}: {line.strip()}")
    assert not offenders, f"엔진에 네트워크 URL 리터럴이 있다: {offenders}"
