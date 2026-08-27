# D-RF-001-B — TF-IDF + linear baseline: archetype **prior** 재현 실험

| | |
|---|---|
| child_id | `D-RF-001-B` |
| rq_id | `RQ-D-RF-001` (parent run `2bf780a9efca4562bdf63a7c165514cc`) |
| plane / authority | D / `NON_CANONICAL` (advisory 아님, 채택 아님) |
| claim_kind | `ANALYSIS` |
| **VERDICT (H-RF001-B-TFIDF)** | **`NOT_SUPPORTED`** |
| VERDICT (H-B-null) | `SUPPORTED` — baseline 과 구분되지 않는다 |
| VERDICT (H-B-leak) | `SUPPORTED` — 분리되는 부분은 브랜드/아티팩트 암기다 |
| seed | `20260827` (전 구간 고정, Restart→Run All 재현 가능) |
| 산출 | `results/RF001_B_tfidf.json`, `figures/RF001_B_*.png` |

---

## 0. 이 문서의 모든 수치가 무엇이 **아닌지** 먼저

> **target 은 gold label 이 아니다.** 예측 대상은 `prior_archetype` — 관측표에 기록된
> **business-domain 유래 prior** 다. 따라서 여기서 보고하는 macro F1 은 **accuracy 가 아니라
> `prior_agreement`** 다. 이 실험은 "텍스트가 정답 archetype 을 맞히는가"를 검정하지 않는다.
> "텍스트가 *사전에 배정된 prior* 를 되찾는가"만 검정한다.
>
> 추가로 확인된 구조: 이 표본에서 `prior_archetype` 과 `prior_business_domain` 은
> **완전 1:1** 이다 (7×7 교차표가 대각). 즉 과제의 실체는 "페이지 텍스트로 **업종**을 맞히기"이며,
> archetype 이라는 이름이 주는 '기능 유형' 의미는 이 데이터에서 검정되지 않는다.
> — assertion type: `OBSERVATION`, 분모 56/56.

---

## 1. RQ

**RQ-D-RF-001 (child B)** — 랜딩 페이지에서 추출한 텍스트만으로 7개 archetype prior 를
stratified baseline 보다 유의하게 되찾을 수 있는가? 되찾는다면 그것은 archetype 의
**기능 어휘**인가, 아니면 **서비스명/브랜드 토큰의 암기**인가?

## 2. 가설과 판정

| 가설 | 내용 | 판정 | 근거 |
|---|---|---|---|
| **H-RF001-B-TFIDF** | 텍스트 TF-IDF 만으로 prior 를 stratified baseline 보다 유의하게 되찾는다 | **`NOT_SUPPORTED`** | 사전 선언 primary 의 95% percentile 구간 `[0.089, 0.313]` 이 stratified 평균 `0.155` 를 포함. A~D 16셀 **전부** 포함. permutation p=0.279 |
| **H-B-null** | n=56·7class·min class n=3 에서 선형 TF-IDF 는 baseline 과 구분되지 않는다 | **`SUPPORTED`** | 정당한 text featureset 16셀 중 하나도 p2.5 > 0.155 를 넘지 못함 |
| **H-B-leak** | 잘 맞는 부분은 archetype 신호가 아니라 브랜드 토큰 암기다 | **`SUPPORTED`** | **브랜드 토큰만 남긴 대조군 E 가 20셀 전체 최고점**(0.363). 브랜드 제거 시 minority class recall 붕괴. 추가로 mojibake·CSS 두 개의 아티팩트 채널 발견 |

## 3. 입력 / 분석단위 / N

- 주 입력: `research_d/results/D_TEXT_CORPUS.csv` (SSOTV2 `01_REPRESENTATIVE_FUNCTION_MAPPING_DT_v2.1.md` §7 Text representation 정의로 빌드)
- 분석단위: **target 1개 = 1행** (`in_mart==1`)
- **N = 56 사용 / 59 기대** (`n_expected=59`, `n_observed=56`; dom_found=56/56)
- class 분포 (분모 56):

| class | n | 비율 |
|---|---|---|
| ITEM_DETAIL | 26 | 26/56 = 46.4% |
| FINANCIAL_ACTION_ENTRY | 10 | 10/56 = 17.9% |
| UTILITY_ENTRY | 5 | 5/56 = 8.9% |
| COMMUNICATION_ENTRY | 4 | 4/56 = 7.1% |
| PLACE_LOOKUP | 4 | 4/56 = 7.1% |
| QUERY | 4 | 4/56 = 7.1% |
| CONTENT_OPEN | 3 | 3/56 = 5.4% |

