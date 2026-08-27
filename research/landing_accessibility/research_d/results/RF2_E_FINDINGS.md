# RF2-E — Abstention / Ambiguity Taxonomy

**child** D-RF2-E · **parent RQ** RQ-D-RF-002 · **hypothesis** H-RF2-E-ABSTENTION-TAXONOMY · **rule/model version** RF2E_TAXONOMY_v1 · **seed** 20260827 · **generated** 2026-08-27T22:57:33.787003+09:00

## VERDICT — PARTIALLY_SUPPORTED

Rule DT 의 abstention 은 **하나의 원인이 아니다.** 40건의 abstain 은 서로 다른 원인 유형의 혼합이고, 원인의 절반은 더 나은 수집으로 풀리지만 나머지 절반은 **이 target URL 에서는 원리적으로 풀리지 않는다** — 관측된 표면이 애초에 대표 기능면이 아니기 때문이다. 따라서 '수집을 고치면 coverage 가 오른다'도 '어차피 안 되니 abstain 이 맞다'도 둘 다 틀렸다.

가장 중요한 단일 사실: **`AMBIGUOUS_UNRESOLVED__NO_STRONG_CANDIDATE` 는 원인이 아니라 증상이다.** 어떤 술어도 발화하지 않은 12건 중 11건은 표면정체성 유형(브랜드면·앱설치면) 또는 캡처품질 유형(인코딩 훼손·렌더 희소)으로 설명된다. 설명되지 않는 잔여는 1건뿐이다.

## RQ

> 현재 ambiguous / abstain 케이스를 원인별로 분류하면 어떤 유형이 나오며, 각 유형은 더 나은 evidence 로 해결 가능한가 원리적으로 미결정인가. 그리고 **어디에서 abstain 해야 하는가.**

## 경쟁가설 판정

판정 규칙: '대부분' = abstain 40 중 60% 초과로 사전 조작화. H-E1/H-E2 는 primary-type 배정(고정 우선순위)과 우선순위-무관 하한/상한을 둘 다 만족해야 SUPPORTED 로 올린다.

| 가설 | 판정 | 근거 |
|---|---|---|
| H-E1 대부분이 evidence 부족(수집으로 해결) | **PARTIALLY_SUPPORTED** | primary-type 기준 RESOLVABLE 20/40 = 0.50. 우선순위와 무관하게 '캡처품질 유형을 하나라도 갖는' abstain 22/40. 절반 수준이지 '대부분' 이 아니다. |
| H-E2 대부분이 원리적 미결정(수집해도 안 됨) | **PARTIALLY_SUPPORTED** | primary-type 기준 UNDECIDABLE_AT_THIS_URL 19/40 = 0.47. 우선순위와 무관하게 '표면부재 계열 유형을 하나라도 갖는' abstain 22/40. 역시 절반 수준이지 '대부분' 이 아니다. |
| H-E3 유형이 뒤섞여 분류 자체가 불안정 | **PARTIALLY_SUPPORTED** | 뒤섞임은 확인된다 — abstain 40 의 target 당 평균 유형 수 2.98, 표면부재계열과 캡처품질계열을 **동시에** 갖는 target 10건, 둘 다 없는 target 6건. 그러나 '분류 자체가 불안정' 은 절반만 맞다: 어느 유형이 primary 인지는 우선순위 규칙에 흔들리지만(민감도 참조), 우선순위와 무관한 하한/상한 (표면부재 유형 보유 22 / 캡처품질 유형 보유 22 / 둘 다 10 / 둘 다 아님 6)은 규칙과 무관하게 고정이다. |

세 가설 모두 PARTIALLY_SUPPORTED 라는 것이 결론이다. H-E1 과 H-E2 는 서로 배타적으로 제시되었지만 데이터는 **둘 다 절반씩 맞다**고 말한다. 그리고 그 절반은 겹친다 — 표면부재 계열과 캡처품질 계열을 **동시에** 갖는 abstain 이 10건이다. 이런 target 은 수집을 고쳐도 표면이 없어서 안 되는 케이스다.

## 입력 · 분석단위 · N

| 입력 | sha256 |
|---|---|
| `results/D_OBSERVATION_TABLE_v2.csv` | `c39c10f09f7a6a76…` |
| `results/D_TEXT_CORPUS_v2.csv` | `bf6bb772faa45541…` |
| `results/RF001_A_rule_dt.json` | `c27078736813e74f…` |
| `results/RF001_C_embedding.json` | `f0efd39ffe9ef5fe…` |
| `results/RQ_D13A_overlay_provenance.json` | `ff3149638eff6600…` |
| `results/RQ_D13_duplicate_vector.json` | `70d6375cb7dc5714…` |
| `results/RQ_D10_slot_mismatch.json` | `8a23e1f7b00ed4f1…` |
| `results/RQ_D9_quality_proxy.json` | `f701590e0a721bf4…` |

- **분석단위** target (wtg, in_mart==1)
- **N** 기대 56 · 관측 56
- **분모 3종** — 유형별 N 은 세 분모 모두에 대해 보고한다:
  - 전체 target `56`
  - abstain `40` = MULTI_CANDIDATE 6 + NO_STRONG_CANDIDATE 34
  - rule 미확정 전체 `45` = abstain 40 + Stage0 UNDETERMINED 5
  - rule 확정 `11` (대조군)

### missing N

- `prior_url_missing_n` = 2
- `probe_absent_n` = 2
- `no_final_url_n` = 2
- `note` = 누락은 배제하지 않고 유형(T07/T09/T12)으로 흡수해 센다.

### 독립 재계산 대조

RF001-A 의 요약수치를 그대로 받지 않고 `decision_trace` 에서 branch 별 R/E 발화를 직접 재구성해 세었다. 결과 일치: **True** (mapped 11 / multi 6 / no-strong 34 / stage0 5).

## 유형 정의 — 전문

한 target 은 **여러 유형에 동시에 해당할 수 있다.** 중복을 허용하고 중복행렬을 따로 낸다. 각 유형의 판정식은 아래 정의 그대로이며 코드 `tools/rf2_e_abstention_taxonomy.py::classify` 에 있다.

### family — EVIDENCE_SHAPE

#### `T01_NO_PREDICATE_FIRED` — 어떤 술어도 발화하지 않음 (insufficient evidence)

**정의.** Stage3 가 실제로 평가되었고(= 14개 R/E 술어가 trace 에 기록됨), 그 14개 중 단 하나도 fired=true 가 아니다. 관측된 표면에 SSOT §5 가 정의한 어떤 archetype 의 region 신호도 endpoint 신호도 없다는 뜻이다. 이것은 **원인이 아니라 증상**이며, 아래 표면유형/수집품질 유형으로 분해되어야 한다.

**N.** 56 중 **12** (21%) · abstain 40 중 **12** (30%) · 미확정 45 중 12 · rule 확정 11 중 0

**해결가능성.** `DECOMPOSES` — 증상이지 원인이 아니다. 아래 표면/수집 유형으로 분해한 뒤 판단한다.

**evidence example** (최대 5건)

| wtg | service | prior | leaf | 최종 URL | 이 유형으로 분류한 관측값 |
|---|---|---|---|---|---|
| `054d78ed187c` | 쿠팡이츠 | ITEM_DETAIL | AU__NO_STRONG_CANDIDATE | `https://www.coupangeats.com/` | Stage3 14개 술어 발화 0 (n_fired=0) |
| `0f3bdb2bd0bb` | 탑마트 | ITEM_DETAIL | AU__NO_STRONG_CANDIDATE | `https://www.seowon.com/` | Stage3 14개 술어 발화 0 (n_fired=0) |
| `190b4501e441` | V3 Mobile Plus | UTILITY_ENTRY | AU__NO_STRONG_CANDIDATE | `https://mplweb.ahnlab.com/mplweb/v3mp/main_android.do` | Stage3 14개 술어 발화 0 (n_fired=0) |
| `35319a420294` | 토스 | FINANCIAL_ACTION_ENTRY | AU__NO_STRONG_CANDIDATE | `https://toss.im/` | Stage3 14개 술어 발화 0 (n_fired=0) |
| `51484a735cdb` | 컴포즈커피 | ITEM_DETAIL | AU__NO_STRONG_CANDIDATE | `https://composecoffee.com/` | Stage3 14개 술어 발화 0 (n_fired=0) |

#### `T02_WEAK_ONE_SIDED_EVIDENCE` — 한쪽 신호만 있는 약한 후보 (region 만 또는 endpoint 만)

**정의.** Stage3 술어가 1개 이상 발화했으나 R 과 E 를 동시에 만족하는 branch 가 하나도 없다(strong=∅, weak≠∅). SSOT §6 의 '유일 후보' 조건을 만족할 수 없어 확정 불가다.

**하위구분.** `ENDPOINT_ONLY__REGION_MISSING`=11 · `BOTH_SIDES_BUT_DIFFERENT_BRANCHES`=5 · `REGION_ONLY__ENDPOINT_MISSING`=6

> ENDPOINT_MISSING 은 상호작용 1스텝 수집으로 확인 가능한 쪽이고, BOTH_SIDES_BUT_DIFFERENT_BRANCHES 는 서로 다른 archetype 의 반쪽 신호가 섞인 것이라 수집이 아니라 §5 술어 조작화 문제다.

**N.** 56 중 **22** (39%) · abstain 40 중 **22** (55%) · 미확정 45 중 22 · rule 확정 11 중 0

