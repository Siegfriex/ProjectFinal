"""L1 Scout → bounded minimality search → Path Freeze → deterministic Replay.

`02 §7` · `§8` · `§9` / `A1 §1` · `§2` · `§4` / `A2 §1.5` · `§1.12`.

## Scout 의 목적은 "최소 경로 발견" 이다

`02 §7`: *자유롭게 full task 를 수행하지 않는다.* 그래서 이 엔진은 탐욕적으로 한 경로를
끝까지 파고들지 않고, **activation 수를 늘려가며 폭우선으로** 후보 경로를 열거한다
(bounded minimality search). 먼저 발견된 경로가 곧 최소 경로다.

## 예산이 없으면 L1 얕은 진입이 full task 로 변질된다 (A1 §2)

선언적 금지목록은 사람에게만 작동한다. `ScoutBudget` 의 네 값이 그 금지를 기계화한다.
예산에 걸린 관측은 `MPFED = 8` 이 **아니라** "8회 안에서는 관측되지 않았다" 이며
`NULL` 로 저장된다 (`A1 §2.4` · 금지 전이 X-5).

## Freeze / Replay

Scout 가 찾은 경로는 `TaskManifest` 로 동결된다. 본수집은 매번 다시 탐색하지 않고
그 경로를 결정적으로 replay 한다. **replay 가 깨지면 조용히 자유탐색으로 대체하지 않고**
`UNRESOLVED_REPLAY_BROKEN` 을 남긴다 (`02 §8` · `A2` 규칙 E-2).
"""

from __future__ import annotations

import hashlib
import json
import re
import time
from collections import deque
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any
from urllib.parse import unquote_plus

from .depth import (
    DepthResult,
    assign_depth_segments,
    auth_gate_before_endpoint,
    auth_gate_observed,
    compute_depth,
    gate_outcome_from_decision,
)
from .evidence import EvidenceRun
from .firewall import ExecutionMode, assert_navigation_allowed
from .gate_classifier import GateKindDecision, GateSignals, classify_gate_kind
from .l0_collector import PROBE_JS, SETTLE_MS, L0Collector, min4_sort_key
from .provenance import ShadowProvenance, utc_now_iso
from .vocabulary import (
    AreaSignalStatus,
    EndpointStatus,
    EndpointStatusDetail,
    EpisodeEndedBy,
    EpisodeKind,
    InputMode,
    InteractionArchetype,
    RegionSignalType,
)

if TYPE_CHECKING:  # pragma: no cover
    from playwright.sync_api import Page


# ── `A1 §2.1` 예산. 전부 **수집 파라미터**이며 해석 임계값이 아니다 (`A1 §0.4`). ──────
@dataclass(frozen=True)
class ScoutBudget:
    max_activations_per_task: int = 8
    max_state_revisits: int = 2
    max_scout_wall_clock_s: float = 180.0
    max_consecutive_no_state_change: int = 2
    #: 한 state 에서 분기시킬 후보 수. 열거의 폭을 유한하게 만드는 구현 파라미터다.
    branching_limit: int = 4
    #: `A1 §4.3` scroll episode 종료 판정용. P-C 검증 후 동결.
    scroll_idle_ms: int = 500


class BudgetExhausted(Exception):
    """예산이 발화했다. 접근성 FAIL 이 아니라 measurement status 다 (`A1 §2.3`)."""

    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


@dataclass(frozen=True)
class TaskDefinition:
    """`dim_representative_task` 의 이 lane 용 최소 형태.

    `region_definition` · `endpoint_definition` 의 **서비스별 값은 P-A codebook 이 동결**한다
    (`A1 §1.8` · `A2 §1.9`). 여기서는 fixture 가 `data-region` / `data-endpoint` 로
    선언한 토큰을 그 자리에 넣는다 — 실제 서비스 값을 이 lane 이 정하지 않는다는 뜻이다.
    """

    task_id: str
    archetype: InteractionArchetype
    region_definition: str | None
    endpoint_definition: str | None
    region_signal_type: RegionSignalType = RegionSignalType.DOM_AX_ROLE
    endpoint_signal_type: RegionSignalType = RegionSignalType.DOM_AX_ROLE
    query_text: str = "고령자 접근성"

    def mapping_frozen_allowed(self) -> bool:
        """`A2` 규칙 P-2 — `CODEBOOK_PENDING` 인 task 는 `FROZEN` 으로 전이할 수 없다."""
        return RegionSignalType.CODEBOOK_PENDING not in (
            self.region_signal_type,
            self.endpoint_signal_type,
        )


@dataclass
class TaskStep:
    """`fact_task_step` 한 행 = **사용자 activation 한 번** (`02 §9`)."""

    step_index: int
    state_id: str
    url: str
    clicked_selector: str
    control_role: str | None
    accessible_name: str | None
    area_signal_detected: int
    endpoint_signal_detected: int
    auth_gate_detected: int
    popup_present: int
    counts_toward_depth: int = 1
    depth_segment: str | None = None
    screenshot_path: str | None = None


@dataclass
class TaskEpisode:
    """`fact_task_episode` 한 행 (`A1 §4.4` · `A2 §1.12`). Depth 에 가산하지 않는다."""

    episode_index: int
    episode_kind: str
    target_selector: str
    state_id: str
    started_after_step_index: int
    ended_by: str
    input_mode: str | None = None
    scroll_distance_px: float | None = None


@dataclass
class TaskEntry:
    """`fact_task_entry` 한 행."""

    task_observation_id: str
    task_id: str
    archetype: str
    endpoint_status: str
    endpoint_status_detail: str | None
    endpoint_reached: int
    area_signal_status: str
    ned: int | None
    ied: int | None
    mpfed: int | None
    auth_gate_before_endpoint: int
    auth_gate_observed: int
    forced_dismissal_count: int
    text_input_episode_count: int
    scroll_episode_count: int
    steps: list[TaskStep] = field(default_factory=list)
    episodes: list[TaskEpisode] = field(default_factory=list)
    budget_reason: str | None = None
    notes: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class TaskManifest:
    """`02 §8` Path Freeze 산출물. replay 의 유일한 입력이다."""

    task_id: str
    archetype: str
    web_target_id: str
    entry_fixture: str
    frozen_at: str
    path: list[dict[str, Any]]
    endpoint_status: str
    endpoint_status_detail: str | None
    ned: int | None
    ied: int | None
    mpfed: int | None
    provenance: dict[str, Any]

    def path_sha256(self) -> str:
        payload = json.dumps(self.path, ensure_ascii=False, sort_keys=True).encode("utf-8")
        return hashlib.sha256(payload).hexdigest()

    def as_dict(self) -> dict[str, Any]:
        return {**asdict(self), "path_sha256": self.path_sha256()}


def state_key(url: str, dom: str) -> str:
    """DOM state key. URL 이 바뀌지 않는 SPA 에서도 상태 전이를 잡아야 한다 (`A1 §2`)."""
    digest = hashlib.sha256(dom.encode("utf-8", "replace")).hexdigest()[:16]
    return f"{url.rsplit('/', 1)[-1]}:{digest}"


# ── 실사이트 신호 원자(atom) — D-R0-14 · D-R0-16 ─────────────────────────────
# 전부 `raw_features`(probe.json, 렌더 후 상태)만 읽는다. `dom.html`/`ax.json` 스냅샷은
# 별도 시점에 캡처된 evidence slot 이라 이 함수들의 입력이 아니다 — LABEL_FROZEN 이후
# Director 가 지적한 NH 쌍(F-A3.1: L2/L3 라벨 불일치 원인 = 서로 다른 evidence slot 열람)과
# 같은 실수를 이 lane 이 반복하지 않기 위함이다. 전부 **존재(exists) 판정**이다 — 개수 임계값
# 판정이 아니다: `primary_action_candidates`(cap 200)·`accessible_name_sources`(cap 300) 는
# 실측 n=58 중 각 7/58·13/58 이 cap 에 도달했다(`T-B-FINDING-002`) — "전부 스캔해야 성립"하는
# 판정 방식은 절단된 관측에서 무너진다. `exists`는 cap 안에 하나라도 있으면 성립하므로 절단에
# 상대적으로 강건하다(완전한 면역은 아니다 — cap 안에 전혀 없는데 cap 밖에만 있는 극단값은
# 여전히 위음성일 수 있다. `observation_truncation_caveats`가 그 잔여 위험을 note 로 남긴다).
_COMMERCE_VOCAB = re.compile(
    r"(구매하기|바로\s*구매|장바구니|담기|주문하기|결제하기|buy\s*now|add\s*to\s*cart|checkout)",
    re.IGNORECASE,
)
#: Branch U(UTILITY_ENTRY) 의 "single-purpose tool surface" 근거(`D-R0-67-1`, W2 rework).
#: **`button`/`role=button` 을 뺐다** — 일반 control(버튼 하나) 존재만으로는 "도구 표면"의
#: 증거가 되지 않는다(catch-all 이었다: C 진단 — 버튼만 있으면 archetype 을 안 가리고
#: UTILITY_ENTRY 가 발화했다). 실제로 값을 입력받는 위젯(input/select/textarea)이 최소
#: 하나 있어야 "이 화면이 뭔가를 입력받아 처리하는 도구"라는 최소한의 구조적 증거가 된다.
#: 이 좁힘의 부작용: 입력 없이 버튼 하나로 끝나는 순수 단일 액션 도구(예: 다운로드 버튼
#: 하나뿐인 페이지)는 이제 evidence 를 못 받는다 — `AMBIGUOUS_UNRESOLVED` 로 남는 것이
#: 의도된 결과다(force-map 금지, `D-R0-12`).
_UTILITY_TOOL_INPUT_TAGS = frozenset({"input", "select", "textarea"})

