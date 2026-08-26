# A2 — 어휘·스키마 바인딩 보충명세 v2.0

| 항목 | 값 |
|---|---|
| 문서 id | `A2_VOCABULARY_AND_SCHEMA_BINDING` |
| 지위 | `EXECUTION_AUTHORITY.md` 권위서열 **9위**. `00`~`05` · `PHASE_GATES.md`(7위) · `A1`(8위) **아래**의 보충명세 |
| 성격 | **보충명세**. 새 연구기준을 만들지 않는다. 이미 정의된 개념에 **허용값·산식·귀속 컬럼**만 부여한다 |
| 대상 결함 | `V2-C001` ssot F6 · F7 · F12 (P2 blocking 3건) |
| 어휘 관할 | `A1`이 도입한 신규 필드·표의 **허용값 도메인은 이 문서가 확정한다** (`A1` §0.3 — 두 문서가 어긋나면 A2의 어휘 정의가 우선) |
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
   | 8 | `docs/v2/A1_MEASUREMENT_OPERATIONALIZATION.md` | 측정 조작화 보충명세. **A1이 도입한 신규 필드·표의 값 도메인은 A2가 확정한다**(`A1` §0.3) |
   | **9** | **`docs/v2/A2_VOCABULARY_AND_SCHEMA_BINDING.md` (이 문서)** | 상태값 어휘·논리↔물리 스키마 대응 |
   | 10 | `docs/07_EVIDENCE_MANIFEST_CONTRACT.md` | evidence identity / manifest 계약. **v1 산물이나 현행 유효**. §4.1 evidence completeness의 근거 |

4. **A1과의 분업 — 관할 선언 (대칭 조항)** `[V2-C005 시정]`

   `A1`은 "어떻게 재는가"(절차·경계·신호)를, 이 문서는 "무슨 값을 쓰는가"(허용값·산식·귀속)를 맡는다.
   아래 절이 정의하는 **상태값의 컬럼 배치·허용값 도메인**은 이 문서가 정본이며, `A1`과 충돌하면
   **이 문서가 우선**한다.

   > 닫는 finding: `a1-0-3-jurisdiction-declaration-drifts-from-a2-and-collides-with-existing-section`
   > (ssot `V2-C004` P2 blocking + adversarial `V2-C004` ADV-C004-02, 두 감사가 독립 재현).
   > **이 표는 `A1 §0.3`의 대칭 조항과 정확히 같은 목록이다.** 한쪽만 갱신하면 그 자체가 drift다.

   | `A1` 절 | 이 문서의 정본 | 관할 대상 |
   |---|---|---|
   | §1.5 · §1.5 auth gate 교차참조 | A2 §1.5.1 · §1.5.1a | 신호 미관측 상태값 · gate 분기 |
   | §1.8 | A2 §1.5.3 · §1.5.4 · §1.9 | step 귀속 필드의 값 도메인 |
   | §2.2 | A2 §1.5.2 | `endpoint_status` vs `endpoint_status_detail` 배치 |
   | §3.2 · §3.3 · §3.4 | A2 §1.6 | dismiss control 필드군 |
   | §4.2 · §4.3 · §4.4 | A2 §1.12 | episode 필드군 |
   | §5.1 | A2 §1.13 | primary action candidate 필드군 |
   | §6.1 | A2 §4.1 · §6.3 | L0 evidence 슬롯 |

   **§1.8 행에 `§1.5.4`가 들어간 이유** `[V2-C005 시정]` — `A1 §1.8`이 요구한 6필드 중
   `fact_task_step.area_signal_detected` · `depth_segment` · `counts_toward_depth` **3필드의 값 도메인은
   이 문서 §1.5.4**에 있고, `fact_task_entry.area_signal_status`는 §1.5.3에,
   `dim_representative_task.region_definition` · `region_signal_type`은 §1.9에 있다.
   §1.5.3 · §1.9만 적으면 3필드가 정본 없이 남는다. **A1 §0.3도 같은 세 절을 적어야 한다.**

   이 문서가 A1의 표현을 다듬은 지점은 §1.5.2(하위 세분값 배치) 한 곳이며, A1의 의도는 그대로 보존된다.
   관할 선언의 A1 쪽 앵커는 **`A1 §0.3`**이다 — 옛 `A1 §0.2`를 가리키는 참조는 전부 갱신됐다.
5. 이 문서가 새 컬럼을 요구하는 것으로 읽혀서는 안 된다. §6에 열거한 미존재 표·컬럼은
   **이 문서가 신설한 것이 아니라 `01`/`02`/`A1`이 이미 요구했으나 아직 물리적으로 없는 것**이다.
   **예외는 정확히 둘이다** `[V2-C005 시정]` — 7항 예외 등재부가 **절차를 부여한** 항목이며,
   원본이 요구한 컬럼이 아니라 이 문서가 절차로서 요구하는 **기록 자리**다.
   둘 다 새 연구기준도 임계값도 아니다(§7 7항).

   | 예외 | 기록 자리 | 어디에 사는가 |
   |---|---|---|
   | EXC-3 — 재수집 사전선언 블록 (§1.11.2 규칙 RC-2) | `recollection_preregistration` | 기존 evidence run manifest(`07_EVIDENCE_MANIFEST_CONTRACT` · `A1 §6.2`) **안** |
   | EXC-4 — 재수집 원장 (§1.11.2 규칙 RC-6 · RC-7) `[V2-C005 시정]` | `recollection_ledger.jsonl` | evidence run **바깥**의 git 추적 append-only 파일. `state/*.parquet`가 **아니다**(규칙 V-4 · V-5 · **V-9**) |
6. 원본 docs pack(`00`~`05`)의 **바이트를 수정하지 않는다.** 명세 공백은 보충명세로만 메운다.
7. **원본 문면과 다른 배치를 채택할 때의 예외 선언** `[V2-C003 시정]`

   2항은 이 문서가 원본의 값·정의·범위를 **조용히** 바꾸는 것을 금지한다.
   원본의 *의도*를 보존하기 위해 배치를 달리해야 하는 경우에는 아래 표에 **예외로 등재**해야 하며,
   등재되지 않은 이탈은 그 자체로 이 문서의 결함이다 (`EXECUTION_AUTHORITY §2`).
   예외 등재는 원본 문면을 무효화하는 장치가 **아니다** — 원본이 요구한 사실이 **어느 컬럼에서 보존되는지**를
   밝히는 것이며, 보존되지 않으면 예외로 인정되지 않는다. 이 표에 없는 이탈은 시정 대상이다.

   | # | 원본 조항 | 원본 문면 | 이 문서의 배치 | 예외 근거 | 원본이 요구한 사실이 보존되는 곳 | 절 |
   |---|---|---|---|---|---|---|
   | **EXC-1** | `02 §13` | `app-only … 별도 measurement status로 기록` | **두 경로로 분리한다.** 관측 이전에 확정된 app-only는 `web_eligibility_status = EXCLUDED_APP_ONLY`, 수집 시점에 발견된 app-only는 `measurement_status = NOT_ELIGIBLE_AT_COLLECTION` | 웹이 없어 관측 행 자체가 생기지 않는 경우와, `ELIGIBLE_WEB`로 동결된 뒤 수집 시점에 반증된 경우는 **서로 다른 사건**이다. 하나의 컬럼에 합치면 규칙 S-1(한 사실 = 한 컬럼)이 깨지고, 나누기만 하면 두 번째 경로가 무주지가 된다 | `measurement_status`에 대응 값이 **실제로 존재한다**(§1.2). `02 §13`의 `별도 measurement status로 기록`은 문면 그대로 충족되며, 접근성 `FAIL`로도 `UNDETERMINED`로도 세지 않는다 (규칙 M-1 · X-4) | §1.2 · §1.3 · §1.4 · §1.11 T-11 · §4.1 |
   | **EXC-2** `[V2-C004 시정]` | `01 §11` | `로그인 전까지만 가능 = AUTH_GATE_REACHED` | **두 archetype에 한해 저장값을 달리한다.** `FINANCIAL_ACTION_ENTRY`(로그인 gate·인증 gate)와 `COMMUNICATION_ENTRY`(**로그인 gate만**)에서 그 gate가 관측되면 `endpoint_status = FUNCTION_ENDPOINT_REACHED` + `endpoint_status_detail = ENDPOINT_VIA_AUTH_GATE`로 기록한다. 나머지 5 archetype과 `COMMUNICATION_ENTRY`의 **본인인증 gate**는 `01 §11` 문면 그대로 `AUTH_GATE_REACHED`(개인정보 입력이 요구되면 `02 §7` `PERSONAL_DATA_REQUIRED`)다 | `00 §3` L1 표(권위 **1위**)가 그 두 행의 endpoint 정의 안에 gate를 넣었다. `00` > `01`이므로 충돌은 `00`을 따라 해소하며 그 해소는 이 문서의 몫이다(§0 1항·8항). 이탈은 **두 archetype**과 **`00 §3`이 그 행에 준 gate 종류**를 넘지 않으며, **그 종류가 확정된 경우로 다시 한 번 좁혀진다**(규칙 E-6 · E-6a · **E-6b** `[V2-C008 시정]`) | `endpoint_status_detail = ENDPOINT_VIA_AUTH_GATE`가 gate로 실현된 endpoint를 전부 식별하고, `auth_gate_before_endpoint`(규칙 E-9)와 규칙 E-8 합집합이 `00 §11`·`01 §10`의 `auth gate` 지표를 과소집계 없이 유지한다. 규칙 E-10이 두 endpoint 의미를 층화해 `MPFED` 통계에서 섞이지 않게 한다 | §1.5.1 · §1.5.1a · §1.5.2 · §4.2 |
   | **EXC-3** `[V2-C004 시정]` | `02 §12` | `재수집 → 새 evidence run` | **기록 방식은 그대로 두고 절차를 부여한다.** 재수집의 횟수 상한·중단규칙·사전선언·정본 run 선택규칙을 §1.11.2 규칙 RC-1~RC-5로 정한다. 원본이 허용한 기록을 금지하지 않는다 — 상한을 넘은 run도 append-only로 남으며, 다만 **정본 지표에 들어가지 않는다** | `02 §12`는 재수집을 **어떻게 기록하는가**만 규정하고 **몇 번·무엇을·어떤 순서로** 재수집하는가에 침묵한다. 침묵을 그대로 두면 `UNDETERMINED`의 유일 탈출구(§1.11.2)가 **원하는 결과가 나올 때까지 다시 재는 통로**가 되고, 그것은 `00 §14`가 금지한 결론 유도다. 절차 부여는 원본의 값·정의·범위를 바꾸지 않으므로 §0 2항과 충돌하지 않는다 | 모든 run이 `02 §12` 그대로 append-only로 보존된다. 어느 run이 정본이고 어느 run이 재수집분인지, 사전선언이 있었는지, 재수집 전후로 `decision coverage`가 얼마나 움직였는지가 `03 Phase 5` 보고(RC-5)에 전부 노출된다 | §1.11.2 · §1.8 · §4.1 · §4.2 |

   | **EXC-4** `[V2-C005 시정]` | `02 §11` · `02 §12` | `hash-based observation id 사용` · `재수집 → 새 evidence run` | **evidence identity와 append-only는 그대로 두고, 그 앞에 선행 앵커 층을 얹는다.** 재수집 시도는 시작 **이전에** git 추적 append-only 원장 `recollection_ledger.jsonl`에 등재·커밋·push되고, run manifest가 그 커밋 SHA를 참조한다(규칙 RC-6). **실행 1회마다 control 인가 1건이 필요하고 `evidence_run_id`가 그 인가에서 유도된다** `[V2-C006 시정]`. **인가 층은 재수집 run 만이 아니라 최초(E001 baseline) run 에도 적용된다** `[V2-C008 시정 · 2차]` — C-2 로 확대됐으므로 이 등재부의 이탈 범위도 최초 run 을 포함한다(ssot V2-C008: EXC-4 등재 범위 미확대). 시도·중단·폐기된 run 전건이 같은 원장에 남는다(규칙 RC-7) | `02 §11`의 evidence identity는 **run이 끝난 뒤**의 산출물만 앵커한다. `02 §12`의 append-only도 **남은 run**만 보존한다. 둘 다 "이 run을 왜, 무엇을 기대하고 시작했는가"와 "몇 번 시도해서 무엇을 버렸는가"를 담지 않으므로, EXC-3의 사전선언이 run 자신의 산출물 안에만 있으면 **결과를 본 뒤 소급 작성(backdating)** 이 가능하다. 원본은 그 자리를 비워두었을 뿐 금지하지 않았고, 앵커 층은 원본의 값·정의·범위를 바꾸지 않는다 | 원장은 evidence를 대체하지 않는다 — `02 §11`의 7종 identity와 `02 §12`의 run 보존은 문면 그대로다. 원장은 그 **앞**에 순서를 고정하고, 앵커 digest가 run manifest에 들어가 `07 §3` manifest 등록을 통해 evidence 해시 집합에 묶인다 | §1.11.2 규칙 RC-6 · RC-7 · §4.2 · §5.7 V-9 · §6.3 · §6.3.1 |

   | **EXC-5** `[V2-C009 시정]` | `00 §14` · `03 Phase 5` | `허용/금지 claim 목록` · `측정 품질 보고 항목` | **원본의 claim boundary 와 품질 보고 항목은 그대로 두고, 그 위에 잔여 위험 한계 절을 추가한다.** 아래 한계 문면을 `03 Phase 6` 역추적 대상 보고와 최종 산출물(논문·보고서 limitation 절)에 싣는다 — 규칙 **RC-8** | `00 §14`는 데이터에서 **도출되는** claim 의 경계를 정하고 `03 Phase 5`는 측정 품질 **지표**를 나열한다. 둘 다 "이 측정 절차가 배제하지 **못하는** 것" 을 담는 자리를 두지 않았다. 그런데 `rc-6-r1`(선별적 로컬 재실행)은 독립 감사가 **환원 불가능**으로 판정하고 조건부 수용한 잔여이며(adversarial `V2-C008` focused), **수용됐으나 서술에서 빠지면 정직한 등재가 은폐로 되돌아간다** — 그것이 감사가 수용 근거의 절반으로 삼은 조건 C-5 다. 두 원본이 프리즈이므로 이 등재부를 통해 보충명세에 싣는다 | 원본의 허용/금지 목록과 지표 정의는 문면 그대로다. 이 항은 **금지를 추가하지 않고** 서술 의무만 부과한다 — 잔여를 감추지 못하게 할 뿐 새 claim 을 허용하지도 기존 claim 을 좁히지도 않는다 | §1.11.2 규칙 RC-8 · RC-5 · §7 13항 |

   `V2-C002` ssot finding `app-only-reallocation-leaves-collection-time-discovery-unrepresented`가
   지적한 두 결손(**예외 미선언** · **수집 시점 발견 경로 부재**)을 이 항과 §1.2가 함께 닫는다.

   **EXC-2 · EXC-3은 `V2-C003` 두 감사가 연 결함을 닫는다** `[V2-C004 시정]`.
   EXC-2는 ssot finding `a2-1-5-1a-deviates-from-01-11-without-exc-registration`을 닫는다 —
   `01 §11`에서 이탈하면서 등재하지 않은 것이 이 문서 자신의 문면(7항 3문장)에 따른 결함이었다.
   EXC-3은 adversarial P1 `recollection-escape-path-unbounded-and-conclusion-prioritized`의
   remedy 5항(`02 §12`는 원본이므로 수정하지 않고 예외 등재 형식으로 절차를 부여한다)을 이행한다.

   **EXC-4는 그 P1이 `V2-C004`에서 재판정 OPEN된 이유를 닫는다** `[V2-C005 시정]`.
   EXC-3만으로는 사전선언이 **새 run 자신의 manifest 안**에만 살아 backdating을 막지 못했다
   (adversarial `V2-C004` §3.4가 실행으로 재현). EXC-4는 사전선언의 **순서 고정을 run 바깥으로**
   옮긴다 — 같은 예외 등재 형식이며 `02`의 바이트를 건드리지 않는다.
8. **`00`과의 충돌은 언제나 이 문서의 결함이다** `[V2-C003 시정]`

   1항의 귀결이다. 이 문서가 `00`보다 좁거나 넓은 규칙을 적었다면 예외 등재로 정당화되지 않으며,
   **이 문서를 고쳐야 한다.** §1.5.1a(auth gate ↔ `00 §3` L1 표)가 그렇게 시정된 사례다.

### 이 문서가 닫는 결함과 위치

| finding id | 심각도 | 닫는 절 |
|---|---|---|
| `measurement-status-vocabulary-unreconciled` (F6) | P2 blocking | §1.2 · §1.3 · §1.11 · **§1.14** |
| `undefined-column-vocabularies` (F7) | P2 blocking | §1 전체 · §2 · §3 · §4 |
| (A1 신규 필드·표의 값 도메인 확정) | — | §1.5 · §1.6 · §1.9 · §1.12 · §1.13 |
| `state-table-mapping-declared-without-correspondence` (F12) | P2 blocking | §5 · §6 |

**`V2-C002` 이후 추가로 닫는 결함** `[V2-C003 시정]`

| finding id | 출처 · 심각도 | 닫는 절 |
|---|---|---|
| `a2-undetermined-to-pass-transition-underspecified-and-narrowed` | adversarial `V2-C002` P1 **blocking** | **§1.11**(T-3 · T-7~T-10 · §1.11.1 · §1.11.2 · X-1 · X-9~X-11) · §1.7 · §1.8 · §2.3 · §7 1항 |
| `app-only-reallocation-leaves-collection-time-discovery-unrepresented` | ssot `V2-C002` P2 **blocking**(`E001_V2`) | **§0 7항 EXC-1** · §1.2 · §1.3 · §1.4 · §1.11 T-11 · X-12 · §4.1 · §7 3항 |
| `00 §3 ↔ A2 §1.5.1 auth gate endpoint 충돌` (오케스트레이터 등재, P1 취급) | `V2-C003` | **§1.5.1a**(규칙 E-5~E-10) · §1.5.1 · §1.5.2 · §7 11항 |

**`V2-C003` 두 감사가 연 결함 — 이 판(`V2-C004`)에서 닫는다** `[V2-C004 시정]`

| finding id | 출처 · 심각도 | 닫는 절 |
|---|---|---|
| `recollection-escape-path-unbounded-and-conclusion-prioritized` | adversarial `V2-C003` **P1 blocking** | **§1.11.2**(규칙 RC-1~RC-5) · §0 7항 EXC-3 · §1.8(`impact_level` 재정의) · §1.11 X-14 · §4.1 주의 4 · §4.2 · §6.3 · §7 13항 |
| `t4-and-2-3-step-4-contradict-t6-for-verdict-state-na` | adversarial `V2-C003` P2 (`V2_SSOT_FROZEN`) | **§1.11 T-4 · T-6** · §2.3 4번 분기 · X-13 · X-15 · §7 15항 |
| `a2-1-5-1a-widens-00-3-community-gate-clause-to-any-auth-gate` | ssot `V2-C003` P2 (`V2_SSOT_FROZEN`) | **§1.5.1a 규칙 E-6a** · §1.5.1 `AUTH_GATE_REACHED` 행 · §1.5.1a 규범표 · §7 11항 |
| `a2-1-5-1a-deviates-from-01-11-without-exc-registration` | ssot `V2-C003` P2 (`V2_SSOT_FROZEN`) | **§0 7항 EXC-2** · §1.5.1a 규범표 `근거` 열 |
| `rule-e-8-omits-01-6-auth-gate-before-endpoint-column` | ssot `V2-C003` P2 (`E001_V2`) | **§1.5.1a 규칙 E-9** · 규칙 E-8 합집합 · §6.3 |
| `gate-endpoint-archetypes-mix-two-endpoint-semantics-without-stratification` | adversarial `V2-C003` P2 (`E001_V2`) | **§1.5.1a 규칙 E-10** · §1.5.2 규칙 E-4 · §6.3 · §7 14항 |
| `new-v2-c003-rules-absent-from-failure-injection-set` | adversarial `V2-C003` P2 (`E001_V2`) | **§6.3 실패주입 대응표** · §1.11 실패주입 V-d~V-g · X-13~X-15 |

**`V2-C004` adversarial 감사가 재판정 OPEN한 결함 — 이 판(`V2-C005`)에서 닫는다** `[V2-C005 시정]`

| finding id | 출처 · 심각도 | 재판정 사유 | 닫는 절 |
|---|---|---|---|
| `recollection-escape-path-unbounded-and-conclusion-prioritized` | adversarial `V2-C004` **P1 blocking** (`V2-C003`에서 승계, 재판정 **OPEN**) | RC-2 사전선언이 **새 run 자신의 manifest 안에만** 존재해 결과를 본 뒤 소급 작성할 수 있다. 시도·폐기된 run을 열거할 장치도 없다 | **§1.11.2 규칙 RC-6 · RC-7** · §0 5항 · §0 7항 **EXC-4** · §1.11 X-14 ⑤~⑦ · §4.2 · §5.7 **V-9** · §6.3 · §6.3.1 I-30~I-41 · §7 13항 |
| `a1-0-3-jurisdiction-declaration-drifts-from-a2-and-collides-with-existing-section` | ssot `V2-C004` **P2 blocking** + adversarial `V2-C004` **ADV-C004-02** (두 감사 독립 재현) | A1 관할표와 A2 §0 목록이 서로 달랐고, A2가 옛 `A1 §0.2`를 가리키는 stale backlink가 4곳 남아 있었다. 스키마 허용값의 최종 권위를 고르는 routing 결함이다 | **§0 4항 대칭 관할표**(A1 §0.3과 글자 그대로 동일) · backlink 4곳 갱신 · A1 절 번호 이동 반영 2곳 |

**`V2-C005` 두 감사가 연 결함 — 이 판(`V2-C006`)에서 닫는다** `[V2-C006 시정]`

| finding id | 출처 · 심각도 | 무엇이 문제였나 | 닫는 절 |
|---|---|---|---|
| `recollection-escape-path-unbounded-and-conclusion-prioritized` | adversarial `V2-C005` **P1 blocking** (세 사이클 연속 OPEN) | 앵커 1건이 인가하는 **실행 횟수를 묶는 것이 없어**, 앵커된 `planned_evidence_run_id`로 K회 로컬 실행 후 1회만 커밋하는 경로가 A-1~A-6·RC-7을 전부 통과했다. A-3·A-5의 부재 증명은 구조적으로 항상 참이었다 | **§1.11.2 규칙 RC-6** — `EXECUTION` 레코드 · 실행 인가 · 검사 **A-7 · A-8** 신설, A-3 · A-5 재정의, **잔여 위험 R-1~R-4 명시** · §1.11 X-14 ⑧ · §5.7 · §6.3.1 **I-38~I-41** |
| `rc-6-a-6-circular-derivation` | ssot `V2-C005` **F3 blocking** | `record_sha256`의 입력집합이 `planned_evidence_run_id`를 포함하는데 A-6은 그 필드가 `record_sha256`에서 유도되기를 요구했다 — 해시 고정점 없이 충족 불가이고 유도식도 없었다 | **§1.11.2 유도식 `f`** — `planned_evidence_run_id` **필드 삭제**, `evidence_run_id`를 `(ledger_record_sha256, countersign_commit_sha, execution_index)`에서 유도, 검사 **A-6 재작성** |
| `hiding-gives-no-benefit` 단언 (부수) | adversarial `V2-C005` ADV-C005-P1-01 §4 | 닫힘 논거표의 `은닉은 정본 선택에 아무 이득을 주지 못한다`가 **동일 앵커 재실행에 대해 거짓**이었다 | **§1.11.2 닫힘 논거표** — 단언 **철회**, 세 행으로 분해(인가받지 않은 id = 닫힘 / 인가받고 숨김 = 닫힘 / 동일 인가 재실행 = **닫히지 않음**) |

**`V2-C007` LANE C가 연 결함 — 이 판(`V2-C008`)에서 닫는다** `[V2-C008 시정]`

| finding id | 출처 · 심각도 | 무엇이 문제였나 | 닫는 절 |
|---|---|---|---|
| `e-6a-accepts-misclassified-gate-kind-and-silently-flips-endpoint` | LANE C P-C fixture engineering (`agent/landing-pc-fixture` @ `0c36c95`) **P2 `E001_V2-blocking`** | 규칙 E-6a가 gate 종류를 **입력으로 받아** 오분류된 본인인증 gate를 로그인으로 승인했다. 그 순간 `endpoint_reached`가 `0→1`, `MPFED`가 `NULL→정수`로 조용히 뒤집힌다. **규칙만으로는 탐지 불가**다 — 분류 결과를 입력으로 받기 때문이다 | **§1.5.1a 규칙 E-6b**(컬럼 `auth_gate_kind` 외 3종 · 비대칭 fail-closed 승격 조건 · 근거 교차검증 · 잔여 **GK-1~GK-3**) · §1.5.1 `AUTH_GATE_REACHED` 행 · §1.5.1a 규범표 · 규칙 **E-8** · **E-9** · **E-10** 3항 · §1.14 규칙 N-1 주 · §6.3 · §6.3.1 **I-42~I-50** · §6.4 · §7 11항 |
| `eligibility-basis-fields-narrower-than-06-still-carried` | v1 승계부채 (ssot `C012` 등재, `PHASE_GATES` §2 부채 승계로 main 승격 차단) | v1 `06` §2-2가 요구한 판정 근거 5필드 중 **4필드가 이 문서에 없었다** — `eligibility_basis` · `eligibility_reviewer` · `eligibility_confidence`는 `docs/v2/` 전체에서 0회, `needs_human_review`는 measurement entity 층에만 바인딩돼 적격성 층과 **한 컬럼으로 뭉개져** 있었다. 그 결과 LANE B shadow가 필드를 스스로 만들어 썼고 같은 사실이 세 갈래 이름·값 도메인으로 갈렸다 `[실측]` | **§1.3.1**(필드 7종 값 도메인 · 규칙 **EB-1~EB-4**) · §5.5 대응표 8행 추가 · §6.2 산출 목록 3행 추가 |
| `merge-decision-merges-nothing-no-alias-assert` | v1 승계부채 (adversarial `C011`/`C012` 계열) | `MERGE` 판정이 **데이터에 흔적을 남겼는지** 확인하는 코드가 없었다. 원장에 `MERGE`라 적기만 하면 별칭을 하나도 흡수하지 않은 entity도 통과했다 | **§5.5 `[V2-C008 시정]` 실측 블록**(층 분리 + 그룹 층 `MERGE` 0건 실측) · 코드: `review_queue.assert_merge_decisions_absorb_aliases` (M1~M3) |

| `rc-6-r1` 재분류 조건 **C-2** — `최초 run은 앵커를 요구하지 않는다 — 선택할 대상이 없기 때문이다` 단언 | adversarial **`V2-C008`** focused adjudication `[V2-C008 시정 · rc-6-r1 C-2 보강]` (`audit/landing-adversarial` @ `fed3e70`, 이 판에서 열려 이 판에서 닫는다), `rc-6-r1`의 `ACCEPTED_BOUNDED_RESIDUAL_RISK` 재분류 **조건부 승인** 6건 중 이 문서 소관 1건 | 뒷문장이 R-1 위협모델 아래에서 **거짓**이었다. 최초 run도 커밋되지 않은 로컬 run 사이의 선택에 열려 있고, 앵커가 없어 A-1~A-8이 전혀 적용되지 않았다. **R-1 수용이 기대는 최상위 탐지층(RC-5 병기)의 기준선이 바로 그 최초 run**이므로 실제보다 작은 잔여를 인증하게 된다. `V2-C005`가 철회한 `은닉은 이득을 주지 못한다`와 같은 범주 오류 | **§1.11.2 규칙 RC-6** — 단언 **철회**, 최초 run에 **실행 인가 층 적용**(선택지 (a)) · 적용범위표 · (b)의 비용 기록 · **잔여 R-1을 위험 *부류*(선별적 로컬 재실행)로 재정의** · 닫힘 논거표 · RC-5 병기 행 한계 · RC-7 조밀성(`attempt_index = 0` 예약) · §6.3 · §6.3.1 **I-51~I-53** · §7 13항 |

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
| Observation | 관측 **시도의 결과** | `measurement_status` · `measurement_status_detail` | §1.2 |
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
| `NOT_ELIGIBLE_AT_COLLECTION` `[V2-C003 시정]` | **적격성 반증** (성공도 실패도 아니다) | `web_eligibility_status = ELIGIBLE_WEB`로 동결된 타겟에 실제로 접속했으나, `00 §3` L0 범위의 **공개 모바일웹 랜딩이 존재하지 않음이 관측**됐다 (앱 설치 인터스티셜·스토어 리다이렉트만 존재하거나, 로그인 이전 공개 랜딩이 없다) | 02 §13 `app-only` · §0 7항 **EXC-1** |

