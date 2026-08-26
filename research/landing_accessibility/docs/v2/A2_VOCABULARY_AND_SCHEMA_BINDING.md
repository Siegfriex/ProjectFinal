# A2 — 어휘·스키마 바인딩 보충명세 v2.0

| 항목 | 값 |
|---|---|
| 문서 id | `A2_VOCABULARY_AND_SCHEMA_BINDING` |
| 지위 | `EXECUTION_AUTHORITY.md` 권위서열 **9위**. `00`~`05` · `PHASE_GATES.md`(7위) · `A1`(8위) **아래**의 보충명세 |
| 성격 | **보충명세**. 새 연구기준을 만들지 않는다. 이미 정의된 개념에 **허용값·산식·귀속 컬럼**만 부여한다 |
| 대상 결함 | `V2-C001` ssot F6 · F7 · F12 (P2 blocking 3건) |
| 어휘 관할 | `A1`이 도입한 신규 필드·표의 **허용값 도메인은 이 문서가 확정한다** (`A1` §0.2 — 두 문서가 어긋나면 A2의 어휘 정의가 우선) |
| 작성 단계 | P0 `V2_REFREEZE` 시정 → P-A 이행 |
| 실측 기준선 | `state/*.parquet` @ `agent/landing-v2-exec` 워크트리, 2026-08-26 실측 |

---

## 0. SSOT 우선 조항

이 문서는 `docs/v2/00_SSOT_v2.0.md`를 최상위 권위로 하는 종속 문서다.

1. 이 문서와 `00_SSOT_v2.0.md`가 충돌하면 **`00`이 우선한다.**
2. 이 문서와 `01_DATA_SPEC_v2.0.md` / `02_COLLECTION_MEASUREMENT_SPEC_v2.0.md`가 충돌하면
   **원본(`01`/`02`)이 우선한다.** 이 문서는 원본이 이름만 두고 값을 열거하지 않은 자리를 채울 뿐이며,
   원본의 값·정의·범위를 **바꾸거나 넓히지 않는다.**
3. `EXECUTION_AUTHORITY.md` §2의 개정된 권위 서열을 그대로 상속한다.

   | 순위 | 문서 | 이 문서와의 관계 |
   |---|---|---|
   | 1~6 | `docs/v2/00`~`05` | 이 문서가 구체화하는 원본. **충돌 시 원본 우선** |
   | 7 | `docs/v2/PHASE_GATES.md` | Gate 이름·통과조건의 정본. §6의 산출 Phase 귀속은 이 문서를 따른다 |
   | 8 | `docs/v2/A1_MEASUREMENT_OPERATIONALIZATION.md` | 측정 조작화 보충명세. **A1이 도입한 신규 필드·표의 값 도메인은 A2가 확정한다**(`A1` §0.2) |
   | **9** | **`docs/v2/A2_VOCABULARY_AND_SCHEMA_BINDING.md` (이 문서)** | 상태값 어휘·논리↔물리 스키마 대응 |
   | 10 | `docs/07_EVIDENCE_MANIFEST_CONTRACT.md` | evidence identity / manifest 계약. **v1 산물이나 현행 유효**. §4.1 evidence completeness의 근거 |

4. **A1과의 분업.** `A1`은 "어떻게 재는가"(절차·경계·신호)를, 이 문서는 "무슨 값을 쓰는가"(허용값·산식·귀속)를 맡는다.
   `A1` §1.8 · §2.2 · §3.2~§3.4 · §4.2~§4.4 · §5.1 · §6.1이 도입한 신규 필드·표의 값 도메인은
   이 문서 §1.5 · §1.6 · §1.9 · §1.12 · §1.13에 등재되어야 **최종 확정**된다.
   이 문서가 A1의 표현을 다듬은 지점은 §1.5(하위 세분값 배치) 한 곳이며, A1의 의도는 그대로 보존된다.
5. 이 문서가 새 컬럼을 요구하는 것으로 읽혀서는 안 된다. §6에 열거한 미존재 표·컬럼은
   **이 문서가 신설한 것이 아니라 `01`/`02`/`A1`이 이미 요구했으나 아직 물리적으로 없는 것**이다.
6. 원본 docs pack(`00`~`05`)의 **바이트를 수정하지 않는다.** 명세 공백은 보충명세로만 메운다.

### 이 문서가 닫는 결함과 위치

| finding id | 심각도 | 닫는 절 |
|---|---|---|
| `measurement-status-vocabulary-unreconciled` (F6) | P2 blocking | §1.2 · §1.3 · §1.11 · **§1.14** |
| `undefined-column-vocabularies` (F7) | P2 blocking | §1 전체 · §2 · §3 · §4 |
| (A1 신규 필드·표의 값 도메인 확정) | — | §1.5 · §1.6 · §1.9 · §1.12 · §1.13 |
| `state-table-mapping-declared-without-correspondence` (F12) | P2 blocking | §5 · §6 |

**다른 담당이 닫은 결함** — 이 문서는 그 결과를 **참조**할 뿐 재정의하지 않는다.

| finding id | 담당 문서 |
|---|---|
| `ned-ied-split-not-operationalized` (F1) · `interrupt-dismiss-fields-have-no-collection-procedure` (F2) · `episode-counters-undefined-and-uncollected` (F3) · `primary-action-identity-not-stored` (F4) · `l0-evidence-artifacts-without-storage-slot` (F5) · `l1-scout-has-no-step-budget` (adversarial) | `A1_MEASUREMENT_OPERATIONALIZATION.md` |
| `phase-gate-names-only-in-nonauthoritative-bootstrap` (F8) | `PHASE_GATES.md` |
| F9 · F10 · F11 · F13 및 adversarial P1 3건 | `EXECUTION_AUTHORITY.md` · `CLAUDE.md` · `INSTALL_MANIFEST.json` · `verify_v2_docs.py` |

### 실측 표기 규약

이 문서에서 **`[실측]`** 이 붙은 수치는 작성 시점에 `state/*.parquet`을 직접 읽어 확인한 값이다.
`[미측정]`은 아직 데이터가 없어 확인할 수 없는 값이다. 둘을 섞어 쓰지 않는다.

---

## 1. 상태값 어휘 사전 (열거형 정본)

> 구체화 대상: 01_DATA_SPEC §2 / §3 / §4 / §5 / §6 / §7 / §9 / §11 · 02_COLLECTION §5 / §7 / §8 / §13 · 00_SSOT §4 / §8 / §9
> 값 도메인 등재 대상: A1 §1.8 / §2.2 / §3.2~§3.4 / §4.2~§4.4 / §5.1 / §6.1

### 1.0 상태값의 수준 분리

가장 흔한 오류는 **서로 다른 수준의 상태값을 한 어휘로 섞는 것**이다.
`V2-C001` F6이 지적한 `app-only` 문제가 정확히 이 오류다.

| 수준 | 무엇에 대한 상태인가 | 컬럼 | 절 |
|---|---|---|---|
| Frame | 관측 **이전**의 적격성·검토 상태 | `review_status` · `web_eligibility_status` · `web_target_status` · `mapping_status` · `region_signal_type` | §1.1 §1.3 §1.4 §1.9 |
| Observation | 관측 **시도의 결과** | `measurement_status` | §1.2 |
| Task | L1 경로 **탐색의 종료 상태** | `endpoint_status` · `endpoint_status_detail` · `area_signal_status` · `depth_segment` | §1.5 |
| Interrupt | 방해요소 **분류·닫기의 상태** | `classification_status` · `final_label` · `dismiss_method` · `dismiss_failure_mode` | §1.6 |
| Criterion | KWCAG **판정의 상태** | `verdict_state` · `final_status` · `automation_grade` | §1.7 · §3 |
| Adjudication | AI 검토 **처리의 상태** | `fact_ai_adjudication.final_status` · `human_required` · `ai_review_status` | §1.8 §1.10 |
| Episode | 비-activation 조작 구간의 상태 | `episode_kind` · `ended_by` · `input_mode` | §1.12 |
| Candidate | 대표기능 후보 선정의 상태 | `selection_basis` · `selection_status` | §1.13 |

**규칙 S-1.** 한 사실은 정확히 한 수준의 한 컬럼에만 기록한다. 두 컬럼이 같은 사실을 주장하면 결함이다.
**규칙 S-2.** 상위 수준의 상태는 하위 수준의 값을 만들어내지 않는다. 전파는 §1.11의 표로만 한다.
**규칙 S-3.** 모든 열거형은 **닫힌 집합**이다. 표에 없는 값이 나오면 파이프라인이 실패해야 하며,
`UNKNOWN`으로 조용히 흡수하지 않는다.

---

### 1.1 `review_status` — `dim_measurement_entity`

> 구체화 대상: 01_DATA_SPEC §2

| 값 | 뜻 | 실측 |
|---|---|---|
| `NOT_IN_REVIEW_QUEUE` | 동일성 검토 대기열에 오르지 않았다. 원문 표기가 1종이고 병합/분리 판단이 필요 없었다 | **74** `[실측]` |
| `KEEP_SEPARATE` | 검토 결과 별개 measurement entity로 유지 | **6** `[실측]` |
| `MERGE` | 검토 결과 다른 표기를 별칭으로 흡수 | **1** `[실측]` |
| `PENDING_HUMAN_REVIEW` | 검토가 필요하나 아직 판정되지 않았다 | **0** `[실측]` |

**상호배타.** 4값은 상호배타이며 합집합이 전체다 (74 + 6 + 1 + 0 = **81** `[실측]`).

**산출.** 물리 표에 `review_status` 컬럼은 없다. 다음 결정적 식으로 유도한다.

```
review_status = review_decision                       if review_decision is not null
              = 'PENDING_HUMAN_REVIEW'                if needs_human_review is True
              = 'NOT_IN_REVIEW_QUEUE'                 otherwise
```

`NOT_IN_REVIEW_QUEUE`는 이 문서가 만든 토큰이 아니다.
`web_target_group.member_review_decisions`에 **이미 리터럴로 존재**한다 (**64행** `[실측]`).

---

### 1.2 `measurement_status` — `fact_landing_observation`

> 구체화 대상: 01_DATA_SPEC §4 / §11 · 02_COLLECTION §11 / §13

`01 §11`은 `수집 실패 = MEASUREMENT_FAILED` 하나만, `02 §13`은 다섯 조건만 말한다.
둘의 관계를 다음과 같이 확정한다.

**`MEASUREMENT_FAILED`는 저장값이 아니라 계열(family) 이름이다.** 저장되는 것은 leaf 토큰이며,
`MEASUREMENT_FAILED`는 `measurement_status LIKE 'FAILED_%'` 로 유도되는 술어다.
이렇게 해야 `02 §13`의 다섯 조건이 서로 구별되면서 `01 §11`의 단일 개념도 보존된다.

| 값 | 계열 | 뜻 | 근거 |
|---|---|---|---|
| `MEASURED` | 성공 | 페이지가 로드됐고 `02 §11`이 요구하는 evidence 5종(DOM / AX / screenshot / probe / manifest)이 모두 산출됐다 | 02 §11 |
| `FAILED_ACCESS_BLOCKED` | 실패 | 서버·WAF·봇차단·지역차단으로 콘텐츠에 도달하지 못했다 (HTTP 401/403/429, 차단 인터스티셜 포함) | 02 §13 `ACCESS_BLOCKED` |
| `FAILED_ROBOTS_OR_TRANSPORT` | 실패 | `robots.txt` 배제로 수집하지 않았거나 DNS·TLS·네트워크 오류로 전송이 성립하지 않았다 | 02 §13 `ROBOTS/transport issue` |
| `FAILED_BROWSER_CRASH` | 실패 | 브라우저 컨텍스트·렌더러가 비정상 종료했다 | 02 §13 `browser crash` |
| `FAILED_PAGE_TIMEOUT` | 실패 | `02 §3`의 고정 안정화 대기 규칙 안에서 페이지가 안정 상태에 도달하지 못했다 | 02 §13 `page timeout` |
| `FAILED_EVIDENCE_INCOMPLETE` | 실패 | 페이지는 로드됐으나 evidence 5종 중 일부가 없거나 `07_EVIDENCE_MANIFEST_CONTRACT` 검증을 통과하지 못했다 | 02 §11 · 07 §4 |

**상호배타.** 6값은 상호배타다. 한 관측 회차는 정확히 한 값을 가진다.
두 실패가 동시에 성립하면 **먼저 발생한 것**을 기록하고 나머지는 `probe_path`의 진단 로그에 남긴다.

**`app-only`는 이 어휘에 속하지 않는다.**
`02 §13`이 `app-only`를 `별도 measurement status로 기록`이라 적은 것은 `V2-C001` F6이 지적한 상충이다.
앱 전용이라 모바일웹이 없다는 사실은 **관측 시도의 결과가 아니라 관측 이전의 적격성**이며,
`01 §3 dim_web_target.web_eligibility_status`의 값 `EXCLUDED_APP_ONLY`(§1.3)에 귀속된다.
웹이 없으면 `fact_landing_observation` 행 자체가 생기지 않으므로 `measurement_status`가 존재할 자리가 없다.

**규칙 M-1.** `measurement_status ≠ 'MEASURED'` 인 관측은 `fact_criterion_result` 행을 **생성하지 않는다.**
수집 실패를 `FAIL`로도 `UNDETERMINED`로도 세지 않는다 (`02 §13`).
결측은 **행의 부재**로 표현하고 0이나 대체값으로 채우지 않는다 (`01 §11`).

