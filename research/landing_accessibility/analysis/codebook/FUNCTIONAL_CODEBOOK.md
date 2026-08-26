# Functional Codebook — Business Domain × Interaction Archetype (P-A A4)

- **산출 phase**: P-A (Analysis Foundation + Task Codebook)
- **닫는 gate 항목**: `PHASE_GATES.md` §3 `ANALYSIS_AND_TASK_CODEBOOK_FROZEN` 의
  `Functional Codebook` 행 — *Business Domain과 Interaction Archetype 분리 정의, archetype 7종 endpoint 명시*
- **상위 권위**: `00_SSOT_v2.0.md` §3 · §6 · §7 · §14 → `01` §3 → `02` §6 · §7 · §9 · §10 → `A1` §1 → `A2` §1.5 · §1.9
- **채택 상태**: `PROPOSED_PENDING_PA_AUDIT`
- **base SHA**: `6fad79fa98e1ec7d315122d79794b4d5442bb42e`

---

## 0. 이 문서의 지위

### 0.1 SSOT 우선 조항

이 문서는 `00_SSOT_v2.0.md`가 **이미 정의한 분류축의 판정 규칙**만 기술한다.
`00`과 충돌하면 `00`이 우선하며, 충돌은 이 문서의 결함이다. `00`~`05` pack의 바이트를 수정하지 않는다.
어휘(열거값)는 `A2`가 우선한다(`A1` §0.2와 동일 규약).

### 0.2 이 문서가 하는 것 / 하지 않는 것

| | 내용 |
|---|---|
| 한다 | Business Domain 8종·Interaction Archetype 7종의 판정규칙, archetype별 region/endpoint 정의와 관측신호, 경계사례, 매핑 절차·동결 규율, 기계판독 코드북 |
| 하지 않는다 | **서비스별 실제 매핑** (P-A A5 pilot / P-B M0 소관), endpoint 신호 탐지 알고리즘 구현(P-C), 임계값·점수 신설 |

### 0.3 새로 만든 것은 정확히 하나다

`00` §3 L1 표에는 **7행**(검색·뉴스·영상·쇼핑·지도·금융·커뮤니티)이 있고 `00` §6 archetype도 **7종**이지만
**일대일이 아니다**(§2.1 대응표). `UTILITY_ENTRY`만 `00` §3에 대응 행이 없고,
`A1` §1.2가 그 endpoint 정의를 명시적으로 P-A로 이관했다.

> `A1` §1.2: *"`UTILITY_ENTRY`는 `00` §3의 7행에 대응 행이 없다. 이 문서는 그 endpoint를 임의로 만들지 않는다.
> `03` P-A의 endpoint codebook이 동결한다. 그때까지 `UTILITY_ENTRY` task는 `mapping_status`를 미동결로 유지한다."*

따라서 이 문서에서:

- archetype 6종(`QUERY`·`CONTENT_OPEN`·`ITEM_DETAIL`·`PLACE_LOOKUP`·`COMMUNICATION_ENTRY`·`FINANCIAL_ACTION_ENTRY`)의
  endpoint는 **`00` §3의 전사(transcription)** 다. 정의를 바꾸지 않았다. `endpoint_definition_source = SSOT_00_S3`.
- `UTILITY_ENTRY` endpoint만 **신규 제안**이다. `endpoint_definition_source = PROPOSED_BY_PA_A4`.
  §2.9에 근거·대안·판정 요청을 분리해 적었다. **감사가 채택을 판정하기 전에는 `region_signal_type = CODEBOOK_PENDING`을 유지하며
  `A2` 규칙 P-2에 따라 `mapping_status = FROZEN`으로 전이할 수 없다.**

### 0.4 금지 재확인 (`00` §4 · §14 · `A1` §0.3)

- `depth >= N = 나쁨` 류 임의 threshold 생성 금지. 이 문서에는 그런 값이 없다.
- 세 축(A 접근성 / B 초기진입 마찰 / C 인증)의 단일 종합점수 합산 금지.
- WA 인증을 gold label로 사용 금지. 인증은 매핑 입력에서 **차단**된다(§3.3).
- Depth·popup·episode 값을 KWCAG `FAIL`로 전환 금지.
- **endpoint를 완료(completion)로 정의 금지.** L1은 "얕은 진입"이다(§2.2 규칙 E-SHAPE).

### 0.5 예시 서술에 관한 고지

경계사례·전형성 서술에 등장하는 서비스 유형 표현은 **규칙을 설명하기 위한 예시**이며
특정 measurement entity에 대한 매핑 판정이 **아니다**. 실제 매핑은 A5/P-B가 별도 절차로 수행한다.

---

## 1. Business Domain 코드북

### 1.0 이 축의 용도 — 해석·보고 전용

`00` §6은 Business Domain을 **"해석·보고용"**, Interaction Archetype을 **"Depth 비교용"** 으로 분리 선언했다.
이 분리를 코드북 수준에서 강제한다.

| 규칙 | 내용 | 근거 |
|---|---|---|
| **BD-USE-1** | `business_domain`은 서술통계·표·시각화의 **레이블**로만 쓴다 (`00` §11 기술통계 `domain/archetype 분포`) | `00` §6 |
| **BD-USE-2** | `business_domain`을 `ExcessDepth`의 기준선 그룹으로 쓰지 않는다. 기준선은 **오직 `interaction_archetype`의 중앙값**이다 | `00` §7 `ExcessDepth = MPFED - 같은 archetype의 중앙값` |
| **BD-USE-3** | `mart_archetype_summary`(`01` §10)는 archetype 단위다. domain 단위 depth 요약표를 만들어 그것으로 깊이를 비교하지 않는다 | `01` §10 |
| **BD-USE-4** | `00` §11 `그룹 비교`(Kruskal–Wallis 등)의 그룹은 archetype 또는 `certified_current`다. domain을 depth 검정의 그룹으로 세우려면 별도 승인이 필요하다 (미결 Q-6) | `00` §11 |
| **BD-USE-5** | domain은 `00` §14 허용 claim 문장에서 **맥락 서술**로만 등장한다. 허용 예시문(`ITEM_DETAIL 유형의 …`)이 archetype으로 쓰인 것에 유의 | `00` §14 |

### 1.1 공통 판정 규칙

| 규칙 | 내용 |
|---|---|
| **BD-1 (단일값)** | `dim_representative_task.business_domain`은 행당 정확히 1개. 다중 라벨·가중 라벨을 만들지 않는다 |
| **BD-2 (1차 정체성)** | 서비스가 복수 도메인 기능을 제공하면 **measurement entity의 1차 정체성**으로 판정한다. 1차 정체성은 (a) 원자료 패널 맥락(`fact_source_ranking`의 카테고리·랭킹 문맥), (b) 공식 서비스의 자기기술(서비스명·공식 소개문), (c) 등록 도메인 문자열 순으로 본다 |
| **BD-3 (archetype 비종속)** | domain 판정에 archetype 판정 결과를 입력으로 쓰지 않는다. 두 축은 **독립적으로** 판정하며, 판정 후 교차표를 만든다. 역도 같다 |
| **BD-4 (잔여이지 쓰레기통 아님)** | `UTILITY_OTHER`는 나머지 7종 중 어느 것으로도 판정할 **근거가 없을 때** 쓴다. 근거가 있는데 애매해서 쓰는 값이 아니다 |
| **BD-5 (상충 시 abstain)** | 두 도메인의 근거가 대등하게 상충하면 `UTILITY_OTHER`로 밀지 않고 §3.5 abstain 경로로 보낸다 (`mapping_status = AMBIGUOUS_UNRESOLVED`) |
| **BD-6 (관측 차단)** | domain 판정에 L0/L1 **관측 산출물**(KWCAG feature, popup 측정, depth)·`certified_current`를 입력으로 쓰지 않는다 (§3.3 입력 allowlist) |

### 1.2 8종 정의

각 항목: **정의 / 포함 / 제외 / 경계**

---

#### `PORTAL_SEARCH`
- **정의**: 특정 콘텐츠 소유 없이 **범용 정보 탐색의 관문** 역할을 1차 정체성으로 갖는 서비스. 종합 포털·범용 검색엔진·범용 웹브라우저 진입면.
- **포함**: 범용 검색엔진, 종합 포털, 브라우저의 기본 시작면(범용 검색을 전면에 두는 경우).
- **제외**: 자사 상품·콘텐츠 **안에서만** 검색되는 서비스(그 서비스의 본래 도메인으로). 특정 주제에 한정된 수직검색(그 주제의 도메인으로).
- **경계**:
  - 포털이 뉴스·쇼핑·지도·금융을 모두 품는다 → BD-2에 따라 **관문 정체성**이 1차이면 `PORTAL_SEARCH`. 그 서비스의 대표 task가 뉴스 열기로 동결되더라도 domain은 `PORTAL_SEARCH`일 수 있다(§4.1 비대각 예시 D1).
  - 브라우저 앱: 주소창이 범용 검색을 겸하면 `PORTAL_SEARCH`. 단 모바일웹 대상이 성립하지 않으면 domain 판정 이전에 `web_eligibility_status`에서 걸러진다(P-B 소관).

#### `CONTENT_VIDEO`
- **정의**: **영상·오디오 스트리밍 콘텐츠 소비**를 1차 정체성으로 갖는 서비스.
- **포함**: 동영상 플랫폼, OTT, 숏폼 영상, 라이브 스트리밍.
- **제외**: 영상이 부수적으로만 쓰이는 서비스(뉴스사의 영상 코너 → `NEWS_CONTENT`, 커머스의 상품영상 → `SHOPPING_COMMERCE`).
- **경계**:
  - **라이브 커머스**: 영상이 매개이고 거래가 목적이면 `SHOPPING_COMMERCE`. 시청 자체가 상품이면 `CONTENT_VIDEO`.
  - **음악 스트리밍**: 영상이 아니지만 미디어 재생 소비라는 점에서 이 값에 포함한다(`MEDIA_STATE` 신호를 공유).
  - 영상 **저장/관리** 도구(개인 미디어 보관함)는 소비 플랫폼이 아니므로 `UTILITY_OTHER`.

