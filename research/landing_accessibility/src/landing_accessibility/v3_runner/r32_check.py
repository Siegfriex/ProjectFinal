"""W5P — `R32`(선택적 입력의 **세 상태**) 적용 지점 검사기.

정본: `control/v3/V3_0_1_SUCCESSOR_DELTA.md` `Δ39`.

    부재(호출자가 주지 않았다)   → 관측이다. `None` + 사유 note
    형태 위반(줬는데 계약과 다르다) → 계약 위반이다. raise
    존재                          → 값

이 모듈은 `docs/v3/R32_APPLICATION_POINTS.md` 의 목록이 **코드와 어긋나면 실패**하게
만든다. 목록을 손으로 적은 표로 두면 코드가 바뀌어도 표는 그대로이고, 그 표를 근거로
"열거했다"고 말하게 된다. 그래서 세 층으로 닫는다.

층 1 — 행동 오라클 (`_probes`)
    각 지점을 **부재 상태로 한 번, 형태 위반 상태로 한 번** 실제로 호출하고 두 출력을
    비교한다. 같으면 `R32_VIOLATION`, 형태 위반이 예외를 내면 `R32_OK`, 부재 자체가
    예외면 `ABSENCE_NOT_TOLERATED`. **판정을 사람이 적지 않고 기계가 계산한다.**
    문서가 적은 판정과 다르면 실패다.

    한 지점이 **여러 코드 경로**를 가지면 경로마다 case 를 둔다 (`Probe.cases`).
    `ax_node` 가 그 예다 — DOM 에서 control 을 찾은 경로에서는 부재와 형태 위반이
    갈리지만, 못 찾은 경로에서는 **완전히 같은 출력**이다. 경로를 하나만 재면
    위반을 놓친다 (실제로 이 검사기의 첫 판이 그렇게 놓쳤다).

대조군 (`CONTROLS`)
    `must_flag` — 반드시 `R32_VIOLATION` 으로 잡혀야 하는 지점.
    `must_not_flag` — 잡히면 **안 되는** 지점(이미 R32 를 지킨다).
    이름을 "양성/음성" 으로 쓰지 않는다 — 이 프로젝트에서 그 말이 이미 두 뜻으로
    쓰였다 (A `Δ40`).

층 2 — 구조 검사
    문서의 모든 행에 대해 파일·함수·키(또는 매개변수)가 **실재하는지** 확인한다.
    함수 이름이 바뀌거나 키가 사라지면 실패한다.

층 3 — 표류 검사 (AST 전수 열거)
    `v3_runner/*.py` 를 다시 훑어 후보를 열거하고, **문서에 없는 후보가 있으면 실패**
    한다. 코드에 새 선택적 입력이 생기면 목록이 자동으로 낡는 것을 막는다.

한계 (정직하게)
    층 1 은 **offline 순수 호출이 가능한 지점만** 덮는다. `load_task_registry` 처럼
    전체 manifest 가 필요한 지점은 층 2/3 만 걸리고 판정은 사람이 코드를 읽어 적었다
    (`판정근거=READ`). 어느 행이 기계 판정이고 어느 행이 사람 판정인지는 문서의
    `판정근거` 열과 이 검사기의 출력이 함께 밝힌다.

    층 3 의 전수 범위 = `v3_runner/*.py` 14개 파일의 **모듈 공개 함수/메서드**와,
    그 함수가 매개변수를 그대로 넘긴 **같은 모듈 private 헬퍼(1-hop)**. `engine/` ·
    테스트 · 2-hop 이상은 밖이다. 문서 §범위 참조.

실행:
    python -m landing_accessibility.v3_runner.r32_check

`exit` 규약 (`Δ46-R39` · A `check_ruling_index.py` 와 같은 규약)
    ``0``  통과 — 산출을 쓴다 (``status: PASS``)
    ``1``  **검사가 돌았고 실패했다** — 산출을 쓴다 (``status: FAIL`` + 실패 목록)
    ``2``  **검사가 돌지 않았다** — 산출을 **쓰지 않는다.** 통과로도 실패로도 읽지 마라

**선언된 실패 동작** (`R35` 셋째 요소 — 이 선언대로 실증한다)
    ``exit 1`` 에서 산출을 **지우지 않고 남긴다.** 감사 흔적이 목적이다 —
    실패를 파일에서 지우면 "검사가 실패했다" 와 "검사를 안 돌렸다" 가 같아진다.
    ``exit 2`` 에서는 산출을 **건드리지 않는다.** 돌지 않은 실행이 이전 산출을
    덮으면 그 파일이 언제 것인지 알 수 없게 된다.
    실증기: :mod:`landing_accessibility.v3_runner.r32_control_failure_demo`.
    측정 대상은 ``exit`` 이 아니라 **산출 파일의 sha256 변화**다 (`Δ46-R40`) —
    ``exit`` 은 파일에 남지 않는다.
"""

from __future__ import annotations

import argparse
import ast
import re
import sys
import tempfile
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from functools import partial
from pathlib import Path
from typing import Any

__all__ = [
    "ABSENCE_NOT_TOLERATED",
    "NOT_APPLICABLE",
    "R32_OK",
    "R32_VIOLATION",
    "DocRow",
    "OracleResult",
    "Probe",
    "bad",
    "check",
    "document_path",
    "oracle_verdicts",
    "parse_document",
    "sweep_candidates",
]

