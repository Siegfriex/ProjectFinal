# RQ-D9 — dom.html 크기 · probe 신호 풍부도 · cap 도달의 관계 구조

> **VERDICT: REFUTED** (크기는 관측 품질의 대리변수가 아니다)
> **+ PARTIALLY_SUPPORTED** (대리변수는 존재한다 — `dom_interactive_n`, 단 rank 수준에서만)
>
> Ticket: `T-B-RQ-D-001` Q2 · Worker: Claude D · 재현: `tools/rq_d9_quality_proxy.py` (Restart→Run All, 35초, 재실행 시 byte-identical)

---

## RQ

`dom.html` 크기 · probe 신호 풍부도 · cap 도달 사이의 관계 구조는 무엇인가?
크기가 관측 품질의 대리변수가 아니라면, **무엇이 대리변수가 될 수 있고 무엇이 될 수 없는가.**

## 왜 중요한가

파이프라인이 관측을 triage·정렬·수집건전성 판정할 때 쓸 수 있는 스칼라가 필요하다.
아티팩트 바이트 크기는 가장 손쉬운 후보이며 이미 모든 관측에 존재한다. 그것이 실제로
품질을 정렬하는지 여부는 "어떤 관측을 재수집할 것인가"를 직접 좌우한다.

## 입력

| 항목 | 값 |
|---|---|
| 파일 | `research_d/results/D_OBSERVATION_TABLE.csv` (유일 입력) |
| 행수 | 66행 × 64열 |
| raw 재파싱 | 없음 (지시대로 관측테이블만 사용) |
| gold label | **열지 않음** (leakage 방지) |

## 분석단위 · N · missing N

**주 분석단위: `in_mart==1 AND probe_present==1` → n = 54 targets (unique wtg 54).**

선택 이유 (명시):

- `in_mart==1`은 **이미 중복제거된 target mart**다 — 56행 / unique wtg 56. 재실행된 target의
  2번째 관측은 `in_mart==0`으로 표시돼 있다. 즉 in_mart가 dedup 플래그 역할을 한다.
  (티켓은 중복 4 target이라 했으나 테이블 실측은 **중복 wtg 7개**, 그중 probe를 가진 것은 4개다.)
- `probe_present==1`만 쓰면 58 obs이지만 unique wtg는 54 — 중복 재실행 4건이 다시 들어와
  관측 독립성이 깨진다. 그래서 이쪽은 **민감도 분석에만** 쓴다.
- 교집합 n=54는 **모든 분석 컬럼에서 missing이 정확히 0**이다. 아래 모든 분모는 별도 표기가
  없으면 54다.

**missing N: 주 grain에서 0/54.** `in_mart==1`에서 탈락한 2 target은 probe payload가 없어
신호 컬럼 전체가 NaN이다:

| service | dom_bytes | dom_element_n | dom_interactive_n | dom_body_empty |
|---|---|---|---|---|
| 롯데하이마트 | 314 | 5 | 0 | 1 |
| 신한 SOL뱅크 | 6072 | 13 | 0 | 1 |

## 사용 변수

- **결과(품질 조작화)**: `n_primary_action_candidates`, `n_accessible_name_sources`, `n_target_size`, `n_contrast`
- **대리변수 후보**: `dom_bytes`, `ax_bytes`, `css_bytes`, `probe_bytes`, `dom_element_n`, `dom_body_element_n`, `dom_interactive_n`, `dom_a_href_n`, `dom_button_n`, `dom_input_n`, `dom_role_n`, `dom_aria_label_n`, `dom_script_n`, `dom_body_text_len`, `probe_scroll_height`
- **파생**: `bytes_per_element`, `capture_ratio`, `signal_richness`(4신호 percentile rank 평균)
- **절단**: `cap_*`, `cap_any`, `cap_count`
- **상태**: `dom_body_empty`, `dom_title`/`probe_title`, `probe_url`/`probe_final_url`

## 방법

- **비모수 우선**: Spearman을 주 통계량으로 사용. tie는 scipy 표준인 **midrank(평균순위)** 보정으로
  처리하며, 부트스트랩 재표본 **내부에서도** 매번 midrank를 다시 계산한다 (벡터화 구현이
  scipy와 1e-10 이내 일치함을 200개 1-D + 50개 2-D 케이스로 검증).