**상호배타.** 7값은 상호배타다. 한 관측 회차는 정확히 한 값을 가진다.
두 실패가 동시에 성립하면 **먼저 발생한 것**을 기록하고 나머지는 `probe_path`의 진단 로그에 남긴다.

**계열 경계 (`[V2-C003 시정]`).** `MEASUREMENT_FAILED` 계열은 `measurement_status LIKE 'FAILED_%'` 다.
`NOT_ELIGIBLE_AT_COLLECTION`은 **의도적으로 이 패턴에 걸리지 않는다.**
수집 시도가 실패한 것이 아니라 **P-B의 적격성 판정이 관측으로 반증된 것**이기 때문이다.
셋을 한 계열로 합치면 `02 §13`이 보호하려던 구분이 사라지고 §4.1 evidence completeness가 오염된다.

| 계열 | 값 | 무엇을 뜻하는가 | criterion 행 | §4.1 분모 |
|---|---|---|---|---|
| 성공 | `MEASURED` | evidence가 산출됐다 | 생성 | 포함 (분자 후보) |
| `MEASUREMENT_FAILED` (`FAILED_%`) | `FAILED_*` 5값 | 관측 시도가 실패했다 | **생성 안 함** (M-1) | 포함, 분자 제외 |
| 적격성 반증 | `NOT_ELIGIBLE_AT_COLLECTION` | 잴 대상이 애초에 범위 밖이었다 | **생성 안 함** (M-1) | **분자·분모 모두 제외** (§4.1 주의 3) |

#### `app-only`의 두 경로 — `02 §13` 대응 `[V2-C003 시정]`

`02 §13`은 `app-only`를 `별도 measurement status로 기록`하라고 지시했다.
`V2-C002` ssot 감사가 지적한 대로, 이 문서의 이전 판은 그 지시를 뒤집으면서 §0 2항의 **예외를 선언하지 않았고**,
그 결과 **수집 시점에 발견된 app-only**가 들어갈 컬럼이 어디에도 없었다.
`app-only`는 하나의 사실이 아니라 **발견 시점이 다른 두 사실**이므로 다음과 같이 나눠 기록한다.

| 발견 시점 | 사실 | 수준 | 기록 컬럼 | 관측 행 |
|---|---|---|---|---|
| **P-B 적격성 판정 시점** (URL 증거 검토 중) | 앱 전용이라 대응하는 공식 모바일웹이 없다 | Frame | `web_eligibility_status = EXCLUDED_APP_ONLY` (§1.3) · `web_target_status = EXCLUDED` (§1.4) | 생성되지 않는다 |
| **수집 시점** (`ELIGIBLE_WEB` 동결 후 접속) | 동결된 URL이 L0 범위의 공개 웹 랜딩을 제공하지 않는다 | Observation | `measurement_status = NOT_ELIGIBLE_AT_COLLECTION` + `measurement_status_detail` | **생성된다** (접속을 시도했으므로) |

두 번째 경로에서 관측 행이 생기는 것은 첫 번째 경로의 논리("웹이 없으면 행 자체가 없다")와 모순이 아니다.
첫 번째는 **접속하지 않았으므로** 행이 없고, 두 번째는 **접속했으므로** 행이 있다.
`02 §13`이 `app-only`를 `ACCESS_BLOCKED`·`browser crash`·`page timeout` 사이에 나열한 것은
원본이 바로 이 **수집 시점 발견**을 상정했다는 정황이며, 이 값이 그 자리를 채운다.

`measurement_status_detail` — `NOT_ELIGIBLE_AT_COLLECTION` 일 때에만 non-null인 동반 컬럼.

| 값 | 뜻 | 대응 `web_eligibility_status` |
|---|---|---|
| `APP_ONLY_AT_COLLECTION` | 앱 설치 유도·스토어 리다이렉트만 있고 웹 콘텐츠가 없다 | `EXCLUDED_APP_ONLY` |
| `NO_PUBLIC_WEB_LANDING_AT_COLLECTION` | 웹은 응답하나 로그인 이전 공개 랜딩이 없다 | `EXCLUDED_NO_PUBLIC_WEB_LANDING` |

**상호배타.** 2값은 상호배타이며, `measurement_status ≠ NOT_ELIGIBLE_AT_COLLECTION` 이면 `NULL`이다.

**규칙 M-1.** `measurement_status ≠ 'MEASURED'` 인 관측은 `fact_criterion_result` 행을 **생성하지 않는다.**
수집 실패를 `FAIL`로도 `UNDETERMINED`로도 세지 않는다 (`02 §13`).
결측은 **행의 부재**로 표현하고 0이나 대체값으로 채우지 않는다 (`01 §11`).

**규칙 M-2.** 시도하지 않은 관측은 이 어휘로 표현하지 않는다. 행이 없는 것이 정답이다.
"적격인데 관측되지 않음"은 §4의 **분모**에서 잡는다 (§4.1 · §4.2).

**규칙 M-3 (파이프라인은 실패하지 않는다) `[V2-C003 시정]`.**
`ELIGIBLE_WEB`로 동결된 타겟이 수집 시점에 공개 웹 랜딩을 제공하지 않는 것은 **정상 처리 가능한 사건**이다.
파이프라인은 이 관측에서 예외를 던지거나 행을 버리지 않고 `NOT_ELIGIBLE_AT_COLLECTION`을 기록하고 진행한다.
규칙 S-3(닫힌 집합 위반 시 실패)은 **표에 없는 값이 나올 때**의 규칙이지, 이 값이 나올 때의 규칙이 아니다.

**규칙 M-4 (증거 요구) `[V2-C003 시정]`.**
`NOT_ELIGIBLE_AT_COLLECTION`은 **양의 관측**이므로 증거 없이 기록할 수 없다.
그 시점에 산출 가능한 evidence(최소한 `screenshot_initial_path` · `dom_path` · 최종 URL)를 남겨야 하며,
남기지 못했으면 그것은 이 값이 아니라 `FAILED_EVIDENCE_INCOMPLETE`다.
증거가 있어야 P-B 적격성 판정의 반증이 제3자에게 재검증 가능하다 (`02 §12` 재판정 전제).

**규칙 M-5 (오용 금지) `[V2-C003 시정]`.**
수집이 어려운 타겟을 표본에서 조용히 빼기 위해 이 값을 쓰지 않는다.
`HTTP 401/403/429`·차단 인터스티셜은 `FAILED_ACCESS_BLOCKED`이고, 응답 지연은 `FAILED_PAGE_TIMEOUT`이며,
그 어느 것도 `NOT_ELIGIBLE_AT_COLLECTION`이 아니다 (금지 전이 X-12).
이 값의 발생 건수는 `03 Phase 5` 측정품질 보고에 **반드시** 노출된다 (§4.1).

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

**`EXCLUDED_APP_ONLY`가 F6을 닫는다.** `02 §13`의 `app-only` 중 **관측 이전에 확정된 것**이 여기로 귀속된다.

**수집 시점에 발견된 app-only는 여기에 직접 쓰지 않는다** `[V2-C003 시정]`.
`ELIGIBLE_WEB`로 동결된 뒤 수집에서 반증된 경우는 `measurement_status = NOT_ELIGIBLE_AT_COLLECTION`(§1.2)에
먼저 기록되고, Frame 수준 반영은 §1.4의 supersede 경로로만 이뤄진다 (전파 규칙 **T-11**).
관측 행이 Frame 컬럼을 in-place로 고쳐 쓰는 것은 규칙 S-2 위반이며, 동결된 값이 조용히 바뀌면
`00 §15 final web target frozen`의 의미가 사라진다.

| 수집 관측 | `measurement_status_detail` | supersede 후행(後行)의 `web_eligibility_status` |
|---|---|---|
| 앱 설치 유도·스토어 리다이렉트만 존재 | `APP_ONLY_AT_COLLECTION` | `EXCLUDED_APP_ONLY` |
| 웹은 응답하나 로그인 이전 공개 랜딩 없음 | `NO_PUBLIC_WEB_LANDING_AT_COLLECTION` | `EXCLUDED_NO_PUBLIC_WEB_LANDING` |

**규칙 W-1 (Frame 값은 관측이 아니라 재판정으로 바뀐다) `[V2-C003 시정]`.**
`web_eligibility_status`의 값이 바뀌는 유일한 경로는 (a) P-B 적격성 판정, (b) §1.4 supersede로 생성되는
**새 행**이다. 두 경로 모두 근거 증거를 요구하며, 기존 행의 값을 덮어쓰지 않는다 (`02 §12` append-only).

**grain 주의.** `01 §3`은 이 컬럼을 `dim_web_target`(web target 수준)에 두지만
물리적으로는 `service_master.web_eligibility_status`(measurement entity 수준, 81행)에 있다.
현재의 81건 판정은 **entity 수준 판정**이며, web target 수준으로 옮길 때 1:1이 보장되지 않는다 (§5.4).

---

### 1.3.1 적격성 판정 **근거** 필드 — v1 `06` §2-2 최소 동등 보장 `[V2-C008 시정]`

> 구체화 대상: v1 `06_ELIGIBILITY_AND_JOIN_RULES.md` §2-2 (부채 승계, `PHASE_GATES` §2)
> 닫는 finding: `eligibility-basis-fields-narrower-than-06-still-carried`

§1.3은 `web_eligibility_status`의 **허용값**만 확정한다. 그 값을 **무엇을 보고 정했는지**를
담는 자리는 이 문서 어디에도 없었다. v1 `06` §2-2는 그것을 다섯 필드로 요구했고,
v2로 넘어오면서 그중 하나(`web_eligibility_status`)만 살아남았다.

**실측 대조** — v1 `06` §2-2 요구 5필드 · LANE B shadow 산출물(`shadow/lane_b/state/web_eligibility_shadow.csv`,
81행 `[실측]`) · 이 문서의 선언 상태.

| v1 `06` §2-2 요구 필드 | LANE B가 실제로 기록한 것 | 이 문서(개정 전) | 물리 `service_master` |
|---|---|---|---|
| `web_eligibility_status` | `web_eligibility_status` (v2 6값) | §1.3에 선언 | 있음 |
| `eligibility_basis` | `eligibility_basis` — **81/81 비어 있지 않음** `[실측]` | **없음** (`docs/v2/` 전체 0회) | `web_eligibility_basis` (이름이 다르고 A2가 바인딩하지 않았다) |
| `eligibility_reviewer` | `eligibility_reviewer` — distinct 1 `[실측]` | **없음** | **없음** |
| `eligibility_confidence` | `url_confidence` / `observation_confidence` (HIGH 59 · MEDIUM 1 · LOW 11 · 결측 10) `[실측]` | **없음** | **없음** |
| `needs_human_review` (적격성 층) | `needs_human_review` — True 34 / False 47 `[실측]` | 이름은 있으나 **측정 entity review 층에만** 바인딩(§1.1 · §5.3) | 있으나 그것은 review 층 값이다 |

즉 5필드 중 **4필드가 이 문서의 스키마에 없다.** 판정 근거를 기록할 자리가 없는 상태에서
LANE B는 필드를 스스로 만들어 썼고, 그 결과 같은 사실이 `eligibility_confidence`(v1) ·
`url_confidence`(LANE B shadow) · `eligibility_confidence: float`(claude-b 구현)라는
서로 다른 이름·서로 다른 값 도메인으로 세 갈래로 갈렸다.

#### 필드 정의 — 값 도메인

이 표가 정본이다. **새 임계값을 만들지 않는다** — 판정을 바꾸지 않고, 이미 내려진 판정이
무엇에 근거했는지를 기록할 뿐이다. LANE B의 71/71 판정을 다시 하지 않는다.

| 컬럼 | 표 | 값 도메인 | 규칙 |
|---|---|---|---|
| `eligibility_basis` | `dim_web_target` | 자유서술 문자열, **NOT NULL** | 실제로 확인한 URL · 페이지 제목 · 리다이렉트 결과를 담는다. `web_eligibility_status ≠ NOT_ASSESSED`인 모든 행에서 비어 있을 수 없다 (규칙 **EB-1**) |
| `eligibility_reviewer` | `dim_web_target` | 자유서술 문자열, **NOT NULL** | 자동 규칙명 또는 사람. 규칙명은 `eligibility_rule`과 함께 적는다 |
| `eligibility_rule` | `dim_web_target` | 닫힌 집합. P-B `E000_V2`에서 규칙 id 목록을 동결한다 | 자동 판정의 규칙 id. 사람 판정이면 `NULL` |
| `eligibility_confidence` | `dim_web_target` | `HIGH` \| `MEDIUM` \| `LOW` (**v1 `06` §2-2 그대로**) | 실수 점수로 바꾸지 않는다. 세 단계는 v1이 정한 것이고 이 문서는 값 도메인을 **좁히지도 넓히지도** 않는다 |
| `eligibility_reviewed_at` | `dim_web_target` | ISO 8601 날짜 | 판정 시점 |
| `eligibility_needs_review` | `dim_web_target` | `bool` | **적격성 층**의 미결 표시. §1.1의 `review_status`(measurement entity 층)와 **다른 컬럼이다** |
| `url_evidence` | `dim_web_target` | 자유서술 문자열 | 이미 §5.5에 `(c) ABSENT → P-B`로 등재돼 있다. 여기서 다시 만들지 않는다 |

**규칙 EB-1 (근거 없는 상태 부여 금지).** `web_eligibility_status`가 `NOT_ASSESSED`가 아닌 행은
`eligibility_basis` · `eligibility_reviewer` · `eligibility_confidence` · `eligibility_reviewed_at`을
**전부** 가져야 한다. 하나라도 비면 그 판정은 무효이며 `NOT_ASSESSED`로 되돌린다.
v1 `06` §2-2의 "근거 없는 상태 부여를 금지한다"가 이 규칙이다.

**규칙 EB-2 (층 분리).** `eligibility_needs_review`와 §1.1의 `review_status`는 **다른 층의 다른 질문**이다.

| 층 | 질문 | 컬럼 |
|---|---|---|
| measurement entity | 이 두 원문 표기가 같은 것을 잰 것인가 | §1.1 `review_status` · `service_master.needs_human_review` |
| web target | 이 대상의 공식 랜딩 URL이 확정되는가 | `eligibility_needs_review` |

한 컬럼으로 뭉개면 "표기 모호성이 해소됐다"가 "URL이 확정됐다"로 읽힌다. 현재 물리
`service_master.needs_human_review`는 **전자**이며(81행 전부 `False` `[실측]`),
후자를 담을 컬럼은 아직 없다. LANE B가 shadow에서 34건을 `True`로 기록한 것은 **후자**다 —
두 값이 같은 이름 아래 놓이면 34가 0으로 보인다.

**규칙 EB-3 (v1 `06` §3-1 URL 근거 사슬).** `06` §3-1은 URL 층에도 근거 5필드
(`official_landing_url` · `url_type` · `url_discovery_method` · `url_evidence` · `url_reviewer` ·
`url_confidence`)를 요구했다. 이 문서 §5.5는 그중 `official_landing_url` · `url_evidence` ·
`registered_domain` · `url_confidence`만 `(c) ABSENT`로 등재하고 있었다.
`url_type` · `url_discovery_method` · `url_reviewer`도 §6.2에 등재한다.
`url_type`의 값 도메인은 **신설하지 않는다** — `06` §3-1의
`WEB_SERVICE_LANDING` \| `OFFICIAL_PRODUCT_PAGE` \| `APP_ONLY` \| `UNRESOLVED` 네 값을 그대로 승계하고,
`web_eligibility_status`(§1.3 6값)와의 대응은 P-B `E000_V2`에서 실측으로 고정한다.

**규칙 EB-4 (v1 `06` §3-3 리다이렉트 보존).** `06` §3-3은 `target_url` · `final_url` ·
`redirect_chain` 셋을 **전부** 보존하라고 요구한다. §5.5는 `final_url`만 등재하고 있었고,
LANE B shadow는 `redirect_hops`(횟수)와 `final_registered_domain`만 남겨 **사슬 자체를 버렸다** `[실측]`.
횟수는 사슬이 아니다 — 중간 홉을 버리면 "어디를 거쳐 갔는가"를 제3자가 재검증할 수 없다.
`redirect_chain`을 §6.2에 등재한다. 등록도메인 비교는 `06` §3-3대로 **Public Suffix List 파서**로 한다.

**이 절이 하지 않는 것.**

- LANE B의 71/71 적격성 판정을 재판정하지 않는다. 이 절은 **스키마 수준의 최소 동등 보장**이며,
  그 판정들이 이 필드들을 채우는지는 P-B 산출 시점에 규칙 EB-1이 검사한다.
- 새 임계값·새 판정 기준을 만들지 않는다. `eligibility_confidence`의 3값은 v1 `06` §2-2의 것이고,
  `url_type`의 4값은 v1 `06` §3-1의 것이다. 이 문서는 그것을 **좁힌 적이 있다는 사실**을 시정할 뿐이다.
- 물리 컬럼을 지금 만들지 않는다. 위 컬럼들은 §6.2의 P-B 산출 목록에 등재되며, 그 자리에서 생긴다.

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
| `SUPERSEDED` | 더 정확한 **URL 증거 또는 수집 증거**로 대체됐다. 이전 행은 남긴다 (append-only, `02 §12`) |

**상호배타.** 5값은 상호배타이며 `DRAFT → PENDING_URL_REVIEW → {FROZEN, EXCLUDED}` 단방향이다.
`FROZEN`에서 벗어나는 유일한 경로는 `SUPERSEDED`이며, 이는 새 행을 만든다.

#### 1.4.1 수집 시점 반증에 의한 supersede `[V2-C003 시정]`

> 닫는 finding: `app-only-reallocation-leaves-collection-time-discovery-unrepresented` (ssot `V2-C002`)

`SUPERSEDED`의 사유는 "더 정확한 URL을 찾았다"만이 아니다.
**"동결된 그 URL이 `00 §3` L0 범위의 대상이 아님을 수집이 보여줬다"**도 증거에 기반한 대체다.
이 경로가 없으면 `FROZEN` 타겟이 수집 시점에 반증됐을 때 기록할 자리가 없다(감사 지적).

| 단계 | 대상 행 | 값 |
|---|---|---|
| 1 | 관측 | `fact_landing_observation.measurement_status = NOT_ELIGIBLE_AT_COLLECTION` + `measurement_status_detail` (§1.2) |
| 2 | 기존 `dim_web_target` 행 (`FROZEN`) | `web_target_status = SUPERSEDED`. **값을 지우거나 덮어쓰지 않는다** |
| 3 | 새 `dim_web_target` 행 | `web_target_status = EXCLUDED` · `web_eligibility_status = EXCLUDED_APP_ONLY` 또는 `EXCLUDED_NO_PUBLIC_WEB_LANDING` (§1.3 대응표) · `superseded_from_web_target_id` = 2단계 행 · 근거로 1단계 `observation_id` |

**단방향 제약과의 관계.** `DRAFT → PENDING_URL_REVIEW → {FROZEN, EXCLUDED}` 단방향 제약은
**한 행의 생애 안에서** 성립하는 제약이다. supersede는 행을 바꾸는 것이 아니라 **새 행을 만드는** 것이므로,
후행이 `EXCLUDED`에서 시작하는 것은 이 제약을 위반하지 않는다. 후행은 이미 증거가 갖춰진 상태로 태어난다.

**규칙 W-2 (배제 방향으로만).** 이 경로는 **타겟을 범위 밖으로 내보내는 방향으로만** 쓸 수 있다.
수집이 잘 안 된다는 이유로 URL을 다른 URL로 바꾸는 데 쓸 수 없으며, 그것은 P-B로 되돌아가는 일이다.
동결 이후의 URL 교체는 `00 §15`가 금지한다.

**규칙 W-3 (반드시 보고).** 이 경로가 한 번이라도 발화하면 P-B 적격성 판정이 틀렸다는 뜻이므로,
`03 Phase 5` 측정품질 보고에 `eligibility_reversal_rate`(§4.1)로 **반드시** 노출한다.
조용히 표본에서 빠지는 타겟이 있어서는 안 된다.

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
| `AUTH_GATE_REACHED` | 로그인/인증 gate가 나타나 `00 §3 절대 제외`에 걸렸다. **단 `00 §3` L1 표가 그 archetype의 endpoint 정의 안에 넣은 종류의 gate에서는 이 값을 쓰지 않는다** — `FINANCIAL_ACTION_ENTRY`의 로그인 gate·인증 gate, `COMMUNICATION_ENTRY`의 **로그인 gate**가 그것이다. `COMMUNICATION_ENTRY`의 **본인인증 gate**는 `00 §3` 커뮤니티 행이 endpoint로 주지 않았으므로 이 값을 그대로 쓴다(개인정보 입력이 요구되면 `PERSONAL_DATA_REQUIRED`) (§1.5.1a 규칙 E-6a) `[V2-C004 시정]`. **gate 종류를 확정하지 못한 gate(`auth_gate_kind = UNDETERMINED`)도 archetype을 가리지 않고 이 값이다** — 승격은 확정된 종류에만 열린다 (§1.5.1a 규칙 E-6b) `[V2-C008 시정]` | 0 | `NULL` |
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

`endpoint_reached`와 `endpoint_status = FUNCTION_ENDPOINT_REACHED`의 동치는 §1.5.1a의 archetype 분기
이후에도 그대로 유지된다 — 분기는 **어느 상태값으로 저장하는가**를 가를 뿐 동치식을 건드리지 않는다.

#### 1.5.1a auth gate가 endpoint인 archetype `[V2-C003 시정]`

> 닫는 finding: `00 §3 ↔ A2 §1.5.1 auth gate endpoint 충돌` (오케스트레이터 등재, P1 취급)
> 구체화 대상: `00_SSOT` §3 L1 표 · §7 · §11 · `01_DATA_SPEC` §10 · **A1 §1.2**

`00 §3` L1 표는 **두 행에서만** endpoint 정의 안에 gate를 넣었다.

| `00 §3` 유형 | 원문 | archetype (`A1 §1.2`) |
|---|---|---|
| 금융 | `금융기능 진입 **또는 로그인/인증 gate가 나타난 순간**` | `FINANCIAL_ACTION_ENTRY` |
| 커뮤니티 | `게시물/스레드/작성영역 진입 **또는 로그인 gate**` | `COMMUNICATION_ENTRY` |

§1.5.1의 `AUTH_GATE_REACHED`를 **모든 archetype에 일반 규칙으로** 적용하면 이 두 archetype에서
`endpoint_reached`가 구조적으로 항상 `0`, `MPFED`가 구조적으로 항상 `NULL`이 된다. 그러면
`00 §11`의 archetype별 `MPFED` median/IQR/mode/ECDF, `00 §7`의 `ExcessDepth` 기준선(= 같은 archetype의 중앙값),
`01 §10 mart_archetype_summary`의 `MPFED median`·`MPFED IQR`·`endpoint reach`가 **이 두 행에서 성립하지 않는다.**
`00`이 최상위 권위이므로(§0 1항·8항) **SSOT가 우선하며 이 문서를 고친다.**

**규범표는 archetype만이 아니라 gate 종류로도 갈린다** `[V2-C004 시정]`.
`00 §3` 두 행의 gate 절이 **서로 다르기** 때문이다 — 금융은 `로그인/인증`, 커뮤니티는 `로그인`뿐이다.
이전 판은 두 행을 똑같이 `auth gate`로 일반화해 `00 §3` 커뮤니티 행을 넓혔고, 그 결과
커뮤니티 대상의 **본인인증 gate**가 `AUTH_GATE_REACHED`(§1.5.1이 금지)와 `FUNCTION_ENDPOINT_REACHED`
(`00 §3`이 주지 않음) 사이에서 **미매핑**이 되어 규칙 S-3으로 파이프라인이 실패했다.
아래 표가 그 무주지를 없앤다 (닫는 finding: `a2-1-5-1a-widens-00-3-community-gate-clause-to-any-auth-gate`).

| archetype | 관측된 gate 종류 (`00 §3` 문면 기준) | `endpoint_status` | `endpoint_status_detail` | `endpoint_reached` | `NED`/`IED`/`MPFED` | 근거 |
|---|---|---|---|---|---|---|
| `FINANCIAL_ACTION_ENTRY` | **로그인 gate 또는 인증(본인인증) gate** | **`FUNCTION_ENDPOINT_REACHED`** | `ENDPOINT_VIA_AUTH_GATE` | **1** | 정수 (`m` 확정, `A1 §1.3`) | `00 §3` 금융 행 `또는 로그인/인증 gate` (§0 7항 **EXC-2**) |
| `COMMUNICATION_ENTRY` | **로그인 gate** | **`FUNCTION_ENDPOINT_REACHED`** | `ENDPOINT_VIA_AUTH_GATE` | **1** | 정수 (`m` 확정, `A1 §1.3`) | `00 §3` 커뮤니티 행 `또는 로그인 gate` (§0 7항 **EXC-2**) |
| `COMMUNICATION_ENTRY` `[V2-C004 시정]` | **본인인증 gate** (로그인 gate가 아닌 것) | `AUTH_GATE_REACHED` — 개인정보 입력이 요구됐으면 `PERSONAL_DATA_REQUIRED` | `NULL` | **0** | `NULL` | `00 §3` 커뮤니티 행에 **인증 gate 문구 없음** · `02 §7`이 두 값을 별개로 둠 · `01 §11` 문면 그대로 (EXC-2의 대상이 **아니다**) |
| `QUERY` · `CONTENT_OPEN` · `ITEM_DETAIL` · `PLACE_LOOKUP` · `UTILITY_ENTRY` | 모든 gate 종류 | `AUTH_GATE_REACHED` — 개인정보 입력이 요구됐으면 `PERSONAL_DATA_REQUIRED` | `NULL` | **0** | `NULL` | `00 §3` 해당 행에 gate 문구 **없음** · `01 §11` 문면 그대로 (EXC-2의 대상이 **아니다**) |
| **모든 archetype** `[V2-C008 시정]` | **종류를 확정하지 못한 gate** (`auth_gate_kind = UNDETERMINED`) | `AUTH_GATE_REACHED` — 개인정보 입력이 요구됐으면 `PERSONAL_DATA_REQUIRED` | `NULL` | **0** | `NULL` | 종류가 확정되지 않으면 `00 §3`이 그 행에 준 gate 절을 충족했다고 말할 수 없다. **이 행이 위 네 행보다 우선한다** (규칙 **E-6b**) |

**규칙 E-5 (`00 §3`이 준 종류의 gate는 그 두 archetype에서 endpoint다) `[V2-C004 시정]`.**
`00 §3`이 gate가 나타난 순간 자체를 endpoint로 정의했으므로, 그 두 archetype의 scout가 관측한 gate 중
**`00 §3`이 그 행에 명시한 종류의 gate**는 정의상 `dim_representative_task.endpoint_definition`을 충족한다.
판정은 P-A endpoint codebook이 동결한 `endpoint_definition`으로 하며(§1.9),
**그 정의에는 이 두 archetype에 한해 `00 §3` 문면 그대로의 gate 절이 반드시 포함**된다 —
금융 행은 `로그인/인증`, 커뮤니티 행은 `로그인`이다. 수집 중에 사람이나 모델이 임의로 가르지 않는다.
따라서 두 archetype에서 `AUTH_GATE_REACHED`가 **전혀 발생하지 않는 것은 아니다** —
`COMMUNICATION_ENTRY`의 본인인증 gate는 그 값으로 남는다(규칙 E-6a).

**규칙 E-6a (gate 종류의 archetype별 한정) `[V2-C004 시정]`.**
`00 §3` L1 표는 두 행에 **서로 다른** gate 절을 주었다. 이 문서는 그 차이를 그대로 옮긴다.

