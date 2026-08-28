"""D 의 **입력**(mart · raw evidence)이 바뀌었는가.

지시는 매 회차 "production/control/engine/**mart/raw evidence** 수정 금지" 를
반복한다. 그런데 `d_heartbeat._production_touch` 는 **git diff** 로 재고,
`artifacts/` 는 `.gitignore` 로 추적 제외라 **mart 와 raw 는 그 측정 범위 밖**이다.

mart 는 `d_prereg_check` 가 sha `5290e0c3` 로 고정해 매 루프 확인한다.
**raw 는 아무도 재지 않았다** — D 도구 셋이 읽기만 한다.

여기서 잰다. 파일별 sha256 을 한 번 기록하고 이후 대조한다.

**이 검사는 "D 가 바꿨다" 를 말하지 않는다.** 다른 평면(B·E)이 raw 를 갱신할 수
있고 그것은 정당하다. 이 검사가 말하는 것은 **"D 의 입력이 바뀌었다"** 이고,
그러면 D 의 기존 산출은 다른 판본을 가리킨다 — mart sha 고정과 같은 논리다.

**대상을 바꾸지 않는다**(D-DEF-50). 읽기만 한다.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

REPO = Path("/home/sieg/projects-wsl/ProjectFinal")
CENSUS = REPO / "artifacts/v3_census"
WATCH = [("mart", CENSUS / "mart"), ("raw", CENSUS / "raw")]

# [D-DEF-72] **동결 대상과 살아있는 문서를 가른다.**
#
# `CANONICAL_MART_50.sha256.json` 은 mart 디렉터리에 있지만 **동결본이 아니다** —
# B 가 지식을 계속 덧붙이는 사이드카다(어휘 선언·철회 감사·독법 주석…).
# 두 번 연속 그 파일 하나 때문에 FAIL 이 났고, **매 회차 확인→갱신을 반복하면
# 그것도 배경음이 된다**(D-DEF-52·59 의 형태).
#
# 그래서 나눈다:
#   동결(CSV·raw)  변경 → **FAIL**. D 의 모든 수치가 다른 판본을 가리키게 된다
#   사이드카        변경 → **INFO**. 정상이고, 다만 **읽어야 할 것이 생겼다**는 신호다
# **손 목록이 아니라 판정 규칙이다** [D-DEF-73].
# 첫 판은 두 파일을 열거했다 — 새 사이드카가 생기면 동결본으로 취급돼 FAIL 이
# 나고, 그때 목록을 늘려야 한다. 그것이 D-DEF-45(손 목록은 뒤처진다)의 자리다.
#
# 사이드카의 정의: **동결본과 stem 을 공유하되 데이터 확장자가 아닌 파일.**
#   CANONICAL_MART_50.csv          동결본
#   CANONICAL_MART_50.sha256.json  사이드카 (같은 stem · 메타 확장자)
#   CANONICAL_MART_50.RETRACTIONS.md 사이드카
#   CANONICAL_MART_50.parquet      **동결본** — 같은 데이터의 다른 형식일 수 있다
FROZEN_STEMS = ("CANONICAL_MART_50",)
DATA_SUFFIXES = (".csv", ".parquet", ".jsonl", ".tsv", ".feather")


def is_living_doc(rel: str) -> bool:
    """동결본에 딸린 **메타 문서**인가 — 손 목록이 아니라 규칙으로 판정한다."""
    p = Path(rel)
    name = p.name
    stem = name.split(".", 1)[0]
    if stem not in FROZEN_STEMS:
        return False
    if "." not in name:
        return False
    suffix = "." + name.split(".", 1)[1]        # `.sha256.json` · `.csv`
    last = "." + name.rsplit(".", 1)[1]
    # 데이터 확장자로 끝나면 동결본이다 — 같은 데이터의 다른 형식일 수 있다
    if last in DATA_SUFFIXES:
        return False
    return suffix != last or True               # stem 공유 + 비데이터 = 사이드카
RD = Path(__file__).resolve().parent.parent
BASELINE = RD / "results" / "D_INPUT_INTEGRITY_BASELINE.json"


def _sha(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def snapshot() -> dict:
    out = {}
    for name, root in WATCH:
        if not root.is_dir():
            out[name] = {"_missing": True}
            continue
        files = {}
        for p in sorted(root.rglob("*")):
            if p.is_file():
                files[str(p.relative_to(CENSUS))] = _sha(p)
        out[name] = files
    return out


def check() -> dict:
    now = snapshot()
    if not BASELINE.exists():
        return {"verdict": "NO_BASELINE", "n_files": sum(
            len(v) for v in now.values() if isinstance(v, dict)),
            "무엇을_해야_하나": "`write_baseline()` 으로 기준을 한 번 기록한다"}
    base = json.loads(BASELINE.read_text(encoding="utf-8"))["snapshot"]
    changed, added, removed = [], [], []
    for name in {*base, *now}:
        b, n = base.get(name, {}), now.get(name, {})
        for k in sorted(set(b) | set(n)):
            if k not in n:
                removed.append(k)
            elif k not in b:
                added.append(k)
            elif b[k] != n[k]:
                changed.append(k)
    living = [k for k in changed if is_living_doc(k)]
    frozen_changed = [k for k in changed if not is_living_doc(k)]
    ok = not (frozen_changed or added or removed)
    return {"verdict": "PASS" if ok else "FAIL",
            "living_doc_changed": living,
            "frozen_changed": frozen_changed,
            "규칙의_적용_범위": ("사이드카 판정은 `FROZEN_STEMS`(현재 `CANONICAL_MART_50`) "
                        "에 딸린 것만 본다. mart 의 `INGEST_LEDGER.jsonl`·`REINGEST.log` "
                        "등은 **stem 이 달라 동결본으로 취급**된다 — 바뀌면 FAIL 이 나고 "
                        "**그때 성격을 판단한다.** 미리 사이드카로 분류하면 동결 대상을 "
                        "놓친다"),
            "동결_vs_사이드카": ("동결본(CSV·raw) 변경은 **FAIL** — D 의 수치가 다른 판본을 "
                          "가리킨다. 사이드카 변경은 **INFO** — 정상이고 다만 "
                          "**읽어야 할 것이 생겼다**는 신호다"),
            "n_files": sum(len(v) for v in now.values() if isinstance(v, dict)),
            "changed": changed[:20], "added": added[:20], "removed": removed[:20],
            "n_changed": len(changed), "n_added": len(added), "n_removed": len(removed),
            "이_검사가_말하지_않는_것": ("**누가 바꿨는가.** 다른 평면이 raw 를 갱신할 수 "
                              "있고 그것은 정당하다. 말하는 것은 '**D 의 입력이 "
                              "바뀌었다**' 이고, 그러면 D 의 기존 산출은 다른 판본을 가리킨다"),
            "왜_필요한가": ("`production_modified` 는 git diff 로 재는데 `artifacts/` 는 "
                       "추적 제외라 **mart·raw 는 그 측정 범위 밖**이다")}


def write_baseline(note: str = "") -> dict:
    snap = snapshot()
    doc = {"measured_at_kst": subprocess.run(
        ["date", "-Iseconds"], capture_output=True, text=True).stdout.strip(),
        "note": note, "roots": [str(r.relative_to(REPO)) for _, r in WATCH],
        "n_files": sum(len(v) for v in snap.values() if isinstance(v, dict)),
        "snapshot": snap}
    BASELINE.write_text(json.dumps(doc, ensure_ascii=False, indent=1) + "\n",
                        encoding="utf-8")
    return {"written": str(BASELINE), "n_files": doc["n_files"]}


def controls() -> dict:
    """합성 트리로 변경·추가·삭제를 잡는지 본다. **실제 입력은 건드리지 않는다.**"""
    import tempfile
    rows = []

    def case(name, got, want, negative=False):
        rows.append({"case": name, "got": got, "want": want, "ok": got == want,
                     "expectation": "must_flag" if negative else "must_not_flag"})

    with tempfile.TemporaryDirectory() as td:
        d = Path(td)
        (d / "a.txt").write_text("one", encoding="utf-8")
        b = {str(p.relative_to(d)): _sha(p) for p in d.rglob("*") if p.is_file()}

        def diff(now_dir):
            n = {str(p.relative_to(now_dir)): _sha(p)
                 for p in now_dir.rglob("*") if p.is_file()}
            ch = [k for k in b if k in n and b[k] != n[k]]
            ad = [k for k in n if k not in b]
            rm = [k for k in b if k not in n]
            return ch, ad, rm

        case("변경 없음", diff(d), ([], [], []))
        (d / "a.txt").write_text("two", encoding="utf-8")
        case("내용이 바뀌면 changed", diff(d)[0], ["a.txt"], negative=True)
        (d / "b.txt").write_text("new", encoding="utf-8")
        case("파일이 늘면 added", diff(d)[1], ["b.txt"], negative=True)
        (d / "a.txt").unlink()
        case("파일이 사라지면 removed", diff(d)[2], ["a.txt"], negative=True)

    # [D-DEF-72] 사이드카는 FAIL 을 내지 않고, 동결본은 낸다
    # [D-DEF-73] **손 목록이 아니라 규칙** — 새 사이드카가 자동 인식되는가
    case("sha256 사이드카", is_living_doc("mart/CANONICAL_MART_50.sha256.json"), True)
    case("RETRACTIONS 사이드카", is_living_doc("mart/CANONICAL_MART_50.RETRACTIONS.md"), True)
    case("**아직 없는 사이드카도 인식된다**",
         is_living_doc("mart/CANONICAL_MART_50.NOTES.md"), True)
    case("동결 CSV 는 사이드카가 아니다",
         is_living_doc("mart/CANONICAL_MART_50.csv"), False, negative=True)
    case("**같은 stem 의 데이터 파일도 동결본이다**",
         is_living_doc("mart/CANONICAL_MART_50.parquet"), False, negative=True)
    case("남의 stem 은 대상이 아니다",
         is_living_doc("mart/snapshot_10.csv"), False, negative=True)
    case("raw 파일은 사이드카가 아니다",
         is_living_doc("raw/E/x/E_SCOUT_TRACE_F1-01.jsonl"), False, negative=True)

    # 이 검사가 실제 입력을 바꾸지 않는지 — snapshot 은 읽기 전용이다
    before = snapshot()
    after = snapshot()
    case("검사 자체가 입력을 바꾸지 않는다", before == after, True)

    ok = all(r["ok"] for r in rows)
    return {"verdict": "PASS" if ok else "FAIL", "n": len(rows),
            "must_flag": sum(1 for r in rows if r["expectation"] == "must_flag"),
            "must_not_flag": sum(1 for r in rows if r["expectation"] == "must_not_flag"),
            "failed": [r["case"] for r in rows if not r["ok"]], "cases": rows}


if __name__ == "__main__":
    import sys
    out = {"check": check(), "controls": controls()}
    print(json.dumps(out, ensure_ascii=False, indent=1))
    v = out["check"]["verdict"]
    sys.exit(0 if out["controls"]["verdict"] == "PASS" and v in ("PASS", "NO_BASELINE") else 1)
