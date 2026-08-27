# D-RF-001-C — SSOT prototype 임베딩 유사도로 archetype prior 를 되찾을 수 있는가

- **child_id**: D-RF-001-C · **rq_id**: RQ-D-RF-001 · **hypothesis_id**: H-RF001-C-EMBED-PROTOTYPE
- **plane**: D (NON_CANONICAL, 연구 가설 · 승인 아님)
- **MLflow**: experiment `LA_03_RF_MAPPING` (id 4), run_id `bd04b82fa1104cd3a93283b40f2dd5cb`,
  parent `2bf780a9efca4562bdf63a7c165514cc`
- **seed**: 20260827 · Monte Carlo / permutation draws = 20000
- **코드**: `research_d/tools/rf001_c_embedding.py` · **결과 JSON**: `research_d/results/RF001_C_embedding.json`
- **VERDICT**: **PARTIALLY_SUPPORTED**

---

## 1. RQ

> SSOT 01 §7 이 규정한 대로 "일곱 archetype 각각에 SSOT 정의를 짧은 prototype 문장으로 둔" 뒤,
> pretrained multilingual sentence embedding 으로 page representation 과 prototype 의 cosine
> similarity 만 계산해서 (학습 없이) business-domain prior 를 되찾을 수 있는가?

이 실험은 **NLP fallback 의 1차 모델**을 그대로 조작화한 것이다. 2차 모델(cross-encoder/NLI),
VLM, Human Final 은 범위 밖이다.

## 2. 가설 판정 요약

| 가설 | 내용 | 판정 | 근거 한 줄 |
|---|---|---|---|
| **H-RF001-C-EMBED-PROTOTYPE** | prototype 유사도만으로 zero-shot 으로 prior 를 stratified baseline 보다 잘 되찾는다 | **PARTIALLY_SUPPORTED** | 9 config 중 8개가 stratified p95 를 넘지만(PRIMARY macro F1 0.497 vs p95 0.221), 문구 세트를 바꾸면 한 모델(e5-small)에서 판정이 뒤집히고 UTILITY_ENTRY 는 0/5 로 전멸한다 |
| **H-C-null** | prototype 유사도는 baseline 과 구분되지 않는다 | **REFUTED** | PRIMARY macro F1 0.497, stratified 예측기 대비 p<5e-5 (20000 draw 중 0회 초과), 라벨 순열 검정 p<5e-5 |
| **H-C-length** | 유사도가 archetype 이 아니라 텍스트 길이/도메인 어휘밀도를 재고 있다 | **PARTIALLY_SUPPORTED** | 길이 자체에 진짜 신호가 있다(길이만 쓰는 LOO 분류기 macro F1 0.252 > stratified p95 0.221). 그러나 길이 tertile 내부에서만 라벨을 섞은 귀무분포(null mean 0.134, p95 0.202)를 PRIMARY 0.497 이 크게 넘어(p=5.0e-5) **길이가 임베딩 신호를 설명하지 못한다** |
| **H-C-prototype** | 성능이 prototype 문구 선택에 민감해서 문구를 바꾸면 결론이 뒤집힌다 | **SUPPORTED** | 9 config macro F1 범위 0.198~0.497 (폭 0.299). e5-small 은 set A 0.443 → set B 0.198 로 기준선 통과 판정 자체가 뒤집힌다. 같은 모델 안에서 세트 간 예측 일치 Cohen κ = 0.12~0.52 |

---

## 3. 입력 · 분석단위 · N

- **입력**: `research_d/results/D_TEXT_CORPUS.csv` 의 `text_blob`.
  SSOT 01 §7 Text representation(title · headings · landmark labels · accessible names ·
  form labels · card descriptors · URL path tokens)을 그대로 이어붙인 필드다. 다른 필드는 쓰지 않았다.
- **분석단위**: target state 1행 = web target 1개 (`in_mart == 1`).
- **N**: **n_observed = 56 / n_expected = 59**. 3건은 mart 밖이라 이 실험에 들어오지 않았다.
- **target 변수**: `prior_archetype`. **gold label 이 아니라 business-domain prior 다.**
  따라서 지표를 accuracy 라 부르지 않고 **prior_agreement** 로 부른다. 불일치가 모델 오류인지
  prior 오류인지 이 실험은 **구분할 수 없다.**

### class 분포 (분모)

| archetype | n | 비율 |
|---|---:|---:|
| ITEM_DETAIL | 26 | 26/56 |
| FINANCIAL_ACTION_ENTRY | 10 | 10/56 |
| UTILITY_ENTRY | 5 | 5/56 |
| COMMUNICATION_ENTRY | 4 | 4/56 |
| PLACE_LOOKUP | 4 | 4/56 |
| QUERY | 4 | 4/56 |
| CONTENT_OPEN | 3 | 3/56 |

**7개 중 5개 class 가 n ≤ 5 다.** 이 class 들의 recall 은 사실상 "5번 중 몇 번" 이고
Wilson 95% CI 폭이 0.4~0.9 에 이른다. 아래 per-class 수치를 성능 서열로 읽으면 안 된다.

### 입력 품질 결함 (성능 상한을 누르는 실물 결함)

