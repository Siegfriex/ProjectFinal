# MAIN50 시간제한 전수관측 보고서 v1

*MAIN50 Time-boxed Acquisition Report v1*

**상태**: `PUBLICATION_READY` 유보 · **수집창** 2026-08-28 10:30–11:50 KST · **분석·검산·봉인** ~12:30 KST
**동결 프레임** FINAL_MAIN50_MANIFEST v3.0.2 (무수정) · **정본 mart** `5290e0c3…` 50행

---

## 0. 한 문장

동일한 생활과업을 기준으로 50개 모바일웹 서비스를 전수 관측했지만, **현재 자동화 프로토콜은 모든 서비스에서 비교 가능한 task-flow evidence를 확보하지 못했다.**

---

## 1. 이 문서가 다루는 표의 성격

최종 mart는 **동일 조건의 50개 census 결과표가 아니다.** R1 전수 → 실패기반 R2/R2B 재측정 → 성공대상 geometry 보충 R3가 섞인 **outcome-conditioned rescue mart**다.

> **Collection run은 교환가능한 반복측정이 아니다. R2와 R3는 이전 관측 결과에 따라 대상이 선택된 rescue pass이므로 run별 terminal 분포를 성능 비교나 서비스 특성 비교에 사용하지 않았다.**

따라서 이 보고서는 **회차 간 성공률·family 간 성공률·8/50을 서비스 reachability로 해석하지 않는다.** `collection_run`과 `superseded_runs`는 provenance 전용이며 통계변수로 쓰지 않았다.

---

## 2. 1층 — 방법론 결과

50개 frozen service×task를 **exactly-once로 전부 시도**했다. 시간제한 수집 종료 시점의 acquisition state는 다음과 같다.

| 집단 | n | 내역 |
|---|---:|---|
| **USABLE PATH EVIDENCE** | 8 | `ENDPOINT_REACHED` 6 · `AUTH_GATE` 2 |
| **SITE-SIDE ROUTE NOT OBSERVED** | 16 | `NO_SAFE_ROUTE_SITE` 16 **[RETRACTED]** |
| **MEASUREMENT / COLLECTOR LIMITED** | 26 | `COLLECTOR_ZERO_CANDIDATE` 21 · `TIMEOUT` 2 · `UNVERIFIED_CANDIDATE_COUNT` 2 · `FORBIDDEN_ACTION_BOUNDARY` 1 |

`FORBIDDEN_ACTION_BOUNDARY`는 사이트가 금지행위를 했다는 뜻이 아니라 **수집기가 경계에서 멈춘 것**이므로 measurement 쪽에 둔다.

### 2.1 실패 44건 중 21건은 사이트에 대한 관측이 아니다

`COLLECTOR_ZERO_CANDIDATE` 21건은 **수집기가 후보를 0개 반환한 것**이다. F1-01의 경우 DOM이 74,469 B로 페이지가 정상 렌더됐는데 후보 탐색 결과가 0이었다.

**viewport 보정(`scroll_into_view_if_needed`)을 적용한 재수집에서도 동일하게 재현됐다** — 그 수정은 R2 배치 시작 *이전*에 이미 적용돼 있었다. 즉 재시도 미적용이 아니라 **적용하고도 바뀌지 않았다**. 얕은 키워드 텍스트매칭이 SPA 메뉴 하위구조를 뚫지 못하는, **이 수집 방법의 계통적 한계**다.

말할 수 있는 것은 **"이 과업군의 진입 경로는 landing에서 얕은 텍스트 탐색으로 도달되지 않는다"**까지다. **"사람도 못 찾는다"로 넘어가지 않는다.**

---

## 3. 2층 — 사례분석 (위치·형태 n=5 · 순서·깊이 n=8)

C가 독립 검증했다: 8개 target 전부 **R3 선택 이전(R1, 11:06–11:26)에 이미 endpoint/auth evidence를 보유**했다(8/8 CONFIRMED). 따라서 8이라는 수는

> **"시간 제한 내 전체 acquisition history에서 8개 고유 target에 usable task-path evidence가 최소 1회 확보됐다"**

를 뜻하며, **"50개 중 8개 서비스가 접근 가능했다"가 아니다.** '접근성 성공률'이라 부르지 않는다.

| 축 | 값 | 판정 |
|---|---|---|
| 진입 위치 `entry_zone` | **4종 / 5** (TOP_LEFT 1 · TOP_CENTER 1 · MID 2 · TOP_RIGHT 1) | **비수렴** |
| control 형태 `entry_control_type` | 2종 / 5 (TEXT_LINK 4 · ICON_TEXT 1) | **비수렴** |
| 조작순서 signature | 1종 (`SELECT_FUNCTION` ×8) | **수렴** |
| 활성화 깊이 `activation_depth` | 1 ×8 | **수렴** |
| 메뉴 의존 `menu_dependency` | False ×8 | **수렴** |
| navigation container | — | **보고 제외** |