**7 class 중 5개가 n≤5.** 이 5개 class 의 per-class 수치는 뒤에서 "추정 불가에 가깝다"로 표시한다.

## 4. Feature set (사전 선언, 5개 전부 보고)

| id | 정의 | 문서당 토큰 median / min / max | 빈 문서 |
|---|---|---|---|
| `A_blob_full` | `text_blob` 전체 (= url_tokens 포함) | 132 / 5 / 945 | 0/56 |
| `B_title_head_nav` | `title + headings + nav_links` 만 | 29.5 / 0 / 221 | 1/56 |
| `C_blob_no_url` | text_blob 구성 필드 중 **url_tokens 제외** | 125.5 / 0 / 942 | 1/56 |
| `D_deleak` | C 에서 **브랜드/서비스명 문자열 183종 전면 제거** | 118 / 0 / 906 | 1/56 |
| `E_brand_only` | text_blob 에서 **브랜드 토큰만 남김 (leak 상한 대조군)** | **10** / 1 / 84 | 0/56 |

`E_brand_only` 는 모델 후보가 아니라 **누출 상한 대조군**이다. H-RF001-B 판정에서 제외한다.

## 5. 방법 · CV 설계 · 기준선

- vectorizer 2종: **word** `TfidfVectorizer(analyzer="word", ngram_range=(1,2), token_pattern=\b\w{2,}\b, sublinear_tf)`
  / **char_wb** `ngram_range=(2,5), min_df=2, sublinear_tf`
  (한국어라 word tokenizer 가 약할 것으로 보고 char n-gram 을 사전에 포함시켰다 — 결과는 §7 참조)
- 분류기 2종: `LogisticRegression(C=1.0, class_weight="balanced", max_iter=5000)` /
  `LinearSVC(C=1.0, class_weight="balanced")`
- **grid = 5 featureset × 2 analyzer × 2 model = 20셀. 결과를 보기 전에 고정했고 20셀을 전부 보고한다.**
  사전 선언 primary = `A_blob_full.word.logreg`, 사전 선언 de-leak primary = `D_deleak.word.logreg`.
  결과를 본 뒤 hyperparameter·feature 를 수정하지 않았다. (실행 중 고친 것은 두 가지뿐이며 둘 다
  점수와 무관하다: matplotlib boxplot API 인자명, 그리고 **판정 로직의 버그** — 최초 코드가
  "20셀 사후 최댓값"을 H-RF001-B 판정 근거로 썼는데 그 최댓값이 하필 leak 대조군 E 여서
  "브랜드 암기 대조군이 이겼으니 가설이 부분 지지"라는 역설이 나왔다. 판정 근거를
  "사전 선언 primary + E 제외 A~D 사후 최댓값" 으로 교정했다. 점수는 재계산되지 않았다.)
- CV: **`RepeatedStratifiedKFold(n_splits=3, n_repeats=10, random_state=20260827)` → fold 30개**
- 기준선 2종 (동일 CV):

| baseline | macro F1 mean | std | 2.5%~97.5% |
|---|---|---|---|
| `DummyClassifier(strategy="stratified")` — **판정 기준선** | **0.155** | 0.087 | 0.033 ~ 0.341 |
| `DummyClassifier(strategy="most_frequent")` — 병기만 | 0.091 | 0.002 | 0.088 ~ 0.092 |

> **majority 대비 lift 를 헤드라인으로 쓰지 않는 이유**: `most_frequent` 는 7 class 중 6개에서
> recall 이 구조적으로 0 이라 macro F1 이 0.091 에 고정된다. 이 값 대비 lift 는 rigged 비교다.
> 아래 모든 판정은 **stratified(0.155)** 기준이다.

## 6. 판정 규칙 (사전 선언)

fold macro F1 30개의 **95% percentile 하한(p2.5) 이 stratified baseline 평균(0.155)보다 위**이면
"분리된다"로 본다. 사전 선언 primary 와, E 를 제외한 A~D 16셀의 사후 최댓값을 **둘 다** 본다.

## 7. 결과 — 20셀 전부 (분모: 30 fold, n=56)

