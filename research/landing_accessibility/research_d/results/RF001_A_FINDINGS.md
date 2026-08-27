# D-RF-001-A — Rule Decision Tree baseline (SSOT 01 §5)

| | |
|---|---|
| child_id | `D-RF-001-A` (parent RQ `RQ-D-RF-001`) |
| hypothesis_id | `H-RF001-A-RULE-DT` |
| rule version | `RULE_DT_SSOT01_v2.1` |
| seed | `20260827` (결정론적 규칙, 난수 미사용 — seed는 재현 선언용) |
| verdict | **NOT_SUPPORTED** |
| plane / authority | D / `NON_CANONICAL` |

---

## 1. RQ

> SSOT 01 (`LA-RFDT-2.1`) §5 Stage 3 branch tree와 §6 Stage 4 multi-candidate resolver를
> 결정론적으로 구현했을 때, **관측 가능한 DOM/AX/form/URL 신호만으로** 56개 frozen target 중
> 몇 개에서 **유일 leaf**가 닫히는가? 닫히지 않으면 어디서 막히는가?

이 실험은 분류기 성능 경쟁이 아니다. **규칙이 관측증거만으로 결정을 닫을 수 있는가**를 재는
조작화 실험이며, 닫히지 않는 경우의 abstention은 실패가 아니라 측정 결과다.

## 2. 가설 / 경쟁가설

- **H-RF001-A**: rule DT를 결정론적으로 구현하면 상당수 target에서 유일 leaf가 닫힌다.
- **H-A-null** (경쟁): rule은 **대부분 다중후보**를 남기고, 유일 leaf가 닫히는 경우도
  prior와 **체계적으로 어긋난다** (= rule이 정보가 없다).

결과는 **둘 다 그대로는 성립하지 않는다**. 상세는 §12.

## 3. 입력

| 파일 | 행 | sha256 |
|---|---|---|
| `results/D_OBSERVATION_TABLE.csv` | 66행 중 `in_mart==1` **56행** 사용 | `014abea3918997235674a0dce86c351dd9cfccddad3f1be856c35dc445fff5a3` |
| `results/D_TEXT_CORPUS.csv` | 56행 | `00420e0b68e4a762bd524040594268deae41bf4e8fac2d887c6b2b3d252c5ad8` |
| `SSOTV2/01_REPRESENTATIVE_FUNCTION_MAPPING_DT_v2.1.md` | 규칙 원문 | `191ee182219e96398a11283bdb49b5b37a3d9e1acd5aa2d55d85946a346b37e8` |

raw evidence(`dom.html`, `probe.json`)를 **다시 파싱하지 않았다.** D 공용 빌더 산출물만 소비했다.
gold label / holdout / `LABEL_SPLIT_FROZEN.json`을 **열지 않았다.** REAL_TARGET에 접속하지 않았다.

## 4. 분석단위 · N · missing N

- **분석단위**: web target (`wtg`), `in_mart==1` 관측단위 1행 = 1 target.
- **N = 56**. n_expected = 59.
- **missing N = 3** — `삼성 인터넷 브라우저`(prior QUERY), `삼성 노트`(prior UTILITY_ENTRY),
  `삼성 월렛`(prior FINANCIAL_ACTION_ENTRY). 세 건 모두 `dom_parse_ok=NaN`,
  `probe_present=NaN` (DOM 미수집).
  **결측은 MCAR이 아니다**: 세 건 모두 삼성 1st-party 앱 안내 페이지 계열이고,
  같은 계열의 `내 파일`·`디바이스 케어`는 §10의 인코딩 파손군에 들어간다.
  즉 결측과 증거파손이 같은 도메인에 몰려 있다.

**prior class 분모** (n=56): ITEM_DETAIL 26 · FINANCIAL_ACTION_ENTRY 10 · UTILITY_ENTRY 5 ·
COMMUNICATION_ENTRY 4 · PLACE_LOOKUP 4 · QUERY 4 · CONTENT_OPEN 3.
**5개 class가 n≤5**다. per-class 수치는 전부 Wilson 95% CI와 함께만 읽어야 한다.

## 5. Feature set (Stage 2, SSOT §4)

관측 테이블 숫자형: `search_inputs_n`, `article_present`, `gate_password_input_n`,
`gate_captcha_iframe_n`, `dom_input_n`, `dom_button_n`, `dom_a_href_n`, `dom_body_empty`,
`probe_present`.

텍스트 코퍼스 필드: `title`, `meta_description`, `headings`, `landmarks`, `nav_links`,
`buttons`, `aria_labels`, `placeholders`, `form_labels`, `input_names`, `card_texts`,
`url_tokens`.

