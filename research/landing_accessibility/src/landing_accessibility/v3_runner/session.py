"""W5H — `SessionDriver` 구현. **fixture 전용**이며 실사이트를 여는 경로가 없다.

## 이 파일이 하는 일

`runner.py`(W5F)가 Protocol 로만 잡아둔 세션 경계 하나를 채운다.

    capture_surface(contract) -> Sequence[SurfaceObservation]
    activate(action)          -> RawTransition

`03 §1` 의 공통 모바일 환경으로 fresh context 를 열고, `03 §3` 의 scroll-only surface
capture 를 `S0`..`Sn` 으로 낸다 (스크롤되지 않는 문서면 `S0` 하나다 — v3 fixture 13종이
그렇다, known limitation 참조). 그리고 control 하나를 활성화해 before/after 를 통째로
담은 `RawTransition` 을 낸다. **판정은 하지 않는다** — derived scalar 는 전부 W5B/W5C/W5D
경계의 것이고, 여기서 나가는 것은 raw 관측과 evidence payload 뿐이다.

## 재사용한 것 (읽기 전용 — 수정하지 않았다)

* `engine/l0_collector.py` — `PROBE_JS` · `VIEWPORT_WIDTH/HEIGHT` · `DEVICE_SCALE_FACTOR` ·
  `LOCALE` · `TIMEZONE_ID` · `MOBILE_USER_AGENT` · `SETTLE_MS` · `_COMPUTED_CSS_JS` ·
  `_COMPUTED_CSS_PROPERTIES` · `L0Collector._ax_tree`.
  환경 상수를 여기서 다시 적지 않는다 — 두 벌이 되면 조용히 갈라진다.
* `engine/l0_probe.js` — `page.evaluate(PROBE_JS, "FIXTURE")` 로만 호출한다.
* `engine/firewall.assert_navigation_allowed` — 항해 직전 강제 통과. 아래 참조.
* `v3_runner/discovery.FixtureInputMode` (W5D1) — Δ8-R5 어휘 5값. 다시 정의하지 않는다.

## 실사이트를 못 여는 이유 — 정책이 아니라 구조

`_resolve_fixture_url()` 은 `assert_navigation_allowed(ExecutionMode.FIXTURE, ...)` 를
거치지 않고는 URL 을 돌려주지 않는다. `FIXTURE` 모드는 `file://` 그리고 `fixture_root`
안쪽만 허용하며 **어떤 scope 로도 완화되지 않는다** (firewall `assert_mode_allowed` 는
`FIXTURE` 에 scope 를 받지 않는다). 이 드라이버에는 `execution_mode` 를 받는 인자가
없고 모듈 안에 `ExecutionMode.REAL_TARGET` 이 등장하지 않는다.

그것과 **다른 구멍**이 하나 더 있다 — firewall 은 *내가 여는* URL 만 본다. fixture 안의
링크나 스크립트가 스스로 밖으로 나가는 경로는 그 검사에 걸리지 않으므로, 컨텍스트 단에서
`NETWORK_ROUTE_PATTERNS` 를 abort 로 라우팅해 한 겹 더 끊었다.

## credential 을 못 넣는 이유 — 역시 구조

1. `PlannedAction`(W5F)에는 **입력할 값을 담는 필드가 없다.** 호출자가 이 드라이버에
   비밀번호를 건네줄 자리 자체가 없다. 넣는 값은 모듈 상수 `SAFE_PROBE_TEXT` 하나다.
2. 이 모듈 전체에서 `Page.fill` 호출부는 `_fill_safe_text()` **한 곳뿐**이고, 그 함수의
   첫 문장이 `is_credential_field()` 거부다. `type`/`press_sequentially`/`insert_text`/
   `keyboard` 경로는 아예 쓰지 않는다.
3. `is_credential_field()` 는 어휘 매칭에 기대지 않는다 — **password 입력을 품고 있는
   form/dialog 안의 모든 입력**을 credential 영역으로 본다. 아이디 칸이 `uid` 처럼
   무해해 보이는 이름을 달고 있어도 잡힌다.

login submit · OTP · CAPTCHA · 송금 · 장바구니 · 주문 · 결제 · 예약 · 좌석선택 ·
외부앱 실행 은 이 파일에 코드 경로가 없다. `activate` 가 할 수 있는 일은 click ·
select_option · (안전 필드 한정) fill 셋뿐이며, 그 셋도 `04 §2` canonical token 을
runner 가 먼저 통과시킨 뒤에만 도달한다.

## input_mode 는 기록용 메타데이터가 아니다 (Δ8-R5)

`SELECT_ORIGIN` / `SELECT_DESTINATION` / `SELECT_DATE` 의 `activation_depth` 포함 여부를
가르는 **관측 입력**이다. A 규칙은 "서비스가 먼저 제시하는 수단을 쓴다 — 수집자가
고르지 않는다" 이므로, 이 드라이버는 control 의 구조(tag/type/role/연결된 목록)만 보고
수단을 정하며 라벨/문구로 추측하지 않는다. 관측된 5값은 `control_facts` 에 그대로
남고(`observed_input_mode`), `RawTransition.input_mode` 에는 Δ9 어휘 4값만 실린다 —
자세한 사정은 `RECORDED_INPUT_MODES` 주석에 적었다.

## known limitation — 측정으로 확인한 것과 판단으로 남긴 것을 나눈다

`KNOWN_LIMITATIONS` 에 기계가 읽는 형태로 있다. 요약하면 다섯이다.

* **ax_node 조인이 없다 (측정)** — `l0_probe.js` 는 accessible name 을 계산하지 않고
  이름의 *출처* 만 낸다. 계산된 이름은 `l0_collector._ax_tree` 의 CDP slim node 에만
  있고 그 노드는 selector 가 아니라 `backendDOMNodeId` 로 키잉된다. selector ↔
  backendDOMNodeId 를 잇는 코드가 base 에 없다. 그래서 W5C `measure_surface` 가
  요구하는 `task_control["ax_node"]` 를 **이 드라이버는 채울 수 없다.** DOM 속성에서
  이름을 추정하면 `visible_label_text` 와 출처가 겹쳐 `00 §8` 의 분리가 무너지므로
  추정하지 않는다 — 자리는 `control_facts["ax_node"] = None` 으로 두고
  `ax_node_join_status` 에 이유를 남긴다. 조인이 생기면 그 자리에 꽂힌다.
* **v3 fixture 13종은 전부 스크롤되지 않는다 (측정)** — 13/13 이
  `scrollHeight == clientHeight == 844`, `body{overflow:hidden}` 이다. 그래서 **이
  집합에서는 `S0` 하나만 나온다.** scroll 열거 코드 경로 자체는 있고 동작한다 —
  스크롤 가능한 문서에서는 `S0..Sn` 이 실제로 만들어진다(회귀가 확인한다).
  이 파일은 `page.evaluate(window.scrollTo)` 로 자기 안에서 열거하므로
  `l0_collector.py` · `l0_probe.js` 를 고칠 필요가 없었다(두 파일은 base 와 바이트 동일).
* **`OTHER` 는 `RawTransition.input_mode` 에 실리지 않는다 (측정)** — Δ8-R5 어휘는
  5값인데 W5F `evidence.INPUT_MODE_VALUES` 는 4값이다. `RECORDED_INPUT_MODES` 주석 참조.
* **`MAP_PAN` 은 관측되지만 구동되지 않는다 (판단)** — 지도 pan/zoom 을 흉내내는 코드
  경로를 만들지 않기로 했다. 관측은 남고 활성화는 `MAP_PAN_NOT_DRIVABLE` 로 실패한다.
* **scout↔replay 사이 세션 리셋 훅이 Protocol 에 없다 (측정)** — `runner.run()` 은
  scout 가 끝난 화면 그대로 replay 로 들어간다. v3 fixture 13종의 핸들러가 전부
  멱등이라 지금은 통과하지만 그것은 fixture 의 성질이지 드라이버의 보장이 아니다.
"""

