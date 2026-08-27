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

    heads = []
    seen = set()
    for m in HEAD.finditer(text):
        t = m.group(1)
        if t not in seen:
            seen.add(t)
            heads.append(t)

    # --- 방향 A: delta 표제 → 색인 행 ---
    a_hit, a_miss = [], []
    for t in heads:
        ids = idx.resolve(t)
        (a_hit if ids else a_miss).append({"delta_head": t, "index_ids": ids})

    # --- 방향 B: 색인 행 → delta ---
    # A 의 `self_check.index_to_delta_reachability` 는 **경로가 셋**이다:
    #   (a) delta 절 헤더 · (b) 별칭 토큰경계 · (c) split_rows 부모 절
    # D 의 첫 구현은 (b) 만 봤다. 그래서 A 는 0 을 보고 D 는 11 을 봤다 —
    # **문서 차이가 아니라 검사 정의 차이다.** 셋을 다 구현하고 경로를 기록한다.
    doc = json.loads(idx.path.read_text(encoding="utf-8"))
    split = (doc.get("split_rows") or {}).get("map", {})
    heads_set = set(heads)
    b_hit, b_miss = [], []
    for r in idx.rows:
        rid = r["id"]
        via = None
        if rid in heads_set:
            via = "a_delta_section_header"
        elif idx.present(rid, text):
            via = "b_alias_token_boundary"
        elif rid in split:
            parent = split[rid]
            if parent in heads_set or idx._hit(parent, text):
                via = f"c_split_parent:{parent}"
        rec = {"index_id": rid, "tokens": idx.variants(rid), "reachable_via": via}
        (b_hit if via else b_miss).append(rec)

    # --- 대조군: 이 검사가 실제로 무언가를 보고 있는가 ---
    ctrl = {
        "delta_heads_found": len(heads),
        "index_rows": len(idx.rows),
        "positive_control": idx.present("Δ21", text),      # 반드시 True
        "negative_control": idx.present("Δ999-R99", text),  # 반드시 None
        "reachability_control": ("Δ999-R99" not in set(heads)
                                 and idx.present("Δ999-R99", text) is None),
    }
    ctrl["verdict"] = (
        "PASS" if (len(heads) >= 10 and len(idx.rows) >= 10
                   and ctrl["positive_control"] is True
                   and ctrl["negative_control"] is None) else "FAIL"
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
        "A_delta_head_to_index": {"n": len(heads), "resolved": len(a_hit),
                                  "UNRESOLVED": a_miss},
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
    print(f"control={ctrl['verdict']} heads={len(heads)} rows={len(idx.rows)}")
    print(f"A) delta표제→색인  해결 {len(a_hit)}/{len(heads)}  미해결 {len(a_miss)}")
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
