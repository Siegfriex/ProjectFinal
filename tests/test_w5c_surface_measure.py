"""W5C — `v3_runner/surface.py::measure_surface` 검증.

**이 파일의 PASS/FAIL 은 합성 fixture 에 대한 측정함수 test 결과다.** 실제 서비스에 대한
research finding 이 아니며 그렇게 인용할 수 없다. fixture 는
`research/landing_accessibility/fixtures/w5c_surface/*.json` 이고, 각 case 의 `comment` 가
"무엇을 검증하려는 것인가" 를 적는다.

정본: `SSOTV3/04_FLOW_CODEBOOK_v3.0.md` §4 표 · §5 · §6 · §7,
      `SSOTV3/02_DATA_SCHEMA_v3.0.md` §3 `fact_surface_state`,
      `SSOTV3/00_SSOT_v3.0_CROSS_SERVICE_FLOW.md` §8.

각 categorical 필드는 **모든 값에 대해 그 값이 나오는 입력과 나오지 않는 대조 입력을 쌍**으로
갖는다. 대조 입력이 없으면 "그 값을 낼 줄 안다" 는 것만 보이고 "그 값을 남발하지 않는다" 는
것은 못 보이기 때문이다.
"""

from __future__ import annotations

import json
import sys
from dataclasses import asdict
from pathlib import Path
from typing import Any

import pytest

REPO = Path(__file__).resolve().parents[1]
RESEARCH = REPO / "research" / "landing_accessibility"
FIXTURES = RESEARCH / "fixtures" / "w5c_surface"
sys.path.insert(0, str(RESEARCH / "src"))

from landing_accessibility.engine.l0_collector import (  # noqa: E402
    Min4ProbeContractError,
    min4_sort_key,
)
from landing_accessibility.v3_runner.surface import (  # noqa: E402
    CARD_MIN_AREA_CSS_PX2,
    CARD_MIN_SIDE_CSS_PX,
    NOT_OBSERVED,
    ZONE_BOTTOM_Y_MIN,
    ZONE_LEFT_X_MAX,
    ZONE_RIGHT_X_MIN,
    ZONE_TOP_Y_MAX,
    SurfaceMeasurement,
    measure_surface,
    normalize_label,
)

# ── 04 §4 표가 정의한 값 집합. 이 밖의 값을 내면 실패다 (새 enum 값 추가 금지). ──
ENTRY_ZONE_VALUES = {
    "TOP_LEFT",
    "TOP_CENTER",
    "TOP_RIGHT",
    "MID",
    "BOTTOM",
    "FLOATING",
    "DRAWER",
}
ENTRY_CONTROL_TYPE_VALUES = {
    "TEXT_LINK",
    "TEXT_BUTTON",
    "ICON_TEXT",
    "ICON_ONLY",
    "TAB",
    "BOTTOM_NAV",
    "HAMBURGER",
    "CARD",
    "SEARCHBOX",
    "LIST_ITEM",
    "OTHER",
}
ENTRY_LABEL_MODALITY_VALUES = {
    "EXPLICIT_TEXT",
    "ICON_TEXT",
    "ICON_ONLY_AX_NAMED",
    "ICON_ONLY_UNNAMED",
    "HIDDEN_UNTIL_REVEAL",
}
ACCESSIBLE_NAME_SOURCE_VALUES = {
    "VISIBLE_TEXT",
    "ARIA_LABEL",
    "ARIA_LABELLEDBY",
    "LABEL",
    "ALT",
    "TITLE",
    "VALUE",
    "MIXED",
    "NONE",
}
LABEL_RELATION_VALUES = {
    "MATCH",
    "SEMANTIC_EQUIV",
    "DIFFERENT",
    "VISIBLE_ONLY",
    "AX_ONLY",
    "NONE",
}


def _load_cases() -> list[dict[str, Any]]:
    assert FIXTURES.is_dir(), f"fixture 디렉터리 없음: {FIXTURES}"
    out: list[dict[str, Any]] = []
    for path in sorted(FIXTURES.glob("*.json")):
        doc = json.loads(path.read_text(encoding="utf-8"))
        for c in doc["cases"]:
            c["_fixture_file"] = path.name
            out.append(c)
    assert out, "fixture case 가 하나도 없다"
    return out


