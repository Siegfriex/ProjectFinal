# RQ-D14 — frame validity: 수집된 target URL 의 정체

- **hypothesis_id** `H-D14-COLLECTED-URL-IDENTITY`
- **marker/rule version** `D14_MARKER_v1` · **seed** `20260827`
- **plane** D (NON_CANONICAL) · **claim_kind** ANALYSIS · **split** none
- **code** `tools/rq_d14_frame_validity.py`
- **result** `results/RQ_D14_frame_validity.json`
- **figures** `figures/RQ_D14_identity_by_archetype.png`, `RQ_D14_triangulation.png`, `RQ_D14_marker_vs_control.png`

---

## 1. RQ

E001 이 수집한 **56개 web target 의 URL 은 그 서비스의 대표기능(archetype) 면인가,
아니면 기업/브랜드/앱설치/제품소개 랜딩인가?**

## 2. 왜 중요한가

D-RF-001-A (rule DT) worker 가 자기 limitation 으로 다음을 보고했다 (원문 요지):

> `prior_archetype` 은 서비스(앱)의 대표기능인데 수집 URL 상당수가 그 서비스의
> 기업/브랜드/앱설치 유도 랜딩이다 (GS25→gsretail, 티맵/카카오T→기업사이트,
> 네이버지도→navercorp, Instagram/TikTok→앱 인터스티셜, Chrome→제품 소개면).
> 이런 면에는 어떤 archetype 의 region/endpoint 도 없다. **DT 결함이 아니라 Stage 0/1 의
> target URL 정의 문제이며 DT 를 고쳐도 해결되지 않는다.**

이것은 **주장이지 사실이 아니었다.** 만약 사실이면 mapping/endpoint detector 를 아무리
고쳐도 회복되지 않으므로 수정 대상이 Stage 0(모집단·URL 정의)으로 옮겨간다.
만약 과일반화면 Stage 0 을 흔들 근거가 없다. 이 RQ 는 그 주장을 raw evidence 로
독립 재현하고 정량화한다.

**RF001-A 의 주장은 두 명제의 연언이다.**
- **P1** 수집 URL 상당수가 기업/브랜드/앱설치/제품소개 랜딩이다.
- **P2** 그런 면에는 어떤 archetype 의 region/endpoint 도 (원리적으로) 없다.

이 구분이 결론의 핵심이다.

## 3. 입력 · 분석단위 · N

| 파일 | 행 | 역할 | sha256 (앞 16) |
|---|---|---|---|
| `results/D_OBSERVATION_TABLE_v2.csv` | 66 (in_mart==1 → 56) | 구조 DOM/probe 지표 | `c39c10f09f7a6a76` |
| `results/D_TEXT_CORPUS_v2.csv` | 56 | surface 별 텍스트 | `bf6bb772faa45541` |
| `results/RF001_A_rule_dt.json` | leaves 56 | **상호참조 전용, 정답 아님** | `c27078736813e74f` |
| `results/RQ_D13_duplicate_vector.json` | — | 퇴화 캡처 4건 목록 | `70d6375cb7dc5714` |

- **분석단위**: web target (`wtg`), `in_mart==1`
- **N**: n_expected 59 / **n_observed 56** (mart 진입 실패 3건은 이 RQ 의 관측 대상이 아니다)
- raw `dom.html` 은 재파싱하지 않았다. 위 두 CSV 만 소비한다.

### missing N

| 항목 | 값 |
|---|---|
| `prior_url` 결측 → `probe_url` 대체 | 2 (G마켓, 네이버) |
| URL 완전 결측 | 0 |
| `search_inputs_n` null (probe 부재) | 2 |
| text corpus 에 없는 target | 0 |

**입력 방화벽 — 아래는 전부 "열지 않았다" 목록이다.**

- 열지 않았다: `**/control/**` · `**/control/label/**`
- 열지 않았다: `LABEL_SPLIT_FROZEN.json` · `RAW_L*.jsonl` · `PACKET_L*`
- 열지 않았다: `*_OVERLAP*` · `PRECEDENCE_CONTESTED*` · `HOLDOUT_*` · `CALIBRATION_FOR_B*`

gold label 을 생산하지도 소비하지도 않았다. 실제 웹사이트(REAL_TARGET)에 접속하지 않았고
네트워크 접근도 없었다. 입력은 위 §3 표의 로컬 artifact 4개뿐이다.

---

## 4. 방법 — 세 갈래 독립 증거 삼각검증

한 신호만으로 판정하지 않는다. 세 증거가 각각 `FUNCTIONAL` / `CORPORATE_OR_APP` /
`UNDETERMINED` 에 1표씩 던진다.

| 증거 | 무엇을 보는가 | 사용 surface |
|---|---|---|
| **(a) host–service 정합** | URL 의 host 가 서비스 브랜드인가 모회사/그룹/통합플랫폼/지원센터인가 | `prior_url` (결측 시 `probe_url`) |
| **(b) 페이지 정체 marker** | 페이지가 스스로를 무엇이라 소개하는가 | title, meta_description, headings, landmarks, nav_links |
| **(c) 기능 컨트롤 부재** | 실제 조작 대상이 있는가 | buttons, aria_labels, placeholders, form_labels, input_names, card_texts + DOM count |

**결합 규칙 (보수적, 모순 허용 안 함)**

```
CORPORATE 표 >= 2 AND FUNCTIONAL 표 == 0  ->  CORPORATE_OR_APP_LANDING
FUNCTIONAL 표 >= 2 AND CORPORATE 표 == 0  ->  FUNCTIONAL_LANDING
그 외 (모순 포함)                          ->  UNDETERMINED
```

억지로 2분류하지 않는다. **UNDETERMINED 비율 자체가 결과다.**

### 4.1 (a) host–service 정합 규칙 — 전문

**작성 규칙 (반순환성)**

- **R-A1** alias 는 서비스명에서만 유도 (관측 URL 역유도 금지)
- **R-A2** service vs corporate alias 분리
- **R-A3** 다어절은 정순+역순 결합 생성
- **R-A4** 길이 3 미만 alias 폐기
- **R-A5** 약어 도메인은 유래 명시 후 인정

