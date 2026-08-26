# ProjectFinal — 고령층 실사용 모바일웹 초기진입 접근성 분석 SSOT v2.0

**상태**: FROZEN FOR IMPLEMENTATION  
**분석 방식**: CRISP-DM + IPOM-C  
**현재 기준선**: `research/landing-accessibility-main @ 5a9015d1e95b15304aaf53a73efb475934610b82`  
**본수집**: 아직 시작하지 않음  
**핵심 범위**: `L0 INITIAL LANDING + L1 SHALLOW REPRESENTATIVE FUNCTION ENTRY`

---

## 1. 한 문장 정의

고령층이 실제 많이 사용하는 서비스의 **모바일웹 첫 화면**과 **대표기능의 첫 진입점**을 같은 조건에서 관측하여,  
① KWCAG 2.2 기반 접근성 장벽, ② 대표기능까지의 구조적 진입 깊이, ③ popup·광고·모달·움직임 등 초기 방해요소를 측정하고, 현재 유효 WA 품질인증 여부를 외부 참조축으로 비교하는 관측형 데이터분석.

---

## 2. 왜 이 분석을 하는가

정책적으로 디지털 접근은 크게 개선됐지만, 실제 생활서비스 활용과 역량의 격차는 여전히 남아 있다.

이 분석은 교육정책의 효과를 직접 평가하지 않는다.

대신 다음 질문을 분리해서 본다.

> 사용자가 충분히 교육받았다고 가정하더라도, 실제 서비스의 **입구 자체**가 보기 어렵거나, 누르기 어렵거나, 방해가 많거나, 대표기능까지 지나치게 깊게 설계돼 있지는 않은가?

즉 사람의 능력보다 **서비스 환경 측 초기 마찰**을 측정한다.

---

## 3. 이번 분석에서 보는 범위

### L0 — 최초 랜딩

모바일 URL에 새 세션으로 접속했을 때 처음 나타나는 상태.

측정:

- 텍스트 명도 대비
- 조작 대상 크기
- accessible name/label
- 최초 viewport에서 대표기능이 보이는지
- popup / modal / 광고 / 앱 설치 유도 / 쿠키 알림
- 대표기능이 popup에 가려지는지
- 닫기 버튼이 보이고 누를 수 있는지
- 자동 움직임 / carousel / autoplay
- 화면의 조작요소 수와 밀도
- KWCAG 2.2 중 이 범위에서 실제 측정 가능한 항목

### L1 — 대표기능의 얕은 진입

서비스의 대표기능이 **시작됐다고 볼 수 있는 첫 상태**까지만 이동한다.

예:

| 유형 | 대표기능 endpoint |
|---|---|
| 검색 | 검색 query가 제출된 순간 |
| 뉴스 | 기사 본문이 열린 순간 |
| 영상 | 영상 재생이 시작된 순간 |
| 쇼핑 | 상품 상세와 핵심 상품정보가 보인 순간 |
| 지도 | 장소검색이 제출되거나 장소 상세가 열린 순간 |
| 금융 | 금융기능 진입 또는 로그인/인증 gate가 나타난 순간 |
| 커뮤니티 | 게시물/스레드/작성영역 진입 또는 로그인 gate |

### 절대 제외

- 로그인 이후
- 본인인증 이후
- 결제 완료
- 송금 완료
- 예약 완료
- 회원가입
- 오류복구 전체 과정
- full task usability
- 사용자별 실제 성공률
- 사이트 전체 KWCAG 인증 재평가

---

## 4. 세 개의 분석축

### Axis A. 표준 접근성

KWCAG 2.2 기준을 그대로 사용한다.

고령자용 임의 threshold는 만들지 않는다.

criterion은 고령자의 주요 사용특성과 연결해 다음과 같이 태깅한다.

- `VISION`: 시력·대비·가독성
- `MOTOR`: 미세조작·버튼/조작대상
- `COGNITIVE_NAVIGATION`: 이해·탐색·방해·예측가능성
- `OTHER`

결과는 원칙적으로:

- PASS
- FAIL
- UNDETERMINED
- NA

를 유지한다.

### Axis B. 초기진입 마찰

KWCAG 위반과는 별개의 변수다.

