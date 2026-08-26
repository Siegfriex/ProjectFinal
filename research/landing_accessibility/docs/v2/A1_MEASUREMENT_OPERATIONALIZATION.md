# A1 — 측정 조작화 보충명세 v2.0

| 항목 | 값 |
|---|---|
| 지위 | `00`~`02`의 **하위 보충문서**. 새 연구기준을 만들지 않는다 |
| 대상 | 감사 `V2_C001`(ssot · adversarial)이 지적한 **측정 조작화 공백** |
| 작성 단계 | P0 `V2_REFREEZE` 시정 |
| 값 동결 시점 | 본 문서가 제시한 **수치 기본값은 전부 P-C에서 검증 후 동결**한다 |

---

## 0. 이 문서의 지위

### 0.1 SSOT 우선 조항

이 문서는 `00_SSOT_v2.0.md`가 **이미 정의한 변수의 산출 절차**만 기술한다.

> 이 문서가 `00_SSOT_v2.0.md`와 충돌하면 **SSOT가 우선한다.**
> 충돌이 발견되면 그것은 SSOT의 결함이 아니라 **이 문서의 결함**이며, 이 문서를 고친다.

`01_DATA_SPEC_v2.0.md` · `02_COLLECTION_MEASUREMENT_SPEC_v2.0.md`에 대해서도 같다.
권위 서열은 `EXECUTION_AUTHORITY.md` §2를 따르며, 이 문서는 그 표에서 `00`~`05` 및
`PHASE_GATES.md` **아래**에 놓인 보충명세다.

이 문서는 `00`~`05` pack의 **바이트를 수정하지 않는다.** 동결본은 그대로 두고 보충으로만 작동한다.

### 0.2 이 문서가 닫는 finding

| finding id | 감사 | 등급 | 본 문서 대응 절 |
|---|---|---|---|
| `ned-ied-split-not-operationalized` | ssot F1 | P1 / blocking | §1 |
| `l1-scout-has-no-step-budget` | adversarial P2-4 | P2 / `E001_V2-blocking` | §2 |
| `interrupt-dismiss-fields-have-no-collection-procedure` | ssot F2 | P2 / blocking | §3 |
| `episode-counters-undefined-and-uncollected` | ssot F3 | P2 / blocking | §4 |
| `primary-action-identity-not-stored` | ssot F4 | P2 / blocking | §5 |
| `l0-evidence-artifacts-without-storage-slot` | ssot F5 | P2 / blocking | §6 |

본 문서가 닫지 않는 finding(ssot F6~F13, adversarial P1 3건)은 다른 담당의 소관이다 —
상태값 어휘·스키마 대응은 `A2_VOCABULARY_AND_SCHEMA_BINDING.md`, gate 이름은 `PHASE_GATES.md`,
권위·승격 강제수단은 `EXECUTION_AUTHORITY.md`가 닫는다.

### 0.3 A2가 우선하는 절 (관할 선언)

아래 절이 정의하는 **상태값의 컬럼 배치·허용값 도메인**은 `A2_VOCABULARY_AND_SCHEMA_BINDING.md`가
정본이며, 본 문서와 충돌하면 **A2가 우선**한다. 본 문서는 그 값을 *언제 어떻게 관측하는가*를 정한다.

> **[V2-C005 시정]** 이 표는 **A2 §0의 대칭 조항과 정확히 같은 목록**이어야 한다.
> V2-C004에서 두 감사(ssot / 독립 adversarial)가 각각 독립적으로 세 목록의 불일치를 재현했다 —
> A1 표에 A2가 열거한 §3.2·§3.3·§4.2·§4.3이 없었고, A2 목록에 A1이 열거한 §1.5가 없었으며,
> 같은 절 안 후속 문단이 또 다른 목록을 말했다. 아래가 **합집합으로 통일된 단일 정본**이다.
> 닫는 결함: `a1-0-3-jurisdiction-declaration-drifts-from-a2-and-collides-with-existing-section`

| 본 문서 절 | A2 정본 | 관할 대상 |
|---|---|---|
| §1.5 · §1.5 auth gate 교차참조 | A2 §1.5.1 · §1.5.1a | 신호 미관측 상태값 · gate 분기 |
| §1.8 | A2 §1.5.3 · §1.5.4 · §1.9 | step 귀속 필드의 값 도메인 (`§1.5.4` 를 빼면 `area_signal_detected`·`depth_segment`·`counts_toward_depth` 3필드가 정본 없이 남는다) |
| §2.2 | A2 §1.5.2 | `endpoint_status` vs `endpoint_status_detail` 배치 |
| §3.2 · §3.3 · §3.4 | A2 §1.6 | dismiss control 필드군 |
| §4.2 · §4.3 · §4.4 | A2 §1.12 | episode 필드군 |
| §5.1 | A2 §1.13 | primary action candidate 필드군 |
| §6.1 | A2 §4.1 · §6.3 | L0 evidence 슬롯 (`§1.0` 은 수준 분리표라 `screenshot_*_path`·`evidence_run_id`·타임스탬프·DPR 을 담지 않는다) |

위 절에서 본 문서가 **제안한 신규 필드·표의 상태값 도메인**은 `A2`의 허용값 표에 등재되어야
최종 확정된다. 본 문서는 그 값을 *언제 어떻게 관측하는가*를 정하고, `A2`는 *어떤 값이 허용되며
어느 컬럼에 담기는가*를 정한다. 두 문서가 어긋나면 `A2`의 어휘 정의가 우선한다.

**이 표는 A1·A2 양쪽에 같은 내용으로 존재하며, 한쪽만 갱신하는 것은 그 자체로 결함이다.**
관할 선언의 앵커는 **본 절(`A1 §0.3`)** 이다 — A2는 `A1 §0.2`가 아니라 이 절을 인용해야 한다.

### 0.4 금지 재확인

이 문서는 다음을 **하지 않으며**, 아래를 어기는 해석이 파생되면 그 해석이 틀린 것이다.

