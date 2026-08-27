# RQ-D13b-1 · RQ-D13b-2 — H1_NO_EFFECT 는 무대상이었고, H4_PIXEL_ONLY 는 페이지 자체의 움직임이었다

**verdict**: `SUPPORTED` (H-13b1-ABSENT)
**재현**: `.venv/bin/python research_d/tools/rq_d13b12_dismissal_dom_effect.py`
**산출**: `results/RQ_D13b12_dismissal_dom_effect.json` · `figures/RQ_D13b12_*.png`
**MLflow**: `LA_10_RESEARCH_D` / `RQ-D13b-1_2_dismissal_dom_effect` / run_id `58bfc5624053435f842b98288855f99d` (동일 이름의 선행 3 run 은 `run_status=SUPERSEDED`)
**노트북**: `notebooks/d_research/RQ_D13b12_dismissal_dom_effect.ipynb` (Restart → Run All · code cell 21 · 에러 0 · 저장본과 assert 대조 통과)
**claim_kind**: OBSERVATION + ANALYSIS · **authority**: NON_CANONICAL (D)

---

## 0. 원 정의를 먼저 박는다 (재정의하지 않았다)

선행 `research_d/tools/rq_d13b_dismissal_effect.py` 원문 그대로:

| 이름 | 원 정의 (코드 인용) |
|---|---|
| `pixel_same` | `v["before"] == v["after"]` — manifest 의 `l0c/{k}/screen_before.png` · `screen_after.png` sha256 동일성 |
| `dom_same` | `cur_sha is not None and prev_sha is not None and cur_sha == prev_sha` — step *k* 의 `dom_after.html` sha256 이 step *k−1* 의 것과 같은가 (step 0 은 `l0a/dom.html`) |
| `H1_NO_EFFECT` | `if pixel_same and dom_same` |
| `H2_DOM_ONLY` | `elif pixel_same and not dom_same` |
| `H4_PIXEL_ONLY` | `elif not pixel_same and dom_same` |
| `EFFECTIVE` | `else` |

**재정의 없음.** 같은 판정식을 독립 재구현해 수치를 먼저 재현했고
(`replication_of_prior_rq.exact_match = true`), 그 위에만 새 측정을 얹었다.
DOM 변화 기준을 바꾼 결과는 §5 에 C1~C5 로 **병기**하며 C1_BYTES 가 원 정의다.

프롬프트가 가설로 준 수치(H1 53 · H4 37)는 **원본에서 그대로 확인됐다.**

## 1. 분모 체인

```
run_dir 60          (manifest.jsonl 을 가진 봉인 run_dir 만 센다)
 └ l0c 있는 run_dir 54
    └ dismissal 시도 step        249
       └ 분류 가능(dom_after 존재)  248     ← 1건 소실: dom_after.html 부재
          └ probe 매핑 가능        248     ← 0건 소실
```

`l0a/probe.json` 이 없는 관측 2건은 **l0c step 도 0건**이라 분모에서 이미 빠져 있다.
따라서 RQ-D13b-1 의 분모는 손실 없이 248 이다.

| 분류 | n | 선행 RQ-D13b |
|---|---|---|
| EFFECTIVE | 129 | 129 ✓ |
| H1_NO_EFFECT | **53** | 53 ✓ |
| H2_DOM_ONLY | 29 | 29 ✓ |
| H4_PIXEL_ONLY | **37** | 37 ✓ |

---

## 2. RQ-D13b-1 — 답: **누를 것이 없었다**

### 2.1 이 측정이 무엇인지

`interrupt_index` 는 `probe.raw_features.modal_overlay_candidates` 의 enumerate 인덱스이고
`l0c/{interrupt_index}/` 가 그대로 step 디렉터리다 (exact SHA `2281c85` 의 `l0_collector.py`
`_build_interrupts` / `_dismiss_pass`). 그래서 **step k ↔ probe 후보 k 가 1:1** 이고,
그 후보의 selector 로 `dismiss_control_candidates` 를 조인하면 **engine 이 그 step 에서
무엇을 누를 수 있었는지** 가 그대로 복원된다. 전 249 step 에서 인덱스 불일치 0 · 조인 실패 0.