#: `D-R0-67-2` family-specific structured-data 매칭. `@type` 문자열은 대소문자가 섞여
#: 오므로(`Product`/`product`) 소문자로 비교한다.
_ITEM_STRUCTURED_TYPES = frozenset({"product"})
_PLACE_STRUCTURED_TYPES = frozenset({"localbusiness", "place"})
_CONTENT_STRUCTURED_TYPES = frozenset({"article", "newsarticle", "blogposting"})
_COMMUNICATION_STRUCTURED_TYPES = frozenset(
    {"discussionforumposting", "comment", "socialmediaposting"}
)


def _is_enabled(candidate: dict[str, Any]) -> bool:
    """`D-R0-70` — HITTABLE(기하학적 hit-test) 은 ENABLED(기능적으로 조작 가능함) 를
    함의하지 않는다. `enabled` 필드가 raw 에 없으면(이번 세션 이전 probe 스냅샷과의
    하위호환) True 로 취급한다 — 결측을 "비활성"으로 단정하지 않는다(규칙 N-3 계열 판단).
    """
    if "enabled" not in candidate:
        return True
    return bool(candidate.get("enabled"))


def _hittable_primary_action_candidates(raw: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        c for c in raw.get("primary_action_candidates", []) if c.get("hittable") and _is_enabled(c)
    ]


def _search_control_ready(raw: dict[str, Any]) -> bool:
    """Branch Q/P Region — FORM_STRUCTURE. marker 비의존, cap 없는 신호(`region_signals`).
    `D-R0-70` — `disabled` 검색 input(예: 로딩 중 비활성화된 검색창)은 region 성립에 안 쓴다.
    """
    signals = raw.get("region_signals", {})
    return any(
        s.get("visible") and s.get("in_form") and s.get("has_submit") and _is_enabled(s)
        for s in signals.get("search_inputs", [])
    )


def _query_reflected_in_url(raw: dict[str, Any], task: TaskDefinition) -> bool:
    """Branch Q/P Endpoint(query submitted) — URL_PATTERN.

    "자동완성 노출만으로 endpoint 처리하지 않는다"(RF-DT §5 Branch Q) — 대신 **실제로
    제출한 값**이 URL 에 반영됐는지를 본다. 서비스별 파라미터 이름(`?q=`/`?query=`/...)을
    추측하지 않는다 — business prior 를 쓰지 않는다는 Layer O 원칙 그대로다.
    """
    if not task.query_text:
        return False
    url = raw.get("viewport", {}).get("final_url") or ""
    if "?" not in url:
        return False
    # `unquote_plus` — GET form(`application/x-www-form-urlencoded`) 제출은 공백을 `%20`
    # 이 아니라 `+`로 인코딩한다. `unquote`만 쓰면 실제 form 제출을 놓친다(실측으로 확인).
    return task.query_text in unquote_plus(url)


def _repeated_card_list_present(raw: dict[str, Any]) -> bool:
    """ "content card/link list" 를 list-container 소속 여부로 판정한다(`l0_probe.js`
    `repeated_structure`, cap 없음). heading 근접성(`nearby_heading`)은 작은 페이지에서
    항상 참에 가까워 판별력이 없었다(`depth_path_3` 류 픽스처로 실측 확인) — 그래서 이
    신호는 그것을 쓰지 않는다.

    `D-R0-67-2` — 이 함수 **단독으로는 더 이상 Item/Place/Communication 의 region evidence
    가 아니다.** family 별 전용 함수(`_item_region_evidence` 등)의 구성요소로만 쓰인다.
    Content-like 만 이 신호를 단독으로도 충분한 evidence 로 받는다 — 다른 family 가 자기
    신호로 못 채간 "순수 카드/링크 목록"의 residual 자리이기 때문이다(Stage2 원문이
    Content-like 에 더 구체적인 구조 신호를 추가로 요구하지 않는다).

    `D-R0-70` — `hittable_enabled_list_item_link_count`(enabled 를 요구)가 있으면 그걸
    쓰고, 구 raw 스냅샷과의 호환을 위해 없으면 `hittable_list_item_link_count`로 폴백한다.
    """
    structure = raw.get("repeated_structure", {})
    if "hittable_enabled_list_item_link_count" in structure:
        return bool(structure.get("hittable_enabled_list_item_link_count", 0))
    return bool(structure.get("hittable_list_item_link_count", 0))


def _content_endpoint_real(raw: dict[str, Any]) -> bool:
    """Branch C(CONTENT_OPEN)/M(COMMUNICATION_ENTRY 비-gate, 최후 폴백) Endpoint —
    DOM_AX_ROLE/MEDIA_STATE. article body open 또는 main media playback start. 둘 다
    marker 가 필요 없는 실신호다.
    """
    signals = raw.get("endpoint_signals", {})
    return bool(signals.get("article_present")) or bool(signals.get("video_playing"))


def _commerce_control_present(raw: dict[str, Any]) -> bool:
    """Branch I(ITEM_DETAIL) Endpoint evidence 일부 — 거래 control 의 **존재**(D-R0-06,
    활성화 아님. 이 lane 에서 "존재"가 정당한 evidence 로 명시 허용된 유일한 자리다).
    `accessible_name_sources`(cap 300)에서 결정적 어휘로 존재만 확인한다.
    """
    for row in raw.get("accessible_name_sources", []):
        name = " ".join(
            filter(None, [row.get("aria_label"), row.get("visible_text"), row.get("title")])
        )
        if _COMMERCE_VOCAB.search(name):
            return True
    return False


def _structured_data_types(raw: dict[str, Any]) -> set[str]:
    """`D-R0-67-2` — `l0_probe.js`(`family_signals.structured_data_types`, JSON-LD `@type`)
    를 소문자 집합으로 정규화한다. 결정적 구조 신호다(파싱된 스키마 값 그대로) — 어휘
    추측이 아니다.
    """
    return {str(t).lower() for t in raw.get("family_signals", {}).get("structured_data_types", [])}


def _utility_tool_surface_present(raw: dict[str, Any]) -> bool:
    """Branch U(UTILITY_ENTRY) Region=Endpoint(`D-R0-41`) — DOM_AX_ROLE.
    "function surface entry control" 이자 "primary control이 present/actionable".

    `D-R0-67-1` 시정 — `primary_action_candidates`(제출/네비게이션 control 전용 쿼리)가
    아니라 `l0_probe.js` 의 `utility_input_widgets`(값을 입력받는 위젯 전용 쿼리,
    `type=search`/`submit`/`button`/`hidden` 제외)를 쓴다. 실제 입력 위젯
    (`_UTILITY_TOOL_INPUT_TAGS`)이 hittable ∧ enabled 상태로 최소 하나 있어야 한다.
    """
    for c in raw.get("utility_input_widgets", []):
        if c.get("tag") in _UTILITY_TOOL_INPUT_TAGS and c.get("hittable") and _is_enabled(c):
            return True
    return False


def _item_region_evidence(raw: dict[str, Any]) -> bool:
    """`D-R0-67-2` Item-like Region — Product structured data,
    또는 (price pattern 또는 거래 control 존재) AND list-container 카드.
    """
    if _ITEM_STRUCTURED_TYPES & _structured_data_types(raw):
        return True
    if not _repeated_card_list_present(raw):
        return False
    fam = raw.get("family_signals", {})
    return bool(fam.get("price_pattern_present")) or _commerce_control_present(raw)


def _item_endpoint_evidence(raw: dict[str, Any]) -> bool:
    """`D-R0-67-2` Item-like Endpoint — Product structured data,
    또는 거래 control 존재 AND list-container 카드(상세면 문맥)."""
    if _ITEM_STRUCTURED_TYPES & _structured_data_types(raw):
        return True
    return _commerce_control_present(raw) and _repeated_card_list_present(raw)


def _place_region_evidence(raw: dict[str, Any]) -> bool:
    """`D-R0-67-2` Place-like Region — LocalBusiness/Place structured data,
    또는 map/place 검색 control, 또는 (주소 어휘 AND list-container 카드)."""
    if _PLACE_STRUCTURED_TYPES & _structured_data_types(raw):
        return True
    fam = raw.get("family_signals", {})
    if fam.get("map_control_present"):
        return True
    return bool(fam.get("address_vocabulary_present")) and _repeated_card_list_present(raw)


def _place_endpoint_evidence(raw: dict[str, Any], task: TaskDefinition) -> bool:
    """`D-R0-67-2` Place-like Endpoint — "place query submitted"(URL_PATTERN, 기존
    `_query_reflected_in_url` 재사용) 또는 "place detail opened"(LocalBusiness/Place
    structured data)."""
    if _PLACE_STRUCTURED_TYPES & _structured_data_types(raw):
        return True
    return _query_reflected_in_url(raw, task)


def _communication_region_evidence(raw: dict[str, Any]) -> bool:
    """`D-R0-67-2` Communication-like Region — 게시판류 structured data,
    또는 compose textarea 존재, 또는 (커뮤니티 어휘 AND list-container 카드)."""
    if _COMMUNICATION_STRUCTURED_TYPES & _structured_data_types(raw):
        return True
    fam = raw.get("family_signals", {})
    if fam.get("compose_textarea_present"):
        return True
    return bool(fam.get("community_vocabulary_present")) and _repeated_card_list_present(raw)


def _communication_endpoint_evidence(raw: dict[str, Any]) -> bool:
    """`D-R0-67-2` Communication-like Endpoint — "post/thread open" 근사(structured data
    또는 article/video 폴백) 또는 "compose area entry"(textarea 존재, Branch M 원문
    그대로)."""
    if _COMMUNICATION_STRUCTURED_TYPES & _structured_data_types(raw):
        return True
    fam = raw.get("family_signals", {})
    if fam.get("compose_textarea_present"):
        return True
    return _content_endpoint_real(raw)


