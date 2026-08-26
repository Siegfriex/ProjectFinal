#!/usr/bin/env python3
"""v2 문서 설치본 무결성 검증.

세 층으로 검증한다.

1. **pack 파생 파일** — 원본 docs pack(`MANIFEST.json`)에서 온 파일.
   설치본에 비권위 배너가 삽입된 경우 배너를 걷어낸 **본문 바이트**가 원본과
   동일해야 한다. 배너는 `INSTALLED-BANNER-START/END` 주석으로 감싸여 있다.

2. **저장소 저작 파일** — 원본 pack에 대응물이 없는 권위문서
   (`EXECUTION_AUTHORITY.md`, `PHASE_GATES.md`, `A*.md` 등).
   외부 앵커가 없으므로 git을 앵커로 쓴다. 추적 중이고 워킹트리가 깨끗해야 한다.
   (닫는 결함: `install-manifest-is-self-anchored`)

3. **커버리지** — `docs/v2/` 아래 모든 `.md`/`.json`이 설치 매니페스트에 등재돼야 한다.
   매니페스트 자신도 git 앵커로 검증한다.
   (닫는 결함: `install-integrity-coverage-gap`)

exit 0 = PASS, exit 1 = FAIL.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parents[1]
V2 = ROOT / "docs" / "v2"
INSTALL_MANIFEST = V2 / "INSTALL_MANIFEST.json"
SOURCE_MANIFEST = V2 / "MANIFEST.json"

BANNER_START = b"<!-- INSTALLED-BANNER-START -->"
BANNER_END = b"<!-- INSTALLED-BANNER-END -->"

# 배너를 넣어도 되는 파일은 이 셋뿐이다. 권위문서(00~05)에 배너가 들어가면
# 위조 조항을 본문처럼 읽히게 할 수 있다 — adversarial V2-C003 이 실제로 뚫었다.
# 정책을 EXECUTION_AUTHORITY 문장에만 두지 않고 여기서 강제한다.
# (닫는 결함: install-manifest-does-not-enforce-declared-banner-policy)
BANNER_ALLOWED = frozenset(
    {
        "docs/v2/README.md",
        "docs/v2/bootstrap/07_CLAUDE_FIRST_SESSION_PROMPT_v2.0.md",
        "CLAUDE.md",
    }
)


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def strip_banner(data: bytes) -> bytes:
    """설치 시 삽입한 비권위 배너를 걷어내고 원본 본문만 남긴다."""
    start = data.find(BANNER_START)
    if start == -1:
        return data
    end = data.find(BANNER_END)
    if end == -1:
        raise ValueError("배너 시작만 있고 종료 표식이 없다")
    tail = data[end + len(BANNER_END) :]
    return data[:start] + tail.lstrip(b"\n")


def git_tracked_and_clean(rel_to_repo: str) -> tuple[bool, str]:
    ls = subprocess.run(
        ["git", "-C", str(REPO), "ls-files", "--error-unmatch", rel_to_repo],
        capture_output=True,
        text=True,
    )
    if ls.returncode != 0:
        return False, "git 미추적"
    diff = subprocess.run(
        ["git", "-C", str(REPO), "status", "--porcelain", "--", rel_to_repo],
        capture_output=True,
        text=True,
    )
    if diff.stdout.strip():
        return False, f"워킹트리 오염: {diff.stdout.strip()}"
    return True, ""


def main() -> int:
    install = json.loads(INSTALL_MANIFEST.read_text(encoding="utf-8"))
    source = json.loads(SOURCE_MANIFEST.read_text(encoding="utf-8"))
    failures: list[str] = []

    for rel, spec in sorted(install["files"].items()):
        target = ROOT / rel
        if not target.exists():
            failures.append(f"MISSING   {rel}")
            continue
        raw = target.read_bytes()

        if sha256(raw) != spec["sha256"]:
            failures.append(f"SHA       {rel}: 설치본 해시가 매니페스트와 다르다")
            continue
        if len(raw) != spec["bytes"]:
            failures.append(f"BYTES     {rel}: {len(raw)} != {spec['bytes']}")
            continue

        # 배너 검사는 앵커 종류와 무관하게 **모든** 설치 파일에 먼저 건다.
        # (닫는 결함: install-manifest-banner-allowlist-skips-repo-authored-authority-docs)
        if BANNER_START in raw or BANNER_END in raw:
            if rel not in BANNER_ALLOWED:
                failures.append(
                    f"BANNER    {rel}: 배너 마커가 있다 — 배너는 {sorted(BANNER_ALLOWED)} 에만 허용된다"
                )
                continue
            if raw.count(BANNER_START) != 1 or raw.count(BANNER_END) != 1:
                failures.append(f"BANNER    {rel}: 배너 마커가 정확히 한 쌍이 아니다")
                continue
            if not raw.startswith(BANNER_START):
                failures.append(f"BANNER    {rel}: 배너가 파일 최상단에 있지 않다")
                continue

        origin = spec.get("source_pack_name")
        if origin:
            ref = source.get(origin)
            if ref is None:
                failures.append(f"ORIGIN    {rel}: {origin} 이 MANIFEST.json 에 없다")
                continue
            try:
                body = strip_banner(raw)
            except ValueError as exc:
                failures.append(f"BANNER    {rel}: {exc}")
                continue
            banner_present = body != raw
            if (
                spec.get("banner_inserted") is not None
                and spec["banner_inserted"] != banner_present
            ):
                failures.append(
                    f"BANNER    {rel}: banner_inserted={spec['banner_inserted']} 인데 실제는 {banner_present}"
                )
                continue
            if banner_present:
                banner = raw[: raw.find(BANNER_END) + len(BANNER_END)]
                declared = spec.get("banner_sha256")
                if not declared:
                    failures.append(
                        f"BANNER    {rel}: banner_sha256 미선언 — 배너 내용이 앵커되지 않는다"
                    )
                    continue
                if sha256(banner) != declared:
                    failures.append(f"BANNER    {rel}: 배너 내용이 매니페스트 선언과 다르다")
                    continue
            body_hash = sha256(body)
            if body_hash != ref["sha256"]:
                failures.append(f"DRIFT     {rel}: 배너 제외 본문이 원본 pack {origin} 과 다르다")
                continue
            if spec.get("body_sha256") and spec["body_sha256"] != body_hash:
                failures.append(f"BODY      {rel}: body_sha256 불일치")
                continue
            mark = "pack" if body == raw else "pack+banner"
        else:
            rel_repo = str((ROOT / rel).relative_to(REPO))
            ok, why = git_tracked_and_clean(rel_repo)
            if not ok:
                failures.append(f"ANCHOR    {rel}: {why}")
                continue
            mark = "repo-authored"

        print(f"{'OK':10} {rel}  [{mark}]")

    # 두 매니페스트 자신의 앵커. layer-1 기준선인 MANIFEST.json 이 무앵커로 남으면
    # 원본 대조의 근거 자체를 바꿔치기할 수 있다 (ssot V2-C002 install-integrity-coverage-gap).
    for manifest in (SOURCE_MANIFEST, INSTALL_MANIFEST):
        rel = manifest.relative_to(ROOT)
        ok, why = git_tracked_and_clean(str(manifest.relative_to(REPO)))
        if not ok:
            failures.append(f"ANCHOR    {rel}: {why}")
        else:
            print(f"{'OK':10} {rel}  [manifest, git-anchored]")

    # 원본 pack 전건이 설치됐는가
    for name in source:
        if name == "MANIFEST.json":
            continue
        if not any(s.get("source_pack_name") == name for s in install["files"].values()):
            failures.append(f"UNINSTALLED  원본 pack {name} 이 설치 매니페스트에 없다")

    # docs/v2 아래 전건이 매니페스트에 등재됐는가
    declared = {(ROOT / r).resolve() for r in install["files"]}
    for path in sorted(V2.rglob("*")):
        if not path.is_file() or path.suffix not in {".md", ".json"}:
            continue
        if path.name in {"MANIFEST.json", "INSTALL_MANIFEST.json"}:
            continue
        if path.resolve() not in declared:
            failures.append(f"UNDECLARED   {path.relative_to(ROOT)} 이 설치 매니페스트에 없다")

    if failures:
        print("\n".join(failures), file=sys.stderr)
        print("V2_DOCS_VERIFY: FAIL", file=sys.stderr)
        return 1
    print("V2_DOCS_VERIFY: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
