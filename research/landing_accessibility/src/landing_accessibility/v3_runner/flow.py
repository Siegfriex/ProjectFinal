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

──────────────────────────────────────────────────────────────────────────
층 한정 의무 — A 사전등록 `T-A-V3-STEP1-003` R6-Q8
──────────────────────────────────────────────────────────────────────────
`action_token=AUTH_GATE`와 `endpoint_status=AUTH_GATE`는 **같은 문자열을
쓰지만 서로 다른 층이다.** `action_token=ABSTAIN`과 `endpoint_status=ABSTAIN`도
마찬가지다. 04 codebook을 개명하지 않는 대신 값을 단독으로 쓰지 않고
항상 층을 한정한다. 이 모듈의 규약:

- Python 상수는 전부 `ACTION_` 접두사를 단다 — `ACTION_AUTH_GATE`,
  `ACTION_ABSTAIN`. 식별자만 봐도 어느 층인지 읽힌다.
- 주석·docstring·에러 메시지는 `action_token=AUTH_GATE` 형태로만 쓴다.
- 산출물에서 층을 지고 있는 것은 필드 이름이다. `task_flow_sequence`·
  `experienced_flow_sequence`의 원소는 **action_token 층의 값**이다.
  이 모듈은 `endpoint_status` 층의 값을 만들지도 반환하지도 않는다.

──────────────────────────────────────────────────────────────────────────
R2 — 진입 flow 지표는 auth gate 여부와 무관하게 산출된다
──────────────────────────────────────────────────────────────────────────
A 원문: "진입 flow 지표는 `action_token=AUTH_GATE` 여부와 무관하게 산출된다.
entry position·visible_label·accessible_name·control type·menu/reveal·
`nav_container_depth`·`auth_gate_stage`는 gate 이전에 전부 관측된다. 이것들의
분모에서 F2~F5의 gate target을 빼지 마라 — 빼면 '인증이 일찍 걸리는 서비스'가
진입구조 분석에서 조용히 사라진다."

따라서 **gate terminal은 이 모듈에서 산출 불능 사유가 아니다.** gate에 걸린
run도 8개 필드를 전부 값으로 낸다. gate 도달 자체가 `auth_gate_stage`를
확정하고, gate까지의 경로가 그대로 두 sequence이며, gate 이전 activation이
`activation_depth`·`flow_step_count`·`menu_dependency`·`nav_container_depth`다.

**이 모듈 산출 8종 중 gate 이후에만 관측 가능한 것은 없다.** `None`이 나오는
경로는 gate와 무관한 둘뿐이다 — (1) 빈 sequence(관측 부재), (2)
`action_token=ABSTAIN` 포함(경로 불확정). 자세한 근거는 KL-03/KL-04/KL-13.

──────────────────────────────────────────────────────────────────────────
Δ9 — 18종 depth 귀속 (A `T-A-V3-STEP1-006`)
──────────────────────────────────────────────────────────────────────────
A가 목록 대신 3항 기준을 세웠다: ① 사용자의 의도적 조작인가 ② control
활성화인가 ③ 상태가 전이되는가.

- **IN (10)**: OPEN_GLOBAL_MENU · OPEN_LOCAL_MENU · SWITCH_TAB ·
  EXPAND_ACCORDION · SELECT_CATEGORY · SELECT_FUNCTION · SUBMIT_QUERY ·
  SELECT_RESULT · OPEN_ITEM_DETAIL · OPEN_PLACE_DETAIL
- **OUT (5)**: INPUT_QUERY(타이핑) · DISMISS_OBSTRUCTION(별도 카운트) ·
  action_token=AUTH_GATE(마주친 상태, 기준 ①) · ENDPOINT_REACHED(종결 표지) ·
  action_token=ABSTAIN(판정 유보). OUT 5종 중 auth encounter와 typing은
  `flow_step_count`에는 포함된다 — 두 축은 다른 질문이다.
- **CONDITIONAL (3)**: SELECT_ORIGIN · SELECT_DESTINATION · SELECT_DATE.
  입력수단에 따라 갈린다. `FlowStep.input_mode`로 판정한다.

**두 축을 혼동하지 마라.** `activation_depth` 귀속과 `menu_dependency`의
reveal 집합은 별개 질문이다. SWITCH_TAB은 `activation_depth`에 **들어가고**
(A Δ9 확정), `REVEAL_TOKENS`에는 **들어가지 않는다**(04 §4 nav_container_type
열거에 tab 없음, A가 그 축에서는 유효하다고 확인). KL-02 참조.

──────────────────────────────────────────────────────────────────────────
Δ15 — 두 지표의 의도된 비대칭 (A `T-A-V3-STEP1-012`, GAP-03)
──────────────────────────────────────────────────────────────────────────
::

    activation_depth : action_token=AUTH_GATE 제외 · ENDPOINT_REACHED 제외 (Δ9)
    flow_step_count  : action_token=AUTH_GATE 포함 · ENDPOINT_REACHED 제외 (Δ15)

`action_token=AUTH_GATE`만 두 지표에서 다르게 취급된다. **버그가 아니다.**

근거는 04 §5의 문면이다 — "typing/submit/**auth encounter** 포함"이라고
`flow_step_count`에만 auth encounter를 **이름 붙여** 넣었다. Δ9의 3항 기준
(①의도적 조작 ②control 활성화 ③상태 전이)으로는 auth는 마주친 상태이지
활성화가 아니라 `activation_depth`에서 빠진다. 두 지표가 다른 질문을 하므로
같은 토큰이 다르게 귀속되는 것이다.

