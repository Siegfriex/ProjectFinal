# Collection & Measurement Spec v3.0

## 1. 공통 모바일 환경

- fresh browser context
- no login / no stored cookie
- locale `ko-KR`, timezone `Asia/Seoul`
- mobile UA, touch enabled
- viewport `390×844 CSS px`
- requested/final URL, timestamp, UA, viewport 기록

## 2. Precheck — Main 50 이전 필수

각 candidate URL에 대해 **task를 수행하지 않고** channel eligibility만 확인한다.

`ELIGIBLE_PUBLIC_MOBILE_WEB / APP_REQUIRED_EXCLUDE / ACCESS_BLOCKED_REVIEW / URL_REMAP_REQUIRED`

APP_REQUIRED_EXCLUDE는 main frame에서 교체한다. app-only를 main outcome으로 사용하지 않는다.

## 3. L0 + Scroll-only Surface Capture

S0 최초 안정화 후 DOM/AX/computed CSS/geometry/screenshot/probe 수집. 이후 고정 scroll 정책으로 S1...Sn을 만들고 task-entry control의 최초 관측 state를 기록한다.

Scroll은 discovery/exposure 변수이며 activation depth에 포함하지 않는다.

## 4. Task-specific Candidate Binding

v3 collector는 task family를 맞히지 않는다. 입력에 이미 `task_id + endpoint_contract`가 있다.

후보 source:
- button/link/tab/menuitem/input/searchbox/card
- visible text / accessible name / placeholder / nearby heading / href
- DOM role/tag / AX role/name
- geometry / visibility / hittability

Rule/NLP/embedding을 후보 ranking 보조로 쓸 수 있으나 **task label을 변경할 수 없다.**

## 5. Scout → Freeze → Replay

### Scout
사전지정 task endpoint까지 최소 허용 path를 발견한다. 각 activation마다 before/after evidence를 저장한다.

### Freeze
성공/terminal path를 normalized action tokens + raw selector/evidence로 manifest화.

### Replay
본수집은 frozen path를 deterministic하게 재생한다. 깨지면 `REPLAY_BROKEN`으로 기록하고 자유탐색으로 조용히 대체하지 않는다.

## 6. Action inclusion

Depth에 포함:
- link/button/tab/menu open
- category/function/result select
- state-changing menu/drawer reveal

Depth에서 제외:
- scroll
- passive load / redirect / wait
- text 한 글자 입력
- popup dismiss

단 `flow_step_count`에는 task-intent typing/submit을 별도 token으로 보존한다.

## 7. Auth

- generic login 버튼 존재만으로 중단 금지.
- task-specific path를 따라가다 auth가 불가피한 순간 `AUTH_GATE` terminal.
- auth stage를 `BEFORE_TASK_DISCOVERY / AFTER_TASK_SELECT / AT_ENDPOINT`로 기록.
- credential 입력·login submit·본인인증 금지.

## 8. Transaction / CAPTCHA

- 구매/장바구니/결제/송금/예약 state-changing activation 금지.
- 상품 상세처럼 endpoint 전 거래 control 존재 확인은 허용하되 누르지 않는다.
- CAPTCHA 해결/우회 금지. active blocking challenge만 terminal.

## 9. Obstruction

popup/modal/banner/fixed/sticky 후보를 수집하되 primary obstruction은 **task-specific**으로 판정한다.

- `task_control_occlusion`
- `dismiss_required_for_task`
- `forced_dismissal_count`

geometry overlap만으로 modal 의미를 확정하지 않는다.

## 10. Evidence package

각 state/step:
- DOM
- AX
- screenshot
- probe/CSS geometry
- URL
- selected control facts
- manifest SHA

AI review는 evidence package만 받고 새로운 기준을 만들 수 없다.

## 11. Current 12 Method Qualification

기존 `V2_DIAGNOSTIC` 12를 끝까지 실행해 다음 기술능력을 검증한다.

- target-specific control binding
- visible label vs accessible name
- bbox / spatial zone
- icon-only/control type
- menu/drawer reveal + direction
- step sequence
- auth gate provenance
- task-specific obstruction
- evidence identity / exactly-once / firewall

12는 효과크기 추정 표본이 아니다.

## 12. Qualification exit

`METHOD_QUALIFIED` 조건:
- systemic schema mismatch 없음
- evidence lineage complete
- prohibited action 0
- manifest outside access 0
- sequence/geometry/name fields 재현 가능
- C 독립 replay/recompute 통과

12 PASS 이후에도 full59를 자동 실행하지 않는다. v3 main target precheck/freeze로 넘어간다.
