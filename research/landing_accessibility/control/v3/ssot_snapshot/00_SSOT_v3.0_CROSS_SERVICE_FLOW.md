# ProjectFinal — 고령층 모바일웹 교차서비스 Task Entry Flow SSOT v3.0

**문서 상태**: `AUTHORITY_CANDIDATE`  
**이 문서가 새로 허가하는 REAL scope**: 없음  
**상위 목적**: 고령층의 디지털 접근·역량 향상에도 불구하고 생활서비스 **활용 단계에서 반복적으로 새 인터페이스를 학습해야 하는 구조적 환경**을 관측 가능한 단위로 측정.

---

## 0. North Star

> **동일한 생활과업을 제공하는 서로 다른 모바일웹에서, 사용자가 과업 진입을 위해 기억해야 하는 위치·명칭·조형·reveal 방식·조작순서·깊이·인증시점은 얼마나 달라지는가?**

본 연구는 이 차이를 `Cross-Service Task Entry Flow Divergence`로 관측하고, 실제 인지부하 자체가 아니라 **구조적 재학습 요구의 proxy**인 `Structural Transfer Friction Proxy (STFP)`로 해석한다.

### 말할 수 있는 것

- 동일 과업의 진입 위치·label·control type·menu/reveal·sequence·depth·auth timing이 서비스마다 얼마나 다른지.
- A 서비스에서 습득한 위치/명칭/순서가 B 서비스 구조와 얼마나 일치하지 않는지.
- cross-service predictability를 낮출 수 있는 구조적 변이가 존재하는지.

### 말하면 안 되는 것

- 이 차이가 고령자의 인지부하를 X만큼 증가시켰다는 인과 주장.
- 실제 학습전이율/실패율 감소를 사람 실험 없이 확정.
- 서로 다른 공급자의 UI가 다르다는 이유만으로 WCAG/KWCAG 위반이라고 판정.

---

## 1. v2.1 → v3.0 핵심 결정

1. **Representative Function 자동추론을 critical path에서 제거.** 페이지에서 task를 추론하지 않음.
2. **Task-first**: 과업은 수집 전에 `Task Family + Task Contract + Endpoint Contract`로 동결.
3. **Flow-first**: 원자료는 ordered `Action Sequence`; NED/IED/MPFED 계열 Depth는 파생 요약치.
4. **Matched comparison**: 무작정 59 서비스를 한 분모로 비교하지 않고 동일 과업 family 내부에서 비교.
5. **7 archetype 유지**: sampling quota가 아니라 legacy metadata / measurement codebook으로만 유지.
6. **12 diagnostic 유지**: `METHOD_QUALIFICATION_SET`; 끝까지 수행하되 결과가 본연구 효과크기 추정치는 아님.
7. **59 유지**: `USAGE_BENCHMARK_FRAME / ROBUSTNESS_CORPUS`; 새 본연구 분모 아님.
8. **50 main candidate**: 5 matched task families × 10 services. mobile-web precheck 후 A가 exact manifest hash로 freeze.
9. **APP_REQUIRED/APP_ONLY 제외**: primary mobile-web frame에서 사전 replacement. 결과를 본 뒤 교체 금지.
10. **Composite 금지**: 단일 ‘고령자 재학습 점수’ 생성 금지. STFP는 다축 profile.

---

## 2. 이론적 연결 — WCAG/KWCAG와의 경계

WCAG 2.2의 `3.2.3 Consistent Navigation`과 `3.2.4 Consistent Identification`은 예측가능성과 일관된 식별을 요구한다. W3C Older Users guidance는 consistent navigation/presentation/labeling이 고령 사용자에게 특히 중요하다고 설명한다.

참고:
- https://www.w3.org/WAI/WCAG22/Understanding/consistent-navigation.html
- https://www.w3.org/WAI/WCAG22/Understanding/consistent-identification.html
- https://www.w3.org/WAI/older-users/developing/