#### `NEWS_CONTENT`
- **정의**: **편집된 텍스트 기사·기고 콘텐츠의 발행과 소비**를 1차 정체성으로 갖는 서비스.
- **포함**: 신문·방송사 뉴스, 뉴스 애그리게이터, 매거진형 텍스트 콘텐츠.
- **제외**: 사용자 생성 게시물이 본체인 서비스(→ `SOCIAL_COMMUNICATION`). 상품 리뷰(→ `SHOPPING_COMMERCE`).
- **경계**:
  - **뉴스 애그리게이터 vs 포털**: 검색 관문이 전면이면 `PORTAL_SEARCH`, 기사 목록이 전면이고 검색이 부수적이면 `NEWS_CONTENT`.
  - **블로그 플랫폼**: 편집주체가 개인/사용자면 `SOCIAL_COMMUNICATION`, 편집국이 있으면 `NEWS_CONTENT`.

#### `SHOPPING_COMMERCE`
- **정의**: **상품·서비스의 탐색과 거래**를 1차 정체성으로 갖는 서비스.
- **포함**: 오픈마켓, 종합몰, 홈쇼핑, 소셜커머스, 배달 주문, 브랜드 자사몰, 식료품 배송.
- **제외**: 금융상품 자체를 파는 서비스(→ `FINANCE_PAYMENT`). 결제수단만 제공하는 서비스(→ `FINANCE_PAYMENT`).
- **경계**:
  - **결제기능 포함 커머스**: 결제는 거래의 부속이므로 domain은 `SHOPPING_COMMERCE`. (단 대표 task가 결제 진입으로 동결되면 archetype은 `FINANCIAL_ACTION_ENTRY`일 수 있다 — 비대각 예시 D3.)
  - **여행·항공·숙박 예약**: 판매 대상이 재화가 아니라 좌석/객실이지만 탐색→상세→거래 구조가 동일하므로 `SHOPPING_COMMERCE`. 단 **예약 완료는 `00` §3 절대 제외**다.
  - **오프라인 점포 브랜드 앱**(멤버십·적립 중심): 상품 목록·주문이 1차면 `SHOPPING_COMMERCE`, 적립/쿠폰 도구가 1차면 `UTILITY_OTHER`.

#### `MAP_MOBILITY`
- **정의**: **지리적 위치 탐색·경로 안내·이동수단 이용**을 1차 정체성으로 갖는 서비스.
- **포함**: 지도, 내비게이션, 대중교통 안내, 택시·차량 호출, 자전거·킥보드 대여.
- **제외**: 위치 기반 상점 목록이지만 목적이 거래인 서비스(→ `SHOPPING_COMMERCE`).
- **경계**:
  - **호출형 모빌리티**: 목적지 검색·경로 확인까지가 domain 특성이며, **호출/배차 확정은 예약 완료에 준해 `00` §3 절대 제외**다.
  - **지도 위 장소 상세가 곧 상점 상세**인 경우: 서비스의 1차 정체성이 지도이면 `MAP_MOBILITY`.

#### `FINANCE_PAYMENT`
- **정의**: **자금·금융상품·결제수단의 조회와 처리**를 1차 정체성으로 갖는 서비스.
- **포함**: 은행, 카드사, 증권, 보험, 간편결제·송금, 통합자산조회.
- **제외**: 커머스의 부속 결제(→ `SHOPPING_COMMERCE`). 가계부·계산기 같은 비거래 도구(→ `UTILITY_OTHER`).
- **경계**:
  - **포인트·리워드 적립 서비스**: 현금성 자산의 조회·이체가 1차면 `FINANCE_PAYMENT`, 광고 시청·걸음수 등 행동 보상 도구가 1차면 `UTILITY_OTHER`.
  - **은행 앱의 비금융 부가기능**(생활 서비스)이 랜딩 전면에 있어도 1차 정체성은 금융이다.

#### `SOCIAL_COMMUNICATION`
- **정의**: **사람 사이의 메시지·게시물 교환**을 1차 정체성으로 갖는 서비스.
- **포함**: 메신저, SNS, 커뮤니티·게시판, 지역기반 이웃 커뮤니티, 사용자 블로그 플랫폼.
- **제외**: 편집국이 발행하는 기사(→ `NEWS_CONTENT`). 판매자–구매자 문의만 있는 커머스(→ `SHOPPING_COMMERCE`).
- **경계**:
  - **중고거래 커뮤니티**: 거래 게시물의 상세가 상품 상세와 구조적으로 같다. 서비스가 스스로를 커뮤니티로 규정하면 `SOCIAL_COMMUNICATION`, 마켓플레이스로 규정하면 `SHOPPING_COMMERCE`. 근거가 대등하면 BD-5(abstain).
  - **영상 플랫폼의 댓글·커뮤니티 탭**은 부속이므로 domain을 바꾸지 않는다.

#### `UTILITY_OTHER`
- **정의**: 위 7종 어디에도 1차 정체성이 귀속되지 않는 **도구·기능 제공형** 서비스. `00` §6 목록의 잔여값.
- **포함**: 기기 관리·보안·백신, 파일/사진 관리, 메모·계산기류 생산성 도구, 걸음수·리워드 적립 도구, 공공·행정 민원 도구, 인증서 지갑, 날씨·시계 등 단일목적 조회 도구.
- **제외**: BD-4 — 7종 중 하나로 볼 근거가 있는 서비스.
- **경계**:
  - **공공 민원 서비스**: 문서 발급·신청은 완료가 절대 제외이므로 domain은 `UTILITY_OTHER`, 대표 task는 조회/신청 진입면까지.
  - **인증서·지갑**: 결제수단 관리가 1차면 `FINANCE_PAYMENT`, 신원증명 도구가 1차면 `UTILITY_OTHER`.
  - `UTILITY_OTHER` domain이 곧 `UTILITY_ENTRY` archetype을 뜻하지 **않는다**(§4.1 비대각 예시 D4·D5).

---

## 2. Interaction Archetype 코드북

### 2.1 `00` §3 L1 표 ↔ `00` §6 archetype 대응표

`00` §3 L1 표는 **7행**, `00` §6 archetype은 **7종**이지만 대응은 **6:6 + 1 결측 + 2:1 병합**이다.

| `00` §3 L1 표의 행 | archetype (`00` §6) | 대응 성격 |
|---|---|---|
| 검색 | `QUERY` | 1:1 |
| 뉴스 | `CONTENT_OPEN` | **2:1 병합** — 뉴스·영상 두 행이 하나의 archetype으로 합쳐진다 |
| 영상 | `CONTENT_OPEN` | 〃 |
| 쇼핑 | `ITEM_DETAIL` | 1:1 (이름 불일치) |
| 지도 | `PLACE_LOOKUP` | 1:1 (이름 불일치) |
| 금융 | `FINANCIAL_ACTION_ENTRY` | 1:1 (이름 불일치) |
| 커뮤니티 | `COMMUNICATION_ENTRY` | 1:1 (**이름 불일치 — 커뮤니티 ⊂ communication**) |
| — (대응 행 없음) | `UTILITY_ENTRY` | **결측. 이 문서가 §2.9에서 제안한다** |

**귀결 1.** `CONTENT_OPEN`은 endpoint 문장이 **두 개**다(기사 본문 열림 / 영상 재생 시작).
따라서 `endpoint_signal_type`이 task마다 다르다(`URL_PATTERN` 또는 `MEDIA_STATE`).
`A2` §1.9의 상호배타는 **행 값**에 대한 제약이므로, archetype 수준에서는 **허용집합**을 주고
task 인스턴스가 그중 정확히 하나를 갖는다(규칙 AR-SIG-1).

**귀결 2.** `COMMUNICATION_ENTRY`의 SSOT 원문 라벨은 "커뮤니티"다. 메신저(1:1 대화)를 이 archetype에
넣을 때 SSOT 원문보다 넓게 해석하는 것이 되므로 §2.7 경계 규칙으로 명시 처리한다.

### 2.2 공통 규칙

