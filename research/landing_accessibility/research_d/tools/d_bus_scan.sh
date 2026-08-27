#!/usr/bin/env bash
# D bus scan — 5분 loop의 1단계. D 앞으로 온 새 티켓과 미ACK 티켓을 찾는다.
set -uo pipefail
BUS=/home/sieg/projects-wsl/ProjectFinal/.agent_bus/landing_v2
echo "=== D 수신 티켓 (to에 D 포함) ==="
for f in "$BUS"/tickets/*.json; do
  if grep -qE '"to"\s*:\s*(\[[^]]*"D"[^]]*\]|"D")' "$f"; then
    id=$(basename "$f" .json)
    ack=$([ -f "$BUS/acks/$id.D.json" ] && echo ACKED || echo "** UNACKED **")
    typ=$(grep -oE '"type"\s*:\s*"[A-Z_]+"' "$f" | head -1 | cut -d'"' -f4)
    prio=$(grep -oE '"priority"\s*:\s*"P[0-4]"' "$f" | head -1 | cut -d'"' -f4)
    echo "$id  $typ  $prio  $ack"
  fi
done
echo
echo "=== cc에 D가 있는 티켓 ==="
grep -lE '"cc"\s*:\s*\[[^]]*"D"' "$BUS"/tickets/*.json 2>/dev/null | xargs -r -n1 basename
echo
echo "=== 최근 event_log 5줄 ==="
tail -5 "$BUS/event_log.jsonl"
