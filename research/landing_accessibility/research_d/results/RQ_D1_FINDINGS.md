# RQ-D1 — E001 Pilot Failure Anatomy 독립 재구성

**verdict**: `SUPPORTED` (재구성 성공) + 신규 **P1 finding 2건**
**claim_kind**: OBSERVATION (F1~F3, F6~F9) / ANALYSIS (F4~F5)
**입력**: raw evidence 4 worker root + frozen mart (`claude_b_analysis_current@82f631f`)
**재현**: `.venv/bin/python research_d/tools/rq_d1_reconstruct.py`
**산출**: `results/RQ_D1_reconstruction.json`
**A/B/C 보고문 사용**: 없음. 전량 raw에서 재계산.

---

## RQ

E001 파일럿의 "59/59 attempted, MPFED 0/59"는 정확히 **어느 지점에서** 무엇을 잃었는가?
그리고 raw 66 관측디렉터리와 mart 56행 사이의 차이는 무엇으로 설명되는가?

## 왜 중요한가

v2.1 복구 로드맵(02 §6)은 offline replay 모집단을 **"E001 mart referenced frozen
DOM/evidence 56"**으로 고정한다. 그 56이 어떻게 만들어졌는지 검증되지 않으면
복구 검증 자체가 편향된 모집단 위에서 이뤄진다.

---

## 분모 사슬 (grain 명시)

| 단계 | 수 | 단위 |
|---|---|---|
| observation 디렉터리 | **66** | evidence dir |
| distinct web_target_group | **59** | target |
| 증거가 하나라도 있는 target | **56** | target |
| `fact_landing_observation` | **56** | target (= observation 1:1) |
| `fact_task_entry` | **31** | target |
| NED/IED/MPFED non-null | **0** | task row |
| `fact_criterion_result` | **0** | criterion row |

총 raw bytes: 753,676,839 (753.7 MB) · sealed dir 60 / 66 · empty dir 6 / 66.

---

## F1 (OBSERVATION) — 66 대 59의 차이는 단일 현상이 아니다

7개 target이 2회씩 관측됐다(66 − 59 = 7). 그런데 이 7건은 **두 개의 서로 다른
기계적 지문**으로 완전히 분리된다.

| class | n | 시간간격 | worker | 산출물 | 판정 |
|---|---|---|---|---|---|
| SHORT | **4** | 6.25 / 6.28 / 6.95 / 7.57 s | 전부 w02 | 양쪽 모두 sealed, artifact 수 **쌍마다 동일** (6·6, 15·15, 33·33, 12·12) | `DUPLICATE_LAUNCH_BOTH_COMPLETE` |
| LONG | **3** | 46.49 / 46.59 / 46.66 s | w02×1, w03×2 | 양쪽 모두 **완전히 빈 디렉터리** (run.json·manifest 없음) | `RETRY_BOTH_EMPTY` |

두 군집 사이(8s~46s)에는 관측이 **하나도 없다**. 46.5s ± 0.09s의 극단적 응집은
고정 timeout의 지문이지 우연한 재시도 분포가 아니다.

## F2 (ANALYSIS) — "retry냐 duplicate launch냐" 논쟁은 둘 다 부분적으로 옳다

- B 계열 주장 "extra run은 retry다" → **LONG 3건에 대해서만 참**.
- C 계열 주장 "duplicate launch다" → **SHORT 4건에 대해서만 참**.

SHORT 4건은 첫 시도가 **완전히 성공해 sealed된 뒤** 6~7초 만에 동일 target을
처음부터 다시 수집했다. 실패 후 재시도가 아니다. 03 §10의 idempotency key가
없었다는 직접 증거다. LONG 3건은 46.5s timeout → 재시도 → **재시도도 실패**로,
exactly-once 위반이 아니라 수집 실패다.

> 단일 숫자 "7"로 이 둘을 묶어 보고하면 어느 쪽 시정조치도 정확해지지 않는다.

