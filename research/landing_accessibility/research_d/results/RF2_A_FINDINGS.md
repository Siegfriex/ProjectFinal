# D-RF2-A — Rule firing / co-occurrence EDA

`RQ-D-RF-002` (Representative Function Observability & Separability) · child **D-RF2-A**
hypothesis_id `H-RF2-A-FIRING-COOCCURRENCE` · rule_version `RF2A_FIRING_v1` · seed `20260827`
plane D · authority `NON_CANONICAL` · claim_kind `ANALYSIS` · split `none`

> **경고 — prior 는 gold label 이 아니다.** `prior_archetype` 은 business-domain prior 다.
> 이 문서의 어떤 수치도 accuracy 가 아니다. prior 대조 지표는 전부 `prior_agreement` 로만 부른다.
> abstention 은 실패가 아니라 결과다. 어떤 target 도 force-map 하지 않았다.

> **firewall.** 이 분석은 holdout label · `LABEL_SPLIT_FROZEN*` · `HOLDOUT_FOR_C*` ·
> `RAW_L1~L4*` · `PACKET_L*` · `*_OVERLAP*` · `PRECEDENCE_CONTESTED*` · `CALIBRATION_FOR_B*` ·
> `**/control/**` · B/C 의 target-level holdout error report 를 **열지 않았다**.
> 입력은 아래 두 파일뿐이다.

---

## 1. Research question

현재 deterministic evidence(수집된 landing 단일 상태의 DOM/AX/텍스트 구조)가
**어떤 archetype 후보들을 동시에 발화시키는지** 해부한다.
"어느 archetype 이 맞는가" 가 아니라 "증거가 몇 개를 동시에 켜는가" 가 질문이다.

## 2. 가설 판정 요약

| 가설 | 판정 | 근거 한 줄 |
|---|---|---|
| **상위** `H-RF2-A-FIRING-COOCCURRENCE` — 결정적 증거는 archetype 을 유일하게 지목하지 못한다 | **SUPPORTED** | STRONG 후보 평균 1.84개 · multi 30/56 > single 13/56 |
| **H-A1** LIST_FAMILY_COLLAPSE (C/I/P/M 가 반복 list·card 신호를 공유해 서로 안 나뉜다) | **PARTIALLY_SUPPORTED** | 기전(공유 card region 신호)은 확인. 그러나 **차별성은 성립 안 함** — family 내부 동시발화(J 0.145/0.548)가 나머지 쌍(0.213/0.581)보다 오히려 **낮다** |
| **H-A2** UTILITY_CATCHALL | **PARTIALLY_SUPPORTED** | 희석형 기준 미충족(단독발화율 오히려 최고 0.219). **구제형(rescue) 기준 충족** — 발화율 최고(52/56), 다른 6개가 모두 non-STRONG 인 20건 중 7건(35%)에서 UTILITY 만 STRONG |
| **H-A3** NO_EVIDENCE_DOMINANT (RF001-A 주장) | **REFUTED** | 증거 부재 13/56(STRONG) · 4/56(WEAK+) < 다중후보 30/56 · 50/56. 지배적 실패는 **증거 부재가 아니라 다중후보**다 |

## 3. 입력 · 분석단위 · N

| 항목 | 값 |
|---|---|
| 관측표 | `results/D_OBSERVATION_TABLE_v2.csv` — 66행 × 65열, sha256 `c39c10f09f7a6a76…` |
| 텍스트 코퍼스 | `results/D_TEXT_CORPUS_v2.csv` — 56행 × 23열, sha256 `bf6bb772faa45541…` |
| 코드 | `tools/rf2_a_rule_firing.py`, sha256 `277c3b3b356a1dd4…` |
| 결과 JSON | `results/RF2_A_rule_firing.json`, sha256 `189a1ba7232cd589…` |
| 분석단위 | **target (`wtg`), `in_mart==1`** |
| **N = 56** (모든 비율의 기본 분모) | 관측표 66행 중 `in_mart==0` 10행 제외 |
| missing | 텍스트 코퍼스 미결합 target **0건** (56/56 join). 단, `dom_body_text_len < 200` 또는 `dom_body_empty==1` 인 **DOM_DEAD 4건**은 모든 branch 를 NONE 으로 고정했다 (`64d30ef2…`, `ef06dc94…`, `95967b50…`, `fb3d1841…`) |
| prior 분포 (gold 아님) | ITEM_DETAIL 26 / FINANCIAL_ACTION_ENTRY 10 / UTILITY_ENTRY 5 / COMMUNICATION_ENTRY 4 / PLACE_LOOKUP 4 / QUERY 4 / CONTENT_OPEN 3 — **5개 class 가 n ≤ 5**. per-class 수치엔 전부 Wilson 95% CI 를 붙였고, 그 폭이 결론을 지지하지 못하는 곳에서는 결론을 내지 않았다 |
| raw 재파싱 | 없음. `dom.html` 을 다시 열지 않고 D 관측표·코퍼스만 사용했다 |

