"""D bus scan 의 수신 판정 로직 — 스캐너와 self-test 가 **같은 함수**를 쓴다.

[T-A-V3-P0-D-001] D-DEF-09 는 시정됐으나 "다시 깨져도 알아채는 장치" 가 없었다.
테스트가 로직 사본을 검사하면 사본만 통과하고 진짜 스캐너는 깨질 수 있으므로,
판정을 여기 한 곳에 두고 d_bus_scan.sh 와 d_bus_scan_selftest.py 가 이것만 호출한다.

핵심 계약: **파싱 실패는 조용히 0건이 되지 않는다.** parse_errors 로 올라오고
호출자는 그것을 비어 있지 않게 취급해야 한다. 빈 결과와 정상이 구분되지 않으면
스캐너는 검증 도구가 아니다.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path


RECIPIENT_FIELDS = ("to", "cc")


def _as_list(v) -> list[str]:
    if v is None:
        return []
    if isinstance(v, str):
        return [v]
    if isinstance(v, list):
        return [x for x in v if isinstance(x, str)]
    return []


def scan(bus_dir: str | Path, plane: str = "D") -> dict:
    """bus_dir/tickets/*.json 에서 plane 앞으로 온 티켓을 찾는다.

    반환: {"rows": [...], "parse_errors": [{"file","error"}], "n_scanned": int}
    rows 각 항목: ticket_id / priority / type / from / channel(to|cc) / acked / expects
    """
    bus = Path(bus_dir)
    tickets = sorted((bus / "tickets").glob("*.json"))
    rows, parse_errors = [], []
    for f in tickets:
        try:
            d = json.loads(f.read_text(encoding="utf-8"))
        except Exception as e:                       # 조용히 넘기지 않는다
            parse_errors.append({"file": f.name, "error": f"{type(e).__name__}: {e}"})
            continue
        if not isinstance(d, dict):
            parse_errors.append({"file": f.name, "error": "최상위가 object 가 아니다"})
            continue
        to, cc = _as_list(d.get("to")), _as_list(d.get("cc"))
        if plane not in to and plane not in cc:
            continue
        tid = d.get("ticket_id") or f.name[:-5]
        # [D-DEF-13] ACK 은 "그때 그 내용" 에 대한 것이다. 티켓이 사후에 덮이면
        # ACK 파일 존재만 보는 판정은 새 내용을 영원히 ACKED 로 숨긴다.
        # ACK 에 기록된 ticket_sha256 과 현재 파일 해시를 대조한다.
        cur_sha = hashlib.sha256(f.read_bytes()).hexdigest()
        ack_p = bus / "acks" / f"{tid}.{plane}.json"
        if not ack_p.exists():
            ack_state = "UNACKED"
        else:
            try:
                a = json.loads(ack_p.read_text(encoding="utf-8"))
            except Exception:
                a = {}
            rec = a.get("ticket_sha256")
            if rec is None:
                ack_state = "ACKED_SHA_UNRECORDED"       # 옛 ACK — 대조 불가
            elif rec == cur_sha:
                ack_state = "ACKED"
            else:
                ack_state = "CONTENT_CHANGED_AFTER_ACK"  # 재ACK 필요
        rows.append({
            "id": tid,
            "prio": d.get("priority", "-"),
            "type": d.get("type", "-"),
            "from": d.get("from", "-"),
            "chan": "to" if plane in to else "cc",
            "acked": ack_state in ("ACKED", "ACKED_SHA_UNRECORDED"),
            "ack_state": ack_state,
            "ticket_sha256": cur_sha,
            "expects": d.get("expected_response", "-"),
        })
    rows.sort(key=lambda r: (str(r["prio"]), str(r["id"])))
    return {"rows": rows, "parse_errors": parse_errors, "n_scanned": len(tickets)}