| archetype | `00 §3` 문면 | endpoint로 인정되는 gate | endpoint가 **아닌** gate와 그 기록 자리 |
|---|---|---|---|
| `FINANCIAL_ACTION_ENTRY` | `또는 로그인/인증 gate가 나타난 순간` | 로그인 gate · 인증(본인인증) gate | 결제 gate → `PAYMENT_GATE_REACHED`, CAPTCHA → `CAPTCHA`, 차단 → `BLOCKED` (`02 §7`) |
| `COMMUNICATION_ENTRY` | `또는 로그인 gate` | **로그인 gate만** | **본인인증 gate → `AUTH_GATE_REACHED`**(개인정보 입력이 요구됐으면 `PERSONAL_DATA_REQUIRED`), 결제 gate → `PAYMENT_GATE_REACHED`, CAPTCHA → `CAPTCHA`, 차단 → `BLOCKED` (`02 §7`) |

`02 §7`이 `AUTH_GATE_REACHED`와 `PERSONAL_DATA_REQUIRED`를 **별개 값**으로 둔 것, 그리고
`00 §3`이 같은 표의 두 행에서 gate 절을 달리 쓴 것이 원본이 두 종류를 구분했다는 증거다.
**미매핑은 남지 않는다** — `COMMUNICATION_ENTRY`에서 관측 가능한 모든 종료 사건이 `02 §7`의 7값 중
정확히 하나로 간다. 규칙 S-3(닫힌 집합 위반 시 실패)이 발화할 자리가 없다.

**gate 종류의 판별은 수집기의 재량이 아니다.** 로그인 gate와 본인인증 gate를 무엇으로 가르는지는
P-A endpoint codebook이 `endpoint_definition`과 **함께 동결**하며(§1.9 규칙 P-1의 동결 순서),
`fact_task_step.auth_gate_detected` 기록과 evidence(스크린샷·DOM)로 사후 검증 가능해야 한다.
codebook이 가르지 못한 gate는 `endpoint_definition` 미충족으로 보아 endpoint로 승격시키지 않는다 —
**모호할 때 endpoint로 올리는 방향의 기본값을 두지 않는다**(그 방향이 `00 §3` 확대다).
**이 문단은 산문이었고, 그래서 강제되지 않았다** `[V2-C008 시정]` — 판별 결과를 담을 컬럼도, 근거를 남길 자리도,
미확정을 표현할 값도 없었다. 규칙 E-6b가 그 셋을 만든다.

**규칙 E-6b (gate 종류 판별의 확정성 — 비대칭 fail-closed) `[V2-C008 시정]`.**
> 닫는 finding: `e-6a-accepts-misclassified-gate-kind-and-silently-flips-endpoint`
> (LANE C P-C fixture engineering, `agent/landing-pc-fixture` @ `0c36c95`, P2 `E001_V2-blocking`)

규칙 E-6a는 **gate 종류를 입력으로 받는다.** 입력이 틀리면 E-6a는 틀린 값을 **정당한 것으로 통과시킨다** —
커뮤니티의 본인인증 gate를 로그인으로 오판한 순간 `endpoint_status`가 `AUTH_GATE_REACHED`에서
`FUNCTION_ENDPOINT_REACHED`로, `endpoint_reached`가 `0`에서 `1`로, `MPFED`가 `NULL`에서 정수로 **조용히 뒤집힌다.**
**규칙만으로는 탐지되지 않는다.** 바로 위 문단이 산문으로 적은 요구를 여기서 **컬럼·허용값·가드로 못박는다.**

**① 오분류는 한 방향으로만 위험하다.**

| 오분류 방향 | 결과 | 위험의 크기 |
|---|---|---|
| 본인인증 → 로그인 (`COMMUNICATION_ENTRY`) | 없어야 할 `ENDPOINT_VIA_AUTH_GATE`가 생기고 `endpoint_reached 0→1` · `MPFED NULL→정수` | **`00 §3` 커뮤니티 행의 범위 확대**(§7 11항 위반). `MPFED` 분포와 `00 §7` `ExcessDepth` 기준선이 오염된다 |
| 로그인 → 본인인증 (`COMMUNICATION_ENTRY`) | 승격되지 않고 `AUTH_GATE_REACHED` · `MPFED = NULL` | `00 §3` 범위를 넘지 않는다. 관측 손실이지만 **없는 endpoint를 만들지 않는다** |
| 두 종류 사이 (`FINANCIAL_ACTION_ENTRY`) | 두 종류가 모두 endpoint이므로 `endpoint_status`는 바뀌지 않는다 | 종류 자체의 오기록은 남아 규칙 E-6a 회귀검사의 근거를 오염시킨다 |

두 방향이 대칭이 아니므로 **기본값도 대칭일 수 없다.** 확정하지 못했을 때의 기본값은 **승격하지 않는 쪽**이다.

**② `fact_task_step`에 판별 결과와 근거를 저장한다** — `01 §6` `auth_gate_detected`의 동반 컬럼 4종.

| 컬럼 | 허용값 | 규약 |
|---|---|---|
| `auth_gate_kind` | `LOGIN` / `IDENTITY_VERIFICATION` / `UNDETERMINED` | `auth_gate_detected = 1` 인 step에서 **필수**(비-`NULL`). `auth_gate_detected = 0` 이면 `NULL`이다 — 규칙 N-1의 "상태 컬럼을 비워두지 않는다"는 **그 컬럼이 적용되는 행**에 대한 요구다 |
| `auth_gate_kind_basis_login` | 로그인 축에서 관측된 **신호 토큰의 배열** | 관측이 없으면 **빈 배열**이며 `NULL`이 아니다 (규칙 N-3 — 찾았으나 없었다) |
| `auth_gate_kind_basis_identity` | 본인인증 축의 신호 토큰 배열 | 같은 규약 |
| `auth_gate_kind_reason` | 문자열 | `UNDETERMINED`일 때 **필수**. 확정일 때도 비우지 않는다 |

**신호 토큰의 사전은 이 문서가 정하지 않는다.** 각 토큰은 P-A endpoint codebook이 `endpoint_definition`과
**함께 동결**하는 gate 신호 사전의 **닫힌 집합**에서만 나오며(§1.9 규칙 P-1 · §6.4), 사전에 없는 토큰이
기록되면 규칙 S-3 계열로 실패한다. A2는 **필드·허용값·저장 의무**만 정한다 — 무엇이 로그인 신호이고
무엇이 본인인증 신호인지는 P-A가 동결하고 P-C가 구현한다(§6.3).

**③ 두 미확정 조건.** 다음 두 경우는 **구조적으로** `UNDETERMINED`다.

1. **두 축이 동시에 확정 수준의 근거를 갖는다** — 한 화면에 두 절차가 섞여 있다. 한쪽으로 강제분류하지 않는다 (`00 §9` · `02 §10`).
2. **어느 축도 확정 수준에 이르지 못한다** — 근거가 없거나 한쪽 어휘 하나뿐이다.

각 축의 **확정 수준**(최소 근거 수·결정적 신호의 지위)은 이 문서가 값을 정하지 **않는다** —
`A1 §7`의 수집 파라미터와 같은 지위로 P-C가 구현하고 P-A codebook이 동결한다(§6.4).
이 문서가 고정하는 것은 **두 미확정 조건의 존재**와 그때의 귀결이다. 새 임계값을 만들지 않는다(§7 7항).

`auth_gate_detected` 자체는 이 판별과 **무관하게** 결정된다 — auth gate 축의 신호가 하나도 관측되지
않았다면 그것은 gate가 아니며 `auth_gate_detected = 0` · `auth_gate_kind = NULL`이다.
`UNDETERMINED`는 **"gate는 관측됐으나 종류를 모른다"** 이지 "gate가 없다"가 아니다.

**④ 승격 조건 (fail-closed).** endpoint 승격은 아래 세 조건의 **논리곱**이며, 하나라도 거짓이면
`AUTH_GATE_REACHED`(개인정보 입력이 요구됐으면 `PERSONAL_DATA_REQUIRED`)로 간다.

```
endpoint_status = FUNCTION_ENDPOINT_REACHED  AND  endpoint_status_detail = ENDPOINT_VIA_AUTH_GATE
  ⟺  archetype ∈ {FINANCIAL_ACTION_ENTRY, COMMUNICATION_ENTRY}       -- 규칙 E-6
      AND  auth_gate_kind ≠ UNDETERMINED                             -- 규칙 E-6b  (신설)
      AND  auth_gate_kind ∈ (E-6a가 그 archetype 행에 허용한 종류)     -- 규칙 E-6a
```

`FINANCIAL_ACTION_ENTRY`에서는 두 종류가 **모두** endpoint이므로 "둘 중 하나인 것만 확실하면 승격해도
결과가 같다"는 반론이 가능하다. **성립하지 않는다** — `UNDETERMINED`는 *둘 중 하나다*가 아니라
*무엇인지 모른다*이며, 결제 gate·CAPTCHA·차단과도 갈리지 않은 상태다. archetype을 가리지 않고 승격시키지 않는다.

**⑤ 기록과 근거의 교차검증을 파이프라인이 강제한다.** `auth_gate_kind`에 기록된 종류가 같은 step의
`auth_gate_kind_basis_*`가 가리키는 종류와 **모순되면 실패**한다(§6.3 가드). `UNDETERMINED`인데 확정 종류로
기록하는 것, 확정 종류인데 그 축의 근거 배열이 비어 있는 것이 모두 여기서 막힌다.
**오분류는 규칙이 아니라 근거로만 잡히기 때문이다** — 규칙 E-6a는 종류를 입력으로 받으므로 이 검사를 대신할 수 없다.
근거 배열은 **사람이 적어 넣는 값이 아니라** 그 step에 저장된 gate 신호에서 **파생된 값**이다 —
저장된 신호로 재계산한 결과와 기록이 다르면 실패한다. **재계산되지 않는 근거는 근거가 아니다**
(규칙 D-1의 "저장 데이터만으로 제3자가 재계산 가능"과 같은 요구).

**⑥ 사후 변경 금지.** 같은 evidence를 다시 보고 `auth_gate_kind`를 `UNDETERMINED`에서 확정 종류로 바꿔
endpoint를 만드는 것은 금지한다 — X-10이 criterion 축에서 막는 것과 같은 세탁이다. 종류를 바꾸려면
**근거가 달라져야 하고**, 근거가 달라지려면 새 evidence run이 필요하다(§1.11.2 · `02 §12`).

**⑦ 관측 사실은 보존된다 — 승격만 막는다.** `auth_gate_kind = UNDETERMINED` 인 step도
`auth_gate_detected = 1`이므로 규칙 E-9의 `auth_gate_before_endpoint`와 규칙 E-8의 `auth_gate_observed`에
**그대로 들어간다.** 그 gate는 `endpoint_status_detail`이 `NULL`이라 E-9가 말하는
"endpoint를 실현한 gate step"이 아니고, 따라서 `auth_gate_before_endpoint = 1`이 되어 E-8 합집합의
**첫 항**으로 집계된다. 승격은 막되 `00 §11`·`01 §10`의 `auth gate` 유병률에서는 사라지지 않는다.

**⑧ 미확정 비율을 노출한다.** `auth_gate_kind = UNDETERMINED` 인 gate로 종료한 task의 비율
(`auth_gate_kind_undetermined_rate`)을 `mart_archetype_summary`에 archetype별로 병기한다(§6.3).
이 비율이 높으면 승격이 보수적으로 막힌 것이므로 `endpoint reach`·`MPFED` 표본이 그만큼 줄었다는 사실이
함께 보여야 한다. **임계값을 두지 않는다** — 몇 %부터 문제라고 말하는 것은 새 연구기준이다(§7 7항).

**⑨ 잔여 위험 — 이 규칙이 닫지 못하는 것.**

| id | 잔여 | 왜 닫히지 않는가 |
|---|---|---|
| **GK-1** | **판별기 자신의 오류.** 신호 사전이 실제 화면과 어긋나 판별기가 본인인증 gate를 **확정적으로** `LOGIN`이라 판단한다 | ⑤의 교차검증은 *기록자*와 *판별기*의 불일치를 잡는다. 둘이 **같은 사전**을 쓰므로 사전이 틀리면 양쪽이 함께 틀리고 검사는 침묵한다. 저장소 안의 어떤 검사로도 닫히지 않는다. 완화는 evidence(스크린샷·DOM)로 제3자가 근거를 **재계산**할 수 있게 두는 것과 P-A codebook 동결 절차뿐이다 (실패주입 **I-50**, 기대결과 `차단되지 않는다`) |
| **GK-2** | **`UNDETERMINED` 과다.** 사전이 빈약하면 승격이 광범위하게 막혀 `MPFED` 표본이 줄어든다 | fail-closed의 대가이며 **위험의 종류가 다르다** — 이 방향은 `00 §3` 확대가 아니다. ⑧의 비율 병기로 노출하되 임계값으로 막지 않는다 |
| **GK-3** | **P-A 동결 이전.** 신호 사전이 동결되기 전에는 이 층의 실효가 "승격 금지"로만 나타난다 | 이 문서는 자리·허용값·가드만 정한다. 서비스별 적용은 §6.4가 P-A로 미룬 항목이다 |


**규칙 E-6 (확대 금지).** 이 예외는 위 두 archetype에만, 그리고 **규칙 E-6a가 그 행에 허용한 gate 종류에만**
적용한다 `[V2-C004 시정]`. `00 §3`이 `또는 gate`를 준 행이 그 둘뿐이기 때문이다.
다른 archetype의 auth gate를 endpoint로 승격시키는 것도, `COMMUNICATION_ENTRY`의 **본인인증 gate**를
endpoint로 승격시키는 것도 똑같이 `00 §3` 범위 확대이며 금지다 (§7 11항). `UTILITY_ENTRY`는 `00 §3`에 대응 행 자체가 없으므로
(`A1 §1.2`) 이 예외의 대상이 **아니다** — 그 archetype의 endpoint는 P-A codebook이 동결한다.

**규칙 E-7 (gate 통과 금지).** endpoint로 세는 것은 gate가 **나타난 순간**이다.
gate를 통과하거나 자격증명을 입력하지 않는다. `00 §3 절대 제외`의 `로그인 이후`·`본인인증 이후`는
그대로 유효하고, `02 §7` `결제·본인인증을 우회하지 않는다`도 그대로다.
scout는 이 두 archetype에서도 gate 관측 **즉시 종료**한다 (`02 §7`). 달라지는 것은 종료 후 저장하는 값뿐이다.

**규칙 E-9 (`fact_task_entry.auth_gate_before_endpoint`의 허용값과 의미) `[V2-C004 시정]`.**
> 닫는 finding: `rule-e-8-omits-01-6-auth-gate-before-endpoint-column` (ssot `V2-C003` P2)

`01 §6 fact_task_entry`는 이 컬럼을 두는데, 이전 판은 문서 전문에서 **한 번도 언급하지 않았다.**
분기 이전에는 `AUTH_GATE_REACHED`가 항상 비-endpoint 종료였으므로 의미가 자명했으나,
gate가 endpoint인 두 archetype이 생기면서 "endpoint **이전**의 gate"가 무엇인지 갈렸다. 여기서 확정한다.

| 항목 | 값 |
|---|---|
| 허용값 | **`0` / `1`** (정수 0/1). `NULL`을 쓰지 않는다 — `fact_task_entry` 행이 있으면 step 로그가 있고, gate 미관측은 **관측된 0**이다 (규칙 N-3) |
| 정본 원천 | `fact_task_step.auth_gate_detected` (`01 §6` · `02 §7`이 각 activation 후 `auth gate` 기록을 요구한다) |

**`auth_gate_detected`는 gate 종류를 가리지 않는다** `[V2-C004 시정]`. 로그인 gate든 본인인증 gate든
관측되면 `1`이다. **종류를 확정하지 못해도(`auth_gate_kind = UNDETERMINED`) `1`이다** — 그것은 종류가
미확정이라는 사실이지 gate가 없었다는 사실이 아니다 (규칙 E-6b ⑦) `[V2-C008 시정]`. gate 종류의 구분(규칙 E-6a)은 **endpoint 판정에서만** 쓰이며,
`auth gate` **유병률**(`00 §7 별도 기록` · `00 §11` · `01 §10`)은 종류를 합쳐 센다 —
`00 §7`이 `auth gate`를 한 항목으로 적었기 때문이다. 두 용도를 한 컬럼으로 합치면 규칙 S-1이 깨지므로
`endpoint_status`(종류가 반영된 판정)와 `auth_gate_detected`(종류 무관 관측)를 분리해 둔다.

```
auth_gate_before_endpoint =
  1  if EXISTS step ∈ fact_task_step(그 task):
         auth_gate_detected = 1  AND  그 step 이 "endpoint 를 실현한 gate step" 이 아니다
  0  otherwise
```

**"endpoint를 실현한 gate step"은 정확히 하나다** — `endpoint_status_detail = ENDPOINT_VIA_AUTH_GATE` 인
task의 **마지막 step**(그 gate 관측으로 scout가 종료한 step, 규칙 E-7)이다. 그 gate는 endpoint **자체**이지
endpoint 앞을 막은 장애물이 아니므로 `before`로 세지 않는다. 따라서:

| 상황 | `auth_gate_before_endpoint` |
|---|---|
| 두 archetype, gate가 endpoint를 실현했고 그 앞 step에는 gate가 없었다 | **0** |
| 두 archetype, gate가 endpoint를 실현했으나 **그보다 앞선 step에서 별도 gate가 관측됐다** | **1** |
| 두 archetype, gate 없이 실제 기능 진입으로 endpoint 도달 | 앞선 step의 gate 관측 여부대로 0 또는 1 |
| 나머지 5 archetype, gate로 종료(`AUTH_GATE_REACHED`) | **1** — 그 gate가 endpoint 도달을 막았다 |
| `COMMUNICATION_ENTRY`의 본인인증 gate로 종료(규칙 E-6a) | **1** — 같은 이유 |
| **종류 미확정 gate로 종료**(`auth_gate_kind = UNDETERMINED`, 규칙 E-6b) `[V2-C008 시정]` | **1** — 승격되지 않았으므로 그 gate는 endpoint를 실현한 step이 아니다 |
| gate가 한 번도 관측되지 않았다 | **0** |

**규칙 E-8 (auth gate 유병률 집계) `[V2-C004 시정]`.** `00 §11`·`01 §10`의 `auth gate` 지표를
`endpoint_status = 'AUTH_GATE_REACHED'` 만으로 세면 이 두 archetype에서 **0으로 과소집계된다.**
집계 조건은 다음 합집합이며, **`01 §6`의 전용 컬럼을 우회하지 않는다.**

```
auth_gate_observed = (auth_gate_before_endpoint = 1)
                  OR (endpoint_status_detail = 'ENDPOINT_VIA_AUTH_GATE')
```

**이 2항 합집합은 이전 판의 3항 합집합과 같은 집합을 가리키며, 규칙 S-1을 지킨다.**
이전 판의 1항(`endpoint_status = 'AUTH_GATE_REACHED'`)과 3항(step 로그에 gate가 있는 task)은
규칙 E-9의 정의에 의해 **둘 다 `auth_gate_before_endpoint = 1`에 포함**된다.
한 사실(= 이 task 경로에서 auth gate가 관측됐다)이 이제 **한 컬럼**에서 나오고,
나머지 한 항은 그 컬럼이 정의상 세지 않는 단 하나의 경우(gate가 endpoint 그 자체인 경우)를 더한다.
`01 §6`의 전용 컬럼을 그대로 쓰는 구현자와 이 합집합을 쓰는 구현자가 **같은 값에 도달한다** —
E-8이 경고한 과소집계의 재발 경로가 닫힌다.
`auth_gate_kind = UNDETERMINED` 인 gate도 **첫 항에 들어간다** `[V2-C008 시정]` — 승격되지 않아
`auth_gate_before_endpoint = 1`이므로, 종류를 확정하지 못했다는 이유로 유병률에서 빠지는 일은 없다 (규칙 E-6b ⑦).

`PERSONAL_DATA_REQUIRED`로 끝난 관측은 그 자체로 `auth_gate_observed = 1`이 되지 **않는다.**
그 값은 개인정보 입력 요구를 뜻하고 auth gate 관측은 `auth_gate_detected`가 말한다 —
두 사실을 합치면 `00 §7 별도 기록`의 `auth gate` 항목이 다른 사건을 흡수한다.
`endpoint reach`(§1.5.2 규칙 E-4)와 `auth gate`는 **서로 다른 지표**이므로 한쪽 값으로 다른 쪽을 대체하지 않는다.

**규칙 E-10 (두 endpoint 의미의 층화) `[V2-C004 시정]`.**
> 닫는 finding: `gate-endpoint-archetypes-mix-two-endpoint-semantics-without-stratification` (adversarial `V2-C003` P2)

`FINANCIAL_ACTION_ENTRY`·`COMMUNICATION_ENTRY` 안에서 `MPFED`는 이제 두 종류의 관측을 담는다 —
**gate가 나타난 시점까지의 깊이**와 **실제 기능 진입까지의 깊이**다. 사실 자체는
`endpoint_status_detail = ENDPOINT_VIA_AUTH_GATE`로 보존되지만, 층화를 요구하지 않으면
`00 §7` `ExcessDepth`의 기준선(= 같은 archetype의 중앙값)이 **혼합분포의 중앙값**이 되고
`동종 대비 깊은가`가 아니라 `로그인 벽을 앞에 세웠는가`를 재게 된다.
`archetype 내부 비교라 괜찮다`는 반론은 성립하지 않는다 — **혼합이 archetype 내부에서 일어나기 때문이다.**

1. **분리 집계.** 그 두 archetype에서 아래 지표는 `endpoint_status_detail = ENDPOINT_VIA_AUTH_GATE` 여부로
   **층을 갈라 병기**한다. 합산값만 제시하지 않는다.

   | 지표 | 출처 |
   |---|---|
   | archetype별 `MPFED` median · IQR · mode · ECDF · `0/1/2/3/4+` 빈도 | `00 §11` Depth |
   | `ExcessDepth` 기준선(= 같은 archetype의 중앙값) | `00 §7` 상대 깊이 |
   | `mart_archetype_summary`의 `n` · `MPFED median` · `MPFED IQR` · `endpoint reach` | `01 §10` |

2. **정본 산식은 바뀌지 않는다.** `ExcessDepth`의 정본은 `00 §7` 문면 그대로
   **`MPFED − 같은 archetype의 중앙값`**이다. 층별 중앙값 기준의 값은 **병기**이며 정본을 대체하지 않는다.
   이 문서는 새 분석 기준을 만들지 않는다(§7 7항) — 기존 지표를 **층별로 한 번 더 산출하라**는 요구일 뿐이다.
3. **층 크기를 반드시 노출한다.** `mart_archetype_summary`에 `endpoint_via_auth_gate_rate`
   (= 그 archetype에서 `endpoint_status_detail = ENDPOINT_VIA_AUTH_GATE` 인 task 비율)와
   **층별 `n`**을 둔다 (§6.3). 한 층의 `n`이 작아 통계가 성립하지 않으면 그 사실을 적고 산출하지 않는다.
   같은 자리에 `auth_gate_kind_undetermined_rate`(규칙 **E-6b** ⑧)도 병기한다 `[V2-C008 시정]` —
   종류 미확정으로 승격이 막힌 만큼 층 크기가 줄었다는 사실이 층별 `n`과 함께 보여야 한다.
4. **`00 §7 별도 기록`과의 관계.** `00 §7`은 `auth gate`를 **Depth와 합치지 않는다**고 적는다.
   이 절은 그 조항을 위반하지 않는다 — 두 archetype에서 gate는 depth에 **더해지는 항**이 아니라
   depth의 **정지점**이며 `m`을 늘리지 않는다. gate의 유병률은 규칙 E-8로 **별도 집계**되어
   `00 §7`이 요구한 `별도 기록`이 그대로 유지된다.
5. **층화는 해석을 만들지 않는다.** 어느 층의 깊이가 더 좋다/나쁘다고 말하지 않는다.
   층화의 목적은 **서로 다른 사건이 한 분포에 섞이는 것을 막는 것**이며,
   `00 §14` Claim Boundary와 `00 §7`의 `절대 cutoff 대신 상대 깊이` 원칙은 그대로다.

**A1과의 정합.** `A1 §1.2` 신호표는 두 archetype의 endpoint 신호를
`금융기능 진입 또는 로그인/인증 gate가 나타난 순간` · `게시물/스레드/작성영역 진입 또는 로그인 gate`로
`00 §3` **원문 그대로** 적었고, 1차 판정 소스도 `DOM/AX + gate 신호`다.
이 절은 그 신호가 관측됐을 때 **어느 상태값으로 저장되는지**만 확정하며 `A1`의 신호 정의를 바꾸지 않는다
(`A1 §0.3` — A1이 도입한 필드의 값 도메인은 A2가 확정한다).

#### 1.5.2 `endpoint_status_detail` — 하위 세분값

`02 §7`의 7값만으로는 **왜** `UNRESOLVED`인지 구분되지 않는다.
`A1` §2.2가 `UNRESOLVED_DEPTH_BUDGET_EXCEEDED`를, `02 §8`이 replay 실패 기록을 요구한다.

**이 문서는 두 값을 최상위 열거값이 아니라 동반 컬럼 `endpoint_status_detail`의 하위값으로 배치한다.**
동결된 7값 집합을 확장하지 않으면서(`A1` §2.2) 사유를 잃지 않기 위함이다.

같은 컬럼이 §1.5.1a의 `ENDPOINT_VIA_AUTH_GATE`도 담는다 `[V2-C003 시정]`. 그 값의 목적은
`UNRESOLVED`의 사유 세분이 아니라 **endpoint가 auth gate로 실현됐다는 사실의 보존**이며,
그것이 있어야 `00 §11`·`01 §10`의 `auth gate` 지표가 과소집계되지 않는다 (규칙 E-8).
어느 경우에도 7값 집합은 확장되지 않는다.

| `endpoint_status_detail` | 상위 `endpoint_status` | 뜻 | 근거 |
|---|---|---|---|
| `UNRESOLVED_DEPTH_BUDGET_EXCEEDED` | `UNRESOLVED` | `A1` §2.1의 activation·state 재방문·wall-clock·무변화 예산 중 하나가 발화했다 | `A1` §2.2 |
| `UNRESOLVED_REPLAY_BROKEN` | `UNRESOLVED` | 동결된 task manifest의 결정적 replay가 깨졌다 | `02 §8` |
| `UNRESOLVED_NO_SIGNAL` | `UNRESOLVED` | 예산 안에서 어떤 종료신호도 발화하지 않았다 | `02 §7` |
| `ENDPOINT_VIA_AUTH_GATE` `[V2-C003 시정]` | `FUNCTION_ENDPOINT_REACHED` | `00 §3`이 gate를 endpoint로 정의한 두 archetype에서 endpoint가 **auth gate로 실현**됐다. **그 gate의 종류가 확정된 경우에 한한다** — `auth_gate_kind = UNDETERMINED` 이면 이 값을 쓰지 않는다 (규칙 **E-6b**) `[V2-C008 시정]` | `00 §3` · §1.5.1a |
| `NULL` | 나머지 값 | 세분이 필요 없다. 상위 값이 이미 사유다 | — |

**roll-up 규칙** `[V2-C003 시정]`. `endpoint_status_detail`의 각 값은 위 표가 지정한 상위 값 **하나만** 갖는다 —
`UNRESOLVED_*` 3값은 `endpoint_status = 'UNRESOLVED'`, `ENDPOINT_VIA_AUTH_GATE`는
`endpoint_status = 'FUNCTION_ENDPOINT_REACHED'`. 그 외 조합은 존재할 수 없다 (규칙 S-3).
집계·보고는 기본적으로 상위 7값으로 하고, 세분값은 측정품질 진단에 쓴다.
**두 개의 예외가 있다** `[V2-C004 시정]` — (1) `auth gate` 지표는 규칙 E-8의 합집합으로 세고,
(2) 두 archetype의 `MPFED` 계열 지표는 `ENDPOINT_VIA_AUTH_GATE` 여부로 **층화해 병기**한다(규칙 E-10).
두 예외 모두 상위 7값 집합을 확장하지 않으며, 세분값을 **집계의 층**으로 쓸 뿐이다.

**A1 표현의 정합화.** `A1` §2.2는 `endpoint_status`에 `UNRESOLVED_DEPTH_BUDGET_EXCEEDED`를 기록한다고 쓰면서
같은 절에서 `02 §7의 7개 종료값 집합을 확장하지 않는다`고 못박았다. 두 문장은 한 컬럼에서 양립하지 않으므로
`A1` §0.3(`두 문서가 어긋나면 A2의 어휘 정의가 우선`)에 따라 위 2컬럼 구조로 확정한다.
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

