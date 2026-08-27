"""판정 id 표기 정규화 — T-A-V3-FC-004 D 배정.

색인·delta·티켓이 같은 판정을 서로 다르게 적는다:

    색인   Δ21 · Δ10-R13a · Δ14-P06 · Δ15-GAP07
    delta  Δ21 절 · R13 · P-06 · GAP-07
    티켓   R21 · R13 · P-06

정규화 없이 대조하면 **상대 문서의 결함이 아니라 내 매칭의 결함**이 나온다.
D 는 이것을 두 번 겪었다 — D-DEF-14(Δ14-P06 ↔ P-06, 28건 오탐, 발행 전 포착)와
R21 ↔ Δ21(1건 오탐, 발행 후 A 가 지적). 두 번째는 첫 번째 시정이 덮지 못한 형태였다.

핵심: `variants(id)` 는 **한 id 가 다른 문서에서 취할 수 있는 표기들**을 낸다.
검색은 그 중 하나라도 걸리면 present 로 본다. 넓게 잡는 쪽이 안전하다 —
좁으면 없는 결함을 만들고, 넓으면 있는 결함을 놓친다. 둘 다 나쁘지만
**없는 결함을 만들어 다른 평면에 보내는 쪽이 더 비싸다.**
"""
from __future__ import annotations

import re

SEC = re.compile(r"^Δ(\d+)(?:-(.+))?$")          # Δ21 · Δ10-R13a
TAIL = re.compile(r"^([A-Za-z]+)(\d+)([a-z]?)$")  # R13a · P06 · GAP07


def variants(rid: str) -> set[str]:
    """id 하나가 색인/delta/티켓에서 취할 수 있는 표기 집합."""
    v: set[str] = {rid}
    m = SEC.match(rid)
    if not m:
        return {x for x in v if len(x) >= 2}
    sec, tail = m.group(1), m.group(2)
    v.add(f"Δ{sec}")
    # [R21 ↔ Δ21 오탐 시정] 절 번호만 있는 id 는 티켓에서 R<번호> 로 불린다.
    if tail is None:
        v |= {f"R{sec}", f"R-{sec}"}
        return {x for x in v if len(x) >= 2}
    v.add(tail)
    t = TAIL.match(tail)
    if t:
        alpha, num, suf = t.groups()
        v |= {f"{alpha}{num}", f"{alpha}-{num}", f"{alpha}{num}{suf}", f"{alpha}-{num}{suf}",
              f"Δ{sec}-{alpha}{num}", f"Δ{sec}-{alpha}-{num}"}
    return {x for x in v if len(x) >= 2}


def present(rid: str, text: str) -> bool:
    """rid 가 text 안에 (어떤 표기로든) 나타나는가. 단어 경계로 끊는다."""
    return any(re.search(r"(?<![A-Za-z0-9])" + re.escape(x) + r"(?![A-Za-z0-9])", text)
               for x in variants(rid))