| featureset | analyzer | model | macro F1 mean | std | 2.5% | 97.5% | stratified 대비 lift | CI 가 baseline 평균 포함 | **분리?** |
|---|---|---|---|---|---|---|---|---|---|
| A_blob_full | word | logreg **(primary)** | 0.215 | 0.080 | 0.089 | 0.313 | +0.060 | 예 | **아니오** |
| A_blob_full | word | linsvc | 0.184 | 0.073 | 0.084 | 0.293 | +0.030 | 예 | 아니오 |
| A_blob_full | char_wb | logreg **(A~D 최고)** | **0.330** | 0.105 | 0.144 | 0.518 | +0.176 | 예 | **아니오** |
| A_blob_full | char_wb | linsvc | 0.291 | 0.114 | 0.101 | 0.476 | +0.137 | 예 | 아니오 |
| B_title_head_nav | word | logreg | 0.213 | 0.070 | 0.090 | 0.320 | +0.058 | 예 | 아니오 |
| B_title_head_nav | word | linsvc | 0.190 | 0.079 | 0.084 | 0.319 | +0.035 | 예 | 아니오 |
| B_title_head_nav | char_wb | logreg | 0.288 | 0.114 | 0.110 | 0.556 | +0.134 | 예 | 아니오 |
| B_title_head_nav | char_wb | linsvc | 0.266 | 0.114 | 0.088 | 0.478 | +0.111 | 예 | 아니오 |
| C_blob_no_url | word | logreg | 0.177 | 0.065 | 0.088 | 0.277 | +0.022 | 예 | 아니오 |
| C_blob_no_url | word | linsvc | 0.166 | 0.062 | 0.084 | 0.267 | +0.012 | 예 | 아니오 |
| C_blob_no_url | char_wb | logreg | 0.305 | 0.112 | 0.144 | 0.518 | +0.150 | 예 | 아니오 |
| C_blob_no_url | char_wb | linsvc | 0.259 | 0.111 | 0.088 | 0.426 | +0.104 | 예 | 아니오 |
| D_deleak | word | logreg **(de-leak primary)** | 0.176 | 0.065 | 0.088 | 0.277 | +0.021 | 예 | 아니오 |
| D_deleak | word | linsvc | 0.165 | 0.059 | 0.084 | 0.267 | +0.010 | 예 | 아니오 |
| D_deleak | char_wb | logreg | 0.243 | 0.094 | 0.131 | 0.462 | +0.088 | 예 | 아니오 |
| D_deleak | char_wb | linsvc | 0.215 | 0.093 | 0.090 | 0.422 | +0.061 | 예 | 아니오 |
| **E_brand_only (대조군)** | word | logreg | 0.328 | 0.119 | 0.149 | 0.555 | +0.173 | 예 | 아니오 |
| **E_brand_only (대조군)** | word | linsvc | 0.334 | 0.110 | **0.170** | 0.545 | +0.179 | **아니오** | **예** |
| **E_brand_only (대조군)** | char_wb | logreg | 0.345 | 0.112 | 0.149 | 0.526 | +0.191 | 예 | 아니오 |
| **E_brand_only (대조군)** | char_wb | linsvc | **0.363** | 0.115 | **0.168** | 0.561 | +0.208 | **아니오** | **예** |

**읽는 법 세 줄**

1. 정당한 텍스트 feature 16셀 중 **stratified baseline 과 분리되는 셀은 0개**다.
2. **20셀 전체 최고점은 문서당 median 10 토큰짜리 브랜드-토큰-온리 대조군**(0.363)이다.
   전체 본문(median 132 토큰)을 다 준 최고 셀(0.330)보다 높다.
3. char n-gram 이 word n-gram 을 모든 featureset 에서 이긴다 (+0.07 ~ +0.13). 한국어에서
   공백 기반 word tokenizer 가 약하다는 사전 예상은 **재현되었다**. 다만 char n-gram 의 이득은
   §9 에서 보듯 상당 부분이 mojibake 바이트 패턴을 잡은 것이다.

### 7.1 fold 분포와 permutation 검정

`figures/RF001_B_fold_distribution.png` — 30개 fold 점수를 baseline 2종 + 20셀에 대해 전부 표시.

| 대상 | permutation p (라벨 200회 셔플, StratifiedKFold(3)) | null mean | null 97.5% | 점수 |
|---|---|---|---|---|
| primary `A_blob_full.word.logreg` | **0.279** | 0.108 | 0.174 | 0.123 |
| de-leak primary `D_deleak.word.logreg` | **0.607** | 0.110 | 0.186 | 0.092 |
| A~D 최고 `A_blob_full.char_wb.logreg` | 0.005 | 0.117 | 0.216 | 0.343 |
| 대조군 `E_brand_only.char_wb.linsvc` | 0.010 | 0.125 | 0.250 | 0.329 |

