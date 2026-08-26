"""popup/modal 검출 — SSOT 02 §5 의 4단계 파이프라인.

1차 후보 -> 2차 공간검사 -> 3차 blocking 여부 -> 4차 의미분류.

4차 의미분류는 결정론적 DOM 텍스트 규칙을 우선하고, 모호하면 VLM 에게
넘기는 자리를 인터페이스(``SemanticClassifier``)로만 남긴다 — 이 fixture
레인은 실제 VLM 을 호출하지 않는다(로컬/합성 픽스처 전용, 실서비스 판정
금지). 배선이 맞는지는 결정론적 스텁 분류기로 테스트한다.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

OVERLAY_CLASSES = frozenset(
    {
        "BLOCKING_MODAL",
        "PROMOTION_MODAL",
        "COOKIE_CONSENT",
        "ADVERTISEMENT",
        "APP_INSTALL_PROMPT",
        "LOGIN_PROMPT",
        "CHAT_WIDGET",
        "BANNER",
        "TOAST",
        "UNKNOWN",
    }
)


@dataclass
class BBox:
    x: float
    y: float
    width: float
    height: float

    @property
    def area(self) -> float:
        return max(0.0, self.width) * max(0.0, self.height)

    def intersection_area(self, other: BBox) -> float:
        x1 = max(self.x, other.x)
        y1 = max(self.y, other.y)
        x2 = min(self.x + self.width, other.x + other.width)
        y2 = min(self.y + self.height, other.y + other.height)
        return max(0.0, x2 - x1) * max(0.0, y2 - y1)


@dataclass
class OverlayCandidate:
    element_ref: str
    bbox: BBox
    is_dialog_tag: bool = False
    role_dialog: bool = False
    aria_modal: bool = False
    is_fixed_or_sticky: bool = False
    high_z_index: bool = False
    has_backdrop: bool = False
    body_scroll_locked: bool = False
    pointer_intercepts: bool = False
    focus_contained: bool = False
    accessible_name: str | None = None
    dismiss_control_present: bool = False
    dismiss_control_visible: bool = False
    dismiss_control_target_size_ok: bool = False
    dismiss_control_contrast_ratio: float | None = None
    dismiss_success: bool | None = None  # None=시도 안 함, 실제 클릭 후 재확인한 결과만 채운다
    dom_text_sample: str = ""

    @property
    def is_candidate(self) -> bool:
        """1차 후보 판정 — 02 §5 목록 중 하나 이상."""
        return any(
            [
                self.is_dialog_tag,
                self.role_dialog,
                self.aria_modal,
                self.is_fixed_or_sticky,
                self.high_z_index,
                self.has_backdrop,
                self.body_scroll_locked,
                self.pointer_intercepts,
                self.focus_contained,
            ]
        )


@dataclass
class OverlayAssessment:
    candidate: OverlayCandidate
    overlay_coverage: float
    primary_action_occlusion: float | None
    is_blocking: bool
    overlay_class: str
    classification_source: str  # "DOM_TEXT_RULE" | "VLM_PENDING_UNRESOLVED" | "UNCLASSIFIED"


class SemanticClassifier(Protocol):
    def __call__(self, candidate: OverlayCandidate) -> str | None: ...


def rule_based_class(candidate: OverlayCandidate) -> str | None:
    """4차 1단계: DOM text/accessible name 우선 분류 (02 §5)."""
    text = (candidate.dom_text_sample or "").lower()
    name = (candidate.accessible_name or "").lower()
    hay = f"{text} {name}"
    if any(k in hay for k in ("cookie", "쿠키")):
        return "COOKIE_CONSENT"
    if any(k in hay for k in ("앱 설치", "앱으로 보기", "app store", "play store", "다운로드")):
        return "APP_INSTALL_PROMPT"
    if any(k in hay for k in ("로그인", "login", "sign in")):
        return "LOGIN_PROMPT"
    if any(k in hay for k in ("채팅", "chat", "상담원")):
        return "CHAT_WIDGET"
    if any(k in hay for k in ("광고", "sponsored", "ad ")):
        return "ADVERTISEMENT"
    if candidate.is_dialog_tag or candidate.role_dialog or candidate.aria_modal:
        return "PROMOTION_MODAL"
    return None


def spatial_metrics(
    candidate: OverlayCandidate, viewport: BBox, primary_action: BBox | None
) -> tuple[float, float | None]:
    """2차 공간검사: OverlayCoverage, PrimaryActionOcclusion (SSOT §8)."""
    coverage = 0.0
    if viewport.area > 0:
        coverage = candidate.bbox.intersection_area(viewport) / viewport.area
    occlusion = None
    if primary_action is not None and primary_action.area > 0:
        occlusion = candidate.bbox.intersection_area(primary_action) / primary_action.area
    return coverage, occlusion


def is_blocking(
    candidate: OverlayCandidate,
    coverage: float,
    occlusion: float | None,
    must_dismiss_for_primary: bool,
) -> bool:
    """3차 blocking 여부: 대표기능을 가리는가 / 진입 전 닫아야 하는가 / 화면
    큰 부분을 덮는가 (02 §5)."""
    if occlusion is not None and occlusion > 0.3:
        return True
    if coverage > 0.6:
        return True
    return bool(must_dismiss_for_primary)


def blocking_modal_count(assessments: list[OverlayAssessment]) -> int:
    return sum(1 for a in assessments if a.is_blocking)


def assess_overlay(
    candidate: OverlayCandidate,
    viewport: BBox,
    primary_action: BBox | None,
    must_dismiss_for_primary: bool,
    classifier: SemanticClassifier | None = None,
) -> OverlayAssessment:
    coverage, occlusion = spatial_metrics(candidate, viewport, primary_action)
    blocking = is_blocking(candidate, coverage, occlusion, must_dismiss_for_primary)
    cls = rule_based_class(candidate)
    source = "DOM_TEXT_RULE"
    if cls is None:
        cls = classifier(candidate) if classifier is not None else None
        if cls is None:
            cls = "UNKNOWN"
            source = "UNCLASSIFIED"
        else:
            source = "VLM_PENDING_RESOLVED"
    return OverlayAssessment(
        candidate=candidate,
        overlay_coverage=coverage,
        primary_action_occlusion=occlusion,
        is_blocking=blocking,
        overlay_class=cls,
        classification_source=source,
    )
