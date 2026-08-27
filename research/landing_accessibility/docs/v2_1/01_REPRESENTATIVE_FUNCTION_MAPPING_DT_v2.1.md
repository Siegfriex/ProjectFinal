# Representative Function Mapping Decision Tree v2.1

**문서 ID**: `LA-RFDT-2.1`  
**목적**: 각 web target의 대표기능을 **service name만으로 추정하지 않고**, source prior와 실제 DOM/AX interaction structure를 결합해 일곱 interaction archetype 중 하나로 매핑하거나 명시적으로 abstain하기 위한 규칙형 Decision Tree.

이 DT는 CART, Random Forest 같은 학습 모델이 아니다. **연구 조작화용 rule decision tree**다.

---

## 1. 핵심 원칙

대표기능 매핑은 두 층이다.

### Layer P — Prior

서비스 정체성, source panel context, frozen business-domain codebook으로 가능한 archetype 후보를 만든다.

이 단계는 **확정이 아니다.**

예:

- 종합 포털 → QUERY 후보가 강함
- 오픈마켓 → ITEM_DETAIL 후보가 강함
- 은행 → FINANCIAL_ACTION_ENTRY 후보가 강함

### Layer O — Observed Interaction

실제 모바일웹의 DOM/AX/Form/URL 구조를 보고 candidate를 검증한다.

최종 archetype은 이 층이 결정한다.

business domain과 observed task shape가 충돌하면 observed task shape를 우선한다.

---

## 2. Stage 0 — Web target validity

첫 질문:

> 이 measurement entity에 연구 범위에 맞는 공식 public mobile web landing이 실제로 확인되는가?

### YES

다음 단계로.

### NO / conflicting / WAF-only / unresolved pair

`UNDETERMINED_URL_EVIDENCE`.

URL을 이름이나 도메인 추론만으로 만들어내지 않는다.

---

## 3. Stage 1 — Candidate generation

각 target에 1~3개의 candidate archetype을 만든다.

입력:

- source panel context
- service self-description
- business domain
- existing P-A/P-B codebook

출력:

- candidate archetype set
- prior basis
- prior confidence는 분석변수가 아니라 mapping trace용

접근성 결과, MPFED 결과, WA certification은 입력으로 쓰지 않는다.

---

## 4. Stage 2 — DOM/AX feature extraction

실제 rendered state에서 최소 다음을 추출한다.

### Global

- page title
- URL / path / query
- headings
- landmarks
- AX roles
- accessible names
- visible text
- clickable controls
- form structure
- repeated card/list structures
- structured data if present

### Query-like

- searchbox / combobox / input[type=search]
- enclosing form
- submit control
- result container signals

### Content-like

- article / heading / media controls
- repeated content cards
- video/audio state

### Item-like

- repeated product/item cards
- product name candidates
- price pattern
- cart/buy/order controls as **presence evidence only**
- Product structured data

### Place-like

- place/address/location vocabulary
- map/place search controls
- repeated place cards
- location detail panel

### Communication-like

- thread/post/message list
- compose/editor/textbox entry
- community/message vocabulary

### Finance-like

- account/balance/transfer/payment/auth entry controls
- finance-specific heading/context
- auth/identity gate structure

### Utility-like

- single-purpose tool surface
- primary control that makes the tool usable

---

## 5. Stage 3 — Archetype branch tree

### Branch Q — QUERY

질문:

> 사용자가 자유 텍스트 질의를 제출하는 것이 이 public web에서의 얕은 대표행동인가?

필수 evidence candidate:

- focusable search input / searchbox / combobox
- submit 가능한 form 또는 submit control

Region:

검색 입력 control이 사용 가능한 상태로 노출.

Endpoint:

질의가 실제 제출되어 결과 state로 전환된 순간.

허용 confirmation:

- query parameter URL 전이
- result list/container 등장

자동완성 노출만으로 endpoint 처리하지 않는다.

---

### Branch C — CONTENT_OPEN

질문:

> 이미 존재하는 기사·영상·콘텐츠 한 건을 선택해 소비를 시작하는 것이 대표행동인가?

Region:

content card/link list가 노출.

Endpoint branch:

- article body open
- main media playback start

미리보기, hover, 광고 pre-roll은 endpoint가 아니다.

---

### Branch I — ITEM_DETAIL

질문:

> 거래 대상 한 건의 상세면에 들어가 핵심정보를 보는 것이 대표행동인가?

Region:

individual item/product card or link list.

Endpoint evidence:

- item/product name
- price 또는 명시적 price unavailable 상태
- transaction control의 **존재**

구매/장바구니/주문 control을 클릭하지 않는다.

Quick view라도 같은 상세문서 안에서 endpoint evidence가 모두 성립하면 허용 가능.

---

### Branch P — PLACE_LOOKUP

질문:

> 장소를 질의하거나 특정 장소 상세를 여는 것이 대표행동인가?

Region:

place search control 또는 place list.

Endpoint:

- place query submitted
- place detail opened

pan/zoom 자체는 endpoint가 아니다.

차량 호출·배차 확정은 절대 제외.

---

### Branch M — COMMUNICATION_ENTRY