**해결가능성.** `COLLECTION_OR_DEFINITION` — R 또는 E 중 한쪽만 붙었다. 누락된 쪽이 endpoint 인 경우는 상호작용 1스텝 수집으로 확인 가능하고, 누락된 쪽이 region 인 경우는 §5 region 정의의 조작화 문제다.

**evidence example** (최대 5건)

| wtg | service | prior | leaf | 최종 URL | 이 유형으로 분류한 관측값 |
|---|---|---|---|---|---|
| `12e3942c0495` | GS25 | ITEM_DETAIL | AU__NO_STRONG_CANDIDATE | `https://www.gsretail.com/brand/gs25` | weak=['CONTENT_OPEN', 'PLACE_LOOKUP'] strong=[] (n_fired=2) |
| `13ed070478ef` | Netflix | CONTENT_OPEN | AU__NO_STRONG_CANDIDATE | `https://www.netflix.com/kr/login?serverState=Bgi8vuvcAxK1AZY` | weak=['PLACE_LOOKUP', 'COMMUNICATION_ENTRY', 'FINANCIAL_ACTION_ENTRY'] strong=[] (n_fired=3) |
| `24e6654bfd1a` | YouTube | CONTENT_OPEN | AU__NO_STRONG_CANDIDATE | `https://m.youtube.com/` | weak=['QUERY'] strong=[] (n_fired=1) |
| `49a5eca8b58f` | 11번가 | ITEM_DETAIL | AU__NO_STRONG_CANDIDATE | `http://m.11st.co.kr/page/main/home` | weak=['QUERY', 'CONTENT_OPEN'] strong=[] (n_fired=2) |
| `517b8047eb5b` | 농협하나로마트 | ITEM_DETAIL | AU__NO_STRONG_CANDIDATE | `https://www.nhhanaro.co.kr/mbshome/mbs/nahh007/index.do` | weak=['ITEM_DETAIL'] strong=[] (n_fired=1) |

#### `T03_MULTI_STRONG_CANDIDATE` — 강한 후보가 둘 이상

**정의.** R 과 E 를 동시에 만족하는 branch 가 2개 이상이다. SSOT §6 '두 개 이상 강한 후보' 분기로, 첫 매칭을 고르지 않고 NLP fallback(§7)으로 넘긴다.

**N.** 56 중 **6** (11%) · abstain 40 중 **6** (15%) · 미확정 45 중 6 · rule 확정 11 중 0

**해결가능성.** `DEFINITION_OR_FALLBACK` — SSOT §6 이 이미 NLP fallback 으로 보내라고 규정한 분기다. 같은 페이지를 더 관측해도 두 후보가 동시에 참인 사실은 변하지 않는다. §6 precedence 를 순서로 확정하거나 §7 fallback 이 갈라야 한다.

**evidence example** (최대 5건)

| wtg | service | prior | leaf | 최종 URL | 이 유형으로 분류한 관측값 |
|---|---|---|---|---|---|
| `088809bf9b31` | 삼성카드 | FINANCIAL_ACTION_ENTRY | AU__MULTI_CANDIDATE | `https://www.samsungcard.com/personal/main/UHPPCO0101M0.jsp` | strong=['QUERY', 'UTILITY_ENTRY'] |
| `46e5a43370f7` | 당근 | COMMUNICATION_ENTRY | AU__MULTI_CANDIDATE | `https://www.daangn.com/kr/` | strong=['QUERY', 'COMMUNICATION_ENTRY'] |
| `6d5510a695d0` | 네이버 | QUERY | AU__MULTI_CANDIDATE | `https://m.naver.com/` | strong=['QUERY', 'CONTENT_OPEN'] |
| `91b952863c62` | 다음 | QUERY | AU__MULTI_CANDIDATE | `https://m.daum.net/?nil_top=mobile` | strong=['QUERY', 'CONTENT_OPEN', 'PLACE_LOOKUP', 'COMMUNICATION_ENTRY'] |
| `b728911c9782` | 현대카드 | FINANCIAL_ACTION_ENTRY | AU__MULTI_CANDIDATE | `https://mycompany.hyundaicard.com/cm/mn/CMMN1001.do?_method=` | strong=['FINANCIAL_ACTION_ENTRY', 'UTILITY_ENTRY'] |

#### `T04_SHARED_LIST_SIGNAL` — 같은 신호를 여러 archetype 이 공유 (list-family)

**정의.** list-family 4개 branch(CONTENT_OPEN / ITEM_DETAIL / PLACE_LOOKUP / COMMUNICATION_ENTRY) 중 2개 이상의 **R 술어**가 같은 target 에서 발화했다. 이들 R 은 모두 '반복 항목 >= 3' 형태라 하나의 카드 목록 관측이 여러 archetype 의 region 정의를 동시에 만족시킨다. region 관측을 아무리 더 모아도 서로를 배제하지 못하고, endpoint(E) 또는 §6 precedence 만이 가른다.

**N.** 56 중 **4** (7%) · abstain 40 중 **2** (5%) · 미확정 45 중 2 · rule 확정 11 중 2

**해결가능성.** `DEFINITION_RESOLVABLE` — region 술어가 서로 배타적이지 않게 조작화되어 있다. region 증거를 더 모아도 배타성이 생기지 않는다. 정의(§5 region predicate 의 상호배타화 또는 §6 precedence 명문화)로만 풀린다.

**evidence example** (최대 5건)

| wtg | service | prior | leaf | 최종 URL | 이 유형으로 분류한 관측값 |
|---|---|---|---|---|---|
| `5c614fc99631` | 홈앤쇼핑 | ITEM_DETAIL | ITEM_DETAIL | `https://m.hnsmall.com/main` | list-family R 동시발화=['ITEM_DETAIL', 'PLACE_LOOKUP'] |
| `888d37f34b5d` | 롯데홈쇼핑 | ITEM_DETAIL | AU__NO_STRONG_CANDIDATE | `https://www.lottehomeshopping.com/user/main/index.lotte` | list-family R 동시발화=['CONTENT_OPEN', 'ITEM_DETAIL'] |
| `88cb7f1e54f2` | 롯데마트 | ITEM_DETAIL | ITEM_DETAIL | `https://lottemartzetta.com/` | list-family R 동시발화=['ITEM_DETAIL', 'PLACE_LOOKUP'] |
| `91b952863c62` | 다음 | QUERY | AU__MULTI_CANDIDATE | `https://m.daum.net/?nil_top=mobile` | list-family R 동시발화=['CONTENT_OPEN', 'PLACE_LOOKUP', 'COMMUNICATION_ENTRY'] |

### family — SURFACE_IDENTITY

#### `T05_GENERIC_BRAND_LANDING` — 일반 기업/브랜드 소개 면

**정의.** 다음 중 하나 이상: (a) SSOT §7 텍스트 묶음 안에 기업/브랜드 어휘(회사소개·IR·채용·보도자료·브랜드 스토리·입점문의·서비스 소개 등)가 3회 이상 등장, (b) probe 최종 URL 경로가 기업/소개 경로 마커(/about /intro /brand/ /service- /solution/ /company /page/detail /chrome /newsroom /introduce)에 일치. **그리고** strong branch 가 없다(=기능 표면이 관측되지 않았다). 즉 target URL 이 서비스의 기능면이 아니라 그 서비스를 '설명하는' 면으로 해석된 경우다.

**N.** 56 중 **16** (29%) · abstain 40 중 **15** (38%) · 미확정 45 중 16 · rule 확정 11 중 0

**해결가능성.** `TARGET_RESOLVABLE__UNDECIDABLE_AT_THIS_URL` — 이 URL 이 실제로 기업/브랜드 소개면이라면 그 면에는 대표 기능 표면이 존재하지 않는다. 같은 URL 에서 evidence 를 더 모아도 없는 표면이 생기지 않는다. target URL 재정의(연구 frame) 문제다.

**evidence example** (최대 5건)

| wtg | service | prior | leaf | 최종 URL | 이 유형으로 분류한 관측값 |
|---|---|---|---|---|---|
| `054d78ed187c` | 쿠팡이츠 | ITEM_DETAIL | AU__NO_STRONG_CANDIDATE | `https://www.coupangeats.com/` | brand_lex=17 path_marker=False strong=[] |
| `0f3bdb2bd0bb` | 탑마트 | ITEM_DETAIL | AU__NO_STRONG_CANDIDATE | `https://www.seowon.com/` | brand_lex=14 path_marker=False strong=[] |
| `12e3942c0495` | GS25 | ITEM_DETAIL | AU__NO_STRONG_CANDIDATE | `https://www.gsretail.com/brand/gs25` | brand_lex=16 path_marker=True strong=[] |
| `35319a420294` | 토스 | FINANCIAL_ACTION_ENTRY | AU__NO_STRONG_CANDIDATE | `https://toss.im/` | brand_lex=4 path_marker=False strong=[] |
| `60d4d22e3809` | 티맵 | PLACE_LOOKUP | AU__NO_STRONG_CANDIDATE | `https://www.tmapmobility.com/` | brand_lex=4 path_marker=False strong=[] |

#### `T06_APP_INSTALL_SURFACE` — 앱 설치/전환 유도 면

**정의.** SSOT §7 텍스트 묶음에 앱스토어/구글플레이/앱 다운로드/앱에서 열기 계열 어휘가 1회 이상 등장하거나, Rule DT 의 `is_app_interstitial` 술어가 1이다. 웹 표면의 대표행동이 '앱으로 나가기'로 대체된 상태.

**하위구분.** `dismissible_control_present_n`=12 · `no_dismiss_control_n`=0

**N.** 56 중 **12** (21%) · abstain 40 중 **11** (28%) · 미확정 45 중 11 · rule 확정 11 중 1