#: **판정 단위 술어** (A `Δ40` ② — 산문이 아니라 검사 가능한 술어로 적는다).
#:
#: 단위는 매개변수가 아니라 **구조 입력 안의 선택적 키 접근**이다. 술어로:
#:
#: ``is_r32_point(site) :=``
#:     ``TOLERATES_ABSENCE(site)``      부재 경로가 있다 — 키/인자가 없어도 예외 없이
#:                                      값이 나온다
#:     ``AND CROSSES_CONTRACT(site)``   그 값을 만드는 쪽이 이 함수 밖이다 (다른 모듈 ·
#:                                      다른 lane · 브라우저 JS · 파일)
#:
#: ``verdict(site) :=``
#:     ``R32_VIOLATION``   ``TOLERATES_ABSENCE ∧ ∃ v : WRONG_SHAPE(v) ∧
#:                          OUT(site, v) == OUT(site, ABSENT)``
#:     ``R32_OK``          ``TOLERATES_ABSENCE ∧ ∀ v : WRONG_SHAPE(v) →
#:                          OUT(site, v) ≠ OUT(site, ABSENT)``
#:                         (``raise`` 는 값과 다른 출력이므로 여기 들어간다)
#:     ``NOT_APPLICABLE``  ``¬TOLERATES_ABSENCE ∨ ¬CROSSES_CONTRACT``
#:
#: ``OUT(site, x)`` = 그 지점을 x 상태로 실제 호출했을 때의 ``(값 | 예외종류)``.
#: 함수가 여러 경로를 가지면 **경로마다** 잰다 — 한 경로에서만 갈려도
#: 다른 경로에서 겹치면 위반이다.
#:
#: `_judge` 가 이 술어를 그대로 구현한다. 문서의 술어와 검사기의 술어는 같은 것이다.
R32_VIOLATION = "R32_VIOLATION"
R32_OK = "R32_OK"
NOT_APPLICABLE = "NOT_APPLICABLE"
#: 오라클 전용 결과 — 부재 자체가 거부된다(선택적 입력이 아니다). 문서에서는 `R32_OK`
#: 또는 `NOT_APPLICABLE` 로 적히며, 어느 쪽이든 "부재를 관측으로 접지 않는다"는 뜻이다.
ABSENCE_NOT_TOLERATED = "ABSENCE_NOT_TOLERATED"

_HERE = Path(__file__).resolve()
V3_RUNNER_DIR = _HERE.parent
_PKG_ROOT = V3_RUNNER_DIR.parent
_RESEARCH_ROOT = _PKG_ROOT.parent.parent


def document_path() -> Path:
    return _RESEARCH_ROOT / "docs" / "v3" / "R32_APPLICATION_POINTS.md"


def result_path() -> Path:
    """`R35` 4요소를 담는 산출. 이 파일의 sha 변화가 실패 동작의 측정 대상이다."""
    return _RESEARCH_ROOT / "docs" / "v3" / "R32_CHECK_RESULT.json"


def demo_sidecar_path() -> Path:
    """실증기(`r32_control_failure_demo`) 가 남기는 sidecar."""
    return _RESEARCH_ROOT / "docs" / "v3" / "R32_FAILURE_DEMO.json"


def tool_sha256(path: Path | None = None) -> str:
    """이 검사기 소스의 sha256. `R40` — 실증은 이 값에 묶인다."""
    import hashlib

    return hashlib.sha256((path or _HERE).read_bytes()).hexdigest()


# ══════════════════════════════════════════════════════════════════════════
# 층 1 — 행동 오라클
# ══════════════════════════════════════════════════════════════════════════


@dataclass(frozen=True)
class Case:
    """한 코드 경로에서의 (부재, 형태 위반 변형들) 쌍."""

    path: str
    absent: Callable[[], Any]
    #: **하나라도** 부재와 같은 출력을 내면 위반이다.
    malformed: tuple[Callable[[], Any], ...]


@dataclass(frozen=True)
class Probe:
    """한 지점. 코드 경로마다 case 를 갖는다."""

    point_id: str
    cases: tuple[Case, ...]


@dataclass(frozen=True)
class OracleResult:
    point_id: str
    verdict: str
    detail: str