여기서 파생한 17개 boolean/count predicate (`has_search_input`, `has_search_submit`,
`content_item_cards`, `has_content_play`, `price_hits`, `item_cards`, `has_txn_control`,
`has_place_widget`, `place_cards`, `has_place_detail`, `comm_cards`, `has_comm_compose`,
`fin_controls`, `has_auth_gate`, `has_tool_function`, `has_tool_primary_form`,
`is_error_page`) 가 branch predicate의 입력이다. 전체 lexicon 정규식은
MLflow artifact `rule_definitions.txt` 및 `tools/rf001_a_rule_dt.py` 상단에 그대로 있다.

**규칙 입력에서 의도적으로 제외한 것**: `prior_archetype`, `prior_business_domain`,
`prior_service`. SSOT §6 evidence precedence 4(source/business prior)·5(service name token)를
기본 경로에서 끈다. 이걸 쓰면 prior_agreement가 순환논증이 된다. precedence 4를 켠 variant는
§11 민감도에서 따로 측정했다.

## 6. 방법 — 규칙 전문

### Stage 0 (SSOT §2) — web target validity

| rule | 조건 | leaf |
|---|---|---|
| `S0_NO_RENDERED_SURFACE` | `dom_body_empty==1` (body innerText < 50자, 상위 빌더가 계산) | `UNDETERMINED_URL_EVIDENCE` |
| `S0_ERROR_PAGE` | title/headings가 error_page lexicon과 매치 | `UNDETERMINED_URL_EVIDENCE` |

### Stage 3 (SSOT §5) — branch tree

각 branch는 **region evidence R과 endpoint evidence E를 모두** 요구한다.
하나만 발화하면 강후보가 아니다(= weak).

| branch | R (region) | E (endpoint) |
|---|---|---|
| **Q** QUERY | focusable search input / searchbox / combobox 노출 | submit 가능한 form 또는 submit control (자동완성만으로는 불가) |
| **C** CONTENT_OPEN | 반복 content card/link list ≥ 3 | `article_present≥1` 또는 media playback 진입 control |
| **I** ITEM_DETAIL | 반복 product/item card or link list ≥ 3 | price pattern(또는 명시적 품절/판매종료) **AND** transaction control **존재** |
| **P** PLACE_LOOKUP | place search control 또는 place list ≥ 3 | place detail control, 또는 (place widget ∧ submit control) |
| **M** COMMUNICATION_ENTRY | thread/post list ≥ 3 또는 compose-entry control | compose control, thread list, 또는 **실제 login gate**(password input) — 로그인 버튼 존재만으로는 불가 |
| **F** FINANCIAL_ACTION_ENTRY | balance/transfer/payment/auth function entry control ≥ 3 | 실제 LOGIN/IDENTITY gate 구조(password/인증서/간편인증) |
| **U** UTILITY_ENTRY | 단일목적 function surface entry control | `dom_input_n≥1` ∧ tool primary control 노출 |

### Stage 4 (SSOT §6) — multi-candidate resolver

```
len(strong)==1 -> MAPPED   (mapping_basis = OBSERVED_INTERACTION_STRUCTURE, precedence 1-3)
len(strong)>=2 -> AMBIGUOUS_UNRESOLVED__MULTI_CANDIDATE     (next: NLP fallback §7)
len(strong)==0 -> AMBIGUOUS_UNRESOLVED__NO_STRONG_CANDIDATE (next: NLP/VLM/Human)
```

