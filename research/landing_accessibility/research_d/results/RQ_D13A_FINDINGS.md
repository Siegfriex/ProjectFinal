# RQ-D13a — `max_overlay_coverage` 는 무엇을 재고 있는가

**verdict**: `PARTIALLY_SUPPORTED` (H1_MODAL 부분 성립, H2_GENERIC 지배)
**corrects**: RQ-D13 F2 의 추론 · D 자신의 1차 계산 오류
**재현**: `.venv/bin/python research_d/tools/rq_d13a_overlay_provenance.py`
**산출**: `results/RQ_D13A_overlay_provenance.json`
**검증**: probe 재계산이 frozen mart 값과 **54/54 일치** (불일치 0)

---

## RQ

Axis C 의 대표값 `max_overlay_coverage` 가 `1.0`(뷰포트 전면 가림)일 때, 실제로 화면을
덮은 것은 무엇인가? SSOT 00 §3 Axis C 가 묻는 "popup·modal·banner·app prompt" 인가?

## 왜 중요한가

RQ-D1 F8 에서 확인했듯 **Axis C 는 현재 세 축 중 유일하게 실측값이 있는 축**이다
(56/56 non-null). Axis A 는 0행, Axis B 는 NED 조차 0/31 이다. 그 유일한 축의 대표값이
정의된 construct 를 재고 있지 않다면, 남은 분석 가능 범위가 사라진다.

---

## 코드 사실 (T1 · IMPLEMENTATION · exact SHA `2281c85`)

| 위치 | 내용 |
|---|---|
| `l0_probe.js` L196-199 | `position:fixed\|sticky` **이거나** `z-index >= 100` 이면 modal 여부와 무관하게 `modal_overlay_candidates` 에 포함 |
| `l0_probe.js` L219 | `viewport_coverage = overlap / (VIEW_W * VIEW_H)` |
| `l0_collector.py` L623-624 | `if not cand.get("visible"): continue` — 보이지 않는 후보는 제외 |
| `l0_collector.py` L575-577 | `max_overlay_coverage = max(viewport_coverage over ALL interrupts)` — **종류 필터 없음** |
| `l0_collector.py` L276-282 | `BLOCKING_MODAL` 은 `dialog_element\|role_dialog\|aria_modal` + coverage≥0.5 일 때만. 그 외 fixed/sticky 는 `BANNER` |

즉 정의상 `max_overlay_coverage` 는 **"보이는 fixed·sticky·high-z 요소 중 뷰포트 점유율 최대값"**
이지 "방해 팝업의 면적" 이 아니다.

---

## 방법 정정 (숨기지 않고 기록)

1차 계산에서 collector 의 `visible` 필터를 빠뜨렸다. 그 결과 보이지 않는 요소를 최대값으로
잡아 mart 와 **4건이 어긋났다**(다음·Chrome·메가커피·Google). collector 규칙을 그대로
적용해 시정했고, 시정 후 **54/54 일치**한다. 시정 전 분류(`H3_INVISIBLE` 4건)는 D 의
계산 오류였지 데이터의 결함이 아니다. 시정 전 수치도 결과 JSON `pre_correction_result` 에 남겼다.

---

## F1 (ANALYSIS) — `coverage == 1.0` 22건 중 실제 모달은 **4건뿐**이다

분모: probe 를 가진 54 targets (mart 56 중 2건은 probe 부재).

| 분류 | n | 비율 | 뜻 |
|---|---|---|---|
| **H1_MODAL** | **4** | 18.2% | `dialog` / `role=dialog` / `aria-modal` / backdrop-like — 정의에 부합 |
| H2_GENERIC_FIXED_OR_HIGHZ | 16 | 72.7% | fixed·sticky·high-z 이지만 모달 아님 |
| H2_GENERIC_LOADING_MASK | 2 | 9.1% | 로딩 차단 마스크 (`div#SHOWBLOCK`) |
| **합계 (coverage 1.0)** | **22** | 100% | |

전체 54 targets 기준으로도 H1_MODAL 은 4건뿐이다 (`NO_VISIBLE_CANDIDATE` 3, 나머지 47 은 H2).

### 결정적 사례

| service | z-index | position | 최대 요소 | 문제 |
|---|---|---|---|---|
| Instagram | **-9999** | fixed | `html>body>div:nth-of-type(3)` | **모든 콘텐츠 뒤에 있는 요소**가 전면 가림으로 계산됨 |
| 하나은행 | **-999** | fixed | `html>body>div:nth-of-type(1)` | 동일 |
| GS25 | None | **sticky** | `section` | 스티키 섹션 = 페이지 구조물이지 방해물 아님 |
| NH스마트뱅킹·콕뱅크 | 100000 | fixed | `div#SHOWBLOCK` | **로딩 차단 마스크** (`div#INGSHOW` 스피너 동반) |
| emart24 | 2147483647 | absolute | `div:nth-of-type(5)` | z-index 최대값 컨테이너 |

음수 z-index 요소가 "뷰포트를 100% 가렸다" 로 기록되는 것은 기하 계산으로는 참이지만
**construct 로는 거짓**이다. 그 요소는 사용자를 방해하지 않는다.

## F2 (OBSERVATION) — RQ-D13 F2 의 내 추론은 **틀렸다**

