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
# 지금은 비어 있어 신호로 안 잡히지만 **생기면 표시돼야 한다** — 빈 값은 나중에 조용해진다
for _f in (ctl.get("failures") or []):
    print(f"  ** control 실패 ** {_f}")
# --- D 발행분 응답 대기 · 평면 생존 (D-DEF-64) ---
# **티켓 발행 ≠ 전달.** D 는 매 회차 "A 판정 대기 · C 검산 대기" 라고 적으면서
# 그 대기가 유효한지 재지 않았다. 발행은 세고 응답은 안 셌다.
try:
    from d_pending_response import check as _pr
    _p = _pr()
    _pen, _liv = _p["pending"], _p["liveness"]
    print(f"\n=== D 발행분 응답 대기 : 실대기 {_pen['n_live']}건 "
          f"{_pen['by_priority_live']} {_pen['by_to']} · 최장 {_pen['oldest_minutes']}분 "
          f"· 판본만료 {_pen['n_stale_mart']} ===")
    for _sm in _pen["stale_mart_pin"]:
        print(f"   판본만료 {_sm['priority']} {_sm['ticket']} — **응답 대기가 아니다**")
    for _dr in _pen["decision_requests"]:
        print(f"   ** DECISION ** {_dr['ticket']}  to={_dr['to']}  {_dr['minutes_ago']}분")
    print("   평면 마지막 활동: " + " · ".join(
        f"{k} {v['minutes_ago']}분" for k, v in _liv.items()))
    print("   (생존은 heartbeat 와 최근 발행 중 **늦은 것** — A 는 heartbeat 를 안 쓴다)")
except Exception as _e:
    print(f"\n=== D 발행분 응답 대기 : 검사 실패 {_e} ===")
    errs.append({"file": "(응답 대기)", "error": f"검사 실행 실패: {_e}"})

# --- 대장 두 분류 정합 (D-DEF-69) ---
# 발행 전에 잡은 것은 `entries` 필드가 아니라 `caught_pre_emission` 리스트에
# 들어간다 — **서수가 거기서 나온다**(R59). 6건이 빠져 있었다.
try:
    from d_ledger_shape import check as _ls
    _l = _ls()
    print(f"\n=== 대장 두 분류 : {_l['verdict']} · entries {_l.get('n_entries')} "
          f"· caught_pre_emission {_l.get('n_caught_pre_emission')} ===")
    for _m in (_l.get("not_in_list") or []):
        print(f"   ** 리스트 미반영 ** {_m['id']} {_m['keys']}")
except Exception as _e:
    print(f"\n=== 대장 두 분류 : 검사 실패 {_e} ===")
    errs.append({"file": "(대장 두 분류)", "error": f"검사 실행 실패: {_e}"})

# --- coverage 교차 일치 (D-DEF-68) ---
# 같은 축을 **세 곳**이 계산한다 — d_coverage · T3 표 · C 의 ANALYSIS_ASSURED.
# 갈라지면 아무도 모른다. C 값이 달라지면 그것도 신호다(C 가 재계산했다).
try:
    from d_citation_check import coverage_agreement as _ca
    _cg = _ca()
    print(f"\n=== coverage 교차 일치 : {_cg['verdict']} · 축 {_cg['n_axes']} "
          f"· 불일치 {len(_cg['disagree'])} ===")
    for _r in _cg["disagree"]:
        print(f"   {_r['axis']}: {_r['values']}")
    for _ms in _cg["missing_sources"]:
        print(f"   ** 원천 없음 ** {_ms}")
except Exception as _e:
    print(f"\n=== coverage 교차 일치 : 검사 실패 {_e} ===")
    errs.append({"file": "(교차 일치)", "error": f"검사 실행 실패: {_e}"})