- tie에 더 강건한 **Kendall tau-b**를 교차확인용으로 같이 보고.
- **부트스트랩 percentile CI95**, B=10,000, seed=20260827. 한쪽 축이 단일값으로 붕괴한 재표본은
  rho가 정의되지 않아 제외하고 그 수를 기록.
- 군간 비교는 **Mann-Whitney U + Vargha-Delaney A12** 효과크기.
- 단조성은 5분위 중앙값 궤적과 중앙값 분할 rho로 검증.
- **causal claim 없음.** 전부 횡단·관측 자료다.

---

## 주요 결과

### 1. B의 두 반례 재현 — 둘 다 재현됨, 단 작은 쪽은 티켓 기술이 불완전하다 [OBSERVATION]

| B의 주장 | 재현 결과 | 일치? |
|---|---|---|
| dom 1657 bytes → primary_action 24 | dom_bytes=1657, n_primary=24 | ✅ 일치 |
| dom 4.7MB → primary_action 17 | dom_bytes=4,778,840 (밴드), n_primary=17 | ✅ 일치 |

**다만 `dom_bytes==1657`은 하나의 관측이 아니라 두 개다.** NH스마트뱅킹(wtg `95967b50…`)과
NH콕뱅크(wtg `fb3d1841…`) — **서로 다른 두 target**이 분석 대상 전 컬럼에서 값이 완전히 동일하다
(dom_element_n 11, dom_interactive_n 0, primary 24, name_sources 67, target_size 24, contrast 26,
scroll 844, gate_text 146, probe_title "NH농협 인터넷뱅킹"). 두 서비스가 같은 랜딩 페이지로
수렴했고, 파이프라인은 이를 독립 관측 2건으로 계수하고 있다.

그리고 이 두 관측이 이 RQ의 핵심 진단을 담고 있다: **`dom_interactive_n==0`인데 probe는
primary_action 24개를 보고한다.** `dom_title`(농협 개인모바일)과 `probe_title`(NH농협 인터넷뱅킹)도
다르다. DOM 아티팩트와 probe가 **같은 페이지 상태를 보고 있지 않다.**

보조 확인: 파싱된 dom.html의 절대 최소는 314 bytes(롯데하이마트)지만 probe가 없다. 즉 B의 1657은
"probe를 가진 관측 중 최소"이고, B의 암묵 grain은 `probe_present==1`이었다. 본 분석도 이를 따랐다.

### 2. dom_bytes는 대리변수가 될 수 없다 [ANALYSIS]

| 대리변수 | Spearman rho (vs primary) | 부트스트랩 CI95 | tau-b | p | n |
|---|---|---|---|---|---|
| **dom_bytes** | **+0.264** | **[−0.024, +0.524]** ← **0 포함** | +0.192 | 0.053 | 54 |
| dom_interactive_n | +0.780 | [+0.604, +0.894] | +0.625 | 3.4e−12 | 54 |
| dom_element_n | +0.707 | [+0.504, +0.848] | +0.545 | 2.3e−09 | 54 |
| dom_a_href_n | +0.761 | [+0.577, +0.882] | — | 2.4e−11 | 54 |
| dom_body_text_len | +0.123 | [−0.190, +0.416] ← 0 포함 | +0.078 | 0.377 | 54 |
| probe_bytes | +0.954 | [+0.897, +0.978] | +0.837 | 6.6e−29 | 54 | ← **순환참조** |

`dom_bytes`는 α=0.05에서 유의하지 않고 CI가 0을 포함한다. **같은 dom.html에서 뽑은 구조적
개수**(interactive/element/anchor)는 강하게 작동하는데 **그 파일의 바이트 크기**는 작동하지 않는다.
문제는 아티팩트가 아니라 바이트라는 요약방식에 있다.

`probe_bytes`가 가장 강한 수치(+0.954)지만 이는 **세는 대상 배열 자체의 직렬화 크기**라 결과를
동어반복한 것이다. 사용 불가로 **배제**하기 위해서만 보고한다. `ax_bytes`(+0.734)도 접근성 트리가
신호와 겹쳐 준-순환이다.

