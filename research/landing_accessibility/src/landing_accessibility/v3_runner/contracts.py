"""v3 수집 파이프라인의 **동결된 계약** 자료형.

이 모듈은 W5A 뿐 아니라 v3_runner 의 다른 worker 들도 공유한다. 정의를 임의로 바꾸지 않는다.

근거:

* ``SSOTV3/00_SSOT_v3.0_CROSS_SERVICE_FLOW.md`` §4 §5 (Task Contract 규칙 · 본표본 n)
* ``SSOTV3/01_TASK_FAMILY_TARGET_FRAME_v3.0.md`` §2 §3
* ``SSOTV3/02_DATA_SCHEMA_v3.0.md`` ``dim_task_contract``
* ``research/landing_accessibility/control/v3/FINAL_MAIN50_MANIFEST.json``
  (A / ``T-A-V3-STEP1-FREEZE``, v3.0.2, body sha ``81d55db9…``)
  — ``stratum`` · ``is_pilot_5`` · ``collection_order`` · ``forbidden_actions``
* A / ``T-A-V3-STEP1-003`` (조작적 정의 사전등록, 02:58)
  — R3 ``task_role`` · R5 ``fixture_input_mode``


필드별 출처 — **계약인지 관측인지 섞지 않는다**
------------------------------------------------

====================== =============== =====================================================
필드                   출처            비고
====================== =============== =====================================================
``target_id``          동결 manifest   정본 ``targets[].target_id``
``family_id``          동결 manifest   정본 ``targets[].family_id``
``service``            동결 manifest   정본 ``service_name``
``starting_url``       동결 manifest   정본 ``starting_url`` (SSOTV3 CSV 는 ``official_entry_url``)
``frozen_task``        동결 manifest   정본 ``frozen_task`` (SSOTV3 CSV 는 ``matched_task``)
``task_instruction``   동결 manifest   정본 ``task_instruction``
``fixed_fixture``      동결 manifest   원문 문자열 보존. ``"없음"`` 도 그대로 둔다
``fixture_override``   동결 manifest   빈 문자열은 "override 없음" 이므로 ``None``
``endpoint_contract``  동결 manifest   원문 보존
``forbidden_actions``  동결 manifest   ``targets[].forbidden_actions``. 비어 있으면 적재 거부
``task_contract_hash`` **파생**        계약 자체의 sha256 (registry 모듈 docstring 이 정의)
``endpoint_contract_hash`` **파생**    ``endpoint_contract`` 원문 바이트의 sha256
``legacy_archetype``   동결 manifest   family 단위. **metadata 전용, 판정 금지**
``mobile_web_eligibility`` 동결 manifest ``PRECHECK_REQUIRED`` — precheck 전 REAL 수집 금지
``stratum``            동결 manifest   F1 시중/지방 · F5 ground/air. 그 외 family 는 ``"_"``
``is_pilot_5``         동결 manifest   ``pilot_5.targets`` 선언과 일치해야 한다
``collection_order``   동결 manifest   SSOTV3 registry 원본 순서. 재정렬 금지
``task_role``          동결 manifest   기본 ``PRIMARY``. manifest 에 없으면 PRIMARY 로 동결
``fixture_input_mode`` **관측값**      계약이 정하지 않는다. 수집 시 runner 가 채운다.
                                       ``activation_depth`` 계산의 **입력**이다 (아래 R5)
====================== =============== =====================================================

``fixture_input_mode`` 만 유일한 **관측 필드**다. 계약 동결 시점에는 언제나 ``None`` 이며,
그래서 ``task_contract_hash`` payload 에서 **제외**된다 (관측이 계약의 신원을 바꾸면 안 된다).


R3 ``task_role`` — 본표본 n 의 기계적 집행
------------------------------------------

``PRIMARY`` | ``SECONDARY_REPEATED``.

F1 은행 10곳에는 '잔액/계좌조회' secondary task 가 붙을 수 있다. 00 §4 · 01 §3 이 이미
"본표본 n 을 늘리지 않는다" 를 정했고, 이 필드는 그것을 스키마로 **집행**한다 —
construct 변경이 아니라 스키마 추가다.

* mart 의 **모든 관측 행**이 ``task_role`` 을 갖는다.
* family-level 집계와 본표본 n 은 ``task_role == 'PRIMARY'`` 로만 필터한다.
* ``SECONDARY_REPEATED`` 는 **별도 task_id 이자 별도 행**이며 본표본 n 을 늘리지 않는다.
* 각 집계 산출물에 **필터 조건 문자열을 남긴다** — "적용했다" 는 주장이 아니라 조건 자체를
  기록한다. 문자열은 :data:`~landing_accessibility.v3_runner.registry.PRIMARY_SAMPLE_FILTER`.


R5 ``fixture_input_mode`` — fixture 는 문자열이 아니라 의미 명세다
------------------------------------------------------------------

``FREE_TEXT`` | ``DROPDOWN`` | ``MIXED`` | ``MAP_PAN`` | ``OTHER`` | ``None``(미관측).

같은 fixture(예: F4 의 "지역=서울특별시 중구; 진료과=내과; 위치권한 허용 안 함")를
지도서비스와 공공 전문검색에 같은 방식으로 넣을 수 없다. 입력수단 차이를 절차의 모호함으로
두면 target 마다 다른 조작이 되지만, **관측 변수로 만들면 그 차이 자체가 데이터**가 되고
v3 가 재려는 cross-service 구조 변이의 일부가 된다.

조작화(실제 구현은 runner 쪽 — W1/W5F 몫):

* 자유입력 → 문자열 그대로 (``FREE_TEXT``)
* 드롭다운/선택지 → 해당 값 선택. 정확히 같은 항목이 없으면 **가장 상위의 포함관계 항목**을
  고르고 그 사실을 기록 (``DROPDOWN``)
* 지도 pan/zoom 으로만 지역 지정이 가능하면 그것도 유효한 수단 (``MAP_PAN``)
* 자유입력과 선택지가 **둘 다** 있으면 실제로 쓴 수단은
  **task path 상 서비스가 먼저 제시하는 수단** — 수집자가 고르지 않는다.
  관측 단위 요약값이 ``MIXED`` 가 되는 것은 **한 관측 안에 서로 다른 수단이 섞였다**는
  뜻이지 "애매하다/판정 불가" 가 아니다.

fixture 를 쓰는 **F2 · F3 · F4 · F5 전부**에 적용된다.

.. important::
   **이 필드는 기록용 메타데이터가 아니라 파생값 계산의 입력이다.**
   A ``T-A-V3-STEP1-006`` (Δ9) 의 ``activation_depth`` 18종 귀속 중 3종이 여기에 의존한다 —
   ``SELECT_ORIGIN`` · ``SELECT_DESTINATION`` · ``SELECT_DATE`` 는 CONDITIONAL 이다.

   * ``DROPDOWN`` / ``MAP_PAN`` 계열 → ``activation_depth`` **포함**
     (값을 정하려면 control 을 활성화해야 한다)
   * ``FREE_TEXT`` → ``activation_depth`` **제외**, ``flow_step_count`` 에만 반영
     (타이핑이므로)
   * ``MIXED`` → 그 step 에서 **실제로 사용한 수단** 기준

   그래서 이 값을 "그냥 참고값" 으로 읽고 결측 처리하면 ``activation_depth`` 가 **조용히
   틀린다.** 3탭 달력을 강제하는 서비스와 텍스트 한 줄이면 되는 서비스는 사용자에게 실제로
   다른 조작량을 요구하며, 입력수단에 따라 depth 가 갈리는 것은 결함이 아니라 측정이다.

.. note::
   **관측 단위 요약값 vs step 단위 실제 수단.**
   한 flow 안에서 출발지는 dropdown, 날짜는 calendar 인 경우가 실재하므로 관측 단위 값
   하나로는 표현되지 않는다. ``TaskContract.fixture_input_mode`` 는 **관측 단위 요약값**이고,
   **step 단위 실제 수단은 ``FlowStep.input_mode`` 가 갖는다 (W5B 소유).**
   두 값이 갈릴 수 있고 **그것이 정상**이다 — 불일치를 결함으로 오인하지 않는다.
   ``activation_depth`` 의 CONDITIONAL 판정은 step 단위 값을 쓴다.
"""