> **두 검정이 서로 다른 말을 한다 — 숨기지 않고 그대로 쓴다.**
> permutation 검정은 `A_blob_full.char_wb.logreg` 에서 p=0.005 로 "무작위 라벨보다 낫다"고 말하고,
> percentile 판정 규칙은 "stratified baseline 과 구분 못 한다"고 말한다. 셋 다 사실이다:
> (a) 두 null 이 다르다 — permutation null 은 *라벨을 섞은 같은 모델*, percentile 판정은
> *stratified dummy* 이고 후자의 평균(0.155)이 전자의 평균(0.117)보다 높다.
> (b) p=0.005 는 **16셀 중 사후 선택된 셀**이다. 다중비교를 보정하면 임계는 0.05/16 ≈ 0.003 이고
> 0.005 는 이를 통과하지 못한다.
> (c) **사전 선언 primary 의 p 는 0.279 로 아무 증거도 없다.**
> → 사전 선언 규칙(§6)에 따라 **`NOT_SUPPORTED`** 로 판정한다.

## 8. per-class 성능 + Wilson 95% CI (primary `A_blob_full.word.logreg`)

recall/precision/F1 은 10 repeat 별로 계산한 뒤 평균. **Wilson CI 의 n 은 class support(독립 표본 수)** 이며
반복수(×10)로 부풀리지 않았다.

| class | support | recall | precision | F1 | recall Wilson 95% CI | 추정 가능? |
|---|---|---|---|---|---|---|
| ITEM_DETAIL | 26/56 | 0.923 | 0.532 | 0.674 | [0.759, 0.979] | 예 |
| FINANCIAL_ACTION_ENTRY | 10/56 | 0.410 | 0.847 | 0.540 | [0.168, 0.687] | 예 |
| UTILITY_ENTRY | 5/56 | 0.380 | 0.297 | 0.332 | [0.118, 0.769] | **추정 불가에 가까움** |
| COMMUNICATION_ENTRY | 4/56 | **0.000** | 0.000 | 0.000 | [0.000, 0.490] | **추정 불가에 가까움** |
| PLACE_LOOKUP | 4/56 | **0.000** | 0.000 | 0.000 | [0.000, 0.490] | **추정 불가에 가까움** |
| QUERY | 4/56 | **0.000** | 0.000 | 0.000 | [0.000, 0.490] | **추정 불가에 가까움** |
| CONTENT_OPEN | 3/56 | **0.000** | 0.000 | 0.000 | [0.000, 0.562] | **추정 불가에 가까움** |

**n≤5 인 5개 class 의 CI 폭이 0.49~0.56 이다. 이 5개 class 에 대해서는 "성능을 측정했다"고
말할 수 없다.** recall 0 과 recall 0.4 를 이 표본은 구분하지 못한다.

혼동행렬 (`figures/RF001_B_confusion.png`, 10 repeat 평균 count, 행=prior / 열=예측):

| prior \ pred | COMM | CONT | FIN | ITEM | PLACE | QUERY | UTIL |
|---|---|---|---|---|---|---|---|
| COMMUNICATION_ENTRY (4) | 0.0 | 0.0 | 0.0 | **4.0** | 0.0 | 0.0 | 0.0 |
| CONTENT_OPEN (3) | 0.0 | 0.0 | 0.0 | **2.0** | 0.0 | 0.0 | 1.0 |
| FINANCIAL_ACTION_ENTRY (10) | 0.0 | 0.0 | 4.1 | 4.8 | 0.0 | 0.0 | 1.1 |
| ITEM_DETAIL (26) | 0.0 | 0.0 | 0.2 | 24.0 | 0.0 | 0.0 | 1.8 |
| PLACE_LOOKUP (4) | 0.0 | 0.0 | 0.0 | **4.0** | 0.0 | 0.0 | 0.0 |
| QUERY (4) | 0.0 | 0.0 | 0.0 | **4.0** | 0.0 | 0.0 | 0.0 |
| UTILITY_ENTRY (5) | 0.0 | 0.0 | 0.7 | 2.4 | 0.0 | 0.0 | 1.9 |