### 3. 크기와 품질의 관계는 비단조다 — 역U자 [ANALYSIS]

`dom_bytes` 5분위별 primary_action 중앙값 (n = 11/11/10/11/11):

```
Q1        Q2        Q3        Q4        Q5
24   →    74   →    90   →    60   →    40
                     ▲ 정점, 이후 하락
```

`dom_interactive_n` 5분위 (같은 n):

```
11   →    31   →    50   →    74   →   200      (엄격 증가)
```

중앙값 분할(median = 150,172 bytes): 하위 절반 rho = **+0.453** (n=27, p=0.018), 상위 절반
rho = **−0.034** (n=27, p=0.867). 즉 상관계수 +0.264는 **관계를 과장한 것이 아니라 과소평가한
것**이다 — 단조 관계 자체가 성립하지 않는다.

**메커니즘 [ANALYSIS, 시사적]**: `bytes_per_element`(구조 노드당 마크업 무게)는 풍부도와
**음의** 관계다 (rho = −0.275, p = 0.044, n=54). 노드당 가장 무거운 8개 문서는 전부 미디어/SPA
셸이다 — 밴드 2330 B/elem, YouTube 2159, Instagram 1717, Netflix 1575. 이들의 바이트는
inline script/JSON payload이지 상호작용 구조가 아니다.

> ⚠️ 단, 이 음의 상관은 부트스트랩 CI95 = [−0.523, **+0.008**]로 0을 아슬아슬하게 포함한다.
> **효과추정치가 아니라 메커니즘 예시로만** 제시한다.

큰 dom_bytes는 **정반대 두 체제**에서 발생한다 — (a) 실제로 거대한 커머스 DOM, (b) 상호작용
마크업이 거의 없는 script-heavy 셸. 그래서 크기가 풍부도에 대해 비단조인 것이다.

### 4. "신호 풍부도"는 4차원이 아니라 사실상 1차원이다 [ANALYSIS]

4개 신호 간 Spearman은 모두 **≥ 0.83**. 특히 `n_primary_action_candidates`와 `n_target_size`는
**rho = 0.999**이고 **54건 중 30건에서 값이 정확히 같다**. 다른 경우에도 항상
target_size ≥ primary다. 두 신호는 사실상 **같은 후보집합을 cap만 달리해(200 vs 300) 자른 것**이다.

→ 대리변수는 4가지를 맞출 필요가 없다. 하나만 맞추면 된다. 동시에 4개 컬럼에 대한 다중검정
보정은 의미가 없다 (독립 검정이 아니다).

### 5. cap 도달 — 절반은 판별 가능, 절반은 NOT_TESTABLE [ANALYSIS]

주 grain 54건의 cap 도달: `cap_any` 14 · name_sources 13 · contrast 8 · primary 7 ·
target_size 6 · body_text_4000 7 · motion_animated_60 1.

**판별 가능한 절반 (SUPPORTED — cap은 페이지 풍부도가 원인이다)**: probe와 **독립적인 경로로**
수집된 DOM 아티팩트가 이를 증언한다.

| 비교 | capped (n=14) 중앙값 | uncapped (n=40) 중앙값 | A12 | p |
|---|---|---|---|---|
| dom_interactive_n | 395 | 59.5 | **0.917** | 4.2e−06 |
| dom_element_n | 2800 | 549 | **0.904** | 8.5e−06 |
| dom_bytes | 306,868 | 109,808 | 0.693 | 0.034 |

dom.html은 probe 배열과 별도 경로로 수집되므로 이 증거는 순환이 아니다.

**판별 불가능한 절반 (NOT_TESTABLE)**: 버려진 꼬리가 **판정을 바꿨을 정보**를 담고 있었는지는
개수만으로 결정할 수 없다. 테이블은 절단된 개수만 저장하고 버려진 항목은 저장하지 않는다.

다만 **손실량의 하한은 계량 가능하다**: primary가 cap(200)에 걸린 7건에서
`dom_interactive_n / 200`은 **1.73× ~ 6.79× (중앙값 2.81×)**. 즉 probe는 DOM이 가진 상호작용
요소의 **15%~58%만** 보고했다.

