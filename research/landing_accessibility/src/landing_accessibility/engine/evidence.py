"""Evidence run store — append-only · overwrite 금지 · symlink escape 차단.

`07_EVIDENCE_MANIFEST_CONTRACT` 는 manifest 의 **읽기·검증** 계약을 정의했다
(`landing_accessibility.evidence_manifest`). 이 모듈은 그 계약을 만족하는 run 을
**쓰는** 쪽이며, `02 §12` append-only 와 `02 §14` 실패주입 목록을 코드로 집행한다.

## 무엇을 막는가

| 사고 | 막는 장치 |
|---|---|
| 같은 evidence 를 덮어쓴다 (`02 §12`) | `write_artifact` 가 기존 파일을 만나면 `EvidenceOverwriteError` |
| 같은 `(observation_id, relpath)` 를 두 번 등록 | in-memory 중복 검사 + `07 §4` |
| observation id 가 겹친다 (`02 §14`) | `open_observation` 이 같은 id 를 두 번 열면 실패 |
| symlink 로 run 디렉터리 밖에 쓴다 (`02 §14`) | 경로 성분마다 symlink 검사 + `resolve()` 후 포함관계 확인 |
| 절대경로·`..` relpath (`07 §3`) | `_safe_relpath` |
| manifest 없는 run (`07 §4`) | `seal()` 없이는 run 이 유효하지 않다 |
| run 을 두 번 봉인해 다시 쓴다 | `seal()` 재호출 실패 |

## run 디렉터리 모양

    <root>/<run_id>/
        run.json                     ← run identity + SHADOW provenance (§4.3)
        manifest.jsonl               ← 07 계약. seal() 이 한 번에 쓴다
        <observation_id>/dom.html
        <observation_id>/ax.json
        <observation_id>/screen_initial.png
        ...
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ..evidence_manifest import ManifestEntry, sha256_of, verify_run, write_run_manifest
from .firewall import ExecutionMode, assert_mode_allowed
from .identity import EVIDENCE_SLOTS
from .provenance import ShadowProvenance, utc_now_iso, validate_provenance


class EvidenceError(RuntimeError):
    """evidence run 계약 위반."""


class EvidenceOverwriteError(EvidenceError):
    """`02 §12` — 같은 evidence 를 덮어쓰려 했다."""


class SymlinkEscapeError(EvidenceError):
    """run 디렉터리 밖을 가리키는 경로 — `02 §14` symlink escape."""


class DuplicateObservationError(EvidenceError):
    """`02 §14` — observation id 중복."""


class RunSealedError(EvidenceError):
    """봉인된 run 에 다시 쓰려 했다 — 재수집은 **새 run** 이다 (`02 §12`)."""


class PreregistrationError(EvidenceError):
    """`A2 §1.11.2` 규칙 RC-2 — 재수집 사전선언 계약 위반."""


def _safe_relpath(relpath: str) -> Path:
    """`07 §3` — run 디렉터리 기준 상대경로만. 절대경로·`..` 금지."""
    if not relpath or relpath.startswith("/"):
        raise EvidenceError(f"relpath 는 상대경로여야 한다: {relpath!r}")
    parts = Path(relpath).parts
    if ".." in parts or any(p == "" for p in parts):
        raise EvidenceError(f"relpath 에 상위 이동이 들어 있다: {relpath!r}")
    return Path(relpath)


def _assert_no_symlink_escape(run_dir: Path, target: Path) -> None:
    """경로 성분 하나라도 symlink 면 거부하고, 최종 실경로가 run 안인지 확인한다.

    `resolve()` 만으로 끝내지 않는 이유: `resolve()` 는 symlink 를 **따라간 결과**를 주므로
    "run 안을 가리키는 symlink" 도 통과시킨다. 그러면 다음 수집 때 그 symlink 가
    바깥을 가리키도록 바뀌어도 검증은 계속 통과한다. symlink 자체를 거부해야 한다.
    """
    root = run_dir.resolve()
    cursor = run_dir
    for part in target.relative_to(run_dir).parts:
        cursor = cursor / part
        if cursor.is_symlink():
            raise SymlinkEscapeError(
                f"evidence 경로에 symlink 가 있다: {cursor} → {os.readlink(cursor)} "
                "(02 §14 symlink escape)"
            )
    resolved_parent = target.parent.resolve()
    if not (resolved_parent == root or resolved_parent.is_relative_to(root)):
        raise SymlinkEscapeError(f"evidence 경로가 run 디렉터리 밖을 가리킨다: {resolved_parent}")


@dataclass
class RecollectionPreregistration:
    """`A2 §1.11.2` 규칙 RC-2 — 재수집 **사전선언**.

    이 블록은 그 run 이 산출할 evidence 를 **보기 전에** 동결된다.
    `preregistered_at < collection_started_at` 이 그 순서의 기계적 증거다 (주입 I-25).
    """

    target_criterion_observation_ids: list[str]
    reason_evidence_gap: int
    reason_impact_level: str
    expected_evidence: list[str]
    attempt_index: int
    preregistered_at: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "target_criterion_observation_ids": list(self.target_criterion_observation_ids),
            "reason_evidence_gap": self.reason_evidence_gap,
            "reason_impact_level": self.reason_impact_level,
            "expected_evidence": list(self.expected_evidence),
            "attempt_index": self.attempt_index,
            "preregistered_at": self.preregistered_at,
        }

    def validate(self, *, collection_started_at: str) -> None:
        if self.attempt_index < 1:
            raise PreregistrationError("attempt_index 는 1부터다 (규칙 RC-1 상한 대조용)")
        if not self.expected_evidence:
            raise PreregistrationError(
                "expected_evidence 가 비어 있다 — 무엇의 복구를 기대하는지 적지 않은 "
                "사전선언은 RC-3 의 교체 조건을 자동으로 만족시킨다 (금지 전이 X-14)"
            )
        unknown = [e for e in self.expected_evidence if e not in EVIDENCE_SLOTS]
        if unknown:
            raise PreregistrationError(
                f"expected_evidence 는 A1 §6.2 의 7종 안에서 고른다. 알 수 없는 값: {unknown}"
            )
        if "manifest" in self.expected_evidence:
            raise PreregistrationError(
                "manifest 는 항상 산출되는 산출물이다 — 이것을 expected_evidence 로 적으면 "
                "RC-3 교체 조건을 자동으로 만족시킨다 (금지 전이 X-14)"
            )
        if not self.preregistered_at < collection_started_at:
            raise PreregistrationError(
                f"preregistered_at({self.preregistered_at}) 는 "
                f"collection_started_at({collection_started_at}) 보다 일러야 한다 "
                "— 결과를 본 뒤의 선언은 사전선언이 아니다 (규칙 RC-2 · 주입 I-25)"
            )


#: `A2 §1.11.2` 규칙 RC-1 기본값. P-D(E000_V2) 검증 후 동결한다.
MAX_RECOLLECTION_RUNS_PER_WEB_TARGET = 1


@dataclass
class EvidenceRun:
    """하나의 evidence run. **재수집은 새 run 이며 기존 run 을 덮어쓰지 않는다.**"""

    run_dir: Path
    run_id: str
    execution_mode: ExecutionMode
    provenance: ShadowProvenance = field(default_factory=ShadowProvenance)
    preregistration: RecollectionPreregistration | None = None
    _entries: list[ManifestEntry] = field(default_factory=list, init=False, repr=False)
    _keys: set[tuple[str, str]] = field(default_factory=set, init=False, repr=False)
    _observations: set[str] = field(default_factory=set, init=False, repr=False)
    _sealed: bool = field(default=False, init=False, repr=False)

    @classmethod
    def create(
        cls,
        root: Path | str,
        run_id: str,
        *,
        execution_mode: object,
        execution_scope: object | None = None,
        provenance: ShadowProvenance | None = None,
        preregistration: RecollectionPreregistration | None = None,
    ) -> EvidenceRun:
        mode = assert_mode_allowed(execution_mode, scope=execution_scope)
        run_dir = Path(root) / run_id
        if run_dir.exists():
            raise EvidenceOverwriteError(
                f"run 디렉터리가 이미 있다: {run_dir} — 재수집은 새 run id 를 쓴다 (02 §12)"
            )
        run_dir.mkdir(parents=True)
        return cls(
            run_dir=run_dir,
            run_id=run_id,
            execution_mode=mode,
            provenance=provenance or ShadowProvenance(),
            preregistration=preregistration,
        )

    # ── 관측 ─────────────────────────────────────────────────────────────
    def open_observation(self, observation_id: str) -> None:
        """관측을 연다. 같은 id 를 두 번 열면 실패한다 (`02 §14` duplicate observation id)."""
        if self._sealed:
            raise RunSealedError(f"run {self.run_id} 은 봉인됐다")
        if observation_id in self._observations:
            raise DuplicateObservationError(
                f"observation_id 중복: {observation_id} — "
                "hash 입력이 같다면 같은 관측이며, 다른 관측이라면 hash 입력이 달라야 한다 "
                "(02 §11 · A1 §6.3)"
            )
        self._observations.add(observation_id)

    def write_artifact(self, observation_id: str, relpath: str, data: bytes) -> ManifestEntry:
        """산출물 하나를 쓰고 manifest 항목을 적립한다.

        덮어쓰기·중복 등록·symlink escape 를 전부 여기서 막는다.
        """
        if self._sealed:
            raise RunSealedError(f"run {self.run_id} 은 봉인됐다 — 재수집은 새 run 이다 (02 §12)")
        if observation_id not in self._observations:
            raise EvidenceError(
                f"열리지 않은 관측에 쓰려 했다: {observation_id} (open_observation 먼저)"
            )

        rel = _safe_relpath(relpath)
        key = (observation_id, str(rel))
        if key in self._keys:
            raise EvidenceOverwriteError(
                f"(observation_id, relpath) 중복: {key} (07 §4). "
                "두 screenshot 은 서로 다른 relpath 를 가져야 한다 (A1 §6.2)"
            )

        target = self.run_dir / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        _assert_no_symlink_escape(self.run_dir, target)
        if target.exists() or target.is_symlink():
            raise EvidenceOverwriteError(
                f"이미 존재하는 evidence 를 덮어쓰려 했다: {rel} — "
                "재수집은 새 evidence run 이고, 재판정은 새 judgment version 이다 (02 §12)"
            )

        with open(target, "xb") as fh:
            fh.write(data)

        entry = ManifestEntry(
            observation_id=observation_id,
            relpath=str(rel),
            sha256=sha256_of(target),
            bytes=len(data),
        )
        self._entries.append(entry)
        self._keys.add(key)
        return entry

    # ── 봉인 ─────────────────────────────────────────────────────────────
    def run_record(self) -> dict[str, Any]:
        """run identity — `07` 의 grain 은 run 이며 관측마다 고유하지 않다 (`A1 §6.2`)."""
        record: dict[str, Any] = {
            "run_id": self.run_id,
            "execution_mode": self.execution_mode.value,
            "sealed_at": utc_now_iso(),
            "observations": sorted(self._observations),
            "artifact_count": len(self._entries),
            "provenance": self.provenance.as_dict(),
        }
        if self.preregistration is not None:
            record["recollection_preregistration"] = self.preregistration.as_dict()
        return record

    def seal(self) -> Path:
        """manifest 와 run record 를 쓴다. run 은 이 시점에 유효해진다 (`07 §4`)."""
        if self._sealed:
            raise RunSealedError(f"run {self.run_id} 은 이미 봉인됐다 (append-only, 02 §12)")
        if not self._entries:
            raise EvidenceError(
                f"run {self.run_id} 에 산출물이 없다 — 관측 0건인 run 은 유효하지 않다 (07 §4)"
            )
        record = self.run_record()
        validate_provenance(record["provenance"])
        (self.run_dir / "run.json").write_text(
            json.dumps(record, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        path = write_run_manifest(self.run_dir, self._entries)
        self._sealed = True
        return path

    def verify(self, *, require_files: bool = True) -> dict[str, Any]:
        """`07` 계약으로 자기 자신을 검증한다."""
        return verify_run(self.run_dir, require_files=require_files)


def select_canonical_run(
    runs: list[dict[str, Any]],
    *,
    max_recollection_runs: int = MAX_RECOLLECTION_RUNS_PER_WEB_TARGET,
) -> dict[str, Any]:
    """`A2 §1.11.2` 규칙 RC-3 — 정본 run 선택.

        정본 run = evidence_run_id 순 최초의 measurement_status = MEASURED run
                   단, RC-2 사전선언을 갖춘 재수집 run 이 사전선언한 expected_evidence 를
                   실제로 산출했다면 그 재수집 run 이 정본이 된다.

    **교체 조건은 evidence 의 존재 여부이지 판정 결과가 아니다.** 이 함수는 어떤 인자로도
    `verdict_state` 를 받지 않는다 — 받을 수 없게 만들어야 X-14(optional stopping) 가
    구현 실수로 열리지 않는다.

    각 run dict 는 `evidence_run_id` · `measurement_status` · `attempt_index`(선택) ·
    `preregistration`(선택) · `produced_evidence`(선택) 를 갖는다.
    """
    for run in runs:
        forbidden = {"verdict_state", "final_status", "pass_count", "undetermined_rate"}
        leaked = forbidden & run.keys()
        if leaked:
            raise EvidenceError(
                f"정본 run 선택에 판정 결과가 흘러들었다: {sorted(leaked)} "
                "— 결과를 보고 run 을 고르는 것은 금지 전이 X-14 다"
            )

    measured = [r for r in runs if r.get("measurement_status") == "MEASURED"]
    if not measured:
        raise EvidenceError(
            "measurement_status = MEASURED 인 run 이 없다 — criterion 행 자체가 없다"
        )
    measured.sort(key=lambda r: str(r["evidence_run_id"]))

    for run in measured:
        attempt = int(run.get("attempt_index") or 0)
        if attempt <= 0:
            continue  # 최초 run
        if attempt > max_recollection_runs:
            continue  # RC-1 상한 초과분은 정본이 될 수 없다 (X-14)
        prereg = run.get("preregistration")
        if not prereg:
            continue  # RC-4 미선언 run 은 정본이 아니다
        expected = set(prereg.get("expected_evidence") or ())
        produced = set(run.get("produced_evidence") or ())
        if expected and expected <= produced:
            return run
    return measured[0]