**해결가능성.** `TARGET_RESOLVABLE__UNDECIDABLE_AT_THIS_URL` — 웹 표면의 대표행동이 '앱으로 나가기'다. 앱 안쪽은 이 연구의 관측범위(공개 web surface) 밖이다. 다만 앱 유도가 dismissible interstitial 인 경우는 수집으로 우회 가능하므로 하위분리해 센다.

**evidence example** (최대 5건)

| wtg | service | prior | leaf | 최종 URL | 이 유형으로 분류한 관측값 |
|---|---|---|---|---|---|
| `054d78ed187c` | 쿠팡이츠 | ITEM_DETAIL | AU__NO_STRONG_CANDIDATE | `https://www.coupangeats.com/` | app_lex=9 |
| `35319a420294` | 토스 | FINANCIAL_ACTION_ENTRY | AU__NO_STRONG_CANDIDATE | `https://toss.im/` | app_lex=4 |
| `49a5eca8b58f` | 11번가 | ITEM_DETAIL | AU__NO_STRONG_CANDIDATE | `http://m.11st.co.kr/page/main/home` | app_lex=1 |
| `5beeafeac2e2` | TikTok | CONTENT_OPEN | AU__NO_STRONG_CANDIDATE | `https://www.tiktok.com/` | app_lex=0 |
| `5ede56738376` | Instagram | COMMUNICATION_ENTRY | AU__NO_STRONG_CANDIDATE | `https://www.instagram.com/` | app_lex=0 |

#### `T07_REPRESENTATIVE_SURFACE_ABSENT` — 대표 표면 자체가 관측되지 않음 (Stage0 NO 분기)

**정의.** Stage0 에서 S0_NO_RENDERED_SURFACE 또는 S0_ERROR_PAGE 가 발화하여 Stage3 가 평가되지도 않았다. frozen evidence 안에 렌더된 공개 web surface 가 없거나 error/not-found 면이다. leaf = UNDETERMINED_URL_EVIDENCE.

**N.** 56 중 **5** (9%) · abstain 40 중 **0** (0%) · 미확정 45 중 5 · rule 확정 11 중 0

**해결가능성.** `TARGET_RESOLVABLE__UNDECIDABLE_AT_THIS_URL` — Stage0 NO 분기. 렌더된 표면이 없거나 error 면이다. SSOT §2 가 이미 확정을 금지한다.

**evidence example** (최대 5건)

| wtg | service | prior | leaf | 최종 URL | 이 유형으로 분류한 관측값 |
|---|---|---|---|---|---|
| `64d30ef262d8` | 신한 SOL뱅크 | FINANCIAL_ACTION_ENTRY | UNDETERMINED_URL_EVIDENCE | `nan` | stage0=['S0_NO_RENDERED_SURFACE'] |
| `699a5e2f3f41` | 카카오톡 | COMMUNICATION_ENTRY | UNDETERMINED_URL_EVIDENCE | `https://www.kakaocorp.com/page/detail/10810?lang=ENG` | stage0=['S0_ERROR_PAGE'] |
| `95967b506836` | NH스마트뱅킹 | FINANCIAL_ACTION_ENTRY | UNDETERMINED_URL_EVIDENCE | `https://m.nonghyup.com/servlet/PMMNP0001R.view` | stage0=['S0_NO_RENDERED_SURFACE'] |
| `ef06dc942ef3` | 롯데하이마트 | ITEM_DETAIL | UNDETERMINED_URL_EVIDENCE | `nan` | stage0=['S0_NO_RENDERED_SURFACE'] |
| `fb3d1841dddf` | NH콕뱅크 | FINANCIAL_ACTION_ENTRY | UNDETERMINED_URL_EVIDENCE | `https://m.nonghyup.com/servlet/PMMNP0001R.view` | stage0=['S0_NO_RENDERED_SURFACE'] |

#### `T08_LOGIN_DOMINATED` — 로그인 지배 표면

**정의.** 다음 중 하나: (a) `gate_password_input_n >= 1`(실제 credential 입력칸 관측), (b) probe 최종 URL 경로에 login/signin, (c) SSOT §7 텍스트 묶음의 로그인/인증 어휘 3회 이상. 하위구분 — GATE_REACHED: (a) 성립, GATE_NOT_REACHED: (a) 불성립이고 (b)/(c)만 성립(= 로그인 '버튼'만 보이고 실제 gate 구조에는 도달하지 못함). SSOT §5 Branch F 의 E_F 는 실제 gate 도달을 요구하므로 GATE_NOT_REACHED 는 endpoint 술어를 발화시키지 못한다.

**하위구분.** `GATE_NOT_REACHED`=14 · `GATE_REACHED`=3

**N.** 56 중 **17** (30%) · abstain 40 중 **12** (30%) · 미확정 45 중 12 · rule 확정 11 중 5

**해결가능성.** `SPLIT` — GATE_REACHED 는 오히려 E_F 를 발화시킬 수 있는 정상 증거다. GATE_NOT_REACHED 는 상호작용 1스텝(로그인 버튼 클릭)으로 gate 구조에 도달하면 해결 가능하다 — COLLECTION_RESOLVABLE.

**evidence example** (최대 5건)

| wtg | service | prior | leaf | 최종 URL | 이 유형으로 분류한 관측값 |
|---|---|---|---|---|---|
| `088809bf9b31` | 삼성카드 | FINANCIAL_ACTION_ENTRY | AU__MULTI_CANDIDATE | `https://www.samsungcard.com/personal/main/UHPPCO0101M0.jsp` | login_lex=9 password_n=0.0 login_url=False subtype=GATE_NOT_REACHED |
| `13ed070478ef` | Netflix | CONTENT_OPEN | AU__NO_STRONG_CANDIDATE | `https://www.netflix.com/kr/login?serverState=Bgi8vuvcAxK1AZY` | login_lex=5 password_n=1.0 login_url=True subtype=GATE_REACHED |
| `22ffba7a86ea` | 코스트코 | ITEM_DETAIL | QUERY | `https://www.costco.co.kr/` | login_lex=9 password_n=0.0 login_url=False subtype=GATE_NOT_REACHED |
| `5beeafeac2e2` | TikTok | CONTENT_OPEN | AU__NO_STRONG_CANDIDATE | `https://www.tiktok.com/` | login_lex=0 password_n=4.0 login_url=False subtype=GATE_REACHED |
| `5c614fc99631` | 홈앤쇼핑 | ITEM_DETAIL | ITEM_DETAIL | `https://m.hnsmall.com/main` | login_lex=4 password_n=0.0 login_url=False subtype=GATE_NOT_REACHED |

### family — CAPTURE_QUALITY

#### `T09_CLIENT_RENDER_SPARSE` — SPA/클라이언트 렌더로 구조가 비어 있음

**정의.** SSOT §7 이 요구하는 8개 텍스트 구성요소(title, headings, landmarks, nav_links, buttons, aria_labels, form_labels, card_texts) 중 비어 있지 않은 것이 2개 이하거나, `dom_body_empty == 1`. DOM 바이트는 클 수 있으나(스크립트 shell) 구조화된 표현이 만들어지지 않는 상태.

**N.** 56 중 **6** (11%) · abstain 40 중 **2** (5%) · 미확정 45 중 6 · rule 확정 11 중 0

**해결가능성.** `COLLECTION_RESOLVABLE` — 같은 수집 스택에서 다른 target 은 §7 구성요소를 8개 중 다수 확보했다. 즉 실패는 표면의 성질이 아니라 캡처 시점/방식이다. hydration 대기·AX 트리 사용·렌더 후 재캡처로 해결 가능하다.

**evidence example** (최대 5건)

| wtg | service | prior | leaf | 최종 URL | 이 유형으로 분류한 관측값 |
|---|---|---|---|---|---|
| `517b8047eb5b` | 농협하나로마트 | ITEM_DETAIL | AU__NO_STRONG_CANDIDATE | `https://www.nhhanaro.co.kr/mbshome/mbs/nahh007/index.do` | SSOT§7 구성요소 2/8 |
| `64d30ef262d8` | 신한 SOL뱅크 | FINANCIAL_ACTION_ENTRY | UNDETERMINED_URL_EVIDENCE | `nan` | SSOT§7 구성요소 1/8 |
| `95967b506836` | NH스마트뱅킹 | FINANCIAL_ACTION_ENTRY | UNDETERMINED_URL_EVIDENCE | `https://m.nonghyup.com/servlet/PMMNP0001R.view` | SSOT§7 구성요소 1/8 |
| `d5ae5426eac2` | 모니모 | FINANCIAL_ACTION_ENTRY | AU__NO_STRONG_CANDIDATE | `https://www.monimo.com/monimo/homepage/main/PGIFPCCHomepageM` | SSOT§7 구성요소 2/8 |
| `ef06dc942ef3` | 롯데하이마트 | ITEM_DETAIL | UNDETERMINED_URL_EVIDENCE | `nan` | SSOT§7 구성요소 0/8 |

#### `T10A_TEXT_ENCODING_CORRUPTION` — 텍스트 인코딩 훼손 (mojibake)

**정의.** 관측표의 `encoding_degraded == 1`. DOM 텍스트 디코딩이 깨져 어휘 술어가 무력화된다.

**N.** 56 중 **8** (14%) · abstain 40 중 **7** (18%) · 미확정 45 중 7 · rule 확정 11 중 1

**해결가능성.** `COLLECTION_RESOLVABLE` — 디코딩 결함이다. dom_encoding 이 관측표에 남아 있고 재디코딩은 결정적(deterministic)이다.

