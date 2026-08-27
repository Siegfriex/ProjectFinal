"""L0 collector — `02 §2` · `§3` · `§4` · `§5` · `§6` · `A1 §3` · `§5` · `§6`.

**이 수집기는 fixture 만 연다.** 모든 항해가 `firewall.assert_navigation_allowed` 를 거치고,
그 함수는 `file://` 이 아닌 scheme 을 전부 거부한다 (`PHASE_GATES §4.5`).

## 층 분리

`02 §4` — *probe 는 판정하지 않고 raw feature 만 저장한다.*
그래서 `l0_probe.js` 는 임계값을 갖지 않고, 이 모듈도 KWCAG verdict 를 만들지 않는다.
여기서 만들어지는 파생값(`primary_action_occlusion` 등)은 `01 §4`·`§5` 가 요구하는
**Axis B 관측 변수**이며 criterion 판정이 아니다 (`A2` 전파 규칙 T-5).

## L0-a / L0-b / L0-c (A1 §3.1)

| 단계 | 내용 | 조작 |
|---|---|---|
| L0-a | DOM · AX · computed CSS · geometry · screenshot 2종 · probe | 없음 |
| L0-b | interrupt 후보 · 공간검사 · blocking · 의미분류 · dismiss control 검사 | 없음 |
| L0-c | dismissal 실제 시도 (interrupt 당 1회, before/after evidence) | 있음 |

L0-a 의 evidence 가 확정된 뒤에만 L0-c 를 수행하고, L0-c 는 L0-a 를 **덮어쓰지 않는다.**
요약 변수(`max_overlay_coverage` · `primary_action_visible_initial` …)는 **L0-a 상태에서만** 산출한다.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import TYPE_CHECKING, Any

from .evidence import EvidenceRun
from .firewall import ExecutionMode, assert_navigation_allowed
from .identity import missing_slots, observation_id
from .provenance import PROTOCOL_VERSION, utc_now_iso
from .vocabulary import (
    NAME_ABSENT,
    ClassificationStatus,
    DismissFailureMode,
    DismissMethod,
    InteractionArchetype,
    InterruptLabel,
    MeasurementStatus,
)

if TYPE_CHECKING:  # pragma: no cover - 타입 전용
    from playwright.sync_api import Page

PROBE_JS = (Path(__file__).parent / "l0_probe.js").read_text(encoding="utf-8")

# ── `02 §2` 공통 모바일 환경 ──────────────────────────────────────────────────
VIEWPORT_WIDTH = 390
VIEWPORT_HEIGHT = 844
DEVICE_SCALE_FACTOR = 3
LOCALE = "ko-KR"
TIMEZONE_ID = "Asia/Seoul"
MOBILE_USER_AGENT = (
    "Mozilla/5.0 (Linux; Android 13; SM-S911N) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Mobile Safari/537.36"
)

#: `02 §3` 고정 안정화 대기 규칙. P-C 수집 파라미터이며 해석 임계값이 아니다.
SETTLE_MS = 400
NAV_TIMEOUT_MS = 15_000

#: `A1 §5.1` — 저장할 대표기능 후보 수. P-C 동결값.
TOP_N_CANDIDATES = 5

_COMPUTED_CSS_PROPERTIES = (
    "display",
    "visibility",
    "opacity",
    "position",
    "z-index",
    "overflow",
    "color",
    "background-color",
    "background-image",
    "font-size",
    "font-weight",
    "line-height",
    "animation-name",
    "animation-iteration-count",
    "pointer-events",
)

_COMPUTED_CSS_JS = """
(props) => [...document.querySelectorAll('body *')].slice(0, 1500).map((el, i) => {
  const cs = getComputedStyle(el);
  const r = el.getBoundingClientRect();
  const o = { index: i, tag: el.tagName.toLowerCase(), id: el.id || null,
    box: {x:+r.x.toFixed(2), y:+r.y.toFixed(2), w:+r.width.toFixed(2), h:+r.height.toFixed(2)} };
  props.forEach((p) => { o[p] = cs.getPropertyValue(p); });
  return o;
})
"""

_DISMISS_STATE_JS = """
(selector) => {
  const el = document.querySelector(selector);
  if (!el) return { present: false, viewport_overlap: 0, hittable: false };
  const r = el.getBoundingClientRect();
  const w = Math.max(0, Math.min(r.x + r.width, window.innerWidth) - Math.max(r.x, 0));
  const h = Math.max(0, Math.min(r.y + r.height, window.innerHeight) - Math.max(r.y, 0));
  const cx = Math.min(Math.max(r.x + r.width / 2, 0), window.innerWidth - 1);
  const cy = Math.min(Math.max(r.y + r.height / 2, 0), window.innerHeight - 1);
  const top = document.elementFromPoint(cx, cy);
  return { present: true, viewport_overlap: +(w * h).toFixed(2),
           hittable: !!top && (top === el || el.contains(top)) };
}
"""

#: `02 §5` 4차 의미분류의 결정적 사전. **탐지 사전이며 판정 기준이 아니다.**
_LABEL_RULES: tuple[tuple[InterruptLabel, tuple[str, ...]], ...] = (
    (InterruptLabel.COOKIE_CONSENT, ("쿠키", "cookie")),
    (InterruptLabel.APP_INSTALL_PROMPT, ("앱 설치", "앱으로 보기", "app store", "install app")),
    (InterruptLabel.LOGIN_PROMPT, ("로그인", "sign in", "log in")),
    (InterruptLabel.CHAT_WIDGET, ("상담", "채팅", "문의하기", "chat")),
    (InterruptLabel.PROMOTION_MODAL, ("이벤트", "할인", "쿠폰", "프로모션", "혜택", "sale")),
    (InterruptLabel.ADVERTISEMENT, ("광고", "sponsored", "advertisement")),
)


@dataclass(frozen=True)
class FixtureTarget:
    """FIXTURE 모드가 측정할 수 있는 유일한 대상 — 로컬 synthetic fixture."""

    web_target_id: str
    fixture: str
    archetype: InteractionArchetype
    task_id: str = "T-FIXTURE"

    def url(self, fixture_root: Path | None) -> str:
        if fixture_root is None:
            raise ValueError("FixtureTarget 은 fixture_root 없이 URL 을 만들 수 없다")
        return f"file://{(Path(fixture_root) / self.fixture).resolve()}"


@dataclass(frozen=True)
class RealServiceTarget:
    """`REAL_TARGET` 모드 + 승인된 scope 에서만 열리는 실제 서비스 target.

    `FixtureTarget` 과 **별도의 타입**인 것이 핵심이다 — 두 타입이 서로의 URL 을 만들 수
    없으므로, fixture 실행기가 실수로 실제 서비스를 여는 조합이 타입 수준에서 성립하지
    않는다. `L0Collector.collect()` 가 모드와 target 타입의 짝을 다시 한 번 확인한다.
    """

    web_target_id: str
    official_url: str
    archetype: InteractionArchetype
    task_id: str = "T-E000"
    canonical_service_key: str | None = None

    def url(self, fixture_root: Path | None = None) -> str:
        return self.official_url


@dataclass
class InterruptRecord:
    """`01 §5 fact_interrupt_element` 한 행 (fixture engine 산출).

    `C-FINDING-214214`/`D-R0-58-1` 시정 — `interrupt_form`(이 오버레이가 어떤 형태인가:
    BLOCKING_MODAL/PROMOTION_MODAL/BANNER/…)과 `interrupt_semantic`(이 오버레이가 무엇을
    하려는가: LOGIN_PROMPT/COOKIE_CONSENT/CHAT_WIDGET/APP_INSTALL_PROMPT/ADVERTISEMENT/…)은
    **직교하는 축**이고 동시에 참일 수 있다(예: sticky 배너인 동시에 로그인 유도문구).
    하나의 필드에 밀어 넣으면 반드시 하나가 죽는다 — 그래서 두 축을 별도 필드로 갖고,
    각 축은 독립적인 `*_status`(`RESOLVED`/`UNRESOLVED`/`NOT_APPLICABLE`, `D-R0-58-1`
    확정 어휘 — `l0_collector.InterruptAxisStatus`, 기존 `vocabulary.ClassificationStatus`
    재사용 아님)를 갖는다. `classify_interrupt()`가 둘을 독립적으로 판정하며, 한쪽이
    `RESOLVED` 됐다고 다른 쪽을 생략하거나 덮지 않는다.

    옛 단일 필드(`classification_status`/`final_label`)는 이 dataclass 에서 제거했다 —
    `vocabulary.py`의 `LEVEL_OF`/`_ENUMS` 표가 그 옛 이름을 여전히 등록해 두고 있지만
    (`vocabulary.py` 는 읽기 전용, W4 가 수정하지 않음) 현재 그 표를 실제로 소비하는
    호출부가 없다(`enum_for`/`validate` 호출처 0건, `grep` 확인). `interrupt_form`/
    `interrupt_semantic`/`*_status` 4개 새 필드도 아직 그 표에 등록돼 있지 않다 — 나중에
    wiring 할 때 이 이름들과 `InterruptAxisStatus` 어휘를 반영해야 한다. 이 사실을
    completion 보고에 명시해 A 에게 확인받는다.
    """

    interrupt_index: int
    selector: str
    candidate_sources: list[str]
    viewport_overlap_css_px2: float
    viewport_coverage: float
    interrupt_form: str
    interrupt_form_status: str
    interrupt_semantic: str
    interrupt_semantic_status: str
    blocks_primary_action: int
    primary_action_occlusion: float | None
    dismiss_control_exists: int
    dismiss_control_visible: int | None
    dismiss_control_accessible_name: str | None
    dismiss_control_width: float | None
    dismiss_control_height: float | None
    dismiss_persistence_hint: int
    dismiss_method: str | None = None
    dismiss_succeeded: int | None = None
    dismiss_failure_mode: str | None = None
    dismiss_screenshot_before: str | None = None
    dismiss_screenshot_after: str | None = None
    dismiss_dom_after: str | None = None


@dataclass
class PrimaryActionCandidate:
    """`A1 §5.1 fact_primary_action_candidate` 한 행. **분모(`area_css_px2`)를 보존한다.**"""

    candidate_id: int
    task_id: str
    rank: int
    selector: str
    dom_order: int
    control_role: str | None
    accessible_name: str | None
    visible_text: str | None
    nearby_heading: str | None
    href: str | None
    bbox_x: float
    bbox_y: float
    bbox_w: float
    bbox_h: float
    area_css_px2: float
    viewport_visible: int
    similarity_score: float | None
    selection_basis: str
    selection_status: str
    selection_confidence: float | None
    ai_review_status: str


@dataclass
class L0Observation:
    """`01 §4 fact_landing_observation` 한 행 + 그 관측의 하위 표들."""

    observation_id: str
    web_target_id: str
    evidence_run_id: str
    requested_url: str
    final_url: str | None
    measurement_status: str
    measurement_status_detail: str | None
    collection_started_at: str
    collection_finished_at: str
    audit_date: str
    viewport_configured_width: int
    viewport_configured_height: int
    viewport_width: int | None
    viewport_height: int | None
    device_pixel_ratio: float | None
    dom_path: str | None
    ax_path: str | None
    screenshot_initial_path: str | None
    screenshot_fullpage_path: str | None
    computed_css_path: str | None
    probe_path: str | None
    manifest_path: str
    max_overlay_coverage: float | None
    primary_action_visible_initial: int | None
    max_primary_action_occlusion: float | None
    interrupts: list[InterruptRecord] = field(default_factory=list)
    primary_action_candidates: list[PrimaryActionCandidate] = field(default_factory=list)
    raw_features: dict[str, Any] = field(default_factory=dict)
    notes: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def _overlap(a: dict[str, float] | None, b: dict[str, float] | None) -> float:
    if not a or not b:
        return 0.0
    w = max(0.0, min(a["x"] + a["w"], b["x"] + b["w"]) - max(a["x"], b["x"]))
    h = max(0.0, min(a["y"] + a["h"], b["y"] + b["h"]) - max(a["y"], b["y"]))
    return round(w * h, 2)


#: `D-R0-58-2` provenance — 이 분류기의 버전. completion 보고와 mart manifest 가 인용한다.
#: `v1` = 단일축(구조 우선, `cf8dbd70` — semantic 라벨이 BANNER 등에 붕괴하는 결함 있음).
#: `v2` = 이 버전, form/semantic 독립 2축(`C-FINDING-214214`/`D-R0-58` 시정).
CLASSIFY_INTERRUPT_VERSION = "interrupt-classifier-v2-form-semantic-split"


class InterruptAxisStatus(StrEnum):
    """`D-R0-58-1` 확정 어휘. `form`/`semantic` 각 축의 판정 상태 — 기존
    `vocabulary.ClassificationStatus`(KWCAG adjudication 등 다른 맥락에서 이미 쓰이는
    5종)를 재사용하지 않는다(A 지시). **이 enum 은 `vocabulary.py` 에 없다** —
    `vocabulary.py` 는 읽기 전용이라 W4 가 그 파일에 새 enum 을 등록할 수 없다. 승격이
    필요하면 A 에게 확인받는다(completion 보고에 명시).
    """

    RESOLVED = "RESOLVED"
    UNRESOLVED = "UNRESOLVED"
    NOT_APPLICABLE = "NOT_APPLICABLE"


#: 기존 `ClassificationStatus` → `InterruptAxisStatus` 대응(내부 판정 로직 재사용,
#: 결과만 새 어휘로 옮긴다). `VLM_REVIEWED` 는 이 lane 에서 나오지 않지만(VLM 미구현)
#: 표에는 넣어 둔다 — 나중에 VLM 을 붙일 때 결과가 `RESOLVED` 로 매핑되게.
_AXIS_STATUS_MAP: dict[ClassificationStatus, InterruptAxisStatus] = {
    ClassificationStatus.NOT_CLASSIFIED: InterruptAxisStatus.NOT_APPLICABLE,
    ClassificationStatus.DETERMINISTIC: InterruptAxisStatus.RESOLVED,
    ClassificationStatus.SEMANTIC_MODEL: InterruptAxisStatus.RESOLVED,
    ClassificationStatus.VLM_REVIEWED: InterruptAxisStatus.RESOLVED,
    ClassificationStatus.AMBIGUOUS: InterruptAxisStatus.UNRESOLVED,
}


@dataclass(frozen=True)
class InterruptClassification:
    """`C-FINDING-214214`/`D-R0-58-1` 확정 필드명 — `interrupt_form`(형태)과
    `interrupt_semantic`(의도)은 **직교하는 축**이다("A"의 표현: 배타적 범주가 아니다).

    ```
    interrupt_form       이 오버레이가 어떤 형태인가      BLOCKING_MODAL / PROMOTION_MODAL / BANNER / …
                          판정 근거 = geometry / DOM 구조
    interrupt_semantic   이 오버레이가 무엇을 하려는가    LOGIN_PROMPT / COOKIE_CONSENT / CHAT_WIDGET / …
                          판정 근거 = 텍스트 / 사전 / 모델
    ```

    "로그인 유도 sticky bar"는 `interrupt_form = BANNER` **이면서** `interrupt_semantic =
    LOGIN_PROMPT` 다 — 한 필드에 밀어 넣으면 반드시 하나가 죽는다(이전 구현의 결함,
    `cf8dbd70`). 두 축은 **서로 독립적으로** 계산되고, 한쪽이 `RESOLVED` 됐다고 다른
    쪽을 생략하거나 비우지 않는다 — 각각 독립적으로 `UNRESOLVED`/`NOT_APPLICABLE` 이
    될 수 있다.
    """

    interrupt_form: InterruptLabel
    interrupt_form_status: InterruptAxisStatus
    interrupt_semantic: InterruptLabel
    interrupt_semantic_status: InterruptAxisStatus


def classify_interrupt(candidate: dict[str, Any]) -> InterruptClassification:
    """`02 §5` 4차 의미분류 — `D-R0-25` 순서 `deterministic rule → text/NLP → VLM → abstain`.

    `A`의 명시: 이 순서는 **확실성의 우선순위**이지 "하나가 다른 하나를 덮는다"는
    뜻이 아니었다(`D-R0-25` 는 semantic → geometry 역방향만 막았지 geometry → semantic
    방향을 막지 않았다 — 이전 구현은 그 열린 방향을 실수로 닫았다, `C-FINDING-214214`).
    `interrupt_form`(구조 신호: `candidate_sources` 의 dialog/aria-modal/sticky/fixed)과
    `interrupt_semantic`(텍스트 사전 `_LABEL_RULES`)은 **각자 독립적으로** 판정한다.
    VLM 단계는 이 lane 에 없다(`W4` 범위) — 확정 못 하면 그 축만 `UNRESOLVED` 로
    abstain 한다(`A2` 규칙 I-1). 억지로 라벨을 고르지 않는다.

    | 축 | tier | 근거 | `*_status` |
    |---|---|---|---|
    | form | 1 deterministic rule | `candidate_sources` — 텍스트 불필요 | `RESOLVED` |
    | form | abstain | 구조 신호 없음 | `UNRESOLVED` |
    | semantic | 2 text/NLP | `_LABEL_RULES` 어휘 사전 매칭 | `RESOLVED` |
    | semantic | abstain | 어휘 매칭 없음 | `UNRESOLVED` |
    | 둘 다 | `viewport_overlap_css_px2 <= 0` | 애초에 판정 대상이 아님 | `NOT_APPLICABLE` |

    **`PROMOTION_MODAL` 은 두 축 모두에서 나올 수 있는 유일한 값이다** — form 축에서는
    "dialog 형태인데 전체 커버리지는 아님"(구조적 shape 추정), semantic 축에서는
    "이벤트/할인/쿠폰 텍스트 매칭"(의도)이라는 **서로 다른 근거**로 같은 이름을 쓴다.
    이것은 vocabulary 가 10종으로 닫혀 있고 form 전용 "작은 모달" 값이 따로 없어서
    생기는 애매함이다 — **W4 가 임의로 정리하지 않고 그대로 남긴다.** A 가 별도 form
    전용 값을 원하면 새 vocabulary 결정이 필요하다(`00 §8`, completion 보고에 명시).

    **불변조건 (`W4` 테스트로 증명)**: 이 함수는 `candidate` 의 이미 계산된 raw 필드
    (좌표·면적·overlap·coverage)를 읽기만 하고 절대 새로 만들거나 바꾸지 않는다 —
    돌려주는 것은 `InterruptClassification` 하나뿐이다. 호출부(`_build_interrupts`)의
    geometry 계산(`_overlap`, `blocks_primary_action` 등)은 이 함수의 반환값과 무관하게
    별도로 이뤄진다. `CLASSIFY_INTERRUPT_VERSION` 이 이 버전을 식별한다.
    """
    if candidate.get("viewport_overlap_css_px2", 0) <= 0:
        na = InterruptAxisStatus.NOT_APPLICABLE
        return InterruptClassification(InterruptLabel.UNKNOWN, na, InterruptLabel.UNKNOWN, na)

    # ── form 축 — 구조 신호만, 텍스트를 절대 참조하지 않는다 ────────────────
    sources = set(candidate.get("candidate_sources") or ())
    modal_like = {"dialog_element", "role_dialog", "aria_modal"} & sources
    if modal_like and candidate.get("viewport_coverage", 0) >= 0.5:
        form_raw_status, form_label = (
            ClassificationStatus.DETERMINISTIC,
            InterruptLabel.BLOCKING_MODAL,
        )
    elif modal_like:
        form_raw_status, form_label = (
            ClassificationStatus.DETERMINISTIC,
            InterruptLabel.PROMOTION_MODAL,
        )
    elif "position_sticky" in sources or "position_fixed" in sources:
        form_raw_status, form_label = ClassificationStatus.DETERMINISTIC, InterruptLabel.BANNER
    else:
        form_raw_status, form_label = ClassificationStatus.AMBIGUOUS, InterruptLabel.UNKNOWN

    # ── semantic 축 — 텍스트 사전만, 구조 신호를 절대 참조하지 않는다.
    # form 이 확정됐다는 이유로 이 블록을 건너뛰지 않는다(C-FINDING-214214 핵심 시정). ──
    text = " ".join(
        str(x) for x in (candidate.get("accessible_text"), candidate.get("aria_label")) if x
    ).lower()
    semantic_raw_status, semantic_label = ClassificationStatus.AMBIGUOUS, InterruptLabel.UNKNOWN
    for label, needles in _LABEL_RULES:
        if any(n.lower() in text for n in needles):
            semantic_raw_status, semantic_label = ClassificationStatus.SEMANTIC_MODEL, label
            break

    return InterruptClassification(
        interrupt_form=form_label,
        interrupt_form_status=_AXIS_STATUS_MAP[form_raw_status],
        interrupt_semantic=semantic_label,
        interrupt_semantic_status=_AXIS_STATUS_MAP[semantic_raw_status],
    )


class Min4ProbeContractError(ValueError):
    """`A2 §1.13` `dom_order` 계약 위반 — 구조값이므로 `NULL`을 허용하지 않는다.

    probe(`l0_probe.js`)는 후보를 낼 때마다 `dom_order`를 채워야 한다. 비어 있으면
    그것은 관측 결측이 아니라 **probe 결함**이다 (`A1 §2.6` 규칙 MIN-4 — "그 자리가
    비는 상황이 정의되지 않는다") — 조용히 기본값(0 등)으로 흡수하지 않는다.
    """


def _dom_order_of(c: dict[str, Any]) -> int:
    value = c.get("dom_order")
    if value is None:
        raise Min4ProbeContractError(
            f"primary_action_candidate without dom_order (selector={c.get('selector')!r}) "
            "— probe contract violation, not a missing observation (A2 §1.13)"
        )
    return int(value)


def min4_sort_key(c: dict[str, Any]) -> tuple[int, int, str]:
    """`A1 §2.6` 규칙 MIN-4 전순서 — `(marked_primary desc, dom_order asc, selector asc)`.

    **`area_css_px2`는 tie-break 키에서 제외한다** `[V2-C010b 시정]` — 관측 잡음이 있는
    면적을 정렬 키로 쓰면 어떤 양자화를 거쳐도 순서가 잡음을 따라간다(양자화 접근은
    원리적으로 폐기됨, `A1 §2.6`). 이 함수는 `l0_collector.rank_primary_action_candidates`와
    `l1_engine.Scout._activation_candidates` 양쪽이 공유한다 — 같은 후보 열에 다른 전순서를
    적용하면 저장된 `SELECTED`/`rank`와 Scout가 실제로 밟는 경로가 어긋난다.

    오름차순 정렬을 쓰므로 `marked_primary`는 `True`를 `0`으로 뒤집어 먼저 오게 한다.
    """
    marked_first = 0 if c.get("marked_primary") else 1
    return (marked_first, _dom_order_of(c), str(c.get("selector") or ""))


def rank_primary_action_candidates(
    raw: list[dict[str, Any]], *, task_id: str, top_n: int = TOP_N_CANDIDATES
) -> list[PrimaryActionCandidate]:
    """`02 §6` 후보 랭킹. 이 lane 은 **결정적 규칙만** 쓴다.

    embedding similarity 는 P-A codebook 이 archetype endpoint 문안을 동결한 뒤에야
    의미가 생긴다. 그때까지 `similarity_score = None`, `selection_basis = DETERMINISTIC_RULE` 이다 —
    `A2 §3` 규칙 G-1(최소 등급 원칙)이 요구하는 자리 그대로다.

    후보를 **버리지 않는다** (`A2` 규칙 C-3): 상위 `top_n` 은 `SELECTED`/`RUNNER_UP`,
    나머지는 `REJECTED` 로 남는다.

    정렬은 `min4_sort_key`(`A1 §2.6` 규칙 MIN-4) — `BRANCHING_LIMIT` 절단선이 이 순서로
    결정되므로(`A1 §2.6` "2차 키 교체는 BRANCHING_LIMIT 절단선을 움직인다"), 이 함수가
    매기는 `rank`/`SELECTED`와 Scout의 경로 열거가 항상 같은 순서를 본다.
    """
    ordered = sorted(raw, key=min4_sort_key)
    out: list[PrimaryActionCandidate] = []
    for i, c in enumerate(ordered):
        box = c.get("box") or {"x": 0.0, "y": 0.0, "w": 0.0, "h": 0.0}
        if i == 0:
            status = "SELECTED"
        elif i < top_n:
            status = "RUNNER_UP"
        else:
            status = "REJECTED"
        out.append(
            PrimaryActionCandidate(
                candidate_id=i,
                task_id=task_id,
                rank=i + 1,
                selector=str(c.get("selector")),
                dom_order=_dom_order_of(c),
                control_role=c.get("role") or c.get("tag"),
                accessible_name=c.get("aria_label") or c.get("visible_text"),
                visible_text=c.get("visible_text"),
                nearby_heading=c.get("nearby_heading"),
                href=c.get("href"),
                bbox_x=float(box["x"]),
                bbox_y=float(box["y"]),
                bbox_w=float(box["w"]),
                bbox_h=float(box["h"]),
                area_css_px2=float(c.get("area_css_px2") or 0.0),
                viewport_visible=1 if c.get("viewport_visible") else 0,
                similarity_score=None,
                selection_basis="DETERMINISTIC_RULE",
                selection_status=status,
                selection_confidence=None,
                ai_review_status="NOT_REQUIRED",
            )
        )
    return out


class L0Collector:
    """fixture 를 열어 L0 evidence 와 raw feature 를 수집한다."""

    def __init__(
        self,
        run: EvidenceRun,
        *,
        fixture_root: Path | None = None,
        execution_mode: ExecutionMode = ExecutionMode.FIXTURE,
        execution_scope: object | None = None,
        ax_join: bool = False,
    ) -> None:
        self.run = run
        self.fixture_root = Path(fixture_root).resolve() if fixture_root is not None else None
        self.execution_mode = execution_mode
        #: `REAL_TARGET` 에서만 의미가 있다 — 어느 승인 범위로 여는가 (`firewall.ExecutionScope`).
        self.execution_scope = execution_scope
        #: W5I — DOM 후보 selector 와 CDP AX slim node 를 잇고 `l0a/ax_join.json` 을 더 낸다.
        #: **기본값이 False 인 것이 가산성의 근거다.** 끄면 이 수집기는 base 와 바이트 단위로
        #: 같은 것을 낸다(artifact 도 manifest 도 `L0Observation` 도 동일). v3 만 켠다.
        self.ax_join = ax_join

    # ── 브라우저 컨텍스트 ──────────────────────────────────────────────────
    def _new_context(self, browser: Any) -> Any:
        """`02 §2` — fresh context, 로그인·쿠키 없음, ko-KR / Asia/Seoul / mobile UA / touch."""
        return browser.new_context(
            viewport={"width": VIEWPORT_WIDTH, "height": VIEWPORT_HEIGHT},
            device_scale_factor=DEVICE_SCALE_FACTOR,
            is_mobile=True,
            has_touch=True,
            locale=LOCALE,
            timezone_id=TIMEZONE_ID,
            user_agent=MOBILE_USER_AGENT,
            java_script_enabled=True,
        )

    @staticmethod
    def _ax_tree(context: Any, page: Page) -> list[dict[str, Any]]:
        """CDP 로 AX tree 를 가져온다 (Playwright 1.62 에서 `page.accessibility` 제거됨)."""
        cdp = context.new_cdp_session(page)
        try:
            cdp.send("Accessibility.enable")
            nodes = cdp.send("Accessibility.getFullAXTree").get("nodes", [])
        finally:
            cdp.detach()
        slim: list[dict[str, Any]] = []
        for n in nodes:
            role = (n.get("role") or {}).get("value")
            if role in (None, "none", "InlineTextBox"):
                continue
            name_node = n.get("name") or {}
            slim.append(
                {
                    "nodeId": n.get("nodeId"),
                    "backendDOMNodeId": n.get("backendDOMNodeId"),
                    "role": role,
                    # 이름이 계산되지 않은 것과 빈 문자열을 구분해 남긴다 (A2 §1.6 NAME_ABSENT).
                    "name": name_node.get("value"),
                    "name_computed": "value" in name_node,
                    "ignored": n.get("ignored", False),
                    "properties": [
                        {"name": p.get("name"), "value": (p.get("value") or {}).get("value")}
                        for p in (n.get("properties") or [])
                    ],
                }
            )
        return slim

    def _assert_target_matches_mode(self, target: FixtureTarget | RealServiceTarget) -> None:
        """모드와 target 타입의 짝을 확인한다 — firewall 이전의 1차 방어선.

        firewall 의 scheme 검사만으로도 잘못된 조합은 막히지만, 그때의 실패 메시지는
        "scheme 이 틀렸다" 가 되어 **무엇이 잘못됐는지**를 말해주지 못한다. 여기서
        타입 자체를 확인해 "fixture 실행기가 실제 서비스 target 을 받았다" 를 그대로
        말한다.
        """
        real = isinstance(target, RealServiceTarget)
        if self.execution_mode is ExecutionMode.REAL_TARGET and not real:
            raise ValueError(
                f"REAL_TARGET 모드에 {type(target).__name__} 이 들어왔다 — "
                "실제 수집 경로는 RealServiceTarget 만 받는다."
            )
        if self.execution_mode is not ExecutionMode.REAL_TARGET and real:
            raise ValueError(
                f"{self.execution_mode.value} 모드에 RealServiceTarget 이 들어왔다 — "
                "fixture 경로는 실제 서비스 target 을 받지 않는다."
            )

    # ── 수집 ─────────────────────────────────────────────────────────────
    def collect(
        self, target: FixtureTarget | RealServiceTarget, *, dismiss_pass: bool = True
    ) -> L0Observation:
        from playwright.sync_api import sync_playwright

        self._assert_target_matches_mode(target)
        requested_url = assert_navigation_allowed(
            self.execution_mode,
            target.url(self.fixture_root),
            fixture_root=self.fixture_root,
            scope=self.execution_scope,
            target_id=target.web_target_id if self.execution_scope is not None else None,
        )
        started = utc_now_iso()
        obs_id = observation_id(
            web_target_id=target.web_target_id,
            evidence_run_id=self.run.run_id,
            requested_url=requested_url,
            protocol_version=PROTOCOL_VERSION,
            collection_started_at=started,
        )
        self.run.open_observation(obs_id)

        notes: list[str] = []
        # W5I / `Δ20` — 수집기 지문을 **관측 행 자체**에 남긴다. 브라우저를 열기 전에
        # 붙이므로 항해가 실패해 `FAILED_*` 로 끝난 행에도 남는다. `ax_join` 이 켜진
        # v3 수집에서만 늘어나므로 legacy 경로의 바이트는 바뀌지 않는다.
        if self.ax_join:
            from ..v3_runner.ax_join import collector_provenance_notes

            notes.extend(collector_provenance_notes())
        status = MeasurementStatus.MEASURED
        paths: dict[str, str | None] = dict.fromkeys(
            ("dom", "ax", "screenshot_initial", "screenshot_fullpage", "computed_css", "probe"),
            None,
        )
        probe: dict[str, Any] = {}
        final_url: str | None = None
        interrupts: list[InterruptRecord] = []
        candidates: list[PrimaryActionCandidate] = []

        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True)
            context = self._new_context(browser)
            page = context.new_page()
            try:
                page.goto(requested_url, wait_until="load", timeout=NAV_TIMEOUT_MS)
                page.wait_for_timeout(SETTLE_MS)
                final_url = page.url

                # ── L0-a: 조작 없음 ──────────────────────────────────────
                dom = page.content().encode("utf-8")
                paths["dom"] = self._store(obs_id, "l0a/dom.html", dom)

                ax = self._ax_tree(context, page)
                paths["ax"] = self._store(obs_id, "l0a/ax.json", _json_bytes(ax))

                css = page.evaluate(_COMPUTED_CSS_JS, list(_COMPUTED_CSS_PROPERTIES))
                paths["computed_css"] = self._store(
                    obs_id, "l0a/computed_css.json", _json_bytes(css)
                )

                paths["screenshot_initial"] = self._store(
                    obs_id, "l0a/screen_initial.png", page.screenshot(full_page=False)
                )
                paths["screenshot_fullpage"] = self._store(
                    obs_id, "l0a/screen_fullpage.png", page.screenshot(full_page=True)
                )
                # full-page 캡처를 위한 프로그램적 스크롤은 episode 가 아니다 (A2 규칙 EP-2).
                page.evaluate("() => window.scrollTo(0, 0)")
                page.wait_for_timeout(SETTLE_MS)

                # `D-R0-42` 이중화 — probe 단 marker 게이팅(W2, `l0_probe.js`)이
                # `execution_mode` 인자 없이는 `undefined`가 되어 FIXTURE 취급으로
                # 조용히 유지되고 있었다(`l0_probe.js` 자체 주석이 이를 명시). 이 값을
                # 실제로 전달한다 — engine 단 단락(우연 일치 위양성 방지)과 별개의
                # 두 번째 겹이다(`C-BLOCKER` 시정, W4 소유 호출부만 수정, `l0_probe.js`
                # 는 W2 소유라 손대지 않는다).
                probe = page.evaluate(PROBE_JS, self.execution_mode.value)
                paths["probe"] = self._store(obs_id, "l0a/probe.json", _json_bytes(probe))

                # ── W5I: selector <-> backendDOMNodeId <-> AX slim node ────
                # `l0_probe.js` 는 accessible name 을 계산하지 않고(이름의 *출처*만 낸다),
                # 계산된 이름은 `ax` slim node 에만 있는데 그 노드는 selector 가 아니라
                # `backendDOMNodeId` 로 키잉된다. `backendDOMNodeId` 는 페이지 JS 에서
                # 관측 불가능하므로 probe 로는 원리적으로 이을 수 없다 — CDP 를 쥔 여기서
                # 잇는다. 산출은 **새 artifact 하나**뿐이고 기존 슬롯/필드는 건드리지 않는다.
                if self.ax_join:
                    try:
                        # 지역 import 다. `v3_runner` 패키지의 `__init__` 은 다른 worker 가
                        # 소유하고 그쪽이 engine 을 다시 import 할 수 있다 — 모듈 최상단에서
                        # 끌어오면 순환 import 가 생긴다. 끄고 쓰는 경로에서는 아예 로드되지
                        # 않는 편이 가산성에도 맞다.
                        from ..v3_runner.ax_join import AX_JOIN_RELPATH, collect_ax_join

                        # `_ax_tree` 와 같은 규율 — 세션은 반드시 되돌려준다. 50 target 을
                        # 도는 동안 관측당 하나씩 새다가는 수집 후반이 조용히 달라진다.
                        cdp = context.new_cdp_session(page)
                        try:
                            payload = collect_ax_join(cdp, probe=probe, ax_nodes=ax)
                        finally:
                            cdp.detach()
                        self._store(obs_id, AX_JOIN_RELPATH, _json_bytes(payload.as_dict()))
                    except Exception as exc:  # 조인 실패가 관측 실패는 아니다
                        notes.append(f"AX_JOIN_FAILED: {type(exc).__name__}: {exc}")

                # ── L0-b: 후보·공간·blocking·의미·dismiss control (조작 없음) ──
                candidates = rank_primary_action_candidates(
                    probe["raw_features"].get("primary_action_candidates", []),
                    task_id=target.task_id,
                )
                interrupts = self._build_interrupts(probe, candidates)

                # ── L0-c: dismissal 시도 (interrupt 당 정확히 1회) ─────────
                if dismiss_pass and interrupts:
                    self._dismiss_pass(page, obs_id, interrupts, probe)
            except Exception as exc:
                status = _classify_failure(exc)
                notes.append(f"{type(exc).__name__}: {exc}")
            finally:
                context.close()
                browser.close()

        finished = utc_now_iso()
        gaps = missing_slots({**paths, "manifest": "manifest.jsonl"})
        if status is MeasurementStatus.MEASURED and gaps:
            status = MeasurementStatus.FAILED_EVIDENCE_INCOMPLETE
            notes.append(f"evidence 슬롯 결손: {gaps} (02 §11 · 07 §4)")

        viewport = probe.get("raw_features", {}).get("viewport", {})
        selected = next((c for c in candidates if c.selection_status == "SELECTED"), None)
        occlusions = [i.primary_action_occlusion for i in interrupts if i.primary_action_occlusion]

        return L0Observation(
            observation_id=obs_id,
            web_target_id=target.web_target_id,
            evidence_run_id=self.run.run_id,
            requested_url=requested_url,
            final_url=final_url,
            measurement_status=status.value,
            measurement_status_detail=None,
            collection_started_at=started,
            collection_finished_at=finished,
            audit_date=_audit_date(started),
            viewport_configured_width=VIEWPORT_WIDTH,
            viewport_configured_height=VIEWPORT_HEIGHT,
            viewport_width=viewport.get("layout_width"),
            viewport_height=viewport.get("layout_height"),
            device_pixel_ratio=viewport.get("device_pixel_ratio"),
            dom_path=paths["dom"],
            ax_path=paths["ax"],
            screenshot_initial_path=paths["screenshot_initial"],
            screenshot_fullpage_path=paths["screenshot_fullpage"],
            computed_css_path=paths["computed_css"],
            probe_path=paths["probe"],
            manifest_path="manifest.jsonl",
            max_overlay_coverage=(
                max((i.viewport_coverage for i in interrupts), default=0.0) if interrupts else 0.0
            ),
            # 규칙 C-1 — SELECTED 후보가 0행이면 NULL 이지 0 이 아니다.
            primary_action_visible_initial=(
                selected.viewport_visible if selected is not None else None
            ),
            max_primary_action_occlusion=(max(occlusions) if occlusions else 0.0),
            interrupts=interrupts,
            primary_action_candidates=candidates,
            raw_features=probe.get("raw_features", {}),
            notes=notes,
        )

    # ── 내부 ─────────────────────────────────────────────────────────────
    def _store(self, obs_id: str, relpath: str, data: bytes) -> str:
        """산출물을 쓰고 **run 디렉터리 기준 상대경로**를 돌려준다 (`07 §3`).

        경로를 `observation_id` 로 네임스페이스한다. manifest 의 유일성 키는
        `(observation_id, relpath)` 라 논리적으로는 충돌하지 않지만, 두 관측이 같은
        `l0a/dom.html` 을 쓰면 **디스크에서** 충돌한다. 그것을 덮어쓰기로 해결하면
        `02 §12` append-only 가 깨지므로, 경로 자체를 관측별로 가른다.
        """
        namespaced = f"{obs_id}/{relpath}"
        self.run.write_artifact(obs_id, namespaced, data)
        return namespaced

    def _build_interrupts(
        self, probe: dict[str, Any], candidates: list[PrimaryActionCandidate]
    ) -> list[InterruptRecord]:
        raw = probe["raw_features"]
        selected = next((c for c in candidates if c.selection_status == "SELECTED"), None)
        primary_box = (
            {
                "x": selected.bbox_x,
                "y": selected.bbox_y,
                "w": selected.bbox_w,
                "h": selected.bbox_h,
            }
            if selected
            else None
        )
        by_container = {
            d["container_selector"]: d for d in raw.get("dismiss_control_candidates", [])
        }
        scroll_locked = bool(raw.get("body_scroll_lock", {}).get("locked"))

        records: list[InterruptRecord] = []
        for idx, cand in enumerate(raw.get("modal_overlay_candidates", [])):
            if not cand.get("visible"):
                continue
            classification = classify_interrupt(cand)
            overlap = _overlap(cand.get("box"), primary_box)
            occlusion = (
                round(overlap / selected.area_css_px2, 4)
                if selected and selected.area_css_px2 > 0
                else None
            )
            # `02 §5` 3차 — 대표기능을 완전히 가리거나 body scroll lock 이면 blocking.
            blocking = int(
                (occlusion is not None and occlusion >= 0.999)
                or (scroll_locked and cand.get("viewport_coverage", 0) >= 0.5)
            )

            dismiss = by_container.get(cand.get("selector"), {})
            controls = dismiss.get("dismiss_control_candidates") or []
            best = next(
                (c for c in controls if c.get("hittable")), controls[0] if controls else None
            )
            exists = 1 if best else 0
            visible_flag: int | None = None
            if best:
                visible_flag = int(
                    best.get("display") != "none"
                    and best.get("visibility") != "hidden"
                    and float(best.get("opacity") or 1) > 0.01
                    and float(best.get("viewport_overlap_css_px2") or 0) > 0
                    and bool(best.get("hittable"))
                )

            records.append(
                InterruptRecord(
                    interrupt_index=idx,
                    selector=str(cand.get("selector")),
                    candidate_sources=list(cand.get("candidate_sources") or []),
                    viewport_overlap_css_px2=float(cand.get("viewport_overlap_css_px2") or 0.0),
                    viewport_coverage=float(cand.get("viewport_coverage") or 0.0),
                    interrupt_form=classification.interrupt_form.value,
                    interrupt_form_status=classification.interrupt_form_status.value,
                    interrupt_semantic=classification.interrupt_semantic.value,
                    interrupt_semantic_status=classification.interrupt_semantic_status.value,
                    blocks_primary_action=blocking,
                    primary_action_occlusion=occlusion,
                    dismiss_control_exists=exists,
                    dismiss_control_visible=visible_flag,
                    # NAME_ABSENT(이름 없음이 관측됨) 과 NULL(잴 대상 없음) 을 섞지 않는다.
                    dismiss_control_accessible_name=(
                        (best.get("accessible_name_source") or NAME_ABSENT) if best else None
                    ),
                    dismiss_control_width=(best.get("width_css_px") if best else None),
                    dismiss_control_height=(best.get("height_css_px") if best else None),
                    dismiss_persistence_hint=int(bool(best and best.get("persistence_hint"))),
                )
            )
        return records

    def _dismiss_pass(
        self,
        page: Page,
        obs_id: str,
        interrupts: list[InterruptRecord],
        probe: dict[str, Any],
    ) -> None:
        """`A1 §3.3` 6차 — interrupt 당 **정확히 1회** 시도하고 before/after 를 남긴다."""
        by_container = {
            d["container_selector"]: d
            for d in probe["raw_features"].get("dismiss_control_candidates", [])
        }
        for rec in interrupts:
            before = f"l0c/{rec.interrupt_index}/screen_before.png"
            rec.dismiss_screenshot_before = self._store(
                obs_id, before, page.screenshot(full_page=False)
            )

            method = DismissMethod.NONE
            failure: DismissFailureMode | None = None
            container = by_container.get(rec.selector, {})
            controls = container.get("dismiss_control_candidates") or []
            control = next((c for c in controls if c.get("hittable")), None)

            try:
                if rec.dismiss_control_visible and control:
                    method = DismissMethod.CONTROL_CLICK
                    page.click(control["selector"], timeout=2000)
                elif container.get("is_dialog_element"):
                    method = DismissMethod.DIALOG_CLOSE
                    page.evaluate(
                        "(s) => { const d = document.querySelector(s); if (d && d.close) d.close(); }",
                        rec.selector,
                    )
                elif controls:
                    method = DismissMethod.CONTROL_CLICK
                    failure = DismissFailureMode.NOT_HITTABLE
                else:
                    method = DismissMethod.ESCAPE_KEY
                    page.keyboard.press("Escape")
            except Exception:
                failure = DismissFailureMode.NOT_HITTABLE

            page.wait_for_timeout(SETTLE_MS)
            state = page.evaluate(_DISMISS_STATE_JS, rec.selector)
            succeeded = int(
                not state["present"] or state["viewport_overlap"] <= 0 or not state["hittable"]
            )
            if not succeeded and failure is None:
                failure = DismissFailureMode.NO_STATE_CHANGE
            if not controls and not container.get("is_dialog_element") and not succeeded:
                failure = DismissFailureMode.NO_CONTROL
                method = DismissMethod.NONE

            rec.dismiss_method = method.value
            rec.dismiss_succeeded = succeeded
            # dismiss_succeeded = 1 ↔ dismiss_failure_mode IS NULL (A2 §1.6 동치)
            rec.dismiss_failure_mode = (
                None if succeeded else (failure or DismissFailureMode.NO_STATE_CHANGE).value
            )
            rec.dismiss_screenshot_after = self._store(
                obs_id,
                f"l0c/{rec.interrupt_index}/screen_after.png",
                page.screenshot(full_page=False),
            )
            rec.dismiss_dom_after = self._store(
                obs_id,
                f"l0c/{rec.interrupt_index}/dom_after.html",
                page.content().encode("utf-8"),
            )


def _json_bytes(obj: Any) -> bytes:
    return (json.dumps(obj, ensure_ascii=False, sort_keys=True, indent=1) + "\n").encode("utf-8")


def _audit_date(started_at: str) -> str:
    """`A1 §6.1` — `audit_date` 는 `collection_started_at` 의 파생이지 독립 입력이 아니다."""
    from datetime import datetime
    from zoneinfo import ZoneInfo

    dt = datetime.fromisoformat(started_at.replace("Z", "+00:00"))
    return dt.astimezone(ZoneInfo(TIMEZONE_ID)).date().isoformat()


def _classify_failure(exc: BaseException) -> MeasurementStatus:
    """`02 §13` — 수집 실패는 접근성 FAIL 이 아니다. 별도 measurement status 로 기록한다."""
    name = type(exc).__name__
    text = str(exc).lower()
    if "timeout" in name.lower() or "timeout" in text:
        return MeasurementStatus.FAILED_PAGE_TIMEOUT
    if "crash" in text or "closed" in text:
        return MeasurementStatus.FAILED_BROWSER_CRASH
    if "net::" in text or "dns" in text:
        return MeasurementStatus.FAILED_ROBOTS_OR_TRANSPORT
    return MeasurementStatus.FAILED_EVIDENCE_INCOMPLETE
