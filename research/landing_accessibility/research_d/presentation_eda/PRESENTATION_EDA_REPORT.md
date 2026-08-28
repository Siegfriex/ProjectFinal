# MAIN50 Presentation Measurement EDA — D

> **READ-ONLY.** 새 연구질문·canonical claim 변경 없음. 새 REAL 접속·수집·model fit 없음.

- authority head `574e32880c2cd81c6b2e85c31306f768a55e274c` · D head `f265df478c409d043dfcaf0ca91497c0dec07295`
- canonical mart `5290e0c306ff7a11375f8da1ee0439e4a424559f18e7a6a662588e46be8f5caf` — **선언값과 일치: True**
- 입력 접근: D 워크트리에 번들이 없어 authority 커밋에서 `git show` 로 읽었다. **읽기이며 수정하지 않았다**

---

## 1. 최종 수치 재현 (TASK A) — `ASSURED_RECALCULATED`

| group | n/50 | % of 50 | 구성 |
|---|---|---|---|
| USABLE_PATH_EVIDENCE | **8/50** | 16.0 | ENDPOINT_REACHED 6 · AUTH_GATE 2 |
| SITE_SIDE_ROUTE_NOT_OBSERVED | **16/50** | 32.0 | NO_SAFE_ROUTE_SITE 16 |
| MEASUREMENT_COLLECTOR_LIMITED | **26/50** | 52.0 | COLLECTOR_ZERO 21 · TIMEOUT 2 · UNVERIFIED 2 · FORBIDDEN 1 |

합 50/50 · unmapped 0 · 전수 시도 50/50.

**percentage 는 frozen frame 50 에 대한 기술값이다.** population estimate 가 아니고
accessibility success rate 가 아니다.

---

## 2. 관측가능성 감사 (TASK B) — `DESCRIPTIVE_VERIFIED`

| 변수 | 관측(direct+supp) | 사후파생 | 모호 | 방법실패 | 미관측 | class |
|---|---|---|---|---|---|---|
| `task_path_evidence` | **50/50** | 0 | 0 | 0 | 0 | DESCRIPTIVE_VERIFIED |
| `entry_x_norm` | **8/50** | 0 | 0 | 0 | 42 | DESCRIPTIVE_VERIFIED |
| `entry_y_norm` | **8/50** | 0 | 0 | 0 | 42 | DESCRIPTIVE_VERIFIED |
| `entry_zone` | **8/50** | 0 | 0 | 0 | 42 | DESCRIPTIVE_VERIFIED |
| `entry_control_type` | **0/50** | 27 | 9 | 4 | 10 | DESCRIPTIVE_VERIFIED |
| `task_flow_sequence` | **28/50** | 0 | 0 | 0 | 22 | DESCRIPTIVE_VERIFIED |
| `activation_depth` | **28/50** | 0 | 0 | 0 | 22 | DESCRIPTIVE_VERIFIED |
| `menu_dependency` | **28/50** | 0 | 0 | 0 | 22 | DESCRIPTIVE_VERIFIED |
| `nav_container_type` | **0/50** | 26 | 10 | 4 | 10 | DESCRIPTIVE_VERIFIED |
| `visible_label_text` | **0/50** | 29 | 7 | 4 | 10 | DESCRIPTIVE_VERIFIED |
| `accessible_name` | **0/50** | 28 | 0 | 22 | 0 | DESCRIPTIVE_VERIFIED |
| `label_relation` | **0/50** | 50 | 0 | 0 | 0 | DESCRIPTIVE_VERIFIED |
| `auth_gate_stage` | **8/50** | 0 | 0 | 0 | 42 | DESCRIPTIVE_VERIFIED |
| `task_control_occlusion` | **0/50** | 0 | 0 | 0 | 50 | NOT_OBSERVABLE |
| `reveal_direction` | **0/50** | 0 | 0 | 0 | 50 | NOT_OBSERVABLE |

**값이 non-null 이라고 OBSERVED 로 세지 않았다.** 세 자리에서 그 차이가 크다:

1. **`accessible_name` — browser-computed AX 는 0/50.** 채워진 28건은 `label_relation ==
   AX_NOT_INDEPENDENTLY_OBSERVED` 로 **visible text 복사**이고, 나머지 22건은 AX 캡처
   실패(오류 스텁)다. AX 원자료는 존재하지 않으며 재추출도 불가능하다.