- `NED`: 대표기능 영역까지 가는 activation 수
- `IED`: 그 영역에서 endpoint까지 가는 activation 수
- `MPFED = NED + IED`
- popup/modal
- overlay coverage
- primary action occlusion
- forced dismissal
- scroll episode
- text input episode
- auth gate
- motion / carousel
- interactive density

`Depth >= 3 = 나쁨` 같은 기준은 만들지 않는다.

동일 interaction archetype의 분포와 비교한다.

### Axis C. 외부 공인 참조축

`certified_current ∈ {0,1}`

WA 품질인증은 **고령 사용자의 실제 성공 여부를 나타내는 gold label이 아니다.**

다만 공인된 접근성 참조라벨로 사용한다.

---

## 5. 분석 단위

### Source Row

Wiseapp 원자료의 한 행.

### Measurement Entity

Wiseapp 측정 의미를 보존한 서비스 단위.

### Web Target

실제로 모바일웹을 관측할 공식 URL 단위.

### Landing Observation

`web_target × audit_date × protocol`

### Representative Task

`web_target × representative_task`

한 web target에 같은 대표task를 여러 번 중복 측정하지 않는다.

### Criterion Observation

`landing_observation × KWCAG criterion`

---

## 6. 대표기능 분류

비즈니스 도메인과 실제 interaction 구조를 분리한다.

### Business Domain

해석·보고용.

예:

- PORTAL_SEARCH
- CONTENT_VIDEO
- NEWS_CONTENT
- SHOPPING_COMMERCE
- MAP_MOBILITY
- FINANCE_PAYMENT
- SOCIAL_COMMUNICATION
- UTILITY_OTHER

### Interaction Archetype

Depth 비교용.

- QUERY
- CONTENT_OPEN
- ITEM_DETAIL
- PLACE_LOOKUP
- COMMUNICATION_ENTRY
- FINANCIAL_ACTION_ENTRY
- UTILITY_ENTRY

한 measurement entity당 원칙적으로 대표 task 1개.

매핑은 접근성 outcome과 인증 여부를 보기 전에 동결한다.

---

## 7. Depth

### NED — Navigation Entry Depth

랜딩에서 대표기능이 있는 영역에 도달하기까지의 최소 state-changing activation 수.

### IED — Interaction Entry Depth

대표기능 영역에서 predefined endpoint까지 필요한 최소 activation 수.

### MPFED

`MPFED = NED + IED`

### 별도 기록

- text input
- scroll
- forced popup dismissal
- auth gate
- redirect

이들은 Depth와 합치지 않는다.

### 상대 깊이

`ExcessDepth = MPFED - 같은 archetype의 중앙값`

절대 cutoff 대신 동종 기능 안에서 상대적으로 얼마나 깊은지 본다.

---

## 8. Popup / Modal / 방해요소

이번 v2의 핵심 신규 측정축.

분류:

- BLOCKING_MODAL
- PROMOTION_MODAL
- COOKIE_CONSENT
- ADVERTISEMENT
- APP_INSTALL_PROMPT
- LOGIN_PROMPT
- CHAT_WIDGET
- BANNER
- TOAST
- UNKNOWN

주요 지표:

`OverlayCoverage = overlay가 최초 화면에서 차지하는 면적 / 최초 화면 면적`

`PrimaryActionOcclusion = 대표기능 control이 overlay에 가려진 면적 / 대표기능 control 면적`

또한 다음을 기록한다.

- 닫기 control 유무
- 닫기 control 가시성
- accessible name
- 조작 대상 크기
- 실제 dismissal 성공
- 대표기능 진입을 위해 반드시 닫아야 하는지

---

## 9. 사람 검토 정책

실제 인간은 **최대 5건**만 본다.

`HUMAN_FINAL_REVIEW_MAX = 5`

검토 cascade:

1. deterministic rule
2. text/embedding/semantic classifier
3. multimodal AI reviewer A
4. 독립 multimodal AI reviewer B
5. AI arbiter
6. 그래도 중요한 모호성만 HUMAN_FINAL

5건을 초과하는 모호한 사례를 억지로 분류하지 않는다.

나머지는 `UNDETERMINED / ABSTAIN`.

AI label을 human gold라고 부르지 않는다.

---

## 10. 모델 사용 원칙

모델을 쓰기 위해 모델을 쓰지 않는다.

현재 수십 개 서비스 규모에서 새 CNN/DNN을 supervised 학습하는 것은 기본 계획이 아니다.