## 4. STRONG / WEAK 정의 (전문 · 결과 관측 전 확정)

```
[FIRING LEVEL DEFINITION — RF2A_FIRING_v1, 결과 관측 전 확정]

SSOT 01_REPRESENTATIVE_FUNCTION_MAPPING_DT_v2.1 §5 는 각 branch 를 REGION evidence 와
ENDPOINT evidence 두 층으로 정의한다. 그 이층 구조를 그대로 3값 firing level 로 쓴다.

  STRONG : REGION evidence ∧ ENDPOINT evidence 가 모두 발화.
           = SSOT §6 "강한 후보(strong candidate)" 에 해당.
  WEAK   : REGION 또는 ENDPOINT 중 정확히 하나만 발화.
           = 후보로 올라오지만 §6 resolver 를 통과시킬 수 없는 부분증거.
  NONE   : 둘 다 발화하지 않음.

  WEAK+  : WEAK 또는 STRONG (= 어떤 형태로든 발화).

이 정의는 정적 DOM/텍스트 증거만으로 판정한다. SSOT §5 의 ENDPOINT 는 원래 "상태 전이가
실제로 일어난 순간"이지만 D 는 조작 없는 landing 단일 상태만 관측하므로, ENDPOINT 는
**전이를 성립시키는 구조의 presence evidence** 로 조작화한다 (SSOT §5 Branch I 가 명시적으로
허용하는 "transaction control 의 존재", §8 "control presence → endpoint evidence 로 사용 가능"
과 동일한 완화). 이 완화는 endpoint 발화를 과대추정하는 방향이며 limitation 에 기재한다.

분석단위 = target (in_mart==1), N=56. 어떤 target 도 force-map 하지 않는다.
abstention(=모든 archetype NONE) 은 실패가 아니라 결과다.
```

## 5. 규칙 전문 (SSOT §5 Stage 3 branch tree 조작화)

```
공통 표기
  CTRL(x)  = buttons|aria_labels|nav_links|form_labels 중 하나라도 어휘 x 매치
  NAV(x)   = title|headings|landmarks|nav_links 중 하나라도 어휘 x 매치
  ANY(x)   = 11개 surface 필드(title,headings,landmarks,nav_links,buttons,aria_labels,
             placeholders,form_labels,input_names,card_texts,url_tokens) 중 하나라도 매치
  CARD     = card_texts 필드가 비어있지 않음 (반복 card/list 구조 존재)
  DOM_DEAD = dom_body_empty==1 또는 dom_body_text_len < 200 (증거 없음 상태)

DOM_DEAD 인 target 은 모든 branch 에서 NONE 으로 고정한다 (force-map 금지).

Branch Q — QUERY (SSOT §5 Branch Q)
  REGION   : search_inputs_n >= 1  OR  ANY(search) on placeholders|input_names
  ENDPOINT : (form_labels 비어있지 않음 또는 input_names 비어있지 않음)
             OR CTRL(search_submit)  OR  url_tokens ~ search|query|q=|find

Branch C — CONTENT_OPEN (SSOT §5 Branch C)
  REGION   : CARD  AND  ANY(content)
  ENDPOINT : article_present == 1  OR  CTRL(media_play)  OR  NAV(media_play)

Branch I — ITEM_DETAIL (SSOT §5 Branch I)
  REGION   : CARD  AND  (ANY(item) OR ANY(price))
  ENDPOINT : ANY(price)  AND  CTRL(txn_control)
             (SSOT: item name + price + transaction control 의 '존재')

Branch P — PLACE_LOOKUP (SSOT §5 Branch P)
  REGION   : ANY(place)  AND  (CARD OR CTRL(place) OR search_inputs_n >= 1)
  ENDPOINT : ANY(place_detail)  OR  (ANY(place) AND search_inputs_n >= 1)
             OR url_tokens ~ map|place|store|location|branch

Branch M — COMMUNICATION_ENTRY (SSOT §5 Branch M)
  REGION   : ANY(comm)  AND  (CARD OR CTRL(comm))
  ENDPOINT : CTRL(compose)  OR  gate_password_input_n >= 1
             (SSOT: 로그인 control '존재'만으로는 endpoint 아님. 실제 login gate 도달 =
              password input 이 DOM 에 존재하는 상태로만 인정)

Branch F — FINANCIAL_ACTION_ENTRY (SSOT §5 Branch F)
  REGION   : CTRL(finance)  OR  NAV(finance)
  ENDPOINT : gate_password_input_n >= 1
             OR url_tokens ~ bank|card|pay|loan|insur|fin|invest|securit
             OR NAV(finance) AND CTRL(auth_gate)

Branch U — UTILITY_ENTRY (SSOT §5 Branch U)
  REGION   : CTRL(utility) OR NAV(utility)
  ENDPOINT : n_primary_action_candidates >= 1
```

