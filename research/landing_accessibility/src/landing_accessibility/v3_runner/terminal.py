"""Terminal 분류 — 8종을 절대 하나의 `FAILED` 로 합치지 않는다.

## 층 한정 의무 (`R6-Q8`)

`AUTH_GATE` 와 `ABSTAIN` 은 **여러 층에 같은 문자열로 존재한다** — `04 §2` action token
층, `04 §4` `endpoint_status` 층, 그리고 이 모듈의 terminal 층. A 는 04 codebook 원본을
고치지 않고 **필드 한정을 의무화**했다: *값만 단독으로 쓰지 않고 항상 층을 명시한다.*

그래서 이 모듈은 어디서도 두 값을 맨몸으로 쓰지 않는다. 반드시 셋 중 하나로 적는다:

- `terminal=AUTH_GATE` — 이 모듈이 내는 terminal 관측값
- `endpoint_status=AUTH_GATE` — `04 §4` 어휘
- `action_token=AUTH_GATE` — `04 §2` 어휘 (이 모듈은 이 층을 산출하지 않는다)

`ABSTAIN` 도 같다 — `endpoint_status=ABSTAIN` / `action_token=ABSTAIN`. terminal 층에는
`ABSTAIN` 이라는 값이 없다(그 자리는 `terminal=NO_SAFE_ROUTE_FOUND` ·
`terminal=SAFETY_STOP` · `resolution=UNDETERMINED` 가 나눠 갖는다).

## 왜 합치면 안 되는가

`terminal=AUTH_GATE`, `terminal=PUBLIC_WEB_UNOBSERVABLE`, `terminal=APP_REQUIRED`,
`terminal=WAF_OR_CHALLENGE`, `terminal=TIMEOUT`, `terminal=EVIDENCE_DEFECT`,
`terminal=NO_SAFE_ROUTE_FOUND`, `terminal=SAFETY_STOP` 은 **서로 다른 사실**이다.

- 셋(`terminal=AUTH_GATE` · `PUBLIC_WEB_UNOBSERVABLE` · `APP_REQUIRED`)은
  **사이트의 성질**이다. 분석 대상이다.
- 둘(`EVIDENCE_DEFECT` · `TIMEOUT`)은 **우리 도구의 결함**이다. 재수집 대상이다.
- 하나(`WAF_OR_CHALLENGE`)는 **사이트가 우리를 거부한 것**이다. 접근성 결론이 아니다.
- 둘(`NO_SAFE_ROUTE_FOUND` · `SAFETY_STOP`)은 **우리의 판단**이다. 관측 실패가 아니라
  관측을 그만둔 것이다.

하나의 `FAILED` 로 합치면 *"이 서비스는 모바일웹으로 과업을 못 한다"* 와 *"우리 크롤러가
타임아웃했다"* 가 같은 값이 된다. 전자는 발견이고 후자는 버그다.

### 특히 `EVIDENCE_DEFECT` 와 `PUBLIC_WEB_UNOBSERVABLE` 을 혼동하지 마라

- `EVIDENCE_DEFECT` = **우리 결함.** DOM/AX/screenshot/manifest 중 하나가 없거나 깨졌다.
  이 target 에 대해 우리는 **아무것도 주장할 수 없다.** 사이트에 대한 진술이 아니다.
  조치는 재수집이며, 분석 표본에서 사이트의 성질로 계수하면 안 된다.
- `PUBLIC_WEB_UNOBSERVABLE` = **관측 결과.** 증거는 온전하고, 그 증거가 *공개 모바일웹
  경로에서 이 과업을 관측할 수 없다* 는 것을 보여준다. 사이트의 성질에 대한 진술이며
  분석 대상이다. 재수집해도 같은 값이 나오는 것이 정상이다.

증거가 깨졌으면 사이트에 대해 **어떤** 결론도 낼 수 없으므로 `terminal=EVIDENCE_DEFECT`
가 다른 모든 판정보다 우선한다(아래 우선순위 1번).

### 그리고 `endpoint_status=ABSTAIN` 은 또 다른 것이다 (`R1`)

세 값이 전부 "과업을 끝까지 못 갔다"로 보이지만 원인 층이 다르다.

| 값 | 무엇에 대한 진술인가 | 조치 |
|---|---|---|
| `endpoint_status=EVIDENCE_DEFECT` | **우리 도구.** 증거가 깨져 아무 주장도 못 한다 | 재수집 |
| `endpoint_status=PUBLIC_WEB_UNOBSERVABLE` | **사이트.** 그 과업 surface 가 공개 모바일웹에 없다 | 분석에 계수 |
| `endpoint_status=ABSTAIN` | **우리 판정의 유보.** 증거는 있으나 경로/후보가 불확정이라 억지로 판정하지 않는다 | 분석에 결측으로 계수 |

`R1` — A 는 "과업 의미가 근본적으로 다르다"를 **교체 사유로 만들지 않기로** 했다. 그런
target 은 frame 에 남고 `TASK_COMPARABILITY_CONCERN` finding 으로 기록되며, 과업 수행이
불가능하면 결과는 `endpoint_status=ABSTAIN` 또는 `endpoint_status=PUBLIC_WEB_UNOBSERVABLE` 이 된다.
*"결측을 결측으로 보고하는 것이 표본을 바꾸는 것보다 정직하다."*

그 결과 이 모듈에는 comparability 입력이 **없다** — comparability concern 은 terminal 이
아니라 finding 이고, 이 모듈은 그것을 새 terminal 로 만들지 않는다. 실제 관측이 어느
쪽이었는지에 따라 기존 8종 중 하나로 떨어진다:

- surface 자체가 공개 모바일웹에 없었다 → `terminal=PUBLIC_WEB_UNOBSERVABLE`
- surface 는 있을 수 있으나 허용 경로를 확정하지 못했다 → `terminal=NO_SAFE_ROUTE_FOUND`
  (→ `endpoint_status=ABSTAIN`)

## `endpoint_status` 는 별도 축이다 (`04 §4`)

`04 §4` 의 `endpoint_status` 어휘는 7종이다: `endpoint_status` ∈ {`REACHED`, `AUTH_GATE`,
`PUBLIC_WEB_UNOBSERVABLE`, `APP_REQUIRED`, `EVIDENCE_DEFECT`, `BLOCKED`, `ABSTAIN`}.

terminal 8종 → `endpoint_status` 7종 매핑은 **다대일**이다. 그래서 `endpoint_status` 에서
terminal 을 복원할 수 없고, 두 값을 **둘 다** 보존한다.

| terminal 층 | endpoint_status 층 | 다대일이 되는 지점 |
|---|---|---|
| `terminal=AUTH_GATE` | `endpoint_status=AUTH_GATE` | 1:1 |
| `terminal=PUBLIC_WEB_UNOBSERVABLE` | `endpoint_status=PUBLIC_WEB_UNOBSERVABLE` | 1:1 |
| `terminal=APP_REQUIRED` | `endpoint_status=APP_REQUIRED` | 1:1 |
| `terminal=WAF_OR_CHALLENGE` | `endpoint_status=BLOCKED` | 1:1 |
| `terminal=EVIDENCE_DEFECT` | `endpoint_status=EVIDENCE_DEFECT` | ← `terminal=TIMEOUT` 과 합류 |
| `terminal=TIMEOUT` | `endpoint_status=EVIDENCE_DEFECT` | 04 §4 에 `TIMEOUT` 값이 없다 |
| `terminal=NO_SAFE_ROUTE_FOUND` | `endpoint_status=ABSTAIN` | ← `terminal=SAFETY_STOP` 과 합류 |
| `terminal=SAFETY_STOP` | `endpoint_status=ABSTAIN` | 04 §4 에 `SAFETY_STOP` 값이 없다 |

**[명세 공백 — A 판단 필요]** `04 §4` 는 `terminal=TIMEOUT` 과 `terminal=SAFETY_STOP` 에
대응하는 `endpoint_status` 값을 명시하지 않는다. 위 두 합류는 이 모듈이 택한 보수적
해석이며(`TIMEOUT` → 증거 미산출 → `endpoint_status=EVIDENCE_DEFECT`, `SAFETY_STOP` →
억지 판정 거부 → `endpoint_status=ABSTAIN`), 어휘를 늘리지 않는 방향을 골랐다. terminal
축이 원본을 보존하므로 정보 손실은 없다. A 가 다른 매핑을 정하면 이 표만 고치면 된다.

## 동반 필드 `terminal_reason` — `endpoint_status` 어휘는 안 바꾼다 (`T-A-V3-STEP1-007` R11)

`endpoint_status` 는 7종 그대로 두고 **옆에 해상도를 둔다.** `Δ10-R11` 13값 + `Δ30`
`BUDGET_EXCEEDED` + `Δ32` `NO_TASK_CANDIDATE_FOUND` + `Δ47` `PATH_NOT_FOUND_BY_POLICY`
= **16값**이며 정본은 `TerminalReason` 이다. 규칙 셋:

1. **모든 terminal 관측은 `endpoint_status` 와 `terminal_reason` 을 둘 다 갖는다.**
2. `terminal_reason=OTHER` 는 **자유기술 note 필수**. note 없는 `OTHER` 는 스키마 위반이며
   `TerminalReasonNoteError` 로 거부된다.
3. `endpoint_status` × `terminal_reason` 허용 조합표는 `ALLOWED_ENDPOINT_STATUS_REASONS`
   가 정본이고 `validate_status_reason()` 이 강제한다. 불가능 조합
   (예: `endpoint_status=REACHED` × `TIMEOUT`)은 `TerminalCombinationError` 다.
   `classify_terminal()` 은 산출 직전에 스스로 이 검증을 통과한다 — 이 모듈은 불가능
   조합을 만들 수 없다.

| endpoint_status | 허용 terminal_reason |
|---|---|
| `endpoint_status=REACHED` | `None` (아래 공백 참조) |
| `endpoint_status=AUTH_GATE` | `AUTH_REQUIRED` |
| `endpoint_status=PUBLIC_WEB_UNOBSERVABLE` | `NO_PUBLIC_MOBILE_WEB` · `TASK_SURFACE_ABSENT` · `OTHER` |
| `endpoint_status=APP_REQUIRED` | `APP_REQUIRED` |
| `endpoint_status=EVIDENCE_DEFECT` | `EVIDENCE_DEFECT` · `TIMEOUT` |
| `endpoint_status=BLOCKED` | `WAF_BLOCK` · `ACTIVE_CHALLENGE` |
| `endpoint_status=ABSTAIN` | `FORBIDDEN_ACTION_REQUIRED` · `CONTROL_DISABLED_OR_INERT` · `REPLAY_BROKEN` · `AMBIGUOUS_MULTIPLE_CANDIDATES` · `BUDGET_EXCEEDED`(Δ30) · `NO_TASK_CANDIDATE_FOUND`(Δ32) · `OTHER` |

**[명세 공백 — A 판단 필요]** A 규칙 1 은 *모든 terminal 관측*에 대한 것인데
`endpoint_status=REACHED` 는 terminal 관측이 아니다(`resolution` 이
`NOT_TERMINAL_ENDPOINT_REACHED`). `04 §4` 와 `02 §5` 어디에도 도달에 대응하는
`terminal_reason` 값이 없다. **지어내지 않고** `None` 으로 두었으며 조합표도 그것만
허용한다. known limitation 으로 올린다.

`resolution=UNDETERMINED`(어떤 terminal 신호도 관측 안 됨)는 terminal 관측은 아니지만
`endpoint_status=ABSTAIN` 을 내보내므로, 사유 없는 `ABSTAIN` 이 되지 않도록
`terminal_reason=OTHER` + 자동 생성 note 를 붙인다.

## 성공/실패 해석은 이 모듈의 일이 아니다 (`R2`)

A 원문: **"`endpoint_status=AUTH_GATE` 는 성공/실패가 아니라 terminal 관측값이다."**
그리고 그 의미는 family 에 따라 갈린다.

- **F1** — `endpoint_contract` 가 auth gate 를 endpoint 로 명시한다 → **endpoint 도달로
  센다**, flow-evaluable 에 포함.
- **F2~F5** — endpoint 미도달 terminal → evidence-bearing n 에는 포함되나 endpoint
  도달률 **분모에서는 미도달**로 집계.

**이 모듈은 그 판정을 하지 않는다.** family 의존이라 `dim_task_contract.endpoint_contract`
를 봐야 알 수 있고, 그 문자열을 여기서 파싱하는 것은 취약하다. 그래서 두 선택지 중
**"terminal 은 관측값만 내고 성공/미도달 해석은 상위(mart) 층에 위임한다"** 를 택했다
(B 권고와 일치). 근거: terminal 은 *무엇이 관측됐는가*이고, 성공/미도달은 *그것을 어느
분모에 넣을 것인가*라는 별개 질문이다. 분모는 family 를 아는 층이 정한다.

그 결과 `TerminalSignals` 에 `endpoint_contract` / `family_id` 입력이 없고,
`TerminalOutcome` 에 `is_success` / `endpoint_reached_effective` 같은 파생 필드도 없다.
`endpoint_reached` 입력은 *러너가 endpoint 조건 충족을 관측했다*는 신호일 뿐이며, F1 의
auth-gate-as-endpoint 해석을 대신하지 않는다.

## 우선순위

여러 신호가 동시에 참일 수 있다. 이 모듈은 **선언된 순서**로 하나를 고르고, 나머지를
`competing_signals` 에 전부 남긴다 — 조용히 버리지 않는다.

1. `terminal=EVIDENCE_DEFECT` — 증거가 못 쓸 것이면 다른 어떤 신호도 신뢰할 수 없다.
2. `terminal=TIMEOUT` — run 이 끝나지 않았다. 그 시점까지의 신호는 완결되지 않았다.
3. `terminal=WAF_OR_CHALLENGE` — 사이트가 응답 자체를 거부/차단했다. 그 뒤 화면은
   사이트의 과업 경로가 아니라 차단 화면이다.
4. `terminal=APP_REQUIRED` — 공개 모바일웹 채널이 과업을 아예 싣지 않는다(`03 §2`).
5. `terminal=PUBLIC_WEB_UNOBSERVABLE` — 채널은 있으나 이 과업을 공개 경로에서 관측할
   수 없다.
6. `terminal=AUTH_GATE` — 과업 경로를 따라가다 인증이 불가피해졌다(`03 §7`).
7. `terminal=SAFETY_STOP` — 남은 경로가 금지 행위를 요구해 우리가 멈췄다(`03 §6`·`§8`).
8. `terminal=NO_SAFE_ROUTE_FOUND` — 허용된 탐색을 소진했으나 endpoint 에 닿지 못했다.

**[명세 공백 — A 판단 필요]** 6 과 7 의 순서(인증 게이트와 금지행위 요구가 동시에 참일
때)는 SSOT 에 근거가 없다. `03 §7` 이 auth gate 를 이름 있는 terminal 로 따로 세운다는
점에 기대 인증을 앞에 뒀다. 실무상 결제 앞에 로그인이 오는 순서와도 맞는다.

## 이 모듈이 하지 않는 것

- **CAPTCHA 를 풀거나 우회하지 않는다.** `03 §8` — 존재 관측과 terminal 분류까지다.
  `active_blocking_challenge` 는 입력으로 받는 관측값이며, 이 모듈에 challenge 를
  해결·재시도·우회하는 경로는 없다.
- **generic login 버튼 존재만으로 중단하지 않는다.** `03 §7` 명시. 그래서 입력은
  `generic_login_control_present`(중단 근거가 **아님**)와
  `auth_required_to_proceed`(과업 경로에서 인증이 불가피해짐)를 분리해 받는다.
  전자만 참이면 `terminal=AUTH_GATE` 가 되지 않는다.
- **모르는 것을 terminal 로 만들지 않는다.** 어느 규칙에도 안 걸리고 endpoint 도 못
  닿았으면 `resolution=UNDETERMINED` / `terminal=None` / `endpoint_status=ABSTAIN`
  이다. 산출 불능은 `None` 이지 `FAILED` 가 아니다.
- **성공/실패를 판정하지 않는다** (`R2`, 위 절 참조).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum

__all__ = [
    "ALLOWED_ENDPOINT_STATUS_REASONS",
    "TERMINAL_PRECEDENCE",
    "TERMINAL_TO_ENDPOINT_STATUS",
    "AuthGateStage",
    "EndpointStatus",
    "TerminalCombinationError",
    "TerminalKind",
    "TerminalOutcome",
    "TerminalReason",
    "TerminalReasonNoteError",
    "TerminalResolution",
    "TerminalSignals",
    "ZeroActivationClaimError",
    "classify_terminal",
    "validate_reached_requires_binding",
    "validate_status_reason",
]


class TerminalKind(StrEnum):
    """8종. 각각이 **무엇을 뜻하고 무엇을 뜻하지 않는지**를 값마다 적는다."""

    AUTH_GATE = "AUTH_GATE"
    """`terminal=AUTH_GATE` — 과업 경로에서 **인증이 불가피해진** 지점에 도달했다 (`03 §7`).

    뜻하는 것: 이 과업은 공개 모바일웹에서 인증 없이는 끝까지 갈 수 없다는 **관측값**이다.
    뜻하지 않는 것:

    - 페이지 어딘가에 로그인 버튼이 있다는 것. `03 §7` 은 generic login control 존재만으로
      중단하는 것을 금지한다.
    - 자격증명을 입력했다는 것. 입력·submit·본인인증은 금지 행위다.
    - **성공이나 실패.** `R2` — 이건 성공/실패가 아니라 terminal 관측값이다. F1(계약이
      auth gate 를 endpoint 로 명시)에서는 endpoint 도달로 세고, F2~F5 에서는 endpoint
      도달률 분모에서 미도달로 센다. 그 판정은 family 를 아는 상위 층의 일이며 이
      모듈은 하지 않는다.

    같은 문자열이 `action_token=AUTH_GATE`(`04 §2`)와 `endpoint_status=AUTH_GATE`
    (`04 §4`)에도 있다. 층을 빼고 쓰지 않는다 (`R6-Q8`).
    """

    PUBLIC_WEB_UNOBSERVABLE = "PUBLIC_WEB_UNOBSERVABLE"
    """증거는 온전한데, 그 증거가 **공개 모바일웹에서 이 과업을 관측할 수 없음**을 보인다.

    뜻하는 것: **사이트의 성질**에 대한 관측 결과. 분석 대상이다.
    뜻하지 않는 것:

    - 우리 수집기가 실패했다는 것 → `terminal=EVIDENCE_DEFECT`.
    - 앱이 필요하다는 것 → `terminal=APP_REQUIRED`.
    - 우리가 판정을 유보했다는 것 → `endpoint_status=ABSTAIN`
      (`terminal=NO_SAFE_ROUTE_FOUND` / `SAFETY_STOP` / `resolution=UNDETERMINED`).
      `R1` 의 세 값 구분이 여기서 갈린다.
    """

    APP_REQUIRED = "APP_REQUIRED"
    """공개 모바일웹 채널이 이 과업을 **싣지 않고** 전용 앱으로만 제공한다 (`03 §2`).

    뜻하는 것: 채널 자체가 과업을 담지 않는다. `03 §2` 는 app-only 를 main outcome 으로
    쓰지 말고 main frame 에서 교체하라고 한다.
    뜻하지 않는 것: 앱 설치 배너가 떴다는 것. 배너는 obstruction 이지 terminal 이 아니다.
    """

    WAF_OR_CHALLENGE = "WAF_OR_CHALLENGE"
    """사이트가 WAF/봇 차단/**active blocking challenge** 로 응답을 거부했다 (`03 §8`).

    뜻하는 것: 사이트가 우리를 거부했다. 접근성 결론이 아니다.
    뜻하지 않는 것: 이 사이트가 접근 불가능하다는 것. 그리고 우리가 challenge 를
    풀거나 우회할 여지가 있다는 것도 아니다 — `03 §8` 은 해결·우회를 금지한다.
    페이지에 숨은 CAPTCHA iframe 이 있기만 한 것은 여기 해당하지 않는다. **능동적으로
    막고 있을 때만** terminal 이다.
    """

    TIMEOUT = "TIMEOUT"
    """run 이 제한 시간 안에 끝나지 않았다.

    뜻하는 것: 우리 쪽 사실. 이 target 은 재수집 대상이다.
    뜻하지 않는 것: 사이트가 느리다/막았다는 판정. 네트워크·러너·대기 정책 어느 쪽이
    원인인지 이 값은 말하지 않는다.
    """

    EVIDENCE_DEFECT = "EVIDENCE_DEFECT"
    """**우리 도구의 결함.** 증거 package(DOM/AX/screenshot/probe/manifest)가 불완전하다.

    뜻하는 것: 이 target 에 대해 우리는 아무것도 주장할 수 없다. 재수집 대상이다.
    뜻하지 않는 것: 사이트에 대한 어떤 진술도 아니다. 특히
    `terminal=PUBLIC_WEB_UNOBSERVABLE`(사이트의 성질)과 절대 합치지 않는다.
    """

    NO_SAFE_ROUTE_FOUND = "NO_SAFE_ROUTE_FOUND"
    """허용된 탐색을 소진했는데 endpoint 로 가는 **허용 경로를 못 찾았다**.

    뜻하는 것: 우리 탐색의 결과. 경로가 없다는 증명이 아니라 우리가 못 찾았다는 기록이다.
    뜻하지 않는 것: 사이트에 그런 경로가 없다는 것 — 그건
    `terminal=PUBLIC_WEB_UNOBSERVABLE` 이 주장하는 바다. depth budget·replay 실패·후보
    모호성 때문일 수 있으므로 `endpoint_status=ABSTAIN`(판정 유보)으로 간다.
    """

    SAFETY_STOP = "SAFETY_STOP"
    """남은 경로가 **금지 행위**를 요구해 우리가 멈췄다 (`03 §6`·`§8`).

    금지 행위: 구매/장바구니/결제/송금/예약 등 state-changing activation, 자격증명 입력,
    login submit, 본인인증, CAPTCHA 해결.

    뜻하는 것: 우리가 관측을 그만뒀다. 관측 실패가 아니라 우리의 판단이다.
    뜻하지 않는 것: 그 지점이 endpoint 라는 것. 그리고 사이트가 우리를 막았다는 것도
    아니다 — 그건 `terminal=WAF_OR_CHALLENGE` 다. `endpoint_status=ABSTAIN` 으로 간다.
    """


class EndpointStatus(StrEnum):
    """`04 §4` `endpoint_status` 어휘 7종. 이 목록에 값을 추가하지 않는다."""

    REACHED = "REACHED"
    AUTH_GATE = "AUTH_GATE"
    PUBLIC_WEB_UNOBSERVABLE = "PUBLIC_WEB_UNOBSERVABLE"
    APP_REQUIRED = "APP_REQUIRED"
    EVIDENCE_DEFECT = "EVIDENCE_DEFECT"
    BLOCKED = "BLOCKED"
    ABSTAIN = "ABSTAIN"


class AuthGateStage(StrEnum):
    """`03 §7` · `04 §4` — auth 를 만난 **위치**. terminal 여부와 별개 축이다."""

    NONE = "NONE"
    BEFORE_TASK_DISCOVERY = "BEFORE_TASK_DISCOVERY"
    AFTER_TASK_SELECT = "AFTER_TASK_SELECT"
    AT_ENDPOINT = "AT_ENDPOINT"


class TerminalResolution(StrEnum):
    """`terminal` 이 `None` 인 두 경우를 가른다.

    `None` 하나로는 *terminal 이 아니었다* 와 *terminal 인지 판정 못 했다* 가 구분되지
    않는다. 이 축이 그 둘을 가른다.
    """

    TERMINAL = "TERMINAL"
    NOT_TERMINAL_ENDPOINT_REACHED = "NOT_TERMINAL_ENDPOINT_REACHED"
    UNDETERMINED = "UNDETERMINED"


class TerminalReason(StrEnum):
    """`terminal_reason` **16값** — `T-A-V3-STEP1-007` (Δ10, R11) 13값
    + `Δ30` `BUDGET_EXCEEDED`(14) + `Δ32` `NO_TASK_CANDIDATE_FOUND`(15)
    + `Δ47` `PATH_NOT_FOUND_BY_POLICY`(16).

    ## 왜 이 축이 따로 있는가

    `endpoint_status` 어휘(`04 §4`, 7종)를 **바꾸지 않는다.** 대신 옆에 해상도를 둔다
    (`R5 fixture_input_mode` · `R7 원좌표+파생 zone` 과 같은 처리다).

    `endpoint_status` 만으로는 이런 것들이 한 값에 삼켜진다:

    - `endpoint_status=BLOCKED` 가 WAF 차단 · active challenge · timeout 을 삼킨다.
    - `endpoint_status=PUBLIC_WEB_UNOBSERVABLE` 이 *공개 모바일웹 자체가 없음*과
      *채널은 있는데 그 과업 surface 가 없음*을 삼킨다.
    - disabled/inert control, 금지행위 요구에는 대응하는 `endpoint_status` 값이 아예 없다.

    ## 규칙

    - **모든 terminal 관측은 `endpoint_status` 와 `terminal_reason` 을 둘 다 갖는다.**
    - `OTHER` 는 **자유기술 note 필수**다. note 없는 `OTHER` 는 스키마 위반이며
      `TerminalReasonNoteError` 로 거부된다.
    - `endpoint_status` × `terminal_reason` 의 허용 조합은
      `ALLOWED_ENDPOINT_STATUS_REASONS` 가 정본이고, 불가능 조합은
      `TerminalCombinationError` 로 거부된다.
    """

    TIMEOUT = "TIMEOUT"
    """run 이 제한 시간 안에 끝나지 않았다. `terminal=TIMEOUT` 의 사유."""

    WAF_BLOCK = "WAF_BLOCK"
    """서버/WAF 가 응답 자체를 거부했다. 풀 수 있는 challenge 가 제시된 것이 아니다."""

    ACTIVE_CHALLENGE = "ACTIVE_CHALLENGE"
    """능동적으로 진행을 막는 challenge(CAPTCHA 등)가 제시됐다. `03 §8` — 관측까지이며
    해결·우회하지 않는다."""

    NO_PUBLIC_MOBILE_WEB = "NO_PUBLIC_MOBILE_WEB"
    """공개 모바일웹 채널 자체가 없다. precheck 의 **교체 사유**로 쓰이는 값도 이것 하나뿐이다."""

    TASK_SURFACE_ABSENT = "TASK_SURFACE_ABSENT"
    """채널은 있으나 **그 과업이 없다**.

    `NO_PUBLIC_MOBILE_WEB` 과 다르다. 그리고 **기록 해상도와 교체 사유는 다른 층**이다 —
    이 값은 관측을 더 정밀하게 적기 위한 것이지 target 교체 사유가 아니다. precheck 의
    교체 사유로는 여전히 `NO_PUBLIC_MOBILE_WEB` 하나만 쓴다.
    """

    APP_REQUIRED = "APP_REQUIRED"
    """전용 앱으로만 제공된다 (`03 §2`)."""

    CONTROL_DISABLED_OR_INERT = "CONTROL_DISABLED_OR_INERT"
    """task 진입 control 이 **있는데 작동하지 않는다** (disabled / inert / 비활성).

    이 세션의 presence≠operative 결함군에 대응하는 값이다 — **control 이 있는데 작동하지
    않는 것을 '없음'으로 접지 않는다.** control 이 아예 없는 것은 이 값이 아니라
    `TASK_SURFACE_ABSENT` 다. 둘을 합치면 "있지만 안 되는 서비스"와 "아예 없는 서비스"가
    같은 값이 된다.
    """

    FORBIDDEN_ACTION_REQUIRED = "FORBIDDEN_ACTION_REQUIRED"
    """경로가 금지행위를 요구해 중단했다.

    **금지행위를 하지 않았다는 기록이지 실패가 아니다.**
    """

    AUTH_REQUIRED = "AUTH_REQUIRED"
    """과업 경로에서 인증이 불가피해졌다 (`03 §7`). `terminal=AUTH_GATE` 의 사유."""

    EVIDENCE_DEFECT = "EVIDENCE_DEFECT"
    """증거 package 가 불완전하다 — 우리 도구의 결함이다."""

    REPLAY_BROKEN = "REPLAY_BROKEN"
    """`03 §5` — frozen path 재생이 깨졌다. **자유탐색으로 조용히 대체하지 않고** 기록한다."""

    AMBIGUOUS_MULTIPLE_CANDIDATES = "AMBIGUOUS_MULTIPLE_CANDIDATES"
    """후보가 여럿이라 경로를 확정할 수 없다 (`04 §2 action_token=ABSTAIN` 의 사유 중 하나)."""

    OTHER = "OTHER"
    """위 어디에도 안 맞는다. **자유기술 note 가 반드시 함께 와야 한다.**"""

    BUDGET_EXCEEDED = "BUDGET_EXCEEDED"
    """**14번째 값** — `Δ30` 이 추가했다. `A1 §2.6` `MIN-7` 의 자리다.

    `[Δ30 인용]` *"`Δ10-R11` 의 13값에 예산 소진이 없다. **`BUDGET_EXCEEDED` 를 추가한다**
    (14값). 조합: `endpoint_status=ABSTAIN` × `terminal_reason=BUDGET_EXCEEDED`"*

    **`MIN-7` — 예산 소진은 관측 없음이며 activation 수에 대한 주장이 아니다.**
    (`Δ36` ① 이 v3 산출·docstring 에서 그 주장의 어휘 자체를 금지했다.) 그래서 이 값은 terminal 8종
    어디에도 매달리지 않는다(`terminal=None` · `resolution=UNDETERMINED`). 예산을 다 써서
    멈춘 것은 사이트에 대한 진술이 아니라 **우리가 그만 본 것**이다.

    `NO_SAFE_ROUTE_FOUND` 와 **다르다** — 그쪽은 허용 경로를 *소진*했다는 관측이고, 이쪽은
    소진하지 못한 채 멈췄다는 사실이다. 둘을 합치면 "더 볼 게 없었다"와 "더 안 봤다"가
    같은 값이 된다.

    **`MIN-7` 후단: 예산값을 대입하지 않는다.** 이 값에 숫자가 붙지 않는 이유다 — 얼마짜리
    예산이었는지는 manifest 의 수집 파라미터이지 관측 결과가 아니다.
    """

    NO_TASK_CANDIDATE_FOUND = "NO_TASK_CANDIDATE_FOUND"
    """**15번째 값** — `Δ32` 가 추가했다. **페이지에 task 후보 control 이 실제로 없었다.**

    `[Δ32 인용]` 판정표: *"페이지에 후보 control 이 실제로 없다 → **관측** →
    `endpoint_status=ABSTAIN` × `terminal_reason=NO_TASK_CANDIDATE_FOUND` (15번째 값)"*

    **binder 계약 위반과 절대 섞이지 않는다.** `[Δ32 인용]` *"구성요소 간 계약 위반은
    **결코 관측이 아니다.** 사이트에 대해 아무것도 말해주지 않는다."* 형태 불일치로
    후보가 전건 탈락한 것은 `RunnerError`(`runner.CandidateBindingContractError`)이며
    관측 행 자체를 만들지 않는다. 이 값은 **형태가 멀쩡한 채로 0건이 관측된 경우만** 쓴다.

    `AMBIGUOUS_MULTIPLE_CANDIDATES`(후보가 *여럿*이라 못 고름) · `TASK_SURFACE_ABSENT`
    (그 *과업 surface* 자체가 채널에 없음)와도 다른 사건이다 — 셋을 합치면 분모를
    복원할 수 없다.
    """

    PATH_NOT_FOUND_BY_POLICY = "PATH_NOT_FOUND_BY_POLICY"
    """**16번째 값** — `Δ47` 이 추가했다. **선언된 정책이 허용 경로를 찾지 못했다.**

    `[Δ47 인용]` *"`R37` 이 이 범주를 **분석에서 따로 세라**고 요구했다. `OTHER` 에 두면:
    `OTHER` 하나가 **두 뜻**을 갖는다 — '정책이 못 찾았다' 와 '분류되지 않았다' /
    구분이 **자유 텍스트 note 안**에 산다. **note 로만 구분되는 것은 범주가 아니다** /
    세려면 문자열 매칭을 해야 하고, 그 매칭은 다음에 조용히 깨진다."*

    ## 이것이 주장하는 것과 주장하지 않는 것

    - 주장하는 것: `search_strategy` 로 선언된 정책이 이 후보 집합에서 endpoint 까지의
      허용 경로에 도달하지 못했다는 **우리 정책에 대한 사실**.
    - 주장하지 **않는** 것: 사이트에 그런 경로가 **없다**는 것. 그것은
      `terminal=PUBLIC_WEB_UNOBSERVABLE` · `TASK_SURFACE_ABSENT` 이 하는 주장이며
      이 값은 그 주장을 하지 않는다 (`R37` 2항 · `runner.assert_no_path_absence_claim`).

    ## 다른 값들과의 경계

    - `NO_TASK_CANDIDATE_FOUND`(15) — 후보가 **0건**이었다. 페이지에 대한 관측이지 정책에
      대한 사실이 아니다. 이쪽은 후보가 **있었는데** 정책이 못 내려갔다.
    - `BUDGET_EXCEEDED`(14) — 예산을 다 써서 **그만 봤다**. 이쪽은 예산이 남은 채로
      더 갈 곳이 없었다.
    - `AMBIGUOUS_MULTIPLE_CANDIDATES` — 후보가 여럿이라 **고르지 못했다**. 이쪽은 골랐고
      그 끝이 endpoint 가 아니었다.
    - `OTHER` — **분류되지 않았다.** `Δ47` 이전에는 이 값이 `OTHER` + note 로 기록됐고,
      그래서 `OTHER` 하나가 두 뜻을 가졌다. 지금은 갈린다.

    두 번째 축 `path_discovery_outcome=POLICY_DID_NOT_FIND_PATH` 가 **그대로 남아 있고**,
    두 축이 서로를 검증한다 (`Δ47`: *"`path_discovery_outcome` 축은 `B` 가 만든 그대로
    둔다. 두 축이 서로를 검증한다."*). note(`runner.PATH_NOT_FOUND_NOTE`)도 유지되지만
    **구분은 note 에 의존하지 않는다** — 이 값 자체가 범주다.
    """


class TerminalCombinationError(ValueError):
    """`endpoint_status` × `terminal_reason` 이 허용 조합표 밖이다 — 불가능한 기록 시도."""


class TerminalReasonNoteError(ValueError):
    """`terminal_reason=OTHER` 인데 자유기술 note 가 없다 — 스키마 위반."""


#: `endpoint_status` × `terminal_reason` **허용 조합표** (`T-A-V3-STEP1-007` R11).
#:
#: 7×15 격자에서 허용 칸만 열거한다. 나머지는 전부 불가능이며
#: `validate_status_reason()` 이 `TerminalCombinationError` 로 거부한다.
#: 예: `endpoint_status=REACHED` × `TIMEOUT` — 도달했는데 시간초과일 수 없다.
#:
#: `endpoint_status=REACHED` 의 값이 `None` 뿐인 이유는 아래 `_REACHED_REASON_GAP` 참조.
ALLOWED_ENDPOINT_STATUS_REASONS: dict[EndpointStatus, frozenset[TerminalReason | None]] = {
    EndpointStatus.REACHED: frozenset({None}),
    EndpointStatus.AUTH_GATE: frozenset({TerminalReason.AUTH_REQUIRED}),
    EndpointStatus.PUBLIC_WEB_UNOBSERVABLE: frozenset(
        {
            TerminalReason.NO_PUBLIC_MOBILE_WEB,
            TerminalReason.TASK_SURFACE_ABSENT,
            TerminalReason.OTHER,
        }
    ),
    EndpointStatus.APP_REQUIRED: frozenset({TerminalReason.APP_REQUIRED}),
    EndpointStatus.EVIDENCE_DEFECT: frozenset(
        {TerminalReason.EVIDENCE_DEFECT, TerminalReason.TIMEOUT}
    ),
    EndpointStatus.BLOCKED: frozenset({TerminalReason.WAF_BLOCK, TerminalReason.ACTIVE_CHALLENGE}),
    EndpointStatus.ABSTAIN: frozenset(
        {
            TerminalReason.FORBIDDEN_ACTION_REQUIRED,
            TerminalReason.CONTROL_DISABLED_OR_INERT,
            TerminalReason.REPLAY_BROKEN,
            TerminalReason.AMBIGUOUS_MULTIPLE_CANDIDATES,
            # Δ30 — MIN-7. 예산 소진은 관측 없음이며 activation 수 주장이 아니다 (Δ36 ①).
            TerminalReason.BUDGET_EXCEEDED,
            # Δ32 — 페이지에 후보 control 이 실제로 없었다(관측). 계약 위반이 아니다.
            TerminalReason.NO_TASK_CANDIDATE_FOUND,
            # Δ47 — 선언된 정책이 경로를 찾지 못했다. OTHER 에서 떼어낸 16번째 값이며
            # `path_discovery_outcome=POLICY_DID_NOT_FIND_PATH` 와 짝이 된다.
            TerminalReason.PATH_NOT_FOUND_BY_POLICY,
            TerminalReason.OTHER,
        }
    ),
}

#: **[명세 공백 — A 판단 필요]** A 규칙은 *"모든 terminal 관측은 둘 다 갖는다"* 인데
#: `endpoint_status=REACHED` 는 **terminal 관측이 아니다**(`resolution` 이
#: `NOT_TERMINAL_ENDPOINT_REACHED`). `04 §4` 와 `02 §5` 어디에도 도달에 대응하는
#: `terminal_reason` 값이 없다. 지어내지 않고 `None` 으로 둔다 — 이 공백은 known
#: limitation 으로 보고한다.
_REACHED_REASON_GAP = (
    "endpoint_status=REACHED 에 대응하는 terminal_reason 값이 04 §4 · 02 §5 에 없다. "
    "REACHED 는 terminal 관측이 아니므로 None 으로 두었다 — A 확인 필요."
)


def validate_status_reason(
    endpoint_status: EndpointStatus | None,
    terminal_reason: TerminalReason | None,
    note: str | None = None,
) -> None:
    """허용 조합표와 `OTHER` note 의무를 강제한다. runner 스키마와 C GATE 1 의 공용 진입점.

    Raises:
        TerminalCombinationError: 조합표 밖의 `endpoint_status` × `terminal_reason`.
        TerminalReasonNoteError: `terminal_reason=OTHER` 인데 note 가 비었다.
    """
    if terminal_reason is TerminalReason.OTHER and not (note or "").strip():
        raise TerminalReasonNoteError(
            "terminal_reason=OTHER 는 자유기술 note 가 필수다 (T-A-V3-STEP1-007 R11)"
        )
    if endpoint_status is None:
        if terminal_reason is not None:
            raise TerminalCombinationError(
                f"endpoint_status 가 없는데 terminal_reason={terminal_reason.value} 가 있다"
            )
        return
    allowed = ALLOWED_ENDPOINT_STATUS_REASONS[endpoint_status]
    if terminal_reason not in allowed:
        shown = terminal_reason.value if terminal_reason else "None"
        raise TerminalCombinationError(
            f"불가능 조합: endpoint_status={endpoint_status.value} × terminal_reason={shown}. "
            f"허용: {sorted(r.value if r else 'None' for r in allowed)}"
        )


class ZeroActivationClaimError(ValueError):
    """`Δ32-R29` — 후보 0건인데 `endpoint_status=REACHED` 를 주장했다.

    `[Δ32-R29 인용]` *"**0 은 관측이 아니라 주장이다. 주장에는 근거가 필요하다.**"* /
    *"**후보 0건은 어떤 경우에도 `endpoint_status=REACHED` 를 낼 수 없다.** 스키마가 그
    조합을 거부한다."*
    """


def validate_reached_requires_binding(
    endpoint_status: EndpointStatus | None,
    *,
    task_candidate_count: int | None,
) -> None:
    """`Δ32-R29` — `endpoint_status=REACHED` 는 **최소 하나의 바인딩된 후보**를 요구한다.

    `task_candidate_count=None`(미관측)은 거부하지 않는다 — 미관측을 `0` 으로 접으면
    그 자체가 `R13` 이 막는 "부재의 증거 없이 부재를 적는 것"이 된다. 거부 대상은
    **관측된 0** 뿐이다.

    Raises:
        ZeroActivationClaimError: `REACHED` × `task_candidate_count == 0`.
    """
    if endpoint_status is not EndpointStatus.REACHED:
        return
    if task_candidate_count is None:
        return
    if task_candidate_count <= 0:
        raise ZeroActivationClaimError(
            "Δ32-R29 위반: 바인딩된 후보가 0건인데 endpoint_status=REACHED 를 주장했다. "
            "0 은 관측이 아니라 주장이며 근거(① endpoint contract 충족 증거 "
            "② 최소 하나의 바인딩된 후보)가 필요하다."
        )


#: terminal → `endpoint_status` (다대일). 모듈 docstring 표의 실행 가능한 정본.
TERMINAL_TO_ENDPOINT_STATUS: dict[TerminalKind, EndpointStatus] = {
    TerminalKind.AUTH_GATE: EndpointStatus.AUTH_GATE,
    TerminalKind.PUBLIC_WEB_UNOBSERVABLE: EndpointStatus.PUBLIC_WEB_UNOBSERVABLE,
    TerminalKind.APP_REQUIRED: EndpointStatus.APP_REQUIRED,
    TerminalKind.WAF_OR_CHALLENGE: EndpointStatus.BLOCKED,
    TerminalKind.TIMEOUT: EndpointStatus.EVIDENCE_DEFECT,
    TerminalKind.EVIDENCE_DEFECT: EndpointStatus.EVIDENCE_DEFECT,
    TerminalKind.NO_SAFE_ROUTE_FOUND: EndpointStatus.ABSTAIN,
    TerminalKind.SAFETY_STOP: EndpointStatus.ABSTAIN,
}

#: 우선순위. 모듈 docstring "우선순위" 절의 실행 가능한 정본.
TERMINAL_PRECEDENCE: tuple[TerminalKind, ...] = (
    TerminalKind.EVIDENCE_DEFECT,
    TerminalKind.TIMEOUT,
    TerminalKind.WAF_OR_CHALLENGE,
    TerminalKind.APP_REQUIRED,
    TerminalKind.PUBLIC_WEB_UNOBSERVABLE,
    TerminalKind.AUTH_GATE,
    TerminalKind.SAFETY_STOP,
    TerminalKind.NO_SAFE_ROUTE_FOUND,
)


@dataclass(frozen=True)
class TerminalSignals:
    """분류 입력. 각 필드는 **하나의 관측/판단**이며 서로 대체하지 않는다.

    `bool | None` 인 필드에서 `None` 은 *미관측*이고 `False`(관측했더니 아님)와 다르다.
    """

    evidence_complete: bool | None = None
    """증거 package 가 온전한가. `False` → `EVIDENCE_DEFECT`. `None` 이면 판정 근거가
    없으므로 **defect 로 몰지 않는다** (우리 결함이라고 단정하는 것도 주장이다)."""

    evidence_defect_reason: str | None = None
    """어느 증거가 왜 깨졌는지. 사이트에 대한 진술이 아니라 우리 파이프라인 진단이다."""

    run_timed_out: bool = False
    """run 이 제한 시간 안에 끝나지 않았다."""

    active_blocking_challenge: bool = False
    """`03 §8` — **능동적으로 진행을 막고 있는** challenge. 숨은 CAPTCHA iframe 존재만으로
    참이 아니다. 이 값이 참이어도 해결·우회하지 않는다."""

    waf_block_observed: bool = False
    """서버/WAF 가 응답 자체를 거부했다(차단 페이지·403 interstitial 등). challenge 가
    제시된 것과 다르며, 둘 다 참이면 `terminal_reason=WAF_BLOCK` 이 앞선다 — 응답을 아예
    못 받았다면 challenge 를 관측했다고 말할 수 없기 때문이다."""

    challenge_kind: str | None = None
    """관측된 challenge 의 종류(예: `RECAPTCHA` / `WAF_INTERSTITIAL`). 관측 기록 전용."""

    app_required: bool = False
    """`03 §2` — 공개 모바일웹이 과업을 싣지 않고 앱으로만 제공한다."""

    app_install_prompt_present: bool = False
    """앱 설치 유도 배너/모달이 떴다. **`APP_REQUIRED` 의 근거가 아니다** — obstruction 이다."""

    public_web_task_observable: bool | None = None
    """공개 모바일웹 경로에서 이 과업을 관측할 수 있는가. `False` →
    `terminal=PUBLIC_WEB_UNOBSERVABLE`. `None` 은 미판정이며 `False` 로 취급하지 않는다."""

    public_mobile_web_present: bool | None = None
    """공개 모바일웹 **채널 자체**가 있는가. `public_web_task_observable=False` 일 때
    사유를 가른다: `True` → `TASK_SURFACE_ABSENT`(채널은 있는데 과업이 없다),
    `False` → `NO_PUBLIC_MOBILE_WEB`(채널이 없다), `None` → 가를 수 없으므로
    `OTHER` + note. 미관측을 한쪽으로 밀어 넣지 않는다."""

    generic_login_control_present: bool = False
    """페이지에 일반 로그인 control 이 있다. `03 §7` — **이것만으로 중단하지 않는다.**
    `terminal=AUTH_GATE` 판정에 쓰이지 않으며, 이 필드를 근거로 삼는 분기는 이 모듈에 없다."""

    auth_required_to_proceed: bool = False
    """과업 경로에서 인증이 **불가피**해졌다. `03 §7` 이 말하는 `terminal=AUTH_GATE` 조건이다."""

    auth_gate_stage: AuthGateStage = AuthGateStage.NONE
    """auth 를 만난 위치. terminal 이 `terminal=AUTH_GATE` 가 아니어도 기록된다."""

    prohibited_action_required: bool = False
    """`03 §6`·`§8` — 진행하려면 금지 행위(결제/구매/자격증명 입력/CAPTCHA 해결 등)를
    해야 한다. 그래서 우리가 멈춘다."""

    prohibited_action_kind: str | None = None
    """무엇이 금지 행위였는지. 관측 기록 전용."""

    permitted_routes_exhausted: bool = False
    """허용된 탐색을 소진했다. endpoint 미도달 시 `terminal=NO_SAFE_ROUTE_FOUND` 근거."""

    task_control_disabled_or_inert: bool = False
    """task 진입 control 을 **찾았는데 작동하지 않는다** (disabled/inert).

    control 이 아예 없는 것과 **다르다**. presence≠operative — 있는데 안 되는 것을
    '없음'으로 접지 않는다. 후자는 `public_web_task_observable=False` +
    `public_mobile_web_present=True` 로 들어와 `TASK_SURFACE_ABSENT` 가 된다."""

    replay_broken: bool = False
    """`03 §5` — frozen path 재생이 깨졌다. 자유탐색으로 조용히 대체하지 않는다."""

    ambiguous_multiple_candidates: bool = False
    """후보가 여럿이라 경로를 확정할 수 없다."""

    other_reason_note: str | None = None
    """`terminal_reason=OTHER` 로 떨어질 때 붙일 자유기술 note. 호출부가 주지 않으면
    이 모듈이 무엇을 가르지 못했는지 서술한 note 를 생성한다 — note 없는 `OTHER` 는
    만들지 않는다."""

    endpoint_reached: bool = False
    """사전정의 endpoint 가 충족됐다 (`04 §2 ENDPOINT_REACHED`)."""

    scout_budget_exhausted: bool = False
    """`Δ30` / `A1 §2.6 MIN-7` — 수집 예산(`MAX_ACTIVATIONS_PER_TASK` 등)을 소진해 멈췄다.

    **관측 없음이며 activation 수에 대한 주장이 아니다** (`Δ36` ①).
    `permitted_routes_exhausted`(허용 경로를 *소진*했다)
    와 다르다 — 그쪽은 관측이고 이쪽은 관측을 그만둔 것이다. 둘 다 참이면 terminal 관측이
    앞서고, 이 사실은 `notes` 에 남는다(합치지 않는다)."""

    policy_did_not_find_path: bool = False
    """`Δ47` — 후보는 **있었는데** 선언된 정책이 endpoint 까지의 허용 경로를 찾지 못했다.

    `scout_budget_exhausted`(예산을 다 써서 그만 봤다)와 **다른 사실**이고,
    `task_candidate_count == 0`(후보가 아예 없었다)과도 **다른 사실**이다. 셋을 한 값에
    담으면 분기가 넓은 서비스에서 더 자주 나는 탐색 실패가 사이트의 성질로 집계된다
    (`Δ43`/`R37`).

    이 값이 참이면 `endpoint_status=ABSTAIN` × `terminal_reason=PATH_NOT_FOUND_BY_POLICY`
    다. **사이트에 경로가 없다는 주장이 아니다** — 그 주장은 이 모듈 어디에도 없다.
    """

    task_candidate_count: int | None = None
    """`Δ32` — binding 단계에서 **실제로 바인딩된 후보 수**. `None` 은 미관측(binder 미주입)
    이며 `0`(관측했더니 후보가 없었다)과 다르다 — `Δ10-R13` 의 `NONE` ≠ `UNDETERMINED` 와
    같은 구분이다.

    `0` 이면 `endpoint_status=ABSTAIN` × `terminal_reason=NO_TASK_CANDIDATE_FOUND` 다.
    **`0` 과 `endpoint_status=REACHED` 는 어떤 경우에도 함께 나올 수 없다**(`R29`) —
    `validate_reached_requires_binding()` 이 거부한다.

    형태 불일치로 후보가 탈락한 경우는 **이 필드로 오지 않는다.** 그건 계약 위반이라
    관측 행을 만들지 않고 `RunnerError` 로 멈춘다(`Δ32`)."""


@dataclass(frozen=True)
class TerminalOutcome:
    """분류 결과. terminal 축과 `endpoint_status` 축을 **둘 다** 보존한다."""

    terminal: TerminalKind | None
    endpoint_status: EndpointStatus | None
    terminal_reason: TerminalReason | None
    terminal_reason_note: str | None
    resolution: TerminalResolution
    auth_gate_stage: AuthGateStage
    competing_signals: tuple[TerminalKind, ...] = ()
    """동시에 참이었으나 우선순위에서 밀린 terminal 들. 조용히 버리지 않는다."""

    evidence_defect_reason: str | None = None
    challenge_kind: str | None = None
    prohibited_action_kind: str | None = None
    notes: tuple[str, ...] = field(default_factory=tuple)


def _matched_terminals(signals: TerminalSignals) -> list[TerminalKind]:
    """참인 terminal 조건을 **전부** 모은다. 우선순위는 여기서 적용하지 않는다."""
    matched: list[TerminalKind] = []

    if signals.evidence_complete is False:
        matched.append(TerminalKind.EVIDENCE_DEFECT)
    if signals.run_timed_out:
        matched.append(TerminalKind.TIMEOUT)
    if signals.active_blocking_challenge:
        matched.append(TerminalKind.WAF_OR_CHALLENGE)
    if signals.app_required:
        matched.append(TerminalKind.APP_REQUIRED)
    if signals.public_web_task_observable is False:
        matched.append(TerminalKind.PUBLIC_WEB_UNOBSERVABLE)
    # `03 §7` — generic login control 존재는 근거가 아니다. 여기서 참조하지 않는다.
    if signals.auth_required_to_proceed:
        matched.append(TerminalKind.AUTH_GATE)
    if signals.prohibited_action_required:
        matched.append(TerminalKind.SAFETY_STOP)
    no_route = (
        signals.permitted_routes_exhausted
        or signals.task_control_disabled_or_inert
        or signals.replay_broken
        or signals.ambiguous_multiple_candidates
    )
    if no_route and not signals.endpoint_reached:
        matched.append(TerminalKind.NO_SAFE_ROUTE_FOUND)

    return matched


def _resolve_reason(
    chosen: TerminalKind, signals: TerminalSignals
) -> tuple[TerminalReason, str | None]:
    """고른 terminal 에 대응하는 `terminal_reason` 과 (필요 시) note 를 낸다.

    한 terminal 이 여러 사유를 가질 수 있는 곳은 셋뿐이며, 각각 명시된 순서로 가른다:

    - `terminal=WAF_OR_CHALLENGE` → `WAF_BLOCK` 이 `ACTIVE_CHALLENGE` 보다 앞선다.
    - `terminal=PUBLIC_WEB_UNOBSERVABLE` → `public_mobile_web_present` 로 가르고,
      미관측이면 `OTHER` + note (한쪽으로 밀어 넣지 않는다).
    - `terminal=NO_SAFE_ROUTE_FOUND` → `CONTROL_DISABLED_OR_INERT` > `REPLAY_BROKEN`
      > `AMBIGUOUS_MULTIPLE_CANDIDATES` > `OTHER`. 가장 구체적인 관측이 앞선다.
    """
    note = signals.other_reason_note

    if chosen is TerminalKind.EVIDENCE_DEFECT:
        return TerminalReason.EVIDENCE_DEFECT, None
    if chosen is TerminalKind.TIMEOUT:
        return TerminalReason.TIMEOUT, None
    if chosen is TerminalKind.APP_REQUIRED:
        return TerminalReason.APP_REQUIRED, None
    if chosen is TerminalKind.AUTH_GATE:
        return TerminalReason.AUTH_REQUIRED, None
    if chosen is TerminalKind.SAFETY_STOP:
        # 금지행위를 하지 않았다는 기록이지 실패가 아니다.
        return TerminalReason.FORBIDDEN_ACTION_REQUIRED, None
    if chosen is TerminalKind.WAF_OR_CHALLENGE:
        if signals.waf_block_observed:
            return TerminalReason.WAF_BLOCK, None
        return TerminalReason.ACTIVE_CHALLENGE, None
    if chosen is TerminalKind.PUBLIC_WEB_UNOBSERVABLE:
        if signals.public_mobile_web_present is False:
            return TerminalReason.NO_PUBLIC_MOBILE_WEB, None
        if signals.public_mobile_web_present is True:
            return TerminalReason.TASK_SURFACE_ABSENT, None
        return TerminalReason.OTHER, note or (
            "public_mobile_web_present 미관측 — NO_PUBLIC_MOBILE_WEB 과 "
            "TASK_SURFACE_ABSENT 를 가를 수 없다"
        )

    # chosen is TerminalKind.NO_SAFE_ROUTE_FOUND
    if signals.task_control_disabled_or_inert:
        # control 이 있는데 작동하지 않는 것을 '없음'으로 접지 않는다.
        return TerminalReason.CONTROL_DISABLED_OR_INERT, None
    if signals.replay_broken:
        return TerminalReason.REPLAY_BROKEN, None
    if signals.ambiguous_multiple_candidates:
        return TerminalReason.AMBIGUOUS_MULTIPLE_CANDIDATES, None
    return TerminalReason.OTHER, note or ("허용 경로를 소진했으나 더 이상의 사유를 관측하지 못했다")


def classify_terminal(signals: TerminalSignals) -> TerminalOutcome:
    """관측 신호 묶음을 terminal 8종 중 하나 + `endpoint_status` 로 분류한다.

    반환 규칙:

    - terminal 조건이 하나라도 참이면 `TERMINAL_PRECEDENCE` 순서로 하나를 고르고,
      나머지 참인 조건은 `competing_signals` 에 남긴다. **합치지 않는다.**
    - 아무 terminal 조건도 참이 아니고 `endpoint_reached` 면
      `NOT_TERMINAL_ENDPOINT_REACHED` / `endpoint_status = REACHED`.
    - 둘 다 아니면 `resolution=UNDETERMINED` / `terminal=None` / `endpoint_status=ABSTAIN`.
      **산출 불능은 `None` 이다. `FAILED` 로 바꾸지 않는다.**

    `endpoint_reached` 는 `EVIDENCE_DEFECT`·`TIMEOUT` 을 **덮지 못한다**. 증거가 깨졌거나
    run 이 안 끝났으면 endpoint 도달 주장 자체를 신뢰할 수 없기 때문이다. 그 경우
    `endpoint_reached_claim_unverifiable` note 를 남긴다.
    """
    matched = _matched_terminals(signals)
    notes: list[str] = []

    # `Δ32-R29` — 후보 0건 위에서 REACHED 를 주장할 수 없다. 산출 **전에** 거부한다.
    if signals.endpoint_reached:
        validate_reached_requires_binding(
            EndpointStatus.REACHED, task_candidate_count=signals.task_candidate_count
        )
    if signals.scout_budget_exhausted and matched:
        # MIN-7 — 예산 소진은 terminal 관측을 이기지 못한다. 그러나 지워지지도 않는다.
        notes.append("scout_budget_exhausted_with_terminal_signal")

    if not matched:
        if signals.endpoint_reached:
            # `endpoint_status=REACHED` 는 terminal 관측이 아니므로 사유가 없다.
            # 04 §4 · 02 §5 에 대응 값이 없다 — 지어내지 않는다 (`_REACHED_REASON_GAP`).
            validate_status_reason(EndpointStatus.REACHED, None, None)
            return TerminalOutcome(
                terminal=None,
                endpoint_status=EndpointStatus.REACHED,
                terminal_reason=None,
                terminal_reason_note=None,
                resolution=TerminalResolution.NOT_TERMINAL_ENDPOINT_REACHED,
                auth_gate_stage=signals.auth_gate_stage,
                challenge_kind=signals.challenge_kind,
            )
        if signals.evidence_complete is None:
            notes.append("evidence_complete_unobserved")

        # `Δ32` — 후보 0건은 **관측**이다. 사유가 있으므로 `OTHER` 로 흘리지 않는다.
        # 형태 불일치(계약 위반)는 여기까지 오지 않는다 — runner 가 먼저 멈춘다.
        if signals.task_candidate_count == 0:
            zero_note = signals.other_reason_note or (
                "binding 단계에서 관측된 task 후보 control 이 0건이었다 "
                "(형태 불일치가 아니라 관측 — Δ32)"
            )
            validate_status_reason(
                EndpointStatus.ABSTAIN, TerminalReason.NO_TASK_CANDIDATE_FOUND, zero_note
            )
            return TerminalOutcome(
                terminal=None,
                endpoint_status=EndpointStatus.ABSTAIN,
                terminal_reason=TerminalReason.NO_TASK_CANDIDATE_FOUND,
                terminal_reason_note=zero_note,
                resolution=TerminalResolution.UNDETERMINED,
                auth_gate_stage=signals.auth_gate_stage,
                challenge_kind=signals.challenge_kind,
                notes=tuple(notes),
            )

        # `Δ30` / `MIN-7` — 예산을 다 써서 멈춘 것은 **관측 없음**이며 activation 수에
        # 대한 주장이 아니다 (`Δ36` ①). 예산값은 대입하지 않는다(MIN-7 후단).
        if signals.scout_budget_exhausted:
            budget_note = signals.other_reason_note or (
                "수집 예산을 소진해 탐색을 멈췄다 — activation 수에 대한 주장이 아니라 "
                "관측 없음이다 (A1 §2.6 MIN-7)"
            )
            validate_status_reason(
                EndpointStatus.ABSTAIN, TerminalReason.BUDGET_EXCEEDED, budget_note
            )
            return TerminalOutcome(
                terminal=None,
                endpoint_status=EndpointStatus.ABSTAIN,
                terminal_reason=TerminalReason.BUDGET_EXCEEDED,
                terminal_reason_note=budget_note,
                resolution=TerminalResolution.UNDETERMINED,
                auth_gate_stage=signals.auth_gate_stage,
                challenge_kind=signals.challenge_kind,
                notes=tuple(notes),
            )

        # `Δ47` — 후보는 있었는데 **선언된 정책이 허용 경로를 찾지 못했다.** `OTHER` 에
        # 두면 한 값이 두 뜻('정책이 못 찾았다'·'분류되지 않았다')을 갖고 구분이 자유
        # 텍스트 note 안에 산다. `[Δ47 인용]` *"note 로만 구분되는 것은 범주가 아니다."*
        #
        # 예산 소진 검사 **뒤**에 온다: 예산을 다 써서 멈춘 것은 "더 안 봤다" 이고
        # 이 값은 "더 볼 곳이 없었다" 이므로, 둘 다 참이면 관측을 그만둔 사실이 앞선다
        # (`runner._to_mart` 의 순서와 같다 — 두 자리가 어긋나면 같은 run 이 두 값을 낸다).
        if signals.policy_did_not_find_path:
            not_found_note = signals.other_reason_note or (
                "선언된 정책이 허용 경로를 찾지 못했다 — 사이트에 경로가 부재한다는 "
                "관측이 아니라 이 정책이 찾지 못했다는 사실이다 (R37)"
            )
            validate_status_reason(
                EndpointStatus.ABSTAIN, TerminalReason.PATH_NOT_FOUND_BY_POLICY, not_found_note
            )
            return TerminalOutcome(
                terminal=None,
                endpoint_status=EndpointStatus.ABSTAIN,
                terminal_reason=TerminalReason.PATH_NOT_FOUND_BY_POLICY,
                terminal_reason_note=not_found_note,
                resolution=TerminalResolution.UNDETERMINED,
                auth_gate_stage=signals.auth_gate_stage,
                challenge_kind=signals.challenge_kind,
                notes=tuple(notes),
            )

        # `endpoint_status=ABSTAIN` 을 사유 없이 내보내지 않는다 — 그게 A 가 막으려는
        # 해상도 손실이다. 어떤 terminal 신호도 관측되지 않았다는 것을 note 로 적는다.
        undetermined_note = signals.other_reason_note or (
            "어떤 terminal 신호도 관측되지 않았고 endpoint 도달도 관측되지 않았다"
        )
        validate_status_reason(EndpointStatus.ABSTAIN, TerminalReason.OTHER, undetermined_note)
        return TerminalOutcome(
            terminal=None,
            endpoint_status=EndpointStatus.ABSTAIN,
            terminal_reason=TerminalReason.OTHER,
            terminal_reason_note=undetermined_note,
            resolution=TerminalResolution.UNDETERMINED,
            auth_gate_stage=signals.auth_gate_stage,
            challenge_kind=signals.challenge_kind,
            notes=tuple(notes),
        )

    order = {kind: i for i, kind in enumerate(TERMINAL_PRECEDENCE)}
    chosen = min(matched, key=lambda k: order[k])
    competing = tuple(k for k in TERMINAL_PRECEDENCE if k in matched and k is not chosen)

    if signals.endpoint_reached and chosen in (
        TerminalKind.EVIDENCE_DEFECT,
        TerminalKind.TIMEOUT,
    ):
        notes.append("endpoint_reached_claim_unverifiable")
    elif signals.endpoint_reached:
        notes.append("endpoint_reached_signal_present_with_terminal")

    if signals.app_install_prompt_present and chosen is not TerminalKind.APP_REQUIRED:
        # 설치 배너는 obstruction 이지 terminal 근거가 아니다. 기록만 남긴다.
        notes.append("app_install_prompt_present_not_terminal_evidence")
    if signals.generic_login_control_present and chosen is not TerminalKind.AUTH_GATE:
        notes.append("generic_login_control_present_not_terminal_evidence")

    endpoint_status = TERMINAL_TO_ENDPOINT_STATUS[chosen]
    reason, reason_note = _resolve_reason(chosen, signals)
    # 산출 직전에 조합표를 스스로 통과시킨다 — 이 모듈이 불가능 조합을 만들 수 없다.
    validate_status_reason(endpoint_status, reason, reason_note)

    return TerminalOutcome(
        terminal=chosen,
        endpoint_status=endpoint_status,
        terminal_reason=reason,
        terminal_reason_note=reason_note,
        resolution=TerminalResolution.TERMINAL,
        auth_gate_stage=signals.auth_gate_stage,
        competing_signals=competing,
        evidence_defect_reason=signals.evidence_defect_reason,
        challenge_kind=signals.challenge_kind,
        prohibited_action_kind=signals.prohibited_action_kind,
        notes=tuple(notes),
    )
