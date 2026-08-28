#!/usr/bin/env bash
# [D-DEF-87] **커밋 전 게이트.** 이 세션에서 두 번, 검사 FAIL 을 보고도 커밋·푸시했다.
# 한 번은 실행 루프가 무조건 "검사 통과" 를 찍어서, 한 번은 확인과 커밋이 다른
# 명령이라 그냥 지나가서. 규율로 안 되므로 **명령 하나로 만든다.**
#
#   bash tools/d_precommit.sh && git commit ... && git push ...
#
# 실패가 하나라도 있으면 **비영 종료** — `&&` 사슬이 끊긴다.
set -u
PY=/home/sieg/projects-wsl/ProjectFinal/.venv/bin/python
cd "$(dirname "$0")/.." || exit 4
fail=0
for t in mlflow_contract d_tool_health d_exit d_emit_ticket d_ticket_schema_check \
         d_surface_coverage d_ledger_shape d_input_integrity d_warn_baseline \
         d_retractions d_coverage d_pending_response d_bus_scan_selftest; do
  if ! "$PY" "tools/$t.py" >/dev/null 2>&1; then
    echo "  FAIL  tools/$t.py"
    fail=1
  fi
done
# 스캔 자신의 구문 — `.sh` 라 위 목록에 안 잡힌다 [D-DEF-84]
if ! "$PY" -c "
import sys; sys.path.insert(0,'tools')
from d_tool_health import embedded_python_syntax as e
r = e()
raise SystemExit(0 if r['verdict'] == 'PASS' else 1)
" 2>/dev/null; then
  echo "  FAIL  d_bus_scan.sh 헤레독 구문"
  fail=1
fi
if [ "$fail" -eq 0 ]; then
  echo "게이트 통과 — 커밋해도 된다"
  exit 0
fi
echo "**게이트 실패 — 커밋하지 마라**"
exit 1
