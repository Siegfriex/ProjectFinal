#!/usr/bin/env bash
# [D-DEF-87/90] **커밋 전 게이트.**
#
#   bash tools/d_precommit.sh && git commit ... && git push ...
#
# 실패가 하나라도 있으면 **비영 종료** — `&&` 사슬이 끊긴다.
#
# 대상 목록은 **계산한다**(A R62): 루프에서 도는 도구 중 대조군 정의가 있는 것.
# 손 목록이었을 때 `d_mlflow_contract_audit` 가 빠져 있었고, 그 모듈은 controls
# FAIL 에 exit 1 을 내는데 게이트가 부르지 않아 조용했다.
#
# **`__main__` 을 돌리지 않는다.** 계산된 목록에는 `d_v3_census`·`d_mlflow`·
# `d_input_firewall` 처럼 실행하면 산출을 쓰거나 run 을 만드는 것이 섞인다 —
# 게이트가 상태를 바꾸면 안 된다. **`controls()` 만 부른다.**
set -u
PY=/home/sieg/projects-wsl/ProjectFinal/.venv/bin/python
cd "$(dirname "$0")/.." || exit 4
"$PY" - <<'PYEOF'
import importlib
import sys
import traceback

sys.path.insert(0, "tools")
from d_tool_health import static_control_presence, embedded_python_syntax

rows = static_control_presence()["rows"]
mods = sorted(x["module"] for x in rows
              if x.get("in_loop") and x.get("has_control_def"))
if not mods:
    print("  FAIL  게이트 대상 목록이 비었다 — **빈 목록은 통과가 아니다**")
    raise SystemExit(4)

# **알려진 실패** — 이유와 날짜를 적는다. 초록불을 만들려고 두는 것이 아니라
# **새 실패와 가르기 위해** 둔다. 새 모듈이 실패하면 게이트는 여전히 막는다.
GATE_BASELINE = {
    "d_v3_bundle_check": (
        "2026-08-28 — `D code sha 기록 == 실제 파일` 이 어긋난다. 이 세션에 검사 도구 4개"
        "(`d_ticket_schema_check` `d_tool_health` `d_input_integrity` `d_warn_baseline`)를 "
        "고쳤고, v3 REPORT_BUNDLE 은 **동결 시점의 code sha** 를 적어 두었다. "
        "**번들은 A 의 동결 산출물이라 D 가 고치지 않는다** — 기록을 맞추면 provenance 를 "
        "위조하는 것이다. `D-V3-FINDING-083` 으로 A 판정을 요청했다"),
}

fail = 0
for m in mods:
    try:
        mod = importlib.import_module(m)
    except Exception:                               # noqa: BLE001
        print(f"  FAIL  {m} — 임포트 실패")
        traceback.print_exc(limit=1)
        fail = 1
        continue
    # [D-DEF-90] 이름 목록을 손으로 쓰지 않는다 — `d_v3_census` 의 대조군은
    # `contract_controls` 라서 손 목록에 안 걸렸다. **AST 가 찾은 이름**을 쓴다.
    names = next((x.get("defs") or [] for x in rows if x["module"] == m), [])
    fn = next((getattr(mod, n) for n in names
               if callable(getattr(mod, n, None))), None)
    if fn is None:
        print(f"  FAIL  {m} — 대조군 정의가 있다고 했는데 부를 수 없다")
        fail = 1
        continue
    try:
        r = fn()
    except Exception as e:                          # noqa: BLE001
        print(f"  FAIL  {m}.{fn.__name__}() — 실행 실패: {type(e).__name__}: {e}")
        fail = 1
        continue
    v = (r or {}).get("verdict")
    if v not in ("PASS", "INFO"):
        if m in GATE_BASELINE:
            print(f"  (알려진 실패) {m} = {v}  {(r or {}).get('failed')}")
            print(f"      {GATE_BASELINE[m]}")
        else:
            print(f"  FAIL  {m}.{fn.__name__}() = {v}  {(r or {}).get('failed')}")
            fail = 1
    elif m in GATE_BASELINE:
        # **알려진 실패가 사라지면 목록에서 빼라** — 손 목록은 썩는다(A R62)
        print(f"  ** 목록 썩음 ** {m} 은 이제 통과한다 — GATE_BASELINE 에서 빼라")
        fail = 1

# `.sh` 라 위 목록에 안 잡힌다 [D-DEF-84]
eps = embedded_python_syntax()
if eps.get("verdict") != "PASS":
    print(f"  FAIL  d_bus_scan.sh 헤레독 구문 : {eps.get('verdict')} {eps.get('errors')}")
    fail = 1

print(f"대상 {len(mods)}개 · 헤레독 1")
raise SystemExit(1 if fail else 0)
PYEOF
rc=$?
if [ "$rc" -eq 0 ]; then
  echo "게이트 통과 — 커밋해도 된다"
else
  echo "**게이트 실패 — 커밋하지 마라**"
fi
exit "$rc"
