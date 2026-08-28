"""W5R — `R43` 실증기 자체의 회귀 시험 (`Δ48`).

**이 파일은 `verify_*` 가 실제로 실패한다는 것을 단언하지 않는다.** 그것은
`r43.check` 가 실행으로 실증하고 `R43_CHECK_RESULT.json` 에 남긴다. 여기서 지키는
것은 그보다 앞의 것 — **검사기의 대조군이 살아 있는가**다.

`Δ48` 의 발단이 정확히 이 자리였다: ``assert verify_retention_manifest(...)["ok"]
is True`` 는 깨질 수 없는 단언이었고, 그 테스트가 함수가 검증하지 않는다는 사실을
가렸다. 그래서 여기서는 **깨질 수 있는 것만** 단언한다 — 대조군의 관측값, 그리고
`R40` 결속이 거짓이 될 수 있다는 사실.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from landing_accessibility.v3_runner.r43 import check as r43

RESULT = Path(r43.result_path())
SIDECAR = Path(r43.demo_sidecar_path())


@pytest.fixture(scope="module")
def outcome() -> tuple[list[str], list[dict], list[dict]]:
    return r43.check()


def test_controls_hold(outcome) -> None:
    """`must_flag` / `must_not_flag` 가 전부 기대대로 나온다."""
    failures, results, _ = outcome
    by_id = {r["point_id"]: r for r in results}
    for role, (pid, want) in r43.CONTROLS.items():
        assert pid in by_id, f"{role}: probe 가 없다 — {pid}"
        assert by_id[pid]["verdict"] == want, (
            f"{role}: {pid} 기대={want} 관측={by_id[pid]['verdict']}"
        )
    assert not [f for f in failures if f.startswith("[대조]")]


def test_crash_is_not_counted_as_failure(outcome) -> None:
    """`R36` — 크래시는 실패가 아니다. 이것이 무너지면 목록 전체가 과대계상된다."""
    _, results, _ = outcome
    crash_only = next(r for r in results if r["point_id"] == "SYNTHETIC::verify_crash_only")
    assert crash_only["verdict"] == r43.CANNOT_FAIL
    assert crash_only["demonstrated_failure_inputs"] == []
    assert len(crash_only["crash_only_inputs"]) == 2


def test_enumeration_and_probes_do_not_drift(outcome) -> None:
    """열거된 계열 함수와 실증 목록이 1:1 이다."""
    failures, results, enumerated = outcome
    repo_ids = {r["point_id"] for r in enumerated}
    probe_ids = {r["point_id"] for r in results if r["kind"] != "SYNTHETIC"}
    assert repo_ids == probe_ids
    assert not [f for f in failures if f.startswith("[표류]")]


def test_every_baseline_passes(outcome) -> None:
    """baseline 이 통과하지 않으면 '실패시켰다' 가 아무 정보도 주지 않는다."""
    _, results, _ = outcome
    assert [r["point_id"] for r in results if not r["baseline_passes"]] == []


def test_vacuous_pass_axis_is_not_always_false(outcome) -> None:
    """축2 가 **실제로 무언가를 가른다**. 항상 거짓인 축은 아무것도 말하지 않는다."""
    _, results, _ = outcome
    flagged = [r["point_id"] for r in results if r["vacuous_pass"]]
    assert "evidence.py::verify_retention_manifest" in flagged
    assert len(flagged) < len(results), "모두 vacuous 면 그 축은 판별하지 않는다"


def test_r40_binding_can_be_false() -> None:
    """`R40` — 결속이 **거짓이 될 수 있음**이 sidecar 에 남아 있다."""
    if not SIDECAR.is_file():
        pytest.skip("sidecar 가 없다 — r43.control_failure_demo 를 먼저 돌려라")
    demo = json.loads(SIDECAR.read_text(encoding="utf-8"))
    binding = demo["binding_invalidation_test"]
    assert binding["sha_matches"]["valid_for_this_commit"] is True
    assert binding["sha_mutated"]["valid_for_this_commit"] is False
    assert binding["binding_is_informative"] is True


def test_declared_failure_behaviour_is_demonstrated() -> None:
    """`exit` 0/1/2 세 갈래가 전부 격리 사본에서 관측됐다."""
    if not SIDECAR.is_file():
        pytest.skip("sidecar 가 없다")
    demo = json.loads(SIDECAR.read_text(encoding="utf-8"))
    assert demo["all_match_declaration"] is True
    assert demo["all_names_verified"] is True  # R36
    assert {c["observed"]["exit"] for c in demo["cases"]} == {0, 1, 2}
    not_run = [c for c in demo["cases"] if c["observed"]["exit"] == 2]
    assert not_run and all(not c["observed"]["wrote_output"] for c in not_run)


def test_result_artifact_is_bound_to_current_tool() -> None:
    """산출이 현재 검사기 sha 에 묶여 있다 (`R40`)."""
    if not RESULT.is_file():
        pytest.skip("산출이 없다 — r43.check 를 먼저 돌려라")
    doc = json.loads(RESULT.read_text(encoding="utf-8"))
    demo = doc["failure_demonstration"]
    assert demo["tool_sha256_now"] == r43.tool_sha256()
    assert demo["valid_for_this_commit"] is True