def _content_region_evidence(raw: dict[str, Any]) -> bool:
    """`D-R0-67-2` Content-like Region — Article 계열 structured data 우선. 없으면
    "순수 list"로 떨어지는 residual 자리다 — Item/Place/Communication 이 각자의 전용
    신호로 못 채간 카드/링크 목록을 Content 가 받는다. 이렇게 해야 "공유 카드 신호 하나로
    4개 archetype 이 동시 evidenced"(C 진단, 36/56)되던 구조가 깨진다 — 나머지 셋은 이제
    자기 신호가 있어야 하고, Content 만 bare list 로 충분하다.
    """
    if _CONTENT_STRUCTURED_TYPES & _structured_data_types(raw):
        return True
    return _repeated_card_list_present(raw)


def _real_region_by_signal_type(raw: dict[str, Any], task: TaskDefinition) -> bool:
    """`D-R0-16` — `task.region_signal_type` 이 실제로 어떤 신호 계열을 쓸지 결정한다.
    이전에는 이 필드가 `mapping_frozen_allowed()`(테스트 전용) 밖에서 읽히지 않았다.
    """
    st = task.region_signal_type
    archetype = task.archetype
    if st is RegionSignalType.FORM_STRUCTURE:
        # 검색 입력 존재는 QUERY/PLACE_LOOKUP 에서만 evidence 다 — 다른 archetype 이
        # FORM_STRUCTURE 를 요청한다고 해서 "페이지 어딘가의 검색창"이 그 archetype 의
        # 증거가 되지는 않는다(resolver 의 Stage 4 다중후보 판정에서 실제로 이 구분이
        # 없으면 검색창 하나 때문에 모든 archetype 이 동시에 evidenced 로 잡힌다).
        if archetype in (InteractionArchetype.QUERY, InteractionArchetype.PLACE_LOOKUP):
            return _search_control_ready(raw)
        return False
    if st is RegionSignalType.MEDIA_STATE:
        return bool(raw.get("endpoint_signals", {}).get("video_playing"))
    if st is RegionSignalType.DOM_AX_ROLE:
        if archetype is InteractionArchetype.UTILITY_ENTRY:
            return _utility_tool_surface_present(raw)
        if archetype is InteractionArchetype.QUERY:
            return _search_control_ready(raw)
        if archetype is InteractionArchetype.ITEM_DETAIL:
            return _item_region_evidence(raw)
        if archetype is InteractionArchetype.PLACE_LOOKUP:
            return _place_region_evidence(raw) or _search_control_ready(raw)
        if archetype is InteractionArchetype.COMMUNICATION_ENTRY:
            return _communication_region_evidence(raw)
        if archetype is InteractionArchetype.CONTENT_OPEN:
            return _content_region_evidence(raw)
        # FINANCIAL_ACTION_ENTRY — `D-R0-67-2` 표에 4-family 에 없다. 공유 list 신호로도
        # 대체하지 않는다(문서화된 gap, 최종 보고 참조) — gate 경로(로그인/본인인증)가 이
        # archetype 의 주 실신호다.
        return False
    # URL_PATTERN(region 전용 신호 미정의 — 문서화된 gap) · GATE_SIGNAL(gate 는 endpoint 전용
    # 축이다) · CODEBOOK_PENDING(정의 없음) — 전부 region 을 만들어내지 않는다.
    return False


def _real_endpoint_by_signal_type(raw: dict[str, Any], task: TaskDefinition) -> bool:
    """`D-R0-16` — endpoint 판정도 동일하게 `task.endpoint_signal_type` 을 소비한다."""
    st = task.endpoint_signal_type
    archetype = task.archetype
    if st in (RegionSignalType.FORM_STRUCTURE, RegionSignalType.URL_PATTERN):
        if archetype is InteractionArchetype.PLACE_LOOKUP:
            return _place_endpoint_evidence(raw, task)
        return _query_reflected_in_url(raw, task)
    if st is RegionSignalType.MEDIA_STATE:
        return bool(raw.get("endpoint_signals", {}).get("video_playing"))
    if st is RegionSignalType.DOM_AX_ROLE:
        if archetype is InteractionArchetype.QUERY:
            return _query_reflected_in_url(raw, task)
        if archetype is InteractionArchetype.PLACE_LOOKUP:
            return _place_endpoint_evidence(raw, task)
        if archetype is InteractionArchetype.CONTENT_OPEN:
            return _content_endpoint_real(raw)
        if archetype is InteractionArchetype.COMMUNICATION_ENTRY:
            return _communication_endpoint_evidence(raw)
        if archetype is InteractionArchetype.ITEM_DETAIL:
            return _item_endpoint_evidence(raw)
        if archetype is InteractionArchetype.UTILITY_ENTRY:
            return _utility_tool_surface_present(raw)
        return False
    # GATE_SIGNAL — endpoint 는 Scout 의 별도 gate 경로(`obs.gate_present` → `detect_gate`)가
    # 처리한다. 여기서 True 를 내면 gate 판별을 우회하게 되므로 항상 False 다.
    # CODEBOOK_PENDING — 정의가 없다. endpoint 를 만들어내지 않는다(force-map 금지).
    return False


#: `TaskEntry.archetype` → 이 archetype 의 판정에 관련된 raw feature 키(truncation 추적 대상).
_TRUNCATION_RELEVANT_KEYS: dict[InteractionArchetype, tuple[str, ...]] = {
    InteractionArchetype.ITEM_DETAIL: ("primary_action_candidates", "accessible_name_sources"),
    InteractionArchetype.CONTENT_OPEN: ("primary_action_candidates",),
    InteractionArchetype.COMMUNICATION_ENTRY: ("primary_action_candidates",),
    InteractionArchetype.PLACE_LOOKUP: ("primary_action_candidates",),
    InteractionArchetype.FINANCIAL_ACTION_ENTRY: ("primary_action_candidates",),
    InteractionArchetype.UTILITY_ENTRY: ("primary_action_candidates",),
    InteractionArchetype.QUERY: (),
}


def observation_truncation_caveats(raw: dict[str, Any], task: TaskDefinition) -> list[str]:
    """이 archetype 의 판정에 쓴 raw feature 가 실제로 절단됐는지 `probe_truncation`
    (`l0_probe.js` W2 신규)에서 확인한다.

    B 의 n=58 전수 재집계(`T-B-FINDING-002`): `primary_action_candidates` 7/58,
    `accessible_name_sources` 13/58 이 cap 에 도달했고 대형 커머스/포털에 편중됐다
    — ITEM_DETAIL 이 동결 59건 중 최다(26건) 집단이라 위음성 위험이 특히 크다.
    cap 은 여기서 올리지 않는다(A 결정 사항, 재수집 필요). 대신 "신호 없음"을 "확인된
    부재"로 단정하지 않도록 이 caveat 을 `TaskEntry.notes` 에 남긴다.
    """
    trunc = raw.get("probe_truncation", {}) or {}
    hit: list[str] = []
    for key in _TRUNCATION_RELEVANT_KEYS.get(task.archetype, ()):
        info = trunc.get(key) or {}
        if info.get("truncated"):
            hit.append(f"{key}(cap={info.get('cap')}, matched={info.get('matched')})")
    if not hit:
        return []
    return [
        "OBSERVATION_TRUNCATED: "
        + "; ".join(hit)
        + " — 신호 미검출을 확인된 부재로 단정하지 않는다 "
        "(T-B-FINDING-002, cap 상향은 A 결정 사항이며 이 lane 이 임의로 올리지 않았다)"
    ]


# ── marker 경로(legacy) — FIXTURE 전용, D-R0-42 ─────────────────────────────
def _marker_region_match(raw: dict[str, Any], task: TaskDefinition) -> bool:
    """`[data-region]` synthetic marker. **FIXTURE 실행에서만** 참여한다.

    REAL_TARGET 에서는 이 함수 자체가 호출되지 않는다(아래 `detect_area_signal` 참조) —
    `l0_probe.js` 도 그 모드에서 이 marker 를 절대 읽지 않으므로(D-R0-42), `raw` 에 이
    필드가 들어 있더라도(예: 방어적 이중화가 깨진 가상의 상황) 이 함수는 FIXTURE 경로
    바깥에서 절대 소비되지 않는다.
    """
    signals = raw.get("region_signals", {})
    if task.region_definition is None:
        return False
    return any(
        s.get("region") == task.region_definition and s.get("present") and s.get("visible")
        for s in signals.get("declared_regions", [])
    )


def _marker_endpoint_match(raw: dict[str, Any], task: TaskDefinition) -> bool:
    """`[data-endpoint]` / `data-endpoint-reached` synthetic marker. FIXTURE 전용(D-R0-42)."""
    if task.endpoint_definition is None:
        return False
    signals = raw.get("endpoint_signals", {})
    if signals.get("body_endpoint_reached") == task.endpoint_definition:
        return True
    return any(
        e.get("endpoint") == task.endpoint_definition and e.get("visible")
        for e in signals.get("declared_endpoints", [])
    )


