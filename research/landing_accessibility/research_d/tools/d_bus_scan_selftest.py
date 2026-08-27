"""d_bus_lib.scan 의 negative-control fixture — T-A-V3-P0-D-001.

세 종류를 실제 파일로 만들어 **실행**한다. "테스트를 작성했다" 는 완료가 아니다.

  known_positive  : D 앞으로 온 4가지 표기 변형 — 전부 검출돼야 한다
  known_negative  : D 앞이 아닌 티켓 — 하나도 검출되면 안 된다 (과탐 0)
  malformed_json  : 깨진 JSON — 조용히 0건이 아니라 parse_errors 로 올라와야 한다

exit code 0 = 전 항목 기대대로. 1 = 하나라도 어긋남.
"""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from d_bus_lib import scan  # noqa: E402

POSITIVES = {
    # (id, JSON 본문) — D-DEF-09 원인형(pretty-print)을 반드시 포함한다
    "FX-POS-1-inline-array": '{"ticket_id":"FX-POS-1-inline-array","from":"A","to":["A","D"],"type":"DIRECTIVE","priority":"P0"}',
    "FX-POS-2-pretty-array": (
        '{\n  "ticket_id": "FX-POS-2-pretty-array",\n  "from": "A",\n'
        '  "to": [\n    "B",\n    "D"\n  ],\n  "type": "FINDING",\n  "priority": "P1"\n}'
    ),
    "FX-POS-3-cc-only": '{"ticket_id":"FX-POS-3-cc-only","from":"C","to":["A"],"cc":["D"],"type":"FINDING","priority":"P2"}',
    "FX-POS-4-string-to": '{"ticket_id":"FX-POS-4-string-to","from":"B","to":"D","type":"COMPLETION","priority":"P3"}',
}
NEGATIVES = {
    "FX-NEG-1-other-plane": '{"ticket_id":"FX-NEG-1-other-plane","from":"A","to":["B","C"],"type":"DIRECTIVE","priority":"P0"}',
    "FX-NEG-2-pretty-other": '{\n  "ticket_id": "FX-NEG-2-pretty-other",\n  "to": [\n    "B"\n  ],\n  "from": "A"\n}',
    # 본문에 "D" 라는 글자가 있으나 수신자가 아닌 경우 — 문자열 검색식 구현이면 여기서 걸린다
    "FX-NEG-3-D-in-text": '{"ticket_id":"FX-NEG-3-D-in-text","from":"A","to":["B"],"scope":"D plane 산출 검토","payload":{"note":"D 가 올린 수치"}}',
    "FX-NEG-4-no-to": '{"ticket_id":"FX-NEG-4-no-to","from":"A","type":"FINDING"}',
}
MALFORMED = {
    "FX-BAD-1-truncated": '{"ticket_id":"FX-BAD-1-truncated","to":["D"],',
    "FX-BAD-2-not-object": '["D"]',
    "FX-BAD-3-empty": "",
}


def run_controls() -> dict:
    """control 결과를 dict 로 반환한다. 스캐너가 매 실행마다 호출한다."""
    fails: list[str] = []
    log: list[str] = []
    with tempfile.TemporaryDirectory() as tmp:
        bus = Path(tmp)
        (bus / "tickets").mkdir()
        (bus / "acks").mkdir()
        for name, body in {**POSITIVES, **NEGATIVES, **MALFORMED}.items():
            (bus / "tickets" / f"{name}.json").write_text(body, encoding="utf-8")
        # positive 하나는 ACK 된 상태로 둬서 acked 판정도 함께 본다
        (bus / "acks" / "FX-POS-1-inline-array.D.json").write_text('{"kind":"ACK"}', encoding="utf-8")

        r = scan(bus, "D")
        found = {row["id"] for row in r["rows"]}
        errs = {e["file"] for e in r["parse_errors"]}
        log.append(f"n_scanned={r['n_scanned']} found={len(found)} parse_errors={len(errs)}")

        # 1) known_positive — 전부 검출
        for pid in POSITIVES:
            if pid in found:
                log.append(f"  OK   positive 검출: {pid}")
            else:
                fails.append(f"positive 미검출: {pid}")
                log.append(f"  FAIL positive 미검출: {pid}")

        # 2) known_negative — 하나도 검출되면 안 된다
        for nid in NEGATIVES:
            if nid not in found:
                log.append(f"  OK   negative 미검출(정상): {nid}")
            else:
                fails.append(f"negative 과탐: {nid}")
                log.append(f"  FAIL negative 과탐: {nid}")

        # 3) malformed — 조용히 0건이 아니라 명시적 오류로
        for bid in MALFORMED:
            if f"{bid}.json" in errs:
                log.append(f"  OK   malformed 가 parse_errors 로 보고됨: {bid}")
            else:
                fails.append(f"malformed 가 조용히 무시됨: {bid}")
                log.append(f"  FAIL malformed 가 조용히 무시됨: {bid}")

        # 4) 부수 계약 — ACK 상태 판정
        acked = {row["id"] for row in r["rows"] if row["acked"]}
        if acked == {"FX-POS-1-inline-array"}:
            log.append("  OK   ACK 상태 판정 정확")
        else:
            fails.append(f"ACK 판정 불일치: {acked}")
            log.append(f"  FAIL ACK 판정 불일치: {acked}")

        # 5) 핵심 계약 — parse_errors 가 있으면 '받을 것이 없음' 과 절대 같지 않아야 한다
        if r["parse_errors"]:
            log.append("  OK   parse_errors 비어 있지 않음 — 빈 결과와 구분 가능")
        else:
            fails.append("parse_errors 가 비었다 — 깨진 파일이 있는데도 정상처럼 보인다")

    return {
        "verdict": "PASS" if not fails else "INVALID",
        "positive": {"expected": len(POSITIVES),
                     "detected": sum(1 for x in log if x.startswith("  OK   positive"))},
        "negative": {"expected": len(NEGATIVES),
                     "not_detected": sum(1 for x in log if x.startswith("  OK   negative"))},
        "malformed": {"expected": len(MALFORMED),
                      "reported": sum(1 for x in log if x.startswith("  OK   malformed"))},
        "failures": fails,
        "log": log,
    }


def main() -> int:
    r = run_controls()
    print("\n".join(r["log"]))
    print()
    if r["verdict"] != "PASS":
        print(f"SELFTEST INVALID — {len(r['failures'])}건")
        for x in r["failures"]:
            print("  -", x)
        return 1
    print("SELFTEST PASS — positive 4/4 검출 · negative 4/4 미검출 · malformed 3/3 명시 오류")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
