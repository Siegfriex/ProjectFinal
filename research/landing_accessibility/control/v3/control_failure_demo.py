#!/usr/bin/env python3
"""`check_ruling_index.py` 의 실패 시 동작을 **실행으로** 실증한다 (Δ46/R40).

`R35` 의 셋째 요소는 "**실행으로 실증된** 실패 시 동작" 이다.
"검사가 실패하면 쓰지 않는다" 는 실행되기 전까지 주장이다 (`R36`).

매 실행마다 자기를 변형할 수는 없다 — 그 실행이 산출을 건드린다.
그래서 **실증을 도구 sha 에 묶는다**(D-V3-FINDING-020 의 설계를 채택).
도구가 바뀌면 실증은 `valid_for_this_commit: false` 가 되고, 없는 실증이 있는 것으로 읽히지 않는다.
"""
import json, os, shutil, subprocess, sys, tempfile, hashlib

HERE = os.path.dirname(os.path.abspath(__file__))
CHECKER = os.path.join(HERE, "check_ruling_index.py")
IDX = os.path.join(HERE, "V3_RULING_INDEX.json")
DELTA = os.path.join(HERE, "V3_0_1_SUCCESSOR_DELTA.md")
SIDECAR = os.path.join(HERE, "CONTROL_FAILURE_DEMO.json")


def sha(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()


def trial(name, mutate, expect_write, patch_checker=None, expect_exit=None):
    """격리 사본에서 --write 를 돌리고 **산출이 바뀌었는지**를 잰다."""
    with tempfile.TemporaryDirectory() as d:
        for src in (CHECKER, IDX, DELTA):
            shutil.copy2(src, d)
        if patch_checker:
            cp = os.path.join(d, os.path.basename(CHECKER))
            src = open(cp, encoding="utf-8").read()
            old, new = patch_checker
            assert old in src, f"{name}: 패치 대상 문자열이 없다 — 변형이 걸리지 않았다"
            open(cp, "w", encoding="utf-8").write(src.replace(old, new, 1))
        idx_copy = os.path.join(d, os.path.basename(IDX))
        if mutate:
            m = json.load(open(idx_copy, encoding="utf-8"))
            mutate(m)
            json.dump(m, open(idx_copy, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        before = sha(idx_copy)
        r = subprocess.run([sys.executable, os.path.join(d, os.path.basename(CHECKER)), "--write"],
                           capture_output=True, text=True)
        after = sha(idx_copy)
        wrote = before != after
        ok = wrote == expect_write and (expect_exit is None or r.returncode == expect_exit)
        return {"case": name, "exit": r.returncode, "expected_exit": expect_exit,
                "output_changed": wrote, "expected_output_changed": expect_write,
                "verdict": "PASS" if ok else "FAIL",
                "kind": "must_not_write" if not expect_write else "must_write"}


def main():
    cases = [
        # 검사 실패 — 쓰지 않아야 한다
        trial("check_fail__count_mismatch",
              lambda m: m.__setitem__("count", 999999), False, expect_exit=1),
        # 양성대조 실패 — **검사기 소스를 변형해** 한 검사를 무력화한다.
        # 데이터만으로는 양성대조를 깨지 못한다(깨려 하면 검사기가 크래시한다) —
        # 첫 판에서 A 가 이것을 `positive_control_fail` 로 이름 붙였다가 실제로는
        # StopIteration 크래시였음을 확인했다. **이름이 거짓이었다.**
        trial("positive_control_fail__check_disabled", None, False, expect_exit=2,
              patch_checker=('        fail.append(("count_mismatch",',
                             '        pass  # 무력화 (변형)\n        _unused = (("count_mismatch",')),
        # 검사기 크래시 — **미실행**이다. 실패(exit 1)와 구분돼야 한다
        trial("checker_crash__unrunnable", lambda m: [r.__setitem__("aliases", []) for r in m["rulings"]],
              False, expect_exit=2),
        # 정상 — 써야 한다 (must_not_flag 대조)
        trial("clean__writes", None, True, expect_exit=0),
    ]
    out = {
        "what": "check_ruling_index.py 의 실패 시 동작 실증 (R35 셋째 요소)",
        "checker": "control/v3/check_ruling_index.py",
        "checker_sha256": sha(CHECKER),
        "declared_failure_behavior": "검사 실패(exit 1) 또는 양성대조 실패(exit 2) 이면 "
                                     "**색인 파일을 쓰지 않는다.** 실패한 검사 아래 나온 값이 "
                                     "디스크에 남으면 다음에 읽는 쪽이 정상 산출과 구분하지 못한다",
        "method": "격리 임시 사본에서 --write 를 돌리고 **산출 파일의 sha 변화**를 잰다. "
                  "exit 코드는 파일에 남지 않으므로 exit 만으로는 실증이 아니다",
        "cases": cases,
        "verdict": "PASS" if all(c["verdict"] == "PASS" for c in cases) else "FAIL",
        "limitation": "변이는 **내가 상상한 고장**만 잰다. 네 종뿐이다",
        "exit_semantics": "0=통과·쓴다 · 1=검사 실패 · **2=검사가 돌지 않았다(양성대조 실패 또는 크래시) — 통과로도 실패로도 읽지 마라**",
    }
    json.dump(out, open(SIDECAR, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    for c in cases:
        print(f"  {c['case']:44s} exit={c['exit']}(기대 {c['expected_exit']}) "
              f"changed={c['output_changed']} {c['verdict']}")
    print(f"verdict={out['verdict']}  checker_sha256={out['checker_sha256'][:16]}…")
    return 0 if out["verdict"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