# ── 신호 판정 (결정적 1단계, `A1 §1.6`) ──────────────────────────────────────
def detect_area_signal(
    raw: dict[str, Any],
    task: TaskDefinition,
    execution_mode: ExecutionMode = ExecutionMode.FIXTURE,
) -> bool:
    """`A1 §1.1` — PRESENT ∧ HITTABLE ∧ NO_FURTHER_ACTIVATION.

    scroll 만으로 도달 가능하면 NO_FURTHER_ACTIVATION 을 만족한다 (`02 §9` 가 scroll 을
    activation 에서 제외하므로). 그래서 viewport 밖이어도 hittable 이면 성립으로 본다.

    `D-R0-14`/`D-R0-16` — 실 DOM/AX 신호(`_real_region_by_signal_type`)가 1순위다.
    `D-R0-42` — `[data-region]` marker 경로는 `execution_mode is REAL_TARGET` 이면
    **절대 평가되지 않는다**(단락 평가로 호출 자체가 생략된다). FIXTURE/SHADOW_DRY_RUN
    에서만 legacy fallback 으로 OR 결합한다 — 기존 marker 기반 fixture 회귀를 깨지 않는다.
    """
    if _real_region_by_signal_type(raw, task):
        return True
    if execution_mode is ExecutionMode.REAL_TARGET:
        return False
    return _marker_region_match(raw, task)


def detect_endpoint_signal(
    raw: dict[str, Any],
    task: TaskDefinition,
    execution_mode: ExecutionMode = ExecutionMode.FIXTURE,
) -> bool:
    """`02 §7` 의 endpoint. 이 lane 은 **새 endpoint 를 만들지 않는다** (`A1 §1.1`).

    `detect_area_signal` 과 같은 게이팅 규약을 따른다 — 자세한 설명은 그쪽 docstring.
    """
    if _real_endpoint_by_signal_type(raw, task):
        return True
    if execution_mode is ExecutionMode.REAL_TARGET:
        return False
    return _marker_endpoint_match(raw, task)


#: `D-R0-59-1` — gate 성립의 **필요조건**. 구조 신호(브라우저가 DOM 에서 직접 알려주는
#: 값)만 센다. `GateSignals.text`(어휘 매칭)는 여기 없다 — 어휘 단독으로는 gate 가 아니다.
#:
#: `captcha_iframe_count`(존재 카운트)는 **일부러 뺐다** — `C-BLOCKER-221347`(P1) 시정.
#: 숨겨진/비활성 iframe 하나만으로 이 게이트를 True 로 만들면 `obs.gate_present` 가
#: 발화해 Scout 가 그 state 를 gate 로 취급한다 — `D-R0-05`("숨김/비활성 script 존재
#: → terminal 아님")는 단지 "CAPTCHA 종류로 승격하지 않는다"가 아니라 **경로 진행을
#: 막는 상태로도 취급하지 않는다**는 뜻이다. 대신 `captcha_challenge_active`(visible/
#: active challenge 가 실제로 관측됨)를 쓴다 — 이건 Scout 종료를 유발해야 맞는 신호다.
def _gate_structural_signal_present(signals: GateSignals) -> bool:
    return any(
        (
            signals.password_input_count,
            signals.username_autocomplete_count,
            signals.tel_autocomplete_count,
            signals.identity_number_input_count,
            signals.otp_input_count,
            signals.carrier_option_count,
            signals.simple_auth_provider_count,
            signals.captcha_challenge_active,
            signals.payment_input_count,
        )
    )


def gate_observed(raw: dict[str, Any]) -> bool:
    """gate 로 볼 신호가 **하나라도** 관측됐는가 — 종류와 무관하다.

    `A2 §1.5.1a` 규칙 E-9: `auth_gate_detected` 는 gate 종류를 가리지 않는다.
    유병률(규칙 E-8)은 종류를 합쳐 세고, 종류 구분은 **endpoint 판정에서만** 쓰인다.

    `D-R0-59-1`(`T-B-BLK-003` P1 결함 시정, A 결정) — **구조 신호 없이 어휘만으로는
    gate 가 성립하지 않는다.** 이전 구현은 `decision.login_basis`/`identity_basis` 가
    비어있지 않기만 하면 True 를 냈다. 그런데 그 basis 는 어휘 항목(`*_vocabulary`)
    하나만으로도 채워질 수 있다 — `google.com/chrome` 이 "비밀번호"(크롬 기능 설명 텍스트)
    로, `band.us/about`/`m.naver.com`/`m.daum.net` 이 같은 방식으로 오탐됐다(B 의 n=58
    재집계: 어휘 매칭 28/58, `password_input_count>0` 4/58, **어휘만 있고 구조 신호 없음
    24/58**). `D-R0-03`("login control 존재는 raw feature/candidate annotation, terminal
    아님")과 `D-R0-04`("chosen path 가 실제로 도달했을 때만 gate observation")를 코드
    수준에서 강제한다.

    어휘 매칭 자체를 버리지 않는다 — `classify_gate_kind` 는 여전히 어휘를 판별 근거의
    일부로 쓴다(예: `auth_ambiguous_gate.html` 처럼 구조 신호가 실제로 있는 화면에서
    RESOLVED/UNDETERMINED 를 가르는 데). 다만 그 어휘가 **유일한** 근거일 때는(구조 신호가
    전혀 없을 때) gate 성립·terminal 판정에 쓰지 않는다 — annotation 으로만 남긴다.
    """
    signals = GateSignals.from_raw(raw)
    if not _gate_structural_signal_present(signals):
        return False
    decision = classify_gate_kind(signals)
    if decision.gate_kind is not None:
        return True
    return bool(decision.login_basis or decision.identity_basis)


def detect_gate(raw: dict[str, Any]) -> GateKindDecision:
    """관측된 gate 의 **종류**를 판별한다 (Q-9).

    `A2 §1.5.1a`: 로그인 gate 와 본인인증 gate 를 무엇으로 가르는지는 P-A endpoint codebook 이
    동결하며 **수집기의 재량이 아니다.** 이 lane 은 그 codebook 이 들어올 자리를 만들고,
    fixture 안에서 판별 절차·abstain 경로·오판 검출을 검증한다.

    fixture 의 `data-gate-kind` 는 **테스트의 기대값**이며 판별 입력이 아니다 —
    판별기가 그것을 읽으면 조작화가 아니라 정답 열람이 된다.
    """
    return classify_gate_kind(GateSignals.from_raw(raw))


def _gate_basis_is_vocabulary_only(decision: GateKindDecision) -> bool:
    """`T-B-BLK-003`(P1, A 결정 대기) 대응 — **`gate_observed()` 자체는 바꾸지 않는다.**

    B 가 발견한 결함: `gate_signals.visible_text`(랜딩 본문 전체)에 "로그인"/"비밀번호" 같은
    어휘가 하나만 있어도 `gate_observed()`가 activation 0회에서 `True` 를 낸다
    (`google.com/chrome`이 "비밀번호"로 오탐된 사례 등). 이 함수는 그 결함을 고치지 않고
    — 조작화 변경은 A 결정 사항이다 — 대신 **gate→endpoint 승격의 근거가 어휘뿐인지
    구조 신호(password_input/otp/identity_number/carrier_option/...)를 포함하는지**를
    구분해 `TaskEntry.notes` 에 남긴다. `gate_classifier._login_basis`/`_identity_basis`
    는 구조 신호 항목에 `이름×개수`를, 어휘 항목에 `_vocabulary` 접미사를 쓴다.
    """
    basis = list(decision.login_basis) + list(decision.identity_basis)
    if not basis:
        return False
    return all(item.endswith("_vocabulary") for item in basis)


# ── RF-DT Stage 4 — multi-candidate resolver (`01 §6` · D-R0-10~13) ────────────
class MappingOutcome:
    """`01 §9` DT leaf 의 두 결과. **문서에 정의된 두 값 밖으로 나가지 않는다.**

    `EXCLUDED`(§9 세 번째 leaf 종류)는 이 lane 의 자원이 아니다 — "research-scope exclusion
    reason이 evidence로 확인된 경우에만" 이며, 그 판단은 W2 detector 가 아니라 P-A 코드북/A 의
    권한이다. 이 lane 은 MAPPED 와 AMBIGUOUS_UNRESOLVED 만 낸다.
    """

    MAPPED = "MAPPED"
    AMBIGUOUS_UNRESOLVED = "AMBIGUOUS_UNRESOLVED"


#: `resolve_representative_function` 이 후보를 검증할 때 시도하는 signal family 순서.
#: `01 §6` evidence precedence 의 "DOM/AX/form state change" 층(tier 3) **안에서**, 더
#: 결정적인 신호를 먼저 본다 — FORM_STRUCTURE(검색창처럼 조작 가능한 구조)가
#: DOM_AX_ROLE(카드/리스트 존재)보다 강한 신호이기 때문이다. URL_PATTERN 은 이 시점
#: (활성화 전 랜딩)엔 아직 반영될 게 없어(질의를 제출하지 않았다) 사실상 발화하지 않지만,
#: 완전성을 위해 순서에는 둔다.
_RESOLVER_SIGNAL_ORDER: tuple[RegionSignalType, ...] = (
    RegionSignalType.FORM_STRUCTURE,
    RegionSignalType.DOM_AX_ROLE,
    RegionSignalType.URL_PATTERN,
)

#: `RegionSignalType.DOM_AX_ROLE` 로 evidenced 된 archetype 은 (QUERY 제외) 전부
#: `_repeated_card_list_present`(list-container 소속 링크) 를 근거로 쓴다 — tier 2 에서
#: "이 evidence 가 top-ranked primary surface 의 list 소속 여부와 부합하는가"를 물을 때
#: 이 집합을 "list 계열"로 취급한다.
_LIST_BASED_ARCHETYPES: frozenset[InteractionArchetype] = frozenset(
    {
        InteractionArchetype.CONTENT_OPEN,
        InteractionArchetype.ITEM_DETAIL,
        InteractionArchetype.PLACE_LOOKUP,
        InteractionArchetype.COMMUNICATION_ENTRY,
        InteractionArchetype.FINANCIAL_ACTION_ENTRY,
    }
)
#: `RegionSignalType.FORM_STRUCTURE` 로 evidenced 된 archetype — "검색 계열".
_SEARCH_BASED_ARCHETYPES: frozenset[InteractionArchetype] = frozenset(
    {InteractionArchetype.QUERY, InteractionArchetype.PLACE_LOOKUP}
)


