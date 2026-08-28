"""SSOTV3 MANIFEST 무결성 — **주장이 아니라 측정**. [D-DEF-98]

`d_heartbeat` 가 3분마다 `"SSOTV3 (MANIFEST_v3.0.json 20/20 sha256 일치, D 독립
검증)"` 을 냈다. **하드코딩된 문장**이다 — manifest 가 깨져도 같은 말을 한다.
A R41(안전·무결성 주장은 **측정기가 낸다**)이 정확히 이 자리다.

측정해 보니 지금은 **참**이다(20/20). 그러나 참인 것과 **재서 참인 것**은 다르다.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

SSOT = Path("/home/sieg/projects-wsl/ProjectFinal/SSOTV3")
MANIFEST = SSOT / "MANIFEST_v3.0.json"


def _entries(doc: dict) -> list:
    return doc.get("files") or []


def verify(root: Path | None = None, doc: dict | None = None) -> dict:
    """manifest 항목별로 실제 파일 sha256 을 다시 계산한다."""
    root = root or SSOT
    if doc is None:
        if not MANIFEST.exists():
            return {"verdict": "NO_MANIFEST", "path": str(MANIFEST)}
        try:
            doc = json.loads(MANIFEST.read_text(encoding="utf-8"))
        except Exception as e:                      # noqa: BLE001
            return {"verdict": "UNREADABLE", "error": str(e)}
    ok, bad, missing = 0, [], []
    for f in _entries(doc):
        p = root / f.get("path", "")
        if not p.exists():
            missing.append(f.get("path"))
            continue
        if hashlib.sha256(p.read_bytes()).hexdigest() == f.get("sha256"):
            ok += 1
        else:
            bad.append(f.get("path"))
    n = len(_entries(doc))
    # **항목이 0 이면 통과가 아니다** — 잴 것이 없었던 것이다
    verdict = ("NO_ENTRIES" if n == 0
               else "PASS" if not bad and not missing else "FAIL")
    return {"verdict": verdict, "n_entries": n, "n_ok": ok,
            "n_mismatch": len(bad), "mismatch": bad[:10],
            "n_missing": len(missing), "missing": missing[:10],
            "manifest_sha256": (hashlib.sha256(MANIFEST.read_bytes()).hexdigest()[:16]
                                if MANIFEST.exists() else None),
            "**주장이 아니라 측정이다**": (
                "`d_heartbeat` 는 이 문장을 **하드코딩**하고 있었다 — manifest 가 깨져도 "
                "같은 말을 냈다. 이제 매 회차 다시 계산한다"),
            "이_수가_말하지_않는_것": (
                "manifest 에 **적힌 20개**가 실제 파일과 같다는 것까지다. "
                "SSOTV3 에 manifest 에 **없는 파일**이 있어도 이 검사는 통과한다")}


def check() -> dict:
    return verify()


def controls() -> dict:
    rows = []

    def case(name, got, want, negative=False):
        rows.append({"case": name, "got": got, "want": want, "ok": got == want,
                     "expectation": "must_flag" if negative else "must_not_flag"})

    import tempfile
    with tempfile.TemporaryDirectory() as td:
        t = Path(td)
        (t / "a.txt").write_text("hello", encoding="utf-8")
        good = hashlib.sha256((t / "a.txt").read_bytes()).hexdigest()
        case("sha 가 맞으면 PASS",
             verify(t, {"files": [{"path": "a.txt", "sha256": good}]})["verdict"], "PASS")
        case("**sha 가 어긋나면 FAIL**",
             verify(t, {"files": [{"path": "a.txt", "sha256": "0" * 64}]})["verdict"],
             "FAIL", negative=True)
        case("**파일이 없으면 FAIL**",
             verify(t, {"files": [{"path": "no_such.txt", "sha256": good}]})["verdict"],
             "FAIL", negative=True)
        case("**항목이 0 이면 PASS 가 아니다** — 잴 것이 없었다",
             verify(t, {"files": []})["verdict"], "NO_ENTRIES", negative=True)
    live = verify()
    case("현재 SSOTV3 manifest 가 통과한다", live["verdict"], "PASS")
    case("항목이 실제로 있다 — 0 이면 검사가 무효다", live["n_entries"] > 0, True)
    ok = all(r["ok"] for r in rows)
    return {"verdict": "PASS" if ok else "FAIL", "n": len(rows),
            "must_flag": sum(1 for r in rows if r["expectation"] == "must_flag"),
            "must_not_flag": sum(1 for r in rows if r["expectation"] == "must_not_flag"),
            "failed": [r["case"] for r in rows if not r["ok"]], "cases": rows}


if __name__ == "__main__":
    c = controls()
    print(json.dumps({"verify": verify(), "controls": c}, ensure_ascii=False, indent=1))
    raise SystemExit(0 if c["verdict"] == "PASS" else 3)