**규칙 M-2.** 시도하지 않은 관측은 이 어휘로 표현하지 않는다. 행이 없는 것이 정답이다.
"적격인데 관측되지 않음"은 §4의 **분모**에서 잡는다 (§4.1 · §4.2).

---

### 1.3 `web_eligibility_status` — `dim_web_target`

> 구체화 대상: 01_DATA_SPEC §3 · 02_COLLECTION §13 · 00_SSOT §3

| 값 | 뜻 | 실측 |
|---|---|---|
| `NOT_ASSESSED` | 웹 수집 적격 여부를 아직 평가하지 않았다. URL 증거가 없다 | **71** `[실측]` |
| `EXCLUDED_INDUSTRY_AXIS` | 축이 업종 카테고리이며 브랜드가 아니다. 웹 수집 대상이 아니다 | **10** `[실측]` |
| `ELIGIBLE_WEB` | 공식 모바일웹 랜딩 URL이 증거와 함께 확정됐다 | **0** `[미측정]` |
| `EXCLUDED_APP_ONLY` | 앱 전용이며 대응하는 공식 모바일웹 랜딩이 없다 | **0** `[미측정]` |
| `EXCLUDED_NO_PUBLIC_WEB_LANDING` | 웹은 존재하나 로그인 이전 공개 랜딩이 없어 `00 §3` L0 범위에 들어오지 않는다 | **0** `[미측정]` |
| `UNDETERMINED_URL_EVIDENCE` | URL 후보가 상충하거나 증거가 불충분해 적격성을 확정할 수 없다 | **0** `[미측정]` |

**상호배타.** 6값은 상호배타다. 현재 값 분포는 `NOT_ASSESSED` **71** + `EXCLUDED_INDUSTRY_AXIS` **10** = **81** `[실측]`
(`service_master.parquet` 전량). 나머지 4값은 P-B에서 처음 채워진다.

**근거 실측.** `EXCLUDED_INDUSTRY_AXIS` 10건은 전부 `axis_type = INDUSTRY_CATEGORY`이고,
`NOT_ASSESSED` 71건은 전부 `axis_type = SERVICE_BRAND`다 `[실측: 교차표 오프대각 0]`.
즉 현재 적격성 판정은 **축 유형 하나만으로** 내려져 있으며, URL 증거에 기반한 판정은 아직 0건이다.

**`EXCLUDED_APP_ONLY`가 F6을 닫는다.** `02 §13`의 `app-only`는 여기로 귀속된다.
`measurement_status`(§1.2)에는 대응 값을 두지 않는다.

**grain 주의.** `01 §3`은 이 컬럼을 `dim_web_target`(web target 수준)에 두지만
물리적으로는 `service_master.web_eligibility_status`(measurement entity 수준, 81행)에 있다.
현재의 81건 판정은 **entity 수준 판정**이며, web target 수준으로 옮길 때 1:1이 보장되지 않는다 (§5.4).

---

### 1.4 `web_target_status` — `dim_web_target`

> 구체화 대상: 01_DATA_SPEC §3 · 00_SSOT §15 · 03_CRISP_DM P-B

`web_eligibility_status`가 "잴 수 있는가"라면 `web_target_status`는 "이 타겟 행이 지금 어느 단계인가"다.

| 값 | 뜻 |
|---|---|
| `DRAFT` | 후보 행이 생성됐으나 URL 검토 전 |
| `PENDING_URL_REVIEW` | URL 후보가 있으나 증거 검토가 끝나지 않았다 |
| `FROZEN` | `00 §15 final web target frozen` 조건을 충족해 동결됐다. 이후 변경 금지 |
| `EXCLUDED` | 동결 전에 대상에서 제외됐다. 제외 사유는 `web_eligibility_status`에 있다 |
| `SUPERSEDED` | 더 정확한 URL 증거로 대체됐다. 이전 행은 남긴다 (append-only, `02 §12`) |

**상호배타.** 5값은 상호배타이며 `DRAFT → PENDING_URL_REVIEW → {FROZEN, EXCLUDED}` 단방향이다.
`FROZEN`에서 벗어나는 유일한 경로는 `SUPERSEDED`이며, 이는 새 행을 만든다.

**현재 물리 대응.** `web_target_group.grouping_status`는
`SINGLETON_PENDING_URL_REVIEW` **65** / `CANDIDATE_PENDING_URL_REVIEW` **3** = **68** `[실측]`이며,
두 값 모두 `PENDING_URL_REVIEW` 하나에 대응한다. 나머지 4값은 아직 실현되지 않았다.

---

### 1.5 Task 수준 어휘 — `fact_task_entry` · `fact_task_step`

> 구체화 대상: 01_DATA_SPEC §6 · 02_COLLECTION §7 / §8 / §9 · 00_SSOT §3 / §7 · **A1 §1.5 / §1.7 / §1.8 / §2.2**

#### 1.5.1 `endpoint_status` — 동결된 7값

`02 §7`이 즉시종료 상태 7종을 **명시적으로 열거**했다. 이 집합은 **확장하지 않는다.**

| 값 | 뜻 | `endpoint_reached` | NED / IED / MPFED |
|---|---|---|---|
| `FUNCTION_ENDPOINT_REACHED` | `dim_representative_task.endpoint_definition`이 정의한 상태에 도달했다 | 1 | 정수 (`A1` §1.3) |
| `AUTH_GATE_REACHED` | 로그인/인증 gate가 나타나 `00 §3 절대 제외`에 걸렸다 | 0 | `NULL` |
| `PAYMENT_GATE_REACHED` | 결제 단계가 나타났다. 우회하지 않는다 | 0 | `NULL` |
| `PERSONAL_DATA_REQUIRED` | 개인정보 입력이 요구됐다 | 0 | `NULL` |
| `CAPTCHA` | 사람 검증이 요구됐다 | 0 | `NULL` |
| `BLOCKED` | 탐색 도중 접근이 차단됐다 | 0 | `NULL` |
| `UNRESOLVED` | 종료조건 어느 것에도 도달하지 못한 채 탐색이 끝났다 | 0 | `NULL` |

**규칙 E-1 (집합 불확장).** 이 7값 집합에 새 값을 추가하지 않는다.
세분이 필요한 사유는 §1.5.2의 동반 컬럼으로 표현한다 (`A1` §2.2).

**상호배타.** 7값은 상호배타다. `endpoint_reached`는 `endpoint_status = FUNCTION_ENDPOINT_REACHED`의
동치 파생값이며 독립 정보를 담지 않는다.

`FUNCTION_ENDPOINT_REACHED` 인데 `MPFED`가 `NULL`인 경우는 없다. 다만
`area_signal_status = INFERRED_FROM_ENDPOINT` 경로에서는 `NED = m`, `IED = 0` 이다 (§1.5.3 · `A1` §1.4).

#### 1.5.2 `endpoint_status_detail` — 하위 세분값

`02 §7`의 7값만으로는 **왜** `UNRESOLVED`인지 구분되지 않는다.
`A1` §2.2가 `UNRESOLVED_DEPTH_BUDGET_EXCEEDED`를, `02 §8`이 replay 실패 기록을 요구한다.

**이 문서는 두 값을 최상위 열거값이 아니라 동반 컬럼 `endpoint_status_detail`의 하위값으로 배치한다.**
동결된 7값 집합을 확장하지 않으면서(`A1` §2.2) 사유를 잃지 않기 위함이다.

| `endpoint_status_detail` | 상위 `endpoint_status` | 뜻 | 근거 |
|---|---|---|---|
| `UNRESOLVED_DEPTH_BUDGET_EXCEEDED` | `UNRESOLVED` | `A1` §2.1의 activation·state 재방문·wall-clock·무변화 예산 중 하나가 발화했다 | `A1` §2.2 |
| `UNRESOLVED_REPLAY_BROKEN` | `UNRESOLVED` | 동결된 task manifest의 결정적 replay가 깨졌다 | `02 §8` |
| `UNRESOLVED_NO_SIGNAL` | `UNRESOLVED` | 예산 안에서 어떤 종료신호도 발화하지 않았다 | `02 §7` |
| `NULL` | 나머지 6값 | 세분이 필요 없다. 상위 값이 이미 사유다 | — |

**roll-up 규칙.** `endpoint_status_detail`이 non-null이면 반드시 `endpoint_status = 'UNRESOLVED'` 이다.
집계·보고는 기본적으로 상위 7값으로 하고, 세분값은 측정품질 진단에만 쓴다.

**A1 표현의 정합화.** `A1` §2.2는 `endpoint_status`에 `UNRESOLVED_DEPTH_BUDGET_EXCEEDED`를 기록한다고 쓰면서
같은 절에서 `02 §7의 7개 종료값 집합을 확장하지 않는다`고 못박았다. 두 문장은 한 컬럼에서 양립하지 않으므로
`A1` §0.2(`두 문서가 어긋나면 A2의 어휘 정의가 우선`)에 따라 위 2컬럼 구조로 확정한다.
**A1의 의도(집합 불확장 + 사유 보존)는 그대로 보존되며, 값 이름도 바뀌지 않는다.**

**규칙 E-2 (자유탐색 대체 금지).** `UNRESOLVED_REPLAY_BROKEN`은 `02 §8`의
`replay가 깨지면 상태를 기록하고 다시 자유탐색으로 조용히 대체하지 않는다`를 이행하는 값이다.
이 값을 남기지 않고 재탐색한 결과를 기록하는 것은 결함이다.

**규칙 E-3 (접근성 FAIL 아님).** `endpoint_status`와 `endpoint_status_detail`은 **measurement status다.**
`AUTH_GATE_REACHED`도 `UNRESOLVED_DEPTH_BUDGET_EXCEEDED`도 KWCAG 판정으로 전환하지 않으며
`fact_criterion_result`의 어떤 값에도 영향을 주지 않는다 (전파 규칙 T-5 · `A1` §2.3).
`이 서비스는 깊어서 실패했다`는 문장의 근거로 쓸 수 없다.
수집기의 탐색 실패와 서비스의 접근성 결함은 서로 다른 사건이다.

**규칙 E-4 (절단 취급).** 예산에 걸린 관측은 `MPFED = 8`이 **아니라**
`8회 안에서는 관측되지 않았다`이다 (`A1` §2.4).

| 산출물 | 취급 |
|---|---|
| `MPFED` 분포 (`00 §11` median/IQR/mode/ECDF) | 우측절단으로 표기해 **별도 집계**. 상한값을 대입하지 않는다 |
| `ExcessDepth` | 산출하지 않는다 (`MPFED`가 `NULL`이므로) |
| `mart_archetype_summary.endpoint reach` | 분모 포함, 분자 제외. **절단 건수를 별도 컬럼으로 노출** |
| `mart_service_summary` | `endpoint_status` 원값을 그대로 전달 |

#### 1.5.3 `area_signal_status` — `fact_task_entry`

`A1` §1이 정의한 **`FUNCTION_AREA_REACHED`** 신호의 관측 결과를 담는다.
`FUNCTION_AREA_REACHED`는 **저장되는 열거값이 아니라 NED가 멈추는 시점을 정의하는 신호**다.
그 신호가 관측됐는지는 이 컬럼이, 어느 step에서 관측됐는지는 `fact_task_step.area_signal_detected`가 담는다.

| 값 | 뜻 | `NED` | `IED` | `MPFED` |
|---|---|---|---|---|
| `OBSERVED` | 영역 신호가 직접 관측됐다 (`A1` §1.1 — PRESENT ∧ HITTABLE ∧ NO_FURTHER_ACTIVATION) | `k` | `m-k` 또는 `NULL` | `m` 또는 `NULL` |
| `INFERRED_FROM_ENDPOINT` | endpoint가 영역보다 먼저 관측돼(`m < k`) `k := m`으로 소급 확정했다 | `m` | `0` | `m` |
| `NOT_OBSERVED` | 영역 신호가 관측되지 않았다 | `NULL` | `NULL` | `NULL` |

**상호배타.** 3값은 상호배타다.

**`INFERRED_FROM_ENDPOINT`는 추정이 아니라 소급 귀속이다.** endpoint에 도달했다면 영역에는
늦어도 그 시점에 도달한 것이므로 `k ≤ m`이 논리적으로 강제된다. 없는 관측을 지어내는 경로가 아니다.
그럼에도 값 자체에 그 사실을 남겨 하류 분석이 `OBSERVED`와 **구분해 다룰 수 있게** 한다.

**`NOT_OBSERVED` ≠ `NED = 0`.** 영역 신호를 못 본 것과 랜딩에서 이미 영역이었던 것(`k = 0` → `NED = 0`)은
다른 사실이다. 전자는 `NULL`, 후자는 `0`이다 (§1.14).

#### 1.5.4 `depth_segment` · `counts_toward_depth` · `area_signal_detected` — `fact_task_step`

| 컬럼 | 값 | 뜻 |
|---|---|---|
| `depth_segment` | `NED` / `IED` / `UNASSIGNED` | 그 activation이 귀속되는 구간 (`A1` §1.7). `area_signal_status = NOT_OBSERVED` 경로의 전 activation은 `UNASSIGNED` |
| `counts_toward_depth` | `0` / `1` | `02 §9`가 activation으로 인정하는가 |
| `area_signal_detected` | `0` / `1` | 그 step 이후 state에서 `FUNCTION_AREA_REACHED`가 성립했는가. 기존 `endpoint_signal_detected`와 대칭 |

**상호배타.** `depth_segment` 3값은 상호배타다.

**규칙 D-1 (사후 재계산 가능성).** 귀속은 `k`·`m`이 확정된 scout 종료 시점에 일괄 확정하되,
각 step의 원시 신호(`area_signal_detected` · `endpoint_signal_detected`)를 그때그때 저장하므로
`depth_segment`는 **저장 데이터만으로 제3자가 재계산 가능**해야 한다 (`A1` §1.7).

