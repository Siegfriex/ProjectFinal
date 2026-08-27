"""ruling_id_norm 자체 대조.

**대조군 먼저.** 색인을 못 읽거나 행이 0이면 아래 음성대조는 전부 자동 통과한다
(변형이 없으니 아무것도 안 걸린다). 그 통과는 '충돌 없음' 이 아니라 '검사 안 함'
이다. 그래서 sanity 대조가 실패하면 본 검사를 돌리지 않고 죽는다.

음성대조 4건은 전부 **v2 가 실제로 틀렸던 형태**다. 새 구현이 통과하는 것만으로는
부족하고, 옛 구현이 여기서 실패해야 이 대조가 무언가를 검사하고 있다는 증거가 된다.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from ruling_id_norm import Index  # noqa: E402


def v2_variants(rid: str) -> set[str]:
    """폐기된 v2 추론 — 음성대조가 실효인지 보이기 위해서만 보존."""
    m = re.match(r"^Δ(\d+)(?:-(.+))?$", rid)
    if not m:
        return {rid}
    sec, tail = m.group(1), m.group(2)
    v = {rid, f"Δ{sec}"}
    if tail is None:
        return v | {f"R{sec}", f"R-{sec}"}
    v.add(tail)
    t = re.match(r"^([A-Za-z]+)(\d+)([a-z]?)$", tail)
    if t:
        a, n, s = t.groups()
        v |= {f"{a}{n}", f"{a}-{n}", f"{a}{n}{s}", f"Δ{sec}-{a}{n}"}
    return v


POSITIVE = [           # (id, 티켓/문서가 쓰는 표기) — 걸려야 한다
    ("Δ21", "R21"),
    ("Δ17-R18", "R18"),
    ("Δ18-R20", "R20"),
    ("Δ19-R8", "R8"),
    ("Δ10-R13a", "Δ10-R13a"),
    # 서술형 별칭 경로 — C 가 8/56, D 가 9/56 을 얻어 갈렸던 그 행이다.
    # D 가 모양으로 걸러 이 경로를 없앴다. 공백·`/`·한글이 섞인 별칭은
    # id 형태가 아니라서 버려졌는데, 실은 **가장 특정한** 별칭이다.
    ("Δ15-domax", "DOM/AX 불일치"),
]
NEGATIVE = [           # (id, 표기) — 걸리면 안 된다.
    # 전부 v2 가 실제로 틀린 지점이다. v2 는 bare `Δn` id 에 `Rn` 을 발명했고,
    # 그 Rn 은 색인에서 **다른 절의 판정**이 이미 쓰고 있었다. bare 행 10건 중
    # 9건이 그랬다 — Δ21 하나만 우연히 맞았고 v2 는 그 하나에서 일반화했다.
    ("Δ7", "R7"),    # R7 의 주인은 Δ8-R7
    ("Δ9", "R9"),    # R9 의 주인은 Δ19-R9
    ("Δ11", "R11"),  # R11 의 주인은 Δ10-R11
    ("Δ20", "R20"),  # R20 의 주인은 Δ18-R20
    ("Δ16", "R16"),  # R16 의 주인은 Δ12-R16
    ("Δ2", "R2"),    # R2  의 주인은 Δ8-R2
]


def main() -> int:
    idx = Index()
    # --- sanity 대조: 검사할 것이 실제로 있는가 ---
    if len(idx.rows) < 10:
        print(f"SANITY FAIL — 색인 행 {len(idx.rows)}건. 본 검사 중단.")
        return 3
    no_alias = [r["id"] for r in idx.rows if not r.get("aliases")]
    print(f"index v{idx.version} sha={idx.sha256[:16]} rows={len(idx.rows)} "
          f"aliases없음={len(no_alias)}")
    if no_alias:
        print("  aliases 없는 행:", no_alias)

    fail = 0
    print("\n[양성] id 가 그 표기로 검출되는가")
    for rid, tok in POSITIVE:
        got = idx.present(rid, f"본문 … {tok} … 끝")
        ok = got is True
        fail += not ok
        print(f"  {'OK ' if ok else 'FAIL'} {rid:<12} ← {tok:<10} present={got} vars={idx.variants(rid)}")

    print("\n[음성] 남의 표기에 걸리지 않는가  (괄호=폐기된 v2 의 결과)")
    for rid, tok in NEGATIVE:
        got = idx.present(rid, f"본문 … {tok} … 끝")
        ok = got is False
        old = tok in v2_variants(rid)
        fail += not ok
        print(f"  {'OK ' if ok else 'FAIL'} {rid:<12} ↛ {tok:<10} present={got}   "
              f"(v2={'걸렸음 → 이 음성대조는 실효' if old else '안 걸림'})   "
              f"주인={idx.resolve(tok)}")

    print("\n[서술형 별칭] 무관한 영문 문단에서 발화하지 않는가 (B 의 음성대조)")
    NEG_DOC = ("This document describes a build pipeline. It has a cache, "
               "b-tree indexes, and c-style comments. Contact plane C for details.")
    fired = [r["id"] for r in idx.rows if idx.present(r["id"], NEG_DOC)]
    ok = not fired
    fail += not ok
    print(f"  {'OK ' if ok else 'FAIL'} present {len(fired)}/{len(idx.rows)}  {fired}")

    print("\n[매칭 방식] 별칭별로 무엇을 쓰는가")
    from collections import Counter
    modes = Counter(idx.match_mode(t) for ts in idx.tokens.values() for t in ts)
    print("  ", dict(modes))

    print("\n[UNKNOWN] 색인에 없는 id 는 False 가 아니라 None")
    got = idx.present("Δ999-R99", "아무 본문")
    ok = got is None
    fail += not ok
    print(f"  {'OK ' if ok else 'FAIL'} Δ999-R99 present={got}")

    print("\n[모호] 한 표기가 여러 id 를 가리키는가 (색인 결함 탐지)")
    amb = {t: ids for t, ids in idx.owner.items() if len(ids) > 1}
    print(f"  중복 표기 {len(amb)}건: {dict(list(amb.items())[:6])}")

    print("\n[버린 별칭] 검색 불가 형태 — 조용히 버리지 않는다")
    for rid, ds in idx.dropped.items():
        print(f"  {rid:<12} {ds}")

    print(f"\nverdict: {'PASS' if fail == 0 else f'FAIL ({fail}건)'}")
    return 0 if fail == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
