# D-SUP-01 — RF embedding signal 은 interaction semantics 인가 business/domain semantics 인가

**inquiry_kind**: `DIRECTOR_SUPPLEMENTAL` (기존 D autonomous research queue 와 별개. 기존 RQ 의
우선순위·판정·산출물을 바꾸지 않는다.)
**child_id**: `D-SUP-01` · **depends_on**: `RQ-D14`
**hypothesis_id (층 1, 사전등록)**: `H-SUP01-SIGNAL-SOURCE`
**hypothesis_id (층 2, 헤드라인)**: `H-SUP01-SIGNAL-SOURCE-PRIORFREE`
**MLflow**: experiment `LA_03_RF_MAPPING`
· 헤드라인 run `989fac476c1d462bbb42d91819cc968c`
· 사전등록 prior 기반 run `5bdd988baeb24d7383ab3b2636413df9` (parent)
· 선행 2개 run `206912ba…`, `453b105e…` 는 `SUPERSEDED` 로 표시했다(전단사 사실 반영 전 판본).

**VERDICT (전체)**: `PARTIALLY_SUPPORTED`
**prior 기반 판별 경로**: `NOT_TESTABLE`

> **판정 범위 고지.** 이 문서가 판정하는 것은 **behavior 층위** — "현행 RF NLP fallback
> representation 이 실제로 무엇을 따라가는가" 다. **correctness 층위** — "어느 신호가 대표기능의
> 옳은 근거인가" 는 이 표본에서 **판정 불가**다(§2). 이 산출물은 threshold 도 GO/NO-GO 도
> 선언하지 않는다.

---

## 1. 연구질문

RF embedding signal 은 **representative interaction semantics**(검색 제출·항목 열기·인증 진입·
도구 진입의 구조)를 재고 있는가, 아니면 **business/domain semantics**(은행·쇼핑·지도 같은
업종·브랜드 어휘)를 재고 있는가.

경쟁가설 4개:

| id | 진술 |
|---|---|
| `H-SUP01-INTERACTION` | 신호는 상호작용 구조에서 온다 |
| `H-SUP01-DOMAIN` | 신호는 업종/브랜드 어휘에서 온다. archetype 과 업종이 상관돼 그렇게 보일 뿐이다 |
| `H-SUP01-BOTH` | 둘 다 기여하며 분리 가능하다 |
| `H-SUP01-INSEPARABLE` | 이 표본에서는 분리 불가하다 |

---

## 2. 먼저 확인해야 하는 구조적 사실 — prior 기반 판별은 원리적으로 불가능하다

D orchestrator 가 전달한 사실을 `D_OBSERVATION_TABLE_v2.csv` (`in_mart==1`, 56행) 원본에서
**독립 재확인**했다. 선행 지적은 D-RF2-D worker.

```
prior_business_domain  →  prior_archetype        n
CONTENT_VIDEO          →  CONTENT_OPEN            3
FINANCE_PAYMENT        →  FINANCIAL_ACTION_ENTRY 10
MAP_MOBILITY           →  PLACE_LOOKUP            4
PORTAL_SEARCH          →  QUERY                   4
SHOPPING_COMMERCE      →  ITEM_DETAIL            26
SOCIAL_COMMUNICATION   →  COMMUNICATION_ENTRY     4
UTILITY_OTHER          →  UTILITY_ENTRY           5

distinct domain = 7, distinct archetype = 7
H(archetype) = H(domain) = H(joint) = 2.3110 bits
MI = 2.3110 bits,  정규화 MI = 1.000
domain 이 archetype 을 유일하게 결정하는 target = 56/56
```

**귀결**: 이 표본에서 두 라벨은 **같은 변수를 다르게 부른 것**이다. 따라서
`prior_agreement` · `macro F1` 처럼 prior 를 정답으로 놓는 어떤 지표도
`H-SUP01-INTERACTION` 과 `H-SUP01-DOMAIN` 을 구분하지 못한다. interaction 신호가 맞아도
domain 신호가 맞아도 **같은 값이 나온다**.

→ **prior 기반 판별 경로 = `NOT_TESTABLE`.** 사전등록된 prior 기반 판정(§7)은 삭제하지 않고
그대로 보존했지만, 구분력이 없는 근거이므로 헤드라인에서 내렸다. 판정은 prior 를 전혀 쓰지 않는
증거(§6)로 옮겼다. 지시받은 판정 우선순위(top-1 이 아니라 stability·top-2 stability·margin·
class coverage)가 **바로 이 이유로 옳았다**.

---

## 3. 사전 예측과 사후 판정

예측은 **결과를 보기 전에** 코드 상수 `PREREG` 에 박아 두었고(`tools/dsup01_representation_ablation.py`),
실행 후 수정하지 않았다.

