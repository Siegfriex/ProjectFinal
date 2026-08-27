"""V3 Surface layer — task-entry control 의 표면 측정 순수함수 (W5C).

정본: `SSOTV3/04_FLOW_CODEBOOK_v3.0.md` §4 표 · §5 · §6 · §7,
      `SSOTV3/02_DATA_SCHEMA_v3.0.md` §3 `fact_surface_state`,
      `SSOTV3/00_SSOT_v3.0_CROSS_SERVICE_FLOW.md` §8.

이 모듈은 **순수함수 하나**만 공개한다. 네트워크·파일·브라우저를 건드리지 않고,
이미 수집된 L0 probe 산출물과 이미 결정된 task-entry control binding 을 입력으로 받아
`fact_surface_state` 의 surface/geometry/label 필드를 계산한다. 판정 임계값을 갖는 곳은
여기이며, 원시 관측은 `engine/l0_probe.js` 가 이미 끝냈다.

## 이 모듈의 존재 이유 — visible label 과 accessible name 의 분리 (00 §8 · 04 §7)

`visible_label_text` 는 **사람이 화면에서 실제 보는 rendered text** 이고,
`accessible_name` 은 **브라우저 AX naming computation 의 결과** 다. 둘은 다른 것이고
절대 한쪽으로 대체하지 않는다. 그래서 이 모듈은 accessible name 을 **계산하지 않는다** —
DOM 속성으로 추정하면 그 순간 두 값이 같은 출처가 되어 분리가 무너진다. accessible name 은
호출자가 `task_control["ax_node"]`(CDP `Accessibility.getFullAXTree` 의 slim node,
`engine/l0_collector.py::L0Collector._ax_tree` 산출 형태)로 넘겨야 한다. 없으면
`accessible_name = None` 이고 `notes` 에 `AX_NODE_ABSENT` 가 남는다.

같은 이유로 `ICON_ONLY_AX_NAMED`(아이콘만 보이지만 AX 이름은 있음)와
`ICON_ONLY_UNNAMED`(AX 이름도 없음)를 반드시 구분한다. 접근성 관점에서 완전히 다른 상태다.

## 입력 형태

### `probe_state`

`engine/l0_probe.js` 산출물 그대로다. 두 형태를 받는다.

1. 단일 scroll state — probe 산출물 자체::

       {"probe_version": ..., "url": ..., "raw_features": {...},
        "state_index": "S0",   # 선택. 없으면 "S0"
        "scroll_y": 0}         # 선택

2. 다중 scroll state 번들::

       {"scroll_states": [<위 1번 형태>, <위 1번 형태>, ...]}

   `scroll_states` 는 주어진 순서대로 S0, S1, ... 로 본다. 각 원소가 `state_index` 를
   가지면 그 값을 쓰고, 없으면 인덱스로 `S{i}` 를 만든다.

   **KNOWN LIMITATION**: 03 §3 은 "고정 scroll 정책으로 S1...Sn 을 만든다"고만 하고 그
   번들의 직렬화 형태를 정의하지 않았다. base SHA 시점 코드베이스에는 scroll state 수집
   구현이 없다(`grep scroll_state|state_index|scroll_y` → 0건). 위 `scroll_states` 키
   이름은 **W5C 가 정한 것**이며 SSOTV3 에 근거가 없다.

### `task_control`

이미 확정된 task-entry control binding (03 §4 "Task-specific Candidate Binding").
후보 선정 자체는 이 모듈의 일이 아니다.

- `selector` (필수) — probe 가 만든 안정 selector. probe 의
  `primary_action_candidates` / `accessible_name_sources` / `utility_input_widgets` /
  `region_signals.search_inputs` 에서 이 selector 로 control 레코드를 찾아 병합한다.
- `ax_node` (선택) — AX tree slim node
  `{"role", "name", "name_computed", "ignored", ...}`. accessible name 의 유일한 출처.
- `nav_container_type` (선택) — 04 §4 `nav_container_type` enum. Flow 레이어(다른 worker)
  가 판정한 값을 **참조만** 한다. Δ15 GAP-06 에 따라 이 값은 **task-entry control 을 직접
  담고 있는 가장 안쪽 container** 다. DRAWER zone 과 `entry_observed_state` 판정에 쓴다.
- `nav_container_chain` (선택) — 바깥→안쪽 순서의 container 배열. 주어지면 최내곽은
  `chain[-1]` 이고 chain 전체를 원자료로 보존한다. `nav_container_type` 과 최내곽이
  다르면 chain 을 쓰고 `NAV_CONTAINER_CHAIN_TYPE_MISMATCH` note 를 남긴다.
- `computed_position` (선택) — 해당 요소의 computed CSS `position`
  (`l0_collector._COMPUTED_CSS_PROPERTIES` 에 수집됨). FLOATING zone 판정에 쓴다.

### `viewport`

`(width, height)` CSS px. 03 §1 은 `390×844` 를 고정한다. 정규화 분모로 쓴다.

## entry_zone 경계 — A `T-A-V3-STEP1-003` R7 사전등록 정의

04 §4 는 `entry_zone` 값 목록만 주고 경계 수치를 주지 않는다. 그 공백은 A 티켓
`T-A-V3-STEP1-003` R7 에서 확정됐고(D 제기 → C 가 SSOTV3 전수 grep 으로 독립 확인 →
A 확정), **REAL 접속 누적 0건 상태에서 정해져 result-blind 다.** 아래는 그 정의의 구현이며
W5C 가 정한 값이 아니다.

좌표 기준은 control bbox 중심을 그 state 의 viewport(03 §1 기준 390×844 CSS px)로
정규화한 값이다. scroll 상태와 무관하게 **그 state 의 viewport** 를 분모로 쓴다.

y 밴드 (하한 포함 · 상한 배제 `[a, b)`)::

    y_norm <  1/3            → TOP
    1/3 <= y_norm <  2/3     → MID
    y_norm >= 2/3            → BOTTOM

TOP 안에서만 x 삼등분 (같은 `[a, b)`)::

    x_norm <  1/3            → TOP_LEFT
    1/3 <= x_norm <  2/3     → TOP_CENTER
    x_norm >= 2/3            → TOP_RIGHT

**MID / BOTTOM 에는 x 삼등분을 적용하지 않는다.** 04 값 목록에 `MID_LEFT` 류가 없기
때문이다.

`[a, b)` 는 x 와 y 양쪽에 일관 적용한다. 따라서 `y = 1/3` 은 **MID** 이고 `y = 2/3` 은
**BOTTOM**, TOP band 안에서 `x = 1/3` 은 **TOP_CENTER** 다.

R7 원문의 마지막 예시 문장("정확히 1/3 인 점은 TOP 이자 TOP_CENTER 다")은 밴드 표와
어긋난다 — `y = 1/3` 이 TOP 이면 `[a, b)` 통일이 깨지고, MID 는 x 삼등분을 하지 않으므로
그 점에서 `TOP_CENTER` 가 산출될 수도 없다. D 가 발견하고 B 가 A 원문으로 독립 재현,
C 가 원문 재확인한 뒤 **A 가 `T-A-FC-001` 로 밴드 표를 정본으로 시정했다.** 이 구현은
시정된 밴드 표를 따른다. 나중에 R7 원문의 그 문장을 다시 읽는 사람을 위해 여기 남긴다.

### 구조적 override — 기하보다 우선한다

`FLOATING` 과 `DRAWER` 는 위치값이 아니라 **구조값**이라 기하 계산을 덮는다.

- `FLOATING`: computed `position` 이 `fixed`/`sticky` 여서 일반 흐름을 벗어나 viewport 에
  고정된 경우.
- `DRAWER`: control 이 reveal 을 요구하는 nav container 안에 있는 경우 —
  `menu_dependency = 1` 을 만든 바로 그 container.
- **둘 다 해당하면 `DRAWER` 가 우선한다.** A 근거: reveal 필요 여부가 사용자에게 더 큰
  구조적 부담이다.

### override 가 걸려도 좌표는 그대로 저장한다

04 §6 이 "좌표 원자료를 버리지 않는다" 를 이미 정했고, A 가 zone 을 blocking 이 아니라고
판정한 근거가 바로 이것이다 — **원좌표가 남아 있으면 zone 은 언제든 재도출 가능해서
재수집이 필요 없다.** 그래서 `FLOATING`/`DRAWER` 로 판정돼도
`entry_x_norm`/`entry_y_norm` 은 기하 그대로 채워지며, clamp 하지 않은
`entry_x_norm_raw`/`entry_y_norm_raw` 와 원 bbox `entry_box_css_px` 도 함께 남는다.

## W5C 가 정한 나머지 임계값 — 04 에 명시가 없다

zone 경계와 달리 아래는 **W5C 가 정했고** SSOTV3 근거가 없다.

- `CARD_MIN_AREA_CSS_PX2 = 8000.0`, `CARD_MIN_SIDE_CSS_PX = 64.0` — CARD 최소 크기
- `HAMBURGER_NAME_LEXICON` — 고정 어휘 목록(아래 상수)
- `_DRAWER_CONTAINERS` — 04 `nav_container_type` 중 drawer 로 보는 부분집합
- `entry_control_type` 판정 순서

## 인접 계약

- **`dom_order`** (`A2 §1.13` · `l0_collector.min4_sort_key`): probe 후보는 `dom_order` 를
  반드시 실어야 하고 비면 `Min4ProbeContractError` 다. 이 모듈은 후보 dict 를 만들지도
  변형하지도 않으므로 계약을 통과시키기만 한다 — 입력 probe 를 그대로 읽고 새 후보 열을
  생성하지 않는다.
- **`TaskContract`**: 이 함수는 task contract 타입을 쓰지 않는다. `task_control` 은
  contract 가 아니라 **이미 결정된 binding 사실**(selector · AX node · container · position)
  이다. contract 타입이 필요해지면 W5A `v3_runner/contracts.py` 에서 import 하고 자체
  정의를 만들지 않는다.

## Δ15 (`T-A-V3-STEP1-012`) 가 닫은 공백

- **GAP-07 / `entry_observed_state`**: `entry_*` 기하는 control 이 최초로 관측 가능해진
  state 기준이다. reveal-gated 면 reveal 이후이고, S0 에 없는 것의 좌표를 `0` 이나
  추정치로 적지 않는다. 모든 행이 `entry_observed_state` 로 자기 시점을 선언한다
  (`"S0"`/`"S1"`/… 또는 `"POST_REVEAL:<nav_container_type>"`).
  `s0_task_control_visible` 과 충돌하지 않는다 — 그것은 여전히 S0 사실이다.
- **GAP-06 / `nav_container_chain`**: `nav_container_type` 은 최내곽 container 이고
  chain 전체를 함께 보존한다.
- **GAP-05 / occlusion 무파생**: `s0_task_control_visible` 은 "S0 viewport 안에 bbox 가
  교차하고 hit-testable 한가" 이고, `task_control_occlusion` 과 **어떤 파생 관계도 갖지
  않는다.** 그래서 이 모듈은 occlusion 을 입력으로 받지도 산출하지도 않는다.
- **GAP-02 / `first_visible_scroll_state`**: control 이 최초로 관측된 scroll state 다.
  reveal 로 나타났으면 그 reveal 이 일어난 scroll state(보통 S0)이지 NULL 이 아니다.
  NULL 은 끝내 관측하지 못한 경우뿐이고 사유는 note 로 남는다.
- **GAP-04 / 결측 표기**: 수치 미관측은 `None`(`0` 아님), 범주 미관측은 `NOT_OBSERVED`
  (빈 문자열 아님, `OTHER` 같은 실측값 아님). **한 행 안에서 두 표기를 섞지 않는다.**

## DOM 과 AX 가 control 존재에서 갈릴 때

W5E 가 `evidence_defect` fixture 에서 DOM `querySelector` 는 button 을 못 찾고
`shadowRoot` 도 `null` 인데 Chrome AX full tree 에는 이름 있는 button 이 있는 경우를
관측했다. A 판정: **둘이 다를 때 어느 쪽도 우선하지 않는다.** 둘 다 기록하고
`dom_ax_divergence` 를 세운다. 한쪽을 정본으로 삼으면 그 divergence 가 데이터에서
사라지는데, 그것은 보조기술 사용자와 시각 사용자가 다른 화면을 보고 있다는 **관측**이므로
버릴 것이 아니라 결과다. 00 §8 의 label 분리를 control 존재 자체로 확장한 것이다.

`ax_node` 키를 아예 넘기지 않은 것은 "AX 에 없다" 가 아니라 "호출자가 알려주지 않았다"
이므로 divergence 판정에서 제외하고 `AX_NODE_ABSENT` note 만 남긴다.

## SEMANTIC_EQUIV 를 내지 않는다

04 §5: "Unicode normalize + whitespace normalize 후 exact; 사전 고정 synonym map 으로
semantic-equivalent 를 별도 표시. embedding similarity 만으로 자동 merge 금지."

**그 고정 synonym map 이 SSOTV3 어디에도 없다.** 그래서 이 모듈은 `SEMANTIC_EQUIV` 를
절대 반환하지 않는다. map 이 생기면 `_SYNONYM_MAP` 을 채우는 것만으로 활성화된다.
"""

