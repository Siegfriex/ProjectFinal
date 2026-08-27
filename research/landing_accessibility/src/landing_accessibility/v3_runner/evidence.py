"""v3 evidence package 방출 — identity · append-only · manifest 연결 · retention.

`SSOTV3/02 §8` · `SSOTV3/03 §10`.

## 이 모듈이 집행하는 네 가지

| 규약 | 근거 | 코드 장치 |
|---|---|---|
| observation identity = `service_id + task_id + run_id` | `02 §8` | `ObservationKey.observation_id()` |
| display name 을 file id 로 쓰지 않는다 | `02 §8` | 파일경로는 **해시와 고정 slot 이름으로만** 만든다. 표시명은 해시 입력에도, 경로에도 들어가지 않는다 |
| 재수집은 새 run 이고 덮어쓰지 않는다 | `02 §8` | `EvidenceOverwriteError` · `RunSealedError` |
| path manifest ↔ evidence manifest hash 연결 | `02 §8` | `seal()` 이 `run.json` 에 양쪽 sha256 을 함께 적는다 |

## 왜 경로를 해시로만 만드는가

`02 §8` 의 금지는 "표시명을 파일 id 로 쓰지 마라" 다. 표시명을 해시 **입력**에서 빼는 것만으로는
부족하다 — 호출자가 `write_payload(node_id="국민은행 이체")` 처럼 표시명을 node 이름에 넣으면
같은 사고가 파일명에서 재발한다. 그래서 `_validate_token()` 이 공백·경로구분자·제어문자·상위이동을
거부하고, 파일명 자체는 `SLOT_FILENAMES` 의 **닫힌 집합**에서만 나온다.

## screenshot 은 절대 JSON 에 들어가지 않는다

`03 §10` 의 evidence package 는 screenshot 을 포함하지만, 바이너리를 JSON 에 인라인하면
manifest 가 증거 자체가 되어 버려 크기·재검증 비용이 모두 무너진다. 그래서
`write_payload()` 는 screenshot 을 별도 파일로 쓰고 manifest 에는 `relpath + sha256 + bytes`
**포인터만** 남긴다. JSON slot 쪽은 `_assert_no_inlined_binary()` 가 `bytes` 값과
`data:image/...` · `*_b64` 키를 거부해 우회로를 막는다.

## 네트워크 없음

이 모듈은 어떤 네트워크 접근도 하지 않는다. 파일시스템과 해시만 쓴다.
"""

from __future__ import annotations

import hashlib
import json
import unicodedata
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import Any

#: evidence 계약 버전. run.json 에 기록되어 후속 재검증이 무엇을 기대할지 알게 한다.
V3_EVIDENCE_PROTOCOL_VERSION = "v3.0"

#: `engine/identity.py` 와 같은 규약 — URL·id 에 나타날 수 없는 바이트를 필드 구분자로 쓴다.
_FIELD_SEPARATOR = "\x1f"

#: 파일명으로 쓰기에 충분히 짧고 충돌 여지가 없다(`engine/identity.py` 동결값과 동일).
OBSERVATION_ID_HEX_LEN = 32

MANIFEST_FILENAME = "manifest.jsonl"
RUN_RECORD_FILENAME = "run.json"

#: sha256 은 접두사 없는 소문자 hex 64자(레지스트리·evidence manifest 규약과 동일).
_SHA256_HEX_LEN = 64


class EvidenceError(RuntimeError):
    """v3 evidence 계약 위반."""


class EvidenceIdentityError(EvidenceError):
    """observation identity 계약 위반 — `02 §8`."""


class EvidenceOverwriteError(EvidenceError):
    """append-only 위반 — 기존 evidence 를 덮어쓰려 했다 (`02 §8`)."""


class RunSealedError(EvidenceError):
    """봉인된 run 에 다시 쓰려 했다 — 재수집은 **새 run** 이다 (`02 §8`)."""


class InlinedBinaryError(EvidenceError):
    """JSON slot 에 바이너리를 인라인하려 했다 — screenshot 은 포인터로만 남는다."""


class ManifestLinkageError(EvidenceError):
    """path manifest ↔ evidence manifest hash 연결이 끊겼다 (`02 §8`)."""


class RetentionManifestError(EvidenceError):
    """retention manifest 계약 위반."""


class EvidenceSlot(StrEnum):
    """`03 §10` evidence package 구성요소. 이 집합 밖의 slot 은 만들지 않는다."""

    DOM = "dom"
    AX = "ax"
    SCREENSHOT = "screenshot"
    PROBE = "probe"
    URL = "url"
    CONTROL_FACTS = "control_facts"
    #: `T-A-V3-STEP1-006` Δ9 — depth 조건부 토큰의 **귀속 근거**. observation 단위 slot.
    DEPTH_ATTRIBUTION = "depth_attribution"


#: slot → 파일명. 파일명은 이 닫힌 사전에서만 나온다(표시명 유입 경로 차단).
SLOT_FILENAMES: dict[EvidenceSlot, str] = {
    EvidenceSlot.DOM: "dom.html",
    EvidenceSlot.AX: "ax.json",
    EvidenceSlot.SCREENSHOT: "screenshot.png",
    EvidenceSlot.PROBE: "probe.json",
    EvidenceSlot.URL: "url.json",
    EvidenceSlot.CONTROL_FACTS: "control_facts.json",
    EvidenceSlot.DEPTH_ATTRIBUTION: "depth_conditional_tokens.json",
}