def bad(fn: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
    """형태 위반을 **일부러** 넘기는 호출. 그것이 이 검사기가 재는 것이다.

    정적 타입 검사를 통과하려고 인자 타입을 지우는 자리이기도 하다 — `mypy` 가
    "이 인자는 그 타입이 아니다" 라고 말하는 것은 맞지만, 그 호출이 바로 측정 대상이다.
    """
    return fn(*args, **kwargs)


def _call(fn: Callable[[], Any]) -> tuple[str, str]:
    try:
        return ("value", repr(fn()))
    except BaseException as exc:  # 예외 종류 자체가 관측 대상이다
        return ("raise", type(exc).__name__)


def _judge(probe: Probe) -> OracleResult:
    """위 술어를 그대로 구현한다. 경로 하나라도 겹치면 `R32_VIOLATION`."""
    collisions: list[str] = []
    distinct: list[str] = []
    absent_rejected: list[str] = []
    for case in probe.cases:
        kind_a, out_a = _call(case.absent)
        if kind_a == "raise":
            absent_rejected.append(f"[{case.path}] 부재 → raise {out_a}")
            continue
        for i, m in enumerate(case.malformed):
            kind_m, out_m = _call(m)
            if kind_m == "raise":
                distinct.append(f"[{case.path}] m{i}: raise {out_m}")
            elif out_m == out_a:
                collisions.append(f"[{case.path}] m{i}: 부재와 **동일 출력**")
            else:
                distinct.append(f"[{case.path}] m{i}: 다른 값")
    if collisions:
        return OracleResult(probe.point_id, R32_VIOLATION, "; ".join(collisions + distinct))
    if not distinct and absent_rejected:
        return OracleResult(probe.point_id, ABSENCE_NOT_TOLERATED, "; ".join(absent_rejected))
    return OracleResult(probe.point_id, R32_OK, "; ".join(distinct + absent_rejected))


def _probes() -> tuple[Probe, ...]:
    """오라클 대상. import 는 여기 안에서 한다 — 검사기 import 가 무거워지지 않게."""
    from landing_accessibility.v3_runner import (
        ax_join,
        evidence,
        safety,
        session,
        surface,
        terminal,
    )
    from landing_accessibility.v3_runner.discovery import discover_task_candidates
    from landing_accessibility.v3_runner.obstruction import (
        BBox,
        InterruptObservation,
        Viewport,
        measure_task_obstruction,
    )
    from landing_accessibility.v3_runner.runner import verify_path_manifest_hash
    from landing_accessibility.v3_runner.terminal import TerminalReason

    SEL = "button#go"

    #: control 이 probe 에 **있는** 봉투와 **없는** 봉투. `measure_surface` 는 이 둘에서
    #: 서로 다른 return 문을 탄다 — 경로를 하나만 재면 안 된다.
    FOUND = {
        "raw_features": {
            "primary_action_candidates": [
                {
                    "selector": SEL,
                    "tag": "button",
                    "visible_text": "예약하기",
                    "dom_order": 0,
                    "box": {"x": 10.0, "y": 20.0, "w": 100.0, "h": 40.0},
                }
            ]
        }
    }
    NOT_FOUND: dict[str, Any] = {"raw_features": {}}

    def surf(env: dict[str, Any], tc_extra: dict[str, Any] | None = None) -> Any:
        tc: dict[str, Any] = {"selector": SEL}
        tc.update(tc_extra or {})
        return surface.measure_surface(env, tc, (390, 844))

    def tc_probe(where: str, key: str, *wrong: Any) -> Probe:
        """`where` 는 그 키를 **실제로 읽는** 함수다 — sweep 의 point_id 와 같아야 한다.

        `measure_surface` 는 DOM 에서 control 을 찾았는지에 따라 **다른 return 문**을
        탄다. 경로마다 case 를 만든다 — 한 경로만 재면 `ax_node` 를 놓친다.
        """
        cases: list[Case] = []
        for name, env in (("DOM 발견", FOUND), ("DOM 미발견", NOT_FOUND)):
            cases.append(
                Case(
                    path=name,
                    absent=partial(surf, env),
                    malformed=tuple(partial(surf, env, {key: v}) for v in wrong),
                )
            )
        return Probe(point_id=f"surface.py::{where}::{key}", cases=tuple(cases))

    def one(point_id: str, absent: Callable[[], Any], *bad: Callable[[], Any]) -> Probe:
        return Probe(point_id, (Case("단일", absent, bad),))

    def disc(state: Any, policy: Any = None) -> Any:
        return [c.selector for c in bad(discover_task_candidates, state, None, policy)]

    def cand(c: dict[str, Any]) -> Any:
        d = safety.classify_auth_boundary(c, on_task_path=True, auth_unavoidable=True)
        return (str(d.boundary), d.action, d.reason)

    def obs(c: dict[str, Any]) -> Any:
        """`GuardedPage.observe`/`evaluate` 가 부르는 관측 조립. page 없이 부를 수 있다."""
        return safety._observe(c)  # 검사기는 이음매를 직접 재야 한다

    def retention(manifest: dict[str, Any]) -> Any:
        with tempfile.TemporaryDirectory() as tmp:
            return evidence.verify_retention_manifest(manifest, base=Path(tmp))

    INTERRUPTS = (
        InterruptObservation(
            interrupt_id="i1",
            interrupt_type="COOKIE_CONSENT",
            selector="div#cookie",
            visible=True,
            box=BBox(x=0.0, y=0.0, w=390.0, h=100.0),
            viewport_coverage=0.3,
        ),
    )
    VP = Viewport(width=390, height=844)

    def bad_bbox(v: Any) -> Any:
        return bad(measure_task_obstruction, INTERRUPTS, v, VP)

    def bad_status(status: Any = None, reason: Any = None, note: Any = None) -> Any:
        return bad(terminal.validate_status_reason, status, reason, note)

    return (
        # ── must_flag 및 그 형제들 — `task_control` 의 선택적 키 ────────────────
        tc_probe("measure_surface", "ax_node", "NOT_A_DICT", 123, ["a"]),
        tc_probe("_resolve_nav_container", "nav_container_type", 123, ["DRAWER"], {"t": "DRAWER"}),
        tc_probe("_resolve_nav_container", "nav_container_chain", "DRAWER", 7, {"0": "DRAWER"}),
        tc_probe("measure_surface", "computed_position", 5, {"pos": "fixed"}, ["fixed"]),
        # ── must_not_flag — W5N `Δ35` 가 고친 자리 ─────────────────────────────
        one(
            "surface.py::_iter_states::scroll_states",
            lambda: surf(FOUND),
            lambda: surf({"scroll_states": "S0"}),
            lambda: surf({"scroll_states": {"S0": {}}}),
            lambda: surf({"scroll_states": []}),
            lambda: surf({"scroll_states": [{"raw_features": 3}]}),
        ),
        one(
            "surface.py::normalize_label::(PARAM:text)",
            lambda: surface.normalize_label(None),
            lambda: bad(surface.normalize_label, 5),
            lambda: bad(surface.normalize_label, []),
        ),
        # ── discovery ────────────────────────────────────────────────────────
        one(
            "discovery.py::discover_task_candidates::primary_action_candidates",
            lambda: disc({}),
            # 형태 위반인데 falsy → `or []` 가 부재로 접는다.
            lambda: disc({"primary_action_candidates": {}}),
            lambda: disc({"primary_action_candidates": ""}),
            lambda: disc({"primary_action_candidates": 0}),
        ),
        # `resolved_policy = policy or MIN4_POLICY` — `or` 는 falsy 형태 위반을
        # 기본값으로 접는다. `is not None` 과 갈리는 자리다.
        one(
            "discovery.py::discover_task_candidates::(PARAM:policy)",
            lambda: disc({"primary_action_candidates": [{"selector": "a#x", "dom_order": 0}]}),
            lambda: disc({"primary_action_candidates": [{"selector": "a#x", "dom_order": 0}]}, {}),
            lambda: disc({"primary_action_candidates": [{"selector": "a#x", "dom_order": 0}]}, 0),
        ),
        # ── ax_join ──────────────────────────────────────────────────────────
        one(
            "ax_join.py::probe_selectors::raw_features",
            lambda: ax_join.probe_selectors({"primary_action_candidates": [{"selector": "a#x"}]}),
            lambda: ax_join.probe_selectors(
                {"raw_features": ["nope"], "primary_action_candidates": [{"selector": "a#x"}]}
            ),
            lambda: ax_join.probe_selectors(
                {"raw_features": "nope", "primary_action_candidates": [{"selector": "a#x"}]}
            ),
        ),
        one(
            "ax_join.py::probe_selectors::<DEFAULT_SELECTOR_FEATURES>",
            lambda: ax_join.probe_selectors({"raw_features": {}}),
            lambda: ax_join.probe_selectors(
                {"raw_features": {"primary_action_candidates": {"a": 1}}}
            ),
            lambda: ax_join.probe_selectors({"raw_features": {"primary_action_candidates": "a#x"}}),
        ),
        one(
            "ax_join.py::selector_ax_index::entries",
            lambda: ax_join.selector_ax_index({}),
            lambda: ax_join.selector_ax_index({"entries": {"a": 1}}),
            lambda: ax_join.selector_ax_index({"entries": "x"}),
        ),
        one(
            "ax_join.py::selector_ax_index::ax_node",
            lambda: ax_join.selector_ax_index({"entries": [{"selector": "a#x"}]}),
            lambda: ax_join.selector_ax_index({"entries": [{"selector": "a#x", "ax_node": "n"}]}),
            lambda: ax_join.selector_ax_index({"entries": [{"selector": "a#x", "ax_node": [1]}]}),
        ),
        # ── safety ───────────────────────────────────────────────────────────
        one(
            "safety.py::resolve_forbidden_actions::(PARAM:contract)",
            lambda: safety.resolve_forbidden_actions(None),
            # 키 이름이 `_CONTRACT_FORBIDDEN_KEYS` 밖인 계약.
            lambda: safety.resolve_forbidden_actions({"forbidden": ["LOGIN_SUBMIT"]}),
            lambda: safety.resolve_forbidden_actions("LOGIN_SUBMIT"),
            lambda: safety.resolve_forbidden_actions(12345),
        ),
        one(
            "safety.py::classify_auth_boundary::(MAPPING:candidate)",
            lambda: cand({}),
            # `_PLANNED_ACTION_FIELD_MAP` 번역을 빠뜨린 모양 — detector 가 읽는 키가
            # 하나도 없다. "신호 없는 후보" 와 구분되지 않는다.
            lambda: cand({"control_visible_text": "로그인하기", "control_selector": "a#login"}),
            lambda: cand({"visible_text": {"t": "로그인하기"}}),
        ),
        # ── session (브라우저 JS → Python 경계) ──────────────────────────────
        # `_CONTROL_FACTS_JS` 는 `found: true` 일 때 이 키들을 **언제나** 낸다
        # (값이 `null` 일 수는 있다). 즉 키 부재 자체가 계약 밖인데 `.get` 이 그것을
        # 관측 가능한 상태로 만든다.
        one(
            "session.py::is_credential_field::type",
            lambda: session.is_credential_field({}),
            lambda: session.is_credential_field({"type": ["password"]}),
            lambda: session.is_credential_field({"type": {"t": "password"}}),
        ),
        one(
            "session.py::is_credential_field::autocomplete",
            lambda: session.is_credential_field({}),
            lambda: session.is_credential_field({"autocomplete": ["current-password"]}),
        ),
        one(
            "session.py::is_credential_field::password_scope",
            lambda: session.is_credential_field({}),
            lambda: session.is_credential_field({"password_scope": []}),
            lambda: session.is_credential_field({"password_scope": 0}),
        ),
        one(
            "session.py::observe_input_mode::tag",
            lambda: session.observe_input_mode({}),
            lambda: session.observe_input_mode({"tag": ["select"]}),
            lambda: session.observe_input_mode({"tag": {"t": "select"}}),
        ),
        one(
            "session.py::observe_input_mode::role",
            lambda: session.observe_input_mode({}),
            lambda: session.observe_input_mode({"role": {"r": "combobox"}}),
            lambda: session.observe_input_mode({"role": ["listbox"]}),
        ),
        one(
            "session.py::observe_input_mode::type",
            lambda: session.observe_input_mode({"tag": "input"}),
            lambda: session.observe_input_mode({"tag": "input", "type": ["submit"]}),
        ),
        one(
            "session.py::observe_input_mode::has_datalist",
            lambda: session.observe_input_mode({"tag": "input"}),
            lambda: session.observe_input_mode({"tag": "input", "has_datalist": []}),
            lambda: session.observe_input_mode({"tag": "input", "has_datalist": 0}),
        ),
        # ── safety `_observe` / `_detect_forbidden_action` (candidate 키) ────
        one(
            "safety.py::_detect_forbidden_action::href",
            lambda: obs({}),
            lambda: obs({"href": {}}),
            lambda: obs({"href": []}),
        ),
        one(
            "safety.py::_detect_forbidden_action::url",
            lambda: obs({}),
            lambda: obs({"url": {}}),
            lambda: obs({"url": 0}),
        ),
        one(
            "safety.py::_observe::selector",
            lambda: obs({}),
            lambda: obs({"selector": {}}),
            lambda: obs({"selector": []}),
        ),
        one(
            "safety.py::_observe::visible_text",
            lambda: obs({}),
            lambda: obs({"visible_text": {}}),
            lambda: obs({"visible_text": ["로그인"]}),
        ),
        one(
            "safety.py::_observe::accessible_name",
            lambda: obs({}),
            lambda: obs({"accessible_name": {}}),
            lambda: obs({"accessible_name": ["로그인"]}),
        ),
        one(
            "safety.py::_observe::hittable",
            lambda: obs({}),
            lambda: obs({"hittable": "yes"}),
            lambda: obs({"hittable": {}}),
        ),
        one(
            "safety.py::_observe::enabled",
            lambda: obs({}),
            lambda: obs({"enabled": "yes"}),
            lambda: obs({"enabled": {}}),
        ),
        one(
            "safety.py::_observe::bbox",
            lambda: obs({}),
            lambda: obs({"bbox": "0,0,1,1"}),
            lambda: obs({"bbox": {}}),
        ),
        # ── evidence ─────────────────────────────────────────────────────────
        one(
            "evidence.py::verify_retention_manifest::roots",
            lambda: retention({}),
            # dict/str 은 `roots` 형태 위반인데 순회가 0회라 부재와 갈리지 않는다.
            lambda: retention({"roots": {}}),
            lambda: retention({"roots": ""}),
        ),
        # ── 부재를 거부하는 지점 (`ABSENCE_NOT_TOLERATED`) ───────────────────
        one(
            "runner.py::verify_path_manifest_hash::(PARAM:declared_sha256)",
            lambda: verify_path_manifest_hash({"a": 1}, None),
            lambda: bad(verify_path_manifest_hash, {"a": 1}, 123),
        ),
        one(
            "obstruction.py::measure_task_obstruction::(PARAM:task_control_bbox)",
            lambda: bad_bbox(None),
            lambda: bad_bbox({"x": 0.0, "y": 0.0, "w": 10.0, "h": 10.0}),
            lambda: bad_bbox("0,0,10,10"),
        ),
        # ── terminal — 검증기지만 `raise` 여부로 세 상태가 갈린다 ────────────
        # `EndpointStatus` 는 `StrEnum` 이므로 `"REACHED"` 는 **형태 위반이 아니라
        # 같은 값의 다른 표기**다. 형태 위반은 list/미정의 문자열/숫자다.
        one(
            "terminal.py::validate_status_reason::(PARAM:endpoint_status)",
            lambda: bad_status(None, None, None),
            lambda: bad_status(["REACHED"], None, None),
            lambda: bad_status("NOT_A_STATUS", None, None),
            lambda: bad_status(123, None, None),
        ),
        one(
            "terminal.py::validate_status_reason::(PARAM:terminal_reason)",
            lambda: bad_status(None, None, None),
            lambda: bad_status(None, ["OTHER"], None),
            lambda: bad_status(None, "NOT_A_REASON", None),
        ),
        one(
            "terminal.py::validate_status_reason::(PARAM:note)",
            lambda: bad_status(None, TerminalReason.OTHER, None),
            lambda: bad_status(None, TerminalReason.OTHER, 5),
            lambda: bad_status(None, TerminalReason.OTHER, ["x"]),
        ),
    )


#: 대조군. `must_flag` 가 `R32_VIOLATION` 이 아니거나 `must_not_flag` 가
#: `R32_OK` 가 아니면 **목록이 아니라 방법이 틀린 것**이다.
CONTROLS: dict[str, tuple[str, str]] = {
    "must_flag": ("surface.py::measure_surface::ax_node", R32_VIOLATION),
    "must_not_flag": ("surface.py::_iter_states::scroll_states", R32_OK),
}


def oracle_verdicts() -> dict[str, OracleResult]:
    return {p.point_id: _judge(p) for p in _probes()}


# ══════════════════════════════════════════════════════════════════════════
# 층 3 — AST 표류 검사 (문서와 무관하게 코드에서 후보를 다시 만든다)
# ══════════════════════════════════════════════════════════════════════════


def _params(fn: ast.FunctionDef | ast.AsyncFunctionDef) -> list[str]:
    a = fn.args
    out = [x.arg for grp in (a.posonlyargs, a.args, a.kwonlyargs) for x in grp]
    if a.vararg:
        out.append(a.vararg.arg)
    if a.kwarg:
        out.append(a.kwarg.arg)
    return out


def _optional_params(fn: ast.FunctionDef | ast.AsyncFunctionDef) -> set[str]:
    a = fn.args
    out: set[str] = set()
    pos = a.posonlyargs + a.args
    for arg, d in zip(pos[len(pos) - len(a.defaults) :], a.defaults, strict=False):
        if isinstance(d, ast.Constant) and d.value is None:
            out.add(arg.arg)
    for arg, kwd in zip(a.kwonlyargs, a.kw_defaults, strict=False):
        if isinstance(kwd, ast.Constant) and kwd.value is None:
            out.add(arg.arg)
    for arg in pos + a.kwonlyargs:
        if arg.annotation is not None and re.search(
            r"\bNone\b|Optional", ast.unparse(arg.annotation)
        ):
            out.add(arg.arg)
    return out


class _Reads(ast.NodeVisitor):
    def __init__(self, names: Iterable[str]) -> None:
        self.names = set(names)
        self.keys: set[str] = set()

    def visit_Call(self, node: ast.Call) -> None:
        f = node.func
        if (
            isinstance(f, ast.Attribute)
            and f.attr == "get"
            and isinstance(f.value, ast.Name)
            and f.value.id in self.names
            and node.args
            and isinstance(node.args[0], ast.Constant)
            and isinstance(node.args[0].value, str)
        ):
            self.keys.add(node.args[0].value)
        self.generic_visit(node)

    def visit_Subscript(self, node: ast.Subscript) -> None:
        if (
            isinstance(node.value, ast.Name)
            and node.value.id in self.names
            and isinstance(node.slice, ast.Constant)
            and isinstance(node.slice.value, str)
        ):
            self.keys.add(node.slice.value)
        self.generic_visit(node)

    def visit_Compare(self, node: ast.Compare) -> None:
        if (
            len(node.ops) == 1
            and isinstance(node.ops[0], ast.In)
            and isinstance(node.comparators[0], ast.Name)
            and node.comparators[0].id in self.names
            and isinstance(node.left, ast.Constant)
            and isinstance(node.left.value, str)
        ):
            self.keys.add(node.left.value)
        self.generic_visit(node)


#: sweep 에서 제외하는 파일. **측정 대상이 아니라 측정 도구**다 — 검사기가 자기
#: 자신을 목록에 넣으면 목록이 "무엇을 쟀는가" 가 아니라 "무엇으로 쟀는가" 를 섞는다.
#: (첫 실행에서 실증기가 표류 후보로 잡혔다. 그 표류 검사는 **정상 동작**이었다.)
W5P_TOOLING = frozenset({"r32_check.py", "r32_control_failure_demo.py"})


def sweep_candidates(root: Path | None = None) -> dict[str, str]:
    """`{point_id: 발견 경로}`. 문서와 독립적으로 코드에서 만든다."""
    root = root or V3_RUNNER_DIR
    out: dict[str, str] = {}
    for path in sorted(root.glob("*.py")):
        if path.name in W5P_TOOLING:
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"))
        fns = {
            n.name: n
            for n in ast.walk(tree)
            if isinstance(n, ast.FunctionDef | ast.AsyncFunctionDef)
        }
        for fn in ast.walk(tree):
            if not isinstance(fn, ast.FunctionDef | ast.AsyncFunctionDef):
                continue
            if fn.name.startswith("_"):
                continue
            params = _params(fn)
            direct = _Reads(params)
            direct.visit(fn)
            for key in direct.keys:
                out[f"{path.name}::{fn.name}::{key}"] = "직접"
            for name in _optional_params(fn):
                out[f"{path.name}::{fn.name}::(PARAM:{name})"] = "선택적 매개변수"
            for call in ast.walk(fn):
                if not isinstance(call, ast.Call) or not isinstance(call.func, ast.Name):
                    continue
                callee = fns.get(call.func.id)
                if callee is None or not callee.name.startswith("_"):
                    continue
                cps = _params(callee)
                for i, arg in enumerate(call.args):
                    if not (isinstance(arg, ast.Name) and arg.id in params):
                        continue
                    if i >= len(cps):
                        continue
                    hop = _Reads({cps[i]})
                    hop.visit(callee)
                    for key in hop.keys:
                        out[f"{path.name}::{callee.name}::{key}"] = f"{fn.name} 1-hop"
    return out


# ══════════════════════════════════════════════════════════════════════════
# R33 선행 확인 — `scroll_states` 와 `raw_features` 를 **동시에** 담은 봉투 실측
# ══════════════════════════════════════════════════════════════════════════
#
# A `Δ40/R33`: 두 키를 함께 가지면 raise (네 번째 상태 '모호'). W5N 이 이미 그렇게
# 구현했다. 빠진 것은 **선행 확인** — 그렇게 넘기는 기존 호출자·fixture·테스트가
# 실제로 있는가. "없다" 는 주장은 **대조군이 필요하다**: 같은 검색이 한쪽 키만 가진
# 봉투는 다수 잡아내야 그 검색이 동작함이 보인다 (`Δ10-R14`).

_AMBIGUOUS_KEYS = ("scroll_states", "raw_features")
#: 검색 범위. REAL_TARGET 누적 0 건이므로 관측치 오염은 없고, 확인 범위는
#: **fixture · 테스트 · 내부 호출부** 다 (A 가 정한 범위 그대로).
R33_SCAN_ROOTS = ("research/landing_accessibility", "tests")


@dataclass(frozen=True)
class EnvelopeSite:
    where: str
    keys: tuple[str, ...]


def _json_maps(node: Any, path: str) -> Iterable[tuple[str, set[str]]]:
    if isinstance(node, dict):
        yield path, set(node)
        for k, v in node.items():
            yield from _json_maps(v, f"{path}.{k}")
    elif isinstance(node, list):
        for i, v in enumerate(node):
            yield from _json_maps(v, f"{path}[{i}]")


def _py_maps(path: Path) -> Iterable[tuple[str, set[str]]]:
    """파이썬 소스의 dict **리터럴**만 본다 — 동적 조립은 잡지 못한다(한계로 보고)."""
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except SyntaxError:
        return
    for node in ast.walk(tree):
        if isinstance(node, ast.Dict):
            keys = {
                k.value
                for k in node.keys
                if isinstance(k, ast.Constant) and isinstance(k.value, str)
            }
            if keys:
                yield f"{path.name}:{node.lineno}", keys


def r33_envelope_scan(repo_root: Path | None = None) -> dict[str, list[EnvelopeSite]]:
    """`{"both": [...], "scroll_states_only": [...], "raw_features_only": [...]}`.

    `both` 가 비어 있다는 주장은 나머지 둘이 **비어 있지 않아야** 근거가 된다.
    """
    import json as _json

    root = repo_root or _RESEARCH_ROOT.parent.parent
    out: dict[str, list[EnvelopeSite]] = {
        "both": [],
        "scroll_states_only": [],
        "raw_features_only": [],
    }
    for rel in R33_SCAN_ROOTS:
        base = root / rel
        if not base.is_dir():
            continue
        for path in sorted(base.rglob("*")):
            if not path.is_file() or ".git" in path.parts:
                continue
            if path.suffix == ".json":
                try:
                    doc = _json.loads(path.read_text(encoding="utf-8"))
                except (ValueError, UnicodeDecodeError):
                    continue
                maps = (
                    (f"{path.relative_to(root)}:{loc}", keys) for loc, keys in _json_maps(doc, "$")
                )
            elif path.suffix == ".py":
                maps = (
                    (f"{path.relative_to(root).parent}/{loc}", keys) for loc, keys in _py_maps(path)
                )
            else:
                continue
            for where, keys in maps:
                has_s = _AMBIGUOUS_KEYS[0] in keys
                has_r = _AMBIGUOUS_KEYS[1] in keys
                if has_s and has_r:
                    out["both"].append(EnvelopeSite(where, tuple(sorted(keys))[:8]))
                elif has_s:
                    out["scroll_states_only"].append(EnvelopeSite(where, ()))
                elif has_r:
                    out["raw_features_only"].append(EnvelopeSite(where, ()))
    return out


# ══════════════════════════════════════════════════════════════════════════
# 층 2 — 문서 파싱 + 구조 검사
# ══════════════════════════════════════════════════════════════════════════

_VERDICTS = {R32_VIOLATION, R32_OK, NOT_APPLICABLE}
_BASIS = {"BEHAVIORAL", "READ"}


@dataclass(frozen=True)
class DocRow:
    point_id: str
    file: str
    chain: tuple[str, ...]
    key: str
    verdict: str
    basis: str
    line: int


_ROW_RE = re.compile(r"^\|\s*(?P<id>[^|]+?)\s*\|\s*(?P<v>[A-Z0-9_]+)\s*\|\s*(?P<b>[A-Z]+)\s*\|")


#: 목록 표가 있는 절. 이 절 **안에서만** 행을 읽는다 — 본문의 설명용 표를 목록으로
#: 오인하지 않기 위해서다.
_TABLE_HEADING = "## 부록 A"


def parse_document(path: Path | None = None) -> list[DocRow]:
    """`## 부록 A` 절의 `| point_id | 판정 | 판정근거 | 근거 |` 표를 읽는다."""
    path = path or document_path()
    if not path.is_file():
        raise FileNotFoundError(f"목록 문서가 없다: {path}")
    rows: list[DocRow] = []
    seen: set[str] = set()
    in_table = False
    for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if line.startswith("## "):
            in_table = line.startswith(_TABLE_HEADING)
            continue
        if not in_table:
            continue
        m = _ROW_RE.match(line)
        if not m:
            continue
        pid = m.group("id").strip().strip("`")
        if pid in ("point_id", "지점 ID") or set(pid) <= {"-", ":", " "}:
            continue
        parts = pid.split("::")
        if len(parts) != 3:
            raise ValueError(f"{path}:{lineno} point_id 형식이 아니다: {pid!r}")
        if pid in seen:
            raise ValueError(f"{path}:{lineno} point_id 중복: {pid!r}")
        seen.add(pid)
        verdict, basis = m.group("v"), m.group("b")
        if verdict not in _VERDICTS:
            raise ValueError(f"{path}:{lineno} 알 수 없는 판정: {verdict!r}")
        if basis not in _BASIS:
            raise ValueError(f"{path}:{lineno} 알 수 없는 판정근거: {basis!r}")
        rows.append(
            DocRow(pid, parts[0], tuple(parts[1].split("→")), parts[2], verdict, basis, lineno)
        )
    return rows


def _structural_failures(rows: list[DocRow]) -> list[str]:
    out: list[str] = []
    cache: dict[str, dict[str, ast.FunctionDef | ast.AsyncFunctionDef]] = {}
    for row in rows:
        path = V3_RUNNER_DIR / row.file
        if not path.is_file():
            out.append(f"[구조] {row.point_id}: 파일이 없다 — {path}")
            continue
        if row.file not in cache:
            tree = ast.parse(path.read_text(encoding="utf-8"))
            cache[row.file] = {
                n.name: n
                for n in ast.walk(tree)
                if isinstance(n, ast.FunctionDef | ast.AsyncFunctionDef)
            }
        fns = cache[row.file]
        missing = [name for name in row.chain if name not in fns]
        if missing:
            out.append(f"[구조] {row.point_id}: 함수가 없다 — {missing}")
            continue
        terminal_fn = fns[row.chain[-1]]
        src = ast.unparse(terminal_fn)
        if row.key.startswith("(PARAM:"):
            name = row.key[len("(PARAM:") : -1]
            if name not in _params(terminal_fn):
                out.append(f"[구조] {row.point_id}: 매개변수가 없다 — {name}")
        elif row.key.startswith(("(MAPPING:", "<")):
            if row.key.startswith("(MAPPING:"):
                name = row.key[len("(MAPPING:") : -1]
                if name not in _params(terminal_fn):
                    out.append(f"[구조] {row.point_id}: 매개변수가 없다 — {name}")
        elif f"'{row.key}'" not in src and f'"{row.key}"' not in src:
            out.append(
                f"[구조] {row.point_id}: 키 리터럴이 {row.chain[-1]} 본문에 없다 — {row.key!r}"
            )
    return out


def check(doc: Path | None = None, *, skip_oracle: bool = False) -> list[str]:
    """실패 목록. 비어 있으면 통과."""
    rows = parse_document(doc)
    by_id = {r.point_id: r for r in rows}
    failures = _structural_failures(rows)

    # 층 3 — 표류
    swept = sweep_candidates()
    for pid, how in sorted(swept.items()):
        if pid not in by_id:
            failures.append(f"[표류] 코드에 있으나 목록에 없는 후보: {pid}  ({how})")

    # 층 1 — 행동 오라클
    if not skip_oracle:
        for pid, res in sorted(oracle_verdicts().items()):
            row = by_id.get(pid)
            if row is None:
                failures.append(f"[오라클] 오라클에 있으나 목록에 없는 지점: {pid}")
                continue
            if row.basis != "BEHAVIORAL":
                failures.append(f"[오라클] {pid}: 오라클이 도는데 문서 판정근거가 {row.basis} 다")
            expected = row.verdict
            actual = res.verdict
            if actual == ABSENCE_NOT_TOLERATED:
                if expected == R32_VIOLATION:
                    failures.append(
                        f"[오라클] {pid}: 부재가 거부되는데 문서는 {expected} — {res.detail}"
                    )
            elif actual != expected:
                failures.append(f"[오라클] {pid}: 문서={expected} · 오라클={actual} — {res.detail}")

        # 대조군 — 이 둘이 무너지면 목록이 아니라 **방법**이 틀린 것이다 (A `Δ40` ①).
        verdicts = oracle_verdicts()
        for role, (pid, want) in CONTROLS.items():
            control = verdicts.get(pid)
            if control is None:
                failures.append(f"[대조군/{role}] 오라클에 {pid} 이 없다")
            elif control.verdict != want:
                failures.append(
                    f"[대조군/{role}] {pid}: 기대={want} · 오라클={control.verdict} — "
                    f"{control.detail}"
                )
            elif by_id.get(pid) is None or by_id[pid].verdict != want:
                got = by_id[pid].verdict if pid in by_id else "목록에 없음"
                failures.append(f"[대조군/{role}] {pid}: 문서가 {got} 로 적었다 (기대 {want})")

    return failures


# ══════════════════════════════════════════════════════════════════════════
# 산출 — `R35` 4요소
# ══════════════════════════════════════════════════════════════════════════

#: 이 검사기가 **선언한** 실패 동작. 실증기가 이 선언대로 동작함을 보인다 (`R35` ③).
DECLARED_FAILURE_BEHAVIOUR = {
    "0": "통과 — 산출을 쓴다 (status=PASS)",
    "1": "검사가 돌았고 실패했다 — 산출을 쓴다 (status=FAIL). 지우지 않는다: 감사 흔적",
    "2": "검사가 돌지 않았다 — 산출을 쓰지 않는다. 통과로도 실패로도 읽지 마라",
}


def build_result(failures: list[str], *, verdicts: dict[str, OracleResult]) -> dict[str, Any]:
    """`R35` 4요소를 한 객체로. **시각·난수를 넣지 않는다** — sha 비교가 측정 수단이다."""
    controls = []
    for role, (pid, want) in sorted(CONTROLS.items()):
        res = verdicts.get(pid)
        controls.append(
            {
                "role": role,  # ① 대조 목록
                "point_id": pid,
                "expected": want,
                "observed": res.verdict if res else None,
                "passed": bool(res and res.verdict == want),  # ② 결과
                "detail": res.detail if res else "오라클에 없다",
            }
        )
    demo = _read_json(demo_sidecar_path())
    current = tool_sha256()
    return {
        "schema": "w5p/r32-check-result/1",
        "status": "PASS" if not failures else "FAIL",
        "controls": controls,
        "failures": failures,
        # ③ 도구 경로
        "tool": {
            "module": "landing_accessibility.v3_runner.r32_check",
            "path": _rel(_HERE),
            "sha256": current,
            "exit_codes": DECLARED_FAILURE_BEHAVIOUR,
            "declared_failure_behaviour": (
                "exit 1 은 산출을 남긴다(감사 흔적). exit 2 는 산출을 건드리지 않는다."
            ),
        },
        # ④ 실패 시 동작의 실증 — `R40` 으로 도구 sha 에 묶인다
        "failure_demonstration": {
            "sidecar": _rel(demo_sidecar_path()),
            "present": demo is not None,
            "tool_sha256_at_demo": (demo or {}).get("tool_sha256"),
            "valid_for_this_commit": bool(demo and demo.get("tool_sha256") == current),
            "cases": [c["name"] for c in (demo or {}).get("cases", [])],
        },
    }


def _rel(path: Path) -> str:
    """research root 기준 상대경로. 밖이면 절대경로 그대로 (테스트 임시 경로 대비)."""
    try:
        return str(path.relative_to(_RESEARCH_ROOT))
    except ValueError:
        return str(path)


def _read_json(path: Path) -> dict[str, Any] | None:
    import json

    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return loaded if isinstance(loaded, dict) else None


def write_result(result: dict[str, Any], path: Path | None = None) -> Path:
    import json

    target = path or result_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return target


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="R32 적용 지점 목록 ↔ 코드 정합 검사")
    ap.add_argument("--doc", type=Path, default=None)
    ap.add_argument(
        "--out", type=Path, default=None, help="산출 경로 (기본: R32_CHECK_RESULT.json)"
    )
    ap.add_argument("--no-write", action="store_true", help="산출을 쓰지 않는다 (진단용)")
    ap.add_argument("--skip-oracle", action="store_true")
    ap.add_argument("--oracle-only", action="store_true")
    ns = ap.parse_args(argv)

    if ns.oracle_only:
        try:
            for pid, res in sorted(oracle_verdicts().items()):
                print(f"{res.verdict:22} {pid}\n{'':22} {res.detail}")
        except Exception as exc:  # 검사가 돌지 않았다
            return _did_not_run(exc)
        return 0

    # ── 검사가 **돌 수 있었는가** 와 **통과했는가** 를 분리한다 (`Δ46`) ──
    try:
        failures = check(ns.doc, skip_oracle=ns.skip_oracle)
        verdicts = {} if ns.skip_oracle else oracle_verdicts()
        result = build_result(failures, verdicts=verdicts)
    except Exception as exc:
        return _did_not_run(exc)

    for f in failures:
        print(f)
    if not ns.no_write:
        # 선언대로: 실패해도 남긴다. 지우면 실패와 미실행이 같아진다.
        print(f"산출 → {write_result(result, ns.out)}")
    demo = result["failure_demonstration"]
    if not demo["valid_for_this_commit"]:
        print(
            "경고: 실패 동작 실증이 현재 도구 sha 와 묶여 있지 않다 "
            f"(sidecar={demo['tool_sha256_at_demo']}). r32_control_failure_demo 를 다시 돌려라.",
            file=sys.stderr,
        )
    print(f"\n실패 {len(failures)}건 — status={result['status']}")
    return 1 if failures else 0


def _did_not_run(exc: BaseException) -> int:
    """`exit 2` — 검사가 돌지 않았다. **산출을 건드리지 않는다.**

    `Δ46`: `exit 1` 은 "검사가 돌아서 실패했다" 와 같은 코드다. 미실행이 그 코드를
    쓰면 미실행과 실패가 같은 출력이 된다 — 이 세션의 중심 결함이다.
    """
    import traceback

    traceback.print_exc()
    print(
        f"\n검사가 돌지 않았다 ({type(exc).__name__}). "
        "통과로도 실패로도 읽지 마라. 산출은 갱신되지 않았다.",
        file=sys.stderr,
    )
    return 2


if __name__ == "__main__":
    sys.exit(main())