R-A1 이 핵심이다. alias 를 관측된 URL 에서 역으로 가져오면 항상 match 가 나서 규칙이
무의미해진다. alias 는 **서비스 이름에서만** 유도했다.

**판정 규칙**

```
host_norm = hostname.lower() 에서 영숫자 아닌 문자 제거
            (www.gsretail.com -> "wwwgsretailcom")
host_norm 안에서 service_alias / corporate_alias 를 substring 검색
가장 긴 매칭 alias 가 이긴다 (longest-alias-wins)
  이긴 alias 가 service   -> SERVICE_HOST
  이긴 alias 가 corporate -> CORPORATE_HOST
  아무것도 안 맞음         -> UNRELATED_HOST
  URL 자체가 없음          -> HOST_UNKNOWN
```

longest-alias-wins 가 필요한 이유: `tmapmobility.com` 은 `tmap`(service, 4자) 과
`tmapmobility`(corporate, 12자) 를 **둘 다** 포함한다. 더 구체적인 법인명이 이겨야 한다.

부수 관측으로 `path_names_service` (URL path/query 가 서비스 alias 를 담고 있는가) 를 기록한다.
이는 "기업 사이트 안의 그 서비스 소개 하위페이지" 를 식별한다.

**alias table 전문 (56 services)** — assertion type `DEFINITION`

| prior_service | service_alias | corporate_alias | note |
|---|---|---|---|
| 쿠팡이츠 | coupangeats | coupang |  |
| 삼성카드 | samsungcard | samsunggroup |  |
| GS25 | gs25 | gsretail | GS25 운영사 = GS리테일 |
| 코스트코 | costco | — |  |
| TikTok | tiktok | bytedance |  |
| 티맵 | tmap | tmapmobility, sktelecom | TMAP 운영사 = 티맵모빌리티 |
| 신한 SOL뱅크 | shinhansol, solbank, shinhanbank, shinhan | shinhanfinancialgroup | 은행 본체 도메인은 서비스 면으로 본다 |
| 밴드 | band | navercorp |  |
| 세븐일레븐 | 7eleven, seveneleven | koreaseven |  |
| 다음 | daum | kakaocorp |  |
| KB Pay | kbpay | kbcard, kookmincard, kbfg | KB Pay 운영사 = KB국민카드 |
| 카카오T | kakaot | kakaomobility, kakaocorp | 카카오T 운영사 = 카카오모빌리티 |
| 디바이스 케어 | devicecare | samsungsvc, samsungservice | 삼성 고객지원센터 |
| 롯데백화점 | lottedepartment, ellotte | lotteon, lotteshopping | 롯데 통합 이커머스 플랫폼 |
| 마켓컬리 | kurly, marketkurly | — |  |
| Netflix | netflix | — |  |
| V3 Mobile Plus | v3mobileplus, v3mobile, v3mp | ahnlab | R-A4 로 'v3' 탈락 |
| 다이소 | daiso | — |  |
| CJ온스타일 | cjonstyle | cjgroup |  |
| 홈앤쇼핑 | hnsmall, homeandshopping | — | R-A5: Home&Shopping -> HNS mall |
| 카카오톡 | kakaotalk | kakaocorp, kakao |  |
| 네이버 | naver | navercorp |  |
| Chrome | chrome | google | Chrome 제조사 = Google |
| 현대카드 | hyundaicard | hyundaimotorgroup |  |
| emart24 | emart24 | emart, shinsegae |  |
| 캐시워크 | cashwalk | — |  |
| 메가커피 | megacoffee, mgccoffee | — |  |
| 롯데하이마트 | himart, lottehimart | lotteshopping |  |
| 신세계백화점 | shinsegae, shinsegaedepartment | shinsegaegroup |  |
| 홈플러스 | homeplus | — |  |
| 탑마트 | topmart | seowon, seowonyutong | 탑마트 운영사 = 서원유통 |
| 토스 | toss | vivarepublica |  |
| 농협하나로마트 | hanaro, nhhanaro | nonghyup |  |
| Instagram | instagram | meta, facebook |  |
| 롯데홈쇼핑 | lottehomeshopping, lotteimall | lotteshopping |  |
| 하나은행 | hanabank, hana | hanafinancialgroup |  |
| NH스마트뱅킹 | nhsmartbanking | nonghyup, nhbank | 앱 브랜드 != 은행 본체 도메인 |
| 에이닷 전화 | adot, adotcall | sktelecom, sktel |  |
| 배달의민족 | baemin, baedalminjok | woowabrothers |  |
| KB스타뱅킹 | kbstar, starbanking, kbstarbanking | kbfg, kookminbank |  |
| 내 파일 | myfiles | samsungsvc, samsungservice | 삼성 고객지원센터 |
| 네이버지도 | navermap, mapnaver | navercorp, naver | R-A3 역순결합 적용 |
| YouTube | youtube | google |  |
| 당근 | daangn, karrot | — |  |
| 11번가 | 11st | sktelecom |  |
| 컴포즈커피 | composecoffee | — |  |
| 이마트 | emart | shinsegae |  |
| 롯데마트 | lottemart | lotteshopping |  |
| NS홈쇼핑 | nsmall, nshomeshopping | harimgroup |  |
| Google | google | alphabet |  |
| 현대백화점 | thehyundai, hyundaidepartment | ehyundai, hyundaidepartmentgroup | R-A3 |
| 모니모 | monimo | samsungfinancialnetworks |  |
| CU | — | bgfretail, bgf | R-A4 로 'cu' 탈락 -> service alias 없음 |
| 카카오맵 | kakaomap, mapkakao | kakaocorp | R-A3 역순결합 적용 |
| G마켓 | gmarket | ebaykorea, shinsegae |  |
| NH콕뱅크 | nhcokbank, cokbank | nonghyup, nhbank |  |

### 4.2 (b) 페이지 정체 marker 사전 — 전문

매칭 규칙: 텍스트는 NFKC 정규화 + lowercase + 공백 압축. **라틴 term 은 단어경계 매칭**
(`(?<![a-z0-9])term(?![a-z0-9])`), **한글 term 은 공백 제거 후 substring 매칭**.
카운트는 **distinct term 수** (같은 term 이 여러 번 나와도 1).