#: Δ9 — observation 단위(= state/step 이 아닌) slot 이 놓이는 고정 node.
OBSERVATION_SCOPE_NODE = "observation"

#: JSON 으로 직렬화되는 slot(= screenshot 외 전부).
_JSON_SLOTS: frozenset[EvidenceSlot] = frozenset(
    slot for slot in EvidenceSlot if slot is not EvidenceSlot.SCREENSHOT
)

_FORBIDDEN_TOKEN_CHARS = frozenset({"/", "\\", "\x00", _FIELD_SEPARATOR})


def canonical_json_bytes(payload: Any) -> bytes:
    """manifest·contract hash 가 쓰는 정규 직렬화. 키 정렬 + 공백 없음 + UTF-8."""
    text = json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return text.encode("utf-8")


def sha256_of_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_of_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_of_json(payload: Any) -> str:
    return sha256_of_bytes(canonical_json_bytes(payload))


def _validate_token(value: str, *, field_name: str) -> str:
    """id/노드 토큰 위생 — 표시명이 파일 id 로 새어 들어오는 경로를 막는다 (`02 §8`).

    표시명은 공백을 갖거나 경로구분자·제어문자를 갖는다. 그런 값은 여기서 거부된다.
    통과한 값도 파일명으로 직접 쓰이지는 않는다 — 파일명은 `SLOT_FILENAMES` 에서만 온다.
    """
    if not isinstance(value, str) or not value.strip():
        raise EvidenceIdentityError(f"{field_name} 는 비어 있을 수 없다 (02 §8)")
    text = unicodedata.normalize("NFC", value).strip()
    if text != value:
        raise EvidenceIdentityError(
            f"{field_name} 에 앞뒤 공백/비정규 형태가 있다: {value!r} — id 는 정규화된 값으로 고정한다"
        )
    if any(char.isspace() for char in text):
        raise EvidenceIdentityError(
            f"{field_name} 에 공백이 있다: {value!r} — 표시명이 아니라 machine id 를 써라 (02 §8)"
        )
    if any(char in _FORBIDDEN_TOKEN_CHARS for char in text):
        raise EvidenceIdentityError(f"{field_name} 에 금지문자가 있다: {value!r}")
    if any(ord(char) < 0x20 or ord(char) == 0x7F for char in text):
        raise EvidenceIdentityError(f"{field_name} 에 제어문자가 있다: {value!r}")
    if text in {".", ".."} or text.startswith("."):
        raise EvidenceIdentityError(f"{field_name} 이 경로 특수토큰이다: {value!r}")
    return text


def _validate_sha256(value: str, *, field_name: str) -> str:
    if not isinstance(value, str) or len(value) != _SHA256_HEX_LEN:
        raise EvidenceError(f"{field_name} 은 접두사 없는 소문자 hex 64자여야 한다: {value!r}")
    if value != value.lower() or any(char not in "0123456789abcdef" for char in value):
        raise EvidenceError(f"{field_name} 은 접두사 없는 소문자 hex 64자여야 한다: {value!r}")
    return value


@dataclass(frozen=True)
class ObservationKey:
    """`02 §8` — observation identity 는 이 셋으로만 구성된다.

    service_name 같은 표시명은 입력에 **없다**. 그래서 표시명이 바뀌어도 id 는 안 바뀌고,
    같은 길이의 한글 표시명이 겹쳐도 id 가 겹치지 않는다.
    """

    service_id: str
    task_id: str
    run_id: str

    def canonical_input(self) -> str:
        return _FIELD_SEPARATOR.join(
            (
                _validate_token(self.service_id, field_name="service_id"),
                _validate_token(self.task_id, field_name="task_id"),
                _validate_token(self.run_id, field_name="run_id"),
            )
        )

    def observation_id(self) -> str:
        digest = hashlib.sha256(self.canonical_input().encode("utf-8")).hexdigest()
        return digest[:OBSERVATION_ID_HEX_LEN]

    def as_record(self) -> dict[str, str]:
        return {
            "service_id": self.service_id,
            "task_id": self.task_id,
            "run_id": self.run_id,
            "observation_id": self.observation_id(),
        }


@dataclass(frozen=True)
class EvidenceEntry:
    """manifest 한 줄. 파일 하나를 가리킨다."""

    observation_id: str
    node_id: str
    slot: str
    relpath: str
    sha256: str
    bytes: int

    def as_record(self) -> dict[str, Any]:
        return {
            "observation_id": self.observation_id,
            "node_id": self.node_id,
            "slot": self.slot,
            "relpath": self.relpath,
            "sha256": self.sha256,
            "bytes": self.bytes,
        }


@dataclass(frozen=True)
class EvidencePayload:
    """`03 §10` 이 요구하는 한 state/step 의 evidence package 전체.

    `screenshot` 만 바이너리다. 나머지는 JSON/텍스트로 직렬화된다.
    `screenshot=None` 은 "찍지 못했다" 이고, 빈 바이트로 바꾸지 않는다.
    """

    node_id: str
    url: str
    dom: str
    ax: Mapping[str, Any]
    probe: Mapping[str, Any]
    control_facts: Mapping[str, Any]
    screenshot: bytes | None = None


@dataclass(frozen=True)
class SealResult:
    """봉인 결과 — path manifest 와 evidence manifest 를 잇는 hash 쌍."""

    observation_id: str
    run_dir: Path
    entry_count: int
    evidence_manifest_sha256: str
    path_manifest_sha256: str