어휘 lexicon 전문은 결과 JSON 의 `signal_lexicon` 에 그대로 있다 (14개 정규식 계열:
`search / search_submit / content / media_play / item / price / txn_control / place /
place_detail / comm / compose / finance / auth_gate / utility`).

**규칙 동결 이력.** 규칙·어휘·임계값은 첫 실행 전에 확정했고 결과를 본 뒤 바꾸지 않았다.
실행 중 고친 것은 구현 결함 두 건뿐이다 — (1) `int(NaN)` 예외, (2) pandas `NaN` 이 truthy 라
`v or ""` 가 `"nan"` 문자열을 만들어 `CARD`/`FORMISH` 가 항상 참이 되던 버그. 둘 다
"규칙이 의도대로 동작하지 않던 것"의 수정이지 규칙 변경이 아니다.

## 6. 방법

1. 66행 관측표에서 `in_mart==1` 56행을 취하고 `wtg` 로 텍스트 코퍼스를 결합 (중복 0, 결측 0).
2. target 당 **명명된 결정적 신호** 를 계산한다 (`CARD`, `SEARCH_INPUT`, `PWD_GATE`,
   `ARTICLE`, `PRIMARY_ACTION`, `DOM_DEAD`, 그리고 14개 어휘 계열 × {ANY, CTRL, NAV} surface).
3. §5 규칙으로 archetype 별 REGION/ENDPOINT 를 판정하고, 발화한 신호 이름을 그대로 기록한다
   (`per_target[*].firing[*].region/endpoint` — 모든 발화에 provenance 가 남는다).
4. 56×7 firing matrix 를 만들고 STRONG / WEAK+ 두 수준에서
   후보 수 분포 · 7×7 동시발화 행렬 · Jaccard · 조건부 확률 · overlap network 를 계산한다.
5. 사전등록 기준을 **코드가** 판정한다 (verdict 를 손으로 쓰지 않는다).

## 7. Firing matrix 요약

그림: `figures/RF2_A_firing_heatmap.png` (56행 × 7열, prior 별 정렬, 0=NONE 1=WEAK 2=STRONG)

**archetype 별 marginal 발화 (분모 N=56, Wilson 95% CI)**

| archetype | STRONG n (rate) | STRONG 95% CI | WEAK+ n (rate) | WEAK+ 95% CI |
|---|---|---|---|---|
| Q QUERY | 20 (0.357) | 0.245–0.488 | 37 (0.661) | — |
| C CONTENT_OPEN | 16 (0.286) | 0.184–0.415 | 38 (0.679) | — |
| I ITEM_DETAIL | 6 (0.107) | 0.050–0.215 | 34 (0.607) | — |
| P PLACE_LOOKUP | 11 (0.196) | 0.113–0.318 | 27 (0.482) | — |
| M COMMUNICATION_ENTRY | 4 (0.071) | 0.028–0.170 | 30 (0.536) | 0.407–0.660 |
| F FINANCIAL_ACTION_ENTRY | 14 (0.250) | 0.155–0.377 | 33 (0.589) | 0.459–0.708 |
| U UTILITY_ENTRY | **32 (0.571)** | 0.441–0.692 | **52 (0.929)** | 0.830–0.972 |

## 8. Candidate-count 분포 (그림 `RF2_A_candidate_distribution.png`)

분모 N=56.

| target 당 후보 수 | 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 평균 |
|---|---|---|---|---|---|---|---|---|---|
| **STRONG** | 13 | 13 | 11 | 12 | 5 | 1 | 0 | 1 | **1.84** |
| **WEAK+** | 4 | 2 | 2 | 5 | 16 | 8 | 7 | 12 | **4.48** |

**7개 archetype 을 전부 WEAK+ 로 켜는 target 이 12/56 (21.4%)** 다.
STRONG 이 4개 이상인 target 도 7/56 (12.5%) 있다.

## 9. no-evidence / single-candidate / multi-candidate (분모 N=56)

| 수준 | no-evidence | single-candidate | multi-candidate |
|---|---|---|---|
| **STRONG** | **13/56 = 0.232** (Wilson 0.141–0.358) | **13/56 = 0.232** (0.141–0.358) | **30/56 = 0.536** (0.408–0.658) |
| **WEAK+** | **4/56 = 0.071** (0.028–0.170) | **2/56 = 0.036** (0.010–0.122) | **50/56 = 0.893** (0.783–0.951) |

