# D-RF2-C — Field-wise semantic ablation

| | |
|---|---|
| child_id | `D-RF2-C` |
| parent program | `RQ-D-RF-002` (parent run `ae754858ba3a4be391e5f811640d3fd8`) |
| hypothesis_id | `H-RF2-C-FIELD-INFORMATION` |
| **VERDICT** | **`PARTIALLY_SUPPORTED`** |
| plane / authority | D / `NON_CANONICAL` — 이 문서는 결정이 아니라 분석이다 |
| code | `tools/rf2_c_field_ablation.py` |
| result | `results/RF2_C_field_ablation.json` |
| notebook | `notebooks/d_research/RF2_C_field_ablation.ipynb` |
| seed | `20260827` (동일 코드 2회 실행 결과 JSON 바이트 동일 — `generated_at_kst` 제외) |

---

## 1. RQ

페이지의 semantic information 이 **정확히 어느 evidence field 에 있는가**.
반드시 답해야 하는 질문: **"전체 페이지 텍스트보다 primary controls / accessibility text 가
더 informative 한가?"**

**답: 아니다. 명확히 덜 informative 하다.** primary controls / accessibility text 계열은
22개 representation 중 하위 6위 안에 전부 모여 있고, 전체 텍스트(`text_blob`) 대비
macro F1 이 절반 수준이다. 자세한 근거는 §6·§9.

---

## 2. 가설 3개 판정

| 가설 | 판정 | 근거 |
|---|---|---|
| **H-C1** `text_blob` 전체가 최선이다 | **REFUTED** | PRIMARY(bge-m3×set A)에서 `title` 단독 macro F1 **0.559** > `identity` 0.556 > `text_blob` **0.509**. 22개 중 3위. |
| **H-C2** primary controls / accessibility text 가 더 informative 하다 | **NOT_SUPPORTED** | `primary_controls` 0.254 · `first_screen_interaction` 0.257 · `accessibility_text` 0.224 — 모두 `text_blob` 0.509 의 절반 이하이며 stratified p95(0.222)에 붙어 있다. |
| **H-C3** field 간 차이가 prototype 노이즈보다 작다 | **REFUTED** (단, e5-small 에서는 성립하지 않음) | bge-m3 between-field sd **0.128** vs between-prototype-set sd **0.038** (3.3배). minilm 0.142 vs 0.029 (4.9배). **e5-small 은 0.098 vs 0.103 으로 역전** — 작은 모델에서는 field 효과가 문구 노이즈에 묻힌다. |

**종합 VERDICT = `PARTIALLY_SUPPORTED`.** "field 마다 정보량이 다르다"는 강하게 성립하지만
(H-C3 REFUTED), 사전에 세운 방향 가설(H-C2)은 **정반대 방향으로** 기각됐고,
1위 field 의 우위는 §8 의 post-hoc 진단에서 상당 부분 **브랜드 식별 순환**으로 밝혀졌다.
즉 "어느 field 에 정보가 있는가"는 답했지만 "그 정보가 interaction semantics 인가"는
아직 닫히지 않았다.

---

## 3. 입력 · 분석단위 · N

| | |
|---|---|
| 입력 | `results/D_TEXT_CORPUS_v2.csv` (sha256 앞 16 = `ffab..` → JSON `inputs` 참조), `results/D_OBSERVATION_TABLE_v2.csv` |
| 대조 입력 | `results/D_TEXT_CORPUS.csv` (v1, 인코딩 결함본 — §10 에서만 사용) |
| 분석단위 | target (`in_mart == 1`), 1 target = 1 L0 landing state |
| N | **56** (`dom_found == 1` 이 56/56) |
| target 변수 | `prior_archetype` — **gold label 이 아니라 business-domain prior**. 따라서 지표명은 `prior_agreement` 이며 이 문서에 "accuracy" 라는 단어는 쓰지 않는다. |
| class n | ITEM_DETAIL 26 · FINANCIAL_ACTION_ENTRY 10 · UTILITY_ENTRY 5 · COMMUNICATION_ENTRY 4 · PLACE_LOOKUP 4 · QUERY 4 · CONTENT_OPEN 3 |

**n ≤ 5 인 class 가 4개**(UTILITY 5 / COMMUNICATION 4 / PLACE 4 / QUERY 4 / CONTENT 3 → 5개).
이들 class 의 recall Wilson 95% CI 폭은 0.3~0.9 로, 개별 class 수치는 **해석하지 않는다.**
macro F1 은 이 5개 class 에 5/7 의 가중치를 준다 — 이 점이 §6 의 순위를 흔드는 주요 요인이다.

### missing N
representation 별 empty 수는 §6 표의 `empty` 열. 전체 텍스트(`text_blob`)는 0/56 이지만
`form_labels` 39/56 · `placeholders` 34/56 · `input_names` 31/56 · `aria_labels` 20/56 이 비어 있다.

**빈 field 처리 규약(사전 등록)**: 빈 representation 은 `ABSTAIN` 으로 두고 **전체-56 분모에서
오답 처리**한다. 정보가 없으면 맞출 수 없기 때문이며, "자주 비는 field 는 production 에서 덜
informative 하다"는 사실을 지표가 흡수하게 하기 위해서다. 동시에 non-empty 부분집합의
조건부 수치도 자체 분모와 함께 §7 에 별도 보고한다.

### research firewall
holdout label · `LABEL_SPLIT_FROZEN*` · `HOLDOUT_FOR_C*` · `RAW_L1~L4*` · `PACKET_L*` ·
`*_OVERLAP*` · `PRECEDENCE_CONTESTED*` · `CALIBRATION_FOR_B*` · `control/**` ·
B/C 의 target-level holdout error report — **이 중 어느 것도 열지 않았다.**
입력은 D 가 스스로 만든 두 CSV 뿐이다. gold label 을 만들지 않았고, REAL_TARGET 에 접속하지
않았으며, 네트워크 다운로드 없이(`HF_HUB_OFFLINE=1`, `TRANSFORMERS_OFFLINE=1`) 로컬 캐시
모델만 썼다. production/control/engine/mart/raw evidence 를 수정하지 않았다.