def _assert_no_inlined_binary(payload: Any, *, slot: EvidenceSlot, path: str = "$") -> None:
    """JSON slot 에 바이너리/base64 이미지가 인라인되는 것을 막는다.

    `03 §10` 은 screenshot 을 evidence package 에 넣으라고 하지, JSON 에 넣으라고 하지 않는다.
    포인터 규약을 우회하는 두 경로(raw `bytes`, base64 문자열)를 여기서 함께 막는다.
    """
    if isinstance(payload, bytes | bytearray | memoryview):
        raise InlinedBinaryError(
            f"{slot.value} slot {path} 에 바이너리가 들어 있다 — screenshot 은 포인터로만 남긴다"
        )
    if isinstance(payload, str):
        if payload.startswith("data:image/") or payload.startswith("data:application/octet-stream"):
            raise InlinedBinaryError(
                f"{slot.value} slot {path} 에 data URI 가 인라인됐다 — 포인터 + sha256 만 남긴다"
            )
        return
    if isinstance(payload, Mapping):
        for key, value in payload.items():
            key_text = str(key)
            if key_text.endswith(("_b64", "_base64", "_bytes")):
                raise InlinedBinaryError(
                    f"{slot.value} slot {path}.{key_text} 는 인라인 바이너리 키다 — 포인터만 남긴다"
                )
            _assert_no_inlined_binary(value, slot=slot, path=f"{path}.{key_text}")
        return
    if isinstance(payload, list | tuple):
        for index, value in enumerate(payload):
            _assert_no_inlined_binary(value, slot=slot, path=f"{path}[{index}]")


class EvidenceRunWriter:
    """한 observation(`service_id+task_id+run_id`) 의 evidence run 을 쓴다.

    run 디렉터리 모양::

        <root>/<observation_id>/
            run.json                      ← identity + 양쪽 manifest sha256 (seal 이 마지막에 쓴다)
            manifest.jsonl                ← evidence manifest. seal 이 한 번에 쓴다
            <node_id>/dom.html
            <node_id>/ax.json
            <node_id>/screenshot.png
            ...

    `run.json` 이 manifest 목록에 들어가지 않는 이유는 순환 때문이다 —
    `evidence_manifest_sha256` 은 `manifest.jsonl` 의 해시이고, `run.json` 이 그 값을 담는다.
    """

    def __init__(self, root: Path, key: ObservationKey) -> None:
        self._root = Path(root)
        self._key = key
        self._observation_id = key.observation_id()
        self._run_dir = self._root / self._observation_id
        self._entries: list[EvidenceEntry] = []
        self._seen: set[tuple[str, str]] = set()
        self._opened = False
        self._sealed = False

    @property
    def observation_id(self) -> str:
        return self._observation_id

    @property
    def run_dir(self) -> Path:
        return self._run_dir

    @property
    def entries(self) -> tuple[EvidenceEntry, ...]:
        return tuple(self._entries)

    def open(self) -> EvidenceRunWriter:
        """run 디렉터리를 만든다. 이미 있으면 거부한다 — 재수집은 **새 run_id** 다 (`02 §8`)."""
        if self._opened:
            raise EvidenceError("이미 열린 run 이다")
        if self._run_dir.exists():
            raise EvidenceOverwriteError(
                f"observation {self._observation_id} 의 run 이 이미 있다 "
                f"({self._run_dir}) — 재수집은 새 run_id 로 한다 (02 §8)"
            )
        self._run_dir.mkdir(parents=True, exist_ok=False)
        self._opened = True
        return self

    def __enter__(self) -> EvidenceRunWriter:
        return self.open()

    def __exit__(self, *exc: object) -> None:
        return None

    def _assert_writable(self) -> None:
        if not self._opened:
            raise EvidenceError("open() 하지 않은 run 에 쓸 수 없다")
        if self._sealed:
            raise RunSealedError("봉인된 run 이다 — 재수집은 새 run 이다 (02 §8)")

    def _write_slot(self, node_id: str, slot: EvidenceSlot, data: bytes) -> EvidenceEntry:
        self._assert_writable()
        node = _validate_token(node_id, field_name="node_id")
        relpath = f"{node}/{SLOT_FILENAMES[slot]}"
        if (node, slot.value) in self._seen:
            raise EvidenceOverwriteError(f"{relpath} 를 두 번 등록하려 했다 (02 §8 append-only)")
        target = self._run_dir / node / SLOT_FILENAMES[slot]
        if target.exists():
            raise EvidenceOverwriteError(f"{relpath} 가 이미 있다 — 덮어쓰지 않는다 (02 §8)")
        target.parent.mkdir(parents=True, exist_ok=True)
        # "x" 모드 — 경합에서도 기존 파일을 건드리지 않는다.
        with target.open("xb") as handle:
            handle.write(data)
        entry = EvidenceEntry(
            observation_id=self._observation_id,
            node_id=node,
            slot=slot.value,
            relpath=relpath,
            sha256=sha256_of_bytes(data),
            bytes=len(data),
        )
        self._entries.append(entry)
        self._seen.add((node, slot.value))
        return entry

    def write_json_slot(self, node_id: str, slot: EvidenceSlot, payload: Any) -> EvidenceEntry:
        if slot not in _JSON_SLOTS:
            raise EvidenceError(f"{slot.value} 는 JSON slot 이 아니다 — write_screenshot 을 써라")
        _assert_no_inlined_binary(payload, slot=slot)
        return self._write_slot(node_id, slot, canonical_json_bytes(payload))

    def write_text_slot(self, node_id: str, slot: EvidenceSlot, text: str) -> EvidenceEntry:
        if slot is not EvidenceSlot.DOM:
            raise EvidenceError(f"{slot.value} 는 텍스트 slot 이 아니다")
        return self._write_slot(node_id, slot, text.encode("utf-8"))

    def write_screenshot(self, node_id: str, data: bytes) -> EvidenceEntry:
        """screenshot 은 바이너리 파일로만 저장하고 manifest 에는 포인터+sha256 만 남는다."""
        if not isinstance(data, bytes | bytearray):
            raise EvidenceError("screenshot 은 bytes 여야 한다")
        return self._write_slot(node_id, EvidenceSlot.SCREENSHOT, bytes(data))

    def write_payload(self, payload: EvidencePayload) -> tuple[EvidenceEntry, ...]:
        """`03 §10` 한 state/step 분 evidence package 를 통째로 쓴다."""
        written = [
            self.write_text_slot(payload.node_id, EvidenceSlot.DOM, payload.dom),
            self.write_json_slot(payload.node_id, EvidenceSlot.AX, dict(payload.ax)),
            self.write_json_slot(payload.node_id, EvidenceSlot.PROBE, dict(payload.probe)),
            self.write_json_slot(payload.node_id, EvidenceSlot.URL, {"url": payload.url}),
            self.write_json_slot(
                payload.node_id, EvidenceSlot.CONTROL_FACTS, dict(payload.control_facts)
            ),
        ]
        if payload.screenshot is not None:
            written.append(self.write_screenshot(payload.node_id, payload.screenshot))
        return tuple(written)

    def seal(self, *, path_manifest_sha256: str) -> SealResult:
        """manifest.jsonl 을 쓰고 `run.json` 으로 path manifest 와 hash 연결한다 (`02 §8`)."""
        self._assert_writable()
        _validate_sha256(path_manifest_sha256, field_name="path_manifest_sha256")
        manifest_path = self._run_dir / MANIFEST_FILENAME
        if manifest_path.exists():
            raise EvidenceOverwriteError(f"{MANIFEST_FILENAME} 이 이미 있다 (02 §8)")
        lines = [
            json.dumps(entry.as_record(), sort_keys=True, ensure_ascii=False, separators=(",", ":"))
            for entry in sorted(self._entries, key=lambda e: (e.node_id, e.slot))
        ]
        body = ("\n".join(lines) + "\n") if lines else ""
        manifest_bytes = body.encode("utf-8")
        with manifest_path.open("xb") as handle:
            handle.write(manifest_bytes)
        evidence_manifest_sha256 = sha256_of_bytes(manifest_bytes)

        run_record = {
            "protocol_version": V3_EVIDENCE_PROTOCOL_VERSION,
            **self._key.as_record(),
            "entry_count": len(self._entries),
            "evidence_manifest_sha256": evidence_manifest_sha256,
            "path_manifest_sha256": path_manifest_sha256,
        }
        run_path = self._run_dir / RUN_RECORD_FILENAME
        with run_path.open("xb") as handle:
            handle.write(canonical_json_bytes(run_record))
        self._sealed = True
        return SealResult(
            observation_id=self._observation_id,
            run_dir=self._run_dir,
            entry_count=len(self._entries),
            evidence_manifest_sha256=evidence_manifest_sha256,
            path_manifest_sha256=path_manifest_sha256,
        )


