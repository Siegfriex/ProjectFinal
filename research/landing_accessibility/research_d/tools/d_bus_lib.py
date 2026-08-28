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
            # [A STEP1-037] 예전에는 파싱 실패를 `a = {}` 로 삼켜서 **읽지 못한
            # ACK 가 `ACKED_SHA_UNRECORDED`(구식 ACK — 알려진 양성 상태)로
            # 보고**됐다. 미독해와 부재는 다른 사건이다.
            a = None
            try:
                a = json.loads(ack_p.read_text(encoding="utf-8"))
            except Exception:
                pass
            if a is None:
                ack_state = "ACK_UNREADABLE"             # 통과로 읽지 마라
                rec = None
            else:
                rec = a.get("ticket_sha256")
            if a is None:
                pass
            elif rec is None:
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
            # `ACK_UNREADABLE` 은 acked 가 아니다 — 읽지 못한 것을 처리됨으로 세지 않는다
            "acked": ack_state in ("ACKED", "ACKED_SHA_UNRECORDED"),
            "ack_state": ack_state,
            "ticket_sha256": cur_sha,
            "expects": d.get("expected_response", "-"),
        })
    rows.sort(key=lambda r: (str(r["prio"]), str(r["id"])))
    return {"rows": rows, "parse_errors": parse_errors, "n_scanned": len(tickets)}


# ─────────────────────────────────────────────────────────────────────
# [R60] event_log 읽기 — A 의 T-A-V3-STEP1-042
#
# 공유 event_log 는 네 조합을 섞어 쓴다. **한 가정으로 읽으면 나머지가 조용히
# 빠진다** — D 가 실제로 988행 중 287행을 'actor 누락' 으로 읽었다.
# A 판정: 쓰기 정본은 `ts`+`actor`, **읽기는 네 조합 전부** 처리하고
# 어느 매핑에도 안 걸린 행은 **`UNPARSED` 로 따로 센다**(Δ54-R54).
# 못 읽은 것을 0 으로 세지 않는다.
TS_KEYS    = ("ts", "at", "at_kst", "timestamp")
ACTOR_KEYS = ("actor", "agent", "plane")


def normalize_event(rec: dict) -> dict:
    """한 행을 정규화한다. 어느 키도 못 찾으면 그 필드는 `None` 이고
    `unparsed` 가 True 다 — **빈 값과 못 읽음을 구분한다.**"""
    tk = next((k for k in TS_KEYS if rec.get(k)), None)
    ak = next((k for k in ACTOR_KEYS if rec.get(k)), None)
    return {"ts": rec.get(tk) if tk else None,
            "actor": rec.get(ak) if ak else None,
            "event": rec.get("event"), "ticket_id": rec.get("ticket_id"),
            "ts_key": tk, "actor_key": ak,
            "unparsed": (tk is None or ak is None),
            "raw": rec}


def read_event_log(path) -> dict:
    """정규화된 행 + **조합 분포 + UNPARSED + JSON 파싱 실패**를 함께 낸다."""
    from collections import Counter
    p = Path(path)
    if not p.exists():
        return {"rows": [], "n": 0, "unparsed": None, "json_errors": None,
                "combos": {}, "note": "LOG_MISSING — 0 이 아니라 판정 불가"}
    rows, json_errors = [], 0
    for line in p.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            rows.append(normalize_event(json.loads(line)))
        except Exception:                                   # noqa: BLE001
            json_errors += 1
    combos = Counter((r["ts_key"] or "NONE", r["actor_key"] or "NONE") for r in rows)
    return {"rows": rows, "n": len(rows),
            "unparsed": sum(1 for r in rows if r["unparsed"]),
            "json_errors": json_errors,
            "combos": {f"{a}+{b}": c for (a, b), c in sorted(combos.items())},
            "canonical_write_schema": "ts+actor (R60)"}


def read_event_log_controls() -> dict:
    """must_flag / must_not_flag — **네 조합은 읽혀야 하고, 미지 모양은 UNPARSED 로 세야 한다.**

    이 통제가 없으면 '정규화했다' 는 주장이 검증되지 않는다. 특히
    미지 모양을 조용히 통과시키면 R60 이 요구한 구분이 사라진다.
    """
    must_not_flag = [                       # 네 조합 — 전부 읽혀야 한다
        {"ts": "T", "actor": "A", "event": "X"},
        {"ts": "T", "agent": "B", "event": "X"},
        {"at": "T", "actor": "C", "event": "X"},
        {"at_kst": "T", "plane": "A", "event": "X"},
    ]
    must_flag = [                           # 미지 모양 — UNPARSED 여야 한다
        {"when": "T", "who": "Z", "event": "X"},
        {"ts": "T", "event": "X"},                       # 주체 없음
        {"actor": "A", "event": "X"},                    # 시각 없음
    ]
    ok_not = [not normalize_event(r)["unparsed"] for r in must_not_flag]
    ok_yes = [normalize_event(r)["unparsed"] for r in must_flag]
    return {"must_not_flag_read": f"{sum(ok_not)}/{len(ok_not)}",
            "must_flag_unparsed": f"{sum(ok_yes)}/{len(ok_yes)}",
            "passed": all(ok_not) and all(ok_yes),
            "why": "네 조합 전부 읽고, 미지 모양은 UNPARSED 로 분리한다 (R60)"}