> **결론: 두 해석이 동시에 참이다.** cap 도달은 정보가 **풍부한** 페이지를 표시하는 **동시에**
> 정보를 **잃은** 측정을 표시한다. 단일 스칼라 "품질" 방향이 아니다.

**비대칭 주의**: 가장 자주 걸리는 cap인 `accessible_name_sources`(13/54)는 **유일하게 visible
필터가 없는** 신호다. 사용자가 지각 가능한 요소가 아니라 raw 노드 수로 절단되므로, 이 cap-hit은
"사용자 대면 풍부도"로 해석하기가 가장 어렵다.

### 6. 포착률(capture ratio)은 실패한다 — 이 RQ의 핵심 음성 결과 [ANALYSIS]

정의: `n_primary_action_candidates / dom_interactive_n`. 정의됨 52/54, 중앙값 0.571,
범위 0.067 ~ 11.0. 세 가지 독립적 이유로 실패한다:

1. **가장 필요한 곳에서 정의되지 않는다.** `dom_interactive_n==0`인 NH 2건 — DOM과 probe가
   실제로 불일치하는 바로 그 관측들이다.
2. **분자가 선택적 부분집합이다.** primary action은 visible 필터를 거친 *선별* 집합이지 전체
   상호작용 요소 열거가 아니다. 따라서 ratio < 1은 **정상 동작**이지 포착 실패가 아니다.
   중앙값 0.571을 "43% 놓침"으로 읽을 수 없다.
3. **탐지해야 할 절단에 의해 스스로 왜곡된다.** cap 200이 분자를 고정하는 동안 분모는 계속
   자라므로, **가장 풍부한 페이지가 가장 낮은 점수를 받는다** — 코스트코 0.147, 메가커피 0.151.

추가로 ratio > 1이 4/52 (최대 11.0, 모니모)인데 이는 **클라이언트 hydration**을 뜻한다 — probe가
서빙된 dom.html에 없는 요소를 정당하게 본 것이다. 즉 이 비율은 hydration과 censoring을 **부호가
반대인 채로** 한 숫자에 섞는다.

### 7. "같은 페이지 상태인가" 후보는 수집기 결함에 오염돼 있다 [OBSERVATION]

`dom_title != probe_title`이 **9/54**. 그러나 그중 **6건은 mojibake**다 — dom_title이
Latin-1 supplement 문자만 있고 한글이 0자인 반면 probe_title은 정상 한글이다
(예: `KB Pay ìë´` vs `KB Pay 안내`, `ììì íµ` vs `서원유통`). **dom.html의 title이
잘못된 코덱으로 디코드되고 있다** — 페이지가 다른 게 아니다.

진짜 상태 불일치는 **3/54**뿐이다: NH 2건(dom_body_empty=1, interactive=0, probe는 24개 관측) +
11번가. `probe_url == probe_final_url`은 54/54라 리다이렉트는 원인이 아니다.

→ 후보 (b)는 **현 상태로 사용 불가**이며, 이 인코딩 결함 자체가 수집기에 보고할 발견이다.

### 8. 재검사 신뢰도 — 크기가 개수보다 덜 안정적이다 [OBSERVATION]

2회 실행된 4 target:

| target | dom_bytes 2회 | 동일? | 4신호 벡터 동일? |
|---|---|---|---|
| Netflix | 675,876 / 677,082 | ✗ | ✗ (name_sources 50 vs 51만 상이) |
| Chrome | 536,881 / 536,881 | ✓ | ✓ |
| 현대카드 | 107,417 / 107,403 | ✗ | ✓ |
| 캐시워크 | 156,676 / 156,630 | ✗ | ✓ |

`n_primary_action_candidates`는 **4/4 정확 재현**. 4신호 전체 벡터는 3/4 재현이며, 어긋난
유일한 신호는 **visible 필터가 없는** name_sources다. `dom_bytes`는 **3/4에서 불일치**.
→ 크기는 타당성이 낮을 뿐 아니라 **재현성도 더 낮다**. (단 n=4 쌍이라 방향성 참고용일 뿐,
신뢰도 계수를 산출할 수 없다.)

---

## 대리변수 후보 평가표