CASES = _load_cases()
CASE_BY_ID = {c["case_id"]: c for c in CASES}


def run(case: dict[str, Any]) -> SurfaceMeasurement:
    return measure_surface(case["probe_state"], case["task_control"], tuple(case["viewport"]))


# ── fixture 자체의 무결성 ────────────────────────────────────────────────────


def test_fixture_case_ids_are_unique() -> None:
    ids = [c["case_id"] for c in CASES]
    assert len(ids) == len(set(ids)), "case_id 중복"


def test_every_fixture_case_has_a_comment() -> None:
    """왜 이 입력을 넣었는지 적히지 않은 case 는 회귀 때 해석할 수 없다."""
    for c in CASES:
        assert c["comment"].strip(), c["case_id"]


# ── case 표 전체 ─────────────────────────────────────────────────────────────


@pytest.mark.parametrize("case", CASES, ids=[c["case_id"] for c in CASES])
def test_expected_fields(case: dict[str, Any]) -> None:
    m = run(case)
    got = asdict(m)
    for field, expected in case["expected"].items():
        actual = got[field]
        if isinstance(actual, tuple) and isinstance(expected, list):
            # JSON 은 tuple 을 표현하지 못한다 — 순서를 유지한 채 비교 형만 맞춘다.
            expected = tuple(expected)
        if isinstance(expected, float):
            assert actual == pytest.approx(expected, abs=1e-6), (
                f"{case['case_id']}.{field}: {actual!r} != {expected!r}"
            )
        else:
            assert actual == expected, (
                f"{case['case_id']}.{field}: {actual!r} != {expected!r} ({case['comment']})"
            )


@pytest.mark.parametrize("case", CASES, ids=[c["case_id"] for c in CASES])
def test_expected_notes(case: dict[str, Any]) -> None:
    m = run(case)
    for note in case["notes_contains"]:
        assert any(n.split(":", 1)[0] == note for n in m.notes), (
            f"{case['case_id']}: note {note!r} 없음 — 실제 {m.notes!r}"
        )


@pytest.mark.parametrize("case", CASES, ids=[c["case_id"] for c in CASES])
def test_categorical_values_stay_inside_codebook(case: dict[str, Any]) -> None:
    """04 §4 표에 없는 값을 새로 만들지 않는다.

    유일한 예외는 Δ15 GAP-04 가 규정한 결측 표지 `NOT_OBSERVED` 다. 그것은 새 관측
    범주가 아니라 "관측하지 못했다" 는 표기이며, 아래 별도 test 가 그 표지가 실제
    미관측일 때만 나오는지 확인한다.
    """
    m = run(case)
    assert m.entry_zone in ENTRY_ZONE_VALUES | {NOT_OBSERVED}
    assert m.entry_control_type in ENTRY_CONTROL_TYPE_VALUES | {NOT_OBSERVED}
    assert m.entry_label_modality in ENTRY_LABEL_MODALITY_VALUES | {NOT_OBSERVED}
    assert m.accessible_name_source in ACCESSIBLE_NAME_SOURCE_VALUES | {NOT_OBSERVED}
    assert m.label_relation in LABEL_RELATION_VALUES | {NOT_OBSERVED}


