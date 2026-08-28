"""mart `visible_label` 의 **R1 쪽 확인 가능성**. [D-DEF-104]

`D-V3-FINDING-094` 가 남긴 한계 — '이 진단은 R3 trace 만 본다. mart 의
`visible_label` 은 **R1** 에서 왔고 그 회차의 확인 가능성은 재지 않는다'.

재보니 R1 trace 에는 `visible_label` 도 `selected_candidate` 도 **없다**.
유일한 대리물 `visible_text_excerpt` 는 **500자에서 잘린다** — 그래서
'발췌에 라벨이 없다' 는 **거의 아무것도 말하지 않는다**.

**중간에 낸 수를 거둬들였다.** 8대상 중 7건이 발췌 안에 있다는 값을 얻었지만
절단 때문에 그 비율은 **신호가 아니다**. 발행하지 않는다.
"""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

REPO = Path("/home/sieg/projects-wsl/ProjectFinal")
E_RAW = REPO / "artifacts/v3_census/raw/E"
R1_ROOT = E_RAW / "E-REAL-CENSUS-1230"
EXCERPT_CAP = 500
# [D-DEF-105] `D-V3-FINDING-095` 는 **R1 만** 봤다. mart 의 `collection_run` 은
# R1 15 · R2 22 · R2B 13 이므로 나머지 두 회차도 재야 한다.
RUNS = ("E-REAL-CENSUS-1230", "E-REAL-CENSUS-1230-R2",
        "E-REAL-CENSUS-1230-R2B", "E-REAL-CENSUS-1230-R3")


def _lines(root: Path):
    for d in sorted(p for p in root.iterdir() if p.is_dir()):
        for f in d.glob("*.jsonl"):
            for line in f.read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                try:
                    yield d.name, json.loads(line)
                except Exception:                   # noqa: BLE001
                    continue


def check(root: Path | None = None) -> dict:
    root = root or R1_ROOT
    if not root.exists():
        return {"verdict": "NO_ROOT", "path": str(root)}
    n = has_label = has_sel = 0
    lens = Counter()
    dom_ok = dom_missing = dom_nopath = dom_sha = 0
    for _t, o in _lines(root):
        n += 1
        if "visible_label" in o:
            has_label += 1
        if "selected_candidate" in o:
            has_sel += 1
        e = o.get("visible_text_excerpt")
        if isinstance(e, str):
            lens[len(e)] += 1
        p = o.get("dom_snapshot_path")
        if not p:
            dom_nopath += 1
        else:
            if o.get("dom_snapshot_sha256"):
                dom_sha += 1
            fp = Path(p) if Path(p).is_absolute() else REPO / p
            if fp.exists():
                dom_ok += 1
            else:
                dom_missing += 1
    capped = lens.get(EXCERPT_CAP, 0)
    n_exc = sum(lens.values())
    return {"verdict": "INFO",       # **판정이 아니다** — 확인 가능성을 잰 것이다
            "n_lines": n,
            "n_with_visible_label": has_label,
            "n_with_selected_candidate": has_sel,
            "n_excerpt": n_exc, "n_excerpt_capped": capped,
            "capped_ratio": round(capped / n_exc, 3) if n_exc else None,
            "excerpt_cap": EXCERPT_CAP,
            "dom_snapshot_present": dom_ok, "dom_snapshot_missing": dom_missing,
            "dom_snapshot_no_path": dom_nopath, "dom_snapshot_sha_recorded": dom_sha,
            "**라벨은 R1 trace 로 확인되지 않는다**": (
                "`visible_label` 도 `selected_candidate` 도 R1 trace 에 **없다**. "
                "유일한 대리물 `visible_text_excerpt` 는 **잘린다** — "
                "**발췌에 없다는 것은 거의 아무것도 말하지 않는다**"),
            "**거둬들인 수**": (
                "8대상 중 7건이 발췌 안에 있다는 값을 얻었지만 **절단 때문에 신호가 아니다**. "
                "그 비율을 발행하지 않는다"),
            "확인은_가능하다_다만_안_했다": (
                "`dom_snapshot_path` 가 전건에 있고 파일이 실재하며 `sha256` 이 기록돼 있다 — "
                "**검증할 재료는 있다.** D 는 열지 않았다: 라벨 축은 A 의 조작화이고 "
                "새 측정은 대상 지정 뒤다(`00 §13`)")}


