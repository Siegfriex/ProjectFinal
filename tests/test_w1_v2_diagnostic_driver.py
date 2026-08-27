"""`scripts/run_v2_diagnostic_pilot.py` — V2_DIAGNOSTIC 전용 구동기 층 검증
(`T-B-BLK-008`, A 결정 (ii): `run_e001_real.py`는 손대지 않고 신규 전용 구동기를 만든다).

## 왜 이 파일이 필요한가 — 로더 층과 구동기 층은 별개다

`tests/test_w1_v2_diagnostic_scope.py`가 이미 `firewall.load_v2_diagnostic_allowlist`
/`load_v2_diagnostic_targets`(로더 층)의 4방향(허용/밖 거부/변조 거부/부재 거부)을
고정했다. 이 파일은 **구동기 층**을 고정한다 — B(coordinator) 원문: "로더가 옳아도
구동기가 로더를 안 부르면 소용없다는 게 애초에 `T-B-BLK-008`의 요지였다." 그래서
여기서는 로더 함수를 직접 부르지 않고 **구동기의 `main()`을 실제로 호출**해서
그 셋(12 target 통과·manifest 밖 거부·sha 변조 거부)이 성립하는지 본다.

## 이 파일의 어떤 테스트도 REAL_TARGET 에 접속하지 않는다

`--check-only`(항해 자체를 하지 않는다) 또는 `BatchRunner.run`을 monkeypatch 로
가로챈 상태로만 구동기를 호출한다 — 이 세션 전체의 REAL_TARGET 접속 흔적 0건을
유지한다(A `T-A-BLK-008-DECIDE-AND-PAUSE`: "A 가 정지한 동안 launch 하지 않는다").

## 핵심 요구 — scope 는 코드에 박혀 있다

A 원문(강한 요구): "신규 구동기는 scope 인자를 받지 않는다.
`ExecutionScope.V2_DIAGNOSTIC`을 하드코딩한다 — 인자로 `E001_FULL`을 넘길 수 있으면
구동기 자체가 방어층이 되지 못한다." 아래 "5. scope 하드코딩" 절이 이걸 세 가지
독립된 방식(소스 정적분석·argparse 인자 부재·env 변수 무시)으로 고정한다 —
`D-R0-70-3`/`D-R0-65-3`와 같은 이유로 하나만 보지 않는다.
"""

from __future__ import annotations

import importlib.util
import json
import os
import sys
from pathlib import Path
from typing import Any

import pytest

REPO = Path(__file__).resolve().parents[1]
RESEARCH = REPO / "research" / "landing_accessibility"
DRIVER_PATH = RESEARCH / "scripts" / "run_v2_diagnostic_pilot.py"
MANIFEST_FIXTURE = (
    Path(__file__).resolve().parent / "fixtures" / "w1_diagnostic_pilot_manifest_v2.json"
)

sys.path.insert(0, str(RESEARCH / "src"))

from landing_accessibility.e001_runner import real_executor as real_executor_module  # noqa: E402
from landing_accessibility.e001_runner.batch import DUPLICATE_SUPPRESSED_OUTCOME  # noqa: E402
from landing_accessibility.engine import firewall  # noqa: E402
from landing_accessibility.engine.firewall import (  # noqa: E402
    DIAGNOSTIC_PILOT_MANIFEST_SHA256,
    AllowlistUnavailableError,
    ExecutionScope,
    ExecutionScopeBlockedError,
    ReleaseDocument,
    TargetNotAllowlistedError,
)