# --- MLflow 계약 사후 감사 (D-DEF-61) ---
# `mlflow_contract` 는 발행 전 차단만 있었다. 도구를 우회해 `start_run()` 을
# 직접 부르면 계약 없는 run 이 남고 아무도 모른다. **두 계약이 별개**다 —
# A 계약(접두 없음, LA_* 실험) · D 자체(`d.` 접두, D_v21 실험).
try:
    from d_mlflow_contract_audit import audit as _ma
    _m = _ma()
    _o = _m.get("d_own") or {}
    _ac = _m.get("accounting") or {}
    print(f"\n=== MLflow 계약 : A {_m.get('verdict')}(위반 {_m.get('n_violating_new','?')}) "
          f"· D자체 {_o.get('verdict')}(위반 {_o.get('n_violating','?')}) "
          f"· 회계 {_ac.get('verdict')}({_ac.get('total_runs','?')} run, 미귀속 "
          f"{(_ac.get('buckets') or {}).get('unaccounted', 0)}) ===")
    if _m.get("verdict") == "NO_SERVER":
        print("   서버 없음 — **통과가 아니다.** 재기동 후 다시 잰다")
except Exception as _e:
    print(f"\n=== MLflow 계약 : 검사 실패 {_e} ===")
    errs.append({"file": "(mlflow 계약)", "error": f"감사 실행 실패: {_e}"})

# --- 방화벽 FAIL 내역 (D-DEF-57) ---
# `holdout_accessed=UNVERIFIED_SCAN_NOT_PASS` 만 보고 **FAIL 개수와 내역을 보지
# 않았다.** D 가 D-DEF-54 시정에서 FAIL 을 1 → 3 으로 늘렸는데 세 회차 동안
# "control/v3 경로 상수 건" 이라고 **단수로** 보고했다. 숫자를 노출한다.
# **파일이 없으면 조용히 넘어가지 않는다.** 첫 판은 `__file__`(= `<stdin>`)로
# 경로를 잡아 `exists()` 가 False 였고 **아무 줄도 찍지 않았다** — 이 스캔이
# 반복해 잡아온 "조용한 통과" 를 그대로 만들었다. 경로는 `sys.argv[2]`(RD) 다.
try:
    import json as _j
    from pathlib import Path as _P
    _fw = _P(sys.argv[2]) / "results" / "D_INPUT_FIREWALL_VERIFICATION.json"
    if not _fw.exists():
        print(f"\n=== 방화벽 : **산출 없음** — {_fw} ===")
        errs.append({"file": "(방화벽)", "error": f"스캔 산출이 없다: {_fw}"})
    else:
        _d = _j.loads(_fw.read_text(encoding="utf-8"))
        _f = [v for v in (_d.get("violations") or []) if v.get("severity") == "FAIL"]
        print(f"\n=== 방화벽 : {_d.get('verdict')} · FAIL {_d.get('fail_count')} "
              f"· WARN {_d.get('warn_count')} ===")
        for _v in _f:
            print(f"   {_v.get('file')}:{_v.get('line')}  {_v.get('reference')}")
        # [D-DEF-59] **총수는 신호가 아니다** — 새 토큰·새 경로만 본다
        try:
            from d_warn_baseline import check as _wb
            _w = _wb()
            # [D-DEF-77] 라벨이 "종류"인데 총수를 찍고 있었다 — 그 검사 스스로
            # "총수는 신호가 아니다"라고 한다. **종류를 앞에 두고 총수는 괄호로 내린다.**
            _kn, _kb = _w.get('n_kinds_now'), _w.get('n_kinds_base')
            _kd = (_kn - _kb) if (_kn is not None and _kb is not None) else None
            print(f"   WARN 종류 : {_w['verdict']} · **종류 {_kn}** (baseline {_kb}, Δ{_kd}) "
                  f"· 총수 {_w.get('n_now')}(Δ{_w.get('delta')} — **신호 아님**)")
            if _w.get("new_references"):
                print(f"     ** 새 토큰 ** {_w['new_references']}")
            if _w.get("new_top_paths"):
                print(f"     ** 새 경로 ** {_w['new_top_paths']}")
        except Exception as _e2:
            print(f"   WARN 종류 : 검사 실패 {_e2}")
except Exception as _e:
    print(f"\n=== 방화벽 내역 : 읽기 실패 {_e} ===")
    errs.append({"file": "(방화벽)", "error": f"내역 읽기 실패: {_e}"})

