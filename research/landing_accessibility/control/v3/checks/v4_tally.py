#!/usr/bin/env python3
"""PROBE V4 최종 집계 — 착수 전 동결.

TRUSTED 기준을 코드 상수로 박는다. 결과를 보고 기준을 고르지 못하게 하기 위해서다.
종료코드: 0 돌았음 · 2 못 돌았다 · 3 입력 없음
"""
import json, glob, hashlib, os, sys, csv, collections, traceback

VIEWPORT = (390, 900)            # 착수 전 고정
# v2 수정(13:01) — 좌표를 못 찾으면 `None` 으로 두고 통과시키던 결함을 고쳤다.
# 원본은 31/31 행에서 조건 4 를 한 번도 적용하지 않고 TRUSTED 6 을 냈다.
# **판정 기준을 완화한 것이 아니라, 적용되지 않던 기준이 적용되게 한 것이다.**
MART = "artifacts/v3_census/mart/CANONICAL_MART_50.csv"
ALREADY = {  # census 8 ∪ v2 3 ∪ v3 TRUSTED 8 = 19 (C 확정)
 "F3-01","F3-03","F3-07",
 "F2-02","F2-05","F2-06","F2-07","F2-09","F2-10","F4-09","F5-01",
}

def sha(p):
    try: return hashlib.sha256(open(p,"rb").read()).hexdigest()
    except OSError: return None

def classify(d):
    """TRUSTED 4조건 — 넷 다 충족해야 한다."""
    rc = glob.glob(f"{d}/E_ROUTE_CANDIDATE_*.json")
    if not rc: return None, "NO_ROUTE_CANDIDATE_FILE", {}
    j = json.load(open(rc[0]))
    ab = j.get("attempted_branches") or []
    cc = max([b.get("candidate_count", 0) for b in ab], default=0)
    st = j.get("scout_status")
    p0, p1 = sha(f"{d}/S0.png"), sha(f"{d}/S1.png")
    d0, d1 = sha(f"{d}/S0.dom.html"), sha(f"{d}/S1.dom.html")
    png_same = bool(p0 and p0 == p1); dom_same = bool(d0 and d0 == d1)
    box = j.get("selected_box") or j.get("click_xy") or {}
    x = box.get("x") if isinstance(box, dict) else (box[0] if box else None)
    y = box.get("y") if isinstance(box, dict) else (box[1] if box else None)
    in_vp = None
    if x is not None and y is not None:
        in_vp = (0 <= x <= VIEWPORT[0]) and (0 <= y <= VIEWPORT[1])
    ev = {"candidate_count": cc, "scout_status": st, "png_same": png_same,
          "dom_same": dom_same, "click_xy": [x, y], "in_viewport": in_vp}
    # ① 후보 ② endpoint ③ 클릭 유효 ④ 좌표 뷰포트 내
    if cc <= 0:                     return False, "NO_CANDIDATE", ev
    if st != "ENDPOINT_REACHED":    return False, f"NOT_ENDPOINT:{st}", ev
    if png_same and dom_same:       return False, "CLICK_NO_EFFECT", ev
    if png_same or dom_same:        return False, "CLICK_AMBIGUOUS", ev
    if in_vp is False:              return False, "COORD_OUT_OF_VIEWPORT", ev
    if in_vp is None:               return False, "COORD_NOT_EVALUABLE", ev   # 없음을 통과로 만들지 않는다
    return True, "TRUSTED", ev

def main():
    roots = glob.glob("artifacts/v3_probe_v4/raw/**/F[1-5]-*", recursive=True)
    roots = [r for r in roots if os.path.isdir(r)]
    if not roots:
        print("!! probe v4 산출 없음", file=sys.stderr); return 3
    tgt = json.load(open("artifacts/v3_probe_v4/PROBE_V4_TARGET_SET.json"))
    planned = set(tgt["A_보류_좌표수정으로_풀릴것"]) | set(tgt["B_미회복_COLLECTOR_ZERO_S2전개필요"]) | set(tgt["C_기타"])
    seen, res = {}, []
    for d in sorted(roots):
        t = os.path.basename(d)
        if t in seen: continue
        ok, why, ev = classify(d); seen[t] = True
        res.append({"target_id": t, "trusted": ok, "reason": why, **ev})
    trusted = {r["target_id"] for r in res if r["trusted"]}
    attempted = {r["target_id"] for r in res}
    out = {
     "viewport": VIEWPORT, "criterion_frozen_before_run": True,
     "planned": len(planned), "attempted": len(attempted),
     "not_attempted": sorted(planned - attempted),
     "off_target": sorted(attempted - planned),
     "v4_trusted": sorted(trusted), "v4_trusted_n": len(trusted),
     "v4_reasons": dict(collections.Counter(r["reason"] for r in res)),
     "already_secured_19": sorted(ALREADY | {r["target_id"] for r in csv.DictReader(open(MART))
                                             if r["terminal_reason"] in ("ENDPOINT_REACHED","AUTH_GATE")}),
     "rows": res,
    }
    out["cumulative_n"] = len(set(out["already_secured_19"]) | trusted)
    json.dump(out, open("artifacts/v3_probe_v4/V4_TALLY.json","w"), ensure_ascii=False, indent=1)
    print(f"계획 {len(planned)} · 시도 {len(attempted)} · 미시도 {len(planned-attempted)} · 대상밖 {len(attempted-planned)}")
    print(f"V4 TRUSTED {len(trusted)}")
    for k,v in sorted(out['v4_reasons'].items(), key=lambda x:-x[1]): print(f"   {v:>3}  {k}")
    print(f"\n누적 확보 {out['cumulative_n']} / 50   (기존 {len(out['already_secured_19'])} + V4 신규 {out['cumulative_n']-len(out['already_secured_19'])})")
    return 0

if __name__ == "__main__":
    try: sys.exit(main())
    except SystemExit: raise
    except Exception:
        traceback.print_exc()
        print("\n!! 집계가 돌지 않았다. 통과로도 실패로도 읽지 마라", file=sys.stderr)
        sys.exit(2)
