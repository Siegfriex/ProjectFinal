# D-RF2-D — Hierarchical interaction architecture vs flat 7-way mapping

| | |
|---|---|
| child_id | `D-RF2-D` (parent RQ `RQ-D-RF-002`, parent run `ae754858ba3a4be391e5f811640d3fd8`) |
| hypothesis_id | `H-RF2-D-HIERARCHY` |
| rule version | `RF2D_HIER_v1` |
| seed | `20260827` (규칙은 결정론적, 임베딩 인코딩만 seed 사용) |
| **verdict** | **NOT_SUPPORTED** |
| plane / authority | D / `NON_CANONICAL` |
| code | `tools/rf2_d_hierarchical.py` |
| result | `results/RF2_D_hierarchical.json` |
| notebook | `notebooks/d_research/RF2_D_hierarchical.ipynb` |

---

## 0. 이것이 construct 변경이 아니라는 선언

최종 output 공간은 **frozen 7 archetype 그대로**다: `QUERY` · `CONTENT_OPEN` · `ITEM_DETAIL` ·
`PLACE_LOOKUP` · `COMMUNICATION_ENTRY` · `FINANCIAL_ACTION_ENTRY` · `UTILITY_ENTRY` · `ABSTAIN`.

Level 1 interaction primitive 는 **중간 단계**이며 leaf 가 아니다. 새 class 를 만들지 않았고,
7 archetype 정의를 손대지 않았고, SSOT 를 수정하지 않았다.

`prior_archetype` 은 **gold label 이 아니라 prior** 다. 따라서 이 문서는 accuracy 라는 단어를
쓰지 않고 `prior_agreement` 로만 보고한다.

---

## 1. RQ

> SSOT 01 (`LA-RFDT-2.1`) §5 Stage 3 는 7 archetype branch 를 **평평하게** 나열한다.
> 그런데 §5 의 각 branch Endpoint 절을 읽으면 branch 들은 서로 다른 **interaction primitive**
> 위에 세워져 있다. 그렇다면 7-way 를 한 번에 가르는 대신 **primitive 를 먼저 가르고 그 안에서
> archetype 으로 분기**하는 계층 구조가 관측 가능한 evidence 와 더 잘 맞는가?

---

## 2. 가설 3개와 판정

| 가설 | 진술 | 판정 |
|---|---|---|
| **H-D1 HIERARCHY_HELPS** | 계층이 flat 보다 coverage 를 올리거나 같은 coverage 에서 prior_agreement 를 올린다 | **PARTIALLY_SUPPORTED** (문자적 coverage 조건만, 실질 이득 0) |
| **H-D2 LEVEL1_IS_EASY** | Level 1(4 primitive)은 관측 evidence 로 잘 갈리는데 Level 2 가 어렵다 | **REFUTED** |
| **H-D3 NO_GAIN** | 계층은 flat 과 실질 차이가 없다 | **SUPPORTED** |
| **최상위 `H-RF2-D-HIERARCHY`** | 계층 구조가 관측 evidence 와 더 잘 맞는다 | **NOT_SUPPORTED** |

`REFUTED` 가 아니라 `NOT_SUPPORTED` 로 닫은 이유: n=56, 7 class 중 5 개가 n≤5, prior 가
gold 가 아니어서 "계층이 **나쁘다**"를 확증할 검정력이 없다. 방향은 일관되게
"이득 없음 ~ 약한 손해"다.

---

## 3. 입력

| 파일 | 행 | sha256 |
|---|---|---|
| `results/D_OBSERVATION_TABLE_v2.csv` | 66행 중 `in_mart==1` **56행** | `82c86d33dcaad61b7d9e9c1ff70d84b2b2a2b7f3ea67c07f4c3e4b1a41f7d2fd`* |
| `results/D_TEXT_CORPUS_v2.csv` | 56행 | (JSON `inputs[]` 에 기록) |
| `SSOTV2/01_REPRESENTATIVE_FUNCTION_MAPPING_DT_v2.1.md` | 규칙 원문 §5 · §6 | (JSON `inputs[]` 에 기록) |

\* 정확한 sha256 값은 `results/RF2_D_hierarchical.json` 의 `inputs[]` 이 정본이다.
이 표는 사람이 읽는 요약이다.

raw evidence(`dom.html`, `probe.json`)를 다시 파싱하지 않았다. D 공용 빌더 산출물만 소비했다.

**방화벽**: holdout label · `LABEL_SPLIT_FROZEN*` · `HOLDOUT_FOR_C*` · `RAW_L1~L4*` ·
`PACKET_L*` · `*_OVERLAP*` · `PRECEDENCE_CONTESTED*` · `CALIBRATION_FOR_B*` · `**/control/**` ·
B/C 의 target-level holdout error report — **하나도 열지 않았다.** REAL_TARGET 에 접속하지
않았다. gold label 을 만들지 않았다. 네트워크를 쓰지 않았다 (`HF_HUB_OFFLINE=1`).

