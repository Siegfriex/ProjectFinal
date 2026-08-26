"""observation identity — hash 기반 id 와 symlink-안전 경로 계산.

닫는 결함(Pilot 감사 evidence-filename-collision-overwrite, CRITICAL):
    ``research/refcohort/src/refcohort/collect.py`` 는 한글 record_id 의
    비-ASCII 문자를 ``_`` 로 치환해 파일명을 만들었다. 글자 수가 같은
    서비스명(예: 4글자 한글 서비스명 8개)이 전부 같은 파일명으로 수렴해
    DOM/AX/Screen/Probe 를 상호 덮어썼다 (R2 실측: 41건 중 30건이 6개
    파일명으로 충돌).

    여기서는 표시명을 파일 id 로 절대 쓰지 않는다. observation_id 는
    (service_id, canonical_url, audit_date, protocol_version) 의 해시다.
    표시명은 오직 사람이 읽는 메타데이터(``observations.jsonl``)로만 남는다.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

OBSERVATION_ID_PREFIX = "obs_"
OBSERVATION_ID_HASH_LEN = 20


def observation_id(
    service_id: str, canonical_url: str, audit_date: str, protocol_version: str
) -> str:
    """SSOT 02 §11: "display name 을 file id 로 쓰지 않는다. hash-based observation id"."""
    parts = (service_id, canonical_url, audit_date, protocol_version)
    if any(not p for p in parts):
        raise ValueError(f"observation_id 구성요소는 전부 비어있으면 안 된다: {parts!r}")
    basis = "\x1f".join(parts)
    digest = hashlib.sha256(basis.encode("utf-8")).hexdigest()
    return f"{OBSERVATION_ID_PREFIX}{digest[:OBSERVATION_ID_HASH_LEN]}"


def sha256_bytes(data: bytes) -> str:
    """접두사 없는 소문자 hex 64자 — evidence_manifest.py 규약과 동일하게 맞춘다."""
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


class SymlinkEscapeError(RuntimeError):
    """evidence 쓰기/읽기 경로가 symlink 를 통해 run root 밖으로 나가려 했다."""


def resolve_within(root: Path, *parts: str) -> Path:
    """``root`` 하위 경로만 반환을 허용한다 (symlink escape guard).

    - 후보 경로의 중간 성분 어디에도 symlink 가 있으면 거부한다.
    - 최종 경로의 (아직 존재하지 않을 수 있는) 부모를 realpath 로 풀었을 때
      ``root`` 밖으로 나가면 거부한다.
    """
    if not parts:
        raise ValueError("parts 는 최소 1개 필요하다")
    root_real = root.resolve(strict=True)

    check = root
    for part in parts[:-1]:
        check = check / part
        if check.exists() and check.is_symlink():
            raise SymlinkEscapeError(f"symlink 경로 성분 발견 (evidence 쓰기 거부): {check}")

    candidate = root
    for part in parts:
        candidate = candidate / part

    resolved_parent = candidate.parent.resolve(strict=False)
    try:
        resolved_parent.relative_to(root_real)
    except ValueError as e:
        raise SymlinkEscapeError(
            f"경로가 run root 밖으로 벗어난다: {candidate} (root={root_real})"
        ) from e
    return candidate