| 결함 | n / 56 | 대상 |
|---|---:|---|
| 완전 중복 blob | 2 | NH스마트뱅킹 · NH콕뱅크 (같은 DOM, 둘 다 FINANCIAL) |
| 인코딩 깨짐(mojibake) 의심 | 7 | KB Pay · V3 Mobile Plus · YouTube · 내 파일 · 디바이스 케어 · 메가커피 · 탑마트 |
| 사실상 URL 만 (≤12 토큰) | 6 | NH스마트뱅킹 · NH콕뱅크 · YouTube · 롯데하이마트 · 신한 SOL뱅크 · 하나은행 |
| blob_tokens | min 5 / p25 43 / median 132 / p75 312 / max 945 | 178배 차이 |

카카오톡 row 의 title 은 `Page not found | Kakao` 다. 즉 일부 target 은 텍스트 자체가
대표 surface 를 담고 있지 않다.

---

## 4. Prototype 문장 전문 (3세트)

**출처 규율**: 세 세트 모두 SSOT 00 §4 archetype 목록과 SSOT 01 §5 Stage-3 branch 정의(질문 +
Region + Endpoint)에서만 유도했다. `D_TEXT_CORPUS` 를 읽고 문구를 맞추지 않았고, **결과를 본 뒤에도
수정하지 않았다.** 코드 상수로 고정돼 있다 (`rf001_c_embedding.py`).

### Set A — `A_SSOT_DEF` (SSOT 정의문 축약형) — **PRIMARY**

```
QUERY
사용자가 검색 입력창에 자유 텍스트 질의를 입력하고 제출하여 검색 결과 목록 상태로 전환하는 것이
대표행동이다. 검색 입력 control, 검색 form, 검색 제출 버튼이 대표 표면이다.
search box, search form, submit query, search results.

CONTENT_OPEN
이미 존재하는 기사, 영상, 콘텐츠 한 건을 목록에서 선택해 본문을 열거나 재생을 시작하는 것이
대표행동이다. 콘텐츠 카드 목록, 기사 본문, 미디어 재생이 대표 표면이다.
article body, news, video playback, content card list.

ITEM_DETAIL
거래 대상 상품 한 건의 상세면에 들어가 상품명, 가격, 거래 control 의 존재를 확인하는 것이
대표행동이다. 반복되는 상품 카드 목록과 상품 상세 문서가 대표 표면이다.
product name, price, cart, order, shopping mall, item detail page.

PLACE_LOOKUP
장소를 질의하거나 특정 장소의 상세면을 여는 것이 대표행동이다. 장소 검색 control, 장소 목록,
지도, 주소, 장소 상세 패널이 대표 표면이다. map, place search, address, location, route, navigation.

COMMUNICATION_ENTRY
사람 사이의 게시물, 스레드, 메시지를 교환하는 공간에 진입하는 것이 대표행동이다. 스레드 목록,
게시글 목록, 글쓰기 진입 control, 실제 로그인 gate 가 대표 표면이다.
message, chat, post, thread, community, social feed, comment.

FINANCIAL_ACTION_ENTRY
금융처리 기능의 시작면을 열거나 그 기능을 시작하기 위해 필요한 실제 로그인 및 본인인증 gate 까지
진입하는 것이 대표행동이다. 잔액 조회, 이체, 송금, 결제, 카드, 보험, 인증 기능 진입 control 이
대표 표면이다. bank, transfer, payment, balance, card, insurance, login, identity verification.

UTILITY_ENTRY
특정 목적의 도구 기능면을 열고 첫 primary control 을 사용할 수 있는 상태로 만드는 것이
대표행동이다. 단일 목적 기능 진입 control 과 그 기능 화면이 대표 표면이다.
utility tool, service function, apply, reserve, issue, lookup, settings.
```

### Set B — `B_USER_BEHAVIOR` (같은 정의를 1인칭 사용자 행동 서술로 재작성)

```
QUERY                   나는 궁금한 것을 검색창에 입력하고 검색 버튼을 눌러 결과 목록을 본다.
CONTENT_OPEN            나는 목록에서 기사나 영상 하나를 골라 눌러서 읽거나 본다.
ITEM_DETAIL             나는 사고 싶은 물건 하나를 눌러 상세 화면에서 가격과 정보를 확인한다.
PLACE_LOOKUP            나는 가려는 장소를 찾아보고 그 장소의 위치와 상세 정보를 확인한다.
COMMUNICATION_ENTRY     나는 다른 사람이 올린 글이나 메시지를 보러 대화 공간에 들어간다.
FINANCIAL_ACTION_ENTRY  나는 은행이나 카드 업무를 시작하려고 로그인 화면까지 들어간다.
UTILITY_ENTRY           나는 필요한 기능 하나를 열어서 바로 쓸 수 있는 상태까지 간다.
```

### Set C — `C_TERSE_LABEL` (archetype 이름의 최소 gloss, 문장이 아니라 라벨에 가까움)

```
QUERY                   검색 질의 search query
CONTENT_OPEN            콘텐츠 열람 content open article video
ITEM_DETAIL             상품 상세 item detail product price
PLACE_LOOKUP            장소 조회 place lookup map location
COMMUNICATION_ENTRY     커뮤니케이션 진입 communication message post
FINANCIAL_ACTION_ENTRY  금융 기능 진입 financial action bank payment
UTILITY_ENTRY           도구 기능 진입 utility function tool
```