## F3 (OBSERVATION) — SHORT 4건은 mart에서 정상 dedup됐다

`fact_landing_observation` 56행의 `observation_id` 중복 = **0**,
`fact_interrupt_element` 235행의 orphan observation = **0**.
즉 duplicate launch가 downstream 이중계산으로 번지지는 **않았다**.

## F4 (ANALYSIS · **신규 P1**) — 3 target이 분모에서 조용히 사라졌다

mart에 없는 3 target = `2cd43b99c1ed87cf`, `dd5061eb74e2d4d4`, `ff3ee504792f6cfc`
= **LONG 재시도 실패 3건과 정확히 동일 집합**.

이들은 `measurement_status = NO_EVIDENCE` 같은 행으로도 남지 않고 **행 자체가 없다**.
결과적으로 분모가 59 → 56으로 줄었는데, mart만 읽는 downstream은 이 손실을 볼 수 없다.

**이것은 informative missingness다.** 사라진 3건은 무작위가 아니라
"46초 timeout을 두 번 유발한 사이트", 즉 체계적으로 어려운 사이트다.
02 §6이 복구 검증 모집단으로 지정한 56은 **어려운 쪽 꼬리가 잘려나간 56**이다.

→ 최소 조치: mart에 `NO_EVIDENCE` 3행을 명시적으로 남기고, 모든 rate의 분모를
`59 attempted / 56 evidence-bearing`로 이중표기.

## F5 (ANALYSIS · **신규 P1**) — 56 → 31의 25 target 손실도 동일한 방식으로 조용하다

`fact_landing_observation` 56 target 중 `fact_task_entry` 행이 **하나도 없는** target = **25**.
이 25는 baseline이 말한 target-level guard block 25/59와 수치가 일치한다(00 §2 G1).

문제는 수치가 아니라 **표현 방식**이다. guard로 막힌 target이 "task 관측 시도했으나
차단됨" 행으로 남는 게 아니라 아예 행이 없다. 따라서 Axis B 분모를 mart에서
자동으로 계산하면 31이 되고, 차단된 25는 **분석에서 존재하지 않는 것처럼 보인다**.

## F6 (OBSERVATION) — Axis B는 partial NED조차 0이다

`fact_task_entry` 31행 전부에서 NED·IED·MPFED = null (non-null 0/31).

SSOT 00 §8.4는 "endpoint 미도달이어도 대표기능 영역까지 관측되면 **NED는 보존**"을
요구한다. 31행 중 `AUTH_GATE_REACHED` 11, `PAYMENT_GATE_REACHED` 1은 경로를 실제로
전진한 관측인데도 NED가 비어 있다. 즉 **G3(detector)만이 아니라 partial-depth
보존 로직 자체가 미구현**이다. "MPFED 0/59"를 detector 결함 하나로 설명하면 부족하다.

endpoint_status 분포 (n=31): UNRESOLVED 18 · AUTH_GATE_REACHED 11 · CAPTCHA 1 · PAYMENT_GATE_REACHED 1.

## F7 (OBSERVATION) — Axis A는 byte 수준에서 비어 있다

`fact_criterion_result.json` = 2 bytes (`[]`), 행 0.
"Axis A NOT_EVALUATED"는 해석이 아니라 **파일 바이트 사실**이다. G4 확인.

## F8 (OBSERVATION) — Axis C만 실제 데이터를 갖고 있다

`max_overlay_coverage` 56/56 non-null, median **0.1281**, max **1.0**.
`max_primary_action_occlusion` 56/56 non-null.
`fact_interrupt_element` 235행 / 51 observation.

세 축 중 즉시 재사용 가능한 유일한 축이다(00 §10, D-14와 일치).
단 primary_action_occlusion은 task binding이 없는 상태에서 계산된 값이므로
"대표행동 가림"으로 해석할 수 없다 — **page-level 값으로만 유효**하다.