**evidence example** (최대 5건)

| wtg | service | prior | leaf | 최종 URL | 이 유형으로 분류한 관측값 |
|---|---|---|---|---|---|
| `0f3bdb2bd0bb` | 탑마트 | ITEM_DETAIL | AU__NO_STRONG_CANDIDATE | `https://www.seowon.com/` | encoding_degraded=1 |
| `190b4501e441` | V3 Mobile Plus | UTILITY_ENTRY | AU__NO_STRONG_CANDIDATE | `https://mplweb.ahnlab.com/mplweb/v3mp/main_android.do` | encoding_degraded=1 |
| `24e6654bfd1a` | YouTube | CONTENT_OPEN | AU__NO_STRONG_CANDIDATE | `https://m.youtube.com/` | encoding_degraded=1 |
| `8fd5d30f8b1d` | 하나은행 | FINANCIAL_ACTION_ENTRY | AU__NO_STRONG_CANDIDATE | `https://m.kebhana.com/` | encoding_degraded=1 |
| `b8b226f9fe32` | KB Pay | FINANCIAL_ACTION_ENTRY | AU__NO_STRONG_CANDIDATE | `https://mbiz.kbcard.com/CXEHMSVCD0012.cms` | encoding_degraded=1 |

#### `T10B_TEXT_CAP_TRUNCATION` — 텍스트/후보 절단 (cap)

**정의.** 관측표의 `cap_any == 1`(l0_probe.js 상수 cap 에 도달한 측정이 하나 이상) 이거나 `gate_visible_text_len >= 3900`(미보고 절단점 4000자 slice 근접). 관측이 상한에서 잘려 실제 구조의 일부만 남았다.

**N.** 56 중 **15** (27%) · abstain 40 중 **8** (20%) · 미확정 45 중 8 · rule 확정 11 중 7

**해결가능성.** `COLLECTION_RESOLVABLE` — cap 은 l0_probe.js 의 상수다(RQ-D9 가 상수값을 코드에서 확인). 상수를 올리면 관측이 늘어난다.

**evidence example** (최대 5건)

| wtg | service | prior | leaf | 최종 URL | 이 유형으로 분류한 관측값 |
|---|---|---|---|---|---|
| `088809bf9b31` | 삼성카드 | FINANCIAL_ACTION_ENTRY | AU__MULTI_CANDIDATE | `https://www.samsungcard.com/personal/main/UHPPCO0101M0.jsp` | cap_any=1 또는 gate_visible_text_len>=3900 |
| `0ee385d0c964` | 홈플러스 | ITEM_DETAIL | ITEM_DETAIL | `https://mfront.homeplus.co.kr/` | cap_any=1 또는 gate_visible_text_len>=3900 |
| `22ffba7a86ea` | 코스트코 | ITEM_DETAIL | QUERY | `https://www.costco.co.kr/` | cap_any=1 또는 gate_visible_text_len>=3900 |
| `377983572bd3` | 다이소 | ITEM_DETAIL | QUERY | `https://www.daiso.co.kr/` | cap_any=1 또는 gate_visible_text_len>=3900 |
| `49a5eca8b58f` | 11번가 | ITEM_DETAIL | AU__NO_STRONG_CANDIDATE | `http://m.11st.co.kr/page/main/home` | cap_any=1 또는 gate_visible_text_len>=3900 |

#### `T11_OVERLAY_OBSTRUCTED` — 오버레이/모달로 대표 표면이 가려짐

**정의.** RQ-D13A 의 overlay provenance 분류가 H1_MODAL 또는 H2_GENERIC_LOADING_MASK 이거나, 관측표의 `body_scroll_locked == 1`. 캡처 시점에 대표 표면이 덮여 있었다.

**N.** 56 중 **14** (25%) · abstain 40 중 **9** (22%) · 미확정 45 중 11 · rule 확정 11 중 3

**해결가능성.** `COLLECTION_RESOLVABLE_PARTIAL` — RQ-D13 의 dismissal 실험에서 248 스텝 중 166 스텝이 화면을 바꿨다(=해제가 실제로 작동). 다만 어떤 스텝으로도 변화가 없던 target 이 6건 있어 전부가 풀리지는 않는다.

**evidence example** (최대 5건)

| wtg | service | prior | leaf | 최종 URL | 이 유형으로 분류한 관측값 |
|---|---|---|---|---|---|
| `088809bf9b31` | 삼성카드 | FINANCIAL_ACTION_ENTRY | AU__MULTI_CANDIDATE | `https://www.samsungcard.com/personal/main/UHPPCO0101M0.jsp` | overlay=H2_GENERIC_FIXED_OR_HIGHZ scroll_locked 포함 |
| `0ee385d0c964` | 홈플러스 | ITEM_DETAIL | ITEM_DETAIL | `https://mfront.homeplus.co.kr/` | overlay=H2_GENERIC_FIXED_OR_HIGHZ scroll_locked 포함 |
| `190b4501e441` | V3 Mobile Plus | UTILITY_ENTRY | AU__NO_STRONG_CANDIDATE | `https://mplweb.ahnlab.com/mplweb/v3mp/main_android.do` | overlay=H2_GENERIC_FIXED_OR_HIGHZ scroll_locked 포함 |
| `5beeafeac2e2` | TikTok | CONTENT_OPEN | AU__NO_STRONG_CANDIDATE | `https://www.tiktok.com/` | overlay=H2_GENERIC_FIXED_OR_HIGHZ scroll_locked 포함 |
| `7f6f1aa6dd21` | 이마트 | ITEM_DETAIL | AU__NO_STRONG_CANDIDATE | `https://eapp.emart.com/main/main.do` | overlay=H1_MODAL scroll_locked 포함 |

#### `T12_DEGENERATE_OR_DUPLICATE_CAPTURE` — 퇴화 캡처 / 중복 캡처

**정의.** RQ-D13 이 식별한 degenerate capture(빈 CSS + 빈 DOM body) 이거나, 다른 target 과 requested URL 이 동일해 같은 증거를 공유한다. 이 target 의 증거는 이 target 을 설명하지 못한다.

**N.** 56 중 **4** (7%) · abstain 40 중 **0** (0%) · 미확정 45 중 4 · rule 확정 11 중 0

**해결가능성.** `COLLECTION_RESOLVABLE` — 빈 CSS·빈 DOM·동일 URL 공유는 수집기 결함이다. 재수집으로 해결된다.

**evidence example** (최대 5건)

| wtg | service | prior | leaf | 최종 URL | 이 유형으로 분류한 관측값 |
|---|---|---|---|---|---|
| `64d30ef262d8` | 신한 SOL뱅크 | FINANCIAL_ACTION_ENTRY | UNDETERMINED_URL_EVIDENCE | `nan` | degenerate capture 또는 동일 requested URL 공유 |
| `95967b506836` | NH스마트뱅킹 | FINANCIAL_ACTION_ENTRY | UNDETERMINED_URL_EVIDENCE | `https://m.nonghyup.com/servlet/PMMNP0001R.view` | degenerate capture 또는 동일 requested URL 공유 |
| `ef06dc942ef3` | 롯데하이마트 | ITEM_DETAIL | UNDETERMINED_URL_EVIDENCE | `nan` | degenerate capture 또는 동일 requested URL 공유 |
| `fb3d1841dddf` | NH콕뱅크 | FINANCIAL_ACTION_ENTRY | UNDETERMINED_URL_EVIDENCE | `https://m.nonghyup.com/servlet/PMMNP0001R.view` | degenerate capture 또는 동일 requested URL 공유 |

### family — PRIOR_CONFLICT

#### `T13_PRIOR_CONTRADICTS_STRUCTURE` — business prior 가 관측 구조와 어긋남

**정의.** prior_archetype 에 해당하는 branch 의 R 과 E 가 **둘 다** 발화하지 않았는데, 다른 branch 에서는 최소 하나의 술어가 발화했다. 관측된 구조는 prior 가 아닌 다른 archetype 을 가리킨다. prior 는 gold label 이 아니므로 이것은 'rule 이 틀렸다'가 아니라 '둘이 어긋난다'는 관측이다.

**N.** 56 중 **17** (30%) · abstain 40 중 **13** (32%) · 미확정 45 중 13 · rule 확정 11 중 4

**해결가능성.** `NOT_AN_EVIDENCE_PROBLEM` — prior 는 gold 가 아니다. 이 유형은 evidence 부족이 아니라 prior 와 관측의 불일치이며, label 없이는 어느 쪽이 틀렸는지 D 가 판정할 수 없다. 더 모아도 D 혼자서는 닫히지 않는다.

**evidence example** (최대 5건)

| wtg | service | prior | leaf | 최종 URL | 이 유형으로 분류한 관측값 |
|---|---|---|---|---|---|
| `12e3942c0495` | GS25 | ITEM_DETAIL | AU__NO_STRONG_CANDIDATE | `https://www.gsretail.com/brand/gs25` | prior=ITEM_DETAIL branch 침묵, 타 branch 발화 n=2 |
| `13ed070478ef` | Netflix | CONTENT_OPEN | AU__NO_STRONG_CANDIDATE | `https://www.netflix.com/kr/login?serverState=Bgi8vuvcAxK1AZY` | prior=CONTENT_OPEN branch 침묵, 타 branch 발화 n=3 |
| `22ffba7a86ea` | 코스트코 | ITEM_DETAIL | QUERY | `https://www.costco.co.kr/` | prior=ITEM_DETAIL branch 침묵, 타 branch 발화 n=5 |
| `24e6654bfd1a` | YouTube | CONTENT_OPEN | AU__NO_STRONG_CANDIDATE | `https://m.youtube.com/` | prior=CONTENT_OPEN branch 침묵, 타 branch 발화 n=1 |
| `49a5eca8b58f` | 11번가 | ITEM_DETAIL | AU__NO_STRONG_CANDIDATE | `http://m.11st.co.kr/page/main/home` | prior=ITEM_DETAIL branch 침묵, 타 branch 발화 n=2 |