def _load_driver():
    """`scripts/` 아래 파일이라 패키지가 아니다 — 파일 경로로 직접 모듈을 로드한다."""
    spec = importlib.util.spec_from_file_location("run_v2_diagnostic_pilot", DRIVER_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


driver = _load_driver()


RELEASED_V2_DIAGNOSTIC: dict[str, Any] = {
    "status": "RELEASED",
    "v2_diagnostic_allowed": True,
    "real_target_allowed": True,
    "promoted_main_sha": "e45d18d0000000000000000000000000000000",
    "manifest_sha256": DIAGNOSTIC_PILOT_MANIFEST_SHA256,
}


def _doc(payload: dict[str, Any] | None, error: str | None = None) -> ReleaseDocument:
    return ReleaseDocument(
        ref="test-ref", path="test-path", data=payload, sha256="0" * 64, error=error
    )


@pytest.fixture(autouse=True)
def _clear_caches() -> Any:
    firewall.reset_release_cache()
    firewall.reset_allowlist_cache()
    yield
    firewall.reset_release_cache()
    firewall.reset_allowlist_cache()


# ══════════════════════════════════════════════════════════════════════════
# 1. 구동기가 실제로 로더를 부른다 — 12 target 통과 (`--check-only`)
# ══════════════════════════════════════════════════════════════════════════
def test_check_only_run_against_the_frozen_manifest_passes_all_twelve(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """구동기의 `main()`을 실제로 호출한다(로더 함수를 직접 부르는 게 아니다) —
    `--check-only`라 어떤 항해도 하지 않는다."""
    monkeypatch.setattr(
        firewall, "read_release_document", lambda **_kw: _doc(RELEASED_V2_DIAGNOSTIC)
    )
    exit_code = driver.main(["--check-only", "--manifest", str(MANIFEST_FIXTURE)])
    out = capsys.readouterr().out
    assert exit_code == 0, out
    assert "PLAN OK — 12 target" in out
    assert "SCOPE VERDICT" in out
    plan_order_line = next(line for line in out.splitlines() if line.startswith("PLAN ORDER:"))
    plan = json.loads(plan_order_line.removeprefix("PLAN ORDER:").strip())
    assert len(plan) == 12
    assert len({t["web_target_id"] for t in plan}) == 12


def test_check_only_reports_non_allowed_verdict_but_still_validates_plan(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """릴리스 문서가 아직 안 열려도(예: pilot 재정지) 구동기는 allowlist 검증
    자체는 계속한다 — `run_e001_real.py`와 같은 설계(plan 검증과 release 검증은
    별개 축)를 재현한다. 다만 exit code 는 0 이 아니어야 한다."""
    monkeypatch.setattr(
        firewall,
        "read_release_document",
        lambda **_kw: _doc({**RELEASED_V2_DIAGNOSTIC, "status": "SUSPENDED"}),
    )
    exit_code = driver.main(["--check-only", "--manifest", str(MANIFEST_FIXTURE)])
    out = capsys.readouterr().out
    assert "PLAN OK — 12 target" in out, "release 미허가와 무관하게 plan 검증은 됐어야 한다"
    assert exit_code == 1


# ══════════════════════════════════════════════════════════════════════════
# 2. 구동기가 실제로 로더를 부른다 — manifest 밖 target 거부
# ══════════════════════════════════════════════════════════════════════════
def test_preflight_validate_rejects_a_target_outside_the_manifest() -> None:
    """구동기가 실제로 쓰는 `_preflight_validate`(`main()`이 항해 직전 호출하는
    바로 그 함수)가, manifest 안에 없는 target 이 plan 에 섞여 있으면 거부하는지
    직접 확인한다. 정상 흐름에서는 plan 이 항상 같은 manifest 에서 만들어지므로
    (`_plan_from_rows`) 이런 target 이 자연히 섞일 수 없다 — 이 테스트는 만약
    plan 구성 로직에 버그가 생겨도 이 방어선이 살아 있는지를 본다."""
    rows = firewall.load_v2_diagnostic_targets(MANIFEST_FIXTURE)
    allowlist = firewall.load_v2_diagnostic_allowlist(MANIFEST_FIXTURE)
    plan = driver._plan_from_rows(rows)

    from landing_accessibility.e001_runner.plan import TargetSpec

    foreign = TargetSpec(
        target_id="wtg_not_in_manifest_at_all",
        canonical_service_key="wtg_not_in_manifest_at_all",
        official_url="https://evil.example.com/",
        interaction_archetype="ITEM_DETAIL",
    )
    with pytest.raises(TargetNotAllowlistedError):
        driver._preflight_validate([*plan, foreign], allowlist)

    # 대조군 — foreign 없이는 통과한다(위 거부가 "아무거나 거부하는" 구현이 아님을 보인다).
    driver._preflight_validate(plan, allowlist)


# ══════════════════════════════════════════════════════════════════════════
# 3. 구동기가 실제로 로더를 부른다 — manifest 파일 sha 변조 거부
# ══════════════════════════════════════════════════════════════════════════
def test_main_refuses_a_tampered_manifest_even_with_check_only(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """`--manifest`로 변조된 파일을 가리켜도 `main()`은 sha256 불일치로 거부한다
    (예외가 위로 전파된다 — 구동기가 조용히 삼키지 않는다). `--check-only`라도
    이 검사는 항해 여부와 무관하게 일어난다."""
    monkeypatch.setattr(
        firewall, "read_release_document", lambda **_kw: _doc(RELEASED_V2_DIAGNOSTIC)
    )
    data = json.loads(MANIFEST_FIXTURE.read_text(encoding="utf-8"))
    data["targets"][0]["web_target_id"] = "wtg_forged0000000"
    forged = tmp_path / "DIAGNOSTIC_PILOT_MANIFEST.json"
    forged.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    with pytest.raises(AllowlistUnavailableError, match="sha256"):
        driver.main(["--check-only", "--manifest", str(forged)])


def test_main_refuses_a_manifest_with_only_whitespace_changed(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(
        firewall, "read_release_document", lambda **_kw: _doc(RELEASED_V2_DIAGNOSTIC)
    )
    forged = tmp_path / "DIAGNOSTIC_PILOT_MANIFEST.json"
    forged.write_bytes(MANIFEST_FIXTURE.read_bytes() + b" ")
    with pytest.raises(AllowlistUnavailableError, match="sha256"):
        driver.main(["--check-only", "--manifest", str(forged)])


def test_main_refuses_when_manifest_file_is_absent(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(
        firewall, "read_release_document", lambda **_kw: _doc(RELEASED_V2_DIAGNOSTIC)
    )
    missing = tmp_path / "DIAGNOSTIC_PILOT_MANIFEST.json"
    with pytest.raises(AllowlistUnavailableError, match="찾지 못했다"):
        driver.main(["--check-only", "--manifest", str(missing)])


# ══════════════════════════════════════════════════════════════════════════
# 4. 구동기가 실제로 로더를 부른다 — REAL_TARGET 경로에서도 scope 가 V2_DIAGNOSTIC 로 전달된다
# ══════════════════════════════════════════════════════════════════════════
def test_non_check_only_path_calls_batch_runner_with_v2_diagnostic_scope_only(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """`--check-only`가 아닌 경로(실제 수집 경로)에서도 `BatchRunner.run`에
    넘어가는 `execution_scope`가 **항상** `V2_DIAGNOSTIC`인지 spy로 직접
    증명한다. `BatchRunner.run` 자체는 monkeypatch 로 가로채 실제로 브라우저를
    켜지 않는다 — REAL_TARGET 접속은 여기서도 0건이다."""
    monkeypatch.setattr(
        firewall, "read_release_document", lambda **_kw: _doc(RELEASED_V2_DIAGNOSTIC)
    )

    captured: dict[str, Any] = {}

    def spy_run(self, plan, *, execution_mode, execution_scope=None, target_executor=None):
        captured["execution_mode"] = execution_mode
        captured["execution_scope"] = execution_scope
        captured["plan_len"] = len(plan)
        return []

    monkeypatch.setattr(driver.BatchRunner, "run", spy_run)

    exit_code = driver.main(["--manifest", str(MANIFEST_FIXTURE), "--out", str(tmp_path / "out")])
    assert exit_code == 0
    assert captured["execution_scope"] is ExecutionScope.V2_DIAGNOSTIC
    assert captured["execution_scope"] is not ExecutionScope.E001_FULL
    assert captured["plan_len"] == 12


# ══════════════════════════════════════════════════════════════════════════
# 5. scope 하드코딩 — E001_FULL 을 여는 경로가 정말 없는가 (세 가지 독립 확인)
# ══════════════════════════════════════════════════════════════════════════
def test_source_never_references_e001_full_or_e000_fast_scope_literals() -> None:
    """정적분석 — 소스에 `ExecutionScope.E001_FULL`/`ExecutionScope.E000_FAST`
    코드 리터럴이 단 한 번도 등장하지 않는다. `V2_DIAGNOSTIC` 리터럴은 여러 번
    등장해야 한다(실제로 쓰이고 있다는 뜻)."""
    source = DRIVER_PATH.read_text(encoding="utf-8")
    assert "ExecutionScope.E001_FULL" not in source
    assert "ExecutionScope.E000_FAST" not in source
    assert source.count("ExecutionScope.V2_DIAGNOSTIC") >= 3


def test_argparse_has_no_scope_selecting_flag() -> None:
    """`--scope`류 인자가 파서에 등록돼 있지 않다 — 등록돼 있었다면
    `option_strings`에 나타난다. 존재하지 않는 인자를 실제로 넘겨서 argparse
    가 스스로 거부하는지도 함께 본다(이중 확인)."""
    import contextlib
    import io

    with pytest.raises(SystemExit) as exc_info, contextlib.redirect_stderr(io.StringIO()):
        driver.main(["--scope", "E001_FULL", "--check-only"])
    assert exc_info.value.code == 2  # argparse 의 "unrecognized arguments" 종료 코드


def test_environment_variables_cannot_change_the_scope(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """이 스크립트는 scope 선택에 어떤 환경변수도 읽지 않는다 — 그럴듯한 이름의
    환경변수를 여러 개 심어도 `BatchRunner.run`에 전달되는 scope 가
    바뀌지 않는다는 것을 spy 로 직접 증명한다."""
    monkeypatch.setattr(
        firewall, "read_release_document", lambda **_kw: _doc(RELEASED_V2_DIAGNOSTIC)
    )
    for env_name in (
        "EXECUTION_SCOPE",
        "SCOPE",
        "E001_FULL",
        "LANDING_ACCESSIBILITY_SCOPE",
        "V2_DIAGNOSTIC_SCOPE",
    ):
        monkeypatch.setenv(env_name, "E001_FULL")
    assert os.environ.get("EXECUTION_SCOPE") == "E001_FULL"  # 실제로 심어졌다는 것을 확인

    captured: dict[str, Any] = {}

    def spy_run(self, plan, *, execution_mode, execution_scope=None, target_executor=None):
        captured["execution_scope"] = execution_scope
        return []

    monkeypatch.setattr(driver.BatchRunner, "run", spy_run)
    exit_code = driver.main(["--manifest", str(MANIFEST_FIXTURE), "--out", str(tmp_path / "out")])
    assert exit_code == 0
    assert captured["execution_scope"] is ExecutionScope.V2_DIAGNOSTIC


def test_no_worker_flag_exists_the_driver_always_runs_all_twelve() -> None:
    """`run_e001_real.py`의 `--worker` 분할과 달리, 이 구동기는 12건뿐이라 분할이
    없다 — `--worker` 인자를 주면 argparse 가 거부해야 한다(그런 인자가 아예
    없다는 것을 증명한다)."""
    import contextlib
    import io

    with pytest.raises(SystemExit) as exc_info, contextlib.redirect_stderr(io.StringIO()):
        driver.main(["--worker", "01", "--check-only"])
    assert exc_info.value.code == 2


# ══════════════════════════════════════════════════════════════════════════
# 6. release document binding — 구동기가 실제로 V2_DIAGNOSTIC_RELEASE.json 경로를 탄다
# ══════════════════════════════════════════════════════════════════════════
def test_main_reads_the_v2_diagnostic_release_document_not_e001_or_e000(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """`T-A-V3-P0-B-001` 요구 2 — manifest hash 뿐 아니라 릴리스 문서도 실제로
    읽는지 확인한다. `_evaluate_release_document`의 `expected_manifest_sha256`
    분기(D-R0-82 §4 요구 5)는 이미 로더 층 테스트가 고정했다 — 여기서는
    **구동기가 그 경로를 실제로 호출**하는지만 spy 로 증명한다."""
    seen_paths: list[str] = []

    def spy(**kw):
        seen_paths.append(str(kw.get("path")))
        return _doc(RELEASED_V2_DIAGNOSTIC)

    monkeypatch.setattr(firewall, "read_release_document", spy)
    exit_code = driver.main(["--check-only", "--manifest", str(MANIFEST_FIXTURE)])
    assert exit_code == 0
    # `main()`이 `evaluate_execution_scope`(SCOPE VERDICT 출력용)와
    # `firewall_state`(FIREWALL 출력용, 내부에서 다시 `evaluate_execution_scope`
    # 를 부른다) 양쪽에서 읽어 총 2회 호출된다 — 둘 다 같은 경로여야 한다.
    assert seen_paths, "read_release_document 가 한 번도 호출되지 않았다"
    assert set(seen_paths) == {firewall.V2_DIAGNOSTIC_RELEASE_PATH}
    assert firewall.E001_RELEASE_PATH not in seen_paths
    assert firewall.P0_RELEASE_PATH not in seen_paths


def test_main_is_blocked_when_release_document_lacks_manifest_binding(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """릴리스 문서가 있어도 `manifest_sha256`이 없거나 다르면(요구 5, scope↔표본
    바인딩) `--check-only`의 exit code 가 0 이 아니다 — 구동기가 이 판정을
    실제로 반영한다는 것을 증명한다."""
    monkeypatch.setattr(
        firewall,
        "read_release_document",
        lambda **_kw: _doc({**RELEASED_V2_DIAGNOSTIC, "manifest_sha256": "0" * 64}),
    )
    exit_code = driver.main(["--check-only", "--manifest", str(MANIFEST_FIXTURE)])
    assert exit_code == 1  # PLAN 자체는 유효하지만(allowlist 검증은 독립 축) verdict.allowed=False


# ══════════════════════════════════════════════════════════════════════════
# 7. `layer_firewall.py` — V2_DIAGNOSTIC 가 아직 그 층에 없다 (구현 중 발견)
# ══════════════════════════════════════════════════════════════════════════
#
# `T-A-V3-P0-B-001` 요구 3·4(dup 억제·launch 전 fail-closed)를 구현하다가 발견한
# 사실: `batch.py.run()`은 `assert_batch_execution_mode_safe`(독립 2층,
# `layer_firewall.py`, **W1 소유 아님·읽기전용**)를 `assert_mode_allowed`(엔진
# 1층, `firewall.py`, 내 소유)보다 **먼저** 부른다. 그런데 `layer_firewall.
# BATCH_LAYER_REAL_SCOPES`는 `{"E000_FAST", "E001_FULL"}`만 알고 `V2_DIAGNOSTIC`
# 을 모른다 — `assert_batch_execution_mode_safe("REAL_TARGET", "V2_DIAGNOSTIC")`
# 는 **릴리스 문서 상태와 무관하게 항상** `BatchRealTargetBlockedError`를 낸다
# (아래 `test_layer_firewall_currently_blocks_v2_diagnostic_unconditionally`가
# 이 사실 자체를 고정한다 — 이 테스트가 언젠가 실패하면 그건 `layer_firewall.py`
# 가 갱신됐다는 신호다).
#
# 이건 **버그가 아니라 지금 phase 의 의도와 일치하는 우연한 추가 방어**다 —
# "P0 가 닫히기 전 REAL 은 어떤 경우에도 금지"(`T-A-V3-P0-B-001`)를 이 층이
# 이미 무조건 만족시키고 있다. 다만 이 상태로는 **exactly-once 락 로직**
# (`_run_real`/`_real_executor`)에 REAL_TARGET 경로로 아예 도달할 수 없다 —
# 그래서 아래 dup-억제 테스트(§8)는 `layer_firewall`을 test-only로 bypass 해
# 그 뒷단만 분리해서 증명한다.
#
# `T-A-V3-STEP1-FREEZE` C_BLK_009_ruling 으로 **이 상태의 의미가 바뀌었다.**
# 작성 당시에는 '아직 배선되지 않은 gap' 이었고 W1 이 소유 밖이라 고치지 않았다.
# 지금은 A 가 `layer_firewall.py` 를 B 본체 소유로 지정하고 `V2_DIAGNOSTIC` 을
# **추가하지 않기로 결정**했다 — DIAG-PILOT-001 12건이 `HISTORICAL_METHOD_ASSURANCE`
# 로 동결돼 실행되지 않으므로 launch 경로가 불필요하다. 관측되는 사실은 같고
# 의미가 다르다: 미구현이 아니라 **의도된 종결 상태**다.
def test_layer_firewall_currently_blocks_v2_diagnostic_unconditionally() -> None:
    """`layer_firewall.py` 2층이 `V2_DIAGNOSTIC` 을 모른다 — 이것은 **의도된 종결
    상태**이며 미구현 gap 이 아니다 (`T-A-V3-STEP1-FREEZE` C_BLK_009_ruling ②).

    릴리스 문서를 아무리 잘 갖춰도 이 층에서 막힌다. 12건 실행이 취소됐으므로
    그 launch 경로는 필요하지 않고, 2층은 이 scope 를 모르는 채로 둔다.

    **이 테스트가 실패하면 누군가 `V2_DIAGNOSTIC` 을 2층에 추가한 것이다.** 그건
    A 의 결정을 뒤집는 변경이므로 그 자체가 검토 대상이다 — 테스트를 고치지 말고
    왜 추가됐는지 먼저 물어라. V3 scope(`V3_PILOT_5`/`V3_MAIN50`)를 2층에 추가하는
    것은 별개이며, 그때는 릴리스 문서뿐 아니라 `manifest_sha256` 을 파일 바이트에서
    **1층 결과 재사용 없이 독립 재확인**해야 한다 (같은 ruling ③) — 그러지 않으면
    2층이 1층보다 약해져 독립 방어의 의미가 사라진다."""
    from landing_accessibility.e001_runner import layer_firewall
    from landing_accessibility.e001_runner.layer_firewall import BatchRealTargetBlockedError

    assert "V2_DIAGNOSTIC" not in layer_firewall.BATCH_LAYER_REAL_SCOPES
    with pytest.raises(BatchRealTargetBlockedError, match="V2_DIAGNOSTIC"):
        layer_firewall.assert_batch_execution_mode_safe("REAL_TARGET", "V2_DIAGNOSTIC")


def test_driver_is_currently_blocked_end_to_end_by_the_batch_layer_gap(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """위 종결 상태가 구동기의 실제 REAL_TARGET 경로에도 그대로 적용된다는 것을
    end-to-end 로 확인한다 — 릴리스 문서를 완벽히 RELEASED 로 갖춰도(엔진 1층은
    통과) 2층(`layer_firewall`)에서 막힌다.

    `run_l1_if_safe_real` 에 spy 를 심어 launch 카운트가 0 인지도 함께 본다 —
    브라우저 기동 **시도 자체가 없었다**는 직접 증거다. 차단됐다는 예외만으로는
    '막혔지만 이미 열긴 열었다' 와 구분되지 않는다."""
    monkeypatch.setattr(
        firewall, "read_release_document", lambda **_kw: _doc(RELEASED_V2_DIAGNOSTIC)
    )
    launch_calls: list[str] = []

    def spy(target, *, run, scope, task=None, budget=None):
        launch_calls.append(target.target_id)
        return {
            "outcome": "MEASURED",
            "scout_invoked": True,
            "measurement_status": "MEASURED",
            "l0": {},
        }

    monkeypatch.setattr(real_executor_module, "run_l1_if_safe_real", spy)

    from landing_accessibility.e001_runner.layer_firewall import BatchRealTargetBlockedError

    with pytest.raises(BatchRealTargetBlockedError):
        driver.main(
            [
                "--manifest",
                str(MANIFEST_FIXTURE),
                "--out",
                str(tmp_path / "out"),
                "--ticket-id",
                "T-TEST-DIAG-LAYER-GAP",
                "--run-id",
                "ROUND-1",
                "--lock-dir",
                str(tmp_path / "locks"),
            ]
        )
    assert launch_calls == [], f"batch layer 가 막았어야 하는데 launch 가 일어났다: {launch_calls}"


# ══════════════════════════════════════════════════════════════════════════
# 8. duplicate/idempotency 억제가 launch 이전에 실제로 소비된다 (구동기 경로,
#    `layer_firewall` gap 을 test-only 로 bypass — §7 참고)
# ══════════════════════════════════════════════════════════════════════════
def _fake_run_l1_if_safe_real(target, *, run, scope, task=None, budget=None):
    """`real_executor.run_l1_if_safe_real`(playwright 기동으로 이어지는 진입점)을
    통째로 대체하는 spy 다 — `tests/test_w1_exactly_once.py`와 같은 기법.
    **실사이트에 붙지 않는다.** `EvidenceRun.seal()`이 요구하는 최소 산출물만
    남긴다."""
    run.open_observation("fake-obs")
    run.write_artifact("fake-obs", "fake/marker.txt", b"1")
    return {
        "outcome": "MEASURED",
        "scout_invoked": True,
        "measurement_status": "MEASURED",
        "l0": {},
    }


@pytest.fixture()
def _bypass_batch_layer_gap(monkeypatch: pytest.MonkeyPatch):
    """`layer_firewall.py`(§7)가 아직 `V2_DIAGNOSTIC`을 모른다 — 그 파일은 내
    소유가 아니라 여기서 고치지 않는다. 이 fixture 는 **이 테스트 프로세스
    안에서만** `assert_batch_execution_mode_safe`를 통과시켜, 뒷단(exactly-once
    락, 내 책임)을 그 gap 과 분리해서 검증한다."""
    monkeypatch.setattr(
        "landing_accessibility.e001_runner.batch.assert_batch_execution_mode_safe",
        lambda mode, scope=None: getattr(mode, "value", None) or str(mode),
    )
    yield


@pytest.fixture()
def _default_manifest_candidates_point_to_fixture(monkeypatch: pytest.MonkeyPatch):
    """`batch.py._run_real`은 **자기 힘으로** 또 한 번(내 driver 의
    `_preflight_validate`와 별개로) `validate_real_target_scope_allowlist(plan,
    scope=scope)`를 부른다(defense-in-depth, `plan.py`, 내 소유) — 이때는
    `path=` 를 넘기지 않으므로 기본 후보 경로(`DIAGNOSTIC_PILOT_MANIFEST_
    CANDIDATES`)로 떨어진다. 이 브랜치 tree 에는 아직 manifest 실물이 없다
    (`T-B-BLK-007` 참고 — merge 대기 중, rebase 하지 않기로 함) — 그래서 이
    fixture 로 기본 후보를 fixture 사본으로 돌린다. **운영 코드를 바꾸는 게
    아니라 이 테스트 프로세스 안에서만** 후보 경로를 대체한다."""
    monkeypatch.setattr(firewall, "DIAGNOSTIC_PILOT_MANIFEST_CANDIDATES", (MANIFEST_FIXTURE,))
    firewall.reset_allowlist_cache()
    yield
    firewall.reset_allowlist_cache()


def test_driver_second_invocation_with_same_ticket_run_launches_zero_times(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    _bypass_batch_layer_gap: None,
    _default_manifest_candidates_point_to_fixture: None,
) -> None:
    """`T-A-V3-P0-B-001` 요구 3 — "락 디렉터리 존재만으로 PASS 하지 마라." 이
    테스트는 디렉터리 존재가 아니라 **launch 카운트**를 직접 센다(`tests/
    test_w1_exactly_once.py`의 `test_real_executor_second_sequential_call_
    launches_zero_times`와 같은 계측 기법, 구동기의 `main()`을 통해서 재현).

    1회차: `driver.main([...])` 호출 → launch 카운트 12(target 전건).
    2회차: **같은 ticket_id/run_id/lock_dir/manifest**로 `driver.main([...])`를
    다시 호출 → launch 카운트가 여전히 12(추가 0) — lock 을 지우는 코드 경로가
    없으므로 같은 프로세스 안에서도 2회차는 억제돼야 한다.
    """
    monkeypatch.setattr(
        firewall, "read_release_document", lambda **_kw: _doc(RELEASED_V2_DIAGNOSTIC)
    )
    launch_calls: list[str] = []

    def spy(target, *, run, scope, task=None, budget=None):
        launch_calls.append(target.target_id)
        return _fake_run_l1_if_safe_real(target, run=run, scope=scope, task=task, budget=budget)

    monkeypatch.setattr(real_executor_module, "run_l1_if_safe_real", spy)

    common_argv = [
        "--manifest",
        str(MANIFEST_FIXTURE),
        "--out",
        str(tmp_path / "out"),
        "--ticket-id",
        "T-TEST-DIAG",
        "--run-id",
        "ROUND-1",
        "--lock-dir",
        str(tmp_path / "locks"),
    ]

    first_exit = driver.main(list(common_argv))
    assert first_exit == 0
    assert len(launch_calls) == 12, (
        f"1회차에 12 target 전부 launch 돼야 하는데 {len(launch_calls)}: {launch_calls}"
    )
    assert len(set(launch_calls)) == 12

    second_exit = driver.main(list(common_argv))
    assert second_exit == 0
    assert len(launch_calls) == 12, (
        f"2회차(같은 ticket/run) 이후에도 launch 카운트는 12여야 하는데 "
        f"{len(launch_calls)} — 2회차에서 브라우저가 다시 기동됐다: {launch_calls}"
    )

    event_log = (tmp_path / "locks").parent / "event_log.jsonl"
    assert event_log.is_file(), "DUPLICATE_SUPPRESSED 이벤트가 event_log 에 기록되지 않았다"
    events = [json.loads(line) for line in event_log.read_text(encoding="utf-8").splitlines()]
    duplicate_events = [e for e in events if e.get("event") == DUPLICATE_SUPPRESSED_OUTCOME]
    # 12건이 아니라 1건이다 — `BatchRunner.abandon_partition_on_suppression`
    # (기본 True, `C-BLOCKER-220418` 시정, T-A-W1-001) 이 첫 억제를 만나는 즉시
    # 그 파티션의 나머지 target 을 전부 포기한다. 그래서 2회차의 첫 target
    # (plan 순서상 `wtg_699a5e2f3f410152`) 하나만 DUPLICATE_SUPPRESSED 로 실제
    # 기록되고, 나머지 11개는 시도 자체가 없어 launch 도 0·이벤트도 0이다 —
    # "launch 카운트가 늘지 않는다"는 핵심 속성은 이미 위에서 확인했다(12→12).
    assert len(duplicate_events) == 1, (
        f"partition-abandon-on-suppression 정책상 2회차는 첫 target 1건만 "
        f"DUPLICATE_SUPPRESSED 로 기록돼야 하는데 {len(duplicate_events)}건: {duplicate_events}"
    )
    expected_first_id = firewall.load_v2_diagnostic_targets(MANIFEST_FIXTURE)[0].web_target_id
    assert duplicate_events[0]["target_id"] == expected_first_id


# ══════════════════════════════════════════════════════════════════════════
# 9. browser launch 전 fail-closed — 엔진 층 단독으로도 launch 카운트가 0 이다 (음성 대조)
# ══════════════════════════════════════════════════════════════════════════
def test_driver_launches_nothing_when_release_verdict_is_not_allowed(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, _bypass_batch_layer_gap: None
) -> None:
    """`T-A-V3-P0-B-001` 요구 4 — 게이트 실패 시 브라우저가 아예 뜨지 않아야
    한다. `layer_firewall` gap(§7)을 bypass 해 **엔진 층(내 책임)만** 단독으로
    시험한다 — 릴리스 문서를 SUSPENDED 로 만든 채 `--check-only` **없이**
    `driver.main([...])`을 호출한다. `ExecutionScopeBlockedError`가
    `_real_executor` 진입(=락 획득·launch 시도) **전에** 올라와야 하고, launch
    카운트는 0 이어야 한다.
    """
    monkeypatch.setattr(
        firewall,
        "read_release_document",
        lambda **_kw: _doc({**RELEASED_V2_DIAGNOSTIC, "status": "SUSPENDED"}),
    )
    launch_calls: list[str] = []

    def spy(target, *, run, scope, task=None, budget=None):
        launch_calls.append(target.target_id)
        return _fake_run_l1_if_safe_real(target, run=run, scope=scope, task=task, budget=budget)

    monkeypatch.setattr(real_executor_module, "run_l1_if_safe_real", spy)

    with pytest.raises(ExecutionScopeBlockedError):
        driver.main(
            [
                "--manifest",
                str(MANIFEST_FIXTURE),
                "--out",
                str(tmp_path / "out"),
                "--ticket-id",
                "T-TEST-DIAG-BLOCKED",
                "--run-id",
                "ROUND-1",
                "--lock-dir",
                str(tmp_path / "locks"),
            ]
        )
    assert launch_calls == [], f"게이트가 닫혔는데도 launch 가 일어났다: {launch_calls}"
    assert not (tmp_path / "locks").exists() or not any((tmp_path / "locks").iterdir()), (
        "게이트가 닫혔는데도 lock 파일이 생성됐다 — launch 시도 흔적이다"
    )
