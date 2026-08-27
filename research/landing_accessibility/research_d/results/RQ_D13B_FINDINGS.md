# RQ-D13b — 강제 dismissal 은 실제로 무엇을 바꿨는가

**verdict**: `PARTIALLY_SUPPORTED` — "픽셀 무변화 = 무효과" 는 **64.6% 만 맞다**.
**파생 근거**: RQ-D13 F4 (`screen_before == screen_after` 82/248 steps)
**재현**: `.venv/bin/python research_d/tools/rq_d13b_dismissal_effect.py`
**산출**: `results/RQ_D13B_dismissal_effect.json`

---

## RQ

RQ-D13 F4 에서 강제 dismissal step 의 **33.1%(82/248)** 가 화면을 바꾸지 않았다. 그때 나는
"화면이 안 바뀌었다 가 곧 dismissal 이 실패했다 는 아니다" 라고 유보했다. 그 유보를 DOM 수준에서
정량화한다.

A 가 22:43 에 `D-R0-72 OverlayCoverage 겹침≠방해` 를 construct decision 으로 냈다. dismissal
에도 같은 형태의 질문이 있다 — **"화면이 안 바뀌었다" 와 "치우지 못했다" 는 같은가?**

## 방법과 그 가정 (먼저 밝힌다)

- l0c 슬롯에는 `dom_before` 가 **없다**. step *k* 의 before DOM 을 step *k−1* 의
  `dom_after.html`(step 0 은 `l0a/dom.html`)로 **대용**했다. 이 대용이 틀리면 delta 해석이 바뀐다.
- DOM 동일성 판정 기준은 **`dom_after.html` 의 sha256 바이트 동일성**이다.
  `element_n`·`interactive_n`·`body_text_len` 같은 요약치는 **CSS/class 토글을 보지 못한다**.
  실제로 **sha 기준과 요약치 기준이 248 step 중 12건에서 갈렸다** — 요약치로 판정했다면 그 12건을
  잘못 분류했을 것이다. 요약치 결과는 `dom_same_by_summary` 로 병기해 남겼다.

---

## F1 (OBSERVATION) — 픽셀 무변화 82건 중 **29건(35.4%)은 DOM 이 바뀌었다**

분모: 평가 가능한 248 step (전체 249 중 1건은 DOM 부재).

| 분류 | n | 뜻 |
|---|---|---|
| **H1_NO_EFFECT** | **53** | 픽셀·DOM 바이트 **둘 다** 무변화 |
| **H2_DOM_ONLY** | **29** | 픽셀은 같은데 DOM 바이트가 바뀜 |
| 픽셀 무변화 소계 | **82** | RQ-D13 F4 와 정확히 일치 (독립 재현) |
| H4_PIXEL_ONLY | 37 | 픽셀은 바뀌었는데 DOM 바이트 동일 |
| EFFECTIVE | 129 | 둘 다 바뀜 |

**"픽셀 무변화 = 무효과" 는 53/82 = 64.6% 만 맞다.** 35.4% 는 DOM 이 실제로 바뀌었고
화면에만 안 나타난 것이다(뷰포트 밖 변화, 시각적으로 동일한 재배치 등).

역방향도 있다: **H4_PIXEL_ONLY 37건**은 픽셀이 바뀌었는데 DOM 바이트는 같다. 같은 DOM 에서
픽셀이 달라지는 것은 애니메이션·미디어·지연 렌더·스크롤 위치 차이로 설명된다. 즉
**픽셀과 DOM 은 서로를 대체하지 못한다.** 어느 한쪽만 보면 37+29 = 66/248 (26.6%) 를 잘못 읽는다.

## F2 (OBSERVATION) — 모든 step 이 무효과인 target 은 **3/50**

RQ-D13 F4 는 픽셀 기준으로 6/50 이라고 했다. DOM 바이트를 함께 보면 **3/50** 로 줄어든다.
나머지 3건은 어느 step 에선가 DOM 이 바뀌었다.

## F3 (ANALYSIS) — `forced_dismissal_count` 의 의미가 정해져 있지 않다

세 가지 서로 다른 수가 가능하다.

| 정의 | 값 | 분모 |
|---|---|---|
| dismissal 을 **시도한** 횟수 | 248 | step |
| 화면이 **바뀐** 횟수 | 166 | step |
| **DOM 이 바뀐** 횟수 | 158 (=129+29) | step |
| 픽셀·DOM 둘 다 바뀐 횟수 | 129 | step |

codebook 이 어느 것인지 말하지 않으면 같은 이름의 변수가 최대 **1.9배** 차이난다.
어느 정의가 옳은지는 D 가 정하지 않는다 — construct 결정은 A 의 권한이다.

---

## 반례 / 대안설명 검토

- ***"H1_NO_EFFECT 53건은 dismissal 이 실패한 것"*** → **배제하지 못했다.** H1 은
  "치우지 못했다" 와 **"치울 게 이미 없었다"(H3 ALREADY_GONE)** 를 구분하지 못한다.
  구분하려면 그 step 에서 dismiss 대상 요소가 실재했는지를 확인해야 하는데, l0c 슬롯에는
  step 별 대상 selector 가 없다. → **RQ-D13b-1** 로 이월.
- *"before DOM 대용 가정이 틀렸다"* → 가능하다. step k−1 의 after 와 step k 의 before 사이에
  시간이 흐르고 페이지가 스스로 변할 수 있다. 그 경우 H2_DOM_ONLY 가 과대계상된다.
- *"H4_PIXEL_ONLY 37 은 캡처 타이밍 노이즈"* → 그럴듯하다. 다만 그렇다면 픽셀 비교 자체의
  신뢰도가 낮다는 뜻이고, 그것 역시 F1 의 결론(둘은 서로를 대체 못 한다)을 강화한다.

## Limitations

1. **H1 이 "실패" 와 "대상 없음" 을 구분하지 못한다.** 이 RQ 의 가장 큰 공백이다.
2. before DOM 대용 가정(§방법)이 결과의 전제다.
3. `dom_after.html` 만 봤다. AX 트리 변화는 보지 않았다.
4. 3건은 target 단위 판정이라 n=50 에서 나온 값이고, 비율로 일반화하기엔 작다.
5. **어느 정의가 옳은지 D 는 정하지 않는다.** construct 는 A 의 권한이다.

## Production implication (제안일 뿐. A ADOPT 전에는 implementation candidate 도 아니다)

- **P2**: `forced_dismissal_count` 의 정의를 codebook 에 명시할 것 — 시도/픽셀변화/DOM변화 중 어느 것인가.
- **P2**: 픽셀과 DOM 중 하나만 보는 판정은 26.6%(66/248) 에서 다른 답을 낸다. 둘을 함께 기록할 것.
- **P3**: l0c 에 step 별 dismiss 대상 selector 를 남기면 H1 의 절반(실패 vs 대상없음)을 가를 수 있다.

## 후속 연구질문

- **RQ-D13b-1**: H1_NO_EFFECT 53건에서 dismiss 대상이 그 시점에 실재했는가 — probe 의
  `dismiss_control_candidates` selector 를 step DOM 에 질의해 분리
- **RQ-D13b-2**: H4_PIXEL_ONLY 37건의 픽셀 변화 원인 — 애니메이션/미디어/스크롤 중 무엇인가