**갈린 것은 "어디에 있는가"이고, 갈리지 않은 것은 "몇 번에 닿는가"다.** 관측된 재학습 요구는 절차적이 아니라 위치·시각적이다.

**navigation container를 제외한 이유**: E가 산출한 적이 없는 변수다. 7건은 전부 B의 사후 DOM 파생이고, 규칙상 인용 가능한 것은 5, 그중 1건은 `AMBIGUOUS_MULTIPLE_CONTAINERS`(판정 불가) → 실질 4/8. **"미관측 8/8"도 "관측 7/8"도 틀렸다.**

### 3.1 반드시 함께 읽어야 할 선택편향

관측된 8건이 **전부 메뉴를 거치지 않는 단일 스텝**이었다. 이는 사이트가 얕아서가 아니라 **수집기가 깊은 경로를 뚫지 못했기 때문일 수 있다.** `COLLECTOR_ZERO_CANDIDATE` 21과 같은 방향의 편향이다. **"사이트가 얕다"로 해석하지 않는다.**

---

## 4. 라벨 축은 버렸다

**이번 census에서 AX 캡처는 한 번도 성공하지 않았다.**

원인은 얕은 AX 트리가 아니라 **API 부재**다. 설치된 Playwright 1.62.0에서 `page.accessibility`가 제거됐고(`hasattr(page,'accessibility') → False`), 캡처 코드가 존재하지 않는 속성에 접근해 매번 `AttributeError`를 냈다. 그것이 except 블록에 잡혀 `{"_error": "'Page' object has no attribute 'accessibility'"}`라는 **고정 60바이트 문자열로 저장**됐다. `.ax.json` **107/107이 이 스텁**이다.

정확한 라벨은 **`AX_CAPTURE_METHOD_FAILURE`(API 버전 불일치) · 실제 캡처 0/50**이다.

따라서 `accessible_name`은 `visible_label`을 그대로 복사한 값이었고, `label_relation`의 `MATCH`는 "두 값이 같더라"가 아니라 **"같은 값을 두 열에 넣었다"**였다. `AX_NOT_INDEPENDENTLY_OBSERVED`로 교체했다.

**독립 관측 쌍은 3이 아니라 0이다.** 최종 mart에서 두 열이 함께 채워진 행은 28건이지만 **그 28건 전부가 `AX_NOT_INDEPENDENTLY_OBSERVED`** 다 — 채워짐이 관측을 뜻하지 않는다. 라벨 축은 **사이트 간 결과지표에서 제외했다.**

> **결측 검사와 값 읽기는 다른 행위다.** mart는 그 28건에 "이건 관측이 아니다"라는 **경고를 값으로** 들고 있었는데, 결측 여부만 보면 그 경고가 통째로 보이지 않는다. A가 이 절의 funnel에 "3"을 적었던 것이 정확히 그 형태였다 — 폐기된 판본의 `DIFFERENT 3`을 값 확인 없이 옮겼다. (D-DEF-41, B 재현)

---

## 5. 안전

**안전가드가 금지 패턴 후보 1건을 감지하여 실행 전에 차단함. 실제 금지행위 실행 0건.**

F1-10에서 후보 라벨 "이체하기"가 실행형 패턴에 매칭돼 클릭 이전에 리턴됐다(`state_count=1` · `activation_depth=0`). **가드가 있다는 것과 작동한다는 것은 다른데, 이번에 작동이 관측됐다.**

raw 필드명 `forbidden_actions_attempted`를 그대로 노출하지 않는다 — "attempted"만 보면 위반으로 오독된다.

---

## 6. 이 실행의 방법론적 산물

### 6.1 하나의 미검증 진술이 네 평면을 통과했다

| | 평면 | 무엇을 했나 |
|---|---|---|
| ① | **E** | `.ax.json`이 *존재하는 것만* 보고 내용을 열지 않은 채 "원자료는 존재한다"고 보고 |
| ② | **A** | 그 진술을 **검증 없이 채택해 판정으로 발행** |
| ③ | **B** | 판정을 받아 동결 문서에 반영. 그러나 **B는 세션 초반에 그 파일이 60바이트 스텁임을 직접 보고 보고까지 했다** — 자기 관측과 대조하지 않았다 |
| ④ | **D** | `ls` 한 번이면 확인됐을 것을 하지 않고 그림에 반영 |
| ⑤ | **C** | `.ax.json` **107/107을 직접 세어** 확인 — **전파가 끊겼다** |
| ⑥ | **E** | 코드에서 근본 원인 확인, **자기 중간 보고를 철회** |

**⑤가 한 일은 `ls -l`과 세기뿐이다.**

교훈:
- **파일 존재는 내용의 증거가 아니다.**
- **권한 평면의 판정이 검증을 대체하지 않는다.**
- **자기가 이미 관측한 것과 새로 받은 판정을 대조해야 한다.**
- **상위 판정이라도 파일 존재·바이트 수준 주장은 인용 전에 직접 확인한다.**

### 6.2 공통 형태 하나