def _top_ranked_primary_candidate(raw: dict[str, Any]) -> dict[str, Any] | None:
    """`01 §6` Stage 4 precedence #2 — "public page primary interaction surface".

    `min4_sort_key`(`A1 §2.6` 규칙 MIN-4, `l0_collector`·`Scout._activation_candidates`
    와 **같은 전순서**)로 정한 1위 candidate. Scout 가 실제로 밟을 후보와 같은 순서를 써야
    resolver 의 "대표 표면"과 실제 activation 경로가 다른 이야기를 하지 않는다.
    """
    cands = [
        c
        for c in raw.get("primary_action_candidates", [])
        if c.get("hittable") and c.get("selector")
    ]
    if not cands:
        return None
    return sorted(cands, key=min4_sort_key)[0]


def _tier2_primary_surface_favors(raw: dict[str, Any]) -> str | None:
    """1위 표면이 "list 계열"인지 "검색 계열"인지 판정한다. 어느 쪽도 아니면 `None`.

    tier 2 는 오직 **list 계열 vs 검색 계열**의 경합만 가른다 — 두 list 계열 후보끼리의
    경합(예: 서로 다른 list 성격을 가진 두 archetype)은 이 신호로 구분되지 않는다
    (그 페이지의 유일한 list 표면이 어느 archetype 의 것인지는 이 tier 로 알 수 없다).
    그런 경우는 force-map 하지 않고 tier 3 결과 그대로 `AMBIGUOUS_UNRESOLVED` 로 남는다.
    """
    top = _top_ranked_primary_candidate(raw)
    if top is None:
        return None
    return "list" if top.get("in_list_container") else "search"


@dataclass(frozen=True)
class RepresentativeFunctionMapping:
    """`01 §9` DT leaf output 의 부분집합 — W2 detector 가 낼 수 있는 필드만 채운다.

    `region_definition`/`endpoint_definition`(서비스별 문자열)은 P-A codebook 의 권한이라
    (`TaskDefinition` docstring 참조) 여기서 만들지 않는다 — `region_signal_type` 까지만
    이 lane 의 산출물이다. `decision_trace`/`forbidden_continuation`/`target_id` 도 마찬가지로
    상류(A/P-A) 조립을 기다린다. **force-map 은 절대 하지 않는다** — 유일 후보가 아니면
    `AMBIGUOUS_UNRESOLVED` 다.

    `evidence_slots_used` — LABEL_FROZEN 이후 Director 지적(F-A3.1, NH 쌍 라벨 불일치의
    원인 = 라벨러가 서로 다른 evidence slot 을 읽음)에 대한 대응. 이 resolver 는 **오직
    `probe.json`(`raw_features`, 렌더 후 상태)만 읽는다** — `dom.html`/`ax.json` 스냅샷은
    읽지 않는다. 그 사실을 판정마다 명시적으로 남긴다.

    `runner_up`/`why_not_runner_up`/`precedence_trace` — `D-R0-61`(PRECEDENCE_CONTESTED)
    대응: 경합이 있었다는 사실 자체를 조용히 삼키지 않는다. 두 후보가 tier 3 에서 동시에
    evidenced 됐는데 tier 2 가 하나를 가렸다면 **MAPPED 를 내면서도** 진 후보와 그 이유를
    남긴다. tier 2 도 못 가르면 `AMBIGUOUS_UNRESOLVED` 이면서 두 후보 모두를
    `candidate_archetypes` 에 남긴다(둘 다 강하면 force-map 하지 않는다, `D-R0-12`).
    """

    outcome: str
    archetype: InteractionArchetype | None
    region_signal_type: RegionSignalType | None
    mapping_basis: str
    evidence_refs: tuple[str, ...]
    candidate_archetypes: tuple[InteractionArchetype, ...]
    evidence_slots_used: tuple[str, ...] = ("probe.json:raw_features",)
    unresolved_reason: str | None = None
    target_id: str = ""
    runner_up: InteractionArchetype | None = None
    why_not_runner_up: str | None = None
    precedence_trace: tuple[str, ...] = ()

    def as_dict(self) -> dict[str, Any]:
        return {
            "outcome": self.outcome,
            "archetype": self.archetype.value if self.archetype else None,
            "region_signal_type": self.region_signal_type.value
            if self.region_signal_type
            else None,
            "mapping_basis": self.mapping_basis,
            "evidence_refs": list(self.evidence_refs),
            "candidate_archetypes": [a.value for a in self.candidate_archetypes],
            "evidence_slots_used": list(self.evidence_slots_used),
            "unresolved_reason": self.unresolved_reason,
            "target_id": self.target_id,
            "runner_up": self.runner_up.value if self.runner_up else None,
            "why_not_runner_up": self.why_not_runner_up,
            "precedence_trace": list(self.precedence_trace),
        }


def resolve_representative_function(
    raw: dict[str, Any],
    candidates: list[InteractionArchetype],
    *,
    target_id: str = "",
    query_text: str = "고령자 접근성",
) -> RepresentativeFunctionMapping:
    """`01 §6` Stage 4 — evidence precedence 를 **명시적으로** 적용해 유일 candidate 를 고른다.

    `D-R0-61`(PRECEDENCE_CONTESTED) — 암묵적 순서(먼저 매칭되는 branch 가 이김) 대신
    RF-DT §6 원문 5단계를 코드로 구현한다. 이 lane 이 실제로 관측할 수 있는 신호는
    2·3단만이다(1단 "actual user-operation structure"는 Scout 가 activation 을 밟은 뒤에만
    존재하므로 Stage 4 시점엔 아직 없다 — landing 만 보고 판단하는 것이 이 함수의 전제다.
    4·5단 "business prior"/"service name token"은 Stage 1 의 자원이며 이 lane 이 만들지
    않는다, `01 §3`):

    ```
    tier 2   public page primary interaction surface   — MIN-4 1위 candidate 의 소속
    tier 3   DOM/AX/form state change evidence          — signal family 별 존재 판정
    ```

    절차:

    1. 각 candidate 를 tier 3 신호(`_RESOLVER_SIGNAL_ORDER`)로 검증해 evidenced 집합을 만든다.
    2. evidenced 가 0 이면 `AMBIGUOUS_UNRESOLVED`(evidence 없음).
    3. evidenced 가 1 이면 `MAPPED`(경합 없음).
    4. evidenced 가 2 이상이면 tier 2(`_tier2_primary_surface_favors`)로 가른다 —
       "list 계열" vs "검색 계열" 경합만 가를 수 있다. 갈리면 `MAPPED` + `runner_up` 기록.
       못 가르면(둘 다 같은 계열이거나 표면이 없으면) **force-map 하지 않고**
       `AMBIGUOUS_UNRESOLVED` — 진 후보가 없으니 경합한 candidate 전부를 기록한다.

    `D-R0-13`: LABEL_FROZEN 이후에도 COMMUNICATION_ENTRY(calibration 0건)·UTILITY_ENTRY
    (1건)는 semantic threshold 를 세울 근거가 없다 — 이 함수는 NLP fallback 을 전혀 쓰지
    않으므로 그 archetype 이 경합에 낀 ambiguity 도 여기서 force-resolve 하지 않는다.

    `raw` 는 후보들이 공유하는 **하나의 관측**(랜딩 state)이다. archetype 별 실제
    `TaskDefinition` 을 만들지 않고, 각 후보를 evidence 검증용 probe `TaskDefinition` 으로
    감싸 `_real_region_by_signal_type`(runtime detector 와 **같은** 원자 함수)를 재사용한다.
    """
    if not candidates:
        return RepresentativeFunctionMapping(
            MappingOutcome.AMBIGUOUS_UNRESOLVED,
            None,
            None,
            "",
            (),
            (),
            unresolved_reason="후보가 없다 — Stage 1 candidate generation 결과가 비어 있다",
            target_id=target_id,
            precedence_trace=("tier1: N/A(pre-Scout)", "tier2: N/A(0 candidates)"),
        )

    evidenced: list[tuple[InteractionArchetype, RegionSignalType, str]] = []
    for archetype in candidates:
        for signal_type in _RESOLVER_SIGNAL_ORDER:
            probe_task = TaskDefinition(
                task_id=f"resolver-probe:{archetype.value}",
                archetype=archetype,
                region_definition=None,
                endpoint_definition=None,
                region_signal_type=signal_type,
                endpoint_signal_type=signal_type,
                query_text=query_text,
            )
            if _real_region_by_signal_type(raw, probe_task):
                evidenced.append((archetype, signal_type, f"{signal_type.value} evidence observed"))
                break

    trace = ["tier1: N/A(pre-Scout, actual user-operation structure 없음)"]

    if not evidenced:
        trace.append("tier3: evidence 없음")
        return RepresentativeFunctionMapping(
            MappingOutcome.AMBIGUOUS_UNRESOLVED,
            None,
            None,
            "",
            (),
            tuple(candidates),
            unresolved_reason=(
                "evidence 없음 — 관측된 DOM/AX/Form/URL 구조가 어떤 candidate 도 뒷받침하지 않는다"
            ),
            target_id=target_id,
            precedence_trace=tuple(trace),
        )

    distinct_archetypes = {a for a, _, _ in evidenced}
    trace.append(f"tier3: evidenced={sorted(a.value for a in distinct_archetypes)}")

    if len(distinct_archetypes) == 1:
        archetype, signal_type, basis = evidenced[0]
        trace.append("tier3 이 유일 candidate 를 냈다 — tier2 불필요")
        return RepresentativeFunctionMapping(
            MappingOutcome.MAPPED,
            archetype,
            signal_type,
            f"observed interaction structure ({signal_type.value}) — {basis}",
            (basis,),
            (archetype,),
            target_id=target_id,
            precedence_trace=tuple(trace),
        )

    # tier 3 에서 2개 이상 경합 — `D-R0-61`: 조용히 하나만 내보내지 않는다. tier 2 로 시도한다.
    tier2_favor = _tier2_primary_surface_favors(raw)
    trace.append(f"tier2: primary surface favors={tier2_favor!r}")
    winners_by_tier2: list[InteractionArchetype] = []
    if tier2_favor == "list":
        winners_by_tier2 = [a for a, _, _ in evidenced if a in _LIST_BASED_ARCHETYPES]
    elif tier2_favor == "search":
        winners_by_tier2 = [a for a, _, _ in evidenced if a in _SEARCH_BASED_ARCHETYPES]

    if len(winners_by_tier2) == 1:
        winner = winners_by_tier2[0]
        losers = sorted((a for a in distinct_archetypes if a is not winner), key=lambda a: a.value)
        winner_entry = next(e for e in evidenced if e[0] is winner)
        _, signal_type, basis = winner_entry
        trace.append(f"tier2 이 {winner.value} 를 승격했다 — 진 후보: {[a.value for a in losers]}")
        return RepresentativeFunctionMapping(
            MappingOutcome.MAPPED,
            winner,
            signal_type,
            f"tier2 primary-surface precedence ({tier2_favor}) over tier3-evidenced 경합",
            (basis,),
            (winner,),
            target_id=target_id,
            runner_up=losers[0] if losers else None,
            why_not_runner_up=(
                f"tier2(public page primary interaction surface)가 {tier2_favor} 계열을 가리켰다 — "
                f"{[a.value for a in losers]} 도 tier3 evidence 는 있었지만 대표 표면이 아니었다"
            ),
            precedence_trace=tuple(trace),
        )

    # tier 2 로도 못 가른다 — force-map 하지 않는다(D-R0-12). 경합한 candidate 전부를 남긴다.
    trace.append("tier2 로도 못 가른다 — force-map 하지 않는다")
    return RepresentativeFunctionMapping(
        MappingOutcome.AMBIGUOUS_UNRESOLVED,
        None,
        None,
        "",
        tuple(basis for _, _, basis in evidenced),
        tuple(candidates),
        unresolved_reason=(
            "강한 candidate 2개 이상, tier2(primary surface)로도 가르지 못했다 — "
            f"경합: {sorted(a.value for a in distinct_archetypes)}. force-map 하지 않는다."
        ),
        target_id=target_id,
        precedence_trace=tuple(trace),
    )


