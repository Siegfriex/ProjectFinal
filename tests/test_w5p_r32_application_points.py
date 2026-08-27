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
    demo_sidecar_path,
    document_path,
    oracle_verdicts,
    parse_document,
    r33_envelope_scan,
    result_path,
    sweep_candidates,
    tool_sha256,
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


# ══════════════════════════════════════════════════════════════════════════
# `Δ46` — R35 4요소 · R40 결속 · exit 규약 · 사례 이름
# ══════════════════════════════════════════════════════════════════════════


@pytest.fixture(scope="module")
def result_doc():
    import json

    path = result_path()
    assert path.is_file(), f"검사기 산출이 없다 — r32_check 를 돌려라: {path}"
    return json.loads(path.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def demo_doc():
    import json

    path = demo_sidecar_path()
    assert path.is_file(), f"실증 sidecar 가 없다 — r32_control_failure_demo 를 돌려라: {path}"
    return json.loads(path.read_text(encoding="utf-8"))


def test_r35_four_elements_are_present(result_doc) -> None:
    """① 대조 목록 ② 결과 ③ 도구 경로 ④ 실패 시 동작의 실증."""
    roles = {c["role"] for c in result_doc["controls"]}
    assert roles == set(CONTROLS), "① 대조 목록이 CONTROLS 와 다르다"
    assert all("passed" in c and "observed" in c for c in result_doc["controls"]), "② 결과 없음"
    assert result_doc["status"] in {"PASS", "FAIL"}
    tool = result_doc["tool"]
    assert tool["path"].endswith("r32_check.py") and tool["sha256"], "③ 도구 경로/sha 없음"
    assert set(tool["exit_codes"]) == {"0", "1", "2"}, "③ exit 규약 미기재"
    assert result_doc["failure_demonstration"]["present"], "④ 실패 동작 실증 없음"


def test_r40_demonstration_is_bound_to_the_current_tool(result_doc, demo_doc) -> None:
    """`R40` — 실증은 그때의 도구 sha 에 묶인다. 현재 도구와 다르면 무효다."""
    assert demo_doc["tool_sha256"] == tool_sha256(), (
        "실증 당시의 검사기 sha 와 현재 검사기가 다르다 — 실증이 무효다. "
        "r32_control_failure_demo 를 다시 돌려라."
    )
    assert result_doc["failure_demonstration"]["valid_for_this_commit"] is True


def test_r40_binding_actually_invalidates_when_the_tool_changes(tmp_path) -> None:
    """결속이 **실제로 무효화하는지** 확인한다.

    `valid_for_this_commit: true` 가 항상 참이면 그 필드는 아무것도 말하지 않는다.
    sidecar 의 sha 를 바꿔 넣고 `false` 가 나오는지 본다.
    """
    import json

    from landing_accessibility.v3_runner import r32_check as mod

    stale = json.loads(demo_sidecar_path().read_text(encoding="utf-8"))
    stale["tool_sha256"] = "0" * 64
    sidecar = tmp_path / "R32_FAILURE_DEMO.json"
    sidecar.write_text(json.dumps(stale), encoding="utf-8")

    real = mod.demo_sidecar_path
    mod.demo_sidecar_path = lambda: sidecar  # type: ignore[assignment]
    try:
        result = mod.build_result([], verdicts=oracle_verdicts())
    finally:
        mod.demo_sidecar_path = real  # type: ignore[assignment]
    assert result["failure_demonstration"]["valid_for_this_commit"] is False


def test_every_demo_case_matches_the_declared_failure_behaviour(demo_doc) -> None:
    bad = [c["name"] for c in demo_doc["cases"] if not c["matches_declaration"]]
    assert not bad, f"선언과 다르게 동작한 사례: {bad}"
    assert demo_doc["all_match_declaration"] is True


def test_case_names_say_what_was_actually_demonstrated(demo_doc) -> None:
    """`R36`/`Δ46` — **이름도 주장이다.** 이름이 실증한 것과 다르면 거짓이다."""
    cases = {c["name"]: c for c in demo_doc["cases"]}

    must_flag_case = cases["must_flag_control_disabled_by_source_edit"]
    controls = {c["role"]: c["passed"] for c in must_flag_case["observed"]["output_controls"]}
    assert controls.get("must_flag") is False, (
        "이름은 must_flag 가 깨졌다고 주장하는데 산출은 통과라고 적었다 — 이름이 거짓이다"
    )
    assert "소스 변형" in must_flag_case["mutation"], "이름이 소스 변형이라 주장한다"

    unparseable = cases["document_unparseable"]
    assert unparseable["observed"]["exit"] == 2
    assert unparseable["observed"]["wrote_output"] is False, (
        "'검사가 돌지 않았다' 인데 산출을 덮었다 — 선언과 다르다"
    )

    deleted = cases["list_row_deleted"]
    deleted_controls = {c["role"]: c["passed"] for c in deleted["observed"]["output_controls"]}
    assert all(deleted_controls.values()), (
        "행 삭제는 대조군을 깨지 않는다 — 깼다면 이름이 실증한 것과 다르다"
    )


def test_exit_2_when_the_check_cannot_run(tmp_path) -> None:
    """미실행이 `exit 1`(= 실패) 과 같은 코드를 쓰면 둘을 구분할 수 없다 (`Δ46`)."""
    import subprocess

    broken = tmp_path / "broken.md"
    broken.write_text(
        "## 부록 A\n\n| point_id | 판정 | 판정근거 |\n|---|---|---|\n"
        "| `not-a-point-id` | R32_OK | READ |\n",
        encoding="utf-8",
    )
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "landing_accessibility.v3_runner.r32_check",
            "--doc",
            str(broken),
            "--no-write",
        ],
        cwd=REPO,
        env={"PYTHONPATH": str(RESEARCH / "src"), "PATH": "/usr/bin:/bin"},
        capture_output=True,
        text=True,
        timeout=300,
        check=False,
    )
    assert proc.returncode == 2, f"기대 exit 2, 실제 {proc.returncode}\n{proc.stderr[-800:]}"
    assert "검사가 돌지 않았다" in proc.stderr