- `depth >= N = 나쁨` 류의 임의 threshold 생성 (`00` §4 · §14)
- KWCAG 2.2 임계값의 변경·완화·고령자용 대체 (`00` §4 Axis A)
- Depth·popup·episode 값을 KWCAG `FAIL`로 전환 (`02` §13)
- 세 축(A/B/C)의 단일 종합점수 합산
- WA 인증을 gold label로 사용 (`00` §4 Axis C)
- `UNDETERMINED`를 `PASS`로 세탁 (`02` §14)

### 0.5 "수집 파라미터"와 "해석 임계값"의 구분

본 문서는 수치를 몇 개 제시한다. 전부 **수집 파라미터**이며 해석 임계값이 아니다.

| 구분 | 성격 | 예 | 허용 여부 |
|---|---|---|---|
| 수집 파라미터 | 수집기를 유한 시간에 멈추게 하고 관측을 재현 가능하게 하는 값 | activation 예산, scroll idle 간격, 저장할 후보 수 | 허용. 단 P-C에서 검증·동결 |
| 해석 임계값 | 관측값을 좋음/나쁨·PASS/FAIL로 바꾸는 값 | `MPFED >= 3 → 부적합` | **금지** |

수집 파라미터에 걸린 관측은 **절단(censored)**으로 기록하며, 그 사실이 분석에 그대로 전달돼야 한다(§2.4).

---

## 1. NED / IED 경계 — `FUNCTION_AREA_REACHED`

> 구체화 대상: `00_SSOT` §3 · §7 / `01_DATA_SPEC` §3 · §6 / `02_COLLECTION` §6 · §7 · §9
> 닫는 finding: `ned-ied-split-not-operationalized`

`00` §7은 NED를 "대표기능이 있는 **영역**에 도달하기까지", IED를 "그 영역에서 endpoint까지"로 정의한다.
`02`는 endpoint 신호(§7)만 규정하고 **영역 도달 신호를 규정하지 않는다.** 이 절이 그 신호를 정의한다.

### 1.1 두 신호의 정의

관측 state 열을 `s0`(랜딩) → `a1` → `s1` → … → `an` → `sn`으로 둔다.
`a_i`는 `02` §9가 activation으로 인정한 조작만을 가리킨다.

**`FUNCTION_AREA_REACHED`** — state `s_i`가 다음 세 조건을 모두 만족하는 최초 시점.

| 조건 | 판정 |
|---|---|
| PRESENT | 해당 task의 **영역진입 control**(§1.2)이 DOM 및 AX tree에 존재한다 |
| HITTABLE | 그 control이 pointer hit-test에서 최상위 대상으로 반환된다 (overlay에 가로막히지 않는다) |
| NO_FURTHER_ACTIVATION | 그 control에 도달하기 위해 추가 activation이 필요하지 않다. **scroll만으로 도달 가능하면 만족**한다 (`02` §9가 scroll을 activation에서 제외하므로) |

**`FUNCTION_ENDPOINT_REACHED`** — `00` §3 L1 표가 그 archetype에 대해 정의한 상태가 관측된 시점.
이 문서는 endpoint를 **새로 정의하지 않는다.** `02` §7의 종료조건 목록을 그대로 쓴다.

### 1.2 archetype별 신호표

`00` §3 L1 표(검색·뉴스·영상·쇼핑·지도·금융·커뮤니티)와 `00` §6 archetype 7종의 대응이다.

| archetype | 영역진입 control (`FUNCTION_AREA_REACHED`) | endpoint 신호 (`FUNCTION_ENDPOINT_REACHED`, `00` §3) | 1차 판정 소스 |
|---|---|---|---|
| `QUERY` | 검색어 입력 control이 focus 가능한 상태로 노출 (`input[type=search]` / `role=searchbox` / `role=combobox` + 제출 가능한 form 또는 제출 control) | 검색 query가 제출된 순간 | DOM/AX role + form 구조 |
| `CONTENT_OPEN` | 개별 콘텐츠(기사·영상) 항목의 링크·카드가 목록 형태로 노출 | 기사 본문이 열린 순간 / 영상 재생이 시작된 순간 | DOM/AX + URL 패턴 + `<video>` play 이벤트 |
| `ITEM_DETAIL` | 개별 상품 항목의 링크·카드가 목록 형태로 노출 | 상품 상세와 핵심 상품정보가 보인 순간 | DOM/AX + URL 패턴 |
| `PLACE_LOOKUP` | 장소검색 입력 control 또는 장소 항목 목록이 노출 | 장소검색이 제출되거나 장소 상세가 열린 순간 | DOM/AX + URL 패턴 |
| `COMMUNICATION_ENTRY` | 게시물/스레드 목록 또는 작성 진입 control이 노출 | 게시물/스레드/작성영역 진입 **또는 로그인 gate** | DOM/AX + gate 신호 |
| `FINANCIAL_ACTION_ENTRY` | 금융기능 진입 control(조회·이체·인증 진입 등)이 노출 | 금융기능 진입 **또는 로그인/인증 gate가 나타난 순간** | DOM/AX + gate 신호 |
| `UTILITY_ENTRY` | 해당 task의 endpoint를 생성하는 control이 노출 | **`00` §3 표에 행이 없다.** endpoint 정의는 P-A endpoint codebook에서 동결 | P-A 산출물 |

> `UTILITY_ENTRY`는 `00` §3의 7행(검색/뉴스/영상/쇼핑/지도/금융/커뮤니티)에 대응 행이 없다.
> 이 문서는 그 endpoint를 **임의로 만들지 않는다.** `03` P-A의 endpoint codebook이 동결한다.
> 그때까지 `UTILITY_ENTRY` task는 `mapping_status`를 미동결로 유지한다.

"영역진입 control"은 `02` §6의 대표기능 후보 랭킹 절차를 **현재 state에 재적용**해 얻는다.
즉 §5의 후보 랭킹은 L0 전용이 아니라 각 scout state에서 반복 수행되며, state별 SELECTED 후보가 그 state의 영역진입 control이다.