**`DICT_CORPORATE`** (73 terms)

```
회사소개, 기업소개, 회사개요, 기업정보, 회사 정보, CEO 인사말
CEO인사말, 대표이사, 경영이념, 기업이념, 가치체계, 기업 연혁
회사 연혁, 연혁, 수상 이력, 비전, 미션, CI/BI
기업 CI, BI 소개, 브랜드스토리, 브랜드 스토리, 브랜드 이야기, 브랜드소개
사업영역, 사업 영역, 사업분야, 투자정보, IR, 기업지배구조
지배구조, 경영성과, 공시정보, 전자공시, 주주, 재무정보
실적, 지속가능경영, 사회적 책임, 사회공헌, 정도경영, 윤리경영
준법경영, ESG, 환경경영, 보도자료, 뉴스룸, 미디어
홍보센터, 채용, 인재채용, 채용문의, 인재상, 공지사항
오시는 길, 찾아오시는 길, 고객헌장, 협력사, 제휴문의, about us
company, corporate, investor relations, investors, careers, recruit
press, newsroom, sustainability, governance, our story, brand story
esg
```

**`DICT_APP_INSTALL`** (34 terms)

```
앱에서 보기, 앱으로 보기, 앱에서 열기, 앱으로 열기, 앱에서 계속, 앱 설치
앱설치, 앱 다운로드, 앱다운로드, 앱 다운받기, 설치하기, 다운로드하기
지금 설치, App Store, 앱스토어, 앱 스토어, Google Play, 구글 플레이
플레이 스토어, 플레이스토어, Play 스토어, 원스토어, 스마트배너, 앱으로 계속
open in app, get the app, download the app, download on the app store, install app, open app
continue in app, intent://, itms-apps, market://
```

**`DICT_PRODUCT_INTRO`** (30 terms)

```
서비스 소개, 서비스소개, 기능 소개, 기능소개, 주요 기능, 주요기능
이용안내, 이용 안내, 이용방법, 이용 방법, 사용방법, 사용 방법
사용법, 설정 방법, 기능 사용방법, 더 알아보기, 자세히 알아보기, 자세히 보기
제품 소개, 제품소개, 서비스 안내, 안내 페이지, learn more, features
overview, how it works, how to use, product tour, what is, guide
```


**(b) 투표 규칙** (동결 임계값)

```
corp_distinct >= 3  OR  app_distinct >= 2  OR  intro_distinct >= 3
    -> CORPORATE_OR_APP
corp_distinct == 0 AND app_distinct == 0 AND intro_distinct <= 1
    -> FUNCTIONAL
그 외 -> UNDETERMINED
```

### 4.3 (c) 기능 affordance 사전 — 전문

**`DICT_SEARCH_AFFORDANCE`** (11 terms)

```
검색, 검색어, 통합검색, 상품검색, 찾기, 검색하기
search, searchbox, query, keyword, find
```

**`DICT_TRANSACTION_AFFORDANCE`** (58 terms)

```
장바구니, 담기, 바로구매, 구매하기, 구매, 주문하기
주문, 결제하기, 결제, 배송, 배달주문, 예약하기
예약, 찜하기, 쿠폰받기, 할인, 이체, 송금
잔액, 계좌조회, 거래내역, 출금, 입금, 충전하기
환전, 납부, 길찾기, 경로, 내비게이션, 출발
도착, 호출하기, 재생, 시청하기, 글쓰기, 글 작성
게시, 보내기, 채팅하기, add to cart, cart, checkout
buy now, buy, order now, pay, payment, transfer
balance, book now, reserve, directions, navigate, play
watch, post, compose, send message
```