**절단과 층화는 서로 다른 축이다** `[V2-C004 시정]`. 위 표는 `UNRESOLVED_*`(잴 수 없었던 관측)의 취급이고,
규칙 E-10의 층화는 `FUNCTION_ENDPOINT_REACHED`(잰 관측)를 **endpoint의 의미**로 가르는 것이다.
두 archetype에서는 두 축이 함께 적용된다 — 층별로 산출하고, 각 층 안에서 절단 건수를 별도로 노출한다.

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

**`ai_review_required = 1`에는 성격이 다른 두 종류가 있다** `[V2-C003 시정]`.

| 발화 조건 | 검토의 목적 | 검토가 `final_status`를 바꿀 수 있는가 | `review_task_type` (§1.8) |
|---|---|---|---|
| 결정적 단계가 신뢰구간을 벗어남 (`verdict_state ∈ {PASS, FAIL}`) | **판정 검토** — 그 판정이 맞는지 | **그렇다.** `PASS ↔ FAIL` 확인·정정, 또는 `ABSTAIN` 시 `UNDETERMINED`로 보수화 | `CRITERION_VERDICT` |
| `verdict_state = UNDETERMINED` | **triage** — 왜 확정 못했는지, 재수집할 가치가 있는지 | **아니다.** 결과는 `UNDETERMINED`로 고정된다 (전파 규칙 **T-8**) | `CRITERION_UNDETERMINED_TRIAGE` |
| 결정적 단계가 신뢰구간을 벗어남 (`verdict_state = NA`) `[V2-C004 시정]` | **적용기회 검토** — 적용 대상이 정말 없는지 | **아니다.** 결과는 `NA`로 고정된다 (전파 규칙 **T-6**). 적용기회 유무를 다시 정하는 유일한 길은 새 evidence run이다 (§1.11.2) | `CRITERION_VERDICT` |

두 번째 행이 이 문서가 `V2-C002` adversarial P1을 닫는 지점이다.
`UNDETERMINED` 행의 검토 산출은 판정이 아니라 `evidence_gap` · `impact_level` · `review_priority`,
즉 **재수집 대기열의 정렬 정보**다 (§1.11.2). 같은 evidence를 다시 읽는 일이
`자료가 부족해 확정할 수 없다`는 진술을 반증할 수는 없기 때문이다.

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

**`evidence_gap`** — 0/1. evidence package(`02 §10`) 자체가 판단에 불충분했다고 검토자가 진술하면 1.

**`evidence_gap`은 전이 허가 조건이 아니다** `[V2-C003 시정]`
(닫는 finding: `a2-undetermined-to-pass-transition-underspecified-and-narrowed`).
이전 판은 이 값을 `laundering 차단의 열쇠`라고 적었고, 그 서술이 금지 전이 X-1에 `evidence_gap = 1`이라는
한정어를 붙이게 만들어 **`evidence_gap = 0` 인 `UNDETERMINED` 행이 `PASS`로 새는 경로**를 열었다.
그 한정어는 제거됐다(§1.11 X-1). 이 값의 용도는 다음 셋뿐이다.

| # | 용도 | 절 |
|---|---|---|
| 1 | `abstention rate` 분자를 `증거 부족` / `의미 모호` / `예산 소진`으로 분해 | §4.5 규칙 B-1 |
| 2 | 사람 검토 5건 선발의 정렬키 (증거가 없으면 사람이 봐도 확정 못하므로 뒤로) | §4.6 규칙 H-1 |
| 3 | **재수집 우선순위 신호** — 어느 `UNDETERMINED` 행을 새 evidence run으로 다시 잴 것인가 | §1.11.2 |

**`evidence_gap = 0`은 "증거가 충분했다"는 뜻이 아니다.** 그것은
**"검토자가 증거 부족을 기권 사유로 들지 않았다"**는 **검토 과정에 대한 진술**이며,
`verdict_state = UNDETERMINED`라는 **데이터에 대한 진술**을 반증하지 못한다 (§2.2의 두 진술 구분).
`evidence_gap = 0`을 근거로 `UNDETERMINED`를 `PASS`(또는 `FAIL`)로 전이하는 것은 금지 전이 **X-9**이자 **X-1**이다.
laundering을 막는 것은 이 컬럼이 아니라 전파 규칙 **T-8**과 금지 전이 **X-1**이다.

**`review_task_type`** — review item이 무엇에 대한 검토인가 `[V2-C003 시정]`.
`01 §9`가 컬럼만 두고 값을 열거하지 않았다. 이 문서가 닫힌 5값으로 확정한다.

| 값 | 검토 대상 | 허용 label 도메인 | criterion `final_status`에 미치는 영향 |
|---|---|---|---|
| `CRITERION_VERDICT` | `verdict_state ∈ {PASS, FAIL, NA}` 인 criterion observation `[V2-C004 시정]` | `{PASS, FAIL, NA}` | `verdict_state ∈ {PASS, FAIL}` 이면 T-7로 전파. **`verdict_state = NA` 이면 전파 없음** — T-6이 우선한다 |
| `CRITERION_UNDETERMINED_TRIAGE` | `verdict_state = UNDETERMINED` 인 criterion observation | `{EVIDENCE_INSUFFICIENT_CONFIRMED, RECOLLECT_RECOMMENDED}` | **없음** (T-8) |
| `INTERRUPT_LABEL` | `fact_interrupt_element`의 방해요소 분류 | §1.6 `final_label` 10값 | 없음 (Axis B) |
| `TASK_MAPPING` | `dim_representative_task`의 대표 task 매핑 | §1.9 `mapping_status` 판단 | 없음 (Frame) |
| `PRIMARY_ACTION_SELECTION` | `fact_primary_action_candidate`의 대표기능 후보 선정 | §1.13 `selection_status` 3값 | 없음 (Axis B) |

**상호배타.** 5값은 상호배타다.

**`verdict_state = NA` ∧ `ai_review_required = 1` 행의 귀속** `[V2-C004 시정]`.
이전 판은 `CRITERION_VERDICT`의 검토 대상을 `verdict_state ∈ {PASS, FAIL}`로,
`CRITERION_UNDETERMINED_TRIAGE`를 `verdict_state = UNDETERMINED`로 두어 **`NA` 행에 붙일 값이 없었다.**
그런데 §1.11.1 전이표 **19·20행**은 그 조합의 존재를 전제한다 — 적용기회 유무의 결정적 판정이
신뢰구간을 벗어나면 `ai_review_required = 1`이 될 수 있기 때문이다(§1.7).
값이 없으면 규칙 S-3으로 파이프라인이 실패한다. `NA`도 **하나의 판정**이므로 `CRITERION_VERDICT`에 귀속시킨다.
**이것이 `NA`에서 나가는 전이를 열지는 않는다** — 그 행의 검토가 무엇으로 끝나든 T-6이 우선하며,
적용기회 유무를 다시 정하는 유일한 길은 **새 evidence run**이다(T-6 · §1.11.2 규칙 RC-1~RC-5).
검토의 산출은 §1.11.2가 정한 재수집 대기열 정보로만 쓰인다.
(이 결손은 `V2-C004` 자기공격의 전수 열거에서 발견됐다 — §1.5.1a 규칙 E-6a가 닫은 무주지와 같은 계열이다.)

**규칙 A-2 (label 도메인 격리).** `CRITERION_UNDETERMINED_TRIAGE` item의 어떤 label 컬럼에도
`PASS`·`FAIL`을 쓰지 않는다. 쓸 수 있게 두면 T-8이 우회될 여지가 생긴다.
triage의 `RESOLVED`는 **triage의 확정**이지 판정의 확정이 아니다.

**`impact_level`** — `HIGH` / `MEDIUM` / `LOW`. **evidence 결손의 성격과 복구 가능성** `[V2-C004 시정]`.
> 닫는 finding: `recollection-escape-path-unbounded-and-conclusion-prioritized` (adversarial `V2-C003` **P1**)

**무엇이 없어서 확정하지 못했는가**, 그리고 **새 evidence run으로 그 결손이 복구될 개연성이 얼마인가**를 적는다.

| 값 | 뜻 |
|---|---|
| `HIGH` | 결손이 **특정됐고** 재수집으로 복구될 개연성이 높다. 예: evidence 7종(`A1 §6.2`) 중 특정 산출물이 비었다 · replay가 깨졌다(`UNRESOLVED_REPLAY_BROKEN`) · 예산 소진으로 관측이 끊겼다(`UNRESOLVED_DEPTH_BUDGET_EXCEEDED`) |
| `MEDIUM` | 결손은 특정되나 복구 개연성이 불확실하다. 예: 동적 렌더링으로 같은 상태가 재현될지 알 수 없다 |
| `LOW` | 재수집으로 복구되지 않는 결손이다. 예: 대상이 그 기준에 대해 관측 가능한 상태를 애초에 노출하지 않는다 |

**이 값은 결론 중립적이다 — 그렇게 정의해야 한다.**
이전 판은 이 값을 `해당 판정이 00 §11 주요 분석 결론을 바꿀 수 있는 정도`로 정의했다.
그 정의 아래에서 §1.11.2의 재수집 우선순위 키로 쓰이면, **명세가 "결론을 바꿀 수 있는 행부터 다시 재라"고
지시하는 것**이 된다. 그것은 결론 방향으로 조준된 optional stopping이며 `00 §14`가 금지한 결론 유도다.
따라서 이 값의 산정에 다음을 **입력으로 쓰지 않는다** (규칙 RC-2 · 금지 전이 X-14).

- `verdict_state` · `final_status` · 그 행의 판정이 어느 쪽이었는지
- `certified_current`(`00 §4` Axis C) · 서비스 정체성 · 도메인·archetype 소속
- 이미 산출된 집계값(`decision coverage` · `undetermined_rate` · 인증 비교 결과 …)

이 값은 **evidence의 상태에 대한 진술**이지 결론에 대한 진술이 아니다 —
`evidence_gap`이 "증거 부족을 기권 사유로 들었는가"라는 검토 과정의 진술인 것과 같은 성질이다(위 문단).

**`review_priority`** — 정수. 사람 검토 5건 선발의 결정적 순서 (§4.6).

**label 컬럼 5종의 전이 권한** `[V2-C003 시정]`.
`01 §9`는 `deterministic_label` · `semantic_model_label` · `reviewer_a_label` · `reviewer_b_label` ·
`arbiter_label` 5개 label 컬럼을 둔다. 어느 것이 criterion `final_status`를 정할 수 있는지 확정한다.

| 컬럼 | `00 §9` cascade 단계 | criterion `final_status`를 단독으로 정할 수 있는가 | 어떻게 반영되는가 |
|---|---|---|---|
| `deterministic_label` | 1. deterministic rule | **아니다** | 결정적 단계의 산출은 이미 `verdict_state`가 담고 있다 (§1.7). 이 컬럼은 cascade 1단계 기록이다 |
| `semantic_model_label` | 2. text/embedding classifier | **아니다** | A·B 검토의 입력. 단독으로 `final_status`가 되지 않는다 |
| `reviewer_a_label` | 3. multimodal reviewer A | **아니다** | A·B가 **일치할 때에만** 합의 label이 되어 T-7의 입력이 된다 (`reviewer_agreement = 1`) |
| `reviewer_b_label` | 4. 독립 reviewer B | **아니다** | 위와 동일 |
| `arbiter_label` | 5. AI arbiter · 6. `HUMAN_FINAL` | **아니다 — 단독으로는.** A·B 불일치 시 확정 label이 되어 T-7의 입력이 된다. 사람 최종검토 결과도 이 컬럼에 담기며 `automation_grade = F_HUMAN_FINAL`로 구별한다 | T-7 |

**세 겹의 제약.** (1) 어느 label 컬럼도 `fact_criterion_result`에 **직접 쓰지 않는다** — 반드시
`fact_ai_adjudication.final_status`를 거쳐 §1.11.1 전이표를 탄다. (2) T-7은 `verdict_state ∈ {PASS, FAIL}`
에서만 작동한다. (3) `verdict_state = UNDETERMINED` 행에서는 T-8이 **label을 읽기 전에** 결과를 고정하므로,
label 컬럼에 무엇이 들어 있든 결과는 `UNDETERMINED`다.

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
| **T-3** `[V2-C003 시정]` | `ai_review_required = 1` → `final_status`는 **§1.11.1 전이표의 전건 대응으로만** 정한다. `fact_ai_adjudication`의 값을 그때그때 해석해 옮기지 않는다. 표에 없는 조합은 존재할 수 없으며, 나타나면 파이프라인이 실패해야 한다 (규칙 S-3) |
| **T-4** `[V2-C004 시정]` | `fact_ai_adjudication.final_status = ABSTAIN` → `fact_criterion_result.final_status = UNDETERMINED`. **단 `verdict_state = NA` 인 행에는 T-6이 우선한다**(전이표 20행). `NA`는 `적용 대상 자체가 없다`는 진술이므로(`01 §7` · `00 §4`) 검토자의 기권이 그것을 `판단불가`로 바꾸지 못한다. 바꾸면 §1.7 항등식 `applicable_count = pass_count + fail_count + undetermined_count`가 깨지고 `decision_coverage_applicable`의 분모가 부풀어 `undetermined_rate`가 과대 보고된다 (금지 전이 X-15) |
| **T-5** | `endpoint_status` · `endpoint_status_detail` · `area_signal_status`는 `fact_criterion_result`로 전파되지 **않는다**. L1 종료 상태는 Axis B 변수이며 Axis A 판정이 아니다 (`00 §4` · `A1 §2.3`) |
| **T-6** `[V2-C004 시정]` | `verdict_state = NA` → `final_status = NA`. adjudication은 `NA`를 바꾸지 못한다 — `RESOLVED`·`ABSTAIN`·`ESCALATED_HUMAN_FINAL`·`PENDING` **네 값 어느 것도 예외가 아니며**, T-4·T-9보다 **우선한다**(전이표 19·20행). 적용기회 유무의 재판정은 새 evidence run에서 `verdict_state`를 다시 내는 일이다(§1.11.2 규칙 RC-1~RC-5) |
| **T-7** `[V2-C003 시정]` | `fact_ai_adjudication.final_status = RESOLVED` → criterion `final_status`는 **`verdict_state ∈ {PASS, FAIL}` 일 때에만** 확정 label로 갱신된다. 확정 label은 `reviewer_agreement = 1` 이면 합의 label(`reviewer_a_label` = `reviewer_b_label`), 아니면 `arbiter_label`이며, 그 값 도메인은 `{PASS, FAIL}`이다. `verdict_state = UNDETERMINED` 인 행에는 **T-8이 우선한다** |
| **T-8** `[V2-C003 시정]` | `verdict_state = UNDETERMINED` → `final_status = UNDETERMINED`. **adjudication 결과가 무엇이든 바뀌지 않는다.** 이 행에 대한 검토의 산출은 `evidence_gap`·`impact_level`·`review_priority`(재수집 우선순위)이지 판정이 아니다 (§1.7 · §1.11.2) |
| **T-9** `[V2-C003 시정]` | `fact_ai_adjudication.final_status ∈ {ESCALATED_HUMAN_FINAL, PENDING}` → criterion `final_status = UNDETERMINED`. 이는 **검토가 끝나지 않았다는 사실의 보수적 표현**이며 판정이 아니다. `03 Phase 5` 측정품질 보고 시점에 `PENDING` 잔여는 **0이어야 한다**. `ESCALATED_HUMAN_FINAL`은 사람 검토가 끝나면 `RESOLVED`로 전이하고, 그때 다시 T-7/T-8을 탄다 |
| **T-10** `[V2-C003 시정]` | 한 criterion observation에 judgment version이 여럿이면 `final_status`는 **가장 최신 version**의 값이다. 이전 version은 삭제하지 않는다 (`02 §12` append-only). 어느 version도 `verdict_state`를 고쳐 쓰지 못한다 (X-10) |
| **T-11** `[V2-C003 시정]` | `measurement_status = NOT_ELIGIBLE_AT_COLLECTION` → Frame 수준 재판정을 **트리거하되 직접 쓰지 않는다.** `dim_web_target`은 §1.4.1의 supersede 경로로만 갱신되며, 관측 행이 Frame 컬럼을 in-place 수정하는 것은 규칙 S-2 위반이다 (§1.3 규칙 W-1) |

#### 1.11.1 adjudication → criterion 전이 전건표 `[V2-C003 시정]`

> 닫는 finding: `a2-undetermined-to-pass-transition-underspecified-and-narrowed` (adversarial `V2-C002` P1)

이전 판은 `fact_ai_adjudication.final_status` 4값 중 `ABSTAIN` 하나만 매핑했고
(`RESOLVED`·`ESCALATED_HUMAN_FINAL`·`PENDING`이 criterion 4값 중 무엇이 되는지 문서 어디에도 없었다),
금지 전이 X-1에는 `evidence_gap = 1` 한정어가 붙어 있었다. 그 둘이 합쳐져
`UNDETERMINED ∧ evidence_gap = 0 ∧ RESOLVED → PASS` 를 막는 규칙이 하나도 없었다.
**아래 표가 전건을 남김없이 열거한다. 표에 없는 조합은 존재할 수 없다.**

| # | `verdict_state` | `ai_review_required` | `fact_ai_adjudication.final_status` | 확정 label (`arbiter_label` 또는 합의 label) | → criterion `final_status` | 규칙 | `UNDETERMINED → PASS` 인가 |
|---|---|---|---|---|---|---|---|
| 1 | `PASS` | 0 | (행 없음) | — | `PASS` | T-2 | 아니오 |
| 2 | `FAIL` | 0 | (행 없음) | — | `FAIL` | T-2 | 아니오 |
| 3 | `NA` | 0 | (행 없음) | — | `NA` | T-2 · T-6 | 아니오 |
| 4 | `UNDETERMINED` | 0 | (행 없음) | — | `UNDETERMINED` | **존재할 수 없는 조합** (§1.7이 `ai_review_required = 1`을 강제). 그래도 결과는 T-8로 `UNDETERMINED` | 아니오 |
| 5 | `PASS` | 1 | `RESOLVED` | `PASS` | `PASS` | T-7 | 아니오 |
| 6 | `PASS` | 1 | `RESOLVED` | `FAIL` | `FAIL` | T-7 (정정) | 아니오 |
| 7 | `PASS` | 1 | `ABSTAIN` | (없음) | `UNDETERMINED` | T-4 (보수화) | 아니오 |
| 8 | `PASS` | 1 | `ESCALATED_HUMAN_FINAL` | (미확정) | `UNDETERMINED` | T-9 | 아니오 |
| 9 | `PASS` | 1 | `PENDING` | (미확정) | `UNDETERMINED` | T-9 | 아니오 |
| 10 | `FAIL` | 1 | `RESOLVED` | `PASS` | `PASS` | T-7 (정정) | 아니오 |
| 11 | `FAIL` | 1 | `RESOLVED` | `FAIL` | `FAIL` | T-7 | 아니오 |
| 12 | `FAIL` | 1 | `ABSTAIN` | (없음) | `UNDETERMINED` | T-4 | 아니오 |
| 13 | `FAIL` | 1 | `ESCALATED_HUMAN_FINAL` | (미확정) | `UNDETERMINED` | T-9 | 아니오 |
| 14 | `FAIL` | 1 | `PENDING` | (미확정) | `UNDETERMINED` | T-9 | 아니오 |
| 15 | **`UNDETERMINED`** | 1 | `RESOLVED` | triage label (`EVIDENCE_INSUFFICIENT_CONFIRMED` / `RECOLLECT_RECOMMENDED`) | **`UNDETERMINED`** | **T-8** | **아니오** |
| 16 | **`UNDETERMINED`** | 1 | `ABSTAIN` | (없음) | **`UNDETERMINED`** | **T-8** (T-4와 같은 결과) | **아니오** |
| 17 | **`UNDETERMINED`** | 1 | `ESCALATED_HUMAN_FINAL` | (미확정) | **`UNDETERMINED`** | **T-8** · T-9 | **아니오** |
| 18 | **`UNDETERMINED`** | 1 | `PENDING` | (미확정) | **`UNDETERMINED`** | **T-8** · T-9 | **아니오** |
| 19 | `NA` | 1 | `RESOLVED` | 무엇이든 | `NA` | **T-6** (adjudication 무시) | 아니오 |
| 20 | `NA` | 1 | `ABSTAIN` / `ESCALATED_HUMAN_FINAL` / `PENDING` | (없음/미확정) | `NA` | **T-6** | 아니오 |

**규칙 충돌의 해소 순서** `[V2-C004 시정]`. 한 행에 둘 이상의 T 규칙이 걸리면 다음 순서로 해소한다.
**T-6(`verdict_state = NA`) > T-8(`verdict_state = UNDETERMINED`) > T-7 · T-4 · T-9.**
두 상위 규칙은 `verdict_state` **하나만** 보고 결과를 고정하므로 adjudication 값과 label을 읽기 전에 끝난다.
19·20행(`NA` ∧ 모든 adjudication)과 15~18행(`UNDETERMINED` ∧ 모든 adjudication)이 그 결과다.

**전건 완전성.** `verdict_state` 4값 × `ai_review_required` 2값 × adjudication 4값 = 논리적 조합 32개다.
`ai_review_required = 0` 이면 adjudication 행이 존재하지 않으므로 그쪽 16개는 1~4행으로 축약되고,
`ai_review_required = 1` 인 16개는 5~20행이 1:1로 덮는다 (`RESOLVED` 행은 확정 label에 따라 다시 갈린다).
**남는 조합은 없다.**

**결론 (15~18행).** `verdict_state = UNDETERMINED` 인 행의 criterion `final_status`는
adjudication 결과 4값 어느 것에서도, 어떤 `evidence_gap` 값에서도, 어떤 label 조합에서도
`UNDETERMINED` 하나다. **`UNDETERMINED → PASS` 경로 수는 0이다.**
`arbiter_label`이 `PASS`라고 적히는 상황 자체가 규칙 A-2(§1.8)로 막혀 있고,
설령 적혀도 T-8이 label을 읽기 전에 결과를 고정한다 — **두 겹으로 닫혀 있다.**

#### 1.11.2 `UNDETERMINED`에서 나가는 유일한 경로 `[V2-C003 시정]`

`UNDETERMINED`는 **"이 evidence로는 확정할 수 없다"**는 진술이다.
같은 evidence를 다시 읽는 어떤 절차도 그 진술을 반증하지 못한다.
`verdict_state`는 evidence의 함수이고(§1.7 — 불변), `final_status`는 §1.11.1 전이표를 통한
`verdict_state`의 함수다. 따라서 **evidence가 바뀌지 않으면 `UNDETERMINED`는 바뀌지 않는다.**

| 경로 | 새 `verdict_state`를 산출하는가 | `UNDETERMINED` 탈출 | 근거 |
|---|---|---|---|
| **새 evidence run**(재수집) → 새 관측 행 → 결정적 파이프라인이 새 `verdict_state` 산출 → 새 judgment version | **예** | **가능 — 단 아래 규칙 RC-1~RC-5의 절차 안에서만.** 새로 산출된 값이 `PASS`·`FAIL`·`UNDETERMINED`·`NA` 무엇이든 그것이 결과다 `[V2-C004 시정]` | `02 §12` `재수집 → 새 evidence run` · §0 7항 EXC-3 |
| 같은 evidence 재판정 → 새 judgment version | 아니다 (`verdict_state` 불변) | **불가능** | `02 §12` + T-8 + X-10 |
| cascade 상위 단계 재호출 (VLM 재실행 · reviewer 교체 · arbiter 재중재) | 아니다 | **불가능** | T-8 · X-1 |
| 사람 최종검토 (`00 §9` 6단계) | 아니다 | **불가능** | T-8 · X-11 |
| `evidence_gap`을 `1`에서 `0`으로 정정 | 아니다 | **불가능** | X-9 |
| `impact_level`·`review_priority` 상향 | 아니다 | **불가능** | X-9 |

**같은 evidence 재판정이 무의미하다는 뜻은 아니다.** `02 §12`가 그 경로를 허용하며, 그것은
`verdict_state ∈ {PASS, FAIL}` 인 행의 판정을 정정하거나(전이표 6·10행), 판정을 `UNDETERMINED`로
보수화하는(7·12행) 데 쓰인다. 막히는 것은 **`UNDETERMINED`에서 나가는 방향**뿐이다.

**재수집이 laundering이 아닌 이유.** 새 evidence run은 `evidence_run_id`·수집 시각·evidence 7종 경로를
새로 남기고 이전 run을 덮어쓰지 않는다 (`02 §12` · `A1 §6`). 판정이 바뀌었다면 **무엇이 달라져서 바뀌었는지가
데이터로 남고 제3자가 두 run을 비교할 수 있다.** 반면 같은 evidence 위의 재판정에서 바뀌는 것은
판단자의 태도뿐이므로 비교할 대상이 없다. 이 비대칭이 X-1을 무조건 금지로 두는 근거다.

**재수집 우선순위.** 어느 `UNDETERMINED` 행을 다시 잴지는 `evidence_gap`·`impact_level`·`review_priority`로
정한다 (§1.8). 이 세 값은 **재수집 대기열의 정렬키**이며 **전이 허가 조건이 아니다** (X-9).
세 값 중 `impact_level`은 §1.8에서 **결론 중립적으로 재정의**됐다 `[V2-C004 시정]` —
`결론을 바꿀 수 있는 정도`가 아니라 **evidence 결손의 성격과 복구 가능성**이다.
이전 정의를 그대로 두면 이 문단이 "결론을 바꿀 수 있는 행부터 다시 재라"는 지시가 된다.
재수집 여부와 무관하게 남은 `UNDETERMINED`는 `00 §11`의 `UNDETERMINED stress bound` 대상이 되어
결론에 미치는 영향이 정량화된다 — 값을 지우는 대신 **영향을 재는 것**이 이 연구의 방식이다.

---

**이 탈출구에는 절차가 필요하다** `[V2-C004 시정]`
> 닫는 finding: `recollection-escape-path-unbounded-and-conclusion-prioritized` (adversarial `V2-C003` **P1 blocking**)
> 예외 등재: §0 7항 **EXC-3** (`02 §12`는 원본이므로 수정하지 않고 절차만 부여한다)

위 표는 재수집을 `UNDETERMINED`의 **유일한 탈출구**로 지정했다. 그런데 `02 §12` 전문은
`재수집 → 새 evidence run` 한 줄이고 **횟수 상한도, 중단규칙도, 사전선언 요구도, 분석 대상 run
선택규칙도 없다.** 그 상태로 두면 다음이 명세를 한 번도 위반하지 않고 성립한다.

> `UNDETERMINED` 행을 다시 잰다 → 여전히 `UNDETERMINED`면 또 잰다 → `PASS`가 나오면 멈춘다.
> 모든 run이 append-only로 남으므로 X-1도 X-10도 전이표도 위반되지 않는다.
> 그럼에도 `decision coverage`는 올라가고 `UNDETERMINED stress bound`는 작아진다.

**laundering을 컬럼에서 막고 파이프라인 재실행 쪽으로 문을 낸 것**이다. 아래 다섯 규칙이 그 문을 닫는다.
추적성(새 `evidence_run_id`가 남는다)은 **선택편향을 막지 못한다** — 남는 것은 두 run의 존재이지
"왜 두 번째 run에서 멈췄는가"가 아니기 때문이다. 그것을 남기는 장치가 사전선언(RC-2)이다.

**규칙 RC-1 (재수집 횟수 상한).**
한 `web_target_id`에 대해 정본 분석에 쓸 수 있는 **재수집 evidence run 수의 상한**을 상수로 둔다.

```
MAX_RECOLLECTION_RUNS_PER_WEB_TARGET = 1      (기본값)
```

- 재수집은 **관측(evidence run) 단위**로 일어나고 한 run이 그 타겟의 모든 criterion 행을 새로 낳으므로,
  상한도 `(web_target, criterion)`이 아니라 **web target 단위**로 둔다. `(web_target, criterion)`당
  재수집 run 수는 여기서 따라 나온다.
- 상한값 **1**은 기본값이며 **P-C에서 구현·P-D(E000_V2 smoke)에서 검증한 뒤 동결**한다.
  `A1 §7`의 수집 파라미터와 같은 지위이며, 동결 전까지는 이 문서의 제안값이다(§6.4).
