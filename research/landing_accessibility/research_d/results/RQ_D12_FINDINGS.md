# RQ-D12 — D 의 측정곤란 신호들은 **같은 target 에 몰려 있지 않다**

**verdict**: `REFUTED` (H1 단일 잠재요인) · `H2_INDEPENDENT` 지지 · `H3_CLUSTERED_PAIRS` 부분 성립
**재현**: `.venv/bin/python research_d/tools/rq_d12_difficulty_concentration.py`
**산출**: `results/RQ_D12_difficulty_concentration.json`
**입력**: D 자신의 선행 RQ 산출 6종 + `D_OBSERVATION_TABLE_v2.csv` (전부 재계산 없이 flag 로 환산)

---

## RQ

D 는 서로 다른 RQ 에서 각기 다른 '측정 곤란' 신호를 찾았다. 이 신호들이 **같은 소수 target 에
집중**되는가, 아니면 서로 다른 target 을 가리키는가?

## 왜 중요한가

- **H1(단일 잠재요인)이 참이면**: 소수 target 을 제외하는 것으로 측정 품질이 크게 오르고,
  missingness 를 하나의 요인으로 모델링할 수 있다.
- **H2(독립)가 참이면**: 각 문제를 따로 고쳐야 하고 **어떤 제외도 나머지를 낫게 하지 않는다.**

## 곤란 신호 7종 (정의 전문)

| flag | 정의 | prevalence (n=56) |
|---|---|---|
| `cap_truncated` | probe 배열이 하드 cap 도달 (`cap_any==1`) — RQ-D8 | 14 |
| `low_structural_richness` | `dom_interactive_n` 이 하위 25%(≤ q25) — RQ-D9 권고 proxy | 15 |
| `slot_mismatch` | RQ-D10 `slot_disagreement_score >= 1` | 6 |
| `degenerate_or_dup` | RQ-D13 퇴화 캡처 또는 동일 URL 중복 쌍 | 4 |
| `overlay_construct_mismatch` | RQ-D13a 최대 overlay 요소가 모달 아님(`H2_GENERIC*`) | 47 |
| `frame_not_functional` | RQ-D14 `identity_class != FUNCTIONAL_LANDING` | 29 |
| `rule_abstain` | RF001-A rule DT 가 유일 leaf 실패(`AMBIGUOUS_*`/`UNDETERMINED_*`) | 45 |

---

## F1 (ANALYSIS) — 집중은 우연 수준이다

**flag 개수 분산의 permutation 검정** (각 flag 개수를 유지한 채 target 에 무작위 배정, B=5000):

| 분석 | 관측 분산 | p |
|---|---|---|
| 전체 7 flag | 1.265 | **0.2012** |
| **제한 5 flag** (prevalence < 60%) | 0.847 | **0.3834** |

두 경우 모두 **우연 배치와 구분되지 않는다.** `flag >= 3` 인 target 수도 39/56, p=0.065 로 유의하지 않다.

**제한 분석을 판정 기준으로 삼은 이유**: `overlay_construct_mismatch`(47/56)와 `rule_abstain`(45/56)은
거의 모든 target 에 붙는다. 고빈도 flag 는 모두의 개수를 함께 올려 **집중처럼 보이는 착시**를 만든다.
prevalence 60% 미만 5개로 제한하면 `clean` target 이 1 → **11/56** 로 늘고 분산 p 는 0.20 → 0.38 이 된다.

## F2 (ANALYSIS) — 두 쌍만 실제로 묶인다 (H3 부분 성립)

| 쌍 | phi | Jaccard | both |
|---|---|---|---|
| `low_structural_richness` ↔ `degenerate_or_dup` | **+0.459** | 0.267 | 4 |
| `low_structural_richness` ↔ `slot_mismatch` | **+0.442** | 0.312 | 5 |
| `slot_mismatch` ↔ `degenerate_or_dup` | +0.352 | 0.250 | 2 |

셋은 같은 이야기를 한다 — **구조가 빈약한 페이지에서 slot 시점 불일치와 퇴화 캡처가 함께 온다.**
이것은 RQ-D10 이 이미 지목한 SPA shell 문제와 일치한다(dom 은 렌더 전, probe 는 렌더 후).
다만 both 가 2~5건이라 **n 이 매우 작다** — phi 값을 세게 읽으면 안 된다.

## F3 (ANALYSIS · 가장 중요) — 신호들이 **서로 반대 방향**을 가리킨다

