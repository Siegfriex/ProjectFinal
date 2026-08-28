"""완결 게이트 adversarial fixture — Director P0 1.2.

D-DEF-10 은 sidecar JSON 이 canonical result 를 가린 사건이었다. 그때는
`_MLFLOW_RUN.json` 을 이름으로 막았지만, **다음 사이드카는 다른 이름을 달고 온다.**
그래서 canonical 선택은 filename exception 이 아니라 **content contract**
(최상위 `verdict` 보유) 로 결정한다. 이 fixture 가 그것을 실증한다.

exit 0 = 전 항목 기대대로. 1 = 하나라도 어긋남.
"""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import d_mlflow  # noqa: E402

CANON = {"verdict": "SUPPORTED", "hypothesis_verdicts": {"H": "SUPPORTED"}, "n": 42}


def _case(tmp: Path, name: str, files: dict, expect_json: str | None, expect_skip_kw: str | None):
    d = tmp / name
    d.mkdir()
    for fn, body in files.items():
        (d / fn).write_text(body if isinstance(body, str) else json.dumps(body, ensure_ascii=False),
                            encoding="utf-8")
    got = {e["rq_id"]: (e["json"].name if e["json"] else None) for e in d_mlflow.discover(d)}
    return got


def main() -> int:
    fails, log = [], []
    with tempfile.TemporaryDirectory() as t:
        tmp = Path(t)

        # SANITY: fixture 의 RQ id 를 파서가 실제로 인식하는가.
        # 인식하지 못하면 아래 모든 케이스가 "빈 결과" 로 조용히 통과한다 —
        # 이 fixture 를 처음 짤 때 실제로 그렇게 됐다.
        s0 = tmp / "sanity"; s0.mkdir()
        (s0 / "RQ_D91_result.json").write_text(json.dumps(CANON), encoding="utf-8")
        if not [x for x in d_mlflow.discover(s0) if x["rq_id"] == "RQ-D91"]:
            print("GATE SELFTEST INVALID — fixture id 를 파서가 인식하지 못한다. 검사 자체가 성립하지 않는다.")
            return 1
        log.append("  OK   sanity: fixture id 인식됨 (이게 실패하면 아래는 전부 무의미)")

        # A) 알파벳상 앞서는 사이드카가 canonical 을 가리면 안 된다 (D-DEF-10 원인형)
        got = _case(tmp, "a", {
            "RQ_D91_MLFLOW_RUN.json": {"run_id": "abc"},
            "RQ_D91_real_result.json": CANON,
            "RQ_D91_FINDINGS.md": "x",
        }, None, None)
        ok = got.get("RQ-D91") == "RQ_D91_real_result.json"
        log.append(f"  {'OK  ' if ok else 'FAIL'} 사이드카 마스킹(기존 이름): 선택={got.get('RQ-D91')}")
        if not ok:
            fails.append("사이드카가 canonical 을 가림 (_MLFLOW_RUN)")

        # B) **이름 예외에 없는 새 사이드카** — content contract 여야만 통과한다
        got = _case(tmp, "b", {
            "RQ_D92_AAA_provenance.json": {"source": "s", "note": "verdict 라는 단어만 있고 키는 없다"},
            "RQ_D92_zzz_result.json": CANON,
            "RQ_D92_FINDINGS.md": "x",
        }, None, None)
        ok = got.get("RQ-D92") == "RQ_D92_zzz_result.json"
        log.append(f"  {'OK  ' if ok else 'FAIL'} 사이드카 마스킹(미지 이름): 선택={got.get('RQ-D92')}")
        if not ok:
            fails.append("이름 예외에 없는 사이드카가 canonical 을 가림 — content contract 미작동")

        # C) verdict 없는 결과만 있으면 canonical 후보가 아니다
        got = _case(tmp, "c", {
            "RQ_D93_partial.json": {"n": 1},
            "RQ_D93_FINDINGS.md": "x",
        }, None, None)
        log.append(f"  OK   verdict 부재 케이스 선택={got.get('RQ-D93')} (게이트가 뒤에서 차단)")

        # D) 게이트 3조건 — 노트북 없음이 통과하면 안 된다
        d = tmp / "d"
        d.mkdir()
        (d / "RQ_D94_result.json").write_text(json.dumps(CANON), encoding="utf-8")
        (d / "RQ_D94_FINDINGS.md").write_text("x", encoding="utf-8")
        e = [x for x in d_mlflow.discover(d) if x["rq_id"] == "RQ-D94"][0]
        has_md = e["md"].exists()
        has_v = "verdict" in json.loads(e["json"].read_text())
        log.append(f"  OK   3조건 재료 확인: verdict={has_v} FINDINGS={has_md} (노트북 조건은 sync 가 검사)")
        if not (has_v and has_md):
            fails.append("게이트 재료 불일치")

    print("\n".join(log))
    print()
    if fails:
        print(f"GATE SELFTEST INVALID — {len(fails)}건")
        for x in fails:
            print("  -", x)
        return 1
    print("GATE SELFTEST PASS — canonical 선택이 filename 이 아니라 content contract 로 결정된다")
    return 0