| 가설 | 사전 예측 (실행 전 기록) | 사후 판정 (헤드라인 = prior-free) | 근거 |
|---|---|---|---|
| `H-SUP01-INTERACTION` | CONTROL_ONLY 가 TOPIC_ONLY 보다 강하고, 브랜드 토큰을 지워도 신호 유지 (`d_ctrl_topic>+0.05`, `drop<0.05`, `pred_change<0.15`) | **REFUTED** | FULL 의 예측을 CONTROL_ONLY 는 20/50 만 재현, TOPIC_ONLY 는 36/50 재현 (McNemar p=0.0025). 3개 prototype 세트 전부 같은 방향(p<0.005) |
| `H-SUP01-DOMAIN` | TOPIC_ONLY 가 더 강하고(`d_ctrl_topic<-0.05`), NO_BRAND_DOMAIN 에서 신호가 크게 무너진다(`drop>0.10` 또는 `pred_change>0.25`) | **PARTIALLY_SUPPORTED** — 주제어휘 limb `SUPPORTED`, **브랜드토큰 limb `REFUTED`** | 주제 표면이 FULL 을 지배(위와 동일). 그러나 브랜드·도메인 토큰 제거의 예측 변화 8/50(16%)는 같은 개수 임의 토큰 제거(placebo 14~18%)와 구별되지 않는다 |
| `H-SUP01-BOTH` | 둘 다 stratified p95 초과 + 서로 낮은 일치 + FULL 이 최대치 이상 | **NOT_SUPPORTED** | 두 표면이 서로 다른 답을 내는 것은 맞으나(일치 16/50, κ=0.19), FULL 의 결정에 컨트롤 표면이 기여한다는 증거가 없다. "둘 다 기여" 가 아니라 "한쪽만 이끈다" |
| `H-SUP01-INSEPARABLE` | 두 차이의 95% bootstrap CI 가 모두 0 을 포함 | **SUPPORTED (범위 한정)** | correctness 층위에서는 전단사 때문에 **구조적으로** 분리 불가. behavior 층위에서는 prior 없이 분리됐다. (사전등록 CI 규칙만 적용하면 `PARTIALLY_SUPPORTED`) |

**H-DOMAIN vs H-INTERACTION 중 반증된 쪽**: `H-SUP01-INTERACTION` 이 반증됐다. 다만 그 반증은
"컨트롤 표면이 대표기능과 무관하다"는 뜻이 **아니라**, "현행 representation 의 출력이 컨트롤
표면을 따라가지 않는다"는 뜻이다. 동시에 `H-SUP01-DOMAIN` 의 강한 형태(브랜드 문자열 의존)도
반증됐다. 남는 그림은 **"업종 브랜드가 아니라 주제·정체성 텍스트(title/meta/headings)가
출력을 이끈다"** 이다.

---

## 4. 입력 · 분석단위 · N

| 파일 | 행수 | sha256 |
|---|---|---|
| `results/D_TEXT_CORPUS_v2.csv` (v2 인코딩 시정본) | 56 | `bf6bb772faa45541c780c75f5cbffa856783a34661a84e3de27a9eb5da4ea36a` |
| `results/D_OBSERVATION_TABLE_v2.csv` | 66 (in_mart==1 → 56) | `c39c10f09f7a6a7603409550eb331612eb44634eb98ec387a604aa5221351e6b` |
| `results/RQ_D14_frame_validity.json` (strata: `per_target[].identity_class`, join key `wtg`) | 56 | `ee4cc0e989ba72ed615293d51f41575e4308360e30bb4338eadfebcc2e739966` |

- **분석단위**: target state (`in_mart==1`), 1행 = 1 web target
- **N**: n_expected 56 / n_observed 56 (파일럿 frame 59 중 mart 진입 56)
- **strata**: `FUNCTIONAL_LANDING` 27 · `UNDETERMINED` 26 · `CORPORATE_OR_APP_LANDING` 3
  (strata join 실패 0건)
- **missing N**:
  | representation | 토큰 <2 인 target | 해당 서비스 |
  |---|---|---|
  | FULL | 0 | — |
  | CONTROL_ONLY | 5 | 신한 SOL뱅크, 롯데하이마트, 농협하나로마트, NH스마트뱅킹, NH콕뱅크 |
  | TOPIC_ONLY | 3 | 롯데하이마트, 농협하나로마트, Google |
  | NO_BRAND_DOMAIN | 1 | 롯데하이마트 |
  - **complete-case n=50** (4개 representation 모두 토큰≥2). 안정성·판정은 complete-case 가
    primary, all56 은 병기.
- **코드**: `tools/dsup01_representation_ablation.py`
  sha256 `669646d104459d26eb2f225a781ab64b626d4038d2ff7a6f32b881ce941bc635`
- **결과 JSON**: `results/DSUP01_representation_ablation.json`
- **모델**: `BAAI/bge-m3` 단일 (max_seq 8192, instruction prefix 미사용 = bge-m3 공식 규약).
  모델 비교는 이 inquiry 의 주제가 아니다. 오프라인(`HF_HUB_OFFLINE=1`,
  `TRANSFORMERS_OFFLINE=1`), 네트워크 다운로드 없음. seed 20260827.

### 방화벽

holdout label · `LABEL_SPLIT_FROZEN*` · `HOLDOUT_FOR_C*` · `RAW_L1~L4*` · `PACKET_L*` ·
`*_OVERLAP*` · `PRECEDENCE_CONTESTED*` · `CALIBRATION_FOR_B*` · `**/control/**` · B/C 의
target-level holdout error report — **하나도 열지 않았다.** 이 run 이 읽은 파일은 위 표 3개와
읽기 전용 대조로 인용한 `RF2_C_field_ablation.json` 뿐이다. gold label 생성 없음,
REAL_TARGET 접속 없음, production/control/engine/mart/raw evidence 수정 없음, git 명령 없음.

---

## 5. prototype 전문 · representation 조작화 정의 전문 · 제거된 브랜드/도메인 토큰

### 5.1 prototype (frozen, 3세트)

RF001-C 에서 동결된 문구를 **그대로** 재사용했다. provenance: SSOT 00 §4 archetype 목록 +
SSOT 01 §5 Stage-3 branch 정의문. 코퍼스를 읽고 조정한 적 없고 결과를 본 뒤에도 수정하지 않았다.
PRIMARY = `A_SSOT_DEF`. (안정성 측정 요건 "최소 2세트" → 3세트 유지)

**Set A — `A_SSOT_DEF`** (SSOT 정의 축약형)