## 중복 행렬

abstain 40 기준 target 당 평균 유형 수 **2.82**, 중앙값 3, 최대 5. 유형 분포 {'3': 23, '4': 11, '2': 12, '1': 6, '5': 3, '0': 1}.

대각선 = 그 유형의 N (abstain 40 기준), 비대각선 = 동시 보유 target 수.

| | T01 | T02 | T03 | T04 | T05 | T06 | T07 | T08 | T09 | T10A | T10B | T11 | T12 | T13 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| **T01** | 12 | · | · | · | 7 | 3 | · | 4 | 1 | 6 | · | 1 | · | · |
| **T02** | · | 22 | · | 1 | 8 | 7 | · | 5 | 1 | 1 | 5 | 6 | · | 13 |
| **T03** | · | · | 6 | 1 | · | 1 | · | 3 | · | · | 3 | 2 | · | · |
| **T04** | · | 1 | 1 | 2 | 1 | · | · | · | · | · | 1 | · | · | · |
| **T05** | 7 | 8 | · | 1 | 15 | 4 | · | 4 | · | 3 | 2 | 2 | · | 2 |
| **T06** | 3 | 7 | 1 | · | 4 | 11 | · | 5 | · | · | 2 | 2 | · | 6 |
| **T07** | · | · | · | · | · | · | · | · | · | · | · | · | · | · |
| **T08** | 4 | 5 | 3 | · | 4 | 5 | · | 12 | · | 3 | 3 | 3 | · | 5 |
| **T09** | 1 | 1 | · | · | · | · | · | · | 2 | · | · | · | · | · |
| **T10A** | 6 | 1 | · | · | 3 | · | · | 3 | · | 7 | · | 1 | · | 1 |
| **T10B** | · | 5 | 3 | 1 | 2 | 2 | · | 3 | · | · | 8 | 3 | · | 3 |
| **T11** | 1 | 6 | 2 | · | 2 | 2 | · | 3 | · | 1 | 3 | 9 | · | 3 |
| **T12** | · | · | · | · | · | · | · | · | · | · | · | · | · | · |
| **T13** | · | 13 | · | · | 2 | 6 | · | 5 | · | 1 | 3 | 3 | · | 13 |

두드러진 동시발생 (≥5건):

- `T02_WEAK_ONE_SIDED_EVIDENCE` × `T13_PRIOR_CONTRADICTS_STRUCTURE` = **13**
- `T02_WEAK_ONE_SIDED_EVIDENCE` × `T05_GENERIC_BRAND_LANDING` = **8**
- `T01_NO_PREDICATE_FIRED` × `T05_GENERIC_BRAND_LANDING` = **7**
- `T02_WEAK_ONE_SIDED_EVIDENCE` × `T06_APP_INSTALL_SURFACE` = **7**
- `T01_NO_PREDICATE_FIRED` × `T10A_TEXT_ENCODING_CORRUPTION` = **6**
- `T02_WEAK_ONE_SIDED_EVIDENCE` × `T11_OVERLAY_OBSTRUCTED` = **6**
- `T06_APP_INSTALL_SURFACE` × `T13_PRIOR_CONTRADICTS_STRUCTURE` = **6**
- `T02_WEAK_ONE_SIDED_EVIDENCE` × `T08_LOGIN_DOMINATED` = **5**
- `T02_WEAK_ONE_SIDED_EVIDENCE` × `T10B_TEXT_CAP_TRUNCATION` = **5**
- `T06_APP_INSTALL_SURFACE` × `T08_LOGIN_DOMINATED` = **5**
- `T08_LOGIN_DOMINATED` × `T13_PRIOR_CONTRADICTS_STRUCTURE` = **5**

유형이 하나도 붙지 않은 target: ['efda6e0b8457d63c'] (rule 이 깨끗하게 확정한 케이스 — taxonomy 가 정상 케이스를 유형으로 오염시키지 않는다는 뜻).

## T01 은 원인이 아니다 — 분해

`T01_NO_PREDICATE_FIRED` 12건 중 표면정체성/캡처품질 유형으로 설명되는 것 **11건**, 미설명 1건 (`['51484a735cdb487b']`).

| 설명 유형 | 겹치는 T01 건수 |
|---|---|
| `T05_GENERIC_BRAND_LANDING` | 7 |
| `T06_APP_INSTALL_SURFACE` | 3 |
| `T08_LOGIN_DOMINATED` | 4 |
| `T09_CLIENT_RENDER_SPARSE` | 1 |
| `T10A_TEXT_ENCODING_CORRUPTION` | 6 |
| `T11_OVERLAY_OBSTRUCTED` | 1 |

> 즉 '증거가 부족하다'는 leaf 문구는 진단이 아니다. 진단은 '이 URL 은 기능면이 아니다' 또는 '캡처가 구조를 잡지 못했다' 둘 중 하나이며, 이 둘은 처방이 정반대다.

## 해결 가능 vs 원리적 미결정

**배정 규칙.** 한 target 이 여러 유형에 해당하므로, 해결가능성 집계에는 고정 우선순위 (표면부재 > 퇴화캡처 > 렌더희소 > 인코딩 > 브랜드면 > 앱면 > 오버레이 > 절단 > 로그인 > 공유신호 > 다중강후보 > 약한증거 > prior충돌 > 무발화) 로 primary type 을 하나 정한다. 우선순위는 '수집으로 고칠 수 있는 것' 보다 '표면이 애초에 없는 것' 을 앞에 둔다 — 뒤집으면 미결정이 과소계상된다.

| 분모 | RESOLVABLE | UNDECIDABLE_AT_THIS_URL | 기타 |
|---|---|---|---|
| 전체 56 | 27 | 27 | 2 |
| abstain 40 | 20 | 19 | 1 |
| 미확정 45 | 20 | 24 | 1 |

### 우선순위에 의존하지 않는 하한/상한

primary type 배정은 우선순위 규칙에 흔들린다. 흔들리지 않는 집계는 이것이다 (abstain 40 기준):

- 표면부재 계열(T05/T06/T07) 유형을 **하나라도** 갖는 target — **22**
- 캡처품질 계열(T09/T10A/T10B/T11/T12) 유형을 **하나라도** 갖는 target — **22**
- **둘 다** 갖는 target — **10** ← 수집을 고쳐도 표면이 없어 안 되는 교집합
- 둘 다 없는 target — **6**

**민감도.** 우선순위를 완전히 뒤집으면 abstain 40 배정이 {'OTHER': 12, 'RESOLVABLE': 15, 'UNDECIDABLE_AT_THIS_URL': 13} 로 바뀐다. primary type 배정은 규칙 의존적이므로, 결론은 위의 우선순위-무관 하한/상한으로만 읽어야 한다.

### 유형별 판정과 근거