---

## 4. Prototype 문장 전문 (3세트, frozen)

**정책**: 세 세트 모두 **모든 field 에 동일하게** 적용했다. field 마다 prototype 을 바꾸면
field 비교 자체가 무너지므로, 문구는 field 와 무관하게 고정이다.
문장은 `SSOTV2/00_SSOT_v2.1_POST_PILOT_RECOVERY.md` §4 archetype 목록과
`SSOTV2/01_REPRESENTATIVE_FUNCTION_MAPPING_DT_v2.1.md` §5 Stage-3 branch 정의문 / §7
"Prototype texts" 조항에서만 유도했고, `D_TEXT_CORPUS` 의 내용을 읽고 문구를 맞추지 않았다.
선행 실험 D-RF-001-C 의 세트와 **문자 단위로 동일**하며 이 run 에서 한 글자도 고치지 않았다.

### Set A — `A_SSOT_DEF` (PRIMARY). SSOT 01 §5 branch 정의(질문 + Region + Endpoint)의 축약형

- **QUERY**: 사용자가 검색 입력창에 자유 텍스트 질의를 입력하고 제출하여 검색 결과 목록 상태로 전환하는 것이 대표행동이다. 검색 입력 control, 검색 form, 검색 제출 버튼이 대표 표면이다. search box, search form, submit query, search results.
- **CONTENT_OPEN**: 이미 존재하는 기사, 영상, 콘텐츠 한 건을 목록에서 선택해 본문을 열거나 재생을 시작하는 것이 대표행동이다. 콘텐츠 카드 목록, 기사 본문, 미디어 재생이 대표 표면이다. article body, news, video playback, content card list.
- **ITEM_DETAIL**: 거래 대상 상품 한 건의 상세면에 들어가 상품명, 가격, 거래 control 의 존재를 확인하는 것이 대표행동이다. 반복되는 상품 카드 목록과 상품 상세 문서가 대표 표면이다. product name, price, cart, order, shopping mall, item detail page.
- **PLACE_LOOKUP**: 장소를 질의하거나 특정 장소의 상세면을 여는 것이 대표행동이다. 장소 검색 control, 장소 목록, 지도, 주소, 장소 상세 패널이 대표 표면이다. map, place search, address, location, route, navigation.
- **COMMUNICATION_ENTRY**: 사람 사이의 게시물, 스레드, 메시지를 교환하는 공간에 진입하는 것이 대표행동이다. 스레드 목록, 게시글 목록, 글쓰기 진입 control, 실제 로그인 gate 가 대표 표면이다. message, chat, post, thread, community, social feed, comment.
- **FINANCIAL_ACTION_ENTRY**: 금융처리 기능의 시작면을 열거나 그 기능을 시작하기 위해 필요한 실제 로그인 및 본인인증 gate 까지 진입하는 것이 대표행동이다. 잔액 조회, 이체, 송금, 결제, 카드, 보험, 인증 기능 진입 control 이 대표 표면이다. bank, transfer, payment, balance, card, insurance, login, identity verification.
- **UTILITY_ENTRY**: 특정 목적의 도구 기능면을 열고 첫 primary control 을 사용할 수 있는 상태로 만드는 것이 대표행동이다. 단일 목적 기능 진입 control 과 그 기능 화면이 대표 표면이다. utility tool, service function, apply, reserve, issue, lookup, settings.

### Set B — `B_USER_BEHAVIOR`. 같은 정의를 1인칭 사용자 행동 서술로. 어휘 register 를 크게 바꾼다

- **QUERY**: 나는 궁금한 것을 검색창에 입력하고 검색 버튼을 눌러 결과 목록을 본다.
- **CONTENT_OPEN**: 나는 목록에서 기사나 영상 하나를 골라 눌러서 읽거나 본다.
- **ITEM_DETAIL**: 나는 사고 싶은 물건 하나를 눌러 상세 화면에서 가격과 정보를 확인한다.
- **PLACE_LOOKUP**: 나는 가려는 장소를 찾아보고 그 장소의 위치와 상세 정보를 확인한다.
- **COMMUNICATION_ENTRY**: 나는 다른 사람이 올린 글이나 메시지를 보러 대화 공간에 들어간다.
- **FINANCIAL_ACTION_ENTRY**: 나는 은행이나 카드 업무를 시작하려고 로그인 화면까지 들어간다.
- **UTILITY_ENTRY**: 나는 필요한 기능 하나를 열어서 바로 쓸 수 있는 상태까지 간다.

### Set C — `C_TERSE_LABEL`. archetype 이름의 최소 gloss. 문장이 아니라 라벨에 가깝다

- **QUERY**: 검색 질의 search query
- **CONTENT_OPEN**: 콘텐츠 열람 content open article video
- **ITEM_DETAIL**: 상품 상세 item detail product price
- **PLACE_LOOKUP**: 장소 조회 place lookup map location
- **COMMUNICATION_ENTRY**: 커뮤니케이션 진입 communication message post
- **FINANCIAL_ACTION_ENTRY**: 금융 기능 진입 financial action bank payment
- **UTILITY_ENTRY**: 도구 기능 진입 utility function tool

---

## 5. Field 정의와 방법

### 5.1 representation 정의 (22개 평가 대상 + 12개 LOO)

결합 규약은 `D_TEXT_CORPUS` 의 `text_blob` 과 **동일**하다: 빈 field 는 생략하고 `" \n "` 으로 잇는다.