from __future__ import annotations

import unicodedata
from dataclasses import dataclass, field
from typing import Any

__all__ = [
    "CARD_MIN_AREA_CSS_PX2",
    "CARD_MIN_SIDE_CSS_PX",
    "NOT_OBSERVED",
    "ZONE_BOTTOM_Y_MIN",
    "ZONE_LEFT_X_MAX",
    "ZONE_RIGHT_X_MIN",
    "ZONE_TOP_Y_MAX",
    "SurfaceMeasurement",
    "measure_surface",
    "normalize_label",
]

# ── entry_zone 경계 — A `T-A-V3-STEP1-003` R7 확정 (result-blind 사전등록) ──
#: `y_norm < 1/3` 이면 TOP band. 하한 포함 · 상한 배제.
ZONE_TOP_Y_MAX = 1.0 / 3.0
#: `y_norm >= 2/3` 이면 BOTTOM.
ZONE_BOTTOM_Y_MIN = 2.0 / 3.0
#: TOP band 안에서만 쓰는 x 삼등분 경계. MID/BOTTOM 에는 적용하지 않는다.
ZONE_LEFT_X_MAX = 1.0 / 3.0
ZONE_RIGHT_X_MIN = 2.0 / 3.0

#: GAP-04 결측 표기 규약 — 범주 필드의 미관측은 명시적 표지로 적는다. 빈 문자열도
#: 아니고, 관측된 값처럼 보이는 대체값(`OTHER` 등)도 아니다. 수치 필드의 미관측은 `None`
#: 이며 `0` 이 아니다. 한 행 안에서 두 표기를 섞지 않는다.
NOT_OBSERVED = "NOT_OBSERVED"

