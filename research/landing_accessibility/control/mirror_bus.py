#!/usr/bin/env python3
"""버스 → `bus_mirror_a` 동기화. **부분 복사와 조용한 실패를 없앤다** (Δ52/R51).

A 는 `cp ... 2>/dev/null` 로 자기가 만진 것만 옮겼다. 결과는 티켓 109/286 · ACK 270/656 이었고,
실패한 복사는 출력이 없어 성공과 구분되지 않았다.

    python3 mirror_bus.py            # 검사만 (exit 1 = 미러가 뒤졌다)
    python3 mirror_bus.py --sync     # 동기화 후 재검증

exit 0 통과 · 1 불일치 · 2 **검사가 돌지 않았다**(Δ46-exit2)
"""
import hashlib, os, shutil, sys

HERE = os.path.dirname(os.path.abspath(__file__))
def _find_bus(start):
    """버스는 **메인 저장소**에 있고 A 는 워크트리에서 돈다 — 위로 올라가며 찾는다.

    첫 판은 워크트리 루트만 보고 `exit 2` 를 냈다. 그 exit 2 가 옳게 동작해서
    '버스가 비었다' 가 아니라 '검사가 돌지 않았다' 로 나왔다 (Δ46-exit2 첫 실사용).
    """
    d = start
    for _ in range(8):
        cand = os.path.join(d, ".agent_bus", "landing_v2")
        if os.path.isdir(cand):
            return cand
        nd = os.path.dirname(d)
        if nd == d:
            break
        d = nd
    return os.path.join(start, ".agent_bus", "landing_v2")   # 없으면 그 경로로 exit 2


BUS = _find_bus(HERE)
MIRROR = os.path.join(HERE, "bus_mirror_a")
DIRS = ("tickets", "acks", "completions", "escalations")


def sha(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()


def scan(sync):
    report, drift = {}, []
    for d in DIRS:
        src, dst = os.path.join(BUS, d), os.path.join(MIRROR, d)
        if not os.path.isdir(src):
            report[d] = {"bus": 0, "note": "버스에 없는 디렉터리"}
            continue
        os.makedirs(dst, exist_ok=True)
        names = sorted(n for n in os.listdir(src) if n.endswith(".json"))
        missing, differing = [], []
        for n in names:
            s, t = os.path.join(src, n), os.path.join(dst, n)
            if not os.path.exists(t):
                missing.append(n)
                if sync:
                    shutil.copy2(s, t)
            elif sha(s) != sha(t):
                differing.append(n)
                if sync:
                    shutil.copy2(s, t)
        extra = sorted(set(os.listdir(dst)) - set(names) - {".gitkeep"})
        report[d] = {"bus": len(names), "mirror_before": len(names) - len(missing),
                     "missing": len(missing), "differing": len(differing),
                     "mirror_only": extra}
        if missing or differing or extra:
            drift.append((d, missing[:5], differing[:5], extra[:5]))
    return report, drift


def main():
    if not os.path.isdir(BUS):
        print(f"!! 버스를 찾지 못했다: {BUS} — 검사가 돌지 않았다. 통과로 읽지 마라")
        return 2
    sync = "--sync" in sys.argv
    report, drift = scan(sync)
    for d, r in report.items():
        print(f"  {d:14s} " + " ".join(f"{k}={v}" for k, v in r.items()))
    if sync:
        _, drift = scan(False)          # 동기화 후 **다시 잰다** — 복사 성공을 가정하지 않는다
        if drift:
            print("!! 동기화 후에도 불일치가 남았다")
            for row in drift:
                print("   ", row)
            return 1
        print("동기화 완료 · 재검증 통과")
        return 0
    if drift:
        print("!! 미러가 버스와 다르다 (--sync 로 맞춰라)")
        for row in drift:
            print("   ", row)
        return 1
    print("미러 = 버스")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except SystemExit:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"\n!! 검사가 돌지 않았다({type(e).__name__}). 통과로도 실패로도 읽지 마라")
        sys.exit(2)
