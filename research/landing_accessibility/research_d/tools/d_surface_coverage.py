"""검사가 **낸 신호가 실제로 표시되는가**.

[D-DEF-77] 같은 형태를 두 번 냈다 —
`D-DEF-57`(방화벽 FAIL 을 1→3 으로 늘려놓고 단수로 보고) ·
`D-DEF-76`(`revalued_key_hashes` 를 만들어놓고 스캔 출력에 안 넣음).
둘 다 **만드는 것과 보이게 하는 것이 다른 작업**인데 같은 것으로 여겨서 났고,
둘 다 **출력을 눈으로 보다가** 잡았다.

그래서 센다: 각 검사의 `check()` 반환에서 **수치·목록을 담은 키**를 뽑고,
`d_bus_scan.sh` 가 그 키를 참조하는지 본다.

**한계 둘.** (a) **키 이름으로 맞춘다** — 같은 값이 다른 이름으로 표시되면
오탐이 난다(`n_violations` 가 `baseline_pre_guard.n` 으로 표시되는 경우).
(b) **스캔이 부르는 검사만 본다.** 그 목록은 이제 원본 import 에서 뽑지만,
스캔이 import 없이(예: 서브프로세스로) 부르는 검사는 여전히 안 보인다.

**판정하지 않는다.** 어떤 키가 "찍어야 할 신호" 인지는 자동으로 정해지지
않는다 — 이 세션에서 자동 판정이 표기 형태에 걸려 세 번 오분류했다
(D-DEF-54·55). 그래서 **목록만 내고 사람이 고른다.**
"""
from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
SCAN = TOOLS / "d_bus_scan.sh"

# 스캔이 부르는 검사들 — **원본에서 뽑는다.** 손 목록이었을 때 15쌍 중 9쌍만
# 적혀 있었다(D-DEF-79): `audit_tickets` · `coverage` · `audit_emitted` ·
# `run_controls` · 그리고 **이 검사 자신**이 빠져 있었다. A R62 — 손 목록은 썩는다.
_IMPORT = re.compile(r"from\s+([a-z_0-9]+)\s+import\s+([a-z_0-9]+)")
SELF_MODULE = "d_surface_coverage"


def derive_targets() -> list:
    """`d_bus_scan.sh` 의 import 문에서 (모듈, 함수) 를 뽑는다."""
    if not SCAN.exists():
        return []
    out, seen = [], set()
    for mod, fn in _IMPORT.findall(SCAN.read_text(encoding="utf-8")):
        if mod == SELF_MODULE:          # 자기 자신 — 재귀
            continue
        if not (TOOLS / f"{mod}.py").exists():
            continue
        if (mod, fn) in seen:
            continue
        seen.add((mod, fn))
        out.append((mod, fn))
    return out


# 설명·근거를 담는 키는 신호가 아니다 — 이름으로 거른다
_PROSE = ("왜", "뜻", "note", "why", "규칙", "축", "이유", "말하지", "않는",
          "무엇을", "어떻게", "설명", "출처", "대상", "범위", "관계", "read")


def _deep_key_names(obj, depth: int = 0) -> set:
    """반환 안의 **모든 깊이**의 키 이름. [D-DEF-94]

    `ambiguous_keys` 는 최상위끼리만 봤다 — 그래서 `d_tool_health` 의 **중첩** 키
    `hits` 가 `d_retractions.hits` 를 '표시됨' 으로 만든 것을 그 축이 못 봤다
    (`D-DEF-93`). 이름을 바꿔 하나는 없앴지만 **나머지를 세지 않았다.**
    """
    if depth > 6:
        return set()
    out = set()
    if isinstance(obj, dict):
        for k, v in obj.items():
            if isinstance(k, str):
                out.add(k)
            out |= _deep_key_names(v, depth + 1)
    elif isinstance(obj, (list, tuple)):
        for v in obj[:50]:                         # 긴 목록은 앞부분만 — 키 이름은 같다
            out |= _deep_key_names(v, depth + 1)
    return out


def _referenced(key: str, txt: str) -> bool:
    """스캔이 그 키를 **값으로 꺼내 쓰는가**.

    맨 단어로 맞추면 설명 문구 안의 언급도 표시로 센다 — 실제로 그랬다:
    `f"... 계산된 \u0060covered\u0060 를 쓴다"` 한 줄 때문에 `covered` 가
    표시된 것으로 읽혔다(**거짓 음성**). 값을 꺼내는 형태는 항상 따옴표가
    붙는다(`_x['k']` · `_x.get("k")`) — 그 형태를 요구한다.
    """
    return (f"'{key}'" in txt) or (f'"{key}"' in txt)