| 규칙 | 내용 | 근거 |
|---|---|---|
| **AR-1 (단일값)** | `interaction_archetype`은 task 행당 정확히 1개 | `00` §6 |
| **AR-2 (행위 우선)** | archetype은 **사용자가 실제로 하는 조작의 구조**로 판정한다. 사업 도메인·서비스명·업종으로 판정하지 않는다 | `00` §6 `비즈니스 도메인과 실제 interaction 구조를 분리한다` |
| **E-SHAPE (완료 금지)** | `00` §3의 7개 endpoint는 전부 **완료가 아닌 진입** 시점이다. 어떤 archetype의 endpoint도 거래·전송·예약·발급의 **완료**로 정의하지 않는다 | `00` §3 절대 제외, `A1` §2.1 |
| **AR-BND (절대 제외 상한)** | 로그인 이후 / 본인인증 이후 / 결제·송금·예약 완료 / 회원가입 을 endpoint에 넣지 않는다. 경로 도중 이들이 나타나면 §2.10 종료조건으로 즉시 종료 | `00` §3 |
| **AR-SIG-1 (신호 허용집합)** | archetype은 `region_signal_type` / `endpoint_signal_type`의 **허용집합**을 정의하고, task 행은 그중 정확히 1값을 갖는다. 두 컬럼은 `A2` §1.9의 **동일 열거형**을 공유한다: `DOM_AX_ROLE` / `FORM_STRUCTURE` / `URL_PATTERN` / `MEDIA_STATE` / `GATE_SIGNAL` / `CODEBOOK_PENDING` | `A2` §1.9 |
| **AR-SIG-2 (1차 소스만)** | 이 두 컬럼은 **1차 판정 소스**만 담는다. 보조 확인 신호는 스키마에 넣지 않고 이 코드북의 `secondary_confirmation`(비구속 주석)에 둔다. 새 컬럼을 만들지 않는다 | `A1` §1.2, `01` §3 |
| **AR-AREA (영역 정의 위임)** | `region_definition`의 archetype 수준 문안은 `A1` §1.2 신호표 원문을 **전사**한다. 서비스별 구체화는 `02` §6 후보 랭킹 절차를 각 state에 재적용해 얻는다 | `A1` §1.2 |
| **AR-3 (region ≠ endpoint 강제 아님)** | 랜딩이 이미 영역이면 `NED=0`, 랜딩이 이미 endpoint면 `NED=IED=MPFED=0`이 정상 관측이다. 이를 피하려고 endpoint를 더 깊게 옮기지 않는다 | `A1` §1.4 |
| **AR-4 (activation 인정범위)** | scroll·문자단위 입력·redirect·passive loading·server wait·popup dismiss는 activation이 아니다. 영역 도달이 **scroll만으로** 가능하면 `FUNCTION_AREA_REACHED`가 성립한다 | `02` §9, `A1` §1.1 |
| **AR-5 (라벨 신설 금지)** | 판정 cascade의 어느 단계도 이 코드북에 없는 archetype·endpoint를 만들 수 없다 | `02` §10, `A1` §1.6 |

### 2.3 `QUERY`

| 항목 | 내용 |
|---|---|
| **정의 (사용자 행동)** | 사용자가 **자유 텍스트 검색어를 입력해 제출**하고, 서비스가 그 질의에 대한 결과 상태로 전환하는 행동 |
| **`region_definition`** | 검색어 입력 control이 focus 가능한 상태로 노출 (`input[type=search]` / `role=searchbox` / `role=combobox` + 제출 가능한 form 또는 제출 control) — `A1` §1.2 전사 |
| **`region_signal_type`** | `DOM_AX_ROLE` (허용집합: `DOM_AX_ROLE`, `FORM_STRUCTURE`) |
| **`endpoint_definition`** | **검색 query가 제출된 순간** — `00` §3 「검색」 전사 |
| **`endpoint_signal_type`** | 기본 `FORM_STRUCTURE` (허용집합: `FORM_STRUCTURE`, `URL_PATTERN`). *secondary_confirmation*: 질의 파라미터를 포함한 URL 전이, 결과 목록 컨테이너의 출현 |
| **종료조건(비-endpoint)** | 제출 전 로그인 요구 → `AUTH_GATE_REACHED` / CAPTCHA → `CAPTCHA` / 차단 → `BLOCKED` / 예산 소진 → `UNRESOLVED` + `UNRESOLVED_DEPTH_BUDGET_EXCEEDED` |
| **경계사례 — 이것은 `QUERY`가 아니다** | ① **자동완성 드롭다운 노출**은 제출이 아니다 → endpoint 미도달. ② 문자 단위 입력은 activation이 아니며 `text_input_episode`로 간다(`A1` §4.2). ③ **필터·정렬·카테고리 탭**은 자유 텍스트 질의가 아니다 → 대표 task가 그것이면 archetype은 `QUERY`가 아니라 목록 탐색이며, 그 목록이 향하는 대상에 따라 `CONTENT_OPEN`/`ITEM_DETAIL`이다. ④ **음성검색 진입**은 마이크 권한 프롬프트를 만들며 제출과 다르다 → 텍스트 경로를 대표 경로로 삼는다. ⑤ 검색으로 상품 상세까지 가는 경로: 대표 task가 `QUERY`로 동결됐다면 endpoint는 **제출 순간**이며 상세까지 가지 않는다(E-SHAPE). ⑥ 사이트 내부 검색만 있고 대표기능이 검색이 아닌 서비스에 `QUERY`를 붙이지 않는다(AR-2) |
| **전형 domain** | `PORTAL_SEARCH` |
| **비전형이나 유효** | `SHOPPING_COMMERCE`·`NEWS_CONTENT`·`MAP_MOBILITY`·`CONTENT_VIDEO` — 랜딩의 대표기능이 검색 제출이면 `QUERY` |

### 2.4 `CONTENT_OPEN`

| 항목 | 내용 |
|---|---|
| **정의 (사용자 행동)** | **이미 존재하는 콘텐츠 1건을 골라 열어 소비를 시작**하는 행동 (기사 읽기 시작 / 영상 재생 시작) |
| **`region_definition`** | 개별 콘텐츠(기사·영상) 항목의 링크·카드가 **목록 형태로** 노출 — `A1` §1.2 전사 |
| **`region_signal_type`** | `DOM_AX_ROLE` |
| **`endpoint_definition`** | **기사 본문이 열린 순간** (텍스트 하위유형) / **영상 재생이 시작된 순간** (미디어 하위유형) — `00` §3 「뉴스」·「영상」 전사. **task 행은 둘 중 하나를 문안으로 갖는다** |
| **`endpoint_signal_type`** | 허용집합 `{URL_PATTERN, MEDIA_STATE}`. 텍스트 하위유형 → `URL_PATTERN`, 미디어 하위유형 → `MEDIA_STATE`. 기본값 없음(task가 선택). *secondary_confirmation*: 기사 = `<article>`/본문 landmark + 제목·본문 텍스트 블록 출현 / 영상 = `<video>` play 이벤트 + `currentTime` 증가 |
| **종료조건(비-endpoint)** | 유료·회원 전용 벽 → `AUTH_GATE_REACHED` / 연령확인이 개인정보 입력을 요구 → `PERSONAL_DATA_REQUIRED` / 지역차단 → `BLOCKED` / 예산 소진 → `UNRESOLVED` |
| **경계사례 — 이것은 endpoint가 아니다** | ① **목록에서 요약(스니펫)만 인라인 확장**되는 것은 본문 열림이 아니다. ② **무음 autoplay 미리보기**는 재생 시작으로 보지 않는다 — 사용자 activation의 결과가 아니며, 자동 움직임은 Axis B의 motion/carousel 지표로 **별도** 기록된다(`00` §3 L0, §4). ③ **광고 pre-roll 재생**은 대표 콘텐츠의 재생이 아니다 → pre-roll 종료 후 본편 재생 시작을 endpoint로 본다. ④ **썸네일 hover/포커스 미리보기** 동일. ⑤ 라이브 스트림은 본편 재생과 동일하게 취급한다. ⑥ 목록 자체가 랜딩이면 `NED=0`이며, 그것을 endpoint로 올리지 않는다 |
| **전형 domain** | `NEWS_CONTENT`, `CONTENT_VIDEO` |
| **비전형이나 유효** | `PORTAL_SEARCH`(뉴스면이 대표기능인 경우), `SOCIAL_COMMUNICATION`(피드의 영상 재생이 대표기능인 경우), `SHOPPING_COMMERCE`(라이브커머스 시청이 대표기능인 경우) |

### 2.5 `ITEM_DETAIL`

| 항목 | 내용 |
|---|---|
| **정의 (사용자 행동)** | **거래 대상 1건의 상세면에 진입해 핵심 정보를 확인**하는 행동. 구매·주문은 하지 않는다 |
| **`region_definition`** | 개별 상품 항목의 링크·카드가 **목록 형태로** 노출 — `A1` §1.2 전사 |
| **`region_signal_type`** | `DOM_AX_ROLE` |
| **`endpoint_definition`** | **상품 상세와 핵심 상품정보가 보인 순간** — `00` §3 「쇼핑」 전사 |
| **핵심 상품정보 조작화** | `00` §3은 "핵심 상품정보"를 정의하지 않는다. 관측 가능한 **동시 충족 조건**으로 조작화한다: **(a) 개별 상품을 식별하는 상품명 텍스트 + (b) 가격 표기(품절·가격미표기 등 명시적 부재 문구 포함) + (c) 1차 거래 control(구매/주문/장바구니 등)이 DOM·AX에 PRESENT** — 세 요소가 같은 상세 문서 안에서 관측되면 충족. 이는 `A1` §0.4의 **수집 파라미터**(관측을 재현 가능하게 하는 판정 규칙)이며 해석 임계값이 아니다. **(c)의 PRESENT는 control의 존재이지 누름이 아니다** — 누르면 E-SHAPE 위반 |
| **`endpoint_signal_type`** | 기본 `URL_PATTERN` (허용집합: `URL_PATTERN`, `DOM_AX_ROLE`). *secondary_confirmation*: 상품 상세 URL 패턴 전이, `Product` 구조화 데이터, 가격 요소의 accessible name |
| **종료조건(비-endpoint)** | 상세 진입 전 로그인 요구 → `AUTH_GATE_REACHED` / 결제 단계 노출 → `PAYMENT_GATE_REACHED` / 성인인증 → `PERSONAL_DATA_REQUIRED` / 예산 소진 → `UNRESOLVED` |
| **경계사례 — 이것은 endpoint가 아니다** | ① **퀵뷰/미리보기 모달**에 가격만 뜬 상태 — (a)(b)(c) 세 요소가 모두 관측되면 충족으로 인정하되 `endpoint_signal_type = DOM_AX_ROLE`로 기록한다(URL이 바뀌지 않으므로). ② **목록 카드의 가격 표시**는 상세가 아니다. ③ **장바구니 담기 후 상태**는 상세 도달이 아니라 그 이후다 → 하지 않는다. ④ **옵션 선택 강제**로 가격이 가려진 경우: 상품명+1차 거래 control이 있고 가격이 "옵션 선택 시 표시"로 명시되면 (b)의 명시적 부재로 인정. ⑤ **카테고리 랜딩·기획전 페이지**는 개별 상품 상세가 아니다. ⑥ 배달 서비스의 **매장 상세**는 상품이 아니라 장소·판매자다 → 대표 task가 메뉴 1건 상세면 `ITEM_DETAIL`, 매장 찾기면 `PLACE_LOOKUP`(§2.6 경계) |
| **전형 domain** | `SHOPPING_COMMERCE` |
| **비전형이나 유효** | `SOCIAL_COMMUNICATION`(중고거래 게시물 상세가 대표기능인 경우), `FINANCE_PAYMENT`(금융상품 상세 열람이 대표기능인 경우), `MAP_MOBILITY`(예약 대상 좌석·차량 상세가 대표기능인 경우) |