WEAK+ 기준 증거가 하나도 없는 4건은 **전부 DOM_DEAD** 다. 즉 "증거가 없다" 는 상황은
**수집 결함(본문 200자 미만)** 과 동일 집합이지 규칙의 판별 실패가 아니다.

SSOT §6 resolver 를 그대로 대입하면: 유일 후보 → RULE 확정 **13건**, 두 개 이상 강후보 →
NLP fallback **30건**, evidence 없음 → `AMBIGUOUS_UNRESOLVED` **13건**.
선행 RF001-A 의 `mapped 11 / abstention 40` 과 자릿수·구조가 일치한다(독립 구현, 판정 재사용 없음).
**RF001-A 의 abstention 40건은 "증거가 없어서" 가 아니라 "강후보가 둘 이상이어서" 발생한 것이다.**

## 10. 7×7 co-occurrence (그림 `RF2_A_cooccurrence.png`, `RF2_A_overlap_network.png`)

행렬 전문은 JSON `cooccurrence_matrix`. 대각은 marginal. 분모는 pair 별로 명시한다.

**STRONG 동시발화 상위 (both_n / Jaccard, 분모 = 합집합)**

| pair | both_n | Jaccard | list-family? |
|---|---|---|---|
| F–U | 13 | 0.394 | no |
| Q–U | 14 | 0.368 | no |
| Q–C | 9 | 0.333 | no |
| C–U | 12 | 0.333 | no |
| Q–F | 8 | 0.308 | no |
| C–F | 7 | 0.304 | no |
| Q–P | 7 | 0.292 | no |
| **C–P** | 6 | 0.286 | **yes** |
| P–U | 8 | 0.229 | no |
| … | | | |
| **C–I** | 3 | 0.158 | **yes** |
| **I–P** | 2 | 0.133 | **yes** |
| **C–M** | 2 | 0.111 | **yes** |
| **I–M** | 1 | 0.111 | **yes** |
| **P–M** | 1 | 0.071 | **yes** |

**WEAK+ 동시발화 상위**: C–U 38 (J 0.731), Q–U 37 (0.712), I–U 34 (0.654),
**I–M 25 (0.641)**, **C–I 28 (0.636)**, F–U 33 (0.635), M–F 24 (0.615) …
최하위는 P–F 16 (0.364).

**WEAK+ 수준에서 Jaccard 가 0.36 아래로 내려가는 쌍이 하나도 없다.** 즉 어떤 두 archetype 을
집어도 절반 가까운 target 에서 함께 켜진다. 이것이 이 EDA 의 1차 결과다.

## 11. H-A1 — list-family collapse 정량화

**사전등록 기준** — (a) 기전: C/I/P/M 네 branch 의 REGION 규칙이 반복 card 구조 신호를 공유하고
실제로 card 기반 region 발화가 각각 1회 이상. (b) 차별성: family 내부 6쌍의 평균 Jaccard >
나머지 15쌍(대조군)의 평균, STRONG·WEAK+ 두 수준 모두.

**(a) 기전 — 충족.** card 기반 REGION 발화 횟수: CONTENT_OPEN 24 · ITEM_DETAIL 43 ·
PLACE_LOOKUP 25 · COMMUNICATION_ENTRY 29. 네 branch 모두 반복 card 구조를 region 근거로 쓴다.
`ITEM_DETAIL` 은 WEAK+ 발화 34건 중 **34건 전부**가 `card_repeat AND lex:item` 이라는 단일
region 신호에서 나온다 — 다른 근거가 사실상 없다.

**(b) 차별성 — 불충족.**

| 수준 | list-family 6쌍 평균 J | 대조군 15쌍 평균 J | gap |
|---|---|---|---|
| STRONG | **0.145** (median 0.122, range 0.071–0.286) | **0.213** (0.229, 0.040–0.394) | **−0.068** |
| WEAK+ | **0.548** (0.518, 0.462–0.641) | **0.581** (0.578, 0.364–0.731) | **−0.034** |

동시발화 절대비율(분모 N=56)도 같은 방향이다: family 평균 STRONG 0.045 vs 대조군 0.111,
WEAK+ 0.408 vs 0.492.

**판정: PARTIALLY_SUPPORTED.** C 가 지적한 **기전은 실재한다** — 네 branch 가 같은 card 신호를
근거로 쓴다. 그러나 **"이 네 개가 서로 특히 안 나뉜다"는 차별적 주장은 데이터에서 성립하지 않는다.**
비분리성은 list-family 국소 문제가 아니라 **7개 전체의 전역 문제**이고, 오히려 가장 강하게 엉키는
쌍은 F–U, Q–U, Q–C 처럼 family 를 가로지르는 쌍이다.