- **상한은 기록의 금지가 아니다.** 상한을 넘어 수집된 run도 `02 §12` append-only로 남는다.
  다만 그 run의 criterion observation은 **정본 지표(§4.2)에 들어가지 않으며**,
  건수를 `03 Phase 5`에 보고한다(RC-5). 상한을 넘겨 정본 지표를 산출하는 것은 금지 전이 **X-14**다.
- 상한을 올려야 할 사유가 생기면 **P-C 착수 전에 상수를 바꿔 동결**한다.
  수집 중에, 결과를 본 뒤에 올리는 것은 X-14다.

**규칙 RC-2 (사전선언과 중단규칙).**
재수집 run은 **시작 이전에** 대상·사유·기대 evidence를 기록해야 하며, 그 기록은
**그 run이 산출할 evidence를 보기 전에 동결**된다.

*어디에 기록하는가* — 새 evidence run의 **run manifest**
(`07_EVIDENCE_MANIFEST_CONTRACT` · `A1 §6.2` `manifest_path`, 관측이 아니라 run 단위 산출물)에
`recollection_preregistration` 블록으로 남긴다. 필드는 다음 5종이다.

| 필드 | 내용 | 출처 |
|---|---|---|
| `target_criterion_observation_ids` | 이 재수집이 겨냥한 `UNDETERMINED` criterion observation 목록 | `fact_criterion_result` |
| `reason_evidence_gap` | 대상 행의 `evidence_gap` 값을 그대로 복사 | `fact_ai_adjudication` (§1.8) |
| `reason_impact_level` | 대상 행의 `impact_level` 값을 그대로 복사 (**결손의 성격·복구 가능성**, §1.8 재정의) | `fact_ai_adjudication` (§1.8) |
| `expected_evidence` | **복구를 기대하는 evidence 종류** — `A1 §6.2`의 7종(DOM / AX / screenshot(initial) / screenshot(fullpage) / computed CSS / probe / manifest) 중 어느 것이 이번 run에서 산출되어야 하는가. **이전 run에서 실제로 결손이었던 것만 적을 수 있다** — 경로가 `NULL`이었거나 `07` 검증이 `VERIFIED`가 아니었던 산출물, 또는 `endpoint_status_detail = UNRESOLVED_REPLAY_BROKEN`이 기록된 경우의 replay다. 항상 산출되는 산출물(예: run manifest)을 적어 RC-3의 교체 조건을 자동으로 만족시키는 것은 금지 전이 **X-14**다 | `A1 §6.2` · `02 §11` · `07 §4` |
| `attempt_index` | 이 web target에 대한 몇 번째 재수집인가 (RC-1 상한 대조용, 1부터) | 파이프라인 |
| `preregistered_at` | 이 블록이 동결된 시각. **`collection_started_at`보다 이르다** | `A1 §6.1` |
| `anchor` `[V2-C005 시정]` | 이 블록이 **collection 이전에** 원장에 등재됐고 그 실행이 **control에서 인가**됐음을 증명하는 선행 앵커. **6필드** `[V2-C006 시정]` 는 **규칙 RC-6**이 정한다. `preregistered_at`은 자기신고이며 **단독으로는 순서를 증명하지 않는다** — 순서를 증명하는 것은 이 필드다 | 규칙 **RC-6** |

> **이 블록만으로는 부족하다** `[V2-C005 시정]`. run manifest는 run이 **끝난 뒤** 쓰이므로
> `preregistered_at < collection_started_at`은 수집자 자신의 신고일 뿐이다. 그 신고에 순서를 부여하는
> 선행 앵커가 **규칙 RC-6**이며, 시도 전건의 열거가 **규칙 RC-7**이다. 이 표의 6필드는 그대로 두고
> `anchor` 한 필드만 추가된다.

*중단규칙* — 다음 중 **하나라도** 성립하면 그 web target에 대한 재수집을 **중단한다.**

| # | 중단 조건 |
|---|---|
| 1 | `attempt_index`가 `MAX_RECOLLECTION_RUNS_PER_WEB_TARGET`에 도달했다 (RC-1) |
| 2 | 사전선언한 `expected_evidence`가 새 run에서 **실제로 산출됐다** — 그 run의 판정 결과가 무엇이든 중단한다 |
| 3 | 대상 행 전부가 `impact_level = LOW`다 (재수집으로 복구되지 않는 결손) |
| 4 | 새 run의 결손이 이전 run과 **동일하다**(같은 evidence가 또 비었다). 같은 결손이 반복되면 그것은 복구 가능한 결손이 아니다 |

> **판정 결과는 중단 조건이 아니다.** 새 run에서 `PASS`가 나왔는지 `UNDETERMINED`가 그대로인지는
> 중단 여부를 **결정하지 않는다.** 판정 결과를 중단 조건으로 쓰는 순간 그것이 optional stopping이며
> 금지 전이 **X-14**다. 중단 조건 2가 "expected evidence가 산출됐는가"이지
> "원하는 판정이 나왔는가"가 아닌 이유가 이것이다.

**규칙 RC-3 (정본 run 선택규칙).**
한 (`web_target_id`, `criterion_id`)에 criterion observation이 여럿이면
**분석의 분자·분모에 들어가는 행은 다음 사전선언된 규칙으로 정확히 하나 고른다.**

```
정본 run = evidence_run_id 순 최초의 measurement_status = MEASURED run
           단, RC-2 사전선언을 갖춘 재수집 run이 사전선언한 expected_evidence 를
           실제로 산출했다면 그 재수집 run 이 정본이 된다.
           (조건을 만족한 재수집 run 이 둘 이상이면 evidence_run_id 순 최초)
```

- **교체 조건은 evidence의 존재 여부이지 판정 결과가 아니다.** 사전선언한 evidence가 산출됐으면
  그 run이 정본이 되며, 그 run의 `verdict_state`가 `PASS`든 `FAIL`이든 `UNDETERMINED`든 `NA`든
  **그것이 결과다.** 판정을 보고 정본을 고르는 것은 금지 전이 **X-14**다.
- **교체는 run 단위로 일괄 일어난다.** 교체 조건(`expected_evidence` 산출 여부)은 **run의 속성**이므로,
  조건이 성립하면 그 run이 낳은 criterion observation **전부**가 함께 정본이 되고,
  성립하지 않으면 **하나도** 정본이 되지 않는다. criterion별로 유리한 run을 골라 섞는 것은
  가장 값싼 optional stopping이며 금지 전이 **X-14**다.
- **교체의 전제는 앵커 검증 통과다** `[V2-C005 시정]`. 규칙 RC-6의 검사 A-1~A-8 중 **하나라도**
  실패한 재수집 run은 `expected_evidence`를 산출했더라도 정본이 되지 못한다 —
  그 run의 사전선언은 순서가 고정되지 않아 **사전선언으로 인정되지 않으며**, RC-4의 미선언 run과
  같이 취급된다(`disposition = UNDECLARED`, RC-7).
- 사전선언한 evidence를 산출하지 못한 재수집 run은 정본이 되지 못하고 **민감도 분석 전용**으로 남는다.
- 이 규칙은 **P-C 착수 전에 동결**한다(규칙 P-1의 동결 순서와 같은 형식 — 결과를 보기 전에 정한다).
  특정 타겟에 다른 선택규칙을 쓰려면 **그 타겟의 재수집 사전선언 시점에** 그 취지를 manifest에 적어야 한다.
- run을 고른 **뒤에** 그 행 안에 judgment version이 여럿이면 최신 version이다 (**T-10**).
  RC-3(어느 run인가)과 T-10(그 run 안 어느 version인가)은 **서로 다른 축**이며 순서대로 적용된다.
- `NULL` 취급: 어떤 run도 `measurement_status = MEASURED`가 아니면 criterion 행 자체가 없다(규칙 M-1).

**규칙 RC-4 (미선언 run은 정본이 아니다).**
`recollection_preregistration` 블록 없이 시작된 재수집 run의 criterion observation은
**정본 지표에 쓰지 않는다.** 삭제하지도 않는다 — `02 §12` append-only로 남기고 건수를 보고한다(RC-5).
`03 Phase 5` 시점에 이 건수는 **0이어야 한다.**

**"블록 없이"는 세 경우를 모두 포함한다** `[V2-C005 시정]` — ① 블록 자체가 없다,
② 블록은 있으나 `anchor`가 없다, ③ `anchor`가 있으나 규칙 RC-6 검사에 실패한다.
셋 다 `disposition = UNDECLARED`이며 `03 Phase 5` 시점 합계가 **0이어야 한다**.

**규칙 RC-5 (재수집 보고 의무).**
`03 Phase 5` 측정품질 보고에 다음을 **반드시** 적는다. 재수집이 결론을 얼마나 움직였는지를 노출하는 장치다.

```
recollection_rate = |재수집 run 이 존재하는 (web_target, criterion)|
                  / |최초 run 에서 verdict_state = UNDETERMINED 였던 (web_target, criterion)|
```

| 항목 | 내용 |
|---|---|
| `recollection_rate` | 위 산식 |
| **재수집 전후 병기** | `decision_coverage_applicable`·`undetermined_rate_applicable`(§4.2)을 **최초 run만으로 계산한 값**과 **RC-3 정본 run으로 계산한 값** 둘 다 적는다. 한쪽만 제시한 문장은 `03 Phase 6` 역추적 요구를 만족하지 않는다. **기준선인 최초 run도 R-1 부류에 열려 있다** `[V2-C008 시정 · C-2]` — 인가 층 적용(RC-6)으로 *다른 id 선택*은 닫히지만 *같은 id 재실행*은 남는다. 이 병기는 R-1의 **탐지층이지 배제층이 아니다** |
| 정본이 교체된 건수 | RC-3의 단서로 재수집 run이 정본이 된 `(web_target, criterion)` 수 |
| 상한 초과 run 수 | RC-1 상한을 넘어 존재하는 run 수 (정본 지표 제외분) |
| 미선언 run 수 | RC-4 위반 건수 (**0이어야 한다**) |
| 중단 사유 분포 | RC-2 중단규칙 1~4 중 무엇으로 멈췄는가의 건수 |
| **원장 대조 결과** `[V2-C005 시정]` | RC-7 양방향 대조의 4수치 — `ledger_attempts` · `observed_runs` · `원장에만 있는 시도 수` · `원장에 없는 run 수`. 뒤 두 값은 **0이어야 한다** |
| **`disposition` 분포** `[V2-C005 시정]` | RC-7 closed vocabulary 9값별 건수. 폐기(`ABORTED_*`) 건수와 그 사유 문장을 그대로 싣는다 |
| **잔여 한계 문면** `[V2-C009 시정]` | 규칙 RC-8 의 네 요소를 갖춘 한계 절이 보고에 실렸는가. 빠지면 `rc-6-r1` 수용의 근거(조건 C-5-①)가 무너진다 |
| **앵커 검증 결과** `[V2-C005 시정]` | run별 RC-6 검사 A-1~A-8 통과 여부. 실패 run 수는 **0이어야 한다**. **재수집 run과 최초(E001 baseline) run을 모두 센다** `[V2-C008 시정 · rc-6-r1 C-2 보강]` — 인가 층이 최초 run으로 넓어졌으므로(RC-6 적용범위표) 이 행을 재수집 한정으로 두면 바로 위 `실행 인가 대조`의 3수와 정의상 어긋나고, 그 3수는 감사 조건 C-4 (i)(ii)가 대조하도록 지정한 수치다 |
| **실행 인가 대조** `[V2-C006 시정]` | control이 인가한 실행 수 `E`(`recollection_prereg_anchors`에서 센다) · 원장 `EXECUTION` 레코드 수 · 제출된 evidence run 수. **세 수가 같아야 한다.** 다르면 그 차이가 곧 인가받고 숨긴 실행 수다 (검사 A-8). **세 수는 재수집 run과 최초(E001 baseline) run을 합쳐 센다** `[V2-C008 시정 · rc-6-r1 C-2 보강]` — 인가 층이 최초 run으로 넓어졌으므로 대조에서 최초 run을 빼면 그만큼이 대조 밖에 남는다 |


**규칙 RC-8 — 잔여 `rc-6-r1`의 한계를 문면으로 공표한다** `[V2-C009 시정]`

> 닫는 조건: adversarial `V2-C008` focused 조건 **C-5-①**. 등재부 **EXC-5**.

`03 Phase 6` 역추적 대상 보고와 최종 산출물(논문·보고서의 limitation 절)에 **다음 취지를 싣는다.**
문면을 줄이거나 "해소했다"로 바꾸지 않는다.

> 정본 run 선택의 검증은 **커밋된 산출물에 한정된다.** 수집을 로컬에서 여러 번 실행한 뒤
> 하나만 커밋하는 경로는 저장소 측 어떤 검사로도 배제되지 않으며, 본 연구는 이에 대해
> **프로세스 통제**(단일 실행 잠금 · 단일 호출 커밋)와 **역할 분리**(수집자 ≠ 인가자 ≠ 감사자),
> 그리고 **재수집 전후 값 병기 보고**에 의존한다.
> 이 잔여는 **독립 감사가 검토·수용한 것이며 해소된 것이 아니다.**

네 요소가 전부 있어야 한다 — ① 커밋 산출물 한정 ② 프로세스 통제 의존 ③ 역할 분리 의존
④ "독립 감사가 검토·수용한 잔여이며 해소된 것이 아니다". 하나라도 빠지면 이 규칙은 미이행이다.
`00 §14`·`03 Phase 5`는 프리즈이므로 이 절이 그 자리를 대신한다(EXC-5).
---

**앵커가 없으면 RC-2는 결과를 본 뒤에 만들 수 있다** `[V2-C005 시정]`
> 닫는 finding: `recollection-escape-path-unbounded-and-conclusion-prioritized`
> (adversarial `V2-C004` **P1 blocking**, 재판정 **OPEN**) · 예외 등재: §0 7항 **EXC-4**

RC-1~RC-5는 사전선언을 **새 run 자신의 run manifest 안**에만 두었다. 그 manifest는 run이 끝난 뒤
쓰이므로, 기계적으로 검사할 수 있는 순서는 블록 안에 적힌 `preregistered_at < collection_started_at`
**한 줄의 자기신고**뿐이다. `V2-C004` adversarial 감사가 그 경로를 실행으로 재현했다.

> 로컬에서 여러 번 재수집해 `UNDETERMINED` · `FAIL` · `PASS`를 **모두 본 뒤**, 원하는 `PASS` run 하나를
> 골라 `attempt_index = 1`과 소급된 `preregistered_at`으로 사전선언을 지어낸다.
> RC-1~RC-4가 전부 통과하고, 보지 않기로 한 run들은 **애초에 존재한 적 없는 것처럼** 사라진다.

두 결손이다 — **(가) 순서를 고정하는 것이 run 바깥에 없다**, **(나) 시도 전건을 열거할 자리가 없다.**
아래 두 규칙이 그 층을 얹는다. **RC-1~RC-5의 문면은 바뀌지 않으며**, 추가되는 것은
RC-2 블록의 `anchor` 필드와 아래 두 규칙뿐이다.

**규칙 RC-6 (선행 앵커 — precollection anchor).**
재수집 시도는 **시작 이전에** 원장 한 줄을 커밋·push해야 하며, 그 커밋이 앵커다.
**최초(E001 baseline) 수집도 같다** `[V2-C008 시정 · rc-6-r1 C-2 보강]` — 이 규칙의 실행 인가 층은
재수집 run과 최초 run 양쪽에 적용되며, 층별 적용 범위는 아래 *적용 범위* 표가 정한다.
**앵커 1건은 실행 1회를 인가한다** `[V2-C006 시정]` — 실행마다 `EXECUTION` 레코드와 그것을 인가한
control countersign이 각각 하나씩 필요하고, `evidence_run_id`는 그 인가에서 유도된다(유도식 `f`).
여러 실행을 하나의 사전선언에 태우는 경로를 닫기 위해서다 (닫는 finding:
`recollection-escape-path-unbounded-and-conclusion-prioritized`, adversarial `V2-C005` **P1 blocking**).

*원장* — `research/landing_accessibility/collection/recollection_ledger.jsonl`.
git 추적 **append-only JSONL**이며 `state/*.parquet`가 아니다(규칙 V-4 · V-5 · **V-9**).
레코드는 **세 종류**이고 셋 다 append로만 쓴다 — 기존 줄을 고치지 않는다 `[V2-C006 시정]`.
`V2-C005` 판의 두 종류(`PREREGISTRATION` · `DISPOSITION`)에 **실행 단위 레코드 `EXECUTION`** 이 추가된다.

| 필드 | `kind = PREREGISTRATION` (시도 **전**) | `kind = EXECUTION` (실행 **전**) `[V2-C006 시정]` | `kind = DISPOSITION` (실행 **후**, 규칙 RC-7) |
|---|---|---|---|
| `ledger_seq` | 1부터 **조밀한** 전역 정수. 결번 금지 | 〃 | 〃 |
| `prev_record_sha256` | 직전 레코드의 `record_sha256`(첫 레코드는 `0`×64). **해시체인** | 〃 | 〃 |
| `record_sha256` | 자신을 제외한 이 레코드 전 필드를 정규화(키 정렬 · UTF-8 · 개행 없음)한 바이트의 sha256 | 〃 | 〃 |
| `web_target_id` · `attempt_index` | RC-1 상한 대조. web target 안에서 1부터 **조밀** | 〃 (참조) | 〃 (참조) |
| `preregistration` | RC-2 6필드를 그대로 담는다 | — | — |
| `execution_index` `[V2-C006 시정]` | — | 이 앵커 아래 몇 번째 실행인가. 1부터 **조밀** | 〃 (참조) |
| `countersign_commit_sha` `[V2-C006 시정]` | — | **이 실행을 인가한** control 커밋 40자리 SHA (검사 A-5 · A-7) | 〃 (참조) |
| `derived_evidence_run_id` `[V2-C006 시정]` | **없다.** 사전선언 레코드는 run id를 담지 않는다 — 담으면 `record_sha256`이 순환한다 | 아래 유도식 `f`의 값. 레코드에 적되 **검증은 재계산으로 한다**(A-6) | 〃 (참조) |
| `refers_to_record_sha256` | — | 대응 `PREREGISTRATION` 레코드의 `record_sha256` | 대응 **`EXECUTION`** 레코드의 `record_sha256` `[V2-C006 시정]` |
| `disposition` · `disposition_note` | — | — | RC-7 closed vocabulary 9값 + 사유 문장 |

*`evidence_run_id` 유도식 `f`* `[V2-C006 시정]`
> 닫는 finding: `rc-6-a-6-circular-derivation` (ssot `V2-C005` **F3 blocking**)

`V2-C005` 판은 `planned_evidence_run_id`를 사전선언 레코드의 필드로 두고 **동시에** 그 레코드의
`record_sha256`에서 유도되기를 요구했다. `record_sha256`의 입력집합이 그 필드를 포함하므로
해시 고정점 없이는 성립할 수 없었고 유도식도 없었다. **필드를 삭제하고 유도식을 명시한다.**

```
evidence_run_id = "rc" || hex( sha256(
        b"landing-v2/RC-6/f/v1"   || 0x1F ||
        ledger_record_sha256      || 0x1F ||   # PREREGISTRATION 레코드의 record_sha256 (64 hex, 소문자)
        countersign_commit_sha    || 0x1F ||   # 이 실행을 인가한 control 커밋 (40 hex, 소문자)
        ascii(decimal(execution_index))        # 앵커 아래 실행 순번, 1부터, 선행 0 없음
) )[0:32]
```

- **순환이 없다.** `PREREGISTRATION` 레코드에 run id 필드가 없으므로 `record_sha256`의 입력집합에
  run id가 들어가지 않는다. `f`의 입력 셋은 전부 그 레코드 **바깥**에서 온다.
- **해석이 하나뿐이다.** 위 식이 전부이며, 검증자는 `f`를 재계산해 제출된 run의 `evidence_run_id`와
  **바이트 비교**한다(검사 A-6). 구현자가 순환을 임의로 푸는 여지가 없다.
- **수집 시작 전에 계산할 수 없다.** `countersign_commit_sha`는 오케스트레이터가 control branch에서
  만드는 값이고 executor는 그 branch를 쓰지 못한다(`05 §6` executor self-approval 금지 ·
  `EXECUTION_AUTHORITY §5`). 인가 이전에는 evidence 경로 이름 자체가 존재하지 않는다.
- **인가 레코드는 `evidence_run_id`를 담지 않는다.** control 등재 레코드가 그 id를 적으면 그 id는
  자기를 담은 커밋의 SHA를 입력으로 갖게 되어 `V2-C005`가 범한 것과 **같은 종류의 순환**이 다시 생긴다.
  등재 레코드는 `(prereg_commit_sha, ledger_record_sha256, execution_index)`만 담고,
  id는 그 커밋이 만들어진 **뒤에** 누구나 `f`로 재계산한다. 같은 이유로 control 쪽 `absence_proof`도
  id를 미리 알 것을 요구할 수 없다 — 부재 증명은 exec 쪽 A-3이 사후에 수행한다.
- 이 인가는 **오케스트레이터(에이전트) 서명**이며 `00 §9`의 `HUMAN_FINAL_REVIEW_MAX = 5`
  (실제 인간의 criterion 검토 예산)와 **다른 자원**이다. 앵커 서명은 그 5건을 소비하지 않는다.

*앵커* — RC-2 블록의 `anchor` **6필드**는 다음이다 `[V2-C006 시정]` (`V2-C005` 판의 5필드 + `execution_index`).

| 필드 | 내용 |
|---|---|
| `ledger_seq` · `ledger_record_sha256` | 이 run의 `PREREGISTRATION` 레코드 지목 |
| `prereg_commit_sha` | 그 레코드를 **담아 push된** 커밋의 40자리 SHA |
| `prereg_pushed_ref` | push 대상 remote ref (예: `origin/agent/landing-v2-exec`) |
| `countersign_commit_sha` | `prereg_commit_sha`를 `control/state.json`의 `recollection_prereg_anchors`에 등재하고 **이 `execution_index`의 실행을 인가한** control branch 커밋 |
| `execution_index` `[V2-C006 시정]` | 이 run에 대응하는 `EXECUTION` 레코드의 실행 순번. 유도식 `f`의 입력이다 |

*검사 A-1~A-8* — **전부 fail-closed**다. 하나라도 실패하면 그 run은 `UNDECLARED`(RC-4 · RC-7)다.
**A-7 · A-8은 `V2-C006`에서 신설**했다. 각 검사의 `무엇을 막는가` 열은 그 검사가 **배제하지 못하는 것**도 함께 적는다 —
구조적으로 항상 참인 조항을 하중 있는 검사로 착각하지 않기 위해서다.

| # | 검사 | 무엇을 막는가 |
|---|---|---|
| **A-1** | `prereg_commit_sha^{commit}`과 `countersign_commit_sha^{commit}`이 **실제 커밋으로 resolve된다.** 해석 불가능한 값(`NOT_A_COMMIT`, 빈 문자열, 짧은 prefix)은 즉시 거절 | dead argument. `V2-C004` ADV-C004-04가 promotion에서 실증한 형태 |
| **A-2** | `prereg_commit_sha`의 tree에서 원장 파일을 읽어 `ledger_seq` 레코드가 존재하고, 그 레코드의 `record_sha256`이 `anchor.ledger_record_sha256`과 **일치**하며, `prev_record_sha256` 체인이 `ledger_seq = 1`까지 **끊김 없이** 이어진다 | 원장 위조·과거 레코드 개작 |
| **A-3** `[V2-C006 시정]` | `prereg_commit_sha`의 tree에 이 run의 `evidence/<evidence_run_id>/`가 **존재하지 않는다** | 이미 커밋된 evidence 위에 앵커를 얹는 것. **배제하지 못하는 것**: 커밋되지 않은 로컬 산출물. 그리고 `f`가 인가 이후에만 계산되므로 이 검사는 **A-6의 귀결에 가깝다** — 독립 근거로 세지 않는다(잔여 R-2). `evidence`는 exec branch에, countersign은 control branch에 있어 **둘 사이에 조상관계가 성립하지 않으므로** 이 검사는 그런 관계를 요구하지 않는다 |
| **A-4** | `prereg_commit_sha`가 run manifest를 담은 커밋의 **조상**이고, 두 SHA가 다르며, `prereg_pushed_ref`의 기록된 tip의 조상이다 | 커밋을 만들었을 뿐 push하지 않은 로컬 앵커, 별도 계보에 숨긴 앵커 |
| **A-5** `[V2-C006 시정]` | `countersign_commit_sha`가 **검증 시점의 remote control tip**(`ls-remote`로 실시간 조회)의 조상이고, 그 tree의 `control/state.json`이 `prereg_commit_sha`를 `(ledger_record_sha256, execution_index)`와 함께 등재한다 | **수집자 자신이 순서를 정하는 것** + push되지 않은 로컬·dangling countersign. control branch는 executor가 쓰지 않는다(`05 §6` · `EXECUTION_AUTHORITY §5`). `V2-C005` 판의 `조상 중 evidence 커밋 없음` 절은 **삭제한다** — countersign은 control에, evidence는 exec branch에 있어 **구조적으로 항상 참**이었고 배제하는 것이 없었다 |
| **A-6** `[V2-C006 시정]` | 검증자가 유도식 `f(ledger_record_sha256, countersign_commit_sha, execution_index)`를 **재계산**해 이 run의 `evidence_run_id`와 바이트 비교한다. 대응 `EXECUTION` 레코드의 `derived_evidence_run_id`도 같은 값이어야 한다 | **인가받지 않은 id로 수집한 run.** 유효한 id는 `f`의 상(image)뿐이고 `f`의 입력에 control 인가 커밋이 들어가므로, 인가 없이는 통과하는 id를 만들 수 없다. `evidence_run_id`는 `observation_id` 해시 입력(`A1 §6.3`)이자 모든 evidence 경로의 일부라 재부착에는 evidence tree와 `manifest.jsonl` 해시 전량 재생성이 필요하다 |
| **A-7** `[V2-C006 시정]` | 이 run의 `(ledger_record_sha256, execution_index)` 쌍으로 인가된 countersign이 **정확히 하나**이고, 그 쌍에 대응하는 `EXECUTION` 레코드가 **정확히 하나**이며, 그 쌍으로 제출된 evidence run이 **정확히 하나**다 | **하나의 인가에 두 개 이상의 run을 태우는 것.** 인가 1건 ↔ 실행 1회 ↔ run 1건의 1:1:1을 강제한다. **배제하지 못하는 것**: 같은 인가된 id로 로컬에서 여러 번 돌린 뒤 하나만 커밋하는 것(잔여 R-1) |
| **A-8** `[V2-C006 시정]` | control이 이 앵커에 대해 인가한 `execution_index` 집합이 `1..E`로 **조밀**하고, 각 index마다 원장에 `EXECUTION` 1건 + `DISPOSITION` 1건이 있으며, 그 `DISPOSITION` 합계가 `E`와 같다 | **인가받고 결과를 숨기는 것.** `E`는 control이 executor와 독립적으로 세는 값이므로, 인가 3건 중 2건만 제출하면 원장이 아니라 **control 쪽 수와 어긋나 잡힌다**. RC-5가 `E`를 보고에 싣는다 |

- **커밋 시각은 앵커가 아니다.** committer date는 `GIT_COMMITTER_DATE`로 위조되므로 A-1~A-8 어디에도
  순서 근거로 쓰지 않는다. 순서를 고정하는 것은 **부모 관계(A-4)** · **수집자가 쓰지 않는 branch의
  대외 서명(A-5)** · **그 서명을 입력으로 하는 run id 유도(A-6)** 세 가지다 `[V2-C006 시정]`.
  A-3의 부재 증명은 그 셋의 **귀결**이지 독립 근거가 아니다. `preregistered_at`과 committer date는
  **보조 표시**이며 단독으로 어떤 검사도 통과시키지 않는다.
- 외부 timestamp/seal(RFC 3161 · OpenTimestamps 등)을 `anchor`에 덧붙이는 것은 **허용되는 보강**이다.
  A-1~A-8을 대체하지 않으며, 없다고 해서 검사가 완화되지도 않는다.