| 유형 | 판정 | 근거의 성격 |
|---|---|---|
| `T01` 어떤 술어도 발화하지 않음 (insufficient evidence) | `DECOMPOSES` | 증상이지 원인이 아니다. 아래 표면/수집 유형으로 분해한 뒤 판단한다.… |
| `T02` 한쪽 신호만 있는 약한 후보 (region 만 또는 endpoint 만) | `COLLECTION_OR_DEFINITION` | R 또는 E 중 한쪽만 붙었다. 누락된 쪽이 endpoint 인 경우는 상호작용 1스텝 수집으로 확인 가능하고, 누락된 쪽이 region 인 경우는 §5 region 정의의 조작화 문제다.… |
| `T03` 강한 후보가 둘 이상 | `DEFINITION_OR_FALLBACK` | SSOT §6 이 이미 NLP fallback 으로 보내라고 규정한 분기다. 같은 페이지를 더 관측해도 두 후보가 동시에 참인 사실은 변하지 않는다. §6 precedence 를 순서로 확정하거나 §7 fallback 이 갈라야 한다.… |
| `T04` 같은 신호를 여러 archetype 이 공유 (list-family) | `DEFINITION_RESOLVABLE` | region 술어가 서로 배타적이지 않게 조작화되어 있다. region 증거를 더 모아도 배타성이 생기지 않는다. 정의(§5 region predicate 의 상호배타화 또는 §6 precedence 명문화)로만 풀린다.… |
| `T05` 일반 기업/브랜드 소개 면 | `TARGET_RESOLVABLE__UNDECIDABLE_AT_THIS_URL` | 이 URL 이 실제로 기업/브랜드 소개면이라면 그 면에는 대표 기능 표면이 존재하지 않는다. 같은 URL 에서 evidence 를 더 모아도 없는 표면이 생기지 않는다. target URL 재정의(연구 frame) 문제다.… |
| `T06` 앱 설치/전환 유도 면 | `TARGET_RESOLVABLE__UNDECIDABLE_AT_THIS_URL` | 웹 표면의 대표행동이 '앱으로 나가기'다. 앱 안쪽은 이 연구의 관측범위(공개 web surface) 밖이다. 다만 앱 유도가 dismissible interstitial 인 경우는 수집으로 우회 가능하므로 하위분리해 센다.… |
| `T07` 대표 표면 자체가 관측되지 않음 (Stage0 NO 분기) | `TARGET_RESOLVABLE__UNDECIDABLE_AT_THIS_URL` | Stage0 NO 분기. 렌더된 표면이 없거나 error 면이다. SSOT §2 가 이미 확정을 금지한다.… |
| `T08` 로그인 지배 표면 | `SPLIT` | GATE_REACHED 는 오히려 E_F 를 발화시킬 수 있는 정상 증거다. GATE_NOT_REACHED 는 상호작용 1스텝(로그인 버튼 클릭)으로 gate 구조에 도달하면 해결 가능하다 — COLLECTION_RESOLVABLE.… |
| `T09` SPA/클라이언트 렌더로 구조가 비어 있음 | `COLLECTION_RESOLVABLE` | 같은 수집 스택에서 다른 target 은 §7 구성요소를 8개 중 다수 확보했다. 즉 실패는 표면의 성질이 아니라 캡처 시점/방식이다. hydration 대기·AX 트리 사용·렌더 후 재캡처로 해결 가능하다.… |
| `T10A` 텍스트 인코딩 훼손 (mojibake) | `COLLECTION_RESOLVABLE` | 디코딩 결함이다. dom_encoding 이 관측표에 남아 있고 재디코딩은 결정적(deterministic)이다.… |
| `T10B` 텍스트/후보 절단 (cap) | `COLLECTION_RESOLVABLE` | cap 은 l0_probe.js 의 상수다(RQ-D9 가 상수값을 코드에서 확인). 상수를 올리면 관측이 늘어난다.… |
| `T11` 오버레이/모달로 대표 표면이 가려짐 | `COLLECTION_RESOLVABLE_PARTIAL` | RQ-D13 의 dismissal 실험에서 248 스텝 중 166 스텝이 화면을 바꿨다(=해제가 실제로 작동). 다만 어떤 스텝으로도 변화가 없던 target 이 6건 있어 전부가 풀리지는 않는다.… |
| `T12` 퇴화 캡처 / 중복 캡처 | `COLLECTION_RESOLVABLE` | 빈 CSS·빈 DOM·동일 URL 공유는 수집기 결함이다. 재수집으로 해결된다.… |
| `T13` business prior 가 관측 구조와 어긋남 | `NOT_AN_EVIDENCE_PROBLEM` | prior 는 gold 가 아니다. 이 유형은 evidence 부족이 아니라 prior 와 관측의 불일치이며, label 없이는 어느 쪽이 틀렸는지 D 가 판정할 수 없다. 더 모아도 D 혼자서는 닫히지 않는다.… |

## coverage ↔ confidence trade-off

> threshold 를 선언하지 않는다. SSOT §7 은 운영 threshold 를 independent label calibration split 에서 정하라고 하고, D 는 그 label 을 열지 않았다. 여기 있는 것은 곡선과 기울기 변화점뿐이다.

prior 다수 class 기저율 = **0.46** (ITEM_DETAIL 26/56). 이 선 아래의 prior_agreement 는 다수결보다 못한 것이다.

### 축 1 — rule 신뢰도

**정의.** branch b 의 발화강도 s_b = [R_b] + [E_b] (0..2). rule_conf = s_top1 + (s_top1 - s_top2)/2, 범위 0..3. 3 = 유일한 R∧E branch.

| threshold | coverage n | coverage | prior_agreement | Wilson95 |
|---|---|---|---|---|
| 0.00 | 56 | 1.000 | 0.286 | [0.18, 0.41] |
| 1.00 | 39 | 0.696 | 0.410 | [0.27, 0.57] |
| 1.50 | 27 | 0.482 | 0.481 | [0.31, 0.66] |
| 2.00 | 17 | 0.304 | 0.529 | [0.31, 0.74] |
| 2.50 | 11 | 0.196 | 0.545 | [0.28, 0.79] |
| 3.00 | 3 | 0.054 | 0.333 | [0.06, 0.79] |

구간별(marginal band) prior_agreement — 곡선의 누적치가 아니라 그 구간에 새로 들어온 target 만:

| band | n | prior_agreement |
|---|---|---|
| `[0,0.5)` | 17 | 0.000 |
| `[1,1.5)` | 12 | 0.250 |
| `[1.5,2)` | 10 | 0.400 |
| `[2,3)` | 14 | 0.571 |
| `[3,3.001)` | 3 | 0.333 |

**기울기가 가장 크게 꺾이는 곳** — coverage 0.70→1.00 구간에서 prior_agreement 가 0.410→0.286 로 떨어진다 (d(agreement)/d(coverage) = -0.41). 이 구간이 정확히 `rule_conf = 0` 인 17건, 즉 **아무 술어도 붙지 않은 target 을 강제로 끌어들이는 구간**이다. 이 17건의 band prior_agreement 는 **0.000** 이다 — 강제로 넣으면 한 건도 맞지 않는다.

### 축 2 — semantic margin

**정의.** bge-m3 + SSOT §7 A_SSOT_DEF prototype 을 D 가 독립 재계산. margin = cos(top1) - cos(top2). D 가 bge-m3 를 오프라인 캐시에서 직접 로드해 독립 재계산했다 (RF001-C 의 수치를 받아쓰지 않았다).

| threshold | coverage n | coverage | prior_agreement | Wilson95 |
|---|---|---|---|---|
| 0.0002 | 56 | 1.000 | 0.679 | [0.55, 0.79] |
| 0.0010 | 52 | 0.929 | 0.712 | [0.58, 0.82] |
| 0.0023 | 48 | 0.857 | 0.729 | [0.59, 0.83] |
| 0.0064 | 44 | 0.786 | 0.773 | [0.63, 0.87] |
| 0.0093 | 40 | 0.714 | 0.800 | [0.65, 0.90] |
| 0.0130 | 36 | 0.643 | 0.861 | [0.71, 0.94] |
| 0.0178 | 32 | 0.571 | 0.906 | [0.76, 0.97] |
| 0.0214 | 28 | 0.500 | 0.893 | [0.73, 0.96] |
| 0.0314 | 24 | 0.429 | 0.917 | [0.74, 0.98] |
| 0.0351 | 20 | 0.357 | 0.900 | [0.70, 0.97] |
| 0.0435 | 16 | 0.286 | 0.875 | [0.64, 0.97] |
| 0.0473 | 12 | 0.214 | 0.917 | [0.65, 0.99] |
| 0.0560 | 8 | 0.143 | 0.875 | [0.53, 0.98] |
| 0.0626 | 4 | 0.071 | 1.000 | [0.51, 1.00] |

| margin 5분위 band | n | prior_agreement |
|---|---|---|
| `[0.0001533,0.005606)` | 11 | 0.364 |
| `[0.005606,0.01668)` | 11 | 0.455 |
| `[0.01668,0.03273)` | 11 | 0.727 |
| `[0.03273,0.04752)` | 11 | 0.909 |
| `[0.04752,0.09169)` | 12 | 0.917 |

**어디서 꺾이는가.** 5분위 band 를 보면 하위 2분위(margin < 0.0167)의 prior_agreement 는 0.36 / 0.45 인데 상위 3분위는 0.73 / 0.91 / 0.92 다. **2분위와 3분위 사이가 꺾이는 지점이다.** 누적곡선에서도 coverage 1.00 → 0.57 구간에서 agreement 가 0.68 → 0.91 로 단조 상승하고, 그 아래로는 CI 만 넓어질 뿐 개선이 멈춘다. **이 관찰은 threshold 선언이 아니다** — SSOT §7 은 운영 threshold 를 independent label calibration split 에서 정하라고 하고, D 는 그 label 을 열지 않았다.

### brand leak 대조군

> prior_archetype 은 prior_business_domain 과 1:1 이다(RF001-B). 텍스트에 브랜드/도메인 어휘가 남아 있으면 semantic top1 의 prior_agreement 는 '표면 기능 식별'이 아니라 '브랜드로부터 prior 복원'을 재는 것일 수 있다. 아래 debranded 대조군과 비교해서만 읽어라.

**정의.** 동일 절차이나 blob 에서 서비스명·도메인 라벨을 제거한 대조군. RF001-B 가 brand leak 을 확인했으므로 semantic 축의 prior_agreement 가 '표면 기능을 읽은 것'인지 '브랜드로 prior 를 되찾은 것'인지 가른다.

| | coverage 1.00 | 0.79 | 0.57 | 0.36 |
|---|---|---|---|---|
| 원본 blob | 0.679 | 0.773 | 0.906 | 0.900 |
| debranded | 0.696 | 0.750 | 0.812 | 0.950 |

서비스명·도메인 라벨을 지워도 곡선이 거의 움직이지 않는다. semantic 축의 prior_agreement 는 브랜드 문자열만으로 prior 를 되찾는 것이 **아니다**. 다만 이 절제는 조악하다 — 상품명·업종어휘 같은 brand-adjacent 어휘는 그대로 남아 있고, prior_archetype 이 prior_business_domain 과 1:1 이라는 구조적 순환(RF001-B)까지 제거하지는 못한다.

### 축 3 — SSOT §6 → §7 캐스케이드

rule 이 유일 강후보를 찾으면 rule 로 확정하고, 아니면 semantic margin 이 임계 위일 때만 확정한다. coverage 분모는 56 고정.

| margin threshold | coverage n | coverage | prior_agreement |
|---|---|---|---|
| 0.0002 | 56 | 1.000 | 0.643 |
| 0.0012 | 51 | 0.911 | 0.667 |
| 0.0064 | 45 | 0.804 | 0.711 |
| 0.0096 | 40 | 0.714 | 0.725 |
| 0.0178 | 35 | 0.625 | 0.771 |
| 0.0234 | 30 | 0.536 | 0.767 |
| 0.0351 | 24 | 0.429 | 0.708 |
| 0.0450 | 20 | 0.357 | 0.650 |
| 0.0560 | 16 | 0.286 | 0.625 |
| 0.0785 | 12 | 0.214 | 0.583 |

