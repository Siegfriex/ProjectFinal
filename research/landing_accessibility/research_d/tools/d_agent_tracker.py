"""D subagent run registry — 서브에이전트가 한 일을 추적 가능하게 만든다.

D는 worker를 병렬로 띄운다. 각 worker가 무엇을 받았고, 얼마를 썼고, 무엇을 냈고,
어떤 verdict를 냈는지가 남지 않으면 "누가 이 숫자를 만들었나"를 되짚을 수 없다.

registry는 Git에 남기고(append-only), MLflow는 이것을 읽어 run 메타로 붙인다.
registry가 canonical, MLflow는 index다.

usage:
    d_agent_tracker.py record --rq RQ-D8 --label "..." --status completed \
        --tokens 108682 --tool-uses 17 --duration-ms 830162 --verdict PARTIALLY_SUPPORTED \
        --owns tools/rq_d8_cap_bias.py results/RQ_D8_cap_bias.json
    d_agent_tracker.py list
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path

RD = Path(__file__).resolve().parents[1]
WT = RD.parents[2]
REGISTRY = RD / "AGENT_RUN_REGISTRY.jsonl"
KST = timezone(timedelta(hours=9))


def git(*a: str) -> str:
    return subprocess.run(["git", *a], cwd=WT, capture_output=True, text=True).stdout.strip()


def record(a: argparse.Namespace) -> int:
    owned = []
    for rel in a.owns or []:
        p = RD / rel
        owned.append({
            "path": rel,
            "exists": p.exists(),
            "bytes": p.stat().st_size if p.exists() else 0,
            "sha256": hashlib.sha256(p.read_bytes()).hexdigest() if p.exists() else None,
        })
    rec = {
        "kind": "SUBAGENT_RUN",
        "rq_id": a.rq,
        "label": a.label,
        "status": a.status,
        "verdict": a.verdict,
        "spawned_by": "D",
        "recorded_at_kst": datetime.now(KST).isoformat(),
        "d_head_sha": git("rev-parse", "HEAD"),
        "subagent_tokens": a.tokens,
        "tool_uses": a.tool_uses,
        "duration_ms": a.duration_ms,
        "duration_min": round(a.duration_ms / 60000, 2) if a.duration_ms else None,
        "owned_files": owned,
        "constraints": {
            "production_modified": False,
            "git_executed": False,
            "labels_produced": False,
            "holdout_accessed": False,
            "real_target_accessed": False,
        },
        "note": a.note,
    }
    with REGISTRY.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
    print(json.dumps(rec, ensure_ascii=False, indent=1))
    return 0


def load() -> list[dict]:
    if not REGISTRY.exists():
        return []
    return [json.loads(line) for line in REGISTRY.read_text(encoding="utf-8").splitlines() if line.strip()]


def latest_by_rq() -> dict[str, dict]:
    out: dict[str, dict] = {}
    for r in load():
        out[r["rq_id"]] = r          # append-only, 뒤가 최신
    return out


def list_runs() -> int:
    for r in load():
        tok = f"{r['subagent_tokens']:,}" if r.get("subagent_tokens") else "-"
        print(f"{r['rq_id']:<8} {r['status']:<10} {str(r.get('verdict')):<22} "
              f"tokens={tok:>9} tools={r.get('tool_uses','-'):>3} "
              f"{r.get('duration_min','-')}min  files={len(r.get('owned_files',[]))}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    rec = sub.add_parser("record")
    rec.add_argument("--rq", required=True)
    rec.add_argument("--label", required=True)
    rec.add_argument("--status", default="completed")
    rec.add_argument("--verdict", default=None)
    rec.add_argument("--tokens", type=int, default=None)
    rec.add_argument("--tool-uses", type=int, default=None)
    rec.add_argument("--duration-ms", type=int, default=None)
    rec.add_argument("--owns", nargs="*", default=[])
    rec.add_argument("--note", default=None)
    sub.add_parser("list")
    a = ap.parse_args()
    return record(a) if a.cmd == "record" else list_runs()


if __name__ == "__main__":
    raise SystemExit(main())
