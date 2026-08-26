"""P-C LANE C — 실패주입 harness 가 실제로 차단하는가.

`02 §14`: *모든 guard 가 실제로 차단하는지 확인한다.*

guard 를 세워 두고 한 번도 태우지 않으면 `E000_V2_VALIDATED` 가 **비어 있는 근거로** 닫힌다.
그리고 차단만 태우면 **과탐**이 검증되지 않으므로, `A2 §6.3.1` 이 일부러 넣은
`MUST_PASS` 케이스(I-4 · I-14)도 함께 태운다.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
RESEARCH = REPO / "research" / "landing_accessibility"
sys.path.insert(0, str(RESEARCH / "src"))

from landing_accessibility.engine import failure_injection as fi  # noqa: E402
from landing_accessibility.engine.provenance import validate_provenance  # noqa: E402

CASES = fi.registry()


@pytest.fixture(scope="module")
def report(tmp_path_factory: pytest.TempPathFactory) -> dict:
    return fi.run_all(tmp_path_factory.mktemp("injection"))


def test_every_case_behaves_as_specified(report: dict) -> None:
    failures = report["failures"]
    assert not failures, "\n".join(
        f"{f['case_id']} ({f['rule']}): {f['outcome']} — {f['detail']}" for f in failures
    )
    assert report["as_expected"] == report["total"]


def test_report_carries_shadow_provenance(report: dict) -> None:
    validate_provenance(report["provenance"])
    assert report["provenance"]["fixture_only"] is True
    assert report["provenance"]["real_target_measurement"] is False


def test_the_02_section_14_list_is_covered() -> None:
    """`02 §14` 가 이름을 붙여 요구한 실패주입 8종이 전부 등록돼 있다."""
    ids = {c.case_id for c in CASES}
    for required in ("C-1", "C-2", "C-3", "C-4", "C-5", "C-9", "V-a", "V-b", "V-c"):
        assert required in ids, f"{required} 가 registry 에 없다"


def test_a2_injection_table_i1_to_i29_is_covered() -> None:
    """`A2 §6.3.1` 대응표 전건."""
    ids = {c.case_id for c in CASES}
    missing = [f"I-{n}" for n in range(1, 30) if f"I-{n}" not in ids]
    assert not missing, f"A2 §6.3.1 주입 케이스 누락: {missing}"
    for extra in ("I-25b", "I-25c", "I-28b"):
        assert extra in ids


def test_v_variants_a_to_g_are_covered() -> None:
    ids = {c.case_id for c in CASES}
    assert {f"V-{c}" for c in "abcdefg"} <= ids


def test_gate_kind_discrimination_cases_are_covered() -> None:
    """Q-9 — 판별·abstain·오판 세 방향이 모두 태워진다."""
    ids = {c.case_id for c in CASES}
    assert {f"Q9-{n}" for n in range(1, 8)} <= ids


def test_over_blocking_is_checked_not_only_blocking() -> None:
    must_pass = {c.case_id for c in CASES if c.expectation is fi.Expectation.MUST_PASS}
    assert {"I-4", "I-14"} <= must_pass
    assert len(must_pass) >= 4


def test_real_target_firewall_cases_are_blocked(report: dict) -> None:
    """가장 중요한 한 줄 — `REAL_TARGET` 은 어떤 경로로도 통과하지 못한다."""
    by_id = {r["case_id"]: r for r in report["results"]}
    for case_id in ("FW-1", "FW-2", "FW-3", "FW-4", "FW-5", "FW-6"):
        assert by_id[case_id]["outcome"] == "AS_EXPECTED"
        assert by_id[case_id]["expectation"] == "BLOCKED"
    assert by_id["FW-7"]["expectation"] == "MUST_PASS"  # 과탐 회귀검사


def test_case_ids_are_unique() -> None:
    ids = [c.case_id for c in CASES]
    assert len(ids) == len(set(ids))
