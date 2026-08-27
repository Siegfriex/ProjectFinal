# RQ-D10 — evidence slot 간 시점 불일치의 정량화와 관측단위 지표 설계

| | |
|---|---|
| **RQ** | evidence slot 간 시점 불일치(dom/ax = 렌더 이전 shell vs probe = 렌더 후)를 raw artifact에서 정량화할 수 있는가. 가능하다면 관측단위 지표의 정의는 무엇이어야 하는가 |
| **티켓** | B `T-B-RQ-D-001` Q3 |
| **관련 주장** | A `F-A3.1` — "라벨러 불일치의 원인 = slot 시점 불일치" (**hypothesis로만 취급**) |
| **VERDICT** | **PARTIALLY_SUPPORTED** |
| **plane / 권위** | D (Independent Research Sandbox) · NON_AUTHORITATIVE |

## VERDICT 한 줄

**PARTIALLY_SUPPORTED** — slot 시점 불일치는 실재하고 raw artifact만으로 재현 가능하게
정량화된다(관측 6/58, 10.3%). 그러나 **전면적 현상이 아니다**: 동일 셀렉터로 잰
dom↔probe 요소 수는 45개 평가가능 관측 중 **29건이 정확히 동일**하고 40건이 |log2비| ≤ 0.15다.
"dom/ax는 렌더 이전 shell"이라는 서술을 **다수 관측에 일반화하면 틀린다**.

## 왜 중요한가

두 사람(또는 두 자동 판정기)이 같은 관측을 보고 서로 다른 slot을 읽으면, 문자 그대로
**다른 문서를 본 것**이 되는 관측이 존재한다. 그 수가 몇 개이고 어느 관측인지가 특정되지
않으면 판정 불일치를 "라벨러 품질" 문제로 오귀속할 위험이 있다. 이 RQ는 그 후보 관측을
**label을 보지 않고** 지목 가능한지를 묻는다.

## 입력

| 파일 | 행/개수 |
|---|---|
| `research_d/results/D_OBSERVATION_TABLE.json` | 66행 (관측단위 공용 테이블) |
| raw evidence `l0a/dom.html` (재파싱) | 60 |
| raw evidence `l0a/ax.json` (신규 파싱) | 60 |
| raw evidence `l0a/probe.json` (재파싱) | 58 |
| slot 파일 mtime (dom·ax·css·screen×2·probe) | 60 관측 × 6 slot |
| source: `l0_collector.py` L410-440 @`876c67d3…` (`claude_b_e001_runner`) | — |
| source: `l0_probe.js` L143-171, L277-299 | — |

raw evidence는 **읽기 전용**으로만 접근했다. label 파일은 열지 않았다.

## 분석단위 · N · missing

- **grain: observation** (`run_dir` × `observation_id`). target(`wtg`)이 아니다.
- 공용 테이블 66행 중 **6행은 관측 디렉터리가 없다**(총실패 run: 삼성 노트·삼성 월렛·삼성
  인터넷 브라우저 각 2회 시도). slot 간 비교가 정의되지 않으므로 **전부 제외**. → **N = 60**.
- 60 중 dom 60 / ax 60 / **probe 58** (신한 SOL뱅크·롯데하이마트 2건 probe 없음) / mart 56.
- **분모 규칙**: slot 간 비교가 필요한 지표는 분모 **58**, dom·ax만 쓰는 지표는 분모 **60**.
- **중복 재실행**: 4 target이 각 2관측(Netflix·Chrome·현대카드·캐시워크, 6.2~7.8초 간격).
  **중복을 병합하지 않았다.** 관측단위 지표를 검증하는 것이 목적이고, 이 4쌍은
  test-retest 자연실험이기 때문이다(아래 §재현성). unique target = 59.

## 사용 변수

`dom.html` 재파싱(`dom_ans_n`, `dom_body_element_n`, `dom_element_n`, `dom_body_text_len`,
`dom_title_utf8`, `dom_script_n`, `dom_noscript_n`) · `ax.json` 신규 파싱(`ax_node_n`,
`ax_interactive_n`, `ax_focusable_n`, role 분포, RootWebArea의 `name`/`url`) ·
`probe.json`(`collected_at`, `url`, `viewport.final_url`, `viewport.title`,
`accessible_name_sources`, `target_size`, `primary_action_candidates`) ·
slot 파일 mtime · prior(`prior_url`, `prior_archetype`, `prior_service`).

