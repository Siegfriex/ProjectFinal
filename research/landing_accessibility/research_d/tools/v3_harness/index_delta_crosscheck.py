"""색인 ↔ delta 대조 — 색인이 선언한 별칭만으로 조회한다.

이 대조는 D 에서 두 번 오탐을 냈다. 두 번 다 원인이 상대 문서가 아니라
**내 매칭**이었다 (D-DEF-14: 28건 · D-DEF-14b: 1건). 그래서 여기엔 표기
추론이 없다. `ruling_id_norm.Index` 가 색인 바이트에서 읽은 id/aliases 만 쓴다.

두 방향을 따로 낸다.
  A) delta 표제 → 색인에 행이 있는가   (미수록 탐지)
  B) 색인 행    → delta 본문에 근거가 있는가 (유령 행 탐지)

어느 쪽도 '없음' 을 바로 결함으로 부르지 않는다. `UNRESOLVED` 로 내고,
사람이 바이트를 보고 판정한다 — R13(관측 증거 없이 '없음' 을 적지 않는다).
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from ruling_id_norm import Index  # noqa: E402

DELTA = Path(
    "/home/sieg/projects-wsl/ProjectFinal/.agent_worktrees/claude_a_control"
    "/research/landing_accessibility/control/v3/V3_0_1_SUCCESSOR_DELTA.md"
)
# delta 가 표제로 선언하는 판정 단위. 헤더 첫 토큰만 읽는다.
HEAD = re.compile(r"^#{2,4}\s*((?:Δ\d+[a-z]?(?:-[A-Za-z0-9]+)?)|(?:R\d+)|(?:P-?\d+)|(?:GAP-?\d+))\b", re.M)


def main() -> int:
    idx = Index()
    text = DELTA.read_text(encoding="utf-8")
    import hashlib
    delta_sha = hashlib.sha256(DELTA.read_bytes()).hexdigest()

    doc0 = json.loads(idx.path.read_text(encoding="utf-8"))
    heads = []
    seen = set()
    for m in HEAD.finditer(text):
        t = m.group(1)
        if t not in seen:
            seen.add(t)
            heads.append(t)

    # --- 방향 A: delta 표제 → 색인 행 ---
    # A 의 `self_check.delta_section_coverage` 규칙: **delta 의 모든 ruling 절이
    # 색인에 대응 행을 가져야 한다. 컨테이너 절은 예외이며 `container_sections`
    # 에 명시된 것뿐.** D 는 그 예외를 적용하지 않아 컨테이너 13개가 계속
    # `미해결` 로 나왔다 — 방향 B 에서 A 의 3경로를 하나만 구현했던 것과
    # 같은 실수다. 상대 문서의 결함이 아니라 내 규칙 미적용이었다.
    #
    # 커버 판정은 세 가지다: 별칭 조회 · 자식 행 존재 · 컨테이너 선언.
    # (`Δ28` 은 자식 `Δ28-R26` 으로 커버된다 — 원시 id 대조만 하면 오탐이 난다.)
    containers = set((doc0.get("container_sections") or {}).get("list", []))
    split_map = (doc0.get("split_rows") or {}).get("map", {})
    child_prefix = {r["id"].split("-")[0] for r in idx.rows if "-" in r["id"]}

    def cover(t):
        ids = idx.resolve(t)
        if ids:
            return {"via": "alias_or_id", "index_ids": ids}
        if t in child_prefix:
            kids = [r["id"] for r in idx.rows if r["id"].startswith(t + "-")]
            return {"via": "child_rows", "index_ids": kids}
        # `split_rows` 가 선언한 부모 절 — 자식이 색인에 있으면 충족이다.
        # `Δ10-R13a` 는 `Δ10-R13` + `a` 라서 `t + "-"` 접두로는 안 걸린다.
        # 접두를 추론해 만들지 않고 **A 가 선언한 map 의 값**을 쓴다.
        kids = sorted(k for k, v in split_map.items() if v == t and k in
                      {r["id"] for r in idx.rows})
        if kids:
            return {"via": "declared_split_parent", "index_ids": kids}
        if t in containers:
            return {"via": "declared_container", "index_ids": []}
        return None

    a_hit, a_miss = [], []
    for t in heads:
        c = cover(t)
        (a_hit if c else a_miss).append({"delta_head": t, **(c or {"via": None})})

    # --- 방향 B: 색인 행 → delta ---
    # A 의 `self_check.index_to_delta_reachability` 는 **경로가 셋**이다:
    #   (a) delta 절 헤더 · (b) 별칭 토큰경계 · (c) split_rows 부모 절
    # D 의 첫 구현은 (b) 만 봤다. 그래서 A 는 0 을 보고 D 는 11 을 봤다 —
    # **문서 차이가 아니라 검사 정의 차이다.** 셋을 다 구현하고 경로를 기록한다.
    split = (doc0.get("split_rows") or {}).get("map", {})
    heads_set = set(heads)
    # 판별 대조군의 가짜 자식 id — delta 해시에서 파생한다 (아래 설명 참조).
    _probe = f"Δ15-P{delta_sha[:10]}"
    _fake_head = f"Δ9{delta_sha[:6]}"     # 방향 A 용 — 존재하지 않는 절 표제

    def reach(rid, tokens):
        """A 가 선언한 세 경로만. 대조군도 이 함수를 탄다 (D-DEF-09)."""
        if rid in heads_set:
            return "a_delta_section_header"
        if any(idx._hit(t, text) for t in tokens):
            return "b_alias_token_boundary"
        if rid in split:
            parent = split[rid]
            if parent in heads_set or idx._hit(parent, text):
                return f"c_split_parent:{parent}"
        return None

    # 양성 대조군용 — 각 경로로 실제 도달하는 행을 하나씩 고른다
    _pos_header = next((r["id"] for r in idx.rows if r["id"] in heads_set), None)
    _pos_alias = next((r["id"] for r in idx.rows
                       if r["id"] not in heads_set
                       and any(idx._hit(t, text) for t in idx.variants(r["id"]))), None)

    b_hit, b_miss = [], []
    for r in idx.rows:
        rid = r["id"]
        via = reach(rid, idx.variants(rid))
        rec = {"index_id": rid, "tokens": idx.variants(rid), "reachable_via": via}
        (b_hit if via else b_miss).append(rec)

    # --- 대조군: 이 검사가 실제로 무언가를 보고 있는가 ---
    ctrl = {
        "delta_heads_found": len(heads),
        "index_rows": len(idx.rows),
        "positive_control": idx.present("Δ21", text),      # 반드시 True
        "negative_control": idx.present("Δ999-R99", text),  # 반드시 None
        # --- 판별 대조군 ---
        # `Δ999-R99` 는 부모 절도 없어서 **좁은 규칙에서도 넓은 규칙에서도**
        # 미도달이다. 그래서 두 규칙을 구분하지 못한다 (D-V3-FINDING-015).
        # 부모 절이 **존재하는** 가짜 자식이라야 갈린다:
        #   선언된 (a)(b)(c) 규칙  → 미도달
        #   authority/부모 상속 규칙 → 도달
        # 이 도구는 선언된 규칙을 구현하므로 미도달이어야 한다. 도달로 나오면
        # 구현이 조용히 넓어진 것이다.
        # --- 양성 도달 대조군 (B 의 R31 양방향 기준) ---
        # 위 대조군은 셋 다 **None 을 기대한다.** `reach()` 가 무조건 None 을
        # 내도록 망가지면 전부 통과하고 전 행이 '미도달' 로 보고된다 —
        # 그리고 그건 진짜 결함 보고와 구분되지 않는다.
        # B 가 T-B-V3-FINDING-011 에서 실증한 것이 이것이다: 위반 단언과 부재
        # 단언은 **서로 다른 변형**으로 각각 실패함을 보여야 한다.
        # 그래서 각 경로마다 실제로 도달하는 행 하나를 고정한다.
        "positive_reach_control": {
            "via_header": {
                "row": _pos_header,
                "reach": reach(_pos_header, idx.variants(_pos_header)) if _pos_header else None,
                "expected": "a_delta_section_header",
            },
            "via_alias": {
                "row": _pos_alias,
                "reach": reach(_pos_alias, idx.variants(_pos_alias)) if _pos_alias else None,
                "expected": "b_alias_token_boundary",
            },
        },
        # 방향 A 대조군 — 커버 판정이 열린 채 망가지면 미커버 0 이 계속 나오고
        # 그건 지금의 정상 출력과 같다. 존재하지 않는 delta 표제가 커버로
        # 나오면 안 된다. id 는 delta 해시에서 파생한다(고정 문자열을 쓰면
        # 그 id 를 적는 순간 죽는다 — C-FINDING-075215).
        "coverage_control": {
            "fake_head": _fake_head,
            "absent_from_index": not idx.resolve(_fake_head),
            "cover_result": (cover(_fake_head) or {}).get("via"),
            "expected": None,
        },
        "discriminating_control": {
            # id 를 **문서 내용에서 파생**한다. 고정 문자열을 쓰면 그 id 를
            # 어딘가에 적는 순간 대조군이 죽는다 — A 의 probe `Δ90001` 이
            # 정확히 그렇게 됐다(C-FINDING-075215): 그 문제를 기술한 delta
            # 부기에 문자열이 들어가면서 authority 경로로 도달 가능해졌다.
            # delta 해시에서 파생하면 문서가 바뀔 때마다 id 도 바뀌므로
            # 미리 적혀 있을 수 없다. 그래도 **부재를 검사한다** — 파생이
            # 우연히 충돌해도 조용히 통과하지 않도록.
            "fake_child": _probe,
            "probe_absent_from_delta": _probe not in text,
            "parent_section_exists": "Δ15" in set(heads),
            "reach_result": reach(_probe, [_probe]),
            "expected": None,
            "why": "부모 절이 존재하는 가짜 자식. 선언 규칙이면 미도달, "
                   "부모 상속 규칙이면 도달 — 두 규칙이 여기서 갈린다",
        },
    }
    ctrl["verdict"] = (
        "PASS" if (len(heads) >= 10 and len(idx.rows) >= 10
                   and ctrl["positive_control"] is True
                   and ctrl["negative_control"] is None
                   and ctrl["discriminating_control"]["parent_section_exists"]
                   and ctrl["discriminating_control"]["probe_absent_from_delta"]
                   and ctrl["discriminating_control"]["reach_result"] is None
                   and ctrl["coverage_control"]["absent_from_index"]
                   and ctrl["coverage_control"]["cover_result"] is None
                   and ctrl["positive_reach_control"]["via_header"]["reach"]
                       == "a_delta_section_header"
                   and ctrl["positive_reach_control"]["via_alias"]["reach"]
                       == "b_alias_token_boundary")
        else "FAIL"
    )

    out = {
        "tool": "tools/v3_harness/index_delta_crosscheck.py",
        "resolver": "ruling_id_norm v3 — 색인 aliases 조회, 추론 없음",
        "checked_at_kst": subprocess.run(["date", "-Iseconds"], capture_output=True,
                                         text=True).stdout.strip(),
        "index": {"version": idx.version, "sha256": idx.sha256,
                  "authority_sha": idx.authority_sha, "rows": len(idx.rows)},
        "delta": {"path": str(DELTA), "sha256": delta_sha},
        "control": ctrl,
        "A_delta_head_to_index": {"n": len(heads), "covered": len(a_hit),
                                  "rule": "A self_check.delta_section_coverage — 별칭/자식행/선언된 컨테이너",
                                  "by_path": {k: sum(1 for x in a_hit if x["via"] == k)
                                              for k in ("alias_or_id", "child_rows",
                                                        "declared_split_parent",
                                                        "declared_container")},
                                  "UNCOVERED": a_miss},
        "B_index_row_to_delta": {"n": len(idx.rows), "reachable": len(b_hit),
                                 "rule": "A self_check.index_to_delta_reachability — (a)헤더 (b)별칭 토큰경계 (c)split_rows 부모",
                                 "by_path": {k: sum(1 for x in b_hit
                                                    if (x["reachable_via"] or "").startswith(k))
                                             for k in ("a_", "b_", "c_")},
                                 "UNRESOLVED": b_miss},
        "dropped_aliases": idx.dropped,
        "ambiguous_tokens": {t: ids for t, ids in idx.owner.items() if len(ids) > 1},
        "claim_kind": "OBSERVATION",
        "not_a_verdict": "D 는 색인·delta 를 고치라고 판정하지 않는다. 미해결 항목은 A 판정 대상이다.",
    }
    Path("results/D_V3_INDEX_DELTA_CROSSCHECK_v3resolver.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    dc = ctrl["discriminating_control"]
    print(f"control={ctrl['verdict']} heads={len(heads)} rows={len(idx.rows)}")
    pr = ctrl["positive_reach_control"]
    print(f"   양성도달   헤더경로 {pr['via_header']['row']}→{pr['via_header']['reach']} · "
          f"별칭경로 {pr['via_alias']['row']}→{pr['via_alias']['reach']}")
    cc = ctrl["coverage_control"]
    print(f"   커버대조군 {cc['fake_head']}: 색인부재={cc['absent_from_index']} "
          f"커버={cc['cover_result']} (기대 None)")
    print(f"   판별대조군 {dc['fake_child']}: 부재={dc['probe_absent_from_delta']} "
          f"부모절존재={dc['parent_section_exists']} 도달={dc['reach_result']} "
          f"(기대 None — 선언 규칙 구현)")
    from collections import Counter as _C
    print(f"A) delta표제→색인  커버 {len(a_hit)}/{len(heads)}  미커버 {len(a_miss)}")
    print(f"   경로별: {dict(_C(x['via'] for x in a_hit))}")
    for x in a_miss:
        print("   -", x["delta_head"])
    from collections import Counter
    paths = Counter((x["reachable_via"] or "?").split(":")[0] for x in b_hit)
    print(f"B) 색인행→delta   도달 {len(b_hit)}/{len(idx.rows)}  미도달 {len(b_miss)}")
    print(f"   경로별: {dict(paths)}")
    for x in b_miss:
        print("   -", x["index_id"], x["tokens"])
    return 0 if ctrl["verdict"] == "PASS" else 3


if __name__ == "__main__":
    raise SystemExit(main())