**POST-HOC 기술 보조분석**(판정 기준 아님): Q 와 U 는 hub 로 관측됐다. 대조군에서 이 둘을 빼면
대조군은 C–F, I–F, P–F, M–F 4쌍만 남고 평균 J 는 STRONG 0.157 / WEAK+ 0.512 가 된다.
gap 은 STRONG −0.012, WEAK+ **+0.036** 으로 부호가 뒤집힌다. 즉 대조군 평균의 상당 부분이
hub 두 개에서 왔다. 그래도 gap 은 ±0.04 규모이고 6쌍 vs 4쌍 비교라 **차별성을 지지하기엔 근거가
약하다.** 이 보조분석은 사전등록 판정을 바꾸지 않는다.

## 12. H-A2 — UTILITY_ENTRY 특이도 / catch-all

**사전등록 기준** — (a) 희석형: UTILITY 의 STRONG 단독발화 비율(`sole_share`)이 7개 중 최소.
(b) 구제형: UTILITY 발화율이 최대이고 `rescue_rate` 가 낮지 않음.

**(a) 희석형 — 불충족.** STRONG 단독발화 비율: **U 0.219 (7/32)** · Q 0.200 (4/20) ·
I 0.167 (1/6) · P 0.091 (1/11) · C 0.000 (0/16) · M 0.000 (0/4) · F 0.000 (0/14).
UTILITY 는 최소가 아니라 **최대**다. STRONG 발화 시 평균 동반 발화 수도 U 가 1.66 으로 가장 낮다
(C 2.44, M 2.75). UTILITY 는 "아무 데나 섞여 희석되는" 형태가 아니다.

**(b) 구제형 — 충족.**
- UTILITY 발화율 WEAK+ **52/56 = 0.929** (Wilson 0.830–0.972), STRONG **32/56 = 0.571** — 둘 다 7개 중 최고.
- `rescue_rate`: 다른 6개가 **모두 non-STRONG** 인 target **20건** 중 UTILITY 가 STRONG 인 것이
  **7건 = 0.350** (Wilson 0.181–0.567). 균등 우연 baseline 1/7 = 0.143 을 넘는다.
  (이 baseline 수치 자체는 결과 관측 후 명시했다 — JSON 에 `post_hoc_specified_threshold: true`
  로 기록. "rescue_rate 가 낮지 않으면 catch-all" 이라는 방향과 지표는 사전등록돼 있었다.)

**규칙 특이도의 구조적 원인.** UTILITY 의 ENDPOINT 는 `n_primary_action_candidates >= 1`
단 하나이고, 이것이 **56건 중 52건에서 켜진다**. 즉 UTILITY 의 endpoint 는 사실상
"이 페이지에 클릭 가능한 주요 컨트롤이 있는가" 라는 **페이지 일반 속성**이다. REGION 어휘
(`신청|발급|접수|예약|예매|등록|납부|계산|조회|변경|해지|취소|확인|…`)도 다른 여섯 branch 의
어휘보다 도메인 결합도가 낮다 — `조회`·`확인`·`신청` 은 은행·쇼핑·공공·통신 어디에나 있다.
대조적으로 F 의 endpoint 는 세 갈래(password gate 3 / url:finance 4 / finance+auth 13)로
분산돼 있고, M 의 endpoint 는 `compose` 2건 + password gate 3건으로 **매우 희소**하다.

**판정: PARTIALLY_SUPPORTED.** UTILITY 는 catch-all 이 맞되, brief 가 상정한 "무차별 희석형"이
아니라 **"최후 잔존형(residual)"** 이다: 가장 자주 켜지고, 다른 게 다 꺼졌을 때 유일하게 남는다.
운영 관점에서 이 둘은 다르게 처치해야 한다 (§16).

## 13. archetype 별 shared-signal profile (그림 `RF2_A_shared_signal_profile.png`)

**exclusivity (WEAK+ 단독발화 비율, 분모 = 자기 발화 수)** — 7개 중 6개가 **0.000**:
Q 0/37, C 0/38, I 0/34, P 0/27, M 0/30, F 0/33. **U 만 2/52 = 0.038** (Wilson 0.011–0.130).
**즉 WEAK+ 수준에서 어떤 archetype 도 혼자 켜지지 못한다.**

**신호 문자열 자체를 두 archetype 이 공유하는 경우는 딱 하나** — `password_gate_reached`
가 M 의 endpoint 와 F 의 endpoint 양쪽에 들어간다 (3 target). 나머지 공유는 문자열이 아니라
**증거 기반의 공유**다: 같은 `card_texts` 블록이 C 의 `content` 어휘, I 의 `item` 어휘,
P 의 `place` 어휘, M 의 `comm` 어휘를 동시에 만족시킨다. 한국어 landing 의 카드 텍스트는
"매장 찾기 | 이벤트 | 리뷰 | 상품 더보기" 처럼 네 어휘를 한 블록에 담는다.