선행 `RF001_A_rule_dt.json` 은 **가설로만** 참조했고 판정을 재사용하지 않았다.
flat 대조군을 이 파일에서 독립 구현했다 (그래서 flat coverage 가 11 이 아니라 14 로 다르다 —
predicate lexicon 이 독립이기 때문이며, 이 차이 자체는 결론에 영향을 주지 않는다.
세 구조가 **동일한 atomic predicate 집합**을 공유하므로 구조 간 비교는 내부적으로 정합한다).

---

## 4. 분석단위 · N · missing N

- **분석단위**: web target (`wtg`), `in_mart==1`. 1 행 = 1 target.
- **N = 56**, `n_expected = 59`, **missing N = 3** (DOM 미수집 3건 — 삼성 1st-party 앱 안내
  페이지 계열. 결측은 MCAR 이 아니다).
- prior class 분모: `ITEM_DETAIL` 26 · `FINANCIAL_ACTION_ENTRY` 10 · `UTILITY_ENTRY` 5 ·
  `COMMUNICATION_ENTRY` 4 · `PLACE_LOOKUP` 4 · `QUERY` 4 · `CONTENT_OPEN` 3.
  **5개 class 가 n≤5** 다. per-class 수치는 Wilson 95% CI 와 함께만 읽어야 한다.

---

## 5. Level 1 정의와 SSOT §5 근거 — assertion type: `DEFINITION`

Level 1 은 **데이터를 보기 전에** SSOT §5 각 branch 의 **Endpoint 절**에서 유도했다.

| SSOT §5 Endpoint 원문 | branch | 유도된 primitive |
|---|---|---|
| "질의가 실제 제출되어 결과 state로 전환된 순간" | Q | `L1_QUERY_SUBMISSION` |
| "place query submitted" | P | `L1_QUERY_SUBMISSION` |
| "article body open" / "main media playback start" | C | `L1_OBJECT_OPENING` |
| "거래 대상 한 건의 상세면에 들어가 핵심정보를 보는" | I | `L1_OBJECT_OPENING` |
| "place detail opened" | P | `L1_OBJECT_OPENING` |
| "post/thread open" | M | `L1_OBJECT_OPENING` |
| "compose area entry" / "actual login gate" | M | `L1_AUTH_ACTION_ENTRY` |
| "finance function surface open" / "LOGIN/IDENTITY gate reached" | F | `L1_AUTH_ACTION_ENTRY` |
| "function surface 가 열리고 primary control 이 present/actionable" | U | `L1_UTILITY_TOOL_ENTRY` |

### Level 1 → Level 2 member 집합

```
L1_QUERY_SUBMISSION    → QUERY, PLACE_LOOKUP
L1_OBJECT_OPENING      → CONTENT_OPEN, ITEM_DETAIL, PLACE_LOOKUP, COMMUNICATION_ENTRY
L1_AUTH_ACTION_ENTRY   → FINANCIAL_ACTION_ENTRY, COMMUNICATION_ENTRY
L1_UTILITY_TOOL_ENTRY  → UTILITY_ENTRY
```

### 정의에서 바로 따라오는 구조적 사실 (결과가 아니다)

**`PLACE_LOOKUP` 은 primitive 2 개에, `COMMUNICATION_ENTRY` 도 primitive 2 개에 속한다.**
→ **SSOT §5 branch tree 는 interaction primitive 위의 분할(partition)이 아니다.**
이것은 실험 결과가 아니라 SSOT 원문에서 읽히는 정의상 사실이며, §11 에서 이것이
계층 구조에 어떤 대가를 물리는지 측정한다.

---

## 6. 방법 — 규칙 전문

### 6.1 공통 원칙: 세 구조는 동일한 atomic predicate 를 공유한다

구조 비교가 lexicon 차이가 아니라 **구조 차이**로 귀속되도록, S1/S2/S3 는 완전히 같은
predicate 집합에서 출발한다. lexicon 과 임계는 **실행 전에 선언**했고 결과를 본 뒤
수정하지 않았다. 전체 정규식·lexicon 은 `tools/rf2_d_hierarchical.py` 상단 `LEX` 와
MLflow artifact `hierarchy_definition.txt` 에 그대로 있다.

### 6.2 Stage 0 (SSOT §2)

| rule | 조건 | leaf |
|---|---|---|
| `EMPTY` | `dom_body_empty==1` | `S0_UNDETERMINED` |
| `ERROR_PAGE` | title/headings 가 error lexicon 매치 | `S0_UNDETERMINED` |

### 6.3 Stage 2 atomic predicate (SSOT §4 feature family 그대로), 56건 중 발화 수

| predicate | 발화 | predicate | 발화 |
|---|---:|---|---:|
| `SEARCH_INPUT` | 25 | `THREAD_LIST` | 5 |
| `SEARCH_SUBMIT` | 22 | `COMPOSE_CTRL` | 1 |
| `CONTENT_CARDS` | 10 | `LOGIN_GATE` | 3 |
| `ARTICLE` | 13 | `FIN_CTRL` | 5 |
| `MEDIA_CTRL` | 15 | `FIN_HEAD` | 11 |
| `ITEM_CARDS` | 20 | `TOOL_SURFACE` | 13 |
| `PRICE` | 5 | `TOOL_PRIMARY` | 30 |
| `TXN_CTRL` | 21 | `EMPTY` | 4 |
| `PLACE_CTRL` | 14 | `ERROR_PAGE` | 2 |
| `PLACE_CARDS` | 8 | `PLACE_DETAIL` | 1 |