#: 04 §4 `nav_container_type` 중 "reveal 이 필요 없음" 을 뜻하는 값들.
_NO_REVEAL_CONTAINERS = frozenset({"NONE", ""})

# ── W5C 가 정한 임계값 (04 에 명시 없음) ────────────────────────────────────
CARD_MIN_AREA_CSS_PX2 = 8000.0
CARD_MIN_SIDE_CSS_PX = 64.0

#: 04 §4 `nav_container_type` 값 중 "서랍형 reveal container" 로 보는 부분집합.
#: TOP_DROPDOWN/INLINE_EXPAND 는 drawer 로 보지 않는다 (W5C 결정).
_DRAWER_CONTAINERS = frozenset(
    {"HAMBURGER", "LEFT_DRAWER", "RIGHT_DRAWER", "BOTTOM_SHEET", "MODAL_MENU"}
)

#: computed CSS `position` 중 FLOATING 으로 보는 값 (W5C 결정).
_FLOATING_POSITIONS = frozenset({"fixed", "sticky"})

#: HAMBURGER control 판정용 고정 어휘. casefold + NFKC + whitespace normalize 후 비교.
#: **W5C 가 정한 목록**이며 SSOTV3 에 근거가 없다.
HAMBURGER_NAME_LEXICON = frozenset(
    {
        "메뉴",
        "메뉴열기",
        "메뉴 열기",
        "전체메뉴",
        "전체 메뉴",
        "전체보기",
        "네비게이션",
        "내비게이션",
        "gnb",
        "menu",
        "main menu",
        "open menu",
        "navigation",
        "navigation menu",
        "site menu",
    }
)

#: 04 §5 가 요구하는 "사전 고정 synonym map". SSOTV3 에 아직 존재하지 않아 비어 있고,
#: 비어 있는 동안 `SEMANTIC_EQUIV` 는 반환되지 않는다.
_SYNONYM_MAP: dict[str, str] = {}

_ROLE_SEARCHBOX = frozenset({"searchbox", "combobox"})
_ROLE_LINK = frozenset({"link"})
_ROLE_BUTTON = frozenset({"button"})
_LINK_TAGS = frozenset({"a"})
_BUTTON_TAGS = frozenset({"button"})
_BUTTONISH_INPUT_TYPES = frozenset({"submit", "button", "reset", "image"})

#: accessible name source 의 ARIA/HTML-AAM 우선순위 (높은 것 먼저).
_NAME_SOURCE_PRECEDENCE = (
    "ARIA_LABELLEDBY",
    "ARIA_LABEL",
    "LABEL",
    "ALT",
    "VALUE",
    "VISIBLE_TEXT",
    "TITLE",
)


def normalize_label(text: str | None) -> str:
    """04 §5 의 비교 정규화 — Unicode(NFKC) + whitespace collapse + strip.

    casefold 는 하지 않는다. 04 §5 가 요구한 것은 "normalize 후 exact" 이고
    대소문자 접기는 그 자체로 label 을 바꾸는 판단이기 때문이다.
    """
    if text is None:
        return ""
    return " ".join(unicodedata.normalize("NFKC", text).split())


