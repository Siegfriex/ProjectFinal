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
R1_ROOT = REPO / "artifacts/v3_census/raw/E/E-REAL-CENSUS-1230"
EXCERPT_CAP = 500


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