**7개 class 중 4개(COMMUNICATION_ENTRY / CONTENT_OPEN / PLACE_LOOKUP / QUERY)에 대해
단 한 번도 그 class 를 예측하지 않았다.** `class_weight="balanced"` 를 켰는데도 그렇다.
모델은 사실상 "ITEM_DETAIL 이냐 아니냐" 이진 분류로 붕괴한다.

## 9. **브랜드 leak ablation — 이 실험의 핵심 반증 절차**

### 9.1 정량

| 지표 | 값 | 분모 |
|---|---|---|
| 제거한 브랜드/서비스 문자열 종수 | 183 | — |
| primary(A, 브랜드 포함) macro F1 | 0.215 | 30 fold |
| de-leak primary(D) macro F1 | 0.176 | 30 fold |
| 절대 하락 | −0.039 | — |
| 잔존율 | 0.819 | — |
| **브랜드 토큰만(E) word·logreg** | **0.328** | 30 fold |
| **브랜드 토큰만(E) char_wb·linsvc — 20셀 전체 1위** | **0.363** | 30 fold |
| D(de-leak)가 stratified 와 분리되는가 | **아니오** | — |
| E(brand-only)가 stratified 와 분리되는가 | **예** (2셀) | — |

> **잔존율 0.82 만 보면 "브랜드를 지워도 82% 남으니 leak 아님"으로 오독하기 쉽다.
> 그 해석은 틀렸다.** 남은 0.176 은 애초에 stratified baseline(0.155)과 구분되지 않는 값이다.
> 즉 **지우고 남은 것은 신호가 아니라 baseline 수준**이다. 반대로 브랜드 토큰만 남긴
> 문서(median 10 토큰)는 전체 본문보다 잘 맞힌다. 방향은 명확하다.

per-class 로 보면 더 분명하다 (recall, primary → de-leak primary):

| class | support | A (브랜드 포함) | D (브랜드 제거) | 변화 |
|---|---|---|---|---|
| FINANCIAL_ACTION_ENTRY | 10 | 0.410 | **0.180** | −0.230 |
| ITEM_DETAIL | 26 | 0.923 | 0.923 | 0.000 |
| UTILITY_ENTRY | 5 | 0.380 | 0.380 | 0.000 |
| 나머지 4개 class | 15 | 0.000 | 0.000 | — |

**금융 class 의 재현율 절반 이상이 브랜드/호스트 토큰에서 나왔다.** 반면 ITEM_DETAIL 은
브랜드 없이도 유지되는데, 이는 §9.2 에서 보듯 그 class 만 진짜 기능 어휘를 갖고 있기 때문이다.

### 9.2 상위 계수 토큰 육안 판정 (`A_blob_full`, LogisticRegression 상위 15개, `*`=브랜드 매치)

| class | top-15 브랜드 비율 | 상위 토큰 | **육안 판정** |
|---|---|---|---|
| FINANCIAL_ACTION_ENTRY | **0.73** | `*banking` `*https banking` `농협 개인모바일` `*nhbank` `*nonghyup` `*nhbank html` `html` `개인모바일` `*com nhbank` `*banking nonghyup` `*shinhan` `*bank` `*농협` | **브랜드 어휘 + URL 호스트 문자열.** 기능 어휘(송금/이체/계좌) 없음 |
| CONTENT_OPEN | 0.40 | `*youtube` `ê² youtube` `ê²` `*tiktok` `휴식` `스크린` `10분` `쿠키` `ê³¼` `êµ ë¹` | **브랜드 + 인코딩 깨짐 조각.** 기능 어휘(재생/시청/구독) 없음 |
| COMMUNICATION_ENTRY | 0.27 | `*instagram` `*당근` `공유해보세요` `*band` `모임` `알바` `일상의 순간을` `친구들과 일상의` `*kakao` | **브랜드 + 특정 페이지 마케팅 문구 통째 암기** (`친구들과 일상의 순간을 공유해보세요` = Instagram 카피). n=4 에서 문서 단위 암기 |
| ITEM_DETAIL | 0.20 | `상품` `브랜드` `co` `co kr` `*himart` `이벤트` `kr` `매장` `**장바구니**` `스토리` `**매장찾기**` `28` | **부분적으로 진짜 기능 어휘** (장바구니·매장찾기·상품·이벤트). 다만 `co` `kr` `28` 같은 무의미 토큰이 섞임 |
| PLACE_LOOKUP | 0.20 | `**지도**` `*카카오` `*카카오맵` `**버스**` `*티맵` `위치` `**길찾기**` `교통정보` `대기정보` `검색 길찾기` | **가장 기능 어휘다운 class** (지도·길찾기·버스·교통정보). 그럼에도 recall 0.000 |
| QUERY | 0.13 | `*google` `상승` `더보기` `none` `뉴스` `**flex**` `여행맛집` `**background**` `**position**` `검색` `스포츠` `*chrome` `검색어` | **검색 어휘 + CSS 토큰 혼입** (`flex` `background` `position` `none`) |
| UTILITY_ENTRY | 0.07 | `ë³` `¼ì` `ëª` `pc` `ai` `*에이닷` `ë³ ë³` `ë² ` `ê³` `ê²` `cs bot` | **거의 전부 인코딩 깨짐 조각.** 실질적으로 mojibake 를 학습 |