## 방법

### M1. slot 순서를 코드에서 먼저 확정했다 (assertion: IMPLEMENTATION)

`l0_collector.py` L410-440 (`876c67d323e0a02b455d841effb6f6876a253fb8`):

```
goto(wait_until="load") → wait 400ms → [dom] → [ax] → [computed_css]
  → screen_initial → screen_fullpage(문서 전체 스크롤 발생) → scrollTo(0,0)
  → wait 400ms → [probe]
```

즉 **probe는 dom/ax보다 구조적으로 뒤다**. 이것은 관측이 아니라 코드에서 읽은 사실이다.
그 사이에 full-page 스크린샷을 위한 **문서 전체 스크롤**이 끼어 있어, lazy-load /
IntersectionObserver 컨텐츠가 probe 시점에만 존재할 수 있는 경로가 코드 수준에서 열려 있다.

### M2. slot 단위 시각의 원천을 검증했다 (assertion: OBSERVATION)

`run.json`은 run 단위(`created_at`/`sealed_at`)만, `probe.json`만 `collected_at`을 갖는다.
slot 단위 시각의 유일한 원천은 **파일 mtime**이다. 신뢰성을 교차검증했다:
`mtime(probe.json) − probe.collected_at` = **+0.015 ~ +0.455 s (n=58, 전부 양수)**.
mtime이 재설정되지 않았고 기록 지연만큼만 늦다.

### M3. dom↔probe를 **동일 셀렉터**로 비교했다 (assertion: DEFINITION)

`l0_probe.js` L169의 `accessible_name_sources` 셀렉터는 **visible 필터가 없다**(L171).
따라서 이 셀렉터를 `dom.html`에 그대로 적용하면 *같은 질의를 두 시점에 실행한* 비교가 되고,
가시성·레이아웃 차이가 섞이지 않는다. RQ-D10의 핵심 지표는 이 위에 세웠다.
`primary_action_candidates`/`target_size`는 visible 필터가 있어 이 목적에 쓸 수 없다.

### M4. 인코딩 교정 (assertion: ANALYSIS — 방법론적 반례)

공용 테이블의 `dom_title`은 lxml이 **raw bytes의 meta charset을 믿어** mojibake를 낳는다.
수집기는 `page.content()`를 **UTF-8로** 기록하므로(L417) UTF-8 강제 디코드가 옳다.
교정 전 dom↔probe 제목 불일치 **9/58** → 교정 후 **3/58**. 즉 순진한 비교의
**6/58은 slot 불일치가 아니라 분석기 자신의 인코딩 결함**이었다.

## 주요 결과 (모든 수치에 분모)

### R1. 시점 불일치는 실재하는가 — 물리적 노출창 (OBSERVATION)

| 양 | n | median | IQR | max |
|---|---|---|---|---|
| `mtime(probe) − mtime(dom)` | 58 | **1.79 s** | 1.19–2.68 | **12.62 s** |
| `mtime(ax) − mtime(dom)` | 60 | **0.055 s** | 0.026–0.087 | 1.29 s |

- slot 기록 순서가 코드와 일치한 관측 **58/58 (평가가능분)**. 나머지 2는 probe 부재로 평가불가.
- → dom과 ax는 **사실상 같은 시점**(median 55 ms), probe만 **1.8초 뒤**다.
  "dom vs ax vs probe" 3자가 아니라 실질적으로 **(dom, ax) vs probe** 2자 구조다.

### R2. 증거별 해당 관측 수 (OBSERVATION)