`PRICE` 가 56건 중 5건에서만 발화한 것이 이 데이터의 핵심 제약이다. prior 상 `ITEM_DETAIL`
이 26건인데 landing snapshot 에 가격 패턴이 거의 없다 — landing 은 상품 목록이 아니라
브랜드 페이지인 경우가 많다.

### 6.4 endpoint 강등 — assertion type: `DEFINITION`

SSOT 의 endpoint 는 **상태 전이**("전환된 순간", "open", "opened", "reached")다. 이 실험의
입력은 **정적 landing snapshot 1 장**이라 전이를 관측할 수 없다. 따라서 모든 branch/primitive
의 E 를 **endpoint-enabling control 의 존재**로 강등했다. 이 강등은 coverage 를 **낙관적으로**
올리는 방향이다. 세 구조에 동일하게 적용했다.

### 6.5 S1 flat (SSOT §5 + §6)

branch b 가 강후보 ⟺ `R_b ∧ E_b`.

| branch | R (region) | E (endpoint-enabling) |
|---|---|---|
| Q QUERY | `SEARCH_INPUT` | `SEARCH_SUBMIT` |
| C CONTENT_OPEN | `CONTENT_CARDS` | `ARTICLE ∨ MEDIA_CTRL` |
| I ITEM_DETAIL | `ITEM_CARDS` | `PRICE ∧ TXN_CTRL` |
| P PLACE_LOOKUP | `PLACE_CTRL ∨ PLACE_CARDS` | `PLACE_DETAIL ∨ (PLACE_CTRL ∧ SEARCH_SUBMIT)` |
| M COMMUNICATION_ENTRY | `THREAD_LIST ∨ COMPOSE_CTRL` | `COMPOSE_CTRL ∨ THREAD_LIST ∨ LOGIN_GATE` |
| F FINANCIAL_ACTION_ENTRY | `FIN_CTRL` | `LOGIN_GATE ∨ FIN_HEAD` |
| U UTILITY_ENTRY | `TOOL_SURFACE` | `TOOL_PRIMARY` |

resolver (SSOT §6): 강후보 1개 → `MAPPED`, 2개 이상 → `ABSTAIN_MULTI_BRANCH`,
0개 → `ABSTAIN_NO_BRANCH`. **force map 0건.**

### 6.6 S2 hierarchical rule

**Level 1** — primitive 수준 R/E (member branch 들의 합집합, branch 간 evidence 혼합 허용).
이것이 계층 구조의 실체다: branch 단위가 아니라 primitive 단위로 region/endpoint 를 본다.

| primitive | R | E |
|---|---|---|
| `L1_QUERY_SUBMISSION` | `SEARCH_INPUT ∨ PLACE_CTRL ∨ PLACE_CARDS` | `SEARCH_SUBMIT` |
| `L1_OBJECT_OPENING` | `CONTENT_CARDS ∨ ITEM_CARDS ∨ PLACE_CARDS ∨ THREAD_LIST` | `ARTICLE ∨ MEDIA_CTRL ∨ (PRICE ∧ TXN_CTRL) ∨ PLACE_DETAIL ∨ THREAD_LIST` |
| `L1_AUTH_ACTION_ENTRY` | `FIN_CTRL ∨ COMPOSE_CTRL` | `LOGIN_GATE ∨ FIN_HEAD ∨ COMPOSE_CTRL` |
| `L1_UTILITY_TOOL_ENTRY` | `TOOL_SURFACE` | `TOOL_PRIMARY` |

강 primitive 1개 → Level 2 로. 2개 이상 → `ABSTAIN_L1_MULTI`. 0개 → `ABSTAIN_L1_NONE`.

**Level 2** — primitive 안에서만 archetype 판별. 1개 발화 → `MAPPED`, 2개 이상 →
`ABSTAIN_L2_MULTI`, 0개 → `ABSTAIN_L2_NONE`.

| primitive | 판별식 |
|---|---|
| `L1_QUERY_SUBMISSION` | `QUERY = SEARCH_INPUT ∧ ¬(PLACE_CTRL ∨ PLACE_CARDS)` · `PLACE_LOOKUP = PLACE_CTRL ∨ PLACE_CARDS` |
| `L1_OBJECT_OPENING` | `ITEM_DETAIL = PRICE ∧ TXN_CTRL ∧ ITEM_CARDS` · `PLACE_LOOKUP = PLACE_CARDS ∨ (PLACE_CTRL ∧ PLACE_DETAIL)` · `COMMUNICATION_ENTRY = THREAD_LIST ∨ COMPOSE_CTRL` · `CONTENT_OPEN = ARTICLE ∨ (CONTENT_CARDS ∧ MEDIA_CTRL)` |
| `L1_AUTH_ACTION_ENTRY` | `FINANCIAL_ACTION_ENTRY = FIN_CTRL ∧ (LOGIN_GATE ∨ FIN_HEAD)` · `COMMUNICATION_ENTRY = COMPOSE_CTRL ∨ THREAD_LIST` |
| `L1_UTILITY_TOOL_ENTRY` | `UTILITY_ENTRY = True` (member 1개) |