from __future__ import annotations

import datetime as _dt
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from types import TracebackType
from typing import Any
from urllib.parse import urlparse

from landing_accessibility.engine.firewall import (
    ExecutionMode,
    assert_navigation_allowed,
)
from landing_accessibility.engine.l0_collector import (
    _COMPUTED_CSS_JS,
    _COMPUTED_CSS_PROPERTIES,
    DEVICE_SCALE_FACTOR,
    LOCALE,
    MOBILE_USER_AGENT,
    PROBE_JS,
    SETTLE_MS,
    TIMEZONE_ID,
    VIEWPORT_HEIGHT,
    VIEWPORT_WIDTH,
    L0Collector,
)
from landing_accessibility.v3_runner.discovery import FixtureInputMode
from landing_accessibility.v3_runner.evidence import INPUT_MODE_VALUES, EvidencePayload
from landing_accessibility.v3_runner.runner import (
    DEPTH_CONDITIONAL_TOKENS,
    PlannedAction,
    RawTransition,
    SurfaceObservation,
    TaskContract,
)

__all__ = [
    "AX_NODE_JOIN_STATUS",
    "DEFAULT_SCROLL_POLICY",
    "KNOWN_LIMITATIONS",
    "RECORDED_INPUT_MODES",
    "SAFE_PROBE_TEXT",
    "CredentialInputRefusedError",
    "EnvironmentRecord",
    "FixtureSessionDriver",
    "ScrollPolicy",
    "SessionError",
    "SessionNotOpenError",
    "is_credential_field",
    "observe_input_mode",
]


# ---------------------------------------------------------------------------
# 예외
# ---------------------------------------------------------------------------


class SessionError(RuntimeError):
    """세션 드라이버 실패의 뿌리."""


class SessionNotOpenError(SessionError):
    """`activate` 가 열린 페이지 없이 호출됐다.

    fail-closed 다 — 여기서 조용히 `starting_url` 로 항해해버리면 "어느 상태에서
    눌렀는가" 가 기록에서 사라진다.
    """


class CredentialInputRefusedError(SessionError):
    """`03 §7` — credential 계열 필드에 값을 넣으려 했다. 실행 전에 멈춘다."""


# ---------------------------------------------------------------------------
# `03 §3` scroll 정책 — discovery/exposure 변수다. activation depth 가 아니다.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ScrollPolicy:
    """고정 scroll 정책. **수집 파라미터이며 해석 임계값이 아니다.**

    `step_ratio` 는 viewport 높이의 배수다(1.0 = 한 화면씩). `max_states` 는 S0 을
    포함한 상한이고, 문서가 더 길면 `truncated` 로 남는다 — 조용히 자르지 않는다.
    """

    step_ratio: float = 1.0
    max_states: int = 8
    settle_ms: int = SETTLE_MS

    def __post_init__(self) -> None:
        if self.step_ratio <= 0:
            raise ValueError("step_ratio 는 0 보다 커야 한다")
        if self.max_states < 1:
            raise ValueError("max_states 는 최소 1 이다 — S0 은 언제나 있다")

    def as_record(self) -> dict[str, Any]:
        return {
            "step_ratio": self.step_ratio,
            "max_states": self.max_states,
            "settle_ms": self.settle_ms,
        }


DEFAULT_SCROLL_POLICY = ScrollPolicy()


# ---------------------------------------------------------------------------
# credential 방어 — 어휘가 아니라 구조를 본다
# ---------------------------------------------------------------------------

#: known limitation 의 기계가 읽는 정본. `basis` 는 `MEASURED`(관측으로 확인) 와
#: `JUDGEMENT`(만들지 않기로 한 결정) 를 구분한다 — 둘을 섞으면 "확인했다" 가
#: "그렇게 두기로 했다" 를 덮는다.
KNOWN_LIMITATIONS: tuple[Mapping[str, str], ...] = (
    {
        "id": "W5H-L1-AX-JOIN-ABSENT",
        "basis": "MEASURED",
        "statement": (
            "selector ↔ backendDOMNodeId 조인이 base 에 없어 W5C measure_surface 가 요구하는 "
            "task_control['ax_node'] 를 채울 수 없다. 자리는 control_facts['ax_node']=None 이고 "
            "ax_node_join_status 에 이유가 남는다. DOM 속성으로 이름을 추정하지 않는다."
        ),
    },
    {
        "id": "W5H-L2-V3-FIXTURES-DO-NOT-SCROLL",
        "basis": "MEASURED",
        "statement": (
            "fixtures/v3 13종은 13/13 이 scrollHeight==clientHeight==844, body{overflow:hidden} "
            "이라 이 집합에서는 S0 하나만 나온다. scroll 열거 경로 자체는 동작하며 스크롤 "
            "가능한 문서에서 S0..Sn 을 만든다. engine/l0_collector.py · l0_probe.js 는 수정하지 "
            "않았다(base 와 바이트 동일)."
        ),
    },
    {
        "id": "W5H-L3-OTHER-OUTSIDE-W5F-VOCABULARY",
        "basis": "MEASURED",
        "statement": (
            "Δ8-R5 input_mode 어휘는 5값(OTHER 포함)인데 W5F evidence.INPUT_MODE_VALUES 는 "
            "4값이다. RawTransition.input_mode 에는 4값만 싣고 관측 5값은 "
            "control_facts['observed_input_mode'] 에 원본 그대로 남긴다."
        ),
    },
    {
        "id": "W5H-L4-MAP-PAN-NOT-DRIVEN",
        "basis": "JUDGEMENT",
        "statement": (
            "지도 pan/zoom 구동 경로를 만들지 않았다. MAP_PAN 은 관측되지만 활성화는 "
            "MAP_PAN_NOT_DRIVABLE 로 실패한다. v3 fixture 13종에 지도 위젯이 없어 필요성도 "
            "확인되지 않았다."
        ),
    },
    {
        "id": "W5H-L5-NO-RESET-HOOK-BETWEEN-SCOUT-AND-REPLAY",
        "basis": "MEASURED",
        "statement": (
            "SessionDriver Protocol 에 세션 리셋 훅이 없어 runner.run() 은 scout 가 끝난 화면 "
            "그대로 replay 로 들어간다. v3 fixture 13종 핸들러가 전부 멱등이라 현재는 통과하지만 "
            "그것은 fixture 의 성질이지 드라이버의 보장이 아니다. reset_session() 을 두었다."
        ),
    },
)