---

## 5. 방법

1. `text_blob` 을 그대로 인코딩. 문서를 자르거나 요약하지 않았다.
2. prototype 7문장을 같은 모델로 인코딩.
3. 둘 다 L2 정규화 → 내적 = cosine. `argmax` 가 top1, 두 번째가 top2, `margin = s1 - s2`.
4. **학습 없음.** 어떤 파라미터도 `prior_archetype` 으로 적합하지 않았다. train/test split 도 없다
   (fit 할 것이 없으므로). 출력은 항상 7 archetype 안이다 — 코드에서 assert 로 강제한다.
5. 모델은 **로컬 HF 캐시만** 사용 (`HF_HUB_OFFLINE=1`, `TRANSFORMERS_OFFLINE=1`). 네트워크 없음.

### 모델 3종과 prefix 규약

| 모델 | dim | max_seq_length | prefix 규약 | 문서 subword median / max | **잘린 문서 수** |
|---|---:|---:|---|---|---:|
| `BAAI/bge-m3` | 1024 | 8192 | **없음** (bge-m3 공식 규약: instruction prefix 미사용) | 546 / 2907 | **0 / 56** |
| `intfloat/multilingual-e5-small` | 384 | 512 | **PRIMARY = 비대칭**: prototype `"query: "`, page `"passage: "` | 546 / 2907 | **30 / 56** |
| `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` | 384 | **128** | 없음 | 546 / 2907 | **48 / 56** |

e5 prefix 규약은 **지켰다.** 추가로 대칭 변형(`"query: "` / `"query: "`)도 돌려 ablation 으로 기록했고,
세 세트 모두 비대칭이 더 좋았다 (Δmacro F1 −0.028 / −0.056 / −0.112, 대칭이 항상 열세).

**MiniLM 은 56건 중 48건이 128 토큰에서 잘린다.** MiniLM 의 성능은 "blob 앞 128 subword 만 보고 낸
성능" 으로 읽어야 한다.

### 사전 등록(pre-registration)

코드 헤더에 명시했다: **PRIMARY = `bge-m3 × A_SSOT_DEF`**. 이유는 (a) bge-m3 만 blob 전체를
자르지 않고, (b) set A 가 SSOT 정의문에서 가장 직접 유도된 세트이기 때문이다. **결과를 보고 고르지
않았다.** 나머지 8 config 은 전부 민감도 분석이다.

### 기준선

- **majority** — 항상 ITEM_DETAIL: prior_agreement **26/56 = 0.464**, macro F1 **0.091**, weighted F1 0.294.
  majority 는 prior_agreement 는 높고 macro F1 은 바닥이다. **macro F1 에서 majority 대비 lift 는
  rigged 이므로 판정에 쓰지 않는다.**
- **stratified (판정 기준선)** — 관측 class marginal 에서 예측을 무작위 추출, 20000 draw:
  prior_agreement mean **0.273** (95% 구간 0.161–0.375, p95 0.357),
  macro F1 mean **0.139** (sd 0.045, 95% 구간 0.065–0.238, **p95 0.221**).
- **라벨 순열 검정** — 예측 벡터를 고정하고 라벨을 20000회 섞은 귀무분포.

---

## 6. 결과 — 9 config (3 model × 3 prototype set), n=56

| config | prior_agreement | macro F1 | weighted F1 | top-2 hit | p vs stratified 예측기 | p 순열 | stratified p95 통과 | 예측된 class 수 |
|---|---:|---:|---:|---:|---:|---:|:--:|---:|
| **bge-m3 \| A_SSOT_DEF (PRIMARY)** | **37/56 = 0.661** | **0.497** | 0.649 | 45/56 | <5e-5 | <5e-5 | ✅ | 6/7 |
| bge-m3 \| C_TERSE_LABEL | 33/56 = 0.589 | 0.463 | 0.592 | 43/56 | <5e-5 | <5e-5 | ✅ | 7/7 |
| bge-m3 \| B_USER_BEHAVIOR | 33/56 = 0.589 | 0.355 | 0.549 | 44/56 | 1.0e-4 | <5e-5 | ✅ | 6/7 |
| minilm \| A_SSOT_DEF | 33/56 = 0.589 | 0.492 | 0.606 | 41/56 | <5e-5 | <5e-5 | ✅ | 7/7 |
| minilm \| B_USER_BEHAVIOR | 34/56 = 0.607 | 0.488 | 0.631 | 44/56 | <5e-5 | <5e-5 | ✅ | 7/7 |
| minilm \| C_TERSE_LABEL | 25/56 = 0.446 | 0.422 | 0.441 | 29/56 | <5e-5 | <5e-5 | ✅ | 7/7 |
| e5-small \| A_SSOT_DEF | 28/56 = 0.500 | 0.443 | 0.529 | 34/56 | <5e-5 | <5e-5 | ✅ | 6/7 |
| e5-small \| C_TERSE_LABEL | 29/56 = 0.518 | 0.371 | 0.522 | 40/56 | 1.0e-4 | <5e-5 | ✅ | 5/7 |
| **e5-small \| B_USER_BEHAVIOR** | 14/56 = 0.250 | **0.198** | 0.293 | 38/56 | **0.106** | <5e-5 | ❌ | 4/7 |

