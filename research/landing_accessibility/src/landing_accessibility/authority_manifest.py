"""A1 권위 매니페스트의 **판본 식별** — 매니페스트 판본과 원문 판본을 구분한다 (C012 / D2).

## 문제

`sources/wiseapp/authority_manifest.json` 에는 version/revision 필드가 없었고 자신의 sha256 도
등록돼 있지 않았다. C001 이후 두 번 바뀌었는데(C009, C011) 어느 시점 판본을 보고 있는지
파일만으로는 알 수 없다. 감사자가 "이 매니페스트가 그때 그 매니페스트인가"를 물으면
git 히스토리를 뒤지는 것 외에 답이 없었다.

## 구분해야 하는 두 가지

| 대상 | 필드 | 성질 |
|---|---|---|
| **A1 원문 판본** | `raw_assets.*.sha256` | **불변**. 2026-08-26 에 동결한 933 판본의 바이트 해시다. 매니페스트를 몇 번 고치든 바뀌지 않는다 |
| **매니페스트 판본** | `manifest_revision` / `revised_at` / `revision_log` | 가변. 우리가 원문을 어떻게 기술했는지의 판본이다 |

이 둘을 한 필드로 뭉개면 "원문이 바뀌었다"와 "우리 설명이 바뀌었다"가 구별되지 않는다.
`raw_assets` 가 C001→C009→C011 전 판본에서 바이트 단위로 동일하다는 사실이
`revision_log` 의 각 항목에 `raw_assets_unchanged: true` 로 기록돼 있다.

## 자기 해시

`manifest_self_sha256_excluding_self_field` 는 **자기 자신을 뺀** 매니페스트의 해시다.
자기 해시를 자기 안에 넣으면 고정점 문제가 생기므로 그 한 필드만 제외하고 계산한다.
정규화는 `sort_keys=True` + 최소 구분자로 고정한다 — 들여쓰기·키 순서를 바꿔도 값이 유지된다.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

SELF_HASH_FIELD = "manifest_self_sha256_excluding_self_field"

SELF_HASH_RECIPE = (
    "sha256(json.dumps(manifest_without_self_field, ensure_ascii=False, sort_keys=True, "
    "separators=(',', ':')).encode('utf-8')).hexdigest(), 'sha256:' 접두 부착"
)


class AuthorityManifestError(Exception):
    """A1 권위 매니페스트 판본 계약 위반."""


def canonical_bytes(manifest: dict[str, Any]) -> bytes:
    """자기 해시 필드를 뺀 정규화 바이트열."""
    payload = {k: v for k, v in manifest.items() if k != SELF_HASH_FIELD}
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode(
        "utf-8"
    )


def compute_self_sha256(manifest: dict[str, Any]) -> str:
    return "sha256:" + hashlib.sha256(canonical_bytes(manifest)).hexdigest()


def load(path: Path | str) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def stamp(path: Path | str) -> str:
    """자기 해시를 재계산해 파일에 기록하고 그 값을 돌려준다."""
    path = Path(path)
    manifest = load(path)
    digest = compute_self_sha256(manifest)
    manifest[SELF_HASH_FIELD] = digest
    path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return digest


def verify(path: Path | str) -> dict[str, Any]:
    """판본 선언과 자기 해시를 검증한다. 위반이면 예외를 던진다."""
    path = Path(path)
    manifest = load(path)

    for required in ("manifest_revision", "revised_at", "revision_log", SELF_HASH_FIELD):
        if required not in manifest:
            raise AuthorityManifestError(f"{path.name}: 판본 필드 누락 — {required}")

    revision = manifest["manifest_revision"]
    if not isinstance(revision, int) or revision < 1:
        raise AuthorityManifestError(f"manifest_revision 은 1 이상 정수여야 한다: {revision!r}")

    log = manifest["revision_log"]
    if not isinstance(log, list) or not log:
        raise AuthorityManifestError("revision_log 가 비어 있다")
    revisions = [entry.get("revision") for entry in log]
    if revisions != sorted(revisions) or revisions != list(range(1, len(revisions) + 1)):
        raise AuthorityManifestError(f"revision_log 가 1..N 연속이 아니다: {revisions}")
    if revisions[-1] != revision:
        raise AuthorityManifestError(
            f"manifest_revision({revision}) 과 revision_log 마지막({revisions[-1]}) 이 다르다"
        )
    for entry in log:
        for key in ("revision", "at", "cycle", "commit", "changes", "raw_assets_unchanged"):
            if key not in entry:
                raise AuthorityManifestError(f"revision_log[{entry.get('revision')}]: {key} 누락")

    declared = manifest[SELF_HASH_FIELD]
    actual = compute_self_sha256(manifest)
    if declared != actual:
        raise AuthorityManifestError(
            f"{SELF_HASH_FIELD} 불일치\n  선언: {declared}\n  실제: {actual}"
        )

    return {
        "manifest_revision": revision,
        "revised_at": manifest["revised_at"],
        "revisions_recorded": len(log),
        "self_sha256": actual,
        "raw_assets_declared_unchanged": all(e["raw_assets_unchanged"] for e in log),
    }