### 6.7 S2s hier_strict (민감도)

Level 1 을 **flat 강후보 집합의 단순 조대화**로 정의: 강 primitive = { primitive(b) : b 가 flat 강후보 }.
나머지는 S2 와 동일. 이 변형은 "계층이 flat 을 잃지 않고 감싸는가"를 직접 검사한다.

### 6.8 S3 hierarchical + semantic Level 2

Level 1 은 S2 와 **동일한 rule**. Level 2 만 텍스트 유사도 순위로 대체.

- 모델 `BAAI/bge-m3` (로컬, `HF_HUB_OFFLINE=1`), dim 1024, max_seq 8192,
  문서 subword 중앙값 498.5 / 최대 2732 → **truncate 0건**.
- 문서 표현 = `D_TEXT_CORPUS_v2.csv` 의 `text_blob` (SSOT §7 Text representation 필드 묶음).
- prototype = **SSOT §5 각 branch 의 질문 문장** (`prototypes.json`).
- Level 2 = primitive member 로 후보를 제한한 뒤 cosine argmax. **추가 abstention 없음**
  (그래서 전체 coverage = Level 1 coverage). 이 설계는 "L2 가 얼마나 비싼가"를 분리해서 본다.
- S3m = 사전 선언한 margin 임계 `0.02` 를 얹은 민감도. **calibration split 이 없으므로 이
  임계는 운영 threshold 가 아니다** (SSOT §7 "임의 숫자를 영구 기준으로 선언하지 않는다").

---

## 7. 세 구조 비교 — 동일 최종 7-way output 기준 (n=56)

| 구조 | mapped | coverage (Wilson 95%) | abstention | prior_agreement \| coverage (Wilson 95%) | prior_agreement overall |
|---|---:|---|---:|---|---|
| **S1 flat rule** | 14 | **0.250** [0.155, 0.376] | 0.750 | **5/14 = 0.357** [0.163, 0.613] | 5/56 = 0.089 |
| **S2 hier rule** | 16 | **0.286** [0.183, 0.415] | 0.714 | **5/16 = 0.3125** [0.142, 0.556] | 5/56 = 0.089 |
| S2s hier strict | 11 | 0.196 [0.113, 0.318] | 0.804 | 4/11 = 0.364 [0.152, 0.646] | 4/56 = 0.071 |
| **S3 hier + semantic** | 16 | **0.286** [0.183, 0.415] | 0.714 | **6/16 = 0.375** [0.185, 0.614] | 6/56 = 0.107 |
| S3m hier + sem margin.02 | 9 | 0.161 [0.087, 0.278] | 0.839 | 5/9 = 0.556 [0.267, 0.811] | 5/56 = 0.089 |

**모든 CI 가 서로 완전히 겹친다.** 어떤 구조도 다른 구조와 구별되지 않는다.

### 7.1 Level 별 분해 — 조건부 분모를 명시한다

| 지표 | 분모 | 값 |
|---|---|---|
| Level 1 coverage | **56 (전체 target)** | 16/56 = **0.286** [0.183, 0.415] |
| Level 1 abstention | 56 | 40/56 = 0.714 (`L1_MULTI` 15 · `L1_NONE` 19 · `S0` 6) |
| Level 2 coverage (S2 rule) | **16 (= Level 1 이 유일 primitive 를 확정한 target)** | 16/16 = **1.000** [0.806, 1.000] |
| Level 2 abstention (S2 rule) | 16 | 0/16 = 0.000 |
| Level 2 prior_agreement (S2 rule) | **16 (Level 2 가 매핑한 건)** | 5/16 = 0.3125 [0.142, 0.556] |
| Level 2 coverage (S3 semantic) | 16 | 16/16 = 1.000 (설계상 abstain 없음) |
| Level 2 prior_agreement (S3 semantic) | 16 | 6/16 = 0.375 [0.185, 0.614] |
| Level 2 coverage (S3m margin .02) | 16 | 9/16 = 0.5625 [0.332, 0.769] |
| Level 2 prior_agreement (S3m) | 9 | 5/9 = 0.556 [0.267, 0.811] |
| 전체 coverage (S2) | 56 | 16/56 = 0.286 |
| 전체 prior_agreement (S2) | 56 | 5/56 = 0.089 [0.039, 0.192] |

> **Level 2 조건부 coverage 1.000 을 "Level 2 는 쉽다"로 읽으면 안 된다.** 이것은 판별식을
> 상호배타적으로 선언한 **정의상 산물**이다. `L1_QUERY_SUBMISSION` 의 두 판별식은
> (`검색표면 ∧ ¬장소`, `장소`) 로 상호배타이므로 L1 이 통과하면 반드시 정확히 하나가 발화한다.
> `L1_UTILITY_TOOL_ENTRY` 는 member 가 1개라 항상 참이다. 즉 Level 2 는 **abstain 하지
> 않도록 정의된 구간을 포함**하며, 그 대가가 prior_agreement 0.3125 로 나타난다.

---

## 8. 어디서 정보를 잃는가

`figures/RF2_D_information_loss.png`