### 2.6 `PLACE_LOOKUP`

| 항목 | 내용 |
|---|---|
| **정의 (사용자 행동)** | **지리적 장소를 질의하거나 특정 장소의 상세를 여는** 행동 |
| **`region_definition`** | 장소검색 입력 control **또는** 장소 항목 목록이 노출 — `A1` §1.2 전사 |
| **`region_signal_type`** | `DOM_AX_ROLE` |
| **`endpoint_definition`** | **장소검색이 제출되거나 장소 상세가 열린 순간** — `00` §3 「지도」 전사. **선언적 OR**: 두 분기 중 먼저 관측된 쪽이 endpoint |
| **`endpoint_signal_type`** | 기본 `URL_PATTERN` (허용집합: `FORM_STRUCTURE`, `URL_PATTERN`, `DOM_AX_ROLE`). 제출 분기 → `FORM_STRUCTURE`, 상세 분기 → `URL_PATTERN`(SPA로 URL이 불변이면 `DOM_AX_ROLE`) |
| **종료조건(비-endpoint)** | 로그인 요구 → `AUTH_GATE_REACHED` / 예산 소진 → `UNRESOLVED` |
| **경계사례** | ① **지도 pan/zoom**은 `02` §9 activation이 아니며 endpoint도 아니다. ② **브라우저 위치권한 프롬프트**는 종료조건이 아니다 — 로그인 gate도 개인정보 입력 요구도 아니므로 `AUTH_GATE_REACHED`/`PERSONAL_DATA_REQUIRED`로 기록하지 않는다. 권한을 부여하지 않고 텍스트 검색 경로로 진행한다(미결 Q-4: 네이티브 프롬프트의 기록 슬롯). ③ **현재 위치 자동표시**만으로는 "장소검색 제출"이 아니다. ④ **경로 안내(길찾기) 시작**은 장소 상세 이후 단계다 → endpoint를 그리로 옮기지 않는다. ⑤ **차량 호출·배차 확정**은 예약 완료에 준하므로 절대 제외. ⑥ 장소 상세가 곧 상점 상세인 경우: 대표 task가 장소 찾기이면 `PLACE_LOOKUP`, 판매 상품 1건 확인이면 `ITEM_DETAIL` |
| **전형 domain** | `MAP_MOBILITY` |
| **비전형이나 유효** | `SHOPPING_COMMERCE`(오프라인 점포 찾기가 대표기능인 경우), `PORTAL_SEARCH`(지도 서비스가 대표기능인 경우), `FINANCE_PAYMENT`(지점·ATM 찾기가 대표기능인 경우) |

### 2.7 `COMMUNICATION_ENTRY`

| 항목 | 내용 |
|---|---|
| **정의 (사용자 행동)** | **사람 사이의 글·메시지 교환 공간에 진입**하는 행동. 실제 발신·게시는 하지 않는다 |
| **`region_definition`** | 게시물/스레드 목록 **또는** 작성 진입 control이 노출 — `A1` §1.2 전사 |
| **`region_signal_type`** | `DOM_AX_ROLE` |
| **`endpoint_definition`** | **게시물/스레드/작성영역 진입 또는 로그인 gate** — `00` §3 「커뮤니티」 전사 |
| **`endpoint_signal_type`** | 허용집합 `{URL_PATTERN, DOM_AX_ROLE, GATE_SIGNAL}`. 게시물 상세 → `URL_PATTERN`, 작성영역(모달/인라인 에디터) → `DOM_AX_ROLE`, gate 분기 → `GATE_SIGNAL` |
| **`gate_is_endpoint`** | **true, 단 로그인 gate에 한한다** `[SHADOW 재정합]` — `00` §3 커뮤니티 행의 gate 절은 `또는 로그인 gate`뿐이다. **본인인증 gate는 endpoint가 아니며** `AUTH_GATE_REACHED`(개인정보 입력 요구 시 `PERSONAL_DATA_REQUIRED`)로 종료한다 (`A2` §1.5.1a 규칙 E-6a). §2.10.2 필독 |
| **`endpoint_status_detail`** | 로그인 gate로 endpoint가 실현되면 `ENDPOINT_VIA_AUTH_GATE` (`A2` §1.5.2). 이 값이 규칙 E-8 유병률 집계와 규칙 E-10 층화의 조건이다 |
| **종료조건(비-endpoint)** | 본인인증(휴대폰·실명) 요구 → `PERSONAL_DATA_REQUIRED` / CAPTCHA → `CAPTCHA` / 예산 소진 → `UNRESOLVED` |
| **경계사례** | ① **실제 메시지 전송·게시물 등록**은 절대 제외. ② **작성창 focus 획득**까지가 진입이며 문자 입력은 `text_input_episode`다. ③ **댓글 입력창**은 대표 task가 그것으로 동결된 경우에만 작성영역으로 인정한다 — 임의로 가장 가까운 입력창을 endpoint로 삼지 않는다. ④ **QR·앱 전환 로그인만 제공**하는 메신저 웹: 그것이 **로그인 gate**이면 endpoint 분기가 성립한다(`endpoint_status_detail = ENDPOINT_VIA_AUTH_GATE`). **본인인증 gate라면 성립하지 않는다**(규칙 E-6a) `[SHADOW 재정합]`. ⑤ **1:1 메신저**는 SSOT 원문 라벨이 "커뮤니티"이므로 확장 해석이다 — archetype 명칭(`COMMUNICATION_ENTRY`)이 `00` §6의 정본이고 §3 표는 예시(`예:`)이므로 포함으로 판정하되, 판정 근거를 `mapping_basis`에 남긴다. ⑥ **고객센터 문의·챗봇**은 사람 사이 교환이 아니면 `UTILITY_ENTRY` 쪽이다 |
| **전형 domain** | `SOCIAL_COMMUNICATION` |
| **비전형이나 유효** | `CONTENT_VIDEO`(커뮤니티 탭이 대표기능인 경우), `SHOPPING_COMMERCE`(중고 거래 채팅 진입이 대표기능인 경우), `PORTAL_SEARCH`(카페·블로그가 대표기능인 경우) |

### 2.8 `FINANCIAL_ACTION_ENTRY`

| 항목 | 내용 |
|---|---|
| **정의 (사용자 행동)** | **금융 처리 기능의 진입면에 도달**하는 행동. 조회·이체·결제의 **시작 지점**까지이며 실행하지 않는다 |
| **`region_definition`** | 금융기능 진입 control(조회·이체·인증 진입 등)이 노출 — `A1` §1.2 전사 |
| **`region_signal_type`** | `DOM_AX_ROLE` |
| **`endpoint_definition`** | **금융기능 진입 또는 로그인/인증 gate가 나타난 순간** — `00` §3 「금융」 전사 |
| **`endpoint_signal_type`** | 허용집합 `{GATE_SIGNAL, DOM_AX_ROLE, URL_PATTERN}`. 기본값 없음 — 한국 금융 모바일웹은 gate 분기 비율이 높을 것으로 예상되나 **예상을 기본값으로 굳히지 않는다** |
| **`gate_is_endpoint`** | **true — 로그인 gate·본인인증 gate 둘 다** `[SHADOW 재정합]`. `00` §3 금융 행의 gate 절이 `또는 로그인/인증 gate`이기 때문이다 (`A2` §1.5.1a 규칙 E-6a). §2.10.2 필독 |
| **`endpoint_status_detail`** | gate로 endpoint가 실현되면 `ENDPOINT_VIA_AUTH_GATE` (`A2` §1.5.2). 규칙 E-8·E-10의 조건 컬럼이다 |
| **종료조건(비-endpoint)** | 결제 단계 노출 → `PAYMENT_GATE_REACHED` / 계좌·주민번호 등 입력 요구 → `PERSONAL_DATA_REQUIRED` / CAPTCHA → `CAPTCHA` / 예산 소진 → `UNRESOLVED` |
| **경계사례** | ① **송금·이체 실행, 결제 완료**는 절대 제외. ② **앱 설치 유도로만 진행 가능**한 경우: 웹에서 더 진행 불가 → `UNRESOLVED`이며 앱 설치 유도 자체는 L0 interrupt 축으로 기록된다(`00` §3 L0). ③ **보안 프로그램 설치 요구**는 로그인 gate와 구분한다 — 진행 차단이면 `BLOCKED`. ④ **공개 정보 조회**(환율·금리 표)는 금융 처리 진입이 아니다 → 대표 task가 그것이면 `UTILITY_ENTRY` 쪽이다. ⑤ **커머스의 결제 진입**: domain이 `SHOPPING_COMMERCE`여도 대표 task가 결제 진입이면 archetype은 `FINANCIAL_ACTION_ENTRY`다(§4.1 D3) |
| **전형 domain** | `FINANCE_PAYMENT` |
| **비전형이나 유효** | `SHOPPING_COMMERCE`(결제 진입이 대표기능), `MAP_MOBILITY`(요금 결제 진입), `UTILITY_OTHER`(포인트 전환·출금 진입) |