SSOT §6이 명시적으로 든 사례("검색창과 상품목록이 동시에 있을 수 있다 → 첫 매칭을 무조건
선택하지 않는다")를 그대로 따랐다. 강후보가 2개 이상이면 **어떤 우선순위로도 억지로 고르지 않는다.**
`force_mapped_n = 0`.

### 정의상 강등 — assertion type: `DEFINITION`

SSOT의 endpoint는 "질의가 실제 제출되어 결과 state로 전환된 **순간**", "article body **open**",
"place detail **opened**" 같은 **상태 전이**다. 이 실험의 입력은 **정적 landing snapshot 1장**이며
전이를 관측할 수 없다. 따라서 모든 branch의 E를 **endpoint-enabling control의 존재**로 강등했다.
이 강등은 coverage를 **낙관적으로** 밀어 올리는 방향이다(전이 확인보다 약한 조건). 그럼에도
coverage가 0.196에 그쳤다는 점이 §12 판정의 근거를 강화한다.

### 재현

```bash
/home/sieg/projects-wsl/ProjectFinal/.venv/bin/python \
  .../research_d/tools/rf001_a_rule_dt.py
```
난수 사용 없음. Restart→Run All 동일 산출.

**구현 결함 1건 시정 기록**: 최초 구현의 `error_page` lexicon이 bare `404`를 포함해
롯데마트 상품 규격 `"(404G)"`에 매치, Stage 0에서 잘못 기각했다. 토큰 경계
`(?<![\w,.])404(?![\w,.])`로 시정했다. 이는 **결과 개선용 threshold 튜닝이 아니라
정규식 결함 시정**이며, 시정 전 수치(coverage 10/56, prior_agreement 5/10)도 함께 남긴다.

## 7. 주요 결과 (모든 분모 명시)

| 지표 | 값 | 분자/분모 | Wilson 95% CI |
|---|---|---|---|
| **coverage** (유일 leaf 비율) | **0.196** | 11/56 | [0.113, 0.318] |
| coverage (Stage 0 기각 제외) | 0.216 | 11/51 | — |
| **abstention rate** | **0.714** | 40/56 | — |
| ├ multi-candidate | 0.107 | 6/56 | — |
| └ no-strong-candidate | 0.607 | 34/56 | — |
| `UNDETERMINED_URL_EVIDENCE` (Stage 0) | 0.089 | 5/56 | — |
| 비-MAPPED 총합 | 0.804 | 45/56 | — |
| **prior_agreement (coverage 내부)** | **0.545** | 6/11 | [0.280, 0.787] |
| **prior_agreement (전체 56 기준)** | **0.107** | 6/56 | [0.050, 0.215] |

> **용어 주의**: `prior_agreement`는 정확도가 아니다. `prior_archetype`은 business-domain
> **prior**이고 SSOT §1은 observed task shape가 prior를 **이긴다**고 규정한다. rule과 prior가
> 갈리는 것이 곧 rule 오류가 아니다. §9에서 5건 전수를 evidence로 판정한다.

SSOT §10 release gate 기준(holdout coverage ≥ 0.75, archetype agreement ≥ 0.85)과 비교하면
coverage는 **CI 상한(0.318)조차 목표의 절반에 못 미친다**. 이 값은 연구결과가 아니라
detector readiness 기준임을 SSOT가 명시하고 있고, 현재 rule DT 단독으로는 gate를 통과하지 못한다.

## 8. Per-class (분모 + Wilson 95% CI)

| prior archetype | n_prior | n_rule_mapped | TP | recall vs prior [CI] | precision vs prior [CI] |
|---|---|---|---|---|---|
| QUERY | 4 | 4 | 0 | 0.000 [0.000, 0.490] | **0.000 [0.000, 0.490]** |
| CONTENT_OPEN | 3 | 0 | 0 | 0.000 [0.000, 0.561] | 정의불가 (분모 0) |
| ITEM_DETAIL | 26 | 4 | 4 | 0.154 [0.062, 0.335] | 1.000 [0.510, 1.000] |
| PLACE_LOOKUP | 4 | 3 | 2 | 0.500 [0.150, 0.850] | 0.667 [0.208, 0.939] |
| COMMUNICATION_ENTRY | 4 | 0 | 0 | 0.000 [0.000, 0.490] | 정의불가 |
| FINANCIAL_ACTION_ENTRY | 10 | 0 | 0 | 0.000 [0.000, 0.278] | 정의불가 |
| UTILITY_ENTRY | 5 | 0 | 0 | 0.000 [0.000, 0.434] | 정의불가 |

**7개 archetype 중 4개(CONTENT_OPEN, COMMUNICATION_ENTRY, FINANCIAL_ACTION_ENTRY,
UTILITY_ENTRY)는 단 한 건도 MAPPED되지 않았다.** 특히 FINANCIAL은 n=10으로 두 번째로 큰 class인데
recall 0/10 [0, 0.278]이다.

가장 눈에 띄는 비대칭: **QUERY branch는 가장 많이 발화(강후보 9회)했는데 precision 0/4다.**
QUERY로 매핑된 4건은 전부 prior가 ITEM_DETAIL인 쇼핑 도메인이고, 정작 prior가 QUERY인
Google·Chrome·네이버·다음 4건은 하나도 QUERY로 닫히지 않았다(2건 multi, 2건 no-evidence).

### Confusion matrix (행 = prior, 열 = rule leaf)

| prior \ leaf | QUERY | CONT | ITEM | PLACE | COMM | FIN | UTIL | ABST-multi | ABST-no-ev | UNDET |
|---|---|---|---|---|---|---|---|---|---|---|
| QUERY (4) | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 2 | 0 |
| CONTENT_OPEN (3) | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 3 | 0 |
| ITEM_DETAIL (26) | 4 | 0 | 4 | 1 | 0 | 0 | 0 | 0 | 16 | 1 |
| PLACE_LOOKUP (4) | 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 2 | 0 |
| COMMUNICATION (4) | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 2 | 1 |
| FINANCIAL (10) | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 5 | 3 |
| UTILITY (5) | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 4 | 0 |

figure: `figures/RF001_A_confusion.png`, `figures/RF001_A_outcome_by_prior.png`

## 9. 어느 규칙이 실제로 일하는가 (규칙별 발화 횟수, 분모 n=56)

| predicate | 발화 | | predicate | 발화 |
|---|---|---|---|---|
| `CONTENT_OPEN.E` | 21 | | `COMMUNICATION_ENTRY.E` | 5 |
| `QUERY.E` | 16 | | `FINANCIAL_ACTION_ENTRY.E` | 5 |
| `QUERY.R` | 13 | | `ITEM_DETAIL.E` | **4** |
| `ITEM_DETAIL.R` | 12 | | `CONTENT_OPEN.R` | **3** |
| `UTILITY_ENTRY.E` | 9 | | `FINANCIAL_ACTION_ENTRY.R` | **2** |
| `PLACE_LOOKUP.R` | 9 | | `UTILITY_ENTRY.R` | **2** |
| `PLACE_LOOKUP.E` | 7 | | `COMMUNICATION_ENTRY.R` | **2** |

Stage 4: `NO_STRONG_CANDIDATE` 34 · `UNIQUE_STRONG` 11 · `MULTI_STRONG` 6.
Stage 0: `S0_NO_RENDERED_SURFACE` 4 · `S0_ERROR_PAGE` 1.

강후보(R∧E)로 성립한 횟수: QUERY 9 · PLACE_LOOKUP 5 · ITEM_DETAIL 4 · UTILITY 2 ·
COMMUNICATION 2 · CONTENT_OPEN 2 · FINANCIAL 1.

**실제로 일한 규칙 세 개**:
1. `QUERY.R ∧ QUERY.E` — 유일하게 반복적으로 닫히는 조합(9회). 그런데 §8에서 보듯 precision 0.
2. `ITEM_DETAIL.E` (price pattern ∧ transaction control 존재) — 발화는 4회뿐이지만, 발화한
   4건 전부가 prior와 일치(precision 1.000)했다. **가장 특이도가 높은 단일 증거**다.
3. `PLACE_LOOKUP.R` — 9회 발화, 그중 5회가 강후보로 승격. place vocabulary는 신호가 있으나
   §9의 네이버지도 사례처럼 **corporate 소개 페이지에서도 발화**한다.

**핵심 진단 — 막히는 지점은 branch마다 다르다.** R∧E 결합이 coverage를 죽이는데,
어느 쪽이 병목인지가 branch별로 반대다.

- ITEM_DETAIL: region 풍부(12) / **endpoint 희소(4)** → landing에 **가격이 없다**.
  가격은 한 클릭 아래에 있다.
- CONTENT_OPEN: **region 희소(3)** / endpoint 풍부(21) → 반복 content card list가
  코퍼스에서 잡히지 않는다(§10 절단 참조).
- UTILITY_ENTRY: **region 희소(2)** / endpoint 9 → 단일목적 tool surface 자체가 landing에 없다.
- FINANCIAL: **양쪽 다 희소(R=2, E=5)** → 은행/카드 public landing은 앱 유도 마케팅면이다.

abstention 34건 중 **12건은 어떤 predicate도 발화하지 않은 완전 증거 진공**
(쿠팡이츠·탑마트·V3·토스·컴포즈커피·밴드·하나은행·KB Pay·카카오T·디바이스 케어·모니모·내 파일).
prior 분포는 FINANCIAL 4 · ITEM 3 · UTILITY 3 · COMM 1 · PLACE 1.
나머지 22건은 predicate가 일부 발화했으나 **같은 branch에서 R과 E가 동시에 서지 못했다.**

## 10. 반례 전수 — 유일 leaf가 닫혔는데 prior와 다른 5건

| # | target | URL | prior | rule leaf | 판정 |
|---|---|---|---|---|---|
| 1 | CJ온스타일 | `display.cjonstyle.com/nfront/search/searchAllList/` | ITEM_DETAIL | QUERY | **rule이 맞다** |
| 2 | 현대백화점 | `thehyundaiseoul.ehyundai.com` | ITEM_DETAIL | PLACE_LOOKUP | **rule이 더 그럴듯하다** |
| 3 | 코스트코 | `costco.co.kr` | ITEM_DETAIL | QUERY | **prior가 맞다 — rule 오류** |
| 4 | 다이소 | `daiso.co.kr` | ITEM_DETAIL | QUERY | **둘 다 아니다 — target URL 문제** |
| 5 | 메가커피 | `m.megacoffee.co.kr` | ITEM_DETAIL | QUERY | **판정 불가 — 증거 파손** |

**1. CJ온스타일 — rule이 맞다.** 수집된 URL이 문자 그대로 통합검색 페이지다.
`title="CJ온스타일"`, `headings="통합 검색 | 추천 검색어 | 인기 검색어"`, placeholder
`"검색어를 입력해주세요"`, card_texts가 인기검색어 랭킹 1~20위. 상품 카드도 가격도 없다.
SSOT §1("business domain과 observed task shape가 충돌하면 observed task shape를 우선")을
그대로 적용하면 이 URL의 observed task shape는 QUERY다. prior ITEM_DETAIL은 **서비스(앱)의
대표기능**이지 **이 URL의 대표기능**이 아니다.

**2. 현대백화점 — rule이 더 그럴듯하다.** `thehyundaiseoul.ehyundai.com`은 백화점 체인 쇼핑몰이
아니라 **더현대 서울이라는 개별 점포의 장소 사이트**다. headings에 `Store`, `Walk`,
`Special Place`, `CONTACT`, `Pop up Calendar`, `주말 및 공휴일 임시주차장 이용 안내`,
buttons에 `오늘 10:30 ~ 20:00`(영업시간). 커머스 surface가 존재하지 않는다.
PLACE_LOOKUP이 관측증거에 부합한다.

**3. 코스트코 — rule 오류.** costco.co.kr은 실제 온라인몰이고 `카트에 담기` 버튼,
`쇼핑카트 0`, 상품 카테고리 트리(디지털/TV/컴퓨터 → Apple → …), placeholder
`"찾으시는 상품을 입력해 보세요"`가 모두 있다. `has_txn_control=1`이지만
`price_hits=0`이라 `ITEM_DETAIL.E`가 서지 못했고, header 검색창이 `QUERY.R∧E`를 통과해
유일 강후보가 됐다. **원인은 QUERY branch에 "primary surface" 판별이 없다는 것**이다.
SSOT §6 precedence 2는 "public page primary interaction surface"를 요구하는데,
header 검색창은 거의 모든 커머스 사이트에 있으므로 primary가 아니다. 규칙 결함이다.

**4. 다이소 — 둘 다 아니다.** daiso.co.kr은 nav_links가 `기업소개 | 인사말 | 기업비전 | 연혁
| CI/BI | 인재채용 | 채용안내 | 가맹문의`인 **기업 소개 사이트**다. 상품도 가격도 장바구니도 없다.
placeholder 두 개는 `검색어를 입력해주세요`(사이트 검색)와 `가까운 다이소 매장을 찾아보세요`
(매장찾기). prior ITEM_DETAIL은 이 URL에 대해 지지되지 않고, rule의 QUERY는 사이트 검색창
artifact다. 이건 DT 문제가 아니라 **Stage 0/1의 target URL 선정 문제**다.

**5. 메가커피 — 판정 불가.** 이 target은 §11의 인코딩 파손군이다. 한글 증거가 전부 mojibake라
`QUERY.R`은 `search_inputs_n=1`(probe 카운터), `QUERY.E`는 ASCII `input name`만으로 발화했다.
**한글 텍스트 증거가 0인 상태에서 leaf가 닫혔다** — 이것은 mapping이 아니라 경고다.
증거가 파손된 target은 매핑되지 말고 abstain되어야 한다.

### 반대 방향 반례 — "맞았지만 이유가 틀린" 1건

**네이버지도** (prior PLACE_LOOKUP → leaf PLACE_LOOKUP, agreement로 집계됨). 그러나 URL은
`navercorp.com/service/map`, 즉 **네이버 기업사이트의 서비스 소개 페이지**다.
placeholder는 `네이버 기업사이트 내 검색`이고 지도 검색창이 아니다. `R_P`는 control 텍스트의
`지도`/`네이버지도` 토큰으로, `E_P`는 (place widget ∧ 사이트검색 submit)으로 발화했다.
**우연히 맞은 것이다.** gold label이 없는 상태에서 prior_agreement는 이런 우연 일치와
진짜 일치를 구분하지 못한다 — prior_agreement를 정확도로 읽으면 안 되는 두 번째 이유다.

### 다중후보 abstention 6건 (SSOT §6이 예상한 그 상황)

| target | prior | 강후보 |
|---|---|---|
| 네이버 | QUERY | QUERY + CONTENT_OPEN |
| 다음 | QUERY | QUERY + CONTENT_OPEN + PLACE_LOOKUP + COMMUNICATION_ENTRY |
| 당근 | COMMUNICATION_ENTRY | QUERY + COMMUNICATION_ENTRY |
| 삼성카드 | FINANCIAL_ACTION_ENTRY | QUERY + UTILITY_ENTRY |
| 현대카드 | FINANCIAL_ACTION_ENTRY | FINANCIAL_ACTION_ENTRY + UTILITY_ENTRY |
| 캐시워크 | UTILITY_ENTRY | QUERY + PLACE_LOOKUP |

포털 2건(네이버·다음)은 SSOT §6이 명시한 전형적 상황이며 **abstain이 규정상 정답**이다.
이들은 NLP fallback(SSOT §7)의 1순위 대상이다.

## 11. 안전 감사 — SSOT §10 release gate

| 항목 | 결과 |
|---|---|
| **unsafe endpoint false-positive** | **0** |
| every mapped leaf has evidence trace | 11/11 충족 (`leaves_missing_evidence_trace_n=0`) |
| every mapped leaf has forbidden_continuation | 11/11 충족 |
| unresolved cases are not force-mapped | `force_mapped_n = 0` |

7개 branch의 `endpoint_signal_type`을 구매/결제/송금/이체/전송/게시 **수행** 패턴으로 정적
스캔한 결과 위반 0. ITEM_DETAIL의 transaction control은 SSOT §4·§8대로
`ITEM_PRICE_AND_TXN_CONTROL_PRESENT` — **존재 증거로만** 쓰이고, 어떤 규칙도 활성화를
endpoint로 삼지 않는다. COMMUNICATION의 login gate도 "버튼 존재"가 아니라
`gate_password_input_n≥1`(실제 form 구조)을 요구한다.

guard annotation은 매핑된 leaf마다 `login_gate` / `captcha_iframe` / `app_interstitial`로
남겼다(SSOT §8). 전체 코호트에서 CAPTCHA iframe 관측 3건(마켓컬리·캐시워크·신세계백화점),
password input 관측 4건, app interstitial 3건(TikTok·Instagram·에이닷 전화).

## 12. 민감도

| variant | n_mapped | coverage | abstention | prior_agree (coverage 내부) |
|---|---|---|---|---|
| repeat_min = 2 | 10 | 0.179 | 0.732 | 0.500 (5/10) |
| **repeat_min = 3 (기본)** | **11** | **0.196** | **0.714** | **0.545 (6/11)** |
| repeat_min = 5 | 10 | 0.179 | 0.732 | 0.400 (4/10) |
| SSOT §6 precedence-4 prior tiebreak ON | 15 | 0.268 | 0.643 | 0.667 (10/15) |
| 인코딩 파손 8건 제외 (n=48) | 10 | 0.208 | 0.688 | 0.600 (6/10) |
| Stage 0 기각 5건 제외 (n=51) | 11 | 0.216 | 0.784 | 0.545 (6/11) |

- **반복 임계값(2/3/5)에 대해 coverage가 0.179–0.196으로 사실상 불변**이다. 결론은
  임의 threshold에 기대고 있지 않다.
- **prior tiebreak을 켜면** coverage 0.196→0.268, prior_agreement 0.545→0.667로 오른다.
  그러나 이 상승분은 **정의상 prior와 일치할 수밖에 없는 4건**에서 나온 것이므로
  "규칙이 좋아졌다"는 증거가 아니다. 기본 경로에서 이 tiebreak을 끈 이유가 이것이다.
- 인코딩 파손군을 빼면 coverage가 0.196→0.208로 **오르고** agreement도 0.545→0.600으로 오른다.
  파손 target은 신호를 지우기만 하는 게 아니라 §10-5(메가커피)처럼 **잘못된 leaf도 만든다.**

## 13. Verdict

**NOT_SUPPORTED** (H-RF001-A).

- assertion type `OBSERVATION`: coverage 11/56 = 0.196 [0.113, 0.318], abstention 40/56 = 0.714,
  Stage 0 기각 5/56, prior_agreement 6/11 = 0.545 [0.280, 0.787].
- assertion type `ANALYSIS`: "상당수 target에서 유일 leaf가 닫힌다"는 주장은 지지되지 않는다.
  7개 archetype 중 4개는 단 한 건도 닫히지 않았고, 가장 큰 class인 ITEM_DETAIL도 4/26이다.
  SSOT §10 readiness 기준(coverage ≥ 0.75)에 CI 상한조차 못 미친다.

**경쟁가설 H-A-null도 그대로는 성립하지 않는다** (assertion type `ANALYSIS`):

1. "대부분 다중후보를 남긴다" — **틀렸다.** 다중후보 abstention은 6/56 = 0.107뿐이고,
   지배적 실패 양상은 **증거 부재**(34/56 = 0.607)다. 규칙이 후보를 과잉생성하는 게 아니라
   **관측면에 증거 자체가 없다.** 12건은 완전 증거 진공이다.
2. "유일 leaf도 prior와 체계적으로 어긋난다" — **부분적으로만 맞다.** 6/11이 일치했고,
   불일치 5건 중 2건(CJ온스타일·현대백화점)은 **rule 쪽이 관측증거에 더 부합**하며
   1건(다이소)은 prior도 틀렸다. 체계적 오류로 판정되는 건 코스트코 1건뿐이고
   그 원인은 진단 가능한 단일 결함(QUERY branch의 primary-surface 판별 부재)이다.
3. "rule이 정보가 없다" — **틀렸다.** `ITEM_DETAIL.E`는 4/4 precision 1.000 [0.510, 1.000]으로
   특이도가 높다. 정보가 없는 게 아니라 **증거가 닿는 target이 적다.**

즉 관측된 그림은 "규칙이 나쁘다"가 아니라 **"규칙이 요구하는 증거가 landing snapshot에
존재하지 않는다"** 쪽이다. 이 구분은 다음 단계 결정(규칙 수정 vs 수집 심화 vs NLP fallback)을
정반대로 가르므로 중요하다.

## 14. Limitation

가장 무거운 것부터.

1. **[가장 무겁다] 관측면과 대표기능의 층위 불일치.** `prior_archetype`은 **서비스(주로 앱)의**
   대표기능인데, 수집된 URL 상당수는 그 서비스의 **기업/브랜드/앱설치 유도 랜딩**이다
   (GS25→gsretail.com 기업사이트, 티맵→tmapmobility.com 기업사이트,
   카카오T→kakaomobility.com, 네이버지도→navercorp.com 서비스소개, 밴드→마케팅 랜딩,
   Instagram/TikTok→앱 인터스티셜, Chrome→브라우저 제품 소개, 다이소→기업소개).
   이런 면에는 어떤 archetype의 region/endpoint도 존재하지 않는다. **이건 DT의 결함이 아니라
   Stage 0/Stage 1의 target URL 정의 문제**이며, DT를 아무리 고쳐도 해결되지 않는다.
2. **정적 단일 snapshot.** SSOT의 endpoint는 상태 전이인데 전이를 관측할 수 없어
   "control 존재"로 강등했다(§6). 실제 전이 확인은 더 엄격하므로 여기 coverage는
   **상한 추정**으로 읽어야 한다.
3. **텍스트 코퍼스 절단.** 공용 빌더가 headings 25 · buttons 30 · aria 40 · cards 25 ·
   nav 40개로 자르고 항목당 40–80자로 자른다. `CONTENT_OPEN.R`이 3회밖에 발화하지 않은 것과
   `price_hits`가 대부분 0인 것은 실제 페이지가 아니라 **절단된 view**의 성질일 수 있다.
   D 지시상 raw 재파싱이 금지되어 이 교란은 이 child run에서 분리할 수 없다.
4. **인코딩 파손 8/56 = 0.143.** CP949/EUC-KR 문서를 latin-1로 읽은 mojibake
   (탑마트·V3·YouTube·하나은행·KB Pay·디바이스 케어·메가커피·내 파일). 이들은 한글 증거가
   전부 소실됐다. 7건은 abstain으로 흘렀지만 1건(메가커피)은 **파손 상태에서 leaf를 닫았다.**
   공용 빌더(`build_text_corpus.py`)의 결함이며 D worker 권한 밖이다. B/A에 보고 필요.
5. **gold label 부재.** prior_agreement는 정확도가 아니고, §10의 네이버지도처럼 **우연 일치**를
   걸러내지 못한다. 진짜 정확도는 A가 조직할 labeler worker의 gold 없이는 측정 불가다.
6. **소표본.** 5개 class가 n≤5다. CONTENT_OPEN recall 0/3의 CI 상한은 0.561로, "이 branch가
   전혀 작동하지 않는다"와 "절반은 잡는다"를 구분하지 못한다.
7. **lexicon 자체가 자유도다.** Wilson CI는 표집 불확실성만 담고 lexicon 선택
   불확실성은 담지 않는다. repeat_min 민감도는 흔들었지만 lexicon은 흔들지 않았다.
8. **결측 3건이 MCAR이 아니다**(§4). 삼성 1st-party 계열에 결측·파손이 몰려 있어
   UTILITY_ENTRY / QUERY / FINANCIAL 쪽 추정이 특히 취약하다.

## 15. Production implication

`IMPLEMENTATION` / `PROJECTION` 성격의 함의. **D는 결정권이 없다. 아래는 A에 대한 제안이다.**

1. **rule DT 단독으로 REAL_TARGET 전면 수집을 열면 안 된다.** SSOT §10 gate
   (coverage ≥ 0.75, agreement ≥ 0.85) 대비 coverage 0.196 [0.113, 0.318]이다.
   SSOT가 규정한 대로 **pilot subset만** 허용되는 상태다.
2. **다음으로 고칠 것은 DT가 아니라 target URL 정의다.** abstention 40건 중 상당수가
   "기업/마케팅 랜딩에는 어떤 archetype surface도 없다"에서 나왔다(§14-1).
   Stage 0/1에서 measurement entity의 **기능면 URL**과 **기업 소개면 URL**을 구분하는
   판정이 먼저다. 이걸 안 고치고 DT를 손보면 없는 증거를 억지로 만드는 방향으로 간다.
3. **NLP fallback의 실제 부하는 다중후보 6건이 아니라 증거부재 34건이다.**
   SSOT §7은 fallback을 "DT가 못 닫은 소수 ambiguity"로 상정하지만, 관측된 분포는
   소수 ambiguity(6)가 아니라 대량 evidence sparsity(34)다. fallback 설계 가정을
   재검토해야 한다. 그중 12건은 텍스트 증거 자체가 진공이라 NLP로도 닫히지 않고
   VLM 또는 Human Final 경로가 필요하다.
4. **`build_text_corpus.py`의 인코딩 처리 결함**(§14-4)은 8/56에 영향한다.
   `lxml.html.fromstring(bytes)`가 meta charset을 못 따라간 경우로 보인다. B 소관.
5. **`ITEM_DETAIL.E`(price ∧ txn control presence)는 detector로 살려둘 가치가 있다.**
   4/4 precision. 다만 landing 한 장에서는 4/26에서만 발화하므로 **가격이 보이는 depth-1
   상태**를 수집해야 쓸모가 생긴다.
6. **QUERY branch에 primary-surface 판별을 넣기 전에는 QUERY leaf를 신뢰하면 안 된다**
   (§10-3). 현재 precision 0/4다. header 검색창과 대표 검색면을 가르는 조건
   (예: 검색 input이 landmark/main 안에 있는가, 페이지의 다른 강후보 surface가 있는가)이
   필요하다. **이건 이 run의 규칙을 고치는 것이므로 새 child run(새 hypothesis_id)으로
   분리해야 하며 본 run을 덮어써서는 안 된다.**
7. 안전 측면은 현 상태로 통과다: unsafe endpoint FP = 0, force-map = 0, 모든 mapped leaf가
   evidence trace와 forbidden_continuation을 보유.

## 16. 추가 연구질문

- **RQ-a**: 수집 URL을 "기능면 / 기업소개면 / 앱설치 유도면"으로 분류했을 때, 기능면 부분집합
   (추정 n≈20)에서 rule DT coverage는 얼마인가? §14-1이 실제 병목인지 직접 검정.
- **RQ-b**: depth-1(대표 region에서 한 번 전이한 상태)까지 수집하면 `ITEM_DETAIL.E`의
   발화가 4/26에서 얼마나 오르는가? endpoint 강등(§6)을 걷어낼 수 있는가?
- **RQ-c**: 인코딩을 시정해 코퍼스를 재생성하면 8건의 leaf가 어떻게 바뀌는가?
   (B가 빌더를 고친 뒤 동일 규칙으로 재실행 — 새 child run)
- **RQ-d**: QUERY branch에 primary-surface 조건을 추가한 `RULE_DT_v2.2`는 precision 0/4를
   개선하면서 coverage를 유지하는가? (새 hypothesis_id 필수)
- **RQ-e**: NLP fallback(SSOT §7)은 다중후보 6건과 증거부재 34건에서 각각 다른 성능을
   보이는가? 후자에서도 유의미하면 §15-3의 우려는 완화된다.
- **RQ-f**: 텍스트 절단 한도를 늘린 코퍼스에서 `CONTENT_OPEN.R`의 발화가 회복되는가?
   (§14-3 교란의 직접 검정)
- **RQ-g**: gold label이 생긴 뒤, 본 run의 11개 MAPPED leaf 중 몇 개가 실제로 맞았는가?
   특히 "맞았지만 이유가 틀린" 네이버지도 유형의 비율은?

---

### 산출물

| 파일 | 내용 |
|---|---|
| `tools/rf001_a_rule_dt.py` | 규칙 DT 구현 (재현 진입점) |
| `results/RF001_A_rule_dt.json` | 최상위 `verdict` + metrics + per_class + confusion + 규칙 발화 + 반례 + 민감도 + **target별 SSOT §9 leaf(decision_trace 포함) 56건** |
| `results/RF001_A_FINDINGS.md` | 이 문서 |
| `figures/RF001_A_confusion.png` | prior × rule leaf confusion |
| `figures/RF001_A_rule_firing.png` | 규칙별 발화 횟수 |
| `figures/RF001_A_outcome_by_prior.png` | prior별 MAPPED/abstain/undetermined 분해 |