def by_run() -> dict:
    """[D-DEF-105] 회차별 확인 가능성. **`visible_label` 은 어느 회차에도 없다.**

    `selected_candidate` 는 **R2B 부터** 있다 — D 가 다른 도구 주석에 'R3 에서 신설'
    이라고 적었는데 **틀렸다**(R2B 11/11 줄에 있다).
    """
    out, empty = {}, []
    for run in RUNS:
        root = E_RAW / run
        if not root.exists():
            out[run] = {"verdict": "NO_ROOT"}
            continue
        r = check(root)
        dirs = [x for x in root.iterdir() if x.is_dir()]
        # **0 바이트 trace 를 따로 센다** — `exists()` 만 보는 검사는 '있음' 으로 읽는다
        zero = []
        for x in sorted(dirs):
            fs = list(x.glob("*.jsonl"))
            if fs and all(f.stat().st_size == 0 for f in fs):
                zero.append(x.name)
        r["n_targets"] = len(dirs)
        r["n_zero_byte_trace"] = len(zero)
        r["zero_byte_targets"] = zero
        out[run] = r
        empty += [f"{run}/{z}" for z in zero]
    return {"verdict": "INFO",
            "runs": out,
            "n_zero_byte_total": len(empty), "zero_byte": empty,
            "**어느 회차에도 `visible_label` 이 없다**": (
                "네 회차 전부 0 이다. mart 의 라벨은 **B 의 사후파생**이고 "
                "trace 에서 그 이름으로 읽어올 수 없다"),
            "`selected_candidate` 는 R2B 부터": (
                "R1 0 · R2 0 · **R2B 있음** · R3 있음. "
                "D 가 `d_v3_report` 주석에 'R3 에서 신설' 이라고 적은 것은 **부정확했다**"),
            "**0 바이트는 결함이 아니다**": (
                "**6 파일 · 대상 4**(`F4-01`·`F4-08`·`F5-06`·`F5-07`; 뒤 둘은 R1·R2B 양쪽). "
                "mart 는 **넷 다** `visible_label=NOT_OBSERVED` 이고 terminal 사유도 일관된다 "
                "(`TIMEOUT` 2 · `NO_SAFE_ROUTE_UNVERIFIED_CANDIDATE_COUNT` 2). "
                "예: `R2B/F5-06`·`F5-07` 이 0 바이트인데 mart 는 그 둘을 "
                "`visible_label=NOT_OBSERVED` · `terminal_reason=NO_SAFE_ROUTE_UNVERIFIED_CANDIDATE` "
                "로 적었다 — **미관측의 기록이고 mart 가 정확히 옮겼다**. "
                "다만 **`exists()` 만 보는 검사는 이 둘을 '있음' 으로 읽는다**")}


def controls() -> dict:
    import tempfile as _tf
    rows = []

    def case(name, got, want, negative=False):
        rows.append({"case": name, "got": got, "want": want, "ok": got == want,
                     "expectation": "must_flag" if negative else "must_not_flag"})

    with _tf.TemporaryDirectory() as t:
        root = Path(t)
        (root / "T1").mkdir()
        (root / "T1" / "a.jsonl").write_text(
            json.dumps({"visible_text_excerpt": "x" * EXCERPT_CAP,
                        "dom_snapshot_path": "no/such.html",
                        "dom_snapshot_sha256": "a" * 64}) + "\n"
            + json.dumps({"visible_label": "L", "selected_candidate": {"visible_label": "L"},
                          "visible_text_excerpt": "short"}) + "\n",
            encoding="utf-8")
        r = check(root)
        case("**절단된 발췌를 센다**", r["n_excerpt_capped"], 1, negative=True)
        case("`visible_label` 이 있으면 센다", r["n_with_visible_label"], 1)
        case("`selected_candidate` 가 있으면 센다", r["n_with_selected_candidate"], 1)
        case("**없는 DOM 스냅샷을 센다**", r["dom_snapshot_missing"], 1, negative=True)
        case("두 줄을 다 읽었다 — 0 이면 무효다", r["n_lines"], 2)

    with _tf.TemporaryDirectory() as t:
        root = Path(t) / "run"
        (root / "Z1").mkdir(parents=True)
        (root / "Z1" / "E_SCOUT_TRACE_Z1.jsonl").write_text("", encoding="utf-8")
        zero = [x.name for x in sorted(root.iterdir())
                if x.is_dir() and (list(x.glob("*.jsonl"))
                                   and all(f.stat().st_size == 0 for f in x.glob("*.jsonl")))]
        case("**0 바이트 trace 를 존재로 세지 않는다**", zero, ["Z1"], negative=True)

    runs = by_run()
    case("네 회차 전부 `visible_label` 0",
         [r.get("n_with_visible_label") for r in runs["runs"].values()], [0, 0, 0, 0])
    case("**R2B 에 `selected_candidate` 가 있다** — 'R3 에서 신설' 은 틀렸다",
         runs["runs"]["E-REAL-CENSUS-1230-R2B"]["n_with_selected_candidate"] > 0, True,
         negative=True)
    # **한 회차만 보고 2 라고 적었다가 대조군이 잡았다** — 실제 6(대상 4, R1 4 + R2B 2)
    case("0 바이트 trace 총 6건(대상 4)", runs["n_zero_byte_total"], 6, negative=True)
    case("0 바이트가 R1 에도 있다 — R2B 만 본 것이 틀렸다",
         runs["runs"]["E-REAL-CENSUS-1230"]["n_zero_byte_trace"], 4, negative=True)

    live = check()
    case("R1 에 `visible_label` 이 없다", live["n_with_visible_label"], 0)
    case("R1 에 `selected_candidate` 가 없다", live["n_with_selected_candidate"], 0)
    case("R1 줄을 실제로 읽었다", live["n_lines"] > 0, True)
    case("DOM 스냅샷은 전건 실재한다", live["dom_snapshot_missing"], 0)
    ok = all(r["ok"] for r in rows)
    return {"verdict": "PASS" if ok else "FAIL", "n": len(rows),
            "must_flag": sum(1 for r in rows if r["expectation"] == "must_flag"),
            "must_not_flag": sum(1 for r in rows if r["expectation"] == "must_not_flag"),
            "failed": [r["case"] for r in rows if not r["ok"]], "cases": rows}


if __name__ == "__main__":
    c = controls()
    print(json.dumps({"check": check(), "controls": c}, ensure_ascii=False, indent=1))
    raise SystemExit(0 if c["verdict"] == "PASS" else 3)