우선순위:

1. Browser native measurement
2. deterministic algorithm
3. classical CV / geometry / pixel analysis
4. embedding / text classifier
5. pretrained VLM / MLLM
6. human final ≤5

Vision 모델은 popup 의미, icon-only 기능, canvas/image text, 복잡한 시각 문맥처럼 browser 정보가 부족할 때 사용한다.

---

## 11. 주요 분석

### 기술통계

- web eligibility
- domain/archetype 분포
- KWCAG PASS/FAIL/UNDET/NA
- popup/modal prevalence
- NED/IED/MPFED
- ExcessDepth
- endpoint reach
- auth gate
- certification reach

### Depth

작은 정수형 변수이므로 평균보다:

- median
- IQR
- mode
- ECDF
- 0/1/2/3/4+ 빈도

를 우선한다.

### 그룹 비교

필요하면:

- Kruskal–Wallis
- pairwise permutation 또는 Dunn
- FDR correction

### 인증 비교

표본이 성립할 때만:

- Mann–Whitney U / permutation
- Fisher exact
- risk difference
- median difference

인과해석 금지.

### 연관성

- MPFED ↔ 접근성 장벽: Spearman
- ExcessDepth ↔ popup/overlay: Spearman
- 인증 ↔ binary barrier: Fisher

### robustness

- leave-one-service-out
- leave-one-archetype-out
- UNDETERMINED stress bound
- service-equal weighting

---

## 12. 핵심 시각화

1. `261 Source Rows → 81 Entities → Web Target → Eligible → Measured`
2. interaction archetype별 MPFED 분포
3. 서비스 × KWCAG heatmap
4. popup/modal 종류와 blocking 비율
5. 최초 viewport obstruction evidence
6. `ExcessDepth × Older-Relevant KWCAG Fail`
7. 점 크기 = Overlay Coverage
8. 점 모양 = WA 인증 여부

---

## 13. 선행연구 차용

### W3C Older Users

고령 사용자에게 text size, contrast, navigation, mouse/keyboard, distraction, page organization, consistent labeling, popup/new window 등이 중요하다는 연결을 이용한다.

### Gwizdka & Spence (2007)

웹 navigation path의 길이·구조와 optimal path similarity를 이용해 navigation difficulty를 정량화한 접근을 차용한다.

단, 본 연구에는 실제 human path가 없으므로 `lostness`는 측정하지 않는다.

### Augello et al. (2026)

고령자용 mHealth usability에서 **올바른 section까지의 click 수**와 **section 내부 task click 수**를 분리한 접근을 차용한다.

본 연구의 NED와 IED 설계 근거.

### Grahame, Laberge & Scialfa (2004)

link size, link number, clutter가 고령자의 웹 탐색 성능에 영향을 주는 결과를 바탕으로 visual/interactivity density를 보조 feature로 수집한다.

### W3C ACT Rules

`Applicability → Expectation → Outcome` 구조를 KWCAG 측정규칙 운영에 차용한다.

---

## 14. 최종 Claim Boundary

허용:

> 고령층 실사용 서비스 frame의 모바일웹 초기진입에서 특정 접근성 장벽이 반복적으로 관측됐다.

> ITEM_DETAIL 유형의 대표기능 진입 깊이는 중앙값 X였고 일부 서비스가 같은 유형보다 Y단계 더 깊었다.

> 최초 viewport에서 blocking modal이 관측된 비율은 X/Y였다.

금지:

> popup 때문에 고령자가 서비스를 포기한다.

> depth가 3 이상이면 고령자에게 부적합하다.

> 인증 때문에 접근성이 좋아졌다.

> 이 서비스는 노인이 사용할 수 없다.

---

## 15. 실행 종료점

본수집 전 반드시 다음을 충족한다.

- final web target frozen
- representative task frozen
- interaction archetype frozen
- KWCAG subset frozen
- L0 collector validated
- L1 scout/replay validated
- popup/obstruction detector validated
- AI review cascade validated
- evidence manifest validated
- HUMAN_FINAL queue policy validated
- E000_V2 smoke PASS
- independent adversarial audit PASS
- independent SSOT audit PASS
- open blocking P0/P1/P2 = 0

이 지점에서:

`READY_FOR_E001_V2`

를 선언하고 사용자의 GO/HOLD를 기다린다.