`action_token=ENDPOINT_REACHED`는 두 지표 모두에서 빠진다 — 04 §5가 이름을
붙이지 않았고, 도달 기록은 사용자가 한 일이 아니라 계측이 남긴 표지다.

**이것을 "맞추려고" 하지 마라.** 대칭으로 보이게 고치는 순간 SSOT 문면과
어긋난다.

──────────────────────────────────────────────────────────────────────────
GAP-04 — 결측 표현 규약 (A)
──────────────────────────────────────────────────────────────────────────
- 수치 필드 미관측은 `None`이다. **`0`이 아니다.**
- 범주 필드는 명시적 판정불능 값(`UNDETERMINED`)이다. **빈 문자열 금지.**
- **한 행 안에서 결측 표현이 섞이지 않는다.** 이 모듈의 한 산출은 수치/bool
  결측을 전부 `None`으로, 범주 결측을 `UNDETERMINED`로만 표현한다.

이 모듈이 지키는 불변식: **count 필드의 `0`은 언제나 "세었고 0"이다.**
못 센 경우는 예외 없이 `None`이다. 이 불변식이 깨지면 "장애물이 없었다"와
"장애물을 관측하지 못했다"가 같은 값이 된다.

──────────────────────────────────────────────────────────────────────────
Δ10 — 증거의 부재는 부재의 증거가 아니다 (A `T-A-V3-STEP1-007` R13)
──────────────────────────────────────────────────────────────────────────
A 원문: "어떤 변수든 '없음'을 적으려면 관측했다는 증거가 있어야 한다.
관측하지 못했으면 판정불능 값을 쓴다."

`auth_gate_stage`에 `UNDETERMINED`가 추가되고 `NONE`의 의미가 좁아진다.
`NONE`은 **경로가 terminal까지 갔고 auth를 만나지 않았다**는 적극적 주장이다.

이 모듈은 terminal 도달 여부로 관측 완결성을 판정한다. **terminal은 endpoint
신호 또는 auth gate 신호다** — 04에서 둘 다 경로의 종결이고, R2가 gate 도달
자체로 진입구조가 확정된다고 못박았으므로 gate도 완결된 진입 관측이다.
terminal이 없는 run(중단·evidence defect)은 진입구조를 끝까지 보지 못한
것이므로 부정 주장을 할 수 없다.

`menu_dependency`·`nav_container_depth`가 이 규칙에 걸린다(KL-15/KL-10).
`activation_depth`·`flow_step_count`·`forced_dismissal_count`는 걸리지 않는다 —
이 셋은 "관측된 run에서 센 수"이고 milestone을 참조하지 않는다. 다만 중단된
run의 값은 **하한**이며 완주 run과 같은 분포로 취급하면 안 된다(KL-13).

**집계 규칙**: `UNDETERMINED`를 분모에서 빼지 마라. 별도 범주로 보고한다.
빼면 그 자체가 selection이고, auth 발생률이 체계적으로 과소추정된다.

──────────────────────────────────────────────────────────────────────────
family별 해석 차이 — 이 모듈은 판정하지 않는다
──────────────────────────────────────────────────────────────────────────
같은 `action_token=AUTH_GATE`가 family에 따라 다른 것을 뜻한다.

- **F1**: `endpoint_contract`가 gate를 endpoint로 명시한다 → endpoint 도달로 센다.
- **F2~F5**: gate는 endpoint 미도달 terminal이다.

`normalize_flow`는 `TaskContract`를 받지 않으므로 **family를 모르고, 알 필요도
없다.** 층 판정(endpoint 도달로 셀 것인가)은 mart 층 몫이다. 이 모듈 산출을
쓰는 쪽은 family별로 다르게 해석해야 한다. 분모도 mart가 나눈다 — gate run은
`evidence-bearing n`에 포함되고, endpoint 의존 지표만 `flow-evaluable n`을 쓴다.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

# SEAM 2 (W5K, A 판정) — `FlowStep` 의 정본은 `contracts.py` 다. KL-01 이 예고한
# 로컬 정의 제거를 여기서 수행한다. `input_mode` 는 이 lane 이 추가했고 A 가 승인해
# 정본에 반영됐다 — 필드 이름·순서는 그대로다.
from .contracts import FlowStep

__all__ = [
    "ACTION_ABSTAIN",
    "ACTION_AUTH_GATE",
    "ACTIVATION_TOKENS",
    "AUTH_STAGE_VALUES",
    "CANONICAL_TOKENS",
    "CONDITIONAL_DEPTH_TOKENS",
    "DISCOVERY_TOKENS",
    "FLOW_STEP_COUNT_EXCLUDED",
    "INPUT_MODES_ACTIVATING",
    "INPUT_MODES_TYPED",
    "KNOWN_LIMITATIONS",
    "REVEAL_TOKENS",
    "TASK_ENGAGEMENT_TOKENS",
    "DepthConditionalRecord",
    "FlowNormalization",
    "FlowStep",
    "normalize_flow",
]


