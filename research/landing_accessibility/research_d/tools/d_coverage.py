"""coverage 를 **열별 허용값 집합(whitelist)** 으로 판정한다.

[D-DEF-45] D 는 `_MISSING_PAT` 이라는 **blacklist** 로 미관측을 걸렀다.
`AMBIGUOUS_MULTIPLE_TYPES` 는 그 패턴에 없어서 관측으로 셌고, D 는
`entry_control_type` 을 28 이라 냈다. **여러 후보가 매칭돼 하나로 정하지
못한 것은 관측이 아니다** — C 의 27 이 옳다(C-FACT_CORRECTION-133903).

D-DEF-37 때 "손 토큰 목록 대신 패턴" 으로 갔는데, **패턴도 결국 손으로 만든
목록**이다. blacklist 는 새 토큰이 생길 때마다 뚫린다. whitelist 는 안 뚫린다 —
모르는 값은 자동으로 미관측이 된다. 방향이 반대다.

`label_relation` 이 0/50 인 이유는 D-DEF-41 과 같다: 관계는 두 라벨이 **독립
관측돼야** 정의되는데 `accessible_name` 독립 관측이 0 이다. `NONE`(둘 다 없음)
과 `VISIBLE_ONLY`(AX 없음) 는 관계를 관측한 것이 아니라 관측할 수 없었던 것이다.
"""
from __future__ import annotations

import re

# 열별 **관측된 값으로 인정하는 집합**. 여기 없으면 미관측이다.
OBSERVED_VALUES = {
    "entry_control_type": frozenset({"ROLE_BUTTON", "LINK", "TEXT_LINK", "BUTTON", "ICON_TEXT"}),
    "nav_container_type": frozenset({"HEADER", "NAV", "FOOTER", "FORM", "NONE"}),
    # 관계는 두 라벨의 독립 관측을 전제한다. NONE·VISIBLE_ONLY 는 미관측이다
    "label_relation": frozenset({"MATCH", "SEMANTIC_EQUIV", "DIFFERENT"}),
    "entry_zone": frozenset({"TOP_LEFT", "TOP_CENTER", "TOP_RIGHT", "MID",
                             "MID_LEFT", "MID_RIGHT", "BOTTOM", "BOTTOM_LEFT",
                             "BOTTOM_CENTER", "BOTTOM_RIGHT"}),
    "auth_gate_stage": frozenset({"NONE", "AT_ENDPOINT", "AT_ENTRY", "MID_FLOW"}),
    "reveal_direction": frozenset({"DOWN", "UP", "LEFT", "RIGHT", "OVERLAY", "NONE"}),
    "task_control_occlusion": frozenset({"TRUE", "FALSE", "True", "False"}),
    "menu_dependency": frozenset({"TRUE", "FALSE", "True", "False"}),
    # [A R74] 수집기의 0 과 사이트의 사실은 **둘 다 관측**이다. 합치면 분모가 사이트 탓을 한다.
    # `NO_SAFE_ROUTE_SITE` 의 **SITE 라벨은 R132/R137 로 철회**됐다 — 값은 남고
    # 인용하는 쪽이 RETRACTED 를 붙인다. 종료 사유가 기록됐다는 사실 자체는 관측이다.
    # `..._UNVERIFIED_CANDIDATE_COUNT` 는 이름이 미검증을 말한다 — 미관측이다.
    "terminal_reason": frozenset({"COLLECTOR_ZERO_CANDIDATE", "ENDPOINT_REACHED",
                                  "AUTH_GATE", "FORBIDDEN_ACTION_BOUNDARY",
                                  "NO_SAFE_ROUTE_SITE", "NO_SAFE_ROUTE", "TIMEOUT"}),
    "attempt_status": frozenset({"TERMINAL_NO_ENDPOINT", "ENDPOINT_REACHED", "ERROR"}),
    "collector_plane": frozenset({"A", "B", "C", "D", "E"}),
}

# 식별자 — 값 집합을 적을 수 없고 미관측 토큰도 오지 않는다
# `evidence_hash` 는 넣지 않는다 — "항상 관측" 으로 두면 **미래에 토큰이 오면 뚫린다**.
# 형태를 명시하는 것이 whitelist 정신에 맞다.
IDENTIFIER = ("target_id", "family_id", "service")
HASHLIKE = ("evidence_hash",)
_HEX = re.compile(r"^[0-9a-fA-F]{16,}$")

# 값 집합을 못 적는 열 — 자유 문자열/수치. 여기서만 판정식을 쓴다
FREE_TEXT = ("visible_label", "accessible_name")
NUMERIC = ("entry_x_norm", "entry_y_norm", "activation_depth")

_TEXT_MISSING = re.compile(
    r"^(NOT_OBSERVED|UNOBSERVED|NOT_OBSERVABLE|UNDETERMINED|NOT_YET|NA_NUMERIC"
    r"|NOT_SEPARABLE|AMBIGUOUS|AX_NOT_INDEPENDENTLY_OBSERVED)")

# [발행 전 자체 검출] 처음에 `NO_[A-Z_]+` 를 미관측 접두로 넣었다가 `NO_SAFE_ROUTE_SITE`
# 16건을 지웠다(terminal_reason 50 -> 32). **접두 규칙은 blacklist 의 재발이다** —
# 이름 모양으로 의미를 넘겨짚은 것이고, A R74 가 관측값으로 확정한 값을 지웠다.
# 규칙을 없애고 그 열에 허용값 집합을 명시했다.