### 1.3 NED / IED 산출식

```
k = min{ i : s_i 에서 FUNCTION_AREA_REACHED 성립 }
m = min{ i : s_i 에서 FUNCTION_ENDPOINT_REACHED 성립 }

NED   = k
IED   = m - k
MPFED = m            ( = NED + IED, 00 §7과 항등 )
```

### 1.4 동시 성립·역전 규칙

| 상황 | 규칙 | 결과 |
|---|---|---|
| `s0`에서 영역 성립 (랜딩에 검색창이 이미 있음) | `k = 0` | `NED = 0` |
| `s0`에서 endpoint까지 성립 (랜딩 자체가 endpoint) | `k = m = 0` | `NED = 0`, `IED = 0`, `MPFED = 0` |
| 한 activation이 영역과 endpoint를 동시에 성립시킴 (`k = m = i`) | 그 activation은 **NED 구간에 귀속** | `IED = 0` |
| endpoint가 영역보다 먼저 관측됨 (`m < k`) | `k := m`으로 소급 확정 | `IED = 0`, `area_signal_status = INFERRED_FROM_ENDPOINT` |
| 영역 성립 후 그 상태가 다시 깨짐 (overlay 재출현 등) | 최초 성립 시점 `k`를 유지한다. 재출현 overlay는 `forced_dismissal_count`(`02` §9)로 별도 기록 | `k` 불변 |

`MPFED = m`은 위 네 경우 모두에서 유지되므로 `00` §7의 `MPFED = NED + IED`와 항상 정합한다.

### 1.5 신호 미관측 시 상태값

`01` §11 `결측을 0으로 바꾸지 않는다`를 그대로 적용한다.

| 관측 결과 | `area_signal_status` | `NED` | `IED` | `MPFED` | `endpoint_status` |
|---|---|---|---|---|---|
| 영역·endpoint 모두 관측 | `OBSERVED` | `k` | `m-k` | `m` | `FUNCTION_ENDPOINT_REACHED` |
| endpoint만 관측 (역전) | `INFERRED_FROM_ENDPOINT` | `m` | `0` | `m` | `FUNCTION_ENDPOINT_REACHED` |
| 영역만 관측, endpoint 전 종료 | `OBSERVED` | `k` | `NULL` | `NULL` | `02` §7의 해당 종료값 |
| 둘 다 미관측 | `NOT_OBSERVED` | `NULL` | `NULL` | `NULL` | `02` §7의 해당 종료값 |

`NULL`을 `0`으로 대체하거나 예산 상한값으로 대체하지 않는다.

> **[V2-C003 시정] auth gate 교차참조.** 위 표의 `02` §7 해당 종료값 중 `AUTH_GATE_REACHED`는
> archetype에 따라 의미가 갈린다. `00` §3이 `FINANCIAL_ACTION_ENTRY`·`COMMUNICATION_ENTRY`
> 두 행의 endpoint 문안에만 gate 조항을 포함시켰기 때문이다.
> **[V2-C004 시정] gate 종류는 두 행이 다르다** — `00` §3 원문은 금융에 "또는 로그인/**인증** gate",
> 커뮤니티에 "또는 **로그인** gate"를 준다. 커뮤니티에서 **본인인증** gate는 endpoint가 아니라
> `02` §7 종료값(`AUTH_GATE_REACHED` / `PERSONAL_DATA_REQUIRED`)으로 기록된다.
> 해당 gate 종류에 한해 gate 도달은 **endpoint 도달**이며 `MPFED`가 산출된다.
> 나머지 5 archetype에서는 종전대로 비-endpoint 종료다.
> 분기 규칙의 정본은 `A2_VOCABULARY_AND_SCHEMA_BINDING.md` §1.5.1a (규칙 E-5~E-10)이며,
> 어느 archetype에서도 **gate를 통과하지 않는다**(규칙 E-7).

### 1.6 판정 cascade

`00` §10 모델 사용 원칙과 `02` §1 우선순위를 그대로 따른다. 결정적 신호를 앞세우고, 모호할 때만 위로 올린다.

| 단계 | 수단 | 산출 |
|---|---|---|
| 1 | DOM / AX (role, accessible name, form 구조, `<video>` 상태), URL 패턴, geometry / hit-test | 결정적 판정 |
| 2 | `02` §6 embedding similarity 랭킹 | 후보 순위 + 유사도 |
| 3 | `02` §10 evidence package → VLM (screenshot crop + DOM/AX 요약 + 허용 label 목록) | JSON classification only |
| 4 | AI reviewer B → arbiter (`00` §9) | 합의/중재 라벨 |
| 5 | `HUMAN_FINAL` (`HUMAN_FINAL_REVIEW_MAX = 5`) | 극소수 |

1단계에서 판정되면 상위 단계를 호출하지 않는다.
어느 단계도 `00` §3이 정의하지 않은 새 endpoint·새 label을 만들 수 없다(`02` §10).
확정 불가 시 `area_signal_status = NOT_OBSERVED` 또는 `ABSTAIN`이며, 억지 분류하지 않는다.

### 1.7 step 단위 귀속 규칙

각 activation은 정확히 한 구간에 귀속된다.

| activation `a_i` | 귀속 |
|---|---|
| `1 <= i <= k` | `NED` |
| `k+1 <= i <= m` | `IED` |
| `i > m` | 발생하지 않는다 (endpoint에서 즉시 종료, `02` §7) |
| 영역 미관측(`NOT_OBSERVED`) 경로의 모든 activation | `UNASSIGNED` |

`02` §9가 activation에서 제외한 행위(문자 단위 입력, passive loading, redirect, server wait, scroll, popup dismiss)는
**어느 구간에도 귀속되지 않으며 step row를 만들지 않는다.** 이들은 §4(episode)와 `forced_dismissal_count`로 간다.