- PRIMARY prior_agreement Wilson 95% CI = **[0.530, 0.771]**.
- **8 / 9 config 이 stratified p95(0.221)를 넘는다.** 넘지 못한 하나는 e5-small × set B.
- 순열 검정은 9개 모두 통과하지만, 순열 귀무는 stratified 예측기 귀무보다 관대하다.
  **판정은 stratified 기준으로 한다.**

### 모델 3종 비교 — 결론이 갈리는 지점

- **집계 성능은 bge-m3 ≈ minilm > e5-small.** 그런데 minilm 은 56건 중 48건을 128 토큰에서 자르고도
  set A 에서 0.492 를 낸다. 즉 **이 과제의 신호 대부분이 blob 앞머리(title/meta/headings)에 있다.**
  전체 문서를 읽는 것이 크게 이득이 아니다 — 이건 "긴 DOM 텍스트를 다 넣어야 한다"는 직관을 부정하는
  결과이며, production 에서 모델 크기를 낮출 여지를 시사한다.
- **문구 견고성은 정반대 순서다.** 세트 간 macro F1 범위: minilm 0.070 < bge-m3 0.142 < e5-small 0.244.
  e5-small 만 판정이 뒤집힌다.
- **margin 의 신뢰도로서의 가치는 bge-m3 만 쓸 만하다** (§9).

---

## 7. PRIMARY per-class (bge-m3 × A_SSOT_DEF), n=56

| archetype | support | 예측 건수 | recall | recall Wilson 95% | precision | precision Wilson 95% | F1 |
|---|---:|---:|---|---|---|---|---:|
| ITEM_DETAIL | 26 | 19 | 18/26 = 0.692 | [0.501, 0.833] | 18/19 = 0.947 | [0.754, 0.991] | 0.800 |
| FINANCIAL_ACTION_ENTRY | 10 | 13 | 10/10 = 1.000 | [0.722, 1.000] | 10/13 = 0.769 | [0.497, 0.918] | 0.870 |
| **UTILITY_ENTRY** | 5 | **0** | **0/5 = 0.000** | **[0.000, 0.434]** | 0/0 = 정의 불가 | — | **0.000** |
| COMMUNICATION_ENTRY | 4 | 7 | 3/4 = 0.750 | [0.301, 0.954] | 3/7 = 0.429 | [0.158, 0.750] | 0.545 |
| PLACE_LOOKUP | 4 | 8 | 3/4 = 0.750 | [0.301, 0.954] | 3/8 = 0.375 | [0.135, 0.694] | 0.500 |
| QUERY | 4 | 7 | 2/4 = 0.500 | [0.150, 0.850] | 2/7 = 0.286 | [0.084, 0.641] | 0.364 |
| CONTENT_OPEN | 3 | 2 | 1/3 = 0.333 | [0.061, 0.792] | 1/2 = 0.500 | [0.094, 0.906] | 0.400 |

**정직하게**: n≤5 인 5개 class 의 CI 는 거의 전 구간을 덮는다. "PLACE_LOOKUP recall 0.75" 는
**4건 중 3건**이라는 뜻일 뿐이며 0.30 일 수도 0.95 일 수도 있다. 신뢰할 만한 추정치는 support 가
있는 ITEM_DETAIL(26)과 FINANCIAL_ACTION_ENTRY(10) 둘뿐이다.

### 혼동행렬 (행 = prior, 열 = 예측)

```
                        QUERY  CONTEN  ITEM_D  PLACE_  COMMUN  FINANC  UTILIT
QUERY                       2       0       1       1       0       0       0
CONTENT_OPEN                1       1       0       0       1       0       0
ITEM_DETAIL                 2       1      18       3       2       0       0
PLACE_LOOKUP                0       0       0       3       0       1       0
COMMUNICATION_ENTRY         0       0       0       1       3       0       0
FINANCIAL_ACTION_ENTRY      0       0       0       0       0      10       0
UTILITY_ENTRY               2       0       0       0       1       2       0
```

**가장 중요한 구조적 결함: UTILITY_ENTRY 열이 전부 0 이다.** PRIMARY 는 56건 어디에도
UTILITY_ENTRY 를 예측하지 않았다. 5건은 QUERY(2) · FINANCIAL(2) · COMMUNICATION(1)로 흩어졌다.
"특정 목적의 도구 기능면" 이라는 정의는 다른 여섯 정의의 상위개념에 가까워서 임베딩 공간에서
고유한 방향을 갖지 못한다. **이건 데이터 부족이 아니라 SSOT 정의의 embedding-separability 문제다.**

FINANCIAL_ACTION_ENTRY 는 recall 10/10 로 완벽하지만 precision 은 10/13 — 은행 어휘가 워낙 특징적이라
쉬운 class 이고, 대신 다른 class 를 3건 빨아들인다.

---

## 8. H-C-length — 길이 교란 검정