- **최초 run에도 실행 인가 층을 적용한다** `[V2-C008 시정 · rc-6-r1 C-2]`.
  `V2-C006` 판이 이 자리에 적었던 **"최초 run은 앵커를 요구하지 않는다 — 선택할 대상이 없기 때문이다"는
  R-1 위협모델 아래에서 거짓이었으므로 철회한다** (adversarial `V2-C007` `rc-6-r1` 재분류 조건 **C-2**,
  `audit/landing-adversarial @ fed3e70`). 최초 run도 **커밋되지 않은 로컬 run 사이의 선택에 완전히 열려 있다.**
  앵커가 없으면 A-1~A-8이 **전혀** 적용되지 않으므로, 같은 id 재실행뿐 아니라 **서로 다른 `evidence_run_id`를
  여럿 만들어 고르는 경로**까지 열린다 — 재수집 run에서는 A-6이 닫은 경로다. `V2-C005`가 아래 닫힘 논거표의
  `은닉은 정본 선택에 아무 이득을 주지 못한다`를 철회한 것과 **같은 범주 오류**였다.

  이것이 하중을 지는 이유는 RC-5다 — **R-1 수용이 기대는 최상위 탐지층이 `재수집 전후 병기`이고,
  그 병기의 기준선이 바로 최초 run이다.** 기준선 자체가 선별 가능하면 실제보다 작은 잔여를 인증하게 된다.

  *적용 범위* — RC-6의 **실행 인가 층만** 최초 run으로 넓힌다. 재수집 전용 조항은 넓히지 않는다.

  | RC-6 층 | 재수집 run | **최초(E001 baseline) run** `[V2-C008 시정 · C-2]` |
  |---|---|---|
  | 원장 `PREREGISTRATION` 등재 | RC-2 6필드 전부 | **`expected_evidence` · `preregistered_at`만.** `target_criterion_observation_ids` · `reason_evidence_gap` · `reason_impact_level`은 **`NA`** — 반응할 이전 판정이 없다(§1.14 `NA` = 적용 대상 없음). `attempt_index = 0`을 최초 run에 **예약**한다 |
  | 실행 인가(control) · `EXECUTION` 레코드 · `DISPOSITION` | 적용 | **적용** |
  | `evidence_run_id = f(ledger_record_sha256, countersign_commit_sha, execution_index)` | 적용 | **적용** |
  | 검사 **A-1 · A-2 · A-3 · A-4 · A-5 · A-6 · A-7 · A-8** | 적용 | **적용** (A-3의 지위는 잔여 R-2로 동일) |
  | RC-1 상한 · RC-3 정본 선택 | 적용 | **적용 대상 아님** — 최초 run에는 대체 후보가 없다. `attempt_index = 0`은 `MAX_RECOLLECTION_RUNS_PER_WEB_TARGET` 계수에 들어가지 않는다 |
  | **RC-4 미선언 배제** `[V2-C008 시정 · rc-6-r1 C-2 보강]` | 적용 | **적용한다.** 인가 층을 넓힌 이상 미선언 배제도 함께 넓혀야 한다 — 넓히지 않으면 주입 **I-51**(등재·인가 없는 최초 run)을 `UNDECLARED`로 만들 규칙이 없어 그 주입은 문면상 차단되지 않는다. 최초 run의 `disposition` 값역은 `CANONICAL` · `COMPLETED_NOT_MEASURED` · `UNDECLARED` · `ABORTED_*` 4계열이며, `NON_CANONICAL_SENSITIVITY_ONLY`(RC-3의 대체 후보가 없다) · `OVER_CAP`(RC-1 계수 밖이다)만 적용 대상이 아니다 |

  *왜 (a)인가, 그리고 (b)의 비용* — 대안 (b)는 *최초 run을 앵커 없이 두고 RC-5 기준선의 한계만 적는 것*이었다.
  문서 비용은 (b)가 작다. 그러나 **(b)가 수용하는 잔여는 R-1보다 한 단계 넓다** — 같은 id 재실행에 더해
  *서로 다른 id로 K회 수집한 뒤 하나를 고르는 경로*까지 포함되며, 그것을 `R-1`이라는 이름으로 수용하면
  C-2가 지적한 범주 오류를 그대로 반복한다. (a)를 택하면 최초 run의 잔여가 재수집 run과 **정확히 같은 크기**로
  정렬되어 수용 경계가 하나가 된다. (a)의 비용은 **E001 착수 전 control 인가 1건**이며, 그 인프라
  (`control/state.json`의 인가 대장 · `05 §6` executor self-approval 금지)는 **이미 존재한다** —
  새 층을 만드는 것이 아니라 **적용 범위를 넓히는 것**이다. 늘어나는 것은 E001 시작 절차 한 단계다.

  *원장 파일명은 바꾸지 않는다.* 최초 run 레코드도 `recollection_ledger.jsonl`에 산다 — 이름을 바꾸면
  §5.7 V-9 · §6.3 · `EXECUTION_AUTHORITY` 전건에 파급되므로 하지 않는다. 이름은 연혁이지 범위가 아니다.
- `ledger_seq` · `attempt_index` · **`execution_index`** `[V2-C006 시정]` 의 **조밀성**이 곧 (나)의 절반이다.
  결번은 은닉의 흔적이며 RC-7이 잡는다. `execution_index`의 상한 `E`는 control이 인가한 수이며 수집자가 정하지 않는다.

*이 앵커가 무엇을 닫고 어디에 기대는가* — 명시해 둔다.

| 닫는 것 | 무엇이 닫는가 |
|---|---|
| 사전선언의 **소급 작성** | A-3(부재 증명) · A-4(조상) · A-5(대외 서명). 시각은 근거가 아니다 |
| 결과를 본 뒤 **로컬 run을 골라 선언에 부착** | A-6(run id 바인딩) — 재부착에 evidence 해시 전량 재생성이 필요하다 |
| **은닉한 run이 결론을 고르는 것** — *인가받지 않은 id* `[V2-C006 시정]` | **닫힌다.** 유효한 `evidence_run_id`는 유도식 `f`의 상뿐이고 `f`의 입력에 control 인가 커밋이 들어간다. 인가 없이 만든 id는 A-6 재계산에서 불일치하고, 인가된 id는 A-7이 run 1건에 묶는다 |
| **인가받고 결과를 숨기는 것** `[V2-C006 시정]` | **닫힌다.** 인가 수 `E`는 control이 독립적으로 세며 A-8이 `E` ↔ `EXECUTION` ↔ `DISPOSITION` 전건을 대조한다 |
| **은닉한 *실행*이 결론을 고르는 것** — *인가된 같은 id로 K회 로컬 실행 후 1회만 커밋* `[V2-C006 시정]` | **닫히지 않는다.** 아래 *잔여 위험* R-1. `V2-C005` 판이 이 자리에 적었던 **"은닉은 정본 선택에 아무 이득을 주지 못한다"는 단언은 동일 앵커 재실행에 대해 거짓이었으므로 철회한다** (adversarial `V2-C005` ADV-C005-P1-01). **최초 E001 run도 같다** `[V2-C008 시정 · C-2]` — 인가 층을 최초 run으로 넓혀 *다른 id를 만들어 고르는* 경로는 닫혔으나, *같은 인가 id로 K회 실행*은 최초 run에서도 닫히지 않는다 |
| **판정을 보고 멈추는 것** | RC-2 중단조건 2와 RC-3 교체조건이 둘 다 `expected_evidence`의 산출 여부만 읽는다. `verdict_state`는 어느 검사에도 입력되지 않는다. 상한 RC-1(기본 1)이 반복 횟수 자체를 묶고, RC-5가 재수집 전후 값을 병기시킨다 |

*이 앵커가 무엇을 닫지 **못하는가** — 잔여 위험* `[V2-C006 시정]`

저장소 안의 검사는 **커밋된 것만** 본다. 그래서 아래 넷은 규칙이 아니라 절차·역할분리에 기댄다.
닫혔다고 쓰지 않는다.

| # | 잔여 | 얼마나 좁혀졌는가 | 무엇에 기대는가 |
|---|---|---|---|
| **R-1** `[V2-C008 시정 · C-2]` | **선별적 로컬 재실행(selective local re-execution).** 인가된 **하나의** `evidence_run_id`로 로컬에서 K회 실행한 뒤 1회만 커밋한다. 버린 K−1은 저장소에 흔적이 없다. **이것은 위험 *부류*이며 재수집 run과 최초 E001 run에 똑같이 적용된다** — `V2-C006` 판이 재수집 한 경우로만 적었던 것을 부류로 넓힌다 | id 하나당 run 하나(A-7), id 집합은 control이 인가한 `E`개로 상한(A-6·A-8). 즉 **서로 다른 id를 여러 개 만들어 고르는 경로는 닫혔고**, 남는 것은 `인가 1건당 몇 번 돌렸는가` 하나다 | 수집 도구와 수집자. **저장소 내부 검사로는 배제 불가**하며 `03 Phase 5` 보고와 두 감사 병행이 유일한 층이다. **RC-5 병기는 탐지층이지 배제층이 아니다** — 그 기준선(최초 run)도 같은 부류에 열려 있다 `[V2-C008 시정 · C-2]` |
| **R-2** | A-3의 부재 증명은 *이미 커밋된 evidence 위에 앵커를 얹는 것*만 배제한다 | `f`가 인가 이후에만 계산되므로 A-3은 **거의 자명하게 참**이다. 하중은 A-6이 진다 | — (A-3을 독립 근거로 세지 않는다) |
| **R-3** | `V2-C005` 판 A-5의 `조상 중 evidence 커밋 없음`은 countersign이 control에, evidence가 exec branch에 있어 **구조적으로 항상 참**이었다 | 그 절은 배제하는 것이 없었으므로 **삭제**하고 remote 실시간 tip 도달성으로 대체했다(A-5) | — (시정 완료) |
| **R-4** | 오케스트레이터가 담합하면 인가는 무제한이다 | 이 규칙이 새로 만드는 층이 아니다 | `05 §6`(executor self-approval 금지 · `MAX_UNAUDITED_EXEC_CYCLES = 1`)과 두 감사 병행 |

기대는 **새 가정이 아니라 이미 강제된 분리**다 — A-5의 대외 서명 자리는 `control/landing-orchestrator`이며
`05 §6`(executor self-approval 금지 · `MAX_UNAUDITED_EXEC_CYCLES = 1`)과 `EXECUTION_AUTHORITY`가
executor가 그 branch를 쓰지 못하게 이미 못박고 있다. 앵커는 그 분리를 **재사용**할 뿐 새로 요구하지 않는다.

**규칙 RC-7 (시도 전건 열거와 폐기 사유).**
**시도한 모든 재수집 run**이 원장에 남아야 하고, 그중 무엇이 정본이며 무엇이 어떤 사유로
폐기됐는지가 기록돼야 한다. 결과가 나쁘다는 것은 **사유가 될 수 없다.**

*양방향 대조* — `03 Phase 5`에서 두 방향을 모두 센다(RC-5에 보고).

| 방향 | 요구 |
|---|---|
| 원장 → run `[V2-C006 시정]` | 모든 `EXECUTION` 레코드에 대응 `DISPOSITION` 레코드가 **정확히 하나** 있다 |
| run → 원장 `[V2-C006 시정]` | 존재하는 모든 재수집 evidence run에 대응 `EXECUTION` 레코드가 **정확히 하나** 있다. 없으면 `UNDECLARED` |
| **인가 → 원장** `[V2-C006 시정]` | control이 인가한 `(ledger_record_sha256, execution_index)` **전건**에 대응 `EXECUTION` 레코드가 정확히 하나 있다. 없으면 **인가받고 결과를 숨긴 것**이며 그 앵커의 run 전부가 `UNDECLARED`다 (검사 A-8) |
| 조밀성 `[V2-C006 시정]` | web target별 `attempt_index`가 1..N, 앵커별 `execution_index`가 1..E, `ledger_seq`가 1..M에 각각 결번 없이 차 있다. **`attempt_index = 0`은 최초 run 예약값이며 1..N의 조밀성과 RC-1 계수에 들어가지 않는다** `[V2-C008 시정 · C-2]` |
| 체인 | `prev_record_sha256` 체인이 `ledger_seq = 1`까지 끊기지 않는다 |

*`disposition` closed vocabulary (9값 · 상호배타)*

| 값 | 뜻 | observation 행 |
|---|---|---|
| `CANONICAL` | RC-3이 정본으로 고른 run | 있다 |
| `NON_CANONICAL_SENSITIVITY_ONLY` | 사전선언 `expected_evidence`를 산출하지 못했다. 민감도 분석 전용(RC-3) | 있다 |
| `COMPLETED_NOT_MEASURED` | run은 끝났으나 `measurement_status ≠ MEASURED`다. criterion 행이 없다(규칙 M-1) | 있다 |
| `OVER_CAP` | RC-1 상한 초과. 보존하되 정본 지표 제외 | 있다 |
| `UNDECLARED` | RC-4 위반(블록 없음 · `anchor` 없음 · RC-6 검사 실패). **0이어야 한다** | 있다 |
| `ABORTED_TRANSPORT` | 네트워크·robots·transport 실패로 관측이 시작되지 못했다 | **없다** |
| `ABORTED_TOOLING` | 브라우저 crash·드라이버 오류로 시작되지 못했다 | **없다** |
| `ABORTED_BUDGET` | 수집 예산·시간 상한(`A1 §2.1` · §7)으로 시작 전에 접었다 | **없다** |
| `ABORTED_OPERATOR` | 운영자가 시작 전에 중단했다. `disposition_note` **필수** | **없다** |

- **폐기의 조건은 산출물의 부재이지 결과가 아니다.** `ABORTED_*` 4값은 그 run이
  `fact_landing_observation` 행을 **하나도 남기지 않았을 때에만** 쓸 수 있다.
  **observation 행이 하나라도 있으면 그 run은 폐기할 수 없고** 앞의 5값 중 하나가 된다 —
  전부 원장·evidence에 남고 RC-5에 보고된다. `verdict_state`가 나왔는데 "폐기"로 지우는 경로는
  이 조건 하나로 닫힌다. 금지 전이 **X-14 ⑦**.
- `disposition_note`에 `verdict_state` · `final_status` · 집계값(`decision coverage` ·
  `undetermined_rate` · 인증 비교 결과)을 **인용할 수 없다.** 인용은 그 자체로 결과 기반 폐기의
  증거이며 금지 전이 **X-14 ⑥**다. `impact_level`이 결론 중립적으로 정의된 것과 같은 이유다(§1.8).
- 원장은 evidence를 **대체하지 않는다.** `02 §11`의 7종 identity와 `02 §12` append-only는 문면 그대로이며,
  원장은 그 **앞**에 순서를 고정할 뿐이다. `anchor`가 run manifest 안에 들어가고 run manifest가
  `07 §3`으로 `(observation_id, relpath, sha256, bytes)` 등록되므로, 앵커 digest는 evidence 해시 집합에 묶인다.

**남는 `UNDETERMINED`를 부끄러워하지 않는다.** 이 다섯 규칙의 목적은 재수집을 줄이는 것이 아니라
**재수집이 결론을 고르는 장치가 되지 않게 하는 것**이다. 상한을 소진하고도 남은 `UNDETERMINED`는
그대로 남기고 `00 §11`의 `UNDETERMINED stress bound`로 영향을 잰다 (규칙 N-7).

#### 금지 전이 (laundering 차단)

| # | 금지 |
|---|---|
| **X-1** `[V2-C003 시정]` | `verdict_state = UNDETERMINED` 인 행을 `final_status = PASS`로 전이하는 것. **조건 없는 금지다.** `evidence_gap` 값, `automation_grade`, reviewer A·B 합의, arbiter 판정, 사람 최종검토 — **어느 것도 예외가 아니다.** 증거가 없어서 판단 못한 것을 "충족 확인됨"으로 바꾸는 것이 laundering이다 (`02 §14` `UNDETERMINED→PASS 시도` 문면 그대로) |
| **X-2** | `final_status = ABSTAIN` (criterion 표에는 이 값이 없다). ABSTAIN은 T-4로만 들어오고 들어오는 순간 `UNDETERMINED`가 된다 |
| **X-3** | `NA`를 `PASS`로 세는 집계. `NA`는 분자에도 분모에도 자동으로 들어가지 않는다 (§4.2) |
| **X-4** | `measurement_status` 실패 계열을 `FAIL`로 세는 집계 |
| **X-5** | `endpoint_reached = 0` 인 행의 `NED`/`IED`/`MPFED`를 `0`이나 예산 상한값(`8`)으로 채우는 것. 정답은 `NULL`이다 (규칙 N-1 · `A1 §1.5` · `A1 §2.4`) |
| **X-6** | 사람 검토 예산 소진을 이유로 `ABSTAIN` 대신 `RESOLVED`를 기록하는 것 (규칙 A-1) |
| **X-7** | `NULL`(미관측)과 `0`(관측된 0)을 같은 칸에 세는 집계 (규칙 N-1 · §1.14) |
| **X-8** | `NAME_ABSENT`(이름 없음이 관측됨)를 `NULL`(잴 대상 없음)과 합치는 집계 (규칙 N-4 · §1.6 · §1.14) |
| **X-9** `[V2-C003 시정]` | `evidence_gap` · `impact_level` · `review_priority` · `automation_grade` 를 **전이 허가 조건으로 쓰는 것.** 이들은 재수집 우선순위·보고 분해용 신호이며 어떤 전이도 허가하지 않는다 (§1.8 · §1.11.2) |
| **X-10** `[V2-C003 시정]` | 같은 evidence 위의 재판정(새 judgment version)으로 `verdict_state`를 고쳐 쓰는 것. `verdict_state`는 evidence의 함수이며 **불변**이다 (§1.7). 값을 바꾸려면 새 evidence run이 필요하다 (`02 §12`) |
| **X-11** `[V2-C003 시정]` | `verdict_state = UNDETERMINED` 인 행을 `final_status = FAIL`로 전이하는 것. 증거가 없어 판단 못한 것을 "미충족 확인됨"으로 바꾸는 것도 같은 종류의 조작이며, `FAIL` 비율을 부풀려 `00 §11` 결론을 반대 방향으로 오염시킨다 (T-8) |
| **X-12** `[V2-C003 시정]` | 수집 실패(`FAILED_*`)를 `NOT_ELIGIBLE_AT_COLLECTION`으로 바꿔 기록해 타겟을 표본에서 빼는 것. 두 계열은 서로 다른 사건이며 증거 요구도 다르다 (규칙 M-4 · M-5) |
| **X-13** `[V2-C004 시정]` | `verdict_state = UNDETERMINED` 인 행을 `final_status = NA`로 전이하는 것. `NA`는 `applicable_count`에서 통째로 빠지므로 이 세탁은 `PASS` 세탁보다 `decision_coverage_applicable`을 **더 크게** 움직인다. T-8이 이미 결과를 고정하지만 X-1·X-11과 **대칭을 맞춰** 금지 전이로 등재해 실패주입 대상에 넣는다 (§6.3 V-d) |
| **X-14** `[V2-C004 시정]` | **결과를 보고 재수집하거나 정본 run을 고르는 것**(optional stopping). 구체적으로 ① `verdict_state`·`final_status`·집계 결과를 재수집 대상 선정·중단 조건으로 쓰는 것, ② 사전선언 없이 재수집을 시작하는 것, ③ 사전선언한 선택규칙 밖에서 분석 대상 run을 바꾸는 것, ④ 상한(규칙 RC-1)을 넘겨 정본 지표를 산출하는 것, **⑤ 선행 앵커(규칙 RC-6) 없이, 또는 검사 A-1~A-8에 실패한 앵커로 재수집 run을 정본 지표에 쓰는 것** `[V2-C005 시정]`, **⑥ 시도한 run을 재수집 원장(규칙 RC-7)에 등재하지 않는 것 · 등재를 사후에 고치거나 지우는 것 · `disposition_note`에 판정·집계값을 인용하는 것** `[V2-C005 시정]`, **⑦ `fact_landing_observation` 행을 남긴 run을 `ABORTED_*`로 폐기 처리하는 것** `[V2-C005 시정]`, **⑧ 하나의 control 인가(하나의 `execution_index`)로 재수집을 **두 번 이상 실행**하는 것 · 인가받은 실행의 결과를 원장에 남기지 않는 것** `[V2-C006 시정]`, **⑨ 최초(E001 baseline) run을 원장 등재·control 인가 없이 수집해 정본 지표에 쓰는 것 · 하나의 최초 run 인가로 두 번 이상 실행하는 것** `[V2-C008 시정 · rc-6-r1 C-2 보강]` — RC-6의 인가 층을 최초 run으로 넓히면서 금지 전이를 넓히지 않으면 그 확대는 **강제되지 않는 선언**으로 남는다. 전이 자체는 합법(새 evidence run은 새 `verdict_state`를 낸다)이나 **선택 절차가 결론에 조준되면** 그 결과는 `00 §14`가 금지한 결론 유도다 (§1.11.2 규칙 RC-1~RC-5) |
| **X-15** `[V2-C004 시정]` | `verdict_state = NA` 인 행을 `final_status = PASS`·`FAIL`·`UNDETERMINED` 어느 것으로도 전이하는 것 — `CRITERION_VERDICT` 검토가 `RESOLVED` + 확정 label로 끝나도 마찬가지다(T-6 > T-7). T-4를 `NA` 행에 문면대로 적용하면 발생하며, §1.7 항등식이 깨지고 `undetermined_rate`가 과대 보고된다. T-6이 우선한다 (전이표 20행) |

#### `02 §14` 실패주입의 구체화 `[V2-C003 시정]`

`02 §14`의 `UNDETERMINED→PASS 시도`는 **조건이 붙지 않은 한 항목**이다.
이전 판의 X-1처럼 `evidence_gap = 1`만 태우면 P-D smoke가 통과해도 아무것도 증명하지 못한다.
이 문서는 그 항목을 다음 **세 변종**으로 구체화한다. 원본 항목을 좁히거나 넓히지 않고 나눠 태우는 것이다.

| 변종 | 주입 | 기대 |
|---|---|---|
| V-a | `verdict_state = UNDETERMINED` ∧ `evidence_gap = 1` ∧ `final_status = PASS` 기록 시도 | **차단** (X-1) |
| V-b | `verdict_state = UNDETERMINED` ∧ `evidence_gap = 0` ∧ `final_status = PASS` 기록 시도 | **차단** (X-1) — 이전 판이 열어두었던 경로 |
| V-c | `verdict_state = UNDETERMINED` ∧ adjudication `final_status = RESOLVED` ∧ `arbiter_label = PASS` ∧ `evidence_gap = 0` → 전파 | **차단** (T-8 · 규칙 A-2). 감사가 실증한 정확한 laundering 경로 |

| V-d `[V2-C004 시정]` | `verdict_state = UNDETERMINED` ∧ `final_status = NA` 기록 시도 | **차단** (T-8 · X-13). `NA` 방향은 `applicable_count`를 통째로 줄이므로 `PASS` 세탁보다 `decision_coverage_applicable`을 더 크게 움직인다 |
| V-e `[V2-C004 시정]` | `verdict_state = UNDETERMINED` ∧ `final_status = FAIL` 기록 시도 | **차단** (T-8 · X-11). 반대 방향 오염 |
| V-f `[V2-C004 시정]` | `verdict_state = NA` ∧ adjudication `ABSTAIN` → T-4를 문면대로 적용해 `final_status = UNDETERMINED` 기록 시도 | **차단** (T-6 우선 · X-15). 통과하면 §1.7 항등식이 깨진다 |
| V-g `[V2-C004 시정]` | 사전선언(RC-2) 없는 재수집 run의 criterion observation을 §4.2 분자·분모에 넣는 시도 / 상한(RC-1) 초과 run을 정본으로 쓰는 시도 / 판정 결과를 보고 정본 run을 바꾸는 시도 | **차단** (RC-1 · RC-3 · RC-4 · X-14) |

추가로 `verdict_state = UNDETERMINED → FAIL` 변종(X-11)도 같은 방식으로 태운다.
나머지 X-2~X-15도 E000_V2 smoke에서 차단 여부를 확인한다.
`V2-C003`·`V2-C004`가 신설한 **나머지 규칙 전건**의 주입 케이스는 **§6.3 실패주입 대응표**가 열거한다
`[V2-C004 시정]` — 이 표(V-a~V-g)는 `UNDETERMINED`/`NA` 계열이고, §6.3은 그 밖의 규칙
(E-5~E-10 · A-2 · W-1~W-3 · M-3~M-5 · N-6~N-7 · B-2 · T-7·T-9~T-11 · X-9·X-10·X-12 · RC-1~RC-5)을 덮는다.
두 표를 합치면 두 사이클이 세운 guard가 **빠짐없이** 한 번씩 태워진다
(닫는 finding: `new-v2-c003-rules-absent-from-failure-injection-set`).

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

**`UNDETERMINED`가 사는 다른 축 하나** `[V2-C008 시정]`. §1.5.1a 규칙 E-6b의
`fact_task_step.auth_gate_kind = UNDETERMINED`는 위 표의 값과 **뜻이 같고 수준이 다르다** —
*판단할 수 없음*을 gate 종류 판별 축에 적용한 것이다. **Step 수준**의 값이므로 `decision_coverage`(§4.2)의
분모에 들어가지 않고 `00 §11` `UNDETERMINED stress bound`의 대상도 아니며, 전이 규칙 T-1~T-11 · X-1 · 규칙 N-7은
criterion 수준의 값에 대한 것이라 이 컬럼에 적용되지 않는다. **같은 evidence로 확정으로 바꾸지 않는다**는
요구만 같다 (규칙 E-6b ⑥).

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

**규칙 N-6 (다섯 번째 "값 없음"은 결측이 아니다) `[V2-C003 시정]`.**
`NOT_ELIGIBLE_AT_COLLECTION`(§1.2)은 위 네 결측 어디에도 속하지 않는다.
그것은 **잴 대상이 범위 밖이었다는 양의 관측**이며, `MEASUREMENT_FAILED` 계열과 합치지 않는다
(계열 술어 `LIKE 'FAILED_%'`에 걸리지 않는다). 집계에서의 취급은 §4.1 주의 3이 정한다.

**규칙 N-7 (`UNDETERMINED`는 결측이지만 삭제 대상이 아니다) `[V2-C003 시정]`.**
`UNDETERMINED`를 줄이는 정당한 방법은 **새 evidence run으로 다시 재는 것**뿐이며,
재판정으로 값을 바꾸거나 행을 빼는 것이 아니다 (§1.11.2 · X-1 · X-10 · X-11).
그 재수집도 **무제한이 아니다** `[V2-C004 시정]` — 상한·중단규칙·사전선언·정본 run 선택규칙
(§1.11.2 규칙 RC-1~RC-5) 아래에서만 정본 지표에 반영되며, 절차 밖의 재수집으로 값을 고르는 것은
금지 전이 X-14다.
남은 `UNDETERMINED`는 지우는 대신 `00 §11` `UNDETERMINED stress bound`로 **영향을 잰다.**

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
| 역방향 | **없다.** `UNDETERMINED`는 어떤 adjudication 값으로도 `PASS`/`FAIL`이 되지 않는다 (T-8 · X-1 · X-11) `[V2-C003 시정]` | |

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
   단 verdict_state = NA 였던 행은 T-6 이 우선해 NA 로 남는다.               [V2-C004 시정]
   adjudication 은 NA 를 바꾸지 못한다 (전이표 19·20행).
5. verdict_state 가 애초에 UNDETERMINED 였던 행은 1~4 어느 분기를 타든
   fact_criterion_result.final_status = UNDETERMINED 다 (T-8).            [V2-C003 시정]
   1번 분기로 RESOLVED 가 나와도 바뀌지 않는다 — 그 RESOLVED 는
   triage 의 확정이지 판정의 확정이 아니다 (review_task_type =
   CRITERION_UNDETERMINED_TRIAGE, 규칙 A-2).