top-15 전체 브랜드 비율 평균 = **0.286** (7 class 평균). de-leak 후에는 0.000 (제거가 실제로 작동함을 확인).

### 9.3 발견된 **추가 누출 채널 2개** (사전 예상 밖, 상위 토큰 육안 검사에서 발견)

| 채널 | 정의 | 영향 | 어느 class 를 오염시키나 |
|---|---|---|---|
| **mojibake (인코딩 깨짐)** | `text_blob` 문자 중 U+0080–U+00FF 비율. UTF-8 을 Latin-1 로 잘못 디코드하면 급증 | **8/56 문서(14.3%)가 20% 초과.** 해당 서비스: KB Pay, 디바이스 케어, V3 Mobile Plus, 메가커피, 탑마트, 하나은행, 내 파일, YouTube | UTILITY_ENTRY **평균 44.7%**, CONTENT_OPEN 20.6%, FINANCIAL 12.5%. **최소 class 2개가 내용이 아니라 깨진 바이트 패턴으로 분리되고 있다** |
| **CSS/style 텍스트 혼입** | 본문 추출물에 CSS 키워드 토큰(`flex` `background` `position` …) | 4/56 문서, 존재 시 median 6개 | **QUERY 평균 7.0 hits/문서** — QUERY 4개 문서에 집중. QUERY 상위 계수 15개 중 4개가 CSS 토큰 |

**결론: char n-gram 이 word n-gram 을 이긴 이득의 상당 부분은 한국어 형태론이 아니라
mojibake 바이트 패턴을 잡은 것으로 보인다.** (char_wb 이득이 가장 큰 featureset 이
mojibake 비율이 가장 높은 A/C 계열이라는 점과 정합적이다. 인과 주장은 하지 않는다.)

이는 `D_TEXT_CORPUS` 를 쓰는 **모든** 후속 NLP 실험에 영향을 준다 → §14 반영.

## 10. Abstention 곡선 (primary `A_blob_full.word.logreg`)

분모 = 30 fold × 예측 = **560개 OOF 예측** (56 표본 × 10 repeat).

| top-1 확률 임계 | coverage | n_kept / n_total | coverage 내 prior_agreement | coverage 내 macro F1 |
|---|---|---|---|---|
| 0.00 – 0.15 | 1.000 | 560/560 | 0.536 | 0.225 |
| 0.20 | 0.304 | 170/560 | 0.794 | 0.425 |
| 0.25 | 0.062 | 35/560 | 0.800 | 0.559 |
| 0.30 | 0.032 | 18/560 | 1.000 | 1.000 |
| 0.35 | 0.013 | 7/560 | 1.000 | 1.000 |
| 0.40 – 0.80 | **0.000** | 0/560 | — | — |

> **어떤 임계도 영구 기준으로 선언하지 않는다.** 곡선의 실제 모양이 말하는 것:
> (a) 모델은 **0.40 을 넘는 확신을 단 한 번도 갖지 않는다** — 7 class 균등이 0.143 임을 감안하면
> 확률 질량이 거의 평평하다. (b) 0.30 에서 agreement 1.000 은 **n=18/560 = 3.2% 표본에서 나온
> 수치**이며, 원 표본으로 환산하면 2개 미만의 target 에 해당한다. 이 1.000 을 성능으로 읽으면 안 된다.
> (c) 실용 구간이라 부를 만한 지점(coverage 30% / agreement 0.79)조차 **버려지는 70%** 를
> rule DT 나 사람이 처리해야 한다는 뜻이다.
> `figures/RF001_B_abstention.png` 에 primary / de-leak / title-head-nav / brand-only 4개 곡선.