| 후보 | 정의 | 계산 가능? | 관측된 관계 (n=54) | 실패 사례 | 권고 |
|---|---|---|---|---|---|
| **dom_bytes** | dom.html 바이트 | 예 54/54 | rho +0.264, **CI [−0.024,+0.524] 0 포함**; 비단조 24/74/90/60/40 | 11번가 16.6KB→138 ; 밴드 4.78MB→17 | **사용불가** |
| **dom_interactive_n** | DOM 상호작용 요소 수 | 예 54/54 | rho **+0.780** [+0.604,+0.894]; name_sources 대비 +0.846; 5분위 엄격증가; 5개 민감도 부분집합 전부 안정 | hydration 페이지(11번가 23→138, 마켓컬리 28→155, 모니모 1→11); NH 2건에서 0 | **권고** (rank 수준 한정) |
| dom_a_href_n | anchor[href] 수 | 예 54/54 | rho +0.761 / +0.837 | 위와 동일 | 조건부 (동등 대체재, 이점 없음) |
| dom_element_n | 전체 요소 수 | 예 54/54 | rho +0.707 [+0.504,+0.848] | 밴드 2051 요소 → 17 | 조건부 (interactive보다 약함) |
| bytes_per_element | dom_bytes / element_n | 예 54/54 | rho **−0.275** (p=0.044) 단 CI [−0.523,+0.008] 0 포함 | 풍부도 척도가 아님 | 조건부 — **bloat 플래그로만** |
| cap_any | 배열 절단 여부 | 예 54/54 | 14/54; capped 중앙값 interactive 395 vs 60 (A12 0.917) | 의미가 양방향 | 조건부 — **censoring 플래그**, 품질점수 아님 |
| probe_bytes | probe payload 크기 | 예 54/54 | rho +0.954 [+0.897,+0.978] | **순환** — 세는 배열의 직렬화 | 사용불가 (실패가 아니라 순환) |
| ax_bytes / css_bytes | 형제 아티팩트 크기 | 예 54/54 | +0.734 / +0.701 | ax는 준-순환, css는 프레임워크 무게 | 비권고 |
| dom_body_text_len | 가시 텍스트 길이 | 예 54/54 | rho +0.123 [−0.190,+0.416] | 기사형=길고 희박, 커머스=짧고 조밀 | **사용불가** |
| **capture_ratio** | primary / dom_interactive_n | **아니오 — 2/54 미정의** | 중앙값 0.571, 범위 0.067~11.0; cap에 의해 왜곡 | 코스트코 0.147·메가커피 0.151이 **가장 풍부해서** 최하점 ; 모니모 11.0은 hydration | **스칼라로 사용불가** — hydration 플래그(>1)와 censoring 플래그(cap_any)로 **분해**하라 |
| dom_title == probe_title | DOM/probe 동일상태 검사 | 예, 단 **오염** | 9/54 불일치, 그중 6건이 mojibake | dom_title 디코딩 결함 6/54 | **인코딩 결함 수정 전까지 사용불가** |
| **dom_body_empty==0 AND dom_interactive_n>0** | 최소 DOM 사용성 게이트 | 예 54/54 | NH 2건을 정확히 배제 — DOM과 probe가 실증적으로 다른 상태인 유일한 행들 | 부분 hydration은 못 잡음 (11번가는 통과하나 DOM이 6배 과소) | **게이트로 권고** (점수 아님), dom_interactive_n과 병용 |

---

## 민감도 분석

`n_primary_action_candidates` 대상 Spearman rho:

| 부분집합 | n | dom_bytes | dom_interactive_n |
|---|---|---|---|
| 주 grain (in_mart & probe) | 54 | +0.264 | +0.780 |
| 대체 grain (probe_present) | 58 | +0.212 | +0.785 |
| uncapped only | 40 | +0.123 | +0.754 |
| body-nonempty only | 52 | +0.236 | +0.785 |
| 최대 dom_bytes 제외 | 53 | **+0.310** CI [+0.012,+0.560] ← 0 배제 | +0.777 |
| ITEM_DETAIL 내부 | 25 | **+0.520** CI [+0.111,+0.802] ← 0 배제 | +0.708 |