| representation | group | 구성 field |
|---|---|---|
| `title` … `url_tokens` (12개) | single | 각각 자기 자신 |
| `first_screen_interaction` | combo | `buttons` + `aria_labels` + `placeholders` |
| `accessibility_text` | combo | `aria_labels` + `form_labels` + `placeholders` + `input_names` |
| `primary_controls` | combo | `buttons` + `aria_labels` + `form_labels` + `placeholders` + `input_names` |
| `identity` | combo | `title` + `meta_description` + `url_tokens` |
| `structure` | combo | `title` + `headings` + `landmarks` |
| `content_body` | combo | `headings` + `card_texts` |
| `nav_surface` | combo | `landmarks` + `nav_links` |
| `ssot7_bundle` | combo | SSOT 01 §7 Text representation 조항 그대로: `title`+`headings`+`landmarks`+`aria_labels`+`buttons`+`form_labels`+`card_texts`+`url_tokens` |
| `controls_plus_identity` | combo | `title`+`url_tokens`+`buttons`+`aria_labels`+`form_labels`+`placeholders`+`input_names` |
| **`text_blob__ALL`** | **control** | 12 field 전체 |
| `blob_minus__<field>` ×12 | loo | 12 field 중 하나를 뺀 것 (§7 ablation 전용) |

### 5.2 방법

1. **동일한 frozen prototype 세트**를 모든 field 에 적용 → prototype 임베딩과 page representation
   임베딩의 코사인 유사도 → top-1 이 `prior_archetype` 과 일치하면 agreement.
2. 학습 없음(zero-shot). 34 representation × 3 model × 3 prototype set = **306 config**.
3. **모델 비교보다 FIELD 비교가 primary.** 모델을 바꾸면 field 표를 **모델별로 분리**해서
   낸다(§9). PRIMARY 는 `bge-m3 × A_SSOT_DEF` — bge-m3 만 8192 context 라 blob 을 자르지 않는다.
4. **e5 prefix 규약을 지켰다**: `intfloat/multilingual-e5-small` 은 비대칭 배치로
   페이지 텍스트에 `"passage: "`, prototype 에 `"query: "` 를 붙였다.
   `bge-m3` 와 `paraphrase-multilingual-MiniLM-L12-v2` 는 prefix 를 쓰지 않는 것이 공식 규약이라
   붙이지 않았다. 이 규약은 truncation 통계 계산에도 동일하게 적용했다.
5. **기준선**: `most_frequent`(항상 ITEM_DETAIL) 와 `stratified`(class prior 로 20,000회 추출).
   macro F1 에서 majority 대비 lift 는 **rigged 비교다** — majority 는 6/7 class 에서 recall 0 이라
   macro F1 이 구조적으로 0.091 밖에 안 나온다. 따라서 **판정 기준선은 stratified**,
   `most_frequent` 는 참고용으로만 병기한다.
6. **불확실성**: config 마다 `prior_archetype` 을 셔플한 **permutation null**(P=20,000,
   모든 config 가 같은 permutation 집합을 공유)을 만들고 관측값을 그 분포에 위치시켰다.
   단일 점수만 보고하지 않는다.

### 5.3 기준선 수치

| 기준선 | macro F1 | prior_agreement |
|---|---|---|
| `most_frequent` (→ ITEM_DETAIL) | 0.0906 | 0.4643 (26/56) |
| `stratified` mean | **0.1386** | 0.2737 |
| `stratified` p95 | **0.2217** | 0.3571 |
| `stratified` p99 | 0.2621 | — |

---

## 6. Field 별 결과표 — PRIMARY (bge-m3 × set A), n=56

`empty` = 그 field 가 빈 target 수. `agr` 분모는 항상 56 (empty = ABSTAIN = 오답).
`stab` = 3개 prototype 세트에 걸친 macro F1 range (작을수록 문구에 둔감).
`trunc` = max_seq(8192) 초과 비율. `perm p` = permutation null 대비 macro F1 p-value.