### 2.2 H1_NO_EFFECT 53건의 대상 실재 funnel

| 단계 | k / n | p | Wilson95 |
|---|---|---|---|
| (a) dismiss control 후보가 **존재** | 15 / 53 | 28.3% | [18.0%, 41.6%] |
| (b) **hittable** 한 control 이 있음 | **1 / 53** | 1.9% | [0.3%, 9.9%] |
| (c) engine 기준 **visible**(=클릭 대상) | **1 / 53** | 1.9% | [0.3%, 9.9%] |
| control 이 **아예 0개** | 38 / 53 | 71.7% | [58.4%, 82.0%] |
| `<dialog>` 요소 | 0 / 53 | 0% | [0%, 6.8%] |

engine 이 실제로 밟은 경로: **ESCAPE_KEY 38 · CONTROL_CLICK_NOT_HITTABLE 14 · CONTROL_CLICK 1.**

즉 H1_NO_EFFECT 53건 중 **52건(98.1%)은 engine 이 클릭할 대상이 없어서 Escape 를 누르거나
hittable 하지 않은 요소를 향해 클릭을 시도한 것**이다.

### 2.3 유일한 반례 1건도 무대상이었다

(c) 를 통과한 단 1건(CJ온스타일 · `header#header` · control `div#smart-banner>…`)은
**step 실행 시점의 DOM 에 그 control 이 없었다** (`control_in_dom_before_step = 0`).
probe 는 l0a 시점이므로, 이 사례조차 "대상이 있었는데 안 닫혔다" 가 아니다.
→ **검증 가능한 "대상 실재 + 무효과" 사례는 0 / 53.**

### 2.4 대조: EFFECTIVE 에서는 대상이 있었다

| 분류 | n | (c) 클릭 가능한 대상 보유 |
|---|---|---|
| H1_NO_EFFECT | 53 | **1.9%** [0.3, 9.9] |
| H4_PIXEL_ONLY | 37 | 2.7% [0.5, 13.8] |
| H2_DOM_ONLY | 29 | 10.3% [3.6, 26.4] |
| EFFECTIVE | 129 | **33.3%** [25.8, 41.9] |
| 전체 | 248 | 19.4% [14.9, 24.7] |

무효과 쪽과 유효 쪽의 차이는 "잘 눌렀는가" 가 아니라 **누를 것이 있었는가** 다.

### 2.5 "이미 사라져서" 는 아니다

step 직전 DOM 에 overlay 컨테이너가 실재했는가를 selector 재질의로 직접 쟀다.

| | overlay 존재(직전) | overlay 존재(직후) | step 이 제거함 |
|---|---|---|---|
| H1 | 50/53 (94.3%) | 50/53 | **0/53** |
| H4 | 35/37 (94.6%) | 35/37 | 0/37 |
| EFFECTIVE | 124/129 (96.1%) | 117/129 (90.7%) | 9/129 (7.0%) |

**overlay 는 거기 있었다. 없었던 것은 그것을 닫을 컨트롤이다.**

### 2.6 무대상을 만든 것은 "overlay 후보" 의 정체다

`l0_probe.js` 는 `dialog` / `role=dialog` / `aria-modal` 뿐 아니라
**`position:fixed|sticky` 이거나 `z-index>=100` 인 모든 요소**를 overlay 컨테이너로 잡는다.
H1 53건의 selector 루트 태그: `div` 32 · `header` 5 · `nav` 4 · `html` 3 · `form` 2 ·
`ul`(스킵메뉴) 1 · `main` 1 · `button` 1. mart 의 `final_label` 은 `UNKNOWN` 32 · `BANNER` 9.

헤더·GNB·스킵메뉴에는 닫기 버튼이 없다. **"닫지 못했다" 가 아니라 "닫는 것이 아니다".**

### 2.7 왕복검증 — 이건 내 파싱 오류가 아니다

상위계층 결함처럼 보이는 관측이므로 보고 전에 내 오류 가능성을 먼저 배제했다.