### 2.9 `UTILITY_ENTRY` — **신규 제안 (감사 판정 대상)**

> **이 절만이 `00`이 정의하지 않은 것을 새로 만든다.** 나머지 6종은 전사다.
> 채택 전까지 `region_signal_type = CODEBOOK_PENDING`이며 `A2` 규칙 P-2에 따라 `mapping_status = FROZEN` 불가.

#### 2.9.1 왜 이 archetype이 필요한가

`00` §6이 `UTILITY_ENTRY`를 archetype 목록에 넣었으나 `00` §3 L1 표에 대응 행을 두지 않았다.
대안(§2.9.4 U-3)은 이 archetype을 폐지하고 6종에 강제 배정하는 것인데, 그것은
`00` §9의 *"5건을 초과하는 모호한 사례를 억지로 분류하지 않는다"* 정신에 반하고,
`ExcessDepth`의 기준선이 되는 archetype 내부 동질성을 오염시킨다(성격이 다른 서비스를
`QUERY` 중앙값 계산에 섞으면 그 중앙값이 다른 서비스의 기준선까지 왜곡한다).

#### 2.9.2 제안 endpoint — **U-1 (권고)**

> **`UTILITY_ENTRY` endpoint = 대표 유틸리티 기능의 전용 기능면(function surface)이 열리고,
> 그 기능의 1차 조작 대상(primary control)이 PRESENT ∧ HITTABLE 상태로 관측된 순간.**

- **PRESENT ∧ HITTABLE**의 의미는 `A1` §1.1이 `FUNCTION_AREA_REACHED`에 대해 정의한 것과 동일한 관측 술어를 재사용한다. 새 술어를 만들지 않았다.
- **"기능면"** = 그 도구의 조작이 이루어지는 화면 영역(계산기의 키패드, 편집기의 입력면, 조회도구의 조건입력·결과면).
- **"1차 조작 대상"** = `02` §6 후보 랭킹 절차의 그 state SELECTED 후보(`A1` §5 `fact_primary_action_candidate`와 동일 개념).
- **endpoint에서 그 control을 누르지 않는다.** 노출·조작가능 관측까지다.
- `endpoint_signal_type` 허용집합 `{DOM_AX_ROLE, URL_PATTERN}`, 기본 `DOM_AX_ROLE`.
- `region_definition` = 해당 task의 **기능면 진입 control**이 노출 (`A1` §1.2 문안의 구체화).
- **`gate_is_endpoint` = false** (§2.9.5 참조).

#### 2.9.3 근거

| # | 근거 | 출처 |
|---|---|---|
| G1 | **명명 정합.** SSOT 저자는 이 값을 `UTILITY_ENTRY`로 명명했다. `_ENTRY` 접미사를 가진 다른 두 archetype(`COMMUNICATION_ENTRY`·`FINANCIAL_ACTION_ENTRY`)의 `00` §3 endpoint는 **행위 완결형이 아니라 진입형**("작성영역 진입", "금융기능 진입")이다. 같은 접미사 family의 endpoint 형태를 따르는 것이 SSOT 어휘와 정합한다 | `00` §6, §3 |
| G2 | **깊이 수준 정합.** `00` §3의 7행 endpoint는 전부 "완료가 아닌 진입"이며 `A1` §2.1이 통상 경로를 navigation 1~2 + 영역 내 1~2로 상정했다. U-1은 그 범위 안에 있고, 완료형(U-2)은 그 범위를 넘길 위험이 있다 | `A1` §2.1 |
| G3 | **절대 제외 미침범.** U-1은 로그인·본인인증·결제/송금/예약 완료·회원가입 중 어느 것도 통과하지 않는다. 유틸리티 서비스에서 절대 제외에 가장 쉽게 닿는 경로는 "도구 실행 결과 확인"인데(발급·전환·신청 완료), U-1은 그 앞에서 멈춘다 | `00` §3 절대 제외 |
| G4 | **관측 가능성.** PRESENT ∧ HITTABLE은 이미 `A1` §1.1이 정의한 결정적 술어이며 DOM/AX + hit-test로 판정된다. 새 신호기를 요구하지 않아 `02` §1 우선순위 1단계에서 닫힌다 | `A1` §1.1, `02` §1 |
| G5 | **이질성 봉쇄.** 유틸리티 도구는 산출물이 제각각(숫자·파일목록·문서·포인트)이라 "결과"를 공통 정의하면 서비스마다 다른 깊이를 뜻하게 된다. "기능면 도달"은 도구 종류와 무관하게 같은 의미를 갖는다 | `00` §7 상대 깊이 |

#### 2.9.4 대안 (감사가 채택할 수 있는 선택지)

| id | 내용 | 장점 | 단점 / 위험 |
|---|---|---|---|
| **U-1** *(권고)* | 기능면 도달 + 1차 조작 대상 PRESENT ∧ HITTABLE | G1~G5 | 단일목적 유틸리티에서 **랜딩 = 기능면**이 되어 `MPFED = 0`에 질량이 몰릴 수 있다 → archetype 내 중앙값이 0이 되어 `ExcessDepth`의 변별력이 낮아진다(미결 Q-3) |
| **U-1g** | U-1 + "또는 로그인/인증 gate가 나타난 순간"(gate 분기 추가, `gate_is_endpoint = true`) | 로그인 선행형 유틸리티에서 depth가 `NULL`로 사라지지 않는다 | `00` §3이 gate 분기를 **금융·커뮤니티 두 행에만** 부여했다. 세 번째 archetype에 확장하는 것은 SSOT가 주지 않은 권한의 확대다 |
| **U-2** | **유틸리티 기능이 1회 실행돼 그 결과 상태가 화면에 반영된 순간** | `QUERY`(제출)·`CONTENT_OPEN`(재생 시작)과 같은 "행위 완결형"이라 6종과 형태가 맞는다 | 결과 정의가 서비스마다 이질적(G5). 발급·신청·전환류에서 **절대 제외 침범 위험**. `00` §3 「금융·커뮤니티」가 진입형인 점과 불일치 |
| **U-3** | archetype 폐지 — 6종 중 최근접으로 강제 배정, 불가하면 `mapping_status = EXCLUDED` | 새 정의를 만들지 않는다(가장 보수적) | `00` §6이 열거한 값을 코드북이 삭제하는 것 = SSOT 위반. 강제 배정은 `00` §9 정신 위반이며 6종의 중앙값을 오염시킨다 |
| **U-4** | U-1을 채택하되 `UTILITY_ENTRY`를 **`ExcessDepth` 기준선 archetype에서 제외**하고 기술통계에만 노출 | 이질 잔여군이 상대깊이 비교를 오염시키지 않는다 | `00` §7·§11에 없는 **분석 규칙 신설**이므로 이 문서의 권한 밖이다 → 미결 Q-3으로 올린다 |

#### 2.9.5 gate 분기를 넣지 않은 이유

`00` §3은 gate-as-endpoint를 **금융·커뮤니티 두 행에만** 부여했다.
새 archetype에 그 권한을 확장하면 "SSOT가 정의하지 않은 것을 만든다"의 범위가 endpoint 문안 하나에서
**종료의미론 확장**으로 커진다. 따라서 U-1은 보수적으로 gate 분기 없이 정의하고,
유틸리티 경로에서 gate를 만나면 `AUTH_GATE_REACHED`로 종료한다(`endpoint_reached = 0`, depth `NULL`).
이 선택의 대가(로그인 선행형 유틸리티의 depth 소실)를 감사가 감수할지 U-1g로 갈지는 **판정 대상**이다(Q-2).

#### 2.9.6 표

| 항목 | 내용 |
|---|---|
| **정의 (사용자 행동)** | 특정 목적의 **도구를 꺼내 쓸 수 있는 상태**로 만드는 행동 |
| **`region_definition`** | 해당 task의 **기능면 진입 control**이 노출 (`A1` §1.2 "endpoint를 생성하는 control이 노출"의 구체화) |
| **`region_signal_type`** | 채택 전 `CODEBOOK_PENDING` → 채택 후 `DOM_AX_ROLE` |
| **`endpoint_definition`** | §2.9.2 U-1 |
| **`endpoint_signal_type`** | 채택 전 `CODEBOOK_PENDING` → 채택 후 기본 `DOM_AX_ROLE` (허용집합 `{DOM_AX_ROLE, URL_PATTERN}`) |
| **종료조건(비-endpoint)** | 로그인/인증 gate → `AUTH_GATE_REACHED` / 개인정보 입력 요구 → `PERSONAL_DATA_REQUIRED` / 결제 → `PAYMENT_GATE_REACHED` / CAPTCHA → `CAPTCHA` / 차단 → `BLOCKED` / 예산 소진 → `UNRESOLVED` |
| **경계사례 — 이것은 `UTILITY_ENTRY`가 아니다** | ① 도구의 **실행 결과 확인**(발급 완료·전환 완료·신청 완료) — E-SHAPE·절대 제외 위반. ② **범용 검색 도구**는 `QUERY`다. ③ **파일·사진 목록에서 항목 1건 열기**가 대표기능이면 `CONTENT_OPEN` 쪽이 더 정확하다 — 목록→개별 콘텐츠 소비 구조이기 때문. ④ **포인트 출금·전환 진입**은 `FINANCIAL_ACTION_ENTRY`다. ⑤ **설정 화면 도달**은 대표기능이 아니다 — 대표기능 후보 랭킹(`02` §6)에서 설정·계정 메뉴는 대표 후보가 아니다. ⑥ **앱 다운로드 페이지만 있는 서비스**는 유틸리티 기능면이 웹에 없다 → `web_eligibility` 단계에서 처리되며 여기서 endpoint를 억지로 만들지 않는다 |
| **전형 domain** | `UTILITY_OTHER` |
| **비전형이나 유효** | `FINANCE_PAYMENT`(공개 환율·금리 조회 도구가 대표기능), `MAP_MOBILITY`(대중교통 시간표 조회 도구), `SHOPPING_COMMERCE`(멤버십 바코드·쿠폰 도구), `PORTAL_SEARCH`(날씨·번역 도구) |