| 손실 지점 | S1 flat | S2 hier |
|---|---:|---:|
| Stage 0 `S0_UNDETERMINED` (빈 body 4 · error page 2) | 6 | 6 |
| 강후보 0개 (`ABSTAIN_NO_BRANCH` / `ABSTAIN_L1_NONE`) | 21 | 19 |
| 강후보 2개 이상 (`ABSTAIN_MULTI_BRANCH` / `ABSTAIN_L1_MULTI`) | 15 | 15 |
| Level 2 에서 손실 | — | **0** |
| `MAPPED` | 14 | 16 |

**병목은 Level 1 이다. Level 2 에서는 한 건도 잃지 않는다.**
즉 계층을 도입해도 손실 구조가 바뀌지 않는다 — flat 의 "강후보 없음 21 / 다중후보 15" 가
계층에서 "L1 없음 19 / L1 다중 15" 로 거의 그대로 이동한다.

### 8.1 Level 1 다중후보의 내역 (15건)

| 충돌한 primitive 조합 | 건수 |
|---|---:|
| `OBJECT_OPENING` + `QUERY_SUBMISSION` | **7** |
| `QUERY_SUBMISSION` + `UTILITY_TOOL_ENTRY` | 2 |
| `OBJECT_OPENING` + `QUERY_SUBMISSION` + `UTILITY_TOOL_ENTRY` | 2 |
| `AUTH_ACTION_ENTRY` + `QUERY_SUBMISSION` | 1 |
| `OBJECT_OPENING` + `UTILITY_TOOL_ENTRY` | 1 |
| `AUTH_ACTION_ENTRY` + `UTILITY_TOOL_ENTRY` | 1 |
| `AUTH_ACTION_ENTRY` + `QUERY_SUBMISSION` + `UTILITY_TOOL_ENTRY` | 1 |

최빈 충돌은 **"검색창 + 반복 카드 목록"** 으로, SSOT §6 이 명시적으로 든 바로 그 사례
("실제 페이지에는 검색창과 상품목록이 동시에 있을 수 있다")다.
**primitive 층은 이 모호성을 없애지 못하고 그대로 재생산한다.**

---

## 9. per-class recall · precision + support + Wilson 95% CI

`figures/RF2_D_per_class.png`. `prior` 는 gold 가 아니므로 아래는 accuracy 가 아니라
**prior 대비 recall/precision** 이다.

### S1 flat rule (mapped 14)

| archetype | support (prior) | n_predicted | tp | recall vs prior [95%] | precision vs prior [95%] |
|---|---:|---:|---:|---|---|
| QUERY | 4 | 7 | 1 | 0.250 [0.046, 0.699] | 0.143 [0.026, 0.513] |
| CONTENT_OPEN | 3 | 0 | 0 | 0.000 [0.000, 0.561] | 정의 불가 (n_pred=0) |
| ITEM_DETAIL | 26 | 1 | 1 | 0.038 [0.007, 0.189] | 1.000 [0.207, 1.000] |
| PLACE_LOOKUP | 4 | 0 | 0 | 0.000 [0.000, 0.490] | 정의 불가 |
| COMMUNICATION_ENTRY | 4 | 3 | 1 | 0.250 [0.046, 0.699] | 0.333 [0.061, 0.792] |
| FINANCIAL_ACTION_ENTRY | 10 | 2 | 2 | 0.200 [0.057, 0.510] | 1.000 [0.342, 1.000] |
| UTILITY_ENTRY | 5 | 1 | 0 | 0.000 [0.000, 0.434] | 0.000 [0.000, 0.793] |

### S2 hier rule (mapped 16)

| archetype | support | n_predicted | tp | recall vs prior [95%] | precision vs prior [95%] |
|---|---:|---:|---:|---|---|
| QUERY | 4 | 7 | 1 | 0.250 [0.046, 0.699] | 0.143 [0.026, 0.513] |
| CONTENT_OPEN | 3 | 2 | 0 | 0.000 [0.000, 0.561] | 0.000 [0.000, 0.658] |
| ITEM_DETAIL | 26 | 1 | 1 | 0.038 [0.007, 0.189] | 1.000 [0.207, 1.000] |
| PLACE_LOOKUP | 4 | 0 | 0 | 0.000 [0.000, 0.490] | 정의 불가 |
| COMMUNICATION_ENTRY | 4 | 3 | 1 | 0.250 [0.046, 0.699] | 0.333 [0.061, 0.792] |
| FINANCIAL_ACTION_ENTRY | 10 | 2 | 2 | 0.200 [0.057, 0.510] | 1.000 [0.342, 1.000] |
| UTILITY_ENTRY | 5 | 1 | 0 | 0.000 [0.000, 0.434] | 0.000 [0.000, 0.793] |

### S3 hier + semantic (mapped 16)