2. **`activation_depth` · `menu_dependency` · `task_flow_sequence` — 관측 28/50.**
   `activation_depth == 0` 인 22건은 **전부 시퀀스가 비어 있고**(`[]`) terminal 이 미도달
   계열이다(COLLECTOR_ZERO 17 · TIMEOUT 2 · UNVERIFIED 2 · FORBIDDEN 1). 그 `0` 은
   "깊이가 0 이었다" 가 아니라 **"관측할 시퀀스가 없었다"** 다. C 의 ASSURED 분모 28/28 과 일치한다.
3. **`nav_container_type` — E 직접 관측 0.** 값이 있는 26건은 전부 B 사후 파생이며
   10건은 모호(`AMBIGUOUS_MULTIPLE_CONTAINERS` 포함)다.

`reveal_direction` · `task_control_occlusion` 은 **50/50 전건 미관측 = UNWIRED** →
`NOT_OBSERVABLE`. 그림 FIG5 에서 값 0 이 아니라 미관측으로 표시했다.

---

## 3. 검증된 case series n=8 (TASK C) — `DESCRIPTIVE_VERIFIED`

pre-R3 usable evidence **8/8 존재 확인**(EVIDENCE_MANIFEST 재대조, R3 이외 run 줄).

| 축 | 결과 |
|---|---|
| `entry_zone` | **5/8** — {'TOP_LEFT': 1, 'BOTTOM': 2, 'TOP_CENTER': 2, 'MID': 2, 'TOP_RIGHT': 1} |
| `entry_control_type` | **2/8** — {'TEXT_LINK': 6, 'ICON_TEXT': 2} |
| `experienced_flow_sequence` | 고유 signature **1/8** |
| `activation_depth` | **1/8** — {'1': 8} |
| `menu_dependency` | {'False': 8} |

`nav_container_type` 은 이 표와 panel 에서 **제외**한다 — E 산출 0.

> **selected case series 다. random sample 이 아니다.**

---

## 4. 탐색적 다양성 (TASK D) — `EXPLORATORY` / appendix 전용

- `entry_zone` — Shannon 1.5596 · normalized 0.969 · Simpson 0.7812 (k=5, n=8)
- `entry_control_type` — Shannon 0.5623 · normalized 0.8113 · Simpson 0.375 (k=2, n=8)

공간 pairwise normalized Euclidean (n_pairs 28):
median 0.3857 · IQR [0.3402, 0.5399] ·
min 0.0161 · max 0.6663
→ **`NOT_ASSURED`** — GEOMETRY_SUPPLEMENT 의 evidence_hash 결속이 NOT_ASSURED 다.

p-value 없음 · uniform null 없음 · population inference 없음.

---

## 5. 결측 기전 (TASK F) — `DESCRIPTIVE_VERIFIED`

{"COLLECTOR_LIMITATION": 21, "(not missing)": 8, "SAFETY_BOUNDARY": 1, "SITE_ROUTE_NOT_OBSERVED": 16, "TIMEOUT": 2, "UNKNOWN": 2}
· AX 축 `API_METHOD_FAILURE` 22건
· UNWIRED {"reveal_direction": 50, "task_control_occlusion": 50}

검증 대상 문장 → **SUPPORTED_AS_WEAKER_FORM**

결측이 원인별로 갈리고(COLLECTOR_LIMITATION 21 · SITE_ROUTE_NOT_OBSERVED 16 · TIMEOUT 2 · SAFETY_BOUNDARY 1), AX 축은 전건이 API 실패라 **결측이 무작위로 흩어져 있지 않다**. 다만 MCAR 를 **검정으로 기각한 것이 아니라** 원인 라벨이 구조적으로 갈린다는 기술적 관찰이다 — '근거가 없다' 까지가 이 데이터가 말하는 것이고 'informative 임을 보였다' 로 쓰지 않는다

**imputation 하지 않았다.**

---

## 6. 기존 figure 재검토

fig1 acquisition · fig2 spatial · fig3 flow · fig4 measurement boundary —
**수정 불필요.** 제목·수치·주석이 A SEALED claim 과 일치한다(3집단 8/16/26,
n=8 개별점, 단일흐름 표기, k=8 CONFIRMED + independently observed label pairs 0/채워진 28).

새 그림 2장만 추가했다: `FIG5_OBSERVABILITY.png` · `FIG6_VARIATION_VS_CONVERGENCE.png`.

---

## 7. A claim 과의 충돌

**충돌 없음.** 재계산 수치가 SEALED claim 과 전건 일치한다.
다만 **발표에서 쓰면 안 되는 자리 하나**를 새로 특정했다 — `activation_depth` 를 50 분모로
평균 내면 0 22건이 섞여 값이 절반이 된다. 이 축의 분모는 **28** 이다. 이것은 claim 수정
사안이 아니라 **발표 문안 주의사항**이라 RECONCILIATION_REQUIRED 로 올리지 않는다.