그러나 WCAG의 규범 범위는 기본적으로 동일 `set of web pages` 내부다. v3은 이를 **cross-provider matched-task observational comparison**으로 확장한다. 따라서 이 연구축은 WCAG 적합성 판정이 아니라 별도의 구조적 predictability/transfer-friction 연구축이다.

---

## 3. 측정 아키텍처

### Axis A — Standard Accessibility
KWCAG 기반 독립축. criterion별 PASS/FAIL/UNDETERMINED/NA. composite 금지.

### Axis B — Task Entry Flow / Cross-Service Flow Divergence — **v3 primary**
사전 동결 task가 어디에, 어떤 이름/형태로, 어떤 navigation sequence를 통해 endpoint에 도달하는지 측정.

### Axis C — Task-Path Obstruction
초기 popup/modal/banner/fixed layer가 **실제로 task control을 가리거나 path 진행에 dismissal을 요구하는지** 측정. 단순 max coverage와 구분.

### External Reference — WA Certification
외부 참조축. gold label 아님. v3 CSEC/STFP와 동일 개념이 아님.

---

## 4. Main matched-task frame

| ID | 생활과업 | domain | legacy archetype | n | endpoint 요지 |
|---|---|---|---|---|---|
| F1 | 개인뱅킹 계좌이체/송금 기능 진입 | 금융 | FINANCIAL_ACTION_ENTRY | 10 | 사용자가 이체/송금 경로를 선택한 뒤 task-specific transfer surface가 열리거나 LOGIN/IDENTITY gate가 불가피하게 나타나는 최초 상태. 자격정보 입력·login submit·수취계좌/금액 입력·이체 실행 금지. |
| F2 | 상품 검색/탐색 후 상품 상세 진입 | 상거래 | ITEM_DETAIL | 10 | 개별 상품 상세면에서 상품명과 가격 또는 가격정보가 확인되는 최초 상태. 장바구니/구매/결제 control은 존재만 관측하고 활성화 금지. |
| F3 | 택배 배송조회/운송장조회 기능 진입 | 배송/조회 | UTILITY_ENTRY | 10 | 운송장/등기번호 입력 control과 조회 실행 control이 관측 가능한 최초 상태. 실사용 번호·개인정보 입력 및 조회 submit 금지. |
| F4 | 병원·약국/의료기관 찾기 | 건강/위치 | PLACE_LOOKUP | 10 | 검색 폼에서 고정 조건을 적용한 뒤 기관 결과목록 또는 지도 결과가 표시되는 최초 상태. 예약·전화·외부앱 실행 금지. |
| F5 | 서울권→부산권, T+1 운행편/항공편 조회 | 교통/예매 | UTILITY_ENTRY | 10 | 조건 입력 후 시간·편명/운행편·가격 또는 예약가능성 정보를 포함한 결과목록이 표시되는 최초 상태. 좌석선택·예약·결제 금지. |

### 표본 해석

- 본표본 독립단위: `service × frozen task`.
- family당 10 service → pairwise matrix 45개지만, **독립 n은 10**이지 45가 아님.
- F1의 잔액/계좌조회 secondary task는 같은 10개 은행 repeated task이며 본표본 n 증가로 세지 않음.
- target 50은 현재 **candidate frame**. mobile-web precheck 후 target manifest freeze 전에는 main REAL 수집 금지.

---

## 5. Task Contract 규칙

각 target은 수집 전에 다음을 가진다.

- `family_id`
- `service_id`
- `matched_task`
- `task_instruction`
- `fixed_fixture`
- `endpoint_contract`
- `auth_rule`
- `forbidden_actions`
- `mobile_web_eligibility`
- `manifest_sha256`

**화면 title/text/domain을 보고 task 자체를 바꾸지 않는다.** 화면은 오직 이미 지정된 task의 control/path를 찾기 위한 evidence다.

---

## 6. Auth / Credential / Transaction 계약