## 11. 데이터 무결성 — 반례와 오염

| 항목 | 내용 |
|---|---|
| **동일 텍스트 중복** | `NH스마트뱅킹` 과 `NH콕뱅크` 의 `text_blob` 이 **완전히 동일**(sha `8d208055e5c4`). 둘 다 FINANCIAL_ACTION_ENTRY. → CV 에서 한쪽이 train, 다른 쪽이 test 에 들어가면 **정답이 그대로 새어 나간다**. 이 class 의 recall 0.410 은 이만큼 낙관 편향돼 있다 |
| **동일 URL 중복** | `https://banking.nonghyup.com/nhbank.html` 이 2개 target 에 배정 (같은 두 서비스). 서로 다른 앱인데 랜딩 URL 이 같다 — prior_url 배정 자체의 문제 신호 |
| **prior_url 결측** | 네이버, G마켓 2건 (2/56). url_tokens 가 비어 A 와 C 의 차이가 없는 행 |
| **최소 문서** | 롯데하이마트 5토큰, 신한 SOL뱅크·NH 2건 8토큰, 하나은행 12토큰. **텍스트가 거의 없는 target 이 존재**한다 (blob_tokens min=5) |
| **B featureset 빈 문서** | 1/56 (title/headings/nav_links 가 전부 빈 문서) |

### 반례 (모델이 틀린 방향이 말해주는 것)

- `FINANCIAL_ACTION_ENTRY` 10개 중 평균 4.8개가 `ITEM_DETAIL` 로 간다. 은행 랜딩의 텍스트가
  "혜택/이벤트/상품" 어휘로 가득해 커머스와 구분되지 않는다 — **업종 어휘와 기능 어휘가 다르다**는 증거.
- `PLACE_LOOKUP` 은 상위 계수 토큰이 7 class 중 가장 기능적(`지도`·`길찾기`·`버스`·`교통정보`)인데
  **recall 은 0.000** 이다. 신호의 질이 아니라 **n=4 라는 표본 크기**가 병목이라는 직접 반례.
- 브랜드 토큰만 남긴 median-10-토큰 문서가 전체 본문을 이긴다 — 텍스트를 더 준다고 나아지지 않는다.

## 12. VERDICT

```
H-RF001-B-TFIDF : NOT_SUPPORTED
H-B-null        : SUPPORTED
H-B-leak        : SUPPORTED
```

**한 문장:** n=56·7class 에서 TF-IDF 선형모델은 stratified baseline 과 구분되지 않으며(정당한
16셀 중 0셀 분리, primary permutation p=0.279), 그나마 분리되는 유일한 구성은 **브랜드 토큰만
남긴 누출 대조군**이고, 남은 신호마저 최소 두 class 에서는 **인코딩 깨짐이라는 수집 아티팩트**다.

assertion type: `ANALYSIS` / authority `NON_CANONICAL` / self_approved `false`.

## 13. Limitation (무거운 순)

1. **n=56, 7 class, 최소 class n=3.** 5개 class 의 per-class 수치는 Wilson CI 폭 0.49~0.56 으로
   **측정했다고 말할 수 없다.** 이 실험은 "TF-IDF 가 안 된다"를 보인 게 아니라 상당 부분
   **"이 표본으로는 판정할 수 없다"** 를 보인 것이다. H-B-null 이 SUPPORTED 인 것은 모델의
   패배가 아니라 **표본의 한계**일 수 있다.
2. **fold 30개는 독립이 아니다.** 표본 56개를 10번 재사용한 것이므로 percentile 구간을
   정식 신뢰구간처럼 읽으면 안 된다. 폭은 과소추정, 유의성은 과대평가 쪽으로 편향된다.
3. **target 이 gold label 이 아니고, `prior_archetype` 은 `prior_business_domain` 과 1:1** 이다.
   이 실험은 archetype(기능 유형) 예측이 아니라 업종 예측을 검정했다.
4. **코퍼스 오염**: mojibake 8/56, CSS 혼입 4/56, 동일 텍스트 중복 1쌍. 이 셋은 결과를 어느
   방향으로든 밀 수 있으며, 특히 CV 를 가로지르는 누출은 낙관 편향이다.