#: W5C `measure_surface` 가 요구하는 AX slim node 의 자리. 채울 수 없는 이유는
#: `KNOWN_LIMITATIONS` 의 `W5H-L1-AX-JOIN-ABSENT` 에 있다.
AX_NODE_JOIN_STATUS = "AX_NODE_ABSENT_NO_SELECTOR_TO_BACKEND_NODE_JOIN"

#: 안전 입력에 넣는 **유일한** 문자열. 호출자가 값을 정할 자리는 이 모듈에 없다.
SAFE_PROBE_TEXT = "조회"

#: 한 조작의 상한. fixture 는 네트워크가 없으니 즉시 끝난다 — 이 상한은 "숨겨진
#: control 을 눌러보려다 30초를 기다리는" 기본값을 막기 위한 수집 파라미터다.
ACTION_TIMEOUT_MS = 2_000

#: 컨텍스트 단 네트워크 차단 패턴. fixture 안의 링크/스크립트가 밖으로 나가는 경로를
#: 끊는다 — firewall 의 URL 검사(내가 여는 URL)와 **다른 구멍**을 막는 것이다.
NETWORK_ROUTE_PATTERNS: tuple[str, ...] = ("http://**", "https://**", "ws://**", "wss://**")

#: `type` 이 이 집합이면 무조건 credential 이다.
CREDENTIAL_INPUT_TYPES: frozenset[str] = frozenset({"password"})

#: `autocomplete` 토큰. 브라우저가 자격증명으로 취급하겠다고 선언한 필드다.
CREDENTIAL_AUTOCOMPLETE: frozenset[str] = frozenset(
    {
        "current-password",
        "new-password",
        "one-time-code",
        "cc-number",
        "cc-csc",
        "cc-exp",
        "cc-exp-month",
        "cc-exp-year",
    }
)

#: 이름/식별자/라벨에 나타나는 자격증명·개인정보 어휘. **보조 신호다** — 이것만으로
#: 판단하지 않는다(아래 `password_scope` 가 구조 신호이고 이쪽이 보강이다).
_CREDENTIAL_TOKEN_RE = re.compile(
    r"(password|passwd|pwd|passcode|secret|otp|one[-_ ]?time|verification[-_ ]?code|"
    r"cvc|cvv|card[-_ ]?number|account[-_ ]?number|resident[-_ ]?registration|ssn|"
    r"비밀번호|암호|인증번호|일회용|주민등록|카드번호|계좌번호|보안코드)",
    re.IGNORECASE,
)


def is_credential_field(facts: Mapping[str, Any]) -> bool:
    """이 필드에 값을 넣는 것이 금지된 credential 입력인가.

    네 신호를 OR 로 본다. 마지막 것이 핵심이다 — **password 입력을 품은 form/dialog
    안쪽의 모든 입력**을 자격증명 영역으로 본다. 로그인 폼의 아이디 칸이 `uid`,
    `email`, `member` 같은 무해한 이름을 달고 있어도 어휘 목록을 늘리지 않고 잡힌다.
    "무엇을 금지어로 적었는가" 에 안전이 걸리지 않게 하는 것이 목적이다.
    """
    input_type = str(facts.get("type") or "").strip().lower()
    if input_type in CREDENTIAL_INPUT_TYPES:
        return True
    autocomplete = str(facts.get("autocomplete") or "").strip().lower()
    if autocomplete in CREDENTIAL_AUTOCOMPLETE:
        return True
    for key in ("name", "id", "aria_label", "placeholder", "label_text"):
        value = facts.get(key)
        if value and _CREDENTIAL_TOKEN_RE.search(str(value)):
            return True
    return bool(facts.get("password_scope"))


# ---------------------------------------------------------------------------
# Δ8-R5 input_mode 관측
# ---------------------------------------------------------------------------

#: `RawTransition.input_mode` 에 실을 수 있는 값 = W5F `evidence.INPUT_MODE_VALUES`
#: (`DROPDOWN`/`MAP_PAN`/`FREE_TEXT`/`MIXED`). Δ8-R5 어휘는 `OTHER` 를 포함한 **5값**
#: 이지만 W5F 의 `_validated_input_mode` 는 4값 밖을 `RunnerError` 로 거부한다.
#:
#: 이 드라이버의 처리: 관측된 5값은 언제나 `control_facts["observed_input_mode"]` 에
#: 원본 그대로 남고, `RawTransition.input_mode` 에는 Δ9 4값일 때만 싣는다.
#: `OTHER` 를 `FREE_TEXT` 로 바꾸지 않고(발명), 관측 사실을 지우지도 않는다(은폐).
#: 어휘 폭 불일치 자체는 W5H 가 판단할 것이 아니라 A/코디네이터에 보고할 사항이다.
RECORDED_INPUT_MODES: frozenset[str] = frozenset(INPUT_MODE_VALUES)