| archetype | support | n_predicted | tp | recall vs prior [95%] | precision vs prior [95%] |
|---|---:|---:|---:|---|---|
| QUERY | 4 | 7 | 1 | 0.250 [0.046, 0.699] | 0.143 [0.026, 0.513] |
| CONTENT_OPEN | 3 | 3 | 0 | 0.000 [0.000, 0.561] | 0.000 [0.000, 0.561] |
| ITEM_DETAIL | 26 | 2 | 2 | 0.077 [0.021, 0.241] | 1.000 [0.342, 1.000] |
| PLACE_LOOKUP | 4 | 0 | 0 | 0.000 [0.000, 0.490] | 정의 불가 |
| COMMUNICATION_ENTRY | 4 | 1 | 1 | 0.250 [0.046, 0.699] | 1.000 [0.207, 1.000] |
| FINANCIAL_ACTION_ENTRY | 10 | 2 | 2 | 0.200 [0.057, 0.510] | 1.000 [0.342, 1.000] |
| UTILITY_ENTRY | 5 | 1 | 0 | 0.000 [0.000, 0.434] | 0.000 [0.000, 0.793] |

세 구조 모두 **`PLACE_LOOKUP` 을 단 한 건도 매핑하지 못한다** (`PLACE_DETAIL` predicate 이
56건 중 1건만 발화). `CONTENT_OPEN` 은 계층에서 오히려 **과탐**이 생긴다(n_pred 0→2→3, tp 0).

---

## 10. "계층이 좋아 보이는 것이 단지 Level 1 이 class 를 뭉쳐 문제를 쉽게 만든 것 아닌가"에 대한 답

이 질문에 세 가지 방식으로 답한다. **결론: 계층이 좋아 보이지도 않았고, 좋아 보였다면
그건 문제를 쉽게 만든 것이었을 것이다.**

### (a) Level 1 성능을 7-way 성능과 직접 비교하지 않았다

Level 1 은 4-way 이고(게다가 2 archetype 은 primitive 2개에 중복 소속) 최종은 7-way 다.
분모와 class 수가 달라 직접 비교하지 않는다. 모든 구조 비교는 **동일 최종 7-way output
기준**(§7)으로만 했다.

### (b) Level 1 을 다수결 기준선과 비교했다 — Level 1 은 기준선보다 **낮다**

| 지표 | 값 (Wilson 95%) |
|---|---|
| L1 이 확정한 16건에서의 prior primitive 일치 | **9/16 = 0.5625** [0.335, 0.766] |
| 같은 16건에서 "항상 `L1_OBJECT_OPENING`" 다수결 기준선 | **13/16 = 0.8125** [0.570, 0.934] |
| 전체 56건에서의 같은 다수결 기준선 | 37/56 = 0.661 [0.530, 0.771] |

`prior` 가 primitive 2개에 걸친 `PLACE_LOOKUP`·`COMMUNICATION_ENTRY` 는 **둘 중 어느 쪽이든
일치로 세는 관대한 규칙**을 썼는데도 그렇다. Level 1 은 "쉽게 만든 문제"조차 못 푼다.

### (c) Level 1 의 후보 제약이 정보를 더하는지 짝지어 검정했다 — **뺀다**

동일한 Level-1 통과 16건에서:

| | prior 일치 |
|---|---:|
| 계층 없이 7-way semantic argmax | **9/16** |
| Level 1 이 후보를 좁힌 뒤 argmax | **6/16** |
| 불일치 (제약 없을 때만 맞음) | 4 |
| 불일치 (제약했을 때만 맞음) | 1 |
| McNemar exact p | 0.375 |

방향은 **음**(계층이 손해)이고, n=16 이라 유의하지는 않다. 최소한 "계층이 후보를 좁혀
정보를 더한다"는 주장은 **지지되지 않는다**.

### (d) 참고 대조 — 규칙 자체가 병목이다

계층 없이 7-way semantic argmax 를 **전부 강제 매핑**하면 prior 일치 **29/56 = 0.518**
(abstention 0). 어떤 규칙 구조도 overall 6/56 = 0.107 를 넘지 못한다. 이 격차는
"flat 이냐 계층이냐"보다 훨씬 크다. 다만 **강제 매핑은 abstention 정책이 다르므로 §7 표와
같은 줄에 놓고 비교할 수 없다.** 이것은 §14 의 후속 질문 RQ-d 로 넘긴다.

---

## 11. 반례 · 개별 사례

### 11.1 계층이 flat 을 잃지 않고 감싸는가 — S2 는 감싸지만 S2s 는 잃는다

| 비교 | 건수 |
|---|---:|
| 두 구조가 같이 매핑하고 **예측이 동일** | **14** |
| 두 구조가 같이 매핑했는데 예측이 다름 | **0** |
| flat 만 매핑 | **0** |
| 계층(S2)만 매핑 | **2** — 둘 다 prior 불일치 |

계층이 추가로 딴 2건: GS25(prior `ITEM_DETAIL` → `CONTENT_OPEN`),
이마트(prior `ITEM_DETAIL` → `CONTENT_OPEN`). **coverage +2, agreement +0.**
McNemar 짝 불일치 b=0, c=0 — 두 구조의 prior 일치 여부가 target 단위로 **완전히 같다.**

**S2s(strict) 는 flat 이 확정하던 3건을 잃는다:**

| target | prior | flat 결과 | strict 결과 | 원인 |
|---|---|---|---|---|
| 밴드 | `COMMUNICATION_ENTRY` | `COMMUNICATION_ENTRY` (일치) | `ABSTAIN_L1_MULTI` | `COMMUNICATION_ENTRY` 가 primitive 2개 소속 |
| 신세계백화점 | `ITEM_DETAIL` | `COMMUNICATION_ENTRY` | `ABSTAIN_L1_MULTI` | 동일 |
| CU | `ITEM_DETAIL` | `COMMUNICATION_ENTRY` | `ABSTAIN_L1_MULTI` | 동일 |