캐스케이드의 관찰된 최고점은 coverage 0.625 (n=35) 에서 prior_agreement 0.771 이며 그 위아래로 모두 떨어진다. **이 좌표를 threshold 로 채택하지 마라** — n=56 의 단일 표본에서 고른 최대값은 낙관 편향을 갖고, prior 는 gold 가 아니다. 캘리브레이션 split 에서 다시 그려야 한다.

### 표면부재 유형을 먼저 abstain 시키면

T05/T06/T07 을 먼저 abstain 시킨 캐스케이드는 같은 coverage 에서 prior_agreement 가 **낮다**. 이것은 의외의 결과이며 정직하게 보고한다: 브랜드/앱 랜딩면은 prior 와 semantic top1 이 **오히려 잘 맞는** 케이스를 포함한다. 브랜드면의 텍스트가 그 서비스의 업종을 강하게 말해주기 때문이다. 즉 이 유형에서 semantic 이 맞히는 것은 '대표 기능 표면을 식별한 것'이 아니라 '업종을 맞힌 것'일 수 있다 — coverage 를 올리는 근거로 쓰면 안 된다.

## force-map 비용 — abstention 세탁의 값

> SSOT §6 은 유일 후보가 아니면 AMBIGUOUS_UNRESOLVED 로 남기라고 한다. 아래는 그 규정을 무시하고 abstain 40건에 강제로 하나를 고를 때의 prior 불일치 비용이다. prior 는 gold 가 아니므로 '오류율'이 아니라 '불일치율'로만 읽어야 한다.

SSOT §6 은 유일 후보가 아니면 `AMBIGUOUS_UNRESOLVED` 로 남기라고 한다. 아래는 그 규정을 무시하고 abstain 40 건에 강제로 하나를 고를 때의 prior 불일치율이다.

| 강제선택 방식 | n | 일치 | 불일치 | 불일치율 | Wilson95 |
|---|---|---|---|---|---|
| rule argmax (발화강도 최댓값) | 40 | 10 | 30 | **0.750** | [0.60, 0.86] |
| SSOT §6 이 금지한 first match | 40 | 9 | 31 | **0.775** | [0.62, 0.88] |
| semantic top1 (bge-m3 × §7 prototype) | 40 | 25 | 15 | **0.375** | [0.24, 0.53] |
| semantic top1 — debranded 대조군 | 40 | 26 | 14 | **0.350** | [0.22, 0.50] |

대조 — rule 이 **실제로 확정한** 11건의 불일치율은 rule 0.455 / semantic 0.273 다. 즉 rule 을 강제로 밀면 abstain 구간의 불일치가 확정 구간보다 크게 나빠진다(0.45 → 0.75).

### 유형별 force-map 불일치율 (분모 = 각 유형의 abstain 40 내 N)

| 유형 | n | rule argmax | first match | semantic top1 | debranded |
|---|---|---|---|---|---|
| `T01` 어떤 술어도 발화하지 않음 (insufficient evidence) | 12 | 1.00 | 1.00 | 0.50 | 0.42 |
| `T02` 한쪽 신호만 있는 약한 후보 (region 만 또는 endpoint 만) | 22 | 0.68 | 0.68 | 0.23 | 0.23 |
| `T03` 강한 후보가 둘 이상 | 6 | 0.50 | 0.67 | 0.67 | 0.67 |
| `T04` 같은 신호를 여러 archetype 이 공유 (list-family) | 2 | 0.50 | 0.50 | 0.50 | 0.50 |
| `T05` 일반 기업/브랜드 소개 면 | 15 | 0.67 | 0.67 | 0.27 | 0.27 |
| `T06` 앱 설치/전환 유도 면 | 11 | 0.91 | 0.91 | 0.55 | 0.45 |
| `T08` 로그인 지배 표면 | 12 | 0.92 | 1.00 | 0.33 | 0.42 |
| `T09` SPA/클라이언트 렌더로 구조가 비어 있음 | 2 | 0.50 | 0.50 | 0.00 | 0.00 |
| `T10A` 텍스트 인코딩 훼손 (mojibake) | 7 | 1.00 | 1.00 | 0.57 | 0.57 |
| `T10B` 텍스트/후보 절단 (cap) | 8 | 0.62 | 0.62 | 0.38 | 0.38 |
| `T11` 오버레이/모달로 대표 표면이 가려짐 | 9 | 0.67 | 0.78 | 0.33 | 0.22 |
| `T13` business prior 가 관측 구조와 어긋남 | 13 | 1.00 | 1.00 | 0.38 | 0.38 |

**어느 유형에서 가장 많이 틀리는가.** rule 을 강제로 밀 때 불일치율 1.00 인 유형이 셋이다 — `T01_NO_PREDICATE_FIRED`(n=12), `T10A_TEXT_ENCODING_CORRUPTION`(n=7), `T13_PRIOR_CONTRADICTS_STRUCTURE`(n=13). 여기에 `T08_LOGIN_DOMINATED`(0.92, n=12)와 `T06_APP_INSTALL_SURFACE`(0.91, n=11)가 붙는다. 이 다섯 유형에서 강제선택은 **사실상 전부 틀린다.** 무발화 상태에서 argmax 를 고르는 것은 동전던지기보다 나쁘고(기저율 0.46), 인코딩이 깨진 텍스트에서 어휘 술어를 믿는 것도 마찬가지다.

semantic 으로 밀면 전체 불일치는 0.375 로 낮아지지만 유형별로 갈린다: `T03_MULTI_STRONG_CANDIDATE` 0.67, `T10A` 0.57, `T06` 0.55 는 여전히 나쁘다. 특히 **T03 은 rule(0.50)보다 semantic(0.67)이 더 나쁘다** — SSOT §6 이 다중강후보를 §7 로 보내라고 했지만, 이 표본에서는 §7 이 그 6건을 더 못 가른다.

## 어디에서 abstain 해야 하는가 — 답

유형별로 나누어 답한다. 이것은 threshold 가 아니라 **abstain 의 근거 구조**다.

**A. 반드시 abstain — evidence 를 더 모아도 이 URL 에서는 안 된다**

- `T07_REPRESENTATIVE_SURFACE_ABSENT` (56 중 5) — SSOT §2 가 이미 확정을 금지한다. 논쟁 없음.
- `T05_GENERIC_BRAND_LANDING` (abstain 40 중 15) — 기업/브랜드 소개면. 그 면에는 대표 기능 표면이 존재하지 않는다. 같은 URL 을 더 정교하게 관측해도 없는 것이 생기지 않는다. **단, 이것은 '연구가 실패했다'가 아니라 'target URL 정의가 틀렸다'는 신호다.**
- `T06_APP_INSTALL_SURFACE` (abstain 40 중 11) — 웹 표면의 대표행동이 '앱으로 나가기'다. 앱 내부는 관측범위 밖이다. 다만 12건 모두 dismiss control 이 관측되므로 interstitial 을 넘긴 뒤의 표면은 수집으로 확인 가능하다 — 이 유형은 **먼저 재수집으로 갈라야** '진짜 앱전용'과 '넘길 수 있는 배너'가 구분된다.
- `T13_PRIOR_CONTRADICTS_STRUCTURE` (abstain 40 중 13) — prior 와 관측 구조가 어긋난다. label 없이 D 혼자서는 어느 쪽이 틀렸는지 판정할 수 없다. **abstain 이 유일하게 정직한 출력이다.**

**B. abstain 하되 '수집 결함' 으로 태그하고 재수집 큐에 넣어야 한다 — 지금의 abstain 은 잘못된 종류의 abstain 이다**

- `T10A_TEXT_ENCODING_CORRUPTION` (abstain 40 중 7) — 디코딩 결함. 강제선택 불일치율 1.00. 이 상태로 확정도 안 되지만, **'ambiguous' 로 남기면 원인이 감춰진다.** 별도 leaf 가 필요하다.
- `T09_CLIENT_RENDER_SPARSE` (56 중 6) / `T12_DEGENERATE_OR_DUPLICATE_CAPTURE` (56 중 4) — 같은 수집 스택에서 다른 target 은 구조를 확보했다. 실패는 표면이 아니라 캡처다.
- `T11_OVERLAY_OBSTRUCTED` (abstain 40 중 9) — 대표 표면이 덮인 채로 관측됐다. RQ-D13 의 dismissal 실험에서 248 스텝 중 166 스텝이 화면을 바꿨으므로 해제 후 재캡처가 유효하다. 다만 어떤 스텝으로도 안 바뀐 target 이 6건 있어 전부가 풀리지는 않는다.
- `T10B_TEXT_CAP_TRUNCATION` (abstain 40 중 8) — cap 은 `l0_probe.js` 의 상수다. 올리면 관측이 는다.

**C. abstain 하되 이유는 '정의' 다 — 수집이 아니라 SSOT 를 고쳐야 한다**