- `QUERY`: 사용자가 검색 입력창에 자유 텍스트 질의를 입력하고 제출하여 검색 결과 목록 상태로 전환하는 것이 대표행동이다. 검색 입력 control, 검색 form, 검색 제출 버튼이 대표 표면이다. search box, search form, submit query, search results.
- `CONTENT_OPEN`: 이미 존재하는 기사, 영상, 콘텐츠 한 건을 목록에서 선택해 본문을 열거나 재생을 시작하는 것이 대표행동이다. 콘텐츠 카드 목록, 기사 본문, 미디어 재생이 대표 표면이다. article body, news, video playback, content card list.
- `ITEM_DETAIL`: 거래 대상 상품 한 건의 상세면에 들어가 상품명, 가격, 거래 control 의 존재를 확인하는 것이 대표행동이다. 반복되는 상품 카드 목록과 상품 상세 문서가 대표 표면이다. product name, price, cart, order, shopping mall, item detail page.
- `PLACE_LOOKUP`: 장소를 질의하거나 특정 장소의 상세면을 여는 것이 대표행동이다. 장소 검색 control, 장소 목록, 지도, 주소, 장소 상세 패널이 대표 표면이다. map, place search, address, location, route, navigation.
- `COMMUNICATION_ENTRY`: 사람 사이의 게시물, 스레드, 메시지를 교환하는 공간에 진입하는 것이 대표행동이다. 스레드 목록, 게시글 목록, 글쓰기 진입 control, 실제 로그인 gate 가 대표 표면이다. message, chat, post, thread, community, social feed, comment.
- `FINANCIAL_ACTION_ENTRY`: 금융처리 기능의 시작면을 열거나 그 기능을 시작하기 위해 필요한 실제 로그인 및 본인인증 gate 까지 진입하는 것이 대표행동이다. 잔액 조회, 이체, 송금, 결제, 카드, 보험, 인증 기능 진입 control 이 대표 표면이다. bank, transfer, payment, balance, card, insurance, login, identity verification.
- `UTILITY_ENTRY`: 특정 목적의 도구 기능면을 열고 첫 primary control 을 사용할 수 있는 상태로 만드는 것이 대표행동이다. 단일 목적 기능 진입 control 과 그 기능 화면이 대표 표면이다. utility tool, service function, apply, reserve, issue, lookup, settings.

**Set B — `B_USER_BEHAVIOR`** (같은 정의를 1인칭 행동 서술로. 어휘 register 를 크게 바꾼다)

- `QUERY`: 나는 궁금한 것을 검색창에 입력하고 검색 버튼을 눌러 결과 목록을 본다.
- `CONTENT_OPEN`: 나는 목록에서 기사나 영상 하나를 골라 눌러서 읽거나 본다.
- `ITEM_DETAIL`: 나는 사고 싶은 물건 하나를 눌러 상세 화면에서 가격과 정보를 확인한다.
- `PLACE_LOOKUP`: 나는 가려는 장소를 찾아보고 그 장소의 위치와 상세 정보를 확인한다.
- `COMMUNICATION_ENTRY`: 나는 다른 사람이 올린 글이나 메시지를 보러 대화 공간에 들어간다.
- `FINANCIAL_ACTION_ENTRY`: 나는 은행이나 카드 업무를 시작하려고 로그인 화면까지 들어간다.
- `UTILITY_ENTRY`: 나는 필요한 기능 하나를 열어서 바로 쓸 수 있는 상태까지 간다.

**Set C — `C_TERSE_LABEL`** (라벨에 가까운 최소 gloss)

- `QUERY`: 검색 질의 search query
- `CONTENT_OPEN`: 콘텐츠 열람 content open article video
- `ITEM_DETAIL`: 상품 상세 item detail product price
- `PLACE_LOOKUP`: 장소 조회 place lookup map location
- `COMMUNICATION_ENTRY`: 커뮤니케이션 진입 communication message post
- `FINANCIAL_ACTION_ENTRY`: 금융 기능 진입 financial action bank payment
- `UTILITY_ENTRY`: 도구 기능 진입 utility function tool

### 5.2 representation 조작화 정의 (전문)

결합 규약은 4종 모두 동일하다: 필드를 아래 순서대로 `" \n "` 로 잇고, 빈 필드는 생략한다
(`D_TEXT_CORPUS_v2.text_blob` 의 정본 규약).

**`FULL`** — `D_TEXT_CORPUS_v2.text_blob` 그대로. 12개 필드 = title, meta_description,
headings, landmarks, nav_links, buttons, aria_labels, placeholders, form_labels, input_names,
card_texts, url_tokens. 현행 RF NLP fallback representation 과 동일하다.

**`CONTROL_ONLY`** — 상호작용 컨트롤 표면만. 필드 = `buttons` + `aria_labels` +
`placeholders` + `form_labels` + `input_names`. 각 필드의 DOM 출처:
`buttons` = `//button | //*[@role='button'] | //input[@type='submit']` 의 텍스트,
`aria_labels` = `//*[@aria-label]` 의 aria-label 속성,
`placeholders` = input/textarea 의 placeholder 속성,
`form_labels` = `//label` 텍스트,
`input_names` = `//input[@name]` 의 name 속성.
즉 "이 화면에서 무엇을 조작할 수 있는가" 의 표면이며, title/meta/headings/card/nav/landmark/url 은
모두 제외한다.

**`TOPIC_ONLY`** — 주제·업종 어휘만. 필드 = `title` + `meta_description` + `headings`.
컨트롤 텍스트와 카드·내비·랜드마크·URL 토큰은 모두 제외한다. 즉 "이 사이트가 무엇에 관한
것인가" 의 표면이다.

**`NO_BRAND_DOMAIN`** — `FULL` 에서 브랜드·도메인 토큰만 제거. 필드 구성은 FULL 과 같고 제거
규칙만 다르다. target 별 제거 대상 토큰 집합:

