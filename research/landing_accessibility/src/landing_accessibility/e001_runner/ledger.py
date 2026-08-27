"""append-only batch ledger — batch마다 manifest+hash를 남기고 봉인한다.

`landing_accessibility.engine.evidence.EvidenceRun`이 관측(observation) 레벨의
append-only·overwrite 금지를 구현한 것과 같은 태도를, 이 모듈은 **batch 레벨**에
적용한다. 재구현이 아니라 다른 grain — evidence run은 target 하나 안의 관측들을
묶고, 이 ledger는 여러 target을 묶은 batch들을 묶는다.

    <out_dir>/
        batches/batch_0001_<batch_id>.json   ← "xb" 로만 쓴다 (덮어쓰기 불가)
        BATCH_CHAIN.jsonl                     ← 각 줄이 이전 줄의 hash를 참조한다

체인이 끊기면(`previous_batch_hash`가 실제 이전 줄의 `batch_hash`와 다르면)
`append()`가 실패한다 — 중간 batch 파일을 조용히 바꿔치기해도 다음 append에서
드러난다.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


class LedgerError(RuntimeError):
    """batch ledger 계약 위반."""


class BatchOverwriteError(LedgerError):
    """이미 봉인된 batch 파일을 다시 쓰려 했다."""


class ChainBrokenError(LedgerError):
    """이 batch의 `previous_batch_hash`가 원장의 마지막 batch_hash와 다르다."""


def _canonical_json(obj: Any) -> bytes:
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode(
        "utf-8"
    )


def compute_batch_hash(manifest_without_hash: dict[str, Any]) -> str:
    """`batch_hash` 필드를 제외한 manifest 전체의 sha256 hex digest."""
    payload = {k: v for k, v in manifest_without_hash.items() if k != "batch_hash"}
    return hashlib.sha256(_canonical_json(payload)).hexdigest()


@dataclass
class BatchManifest:
    """봉인된 batch 하나. `commit_batch`가 만들고 `BatchLedger.append`가 원장에 붙인다."""

    batch_index: int
    batch_id: str
    execution_mode: str
    target_ids: list[str]
    results: list[dict[str, Any]]
    provenance: dict[str, Any]
    committed_at: str
    previous_batch_hash: str | None
    batch_hash: str = field(default="")

    def as_dict(self) -> dict[str, Any]:
        return {
            "batch_index": self.batch_index,
            "batch_id": self.batch_id,
            "execution_mode": self.execution_mode,
            "target_ids": list(self.target_ids),
            "results": list(self.results),
            "provenance": self.provenance,
            "committed_at": self.committed_at,
            "previous_batch_hash": self.previous_batch_hash,
            "batch_hash": self.batch_hash,
        }


class BatchLedger:
    """`out_dir` 아래 append-only batch 원장. batch 파일 재작성·순서 위조를 막는다."""

    def __init__(self, out_dir: Path | str) -> None:
        self.out_dir = Path(out_dir)
        self.batches_dir = self.out_dir / "batches"
        self.chain_path = self.out_dir / "BATCH_CHAIN.jsonl"
        self.batches_dir.mkdir(parents=True, exist_ok=True)

    def last_batch_hash(self) -> str | None:
        if not self.chain_path.exists():
            return None
        last_line: str | None = None
        with self.chain_path.open("r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if line:
                    last_line = line
        if last_line is None:
            return None
        return json.loads(last_line)["batch_hash"]

    def next_batch_index(self) -> int:
        if not self.chain_path.exists():
            return 1
        count = 0
        with self.chain_path.open("r", encoding="utf-8") as fh:
            for line in fh:
                if line.strip():
                    count += 1
        return count + 1

    def append(self, manifest: BatchManifest) -> BatchManifest:
        """manifest를 봉인하고 원장에 append-only로 붙인다.

        1. 체인 연속성을 검사한다 (`previous_batch_hash` == 현재 원장의 마지막 hash).
        2. `batch_hash`를 계산해 채운다.
        3. batch 파일을 `xb`(exclusive create)로 쓴다 — 이미 있으면 실패한다.
        4. 원장 jsonl에 한 줄 append한다.

        어느 단계든 실패하면 원장은 이전 상태 그대로다 — 부분 write로 체인이
        오염되지 않는다 (batch 파일을 먼저 쓰고, 그것이 성공한 뒤에만 원장에 붙인다).
        """
        expected_previous = self.last_batch_hash()
        if manifest.previous_batch_hash != expected_previous:
            raise ChainBrokenError(
                f"batch {manifest.batch_index} 의 previous_batch_hash"
                f"({manifest.previous_batch_hash!r}) 가 원장의 마지막 hash"
                f"({expected_previous!r}) 와 다르다 — 순서가 어긋났거나 원장이 변조됐다"
            )

        payload = manifest.as_dict()
        payload["batch_hash"] = ""
        batch_hash = compute_batch_hash(payload)
        sealed = BatchManifest(
            **{**manifest.as_dict(), "batch_hash": batch_hash},
        )

        batch_path = self.batches_dir / f"batch_{manifest.batch_index:04d}_{manifest.batch_id}.json"
        if batch_path.exists():
            raise BatchOverwriteError(f"이미 봉인된 batch 파일이다: {batch_path}")
        data = json.dumps(sealed.as_dict(), ensure_ascii=False, indent=2, sort_keys=True) + "\n"
        with open(batch_path, "x", encoding="utf-8") as fh:
            fh.write(data)

        chain_line = json.dumps(
            {
                "batch_index": sealed.batch_index,
                "batch_id": sealed.batch_id,
                "batch_hash": sealed.batch_hash,
                "previous_batch_hash": sealed.previous_batch_hash,
                "committed_at": sealed.committed_at,
                "target_count": len(sealed.target_ids),
            },
            ensure_ascii=False,
            sort_keys=True,
        )
        with self.chain_path.open("a", encoding="utf-8") as fh:
            fh.write(chain_line + "\n")

        return sealed

    def verify_chain(self) -> dict[str, Any]:
        """원장 전체를 처음부터 재검증한다 — 각 줄의 `previous_batch_hash` 연쇄가 맞는지."""
        if not self.chain_path.exists():
            return {"status": "EMPTY", "entries": 0}
        prev: str | None = None
        entries = 0
        with self.chain_path.open("r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                row = json.loads(line)
                if row["previous_batch_hash"] != prev:
                    return {
                        "status": "BROKEN",
                        "entries": entries,
                        "broken_at_batch_index": row["batch_index"],
                    }
                prev = row["batch_hash"]
                entries += 1
        return {"status": "OK", "entries": entries, "last_hash": prev}


__all__ = [
    "BatchLedger",
    "BatchManifest",
    "BatchOverwriteError",
    "ChainBrokenError",
    "LedgerError",
    "compute_batch_hash",
]