def controls() -> dict:
    """[D-DEF-102] 이 fixture 를 **게이트가 부를 수 있게** 감싼다.

    `D-V3-FINDING-092` 에서 나는 '`controls()` 진입점이 없어 무엇을 부를지 정해야
    하고 아무 함수나 골라 부르면 그것이 임의 판정' 이라고 적었다. **틀렸다** —
    `main()` 이 정의된 진입점이고(docstring: `exit 0 = 전 항목 기대대로`)
    `tempfile` 밖으로는 아무것도 쓰지 않는다. **읽지 않고 조심한 것이다.**
    """
    import contextlib
    import io
    import json as _j
    import tempfile as _tf

    rows = []

    def case(name, got, want, negative=False):
        rows.append({"case": name, "got": got, "want": want, "ok": got == want,
                     "expectation": "must_flag" if negative else "must_not_flag"})

    # 본 fixture — 출력은 삼킨다(스캔 출력에서 소음이 된다). 삼키는 것은 **출력**이지 결과가 아니다
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc = main()
    case("fixture 전 항목이 기대대로다 (exit 0)", rc, 0)
    case("**계약 대상이 실재한다** — CANON 에 최상위 `verdict` 가 있다",
         "verdict" in CANON, True)

    # 음성 — **층을 맞춘다.** 처음엔 `discover()` 가 `verdict` 없는 파일을 안 뽑을 거라
    # 가정했는데 **틀렸다**: `discover` 는 뽑고 **차단은 `gate()` 가 한다**
    # (이 fixture 의 케이스 C 가 '게이트가 뒤에서 차단' 이라고 이미 적어 두었다).
    with _tf.TemporaryDirectory() as t:
        d = Path(t) / "neg"
        d.mkdir()
        (d / "RQ_D99_partial.json").write_text(_j.dumps({"note": "verdict 키가 없다"}),
                                               encoding="utf-8")
        got = [x for x in d_mlflow.discover(d) if x["rq_id"] == "RQ-D99"]
        chosen = got[0].get("json") if got else None
        case("`discover` 는 후보로 뽑는다 — 차단 층이 아니다",
             bool(chosen), True)
        case("**뽑힌 것에 `verdict` 가 없다** — 뒤 게이트가 막을 재료가 있다",
             "verdict" in _j.loads(Path(chosen).read_text(encoding="utf-8")) if chosen else None,
             False, negative=True)

    ok = all(r["ok"] for r in rows)
    return {"verdict": "PASS" if ok else "FAIL", "n": len(rows),
            "must_flag": sum(1 for r in rows if r["expectation"] == "must_flag"),
            "must_not_flag": sum(1 for r in rows if r["expectation"] == "must_not_flag"),
            "failed": [r["case"] for r in rows if not r["ok"]],
            "fixture_stdout_lines": len(buf.getvalue().splitlines()),
            "cases": rows}


if __name__ == "__main__":
    raise SystemExit(main())