# --- D 입력(mart·raw) 무결성 (D-DEF-53) ---
# `production_modified` 는 git diff 로 재는데 `artifacts/` 는 추적 제외라
# **mart·raw 는 그 측정 범위 밖**이다. 여기서 파일별 sha 로 잰다.
try:
    from d_input_integrity import check as _ii
    _i = _ii()
    print(f"\n=== D 입력 무결성(mart·raw) : {_i['verdict']} · {_i.get('n_files','?')} 파일 ===")
    for _ld in (_i.get("living_doc_changed") or []):
        _kd = (_i.get("sidecar_key_delta") or {}).get(_ld) or {}
        _g = len(_kd.get("gained_key_hashes") or [])
        _l = len(_kd.get("lost_key_hashes") or [])
        _rv = len(_kd.get("revalued_key_hashes") or [])
        # [D-DEF-76] `revalued` 를 만들어놓고 **출력에 안 넣었다** — 만든 기능이
        # 보이지 않으면 없는 것과 같다(D-DEF-57 과 같은 형태).
        _bits = []
        if _g:
            _bits.append(f"새 키 {_g}")
        if _l:
            _bits.append(f"사라진 키 {_l}")
        if _rv:
            _bits.append(f"**값 바뀐 키 {_rv}**")
        print(f"   사이드카 갱신 {_ld} — **읽어야 할 것이 생겼다**(FAIL 아님)"
              + (" · " + " · ".join(_bits) if _bits else " · 변화 없음"))
        if _rv:
            print(f"     값 바뀐 키 해시: {(_kd.get('revalued_key_hashes') or [])[:5]}"
                  f"  (원본에서 그 키만 읽으면 된다)")
    if _i["verdict"] == "FAIL":
        print(f"   변경 {_i['n_changed']} · 추가 {_i['n_added']} · 삭제 {_i['n_removed']}")
        for _f in (_i["changed"] + _i["added"] + _i["removed"])[:6]:
            print(f"     {_f}")
        print("   (누가 바꿨는지는 말하지 않는다 — **D 의 입력이 바뀌었다**는 사실이다)")
except Exception as _e:
    print(f"\n=== D 입력 무결성 : 검사 실패 {_e} ===")
    errs.append({"file": "(입력 무결성)", "error": f"무결성 검사 실행 실패: {_e}"})

# --- D 도구 문법 건전성 (D-DEF-50) ---
# `d_presentation_eda.py` 가 syntax error 인 채로 두 회차를 지났다. 검사 7종이
# 전부 exit 0 이었고 **그 파일을 실행하는 검사가 하나도 없었기 때문**이다.
try:
    from d_tool_health import check as _th
    _t = _th()
    from d_tool_health import coverage as _tc
    _c = _tc()
    print(f"\n=== D 도구 문법 : {_t['verdict']} · {_t['ok']}/{_t['n_tools']} "
          f"· 루프 실행 {_c['executed_in_loop']} / 문법만 {_c['syntax_only']} ===")
    from d_tool_health import embedded_python_syntax as _eps_fn
    _eps = _eps_fn()
    print(f"   **스캔 자신의 구문**(헤레독 {_eps.get('n_blocks')}블록) : {_eps.get('verdict')} "
          f"· 오류 {_eps.get('n_errors')} — 깨지면 감사가 **사라진다**(셸은 계속 돈다)")
    for _e8 in (_eps.get("errors") or [])[:3]:
        print(f"     ** {_e8['line_in_file']}행 ** {_e8['msg']}")
    from d_tool_health import static_control_presence as _scp
    _sp = _scp()
    print(f"   대조군 정의(AST, 임포트 안 함) : 루프 {_sp['loop_with']}/{_sp['loop_with']+_sp['loop_without']} "
          f"· 문법만 {_sp['static_with']}/{_sp['static_with']+_sp['static_without']} "
          f"— **존재는 유효가 아니다**")
    if _sp.get("hand_list_only"):
        print(f"     손 목록에만 있는 것 : {_sp['hand_list_only']} "
              f"— 계산된 `covered` 를 쓴다(A R62)")
    if _sp.get("loop_without_names"):
        print(f"     ** 루프인데 대조군 정의 없음 ** {_sp['loop_without_names']}")
    for _b in _t["syntax_error"]:
        print(f"   {_b['tool']}:{_b['line']}  {_b['msg']}")