**규칙 D-2.** `02 §9`가 activation에서 제외한 행위(문자 단위 입력·passive loading·redirect·server wait·
scroll·popup dismiss)는 애초에 `fact_task_step` 행을 만들지 않는다 (`A1` §1.7).
이들은 §1.12 episode 축과 `forced_dismissal_count`로 간다.
따라서 `counts_toward_depth`는 정상 파이프라인에서 항상 `1`이며, `0`이 나타나면 **결함 탐지 신호**다.

**규칙 D-3 (합성 금지).** `text_input_episode_count` · `scroll_episode_count` · `forced_dismissal_count`를
`NED`/`IED`/`MPFED`에 더해 "총 조작 수" 같은 변수를 만들지 않는다 (`00 §7` · `A1` §4.1).

**규칙 D-4 (해석 금지).** `NED = 0`을 "진입이 쉽다"로 읽어 점수화하지 않는다.
랜딩에 영역진입 control이 있었다는 **관측 사실**일 뿐이다 (`A1` §8).

### 1.6 Interrupt 수준 어휘 — `fact_interrupt_element`

> 구체화 대상: 01_DATA_SPEC §5 · 02_COLLECTION §5 / §10 · 00_SSOT §8 · **A1 §3.2 / §3.3 / §3.4**

#### `classification_status` — 분류가 어느 단계에서 확정됐는가

| 값 | 뜻 |
|---|---|
| `NOT_CLASSIFIED` | `02 §5` 2차 공간검사에서 viewport와 겹치지 않아 의미분류 대상이 아니다 |
| `DETERMINISTIC` | DOM text / accessible name 규칙만으로 확정됐다 (`02 §5` 4차 1순위) |
| `SEMANTIC_MODEL` | text/embedding 분류기로 확정됐다 |
| `VLM_REVIEWED` | screenshot crop + DOM/AX 요약을 VLM에 전달해 확정됐다 |
| `AMBIGUOUS` | cascade가 확정하지 못했다 |

**상호배타.** 5값은 상호배타다.

#### `final_label` — 무엇으로 분류됐는가

`00 §8`이 이미 열거한 10종을 그대로 값 도메인으로 확정한다. 새 라벨을 추가하지 않는다
(`02 §10` `자유로운 새 기준 생성 금지`).

`BLOCKING_MODAL` · `PROMOTION_MODAL` · `COOKIE_CONSENT` · `ADVERTISEMENT` · `APP_INSTALL_PROMPT` ·
`LOGIN_PROMPT` · `CHAT_WIDGET` · `BANNER` · `TOAST` · `UNKNOWN`

**규칙 I-1.** `classification_status ∈ {NOT_CLASSIFIED, AMBIGUOUS}` 이면 `final_label = UNKNOWN`이다.
그 반대도 성립한다 — `final_label = UNKNOWN`인데 `classification_status`가 확정 3값 중 하나이면 결함이다.

**규칙 I-2.** `UNKNOWN`은 집계에서 **다른 라벨로 배분하지 않는다.** `00 §8`의 prevalence 지표는
`UNKNOWN`을 별도 칸으로 보고한다.

#### `dismiss_method` — 어떤 경로로 닫기를 시도했는가

`A1` §3.3이 도입한 컬럼이다. 시행은 한 interrupt당 정확히 1회다.

| 값 | 뜻 |
|---|---|
| `CONTROL_CLICK` | `dismiss_control_visible = 1` 인 닫기 control을 눌렀다 |
| `DIALOG_CLOSE` | `<dialog>`의 close 경로를 썼다 |
| `ESCAPE_KEY` | `Escape` 키를 보냈다 |
| `BACKDROP_CLICK` | backdrop을 눌렀다 |
| `NONE` | 시도 가능한 경로가 없었다 |

**상호배타.** 5값은 상호배타다. `NONE`이면 `dismiss_succeeded = 0`이다.

#### `dismiss_failure_mode` — 왜 닫히지 않았는가

| 값 | 뜻 |
|---|---|
| `NO_CONTROL` | 닫기 control도 대체 경로도 없었다 |
| `NOT_HITTABLE` | control은 있으나 hit-test가 그것을 반환하지 않았다 |
| `NO_STATE_CHANGE` | 조작 후 안정화 대기를 거쳐도 상태가 변하지 않았다 |
| `NEW_INTERRUPT_APPEARED` | 닫히자마자 다른 방해요소가 나타났다 |
| `NAVIGATED_AWAY` | dismissal이 페이지 이동을 유발했다 |
| `NULL` | `dismiss_succeeded = 1` (실패하지 않았다) |

**상호배타.** 5값 + `NULL`은 상호배타다.
`dismiss_succeeded = 1` ↔ `dismiss_failure_mode IS NULL` 은 동치다.

**규칙 I-3 (L0-a 고정).** `NAVIGATED_AWAY`가 발생해도 그 관측의 L0 요약 변수
(`max_overlay_coverage` · `primary_action_visible_initial` 등)는 **L0-a 스냅샷을 유지**하며
이동 후 화면으로 갱신하지 않는다 (`A1` §3.1 · §3.3).

#### `dismiss_persistence_hint` — 0/1

`오늘 하루 보지 않기` 유형처럼 **다음 회차 관측이 달라질 수 있는** 닫기 경로였으면 1.
이 값은 재현성 진단용이며 **판정에 쓰지 않는다** (`A1` §3.2).

#### `dismiss_control_accessible_name` — `NAME_ABSENT` 센티널

`A1` §3.2는 이름이 비어 있을 때 빈 문자열이 아니라 `NAME_ABSENT`를 기록하도록 정했다.
이 문서는 그 센티널의 지위를 다음과 같이 확정한다.

| 저장값 | 뜻 |
|---|---|
| 임의 문자열 | 브라우저 AX tree가 계산한 accessible name **그대로** |
| `NAME_ABSENT` | control은 존재하나 브라우저가 계산한 이름이 **비어 있음** — 관측된 사실 |
| `NULL` | `dismiss_control_exists = 0` — 잴 대상이 없었음 |

**셋을 섞지 않는다.** `NAME_ABSENT`(이름 없음이 관측됨)와 `NULL`(관측 자체가 없음)은 다르다 (§1.14).
VLM이 아이콘을 보고 추정한 이름을 이 필드에 넣지 않는다. 추정은 `fact_ai_adjudication`에 남긴다.

**규칙 I-4 (독립 변수).** `dismiss_succeeded`는 `blocks_primary_action`과 **독립**이다.
또한 L0의 닫기 가능성 측정과 L1의 `forced_dismissal_count`는 별개이며 **합산하지 않는다** (`A1` §3.3).

---

### 1.7 `verdict_state` · `final_status` — `fact_criterion_result`

> 구체화 대상: 01_DATA_SPEC §7 / §11 · 00_SSOT §4 · 02_COLLECTION §4 / §14

두 컬럼은 **같은 값 도메인**을 쓰되 **다른 시점**을 가리킨다. 이 구분이 `V2-C001` F7의 핵심이다.

| 컬럼 | 시점 | 누가 정하는가 | 변경 가능성 |
|---|---|---|---|
| `verdict_state` | AI 검토 **이전** | 결정적 측정 파이프라인 (`02 §4` raw feature → criterion opportunity → verdict) | **불변.** 값을 고치려면 새 evidence run이 필요하다 (`02 §12`) |
| `final_status` | adjudication **이후** | §1.11의 전이 규칙 | judgment version 단위로 append |

값 도메인 (둘 다 동일, `00 §4`):

| 값 | 뜻 |
|---|---|
| `PASS` | 기준 충족이 **확인됐다** |
| `FAIL` | 기준 미충족이 **확인됐다** |
| `UNDETERMINED` | 자료가 부족해 확정할 수 없다 |
| `NA` | 그 관측에 해당 기준을 적용할 대상 자체가 없다 |

**상호배타.** 4값은 상호배타이며 합집합이 전체다.

**카운트 컬럼과의 항등식.** `01 §7`의 4개 카운트는 criterion opportunity 수준의 집계이며
다음 항등식을 **반드시** 만족한다.

```
applicable_count = pass_count + fail_count + undetermined_count
```

`NA`는 `applicable_count`에 들어가지 않는다 — 적용기회가 없다는 뜻이므로 정의상 0이다.
`verdict_state = NA` 인 행은 `applicable_count = 0`이고 나머지 셋도 0이다.
**이 0들은 결측이 아니라 참인 0이다.** 반대로 `measurement_status ≠ MEASURED`로 행이 없는 경우와 혼동하지 않는다 (규칙 M-1).

**`ai_review_required`** — 0/1. `verdict_state = UNDETERMINED` 이거나 결정적 단계가 신뢰구간을 벗어난 경우 1.
`automation_grade ∈ {D_EMBEDDING_TEXT, E_VLM, F_HUMAN_FINAL}` 인 행은 반드시 `ai_review_required = 1`이다 (§3 제약 G-2).

---

### 1.8 `final_status` · `human_required` — `fact_ai_adjudication`

> 구체화 대상: 01_DATA_SPEC §9 · 00_SSOT §9 · 02_COLLECTION §10

이 표의 `final_status`는 `fact_criterion_result.final_status`와 **이름은 같지만 값 도메인이 다르다.**
여기에 `ABSTAIN`이 산다 (§2).

| 값 | 뜻 |
|---|---|
| `RESOLVED` | cascade가 허용 label 중 하나로 확정했다. 확정된 라벨 자체는 `arbiter_label`(또는 합의된 reviewer label)에 있다 |
| `ABSTAIN` | 확신할 수 없어 억지로 분류하지 않았다 (`04` `Abstain`) |
| `ESCALATED_HUMAN_FINAL` | 사람 최종검토 대기열에 올랐다. `human_required = 1` |
| `PENDING` | 검토가 아직 끝나지 않았다 |

**상호배타.** 4값은 상호배타다.

**`human_required`** — 0/1. `final_status = ESCALATED_HUMAN_FINAL` 과 동치다.
전 연구를 통틀어 `human_required = 1` 인 distinct `review_item_id` 수는 **5를 넘을 수 없다**
(`HUMAN_FINAL_REVIEW_MAX = 5`, `00 §9` · `EXECUTION_AUTHORITY §1`).

**`reviewer_agreement`** — 0/1/`NA`. reviewer A·B가 **둘 다 라벨을 냈고 서로 같으면** 1, 다르면 0,
한쪽이라도 `ABSTAIN`이거나 라벨이 없으면 `NA`. `NA`를 0으로 세지 않는다 (§4.4).

**`evidence_gap`** — 0/1. evidence package(`02 §10`) 자체가 판단에 불충분했으면 1.
이 값이 laundering 차단의 열쇠다 (규칙 T-3).

**`impact_level`** — `HIGH` / `MEDIUM` / `LOW`. 해당 판정이 `00 §11` 주요 분석 결론을 바꿀 수 있는 정도.
**`review_priority`** — 정수. 사람 검토 5건 선발의 결정적 순서 (§4.6).

**AI label은 human gold가 아니다.** `arbiter_label`·`reviewer_*_label`은 `04`의 `Gold Label` 정의에 해당하지 않는다.
분석 문장에서 이들을 정답으로 서술하지 않는다 (`00 §9`).

---

### 1.9 `mapping_status` — `dim_representative_task`

> 구체화 대상: 01_DATA_SPEC §3 · 00_SSOT §6 · 03_CRISP_DM M0 / P-A

| 값 | 뜻 |
|---|---|
| `DRAFT` | 후보 매핑이 생성됐다 |
| `CANDIDATE` | 규칙·source context·embedding으로 후보가 좁혀졌으나 확정 전 |
| `FROZEN` | `00 §6` `매핑은 접근성 outcome과 인증 여부를 보기 전에 동결한다`를 이행해 동결됐다 |
| `AMBIGUOUS_UNRESOLVED` | cascade와 사람 검토 예산으로도 확정하지 못했다 |
| `EXCLUDED` | 대표 task를 정의할 수 없어 L1 대상에서 제외했다 |

**상호배타.** 5값은 상호배타이며 `DRAFT → CANDIDATE → {FROZEN, AMBIGUOUS_UNRESOLVED, EXCLUDED}` 단방향이다.

**규칙 P-1 (동결 순서).** `FROZEN` 전이는 KWCAG 결과·`certified_current`를 **읽기 전에** 일어나야 한다.
동결 시각과 접근성 산출물 생성 시각의 순서를 artifact로 남긴다.

**`mapping_basis`** — 어떤 근거로 정했는가. `RULE` / `SOURCE_CONTEXT` / `EMBEDDING` / `AI_REVIEW` / `HUMAN_FINAL`
(`03 M0`의 4요소 + 사람). `mapping_status`와 별개 축이다.

**`human_final_required`** — 0/1. 1이면 `HUMAN_FINAL_REVIEW_MAX = 5` 예산을 소비한다.
`fact_ai_adjudication.human_required` 와 **같은 예산**을 공유한다 (§4.6).

#### `region_definition` · `region_signal_type` — A1 §1.8 신규 필드

`A1`이 `endpoint_definition` / `endpoint_signal_type`과 **대칭**으로 도입한 두 필드다.
NED가 멈추는 `FUNCTION_AREA_REACHED` 신호(§1.5.3)를 task별로 지정한다.