### 2.10 종료조건 — 공통 (비-endpoint)

#### 2.10.1 `02` §7의 7값 (`A2` §1.5.1, 집합 불확장)

| 상황 | `endpoint_status` | `endpoint_reached` | NED/IED/MPFED |
|---|---|---|---|
| 해당 archetype의 endpoint 관측 | `FUNCTION_ENDPOINT_REACHED` | 1 | 정수 |
| 로그인/인증 gate — **`A2` §1.5.1a가 그 archetype·그 gate 종류에 endpoint를 주지 않은 경우** `[SHADOW 재정합]` | `AUTH_GATE_REACHED` | 0 | `NULL` |
| 로그인/인증 gate — **`A2` §1.5.1a 규범표가 endpoint로 준 경우**(금융의 로그인·본인인증 gate, 커뮤니티의 로그인 gate) | `FUNCTION_ENDPOINT_REACHED` + `endpoint_status_detail = ENDPOINT_VIA_AUTH_GATE` | 1 | 정수 |
| 결제 단계 노출 | `PAYMENT_GATE_REACHED` | 0 | `NULL` |
| 개인정보 입력 요구 | `PERSONAL_DATA_REQUIRED` | 0 | `NULL` |
| 사람 검증 요구 | `CAPTCHA` | 0 | `NULL` |
| 접근 차단 | `BLOCKED` | 0 | `NULL` |
| 어느 조건에도 미도달 | `UNRESOLVED` (+ `endpoint_status_detail`) | 0 | `NULL` |

- **결제·본인인증을 우회하지 않는다**(`02` §7).
- **`NULL`을 `0`이나 예산 상한으로 대체하지 않는다**(`A1` §1.5, §2.4).
- **이들은 measurement status이며 KWCAG 판정으로 전환하지 않는다**(`A2` 규칙 E-3).

#### 2.10.2 gate가 endpoint인 두 archetype — **A2 §1.5.1a 로 해소됨 (Q-1 CLOSED)**

> 이 절은 `[SHADOW 재정합 · base d5f1da5]`에서 다시 쓰였다. 초판(base `6fad79f`)은 이것을
> **미결 Q-1**으로 올렸고, 그 사이 LANE 0가 `V2-C003`·`V2-C004`로 `A2` §1.5.1a를 신설해 닫았다.
> **정본은 `A2` §1.5.1a(규칙 E-5 ~ E-10)이며 이 절은 그것을 가리킬 뿐 정책을 복제하지 않는다.**
> 코드북 초판이 제안했던 규칙 `GATE-1`은 **폐기**한다 — 아래 ②의 이유로 문면이 틀렸다.

**해소된 충돌.** `00` §3은 금융·커뮤니티의 endpoint 문안 안에 gate를 넣었는데
`A2` §1.5.1의 `AUTH_GATE_REACHED`는 `endpoint_reached = 0` · `MPFED = NULL`이다.
그대로 겹치면 두 archetype의 depth가 구조적으로 전부 `NULL`이 되어
`00` §11 분포와 `00` §7 `ExcessDepth` 기준선이 성립하지 않는다.
`A2` §0 7항 **EXC-2**가 `00 > 01` 우선순위로 이 충돌을 해소했다.

**A2가 확정한 기록 방식** (정본: `A2` §1.5.1a 규범표):

| archetype | 관측된 gate 종류 | `endpoint_status` | `endpoint_status_detail` | `endpoint_reached` |
|---|---|---|---|---|
| `FINANCIAL_ACTION_ENTRY` | 로그인 gate **또는 본인인증 gate** | `FUNCTION_ENDPOINT_REACHED` | `ENDPOINT_VIA_AUTH_GATE` | 1 |
| `COMMUNICATION_ENTRY` | **로그인 gate만** | `FUNCTION_ENDPOINT_REACHED` | `ENDPOINT_VIA_AUTH_GATE` | 1 |
| `COMMUNICATION_ENTRY` | **본인인증 gate** | `AUTH_GATE_REACHED` (개인정보 입력 요구 시 `PERSONAL_DATA_REQUIRED`) | `NULL` | 0 |
| 나머지 5 archetype | 모든 gate 종류 | `AUTH_GATE_REACHED` (동상) | `NULL` | 0 |

**초판 GATE-1이 틀렸던 두 지점.**

① **기록 슬롯.** GATE-1은 사실을 `endpoint_signal_type = GATE_SIGNAL`에 담자고 했다.
`A2`는 `endpoint_status_detail = ENDPOINT_VIA_AUTH_GATE`(§1.5.2)에 담는다.
`endpoint_signal_type`은 *무엇이 신호를 냈는가*(신호원)이고 `endpoint_status_detail`은
*endpoint가 무엇으로 실현됐는가*(사건의 의미)다. 규칙 E-8의 유병률 합집합과 규칙 E-10의 층화가
**후자를 조건으로 쓰므로**, 전자에만 적으면 두 집계가 성립하지 않는다.

② **gate 종류의 archetype별 한정 (규칙 E-6a).** GATE-1은 두 archetype을 똑같이
"로그인/인증 gate"로 일반화했다. `00` §3의 두 행은 gate 절이 **서로 다르다** —
금융은 `로그인/인증`, 커뮤니티는 `로그인`뿐이다. 일반화는 `00` §3 커뮤니티 행을 넓히는 SSOT 침범이며,
`V2-C003` 감사가 `a2-1-5-1a-widens-00-3-community-gate-clause-to-any-auth-gate`로 지적해 `V2-C004`가 시정했다.
**따라서 `COMMUNICATION_ENTRY`의 본인인증 gate는 endpoint가 아니다.**

**여전히 유효한 무조건 규칙.**

- **GATE-2 (유지, = `A2` 규칙 E-7).** gate를 **통과하지 않는다.** `00` §3 절대 제외는 불변이며
  scout는 두 archetype에서도 gate 관측 **즉시 종료**한다. 달라지는 것은 종료 후 저장하는 값뿐이다.
- **GATE-3 (유지, = `A2` 규칙 E-6).** 7값 집합은 확장되지 않는다. 이 예외는 위 두 archetype과
  규칙 E-6a가 그 행에 허용한 gate 종류를 **넘지 않는다.** `UTILITY_ENTRY`를 포함한 다른 archetype으로의
  확장은 금지다.
- **GATE-4 (신설 — 코드북의 몫).** gate 종류(로그인 gate ↔ 본인인증 gate)의 판별은
  **수집기의 재량이 아니라 이 코드북이 정의할 관측 규칙**이다(`A2` §1.5.1a).
  코드북이 가르지 못한 gate는 `endpoint_definition` 미충족으로 보아 endpoint로 승격시키지 않는다.
  → 이 판별 규칙 자체는 아직 **미작성**이다. `OPEN_QUESTIONS.md` **Q-9**로 새로 등재했다.

**층화 의무 (규칙 E-10).** 이 두 archetype의 `MPFED` 계열 지표는
`endpoint_status_detail = ENDPOINT_VIA_AUTH_GATE` 여부로 **층을 갈라 병기**해야 한다.
합산값만 제시하면 `ExcessDepth` 기준선이 `동종 대비 깊은가`가 아니라
`로그인 벽을 앞에 세웠는가`를 재게 된다. 이는 분석 phase(P-H)의 이행 의무다.

#### 2.10.3 예산 소진

`A1` §2.1의 네 예산(`MAX_ACTIVATIONS_PER_TASK=8` 등) 중 하나가 발화하면
`endpoint_status = UNRESOLVED` + `endpoint_status_detail = UNRESOLVED_DEPTH_BUDGET_EXCEEDED`,
우측절단으로 별도 집계, `ExcessDepth` 산출하지 않음(`A2` 규칙 E-4).
**이 값은 접근성 FAIL이 아니다**(`A1` §2.3).

---

## 3. 매핑 규칙

### 3.1 대표 task 1개 원칙

`00` §6: *"한 measurement entity당 원칙적으로 대표 task 1개."*
`00` §5: *"Representative Task = `web_target × representative_task`. 한 web target에 같은 대표task를 여러 번 중복 측정하지 않는다."*

| 규칙 | 내용 |
|---|---|
| **MAP-1 (기본)** | 한 `measurement_entity_id`에 `mapping_status ∈ {FROZEN}` 인 `dim_representative_task` 행은 **1개**다 |
| **MAP-2 (선정 기준)** | 대표 task는 (a) 그 서비스가 스스로 1차로 내세우는 기능, (b) `02` §6 후보 랭킹에서 최상위로 선택된 기능, (c) 해당 domain에서 그 서비스가 패널에 등재된 이유 — 순으로 판정한다 |
| **MAP-3 (예외 A: web target 분기)** | 한 measurement entity가 **복수의 web target**을 갖는 경우(`web_target_group`이 1:N), task 행은 `web_target_id` 단위로 생성될 수 있다. 이때도 **web target 하나당 task 1개**다. entity 수준 요약(`mart_service_summary`)에서 어느 target을 대표로 쓸지는 P-B가 정한다 |
| **MAP-4 (예외 B: 동률 후보)** | 후보 2개의 랭킹 근거가 대등하면 **둘 다 만들지 않는다.** §3.5 abstain으로 보내고 cascade가 해소한다. 두 개를 다 동결해 depth를 두 번 세는 것을 금지한다 |
| **MAP-5 (예외 C: 대표 task 부재)** | 웹에서 어떤 대표기능도 성립하지 않으면(앱 전용 안내면 등) `mapping_status = EXCLUDED`. 억지로 archetype을 붙이지 않는다 |
| **MAP-6 (중복 측정 금지)** | 같은 `web_target × archetype` 조합으로 task 행을 2개 만들지 않는다. 재측정은 `fact_task_entry` 수준의 append이지 새 task 행이 아니다 |
| **MAP-7 (domain·archetype 독립)** | 두 컬럼은 BD-3/AR-2에 따라 독립 판정되며, 한쪽이 abstain이어도 다른 쪽은 확정될 수 있다. **`mapping_status`는 두 축 중 하나라도 미확정이면 `FROZEN`이 될 수 없다** |