| # | representation | group | macro F1 | prior_agr (56분모) | Wilson 95% | empty | tok med | trunc | margin med | perm p | stab |
|---:|---|---|---:|---:|---|---:|---:|---:|---:|---:|---:|
| 1 | `title` | single | **0.559** | 0.607 (34/56) | .476–.723 | 1 | 8 | 0.00 | .0237 | <1e-5 | 0.081 |
| 2 | `identity` | combo | 0.556 | **0.679 (38/56)** | .547–.786 | 0 | 29 | 0.00 | .0222 | <1e-5 | 0.049 |
| 3 | **`text_blob__ALL`** | **control** | **0.509** | **0.679 (38/56)** | .547–.786 | 0 | 498 | 0.00 | .0214 | <1e-5 | 0.151 |
| 4 | `meta_description` | single | 0.496 | 0.518 (29/56) | .389–.644 | 15 | 26 | 0.00 | .0210 | <1e-5 | 0.109 |
| 5 | `content_body` | combo | 0.449 | 0.589 (33/56) | .459–.708 | 6 | 220 | 0.00 | .0218 | <1e-5 | 0.123 |
| 6 | `nav_links` | single | 0.438 | 0.482 (27/56) | .356–.610 | 16 | 106 | 0.00 | .0249 | <1e-5 | 0.129 |
| 7 | `headings` | single | 0.436 | 0.482 (27/56) | .356–.610 | 9 | 62 | 0.00 | .0220 | <1e-5 | 0.132 |
| 8 | `ssot7_bundle` | combo | 0.433 | 0.661 (37/56) | .528–.770 | 0 | 390 | 0.00 | .0217 | <1e-5 | 0.101 |
| 9 | `structure` | combo | 0.421 | 0.643 (36/56) | .510–.755 | 1 | 136 | 0.00 | .0241 | <1e-5 | 0.098 |
| 10 | `card_texts` | single | 0.420 | 0.554 (31/56) | .424–.675 | 9 | 181 | 0.00 | .0240 | <1e-5 | 0.098 |
| 11 | `nav_surface` | combo | 0.412 | 0.536 (30/56) | .406–.659 | 13 | 165 | 0.00 | .0217 | <1e-5 | 0.127 |
| 12 | `landmarks` | single | 0.400 | 0.500 (28/56) | .373–.627 | 13 | 94 | 0.00 | .0227 | <1e-5 | 0.138 |
| 13 | `controls_plus_identity` | combo | 0.400 | 0.554 (31/56) | .424–.675 | 0 | 116 | 0.00 | .0214 | <1e-5 | 0.092 |
| 14 | `url_tokens` | single | 0.361 | 0.482 (27/56) | .356–.610 | 2 | 8 | 0.00 | .0158 | 1e-4 | 0.121 |
| 15 | `buttons` | single | 0.334 | 0.321 (18/56) | .213–.454 | 12 | 56 | 0.00 | .0211 | 5e-5 | 0.122 |
| 16 | `first_screen_interaction` | combo | 0.257 | 0.304 (17/56) | .198–.435 | 7 | 86 | 0.00 | .0196 | .0018 | 0.101 |
| 17 | `primary_controls` | combo | 0.254 | 0.304 (17/56) | .198–.435 | 5 | 109 | 0.00 | .0162 | .0022 | 0.118 |
| 18 | `accessibility_text` | combo | 0.224 | 0.321 (18/56) | .213–.454 | 7 | 48 | 0.00 | .0195 | .0058 | 0.079 |
| 19 | `aria_labels` | single | 0.220 | 0.232 (13/56) | .140–.359 | 20 | 47 | 0.00 | .0206 | .0011 | 0.073 |
| 20 | `placeholders` | single | 0.116 | 0.125 (7/56) | .062–.238 | 34 | 8 | 0.00 | .0364 | .0136 | 0.014 |
| 21 | `input_names` | single | 0.061 | 0.089 (5/56) | .039–.192 | 31 | 12 | 0.00 | .0164 | **0.614** | 0.035 |
| 22 | `form_labels` | single | 0.030 | 0.054 (3/56) | .019–.147 | 39 | 8 | 0.00 | .0288 | **0.611** | 0.018 |

**truncation: 22/22 representation 에서 0/56.** bge-m3 max_seq 8192 에 대해 최장 representation
(`text_blob`)의 최대 토큰이 그보다 훨씬 작아 절단이 일어나지 않았다. 즉 §9 의 모델 간 차이는
절단 아티팩트가 아니다. (e5-small max_seq 512 / MiniLM max_seq 128 에서는 절단이 발생하며,
그 수치는 JSON `token_stats` 에 모델별로 따로 있다.)

**margin**: top1-top2 코사인 margin 중앙값이 22개 representation 전부 **0.016~0.036** 의
매우 좁은 띠에 있다. 즉 **margin 은 field 를 구분하지 못한다** — 잘 맞히는 field 라고 해서
결정이 더 확신에 차 있지 않다. margin 을 운영 abstention threshold 로 쓰려는 시도는
이 코호트에서 field 선택 문제를 해결해 주지 않는다.

**permutation null 대비 위치**: 20개 representation 은 null 분포 밖에 명확히 있다
(`title` z=+9.66, `text_blob` z=+8.98, `primary_controls` z=+3.38, `accessibility_text` z=+2.98).
**`form_labels`(p=0.611, z=−0.54) 와 `input_names`(p=0.614, z=−0.30) 는 null 과 구별되지 않는다** —
이 두 field 는 이 코호트에서 archetype 정보를 **전혀** 담고 있지 않다.

---

## 7. Leave-one-field-out ablation (PRIMARY)

Δ = macro F1(`text_blob`) − macro F1(`text_blob` 에서 해당 field 제거).
**Δ > 0 이면 그 field 는 blob 안에서 신호를 보태고 있고, Δ < 0 이면 노이즈다.**
판정 임계는 ±0.02 (사전 등록).

| field | Δ macro F1 | Δ prior_agr | 단독 macro F1 | 판정 |
|---|---:|---:|---:|---|
| `nav_links` | **+0.061** | +0.018 | 0.438 | HELPS |
| `buttons` | **+0.044** | 0.000 | 0.334 | HELPS |
| `aria_labels` | **+0.035** | 0.000 | 0.220 | HELPS |
| `meta_description` | **+0.033** | 0.000 | 0.496 | HELPS |
| `form_labels` | **+0.030** | +0.018 | 0.030 | HELPS |
| `landmarks` | +0.015 | 0.000 | 0.400 | NEUTRAL |
| `url_tokens` | +0.006 | +0.036 | 0.361 | NEUTRAL |
| `card_texts` | +0.004 | 0.000 | 0.420 | NEUTRAL |
| `title` | −0.018 | −0.036 | **0.559** | NEUTRAL |
| `input_names` | **−0.072** | −0.036 | 0.061 | **NOISE** |
| `placeholders` | **−0.088** | −0.054 | 0.116 | **NOISE** |
| `headings` | **−0.096** | −0.054 | 0.436 | **NOISE** |

### 이 표가 말하는 두 가지 반직관

1. **혼자서는 강한데 blob 안에서는 노이즈인 field 가 있다.** `headings` 는 단독 0.436
   (22개 중 7위)인데 blob 에서 빼면 **macro F1 이 0.096 올라간다.** `title` 도 단독 1위인데
   빼도 손해가 −0.018 뿐이다. → **field 의 단독 정보량과 앙상블 기여도는 다른 양이다.**
   긴 field 는 blob 안에서 짧고 정확한 field 의 신호를 희석한다.
2. **혼자서는 무의미한데 blob 안에서는 도움이 되는 field 가 있다.** `form_labels` 는
   단독 macro F1 0.030 (permutation null 과 구별 불가)인데 blob 에서 빼면 0.030 이 떨어진다.
   n=56 규모에서 이 크기의 Δ 는 1~2건 뒤집힘으로도 생기므로 **과해석하지 않는다.**

