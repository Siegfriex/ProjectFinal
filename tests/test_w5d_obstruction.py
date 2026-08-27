"""W5D — task-specific obstruction 측정 검정.

이 파일이 지키려는 명제는 넷이다.

1. `task_control_occlusion` 과 `overlay_coverage` 는 **다른 양**이며 같은 입력에서
   반대 방향으로 갈릴 수 있다 (`02 §5`).
2. `dismiss_control_exists` 계열 4필드는 **단위·모집단·원천 필드** 세 축에 의존하며,
   축 하나만 바꾼 대조군에서 값이 달라진다 (`T-A-V3-P0-003 ruling_11`).
3. "닫을 대상이 없다" / "닫기 control 이 없다" / "닫기가 실패했다" 는 **서로 다른 출력**이다.
4. 산출 불능은 `None` 이다. `0.0` 이나 `False` 로 바뀌지 않는다.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import pytest

REPO = Path(__file__).resolve().parents[1]
RESEARCH = REPO / "research" / "landing_accessibility"
sys.path.insert(0, str(RESEARCH / "src"))

from landing_accessibility.v3_runner.obstruction import (  # noqa: E402
    BBox,
    BlockingBasis,
    DismissalState,
    DismissControlObservation,
    InterruptObservation,
    ObstructionStatus,
    Viewport,
    measure_task_obstruction,
)

FIXTURE = RESEARCH / "fixtures" / "w5d" / "obstruction_cases.json"


def _load() -> dict[str, Any]:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def _bbox(raw: dict[str, float] | None) -> BBox | None:
    return None if raw is None else BBox(**raw)


def _interrupt(raw: dict[str, Any]) -> InterruptObservation:
    controls = tuple(DismissControlObservation(**c) for c in raw.get("dismiss_controls", []) or [])
    return InterruptObservation(
        interrupt_id=raw["interrupt_id"],
        interrupt_type=raw["interrupt_type"],
        selector=raw["selector"],
        visible=raw.get("visible"),
        box=_bbox(raw.get("box")),
        viewport_coverage=raw.get("viewport_coverage"),
        intercepts_task_control=raw.get("intercepts_task_control"),
        traps_interaction=raw.get("traps_interaction"),
        dismiss_container_observed=raw.get("dismiss_container_observed", True),
        dismiss_controls=controls,
        dismiss_attempted=raw.get("dismiss_attempted", False),
        dismiss_succeeded_observed=raw.get("dismiss_succeeded_observed"),
        dismiss_failure_mode=raw.get("dismiss_failure_mode"),
    )


def _measure(case: dict[str, Any], doc: dict[str, Any]) -> Any:
    control_raw = (
        case["task_control_bbox"] if "task_control_bbox" in case else doc["task_control_bbox"]
    )
    return measure_task_obstruction(
        [_interrupt(i) for i in case["interrupts"]],
        _bbox(control_raw),
        Viewport(**doc["viewport"]),
    )


@pytest.fixture(scope="module")
def doc() -> dict[str, Any]:
    return _load()


@pytest.fixture(scope="module")
def cases(doc: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {c["case_id"]: c for c in doc["cases"]}


def _case_ids() -> list[str]:
    return [c["case_id"] for c in _load()["cases"]]


# ── fixture 전건 회귀 ────────────────────────────────────────────────────────
@pytest.mark.parametrize("case_id", _case_ids())
def test_fixture_case_matches_expected_measurement(
    case_id: str, doc: dict[str, Any], cases: dict[str, dict[str, Any]]
) -> None:
    case = cases[case_id]
    got = _measure(case, doc)
    expect = case["expect"]

    for key, want in expect.items():
        if key == "blocking_population":
            assert list(got.blocking_population) == want, f"{case_id}: blocking_population"
            continue
        actual = getattr(got, key)
        if hasattr(actual, "value"):
            actual = actual.value
        assert actual == want, f"{case_id}: {key} — got {actual!r}, want {want!r}"

    rows = {r.interrupt_id: r for r in got.rows}
    assert len(rows) == len(case["interrupts"]), f"{case_id}: 행 수가 interrupt 수와 다르다"
    for want_row in case["expect_rows"]:
        row = rows[want_row["interrupt_id"]]
        assert row.blocking_basis.value == want_row["blocking_basis"], f"{case_id}: basis"
        assert row.task_control_occlusion == want_row["task_control_occlusion"], (
            f"{case_id}: 행 단위 기하 occlusion"
        )


# ── 1. 두 값이 갈리는가 ──────────────────────────────────────────────────────
def test_wide_overlay_and_precise_overlay_rank_in_opposite_directions(
    doc: dict[str, Any], cases: dict[str, dict[str, Any]]
) -> None:
    """`02 §5` — `max_overlay_coverage` 만으로 modal obstruction 을 대표하면 순위가 뒤집힌다.

    넓은 배너는 화면을 훨씬 많이 덮지만 task control 을 안 가리고, 작은 팝업은 화면을
    거의 안 덮지만 task control 을 완전히 가린다. 과업 수행을 막는 쪽은 후자다.
    """
    wide = _measure(cases["divergence_wide_banner_misses_control"], doc)
    precise = _measure(cases["divergence_small_modal_covers_control"], doc)

    # 보조값 기준 순위
    assert wide.overlay_coverage is not None and precise.overlay_coverage is not None
    assert wide.overlay_coverage > precise.overlay_coverage

    # primary 기준 순위 — 정확히 반대다
    assert wide.task_control_occlusion is not None
    assert precise.task_control_occlusion is not None
    assert precise.task_control_occlusion > wide.task_control_occlusion

    # 그리고 dismissal 필요 여부도 반대다
    assert wide.dismiss_required_for_task is False
    assert precise.dismiss_required_for_task is True
    assert wide.forced_dismissal_count == 0
    assert precise.forced_dismissal_count == 1


def test_blocking_without_geometric_overlap_is_still_obstruction(
    doc: dict[str, Any], cases: dict[str, dict[str, Any]]
) -> None:
    """역방향 — occlusion 이 0.0 인데도 막는 경우가 있다(상호작용 포획)."""
    got = _measure(cases["modal_trap_without_geometric_overlap"], doc)
    assert got.task_control_occlusion == 0.0
    assert got.dismiss_required_for_task is True
    assert got.rows[0].blocking_basis is BlockingBasis.MODAL_TRAP
    assert got.forced_dismissal_count == 1


# ── 2. 세 축 대조군 ──────────────────────────────────────────────────────────
def test_axis1_unit_is_interrupt_not_fieldwise_aggregate(
    doc: dict[str, Any], cases: dict[str, dict[str, Any]]
) -> None:
    """축 1(단위) 대조군.

    blocking interrupt 가 둘이고 한쪽에만 닫기 control 이 있다. 필드별 `any` 집계였다면
    `dismiss_control_exists = True` 가 나오지만, 그건 **실재하지 않는 조합**이다 —
    이름은 A 의 것이고 exists 는 B 의 것이 섞이기 때문이다. 대표 행 축약은 최대 occlusion
    행(B)의 값을 그대로 쓴다.
    """
    got = _measure(cases["axis1_unit_representative_row"], doc)

    assert len(got.blocking_population) == 2, "두 interrupt 모두 blocking 모집단이다"
    assert got.representative_interrupt_id == "i_high"
    assert got.dismiss_control_exists is False
    assert got.dismissal_state is DismissalState.NO_CONTROL

    # 원자료는 살아 있다 — 요약이 행을 지우지 않는다.
    rows = {r.interrupt_id: r for r in got.rows}
    assert rows["i_low"].dismiss_control_exists is True
    assert rows["i_low"].dismiss_control_accessible_name == "확인"
    assert rows["i_high"].dismiss_control_exists is False


def test_axis2_population_is_conditional_on_blocking(
    doc: dict[str, Any], cases: dict[str, dict[str, Any]]
) -> None:
    """축 2(모집단) 대조군.

    보이는 오버레이(chat widget)가 **닫기 control 을 갖고 있다**. 모집단을 "보이는 오버레이
    전체"로 잡으면 `dismiss_control_exists = True` 가 된다. `P_blocking` 으로 잡으면
    모집단이 비어 있으므로 `None` — 닫을 대상 자체가 없기 때문이다.
    """
    got = _measure(cases["axis2_population_nonblocking_has_dismiss_control"], doc)

    assert got.blocking_population == ()
    assert got.dismiss_control_exists is None, "모집단이 비면 False 가 아니라 None 이다"
    assert got.dismissal_state is DismissalState.NO_TARGET

    # 같은 자료에서 '보이는 오버레이 전체' 모집단은 True 를 낸다 — 두 수는 다른 양이다.
    row = got.rows[0]
    assert row.blocking_basis is BlockingBasis.NOT_BLOCKING
    assert row.dismiss_control_exists is None
    raw_interrupt = cases["axis2_population_nonblocking_has_dismiss_control"]["interrupts"][0]
    assert raw_interrupt["visible"] is True, "'보이는 오버레이' 모집단에는 들어간다"
    assert raw_interrupt["dismiss_controls"], "원천 필드에는 닫기 후보가 실재한다"


def test_axis3_source_field_absence_is_not_false(
    doc: dict[str, Any], cases: dict[str, dict[str, Any]]
) -> None:
    """축 3(원천 필드) 대조군 — 원천을 못 봤으면 `None`, 보고 없었으면 `False`."""
    unobserved = _measure(cases["axis3_source_container_unobserved"], doc)
    observed_empty = _measure(cases["no_control_blocking_without_close"], doc)

    assert unobserved.dismiss_control_exists is None
    assert unobserved.dismissal_state is DismissalState.UNDETERMINED
    assert unobserved.status is ObstructionStatus.PARTIAL

    assert observed_empty.dismiss_control_exists is False
    assert observed_empty.dismissal_state is DismissalState.NO_CONTROL
    assert observed_empty.status is ObstructionStatus.MEASURED

    assert unobserved.dismiss_control_exists != observed_empty.dismiss_control_exists


def test_axis3_name_absent_is_not_null(
    doc: dict[str, Any], cases: dict[str, dict[str, Any]]
) -> None:
    """축 3 — 이름 없음이 **관측**된 것(`NAME_ABSENT`)과 잴 대상이 없는 것(`None`)은 다르다."""
    named_absent = _measure(cases["axis3_name_absent_is_not_null"], doc)
    no_control = _measure(cases["no_control_blocking_without_close"], doc)

    assert named_absent.dismiss_control_accessible_name == "NAME_ABSENT"
    assert no_control.dismiss_control_accessible_name is None


# ── 3. 세 상태가 각각 다른 출력을 낸다 ───────────────────────────────────────
def test_no_target_no_control_and_dismiss_failed_are_three_distinct_outputs(
    doc: dict[str, Any], cases: dict[str, dict[str, Any]]
) -> None:
    """합치면 안 되는 세 상태.

    - 닫을 대상이 없다 → `NO_TARGET`, exists `None`, succeeded `None`
    - 닫기 control 이 없다 → `NO_CONTROL`, exists `False`, succeeded `None`
    - 닫기가 실패했다 → `DISMISS_FAILED`, exists `True`, succeeded `False`
    """
    no_target = _measure(cases["no_target_nothing_to_dismiss"], doc)
    no_control = _measure(cases["no_control_blocking_without_close"], doc)
    failed = _measure(cases["dismiss_failed"], doc)

    triples = {
        (m.dismissal_state, m.dismiss_control_exists, m.dismiss_succeeded)
        for m in (no_target, no_control, failed)
    }
    assert len(triples) == 3, "세 상태가 서로 다른 값 조합을 내야 한다"

    assert (no_target.dismissal_state, no_target.dismiss_control_exists) == (
        DismissalState.NO_TARGET,
        None,
    )
    assert (no_control.dismissal_state, no_control.dismiss_control_exists) == (
        DismissalState.NO_CONTROL,
        False,
    )
    assert (failed.dismissal_state, failed.dismiss_control_exists, failed.dismiss_succeeded) == (
        DismissalState.DISMISS_FAILED,
        True,
        False,
    )

    # 셋 다 forced_dismissal_count 는 0 이지만, 그 0 의 뜻이 다르다.
    # count 하나로 세 상태를 복원할 수 없다 — 그래서 dismissal_state 를 따로 남긴다.
    assert no_target.forced_dismissal_count == no_control.forced_dismissal_count == 0
    assert failed.forced_dismissal_count == 0


def test_attempted_and_not_attempted_are_distinct_from_failed(
    doc: dict[str, Any], cases: dict[str, dict[str, Any]]
) -> None:
    """시도하지 않은 것은 실패가 아니다 — `succeeded` 는 `None` 이지 `False` 가 아니다."""
    not_attempted = _measure(cases["axis3_name_absent_is_not_null"], doc)
    failed = _measure(cases["dismiss_failed"], doc)

    assert not_attempted.dismissal_state is DismissalState.CONTROL_PRESENT_NOT_ATTEMPTED
    assert not_attempted.dismiss_succeeded is None
    assert failed.dismiss_succeeded is False


# ── 4. 산출 불능은 None ──────────────────────────────────────────────────────
def test_geometry_overlap_alone_does_not_confirm_blocking(
    doc: dict[str, Any], cases: dict[str, dict[str, Any]]
) -> None:
    """`03 §9` — 겹치기만 하고 입력 가로채기가 미관측이면 확정하지 않는다."""
    got = _measure(cases["geometry_overlap_without_interception"], doc)

    assert got.rows[0].task_control_occlusion == 1.0, "행 단위 기하 원자료는 보존된다"
    assert got.rows[0].blocking_basis is BlockingBasis.UNDETERMINED
    assert got.task_control_occlusion is None, "0.0 으로 바꾸지 않는다"
    assert got.dismiss_required_for_task is None
    assert got.status is ObstructionStatus.UNDETERMINED


def test_missing_task_control_bbox_yields_none_not_zero(
    doc: dict[str, Any], cases: dict[str, dict[str, Any]]
) -> None:
    got = _measure(cases["task_control_bbox_missing"], doc)
    assert got.task_control_occlusion is None
    assert got.status is ObstructionStatus.UNDETERMINED
    # 보조값은 여전히 산출된다 — 하나가 불능이라고 나머지를 버리지 않는다.
    assert got.overlay_coverage == 1.0


def test_zero_occlusion_and_none_occlusion_are_distinguishable(
    doc: dict[str, Any], cases: dict[str, dict[str, Any]]
) -> None:
    """`0.0`(재 봤더니 안 가려짐)과 `None`(못 쟀음)이 같은 값으로 붕괴하지 않는다."""
    measured_zero = _measure(cases["divergence_wide_banner_misses_control"], doc)
    undetermined = _measure(cases["geometry_overlap_without_interception"], doc)

    assert measured_zero.task_control_occlusion == 0.0
    assert measured_zero.status is ObstructionStatus.MEASURED
    assert undetermined.task_control_occlusion is None
    assert undetermined.status is ObstructionStatus.UNDETERMINED


def test_invisible_overlay_keeps_geometry_but_is_not_blocking(
    doc: dict[str, Any], cases: dict[str, dict[str, Any]]
) -> None:
    got = _measure(cases["invisible_overlay_not_blocking"], doc)
    assert got.rows[0].task_control_occlusion == 1.0
    assert got.rows[0].blocking_basis is BlockingBasis.NOT_BLOCKING
    assert got.task_control_occlusion == 0.0
    assert got.overlay_coverage == 0.0


# ── 폐쇄 어휘 · identity ─────────────────────────────────────────────────────
def test_unknown_interrupt_type_is_rejected() -> None:
    """`02 §10` — 자유 라벨을 만들지 않는다."""
    bad = InterruptObservation(
        interrupt_id="i1",
        interrupt_type="MEGA_POPUP",
        selector="#x",
        visible=True,
        box=BBox(0, 0, 10, 10),
        viewport_coverage=0.01,
    )
    with pytest.raises(ValueError, match="폐쇄 어휘"):
        measure_task_obstruction([bad], BBox(0, 0, 10, 10), Viewport(390, 844))


def test_duplicate_interrupt_id_is_rejected() -> None:
    """`02 §8` — observation identity 는 `observation_id + interrupt_id` 다."""
    one = InterruptObservation(
        interrupt_id="dup",
        interrupt_type="BANNER",
        selector="#a",
        visible=True,
        box=BBox(0, 0, 10, 10),
        viewport_coverage=0.01,
        traps_interaction=False,
    )
    with pytest.raises(ValueError, match="중복 interrupt_id"):
        measure_task_obstruction([one, one], BBox(0, 0, 10, 10), Viewport(390, 844))


def test_module_does_not_perform_dismissal() -> None:
    """이 모듈은 순수 함수다 — 조작 결과는 입력으로만 들어온다.

    `dismiss_attempted=False` 인 입력에서 `dismiss_succeeded` 가 저절로 채워지지 않는다.
    """
    interrupt = InterruptObservation(
        interrupt_id="i1",
        interrupt_type="BLOCKING_MODAL",
        selector="#m",
        visible=True,
        box=BBox(0, 0, 390, 844),
        viewport_coverage=1.0,
        intercepts_task_control=True,
        traps_interaction=True,
        dismiss_controls=(
            DismissControlObservation(
                selector="#m .close",
                accessible_name_source="닫기",
                matches_close_vocabulary=True,
                icon_only=True,
                hittable=True,
                viewport_overlap_css_px2=400,
            ),
        ),
        dismiss_attempted=False,
    )
    got = measure_task_obstruction([interrupt], BBox(10, 10, 100, 44), Viewport(390, 844))
    assert got.dismiss_succeeded is None
    assert got.forced_dismissal_count == 0
    assert got.dismissal_state is DismissalState.CONTROL_PRESENT_NOT_ATTEMPTED