except Exception as _e:
    print(f"\n=== D 도구 문법 : 검사 실패 {_e} ===")
    errs.append({"file": "(도구 문법)", "error": f"문법 감사 실행 실패: {_e}"})

# --- 철회 라벨 인용 상주 감사 (A R163 / D-DEF-48) ---
# "검사는 CSV 의 값을 보지 그 값이 사람에게 어떻게 읽히는지를 안 본다" (B).
# 철회 사실을 주석·문서에만 두면 아무것도 강제하지 않는다.
try:
    from d_retractions import audit_artifacts as _ra, retracted_tokens as _rt
    from d_retractions import audit_tickets as _rk, audit_superseded as _rs
    _r, _k, _s = _ra(), _rk(), _rs()
    print(f"\n=== 철회 라벨 인용 : 산출물 {_r['verdict']}({_r['n']}) · "
          f"발행티켓 {_k['verdict']}(새 {_k['n_new']} / baseline {_k['baseline_pre_guard']['n']}) "
          f"· 철회토큰 {sorted(_rt())} ===")
    for _f in _r["files"]:
        print(f"   산출물  {_f}")
    for _f in _k["baseline_pre_guard"]["tickets"]:
        print(f"   티켓    {_f}  (차단 이전 발행 — 고칠 수 없다. verdict 를 좌우하지 않음)")
    for _h in _k["new"]:
        print(f"   ** 새 위반 **  {_h['source']}  {_h['token']}")
    if _k["자기신고_시각_불일치"]["n"]:
        print(f"   자기신고 시각 불일치 {_k['자기신고_시각_불일치']['n']}건 "
              f"— 분류는 파일 실제 시각으로 한다")
    if _k["철회_이전_인용"]["n"]:
        print(f"   철회 이전 인용 {_k['철회_이전_인용']['n']}건 — **위반 아님**")
    print(f"   폐기 산출물 인용 : {_s['verdict']}({_s['n']}) · 폐기본 {_s['n_superseded']}")
    for _f in _s["files"]:
        print(f"     경로 없는 인용  {_f}")
except Exception as _e:
    print(f"\n=== 철회 라벨 인용 : 검사 실패 {_e} ===")
    errs.append({"file": "(철회 인용)", "error": f"철회 감사 실행 실패: {_e}"})

# --- D 자기 발행분 **스키마 정본** 상주 감사 (D-DEF-47) ---
# 발행 도구를 우회해 손으로 티켓을 쓰면 도구의 가드가 무의미하다.
# 그래서 **사후 스캔**을 매 루프에 붙인다 — 우회해도 다음 스캔에서 보인다.
# [D-DEF-77] **만든 신호가 표시되는가** — `D-DEF-57`·`D-DEF-76` 이 같은 형태였다.
# 이 검사가 스캔에 안 들어가면 그 자체가 같은 결함이므로 여기에 둔다.
try:
    from d_surface_coverage import check as _surf
    _sf = _surf()
    print(f"\n=== 표시 누락(만든 신호가 안 보이는가) : INFO · 검사 {_sf['n_modules']} "
          f"· 미표시 {_sf['n_unsurfaced']} (판단됨 {_sf['n_unsurfaced'] - _sf['n_unreviewed']} "
          f"/ **미검토 {_sf['n_unreviewed']}**) ===")
    for _u in _sf["unreviewed"]:
        print(f"   ** 미검토 ** {_u['module']}.{_u['key']}")
    for _st in _sf["stale_accepted"]:
        print(f"   ** 목록 썩음 ** {_st['module']}.{_st['key']} — 검사가 더는 내지 않는다")
    print("   (판정이 아니다 — 무엇이 신호인지는 자동으로 정해지지 않는다)")
