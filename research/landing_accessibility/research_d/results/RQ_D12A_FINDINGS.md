# RQ-D12a — 세 신호는 SPA 렌더 시점 하나가 아니다

**verdict**: `REFUTED` (H1_SPA_TIMING) · **H2_DISTINCT 지지**
**정정 대상**: RQ-D12 F2 에서 D 가 한 추측 — "셋 다 SPA 렌더 시점 문제와 방향이 같다"
**재현**: `.venv/bin/python research_d/tools/rq_d12a_spa_timing.py`
**산출**: `results/RQ_D12A_spa_timing.json`

---

## RQ

RQ-D12 F2 에서 세 flag 만 서로 묶였다
(`low_structural_richness` ↔ `degenerate_or_dup` φ +0.459, ↔ `slot_mismatch` +0.442).
그때 나는 **"셋 다 SPA 렌더 시점 문제와 방향이 같다"** 고 추측했다. 그 추측을 가른다.

## 판별 논리 (먼저 적는다)

SPA 렌더 시점 문제라면 **DOM 은 빈약한데 probe(렌더 후)는 풍부**해야 한다.
진짜로 빈약한 페이지라면 **DOM 도 probe 도 둘 다 빈약**하다.

| 서명 | 정의 |
|---|---|
| `SIGNATURE_SPA` | `dom_interactive_n` ≤ 중앙값 **AND** `n_primary_action_candidates` > 중앙값 |
| `SIGNATURE_SPARSE` | 둘 다 ≤ 중앙값 |
| `BOTH_RICH` / `DOM_RICH_PROBE_POOR` / `NO_PROBE` | 나머지 |

절단점은 `in_mart` 표본 중앙값 (`dom_interactive_n` 90.5, `n_primary_action_candidates` 49.5).
RQ-D12 의 q25 와 다른 기준을 쓴 이유는 여기서는 곤란도 flag 재현이 아니라 **상대 비교**이기 때문이며,
이 사실을 결과 JSON `thresholds.note` 에 남겼다.

---

## F1 (ANALYSIS) — 구조빈약의 **73%는 진짜 빈약한 페이지**다

`low_structural_richness` 15건의 내역:

| 서명 | n | 비율 |
|---|---|---|
| **`SIGNATURE_SPARSE`** | **11** | **73.3%** |
| `SIGNATURE_SPA` | 2 | 13.3% |
| `NO_PROBE` | 2 | 13.3% |

SPA 서명은 15건 중 **2건**뿐이다. **추측이 틀렸다.**

## F2 (OBSERVATION) — 퇴화 4건에는 SPA 서명이 **0건**이다

| flag | n | 서명 분포 |
|---|---|---|
| `f_low_richness` | 15 | SPARSE 11 · SPA 2 · NO_PROBE 2 |
| `f_slot_mismatch` | 6 | SPARSE 3 · SPA 2 · BOTH_RICH 1 |
| `f_degenerate` | 4 | NO_PROBE 2 · SPARSE 2 · **SPA 0** |

`slot_mismatch` 만 SPA 서명을 절반 가까이(2/6) 갖는다. 나머지 둘은 아니다.
**세 flag 가 묶인 것은 사실이지만, 공통 원인이 SPA 렌더 시점은 아니다.**

## F3 (OBSERVATION) — 경과시간도 구분하지 못한다

`dom → probe` 경과의 서명별 중앙값:

| 서명 | median (s) |
|---|---|
| BOTH_RICH | 2.688 |
| SIGNATURE_SPA | 1.732 |
| DOM_RICH_PROBE_POOR | 1.389 |
| SIGNATURE_SPARSE | 1.175 |

**SPA 서명이 특별히 오래 걸린 것도 아니다.** 시간이 원인이었다면 SPA 서명에서 경과가 길어야 하는데
오히려 `BOTH_RICH` 가 가장 길다. 타이밍 가설의 또 다른 반증이다.