| 검사 | 방법 | 결과 |
|---|---|---|
| step index ↔ probe 후보 index | 두 인덱스 집합 비교 | 60 관측 전부 일치, out-of-range 0, 조인 실패 0 |
| engine 산출과 역산 대조 | frozen mart `fact_interrupt_element.json` 의 `dismiss_control_exists` vs 내 재계산 | **234/234 완전 일치** (visible 도 불일치 0) |
| manifest sha 왕복 | manifest sha256 vs 파일 직접 해시 | 248/248 일치, 실패 0 |
| 선행 RQ 재현 | 판정식 재구현 후 분류 카운트 비교 | 4개 분류 전부 일치 |

### 2.8 부수 관측 — `dismiss_succeeded` 는 변화가 아니라 상태를 잰다

픽셀도 DOM 바이트도 **하나도** 안 바뀐 H1 step 중 mart 에 있는 48건에서
`dismiss_succeeded = 1` 이 **30건 (62.5% [48.4, 74.8])** 이다.

engine 의 정의가 `not present or viewport_overlap<=0 or not hittable` 이라
**시도 직후의 상태 술어**이지 **변화 술어**가 아니기 때문이다. overlay 가 원래부터
뷰포트 밖이거나 hit-test 최상위가 아니면 아무 일이 없어도 1 이 된다.
이것이 결함인지 의도된 정의인지는 **construct 판단이며 D 가 정하지 않는다.**

---

## 3. RQ-D13b-2 — 답: 픽셀은 dismissal 이 아니라 **페이지가** 바꿨다

### 3.1 설계

DOM 바이트가 동일한 step 만 남기면 그 안의 대비는 정확히
**H1(픽셀도 동일, 53) vs H4(픽셀만 변함, 37) = 90건**이다 (`sanity_partition = true`).
이 부분모집단에서 "무엇이 픽셀 변화를 예측하는가" 를 잰다.

### 3.2 무조작 대조군을 만들었다

코드상 `screen_after[k−1]` 과 `screen_before[k]` 사이에는 **`dom_after` 캡처밖에 없다.**
조작이 전혀 없는 구간이다. 이 구간의 픽셀 변화 = 페이지 자체 변화의 하한 추정치.

- n = 195 gap · **55.9% [48.9, 62.7] 에서 픽셀이 변한다** · 26.7% 는 1% 넘게 변한다.
- 즉 **아무것도 하지 않아도 화면의 절반 이상이 흔들린다.**

### 3.3 결정적 비교 — 짝지어 보면 차이가 없다

| 비교 | 결과 |
|---|---|
| H4 vs 대조군 (**비짝**) | median 0.004149 vs 0.000144 · CLE 0.728 · **p = 5e-05** |
| H4 내부 **짝지음** (같은 step 의 조작구간 vs 무조작구간) | median 0.004149 vs 0.003204 · 차이 **6.9e-05** · **p = 0.382** |

비짝 비교는 유의하지만 **페이지 정체성이 교란된다** — H4 step 은 원래 잘 흔들리는 페이지에서
나온다. **같은 step 안에서 짝지으면 조작구간이 무조작구간보다 더 변하지 않는다.**
이것이 이 RQ 의 핵심 증거다. 나는 내 가설을 방어하지 않는다: 비짝 결과도 그대로 남긴다.

### 3.4 경쟁가설별 연관 (DOM 바이트 동일 90건, y=1 이 H4)

| 가설 | 예측자 | φ | permutation p | 표 (n11/n10/n01/n00) |
|---|---|---|---|---|
| **ANIMATION** | `infinite_animation>0` | **+0.663** | **5e-05** | 24/2/13/51 |
| ANIMATION | `animated_elements>0` | +0.394 | 3e-04 | 30/22/7/31 |
| ANIMATION | `autoplay_media>0` | +0.096 | 0.563 | 2/1/35/52 |
| **LAZY_RENDER** | `script_n>=20` | +0.418 | 1e-04 | 37/35/**0**/18 |
| LAZY_RENDER | `iframe_n>0` | +0.188 | 0.086 | 21/20/16/33 |
| LAZY_RENDER | `img_n>=20` | −0.067 | 0.660 | 22/35/15/18 |
| DOM_INSENSITIVE | `canvas_n>0 or video_n>0` | +0.379 | 2e-04 | 13/3/24/50 |
| REAL_PIXEL_ONLY | `engine_method==CONTROL_CLICK` | +0.027 | 1.000 | 1/1/36/52 |