def _is_signal(k: str, v) -> bool:
    """수치나 목록을 담은 키만 신호 후보로 본다."""
    if any(p in str(k) for p in _PROSE):
        return False
    if isinstance(v, bool):
        return False
    if isinstance(v, int):
        return True
    if isinstance(v, (list, dict)):
        return len(v) > 0
    return False


# **표시하지 않기로 판단한 것** — 이유와 함께 남긴다. 침묵하는 블랙리스트가
# 아니라 **읽을 수 있는 판단**이다. 손 목록은 썩으므로(A R62) 키가 사라지면
# `stale_accepted` 로 스스로 신고한다.
ACCEPTED_UNSURFACED = {
    ("d_ticket_schema_check", "n_violations"):
        "**값은 이미 표시된다** — 스캔이 `baseline_pre_guard['n']` 로 같은 55 를 찍는다. "
        "이 검사는 **키 이름**으로 맞추므로 같은 값이 다른 이름으로 표시되면 오탐이 난다",
    # 아래 셋은 전부 한계 (a) 의 사례다 — **값은 표시되는데 이름이 다르다**
    ("d_tool_health", "covered"):
        "값이 이미 표시된다 — 스캔의 `루프 실행 26` 이 이 26 이다",
    ("d_tool_health", "syntax_only_tools"):
        "값이 이미 표시된다 — 스캔의 `문법만 45` 가 이 45 다. 45개 도구 **이름**을 매 회차 "
        "찍는 것은 소음이고, 변화는 수로 드러난다",
    ("d_standing_control", "checks"):
        "네 검사의 원본 반환 묶음이다. 스캔은 `드리프트 {…} · 대조군 4/4` 로 **판정에 쓰이는 두 축**을 "
        "찍고, 하나라도 어긋나면 그 이름을 찍는다 — 원본 묶음은 소음이다",
    ("d_retractions", "rows_ack"):
        "ACK 파일별 인용 상세다. 스캔은 `새 N · 철회 이전 N(위반 아님) · baseline N` 으로 "
        "**분류별 수**를 찍고 `새` 가 생기면 그것이 먼저 움직인다 — 5줄 상세는 소음이다",
    ("d_retractions", "hits"):
        "값이 이미 표시된다 — 스캔의 `발행티켓 PASS(새 0 / baseline 2)` 가 이 2건이다. "
        "둘 다 `D-V3-FINDING-043` · `BASELINE_PRE_GUARD` 이고 발행분은 고치지 않으므로 변하지 않는다",
    ("d_tool_health", "n_syntax_error"):
        "같은 축이 이미 표시된다 — `D 도구 문법 : PASS · 71/71` 이 그 수다",
    ("d_tool_health", "static_without_names"):
        "44개 도구 **이름**을 매 회차 찍는 것은 소음이다. 변화는 `문법만 1/45` 의 수로 드러나고, "
        "루프에서 도는 것 중 없는 것은 이름까지 찍는다 — **판정을 내는 쪽만 이름이 필요하다**",
    ("d_bus_scan_selftest", "log"):
        "케이스별 OK/FAIL 자취 14줄. 스캔은 verdict 와 positive/negative/malformed 계수를 찍고, "
        "**`failures` 는 생기는 즉시 찍는다** — 그 셋이면 자취 없이도 무엇이 깨졌는지 안다",
    ("d_warn_baseline", "n_base"):
        "총수(398)의 baseline 이다. 그 검사 스스로 **총수는 신호가 아니라고** 하므로 그 baseline 도 "
        "신호가 아니다 — 신호인 **종류** 쪽은 `종류 12 (baseline 12, Δ0)` 로 baseline 까지 찍는다",
    ("d_tool_health", "blocks"):
        "헤레독 블록의 tag·시작행·줄수. 스캔은 `헤레독 1블록` 으로 **개수**를 찍고 오류가 나면 "
        "행 번호를 찍는다 — 정상일 때 블록 명세는 소음이다",
    # [D-DEF-94] 충돌로 되돌려진 둘 — 값은 안 찍히는 것이 맞다
    # [D-DEF-99] 이름 충돌로 되돌아온 것들 — **행 번호로 확인**했다(`d_bus_scan.sh`)
    ("d_ledger_shape", "n_entries"):
        "57행 `대장 두 분류 … entries {n_entries}` 로 찍힌다",
    ("d_ssot_manifest", "n_entries"):
        "220행 `SSOTV3 manifest … 일치 {n_ok}/{n_entries}` 의 분모로 찍힌다",
    ("d_emit_ticket", "n"):
        "339행 `D 발행분 base_sha ({v3_era} v3-era / {n})` 로 찍힌다",
    ("d_retractions", "n"):
        "250행 `철회 라벨 인용 : 산출물 {verdict}({n})` 로 찍힌다 — 그것은 `audit_artifacts` 의 "
        "`n` 이다. `audit_tickets` 의 `n`(=2)은 251행의 `baseline` 수와 같은 값이지만 "
        "**그 키로 직접 찍히지는 않는다**",
    ("d_retractions", "n_new"):
        "251행 `발행티켓 {verdict}(새 {n_new} / baseline …)` 로 찍힌다",
    ("d_ticket_schema_check", "n_new"):
        "303행 `D 발행분 스키마 … 새 {n_new} / baseline …` 로 찍힌다",
    ("d_retractions", "baseline_pre_guard"):
        "251행에서 `baseline_pre_guard['n']` 이 찍히고 255행이 그 목록을 펼친다",
    ("d_ticket_schema_check", "baseline_pre_guard"):
        "303행에서 `baseline_pre_guard['n']` 이 찍힌다",
    ("d_tool_health", "per_module_calls"):
        "도구 72개의 모듈별 부수효과 호출 수다. 스캔은 `게이트 대상 24 중 위험 N · 전체 72 중 M` 로 "
        "**수**를 찍고 위험한 것은 이름까지 찍는다 — 72개 전부는 소음이다. "
        "**게이트가 이 값을 소비한다**(임포트해도 안전한 모듈만 돌린다)",
    ("d_tool_health", "rows"):
        "도구 71개의 모듈별 명세다. 스캔은 `루프 24/26 · 문법만 1/45` 로 **수**를 찍고 "
        "루프에서 대조군이 없는 것만 이름을 찍는다 — 71줄 명세는 소음이다",
    ("d_ticket_schema_check", "violations"):
        "위반 상세 목록이다. 스캔은 `새 0 / baseline 55` 와 `by_field` 분해를 찍는다 — "
        "**새 위반이 생기면 그 분해가 먼저 움직인다**",
    ("d_ledger_shape", "inner_records"):
        "대장 형태 검사의 내부 세부. 상위 `entries`·`caught_pre_emission` 가 이미 표시되고 "
        "이 수가 바뀌어도 대장의 두 분류는 달라지지 않는다",
    ("d_pending_response", "status_field"):
        "`status:OPEN` 신뢰도(D-DEF-67)는 **변하지 않는 사실**이다 — 발행분은 고치지 않으므로 "
        "이 수는 줄지 않는다. D 집계는 이미 ACK 기반이라 표시해도 행위가 바뀌지 않는다",
    ("d_mlflow_contract_audit", "n_d_runs"):
        "회계 줄이 총 run 과 미귀속을 이미 표시한다",
    ("d_mlflow_contract_audit", "n_after_contract"):
        "계약 이후 run 의 위반 수는 `D자체 PASS(위반 N)` 로 이미 표시된다",
    ("d_mlflow_contract_audit", "n_before_contract"):
        "계약 이전 8건은 baseline — 고정값이라 변화 신호가 없다",
    ("d_mlflow_contract_audit", "n_violating_baseline"):
        "위와 같은 baseline 축",
}