```

**5번은 1~4번의 예외가 아니라 상위 제약이다** `[V2-C003 시정]`.
1~4번은 **판정 검토**(`verdict_state ∈ {PASS, FAIL}`)의 경로이고, 5번은 `verdict_state = UNDETERMINED`
행에 대한 무조건 제약이다. 전건 전체는 §1.11.1 표가 열거한다.

**4번의 단서도 같은 성질의 상위 제약이다** `[V2-C004 시정]`
(닫는 finding: `t4-and-2-3-step-4-contradict-t6-for-verdict-state-na`).
이전 판은 T-4와 이 4번 분기를 **조건 없이** 적어 `verdict_state = NA` 행에서 T-6과 정면으로 갈렸다
(T-4는 무조건 `UNDETERMINED`, T-6은 무조건 `NA`). §1.11.1 전이표 19·20행은 `NA`로 해소하고 있었으나
본문 두 곳에 예외 표기가 없었다. **SSOT 근거로 T-6이 옳다** — `01 §7`·`00 §4`에서 `NA`는
`적용 대상 자체가 없음`이라는 **데이터에 대한 진술**이고, `ABSTAIN`은 §2.2가 정한 대로
**검토 과정에 대한 진술**이다. 검토자가 기권했다는 사실이 "적용 대상이 없다"를 "판단할 수 없다"로
바꿀 수는 없다. 게다가 T-4 쪽으로 통일하면 §1.7 항등식
`applicable_count = pass_count + fail_count + undetermined_count`가 깨진다(`NA` 행은 `applicable_count = 0`).
**T-4 · 4번 분기 · T-6 · 전이표 19·20행이 이제 한 방향(`NA` 유지)으로 통일됐다.**

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
`frame_coverage`의 분모는 supersede(§1.4.1) 이후 **각 타겟의 최신 행 기준**으로 센다.

**주의 3 `[V2-C003 시정]`.** `measurement_status = NOT_ELIGIBLE_AT_COLLECTION` 인 행은
**분자·분모 양쪽에서 제외**한다. 이 행은 evidence 산출의 실패가 아니라
**P-B 적격성 판정이 관측으로 반증된 사건**이므로, 분모에 넣으면 적격성 오판정이
evidence completeness 하락으로 잘못 표시되고, 분자에 넣으면 잴 수 없었던 대상을 잰 것처럼 센다.
대신 **별도 지표로 반드시 보고**한다 (§1.4.1 규칙 W-3).

```
eligibility_reversal_rate = |NOT_ELIGIBLE_AT_COLLECTION 이 관측된 web target|
                          / |P-B 에서 ELIGIBLE_WEB 로 동결된 web target|