| 컬럼 | 값 | 뜻 |
|---|---|---|
| `region_definition` | 자유 텍스트 | 그 task의 영역진입 control 정의. **서비스별 값은 P-A endpoint codebook과 함께 동결**한다 |
| `region_signal_type` | `DOM_AX_ROLE` / `FORM_STRUCTURE` / `URL_PATTERN` / `MEDIA_STATE` / `GATE_SIGNAL` / `CODEBOOK_PENDING` | 영역 도달 판정의 1차 소스 유형 |

`region_signal_type` 값은 `A1` §1.2 신호표의 `1차 판정 소스` 열을 토큰화한 것이다.
`endpoint_signal_type`도 **같은 열거형을 공유**한다 — 두 신호는 판정 소스 유형이 같은 종류이기 때문이다.

**상호배타.** 6값은 상호배타다.

**규칙 P-2.** `region_signal_type = CODEBOOK_PENDING` 인 task는 `mapping_status = FROZEN`으로
전이할 수 없다. `A1` §1.2가 `UTILITY_ENTRY`에 대해 `00 §3` 대응 행이 없다고 명시했으므로,
해당 archetype의 task는 P-A codebook 동결까지 미동결로 유지한다.

---

### 1.10 `ai_review_status` — 공유 열거형

> 구체화 대상: 01_DATA_SPEC §5 (`fact_interrupt_element.ai_review_status`) / §3 (`dim_representative_task.mapping_ai_review_status`)

두 컬럼은 **같은 열거형**을 쓴다. 별개 어휘를 만들지 않는다.

| 값 | 뜻 |
|---|---|
| `NOT_REQUIRED` | 결정적 단계에서 확정돼 AI 검토가 필요 없었다 |
| `QUEUED` | 검토 대기 중 |
| `COMPLETED_AGREED` | reviewer A·B가 합의해 확정됐다 |
| `COMPLETED_ARBITRATED` | A·B가 갈려 arbiter가 확정했다 |
| `ABSTAINED` | cascade가 `ABSTAIN`으로 종료했다 |
| `ESCALATED_HUMAN_FINAL` | 사람 최종검토로 올라갔다 |
| `ESCALATION_DECLINED_BUDGET` | 사람 검토가 타당했으나 5건 예산이 이미 소진돼 올리지 못했다 |

**상호배타.** 7값은 상호배타다.

**규칙 A-1.** `ESCALATION_DECLINED_BUDGET`은 반드시 `fact_ai_adjudication.final_status = ABSTAIN`과 짝을 이룬다.
예산 부족을 이유로 `RESOLVED`로 내리지 않는다 — 이것이 `00 §9`
`5건을 초과하는 모호한 사례를 억지로 분류하지 않는다`의 기계적 이행이다 (§2).

---

### 1.11 상태값 사이의 관계와 전파

> 구체화 대상: 01_DATA_SPEC §11 · 02_COLLECTION §13 / §14 · 00_SSOT §4 / §9

#### 어느 수준의 값인가 — 한 표로

| 토큰 | 수준 | 컬럼 | criterion 판정인가 |
|---|---|---|---|
| `PASS` / `FAIL` / `UNDETERMINED` / `NA` | Criterion | `verdict_state` · `final_status` | **예** |
| `MEASUREMENT_FAILED` (계열) | Observation | `measurement_status` | 아니다 |
| `AUTH_GATE_REACHED` | Task | `endpoint_status` | 아니다 |
| `ABSTAIN` | Adjudication | `fact_ai_adjudication.final_status` | 아니다 |

`01 §11`이 네 토큰을 한 목록에 나란히 적은 것은 **"결측을 0으로 바꾸지 않는다"는 원칙의 예시 나열**이지
같은 컬럼의 값 목록이 아니다. 이 문서는 그 넷을 서로 다른 컬럼으로 분리해 확정한다.

#### 전파 규칙

| # | 규칙 |
|---|---|
| **T-1** | `measurement_status ≠ MEASURED` → `fact_criterion_result` 행 **생성하지 않음**. `FAIL`·`UNDETERMINED` 어느 쪽으로도 세지 않는다 (`02 §13`) |
| **T-2** | `ai_review_required = 0` → `final_status = verdict_state` (항등 전파) |
| **T-3** | `ai_review_required = 1` → `final_status`는 `fact_ai_adjudication`에서 전파. **단 아래 금지 전이를 지킨다** |
| **T-4** | `fact_ai_adjudication.final_status = ABSTAIN` → `fact_criterion_result.final_status = UNDETERMINED` |
| **T-5** | `endpoint_status` · `endpoint_status_detail` · `area_signal_status`는 `fact_criterion_result`로 전파되지 **않는다**. L1 종료 상태는 Axis B 변수이며 Axis A 판정이 아니다 (`00 §4` · `A1 §2.3`) |
| **T-6** | `verdict_state = NA` → `final_status = NA`. adjudication은 `NA`를 바꾸지 못한다. 적용기회 유무의 재판정은 새 evidence run에서 `verdict_state`를 다시 내는 일이다 |

#### 금지 전이 (laundering 차단)

| # | 금지 |
|---|---|
| **X-1** | `verdict_state = UNDETERMINED` 이고 `evidence_gap = 1` 인 행을 `final_status = PASS`로 전이하는 것. **증거가 없어서 판단 못한 것을 "충족 확인됨"으로 바꾸는 것이 laundering이다** (`02 §14` `UNDETERMINED→PASS 시도`) |
| **X-2** | `final_status = ABSTAIN` (criterion 표에는 이 값이 없다). ABSTAIN은 T-4로만 들어오고 들어오는 순간 `UNDETERMINED`가 된다 |
| **X-3** | `NA`를 `PASS`로 세는 집계. `NA`는 분자에도 분모에도 자동으로 들어가지 않는다 (§4.2) |
| **X-4** | `measurement_status` 실패 계열을 `FAIL`로 세는 집계 |
| **X-5** | `endpoint_reached = 0` 인 행의 `NED`/`IED`/`MPFED`를 `0`이나 예산 상한값(`8`)으로 채우는 것. 정답은 `NULL`이다 (규칙 N-1 · `A1 §1.5` · `A1 §2.4`) |
| **X-7** | `NULL`(미관측)과 `0`(관측된 0)을 같은 칸에 세는 집계 (규칙 N-1 · §1.14) |
| **X-8** | `NAME_ABSENT`(이름 없음이 관측됨)를 `NULL`(잴 대상 없음)과 합치는 집계 (규칙 N-4 · §1.6 · §1.14) |
| **X-6** | 사람 검토 예산 소진을 이유로 `ABSTAIN` 대신 `RESOLVED`를 기록하는 것 (규칙 A-1) |

`02 §14` 실패주입은 X-1을 실제로 차단하는지 확인한다. 나머지 X-2~X-6도 같은 방식으로
E000_V2 smoke에서 차단 여부를 확인한다.

### 1.12 Episode 수준 어휘 — `fact_task_episode`

> 구체화 대상: 01_DATA_SPEC §6 · 00_SSOT §7 · 02_COLLECTION §9 · **A1 §4.1~§4.4**

`A1` §4.4가 제안한 신규 표 `fact_task_episode`의 값 도메인을 확정한다.
episode는 activation과 **별개 축**이며 Depth에 가산되지 않는다 (`00 §7` · 규칙 D-3).

#### `episode_kind`

| 값 | 뜻 |
|---|---|
| `TEXT_INPUT` | 하나의 입력 control에 대한 focus 획득~종료 사이의 연속 입력 구간 1개 (`A1` §4.2) |
| `SCROLL` | 하나의 scroll container에 대한 연속 scroll 입력 구간 1개 (`A1` §4.3) |

**상호배타.** 2값은 상호배타다.

#### `ended_by` — episode를 끝낸 사건

| 값 | 적용 `episode_kind` | 뜻 |
|---|---|---|
| `BLUR` | `TEXT_INPUT` | 대상 control이 focus를 잃었다 |
| `SUBMIT` | `TEXT_INPUT` | 폼이 제출됐다 |
| `FOCUS_MOVED` | `TEXT_INPUT` | 다른 control로 focus가 옮겨갔다 |
| `IDLE` | `SCROLL` | scroll idle이 `SCROLL_IDLE_MS` 이상 지속됐다 |
| `DIRECTION_REVERSAL` | `SCROLL` | scroll 방향이 반전됐다 |
| `CONTAINER_CHANGE` | `SCROLL` | scroll container가 바뀌었다 |
| `ACTIVATION` | 둘 다 | activation이 발생했다 |
| `STATE_CHANGE` | 둘 다 | state 전이가 일어났다 |
| `SCOUT_END` | 둘 다 | scout이 종료됐다 |

**상호배타.** 9값은 상호배타다. 여러 조건이 동시에 성립하면 **먼저 온 것**을 기록한다 (`A1` §4.2 · §4.3).

#### `input_mode`

| 값 | 뜻 |
|---|---|
| `HUMAN_SIMULATED` | 사람 입력을 모사한 키 입력 |
| `PROGRAMMATIC` | 수집기가 값을 프로그램적으로 주입 |
| `NULL` | `episode_kind = SCROLL` (해당 없음) |

**규칙 EP-1 (카운트 항등식).**

```
fact_task_entry.text_input_episode_count = count(episode_kind = 'TEXT_INPUT')
fact_task_entry.scroll_episode_count     = count(episode_kind = 'SCROLL')
```

두 카운터는 `fact_task_episode`의 **파생값**이며 독립 입력이 아니다.
상류 표가 없으면 두 값은 `NULL`이지 `0`이 아니다 (§1.14).

**규칙 EP-2 (자동 스크롤 제외).** full-page screenshot 캡처를 위한 프로그램적 스크롤은
episode가 **아니다.** 사용자 행동 모사가 아니므로 세지 않는다 (`A1` §4.3).

**규칙 EP-3 (거리·문자수 무관).** 100자를 넣어도 1 episode, 얼마를 스크롤해도 1 episode다.
`scroll_distance_px`는 보조 기록이며 episode 수를 나누는 근거가 아니다.

---

### 1.13 Candidate 수준 어휘 — `fact_primary_action_candidate`

> 구체화 대상: 00_SSOT §8 · 01_DATA_SPEC §4 / §5 · 02_COLLECTION §6 · **A1 §5.1~§5.3**

`A1` §5.1이 제안한 신규 표의 값 도메인을 확정한다.
이 표가 `PrimaryActionOcclusion`의 **분모**(`area_css_px2`)를 저장해 재판정을 가능하게 한다.

#### `selection_basis` — 무엇이 이 후보를 골랐는가

| 값 | 대응 `automation_grade` (§3) |
|---|---|
| `DETERMINISTIC_RULE` | `B_DETERMINISTIC_RULE` 이하 |
| `EMBEDDING_RANK` | `D_EMBEDDING_TEXT` |
| `AI_REVIEW` | `E_VLM` |
| `HUMAN_FINAL` | `F_HUMAN_FINAL` |

**상호배타.** 4값은 상호배타다. 오른쪽 열의 대응은 §3 최소 등급 원칙(G-1)과 정합해야 한다.

#### `selection_status`

| 값 | 뜻 |
|---|---|
| `SELECTED` | 이 관측·task의 대표기능 control로 확정됐다 |
| `RUNNER_UP` | 저장 상한(`TOP_N_CANDIDATES`) 안의 차순위 후보 |
| `REJECTED` | 후보였으나 배제됐다 |

**상호배타.** 3값은 상호배타다.

**규칙 C-1 (SELECTED 유일성).** `SELECTED`는 (관측 × task)당 **최대 1행**이다.
0행이면 `fact_landing_observation.primary_action_visible_initial = NULL` 이며 `0`이 아니다 (`A1` §5.1).

**규칙 C-2 (분모 보존).** `primary_action_occlusion`의 분모는 `SELECTED` 후보의 `area_css_px2`다.
분자·분모가 모두 저장되므로 **제3자 재계산이 가능**해야 한다 (`02 §12` 재판정 전제).

**규칙 C-3 (후보 소실 금지).** `RUNNER_UP`·`REJECTED`를 지우지 않는다.
embedding 랭킹은 오분류 여지가 있으므로(`02 §6` `모호하면 AI review`),
어느 후보가 왜 선택됐는지가 남아야 AI review의 감사 추적이 끊기지 않는다.

---

### 1.14 `NULL` / `UNDETERMINED` / `NA` / `MEASUREMENT_FAILED` — 네 결측의 분리

> 구체화 대상: 01_DATA_SPEC §11 · 02_COLLECTION §13 · **A1 §1.5 / §2.4 / §5.1**

`01 §11`의 `결측을 0으로 바꾸지 않는다`를 구체화한다.
네 개념은 **모두 "값이 없다"로 보이지만 서로 다른 사실**이며, 이 구분이 감사가 지적한
`measurement-status-vocabulary-unreconciled`의 핵심이다.

| | `NULL` | `UNDETERMINED` | `NA` | `MEASUREMENT_FAILED` (계열) |
|---|---|---|---|---|
| **무엇** | 값이 **관측되지 않음** | **판단할 수 없음** | **적용 대상이 없음** | **관측 시도가 실패함** |
| **타입** | SQL/parquet **null** — 상태값이 아니다 | `verdict_state`·`final_status`의 **열거값** | 같은 두 컬럼의 **열거값** | `measurement_status`의 **값 계열** |
| **수준** | 임의의 수치 컬럼 | Criterion | Criterion | Observation |
| **사는 곳** | `NED`·`IED`·`MPFED`·`ExcessDepth`·`primary_action_visible_initial`·`dismiss_control_*`·`rows_expected`·`value` … | `fact_criterion_result` | `fact_criterion_result` | `fact_landing_observation` |
| **전형 사례** | endpoint 미도달로 Depth 없음 (`A1` §1.5) | 대비비를 잴 수 있었으나 배경이 이미지라 확정 불가 | 그 페이지에 해당 기준의 적용 대상 자체가 없음 | 페이지가 로드되지 않음 |
| **집계 분모** | 그 변수의 분포에서 **제외** | `decision_coverage`의 **분모에 포함**, 분자에서 제외 | `decision_coverage_applicable`의 분모에서 **제외** | criterion 행이 **생성되지 않음** (규칙 M-1) |
| **0으로 대체** | **금지** | 해당 없음 (수치 아님) | 해당 없음 | 해당 없음 |