- landing에 generic login이 **존재**한다는 이유로 중단하지 않는다.
- 사전지정 task path를 따라가다가 인증이 불가피해지는 최초 상태에서 `AUTH_GATE` terminal 허용.
- `BEFORE_TASK_DISCOVERY / AFTER_TASK_SELECT / AT_ENDPOINT`를 구분.
- credential 입력, login submit, 본인인증 수행, CAPTCHA 해결/우회 금지.
- 구매·송금·예약·결제·장바구니 등 거래 state-changing activation 금지. 존재와 geometry만 관측 가능.

---

## 7. Flow가 본체, Depth는 파생

### Raw primary
`task_flow_sequence`와 `experienced_flow_sequence`.

- `task_flow_sequence`: 서비스 자체 navigation/task 구조. forced dismissal 제외.
- `experienced_flow_sequence`: 실사용자가 실제 겪은 path. forced dismissal 포함.

### Derived
- `menu_dependency`
- `nav_container_depth`
- `activation_depth`
- `NED/IED/MPFED` compatibility fields
- `flow_step_count`
- `auth_gate_stage`

Scroll은 `first_visible_scroll_state`로 별도 측정하며 activation depth에 합산하지 않는다.

---

## 8. Visible Label / Accessible Name 분리

`visible_label_text` = 사용자가 화면에서 실제 보는 rendered text.  
`accessible_name` = browser AX tree가 계산한 보조기술용 이름.

반드시 둘을 분리하고 `accessible_name_source`, `label_relation`, `entry_label_modality`를 저장한다. `ICON_ONLY_AX_NAMED`와 `ICON_ONLY_UNNAMED`를 구분한다.

---

## 9. 수집 경로

`Frozen Task Registry → Mobile Web Eligibility → L0/Scroll Surface Capture → Task-specific Candidate Binding → Scout → Path Freeze → Deterministic Replay → Flow Mart → Family Comparison`

### 금지

- RF classifier가 task family를 재결정.
- NLP/embedding이 task label을 바꿈.
- replay 실패 시 자유탐색으로 조용히 fallback.
- 결과를 본 뒤 target 교체/endpoint 변경.

---

## 10. 12 / 59 / 50의 역할

| Frame | 역할 | 본연구 추론분모? |
|---|---|---|
| Diagnostic 12 | METHOD_QUALIFICATION_SET — collector/guard/evidence 검증 | 아니오 |
| Existing 59 | USAGE_BENCHMARK / ROBUSTNESS_CORPUS — broad site 강건성·legacy 비교 | 아니오 |
| New matched 50 | SUBSTANTIVE MAIN FRAME 후보 — 5 families×10 | precheck/freeze 후 예 |

12 PASS가 자동으로 full59 REAL 수집을 허가하지 않는다.

---

## 11. v3 Claim Boundary

**Primary claims**: cross-service structural variation, task flow dispersion, label/control/spatial/menu/auth/obstruction variation.

**Secondary interpretation**: structural relearning demand / transfer-friction proxy.

**금지**: user cognitive load causal effect, actual transfer success, old-age-specific behavioral effect without person-level study, composite ‘senior accessibility score’.

---

## 12. Supersession

v3이 우선하는 v2.1 영역:
- 대표기능 자동매핑/RF-DT/NLP fallback의 **본수집 필수성**
- 59를 본연구 단일 분석 frame으로 보는 해석
- Depth를 primary construct로 보는 해석

v2.1에서 그대로 승계:
- 안전 guard/firewall
- append-only evidence/provenance
- KWCAG 독립축
- obstruction 독립축
- Scout→Freeze→Replay 원칙
- C 독립 assurance
- D non-canonical research sandbox

---

## 13. 현재 실행권한

이 문서 자체는 새 REAL 실행권한을 주지 않는다. 현재 허가된 REAL은 기존 A release가 허용한 `V2_DIAGNOSTIC` 12 targets뿐이다. v3 main 50은 별도 A manifest freeze/release가 필요하다.