@pytest.mark.parametrize("case", CASES, ids=[c["case_id"] for c in CASES])
def test_missing_representation_is_consistent_within_a_row(case: dict[str, Any]) -> None:
    """Δ15 GAP-04 — 한 행 안에서 결측 표현이 섞이지 않는다.

    수치 미관측은 `None`(`0` 아님), 범주 미관측은 `NOT_OBSERVED`(빈 문자열 아님).
    A 가 든 선례: probe 없는 행에서 `max_overlay_coverage` 는 `0.0` 인데 같은 행의
    `primary_action_visible_initial` 은 `null` 이라 한 행 안에서 표기가 어긋났다.
    """
    m = run(case)
    if not m.dom_control_observed:
        # DOM 관측이 없으면 기하·범주 전부 결측 표기여야 한다.
        assert m.entry_x_norm is None and m.entry_y_norm is None
        assert m.entry_x_norm_raw is None and m.entry_y_norm_raw is None
        assert m.entry_box_css_px is None
        assert m.entry_zone == NOT_OBSERVED
        assert m.entry_control_type == NOT_OBSERVED
        assert m.entry_label_modality == NOT_OBSERVED
        assert m.entry_observed_state == NOT_OBSERVED
    else:
        # 관측했으면 범주에 결측 표지가 섞이지 않는다.
        assert m.entry_control_type != NOT_OBSERVED
        assert m.entry_label_modality != NOT_OBSERVED
        assert m.entry_observed_state != NOT_OBSERVED
    for value in (m.entry_x_norm, m.entry_y_norm, m.entry_x_norm_raw, m.entry_y_norm_raw):
        assert value is None or isinstance(value, float)
    assert "" not in {
        m.entry_zone,
        m.entry_control_type,
        m.entry_label_modality,
        m.accessible_name_source,
        m.label_relation,
        m.entry_observed_state,
    }


@pytest.mark.parametrize("case", CASES, ids=[c["case_id"] for c in CASES])
def test_normalized_coordinates_are_bounded_and_raw_is_preserved(
    case: dict[str, Any],
) -> None:
    """04 §6 — zone 은 요약값이고 정규화 원좌표를 버리지 않는다."""
    m = run(case)
    if m.entry_x_norm is None:
        assert m.entry_y_norm is None
        assert m.entry_box_css_px is None
        assert m.entry_zone == NOT_OBSERVED
        return
    assert 0.0 <= m.entry_x_norm <= 1.0
    assert m.entry_y_norm is not None and 0.0 <= m.entry_y_norm <= 1.0
    assert m.entry_x_norm_raw is not None and m.entry_y_norm_raw is not None
    assert m.entry_box_css_px is not None
    b = m.entry_box_css_px
    assert m.entry_x_norm_raw == pytest.approx((b["x"] + b["w"] / 2) / m.viewport_width)
    assert m.entry_y_norm_raw == pytest.approx((b["y"] + b["h"] / 2) / m.viewport_height)


@pytest.mark.parametrize("case", CASES, ids=[c["case_id"] for c in CASES])
def test_pure_function_does_not_mutate_inputs(case: dict[str, Any]) -> None:
    """순수함수다 — 입력 dict 를 건드리지 않는다."""
    before = json.dumps(
        {"p": case["probe_state"], "t": case["task_control"]},
        ensure_ascii=False,
        sort_keys=True,
    )
    run(case)
    after = json.dumps(
        {"p": case["probe_state"], "t": case["task_control"]},
        ensure_ascii=False,
        sort_keys=True,
    )
    assert before == after


@pytest.mark.parametrize("case", CASES, ids=[c["case_id"] for c in CASES])
def test_deterministic(case: dict[str, Any]) -> None:
    assert run(case) == run(case)


# ── categorical 값 coverage: 모든 값이 최소 한 번 산출되는가 ────────────────


def _produced(attr: str) -> set[str | None]:
    return {getattr(run(c), attr) for c in CASES}


def test_not_observed_marker_appears_only_when_nothing_was_observed() -> None:
    """결측 표지가 실측값 자리를 대신 차지하지 않는다."""
    for c in CASES:
        m = run(c)
        if NOT_OBSERVED in (m.entry_control_type, m.entry_label_modality, m.entry_zone):
            assert not m.dom_control_observed, c["case_id"]


def test_all_entry_zone_values_are_covered() -> None:
    assert _produced("entry_zone") >= ENTRY_ZONE_VALUES


def test_all_entry_control_type_values_are_covered() -> None:
    assert _produced("entry_control_type") >= ENTRY_CONTROL_TYPE_VALUES