**규칙 N-1 (`NULL`은 상태값이 아니다).** `NULL`은 *수치 컬럼*의 결측 표현이고,
`UNDETERMINED`·`NA`·`MEASUREMENT_FAILED`는 *상태 컬럼*의 값이다.
`01 §11` `상태와 수치는 분리한다`가 여기서 작동한다 —
수치 컬럼에 `'UNDETERMINED'` 같은 문자열을 넣지 않고, 상태 컬럼을 `NULL`로 비워두지 않는다.

**규칙 N-2 (사유는 상태 컬럼에 있다).** `MPFED IS NULL` 인 이유는 `MPFED` 자신이 아니라
`endpoint_status`(§1.5.1) · `endpoint_status_detail`(§1.5.2) · `area_signal_status`(§1.5.3)가 말한다.
따라서 `NULL`을 보고할 때는 **반드시 짝이 되는 상태 컬럼을 함께 보고**한다.

**규칙 N-3 (관측된 0 ≠ NULL).** `NED = 0`(랜딩이 이미 영역이었다)과 `NED IS NULL`(영역을 못 봤다)은
**다른 사실이다.** 마찬가지로 `dismiss_control_exists = 0`(찾았으나 없었다)과
`dismiss_control_visible IS NULL`(찾을 대상이 없어 재지 않았다)도 다르다.

**규칙 N-4 (센티널 금지, 단 하나의 예외).** `-1` · `8` · `''` 같은 마법값으로 결측을 표현하지 않는다.
유일한 예외는 `dismiss_control_accessible_name = 'NAME_ABSENT'`이며,
이는 결측이 아니라 **"이름이 비어 있음이 관측됐다"는 양의 사실**이기 때문이다 (§1.6).

**규칙 N-5 (`MEASUREMENT_FAILED`는 UNDETERMINED가 아니다).** 수집 실패 관측은
`UNDETERMINED`로도 세지 않는다. criterion 행 자체를 만들지 않으며(규칙 M-1),
그 사실은 §4.1 evidence completeness와 frame coverage에서만 드러난다.
둘을 합치면 `UNDETERMINED stress bound`(`00 §11`)가 오염된다.

---

---

## 2. `ABSTAIN`의 귀속

> 구체화 대상: 00_SSOT §9 · 01_DATA_SPEC §9 / §7 · 04_GLOSSARY `Abstain`

### 2.1 어느 표의 어느 컬럼인가

**`ABSTAIN`은 `fact_ai_adjudication.final_status`의 값이다.** (§1.8)

다른 어느 표에도 이 값을 두지 않는다. 특히:

- `fact_criterion_result.final_status` — `ABSTAIN` **없음** (금지 전이 X-2)
- `fact_criterion_result.verdict_state` — `ABSTAIN` **없음**. 결정적 파이프라인은 기권하지 않는다. 판단이 안 되면 `UNDETERMINED`다
- `fact_interrupt_element.final_label` — `ABSTAIN` **없음**. 기권의 결과는 `UNKNOWN` 라벨 + `ai_review_status = ABSTAINED`

보조 컬럼:

| 컬럼 | 표 | ABSTAIN과의 관계 |
|---|---|---|
| `ai_review_status = ABSTAINED` | `fact_interrupt_element` · `dim_representative_task` | 해당 항목의 검토가 기권으로 끝났음을 표시하는 그림자 상태. 정본은 `fact_ai_adjudication.final_status` |
| `evidence_gap` | `fact_ai_adjudication` | 기권 사유가 "증거 부족"인지 "증거는 충분하나 의미가 갈림"인지 구분 |
| `human_required = 0` | `fact_ai_adjudication` | 기권한 항목은 사람 대기열에 올라가지 않는다 |

### 2.2 `UNDETERMINED`와 무엇이 다른가

| | `UNDETERMINED` | `ABSTAIN` |
|---|---|---|
| 수준 | Criterion (`fact_criterion_result`) | Adjudication (`fact_ai_adjudication`) |
| 뜻 | **판단불가** — 자료가 부족해 그 기준을 확정할 수 없다 | **판단보류** — 검토자가 확신할 수 없어 억지로 분류하지 않기로 했다 |
| 주체 | 측정 파이프라인 또는 최종 판정 | AI 검토 cascade |
| 대상 | 하나의 (관측 × KWCAG criterion) | 하나의 review item (criterion일 수도, interrupt일 수도, mapping일 수도 있다) |
| 분석에서의 쓰임 | `decision coverage`의 미확정분 (§4.2), `UNDETERMINED stress bound`(`00 §11`)의 대상 | `abstention rate`의 분자 (§4.5) |
| 관계 | `ABSTAIN`은 criterion 수준으로 전파될 때 **`UNDETERMINED`가 된다** (T-4) | |

**한 문장.** `UNDETERMINED`는 데이터에 대한 진술이고, `ABSTAIN`은 검토 과정에 대한 진술이다.
둘을 한 컬럼에 합치면 `abstention rate`(§4.5)와 `UNDETERMINED stress`가 서로를 오염시킨다.

### 2.3 강제분류를 유발하지 않는 경로

`00 §9`의 `5건을 초과하는 모호한 사례를 억지로 분류하지 않는다. 나머지는 UNDETERMINED / ABSTAIN.`
을 다음 결정적 순서로 이행한다.

```
1. cascade 1~5단계가 확정   → final_status = RESOLVED,  human_required = 0
2. 확정 못함 + 사람 예산 남음 → final_status = ESCALATED_HUMAN_FINAL, human_required = 1
                              ai_review_status = ESCALATED_HUMAN_FINAL
3. 확정 못함 + 사람 예산 소진 → final_status = ABSTAIN,  human_required = 0
                              ai_review_status = ESCALATION_DECLINED_BUDGET
4. ABSTAIN → (T-4) → fact_criterion_result.final_status = UNDETERMINED
```

**어느 분기에서도 값을 지어내지 않는다.** 3번 분기는 "예산이 없으니 대충 정하자"가 아니라
"예산이 없으므로 판단을 남기지 않는다"이며, 그 결과는 4번에서 `UNDETERMINED`로 **보존**된다.
`UNDETERMINED`는 `00 §11`의 `UNDETERMINED stress bound` 분석 대상이 되므로,
기권이 결론에 미치는 영향은 **숨겨지지 않고 정량화된다.**

**규칙 B-1.** 3번 분기가 발생한 건수(`ESCALATION_DECLINED_BUDGET`)는 `03 Phase 5` 측정품질 보고에
`abstention rate`와 **별도로** 명시한다. 예산 때문에 기권한 것과 증거 때문에 기권한 것은 다른 사실이다.

---

## 3. `automation_grade`

> 구체화 대상: 01_DATA_SPEC §7 · 02_COLLECTION §1 · 00_SSOT §10

### 3.1 허용값

`02 §1` 수집 우선순위 6단계와 `00 §10` 모델 사용 원칙 6단계는 **같은 사다리**다.
`automation_grade`는 그 사다리의 몇 번째 칸에서 이 행의 `final_status`가 결정됐는지를 기록한다.

| 값 | `02 §1` / `00 §10` 단계 | 무엇으로 정했는가 | 요구되는 증거 |
|---|---|---|---|
| `A_BROWSER_NATIVE` | 1. Playwright / Browser API · Browser native measurement | 브라우저가 직접 반환한 값 (`getComputedStyle` · AX tree 노드 · `getBoundingClientRect`) | `probe_path` + `dom_path` + `ax_path` |
| `B_DETERMINISTIC_RULE` | 2. DOM/AX/CSS/geometry · deterministic algorithm | A의 값 위에 KWCAG 원문 수치와 결정적 산식만 적용 | A의 증거 + 규칙 id + 적용한 임계값·파라미터 |
| `C_CV_GEOMETRY` | 3. pixel / image difference · classical CV / geometry | 픽셀·기하 계산 (canvas/이미지 내 텍스트 대비, overlay 실면적 검증 등) | `screenshot_path` + bbox + 알고리즘 id·파라미터 |
| `D_EMBEDDING_TEXT` | 4. NLP / embedding · embedding / text classifier | 텍스트 분류기·임베딩 유사도 | 입력 텍스트 + 모델 id + 점수 + 허용 label 목록 |
| `E_VLM` | 5. multimodal AI · pretrained VLM / MLLM | 멀티모달 검토 | `evidence_package_id` (`02 §10`) + 모델 id + JSON 출력 |
| `F_HUMAN_FINAL` | 6. 인간 최대 5건 · human final ≤5 | 사람 최종검토 | reviewer id + 근거 진술 + `evidence_package_id` |
| `UNGRADED` | — | 판정에 도달하지 못했다 | `verdict_state = UNDETERMINED` 또는 `NA` |

**상호배타.** 7값은 상호배타다.

### 3.2 산식

**규칙 G-1 (최소 등급 원칙).** `automation_grade`는 그 행의 `final_status`를 결정한
**가장 낮은 단계(= 사다리에서 가장 위)** 를 기록한다. A로 시작해 필요한 최소 단계까지만 내려간다.

```
automation_grade = min{ 단계 k : k단계까지의 증거로 final_status가 확정됨 }
                 = 'UNGRADED'  if final_status ∈ {UNDETERMINED, NA}
```

`00 §10` `모델을 쓰기 위해 모델을 쓰지 않는다`와 `02 §1`
`브라우저가 이미 알고 있는 정보는 AI가 다시 추정하지 않는다`의 기계적 이행이다.
A로 확정 가능한 항목을 E로 기록하면 결함이다.

### 3.3 정합 제약

| # | 제약 |
|---|---|
| **G-2** | `automation_grade ∈ {D_EMBEDDING_TEXT, E_VLM, F_HUMAN_FINAL}` → `ai_review_required = 1` |
| **G-3** | `automation_grade ∈ {A_BROWSER_NATIVE, B_DETERMINISTIC_RULE}` → 대응 `fact_ai_adjudication` 행이 없거나 `evidence_gap = 0` |
| **G-4** | `automation_grade = F_HUMAN_FINAL` 인 distinct `review_item_id` 수 ≤ **5** (`HUMAN_FINAL_REVIEW_MAX`) |
| **G-5** | `automation_grade = UNGRADED` ↔ `final_status ∈ {UNDETERMINED, NA}` (동치) |
| **G-6** | 등급이 요구하는 증거가 하나라도 없으면 그 등급을 기록할 수 없다. 증거 없이 상위 등급을 주장하지 않는다 |

### 3.4 분석에서의 쓰임

`automation_grade` 분포는 `03 Phase 5` 측정품질 보고의 필수 항목이다.
`D`·`E` 비중이 높으면 결론의 근거가 모델 판단에 의존한다는 뜻이므로,
`00 §14` claim boundary 안에서 서술할 때 그 비중을 함께 밝힌다.

**`automation_grade`는 정확도가 아니다.** 낮은 등급이 더 정확하다는 뜻이 아니라
**더 재현 가능하다**는 뜻이다. 두 의미를 바꿔 쓰지 않는다.

---

## 4. 품질지표 산식

> 구체화 대상: 03_CRISP_DM Phase 5 / Phase 6 · 01_DATA_SPEC §10 · 00_SSOT §9

`03 Phase 6`은 `모든 주요 문장은 numerator/denominator와 artifact에 역추적 가능해야 한다`고 요구한다.
아래 6개 지표의 분자·분모를 확정한다.

| # | 지표 | 수준 |
|---|---|---|
| 4.1 | evidence completeness | Observation |
| 4.2 | decision coverage | Criterion |
| 4.3 | AI review rate | Criterion / Interrupt |
| 4.4 | reviewer agreement | Adjudication |
| 4.5 | abstention rate | Adjudication |
| 4.6 | human escalation ≤5 | Adjudication (절대 상한) |

### 4.1 evidence completeness

| | 정의 |
|---|---|
| 분자 | `measurement_status = MEASURED` 이면서 evidence identity 집합의 경로가 모두 non-null이고, `07_EVIDENCE_MANIFEST_CONTRACT` 검증 결과가 `VERIFIED`인 observation 수 |
| 분모 | 관측이 **시도된** 전체 observation 수 = `fact_landing_observation` 행수 |

**evidence identity 집합.** `02 §11`은 5종(DOM / AX / screenshot / probe / manifest)을 열거하지만
`02 §3`은 screenshot 2종과 computed CSS를 수집한다. `A1` §6.2가 이 집합을
`DOM / AX / screenshot(initial) / screenshot(fullpage) / computed CSS / probe / manifest` **7종**으로 확정했다.
분자는 그 7종 경로 컬럼
(`dom_path` · `ax_path` · `screenshot_initial_path` · `screenshot_fullpage_path` ·
`computed_css_path` · `probe_path` · `manifest_path`)을 센다.

**주의 0.** `manifest_path`는 run manifest 경로이며 **관측마다 고유하지 않다** —
한 run의 전 관측이 같은 값을 공유한다 (`07` §3 grain · `A1` §6.2).
고유성 검사를 이 컬럼에 걸지 않는다.