**archetype 별 주 발화 신호 (상위)**

| | 주 신호 (발화 target 수) |
|---|---|
| Q | endpoint `lex:search_submit@control` 31 · endpoint `form_or_input_present` 29 · region `lex:search@placeholder/input_name` 18 · region `search_inputs_n>=1` 10 |
| C | region `card_repeat AND lex:content` 24 · endpoint `lex:media_play@control` 23 · endpoint `lex:media_play@nav` 16 · endpoint `article_present` 7 |
| I | region `card_repeat AND lex:item` **34 (= 발화 전량)** · region `card_repeat AND lex:price` 9 · endpoint `lex:price AND lex:txn_control@control` **6** |
| P | region `lex:place AND (card|place@ctrl|search)` 25 · endpoint `lex:place_detail` 6 · endpoint `lex:place AND search_input` 5 · endpoint `url:place` 4 |
| M | region `lex:comm AND (card|comm@ctrl)` 29 · endpoint `password_gate_reached` 3 · endpoint `lex:compose@control` 2 |
| F | region `lex:finance@control` 24 · region `lex:finance@nav` 23 · endpoint `finance@nav AND auth_gate@ctrl` 13 · endpoint `url:finance` 4 · endpoint `password_gate_reached` 3 |
| U | endpoint `n_primary_action_candidates>=1` **52** · region `lex:utility@control` 29 · region `lex:utility@nav` 18 |

**비대칭이 핵심이다.** I 와 M 은 **region 은 흔하고 endpoint 는 거의 없다** (I: region 34 →
endpoint 6, M: region 29 → endpoint 5). 반대로 U 는 **endpoint 가 흔하고**(52), Q 도
endpoint 가 흔하다(31+29). 그래서 STRONG 은 U/Q/C/F 로 쏠리고, prior 상 최대 class 인
ITEM_DETAIL(n=26)은 STRONG 이 6건밖에 안 된다. **가장 많은 target 을 차지하는 prior class 가
가장 증거가 안 잡히는 class 다.**

## 14. prior_agreement (accuracy 아님)

`prior_archetype` 은 business-domain prior 일 뿐이고 gold 가 아니다. 아래는 "규칙 발화가
prior 와 겹치는가" 의 기술통계일 뿐, 정오 판정이 아니다.

| 지표 | n / 분모 | rate | Wilson 95% |
|---|---|---|---|
| prior 가 STRONG 후보 집합에 포함 | 17 / 56 | 0.304 | 0.199–0.433 |
| prior 가 WEAK+ 후보 집합에 포함 | 43 / 56 | 0.768 | 0.642–0.859 |
| **유일 STRONG 후보 = prior** | **1 / 56** | **0.018** | 0.003–0.095 |

**prior 는 후보 집합 안에는 대체로 들어오지만(0.768), 규칙이 그것을 유일하게 지목한 경우는
56건 중 1건뿐이다.** 즉 문제는 "증거가 prior 를 놓친다" 가 아니라 "증거가 prior 를 다른 여섯 개와
구분하지 못한다" 이다.

per-prior-class (n≤5 가 5개 class — CI 폭 때문에 class 간 비교는 하지 않는다):
COMMUNICATION_ENTRY 0/4 (0.000, 0.000–0.490) · CONTENT_OPEN 0/3 (0.000, 0.000–0.562) ·
FINANCIAL 3/10 (0.300, 0.108–0.603) · ITEM_DETAIL 5/26 (0.192, 0.085–0.379) ·
PLACE 3/4 (0.750, 0.301–0.954) · QUERY 3/4 (0.750, 0.301–0.954) · UTILITY 3/5 (0.600, 0.231–0.882).

## 15. 반례 · 결론에 불리한 관측

1. **H-A1 의 반례가 곧 §11 결과다.** C 의 construct risk 를 검증하러 갔다가 "그 네 개가 특히
   나쁘지는 않다" 를 얻었다. 이건 C 의 우려를 기각하는 게 아니라 **범위를 넓히는** 반례다.
2. **UTILITY 를 빼도 문제가 사라지지 않는다.** UTILITY 를 제외한 6개만으로도 WEAK+ multi-candidate
   는 여전히 지배적이다 (Q–C 28, C–I 28, Q–F 26, Q–I 26, I–M 25). catch-all 제거는 부분 처방이다.
