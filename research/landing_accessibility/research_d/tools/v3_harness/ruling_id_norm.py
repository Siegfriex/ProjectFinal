"""판정 id 표기 해석 — 색인이 선언한 별칭만 쓴다 (추론 금지).

이 모듈은 두 번 다시 쓰였다.

  v1  패턴 추론 `Δn-Rm ↔ Rm ↔ P-nn`  — D-DEF-14 시정
  v2  + bare `Δn ↔ Rn`               — D-DEF-14b 시정
  v3  추론 전면 폐기, 색인 `aliases[]` 조회  — 지금

v2 를 실측한 결과 `Δn ↔ Rn` 은 **내가 발명한 규칙**이었고 4개 절에서 틀렸다:

    Δ8 → R7 · Δ10 → R11~R14 · Δ18 → R20 · Δ19 → R8,R9,R10

그중 둘은 단순한 누락이 아니라 **오탐 경로**다. 텍스트가 `R8` 을 말하면 실제
소유자는 Δ19-R8 인데 v2 는 그것을 Δ8 로도 읽었다 (`R10` → Δ10 도 같다).
서로 다른 판정 둘을 같은 것으로 보는 매칭은 "수록됨" 을 거짓으로 만든다.

A 가 색인 v8 `id_notation` 에서 규약을 바꿨다:

    "색인이 자기 별칭을 선언한다. 소비자는 별칭을 추론하지 않는다."
    "대조 도구는 `id` 와 `aliases` 를 둘 다 조회한다.
     어느 쪽에도 없으면 그때가 진짜 미수록이다."

따라서 여기엔 표기 규칙이 없다. 색인 바이트(T1)를 읽어 그대로 쓴다.
색인에 없는 id 는 추론해서 메우지 않고 `UNKNOWN` 으로 낸다 — 조용히 채우면
그 자리에서 다시 발명이 시작된다.
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

DEFAULT_INDEX = Path(
    "/home/sieg/projects-wsl/ProjectFinal/.agent_worktrees/claude_a_control"
    "/research/landing_accessibility/control/v3/V3_RULING_INDEX.json"
)

# 별칭이 텍스트 검색에 쓰이려면 id 형태여야 한다. 색인에는 서술형 별칭
# ('색인 유지')과 한 글자 조각('a','b')이 섞여 있는데, 그대로 정규식에 넣으면
# 문서 전체에 걸린다. 버리되 **버린 것을 결과에 남긴다** — 조용한 절단 금지.
_USABLE = re.compile(r"^[A-Za-zΔ0-9][A-Za-zΔ0-9\-_.]{1,}$")


class Index:
    def __init__(self, path: Path | str = DEFAULT_INDEX):
        self.path = Path(path)
        raw = self.path.read_bytes()
        self.sha256 = hashlib.sha256(raw).hexdigest()
        doc = json.loads(raw)
        self.version = doc.get("version")
        self.authority_sha = doc.get("authority_sha")
        self.rows = doc["rulings"]
        self.tokens: dict[str, list[str]] = {}   # id → 검색 가능한 표기들
        self.dropped: dict[str, list[str]] = {}  # id → 쓸 수 없어 버린 별칭
        self.owner: dict[str, list[str]] = {}    # 표기 → 그 표기를 가진 id 들
        for r in self.rows:
            rid = r["id"]
            keep, drop = [], []
            for a in [rid, *r.get("aliases", [])]:
                (keep if _USABLE.match(a) else drop).append(a)
            self.tokens[rid] = sorted(set(keep))
            if drop:
                self.dropped[rid] = drop
            for t in self.tokens[rid]:
                self.owner.setdefault(t, []).append(rid)

    def variants(self, rid: str) -> list[str]:
        """rid 의 검색 가능한 표기. 색인에 없으면 빈 리스트 — 추론하지 않는다."""
        return self.tokens.get(rid, [])

    def resolve(self, token: str) -> list[str]:
        """표기 하나가 가리키는 id 들. 둘 이상이면 색인이 모호한 것이다."""
        return sorted(self.owner.get(token, []))

    def present(self, rid: str, text: str) -> bool | None:
        """rid 가 text 에 (색인이 선언한 어떤 표기로든) 나타나는가.

        색인에 없는 id 는 True/False 가 아니라 **None**(UNKNOWN)을 낸다.
        모르는 것을 '없음' 으로 적는 것이 D-DEF-14 계열 오탐의 출발점이었다.
        """
        vs = self.variants(rid)
        if not vs:
            return None
        return any(
            re.search(r"(?<![A-Za-z0-9])" + re.escape(v) + r"(?![A-Za-z0-9])", text)
            for v in vs
        )


_default: Index | None = None


def _idx() -> Index:
    global _default
    if _default is None:
        _default = Index()
    return _default


def variants(rid: str) -> list[str]:
    return _idx().variants(rid)


def resolve(token: str) -> list[str]:
    return _idx().resolve(token)


def present(rid: str, text: str) -> bool | None:
    return _idx().present(rid, text)