귀속은 `k`와 `m`이 확정된 **scout 종료 시점에 일괄 확정**한다. 실행 중에는 확정할 수 없다.
다만 각 step의 원시 신호(`area_signal_detected` / `endpoint_signal_detected`)를 그때그때 저장하므로
귀속은 저장 데이터만으로 **사후 재계산 가능**해야 한다.

### 1.8 저장 요구

현재 `01`에 이 귀속을 담을 필드가 없다. 다음이 필요하다.

| 표 | 추가 필드 | 값 |
|---|---|---|
| `fact_task_step` | `area_signal_detected` | `0/1` — 기존 `endpoint_signal_detected`와 대칭 |
| `fact_task_step` | `depth_segment` | `NED` / `IED` / `UNASSIGNED` |
| `fact_task_step` | `counts_toward_depth` | `0/1` — `02` §9 activation 인정 여부 |
| `fact_task_entry` | `area_signal_status` | `OBSERVED` / `INFERRED_FROM_ENDPOINT` / `NOT_OBSERVED` |
| `dim_representative_task` | `region_definition` | 그 task의 영역진입 control 정의(자연어) — `endpoint_definition`과 대칭 |
| `dim_representative_task` | `region_signal_type` | 판정 소스 유형 — `endpoint_signal_type`과 대칭 |

`region_definition` / `region_signal_type`의 **서비스별 값 지정은 P-A endpoint codebook과 함께 동결**한다.
이 문서는 필드의 존재와 의미만 확정한다.

---

## 2. L1 Scout activation 예산

> 구체화 대상: `02_COLLECTION` §7 · §9 · §13 / `00_SSOT` §3
> 닫는 finding: `l1-scout-has-no-step-budget`

`02` §7의 종료조건은 전부 **신호 탐지 성공에 의존**한다. 신호가 발화하지 않는 대상
(URL이 바뀌지 않는 SPA, endpoint 휴리스틱 실패, gate 키워드 미탐지)에서 scout는 멈출 근거가 없고,
`L1 얕은 진입`이 full task로 변질된다. 선언적 금지목록(`00` §3 절대 제외)은 사람에게만 작동한다.

### 2.1 예산

| 파라미터 | 기본값 | 근거 |
|---|---|---|
| `MAX_ACTIVATIONS_PER_TASK` | `8` | `00` §3의 7개 endpoint는 전부 **완료가 아닌 진입** 시점이다. 통상 경로는 navigation 진입 1~2 + 영역 내 1~2로 4 이내이며, 8은 그 2배 여유를 둔 값이다 |
| `MAX_STATE_REVISITS` | `2` | 같은 DOM state key로 3번째 도달하면 순환이다 |
| `MAX_SCOUT_WALL_CLOCK_S` | `180` | activation은 안 늘어도 로딩만 반복되는 경우를 끊는다 |
| `MAX_CONSECUTIVE_NO_STATE_CHANGE` | `2` | activation 후 URL·DOM state key가 모두 불변인 상태가 연속되면 진행이 없다 |

네 값 모두 **P-C `E000_V2`에서 검증 후 동결**한다. 기본값은 착수용이다.

### 2.2 예산 소진 시 종료상태

```
UNRESOLVED_DEPTH_BUDGET_EXCEEDED
```

`02` §7의 종료값 `UNRESOLVED`의 **하위 세분값**이다. `02` §7의 7개 종료값 집합을 확장하지 않는다.

> **[V2-C004 시정]** 이 값은 `endpoint_status`가 아니라 **`endpoint_status_detail`** 에 기록한다.
> `endpoint_status`는 `02` §7의 동결 7값만 담고, 하위 세분은 동반 컬럼으로 분리한다 —
> 그래야 동결 집합을 확장하지 않는다는 위 문장이 스키마에서도 참이 된다.
> 배치의 정본은 `A2_VOCABULARY_AND_SCHEMA_BINDING.md` §1.5.2이며 roll-up 규칙도 거기 있다.
> 닫는 결함: `a1-endpoint-status-placement-contradicts-a2` (ssot V2-C002 → V2-C003 OPEN 유지분)

따라서 `endpoint_status = UNRESOLVED`, `endpoint_status_detail = UNRESOLVED_DEPTH_BUDGET_EXCEEDED`,
`endpoint_reached = 0`, `NED`/`IED`/`MPFED`는 §1.5에 따라 `NULL`이다.

### 2.3 이것은 접근성 FAIL이 아니다

`02` §13과 동일한 규범을 적용한다.

> `UNRESOLVED_DEPTH_BUDGET_EXCEEDED`는 **measurement status**다.
> KWCAG 판정으로 전환하지 않는다. `fact_criterion_result`의 어떤 값에도 영향을 주지 않는다.
> "이 서비스는 깊어서 실패했다"는 문장의 근거로 쓸 수 없다.

수집기의 탐색 실패와 서비스의 접근성 결함은 서로 다른 사건이다.

### 2.4 절단(censoring) 취급

예산에 걸린 관측은 "MPFED가 8이었다"가 **아니다.** "8회 안에서는 관측되지 않았다"이다.

| 산출물 | 취급 |
|---|---|
| `MPFED` 분포 (`00` §11 median/IQR/mode/ECDF) | 우측절단으로 표기하고 별도 집계한다. 상한값으로 대입하지 않는다 |
| `ExcessDepth` | 산출하지 않는다 (`MPFED`가 `NULL`이므로) |
| `mart_archetype_summary.endpoint reach` | 분모에 포함, 분자에서 제외. 절단 건수를 별도 컬럼으로 노출한다 |
| `mart_service_summary` | `endpoint_status` 원값과 `endpoint_status_detail`을 함께 전달한다 |

### 2.5 검증 요구

`02` §14 실패주입 목록에 다음 케이스가 추가로 필요하다(P-C/P-D 수행).