def _casefolded(text: str | None) -> str:
    return normalize_label(text).casefold()


@dataclass(frozen=True)
class SurfaceMeasurement:
    """`fact_surface_state` (02 §3) 의 surface/geometry/label 필드.

    04 §6 에 따라 zone 요약값과 함께 정규화 원좌표·원 bbox 를 모두 보존한다.
    """

    # ── 04 §4 표가 요구하는 9 필드군 ──────────────────────────────────────
    s0_task_control_visible: bool
    first_visible_scroll_state: str | None
    entry_x_norm: float | None
    entry_y_norm: float | None
    entry_zone: str
    entry_control_type: str
    entry_label_modality: str
    visible_label_text: str | None
    accessible_name: str | None
    accessible_name_source: str
    label_relation: str

    # ── Δ15 GAP-07 — 모든 행이 자기 기하가 어느 시점 것인지 선언한다 ───────
    #: `"S0"`/`"S1"`/… 또는 reveal-gated 면 `"POST_REVEAL:<nav_container_type>"`,
    #: 끝내 관측하지 못했으면 `NOT_OBSERVED`.
    entry_observed_state: str = NOT_OBSERVED

    # ── Δ15 GAP-06 — 최내곽 container 와 바깥→안쪽 chain 원자료 ────────────
    nav_container_type: str | None = None
    nav_container_chain: tuple[str, ...] = field(default_factory=tuple)

    # ── Δ15 — DOM 과 AX 가 control 존재 자체에서 갈리는가 ──────────────────
    dom_control_observed: bool = False
    ax_control_observed: bool = False
    dom_ax_divergence: bool = False

    # ── 04 §6 "좌표 원자료를 버리지 않는다" ────────────────────────────────
    entry_x_norm_raw: float | None = None
    entry_y_norm_raw: float | None = None
    entry_box_css_px: dict[str, float] | None = None
    viewport_width: int = 0
    viewport_height: int = 0

    # ── provenance / 관측 불가 사유 ────────────────────────────────────────
    notes: tuple[str, ...] = field(default_factory=tuple)


# ── probe 접근 helper ────────────────────────────────────────────────────────


def _iter_states(probe_state: dict[str, Any]) -> list[tuple[str, dict[str, Any]]]:
    """`probe_state` 를 `(state_index, raw_features)` 순서열로 편다."""
    bundle = probe_state.get("scroll_states")
    states = bundle if isinstance(bundle, list) else [probe_state]
    out: list[tuple[str, dict[str, Any]]] = []
    for i, st in enumerate(states):
        if not isinstance(st, dict):
            continue
        idx = st.get("state_index") or f"S{i}"
        raw = st.get("raw_features")
        out.append((str(idx), raw if isinstance(raw, dict) else {}))
    return out


def _control_records(raw: dict[str, Any]) -> list[tuple[str, dict[str, Any]]]:
    """probe raw_features 안에서 control 레코드를 담는 모든 목록을 `(출처, 행)` 으로 낸다."""
    out: list[tuple[str, dict[str, Any]]] = []
    for key in ("primary_action_candidates", "accessible_name_sources", "utility_input_widgets"):
        rows = raw.get(key)
        if isinstance(rows, list):
            out.extend((key, r) for r in rows if isinstance(r, dict))
    region = raw.get("region_signals")
    if isinstance(region, dict):
        rows = region.get("search_inputs")
        if isinstance(rows, list):
            out.extend(("search_inputs", r) for r in rows if isinstance(r, dict))
    return out


def _merge_control(raw: dict[str, Any], selector: str) -> dict[str, Any] | None:
    """selector 로 control 을 찾아 여러 probe 목록의 필드를 하나로 병합한다.

    `primary_action_candidates` 는 이미 `visible` 필터를 통과한 목록이라 `visible` 키가
    없다 — 거기서 발견되면 `visible=True` 로 본다(`l0_probe.js` 의 `filter(visible)`).
    """
    merged: dict[str, Any] = {}
    sources: list[str] = []
    for origin, row in _control_records(raw):
        if row.get("selector") != selector:
            continue
        sources.append(origin)
        for k, v in row.items():
            if v is None and k in merged:
                continue
            if k not in merged or merged[k] is None:
                merged[k] = v
    if not sources:
        return None
    merged["_probe_lists"] = tuple(sources)
    if "visible" not in merged and "primary_action_candidates" in sources:
        merged["visible"] = True
    return merged


def _descendant_rows(raw: dict[str, Any], selector: str) -> list[dict[str, Any]]:
    """selector 를 접두사로 갖는 하위 요소 레코드.

    KNOWN LIMITATION: `l0_probe.js::sel()` 은 조상에 `id` 가 나오면 거기서 경로를 끊는다
    (`tag#id` 로 시작하는 짧은 selector 가 된다). 그래서 중간에 id 를 가진 요소가 있으면
    접두사 일치가 성립하지 않아 하위 요소를 놓칠 수 있다. 놓치면 icon 신호가 약해질 뿐
    새 판정을 만들지는 않는다.
    """
    prefix = selector + ">"
    out: list[dict[str, Any]] = []
    seen: set[str] = set()
    for _origin, row in _control_records(raw):
        sel = row.get("selector")
        if not isinstance(sel, str) or not sel.startswith(prefix):
            continue
        if sel in seen:
            continue
        seen.add(sel)
        out.append(row)
    return out


def _box_of(rec: dict[str, Any]) -> dict[str, float] | None:
    box = rec.get("box")
    if not isinstance(box, dict):
        return None
    try:
        return {
            "x": float(box["x"]),
            "y": float(box["y"]),
            "w": float(box["w"]),
            "h": float(box["h"]),
        }
    except (KeyError, TypeError, ValueError):
        return None