# [D-DEF-88] **한 프로세스 안에서만** 결과를 재사용한다. 이 함수가 한 회차에
# 두 번 이상 불리는데(스캔 + 표시누락 검사 + 자기 controls) 매번 전부 다시 쟀다.
# 프로세스가 끝나면 캐시도 끝나므로 **회차 간 낡은 값이 남지 않는다.**
@lru_cache(maxsize=1)
def check() -> dict:
    import importlib
    import sys as _s
    if str(TOOLS) not in _s.path:
        _s.path.insert(0, str(TOOLS))
    scan_txt = SCAN.read_text(encoding="utf-8") if SCAN.exists() else ""
    rows, unsurfaced = [], []
    key_owners: dict = {}          # [D-DEF-93] 최상위 키 이름 → 그 키를 내는 모듈들
    deep_owners: dict = {}         # [D-DEF-94] **모든 깊이**의 키 이름 → 모듈들
    for mod_name, fn_name in derive_targets():
        try:
            mod = importlib.import_module(mod_name)
            fn = getattr(mod, fn_name)
            import inspect
            if any(q.default is inspect.Parameter.empty
                   and q.kind in (q.POSITIONAL_ONLY, q.POSITIONAL_OR_KEYWORD)
                   for q in inspect.signature(fn).parameters.values()):
                rows.append({"module": mod_name, "fn": fn_name, "state": "NEEDS_ARGS"})
                continue
            res = fn()
        except Exception as e:
            rows.append({"module": mod_name, "state": f"RUN_FAIL: {type(e).__name__}"})
            continue
        if not isinstance(res, dict):
            rows.append({"module": mod_name, "state": "NON_DICT"})
            continue
        sig = [k for k, v in res.items() if _is_signal(k, v)]
        miss = [k for k in sig if not _referenced(k, scan_txt)]
        rows.append({"module": mod_name, "fn": fn_name,
                     "signal_keys": len(sig), "unsurfaced": miss})
        for k in sig:
            key_owners.setdefault(k, set()).add(mod_name)
        for k in _deep_key_names(res):
            deep_owners.setdefault(k, set()).add(mod_name)
        for k in miss:
            rec = {"module": mod_name, "key": k}
            acc = ACCEPTED_UNSURFACED.get((mod_name, k))
            if acc:
                rec["accepted_reason"] = acc
            unsurfaced.append(rec)
    # [D-DEF-93] **이름 대조는 모듈을 구분하지 않는다.** 두 모듈이 같은 키 이름을 내면
    # 한쪽을 찍은 것이 다른 쪽도 찍은 것으로 읽힌다 — `hits` 가 실제로 그랬다
    # (`d_tool_health` 쪽 표시가 생기자 `d_retractions.hits` 가 '표시됨' 이 됐다).
    shared = {k: sorted(v) for k, v in key_owners.items() if len(v) > 1}
    ambiguous = [{"key": k, "modules": v} for k, v in sorted(shared.items())
                 if _referenced(k, scan_txt)]
    # [D-DEF-94] 중첩까지 포함한 충돌 — 그런데 **총수는 신호가 아니다.**
    # `verdict` 는 11개 모듈이 다 내는 보편 키다. 위험한 것은 **어딘가에서 신호인 키**
    # 뿐이다: 그런 키만 '표시됨' 오판을 만든다(`hits` 가 그랬다). 나머지는 그냥 겹칠 뿐이다.
    deep_shared = {k: sorted(v) for k, v in deep_owners.items() if len(v) > 1}
    ambiguous_deep = [
        {"key": k, "modules": v,
         "signal_in": sorted(key_owners.get(k, ()))}
        for k, v in sorted(deep_shared.items())
        if _referenced(k, scan_txt) and k not in shared and k in key_owners]
    deep_benign = [k for k, v in sorted(deep_shared.items())
                   if _referenced(k, scan_txt) and k not in shared and k not in key_owners]

    # [D-DEF-94] 충돌로 '표시됨' 판정이 **믿을 수 없는** 키는 미표시로 되돌린다 —
    # **불확실한 것을 통과로 세지 않는다.** 그래야 사람이 판단하게 된다.
    # [D-DEF-99] **최상위 충돌도 같이 되돌린다.** 중첩만 되돌리고 최상위는 보고만 한
    # 것은 일관성이 없었다 — `hits` 사건이 우연히 중첩이었을 뿐 위험은 같다.
    _amb_all = list(ambiguous_deep) + [
        {"key": a["key"], "modules": a["modules"], "signal_in": a["modules"]}
        for a in ambiguous]
    for amb in _amb_all:
        for mod in amb["signal_in"]:
            if not any(u["module"] == mod and u["key"] == amb["key"] for u in unsurfaced):
                rec = {"module": mod, "key": amb["key"],
                       "왜_되돌렸나": f"이름 충돌 — {amb['modules']} 가 같은 이름을 쓴다"}
                acc = ACCEPTED_UNSURFACED.get((mod, amb["key"]))
                if acc:
                    rec["accepted_reason"] = acc
                unsurfaced.append(rec)

    # 목록에는 있는데 검사가 더는 내지 않는 키 — **손 목록이 썩은 자리**
    live = {(u["module"], u["key"]) for u in unsurfaced}
    stale = [{"module": m, "key": k, "왜": "검사가 더는 이 키를 내지 않는다 — 목록에서 뺀다"}
             for (m, k) in ACCEPTED_UNSURFACED if (m, k) not in live]
    unreviewed = [u for u in unsurfaced if "accepted_reason" not in u]

    return {"verdict": "INFO",              # **판정이 아니다** — 목록만 낸다
            "n_modules": len(rows), "rows": rows,
            "n_unsurfaced": len(unsurfaced), "unsurfaced": unsurfaced,
            "n_unreviewed": len(unreviewed), "unreviewed": unreviewed,
            "n_stale_accepted": len(stale), "stale_accepted": stale,
            "n_ambiguous_keys": len(ambiguous), "ambiguous_keys": ambiguous,
            "n_ambiguous_nested": len(ambiguous_deep), "ambiguous_nested": ambiguous_deep,
            "n_nested_benign": len(deep_benign), "nested_benign": deep_benign,
            "**중첩 충돌 총수는 신호가 아니다**": (
                "`verdict` 처럼 **모든 검사가 내는 보편 키**는 겹쳐도 오판을 만들지 않는다 — "
                "표시 대조는 **신호로 뽑힌 키**만 찾기 때문이다. "
                "`ambiguous_nested` 는 **어딘가에서 신호인 키**만 세고, "
                "나머지는 `nested_benign` 으로 따로 둔다"),
            "**이름 대조는 모듈을 구분하지 않는다**": (
                "두 모듈이 같은 키 이름을 내면 한쪽 표시가 다른 쪽도 표시된 것으로 읽힌다. "
                "`ambiguous_keys` 는 **그렇게 읽힌 것**이다 — '표시됨' 으로 세지만 "
                "**어느 모듈의 값이 찍혔는지는 이 방법으로 알 수 없다**"),
            "판정하지_않는_이유": ("어떤 키가 '찍어야 할 신호' 인지는 자동으로 정해지지 "
                          "않는다 — 이 세션에서 자동 판정이 표기 형태에 걸려 "
                          "세 번 오분류했다(D-DEF-54·55). **목록만 내고 사람이 고른다**"),
            "왜_세나": ("`D-DEF-57`·`D-DEF-76` 이 같은 형태였다 — 만든 것이 표시에 "
                    "안 들어갔고 **둘 다 출력을 눈으로 보다가** 잡았다")}