def test_all_entry_label_modality_values_are_covered() -> None:
    assert _produced("entry_label_modality") >= ENTRY_LABEL_MODALITY_VALUES


def test_all_accessible_name_source_values_are_covered() -> None:
    assert _produced("accessible_name_source") >= ACCESSIBLE_NAME_SOURCE_VALUES


def test_label_relation_values_are_covered_except_semantic_equiv() -> None:
    produced = _produced("label_relation")
    assert produced >= (LABEL_RELATION_VALUES - {"SEMANTIC_EQUIV"})


# ── 04 §5 — SEMANTIC_EQUIV 는 고정 synonym map 없이 나오면 안 된다 ──────────


def test_semantic_equiv_is_never_produced_without_a_fixed_synonym_map() -> None:
    """04 §5: embedding similarity 로 자동 merge 금지. 고정 synonym map 이 없으므로
    사람 눈에 동의어인 쌍이라도 DIFFERENT 여야 한다."""
    assert "SEMANTIC_EQUIV" not in _produced("label_relation")


def test_synonym_pair_stays_different() -> None:
    m = run(CASE_BY_ID["lr_different_synonym_not_merged"])
    assert m.visible_label_text == "이체"
    assert m.accessible_name == "송금"
    assert m.label_relation == "DIFFERENT"


# ── 00 §8 — visible label 과 accessible name 의 분리 ─────────────────────────


def test_icon_only_named_vs_unnamed_differ_only_by_aria_label() -> None:
    """구조가 완전히 동일하고 `aria-label` 유무만 다른 쌍. 접근성 관점에서 전혀 다른
    상태이므로 `entry_label_modality` 가 갈라져야 한다."""
    named = CASE_BY_ID["lm_icon_only_ax_named"]
    unnamed = CASE_BY_ID["lm_icon_only_unnamed"]

    # 두 fixture 의 차이가 정말 aria-label / AX 이름뿐인지 먼저 확인한다.
    def strip(case: dict[str, Any]) -> str:
        raw = json.loads(json.dumps(case["probe_state"], ensure_ascii=False))
        for row in raw["raw_features"]["primary_action_candidates"]:
            row.pop("aria_label", None)
        for row in raw["raw_features"]["accessible_name_sources"]:
            row.pop("aria_label", None)
        return json.dumps(raw, ensure_ascii=False, sort_keys=True)

    assert strip(named) == strip(unnamed), "두 fixture 가 aria-label 외에도 다르다"

    a, b = run(named), run(unnamed)
    assert a.entry_control_type == b.entry_control_type == "ICON_ONLY"
    assert a.visible_label_text is None and b.visible_label_text is None
    assert a.entry_label_modality == "ICON_ONLY_AX_NAMED"
    assert b.entry_label_modality == "ICON_ONLY_UNNAMED"
    assert a.accessible_name == "검색"
    assert b.accessible_name is None


def test_accessible_name_is_never_inferred_from_dom() -> None:
    """`ax_node` 가 없으면 DOM 속성으로 accessible name 을 지어내지 않는다 (00 §8)."""
    m = run(CASE_BY_ID["ns_ax_node_absent"])
    assert m.visible_label_text == "이체"
    assert m.accessible_name is None
    assert m.accessible_name_source == "NONE"
    assert m.label_relation == "VISIBLE_ONLY"
    assert "AX_NODE_ABSENT" in m.notes


def test_visible_label_and_accessible_name_are_stored_separately() -> None:
    """두 값이 다를 때 어느 한쪽으로 덮어쓰지 않는다 (04 §7)."""
    m = run(CASE_BY_ID["ns_aria_label_beats_visible_text"])
    assert m.visible_label_text == "이체"
    assert m.accessible_name == "계좌이체하기"
    assert m.accessible_name_source == "ARIA_LABEL"
    assert m.label_relation == "DIFFERENT"