except Exception as _e9:
    print(f"\n=== 표시 누락 : 검사 실패 {_e9} ===")
    errs.append({"file": "(표시누락)", "error": str(_e9)})

try:
    from d_ticket_schema_check import check as _schema_check
    _sc = _schema_check()
    print(f"\n=== D 발행분 스키마(SSOTV3 정본) : {_sc['verdict']} "
          f"· 새 {_sc['n_new']} / baseline {_sc['baseline_pre_guard']['n']} ===")
    from d_ticket_schema_check import self_approval_record as _sar_fn
    _sar = _sar_fn()
    _sv = _sar.get("**정본에 없는 필드다**") or {}
    print(f"   자기승인 기록 : {_sar['verdict']} · true {_sar['n_true']} "
          f"· false {_sar['n_false']} · **부재 {_sar['n_absent']}**"
          f"(가드 이후 {_sar['n_absent_since_guard']}, 마지막 부재 {_sar['last_absent_at']}) "
          f"· 이상값 {_sar['n_other_value']}")
    print(f"     **정본 스키마에 없는 필드다** — required {_sv.get('in_required')} / "
          f"properties {_sv.get('in_properties')}. 부재는 위반이 아니고, "
          f"true 0 을 정본이 보증하지도 않는다")
    if _sar.get("absent_since_guard"):
        print(f"     ** 가드 이후 부재 ** {_sar['absent_since_guard'][:5]}")
    _au = _sc.get("authority") or {}
    print(f"   권한 축(D 가 낼 수 없는 type) : {'PASS' if _au.get('n') == 0 else 'FAIL'} "
          f"· 위반 {_au.get('n')} "
          f"· 금지 {len(_au.get('forbidden') or [])}종  "
          f"— **스키마와 다른 축이다**(enum 은 전 평면 공용)")
    if _au.get("violations"):
        for _v in _au["violations"][:5]:
            print(f"     ** {_v} **")
    if _sc["by_field"]:
        for _k, _v in sorted(_sc["by_field"].items(), key=lambda x: -x[1]):
            print(f"   {_v:>3}  {_k}")
        print("   (v3 이전은 대상 아님. 차단 이전 발행분은 baseline — "
              "고칠 수 없고 verdict 를 좌우하지 않는다)")
    for _n in _sc["new"]:
        print(f"   ** 새 위반 **  {_n['ticket']}  {_n['missing_required']}{_n['enum_violation']}")
except Exception as _e:
    print(f"\n=== D 발행분 스키마 : 검사 실패 {_e} ===")
    errs.append({"file": "(D 발행분 스키마)", "error": f"스키마 감사 실행 실패: {_e}"})

# --- D 자기 발행분 base_sha 상주 감사 (Δ26 / T-A-V3-STEP1-024) ---
try:
    from d_emit_ticket import audit_emitted
    au = audit_emitted()
    print(f"\n=== D 발행분 base_sha ({au['v3_era']} v3-era / {au['n']}) : {au['verdict']} ===")
    _er = au.get("emission_record") or {}
    print(f"   발행기록(event_log 대조) : {_er.get('verdict')} · 기록 있음 {_er.get('n_with_record')} "
          f"· **새 누락 {_er.get('n_missing_new')}** · baseline 누락 {_er.get('n_missing_baseline')} "
          f"· created_at 없음 {_er.get('n_no_created_at')}")
    _lnf = _er.get("logged_no_file_other_planes") or {}
    print(f"     반대 방향(로그에만 있고 파일 없음) : D **{_er.get('n_logged_no_file_D')}** "
          f"· 다른 평면 { {k: len(v) for k, v in _lnf.items() if k != 'D'} } "
          f"— 다른 평면 것은 **관측만 한다**")
    if _er.get("logged_no_file_D"):
        print(f"     ** D 로그-only ** {_er['logged_no_file_D'][:5]}")
    if _er.get("missing_new"):
        print(f"     ** 새 누락 ** {_er['missing_new'][:5]}")
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