---

## 8. POST-HOC 진단 — 1위 field 의 우위는 브랜드 식별인가

> **이 절은 사전 등록 항목이 아니다.** 결과를 본 뒤 추가한 confound 진단이며,
> prototype 문구도 임계값도 바꾸지 않았다. brand-masked 표현을 하나 더 평가했을 뿐이다.
> `figures/RF2_C_brand_masking.png`.

**동기**: `prior_archetype` 은 business domain prior 에서 왔고 business domain 은 **service
identity** 에서 왔다. 그런데 1위 `title` 과 2위 `identity` 는 정확히 service identity 를 담는
field 다. 이걸 분리하지 않으면 "title 이 archetype 을 안다"가 아니라 "title 이 브랜드를 읽고,
브랜드→archetype 매핑을 되짚었다"는 순환일 수 있다.

**방법**: 각 target 의 `prior_service` 문자열 변형 + URL host 토큰(www/com/co/kr 등 제외)을
대소문자 무시로 **모든 field 에서 제거**한 뒤 PRIMARY config 를 재계산.
예: `쿠팡이츠 → ["coupangeats","쿠팡이츠"]`, `삼성카드 → ["samsungcard","삼성카드"]`,
`GS25 → ["gsretail","gs25"]`.

| representation | 원본 F1 | 브랜드 마스킹 F1 | Δ | Δ prior_agr |
|---|---:|---:|---:|---:|
| `url_tokens` | 0.361 | 0.138 | **−0.223** | −0.268 |
| `title` | **0.559** | **0.357** | **−0.202** | **−0.214** |
| `identity` | 0.556 | 0.411 | −0.145 | −0.089 |
| `buttons` | 0.334 | 0.223 | −0.111 | −0.053 |
| `landmarks` | 0.400 | 0.331 | −0.069 | −0.036 |
| `meta_description` | 0.496 | 0.444 | −0.052 | −0.018 |
| **`text_blob__ALL`** | 0.509 | **0.478** | **−0.031** | −0.018 |
| `card_texts` | 0.420 | 0.429 | +0.009 | 0.000 |
| `content_body` | 0.449 | 0.457 | +0.008 | 0.000 |
| `structure` | 0.421 | **0.462** | **+0.041** | −0.018 |
| `aria_labels` | 0.220 | 0.220 | −0.001 | 0.000 |
| `primary_controls` | 0.254 | 0.197 | −0.057 | −0.036 |

**결론**: 브랜드 문자열을 지우면 **`title` 의 1위가 무너지고(0.559 → 0.357, agreement 34/56 → 22/56)
`text_blob__ALL` 이 1위로 올라온다(0.478).** `url_tokens` 의 신호는 사실상 전부 브랜드다.
반대로 `card_texts` · `content_body` · `structure` 는 브랜드를 지워도 떨어지지 않거나
오히려 오른다 — 이들은 **실제 페이지 내용에서** archetype 을 읽고 있다.

따라서 §2 의 **H-C1 REFUTED 는 조건부다.** "as collected" 텍스트에서는 `title` 이 이기지만,
그 우위의 **약 2/3 (0.202/0.559 ≈ 36%p 상대 하락)** 은 브랜드 식별에서 나온다.
**브랜드 식별 경로를 막으면 H-C1(전체 텍스트가 최선)이 다시 성립한다.**
반면 §2 의 **H-C2 NOT_SUPPORTED 는 마스킹 후에도 그대로다** — `primary_controls` 는
0.254 → 0.197 로 오히려 stratified p95(0.222) **아래로** 내려간다.

---

## 9. 모델별 field 표 (secondary) — 모델 비교가 아니라 field 순위의 재현성 확인

set A 고정. 표를 **모델별로 분리**해서 낸다. macro F1 기준 상위 5 + 핵심 항목의 순위.

| 순위 | bge-m3 (8192) | e5-small (512, passage:/query:) | MiniLM (128) |
|---:|---|---|---|
| 1 | `title` 0.559 | `ssot7_bundle` 0.478 | **`text_blob__ALL` 0.543** |
| 2 | `identity` 0.556 | **`text_blob__ALL` 0.458** | `card_texts` 0.482 |
| 3 | **`text_blob__ALL` 0.509** | `identity` 0.439 | `content_body` 0.479 |
| 4 | `meta_description` 0.496 | `structure` 0.435 | `structure` 0.468 |
| 5 | `content_body` 0.449 | `title` 0.432 | `identity` 0.455 |
| — | `primary_controls` **17위** 0.254 | `primary_controls` **13위** | `primary_controls` **13위** |

**세 모델 모두에서 `primary_controls` 는 하위권이고 `text_blob` 은 상위 3위 안이다.**
즉 §2 의 H-C2 기각은 모델 선택에 의존하지 않는다.
반대로 **"`title` 단독이 `text_blob` 을 이긴다"는 bge-m3 에서만 나타난다** — e5-small 에서 5위,
MiniLM 에서 7위다. e5-small/MiniLM 은 max_seq 가 짧아 `text_blob` 이 실제로 절단되는데도
`text_blob` 이 더 위다. 따라서 §2 의 H-C1 REFUTED 는 **PRIMARY config 국한 결과**이며,
§8 의 브랜드 진단과 합치면 "1위 title" 은 견고한 발견이 아니다.

### prototype 문구 안정성 (H-C3)

| 모델 | between-FIELD sd | between-PROTOTYPE-SET sd | 비 | field 순위 Spearman (세트 쌍) |
|---|---:|---:|---:|---|
| bge-m3 | **0.1276** | 0.0384 | 3.3× | .68 / .86 / .70 |
| e5-small | 0.0977 | **0.1027** | **0.95×** | .75 / .76 / .73 |
| MiniLM | **0.1418** | 0.0289 | 4.9× | .86 / .89 / .84 |