def _intersects_viewport(box: dict[str, float] | None, vw: int, vh: int) -> bool:
    if box is None:
        return False
    w = min(box["x"] + box["w"], float(vw)) - max(box["x"], 0.0)
    h = min(box["y"] + box["h"], float(vh)) - max(box["y"], 0.0)
    return w > 0 and h > 0


def _element_visible(rec: dict[str, Any]) -> bool:
    """요소 수준 가시성 — display/visibility/opacity/크기. viewport 안인지와 무관."""
    v = rec.get("visible")
    if isinstance(v, bool):
        return v
    # `primary_action_candidates` 는 이미 visible 필터를 통과한 목록이다.
    return "primary_action_candidates" in rec.get("_probe_lists", ())


def _viewport_visible(rec: dict[str, Any], vw: int, vh: int) -> bool:
    if not _element_visible(rec):
        return False
    v = rec.get("viewport_visible")
    if isinstance(v, bool):
        return v
    return _intersects_viewport(_box_of(rec), vw, vh)


def _observed(rec: dict[str, Any], vw: int, vh: int, notes: list[str]) -> bool:
    """Δ15 GAP-05 — "그 state 의 viewport 안에 bbox 가 교차하고 hit-testable 한가".

    **`task_control_occlusion` 과는 어떤 파생 관계도 없다.** A 판정: 90% 가려져도 노출된
    모서리에서 hit-testable 이면 보이는 것이고, 0% 가려져도 viewport 밖이면 보이지 않는
    것이다. 둘은 독립이며 파생 로직을 넣으면 없는 인과를 스키마에 새기게 된다. 그래서 이
    모듈은 occlusion 값을 입력으로 받지도, 산출하지도 않는다.

    KNOWN LIMITATION: `hittable` 은 `primary_action_candidates` /
    `region_signals.search_inputs` / `utility_input_widgets` 에만 있고
    `accessible_name_sources` 에는 없다. 신호가 아예 없으면 hit-test 를 확정할 수 없으므로
    viewport 교차만으로 판단하고 `HITTABLE_SIGNAL_ABSENT` note 를 남긴다 — 신호 부재를
    `False` 로 바꾸지 않는다.
    """
    if not _viewport_visible(rec, vw, vh):
        return False
    hittable = rec.get("hittable")
    if hittable is False:
        return False
    if not isinstance(hittable, bool):
        note = "HITTABLE_SIGNAL_ABSENT"
        if note not in notes:
            notes.append(note)
    return True


# ── nav container (Δ15 GAP-06) ──────────────────────────────────────────────


def _resolve_nav_container(
    task_control: dict[str, Any], notes: list[str]
) -> tuple[str | None, tuple[str, ...]]:
    """`(최내곽 nav_container_type, 바깥→안쪽 chain)` 을 낸다.

    Δ15 GAP-06 — `nav_container_type` 은 **task-entry control 을 직접 담고 있는 가장
    안쪽 container** 다. hamburger 안 accordion 이면 `INLINE_EXPAND` 이고 바깥 container 는
    `nav_container_depth` 가 이미 센다. 요약값이 원자료를 덮지 않도록 chain 전체를 함께
    보존한다 (`Δ8-R7` 과 같은 처리).

    chain 과 `nav_container_type` 이 둘 다 주어졌는데 최내곽이 서로 다르면 chain 을 쓰고
    불일치를 note 로 남긴다 — 어느 쪽도 조용히 버리지 않는다.
    """
    raw_chain = task_control.get("nav_container_chain")
    chain: tuple[str, ...] = ()
    if isinstance(raw_chain, (list, tuple)):
        chain = tuple(str(c) for c in raw_chain if isinstance(c, str) and c)
    declared = task_control.get("nav_container_type")
    declared_str = declared if isinstance(declared, str) and declared else None
    innermost = chain[-1] if chain else declared_str
    if chain and declared_str and declared_str != chain[-1]:
        notes.append("NAV_CONTAINER_CHAIN_TYPE_MISMATCH")
    return innermost, chain


def _entry_observed_state(state_index: str | None, nav_container_type: str | None) -> str:
    """Δ15 GAP-07 — 이 행의 `entry_*` 기하가 어느 시점 것인지 선언한다.

    A 근거: 한 시점을 전제로 두면 어떤 행은 그 전제를 어기고 그것이 조용히 남는다.
    행이 자기 시점을 들고 있으면 어긴다는 개념 자체가 사라진다.

    `s0_task_control_visible` 과 충돌하지 않는다 — 그것은 여전히 S0 사실이고
    reveal-gated control 이면 `False` 다. 두 변수는 다른 것을 잰다.
    """
    if nav_container_type and nav_container_type.upper() not in _NO_REVEAL_CONTAINERS:
        return f"POST_REVEAL:{nav_container_type}"
    if state_index is None:
        return NOT_OBSERVED
    return state_index


# ── 아이콘 / 텍스트 신호 ─────────────────────────────────────────────────────


def _has_icon(rec: dict[str, Any], descendants: list[dict[str, Any]]) -> bool:
    """자신 또는 하위에 이미지성 요소가 있는가.

    KNOWN LIMITATION: `l0_probe.js` 의 name-source 쿼리는 `img` 와 `[role=img]` 만 잡고
    inline `<svg>` · CSS background icon 은 잡지 않는다. 그래서 icon "있음" 은 신뢰할 수
    있으나 icon "없음" 은 확정이 아니다. 이 때문에 label modality/control type 판정의
    1차 축은 icon 유무가 아니라 **visible text 유무**로 잡는다 — visible text 가 없으면
    icon 을 못 봤더라도 사용자에게는 비텍스트 control 이다.
    """
    if rec.get("tag") == "img" or rec.get("role") == "img":
        return True
    return any(d.get("tag") == "img" or d.get("role") == "img" for d in descendants)


# ── accessible name / source / relation ──────────────────────────────────────


