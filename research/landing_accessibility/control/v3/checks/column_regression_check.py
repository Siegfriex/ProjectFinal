#!/usr/bin/env python3
"""판본 간 열별 관측수 회귀 검사.

이 검사가 존재하는 이유
-----------------------
2026-08-28 MAIN50 census 에서 한 결함의 **시정이 다른 열을 비웠다**.
`label_relation` 매핑을 고치자 provenance 분기가 뒤바뀌어 `entry_control_type`
관측이 28 -> 9 로 조용히 떨어진 판본이 실제로 동결됐다.

기존 검사 둘 다 통과시켰다:
  - `COLUMN_SENTINEL`  : 전건 sentinel 이 아니므로 통과
  - `undermapped_columns` : 원본이 8건뿐이라 9 > 8 을 손실로 보지 않음
생산자가 출력 대조로 잡았다. **검사가 아니라 눈이 잡았다.**

이 검사는 그 자리를 메운다: **이전 판본 대비 관측수가 줄어든 열을 flag** 한다.

종료 코드
--------
  0  돌았고 회귀 없음
  1  돌았고 회귀 있음        <- 실패
  2  못 돌았다 (예외)        <- 통과로도 실패로도 읽지 마라
  3  입력 없음
"""
import csv, sys, json, hashlib, argparse, traceback, collections

# 열별 sentinel — 전역 목록을 쓰면 값을 결측으로 만든다 (D 의 R125)
GLOBAL_SENTINELS = {"NOT_OBSERVED", "NA_NUMERIC_UNOBSERVED", "", "NOT_PROVIDED_BY_E",
                    "AMBIGUOUS_E_SUPPLIES_ONE_SEQUENCE", "NOT_SEPARABLE_IN_THIS_CENSUS",
                    "NOT_OBSERVABLE_FROM_STATIC_DOM", "E_RAW_NOT_YET_RECEIVED"}
# NONE 이 '값' 인 열 — 여기서는 sentinel 로 세지 않는다
NONE_IS_A_VALUE = {"superseded_runs", "label_relation", "nav_container_type", "auth_gate_stage"}
# 값이지만 '이건 관측이 아니다' 라고 말하는 값 — 채워짐으로 세지 않는다 (D-DEF-41)
NOT_AN_OBSERVATION = {"AX_NOT_INDEPENDENTLY_OBSERVED", "AMBIGUOUS_MULTIPLE_CONTAINERS",
                      "NOT_RECORDED_BY_E", "UNDETERMINED"}

def sentinels_for(col):
    s = set(GLOBAL_SENTINELS)
    if col not in NONE_IS_A_VALUE:
        s.add("NONE")
    return s

def observed_counts(path):
    with open(path, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    counts, notobs = {}, {}
    for col in (rows[0].keys() if rows else []):
        sent = sentinels_for(col)
        counts[col] = sum(1 for r in rows if (r.get(col) or "").strip() not in sent
                          and (r.get(col) or "").strip() not in NOT_AN_OBSERVATION)
        notobs[col] = sum(1 for r in rows if (r.get(col) or "").strip() in NOT_AN_OBSERVATION)
    return counts, notobs, len(rows)

def sha(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--prev", required=True, help="이전 판본 CSV")
    ap.add_argument("--curr", required=True, help="현재 판본 CSV")
    ap.add_argument("--json", help="결과를 이 경로에 쓴다")
    a = ap.parse_args()

    for p in (a.prev, a.curr):
        try:
            open(p, "rb").close()
        except OSError:
            print(f"!! 입력 없음: {p}", file=sys.stderr)
            return 3

    pc, pn, prow = observed_counts(a.prev)
    cc, cn, crow = observed_counts(a.curr)

    regressions, new_cols, dropped_cols = [], [], []
    for col in sorted(set(pc) | set(cc)):
        if col not in cc:
            dropped_cols.append(col); continue
        if col not in pc:
            new_cols.append(col); continue
        if cc[col] < pc[col]:
            regressions.append({"column": col, "prev": pc[col], "curr": cc[col],
                                "loss": pc[col] - cc[col],
                                "not_an_observation_prev": pn[col], "not_an_observation_curr": cn[col]})

    out = {"prev": {"path": a.prev, "sha256": sha(a.prev), "rows": prow},
           "curr": {"path": a.curr, "sha256": sha(a.curr), "rows": crow},
           "regressions": regressions, "dropped_columns": dropped_cols, "new_columns": new_cols,
           "verdict": "REGRESSION" if regressions else ("DROPPED_COLUMN" if dropped_cols else "CLEAN")}
    if a.json:
        json.dump(out, open(a.json, "w"), ensure_ascii=False, indent=1)

    print(f"prev {out['prev']['sha256'][:12]} ({prow}행)  ->  curr {out['curr']['sha256'][:12]} ({crow}행)")
    if dropped_cols:
        print(f"  !! 사라진 열 {len(dropped_cols)}: {', '.join(dropped_cols)}")
    if new_cols:
        print(f"  +  새 열 {len(new_cols)}: {', '.join(new_cols)}")
    if regressions:
        print(f"  !! 관측수 회귀 {len(regressions)}열")
        for r in regressions:
            print(f"     {r['column']:28s} {r['prev']:>3} -> {r['curr']:>3}  (-{r['loss']})")
        return 1
    if dropped_cols:
        return 1
    print("  회귀 없음")
    return 0

if __name__ == "__main__":
    try:
        sys.exit(main())
    except SystemExit:
        raise
    except Exception:
        traceback.print_exc()
        print("\n!! 검사가 돌지 않았다. 통과로도 실패로도 읽지 마라", file=sys.stderr)
        sys.exit(2)