| 증거 | n / 분모 | 비고 |
|---|---|---|
| (a) DOM body 빈 shell인데 probe는 요소 관측 | **2 / 60** | NH스마트뱅킹, NH콕뱅크 (둘 다 `m.nonghyup.com` 동일 페이지로 귀결) |
| (b) 제목 불일치 (dom/ax/probe 세 쌍 중 하나라도) | **3 / 58** | 인코딩 교정 후. 교정 전이면 9/58 (§M4) |
| (c) 요청 URL ≠ `final_url` (리다이렉트) | **17 / 58** | host 8 / path 6 / query 3. **slot 불일치가 아니다** |
| (c') **slot 간** URL 드리프트 (`ax` RootWebArea url ≠ `probe.final_url`) | **3 / 58** | NH스마트뱅킹, NH콕뱅크, 모니모 — 전부 path 변경 |
| (d) 동일 셀렉터 요소 수 괴리 `|log2| > 0.534` | **5 / 45** (검열 13 제외, 분모 58 중) | 마켓컬리·홈플러스·모니모·NH×2 |
| **어느 하나라도 해당 (`slot_disagreement_score ≥ 1`)** | **6 / 58 (10.3%)** | 서로 다른 final URL은 **5개** |

**(c)는 slot 불일치가 아니다**를 명시한다. 17건 중 14건은 navigation 시점의 서버
리다이렉트로, dom·ax·probe **모두 같은 최종 문서**를 본다. slot 간 불일치는 3건뿐이다.
이 구분을 하지 않으면 17/58(29%)로 3배 가까이 과대계상된다.

### R3. 괴리의 분포는 이봉(bimodal)이고 **단방향**이다 (ANALYSIS)

`slot_name_source_gap = log2((probe_ans_n+1)/(dom_ans_n+1))`, n=45 (검열 13 제외):

- **정확히 0: 29 / 45**, |gap| ≤ 0.05: **38 / 45**, |gap| ≤ 0.15: **40 / 45**
- |gap| ≥ 0.9: **5 / 45**
- 정렬된 |gap| 상위: … 0.046, 0.070, **0.149 ‖ 0.919**, 2.733, 3.700, 6.088, 6.088
  → **0.149와 0.919 사이에 관측이 하나도 없다.** 임계값을 이 빈틈에서 잡는다.
- **음수 방향(probe < dom) 이탈 0 / 45** (|gap| > 0.05 기준). 부호가 코드에서 읽은
  slot 순서(dom → probe)와 완전히 일치한다.

제목도 같은 방향성을 보인다: dom↔ax 제목 불일치 **0 / 58**, 불일치 3건은 전부
**dom = ax ≠ probe**이고 **역방향(ax = probe ≠ dom)은 0 / 58**이다.

### R4. AX slot의 3자 비교 — AX는 "시점"이 아니라 "표상"이 다르다 (ANALYSIS)

| 비교 | n | median log2 |
|---|---|---|
| `ax_interactive_n` / `dom_ans_n` | 58 | **−1.13** (AX가 DOM의 약 46%) |
| `probe_ans_n` / `ax_interactive_n` | 58 | **+1.10** |
| `probe_ans_n` / `dom_ans_n` (동일 셀렉터) | 45 | **0.00** |

AX가 DOM보다 항상 적은 것은 **시점 차이로 해석하면 안 된다**. 근거: (i) dom→ax 경과가
median 55 ms, (ii) dom↔ax 제목 불일치가 58/58에서 0, (iii) AX 트리는 ignored/hidden
노드를 가지치기하고 role 어휘도 다르다. 따라서 AX-vs-DOM 괴리는 **표상 차이**이고,
AX가 slot 비교에서 하는 실제 역할은 다르다:

> **AX는 "누가 늦었는지"의 심판이다.** RootWebArea의 `name`·`url` 프로퍼티가 dom과 같은
> 시점의 제목·URL을 독립적으로 증언하므로, dom과 probe가 어긋날 때 AX가 dom 쪽에 붙는지
> probe 쪽에 붙는지로 **드리프트 방향**이 결정된다. 실측 결과 AX는 **58/58에서 dom 쪽**이다.

R2(a)의 4개 DOM-빈 관측 전부에서 `ax_node_n == 1` (RootWebArea만)이다. 즉 dom·ax 두 slot이
동시에 비었고 probe만 채워졌다 — 3-slot 궤적이 시간 순서와 일치한다.

### R5. 물리적 노출창 길이는 괴리를 예측하지 않는다 (ANALYSIS)

`slot_elapsed_dom_to_probe_s` vs `slot_name_source_gap`: Spearman **ρ = 0.036, p = 0.815 (n = 45)**.
→ 괴리는 "더 오래 기다렸으니 더 벌어졌다"가 아니라 **특정 페이지의 클라이언트 동작
(JS 리다이렉트 / SPA 하이드레이션)** 에서 온다. 단, 노출창은 페이지 무게(스크린샷 소요시간)와
교락돼 있으므로 이 상관의 부재를 인과 부재로 읽지 않는다. **인과 주장 아님.**

## 제안 지표 정의

단일 스칼라로 뭉개지 않는다. 성분 flag를 **항상 함께 저장**해야 한다.

### I1. `slot_elapsed_dom_to_probe_s` — 연속형 (초)
- **정의**: `mtime(probe.json) − mtime(dom.html)`.
- **계산식**: 위 그대로. 임계값 없음(원형이 연속형).
- **근거**: slot이 같은 시점의 문서가 아님을 파일에서 직접 보이는 유일한 양.
- **한계**: mtime이 원천이다. 아카이브·복사로 mtime이 재설정되면 무효 →
  `probe.collected_at`과의 차이로 매번 검증해야 한다(본 데이터에서는 +0.015~+0.455 s로 정상).

### I2. `slot_dom_empty_probe_rich` — binary
- **정의**: `dom_body_element_n == 0 AND probe_ans_n > 0`.
- **연속형 버전**: `dom_body_fill = dom_body_element_n / dom_element_n` (0이면 shell).
- **임계값 근거**: 0은 임계값이 아니라 경계 자체(빈 body). 임의 상수 없음.
- **한계**: 단독으로는 "shell"과 "수집 실패"를 구별하지 못한다(§반례).

### I3. `slot_title_mismatch` — binary (+ 연속형 `title_dissim_max`)
- **정의**: NFKC 정규화 → 공백 축약 → casefold 후 dom·ax·probe 세 제목 중 한 쌍이라도 불일치.
- **연속형 버전**: `title_dissim_max = max(1 − SequenceMatcher.ratio)` over 세 쌍. 임계값 불필요.
- **임계값 근거**: flag는 정확일치 기준이라 임계값이 없다.
- **필수 전제**: `dom.html`을 **UTF-8로 강제 디코드**해야 한다. 바이트 파싱은 허위 불일치를
  6/58 만든다(§M4).

### I4. `slot_url_drift_interslot` — ordinal 0–3
- **정의**: `ax.json` RootWebArea의 `url`과 `probe.viewport.final_url`을 비교.
  0 동일 / 1 query·fragment만 / 2 path 변경 / 3 host 변경.
- **연속형/무임계 버전**: ordinal 자체가 임계값 없는 형태. 필요하면 성분별로 분해해 쓴다.
- **임계값 근거**: URL 성분 위계에서 유도. 임의 상수 없음.
- **주의**: 요청 URL(`prior_url`)은 slot이 아니다. 요청↔final 비교(17/58)를 slot 불일치로
  세면 3배 과대계상된다.

### I5. `slot_name_source_gap` — 연속형 (log2 비) ★ 핵심
- **정의**: `log2((probe_ans_n + 1) / (dom_ans_n + 1))`.
  양변 모두 `l0_probe.js` L169 셀렉터
  (`a[href],button,input:not([type=hidden]),select,textarea,img,[role=button|link|img|checkbox|radio|tab]`)로
  센 수 — probe는 런타임, dom은 `dom.html` 재파싱. **양쪽 다 visible 필터가 없다.**
- **flag 버전**: `|gap| > thr`.
- **임계값의 출처**: `thr = max(재실행 4쌍의 |Δgap| 최댓값, gap 분포의 첫 큰 빈틈 중점)`
  = `max(0.000, 0.534)` = **0.534** (비율 1.45배). **임의 상수가 아니라 데이터 유래**이며,
  0.149와 0.919 사이의 관측 공백에서 나왔다. 표본이 45(+검열 13)뿐이므로
  **영구 기준이 아니라 현 데이터의 잠정값**이다.
- **검열 처리 필수**: probe의 cap 300에 걸린 관측은 비율이 절단되므로 **결측**으로 둔다
  (`slot_name_source_gap_censored = 1`, **13/58**).

### I6. `slot_disagreement_score` — count 0–4
- **정의**: I2·I3·I4(>0)·I5-flag 중 참인 개수. 평가 불가 성분은 분모에서 뺀다 →
  `slot_disagreement_evaluable_n`을 **반드시 동반 저장**한다.
- **가중합은 권장하지 않는다**: 성분 간 교환비의 근거가 없다.
- **본 데이터 분포 (분모 58)**: 0 → **52**, 1 → **3**, 2 → **1**, 3 → **0**, 4 → **2**.

### 최소 권장 세트

production에 넣는다면 **I1(연속) + I5(연속) + I4(ordinal) + I2(binary)** 를 관측단위 컬럼으로
저장하고, I6는 조회 편의를 위한 파생으로만 둔다. 연속형을 저장하면 임계값을 나중에 바꿔도
재수집이 필요 없다.

## 재현성 — 중복 재실행 쌍 test-retest (OBSERVATION)

동일 target을 6.2~7.8초 간격으로 두 번 수집한 **4쌍**(Netflix·Chrome·현대카드·캐시워크):

| target | 간격 | `dom_ans_n` | `probe_ans_n` | `slot_name_source_gap` | `|Δgap|` | score |
|---|---|---|---|---|---|---|
| Netflix | 7.8 s | 50 / 51 | 50 / 51 | 0.000 / 0.000 | **0.0000** | 0 / 0 |
| Chrome | 6.3 s | 132 / 132 | 132 / 132 | 0.000 / 0.000 | **0.0000** | 0 / 0 |
| 현대카드 | 6.2 s | 197 / 197 | 197 / 197 | 0.000 / 0.000 | **0.0000** | 0 / 0 |
| 캐시워크 | 6.3 s | 204 / 204 | 203 / 203 | −0.0071 / −0.0071 | **0.0000** | 0 / 0 |

- **`|Δ slot_name_source_gap|` = 0.0000, 4/4 쌍.**
- `slot_title_mismatch` 일치 **4/4**, `slot_url_drift` 일치 **4/4**,
  `slot_disagreement_score` 일치 **4/4**.
- 캐시워크의 −0.0071(dom 204 vs probe 203)은 **양쪽 실행에서 동일하게** 재현됐다.
  노이즈가 아니라 결정적 구조 차이다.
- → 관측된 재현 노이즈 바닥은 **0**. 다만 **쌍이 4개뿐**이고 네 쌍 모두 비-flag 관측이므로,
  **flag 영역(|gap| ≥ 0.9)의 재현성은 이 데이터로 추정되지 않았다**. 이것이 이 RQ의
  가장 큰 미검증 지점이다.

## 민감도 분석

### S1. gap 임계값 격자 (분모 45)

| thr (log2) | 0.10 | 0.15 | 0.20 | 0.26 | 0.32 | 0.40 | **0.534** | 0.75 | 1.00 |
|---|---|---|---|---|---|---|---|---|---|
| = 배수 | 1.07 | 1.11 | 1.15 | 1.20 | 1.25 | 1.32 | **1.45** | 1.68 | 2.00 |
| n flagged | 6 | 5 | 5 | 5 | 5 | 5 | **5** | 5 | 4 |
| n 음수방향 | **0** | **0** | **0** | **0** | **0** | **0** | **0** | **0** | **0** |

임계값을 0.15~0.75(1.11~1.68배) 어디에 두어도 **flag 수는 5로 불변**이다.
지표는 이 데이터에서 임계값에 둔감하다.

### S2. "DOM이 비었다"의 정의 대안 (분모 60)

| 규칙 | n |
|---|---|
| `dom_body_element_n == 0` | 4 |
| `dom_body_text_len < 50` (공용 테이블 정의) | 4 |
| `dom_ans_n == 0` | 4 |
| `dom_ans_n == 0 AND probe_ans_n > 0` | **2** |

네 정의가 **같은 4건**을 고른다. probe 조건을 붙이는 순간 4 → 2로 반감한다.
**probe 조건이 flag의 의미를 결정한다.**

### S3. 검열의 비무작위성 (분모 58)

cap 300 검열 13건의 `dom_ans_n` median = **566**, 비검열 45건 = **84**.
검열은 큰 페이지에 몰려 있다. **`slot_name_source_gap`의 결측은 MCAR이 아니다.**
이 13건에서 slot 불일치가 없다고 말할 수 없다 — 측정하지 않았을 뿐이다.
(RQ-D8/D9의 cap 절단 문제와 같은 뿌리다.)

## 반례 / 대안설명 검토

### C1. "`dom_body_empty`는 SPA가 아니라 그냥 수집 실패다" → **절반은 맞다** (ANALYSIS)

DOM body가 빈 4건(분모 60)을 AX·probe로 갈랐다:

| target | dom bytes | script | `ax_node_n` | AX RootWebArea title / url | probe | 판정 |
|---|---|---|---|---|---|---|
| 신한 SOL뱅크 | 6072 | 4 | 1 | "Shinhan Bank" / `bank.shinhan.com/` | **없음** | **구별 불가** |
| 롯데하이마트 | 314 | 3 | 1 | "" / `e-himart.co.kr/index.jsp` | **없음** | **수집 실패에 가깝다** (AX 제목도 빔) |
| NH스마트뱅킹 | 1657 | 6 | 1 | "농협 개인모바일" / `m.nonghyup.com/index_mobile.html` | ans 67 | **slot 불일치** |
| NH콕뱅크 | 1657 | 6 | 1 | "농협 개인모바일" / `m.nonghyup.com/index_mobile.html` | ans 67 | **slot 불일치** |

- **2/4는 probe 자체가 없어 대안설명과 구별되지 않는다.** 이 2건은
  `slot_dom_empty_probe_rich`가 0이며, 그것이 이 지표의 올바른 거동이다.
- NH 2건은 slot 불일치가 맞다. **결정적 근거**: dom·ax가 본 URL
  (`m.nonghyup.com/index_mobile.html`)과 probe가 본 URL(`m.nonghyup.com/servlet/PMMNP0001R.view`)이
  **다른 문서**다. `load` 이후 JS가 리다이렉트했고 dom·ax는 중간 shell을, probe는 목적지를 봤다.
  "렌더 지연"이 아니라 **문서 교체**다.
- 부수 관측: 이 4건은 **전부 `in_mart == 1`** 이다. probe 없는 2건도 mart에 남아 있다.
  분모 손실을 다루는 RQ-D7과 교차하는 지점이다.

### C2. "제목 불일치가 9건이다" → **REFUTED, 3건이다**

6/58은 D 자신의 바이트 파싱 mojibake였다(§M4). **타인의 수치뿐 아니라 D 자신의 중간 산출도
반례 검토 대상**이라는 사례로 기록한다.

### C3. "URL 드리프트가 17건이다" → **REFUTED, slot 간은 3건이다**

14건은 navigation 시점 리다이렉트로 세 slot이 모두 같은 문서를 본다(§R2).

### C4. "AX가 DOM보다 요소가 적으니 DOM이 더 나중이다" → **REFUTED**

AX-DOM 격차는 표상 차이다(§R4). dom→ax 경과 median 55 ms, 제목 불일치 0/58.

## Limitations

1. **인과 불가**: D는 label을 열지 않았고 열 수 없다. "slot 불일치 → 라벨러 불일치"는
   이 RQ로 검증되지 **않았다**. A `F-A3.1`은 hypothesis로 남는다.
2. **flag 영역의 재현성 미검증**: 재실행 4쌍이 전부 비-flag 관측이다. flag가 켜지는 관측이
   재수집에서도 켜지는지는 모른다. → 추가 재실행이 필요하다(§추가 RQ).
3. **비MCAR 결측**: cap 300 검열 13/58이 큰 페이지에 편중돼 `slot_name_source_gap`이
   구조적으로 결측이다.
4. **mtime 의존**: slot 단위 시각은 파일시스템 mtime이 유일 원천이다. evidence를 아카이브·
   복사·재패킹하면 I1이 무효가 된다. 수집기가 slot별 타임스탬프를 매니페스트에 남기지 않는 것이
   근본 원인이다.
5. **표본**: 58 관측 / 59 target / 6 flagged. flagged 6건 중 서로 다른 final URL은 5개다
   (NH 2 target이 같은 페이지). 하위집단 비교는 검정력이 없다 — archetype 분포
   (flagged: ITEM_DETAIL 3, FINANCIAL_ACTION_ENTRY 3 / 전체 25, 10)는 **기술통계로만** 적고
   검정하지 않는다.
6. **단일 브라우저·단일 프로토콜**(`pc-fixture-1`, layout 390px, SETTLE 400 ms).
   SETTLE_MS를 바꾸면 flag 수가 달라질 것으로 **예상되나 측정하지 않았다** (PROJECTION).
7. `screen_fullpage` 캡처가 유발하는 전체 스크롤이 lazy-load를 촉발하는 경로는 코드에서
   확인했으나, 그것이 R3의 5건에서 실제 작동했는지는 **분리 실험 없이는 알 수 없다**.

## Production implication (assertion: IMPLEMENTATION / PROJECTION)

D는 권위가 없다. 아래는 제안이지 지시가 아니다.

1. **(저비용·고효용) 수집기가 slot별 타임스탬프를 `manifest.jsonl`에 기록하면**
   I1이 mtime 의존에서 벗어난다. 현재 매니페스트는 `bytes`/`sha256`만 갖는다.
2. **판정 파이프라인은 어느 slot을 읽는지 명시해야 한다.** 같은 관측에서 dom과 probe가
   다른 문서인 경우가 6/58 존재한다. slot을 명시하지 않은 판정은 6건에서 재현되지 않는다.
3. **`slot_disagreement_score ≥ 1`인 관측은 자동 판정에서 제외하는 게 아니라
   flag를 달아 human review 큐로 보내는 게 맞다** — 6/58(10.3%)은
   `HUMAN_FINAL_REVIEW_MAX = 5`를 초과하므로, 제외 대신 우선순위 정렬에 쓰는 편이 현실적이다.
4. **연속형을 저장하라.** I1·I5를 연속형으로 mart에 넣어두면 임계값을 나중에 바꿔도
   재수집이 불필요하다. flag만 저장하면 임계값이 영구 동결된다.
5. **공용 관측 테이블의 `dom_title`은 UTF-8 재파싱으로 교체를 권한다** —
   현재 값은 9/58에서 mojibake다. (D 내부 산출물이며 production mart 이슈는 아니다.)

## 추가 연구질문

- **RQ-D10a**: flag가 켜진 6건을 재수집하면 다시 켜지는가. flag 영역의 test-retest.
  (본 RQ의 최대 공백. 재수집은 REAL_TARGET 접속이므로 D 범위 밖 — B에 이관해야 한다.)
- **RQ-D10b**: `SETTLE_MS`(400)와 `wait_until`(`load` vs `networkidle`)을 바꾸면
  `slot_name_source_gap` 분포가 어떻게 이동하는가. slot 불일치는 프로토콜 파라미터의 함수인가.
- **RQ-D10c**: `screen_fullpage` 캡처의 전체 스크롤을 제거한 조건과 비교하면
  R3의 5건 중 몇 건이 남는가. (lazy-load 경로의 분리 실험)
- **RQ-D10d**: cap 300 검열 13건에서 slot 불일치를 측정할 대체 지표
  (예: `dom_ans_n`을 300으로 절단해 좌우 동일 검열을 걸고 비교)는 편향을 얼마나 줄이는가.
- **RQ-D10e**: `computed_css.json`·`screen_initial.png`도 slot이다. 스크린샷 픽셀 차이
  (`screen_initial` vs `screen_fullpage` 상단 크롭)로 slot 불일치를 **독립 채널**에서
  교차확인할 수 있는가.

## Label 경계선 (명시)

D는 `control/label/**` 및 holdout label 파일을 **열지 않았다**. 이 RQ가 답한 범위는:

> slot 불일치는 실재하고, raw artifact만으로 재현 가능하게 정량화되며,
> **어느 slot을 읽었는지에 따라 서로 다른 문서를 본 셈이 되는 관측이 58 중 6개**다.

여기서 멈춘다. 그 6개가 실제 라벨러 불일치와 겹치는지는 **D가 검증할 수 없고 하지 않았다.**
A `F-A3.1`의 인과 서술은 사실로 채택되지 않았다.

## 산출

| 파일 |
|---|
| `research_d/tools/rq_d10_slot_mismatch.py` (Restart→Run All 가능, read-only) |
| `research_d/results/RQ_D10_slot_mismatch.json` |
| `research_d/results/RQ_D10_FINDINGS.md` (이 문서) |
| `research_d/figures/RQ_D10_gap_distribution.png` |
| `research_d/figures/RQ_D10_three_slot_trajectory.png` |