RQ-D13 에서 나는 NH 두 관측을 두고 "빈 body 인데 coverage 1.0 이 붙었다 — 측정대상이 없는
상태의 기하 계산 결과일 가능성" 이라고 썼다. **raw probe 가 이를 반증한다.**

NH 관측의 probe 는 `primary_action_candidates` **24개**, `dismiss_control_candidates` 15개,
`viewport 390×844`, `document_scroll_height 844` 를 기록했다. 페이지는 렌더돼 있었다.
`dom.html` 이 1657 B 이고 body 가 빈 것은 **DOM slot 이 렌더 전에 캡처됐기 때문**이며
(RQ-D10 이 확인한 slot 시점 불일치, dom→probe median 1.79 s), probe 시점의 페이지 상태가
아니다. NH 두 건은 RQ-D10 이 "문서 교체" 로 지목한 바로 그 사례다.

정정된 서술: **coverage 1.0 은 실재하는 전면 요소에서 나왔다. 다만 그 요소가 모달이 아니라
로딩 마스크다.**

## F3 (ANALYSIS) — 이것은 수집 결함이 아니라 **construct 정의 문제**다

`max_overlay_coverage` 계산은 코드대로 정확히 동작한다(54/54 재현). 문제는 그 값에
"초기 obstruction" 이라는 이름을 붙일 수 있느냐다.

SSOT 00 §3 Axis C 의 질문은 이것이다:

> 최초 viewport 에서 **popup, modal, banner, app prompt 등**이 화면 또는 대표행동을 얼마나 방해하는가?

`z=-9999` 인 배경 div, sticky 섹션, 로딩 마스크는 이 목록의 어디에도 없다.

`classify_interrupt` 는 이 구분을 **이미 갖고 있다** — `BLOCKING_MODAL` / `PROMOTION_MODAL` /
`BANNER` / `UNKNOWN`. 그러나 `max_overlay_coverage` 는 그 분류를 **쓰지 않고** 전체 최대값을 취한다.
분류는 있는데 대표값이 분류를 통과하지 않는다.

---

## 반례 / 대안설명 검토

- *"fixed·high-z 전면 요소는 실질적으로 모달과 같다"* → 일부는 그렇다(현대카드 `div#mainPopNotice1`
  은 이름부터 공지 팝업이다). 그러나 음수 z-index 2건과 sticky 1건은 방해하지 않는다.
  **"전부 잘못" 도 "전부 맞음" 도 아니다.** 그래서 verdict 는 PARTIALLY_SUPPORTED 다.
- *"D 의 H1/H2 분류가 자의적이다"* → 분류 기준은 collector 자신의 `MODAL_SOURCES`
  (`dialog_element`·`role_dialog`·`aria_modal`·`backdrop_like`)를 그대로 썼다. D 가 새로 만들지 않았다.
- *"로딩 마스크 판정이 사전 의존이다"* → 그렇다. `LOADING_TOKENS` 사전을 전문 공개했고,
  이 사전을 빼도 두 건은 H2_GENERIC 에 남아 F1 의 결론(H1 은 4건)은 바뀌지 않는다.

## Limitations

1. **`scroll_lock` 과 `dismiss_control` 을 판정에 쓰지 않았다.** 이마트·NS홈쇼핑·카카오맵처럼
   `lock=True` 인 건은 실제 모달일 가능성이 높지만, H2 중에도 lock=True 가 여럿이다
   (TikTok·마켓컬리·삼성카드·홈플러스·emart24·현대카드·V3). 다차원 판정은 후속 과제다.
2. **시각 확인을 하지 않았다.** 스크린샷을 사람이나 VLM 으로 보면 판정이 달라질 수 있다.
   D 는 픽셀을 보지 않고 DOM/CSS 속성만으로 판정했다.
3. `NO_VISIBLE_CANDIDATE` 3건과 probe 부재 2건은 분석에서 빠졌다 (54/56).
4. **어떤 값이 "옳은" 값인지 D 는 정하지 않는다.** construct 정의는 A 의 권한이다.

## Production implication (제안일 뿐. A ADOPT 전에는 implementation candidate 도 아니다)

- **P1**: `max_overlay_coverage` 를 그대로 "초기 obstruction" 으로 보고하면 22건 중 18건이
  정의 밖 요소에서 나온 값이다. 대표값을 `classify_interrupt` 라벨로 필터한 버전
  (예: `max_coverage_over_modal_and_banner`)과 병기하는 것을 검토할 수 있다.
- **P2**: 음수 z-index 요소를 후보에서 제외하는 것은 코드 한 줄이지만, 그것이 옳은지는
  construct 결정이다. D 는 판단하지 않는다.
- **P2**: RQ-D13 F2 에서 D 가 잘못 지목한 "퇴화 캡처가 MEASURED 로 기록됨" 은 철회한다.
  NH 두 건은 렌더된 페이지였다. 다만 `dom.html` slot 이 렌더 전 상태라는 문제는 남는다(RQ-D10).

## 후속 연구질문

- **RQ-D13a-1**: `scroll_lock` + `dismiss_control` + `hittable` + `contains_focus` 를 결합한
  다차원 모달 판정이 H1/H2 경계를 얼마나 바꾸는가
- **RQ-D13a-2**: `classify_interrupt` 라벨로 필터한 대표값과 현재 값의 분포 차이
- **RQ-D13b**: `dom_after.html` 로 dismissal 의 DOM 수준 효과 재판정 (픽셀 무변화 82/248)