- bge-m3 · MiniLM: **field 효과가 prototype 문구 노이즈보다 3~5배 크다 → H-C3 REFUTED.**
- e5-small: 둘이 거의 같다 → 이 모델에서는 H-C3 를 기각할 수 없다. **작은 모델을 쓰면
  "어느 field 를 쓰느냐"와 "prototype 을 어떻게 쓰느냐"가 같은 크기의 결정이 된다.**
- field 순위 자체는 세 세트에 걸쳐 Spearman 0.68~0.89 로 **순위는 대체로 보존**된다.
- **stratified p95 통과 여부가 prototype 세트에 따라 뒤집히는 representation 은 2개**:
  `buttons` (A .334 / B .313 / C .212) 와 `aria_labels` (A .220 / B .273 / C .294).
  하필 H-C2 의 핵심 field 두 개다 → **primary controls 계열의 결론은 문구에 취약하다.**
  단, 뒤집힘의 방향이 "기준선 근처에서 왔다 갔다" 하는 것이므로 §2 의 NOT_SUPPORTED
  판정 자체는 바뀌지 않는다(어느 세트에서도 `text_blob` 을 넘지 못한다).
- `text_blob` 자체의 range 는 0.151(A .509 / B .387 / C .537)로 **오히려 큰 편**이다 —
  긴 텍스트일수록 prototype register 에 민감하다.

---

## 10. v1 → v2 인코딩 시정의 효과

v1 코퍼스는 한글이 깨져 있었다(`html_decode.py` 로 선언 charset 준수 후 v2 재생성).
**동일 코드 · 동일 prototype · PRIMARY 모델**로 v1 을 재계산해 차이를 격리했다.
`figures/RF2_C_v1_v2_encoding.png`.

- 텍스트가 달라진 target: **8/56**. field 별 변경 건수 — `headings` 7 · `buttons` 7 ·
  `card_texts` 7 · `title` 6 · `meta_description` 5 · `landmarks`/`nav_links`/`placeholders`/`form_labels` 4 ·
  `aria_labels` 2 · `input_names` 0 · `url_tokens` 0.
- `blob_tokens` 중앙값 **132 → 173.5**.

| representation | v1 macro F1 | v2 macro F1 | Δ |
|---|---:|---:|---:|
| `title` | 0.434 | **0.559** | **+0.125** |
| `controls_plus_identity` | 0.307 | 0.400 | +0.093 |
| `card_texts` | 0.358 | 0.420 | +0.062 |
| `headings` | 0.381 | 0.436 | +0.055 |
| `nav_links` | 0.390 | 0.438 | +0.047 |
| `identity` | 0.516 | 0.556 | +0.040 |
| `text_blob__ALL` | 0.497 | 0.509 | +0.012 |
| `placeholders` | 0.180 | 0.116 | −0.064 |
| `ssot7_bundle` | 0.464 | 0.433 | −0.031 |

### 결론이 바뀌었는가 — 부분적으로 그렇다

- **1위 field 가 바뀌었다: `identity` (v1) → `title` (v2).** 상위 5 구성도 바뀌었다
  (v1: identity, text_blob, meta_description, ssot7_bundle, structure /
  v2: title, identity, text_blob, meta_description, content_body).
- 이득이 **짧고 정보밀도 높은 field 에 집중**됐다. `title` 은 중앙값 8토큰짜리 field 인데
  8/56 target 에서 6건이 바뀌었고 그 결과 macro F1 이 12.5%p 올랐다.
  긴 `text_blob` 은 +0.012 밖에 안 올랐다 — **깨진 문자 몇 개가 긴 텍스트에서는 희석되지만
  짧은 텍스트에서는 그 field 전체를 망친다.**
- **`text_blob` 하나만 봤다면 인코딩 결함의 영향을 +0.012 로 과소평가했을 것이다.**
  선행 실험 D-RF-001-C 가 v1 위에서 `text_blob` 중심으로 돌았다는 점을 감안하면,
  그 실험의 절대 수치는 field 수준 결론의 근거로 재사용해서는 안 된다.
- 단, §2 의 세 가설 판정은 v1 에서도 **모두 동일**하다(v1 에서도 1위는 `text_blob` 이 아닌 `identity`(2위가 `text_blob`)였고,
  `primary_controls` 는 v1 에서도 17위였다). **판정은 안 바뀌고 순위는 바뀐다.**

---

## 11. 반례

`text_blob__ALL` 예측과 `first_screen_interaction` 예측이 갈린 target 25건.

| 방향 | 건수 |
|---|---:|
| blob 맞음 / controls 틀림 | **23** |
| controls 맞음 / blob 틀림 | **2** |

**23 : 2 의 비대칭이 §2 H-C2 기각의 가장 직접적인 증거다.**

controls 가 이긴 2건 (반례로서 유일하게 의미 있는 사례):

| service | prior | blob 예측 | first_screen_interaction 예측 |
|---|---|---|---|
| TikTok | CONTENT_OPEN | COMMUNICATION_ENTRY ✗ | **CONTENT_OPEN ✓** |
| 네이버 | QUERY | ITEM_DETAIL ✗ | **QUERY ✓** |

둘 다 **전체 텍스트가 브랜드/주변 콘텐츠에 끌려간 반면, 조작 표면이 대표행동을 그대로 드러낸
사례**다. 네이버 첫 화면의 전체 텍스트는 쇼핑·뉴스 카드로 뒤덮여 ITEM_DETAIL 로 끌려가지만
검색 버튼/입력 aria-label 은 QUERY 를 정확히 가리킨다. 이 2건은 **H-C2 를 되살리지는 못하지만,
"controls 가 무의미하다"는 반대 극단도 틀렸음**을 보여준다.