`infinite_animation>0` 인 26 step 중 **24 step 이 H4** 다. 무한 애니메이션이 있으면
DOM 이 그대로여도 픽셀은 거의 항상 변한다.

`script_n>=20` 은 `n01=0` — **H4 37건 전부가 스크립트 다량 페이지**다. 필요조건이지
충분조건이 아니다(72건 중 37건만 H4). "무거운 JS 페이지" 표지로만 읽어야 한다.

### 3.5 변화의 위치 — overlay 위가 아니다

| | diff bbox 의 overlay 겹침 중앙값 | 변화가 overlay 에 집중(≥50%) | 전면재도색(변화행 ≥90%) |
|---|---|---|---|
| H4 | **0.000** | 5/37 (13.5%) | 11/37 (29.7%) |
| EFFECTIVE | 0.005 | 31/129 (24.0%) | 20/129 (15.5%) |

H4 의 픽셀 변화는 **치우려던 그 요소 위에서 일어나지 않았다.**

### 3.6 DOM 기준이 둔감했나 — 구조적으로 아니다

C1_BYTES 는 직렬화된 DOM 에 대해 **가장 민감한** 기준이다(inline `style`·`class` 한 글자까지 본다).
더 둔감한 C2~C5 가 H4 를 "변화" 로 뒤집는 일은 **불가능**하고, 실제로 뒤집힘 **0건**이다.
남는 여지는 `page.content()` 가 도달하지 못하는 곳뿐이다:

- iframe 보유율 H4 56.8% vs 전체 56.05% → **기저율 대비 +0.7%p. 몰려 있지 않다.**
- canvas/video 보유는 **몰려 있다** (φ=+0.379, p=2e-04; canvas/video 있는 16건 중 13건이 H4).

→ `PARTIALLY_SUPPORTED`. 다만 canvas/video 는 §3.4 의 애니메이션 지표와 겹쳐,
"둔감" 이라기보다 **"움직이는 콘텐츠는 원래 DOM 에 안 나타난다"** 로 읽는 편이 사실에 가깝다.

### 3.7 픽셀 판정 자체는 건전하다

원 정의는 PNG **바이트** sha256 동일성이다. 실제 픽셀값으로 다시 재봤다:
**248/248 에서 sha 동일 ↔ 픽셀 차이 0 이 정확히 일치**했다(불일치 0건).
PNG 인코딩 차이로 인한 위양성은 없다.

---

## 4. 가설별 판정

| 가설 | 판정 | 근거 한 줄 |
|---|---|---|
| **H-13b1-ABSENT** | **SUPPORTED** | 52/53 (98.1% [90.1, 99.7]) 에서 클릭 가능한 dismiss 대상이 없었다 |
| H-13b1-PRESENT_INEFFECTIVE | **REFUTED** | 1/53, 그 1건조차 step 시점 DOM 에 control 부재 |
| H-13b1-MIXED | **NOT_SUPPORTED** | 한쪽이 98% 다. "섞여 있다" 는 요약이 사실을 가린다 |
| **H-13b2-ANIMATION** | **SUPPORTED** | `infinite_animation>0` φ=+0.663, p=5e-05 (26건 중 24건이 H4) |
| **H-13b2-LAZY_RENDER** | **SUPPORTED** | `script_n>=20` φ=+0.418, p=1e-04. 단 iframe 은 유의하지 않다(p=0.086) |
| H-13b2-DOM_INSENSITIVE | **PARTIALLY_SUPPORTED** | 기준 뒤집힘 0. canvas/video 편중만이 유일한 근거 |
| H-13b2-REAL_PIXEL_ONLY | **REFUTED** | 엄밀 정의 만족 0/37. C1 동일은 속성 토글을 이미 배제한다 |