**이것이 §5 에서 예고한 구조적 대가다.** flat 이 **유일 강후보**를 확정했는데도, 그 archetype
이 primitive 2개에 걸쳐 있어서 Level 1 이 다중후보가 되어 abstain 한다. 계층을 강제하면
SSOT §5 가 분할이 아니라는 사실이 **coverage 손실로 청구된다.**

### 11.2 계층이 무엇을 잘못 흡수하는가 — 가장 중요한 반례

Level 1 이 확정한 16건 중 **7건이 `L1_QUERY_SUBMISSION`** 이고, 그 중 prior 가 `QUERY` 인
것은 **1건뿐**이다(Google). 나머지는:

| target | prior | L1 | 최종 |
|---|---|---|---|
| 코스트코 | `ITEM_DETAIL` | `QUERY_SUBMISSION` | `QUERY` |
| CJ온스타일 | `ITEM_DETAIL` | `QUERY_SUBMISSION` | `QUERY` |
| 메가커피 | `ITEM_DETAIL` | `QUERY_SUBMISSION` | `QUERY` |
| 11번가 | `ITEM_DETAIL` | `QUERY_SUBMISSION` | `QUERY` |
| Netflix | `CONTENT_OPEN` | `QUERY_SUBMISSION` | `QUERY` |
| YouTube | `CONTENT_OPEN` | `QUERY_SUBMISSION` | `QUERY` |

**landing snapshot 에서 가장 뚜렷하게 완결된 interaction affordance 가 검색창이기 때문**이다.
쇼핑·콘텐츠 서비스의 첫 화면은 상품/콘텐츠 카드를 다 갖추지 못한 브랜드 페이지인 반면,
검색 input + submit 은 거의 항상 있다. 즉 Level 1 은 **"이 서비스의 대표기능이 무엇인가"가
아니라 "이 랜딩 페이지가 지금 무엇을 할 수 있게 해주는가"를 측정한다.** 이 둘은 체계적으로
다르며, primitive 층을 넣는다고 좁혀지지 않는다.

### 11.3 semantic Level 2 가 바꾼 3건

| target | prior | rule L2 | semantic L2 | 판정 |
|---|---|---|---|---|
| 신세계백화점 | `ITEM_DETAIL` | `COMMUNICATION_ENTRY` | `ITEM_DETAIL` | semantic 이 고침 |
| CU | `ITEM_DETAIL` | `COMMUNICATION_ENTRY` | `ITEM_DETAIL` | semantic 이 고침 |
| NS홈쇼핑 | `ITEM_DETAIL` | `ITEM_DETAIL` | `CONTENT_OPEN` | semantic 이 망침 |

순 +1 (5/16 → 6/16). n=16 에서 순 1건은 **noise 와 구별되지 않는다.**

### 11.4 Stage 0 로 빠진 6건은 무작위가 아니다

빈 body 4건 중 3건이 은행(신한 SOL뱅크 · NH스마트뱅킹 · NH콕뱅크)이다. error page 2건은
카카오톡(Page not found)·롯데마트. **결측·파손이 `FINANCIAL_ACTION_ENTRY` 도메인에 몰려 있다.**
`FINANCIAL_ACTION_ENTRY` 10건 중 3건이 Stage 0 에서 빠졌다.

---

## 12. Verdict

**`H-RF2-D-HIERARCHY` = `NOT_SUPPORTED`**

interaction primitive 를 먼저 구분하는 계층 구조가 flat 7-way 보다 관측 evidence 와 더 잘
맞는다는 근거가 이 데이터에 없다.

- coverage 는 14/56 → 16/56 으로 올랐지만 CI 가 거의 완전히 겹치고, 늘어난 2건은 둘 다
  prior 와 불일치해 **prior_agreement 는 5/56 → 5/56 으로 변하지 않았다.**
- 두 구조가 같이 매핑한 14건에서 **예측이 100% 동일**하다. 같은 coverage 구간에서 계층은
  정보를 전혀 더하지 않는다.
- Level 1 은 쉽지 않다: 56건 중 16건만 닫히고(0.286), 닫힌 건의 prior primitive 일치
  9/16=0.5625 는 다수결 기준선 13/16=0.8125 **보다 낮다.**
- Level 1 의 후보 제약은 semantic arm 에서 동일 16건 기준 9/16 → 6/16 으로 **낮췄다.**
- 계층을 엄격히 강제하면(S2s) SSOT §5 가 primitive 분할이 아니라는 이유만으로
  flat 이 확정하던 3건을 잃는다.

이 결과는 **`RECOMMENDED_EXPERIMENTAL_CANDIDATE` 를 하나도 배출하지 않는다.** 세 구조 중
어느 것도 후속 구현 후보로 올릴 근거가 없다.

---

## 13. Limitation

