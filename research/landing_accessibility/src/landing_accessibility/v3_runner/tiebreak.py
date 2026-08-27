"""`Δ30` — v3 경로선택 tie-break 전순서. **v2 의 `min4_sort_key` 를 고치지 않는다.**

## 정본 (A `V3_0_1_SUCCESSOR_DELTA.md` `## Δ30` 축자)

> **(2) MIN-4 의 1차 키 `marked_primary` → v3 에 없다**
>
> `marked_primary` 는 대표기능 classifier 의 산물이고 v3 는 그것을 퇴역시켰다(`D3-03`).
>
> → 1차 키를 **`task_binding_candidate desc`** 로 대체한다 — `03 §4` 의 결정론적
> binder 가 이 `task_id` 의 후보로 지명했는가(**점수가 아니라 집합 소속**).
> 2차 `dom_order asc`, 3차 `selector asc` 는 그대로.
>
> **점수를 1차 키로 쓰지 않는 이유**: `Δ6-d` 의 목적이 결정성이다. 점수는 구현이
> 바뀌면 순서가 바뀐다. 집합 소속은 `03 §4` 의 선언된 규칙에서 나온다.

## 왜 v2 함수를 고치지 않고 새 파일인가

`engine/l0_collector.min4_sort_key` 의 docstring 이 스스로 적고 있다 — 그 함수는
`l0_collector.rank_primary_action_candidates` 와 **v2 `l1_engine.Scout.
_activation_candidates` 가 공유**한다. 1차 키를 그 자리에서 바꾸면 v2 경로(freeze
대상, `b28aaa5` NOT_PASSED)의 분기 순서가 같이 바뀐다. Δ30 은 v3 정책을 정한
것이지 v2 관측을 소급 변경하라고 하지 않았다. 그래서 **v3 는 자기 전순서를 여기서
따로 갖는다** — `l0_collector.py` 는 한 줄도 지우지 않는다(가산 0, 삭제 0).

`_dom_order_of` 만 v2 에서 **읽기전용으로 재사용**한다. `dom_order` 결측을
`Min4ProbeContractError` 로 거부하는 계약(`A2 §1.13`)은 v3 에서도 같아야 하고,
같은 판정을 두 번 구현하면 정본이 둘이 된다.

## 1차 키의 소스가 **트리에 없다** (측정값, 지어내지 않는다)

`task_binding_candidate` 를 산출하는 코드가 이 저장소에 **0곳**이다. `03 §4`
(`Task-specific Candidate Binding`) 원문도 후보 source 목록과 *"task label 을
변경할 수 없다"* 만 적을 뿐, **어떤 후보가 이 `task_id` 의 지명 후보인가를 가르는
결정론적 규칙을 선언하지 않는다.** v3 의 유일한 binder 구현(`discovery.
discover_task_candidates`)도 자기 docstring 에서 *"어떤 candidate 가 그 task 의
진짜 버튼인가를 판정하지 않는다"* 고 명시한다.

따라서 이 모듈은 **1차 키를 읽되 만들지 않는다.** 필드가 없으면 전건이 "비지명"
으로 같은 값을 받고 전순서는 `(dom_order asc, selector asc)` 로 축퇴한다 — 그것도
결정적이고 구조값만 쓴다. binder 가 생겨 필드를 채우는 날 이 파일은 고치지 않아도
1차 키가 발화한다. 이 상태는 `TASK_BINDING_CANDIDATE_SOURCE_ABSENT` 로 선언해 둔다.

**지어내지 않은 것**: 라벨/문구/유사도로 "이게 그 task 의 버튼 같다" 를 추정하는
가짜 binder. 그건 v3 가 퇴역시킨 대표기능 classifier 의 재발이다(`D3-03`).
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

_RESEARCH_ROOT = Path(__file__).resolve().parents[3]
if str(_RESEARCH_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(_RESEARCH_ROOT / "src"))

from landing_accessibility.engine.l0_collector import (  # noqa: E402
    Min4ProbeContractError,
    _dom_order_of,
)

#: 1차 키가 읽는 필드 이름. `03 §4` binder 가 채울 자리다.
TASK_BINDING_CANDIDATE_FIELD = "task_binding_candidate"

#: Δ30 전순서의 선언. 문자열 자체가 계약이며 테스트가 이 순서를 고정한다.
V3_TIEBREAK_TOTAL_ORDER: tuple[str, ...] = (
    "task_binding_candidate desc",
    "dom_order asc",
    "selector asc",
)

#: Δ30 이 v3 에서 **퇴역**시킨 키들. 이 전순서는 이 이름들을 읽지 않는다.
#: `marked_primary` = 대표기능 classifier 산물(`D3-03`).
#: 나머지 = 점수/관측 잡음 — "점수는 구현이 바뀌면 순서가 바뀐다"(Δ30).
V3_TIEBREAK_RETIRED_KEYS: frozenset[str] = frozenset(
    {
        "marked_primary",
        "area_css_px2",
        "similarity_score",
        "score",
        "rank_score",
        "viewport_score",
    }
)

#: **측정 사실**(B, `T-B-V3-BLK-013` 구현 중): 1차 키를 산출하는 코드가 트리에 없다.
TASK_BINDING_CANDIDATE_SOURCE_ABSENT = (
    "Δ30 의 1차 키 `task_binding_candidate` 를 산출하는 `03 §4` 결정론적 binder 가 "
    "저장소에 존재하지 않는다(측정: 트리 전체 0 출현). `03 §4` 원문도 지명 규칙을 "
    "선언하지 않는다. 이 모듈은 필드를 읽되 만들지 않으며, 값이 없는 동안 전순서는 "
    "`(dom_order asc, selector asc)` 로 축퇴한다 — 구조값만 쓰므로 결정적이다. "
    "가짜 binder 를 세우지 않는다(대표기능 classifier 재발 방지, D3-03)."
)


def task_binding_candidate_membership(candidate: Any) -> bool | None:
    """`03 §4` binder 의 **집합 소속**을 읽는다. 점수가 아니다.

    - `True` / `False` — binder 가 지명했다 / 지명하지 않았다 (관측된 판정).
    - `None` — 필드 자체가 없다. **관측 없음이며 `False` 가 아니다**
      (`Δ10-R13` 의 `NONE` ≠ `UNDETERMINED` 와 같은 구분).

    `None` 을 `False` 로 접지 않는 이유: 소속을 정렬에 쓸 때 둘은 같은 자리로 가지만
    (아래 `v3_tiebreak_sort_key` 참고), **기록에서는 달라야 한다** — 지명되지 않았다는
    관측과 binder 가 아예 없었다는 사실을 같은 값으로 적으면 나중에 분모를 복원할 수 없다.
    """
    get = getattr(candidate, "get", None)
    value = get(TASK_BINDING_CANDIDATE_FIELD) if callable(get) else None
    if value is None:
        return None
    return bool(value)


def v3_tiebreak_sort_key(c: Any) -> tuple[int, int, str]:
    """Δ30 전순서 `(task_binding_candidate desc, dom_order asc, selector asc)`.

    오름차순 정렬을 쓰므로 1차 키는 지명(`True`)을 `0` 으로 뒤집어 먼저 오게 한다.
    비지명(`False`)과 미관측(`None`)은 **정렬에서만** 같은 `1` 을 받는다 — 미관측을
    지명으로도 비지명으로도 승격시키지 않는 유일한 자리다.

    **읽지 않는 것**: `marked_primary`, 면적, 유사도, 그 밖의 어떤 점수도 읽지 않는다
    (`V3_TIEBREAK_RETIRED_KEYS`). 2차 키 `dom_order` 는 구조값이라 서브픽셀 흔들림에
    면역이다(`V2-C008` 시정 취지 승계).

    `dom_order` 가 없으면 `Min4ProbeContractError` 다 — v2 와 **같은 계약**이며
    같은 함수(`_dom_order_of`)로 판정한다. 관측 결측이 아니라 probe 결함이다.
    """
    member = task_binding_candidate_membership(c)
    bound_first = 0 if member is True else 1
    get = getattr(c, "get", None)
    if not callable(get):
        raise Min4ProbeContractError(
            f"candidate 가 Mapping 계약을 만족하지 않는다: {type(c).__name__} "
            "— Δ30 전순서는 후보의 형을 추측하지 않는다"
        )
    return (bound_first, _dom_order_of(c), str(get("selector") or ""))


__all__ = [
    "TASK_BINDING_CANDIDATE_FIELD",
    "TASK_BINDING_CANDIDATE_SOURCE_ABSENT",
    "V3_TIEBREAK_RETIRED_KEYS",
    "V3_TIEBREAK_TOTAL_ORDER",
    "task_binding_candidate_membership",
    "v3_tiebreak_sort_key",
]