controls 가 진 23건 중 4건은 아예 `ABSTAIN` (조작 표면이 비어 있음: 신한 SOL뱅크, 세븐일레븐 등).
나머지는 GS25 → FINANCIAL_ACTION_ENTRY, 마켓컬리 → FINANCIAL_ACTION_ENTRY,
롯데백화점 → QUERY, Netflix → QUERY, 카카오톡 → QUERY 처럼 **버튼 문구가 결제·검색 같은
보조 기능을 가리켜 대표행동을 오도**하는 패턴이다.

### class 수준 반례: UTILITY_ENTRY (n=5)

`text_blob` 의 UTILITY_ENTRY recall = **0/5** (Wilson 95% CI 0.000–0.435).
22개 representation 중 UTILITY_ENTRY 를 하나라도 맞힌 것은 `title` 2건, `controls_plus_identity`
2건, `identity` 1건, `headings` 1건 **뿐**이고 나머지 18개는 전부 0건이다.
**n=5 이므로 과해석하지 않지만**, 이는 D-RF-001-C 가 v1 에서 관찰한 "UTILITY_ENTRY 0/5" 가
인코딩 시정 후에도 살아남았다는 뜻이며, prototype 문구 문제가 아니라 **UTILITY_ENTRY 정의가
텍스트 표면에 흔적을 남기지 않는 구조적 문제**일 가능성을 시사한다.

---

## 12. VERDICT

**`PARTIALLY_SUPPORTED`**

성립한 것:
- semantic information 은 **field 마다 크게 다르다**. bge-m3 기준 34개 representation 에 걸친 macro F1 range 0.537 (평가 대상 22개만 보면 0.030~0.559),
  field 간 sd 가 prototype 문구 노이즈 sd 의 3.3배 (H-C3 REFUTED).
- **어떤 field 는 정보가 전혀 없다**: `form_labels`(p=.611) · `input_names`(p=.614) 는
  permutation null 과 구별되지 않는다.
- **어떤 field 는 blob 안에서 노이즈다**: `headings`(Δ −0.096) · `placeholders`(Δ −0.088) ·
  `input_names`(Δ −0.072) 를 blob 에서 빼면 macro F1 이 오른다.
- **짧은 field 가 전체 텍스트에 필적한다**: `identity`(중앙값 29토큰)가 `text_blob`(498토큰)과
  prior_agreement 38/56 로 동률이고 macro F1 은 더 높다(0.556 vs 0.509).
  세 모델 모두에서 `identity`/`structure`/`ssot7_bundle` 이 상위권이다.

성립하지 않은 것:
- 사전 가설 H-C2 의 방향이 **반대로** 나왔다. primary controls / accessibility text 는
  전체 텍스트보다 훨씬 덜 informative 하다.
- 1위 `title` 의 우위는 §8 브랜드 마스킹에서 대부분 사라진다 → H-C1 REFUTED 는
  "as collected" 조건부이며 confound 를 통제하면 뒤집힌다.

---

## 13. Limitation

가장 무거운 것부터.

1. **target 이 gold label 이 아니라 순환 가능한 prior 다.** `prior_archetype` 은 business domain
   prior 이고 business domain 은 service identity 에서 왔다. `title`/`url_tokens` 같은 identity
   field 의 높은 `prior_agreement` 는 semantic 능력이 아니라 **prior 생성 경로 역추적**일 수 있다.
   §8 이 이를 부분적으로만 통제한다(브랜드 문자열은 지웠지만 도메인 특유 어휘 — "배달", "이체",
   "장바구니" — 는 그대로 남아 있고, 그 어휘 자체가 business domain 을 규정한다).
   **이 실험은 "field 가 prior 를 얼마나 복원하는가"를 재지, "field 가 실제 대표기능을 얼마나
   잘 식별하는가"를 재지 못한다.** 후자는 독립 라벨이 있어야 하고, 그 라벨은 D 의 방화벽 밖에 있다.
2. **n=56, 7 class, 5개 class 가 n≤5.** macro F1 이 이 5개 class 에 5/7 가중치를 준다.
   n=3(CONTENT_OPEN) class 에서 1건이 뒤집히면 macro F1 이 ~0.05 움직인다.
   §6 순위의 1~4위(0.559 / 0.556 / 0.509 / 0.496)는 **이 잡음 크기 안에 있으므로 서로 구별되지
   않는다**. "title 이 1위"라고 읽지 말고 "identity 계열 4개가 상위 그룹"이라고 읽어야 한다.
3. **prior_agreement 와 macro F1 이 서로 다른 순위를 준다.** `text_blob`/`identity` 는
   agreement 38/56 로 공동 1위지만 macro F1 에서는 `title` 이 위다. 다수 class(ITEM_DETAIL 26)를
   잘 맞히느냐 소수 class 를 고르게 맞히느냐의 차이다. **어느 쪽을 운영 지표로 쓸지는
   D 가 정할 수 있는 문제가 아니다.**
4. **abstention 을 오답으로 계산한 것이 controls 계열에 불리하게 작동한다.**
   `primary_controls` 는 5/56, `first_screen_interaction` 은 7/56 이 비어 있다.
   non-empty 조건부로 보면 `first_screen_interaction` 17/49 = 0.347 로 조금 오르지만
   `text_blob` 38/56 = 0.679 와의 격차는 그대로다 → **H-C2 기각은 이 규약 때문이 아니다.**
   반대로 `meta_description` 은 조건부 29/41 = **0.707** 로 전체 최고인데 15/56 이 비어 있어
   전체 분모에서는 4위로 내려간다.
5. **단일 코호트 · 단일 스냅샷 · L0 landing 만.** L1 이후는 보지 않았다. 첫 화면의 조작 표면이
   빈약한 것이 대표기능 진입 자체의 성질인지 L0 의 성질인지 이 실험은 구분하지 못한다.