- endpoint 신호가 발화하지 않는 대상 → 예산이 실제로 발화하는가
- 순환 navigation 대상 → `MAX_STATE_REVISITS`가 먼저 발화하는가
- 예산 소진 관측이 `MPFED = 8`로 새지 않고 `NULL`로 저장되는가

---

## 3. Dismiss control 수집절차

> 구체화 대상: `00_SSOT` §8 / `01_DATA_SPEC` §5 / `02_COLLECTION` §3 · §5 · §11 · §12
> 닫는 finding: `interrupt-dismiss-fields-have-no-collection-procedure`

`02` §5의 4단계(1차 후보 → 2차 공간검사 → 3차 blocking → 4차 의미분류)에 **5차·6차를 잇는다.**

### 3.1 L0 단계 분할과 순서

`dismiss_succeeded`는 실제 조작을 요구하므로, `02` §3의 "L0에서는 대표기능을 아직 클릭하지 않는다"와
`02` §12 append-only를 동시에 지키려면 순서가 고정돼야 한다.

| 단계 | 내용 | 조작 |
|---|---|---|
| L0-a | `02` §3 수집 전량 (최초 viewport / full-page screenshot / DOM / AX / computed CSS / geometry) | 없음 |
| L0-b | `02` §5 1~4차 + 본 절 5차 (dismiss control 탐색·기하·이름) | 없음 |
| L0-c | 본 절 6차 (dismissal 실제 시도) | **있음** |

**L0-a의 evidence가 확정된 뒤에만 L0-c를 수행한다.** L0-c의 결과물은 L0-a의 evidence를 덮어쓰지 않고
새 relpath로 추가된다(`02` §12, `07_EVIDENCE_MANIFEST_CONTRACT` §3).
`01` §4의 요약 변수(`max_overlay_coverage`, `primary_action_visible_initial` 등)는 **L0-a 상태에서만** 산출한다.

### 3.2 5차 — dismiss control 검사 (조작 없음)

각 `fact_interrupt_element` 행마다 독립 수행한다.

| 필드 | 절차 |
|---|---|
| `dismiss_control_exists` | interrupt 요소의 subtree와 그 backdrop/`aria-labelledby` 컨테이너 안에서 후보를 찾는다. 후보 source: ① `<dialog>`의 `form[method=dialog]` submit ② `role=button` / `<button>` / `role=link`로 accessible name이 닫기 어휘에 해당 ③ `aria-label` / `title`이 닫기 어휘 ④ 텍스트 노드가 `×` `✕` `X` 등 닫기 기호 ⑤ 닫기 아이콘 전용 버튼(가시 텍스트 없음). 하나 이상이면 `1`, 없으면 `0` |
| `dismiss_control_visible` | `exists=1`일 때만 산출. bbox 면적 > 0, computed style의 `display`/`visibility`/`opacity`가 비가시가 아님, viewport 교차면적 > 0, hit-test가 그 control을 반환 — 전부 만족하면 `1`. `exists=0`이면 `NULL` |
| `dismiss_control_accessible_name` | **브라우저 AX tree의 computed name을 그대로 저장**한다. 이름이 비어 있으면 빈 문자열이 아니라 `NAME_ABSENT`로 기록한다. VLM이 아이콘을 보고 추정한 이름을 이 필드에 넣지 않는다 — 추정은 `fact_ai_adjudication`에 남기고 이 필드는 브라우저 계산값 전용이다 |
| `dismiss_control_width` / `_height` | L0-a와 같은 geometry 스냅샷에서 border-box 렌더 사각형을 CSS px로 저장한다. device pixel ratio를 곱하지 않는다. `transform`이 적용된 경우 실제 렌더 사각형을 쓴다. `exists=0`이면 `NULL` |

닫기 어휘 목록(`닫기` `확인` `취소` `close` `dismiss` `skip` `나중에` `오늘 하루 보지 않기` …)은
**탐지 사전이며 판정 기준이 아니다.** 목록 자체는 P-C에서 동결한다.
"오늘 하루 보지 않기" 유형은 dismiss control로 인정하되 `dismiss_persistence_hint = 1`로 구분 기록한다
(다음 회차 관측이 달라질 수 있다는 사실을 남기기 위함이며, 판정에 쓰지 않는다).

조작 대상 크기의 KWCAG 판정은 여기서 하지 않는다. `fact_criterion_result` 소관이며,
본 절은 `00` §8이 지시한 **기록**만 수행한다.

### 3.3 6차 — dismissal 시도

| 항목 | 규칙 |
|---|---|
| 시행 횟수 | 한 interrupt 당 **정확히 1회** |
| 대상 | `dismiss_control_visible = 1`인 control. 없으면 `<dialog>` close, `Escape` 키, backdrop click 순으로 대체 경로를 시도한다 |
| 사용 경로 기록 | `dismiss_method ∈ {CONTROL_CLICK, DIALOG_CLOSE, ESCAPE_KEY, BACKDROP_CLICK, NONE}` |
| 안정화 | `02` §3과 동일한 고정 대기 규칙을 적용한 뒤 재검사한다 |
| 성공 판정 (`dismiss_succeeded = 1`) | 재검사에서 ① 해당 요소가 DOM에서 제거됐거나 ② viewport 교차면적이 0이거나 ③ hit-test 가로막기가 사라짐 — 하나 이상 성립 |
| 실패 사유 | `dismiss_failure_mode ∈ {NO_CONTROL, NOT_HITTABLE, NO_STATE_CHANGE, NEW_INTERRUPT_APPEARED, NAVIGATED_AWAY}` |
| 이탈 | dismissal이 페이지 이동을 유발하면 즉시 중단하고 `NAVIGATED_AWAY`로 기록한다. 그 관측의 L0 값은 **L0-a 스냅샷을 유지**하며 이동 후 화면으로 갱신하지 않는다 |
| 시도 불가 | `dismiss_control_exists = 0`이고 대체 경로도 모두 실패하면 `dismiss_succeeded = 0`, `dismiss_method = NONE` |

