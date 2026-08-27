"""D input snapshot freezer.

RQ-independent. 모든 D 연구의 입력 동일성을 보장하기 위해
(1) SSOTV2 문서 11종 SHA256
(2) origin의 exact remote heads
(3) E001 raw evidence root별 observation 목록과 manifest 해시
를 하나의 JSON으로 동결한다.

이 스크립트는 어떤 production 경로도 수정하지 않는다 (read-only).
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

REPO = Path("/home/sieg/projects-wsl/ProjectFinal")
SSOTV2 = REPO / "SSOTV2"
EVIDENCE_ROOTS = {
    f"w{n}": REPO / f".agent_worktrees/claude_b_e001_worker_{n}/artifacts/e001_w{n}/evidence"
    for n in ("01", "02", "03", "04")
}
MART_ROOTS = {
    "analysis_current": REPO / ".agent_worktrees/claude_b_analysis_current/artifacts/e001_real_marts",
    "handoff_b": REPO / ".agent_worktrees/claude_b_handoff/artifacts/e001_real_marts",
}


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def dir_bytes(p: Path) -> int:
    return sum(f.stat().st_size for f in p.rglob("*") if f.is_file())


def remote_heads() -> dict[str, str]:
    out = subprocess.run(
        ["git", "ls-remote", "--heads", "origin"],
        cwd=REPO, capture_output=True, text=True, check=True,
    ).stdout
    heads = {}
    for line in out.splitlines():
        sha, ref = line.split("\t")
        heads[ref.removeprefix("refs/heads/")] = sha
    return heads


def observations(root: Path) -> list[dict]:
    rows = []
    for d in sorted(p for p in root.iterdir() if p.is_dir()):
        man = d / "manifest.jsonl"
        run = d / "run.json"
        rows.append({
            "observation_dir": d.name,
            "manifest_sha256": sha256_file(man) if man.exists() else None,
            "run_sha256": sha256_file(run) if run.exists() else None,
            "bytes": dir_bytes(d),
            "file_count": sum(1 for f in d.rglob("*") if f.is_file()),
        })
    return rows


def main() -> int:
    created_at = sys.argv[1] if len(sys.argv) > 1 else None
    snap = {
        "snapshot_id": "D-INPUT-SNAPSHOT-v2.1",
        "created_at_kst": created_at,
        "producer": "D",
        "read_only": True,
        "ssot_authority": {
            "root": str(SSOTV2),
            "git_tracked": False,
            "files": {p.name: sha256_file(p) for p in sorted(SSOTV2.iterdir()) if p.is_file()},
        },
        "remote_heads": remote_heads(),
        "evidence_roots": {},
        "mart_roots": {},
    }
    for name, root in EVIDENCE_ROOTS.items():
        if not root.exists():
            snap["evidence_roots"][name] = {"root": str(root), "exists": False}
            continue
        obs = observations(root)
        snap["evidence_roots"][name] = {
            "root": str(root),
            "exists": True,
            "observation_count": len(obs),
            "bytes": sum(o["bytes"] for o in obs),
            "observations": obs,
        }
    for name, root in MART_ROOTS.items():
        if not root.exists():
            snap["mart_roots"][name] = {"root": str(root), "exists": False}
            continue
        snap["mart_roots"][name] = {
            "root": str(root),
            "exists": True,
            "files": {p.name: {"sha256": sha256_file(p), "bytes": p.stat().st_size}
                      for p in sorted(root.iterdir()) if p.is_file()},
        }
    out = Path(__file__).resolve().parents[1] / "INPUT_SNAPSHOT_v21.json"
    out.write_text(json.dumps(snap, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    total = sum(v.get("observation_count", 0) for v in snap["evidence_roots"].values())
    print(f"wrote {out}")
    print(f"observation_count total = {total}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