1. `prior_service` 를 `[a-zA-Z0-9가-힣]+` 로 토큰화한 것 중 **길이≥2** 인 토큰 + 공백 제거
   압축형 (예: `신한 SOL뱅크` → `신한`/`sol`/`뱅크`/`신한sol뱅크`)
2. 대상 **host 의 라벨 토큰**. host 는 `prior_url` 의 hostname 이며 RQ-D14 `per_target.a_host`
   와 대조해 확인했다(`wtg` 자체는 16자리 불투명 id 라 host 문자열을 담고 있지 않다).
   host 를 `[.-]` 로 쪼갠 라벨 중 길이≥2 인 것 전부
3. `url_tokens` 의 **도메인 성분** — scheme/host 유래 구문 토큰
   `{https, http, www, com, co, kr, net, org}` 를 항상 포함
4. RQ-D14 `per_target.a_matched_alias` (브랜드 alias)가 있으면 그 토큰

제거 방식: **라틴 토큰**은 앞뒤가 `[A-Za-z0-9]` 가 아닌 위치에서만 대소문자 무시 치환,
**한글 토큰**은 어절 경계가 없으므로 단순 부분문자열 치환(대소문자 무시). 치환 결과는 공백
1칸으로 바꾸고 줄 단위로 공백을 정규화하며, 비게 된 줄은 버린다.

### 5.3 제거된 브랜드·도메인 토큰

**distinct 토큰 120개, 총 601회 제거.** 토큰 질량 기준 중앙 제거율은 4.5% (최대 100%).
전역 상위 제거 횟수:

```
https 54 · com 41 · chrome 40 · google 35 · www 28 · 티맵 26 · cu 25 · kr 18 · 다이소 16 ·
이마트 15 · co 12 · 파일 10 · 롯데마트 10 · gs25 9 · 토스 9 · netflix 8 · 에이닷 8 · 당근 8 ·
instagram 7 · youtube 7 · 쿠팡이츠 6 · 코스트코 6 · band 6 · 롯데백화점 6 · 카카오맵 6 …
```

**target 별 blacklist 와 실제 제거 횟수 전문**은 결과 JSON `brand_domain_removal.per_target`
(56행 전부)과 MLflow artifact `removed_brand_domain_tokens.txt` 에 있다.

**부수 제거 고지**: 한글 브랜드는 부분문자열로 지우므로 브랜드명이 일반어와 겹치면 일반어까지
지워진다. 실제 사례 — `내 파일`(서비스) 때문에 일반어 `파일` 이 10회 제거됨, `당근`(당근마켓)
8회, `다음`(Daum) 등. 감사 목록에 전부 남겼다.

**입력 결손 고지**: `prior_url` 이 빈 2건(네이버 `wtg=6d5510a695d0a614`, G마켓
`wtg=f9fbd771ffcdbd42`)은 host 라벨 규칙(2번)이 적용되지 않았다. 다만 D14 alias(`naver`,
`gmarket`)와 서비스 토큰이 4번·1번 규칙으로 잡혀 브랜드 문자열 자체는 제거됐다.

---

## 6. 헤드라인 — prior 를 쓰지 않는 증거 (complete-case n=50)

### E1. FULL 의 예측을 어느 부분표면이 재현하는가 (prior 불필요, 두 subset 대칭 비교)

| prototype set | TOPIC_ONLY 가 FULL 재현 | CONTROL_ONLY 가 FULL 재현 | 차이 | McNemar exact p |
|---|---|---|---|---|
| A_SSOT_DEF (PRIMARY) | **36/50 = 0.720** [0.583, 0.825] | 20/50 = 0.400 [0.276, 0.538] | +0.320 | **0.0025** |
| B_USER_BEHAVIOR | 39/50 = 0.780 | 24/50 = 0.480 | +0.300 | 0.0015 |
| C_TERSE_LABEL | 41/50 = 0.820 | 24/50 = 0.480 | +0.340 | 0.00049 |

**길이 교란 통제**: CONTROL_ONLY 의 토큰 중앙값 34 ≥ TOPIC_ONLY 의 31 (FULL 대비 질량 비율도
0.221 vs 0.215). 컨트롤 표면이 **더 길다**. 따라서 "주제 표면이 FULL 을 더 잘 재현한다" 를
텍스트 길이로 설명할 수 없다.

### E2. 브랜드·도메인 토큰 제거 vs 같은 개수 임의 토큰 제거(placebo, 3반복)

| prototype set | 브랜드 제거 시 예측 변화 | placebo 변화 (min~max) | 브랜드가 placebo 최대치 초과? |
|---|---|---|---|
| A_SSOT_DEF | **8/50 = 0.16** [0.083, 0.285] | 0.14 ~ 0.18 | **아니오** (placebo 범위 안) |
| B_USER_BEHAVIOR | 9/50 = 0.18 | 0.16 ~ 0.16 | 예 (+0.02, 1건 차이) |
| C_TERSE_LABEL | 4/50 = 0.08 | 0.06 ~ 0.12 | 아니오 |

→ 브랜드 문자열은 **특별하지 않다**. 같은 양의 아무 토큰을 지워도 같은 정도로 흔들린다.
`H-SUP01-DOMAIN` 의 브랜드토큰 limb 은 **REFUTED**.

### E3~E6. 지시받은 우선순위 지표 (PRIMARY = proto A, complete-case n=50)

**prediction stability across representations**