### 3.2 동결 규율 — 절차로서의 blind mapping

`00` §6: *"매핑은 접근성 outcome과 인증 여부를 보기 전에 동결한다."*
`A2` 규칙 P-1: *"`FROZEN` 전이는 KWCAG 결과·`certified_current`를 읽기 전에 일어나야 한다. 동결 시각과 접근성 산출물 생성 시각의 순서를 artifact로 남긴다."*
`PHASE_GATES` P-A: *"Pilot Mapping — 10~15개 service를 **source context만** 보고 매핑. 인증·KWCAG outcome 차단 확인."*

선언이 아니라 **절차**로 강제한다.

| 단계 | 행위 | 남기는 artifact |
|---|---|---|
| **F0** | 매핑 작업공간을 연다. 입력 allowlist(§3.3)에 없는 산출물 경로를 **읽지 않는다** | `mapping_run_manifest`: 실행 시각, base SHA, 허용 입력 경로 목록과 각각의 content hash |
| **F1** | domain·archetype·endpoint를 판정한다. cascade는 §3.4 | 단계별 `mapping_basis`, cascade 단계 기록 |
| **F2** | `mapping_status`를 `DRAFT → CANDIDATE`로 전이 | 전이 시각 |
| **F3** | **동결 선언.** `mapping_status = FROZEN`. 이 시점의 task 집합 전체를 해시로 봉인 | `mapping_freeze_stamp`: 동결 시각(UTC), 동결된 행 집합의 hash, base SHA |
| **F4** | **동결 이후에만** L0/L1 수집·KWCAG 판정·`certified_current` 산출을 시작한다 | 각 접근성 산출물의 생성 시각 |
| **F5** | **순서 검증.** `mapping_freeze_stamp.frozen_at < min(모든 접근성 산출물 생성 시각)` 을 자동 검사한다. 위반이면 gate 실패 | 검증 결과 |

| 규칙 | 내용 |
|---|---|
| **FRZ-1 (단방향)** | `DRAFT → CANDIDATE → {FROZEN, AMBIGUOUS_UNRESOLVED, EXCLUDED}` 단방향(`A2` §1.9). `FROZEN` 이후 되돌리지 않는다 |
| **FRZ-2 (동결 후 변경)** | 동결 후 매핑 오류가 발견되면 조용히 고치지 않는다. **정정 사유·발견 시점·발견자·정정 후 재동결 시각**을 append로 남기고 그 사실을 분석 보고에 노출한다 |
| **FRZ-3 (재동결 금지 사유)** | 접근성 결과·인증 결과를 본 뒤에 "이 서비스는 archetype이 잘못됐다"는 이유로 매핑을 바꾸는 것은 **금지**다. 이것이 `00` §6이 막으려는 정확한 행위다 |
| **FRZ-4 (`CODEBOOK_PENDING` 차단)** | `region_signal_type = CODEBOOK_PENDING` 또는 `endpoint_signal_type = CODEBOOK_PENDING`인 행은 `FROZEN`이 될 수 없다(`A2` 규칙 P-2) |

### 3.3 입력 allowlist / denylist

| 티어 | 허용 입력 | 적용 |
|---|---|---|
| **T1 (source context)** | `panel_registry`, `source_ranking_rows`, `source_membership`, `service_master`(`service_name_canonical`·`domain`·`axis_type`·`canonicalization_basis`), `entity_alias_map` | Pilot(P-A A5)은 **T1만** 사용한다 (`PHASE_GATES` P-A) |
| **T2 (target identity)** | `dim_web_target`의 `official_landing_url`·`final_url`·`registered_domain`·`url_evidence` | P-B 본매핑에서 추가 허용 |
| **T3 (기능면 구조)** | `02` §6 대표기능 후보 추출 결과(accessible name, visible text, nearby heading, href, role, bbox, viewport visibility) 및 그 embedding 랭킹 | P-B 본매핑에서 추가 허용. **구조 정보이지 접근성 판정이 아니다** |

| **차단(denylist) — 어느 티어에서도 금지** | 근거 |
|---|---|
| `fact_criterion_result` 전체 (PASS/FAIL/UNDETERMINED/NA, verdict_state, final_status) | `00` §6, `A2` P-1 |
| `dim_certification` · `certified_current` · 인증목록 원자료 | `00` §4 Axis C, `00` §6 |
| `fact_landing_observation`의 측정 스칼라(대비·크기·overlay coverage·occlusion·density) | Axis A/B 산출물 |
| `fact_interrupt_element`의 판정 결과(`final_label`, `blocking`, `dismiss_*`) | 〃 |
| `fact_task_entry` / `fact_task_step`의 depth·endpoint 결과 | 매핑의 하류이므로 순환 |
| `mart_*` 전체 | 위의 집계 |

**규칙 IN-1.** T3의 구조 정보는 **접근성 판정이 아니므로** 매핑 입력으로 허용되나,
그것을 근거로 "이 서비스는 대비가 나쁘니 다른 archetype으로 보자" 같은 추론을 하는 순간 FRZ-3 위반이다.
**T3는 무엇을 하는 서비스인가만 답할 수 있고, 얼마나 잘 하는가는 답할 수 없다.**

**규칙 IN-2.** allowlist 위반은 사후에 증명할 수 없으므로 **F0의 `mapping_run_manifest`에 읽은 입력의 hash를 남기는 것**이
유일한 강제수단이다. manifest에 없는 경로를 읽은 흔적(로그·캐시)이 발견되면 그 매핑 run은 무효다.

### 3.4 판정 cascade — 각 단계가 무엇을 보고 무엇을 못 보는가

`00` §9·§10, `02` §1·§10, `03` M0(`rule + source context + embedding + AI review`), `A1` §1.6을 따른다.
**1단계에서 판정되면 상위 단계를 호출하지 않는다.**

| 단계 | `mapping_basis` | 보는 것 | **못 보는 것 / 못 하는 것** | 산출 |
|---|---|---|---|---|
| **1. deterministic rule** | `RULE` | 등록 도메인 문자열, 서비스명 canonical 토큰, `axis_type`, 이 코드북의 포함/제외 규칙 | 화면을 못 본다. 의미 유사도를 못 쓴다. 규칙에 없는 신조어를 못 다룬다 | domain·archetype 확정 또는 `NO_RULE_MATCH` |
| **2. source context** | `SOURCE_CONTEXT` | 원자료 패널의 카테고리 문맥, 랭킹 위치, 다른 패널에서의 동반 등장 | 서비스 **내부** 구조를 못 본다. 패널 카테고리가 사업분류라 **archetype(행위 구조)을 직접 답하지 못한다** — 주로 domain에 기여 | domain 후보 + 신뢰도 |
| **3. embedding similarity** | `EMBEDDING` | 후보 control의 accessible name·visible text·nearby heading을 archetype **endpoint 설명문**과 임베딩 비교(`02` §6) | 시각적 배치·아이콘 의미를 못 본다. 텍스트가 없는 icon-only control을 못 다룬다. **유사도는 순위이지 판정이 아니다** — 임계값으로 자동 확정하지 않는다 | 후보 순위 + 유사도 점수 |
| **4. AI reviewer A** | `AI_REVIEW` | `02` §10 evidence package만(screenshot crop, surrounding screenshot, DOM/AX facts, bbox, relevant text, **허용 label 목록**, rule excerpt) | **사이트를 자유 탐색하지 못한다.** 새 label·새 endpoint를 만들지 못한다(AR-5). 접근성·인증 정보를 받지 못한다(§3.3) | JSON classification only |
| **4′. AI reviewer B → arbiter** | `AI_REVIEW` | A와 **독립**으로 같은 evidence package | A의 답을 보지 못한다(독립성 조건). arbiter는 두 답과 evidence만 본다 | 합의 라벨 또는 불일치 |
| **5. HUMAN_FINAL** | `HUMAN_FINAL` | 전체 evidence package + 이 코드북 | 예산 `HUMAN_FINAL_REVIEW_MAX = 5`. `fact_ai_adjudication.human_required`와 **같은 예산을 공유**(`A2` §1.9·§4.6) | 최종 라벨 |

| 규칙 | 내용 |
|---|---|
| **CAS-1** | `mapping_basis`는 **최종 확정에 사용된 단계**를 기록한다. 거쳐온 단계 이력은 별도로 남긴다 |
| **CAS-2** | 3단계 유사도만으로 확정하지 않는다. 1위와 2위 후보가 근접하면 4단계로 올린다 |
| **CAS-3** | 4단계 이상에서 `ABSTAIN`이 나오면 §3.5 |
| **CAS-4** | 어느 단계도 이 코드북에 없는 archetype·endpoint·domain 값을 만들 수 없다 |
| **CAS-5** | 예산(5건)이 소진된 상태에서 5단계가 필요하면 **`RESOLVED`로 위장하지 않는다** — `ai_review_status = ESCALATION_DECLINED_BUDGET` + `ABSTAIN`(`A2` 규칙 A-1) |

### 3.5 abstain 경로

`00` §9: *"5건을 초과하는 모호한 사례를 억지로 분류하지 않는다. 나머지는 `UNDETERMINED / ABSTAIN`."*