## F4 (OBSERVATION) — SPA 서명 자체가 드물다

전체 56 target 중 `SIGNATURE_SPA` 는 **4건**뿐이다
(SPARSE 22 · BOTH_RICH 23 · DOM_RICH_PROBE_POOR 5 · NO_PROBE 2).
RQ-D10 이 확인한 slot 시점 불일치 6/58 과 같은 규모다 — **실재하지만 소수 현상**이다.

---

## 가설 판정

| 가설 | 판정 | 근거 |
|---|---|---|
| **H1_SPA_TIMING** | **REFUTED** | 구조빈약 15건 중 SPA 서명 2건(13.3%), 퇴화 4건 중 0건, 경과시간도 역방향 |
| **H2_DISTINCT** | **SUPPORTED** | 구조빈약은 SPARSE 지배(73.3%), slot_mismatch 만 SPA 서명을 일부 가짐 |
| H3_MIXED | 부분 | `slot_mismatch` 6건은 SPA 2 / SPARSE 3 / BOTH_RICH 1 로 섞여 있다 |

## 이 결과가 바꾸는 것

RQ-D12 의 **production implication P3** — "구조빈약·slot 불일치·퇴화 세 신호는 하나의 원인(SPA 렌더 시점)일
가능성이 있다. RQ-D10 의 slot 지표와 함께 다루면 중복 노력을 줄일 수 있다" — 는 **철회한다.**
셋을 하나로 묶어 처리하면 진짜 빈약한 페이지 11건을 SPA 문제로 오진한다.

RQ-D12 의 다른 결론(집중 없음, 부호 반대 신호 혼재)은 이 결과에 영향받지 않는다.

## 반례 / 대안설명

- *"중앙값 절단이 결과를 만들었다"* → 가능하다. 다만 SPARSE 11 vs SPA 2 는 절단점을 웬만큼 움직여도
  뒤집히기 어려운 격차다. 민감도 분석은 하지 않았다 — **이것이 이 RQ 의 주된 한계다.**
- *"probe 도 cap 에 걸려 풍부도가 과소평가됐다"* → `n_primary_action_candidates` 는 200 cap 이 있다.
  cap 에 걸린 target 은 '풍부' 쪽이므로 SPA 서명을 **과대**계상하는 방향이고, 그래도 2건뿐이다.
- *"DOM 빈약의 원인이 SPA 가 아니라면 무엇인가"* → 이 RQ 는 답하지 않는다. RQ-D14 는 이 중 일부가
  기업/앱설치 랜딩이라고 보고했다(CORPORATE 3, UNDETERMINED 26). 교차 확인은 후속 과제다.

## Limitations

1. **절단점 민감도 분석을 하지 않았다.** 중앙값 하나만 썼다.
2. `dom_interactive_n` 과 `n_primary_action_candidates` 는 서로 다른 슬롯의 서로 다른 셀렉터 집합이라
   직접 비교가 아니다. '풍부/빈약' 의 상대 순위만 쓴다.
3. n=56, flag 별 4~15건. 서명 분포의 비율은 넓은 CI 를 갖는다 (CI 를 계산하지 않았다).
4. `NO_PROBE` 2건은 판별 자체가 불가능하다.

## Production implication (제안일 뿐)

- **P2**: RQ-D12 P3 제안 철회. 세 신호를 하나로 묶어 처리하지 말 것.
- **P3**: `slot_mismatch` 만 SPA 성격을 일부 가진다. RQ-D10 의 지표는 그 6건에 국한해 쓸 것.

## 후속 연구질문

- **RQ-D12a-1**: 절단점 민감도 — 사분위·삼분위·연속형으로 바꿔도 SPARSE 지배가 유지되는가
- **RQ-D12a-2**: `SIGNATURE_SPARSE` 11건이 RQ-D14 의 `CORPORATE_OR_APP`/`UNDETERMINED` 와 겹치는가