3. **DOM_DEAD 4건을 어떻게 세느냐가 H-A3 를 흔들지 않는다.** 4건을 전부 "증거 부재" 로 넣어도
   4/56 = 0.071 로 multi 50/56 = 0.893 에 한참 못 미친다. 반대로 4건을 제외하면(N=52)
   WEAK+ no-evidence 는 0/52 가 된다. **어느 쪽으로 세도 H-A3 는 기각된다.**
4. **단독 STRONG 13건이 곧 "잘 잡힌 13건" 은 아니다.** 그중 prior 와 일치한 것은 1건이다.
   유일성이 타당성을 뜻하지 않는다.
5. **STRONG 7개 전부가 켜진 target 이 1건 있다.** 규칙이 페이지 하나에서 모든 archetype 의
   region∧endpoint 를 동시에 만족시킬 수 있다는 존재증명이다.

## 16. Verdict

**`SUPPORTED`** — 상위 가설 `H-RF2-A-FIRING-COOCCURRENCE`:
현재의 deterministic evidence 는 target 당 **평균 1.84개의 STRONG 후보, 4.48개의 WEAK+ 후보**를
발화시키며, STRONG multi-candidate(30/56)가 single-candidate(13/56)를 압도한다.
**결정적 증거는 archetype 을 유일하게 지목하지 못한다.**

하위 판정: H-A1 `PARTIALLY_SUPPORTED` · H-A2 `PARTIALLY_SUPPORTED` · H-A3 `REFUTED`.

## 17. Limitation

**가장 무거운 것부터.**

1. **ENDPOINT 를 정적 presence 로 완화한 것이 이 EDA 의 최대 위협이다.** SSOT §5 의 endpoint 는
   "상태 전이가 실제로 일어난 순간" 인데 D 는 조작 없는 단일 상태만 본다. 그래서 endpoint 를
   "전이를 성립시키는 구조의 존재" 로 읽었다 (SSOT §5 Branch I / §8 이 허용하는 완화). 이 완화는
   **endpoint 발화를 일방적으로 과대추정**하고, 따라서 STRONG 발화와 동시발화율을 **위로 편향**시킨다.
   상호작용 기반 endpoint 로는 STRONG 수가 줄고 no-evidence 가 늘 것이다 — 즉 H-A3 기각의 강도는
   이 완화에 의존한다. **다만 WEAK+ 수준의 non-separability(어떤 쌍도 J 0.36 미만이 없음)는
   region 신호만으로도 성립하므로 이 완화에 의존하지 않는다.**
2. **어휘 lexicon 은 내가 만든 조작화다.** SSOT §5 는 "place/address/location vocabulary" 같은
   자연어 서술만 주고 어휘 목록을 주지 않는다. 동시발화율은 페이지의 성질인 만큼이나
   **내 어휘 경계의 성질**이다. 어휘를 좁히면 발화가 줄고 co-firing 도 준다.
   → 재현 시 lexicon 을 바꿔 민감도를 봐야 한다 (§18).
3. **n ≤ 5 인 prior class 가 5개** (UTILITY 5 / COMMUNICATION 4 / PLACE 4 / QUERY 4 / CONTENT 3).
   per-class Wilson CI 폭이 0.5 를 넘는 곳이 많다. class 간 순위 비교는 하지 않았고 하면 안 된다.
4. **56건은 pair 통계에 작다.** list-family 6쌍 vs 대조군 15쌍 비교는 쌍 수준 n 이 각각 6, 15 라
   평균 차 ±0.07 에 신뢰구간을 붙이지 않았다. §11 의 gap 은 **점추정 방향 진술**이지 검정이 아니다.
5. **DOM_DEAD 4건은 규칙의 실패가 아니라 수집의 실패**인데 같은 표에 섞여 있다.
   §15-3 처럼 양방향으로 세어봤지만, 수집 결함과 매핑 불가를 하나의 파이프라인이 같은 출력으로
   내보내는 구조 자체가 위험하다.
6. **prior_archetype 은 gold 가 아니다.** §14 는 어떤 의미로도 정확도가 아니다. 진짜 분리가능성은
   독립 label 없이는 판정할 수 없다.
7. **단일 상태·단일 시점.** 동적 로딩·A/B·개인화·지역 차이를 관측하지 않았다.

## 18. Production implication

1. **NLP fallback 을 "소수 ambiguity 해결기" 로 설계한 SSOT §7 의 전제는 이 데이터에서 성립하지 않는다.**
   §6 resolver 를 그대로 돌리면 56건 중 **30건(53.6%)이 fallback 으로 간다.** fallback 은 예외
   경로가 아니라 **주 경로**다. §7 의 threshold 정책·coverage 목표를 이 비율 위에서 다시 잡아야 한다.