@dataclass
class _StateObservation:
    state_id: str
    url: str
    raw: dict[str, Any]
    area: bool
    endpoint: bool
    gate: GateKindDecision
    gate_present: bool
    dom: str


class Scout:
    """`02 §7` L1 Scout. **fixture 만 연다** — 모든 항해가 firewall 을 거친다."""

    def __init__(
        self,
        *,
        fixture_root: Path | None = None,
        budget: ScoutBudget | None = None,
        execution_mode: ExecutionMode = ExecutionMode.FIXTURE,
        execution_scope: object | None = None,
        run: EvidenceRun | None = None,
    ) -> None:
        self.fixture_root = Path(fixture_root).resolve() if fixture_root is not None else None
        self.budget = budget or ScoutBudget()
        self.execution_mode = execution_mode
        #: `REAL_TARGET` 에서만 의미가 있다 — 어느 승인 범위로 여는가.
        self.execution_scope = execution_scope
        self.run = run

    def _provenance_block(self) -> dict[str, Any]:
        """이 Scout 이 낸 산출물의 provenance. 모드에 따라 **다른 계약**을 쓴다.

        실제 수집(`REAL_TARGET` + scope)에서 `ShadowProvenance` 를 붙이면
        `real_target_measurement = false` 로 나가 하류가 fixture 산물로 오인한다.
        """
        if self.execution_mode is ExecutionMode.REAL_TARGET:
            from .provenance import RealTargetProvenance

            return RealTargetProvenance.for_scope(self.execution_scope).as_dict()
        return ShadowProvenance().as_dict()

    # ── 관측 ─────────────────────────────────────────────────────────────
    def _observe_after_clearing(
        self, page: Page, task: TaskDefinition
    ) -> tuple[_StateObservation, int]:
        """state 를 관측하고, 진행을 막는 popup 이 있으면 닫은 뒤 **다시** 관측한다.

        강제 dismissal 은 activation 이 아니라 **경로의 전제조건**이다 (`02 §9`).
        그래서 후보 열거 전에 끝내고 횟수만 `forced_dismissal_count` 로 남긴다.
        """
        obs = self._observe(page, task)
        closed = self._dismiss_blockers(page, obs.raw)
        if closed:
            obs = self._observe(page, task)
        return obs, closed

    def _observe(self, page: Page, task: TaskDefinition) -> _StateObservation:
        page.wait_for_timeout(SETTLE_MS)
        # `execution_mode.value` 를 probe 에 넘긴다 — REAL_TARGET 이면 `l0_probe.js` 가
        # marker 3종(`[data-region]`/`[data-endpoint]`/`data-endpoint-reached`) querySelectorAll
        # /getAttribute 호출 자체를 건너뛴다(D-R0-42, Director 지시). `L0Collector` 는 이 인자
        # 없이 `PROBE_JS`를 호출하므로(그쪽은 W4 소유, 손대지 않는다) 그 경로의 동작은 그대로다.
        probe = page.evaluate(PROBE_JS, self.execution_mode.value)
        raw = probe["raw_features"]
        dom = page.content()
        return _StateObservation(
            state_id=state_key(page.url, dom),
            url=page.url,
            raw=raw,
            area=detect_area_signal(raw, task, self.execution_mode),
            endpoint=detect_endpoint_signal(raw, task, self.execution_mode),
            gate=detect_gate(raw),
            gate_present=gate_observed(raw),
            dom=dom,
        )

    @staticmethod
    def _activation_candidates(raw: dict[str, Any], limit: int) -> list[dict[str, Any]]:
        """이 state 에서 시도할 activation 후보.

        **popup 의 닫기 control 은 후보가 아니다.** `02 §9` 가 popup dismiss 를 activation 에서
        제외했고, 그것을 후보로 두면 닫기가 depth 로 세어지는 것은 물론 `_dismiss_blockers` 와
        같은 요소를 두 번 누르게 되어 경로가 스스로 무너진다.

        정렬은 `l0_collector.min4_sort_key`(`A1 §2.6` 규칙 MIN-4)와 **같은 함수**를 쓴다 —
        `rank_primary_action_candidates`가 매기는 `SELECTED`/`rank`와 이 열거 순서가 갈리면
        저장된 대표 control과 Scout가 실제로 밟는 경로가 서로 다른 이야기를 하게 된다.
        이 순서가 곧 `BRANCHING_LIMIT` 절단선(`limit`)이 무엇을 자르는지를 결정한다.
        """
        dismiss_selectors = {
            str(ctrl.get("selector"))
            for container in raw.get("dismiss_control_candidates", [])
            for ctrl in container.get("dismiss_control_candidates", [])
        }
        cands = [
            c
            for c in raw.get("primary_action_candidates", [])
            if c.get("hittable")
            and c.get("selector")
            and str(c.get("selector")) not in dismiss_selectors
        ]
        cands.sort(key=min4_sort_key)
        seen: set[str] = set()
        out: list[dict[str, Any]] = []
        for c in cands:
            sel = str(c["selector"])
            if sel in seen:
                continue
            seen.add(sel)
            out.append(c)
            if len(out) >= limit:
                break
        return out

    # ── 탐색 ─────────────────────────────────────────────────────────────
    def scout(
        self,
        *,
        web_target_id: str,
        entry_fixture: str | None = None,
        task: TaskDefinition,
        entry_real_url: str | None = None,
    ) -> tuple[TaskEntry, TaskManifest | None]:
        """bounded minimality search. 최소 activation 경로를 찾거나 예산에서 멈춘다.

        진입점은 둘 중 **정확히 하나**다:

        - `entry_fixture` — FIXTURE 모드. `fixture_root` 안의 로컬 파일.
        - `entry_real_url` — `REAL_TARGET` + 승인된 scope. 실제 서비스 진입 URL.

        둘 다 주거나 둘 다 안 주면 실패한다 — "어느 쪽인지 모르는 채로" 항해하지 않는다.
        어느 쪽이든 `assert_navigation_allowed` 를 거치므로, 모드와 진입점이 어긋나면
        firewall 이 막는다.
        """
        from playwright.sync_api import sync_playwright

        if (entry_fixture is None) == (entry_real_url is None):
            raise ValueError(
                "entry_fixture 와 entry_real_url 중 정확히 하나를 지정해야 한다 "
                f"(fixture={entry_fixture!r}, real={entry_real_url!r})"
            )
        if entry_real_url is not None:
            entry_url = assert_navigation_allowed(
                self.execution_mode,
                entry_real_url,
                scope=self.execution_scope,
                target_id=web_target_id,
            )
            entry_label = entry_real_url
        else:
            if self.fixture_root is None or entry_fixture is None:
                raise ValueError("entry_fixture 를 쓰려면 fixture_root 가 있어야 한다")
            entry_url = assert_navigation_allowed(
                self.execution_mode,
                f"file://{(self.fixture_root / entry_fixture).resolve()}",
                fixture_root=self.fixture_root,
            )
            entry_label = entry_fixture
        started = time.monotonic()
        collector = (
            L0Collector(
                self.run,
                fixture_root=self.fixture_root,
                execution_mode=self.execution_mode,
                execution_scope=self.execution_scope,
            )
            if self.run
            else None
        )

        best_path: list[dict[str, Any]] | None = None
        best_steps: list[TaskStep] = []
        episodes: list[TaskEpisode] = []
        forced_dismissals = 0  # 최소 경로 위에서 실제로 닫아야 했던 횟수만 남긴다
        budget_reason: str | None = None
        terminal: tuple[EndpointStatus, EndpointStatusDetail | None] | None = None
        area_index: int | None = None
        endpoint_index: int | None = None
        landing_gate_detected = 0
        notes: list[str] = []
        last_obs: _StateObservation | None = None
        # `D-R0-20` partial depth 보존 — endpoint/gate 를 예산 안에서 못 찾아도, 탐색한
        # 어느 경로에서 region 이 관측됐다면 그 지점을 기억해 둔다. 종료까지 endpoint 가
        # 안 나오면(terminal 이 끝내 None) 이 값으로 NED 를 채운다. IED/MPFED 는 여전히
        # NULL(m 을 모르므로) — `assign_depth_segments` 는 그 나머지 step 을 `UNASSIGNED`로
        # 라벨링한다(depth.py 결함 시정). 이전 구현은 endpoint/gate 를 찾은 경로에서만
        # area_index 를 채워서, 못 찾은 경우 region 이 실제로 관측됐어도 조용히 버려졌다
        # — area 신호가 전부 marker 뿐이던 때는 한 번도 발화하지 않았을 결함이다.
        partial_area_index: int | None = None
        partial_area_steps: list[TaskStep] = []

        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True)
            context = (
                collector._new_context(browser)
                if collector
                else browser.new_context(viewport={"width": 390, "height": 844})
            )
            page = context.new_page()
            try:
                queue: deque[list[dict[str, Any]]] = deque([[]])

                while queue:
                    if time.monotonic() - started > self.budget.max_scout_wall_clock_s:
                        budget_reason = "MAX_SCOUT_WALL_CLOCK_S"
                        break
                    prefix = queue.popleft()
                    if len(prefix) > self.budget.max_activations_per_task:
                        budget_reason = "MAX_ACTIVATIONS_PER_TASK"
                        continue

                    # 예산 중 state 재방문·연속 무변화는 **한 탐색 경로 안에서** 센다.
                    # BFS 는 경로마다 랜딩부터 다시 밟으므로, 전역으로 세면 재탐색 자체가
                    # 순환으로 오탐된다 — 예산이 대상의 성질이 아니라 탐색 전략을 재게 된다.
                    visits: dict[str, int] = {}
                    consecutive_no_change = 0

                    page.goto(entry_url, wait_until="load")
                    obs, path_dismissals = self._observe_after_clearing(page, task)
                    steps: list[TaskStep] = []
                    trail: list[dict[str, Any]] = []
                    replay_ok = True

                    # 랜딩 상태 자체의 신호 (k=0 / m=0 가능, `A1 §1.4`)
                    landing_area = obs.area
                    landing_endpoint = obs.endpoint
                    landing_gate = obs.gate if obs.gate_present else None
                    landing_gate_detected = max(landing_gate_detected, int(obs.gate_present))
                    previous_state = obs.state_id

                    for depth_i, action in enumerate(prefix, start=1):
                        if not self._activate(page, action, task, episodes, len(steps)):
                            replay_ok = False
                            break
                        obs, closed = self._observe_after_clearing(page, task)
                        path_dismissals += closed
                        visits[obs.state_id] = visits.get(obs.state_id, 0) + 1
                        if visits[obs.state_id] > self.budget.max_state_revisits:
                            budget_reason = "MAX_STATE_REVISITS"
                            replay_ok = False
                            break  # 이 가지만 쳐낸다. 다른 가지가 남아 있으면 계속 탐색한다
                        if obs.state_id == previous_state:
                            consecutive_no_change += 1
                            if consecutive_no_change >= self.budget.max_consecutive_no_state_change:
                                budget_reason = "MAX_CONSECUTIVE_NO_STATE_CHANGE"
                                replay_ok = False
                                break
                        else:
                            consecutive_no_change = 0
                        previous_state = obs.state_id

                        steps.append(
                            TaskStep(
                                step_index=depth_i,
                                state_id=obs.state_id,
                                url=obs.url,
                                clicked_selector=str(action["selector"]),
                                control_role=action.get("role") or action.get("tag"),
                                accessible_name=action.get("aria_label")
                                or action.get("visible_text"),
                                area_signal_detected=int(obs.area),
                                endpoint_signal_detected=int(obs.endpoint),
                                auth_gate_detected=int(obs.gate_present),
                                popup_present=int(bool(obs.raw.get("modal_overlay_candidates"))),
                            )
                        )
                        trail.append(
                            {
                                "step_index": depth_i,
                                "selector": str(action["selector"]),
                                # `A1 §2.6`/`§8` — Freeze 산출물은 그 관측 시점에 이 후보가
                                # 어떤 문서 순서였는지도 함께 담아야 "무엇이 최소였는가"를
                                # 재현 대조할 수 있다 (규칙 MIN-4 · MIN-8) `[V2-C012 반영]`.
                                "dom_order": action.get("dom_order"),
                                "expected_state_id": obs.state_id,
                                "expected_url_tail": obs.url.rsplit("/", 1)[-1],
                            }
                        )
                        if obs.endpoint or obs.gate_present:
                            break

                    if not replay_ok:
                        continue

                    # 종료조건 평가 — `02 §7` 즉시종료
                    area_here = _first_index(landing_area, steps, "area_signal_detected")
                    endpoint_here = _first_index(
                        landing_endpoint, steps, "endpoint_signal_detected"
                    )
                    gate_here = (obs.gate if obs.gate_present else None) if steps else landing_gate
                    last_obs = obs

                    # `D-R0-20` partial depth — endpoint/gate 가 이 prefix 에서 안 나와도
                    # region 이 관측됐다면 기록해 둔다. 탐색이 끝내 terminal 을 못 찾으면
                    # (전부 UNRESOLVED) 이 값이 최종 NED 가 된다. 마지막으로 관측된 경로를
                    # 쓴다 — BFS 가 계속 더 깊이 탐색하며 최신 관측을 갱신한다.
                    if area_here is not None:
                        partial_area_index = area_here
                        partial_area_steps = steps

                    if endpoint_here is not None:
                        terminal = (EndpointStatus.FUNCTION_ENDPOINT_REACHED, None)
                        area_index, endpoint_index = area_here, endpoint_here
                        best_path, best_steps = trail, steps
                        forced_dismissals = path_dismissals
                        break
                    if gate_here is not None:
                        status, detail = gate_outcome_from_decision(
                            task.archetype,
                            gate_here,
                            personal_data_required=bool(
                                obs.raw.get("gate_signals", {}).get("personal_data_keyword")
                            ),
                        )
                        notes.append(
                            f"gate 판별: {gate_here.status.value} "
                            f"{gate_here.gate_kind.value if gate_here.gate_kind else '-'} "
                            f"({gate_here.reason})"
                        )
                        if (
                            detail is EndpointStatusDetail.ENDPOINT_VIA_AUTH_GATE
                            and _gate_basis_is_vocabulary_only(gate_here)
                        ):
                            notes.append(
                                "GATE_BASIS_VOCABULARY_ONLY: 이 gate→endpoint 승격의 판별 근거가 "
                                "어휘 매칭뿐이다(구조 신호 없음) — T-B-BLK-003(P1, A 결정 대기) 영향권. "
                                "gate_observed() 의 어휘 단독 위양성이 확정되면 이 endpoint 판정도 "
                                "재검토 대상이다."
                            )
                        terminal = (status, detail)
                        area_index = area_here
                        endpoint_index = (
                            len(steps)
                            if status is EndpointStatus.FUNCTION_ENDPOINT_REACHED
                            else None
                        )
                        best_path, best_steps = trail, steps
                        forced_dismissals = path_dismissals
                        break

                    # 아직 종료하지 않았다 — 다음 depth 로 확장
                    if len(prefix) < self.budget.max_activations_per_task:
                        for cand in self._activation_candidates(
                            obs.raw, self.budget.branching_limit
                        ):
                            queue.append([*prefix, cand])
                    else:
                        budget_reason = "MAX_ACTIVATIONS_PER_TASK"

                    # scroll episode — 목록형 상태에서 사용자 스크롤을 1회 모사한다.
                    if obs.raw.get("viewport", {}).get("document_scroll_height", 0) > 844:
                        episodes.append(
                            TaskEpisode(
                                episode_index=len(episodes),
                                episode_kind=EpisodeKind.SCROLL.value,
                                target_selector="body",
                                state_id=obs.state_id,
                                started_after_step_index=len(steps),
                                ended_by=EpisodeEndedBy.IDLE.value,
                                input_mode=None,
                                scroll_distance_px=600.0,
                            )
                        )
                        page.evaluate("() => window.scrollBy(0, 600)")
                        page.wait_for_timeout(self.budget.scroll_idle_ms)
            except Exception as exc:
                notes.append(f"{type(exc).__name__}: {exc}")
                budget_reason = budget_reason or "SCOUT_ERROR"
            finally:
                context.close()
                browser.close()

        if terminal is None:
            status = EndpointStatus.UNRESOLVED
            detail = (
                EndpointStatusDetail.UNRESOLVED_DEPTH_BUDGET_EXCEEDED
                if budget_reason
                else EndpointStatusDetail.UNRESOLVED_NO_SIGNAL
            )
            # `D-R0-20` partial depth 보존 — endpoint/gate 를 못 찾았어도 region 이 어딘가에서
            # 관측됐다면 NED 는 버리지 않는다. `depth.compute_depth` 가 `area_step_index` 로
            # `AreaSignalStatus.OBSERVED`(NED 有 · IED/MPFED NULL) 를 낸다.
            if partial_area_index is not None:
                area_index = partial_area_index
                best_steps = partial_area_steps
                notes.append(
                    f"partial depth 보존: region 이 activation {partial_area_index} 에서 관측됐으나 "
                    "endpoint/gate 는 예산 안에서 관측되지 않았다 (D-R0-20)"
                )
        else:
            status, detail = terminal

        if last_obs is not None:
            notes.extend(observation_truncation_caveats(last_obs.raw, task))

        depth = compute_depth(
            archetype=task.archetype,
            area_step_index=area_index,
            endpoint_step_index=endpoint_index,
            endpoint_status=status,
            endpoint_status_detail=detail,
        )
        segments = assign_depth_segments(len(best_steps), depth)
        for step, seg in zip(best_steps, segments, strict=True):
            step.depth_segment = seg.value

        # 규칙 E-9 의 정본 원천은 `fact_task_step.auth_gate_detected` 지만, gate 가 **랜딩 자체**에
        # 있으면 activation 이 없어 step 행이 하나도 없다. 그 경우를 빼면 `00 §7` 이 요구한
        # auth gate 별도 기록이 0으로 과소집계된다 — 규칙 E-8 이 경고한 바로 그 형태다.
        # 그래서 s0 의 관측을 열의 맨 앞에 둔다. "endpoint 를 실현한 gate" 의 제외 규칙은
        # 마지막 원소에 적용되므로, 랜딩 gate 가 곧 endpoint 인 경우도 그대로 성립한다.
        gate_flags = [landing_gate_detected, *(s.auth_gate_detected for s in best_steps)]
        agbe = auth_gate_before_endpoint(
            auth_gate_detected_per_step=gate_flags,
            endpoint_status_detail=depth.endpoint_status_detail,
        )
        entry = TaskEntry(
            task_observation_id=f"{web_target_id}:{task.task_id}",
            task_id=task.task_id,
            archetype=task.archetype.value,
            endpoint_status=depth.endpoint_status.value,
            endpoint_status_detail=(
                depth.endpoint_status_detail.value if depth.endpoint_status_detail else None
            ),
            endpoint_reached=depth.endpoint_reached,
            area_signal_status=depth.area_signal_status.value,
            ned=depth.ned,
            ied=depth.ied,
            mpfed=depth.mpfed,
            auth_gate_before_endpoint=agbe,
            auth_gate_observed=auth_gate_observed(
                auth_gate_before_endpoint_value=agbe,
                endpoint_status_detail=depth.endpoint_status_detail,
            ),
            forced_dismissal_count=forced_dismissals,
            text_input_episode_count=sum(
                1 for e in episodes if e.episode_kind == EpisodeKind.TEXT_INPUT.value
            ),
            scroll_episode_count=sum(
                1 for e in episodes if e.episode_kind == EpisodeKind.SCROLL.value
            ),
            steps=best_steps,
            episodes=episodes,
            budget_reason=budget_reason,
            notes=notes,
        )

        manifest: TaskManifest | None = None
        if best_path is not None and depth.endpoint_reached:
            manifest = TaskManifest(
                task_id=task.task_id,
                archetype=task.archetype.value,
                web_target_id=web_target_id,
                entry_fixture=entry_label,
                frozen_at=utc_now_iso(),
                path=best_path,
                endpoint_status=depth.endpoint_status.value,
                endpoint_status_detail=(
                    depth.endpoint_status_detail.value if depth.endpoint_status_detail else None
                ),
                ned=depth.ned,
                ied=depth.ied,
                mpfed=depth.mpfed,
                provenance=self._provenance_block(),
            )
        return entry, manifest

    # ── 조작 ─────────────────────────────────────────────────────────────
    def _activate(
        self,
        page: Page,
        action: dict[str, Any],
        task: TaskDefinition,
        episodes: list[TaskEpisode],
        step_count: int,
    ) -> bool:
        """activation 1회. `02 §9` 가 activation 으로 인정하는 조작만 한다."""
        selector = str(action["selector"])
        try:
            # QUERY 는 제출 전에 입력이 필요하다. **문자 입력은 activation 이 아니다** —
            # episode 축으로만 센다 (`A1 §4.2` · `02 §9`).
            if task.archetype is InteractionArchetype.QUERY:
                boxes = page.query_selector_all("input[type=search],[role=searchbox]")
                if boxes:
                    boxes[0].fill(task.query_text)
                    episodes.append(
                        TaskEpisode(
                            episode_index=len(episodes),
                            episode_kind=EpisodeKind.TEXT_INPUT.value,
                            target_selector="input[type=search]",
                            state_id="pre-submit",
                            started_after_step_index=step_count,
                            ended_by=EpisodeEndedBy.SUBMIT.value,
                            input_mode=InputMode.PROGRAMMATIC.value,
                        )
                    )
            page.click(selector, timeout=3000)
            page.wait_for_timeout(SETTLE_MS)
            return True
        except Exception:
            return False

    def _dismiss_blockers(self, page: Page, raw: dict[str, Any]) -> int:
        """경로 진행을 위해 실제로 닫아야 했던 popup 수 — `02 §9` `forced_dismissal_count`.

        L0 의 dismiss 가능성 측정과 **합산하지 않는다** (`A2` 규칙 I-4).
        popup dismiss 는 activation 이 아니므로 step row 를 만들지 않는다.
        """
        closed = 0
        for container in raw.get("dismiss_control_candidates", []):
            for control in container.get("dismiss_control_candidates", []):
                if not control.get("hittable"):
                    continue
                try:
                    page.click(control["selector"], timeout=1000)
                    page.wait_for_timeout(SETTLE_MS)
                    closed += 1
                except Exception:
                    continue
                break
        return closed