**두 grain에서 결론이 바뀌지 않는다** (dom_bytes +0.264 vs +0.212 ; dom_interactive_n
+0.780 vs +0.785). cap 상태·body 공백 여부에서도 dom_bytes는 약하고 CI가 0을 포함한다.

> ### ⚠️ 자기 반증: dom_bytes의 CI가 0을 배제하는 부분집합이 **두 개 있다**
>
> 방법론 지시 #7(능동적 반례 탐색)에 따라 **우리 자신의 판정에 대한 반례를 보고한다.**
>
> - **ITEM_DETAIL만** (n=25): rho **+0.520**, CI [+0.111, +0.802] — 0 배제
> - **4.78MB 극단점 제외** (n=53): rho **+0.310**, CI [+0.012, +0.560] — 0 배제
>
> **이것이 dom_bytes를 구제하지는 않지만, 왜 실패하는지를 더 날카롭게 만든다.** 두 부분집합은
> 모두 **아키타입 이질성을 제거**하는 방식으로 작동한다 — ITEM_DETAIL은 동질적 커머스이고,
> 제거된 점은 가장 극단적인 SPA 셸 하나다. 이는 §3에서 제시한 **2체제 메커니즘 그대로**다:
> script-heavy 셸과 진짜로 거대한 커머스 DOM을 **한데 섞는 것**이 단조성을 파괴한다.
>
> 그리고 **두 부분집합 모두에서 dom_bytes는 동일 행의 dom_interactive_n보다 여전히 명백히
> 약하다** (0.520 vs 0.708 ; 0.310 vs 0.777)이며 두 CI 모두 매우 넓다.
>
> → 따라서 REFUTED 판정은 **production이 실제로 하게 될 pooled·cross-archetype 사용**에 대해
> 유효하며, 고정 아키타입 내부에서는 **뒤집히는 것이 아니라 한정(qualified)된다.**

**Pearson 대조 (방법론 주석)**: dom_bytes raw Pearson r = 0.096, log10 변환 후 r = 0.299,
Spearman = 0.264. dom_bytes는 1.66e3 ~ 4.78e6로 3.5 오더에 걸쳐 있고 4.8MB 점 하나가 raw
Pearson을 지배한다. **Pearson만 보고했다면 어느 방향으로든 오도했을 것**이며, 이것이 Spearman을
주 통계량으로 쓴 이유다.

**아키타입 층화**: cap 도달 14건 중 11건이 ITEM_DETAIL(n=25), 2건이 QUERY(n=4)에 몰린다.
반면 CONTENT_OPEN(중앙값 466KB)과 COMMUNICATION_ENTRY(396KB)는 dom_bytes 중앙값이 가장
큰데 primary 중앙값은 가장 낮다(11, 23.5). **절단이 어디서 일어나는지를 결정하는 것은 크기가
아니라 아키타입이다.**

---

## 반례 (능동 탐색 결과)

- **dom_bytes**: 양방향 반례 다수. 11번가 16.6KB(Q1)에서 primary 138 + name_sources 300 cap
  도달 ; 밴드 4.78MB(287배 큼)에서 17, cap 0건. Instagram 640KB→5, YouTube 466KB→8.
  상위 구간 전체에서 바이트 순서가 풍부도 순서를 **역전**시킨다.
- **dom_interactive_n**: 반례 **존재하며 진단 가능**하다. hydration 방향 — 11번가 23→138,
  마켓컬리 28→155, 모니모 1→11 (전부 capture_ratio > 1). 반대 방향 — 신세계백화점
  341→23 (ratio 0.067, visible 필터가 대부분 노드를 정당하게 기각). NH 2건에서는 0이라
  틀렸다기보다 **무정보**다. → 좋은 **rank 수준** 대리변수이지 점 예측기가 아니다.
- **capture_ratio**: 코스트코·메가커피가 가장 풍부해서 최하점을 받는 구조적 반례.
- **우리 자신의 판정에 대한 반례 — 발견됨**: "dom_bytes는 CI가 0을 배제하는 부분집합을 갖지
  않는다"는 주장은 **거짓으로 판명됐다.** grain 2종, cap 상태, body 공백 여부, 극단점 제거,
  최대 아키타입에 걸쳐 탐색한 결과 **두 부분집합에서 CI가 0을 배제한다** — ITEM_DETAIL
  (n=25, rho +0.520 [+0.111,+0.802])과 4.78MB 극단점 제외(n=53, rho +0.310 [+0.012,+0.560]).
  위 민감도 절의 경고 박스에 전문을 기록했다. 두 경우 모두 동일 행의 dom_interactive_n보다
  약하며, 판정은 pooled 사용에 대해 유지되고 층 내부에서는 한정된다.