| pair | top-1 일치 | Cohen κ | top-2 집합 일치 |
|---|---|---|---|
| FULL ~ NO_BRAND_DOMAIN | 0.840 (42/50) | 0.788 | 0.720 |
| FULL ~ TOPIC_ONLY | 0.720 (36/50) | 0.633 | 0.580 |
| TOPIC_ONLY ~ NO_BRAND_DOMAIN | 0.680 (34/50) | 0.573 | 0.540 |
| CONTROL_ONLY ~ NO_BRAND_DOMAIN | 0.440 (22/50) | 0.326 | 0.280 |
| FULL ~ CONTROL_ONLY | 0.400 (20/50) | 0.281 | 0.220 |
| CONTROL_ONLY ~ TOPIC_ONLY | **0.320 (16/50)** | **0.193** | **0.160** |

- **4-way top-1 만장일치 = 15/50 = 0.300** [0.191, 0.438]
- **4-way top-2 집합 만장일치 = 6/50 = 0.120** [0.056, 0.238]
- target 당 서로 다른 예측 개수 분포: 1개 15건 · 2개 24건 · 3개 11건 (평균 1.92)
- 다른 prototype 세트에서도 같은 그림: 4-way 만장일치 B 0.38 · C 0.42

**representation × 주요 지표**

| representation | margin 중앙값 | class coverage (7 중) | 한 번도 예측 안 된 class | 토큰 중앙값 |
|---|---|---|---|---|
| FULL | 0.0214 | 6 | UTILITY_ENTRY | 173.5 |
| CONTROL_ONLY | **0.0158** | **7** | — | 32.5 |
| TOPIC_ONLY | 0.0264 | 6 | UTILITY_ENTRY | 28.0 |
| NO_BRAND_DOMAIN | 0.0280 | **7** | — | 166.0 |

- margin 은 4종 모두 **코사인 0.016~0.028** 수준이다. top-1 은 거의 동점 근처에서 갈린다.
- class coverage 는 **가장 약한 표면(CONTROL_ONLY)에서 가장 높다**. coverage 는 정확도와
  같은 방향이 아니다. 선행 RF001-C 에서 UTILITY_ENTRY 가 0/5 로 사실상 6-class 였던 문제는
  FULL·TOPIC_ONLY 에서 재현됐고(UTILITY_ENTRY 예측 0건), CONTROL_ONLY·NO_BRAND_DOMAIN 에서만
  1건 예측됐다.
- CONTROL_ONLY 의 예측은 QUERY 로 쏠린다(16/50, prior QUERY 는 4건). 컨트롤 표면에는 검색창이
  거의 항상 있기 때문으로 보인다 — 컨트롤 표면 단독은 "검색 가능성" 을 재고 있고 대표기능을
  재고 있지 않다.

**prototype stability** (같은 representation, prototype 세트만 교체)

| representation | 3-way 만장일치 | pairwise 일치 (κ) | macro F1 범위 | 기준선 통과 판정 뒤집힘 |
|---|---|---|---|---|
| FULL | 23/56 = 0.411 | 0.518~0.607 (κ 0.35~0.47) | 0.230 | 없음 |
| CONTROL_ONLY | 23/51 = 0.451 | 0.529~0.569 (κ 0.42~0.47) | 0.104 | 없음 |
| TOPIC_ONLY | 24/53 = 0.453 | 0.566~0.623 (κ 0.42~0.51) | 0.194 | 없음 |
| NO_BRAND_DOMAIN | 22/55 = 0.400 | 0.455~0.618 (κ 0.29~0.49) | 0.243 | 없음 |

→ **prototype 문구 민감도는 재현됐다.** 문구만 바꿔도 예측의 절반 이상이 바뀐다(3-way 만장일치
0.40~0.45, κ 0.29~0.51). 다만 §6 E1 의 방향(주제 표면이 FULL 을 이끈다)은 세 세트 전부에서
동일하다 — **판정에 쓰는 결론은 prototype 문구에 강건하다.**

---

## 7. 사전등록 prior 기반 층 (보존, 구분력 없음)

지시대로 계산했고 수정하지 않았다. §2 때문에 **두 경쟁가설을 구분하지 못하는 근거**임을 명시한다.

| representation | macro F1 (cc) | prior_agreement (진단용, cc) | top-2 포함율 | permutation p | stratified p95 초과 |
|---|---|---|---|---|---|
| FULL | 0.475 | 0.640 | 0.820 | <0.0001 | 예 |
| CONTROL_ONLY | 0.260 | 0.320 | 0.440 | 0.0027 | 예 |
| TOPIC_ONLY | 0.501 | 0.660 | 0.840 | <0.0001 | 예 |
| NO_BRAND_DOMAIN | 0.430 | 0.640 | 0.840 | <0.0001 | 예 |

- 기준선: **stratified** (n=20000) macro F1 p95 = **0.2238**, prior_agreement p95 = 0.380.
  majority(ITEM_DETAIL) macro F1 = 0.093 — 6/7 class recall 0 이라 판정 기준선이 될 수 없어
  **참고용으로만 병기**한다.
- **permutation null (prior 셔플, n=20000)**: 4종 모두 관측값이 null 분포 상단 바깥에 있다
  (p ≤ 0.0027). 즉 "아무 신호도 없다" 는 기각된다 — 단, 그 신호가 interaction 인지 domain 인지는
  이 지표가 말할 수 없다.
- 사전등록 판정: `d_ctrl_topic` = −0.241 (95% paired bootstrap CI [−0.411, −0.044]),
  `drop_brand` = +0.045 (CI [−0.049, +0.132]), `pred_change_brand` = 0.160,
  `agree_ctrl_topic` = 0.320
  → INTERACTION `REFUTED` · DOMAIN `PARTIALLY_SUPPORTED` · BOTH `PARTIALLY_SUPPORTED` ·
  INSEPARABLE `PARTIALLY_SUPPORTED`, 전체 `PARTIALLY_SUPPORTED`
  (MLflow run `5bdd988baeb24d7383ab3b2636413df9`, 태그 `discriminative_power=NONE_prior_route_not_testable`)
