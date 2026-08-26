"""append-only 를 실제로 강제하는 evidence 쓰기 계층.

``landing_accessibility.evidence_manifest`` (``docs/07_EVIDENCE_MANIFEST_CONTRACT.md``) 는
manifest 의 **형식**(observation_id/relpath/sha256/bytes)과 **사후 검증**
(``verify_run``)을 계약한다. 그러나 "수집 도중 이전 관측을 덮어쓰지 못하게
막는 것" 자체는 그 계약의 책임이 아니다(§5 "이 계약이 하지 않는 것").

이 모듈이 그 빠진 조각이다.

닫는 결함(Pilot 감사 append-only-not-enforced, MEDIUM):
    ``research/refcohort/src/refcohort/guard.py:168`` 의 ``check_append_only``
    는 정의만 되고 **어디서도 호출되지 않았다**
    (``grep -rn check_append_only`` 결과 정의부 1줄뿐). ``pipeline.py`` 의
    ``run_batch`` 는 ``records.jsonl`` 을 ``'w'`` 모드로 열어 같은 run_id 를
    재실행하면 이전 레코드와 증거 파일을 그냥 덮어썼다.

    여기서는 가드를 "나중에 부를 수도 있는 함수"로 두지 않는다.
    ``GuardedEvidenceWriter.write_evidence_file`` 자체가 파일 시스템에 아무것도
    쓰기 전에 (a) symlink escape (b) 같은 relpath 존재 여부(overwrite) 를
    확인하고, ``finalize()`` 는 이전에 커밋된 baseline entry 전부를 디스크에서
    재해시해 바뀌지 않았는지 확인한다 — 가드를 "안 부르는" 경로 자체가 없다.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from landing_accessibility.evidence_manifest import (
    ManifestEntry,
    MissingRunManifestError,
    load_run_manifest,
    sha256_of,
    write_run_manifest,
)

from .execution_mode import enforce_real_target_firewall
from .identity import resolve_within, sha256_bytes
from .provenance import build_provenance

OBSERVATIONS_FILENAME = "observations.jsonl"
PROVENANCE_FILENAME = "provenance.json"
DISCARDED_ATTEMPTS_FILENAME = "discarded_attempts.jsonl"


class OverwriteGuardError(RuntimeError):
    """같은 run 안에서 같은 relpath 에 두 번째로 쓰려고 했다."""


class AppendOnlyViolation(RuntimeError):
    """이전 run 의 커밋된 evidence 가 disk 에서 사라졌거나 바뀌었다 (swap 포함)."""


class DuplicateObservationError(RuntimeError):
    """같은 run 안에서 같은 observation_id 를 두 번 기록하려고 했다."""


class BackdatingViolation(RuntimeError):
    """observation 의 collected_at 이 이 writer 가 생성된 시점보다 과거다
    (prereg backdating 시도 — 나중에 수집해놓고 더 이른 시각에 수집한 것처럼
    타임스탬프를 조작하는 경로를 차단한다)."""


@dataclass
class ObservationRecord:
    """``manifest.jsonl`` (파일 인벤토리)과 별개로, observation 수준의 의미
    필드를 담는다. 파일당 1줄인 ManifestEntry 와 달리 observation 당 1줄이다.
    """

    observation_id: str
    service_id: str
    canonical_url: str
    requested_url: str
    audit_date: str
    protocol_version: str
    collected_at: str
    execution_mode: str = "FIXTURE"
    static_evidence_complete: bool = False
    interaction_evidence_present: bool = False
    gated_boundary_tag: str = "NONE"
    gate_fired_signals: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    provenance: dict[str, Any] = field(default_factory=build_provenance)
    extra: dict[str, Any] = field(default_factory=dict)

    def to_json(self) -> dict[str, Any]:
        d = {
            "observation_id": self.observation_id,
            "service_id": self.service_id,
            "canonical_url": self.canonical_url,
            "requested_url": self.requested_url,
            "audit_date": self.audit_date,
            "protocol_version": self.protocol_version,
            "collected_at": self.collected_at,
            "execution_mode": self.execution_mode,
            "static_evidence_complete": self.static_evidence_complete,
            "interaction_evidence_present": self.interaction_evidence_present,
            "gated_boundary_tag": self.gated_boundary_tag,
            "gate_fired_signals": self.gate_fired_signals,
            "notes": self.notes,
            "provenance": self.provenance,
        }
        d.update(self.extra)
        return d


class GuardedEvidenceWriter:
    """한 ``run_dir`` 에 대해 evidence 파일 + manifest + observations 를
    append-only 로 쓴다.

    두 개의 별도 run 디렉터리(재수집)를 섞지 않는다 — 재수집은 항상 새
    ``run_dir`` (새 ``run_id``) 를 요구한다. 같은 run_dir 안에서는 어떤
    observation_id·relpath 도 두 번 쓸 수 없다.
    """

    def __init__(self, run_dir: Path, *, run_id: str, execution_mode: str = "FIXTURE") -> None:
        # REAL-TARGET FIREWALL (PHASE_GATES.md §4.5) — 다른 어떤 부수효과보다 먼저 검사한다.
        # writer 를 만드는 시점에 이미 막아서, 이후 어떤 write 경로도 REAL_TARGET 으로
        # 도달할 수 없게 한다.
        enforce_real_target_firewall(execution_mode)
        self.execution_mode = execution_mode
        self.run_dir = run_dir
        self.run_id = run_id
        self.run_dir.mkdir(parents=True, exist_ok=True)
        # prereg backdating guard 의 기준시각 — 이 writer 가 실제로 생성된 시점.
        # 어떤 observation 도 이 시각보다 "이전"에 수집됐다고 주장할 수 없다.
        self.created_at = datetime.now(UTC)

        self._write_or_verify_run_provenance()
        self._discarded_path = run_dir / DISCARDED_ATTEMPTS_FILENAME

        try:
            self._baseline_entries: list[ManifestEntry] = load_run_manifest(run_dir)
        except MissingRunManifestError:
            self._baseline_entries = []

        self._baseline_keys = {(e.observation_id, e.relpath) for e in self._baseline_entries}
        self._new_entries: list[ManifestEntry] = []

        self._obs_path = run_dir / OBSERVATIONS_FILENAME
        self._committed_observation_ids: set[str] = set()
        if self._obs_path.exists():
            for line in self._obs_path.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if line:
                    self._committed_observation_ids.add(json.loads(line)["observation_id"])

    # ---- 파일 쓰기 (overwrite guard + symlink guard) ----
    def write_evidence_file(
        self, observation_id: str, subdir: str, filename: str, data: bytes
    ) -> ManifestEntry:
        target = resolve_within(self.run_dir, subdir, filename)
        relpath = f"{subdir}/{filename}"

        if (observation_id, relpath) in self._baseline_keys:
            raise AppendOnlyViolation(
                f"{observation_id}:{relpath} 는 이미 이전 write 에서 커밋됐다. "
                "재수집은 새 run_id 로 해야 한다 (같은 evidence 를 덮어쓰지 않는다)."
            )
        if target.exists():
            raise OverwriteGuardError(f"evidence 파일이 이미 존재한다 (덮어쓰기 금지): {target}")
        if any(
            e.observation_id == observation_id and e.relpath == relpath for e in self._new_entries
        ):
            raise OverwriteGuardError(
                f"이번 run 안에서 {observation_id}:{relpath} 를 두 번 쓰려 했다"
            )

        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        entry = ManifestEntry(
            observation_id=observation_id,
            relpath=relpath,
            sha256=sha256_bytes(data),
            bytes=len(data),
        )
        self._new_entries.append(entry)
        return entry

    # ---- observation 레코드 append ----
    def append_observation(self, record: ObservationRecord) -> None:
        if record.observation_id in self._committed_observation_ids:
            raise DuplicateObservationError(
                f"observation_id 중복: {record.observation_id} 는 이미 이 run 의 "
                f"{OBSERVATIONS_FILENAME} 에 있다."
            )
        collected_at = datetime.fromisoformat(record.collected_at)
        # created_at 은 tz-aware(UTC), collected_at 이 naive 로 들어오면 비교 전 정규화한다.
        if collected_at.tzinfo is None:
            collected_at = collected_at.replace(tzinfo=UTC)
        if collected_at < self.created_at:
            raise BackdatingViolation(
                f"{record.observation_id}: collected_at={record.collected_at} 이 이 writer 의 "
                f"생성 시각({self.created_at.isoformat()})보다 이전이다 — prereg backdating 의심."
            )
        with self._obs_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record.to_json(), ensure_ascii=False, sort_keys=True) + "\n")
        self._committed_observation_ids.add(record.observation_id)

    def record_discarded_attempt(
        self, *, observation_id: str | None, reason: str, detail: str = ""
    ) -> None:
        """실패한 수집 시도를 append-only 로 남긴다.

        "discarded attempt omission" 실패주입을 닫는 자리다 — 수집이 중간에
        실패해 호출자가 재시도하더라도, 실패했던 시도 자체가 조용히 사라지지
        않고 여기 남는다. 이 파일은 절대 지우거나 잘라내지 않는다.
        """
        line = {
            "observation_id": observation_id,
            "reason": reason,
            "detail": detail,
            "recorded_at": datetime.now(UTC).isoformat(),
        }
        with self._discarded_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(line, ensure_ascii=False, sort_keys=True) + "\n")

    def discarded_attempts(self) -> list[dict[str, Any]]:
        if not self._discarded_path.exists():
            return []
        return [
            json.loads(ln)
            for ln in self._discarded_path.read_text(encoding="utf-8").splitlines()
            if ln.strip()
        ]

    def _write_or_verify_run_provenance(self) -> None:
        """run 수준 provenance.json 을 쓴다. 이미 있으면 (append-only) 재검증만
        하고 값을 바꾸지 않는다 — 같은 run 안에서 provenance 가 흔들리면 안 된다."""
        path = self.run_dir / PROVENANCE_FILENAME
        if path.exists():
            existing = json.loads(path.read_text(encoding="utf-8"))
            if existing.get("execution_mode") != self.execution_mode:
                raise AppendOnlyViolation(
                    f"run {self.run_id} 의 provenance.json execution_mode "
                    f"({existing.get('execution_mode')!r}) 가 이번 writer 요청"
                    f"({self.execution_mode!r})과 다르다 — 한 run 안에서 execution_mode 를 바꿀 수 없다"
                )
            return
        prov = build_provenance(
            extra={"run_id": self.run_id, "execution_mode": self.execution_mode}
        )
        path.write_text(
            json.dumps(prov, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8"
        )

    def observation_provenance(self) -> dict[str, Any]:
        """이 writer 의 execution_mode 를 반영한 observation-level provenance."""
        return build_provenance(extra={"execution_mode": self.execution_mode})

    # ---- append-only 실제 강제: baseline 재해시 + manifest 재작성 ----
    def finalize(self) -> dict[str, Any]:
        """이전에 커밋된 entry 가 그대로인지 disk 에서 재확인하고, manifest 를
        (baseline + new) 로 재작성한다.

        이 메서드가 Pilot 의 ``check_append_only`` 와 대응하는 자리다 — 다만
        여기서는 "정의만 하고 호출 안 하는" 실수가 구조적으로 불가능하도록
        파이프라인의 마지막 필수 단계로 만든다 (``pipeline.run_l0_batch`` 가
        관측마다 호출한다).
        """
        problems: list[str] = []
        for e in self._baseline_entries:
            p = self.run_dir / e.relpath
            if not p.exists():
                problems.append(f"append_only: 이전 evidence 파일 사라짐: {e.relpath}")
                continue
            got = sha256_of(p)
            if got != e.sha256:
                problems.append(
                    f"append_only: 이전 evidence 파일 변경됨(swap 의심): {e.relpath} "
                    f"(expect={e.sha256} got={got})"
                )
        if problems:
            raise AppendOnlyViolation("; ".join(problems))

        all_entries = self._baseline_entries + self._new_entries
        write_run_manifest(self.run_dir, all_entries)
        # 새로 쓴 것도 baseline 으로 승격 — 같은 writer 로 연속 finalize 해도 안전하다
        self._baseline_entries = all_entries
        self._baseline_keys = {(e.observation_id, e.relpath) for e in all_entries}
        self._new_entries = []
        return {
            "run_dir": str(self.run_dir),
            "total_entries": len(all_entries),
            "status": "OK",
        }