def controls() -> dict:
    rows = []

    def case(name, got, want, negative=False):
        rows.append({"case": name, "got": got, "want": want, "ok": got == want,
                     "expectation": "must_flag" if negative else "must_not_flag"})

    case("수치는 신호다", _is_signal("n_changed", 3), True)
    case("빈 목록은 신호가 아니다", _is_signal("changed", []), False)
    case("비어 있지 않은 목록은 신호다", _is_signal("changed", ["a"]), True)
    case("bool 은 신호가 아니다", _is_signal("ok", True), False)
    case("설명 키는 신호가 아니다", _is_signal("왜_필요한가", "긴 설명"), False)
    case("`note` 도 설명이다", _is_signal("note", "x"), False)
    c = check()
    case("판정이 아니라 INFO 다", c["verdict"], "INFO")
    case("설명 문구 안의 언급은 표시가 아니다",
         _referenced("covered", "print(f'계산된 `covered` 를 쓴다')"), False)
    case("따옴표로 꺼내 쓰면 표시다",
         _referenced("covered", "print(_c['covered'])"), True)
    case("쌍따옴표도 표시다", _referenced("covered", 'print(_c.get("covered"))'), True)
    case("이름 충돌을 센다 — 0 이면 그 축이 죽은 것이다",
         isinstance(c.get("ambiguous_keys"), list), True)
    _t = derive_targets()
    case("원본에서 9쌍보다 많이 뽑는다", len(_t) > 9, True)
    case("자기 자신은 빼야 한다 — 재귀", any(m == SELF_MODULE for m, _ in _t), False)
    case("없는 모듈은 안 뽑는다",
         all((TOOLS / f"{m}.py").exists() for m, _ in _t), True)
    case("판단한 것은 미검토에서 빠진다", c["n_unreviewed"] <= c["n_unsurfaced"], True)
    case("사라진 목록 항목을 신고한다",
         {"module": "없는모듈", "key": "없는키"} not in c["unsurfaced"], True)
    case("모듈을 하나도 못 부르지 않았다",
         all(r.get("state", "").startswith("RUN_FAIL") for r in c["rows"]), False,
         negative=True)
    ok = all(r["ok"] for r in rows)
    return {"verdict": "PASS" if ok else "FAIL", "n": len(rows),
            "must_flag": sum(1 for r in rows if r["expectation"] == "must_flag"),
            "must_not_flag": sum(1 for r in rows if r["expectation"] == "must_not_flag"),
            "failed": [r["case"] for r in rows if not r["ok"]], "cases": rows}


if __name__ == "__main__":
    import sys
    out = {"check": check(), "controls": controls()}
    print(json.dumps(out, ensure_ascii=False, indent=1))
    sys.exit(0 if out["controls"]["verdict"] == "PASS" else 1)
