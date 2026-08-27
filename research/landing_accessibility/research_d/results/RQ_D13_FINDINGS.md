# RQ-D13 — Duplicate Measurement-Vector Detection

**verdict**: `PARTIALLY_SUPPORTED` — 중복은 실재하나 원인은 수집기 결함이 아니라 **frame 등록 중복 + 퇴화 캡처** 두 가지다.
**파생 근거**: RQ-D9 부수발견(서로 다른 target 이 byte-identical 관측 생성) · D amendment D5 우선순위 4
**재현**: `.venv/bin/python research_d/tools/rq_d13_duplicate_vector.py`
**산출**: `results/RQ_D13_duplicate_vector.json`
**A/B/C 보고문 사용**: 없음. manifest per-file sha256 과 frozen mart 에서 전량 재계산.

---

## RQ

wtg 단위 dedup 으로는 잡히지 않는 중복이 몇 건이며, 그것은 수집기 결함인가 서비스가 실제로 랜딩을 공유한 것인가?

## 경쟁가설

| id | 가설 | 판정 |
|---|---|---|
| H1 COLLECTOR | 수집기가 같은 페이지를 두 target 에 기록 (결함) | **REFUTED** — 요청 URL 자체가 같다 |
| H2 SHARED | 두 서비스가 실제로 같은 랜딩 공유 (frame 문제) | **SUPPORTED (형태 수정)** — 공유가 아니라 **동일 URL 등록** |
| H3 BLOCKPAGE | WAF/에러 페이지가 동일하게 반환 | **NOT_SUPPORTED** — 공유 artifact 는 blank 캡처이지 차단 페이지가 아니다 |
| H4 NONE | 요약 통계만 같고 바이트는 다름 | **부분 성립** — 3 그룹 중 2 그룹이 slot 일부만 공유 |

---

## F1 (OBSERVATION) — 59 attempted target 의 distinct 요청 URL 은 **56개**다

| grain | 수 |
|---|---|
| observation 디렉터리 | 66 |
| distinct web_target_group (wtg) | 59 |
| **distinct 요청 URL** | **56** |
| mart landing rows | 56 |

URL 수준 중복 그룹 1건:

```
https://banking.nonghyup.com/nhbank.html
  → NH스마트뱅킹 (wtg 95967b50683649f2)
  → NH콕뱅크     (wtg fb3d1841dddfd982)
```

두 wtg 모두 mart 에 **별도 행으로** 들어가 있다. 즉 mart 56 행은 **55개 distinct URL** 을 덮는다.

두 관측의 `dom.html` 은 byte-identical (sha `b783cbd0ec76`, 1657 B)이다. 같은 URL 을 두 번 요청했으니 당연한 결과이고, **수집기 결함의 증거가 아니다.**

> 이것은 D-VRC-001-B 에서 D 가 "수집기 결함 후보" 로 올린 항목의 **원인 정정**이다.
> 결함은 수집기가 아니라 target 등록(frame)에 있다.

**분모 영향**: 서비스 단위 분석에서 두 행은 독립 관측이 아니다. 두 서비스가 같은 웹 랜딩을 쓰는 것이
사실이라면 frame 정의상 정당할 수 있으나, 그렇다면 "서비스 59개" 가 아니라 "웹 랜딩 56개" 가
분석 단위여야 한다. 어느 쪽인지는 A 의 frame 결정 사항이다.

## F2 (OBSERVATION) — 같은 퇴화 서명이 **두 가지로 분류**됐다

`computed_css.json` 이 **3 바이트**(사실상 빈 배열)인 관측이 60개 중 **4개**다. 네 건 모두
`dom_body_empty=1`, `dom_interactive_n=0` 이고 `screen_initial.png` 가 서로 byte-identical
(sha `04efb0e77f29`, 14,074 B, 1170×2531)이다 — 빈 화면 렌더다.

| wtg | service | css | dom | interactive | **mart status** | overlay cov | occlusion |
|---|---|---|---|---|---|---|---|
| 64d30ef2 | 신한 SOL뱅크 | 3 B | 6,072 B | 0 | `FAILED_EVIDENCE_INCOMPLETE` | 0.0 | 0.0 |
| ef06dc94 | 롯데하이마트 | 3 B | 314 B | 0 | `FAILED_EVIDENCE_INCOMPLETE` | 0.0 | 0.0 |
| 95967b50 | NH스마트뱅킹 | 3 B | 1,657 B | 0 | **`MEASURED`** | **1.0** | **1.0** |
| fb3d1841 | NH콕뱅크 | 3 B | 1,657 B | 0 | **`MEASURED`** | **1.0** | **1.0** |

**동일한 퇴화 서명이 2건은 실패로, 2건은 성공으로 기록됐다.** 그리고 성공으로 기록된 2건은
F1 의 동일 URL 쌍이며, "오버레이가 뷰포트를 100% 덮고 대표행동을 100% 가림" 으로 값이 붙었다.

빈 body 에서 overlay coverage 1.0 이 나오는 것은 obstruction 의 의미(초기 진입 방해)가 아니라
**측정 대상이 없는 상태의 기하 계산 결과**일 가능성이 높다. 다만 D 는 overlay 계산 코드를 읽지
않았으므로 그 메커니즘을 확정하지 않는다 (→ RQ-D13a).

## F3 (ANALYSIS) — Axis C 분포에 대한 영향은 **제한적**이다. 과장하지 않는다

