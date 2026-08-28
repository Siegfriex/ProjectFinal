# 보고서 수치 자체검증

**대상** `data/CANONICAL_MART_50.csv` sha256 `5290e0c306ff7a11…` · 50행
**방법** 보고서 본문의 모든 수치를 mart에서 직접 재계산해 대조
**결과** **18항 전부 일치 · 불일치 0건**

| 주장 | 실측 |
|---|---|
| attempted 50 | 50 |
| ENDPOINT_REACHED 6 | 6 |
| AUTH_GATE 2 | 2 |
| USABLE PATH EVIDENCE 8 | 8 |
| NO_SAFE_ROUTE_SITE 16 | 16 |
| COLLECTOR_ZERO_CANDIDATE 21 | 21 |
| TIMEOUT 2 | 2 |
| UNVERIFIED_CANDIDATE_COUNT 2 | 2 |
| FORBIDDEN_ACTION_BOUNDARY 1 | 1 |
| MEASUREMENT 집단 26 | 26 |
| label_relation MATCH 0 | 0 |
| AX_NOT_INDEPENDENTLY_OBSERVED 28 | 28 |
| auth_gate_stage UNDETERMINED 42 | 42 |
| auth_gate_stage AT_ENDPOINT 2 | 2 |
| k=8 entry_zone 5종 | 5종 (TOP_LEFT 1 · TOP_CENTER 2 · TOP_RIGHT 1 · MID 2 · BOTTOM 2) |
| k=8 control type 2종 | 2종 (TEXT_LINK 6 · ICON_TEXT 2) |
| k=8 activation_depth 단일 | `1` ×8 |
| k=8 menu_dependency 단일 | `False` ×8 |

`collection_run` 실측: R1 **15** · R2 **22** · R2B **13** (R3는 선택 풀 제외)

---

## 이 검증이 잡지 못하는 것

**수치의 일치는 해석의 정당성이 아니다.** 이 표는 보고서의 숫자가 mart와 같다는 것만 말한다.

- mart 자체가 **outcome-conditioned rescue mart**라는 사실은 이 검증으로 바뀌지 않는다
- `AX_NOT_INDEPENDENTLY_OBSERVED 28`이 **일치**하지만, 그 28은 관측이 아니다 — **값이 맞게 계산됐다는 것과 그 값이 사이트에 대해 말한다는 것은 다르다**
- 이 검증은 **A가 자기 산출을 자기가 확인한 것**이다. 독립 검산은 `assurance/` 세 파일이고, 그쪽이 상위 근거다

## 왜 이걸 마지막에 했는가

직전에 measurement boundary funnel의 `paired label cases`를 **3**으로 적었다가 mart에서 직접 세어 **0**임을 발견했다(D-DEF-41). 폐기된 판본의 값을 확인 없이 옮긴 것이었다. **같은 형태가 다른 자리에 더 있는지 세어봐야 했다.** 결과는 없었다.
