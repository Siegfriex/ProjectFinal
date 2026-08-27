"""W5P — `R32` 적용 지점 목록이 코드와 일치하는가.

**이 파일은 목록 문서와 코드의 정합만 본다.** `R32_VIOLATION` 으로 적힌 지점을
고치는 것은 이 lane 의 과업이 아니다 (W5P 는 열거만 한다).

정본: `control/v3/V3_0_1_SUCCESSOR_DELTA.md` `Δ39`(R32) · `Δ40`(단위·대조 명칭).
목록: `research/landing_accessibility/docs/v3/R32_APPLICATION_POINTS.md`
검사기: `landing_accessibility.v3_runner.r32_check`

대조군 이름은 `Δ40` 대로 `must_flag` / `must_not_flag` 다 — "양성/음성" 을 쓰지
않는다(이 프로젝트에서 그 말이 이미 두 뜻으로 쓰였다).
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
RESEARCH = REPO / "research" / "landing_accessibility"
sys.path.insert(0, str(RESEARCH / "src"))

from landing_accessibility.v3_runner.r32_check import (  # noqa: E402
    CONTROLS,
    check,
    document_path,
    oracle_verdicts,
    parse_document,
    r33_envelope_scan,
    sweep_candidates,
)


@pytest.fixture(scope="module")
def rows():
    return parse_document()


@pytest.fixture(scope="module")
def oracle():
    return oracle_verdicts()


def test_document_exists_and_parses(rows) -> None:
    assert document_path().is_file()
    assert len(rows) >= 60, "목록이 갑자기 줄었다면 표가 깨진 것이다"


@pytest.mark.parametrize("role", sorted(CONTROLS))
def test_controls(role: str, oracle, rows) -> None:
    """`must_flag` 는 반드시 잡히고 `must_not_flag` 는 잡히면 안 된다.

    **오라클과 문서 양쪽**에서 본다. 둘 중 하나만 보면 목록을 고쳐 통과시킬 수 있다.
    """
    point_id, expected = CONTROLS[role]
    assert point_id in oracle, f"{role} 대조군이 오라클에 없다: {point_id}"
    assert oracle[point_id].verdict == expected, (
        f"{role} 실패 — {point_id}: 기대={expected} · 오라클={oracle[point_id].verdict}\n"
        f"{oracle[point_id].detail}\n"
        "목록이 아니라 **방법**이 틀렸다."
    )
    doc = {r.point_id: r for r in rows}
    assert point_id in doc, f"{role} 대조군이 목록에 없다: {point_id}"
    assert doc[point_id].verdict == expected


def test_no_candidate_drifts_out_of_the_list(rows) -> None:
    """코드에 있는데 목록에 없는 후보가 생기면 실패한다."""
    listed = {r.point_id for r in rows}
    missing = sorted(set(sweep_candidates()) - listed)
    assert not missing, "목록에 없는 후보:\n  " + "\n  ".join(missing)


def test_list_matches_code(rows) -> None:
    """구조·표류·오라클 세 층 전부. 실패 목록을 그대로 보여준다."""
    failures = check()
    assert not failures, "\n".join(failures)


def test_r33_no_caller_passes_both_envelope_forms() -> None:
    """`Δ40/R33` 선행 확인 — 두 키를 함께 넘기는 fixture·테스트·호출부 실측.

    **`both == 0` 만 단언하지 않는다.** 빈 결과는 관측이 아니므로, 같은 검색이
    한쪽 키만 가진 봉투를 실제로 잡아내는지(대조군)를 함께 단언한다.
    """
    scan = r33_envelope_scan()
    assert scan["scroll_states_only"], "대조군 없음 — 검색이 동작하는지 알 수 없다"
    assert scan["raw_features_only"], "대조군 없음 — 검색이 동작하는지 알 수 없다"

    # 유일하게 허용되는 동거는 **raise 를 단언하는 부정 테스트** 뿐이다.
    unexpected = [s.where for s in scan["both"] if "test_w5c_surface_measure.py" not in s.where]
    assert not unexpected, (
        "두 형태를 동시에 넘기는 호출자·fixture 가 있다 — `Δ40/R33` 2단계 대상:\n  "
        + "\n  ".join(unexpected)
    )
