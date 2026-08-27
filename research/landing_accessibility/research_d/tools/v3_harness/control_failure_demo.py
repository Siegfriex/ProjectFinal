"""대조군 실패 시 동작을 **실행으로** 실증하고 그 결과를 도구 커밋에 묶어 남긴다.

A 의 Δ41-R35 는 산출물이 네 가지를 담기를 요구한다 —
대조 목록 · 각 결과 · **실행으로 실증된 실패 시 동작** · 도구 경로와 커밋.

셋째가 어렵다. 도구가 "대조군이 실패하면 산출을 쓰지 않는다" 고 적는 것은
**주장**이고, R36 대로 주장은 실행으로 실증되지 않으면 주장일 뿐이다.
그런데 매 실행마다 자기를 변형해 돌릴 수는 없다(그 실행 자체가 산출을
건드린다).

그래서 실증을 **도구 커밋에 묶는다**. 변형 실행은 여기서 한 번 하고 결과를
sidecar 에 남기며, 그 sidecar 는 그때의 도구 파일 sha 를 함께 적는다.
도구가 바뀌면 sha 가 달라지고 산출물은 `NOT_DEMONSTRATED_FOR_THIS_COMMIT`
으로 나온다 — **없는 실증을 있는 것으로 읽지 않는다.**
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

HARNESS = Path(__file__).resolve().parent
RD = HARNESS.parent.parent
OUT = RD / "results" / "CONTROL_FAILURE_DEMOS.json"


def _sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def demonstrate(tool: Path, mutation: tuple[str, str], expect_exit: int,
                guards: list[Path]) -> dict:
    """tool 을 한 줄 변형해 별도 파일로 실행하고, 종료코드와 산출 불변을 잰다."""
    src = tool.read_text(encoding="utf-8")
    old, new = mutation
    if old not in src:
        return {"demonstrated": False, "why": f"변형 지점을 찾지 못했다: {old[:40]}"}
    before = {str(g): (_sha(g) if g.exists() else None) for g in guards}
    mut = tool.with_name("_mut_" + tool.name)
    try:
        mut.write_text(src.replace(old, new, 1), encoding="utf-8")
        r = subprocess.run([sys.executable, str(mut)], capture_output=True, text=True)
        after = {str(g): (_sha(g) if g.exists() else None) for g in guards}
        first = next((l for l in r.stdout.splitlines() if l.strip()), "")
        return {"demonstrated": True,
                "mutation": old.strip()[:60] + " → " + new.strip()[:60],
                "exit_code": r.returncode,
                "exit_as_expected": r.returncode == expect_exit,
                "first_output_line": first[:120],
                "guarded_files_unchanged": before == after,
                "guarded_files": [str(Path(g).relative_to(RD)) for g in guards]}
    finally:
        mut.unlink(missing_ok=True)


def demonstrate_records(tool: Path, mutation: tuple[str, str], out_file: Path,
                        expect_verdict: str) -> dict:
    """실패 시 **쓰지 않는** 것이 아니라 **기록하는** 도구용. 산출에 그 verdict 가
    실제로 남는지 잰다 — 방화벽은 감사 흔적을 지우지 않는 쪽이 맞다."""
    import shutil
    src = tool.read_text(encoding="utf-8")
    old, new = mutation
    if old not in src:
        return {"demonstrated": False, "why": f"변형 지점 없음: {old[:40]}"}
    backup = out_file.read_bytes() if out_file.exists() else None
    mut = tool.with_name("_mut_" + tool.name)
    try:
        mut.write_text(src.replace(old, new, 1), encoding="utf-8")
        r = subprocess.run([sys.executable, str(mut)], capture_output=True, text=True)
        got = json.loads(out_file.read_text(encoding="utf-8")).get("verdict") if out_file.exists() else None
        return {"demonstrated": True,
                "mutation": old.strip()[:60] + " → " + new.strip()[:60],
                "exit_code": r.returncode,
                "recorded_verdict": got,
                "verdict_as_expected": got == expect_verdict,
                "artifact_kept": out_file.exists()}
    finally:
        mut.unlink(missing_ok=True)
        if backup is not None:
            out_file.write_bytes(backup)          # 원래 산출을 되돌린다


DEMOS = [
    {"name": "reconcile_lanes",
     "tool": HARNESS / "reconcile_lanes.py",
     "mutation": ("def _names(container) -> list[str]:",
                  "def _names(container) -> list[str]:\n    return []  # MUTATION"),
     "expect_exit": 3,
     "guards": [RD / "results" / "harness" / "RECONCILIATION.json"],
     "why": "D-DEF-11 재현 — 이름 추출이 실패하면 겹침이 있어도 0 건이 된다"},
    {"name": "index_delta_crosscheck",
     "tool": HARNESS / "index_delta_crosscheck.py",
     "mutation": ("    def reach(rid, tokens):",
                  "    def reach(rid, tokens):\n        return None  # MUTATION"),
     "expect_exit": 3,
     "guards": [RD / "results" / "D_V3_INDEX_DELTA_CROSSCHECK_v3resolver.json"],
     "why": "도달 판정이 무조건 미도달이 되면 전 행이 '미도달' 로 보고된다"},
]


def main() -> int:
    ts = subprocess.run(["date", "-Iseconds"], capture_output=True,
                        text=True).stdout.strip()
    head = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True,
                          text=True).stdout.strip()
    out = {"artifact": "D_CONTROL_FAILURE_DEMOS", "measured_at_kst": ts,
           "d_head": head, "rule": "Δ41-R35 — 실행으로 실증된 실패 시 동작",
           "demos": {}}
    ok = True
    # 기록형 도구 — 방화벽
    fw = RD / "tools" / "d_input_firewall.py"
    fw_out = RD / "results" / "D_INPUT_FIREWALL_VERIFICATION.json"
    fres = demonstrate_records(
        fw, ("def severity(hit: dict, text: str) -> str:",
             'def severity(hit: dict, text: str) -> str:\n    return "ALLOWED_BY_EXCEPTION"  # MUTATION'),
        fw_out, "CONTROL_FAIL")
    fres.update({"tool": "tools/d_input_firewall.py", "tool_sha256": _sha(fw),
                 "why_this_mutation": "매처가 열리면 금지 경로가 전부 허용된다",
                 "expected_behavior": "CONTROL_FAIL 로 기록하고 exit 2"})
    fres["verdict"] = "PASS" if (fres.get("verdict_as_expected")
                                 and fres.get("artifact_kept")) else "FAIL"
    ok &= fres["verdict"] == "PASS"
    out["demos"]["d_input_firewall"] = fres
    print(f"  {'d_input_firewall':<26} exit={fres.get('exit_code')} "
          f"기록된verdict={fres.get('recorded_verdict')} → {fres['verdict']}")

    for d in DEMOS:
        res = demonstrate(d["tool"], d["mutation"], d["expect_exit"], d["guards"])
        res["tool"] = str(d["tool"].relative_to(RD))
        res["tool_sha256"] = _sha(d["tool"])
        res["why_this_mutation"] = d["why"]
        res["expect_exit"] = d["expect_exit"]
        good = res.get("exit_as_expected") and res.get("guarded_files_unchanged")
        res["verdict"] = "PASS" if good else "FAIL"
        ok &= bool(good)
        out["demos"][d["name"]] = res
        print(f"  {d['name']:<26} exit={res.get('exit_code')} "
              f"기대={d['expect_exit']} 산출불변={res.get('guarded_files_unchanged')} "
              f"→ {res['verdict']}")
    out["verdict"] = "PASS" if ok else "FAIL"
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"wrote {OUT.relative_to(RD)}  verdict={out['verdict']}")
    return 0 if ok else 1


import sys as _sys; from pathlib import Path as _P
_sys.path.insert(0, str(_P(__file__).resolve().parents[1]))
import d_exit

if __name__ == "__main__":
    raise SystemExit(d_exit.run(main))