def _accessible_name_from_ax(ax_node: Any, notes: list[str]) -> str | None:
    """AX tree slim node 에서만 accessible name 을 읽는다 (00 §8).

    DOM 속성으로 추정하지 않는다. 추정하는 순간 `visible_label_text` 와 출처가 겹쳐
    04 §7 이 요구한 분리가 무너진다.
    """
    if not isinstance(ax_node, dict):
        notes.append("AX_NODE_ABSENT")
        return None
    if ax_node.get("name_computed") is False:
        notes.append("AX_NAME_NOT_COMPUTED")
        return None
    name = ax_node.get("name")
    if not isinstance(name, str):
        notes.append("AX_NAME_NOT_COMPUTED")
        return None
    norm = normalize_label(name)
    if not norm:
        notes.append("AX_NAME_EMPTY")
        return None
    return norm


def _declared_name_sources(
    rec: dict[str, Any], descendants: list[dict[str, Any]]
) -> list[tuple[str, str | None]]:
    """`(source, 비교가능 텍스트 or None)` 를 ARIA/HTML-AAM 우선순위대로 낸다.

    텍스트가 `None` 인 것은 "선언돼 있으나 probe 로는 텍스트를 해석할 수 없음"을 뜻한다
    (`aria-labelledby` 의 참조 대상 텍스트, `<label for>` 의 텍스트).
    """
    out: list[tuple[str, str | None]] = []
    if normalize_label(rec.get("aria_labelledby")):
        out.append(("ARIA_LABELLEDBY", None))
    aria_label = normalize_label(rec.get("aria_label"))
    if aria_label:
        out.append(("ARIA_LABEL", aria_label))
    if rec.get("labelled_by_for") is True:
        out.append(("LABEL", None))
    alt = normalize_label(rec.get("alt"))
    if not alt:
        for d in descendants:
            alt = normalize_label(d.get("alt"))
            if alt:
                break
    if alt:
        out.append(("ALT", alt))
    value = normalize_label(rec.get("value"))
    if value:
        out.append(("VALUE", value))
    visible_text = normalize_label(rec.get("visible_text"))
    if visible_text:
        out.append(("VISIBLE_TEXT", visible_text))
    title = normalize_label(rec.get("title"))
    if title:
        out.append(("TITLE", title))
    out.sort(key=lambda p: _NAME_SOURCE_PRECEDENCE.index(p[0]))
    return out


def _resolve_name_source(
    accessible_name: str | None,
    rec: dict[str, Any],
    descendants: list[dict[str, Any]],
    notes: list[str],
) -> str:
    """`accessible_name_source` (04 §4 9값) 를 결정한다.

    절차:

    1. accessible name 이 없으면 `NONE`.
    2. 선언된 source 를 ARIA/HTML-AAM 우선순위로 세운다. 최상위 source 의 텍스트를
       probe 로 해석할 수 없으면(`aria-labelledby`, `<label for>`) 그 source 를 낸다 —
       브라우저 naming computation 이 그것을 먼저 썼을 것이기 때문이다.
    3. 최상위 source 의 텍스트가 accessible name 과 정확히 일치하면 그 source.
    4. 아니면 정확히 일치하는 다른 source 를 우선순위대로 찾는다.
    5. 그래도 없으면 accessible name 의 부분문자열로 기여한 source 를 센다. 둘 이상이면
       `MIXED`.
    6. 하나뿐이면 그 source.
    7. 아무것도 귀속되지 않으면 `NONE` + `ACCESSIBLE_NAME_SOURCE_UNRESOLVED` note.

    KNOWN LIMITATION (7번): AX 이름이 있는데 출처를 특정하지 못하는 경우
    (pseudo-element `::before` content 등, 04 §7 이 지목한 경우) enum 에 "미상" 값이
    없어 `NONE` 을 낸다. 이름 자체는 `accessible_name` 에 그대로 남고 note 로 구분된다.
    """
    if not accessible_name:
        return "NONE"
    declared = _declared_name_sources(rec, descendants)
    if not declared:
        notes.append("ACCESSIBLE_NAME_SOURCE_UNRESOLVED")
        return "NONE"

    top_src, top_text = declared[0]
    if top_text is None:
        return top_src
    if top_text == accessible_name:
        return top_src
    notes.append(f"NAME_SOURCE_PRECEDENCE_MISMATCH:{top_src}")

    for src, text in declared[1:]:
        if text is None:
            return src
        if text == accessible_name:
            return src

    contributors = {src for src, text in declared if text and text in accessible_name}
    if len(contributors) >= 2:
        return "MIXED"
    if len(contributors) == 1:
        return next(iter(contributors))
    notes.append("ACCESSIBLE_NAME_SOURCE_UNRESOLVED")
    return "NONE"


def _label_relation(visible_label_text: str | None, accessible_name: str | None) -> str:
    """04 §5 — normalize 후 exact 비교. embedding similarity 로 자동 merge 하지 않는다."""
    v = normalize_label(visible_label_text)
    a = normalize_label(accessible_name)
    if not v and not a:
        return "NONE"
    if v and not a:
        return "VISIBLE_ONLY"
    if a and not v:
        return "AX_ONLY"
    if v == a:
        return "MATCH"
    v_key, a_key = _SYNONYM_MAP.get(v), _SYNONYM_MAP.get(a)
    if v_key is not None and v_key == a_key:
        return "SEMANTIC_EQUIV"
    return "DIFFERENT"


# ── control type / label modality / zone ─────────────────────────────────────


def _has_nav_ancestor(selector: str | None) -> bool:
    """selector 경로에 `nav` 세그먼트가 있는가 (`l0_probe.js::sel()` 은 tag 경로를 낸다)."""
    if not selector:
        return False
    for seg in selector.split(">"):
        tag = seg.split("#", 1)[0].split(":", 1)[0]
        if tag == "nav":
            return True
    return False


