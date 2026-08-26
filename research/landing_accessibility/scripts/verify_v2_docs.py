#!/usr/bin/env python3
"""v2 문서 설치본 무결성 검증.

설치된 각 파일의 sha256을 INSTALL_MANIFEST.json 과 대조하고, 원본 docs pack
MANIFEST.json 에 기록된 바이트/해시와도 일치하는지 확인한다.

exit 0 = PASS, exit 1 = FAIL.
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
V2 = ROOT / "docs" / "v2"
INSTALL_MANIFEST = V2 / "INSTALL_MANIFEST.json"
SOURCE_MANIFEST = V2 / "MANIFEST.json"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    install = json.loads(INSTALL_MANIFEST.read_text(encoding="utf-8"))
    source = json.loads(SOURCE_MANIFEST.read_text(encoding="utf-8"))
    failures: list[str] = []

    for rel, spec in install["files"].items():
        target = ROOT / rel
        if not target.exists():
            failures.append(f"MISSING  {rel}")
            continue
        actual = sha256(target)
        if actual != spec["sha256"]:
            failures.append(f"SHA      {rel}: {actual} != {spec['sha256']}")
            continue
        size = target.stat().st_size
        if size != spec["bytes"]:
            failures.append(f"BYTES    {rel}: {size} != {spec['bytes']}")
            continue
        origin = spec.get("source_pack_name")
        if origin:
            ref = source.get(origin)
            if ref is None:
                failures.append(f"ORIGIN   {rel}: {origin} not in MANIFEST.json")
            elif ref["sha256"] != actual:
                failures.append(f"DRIFT    {rel}: 원본 pack {origin} 과 바이트 불일치")
        print(f"{'OK':8} {rel}")

    for name in source:
        if name == "MANIFEST.json":
            continue
        if not any(s.get("source_pack_name") == name for s in install["files"].values()):
            failures.append(f"UNINSTALLED  원본 pack {name} 이 설치 매니페스트에 없다")

    if failures:
        print("\n".join(failures), file=sys.stderr)
        print("V2_DOCS_VERIFY: FAIL", file=sys.stderr)
        return 1
    print("V2_DOCS_VERIFY: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