- McNemar(prior_agreement): FULL vs NO_BRAND_DOMAIN 은 불일치 4건, p=1.0 — 브랜드 제거가
  prior 일치도를 유의하게 바꾸지 않는다. CONTROL vs TOPIC 은 2 vs 19, p=0.00022.

---

## 8. strata 별 결과 (RQ-D14 `identity_class`, PRIMARY proto A, complete-case)

### `FUNCTIONAL_LANDING` (all56 n=27, complete-case n=23)

| rep | prior_agreement [Wilson 95%] | macro F1 | coverage | margin med | top-2 포함율 |
|---|---|---|---|---|---|
| FULL | 0.696 [0.491, 0.844] | 0.390 | 5 | 0.0357 | 0.826 |
| CONTROL_ONLY | 0.391 [0.222, 0.592] | 0.257 | 7 | 0.0228 | 0.565 |
| TOPIC_ONLY | **0.783** [0.581, 0.903] | 0.440 | 5 | 0.0395 | 0.870 |
| NO_BRAND_DOMAIN | 0.609 [0.408, 0.778] | 0.308 | 6 | 0.0333 | 0.783 |

4-way 만장일치 8/23 [0.188, 0.551]. FULL~TOPIC 0.739 vs FULL~CONTROL 0.478.

### `UNDETERMINED` (all56 n=26, complete-case n=24)

| rep | prior_agreement [Wilson 95%] | macro F1 | coverage | margin med | top-2 포함율 |
|---|---|---|---|---|---|
| FULL | 0.583 [0.388, 0.755] | 0.483 | 5 | 0.0134 | 0.792 |
| CONTROL_ONLY | 0.292 [0.149, 0.492] | 0.303 | 6 | 0.0155 | 0.333 |
| TOPIC_ONLY | 0.583 [0.388, 0.755] | 0.492 | 5 | 0.0203 | 0.792 |
| NO_BRAND_DOMAIN | **0.667** [0.467, 0.820] | **0.556** | 6 | 0.0221 | 0.875 |

4-way 만장일치 6/24 [0.120, 0.449].
**주목**: 이 stratum 에서는 브랜드·도메인 토큰을 지우는 편이 prior 일치가 **더 높다**
(0.667 vs FULL 0.583). FUNCTIONAL 에서는 반대(0.609 vs 0.696). 방향이 stratum 별로 뒤집히며,
두 CI 는 크게 겹친다 — 이 차이를 실질로 읽으면 안 된다.

### `CORPORATE_OR_APP_LANDING` (all56 n=3, complete-case n=3)

| rep | prior_agreement [Wilson 95%] | macro F1 | coverage |
|---|---|---|---|
| FULL | 0.667 [0.208, 0.939] | 0.143 | 2 |
| CONTROL_ONLY | 0.000 [0.000, 0.561] | 0.000 | 2 |
| TOPIC_ONLY | 0.333 [0.061, 0.792] | 0.095 | 3 |
| NO_BRAND_DOMAIN | 0.667 [0.208, 0.939] | 0.143 | 2 |

> **n=3 은 사실상 추정 불가에 가깝다.** Wilson CI 폭이 거의 전 구간이라(예: 0.000 의 상한이
> 0.561) 이 stratum 단독으로는 어떤 순위 비교도 성립하지 않는다. 수치는 기록용이며 판정 근거로
> 쓰지 않았다.

---

## 9. 반례

**4개 representation 이 3개 이상 서로 다른 archetype 을 준 target: 11건** (complete-case 50 중)

| 서비스 | prior | stratum | FULL | CTRL | TOPIC | NOBRAND |
|---|---|---|---|---|---|---|
| 쿠팡이츠 | ITEM_DETAIL | UNDETERMINED | COMMUNICATION_ENTRY | CONTENT_OPEN | ITEM_DETAIL | CONTENT_OPEN |
| 디바이스 케어 | UTILITY_ENTRY | UNDETERMINED | FINANCIAL_ACTION_ENTRY | COMMUNICATION_ENTRY | ITEM_DETAIL | FINANCIAL_ACTION_ENTRY |
| Netflix | CONTENT_OPEN | FUNCTIONAL | CONTENT_OPEN | QUERY | CONTENT_OPEN | UTILITY_ENTRY |
| 카카오톡 | COMMUNICATION_ENTRY | UNDETERMINED | COMMUNICATION_ENTRY | QUERY | PLACE_LOOKUP | COMMUNICATION_ENTRY |
| 네이버 | QUERY | FUNCTIONAL | ITEM_DETAIL | **QUERY** | CONTENT_OPEN | ITEM_DETAIL |
| 탑마트 | ITEM_DETAIL | CORPORATE | ITEM_DETAIL | PLACE_LOOKUP | CONTENT_OPEN | ITEM_DETAIL |
| 하나은행 | FINANCIAL_ACTION_ENTRY | FUNCTIONAL | FINANCIAL_ACTION_ENTRY | UTILITY_ENTRY | FINANCIAL_ACTION_ENTRY | ITEM_DETAIL |
| 배달의민족 | ITEM_DETAIL | UNDETERMINED | PLACE_LOOKUP | COMMUNICATION_ENTRY | PLACE_LOOKUP | ITEM_DETAIL |
| 내 파일 | UTILITY_ENTRY | UNDETERMINED | FINANCIAL_ACTION_ENTRY | COMMUNICATION_ENTRY | PLACE_LOOKUP | FINANCIAL_ACTION_ENTRY |
| 11번가 | ITEM_DETAIL | FUNCTIONAL | PLACE_LOOKUP | QUERY | COMMUNICATION_ENTRY | COMMUNICATION_ENTRY |
| 현대백화점 | ITEM_DETAIL | FUNCTIONAL | CONTENT_OPEN | COMMUNICATION_ENTRY | PLACE_LOOKUP | COMMUNICATION_ENTRY |

