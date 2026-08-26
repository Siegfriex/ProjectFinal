"""E001 증거 Run 의 manifest 계약 — **수집 전에 검증 경로를 먼저 만든다.**

## 왜 이 파일이 수집보다 먼저 있는가 (C012 / D1)

`.gitignore` 는 `evidence/*/dom/`·`ax/`·`screen/`·`probe/` 를 선제 제외한다.
즉 **한 줄도 수집하기 전에 재검증 불가 구조를 이미 만들어 뒀다.**
Pilot 이 원증거 682MB 를 gitignore 해 단일 머신에만 남긴 것과 정확히 같은 패턴이다.
Pilot 의 그 자산은 지금 논리 백업으로만 남아 있고, 다른 clone 에서 재검증할 수 없다.

제외 자체는 유지한다 — 수백 MB 의 DOM/스크린샷을 git 에 넣는 것은 다른 종류의 사고다.
대신 **제외를 감당 가능하게 만드는 조건**을 코드로 건다.

    evidence/<run_id>/manifest.jsonl 은 반드시 추적된다.
    manifest 가 없는 Run 은 유효하지 않다.

manifest 한 줄은 파일 하나를 가리키고 `observation_id` · `relpath` · `sha256` · `bytes` 를 갖는다.
raw 바이트가 로컬에만 있어도, 다른 clone 을 받은 사람은
  - Run 에 어떤 관측이 몇 건 있었는지
  - 각 관측의 어떤 산출물이 몇 바이트였고 해시가 무엇이었는지
  - 자기 손에 있는 파일이 그 해시와 같은지
를 전부 확인할 수 있다. **재현은 못 해도 위조는 잡힌다.**

## 계약

1. `load_run_manifest()` 는 manifest 가 없으면 `MissingRunManifestError` 를 던진다.
   "manifest 없이는 Run 이 유효하지 않다" 를 문서가 아니라 코드가 강제한다.
2. `verify_run()` 은 manifest 를 기준선으로 삼아 로컬 파일을 대조한다.
   raw 가 없는 clone 에서는 `require_files=False` 로 **구조 검증만** 수행하고,
   그 사실을 보고서의 `mode` 에 남긴다 — 검사하지 않은 것을 통과로 세지 않는다.
3. 이 모듈은 어떤 네트워크 접근도 하지 않는다. E001 본수집과 무관하다.

근거 메모: `docs/07_EVIDENCE_MANIFEST_CONTRACT.md`
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

MANIFEST_FILENAME = "manifest.jsonl"

#: manifest 한 줄이 반드시 가져야 하는 필드.
REQUIRED_ENTRY_FIELDS: frozenset[str] = frozenset({"observation_id", "relpath", "sha256", "bytes"})

#: sha256 은 접두사 없는 소문자 hex 64자로 적는다(레지스트리 스냅샷과 동일 규약).
_SHA256_LEN = 64


class RunManifestError(Exception):
    """Run manifest 계약 위반."""


class MissingRunManifestError(RunManifestError):
    """manifest 가 없다 — 그 Run 은 유효하지 않다."""


class MalformedRunManifestError(RunManifestError):
    """manifest 는 있으나 계약을 만족하지 않는다."""


@dataclass(frozen=True)
class ManifestEntry:
    observation_id: str
    relpath: str
    sha256: str
    bytes: int
    extra: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            "observation_id": self.observation_id,
            "relpath": self.relpath,
            "sha256": self.sha256,
            "bytes": self.bytes,
            **self.extra,
        }


def manifest_path(run_dir: Path | str) -> Path:
    return Path(run_dir) / MANIFEST_FILENAME


def load_run_manifest(run_dir: Path | str) -> list[ManifestEntry]:
    """Run manifest 를 읽는다. 없으면 `MissingRunManifestError` 를 던진다.

    이 예외가 계약의 전부다. 하류 코드는 manifest 를 우회해 evidence 디렉터리를
    직접 걷지 않는다 — 걸으면 로컬에만 있는 파일이 곧 진실이 되어버린다.
    """
    path = manifest_path(run_dir)
    if not path.exists():
        raise MissingRunManifestError(
            f"{path} 가 없다. manifest 없는 Run 은 유효하지 않다 "
            "(docs/07_EVIDENCE_MANIFEST_CONTRACT.md)."
        )

    entries: list[ManifestEntry] = []
    seen: set[tuple[str, str]] = set()
    for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            rec = json.loads(line)
        except json.JSONDecodeError as exc:
            raise MalformedRunManifestError(f"{path}:{lineno} JSON 파싱 실패: {exc}") from exc
        if not isinstance(rec, dict):
            raise MalformedRunManifestError(f"{path}:{lineno} 객체가 아니다")
        missing = REQUIRED_ENTRY_FIELDS - rec.keys()
        if missing:
            raise MalformedRunManifestError(f"{path}:{lineno} 필수 필드 누락: {sorted(missing)}")

        sha = str(rec["sha256"])
        if len(sha) != _SHA256_LEN or any(c not in "0123456789abcdef" for c in sha):
            raise MalformedRunManifestError(
                f"{path}:{lineno} sha256 은 접두사 없는 소문자 hex 64자여야 한다: {sha!r}"
            )
        if not isinstance(rec["bytes"], int) or rec["bytes"] < 0:
            raise MalformedRunManifestError(f"{path}:{lineno} bytes 가 음이 아닌 정수가 아니다")

        relpath = str(rec["relpath"])
        if relpath.startswith("/") or ".." in Path(relpath).parts:
            raise MalformedRunManifestError(
                f"{path}:{lineno} relpath 는 Run 디렉터리 기준 상대경로여야 한다: {relpath!r}"
            )

        key = (str(rec["observation_id"]), relpath)
        if key in seen:
            raise MalformedRunManifestError(
                f"{path}:{lineno} (observation_id, relpath) 중복: {key}"
            )
        seen.add(key)

        entries.append(
            ManifestEntry(
                observation_id=str(rec["observation_id"]),
                relpath=relpath,
                sha256=sha,
                bytes=int(rec["bytes"]),
                extra={k: v for k, v in rec.items() if k not in REQUIRED_ENTRY_FIELDS},
            )
        )

    if not entries:
        raise MalformedRunManifestError(f"{path} 가 비어 있다 — 관측 0건인 Run 은 유효하지 않다")
    return entries


def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def verify_run(run_dir: Path | str, *, require_files: bool = True) -> dict[str, Any]:
    """manifest 를 기준선으로 Run 을 검증한다.

    require_files=False 는 raw 가 없는 clone 용이다. 그 경우 파일 대조를 **하지 않았다**고
    보고서에 남기고, 없는 파일을 통과로 세지 않는다.
    """
    run_dir = Path(run_dir)
    entries = load_run_manifest(run_dir)

    report: dict[str, Any] = {
        "run_id": run_dir.name,
        # 절대경로를 보고서에 넣지 않는다 (C012/D3 와 같은 이유).
        "manifest": MANIFEST_FILENAME,
        "mode": "FULL_BYTE_VERIFICATION" if require_files else "STRUCTURE_ONLY_RAW_ABSENT",
        "entries": len(entries),
        "observations": len({e.observation_id for e in entries}),
        "declared_bytes": sum(e.bytes for e in entries),
        "files_checked": 0,
        "missing_files": [],
        "byte_mismatch": [],
        "hash_mismatch": [],
    }

    for entry in entries:
        target = run_dir / entry.relpath
        if not target.exists():
            if require_files:
                report["missing_files"].append(entry.relpath)
            continue
        report["files_checked"] += 1
        actual_bytes = target.stat().st_size
        if actual_bytes != entry.bytes:
            report["byte_mismatch"].append(
                {"relpath": entry.relpath, "declared": entry.bytes, "actual": actual_bytes}
            )
        actual_sha = sha256_of(target)
        if actual_sha != entry.sha256:
            report["hash_mismatch"].append(
                {"relpath": entry.relpath, "declared": entry.sha256, "actual": actual_sha}
            )

    failed = report["missing_files"] or report["byte_mismatch"] or report["hash_mismatch"]
    if failed:
        report["status"] = "FAILED"
    elif require_files:
        report["status"] = "VERIFIED"
    else:
        report["status"] = "MANIFEST_WELL_FORMED_FILES_NOT_CHECKED"
    return report


def write_run_manifest(run_dir: Path | str, entries: list[ManifestEntry]) -> Path:
    """manifest 를 쓴다. 정렬을 고정해 같은 입력이 같은 바이트를 낸다."""
    run_dir = Path(run_dir)
    run_dir.mkdir(parents=True, exist_ok=True)
    path = manifest_path(run_dir)
    ordered = sorted(entries, key=lambda e: (e.observation_id, e.relpath))
    path.write_text(
        "".join(
            json.dumps(e.as_dict(), ensure_ascii=False, sort_keys=True) + "\n" for e in ordered
        ),
        encoding="utf-8",
    )
    return path