def observe_input_mode(facts: Mapping[str, Any]) -> FixtureInputMode | None:
    """control 의 **구조 신호만** 보고 입력수단을 관측한다 (Δ8-R5).

    A 규칙 "서비스가 먼저 제시하는 수단을 쓴다 — 수집자가 고르지 않는다" 를 코드로
    옮기면 이렇게 된다: 라벨·문구·과업 의도를 보지 않고 tag/type/role/연결된 목록만
    본다. 신호가 하나도 없으면 `None` 이다 — `OTHER` 로 단정하지 않는다
    (`OTHER` 는 "버튼/링크류로 관측됐다" 이지 "모른다" 가 아니다).

    W5D1 `_infer_fixture_input_mode` 와 같은 어휘를 쓰되 관측 입력이 다르다 — 저쪽은
    probe candidate mapping(`type` 이 거의 없다)을, 이쪽은 실제 DOM 요소의 `type` ·
    `multiple` · `list` 연결까지 본다. 그래서 이쪽이 `FREE_TEXT`/`DROPDOWN`/`MIXED`
    를 실제로 구분할 수 있다.
    """
    tag = str(facts.get("tag") or "").strip().lower()
    role = str(facts.get("role") or "").strip().lower()
    input_type = str(facts.get("type") or "").strip().lower()

    # `<input list=...>` 는 자유입력과 목록선택이 한 control 에 같이 있다 = MIXED.
    if tag == "input" and facts.get("has_datalist"):
        return FixtureInputMode.MIXED
    if role == "combobox":
        return FixtureInputMode.MIXED
    if tag == "select" or role in ("listbox", "menu"):
        return FixtureInputMode.DROPDOWN
    if tag in ("textarea",):
        return FixtureInputMode.FREE_TEXT
    if tag == "input" and input_type not in (
        "submit",
        "button",
        "checkbox",
        "radio",
        "hidden",
        "image",
        "reset",
        "file",
    ):
        return FixtureInputMode.FREE_TEXT
    if role == "application" or "map" in tag:
        # 구조적으로 지도 위젯임이 명시된 경우만. "지도" 라는 라벨로 추측하지 않는다.
        return FixtureInputMode.MAP_PAN
    if tag in ("button", "a", "summary") or role in ("button", "link", "tab", "menuitem"):
        return FixtureInputMode.OTHER
    return None


# ---------------------------------------------------------------------------
# `03 §1` 환경 기록 — 선언값과 렌더값을 **둘 다** 남긴다
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class EnvironmentRecord:
    """`03 §1` 이 기록하라고 한 것 + 그 선언이 실제로 걸렸는지의 관측값.

    선언만 남기면 "viewport 를 390 으로 설정했다" 가 "390 으로 렌더됐다" 를 증명하지
    못한다. 두 값을 나란히 두고 `matches()` 로 대조한다.
    """

    requested_url: str
    final_url: str
    collected_at: str
    viewport_width_configured: int
    viewport_height_configured: int
    viewport_width_rendered: int | None
    viewport_height_rendered: int | None
    device_pixel_ratio: float | None
    user_agent_configured: str
    user_agent_rendered: str | None
    locale_configured: str
    locale_rendered: str | None
    timezone_configured: str
    timezone_rendered: str | None
    is_mobile: bool
    has_touch: bool
    max_touch_points: int | None
    fresh_context: bool
    stored_cookie_count: int
    login_performed: bool
    execution_mode: str

    def matches(self) -> dict[str, bool]:
        """선언 ↔ 렌더 대조 결과. 관측 못 한 항목은 `False` 다 (미확인은 통과가 아니다)."""
        return {
            "viewport_width": self.viewport_width_rendered == self.viewport_width_configured,
            "viewport_height": self.viewport_height_rendered == self.viewport_height_configured,
            "user_agent": self.user_agent_rendered == self.user_agent_configured,
            "locale": self.locale_rendered == self.locale_configured,
            "timezone": self.timezone_rendered == self.timezone_configured,
        }

    def as_record(self) -> dict[str, Any]:
        return {
            "requested_url": self.requested_url,
            "final_url": self.final_url,
            "collected_at": self.collected_at,
            "viewport_width_configured": self.viewport_width_configured,
            "viewport_height_configured": self.viewport_height_configured,
            "viewport_width_rendered": self.viewport_width_rendered,
            "viewport_height_rendered": self.viewport_height_rendered,
            "device_pixel_ratio": self.device_pixel_ratio,
            "user_agent_configured": self.user_agent_configured,
            "user_agent_rendered": self.user_agent_rendered,
            "locale_configured": self.locale_configured,
            "locale_rendered": self.locale_rendered,
            "timezone_configured": self.timezone_configured,
            "timezone_rendered": self.timezone_rendered,
            "is_mobile": self.is_mobile,
            "has_touch": self.has_touch,
            "max_touch_points": self.max_touch_points,
            "fresh_context": self.fresh_context,
            "stored_cookie_count": self.stored_cookie_count,
            "login_performed": self.login_performed,
            "execution_mode": self.execution_mode,
            "declared_vs_rendered": self.matches(),
        }


# ---------------------------------------------------------------------------
# 브라우저 안에서 도는 관측 스크립트 — 전부 읽기 전용이다
# ---------------------------------------------------------------------------

_ENV_JS = """
() => ({
  inner_width: window.innerWidth,
  inner_height: window.innerHeight,
  device_pixel_ratio: window.devicePixelRatio,
  user_agent: navigator.userAgent,
  language: navigator.language,
  timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
  max_touch_points: navigator.maxTouchPoints,
  url: location.href,
})
"""

_SCROLL_STATE_JS = """
() => ({
  scroll_x: window.scrollX,
  scroll_y: window.scrollY,
  scroll_height: document.documentElement.scrollHeight,
  client_height: document.documentElement.clientHeight,
  body_scroll_height: document.body ? document.body.scrollHeight : null,
})
"""

_SCROLL_TO_JS = "(y) => { window.scrollTo(0, y); return window.scrollY; }"