**60바이트 오류 스텁은 파일 목록에서 정상 파일과 구분되지 않는다.** 이 census가 겪은 결함이 전부 같은 형태였다 — **없음과 있음이 같은 출력으로 보이는 것.**

- C — checker v1이 `NOT_OBSERVED` 토큰을 evidence로 세어 **관측 0인 입력에서 50/50 만점**
- D — `data_state`가 행수만 보고 evidence 2건 mart에 COMPLETE. **그 형태를 막으려 만든 표지가 스스로 그 형태를 냈다**
- B — `collection_run`이 50행 전건 sentinel인 채 **모든 검사를 통과**. 생산자의 눈이 잡았다
- B — 두 run이 겹칠 때 `found[tid]=ev`로 조용한 덮어쓰기. **실패가 아니라 성공처럼 보이는 변경**
- B — `selection_rule` 이름은 `LATEST_RUN`인데 계산은 **사전순**. **이름이 계산을 잘못 설명하고 있었다**
- A — 폐기된 판본 기준 수치를 확정치로 하달(2회), 손으로 적은 시각(2회), 부분 수치를 전체로 인용
- 폐기된 그림 6장이 최종본과 **같은 디렉터리**에 있었다

### 6.3 검사로 옮긴 것

- `COLUMN_SENTINEL` — 열 100% sentinel = **미배선**(`WIRED: false`). 첫 실행에서 즉시 2건 정탐(`reveal_direction`·`task_control_occlusion`)
- `undermapped_columns` — 원본보다 덜 실린 열. `visible_label` 28→4가 그 형태였다
- `must_flag` / `must_not_flag` — 검사가 실제로 실패를 잡는지 실행으로 증명
- 미실행과 실패의 종료코드 분리

가장 깊은 한 줄은 B의 것이다:

> **"첫 재동결은 오류 없이 통과했고 값만 틀렸다. 검사가 잡은 게 아니라 내가 출력에서 봤다."**

같은 형태가 재발했을 때는 검사가 잡았다. **검사로의 이전이 이 실행의 실제 산물이다.**

### 6.4 아직 못 잡는 것

**시정이 새 결측을 만드는 경로.** B가 `label_relation` 결함을 고치자 분기가 뒤바뀌어 `entry_control_type`이 28→9로 조용히 떨어진 판본이 실제로 동결됐다. `unwired_columns`도 `undermapped_columns`도 통과시켰고 생산자의 눈이 잡았다.

---

## 7. 검증하지 않은 것

- **결정론적 replay 면제** — 같은 코드로 다시 돌려도 같은 raw가 나온다는 근거가 없다
- **`COLLECTOR_ZERO_CANDIDATE` 21 미해소**
- **geometry 보충 hash 미결속** — `GEOMETRY_SUPPLEMENT_E.jsonl`에 `evidence_hash`가 없어 n=8 위치 관측의 hash 결속은 R1 줄 hash로만
- **재측정 전수 적용 미검증** — 합집합 35 중 미재측정 7 (좁은 기준 안 4: F1-01·02·07·09)
- **사유 없는 결측 88건** — 없음은 알지만 왜 없는지를 모른다
- **누수·오염** — `NOT_ASSESSED_BEYOND_EXISTING_CONTROLS`. **"누수 없음"이 아니라 "미측정"이다**

---

## 8. 말하지 않는 것

실제 고령자의 인지부하 증가량 · 실제 학습전이 실패의 인과효과 · cross-provider WCAG/KWCAG 위반 판정 · 사람 대상 연구 없는 연령별 행동효과 · composite '고령자 접근성 점수' · 서비스 접근성 순위 · family 우열.

**이 구조적 차이가 실제 고령 사용자의 재학습 부담이나 과업 실패를 유발하는지는 이번 연구에서 직접 측정하지 않았다.**

---

## 9. 이번 결과의 위치

이번 결과는 서비스 간 구조적 불일치의 **전체 발생률을 추정한 것이 아니라**, 동일 과업을 비교하려면 단순 페이지 수집보다 **task-aware interaction measurement가 필요함**을 보여주는 1차 전수관측이다.

> 사람의 디지털 역량은 오래 측정해 왔지만, 실제 서비스의 길을 비교하려면 **그 길을 측정할 수 있는 방법부터** 필요했다. 이번 연구는 그 측정 프레임과 한계를 50개 서비스에서 확인했다.

---

## 10. 다음 실행 권고

1. **AX 트리 캡처 복구** — 원인은 Playwright 1.62.0의 `page.accessibility` 제거. 현행 API로 교체
2. **얕은 키워드 매처를 SPA 하위구조 탐색으로 교체** — `COLLECTOR_ZERO_CANDIDATE` 21의 직접 원인
3. **geometry를 수집 시점에 기록** — 소급 복구가 불가능했다
4. **"시정이 새 결측을 만드는" 경로를 잡는 검사** — 판본 간 열별 관측수 diff
5. **위 넷을 마친 뒤에야 replay를 포함한 본수집을 논한다**
