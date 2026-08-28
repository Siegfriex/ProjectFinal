"""W5R — `R43` 검증 함수 실패 실증기 (`Δ48`).

`R43` (`Δ48`)
    `verify_*` · `assert_*` · `check_*` 계열 **전수**에 대해 각각 **실패하는 입력이
    존재함을 실증한다.** 실증할 수 없으면 그 함수는 이름이 약속을 하고 이행하지
    않는 것이므로 시정하거나 제거한다. **`GATE 1` 조건이다.**

열거 범위 — "전수" 가 무엇의 전수인가
    `src/landing_accessibility/v3_runner/**/*.py` 안의 **모든** `def`/`async def` 중,
    이름에서 선행 `_` 를 뗀 뒤 `verify_` · `assert_` · `check_` 로 시작하거나 정확히
    `check`/`verify`/`assert` 인 것. 중첩(메서드·내부함수) 포함. AST 로 연다 —
    정규식은 데코레이터·줄바꿈 시그니처에서 새고, 이 목록은 새면 안 된다.

    접미사 없는 `verify`/`assert` 를 넣은 이유: `engine/evidence.py::EvidenceRun.verify`
    가 실제로 그 형태다. `v3_runner` 안에는 해당 사례가 없어 건수는 변하지 않지만,
    **규칙이 그 형태를 놓치지 않는다는 것 자체가 이 열거의 주장**이다.

    이 lane 자신의 도구(`v3_runner/r43/**`)는 대상에서 뺀다 — 도구가 자기를 세면
    목록이 자기지시가 된다.

    `src/landing_accessibility/engine/**` 은 **0건이 아니라 미실증**이다. 열거만 하고
    (`ENGINE_ENUMERATED`) 실증은 하지 않았다. 다른 평면 소관이며 이 lane 은 손대지
    않는다 (`Δ48` — "'전수' 라고 쓰지 않았다").

무엇이 "실패" 인가 — 함수마다 다르다
    이 계열은 실패를 세 가지 형태로 낸다. **각 함수가 선언한 형태로만** 실증한다.

    ``RAISE:<Exc>``   선언된 예외를 던진다
    ``DICT_OK_FALSE`` ``{"ok": False}`` 를 돌려준다
    ``NONEMPTY_LIST`` 비어 있지 않은 실패 목록을 돌려준다
    ``NEVER``         실패를 표현할 수단이 본문에 없다 (Protocol stub · 기록용 fake)

    **크래시는 실패가 아니다.** 선언된 예외가 아닌 `TypeError`/`AttributeError` 는
    ``CRASH`` 로 따로 적는다. `R36` — A 가 크래시를 `positive_control_fail` 이라
    부른 것이 이 구분을 만든 사건이다. 크래시만 나는 함수는 **`CANNOT_FAIL`** 이다.

두 번째 축 — `VACUOUS_PASS`
    `Δ48` 이 실제로 본 결함은 "실패 입력이 없다" 가 아니라 **"아무것도 검사하지
    않고 성공을 낸다"** 였다. 이 둘은 다르다. 그래서 판정을 두 축으로 낸다:
    ``can_fail`` 과 ``vacuous_pass``. 한 축만 재면 `verify_retention_manifest` 를
    놓치거나(축1) 잡되 이유를 틀리게 적는다(축2).

`exit` 규약 (`Δ46`)
    ``0`` 통과 · ``1`` 검사가 돌았고 실패했다 · ``2`` **검사가 돌지 않았다**

실행::

    python -m landing_accessibility.v3_runner.r43.check
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import sys
import tempfile
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

__all__ = [
    "CONTROLS",
    "DECLARED_FAILURE_BEHAVIOUR",
    "PROBES",
    "Probe",
    "build_result",
    "check",
    "enumerate_family",
    "main",
    "tool_sha256",
]

_HERE = Path(__file__).resolve()
_R43_DIR = _HERE.parent
_V3_RUNNER = _R43_DIR.parent
_PKG = _V3_RUNNER.parent
_RESEARCH_ROOT = _PKG.parent.parent

_FAMILY_PREFIXES = ("verify_", "assert_", "check_")
_FAMILY_EXACT = ("check", "verify", "assert")


# ══════════════════════════════════════════════════════════════════════════
# 층 0 — 열거 (AST)
# ══════════════════════════════════════════════════════════════════════════


def _is_family(name: str) -> bool:
    bare = name.lstrip("_")
    return bare.startswith(_FAMILY_PREFIXES) or bare in _FAMILY_EXACT


def _body_is_ellipsis_only(node: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    """docstring 을 뺀 본문이 `...` 하나뿐인가 — Protocol 선언의 형태다."""
    body = list(node.body)
    if (
        body
        and isinstance(body[0], ast.Expr)
        and isinstance(body[0].value, ast.Constant)
        and isinstance(body[0].value.value, str)
    ):
        body = body[1:]
    return len(body) == 1 and (
        isinstance(body[0], ast.Expr)
        and isinstance(body[0].value, ast.Constant)
        and body[0].value.value is Ellipsis
    )


def enumerate_family(root: Path) -> list[dict[str, Any]]:
    """`root` 아래 모든 `.py` 에서 계열 함수를 AST 로 전수 열거한다."""
    rows: list[dict[str, Any]] = []
    for path in sorted(Path(root).rglob("*.py")):
        if _R43_DIR in path.parents or path == _HERE:
            # 이 lane 의 도구는 대상이 아니다 — 도구가 자기를 세면 목록이 자기지시가 된다.
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        stack: list[tuple[ast.AST, list[str]]] = [(tree, [])]
        while stack:
            node, ctx = stack.pop()
            for child in ast.iter_child_nodes(node):
                nctx = ctx
                if isinstance(child, ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef):
                    nctx = [*ctx, child.name]
                if isinstance(child, ast.FunctionDef | ast.AsyncFunctionDef) and _is_family(
                    child.name
                ):
                    rows.append(
                        {
                            "point_id": f"{path.name}::{'.'.join(nctx)}",
                            "file": path.name,
                            "qualname": ".".join(nctx),
                            "lineno": child.lineno,
                            "ellipsis_body": _body_is_ellipsis_only(child),
                        }
                    )
                stack.append((child, nctx))
    rows.sort(key=lambda r: (r["file"], r["lineno"]))
    return rows


def v3_runner_root() -> Path:
    return _V3_RUNNER


def engine_root() -> Path:
    return _PKG / "engine"


# ══════════════════════════════════════════════════════════════════════════
# 층 1 — 실증
# ══════════════════════════════════════════════════════════════════════════

PASS = "PASS"
DECLARED_FAIL = "DECLARED_FAIL"
CRASH = "CRASH"
MALFORMED = "MALFORMED_RETURN"

CAN_FAIL = "CAN_FAIL"
CANNOT_FAIL = "CANNOT_FAIL"


@dataclass(frozen=True)
class Probe:
    """계열 함수 하나에 대한 실증 묶음."""

    point_id: str
    #: 선언한 실패 형태. `RAISE:<Exc>` / `DICT_OK_FALSE` / `NONEMPTY_LIST` / `NEVER`
    declared_failure: str
    #: VERIFIER · PROTOCOL_DECLARATION · TEST_DOUBLE · ACTUATION_NAME_COLLISION · SYNTHETIC
    kind: str
    #: 통과해야 하는 입력. 이것이 통과하지 않으면 "무엇을 넣어도 실패" 라서 실증이 공허하다.
    baseline: Callable[[], Any]
    #: 실패시키려는 입력들. 이름은 **무엇을 넣었는가**를 적는다 (`R36`).
    failing: tuple[tuple[str, Callable[[], Any]], ...] = ()
    #: 검사를 0회 하고 성공을 내는 입력 (있으면). 축2 `VACUOUS_PASS` 의 근거.
    vacuous: tuple[str, Callable[[], Any]] | None = None
    note: str = ""
    #: 판정을 사람이 다시 읽을 수 있게 하는 소스 근거 (선택)
    evidence: str = ""


def _classify(declared: str, ran: Callable[[], Any]) -> dict[str, Any]:
    """한 입력의 결과를 선언된 실패 형태에 비추어 분류한다."""
    try:
        value = ran()
    except BaseException as exc:
        name = type(exc).__name__
        if declared.startswith("RAISE:") and name in {
            n.strip() for n in declared[len("RAISE:") :].split("|")
        }:
            return {"outcome": DECLARED_FAIL, "detail": f"{name}: {str(exc)[:160]}"}
        return {"outcome": CRASH, "detail": f"{name}: {str(exc)[:160]}"}
    if declared.startswith("RAISE:"):
        return {"outcome": PASS, "detail": f"반환 {type(value).__name__} — 예외 없음"}
    if declared == "DICT_OK_FALSE":
        if isinstance(value, dict) and value.get("ok") is False:
            return {"outcome": DECLARED_FAIL, "detail": _brief(value)}
        if isinstance(value, dict) and value.get("ok") is True:
            return {"outcome": PASS, "detail": _brief(value)}
        return {"outcome": MALFORMED, "detail": _brief(value)}
    if declared == "NONEMPTY_LIST":
        if isinstance(value, list) and value:
            return {"outcome": DECLARED_FAIL, "detail": f"{len(value)}건: {value[0][:120]}"}
        if isinstance(value, list):
            return {"outcome": PASS, "detail": "빈 목록"}
        return {"outcome": MALFORMED, "detail": _brief(value)}
    # NEVER — 실패를 표현할 수단이 없다고 선언한 함수
    return {"outcome": PASS, "detail": f"반환 {value!r}"[:160]}


def _brief(value: Any) -> str:
    try:
        return json.dumps(value, ensure_ascii=False, default=str)[:200]
    except (TypeError, ValueError):
        return repr(value)[:200]


def _is_vacuous_success(value: Any) -> bool:
    """'성공' 인데 **검사한 흔적이 0** 인가.

    dict 형태 검증기의 증거 목록이 전부 비었는데 `ok: True` 면, 그 True 는
    "대조했고 맞았다" 가 아니라 "대조할 것이 없었다" 다. 두 문장은 다른 사실이고
    같은 출력으로 나오면 안 된다 (`Δ39-R32` 와 같은 형태).
    """
    if not isinstance(value, dict) or value.get("ok") is not True:
        return False
    lists = [v for v in value.values() if isinstance(v, list)]
    return bool(lists) and all(not v for v in lists)


def run_probe(probe: Probe) -> dict[str, Any]:
    baseline = _classify(probe.declared_failure, probe.baseline)
    cases = [{"input": name, **_classify(probe.declared_failure, fn)} for name, fn in probe.failing]
    demonstrated = [c for c in cases if c["outcome"] == DECLARED_FAIL]
    crashed = [c for c in cases if c["outcome"] == CRASH]
    verdict = CAN_FAIL if demonstrated else CANNOT_FAIL

    vac: dict[str, Any] | None = None
    if probe.vacuous is not None:
        vname, vfn = probe.vacuous
        try:
            vvalue = vfn()
        except BaseException as exc:
            vac = {"input": vname, "vacuous_pass": False, "detail": f"{type(exc).__name__}"}
        else:
            vac = {
                "input": vname,
                "vacuous_pass": _is_vacuous_success(vvalue),
                "detail": _brief(vvalue),
            }
    return {
        "point_id": probe.point_id,
        "kind": probe.kind,
        "declared_failure": probe.declared_failure,
        "verdict": verdict,
        "baseline_passes": baseline["outcome"] == PASS,
        "baseline_detail": baseline["detail"],
        "demonstrated_failure_inputs": [c["input"] for c in demonstrated],
        "crash_only_inputs": [c["input"] for c in crashed],
        "cases": cases,
        "vacuous": vac,
        "vacuous_pass": bool(vac and vac["vacuous_pass"]),
        "note": probe.note,
        "evidence": probe.evidence,
    }


# ══════════════════════════════════════════════════════════════════════════
# 층 2 — 대조 (`Δ40` 명칭: must_flag / must_not_flag)
# ══════════════════════════════════════════════════════════════════════════
#
# `must_flag`      = 이 도구가 **결함으로 잡아야 하는** 것 (기대 판정 `CANNOT_FAIL`)
# `must_not_flag`  = 이 도구가 **잡으면 안 되는** 것 (기대 판정 `CAN_FAIL`)
#
# 합성(SYNTHETIC) 대조를 함께 두는 이유: 저장소 안의 함수를 대조로 쓰면, 그 함수가
# 고쳐지는 순간 대조가 조용히 사라진다. 합성 대조는 저장소 상태와 무관하게 **방법
# 자체**를 잰다.

CONTROLS: dict[str, tuple[str, str]] = {
    # role -> (point_id, expected verdict)
    "must_flag__synthetic_always_ok": ("SYNTHETIC::verify_always_ok", CANNOT_FAIL),
    "must_flag__synthetic_crash_only": ("SYNTHETIC::verify_crash_only", CANNOT_FAIL),
    "must_flag__protocol_stub": ("runner.py::EligibilityChecker.check", CANNOT_FAIL),
    "must_not_flag__synthetic_raiser": ("SYNTHETIC::assert_positive", CAN_FAIL),
    "must_not_flag__repo_raiser": ("evidence.py::assert_layer_qualified", CAN_FAIL),
}

#: `B` 가 지정한 must_flag. **관측이 지정과 다르다** — 별도로 기록하고 게이트에 걸지
#: 않는다. 근거는 `docs/v3/R43_VERIFIER_FAILURE_DEMO.md` 의 「지정 대조의 반증」.
BRIEFED_CONTROL = ("evidence.py::verify_retention_manifest", CANNOT_FAIL)


# ══════════════════════════════════════════════════════════════════════════
# 합성 대조 대상
# ══════════════════════════════════════════════════════════════════════════


def _synthetic_verify_always_ok(payload: Any) -> dict[str, Any]:
    """`Δ48` 의 발단이 된 형태 — 아무것도 보지 않고 `ok: True`."""
    return {"ok": True, "checked": []}


def _synthetic_verify_crash_only(payload: Any) -> dict[str, Any]:
    """선언은 `DICT_OK_FALSE` 인데 나쁜 입력에는 `TypeError` 로 죽는다.

    **크래시를 실패로 세면 이 함수가 `CAN_FAIL` 로 나온다.** 그게 `R36` 이 막는 오독이다.
    """
    return {"ok": payload["ok"], "checked": [payload]}


def _synthetic_assert_positive(n: Any) -> None:
    if not isinstance(n, int) or n <= 0:
        raise ValueError(f"양수가 아니다: {n!r}")


# ══════════════════════════════════════════════════════════════════════════
# 층 3 — 실제 probe 목록
# ══════════════════════════════════════════════════════════════════════════


def _build_probes() -> tuple[Probe, ...]:
    from landing_accessibility.v3_runner import evidence, r32_check, runner, safety
    from landing_accessibility.v3_runner.contracts import TaskContract

    tmp = Path(tempfile.mkdtemp(prefix="w5r-r43-"))

    # ── 공용 fixture ──────────────────────────────────────────────────────
    real = tmp / "real"
    real.mkdir()
    (real / "a.txt").write_bytes(b"hello")
    good_files = [
        {
            "path": "real/a.txt",
            "sha256": evidence.sha256_of_file(real / "a.txt"),
            "bytes": 5,
        }
    ]

    def _retention(files: list[dict[str, Any]], *, aggregate: str | None = None) -> dict[str, Any]:
        agg = aggregate if aggregate is not None else evidence._aggregate_sha256(files)
        return {"roots": [{"root": "real", "files": files, "aggregate_sha256": agg}]}

    # evidence run — seal 까지 간 진짜 run 하나
    run_root = tmp / "runs"
    key = evidence.ObservationKey(service_id="svc", task_id="task", run_id="r1")
    writer = evidence.EvidenceRunWriter(run_root, key).open()
    writer.write_text_slot("n1", evidence.EvidenceSlot.DOM, "<html></html>")
    path_manifest = {"steps": []}
    pm_bytes = evidence.canonical_json_bytes(path_manifest)
    writer.seal(path_manifest_sha256=evidence.sha256_of_bytes(pm_bytes))
    run_dir = writer.run_dir

    tampered_root = tmp / "runs_tampered"
    import shutil as _shutil

    _shutil.copytree(run_root, tampered_root)
    tampered_dir = tampered_root / key.observation_id()
    (tampered_dir / "n1" / "dom.html").write_text("<html>TAMPERED</html>", encoding="utf-8")

    unopened_writer = evidence.EvidenceRunWriter(tmp / "never_opened", key)

    # slot 을 하나도 쓰지 않고 봉인한 run — 대조할 것이 0개인 상태.
    empty_key = evidence.ObservationKey(service_id="svc", task_id="task", run_id="empty")
    empty_writer = evidence.EvidenceRunWriter(run_root, empty_key).open()
    empty_writer.seal(path_manifest_sha256=evidence.sha256_of_bytes(b"{}"))
    empty_run_dir = empty_writer.run_dir

    ledger = evidence.ReplacementLedger(family_id="F1", frozen_at="2026-01-01")
    good_chain = {"family_id": "F1", "replacement_ledger_sha256": ledger.sha256()}

    def contract(**over: Any) -> TaskContract:
        base = {
            "target_id": "T1",
            "family_id": "F1",
            "service": "S",
            "starting_url": "https://example.invalid/",
            "frozen_task": "task",
            "task_instruction": "i",
            "fixed_fixture": "FIX",
            "fixture_override": None,
            "endpoint_contract": "EC",
            "forbidden_actions": ("PAYMENT_EXECUTION",),
            "task_contract_hash": "T" * 64,
            "endpoint_contract_hash": "E" * 64,
        }
        base.update(over)
        return TaskContract(**base)  # type: ignore[arg-type]

    class _Hasher:
        def task_contract_hash(self, c: TaskContract) -> str | None:
            return c.task_contract_hash

        def endpoint_contract_hash(self, c: TaskContract) -> str | None:
            return c.endpoint_contract_hash

    class _NullGuard:
        def assert_action_allowed(self, c: Any, a: Any) -> None:
            return None

    rnr = runner.V3Runner(
        evidence_root=tmp / "ev",
        contract_hasher=_Hasher(),
        safety=_NullGuard(),
    )
    ok_action = runner.PlannedAction(action_token="OPEN_GLOBAL_MENU", control_selector="#go")

    guard = safety.ActivationSafetyGuard(contract())

    class _Page:
        def __init__(self) -> None:
            self.calls: list[tuple[str, str, Any]] = []

        def click(self, selector: str, *a: Any, **k: Any) -> str:
            self.calls.append(("click", selector, None))
            return "clicked"

        def check(self, selector: str, *a: Any, **k: Any) -> str:
            self.calls.append(("check", selector, None))
            return "checked"

        def fill(self, selector: str, value: str, *a: Any, **k: Any) -> str:
            self.calls.append(("fill", selector, value))
            return "filled"

    gpage = safety.GuardedPage(_Page(), guard)
    rpage = safety.RecordingPage() if hasattr(safety, "RecordingPage") else None

    # r32_check 문서 — 정본 사본과, 행을 지운 사본
    r32_doc = r32_check.document_path()
    broken_doc = tmp / "r32_broken.md"
    if r32_doc.is_file():
        lines = r32_doc.read_text(encoding="utf-8").splitlines(keepends=True)
        target = "| `session.py::is_credential_field::password_scope` |"
        broken_doc.write_text(
            "".join(ln for ln in lines if not ln.startswith(target)), encoding="utf-8"
        )

    probes: list[Probe] = [
        # ── 합성 대조 ────────────────────────────────────────────────────
        Probe(
            "SYNTHETIC::verify_always_ok",
            "DICT_OK_FALSE",
            "SYNTHETIC",
            lambda: _synthetic_verify_always_ok({"ok": True}),
            (
                ("payload={'ok': False}", lambda: _synthetic_verify_always_ok({"ok": False})),
                ("payload=None", lambda: _synthetic_verify_always_ok(None)),
                ("payload=<객체>", lambda: _synthetic_verify_always_ok(object())),
            ),
            note="구조적으로 실패할 수 없다. 도구가 이것을 CANNOT_FAIL 로 잡아야 한다",
        ),
        Probe(
            "SYNTHETIC::verify_crash_only",
            "DICT_OK_FALSE",
            "SYNTHETIC",
            lambda: _synthetic_verify_crash_only({"ok": True}),
            (
                ("payload=None (TypeError)", lambda: _synthetic_verify_crash_only(None)),
                ("payload={} (KeyError)", lambda: _synthetic_verify_crash_only({})),
            ),
            note="나쁜 입력에 크래시만 낸다. 크래시를 실패로 세면 CAN_FAIL 로 오판된다 (R36)",
        ),
        Probe(
            "SYNTHETIC::assert_positive",
            "RAISE:ValueError",
            "SYNTHETIC",
            lambda: _synthetic_assert_positive(1),
            (
                ("n=0", lambda: _synthetic_assert_positive(0)),
                ("n=-3", lambda: _synthetic_assert_positive(-3)),
            ),
            note="정상적으로 실패를 내는 함수. 도구가 잡으면 안 된다",
        ),
        # ── evidence.py ─────────────────────────────────────────────────
        Probe(
            "evidence.py::_assert_no_inlined_binary",
            "RAISE:InlinedBinaryError",
            "VERIFIER",
            lambda: evidence._assert_no_inlined_binary(
                {"ptr": "n1/screenshot.png"}, slot=evidence.EvidenceSlot.CONTROL_FACTS
            ),
            (
                (
                    "payload=b'\\x89PNG'",
                    lambda: evidence._assert_no_inlined_binary(
                        b"\x89PNG", slot=evidence.EvidenceSlot.SCREENSHOT
                    ),
                ),
                (
                    "payload='data:image/png;base64,...'",
                    lambda: evidence._assert_no_inlined_binary(
                        "data:image/png;base64,AAAA", slot=evidence.EvidenceSlot.SCREENSHOT
                    ),
                ),
                (
                    "payload={'shot_b64': 'AAAA'}",
                    lambda: evidence._assert_no_inlined_binary(
                        {"shot_b64": "AAAA"}, slot=evidence.EvidenceSlot.DOM
                    ),
                ),
            ),
        ),
        Probe(
            "evidence.py::EvidenceRunWriter._assert_writable",
            "RAISE:EvidenceError|RunSealedError",
            "VERIFIER",
            lambda: evidence.EvidenceRunWriter(tmp / "w_ok", key).open()._assert_writable(),
            (
                ("open() 하지 않은 writer", unopened_writer._assert_writable),
                ("seal() 된 writer", writer._assert_writable),
            ),
        ),
        Probe(
            "evidence.py::verify_manifest_linkage",
            "RAISE:ManifestLinkageError",
            "VERIFIER",
            lambda: evidence.verify_manifest_linkage(run_dir, path_manifest_bytes=pm_bytes),
            (
                (
                    "path_manifest_bytes 를 다른 바이트로 교체",
                    lambda: evidence.verify_manifest_linkage(
                        run_dir, path_manifest_bytes=b'{"steps":[1]}'
                    ),
                ),
                (
                    "manifest.jsonl 에 1바이트 덧붙임",
                    lambda: evidence.verify_manifest_linkage(
                        _append_byte(tampered_dir / "manifest.jsonl", tampered_dir),
                        path_manifest_bytes=pm_bytes,
                    ),
                ),
            ),
        ),
        Probe(
            "evidence.py::verify_evidence_run",
            "DICT_OK_FALSE",
            "VERIFIER",
            lambda: evidence.verify_evidence_run(run_dir),
            (("dom.html 내용 변조", lambda: evidence.verify_evidence_run(tampered_dir)),),
            vacuous=(
                "slot 0개로 봉인된 run (manifest 가 비어 있다)",
                lambda: evidence.verify_evidence_run(empty_run_dir),
            ),
        ),
        Probe(
            "evidence.py::verify_retention_manifest",
            "DICT_OK_FALSE",
            "VERIFIER",
            lambda: evidence.verify_retention_manifest(_retention(good_files), base=tmp),
            (
                (
                    "파일 sha256 을 0*64 로 변조",
                    lambda: evidence.verify_retention_manifest(
                        _retention([{**good_files[0], "sha256": "0" * 64}]), base=tmp
                    ),
                ),
                (
                    "manifest 에만 있고 디스크에 없는 path",
                    lambda: evidence.verify_retention_manifest(
                        _retention([{"path": "real/ghost.txt", "sha256": "0" * 64, "bytes": 1}]),
                        base=tmp,
                    ),
                ),
                (
                    "aggregate_sha256 을 0*64 로 변조",
                    lambda: evidence.verify_retention_manifest(
                        _retention(good_files, aggregate="0" * 64), base=tmp
                    ),
                ),
            ),
            vacuous=(
                "manifest={} (roots 키 자체가 없다)",
                lambda: evidence.verify_retention_manifest({}, base=tmp),
            ),
            note="B 가 지정한 must_flag. 관측은 지정과 다르다 — 실패 입력이 존재한다",
            evidence="evidence.py:625-652 — sha256_of_file 재계산 후 manifest 값과 비교한다",
        ),
        Probe(
            "evidence.py::assert_layer_qualified",
            "RAISE:LayerQualificationError",
            "VERIFIER",
            lambda: evidence.assert_layer_qualified({"endpoint_status": "AUTH_GATE"}),
            (
                (
                    "{'status': 'AUTH_GATE'} — 층 미표시 키",
                    lambda: evidence.assert_layer_qualified({"status": "AUTH_GATE"}),
                ),
                ("['ABSTAIN'] — 리스트 원소", lambda: evidence.assert_layer_qualified(["ABSTAIN"])),
                (
                    "'AUTH_GATE' — 최상위 문자열",
                    lambda: evidence.assert_layer_qualified("AUTH_GATE"),
                ),
            ),
        ),
        Probe(
            "evidence.py::assert_coordinates_preserved",
            "RAISE:CoordinateDropError",
            "VERIFIER",
            lambda: evidence.assert_coordinates_preserved(
                {"entry_zone": "TOP", "entry_x_norm": 0.1, "entry_y_norm": 0.2}
            ),
            (
                (
                    "entry_zone 만 남기고 좌표 키 삭제",
                    lambda: evidence.assert_coordinates_preserved({"entry_zone": "TOP"}),
                ),
                (
                    "FLOATING override 인데 좌표 키 삭제",
                    lambda: evidence.assert_coordinates_preserved({"entry_zone": "FLOATING"}),
                ),
                (
                    "중첩 record 안에서 좌표 키 삭제",
                    lambda: evidence.assert_coordinates_preserved(
                        {"rows": [{"entry_zone": "MID"}]}
                    ),
                ),
            ),
        ),
        Probe(
            "evidence.py::verify_denominator_chain",
            "RAISE:DenominatorError",
            "VERIFIER",
            lambda: evidence.verify_denominator_chain(good_chain, ledger=ledger),
            (
                (
                    "chain 의 원장 sha 를 0*64 로 변조",
                    lambda: evidence.verify_denominator_chain(
                        {**good_chain, "replacement_ledger_sha256": "0" * 64}, ledger=ledger
                    ),
                ),
                (
                    "chain 에서 원장 sha 키 삭제",
                    lambda: evidence.verify_denominator_chain({"family_id": "F1"}, ledger=ledger),
                ),
            ),
        ),
        Probe(
            "evidence.py::assert_depth_attribution_evidenced",
            "RAISE:DepthAttributionEvidenceError",
            "VERIFIER",
            lambda: evidence.assert_depth_attribution_evidenced(
                [
                    {
                        "action_token": "SELECT_ORIGIN",
                        "step_index": 0,
                        "input_mode": "DROPDOWN",
                        "included": True,
                    }
                ]
            ),
            (
                (
                    "필수 필드 input_mode 삭제",
                    lambda: evidence.assert_depth_attribution_evidenced(
                        [{"action_token": "SELECT_ORIGIN", "step_index": 0, "included": True}]
                    ),
                ),
                (
                    "input_mode 를 Δ9 어휘 밖 값으로",
                    lambda: evidence.assert_depth_attribution_evidenced(
                        [
                            {
                                "action_token": "SELECT_ORIGIN",
                                "step_index": 0,
                                "input_mode": "VOICE",
                                "included": True,
                            }
                        ]
                    ),
                ),
                (
                    "input_mode=None 인데 included 판정만 존재",
                    lambda: evidence.assert_depth_attribution_evidenced(
                        [
                            {
                                "action_token": "SELECT_ORIGIN",
                                "step_index": 0,
                                "input_mode": None,
                                "included": False,
                            }
                        ]
                    ),
                ),
            ),
        ),
        # ── r32_check.py ────────────────────────────────────────────────
        Probe(
            "r32_check.py::check",
            "NONEMPTY_LIST",
            "VERIFIER",
            lambda: r32_check.check(None, skip_oracle=True),
            (
                (
                    "목록 문서에서 행 1개 삭제한 사본",
                    lambda: r32_check.check(broken_doc, skip_oracle=True),
                ),
            ),
            note="오라클 층은 브라우저를 열지 않지만 무겁다 — 구조/표류 층으로만 실증한다",
        ),
        # ── runner.py ───────────────────────────────────────────────────
        Probe(
            "runner.py::EligibilityChecker.check",
            "NEVER",
            "PROTOCOL_DECLARATION",
            lambda: runner.EligibilityChecker.check(object(), contract()),  # type: ignore[arg-type]
            (
                ("contract=None", lambda: runner.EligibilityChecker.check(object(), None)),  # type: ignore[arg-type]
                ("contract=<객체>", lambda: runner.EligibilityChecker.check(object(), object())),  # type: ignore[arg-type]
            ),
            note="Protocol 선언. 본문이 `...` 라 어떤 입력에도 None 을 낸다",
            evidence="runner.py:249 — 본문이 Ellipsis 하나",
        ),
        Probe(
            "runner.py::SafetyGuard.assert_action_allowed",
            "NEVER",
            "PROTOCOL_DECLARATION",
            lambda: runner.SafetyGuard.assert_action_allowed(object(), contract(), ok_action),  # type: ignore[arg-type]
            (
                (
                    "action_token 이 어휘 밖",
                    lambda: runner.SafetyGuard.assert_action_allowed(  # type: ignore[arg-type]
                        object(), contract(), runner.PlannedAction(action_token="NOT_A_TOKEN")
                    ),
                ),
                (
                    "contract=None, action=None",
                    lambda: runner.SafetyGuard.assert_action_allowed(object(), None, None),  # type: ignore[arg-type]
                ),
            ),
            note="Protocol 선언. 집행은 safety.ActivationSafetyGuard 가 한다",
            evidence="runner.py:278 — 본문이 Ellipsis 하나",
        ),
        Probe(
            "runner.py::verify_path_manifest_hash",
            "RAISE:PathManifestHashMismatchError",
            "VERIFIER",
            lambda: runner.verify_path_manifest_hash(
                path_manifest, runner.path_manifest_sha256(path_manifest)
            ),
            (
                (
                    "declared_sha256=None (부재)",
                    lambda: runner.verify_path_manifest_hash(path_manifest, None),
                ),
                (
                    "declared_sha256='' (빈 문자열)",
                    lambda: runner.verify_path_manifest_hash(path_manifest, ""),
                ),
                (
                    "declared_sha256=0*64 (불일치)",
                    lambda: runner.verify_path_manifest_hash(path_manifest, "0" * 64),
                ),
            ),
        ),
        Probe(
            "runner.py::V3Runner.verify_contract_hashes",
            "RAISE:ContractHashMismatchError",
            "VERIFIER",
            lambda: rnr.verify_contract_hashes(contract()),
            (
                (
                    "task_contract_hash='' (부재)",
                    lambda: rnr.verify_contract_hashes(contract(task_contract_hash="")),
                ),
                (
                    "endpoint_contract_hash='' (부재)",
                    lambda: rnr.verify_contract_hashes(contract(endpoint_contract_hash="")),
                ),
                (
                    "task_role 이 R3 어휘 밖",
                    lambda: rnr.verify_contract_hashes(contract(task_role="TERTIARY")),
                ),
                (
                    "hasher 가 다른 해시를 낸다 (불일치)",
                    lambda: runner.V3Runner(
                        evidence_root=tmp / "ev2",
                        contract_hasher=_MismatchHasher(),
                        safety=_NullGuard(),
                    ).verify_contract_hashes(contract()),
                ),
            ),
        ),
        Probe(
            "runner.py::V3Runner._assert_action_allowed",
            "RAISE:ProhibitedActionError",
            "VERIFIER",
            lambda: rnr._assert_action_allowed(contract(), ok_action),
            (
                (
                    "action_token 이 04 §2 어휘 밖",
                    lambda: rnr._assert_action_allowed(
                        contract(), runner.PlannedAction(action_token="NOT_A_TOKEN")
                    ),
                ),
                (
                    "계약의 forbidden_actions 에 든 토큰",
                    lambda: rnr._assert_action_allowed(
                        contract(forbidden_actions=("OPEN_GLOBAL_MENU",)), ok_action
                    ),
                ),
            ),
        ),
        # ── safety.py ───────────────────────────────────────────────────
        Probe(
            "safety.py::ActivationSafetyGuard.assert_action_allowed",
            "RAISE:SafetyStop",
            "VERIFIER",
            lambda: safety.ActivationSafetyGuard(contract()).assert_action_allowed(
                contract(), ok_action
            ),
            (
                (
                    "결제 실행으로 읽히는 control (visible_text='결제하기')",
                    lambda: safety.ActivationSafetyGuard(contract()).assert_action_allowed(
                        contract(),
                        runner.PlannedAction(
                            action_token="OPEN_GLOBAL_MENU",
                            control_selector="#pay",
                            control_visible_text="결제하기",
                        ),
                    ),
                ),
            ),
        ),
        Probe(
            "safety.py::GuardedPage._check_press",
            "RAISE:SafetyStop",
            "VERIFIER",
            lambda: gpage._check_press("click", "#plain-link"),
            (("selector='text=결제하기'", lambda: gpage._check_press("click", "text=결제하기")),),
        ),
        Probe(
            "safety.py::GuardedPage._check_text",
            "RAISE:SafetyStop",
            "VERIFIER",
            lambda: gpage._check_text("fill", "#q", "FIX"),
            (
                (
                    "계약 fixture 밖의 텍스트 입력",
                    lambda: gpage._check_text("fill", "#q", "01012345678"),
                ),
                (
                    "자격정보 필드로 판정되는 selector",
                    lambda: gpage._check_text("fill", "input[type=password]", "FIX"),
                ),
            ),
        ),
        Probe(
            "safety.py::GuardedPage.check",
            "RAISE:SafetyStop",
            "ACTUATION_NAME_COLLISION",
            lambda: gpage.check("#agree"),
            (("selector='text=결제하기'", lambda: gpage.check("text=결제하기")),),
            note="playwright checkbox `check` 다 — 검증 함수가 아니다. 이름 충돌로 계열에 들어왔다",
        ),
        Probe(
            "safety.py::RecordingPage.check",
            "NEVER",
            "TEST_DOUBLE",
            lambda: rpage.check("#agree") if rpage else None,
            (
                (
                    "selector='text=결제하기'",
                    lambda: rpage.check("text=결제하기") if rpage else None,
                ),
                ("selector=None", lambda: rpage.check(None) if rpage else None),  # type: ignore[arg-type]
            ),
            note="기록용 fake. 검증하지 않는다고 선언한 것이므로 R43 시정 대상이 아니다",
        ),
    ]
    return tuple(probes)


class _MismatchHasher:
    def task_contract_hash(self, c: Any) -> str:
        return "F" * 64

    def endpoint_contract_hash(self, c: Any) -> str:
        return "F" * 64


def _append_byte(target: Path, run_dir: Path) -> Path:
    with target.open("ab") as fh:
        fh.write(b"\n")
    return run_dir


PROBES: tuple[Probe, ...] = ()


# ══════════════════════════════════════════════════════════════════════════
# 층 4 — 검사
# ══════════════════════════════════════════════════════════════════════════


def check() -> tuple[list[str], list[dict[str, Any]], list[dict[str, Any]]]:
    """(실패 목록, probe 결과, 열거 결과) — 실패 목록이 비어 있으면 통과."""
    enumerated = enumerate_family(v3_runner_root())

    probes = _build_probes()
    results = [run_probe(p) for p in probes]
    by_id = {r["point_id"]: r for r in results}

    failures: list[str] = []

    # ── 대조가 먼저다. 대조가 깨지면 목록을 신뢰할 수 없다 ────────────────
    for role, (pid, want) in sorted(CONTROLS.items()):
        got = by_id.get(pid)
        if got is None:
            failures.append(f"[대조] {role}: probe 가 없다 — {pid}")
        elif got["verdict"] != want:
            failures.append(f"[대조] {role}: {pid} 기대={want} 관측={got['verdict']}")

    # ── 열거 ↔ probe 정합 (표류 금지) ────────────────────────────────────
    repo_ids = {r["point_id"] for r in enumerated}
    probe_ids = {r["point_id"] for r in results if r["kind"] != "SYNTHETIC"}
    for pid in sorted(repo_ids - probe_ids):
        failures.append(f"[표류] 코드에 있으나 실증 목록에 없다 — {pid}")
    for pid in sorted(probe_ids - repo_ids):
        failures.append(f"[표류] 실증 목록에 있으나 코드에 없다 — {pid}")

    # ── baseline 이 통과하지 않으면 실증이 공허하다 ──────────────────────
    for r in results:
        if not r["baseline_passes"]:
            failures.append(
                f"[공허] {r['point_id']}: baseline 입력이 통과하지 않는다 — {r['baseline_detail']}"
            )

    return failures, results, enumerated


# ══════════════════════════════════════════════════════════════════════════
# 산출 — `R35` 4요소
# ══════════════════════════════════════════════════════════════════════════

DECLARED_FAILURE_BEHAVIOUR = {
    "0": "통과 — 산출을 쓴다 (status=PASS)",
    "1": "검사가 돌았고 실패했다 — 산출을 쓴다 (status=FAIL). 지우지 않는다: 감사 흔적",
    "2": "검사가 돌지 않았다 — 산출을 쓰지 않는다. 통과로도 실패로도 읽지 마라",
}


def result_path() -> Path:
    return _RESEARCH_ROOT / "docs" / "v3" / "R43_CHECK_RESULT.json"


def demo_sidecar_path() -> Path:
    return _RESEARCH_ROOT / "docs" / "v3" / "R43_FAILURE_DEMO.json"


def tool_sha256(path: Path | None = None) -> str:
    """이 검사기 소스의 sha256. `R40` — 실증은 이 값에 묶인다."""
    return hashlib.sha256((path or _HERE).read_bytes()).hexdigest()


def _rel(path: Path) -> str:
    try:
        return str(path.relative_to(_RESEARCH_ROOT))
    except ValueError:
        return str(path)


def _read_json(path: Path) -> dict[str, Any] | None:
    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return loaded if isinstance(loaded, dict) else None


def build_result(
    failures: list[str], results: list[dict[str, Any]], enumerated: list[dict[str, Any]]
) -> dict[str, Any]:
    """`R35` 4요소. **시각·난수를 넣지 않는다** — sha 비교가 측정 수단이다."""
    by_id = {r["point_id"]: r for r in results}
    controls = []
    for role, (pid, want) in sorted(CONTROLS.items()):
        got = by_id.get(pid)
        controls.append(
            {
                "role": role,  # ① 대조 목록
                "point_id": pid,
                "expected": want,
                "observed": got["verdict"] if got else None,
                "passed": bool(got and got["verdict"] == want),  # ② 결과
                "detail": (got or {}).get("note", "probe 가 없다"),
            }
        )
    briefed_pid, briefed_want = BRIEFED_CONTROL
    briefed_got = by_id.get(briefed_pid)
    repo = [r for r in results if r["kind"] != "SYNTHETIC"]
    engine_rows = enumerate_family(engine_root()) if engine_root().is_dir() else []
    return {
        "schema": "w5r/r43-check-result/1",
        "status": "PASS" if not failures else "FAIL",
        "scope": {
            "enumerated_over": "src/landing_accessibility/v3_runner/**/*.py",
            "rule": (
                "def/async def 중 이름에서 선행 '_' 를 뗀 뒤 "
                "verify_ · assert_ · check_ 로 시작하거나 "
                "정확히 'check'/'verify'/'assert' 인 것 (AST, 중첩 포함)"
            ),
            "excluded": "v3_runner/r43/** (이 lane 의 도구 자신)",
            "v3_runner_total": len(enumerated),
            "engine_status": "ENUMERATED_NOT_DEMONSTRATED",
            "engine_total": len(engine_rows),
            "engine_note": "0건이 아니라 미실증이다 (Δ48). 다른 평면 소관",
        },
        "counts": {
            "total": len(repo),
            "CAN_FAIL": sum(1 for r in repo if r["verdict"] == CAN_FAIL),
            "CANNOT_FAIL": sum(1 for r in repo if r["verdict"] == CANNOT_FAIL),
            "VACUOUS_PASS": sum(1 for r in repo if r["vacuous_pass"]),
            "by_kind": {
                k: sum(1 for r in repo if r["kind"] == k) for k in sorted({r["kind"] for r in repo})
            },
            "CANNOT_FAIL_by_kind": {
                k: sum(1 for r in repo if r["kind"] == k and r["verdict"] == CANNOT_FAIL)
                for k in sorted({r["kind"] for r in repo if r["verdict"] == CANNOT_FAIL})
            },
        },
        "controls": controls,
        "briefed_control": {
            "point_id": briefed_pid,
            "role": "must_flag (B 의 과업 지시)",
            "expected": briefed_want,
            "observed": briefed_got["verdict"] if briefed_got else None,
            "status": "FALSIFIED"
            if briefed_got and briefed_got["verdict"] != briefed_want
            else "UPHELD",
            "gating": False,
            "why_not_gating": (
                "이 대조는 방법이 아니라 저장소 상태에 대한 주장이다. 관측이 지시와 다르면 "
                "방법이 틀린 것이 아니라 지시의 전제가 틀린 것이므로, 게이트가 아니라 "
                "반증 기록으로 낸다. 방법 검증은 SYNTHETIC 대조 3건이 담당한다"
            ),
            "demonstrated_failure_inputs": (briefed_got or {}).get("demonstrated_failure_inputs"),
            "vacuous": (briefed_got or {}).get("vacuous"),
        },
        "failures": failures,
        "probes": results,
        "enumeration": enumerated,
        # ③ 도구 경로
        "tool": {
            "module": "landing_accessibility.v3_runner.r43.check",
            "path": _rel(_HERE),
            "sha256": tool_sha256(),
            "exit_codes": DECLARED_FAILURE_BEHAVIOUR,
            "declared_failure_behaviour": (
                "exit 1 은 산출을 남긴다(감사 흔적). exit 2 는 산출을 건드리지 않는다."
            ),
        },
        # ④ 실패 시 동작의 실증 — `R40` 으로 도구 sha 에 묶인다
        "failure_demonstration": _demo_binding(),
    }


def _demo_binding() -> dict[str, Any]:
    demo = _read_json(demo_sidecar_path())
    current = tool_sha256()
    return {
        "sidecar": _rel(demo_sidecar_path()),
        "present": demo is not None,
        "tool_sha256_at_demo": (demo or {}).get("tool_sha256"),
        "tool_sha256_now": current,
        "valid_for_this_commit": bool(demo and demo.get("tool_sha256") == current),
        "cases": [c["name"] for c in (demo or {}).get("cases", [])],
    }


def write_result(result: dict[str, Any], path: Path | None = None) -> Path:
    target = path or result_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return target


def _did_not_run(exc: BaseException) -> int:
    """`exit 2` — 검사가 돌지 않았다. **산출을 건드리지 않는다.**"""
    import traceback

    traceback.print_exc()
    print(
        f"\n검사가 돌지 않았다 ({type(exc).__name__}). "
        "통과로도 실패로도 읽지 마라. 산출은 갱신되지 않았다.",
        file=sys.stderr,
    )
    return 2


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="R43 — 검증 함수 실패 실증 (Δ48)")
    ap.add_argument("--out", type=Path, default=None)
    ap.add_argument("--no-write", action="store_true")
    ap.add_argument("--list-only", action="store_true", help="열거만 하고 실증하지 않는다")
    ns = ap.parse_args(argv)

    if ns.list_only:
        try:
            rows = enumerate_family(v3_runner_root())
        except Exception as exc:
            return _did_not_run(exc)
        for r in rows:
            print(f"{r['point_id']:60} :{r['lineno']}")
        print(f"\n총 {len(rows)}건")
        return 0

    try:
        failures, results, enumerated = check()
        result = build_result(failures, results, enumerated)
    except Exception as exc:
        return _did_not_run(exc)

    for f in failures:
        print(f)
    if not ns.no_write:
        print(f"산출 → {write_result(result, ns.out)}")
    demo = result["failure_demonstration"]
    if not demo["valid_for_this_commit"]:
        print(
            "경고: 실패 동작 실증이 현재 도구 sha 와 묶여 있지 않다 "
            f"(sidecar={demo['tool_sha256_at_demo']}). r43.control_failure_demo 를 다시 돌려라.",
            file=sys.stderr,
        )
    c = result["counts"]
    print(
        f"\n계열 {c['total']}건 — CAN_FAIL {c['CAN_FAIL']} / "
        f"CANNOT_FAIL {c['CANNOT_FAIL']} / VACUOUS_PASS {c['VACUOUS_PASS']}"
    )
    print(f"실패 {len(failures)}건 — status={result['status']}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