| 지표 | 전체 (n=56) | 퇴화 4건 제외 (n=52) |
|---|---|---|
| median overlay coverage | 0.1281 | **0.1281** (변화 없음) |
| mean overlay coverage | 0.4428 | 0.4384 |
| `coverage == 1.0` | 22/56 | 20/52 |

`coverage == 1.0` 인 22 target 중 **20건은 정상 DOM 을 가진 실제 페이지**다 (TikTok 329 KB·
삼성카드 451 interactive·홈앤쇼핑 562 interactive 등). 따라서 **"Axis C 상단이 퇴화로 오염됐다"
는 주장은 성립하지 않는다.**

정확한 서술은 이것이다: **Axis C 에 비독립 관측 2행(동일 URL)과 측정대상 부재 관측 2행이
섞여 있고, 그 4행은 median 을 바꾸지 않는다.**

## F4 (OBSERVATION) — 강제 dismissal 의 **33.1%** 가 화면을 전혀 바꾸지 않았다

l0c step 별 `screen_before` 와 `screen_after` 의 sha256 비교:

| | 수 |
|---|---|
| step 총계 | 248 |
| **before == after (무변화)** | **82 (33.1%)** |
| before != after | 166 |
| l0c 를 가진 target | 50 |
| **모든 step 에서 무변화인 target** | **6 / 50** |

`forced_dismissal_count` 를 "실제로 방해물을 치운 횟수" 로 읽으면 최대 33% 가 과대계상이다.
다만 "화면이 안 바뀌었다" 가 곧 "dismissal 이 실패했다" 는 아니다 — 뷰포트 밖 변화, DOM 만
바뀌고 픽셀은 동일한 경우가 있을 수 있다. `dom_after.html` 이 slot 에 있으므로 DOM 수준
비교로 구분 가능하다 (→ RQ-D13b).

## F5 (OBSERVATION) — 교차 target byte-identical artifact 는 **5종뿐**이다

| sha | bytes | slot | targets |
|---|---|---|---|
| `04efb0e77f29` | 14,074 | `l0a/screen_initial.png` | 4 |
| `a75c5429b481` | 14,079 | `l0a/screen_fullpage.png`, `l0c/9/screen_after.png` | 4 |
| `37517e5f3dc6` | 3 | `l0a/computed_css.json` | 4 |
| `ff34c3e35ae5` | 215,136 | l0c 다수 step | 2 (NH 쌍) |
| `b783cbd0ec76` | 1,657 | `l0a/dom.html` | 2 (NH 쌍) |

전부 F1(동일 URL) 또는 F2(빈 캡처)로 설명된다. **수치 측정벡터만 동일하고 바이트는 다른
중복 그룹은 0건**이다 (`numeric_vector_duplicate_groups = 0`).

즉 **"측정벡터 중복" 이라는 현상은 이 데이터에 존재하지 않는다.** 존재하는 것은 URL 중복과
빈 캡처다. wtg 외에 측정벡터 해시로 dedup 을 추가할 근거는 이 표본에서는 나오지 않았다.

---

## 반례 / 대안설명 검토

- *"NH 두 서비스는 실제로 같은 앱의 두 브랜드라 같은 웹 랜딩이 맞다"* → **배제하지 못했다.**
  그렇다면 결함이 아니라 frame 정의 문제다. 어느 쪽인지는 서비스 등록 근거를 봐야 하고
  그건 A 의 frame 영역이다.
- *"빈 캡처 4건은 사이트가 실제로 빈 페이지를 반환한 것"* → 가능하다. 하지만 그렇다면
  `MEASURED` 와 `FAILED_EVIDENCE_INCOMPLETE` 로 갈린 이유가 설명되지 않는다.
- *"before==after 82건은 dismissal 이 필요 없었던 경우"* → 가능하다. DOM 비교로 구분해야 한다.

## Limitations

1. **overlay coverage 계산 코드를 읽지 않았다.** 빈 body 에서 1.0 이 나오는 메커니즘은 추론이지
   확인이 아니다. `measurement_status` 를 가르는 규칙도 읽지 않았다.
2. **before/after 비교는 픽셀 동일성이다.** DOM 수준 변화는 검사하지 않았다.
3. NH 쌍이 정당한 공유인지 등록 오류인지 D 는 판정할 수 없다. 판정에 필요한 것은 서비스
   등록 근거이고 그것은 frame 결정이다.
4. 표본이 56 target 이라 "중복 0건" 은 "중복이 드물다" 이지 "없다" 가 아니다.

## Production implication (제안일 뿐. A ADOPT 전에는 implementation candidate 도 아니다)

- **P1**: 동일 요청 URL 을 가진 두 wtg 가 mart 에 독립 행으로 들어간다. 서비스 단위 통계의
  분모를 "web target 59" 로 쓰면 55개 URL 을 59로 세는 셈이 된다.
- **P1**: 같은 퇴화 서명이 `MEASURED`/`FAILED` 로 갈린다. 분류 규칙을 evidence 완결성 기준으로
  통일하지 않으면 어느 쪽 값도 신뢰할 수 없다.
- **P2**: `forced_dismissal_count` 의 의미를 "시도" 인지 "성공" 인지 codebook 에 명시할 것.

## 후속 연구질문

- **RQ-D13a**: 빈 body 에서 overlay coverage 1.0 이 나오는 계산 경로 — 코드를 exact SHA 로 읽어 확인
- **RQ-D13b**: `dom_after.html` 로 dismissal 의 DOM 수준 효과를 재판정 — 픽셀 무변화 82건 중 몇 건이 실제 무효과인가
- **RQ-D13c**: `measurement_status` 를 가르는 규칙과 evidence 완결성의 관계