| 쌍 | phi | 해석 |
|---|---|---|
| `cap_truncated` ↔ `rule_abstain` | **−0.441** | cap 에 걸린 target 은 **덜** abstain 된다 |
| `cap_truncated` ↔ `frame_not_functional` | **−0.351** | cap 에 걸린 target 이 오히려 기능 랜딩 쪽이다 |
| `cap_truncated` ↔ `low_structural_richness` | −0.256 | 정의상 당연하나 방향 확인 |

**`cap_truncated` 는 '어려움' 이 아니라 '신호 풍부' 를 표시한다.** RQ-D9 가 이미 관측한
"capped(14/54) 의 `dom_interactive_n` 중앙값 395 vs uncapped 59.5, A12=0.917" 와 같은 방향이다.

따라서 7개 flag 를 하나의 '측정 곤란도' 로 합산하는 것은 **부호가 반대인 것들을 더하는 셈**이다.
`cap_truncated` 는 오히려 signal-rich marker 로 별도 취급해야 한다.

## F4 (OBSERVATION) — 완전히 깨끗한 target 은 거의 없다

전체 7 flag 기준 flag 0 인 target 은 **1/56**. 제한 5 flag 기준으로도 **11/56** 뿐이다.
즉 "문제 있는 소수를 빼면 된다" 는 전략은 성립하지 않는다 — 뺄 게 소수가 아니다.

---

## 가설 판정

| 가설 | 판정 | 근거 |
|---|---|---|
| **H1_SINGLE_LATENT** | **REFUTED** | 제한분석 분산 p=0.3834, 전체 p=0.2012 |
| **H2_INDEPENDENT** | **SUPPORTED** | 대부분 쌍의 \|phi\| < 0.36, 집중 없음 |
| **H3_CLUSTERED_PAIRS** | **PARTIALLY_SUPPORTED** | 구조빈약·slot·퇴화 3개만 묶임(phi 0.35~0.46, both 2~5건) |

## 반례 / 대안설명

- *"flag 정의가 자의적이라 독립처럼 보인다"* → 각 flag 는 **선행 RQ 가 독립적으로 도출한 판정**을
  그대로 이진화한 것이고 이 RQ 에서 새로 만들지 않았다. 다만 `low_structural_richness` 의
  q25 절단점은 이 RQ 에서 정했다 — 임의성이 남는다.
- *"n=56 에서 permutation 검정력이 낮아 집중을 놓쳤을 수 있다"* → 그렇다. p=0.38 은
  "집중이 없다" 가 아니라 **"이 표본에서는 집중을 검출하지 못했다"** 다. 이 구분을 지킨다.
- *"고빈도 flag 를 뺀 것이 결론을 만들었다"* → 두 분석 모두 p>0.05 다. 제한분석은 결론을
  바꾸지 않고 **강화**했다.

## Limitations

1. **검정력**. n=56, flag 별 개수 4~47. 중간 크기의 집중은 검출 못 한다.
2. `low_structural_richness` 의 q25 절단점은 이 RQ 에서 정한 것이라 임의성이 있다.
3. flag 들이 **같은 raw 소스**를 일부 공유한다(모두 같은 60 관측에서 나왔다). 완전 독립 측정이 아니다.
4. phi 는 이진 상관이라 both 가 2~5건인 쌍에서 매우 불안정하다.
5. RF-002 child A~E 결과가 아직 안 나왔다. 그 결과가 나오면 flag 목록이 늘어날 수 있고 결론이 바뀔 수 있다.

## Production implication (제안일 뿐. A ADOPT 전에는 implementation candidate 도 아니다)

- **P2**: '측정 곤란' 을 단일 스칼라로 합산하지 말 것. `cap_truncated` 는 부호가 반대다.
- **P2**: "문제 target 을 제외한다" 전략은 이 데이터에서 근거가 없다 — 깨끗한 target 이 11/56 뿐이다.
- **P3**: 구조빈약·slot 불일치·퇴화 세 신호는 하나의 원인(SPA 렌더 시점)일 가능성이 있다.
  RQ-D10 의 slot 지표와 함께 다루면 중복 노력을 줄일 수 있다.

## 후속 연구질문

- **RQ-D12a**: 구조빈약·slot·퇴화 3개 묶음이 정말 SPA 렌더 시점 하나로 설명되는가
- **RQ-D12b**: RF-002 child A~E 결과를 flag 로 추가했을 때 집중도 결론이 바뀌는가