## F9 (OBSERVATION · **archetype 편중**) — QUERY가 0이다

`fact_task_entry` 31행의 archetype 분포:

| archetype | n | 00 §12 n-rule |
|---|---|---|
| ITEM_DETAIL | **16** (51.6%) | 정상 |
| PLACE_LOOKUP | 4 | LOW_N |
| FINANCIAL_ACTION_ENTRY | 4 | LOW_N |
| CONTENT_OPEN | 3 | LOW_N |
| COMMUNICATION_ENTRY | 2 | 과해석 금지 |
| UTILITY_ENTRY | 2 | 과해석 금지 |
| **QUERY** | **0** | **부재** |

7개 frozen archetype 중 **QUERY는 아예 없다**. ExcessDepth는 same-archetype median
기준이므로, 이 구성에서는 ITEM_DETAIL 외의 모든 archetype에서 baseline median이
n≤4로 추정된다. 즉 **현 파일럿 데이터로는 ExcessDepth가 archetype 6개 중 5개에서
통계적으로 의미가 없다**.

---

## 반례 / 대안설명 검토

- *"SHORT 4건은 사실 서로 다른 URL의 우연한 해시 충돌"* → 반박됨. wtg id가 동일하고
  screenshot 바이트 크기까지 쌍마다 일치(328,324 / 233,653).
- *"LONG 3건 빈 디렉터리는 사후 정리로 지워진 것"* → 미배제. 디렉터리 mtime(14:16~14:20)이
  다른 디렉터리와 같은 대역이라 "생성만 되고 채워지지 않음"이 더 단순한 설명이나,
  runner 로그를 보지 않고는 확정할 수 없다. → RQ-D1b로 이월.
- *"25 guard block은 mart 밖 다른 테이블에 있다"* → 현재 mart 디렉터리 파일 목록에는
  guard/skip fact 테이블이 없다. 다른 브랜치에 존재할 가능성은 미확인.

## Limitations

1. mart는 `claude-b/analysis-current@82f631f` 한 스냅샷만 검사했다. `handoff/landing-b`
   사본은 fact_*.json이 없어 비교 불가.
2. 재시도/타임아웃 판정은 디렉터리 타임스탬프와 산출물 유무에서 **역추론**한 것이고
   runner 로그를 직접 읽은 것이 아니다. (T2 수준이지 T1 수준의 runtime log 확인 아님)
3. 3건 total-failure target의 실제 URL/서비스 정체는 확인하지 않았다 — 어떤 종류의
   사이트가 잘려나갔는지는 F4의 편향 크기를 정하는 데 필요하다. → RQ-D1c.

## Production implication (제안일 뿐, 반영은 A/B의 권한)

- **P1**: mart에 evidence 부재·guard 차단을 **행으로** 남길 것. 분모 손실이 조용해선 안 된다.
- **P1**: real launch idempotency key(03 §10)는 "실패 후 재시도"와 "성공 후 재실행"을
  구분해야 한다. 현재 7건을 하나로 세면 억제 로직이 재시도까지 막거나 중복을 놓친다.
- **P1**: partial NED 보존을 detector 복구와 **별개 항목**으로 검증할 것(F6).
- **P2**: 복구 검증 모집단을 56이 아니라 "59 attempted 중 56 evidence-bearing, 3 결측"으로
  명시하고, 결측 3건의 사이트 특성을 sensitivity에 넣을 것.

## 후속 연구질문

- **RQ-D1b**: runner 로그에서 LONG 3건의 종료 사유를 직접 확인 (timeout? WAF? navigation error?)
- **RQ-D1c**: total-failure 3 target의 서비스 정체·archetype prior → F4 편향 크기 추정
- **RQ-D2**: guard 25건이 archetype coverage를 어떻게 왜곡했는가 (QUERY 0의 원인)
- **RQ-D6 (신규)**: partial-depth(NED) 보존 미구현이 detector 결함과 독립인지 검증
