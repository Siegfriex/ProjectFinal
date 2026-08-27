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


if __name__ == "__main__":
    raise SystemExit(main())