def _control_type(
    rec: dict[str, Any],
    descendants: list[dict[str, Any]],
    visible_text: str,
    accessible_name: str | None,
    y_norm: float | None,
) -> str:
    """04 §4 `entry_control_type` 11값. 판정 순서는 W5C 가 정했고 04 에 근거가 없다.

    순서: SEARCHBOX > TAB > HAMBURGER > BOTTOM_NAV > CARD > ICON_ONLY > LIST_ITEM >
    ICON_TEXT > TEXT_LINK > TEXT_BUTTON > OTHER.
    """
    tag = rec.get("tag")
    role = rec.get("role")
    input_type = rec.get("type")
    lists = rec.get("_probe_lists", ())

    if role in _ROLE_SEARCHBOX or "search_inputs" in lists:
        return "SEARCHBOX"
    if tag == "input" and input_type == "search":
        return "SEARCHBOX"
    if role == "tab":
        return "TAB"

    if not visible_text:
        name_key = _casefolded(accessible_name)
        if name_key and name_key in HAMBURGER_NAME_LEXICON:
            return "HAMBURGER"
        aria_key = _casefolded(rec.get("aria_label"))
        if aria_key and aria_key in HAMBURGER_NAME_LEXICON:
            return "HAMBURGER"

    if (
        _has_nav_ancestor(rec.get("selector"))
        and y_norm is not None
        and y_norm >= ZONE_BOTTOM_Y_MIN
    ):
        return "BOTTOM_NAV"

    box = _box_of(rec)
    if visible_text and _has_icon(rec, descendants) and box is not None:
        area = box["w"] * box["h"]
        if area >= CARD_MIN_AREA_CSS_PX2 and min(box["w"], box["h"]) >= CARD_MIN_SIDE_CSS_PX:
            return "CARD"

    if not visible_text:
        return "ICON_ONLY"
    if rec.get("in_list_container") is True:
        return "LIST_ITEM"
    if _has_icon(rec, descendants):
        return "ICON_TEXT"
    if tag in _LINK_TAGS or role in _ROLE_LINK:
        return "TEXT_LINK"
    if tag in _BUTTON_TAGS or role in _ROLE_BUTTON:
        return "TEXT_BUTTON"
    if tag == "input" and input_type in _BUTTONISH_INPUT_TYPES:
        return "TEXT_BUTTON"
    return "OTHER"


def _label_modality(
    rec: dict[str, Any],
    descendants: list[dict[str, Any]],
    visible_text: str,
    accessible_name: str | None,
    element_visible_anywhere: bool,
) -> str:
    """04 §4 `entry_label_modality` 5값.

    `HIDDEN_UNTIL_REVEAL` 이 최우선이다 — 어느 scroll state 에서도 **요소 수준으로**
    보이지 않는(display/visibility/opacity/크기) control 은 reveal 없이는 label 자체가
    존재하지 않는다. viewport 밖(fold 아래)인 것은 여기 해당하지 않는다. 그건 scroll 로
    도달 가능하고 `first_visible_scroll_state` 가 따로 잰다 (04 §4 · 00 §7).
    """
    if not element_visible_anywhere:
        return "HIDDEN_UNTIL_REVEAL"
    if visible_text:
        return "ICON_TEXT" if _has_icon(rec, descendants) else "EXPLICIT_TEXT"
    return "ICON_ONLY_AX_NAMED" if accessible_name else "ICON_ONLY_UNNAMED"


def _zone(
    x_norm: float | None,
    y_norm: float | None,
    nav_container_type: Any,
    computed_position: Any,
) -> str:
    """04 §4 `entry_zone` 7값. 경계는 A `T-A-V3-STEP1-003` R7 확정 정의다.

    DRAWER > FLOATING > 기하 순으로 우선한다. 구조적 override 가 걸려도 호출부는
    `entry_x_norm`/`entry_y_norm` 을 그대로 저장한다 — 요약값이 원자료를 덮지 않는다
    (04 §6).
    """
    if isinstance(nav_container_type, str) and nav_container_type.upper() in _DRAWER_CONTAINERS:
        return "DRAWER"
    if (
        isinstance(computed_position, str)
        and computed_position.strip().lower() in _FLOATING_POSITIONS
    ):
        return "FLOATING"
    if x_norm is None or y_norm is None:
        return NOT_OBSERVED
    if y_norm < ZONE_TOP_Y_MAX:
        if x_norm < ZONE_LEFT_X_MAX:
            return "TOP_LEFT"
        if x_norm < ZONE_RIGHT_X_MIN:
            return "TOP_CENTER"
        return "TOP_RIGHT"
    if y_norm >= ZONE_BOTTOM_Y_MIN:
        return "BOTTOM"
    return "MID"


def _clamp01(v: float) -> float:
    return 0.0 if v < 0.0 else (1.0 if v > 1.0 else v)


# ── 공개 함수 ────────────────────────────────────────────────────────────────