# ══════════════════════════════════════════════════════════════════════════
# 1. Canonical action tokens — 04 §2 (18종, 이 목록이 전부다)
#
#    상수 이름의 `ACTION_` 접두사는 R6-Q8 층 한정이다. 값 자체는 04 §2
#    canonical 어휘라 바꾸지 않는다 — 바꾸는 것이 새 토큰 생성이다.
# ══════════════════════════════════════════════════════════════════════════
ACTION_OPEN_GLOBAL_MENU = "OPEN_GLOBAL_MENU"
ACTION_OPEN_LOCAL_MENU = "OPEN_LOCAL_MENU"
ACTION_SWITCH_TAB = "SWITCH_TAB"
ACTION_EXPAND_ACCORDION = "EXPAND_ACCORDION"
ACTION_SELECT_CATEGORY = "SELECT_CATEGORY"
ACTION_SELECT_FUNCTION = "SELECT_FUNCTION"
ACTION_INPUT_QUERY = "INPUT_QUERY"
ACTION_SELECT_ORIGIN = "SELECT_ORIGIN"
ACTION_SELECT_DESTINATION = "SELECT_DESTINATION"
ACTION_SELECT_DATE = "SELECT_DATE"
ACTION_SUBMIT_QUERY = "SUBMIT_QUERY"
ACTION_SELECT_RESULT = "SELECT_RESULT"
ACTION_OPEN_ITEM_DETAIL = "OPEN_ITEM_DETAIL"
ACTION_OPEN_PLACE_DETAIL = "OPEN_PLACE_DETAIL"
ACTION_DISMISS_OBSTRUCTION = "DISMISS_OBSTRUCTION"
#: 층 주의: 같은 문자열이 endpoint_status 층에도 있다(04 §4). 여기서는
#: action_token 층의 값이다 — 04 §2 "인증이 불가피해지는 상태에 도달한다".
ACTION_AUTH_GATE = "AUTH_GATE"
ACTION_ENDPOINT_REACHED = "ENDPOINT_REACHED"
#: 층 주의: 같은 문자열이 endpoint_status 층에도 있다(04 §4). 여기서는
#: action_token 층의 값이다 — 04 §2 "증거 부족/다중 후보/경로 불확정".
ACTION_ABSTAIN = "ABSTAIN"

CANONICAL_TOKENS: frozenset[str] = frozenset(
    {
        ACTION_OPEN_GLOBAL_MENU,
        ACTION_OPEN_LOCAL_MENU,
        ACTION_SWITCH_TAB,
        ACTION_EXPAND_ACCORDION,
        ACTION_SELECT_CATEGORY,
        ACTION_SELECT_FUNCTION,
        ACTION_INPUT_QUERY,
        ACTION_SELECT_ORIGIN,
        ACTION_SELECT_DESTINATION,
        ACTION_SELECT_DATE,
        ACTION_SUBMIT_QUERY,
        ACTION_SELECT_RESULT,
        ACTION_OPEN_ITEM_DETAIL,
        ACTION_OPEN_PLACE_DETAIL,
        ACTION_DISMISS_OBSTRUCTION,
        ACTION_AUTH_GATE,
        ACTION_ENDPOINT_REACHED,
        ACTION_ABSTAIN,
    }
)

#: 04 §5 `menu_dependency`가 이름으로 지목한 reveal token 3종.
#: 04 원문은 "OPEN_GLOBAL_MENU/OPEN_LOCAL_MENU/EXPAND_ACCORDION **등**"이라
#: 열린 목록처럼 보이지만, 명시된 것만 넣는다 — 확장은 새 조작화다(KL-02).
REVEAL_TOKENS: frozenset[str] = frozenset(
    {ACTION_OPEN_GLOBAL_MENU, ACTION_OPEN_LOCAL_MENU, ACTION_EXPAND_ACCORDION}
)

#: 도달한 **상태** 표지이지 사용자의 activation이 아니다.
#: 04 §2 정의: action_token=AUTH_GATE "…상태에 도달한다",
#: action_token=ENDPOINT_REACHED "…충족된다".
STATE_MARKER_TOKENS: frozenset[str] = frozenset({ACTION_AUTH_GATE, ACTION_ENDPOINT_REACHED})

#: 03 §6 "Depth에서 제외: … text 입력". 04 §5 "scroll/typing/passive/dismiss 제외".
TYPING_TOKENS: frozenset[str] = frozenset({ACTION_INPUT_QUERY})

#: A Δ9 CONDITIONAL 3종. 입력수단에 따라 activation 귀속이 갈린다.
#: picker/dropdown/calendar처럼 control을 활성화해야 값이 정해지면 포함,
#: 자유입력란에 타이핑했으면 제외(타이핑이므로 `flow_step_count`에만).
CONDITIONAL_DEPTH_TOKENS: frozenset[str] = frozenset(
    {ACTION_SELECT_ORIGIN, ACTION_SELECT_DESTINATION, ACTION_SELECT_DATE}
)

#: A Δ9 IN 10종 — 입력수단과 무관하게 항상 activation으로 센다.
#: 04 §5 "scroll·typing·passive wait·dismiss 제외". scroll/passive는 canonical
#: token에 아예 없으므로(04 §4) 실제로 빠지는 것은 typing·dismiss·state
#: marker·action_token=ABSTAIN, 그리고 별도 판정하는 CONDITIONAL 3종이다.
ACTIVATION_TOKENS: frozenset[str] = (
    CANONICAL_TOKENS
    - TYPING_TOKENS
    - STATE_MARKER_TOKENS
    - CONDITIONAL_DEPTH_TOKENS
    - {ACTION_DISMISS_OBSTRUCTION, ACTION_ABSTAIN}
)

#: A Δ15(GAP-03) `flow_step_count` 제외 집합.
#: 04 §5 "task-intent token 수. typing/submit/auth encounter 포함, scroll/
#: passive 제외"를 축자로 읽는다 — auth encounter는 **이름이 붙어** 포함되고
#: (action_token=AUTH_GATE), ENDPOINT_REACHED는 이름이 없다. 도달 기록은
#: 계측이 남긴 표지이므로 task-intent가 아니다. action_token=ABSTAIN은
#: 판정 유보이지 행위가 아니다. DISMISS_OBSTRUCTION은 서비스의
#: task-intent가 아니다(04 §3).
FLOW_STEP_COUNT_EXCLUDED: frozenset[str] = frozenset(
    {ACTION_ENDPOINT_REACHED, ACTION_ABSTAIN, ACTION_DISMISS_OBSTRUCTION}
)

