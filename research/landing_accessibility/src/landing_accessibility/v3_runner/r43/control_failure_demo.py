"""W5R — `r43.check` 의 **선언된 실패 동작**을 격리 사본에서 실증한다 (`Δ46` R35③ · `R40`).

왜 별도 도구이고 왜 격리 사본인가
    매 실행마다 자기를 변형할 수는 없다 — 그 실행이 산출을 건드린다. 그래서 실증은
    **저장소 밖 임시 사본**에서 하고, 결과를 sidecar 에 남기며 **그때의 검사기
    sha256** 을 함께 적는다. 검사기를 고치면 sha 가 달라지고 실증은 자동으로
    무효가 된다 — `r43.check` 산출의 ``valid_for_this_commit`` 이 그 비교 결과다.

무엇을 측정하는가
    ``exit`` 이 **아니라** 산출 파일(``R43_CHECK_RESULT.json``)의 **sha256 변화**다.
    `Δ46`: "exit 은 파일에 남지 않는다." ``exit`` 도 함께 기록하되, 판정 근거는
    파일이 바뀌었는가(``wrote_output``)다.

실증하는 선언 (`r43.check.DECLARED_FAILURE_BEHAVIOUR`)
    ``0`` 통과 → 쓴다 · ``1`` 검사 실패 → **쓴다**(감사 흔적) · ``2`` 미실행 → **안 쓴다**

사례 이름에 대하여 (`R36`)
    **이름도 주장이다.** A 가 데이터 변형 사례에 ``positive_control_fail`` 이라
    붙였는데 실제로는 크래시였다. 그래서 각 사례는 ``mutation`` 에 **무엇을 어디서
    변형했는지**를 적고, ``asserts`` 에 **그 이름이 주장하는 것**을 적는다. 이름이
    주장한 것이 관측되지 않으면 ``name_verified`` 가 거짓이다.

    ``data_mutation_leaves_controls_intact`` 는 데이터만 고쳐서는 대조군이 깨지지
    않는다는 것을 **이름 그대로** 실증한다. 대조군을 실제로 깨는 사례는
    ``must_flag_control_disabled_by_source_edit`` 하나뿐이고, 그것은 **검사기 소스**
    를 고친다.

`R40` 결속이 실제로 무효화하는가
    ``--test-binding`` 은 사본에서 검사기 소스에 주석 한 줄을 더해 sha 를 바꾼 뒤
    ``valid_for_this_commit`` 이 ``false`` 가 되는지 본다. **항상 참인 필드는
    아무것도 말하지 않는다** — 참이 될 수 있는 것만으로는 부족하고, 거짓이 될 수
    있음을 보여야 그 필드가 정보를 담는다.

실행::

    python -m landing_accessibility.v3_runner.r43.control_failure_demo
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

from landing_accessibility.v3_runner.r43.check import (
    DECLARED_FAILURE_BEHAVIOUR,
    demo_sidecar_path,
    tool_sha256,
)

__all__ = ["CASES", "Case", "main", "run_all", "test_binding"]

_HERE = Path(__file__).resolve()
_R43_DIR = _HERE.parent
_V3_RUNNER = _R43_DIR.parent
_PKG = _V3_RUNNER.parent
_RESEARCH_ROOT = _PKG.parent.parent

_REL_CHECKER = "src/landing_accessibility/v3_runner/r43/check.py"
_REL_TARGET = "src/landing_accessibility/v3_runner/evidence.py"
_REL_OUT = "docs/v3/R43_CHECK_RESULT.json"
_MODULE = "landing_accessibility.v3_runner.r43.check"

#: 실증기가 기대하는 것. 실측이 이와 다르면 sidecar 의 `matches_declaration` 이 거짓이다.
_EXPECTED: dict[str, tuple[int, bool]] = {  # name -> (exit, 산출을 썼는가)
    "clean": (0, True),
    "data_mutation_leaves_controls_intact": (0, True),
    "must_flag_control_disabled_by_source_edit": (1, True),
    "probe_target_renamed_in_source": (1, True),
    "target_module_unimportable": (2, False),
}

#: `R36` — 각 이름이 **주장하는 것**. 관측이 이 술어를 만족해야 이름이 참이다.
_NAME_CLAIMS: dict[str, str] = {
    "clean": "변형이 없으면 대조 5건이 전부 통과하고 실패 0건이다",
    "data_mutation_leaves_controls_intact": (
        "데이터(산출 JSON)만 고치면 대조군은 그대로 통과한다 — 데이터로는 대조군을 못 깬다"
    ),
    "must_flag_control_disabled_by_source_edit": (
        "검사기 소스를 고쳐 크래시를 실패로 세게 만들면 must_flag 대조가 깨진다"
    ),
    "probe_target_renamed_in_source": (
        "실증 대상 함수의 def 이름을 바꾸면(호출은 별칭으로 살아 있어도) [표류] 로 "
        "잡힌다 — 목록이 코드와 붙어 있다"
    ),
    "target_module_unimportable": (
        "검사 대상 모듈을 import 할 수 없으면 exit 2 이고 산출을 건드리지 않는다"
    ),
}


@dataclass(frozen=True)
class Case:
    name: str
    mutation: str
    #: 격리 사본 루트를 받아 변형한다.
    apply: Callable[[Path], None]
    #: 관측 dict 를 받아 이름이 주장한 것이 실제로 일어났는지 본다 (`R36`).
    name_check: Callable[[dict[str, Any]], bool]


def _edit(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    if old not in text:
        raise RuntimeError(f"변형 대상이 없다 — 실증이 성립하지 않는다: {path.name} / {old!r}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


# ── 변형 ──────────────────────────────────────────────────────────────────


def _mutate_output_only(root: Path) -> None:
    """산출 JSON 을 손으로 고친다. **데이터 변형** — 검사기 로직은 건드리지 않는다."""
    out = root / _REL_OUT
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(
            {
                "schema": "w5r/r43-check-result/1",
                "status": "PASS",
                "counts": {"total": 999, "CAN_FAIL": 999, "CANNOT_FAIL": 0},
                "controls": [{"role": "must_flag__synthetic_always_ok", "passed": True}],
                "failures": [],
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


def _disable_must_flag(root: Path) -> None:
    """**검사기 소스**를 고쳐 크래시를 선언된 실패로 세게 만든다.

    이것이 `R36` 이 막는 바로 그 오독이다 — 크래시를 실패로 세면
    ``SYNTHETIC::verify_crash_only`` 가 `CAN_FAIL` 로 뒤집히고 must_flag 대조가 깨진다.
    데이터로는 이 대조를 깰 수 없다.
    """
    _edit(
        root / _REL_CHECKER,
        '        return {"outcome": CRASH, "detail": f"{name}: {str(exc)[:160]}"}',
        '        return {"outcome": DECLARED_FAIL, "detail": f"{name}: {str(exc)[:160]}"}'
        "  # 실증용 변형 — 크래시를 실패로 센다",
    )


def _rename_probe_target(root: Path) -> None:
    """실증 대상 함수의 `def` 이름만 바꾸고 **런타임 별칭은 남긴다**.

    첫 판은 함수를 통째로 잘라냈는데, 뒤따르는 상수 블록까지 함께 사라져 모듈이
    import 되지 않았다 — `exit 2`(미실행)가 나왔고 이름이 주장한 `[표류]` 는
    관측되지 않았다. `name_verified` 가 그것을 잡았다(`R36`). 그래서 변형을
    **이름만** 바꾸는 것으로 좁혔다: 별칭이 있어 호출은 그대로 되고 `def` 이름만
    사라지므로, 잡히면 그건 순수하게 목록↔코드 결속 때문이다.
    """
    target = root / _REL_TARGET
    _edit(
        target,
        'def assert_layer_qualified(payload: Any, *, path: str = "$") -> None:',
        'def enforce_layer_qualified(payload: Any, *, path: str = "$") -> None:',
    )
    text = target.read_text(encoding="utf-8")
    text = text.replace(
        "assert_layer_qualified(value, path=", "enforce_layer_qualified(value, path="
    )
    target.write_text(
        text + "\n\n# 실증용 변형 — 호출부는 살려 둔다. 사라진 것은 `def` 이름뿐이다.\n"
        "assert_layer_qualified = enforce_layer_qualified\n",
        encoding="utf-8",
    )


def _break_target_module(root: Path) -> None:
    """검사 대상 모듈을 import 불가로 만든다 — **검사가 돌지 않는다**(exit 2)."""
    (root / _REL_TARGET).write_text("this is not python(\n", encoding="utf-8")


CASES: tuple[Case, ...] = (
    Case(
        "clean",
        "변형 없음 (대조)",
        lambda _root: None,
        lambda o: (
            o["output_status"] == "PASS"
            and o["output_failures"] == []
            and len(o["output_controls"]) == 5
            and all(c["passed"] for c in o["output_controls"])
        ),
    ),
    Case(
        "data_mutation_leaves_controls_intact",
        f"{_REL_OUT}: 산출 JSON 을 손으로 조작 (데이터 변형)",
        _mutate_output_only,
        lambda o: (
            o["output_status"] == "PASS"
            and all(c["passed"] for c in o["output_controls"])
            and o["output_counts"].get("total") != 999
        ),
    ),
    Case(
        "must_flag_control_disabled_by_source_edit",
        f"{_REL_CHECKER}: `_classify` 의 CRASH 분기를 DECLARED_FAIL 로 바꿈 (**소스 변형**)",
        _disable_must_flag,
        lambda o: (
            o["output_status"] == "FAIL"
            and any(
                c["role"] == "must_flag__synthetic_crash_only" and not c["passed"]
                for c in o["output_controls"]
            )
        ),
    ),
    Case(
        "probe_target_renamed_in_source",
        f"{_REL_TARGET}: `assert_layer_qualified` 의 def 이름을 변경 + 별칭 유지 (**소스 변형**)",
        _rename_probe_target,
        lambda o: (
            o["output_status"] == "FAIL"
            and any(f.startswith("[표류]") for f in o["output_failures"])
        ),
    ),
    Case(
        "target_module_unimportable",
        f"{_REL_TARGET}: 문법 파괴로 import 불가 (**소스 변형**)",
        _break_target_module,
        lambda o: o["exit"] == 2 and not o["wrote_output"],
    ),
)


def _sha(path: Path) -> str | None:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError:
        return None


def _copy_tree(dest: Path) -> Path:
    root = dest / "landing_accessibility"
    shutil.copytree(_RESEARCH_ROOT / "src", root / "src")
    shutil.copytree(_RESEARCH_ROOT / "docs", root / "docs")
    return root


def _invoke(root: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", _MODULE],
        cwd=root,
        env={"PYTHONPATH": str(root / "src"), "PATH": "/usr/bin:/bin"},
        capture_output=True,
        text=True,
        timeout=600,
        check=False,
    )


def _run_case(case: Case, seed_out: bool) -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix="w5r-r43-demo-") as tmp:
        root = _copy_tree(Path(tmp))
        out = root / _REL_OUT
        if seed_out:
            # "덮었는가" 를 재려면 덮을 대상이 있어야 한다.
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text('{"schema": "seed", "status": "SEED"}\n', encoding="utf-8")
        case.apply(root)
        before = _sha(out)
        proc = _invoke(root)
        after = _sha(out)
        wrote = after is not None and after != before
        expected_exit, expected_wrote = _EXPECTED[case.name]
        status, failures, controls, counts = None, [], [], {}
        if after is not None:
            try:
                doc = json.loads(out.read_text(encoding="utf-8"))
            except ValueError:
                status = "UNPARSEABLE"
            else:
                status = doc.get("status")
                failures = doc.get("failures", [])
                counts = doc.get("counts", {})
                controls = [
                    {"role": c["role"], "passed": c["passed"], "observed": c.get("observed")}
                    for c in doc.get("controls", [])
                ]
        observed = {
            "exit": proc.returncode,
            "wrote_output": wrote,
            "output_sha256_before": before,
            "output_sha256_after": after,
            "output_status": status,
            "output_counts": counts,
            "output_controls": controls,
            "output_failures": failures[:6],
        }
        try:
            name_ok = bool(case.name_check(observed))
        except (KeyError, TypeError):
            name_ok = False
        return {
            "name": case.name,
            "mutation": case.mutation,
            "asserts": _NAME_CLAIMS[case.name],
            "expected": {"exit": expected_exit, "wrote_output": expected_wrote},
            "observed": observed,
            "matches_declaration": (proc.returncode == expected_exit and wrote == expected_wrote),
            # `R36` — 이름이 실증한 것과 같은가
            "name_verified": name_ok,
            "stderr_tail": proc.stderr.strip().splitlines()[-1:] or [""],
        }


def test_binding() -> dict[str, Any]:
    """`R40` 결속이 **실제로 무효화하는지** 시험한다.

    sidecar 를 심어 `valid_for_this_commit` 이 참이 되는 상태를 만든 뒤, 검사기 소스만
    바꿔 sha 를 어긋나게 하고 같은 필드가 거짓이 되는지 본다. 두 값이 다 관측돼야
    이 필드가 정보를 담는다 — **항상 참인 필드는 아무것도 말하지 않는다.**
    """
    out: dict[str, Any] = {}
    for label, mutate in (("sha_matches", False), ("sha_mutated", True)):
        with tempfile.TemporaryDirectory(prefix="w5r-r43-bind-") as tmp:
            root = _copy_tree(Path(tmp))
            checker = root / _REL_CHECKER
            sidecar = root / "docs" / "v3" / demo_sidecar_path().name
            sidecar.parent.mkdir(parents=True, exist_ok=True)
            sidecar.write_text(
                json.dumps(
                    {
                        "schema": "w5r/r43-failure-demo/1",
                        "tool_sha256": hashlib.sha256(checker.read_bytes()).hexdigest(),
                        "cases": [{"name": "binding-probe"}],
                    },
                    ensure_ascii=False,
                )
                + "\n",
                encoding="utf-8",
            )
            if mutate:
                checker.write_text(
                    checker.read_text(encoding="utf-8") + "\n# R40 결속 시험용 변형 — 한 줄 추가\n",
                    encoding="utf-8",
                )
            proc = _invoke(root)
            doc = json.loads((root / _REL_OUT).read_text(encoding="utf-8"))
            out[label] = {
                "exit": proc.returncode,
                "tool_sha256_at_demo": doc["failure_demonstration"]["tool_sha256_at_demo"],
                "tool_sha256_now": doc["failure_demonstration"]["tool_sha256_now"],
                "valid_for_this_commit": doc["failure_demonstration"]["valid_for_this_commit"],
            }
    out["binding_is_informative"] = (
        out["sha_matches"]["valid_for_this_commit"] is True
        and out["sha_mutated"]["valid_for_this_commit"] is False
    )
    return out


def run_all(*, seed_out: bool = True) -> dict[str, Any]:
    cases = [_run_case(c, seed_out) for c in CASES]
    binding = test_binding()
    return {
        "schema": "w5r/r43-failure-demo/1",
        # `R40` — 실증을 도구 sha 에 묶는다. 검사기를 고치면 이 실증은 무효다.
        "tool_sha256": tool_sha256(),
        "tool_path": _REL_CHECKER,
        "demonstrator_path": str(_HERE.relative_to(_RESEARCH_ROOT)),
        "demonstrator_sha256": hashlib.sha256(_HERE.read_bytes()).hexdigest(),
        "declared_failure_behaviour": DECLARED_FAILURE_BEHAVIOUR,
        "measured": "산출 파일(R43_CHECK_RESULT.json)의 sha256 변화. exit 은 파일에 남지 않는다",
        "isolation": "저장소 밖 임시 디렉터리로 src/ + docs/ 를 복사해 그 안에서만 변형한다",
        "all_match_declaration": all(c["matches_declaration"] for c in cases),
        "all_names_verified": all(c["name_verified"] for c in cases),
        "binding_invalidation_test": binding,
        "cases": cases,
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="r43.check 의 실패 동작 실증 (격리 사본)")
    ap.add_argument("--out", type=Path, default=None)
    ap.add_argument("--no-write", action="store_true")
    ap.add_argument("--binding-only", action="store_true")
    ns = ap.parse_args(argv)

    try:
        report = test_binding() if ns.binding_only else run_all()
    except Exception as exc:  # 실증기가 돌지 않았다
        import traceback

        traceback.print_exc()
        print(f"\n실증이 돌지 않았다 ({type(exc).__name__}).", file=sys.stderr)
        return 2

    if ns.binding_only:
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0 if report["binding_is_informative"] else 1

    for c in report["cases"]:
        mark = "OK  " if c["matches_declaration"] else "DIFF"
        nm = "이름OK" if c["name_verified"] else "이름불일치"
        print(
            f"{mark} {nm:10} {c['name']:42} "
            f"exit={c['observed']['exit']} wrote={c['observed']['wrote_output']}"
        )
    b = report["binding_invalidation_test"]
    print(
        f"\nR40 결속: sha일치={b['sha_matches']['valid_for_this_commit']} "
        f"sha변형={b['sha_mutated']['valid_for_this_commit']} "
        f"→ 정보를 담는가={b['binding_is_informative']}"
    )
    if not ns.no_write:
        target = ns.out or demo_sidecar_path()
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(
            json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        print(f"sidecar → {target}")
    ok = (
        report["all_match_declaration"]
        and report["all_names_verified"]
        and b["binding_is_informative"]
    )
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