from __future__ import annotations

from dataclasses import dataclass

#: R3 task_role 허용값.
TASK_ROLE_PRIMARY = "PRIMARY"
TASK_ROLE_SECONDARY_REPEATED = "SECONDARY_REPEATED"
TASK_ROLES: tuple[str, ...] = (TASK_ROLE_PRIMARY, TASK_ROLE_SECONDARY_REPEATED)

#: R5 fixture_input_mode 허용값 (``None`` = 아직 관측되지 않음).
FIXTURE_INPUT_MODES: tuple[str, ...] = (
    "FREE_TEXT",
    "DROPDOWN",
    "MIXED",
    "MAP_PAN",
    "OTHER",
)


@dataclass(frozen=True)
class TaskContract:
    """수집 **전에** 동결된 과업 계약. v3 00 §5 / 02 dim_task_contract."""

    target_id: str
    family_id: str
    service: str
    starting_url: str
    frozen_task: str  # v3 01 §2 matched_task
    task_instruction: str
    fixed_fixture: str  # "없음" 이면 fixture 없음. 문자열 그대로 보존
    fixture_override: str | None
    endpoint_contract: str
    forbidden_actions: tuple[str, ...]
    task_contract_hash: str  # 이 계약 자체의 sha256
    endpoint_contract_hash: str  # endpoint_contract 원문 바이트의 sha256
    legacy_archetype: str | None = None  # metadata 전용. 판정에 쓰지 않는다
    mobile_web_eligibility: str = "PRECHECK_REQUIRED"
    stratum: str | None = None  # F1: 시중/지방, F5: ground/air. 사전등록된 층
    is_pilot_5: bool = False
    collection_order: int | None = None
    task_role: str = TASK_ROLE_PRIMARY  # PRIMARY | SECONDARY_REPEATED (R3)
    # R5. **관측값** — 계약이 미리 정하지 않는다. 수집 시 runner 가 채우며
    # task_contract_hash 에는 들어가지 않는다. 기록용이 아니라 activation_depth 파생의
    # 입력이며, step 단위 실제 수단은 FlowStep.input_mode(W5B)가 갖는다.
    fixture_input_mode: str | None = None