# ── zone 경계 — A `T-A-V3-STEP1-003` R7 확정 정의를 정확값으로 고정한다 ────
#
# 밴드는 `y < 1/3 → TOP`, `1/3 <= y < 2/3 → MID`, `y >= 2/3 → BOTTOM` 이고 TOP 안에서만
# x 를 삼등분한다. 하한 포함 · 상한 배제 `[a, b)`.
#
# 부동소수 때문에 `(y + h/2) / VH` 가 정확히 1/3 이 되는 390x844 박스를 만들 수 없다.
# 그래서 경계 "정확값" 은 300x300 viewport 로 잰다 — `100/300` 과 `200/300` 은 IEEE754
# 에서 각각 `1/3`, `2/3` 과 비트단위로 같다(아래 test 가 그 전제를 먼저 확인한다).

EXACT_VW = EXACT_VH = 300


def _zone_probe(cx: float, cy: float) -> tuple[dict[str, Any], dict[str, Any]]:
    sel = "body>main>a"
    b = {"x": cx - 1.0, "y": cy - 1.0, "w": 2.0, "h": 2.0}
    probe = {
        "raw_features": {
            "primary_action_candidates": [
                {
                    "selector": sel,
                    "tag": "a",
                    "role": None,
                    "aria_label": None,
                    "visible_text": "이체",
                    "href": "#",
                    "in_list_container": False,
                    "box": b,
                    "viewport_visible": True,
                    "hittable": True,
                    "dom_order": 0,
                }
            ],
            "accessible_name_sources": [],
        }
    }
    return probe, {"selector": sel}


def _zone_at(cx: float, cy: float) -> str | None:
    probe, tc = _zone_probe(cx, cy)
    return measure_surface(probe, tc, (EXACT_VW, EXACT_VH)).entry_zone


def test_exact_boundary_construction_is_really_exact() -> None:
    """경계 정확값 test 가 의미를 가지려면 분수가 비트단위로 일치해야 한다."""
    assert 100 / EXACT_VH == ZONE_TOP_Y_MAX == 1.0 / 3.0
    assert 200 / EXACT_VH == ZONE_BOTTOM_Y_MIN == 2.0 / 3.0
    assert 100 / EXACT_VW == ZONE_LEFT_X_MAX
    assert 200 / EXACT_VW == ZONE_RIGHT_X_MIN


@pytest.mark.parametrize(
    ("cy", "expected", "why"),
    [
        (99.9, "TOP_CENTER", "y=1/3 바로 아래 → 아직 TOP"),
        (100.0, "MID", "y 가 정확히 1/3 → 하한 포함이므로 MID (A T-A-FC-001)"),
        (100.1, "MID", "y=1/3 바로 위 → MID"),
        (199.9, "MID", "y=2/3 바로 아래 → 아직 MID"),
        (200.0, "BOTTOM", "y 가 정확히 2/3 → 하한 포함이므로 BOTTOM"),
        (200.1, "BOTTOM", "y=2/3 바로 위 → BOTTOM"),
    ],
)
def test_y_band_boundaries_are_lower_inclusive(cy: float, expected: str, why: str) -> None:
    assert _zone_at(150.0, cy) == expected, why


@pytest.mark.parametrize(
    ("cx", "expected", "why"),
    [
        (99.9, "TOP_LEFT", "x=1/3 바로 아래 → TOP_LEFT"),
        (100.0, "TOP_CENTER", "x 가 정확히 1/3 인 점은 TOP 이자 TOP_CENTER 다"),
        (100.1, "TOP_CENTER", "x=1/3 바로 위 → TOP_CENTER"),
        (199.9, "TOP_CENTER", "x=2/3 바로 아래 → 아직 TOP_CENTER"),
        (200.0, "TOP_RIGHT", "x 가 정확히 2/3 → 하한 포함이므로 TOP_RIGHT"),
        (200.1, "TOP_RIGHT", "x=2/3 바로 위 → TOP_RIGHT"),
    ],
)
def test_x_thirds_inside_top_band_are_lower_inclusive(cx: float, expected: str, why: str) -> None:
    assert _zone_at(cx, 30.0) == expected, why


