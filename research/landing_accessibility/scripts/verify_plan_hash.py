#!/usr/bin/env python3
"""동결 계획 파일의 hash candidate 를 재계산해 대조한다.

**규칙 (B lane 산출물)**

    payload = 계획 dict 에서 hash 필드 **하나만** 제거한 것 (파일의 키 순서 그대로)
    blob    = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=False).encode("utf-8")
    hash    = sha256(blob).hexdigest()

`sort_keys=False` 이므로 **키 순서가 해시에 들어간다.** 파일을 읽을 때 순서를 보존해야 한다
(Python 3.7+ dict 는 삽입 순서를 유지하므로 `json.load` 로 충분하다).

적용 대상:
    E001_MASTER_PLAN.json  ← frozen_plan_hash_candidate
    E000_FAST_PLAN.json    ← fast_plan_hash_candidate

**적용되지 않는 것 — E000_PLAN.json (`e000_plan_hash_candidate`)**
그 파일은 다른 방식으로 만들어졌다: 자기 자신의 hash 필드를 placeholder 로 둔 상태의
파일 바이트를 해싱한 뒤 값을 덮어썼다. 최종 산출물만으로는 placeholder 표현을 알 수 없어
**독립 재현이 불가능하다.** 이 스크립트는 그 파일을 UNVERIFIABLE 로 보고한다 — 통과시키지 않는다.

usage: verify_plan_hash.py <plan.json> <hash_field>
       verify_plan_hash.py --all        (알려진 계획 파일 전체)
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

UNVERIFIABLE_SCHEME = {"e000_plan_hash_candidate"}


def recompute(path: Path, hash_field: str) -> tuple[str, str]:
    """(declared, recomputed) 을 돌려준다."""
    with open(path, encoding="utf-8") as f:
        plan = json.load(f)
    declared = plan.pop(hash_field)
    blob = json.dumps(plan, ensure_ascii=False, indent=2, sort_keys=False).encode("utf-8")
    return declared, hashlib.sha256(blob).hexdigest()


def check(path: Path, hash_field: str) -> bool:
    if hash_field in UNVERIFIABLE_SCHEME:
        print(f"UNVERIFIABLE  {path.name}:{hash_field} — placeholder-byte scheme, 최종본만으로 재현 불가")
        return False
    declared, got = recompute(path, hash_field)
    ok = declared == got
    print(f"{'MATCH       ' if ok else 'MISMATCH    '}  {path.name}:{hash_field}\n"
          f"              declared   = {declared}\n"
          f"              recomputed = {got}")
    return ok


def main(argv: list[str]) -> int:
    if len(argv) == 2 and argv[1] == "--all":
        root = Path(__file__).resolve().parents[1] / "shadow"
        known = [
            (root / "e001_plan" / "E001_MASTER_PLAN.json", "frozen_plan_hash_candidate"),
            (root / "e000_plan" / "E000_FAST_PLAN.json", "fast_plan_hash_candidate"),
        ]
        results = [check(p, f) for p, f in known if p.exists()]
        return 0 if results and all(results) else 1
    if len(argv) != 3:
        print(__doc__, file=sys.stderr)
        return 2
    return 0 if check(Path(argv[1]), argv[2]) else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