ANIMATION 과 LAZY_RENDER 는 **서로 배타적이지 않고 이 데이터로 갈리지 않는다.**
둘 다 "dismissal 과 무관한 페이지 자체 변화" 라는 한 가족이며, §3.3 의 짝지음 대조가
그 가족 전체를 지지한다. **둘 중 어느 쪽인지는 이 RQ 가 답하지 못한다.**

---

## 5. 민감도 — 결론 방향은 기준을 바꿔도 유지된다

### 5.1 DOM 변화 기준 5종

| 기준 | H1 | H2 | H4 | EFFECTIVE | C1 과 일치율 |
|---|---|---|---|---|---|
| **C1_BYTES** (원 정의) | 53 | 29 | **37** | 129 | — |
| C2_SUMMARY_COUNTS | 56 | 26 | 46 | 120 | 95.2% |
| C3_STRUCT_HASH | 74 | 8 | 98 | 68 | 66.9% |
| C4_VIS_ATTRS | 60 | 22 | 43 | 123 | 94.8% |
| C5_OVERLAY_SUBTREE | 81 | 1 | 141 | 25 | 46.8% |

- **H4 는 어떤 기준에서도 사라지지 않는다** (37 ~ 141).
- 픽셀↔DOM 연관은 네 기준 모두 양이고 전부 p<0.001:
  C1 φ=0.414 · C3 φ=0.319 · C4 φ=0.451 · C5 φ=0.213. **방향 불변.**
- C3 로 보면 DOM 바이트 변화의 대부분은 **구조 변화가 아니라 속성/텍스트 변화**다
  (구조까지 바뀐 step 은 76/248).
- **C5 가 가장 무거운 관측이다: dismissal 시도 248건 중 222건(89.5%)이
  겨냥한 overlay 의 서브트리를 구조·가시성속성 모두 그대로 남겼다.**

### 5.2 픽셀 임계값

| 픽셀 변화 기준 | H1 | H2 | H4 | EFFECTIVE |
|---|---|---|---|---|
| `frac_any > 0` (= 원 sha 정의) | 53 | 29 | 37 | 129 |
| `frac_gt8 > 0.001` | 63 | 48 | 27 | 110 |
| `frac_gt8 > 0.01` | 74 | 71 | 16 | 87 |
| `frac_gt32 > 0` | 60 | 32 | 30 | 126 |

임계값을 올리면 H4 가 37 → 16 으로 줄지만 **0 이 되지 않는다.**

---

## 6. 반례와 대안설명 (내 결론에 불리한 것부터)

- **"비짝 검정은 H4 가 대조군보다 크다고 말한다"** (p=5e-05) → 맞다. 그래서 짝지음 결과와
  함께 남겼다. 두 결과의 차이는 페이지 간 이질성으로 설명되지만, **짝지음 n=37 은 작다.**
- **"probe 는 l0a 시점이다"** → 가장 무거운 한계다(§7 L1). 다만 engine 자신이 바로 그 l0a
  probe 로 클릭 대상을 골랐으므로, "engine 이 누를 대상을 가지고 있었는가" 에는 정확한 측정이다.
  **"그 시점 페이지에 닫기 버튼이 실재했는가" 라는 더 넓은 질문에는 답하지 못한다.**
- **"dismiss control 탐지 어휘가 좁아서 무대상이 만들어졌다"** → **배제하지 못했다.**
  `l0_probe.js` 는 `CLOSE_WORDS` 정규식 또는 `icon_only` 를 만족하는 요소만 후보로 남긴다.
  어휘를 넓히면 대상이 생기는 overlay 가 있을 수 있다 → RQ-D13b-1b 로 이월.
- **"H4 5건은 변화가 overlay 위에 집중됐다"** → 그렇다. 소수지만 REAL_PIXEL_ONLY 의
  근접 사례로 JSON 에 전수 남겼다. 다만 그중 CONTROL_CLICK 경로는 0건이다.
- **"EFFECTIVE 129건도 대부분 무대상이다"** (클릭 가능 대상 33.3%) → 그렇다.
  **EFFECTIVE 라는 이름이 dismissal 의 효과를 뜻하지 않을 수 있다.** 이 RQ 는 H1/H4 만
  다뤘고 EFFECTIVE 의 인과 귀속은 검사하지 않았다.