---

## VERDICT

| 주장 | 판정 | 근거 |
|---|---|---|
| dom_bytes는 관측 품질의 대리변수다 | **REFUTED** (pooled 한정) | 아키타입 통합: rho +0.264, n=54, CI95 [−0.024,+0.524]가 0 포함 ; 5분위 역U자 비단조(24/74/90/60/40). **범위 주석**: ITEM_DETAIL 내부(n=25)에서는 rho +0.520 CI [+0.111,+0.802]로 0을 배제하므로, 이 반증은 production이 실제로 할 **pooled 사용**에 적용되며 모든 층에 적용되는 것은 아니다. 그 층에서도 dom_interactive_n(+0.708)에 진다 |
| 측정 가능한 신호 풍부도 대리변수가 존재한다 | **PARTIALLY_SUPPORTED** | dom_interactive_n rho +0.780 [+0.604,+0.894], 5분위 엄격증가, 5개 민감도 부분집합 안정 — 단 hydration 반례와 empty-body 무정보 때문에 rank 수준 한정 |
| 포착률이 크기보다 나은 대리변수다 | **NOT_SUPPORTED** | 2/54 미정의, cap censoring과 hydration이 부호 반대로 혼입, 분자가 선택적 부분집합이라 척도 해석 불가 |
| cap 도달이 풍부/손실 중 무엇인지 구분 가능하다 | **PARTIALLY_SUPPORTED / NOT_TESTABLE** | 풍부도 원인은 probe-독립 DOM 증거로 SUPPORTED (A12 0.917). 손실 정보량은 버려진 항목이 저장되지 않아 NOT_TESTABLE — 하한(1.73×~6.79×)만 도출 가능 |

---

## Limitations

- n=54 target. 모든 CI가 넓다. **rho 차이 0.15 이하는 분해되지 않는다.**
- target당 실행 1회(중복 4건 제외)라 실행간 분산이 사실상 미측정이다. 4쌍은 방향성 참고용.
- **"관측 품질"을 신호 풍부도(probe가 얼마나 기록했는가)로 조작화했다. 이는 측정
  정확성(correctness)이 아니다.** 기록된 신호가 옳은지는 여기서 전혀 검증하지 않았다 —
  그것은 gold label이 필요하며 본 RQ에서는 의도적으로 열지 않았다.
- 결과변수 자체가 14/54에서 **우측 절단**돼 있어 보고된 모든 rho가 감쇠(attenuate)된다.
  참 |rho|는 보고값보다 클 가능성이 높다.
- 4개 신호가 사실상 1차원(비대각 rho ≥ 0.83, primary vs target_size 0.999)이라 4개 컬럼은
  독립 검정이 아니며 다중성 보정이 무의미하다.
- dom.html은 서빙된 응답이고 probe는 hydration 이후 실행이다. 둘이 같은 DOM을 기술한다는
  보장이 없으며, 이것이 **모든 DOM 기반 대리변수의 원리적 상한**이다.
- `bytes_per_element` 음의 상관은 CI가 0을 포함하므로 "markup bloat" 설명은 그럴듯하되
  확립된 것이 아니다.
- **dom_bytes 반증은 pooled·cross-archetype 사용으로 범위가 한정된다.** ITEM_DETAIL 내부
  (n=25)에서는 CI가 0을 배제하며(+0.520 [+0.111,+0.802]), 4.78MB 점 제거 시에도 그렇다
  (+0.310 [+0.012,+0.560]). 두 CI 모두 넓고 동일 행의 dom_interactive_n보다 낮지만, 단일
  아키타입으로 한정해 읽는 독자는 dom_bytes를 순수 잡음으로 취급해서는 안 된다.
- 횡단·관측 자료. **어떤 인과 주장도 하지 않으며 지지되지 않는다.**

---