`dismiss_succeeded`는 `blocks_primary_action`(`02` §5 3차)과 **독립 변수**다.
닫기에 성공했다고 blocking이 아니었던 것이 아니며, 그 반대도 아니다.

L1의 `forced_dismissal_count`(`02` §9)와도 별개다. 전자는 L0에서의 닫기 가능성 측정,
후자는 L1 경로에서 실제로 닫아야 했던 횟수다. 두 값을 합산하지 않는다.

### 3.4 evidence 요구

dismissal 시도는 **반드시 before/after evidence를 남긴다.**

| evidence | 시점 |
|---|---|
| `dismiss_screenshot_before` | 시도 직전 viewport |
| `dismiss_screenshot_after` | 안정화 대기 후 viewport |
| `dismiss_dom_after` | 안정화 대기 후 DOM 스냅샷 (성공 판정의 근거) |

세 파일은 같은 `observation_id`에 서로 다른 `relpath`로 run manifest에 등록한다
(`07_EVIDENCE_MANIFEST_CONTRACT` §3 — `(observation_id, relpath)` 중복 금지).
L0-a의 evidence를 덮어쓰지 않는다.

이 세 경로를 담을 컬럼이 `01` §5에 없다. `fact_interrupt_element`에
`dismiss_screenshot_before` / `dismiss_screenshot_after` / `dismiss_dom_after` /
`dismiss_method` / `dismiss_failure_mode` / `dismiss_persistence_hint` 추가가 필요하다.

---

## 4. Episode 정의

> 구체화 대상: `00_SSOT` §7 / `01_DATA_SPEC` §6 / `02_COLLECTION` §7 · §9 / `04_GLOSSARY`
> 닫는 finding: `episode-counters-undefined-and-uncollected`

`00` §7은 text input과 scroll을 "별도 기록"하고 "Depth와 합치지 않는다"고 지시했다.
`01` §6은 `text_input_episode_count` / `scroll_episode_count` 컬럼을 뒀다.
`02`는 이 둘을 activation에서 제외만 하고 정의도 적재처도 주지 않았다.

### 4.1 episode는 activation과 별개 축이다

| | activation | episode |
|---|---|---|
| 정의처 | `02` §9 | 본 절 |
| Depth 기여 | `NED`/`IED`/`MPFED`에 가산 | **가산하지 않는다** (`00` §7) |
| 저장 | `fact_task_step` 한 행 | `fact_task_episode` 한 행 (§4.4) |
| 귀속 | `depth_segment` (§1.7) | 없음. 발생 시점의 state만 기록 |

두 값을 더해 "총 조작 수" 같은 합성 변수를 만들지 않는다.

### 4.2 `text_input_episode`

> 하나의 입력 control에 대해, **focus 획득부터 그 focus가 끝날 때까지의 연속 입력 구간 1개.**

| 규칙 | 내용 |
|---|---|
| 시작 | 대상 control이 focus를 얻고 첫 문자가 입력된 시점 |
| 종료 | blur / submit / 다른 control로 focus 이동 / state 전이 / scout 종료 중 먼저 오는 것 |
| 문자 수 | episode 수와 무관하다. 100자를 넣어도 1 episode |
| 재입력 | 같은 control에 focus가 다시 잡혀 입력이 재개되면 **새 episode** |
| IME | 한글 조합 중인 문자를 개별 episode로 쪼개지 않는다 |
| 자동입력 | 수집기가 프로그램적으로 값을 주입한 경우도 1 episode로 센다. 단 `input_mode = PROGRAMMATIC`으로 구분 기록 |

이 정의는 `02` §9의 `텍스트 한 글자씩 입력` 제외 규칙과 정합한다 — 문자는 activation이 아니고,
입력 행위 자체는 episode 축에서만 센다.

### 4.3 `scroll_episode`

> 하나의 scroll container에 대한 **연속 scroll 입력 구간 1개.**

| 규칙 | 내용 |
|---|---|
| 시작 | 해당 container의 scroll offset이 변하기 시작한 시점 |
| 종료 | 다음 중 먼저 오는 것 — ① scroll idle이 `SCROLL_IDLE_MS` 이상 지속 ② scroll 방향 반전 ③ activation 발생 ④ scroll container 변경 ⑤ state 전이 |
| `SCROLL_IDLE_MS` | 기본 `500`. **P-C에서 검증 후 동결** |
| 거리 | episode 수와 무관하다. `02` §9가 scroll distance를 activation에서 제외하므로 거리는 보조 기록(`scroll_distance_px`)으로만 남긴다 |
| 수집기 자동 스크롤 | full-page screenshot 캡처를 위한 프로그램적 스크롤은 **episode가 아니다.** 사용자 행동 모사가 아니므로 카운트하지 않는다 |

### 4.4 저장 위치

`fact_task_step`은 "한 행 = 사용자 activation 한 번"이므로 episode를 담을 수 없다.
`01` §6 두 카운터의 상류가 되는 표가 필요하다.

**제안 표 `fact_task_episode`** (매핑/머티리얼라이제이션 레이어 신규 산출물)

| 컬럼 | 의미 |
|---|---|
| `task_observation_id` | `fact_task_entry` FK |
| `episode_index` | 관측 내 일련번호 |
| `episode_kind` | `TEXT_INPUT` / `SCROLL` |
| `target_selector` | 입력 control 또는 scroll container |
| `state_id` | 발생 시점의 DOM state key |
| `started_after_step_index` | 직전 activation의 `step_index` (없으면 `0`) |
| `ended_by` | `BLUR` / `SUBMIT` / `FOCUS_MOVED` / `STATE_CHANGE` / `IDLE` / `DIRECTION_REVERSAL` / `ACTIVATION` / `CONTAINER_CHANGE` / `SCOUT_END` |
| `input_mode` | `TEXT_INPUT`일 때 `HUMAN_SIMULATED` / `PROGRAMMATIC` |
| `scroll_distance_px` | `SCROLL`일 때 보조 기록 |