#: Δ8-R5 `fixture_input_mode` 중 A가 이름으로 지목한 값만 인지한다.
#: "DROPDOWN/MAP_PAN 계열"의 '계열'을 임의 확장하지 않는다 — 미인지 값은
#: 판정 불능으로 처리하고 KL-16에 그 공백을 적는다.
INPUT_MODES_ACTIVATING: frozenset[str] = frozenset({"DROPDOWN", "MAP_PAN"})
INPUT_MODES_TYPED: frozenset[str] = frozenset({"FREE_TEXT"})
INPUT_MODE_MIXED = "MIXED"

#: task 자체를 붙잡는 게 아니라 control을 **드러내는** navigation.
#: action_token=SWITCH_TAB은 reveal(=nav container expansion)로는 세지 않지만
#: (KL-02), task selection으로도 세지 않는다 — 탭 전환은 아직 과업 control을
#: 고른 게 아니라 화면을 바꾼 것이다.
DISCOVERY_TOKENS: frozenset[str] = REVEAL_TOKENS | {ACTION_SWITCH_TAB}

#: 과업 자체에 손을 댄 token. `auth_gate_stage`의 BEFORE/AFTER 분기와
#: `nav_container_depth`의 "task control 노출" 시점을 정의한다.
TASK_ENGAGEMENT_TOKENS: frozenset[str] = (
    CANONICAL_TOKENS
    - DISCOVERY_TOKENS
    - STATE_MARKER_TOKENS
    - {ACTION_DISMISS_OBSTRUCTION, ACTION_ABSTAIN}
)
# NOTE: CONDITIONAL 3종은 여기 포함된다. depth 귀속이 입력수단에 따라 갈리는
# 것과, 그 조작이 과업에 손을 댄 것이냐는 별개 질문이다 — 출발지를 자유
# 입력으로 쳤든 dropdown으로 골랐든 과업에 관여한 것은 같다.


# ══════════════════════════════════════════════════════════════════════════
# 2. 입력 계약 — 02 §4 `fact_flow_step` 투영
# ══════════════════════════════════════════════════════════════════════════
@dataclass(frozen=True)
class DepthConditionalRecord:
    """CONDITIONAL 토큰 한 건의 depth 귀속 판정 기록 (A Δ9 요구).

    어느 토큰이 어떤 근거로 포함/제외됐는지 관측마다 남긴다.
    `included_in_activation_depth`가 `None`이면 판정 불능이며, 그 관측의
    `activation_depth` 전체가 `None`이 된다.
    """

    step_index: int
    action_token: str
    input_mode: str | None
    included_in_activation_depth: bool | None
    basis: str


@dataclass(frozen=True)
class FlowNormalization:
    """04 §4 flow measurement variable 중 sequence-derived 부분.

    두 sequence 필드의 원소는 **action_token 층**의 값이다(R6-Q8). 이 모듈은
    `endpoint_status` 층의 값을 만들지 않는다 — 그 층은 mart 몫이다.

    산출 불능은 `None`이다. 0이나 FAIL로 접지 않는다 — 0은 "관측했고 없었다"
    라는 실측값이고 `None`은 "판정하지 않았다"는 다른 사실이다. 특히
    `auth_gate_stage`의 `"NONE"`(auth 신호를 관측했고 없었다)과 `None`
    (판정하지 않았다)은 서로 다른 사실이며 집계에서 섞으면 안 된다.

    **auth gate terminal은 산출 불능 사유가 아니다**(R2). gate에 걸린 run도
    진입구조 필드를 전부 값으로 낸다. 이 산출 중 gate 이후에만 관측 가능한
    것은 없다.

    `auth_gate_stage`는 `None`이 아니다 — enum에 `UNDETERMINED`가 있으므로
    판정 불능도 값으로 표현한다(Δ10). 집계에서 `UNDETERMINED`를 분모에서
    빼지 마라. 별도 범주로 보고한다.
    """

    task_flow_sequence: tuple[str, ...]
    experienced_flow_sequence: tuple[str, ...]
    activation_depth: int | None
    flow_step_count: int | None
    menu_dependency: bool | None
    nav_container_depth: int | None
    forced_dismissal_count: int | None
    auth_gate_stage: str
    #: CONDITIONAL 3종의 관측별 귀속 판정 기록 (A Δ9). 비어 있으면 그 run에
    #: CONDITIONAL 토큰이 없었다는 뜻이다.
    depth_conditional_tokens: tuple[DepthConditionalRecord, ...] = ()


# `auth_gate_stage` 값 (04 §4). action_token 층과 문자열이 겹치지 않는
# 별도 어휘다 — 이 네 값은 stage 층에만 존재한다.
#: 관측했고 auth gate가 없었다. **적극적 주장이며 terminal 도달을 요구한다**
#: (Δ10). 관측하지 못한 것을 여기에 넣으면 auth 발생률이 과소추정된다.
AUTH_STAGE_NONE = "NONE"
#: 판정할 수 없었다 — 증거 부재·경로 미완·evidence defect (Δ10 신규).
AUTH_STAGE_UNDETERMINED = "UNDETERMINED"
AUTH_STAGE_BEFORE_TASK_DISCOVERY = "BEFORE_TASK_DISCOVERY"
AUTH_STAGE_AFTER_TASK_SELECT = "AFTER_TASK_SELECT"
AUTH_STAGE_AT_ENDPOINT = "AT_ENDPOINT"

