"""W5P — `r32_check` 의 **선언된 실패 동작**을 격리 사본에서 실증한다 (`Δ46` R35③·R40).

왜 별도 도구인가
    매 실행마다 자기를 변형할 수는 없다 — 그 실행이 산출을 건드린다. 그래서 실증은
    **격리 사본**에서 하고, 결과를 sidecar 에 남기며, **그때의 검사기 sha256** 을
    함께 적는다. 검사기를 고치면 sha 가 달라지고 실증은 자동으로 무효가 된다.
    `r32_check` 산출의 ``valid_for_this_commit`` 이 그 비교 결과다.

무엇을 측정하는가
    ``exit`` 이 **아니라** 산출 파일(``R32_CHECK_RESULT.json``)의 **sha256 변화**다.
    `Δ46`: "exit 은 파일에 남지 않는다." ``exit`` 도 함께 기록하되, 판정 근거는
    파일이 바뀌었는가(``wrote``)다.

실증하는 선언 (`r32_check.DECLARED_FAILURE_BEHAVIOUR`)
    ``0`` 통과 → 쓴다 · ``1`` 검사 실패 → **쓴다**(감사 흔적) · ``2`` 미실행 → **안 쓴다**

사례 이름에 대하여 (`R36` · `Δ46`)
    **이름도 주장이다.** A 가 데이터 변형으로 만든 사례에 ``positive_control_fail``
    이라 붙였는데 실제로는 `StopIteration` 크래시였다. 그래서 이 파일의 각 사례는
    ``mutation`` 필드에 **무엇을 변형했는지**를 그대로 적고, 이름은 실증된 것과
    같은지 실행 결과로 확인한 뒤 붙였다. 특히
    ``must_flag_control_disabled_by_source_edit`` 은 **데이터가 아니라 검사기 소스**
    를 고쳐 만든다 — 데이터만으로는 대조군을 무력화할 수 없기 때문이다.

실행:
    python -m landing_accessibility.v3_runner.r32_control_failure_demo
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from landing_accessibility.v3_runner.r32_check import (
    DECLARED_FAILURE_BEHAVIOUR,
    demo_sidecar_path,
    document_path,
    tool_sha256,
)

__all__ = ["CASES", "Case", "main", "run_all"]

_HERE = Path(__file__).resolve()
_V3_RUNNER = _HERE.parent
_PKG = _V3_RUNNER.parent
_RESEARCH_ROOT = _PKG.parent.parent

_REL_CHECKER = "src/landing_accessibility/v3_runner/r32_check.py"
_REL_DOC = "docs/v3/R32_APPLICATION_POINTS.md"
_REL_OUT = "docs/v3/R32_CHECK_RESULT.json"

#: 실증기가 기대하는 것. 실측이 이와 다르면 sidecar 의 `matches_declaration` 이 거짓이다.
_EXPECTED: dict[str, tuple[int, bool]] = {  # name -> (exit, 산출을 썼는가)
    "clean": (0, True),
    "list_row_deleted": (1, True),
    "must_flag_control_disabled_by_source_edit": (1, True),
    "document_unparseable": (2, False),
}


@dataclass(frozen=True)
class Case:
    name: str
    mutation: str
    #: 격리 사본 루트를 받아 변형한다.
    apply: Callable[[Path], None]


def _edit(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    if old not in text:
        raise RuntimeError(f"변형 대상이 없다 — 실증이 성립하지 않는다: {path.name} / {old!r}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


def _delete_row(root: Path) -> None:
    doc = root / _REL_DOC
    target = "| `session.py::is_credential_field::password_scope` |"
    lines = doc.read_text(encoding="utf-8").splitlines(keepends=True)
    kept = [ln for ln in lines if not ln.startswith(target)]
    if len(kept) == len(lines):
        raise RuntimeError("지울 행이 없다 — 실증이 성립하지 않는다")
    doc.write_text("".join(kept), encoding="utf-8")


def _disable_must_flag(root: Path) -> None:
    """**검사기 소스**를 고쳐 충돌 탐지를 무력화한다.

    데이터(문서)만 고쳐서는 대조군을 깰 수 없다 — 문서를 고치면 문서 판정이 틀렸다고
    잡힐 뿐 대조군 자체는 여전히 오라클에서 통과한다. 대조군이 진짜로 무력화되는
    유일한 길은 **판정 술어를 고치는 것**이다.
    """
    _edit(
        root / _REL_CHECKER,
        "            elif out_m == out_a:",
        "            elif False:  # 실증용 변형 — 충돌 탐지 무력화",
    )


def _break_document(root: Path) -> None:
    """부록 A 의 `point_id` 형식을 깨뜨려 **파싱 자체가** 못 돌게 한다.

    본문의 설명용 표에도 같은 문자열이 있으므로 **행 시작**으로 찾는다. 첫 판은
    그것을 놓쳐 본문을 고쳤고 파싱이 멀쩡히 돌았다 — 이름(`document_unparseable`)이
    실증한 것과 달랐을 뻔했다 (`R36`).
    """
    doc = root / _REL_DOC
    target = "| `surface.py::measure_surface::ax_node` |"
    lines = doc.read_text(encoding="utf-8").splitlines(keepends=True)
    hit = False
    for i, ln in enumerate(lines):
        if ln.startswith(target):
            lines[i] = ln.replace("::", "-", 2)
            hit = True
            break
    if not hit:
        raise RuntimeError("부록 A 에서 변형 대상 행을 찾지 못했다 — 실증이 성립하지 않는다")
    doc.write_text("".join(lines), encoding="utf-8")


CASES: tuple[Case, ...] = (
    Case("clean", "변형 없음 (대조)", lambda _root: None),
    Case("list_row_deleted", f"{_REL_DOC}: 목록 표에서 행 1개 삭제 (데이터 변형)", _delete_row),
    Case(
        "must_flag_control_disabled_by_source_edit",
        f"{_REL_CHECKER}: `_judge` 의 충돌 비교를 `False` 로 바꿔 무력화 (**소스 변형**)",
        _disable_must_flag,
    ),
    Case("document_unparseable", f"{_REL_DOC}: point_id 형식 파괴 (데이터 변형)", _break_document),
)


def _sha(path: Path) -> str | None:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError:
        return None


def _run_case(case: Case, seed_out: bool) -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix="w5p-r32-demo-") as tmp:
        root = Path(tmp) / "landing_accessibility"
        shutil.copytree(_RESEARCH_ROOT / "src", root / "src")
        shutil.copytree(_RESEARCH_ROOT / "docs", root / "docs")
        out = root / _REL_OUT
        if seed_out:
            # 이전 실행이 남긴 산출이 있는 상태에서 시작한다 — "덮었는가" 를 재려면
            # 덮을 대상이 있어야 한다.
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text('{"schema": "seed", "status": "SEED"}\n', encoding="utf-8")
        before = _sha(out)
        case.apply(root)
        proc = subprocess.run(
            [sys.executable, "-m", "landing_accessibility.v3_runner.r32_check"],
            cwd=root,
            env={"PYTHONPATH": str(root / "src"), "PATH": "/usr/bin:/bin"},
            capture_output=True,
            text=True,
            timeout=300,
            check=False,
        )
        after = _sha(out)
        wrote = after is not None and after != before
        expected_exit, expected_wrote = _EXPECTED[case.name]
        status, failures, controls = None, [], []
        if after is not None:
            try:
                doc = json.loads(out.read_text(encoding="utf-8"))
            except ValueError:
                status = "UNPARSEABLE"
            else:
                status = doc.get("status")
                failures = doc.get("failures", [])
                controls = [
                    {"role": c["role"], "passed": c["passed"]} for c in doc.get("controls", [])
                ]
        return {
            "name": case.name,
            "mutation": case.mutation,
            "expected": {"exit": expected_exit, "wrote_output": expected_wrote},
            "observed": {
                "exit": proc.returncode,
                "wrote_output": wrote,
                "output_sha256_before": before,
                "output_sha256_after": after,
                "output_status": status,
                # `R36` — 이름이 주장하는 것을 이 두 필드가 뒷받침한다. 이름이
                # `must_flag_...` 인데 must_flag 가 통과했다면 이름이 거짓이다.
                "output_controls": controls,
                "output_failures": failures[:6],
            },
            "matches_declaration": (proc.returncode == expected_exit and wrote == expected_wrote),
            "stderr_tail": proc.stderr.strip().splitlines()[-1:] or [""],
        }


def run_all(*, seed_out: bool = True) -> dict[str, Any]:
    cases = [_run_case(c, seed_out) for c in CASES]
    return {
        "schema": "w5p/r32-failure-demo/1",
        # `R40` — 실증을 도구 sha 에 묶는다. 검사기를 고치면 이 실증은 무효다.
        "tool_sha256": tool_sha256(),
        "tool_path": _REL_CHECKER,
        "demonstrator_path": str(_HERE.relative_to(_RESEARCH_ROOT)),
        "demonstrator_sha256": hashlib.sha256(_HERE.read_bytes()).hexdigest(),
        "document_sha256": _sha(document_path()),
        "declared_failure_behaviour": DECLARED_FAILURE_BEHAVIOUR,
        "measured": "산출 파일(R32_CHECK_RESULT.json)의 sha256 변화. exit 은 파일에 남지 않는다",
        "all_match_declaration": all(c["matches_declaration"] for c in cases),
        "cases": cases,
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="r32_check 의 실패 동작 실증 (격리 사본)")
    ap.add_argument("--out", type=Path, default=None)
    ap.add_argument("--no-write", action="store_true")
    ns = ap.parse_args(argv)
    try:
        report = run_all()
    except Exception as exc:  # 실증기가 돌지 않았다
        import traceback

        traceback.print_exc()
        print(
            f"\n실증이 돌지 않았다 ({type(exc).__name__}). 실증됨으로 읽지 마라.",
            file=sys.stderr,
        )
        return 2
    for c in report["cases"]:
        mark = "OK " if c["matches_declaration"] else "MISMATCH"
        print(
            f"{mark:9} {c['name']:44} exit={c['observed']['exit']} "
            f"wrote={c['observed']['wrote_output']} status={c['observed']['output_status']}"
        )
    if not ns.no_write:
        target = ns.out or demo_sidecar_path()
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(
            json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        print(f"sidecar → {target}")
    return 0 if report["all_match_declaration"] else 1


if __name__ == "__main__":
    sys.exit(main())