```
fact_task_entry.text_input_episode_count = count(episode_kind = 'TEXT_INPUT')
fact_task_entry.scroll_episode_count     = count(episode_kind = 'SCROLL')
```

또한 `02` §7의 activation별 기록목록(URL / DOM state key / screenshot / clicked control /
endpoint signal / popup / auth gate)에 **`text input episode` / `scroll episode`가 없다.**
scout는 두 episode의 시작·종료를 기록해야 위 표를 채울 수 있다.

---

## 5. Primary action identity

> 구체화 대상: `00_SSOT` §8 / `01_DATA_SPEC` §4 · §5 / `02_COLLECTION` §3 · §6 · §12
> 닫는 finding: `primary-action-identity-not-stored`

`00` §8: `PrimaryActionOcclusion = 대표기능 control이 overlay에 가려진 면적 / 대표기능 control 면적`.
`01`이 저장하는 것은 `primary_action_visible_initial` · `max_primary_action_occlusion` ·
`blocks_primary_action` · `primary_action_occlusion` — **전부 파생 스칼라**다.
**분모(대표기능 control 면적)를 저장 데이터로 재구성할 수 없어 재판정이 불가능하다.**
`02` §12가 전제하는 "같은 evidence 재판정 → 새 judgment version"이 성립하지 않는다.

### 5.1 제안 표 `fact_primary_action_candidate`

`02` §6이 추출·랭킹한 후보를 **소실시키지 않고** 저장한다.

| 컬럼 | 의미 |
|---|---|
| `observation_id` | `fact_landing_observation` FK |
| `candidate_id` | 관측 내 후보 식별자 |
| `task_id` | 어느 대표 task 기준의 랭킹인가 |
| `rank` | 랭킹 순위 (1이 최상위) |
| `selector` | 재현 가능한 selector |
| `control_role` | AX role |
| `accessible_name` | AX computed name |
| `visible_text` | 가시 텍스트 |
| `nearby_heading` | `02` §6 추출항목 |
| `href` | 링크인 경우 |
| `bbox_x` `bbox_y` `bbox_w` `bbox_h` | CSS px, L0-a 기준 |
| `area_css_px2` | `bbox_w × bbox_h`. **`PrimaryActionOcclusion`의 분모** |
| `viewport_visible` | 최초 viewport 가시 여부 |
| `similarity_score` | `02` §6 embedding similarity |
| `selection_basis` | `DETERMINISTIC_RULE` / `EMBEDDING_RANK` / `AI_REVIEW` / `HUMAN_FINAL` |
| `selection_status` | `SELECTED` / `RUNNER_UP` / `REJECTED` |
| `selection_confidence` | 선정 신뢰도 |
| `ai_review_status` | `02` §6 `모호하면 AI review` 경유 여부 |
| `evidence_package_id` | AI review를 탔다면 `fact_ai_adjudication` 연결 |

저장 후보 수 기본값 `TOP_N_CANDIDATES = 5`. **P-C에서 동결.**
`SELECTED`는 관측·task당 최대 1행이며, 0행이면 `primary_action_visible_initial = NULL`이다(`0`이 아니다).

### 5.2 기존 파생 스칼라와의 연결

```
fact_landing_observation.primary_action_visible_initial
    = SELECTED 후보의 viewport_visible

fact_interrupt_element.primary_action_occlusion
    = (그 interrupt가 SELECTED 후보 bbox를 가린 면적) / SELECTED 후보의 area_css_px2

fact_landing_observation.max_primary_action_occlusion
    = max over interrupts ( primary_action_occlusion )
```

세 값 모두 L0-a 상태에서 산출한다(§3.1). 분자·분모가 모두 저장되므로 제3자 재계산이 가능하다.

### 5.3 §1과의 관계

L0의 `SELECTED` 후보는 **NED 경로의 첫 목표**다.
§1.2의 "영역진입 control"은 각 scout state에서 같은 랭킹 절차를 재적용해 얻은 그 state의 `SELECTED` 후보다.
따라서 이 표는 L0 관측뿐 아니라 scout state에도 확장될 수 있다 —
그 경우 `observation_id` 대신 `task_observation_id` + `state_id`로 grain을 잡는다. 확장 여부는 P-C에서 결정한다.

### 5.4 레이어 귀속

> `fact_primary_action_candidate`와 §4.4의 `fact_task_episode`는 **매핑/머티리얼라이제이션 레이어의
> 신규 산출물**이다. 기존 `state/*.parquet` 파일을 삭제·rename·migration하지 않는다 (`01` 서두).

---

## 6. L0 evidence 저장 슬롯

> 구체화 대상: `01_DATA_SPEC` §4 / `02_COLLECTION` §2 · §3 · §11 · §12 / `07_EVIDENCE_MANIFEST_CONTRACT`
> 닫는 finding: `l0-evidence-artifacts-without-storage-slot`

`02` §3은 최초 viewport screenshot과 full-page screenshot **두 종류**를 수집하는데
`01` §4는 `screenshot_path` 단수다. computed CSS의 귀속도 불명이다.
`02` §2는 수집시각을, `01` §4는 `audit_date`(일 단위)를 규정해 **같은 날 재수집한 두 run이 구분되지 않는다.**

### 6.1 `fact_landing_observation` 확장 제안

