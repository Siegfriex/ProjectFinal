"""V3 MAIN50 census — mart 계약 · 분모 · 결측 규약. (T-A-V3-TBX-008/010)

D 는 이 파일에서 **아무것도 판정하지 않는다.** mart 를 읽고, 분모를 세고,
결측을 결측으로 유지한다. claim 후보는 C 가 독립 재계산한다.

이 세션에서 반복해서 나온 결함족을 여기서 미리 막는다:
  · 빈 결과와 통과가 같은 출력을 낸다        → `NO_DATA` 를 값으로 남긴다
  · 부재·공집합·값이 같은 칸에 들어간다      → `UNDETERMINED`/`NOT_OBSERVED`/빈칸을 구분한다
  · 컬럼 이름이 조용히 어긋난다              → 이름 불일치는 예외다(C checker 가 같은 이름에 묶여 있다)
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

REPO = Path("/home/sieg/projects-wsl/ProjectFinal")
CENSUS = REPO / "artifacts/v3_census"
MART_DIR = CENSUS / "mart"
ANALYSIS = CENSUS / "analysis"

# T-A-V3-TBX-010 재게시분 그대로. **이름을 바꾸지 않는다** — C checker 가 묶여 있다.
COLUMNS = [
    "target_id", "family_id", "service", "attempt_status", "terminal_reason",
    "visible_label", "accessible_name", "label_relation",
    "entry_x_norm", "entry_y_norm", "entry_zone", "entry_control_type",
    "nav_container_type", "reveal_direction", "menu_dependency",
    "task_flow_sequence", "experienced_flow_sequence", "activation_depth",
    "auth_gate_stage", "task_control_occlusion",
    "collector_plane", "evidence_hash", "missing_reason",
]

# [A R76] 사후 DOM 복원분의 출처 표시. CANONICAL_MART_50 에서 24번째 컬럼으로 들어왔다.
# 계약 검사가 이것을 **초과 컬럼으로 막았다** — 조용히 통과시키지 않은 것이 옳고,
# A 지시 필드이므로 optional 로 편입한다. 없어도 되고 있으면 읽는다.
# A 지시로 추가된 필드들. 계약 검사가 매번 **초과 컬럼으로 막았고**, 그때마다
# A 지시분임을 확인하고 편입했다 — 조용히 통과시키지 않는 것이 이 검사의 값이다.
OPTIONAL_COLUMNS = ("entry_observation_provenance",      # R76 사후 DOM 복원 출처
                    "collection_run",                    # R98 조건2 — 섞임을 보이게
                    "superseded_runs",                   # R99 재측정 이력
                    "entry_geometry_provenance",         # R106 E_R3_SUPPLEMENT
                    "route_diagnosis", "route_diagnosis_provenance",
                    "label_relation_rule", "label_provenance")
PROV_LIVE = "E_LIVE_SCOUT"
PROV_POSTHOC = "B_DERIVED_FROM_DOM_POSTHOC"

# 관측되지 않은 것을 나타내는 토큰. **빈칸과 0 과 다르다** (TBX-006 명시)
# 실데이터(snapshot_00, 11:00)에서 관측된 결측 토큰을 포함한다.
# `NA_NUMERIC_UNOBSERVED` 148건 · `E_RAW_NOT_YET_RECEIVED` 48건이 초기 목록에 없어
# **결측이 값으로 새어 들어갔다**. 토큰 목록은 손 유지 목록이라 또 뒤처진다(A R62) —
# 그래서 아래 `unknown_tokens()` 로 목록 밖 대문자 토큰을 **세어서 드러낸다**.
MISSING_TOKENS = ("UNDETERMINED", "NOT_OBSERVED", "NA_NUMERIC_UNOBSERVED",
                  "E_RAW_NOT_YET_RECEIVED", "NOT_YET_RECEIVED",
                  "NOT_OBSERVABLE_FROM_STATIC_DOM", "NOT_SEPARABLE_IN_THIS_CENSUS")
# 결측이 아니라 **상태값**이다. 결측으로 접으면 분모가 조용히 줄어든다.
STATUS_TOKENS = ("NOT_ATTEMPTED", "NO_SAFE_ROUTE", "AMBIGUOUS_E_SUPPLIES_ONE_SEQUENCE")
LABEL_RELATIONS = ("MATCH", "SEMANTIC_EQUIV", "DIFFERENT", "VISIBLE_ONLY", "AX_ONLY", "NONE")
N_PER_FAMILY = 10
N_TOTAL = 50


def empty_mart():
    """0행 mart. **template 이 데이터 없이도 끝까지 돈다는 것을 보이는 용도.**"""
    import pandas as pd
    return pd.DataFrame({c: pd.Series(dtype="object") for c in COLUMNS})


def read_mart_pinned(path):
    """바이트를 **한 번** 읽어 sha 와 표를 같은 판본에서 만든다.

    [D-DEF-34] B 가 streaming 으로 mart 를 갱신한다. 표를 읽은 뒤 sha 를 따로
    계산하면 그 사이 파일이 바뀌어 **provenance 의 해시가 그림과 다른 표를
    가리킨다** — 그리고 둘 다 정상으로 보인다. C 가 그 sha 로 재계산하면
    값이 안 맞고, 원인은 D 쪽에 있다.
    """
    import hashlib, io
    import pandas as pd
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"mart 없음: {p}")
    raw = p.read_bytes()
    sha = hashlib.sha256(raw).hexdigest()
    df = pd.read_csv(io.BytesIO(raw), dtype=str, keep_default_na=False)
    missing = [c for c in COLUMNS if c not in df.columns]
    extra = [c for c in df.columns if c not in COLUMNS + list(OPTIONAL_COLUMNS)]
    if missing or extra:
        raise ValueError(f"컬럼 계약 위반 — 누락 {missing} / 초과 {extra}")
    opt = [c for c in OPTIONAL_COLUMNS if c in df.columns]
    return df[COLUMNS + opt], {"path": str(p), "sha256": sha, "bytes": len(raw),
                               "optional_present": opt}


def read_mart(path):
    """snapshot 또는 canonical mart 를 읽는다.

    컬럼 이름이 다르면 **예외다.** 조용히 맞춰주면 C checker 와 D figure 가
    서로 다른 표를 보게 된다 — 그 어긋남은 그림이 그려지는 한 보이지 않는다.
    """
    import pandas as pd
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"mart 없음: {p}")
    df = pd.read_csv(p, dtype=str, keep_default_na=False)
    missing = [c for c in COLUMNS if c not in df.columns]
    extra = [c for c in df.columns if c not in COLUMNS]
    if missing or extra:
        raise ValueError(f"컬럼 계약 위반 — 누락 {missing} / 초과 {extra}")
    return df[COLUMNS]


# 미관측을 뜻하는 토큰의 **패턴**. 손 목록은 매번 뒤처졌다 (A R62) —
# 실제로 NOT_OBSERVED → NA_NUMERIC_UNOBSERVED → E_RAW_NOT_YET_RECEIVED →
# NOT_OBSERVABLE_FROM_STATIC_DOM 순으로 네 번 뒤처졌고, 그때마다 **미관측이
# 값으로 세어졌다**(entry_zone 이 0/50 인데 23/50 으로 보였다).
_MISSING_PAT = re.compile(
    r"(NOT_OBSERV|UNOBSERV|NOT_OBSERVABLE|UNDETERMINED|NOT_YET|NA_NUMERIC|NOT_SEPARABLE)")


def is_missing(v) -> bool:
    t = "" if v is None else str(v).strip()
    if t == "" or t in MISSING_TOKENS:
        return True
    if t in STATUS_TOKENS:          # 상태값은 결측이 아니다 — 접으면 분모가 줄어든다
        return False
    return bool(_MISSING_PAT.search(t))


# [A R74] 수집기의 0 과 사이트의 사실을 분리한다. 합치면 분모가 사이트 탓을 한다.
COLLECTOR_ZERO = "COLLECTOR_ZERO_CANDIDATE"      # 후보 추출이 0 을 반환 — 수집기 관측
SITE_NO_ROUTE = "NO_SAFE_ROUTE_SITE"             # 후보는 찾았으나 안전 경로 없음 — 사이트 관측
UNSPLIT_NO_ROUTE = "NO_SAFE_ROUTE"               # **아직 나뉘지 않은 옛 라벨.** 어느 쪽인지 모른다
# [A R92] '못 셌다' 는 세 번째 상태다. 0 으로 접지 않는다.
UNVERIFIED_COUNT = "NO_SAFE_ROUTE_UNVERIFIED_CANDIDATE_COUNT"

# [A R78] 분모 분류 확정
COMPLETED_TOKENS = ("ENDPOINT_REACHED",)
NOT_ATTEMPTED_TOKEN = "NOT_ATTEMPTED"


def denominators(df) -> dict:
    """family별 + overall 로 attempted / evidence_adequate / completed / failed.

    `attempted` 는 언제나 10 / 50 이다 (TBX-006). 실제 행이 그보다 적으면
    그것은 **아직 안 들어온 것**이지 분모가 줄어든 것이 아니다 — 둘을 구분해 적는다.
    """
    fams = sorted({str(x) for x in df["family_id"].tolist() if str(x).strip()})
    def block(sub, attempted_target):
        # [A R78] completed = ENDPOINT_REACHED 만. failed = attempted 했으나 미도달 전부.
        # NOT_ATTEMPTED 는 attempted 에 세지 않는다. 분모(frozen)는 그대로 유지된다.
        from collections import Counter
        ea = int(sum(1 for _, r in sub.iterrows()
                     if not is_missing(r["evidence_hash"])))
        st = [str(r["attempt_status"]).strip().upper() for _, r in sub.iterrows()]
        not_att = sum(1 for x in st if x == NOT_ATTEMPTED_TOKEN)
        attempted = len(st) - not_att
        comp = sum(1 for x in st if x in COMPLETED_TOKENS)
        fail = attempted - comp
        # [D-DEF-35] `completed`/`failed` 는 **알려진 토큰만** 센다. 실데이터의
        # `TERMINAL_NO_ENDPOINT` 처럼 목록 밖 상태를 임의로 실패로 접으면 그것은
        # D 의 조작화다 — D 권한이 아니다. 접지 말고 **값별로 전수 분해해 드러낸다.**
        from collections import Counter
        # failed 를 혼자 두지 않는다 (R78) — terminal_reason 을 항상 붙인다.
        fr = Counter(str(r["terminal_reason"]).strip() for _, r in sub.iterrows()
                     if str(r["attempt_status"]).strip().upper() != NOT_ATTEMPTED_TOKEN
                     and str(r["attempt_status"]).strip().upper() not in COMPLETED_TOKENS)
        split = {"collector_observation": int(fr.get(COLLECTOR_ZERO, 0)),
                 "site_observation": int(fr.get(SITE_NO_ROUTE, 0)),
                 "unverified_candidate_count": int(fr.get(UNVERIFIED_COUNT, 0)),
                 "NOT_YET_SPLIT": int(fr.get(UNSPLIT_NO_ROUTE, 0))}
        return {"denominator_frozen": attempted_target,
                "rows_present": int(len(sub)),
                "attempted": attempted, "not_attempted": not_att,
                "evidence_adequate": ea, "completed": comp, "failed": fail,
                "unaccounted": attempted - comp - fail,
                "failed_by_terminal_reason": dict(fr),
                "collector_vs_site": split,
                "split_note": ("R74 — 수집기의 0 과 사이트의 사실을 분리한다. "
                               "`NOT_YET_SPLIT` 은 옛 `NO_SAFE_ROUTE` 라벨이며 **어느 쪽인지 모른다** — "
                               "D 가 임의로 배분하지 않는다"),
                "classification_note": "R78 적용. 목록 밖 상태가 나오면 unaccounted 가 0 이 아니게 되어 드러난다"}
    out = {"overall": block(df, N_TOTAL),
           "by_family": {f: block(df[df["family_id"].astype(str) == f], N_PER_FAMILY)
                         for f in fams}}
    out["notation"] = "k/10 (family) · k/50 (overall) — TBX-008 요구"
    out["what_this_does_not_say"] = (
        "rows_present < attempted 는 '분모가 작다' 가 아니라 '아직 안 들어왔다' 다. "
        "실패 target 도 분모 50 에 남는다 — 빠지면 denominator corruption")
    return out


def data_state(df) -> str:
    """행수와 **관측 충실도를 함께** 낸다. 그림과 표에 반드시 실린다.

    [D-DEF-33] 처음에는 행수만 봤다. B 의 mart 는 실패 target 도 행으로 남기므로
    (그래야 분모 50 이 지켜진다) evidence 가 2건뿐인 snapshot_00 에서도
    `COMPLETE` 가 나왔다 — **골격 50행과 관측 50건이 같은 출력을 냈다.**
    이 세션 내내 다룬 그 형태를, 그것을 막으려고 만든 표지가 스스로 냈다.
    """
    n = len(df)
    if n == 0:
        return "NO_DATA"
    ea = int(sum(1 for _, r in df.iterrows() if not is_missing(r["evidence_hash"])))
    if ea == 0:
        return f"SKELETON_{n}_ROWS_0_EVIDENCE"
    if ea >= N_TOTAL:
        return f"COMPLETE_{n}_ROWS_{ea}_EVIDENCE"
    return f"PARTIAL_{ea}_OF_{N_TOTAL}_EVIDENCE_IN_{n}_ROWS"


def unknown_tokens(df) -> dict:
    """MISSING_TOKENS/STATUS_TOKENS 어디에도 없는 대문자 토큰을 **센다**.

    [A R62] 손으로 유지하는 포함/제외 목록은 썩는다. 목록을 늘리는 대신,
    목록 밖의 것이 **보이게** 만든다 — 모르는 토큰이 조용히 값으로 새는 것을 막는다.
    """
    import re
    known = set(MISSING_TOKENS) + set() if False else set(MISSING_TOKENS) | set(STATUS_TOKENS)
    pat = re.compile(r"^[A-Z][A-Z0-9_]{2,59}$")
    seen = {}
    for c in COLUMNS:
        for v in df[c]:
            t = str(v).strip()
            if pat.match(t) and t not in known:
                seen.setdefault(t, {"count": 0, "columns": set()})
                seen[t]["count"] += 1
                seen[t]["columns"].add(c)
    return {k: {"count": v["count"], "columns": sorted(v["columns"])}
            for k, v in sorted(seen.items(), key=lambda x: -x[1]["count"])}


def synthetic_fixture(n=50, seed_note="deterministic, not random"):
    """**합성이다. REAL 이 아니고 gold 도 아니다.**

    코드가 도는지 보이려면 데이터가 필요한데, 실데이터는 아직 없고 D 는 REAL 에
    접속하지 않는다. 그래서 결정적 합성표를 만든다 — 값은 전부 `SYNTHETIC_` 접두를
    달거나 구조적으로 생성되며, 어떤 산출에도 실측으로 실리지 않는다.
    """
    import pandas as pd
    fams = ["F1", "F2", "F3", "F4", "F5"]
    ctrl = ["link", "button", "menuitem", "tab"]
    navc = ["header", "footer", "sidebar", "inline"]
    rev = ["down", "right", "none", "overlay"]
    rows = []
    for i in range(n):
        f = fams[i // 10 % 5]
        stat = "COMPLETED" if i % 7 else "FAILED"
        obs = i % 5 == 0
        rows.append({
            "target_id": f"SYNTHETIC_T{i:03d}", "family_id": f,
            "service": f"SYNTHETIC_SVC_{f}_{i%10}",
            "attempt_status": stat,
            "terminal_reason": "OK" if stat == "COMPLETED" else
                               ["WAF", "TIMEOUT", "AUTH_GATE", "NOT_FOUND"][i % 4],
            "visible_label": f"SYNTHETIC_LBL_{i%6}",
            "accessible_name": ("UNDETERMINED" if obs else f"SYNTHETIC_AX_{i%6}"),
            "label_relation": ("UNDETERMINED" if obs else LABEL_RELATIONS[i % len(LABEL_RELATIONS)]),
            "entry_x_norm": ("NOT_OBSERVED" if obs else round(((i * 37) % 100) / 100, 3)),
            "entry_y_norm": ("NOT_OBSERVED" if obs else round(((i * 53) % 100) / 100, 3)),
            "entry_zone": ("NOT_OBSERVED" if obs else
                           ["top", "bottom", "left", "right", "center"][i % 5]),
            "entry_control_type": ctrl[i % len(ctrl)],
            "nav_container_type": navc[i % len(navc)],
            "reveal_direction": rev[i % len(rev)],
            "menu_dependency": "true" if i % 3 == 0 else "false",
            "task_flow_sequence": "|".join(f"s{k}" for k in range(1 + i % 4)),
            "experienced_flow_sequence": "|".join(f"s{k}" for k in range(1 + (i + 1) % 5)),
            "activation_depth": ("UNDETERMINED" if obs else 1 + i % 6),
            "auth_gate_stage": ["none", "pre_entry", "post_entry", "mid_flow"][i % 4],
            "task_control_occlusion": "true" if i % 4 == 0 else "false",
            "collector_plane": "E",
            "evidence_hash": ("" if obs else hashlib.sha256(f"syn{i}".encode()).hexdigest()),
            "missing_reason": ("SYNTHETIC_NOT_OBSERVED_DEMO" if obs else ""),
        })
    df = pd.DataFrame(rows)[COLUMNS]
    df.attrs["synthetic"] = True
    df.attrs["seed_note"] = seed_note
    return df


NUMERIC_AXES = ("entry_x_norm", "entry_y_norm", "activation_depth")


def numeric_observed(v) -> bool:
    """수치 축은 **토큰 목록이 아니라 변환 가능성**으로 판정한다.

    [D-DEF-37] `NOT_OBSERVABLE_FROM_STATIC_DOM` 이 B 의 사후 추출에서 새로 나왔고
    손 목록에 없어 float() 에서 터졌다. 목록을 또 늘리면 다음 토큰에서 또 터진다 —
    **수치로 읽히는가**가 정의상 참인 기준이다 (A R62).
    """
    if is_missing(v):
        return False
    try:
        float(str(v).strip())
        return True
    except (TypeError, ValueError):
        return False


AXIS_COLUMNS = ("entry_x_norm", "entry_y_norm", "entry_zone", "entry_control_type",
                "nav_container_type", "reveal_direction", "menu_dependency",
                "auth_gate_stage", "activation_depth", "visible_label",
                "accessible_name", "label_relation", "task_control_occlusion",
                "experienced_flow_sequence")


def axis_coverage(df) -> dict:
    """축별 `k/n` 관측 수. **그림을 그릴지 말지의 입력이다** (A R87).

    입력이 0 인 축을 그리면 빈 그림이 나오고 **없음이 0 으로 보인다.**
    그래서 0 인 축은 렌더하지 않고 `AXIS_NOT_OBSERVED` 로 남긴다.
    """
    n = len(df)
    out = {}
    for c in AXIS_COLUMNS:
        if c not in df.columns:
            out[c] = {"observed": 0, "n": n, "state": "COLUMN_ABSENT"}
            continue
        pred = numeric_observed if c in NUMERIC_AXES else (lambda x: not is_missing(x))
        k = int(sum(1 for v in df[c] if pred(v)))
        out[c] = {"observed": k, "n": n,
                  "state": "AXIS_NOT_OBSERVED" if k == 0 else f"{k}/{n}"}
    return out


def contract_controls() -> dict:
    """계약이 실제로 무언가를 막는가 — must_flag / must_not_flag (Δ40).

    검사를 넣고 대조군을 넣지 않으면 그 검사는 다시 '이름만 있는 조건' 이다.
    """
    import pandas as pd
    cases = []

    def case(name, fn, must_flag):
        try:
            fn(); raised = False; err = None
        except Exception as e:
            raised = True; err = f"{type(e).__name__}"
        cases.append({"case": name, "expectation": "must_flag" if must_flag else "must_not_flag",
                      "raised": raised, "detail": err, "ok": raised is must_flag})

    good = synthetic_fixture(10)
    tmp = ANALYSIS / "_control_tmp.csv"
    tmp.parent.mkdir(parents=True, exist_ok=True)

    good.to_csv(tmp, index=False)
    case("계약을 지킨 mart 는 통과", lambda: read_mart(tmp), False)

    good.rename(columns={"visible_label": "label_visible"}).to_csv(tmp, index=False)
    case("컬럼 이름이 바뀌면 막힘", lambda: read_mart(tmp), True)

    good.drop(columns=["evidence_hash"]).to_csv(tmp, index=False)
    case("컬럼이 빠지면 막힘", lambda: read_mart(tmp), True)

    g2 = good.copy(); g2["extra_col"] = "x"; g2.to_csv(tmp, index=False)
    case("컬럼이 늘면 막힘", lambda: read_mart(tmp), True)

    case("없는 파일은 막힘", lambda: read_mart(ANALYSIS / "_nope.csv"), True)
    tmp.unlink(missing_ok=True)

    # 결측 구분: 빈칸·토큰·0 이 같은 칸으로 접히면 안 된다
    sep = {"empty→missing": is_missing(""), "UNDETERMINED→missing": is_missing("UNDETERMINED"),
           "NOT_OBSERVED→missing": is_missing("NOT_OBSERVED"),
           "0→NOT missing": not is_missing("0"), "0.0→NOT missing": not is_missing(0.0)}
    cases.append({"case": "빈칸/토큰은 결측, 0 은 값 (빈칸≠0)",
                  "expectation": "must_not_flag", "raised": False,
                  "detail": sep, "ok": all(sep.values())})

    # NO_DATA 가 값으로 남는가
    nd = data_state(empty_mart())
    cases.append({"case": "0행에서 data_state 가 NO_DATA 를 낸다 (빈 결과≠통과)",
                  "expectation": "must_not_flag", "raised": False,
                  "detail": nd, "ok": nd == "NO_DATA"})

    ok = all(c["ok"] for c in cases)
    return {"verdict": "PASS" if ok else "FAIL", "n": len(cases), "cases": cases,
            "naming": "Δ40 — must_flag(막아야 함) / must_not_flag(통과해야 함)"}


if __name__ == "__main__":
    r = contract_controls()
    print(json.dumps(r, ensure_ascii=False, indent=1))
    raise SystemExit(0 if r["verdict"] == "PASS" else 2)