@pytest.mark.parametrize("cy", [150.0, 250.0])
@pytest.mark.parametrize("cx", [1.0, 99.9, 100.0, 200.0, 299.0])
def test_mid_and_bottom_never_split_by_x(cx: float, cy: float) -> None:
    """MID/BOTTOM 에는 x 삼등분을 적용하지 않는다 — 04 값 목록에 MID_LEFT 류가 없다."""
    zone = _zone_at(cx, cy)
    assert zone in {"MID", "BOTTOM"}
    assert zone == ("MID" if cy < 200.0 else "BOTTOM")


# ── 구조적 override 는 기하를 덮되 좌표는 덮지 않는다 ───────────────────────


@pytest.mark.parametrize(
    ("case_id", "expected_zone"),
    [
        ("zone_floating", "FLOATING"),
        ("zone_floating_sticky", "FLOATING"),
        ("zone_drawer", "DRAWER"),
        ("zone_drawer_beats_floating", "DRAWER"),
    ],
)
def test_structural_override_keeps_raw_coordinates(case_id: str, expected_zone: str) -> None:
    """override 가 적용돼도 `entry_x_norm`/`entry_y_norm` 은 기하 그대로다.

    04 §6 — 요약값이 원자료를 덮지 않는다. 원좌표가 남아 있으면 zone 은 언제든 재도출
    가능하므로 zone 정의가 바뀌어도 재수집이 필요 없다.
    """
    baseline = run(CASE_BY_ID["zone_mid"])
    assert baseline.entry_zone == "MID"

    m = run(CASE_BY_ID[case_id])
    assert m.entry_zone == expected_zone
    assert m.entry_x_norm == baseline.entry_x_norm
    assert m.entry_y_norm == baseline.entry_y_norm
    assert m.entry_x_norm_raw == baseline.entry_x_norm_raw
    assert m.entry_y_norm_raw == baseline.entry_y_norm_raw
    assert m.entry_box_css_px == baseline.entry_box_css_px


def test_drawer_wins_over_floating() -> None:
    """둘 다 성립하면 DRAWER — reveal 필요 여부가 더 큰 구조적 부담이라는 A 판단."""
    tc = {
        "selector": "body>header>a",
        "ax_node": {"role": "link", "name": "이체", "name_computed": True},
        "nav_container_type": "BOTTOM_SHEET",
        "computed_position": "fixed",
    }
    probe = CASE_BY_ID["zone_mid"]["probe_state"]
    assert measure_surface(probe, tc, (390, 844)).entry_zone == "DRAWER"


def test_zone_constants_match_the_preregistered_definition() -> None:
    """A `T-A-V3-STEP1-003` R7 이 확정한 수치 그대로여야 한다 (W5C 가 정한 값이 아니다)."""
    assert ZONE_TOP_Y_MAX == 1.0 / 3.0
    assert ZONE_BOTTOM_Y_MIN == 2.0 / 3.0
    assert ZONE_LEFT_X_MAX == 1.0 / 3.0
    assert ZONE_RIGHT_X_MIN == 2.0 / 3.0


def test_card_thresholds_are_declared_as_numbers() -> None:
    """CARD 임계는 04 에 없어 W5C 가 정한 값이다. 상수로 노출돼 있어야 감사할 수 있다."""
    assert CARD_MIN_AREA_CSS_PX2 == 8000.0
    assert CARD_MIN_SIDE_CSS_PX == 64.0


# ── normalize_label 자체 ─────────────────────────────────────────────────────


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        (None, ""),
        ("", ""),
        ("  ", ""),
        ("계좌  이체", "계좌 이체"),
        ("\n계좌\t이체\r\n", "계좌 이체"),
        ("ＩＤ", "ID"),  # noqa: RUF001 — 전각 입력이 test data 자체다
        ("ﾒﾆｭｰ", "メニュー"),
        ("Login", "Login"),
    ],
)
def test_normalize_label(raw: str | None, expected: str) -> None:
    assert normalize_label(raw) == expected


def test_normalize_label_does_not_casefold() -> None:
    """04 §5 의 'exact' 를 대소문자 접기로 느슨하게 만들지 않는다."""
    assert normalize_label("Login") != normalize_label("login")


