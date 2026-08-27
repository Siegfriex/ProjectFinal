"""Task-specific obstruction 측정 — `02 §5 fact_task_obstruction` · `03 §9` · `04 §4`.

## 이 모듈이 재는 것 — page-level 이 아니라 task-specific 이다

`02 §5` 는 primary 를 `task_control_occlusion` 으로, `overlay_coverage` 를 **보조 설명값**으로
못박고 이렇게 끝난다: *"`max_overlay_coverage` 만으로 modal obstruction 을 대표하지 않는다."*

이 둘은 서로 다른 질문에 답한다.

| 값 | 질문 | 분모 |
|---|---|---|
| `overlay_coverage` | 이 오버레이가 **화면**을 얼마나 덮는가 | viewport 면적 |
| `task_control_occlusion` | 이 오버레이가 **사전지정 task 진입 control** 을 얼마나 덮는가 | task-entry control bbox 면적 |

그래서 두 값은 **반대 방향으로 갈릴 수 있다**. 화면 90% 를 덮지만 task control 을 비켜 간
쿠키 배너는 `overlay_coverage≈0.9 / task_control_occlusion=0.0` 이고, 화면 2% 만 덮지만
버튼 위에 정확히 앉은 작은 팝업은 `overlay_coverage≈0.02 / task_control_occlusion=1.0` 이다.
후자가 과업 수행을 막는 쪽이다. page-level 요약값으로 대표하면 이 순위가 뒤집힌다.

## geometry 만으로 modal 의미를 확정하지 않는다 (`03 §9`)

`03 §9` 는 *"geometry overlap 만으로 modal 의미를 확정하지 않는다"* 고 한다. 이 모듈은
그래서 **기하와 의미를 분리해 둘 다 남긴다**:

- 행 단위 `task_control_occlusion` 은 **순수 기하**다. `pointer-events:none` 인 장식
  오버레이라도 겹치면 겹친 비율이 그대로 기록된다. 기하 원자료를 버리지 않는다.
- 그 행이 실제로 과업을 **막았는지**는 별도 축 `blocking_basis` 가 판정하며, 판정에는
  기하 밖의 신호가 필요하다 — task control 지점의 hit-test 결과(`intercepts_task_control`,
  `document.elementFromPoint` 계열 browser-native 신호) 또는 상호작용 포획
  (`traps_interaction`: `aria-modal` / `<dialog>` / body scroll lock).
- 겹치기는 하는데 그 신호가 **미관측**이면 `UNDETERMINED` 이고, measurement 수준
  `task_control_occlusion` 은 `0.0` 이 아니라 `None` 이 된다.

measurement 수준 primary 값은 **blocking 으로 확정된 행에서만** 집계한다. 그래서
"겹쳤지만 안 막았다"(`NOT_BLOCKING`) 와 "겹쳤는데 막았는지 모른다"(`UNDETERMINED`) 가
같은 숫자로 붕괴하지 않는다.

## 산출 불능은 `None` 이다

`0.0` 도 `False` 도 아니다. `0.0` 은 *재 봤더니 가려지지 않았다*, `False` 는 *재 봤더니
없었다* 는 **관측 결과**이고, `None` 은 *잴 수 없었다* 는 뜻이다. 이 셋을 하나로 합치면
하류에서 되살릴 방법이 없다.

## 이 모듈이 하지 않는 것

- **interrupt 라벨을 다시 판정하지 않는다.** `interrupt_type` 은 상류 분류기
  (`engine.l0_collector.classify_interrupt`) 산출을 그대로 옮기며, `InterruptLabel` 폐쇄
  어휘 밖의 값은 받지 않는다(`02 §10` 자유 라벨 생성 금지).
- **dismissal 을 시도하지 않는다.** 조작 결과(`dismiss_attempted` / `dismiss_succeeded_observed`)
  는 입력으로 받는다. 이 모듈은 순수 함수다.
- **실제 서비스에 접속하지 않는다.**
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from ..engine.vocabulary import NAME_ABSENT, InterruptLabel

__all__ = [
    "BBox",
    "BlockingBasis",
    "DismissControlObservation",
    "DismissalState",
    "InterruptObservation",
    "ObstructionMeasurement",
    "ObstructionStatus",
    "TaskObstructionRow",
    "Viewport",
    "measure_task_obstruction",
]


# ── 입력 구조 ────────────────────────────────────────────────────────────────
@dataclass(frozen=True)
class BBox:
    """CSS px 단위 bounding box. `x`/`y` 는 viewport 좌상단 기준."""

    x: float
    y: float
    w: float
    h: float

    @property
    def area(self) -> float:
        return max(0.0, self.w) * max(0.0, self.h)


@dataclass(frozen=True)
class Viewport:
    """`03 §1` 고정 모바일 viewport (`390×844 CSS px`). 분모 보존을 위해 원자료로 받는다."""

    width: float
    height: float

    @property
    def area(self) -> float:
        return max(0.0, self.width) * max(0.0, self.height)


@dataclass(frozen=True)
class DismissControlObservation:
    """probe `raw_features.dismiss_control_candidates[c].dismiss_control_candidates[]` 한 원소.

    이 목록은 probe 단계에서 이미 `matches_close_vocabulary or icon_only` 로 걸러진
    집합이다(`engine/l0_probe.js` "dismiss control 5차"). 즉 **컨테이너 안의 모든 버튼이
    아니라 닫기 후보로 인정된 버튼**만 들어온다. 이 모듈은 그 필터를 다시 적용하지 않는다.
    """

    selector: str
    accessible_name_source: str | None
    matches_close_vocabulary: bool
    icon_only: bool
    hittable: bool
    display: str = "block"
    visibility: str = "visible"
    opacity: float = 1.0
    viewport_overlap_css_px2: float = 0.0
    persistence_hint: bool = False


@dataclass(frozen=True)
class InterruptObservation:
    """한 step 에서 관측된 interrupt 하나. `02 §5` 행 단위(`observation_id + interrupt_id`).

    `visible` / `intercepts_task_control` / `traps_interaction` 이 `None` 이면 **미관측**
    이며 `False`(관측했더니 아니었다)와 섞지 않는다.

    `dismiss_container_observed` 는 *probe 가 이 interrupt 의 컨테이너를 실제로 훑었는가*
    다. `False` 면 `dismiss_control_exists` 는 `False`(닫기 control 없음)가 아니라
    `None`(닫기 control 유무를 재지 못함)이 된다.
    """

    interrupt_id: str
    interrupt_type: str
    selector: str
    visible: bool | None
    box: BBox | None
    viewport_coverage: float | None
    intercepts_task_control: bool | None = None
    traps_interaction: bool | None = None
    dismiss_container_observed: bool = True
    dismiss_controls: tuple[DismissControlObservation, ...] = ()
    dismiss_attempted: bool = False
    dismiss_succeeded_observed: bool | None = None
    dismiss_failure_mode: str | None = None


# ── 판정 축 ──────────────────────────────────────────────────────────────────
class BlockingBasis(StrEnum):
    """이 interrupt 가 task 를 막았다고 볼 **근거**. `03 §9` 대응 축이다.

    - `POINTER_INTERCEPT` — task control 지점의 hit-test 가 이 오버레이를 돌려줬다.
      기하 겹침 + 입력 가로채기가 **둘 다** 확인된 경우다.
    - `MODAL_TRAP` — `aria-modal` / `<dialog>` / body scroll lock 으로 상호작용을
      포획했다. 이 경우 task control 과 기하적으로 겹치지 않아도 막는다.
    - `NOT_BLOCKING` — 관측했고, 막지 않았다. (안 보이거나, 안 겹치거나,
      겹쳤지만 입력을 가로채지 않았다 — 예: `pointer-events:none` 장식 오버레이.)
    - `UNDETERMINED` — 이 자료로는 확정할 수 없다. **기하 겹침만으로 blocking 이라고
      단정하지 않는다.** 이 값은 `NOT_BLOCKING` 과 다르며 상류로 합치지 않는다.
    """

    POINTER_INTERCEPT = "POINTER_INTERCEPT"
    MODAL_TRAP = "MODAL_TRAP"
    NOT_BLOCKING = "NOT_BLOCKING"
    UNDETERMINED = "UNDETERMINED"


#: `blocking` 으로 **확정된** 근거들. measurement 수준 primary 집계 모집단의 정의다.
BLOCKING_BASES: frozenset[BlockingBasis] = frozenset(
    {BlockingBasis.POINTER_INTERCEPT, BlockingBasis.MODAL_TRAP}
)


class DismissalState(StrEnum):
    """**"닫을 대상이 없다" / "닫기 control 이 없다" / "닫기가 실패했다" 는 서로 다른 상태다.**

    셋을 하나로 합치면 안 된다. legacy 자료에서 이 구분 부재가 실증됐다 — 합치면
    *방해요소가 애초에 없어서 안 닫은 것*과 *닫으려 했는데 닫기 버튼이 없던 것*과
    *버튼을 눌렀는데 안 닫힌 것*이 같은 값으로 나온다. 앞의 하나는 접근성 문제가 아니고
    뒤의 둘은 서로 다른 접근성 문제다.

    - `NO_TARGET` — **닫을 대상이 없다.** 이 interrupt 는 task 를 막지 않으므로
      dismissal 대상이 아니다. measurement 수준에서는 blocking 모집단이 비어 있다는 뜻.
      `dismiss_control_exists` 는 `False` 가 아니라 `None` (잴 대상이 없었다).
    - `NO_CONTROL` — **닫기 control 이 없다.** 막고 있는데 허용된 닫기 control 이
      컨테이너 안에 없다. `dismiss_control_exists = False` — 이건 관측 결과다.
    - `CONTROL_PRESENT_NOT_ATTEMPTED` — 닫기 control 은 있고, 조작을 시도하지 않았다.
      `dismiss_succeeded` 는 `None` 이다(실패가 아니다).
    - `DISMISS_FAILED` — **닫기가 실패했다.** 시도했고 상태가 안 바뀌었다.
      `dismiss_control_exists = True`, `dismiss_succeeded = False`.
    - `DISMISS_SUCCEEDED` — 시도했고 제거됐다.
    - `UNDETERMINED` — 위 어디로도 확정할 수 없다(컨테이너 미관측 등).
    """

    NO_TARGET = "NO_TARGET"
    NO_CONTROL = "NO_CONTROL"
    CONTROL_PRESENT_NOT_ATTEMPTED = "CONTROL_PRESENT_NOT_ATTEMPTED"
    DISMISS_FAILED = "DISMISS_FAILED"
    DISMISS_SUCCEEDED = "DISMISS_SUCCEEDED"
    UNDETERMINED = "UNDETERMINED"


class ObstructionStatus(StrEnum):
    """measurement 전체의 산출 상태.

    - `MEASURED` — primary 와 dismiss 4필드가 전부 확정됐다.
    - `PARTIAL` — primary 는 확정됐으나 일부 축이 미확정이다.
    - `UNDETERMINED` — primary(`task_control_occlusion`)를 산출하지 못했다.
    """

    MEASURED = "MEASURED"
    PARTIAL = "PARTIAL"
    UNDETERMINED = "UNDETERMINED"


# ── 산출 구조 ────────────────────────────────────────────────────────────────
@dataclass(frozen=True)
class TaskObstructionRow:
    """`02 §5 fact_task_obstruction` 한 행 = 한 observation 의 한 interrupt.

    `task_control_occlusion` 은 이 행에서는 **순수 기하값**이다(blocking 여부와 무관).
    의미 판정은 `blocking_basis` 가 따로 들고 있다.
    """

    interrupt_id: str
    interrupt_type: str
    overlay_coverage: float | None
    task_control_occlusion: float | None
    blocking_basis: BlockingBasis
    dismiss_control_exists: bool | None
    dismiss_control_visible: bool | None
    dismiss_control_accessible_name: str | None
    dismiss_required_for_task: bool | None
    dismiss_succeeded: bool | None
    dismissal_state: DismissalState


@dataclass(frozen=True)
class ObstructionMeasurement:
    """한 step 의 task-specific obstruction 측정 결과.

    `rows` 는 `fact_task_obstruction` 원자료(interrupt 단위)를 그대로 보존하고, 나머지
    스칼라는 `fact_flow_observation` 이 쓰는 step 단위 요약이다. **요약은 원자료를
    대체하지 않는다** — 둘 다 남긴다.
    """

    task_control_occlusion: float | None
    overlay_coverage: float | None
    dismiss_control_exists: bool | None
    dismiss_control_visible: bool | None
    dismiss_control_accessible_name: str | None
    dismiss_required_for_task: bool | None
    dismiss_succeeded: bool | None
    forced_dismissal_count: int
    dismissal_state: DismissalState
    status: ObstructionStatus
    blocking_population: tuple[str, ...]
    representative_interrupt_id: str | None
    rows: tuple[TaskObstructionRow, ...]


# ── 기하 ─────────────────────────────────────────────────────────────────────
def _overlap_area(a: BBox | None, b: BBox | None) -> float | None:
    if a is None or b is None:
        return None
    w = max(0.0, min(a.x + a.w, b.x + b.w) - max(a.x, b.x))
    h = max(0.0, min(a.y + a.h, b.y + b.h) - max(a.y, b.y))
    return w * h


def _occlusion(interrupt_box: BBox | None, control_box: BBox | None) -> float | None:
    """task control bbox 면적 대비 겹침 비율. 분모가 0 이거나 bbox 가 없으면 `None`."""
    if control_box is None or control_box.area <= 0:
        return None
    overlap = _overlap_area(interrupt_box, control_box)
    if overlap is None:
        return None
    return round(min(1.0, overlap / control_box.area), 4)


def _blocking_basis(interrupt: InterruptObservation, occlusion: float | None) -> BlockingBasis:
    """`03 §9` — 기하 겹침만으로 blocking 을 확정하지 않는다."""
    if interrupt.visible is False:
        return BlockingBasis.NOT_BLOCKING
    if interrupt.visible is None:
        return BlockingBasis.UNDETERMINED
    if interrupt.traps_interaction is True:
        # 상호작용 포획은 기하 겹침과 무관하게 task 경로를 막는다.
        return BlockingBasis.MODAL_TRAP
    if occlusion is None:
        # 기하를 못 쟀다 — hit-test 단독 신호가 있으면 그것으로 확정한다.
        if interrupt.intercepts_task_control is True:
            return BlockingBasis.POINTER_INTERCEPT
        if interrupt.intercepts_task_control is False:
            return BlockingBasis.NOT_BLOCKING
        return BlockingBasis.UNDETERMINED
    if occlusion <= 0:
        # task control 을 안 가린다. 포획 여부가 미관측이면 확정하지 않는다.
        if interrupt.traps_interaction is False:
            return BlockingBasis.NOT_BLOCKING
        return BlockingBasis.UNDETERMINED
    if interrupt.intercepts_task_control is True:
        return BlockingBasis.POINTER_INTERCEPT
    if interrupt.intercepts_task_control is False:
        # 겹치지만 입력을 가로채지 않는다 (`pointer-events:none` 등).
        return BlockingBasis.NOT_BLOCKING
    return BlockingBasis.UNDETERMINED


# ── dismiss 4필드 ────────────────────────────────────────────────────────────
#
# ## `dismiss_control_exists` 계열 4필드 — 세 축 조작적 정의 (`T-A-V3-P0-003 ruling_11`)
#
# 이 네 필드(`dismiss_control_exists` · `dismiss_control_visible` ·
# `dismiss_control_accessible_name` · `dismiss_succeeded`)는 **단위 · 모집단 · 원천 필드**
# 세 축이 미명시인 채로 쓰이면 두 독립 구현이 같은 동결 DOM 에서 다른 수를 낸다. 실제로
# C 와 D 가 같은 자료에서 `3/54` 와 `38/53` 을 얻었다. 두 수는 **충돌이 아니라 서로 다른
# 양**이다 — 아래 축 정의가 다르면 다른 수가 나오는 게 정상이다.
#
# ### 축 1 — 단위 (unit)
#
# **행 단위는 `observation_id + interrupt_id` 다. target 이 아니고 step 도 아니다.**
# `02 §5 fact_task_obstruction` 의 행 키가 그렇게 정의돼 있다. 한 step 에 interrupt 가
# n 개면 이 네 필드는 n 개 값을 갖는다.
#
# `ObstructionMeasurement` 의 동명 스칼라는 **step 단위 파생 요약**이며, target 단위가
# 아니다. 요약 방식은 아래 "대표 행 축약"으로 고정한다 — 필드별로 제각기 집계하면
# (예: exists 는 any, name 은 first) 서로 다른 interrupt 의 값이 한 행에 섞여 실재하지
# 않는 조합이 만들어진다.
#
#   대표 행 = blocking 모집단 중 `task_control_occlusion` 이 최대인 행,
#             동률이면 `interrupt_id` 사전순 최소.
#
# target 단위 수치가 필요하면 step 요약을 다시 집계해야 하며, 그 집계 규칙은 이 모듈이
# 정하지 않는다(명세 공백 — 보고 대상).
#
# ### 축 2 — 모집단 (population)
#
# **전체가 아니라 조건부다.** step 요약의 분모는
#
#   `P_blocking = { i ∈ interrupts : blocking_basis(i) ∈ {POINTER_INTERCEPT, MODAL_TRAP} }`
#
# 즉 *이 step 에서 사전지정 task 진입 control 을 실제로 막은 것으로 확정된 interrupt* 다.
# 다음 세 모집단과 명시적으로 다르다:
#
#   (a) `raw_features.modal_overlay_candidates[]` 전체 — `visible=false` 를 포함한다.
#   (b) `(a)` 중 `visible=true` — legacy `engine.l0_collector._build_interrupts` 의 모집단.
#       task 와 무관한 오버레이를 전부 포함한다.
#   (c) `raw_features.dismiss_control_candidates[]` 컨테이너 전체 — probe 가
#       `dialog`/`[role=dialog]`/`[aria-modal]` 에 더해 **모든 `position:fixed|sticky`
#       및 `z-index>=100` 요소**를 컨테이너로 올린다(`l0_probe.js`). 페이지당 수십 개가
#       정상이며 대부분은 오버레이가 아니다.
#
# `|P_blocking| = 0` 이면 **닫을 대상이 없다**. 네 필드는 전부 `None` 이고 `False` 가
# 아니다. `dismissal_state = NO_TARGET`.
#
# [추정] C `3/54` 대 D `38/53` 의 자릿수 차이는 (b) 대 (c) 의 차이와 규모가 맞는다.
# 이 모듈은 그 재구성을 사실로 주장하지 않는다 — 세 축을 못박아 **두 독립 구현이 같은
# 양을 재는지 검정할 수 있게** 만드는 것이 목적이다. 대조는 C/D 가 각자 자기 모집단을
# 위 (a)/(b)/(c)/`P_blocking` 중 무엇으로 잡았는지 밝혀 수행한다.
#
# ### 축 3 — 원천 필드 (source field)
#
# 모두 `probe.raw_features` 에서 온다. 다른 이름의 필드로 대체하지 않는다.
#
# | 필드 | 원천 |
# |---|---|
# | `dismiss_control_exists` | `dismiss_control_candidates[c].dismiss_control_candidates[]` 가 비어 있지 않은가. `c.container_selector == interrupt.selector` 로 결합한다. probe 가 이미 `matches_close_vocabulary or icon_only` 로 걸러 둔 집합이다. 컨테이너 자체가 미관측이면 `None`. |
# | `dismiss_control_visible` | 대표 control 의 `display != "none"` ∧ `visibility != "hidden"` ∧ `opacity > 0.01` ∧ `viewport_overlap_css_px2 > 0` ∧ `hittable == true`. 대표 control = `hittable` 인 첫 원소, 없으면 첫 원소. |
# | `dismiss_control_accessible_name` | 대표 control 의 `accessible_name_source`. control 은 있는데 이름이 비면 `NAME_ABSENT`(이름 없음이 **관측**됨), control 자체가 없으면 `None`(잴 대상 없음). 두 값을 섞지 않는다. |
# | `dismiss_succeeded` | L0-c 조작 결과 `dismiss_succeeded_observed`. **시도하지 않았으면 `None`** 이며 `False`(시도했는데 실패)와 섞지 않는다. |
#
# `dismiss_required_for_task` 는 위 네 필드와 축이 다르다 — 모집단이 `P_blocking` 이
# 아니라 **관측된 interrupt 전체**이고, 값은 "이 interrupt 를 닫지 않으면 task 를
# 진행할 수 없는가" 다. 행 단위로는 `blocking_basis` 의 재표현이며,
# step 단위로는 `|P_blocking| > 0` 이다.


def _representative_control(
    controls: tuple[DismissControlObservation, ...],
) -> DismissControlObservation | None:
    if not controls:
        return None
    return next((c for c in controls if c.hittable), controls[0])


def _dismiss_fields(
    interrupt: InterruptObservation, basis: BlockingBasis
) -> tuple[bool | None, bool | None, str | None, bool | None, DismissalState]:
    """(exists, visible, accessible_name, succeeded, state) — 축 3 표 그대로."""
    if basis not in BLOCKING_BASES:
        # 닫을 대상이 아니다. `False` 가 아니라 `None`.
        return None, None, None, None, DismissalState.NO_TARGET

    if not interrupt.dismiss_container_observed:
        return None, None, None, None, DismissalState.UNDETERMINED

    control = _representative_control(interrupt.dismiss_controls)
    if control is None:
        # 막고 있는데 닫기 control 이 없다 — 관측 결과로서의 부재.
        return False, None, None, None, DismissalState.NO_CONTROL

    visible = (
        control.display != "none"
        and control.visibility != "hidden"
        and control.opacity > 0.01
        and control.viewport_overlap_css_px2 > 0
        and control.hittable
    )
    name = control.accessible_name_source or NAME_ABSENT

    if not interrupt.dismiss_attempted:
        return True, visible, name, None, DismissalState.CONTROL_PRESENT_NOT_ATTEMPTED
    if interrupt.dismiss_succeeded_observed is None:
        return True, visible, name, None, DismissalState.UNDETERMINED
    if interrupt.dismiss_succeeded_observed:
        return True, visible, name, True, DismissalState.DISMISS_SUCCEEDED
    return True, visible, name, False, DismissalState.DISMISS_FAILED


# ── 진입점 ───────────────────────────────────────────────────────────────────
def measure_task_obstruction(
    interrupts: list[InterruptObservation] | tuple[InterruptObservation, ...],
    task_control_bbox: BBox | None,
    viewport: Viewport,
) -> ObstructionMeasurement:
    """한 step 의 task-specific obstruction 을 잰다.

    `task_control_bbox` 가 `None` 이면 (task 진입 control 을 아직 못 찾았거나 가려져서
    bbox 를 못 잰 경우) primary 는 `None` 이 되고 `status = UNDETERMINED` 다. `0.0` 으로
    바꾸지 않는다 — `0.0` 은 *control 을 봤고 가려지지 않았다* 는 뜻이기 때문이다.

    `viewport` 는 `overlay_coverage` 의 분모를 감사할 수 있도록 받는다. 이 모듈은
    `viewport_coverage` 를 재계산하지 않고 probe 관측값을 그대로 옮긴다 — 재계산하면
    probe 의 clip/scroll 처리와 어긋난다. 다만 분모가 0 이면(비정상 viewport) 보조값을
    신뢰할 수 없으므로 `overlay_coverage` 를 `None` 으로 돌린다.

    Raises:
        ValueError: `interrupt_type` 이 `InterruptLabel` 폐쇄 어휘 밖일 때
            (`02 §10` 자유 라벨 생성 금지), 또는 `interrupt_id` 가 중복일 때
            (`02 §8` observation identity).
    """
    seen: set[str] = set()
    rows: list[TaskObstructionRow] = []

    for interrupt in interrupts:
        if interrupt.interrupt_type not in InterruptLabel.__members__:
            raise ValueError(
                f"폐쇄 어휘 밖의 interrupt_type: {interrupt.interrupt_type!r} "
                f"(interrupt_id={interrupt.interrupt_id!r})"
            )
        if interrupt.interrupt_id in seen:
            raise ValueError(f"중복 interrupt_id: {interrupt.interrupt_id!r}")
        seen.add(interrupt.interrupt_id)

        occlusion = _occlusion(interrupt.box, task_control_bbox)
        basis = _blocking_basis(interrupt, occlusion)
        exists, visible, name, succeeded, state = _dismiss_fields(interrupt, basis)

        required: bool | None
        if basis in BLOCKING_BASES:
            required = True
        elif basis is BlockingBasis.UNDETERMINED:
            required = None
        else:
            required = False

        rows.append(
            TaskObstructionRow(
                interrupt_id=interrupt.interrupt_id,
                interrupt_type=interrupt.interrupt_type,
                overlay_coverage=(interrupt.viewport_coverage if viewport.area > 0 else None),
                task_control_occlusion=occlusion,
                blocking_basis=basis,
                dismiss_control_exists=exists,
                dismiss_control_visible=visible,
                dismiss_control_accessible_name=name,
                dismiss_required_for_task=required,
                dismiss_succeeded=succeeded,
                dismissal_state=state,
            )
        )

    blocking_rows = [r for r in rows if r.blocking_basis in BLOCKING_BASES]
    undetermined_rows = [r for r in rows if r.blocking_basis is BlockingBasis.UNDETERMINED]

    # ── primary: blocking 으로 확정된 행에서만 집계한다 ──────────────────────
    occlusion_values = [
        r.task_control_occlusion for r in blocking_rows if r.task_control_occlusion is not None
    ]
    agg_occlusion: float | None
    if task_control_bbox is None or task_control_bbox.area <= 0:
        agg_occlusion = None
    elif occlusion_values:
        agg_occlusion = max(occlusion_values)
    elif undetermined_rows or any(r.task_control_occlusion is None for r in blocking_rows):
        # 막았을 수도 있는 것이 남아 있다 — `0.0`(안 가려짐)으로 단정하지 않는다.
        agg_occlusion = None
    else:
        agg_occlusion = 0.0

    # ── 보조: page-level 요약. 순위 대표로 쓰지 않는다 (`02 §5`) ─────────────
    coverage_values = [
        r.overlay_coverage
        for r, i in zip(rows, interrupts, strict=True)
        if r.overlay_coverage is not None and i.visible is not False
    ]
    agg_coverage: float | None
    if viewport.area <= 0:
        agg_coverage = None
    elif coverage_values:
        agg_coverage = max(coverage_values)
    elif any(i.visible is not False and i.viewport_coverage is None for i in interrupts):
        agg_coverage = None
    else:
        agg_coverage = 0.0

    # ── dismiss 4필드: 대표 행 축약 (축 1) ──────────────────────────────────
    representative = None
    if blocking_rows:
        representative = min(
            blocking_rows,
            key=lambda r: (-(r.task_control_occlusion or 0.0), r.interrupt_id),
        )

    if representative is None:
        agg_exists: bool | None = None
        agg_visible: bool | None = None
        agg_name: str | None = None
        agg_succeeded: bool | None = None
        agg_state = DismissalState.UNDETERMINED if undetermined_rows else DismissalState.NO_TARGET
    else:
        agg_exists = representative.dismiss_control_exists
        agg_visible = representative.dismiss_control_visible
        agg_name = representative.dismiss_control_accessible_name
        agg_succeeded = representative.dismiss_succeeded
        agg_state = representative.dismissal_state

    # `dismiss_required_for_task` 는 모집단이 다르다 — interrupt 전체에서 본다.
    agg_required: bool | None
    if blocking_rows:
        agg_required = True
    elif undetermined_rows:
        agg_required = None
    else:
        agg_required = False

    # `04 §4` — task 진행에 **실제 필요했던** dismissal 수. 확정된 성공만 센다.
    forced = sum(1 for r in blocking_rows if r.dismiss_succeeded is True)

    if agg_occlusion is None:
        status = ObstructionStatus.UNDETERMINED
    elif (
        undetermined_rows
        or agg_state is DismissalState.UNDETERMINED
        or agg_coverage is None
        or any(r.blocking_basis is BlockingBasis.UNDETERMINED for r in rows)
    ):
        status = ObstructionStatus.PARTIAL
    else:
        status = ObstructionStatus.MEASURED

    return ObstructionMeasurement(
        task_control_occlusion=agg_occlusion,
        overlay_coverage=agg_coverage,
        dismiss_control_exists=agg_exists,
        dismiss_control_visible=agg_visible,
        dismiss_control_accessible_name=agg_name,
        dismiss_required_for_task=agg_required,
        dismiss_succeeded=agg_succeeded,
        forced_dismissal_count=forced,
        dismissal_state=agg_state,
        status=status,
        blocking_population=tuple(r.interrupt_id for r in blocking_rows),
        representative_interrupt_id=(
            representative.interrupt_id if representative is not None else None
        ),
        rows=tuple(rows),
    )