def load_run_record(run_dir: Path) -> dict[str, Any]:
    run_path = Path(run_dir) / RUN_RECORD_FILENAME
    if not run_path.is_file():
        raise ManifestLinkageError(f"{RUN_RECORD_FILENAME} 이 없다 — 봉인되지 않은 run 은 무효다")
    record = json.loads(run_path.read_text(encoding="utf-8"))
    if not isinstance(record, dict):
        raise ManifestLinkageError(f"{RUN_RECORD_FILENAME} 형식 오류")
    return record


def load_evidence_manifest(run_dir: Path) -> list[EvidenceEntry]:
    manifest_path = Path(run_dir) / MANIFEST_FILENAME
    if not manifest_path.is_file():
        raise ManifestLinkageError(f"{MANIFEST_FILENAME} 이 없다 — 그 run 은 유효하지 않다")
    entries: list[EvidenceEntry] = []
    for line_no, line in enumerate(manifest_path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        record = json.loads(line)
        missing = {"observation_id", "node_id", "slot", "relpath", "sha256", "bytes"} - set(record)
        if missing:
            raise ManifestLinkageError(
                f"{MANIFEST_FILENAME}:{line_no} 필수 필드 누락 {sorted(missing)}"
            )
        entries.append(
            EvidenceEntry(
                observation_id=record["observation_id"],
                node_id=record["node_id"],
                slot=record["slot"],
                relpath=record["relpath"],
                sha256=record["sha256"],
                bytes=int(record["bytes"]),
            )
        )
    return entries


def verify_manifest_linkage(run_dir: Path, *, path_manifest_bytes: bytes) -> dict[str, Any]:
    """`02 §8` — path manifest 와 evidence manifest 가 hash 로 이어져 있는지 확인한다.

    양방향으로 본다: `run.json` 이 적어 둔 evidence manifest 해시가 실제 `manifest.jsonl`
    해시와 같은지, 그리고 적어 둔 path manifest 해시가 손에 든 path manifest 바이트와 같은지.
    한쪽만 보면 manifest 를 통째로 갈아끼운 사고를 놓친다.
    """
    run_dir = Path(run_dir)
    record = load_run_record(run_dir)
    actual_evidence_sha = sha256_of_file(run_dir / MANIFEST_FILENAME)
    if record.get("evidence_manifest_sha256") != actual_evidence_sha:
        raise ManifestLinkageError(
            "evidence manifest 해시가 run.json 기록과 다르다 — manifest 가 교체됐다"
        )
    actual_path_sha = sha256_of_bytes(path_manifest_bytes)
    if record.get("path_manifest_sha256") != actual_path_sha:
        raise ManifestLinkageError(
            "path manifest 해시가 run.json 기록과 다르다 — frozen path 가 교체됐다"
        )
    return {
        "observation_id": record.get("observation_id"),
        "evidence_manifest_sha256": actual_evidence_sha,
        "path_manifest_sha256": actual_path_sha,
        "linked": True,
    }


def verify_evidence_run(run_dir: Path) -> dict[str, Any]:
    """manifest 를 기준선으로 로컬 파일 바이트를 대조한다. 재현은 못 해도 위조는 잡힌다."""
    run_dir = Path(run_dir)
    entries = load_evidence_manifest(run_dir)
    verified: list[str] = []
    mismatched: list[str] = []
    missing: list[str] = []
    for entry in entries:
        target = run_dir / entry.relpath
        if not target.is_file():
            missing.append(entry.relpath)
            continue
        if sha256_of_file(target) == entry.sha256 and target.stat().st_size == entry.bytes:
            verified.append(entry.relpath)
        else:
            mismatched.append(entry.relpath)
    return {
        "entry_count": len(entries),
        "verified": sorted(verified),
        "mismatched": sorted(mismatched),
        "missing": sorted(missing),
        "ok": not mismatched and not missing,
    }


# ---------------------------------------------------------------------------
# retention manifest — `handoff/ARTIFACT_RETENTION_MANIFEST_E001.json` 형식 승계
# ---------------------------------------------------------------------------


@dataclass
class _RootScan:
    files: list[dict[str, Any]] = field(default_factory=list)
    total_bytes: int = 0


def _scan_root(root: Path, base: Path) -> _RootScan:
    scan = _RootScan()
    for path in sorted(root.rglob("*")):
        if path.is_symlink():
            raise RetentionManifestError(
                f"retention root 안에 symlink 가 있다: {path} — 바이트 대조를 신뢰할 수 없다"
            )
        if not path.is_file():
            continue
        size = path.stat().st_size
        scan.files.append(
            {
                "path": path.relative_to(base).as_posix(),
                "bytes": size,
                "sha256": sha256_of_file(path),
            }
        )
        scan.total_bytes += size
    return scan


def _aggregate_sha256(files: Iterable[Mapping[str, Any]]) -> str:
    """root 단위 집계 해시. 파일 하나만 바뀌어도 값이 바뀐다.

    입력은 `path\\x1fsha256\\n` 을 path 정렬 순으로 이은 것이다 — 경로를 넣어야
    "같은 내용 파일 두 개의 이름이 서로 바뀐" 사고까지 잡힌다.
    """
    digest = hashlib.sha256()
    for record in sorted(files, key=lambda item: str(item["path"])):
        digest.update(f"{record['path']}{_FIELD_SEPARATOR}{record['sha256']}\n".encode())
    return digest.hexdigest()


def build_retention_manifest(
    *,
    manifest_id: str,
    producer: str,
    producer_sha: str,
    roots: Sequence[Path],
    base: Path,
    read_only: bool = True,
) -> dict[str, Any]:
    """파일별 sha256 + bytes 를 가진 retention manifest 를 만든다.

    `base` 는 `path` 를 상대화할 기준(보통 repo root)이다. 절대경로를 그대로 적으면
    다른 clone 에서 대조가 불가능해진다.
    """
    base = Path(base).resolve()
    root_records: list[dict[str, Any]] = []
    for root in roots:
        root_path = Path(root).resolve()
        if not root_path.is_dir():
            raise RetentionManifestError(f"retention root 가 디렉터리가 아니다: {root_path}")
        scan = _scan_root(root_path, base)
        root_records.append(
            {
                "root": root_path.relative_to(base).as_posix(),
                "artifact_count": len(scan.files),
                "bytes": scan.total_bytes,
                "aggregate_sha256": _aggregate_sha256(scan.files),
                "files": scan.files,
            }
        )
    return {
        "manifest_id": manifest_id,
        "producer": producer,
        "producer_sha": producer_sha,
        "read_only": read_only,
        "protocol_version": V3_EVIDENCE_PROTOCOL_VERSION,
        "roots": root_records,
    }


def verify_retention_manifest(manifest: Mapping[str, Any], *, base: Path) -> dict[str, Any]:
    """retention manifest 의 sha256 이 실제 파일과 일치하는지 재계산으로 확인한다."""
    base = Path(base).resolve()
    verified: list[str] = []
    mismatched: list[str] = []
    missing: list[str] = []
    aggregate_mismatched: list[str] = []
    for root_record in manifest.get("roots", []):
        for file_record in root_record.get("files", []):
            target = base / str(file_record["path"])
            if not target.is_file():
                missing.append(str(file_record["path"]))
                continue
            if (
                sha256_of_file(target) == file_record["sha256"]
                and target.stat().st_size == file_record["bytes"]
            ):
                verified.append(str(file_record["path"]))
            else:
                mismatched.append(str(file_record["path"]))
        recomputed = _aggregate_sha256(root_record.get("files", []))
        if recomputed != root_record.get("aggregate_sha256"):
            aggregate_mismatched.append(str(root_record.get("root")))
    return {
        "verified": sorted(verified),
        "mismatched": sorted(mismatched),
        "missing": sorted(missing),
        "aggregate_mismatched": sorted(aggregate_mismatched),
        "ok": not mismatched and not missing and not aggregate_mismatched,
    }


# ---------------------------------------------------------------------------
# R6-Q8 — `AUTH_GATE` / `ABSTAIN` 층 한정 (A `T-A-V3-STEP1-003`)
# ---------------------------------------------------------------------------

#: 두 값은 `04 §2` action token 층과 `04 §4` endpoint_status 층에 **같은 문자열로** 존재한다.
#: codebook 을 고치는 대신 "값만 단독으로 쓰지 않는다" 를 필드 한정으로 의무화했다.
LAYER_AMBIGUOUS_VALUES: frozenset[str] = frozenset({"AUTH_GATE", "ABSTAIN"})

#: 이 값들을 담을 수 있는 유일한 키. 컬럼명이 층을 말해야 한다.
LAYER_QUALIFYING_KEYS: frozenset[str] = frozenset({"endpoint_status", "action_token"})


class LayerQualificationError(EvidenceError):
    """`AUTH_GATE`/`ABSTAIN` 이 층 표시 없이 단독으로 등장했다 — C GATE 3 finding 대상."""


def qualified_layer_text(key: str, value: str) -> str:
    """로그 문자열용 — 값만 적지 않고 `endpoint_status=AUTH_GATE` 처럼 층을 붙여 적는다."""
    if key not in LAYER_QUALIFYING_KEYS:
        raise LayerQualificationError(
            f"{key!r} 는 층 한정 키가 아니다 — {sorted(LAYER_QUALIFYING_KEYS)} 중 하나여야 한다"
        )
    return f"{key}={value}"


def assert_layer_qualified(payload: Any, *, path: str = "$") -> None:
    """산출 record 전체를 훑어 층 표시 없는 `AUTH_GATE`/`ABSTAIN` 을 거부한다.

    JSON 키·mart 컬럼명·로그 문자열 전부에 같은 규칙을 적용한다. 검사 대상은 **값이 놓인 키**다 —
    값만 담긴 컬럼이 있으면 그 컬럼명이 층을 말해야 하고, 말하지 않으면 여기서 걸린다.
    """
    if isinstance(payload, Mapping):
        for key, value in payload.items():
            key_text = str(key)
            if isinstance(value, str) and value in LAYER_AMBIGUOUS_VALUES:
                if key_text not in LAYER_QUALIFYING_KEYS:
                    raise LayerQualificationError(
                        f"{path}.{key_text} 에 층 표시 없는 {value!r} 가 있다 "
                        f"— {sorted(LAYER_QUALIFYING_KEYS)} 중 하나를 컬럼명으로 써라 (R6-Q8)"
                    )
                continue
            assert_layer_qualified(value, path=f"{path}.{key_text}")
        return
    if isinstance(payload, list | tuple):
        for index, value in enumerate(payload):
            if isinstance(value, str) and value in LAYER_AMBIGUOUS_VALUES:
                raise LayerQualificationError(
                    f"{path}[{index}] 에 층 표시 없는 {value!r} 가 있다 (R6-Q8)"
                )
            assert_layer_qualified(value, path=f"{path}[{index}]")
        return
    if isinstance(payload, str) and payload in LAYER_AMBIGUOUS_VALUES:
        raise LayerQualificationError(f"{path} 에 층 표시 없는 {payload!r} 가 있다 (R6-Q8)")


# ---------------------------------------------------------------------------
# R7 — 요약값이 원자료를 덮지 않는다
# ---------------------------------------------------------------------------

#: `entry_zone` 은 요약값이다. `04 §6` — 정규화 좌표 원자료를 버리지 않는다.
ZONE_SUMMARY_KEY = "entry_zone"
ZONE_RAW_KEYS: tuple[str, str] = ("entry_x_norm", "entry_y_norm")

#: W5C 의 structural override 가 좌표와 무관하게 zone 을 확정하는 두 값.
STRUCTURAL_OVERRIDE_ZONES: frozenset[str] = frozenset({"FLOATING", "DRAWER"})


class CoordinateDropError(EvidenceError):
    """`entry_zone` 만 남고 정규화 좌표가 사라졌다 — `04 §6` · R7 위반."""


def assert_coordinates_preserved(payload: Any, *, path: str = "$") -> None:
    """`entry_zone` 이 있는 모든 record 는 `entry_x_norm`/`entry_y_norm` 을 함께 가져야 한다.

    `FLOATING`/`DRAWER` structural override 가 걸려도 마찬가지다 — override 는 zone 을
    결정할 뿐 좌표를 무효화하지 않는다. 좌표가 `None` 인 것은 "관측 못 했다" 이므로
    키 자체가 없는 것과 구분해서 허용한다.
    """
    if isinstance(payload, Mapping):
        if ZONE_SUMMARY_KEY in payload and payload[ZONE_SUMMARY_KEY] is not None:
            missing = [key for key in ZONE_RAW_KEYS if key not in payload]
            if missing:
                raise CoordinateDropError(
                    f"{path} 에 {ZONE_SUMMARY_KEY}={payload[ZONE_SUMMARY_KEY]!r} 가 있는데 "
                    f"{missing} 가 없다 — 요약값이 원자료를 덮었다 (04 §6 · R7)"
                )
        for key, value in payload.items():
            assert_coordinates_preserved(value, path=f"{path}.{key}")
        return
    if isinstance(payload, list | tuple):
        for index, value in enumerate(payload):
            assert_coordinates_preserved(value, path=f"{path}[{index}]")


# ---------------------------------------------------------------------------
# R3 / R2 / R4 — task_role 필터 · 두 분모 · 분모 사슬
# ---------------------------------------------------------------------------

#: `R3` — 본표본 n 은 PRIMARY 만 센다. F1 은행의 잔액조회 secondary 가 n 을 늘리지 않게.
TASK_ROLE_PRIMARY = "PRIMARY"
TASK_ROLE_VALUES: frozenset[str] = frozenset({TASK_ROLE_PRIMARY, "SECONDARY_REPEATED"})

#: 집계 산출물에 실리는 **필터 조건 문자열**. "적용했다"는 주장이 아니라 조건 자체를 남긴다.
PRIMARY_TASK_FILTER_EXPR = "task_role == 'PRIMARY'"

#: `R2` — 두 분모. 섞으면 selection 이 생긴다.
DENOMINATOR_EVIDENCE_BEARING = "evidence_bearing_n"
DENOMINATOR_FLOW_EVALUABLE = "flow_evaluable_n"

#: 진입 flow 지표. `AUTH_GATE` 여부와 무관하게 산출된다 — 여기서 AUTH_GATE target 을 빼면
#: "인증이 일찍 걸리는 서비스" 가 진입구조 분석에서 조용히 사라진다.
ENTRY_FLOW_METRICS: frozenset[str] = frozenset(
    {
        "entry_x_norm",
        "entry_y_norm",
        "entry_zone",
        "entry_control_type",
        "entry_label_modality",
        "visible_label_text",
        "accessible_name",
        "accessible_name_source",
        "label_relation",
        "nav_container_type",
        "reveal_direction",
        "nav_container_depth",
        "menu_dependency",
        "auth_gate_stage",
        "s0_task_control_visible",
        "first_visible_scroll_state",
    }
)

#: endpoint 도달 여부에 의존하는 지표만 flow-evaluable 을 분모로 쓴다.
ENDPOINT_DEPENDENT_METRICS: frozenset[str] = frozenset(
    {
        "endpoint_reach_rate",
        "endpoint_status",
        "activation_depth",
        "flow_step_count",
        "task_flow_sequence",
        "experienced_flow_sequence",
    }
)


class DenominatorError(EvidenceError):
    """분모 사슬 계약 위반 — `05 §6` · R2 · R4."""


def denominator_for_metric(metric: str) -> str:
    """지표별 분모를 사전등록된 표에서만 고른다. 모르는 지표는 조용한 기본값 대신 거부다."""
    if metric in ENTRY_FLOW_METRICS:
        return DENOMINATOR_EVIDENCE_BEARING
    if metric in ENDPOINT_DEPENDENT_METRICS:
        return DENOMINATOR_FLOW_EVALUABLE
    raise DenominatorError(
        f"{metric!r} 의 분모가 사전등록되어 있지 않다 — 임의 분모를 고르지 않는다 (R2)"
    )


@dataclass(frozen=True)
class Replacement:
    """`R4` — 교체 1건의 전체 provenance. 다섯 필드 중 하나라도 비면 기록이 아니다."""

    excluded_target_id: str
    reason: str
    reserve_rank: int
    decided_at: str
    decided_by: str

    def as_record(self) -> dict[str, Any]:
        return {
            "excluded_target_id": self.excluded_target_id,
            "reason": self.reason,
            "reserve_rank": self.reserve_rank,
            "decided_at": self.decided_at,
            "decided_by": self.decided_by,
        }


@dataclass(frozen=True)
class ReplacementLedger:
    """precheck 단계에서 동결되는 교체 원장.

    교체는 precheck 에서만 가능하므로 이 원장은 `attempted` **이전에** 동결된다.
    그 시점 규약을 문장이 아니라 해시로 집행한다 — 분모 사슬이 이 원장의 sha256 을
    싣고 있으므로, attempted 이후에 교체 한 건을 끼워 넣으면 사슬 검증이 깨진다.
    """

    family_id: str
    frozen_at: str
    replacements: tuple[Replacement, ...] = ()

    def as_record(self) -> dict[str, Any]:
        return {
            "family_id": self.family_id,
            "frozen_at": self.frozen_at,
            # k=0 이어도 0 을 명시한다 — 필드 부재와 0 이 같아 보이면 안 된다 (R4)
            "replaced_count": len(self.replacements),
            "replacements": [item.as_record() for item in self.replacements],
        }

    def sha256(self) -> str:
        return sha256_of_json(self.as_record())


def build_denominator_chain(
    *,
    family_id: str,
    candidate_target_ids: Sequence[str],
    ledger: ReplacementLedger,
    frozen_target_ids: Sequence[str],
    attempted_target_ids: Sequence[str],
    evidence_bearing_target_ids: Sequence[str],
    flow_evaluable_target_ids: Sequence[str],
    task_role_filter: str = PRIMARY_TASK_FILTER_EXPR,
) -> dict[str, Any]:
    """`05 §6` 분모 사슬을 교체 이력이 보이는 형태로 낸다.

        candidate 10 → [replaced k, 사유별 내역] → eligible/frozen 10 → attempted n
                     → evidence-bearing n → flow-evaluable n

    `AUTH_GATE` 는 evidence-bearing 에 **포함**된다. 진입 flow 지표는 flow-evaluable 이
    아니라 evidence-bearing 을 분모로 쓴다 (R2).
    """
    if ledger.family_id != family_id:
        raise DenominatorError(
            f"원장 family_id({ledger.family_id}) 가 사슬 family_id({family_id}) 와 다르다"
        )
    evidence_bearing = set(evidence_bearing_target_ids)
    flow_evaluable = set(flow_evaluable_target_ids)
    if not flow_evaluable <= evidence_bearing:
        raise DenominatorError(
            "flow-evaluable 이 evidence-bearing 의 부분집합이 아니다 — 두 분모가 섞였다 (R2)"
        )
    if not evidence_bearing <= set(attempted_target_ids):
        raise DenominatorError("evidence-bearing 이 attempted 의 부분집합이 아니다")
    return {
        "family_id": family_id,
        "applied_filter": task_role_filter,
        "replacement_ledger_sha256": ledger.sha256(),
        "replacement_ledger": ledger.as_record(),
        "chain": [
            {
                "stage": "candidate",
                "n": len(candidate_target_ids),
                "target_ids": list(candidate_target_ids),
            },
            {
                "stage": "replaced",
                "n": len(ledger.replacements),
                "detail": [item.as_record() for item in ledger.replacements],
            },
            {
                "stage": "eligible_frozen",
                "n": len(frozen_target_ids),
                "target_ids": list(frozen_target_ids),
            },
            {
                "stage": "attempted",
                "n": len(attempted_target_ids),
                "target_ids": list(attempted_target_ids),
            },
            {
                "stage": "evidence_bearing",
                "n": len(evidence_bearing),
                "target_ids": sorted(evidence_bearing),
                "note": "endpoint_status=AUTH_GATE 인 target 도 여기에 포함된다 (R2)",
            },
            {
                "stage": "flow_evaluable",
                "n": len(flow_evaluable),
                "target_ids": sorted(flow_evaluable),
                "note": "endpoint 의존 지표만 이 분모를 쓴다 (R2)",
            },
        ],
        "denominator_assignment": {
            DENOMINATOR_EVIDENCE_BEARING: sorted(ENTRY_FLOW_METRICS),
            DENOMINATOR_FLOW_EVALUABLE: sorted(ENDPOINT_DEPENDENT_METRICS),
        },
    }


def verify_denominator_chain(
    chain: Mapping[str, Any], *, ledger: ReplacementLedger
) -> dict[str, Any]:
    """attempted 이후 교체가 끼어들었는지 해시로 확인한다 (R4)."""
    recomputed = ledger.sha256()
    linked = chain.get("replacement_ledger_sha256") == recomputed
    if not linked:
        raise DenominatorError(
            "교체 원장 해시가 분모 사슬 기록과 다르다 — attempted 이후 교체가 끼어들었다 (R4)"
        )
    return {
        "family_id": chain.get("family_id"),
        "replacement_ledger_sha256": recomputed,
        "linked": True,
    }


# ---------------------------------------------------------------------------
# Δ9 (`T-A-V3-STEP1-006`) — depth 조건부 토큰의 귀속 근거를 raw 로 보존한다
# ---------------------------------------------------------------------------

#: `SELECT_ORIGIN`/`SELECT_DESTINATION`/`SELECT_DATE` 의 `activation_depth` 포함 여부를
#: 가르는 입력수단. `MIXED` 인 control 은 **실제 사용된 수단**으로 판정한다.
INPUT_MODE_VALUES: frozenset[str] = frozenset({"DROPDOWN", "MAP_PAN", "FREE_TEXT", "MIXED"})

#: 조건부 귀속 record 한 건이 반드시 갖는 필드. `included` 는 W5B 의 판정 자리다.
DEPTH_ATTRIBUTION_FIELDS: frozenset[str] = frozenset(
    {"action_token", "step_index", "input_mode", "included"}
)


class DepthAttributionEvidenceError(EvidenceError):
    """Δ9 — 조건부 토큰의 귀속 근거가 빠졌다."""


def assert_depth_attribution_evidenced(records: Sequence[Mapping[str, Any]]) -> None:
    """ "판정했다" 가 아니라 "무엇을 근거로 어떻게 판정했다" 가 남았는지 본다.

    `included` 가 `None` 인 것은 결함이 아니다 — W5B 경계가 아직 안 붙었다는 뜻이며,
    `09 D3-05` 대로 불능은 `None` 이다. 결함인 것은 **근거(`input_mode`)가 없는데
    포함/제외 판정만 있는** 상태다. 그건 판정을 재검증할 수 없게 만든다.
    """
    for index, record in enumerate(records):
        missing = DEPTH_ATTRIBUTION_FIELDS - set(record)
        if missing:
            raise DepthAttributionEvidenceError(
                f"depth_conditional_tokens[{index}] 필수 필드 누락 {sorted(missing)} (Δ9)"
            )
        mode = record["input_mode"]
        if mode is not None and mode not in INPUT_MODE_VALUES:
            raise DepthAttributionEvidenceError(
                f"depth_conditional_tokens[{index}].input_mode 가 Δ9 어휘 밖이다: {mode!r}"
            )
        if record["included"] is not None and mode is None:
            raise DepthAttributionEvidenceError(
                f"depth_conditional_tokens[{index}] 는 근거(input_mode) 없이 "
                f"included={record['included']!r} 만 갖고 있다 — 재검증이 불가능하다 (Δ9)"
            )