1. **`prior_archetype` 은 gold 가 아니다.** 이 데이터에서 `prior_archetype` 은
   `prior_business_domain` 과 1:1 로 붙어 있다(SHOPPING_COMMERCE↔ITEM_DETAIL 등).
   따라서 `prior_agreement` 는 "규칙이 도메인 prior 를 재현하는가"에 가깝고 "옳은가"가 아니다.
   `prior_agreement` 가 낮은 것이 규칙이 틀렸다는 뜻도, prior 가 옳다는 뜻도 아니다.
2. **endpoint 강등(§6.4)** — 상태전이를 관측 못 해 모든 E 를 control 존재로 강등했다.
   coverage 를 낙관적으로 올리는 강등이며, 그럼에도 coverage 가 0.286 에 그친다.
3. **n=56, 5개 class 가 n≤5.** per-class Wilson CI 가 사실상 [0,1] 폭이다. §7 의 어떤 구조
   비교도 통계적으로 구별되지 않는다. 이 실험은 **가설을 기각하지 못한 것**이지
   "계층이 나쁘다"를 확증한 것이 아니다.
4. **Level 1 primitive 경계는 이 실험의 `DEFINITION`** 이다. SSOT §5 endpoint 절에서
   유도했지만 독립 검증을 받지 않았다. 다른 primitive 분할이면 결론이 달라질 수 있다.
   (그런 분할을 시도하려면 **새 hypothesis_id + 새 run** 이어야 한다.)
5. **semantic L2 는 calibration 이 없다.** prototype 과 margin 0.02 는 사전 선언일 뿐
   운영 threshold 가 아니다.
6. **missing N=3 은 MCAR 이 아니다** (삼성 1st-party 계열), Stage 0 손실 6건도 금융 도메인에
   편중돼 있다(§11.4). 따라서 §7 수치는 56건 population 을 대표한다고 보기 어렵다.
7. flat 대조군을 독립 구현했으므로 이 문서의 flat coverage 14 는 선행 `RF001_A` 의 11 과
   다르다. **선행 판정을 반박하는 것이 아니다** — lexicon 이 다르면 flat 수치도 달라진다는
   것 자체가 규칙 매핑의 민감도를 보여준다.

---

## 14. Production implication

- **SSOT 01 §5 의 flat branch tree 를 계층 구조로 바꿀 근거가 없다. SSOT 를 바꾸지 말 것.**
- 병목은 **구조가 아니라 evidence** 다. landing snapshot 은 representative function 이 아니라
  "랜딩 페이지가 지금 제공하는 affordance" 만 담고 있고, 둘은 체계적으로 다르다(§11.2).
- **SSOT §5 branch tree 는 interaction primitive 위의 분할이 아니다** — `PLACE_LOOKUP` 과
  `COMMUNICATION_ENTRY` 가 primitive 2개에 걸쳐 있다. 이 사실은 계층 도입을 검토할 때
  반드시 먼저 해소돼야 하며, 해소하려면 7 archetype 정의를 손대야 한다 → **A 결정 사항이고
  D 는 제안만 한다.**
- SSOT §10 release safety gate 대비: 어떤 구조도 `holdout coverage >= 0.75`,
  `archetype agreement >= 0.85` 근처에도 못 간다. **detector readiness 미달**이며,
  full REAL_TARGET 을 막고 pilot subset 만 허용하는 조건에 해당한다.
  (단 이 실험은 holdout 이 아니라 `split=none` 이다. holdout 판정 권한은 C 에 있다.)

---

## 15. 추가 연구질문

- **RQ-a**: representative function 은 landing snapshot 이 아니라 **1-hop 전이 후** 상태에서만
  관측 가능한가? endpoint 강등(§6.4)을 풀 수 있는 최소 수집 단위는 무엇인가?
- **RQ-b**: Level 1 이 `QUERY_SUBMISSION` 으로 흡수하는 현상(§11.2)은 "검색창 우선"이라는
  **랜딩 디자인 관행의 측정**인가, **매핑 규칙의 결함**인가? 두 가설을 가르는 관측은 무엇인가?
- **RQ-c**: SSOT §5 를 primitive 분할이 되도록 재정의하면(예: `PLACE_LOOKUP` 을
  place-query / place-detail 로 분리) §11.1 의 계층 손실이 사라지는가?
  **7 archetype 변경이므로 A 결정 사항**이며 D 는 제안만 한다.
- **RQ-d**: 계층 없는 7-way semantic argmax 가 강제매핑 기준 29/56 을 얻는데 규칙이 5/56 에
  그치는 차이는 "규칙이 abstain 하기 때문"인가 "규칙 predicate 이 틀렸기 때문"인가?
  동일 abstention 정책 아래에서 다시 재보아야 한다.
- **RQ-e**: `PRICE` predicate 이 56건 중 5건만 발화하는데 prior `ITEM_DETAIL` 은 26건이다.
  이 격차는 수집 시점 문제(랜딩=브랜드 페이지)인가 predicate 문제인가?

---

## 16. 재현

```bash
/home/sieg/projects-wsl/ProjectFinal/.venv/bin/python \
  research/landing_accessibility/research_d/tools/rf2_d_hierarchical.py
```

결정론적이다(임베딩 인코딩만 `torch.manual_seed(20260827)`; bge-m3 추론은 결정론적).
MLflow 기록을 건너뛰려면 `--no-mlflow`.