# ── 입력 계약 ────────────────────────────────────────────────────────────────


def test_missing_selector_raises() -> None:
    with pytest.raises(ValueError, match="selector"):
        measure_surface({"raw_features": {}}, {}, (390, 844))


@pytest.mark.parametrize("viewport", [(0, 844), (390, 0), (-1, 844)])
def test_non_positive_viewport_raises(viewport: tuple[int, int]) -> None:
    with pytest.raises(ValueError, match="viewport"):
        measure_surface({"raw_features": {}}, {"selector": "a"}, viewport)


def test_empty_probe_is_reported_not_guessed() -> None:
    """probe 가 비어 있을 때 값을 지어내지 않고 note 로 남긴다."""
    m = measure_surface({"raw_features": {}}, {"selector": "body>a"}, (390, 844))
    assert m.entry_x_norm is None  # GAP-04 — 0 이 아니라 null
    assert m.entry_zone == NOT_OBSERVED  # GAP-04 — 빈 문자열도 실측값도 아니다
    assert m.accessible_name is None
    assert m.entry_observed_state == NOT_OBSERVED
    assert "TASK_CONTROL_NOT_IN_PROBE" in m.notes


def test_measurement_is_frozen() -> None:
    m = run(CASE_BY_ID["lr_match"])
    with pytest.raises(Exception):  # noqa: B017 — dataclasses.FrozenInstanceError
        m.entry_zone = "MID"  # type: ignore[misc]


# ══════════════════════════════════════════════════════════════════════════
# Δ15 — A `T-A-V3-STEP1-012` 가 추가한 필드와 정의
# ══════════════════════════════════════════════════════════════════════════


def test_entry_observed_state_declares_post_reveal() -> None:
    """GAP-07 — reveal-gated control 의 행은 자기 기하가 reveal 이후 것임을 선언한다.

    A 근거: 한 시점을 전제로 두면 어떤 행은 그 전제를 어기고 그것이 조용히 남는다.
    행이 자기 시점을 들고 있으면 어긴다는 개념 자체가 사라진다.
    """
    m = run(CASE_BY_ID["d15_nav_container_chain_drawer_innermost"])
    assert m.entry_observed_state == "POST_REVEAL:LEFT_DRAWER"
    assert m.entry_zone == "DRAWER"

    plain = run(CASE_BY_ID["d15_no_reveal_declares_scroll_state"])
    assert plain.entry_observed_state == "S0"


def test_entry_observed_state_does_not_collide_with_s0_visibility() -> None:
    """`s0_task_control_visible` 은 여전히 S0 사실이다 — 두 변수는 다른 것을 잰다."""
    m = run(CASE_BY_ID["sv_first_visible_at_s1"])
    assert m.s0_task_control_visible is False
    assert m.first_visible_scroll_state == "S1"
    assert m.entry_observed_state == "S1"


def test_nav_container_type_is_the_innermost_container() -> None:
    """GAP-06 — hamburger 안 accordion 이면 최내곽 INLINE_EXPAND 이고 chain 은 보존된다."""
    m = run(CASE_BY_ID["d15_nav_container_chain_innermost"])
    assert m.nav_container_type == "INLINE_EXPAND"
    assert m.nav_container_chain == ("HAMBURGER", "INLINE_EXPAND")


def test_nav_container_chain_mismatch_is_reported_not_silently_dropped() -> None:
    m = run(CASE_BY_ID["d15_nav_container_chain_type_mismatch"])
    assert m.nav_container_type == "INLINE_EXPAND"
    assert "NAV_CONTAINER_CHAIN_TYPE_MISMATCH" in m.notes


