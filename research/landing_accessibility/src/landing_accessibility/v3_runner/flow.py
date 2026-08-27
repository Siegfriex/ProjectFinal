"""v3 Flow 정규화 — raw action sequence → derived flow measurement.

근거 문서는 `SSOTV3/04_FLOW_CODEBOOK_v3.0.md` 하나다. §2 canonical token 18종,
§4 measurement variable 정의, §5 derived 규칙만 구현한다. 보조로
`SSOTV3/03_COLLECTION_MEASUREMENT_SPEC_v3.0.md` §6(action inclusion)·§7(auth),
`SSOTV3/02_DATA_SCHEMA_v3.0.md` §4(`fact_flow_step` 필드)를 참조한다.

**새 토큰·새 조작화를 만들지 않는다.** 04에 규정이 없는 지점은 이 모듈에서
임의로 채우지 않고, (a) 가장 보수적인 처리를 하고 (b) 아래
`KNOWN_LIMITATIONS`에 그 공백을 명시한다.

핵심 분기는 하나다 — **dismissal은 서비스의 task navigation이 아니다.**
`task_flow_sequence`에서 빠지고 `activation_depth`에도 들어가지 않지만
`experienced_flow_sequence`와 `forced_dismissal_count`에는 남는다(04 §3).

D3-11(09 결정로그): menu dependency는 수기 독립라벨이 아니라 action sequence
에서 derive한다. 그래서 `normalize_flow`는 raw step 외의 인자를 받지 않는다.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

__all__ = [
    "ABSTAIN",
    "ACTIVATION_TOKENS",
    "CANONICAL_TOKENS",
    "DISCOVERY_TOKENS",
    "KNOWN_LIMITATIONS",
    "REVEAL_TOKENS",
    "TASK_ENGAGEMENT_TOKENS",
    "FlowNormalization",
    "FlowStep",
    "normalize_flow",
]


# ══════════════════════════════════════════════════════════════════════════
# 1. Canonical tokens — 04 §2 (18종, 이 목록이 전부다)
# ══════════════════════════════════════════════════════════════════════════
OPEN_GLOBAL_MENU = "OPEN_GLOBAL_MENU"
OPEN_LOCAL_MENU = "OPEN_LOCAL_MENU"
SWITCH_TAB = "SWITCH_TAB"
EXPAND_ACCORDION = "EXPAND_ACCORDION"
SELECT_CATEGORY = "SELECT_CATEGORY"
SELECT_FUNCTION = "SELECT_FUNCTION"
INPUT_QUERY = "INPUT_QUERY"
SELECT_ORIGIN = "SELECT_ORIGIN"
SELECT_DESTINATION = "SELECT_DESTINATION"
SELECT_DATE = "SELECT_DATE"
SUBMIT_QUERY = "SUBMIT_QUERY"
SELECT_RESULT = "SELECT_RESULT"
OPEN_ITEM_DETAIL = "OPEN_ITEM_DETAIL"
OPEN_PLACE_DETAIL = "OPEN_PLACE_DETAIL"
DISMISS_OBSTRUCTION = "DISMISS_OBSTRUCTION"
AUTH_GATE = "AUTH_GATE"
ENDPOINT_REACHED = "ENDPOINT_REACHED"
ABSTAIN = "ABSTAIN"

CANONICAL_TOKENS: frozenset[str] = frozenset(
    {
        OPEN_GLOBAL_MENU,
        OPEN_LOCAL_MENU,
        SWITCH_TAB,
        EXPAND_ACCORDION,
        SELECT_CATEGORY,
        SELECT_FUNCTION,
        INPUT_QUERY,
        SELECT_ORIGIN,
        SELECT_DESTINATION,
        SELECT_DATE,
        SUBMIT_QUERY,
        SELECT_RESULT,
        OPEN_ITEM_DETAIL,
        OPEN_PLACE_DETAIL,
        DISMISS_OBSTRUCTION,
        AUTH_GATE,
        ENDPOINT_REACHED,
        ABSTAIN,
    }
)

#: 04 §5 `menu_dependency`가 이름으로 지목한 reveal token 3종.
#: 04 원문은 "OPEN_GLOBAL_MENU/OPEN_LOCAL_MENU/EXPAND_ACCORDION **등**"이라
#: 열린 목록처럼 보이지만, 명시된 것만 넣는다 — 확장은 새 조작화다(KL-02).
REVEAL_TOKENS: frozenset[str] = frozenset({OPEN_GLOBAL_MENU, OPEN_LOCAL_MENU, EXPAND_ACCORDION})

#: 도달한 **상태** 표지이지 사용자의 activation이 아니다.
#: 04 §2 정의: AUTH_GATE "…상태에 도달한다", ENDPOINT_REACHED "…충족된다".
STATE_MARKER_TOKENS: frozenset[str] = frozenset({AUTH_GATE, ENDPOINT_REACHED})

#: 03 §6 "Depth에서 제외: … text 입력". 04 §5 "scroll/typing/passive/dismiss 제외".
TYPING_TOKENS: frozenset[str] = frozenset({INPUT_QUERY})

#: 04 §5 `activation_depth` = state-changing activation token 수.
#: scroll·typing·passive wait·dismiss 제외. scroll/passive는 canonical token에
#: 아예 없으므로(04 §4: "scroll은 activation depth에 포함하지 않음") 여기서
#: 실제로 빼는 것은 typing·dismiss·state marker·ABSTAIN이다.
ACTIVATION_TOKENS: frozenset[str] = (
    CANONICAL_TOKENS - TYPING_TOKENS - STATE_MARKER_TOKENS - {DISMISS_OBSTRUCTION, ABSTAIN}
)

#: task 자체를 붙잡는 게 아니라 control을 **드러내는** navigation.
#: SWITCH_TAB은 reveal(=nav container expansion)로는 세지 않지만(KL-02),
#: task selection으로도 세지 않는다 — 탭 전환은 아직 과업 control을 고른 게
#: 아니라 화면을 바꾼 것이다.
DISCOVERY_TOKENS: frozenset[str] = REVEAL_TOKENS | {SWITCH_TAB}

#: 과업 자체에 손을 댄 token. `auth_gate_stage`의 BEFORE/AFTER 분기와
#: `nav_container_depth`의 "task control 노출" 시점을 정의한다.
TASK_ENGAGEMENT_TOKENS: frozenset[str] = (
    CANONICAL_TOKENS - DISCOVERY_TOKENS - STATE_MARKER_TOKENS - {DISMISS_OBSTRUCTION, ABSTAIN}
)


# ══════════════════════════════════════════════════════════════════════════
# 2. 입력 계약 — 02 §4 `fact_flow_step` 투영
# ══════════════════════════════════════════════════════════════════════════
@dataclass(frozen=True)
class FlowStep:
    """raw 관측 한 step. v3 02 §4 `fact_flow_step` 투영.

    NOTE(KL-01): 이 dataclass의 정본 위치는 `v3_runner/contracts.py`(W5A 소유)다.
    W5B는 그 파일을 만들지 않으므로 여기에 로컬 정의를 둔다. contracts.py가
    올라오면 이 정의를 지우고 그쪽을 import해야 한다 — 필드 이름·순서는
    W5B 티켓에 명시된 계약 그대로다.
    """

    step_index: int
    action_token: str
    state_before_id: str
    state_after_id: str
    control_selector: str | None
    control_role: str | None
    control_visible_text: str | None
    control_accessible_name: str | None
    bbox_before: tuple[float, float, float, float] | None
    url_before: str
    url_after: str
    auth_gate_detected: bool
    endpoint_signal_detected: bool


@dataclass(frozen=True)
class FlowNormalization:
    """04 §4 flow measurement variable 중 sequence-derived 부분.

    산출 불능은 `None`이다. 0이나 FAIL로 접지 않는다 — 0은 "관측했고 없었다"
    라는 실측값이고 `None`은 "판정하지 않았다"는 다른 사실이다.
    """

    task_flow_sequence: tuple[str, ...]
    experienced_flow_sequence: tuple[str, ...]
    activation_depth: int | None
    flow_step_count: int | None
    menu_dependency: bool | None
    nav_container_depth: int | None
    forced_dismissal_count: int | None
    auth_gate_stage: str | None


# auth_gate_stage 값 (04 §4)
AUTH_STAGE_NONE = "NONE"
AUTH_STAGE_BEFORE_TASK_DISCOVERY = "BEFORE_TASK_DISCOVERY"
AUTH_STAGE_AFTER_TASK_SELECT = "AFTER_TASK_SELECT"
AUTH_STAGE_AT_ENDPOINT = "AT_ENDPOINT"

AUTH_GATE_STAGES: frozenset[str] = frozenset(
    {
        AUTH_STAGE_NONE,
        AUTH_STAGE_BEFORE_TASK_DISCOVERY,
        AUTH_STAGE_AFTER_TASK_SELECT,
        AUTH_STAGE_AT_ENDPOINT,
    }
)


# ══════════════════════════════════════════════════════════════════════════
# 3. 정규화
# ══════════════════════════════════════════════════════════════════════════
def normalize_flow(steps: Sequence[FlowStep]) -> FlowNormalization:
    """raw step sequence 하나를 04 §4/§5 derived 값으로 정규화한다.

    손으로 붙인 라벨을 인자로 받지 않는다(09 D3-11). 모든 값은 `steps`에서
    derive된다.

    Raises:
        ValueError: canonical 아닌 action_token, 또는 `step_index`가 강한
            증가 순서가 아닌 경우. 둘 다 수집기 결함이지 측정 결과가
            아니므로 조용히 정규화하지 않고 올린다(KL-06, KL-07).
    """
    _validate(steps)

    experienced = tuple(s.action_token for s in steps)
    task_flow = tuple(t for t in experienced if t != DISMISS_OBSTRUCTION)

    # ── 산출 불능 두 경우 → 파생값 전부 None ────────────────────────────
    # (1) 빈 sequence: derive할 관측 자체가 없다(KL-04).
    # (2) ABSTAIN 포함: "경로 불확정"이 명시된 관측이다. 불확정 경로에서
    #     depth/stage를 확정값으로 내보내는 것이 ABSTAIN 토큰이 막으려는
    #     바로 그 행위다. 04에 파생 규칙이 없어 가장 보수적으로 간다(KL-03).
    if not steps or ABSTAIN in experienced:
        return FlowNormalization(
            task_flow_sequence=task_flow,
            experienced_flow_sequence=experienced,
            activation_depth=None,
            flow_step_count=None,
            menu_dependency=None,
            nav_container_depth=None,
            forced_dismissal_count=None,
            auth_gate_stage=None,
        )

    endpoint_idx = _first_endpoint_index(steps)
    auth_idx = _first_auth_index(steps)

    # 04 §5: activation_depth = state-changing activation token 수.
    activation_depth = sum(1 for t in experienced if t in ACTIVATION_TOKENS)

    # 04 §5: flow_step_count = task-intent token 수. typing/submit/auth
    # encounter 포함, scroll/passive 제외. dismissal은 서비스의 task-intent가
    # 아니므로(04 §3) 제외 → task_flow_sequence 길이와 같다(KL-05).
    flow_step_count = len(task_flow)

    # 04 §5: menu_dependency = 1 iff endpoint 전 reveal token 존재.
    endpoint_cut = len(experienced) if endpoint_idx is None else endpoint_idx
    menu_dependency = any(t in REVEAL_TOKENS for t in experienced[:endpoint_cut])

    # 04 §5: nav_container_depth = task control 노출 전 nested reveal 수.
    # "노출"의 관측 가능한 표지는 과업 control을 실제로 건드린 첫 token이다.
    engage_idx = _first_engagement_index(experienced)
    engage_cut = len(experienced) if engage_idx is None else engage_idx
    nav_container_depth = sum(1 for t in experienced[:engage_cut] if t in REVEAL_TOKENS)

    # 03 §9 / 04 §4: task 진행에 실제 필요했던 dismissal 수. DISMISS_OBSTRUCTION
    # token의 정의 자체가 "task path 진행에 필수인 방해요소"(04 §2)이므로
    # token 출현 수가 곧 필요했던 dismissal 수다.
    forced_dismissal_count = sum(1 for t in experienced if t == DISMISS_OBSTRUCTION)

    auth_gate_stage = _auth_gate_stage(experienced, auth_idx, endpoint_idx)

    return FlowNormalization(
        task_flow_sequence=task_flow,
        experienced_flow_sequence=experienced,
        activation_depth=activation_depth,
        flow_step_count=flow_step_count,
        menu_dependency=menu_dependency,
        nav_container_depth=nav_container_depth,
        forced_dismissal_count=forced_dismissal_count,
        auth_gate_stage=auth_gate_stage,
    )


# ══════════════════════════════════════════════════════════════════════════
# 4. 내부 helper
# ══════════════════════════════════════════════════════════════════════════
def _validate(steps: Sequence[FlowStep]) -> None:
    previous: int | None = None
    for position, step in enumerate(steps):
        if step.action_token not in CANONICAL_TOKENS:
            raise ValueError(
                f"non-canonical action_token at position {position}: "
                f"{step.action_token!r} (04 §2 18종 밖)"
            )
        if previous is not None and step.step_index <= previous:
            raise ValueError(
                f"step_index must strictly increase; got {step.step_index} "
                f"after {previous} at position {position}"
            )
        previous = step.step_index


def _first_endpoint_index(steps: Sequence[FlowStep]) -> int | None:
    """endpoint가 처음 신호된 위치.

    04는 `ENDPOINT_REACHED` token만 말하지만 02 §4 `fact_flow_step`은
    `endpoint_signal_detected` 필드를 따로 갖는다. 둘 중 이른 쪽을 쓴다(KL-08).
    """
    for i, step in enumerate(steps):
        if step.action_token == ENDPOINT_REACHED or step.endpoint_signal_detected:
            return i
    return None


def _first_auth_index(steps: Sequence[FlowStep]) -> int | None:
    """auth gate가 처음 걸린 위치. token과 `auth_gate_detected` 중 이른 쪽(KL-08)."""
    for i, step in enumerate(steps):
        if step.action_token == AUTH_GATE or step.auth_gate_detected:
            return i
    return None


def _first_engagement_index(tokens: Sequence[str]) -> int | None:
    for i, token in enumerate(tokens):
        if token in TASK_ENGAGEMENT_TOKENS:
            return i
    return None


def _auth_gate_stage(tokens: Sequence[str], auth_idx: int | None, endpoint_idx: int | None) -> str:
    """04 §4 / 03 §7 — auth가 **언제** 걸렸는가.

    - `NONE`: auth 신호 없음.
    - `AT_ENDPOINT`: endpoint 신호가 auth와 같거나 그보다 앞. 과업 경로를 다
      밟고 endpoint에서 인증이 요구된 경우.
    - `AFTER_TASK_SELECT`: auth 전에 과업 control을 이미 건드렸다.
    - `BEFORE_TASK_DISCOVERY`: auth 전에는 reveal/dismiss밖에 없었다 —
      과업 진입 control을 고르기도 전에 인증이 걸렸다.
    """
    if auth_idx is None:
        return AUTH_STAGE_NONE
    if endpoint_idx is not None and endpoint_idx <= auth_idx:
        return AUTH_STAGE_AT_ENDPOINT
    if any(t in TASK_ENGAGEMENT_TOKENS for t in tokens[:auth_idx]):
        return AUTH_STAGE_AFTER_TASK_SELECT
    return AUTH_STAGE_BEFORE_TASK_DISCOVERY


# ══════════════════════════════════════════════════════════════════════════
# 5. Known limitations — 04에 규정이 없어 W5B가 판단한 지점 전부
# ══════════════════════════════════════════════════════════════════════════
KNOWN_LIMITATIONS: tuple[str, ...] = (
    "KL-01 FlowStep 정본은 v3_runner/contracts.py(W5A 소유)다. W5B는 그 파일을 "
    "만들지 않으므로 flow.py에 로컬 정의를 뒀다. contracts.py 편입 시 중복 "
    "정의를 제거하고 import로 교체해야 한다. v3_runner에 __init__.py를 두지 "
    "않았다(W5A와 같은 파일을 동시에 만들지 않기 위해) — namespace package로 "
    "import된다.",
    "KL-02 04 §5는 reveal token을 'OPEN_GLOBAL_MENU/OPEN_LOCAL_MENU/"
    "EXPAND_ACCORDION 등'으로 적어 목록이 열려 있다. W5B는 명시된 3종만 "
    "reveal로 센다. SWITCH_TAB을 넣지 않은 근거는 04 §4 nav_container_type "
    "열거(NONE/HAMBURGER/LEFT_DRAWER/RIGHT_DRAWER/TOP_DROPDOWN/BOTTOM_SHEET/"
    "MODAL_MENU/INLINE_EXPAND)에 tab이 없다는 것뿐이다. 이 판단이 뒤집히면 "
    "menu_dependency/nav_container_depth가 함께 움직인다.",
    "KL-03 04에는 ABSTAIN이 섞인 sequence의 derived 규칙이 없다. W5B는 "
    "'경로 불확정'이라는 토큰 정의(04 §2)를 근거로 파생 scalar 6개를 전부 "
    "None으로 둔다. sequence 2종은 raw 투영이므로 ABSTAIN을 남긴 채 반환한다. "
    "다른 선택(예: ABSTAIN 앞부분만 부분 derive)도 가능하며 04가 정하지 않았다.",
    "KL-04 빈 step sequence의 처리도 04에 없다. W5B는 '관측이 없다'를 "
    "'값이 0이다'로 바꾸지 않기 위해 파생값을 None으로 둔다. 실제로 활성화가 "
    "0회였던 flow는 최소한 ENDPOINT_REACHED/AUTH_GATE 같은 terminal token을 "
    "갖게 되므로 빈 sequence와 구분된다.",
    "KL-05 04 §5 flow_step_count는 'typing/submit/auth encounter 포함'만 "
    "열거하고 ENDPOINT_REACHED·DISMISS_OBSTRUCTION을 언급하지 않는다. W5B는 "
    "(a) dismissal은 서비스 task-intent가 아니므로 제외(04 §3), "
    "(b) ENDPOINT_REACHED는 AUTH_GATE와 같은 terminal 상태 표지이므로 "
    "AUTH_GATE가 포함되는 이상 대칭적으로 포함 — 결과적으로 flow_step_count == "
    "len(task_flow_sequence)다.",
    "KL-06 04는 canonical 밖 token의 처리를 정하지 않는다. W5B는 ValueError를 "
    "올린다. 조용히 무시하면 없는 step이 depth에서 사라져 과소측정이 된다.",
    "KL-07 step_index가 강한 증가가 아닌 입력도 04에 규정이 없다. flow는 "
    "ordered sequence가 primary(04 §1)이므로 재정렬하지 않고 ValueError로 "
    "올린다 — 순서 붕괴는 수집기 결함이다.",
    "KL-08 04는 AUTH_GATE/ENDPOINT_REACHED를 token으로만 말하지만 02 §4 "
    "fact_flow_step에는 auth_gate_detected/endpoint_signal_detected 불리언이 "
    "따로 있다. W5B는 token과 flag 중 이른 쪽을 신호 위치로 쓴다. 두 신호가 "
    "충돌할 때 어느 쪽이 정본인지는 04·02 모두 정하지 않았다.",
    "KL-09 activation_depth에 SUBMIT_QUERY를 포함했다. 04 §5의 제외 목록"
    "(scroll/typing/passive/dismiss)에 submit이 없기 때문이다. 다만 03 §6은 "
    "'단 flow_step_count에는 task-intent typing/submit을 별도 token으로 "
    "보존한다'고 적어 submit도 depth 밖이라는 읽기가 가능하다. 04를 정본으로 "
    "삼았고 이 충돌은 미해소다.",
    "KL-10 nav_container_depth의 'task control 노출'을 '첫 task-engagement "
    "token'으로 조작화했다. engagement token이 아예 없는 flow(예: reveal만 "
    "하다 중단)에서는 전체 prefix의 reveal 수를 센다 — '노출 전'이 sequence "
    "전체이기 때문이다. 04에 명시 없음.",
    "KL-11 auth_gate_stage의 AT_ENDPOINT를 'endpoint 신호 index <= auth 신호 "
    "index'로 조작화했다. 04는 세 값의 이름만 주고 경계를 정의하지 않는다. "
    "BEFORE_TASK_DISCOVERY/AFTER_TASK_SELECT 경계도 마찬가지로 "
    "TASK_ENGAGEMENT_TOKENS 출현 여부로 W5B가 조작화한 것이다.",
    "KL-12 이 모듈은 sequence-derived 변수만 산출한다. 04 §4의 geometry/label/"
    "occlusion 계열(entry_x_norm, label_relation, task_control_occlusion, "
    "endpoint_status 등)과 legacy NED/IED/MPFED는 W5B claim 밖이다. FlowStep의 "
    "bbox_before/control_* 필드는 계약대로 받되 이 모듈에서 사용하지 않는다.",
)