**주의 1.** `07 §4`의 `MANIFEST_WELL_FORMED_FILES_NOT_CHECKED`는 분자에 넣지 **않는다.**
`검사하지 않은 것을 통과로 세지 않는다`(07 §4).

**주의 2.** 이 비율만으로는 "적격인데 아예 시도되지 않은 타겟"이 보이지 않는다.
반드시 **frame coverage**를 병기한다.

```
frame_coverage = |관측 행이 1개 이상 있는 web target| / |web_eligibility_status = ELIGIBLE_WEB 인 web target|
```

두 분모가 다르다는 점이 핵심이다 — 규칙 M-2가 말한 "행의 부재"는 여기서만 잡힌다.

### 4.2 decision coverage

`01 §10` `mart_service_summary`와 `03 Phase 5`가 함께 쓰는 지표다. **두 변종을 모두 저장한다.**

| 변종 | 분자 | 분모 |
|---|---|---|
| `decision_coverage_applicable` **(정본)** | `final_status ∈ {PASS, FAIL}` 인 criterion observation 수 | `final_status ∈ {PASS, FAIL, UNDETERMINED}` 인 criterion observation 수 |
| `decision_coverage_all` (보조) | `final_status ∈ {PASS, FAIL, NA}` | `final_status ∈ {PASS, FAIL, NA, UNDETERMINED}` |

**정본은 `decision_coverage_applicable`이다.** "적용기회가 있는 기준 중 판정이 확정된 비율"이며,
`NA`를 분모에 넣는 `decision_coverage_all`은 적용기회가 적은 서비스에서 값이 부풀려진다.
보고 시 **어느 변종인지 반드시 명시**한다.

항등식:

```
decision_coverage_applicable = 1 - undetermined_rate_applicable
undetermined_rate_applicable = |UNDETERMINED| / |{PASS, FAIL, UNDETERMINED}|
```

**함정 경고 (필수 병기).** `decision coverage`는 **수집 실패를 숨긴다.**
규칙 M-1에 따라 수집 실패 관측은 criterion 행을 만들지 않으므로 분모에 들어오지 않는다.
따라서 `decision coverage`는 **항상 `evidence completeness`(§4.1)와 함께** 보고한다.
둘 중 하나만 제시한 문장은 `03 Phase 6` 역추적 요구를 만족하지 않는다.

서비스 수준(`mart_service_summary`)은 같은 산식을 그 서비스의 criterion observation으로 좁혀 계산한다.

### 4.3 AI review rate

| 수준 | 분자 | 분모 |
|---|---|---|
| Criterion | `ai_review_required = 1` 인 criterion observation 수 | 전체 criterion observation 수 |
| Interrupt | `ai_review_status ≠ NOT_REQUIRED` 인 interrupt element 수 | 전체 interrupt element 수 |
| Mapping | `mapping_ai_review_status ≠ NOT_REQUIRED` 인 task 수 | 전체 task 수 |

**병기 필수 — model-decided rate.** AI 검토를 **거친** 비율과 AI가 **결과를 정한** 비율은 다르다.

```
model_decided_rate = |automation_grade ∈ {D_EMBEDDING_TEXT, E_VLM}| / |전체 criterion observation|
```

`00 §10` 모델 사용 원칙의 준수 여부는 `AI review rate`가 아니라 이 값으로 판단한다.

### 4.4 reviewer agreement

| | 정의 |
|---|---|
| 분자 | `reviewer_a_label = reviewer_b_label` 인 review item 수 |
| 분모 | reviewer A·B가 **둘 다** 라벨을 낸 review item 수 (= `reviewer_agreement ≠ NA`) |

**규칙 R-1 (이중계산 금지).** 한쪽이라도 `ABSTAIN`이거나 라벨이 없는 item은
분모에서 제외하고 `abstention rate`(§4.5)에서만 센다. 두 지표의 분모는 겹치지 않는다.

