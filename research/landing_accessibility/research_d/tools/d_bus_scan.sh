#!/usr/bin/env bash
# D bus scan — D 앞으로 온 티켓과 미ACK 티켓을 찾는다.
#
# [D-DEF-09 시정] 이전 판본은 grep 으로 `"to": [... "D" ...]` 를 한 줄에서만 찾았다.
# 버스 티켓 대부분이 pretty-print 라 `"to"` 와 `"D"` 가 다른 줄에 있어 매칭되지 않았고,
# 그 결과 P0 4건·P1 4건을 포함한 14건이 스캔에서 사라진 채 "새 티켓 없음" 으로 보였다.
# JSON 을 파싱해서 판정한다. cc 도 같은 방식으로 본다.
set -uo pipefail
BUS=/home/sieg/projects-wsl/ProjectFinal/.agent_bus/landing_v2
PY=/home/sieg/projects-wsl/ProjectFinal/.venv/bin/python

"$PY" - "$BUS" <<'PY'
import json, glob, os, sys
BUS = sys.argv[1]
rows = []
for f in sorted(glob.glob(BUS + "/tickets/*.json")):
    try:
        d = json.load(open(f))
    except Exception as e:
        print(f"  !! 파싱 실패 {os.path.basename(f)}: {e}")
        continue
    to = d.get("to") or []
    cc = d.get("cc") or []
    to = [to] if isinstance(to, str) else list(to)
    cc = [cc] if isinstance(cc, str) else list(cc)
    if "D" not in to and "D" not in cc:
        continue
    tid = d.get("ticket_id") or os.path.basename(f)[:-5]
    acked = os.path.exists(f"{BUS}/acks/{tid}.D.json")
    rows.append({
        "prio": d.get("priority", "-"), "id": tid, "type": d.get("type", "-"),
        "from": d.get("from", "-"), "chan": "to" if "D" in to else "cc",
        "ack": "ACKED" if acked else "** UNACKED **",
        "expects": d.get("expected_response", "-"), "at": d.get("created_at", "-"),
    })
rows.sort(key=lambda r: (r["prio"], r["id"]))
print(f"=== D 수신 티켓 {len(rows)}건 (to+cc) ===")
for r in rows:
    print("  {prio:<3} {id:<34} {type:<20} from={from:<3} {chan:<3} "
          "expects={expects:<9} {ack}".format(**r))
un = [r for r in rows if "UNACKED" in r["ack"]]
print(f"\n=== 미ACK {len(un)}건 "
      f"(P0 {sum(1 for r in un if r['prio']=='P0')} · "
      f"P1 {sum(1 for r in un if r['prio']=='P1')}) ===")
for r in un:
    print("  {prio:<3} {id:<34} {type:<20} expects={expects}".format(**r))
PY

echo
echo "=== 최근 event_log 5줄 ==="
tail -5 "$BUS/event_log.jsonl"
