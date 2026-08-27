# W5J — 커밋된 스크롤 fixture (`Δ22-scrollfix`)

```
lane                = W5J (scroll state)
status              = FIXTURE_ONLY
authoritative       = false
fixture_only        = true
real_target_measurement = false
base_sha            = 7c5ae70def2da675f7d2d586a0b678ba9fdfc6dc
```

## 이 lane 이 남긴 것과 버린 것

**버렸다 — 스크롤 상태 열거 구현.** 이 lane 은 "base 에 scroll 열거 코드가 없다" 는
전제로 열렸고 그 전제가 틀렸다. W5H
`v3_runner/session.py::FixtureSessionDriver.capture_surface` 가 engine 을 고치지 않고
`page.evaluate(window.scrollTo)` 로 이미 `S0..Sn` 을 낸다. **그것이 정본이다.**

> B 확정 판정: **열거 모듈은 폐기, 커밋 fixture 는 존치.**
> 폐기 근거 — 같은 일을 하는 두 구현을 두면 관측이 어느 쪽에서 나왔는지 `R22` 로도
> 구분되지 않는다.
> 존치 근거 — fixture 는 구현이 아니라 **입력**이다. 두 구현은 충돌하지만
> 한 구현 + 그것을 실행시키는 입력은 충돌하지 않는다.

**남겼다 — 이 디렉터리.** A 판정(`T-A-V3-STEP1-021`):

> W5H 는 런타임 임시 파일로 대조했다. 커밋된 것이 아니다. GATE 1 에서 `S1..Sn` 을
> 재현 가능하게 검증하려면 **커밋된 fixture** 가 필요하다. v3 fixture 13/13 이
> `body{overflow:hidden}` 이라 스크롤되지 않는다. **그 집합으로는 scroll 경로가
> 영원히 검증되지 않는다** — 코드가 있어도.

## 파일

| fixture | 대조 | `scrollHeight` | `innerHeight` | 기대 state | 무엇을 검증하는가 |
|---|---|---|---|---|---|
| `scroll_reveal_control.html` | **양성** | 2616 | 844 | `S0 S1 S2 S3` (4) | 실제로 스크롤되고, 마크업이 같은 세 control 이 `S0` / `S1` / `NULL` 로 갈린다 |
| `scroll_single_state.html` | **음성** | 844 | 844 | `S0` (1) | 한 화면 문서는 `scrollTo` 를 불러도 안 움직이고 단계가 늘지 않는다 |

기대값의 기계 판독본은 `expectations.json` 이다(파일별 `sha256` 포함).
`tests/test_w5j_scroll_state.py` 가 그 파일을 읽어 집행한다.

양성만 두면 검사가 동작하는지 알 수 없다. **음성이 짝으로 있어야** "S1 이 났다" 가
"열거기가 무조건 S1 을 만든다" 와 구분된다.

## 이 브랜치에서 검증되는 것과, 병합 뒤에야 검증되는 것

**이 fixture 는 W5H `ScrollPolicy` 와 병합된 뒤에야 `S1..Sn` 경로를 실행한다.**

`ScrollPolicy` · `FixtureSessionDriver.capture_surface`(W5H)와
`measure_surface.first_visible_scroll_state`(W5C)는 **다른 브랜치에 있고 이 워크트리에
없다.** 그래서 이 브랜치의 테스트는 그 모듈을 import 하지 않고, 대신 Playwright 로
fixture 를 직접 열어 **기하만** 실측한다 —
`document.documentElement.scrollHeight`, `window.innerHeight`, `window.scrollTo` 가
실제로 `scrollY` 를 옮기는지, control 의 `getBoundingClientRect` 가 어느 offset 에서
viewport 와 교차하는지.

| 주장 | 어디서 검증되나 | 누구 의무 |
|---|---|---|
| 문서가 실제로 스크롤된다 (2616 > 844) | 이 브랜치 · Playwright 실측 | W5J (완료) |
| 보폭 844 로 offset 열 `0/844/1688/1772` 4단계 | 이 브랜치 · Playwright 실측 | W5J (완료) |
| 음성 대조군이 S0 하나만 낸다 | 이 브랜치 · Playwright 실측 | W5J (완료) |
| 세 control 의 문서상 위치가 갈린다 | 이 브랜치 · `getBoundingClientRect` | W5J (완료) |
| `ScrollPolicy` 가 이 fixture 에서 `S0..S3` 을 **열거**한다 | 병합 뒤 통합 테스트 | **B (병합 시점)** |
| `first_visible_scroll_state` 가 `S0`/`S1`/`None` 을 낸다 | 병합 뒤 통합 테스트 | **B (병합 시점)** |

병합 시점에 아래 두 줄이 `expectations.json` 을 그대로 읽어 통과해야 한다.
fixture 와 기대값은 손대지 않고 쓸 수 있다.

```
capture_surface(scroll_reveal_control) -> state_indices == ["S0","S1","S2","S3"]
first_visible_scroll_state(...)        -> {"button#ctl-s0":"S0","button#ctl-s1":"S1","button#ctl-never":None}
```

## 규약

1. `fixtures/v3/` 를 비롯한 **다른 lane 의 fixture 를 건드리지 않는다.**
2. fixture 는 외부 자원을 참조하지 않는다. `http(s)://` 가 한 글자라도 들어가면
   real-target 수집이 되고 테스트가 막는다.
3. 값을 고칠 때는 HTML 상단 주석 · `expectations.json`(`sha256` 포함) · 이 표를
   **함께** 고친다. 한쪽만 고치면 그 자체가 drift 다.
4. 이 lane 은 `engine/l0_collector.py` · `engine/l0_probe.js` 를 고치지 않는다.
   base 와 바이트 동일함을 테스트가 sha256 으로 고정한다.