```

이 값이 0이 아니면 `03 Phase 5` 측정품질 보고에 건수와 함께 적고,
`measurement_status_detail`로 `APP_ONLY_AT_COLLECTION` / `NO_PUBLIC_WEB_LANDING_AT_COLLECTION`을 분해한다.
숨기면 `02 §13`이 보호하려던 사실 자체가 사라진다.

**주의 4 `[V2-C004 시정]` — 이 지표에는 §1.11.2 규칙 RC-3의 run 선택규칙을 적용하지 않는다.**
분모가 `관측이 **시도된** 전체 observation 수`이므로 **재수집 run도 하나의 시도**이며 분모에 들어간다.
정본 run 하나만 세면 재수집이 evidence completeness를 **보이지 않게** 만든다.
§4.2(criterion 수준)와 이 지표(observation 수준)가 서로 다른 행 집합을 세는 것은 의도된 것이며,
그래서 두 지표를 **항상 함께** 보고하라는 §4.2의 요구가 여기서도 유효하다.
재수집으로 늘어난 시도 건수는 `recollection_rate`(규칙 RC-5)와 대조해 읽는다.

### 4.2 decision coverage

`01 §10` `mart_service_summary`와 `03 Phase 5`가 함께 쓰는 지표다. **두 변종을 모두 저장한다.**

| 변종 | 분자 | 분모 |
|---|---|---|
| `decision_coverage_applicable` **(정본)** | `final_status ∈ {PASS, FAIL}` 인 criterion observation 수 | `final_status ∈ {PASS, FAIL, UNDETERMINED}` 인 criterion observation 수 |
| `decision_coverage_all` (보조) | `final_status ∈ {PASS, FAIL, NA}` | `final_status ∈ {PASS, FAIL, NA, UNDETERMINED}` |

**분자·분모에 들어가는 criterion observation 행의 선택** `[V2-C004 시정]`
> 닫는 finding: `recollection-escape-path-unbounded-and-conclusion-prioritized` (adversarial `V2-C003` **P1**)

한 (`web_target_id`, `criterion_id`)에 evidence run이 여럿이면 — 재수집(`02 §12`)이 새 `evidence_run_id`를
낳고 그것이 새 `observation_id`(`A1 §6`)를 거쳐 **새 criterion observation 행**을 만들기 때문에 —
분자·분모는 **§1.11.2 규칙 RC-3이 정한 정본 run 하나의 행만** 센다.

| 축 | 규칙 | 무엇을 고르는가 |
|---|---|---|
| run | **RC-3** (§1.11.2) | 여러 evidence run 중 **정본 run 하나** |
| judgment version | **T-10** (§1.11) | 그 run 안에서 **최신 version** |

두 축은 **순서대로** 적용된다. T-10만으로는 부족하다 — T-10은 한 criterion observation **안의**
version만 다루고, 재수집은 **행 자체를 새로 만들기** 때문이다. 이 순서를 적지 않으면
"최신 run을 쓴다"는 암묵 관행이 규칙 자리를 대신하고, 그것이 곧 optional stopping의 통로가 된다.

- 정본이 아닌 run의 criterion observation은 **민감도 분석 전용**이며 정본 지표를 대체하지 않는다.
- **결과를 보고 run을 고르는 것은 금지 전이 X-14다.** RC-3의 교체 조건은 사전선언한
  `expected_evidence`의 산출 여부이지 판정 결과가 아니다.
- **정본이 되려면 선행 앵커가 있어야 한다** `[V2-C005 시정]`. 재수집 run의 criterion observation은
  규칙 **RC-6** 검사 A-1~A-8을 전부 통과하고 규칙 **RC-7** 원장 대조에서 대응 레코드가 확인될 때에만
  분자·분모에 들어간다. 앵커 없는 사전선언은 결과를 본 뒤에도 쓸 수 있으므로 **사전선언이 아니다**.
- **최초(E001 baseline) run의 criterion observation도 같은 조건을 받는다** `[V2-C008 시정 · rc-6-r1 C-2 보강]` — 인가 층을 넓힌 이상
  기준선 run 역시 A-1~A-8 통과와 RC-7 원장 대조가 확인될 때에만 분자·분모에 들어간다. 이 조건을 최초 run에
  걸지 않으면 RC-5 병기의 `전` 값만 앵커 밖에 남아, C-2가 지적한 **기준선 오염**이 그대로 남는다.
- 재수집 전후 값을 **병기**하는 의무는 규칙 RC-5에 있다. 그 병기가 **탐지층이지 배제층이 아닌** 이유는 RC-5 표 주 참조.
- 같은 선택규칙이 `mart_service_summary`·`mart_archetype_summary`의 criterion 계열 집계와
  `00 §11`의 `decision coverage`·`UNDETERMINED stress bound`에도 그대로 적용된다.

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

**규칙 B-2 (`review_task_type`별 분리) `[V2-C003 시정]`.** 분자·분모를 `review_task_type`(§1.8)별로
**나눠 보고한다.** `CRITERION_UNDETERMINED_TRIAGE` item의 기권은 "판정을 못 정했다"가 아니라
"재수집 권고를 못 정했다"이므로, 판정 검토(`CRITERION_VERDICT`)의 기권율과 한 칸에 합치면
`abstention rate`가 실제보다 나쁘게 보인다. 정본으로 보고하는 값은 `CRITERION_VERDICT` 기준이며,
triage 기권율은 병기한다.

**주의.** `abstention rate`의 분모는 **AI 검토에 올라온 건수**이지 전체 criterion observation이 아니다.
criterion 수준의 `UNDETERMINED` 비율(§4.2)과 다른 값이며, 서로 대체할 수 없다.

**criterion `UNDETERMINED`의 세 성분** `[V2-C003 시정]`. §1.11.1 전이표에 따라 다음 셋이 섞이므로
`03 Phase 5` 보고에서 **나눠 적는다.** 셋을 합쳐 놓으면 `00 §11` `UNDETERMINED stress bound`의
해석이 불가능해진다.

| 성분 | 조건 | 뜻 |
|---|---|---|
| (a) 측정 미확정 | `verdict_state = UNDETERMINED` (전이표 15~18행, T-8) | **데이터가 부족했다.** 재수집(새 evidence run) 대상이며 재판정으로는 바뀌지 않는다 (§1.11.2) |
| (b) 기권 전파 | `verdict_state ∈ {PASS, FAIL}` ∧ adjudication `ABSTAIN` (7·12행, T-4) | **검토가 확신하지 못해 보수화됐다.** `abstention rate`의 분자와 대응한다 |
| (c) 검토 미완결 | `verdict_state ∈ {PASS, FAIL}` ∧ adjudication `ESCALATED_HUMAN_FINAL`/`PENDING` (8·9·13·14행, T-9) | **아직 끝나지 않았다.** `PENDING` 잔여는 보고 시점에 0이어야 한다 (T-9) |

(a)는 AI 검토에 `CRITERION_UNDETERMINED_TRIAGE`로 올라가지만 그 검토가 판정을 바꾸지 않으므로,
`CRITERION_VERDICT` 기준 `abstention rate`(규칙 B-2)와 **대응하지 않는다.**
두 지표를 서로의 대용으로 쓰지 않으며, (a)의 규모는 §4.2 `undetermined_rate_applicable`과
`00 §11` `UNDETERMINED stress bound`에서 읽는다.

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
| `url_confidence` | 없음 | — | **(c) ABSENT → P-B** | 값 도메인 `HIGH`/`MEDIUM`/`LOW` — §1.3.1 `[V2-C008 시정]` |
| `eligibility_basis` | `service_master.web_eligibility_basis` | **entity 수준** | (b) DERIVED, **grain 불일치** | 이름이 다르고 이 문서가 바인딩하지 않고 있었다. §1.3.1 규칙 EB-1 `[V2-C008 시정]` |
| `eligibility_reviewer` | 없음 | — | **(c) ABSENT → P-B** | v1 `06` §2-2 요구. §1.3.1 `[V2-C008 시정]` |
| `eligibility_confidence` | 없음 | — | **(c) ABSENT → P-B** | v1 `06` §2-2 요구. §1.3.1 `[V2-C008 시정]` |
| `eligibility_reviewed_at` | 없음 | — | **(c) ABSENT → P-B** | §1.3.1 `[V2-C008 시정]` |
| `eligibility_needs_review` | 없음 | — | **(c) ABSENT → P-B** | `service_master.needs_human_review`는 **다른 층**이다 — §1.3.1 규칙 EB-2 `[V2-C008 시정]` |
| `url_type` · `url_discovery_method` · `url_reviewer` | 없음 | — | **(c) ABSENT → P-B** | v1 `06` §3-1 근거 사슬. §1.3.1 규칙 EB-3 `[V2-C008 시정]` |
| `redirect_chain` · `target_url` | 없음 | — | **(c) ABSENT → P-B** `[V2-C008 시정 · 2차]` | `06` §3-3은 사슬 **전체** 보존을 요구한다. 홉 **수**는 사슬이 아니다 — §1.3.1 규칙 EB-4 `[V2-C008 시정]`. **P-B 다** — eligibility 판정의 근거 필드이므로 §6.2 P-B 목록과 같은 phase 여야 한다(이전 판의 `P-C` 는 §6.2 와 자기모순이었다: ssot V2-C008) |

**지적 3.** `01 §3`이 `dim_web_target`을 `신규`로 분류하지만 기준선에 이미 `web_target_group`(68행, C012 산물)이 있다.
둘의 관계는 **대응이 아니라 선행**이다 — `web_target_group`은 P-B의 **입력**이며,
URL 증거로 검증되면 `dim_web_target` 행이 되고, falsifier가 성립하면 SPLIT된다.
`expected_url_relationship_confirmed_by_url`이 전부 `False` `[실측]` 인 지금,
그룹을 web target으로 간주한 어떤 집계도 근거가 없다.

**`MERGE` 판정은 이 층에 존재하지 않는다 — 실측** `[V2-C008 시정]`

> 닫는 finding: `merge-decision-merges-nothing-no-alias-assert` (v1 승계)

이 결함은 "`MERGE` 판정이 실제로는 아무것도 병합하지 않는다"를 지적한다. 두 층을 나눠 실측했다.

| 층 | 판정 원장 | `MERGE` 건수 | 판정 |
|---|---|---|---|
| **web target 그룹 가설** | LANE B `shadow/lane_b/state/web_target_group_shadow.csv` 68행 | **0** `[실측]` | **적용대상 없음 (MOOT)** |
| **measurement entity** | `state/entity_review_decisions.json` 7건 | **1** `[실측]` | 실재하며 실제로 별칭을 흡수한다 |

그룹 층 68행의 `hypothesis_outcome` 분포는
`NOT_APPLICABLE_SINGLETON` **65** · `FALSIFIED_SPLIT_SAME_DOMAIN_DIFFERENT_PATH` **2**(gmarket · naver) ·
`NOT_TESTABLE_MEMBER_URL_UNRESOLVED` **1**(coupang)이며 `MERGE`도 `CONFIRMED_*`도 **0건**,
`confirmed_by_url`은 68행 전부 `False`다 `[실측]`. 그룹 층에서는 이 결함이 **재현되지 않는다** —
고친 것이 아니라 적용할 판정이 없다. 이 사실 자체가 감사가 검증해야 할 근거다.

entity 층의 `MERGE` 1건(`hyundai_homeshopping_hmall`)은 원문 표기 2종
(`현대홈쇼핑/현대Hmall` · `현대홈쇼핑/현대Hmallord`)을 실제로 흡수한다 `[실측]`.
그룹 층 `member_count`가 1로 유지되는 것은 그 흡수가 C003에서 이미 별칭으로 끝난 뒤이기 때문이며
(두 축 독립, §1.3 `REVIEW_AXIS_INDEPENDENCE_NOTE`), **병합이 없었다는 뜻이 아니다.**

없던 것은 판정이 아니라 **단언**이었다. `MERGE`가 데이터 상 무엇을 뜻하는지 검사하는 코드가
어디에도 없어, 원장에 `MERGE`라고 적기만 하면 흡수가 0건이어도 빌드가 통과했다.
`src/landing_accessibility/review_queue.py::assert_merge_decisions_absorb_aliases`가 세 조건을 단언한다.

| # | 조건 |
|---|---|
| **M1** | `MERGE`로 판정된 canonical entity는 서로 다른 `entity_name_raw`를 2종 이상 갖는다 — 흡수할 것이 없으면 `MERGE`가 아니다 |
| **M2** | 흡수된 표기가 별칭 원장(`entity_alias_map`)에 그 entity로 등재돼 있다 — 원자료에만 있고 원장에 없으면 흡수가 아니라 유실이다 |
| **M3** | 흡수된 표기가 다른 canonical entity로도 매핑되지 않는다 — 매핑되면 흡수가 아니라 중복이다 |

`MERGE` 0건은 이 단언의 **정상 상태**이며 오류가 아니다(그룹 층이 그 경우다).
반례 4종이 `tests/test_c012_review_and_grouping.py`에 주입돼 있다.

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
| **V-9** `[V2-C005 시정]` | 재수집 원장 `recollection_ledger.jsonl`(규칙 RC-6 · RC-7 · §0 7항 EXC-4)은 **`research/landing_accessibility/collection/`** 에 두는 **머티리얼라이제이션 레이어 산출물**이며 `state/*.parquet`의 표가 아니다. 원본 parquet에 컬럼·행·파일을 추가하지 않는다(규칙 V-1 · V-4 · V-5 · §7 8항). git 추적 대상이며 **append로만** 쓴다 — 기존 줄 수정·삭제는 규칙 RC-7 체인 검사가 잡는다 |

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
| **컬럼**: `superseded_from_web_target_id` | §1.4.1 수집 시점 반증 supersede의 계보 링크. 물리 컬럼 없음 `[V2-C003 시정]` |
| `dim_representative_task` 동결 | `mapping_status = FROZEN` 전이. 규칙 P-1 순서 준수. `region_signal_type = CODEBOOK_PENDING` 잔여 0 (규칙 P-2) |
| `dim_certification` join 준비 | `state/_invalidated/`의 draft는 무효 보관물이며 입력이 아니다 |
| 3건 그룹 가설 검정 | `expected_url_relationship_falsifier` 3건 `[실측]` 을 URL 증거로 검정. SPLIT 여부 확정 |
| **컬럼**: `eligibility_basis` · `eligibility_reviewer` · `eligibility_confidence` · `eligibility_reviewed_at` · `eligibility_needs_review` · `eligibility_rule` | v1 `06` §2-2 판정 근거 요건. 규칙 **EB-1**(근거 없는 상태 부여 금지) · **EB-2**(층 분리)가 이 컬럼들을 검사한다 — §1.3.1 `[V2-C008 시정]` |
| **컬럼**: `url_type` · `url_discovery_method` · `url_reviewer` | v1 `06` §3-1 URL 근거 사슬. `url_type`의 4값은 `06` §3-1을 그대로 승계한다 — §1.3.1 규칙 **EB-3** `[V2-C008 시정]` |
| **컬럼**: `redirect_chain` · `target_url` | `06` §3-3은 셋 전부 보존을 요구한다. 등록도메인 비교는 PSL 파서로 — §1.3.1 규칙 **EB-4** `[V2-C008 시정]` |

### 6.3 P-C (L0/L1 엔진)

| 산출물 | 내용 |
|---|---|
| `fact_landing_observation` 표 | `measurement_status` **7값** 어휘 구현 + `measurement_status_detail` 2값 (§1.2) `[V2-C003 시정]` |
| **컬럼**: `screenshot_initial_path` · `screenshot_fullpage_path` · `computed_css_path` · `evidence_run_id` · `collection_started_at` · `collection_finished_at` · `viewport_configured_*` · `device_pixel_ratio` | `A1` §6.1. §4.1 evidence completeness 분자의 근거 |
| `fact_interrupt_element` 표 | `classification_status` 5값 · `final_label` 10값 · `ai_review_status` 7값 (§1.6 · §1.10) |
| **컬럼**: `dismiss_method` 5값 · `dismiss_failure_mode` 5값 · `dismiss_persistence_hint` · `dismiss_screenshot_before/after` · `dismiss_dom_after` | `A1` §3.3 · §3.4 (§1.6) |
| `fact_task_entry` 표 | `endpoint_status` 7값 + `endpoint_status_detail` **4값** + `area_signal_status` 3값 (§1.5). archetype별·**gate 종류별** auth gate 분기(§1.5.1a 규칙 E-5 · E-6 · **E-6a** · **E-6b** `[V2-C008 시정]` · E-7) 구현. 규칙 N-1~N-7 `NULL` 처리 구현 `[V2-C004 시정]` |
| **컬럼**: `auth_gate_before_endpoint` | `01 §6`의 실재 컬럼. 허용값 `0`/`1`, 정본 원천 `fact_task_step.auth_gate_detected`, 산식과 경계 사례는 **규칙 E-9**(§1.5.1a). `auth gate` 유병률(규칙 E-8)이 이 컬럼에서 나온다 `[V2-C004 시정]` |
| **컬럼**: `auth_gate_kind` · `auth_gate_kind_basis_login` · `auth_gate_kind_basis_identity` · `auth_gate_kind_reason` (`fact_task_step`) | 규칙 **E-6b** `[V2-C008 시정]`. `auth_gate_detected = 1` 인 step에서 `auth_gate_kind` **3값**(`LOGIN`/`IDENTITY_VERIFICATION`/`UNDETERMINED`) 필수, 근거 배열은 **빈 배열 허용·`NULL` 금지**(규칙 N-3). 신호 토큰은 P-A codebook이 동결한 닫힌 집합에서만 나온다 |
| **지표**: `auth_gate_kind_undetermined_rate` | 규칙 **E-6b** ⑧. `mart_archetype_summary`에 archetype별 병기. **임계값을 두지 않는다** `[V2-C008 시정]` |
| `mart_archetype_summary` 층화 | 규칙 **E-10** — `FINANCIAL_ACTION_ENTRY`·`COMMUNICATION_ENTRY`에서 `MPFED` median/IQR/mode/ECDF · `endpoint reach` · `ExcessDepth` 기준선을 `endpoint_status_detail = ENDPOINT_VIA_AUTH_GATE` 여부로 **층별 병기**. **컬럼**: `endpoint_via_auth_gate_rate` + 층별 `n` `[V2-C004 시정]` |
| **run manifest**: `recollection_preregistration` 블록 | 규칙 **RC-2**의 사전선언 기록 자리. 5필드(`target_criterion_observation_ids` · `reason_evidence_gap` · `reason_impact_level` · `expected_evidence` · `attempt_index` · `preregistered_at`). `07_EVIDENCE_MANIFEST_CONTRACT` · `A1 §6.2` run manifest 안에 산다 (§0 5항의 단 하나의 예외) `[V2-C004 시정]` |
| **상수**: `MAX_RECOLLECTION_RUNS_PER_WEB_TARGET` | 규칙 **RC-1**. 기본값 **1**. P-C 구현 → P-D(E000_V2) 검증 → 동결. `A1 §7`의 수집 파라미터와 같은 지위 `[V2-C004 시정]` |
| **원장**: `research/landing_accessibility/collection/recollection_ledger.jsonl` | 규칙 **RC-6** · **RC-7**의 append-only JSONL. **세 레코드 종류**(`PREREGISTRATION` / **`EXECUTION`** / `DISPOSITION`) `[V2-C006 시정]` 와 필드는 §1.11.2 표 그대로. **최초 run 레코드도 같은 원장에 산다**(`attempt_index = 0`, RC-2 재수집 사유 3필드는 `NA`) `[V2-C008 시정 · C-2]`. **머티리얼라이제이션 레이어 산출물이며 `state/*.parquet`가 아니다**(규칙 V-9 · §0 7항 EXC-4) `[V2-C005 시정]` |
| **run manifest**: `recollection_preregistration.anchor` **6필드** | 규칙 **RC-6**. `ledger_seq` · `ledger_record_sha256` · `prereg_commit_sha` · `prereg_pushed_ref` · `countersign_commit_sha` · **`execution_index`** `[V2-C006 시정]` |
| **control**: `control/state.json` → `recollection_prereg_anchors` | 규칙 **RC-6** 검사 A-5 · **A-7 · A-8**의 대외 서명 자리이자 **실행 인가 대장**이다 `[V2-C006 시정]`. 항목은 `(prereg_commit_sha, ledger_record_sha256, execution_index)`를 담으며 `execution_index`는 앵커별 1..E 조밀이다. **오케스트레이터가 control branch에서만 쓴다** — executor는 쓰지 않는다(`05 §6`). 이 문서는 자리·필드·검사만 정하고 control 산출물의 형식은 `EXECUTION_AUTHORITY`를 따른다 |
| **가드**: 규칙 **RC-6** 선행 앵커 | **재수집 run과 최초(E001 baseline) run 양쪽에** `[V2-C008 시정 · C-2]` 검사 **A-1~A-8을 전부 fail-closed로** 구현한다. `prereg_commit_sha`·`countersign_commit_sha`를 `rev-parse <sha>^{commit}`로 해석하지 못하면 즉시 실패, tree에 evidence 경로가 있으면 실패, 조상관계가 아니면 실패, control 등재가 없으면 실패, **유도식 `f` 재계산값이 `evidence_run_id`와 다르면 실패, 인가 1건에 run이 0건이거나 2건 이상이면 실패, control 인가 수 `E`와 `EXECUTION`·`DISPOSITION` 수가 다르면 실패** `[V2-C006 시정]`. **committer date를 순서 근거로 쓰지 않는다** |
| **가드**: 규칙 **RC-7** 원장 전수 대조 | 양방향 대조 4수치 · **인가 → 원장 대조** `[V2-C006 시정]` · `attempt_index`/`ledger_seq`/**`execution_index`** 조밀성 · `prev_record_sha256` 체인 연속성 · `disposition` 9값 도메인 · **observation 행이 있는 run의 `ABORTED_*` 금지** · `disposition_note`의 판정·집계값 인용 금지를 파이프라인이 **거부**한다 `[V2-C005 시정]` |
| **지표**: `recollection_rate` + 재수집 전후 병기 | 규칙 **RC-5**. `03 Phase 5` 측정품질 보고 항목 6종 `[V2-C004 시정]` |
| `fact_task_step` 확장 | `depth_segment` 3값 · `counts_toward_depth` · `area_signal_detected` (§1.5.4, `A1` §1.8) |
| `fact_task_episode` 표 (신규) | `episode_kind` 2값 · `ended_by` 9값 · `input_mode` 2값 (§1.12, `A1` §4.4) |
| `fact_primary_action_candidate` 표 (신규) | `selection_basis` 4값 · `selection_status` 3값 · `area_css_px2` (§1.13, `A1` §5.1) |
| `fact_task_step` 표 | — |
| `fact_criterion_result` 표 | `verdict_state` · `final_status` · `automation_grade` 7값 · `ai_review_required` (§1.7 · §3) |
| `fact_ai_adjudication` 표 | `final_status` 4값(`ABSTAIN` 포함) · `human_required` · `review_priority` · `review_task_type` **5값** (§1.8 · §2) `[V2-C003 시정]` |
| **가드**: 전이 규칙 **T-1~T-11** | 파이프라인에 강제. §1.11.1 전이표를 **표 그대로 구현**하고, 표에 없는 조합에서 실패시킨다. 규칙 충돌은 **T-6 > T-8 > T-7·T-4·T-9** 순서로 해소한다 `[V2-C004 시정]` |
| **가드**: 재수집 규칙 **RC-1~RC-5** | 상한 초과·미선언·결과 기반 run 선택을 파이프라인이 **거부**한다. 사전선언 블록의 `preregistered_at < collection_started_at` 검사 포함 — 단 이 검사는 **자기신고 보조 검사**이며 순서 증명은 RC-6이 맡는다 `[V2-C005 시정]` |
| **가드**: 규칙 **E-6a** gate 종류 한정 | `COMMUNICATION_ENTRY`에 본인인증 gate로 `endpoint_status_detail = ENDPOINT_VIA_AUTH_GATE`가 붙으면 실패 `[V2-C004 시정]` |
| **가드**: 규칙 **E-6b** 승격 fail-closed | `auth_gate_kind = UNDETERMINED` 인 gate에 `FUNCTION_ENDPOINT_REACHED` · `ENDPOINT_VIA_AUTH_GATE` · `endpoint_reached = 1` · 정수 `MPFED` 중 **어느 하나라도** 붙으면 실패 `[V2-C008 시정]` |
| **가드**: 규칙 **E-6b** 근거 교차검증 | 기록된 `auth_gate_kind`가 같은 step의 근거 배열이 가리키는 종류와 **모순되면** 실패. 확정 종류인데 그 축의 근거 배열이 비었으면 실패. **근거 배열은 저장된 gate 신호에서 재계산해 대조**하며 손으로 적은 값을 받지 않는다. **`auth_gate_kind`가 비-`NULL`인데 `auth_gate_detected = 0`이면 실패**(유병률 누락 차단, 규칙 E-6b ⑦) `[V2-C008 시정]` |
| **가드**: 규칙 **E-9** 컬럼 정합 | `auth_gate_before_endpoint`가 step 로그와 어긋나면 실패. `auth_gate_observed` 2항 합집합과 step 로그 기반 재계산이 **일치**해야 한다 `[V2-C004 시정]` |
| **가드**: 규칙 **E-10** 층화 | 두 archetype의 `MPFED` 계열 지표가 층별 값 없이 합산값만 산출되면 실패 `[V2-C004 시정]` |
| **가드**: 금지 전이 **X-1~X-15** | `02 §14` 실패주입으로 차단 검증. `UNDETERMINED→PASS`는 §1.11 세 변종(V-a·V-b·V-c) 전부를 태우고, `→FAIL`(V-e) · `→NA`(V-d) · `NA→UNDETERMINED`(V-f) · optional stopping(V-g)도 태운다 `[V2-C004 시정]` |
| **가드**: 규칙 A-2 label 도메인 격리 | `CRITERION_UNDETERMINED_TRIAGE` item의 label 컬럼에 `PASS`/`FAIL`이 들어가면 실패 `[V2-C003 시정]` |
| **가드**: 규칙 W-1~W-3 · T-11 | 관측이 Frame 컬럼을 in-place 수정하지 못하게 강제. supersede 경로만 허용 `[V2-C003 시정]` |
| **가드**: 정합 제약 G-2~G-6 | `automation_grade` 검증 |
| **가드**: 항등식 | `applicable_count = pass_count + fail_count + undetermined_count` (§1.7) |
| **지표**: §4의 6개 산식 | numerator/denominator를 코드로 고정. `03 Phase 6` 역추적 요구 |

#### 6.3.1 `02 §14` 실패주입 대응표 — `V2-C003`·`V2-C004` 신규 규칙 전건 `[V2-C004 시정]`

> 닫는 finding: `new-v2-c003-rules-absent-from-failure-injection-set` (adversarial `V2-C003` P2, `E001_V2-blocking`)

`02 §14`는 `모든 guard가 실제로 차단하는지 확인한다`고 요구한다. 두 사이클이 세운 규칙이 한 번도
태워지지 않으면 `E000_V2_VALIDATED`가 **비어 있는 근거로** 닫힌다. 아래 표가 각 규칙에 주입 케이스를
1:1로 붙인다. `UNDETERMINED`/`NA` 계열(V-a~V-g)은 §1.11에 있고 여기서 반복하지 않는다.

**기대결과가 `차단되지 않는다`인 행이 셋 있다** `[V2-C006 시정 · V2-C008 갱신]` — **I-41 · I-50 · I-53**. 실패주입 표는
가드가 막는 것을 증명하는 자리이자 **막지 못하는 것을 은폐하지 않는 자리**다. 막지 못하는 주입을
표에서 빼면 그 표는 "전건이 차단된다"는 거짓 인상을 준다. §1.11.2 잔여 위험 R-1 · §1.5.1a 잔여 **GK-1**과 짝을 이룬다.

| 주입 id | 규칙 | 주입 | 기대 |
|---|---|---|---|
| **I-1** | **E-5** | `FINANCIAL_ACTION_ENTRY` 대상에서 로그인 gate 관측 후 `endpoint_status = AUTH_GATE_REACHED` 기록 시도 | **차단** — `00 §3` 금융 행이 그 gate를 endpoint로 정의했다 |
| **I-2** | **E-6** | `QUERY` archetype 행에 `endpoint_status_detail = ENDPOINT_VIA_AUTH_GATE` 기록 시도 | **차단** (E-6 · S-3 · roll-up 규칙) |
| **I-3** | **E-6a** | `COMMUNICATION_ENTRY` 대상에서 **본인인증 gate** 관측 후 `FUNCTION_ENDPOINT_REACHED` + `ENDPOINT_VIA_AUTH_GATE` 기록 시도 | **차단** — `00 §3` 커뮤니티 행은 `로그인 gate`만 준다 |
| **I-4** | **E-6a** (역방향, 미매핑 회귀) | `COMMUNICATION_ENTRY`의 본인인증 gate 관측을 `AUTH_GATE_REACHED`(또는 `PERSONAL_DATA_REQUIRED`)로 기록 | **통과해야 한다** — 이 값이 막히면 `V2-C003` ssot F1의 무주지가 재발한다. S-3 미발화를 확인한다 |
| **I-5** | **E-7** | 두 archetype에서 gate 관측 **이후** activation이 더 발생한 궤적 주입 (자격증명 입력·gate 통과) | **차단** (E-7 · `02 §7` 즉시종료 · `00 §3 절대 제외`) |
| **I-6** | **E-8** | `auth gate` 유병률을 `endpoint_status = 'AUTH_GATE_REACHED'` 단독으로 집계 | **차단/불일치 검출** — 두 archetype에서 0으로 과소집계됨을 회귀검사가 잡는다 |
| **I-7** | **E-9** | `endpoint_status_detail = ENDPOINT_VIA_AUTH_GATE` 인 task에 `auth_gate_before_endpoint = 1`을 그 endpoint gate 하나만 근거로 기록 | **차단** — endpoint를 실현한 gate는 `before`가 아니다 |
| **I-8** | **E-9** | `auth_gate_before_endpoint`를 `NULL`로 기록 | **차단** (허용값 0/1, 규칙 N-3 관측된 0) |
| **I-9** | **E-10** | 두 archetype의 `MPFED median`·`ExcessDepth` 기준선을 층 구분 없이 합산값만 산출 | **차단** — 층별 값과 `endpoint_via_auth_gate_rate` 누락 시 산출 실패 |
| **I-10** | **A-2** | `CRITERION_UNDETERMINED_TRIAGE` item의 label 컬럼에 `PASS`/`FAIL` 기록 시도 | **차단** |
| **I-11** | **W-1** · **T-11** | 관측 행이 `dim_web_target`의 Frame 컬럼을 in-place 수정 시도 | **차단** (S-2 · supersede 경로만 허용) |
| **I-12** | **W-2** | supersede 경로를 **범위 안으로 되돌리는** 방향(`EXCLUDED` → `ELIGIBLE_WEB`)으로 사용 시도 | **차단** (배제 방향으로만) |
| **I-13** | **W-3** | `NOT_ELIGIBLE_AT_COLLECTION`이 1건 이상인데 `eligibility_reversal_rate` 미보고 | **차단** (보고 누락 시 Phase 5 산출 실패) |
| **I-14** | **M-3** | `measurement_status = NOT_ELIGIBLE_AT_COLLECTION` 기록 시 파이프라인이 실패 | **실패하면 안 된다** — S-3은 표에 **없는** 값의 규칙이다. 오탐 회귀검사 |
| **I-15** | **M-4** | 증거 없이 `NOT_ELIGIBLE_AT_COLLECTION` 기록 시도 | **차단** (증거 못 남기면 `FAILED_EVIDENCE_INCOMPLETE`) |
| **I-16** | **M-5** · **X-12** | `FAILED_*` 관측을 `NOT_ELIGIBLE_AT_COLLECTION`으로 재분류해 표본에서 제외 시도 | **차단** |
| **I-17** | **N-6** | `NOT_ELIGIBLE_AT_COLLECTION`을 `LIKE 'FAILED_%'` 계열에 넣어 §4.1 분모에 산입 | **차단** (계열 경계 위반) |
| **I-18** | **N-7** | 남은 `UNDETERMINED` 행을 삭제하거나 `stress bound` 대상에서 제외 | **차단** |
| **I-19** | **B-2** | `abstention rate`를 `review_task_type` 분리 없이 한 칸에 합산 | **차단** (정본은 `CRITERION_VERDICT` 기준, triage 병기 필수) |
| **I-20** | **T-7** | `verdict_state = UNDETERMINED` 행에 `RESOLVED` + 확정 label로 T-7 적용 시도 | **차단** (T-8 우선) |
| **I-21** | **T-9** | `03 Phase 5` 시점에 `PENDING` 잔여 > 0 | **차단** (잔여는 0이어야 한다) |
| **I-22** | **T-10** · **X-10** | 새 judgment version으로 `verdict_state`를 고쳐 쓰는 시도 | **차단** (`verdict_state` 불변) |
| **I-23** | **X-9** | `evidence_gap = 0`·`impact_level = HIGH`를 전이 허가 조건으로 사용 | **차단** |
| **I-24** | **RC-1** | `attempt_index > MAX_RECOLLECTION_RUNS_PER_WEB_TARGET` 인 run을 정본으로 사용 | **차단** (X-14) |
| **I-25** | **RC-2** | `preregistered_at >= collection_started_at` 인 사전선언 블록 / `expected_evidence` 없는 블록 | **차단** (결과를 본 뒤의 선언) |
| **I-26** | **RC-2** 중단규칙 | 판정 결과(`PASS` 등장)를 중단 조건으로 삼은 재수집 궤적 주입 | **차단** (X-14 optional stopping) |
| **I-27** | **RC-3** | 사전선언한 `expected_evidence`를 산출하지 못한 재수집 run을 정본으로 사용 | **차단** |
| **I-28** | **RC-4** | 사전선언 블록 없는 재수집 run의 criterion observation을 §4.2 분자·분모에 산입 | **차단** |
| **I-28b** | **RC-3** (run 단위 일괄) | 같은 web target에서 criterion마다 서로 다른 run을 정본으로 골라 섞는 시도 | **차단** (X-14) |
| **I-29** | **RC-5** | 재수집이 1건 이상인데 재수집 전후 `decision_coverage_applicable` 병기 누락 | **차단** (Phase 5 산출 실패) |
| **I-30** `[V2-C005 시정]` | **RC-6** A-1 | `anchor.prereg_commit_sha`를 누락하거나 해석 불가능한 값(`NOT_A_COMMIT` · 빈 문자열 · 7자리 prefix)으로 두고 정본 지정 시도 | **차단** (fail-closed. dead argument 금지) |
| **I-31** `[V2-C005 시정 · V2-C006 갱신]` | **RC-6** A-3 · A-6 | **backdating 재현** — 로컬에서 재수집을 여러 번 돌려 결과를 모두 본 뒤 사전선언 레코드를 커밋해 앵커로 제출. 그 커밋 tree에는 이미 `evidence/<run_id>/`가 있다 | **차단** — A-3 부재 증명 실패. 나아가 그 로컬 run의 id는 인가 이전에 정해졌으므로 유도식 `f` 재계산과도 불일치한다(A-6). `V2-C004` §3.4가 통과시켰던 정확한 경로다 |
| **I-32** `[V2-C005 시정]` | **RC-6** A-2 | 과거 `PREREGISTRATION` 레코드의 `expected_evidence`·`attempt_index`를 고치고 history를 rewrite해 앵커를 재작성 | **차단** — `prev_record_sha256` 체인 단절 + 기존 `prereg_commit_sha` 참조 전건이 resolve 실패 + A-5 조상관계 파탄 |
| **I-33** `[V2-C005 시정]` | **RC-6** A-5 | control branch 등재 없이(또는 evidence 커밋 이후에 등재된 countersign으로) 재수집 run을 정본 지정 | **차단** — 수집자 자신이 순서를 정하는 경로 |
| **I-34** `[V2-C005 시정]` | **RC-7** 양방향 | 시도한 run 하나를 원장에서 누락 — evidence run에 대응 `PREREGISTRATION`이 없거나, web target의 `attempt_index`가 1..N에 결번 | **차단** — 은닉 흔적. 누락분은 `UNDECLARED`로 계상되어 RC-4의 `0` 요구를 깨뜨린다 |
| **I-35** `[V2-C005 시정]` | **RC-7** 폐기조건 | `fact_landing_observation` 행을 남긴 run을 `ABORTED_OPERATOR`로 기록해 원장에서 폐기 처리 | **차단** — `ABORTED_*`는 observation 행 0건일 때만 |
| **I-36** `[V2-C005 시정]` | **RC-7** 사유 | `disposition`을 closed vocabulary 9값 밖 값으로 기록 / `disposition_note`에 `verdict_state`·`decision coverage` 등 판정·집계값을 인용 | **차단** (X-14 ⑥) |
| **I-37** `[V2-C005 시정 · V2-C006 갱신]` | **RC-6** A-6 | 사전선언·인가는 정상인데, 실제 제출된 run의 `evidence_run_id`가 유도식 `f`의 재계산값과 다르다(= 다른 id로 로컬 수집한 run을 재부착) | **차단** — `f` 재계산 불일치. 재부착하려면 `observation_id`(`A1 §6.3`)와 `manifest.jsonl` 해시 전량 재생성이 필요하다 |
| **I-38** `[V2-C006 시정]` | **RC-6** A-6 | control 인가 없이 임의의 `evidence_run_id`(또는 앵커 취득 전에 미리 정한 id)로 재수집 run을 만들어 정본 지정 시도 | **차단** — 유효 id는 `f`의 상뿐이고 `f`의 입력에 `countersign_commit_sha`가 들어간다. 인가 이전에는 통과하는 id를 계산할 수 없다 |
| **I-39** `[V2-C006 시정]` | **RC-6** A-7 | 하나의 `(ledger_record_sha256, execution_index)` 인가에 evidence run 2건을 붙여 제출 / 같은 쌍으로 `EXECUTION` 레코드를 2건 append | **차단** — 인가 1건 ↔ 실행 1회 ↔ run 1건의 1:1:1 위반 |
| **I-40** `[V2-C006 시정]` | **RC-6** A-8 · **RC-7** 인가→원장 | control이 `execution_index` 1·2·3을 인가했는데 원장·evidence에 1·3만 제출(2를 숨긴다) | **차단** — `execution_index` 조밀성 결번 + control 인가 수 `E = 3` ≠ `EXECUTION` 2건. `E`는 executor가 쓰지 못하는 자리에서 센다 |
| **I-41** `[V2-C006 시정]` — **잔여 명시** | **RC-6** 잔여 R-1 | 인가된 **하나의** id로 로컬에서 K회 실행한 뒤 결과가 가장 좋은 1회만 커밋한다 | **차단되지 않는다.** 저장소 안의 어떤 검사도 커밋되지 않은 로컬 실행을 볼 수 없다. 실패주입 대상으로 **등재하되 기대결과를 `통과`로 적는다** — 가드가 이것을 막는다고 주장하지 않기 위해서다. §1.11.2 잔여 위험 R-1 |
| **I-42** `[V2-C008 시정]` | **E-6b** ⑤ (LANE C `Q9-1`) | 로그인 축 신호가 확정 수준으로 관측된 step에 `auth_gate_kind = LOGIN` 기록 | **통과해야 한다** — 근거가 있는 확정 기록이다. 과탐 회귀검사 |
| **I-43** `[V2-C008 시정]` | **E-6b** ⑤ (LANE C `Q9-2`) | 본인인증 축 신호가 확정 수준으로 관측된 step에 `auth_gate_kind = IDENTITY_VERIFICATION` 기록 | **통과해야 한다** — 같은 이유 |
| **I-44** `[V2-C008 시정]` | **E-6b** ⑤ (LANE C `Q9-3`) | 본인인증 신호가 관측된 step에 `auth_gate_kind = LOGIN` 기록 (오분류 주입) | **차단** — 근거 교차검증. **규칙 E-6a는 이것을 잡지 못한다**(종류를 입력으로 받는다) |
| **I-45** `[V2-C008 시정]` | **E-6b** ① · **E-6a** (LANE C `Q9-4`) | 그 오분류로 `COMMUNICATION_ENTRY`에 `ENDPOINT_VIA_AUTH_GATE` · `endpoint_reached = 1` · 정수 `MPFED`가 생기는 궤적 | **차단** — 오분류의 **결과**가 실제로 뒤집힘을 만든다는 것을 증명하는 케이스다 |
| **I-46** `[V2-C008 시정]` | **E-6b** ③ (LANE C `Q9-5`) | 두 축 신호가 함께 확정 수준으로 관측된 gate를 `UNDETERMINED`로 기록하고 두 축 근거를 모두 저장 | **통과해야 한다** — 강제분류하지 않는 정본 경로다. 과탐 회귀검사 |
| **I-47** `[V2-C008 시정]` | **E-6b** ⑤ (LANE C `Q9-6`) | 확정하지 못한 gate를 `LOGIN`(또는 `IDENTITY_VERIFICATION`)으로 기록 | **차단** — 모호할 때 한쪽으로 넣는 기본값을 두지 않는다 |
| **I-48** `[V2-C008 시정]` | **E-6b** ④ (LANE C `Q9-7`) | `auth_gate_kind = UNDETERMINED` 인 gate를 `FINANCIAL_ACTION_ENTRY` · `COMMUNICATION_ENTRY` · `QUERY` 세 archetype에서 각각 판정 | **통과해야 한다** — 세 곳 모두 `AUTH_GATE_REACHED` · `endpoint_status_detail = NULL` 이어야 한다. 승격 경로가 남아 있으면 여기서 드러난다 |
| **I-49** `[V2-C008 시정]` — **LANE C 미대응** | **E-6b** ⑦ · **E-8** · **E-9** | `auth_gate_kind = UNDETERMINED` 인 step을 `auth_gate_detected = 0`으로 기록해 auth gate 유병률에서 누락 | **차단** — 승격을 막는 것과 관측을 지우는 것은 다르다. `auth_gate_observed` 합집합과 step 로그 재계산이 어긋난다(E-8 · E-9) |
| **I-51** `[V2-C008 시정 · C-2]` | **RC-6** 최초 run 적용 | 최초 E001 run을 원장 등재·control 인가 없이 수집해 정본 지정 | **차단** — `UNDECLARED`. `V2-C006` 판에서는 통과했던 경로다 |
| **I-52** `[V2-C008 시정 · C-2]` | **RC-6** A-6 (최초 run) | 최초 run을 임의의 `evidence_run_id`로 로컬에서 여러 개 만든 뒤 결과가 가장 좋은 하나를 제출 | **차단** — 유효 id는 `f`의 상뿐이다. **이 경로가 (b)에서는 열려 있었다** |
| **I-53** `[V2-C008 시정 · C-2]` — **잔여 명시** | **RC-6** 잔여 **R-1** (최초 run) | 인가된 **하나의** 최초 run id로 로컬에서 K회 실행한 뒤 1회만 커밋 | **차단되지 않는다.** I-41과 같은 부류이며 기준선에도 같은 크기로 남는다. 등재하되 기대결과를 `통과`로 적는다 |
| **I-50** `[V2-C008 시정]` — **잔여 명시** | **E-6b** 잔여 **GK-1** | 신호 사전이 실제 화면과 어긋나 판별기가 본인인증 gate를 **확정적으로** `LOGIN`이라 판단한다 | **차단되지 않는다.** 기록자와 판별기가 같은 사전을 쓰므로 사전이 틀리면 교차검증(⑤)이 침묵한다. **등재하되 기대결과를 `통과`로 적는다** — 가드가 이것을 막는다고 주장하지 않기 위해서다. §1.5.1a 잔여 **GK-1** |

**주입 케이스가 통과해야 하는 것을 일부러 넣었다** — I-4 · I-14, 그리고 `[V2-C008 시정]` I-42 · I-43 · I-46 · I-48이다. 차단만 태우면
**과탐(over-blocking)** 이 검증되지 않는다 — 규칙 S-3이 정당한 값을 막아 파이프라인을 세우는 것도
결함이며, `V2-C003` ssot F1이 지적한 무주지가 정확히 그 형태였다.

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
| `MAX_RECOLLECTION_RUNS_PER_WEB_TARGET`의 **확정값** (이 문서의 기본값 = **1**, 규칙 RC-1) `[V2-C004 시정]` | P-C 구현 → P-D(E000_V2) 검증 → 동결 |
| 로그인 gate ↔ 본인인증 gate **판별 기준의 서비스별 적용**(규칙 E-6a) `[V2-C004 시정]` · **gate 신호 사전의 토큰 집합**과 **각 축의 확정 수준**(규칙 E-6b ②③) `[V2-C008 시정]` | P-A endpoint codebook → P-B 동결 (§1.9 규칙 P-1) |

## 7. 금지사항 재확인

이 문서의 어떤 조항도 다음을 허용하는 것으로 읽혀서는 안 된다.

| # | 금지 |
|---|---|
| 1 | **`UNDETERMINED`를 `PASS`로 흡수하지 않는다** (laundering). 금지 전이 X-1은 **무조건**이다 — `evidence_gap` 값·`automation_grade`·reviewer 합의·arbiter 판정·사람 최종검토 어느 것도 예외가 아니다. `UNDETERMINED`에서 나가는 유일한 경로는 **새 evidence를 수집한 새 evidence run**이며(§1.11.2 · `02 §12`), 같은 evidence 재판정으로는 바꿀 수 없다(X-10). `FAIL`로 흡수하는 것도 같은 금지다(X-11) `[V2-C003 시정]` |
| 2 | **결측을 0으로 치환하지 않는다** (`01 §11`). 규칙 N-1~N-7 · X-5 · X-7. `endpoint_reached = 0`의 `MPFED`는 **`NULL`**이며 `0`도 예산 상한 `8`도 아니다. `rows_expected` 결측 8행 `[실측]`, `value` 결측 7행 `[실측]` 도 0이 아니다 |
| 3 | **상태와 수치를 분리한다** (`01 §11`). §1.0의 수준을 섞지 않는다. `app-only`는 **발견 시점에 따라** 관측 이전 적격성(`web_eligibility_status = EXCLUDED_APP_ONLY`)과 수집 시점 반증(`measurement_status = NOT_ELIGIBLE_AT_COLLECTION`)으로 나눠 기록하며(§0 7항 EXC-1 · §1.2), 어느 쪽도 접근성 `FAIL`로 세지 않는다 `[V2-C003 시정]` |
| 4 | **AI 라벨을 human gold라 부르지 않는다** (`00 §9` · `04 Gold Label`). 규칙 R-3. `reviewer_agreement`가 높아도 정확도가 아니다 |
| 5 | **인증을 gold label로 쓰지 않는다** (`00 §4 Axis C`). `certified_current`는 외부 참조축이며 정답이 아니다 |
| 6 | **수집 실패를 접근성 FAIL로 세지 않는다** (`02 §13`). 규칙 M-1 · X-4 |
| 7 | **새 연구기준을 만들지 않는다.** 이 문서는 허용값·산식·귀속 컬럼만 부여했다. 임계값(`Depth >= 3 = 나쁨` 등)을 만들지 않는다 (`00 §7` · `00 §14`) |
| 7-a | **수집 파라미터를 해석 임계값으로 읽지 않는다.** `A1` §2.1의 `MAX_ACTIVATIONS_PER_TASK = 8`은 수집 예산이며 `8단계 넘으면 접근성이 나쁘다`가 아니다 (`A1` §0.5 · §2.3 · 규칙 E-3) |
| 7-b | **세 축(A/B/C)을 단일 종합점수로 합산하지 않는다.** Depth·episode·popup을 KWCAG `FAIL`로 전환하지 않는다 (`A1` §0.4 · 전파 규칙 T-5) |
| 7-c | **`NED = 0`을 "진입이 쉽다"로 점수화하지 않는다.** 관측 사실일 뿐이다 (규칙 D-4) |
| 8 | **원본 `state/*.parquet`를 rename·migration·수정하지 않는다** (`01` 서두 · `03 Phase 3`). 규칙 V-1 · V-4 · V-5 |
| 9 | **`research/refcohort/**`(Pilot)은 `READ_ONLY`.** 규칙 V-8 |
| 10 | **예산 소진을 이유로 강제분류하지 않는다** (`00 §9`). 규칙 A-1 · X-6. §2.3의 3번 분기가 정본 경로다 |
| 11 | **auth gate를 endpoint로 세는 것은 두 archetype뿐이며, 그 두 행의 gate 절이 서로 다르다** — `FINANCIAL_ACTION_ENTRY`는 로그인 gate·인증 gate, `COMMUNICATION_ENTRY`는 **로그인 gate만**이다 (`00 §3` L1 표가 `또는 gate`를 준 행이 그 둘뿐이다). 다른 archetype으로도, `COMMUNICATION_ENTRY`의 **본인인증 gate**로도 확대하지 않는다 — 그 gate는 `AUTH_GATE_REACHED`(또는 `PERSONAL_DATA_REQUIRED`)로 남는다. 두 archetype에서도 gate를 **통과하지 않는다** — `00 §3 절대 제외`의 `로그인 이후`·`본인인증 이후`는 그대로다 (§1.5.1a 규칙 E-6 · **E-6a** · E-7) `[V2-C004 시정]`. **그리고 gate 종류를 확정하지 못했으면 승격시키지 않는다** `[V2-C008 시정]` — `auth_gate_kind = UNDETERMINED`는 archetype을 가리지 않고 `AUTH_GATE_REACHED`다(규칙 **E-6b**). 오분류의 위험은 **비대칭**이며(identity를 login으로 보면 없어야 할 endpoint가 생기고, 반대는 `MPFED`가 `NULL`로 남는다), 의심스러울 때의 기본값은 **승격하지 않는 쪽**이다. 승격만 막을 뿐 그 gate는 `auth_gate_detected = 1`로 남아 `auth gate` 유병률에서 사라지지 않는다 (규칙 E-8 · E-9) |
| 13 | **재수집으로 결과를 고르지 않는다** `[V2-C004 시정]`. `UNDETERMINED`의 유일 탈출구인 재수집은 상한(RC-1)·사전선언과 중단규칙(RC-2)·정본 run 선택규칙(RC-3)·미선언 배제(RC-4)·보고 의무(RC-5)·**선행 앵커(RC-6)**·**시도 전건 열거와 폐기 사유(RC-7)** 아래에서만 정본 지표에 반영된다 `[V2-C005 시정]`. **앵커 1건은 실행 1회를 인가하고, `evidence_run_id`는 그 인가에서 유도된다** `[V2-C006 시정]` — 인가 없이는 통과하는 id를 만들 수 없고(A-6), 인가 1건에 run은 하나뿐이며(A-7), 인가 수는 control이 독립적으로 센다(A-8). **인가 층은 재수집 run만이 아니라 최초(E001 baseline) run에도 적용된다** `[V2-C008 시정 · C-2]` — `최초 run은 선택할 대상이 없다`는 이전 판의 단언은 거짓이었으므로 철회했다(§1.11.2 RC-6). **다만 인가된 하나의 id로 로컬에서 여러 번 돌린 뒤 하나만 커밋하는 것은 저장소 내부 검사로 배제되지 않으며, 이는 재수집 run과 최초 run에 똑같이 적용되는 위험 부류(선별적 로컬 재실행)다** — §1.11.2 잔여 위험 R-1로 명시하며 닫혔다고 쓰지 않는다. **RC-5의 재수집 전후 병기는 그 부류의 탐지층이지 배제층이 아니다** — 기준선인 최초 run도 같은 부류에 열려 있다. **사전선언은 순서가 run 바깥에서 고정될 때에만 사전선언이다** — 결과를 본 뒤 지어낸 선언, 원장에 없는 run, 판정을 보고 붙인 폐기 사유는 전부 optional stopping이다 (X-14 ⑤~⑦). 원하는 판정이 나올 때까지 다시 재는 것, 판정 결과를 중단 조건으로 쓰는 것, 결과를 보고 정본 run을 바꾸는 것은 **optional stopping**이며 `00 §14`가 금지한 결론 유도다 (X-14). `impact_level`은 그래서 **결론 중립적**으로 정의된다(§1.8) — 재수집 우선순위가 `00 §11` 결론 방향을 따라가면 명세 자신이 편향을 지시하게 된다. **그리고 이 잔여는 문면으로 공표해야 한다** `[V2-C009 시정]` — 검증은 **커밋된 산출물에 한정**되고, 남은 경로는 **프로세스 통제**(단일 실행 잠금·단일 호출 커밋)와 **역할 분리**(수집자 ≠ 인가자 ≠ 감사자), **재수집 전후 값 병기 보고**에 의존하며, 이 잔여는 **독립 감사가 검토·수용한 것이며 해소된 것이 아니다**(규칙 RC-8 · 등재부 EXC-5). 수용됐으나 서술에서 빠진 잔여는 정직한 등재를 은폐로 되돌린다 |
| 14 | **두 endpoint 의미를 한 분포에 섞어 제시하지 않는다** `[V2-C004 시정]`. gate가 endpoint인 두 archetype에서 `MPFED` 계열 지표는 `endpoint_status_detail = ENDPOINT_VIA_AUTH_GATE` 여부로 **층별 병기**한다 (규칙 E-10). 층화는 **기존 지표를 한 번 더 산출하라는 요구**이며 새 분석 기준이 아니다 — `ExcessDepth`의 정본 산식은 `00 §7` 문면 그대로다. 어느 층이 더 좋다/나쁘다고 말하지 않는다 (`00 §14`) |
| 15 | **`NA`와 `UNDETERMINED`를 서로 바꿔 기록하지 않는다** `[V2-C004 시정]`. `NA`는 `적용 대상이 없음`(`01 §7` · `00 §4`)이고 `UNDETERMINED`는 `판단할 수 없음`이다. `verdict_state = NA` 행은 adjudication 4값 어느 것으로도 `UNDETERMINED`가 되지 않으며(T-6 우선 · X-15), `verdict_state = UNDETERMINED` 행은 `NA`가 되지 않는다(T-8 · X-13). 둘을 섞으면 §1.7 항등식 `applicable_count = pass_count + fail_count + undetermined_count`가 깨진다 |
| 12 | **Frame 수준 동결값을 관측이 조용히 덮어쓰지 않는다.** 수집 시점 반증은 §1.4.1 supersede로 **새 행**을 만들고 이전 행을 남긴다 (규칙 W-1 · T-11 · `02 §12`). 수집이 어렵다는 이유로 타겟을 표본에서 빼지 않는다 (X-12 · 규칙 W-2) `[V2-C003 시정]` |

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