### 8.1 길이 자체에 신호가 있는가 → **있다**

archetype 별 blob_tokens 중앙값:

| archetype | n | tokens median |
|---|---:|---:|
| QUERY | 4 | 337 |
| PLACE_LOOKUP | 4 | 191 |
| ITEM_DETAIL | 26 | 179 |
| COMMUNICATION_ENTRY | 4 | 105 |
| CONTENT_OPEN | 3 | 56 |
| UTILITY_ENTRY | 5 | 37 |
| FINANCIAL_ACTION_ENTRY | 10 | **25** |

금융 랜딩은 텍스트가 거의 없고(중앙값 25 토큰) 쇼핑·검색 랜딩은 길다. 그래서
**길이만 쓰는 분류기**(log1p(blob_tokens) 위 LOO nearest-class-mean)가
prior_agreement **14/56 = 0.250**, macro F1 **0.252** 를 낸다 — stratified p95(0.221)를 넘는다.
**길이는 진짜 교란변수다. 무시할 수 없다.**

### 8.2 그런데 길이가 임베딩 신호를 설명하는가 → **아니다**

**길이 tertile 내부에서만 라벨을 섞은 순열 귀무분포**(길이-라벨 연관을 보존):

| 항목 | 값 |
|---|---|
| 귀무 macro F1 mean | 0.134 |
| 귀무 macro F1 p95 | 0.202 |
| PRIMARY 관측 macro F1 | **0.497** |
| p | **5.0e-5** (20000 순열 중 0회 초과) |
| 판정 | **길이 통제 후에도 신호가 남는다** |

**9 config 전부** 길이 통제 순열에서 p < 5e-5 로 살아남았다 (macro F1 0.198 인 e5-small×B 포함).

### 8.3 그래도 남는 길이 의존성 — 정직하게

PRIMARY 의 prior_agreement 는 길이 tertile 을 따라 **단조 증가**한다:

| tertile | 토큰 범위 | n | prior_agreement | Wilson 95% |
|---|---|---:|---|---|
| T1_short | 5–66 | 19 | 10/19 = 0.526 | [0.317, 0.727] |
| T2_mid | 73–238 | 18 | 12/18 = 0.667 | [0.437, 0.837] |
| T3_long | 243–945 | 19 | 15/19 = 0.789 | [0.567, 0.915] |

세 CI 가 크게 겹치므로 이 기울기 자체는 통계적으로 강하지 않다. 방향은 "텍스트가 많을수록 잘 맞춘다"
= **evidence 양의 효과**로 읽는 것이 자연스럽고, "길이가 라벨의 대리변수" 라는 해석과는 다르다.
그러나 두 해석을 이 데이터로 완전히 분리할 수는 없다.

상관은 config 마다 방향이 뒤집힌다 (Spearman ρ(tokens, top1_sim): bge-m3×A −0.069, minilm×A +0.363,
minilm×C −0.323). **길이-유사도 상관은 안정적 현상이 아니다.** 정답 여부와 토큰 수의
Mann-Whitney 는 PRIMARY 에서 p=0.158 (중앙값 정답 177 vs 오답 81) 로 유의하지 않다.

**H-C-length 판정 = PARTIALLY_SUPPORTED**: 길이는 실제 교란변수지만, 관측된 임베딩 성능을
설명하기에는 한참 부족하다 (0.252 vs 0.497).

---

## 9. H-C-prototype — 문구 민감도

### 9.1 정량

| 모델 | set A | set B | set C | 범위 | 기준선 통과 판정 뒤집힘 |
|---|---:|---:|---:|---:|:--:|
| bge-m3 | 0.497 | 0.355 | 0.463 | 0.142 | 아니오 (3/3 통과) |
| minilm | 0.492 | 0.488 | 0.422 | 0.070 | 아니오 (3/3 통과) |
| **e5-small** | 0.443 | **0.198** | 0.371 | **0.244** | **예 (set B 만 실패)** |
| **9 config 전체** | min 0.198 · max 0.497 | | | **0.299** | 8/9 통과 |

### 9.2 예측 자체가 얼마나 흔들리는가 (같은 모델, 세트만 교체)

| 비교 | Cohen κ | 원시 예측 일치 |
|---|---:|---:|
| minilm A~B | 0.522 | 34/56 = 0.607 |
| bge-m3 A~B | 0.477 | 34/56 = 0.607 |
| bge-m3 A~C | 0.444 | 32/56 = 0.571 |
| minilm A~C | 0.464 | 31/56 = 0.554 |
| minilm B~C | 0.393 | 27/56 = 0.482 |
| bge-m3 B~C | 0.368 | 30/56 = 0.536 |
| e5-small A~C | 0.248 | 21/56 = 0.375 |
| e5-small B~C | 0.179 | 27/56 = 0.482 |
| **e5-small A~B** | **0.116** | 11/56 = 0.196 |

**같은 모델, 같은 페이지, 같은 SSOT 정의에서 유도한 문구인데 예측의 40~50% 가 바뀐다.**
가장 좋은 경우조차 κ=0.52 (moderate) 다.