#: 한 control 의 **관측 사실**. 판정하지 않는다 — 값만 낸다.
#: `password_scope` 가 credential 방어의 구조 신호다 (아래 `is_credential_field`).
_CONTROL_FACTS_JS = """
(selector) => {
  const el = document.querySelector(selector);
  if (!el) return { found: false, selector };
  const cs = getComputedStyle(el);
  const r = el.getBoundingClientRect();
  const box = { x: +r.x.toFixed(2), y: +r.y.toFixed(2),
                w: +r.width.toFixed(2), h: +r.height.toFixed(2) };
  const vw = window.innerWidth, vh = window.innerHeight;
  const ow = Math.max(0, Math.min(r.x + r.width, vw) - Math.max(r.x, 0));
  const oh = Math.max(0, Math.min(r.y + r.height, vh) - Math.max(r.y, 0));
  const cx = Math.min(Math.max(r.x + r.width / 2, 0), Math.max(vw - 1, 0));
  const cy = Math.min(Math.max(r.y + r.height / 2, 0), Math.max(vh - 1, 0));
  const top = document.elementFromPoint(cx, cy);
  const listId = el.getAttribute ? el.getAttribute('list') : null;
  const scope = el.closest ? el.closest('form,dialog,[role=dialog],fieldset') : null;
  let label = null;
  if (el.id) {
    const lab = document.querySelector('label[for="' + CSS.escape(el.id) + '"]');
    if (lab) label = (lab.textContent || '').replace(/\\s+/g, ' ').trim();
  }
  if (!label && el.closest) {
    const wrap = el.closest('label');
    if (wrap) label = (wrap.textContent || '').replace(/\\s+/g, ' ').trim();
  }
  return {
    found: true,
    selector,
    tag: el.tagName.toLowerCase(),
    type: el.getAttribute ? el.getAttribute('type') : null,
    role: el.getAttribute ? el.getAttribute('role') : null,
    id: el.id || null,
    name: el.getAttribute ? el.getAttribute('name') : null,
    autocomplete: el.getAttribute ? el.getAttribute('autocomplete') : null,
    placeholder: el.getAttribute ? el.getAttribute('placeholder') : null,
    aria_label: el.getAttribute ? el.getAttribute('aria-label') : null,
    aria_expanded: el.getAttribute ? el.getAttribute('aria-expanded') : null,
    aria_hidden: el.getAttribute ? el.getAttribute('aria-hidden') : null,
    label_text: label,
    visible_text: (el.textContent || '').replace(/\\s+/g, ' ').trim() || null,
    disabled: !!el.disabled,
    hidden_attribute: el.hasAttribute ? el.hasAttribute('hidden') : false,
    display: cs.display,
    visibility: cs.visibility,
    opacity: cs.opacity,
    pointer_events: cs.pointerEvents,
    box,
    viewport_overlap_css_px2: +(ow * oh).toFixed(2),
    hittable: !!top && (top === el || el.contains(top)),
    option_count: el.tagName === 'SELECT' ? el.options.length : null,
    has_multiple: el.tagName === 'SELECT' ? !!el.multiple : null,
    has_datalist: !!(listId && document.getElementById(listId)),
    password_scope: !!(scope && scope.querySelector('input[type=password]')),
    document_password_field_count: document.querySelectorAll('input[type=password]').length,
  };
}
"""

#: `03 §7` auth 신호의 **원시 관측**. 분류(`auth_gate_stage`)는 W5D `terminal.py` 다.
_AUTH_SIGNAL_JS = """
() => {
  const vis = (el) => {
    if (!el) return false;
    const cs = getComputedStyle(el);
    if (cs.display === 'none' || cs.visibility === 'hidden' || +cs.opacity === 0) return false;
    const r = el.getBoundingClientRect();
    return r.width > 0 && r.height > 0;
  };
  const pw = [...document.querySelectorAll('input[type=password]')];
  const visible = pw.filter(vis);
  return {
    password_field_count: pw.length,
    visible_password_field_count: visible.length,
    visible_password_selectors: visible.map((el) => el.id ? '#' + el.id : el.tagName.toLowerCase()),
  };
}
"""

#: fixture 가 선언한 endpoint marker. `l0_probe.js` 의 `[data-endpoint]` 경로와 같은
#: 신호를 본다 — 여기서 새 어휘를 만들지 않는다.
_ENDPOINT_SIGNAL_JS = """
() => {
  const declared = [...document.querySelectorAll('[data-endpoint]')].map((el) => ({
    endpoint: el.getAttribute('data-endpoint'),
    hidden: el.hasAttribute('hidden'),
  }));
  return {
    body_endpoint_reached: document.body ? document.body.getAttribute('data-endpoint-reached') : null,
    declared_endpoints: declared,
  };
}
"""


def _utc_now_iso() -> str:
    return _dt.datetime.now(_dt.UTC).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def _not_actionable_reason(facts: Mapping[str, Any]) -> str | None:
    """활성화를 시도조차 할 수 없는 상태인가. **관측값만** 본다 — 판정이 아니다.

    이것이 없으면 숨겨진 control 을 누르려다 playwright 기본 actionability 대기
    30초를 그대로 기다린 뒤 timeout 으로 실패한다. 결론은 같지만 그 사이에 이유가
    "숨겨져 있었다" 가 아니라 "느렸다" 로 바뀐다.
    """
    if facts.get("hidden_attribute"):
        return "CONTROL_NOT_ACTIONABLE:HIDDEN_ATTRIBUTE"
    if str(facts.get("display") or "").lower() == "none":
        return "CONTROL_NOT_ACTIONABLE:DISPLAY_NONE"
    if str(facts.get("visibility") or "").lower() == "hidden":
        return "CONTROL_NOT_ACTIONABLE:VISIBILITY_HIDDEN"
    box = facts.get("box") or {}
    if not (float(box.get("w") or 0) > 0 and float(box.get("h") or 0) > 0):
        return "CONTROL_NOT_ACTIONABLE:ZERO_BOX"
    if facts.get("disabled"):
        return "CONTROL_NOT_ACTIONABLE:DISABLED"
    return None


def _box_tuple(box: Mapping[str, Any] | None) -> tuple[float, float, float, float] | None:
    if not box:
        return None
    try:
        return (float(box["x"]), float(box["y"]), float(box["w"]), float(box["h"]))
    except (KeyError, TypeError, ValueError):
        return None


# ---------------------------------------------------------------------------
# 드라이버
# ---------------------------------------------------------------------------


@dataclass
class _OpenSession:
    """열린 fixture 세션 하나. `capture_surface` 가 만들고 `close()` 가 없앤다."""

    context: Any
    page: Any
    environment: EnvironmentRecord
    contract_id: str
    state_count: int = 0
    step_count: int = 0
    action_log: list[dict[str, Any]] = field(default_factory=list)