---

## 7. Limitations (무거운 순)

1. **L1 (가장 무겁다) probe 시점 불일치** — control 의 존재/가시성/hittable 은 l0a(조작 전)
   probe 로만 잴 수 있다. step k 실행 시점의 실시간 상태가 아니다.
2. **L2 before-DOM 대용** — l0c 에 `dom_before` 슬롯이 없어 step k−1 의 `dom_after.html`
   (첫 step 은 `l0a/dom.html`)로 대용했다. 첫 step 은 사이에 ax/css/screenshot/probe 가 끼어
   시간 간격이 크다.
3. **L3 정적 DOM 에는 layout 이 없다** — 존재는 재확인했으나 visible/hittable 은 못 했다.
4. **L4 selector 재질의 모호성** — probe selector 는 최대 8단계 상대경로라 여러 곳에 매칭될 수
   있다(`match_n` 병기).
5. **L5 iframe 내부·shadow DOM·canvas·video 는 `page.content()` 에 없다** — 어떤 DOM 기준으로도
   보이지 않는다.
6. **L6 `engine_method` 는 의도된 경로**다. 클릭 timeout 같은 실행 예외는 정적으로 알 수 없다.
7. **L7 n=60 관측 · 50 target** — 비율 정밀도가 낮고 target 단위 결론은 특히 약하다.

## 8. 이 RQ 가 답하지 않는 것

**dismissal 대상이 없는 것이 결함인지 정상인지** — 무대상이 접근성 문제인지 측정 설계 문제인지는
construct 판단이며 **A 의 권한**이다. D 는 GO/NO_GO·threshold·수정 지시를 내지 않는다.

## 9. 후속 연구질문

- **RQ-D13b-1a**: overlay 후보를 `candidate_sources` 별로 나누면 무대상 비율이 다른가
  (`dialog/role` 계열 vs `position:fixed|z-index` 계열).
- **RQ-D13b-1b**: `CLOSE_WORDS`/`CLOSE_GLYPH`/`icon_only` 어휘를 넓히면 대상이 생기는 overlay 가
  몇 건인가 — 무대상이 페이지의 사실인지 탐지기의 사실인지 가른다.
- **RQ-D13b-2a**: 무조작 구간 픽셀 변화를 관측 단위 노이즈 기준선으로 삼아 step 별 신호대잡음비를
  정의할 수 있는가.
- **RQ-D13b-2b**: EFFECTIVE 129건도 짝지음 대조로 재검사하면 몇 건이 dismissal 귀속 가능한가.
- **RQ-D13b-2c**: l0c 에 `dom_before` 슬롯이 생기면 H2_DOM_ONLY 29건 중 몇 건이 대용가정의
  산물인가 (수집 재실행 필요 — D 권한 밖).

---

## 표본 (JSON `samples_for_human_verification`)

각 가설의 지지·반박 사례를 실제 `run_dir` / `observation_id` / `step` 과 함께 남겼다.
`H1_all_steps`(53건 전수) · `H4_all_steps`(37건 전수)도 들어 있어 사람이 전수 확인할 수 있다.
모집단 자체가 10건에 못 미치는 칸(PRESENT_INEFFECTIVE 지지 1건, REAL_PIXEL_ONLY 지지 0건)은
그 사실이 곧 판정 근거이며, 조건을 하나씩 푼 근접 사례를 대신 전수로 남겼다.

**확인 방법**: 지지 사례의 `run_dir`/`observation_id` 로
`evidence/<run_dir>/<observation_id>/l0a/probe.json` 을 열어
`raw_features.dismiss_control_candidates` 에서 `container_selector == overlay_selector` 인 항목을
찾으면 `dismiss_control_candidates` 가 비어 있다.

## 방화벽

`D_INPUT_ALLOWLIST.json` 의 denied 목록을 하나도 열지 않았다. 입력은 allowlist 의
`RAW_EVIDENCE_E001` · `FROZEN_MART_E001` · `CODE_AT_EXACT_SHA` · `D_OWN_SCOPE` 뿐이다.
label 생산 없음 · production 수정 없음 · 네트워크 접근 없음.
