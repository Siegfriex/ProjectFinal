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
import time
from collections import deque
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

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


# ── 신호 판정 (결정적 1단계, `A1 §1.6`) ──────────────────────────────────────
def detect_area_signal(raw: dict[str, Any], task: TaskDefinition) -> bool:
    """`A1 §1.1` — PRESENT ∧ HITTABLE ∧ NO_FURTHER_ACTIVATION.

    scroll 만으로 도달 가능하면 NO_FURTHER_ACTIVATION 을 만족한다 (`02 §9` 가 scroll 을
    activation 에서 제외하므로). 그래서 viewport 밖이어도 hittable 이면 성립으로 본다.
    """
    signals = raw.get("region_signals", {})
    if task.archetype is InteractionArchetype.QUERY:
        return any(
            s.get("visible") and s.get("in_form") and s.get("has_submit")
            for s in signals.get("search_inputs", [])
        )
    if task.region_definition is None:
        return False
    return any(
        s.get("region") == task.region_definition and s.get("present") and s.get("visible")
        for s in signals.get("declared_regions", [])
    )


def detect_endpoint_signal(raw: dict[str, Any], task: TaskDefinition) -> bool:
    """`02 §7` 의 endpoint. 이 lane 은 **새 endpoint 를 만들지 않는다** (`A1 §1.1`)."""
    if task.endpoint_definition is None:
        return False
    signals = raw.get("endpoint_signals", {})
    if signals.get("body_endpoint_reached") == task.endpoint_definition:
        return True
    return any(
        e.get("endpoint") == task.endpoint_definition and e.get("visible")
        for e in signals.get("declared_endpoints", [])
    )


def gate_observed(raw: dict[str, Any]) -> bool:
    """gate 로 볼 신호가 **하나라도** 관측됐는가 — 종류와 무관하다.

    `A2 §1.5.1a` 규칙 E-9: `auth_gate_detected` 는 gate 종류를 가리지 않는다.
    유병률(규칙 E-8)은 종류를 합쳐 세고, 종류 구분은 **endpoint 판정에서만** 쓰인다.
    """
    decision = detect_gate(raw)
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
        fixture_root: Path,
        budget: ScoutBudget | None = None,
        execution_mode: ExecutionMode = ExecutionMode.FIXTURE,
        run: EvidenceRun | None = None,
    ) -> None:
        self.fixture_root = Path(fixture_root).resolve()
        self.budget = budget or ScoutBudget()
        self.execution_mode = execution_mode
        self.run = run

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
        probe = page.evaluate(PROBE_JS)
        raw = probe["raw_features"]
        dom = page.content()
        return _StateObservation(
            state_id=state_key(page.url, dom),
            url=page.url,
            raw=raw,
            area=detect_area_signal(raw, task),
            endpoint=detect_endpoint_signal(raw, task),
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
        entry_fixture: str,
        task: TaskDefinition,
    ) -> tuple[TaskEntry, TaskManifest | None]:
        """bounded minimality search. 최소 activation 경로를 찾거나 예산에서 멈춘다."""
        from playwright.sync_api import sync_playwright

        entry_url = assert_navigation_allowed(
            self.execution_mode,
            f"file://{(self.fixture_root / entry_fixture).resolve()}",
            fixture_root=self.fixture_root,
        )
        started = time.monotonic()
        collector = (
            L0Collector(
                self.run, fixture_root=self.fixture_root, execution_mode=self.execution_mode
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
        else:
            status, detail = terminal

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
                entry_fixture=entry_fixture,
                frozen_at=utc_now_iso(),
                path=best_path,
                endpoint_status=depth.endpoint_status.value,
                endpoint_status_detail=(
                    depth.endpoint_status_detail.value if depth.endpoint_status_detail else None
                ),
                ned=depth.ned,
                ied=depth.ied,
                mpfed=depth.mpfed,
                provenance=ShadowProvenance().as_dict(),
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
    "ReplayBroken",
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
    "replay",
    "state_key",
]