5. **브랜드 제거는 문자열 치환**이라 `다음`(Daum vs "next"), `하나`(Hana vs "one"),
   `현대`(Hyundai vs "modern"), `밴드`(Band vs "band") 같은 동형이의어까지 지웠다.
   → **de-leak 결과는 보수적(과소평가) 방향**이며, 진짜 기능 어휘도 일부 잃었다.
6. **char_wb 의 우위를 한국어 형태론의 증거로 쓸 수 없다.** mojibake 와 교락돼 있다.
7. permutation p 는 사후 선택된 셀에서 나왔고 다중비교 보정 전이다.
8. **인과 주장 없음.** 어떤 토큰이 archetype 을 "만든다"거나 "결정한다"는 해석은 불가.

## 14. Production implication

1. **이 모델을 RF mapping 의 1차 판정기로 쓸 수 없다.** 7 class 중 4개는 한 번도 예측되지
   않았고, 전체가 stratified 난수와 구분되지 않는다. `NON_CANONICAL` 이며 채택 대상이 아니다.
2. 쓴다면 **rule DT 가 abstain 한 경우의 보조 신호**로만이고, 반드시 abstention 임계와 함께
   써야 하며 **임계는 이 데이터가 아닌 별도 데이터로 정해야 한다** (여기서 나온 0.20/0.30 은
   각각 coverage 30%/3.2% 짜리다).
3. **선행 조치가 더 급하다 — 모델이 아니라 코퍼스**:
   (a) `build_text_corpus.py` 의 `lxml_html.fromstring(dom.read_bytes())` 는 charset 을
   추론에 맡긴다 → 8/56 문서 인코딩 파손. **명시적 charset 처리 필요.**
   (b) `//li[.//a] | //article` 카드 추출에 `<style>` 내용이 딸려 들어옴 → **style/script 제외 필요.**
   (c) `NH스마트뱅킹`/`NH콕뱅크` 의 prior_url 중복 → prior 배정 재검토 필요.
   이 셋을 고치기 전의 어떤 NLP 결과도 (본 실험 포함) 신뢰 구간이 실제보다 낙관적이다.
   — 단 이는 **관찰 보고이지 수정 지시가 아니다.** production 경로는 이 워커가 건드리지 않았다.
4. 브랜드 사전을 **feature 로** 쓰는 선택지는 정직하게 문서화해야 한다. E 대조군이 보여주듯
   "서비스명 → 업종" 룩업이 텍스트 모델보다 잘 작동한다. 그것을 원한다면 **모델이 아니라
   사전(lookup table)으로 명시**해야 하며, 신규 서비스에 일반화되지 않음을 전제로 해야 한다.

## 15. 추가 연구질문

1. 형태소 분석기(`kiwipiepy`) 토크나이즈가 word n-gram 열세를 얼마나 회복하는가 —
   **mojibake 를 먼저 고친 뒤**에 물어야 답이 해석 가능하다.
2. **인코딩·CSS 오염을 제거한 코퍼스로 이 20셀 grid 를 그대로 재실행**하면 char_wb 우위가
   유지되는가? 유지되지 않으면 §7 의 3번 관찰은 아티팩트였던 것이다.
3. archetype 을 예측하는 대신 **기능 어휘 사전(장바구니/길찾기/송금/검색/재생…) 기반 규칙**이
   TF-IDF 를 이기는가? PLACE_LOOKUP·ITEM_DETAIL 의 상위 토큰은 그 사전이 실재함을 시사한다.
4. minority class 가 "추정 가능"해지는 최소 표본은? class 당 n≥30 을 기준으로 하면
   7 class × 30 = 210 target 이 필요하다. 59 → 210 의 비용이 정당한지는 A plane 결정 사항.
5. `prior_archetype` 과 `prior_business_domain` 의 1:1 관계를 깨는 target(같은 업종·다른 기능)이
   모집단에 존재하는가? 존재하지 않으면 archetype 축은 이 코호트에서 검정 불가능하다.

---

### 재현

```bash
cd /home/sieg/projects-wsl/ProjectFinal/.agent_worktrees/claude_d_research/research/landing_accessibility/research_d
OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 \
  /home/sieg/projects-wsl/ProjectFinal/.venv/bin/python -u tools/rf001_b_tfidf.py
```

seed 20260827 고정, Restart→Run All 재현 가능. `--no-mlflow` 를 붙이면 MLflow 기록 없이 산출만 만든다.
(스레드 수를 제한하지 않으면 고부하 상태에서 BLAS 스레드 경합으로 극단적으로 느려진다 — 수치에는 영향 없음.)