@dataclass(frozen=True)
class FlowStep:
    """`02 §4 fact_flow_step` — raw ordered action 한 건. derived 값은 여기 없다.

    `action_token` 은 `04 §2` canonical 18종 중 하나이며 **action_token 층**의
    값이다 (R6-Q8). `endpoint_status` 층의 값을 여기에 넣지 않는다.

    정본 위치 확정 (W5K / SEAM 2, A 판정)
    -------------------------------------
    이 dataclass 는 세 곳에 중복 정의돼 있었다 — `runner.py`(W5F) · `flow.py`(W5B) ·
    여기. A 가 ``contracts.py`` 를 정본으로 확정했고, ``flow.py`` 의 ``input_mode``
    추가를 승인했다. 나머지 두 곳은 이 정의를 import 한다.
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
    #: Δ8-R5 ``fixture_input_mode`` 의 **step 단위** 값 (W5B 추가, A 승인).
    #: CONDITIONAL 3종(``SELECT_ORIGIN``·``SELECT_DESTINATION``·``SELECT_DATE``)의
    #: ``activation_depth`` 귀속 판정에만 쓴다. ``None`` 은 미기록 → 판정 불능이다.
    #:
    #: 관측 단위(:attr:`TaskContract.fixture_input_mode`)가 아니라 step 단위인 이유:
    #: 한 flow 안에서 출발지는 dropdown, 날짜는 calendar 인 경우가 실재하고 관측 단위
    #: 스칼라 하나로는 그걸 표현할 수 없다. 기본값이 있어 기존 호출부는 그대로 동작한다.
    #:
    #: .. important::
    #:    이 필드는 **판정 지점까지 실제로 도달해야** 의미가 있다. 값을 채우지 않고
    #:    ``flow.normalize_flow`` 에 넘기면 CONDITIONAL 3종이 전부 판정 불능이 되고
    #:    ``activation_depth`` 가 조용히 ``None`` 으로 접힌다 — 그것은 결측이 아니라
    #:    배선 누락이다 (W5K SEAM 2).
    input_mode: str | None = None
