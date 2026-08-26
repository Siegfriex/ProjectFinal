# 데이터 수집·측정 명세 v2.0

이 문서는 “웹사이트에서 정확히 무엇을 가져오고, 어디서 멈추는가”를 설명한다.

---

## 1. 수집 원칙

브라우저가 이미 알고 있는 정보는 AI가 다시 추정하지 않는다.

우선순위:

1. Playwright / Browser API
2. DOM / AX / CSS / geometry
3. pixel / image difference
4. NLP / embedding
5. multimodal AI
6. 인간 최대 5건

---

## 2. 공통 모바일 환경

- fresh browser context
- 로그인 상태 없음
- 저장 cookie 없음
- locale: ko-KR
- timezone: Asia/Seoul
- mobile UA
- touch enabled
- 기준 viewport는 기존 프로토콜의 390×844 CSS px 유지
- 수집시각 기록
- requested URL과 final URL 모두 기록

---

## 3. L0 수집

웹페이지 최초 진입 후 고정된 안정화 대기 규칙을 적용한다.

수집:

- 최초 viewport screenshot
- full-page screenshot
- DOM snapshot
- AX tree
- computed CSS
- bounding box
- visible interactive element
- text/color/background feature
- animation / autoplay
- modal candidate
- body scroll lock
- primary-action candidate

L0에서는 대표기능을 아직 클릭하지 않는다.

---

## 4. KWCAG raw feature

기존 Pilot probe에서 재사용 가능한 기능:

- text contrast
- target geometry
- accessible name / label
- media autoplay
- animation
- keyboard-operability signals
- DOM vs visual ordering
- landmark/heading 등

단, Main Study에서는 raw feature collector와 verdict를 분리한다.

probe는 **판정하지 않고 raw feature만 저장**한다.

---

## 5. Popup / Modal 검출

### 1차 후보

다음 중 하나 이상이면 candidate.

- `<dialog>`
- `role=dialog`
- `aria-modal=true`
- fixed/sticky
- viewport 앞쪽 고 z-index
- backdrop
- body scroll lock
- pointer interception
- focus containment

### 2차 공간검사

viewport와 실제로 겹치는지 계산.

### 3차 blocking 여부

- 대표기능을 가리는가
- 대표기능 진입 전에 닫아야 하는가
- 화면의 큰 부분을 덮는가

### 4차 의미분류

DOM text/accessible name으로 우선 분류.

모호하면 screenshot crop + DOM/AX 요약을 VLM에 전달.

---

## 6. 대표기능 후보 찾기

후보 source:

- button
- link
- input
- role=button/link/tab
- navigation item
- prominent card

각 후보에서:

- accessible name
- visible text
- nearby heading
- href
- role
- bbox
- viewport visibility

를 추출한다.

Interaction archetype의 endpoint 설명과 embedding similarity를 계산해 후보를 ranking한다.

모호하면 AI review.

---

## 7. L1 Scout

Scout의 목적은 “최소 경로 발견”.

자유롭게 full task를 수행하지 않는다.

각 activation 후:

- URL
- DOM state key
- screenshot
- clicked control
- endpoint signal
- popup
- auth gate

를 기록한다.

다음 상태가 나오면 즉시 종료:

- FUNCTION_ENDPOINT_REACHED
- AUTH_GATE_REACHED
- PAYMENT_GATE_REACHED
- PERSONAL_DATA_REQUIRED
- CAPTCHA
- BLOCKED
- UNRESOLVED

결제·본인인증을 우회하지 않는다.

---

## 8. Path Freeze와 Replay

Scout가 발견한 경로는 task manifest로 저장한다.

본수집은 VLM이 매번 사이트를 다시 탐색하지 않고 deterministic replay한다.

`Scout → Freeze → Replay`

replay가 깨지면 상태를 기록하고 다시 자유탐색으로 조용히 대체하지 않는다.

---

## 9. Depth 계산

activation 예:

- button tap
- link tap
- menu open
- item select

제외:

- 텍스트 한 글자씩 입력
- passive loading
- redirect 자체
- server wait
- scroll distance
- popup dismiss

Popup dismiss는 `forced_dismissal_count`에 따로 기록.

---

## 10. AI Review

AI에게는 원본 전체 사이트를 무제한 탐색시키지 않는다.

항상 evidence package만 전달한다.

예:

- screenshot crop
- surrounding screenshot
- DOM facts
- AX facts
- bbox
- relevant text
- 허용 label 목록
- rule excerpt

출력은 JSON classification only.

자유로운 새 기준 생성 금지.

---

## 11. Evidence Identity

한 observation은 정확히 다음과 대응해야 한다.

- DOM
- AX
- screenshot
- probe
- manifest

Task step도 before/after evidence가 trace와 연결되어야 한다.

display name을 file id로 사용하지 않는다.

hash-based observation id 사용.

---

## 12. Append-only

같은 evidence를 덮어쓰지 않는다.

- 재수집 → 새 evidence run
- 같은 evidence 재판정 → 새 judgment version

---

## 13. 수집 실패

다음은 접근성 FAIL이 아니다.

- ACCESS_BLOCKED
- ROBOTS/transport issue
- browser crash
- page timeout
- app-only

별도 measurement status로 기록.

---

## 14. E000_V2 Smoke

본수집 전에 8~12개 서비스로 반드시 검증한다.

포함:

- QUERY
- CONTENT_OPEN
- ITEM_DETAIL
- PLACE_LOOKUP
- FINANCIAL_ACTION_ENTRY
- popup-heavy
- motion-heavy
- auth gate
- 같은 길이의 한글 이름 등 ID collision 위험
- certified/non-certified 가능하면 혼합

실패주입:

- observation id duplicate
- manifest missing
- evidence file swap
- wrong URL
- overwrite
- symlink escape
- AI disagreement
- UNDETERMINED→PASS 시도

모든 guard가 실제로 차단하는지 확인한다.