```
후보 모호 (BD-5 / MAP-4 / CAS-2)
  └→ cascade 3 → 4 → 4′
        ├ 합의 → mapping_status = FROZEN,  mapping_basis = AI_REVIEW
        ├ 불일치 + 사람 예산 남음 → human_final_required = 1 → HUMAN_FINAL
        │     └→ mapping_status = FROZEN,  mapping_basis = HUMAN_FINAL
        └ 불일치 + 사람 예산 소진
              → fact_ai_adjudication.final_status = ABSTAIN
              → dim_representative_task.mapping_ai_review_status = ABSTAINED
                 (+ ESCALATION_DECLINED_BUDGET)
              → mapping_status = AMBIGUOUS_UNRESOLVED
```

| 규칙 | 내용 |
|---|---|
| **AB-1 (귀속)** | `ABSTAIN`은 `fact_ai_adjudication.final_status`의 값이다. `dim_representative_task`에는 `mapping_ai_review_status = ABSTAINED`라는 **그림자 상태**로 나타나고, task 자체의 상태는 `mapping_status = AMBIGUOUS_UNRESOLVED`다 (`A2` §2.1) |
| **AB-2 (강제분류 금지)** | `AMBIGUOUS_UNRESOLVED`를 피하려고 `UTILITY_OTHER`/`UTILITY_ENTRY`로 밀어넣지 않는다. 잔여값은 **근거가 없을 때** 쓰는 값이지 **판단이 안 될 때** 쓰는 값이 아니다(BD-4) |
| **AB-3 (하류 취급)** | `AMBIGUOUS_UNRESOLVED` task는 L1 측정 대상이 되지 않는다. `mart_archetype_summary`의 어떤 archetype 분모에도 넣지 않으며, 별도 건수로 보고한다 |
| **AB-4 (실증 요구)** | `PHASE_GATES` P-A는 *"ambiguous가 강제분류되지 않고 abstain 가능함이 **실증**됨"* 을 통과조건으로 둔다. Pilot(A5)에서 **최소 1건의 abstain 또는 abstain 경로 도달 기록**이 나와야 한다. 0건이면 경로가 실제로 열려 있는지 주입 시험으로 증명한다 |
| **AB-5 (`EXCLUDED`와 구분)** | `EXCLUDED`는 *대표 task를 정의할 수 없다*(대상 부재), `AMBIGUOUS_UNRESOLVED`는 *정의는 되는데 어느 것인지 확정 못한다*(판정 실패). 둘을 섞지 않는다 |

### 3.6 `dim_representative_task` 필드 채움 규칙

`01` §3의 12개 컬럼 + `A1` §1.8의 2개 추가 컬럼. **이 코드북은 새 컬럼을 만들지 않는다.**

| 컬럼 | 채움 규칙 |
|---|---|
| `task_id` | P-B 소관(식별자 생성 규칙) |
| `measurement_entity_id` | `service_master` 조인 |
| `web_target_id` | `dim_web_target` 조인. MAP-3 |
| `business_domain` | §1.2 8종 중 1 |
| `interaction_archetype` | §2 7종 중 1 |
| `primary_function_name` | 그 서비스에서 관측된 대표기능의 **자연어 명칭**(자유 텍스트). archetype 코드를 그대로 복사하지 않는다 |
| `endpoint_definition` | 해당 archetype의 `endpoint_definition` 문안을 기본으로 하고, `CONTENT_OPEN`·`PLACE_LOOKUP`처럼 분기가 있는 경우 **선택된 분기 문안**을 넣는다. 문안을 임의로 깊게 고쳐 쓰지 않는다 |
| `endpoint_signal_type` | 해당 archetype 허용집합 중 1 (AR-SIG-1) |
| `mapping_basis` | `RULE` / `SOURCE_CONTEXT` / `EMBEDDING` / `AI_REVIEW` / `HUMAN_FINAL` (§3.4 CAS-1) |
| `mapping_status` | `DRAFT` / `CANDIDATE` / `FROZEN` / `AMBIGUOUS_UNRESOLVED` / `EXCLUDED` (§3.2) |
| `mapping_ai_review_status` | `A2` §1.10 공유 열거형 |
| `human_final_required` | 0/1. 1이면 5건 예산 소비 |
| `region_definition` *(A1 §1.8)* | 해당 archetype의 `region_definition` 문안 + 서비스별 구체화 |
| `region_signal_type` *(A1 §1.8)* | 해당 archetype 허용집합 중 1. `UTILITY_ENTRY`는 채택 전 `CODEBOOK_PENDING` |

---

## 4. Business Domain × Interaction Archetype 은 1:1이 아니다

### 4.1 비대각 예시 (규칙 설명용, 매핑 판정 아님 — §0.5)

| id | domain | archetype | 왜 이렇게 갈리는가 |
|---|---|---|---|
| **D1** | `PORTAL_SEARCH` | `CONTENT_OPEN` | 관문 서비스이지만 랜딩의 대표기능이 뉴스면 기사 열기이면 행위 구조는 콘텐츠 열기다 |
| **D2** | `NEWS_CONTENT` | `QUERY` | 언론사 서비스이지만 랜딩 대표기능이 기사 검색 제출이면 행위 구조는 질의 제출이다 |
| **D3** | `SHOPPING_COMMERCE` | `FINANCIAL_ACTION_ENTRY` | 커머스이지만 대표기능이 결제·페이 진입이면 행위 구조는 금융 진입이다 |
| **D4** | `UTILITY_OTHER` | `CONTENT_OPEN` | 사진·파일 관리 도구에서 대표기능이 항목 1건 열기이면 목록→개별 콘텐츠 소비 구조다 (§2.9.6 경계 ③) |
| **D5** | `UTILITY_OTHER` | `QUERY` | 사전·번역·조회 도구에서 대표기능이 검색어 제출이면 `QUERY`다 |
| **D6** | `FINANCE_PAYMENT` | `UTILITY_ENTRY` | 은행 서비스이지만 로그인 없이 쓰는 공개 환율·금리 **조회 도구**가 대표기능이면 금융 처리 진입이 아니다 |
| **D7** | `MAP_MOBILITY` | `ITEM_DETAIL` | 모빌리티 서비스이지만 대표기능이 예약 대상(좌석·차량) 1건 상세 확인이면 상세 확인 구조다 |
| **D8** | `SOCIAL_COMMUNICATION` | `ITEM_DETAIL` | 중고거래 커뮤니티에서 대표기능이 거래 게시물 상세 확인이면 상품 상세 구조와 같다 |
| **D9** | `CONTENT_VIDEO` | `COMMUNICATION_ENTRY` | 영상 플랫폼이지만 대표기능이 커뮤니티 탭 진입이면 교환 공간 진입 구조다 |
| **D10** | `SHOPPING_COMMERCE` | `PLACE_LOOKUP` | 오프라인 유통 브랜드에서 대표기능이 점포 찾기이면 장소 탐색 구조다 |

### 4.2 대각(전형) 대응은 규범이 아니라 **경향**이다

| domain | 전형 archetype | 단, 반증 예 |
|---|---|---|
| `PORTAL_SEARCH` | `QUERY` | D1 |
| `CONTENT_VIDEO` | `CONTENT_OPEN` | D9 |
| `NEWS_CONTENT` | `CONTENT_OPEN` | D2 |
| `SHOPPING_COMMERCE` | `ITEM_DETAIL` | D3, D10 |
| `MAP_MOBILITY` | `PLACE_LOOKUP` | D7 |
| `FINANCE_PAYMENT` | `FINANCIAL_ACTION_ENTRY` | D6 |
| `SOCIAL_COMMUNICATION` | `COMMUNICATION_ENTRY` | D8 |
| `UTILITY_OTHER` | `UTILITY_ENTRY` | D4, D5 |

**규칙 XT-1.** 전형 대응을 **기본값으로 자동 채우지 않는다.** archetype은 항상 AR-2(행위 구조)로 독립 판정한다.
전형표는 판정 결과의 **사후 점검용**이며, 비대각이 나왔다고 그것을 오류로 간주하지 않는다.

**규칙 XT-2.** domain × archetype 교차표는 `00` §11 기술통계의 `domain/archetype 분포`로 보고한다.
셀 빈도가 낮다고 archetype을 병합하지 않는다 — 병합은 `ExcessDepth` 기준선을 바꾸는 행위다.

---

## 5. 이 코드북을 읽고 나서 하지 말 것

- `business_domain`으로 depth를 비교하는 것 (BD-USE-2·BD-USE-3).
- 전형 대응표(§4.2)를 자동 채움 규칙으로 쓰는 것 (XT-1).
- `UTILITY_ENTRY`의 U-1 endpoint를 감사 채택 전에 `FROZEN`으로 쓰는 것 (FRZ-4, `A2` P-2).
- gate가 endpoint인 archetype에서 gate를 **통과**하는 것 (GATE-2 = `A2` 규칙 E-7). 기록값만 달라질 뿐 종료 시점은 같다.
- `COMMUNICATION_ENTRY`의 **본인인증 gate**를 endpoint로 승격시키는 것 (`A2` 규칙 E-6a) `[SHADOW 재정합]`.
- gate 종류 판별 규칙 없이 gate를 endpoint로 승격시키는 것 (GATE-4 · Q-9) `[SHADOW 재정합]`.
- `ITEM_DETAIL`의 「핵심 상품정보」 조작화(a·b·c)를 **품질 임계값**으로 읽는 것 — 관측 판정 규칙이다(`A1` §0.4).
- `MPFED = 0`을 "진입이 쉽다"로 점수화하는 것 (`A2` 규칙 D-4).
- 모호한 사례를 `UTILITY_OTHER`/`UTILITY_ENTRY`로 밀어 abstain을 회피하는 것 (AB-2).
- 접근성·인증 결과를 본 뒤 매핑을 고치는 것 (FRZ-3).