class FixtureSessionDriver:
    """`runner.SessionDriver` Protocol 구현. **fixture 만 연다.**

    사용::

        with FixtureSessionDriver(fixture_root=FIXTURES) as driver:
            states = driver.capture_surface(contract)
            transition = driver.activate(PlannedAction("OPEN_GLOBAL_MENU", "#open"))

    `browser` 를 주입하면 컨텍스트만 만들고 브라우저 수명은 호출자가 갖는다
    (13종 fixture 를 한 브라우저로 돌 때 쓴다). 주입하지 않으면 첫 `capture_surface`
    에서 chromium 을 직접 띄우고 `close()` 에서 내린다.
    """

    #: `03 §1` 선언값. `l0_collector` 의 상수를 그대로 쓴다 — 여기서 다시 정하지 않는다.
    VIEWPORT_WIDTH = VIEWPORT_WIDTH
    VIEWPORT_HEIGHT = VIEWPORT_HEIGHT
    LOCALE = LOCALE
    TIMEZONE_ID = TIMEZONE_ID
    USER_AGENT = MOBILE_USER_AGENT
    EXECUTION_MODE = ExecutionMode.FIXTURE

    def __init__(
        self,
        *,
        fixture_root: Path | str,
        browser: Any | None = None,
        scroll_policy: ScrollPolicy = DEFAULT_SCROLL_POLICY,
        capture_screenshots: bool = True,
    ) -> None:
        self._fixture_root = Path(fixture_root).resolve()
        self._browser = browser
        self._owns_browser = browser is None
        self._playwright: Any | None = None
        self._scroll_policy = scroll_policy
        self._capture_screenshots = capture_screenshots
        self._session: _OpenSession | None = None

    # -- 수명 -----------------------------------------------------------------

    def __enter__(self) -> FixtureSessionDriver:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        self.close()

    @property
    def fixture_root(self) -> Path:
        return self._fixture_root

    @property
    def scroll_policy(self) -> ScrollPolicy:
        return self._scroll_policy

    @property
    def environment(self) -> EnvironmentRecord | None:
        """마지막으로 연 세션의 `03 §1` 환경 기록. 세션이 없으면 `None`."""
        return self._session.environment if self._session is not None else None

    @property
    def action_log(self) -> tuple[Mapping[str, Any], ...]:
        """이 세션에서 실행된 activation 의 관측 기록. 판정값은 없다."""
        return () if self._session is None else tuple(self._session.action_log)

    def close(self) -> None:
        self._close_session()
        if self._owns_browser and self._browser is not None:
            self._browser.close()
            self._browser = None
        if self._playwright is not None:
            self._playwright.stop()
            self._playwright = None

    def _close_session(self) -> None:
        if self._session is not None:
            self._session.context.close()
            self._session = None

    def reset_session(self, contract: TaskContract) -> None:
        """세션을 닫고 `starting_url` 에서 **fresh context** 로 다시 연다.

        `03 §5` replay 는 frozen path 를 처음 상태에서 재생해야 한다. `SessionDriver`
        Protocol 에는 이 훅이 없어 `runner.run()` 은 scout 가 끝난 화면 그대로 replay 로
        들어간다 — 그 사실은 코디네이터에 보고했다. 이 메서드는 훅이 생겼을 때
        붙일 자리이며, 호출자가 명시적으로 부르지 않는 한 아무 일도 하지 않는다.
        """
        self._close_session()
        self._open(contract)

    # -- Protocol: capture_surface -------------------------------------------

    def capture_surface(self, contract: TaskContract) -> Sequence[SurfaceObservation]:
        """`03 §3` — S0 안정화 후 고정 scroll 정책으로 S1..Sn 을 만든다.

        **이 메서드는 `RawTransition` 을 만들지 않는다.** scroll 은 discovery/exposure
        변수이며 `activation_depth` 에 들어가지 않으므로, 여기서 나오는 것은
        `SurfaceObservation` 뿐이고 flow step 이 될 수 있는 산출물이 하나도 없다.
        이것이 "scroll 이 depth 에 섞이지 않는다" 의 구조적 집행이다.
        """
        session = self._open(contract)
        observations: list[SurfaceObservation] = []
        policy = self._scroll_policy
        step_px = max(1.0, session.environment.viewport_height_configured * policy.step_ratio)

        truncated = False
        for index in range(policy.max_states):
            state_index = f"S{index}"
            scroll = session.page.evaluate(_SCROLL_STATE_JS)
            current_y = float(scroll["scroll_y"])
            observations.append(
                self._observe_state(session, state_index=state_index, scroll=scroll)
            )
            reached_bottom = (
                float(scroll["scroll_y"]) + float(scroll["client_height"])
                >= float(scroll["scroll_height"]) - 0.5
            )
            if reached_bottom:
                break
            if index + 1 >= policy.max_states:
                truncated = True
                break
            target = current_y + step_px
            new_y = float(session.page.evaluate(_SCROLL_TO_JS, target))
            session.page.wait_for_timeout(policy.settle_ms)
            if new_y <= current_y + 0.5:
                break

        session.state_count = len(observations)
        session.action_log.append(
            {
                "kind": "capture_surface",
                "state_count": len(observations),
                "scroll_policy": policy.as_record(),
                "scroll_states_truncated": truncated,
                "produced_transitions": 0,
            }
        )
        return tuple(observations)

    # -- Protocol: activate ---------------------------------------------------

    def activate(self, action: PlannedAction) -> RawTransition:
        """control 하나를 활성화하고 before/after 를 전부 담은 `RawTransition` 을 낸다.

        실패는 예외가 아니라 `ok=False` + `failure_reason` 이다 — replay 가 깨졌을 때
        `REPLAY_BROKEN` 으로 기록되어야 하고, 예외로 터지면 그 기록이 남지 않는다.
        예외로 나가는 것은 **금지된 조작을 시도한 경우**(credential) 뿐이다.
        """
        session = self._require_session()
        selector = action.control_selector
        before_state = f"step{session.step_count:04d}_before"
        after_state = f"step{session.step_count:04d}_after"
        url_before = session.page.url

        if not selector:
            return self._failed(
                session,
                action,
                before_state,
                after_state,
                url_before,
                None,
                None,
                "NO_CONTROL_SELECTOR",
            )

        facts_before = session.page.evaluate(_CONTROL_FACTS_JS, selector)
        # 관측을 payload **전에** 한다 — 실패 경로에서도 "무엇으로 관측됐는가" 가 남는다.
        observed_mode = observe_input_mode(facts_before) if facts_before.get("found") else None
        payload_before = self._payload(
            session,
            node_id=before_state,
            extra_control_facts={
                "planned_action": action.as_record(),
                "control": facts_before,
                "observed_input_mode": observed_mode.value if observed_mode else None,
            },
        )
        bbox_before = _box_tuple(facts_before.get("box")) if facts_before.get("found") else None

        if not facts_before.get("found"):
            return self._failed(
                session,
                action,
                before_state,
                after_state,
                url_before,
                payload_before,
                None,
                "CONTROL_NOT_FOUND",
                bbox_before=bbox_before,
            )

        not_actionable = _not_actionable_reason(facts_before)
        if not_actionable is not None:
            return self._failed(
                session,
                action,
                before_state,
                after_state,
                url_before,
                payload_before,
                None,
                not_actionable,
                bbox_before=bbox_before,
                observed_mode=observed_mode,
            )

        try:
            used_mode, dispatch = self._dispatch(
                session, action, selector, facts_before, observed_mode
            )
        except CredentialInputRefusedError:
            raise
        except Exception as exc:  # pragma: no cover - playwright 런타임 실패 경로
            return self._failed(
                session,
                action,
                before_state,
                after_state,
                url_before,
                payload_before,
                None,
                f"ACTIVATION_FAILED:{type(exc).__name__}",
                bbox_before=bbox_before,
                observed_mode=observed_mode,
            )

        if dispatch is None:
            return self._failed(
                session,
                action,
                before_state,
                after_state,
                url_before,
                payload_before,
                None,
                used_mode or "NOT_DRIVABLE",
                bbox_before=bbox_before,
                observed_mode=observed_mode,
            )

        session.page.wait_for_timeout(self._scroll_policy.settle_ms)
        url_after = session.page.url
        auth = session.page.evaluate(_AUTH_SIGNAL_JS)
        endpoint = session.page.evaluate(_ENDPOINT_SIGNAL_JS)
        facts_after = session.page.evaluate(_CONTROL_FACTS_JS, selector)
        recorded_mode = self._recorded_input_mode(action, used_mode or observed_mode)

        payload_after = self._payload(
            session,
            node_id=after_state,
            extra_control_facts={
                "planned_action": action.as_record(),
                "control": facts_after,
                "dispatch": dispatch,
                "observed_input_mode": observed_mode.value if observed_mode else None,
                "used_input_mode": (
                    used_mode.value if isinstance(used_mode, FixtureInputMode) else None
                ),
                "recorded_input_mode": recorded_mode,
                "auth_signal": auth,
                "endpoint_signal": endpoint,
            },
        )

        auth_gate = int(auth.get("visible_password_field_count") or 0) > 0
        endpoint_reached = bool(endpoint.get("body_endpoint_reached")) or any(
            not item.get("hidden") for item in endpoint.get("declared_endpoints") or []
        )

        session.step_count += 1
        session.action_log.append(
            {
                "kind": "activate",
                "action_token": action.action_token,
                "selector": selector,
                "dispatch": dispatch,
                "observed_input_mode": observed_mode.value if observed_mode else None,
                "recorded_input_mode": recorded_mode,
                "ok": True,
            }
        )
        return RawTransition(
            ok=True,
            state_before_id=before_state,
            state_after_id=after_state,
            url_before=url_before,
            url_after=url_after,
            bbox_before=bbox_before,
            auth_gate_detected=auth_gate,
            endpoint_signal_detected=endpoint_reached,
            payload_before=payload_before,
            payload_after=payload_after,
            failure_reason=None,
            input_mode=recorded_mode,
        )

    # -- 조작 dispatch --------------------------------------------------------

    def _dispatch(
        self,
        session: _OpenSession,
        action: PlannedAction,
        selector: str,
        facts: Mapping[str, Any],
        observed: FixtureInputMode | None,
    ) -> tuple[FixtureInputMode | str | None, str | None]:
        """관측된 수단대로 control 을 다룬다. **수집자가 수단을 고르지 않는다.**

        가능한 조작은 셋뿐이다 — click · select_option · (안전 필드 한정) fill.
        제출/결제/예약/좌석선택 같은 것은 별도 코드 경로가 없으므로 여기서 나갈 수 없다.
        """
        if observed is FixtureInputMode.DROPDOWN:
            if not facts.get("option_count"):
                return "DROPDOWN_WITHOUT_OPTIONS", None
            session.page.select_option(
                selector,
                index=min(1, int(facts["option_count"]) - 1),
                timeout=ACTION_TIMEOUT_MS,
            )
            return FixtureInputMode.DROPDOWN, "select_option"
        if observed is FixtureInputMode.MIXED:
            # 목록 affordance 가 실제로 붙어 있으면 그것이 서비스가 먼저 제시한 수단이다.
            if facts.get("option_count"):
                session.page.select_option(
                    selector,
                    index=min(1, int(facts["option_count"]) - 1),
                    timeout=ACTION_TIMEOUT_MS,
                )
                return FixtureInputMode.DROPDOWN, "select_option"
            self._fill_safe_text(session, selector, facts)
            return FixtureInputMode.FREE_TEXT, "fill"
        if observed is FixtureInputMode.FREE_TEXT:
            self._fill_safe_text(session, selector, facts)
            return FixtureInputMode.FREE_TEXT, "fill"
        if observed is FixtureInputMode.MAP_PAN:
            # 지도 pan/zoom 을 구동하는 코드 경로를 여기에 만들지 않았다.
            # 없는 기능을 있는 것처럼 흉내내면 관측이 아니라 연출이 된다.
            return "MAP_PAN_NOT_DRIVABLE", None
        session.page.click(selector, timeout=ACTION_TIMEOUT_MS)
        return observed, "click"

    def _fill_safe_text(
        self, session: _OpenSession, selector: str, facts: Mapping[str, Any]
    ) -> None:
        """이 모듈에서 `Page.fill` 이 호출되는 **유일한 자리**다.

        첫 문장이 credential 거부이고, 넣는 값은 모듈 상수 하나다. 호출자가 값을
        건네줄 인자가 없고 `PlannedAction` 에도 값 필드가 없다.
        """
        if is_credential_field(facts):
            raise CredentialInputRefusedError(
                f"credential 계열 필드에 입력하지 않는다 (03 §7): {selector!r} "
                f"type={facts.get('type')!r} password_scope={facts.get('password_scope')!r}"
            )
        session.page.fill(selector, SAFE_PROBE_TEXT, timeout=ACTION_TIMEOUT_MS)

    def _recorded_input_mode(
        self, action: PlannedAction, mode: FixtureInputMode | str | None
    ) -> str | None:
        """`RawTransition.input_mode` 에 실을 값. 자세한 이유는 `RECORDED_INPUT_MODES`.

        조건부 토큰이 아닌 step 에서는 `None` 이다 — 그 자리의 "입력수단" 은 Δ9 가 묻는
        질문이 아니고, `OTHER` 를 억지로 실으면 W5F `_validated_input_mode` 가 거부한다.
        """
        if action.action_token not in DEPTH_CONDITIONAL_TOKENS:
            return None
        if not isinstance(mode, FixtureInputMode):
            return None
        return mode.value if mode.value in RECORDED_INPUT_MODES else None

    # -- 세션/관측 ------------------------------------------------------------

    def _require_session(self) -> _OpenSession:
        if self._session is None:
            raise SessionNotOpenError(
                "activate 전에 capture_surface 로 세션을 열어야 한다 — "
                "여기서 조용히 항해하면 '어느 상태에서 눌렀는가' 가 기록에서 사라진다"
            )
        return self._session

    def _resolve_fixture_url(self, starting_url: str) -> str:
        """`file://` fixture URL 로 정규화하고 firewall 을 **반드시** 통과시킨다.

        상대 경로/파일명은 `fixture_root` 아래로 붙인다. 네트워크 scheme 은 여기서
        정규화되지 않고 `assert_navigation_allowed` 가 `NavigationBlockedError` 로
        막는다 — 이 함수에는 그 예외를 삼키는 자리가 없다.
        """
        text = str(starting_url).strip()
        parsed = urlparse(text)
        if not parsed.scheme:
            candidate = (self._fixture_root / text).resolve()
            text = candidate.as_uri()
        return assert_navigation_allowed(self.EXECUTION_MODE, text, fixture_root=self._fixture_root)

    def _ensure_browser(self) -> Any:
        if self._browser is not None:
            return self._browser
        from playwright.sync_api import sync_playwright

        self._playwright = sync_playwright().start()
        self._browser = self._playwright.chromium.launch()
        return self._browser

    def _new_context(self, browser: Any) -> Any:
        """`03 §1` — fresh context · no login · no stored cookie · ko-KR / Asia/Seoul / mobile.

        `L0Collector._new_context` 와 같은 파라미터를 쓴다(같은 상수에서 온다). 저장된
        상태를 실어오는 `storage_state` 인자는 이 호출에 없다 — 쿠키가 들어올 자리가 없다.
        """
        context = browser.new_context(
            viewport={"width": self.VIEWPORT_WIDTH, "height": self.VIEWPORT_HEIGHT},
            device_scale_factor=DEVICE_SCALE_FACTOR,
            is_mobile=True,
            has_touch=True,
            locale=self.LOCALE,
            timezone_id=self.TIMEZONE_ID,
            user_agent=self.USER_AGENT,
            java_script_enabled=True,
        )
        # `_resolve_fixture_url` 은 **내가 여는** URL 만 막는다. fixture 안의 링크가
        # 네트워크로 나가는 경로는 그것과 별개라 컨텍스트 단에서 한 겹 더 끊는다.
        for pattern in NETWORK_ROUTE_PATTERNS:
            context.route(pattern, lambda route: route.abort())
        return context

    def _open(self, contract: TaskContract) -> _OpenSession:
        if self._session is not None and self._session.contract_id == contract.target_id:
            return self._session
        self._close_session()

        requested_url = self._resolve_fixture_url(contract.starting_url)
        browser = self._ensure_browser()
        context = self._new_context(browser)
        page = context.new_page()
        started = _utc_now_iso()
        page.goto(requested_url, wait_until="load")
        page.wait_for_timeout(self._scroll_policy.settle_ms)

        env = page.evaluate(_ENV_JS)
        environment = EnvironmentRecord(
            requested_url=requested_url,
            final_url=str(env.get("url") or page.url),
            collected_at=started,
            viewport_width_configured=self.VIEWPORT_WIDTH,
            viewport_height_configured=self.VIEWPORT_HEIGHT,
            viewport_width_rendered=env.get("inner_width"),
            viewport_height_rendered=env.get("inner_height"),
            device_pixel_ratio=env.get("device_pixel_ratio"),
            user_agent_configured=self.USER_AGENT,
            user_agent_rendered=env.get("user_agent"),
            locale_configured=self.LOCALE,
            locale_rendered=env.get("language"),
            timezone_configured=self.TIMEZONE_ID,
            timezone_rendered=env.get("timezone"),
            is_mobile=True,
            has_touch=True,
            max_touch_points=env.get("max_touch_points"),
            fresh_context=True,
            stored_cookie_count=len(context.cookies()),
            login_performed=False,
            execution_mode=str(self.EXECUTION_MODE.value),
        )
        self._session = _OpenSession(
            context=context, page=page, environment=environment, contract_id=contract.target_id
        )
        return self._session

    def _payload(
        self,
        session: _OpenSession,
        *,
        node_id: str,
        extra_control_facts: Mapping[str, Any],
    ) -> EvidencePayload:
        """`03 §10` evidence package 한 벌 — DOM · AX · screenshot · probe/CSS · URL · control facts."""
        page = session.page
        ax_nodes = L0Collector._ax_tree(session.context, page)
        probe = page.evaluate(PROBE_JS, str(self.EXECUTION_MODE.value))
        computed_css = page.evaluate(_COMPUTED_CSS_JS, list(_COMPUTED_CSS_PROPERTIES))
        scroll = page.evaluate(_SCROLL_STATE_JS)
        screenshot: bytes | None = None
        if self._capture_screenshots:
            screenshot = page.screenshot(full_page=False)
        control_facts: dict[str, Any] = {
            "environment": session.environment.as_record(),
            "scroll": scroll,
            # W5C `measure_surface` 가 읽는 자리. **비어 있는 것이 정답이다** — 조인이
            # 없는데 DOM 속성으로 이름을 추정하면 `visible_label_text` 와 출처가 겹쳐
            # `00 §8` 의 분리가 무너진다. 조인이 생기면 여기에 slim node 가 꽂힌다.
            "ax_node": None,
            "ax_node_join_status": AX_NODE_JOIN_STATUS,
            **dict(extra_control_facts),
        }
        return EvidencePayload(
            node_id=node_id,
            url=page.url,
            dom=page.content(),
            ax={"nodes": ax_nodes},
            probe={
                "l0_probe": probe,
                "computed_css": computed_css,
                "computed_css_properties": list(_COMPUTED_CSS_PROPERTIES),
                "scroll": scroll,
            },
            control_facts=control_facts,
            screenshot=screenshot,
        )

    def _observe_state(
        self, session: _OpenSession, *, state_index: str, scroll: Mapping[str, Any]
    ) -> SurfaceObservation:
        payload = self._payload(
            session,
            node_id=state_index.lower(),
            extra_control_facts={
                "state_index": state_index,
                "scroll_policy": self._scroll_policy.as_record(),
                "scroll_is_not_activation_depth": True,
            },
        )
        return SurfaceObservation(
            state_index=state_index,
            scroll_y=float(scroll["scroll_y"]),
            viewport_width=int(session.environment.viewport_width_rendered or self.VIEWPORT_WIDTH),
            viewport_height=int(
                session.environment.viewport_height_rendered or self.VIEWPORT_HEIGHT
            ),
            url=session.page.url,
            payload=payload,
        )

    def _failed(
        self,
        session: _OpenSession,
        action: PlannedAction,
        before_state: str,
        after_state: str,
        url_before: str,
        payload_before: EvidencePayload | None,
        payload_after: EvidencePayload | None,
        reason: str,
        *,
        bbox_before: tuple[float, float, float, float] | None = None,
        observed_mode: FixtureInputMode | None = None,
    ) -> RawTransition:
        """실패한 activation 도 관측이다 — before evidence 를 버리지 않고 기록한다."""
        session.step_count += 1
        session.action_log.append(
            {
                "kind": "activate",
                "action_token": action.action_token,
                "selector": action.control_selector,
                "dispatch": None,
                "observed_input_mode": observed_mode.value if observed_mode else None,
                "recorded_input_mode": None,
                "ok": False,
                "failure_reason": reason,
            }
        )
        return RawTransition(
            ok=False,
            state_before_id=before_state,
            state_after_id=after_state,
            url_before=url_before,
            url_after=session.page.url,
            bbox_before=bbox_before,
            auth_gate_detected=False,
            endpoint_signal_detected=False,
            payload_before=payload_before,
            payload_after=payload_after,
            failure_reason=reason,
            input_mode=None,
        )