**네이버는 판정에 대한 정면 반례다.** prior QUERY 를 맞힌 유일한 representation 이
CONTROL_ONLY 다 — 검색 컨트롤이 실제로 대표기능을 가리킨 사례. 즉 "컨트롤 표면이 쓸모없다" 가
아니라 "현행 FULL 이 컨트롤 표면을 따라가지 않는다" 가 옳은 진술이다.

**브랜드 제거로 예측이 뒤집힌 8건**: 쿠팡이츠, Netflix, 하나은행, 에이닷 전화, 배달의민족,
11번가, 컴포즈커피, 현대백화점. 이 중 배달의민족·컴포즈커피는 브랜드 제거 **후에** prior 와
일치하게 됐고(PLACE_LOOKUP→ITEM_DETAIL, QUERY→ITEM_DETAIL), 하나은행·Netflix 는 반대로 어긋났다.
방향이 일정하지 않다 — placebo 대조(E2)와 같은 결론이다.

---

## 10. 기존 D 결과와의 관계 · superseding finding

기존 D 산출물은 **하나도 수정하지 않았다.** 아래는 이 문서에만 기록한다.

### 10.1 재현 확인 (기존 D 파이프라인과 어긋나지 않음)

`RF2_C_field_ablation.json` 의 `primary_controls`(필드 집합이 `CONTROL_ONLY` 와 동일, 결합
순서만 다름)와 `text_blob__ALL`(= `FULL`)을 독립 재계산했다.

| 항목 | RF2-C 보고값 | D-SUP-01 재계산 |
|---|---|---|
| primary_controls macro F1 (all56) | 0.2543 | **0.25431** (RF2-C 필드순서), 0.25876 (본 정의 순서) |
| primary_controls prior_agreement | 0.3036 | 0.30357 |
| text_blob__ALL macro F1 | 0.5088 | **0.50878** |
| text_blob__ALL prior_agreement | 0.6786 | 0.67857 |

필드 결합 순서 차이의 macro F1 영향 = 0.0045. **파이프라인 일치 확인.**

### 10.2 SUPERSEDING FINDING — 기존 D 해석 중 이 결과가 반박하는 부분

1. **`RF001_C` 의 헤드라인(bge-m3 macro F1 0.497 vs stratified 0.139, "기준선을 넘는다")은
   두 가설을 구분하는 근거로 쓸 수 없다.** 그 지표의 정답축인 `prior_archetype` 이
   `prior_business_domain` 과 전단사이기 때문이다(§2). 숫자가 틀렸다는 것이 아니라, 그 숫자로
   "대표기능(interaction)을 재고 있다" 고 말할 수 없다는 뜻이다. RF001-C 파일은 수정하지 않았다.
   D-RF2-D worker 의 "prior_agreement 는 도메인 prior 재현율에 가깝다" 는 지적이 이 결론과 같다.
2. **`RF2_C` 의 "H-C2 primary controls·accessibility text 가 더 informative = NOT_SUPPORTED"**
   는 이 run 에서 **더 강한 형태로 재확인**된다. RF2-C 는 prior 기준으로 그렇게 말했지만,
   D-SUP-01 은 prior 없이도 같은 결론에 도달했다(E1: 컨트롤 표면은 FULL 의 결정을 20/50 만
   재현). 반박이 아니라 **독립 근거로의 승격**이다.
3. **`RF001_B` (TF-IDF) 의 `brand_leak_test` 는 "deleak 후 stratified 를 넘지 못한다
   (`deleak_still_above_stratified=false`, drop 0.039)" 로 브랜드 누출을 강하게 시사했다.
   임베딩 경로에서는 그렇지 않다.** 같은 취지의 제거를 임베딩에 적용하면 예측 변화는 8/50 이고
   이는 placebo 와 구별되지 않는다(§6 E2). **표현 방식(TF-IDF vs 임베딩)에 따라 브랜드 의존성
   결론이 달라진다** — TF-IDF 는 브랜드 문자열 자체를 feature 로 쓰므로 제거에 취약하고,
   임베딩은 브랜드를 지워도 남은 주제 문맥에서 같은 방향을 유지한다. RF001-B 파일은 수정하지
   않았으며, 그 결론은 TF-IDF 경로에 한정해 읽어야 한다는 것이 이 문서의 superseding 주장이다.
4. **선행 RF001-C 의 "UTILITY_ENTRY 0/5" 는 v2 코퍼스·complete-case 에서도 사실상 유지된다.**
   FULL·TOPIC_ONLY 에서 UTILITY_ENTRY 예측 0건, CONTROL_ONLY·NO_BRAND_DOMAIN 에서 1건.
   7-class 가 실질 6-class 로 작동하는 문제는 해소되지 않았다.

---

## 11. VERDICT

| 항목 | 값 |
|---|---|
| **전체** | **`PARTIALLY_SUPPORTED`** (behavior 층위) |
| prior 기반 판별 경로 | **`NOT_TESTABLE`** |
| `H-SUP01-INTERACTION` | **`REFUTED`** (prior-free) |
| `H-SUP01-DOMAIN` | **`PARTIALLY_SUPPORTED`** — 주제어휘 limb `SUPPORTED`, 브랜드토큰 limb `REFUTED` |
| `H-SUP01-BOTH` | `NOT_SUPPORTED` |
| `H-SUP01-INSEPARABLE` | `SUPPORTED` (correctness 층위 한정. behavior 층위는 분리됨) |