**H-C-prototype 판정 = SUPPORTED.** prototype 문구는 하이퍼파라미터이며, 지금은 **calibrate 되지 않은
자유도**다. 문구를 고정하지 않고 이 방법을 production 에 넣는 것은 재현 불가능한 시스템을 넣는 것이다.

부수 소견: **1인칭 사용자 행동 서술(set B)이 항상 나쁜 것은 아니다** — minilm 에서는 set A 와 사실상
동률(0.488 vs 0.492)이다. 즉 "어떤 문구가 좋은가" 는 모델과 상호작용하며, 모델 독립적인 최적 문구는
이 실험에서 확인되지 않았다.

---

## 10. Abstention — margin-coverage 곡선 (임계 미선언)

SSOT 01 §7 은 threshold 를 **independent label calibration split** 에서 정하라고 규정한다.
이 worker 는 gold label 과 holdout 에 접근할 수 없다. 따라서 **임계를 선언하지 않고 곡선만 제출한다.**
아래 표의 어떤 행도 운영 기준이 아니다.

### PRIMARY (bge-m3 × A_SSOT_DEF) margin 임계별

| margin ≥ | coverage n | coverage | abstention | prior_agreement (분모 포함) | Wilson 95% |
|---:|---:|---:|---:|---|---|
| 0.0000 | 56 | 1.000 | 0.000 | 37/56 = 0.661 | [0.53, 0.77] |
| 0.0010 | 50 | 0.893 | 0.107 | 34/50 = 0.680 | [0.54, 0.79] |
| 0.0028 | 45 | 0.804 | 0.196 | 31/45 = 0.689 | [0.54, 0.80] |
| 0.0056 | 40 | 0.714 | 0.286 | 31/40 = 0.775 | [0.62, 0.88] |
| 0.0097 | 35 | 0.625 | 0.375 | 29/35 = 0.829 | [0.67, 0.92] |
| **0.0167** | **30** | **0.536** | **0.464** | **27/30 = 0.900** | [0.74, 0.97] |
| 0.0327 | 20 | 0.357 | 0.643 | 18/20 = 0.900 | [0.70, 0.97] |
| 0.0436 | 15 | 0.268 | 0.732 | 13/15 = 0.867 | [0.62, 0.96] |
| 0.0610 | 5 | 0.089 | 0.911 | 5/5 = 1.000 | [0.57, 1.00] |

margin 분포: p10 = 0.0011, median = 0.0190, p90 = 0.0600. top1 cosine 중앙값 0.481.
**top-2 안에 prior 가 들어오는 비율은 45/56 = 0.804** — 2차 모델(cross-encoder)이 top-2 만 재순위해도
상한 0.80 을 볼 수 있다는 뜻이다.

### margin 이 신뢰도로 작동하는가 — 모델별로 다르다

고정 coverage 에서의 prior_agreement (set A):

| 모델 | cov 56 (100%) | cov 42 (75%) | cov 28 (50%) | cov 14 (25%) |
|---|---|---|---|---|
| bge-m3 | 37/56 = 0.66 | 31/42 = 0.74 | **25/28 = 0.89** | 12/14 = 0.86 |
| minilm | 33/56 = 0.59 | 27/42 = 0.64 | 19/28 = 0.68 | 11/14 = 0.79 |
| e5-small | 28/56 = 0.50 | 21/42 = 0.50 | 15/28 = 0.54 | 11/14 = 0.79 |

**bge-m3 의 margin 만 유용한 신뢰도다.** e5-small 은 coverage 를 절반으로 줄여도 0.50 → 0.54 로
거의 개선되지 않는다 — **abstention 을 붙여도 못 고친다.**

### 실용적 시사 한 줄

bge-m3 기준으로 **abstention 을 약 46% 까지 올리면 남는 54% 에서 prior_agreement 0.90 (27/30)에
도달**하지만, 이건 "56건 중 30건만 자동 처리" 라는 뜻이고 그 임계값은 **label calibration split 에서
다시 정해져야 한다**.

---

## 11. 반례 (counterexample)

### 11.1 확신이 높은데 틀린 사례 — abstention 이 못 잡는 오류

margin 상위권에서 틀린 건이 존재한다:

| target | prior | 예측 | margin | 비고 |
|---|---|---|---:|---|
| **당근** | COMMUNICATION_ENTRY | PLACE_LOOKUP | **0.0576 (전체 p90 이상)** | 지역/동네 어휘가 place 어휘와 충돌. **margin 최댓값 근처의 오류** |
| **캐시워크** | UTILITY_ENTRY | FINANCIAL_ACTION_ENTRY | 0.0470 | 리워드/포인트 어휘가 금융으로 흡수 |
| 다음 | QUERY | PLACE_LOOKUP | 0.0221 | 포털 랜딩의 지도/장소 모듈이 검색창을 이김 |
| 카카오T | PLACE_LOOKUP | FINANCIAL_ACTION_ENTRY | 0.0167 | 결제 어휘가 place 어휘를 이김 |

margin 0.0436 이상(n=15)에서도 오답 2건(당근·캐시워크)이 남는다. **margin 은 오류를 줄이지만
제거하지 못한다.**

### 11.2 도메인 어휘가 archetype 을 삼키는 체계적 패턴