질문:

> 사람 사이의 게시물·스레드·메시지 교환 공간에 진입하는 것이 대표행동인가?

Region:

thread/post list 또는 compose-entry control.

Endpoint:

- post/thread open
- compose area entry
- actual login gate, when the public path reaches it

메시지 발신·게시 완료는 금지.

로그인 버튼 **존재**만으로 endpoint 처리하지 않는다.

---

### Branch F — FINANCIAL_ACTION_ENTRY

질문:

> 금융처리 기능의 시작면 또는 해당 기능을 시작하기 위해 필요한 실제 로그인/본인인증 gate까지 가는 것이 대표행동인가?

Region:

balance/transfer/payment/auth function entry control.

Endpoint:

- finance function surface open
- finance function URL transition
- actual LOGIN/IDENTITY gate reached on chosen path

송금·이체·결제 수행은 금지.

---

### Branch U — UTILITY_ENTRY

질문:

> 특정 목적의 도구 기능면을 열고 첫 primary control을 사용할 수 있는 상태로 만드는 것이 대표행동인가?

Region:

function surface entry control.

Endpoint:

function surface가 열리고 primary control이 present/actionable.

도구별 완료작업은 하지 않는다.

---

## 6. Stage 4 — Multi-candidate resolver

실제 페이지에는 검색창과 상품목록이 동시에 있을 수 있다.

따라서 첫 매칭을 무조건 선택하지 않는다.

### Evidence precedence

1. actual user-operation structure
2. public page primary interaction surface
3. DOM/AX/form state change evidence
4. source/business prior
5. service name token

### 유일 후보

RULE 확정.

### 두 개 이상 강한 후보

NLP fallback으로 이동.

### evidence 없음

`AMBIGUOUS_UNRESOLVED`.

---

## 7. NLP fallback

목적은 DT가 못 닫은 소수 ambiguity를 해결하는 것이며, 범용 의미추론 제품을 만드는 것이 아니다.

### Text representation

한 target state를 다음 텍스트 묶음으로 표현한다.

- title
- top headings
- landmark labels
- accessible names of top controls
- visible labels around representative region
- form labels
- repeated card descriptors
- URL path tokens

### Prototype texts

일곱 archetype 각각에 SSOT 정의를 짧은 prototype 문장으로 둔다.

### 1차 모델

pretrained sentence embedding으로 page representation과 archetype prototype similarity를 계산한다.

### 2차 모델

top-2가 가깝거나 구조충돌이 있으면 cross-encoder / NLI 스타일 semantic classifier를 쓸 수 있다.

### Threshold

임의 숫자를 영구 기준으로 선언하지 않는다.

Independent label calibration split에서:

- top-1 correctness
- top1-top2 margin
- abstention rate

를 보고 운영 threshold를 정한다.

### Holdout

C가 독립 holdout에서 검증한다.

false certainty가 있으면 coverage를 낮추고 abstain을 늘린다.

### VLM

다음 경우에만:

- icon-only navigation
- image/canvas 중심 interface
- DOM/AX text가 의미를 잃은 경우
- modal/visual hierarchy 때문에 텍스트만으로 대표 surface 구분이 어려운 경우

### Human Final

최대 5건.

---

## 8. Guard-aware mapping

대표기능 DT와 안전가드를 분리한다.

### 로그인

- 로그인 control exists → candidate annotation
- chosen representative path가 로그인 control을 거쳐야 함 → 조건부 navigation 가능
- login form reached → gate observation
- password/credential fill → forbidden
- submit login → forbidden

### CAPTCHA

- hidden/inactive script 존재 → terminal 아님
- visible active challenge가 chosen path를 막음 → CAPTCHA terminal
- solve/bypass → forbidden

### Purchase / Payment

- control presence → endpoint evidence로 사용 가능
- control activation → forbidden if transaction continuation

---

## 9. DT leaf output schema

각 target은 최종적으로 다음 중 하나다.

### MAPPED

- target_id
- archetype
- region_definition
- region_signal_type
- endpoint_definition
- endpoint_signal_type
- mapping_basis
- evidence_refs
- decision_trace
- forbidden_continuation

### AMBIGUOUS_UNRESOLVED

- candidate_archetypes
- unresolved_reason
- evidence_refs
- next fallback stage

### EXCLUDED

research-scope exclusion reason이 evidence로 확인된 경우에만.

---

## 10. Validation

Detector producer는 B다.

Gold label producer는 B도 C도 아니다.

A가 별도 labeler worker를 조직한다.

### 권장 split

56 frozen DOM/evidence를 stratified하게 calibration / holdout으로 나눈다.

가능하면 각 archetype이 양쪽에 존재하게 한다.

### Release safety gate

다음은 연구 threshold가 아니라 engineering release gate다.

- unsafe endpoint false-positive = 0
- every mapped leaf has evidence trace
- unresolved cases are not force-mapped
- holdout archetype agreement target >= 0.85
- holdout coverage target >= 0.75

목표 미달 시 full REAL_TARGET을 막고 pilot subset만 허용한다.

수치 자체는 연구결과가 아니라 detector readiness 기준임을 문서에 명시한다.