> **로그인/login 은 의도적으로 제외했다.** SSOT S6 의 `E_M` 주석("실제 login gate 도달.
> 로그인 버튼 존재만으로는 불가")과 정합을 맞추기 위해서다.

**(c) 투표 규칙** (동결 임계값)

```
control_score = [search_inputs_n>0 or 검색어휘 발화]
              + [dom_input_n>0]
              + [거래어휘 발화]
              + [card 항목수 >= 3]

dom_body_empty==1 or dom_element_n < 100  -> CONTROL_UNOBSERVABLE  (H4 guard) -> UNDETERMINED
control_score >= 3                            -> CONTROL_PRESENT      -> FUNCTIONAL
control_score <= 1                            -> CONTROL_ABSENT       -> CORPORATE_OR_APP
그 외 (== 2)                                     -> CONTROL_WEAK         -> UNDETERMINED
```

`CONTROL_UNOBSERVABLE` 분기가 **H4 를 구조적으로 격리한다**: 빈 캡처는 "기능 없음" 이 아니라
"관측 불가" 로 흐른다.

---

## 5. 삼각검증 교차표 — assertion type `OBSERVATION`

| (a) host | (b) marker | (c) control | n |
|---|---|---|---|
| FUNCTIONAL | FUNCTIONAL | FUNCTIONAL | 17 |
| FUNCTIONAL | FUNCTIONAL | CORPORATE_OR_APP | 5 |
| FUNCTIONAL | FUNCTIONAL | UNDETERMINED | 5 |
| FUNCTIONAL | UNDETERMINED | FUNCTIONAL | 5 |
| CORPORATE_OR_APP | CORPORATE_OR_APP | FUNCTIONAL | 4 |
| FUNCTIONAL | CORPORATE_OR_APP | FUNCTIONAL | 4 |
| CORPORATE_OR_APP | UNDETERMINED | FUNCTIONAL | 3 |
| FUNCTIONAL | CORPORATE_OR_APP | CORPORATE_OR_APP | 2 |
| CORPORATE_OR_APP | CORPORATE_OR_APP | UNDETERMINED | 2 |
| CORPORATE_OR_APP | FUNCTIONAL | FUNCTIONAL | 2 |
| CORPORATE_OR_APP | FUNCTIONAL | CORPORATE_OR_APP | 2 |
| CORPORATE_OR_APP | FUNCTIONAL | UNDETERMINED | 2 |
| CORPORATE_OR_APP | UNDETERMINED | CORPORATE_OR_APP | 1 |
| FUNCTIONAL | CORPORATE_OR_APP | UNDETERMINED | 1 |
| FUNCTIONAL | UNDETERMINED | UNDETERMINED | 1 |

- **세 증거 만장일치 FUNCTIONAL: 17/56 targets**
  (삼성카드, 코스트코, 세븐일레븐, 다음, 마켓컬리, Netflix, CJ온스타일, 홈앤쇼핑, 네이버, 메가커피, 신세계백화점, 하나은행, YouTube, 당근, 11번가, 롯데마트, Google)
- **세 증거 만장일치 CORPORATE_OR_APP: 0/56 targets**

**쌍별 일치율** (둘 다 UNDETERMINED 아닌 경우만 분모)

| 쌍 | 둘 다 결정적 | 일치 | 일치율 |
|---|---|---|---|
| (a)–(b) | 46 | 33 | 0.717 |
| (a)–(c) | 45 | 29 | 0.644 |
| (b)–(c) | 36 | 21 | 0.583 |

**세 증거는 서로 잘 맞지 않는다.** 이것이 이 RQ 의 첫 번째 실질 결과다.
특히 (b)–(c) 는 36건 중 21건만 일치(58.3%)한다.

---

## 6. 3분류 결과 — assertion type `OBSERVATION`

**퇴화 캡처 포함 (전체 56 targets)**

| class | n / 56 | rate |
|---|---|---|
| FUNCTIONAL_LANDING | 27/56 | 0.482 |
| UNDETERMINED | 26/56 | 0.464 |
| CORPORATE_OR_APP_LANDING | 3/56 | 0.054 (Wilson95 [0.018, 0.146]) |

**퇴화 캡처 4건 제외 (52 targets)**

| class | n / 52 | rate |
|---|---|---|
| FUNCTIONAL_LANDING | 25/52 | 0.481 |
| UNDETERMINED | 24/52 | 0.462 |
| CORPORATE_OR_APP_LANDING | 3/52 | 0.058 (Wilson95 [0.020, 0.156]) |

**증거별 단독 분포**

| 증거 | 분포 |
|---|---|
| (a) host | SERVICE_HOST 40/56 · CORPORATE_HOST 16/56 · UNRELATED_HOST 0/56 |
| (b) marker | FUNCTIONAL 33 · CORPORATE_OR_APP 13 · UNDETERMINED 10 |
| (c) control | CONTROL_PRESENT 35 · CONTROL_WEAK 7 · CONTROL_ABSENT 10 · CONTROL_UNOBSERVABLE 4 |

### 6.1 P1 은 지지된다 — host 층위 (증거 (a) 단독)

**16/56 targets (28.6%, Wilson95 [0.184, 0.415]) 의 URL host 가
서비스 브랜드가 아니라 모회사/그룹/통합플랫폼/고객지원센터 도메인이다.**
퇴화 제외 시 14/52.
16건 전부 `CORPORATE_HOST` 였고 `UNRELATED_HOST` 는 0건 — 즉 alias table 이 host 를 놓쳐서
생긴 위양성이 아니다.

이 중 5건은 URL path 가 서비스명을 담고 있다
(기업 사이트 **안의** 서비스 소개 하위페이지):
`https://www.gsretail.com/brand/gs25`, `https://www.kakaomobility.com/service-kakaot`, `https://www.lotteon.com:443/p/display/main/ellotte?mall_no=2`, `https://mplweb.ahnlab.com/mplweb/v3mp/main_android.do`, `https://www.google.com/chrome/`

### 6.2 P2 는 지지되지 않는다 — control 층위

corporate/unrelated host 16건 중
**CONTROL_PRESENT 가 9건, CONTROL_ABSENT 는 3건뿐이다.**
"이런 면에는 어떤 archetype 의 region/endpoint 도 없다" 는 관측으로 뒷받침되지 않는다.

---

## 7. archetype 별 — assertion type `ANALYSIS`

### 7.1 삼각검증 3분류 기준

| archetype | n | CORPORATE_OR_APP_LANDING | rate | Wilson 95% CI | n<=5 |
|---|---|---|---|---|---|
| ITEM_DETAIL | 26 | 2 | 0.077 | [0.021, 0.241] |  |
| FINANCIAL_ACTION_ENTRY | 10 | 0 | 0.000 | [0.000, 0.278] |  |
| UTILITY_ENTRY | 5 | 0 | 0.000 | [0.000, 0.434] | ⚠️ |
| COMMUNICATION_ENTRY | 4 | 0 | 0.000 | [0.000, 0.490] | ⚠️ |
| PLACE_LOOKUP | 4 | 1 | 0.250 | [0.046, 0.699] | ⚠️ |
| QUERY | 4 | 0 | 0.000 | [0.000, 0.490] | ⚠️ |
| CONTENT_OPEN | 3 | 0 | 0.000 | [0.000, 0.561] | ⚠️ |

### 7.2 host 층위 (증거 (a) 단독) — 신호가 훨씬 뚜렷하다

| archetype | n | corporate/unrelated host | rate | Wilson 95% CI | n<=5 |
|---|---|---|---|---|---|
| ITEM_DETAIL | 26 | 4 | 0.154 | [0.061, 0.335] |  |
| FINANCIAL_ACTION_ENTRY | 10 | 3 | 0.300 | [0.108, 0.603] |  |
| UTILITY_ENTRY | 5 | 4 | 0.800 | [0.376, 0.964] | ⚠️ |
| COMMUNICATION_ENTRY | 4 | 1 | 0.250 | [0.046, 0.699] | ⚠️ |
| PLACE_LOOKUP | 4 | 3 | 0.750 | [0.301, 0.954] | ⚠️ |
| QUERY | 4 | 1 | 0.250 | [0.046, 0.699] | ⚠️ |
| CONTENT_OPEN | 3 | 0 | 0.000 | [0.000, 0.561] | ⚠️ |

- **UTILITY_ENTRY 4/5** 와
  **PLACE_LOOKUP 3/4** 가 가장 높다.
  **둘 다 n<=5 이므로 Wilson CI 가 각각 [0.376, 0.964], [0.301, 0.954] 로 극도로 넓다. 과해석 금지.**
  가리키는 방향만 기록한다.
- **RF001-A 가 특히 의심한 QUERY 4건은 실제로는 1/4 에 그친다** (Chrome 뿐).
  Google·네이버·다음은 모두 SERVICE_HOST 이고 삼각검증에서 FUNCTIONAL_LANDING 으로 판정됐다.
  **QUERY 에 대한 RF001-A 의 의심은 이 증거로는 지지되지 않는다.**
- ITEM_DETAIL (n=26, 유일하게 n>=20 인 class) 은 4/26 = 15.4%
  로 전체 평균보다 **낮다**.

---

## 8. H4 배제 논증 — assertion type `ANALYSIS`

**H4 = "기능이 없어 보이는 것이 페이지 정체 때문이 아니라 수집 실패/빈 캡처 때문이다"**

RQ-D13 이 확인한 퇴화 캡처 4건 (`computed_css` 3바이트, `dom_body_empty=1`):
NH스마트뱅킹, NH콕뱅크, 롯데하이마트, 신한 SOL뱅크.

| 검사 | 결과 |
|---|---|
| 퇴화 4건이 받은 판정 | {"FUNCTIONAL_LANDING": 2, "UNDETERMINED": 2} — **CORPORATE_OR_APP_LANDING 0건** |
| `CONTROL_UNOBSERVABLE` 로 격리된 target | 4건, 퇴화 4건과 **정확히 일치** |
| CORPORATE 판정 (전체 56) | 3 |
| CORPORATE 판정 (퇴화 제외 52) | 3 — **변하지 않는다** |
| CORPORATE 판정 중 `dom_body_empty==0` | 3/3 — **전부 정상 캡처** |
| CORPORATE 판정의 최소 `dom_element_n` | 567 (빈 페이지가 아니다) |
| CORPORATE 판정의 최소 identity 텍스트 길이 | 405자 |
| host 층위 결론 (퇴화 제외) | 14/52 — 유지 |

**H4 는 이 결과의 유일한 설명이 될 수 없다 (REFUTED as sole explanation).**
퇴화 캡처는 CORPORATE 판정에 **한 건도 기여하지 않았고**, 4건을 제거해도 host 층위와
삼각검증 결론이 모두 유지된다. 다만 H4 는 **UNDETERMINED 4건에 대해서는 유효한 설명**이며,
그 4건은 "정체 불명" 이 아니라 "관측 불가" 로 분류돼야 한다.

---

## 9. RF001-A 와의 수렴 — assertion type `ANALYSIS`

> RF001-A 의 판정은 **정답이 아니라 독립 상호참조**다. 수렴은 증거이지 검증이 아니다.

### 9.1 abstain 대조

RF001-A rule DT 의 abstain (`AMBIGUOUS_UNRESOLVED__*`) = **40/56**, 매핑 성공 = 16/56.

| | D14 CORPORATE | D14 FUNCTIONAL | D14 UNDETERMINED |
|---|---|---|---|
| RF001-A abstain (40) | 3 | 16 | 21 |
| RF001-A mapped (16) | 0 | 11 | 5 |

- **방향은 완전히 수렴한다**: D14 가 CORPORATE 로 판정한 3건은 **100% 전부** RF001-A abstain 안에 있고,
  RF001-A 가 매핑에 성공한 16건 중 D14 CORPORATE 는 **0건**이다. 모순이 없다.
- **그러나 설명력은 작다**: abstain 40건 중 CORPORATE 로 설명되는 것은 **3건 = 7.5%** 에 불과하다.
  abstain 의 16건은 D14 가 **기능 랜딩**으로 판정한 target 이다.
  **RF001-A 의 abstain 대부분은 URL 정체로 설명되지 않는다.**

### 9.2 앱 인터스티셜 — 두 검출기가 서로 다른 것을 재고 있다

| | services |
|---|---|
| RF001-A `app_interstitial=1` (3) | Instagram, TikTok, 에이닷 전화 |
| D14 `(b)` 앱설치 marker 발화 (5) | 롯데백화점, 배달의민족, 캐시워크, 쿠팡이츠, 토스 |

**두 집합의 교집합은 0 이다.** D14 가 잡은 5건은 정상 기능 사이트의 "앱 다운로드" 푸터 배너이고,
RF001-A 가 잡은 3건은 D14 텍스트 사전이 발화하지 않는 구조적 인터스티셜이다.
`intent://` `itms-apps` `market://` 같은 **스킴 marker 는 text corpus 에 href 가 없어 원리적으로 관측 불가**했다.
→ D14 의 앱설치 검출은 **과소계수**이며, 이 축에서는 RF001-A 쪽 신호가 더 신뢰할 만하다.

### 9.3 RF001-A 가 이름을 댄 7건 — 직접 검증

| service | RF001-A 주장 | URL | D14 (a) host | D14 (c) control | D14 3분류 | 주장 확인 |
|---|---|---|---|---|---|---|
| GS25 | 기업 도메인 gsretail 로 갔다 | `https://www.gsretail.com/brand/gs25` | CORPORATE_HOST (`gsretail`) | CONTROL_WEAK | CORPORATE_OR_APP_LANDING | ✅ 확인 |
| 티맵 | 기업사이트로 갔다 | `https://www.tmapmobility.com/` | CORPORATE_HOST (`tmapmobility`) | CONTROL_PRESENT | UNDETERMINED | ✅ 확인 |
| 카카오T | 기업사이트로 갔다 | `https://www.kakaomobility.com/service-kakaot` | CORPORATE_HOST (`kakaomobility`) | CONTROL_ABSENT | CORPORATE_OR_APP_LANDING | ✅ 확인 |
| 네이버지도 | navercorp 로 갔다 | `https://www.navercorp.com/service/map` | CORPORATE_HOST (`navercorp`) | CONTROL_PRESENT | UNDETERMINED | ✅ 확인 |
| Instagram | 앱 인터스티셜 | `https://www.instagram.com/` | SERVICE_HOST (`instagram`) | CONTROL_ABSENT | UNDETERMINED | 앱marker 미관측 |
| TikTok | 앱 인터스티셜 | `https://www.tiktok.com/` | SERVICE_HOST (`tiktok`) | CONTROL_ABSENT | UNDETERMINED | 앱marker 미관측 |
| Chrome | 제품 소개면 | `https://www.google.com/chrome/` | CORPORATE_HOST (`google`) | CONTROL_PRESENT | UNDETERMINED | ✅ 확인 |

**host 주장 5건(GS25·티맵·카카오T·네이버지도·Chrome)은 전부 문자 그대로 사실이다.**
앱 인터스티셜 주장 2건(Instagram·TikTok)은 host 는 정상 서비스 도메인이고
D14 텍스트 marker 로는 재현되지 않았으나, 둘 다 `CONTROL_ABSENT` 라는 점에서 정체는 다르지만
**기능 컨트롤 부재라는 관측은 일치**한다.

---

## 10. 반례 전수 — assertion type `OBSERVATION`

### (i) 기업/모회사 도메인인데 기능 컨트롤이 관측되는 사이트 — 9/16 corporate hosts

| service | url | matched corporate alias | control_score | D14 3분류 | RF001-A leaf |
|---|---|---|---|---|---|
| 티맵 | `https://www.tmapmobility.com/` | `tmapmobility` | 3 | UNDETERMINED | AMBIGUOUS_UNRESOLVED__NO_STRONG_CANDIDATE |
| KB Pay | `https://mbiz.kbcard.com/CXEHMSVCD0012.cms` | `kbcard` | 3 | UNDETERMINED | AMBIGUOUS_UNRESOLVED__NO_STRONG_CANDIDATE |
| 디바이스 케어 | `https://www.samsungsvc.co.kr/solution/42404` | `samsungsvc` | 4 | UNDETERMINED | AMBIGUOUS_UNRESOLVED__NO_STRONG_CANDIDATE |
| 롯데백화점 | `https://www.lotteon.com:443/p/display/main/ellotte?mall_no=2` | `lotteon` | 3 | UNDETERMINED | AMBIGUOUS_UNRESOLVED__NO_STRONG_CANDIDATE |
| 카카오톡 | `https://www.kakaocorp.com/page/detail/10810?lang=ENG` | `kakaocorp` | 3 | UNDETERMINED | UNDETERMINED_URL_EVIDENCE |
| Chrome | `https://www.google.com/chrome/` | `google` | 3 | UNDETERMINED | AMBIGUOUS_UNRESOLVED__NO_STRONG_CANDIDATE |
| 내 파일 | `https://www.samsungsvc.co.kr/solution/164886` | `samsungsvc` | 4 | UNDETERMINED | AMBIGUOUS_UNRESOLVED__NO_STRONG_CANDIDATE |
| 네이버지도 | `https://www.navercorp.com/service/map` | `navercorp` | 4 | UNDETERMINED | PLACE_LOOKUP |
| CU | `https://cu.bgfretail.com/` | `bgfretail` | 4 | UNDETERMINED | AMBIGUOUS_UNRESOLVED__NO_STRONG_CANDIDATE |

> **가장 강한 반례: 네이버지도 `https://www.navercorp.com/service/map`.**
> RF001-A 가 frame 결함의 대표 사례로 직접 지목한 URL 인데, `control_score 4/4`
> (검색·입력·거래어휘·카드 전부 발화)이고 **RF001-A 자신의 rule DT 가 이 target 을
> `PLACE_LOOKUP` 으로 매핑에 성공했다** (abstain 이 아니다). 이 한 건이
> "기업 도메인이면 archetype region/endpoint 가 없다" 를 직접 반증한다.
>
> **두 번째 반례: 롯데백화점 `https://www.lotteon.com/p/display/main/ellotte`.**
> host 는 롯데의 통합 이커머스 플랫폼(서비스 브랜드 아님)이지만 path 가 서비스면(`ellotte`)을
> 지정하고 있고 control_score 3, 검색 입력 존재. host 불일치가 곧 기능 부재가 아님을 보여준다.

### (ii) 서비스 도메인인데 기능 컨트롤이 관측되지 않는 사이트 — 7/40 service hosts

| service | url | control_score | D14 3분류 | RF001-A leaf |
|---|---|---|---|---|
| 쿠팡이츠 | `https://www.coupangeats.com/` | 1 | UNDETERMINED | AMBIGUOUS_UNRESOLVED__NO_STRONG_CANDIDATE |
| TikTok | `https://www.tiktok.com/` | 1 | UNDETERMINED | AMBIGUOUS_UNRESOLVED__NO_STRONG_CANDIDATE |
| 밴드 | `https://www.band.us/` | 1 | UNDETERMINED | AMBIGUOUS_UNRESOLVED__NO_STRONG_CANDIDATE |
| Instagram | `https://www.instagram.com/` | 0 | UNDETERMINED | AMBIGUOUS_UNRESOLVED__NO_STRONG_CANDIDATE |
| 배달의민족 | `https://baemin.com/` | 0 | UNDETERMINED | AMBIGUOUS_UNRESOLVED__NO_STRONG_CANDIDATE |
| 컴포즈커피 | `https://composecoffee.com/` | 1 | UNDETERMINED | AMBIGUOUS_UNRESOLVED__NO_STRONG_CANDIDATE |
| 모니모 | `https://www.monimo.com/` | 0 | UNDETERMINED | AMBIGUOUS_UNRESOLVED__NO_STRONG_CANDIDATE |

> 이 7건은 RF001-A 의 프레임이 **놓치는** 부류다. host 는 완벽히 정상인데 첫 화면에
> 조작 대상이 관측되지 않는다 (앱 인터스티셜·로그인 월·SPA 미수화 등이 후보이나
> 이 RQ 는 그 원인을 판정하지 않는다). **"URL 을 바꾸면 해결된다" 는 처방이 듣지 않는 집합이다.**

### 교차 반례 (3분류 기준)

- corporate host → FUNCTIONAL_LANDING 판정: 0건
- service host → CORPORATE_OR_APP_LANDING 판정: 0건

보수적 결합 규칙이 모순을 UNDETERMINED 로 흡수하므로 3분류 층위에서는 교차 반례가 0 이다.
반례는 전부 (a)–(c) 불일치 형태로 나타난다.

---

## 11. 민감도

| 변형 | FUNCTIONAL | UNDETERMINED | CORPORATE |
|---|---|---|---|
| `primary_corp3_app2_intro3` | 27 | 26 | 3 |
| `strict_corp5_app3_intro4` | 28 | 25 | 3 |
| `loose_corp2_app1_intro2` | 24 | 29 | 3 |
| `combine_plain_majority_allows_contradiction` | 39 | 6 | 11 |
| `leave_out_a` | 19 | 35 | 2 |
| `leave_out_b` | 26 | 27 | 3 |
| `leave_out_c` | 27 | 23 | 6 |

- **(b) 임계값에 거의 둔감하다.** corp 2/5, app 1/3, intro 2/4 로 흔들어도 CORPORATE 판정은 **3건 고정**이다.
  결론을 만드는 것은 marker 임계값이 아니라 **결합 규칙의 보수성**이다.
- **결합 규칙을 단순 다수결(모순 허용)로 바꾸면 CORPORATE 가 3 → 11 로 뛴다.** 이 차이가
  UNDETERMINED 26건의 정체다: 세 증거가 **서로 반대 방향을 가리키는** 사례들이다.
- **leave-one-evidence-out**: (a) 를 빼면 CORPORATE 3→2, UNDETERMINED 26→35 (증거 (a) 가 정보의 대부분을 지고 있다).
  (c) 를 빼면 CORPORATE 3→6 ((c) 가 CORPORATE 판정을 가장 많이 막고 있다).

> 위 민감도는 **동일 run 내부의 robustness 보고**이며, primary 사전/임계값
> (`D14_MARKER_v1`) 은 결과를 본 뒤 수정하지 않았다. 다른 사전을 primary 로 시험하려면
> 새 hypothesis_id 의 child run 을 만들어야 한다.

---

## 12. 가설별 판정

| 가설 | 판정 | 근거 |
|---|---|---|
| **H1 FRAME_OK** | PARTIALLY_SUPPORTED | 기능 컨트롤이 관측되는 target 이 35/56 로 다수이고 만장일치 FUNCTIONAL 이 17건. 그러나 host 정합이 깨진 target 이 16/56 (28.6%) 로 "소수 사례 과일반화" 라 부를 수준이 아니다. |
| **H2 FRAME_DEFECT** | PARTIALLY_SUPPORTED | **P1 지지** (16/56 corporate host, Wilson95 [0.184,0.415]). **P2 미지지** (그 16건 중 9건이 CONTROL_PRESENT, CONTROL_ABSENT 는 3건). |
| **H3 NOT_SEPARABLE** | PARTIALLY_SUPPORTED | 구분이 원리적으로 불가능하지는 않다 (만장일치 FUNCTIONAL 17건, 만장일치 CORPORATE 0건). 그러나 현재 관측 증거로는 **26/56 = 46.4% 가 미결**이고 (b)–(c) 일치율이 0.583 에 그친다. |
| **H4 CONFOUNDED_BY_CAPTURE** | REFUTED (유일 설명으로서) | 퇴화 4건은 CORPORATE 판정에 0건 기여, 제외해도 3/52 로 불변. 단 UNDETERMINED 4건에 대해서는 유효한 설명이다. |

---

## 13. VERDICT

**`PARTIALLY_SUPPORTED`**

P1(호스트가 기업/모회사/무관 도메인) 16/56 = 28.6% Wilson95 [0.184,0.415] -> 지지. P2(그 면에 기능 컨트롤이 없다) 삼각검증 CORPORATE_OR_APP_LANDING 3/56 = 5.4% Wilson95 [0.018,0.146] -> 미지지. 연언 중 하나만 성립하므로 PARTIALLY_SUPPORTED.

> **사전등록 규칙과의 관계 (전문 공개).**
> 코드에는 삼각검증 CORPORATE 비율만으로 H2 를 판정하는 동결 규칙이 들어 있었고
> (`>=.30 SUPPORTED / >=.15 PARTIALLY / >.05 NOT_SUPPORTED / else REFUTED`),
> 그 규칙의 출력은 **`NOT_SUPPORTED`** 이다. 이 값은 손대지 않고
> `prereg_h2_only_verdict` 로 JSON 에 그대로 남겼다.
> run 전체 verdict 를 `PARTIALLY_SUPPORTED` 로 둔 이유는 임계값을 고쳐서가 아니라,
> **RQ 전체(H1~H4·P1∧P2)에 대한 판정 규칙을 사전등록하지 않았기 때문**이다.
> 비어 있던 규칙을 §12 의 P1/P2 분해로 채웠고, 두 값을 모두 공개한다.
> 임계값·사전은 어느 것도 결과를 본 뒤 수정되지 않았다.

**한 줄 요약**: RF001-A 의 **관측**(수집 URL 의 28.6% 가 기업/모회사 도메인)은 정확했고
이름을 댄 host 사례 5건은 전부 사실이다. 그러나 RF001-A 가 그로부터 끌어낸 **추론**
("따라서 그 면에는 archetype region/endpoint 가 없다")은 관측으로 지지되지 않는다 —
그 16건 중 9건에서 기능 컨트롤이 관측된다.

---

## 14. Limitation

1. **`FUNCTIONAL_LANDING` 의 독립 정답이 없다.** alias table 과 marker 사전은 저자가 손으로 쓴
   `DEFINITION` 이며 gold label 이 아니다. 따라서 정확도·재현율을 계산할 수 없고
   **구성타당도(construct validity)만 논증**한다. 이 RQ 는 label 을 생산하지 않았다.
2. **가장 무거운 한계 — 세 증거가 독립적이지 않다.** (b) 와 (c) 는 같은 DOM 캡처에서 나온
   서로 다른 surface 이고, 둘 다 `pc-fixture-1` 로 수집된 하나의 시점 스냅샷에 의존한다.
   "삼각검증" 이라는 이름이 실제 독립성보다 강한 인상을 준다. (a) 만이 캡처와 무관한
   진짜 외생 증거이며, leave-one-out 에서 (a) 를 빼면 UNDETERMINED 가 26→35 로 뛰는 것이 그 방증이다.
3. **corpus 절단 (censoring).** `D_TEXT_CORPUS_v2` 는 surface 별 상한이 있다
   (headings 25 노드, landmarks 6×200자, nav_links 40×40자, buttons 30×40자, card_texts 25×60자 …).
   대형 기업사이트의 corporate 어휘 distinct count 는 **위쪽이 잘려 과소계수**된다.
   방향은 보수적이라 H2 에 불리하게 작동한다.
4. **앱설치 검출 과소계수.** text corpus 에 href 가 없어 `intent://` `itms-apps` `market://`
   스킴 marker 는 **원리적으로 관측 불가**했다. §9.2 참조.
5. **(c) 의 알려진 위양성 모드 — 전역 사이트 chrome 오염.** `디바이스 케어` 와 `내 파일`
   (둘 다 `samsungsvc.co.kr/solution/*`) 은 control surface 에서 `장바구니·구매·주문·배송·예약`
   이 **동일하게** 발화해 `control_score 4` 를 받았다. 이는 페이지 기능이 아니라 삼성 전역
   내비게이션 템플릿이다. 같은 template 을 공유하는 지원센터 페이지에서 (c) 는 신뢰할 수 없다.
6. **alias table 의 저자 재량.** `홈앤쇼핑 → hnsmall` 같은 약어 인정, `CU` 의 alias 탈락(R-A4),
   은행 본체 도메인(`bank.shinhan.com`, `banking.hanabank.com`)을 SERVICE 로 본 판단은
   모두 저자 결정이다. 표를 전문 공개했으므로 재판정이 가능하다.
7. **n≤5 class 5개** (UTILITY 5 / COMMUNICATION 4 / PLACE 4 / QUERY 4 / CONTENT 3).
   Wilson CI 를 붙였으나 폭이 0.4~0.7 에 달한다. archetype 별 순위를 주장하지 않는다.
8. **단일 시점 · 단일 fixture.** 재수집 시 동일 URL 이 다른 면을 낼 수 있다.

## 15. Causal disclaimer

이 RQ 는 **어떤 URL 도 detector 실패의 원인이라고 주장하지 않는다.**
말할 수 있는 것은 "이 URL 에는 해당 archetype 의 region/endpoint 가 관측되지 않는다" 까지다.
§9.1 의 수렴은 상관 관측이며, RF001-A 의 abstain 40건 중 3건만이 CORPORATE 판정과
겹친다는 사실 자체가 **URL 정체를 원인으로 놓는 설명의 한계**를 보여준다.

## 16. Production implication — assertion type `PROJECTION`

> 아래는 D plane 의 **비권위 제안**이다. 채택 권한은 A plane 에 있다.

1. **"Stage 0 을 고치면 된다" 는 처방은 부분적으로만 옳다.** URL 교체로 해결될 수 있는 후보는
   최대 16/56 (host 불일치) 이고, 그중 실제로 기능 컨트롤이 없는 것은 3건이다.
   반대로 host 가 정상인데 컨트롤이 없는 7건은 URL 을 바꿔도 해결되지 않는다.
   **RF001-A 의 abstain 40건 중 URL 정체로 설명되는 것은 7.5% 다.**
2. **Stage 0 에 host–service 정합 게이트를 넣는 것은 값싸고 방향이 맞다.** 수집 전에
   `SERVICE_HOST / CORPORATE_HOST / UNRELATED_HOST` 를 계산해 `CORPORATE_HOST` 를
   **차단이 아니라 flag** 로 남기면, 후속 abstain 진단에서 이 축을 분리해낼 수 있다.
   차단하면 안 되는 이유는 §10(i) 의 9건 반례다.
3. **`URL_IDENTITY` 를 target 메타로 기록할 것.** archetype mapping 실패를 조사할 때
   "면이 그 기능면이 아니었다" 와 "면은 맞는데 detector 가 못 봤다" 를 구분하는 축이 현재 없다.
4. **퇴화 캡처 4건은 재수집 대상이지 판정 대상이 아니다.** `CONTROL_UNOBSERVABLE` 을
   파이프라인 상태값으로 승격하면 "기능 없음" 과 "관측 불가" 가 섞이지 않는다.
5. **앱 인터스티셜은 텍스트가 아니라 href 스킴/구조로 재야 한다.** 현행 text corpus 로는
   원리적으로 불가능하다 (§9.2).

## 17. 추가 연구질문

- **RQ-D14a** `intent://` `itms-apps` `market://` `<a href>` 스킴과 스마트배너 DOM 구조를
  corpus 에 넣으면 앱 인터스티셜 검출이 RF001-A 의 `app_interstitial` 과 수렴하는가?
  (D14 의 5건 vs RF001-A 의 3건, 교집합 0 을 설명해야 한다)
- **RQ-D14b** §10(ii) 의 7건 (service host + CONTROL_ABSENT: 쿠팡이츠, TikTok, 밴드, Instagram, 배달의민족, 컴포즈커피, 모니모)
  은 무엇인가? 인터스티셜 / 로그인 월 / SPA 미수화 / 수집 시점 문제 중 어느 것인지
  `dom_script_n`·`body_scroll_locked`·`modal_overlay_n`·`gate_*` 로 분리 가능한가?
- **RQ-D14c** RF001-A abstain 40건 중 URL 정체로 설명되지 않는 37건의
  공통 구조는 무엇인가? (D9 quality proxy · D10 slot mismatch 와 결합)
- **RQ-D14d** UTILITY_ENTRY 와 PLACE_LOOKUP 의 host 불일치율이 높은 것이 진짜 archetype
  효과인가, 아니면 "앱 전용 서비스는 웹 대응면이 기업사이트뿐" 이라는 **모집단 선택 효과**인가?
  n≤5 로는 답할 수 없다. 모집단 확장이 선행돼야 한다.
- **RQ-D14e** (c) 의 전역 사이트 chrome 오염(limitation 5)을 main landmark 범위 제한으로
  걷어내면 삼각검증 UNDETERMINED 26건이 얼마나 줄어드는가? → **새 hypothesis_id 의 child run**.

---

*생성: `tools/rq_d14_frame_validity.py` (Restart→Run All 재현 가능, seed 20260827, 입력은 CSV 2개).
D plane 산출물이며 authority_status = NON_CANONICAL. 실제 웹사이트 접속·네트워크 접근 없음.*
