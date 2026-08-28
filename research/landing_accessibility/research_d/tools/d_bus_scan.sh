#!/usr/bin/env bash
# D bus scan — D 앞으로 온 티켓과 미ACK 티켓을 찾는다.
#
# 판정 로직은 tools/d_bus_lib.py 에 있고 self-test 가 **같은 함수**를 검사한다
# (tools/d_bus_scan_selftest.py, T-A-V3-P0-D-001). 여기서 로직을 복제하지 않는다.
# parse_errors 가 하나라도 있으면 exit 2 로 끝난다 — 깨진 파일이 '받을 것 없음'으로
# 보이면 D-DEF-09 가 재발한다.
set -uo pipefail
BUS=/home/sieg/projects-wsl/ProjectFinal/.agent_bus/landing_v2
PY=/home/sieg/projects-wsl/ProjectFinal/.venv/bin/python
RD="$(cd "$(dirname "$0")/.." && pwd)"

"$PY" - "$BUS" "$RD" <<'PYEOF'
import sys
sys.path.insert(0, f"{sys.argv[2]}/tools")
from d_bus_lib import scan, RECIPIENT_FIELDS
from d_bus_scan_selftest import run_controls

# [Director P0 1.1] control 을 매 실행마다 먼저 돌린다.
# control PASS 없이 "0건" 을 CLEAN 으로 읽지 않는다.
ctl = run_controls()
print(f"=== scanner control ===")
print(f"  verdict          : {ctl['verdict']}")
print(f"  positive control : {ctl['positive']['detected']}/{ctl['positive']['expected']} 검출")
print(f"  negative control : {ctl['negative']['not_detected']}/{ctl['negative']['expected']} 미검출(과탐 0)")
print(f"  malformed control: {ctl['malformed']['reported']}/{ctl['malformed']['expected']} 명시 오류")
# --- D 자기 발행분 **스키마 정본** 상주 감사 (D-DEF-47) ---
# 발행 도구를 우회해 손으로 티켓을 쓰면 도구의 가드가 무의미하다.
# 그래서 **사후 스캔**을 매 루프에 붙인다 — 우회해도 다음 스캔에서 보인다.
try:
    from d_ticket_schema_check import check as _schema_check
    _sc = _schema_check()
    print(f"\n=== D 발행분 스키마(SSOTV3 정본) : {_sc['verdict']} "
          f"· 위반 {_sc['n_violations']} ===")
    if _sc["by_field"]:
        for _k, _v in sorted(_sc["by_field"].items(), key=lambda x: -x[1]):
            print(f"   {_v:>3}  {_k}")
        print("   (v3 이전 발행분은 대상 아님 — 소급하지 않는다. 발행분은 고치지 않는다)")
except Exception as _e:
    print(f"\n=== D 발행분 스키마 : 검사 실패 {_e} ===")
    errs.append({"file": "(D 발행분 스키마)", "error": f"스키마 감사 실행 실패: {_e}"})

# --- D 자기 발행분 base_sha 상주 감사 (Δ26 / T-A-V3-STEP1-024) ---
try:
    from d_emit_ticket import audit_emitted
    au = audit_emitted()
    print(f"\n=== D 발행분 base_sha ({au['v3_era']} v3-era / {au['n']}) : {au['verdict']} ===")
    for r in au["v3_era_non_resolving"]:
        print(f"   {r['state']:<9} {r['file']}")
    if au["verdict"] != "PASS":
        errs.append({"file": "(D 발행분)", "error": "v3 이후 base_sha 해석 불가"})
except Exception as _e:
    print(f"\n=== D 발행분 base_sha : 검사 실패 {_e} ===")
    errs.append({"file": "(D 발행분)", "error": f"base_sha 감사 실행 실패: {_e}"})

if ctl["verdict"] != "PASS":
    print("  !! SCANNER VERDICT INVALID — 아래 결과를 신뢰하지 마라")
    for x in ctl["failures"]:
        print("     -", x)
print()

r = scan(sys.argv[1], "D")
print(f"=== scan provenance ===")
print(f"  input path     : {sys.argv[1]}/tickets/*.json")
print(f"  parser         : json.loads (d_bus_lib.scan)")
print(f"  recipient field: {RECIPIENT_FIELDS}")
print()
rows, errs = r["rows"], r["parse_errors"]
print(f"=== D 수신 티켓 {len(rows)}건 (to+cc) · 스캔 {r['n_scanned']}파일 ===")
for x in rows:
    print("  {prio:<3} {id:<34} {type:<20} from={from:<3} {chan:<3} expects={expects:<9} {ack}".format(
        ack={"ACKED":"ACKED","ACKED_SHA_UNRECORDED":"ACKED(sha 미기록)",
             "CONTENT_CHANGED_AFTER_ACK":"** 내용변경 재ACK필요 **","UNACKED":"** UNACKED **"}[x["ack_state"]], **x))
un = [x for x in rows if not x["acked"]]
changed = [x for x in rows if x["ack_state"] == "CONTENT_CHANGED_AFTER_ACK"]
nosha = [x for x in rows if x["ack_state"] == "ACKED_SHA_UNRECORDED"]
print(f"\n=== 미ACK {len(un)}건 (P0 {sum(1 for x in un if x['prio']=='P0')} · "
      f"P1 {sum(1 for x in un if x['prio']=='P1')}) ===")
for x in un:
    print("  {prio:<3} {id:<34} {type:<20} expects={expects}".format(**x))
print(f"\n=== matched ticket ids ({len(rows)}) ===")
print("  " + (", ".join(x["id"] for x in rows) if rows else "(없음)"))
print(f"\n=== parse errors ({len(errs)}) ===")
for e in errs:
    print(f"   {e['file']}: {e['error']}")
if not errs:
    print("   (없음)")

if ctl["verdict"] != "PASS":
    sys.exit(3)          # control 실패 — 결과 자체가 무효
if errs:
    sys.exit(2)          # 파싱 실패는 조용히 넘기지 않는다
PYEOF
rc=$?

echo
echo "=== 최근 event_log 5줄 ==="
tail -5 "$BUS/event_log.jsonl"
exit $rc
