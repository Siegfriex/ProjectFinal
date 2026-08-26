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


# --------------------------------------------------------------------------
# 해시 등재 커버리지 (V2-C008)
#
# 닫는 결함: `a1-raw-payload-files-not-hash-registered-in-authority-manifest` (v1 승계)
#            `EDA00-PROV-UNDECLARED-FILES` (LANE A EDA-00, P2)
#
# LANE A 의 EDA-00 이 실측한 것: `sources/wiseapp` 20파일 중 4개가 **어떤 매니페스트에도**
# sha256 이 없다 — `raw/wiseapp933_api.json`, `raw/wiseapp933_images.json`,
# `source_evidence_manifest.json`(자기해시 필드 자체가 없음), `authority_manifest.json`.
# 그중 `wiseapp933_api.json` 은 `freeze_validity_window.publisher_notice.observed_in` 이
# 근거로 인용하는 파일이다 — 해시 없는 파일이 동결 유효성 주장의 유일한 근거였다.
#
# 네 줄을 채우는 것으로 닫지 않는다. 다음에 파일이 하나 더 생겨도 같은 결함이 다시
# 열리기 때문이다. `hash_registry` 는 **커버리지 규칙**이다: scope 아래 모든 파일이
# 세 갈래 중 하나에 속해야 하고, 세 갈래의 합집합이 실제 파일 집합과 정확히 같아야 한다.
#
#   files                실제 sha256 을 여기에 적는다
#   delegated            해시가 다른 매니페스트에 있다 — 그 위치를 가리킨다 (값을 복제하지 않는다)
#   self_hash_exemption  자기 자신. 파일 해시는 순환이므로 자기해시 앵커로 대체한다
#
# 값을 복제하지 않는 이유: 같은 해시를 두 곳에 적으면 두 개의 진실이 생기고, 갈라졌을 때
# 어느 쪽이 맞는지 판정할 근거가 없어진다. 포인터는 갈라지지 않는다.
# --------------------------------------------------------------------------

REGISTRY_FIELD = "hash_registry"


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return "sha256:" + h.hexdigest()


def _dig(payload: Any, field: str) -> Any:
    """`raw_assets.detail_json.sha256` · `figures[3].sha256` 같은 경로를 따라간다."""
    cursor = payload
    for part in field.split("."):
        if part.endswith("]") and "[" in part:
            name, _, index = part.partition("[")
            if name:
                cursor = cursor[name]
            cursor = cursor[int(index.rstrip("]"))]
        else:
            cursor = cursor[part]
    return cursor


def verify_hash_registry(manifest_path: Path | str, source_root: Path | str) -> dict[str, Any]:
    """`hash_registry` 커버리지와 선언값을 실제 파일에 대고 검증한다.

    Args:
        manifest_path: `sources/wiseapp/authority_manifest.json` 경로.
        source_root: 매니페스트의 경로 표기가 기준으로 삼는 루트
            (`research/landing_accessibility`). 등재 경로는 이 루트 기준 상대경로다.

    Raises:
        AuthorityManifestError: 미등재 파일 · 유령 등재 · 해시 불일치 · 위임 포인터 파손.
    """
    manifest_path = Path(manifest_path)
    root = Path(source_root)
    manifest = load(manifest_path)

    registry = manifest.get(REGISTRY_FIELD)
    if not isinstance(registry, dict):
        raise AuthorityManifestError(f"{REGISTRY_FIELD} 가 없다 — 해시 등재 규칙이 선언되지 않았다")

    scope = root / str(registry["scope_root"])
    if not scope.is_dir():
        raise AuthorityManifestError(f"scope_root 가 디렉터리가 아니다: {scope}")

    present = {
        str(path.relative_to(root)).replace("\\", "/")
        for path in scope.rglob("*")
        if path.is_file()
    }

    files: dict[str, Any] = registry.get("files") or {}
    delegated: list[dict[str, Any]] = registry.get("delegated") or []
    exemption: dict[str, Any] = registry.get("self_hash_exemption") or {}

    # 자기해시 면제는 이 매니페스트 자신에게만 허용된다. 다른 파일을 면제로 빼돌리는 경로를 막는다.
    exempt_path = str(exemption.get("path", ""))
    if exempt_path != str(manifest_path.relative_to(root)).replace("\\", "/"):
        raise AuthorityManifestError(
            f"self_hash_exemption 은 이 매니페스트 자신만 대상으로 한다: {exempt_path!r}"
        )
    if exemption.get("anchor_field") != SELF_HASH_FIELD:
        raise AuthorityManifestError("self_hash_exemption.anchor_field 가 자기해시 필드가 아니다")

    delegated_paths = [str(entry["path"]) for entry in delegated]
    covered_list = [*files, *delegated_paths, exempt_path]
    duplicates = sorted({p for p in covered_list if covered_list.count(p) > 1})
    if duplicates:
        raise AuthorityManifestError(f"한 파일이 두 갈래에 동시에 등재됐다: {duplicates}")

    covered = set(covered_list)
    undeclared = sorted(present - covered)
    if undeclared:
        raise AuthorityManifestError(
            f"{registry['scope_root']} 아래 해시 미선언 파일: {undeclared}\n"
            "  files / delegated / self_hash_exemption 중 하나에 등재하라."
        )
    phantom = sorted(covered - present)
    if phantom:
        raise AuthorityManifestError(f"등재됐으나 실재하지 않는 파일: {phantom}")

    # files — 선언값을 실제 바이트에 대고 확인한다.
    for relpath, record in sorted(files.items()):
        target = root / relpath
        actual = _sha256_file(target)
        if record["sha256"] != actual:
            raise AuthorityManifestError(
                f"{relpath}: sha256 불일치\n  선언: {record['sha256']}\n  실제: {actual}"
            )
        size = target.stat().st_size
        if record["bytes"] != size:
            raise AuthorityManifestError(f"{relpath}: bytes 불일치 {record['bytes']} != {size}")

    # delegated — 포인터가 실재하는 선언을 가리키고, 그 선언이 실제 파일과 맞는지 확인한다.
    cache: dict[str, dict[str, Any]] = {str(manifest_path.relative_to(root)): manifest}
    for entry in delegated:
        holder = str(entry["declared_in"])
        if holder not in cache:
            cache[holder] = load(root / holder)
        try:
            declared = _dig(cache[holder], str(entry["field"]))
        except (KeyError, IndexError, TypeError) as exc:
            raise AuthorityManifestError(
                f"{entry['path']}: 위임 포인터가 끊겼다 — {holder}::{entry['field']} ({exc})"
            ) from exc
        actual = _sha256_file(root / str(entry["path"]))
        if str(declared) != actual:
            raise AuthorityManifestError(
                f"{entry['path']}: 위임된 sha256 불일치 ({holder}::{entry['field']})\n"
                f"  선언: {declared}\n  실제: {actual}"
            )

    return {
        "scope_root": registry["scope_root"],
        "files_present": len(present),
        "declared_directly": len(files),
        "declared_by_delegation": len(delegated),
        "self_hash_exempt": 1,
        "undeclared": 0,
    }