2. **§10 release gate 의 `holdout coverage >= 0.75` 는 현재 rule-only 로 도달 불가다.**
   유일 STRONG 후보가 나오는 target 이 13/56 = 0.232 다. coverage 를 rule 로 채우려는 시도는
   force-map 압력이 되고, 이는 §6 의 "unresolved cases are not force-mapped" 와 정면 충돌한다.
   **coverage 목표를 낮추거나, evidence 를 늘리거나, 둘 중 하나다 — 규칙 완화는 답이 아니다.**
3. **UTILITY_ENTRY 의 endpoint 정의를 바꿔야 한다.** `n_primary_action_candidates >= 1` 에
   해당하는 "primary control 이 actionable" 은 56건 중 52건에서 참이므로 판별력이 사실상 0 이다.
   SSOT §5 Branch U 의 "특정 목적의 도구 기능면" 에서 **"특정 목적"** 을 구조로 조작화하지 않으면
   UTILITY 는 계속 residual 로 남는다. 최소한 **resolver 에서 UTILITY 를 마지막 순위로 강등**하고
   (§6 evidence precedence 에 명시), 다른 후보가 있으면 UTILITY 를 자동 탈락시키는 편이 낫다.
4. **ITEM_DETAIL 과 COMMUNICATION_ENTRY 는 region 은 흔한데 endpoint 가 거의 없다** (34→6, 29→5).
   detector 를 만들 때 이 두 archetype 은 **region 만으로 채택하면 대량 과탐**, endpoint 를 요구하면
   **대량 미탐**이 된다. prior 상 최대 class 인 ITEM_DETAIL(n=26)이 여기 걸린다 —
   B 의 detector 우선순위는 여기다.
5. **네 개(C/I/P/M)만 병합하는 처방은 근거가 없다.** §11 이 보여주듯 얽힘은 전역적이고 최강 쌍은
   F–U, Q–U 다. archetype taxonomy 를 손댈 거면 4개 병합이 아니라 **7개 전체의 판별 신호 재설계**다.
   단, 7 archetype 은 SSOT 동결 대상이므로 D 는 변경을 제안하지 않는다 — **신호 재설계** 만 제안한다.
6. **`password_gate_reached` 가 M 과 F 양쪽 endpoint 에 들어간다.** 유일하게 문자열까지 공유되는
   신호다. 이 3건은 guard 관점에서도 민감하므로(§8 login gate) B/C 가 별도로 봐야 한다.

## 19. 추가 연구질문

- **RQ-D-RF-002-a1** lexicon 민감도: 어휘 경계를 ±30% 넓히고 좁혔을 때 §10 의 pairwise Jaccard
  하한(현재 0.364)이 얼마나 움직이는가. 비분리성이 어휘 인공물인지 페이지 성질인지 가른다.
- **RQ-D-RF-002-a2** endpoint 완화 제거: endpoint 를 `article_present`, `search_inputs_n`,
  `gate_password_input_n`, `n_primary_action_candidates` 같은 **구조 신호만**으로 좁히면
  (어휘 기반 endpoint 전부 제거) no-evidence 비율이 얼마가 되는가. H-A3 의 완화 의존도 정량화.
- **RQ-D-RF-002-a3** region-endpoint 비대칭 지수: archetype 별 `endpoint_n / region_n` 을
  detector 난이도 예측자로 쓸 수 있는가 (I 0.18, M 0.17 vs U 1.00 — 이 순서가 B 의 실제
  detector 성능 순서와 맞는지는 D 가 검증할 수 없다).
- **RQ-D-RF-002-a4** DOM_DEAD 4건이 수집 결함인지 실제 빈 landing 인지 — 수집 파이프라인 쪽 질문.
- **RQ-D-RF-002-a5** "primary action candidate" 를 목적 특이적으로 재정의할 수 있는가.
  UTILITY residual 문제의 직접 처방.

---

### 산출물

| 파일 | 내용 |
|---|---|
| `tools/rf2_a_rule_firing.py` | 규칙 구현 · 전 분석 · 그림 생성 |
| `results/RF2_A_rule_firing.json` | 56×7 firing matrix · per-target signal provenance · co-occurrence · 판정 |
| `results/RF2_A_FINDINGS.md` | 이 문서 |
| `figures/RF2_A_firing_heatmap.png` | 56×7 firing matrix |
| `figures/RF2_A_candidate_distribution.png` | STRONG / WEAK+ 후보 수 분포 |
| `figures/RF2_A_cooccurrence.png` | 7×7 동시발화 행렬 (STRONG / WEAK+) |
| `figures/RF2_A_overlap_network.png` | strong-candidate overlap network |
| `figures/RF2_A_shared_signal_profile.png` | exclusivity + 조건부 발화확률 |
| `notebooks/d_research/RF2_A_rule_firing.ipynb` | 요약 노트북 (Restart→Run All 검증) |