def is_observed(col: str, val: str) -> bool:
    v = (val or "").strip()
    if not v:
        return False
    if col in OBSERVED_VALUES:
        return v in OBSERVED_VALUES[col]          # **모르는 값은 미관측**
    if col in NUMERIC:
        try:
            float(v)
            return True
        except ValueError:
            return False
    if col in IDENTIFIER:
        return True
    if col in HASHLIKE:
        return bool(_HEX.match(v))
    if col in FREE_TEXT:
        return not _TEXT_MISSING.match(v)
    return not _TEXT_MISSING.match(v)


def coverage(df, cols=None) -> dict:
    cols = cols or [c for c in df.columns]
    return {c: int(sum(is_observed(c, v) for v in df[c])) for c in cols}


def controls() -> dict:
    """**새 토큰이 생겼을 때** blacklist 와 whitelist 가 갈리는지 본다."""
    rows = []

    def case(name, got, want):
        rows.append({"case": name, "got": got, "want": want, "ok": got == want})

    # 1. 실제로 났던 사고: AMBIGUOUS_MULTIPLE_TYPES
    case("AMBIGUOUS_MULTIPLE_TYPES 는 미관측",
         is_observed("entry_control_type", "AMBIGUOUS_MULTIPLE_TYPES"), False)
    # 2. **아직 존재하지 않는 토큰** — blacklist 가 뚫리는 자리
    case("처음 보는 토큰은 미관측 (whitelist 의 요점)",
         is_observed("entry_control_type", "PARTIALLY_RESOLVED_BY_HEURISTIC"), False)
    case("nav 도 마찬가지",
         is_observed("nav_container_type", "AMBIGUOUS_MULTIPLE_CONTAINERS"), False)
    # 3. 참인 값은 통과해야 한다 — 전부 막으면 검사가 무의미하다
    case("LINK 은 관측", is_observed("entry_control_type", "LINK"), True)
    case("nav NONE 은 관측(컨테이너 없음을 관측)",
         is_observed("nav_container_type", "NONE"), True)
    # 4. label_relation 은 관계 관측만 [D-DEF-41]
    case("label NONE 은 미관측", is_observed("label_relation", "NONE"), False)
    case("label VISIBLE_ONLY 은 미관측", is_observed("label_relation", "VISIBLE_ONLY"), False)
    case("label MATCH 는 관측", is_observed("label_relation", "MATCH"), True)
    # 5. 수치
    case("좌표 0.42 는 관측", is_observed("entry_x_norm", "0.42"), True)
    case("좌표 NA_NUMERIC 은 미관측", is_observed("entry_x_norm", "NA_NUMERIC_UNOBSERVED"), False)
    # 6. **과잉 차단** 대조군 — whitelist 도 틀릴 수 있다. 발행 전에 실제로 났다
    case("NO_SAFE_ROUTE_SITE 는 관측 [A R74] — 접두로 지우면 안 된다",
         is_observed("terminal_reason", "NO_SAFE_ROUTE_SITE"), True)
    case("NO_SAFE_ROUTE_UNVERIFIED_CANDIDATE_COUNT 는 미관측",
         is_observed("terminal_reason", "NO_SAFE_ROUTE_UNVERIFIED_CANDIDATE_COUNT"), False)
    case("COLLECTOR_ZERO_CANDIDATE 는 관측(수집기 사실) [A R74]",
         is_observed("terminal_reason", "COLLECTOR_ZERO_CANDIDATE"), True)
    case("식별자는 항상 관측", is_observed("service", "KB국민은행"), True)
    case("evidence_hash 는 해시 형태만 관측",
         is_observed("evidence_hash", "a3f19c" * 8), True)
    case("evidence_hash 에 토큰이 오면 미관측",
         is_observed("evidence_hash", "E_RAW_NOT_YET_RECEIVED"), False)

    ok = all(r["ok"] for r in rows)
    return {"verdict": "PASS" if ok else "FAIL", "n": len(rows),
            "failed": [r["case"] for r in rows if not r["ok"]], "cases": rows,
            "양방향":"2번은 **과소 차단**(뚫림), 6번대는 **과잉 차단**(지워버림)을 잡는다. whitelist 도 틀릴 수 있다",
            "왜_이_대조군인가": ("2번이 핵심이다. **아직 없는 토큰**을 넣었을 때 blacklist 는 "
                          "관측으로 세고 whitelist 는 막는다. D 가 실제로 뚫린 방식이다")}


if __name__ == "__main__":
    import json
    import sys
    sys.path.insert(0, str(__import__("pathlib").Path(__file__).parent))
    from d_v3_census import MART_DIR, read_mart_pinned
    df, pin = read_mart_pinned(MART_DIR / "CANONICAL_MART_50.csv")
    cols = ["visible_label", "accessible_name", "label_relation", "entry_x_norm",
            "entry_y_norm", "entry_zone", "entry_control_type", "nav_container_type",
            "reveal_direction", "menu_dependency", "activation_depth",
            "auth_gate_stage", "task_control_occlusion"]
    out = {"mart_sha256": pin["sha256"][:8], "coverage": coverage(df, cols),
           "controls": controls(),
           "method": "열별 허용값 집합(whitelist) — 모르는 값은 미관측 [D-DEF-45]"}
    print(json.dumps(out, ensure_ascii=False, indent=1))
    sys.exit(0 if out["controls"]["verdict"] == "PASS" else 1)