| 컬럼 | 의미 | 비고 |
|---|---|---|
| `screenshot_initial_path` | 최초 viewport screenshot | 기존 `screenshot_path`의 의미를 이것으로 확정 |
| `screenshot_fullpage_path` | full-page screenshot | 신규. `02` §11 identity 집합에 명시 필요 |
| `computed_css_path` | computed CSS 덤프 | `probe_path`와 **별도 파일**로 분리한다. probe는 `02` §4 raw feature 전용 |
| `evidence_run_id` | `evidence/<run_id>` | `07` 계약의 run grain 연결 |
| `collection_started_at` | 수집 시작 시각 (UTC, ISO-8601) | `02` §2 `수집시각 기록` |
| `collection_finished_at` | 수집 종료 시각 (UTC, ISO-8601) | 안정화 대기 포함 여부를 명확히 |
| `audit_date` | 기존 유지 | `collection_started_at`을 `Asia/Seoul` 기준으로 파생. 독립 입력이 아니다 |
| `viewport_configured_width` / `_height` | 프로토콜 설정값 | `02` §2의 `390 × 844` |
| `viewport_width` / `viewport_height` | 기존 컬럼. **실측 layout viewport**로 의미 확정 | 설정값과 다를 수 있다 |
| `device_pixel_ratio` | 실측 DPR | screenshot px ↔ CSS px 환산 근거 |

### 6.2 evidence identity 정합

`02` §11 · `07_EVIDENCE_MANIFEST_CONTRACT`와 어긋나지 않게 다음을 지킨다.

| 규약 | 근거 |
|---|---|
| `01`의 모든 `*_path` 컬럼은 **run 디렉터리 기준 상대경로**를 저장한다. 절대경로·`..` 금지 | `07` §3 |
| 위 경로 전량이 `evidence/<run_id>/manifest.jsonl`에 `(observation_id, relpath, sha256, bytes)`로 등록된다 | `07` §3 |
| `(observation_id, relpath)` 중복 금지 — 두 screenshot이 서로 다른 relpath를 가져야 하는 이유 | `07` §4 |
| `manifest_path`는 **run manifest 경로이며 관측마다 고유하지 않다.** 한 run의 전 관측이 같은 값을 공유한다 | `07` §3 grain |
| `02` §11의 identity 집합을 `DOM / AX / screenshot(initial) / screenshot(fullpage) / computed CSS / probe / manifest`로 읽는다 | `02` §11 + `02` §3 |
| 재수집은 새 `evidence_run_id`를 만든다. 기존 run을 덮어쓰지 않는다 | `02` §12 · `07` §4 |

### 6.3 `observation_id` 산출

`02` §11: `display name을 file id로 사용하지 않는다. hash-based observation id 사용.`

같은 날 재수집을 구분하려면 해시 입력에 시각이 들어가야 한다.

```
observation_id = hash( web_target_id, evidence_run_id, requested_url,
                       protocol_version, collection_started_at )
```

해시 함수·정규화 규칙·자릿수는 **P-C에서 동결**한다. 이 문서는 입력 집합만 확정한다.
`audit_date`만으로 관측을 식별하지 않는다.

### 6.4 L0-c evidence

§3.4의 dismissal before/after 산출물도 같은 run manifest에 등록되며,
`fact_interrupt_element`의 경로 컬럼(§3.4)으로 참조한다. `fact_landing_observation`에는 넣지 않는다 —
grain이 interrupt 단위이기 때문이다.

---

## 7. P-C에서 검증·동결할 항목

이 문서가 **기본값만 제시하고 확정하지 않은** 항목이다. `03` P-C(L0/L1 Engine) 및 P-D(`E000_V2`)에서 닫는다.

| 항목 | 기본값 | 동결 단계 | 비고 |
|---|---|---|---|
| `MAX_ACTIVATIONS_PER_TASK` | `8` | P-C → P-D 검증 | §2.1 |
| `MAX_STATE_REVISITS` | `2` | P-C → P-D 검증 | §2.1 |
| `MAX_SCOUT_WALL_CLOCK_S` | `180` | P-C | §2.1 |
| `MAX_CONSECUTIVE_NO_STATE_CHANGE` | `2` | P-C | §2.1 |
| `SCROLL_IDLE_MS` | `500` | P-C | §4.3 |
| `TOP_N_CANDIDATES` | `5` | P-C | §5.1 |
| 닫기 어휘 사전 | 미확정 | P-C | §3.2 |
| `observation_id` 해시 함수·정규화 | 미확정 | P-C | §6.3 |
| `fact_primary_action_candidate`의 scout state 확장 여부 | 미확정 | P-C | §5.3 |

이 문서가 **의도적으로 미루는** 항목 — 여기서 못박지 않는다.

| 항목 | 소관 |
|---|---|
| 서비스별 대표기능 지정 · `endpoint_definition` · `region_definition` 값 | P-A endpoint codebook → P-B task frame 동결 |
| `UTILITY_ENTRY`의 endpoint 정의 | P-A (`00` §3에 대응 행 없음, §1.2) |
| KWCAG criterion subset 확정 | `00` §15 · `03` P-C |
| `measurement_status` 등 상태값 허용값 집합 (ssot F6·F7) | `A2_VOCABULARY_AND_SCHEMA_BINDING.md` |
| gate 이름 정본화 (ssot F8) | `PHASE_GATES.md` |
| 논리표 ↔ 물리 `state/*` 대응표 (ssot F12) | `A2_VOCABULARY_AND_SCHEMA_BINDING.md` / P-A 최초 산출물 |

---

## 8. 이 문서를 읽고 나서 하지 말 것

- §2의 `MAX_ACTIVATIONS_PER_TASK = 8`을 "8단계 넘으면 접근성이 나쁘다"로 읽는 것 — 수집 예산이지 해석 임계값이 아니다(§0.5, §2.3).
- 예산에 걸린 관측의 `MPFED`를 `8`로 채우는 것 — `NULL`이다(§1.5, §2.4).
- `dismiss_succeeded = 0`을 KWCAG `FAIL`로 전환하는 것 — 별개 축이다(`00` §4 Axis B).
- `text_input_episode_count` / `scroll_episode_count`를 Depth에 더하는 것 — `00` §7이 금지한다.
- §1.6 cascade의 AI 단계에서 `00` §3에 없는 새 endpoint를 만드는 것 — `02` §10이 금지한다.
- `NED = 0`을 "진입이 쉽다"로 해석해 점수화하는 것 — 랜딩에 control이 있었다는 관측 사실일 뿐이다.