- **ITEM_DETAIL → PLACE_LOOKUP 3건** (배달의민족 · 탑마트 · 11번가): 배송지/매장/주소 어휘.
- **ITEM_DETAIL → COMMUNICATION_ENTRY 2건** (다이소 · 쿠팡이츠): 고객문의/입점문의/브랜드스토리 어휘.
- **UTILITY_ENTRY → 전멸 5건**: §7 참조.

이는 SSOT 01 §1 이 경고한 그대로다 — **business domain 어휘와 observed task shape 가 충돌하면
observed task shape 를 우선해야 하는데, 임베딩 유사도는 그 우선순위를 표현할 수단이 없다.**

### 11.3 텍스트가 없으면 결과도 없다

- **YouTube** (blob 11 토큰, mojibake) → CONTENT_OPEN 인데 QUERY 로 예측, margin 0.003.
- **카카오톡** 의 blob 은 `Page not found | Kakao` 로 시작한다.
- **NH스마트뱅킹 / NH콕뱅크** 는 blob 이 완전히 동일 — 임베딩상 구분 불가능한 두 target 이다
  (둘 다 FINANCIAL 이라 우연히 둘 다 맞았다).

---

## 12. VERDICT

### **PARTIALLY_SUPPORTED**

SSOT 정의에서 유도한 prototype 과의 임베딩 유사도는 **판정 기준선(stratified)을 명확히 그리고
반복적으로 넘는다** — 9 config 중 8개, PRIMARY 는 macro F1 0.497 vs 귀무 p95 0.221, p<5e-5.
길이 교란을 통제해도 살아남는다. **H-C-null 은 REFUTED 다.**

그러나 **SUPPORTED 로 올릴 수 없는 이유가 세 가지 있다**:

1. **문구 민감도가 통제되지 않았다** (H-C-prototype SUPPORTED). 같은 SSOT 정의에서 유도한 다른 문구로
   예측의 40~50% 가 바뀌고, e5-small 에서는 기준선 통과 판정 자체가 뒤집힌다.
2. **7 class 중 1개(UTILITY_ENTRY, n=5)가 구조적으로 전멸한다.** 예측조차 되지 않으므로 이 방법은
   현재 사실상 6-class 분류기다.
3. **target 이 gold label 이 아니다.** prior_agreement 0.661 의 불일치 19건이 모델 오류인지 prior
   오류인지 이 실험은 구분할 수 없다. "정확도 66%" 라는 문장은 이 데이터로 쓸 수 없다.

**causal claim 없음.** 임베딩 유사도가 archetype 을 "결정" 한다거나, 낮은 유사도가 접근성 결함을
"유발" 한다는 주장은 하지 않는다. 관측된 것은 연관뿐이다.

---

## 13. Limitation

1. **n=56 에 7 class, 5개 class 가 n≤5.** per-class Wilson CI 폭이 0.4~0.9. macro F1 은 소수 class 에
   지배되므로 재수집 시 크게 흔들릴 수 있다.
2. **target = business-domain prior ≠ gold label.** 불일치의 귀책이 모델인지 prior 인지 분리 불가.
   `prior_archetype` 자체가 SSOT 01 Layer P 산출물이며 Layer O 검증을 거치지 않았다.
3. **입력 DOM 품질 결함이 상한을 누른다**: 중복 blob 2건, mojibake 의심 7건, 사실상 URL only 6건,
   404 페이지 1건. 최소 12/56 이 대표 surface 를 담지 못한다.
4. **prototype 문구가 calibrate 되지 않은 자유도.** 세 세트 모두 SSOT 유도이지만 어느 것이 "옳은"
   조작화인지 정할 근거가 이 실험 안에 없다. 세트를 더 만들수록 최댓값은 낙관 편향된다.
5. **MiniLM 은 56건 중 48건이 잘렸고 e5-small 은 30건이 잘렸다.** 모델 비교는 "동일 조건 비교" 가
   아니라 "각 모델의 실제 운용 조건 비교" 다.
6. **threshold 미정.** margin 곡선의 어떤 지점도 운영 기준이 아니다. calibration split 없이 임계를
   고르면 이 문서의 곡선에 과적합된다.
7. **1차 모델만 검정했다.** SSOT §7 의 2차 모델(cross-encoder/NLI), VLM, Human Final 은 미검증.
8. Spearman/Mann-Whitney 의 p 는 정규 근사이며 n=56 에서 정확 검정이 아니다. macro F1 관련 판정은
   전부 20000회 재추출 기반이라 근사에 의존하지 않는다.

---

## 14. Production implication

**지금 이대로 production 에 넣으면 안 된다.** 그러나 SSOT 01 §7 이 설계한 자리 — "DT 가 못 닫은
소수 ambiguity 만 해결" — 에는 쓸 수 있는 신호가 있다. 구체적으로:

1. **단독 분류기로 쓰지 말 것.** prior_agreement 0.661 (37/56) 은 대표기능 매핑의 단독 근거가 될
   수 없고, SSOT 01 §6 evidence precedence 에서 임베딩은 4순위 prior 수준의 증거다.
2. **DT 가 2개 이상 강한 후보를 남긴 경우에만, top-2 재순위 용도로.** top-2 hit 45/56 = 0.804 는
   후보 축소기로서의 유용성을 시사한다.