@pytest.mark.parametrize(
    ("case_id", "dom", "ax", "diverges"),
    [
        ("sv_control_absent_from_probe", False, True, True),
        ("d15_dom_present_ax_absent_diverges", True, False, True),
        ("d15_dom_present_ax_present_no_divergence", True, True, False),
        ("d15_ax_node_not_supplied_is_not_divergence", True, False, False),
        ("d15_ax_ignored_node_is_not_observed", True, False, True),
    ],
)
def test_dom_ax_divergence_records_both_sides(
    case_id: str, dom: bool, ax: bool, diverges: bool
) -> None:
    """둘이 다를 때 어느 쪽도 우선하지 않는다 — 둘 다 기록하고 플래그를 세운다.

    한쪽을 정본으로 삼으면 그 divergence 가 데이터에서 사라진다. 그리고 그것은 보조기술
    사용자와 시각 사용자가 다른 화면을 보고 있다는 관측이므로 결과다 (00 §8 의 확장).
    """
    m = run(CASE_BY_ID[case_id])
    assert m.dom_control_observed is dom
    assert m.ax_control_observed is ax
    assert m.dom_ax_divergence is diverges


def test_dom_absent_but_ax_present_keeps_the_accessible_name() -> None:
    """DOM 이 못 본 control 이라도 AX 가 준 이름은 버리지 않는다."""
    m = run(CASE_BY_ID["sv_control_absent_from_probe"])
    assert m.accessible_name == "이체"
    assert m.dom_ax_divergence is True
    assert m.entry_control_type == NOT_OBSERVED


# ── GAP-05 — s0 가시성과 occlusion 은 독립이다 ─────────────────────────────


def test_hit_testability_gates_s0_visibility() -> None:
    """bbox 가 viewport 와 교차해도 hit-testable 하지 않으면 보이는 것이 아니다."""
    hidden = run(CASE_BY_ID["d15_hittable_false_is_not_visible"])
    shown = run(CASE_BY_ID["d15_hittable_true_is_visible"])
    assert hidden.s0_task_control_visible is False
    assert shown.s0_task_control_visible is True
    assert hidden.entry_box_css_px == shown.entry_box_css_px


def test_surface_measurement_has_no_occlusion_derivation() -> None:
    """GAP-05 — `s0_task_control_visible` 과 `task_control_occlusion` 은 독립이다.

    A 근거: 90% 가려져도 노출된 모서리에서 hit-testable 이면 보이는 것이고, 0% 가려져도
    viewport 밖이면 보이지 않는 것이다. 파생 관계를 만들면 없는 인과를 스키마에 새기게
    된다. 그래서 이 모듈은 occlusion 을 필드로 갖지도, 입력으로 소비하지도 않는다.
    """
    assert not hasattr(SurfaceMeasurement, "task_control_occlusion")
    assert "task_control_occlusion" not in asdict(run(CASE_BY_ID["lr_match"]))

    base = CASE_BY_ID["d15_hittable_true_is_visible"]
    with_occlusion = dict(base["task_control"])
    with_occlusion["task_control_occlusion"] = 0.97
    m = measure_surface(base["probe_state"], with_occlusion, tuple(base["viewport"]))
    assert m == run(base), "occlusion 값이 surface 측정을 바꾸면 안 된다"


# ── W5G 요구 — `min4_sort_key` 의 `dom_order` 계약 ──────────────────────────


def test_fixture_candidates_satisfy_the_dom_order_contract() -> None:
    """`min4_sort_key` 는 `dom_order` 가 없으면 `Min4ProbeContractError` 를 던진다.

    `measure_surface` 는 후보 dict 를 만들지도 변형하지도 않지만, 이 모듈이 소비하는
    probe 형태가 그 계약을 만족하는지는 fixture 로 고정해 둔다.
    """
    seen = 0
    for c in CASES:
        probe = c["probe_state"]
        states = probe.get("scroll_states") or [probe]
        for st in states:
            for row in st.get("raw_features", {}).get("primary_action_candidates", []):
                min4_sort_key(row)
                seen += 1
    assert seen > 0


def test_dom_order_contract_is_a_hard_error_not_a_default() -> None:
    """계약 위반을 기본값 0 으로 조용히 흡수하지 않는다는 것을 대조로 고정한다."""
    with pytest.raises(Min4ProbeContractError):
        min4_sort_key({"selector": "body>a", "marked_primary": False})