**한 문장**: 현행 RF NLP fallback representation 의 출력은 **브랜드 문자열이 아니라 주제·정체성
텍스트(title/meta/headings)를 따라가며, 상호작용 컨트롤 표면은 그 결정을 이끌지 않는다.**
그러나 "그래서 그것이 틀렸는가" 는 이 표본에서 판정할 수 없다 — 정답으로 쓸 수 있는 유일한
라벨이 업종 라벨과 같은 변수이기 때문이다.

**threshold 및 GO/NO-GO 는 선언하지 않는다.**

---

## 12. Limitation

0. **가장 무거운 한계**: 이 표본에서 `prior_archetype` 과 `prior_business_domain` 은 완전
   전단사다(NMI=1.000, MI=H=2.311 bits, 56/56 결정적). 두 라벨이 같은 변수이므로 prior 를
   정답으로 쓰는 어떤 지표도 interaction 가설과 domain 가설을 구분하지 못한다. 그래서 판정을
   prior-free 증거로 옮겼고, 그 대가로 **correctness 에 대해서는 아무 말도 하지 못한다.**
1. target 은 gold label 이 아니라 business-domain prior 다. `prior_agreement` 는 정확도가 아니다.
2. n=56 에 7 class, 5개 class 가 n≤5 라 per-class Wilson CI 가 거의 [0,1] 이다.
3. `CORPORATE_OR_APP_LANDING` 은 n=3 으로 사실상 추정 불가.
4. `CONTROL_ONLY` 가 5개 target 에서 비어 있다. "컨트롤 표면이 약하다" 가 **의미론적 무력함**인지
   **수집 시점의 DOM 부재(SPA hydration 이전·앱 인터스티셜)**인지 이 설계로는 분리되지 않는다.
   비어 있는 5건은 전부 은행·마트 계열이다.
5. 한글 브랜드 제거는 어절 경계가 없어 부분문자열 치환이며, 일반어 부수 제거가 발생한다
   (`파일` 10회 등). 전량 감사 공개했지만 제거 규칙 자체의 정밀도 한계는 남는다.
   `prior_url` 결손 2건은 host 라벨 규칙이 적용되지 않았다.
6. `NO_BRAND_DOMAIN` 은 **브랜드 문자열**을 지울 뿐 **업종 의미**(배달·은행·상품·장바구니 …)는
   그대로 남긴다. 따라서 E2 는 "브랜드 토큰 의존" 만 반증하며 "업종 의미 의존" 을 반증하지 않는다.
   업종 의미 제거는 이 설계로 조작화되지 않는다.
7. placebo 대조와 McNemar 비교는 사전등록에 없던 사후 추가 도구다(추가 사유는 결과 JSON
   `posthoc_additions` 에 명시). exploratory 로 취급해야 한다. 재사용한 임계값 0.25·0.60 은
   사전등록 값 그대로다.
8. 단일 모델(bge-m3)·단일 임베딩 공간이며 SSOT 01 §7 의 2차 모델(cross-encoder/NLI)은 시험하지
   않았다. margin 이 0.016~0.028 로 매우 작아 top-1 은 거의 동점에서 갈린다.
9. prototype 문구 민감도가 크다(3-way 만장일치 0.40~0.45). 판정 방향은 세 세트에서 일치했으나,
   개별 target 의 예측은 문구에 흔들린다.

---

## 13. 추가 연구질문

1. **표본 설계 문제**: 두 신호원을 correctness 층위에서 분리하려면 같은 업종 안에서 archetype 이
   갈리는 target(포털의 지도 진입 vs 검색 진입, 은행의 콘텐츠 열람 vs 금융 진입 …)을 넣어
   domain-archetype 결합을 깨야 한다. **분석으로는 해결되지 않는다.**
2. `prior_archetype` 대신 독립 gold label 로 같은 ablation 을 돌리면 순환이 끊기는가
   (라벨 생산은 D 권한 밖 — A 의 labeler worker 필요).
3. `CONTROL_ONLY` 가 빈 5건을 렌더 후 DOM(SPA hydration 이후)으로 재수집하면 컨트롤 표면의
   신호가 살아나는가. 살아난다면 limitation 4 가 결론을 바꾼다.
4. `TOPIC_ONLY` 내부 재분해 — RF2-C 의 "title 단독이 FULL 보다 강하다" 가 브랜드 토큰 제거 후에도
   유지되는가.
5. top-2 집합이 안정적인 target 만 자동 매핑하고 나머지를 abstain 시키는 규칙의 coverage 곡선
   (단, threshold 선언은 A 권한).
6. 업종 의미 어휘(브랜드가 아닌 `배달`·`은행`·`상품` 같은 도메인 명사)를 제거하는 별도 ablation —
   limitation 6 을 조작화하는 새 hypothesis_id 가 필요하다.

---

## 14. 산출물

| 파일 | 내용 |
|---|---|
| `tools/dsup01_representation_ablation.py` | 분석 코드 (sha256 `669646d1…`) |
| `results/DSUP01_representation_ablation.json` | 결과 전문 (최상위 `"verdict"` 포함) |
| `results/DSUP01_FINDINGS.md` | 이 문서 |
| `figures/DSUP01_priorfree_evidence.png` | **헤드라인** — E1/E2 + 라벨 식별가능성 |
| `figures/DSUP01_stability_matrix.png` | representation 간 top-1/top-2 일치 + strata 별 만장일치 |
| `figures/DSUP01_signal_margin_coverage.png` | 기준선 대비 신호·margin·class coverage |
| `figures/DSUP01_strata.png` | strata 분해 (Wilson CI) |
| `figures/DSUP01_prototype_stability.png` | prototype 세트 교체 κ · 순위 민감도 |
| `../notebooks/d_research/DSUP01_representation_ablation.ipynb` | 결과 JSON 을 읽어 렌더 (Restart→Run All 검증) |