3. **prototype 문구를 SSOT 문서에 문자열로 동결(freeze)하고 버전을 매길 것.** 지금은 문구가 코드
   상수이고, 문구를 바꾸면 시스템이 바뀐다. 문구는 코드가 아니라 **SSOT 정의물**로 취급해야 한다.
4. **UTILITY_ENTRY 는 임베딩 fallback 으로 절대 확정하지 말 것.** 이 방법은 UTILITY_ENTRY 를
   예측하지 않는다. UTILITY 후보는 Rule DT 또는 `AMBIGUOUS_UNRESOLVED` 로 보내야 한다.
5. **모델을 고른다면 bge-m3.** 성능 때문이 아니라(minilm 과 macro F1 0.005 차) **margin 이 신뢰도로
   작동하는 유일한 모델이기 때문이다.** abstention 을 붙일 계획이면 이게 결정적이다.
   반대로 abstention 없이 top-1 만 쓸 거면 minilm(128 토큰, 118MB)로 충분하다.
6. **e5-small 은 이 과제에 권장하지 않는다.** 문구 민감도가 가장 크고 margin 이 신뢰도로 동작하지 않는다.
7. **threshold 는 C 가 independent label calibration split 에서 정해야 한다.** 이 문서는 곡선만 제공한다.

---

## 15. 추가 연구질문

- **RQ-C1**: prototype 문구를 SSOT 정의문 하나로 고정하는 대신, archetype 당 k개 문장의 **centroid**
  를 쓰면 문구 민감도(κ 0.12~0.52)가 줄어드는가? — 별도 child run 필요 (기존 run 덮어쓰기 금지).
- **RQ-C2**: UTILITY_ENTRY 가 임베딩 공간에서 고유 방향을 갖지 못하는 것이 정의의 문제인가 데이터의
  문제인가? prototype 을 뺀 6-class 문제로 재실험하면 나머지 class 의 precision 이 오르는가?
- **RQ-C3**: `text_blob` 전체 대신 **field 별 임베딩**(title / headings / buttons / url_tokens 만)이
  더 나은가? minilm 이 128 토큰만 보고도 0.492 를 낸 사실은 앞머리 field 가 대부분의 신호를
  가진다는 뜻이다.
- **RQ-C4**: SSOT §7 의 **2차 모델** — top-2 가 가까운 11~26건에만 cross-encoder/NLI 를 태우면
  top-2 hit 0.804 중 얼마를 top-1 로 바꿀 수 있는가?
- **RQ-C5**: 입력 품질(중복 blob · mojibake · URL only 12/56)을 고친 뒤 같은 실험을 반복하면
  prior_agreement 가 얼마나 오르는가? 즉 지금 관측된 0.661 중 얼마가 **수집 결함의 상한**인가?
- **RQ-C6**: prior_archetype 대신 Layer O(관측된 DOM/AX 구조)로 검증된 라벨을 target 으로 쓰면
  같은 방법의 성능이 오르는가 내리는가? — **gold label 이 존재할 때만 가능. 이 worker 범위 밖.**
- **RQ-C7**: 이 실험은 zero-shot 이다. 학습(예: prototype 을 fit)을 한다면 **반드시 새 hypothesis_id
  로 새 child run** 을 만들어야 하며, 이 run 과 같은 계열로 비교하면 안 된다 (누수 위험).

---

## 부록 — 산출 파일

| 파일 | 내용 |
|---|---|
| `research_d/tools/rf001_c_embedding.py` | 전체 실험 코드. Restart→Run All 재현 가능, seed 20260827 |
| `research_d/results/RF001_C_embedding.json` | 전 수치 (최상위 `verdict` 키 포함, assertion 6건) |
| `research_d/results/RF001_C_FINDINGS.md` | 이 문서 |
| `research_d/figures/RF001_C_margin_coverage.png` | margin-coverage 곡선 + margin 분포 (3 모델) |
| `research_d/figures/RF001_C_model_prototype_grid.png` | 3×3 macro F1 그리드 vs stratified 기준선 |
| `research_d/figures/RF001_C_length_confound.png` | 길이 vs margin / 유사도 / tertile 별 agreement |
| `research_d/figures/RF001_C_confusion_primary.png` | PRIMARY 혼동행렬 |
| MLflow run `bd04b82fa1104cd3a93283b40f2dd5cb` | 전 metric · `prototype_definitions.txt` · 4개 그림 · `result/RF001_C_predictions.csv` (target 별 9 config 예측 + margin) |

**규율 준수 확인**: gold label 미생산 · holdout 미열람 (`**/control/label/**`,
`LABEL_SPLIT_FROZEN.json` 미접근) · REAL_TARGET 미접속 · 네트워크 다운로드 없음
(`HF_HUB_OFFLINE=1`, `TRANSFORMERS_OFFLINE=1`) · production 경로 미수정 · git 명령 미실행 ·
threshold 미선언 · 출력이 7 archetype 밖으로 나가지 않음 · **결과를 본 뒤 prototype 문구나 임계값을
수정하지 않음** (3세트 전부 사전 고정, 전부 보고).