def measure_surface(
    probe_state: dict[str, Any],
    task_control: dict[str, Any],
    viewport: tuple[int, int],
) -> SurfaceMeasurement:
    """L0 probe 산출물 + 확정된 task-entry control binding → surface 측정값.

    순수함수다. 네트워크·파일·시계·난수를 쓰지 않는다.

    Args:
        probe_state: `engine/l0_probe.js` 산출물(단일 state) 또는 `scroll_states` 번들.
        task_control: 최소 `{"selector": ...}`. 선택적으로 `ax_node`,
            `nav_container_type`, `computed_position`. 모듈 docstring 참조.
        viewport: `(width, height)` CSS px. 03 §1 기준 `(390, 844)`.

    Returns:
        `SurfaceMeasurement` — 04 §4 표의 surface/geometry/label 필드와, 04 §6 이 요구한
        정규화 원좌표·원 bbox·관측 state 를 함께 보존한 값.

    Raises:
        ValueError: `task_control["selector"]` 가 없거나 viewport 가 양수가 아닐 때.
            명세 공백을 추정으로 메우지 않는다.
    """
    selector = task_control.get("selector")
    if not isinstance(selector, str) or not selector:
        raise ValueError("task_control['selector'] 가 필요하다 (03 §4 binding 결과)")
    vw, vh = int(viewport[0]), int(viewport[1])
    if vw <= 0 or vh <= 0:
        raise ValueError(f"viewport 는 양수여야 한다: {viewport!r}")

    notes: list[str] = []
    states = _iter_states(probe_state)
    if not states:
        notes.append("PROBE_STATES_EMPTY")

    nav_container_type, nav_container_chain = _resolve_nav_container(task_control, notes)

    # AX 쪽이 이 control 을 갖고 있는가. `ax_node` 키를 넘기지 않은 것은 "AX 에 없다" 가
    # 아니라 "호출자가 알려주지 않았다" 이므로 divergence 판정에서 제외한다.
    ax_declared = "ax_node" in task_control
    ax_raw = task_control.get("ax_node")
    ax_observed = isinstance(ax_raw, dict) and ax_raw.get("ignored") is not True

    # ── control 을 각 state 에서 찾는다 ────────────────────────────────────
    found: list[tuple[str, dict[str, Any], dict[str, Any]]] = []  # (state, rec, raw)
    for state_index, raw in states:
        rec = _merge_control(raw, selector)
        if rec is not None:
            found.append((state_index, rec, raw))

    if not found:
        # DOM 쪽에서 control 을 관측하지 못했다. AX 쪽 관측은 그대로 살려 둔다 — 어느
        # 한쪽을 정본으로 삼으면 divergence 자체가 데이터에서 사라진다 (Δ15).
        notes.append("TASK_CONTROL_NOT_IN_PROBE")
        accessible_name = _accessible_name_from_ax(task_control.get("ax_node"), notes)
        if ax_observed:
            notes.append("DOM_AX_DIVERGENCE")
        return SurfaceMeasurement(
            s0_task_control_visible=False,
            first_visible_scroll_state=None,
            # GAP-04 — 미관측 수치는 null 이지 0 이 아니다.
            entry_x_norm=None,
            entry_y_norm=None,
            # GAP-04 — 미관측 범주는 명시적 표지다. `OTHER` 같은 실측값을 쓰지 않는다.
            entry_zone=NOT_OBSERVED,
            entry_control_type=NOT_OBSERVED,
            entry_label_modality=NOT_OBSERVED,
            visible_label_text=None,
            accessible_name=accessible_name,
            accessible_name_source=NOT_OBSERVED,
            label_relation=NOT_OBSERVED,
            entry_observed_state=NOT_OBSERVED,
            nav_container_type=nav_container_type,
            nav_container_chain=nav_container_chain,
            dom_control_observed=False,
            ax_control_observed=ax_observed,
            dom_ax_divergence=ax_declared and ax_observed,
            viewport_width=vw,
            viewport_height=vh,
            notes=tuple(notes),
        )

    # ── S0 가시성 · 최초 관측 state (04 §4: scroll 은 activation depth 아님) ──
    s0_state, s0_rec, _s0_raw = found[0]
    if s0_state != states[0][0]:
        notes.append("TASK_CONTROL_ABSENT_AT_S0")
    s0_visible = s0_state == states[0][0] and _observed(s0_rec, vw, vh, notes)

    # GAP-02 — control 이 최초로 관측된 scroll state. reveal 로 나타난 control 이면 그
    # reveal 이 일어난 scroll state 다(보통 S0). NULL 은 끝내 관측하지 못한 경우뿐이다.
    first_visible_state: str | None = None
    entry_state, entry_rec, entry_raw = found[0]
    for state_index, rec, raw in found:
        if _observed(rec, vw, vh, notes):
            first_visible_state = state_index
            entry_state, entry_rec, entry_raw = state_index, rec, raw
            break
    if first_visible_state is None:
        notes.append("TASK_CONTROL_NEVER_OBSERVED_IN_VIEWPORT")

    element_visible_anywhere = any(_element_visible(rec) for _s, rec, _r in found)

    # ── 기하 (04 §6: zone 은 요약값, 원좌표를 버리지 않는다) ────────────────
    box = _box_of(entry_rec)
    if box is None:
        notes.append("ENTRY_BOX_ABSENT")
        x_raw = y_raw = None
        x_norm = y_norm = None
    else:
        x_raw = (box["x"] + box["w"] / 2.0) / float(vw)
        y_raw = (box["y"] + box["h"] / 2.0) / float(vh)
        x_norm = _clamp01(x_raw)
        y_norm = _clamp01(y_raw)
        if x_raw != x_norm or y_raw != y_norm:
            notes.append("ENTRY_CENTER_OUTSIDE_VIEWPORT_CLAMPED")

    # ── label: visible rendered text 와 AX computed name 은 끝까지 별개다 ──
    descendants = _descendant_rows(entry_raw, selector)
    visible_text = normalize_label(entry_rec.get("visible_text"))
    accessible_name = _accessible_name_from_ax(task_control.get("ax_node"), notes)
    name_source = _resolve_name_source(accessible_name, entry_rec, descendants, notes)
    relation = _label_relation(visible_text or None, accessible_name)

    return SurfaceMeasurement(
        s0_task_control_visible=s0_visible,
        first_visible_scroll_state=first_visible_state,
        entry_x_norm=x_norm,
        entry_y_norm=y_norm,
        entry_zone=_zone(
            x_norm,
            y_norm,
            nav_container_type,
            task_control.get("computed_position"),
        ),
        entry_control_type=_control_type(
            entry_rec, descendants, visible_text, accessible_name, y_norm
        ),
        entry_label_modality=_label_modality(
            entry_rec, descendants, visible_text, accessible_name, element_visible_anywhere
        ),
        visible_label_text=visible_text or None,
        accessible_name=accessible_name,
        accessible_name_source=name_source,
        label_relation=relation,
        entry_observed_state=_entry_observed_state(entry_state, nav_container_type),
        nav_container_type=nav_container_type,
        nav_container_chain=nav_container_chain,
        dom_control_observed=True,
        ax_control_observed=ax_observed,
        dom_ax_divergence=ax_declared and not ax_observed,
        entry_x_norm_raw=x_raw,
        entry_y_norm_raw=y_raw,
        entry_box_css_px=box,
        viewport_width=vw,
        viewport_height=vh,
        notes=tuple(notes),
    )