**규칙 R-2.** 라벨 분포가 한 값에 심하게 쏠리면 단순 일치율이 과대평가되므로,
우연일치 보정치(Cohen's κ 등)를 병기할 수 있다. 단 **단순 일치율은 항상 함께 보고**하며
보정치만 제시하지 않는다.

**규칙 R-3.** `reviewer agreement`는 정확도가 아니다. 두 AI가 같은 오류를 낼 수 있다.
이 값을 근거로 라벨을 gold라 부르지 않는다 (`00 §9`).

### 4.5 abstention rate

| | 정의 |
|---|---|
| 분자 | `fact_ai_adjudication.final_status = ABSTAIN` 인 review item 수 |
| 분모 | `fact_ai_adjudication` 전체 review item 수 (= AI 검토에 올라온 건수) |

**분해 (규칙 B-1).** 분자를 사유별로 나눠 함께 보고한다.

| 성분 | 조건 |
|---|---|
| 증거 부족 기권 | `ABSTAIN` ∧ `evidence_gap = 1` |
| 의미 모호 기권 | `ABSTAIN` ∧ `evidence_gap = 0` ∧ `ai_review_status ≠ ESCALATION_DECLINED_BUDGET` |
| 예산 소진 기권 | `ABSTAIN` ∧ `ai_review_status = ESCALATION_DECLINED_BUDGET` |

**주의.** `abstention rate`의 분모는 **AI 검토에 올라온 건수**이지 전체 criterion observation이 아니다.
criterion 수준의 `UNDETERMINED` 비율(§4.2)과 다른 값이며, 서로 대체할 수 없다.
`UNDETERMINED`에는 (a) AI 검토에 올라가지도 않고 결정적 단계에서 이미 판단불가였던 것과
(b) `ABSTAIN` 전파분(T-4)이 섞이므로, 두 성분을 나눠 보고한다.

### 4.6 human escalation ≤5

**이것은 비율이 아니라 절대 상한 게이트다.** 분모가 없다.

| | 정의 |
|---|---|
| 카운트 | `fact_ai_adjudication.human_required = 1` 인 **distinct `review_item_id`** 수 + `dim_representative_task.human_final_required = 1` 인 task 수 |
| 상한 | **5** (`HUMAN_FINAL_REVIEW_MAX`, `00 §9` · `EXECUTION_AUTHORITY §1`) |
| 판정 | 카운트 ≤ 5 이면 PASS. 초과하면 `03 Phase 5` 측정품질 FAIL |

**두 컬럼은 같은 예산을 공유한다.** mapping 검토와 판정 검토를 각각 5건씩 쓰지 않는다.

**규칙 H-1 (결정적 선발).** 후보가 5건을 넘으면 `review_priority` 내림차순으로 상위 5건만 남기고,
나머지는 §2.3의 3번 분기(`ABSTAIN` + `ESCALATION_DECLINED_BUDGET`)로 보낸다.
`review_priority`는 다음 결정적 순서로 정하며, **접근성 outcome과 `certified_current`를 보기 전에 확정한다**
(`00 §6` 동결 원칙 준용).

```
review_priority 정렬키 = ( impact_level {HIGH=3, MEDIUM=2, LOW=1} 내림차순,
                          evidence_gap {0=먼저} 오름차순,
                          review_item_id 사전순 )
```

`evidence_gap = 1` 인 항목을 뒤로 두는 이유는, 사람이 봐도 증거가 없으면 확정할 수 없어
5건 예산이 낭비되기 때문이다. 증거는 있는데 의미가 갈리는 항목이 사람 검토의 최적 대상이다.

**병기.** `human_escalation_rate = 카운트 / |fact_ai_adjudication 전체 review item|`
을 함께 보고한다. 절대 카운트만으로는 검토 규모 대비 비중이 보이지 않는다.

---

## 5. 논리 ↔ 물리 대응표

> 구체화 대상: 01_DATA_SPEC 서두 / §2 / §3 · 03_CRISP_DM Phase 3-7 / P-A / P-B

### 5.0 이 절의 전제

**`01 §2`의 절 제목 `기존 정형 데이터`는 오해를 부른다.**
`dim_panel` · `fact_source_ranking` · `dim_measurement_entity` · `bridge_source_membership` 이라는
**이름의 파일은 존재하지 않는다.** 이들은 매핑 레이어가 제공할 **논리 표의 이름**이다.
`state/` 아래의 실제 파일명은 `panel_registry` · `source_ranking_rows` · `service_master` · `source_membership` 이다.

**규칙 V-1 (원본 불변).** `state/*.parquet` 원본은 **삭제·rename·migration하지 않는다** (`01` 서두 · `03 Phase 3`).
이 절의 대응은 **read-only view 또는 별도 경로의 머티리얼라이제이션**으로만 제공한다.
매핑 산출물은 원본 파일을 덮어쓰지 않으며, 원본과 다른 디렉터리에 둔다.
원본을 논리명으로 바꾸는 것은 이 문서가 요구하는 바가 **아니다.**

**규칙 V-2 (대응 분류).** 각 논리 필드를 다음 셋 중 하나로 분류한다.

| 분류 | 뜻 |
|---|---|
| **(a) DIRECT** | 물리 컬럼에 직접 대응. 이름만 다르거나 그대로다 |
| **(b) DERIVED** | 조인·파생으로 유도 가능. 유도 규칙을 명시한다 |
| **(c) ABSENT** | 아직 존재하지 않는다. 산출 Phase를 명시한다 (P-A / P-B / P-C / P-F) |

**규칙 V-3 (grain 우선).** 이름이 대응해도 **grain(입도)이 다르면 대응이 아니다.**
이 절은 이름보다 grain 불일치를 먼저 표기한다.

### 5.1 `dim_panel` ↔ `panel_registry.parquet`

**grain 일치.** 논리 grain = panel, 물리 grain = panel. 키 `panel_id`, **17행 / 중복 0** `[실측]`.
물리는 26컬럼 `[실측]`이며 논리가 요구하는 8개는 그 부분집합이다.

| 논리 (01 §2 `dim_panel`) | 물리 (`panel_registry`) | grain | 대응 | 비고 |
|---|---|---|---|---|
| `panel_id` | `panel_id` | panel | (a) DIRECT | 17행 유일 `[실측]` |
| `domain` | `domain` | panel | (a) DIRECT | `APP` / `RETAIL` 2값 `[실측]` |
| `axis_type` | `axis_type` | panel | (a) DIRECT | `SERVICE_BRAND` / `INDUSTRY_CATEGORY` 2값 `[실측]` |
| `source_section` | `source_section` | panel | (a) DIRECT | `int64`, 4개 값 `[실측]`. 제목은 별도 `source_section_title` |
| `period_axis` | `period_axis` | panel | (a) DIRECT | `HALF_YEAR` / `SINGLE_MONTH` 2값 `[실측]` |
| `metric_name` | `metric_columns` (JSON 배열) · `n_metrics` | **불일치** | (b) DERIVED | **panel당 metric이 1~4개** `[실측: n_metrics = 1→8, 2→5, 3→3, 4→1 패널]`. 논리가 가정한 panel당 단일 `metric_name`은 성립하지 않는다. 스칼라 metric은 `source_ranking_rows.metric_name`(261행 수준, 23종 `[실측]`)에 있다 |
| `unit` | `metric_columns[].unit` · `source_ranking_rows.unit` | **불일치** | (b) DERIVED | 위와 동일. `unit` 9종 `[실측]` |
| `rows_expected` | `rows_expected` | panel | (a) DIRECT | **`Int64`, 9/17 nonnull — 8행 결측** `[실측]`. 결측은 `row_count_verification = VISUAL_COUNT_ONLY`(8행 `[실측]`)에 대응하며 **0으로 채우지 않는다** |

**지적 1 (grain).** `metric_name`·`unit`을 `dim_panel`의 컬럼으로 두면 9개 패널에서 값이 하나로 정해지지 않는다
`[실측: n_metrics > 1 인 패널 9개]`. 매핑 레이어는 둘 중 하나를 택해야 한다 —
① `dim_panel`에서 두 컬럼을 빼고 `fact_source_ranking` 수준에서만 다루거나,
② `dim_panel_metric`(panel × metric) 브리지를 신설한다. **P-A에서 결정한다.**

### 5.2 `fact_source_ranking` ↔ `source_ranking_rows.parquet`

**grain 일치.** 논리·물리 모두 source row. 키 `source_row_id`, **261행 / 중복 0** `[실측]`.

| 논리 (01 §2) | 물리 (`source_ranking_rows`) | grain | 대응 | 비고 |
|---|---|---|---|---|
| `source_row_id` | `source_row_id` | source row | (a) DIRECT | 261행 유일 `[실측]` |
| `panel_id` | `panel_id` | source row | (a) DIRECT | 17종 `[실측]` |
| `measurement_entity_id` | **없음** | source row | **(b) DERIVED** | §5.2.1 조인으로 유도 |
| `rank` | `rank` | source row | (a) DIRECT | `int64` `[실측]` |
| `raw_label` | `value_label` | source row | (a) DIRECT | **254/261 nonnull — 7행 결측** `[실측]` |
| `raw_value` | `value` | source row | (a) DIRECT | `float64`, **254/261 nonnull — 7행 결측** `[실측]` |
| `raw_unit` | `unit` | source row | (a) DIRECT | 9종 `[실측]` |
| — | `entity_name_raw` | source row | **논리에 자리 없음** | 원문 표기 문자열(81종 `[실측]`). 논리 표가 `measurement_entity_id`만 두면 **원문 표기가 소실된다.** 매핑 레이어는 이 컬럼을 유지해야 한다 — `02 §14` ID collision 검사와 계보 추적의 근거다 |

**결측 실측.** `value`/`value_label` 결측 7행은 전부 `panel_id = fig07_t1`, `metric_name = 성장률`, `unit = %` 다 `[실측]`.
원문 이미지에 수치가 표기되지 않은 행이며, **0이 아니다.** `01 §11` 결측 0 치환 금지 대상이다.

#### 5.2.1 `measurement_entity_id` 유도 — 조인 성립 실측

`source_ranking_rows`에는 `measurement_entity_id`(= 물리 `service_id`) 컬럼이 **없다.**
`entity_alias_map`을 다음 키로 조인해 유도한다.

```
source_ranking_rows ⋈ entity_alias_map  ON (entity_name_raw, domain, axis_type)
```

**실측 결과 (작성 시점 재실측):**

| 검사 | 결과 |
|---|---|
| 조인 키 `(entity_name_raw, domain, axis_type)`의 `entity_alias_map` 내 유일성 | **중복 0 · 유일 키 82종** `[실측]` |
| 좌변 행수 | **261** `[실측]` |
| 조인 결과 행수 | **261** `[실측]` |
| **fan-out** | **0** `[실측]` |
| **미매칭** | **0** `[실측]` |
| 유도된 distinct `(service_id, panel_id)` 쌍 | **142** `[실측]` |
| `source_membership.parquet` 행수 | **142** `[실측]` |
| 두 집합의 동일성 | **동일** — 차집합 양방향 **0** `[실측]` |

조인이 1:1로 성립하고, 유도 결과가 저장된 물리 표와 정확히 일치한다.

**교차검증 2건 (추가 실측):**

| 검사 | 결과 |
|---|---|
| `source_membership.rank` == 조인 결과의 `min(rank)` | **불일치 0** `[실측]` |
| `source_membership.n_metrics` == `panel_registry.n_metrics` | **불일치 0** `[실측]` |
| `entity_alias_map.panel_ids`(쉼표 구분)를 explode한 `(service_id, panel_id)` 쌍 | **142쌍, `source_membership`과 집합 동일** `[실측]` |

세 경로(조인 유도 · 저장된 물리 표 · alias의 `panel_ids` explode)가 **같은 답을 준다.**

**주의 — 조인 키 유일성의 취약점.** 키가 유일한 것은 현재 데이터에서만 확인된 사실이다.
`entity_name_raw = '쿠팡'` 은 **2행**에 나타나며 `domain`(APP / RETAIL)으로만 갈린다 `[실측]`.
`entity_name_raw` 단독 조인은 fan-out을 일으킨다. **키 3요소를 모두 써야 한다.**
`entity_alias_map`은 82행 / 81 service_id이며, 2개 별칭을 가진 유일한 service는
`현대홈쇼핑/현대Hmall` ↔ `현대홈쇼핑/현대Hmallord`(원문 오타 흡수, `match_basis = REVIEWED`) 다 `[실측]`.
`match_basis` 분포는 `EXACT` 81 / `REVIEWED` 1 `[실측]`.

### 5.3 `dim_measurement_entity` ↔ `service_master.parquet`

**grain 일치.** 논리·물리 모두 measurement entity. 키 `service_id`, **81행 / 중복 0** `[실측]`.
물리는 24컬럼 `[실측]`.

| 논리 (01 §2) | 물리 (`service_master`) | grain | 대응 | 비고 |
|---|---|---|---|---|
| `measurement_entity_id` | `service_id` | entity | (a) DIRECT | **키 이름이 다르다.** 81행 유일 `[실측]` |
| `canonical_name` | `service_name_canonical` | entity | (a) DIRECT | **81행 중 고유값 80** `[실측]` — 이름은 유일키가 **아니다**. 중복은 `쿠팡`(APP/RETAIL) 1쌍 `[실측]` |
| — | `canonical_service_key` | entity | 사실상의 자연키 | **81행 유일** `[실측]`. 사람이 읽는 안정 키. 논리 표에 자리가 없다 — 유지 필요 |
| `source_domain` | `domain` | entity | (a) DIRECT | `APP` / `RETAIL` `[실측]` |
| `entity_type` | `axis_type` | entity | (b) DERIVED | `01`에 `entity_type`의 정의가 없다. `SERVICE_BRAND` / `INDUSTRY_CATEGORY` 2값으로 바인딩한다 `[실측]` |
| `review_status` | `review_decision` + `needs_human_review` | entity | **(b) DERIVED** | §1.1의 식. 실측 `NOT_IN_REVIEW_QUEUE` 74 / `KEEP_SEPARATE` 6 / `MERGE` 1 / `PENDING_HUMAN_REVIEW` 0 `[실측]` |

**지적 2 (ID collision).** `service_name_canonical`이 유일하지 않다는 사실 `[실측: 81행 / 80고유]` 은
`02 §14`가 smoke 대상으로 지정한 `같은 길이의 한글 이름 등 ID collision 위험` 과 직접 연결된다.
매핑 레이어는 표시명이 아니라 `service_id` 또는 `canonical_service_key`로 조인해야 한다.

### 5.4 `bridge_source_membership` ↔ `source_membership.parquet` — **grain 불일치**

**이것이 `V2-C001` F12가 지적한 핵심 불일치다.**

| | 논리 `bridge_source_membership` | 물리 `source_membership.parquet` |
|---|---|---|
| grain | **source row 단위** (`measurement_entity_id`, `panel_id`, **`source_row_id`**) | **(service_id, panel_id) 집계 단위** |
| 기대 행수 | **261** (source row 수) | **142** `[실측]` |
| `source_row_id` 컬럼 | 있음 | **없음** `[실측: 7컬럼 = service_id, panel_id, figure_id, domain, axis_type, rank, n_metrics]` |

| 논리 필드 | 물리 | grain | 대응 | 비고 |
|---|---|---|---|---|
| `measurement_entity_id` | `service_id` | (svc, panel) | (a) DIRECT | 81종 `[실측]` |
| `panel_id` | `panel_id` | (svc, panel) | (a) DIRECT | 17종 `[실측]` |
| `source_row_id` | **없음** | — | **(b) DERIVED** | §5.2.1 조인으로 261행 bridge를 유도한다 |

**판정.** 물리 `source_membership`은 논리 `bridge_source_membership`이 **아니다.**
그것은 논리 bridge의 **결정적 집계 뷰**다 — §5.2.1의 실측대로 조인 결과의
distinct `(service_id, panel_id)` 142쌍과 정확히 일치하고,
`rank`·`n_metrics`도 조인 결과·`panel_registry`로부터 불일치 0으로 재현된다 `[실측]`.
즉 **독립 정보를 담고 있지 않다.**

**매핑 레이어 산출.**
- 논리 `bridge_source_membership`(261행) = `source_ranking_rows ⋈ entity_alias_map` 의 read-only view. **P-A**.
- 물리 `source_membership`(142행)은 그대로 둔다. 유도 결과와의 일치는 **회귀검사**로 상시 확인한다.

### 5.5 `dim_web_target` ↔ `web_target_group.parquet` + `service_master` — **grain 불일치**

**`web_target_group`은 `dim_web_target`이 아니다.** URL 확정 **이전의 그룹 후보 표**다.

| | 논리 `dim_web_target` | 물리 `web_target_group.parquet` |
|---|---|---|
| grain | web target (확정된 공식 URL 1개) | **URL 검토 전 그룹 후보** |
| 행수 | **미확정** `[미측정]` | **68** `[실측]` (`member_count` 1→65, 2→3 `[실측]`) |
| 확정성 | P-B에서 동결 | **전부 가설** — `expected_url_relationship_is_hypothesis = True` 3건, `confirmed_by_url = True` **0건** `[실측]` |

| 논리 (01 §3) | 물리 | grain | 대응 | 비고 |
|---|---|---|---|---|
| `web_target_id` | `web_target_group_id` | **불일치** | (b) DERIVED, **불확정** | 그룹은 "같은 랜딩일 것"이라는 **가설**이며 URL 확정 시 SPLIT될 수 있다. `expected_url_relationship_falsifier`가 3건 명시돼 있다 `[실측]`. 1:1 대응으로 취급하면 안 된다 |
| `measurement_entity_id` | `service_master.web_target_group_id` ← `service_id` | entity → group | (b) DERIVED | **nonnull 71 / null 10** `[실측]`. null 10은 `EXCLUDED_INDUSTRY_AXIS` 10과 일치 `[실측]`. distinct group **68** `[실측]` (71 entity = 65 singleton + 3 그룹 × 2 member) |
| `web_eligibility_status` | `service_master.web_eligibility_status` | **entity 수준** | (b) DERIVED, **grain 불일치** | 논리는 web target 수준. 현재 81건 판정은 entity 수준이다 (§1.3) |
| `web_target_status` | `web_target_group.grouping_status` · `service_master.web_target_grouping_status` | group / entity | (b) DERIVED, 부분 | 두 물리 값(`SINGLETON_PENDING_URL_REVIEW` 65 / `CANDIDATE_PENDING_URL_REVIEW` 3 `[실측]`)이 모두 `PENDING_URL_REVIEW` 하나에 대응 (§1.4) |
| `official_landing_url` | `web_target_group.web_target_url` | — | **(c) ABSENT → P-B** | **nonnull 0** `[실측]` — 컬럼은 있으나 전량 결측 |
| `url_evidence` | `web_target_group.url_evidence` | — | **(c) ABSENT → P-B** | **nonnull 0** `[실측]` |
| `final_url` | 없음 | — | **(c) ABSENT → P-C** | 수집 시점에 채워진다 (`02 §2`) |
| `registered_domain` | 없음 | — | **(c) ABSENT → P-B** | `expected_url_relationship_falsifier`가 PSL 등록도메인 비교를 요구한다 `[실측]` |
| `url_confidence` | 없음 | — | **(c) ABSENT → P-B** | |

**지적 3.** `01 §3`이 `dim_web_target`을 `신규`로 분류하지만 기준선에 이미 `web_target_group`(68행, C012 산물)이 있다.
둘의 관계는 **대응이 아니라 선행**이다 — `web_target_group`은 P-B의 **입력**이며,
URL 증거로 검증되면 `dim_web_target` 행이 되고, falsifier가 성립하면 SPLIT된다.
`expected_url_relationship_confirmed_by_url`이 전부 `False` `[실측]` 인 지금,
그룹을 web target으로 간주한 어떤 집계도 근거가 없다.

### 5.6 나머지 논리 표 — 전부 (c) ABSENT

| 논리 표 | 출처 | 산출 Phase | 현재 물리 대응 |
|---|---|---|---|
| `dim_representative_task` | 01 §3 | **P-A**(codebook·pilot 매핑) → **P-B**(동결) | 없음 |
| `fact_landing_observation` | 01 §4 | **P-C**(엔진) → **P-F**(본수집) | 없음 |
| `fact_interrupt_element` | 01 §5 | P-C → P-F | 없음 |
| `fact_task_entry` | 01 §6 | P-C → P-F | 없음 |
| `fact_task_step` | 01 §6 | P-C → P-F | 없음 |
| `fact_criterion_result` | 01 §7 | P-C → P-F | 없음 |
| `dim_certification` | 01 §8 | **P-B**(join 준비) → P-F | `state/_invalidated/service_certification_match_draft.csv` 는 **무효화 보관물**이며 대응이 아니다. 인용 금지 |
| `fact_ai_adjudication` | 01 §9 | P-C(cascade 검증) → **P-G** | 없음 |
| `fact_task_episode` | **A1 §4.4** (신규 제안) | P-C → P-F | 없음. 매핑/머티리얼라이제이션 레이어 산출물 (`A1` §5.4) |
| `fact_primary_action_candidate` | **A1 §5.1** (신규 제안) | P-C → P-F | 없음. 매핑/머티리얼라이제이션 레이어 산출물 (`A1` §5.4) |
| `mart_service_summary` | 01 §10 | **P-H** | 없음 |
| `mart_archetype_summary` | 01 §10 | **P-H** | 없음 |

### 5.7 매핑 레이어 산출 규약

| # | 규약 |
|---|---|
| **V-4** | 매핑은 **read-only view 또는 별도 경로의 머티리얼라이제이션**으로만 제공한다. `state/*.parquet` 원본을 읽기만 하고 쓰지 않는다 |
| **V-5** | 산출물은 원본과 **다른 디렉터리**에 둔다. 원본 파일명을 논리명으로 바꾸지 않는다 |
| **V-6** | 모든 논리 표는 **유도 식과 실측 회귀검사**를 함께 갖는다. §5.2.1의 3개 검사(행수 261 / fan-out 0 / 집합 동일 142)는 회귀검사로 상시 실행한다 |
| **V-7** | grain이 다른 대응(§5.4 · §5.5)은 **뷰 이름에 grain을 드러낸다**. `source_membership`을 `bridge_source_membership`이라는 이름으로 노출하지 않는다 |
| **V-8** | `research/refcohort/**`(Pilot)은 `READ_ONLY`다. 매핑 레이어는 Pilot 산물을 수정하지 않는다 |

---

## 6. P-B / P-C에서 산출해야 하는 미존재 표·컬럼

> 구체화 대상: 03_CRISP_DM P-A / P-B / P-C · 00_SSOT §15

이 목록은 **이 문서가 신설한 요구가 아니라**, `01`/`02`가 이미 요구했으나 물리적으로 없는 것의 목록이다.

### 6.1 P-A (분석 기반 + task codebook)

| 산출물 | 내용 |
|---|---|
| `bridge_source_membership` view (261행) | §5.2.1 조인의 read-only view + 회귀검사 3종 |
| `dim_panel` view (17행) | §5.1. `metric_name`/`unit` grain 문제의 결론(①/② 중 택1) 포함 |
| `fact_source_ranking` view (261행) | `measurement_entity_id` 유도 + `entity_name_raw` 유지 |
| `dim_measurement_entity` view (81행) | `review_status` 유도 (§1.1) |
| `dim_representative_task` 초안 | `interaction_archetype` · `endpoint_definition` codebook (`03 P-A`) |
| **컬럼**: `region_definition` · `region_signal_type` | `A1` §1.8 신규 필드. 서비스별 값은 endpoint codebook과 **함께 동결** (§1.9) |
| **컬럼**: `dim_panel_metric` 브리지 (선택) | §5.1 지적 1의 ② 안을 택할 경우 |

### 6.2 P-B (target / task frame)

| 산출물 | 내용 |
|---|---|
| `dim_web_target` 표 전체 | 현재 어떤 물리 표도 이 grain을 갖지 않는다 (§5.5) |
| **컬럼**: `web_target_id` | `web_target_group_id`와 다르다. 그룹 가설 검증 후 확정 |
| **컬럼**: `official_landing_url` | `web_target_group.web_target_url` nonnull **0** `[실측]` |
| **컬럼**: `url_evidence` | nonnull **0** `[실측]` |
| **컬럼**: `url_confidence` | 물리 컬럼 없음 |
| **컬럼**: `registered_domain` | 물리 컬럼 없음. falsifier 판정에 필요 `[실측: falsifier 3건 기재]` |
| **값**: `web_eligibility_status` 4값 | `ELIGIBLE_WEB` · `EXCLUDED_APP_ONLY` · `EXCLUDED_NO_PUBLIC_WEB_LANDING` · `UNDETERMINED_URL_EVIDENCE` — 현재 전부 0건 `[실측]` |
| **값**: `web_target_status` 4값 | `DRAFT` · `FROZEN` · `EXCLUDED` · `SUPERSEDED` — 현재 전부 0건 `[실측]` |
| `dim_representative_task` 동결 | `mapping_status = FROZEN` 전이. 규칙 P-1 순서 준수. `region_signal_type = CODEBOOK_PENDING` 잔여 0 (규칙 P-2) |
| `dim_certification` join 준비 | `state/_invalidated/`의 draft는 무효 보관물이며 입력이 아니다 |
| 3건 그룹 가설 검정 | `expected_url_relationship_falsifier` 3건 `[실측]` 을 URL 증거로 검정. SPLIT 여부 확정 |

### 6.3 P-C (L0/L1 엔진)

| 산출물 | 내용 |
|---|---|
| `fact_landing_observation` 표 | `measurement_status` 6값 어휘 구현 (§1.2) |
| **컬럼**: `screenshot_initial_path` · `screenshot_fullpage_path` · `computed_css_path` · `evidence_run_id` · `collection_started_at` · `collection_finished_at` · `viewport_configured_*` · `device_pixel_ratio` | `A1` §6.1. §4.1 evidence completeness 분자의 근거 |
| `fact_interrupt_element` 표 | `classification_status` 5값 · `final_label` 10값 · `ai_review_status` 7값 (§1.6 · §1.10) |
| **컬럼**: `dismiss_method` 5값 · `dismiss_failure_mode` 5값 · `dismiss_persistence_hint` · `dismiss_screenshot_before/after` · `dismiss_dom_after` | `A1` §3.3 · §3.4 (§1.6) |
| `fact_task_entry` 표 | `endpoint_status` 7값 + `endpoint_status_detail` 3값 + `area_signal_status` 3값 (§1.5). 규칙 N-1~N-5 `NULL` 처리 구현 |
| `fact_task_step` 확장 | `depth_segment` 3값 · `counts_toward_depth` · `area_signal_detected` (§1.5.4, `A1` §1.8) |
| `fact_task_episode` 표 (신규) | `episode_kind` 2값 · `ended_by` 9값 · `input_mode` 2값 (§1.12, `A1` §4.4) |
| `fact_primary_action_candidate` 표 (신규) | `selection_basis` 4값 · `selection_status` 3값 · `area_css_px2` (§1.13, `A1` §5.1) |
| `fact_task_step` 표 | — |
| `fact_criterion_result` 표 | `verdict_state` · `final_status` · `automation_grade` 7값 · `ai_review_required` (§1.7 · §3) |
| `fact_ai_adjudication` 표 | `final_status` 4값(`ABSTAIN` 포함) · `human_required` · `review_priority` (§1.8 · §2) |
| **가드**: 전이 규칙 T-1~T-6 | 파이프라인에 강제 |
| **가드**: 금지 전이 X-1~X-6 | `02 §14` 실패주입으로 차단 검증 |
| **가드**: 정합 제약 G-2~G-6 | `automation_grade` 검증 |
| **가드**: 항등식 | `applicable_count = pass_count + fail_count + undetermined_count` (§1.7) |
| **지표**: §4의 6개 산식 | numerator/denominator를 코드로 고정. `03 Phase 6` 역추적 요구 |

### 6.4 이 문서가 닫지 않는 것

`V2-C001`의 나머지 finding은 이 문서의 소관이 아니며, 아래 문서들이 닫았다.
이 문서는 그 결과를 **참조**하고 값 도메인만 확정했다.

| 결함 | 닫은 문서 | 이 문서와의 접점 |
|---|---|---|
| F1 `ned-ied-split-not-operationalized` | `A1` §1 | §1.5.3 `area_signal_status` · §1.9 `region_signal_type` |
| F2 `interrupt-dismiss-fields-have-no-collection-procedure` | `A1` §3 | §1.6 `dismiss_method` · `dismiss_failure_mode` · `NAME_ABSENT` |
| F3 `episode-counters-undefined-and-uncollected` | `A1` §4 | §1.12 `fact_task_episode` 값 도메인 |
| F4 `primary-action-identity-not-stored` | `A1` §5 | §1.13 `fact_primary_action_candidate` 값 도메인 |
| F5 `l0-evidence-artifacts-without-storage-slot` | `A1` §6 | §4.1 evidence completeness 분자의 7종 집합 |
| `l1-scout-has-no-step-budget` (adversarial) | `A1` §2 | §1.5.2 `endpoint_status_detail` · 규칙 E-4 |
| F8 `phase-gate-names-only-in-nonauthoritative-bootstrap` | `PHASE_GATES.md` | §6의 산출 Phase 귀속 |
| F9 · F10 · F11 · F13 · adversarial P1 3건 | `EXECUTION_AUTHORITY.md` 외 | §0 권위 서열 |

**여전히 P-A/P-B/P-C로 미룬 것** — 이 문서가 값 도메인은 확정했으나 **서비스별 값이 비어 있는** 항목이다.

| 항목 | 동결 Phase |
|---|---|
| `region_definition` · `endpoint_definition`의 **서비스별 값** | P-A codebook → P-B frame 동결 |
| `UTILITY_ENTRY` archetype의 endpoint 정의 (`00 §3`에 대응 행 없음) | P-A |
| KWCAG criterion subset 및 `criterion_id` 목록 | `00 §15` · P-C |
| `A1` §7의 수집 파라미터 8종 (`MAX_ACTIVATIONS_PER_TASK` 등) | P-C → P-D 검증 |

## 7. 금지사항 재확인

이 문서의 어떤 조항도 다음을 허용하는 것으로 읽혀서는 안 된다.

| # | 금지 |
|---|---|
| 1 | **`UNDETERMINED`를 `PASS`로 흡수하지 않는다** (laundering). 금지 전이 X-1. 증거 부족(`evidence_gap = 1`)은 어떤 검토로도 충족 확인이 되지 않는다 |
| 2 | **결측을 0으로 치환하지 않는다** (`01 §11`). 규칙 N-1~N-5 · X-5 · X-7. `endpoint_reached = 0`의 `MPFED`는 **`NULL`**이며 `0`도 예산 상한 `8`도 아니다. `rows_expected` 결측 8행 `[실측]`, `value` 결측 7행 `[실측]` 도 0이 아니다 |
| 3 | **상태와 수치를 분리한다** (`01 §11`). §1.0의 6개 수준을 섞지 않는다. `app-only`를 `measurement_status`에 두지 않는다 |
| 4 | **AI 라벨을 human gold라 부르지 않는다** (`00 §9` · `04 Gold Label`). 규칙 R-3. `reviewer_agreement`가 높아도 정확도가 아니다 |
| 5 | **인증을 gold label로 쓰지 않는다** (`00 §4 Axis C`). `certified_current`는 외부 참조축이며 정답이 아니다 |
| 6 | **수집 실패를 접근성 FAIL로 세지 않는다** (`02 §13`). 규칙 M-1 · X-4 |
| 7 | **새 연구기준을 만들지 않는다.** 이 문서는 허용값·산식·귀속 컬럼만 부여했다. 임계값(`Depth >= 3 = 나쁨` 등)을 만들지 않는다 (`00 §7` · `00 §14`) |
| 7-a | **수집 파라미터를 해석 임계값으로 읽지 않는다.** `A1` §2.1의 `MAX_ACTIVATIONS_PER_TASK = 8`은 수집 예산이며 `8단계 넘으면 접근성이 나쁘다`가 아니다 (`A1` §0.4 · §2.3 · 규칙 E-3) |
| 7-b | **세 축(A/B/C)을 단일 종합점수로 합산하지 않는다.** Depth·episode·popup을 KWCAG `FAIL`로 전환하지 않는다 (`A1` §0.3 · 전파 규칙 T-5) |
| 7-c | **`NED = 0`을 "진입이 쉽다"로 점수화하지 않는다.** 관측 사실일 뿐이다 (규칙 D-4) |
| 8 | **원본 `state/*.parquet`를 rename·migration·수정하지 않는다** (`01` 서두 · `03 Phase 3`). 규칙 V-1 · V-4 · V-5 |
| 9 | **`research/refcohort/**`(Pilot)은 `READ_ONLY`.** 규칙 V-8 |
| 10 | **예산 소진을 이유로 강제분류하지 않는다** (`00 §9`). 규칙 A-1 · X-6. §2.3의 3번 분기가 정본 경로다 |

---

## 8. 실측 근거 요약

작성 시점에 `/home/sieg/projects-wsl/ProjectFinal/.venv/bin/python`으로
`state/*.parquet` 6종을 직접 읽어 확인한 값이다.

| 파일 | 행수 | 컬럼수 | 키 | 중복 |
|---|---|---|---|---|
| `panel_registry.parquet` | **17** | 26 | `panel_id` | 0 |
| `source_ranking_rows.parquet` | **261** | 16 | `source_row_id` | 0 |
| `service_master.parquet` | **81** | 24 | `service_id` | 0 |
| `entity_alias_map.parquet` | **82** | 8 | `alias_id` | 0 |
| `source_membership.parquet` | **142** | 7 | `(service_id, panel_id)` | 0 |
| `web_target_group.parquet` | **68** | 17 | `web_target_group_id` | 0 |

| 검사 | 결과 |
|---|---|
| `source_ranking_rows ⋈ entity_alias_map ON (entity_name_raw, domain, axis_type)` | 261 → **261행**, fan-out **0**, 미매칭 **0** |
| 유도된 distinct `(service_id, panel_id)` | **142** = `source_membership` 142, 집합 **동일**(차집합 양방향 0) |
| `source_membership.rank` == 유도 `min(rank)` | 불일치 **0** |
| `source_membership.n_metrics` == `panel_registry.n_metrics` | 불일치 **0** |
| `entity_alias_map.panel_ids` explode → `(service_id, panel_id)` | **142쌍**, `source_membership`과 집합 동일 |
| `service_master.web_eligibility_status` | `NOT_ASSESSED` **71** / `EXCLUDED_INDUSTRY_AXIS` **10** |
| `axis_type` × `web_eligibility_status` 교차 | `SERVICE_BRAND`→`NOT_ASSESSED` 71, `INDUSTRY_CATEGORY`→`EXCLUDED_INDUSTRY_AXIS` 10, 오프대각 **0** |
| `review_status` 유도 (§1.1) | `NOT_IN_REVIEW_QUEUE` **74** / `KEEP_SEPARATE` **6** / `MERGE` **1** / `PENDING_HUMAN_REVIEW` **0** (합 81) |
| `NOT_IN_REVIEW_QUEUE` 리터럴 in `web_target_group.member_review_decisions` | **64행** (기준선에 이미 존재하는 토큰) |
| `entity_alias_map.match_basis` | `EXACT` **81** / `REVIEWED` **1** |
| `service_name_canonical` 고유값 | **80** / 81행 (`쿠팡` 중복 1쌍) — 이름은 유일키 아님 |
| `canonical_service_key` 유일성 | **유일** (81/81) |
| `source_ranking_rows.value` 결측 | **7행** (전부 `fig07_t1` · `성장률` · `%`) |
| `panel_registry.rows_expected` 결측 | **8행** (`row_count_verification = VISUAL_COUNT_ONLY` 8행과 대응) |
| `panel_registry.n_metrics` 분포 | 1→8 / 2→5 / 3→3 / 4→1 (다중 metric 패널 **9개**) |
| `web_target_group.member_count` | 1→**65** / 2→**3** (합 68) |
| `service_master.web_target_group_id` | nonnull **71** / null **10**, distinct **68** |
| `web_target_group.web_target_url` · `url_evidence` | nonnull **0** (전량 결측) |
| `expected_url_relationship_confirmed_by_url = True` | **0건** (URL로 확인된 그룹 가설 없음) |
| `expected_url_relationship_is_hypothesis = True` | **3건** |