- `T04_SHARED_LIST_SIGNAL` (56 중 4) — list-family 4개 branch 의 region 술어가 서로 배타적이지 않다. region 증거를 더 모아도 배타성이 생기지 않는다. §5 술어 상호배타화 또는 §6 precedence 명문화가 필요하다.
- `T03_MULTI_STRONG_CANDIDATE` (56 중 6) — §6 이 §7 로 보내라고 규정한 분기인데, 이 표본에서 §7(semantic) 의 불일치율이 rule 보다 **높다**(0.67 vs 0.50). §7 이 §6 의 다중후보를 실제로 가르는지는 아직 입증되지 않았다.
- `T02_WEAK_ONE_SIDED_EVIDENCE` (abstain 40 중 22, 최대 유형) — 하위구분이 중요하다: {'ENDPOINT_ONLY__REGION_MISSING': 11, 'BOTH_SIDES_BUT_DIFFERENT_BRANCHES': 5, 'REGION_ONLY__ENDPOINT_MISSING': 6}. `ENDPOINT_ONLY__REGION_MISSING` 과 `REGION_ONLY__ENDPOINT_MISSING` 은 성격이 다르고, `BOTH_SIDES_BUT_DIFFERENT_BRANCHES` 는 서로 다른 archetype 의 반쪽 신호가 섞인 것이라 수집이 아니라 술어 조작화 문제다.

**D. abstain 하지 않아도 되는 것**

- `T08_LOGIN_DOMINATED` 의 `GATE_REACHED` 하위유형 (3건) — 실제 credential 입력칸이 관측된 것은 SSOT §5 Branch F 의 `E_F` 를 발화시킬 수 있는 **정상 증거**다. 로그인이 보인다고 abstain 하면 FINANCIAL_ACTION_ENTRY 의 정의된 endpoint 를 스스로 버리는 것이다. 반면 `GATE_NOT_REACHED` (14건) 는 로그인 '버튼'만 보이고 gate 구조에 도달하지 못한 것이라 상호작용 1스텝 수집이 필요하다.

**한 줄 답.** *abstain 은 '증거가 부족할 때'가 아니라 **'관측된 표면이 대표 기능면이 아닐 때'와 '관측 자체가 손상됐을 때'** 해야 하며, 이 둘은 같은 leaf 로 묶이면 안 된다 — 전자는 target 재정의를, 후자는 재수집을 부른다.*

## 반례

taxonomy 가 자기 주장의 반례를 스스로 찾도록 만들었다. 발견된 것:

- **브랜드/앱면 유형인데 rule 이 확정한 케이스 — '브랜드면=미결정' 주장의 반례** — wtg=95e22b9aff7196b3 service=NS홈쇼핑 leaf=ITEM_DETAIL strong=['ITEM_DETAIL'] prior_archetype=ITEM_DETAIL
- **어떤 표면/수집 유형으로도 설명되지 않는 무발화 — taxonomy 의 미설명 잔여** — wtg=51484a735cdb487b service=컴포즈커피
- **인코딩 훼손인데도 rule 이 확정 — '인코딩 훼손 => 미결정' 의 반례** — wtg=ea031f85e857140e service=메가커피 leaf=QUERY

이 세 반례가 말하는 것: (1) 브랜드면이라고 항상 미결정인 것은 아니다 — NS홈쇼핑은 브랜드 어휘가 있으면서도 item 카드 구조가 살아 있어 rule 이 확정했다. (2) 인코딩이 깨져도 URL/구조 신호만으로 확정되는 경우가 있다(메가커피 → QUERY). (3) 컴포즈커피 1건은 어떤 유형으로도 설명되지 않는 **taxonomy 의 미설명 잔여**다 — blob 19 토큰의 극단적으로 빈약한 표면인데 `dom_body_empty=0` 이고 인코딩도 정상이라 기존 유형 어디에도 걸리지 않는다.

## LIMITATION

1. **prior_archetype 은 gold label 이 아니다.** 모든 '불일치'는 rule 오류일 수도 prior 오류일 수도 있고, D 는 label 을 열지 않아 어느 쪽인지 가를 수 없다. 이 문서의 모든 수치는 `prior_agreement` 이며 accuracy 가 아니다.
2. **유형 판정식은 D 가 정한 조작화다.** 어휘 사전(기업/브랜드·앱설치·로그인), 경로 마커, SSOT §7 구성요소 개수 임계(≤2), 브랜드 어휘 3회 임계 — 어느 것도 SSOT 에 명문화되어 있지 않다. 임계를 옮기면 유형별 N 이 움직인다.
3. **n=56, 유형별 N 이 2~22 이라 유형별 비율의 신뢰구간이 매우 넓다.** force-map 유형별 불일치율은 대부분 n<15 에서 계산됐다.
4. **해결가능성 판정은 반사실(counterfactual) 주장이다.** 재수집 실험 없이는 검증되지 않는다.
5. **곡선은 prior 기준이므로 운영 threshold 결정에 그대로 쓸 수 없다.** 특히 캐스케이드 곡선의 관찰된 최고점은 단일 표본에서 고른 최대값이라 낙관 편향을 갖는다.
6. **brand leak 절제는 조악하다.** 서비스명·도메인 라벨만 지웠고, 상품명·업종어휘와 `prior_archetype ↔ prior_business_domain` 1:1 구조(RF001-B)까지 제거하지 못했다.
7. **선행 D 결과(RQ-D9/D10/D13/D13A)의 파생 플래그를 유형 판정에 썼다.** decision_trace 기반 수치는 직접 재계산해 RF001-A 와 일치를 확인했지만, overlay 분류·퇴화캡처 목록은 재계산하지 않고 받아 썼다.

가장 무거운 것은 4번이다. **해결가능성 판정은 반사실(counterfactual) 주장이다.** '재수집하면 풀린다'는 재수집 실험을 하기 전까지 검증되지 않았고, 이 문서의 RESOLVABLE 20 / UNDECIDABLE 19 는 그 실험의 **가설**이지 결과가 아니다.

추가로: holdout label 을 열지 않았다 — `LABEL_SPLIT_FROZEN*`, `HOLDOUT_FOR_C*`, `RAW_L1~L4*`, `PACKET_L*`, `*_OVERLAP*`, `PRECEDENCE_CONTESTED*`, `CALIBRATION_FOR_B*`, `**/control/**` 은 이 분석에서 한 번도 읽지 않았다. 그래서 **이 문서는 어떤 threshold 도 선언하지 않는다.**

## PRODUCTION IMPLICATION

1. **`AMBIGUOUS_UNRESOLVED` 를 하나의 leaf 로 두면 안 된다.** 최소한 `SURFACE_NOT_REPRESENTATIVE`(target 재정의 필요) / `EVIDENCE_DEFECT`(재수집 필요) / `GENUINELY_AMBIGUOUS`(정의·fallback 필요) 세 갈래로 나눠야 한다. 지금은 처방이 정반대인 케이스가 같은 통에 들어가 coverage 통계가 무의미해진다.
2. **coverage 를 올리려는 첫 시도는 detector 개선이 아니라 target URL 감사여야 한다.** abstain 40 중 22건이 표면부재 계열 유형을 갖는다. 탑마트→seowon.com, 카카오T→kakaomobility.com/service-kakaot 처럼 요청 URL 이 서비스의 기능면이 아니라 그 서비스를 설명하는 면으로 해석된 사례가 반복된다.
3. **force-map 은 금지되어야 한다.** rule argmax 강제선택의 prior 불일치율 0.75, §6 이 금지한 first-match 는 0.775 로 더 나쁘다. SSOT §6 의 금지는 데이터로 지지된다.
4. **인코딩 훼손은 별도 leaf 로 승격해야 한다.** 8건(56 중 14%)이고 강제선택 불일치율 1.00 이다. 'ambiguous' 로 감추면 수집 결함이 연구결과로 세탁된다.
5. **로그인 표면을 일괄 abstain 시키지 마라.** `GATE_REACHED` 는 §5 Branch F 의 정의된 endpoint 다.

## 추가 연구질문

1. **재수집 반사실 검증** — T09/T10A/T10B/T11/T12 로 태그된 target 을 hydration 대기·인코딩 수정·cap 상향·dismiss 후 재캡처로 다시 수집하면 실제로 몇 건이 strong candidate 를 얻는가? 이 문서의 RESOLVABLE 20 은 이 실험으로만 검증된다.
2. **target URL 감사** — prior 표의 URL 이 서비스의 기능면인지 소개면인지를 독립 기준으로 판정하면, T05/T06 의 15/11 건 중 몇 건이 '더 나은 URL 이 존재한다'로 바뀌는가? 이것은 detector 문제가 아니라 모집단 정의 문제다.
3. **§7 이 §6 의 다중후보를 실제로 가르는가** — T03 6건에서 semantic 불일치율이 rule 보다 높았다. n=6 이라 결론을 낼 수 없다. 다중후보 케이스를 늘려 §7 fallback 의 조건부 성능을 따로 재야 한다.
4. **list-family region 술어의 상호배타화** — §5 의 4개 list R 술어를 어떻게 다시 쓰면 동시발화가 줄고, 그 대가로 어떤 recall 을 잃는가?
5. **미설명 잔여의 성격** — 컴포즈커피 1건처럼 어떤 유형에도 걸리지 않는 빈약 표면이 REAL_TARGET 규모에서 몇 %가 되는가? taxonomy 의 완결성 상한을 정한다.

## 산출물

- `results/RF2_E_abstention_taxonomy.json` — 전체 결과 (per_target 56행 포함)
- `tools/rf2_e_abstention_taxonomy.py` — 재현 코드
- `figures/RF2_E_taxonomy_counts.png` · `RF2_E_overlap_matrix.png` · `RF2_E_coverage_confidence.png` · `RF2_E_cascade_curve.png` · `RF2_E_forcemap_cost.png` · `RF2_E_resolvability.png`
- `notebooks/d_research/RF2_E_abstention_taxonomy.ipynb`