## Production Implications

1. **[IMPLEMENTATION] `dom_bytes`(및 모든 아티팩트 바이트 크기)를 수집 건전성 체크나 triage
   정렬키로 쓰지 마라.** 풍부도에 대해 비단조라서 밴드(4.78MB, 17 actions)를 11번가(16.6KB,
   138 actions)보다 위로 정렬한다.
2. **[IMPLEMENTATION] 관측 인정 전 `dom_body_empty==0 AND dom_interactive_n>0` 게이트를 걸어라.**
   DOM 아티팩트와 probe가 서로 다른 페이지 상태를 기술하는 NH 2건을 정확히 잡아낸다.
3. **[IMPLEMENTATION] 서로 다른 두 target(NH스마트뱅킹·NH콕뱅크)이 byte-identical 관측을
   생성했다.** wtg만이 아니라 **측정 벡터로도 중복제거**하라. 아니면 모든 집계에서 이중계수된다.
4. **[IMPLEMENTATION] `dom_title`이 6/54에서 오디코드된다** (Latin-1 supplement 바이트, 한글 0자,
   반면 probe_title은 정상). dom.html 읽기 시점의 charset 처리를 고쳐라. 그 전까지 dom_title
   기반 비교는 어느 것도 신뢰할 수 없다.
5. **[IMPLEMENTATION] cap이 14/54에서 걸리고, DOM은 200-cap이 허용하는 것보다 1.73×~6.79× 많은
   상호작용 요소가 존재한다고 말한다.** 각 배열 옆에 `truncated=true` 플래그와 **절단 전 총계**를
   같이 저장하라. 그래야 하위 소비자가 "정확히 200"과 "최소 200"을 구분할 수 있다.
6. **[IMPLEMENTATION] `cap_accessible_name_sources`(300)는 가장 자주 걸리면서 유일하게 visible
   필터가 없는 신호다.** 나머지 3개와 같은 필터를 적용해 cap-hit의 의미를 통일하는 것을 검토하라.
   (재검사에서 유일하게 불안정했던 신호이기도 하다.)
7. **[OBSERVATION] B가 티켓에서 보고하지 않은 절단점 3개는 이론이 아니라 실제로 발동 중이다** —
   본 grain에서 `cap_body_text_4000` 7/54, `cap_motion_animated_60` 1/54. motion `body *`
   slice(3000)를 포함해 동일한 truncation-flag 처리 대상에 넣어야 한다.

---

## 추가 연구질문

1. `dom_interactive_n`이 단순 신호 개수가 아니라 **판정 안정성**을 예측하는가? gold label이
   필요하므로 본 RQ 설계상 범위 밖이다.
2. cap을 5배로 올려 capped 관측을 재수집하면 **추가된 꼬리가 판정을 바꾸는가?** cap 질문의
   NOT_TESTABLE 절반을 검정 가능하게 만드는 유일한 경로다.
3. dom.html을 fetch 시점뿐 아니라 **probe 시점에도** 캡처해 hydration lag를 직접 계량하라.
   현재 `capture_ratio > 1`(4/54)이 유일한 대리 지표다.
4. target당 ≥5회 실행으로 각 신호의 **재검사 신뢰도 계수**를 추정하라. 현재 4쌍은 정확 일치
   여부만 보여줄 뿐이다.
5. `bytes_per_element`가 그 자체로 **SPA/셸 분류기**로 쓸 만한가? bloat 상위 8개가 전부
   미디어/SPA 앱이라 깨끗한 threshold가 있을 가능성을 시사한다.

---

## 산출물

| 파일 | 내용 |
|---|---|
| `tools/rq_d9_quality_proxy.py` | 재현 스크립트 (입력=CSV 1개, hidden state 없음, 35초) |
| `results/RQ_D9_quality_proxy.json` | machine-readable 전체 수치 |
| `figures/RQ_D9_dom_bytes_vs_signal.png` | dom_bytes vs primary (log-x), cap 구분, 반례 주석 |
| `figures/RQ_D9_proxy_forest.png` | 후보별 rho + 부트스트랩 CI forest plot |
| `figures/RQ_D9_monotonicity.png` | 5분위 중앙값 궤적 — 비단조 대 단조 |