def _first_index(landing_signal: bool, steps: list[TaskStep], attr: str) -> int | None:
    """신호가 최초로 성립한 state 의 index. 랜딩에서 성립했으면 `0`."""
    if landing_signal:
        return 0
    for step in steps:
        if getattr(step, attr):
            return step.step_index
    return None


class ReplayBroken(Exception):
    """`02 §8` — 동결된 경로의 결정적 replay 가 깨졌다."""


def replay(
    manifest: TaskManifest,
    *,
    fixture_root: Path,
    execution_mode: ExecutionMode = ExecutionMode.FIXTURE,
) -> dict[str, Any]:
    """동결된 task manifest 를 결정적으로 다시 실행한다.

    깨지면 **조용히 자유탐색으로 대체하지 않고** `UNRESOLVED_REPLAY_BROKEN` 을 돌려준다
    (`A2` 규칙 E-2). 그 값을 남기지 않고 재탐색한 결과를 기록하는 것이 결함이다.
    """
    from playwright.sync_api import sync_playwright

    root = Path(fixture_root).resolve()
    entry_url = assert_navigation_allowed(
        execution_mode, f"file://{(root / manifest.entry_fixture).resolve()}", fixture_root=root
    )
    observed: list[dict[str, Any]] = []
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        page = browser.new_context(viewport={"width": 390, "height": 844}).new_page()
        try:
            page.goto(entry_url, wait_until="load")
            page.wait_for_timeout(SETTLE_MS)
            for node in manifest.path:
                try:
                    page.click(str(node["selector"]), timeout=3000)
                except Exception as exc:
                    return {
                        "status": "UNRESOLVED",
                        "endpoint_status_detail": (
                            EndpointStatusDetail.UNRESOLVED_REPLAY_BROKEN.value
                        ),
                        "broken_at_step": node["step_index"],
                        "reason": f"{type(exc).__name__}: {exc}",
                        "observed": observed,
                    }
                page.wait_for_timeout(SETTLE_MS)
                actual = state_key(page.url, page.content())
                observed.append({"step_index": node["step_index"], "state_id": actual})
                if actual != node["expected_state_id"]:
                    return {
                        "status": "UNRESOLVED",
                        "endpoint_status_detail": (
                            EndpointStatusDetail.UNRESOLVED_REPLAY_BROKEN.value
                        ),
                        "broken_at_step": node["step_index"],
                        "reason": (
                            f"state 불일치: 기대 {node['expected_state_id']} / 실제 {actual}"
                        ),
                        "observed": observed,
                    }
        finally:
            browser.close()
    return {
        "status": manifest.endpoint_status,
        "endpoint_status_detail": manifest.endpoint_status_detail,
        "broken_at_step": None,
        "reason": None,
        "observed": observed,
        "path_sha256": manifest.path_sha256(),
    }


__all__ = [
    "AreaSignalStatus",
    "BudgetExhausted",
    "DepthResult",
    "MappingOutcome",
    "ReplayBroken",
    "RepresentativeFunctionMapping",
    "Scout",
    "ScoutBudget",
    "TaskDefinition",
    "TaskEntry",
    "TaskEpisode",
    "TaskManifest",
    "TaskStep",
    "detect_area_signal",
    "detect_endpoint_signal",
    "detect_gate",
    "gate_observed",
    "observation_truncation_caveats",
    "replay",
    "resolve_representative_function",
    "state_key",
]