6. **zero-shot 유사도만 사용했고 threshold 를 정하지 않았다.** SSOT 01 §7 의 threshold 조항은
   independent calibration split 을 요구하는데 그 split 은 D 의 방화벽 밖이다. 따라서
   운영 abstention 비율을 이 결과에서 도출할 수 없다.
7. **e5-small 에서 H-C3 가 성립한다**(§9). 즉 결론이 embedding 용량에 의존한다.
   더 작은/다른 모델에서는 field 선택의 이득이 prototype 문구 운에 묻힐 수 있다.
8. `text_blob` 결합 순서가 고정(title→…→url_tokens)이라 LOO ablation Δ 에 위치 효과가
   섞여 있을 수 있다. 순서 셔플 대조는 하지 않았다.

---

## 14. Production implication

이 문서는 **NON_CANONICAL** 이다. 아래는 결정이 아니라 B/A 가 검토할 후보다.

1. **NLP fallback 의 입력을 "페이지 전체 텍스트"로 두는 것은 최선이 아니다.**
   `identity`(title+meta+url, 중앙값 29토큰)가 `text_blob`(498토큰)과 동일한 prior_agreement 를
   내면서 macro F1 은 더 높다. **입력 토큰을 17배 줄여도 손해가 없다.**
   단 §13-1 때문에 이 이득의 상당 부분은 브랜드 순환일 수 있으므로,
   **독립 라벨로 재검증하기 전에 identity-only 로 좁히면 안 된다.**
2. **SSOT 01 §7 의 Text representation 목록은 그대로 쓰면 손해다.**
   조항 그대로 구현한 `ssot7_bundle` 은 PRIMARY 에서 8위(0.433)로, 그 안에 든
   `title` 단독(0.559)보다 낮다. **§7 목록에서 `form_labels`·`input_names` 를 빼고
   `meta_description` 을 넣는 것이 후보 수정안이다** — 단 이는 SSOT 변경 제안이며
   D 가 실행할 수 없다. A 결정 사항으로 올린다.
3. **accessibility text 를 archetype 분류의 주 입력으로 쓰지 마라.**
   `aria_labels` 는 20/56 에서 비어 있고, 비어 있지 않을 때도 조건부 13/36 = 0.361 이다.
   접근성 텍스트는 **KWCAG 축의 측정 대상이지 archetype 분류의 feature 가 아니다.**
   두 용도를 섞으면 접근성이 나쁜 페이지에서 archetype 분류가 동시에 무너져
   **두 축의 독립성(SSOT: "세 축을 단일 종합점수로 합치지 않는다")이 통계적으로 깨진다.**
   이것이 이 실험의 가장 실무적인 함의다.
4. **`headings` 를 blob 에 넣는 현재 결합은 재검토 대상이다.** 빼면 macro F1 +0.096.
5. **margin 기반 abstention 은 field 선택 문제를 해결하지 못한다.** 22개 전부 margin 중앙값이
   0.016~0.036 의 좁은 띠라 margin threshold 로 좋은 field 와 나쁜 field 를 가를 수 없다.
   abstention 은 margin 이 아니라 **field missingness** 로 거는 편이 낫다
   (`form_labels` 39/56 empty 인데 margin 은 0.029 로 평균보다 오히려 높다 —
   **정보가 없을수록 margin 이 커지는 역전이 있다**).
6. **인코딩 검증을 파이프라인 게이트로 넣어라.** §10 에서 8/56 target 의 mojibake 가
   짧은 field 의 macro F1 을 12.5%p 떨어뜨렸는데 `text_blob` 수준 지표로는 1.2%p 로만 보였다.
   **blob 수준 모니터링은 인코딩 결함을 숨긴다.**

---

## 15. 추가 연구질문

1. **[가장 중요]** 브랜드·도메인 어휘를 모두 제거한 뒤에도 남는 archetype 신호가 있는가?
   §8 은 브랜드 문자열만 지웠다. domain-vocabulary ablation (예: 금융/쇼핑 어휘 사전 마스킹)이
   필요하다. 이것이 "semantic 인가 identity 인가"를 닫는 유일한 D-내부 경로다.
2. `headings` 가 왜 blob 안에서 노이즈인가? 길이 때문인가 내용 때문인가?
   같은 길이로 자른 `headings` 와 `card_texts` 를 비교하면 분리된다.
3. field 결합 순서를 셔플하면 LOO Δ 가 유지되는가 (§13-8).
4. UTILITY_ENTRY 가 22개 representation 중 18개에서 0/5 인 이유 — prototype 문제인가
   archetype 정의가 텍스트 표면에 흔적을 남기지 않는 것인가. n=5 를 늘리지 않으면 답할 수 없다.
5. `meta_description` 은 조건부 0.707 로 최고인데 15/56 이 비어 있다.
   meta 가 있는 페이지와 없는 페이지가 체계적으로 다른가 (예: SPA vs 정적)?
   그렇다면 missingness 자체가 feature 다.
6. AX tree 를 직접 쓰면(`aria_labels` 는 DOM 속성 추출이지 AX tree 가 아니다) accessibility
   계열의 결론이 바뀌는가.
7. e5-small 에서만 H-C3 가 성립하는 것이 모델 크기 때문인가 prefix 규약 때문인가.

---

## 16. 재현

```bash
export HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1
/home/sieg/projects-wsl/ProjectFinal/.venv/bin/python \
  research/landing_accessibility/research_d/tools/rf2_c_field_ablation.py all
# compute → results/RF2_C_field_ablation.json
# figures → figures/RF2_C_*.png
# mlflow  → LA_03_RF_MAPPING / "D-RF2-C field-wise semantic ablation"
```

모델 가중치는 MLflow artifact 로 올리지 않았다. 네트워크 다운로드 없이
`~/.cache/huggingface/hub` 의 로컬 캐시만 사용했다.
