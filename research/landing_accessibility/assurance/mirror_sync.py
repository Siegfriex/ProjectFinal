#!/usr/bin/env python3
"""C bus mirror — R51 (Δ52, T-A-V3-FC-009): a mirror is a MEASURED synchronisation.
① whole origin, not "what C touched"  ② re-hash after copy (copy success is never assumed)
③ no swallowed errors  ④ three directions: missing / different / only-in-mirror  ⑤ origin not found ⇒ exit 2 (did not run).
exit 0 = synced and verified · exit 1 = residual mismatch after sync · exit 2 = did not run.
Usage: mirror_sync.py [--check-only]"""
from __future__ import annotations
import datetime, hashlib, json, pathlib, shutil, sys
BUS = pathlib.Path("/home/sieg/projects-wsl/ProjectFinal/.agent_bus/landing_v2")
M = pathlib.Path(__file__).resolve().parent / "bus_mirror_c"
SUBS = ("tickets", "acks", "completions", "heartbeats", "escalations")
# Δ58-unit: the unit is not only directories — top-level record FILES of the bus are part of "the whole origin".
TOP_FILES_GLOB = ("*.jsonl", "*.json", "*.md")
# Declared exclusions (not "forgotten" — stated): holdout_c_only (holdout non-exposure prohibition — never enters git),
# _b_tools (B's code, not a record), locks (ephemeral). Their names are recorded in MIRROR_STATE so the gap is visible.
EXCLUDED_DIRS = ("holdout_c_only", "_b_tools", "locks")
def _sha(p: pathlib.Path) -> str: return hashlib.sha256(p.read_bytes()).hexdigest()
def _index(root: pathlib.Path, sub: str) -> dict:
    d = root / sub
    return {p.name: _sha(p) for p in sorted(d.glob("*.json"))} if d.exists() else {}
def _top_files(root: pathlib.Path) -> dict:
    out = {}
    for g in TOP_FILES_GLOB:
        for p in sorted(root.glob(g)):
            if p.is_file(): out[p.name] = _sha(p)
    return out
def diff(bus: pathlib.Path, mirror: pathlib.Path) -> dict:
    out = {}
    s, m = _top_files(bus), _top_files(mirror / "_top")
    out["_top_files"] = {"origin": len(s), "mirror": len(m), "missing": sorted(k for k in s if k not in m),
                         "different": sorted(k for k in s if k in m and s[k] != m[k]), "only_in_mirror": sorted(k for k in m if k not in s)}
    for sub in SUBS:
        s, m = _index(bus, sub), _index(mirror, sub)
        out[sub] = {"origin": len(s), "mirror": len(m), "missing": sorted(k for k in s if k not in m),
                    "different": sorted(k for k in s if k in m and s[k] != m[k]), "only_in_mirror": sorted(k for k in m if k not in s)}
    return out
def residual(d: dict) -> int: return sum(len(v["missing"]) + len(v["different"]) + len(v["only_in_mirror"]) for v in d.values())
def sync(bus: pathlib.Path, mirror: pathlib.Path) -> None:
    (mirror / "_top").mkdir(parents=True, exist_ok=True)
    for g in TOP_FILES_GLOB:
        for p in sorted(bus.glob(g)):
            if p.is_file(): shutil.copyfile(p, mirror / "_top" / p.name)
    for q in (mirror / "_top").glob("*"):
        if not (bus / q.name).exists(): q.unlink()
    for sub in SUBS:
        (mirror / sub).mkdir(parents=True, exist_ok=True)
        for p in sorted((bus / sub).glob("*.json")):
            shutil.copyfile(p, mirror / sub / p.name)          # raises on failure — nothing is swallowed
        for q in (mirror / sub).glob("*.json"):
            if not (bus / sub / q.name).exists(): q.unlink()   # only-in-mirror ⇒ removed (origin is the authority)
    legacy = mirror / "heartbeat"                                # pre-R51 layout: single-plane heartbeat dir
    if legacy.exists(): shutil.rmtree(legacy)
def main(argv: list[str]) -> int:
    kst = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9))).isoformat(timespec="seconds")
    if not BUS.exists() or not any((BUS / s).exists() for s in SUBS):
        print(json.dumps({"measured_at_kst": kst, "status": "DID_NOT_RUN", "note": "bus origin not found — read neither as synced nor as empty (exit 2)"})); return 2
    before = diff(BUS, M)
    if "--check-only" not in argv: sync(BUS, M)
    after = diff(BUS, M)
    rec = {"measured_at_kst": kst, "origin": str(BUS), "mirror": str(M), "mode": "check-only" if "--check-only" in argv else "sync+verify",
           "before": {k: {kk: (len(vv) if isinstance(vv, list) else vv) for kk, vv in v.items()} for k, v in before.items()},
           "after": {k: {kk: (len(vv) if isinstance(vv, list) else vv) for kk, vv in v.items()} for k, v in after.items()},
           "residual_after": residual(after), "status": "SYNCED_VERIFIED" if residual(after) == 0 else "RESIDUAL_MISMATCH",
           "declared_exclusions": {"dirs": list(EXCLUDED_DIRS), "reason": {"holdout_c_only": "holdout non-exposure — never mirrored into git", "_b_tools": "B code, not a record", "locks": "ephemeral"}},
           "unit": "directories " + ",".join(SUBS) + " + top-level files " + ",".join(TOP_FILES_GLOB)}
    (M / "MIRROR_STATE.json").write_text(json.dumps(rec, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps({k: rec[k] for k in ("measured_at_kst", "mode", "residual_after", "status")}, ensure_ascii=False))
    return 0 if rec["residual_after"] == 0 else 1
if __name__ == "__main__":
    try: sys.exit(main(sys.argv[1:]))
    except SystemExit: raise
    except Exception as e:
        import traceback; traceback.print_exc(); print("mirror_sync: did not run — read neither as pass nor fail (exit 2)", file=sys.stderr); sys.exit(2)