AUTH_STAGE_VALUES: frozenset[str] = frozenset(
    {
        AUTH_STAGE_NONE,
        AUTH_STAGE_UNDETERMINED,
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
    derive된다. family/task contract도 받지 않는다 — 층 판정은 mart 몫이다.

    auth gate에서 경로가 끊긴 run도 파생값을 전부 산출한다(R2). 조기 종료를
    산출 불능으로 접으면 '인증이 일찍 걸리는 서비스'가 진입구조 분석에서
    사라진다.

    Raises:
        ValueError: canonical 아닌 `action_token`, 또는 `step_index`가 강한
            증가 순서가 아닌 경우. 둘 다 수집기 결함이지 측정 결과가
            아니므로 조용히 정규화하지 않고 올린다(KL-06, KL-07).
    """
    _validate(steps)

    experienced = tuple(s.action_token for s in steps)
    task_flow = tuple(t for t in experienced if t != ACTION_DISMISS_OBSTRUCTION)
    conditional_records = _conditional_records(steps)

    # ── 산출 불능 두 경로 ────────────────────────────────────────────
    # 여기에 auth gate는 없다. gate terminal은 산출 불능이 아니다(R2).
    #
    # (1) 빈 sequence: derive할 관측 자체가 없다(KL-04).
    # (2) action_token=ABSTAIN 포함: "경로 불확정"이 명시된 관측이다. 불확정
    #     경로에서 depth/stage를 확정값으로 내보내는 것이 그 토큰이 막으려는
    #     바로 그 행위다. 04에 파생 규칙이 없어 가장 보수적으로 간다(KL-03).
    #
    # 단 `auth_gate_stage`는 이제 None이 아니라 UNDETERMINED다 — enum에
    # 판정불능 값이 생겼으므로 None으로 접을 이유가 없다(Δ10).
    if not steps or ACTION_ABSTAIN in experienced:
        return FlowNormalization(
            task_flow_sequence=task_flow,
            experienced_flow_sequence=experienced,
            activation_depth=None,
            flow_step_count=None,
            menu_dependency=None,
            nav_container_depth=None,
            forced_dismissal_count=None,
            auth_gate_stage=AUTH_STAGE_UNDETERMINED,
            depth_conditional_tokens=conditional_records,
        )

    endpoint_idx = _first_endpoint_index(steps)
    auth_idx = _first_auth_index(steps)
    # Δ10 관측 완결성. endpoint 신호 또는 auth gate 신호 = terminal 도달.
    # terminal이 없으면 진입구조를 끝까지 보지 못한 것이므로 부정 주장
    # ("reveal 없이 도달했다")을 할 수 없다.
    has_terminal = endpoint_idx is not None or auth_idx is not None

    # 04 §5: activation_depth = state-changing activation token 수.
    # CONDITIONAL 3종은 입력수단으로 따로 판정한다(Δ9). 한 건이라도 판정
    # 불능이면 합계가 확정되지 않으므로 None이다 — 모르는 것을 0으로 세면
    # 그 자체가 과소측정이다.
    if any(rec.included_in_activation_depth is None for rec in conditional_records):
        activation_depth: int | None = None
    else:
        activation_depth = sum(1 for t in experienced if t in ACTIVATION_TOKENS) + sum(
            1 for rec in conditional_records if rec.included_in_activation_depth
        )

    # 04 §5: flow_step_count = task-intent token 수 (A Δ15).
    # CONDITIONAL 3종은 입력수단과 무관하게 여기 포함된다 — 자유입력이면
    # 타이핑이라 activation에서만 빠지고 task-intent인 것은 변함없다.
    # `len(task_flow_sequence)`와 같지 않다 — endpoint 도달 flow에서는
    # 정확히 1 작다(KL-05).
    flow_step_count = sum(1 for t in experienced if t not in FLOW_STEP_COUNT_EXCLUDED)

    # 04 §5: menu_dependency = 1 iff endpoint 전 reveal token 존재.
    # endpoint 신호가 없으면(gate terminal·중단) 관측된 sequence 전체가
    # "endpoint 전"이다 — gate 이전 reveal이 그대로 잡힌다(R2).
    endpoint_cut = len(experienced) if endpoint_idx is None else endpoint_idx
    menu_dependency = _menu_dependency(experienced[:endpoint_cut], has_terminal)

    # 04 §5: nav_container_depth = task control 노출 전 nested reveal 수.
    nav_container_depth = _nav_container_depth(experienced, has_terminal)

    # 03 §9 / 04 §4: task 진행에 실제 필요했던 dismissal 수.
    # action_token=DISMISS_OBSTRUCTION의 정의 자체가 "task path 진행에 필수인
    # 방해요소"(04 §2)이므로 token 출현 수가 곧 필요했던 dismissal 수다.
    forced_dismissal_count = sum(1 for t in experienced if t == ACTION_DISMISS_OBSTRUCTION)

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
        depth_conditional_tokens=conditional_records,
    )


# ══════════════════════════════════════════════════════════════════════════
# 4. 내부 helper
# ══════════════════════════════════════════════════════════════════════════
def _conditional_records(
    steps: Sequence[FlowStep],
) -> tuple[DepthConditionalRecord, ...]:
    """CONDITIONAL 3종의 관측별 depth 귀속을 판정하고 근거를 남긴다 (A Δ9)."""
    records: list[DepthConditionalRecord] = []
    for st in steps:
        if st.action_token not in CONDITIONAL_DEPTH_TOKENS:
            continue
        verdict, basis = _conditional_verdict(st.input_mode)
        records.append(
            DepthConditionalRecord(
                step_index=st.step_index,
                action_token=st.action_token,
                input_mode=st.input_mode,
                included_in_activation_depth=verdict,
                basis=basis,
            )
        )
    return tuple(records)


def _conditional_verdict(input_mode: str | None) -> tuple[bool | None, str]:
    """입력수단 하나를 depth 귀속으로 옮긴다. `None` verdict = 판정 불능."""
    if input_mode is None:
        return None, "input_mode 미기록 — Δ8-R5 fixture_input_mode 없이 판정 불가"
    if input_mode in INPUT_MODES_ACTIVATING:
        return True, f"input_mode={input_mode} — control 활성화로 값이 정해짐 (Δ9)"
    if input_mode in INPUT_MODES_TYPED:
        return False, f"input_mode={input_mode} — 자유입력 타이핑, flow_step_count에만 (Δ9)"
    if input_mode == INPUT_MODE_MIXED:
        return None, "input_mode=MIXED — step 층에서 실제 사용 수단 미해소 (Δ9)"
    return None, f"input_mode={input_mode} — Δ8-R5 열거에서 미인지 (KL-16)"


def _menu_dependency(prefix: Sequence[str], has_terminal: bool) -> bool | None:
    """reveal 존재는 양성 관측이라 항상 확정. 부재 주장은 terminal을 요구한다.

    Δ10: 중단된 run에서 reveal을 못 봤다는 것은 "reveal이 필요 없었다"가
    아니라 "거기까지 못 갔다"일 수 있다.
    """
    if any(t in REVEAL_TOKENS for t in prefix):
        return True
    return False if has_terminal else None


def _nav_container_depth(tokens: Sequence[str], has_terminal: bool) -> int | None:
    """task control 노출 전 nested reveal 수.

    노출의 관측 가능한 표지는 과업 control을 실제로 건드린 첫 token이다.
    노출이 일어나지 않았고 terminal도 없으면 값이 정의되지 않는다 —
    진짜 depth가 더 컸을 수 있다(KL-10).
    """
    engage_idx = _first_engagement_index(tokens)
    if engage_idx is None and not has_terminal:
        return None
    cut = len(tokens) if engage_idx is None else engage_idx
    return sum(1 for t in tokens[:cut] if t in REVEAL_TOKENS)


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

    04는 `action_token=ENDPOINT_REACHED`만 말하지만 02 §4 `fact_flow_step`은
    `endpoint_signal_detected` 필드를 따로 갖는다. 둘 중 이른 쪽을 쓴다(KL-08).
    """
    for i, step in enumerate(steps):
        if step.action_token == ACTION_ENDPOINT_REACHED or step.endpoint_signal_detected:
            return i
    return None


def _first_auth_index(steps: Sequence[FlowStep]) -> int | None:
    """auth gate가 처음 걸린 위치.

    `action_token=AUTH_GATE`와 `auth_gate_detected` 플래그 중 이른 쪽(KL-08).
    """
    for i, step in enumerate(steps):
        if step.action_token == ACTION_AUTH_GATE or step.auth_gate_detected:
            return i
    return None


def _first_engagement_index(tokens: Sequence[str]) -> int | None:
    for i, token in enumerate(tokens):
        if token in TASK_ENGAGEMENT_TOKENS:
            return i
    return None


def _auth_gate_stage(tokens: Sequence[str], auth_idx: int | None, endpoint_idx: int | None) -> str:
    """04 §4 / 03 §7 — auth가 **언제** 걸렸는가.

    gate에 걸렸다는 사실이 이 값을 확정한다. 산출을 미루지 않는다(R2).

    - `NONE`: **관측했고 auth gate가 없었다.** endpoint 신호까지 갔는데
      auth를 만나지 않은 경우만이다(Δ10). 적극적 주장이므로 증거를 요구한다.
    - `UNDETERMINED`: 판정할 수 없었다 — auth 신호도 endpoint 신호도 없이
      경로가 끝났다. 중단·evidence defect가 여기 들어온다.
    - `AT_ENDPOINT`: endpoint 신호가 auth와 같거나 그보다 앞. 과업 경로를 다
      밟고 endpoint에서 인증이 요구된 경우.
    - `AFTER_TASK_SELECT`: auth 전에 과업 control을 이미 건드렸다.
    - `BEFORE_TASK_DISCOVERY`: auth 전에는 reveal/dismiss밖에 없었다 —
      과업 진입 control을 고르기도 전에 인증이 걸렸다.
    """
    if auth_idx is None:
        # 증거의 부재를 부재의 증거로 적지 않는다. endpoint까지 갔다는
        # 것이 확인돼야 "auth가 없었다"고 말할 수 있다.
        return AUTH_STAGE_NONE if endpoint_idx is not None else AUTH_STAGE_UNDETERMINED
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
    "정의를 제거하고 import로 교체해야 한다. **input_mode 필드를 W5B가 추가"
    "했으므로(A Δ9 CONDITIONAL 3종 판정에 필수) contracts.py 정본에도 반드시 "
    "반영돼야 한다** — 빠지면 CONDITIONAL 판정이 전부 불능이 된다. v3_runner에 "
    "__init__.py를 두지 않았다 — namespace package로 import된다.",
    "KL-02 [A Δ9로 부분 확정] 두 축을 구분한다. (a) activation_depth 귀속: "
    "A가 3항 기준으로 확정했고 action_token=SWITCH_TAB은 IN이다. W5B 구현은 "
    "처음부터 IN이었고 변경 없음. (b) menu_dependency/nav_container_depth의 "
    "REVEAL_TOKENS: A가 T-A-V3-STEP1-011 P-06에서 C 독해를 채택해 확정했다 — "
    "'action_token=SWITCH_TAB은 reveal 토큰이 아니다. menu_dependency 0.' "
    "W5B의 원래 근거(04 §4 nav_container_type 열거에 tab 없음)가 이 축에서 "
    "유효했다. 두 축 모두 확정됐으므로 이 항목은 더 이상 미해소가 아니다. "
    "다만 04 §5의 '…등'이라는 열린 표현 자체는 그대로 남아 있다.",
    "KL-03 04에는 action_token=ABSTAIN이 섞인 sequence의 derived 규칙이 없다. "
    "W5B는 '경로 불확정'이라는 토큰 정의(04 §2)를 근거로 파생 scalar 5개를 "
    "None으로 둔다. auth_gate_stage는 Δ10 이후 None이 아니라 UNDETERMINED다. "
    "sequence 2종은 raw 투영이므로 그 토큰을 남긴 채 반환한다. 다른 선택"
    "(불확정 지점 앞부분만 부분 derive)도 가능하며 04가 정하지 않았다.",
    "KL-04 빈 step sequence의 처리도 04에 없다. W5B는 '관측이 없다'를 "
    "'값이 0이다'로 바꾸지 않기 위해 count/bool 파생값을 None으로, "
    "auth_gate_stage를 UNDETERMINED로 둔다(Δ10).",
    "KL-05 **[A Δ15로 뒤집힘 — W5B 판단이 교정됐다]** 이전 구현은 "
    "flow_step_count에 action_token=ENDPOINT_REACHED를 포함했다. W5B 근거는 "
    "'같은 terminal 표지인 action_token=AUTH_GATE가 포함되는 이상 비대칭 "
    "처리할 근거가 없다'였다. A가 GAP-03에서 뒤집었다 — 근거가 있다. 04 §5가 "
    "'typing/submit/auth encounter 포함'이라고 **하나는 이름 붙이고 하나는 "
    "붙이지 않았다.** 또한 ENDPOINT_REACHED는 사용자가 한 일이 아니라 계측이 "
    "남긴 도달 표지이므로 'task-intent token'이 아니다. 현재 구현은 "
    "ENDPOINT_REACHED·action_token=ABSTAIN·DISMISS_OBSTRUCTION을 "
    "flow_step_count에서 "
    "제외하고 auth encounter는 포함한다. "
    "**결과적으로 flow_step_count == len(task_flow_sequence) 등식이 깨진다** — "
    "endpoint 도달 flow에서는 정확히 1 작고(task_flow에 ENDPOINT_REACHED가 "
    "남아 있으므로), gate terminal flow에서는 같다(auth는 양쪽 다 포함). "
    "등식이 성립하지 않는다는 것 자체가 정보다: 두 산출은 다른 질문에 답한다.",
    "KL-05b Δ9와 Δ15의 비대칭은 의도된 것이다. activation_depth는 "
    "action_token=AUTH_GATE를 제외하고 flow_step_count는 포함한다. 각각 SSOT "
    "문면에 근거한다 — 04 §5가 flow_step_count에만 auth encounter를 명시한다. "
    "대칭으로 '고치면' SSOT와 어긋난다. 이 항목은 미해소가 아니라 경고다.",
    "KL-06 04는 canonical 밖 token의 처리를 정하지 않는다. W5B는 ValueError를 "
    "올린다. 조용히 무시하면 없는 step이 depth에서 사라져 과소측정이 된다.",
    "KL-07 step_index가 강한 증가가 아닌 입력도 04에 규정이 없다. flow는 "
    "ordered sequence가 primary(04 §1)이므로 재정렬하지 않고 ValueError로 "
    "올린다 — 순서 붕괴는 수집기 결함이다.",
    "KL-08 04는 action_token=AUTH_GATE / action_token=ENDPOINT_REACHED를 "
    "token으로만 말하지만 02 §4 fact_flow_step에는 auth_gate_detected/"
    "endpoint_signal_detected 불리언이 따로 있다. W5B는 token과 flag 중 이른 "
    "쪽을 신호 위치로 쓴다. 두 신호가 충돌할 때 어느 쪽이 정본인지는 04·02 "
    "모두 정하지 않았다.",
    "KL-09 [A Δ9로 해소됨] activation_depth에 action_token=SUBMIT_QUERY 포함. "
    "A가 03 §6과 04 §5의 제외 목록 어디에도 submit이 없음을 확인하고, 03의 "
    "마지막 문장이 typing과 submit을 묶어 언급한 한 문장의 중의성이었을 뿐 "
    "충돌이 아니라고 재정했다. W5B 판단이 유지됐다. 미해소 아님.",
    "KL-10 [Δ10으로 개정] nav_container_depth의 'task control 노출'을 '첫 "
    "task-engagement token'으로 조작화했다. engagement가 없고 terminal도 없는 "
    "run은 이제 None이다 — 이전 구현은 prefix 전체 reveal 수를 셌으나 그것은 "
    "하한이지 값이 아니다. engagement는 없지만 terminal(gate 포함)에 닿은 "
    "run은 관측된 reveal 수를 낸다(R2가 gate에서 이 값이 확정된다고 못박음). "
    "04에 명시 없는 조작화다.",
    "KL-11 auth_gate_stage의 AT_ENDPOINT를 'endpoint 신호 index <= auth 신호 "
    "index'로 조작화했다. 04는 값의 이름만 주고 경계를 정의하지 않는다. "
    "BEFORE_TASK_DISCOVERY/AFTER_TASK_SELECT 경계도 TASK_ENGAGEMENT_TOKENS "
    "출현 여부로 W5B가 조작화한 것이다.",
    "KL-12 이 모듈은 sequence-derived 변수만 산출한다. 04 §4의 geometry/label/"
    "occlusion 계열(entry_x_norm, label_relation, task_control_occlusion, "
    "endpoint_status 등)과 legacy NED/IED/MPFED는 W5B claim 밖이다. FlowStep의 "
    "bbox_before/control_* 필드는 계약대로 받되 이 모듈에서 사용하지 않는다.",
    "KL-13 R2 적용 결과: 이 모듈 산출 중 gate 이후에만 관측 가능한 것은 없고 "
    "gate terminal에서 None이 되는 필드도 없다. 다만 gate run의 "
    "activation_depth/flow_step_count는 '완주에 필요한 depth'가 아니라 "
    "'gate까지 관측된 depth'다 — 절단된 관측이며 endpoint 도달 run의 같은 "
    "필드와 같은 분포로 취급하면 안 된다. 이 구분은 값이 아니라 분모로 "
    "표현되며(evidence-bearing n vs flow-evaluable n) 분모는 mart 몫이다.",
    "KL-14 R6-Q8 층 한정을 이 모듈은 (a) Python 상수 ACTION_* 접두사, "
    "(b) 주석/docstring/에러 메시지의 action_token= 한정, (c) 층을 지는 필드 "
    "이름으로 지킨다. 다만 두 sequence 필드의 **원소 문자열 자체**는 04 §2 "
    "canonical 값이라 한정 접두사를 붙일 수 없다 — 'AUTH_GATE'라는 원소를 "
    "가진 tuple이 그대로 나간다. 이 원소를 mart 컬럼이나 집계로 옮기는 쪽이 "
    "층 한정을 유지할 책임을 진다.",
    "KL-15 **[A 재정 필요]** Δ10은 '없음'을 적으려면 관측 증거를 요구한다. "
    "W5B는 menu_dependency를 bool|None으로 두고, reveal을 실제로 봤으면 True"
    "(양성 관측이라 항상 확정), 못 봤으면 terminal 도달 시에만 False, 아니면 "
    "None으로 낸다. **그런데 04 §4는 이 변수의 type을 bool로, §5는 "
    "'menu_dependency = 1 iff ...'로 적어 null 상태가 없다.** mart가 이걸 "
    "non-nullable bool 컬럼으로 저장하면 None이 False로 접히고 Δ10이 막으려는 "
    "결함이 저장층에서 그대로 재발한다. 04 type 개정 또는 nullable 저장 "
    "보장이 필요하다 — W5B는 지어내지 않고 올린다.",
    "KL-16 Δ8-R5 fixture_input_mode의 전체 열거를 W5B가 확보하지 못했다. "
    "A가 이름으로 준 DROPDOWN/MAP_PAN(포함)·FREE_TEXT(제외)·MIXED만 인지하고 "
    "'DROPDOWN/MAP_PAN 계열'의 '계열'을 임의 확장하지 않았다. 미인지 값과 "
    "미기록(None)은 판정 불능으로 처리하며 그 관측의 activation_depth 전체가 "
    "None이 된다. 실제 열거에 CALENDAR/PICKER 같은 값이 있다면 지금 구현은 "
    "그것을 전부 불능으로 접는다 — 열거 확보 후 INPUT_MODES_ACTIVATING 갱신 "
    "필요. MIXED를 step 층에서 불능으로 본 것도 W5B 판단이다(A는 '실제 사용 "
    "수단 기준'이라 했고, step 층 값이 MIXED면 그 해소가 안 된 상태로 읽었다).",
    "KL-17 [A R14] 이 모듈의 fixture 21개와 테스트는 W5B가 04를 읽고 만든 "
    "것이다. 테스트 통과는 **구현이 W5B의 독해와 일치한다**는 뜻이지 그 독해가 "
    "옳다는 뜻이 아니다. 조작화 판단을 코드에 묻지 않으려고 이 목록을 둔다. "
    "독립 검증은 SSOT 원문에서 따로 파생한 C의 fixture가 한다.",
    "KL-18 [A GAP-04 규약과 정합 확인] count 0의 의미. 이 모듈의 불변식은 "
    "'count 필드의 0은 언제나 세었고 0이다'이며 못 센 경우는 예외 없이 None"
    "이다. 빈 sequence는 전 필드 None(KL-04), input_mode 불능은 "
    "activation_depth None(KL-16), milestone 미도달은 nav_container_depth "
    "None(KL-10)으로 이미 갈린다. activation_depth·flow_step_count·"
    "forced_dismissal_count를 관측만 있으면 확정값으로 내는 근거는 이 셋이 "
    "정의상 milestone을 참조하지 않는 '관측된 run 안에서 센 수'라는 것이다 — "
    "반면 menu_dependency('endpoint 전')와 nav_container_depth('task control "
    "노출 전')는 milestone이 없으면 값 자체가 정의되지 않는다. 중단 run의 "
    "count가 하한이라는 사실은 값이 아니라 분모로 표현된다(KL-13). "
    "한 산출 안에서 결측 표현은 섞이지 않는다 — 수치/bool은 None, 범주는 "
    "UNDETERMINED뿐이고 0이나 빈 문자열을 결측으로 쓰지 않는다.",
)
