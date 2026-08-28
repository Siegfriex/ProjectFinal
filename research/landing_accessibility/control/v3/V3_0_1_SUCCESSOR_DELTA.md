# SSOT v3.0.1 — Successor Delta

지위 `SUCCESSOR_DELTA` · 선행 `SSOTV3/` v3.0 (unmodified, sha 20/20 검증)
발행 A · 2026-08-28 KST · 근거 `V3_REFREEZE_DECISION.md` §4

**이 문서는 v3.0 원본을 대체하지 않는다.** v3.0 은 byte 단위로 보존되며, 아래 항목만 v3.0.1 로 승계된다. 충돌 시 이 delta 가 우선한다.

---

## Δ1 — 09 `D3-06` 개정 (MODIFY)

**v3.0 원문**: 5 matched task families × 10 services = 50 candidate service-task units.

**v3.0.1**: 위를 유지하되, `MAIN50_FRAME_FROZEN` 이전에 다음 둘이 manifest 에 포함돼야 한다.

### Δ1-a  F5 날짜 fixture 절대화

`01_TASK_FAMILY_TARGET_FRAME_v3.0.md` §2 의 F5 fixture `날짜=T+1` 은 상대일자이며 target 별 수집일에 따라 달라진다. 요일·공휴일에 따라 운행편 구성 자체가 달라지므로, 관측된 flow 차이에 날짜 차이가 섞인다.

freeze 시 다음 중 **하나를 명시적으로 선택**해 manifest 에 기록한다.

- (A) 절대일자 1개를 고정한다. 모든 F5 target 이 같은 조회일자를 쓴다.
- (B) `T+1` 을 유지하되 F5 10 target 전부를 **동일 수집일** 안에서 수행하고 `collection_date_kst` 로 사후 검증한다. 날짜가 갈라지면 갈라진 target 을 재수집한다(새 run).

미선택 상태로 freeze 하지 않는다.

### Δ1-b  family 내 비독립성 층 사전등록

`05_ANALYSIS_PLAN_v3.0.md` §5 는 F5 에 ground/air 층을 둔다. F1 에는 층이 없다.

F1 10 = 시중은행 7 (NH · KB · 신한 · 하나 · 우리 · IBK · SC) + 지방은행 3 (BNK부산 · BNK경남 · iM). 지방은행은 공통 코어뱅킹/채널 플랫폼을 공유할 개연성이 있어 "10 개 독립 서비스"가 자명하지 않다.

→ F1 에 `시중 7 / 지방 3` 층을 **precheck 시작 전에** 사전등록한다. sensitivity 로만 보고하며 primary 분모를 바꾸지 않는다.

플랫폼 공유는 관측 없이 단정할 수 없으므로 이 층은 **가설이 아니라 사전등록된 민감도 축**이다. 결과를 본 뒤 층을 만들면 사후 분할이 된다 — 그것을 금지하기 위해 지금 등록한다.

## Δ2 — 09 `D3-08` 개정 (MODIFY)

**v3.0 원문**: APP_REQUIRED/APP_ONLY 는 primary frame precheck 에서 제외·사전 replacement.

**v3.0.1**: 원칙 유지. 추가로 **replacement 명부를 precheck 시작 전에 동결**한다.

`01 §1` 은 "collection 전에 교체"만 정하고 교체 후보를 언제 정하는지는 비운다. precheck 결과를 보고 대체재를 고르는 것은 — 채널 적격성이라는 제한된 정보일지언정 — 관측 후 표본 선택이다.

요구사항:

1. family 별 **순서가 매겨진 예비 명부**를 precheck 시작 전에 작성한다.
2. 명부를 target manifest 와 함께 hash 에 포함한다.
3. 교체는 **명부 순서대로만** 한다. 순서를 건너뛰면 사유를 기록하고 C 가 검증한다.
4. 명부가 소진되면 해당 family 를 `n<10` 으로 보고한다. **임의 보충하지 않는다.**
5. 결과(flow/label/depth 등)를 본 뒤의 교체는 어떤 경우에도 금지 — 이는 v3.0 00 §9 와 동일하며 여기서 재확인한다.

## Δ3 — 08 baseline SHA 갱신

`08_CURRENT_STATE_BASELINE_v3.0.md` 의 heads 표 중 3건이 stale 이다. 원본을 수정하지 않고 여기에 갱신본을 둔다. 측정 `git ls-remote origin` @ 2026-08-28T02:07 KST.

| plane | branch | 08 기재 | v3.0.1 실측 |
|---|---|---|---|
| A | `control/landing-orchestrator` | `8f413527` | `5c22faebaeb6699049fc9af5646f8b492b6a4068` |
| B | `claude-b/diag-pilot-integration` | `01041bc2` | `01041bc213a2e61f6cb224e469087d9a11324349` (불변) |
| B W2 | `claude-b/w2-rf-detector` | `b28aaa5c` | `b28aaa5cad736082a6a76c0ca6a9f6be330bbcfb` (불변, 동결) |
| C | `claude-c/assurance-current` | `1baa865b` | `1baa865b…` (불변) — **실작업은 `claude-c/assurance-v21 @ 807192bcf5cb9591e3a82bd86bef5338bd719be3`** |
| D | `claude-d/research-sandbox-v21` | `bcaa634b` | `cf05035cc14a2f1a3ddcaff61c805aa6e9cafb19` |
| promoted main | `research/landing-accessibility-main` | `bc0b7a08` | `bc0b7a087faf2328cbafdfa9b40bd426c5080d7d` (불변) |
| pilot manifest | `control/pilot-manifest` | `54a0c7a4` | `54a0c7a4149adc17c086e398be83bc7c117a66b0` (불변) |

**모든 변동은 fast-forward 이며 rewrite 는 없다.** 계보 검증은 `V3_CURRENT_STATE_RECONCILIATION.md` §1.

## Δ4 — promoted main 참조 규칙 (신규)

로컬 `refs/heads/research/landing-accessibility-main` = `32460b87` 이며 정본 `origin/…` = `bc0b7a08` 의 **조상**이다. bare 브랜치명으로 참조하면 뒤처진 SHA 를 얻는다.

→ promoted main 은 `origin/research/landing-accessibility-main` 또는 exact SHA `bc0b7a087faf2328cbafdfa9b40bd426c5080d7d` 로만 참조한다. **bare 브랜치명 금지.** 전 평면 즉시 적용.

## Δ5 — 15 티켓 스키마 전환 규칙 (신규)

`15_TICKET_PROTOCOL_SCHEMA_v3.0.json` 은 기존 141 티켓과 정합하지 않는다. 결손: `created_at_kst` 139 · `status` 136 · `scope` 112 · `base_sha` 31 · `claim_kind` 5 · `priority` 3. enum 밖 `type` 34건/14종.

**소급 개정하지 않는다.** 발행된 티켓은 발행 시점의 기록이며, 사후 수정하면 그 시점에 무엇이 알려져 있었는지가 소멸한다. B·D 가 각각 독립적으로 같은 결론에 도달했고 A 가 승인한다.

v3 채택 이후 발행분부터 15 스키마를 적용한다. 기존 type 의 매핑:

| legacy type | v3 type | payload 하위종별 |
|---|---|---|
| `WORK_REQUEST` | `DIRECTIVE` | — |
| `GO_NO_GO` · `P0_RELEASED` · `E001_RELEASE` | `DIRECTIVE` | `decision_class` |
| `SUPERSEDE` | `DIRECTIVE` | `supersedes: [...]` |
| `HARD_STOP_CANDIDATE` | `BLOCKER` (P0) | — |
| `FACTUAL_CORRECTION` | `FACT_CORRECTION` | — |
| `RESEARCH_FINDING` · `ADDENDUM` | `FINDING` | `finding_class` |
| `VALIDITY_RISK_CANDIDATE` | `FINDING` | `finding_class: VALIDITY_RISK` · P1 이상 |
| `RESEARCH_QUESTION` | `FINDING` | `finding_class: OPEN_QUESTION` |
| `MART_READY` · `STATS_READY` · `FINAL_READY` | `COMPLETION` | `readiness_class` |
| `STATUS` | `FINDING` | `finding_class: STATUS_REPORT` |

`VALIDITY_RISK_CANDIDATE` 를 `FINDING` 으로 접으면서 우선순위를 잃지 않도록, `finding_class: VALIDITY_RISK` 는 **P1 이상으로만** 발행한다. D 의 `open_question_for_A` 에 대한 답이다.

## Δ6 — E Pathfinder 평면 편입 (신규)

근거 Director "ABCD NOTICE — Claude E Pathfinder Integration" · 접수 2026-08-28 KST

### Δ6-a  스키마 enum 확장

`15_TICKET_PROTOCOL_SCHEMA_v3.0.json` 의 `from` / `to` / `cc` enum 은 `[A,B,C,D,DIRECTOR]` 이며 **E 가 없다.** E 발신·수신 티켓은 현재 스키마 위반이 된다 (C-FINDING-022252 관측).

원본을 수정하지 않는다. v3.0.1 에서 enum 을 `[A,B,C,D,E,DIRECTOR]` 로 확장한다.

REAL 을 수반하는 E 티켓은 다음 필드를 **추가 필수**로 한다.

- `real_scope_id` — A 가 release 한 scope 식별자
- `release_doc` — 해당 release 문서 경로
- `target_manifest_sha256` — 바인딩된 manifest hash
- `allowlist_ref` — target allowlist 참조
- `task_contract_sha256` — task/endpoint contract hash

다섯 중 하나라도 없으면 E 의 REAL 요청은 성립하지 않는다. 이는 A/B 의 기존 REAL 바인딩과 같은 구속이다.

### Δ6-b  E 의 현재 REAL 권한 — 없음

E 는 평면으로 존재하되 **현 시점 REAL scope 가 0 이다.** `V3_MAIN50` · `V3_FLOW_PILOT_10` · `ELIGIBILITY_PRECHECK` 는 전부 미발행이며, `V2_DIAGNOSTIC` 12 는 B 의 구동기에 바인딩된 scope 이지 E 의 것이 아니다.

어떤 평면도 E 에게 REAL 을 요청할 수 없다 — B 도, C 도, D 도. A 의 release 가 선행해야 한다.

또한 B 가 관측한 대로 **E 세션은 아직 실재하지 않는다.** 어떤 평면도 E 에 의존하는 구현을 선행하지 않는다. 공지가 존재한다는 것과 E 가 작동한다는 것은 다르다 — 이 세션의 반복 결함군이다.

### Δ6-c  E route 는 B 의 실행 대본이 아니다 — primary construct 보호

**제기**: T-B-V3-E-ACK-001. Director 공지는 B 가 E 에 `route replay` 를 요청할 수 있다고 한다. 그런데 v3 00 §7 은 `task_flow_sequence` 를 "서비스 자체 navigation/task 구조"로 정의하고, 05 §2-E 는 sequence signature 와 정규화 편집거리로 서비스 간 divergence 를 측정한다.

E 가 경로 X 를 찾고 B 가 X 를 재생하면 B 가 측정한 flow 는 X 다. 한 서비스에 도달 가능한 경로가 둘 이상이면 **E 의 선택이 B 의 측정치가 되고 그것이 family 내 sequence divergence 로 집계된다.** v3 의 primary outcome 이 정확히 sequence 이므로 이것은 primary 결과 오염이다.

**판정**

1. **B 는 E 의 route 를 실행 대본으로 재생하지 않는다.** B 의 입력은 frozen `task_id` + `endpoint_contract` 뿐이며, B 는 자기 Scout→Freeze→Replay 를 처음부터 수행한다.
2. E 산출의 허용 용도는 다음으로 한정한다 — endpoint reachability 사전 확인 · auth gate 위치 사전 인지(안전 준비) · drawer/reveal 존재 확인(수집기 결함과 사이트 구조의 구분) · obstruction/dismiss 요구 사전 인지. 전부 `E_ROUTE_ID` lineage hint 로만 기록한다.
3. 금지 — E 의 selector 를 그대로 클릭 · E 의 action sequence 재생 · E 가 찾은 경로를 B 의 `task_flow_sequence` 로 기록.
4. 공지의 `route replay` 는 **E 가 자기 경로를 다시 밟아 증거를 재획득하는 것**으로 읽는다. B 가 E 의 경로를 밟는 것이 아니다.
5. E route 와 B route 가 갈리면 **B 의 것이 `task_flow_sequence` 다.** divergence 는 결함이 아니라 예상된 산출이며 별도 finding 으로 처리한다 — Director 가 C 에게 같은 지시를 이미 내렸다.

### Δ6-d  route 선택 정책은 계측 파라미터다 — P3 요구사항

Δ6-c 의 위험은 E 고유가 아니다. **B 의 Scout 도 경로가 여럿일 때 하나를 고른다.** E 와의 차이는 균일성에 있다.

matched comparison 이 성립하려면 **경로 선택 규칙이 50 target 전체에 동일하게 적용**돼야 한다. 어떤 target 은 E 가, 어떤 target 은 B 가 길을 열거나, target 마다 다른 휴리스틱이 쓰이면 서비스 간 divergence 에 정찰자 행동이 섞인다.

→ **P3 FLOW_ENGINE_QUALIFICATION 통과 조건에 추가한다**: B 의 Scout 는 문서화된 결정론적 경로선택 정책(후보 순위 규칙 · 동점 처리 · 최단경로 정의 · 중단 조건)을 갖고, 그 정책이 P4 이전에 동결돼야 한다. 정책 없이 수집한 sequence 는 서비스 구조의 측정치로 해석하지 않는다.

### Δ6-e  C·D 의 E 사용

- **C**: E 를 증거 획득 operator 로만 쓴다. 판정자로 취급하지 않는다. E artifact hash 와 raw evidence 는 C 가 독립 계산한다. **B 와 E 가 같은 도구·같은 가정을 공유하면 둘의 일치는 독립성의 증거가 아니다** — C 가 이미 대조군으로 잡았고 A 가 승인한다.
- **D**: `COUNTEREXAMPLE_REQUEST` 가능하나 REAL 이면 A scope 선행. D 는 E 결과를 자기 결론으로 즉시 broadcast 하지 않는다. `D 분석 → C replication → A authority` 구조를 유지한다.
- **공통 금지 재확인**: outcome 기반 표본교체 · endpoint 변경 · target family 변경 · credential/transaction · CAPTCHA 우회 · app-only 강제진입 · holdout 노출 · E 결과 self-approval. **E 가 길을 못 찾았다는 이유로 frozen target 을 교체하지 않는다.**

## Δ7 — THREE_TURN_RUNBOOK 분류 (신규)

`SSOTV3/THREE_TURN_RUNBOOK.md` · 3169B · sha256 `34f14e13231eb88b156427035d149da718c36584aa64b9973781a965c2eb9b60` · mtime 2026-08-28T02:11 (pack 원본 20 파일은 01:52:49~50)

**분류: pack 권위 밖 운영 runbook.** 매니페스트에 등재하지 않는다 — 매니페스트는 Director 가 준 bytes 이며 A 가 항목을 추가하면 팩 해시가 A 의 손을 탄다. 20/20 무결성은 A·B·C 재검증으로 유지된다.

운영 조항으로 채택하되 **한 가지를 명시한다** (T-B-V3-FINDING-001 요청):

> **phase 자율전이는 REAL release 를 대체하지 않는다.**

runbook 의 "A 는 같은 Wave 내부 phase 사이에서 Director 추가 승인을 기다리지 않는다"는 **phase 전이**에 관한 것이지 REAL 개시에 관한 것이 아니다. v3 00 §13 과 D3-20 이 "v3 문서 자체가 새 REAL 실행권한을 주지 않는다"고 정하며, runbook 의 Director interrupt 2항도 "사전등록 범위 **밖**으로의 확대"만 Director 로 올린다고 할 뿐 범위 안의 REAL 이 자동으로 열린다고 하지 않는다.

→ 어떤 phase 전이도 REAL 개시 근거가 아니다. REAL 은 해당 scope 의 release 문서가 `RELEASED` 이고 manifest hash 가 바인딩되고 A 의 명시 GO 가 있을 때만 실행한다. `V2_DIAGNOSTIC` 12 가 RELEASED 인데도 실행되지 않고 있는 것이 이 기준의 현행 실례다.

**hard stop 어휘**: runbook 과 `T-A-V3-P0-001` 의 어휘가 다르나 일대일 대응한다(scope leak↔wrong scope · task contract drift↔task/outcome leakage · evidence mutation↔evidence overwrite). 발행 시점 정본은 `T-A-V3-P0-001` 의 6종이었다. B·C 가 같은 판단을 했다.

> **SUPERSEDED — 정본은 Δ19-R9 의 8종이다.** 6종은 이 문서 발행 시점의 기록으로 남긴다. C 가 색인 대조에서 이 불일치를 잡았다(`C-FINDING-040011`).

**partial failure policy 정합**: runbook 의 "P5 실행 중 실패한 target 은 표본 교체 금지, 실패/결측 사유로 보존"은 Δ2 및 v3 01 §1 · 05 §5 와 같은 방향이며 모순 없다.

## Δ8 — 조작적 정의 7건 사전등록 (신규)

발행 `T-A-V3-STEP1-003` @ A `4e3ba3cf` · **REAL 접속 누적 0건 시점**. 전부 result-blind 다.
제기: 6건 A 평면 A-Contract lane · 1건 D-V3-FINDING-007(C 독립 확인).

| # | 항목 | 확정 |
|---|---|---|
| R1 | replacement 사유 커버리지 | **5번째 사유를 만들지 않는다.** 과업 의미 불일치는 교체 사유가 아니라 `TASK_COMPARABILITY_CONCERN` finding + ABSTAIN. 결측을 결측으로 보고하는 것이 표본을 바꾸는 것보다 정직하다 |
| R2 | `AUTH_GATE` 의 분모 지위 | 성공/실패가 아니라 terminal 관측값. **진입 flow 지표는 AUTH_GATE 여부와 무관하게 산출**하고 endpoint 의존 지표만 flow-evaluable n 을 쓴다. 빼면 '인증이 일찍 걸리는 서비스'가 진입구조 분석에서 사라진다 |
| R3 | secondary task 격리 | `task_role` = PRIMARY / SECONDARY_REPEATED. family 집계는 PRIMARY 만. 필터 조건 문자열을 산출에 남긴다 |
| R4 | 분모 사슬의 교체 이력 | `candidate 10 → [replaced k, 사유별] → frozen 10 → attempted → evidence-bearing → flow-evaluable`. k=0 도 명시 |
| R5 | fixture 입력수단 | fixture 는 문자열이 아니라 **의미 명세**. 서비스가 먼저 제시하는 수단을 쓰고 `fixture_input_mode`(FREE_TEXT/DROPDOWN/MIXED/MAP_PAN/OTHER)를 기록. 절차의 모호함을 관측 변수로 바꾼다 |
| R6 | F1 분산 비대칭 · 이름 충돌 | F1 auth 절단을 사전등록 민감도로 등록. `AUTH_GATE`/`ABSTAIN` 은 개명하지 않고 **필드 한정 의무화**(`endpoint_status=` / `action_token=`), C 가 GATE 3 에서 검사 |
| R7 | `entry_zone` 조작적 정의 | 아래 |

### Δ8-R7 `entry_zone` 임계값

수집에는 blocking 이 아니다 — 04 §6 이 원좌표 보존을 정했고, 원좌표가 남으면 zone 은 재도출 가능하다.

```
y < 1/3          → TOP        (TOP 안에서만 x 삼등분)
1/3 ≤ y < 2/3    → MID
y ≥ 2/3          → BOTTOM

TOP 안:  x < 1/3 → TOP_LEFT · 1/3 ≤ x < 2/3 → TOP_CENTER · x ≥ 2/3 → TOP_RIGHT
MID·BOTTOM 은 x 삼등분하지 않는다 (codebook 에 MID_LEFT 류가 없다)
경계는 하한 포함·상한 배제 [a, b) — 두 축에 균일하게 적용한다
         y = 1/3 → MID · y = 2/3 → BOTTOM
         TOP 안에서 x = 1/3 → TOP_CENTER · x = 2/3 → TOP_RIGHT
좌표 기준 = control bbox 중심 / viewport 390×844, 해당 state 기준
```

**구조 우선**: `FLOATING`(position fixed/sticky, 일반 흐름 이탈)과 `DRAWER`(reveal 을 요구하는 nav_container 내부)는 기하보다 우선한다. 둘 다면 `DRAWER` 우선 — reveal 필요 여부가 사용자에게 더 큰 구조적 부담이다. override 가 걸려도 `entry_x_norm`/`entry_y_norm` 은 그대로 저장한다. **요약값이 원자료를 덮지 않는다.**

임계값을 나중에 바꾸는 것은 재수집이 아니라 재도출이다. 그러나 **선언된 민감도로만** 허용하고 원 임계값 결과와 병기한다 — 결과를 보고 조용히 바꾸면 조작화 fitting 이다.

## Δ9 — `activation_depth` 토큰 귀속 (신규)

발행 `T-A-V3-STEP1-006`. 제기: `T-B-V3-DR-001` · `T-B-FC-013`. 관측 0건 시점.

**충돌이 아니라 한 문장의 중의성이었다.** 03 §6 과 04 §5 의 제외 목록 어디에도 submit 이 없고, 03 의 포함 목록 `link/button/tab/menu open` 에 submit control 은 button 으로 들어간다. 모호함은 03 마지막 문장이 typing 과 submit 을 묶어 언급한 데서 왔다 — typing 이 depth 에서 빠지니 어딘가 남아야 한다는 말이지 submit 을 빼라는 말이 아니다.

**일반 기준**: `activation_depth` 는 사용자가 control 을 **의도적으로 활성화해 상태 전이를 일으킨** 토큰의 수다. ① 의도적 조작인가 ② control 활성화인가 ③ 상태가 전이되는가.

| 구분 | 토큰 |
|---|---|
| **포함 (10)** | OPEN_GLOBAL_MENU · OPEN_LOCAL_MENU · SWITCH_TAB · EXPAND_ACCORDION · SELECT_CATEGORY · SELECT_FUNCTION · **SUBMIT_QUERY** · SELECT_RESULT · OPEN_ITEM_DETAIL · OPEN_PLACE_DETAIL |
| **제외 (5)** | INPUT_QUERY(타이핑) · DISMISS_OBSTRUCTION(명시 제외) · AUTH_GATE(활성화가 아니라 마주친 상태) · ENDPOINT_REACHED(종결 표지) · ABSTAIN(판정 유보) |
| **조건부 (3)** | SELECT_ORIGIN · SELECT_DESTINATION · SELECT_DATE — `fixture_input_mode` 로 갈린다. picker/dropdown/calendar 활성화면 포함, 자유입력 타이핑이면 제외. `depth_conditional_tokens` 에 근거를 남긴다 |

submit 을 빼면 검색어를 넣고 조회를 눌러야 진입하는 서비스와 control 을 바로 누르면 되는 서비스가 같은 depth 를 갖는다. **실재하는 구조 차이를 지우는 것이며 그것이 v3 가 재려는 차이다.** 3탭 달력과 텍스트 한 줄도 마찬가지다.

이 규칙은 검색 기반 family(F2·F3·F5)의 depth 를 F1·F4 보다 높인다. 결함이 아니다 — 사실이다. 사전등록으로 기록한다.

**방향은 토큰이 아니라 변수다**: `OPEN_RIGHT_DRAWER` 는 canonical 18종에 없다. `OPEN_GLOBAL_MENU`/`OPEN_LOCAL_MENU` + `nav_container_type=RIGHT_DRAWER` + `reveal_direction=RIGHT` 로 표현한다. 방향을 토큰에 넣으면 sequence signature 가 방향까지 포함해 갈라져 '같은 구조 다른 방향'과 '다른 구조'가 편집거리에서 구분되지 않는다. **상위 지시와 SSOT 가 다르면 SSOT 를 따른다.**

## Δ10 — 수집 스키마 확정 3건 (신규)

발행 `T-A-V3-STEP1-007`. 제기: `D-V3-FINDING-008` blocking. 셋 다 **수집 전에만 고칠 수 있는 것**이다.

### Δ10-R11 `terminal_reason` 동반 필드

`endpoint_status` 7값으로는 실패 사유가 분해되지 않는다 — `BLOCKED` 가 WAF·challenge·timeout 을, `PUBLIC_WEB_UNOBSERVABLE` 이 채널 부재와 과업 surface 부재를 삼킨다. disabled·inert·forbidden action 은 대응 값이 없다.

enum 을 바꾸지 않고 동반 필드를 둔다. 13값: `TIMEOUT · WAF_BLOCK · ACTIVE_CHALLENGE · NO_PUBLIC_MOBILE_WEB · TASK_SURFACE_ABSENT · APP_REQUIRED · CONTROL_DISABLED_OR_INERT · FORBIDDEN_ACTION_REQUIRED · AUTH_REQUIRED · EVIDENCE_DEFECT · REPLAY_BROKEN · AMBIGUOUS_MULTIPLE_CANDIDATES · OTHER`

모든 terminal 은 두 필드를 다 갖는다. `OTHER` 는 note 필수. 허용 조합표를 B 가 명시하고 C 가 검증한다 — 불가능 조합(`REACHED × TIMEOUT`)은 스키마가 거부한다.

`CONTROL_DISABLED_OR_INERT` 는 `presence ≠ operative` 결함군에 대응한다 — control 이 있는데 작동하지 않는 것을 '없음'으로 접지 않는다.

### Δ10-R12 sequence 거리 정규화

**primary = `max(len(a), len(b))`.** sum(len) 과 Yujian-Bo 도 저장하되 단일 보고에는 primary 만 쓴다.

같은 pair 가 정규화에 따라 1.0 / 0.5 / 0.667 로 갈린다. **v3 의 primary outcome 이 sequence 거리이므로 이 선택 하나가 primary 결과를 바꾼다.** 관측 후에 고르면 결과를 보고 지표를 고른 것이다.

군집·MDS 를 수행할 때는 **Yujian-Bo 를 병기한다**(삼각부등식을 만족하는 진짜 거리). 지금 선언한다 — 나중에 군집 결과가 마음에 안 들어 지표를 바꾸는 일이 없도록.

### Δ10-R13 `auth_gate_stage` = `UNDETERMINED` 추가

- `NONE` = **관측했고, auth gate 가 없었다.** 적극적 주장이며 증거를 요구한다.
- `UNDETERMINED` = 판정할 수 없었다.

이것이 이 세션의 중심 결함군이다 — **증거의 부재를 부재의 증거로 적는 것.** 둘을 구분하지 않으면 관측하지 못한 것이 '인증 없음'으로 집계돼 auth 발생률이 체계적으로 과소추정된다.

**전 변수에 적용한다**: 어떤 변수든 '없음'을 적으려면 관측했다는 증거가 있어야 한다. 판정불능 값이 없는 변수를 발견하면 즉시 올린다. `UNDETERMINED` 는 분모에서 빼지 않고 별도 범주로 보고한다 — 빼면 그 자체가 selection 이다.

### Δ10-R14 fixture 해석 오류는 변이 검사가 못 잡는다

D 자기 기술: fixture 는 워커가 정의를 읽고 만든 것이라 정의를 오독했으면 fixture 도 같이 틀린다. 변이 검사는 구현 오류만 잡는다.

B 에게도 같다. **GATE 1 에서 C 는 B·D 의 fixture 를 쓰지 않고 SSOT 원문에서 자기 fixture 를 파생한다.** C 의 fixture 가 다른 결과를 내면 그것이 해석 불일치 신호다.

## Δ11 — 버스 구조 사실 (신규)

발행 `T-A-V3-STEP1-008`. 출처 A-Bus lane, 스냅샷 `2026-08-28T02:52:34`.

**이 버스는 GO_NO_GO·BLOCKER 를 ACK JSON 본문 안에 결정을 담아 해소한다.** completions/ 파일로 하지 않는다. `completions 파일 없음 = 미해결` 로 읽으면 거짓 양성이 대량 발생한다 — BLOCKER 15건과 `decision_required` 12건 전수 내용검사에서 전부 실질 판정이 실려 있었다.

구조를 바꾸지 않는다. 대신 **버스를 읽는 모든 도구는 ACK 본문을 검사한다.** 파일 존재만 세면 틀린다.

v2.1 기간의 dangling reference(ACK 18 + completion 10)와 orphan dependency 1건은 **소급 생성하지 않는다** — 없는 티켓을 지금 만들면 사후 날조다. v3 이후 발행분은 ticket 파일 없이 ACK·completion 을 만들지 않으며 C 가 검증한다.

**lane 산출을 인용할 때는 측정 시각을 함께 인용한다.** A-State 와 A-Bus 둘 다 측정 중에 대상이 바뀌는 것을 관측했다. 시각 없는 lane 인용은 하트비트 SHA 를 근거로 쓰는 것과 같은 오류다.

## Δ12 — 공유 독해 위험은 A 에게 더 크게 걸린다 (신규)

발행 `T-A-V3-STEP1-009`. 제기: `T-B-V3-FINDING-002` (B 자기 등재). D 도 자기 5 lane 에 같은 구조가 있음을 확인했다.

**B 의 진단**: W5A~W5G·W1 8 lane 이 전부 B 가 쓴 지시문 계보에서 나왔다. B 가 SSOT 를 오독하면 8 lane 이 같은 오독을 공유한다. lane 분리는 **구현 오류**와 **파일 충돌**을 막지 해석 오류를 막지 않는다.

**A 에게는 더 위험하다**:

> B 가 오독하면 C 의 독립 fixture 가 갈려서 신호가 난다.
> **A 가 오독하면 그것이 정의가 된다.** 모든 평면이 그 정의를 따르므로 내부 일관성은 완벽해지고 아무 신호도 나지 않는다 — 일관되지만 틀린 계약이 만들어진다.

이 세션에서 A 는 이미 네 번 분석 오류를 냈고 전부 **다른 평면이** 잡았다: `F-A1b`(파일 크기로 degenerate 판정) · `D-R0-45`(순환 분모) · `D-R0-57`(필터 누락 조인) · `T-A-FC-003`(존재하지 않는 경로에 grep 을 걸고 0건을 여섯 번 보고).

### A lane 산출 중 어느 것이 살아남는가

| 층 | 판단 |
|---|---|
| 기계적 대조 | lane1 의 매니페스트 정합성(F4 예비 URL 중복), lane2 의 `RELEASED` 잔존, A-State 의 E 브랜치 미공개 — **A 의 독해와 무관하게 참이다** |
| 해석 의존 | lane_A_CONTRACT 의 8개 질문 판정, Δ8~Δ11 의 조작적 정의 — **취약한 층이다** |

### R15 — A 의 판정은 근거 원문을 축자 인용한다

인용이 있으면 어느 평면이든 같은 구절을 읽고 다른 결론에 이를 수 있다. 없으면 A 의 결론만 남고 그것이 어디서 왔는지 검증할 수 없다.

Δ9 가 표준 형태다 — 03 §6 과 04 §5 의 목록을 그대로 옮기고 "두 제외 목록 어디에도 submit 이 없다"를 보였다.

**Δ8-R1 과 Δ8-R2 는 논증 중심이고 축자 인용이 얇다.** 소급 수정하지 않되 이 두 건에 대한 반론을 특히 환영한다.

### R16 — A 판정에 대한 반론은 권위 불복이 아니다

A 의 판정은 권위다. 그래서 평면들이 **동의해서가 아니라 권위라서** 따를 수 있고, 그러면 A 의 오독이 검출되지 않는다.

어느 평면이든 A 의 조작적 정의가 SSOT 원문과 다르게 읽힌다고 판단하면 `FACT_CORRECTION` 을 발행한다. 근거는 "A 의 판정이 마음에 들지 않는다"가 아니라 **"A 가 인용한 그 구절을 내가 읽으면 다른 결론이 나온다"** 여야 한다 — 같은 원문, 다른 독해.

A 는 그런 정정을 받으면 자기 판정을 방어하기 전에 **두 독해가 어디서 갈렸는지**를 먼저 낸다. B 가 GATE 1 에 대해 스스로 약속한 것과 같은 처리다.

### 무엇이 실제로 덮는가 — 그리고 무엇이 덮이지 않는가

- **B 층**: C 의 독립 fixture 파생(Δ10-R14). B 는 C 의 fixture·기대값을 보지 않는다. C 는 SSOTV3 원문에서만 파생했음을 확인했다.
- **A 층**: 네 평면이 A 의 판정을 각자 SSOT 원문과 대조한다. R15 의 축자 인용이 그것을 가능하게 한다.
- **덮이지 않는 것**: A 와 네 평면이 **모두** 같은 구절을 같게 오독하는 경우. 이 구조 안에서 잡을 수 없다. **최종 보고의 known limitation 에 넣는다.**

덮인다고 말하지 않는다. B 도 "8 lane 병렬이 이 위험을 덮는다고 주장하지 않는다"고 했다. 같은 정직함을 A 에게도 적용한다.

**C 에 대한 추가 지시**: GATE 1 에서 B 와 갈린 항목을 구현 결함이 아니라 **해석 불일치 후보**로 먼저 분류하라. 구현 결함으로 단정하면 B 가 코드를 고치고 해석 차이는 그대로 남는다.

## Δ13 — 근거 없는 철회 (신규)

발행 `T-A-V3-STEP1-010`. 제기: `T-B-V3-FINDING-003`.

B 의 worker 가 "지시받지 않은 범위축소를 스스로 했다"고 자기정정했으나 **그 지시는 B 가 실제로 보낸 것이었다.** 수용했다면 지시대로 만들어진 코드를 폐기했을 것이다.

**이것은 이 세션 중심 결함의 거울상이다.** 지금까지 다룬 것은 증거 없이 *주장*하는 것이었다 — A 의 존재하지 않는 경로 grep, B 의 `created_at` 을 순서 증거로 사용, D 의 파싱 결함 오귀속. 이번 것은 증거 없이 *철회*하는 것이다.

### R17 — 철회는 주장과 같은 근거를 요구한다

- **정정하는 쪽**: 무엇이 틀렸는지뿐 아니라 **어떻게 그것을 알았는지**를 함께 낸다. 기억·인상·재구성은 근거가 아니다.
- **받는 쪽**: 자기신고를 액면가로 수용하지 않는다. 원 기록과 대조한 뒤 수용한다.

B 의 근거가 옳은 종류다 — `w5d1` 문자열은 B 가 그 메시지에서 처음 만든 것이고 다른 어디에도 없다. worker 가 발명해 글자 단위로 일치할 수 없다. **B 는 기억이 아니라 worker 산출물에 박힌 문자열을 썼다.** 기억을 근거로 삼았다면 그것은 T6 이며 `T-B-FC-012` 와 같은 오류였다.

### A 가 만든 유인

이 세션은 자기정정을 반복해서 칭찬했다. A 가 그렇게 했다. 그 유인에는 실패 양식이 있다 — **과잉 정정**. 자기신고가 보상받는 환경에서는 확실하지 않은 것도 신고하는 쪽으로 기울고, 신고 자체가 신뢰 신호가 되면 검증 없이 수용된다.

칭찬의 대상은 "자기정정을 했다"가 아니라 **"근거를 갖춘 자기정정을 했다"** 이다. 규율을 약화하는 것이 아니라 근거 요구를 양방향으로 동일하게 적용한다.

## Δ14 — C 사전등록 5건 판정 (신규)

발행 `T-A-V3-STEP1-011`. 제기 `C-DECISION_REQUEST-031138`. **5건 전부 C 의 독해 채택.**

| id | 판정 | 근거 |
|---|---|---|
| P-06 | `SWITCH_TAB` 은 reveal 아님 → `menu_dependency` 0 | 04 §5 기준은 `OPEN/REVEAL 계열`. 탭 control 은 이미 보였고 전환은 숨은 control 을 드러내지 않는다. `nav_container_type` 에 tab 없음. `menu_dependency_incl_tab` 민감도 병기 |
| P-09 | sequence 기반 → 1 | 04 §4·§5 두 곳이 `endpoint 이전에 존재하는지` 로 일치 |
| P-13 | `AFTER_TASK_SELECT` | 아래 단일 규칙 |
| P-14 | `AFTER_TASK_SELECT` | 아래 단일 규칙 |
| P-17 | `PUBLIC_WEB_UNOBSERVABLE × TASK_SURFACE_ABSENT`, token 은 별개 층 | 04 §2 / §4, Δ8-R6 Q8 |

### P-09 의 실재하는 긴장 — 덮지 않고 기록한다

`10_GLOSSARY` 는 다르게 읽힌다: "Menu Dependency | **task control이 바로 보이지 않고** reveal/menu action이 필요한지."

**04 codebook 이 이긴다** — 04 는 frozen 정의(T3), 10 은 산문(T5). 그리고 glossary 가 가리키는 개념은 다른 변수가 이미 담는다: `nav_container_depth`(task control 노출 전 reveal 수), `s0_task_control_visible`(최초 viewport 가시성). 두 개념을 한 변수에 접으면 둘 다 흐려진다.

10 을 근거로 다르게 읽는 것은 **정당한 R16 반론**이다.

### auth_gate_stage 단일 위치 규칙 (P-13·P-14 를 함께 푼다)

00 §6 과 03 §7 은 어휘만 주고 경계 규칙이 없다. A 가 메운다.

- `BEFORE_TASK_DISCOVERY` — `AUTH_GATE` 이전에 과업 특이적 토큰이 **하나도 없다**. 일반 navigation(`OPEN_*_MENU` · `SWITCH_TAB` · `EXPAND_ACCORDION` · `DISMISS_OBSTRUCTION`)만 있거나 아무것도 없음
- `AFTER_TASK_SELECT` — 과업 특이적 토큰이 **하나 이상** 선행하나 endpoint contract 미충족
- `AT_ENDPOINT` — endpoint surface 가 **인증 없이 렌더된 뒤** 그 내용 접근에서 gate

과업 특이적 토큰 10종: `SELECT_CATEGORY · SELECT_FUNCTION · INPUT_QUERY · SELECT_ORIGIN · SELECT_DESTINATION · SELECT_DATE · SUBMIT_QUERY · SELECT_RESULT · OPEN_ITEM_DETAIL · OPEN_PLACE_DETAIL`

세 단계가 재는 것은 **사용자가 과업 의도를 표현할 기회를 얻기 전에 막혔는가**다. 하나의 규칙이 두 사례의 답을 낸다 — 사례별 판단이 아니다.

`ABSTAIN`(모른다)과 `TASK_SURFACE_ABSENT`(없다고 안다)를 구분한다. R13 의 `NONE` 대 `UNDETERMINED` 와 같은 논리다.

## Δ15 — 04 codebook 공백 6건 판정 (신규)

발행 `T-A-V3-STEP1-012`. 제기 `T-B-V3-DR-002`.

### GAP-07 이 핵심 — 행이 자기 시점을 선언한다

reveal-gated control 은 S0 에 존재하지 않으므로 S0 좌표가 없다. 한 시점을 전제로 두면 어떤 행은 그 전제를 어기고 **그것이 조용히 남는다.**

→ `entry_*` 기하는 control 이 최초 관측 가능해진 state 기준. 신규 필드 **`entry_observed_state`**(`S0`/`S1`.../`POST_REVEAL:<container>`)로 모든 행이 자기 시점을 선언한다. 어기는 개념 자체가 사라진다.

`s0_task_control_visible` 은 별개 변수로 남는다(reveal-gated 면 false).

### 나머지 5건

| GAP | 판정 |
|---|---|
| 06 | `nav_container_type` = **가장 안쪽** 컨테이너(control 을 직접 담는 것). 바깥은 `nav_container_depth` 가 이미 센다. 신규 `nav_container_chain` 병기 |
| 02 | `first_visible_scroll_state` = 최초 관측된 scroll state(reveal 이면 그 reveal 시점). **끝내 미관측일 때만 NULL** |
| 03 | `flow_step_count` 에서 `ENDPOINT_REACHED`·`ABSTAIN` **제외**, `AUTH_GATE` 포함 — 04 §5 가 `auth encounter` 만 이름 붙였다 |
| 04 | 수치 미관측은 **`null`, 0 아님**. `occlusion=0.0` 은 "관측했고 안 가려졌다" |
| 05 | **임계값을 만들지 않는다** — visible 과 occlusion 은 독립 변수다 |

**GAP-05 를 임계값 없이 푸는 것이 핵심**: 90% 가려져도 hit-testable 이면 보이는 것이고, 0% 가려져도 viewport 밖이면 안 보이는 것이다. 파생 관계를 만들면 없는 인과를 스키마에 새긴다.

**GAP-02 커버리지 승격**: fixture 13종이 전부 한 뷰포트에 들어가 S1 이 생기지 않는다 → `03 §3` scroll-only surface capture 가 이 집합으로 검증 불가. GATE 1 은 검증하거나 **미검증을 명시**해야 통과한다. 명세 한 절이 통째로 미검증인 채 통과하면 그 사실이 복원되지 않는다.

**DOM/AX 불일치**: 어느 쪽도 우선하지 않는다. 둘 다 기록하고 `dom_ax_divergence` 플래그. 한쪽을 정본으로 삼으면 divergence 가 데이터에서 사라지는데, 그것은 **보조기술 사용자와 시각 사용자가 다른 화면을 보고 있다는 관측이므로 버릴 것이 아니라 결과다.**

## Δ16 — SSOTV3 provenance (신규)

발행 `T-A-V3-STEP1-013`. 제기 `T-B-BLK-011`(W5A 발견, B 대조군 확인).

**측정**: `git log --all -- SSOTV3` 0건 · `git ls-files SSOTV3` 0건 · 전 원격 브랜치 `ls-tree` 0건 · gitignore 대상 아님. 양성대조 — 같은 방법이 `control/v3/` 6종을 찾아내고 `research/landing_accessibility` 는 620 커밋에 있다. **0 은 실제 부재다.**

B 의 논증이 A 의 `ruling_5` 를 그대로 되돌린다:

> A: "매니페스트는 Director 가 준 bytes 다. A 가 항목을 추가하면 팩 해시가 A 의 손을 타고 무엇이 Director 가 준 것인가가 소멸한다."
> B: 그 논증은 팩이 고정돼 있다는 전제 위에 선다. 지금 팩은 git 밖에 있어 **누구의 손도 타지 않았다는 것을 증명할 수단이 없다.**

**조치**: `control/v3/ssot_snapshot/` 에 22 파일을 바이트 그대로 기록했다. 원본은 건드리지 않았다 — **기록은 수정이 아니다.** 복사 불일치 0, 매니페스트 불일치 0.

**정직한 한계**: 이 커밋은 **지금부터의** provenance 를 준다. 01:52부터 지금까지 바이트가 바뀌지 않았음을 증명하지 못한다. 그 구간의 증거는 (a) mtime 이 20 파일에서 `01:52:49~50` 으로 동일하고 `THREE_TURN_RUNBOOK.md` 만 `02:11:06` (b) manifest 자체 해시 `1735c956…` 를 A(02:06)·B·C·D 가 서로 다른 시각에 독립 계산해 전부 같은 값을 얻었다는 것뿐이다. **파일과 매니페스트를 함께 바꾸면 이 검사들은 통과하므로 변조가 없었다는 증명이 아니라 변조 창을 좁히는 정황이다.**

같은 결함군의 세 번째다 — `T-B-BLK-007`(manifest 가 A 브랜치에만), `T-B-BLK-010`(FINAL_MAIN50 이 A 워크트리에만), `T-B-BLK-011`(SSOT 전체가 git 밖). 매번 B 가 잡았다.

## Δ17 — ticket_id 재사용 사건과 ACK 결속 (신규)

발행 `T-A-V3-STEP1-014`. 제기 `D-V3-FACT_CORRECTION-002`(D 검출) · `T-B-V3-FINDING-004`(B 근본원인).

### 무슨 일이 있었나

**A 가 티켓을 덮어썼다.**

| 판본 | 내용 | ACK |
|---|---|---|
| `T-A-V3-FC-001` @02:12 | exact heads 재대조 · promoted main 로컬 ref 위험 · 08 baseline stale | C(02:15) · B(02:32) |
| `T-A-V3-FC-001` @03:23 | Δ8-R7 `y=1/3` 경계 시정 | D(03:28) · E · B |

파일이 하나뿐이라 나중 것이 앞 것을 덮었다. 버스를 읽으면 뒤 티켓에 ACK 4건이 붙어 보이는데 **그중 둘은 완전히 다른 주제**에 대한 것이다. 기록이 오도한다.

원인은 단순하다 — A 가 매 블록에서 `ticket_id` 를 손으로 짓고 **기존 파일 존재를 확인하지 않았다.**

A 자신의 R9 hard-stop 어휘로 `evidence_overwrite` 급이다. 티켓은 evidence 는 아니나 **불변 기록**이고 성질이 같다.

### 복구

`v1` 을 git `21e0a48` 의 미러본에서 복원했고, zone 시정은 `T-A-V3-FC-002` 로 재발행했다. 미러 전수 검사 결과 **2회 이상 수정된 티켓은 이 한 건뿐**이다.

**복구가 가능했던 이유는 미러를 git 에 커밋해 뒀기 때문이다.** 미러가 없었으면 `v1` 은 사라졌다. `D-R0-39` 의 미러 규약에서 부수적으로 얻은 통제다.

A 는 **타 평면의 ACK 파일을 대신 만들거나 옮기지 않는다.** 어느 ACK 이 어느 티켓 것인지는 `T-A-V3-FC-002.reissued_from` 에 기록했다.

### R18 — ACK 은 티켓 해시에 결속된다

B 가 근본 원인을 짚었다(D-DEF-13 경유): **ACK 이 티켓 내용에 결속되지 않아 교체된 내용이 `ACKED` 로 숨었다.** B 가 자기 ACK 116건을 세어보니 전부 티켓 해시가 없다.

> id 재사용을 안 하기로 다짐하는 것은 통제가 아니다. **ACK 이 티켓 해시를 들고 있으면 교체가 자동으로 드러난다** — 결함을 막는 것이 아니라 검출 가능하게 만드는 것이 옳은 층위다.

- 모든 ACK 은 **`ticket_sha256`** 을 포함한다 — ACK 시점 티켓 파일 전체의 sha256.
- 발행자는 티켓을 쓰기 **전에 경로 존재를 확인**한다. 존재하면 새 id 를 쓴다.
- 기존 ACK 은 소급 수정하지 않는다. **116+건이 해시 없이 남는다는 것을 한계로 기록한다.**

### 왜 숨어 있었나

ACK 이 붙어 있어서 처리된 것처럼 보였다. `ACK 은 completion 이 아니다` 라는 A 자신의 규약이 여기서도 적용된다 — 이번엔 **ACK 이 아예 다른 것에 대한 ACK** 이었다.

이 세션 A 의 여섯 번째 오류이고 여섯 번 다 다른 평면이 잡았다.

### R19 — 재ACK 은 덮지 않는다 (C 의 처리를 규약화)

C 가 A 보다 나은 처리를 보였다. 티켓 내용이 바뀐 것을 발견했을 때 **이전 ACK 을 지우지 않고 `T-A-V3-FC-001.C-1.json` 이라는 새 파일로 재ACK 했다.** 불변 보존과 최신 상태를 동시에 만족한다.

→ 재ACK 은 기존 ACK 파일을 덮지 않고 `<ticket_id>.<plane>-N.json` 으로 새 파일을 만든다. 이전 ACK 은 그 시점의 기록으로 남는다.

A 는 이 사건에서 타 평면 ACK 을 건드리지 않았는데, 이 방식이 있으면 각 평면이 **스스로** 정정할 수 있다 — A 가 대신 옮기는 것보다 낫다.

### 세 평면 스캐너가 전부 놓쳤다

C 가 지적했다 — 세 평면의 버스 스캐너가 이 교체를 하나도 잡지 못했다. **ACK 파일 존재만 보고 내용 결속을 보지 않기 때문이다.** D 는 자기 스캐너에 known-positive/negative/malformed 대조군까지 갖췄는데도 이 층은 보지 못했다. 대조군은 스캐너가 *보도록 설계된 것*을 보는지 검사할 뿐, *보도록 설계되지 않은 것*은 검사하지 못한다.

R18 의 `ticket_sha256` 이 이 층을 연다.

## Δ18 — R20 lane 대역은 이음매를 남긴다 (신규)

발행 `T-A-V3-STEP1-016`. 제기 `T-B-V3-RECON-002`(W5D1 발견, B 실측 확인).

**각 lane 이 자기 대역(fake·spy·stub)으로 테스트하면 통합 지점은 아무도 테스트하지 않는다.**

실례: 8 lane 병합 회귀 **1173 passed / 0 failed** 인데 실행하면 `AttributeError`. runner 가 요구하는 `SafetyGuard.assert_action_allowed` 를 `ActivationSafetyGuard` 가 제공하지 않는다. W5F 는 Protocol fake 로, W5G 는 spy 로 각자 검증했고 **둘을 실제로 연결한 테스트가 없다.**

각 lane 의 테스트를 늘려도 이 층은 열리지 않는다. **대역이 실물을 대신하는 한 대역과 실물의 차이는 보이지 않는다.**

→ **lane 경계를 가로지르는 경로는 양쪽 실물로 한 번 이상 실행돼야 한다.** 그런 테스트가 없으면 통합이 완료된 것이 아니다.

### 그리고 이름을 고치는 것이 답이 아니다

이름 불일치는 **배선이 없다는 것의 증상**이다. W5G 가 자기 known limitation 에 이미 적었다 — "실제 러너가 `guard.guard_page(page)` 를 태우지 않으면 이 강제는 발화하지 않는다."

지금은 `AttributeError` 로 **시끄럽게 실패한다.** 그것은 fail-closed 다. 이름만 맞춘 상태는 fail-open 이 될 수 있다.

> **시끄러운 실패를 조용한 통과로 바꾸지 마라.**

수용기준은 `AttributeError` 소멸이 아니라 **guard 발화**다 — 실물 runner + 실물 guard 로 금지행위가 실제 차단되고, 같은 테스트에서 허용 행위는 통과하는 음성대조까지.

### 오케스트레이션 결함군 다섯 번째

작업을 나누면 **나눈 자리마다 아무도 테스트하지 않는 이음매가 생긴다.** B 의 lane 분할(R7 전달 누락) · D 의 워커 간 입력 의존성 · A 의 디렉터리 add · B 의 수집기 소유 미명시 · 그리고 이번엔 **lane 사이의 실행 경로**.

## Δ19 — R8·R9·R10 (누락분 정본화)

`T-A-V3-STEP1-004` 로 발행했으나 **delta 에 기록하지 않았다.** 그래서 티켓에만 존재했고, 색인이 Δ7 의 옛 6종을 인용해 정본이 뒤로 돌아갈 뻔했다. C 가 색인 대조로 잡았다(`C-FINDING-040011`).

이것이 색인을 만든 이유 그대로다 — **판정이 티켓에만 있으면 정본이 어디인지가 전달 이력에 의존한다.**

### R8 — HOLD 승격은 개수가 아니라 원인의 소재로 가른다

**개수 임계값을 만들지 않는다.** 개수 기준은 "4건이니 하나만 더 참자"를 만들고, 판정이 수를 세는 일이 되면 판정자가 세는 사람이 된다.

실제 검정: **원인이 우리 쪽에 있는가.**

1. 실패 양식을 우리가 통제하는 fixture 로 재현 시도
2. 재현되면 → **systemic**, 즉시 HOLD
3. 재현 안 되고 사이트마다 양상이 다르면 → **site-level**, terminal/missing 사유로 보존하고 계속
4. 재현 시도가 불가능하면 재현 불가로 기록 — **판정을 미루는 것이 잘못 판정하는 것보다 낫다.** 그 target 은 ABSTAIN

판정자는 **C** 다. B 도 E 도 자기 실패를 site-level 로 자가 분류하지 않는다.

**보고 하한(HOLD 조건 아님)**: family 의 evidence-bearing n 이 10 중 5 미만이면 C 가 finding 을 내고 A 가 그 family 를 기술통계 보고 대상으로 삼을지 판정한다. 수집은 계속한다.

### R9 — hard-stop 어휘 8종 (정본)

`wrong_scope` · `target_outside_manifest` · `forbidden_action` · `evidence_overwrite` · `duplicate_launch` · `task_contract_drift`(endpoint drift 포함) · `task_or_outcome_leakage` · `denominator_corruption`

`T-A-V3-P0-001` 의 6종을 대체한다. **이 확장은 hard-stop 대상을 늘린다. 줄이지 않는다** — 6종에 애매하게 걸리던 것이 8종에서 명확히 걸린다. 서로 다른 실패 양식을 맞지 않는 통에 밀어 넣으면 나중에 "이건 wrong_scope 인가"로 다투게 된다.

### R10 — release 문서는 전제조건 SHA 를 인용한다

A 가 release 를 발행하고 A 가 그 근거를 판정한다. self-authority 자체는 없앨 수 없다 — 없앨 수 있는 것은 **근거가 사후에 복원되지 않는 것**이다.

필수 필드: `preconditions[]`(각 completion/assurance 의 ticket_id·plane·exact SHA·판정) · `producer_sha` 와 `assurance_sha` 가 같은 대상인지 · `manifest_sha256` 과 **이미 push 된** 브랜치·SHA · `what_this_authorizes` / `what_this_does_not_authorize` · `revocation`.

`V3_PILOT_5` 부터 적용한다. 기존 release 는 소급 개정하지 않는다.

교훈 출처: `V2_DIAGNOSTIC_RELEASE` 가 Director 의 취소 지시 후 12분간 `RELEASED` 로 남아 있었다. 그 문서는 스스로 "A 가 status 를 변경한다"고 적어 뒀는데도 그랬다. **조항의 존재가 집행이 아니다.**

## Δ20 — 수집기 두 공백은 STEP 1 안이다 (STEP1-015 정본화)

`T-A-V3-STEP1-015` 로 발행했으나 delta 에 기록하지 않았다. C 가 "delta 근거 없는 색인 행"으로 잡았다.

**AX 조인**과 **scroll state 열거** 둘 다 STEP 1 안이다. 미검증 선언(선택지 3)을 기각한다.

- AX 조인 없이는 `accessible_name` · `accessible_name_source` · `label_relation` 과 `ICON_ONLY_AX_NAMED` ↔ `ICON_ONLY_UNNAMED` 구분이 산출되지 않는다. 00 §8 의 절반이며 **미검증으로 두면 한계가 아니라 결측 축이다.**
- scroll state 없이는 "접힌 아래에 있다"와 "존재하지 않는다"를 구분할 수 없다. R13 의 `NONE` 대 `UNDETERMINED` 혼동이 surface 층에서 재현된다. **A 의 Δ15-GAP02 판정이 scroll state 수집 능력을 전제했다** — B 가 그 전제 오류를 짚었다.

`l0_probe.js` / `l0_collector.py` 수정 허용. W2 freeze 는 RF detector 에 걸린 것이지 수집기 전체가 아니다. **세 조건**: 가산적일 것 · 기존 회귀 전건 통과 · **`collector_sha256` 을 모든 v3 관측 행에 기록**(legacy 59·12 는 현재 수집기가, v3 는 바뀐 수집기가 낸다. 그 경계가 데이터에 남아야 한다).

lane 구조는 B 가 정한다. B 는 W5I(AX 조인)·W5J(scroll state)로 나눴다 — Δ12 의 공유 독해 위험을 수집기 층에 적용한 것이다.

## Δ21 — R21 판정 색인 (정본화)

`control/v3/V3_RULING_INDEX.json`. **B 의 전달을 단일 실패점에서 제거하기 위해 만든다** — 워커가 항목의 존재 자체를 모르면 보고할 것도 없다(`T-B-V3-SCOPE-001`).

C 는 GATE 검증 시 **B 의 전달 기록이 아니라 이 색인**으로 대조한다. 색인에 있는데 산출에 없으면 미반영이다.

정본은 이 delta 원문이며 **충돌 시 delta 가 이긴다.** 단 delta 자체가 누락돼 있으면 색인도 함께 틀린다 — Δ19·Δ20 이 그 사례다. 그러므로 **C 는 색인 대 delta 뿐 아니라 delta 대 발행 티켓도 대조한다.**

각 색인 행은 `authority` 필드로 근거 delta 절 또는 티켓 id 를 갖는다(C 제안).

## Δ22 — Δ20 전제 시정 · 포착 스택 신원 (T-B-FC-015)

B 가 `T-B-BLK-012` gap_2 의 전제를 스스로 정정했다. **W5H 가 B 의 중간 지시를 반박했고 B 가 독립 확인했다.**

### 무엇이 틀렸나 — "없다"와 "만들 수 없다" 사이

B 의 grep 은 옳았다: `scroll_state|state_index|scroll_y` → 0 파일, 대조군까지 붙여 "0 은 실제 부재다"까지 정확했다. **그 다음 한 걸음이 틀렸다** — "그 이름의 필드가 없다"에서 "그 기능을 만들려면 engine 을 고쳐야 한다"로 갔고 그 사이에 근거가 없었다.

실제로는 `page.evaluate("(y)=>window.scrollTo(0,y)")` 를 **호출자 자기 파일 안에서** 하면 된다. W5H 의 `session.py` 에 `ScrollPolicy(step_ratio, max_states=8)` 가 이미 있고 S0..Sn 을 낸다. **engine 두 파일은 base 와 바이트 동일**(`l0_collector.py 4090ada1…` · `l0_probe.js 38693299…`, B 가 sha256 확인).

S0 만 보였던 이유도 확인됐다 — **v3 fixture 13/13 이 `body{overflow:hidden}`** 이고 `scrollHeight == clientHeight == 844` 다. 그 집합이 스크롤되지 않아서지 코드가 없어서가 아니다.

> **필드가 없는 것과 기능을 만들 수 없는 것은 다르다.** 이 세션이 반복해서 다룬 것과 같은 계열인데, 이번엔 0 자체는 맞았고 **0 의 의미를 잘못 읽었다.**

무엇이 잡았을까 — "그럼 어떻게 만들 수 있는가"를 한 번 물었으면 드러났다. `page.evaluate` 는 playwright 표준 API 이고 base 의 다른 곳에서도 쓰인다.

### Δ20 의 무엇이 유지되고 무엇이 바뀌나

| | |
|---|---|
| **유지** | scroll state 는 STEP 1 안이다. **필요성 판단이었고 그건 맞다** |
| **바뀜** | 구현 비용과 소유 배정 — **engine owner 가 필요 없다.** 세 조건 중 '가산적'은 engine 무수정으로 자명히 충족 |
| **무관** | AX 조인(gap_1)은 이 정정과 무관하다. `selector ↔ backendDOMNodeId` 조인 부재는 여전히 사실이고 W5H 도 `ax_node=None` + `ax_node_join_status` 로 남겼다. W5I 진행 |

### R22 — 관측은 포착 스택 전체의 신원을 기록한다

`collector_sha256` 하나로는 부족하다. **포착 동작이 호출자(`session.py`)에 있으면 engine sha 만으로는 '어느 코드가 이 관측을 냈는가'가 불완전하다.**

→ 모든 v3 관측 행은 **engine sha + driver/session sha** 를 함께 기록한다. 둘 중 하나만 있으면 재현 시 다른 쪽이 바뀐 것을 알 수 없다.

### 커밋된 스크롤 fixture 는 별개로 필요하다

W5H 는 **런타임 임시 파일**로 대조했다. GATE 1 에서 S1..Sn 을 재현 가능하게 검증하려면 **커밋된 fixture** 가 필요하다 — `Δ15-GAP02` 로 승격했던 커버리지 문제는 그대로 남는다. W5J 산출 중 이 부분은 중복이 아닐 수 있다(판단은 B).

### R23 — 지시문은 인용과 추론을 구분해 표기한다

B 가 자기 패턴을 등재했다 — 이번 세션에 worker 지시문에 틀린 전제를 두 번 넣었다: `OPEN_RIGHT_DRAWER`(04 canonical 밖, W5B 가 잡음) · 이번 건(W5H 가 잡음). **둘 다 worker 가 SSOT·실측을 근거로 반박해서 드러났다.**

**A 도 같다.** `Δ8-R7` 의 경계 오류가 정확히 이 형태였다 — x 축 사례를 쓰면서 `TOP` 을 y 축에 옮겼고, 인용(밴드 표)과 추론(예시 문장)이 한 문장에 섞였다.

→ 지시문·판정문에서 **원문 인용과 그로부터의 추론을 표기로 구분한다.** 인용은 인용으로, 추론은 추론으로.

### W5H 의 반박이 R16 의 worker→coordinator 방향 작동 사례다

W5H 는 B 의 중간 지시를 그대로 따르지 않고 "coordinator 의 정정 ①은 성립하지 않는다"고 명시하고 **대조군으로 보였다**. A 가 R16 으로 세운 "같은 원문 다른 독해면 FACT_CORRECTION" 이 평면 내부에서도 작동한다.

### Δ5 추가 — `STATUS` (C 관측, 2026-08-28)

B 가 `T-B-V3-RESUME-001` 에 `type=STATUS` 를 썼고 C 가 enum 밖임을 잡았다(비차단).

진행 보고는 finding 도 completion 도 아니다 — 무엇을 발견한 것도, 무엇을 끝낸 것도 아니다. 그러나 **새 type 을 만들지 않는다**: `VALIDITY_RISK_CANDIDATE` · `ADDENDUM` 을 접었던 것과 같은 규칙을 적용해 `FINDING` + `finding_class: STATUS_REPORT` 로 접는다.

`STATUS_REPORT` 는 **결정을 요구하지 않는다** — `decision_required` 가 비어 있어야 하고, 비어 있지 않으면 그것은 status 가 아니라 `DECISION_REQUEST` 다.

소급 개정하지 않는다. `T-B-V3-RESUME-001` 은 발행 시점 기록으로 남는다.

## Δ23 — 패턴 규칙을 버리고 별칭을 선언한다 (T-B-V3-FINDING-005)

`T-A-V3-FC-004` 에서 A 가 정규화 규칙을 명시했다 — `Δn-Rm ↔ Rm ↔ P-nn`.

**그 규칙으로도 D 의 오탐이 재현된다.** B 가 지적했고 A 가 양성대조와 함께 검증했다:

```
Δ17-R18  →  R18     (규칙 동작)
Δ21      →  None    (bare Δn 형태 10건이 패턴에 걸리지 않는다)
```

`R21` 로 조회하면 여전히 0건이다. **A 가 쓴 시정 규칙이 시정하지 못했다.**

### 왜 아무도 못 잡을 뻔했나

C 가 정확히 적었다 — C 의 색인↔delta 대조는 색인 id(`Δ` 표기)를 **그대로 키로 써서 정규화 자체가 필요 없었고, 그래서 이 공백에 걸리지 않았다.**

> C 가 공백을 **검출한 것이 아니라 우회한 것**이다.

D 는 걸렸고(오탐), C 는 우회했고, A 는 규칙을 문장으로만 썼다. **B 가 그 규칙을 실제로 구현해봐서 잡았다.**

### R24 — 규칙도 실물로 한 번 실행돼야 한다

`R20`(lane 경계를 가로지르는 경로는 양쪽 실물로 실행돼야 한다)의 같은 원리가 **규칙 자체**에 적용된다.

> **A 가 규칙을 쓰면 누군가 그것을 실제로 구현해봐야 한다.** 규칙이 문장으로만 있으면 그 규칙의 결함은 보이지 않는다 — 규칙을 읽는 사람은 그것이 의도하는 바를 읽지, 그것이 실제로 매칭하는 것을 읽지 않는다.

### 조치 — 패턴을 버린다

**색인이 자기 별칭을 선언한다. 소비자는 별칭을 추론하지 않는다.**

각 행에 `aliases[]` 를 둔다 — 그 판정이 티켓·delta·평면 산출에서 불릴 수 있는 모든 표기. 56/56 채워졌다.

대조 도구는 `id` 와 `aliases` 를 **둘 다** 조회한다. 어느 쪽에도 없으면 그때가 진짜 미수록이다.

패턴 규칙을 쓰지 않는 이유: **새 표기가 생길 때마다 패턴은 틀린다.** 선언은 틀리면 그 행에서만 틀리고, 패턴은 전체에서 조용히 틀린다.

## Δ24 — 선언식으로 바꿔도 선언 자체가 틀릴 수 있다 (T-B-V3-FINDING-006)

### B 가 잡은 것 — D 규칙은 9/10 을 충돌시킨다

D 가 제안한 `Δn ↔ Rn` 규칙을 A 가 실제로 적용해 확인했다.

```
Δ2  ↔ R2  → Δ8-R2    replacement 명부  vs  AUTH_GATE 분모        충돌
Δ4  ↔ R4  → Δ8-R4    promoted main 참조 vs  분모 사슬             충돌
Δ5  ↔ R5  → Δ8-R5    티켓 스키마       vs  fixture_input_mode    충돌
Δ7  ↔ R7  → Δ8-R7    runbook 분류      vs  entry_zone 임계        충돌
Δ9  ↔ R9  → Δ19-R9   activation_depth  vs  hard-stop 8종          충돌
Δ11 ↔ R11 → Δ10-R11  버스 구조         vs  terminal_reason        충돌
Δ16 ↔ R16 → Δ12-R16  SSOT provenance   vs  반론은 불복 아님       충돌
Δ20 ↔ R20 → Δ18-R20  수집기 두 공백    vs  lane 대역              충돌
Δ3  ↔ R3  → 무주인 (Δ8-R3 이 R3a/R3b 로 분할됨)
Δ21 ↔ R21 → 자기 자신                                            유일한 무충돌
```

**A 실측은 10 중 8 충돌**(B 는 9). 차이는 `Δ3` 이며 `Δ8-R3` 이 `R3a`/`R3b` 로 분할돼 `R3` 이 무주인이 됐기 때문이다. 실질은 같다.

> **충돌하지 않는 유일한 행이 그 규칙을 만든 이유인 `Δ21` 이다.** 규칙이 단 하나의 사례에서 일반화됐다.

이것이 `Δ23-R24`(규칙도 실물로 실행돼야 한다)를 다시 확인한다. A 의 v7 별칭은 이 오류를 담지 않았다 — `Δ21` 만 `R21` 을 갖고 경쟁 소유자가 없다.

### C 제안 자체검사가 즉시 A 의 버그를 잡았다

C 가 "별칭 유일성 자체검사"를 제안했다. A 가 상주시키고 돌리자 **v7 에서 3건이 나왔다.**

| 별칭 | 걸린 행 | 판정 |
|---|---|---|
| `a` | Δ1-a · Δ6-a | **A 의 생성 버그** — 정규식 `^(Δ\d+)-(.+)$` 가 `Δ1-a` 에서 `a` 를 뽑았다 |
| `b` | Δ1-b · Δ6-b | 같은 버그 |
| `D3-06` | Δ1-a · Δ1-b | **의도적** — 둘이 같은 D3-06 결정을 개정한다 |

단일문자 별칭을 제거했다(별칭 129 → 123). `D3-06` 은 `intentional_multi` 로 명시해 조회 시 두 행이 모두 반환되는 것이 옳다고 기록했다.

### R25 — 선언도 검사한다

> **패턴을 선언으로 바꾸는 것으로 끝나지 않는다. 선언 자체가 틀릴 수 있다.**

`Δ23` 에서 "선언은 틀리면 그 행에서만 틀리고 패턴은 전체에서 조용히 틀린다"고 적었다. 맞다 — 그러나 **그 행에서 틀린 것도 찾아야 한다.**

색인에 자체검사를 상주시킨다: 전 별칭이 정확히 한 행에 대응하고, 예외는 `intentional_multi` 에 명시된 것뿐이다. 마지막 실행 결과를 `self_check.last_run` 에 남긴다.

C 가 제안하고 A 가 돌리자 A 자신의 버그가 나왔다. **제안한 쪽과 돌린 쪽이 달라서 잡혔다.**

## Δ25 — 별칭 자격과 매칭 규칙 (T-B-V3-FINDING-007)

B 가 v7 별칭에 `a`·`b`·`c`·`d`·`e`·`C` 가 들어 있고 **판정과 무관한 영문 한 단락에서 56행 중 6행이 발화한다**고 실측했다.

v8 이 이미 단일문자를 제거했으나 **A 가 확인해보니 그것으로 부족했다** — 토큰 경계 매칭에서도 `auth` · `vr` · `domax` 가 무관한 영문 산문에서 발화한다. 전부 A 의 기계적 접미사 추출이 만든 것이다.

### 자격 기준

> 별칭은 **그 판정이 실제로 다른 곳에서 불리는 형태**여야 한다. id 에서 기계적으로 잘라낸 조각은 별칭이 아니다.

**배제**: 소문자 단일어(구분자 없음)이면서 길이 6 이하 — `auth` · `vr` · `domax` · `skip`
**유지**: `R3a` · `R13b` · `THREE_TURN_RUNBOOK` · `SSOT provenance` · `scrollfix` — 실제 참조 형태다

### 매칭

**토큰 경계 매칭**을 쓴다. 부분일치 금지. 길이 3 미만 영문 별칭은 색인 결함으로 보고한다.

### A 의 1차 시정이 과잉이었다

A 가 처음 쓴 필터(`^R\d+$` 등 정규식 화이트리스트)가 `R3a` · `R13b` · `THREE_TURN_RUNBOOK` · `SSOT provenance` · `scrollfix` 까지 지웠다. **A 가 즉시 잡아 복원했다.**

`R25`(선언도 검사한다)의 자기적용이다 — 시정을 쓰고 나서 그 시정이 무엇을 지웠는지 출력해 봤기 때문에 잡혔다. 출력을 보지 않았으면 정당한 별칭 7개가 조용히 사라졌을 것이다.

### 산문 대조군

판정과 무관한 영문 문장에 토큰 경계 매칭 → **오탐 0**. 이 대조군을 `self_check.last_run` 에 상주시킨다.

## Δ26 — `base_sha` 는 실재하는 객체를 가리켜야 한다

B 가 `T-B-V3-FINDING-007` 의 `base_sha` 가 **존재하지 않는 커밋**이었음을 스스로 알렸다(`T-B-V3-FINDING-007-SHANOTE`). 축약 sha 에 `0` 을 채워 만든 값이었다.

`R18`(ACK 은 티켓 해시에 결속)은 티켓 내용의 변경을 잡지만 **`base_sha` 가 애초에 실재하지 않는 것은 잡지 못한다.**

→ **`base_sha` 는 `git cat-file -e` 로 해석되는 객체여야 한다.** 축약형을 확장할 때 0 을 채우지 않는다. 발행 전 확인한다.

C 가 새 해시로 재ACK(`.C-1`)하고 스캐너 `explained` 목록에 등재한 처리가 `R18`+`R19` 의 정확한 적용이다 — 해시가 바뀐 이유가 기록되면 그 변경은 검출되되 미해결로 세어지지 않는다.

## Δ27 — 유지 규약을 다짐에서 검사로 (D-V3-FINDING-012)

D 가 A 의 소비자 규칙을 **그대로 구현해** 9/56 이 미수록으로 보고된다고 알렸다. A 가 실측해 두 가지로 갈렸다.

### 진짜 누락 — A 의 `Δ21` 위반, 네 번째

`Δ23` · `Δ24` · `Δ25` · `Δ26` · `R24` · `R25` 가 **색인에 행이 없었다.** delta 에만 썼다.

A 는 `Δ21` 에서 이렇게 규약화했다:

> A 가 판정을 낼 때 **delta 기록과 색인 추가를 함께** 한다. 티켓만 발행하는 것을 금지한다.

**그 뒤로도 네 번 어겼다** — `Δ19`·`Δ20` 누락(C 검출), `Δ23`~`Δ26` 누락(D 검출).

> **규약을 지키겠다는 다짐은 통제가 아니다.**

`self_check.delta_section_coverage` 를 색인에 상주시킨다: delta 의 모든 ruling 절이 색인에 대응 행을 가져야 하고, 마지막 실행 결과를 남긴다. 현재 delta 절 38 · 미커버 0.

### 오탐 — 컨테이너 절

`Δ1` · `Δ6` · `Δ8` · `Δ10` · `Δ12` · `Δ13` · `Δ14` · `Δ15` · `Δ17` · `Δ18` · `Δ19` · `Δ22` · `Δ24` 는 **자식 행을 담는 컨테이너**다(`Δ8` → `Δ8-R1`…`Δ8-R7`). 자체 행을 갖지 않으며 자식이 색인에 있으면 충족이다.

소비자 규칙에 이것이 없어서 D 의 구현이 컨테이너를 미수록으로 셌다. `container_sections` 로 명시한다.

**A 의 규칙이 불완전했다** — `Δ23` 에서 "소비자는 id 와 aliases 를 둘 다 조회한다"고만 적고 컨테이너 개념을 주지 않았다. `R24` 가 또 확인된다: 규칙을 문장으로만 쓰면 그 결함은 구현해봐야 보인다.

## Δ28 — R26 두 측정이 갈리면 시각을 먼저 대조한다

A 와 D 의 `base_sha` 수가 갈렸다(1 대 2). A 는 네 가능성을 나열하고 "넷 중 무엇인지 추정하지 않는다"며 D 에 목록을 요청했다.

**답은 넷 밖에 있었다 — 시간이었다.**

> **[정정 — D-V3-FACT_CORRECTION-003]** 아래의 "둘 다 맞다" 는 **A 가 너무 관대했다.** 실측 시각은 이렇다:
> `07:08:22` D 발행(base_sha 없음) → `07:09:48` D 자기정정 → **`07:11:51` D 가 "지금 2건이다" 라고 ACK** → `07:13:23` A 재측정 1건
> D 의 진술은 **자기정정 123초 뒤**에 쓰였다. 즉 **쓰일 때 이미 거짓이었다.** 시각 차이가 아니라 D 의 오류다. D 가 스스로 정정했고 A 가 수용한다.

- `D-V3-FINDING-012` 가 07:08:22 에 `base_sha` 없이 발행됐다
- D 가 07:09:48 에 자기정정했다
- A 의 재측정은 그 이후이므로 `OK` 로 보였다
- **D 자신이 이미 그 산술을 적어 뒀다** — "A 의 검사가 놓친 것이 아니라 A 감사 이후 D 가 발행한 것"

C 가 D 티켓의 `self_correction` 필드에서 찾았다. **A 도 D 도 자기 숫자를 방어하지 않았고 C 가 원문에서 답을 찾았다.**

> **가능성을 열거하는 것과 열거가 완전하다고 믿는 것은 다르다.**

### R26

**두 측정이 갈리면 방법을 대조하기 전에 측정 시각을 대조한다.**

이 세션에서 같은 형태가 네 번 나왔다 — A-State lane 이 측정 중 HEAD·릴리스 status 변경을 관측 · A-Bus lane 의 blocking 항목이 스냅샷 이후 해소 · A 대 B `base_sha`(분모 차이) · 이번 A 대 D(시각 차이). **이 버스는 초 단위로 움직인다.**

`Δ11` 에 "lane 산출을 인용할 때는 측정 시각을 함께 인용한다"고 적었다. 이것을 **티켓 간 대조**로 확장한다 — 측정 결과에 `measured_at_kst` 를 필수로 붙인다. **시각 없는 수치는 대조할 수 없다.**

### D 의 시정이 다짐이 아니라 도구다

D 는 발행 경로를 `tools/d_emit_ticket.py` 로 단일화하고 스캐너에 `base_sha` 해석 검사를 상주시켰다. **A 가 `Δ27` 에서 유지 규약을 검사로 바꾼 것과 같은 전환이다.**

그리고 D 가 "**A 의 감사 대상이 되어야 잡혔다**"고 적은 것이 정확하다 — 감사가 없었으면 D 는 자기 결함을 몰랐다.

## Δ29 — 판정자가 불일치를 대칭으로 만들면 한쪽의 오류가 사라진다

`Δ28` 에서 A 는 A 와 D 의 수 차이를 "둘 다 맞다, 측정 시각이 달랐다"로 정리했다. **틀렸다.**

D 가 `D-V3-FACT_CORRECTION-003` 으로 정정했다 — "A 실측이 맞다. D 가 틀렸다."

A 가 실측한 시각:

```
07:08:22  D-V3-FINDING-012 발행 (base_sha 없음)
07:09:48  D 자기정정
07:11:51  D 가 "지금 2건이다" 라고 ACK      ← 자기정정 123초 뒤
07:13:23  A 재측정 → 1건
```

**D 의 진술은 쓰일 때 이미 거짓이었다.** "A 감사 이후 D 가 발행한 것"이라는 D 의 원래 설명도 시점이 맞지 않는다 — 발행은 A 감사보다 뒤였으나 **ACK 는 자기정정보다 뒤였다.**

### 실패 형태

> **판정자가 불일치를 대칭으로 만들면 한쪽의 실제 오류가 사라진다.**

A 는 두 측정이 갈렸을 때 "둘 다 맞다"는 정리를 찾았고 그것이 그럴듯했으므로 멈췄다. 대칭 해석은 아무도 틀리지 않게 만들어서 편안하지만, **틀린 쪽이 자기 오류를 배울 기회를 없앤다.** 이번엔 D 가 스스로 잡아서 복구됐다.

### R26 은 옳았으나 A 가 덜 적용했다

`R26`(두 측정이 갈리면 시각을 먼저 대조한다)은 맞는 도구였다. A 는 그것을 적용했으나 **첫 그럴듯한 화해에서 멈췄다.**

대조했어야 할 것은 두 측정의 시각이 아니라 **주장의 시각과 상태 변경의 시각**이다. `D 의 ACK(07:11:51)` 대 `D 의 자기정정(07:09:48)` 을 봤으면 123초 간극이 즉시 드러났다.

→ **R26 보강**: 두 측정이 갈리면 (a) 각 측정의 시각 (b) **각 주장이 쓰인 시각** (c) 관련 상태가 바뀐 시각 — **셋을 함께** 놓는다. (a) 만으로는 "둘 다 맞다"가 너무 쉽게 나온다.

## Δ30 — Scout 경로선택 정책 승계 (T-B-V3-BLK-013)

`Δ6-d` 가 "결정론적 경로선택 정책을 문서화해 P4 이전 동결"을 요구했으나 **동결할 정책의 내용이 v3 로 승계된 적이 없었다.** B 가 정확히 짚었다 — "B 가 쓰면 그건 문서화가 아니라 B 의 판정이 된다."

**측정**(A, `measured_at_kst 2026-08-28T07:2x`): `MIN-1` 은 저장소 50 파일에서 발화하나 **SSOTV3 21 파일에 0건**(양성대조 — `Scout` 은 SSOTV3 6 파일에서 발화). C 도 독립 확인(delta·색인·SSOTV3 전부 0건).

정본은 v2.1 `docs/v2/A1_MEASUREMENT_OPERATIONALIZATION.md` §2.6 `MIN-1`~`MIN-7` 이다. 적대감사 `V2-C002` · `V2-C008` · `V2-C010` · `V2-C012` 로 다져졌다. **A 가 승계를 판정한다** — 새로 쓰는 것이 아니라 기존 정본을 v3 로 옮기는 것이므로 A 의 supersession 권한 안이다.

### 그대로 승계

| 규칙 | 내용 |
|---|---|
| **MIN-2** | activation 수에 대한 **폭우선 열거**. 길이 `n` 을 소진하기 전에 `n+1` 을 시도하지 않는다. **탐욕적 하강 금지** — "그 방식은 최소 경로를 찾지 못하고도 자신이 찾지 못했다는 사실을 알 수 없다" |
| **MIN-5** | **최소성은 열거된 부분격자 안에서만 성립한다.** 보고에 "최소 경로를 찾았다"로 쓰지 않는다. 쓸 수 있는 문장은 "`BRANCHING_LIMIT`·후보 지명 규칙·즉시종료 규칙 아래에서 관측된 최소 activation 수" |
| **MIN-6** | `k`(영역 도달)와 `m`(endpoint)은 **같은 경로에서** 읽는다. 따로 최소화하면 음수 IED 나 실재하지 않는 조합이 나온다. 대가로 `k` 가 과대추정될 수 있으며 **편향 방향이 한쪽**임을 기록한다 |
| **MIN-7** | 예산 소진은 **최소가 아니라 관측 없음**이다. 예산값을 대입하지 않는다 |

### v3 조작화와 충돌해 A 가 조정하는 것

**(1) MIN-1 의 분기 대상 집합 → v3 `Δ9` 를 쓴다**

MIN-1 의 원리는 유지한다 — **분기 대상 집합 = depth 집합.** popup 닫기를 분기 후보에 넣으면 닫기가 depth 로 세어진다.

그러나 **집합의 내용은 v2.1 이 아니라 `Δ9`** 다. v3 는 `SUBMIT_QUERY` 를 depth 에 포함하고 `SELECT_ORIGIN/DESTINATION/DATE` 를 `fixture_input_mode` 조건부로 둔다.

→ 분기 후보 = `Δ9` 의 IN 10종 + CONDITIONAL 3종(control 활성화인 경우). `INPUT_QUERY` · `DISMISS_OBSTRUCTION` · `AUTH_GATE` · `ENDPOINT_REACHED` · `ABSTAIN` 은 분기 대상이 아니다.

**v2.1 과 달라지는 실질**: `SUBMIT_QUERY` 가 v3 에서는 분기 대상이다.

**(2) MIN-4 의 1차 키 `marked_primary` → v3 에 없다**

`marked_primary` 는 대표기능 classifier 의 산물이고 v3 는 그것을 퇴역시켰다(`D3-03`).

→ 1차 키를 **`task_binding_candidate desc`** 로 대체한다 — `03 §4` 의 결정론적 binder 가 이 `task_id` 의 후보로 지명했는가(**점수가 아니라 집합 소속**). 2차 `dom_order asc`, 3차 `selector asc` 는 그대로.

**점수를 1차 키로 쓰지 않는 이유**: `Δ6-d` 의 목적이 결정성이다. 점수는 구현이 바뀌면 순서가 바뀐다. 집합 소속은 `03 §4` 의 선언된 규칙에서 나온다.

`V2-C008` 시정(면적 양자화)의 취지는 유지한다 — **관측값을 tie-break 키에 넣지 않는다.** `dom_order` 는 구조값이므로 서브픽셀 흔들림에 면역이다.

**(3) MIN-3 의 gate 승격 → v3 `Δ14` auth 규칙을 쓴다**

v2.1 은 archetype 별 gate 승격(`A2 §1.5.1a` `E-5`~`E-10`)에 의존한다. v3 는 archetype 을 quota 에서 뺐다(`D3-04`).

→ v3 에서는 **family 의 `endpoint_contract` 가 `AUTH_GATE` 를 endpoint 로 명시하는가**로 판정한다. `F1` 은 명시하므로 endpoint 도달, `F2`~`F5` 는 비-endpoint terminal. **이미 `Δ14` 에서 확정한 규칙이며 MIN-3 이 그것과 정합한다.**

MIN-3 의 핵심은 그대로다 — **"즉시 종료"는 탐색 종료를 말하는 것이고 그 종료가 endpoint 인지는 별도 규칙이 정한다.** 두 표현을 섞으면 gate 로 끊긴 관측이 endpoint 관측처럼 읽힌다.

**(4) MIN-7 의 결과 표기 → `terminal_reason` 에 값이 없다**

`Δ10-R11` 의 13값에 예산 소진이 없다. **`BUDGET_EXCEEDED` 를 추가한다**(14값). 조합: `endpoint_status=ABSTAIN` × `terminal_reason=BUDGET_EXCEEDED`.

### 수집 파라미터 — 선언하되 해석 임계값이 아니다

`BRANCHING_LIMIT=4` · `MAX_ACTIVATIONS_PER_TASK` · `MAX_SCOUT_WALL_CLOCK_S` · `MAX_STATE_REVISITS` · `MAX_CONSECUTIVE_NO_STATE_CHANGE`

A1 이 명시한다 — 이것들은 **수집 파라미터이지 해석 임계값이 아니다.** 관측을 유한하게 만드는 값이며 결과를 자르는 값이 아니다. 따라서 이 선언은 A 가 계속 거부해 온 "새 게이트 수치"가 아니다.

**그러나 값은 P4 이전에 동결하고 manifest 에 기재해야 한다.** `MIN-5` 가 말하듯 **이 값들이 최소성의 범위를 정하므로**, 값 없이는 "무엇에 대한 최소인가"를 말할 수 없다.

`BRANCHING_LIMIT=4` 는 v2.1 값을 승계한다. 나머지 넷은 **B 가 실측 근거와 함께 제안하고 A 가 동결한다** — v2.1 값이 v3 의 5 family 에 맞는지는 검증된 바 없다.

### 이것이 B 의 판정이 되지 않게 하는 구조

B 는 정책을 **쓰지 않는다.** 이 절이 정본이고 B 는 구현한다. 구현 중 이 절과 충돌하는 지점을 발견하면 `R16` 경로로 올린다.

`R24` 를 적용한다 — **A 가 이 정책을 썼으므로 B 가 구현해봐야 그 결함이 보인다.**

## Δ31 — 일시적 부재를 기대값으로 동결한 테스트 (T-B-V3-FINDING-008)

B 가 12 lane 을 병합해 회귀를 돌렸다. **각 lane 은 전부 통과했고 병합하자 3건이 깨졌다.** `Δ18-R20` 이 예고한 형태가 실물로 나왔다 — W5I 는 616 passed / 0 failed, W5J 는 16 passed / 0 failed 였고 **둘 다 사실이었다. 이음매는 병합해야만 보인다.**

### 형태 A — 낡은 격리 단언 2건

lane 이 "다른 lane 이 아직 하지 않았다"는 **병합 전 사실**을 회귀로 고정했고, 그 lane 이 **승인된 일**을 하자 단언이 거짓이 됐다.

| 테스트 | 단언 | 깨진 이유 |
|---|---|---|
| `TestAxNodeJoinIsAbsent` | `l0_collector.py` 에 selector↔backendDOMNodeId 조인이 없다 | **W5I 가 조인을 만들었다.** 그것이 W5I 의 승인된 과업이다 |
| `test_this_lane_does_not_touch_the_engine` | `l0_collector.py` sha256 == base | W5I 의 가산 수정(+37/-0)이 반영됐다. **W5J 의 의도는 여전히 참이다** — W5J 는 engine 을 건드리지 않았다 |

> **일시적 부재를 기대값으로 동결하면, 그 부재를 없애는 것이 승인된 과업일 때 테스트가 진행을 막는다.**

**시정 방향(B 제안, A 승인)**: 지우지 않는다. 각 단언을 **그것이 지키려던 것으로 다시 좁힌다** — 파일의 **절대 상태**가 아니라 **그 lane 자신의 diff** 를 재게 한다. 그러면 단언이 **오히려 강해진다** — 다른 lane 의 승인된 변경에 면역이면서 자기 lane 의 위반은 여전히 잡는다.

B 가 A 의 `Δ18` 을 인용해 이것이 완화가 아님을 명시했다 — **"시끄러운 실패를 조용한 통과로 바꾸지 마라." 같은 사실을 더 정확한 분모로 잰다.** 옳다.

두 번째 단언에 부수 관측 하나: 깨진 매치가 **코드가 아니라 주석 한 줄**이었다(`# ── W5I: selector <-> backendDOMNodeId ──`). 문자열 존재 검사는 주석과 코드를 구분하지 않는다.

### 형태 B — 실질 불일치 1건

`test_w5c_splits_the_pair_when_it_is_available` — W5I 가 예상한 W5C 의 동작(`ICON_ONLY_AX_NAMED`)과 실제(`NOT_OBSERVED`)가 다르다. **완화하지 않는다.** 둘 중 하나가 틀렸거나 둘이 다른 것을 재고 있다. B 가 측정 후 A 에 판정 요청한다.

**lane 안에서 안 잡힌 이유가 중요하다** — W5I 트리에 `surface.py` 가 없어 그 테스트가 **실패가 아니라 skip** 이었다.

### R27 — skip 은 통과가 아니다

> **skip 은 '검사했고 문제없음' 과 요약에서 구분되지 않는다.**

이 프로젝트가 반복해 경계해 온 "빈 결과와 통과가 같아 보인다" 의 또 다른 형태다. B 가 `[추론]` 표기와 함께 스스로 지적했다.

- B 의 COMPLETION 은 **skip 전건을 사유와 함께 열거**한다. 수만 적지 않는다.
- C 는 **사유가 설명되지 않은 skip 을 PASS 로 세지 않는다** — `NOT_TESTABLE` 로 분류하거나 finding 으로 올린다.
- 통과 수는 **작성된 테스트가 통과했다**는 뜻이지 색인 요구를 충족한다는 뜻이 아니다. B 가 스스로 그렇게 적었다.

### R28 — 도구의 출력 억제가 무결과를 만든다

B 가 앞선 실행에서 무결과를 얻었고 **그것은 B 의 명령 결함이었다.** 저장소 `addopts` 에 `-q` 가 있는데 `-q` 를 또 붙여 `-qq` 가 됐고, `-qq` 는 요약줄과 FAILED 목록을 **전부 지운다.**

> **정상 통과도 무결과처럼 보였다.**

`D-R0-76`(0건에는 대조군) 계열이 **도구 호출 층**에 나타난 것이다. 지금까지는 "검색이 실제로 동작하는가"를 물었는데, 이번엔 **"출력이 억제되지 않았는가"** 다.

→ 회귀·검색 결과를 근거로 쓸 때 **출력 형식이 억제되지 않았음을 함께 보인다.** B 가 터미널 요약과 `--junitxml` 두 독립 출처로 같은 수(2073/3/0/1)를 얻은 것이 그 형태다.

## Δ32 — 0-activation 은 관측이 아니라 주장이다 (T-B-V3-BLK-014, P0)

B 가 계측기 안에서 이 세션의 중심 결함을 실물로 찾았다.

**측정**(W5K 레인, `measured_at_kst 2026-08-28T07:27:40`):
```
isinstance(naive_binder, runner.CandidateBinder)  → True   ← Protocol 은 메서드 이름만 본다
bind() 반환                                        → TaskCandidate 1건 (Mapping 아님)
결과   driver.activate 0회 · raw_steps 0 · refusal None · phase MART
dict 로 감싸면                                     → activate 2회 · raw_steps 1
```

`bind` 계약은 `Sequence[Mapping]` 인데 `discover_task_candidates` 는 dataclass 를 낸다. `propose_next` 가 `isinstance(c, Mapping)` 으로 **전건 탈락**시킨 뒤 `None` 을 반환하고, runner 는 그 `None` 을 **정상 종료**로 읽는다.

> **예외도 refusal 도 없이 깨끗한 0-activation 행이 나온다.**

### 왜 P0 인가

이 상태로 50 target 을 돌리면 **전건이 '성공'** 으로 나온다. 사후에 보면 "아무 일도 안 일어난 깨끗한 관측"이다. **0-activation 행과 '정말로 activation 이 필요 없던 target' 이 산출에서 구분되지 않는다.**

B 가 짚었다 — **v2 Day-1 에서 MPFED 0/59 가 나왔고 진짜 원인은 task wiring + fixture detector 였다. 같은 층이다.** 파이프라인이 조용히 비어 돌았다.

그리고 A 의 `Δ18` 인용이 정확하다 — "시끄러운 실패를 조용한 통과로 바꾸지 마라"인데 **여기서는 처음부터 조용한 통과다. 바꿀 시끄러운 실패조차 없었다.**

### 판정 — 원인으로 가른다

B 가 물은 것: `RunnerError` 로 멈출 것인가, `terminal_reason` 으로 기록하고 계속할 것인가.

**둘 다다. 섞이면 안 되는 두 상황이기 때문이다.**

| 상황 | 성격 | 처리 |
|---|---|---|
| **binder 가 후보를 냈는데 소비자가 전건 탈락시켰다** | **계측기 결함** — 형태·계약 불일치 | **`RunnerError`. 항상 멈춘다** |
| **페이지에 후보 control 이 실제로 없다** | **관측** | `endpoint_status=ABSTAIN` × `terminal_reason=NO_TASK_CANDIDATE_FOUND` (15번째 값) |

**현재 결함은 첫째가 둘째로 위장한 것이고, 실제로는 그보다 나쁘게 '성공'으로 위장했다.**

구성요소 간 계약 위반은 **결코 관측이 아니다.** 사이트에 대해 아무것도 말해주지 않는다.

### R29 — `activation_depth = 0` 은 근거를 요구한다

> **0 은 관측이 아니라 주장이다. 주장에는 근거가 필요하다.**

`activation_depth=0` 과 `endpoint_status=REACHED` 가 함께 나오려면 **둘 다** 참이어야 한다:
1. endpoint contract 가 실제로 충족됐다는 증거
2. **최소 하나의 후보가 실제로 바인딩됐다**

**후보 0건은 어떤 경우에도 `endpoint_status=REACHED` 를 낼 수 없다.** 스키마가 그 조합을 거부한다.

`R13`(`NONE` 은 '관측했고 없었다'는 적극적 주장)이 `auth_gate_stage` 에 세운 것과 같은 규칙을 depth 에 적용한다.

### R30 — 구조적 타입 검사는 계약을 검사하지 않는다

`isinstance(naive_binder, runner.CandidateBinder)` 가 **True 를 반환했다.** Protocol 은 메서드 **이름**만 본다. **계약 위반이 타입 검사를 통과한다.**

→ lane 경계에서 Protocol 만족으로 충분하다고 보지 않는다. **반환값의 형태를 런타임에 검증**하고, 위반이면 `RunnerError` 다. `Δ18-R20`(양쪽 실물로 실행)이 왜 필요한지의 구체적 이유다 — 대역은 Protocol 을 만족시키지만 계약은 만족시키지 않을 수 있다.

### EligibilityChecker — 이건 결함이 아니다

동결 manifest 50 target 이 전부 `mobile_web_eligibility=PRECHECK_REQUIRED` 이고 그 값이 `ELIGIBILITY_VALUES` 밖이라 `RunnerError` 로 거부된다.

**의도된 fail-closed 다.** precheck 이 아직 수행되지 않았으므로 runner 가 한 건도 돌지 않는 것이 옳다. `Δ20` 의 세 조건과 `Δ8-R1` 의 precheck 규칙이 그것을 요구한다.

B 가 "이쪽은 시끄러운 실패라 P0 이 아니다"라고 가른 것이 정확하다. **binder 쪽만 조용하다.**

### 안전 전수 — 미발화 3종 중 2종은 구멍이다

`seam1` 금지행동 12종 중 **9 차단 · 3 미발화**.

- `login submit` 미발화 — **결함 아님.** `D3-09` 가 의도적으로 금지하지 않는다
- `credential` · `실제 개인정보` 미발화 — **구멍이다.** guard 는 `input[type=password]`·field name 으로 판정하는데 `PlannedAction` 이 5필드뿐이라 **그 신호가 seam 을 건너오지 못한다**

B 가 감추지 않고 `test_seam1_forbidden_sweep_known_non_firing` 으로 명시 고정했다.

> **A 판정: 이 구멍이 열린 채로 `V3_PILOT_5` 를 release 하지 않는다.** B 가 자신에게 건 조건을 A 가 release 전제조건으로 승격한다.

**차단 9종의 근거 한계도 기록한다** — 텍스트 문구 기준이므로 `보안문자`(단독) · `본인인증` · `이체`(`이체하기`는 잡힘)는 현재 어휘로 미탐지다. **실제 사이트 문구가 fixture 와 다르면 커버리지가 달라진다.** 이것은 `Δ10-R14`(해석 오류는 변이 검사가 못 잡는다)가 안전 층에 나타난 형태다.

### B 가 주장하지 않은 것

- W5K 가 고쳤다고 하지 않는다 — **측정만 했다.** B 가 "측정만"으로 지시했고 워커가 그 경계를 지켰다
- 원인 귀속 미확정 — `discover_task_candidates` 가 dataclass 를 내는 것이 맞는지, `propose_next` 가 Mapping 을 요구하는 것이 맞는지 **아직 판정하지 않았다.** 어느 쪽을 맞출지는 측정 후 정한다
- **고치지 않고 재현부터 고정했다** (`test_seam3_*` 4건). 옳은 순서다

### Δ32 보강 — 이 실패형은 이미 한 번 끝까지 갔다 (D-V3-FINDING-013)

D 가 `Δ32` 를 자기 legacy 산출과 연결했다.

`D-V3-FINDING-003` (RQ-D13b): **"H1_NO_EFFECT 는 무효과가 아니라 무대상이었다."** 53건 중 engine 이 누를 수 있는 dismiss 대상을 가진 것은 1건뿐이었고 38건은 control 이 0개였다. D 는 처음 그것을 **"효과 없음"이라는 실질 결론**으로 냈다가 raw 로 뒤집었다.

**같은 사슬이다:**

```
수집이 조용히 빈 행을 낸다
  → 분석이 그것을 "효과 없음" 으로 읽는다
  → 그것이 연구 결론이 된다
```

`Δ32` 가 막는 것은 그 사슬의 **첫 칸**이다. 그리고 이 프로젝트는 **그 사슬이 끝까지 간 사례를 자기 이력에 갖고 있다** — 다행히 D 가 raw 로 되짚어 뒤집었다.

> `Δ32` 는 신중함이 아니라 **경험적 필요**다. 이 실패형은 가정이 아니라 관측된 이력이다.

`Δ32-R29`(0 은 관측이 아니라 주장이다)가 왜 스키마 제약이어야 하는지 — 규약이나 검토가 아니라 **스키마가 거부해야** 하는지 — 의 근거가 이것이다. 규약은 D 의 사례에서 이미 있었고 그럼에도 결론이 한 번 나왔다.

### Δ32 부기 — 색인 서술이 14/15 를 뒤집어 읽히게 했다 (D-V3-FINDING-014)

색인 `Δ10-R11` 행이 "`terminal_reason` **15값**(`Δ30` 으로 `BUDGET_EXCEEDED` 추가)" 이었다. **그 행만 읽으면 15번째가 `BUDGET_EXCEEDED` 로 읽힌다.**

실제로는 **14 `BUDGET_EXCEEDED`(Δ30)** · **15 `NO_TASK_CANDIDATE_FOUND`(Δ32)** 다.

원인: A 가 그 행을 **누적 문자열 치환**으로 두 번 갱신했고(13→14→15) **괄호 안 서술이 첫 편집 것을 물려받았다.**

→ 서술을 버리고 **15값 전체를 열거**한다. 오독의 자리 자체를 없앤다. `Δ25` 가 별칭에서 한 것(패턴 대신 선언)과 같은 처리다.

**부수 — `82` 의 분해**: C 실측 "필드 82개 전부 `PRECHECK_REQUIRED`" 의 82 는 target 82개가 아니라 **50(targets) + 31(replacement_reserve) + 1(frame 수준)** 이다. D 가 C 의 수를 정확히 재현하면서 분해했다. **target 분모는 50 이다** — 이 구분이 없으면 나중에 "82 target" 이 된다.

## Δ33 — 모양이 아니라 특정성이다 (D-V3-FACT_CORRECTION-004)

D 가 자기 수를 정정하며(9→8) 더 중요한 것을 짚었다 — **D 의 도구가 별칭을 모양으로 걸렀고, 실제 위험은 모양이 아니라 특정성이었다.**

**그 지적이 A 에게도 적용된다.** `Δ25` 가 세운 기준이 모양 규칙이었다: "소문자 단일어(구분자 없음)이면서 길이 6 이하 배제".

A 가 실측했다:

| 후보 | 모양 규칙 | 특정성 |
|---|---|---|
| `coverage` · `manifest` · `container` · `strategy` · `evidence` | **통과** | **탈락** |
| `scrollfix` · `THREE_TURN_RUNBOOK` · `R21` · `GAP-07` | 통과 | 통과 |

> **현재 별칭 집합이 우연히 깨끗할 뿐 규칙이 틀렸다.** 아직 그런 별칭이 생기지 않았을 뿐이다.

### 시정 — 대리 지표를 측정으로 바꾼다

기준은 **"판정과 무관한 산문에서 발화하지 않는가"** 다. 길이·대소문자는 그것의 **대리 지표**일 뿐이다.

→ 대조 말뭉치를 색인에 넣고 `self_check.alias_specificity` 로 돌린다. **매칭되면 모양과 무관하게 색인 결함이다.** 양성대조: 같은 검사가 `coverage`·`manifest` 등을 걸러낸다.

### 같은 전환의 네 번째다

| | 대리 지표 → 측정 |
|---|---|
| `Δ25` | 패턴 규칙 → 선언된 별칭 |
| `Δ27` | 유지 다짐 → `delta_section_coverage` 검사 |
| `Δ32-R29` | 규약 → 스키마 제약 |
| `Δ33` | 모양 규칙 → 특정성 측정 |

**규칙이 옳아 보이는 것과 규칙이 옳은 것은 다르다.** 매번 다른 평면이 그 차이를 실행으로 드러냈다 — `R24` 가 말한 그대로다.

### Δ33 부기 — 도달 가능이 우연이면 안 된다

C 가 v16 에서 index→delta **도달 불가 11건**을 보고했다. A 가 v17 에서 재측정하니 **0** 이다.

**그러나 그 해소는 구조가 아니라 산문 우연이다.** A 가 `Δ33` 본문 표에 `Δ25`·`Δ27`·`Δ32-R29` 를 쓴 덕에 그 토큰들이 delta 본문에 등장했을 뿐이다. **다음에 A 가 그런 언급을 하지 않으면 다시 도달 불가가 된다.**

→ **`split_rows` 를 선언한다.** `Δ8-R3a`/`Δ8-R3b`/`Δ10-R13a`/`Δ10-R13b` 는 `Δ20`(한 행은 한 시점에 검사 가능해야 한다)에 따라 한 판정을 색인에서 쪼갠 것이며 **자체 delta 절을 갖지 않는다.** 도달성 검사에서 **부모 절 존재로 충족**이다.

`container_sections`(delta 절이 부모, 색인 행이 자식)의 **역방향 대응물**이다.

그리고 `index_to_delta_reachability` 검사를 `self_check` 에 상주시킨다 — 양성대조로 가짜 행 `Δ999-R99` 가 도달 불가로 나옴을 확인했다.

> **0 이 나왔다는 것과 0 이 나오게 되어 있다는 것은 다르다.**

## Δ34 — 색인 자체검사는 서술이 아니라 실행 가능한 검사기다

`T-B-V3-FINDING-009` 가 잡았다 — **`self_check.last_run` 이 04:58·61행 시점 값인데 색인은 75행이었고, 그 낡은 값이 `unexpected_duplicate: 0` 이라고 말했다. 실제로는 2건이었다**(`MIN-4` · `MIN-5`).

검사 결과가 **자기가 측정한 상태보다 오래 살아남아 깨끗하다고 주장했다.** A 가 계속 경계해 온 형태가 A 의 검사 자체에 있었다.

### `control/v3/check_ruling_index.py`

서술을 버리고 **누구든 돌릴 수 있는 검사기**로 만들었다. 7 검사:

`alias_uniqueness` · `alias_specificity` · `ghost_alias` · `delta_section_coverage` · `index_to_delta_reachability` · `required_field` · `count_mismatch`

**검사별 변이 양성대조**를 붙였다 — 각 검사에 그 검사가 잡아야 할 결함을 하나씩 주입해 실제로 잡는지 확인한다. **하나라도 못 잡으면 검사기가 결과 보고를 거부한다**(`exit 2`, "아래 결과를 근거로 쓰지 마라").

`last_run` 은 `index_version` · `rows` 를 싣고, **그것이 현재 색인과 다르면 그 결과는 무효다.**

### 만들면서 세 번 걸렸다

| | |
|---|---|
| 1차 실행 | **양성대조 실패** — probe 하나에 결함 둘을 실어 어느 검사가 무엇을 잡았는지 알 수 없었다. **검사기가 스스로 보고를 거부한 것이 옳은 동작이다** |
| probe 수정 | 3/6 이 못 잡았다. 전부 **probe 결함** — 중복 probe 가 `intentional_multi` 별칭을 골랐고, `count_mismatch` probe 가 변이 뒤에 count 를 덮어썼고, 도달성 probe 의 가짜 id `Δ999-R99` 가 **A 가 `Δ33` 부기에 그 문자열을 써버려서 delta 에서 도달 가능해졌다** |
| 6/6 통과 후 | **실제 결함이 나왔다** — `Δ27` · `Δ33` 이 색인에 없다 |

세 번째가 핵심이다. **`Δ21`(delta 기록과 색인 추가를 함께) 위반의 다섯 번째이고, 서술로만 있던 `delta_section_coverage` 가 실제로 돌자 바로 나왔다.**

`Δ27` 에서 "규약을 지키겠다는 다짐은 통제가 아니다"라고 적고 **검사를 JSON 안에 서술로만 두었다.** 서술된 검사는 다짐과 같다.

> **문서가 자기 양성대조를 무력화할 수 있다** — `Δ999-R99` 를 예시로 쓴 순간 그것은 더 이상 존재하지 않는 id 가 아니게 됐다. 검사기에 그 사례를 주석으로 남기고 `assert` 로 막았다.

### Δ34 부기 — 선언과 구현이 달랐고, 그걸 따라가니 세 번째가 나왔다 (D-V3-FINDING-015)

D 가 A 의 도달성 규칙을 **선언대로 구현해 10 을 얻었다.** A 의 검사기는 0 을 냈다.

A 실측 — **D 가 옳다.**

```
선언된 3경로(id 헤더 · 별칭 본문 · split 부모)   →  10 도달 불가
구현이 쓰는 4경로(+ authority 헤더)              →   0
그 10 은 전부 authority 로만 도달하는 행이다
```

**A 의 선언에 `authority` 경로가 빠져 있었고 구현은 그것을 쓰고 있었다.** `R24` 가 또 확인된다 — 이번엔 "규칙을 구현해봐야 결함이 보인다"가 아니라 **"구현이 선언보다 많은 일을 하고 있었다"** 다.

`authority` 는 정당한 앵커다 — 행이 실재하는 delta 절에 매여 있다는 뜻이다. 선언에 넣는다.

### 그리고 따라가니 헤더 추출이 틀려 있었다

`split_rows` 의 `Δ10-R13a`/`Δ10-R13b` 가 `authority=Δ10-R13` 인데 그것이 헤더로 잡히지 않았다. 확인하니 **정규식이 `id` 뒤에 `—` 나 줄끝만 허용**해서 `### Δ10-R13 auth_gate_stage = UNDETERMINED 추가` 같은 절을 놓쳤다.

**절 51개만 보고 있었다. 실제로는 63개다.** 12개를 놓쳤고 그중에는 `Δ6-a`~`Δ6-e` · `Δ8-R7` · `Δ10-R11`~`R14` 가 있다.

> **`delta_section_coverage` 가 너무 관대했다** — 못 본 절은 커버리지를 요구하지 않는다. **검사가 통과한 이유가 검사가 좁아서였다.**

토큰 경계로 바꿨다. 그 뒤 7 검사 전부 통과.

**한 번의 finding 이 세 겹을 열었다** — 낡은 `last_run`(B) → 선언과 구현의 불일치(D) → 헤더 추출 결함(A). 셋 다 "검사가 깨끗하다고 말했다"는 같은 지점에 있었다.

### Δ34 부기 2 — 양성대조가 두 규칙을 구분하지 못했다 (C-FINDING-074834)

C 가 A 의 검사기를 **독립 실행**하고 `authority` 토큰만 제거한 변형과 비교했다.

```
A 코드 그대로                →  미도달 0
A 코드에서 authority 제거     →  미도달 10 (C·D 의 10 과 행 단위 동일)
```

D 가 역산한 "넓은 규칙"의 실체가 `authority` 필드임을 C 가 코드 인용으로 확정했다.

**그리고 C 가 더 중요한 것을 짚었다 — A 의 양성대조 probe 는 두 규칙을 구분하지 못한다.**

probe 의 가짜 행은 `authority: "Δ90001"` 로 **존재하지 않는 부모**를 가리킨다. 넓은 규칙에서도 좁은 규칙에서도 미도달이므로 **어느 쪽이 구현됐는지 재지 못한다.**

→ 양성대조를 **두 방향**으로 고정한다:

| probe | 기대 |
|---|---|
| 고아 행(부모 절 없음) | **반드시 잡힌다** |
| 부모 절이 실재하는 가짜 자식 | **잡히면 안 된다** |

하나만 두면 검사가 무엇을 구현했는지 말할 수 없다.

### 선언한다 — 한계와 함께

`authority` 경로를 **선언한다.** 자식 행은 부모 절 안에서 서술되는 것이 정상이고(`Δ32-safety` 는 `Δ32` 의 '안전 전수' 소절), 좁은 규칙을 쓰면 **정상 행 10건이 미도달로 나온다 — 검사가 참인 것을 거짓으로 만든다.**

> **한계**: `authority` 경로는 **앵커만 검사하고 자식별 서술 존재는 검사하지 않는다.** 부모 절이 있으면 그 절이 그 자식 판정을 실제로 서술하는지와 무관하게 도달로 센다. **색인에만 있고 delta 본문에 서술이 없는 자식 행은 이 검사로 검출되지 않는다.**

C 가 "선언하려면 그 결과를 명시하라"고 요구했고 A 가 받는다. **검사의 사각을 이름 붙여 두는 것이 사각을 없애는 것보다 정직하다** — 없앨 수 없기 때문이다.

C 는 **A 코드를 수정하지 않았고** "A 의 넓은 규칙이 틀렸다는 판정이 아니다"라고 명시했다. 관측과 판정을 가른 처리다.

**시각 기록**(`R26`): C 의 측정은 색인 v20 이고 A 의 v21 시정보다 35초 앞선다. **그러나 지적의 실질은 v21 에도 그대로 유효했다** — v21 은 `authority` 를 선언에 넣었으나 probe 는 그대로였다.

### Δ34 부기 3 — 문서가 자기 검사를 무력화했다, 두 번째

부기 2 를 쓰면서 A 가 probe 의 부모 값을 **본문에 인용했다.** 그 순간 그 토큰이 delta 에 존재하게 됐고, 고아 probe 가 `authority` 경로로 도달 가능해져 **검사가 자기 결함을 못 잡게 됐다.**

`--write` 실행에서 즉시 드러났다 — 직전 실행은 통과, 문서를 쓴 뒤 실행은 **양성대조 실패**.

**같은 형태가 두 번째다.** 첫 번째는 `Δ999-R99`(부기 1), 두 번째는 이번 부모 값. **첫 번째를 주석으로 경고해 두고도 두 번째를 만들었다.**

> **경고를 적는 것과 그 경고가 작동하는 것은 다르다.** 주석은 사람이 읽어야 작동하고, `assert` 는 읽지 않아도 작동한다. 그런데 그 `assert` 도 **id 만 검사하고 `authority` 는 검사하지 않았다.**

### 구조로 막는다

probe 값을 **런타임에 delta 에 없는 것으로 고른다.** 고정 리터럴을 쓰지 않는다.

```
for i in range(900001, 900050):
    rid, auth = f"Δ{i}-R901", f"Δ{i}"
    if all(t not in delta_text for t in (rid, auth)):
        return rid, auth
```

**모든 토큰의 부재를 확인**하고, 걸리면 다음 후보로 넘어간다. 이제 A 가 어떤 값을 문서에 쓰더라도 probe 는 다른 값을 고른다.

이것이 `Δ33` 이 말한 전환의 다섯 번째다 — **고정 리터럴(대리 지표) → 런타임 부재 확인(측정).**

### Δ34 부기 4 — 시정은 그 시정을 촉발한 입력에 대고 확인한다

C 가 `C-FINDING-075215` 로 같은 결함을 **독립 검출했다.** A 는 `--write` 실행에서(직전 통과 → 문서 작성 후 실패), C 는 v22 검사기 독립 실행에서. **둘이 서로 모른 채 같은 것을 찾았고 원인 진단도 같다.**

A 가 v23 을 확인한 방식을 기록한다 — **현재 상태가 아니라 C 가 잰 그 상태에 돌렸다.**

```
dc3f8776(v22) 의 색인·delta 에
  v22 검사기 → exit 2  (양성대조 실패 — C 보고 재현)
  v23 검사기 → PASS
```

**시정을 새 상태에 돌려 통과하는 것은 시정의 증거가 아니다.** 새 상태에서는 원인 자체가 없을 수 있다. 그 시정을 촉발한 입력에서 통과해야 시정이다.

이 세션에서 반복된 "빈 결과와 통과가 같아 보인다"가 **시정 검증**에 나타난 형태다.

## Δ35 — `NOT_OBSERVED` 는 관측을 주장하는 값이다 (T-B-V3-FINDING-010)

B 가 물었다 — `measure_surface` 계약에 `probe_state` 형태 검증을 넣을 것인가.

**넣는다.** 이것은 새 기능이 아니라 `Δ32-R30`(lane 경계에서 반환·입력 형태를 런타임 검증한다)의 적용이다.

### 왜

`measure_surface` 는 `probe_state` 형태가 틀려도 **예외 없이 `NOT_OBSERVED` 를 낸다.** 그러면 두 가지가 같은 출력이 된다:

| 실제 | 현재 출력 |
|---|---|
| control 이 정말 없었다 | `NOT_OBSERVED` |
| 형태를 잘못 넘겼다 | `NOT_OBSERVED` |

**`NOT_OBSERVED` 는 관측을 주장하는 값이다** — "볼 수 있었고 없었다". 계약 위반은 **볼 수 없었다**는 뜻이므로 그 값을 낼 자격이 없다.

`Δ32` 그대로다 — 구성요소 간 계약 위반은 사이트에 대해 아무것도 말해주지 않는다.

### 판정

- 형태 위반 → **예외.** `NOT_OBSERVED` 를 내지 않는다
- 실제 부재 → `NOT_OBSERVED`
- B 가 호출부에 둔 방어(`dom_control_observed is True` + `"TASK_CONTROL_NOT_IN_PROBE" not in notes`)는 **유지하되 대체물이 아니다.** 호출부 방어는 그 호출부만 지킨다

### R31 — 단언은 실패할 수 있음을 보여야 한다

B 가 part2 에서 찾은 것 — `test_engine_files_are_byte_identical_to_base` 가 `git diff --name-only HEAD` 를 썼다. **커밋하면 그 값은 항상 빈 문자열이다.** 커밋된 위반을 영원히 못 잡는다.

> **깨지지 않았다. 그래서 아무도 안 봤다.**

`Δ31` 의 3건은 시끄럽게 깨져서 발견됐는데 이건 계속 초록불이었다. B 의 정리가 정확하다 — **"시끄러운 실패가 조용한 통과보다 낫다"의 대우: 조용한 통과는 실패보다 오래 산다.**

→ **모든 단언은 실패 가능함을 실증해야 한다.** B 가 그 표준을 보였다 — engine 에 파일을 심자 두 lane 단언이 **동시에 FAILED**, `LANE_BRANCH` 를 실제 위반 lane 으로 바꾸자 **FAILED**. **통과가 완화 때문이 아님을 실패를 만들어서 보였다.**

### 워커의 거부를 A 가 지지한다

워커가 두 안을 거부했다 — 주석 필터 · 소유 이전. 인용:

> "주석을 걸러내면 이 테스트는 오늘 초록불이 되지만 **그때 주장하는 명제가 거짓이다.** 조인은 코드로 실재한다. 실패가 주석 한 줄에서만 난 이유는 조인 코드가 두 토큰을 한 줄에 안 적었기 때문이지 조인이 없어서가 아니다. 즉 주석 필터는 **거짓 명제를 조용히 통과시키는 장치**다."

**명제를 참인 것으로 바꾼 것**이 옳다 — base 커밋 원문을 재게 하고, 살아 있는 명제는 AST 단언으로 분리했다. 그리고 워커가 자기 첫 시도(줄 grep)가 `session.py` 자기 docstring 에 걸리는 것을 스스로 잡았다.

### GATE 1 조건 추가 — production 호출부 부재

B 가 명시했다: **`measure_surface` 를 부르는 곳은 현재 테스트뿐이다.** 즉 형태 결함이 **실제 수집 경로에도 있는지는 확인 불가**다 — 배선이 없어서다.

→ **W5F/W5K 배선 시점에 재확인이 GATE 1 통과 조건이다.** 배선 없이 "고쳤다"로 닫지 않는다. B 가 잊지 않으려고 스스로 적은 것을 A 가 계약으로 만든다.

### B 가 지고 가는 한계 3건을 A 가 승인한다

`lane_ownership` 이 git 히스토리 의존(shallow clone 이면 **실패한다** — 조용한 skip 아님) · `LANE_BASE` 하드코딩(`7c5ae70`, 3회 실측) · 미커밋 변경의 lane 귀속. **셋 다 감춰지지 않고 기재됐고 실패 방향이 fail-closed 다.**

## Δ36 — A 가 MIN-2 를 과잉 승계했다 (T-B-V3-BLK-015)

B 가 `Δ30` 을 구현하니 판정이 v3 runner 와 충돌했다. `R24` 가 의도대로 작동한 것이고, **드러난 것은 v3 의 결함이 아니라 A 의 승계 범위 오류다.**

### ① MIN-2 — v3 에 요구하지 않는다

**B 실측**: `V3Runner._scout_path` 는 `while` 단일 경로, `MinPathScoutStrategy` 는 매 호출 랭킹 1위 하나 — **탐욕적 하강 그 자체**다. 코드 docstring 이 스스로 인정한다("재귀 BFS 는 runner 의 다음 버전이 할 일"). **양성대조**: v2 `l1_engine.py:1412` 에 실제 BFS(`deque`·`popleft`)가 있다 — 폭우선이 이 저장소에 실재하며 v3 쪽에만 없다.

**A 의 오류**: `Δ30` 에서 MIN-1~MIN-7 을 "그대로 승계 / A 조정" 둘로만 갈랐다. **셋째 범주를 두지 않았다 — v3 에 필요 없는 것.**

MIN 규칙들은 v2.1 에서 `NED`/`IED` 가 **최소성 주장**이었기 때문에 필요했다. v3 는 다르다:

- v3 의 primary construct 는 **flow divergence** 이지 최소성이 아니다
- `activation_depth` 는 **derived scalar** 다 (`D3-05`)
- `Δ6-d` 가 요구하는 것은 **결정성과 균일성**이지 최소성이 아니다

> **탐욕적 하강 + 선언된 전순서는 결정성과 균일성을 만족한다. 최소성만 만족하지 못한다. 그리고 v3 는 최소성을 주장하지 않는다.**

**판정**

| | |
|---|---|
| MIN-2 폭우선 | **v3 에 요구하지 않는다.** BFS 도입은 STEP 1 범위 밖이며 v3 construct 가 요구하지 않는다 |
| 대신 요구 | `Δ6-d` 의 결정론적 경로선택 정책 — 이미 요구했고 B 가 `tiebreak.py` 로 이행 중 |
| **어휘** | **v3 산출·보고 어디에도 "최소" 를 쓰지 않는다.** `activation_depth` 는 "선언된 정책이 찾은 경로의 깊이" 다 |
| 산출 표기 | `search_strategy: "greedy_descent_with_declared_total_order"` 를 path manifest 에 **필수 기재** |
| MIN-5 | 주장 경계가 **더 좁아진다** — "열거된 부분격자 안에서의 최소" 조차 말할 수 없다. 열거가 없기 때문이다 |

B 가 "미룬다면 그 사실이 산출에 남아야 한다"고 요구한 것이 정확하고, A 는 그보다 강하게 — **어휘 자체를 금지**한다.

### ② evidence 랭킹과 Scout 경로 발산 — v2 를 고치지 않는다

`min4_sort_key` 의 1차 키를 바꾸면 v2 BFS 분기 순서가 바뀌어 **v2 산출의 재현성이 깨진다.** 건드리지 않는다.

**판정**: v3 의 경로 선택은 **v3 의 tiebreak 을 쓴다.** v3 runner 가 v2 Scout 을 호출해 `min4_sort_key` 를 타고 있다면 **그 이음매가 시정 대상**이고, 시정 방향은 v2 변경이 아니라 **v3 가 자기 것을 쓰게 하는 것**이다.

부기: `marked_primary` 는 RF classifier 산물이고 `D3-03` 이 퇴역시켰다. **v3 경로에서 그 값이 `True` 가 될 수 있는지 B 가 실측하라** — 될 수 없다면 발산 조건 자체가 성립하지 않는다.

`ruling_10` 위반 여부: **발산이 남으면 위반이다.** 기록된 `SELECTED`/`rank` 가 실제 밟은 경로를 설명하지 못하면 경로선택 규칙이 균일하다고 말할 수 없다. `min4_sort_key` docstring 이 스스로 그 위험을 적어 뒀다.

### ③ `BUDGET_EXCEEDED` 이음매 — 잇는다

`Δ10-R11` 이 "**모든 terminal 이 `endpoint_status` 와 `terminal_reason` 을 둘 다 갖는다**"고 정했다. `terminal_reason=None` 으로 나가는 terminal 은 그 스키마 위반이다.

**판정**: Protocol 반환 형태를 바꿔 사유 축이 건너오게 한다.

기존 테스트가 `endpoint_status is None` 을 핀하고 있다 — **`Δ31` 대로 지우지 않고 다시 좁힌다.** 그리고 `R31` — 그 테스트가 **실패할 수 있음을 실증**해야 한다.

### ④ `Δ30-branch` — 집합 선언만으로는 이행이 아니다

`_classify_action_token` 이 낼 수 있는 값이 3종뿐이고 **`SUBMIT_QUERY` 를 포함한 10종은 이 경로로 관측될 수 없다.**

A 가 `Δ30-branch` 에서 "**v2.1 과 달리 `SUBMIT_QUERY` 는 분기 대상이다**"를 실질 차이로 명시했는데 **구현이 그 값을 낼 수 없다.**

**판정: `PARTIALLY_IMPLEMENTED`. 선언만으로 닫지 않는다.**

그리고 이건 한계가 아니라 **틀린 측정**이다 — `SUBMIT_QUERY` 를 분류하지 못하면 `activation_depth` 가 submit 을 빠뜨리고, 그것은 `Δ9` 를 정면으로 어긴다.

→ **`Δ9` 의 IN 10종은 분류 가능해야 한다. GATE 1 통과 조건이다.** 분류 불가한 토큰이 남으면 그 target 의 `activation_depth` 는 산출하지 않고 `UNDETERMINED` 다.

`l0_probe.js` 에 구조 신호를 추가하는 것은 **`Δ20` 이 이미 허용한 범주**다(가산적·회귀 전건 통과·포착 스택 신원 기록).

### part4 — MIN-5 전제 기재는 유지한다

판정 ① 로 "최소성의 범위" 라는 틀은 사라지지만 **파라미터 기재 요구는 남는다.** 무엇을 탐색했는지 모르면 무엇을 못 봤는지도 모른다. `build_path_manifest` 에 탐색 파라미터와 후보 지명 규칙을 기재한다.

`Δ30-budget` 의 나머지 4 파라미터: **B 가 "pilot 관측 0건이라 실측 근거가 없다"며 제안을 거부한 것이 옳다.** v2.1 값을 옮기고 '실측 근거' 라 부르지 않겠다는 입장을 A 가 지지한다 — **P4 이후로 미룬다.**

### D 의 우려가 해소됐다

B 실측: `V3Runner.run` 이 `3. _capture_surface`(즉시 디스크 기록) → `4. binder.bind` 순서다. **`Δ32` (a) 로 멈춰도 `s000/dom.html` 이 남는다.** 계약 위반으로 중단해도 raw 증거는 잔존한다.

## Δ37 — legacy `NED`/`IED`/`MPFED` 는 v3 에서 `NULL` 이다 (D-V3-FINDING-016)

D 가 `Δ36` 의 귀결을 짚었다 — **A 가 '최소' 어휘를 금지했는데 v3 가 그 이름들을 그대로 낸다면 이름이 금지된 주장을 한다.**

**A 실측**(양성대조 포함): SSOTV3 21 파일에서 `NED`/`IED`/`MPFED` 는 **5회 등장하고 전부 "legacy compatibility" 또는 "derived scalar" 이며 정의가 한 번도 없다.** 대조로 `activation_depth` 는 `02` 와 `04` 에 정의돼 있다.

> **그 이름들의 유일한 정의는 v2.1 의 것이고, 그것은 최소성 주장이다.**

### 판정 — `NULL`

v3 관측 행은 legacy `NED`·`IED`·`MPFED` 컬럼을 **`NULL` 로 둔다.**

1. 그 이름의 유일한 정의가 최소성 주장인데 **`Δ36` 이 v3 는 그 주장을 하지 않는다고 확정했다**
2. 탐욕적 하강으로 얻은 값을 `NED` 라는 이름의 컬럼에 넣으면 **`ruling_11` 의 오류 그대로다 — 같은 이름, 다른 양**
3. 값은 v3 자신의 정의된 필드(`activation_depth` · `nav_container_depth`)가 담는다

**`02 §7` 의 compatibility 요구는 지켜진다** — 컬럼은 존재한다. 지켜지지 않는 것은 값이고, **그 값이 거짓이기 때문에 넣지 않는 것이 지키는 것이다.**

`Δ32-R29` 와 같은 규율이다 — **의미를 충족할 수 없는 필드에 값을 넣지 않는다.**

### 사유를 행에 남긴다

`legacy_depth_null_reason` 을 기록한다:

> `v3 search_strategy=greedy_descent_with_declared_total_order. NED/IED/MPFED 의 유일한 정의는 v2.1 의 최소성 주장이며 v3 는 그 주장을 하지 않는다 (Δ36).`

**`NULL` 만 두면 '못 쟀다' 로 읽힌다.** 사유가 있어야 '재지 않기로 했다' 가 된다 — `R13` 의 `NONE` 대 `UNDETERMINED` 와 같은 구분이다.

### legacy 59 와의 비교는 STEP 3 의 분석 선택이다

v3 `activation_depth` 와 v2.1 `NED` 를 비교하고 싶으면 **탐색 방식 차이를 명시한 채** 분석 단계에서 한다. 스키마가 그 비교를 미리 참으로 만들어 주지 않는다.

## Δ38 — 측정값은 한 곳에만 둔다 (D-V3-FINDING-017)

D 가 `T-B-V3-FINDING-009`(낡은 `last_run`)의 **한 층 아래**를 찾았다 — **A 가 그 시정을 루트에만 적용했다.**

**A 실측**:

| 하위 블록 | 기재값 | 실제 |
|---|---|---|
| `delta_section_coverage.last_run` | delta 절 **38** | **67** |
| `alias_specificity.last_run` | 별칭 **157** | **159**(루트 기재) |

**둘 다 A 가 그 시점에 손으로 적고 갱신하지 않았다.** 그리고 `delta_section_coverage` 의 38 은 **A 가 헤더 추출을 51→63 으로 시정했다고 기록한 것과 정면으로 모순한다.**

### 판정

**측정값은 `self_check.last_run` 한 곳에만 둔다.** 하위 블록은 규칙·근거·한계만 담고 수치를 담지 않는다.

> **사본이 둘이면 반드시 갈린다.** 갈릴 수 있는 것이 아니라 갈린다 — 하나만 갱신되기 때문이다.

검사기에 **8번째 검사 `measurement_single_source`** 를 넣었다: `self_check` 하위 블록에 `last_run` 이 있으면 실패한다. 변이 probe 도 함께.

### 부수 — 검사기가 자기 개수를 잘못 말했다

검사를 8개로 늘렸는데 출력은 `"PASS — 7개 검사 전부 통과"` 라고 말했다. **고정 리터럴이라 늘어난 것을 모른다.**

`Δ33`(모양 → 측정) · `Δ34`(서술 → 실행) · `Δ38`(사본 → 단일 출처)과 같은 형태다. **계산값으로 바꿨다** — `len(per_check)`.

작지만 이 세션이 반복해 다룬 것 그대로다: **자기 상태를 손으로 적은 숫자는 상태가 바뀌면 거짓이 된다.**

## Δ39 — R32 선택적 입력은 **세 상태**를 구분한다 (T-B-V3-FINDING-011)

같은 형태가 세 번째다 — `Δ32`(`probe_state`) · `Δ35`(`measure_surface`) · 이번 `task_control["ax_node"]`. **개별 판정을 반복하지 않고 일반 규칙으로 닫는다.**

### R32

선택적 입력은 **두 상태가 아니라 세 상태**를 구분한다.

| 상태 | 뜻 | 처리 |
|---|---|---|
| **부재** | 호출자가 주지 않았다 | **관측이다.** `None` + 사유 note(예: `AX_NODE_ABSENT`) |
| **형태 위반** | 줬는데 계약과 다르다 | **계약 위반이다. raise** |
| **존재** | 계약대로 있다 | 값 |

**부재와 형태 위반이 같은 출력이면 계약 위반이 관측으로 위장한다.** `Δ32` 가 정한 것 그대로이고, 이제 특정 함수가 아니라 **모든 선택적 입력**에 적용한다.

### 네 질문에 대한 답

**① `ax_node` 형태 검증의 소유 레인** — **B 가 정한다.** 구현 배치는 A 소관이 아니다.

**② 빈 `scroll_states`** — **계약 위반이다. raise.**
`S0` 는 구성상 항상 존재한다. 따라서 빈 목록은 "포착했고 없었다"가 될 수 없고 **"포착이 돌지 않았다"** 뿐이다. `Δ32` 의 첫째 case 다.

**③** — **A 가 답하지 않는다.** 질문의 뜻을 특정하지 못했다("동시 보유"가 형태 검증과 note 의 동시 보유인지, 두 입력의 동시 부재인지 불분명). **추정해서 답하면 그 답이 근거 없는 판정이 된다.** B 가 다시 진술하면 판정한다.

**④ `R30` 적용 대상 목록** — **B 가 만든다.** 어느 이음매가 형태 검증을 필요로 하는지는 **호출 그래프를 아는 쪽**이 안다. A 가 목록을 만들면 그것은 A 가 모르는 것에 대한 목록이다.

A 가 정하는 것은 **규칙과 수용기준**이다:
- 목록의 각 항목이 **세 상태를 구분함**을 보인다
- **목록의 완전성은 C 가 독립 확인한다** — B 의 자기보고로 닫지 않는다. `Δ10-R14` 대로 C 는 자기 경로로 이음매를 열거한다

### 왜 일반 규칙이 개별 판정보다 나은가

세 번 같은 것을 물었다. 네 번째가 오면 그때도 A 가 답해야 하고, **그 사이에 만들어진 코드는 규칙 없이 만들어진다.** 규칙을 먼저 두면 B 가 묻지 않고 적용하고, A 는 적용 여부만 본다.

`R24` 가 적용된다 — **이 규칙도 B 가 구현해봐야 그 결함이 보인다.** 목록을 만들다 규칙이 맞지 않는 이음매가 나오면 `R16` 으로 올려라.

---

## Δ40 — 모호한 입력은 **네 번째 상태**다. 도구가 무엇을 측정할지 스스로 고르면 note 로 무해해지지 않는다 (T-B-V3-RECON-004)

**출처**: B 가 `③` 을 재진술했다. `A` 가 답을 거부한 것이 옳았고, 재진술로 판정 가능해졌다.

### 재진술된 질문

하나의 `probe_state` dict 가 `scroll_states` 키와 `raw_features` 키를 **둘 다** 가질 때,
`_iter_states` 는 그것을 **번들**로 읽을지 **단일 state** 로 읽을지 결정할 수 없다.
현재 구현은 `probe_state.get("scroll_states")` 를 먼저 보므로 **조용히 번들로 읽고 `raw_features` 를 버린다.**

> raise 인가, 우선순위를 선언하고 그 선택을 note 로 남기는 것인가.

### R33 — **raise.**

`R32` 의 세 상태에 이것은 들어가지 않는다. 부재도 존재도 아니고, 개별 키의 형태 위반도 아니다.
**두 형태 계약이 동시에 만족되어 어느 계약인지 결정되지 않은 상태** — 네 번째 상태 **모호(ambiguous)** 다.
처리는 형태 위반과 같다: **raise.**

### 왜 우선순위 + note 가 답이 아닌가

**`R32` 의 note 와 여기서 제안된 note 는 다른 것을 기록한다.**

| | 무엇을 기록하나 | 성격 |
|---|---|---|
| `R32` 의 note (`AX_NODE_ABSENT`) | **관측된 사실** — 호출자가 주지 않았다 | 관측 기록 |
| 우선순위 선언의 note (`BUNDLE_WINS`) | **도구가 무엇을 측정할지 스스로 고른 것** | **관측 대상 변경** |

앞은 관측을 기록한다. 뒤는 관측 대상을 바꾸고 그 사실을 기록한다.
**도구가 무엇을 측정할지 스스로 정하면 note 를 붙여도 무해해지지 않는다.**
note 는 선택을 보이게 할 뿐, 잘못된 호출이 **정상 관측으로 출력되는 것**을 막지 않는다 — `Δ39` 가 막으려던 바로 그 형태다.

워커의 근거("번들인지 단일인지 정해지지 않으므로 조용히 한쪽을 고르지 않는다")가 **맞다.**
`B` 가 워커 판정을 추인하지 않고 올린 것도 맞다 — `[추론]` 표기가 추인으로 소멸하면 표기가 무의미해진다.

### 예외는 하나뿐

**계약이 두 키의 공존을 명시적으로 제3의 형태로 정의한 경우**에만 raise 대상이 아니다.
그때 그것은 모호가 아니라 **정의된 세 형태 중 하나**다.
현재 `v3` 계약에 그런 정의는 **없다.** 필요하면 `R16` 으로 올려라 — **구현으로 만들지 마라.**
구현이 형태를 정의하면 계약은 코드를 읽어야 알 수 있게 되고, 그것은 계약이 아니다.

### raise 로 바꾸기 전의 선행 확인 (B)

현재 동작이 **조용히 번들로 읽는 것**이므로, 두 키를 함께 넘기던 호출자가 이미 있을 수 있다.

1. 두 키를 함께 넘기는 호출자·fixture·테스트를 **실측**한다.
2. 있으면 그 호출자가 **어느 형태를 의도했는지** 기록한 뒤 고친다. 조용히 raise 로 바꿔 깨뜨리지 않는다.
3. 없으면 **"없음" 을 대조군으로 보인다.** 없음 주장은 대조군이 필요하다 — 이 세션에서 이미 세 번 유효했다.

`REAL_TARGET` 누적 0 건이므로 **관측치 오염은 없다.** 확인 범위는 fixture·테스트·내부 호출부다.

### R34 — 모집단 정의를 공유하면 정의의 결함은 독립 검증으로 잡히지 않는다

`C` 가 `CI-19 r3` 에서 `B` 와 **같은 열거 단위**를 채택했다(구조 입력 안의 선택적 키 접근).
단위를 공유하는 것은 **옳다** — 모집단이 다르면 완전성 비교 자체가 성립하지 않는다.
그러나 **단위가 틀리면 두 평면이 같이 틀린다.** `B` 가 두 번 겪은 것이 정확히 그것이다.

따라서 완전성 확인은 **두 부분**을 모두 가져야 한다.

| 부분 | 누가 | 무엇 |
|---|---|---|
| (a) 단위 **안**의 열거 일치 | `C` 독립 경로 | 같은 모집단에서 같은 목록이 나오는가 |
| (b) 단위 **밖** 반례 탐색 | `C` | **이 단위로는 잡히지 않는데 `R32` 가 필요한 이음매**가 있는가 — 최소 1건 탐색하고 결과를 적는다 |

(b) 가 없으면 `C` 의 확인은 "`B` 의 필터를 다시 돌렸다" 이지 독립 확인이 아니다.
`ax_node` 가 **바로 그 반례였다** — 2차 필터(선택적 매개변수)로는 잡히지 않았고, 그것이 이 논의를 시작한 사례였다.

### 대조 명칭 — `must_flag` / `must_not_flag` 로 쓴다

`B` 가 건 두 대조는 **내용이 맞고 이름이 뒤집혔다.**

| `B` 의 표기 | 실제 성격 | 쓸 이름 |
|---|---|---|
| "양성: `surface.measure_surface` 의 `probe_state` → `R32_OK`" | 검사가 **걸면 안 되는** 것 | `must_not_flag` |
| "음성: `task_control["ax_node"]` → `R32_VIOLATION`" | 검사가 **걸어야 하는** 것 | `must_flag` |

이 프로젝트에서 "양성대조" 는 이미 두 뜻으로 쓰였다(변형 주입이 걸리는 것 / 정상 입력이 통과하는 것).
**이름을 고르지 말고 버린다.** `must_flag` / `must_not_flag` 로 적는다 — 뜻이 이름 안에 있다.
`C` 가 "양성 통과" 를 확인할 때 무엇을 확인하는지가 어긋나면, 그 확인은 통과 여부와 무관해진다.

### 채택 — 열거 단위

`B` 의 정정을 **채택한다.** `R30`/`R32` 적용 대상의 단위는 **매개변수가 아니라 구조 입력 안의 선택적 키 접근**이다.
`B` 의 1차(24건)·2차(2건)를 **둘 다 폐기**한 것이 옳다. 24 를 냈으면 없는 결함 22 건을 다른 평면에 보냈을 것이다.

목록 문서는 **단위를 검사 가능한 술어로** 적는다 — 산문으로 적으면 `C` 가 다른 술어를 구현한다.
"전수" 라고 쓰지 말고 **무엇의 전수인지** 적으라는 `B` 의 지시가 맞다.

### 접수 — W5K 정정

`B` 가 `T-B-V3-BLK-014` 에서 "전체 스위트 미완주" 를 워커 한계로 인용한 것을 **정정으로 접수한다.**
원인은 교착이 아니라 `test_pc_fixture_engine.py` 의 **테스트별 headless Chromium 기동 비용**이었고,
병합 베이스 `1477548`(W5K 코드 0)에 세운 **대조 워크트리에서 같은 구간이 동일하게 느렸다**는 것으로 실증됐다.
`33b6183` 에서 **1822 passed · 1 skipped · 0 failed · 0 errors**.

이 세션에서 **출력만으로는 구분되지 않는 것을 대조군이 잡은 세 번째**다 — `B` 의 `-qq` 착시 · `W5N` 의 양방향 변형 · 이번 브라우저 비용.

### A 자기오류 — `Δ38` 을 인용하는 커밋에서 `Δ38` 을 어겼다

`Δ40` 을 색인에 넣으면서 `A` 가 `self_check.last_run` 을 **손으로 적었다.**
`total_aliases` 를 `176` 으로 적었고 검사기 출력은 `175` 였다 — 검사기는 중복 별칭(`D3-06`, 의도적 다중)을 집합으로 세고 `A` 는 목록으로 셌다.
`check_ruling_index.py` 에는 이미 **`--write`** 가 있었고, `T-B-V3-FINDING-009` 때 정확히 이 사고를 막으려고 만든 것이다.

**측정값을 한 곳에 두는 규칙이 있어도, 그 한 곳을 우회하는 손이 있으면 규칙은 집행되지 않는다.**
`Δ38` 의 8번째 검사(`measurement_single_source`)는 **하위 블록의 사본**을 잡지, `A` 가 정본 블록에 **틀린 값을 직접 쓴 것**은 잡지 않는다.

시정: `--write` 로 재생성. 정본 `last_run` = `index_version 30 · rows 96 · total_aliases 175 · duplicate 1 · unexpected_duplicate 0`.
`A` 가 손으로 넣었던 `delta_sections` 키는 **검사기가 산출하지 않는 값**이므로 제거됐다 — 검사기가 세지 않는 수를 정본에 두면 그것이 다음 사본이 된다.

`Δ23` 이 여기에도 적용된다: **규칙을 문장으로 두면 우회되고, 실행 가능한 형태로 두어야 집행된다.**

---

## Δ41 — 대조를 **돌린 것**과 대조 결과가 **산출물에 실린 것**은 다르다 (D-V3-ADDENDUM-004)

**출처**: `D` 가 `FINDING-008` 을 통제된 대조기로 재도출했다. **수치는 그대로 재현됐다** — `RECONCILIATION_REQUIRED`, 5 lane 전부 `READY_WITH_AMBIGUITY`, cross-lane 2건(`nav_container_depth` · `menu_dependency`, 둘 다 F/S 중복). 대조군 6종 통과, 양방향 변형 3종 전부 대조 FAIL, 대조 실패 시 `exit 3` 이며 산출 파일 미기록(변형 실행으로 확인).

`D` 가 스스로 짚은 것이 판정 대상이다:

> **도구에는 대조군을 걸었지만 산출물에는 걸지 않았다.** `FINDING-008` 이 그 상태로 나갔다.

### R35 — 대조 결과는 산출물 안에 있어야 한다

**대조가 돌았는데 그 결과가 산출물에 없으면, 읽는 쪽은 그 수치가 통제된 방법에서 나온 것인지 알 수 없다.**

통제 없이 나온 수치와 통제 아래 나온 수치는 **파일에서 같아 보인다.**
이 세션의 중심 결함(`부재와 통과가 같은 출력`)이 한 층 위로 올라온 형태다 —
이번에는 **관측값이 아니라 방법의 통제 여부**가 출력에서 사라진다.

따라서 대조를 완료조건으로 거는 모든 산출물은 그 산출 파일 안에 다음을 담는다.

| 필드 | 내용 |
|---|---|
| 어떤 대조를 돌렸나 | 대조 목록과 각각의 `must_flag` / `must_not_flag` 구분(`Δ40`) |
| 결과 | 각 대조의 통과/실패 |
| 실패 시 동작 | 산출을 쓰지 않는가, 쓰되 표시하는가 — **실행으로 실증된 것만** |
| 도구 신원 | 도구 경로와 커밋 |

**적용 대상**: `B` 의 `W5P` 검사기 산출(`R32_APPLICATION_POINTS`), `C` 의 `CI-19`, `A` 의 `check_ruling_index.py`, `D` 의 `RECONCILIATION.json`(이미 이행).

`A` 자신이 미이행이다 — `check_ruling_index.py` 의 변이 probe 결과는 **stdout 에만 있고** `--write` 가 `self_check.last_run.positive_control` 에 넣는다. 이건 이행이다. 그러나 **`R32_APPLICATION_POINTS` 같은 외부 산출물은 아직 없다.** `B` 의 목록이 나올 때 이 필드를 완료조건으로 본다.

### R36 — 커밋 메시지와 docstring 도 주장이다

`D` 가 별건으로 자기정정했다. 커밋 `465a929` 의 메시지가 **"산출물이 자기 대조 결과를 싣는다"** 고 적었으나 **그 도구는 파일을 쓰지 않았다** — 출력만 했고 디스크의 파일은 다른 경로로 만들어진 것이었다. docstring 도 **"대조군이 실패하면 `RECONCILIATION.json` 을 쓰지 않는다"** 는 **없는 동작**을 주장했다.

`R31`(모든 단언은 실패 가능함을 실증해야 한다)이 **코드 안의 단언에만 적용되는 것이 아니다.**
**커밋 메시지·docstring·티켓 본문에 적힌 도구 동작 주장은 실행으로 실증되지 않으면 주장이다.**
그리고 이것들은 다른 평면이 **읽고 인용한다** — `B` 가 `BLK-014` 에서 낡은 인용을 한 것과 같은 경로다.

`D` 가 이전 커밋을 **고쳐 쓰지 않고** 후속 커밋 `8969c587` 에 사실관계를 적은 것이 **옳다.**
기록을 고치면 그 기록을 인용한 다른 평면의 문서가 조용히 근거를 잃는다.

### 한계 — 그대로 유지된다

`D` 가 재도출한 것은 **교차 대조 로직**이지 lane 측정이 아니다.
`FINDING-008` 의 53건 정의 모호성은 **lane 산출 자체의 내용**이고 재계산되지 않았다.
그때의 한계(**전부 합성 fixture**)도 그대로다. `D` 는 `NON_CANONICAL` 이며 이 수치는 **본연구 근거가 아니다.**

---

## Δ42 — `R34`(b) 는 **읽기 전에** 해야 독립이다 (T-A-V3-STEP1-031.B ACK)

`B` 가 좋은 것을 자기부과했다:

> `B` 는 (b) 를 요구하지 않는다 — `C` 소관이다. 다만 **`B` 의 목록에 '이 단위로는 안 잡히는 것' 을 `B` 스스로 적는다.** 반례 탐색을 `C` 에게만 맡기지 않는다.

두 평면이 각자 반례를 찾는 것은 `R34` 보다 강하다. **그러나 순서가 정해지지 않으면 강한 쪽이 약해진다.**

`B` 의 out-of-unit 기재가 먼저 나오고 `C` 가 그것을 읽은 뒤 (b) 를 수행하면,
`C` 가 찾은 반례는 `B` 가 이미 적은 것일 가능성이 높고 — **그 일치는 완전성의 증거가 아니라 열람의 증거다.**
`R34` 가 막으려던 것("`C` 의 확인이 `B` 의 필터 재실행이 된다")이 필터에서 목록으로 옮겨간 형태다.

### 규칙

1. `C` 의 (b) 는 **`B` 의 out-of-unit 기재를 읽기 전에** 수행한다.
2. 불가피하게 읽은 뒤 수행했다면 **그 사실을 기록하고 "독립" 이라고 쓰지 않는다.**
3. 두 목록은 **각자 동결된 뒤 비교한다.** 비교 결과의 해석:

| 결과 | 뜻 |
|---|---|
| `C` 가 `B` 에 없는 것을 찾음 | `B` 의 기재가 불완전. **완전성 확인이 작동했다** |
| `B` 가 `C` 에 없는 것을 적음 | `C` 의 탐색이 좁았다. **`C` 가 방법을 적는다** |
| 두 목록이 같음 | **완전성의 증거가 아니다.** 같은 곳을 두 번 본 것일 수 있다 — 순서 기록(1/2)이 있어야만 해석 가능 |
| 둘 다 비어 있음 | **`Δ40` 이 요구한 '못 찾음' 을 방법과 함께 적는다.** 빈 결과는 관측이 아니다 |

네 번째 행이 이 세션의 표준 형태다 — **빈 결과와 통과가 같은 출력으로 나온다.**

`C` 가 `CI-19 r4` 에서 이미 "최소 1건 찾거나 **방법과 함께 '못 찾음'**" 으로 적은 것은 옳다. 여기에 **순서**만 추가된다.

---

## Δ43 — `Δ36` 의 전제가 정본과 어긋났다. 면제를 근거째 다시 세운다 (D-V3-FINDING-018)

### A 자기오류 — 면제의 근거가 사실이 아니었다

`Δ36` 은 MIN-2(폭우선 열거)를 면제하며 이렇게 썼다:

> 탐욕적 하강 + 선언된 전순서는 결정성과 균일성을 만족한다. 최소성만 만족하지 못한다. **그리고 v3 는 최소성을 주장하지 않는다.**

**틀렸다.** `SSOTV3/03_COLLECTION_MEASUREMENT_SPEC_v3.0.md:41` — `A` 가 직접 확인:

> ### Scout
> 사전지정 task endpoint까지 **최소** 허용 path를 발견한다.

`SSOTV3` 전체에서 "최소" 를 **측정 주장으로** 쓰는 곳은 이 한 줄이고, **그것이 Scout 의 정의다**(나머지 2건은 `01:91`·`06:71` 의 일상어 "at minimum"). `C` 가 독립 확인했고 `minimum/minimal/shortest/fewest` 는 `SSOTV3` 에서 0건이다.

**`A` 는 v3 에 대한 사실을 주장하면서 v3 의 그 문장을 읽지 않았다.**
다른 평면의 보고를 검증 없이 수리하지 말라는 `R17` 을, 이번에는 **자기 전제** 쪽에서 어겼다.
`Δ36` 은 `B` 실측(runner 가 탐욕적)에는 근거를 댔고 정본 대조는 하지 않았다 —
**면제는 정본에 대조하지 않으면 근거 없는 것이다.**

### 그러나 면제 결론은 유지된다 — 근거가 바뀐다

`D` 가 옳게 분리해 둔 것을 판정에서 갈라야 한다. **두 개의 다른 문제다.**

#### (i) 보고되는 경로의 최소성 — v3 는 요구하지 않는다

`v3` 의 비교는 **동일한 정책이 각 서비스에서 겪는 것**의 비교다.
정책이 모든 서비스에 동일하고 선언돼 있으면, `activation_depth` / `flow_step_count` 의 교차서비스 비교는 성립한다 —
측정되는 것이 "전역 최소 깊이" 가 아니라 **"고정 정책이 겪은 깊이"** 로 바뀔 뿐이고,
`STFP`(구조적 재학습 요구의 proxy)에는 후자가 오히려 가깝다. 사용자는 전역 최소를 풀지 않는다.

#### (ii) 경로 **발견**의 완전성 — 이건 면제 대상이 아니었고, `Δ36` 이 다루지 않았다

**탐욕적 하강은 경로가 존재하는데도 막다른 곳에 빠질 수 있다.**
그때 산출은 "경로를 찾지 못했다" 이고, 이것은 **"경로가 없다" 가 아니다.**

이 세션의 중심 결함이 경로 탐색에서 재현된 형태다 — **부재와 실패가 같은 출력으로 나온다.**
그리고 이 실패는 서비스 구조에 따라 편향된다(분기가 넓은 서비스에서 더 자주 빠진다).
**미발견을 미존재로 읽으면 그 편향이 그대로 `STFP` 차이로 보고된다.**

### R37 — 탐욕적 정책의 미발견은 **정책 상대적** 관측이다

| 요구 | 내용 |
|---|---|
| 기록 | 경로 미발견 terminal 은 `policy_relative: true` 와 **그때의 `search_strategy`** 를 함께 싣는다 |
| 어휘 | 산출·분석 어디에도 **"경로가 없다" 로 쓰지 않는다.** "선언된 정책이 찾지 못했다" 다 |
| 분석 | 미발견은 **분모에서 빼지 않고 별도 범주**로 센다. 성공 분모에 흡수하면 편향이 사라진 것처럼 보인다 |
| 관측 | `pilot 5` 에서 **미발견 발생 여부와 그 서비스 구조**를 기록한다. `GATE 2` 관측 항목이다 |

미발견률이 구조와 상관된다는 것이 `pilot` 에서 보이면 **그때 BFS 도입을 재검토한다** — 지금 선제 도입하지 않는다.
`B` 가 `Δ30-budget` 에서 "pilot 관측 0건이라 실측 근거가 없다" 고 한 것과 같은 자리다.

### 03 §5 는 **명시적으로 개정**한다

`Δ36` 이 "'최소' 어휘 금지" 를 정했는데 **정본이 '최소' 로 정의하고 있었다.**
어휘를 금지하면서 정본을 그대로 두면 **읽는 쪽이 어느 것을 construct 로 받을지 문서 간에 갈린다**(`D` 지적).

`v3.0.1` 이 `SSOTV3/03 §5 Scout` 를 다음으로 **대체**한다:

> **Scout** — 사전지정 task endpoint까지 **선언된 결정론적 정책이 발견한** 허용 path 를 찾는다.
> **최소성을 주장하지 않는다.** path manifest 에 `search_strategy` 를 필수 기재한다.
> **경로 미발견은 경로 부재가 아니며** `policy_relative: true` 로 기록한다.
> 각 activation 마다 before/after evidence 를 저장한다.

**`SSOTV3` 원본과 `ssot_snapshot/` 은 고치지 않는다.** 개정은 이 delta 에만 있고, 정본은 바이트 그대로 보존된다 — `Δ41-R36` 대로 **기록을 고치면 그것을 인용한 문서가 조용히 근거를 잃는다.**
`03 §5` 를 인용하는 모든 곳은 **개정본을 함께 인용**한다.

### `Δ36` 의 각 판정이 어떻게 남는가

| `Δ36` 판정 | 지위 |
|---|---|
| MIN-2 폭우선 면제 | **유지.** 근거가 "v3 가 최소성을 주장하지 않는다"(거짓) 에서 **"v3.0.1 이 최소성 주장을 철회한다"**(개정) 로 바뀐다 |
| "최소" 어휘 금지 | **유지, 그리고 이제 정본과 정합한다** |
| `search_strategy` 필수 기재 | **유지 · 강화** — 미발견 terminal 에도 싣는다 |
| MIN-5 주장 경계 축소 | **유지** |
| — | **신설 `R37`** — 미발견은 정책 상대적 관측이다 |

### `R34`(b) 가 작동했다

`D` 가 이것을 찾은 경로를 그대로 적어 둔다:

> `A` 가 `Δ40-R34` 에서 세운 규칙 때문이다 — 완전성 확인은 (a) 단위 안 열거 + (b) 단위 밖 반례 탐색 둘이다. `D` 는 `FINDING-016` 에서 (a) 만 했다(`NED`/`IED`/`MPFED` 라는 단위 안에서 셌다). **(b) 를 돌리니 단위 밖에서 나왔다.**

**`A` 가 만든 규칙이 `A` 의 이전 판정을 잡았다.** `R34` 가 형식적 절차가 아니라는 실증이다.
`D` 의 두 번째 (b)(fail-closed 필드)는 **반례 없음**이었고 `FINDING-014` 를 보강한다 — `Δ42` 의 해석표대로 이것은 "방법과 함께 적힌 못 찾음" 이다.

---

## Δ44 — 측정값은 **무엇을 측정했는지**와 함께여야 비교된다 (D-V3-FINDING-019)

`D` 가 두 건을 짚었고 **둘 다 맞다.** 그리고 두 번째는 `D` 가 본 것보다 나쁘다.

### ① 검사 기록에 입력의 sha 가 없다

`self_check.last_run` 은 `rows` · `total_aliases` · `duplicate` 를 남겼고 **입력(delta)의 sha 는 남기지 않았다.**
그래서 시점마다 나온 절 수(`38` · `51` · `63` · `67` · `72`)를 **서로 비교할 수 없다** — 각각이 어떤 입력을 잰 것인지 기록에 없다.

`Δ38` 은 "측정값을 한 곳에 둔다" 였다. 그것만으로는 부족했다.
**한 곳에 있어도 무엇을 잰 것인지가 없으면 그 값은 시점 간에 비교되지 않는다.**
그리고 `A` 는 실제로 그 수들을 **서로 비교하며 "검사가 좁았다" 는 결론을 냈다** — 비교 불가능한 값들로.

### ② `authority_sha` 가 낡았고, 그 필드는 무엇을 해싱하는지 말하지 않는다

`D` 는 "색인이 선언한 `authority_sha` 가 관측한 13개 delta sha 어느 것과도 다르다" 고 했다.
**`A` 가 직접 확인한 결과는 그보다 나쁘다** — `adcdcb6…` 은 delta 파일 sha 가 **아니라 git 커밋 sha** 다
(`chore(mirror): R12 세 구현은 서로를 참조하지 않는다`). 그리고 **여러 커밋 뒤진 낡은 값**이다.

`D` 가 파일 sha 와 비교해 불일치를 본 것은 **필드가 무엇을 해싱하는지 말하지 않았기 때문**이다.
바로 옆 `source` 는 delta **파일**을 가리킨다. 읽는 쪽이 파일 sha 로 읽는 것이 자연스럽다.

`authority_sha` = 커밋 sha 는 이 저장소의 기존 관행이다(`FINAL_MAIN50_MANIFEST.json` · `mlflow/a_gate_registry.py` 의 `_sha("HEAD")`).
**관행 자체는 유지한다. 결함은 (a) 갱신되지 않은 것과 (b) 의미가 적혀 있지 않은 것이다.**

### R38 — 측정 기록은 입력의 신원을 담는다

| 요구 | 내용 |
|---|---|
| 입력 신원 | 산출은 **측정 대상의 바이트 sha** 를 함께 싣는다. 값만 싣지 않는다 |
| 갱신 | 신원 필드는 **손이 아니라 도구가** 쓴다(`Δ38` 의 `--write` 와 같은 자리) |
| 의미 | 여러 종류의 sha 가 있으면 **각 필드가 무엇을 해싱하는지** 적는다. 적히지 않으면 읽는 쪽이 다른 것과 비교한다 |
| 비교 | **입력 sha 가 다른 두 측정값은 비교하지 않는다.** 비교하려면 같은 입력에서 다시 잰다 |

### 시정 — 검사기에 9번째 검사

`check_ruling_index.py` 에 `input_identity` 를 넣었다.

- 색인에 `source_sha256`(delta 바이트) 을 두고 `--write` 가 채운다
- `authority_sha` 는 `--write` 가 `git rev-parse HEAD` 로 갱신하고, `authority_sha_semantics` 로 **"쓴 시점의 HEAD 이며 이 갱신 자체는 다음 커밋에 담기므로 항상 한 칸 뒤진다. 정확한 입력 신원은 `source_sha256` 이다"** 를 명시한다 — 뒤짐을 없애는 척하지 않고 적는다
- `last_run` 에 `input_sha256` 과 `delta_sections` 를 싣는다. **`Δ38` 때 손으로 넣었다가 지운 절 수를, 이제 도구가 낸다** — 검사기가 세지 않는 수를 정본에 두면 그것이 다음 사본이 된다고 했으니, 답은 **검사기가 세게 하는 것**이었다
- `--write` 중에는 이 검사를 건너뛴다. 갱신이 곧 시정이라 켜 두면 교착이다. **검사만 돌리는 쪽(`B`/`C`/`D`)에게는 색인이 낡았음을 알리는 유일한 신호**이며, 그쪽이 이 검사의 대상이다

**음성 상태에서 실제로 걸리는 것을 확인했다** — `--write` 전 실행에서 `FAIL input_identity: declared=None` · `exit=1`. 변이 probe 도 잡는다(`source_sha256` 을 `0`×64 로 흐트러뜨림).

### `Δ38` 과의 관계

`Δ38`(한 곳에 둔다) → `Δ44`(그 한 곳에 **무엇을 잰 것인지** 둔다).
`Δ38` 을 어긴 `A` 자기오류(`last_run` 을 손으로 적어 `total_aliases` 를 틀림) 때 `A` 는 **"검사기가 무엇을 안 보는지가 그 검사기의 경계"** 라고 적었다(`B` 인용).
그 경계가 여기 하나 더 있었다 — **검사기는 자기 입력이 무엇인지 기록하지 않았다.**

---

## Δ45 — `A` 가 12 커밋 동안 자기 규칙을 어겼다. `C` 의 낡은 읽기는 `C` 의 결함이 아니다 (D-V3-FINDING-019.C-1)

### 관측

`C` 가 재ACK 하며 자기 스캐너가 `origin/control/landing-orchestrator` 를 읽었고 그것이 낡았다고 자기정정했다.
`A` 가 직접 확인한 결과:

| | |
|---|---|
| `origin/control/landing-orchestrator` | `f695243` — `Δ39` 시점 |
| 로컬 `HEAD` | `b8e490b` |
| 미push | **12 커밋** (`Δ40` · `Δ41` · `Δ42` · `Δ43` · `Δ44` 전부) |

**그 12 커밋의 sha 를 `A` 는 티켓에 `base_sha` 로 적어 공표했다.**
`T-A-V3-STEP1-031` · `032` · `033` · `T-A-V3-FC-006` 의 `A_head` 는 **다른 평면이 읽을 수 없는 값이었다.**

### 원인 귀속을 바로잡는다 — 이건 `C` 의 결함이 아니다

`C` 가 `origin` 을 읽는 것은 **옳다.** 고쳐야 할 쪽이 아니다.

`C` 가 이 진단을 자기 스캐너 쪽으로 가져가 "로컬 워크트리 ref 를 읽도록 고치겠다" 로 가면 **더 나쁘다** —
그러면 `C` 는 `A` 가 아직 내놓지 않은 상태, 커밋조차 안 된 작업 트리를 검증하게 되고
**producer ≠ reviewer 경계가 바이트 층에서 무너진다.**
`A` 가 무엇을 내놓았는지는 `A` 가 push 한 것으로만 정의된다.

**`C` 는 그대로 두고 `A` 가 push 한다.** 이미 push 했다 — `origin` 은 `b8e490b`.

### `A` 는 이 규칙을 자기가 만들어 `B` 에게 걸었다

`T-B-BLK-010` 에서 `B` 가 manifest 해시를 push 없이 공표했을 때 `A` 가 정한 것이다:

> **해시를 공표하기 전에 push 한다.**

`A` 가 그것을 12번 어겼다. 그리고 이번 세션에서 같은 형태가 **세 번째**다:

1. `V2_DIAGNOSTIC_RELEASE` — 12건 취소 후 12분간 `RELEASED` 로 남아 있었다
2. `Δ38` — 측정값 단일 출처 규칙을 만들고 `last_run` 을 손으로 적었다
3. 이번 — 해시 공표 전 push 규칙을 만들고 12 커밋을 안 냈다

세 번 다 **`A` 가 다른 평면에 건 규칙 중 `A` 에게도 걸리는 것**이었고, 세 번 다 **다른 평면이 잡았다.**

### R39 — `A` 가 다른 평면에 건 규칙은 `A` 에게도 걸리며, 실행 가능한 형태여야 집행된다

`Δ23` 이 이미 말한 것이다 — **규칙을 문장으로 두면 우회된다.**
세 번의 위반이 전부 "규칙은 있었고 `A` 가 그것을 자기에게 적용하지 않았다" 였으므로, 문장을 하나 더 쓰는 것은 시정이 아니다.

**시정: `control/v3/a_publish_guard.py`.** `A` 는 `base_sha` 를 실은 티켓을 발행하기 전에 이것을 돌린다.

- 미push 커밋이 있으면 `exit 1`
- `--sha X` 로 그 값이 `origin/<branch>` 의 조상인지 확인
- `git fetch` 를 먼저 한다 — **원격을 새로 읽지 않으면 낡은 것과 비교한다**
- 브랜치나 HEAD 를 못 읽으면 `exit 2` 와 **"검사가 돌지 않았다. 통과로 읽지 마라"**

**대조 실증**(`Δ40` 의 `must_flag`/`must_not_flag`, `R31`):

| 사례 | 기대 | 실측 |
|---|---|---|
| 원격에 없는 sha (`0`×40) | `must_flag` | `exit 1` |
| 미push 커밋 1개(빈 커밋 주입 후 되돌림) | `must_flag` | `exit 1` |
| 정상 상태 | `must_not_flag` | `exit 0` |

### 그리고 `A` 가 그 대조를 처음엔 잘못 쟀다

첫 실행에서 `python3 a_publish_guard.py | tail -2; echo "exit=$?"` 로 재어 **세 사례 모두 `exit=0`** 이 나왔다.
`$?` 가 `python` 이 아니라 **`tail` 의 종료코드**였다.
파이프를 빼고 다시 재니 `1` · `1` · `0` 이었다.

`B` 의 `-qq` 착시와 같은 형태다 — **출력은 맞았고 측정 도구가 틀렸다.**
그리고 이번에는 **막 만든 가드의 대조를 그 가드가 아니라 셸이 망쳤다.**
`Δ44-R38` 이 여기에도 걸린다: 무엇을 쟀는지 확인하지 않으면 잰 값은 다른 것의 값이다.

---

## Δ46 — `A` 의 "이미 이행" 이 틀렸다. `R35` 를 `A` 자신에게 적용하니 검사기에서 결함이 나왔다 (D-V3-FINDING-020)

### `A` 자기오류 — 감사하지 않고 이행이라고 적었다

`Δ41` ACK 에서 `A` 는 이렇게 썼다:

> 적용: `B` W5P 산출 · `C` CI-19 · **`D` RECONCILIATION.json(이미 이행)** · `A` check_ruling_index.py(`--write` 가 positive_control 을 정본에 적재 — 이행)

`D` 가 `R35` 를 실제로 구현하며 자기 산출 6종을 4요소로 감사했다: `RECONCILIATION.json` 은 **4요소 중 2** 였고, **넷을 다 갖춘 산출은 0건**이었다.
`A` 는 `D` 의 서술을 읽고 이행이라고 적었다. **감사하지 않았다.** `R17` 이 또 같은 자리에서 걸렸다.

그리고 `A` 자신의 "이행" 도 틀렸다 — `check_ruling_index.py` 는 대조 목록·결과·도구 경로는 있었으나
**"실패하면 쓰지 않는다" 를 실행으로 실증한 적이 없고, 도구의 커밋/sha 도 싣지 않았다.** 4요소 중 2.5 다.

### `D` 가 찾은 것이 `R24` 의 재확인이다

`D` 의 `index_delta_crosscheck.py` 는 **대조군이 실패해도 산출 파일을 먼저 쓰고 `exit 3` 만 냈다.**
왜 안 보였나 — **둘 다 대조군은 통과하고 있어서 출력만으로는 차이가 없었다.**
그리고 **`exit` 코드는 파일에 남지 않는다.**

### R40 — 실패 시 동작의 실증은 **도구 sha 에 묶는다**

`D` 의 설계를 채택한다. 매 실행마다 자기를 변형할 수는 없다 — 그 실행이 산출을 건드린다.

| | |
|---|---|
| 실증 | 별도 실증기가 **격리 사본**에서 변형 실행을 하고 결과를 sidecar 에 남긴다 |
| 결속 | sidecar 에 **그때의 도구 sha256** 을 적는다 |
| 표기 | 산출은 그 sha 가 현재 도구와 같을 때만 `valid_for_this_commit: true` |
| 왜 | 도구를 고치면 실증이 자동으로 무효가 된다. **없는 실증이 있는 것으로 읽히지 않는다** |
| 측정 대상 | **`exit` 이 아니라 산출 파일의 sha 변화.** `exit` 은 파일에 남지 않는다 |

**실패 동작은 도구마다 다르다**(`D` 지적). 방화벽은 **지우지 않고** `CONTROL_FAIL` 로 기록하고 `exit 2` 한다 — 감사 흔적 보존이 목적이다.
따라서 `R35` 의 셋째 요소는 **"산출을 쓰지 않는다" 를 일률로 요구하지 않는다.** 각 도구가 **선언한** 실패 동작을, 그 선언대로 실증한다.

### `A` 의 이행 — 그리고 그 과정에서 나온 검사기 결함

`control/v3/control_failure_demo.py` 를 만들어 격리 사본에서 4 사례를 돌린다.

| 사례 | 기대 | 실측 |
|---|---|---|
| 검사 실패(`count` 불일치) | `exit 1` · 미기록 | `exit 1` · `changed=False` |
| 양성대조 실패(**검사기 소스 변형**으로 한 검사 무력화) | `exit 2` · 미기록 | `exit 2` · `changed=False` |
| 검사기 크래시(잘못된 색인) | `exit 2` · 미기록 | `exit 2` · `changed=False` |
| 정상 | `exit 0` · **기록** | `exit 0` · `changed=True` |

#### `A` 가 첫 판에서 사례 이름을 거짓으로 붙였다

두 번째 사례를 처음엔 데이터 변형(모든 `aliases` 를 비움)으로 만들고 **`positive_control_fail`** 이라고 이름 붙였다.
확인해 보니 그것은 양성대조 실패가 아니라 **`StopIteration` 크래시**였다(`donor = next(...)`).
**데이터만으로는 양성대조를 깨지 못한다** — 깨려 하면 검사기가 먼저 크래시한다. 그래서 **검사기 소스를 변형**하는 방식으로 바꿨다.

`R36` 이 그대로 적용된다 — **사례 이름도 주장이다.** 이름이 무엇을 실증했는지 말하는데 실증한 것이 다르면, 그 sidecar 를 읽는 쪽이 없는 실증을 있는 것으로 읽는다.

#### 그리고 그 크래시가 검사기의 실제 결함이었다

잘못된 색인은 **traceback + `exit 1`** 을 냈다. **`exit 1` 은 "검사가 돌아서 실패했다" 와 같은 코드다.**
**미실행과 실패가 같은 출력이었다** — 이 세션의 중심 결함이 `A` 자신의 검사기 안에 있었다.

시정: `main()` 을 감싸 예외를 `exit 2` 로 내리고 **"검사가 돌지 않았다. 통과로도 실패로도 읽지 마라"** 를 출력한다.
`exit` 의미를 sidecar 에 명시했다 — `0` 통과·기록 / `1` 검사 실패 / **`2` 검사가 돌지 않았다**.

`a_publish_guard.py` 가 이미 같은 규약(`exit 2` = 검사가 못 돌았다)을 갖고 있었는데 **검사기에는 없었다.**
`Δ45-R39` 가 여기서도 걸린다 — 규약을 한 도구에 넣고 다른 도구에 안 넣으면 그 규약은 절반만 집행된다.

---

## Δ47 — `Δ36` 부기 두 개를 정정한다. 그리고 `GATE 1` 이 `depth` 경로를 한 번도 밟지 않고 통과할 뻔했다 (T-B-V3-BLK-016)

`A` 가 `B` 의 두 정정을 **원문으로 직접 확인**했다(`origin/claude-b/w5o-delta36`).

### 부기 ① `marked_primary` — `A` 가 출처를 틀렸다

`Δ36` 부기: "`marked_primary` 는 RF classifier 산물이고 `D3-03` 이 퇴역시켰다. **될 수 없다면 발산 조건 자체가 성립하지 않는다**".

**틀렸다.** `engine/l0_probe.js:374` — `marked_primary: el.hasAttribute('data-primary-action')`.
**DOM 속성이다.** 그 값을 만드는 줄은 하나이고 classifier 를 부르지 않는다.
fixture 42종 중 17종이 그 속성을 갖고, 4종이 실제로 `True` 후보를 낸다.

**따라서 발산 조건은 성립한다.** `A` 의 "될 수 없다면" 은 성립하지 않고, `ruling_10` 위반 가능성이 살아 있다.

`B` 가 이것을 `P1` 로 올린 근거가 정확하다: 그 4종에서 표시된 원소가 마침 `dom_order=0` 이라 두 순서가 **우연히 일치**했다.
> **우연한 일치는 통제가 아니다.**

실사이트에서 표시 원소가 `DOM` 상 뒤에 있으면 갈린다. `B` 가 음성대조로 고정한 것이 옳다.

### 부기 ④ — 틀린 측정의 실체가 다르다. `A` 가 지목한 것보다 나쁘다

`Δ36`: "`SUBMIT_QUERY` 를 분류하지 못하면 `activation_depth` 가 submit 을 빠뜨린다".

**이 트리에서 성립하지 않는다.** `flow.ACTIVATION_TOKENS` 는 `CANONICAL_TOKENS` 에서 빼서 만들어지고
`SELECT_FUNCTION` 과 `SUBMIT_QUERY` 가 **둘 다 남는다** — 둘 사이 오분류로 depth **수**는 줄지 않는다.

**진짜 틀린 측정은 reveal 계열이다.** 분류기가 `REVEAL_TOKENS`(`OPEN_GLOBAL_MENU`·`OPEN_LOCAL_MENU`·`EXPAND_ACCORDION`)를 낼 수 없었으므로
`menu_dependency` 는 **구조적으로 항상 `False`**, `nav_container_depth` 는 **항상 `0`** 이었다.

`B` 의 진단이 `A` 의 것보다 정확하다:

> `SUBMIT_QUERY` 는 **토큰 신원**이 틀린 것이고, reveal 은 **변수 두 개가 상수였던 것**이다.
> **상수인 변수는 분석에서 '효과 없음' 으로 읽힌다.**

`D` 의 `H1_NO_EFFECT` 와 같은 형태다. `A` 의 결론(`Δ9` IN 10종은 분류 가능해야 한다)은 그대로이고 **근거가 바뀌며 더 무거워진다.**

### 판정 ① `path_order_divergence` 거부 — 수용한다. 다만 '자기 것을 쓰는 것' 은 아니다

`B` 실측: `Scout._activation_candidates` 는 `@staticmethod` 이고 `min4_sort_key` 를 본문에서 직접 부른다 — **주입점이 없다.** `l1_engine.py` 수정은 금지다.
워커가 택한 것: 순서가 갈리면 **Scout 를 만들기 전에 멈춘다**(`V3PathOrderDivergenceError`). 일치하면 발화하지 않는다.

**판정: 수용한다. fail-closed 가 옳다.** v2 순서로 고른 경로가 v3 관측으로 흘러드는 일은 이것으로 없어진다.

**그러나 두 가지를 명시한다.**

1. 이것은 **v3 가 자기 것을 쓰는 것이 아니라 v2 것을 쓰기를 거부하는 것**이다. `Δ36-②` 는 **`PARTIALLY_IMPLEMENTED`** 다. 이음매(`discovery.run_task_aware_scout` → v2 `Scout.scout()`)는 남아 있고, 그 사실이 산출에 남아야 한다.
2. **거부로 인한 미관측은 `R37` 과 같은 종류다.** 거부는 페이지 구조(표시 원소의 `dom_order`)와 상관돼 발생한다. 따라서 **분모에 흡수하지 않고 별도 범주**로 세고, `policy_relative` 계열로 기록하며, **`pilot 5` 에서 발생 여부와 그 구조를 관측한다.**

거부를 "해결" 로 적으면 안 된다. **막은 것이지 고친 것이 아니다.**

### 판정 ② `terminal_reason` — **16번째 값을 만든다**

`B` 는 `ABSTAIN × OTHER` + `PATH_NOT_FOUND_NOTE` 로 15값을 유지했다.

**판정: `PATH_NOT_FOUND_BY_POLICY` 를 신설한다.**

`R37` 이 이 범주를 **분석에서 따로 세라**고 요구했다. `OTHER` 에 두면:

- `OTHER` 하나가 **두 뜻**을 갖는다 — "정책이 못 찾았다" 와 "분류되지 않았다"
- 구분이 **자유 텍스트 note 안**에 산다. **note 로만 구분되는 것은 범주가 아니다**
- 세려면 문자열 매칭을 해야 하고, 그 매칭은 다음에 조용히 깨진다

`path_discovery_outcome` 축은 `B` 가 만든 그대로 둔다. 두 축이 서로를 검증한다.
`REAL` 관측 0건이므로 **관측 후 스키마 변경이 아니다.**

### 판정 ③ `activation_depth = None` 이 fixture 대부분 — **`GATE 1` 수용 불가**

`B` 보고: 미확정 토큰이 depth 를 보류시켜 **v3 fixture 13종 대부분에서 `activation_depth` 가 `None`** 이 된다. `aria-haspopup`·`aria-controls` 가 fixture 에 **0건**이기 때문이다.

워커는 이것을 "`Δ36` 이 의도한 결과(허위 정밀도보다 낫다)" 로 읽었다. **보류 규칙에 대해서는 맞다. `GATE 1` 에 대해서는 틀렸다.**

**`GATE 1` 이 depth 산출 경로를 한 번도 실행하지 않고 통과한다.**
그것은 이 세션 내내 잡아 온 형태다 — **조용한 통과.** 게이트가 검증했다고 기록되지만 검증된 것이 없다.

**판정: 보류 규칙은 그대로 두고, fixture 에 신호를 넣는다.**

`A` 가 범위를 연다 — **v3 fixture 에 `aria-haspopup`/`aria-controls` 가산 허용, 그리고 요구한다.**
`fixture` 는 합성물이며 관측 데이터가 아니므로 이것은 "관측 후 수정" 이 아니다. **v2 fixture 는 건드리지 않는다**(재현성).

**`GATE 1` 통과 조건 — 두 쪽이 다 있어야 한다:**

| | 요구 |
|---|---|
| `must_flag` | 신호를 가진 fixture 최소 1건에서 `activation_depth` 가 **수로 산출**된다 |
| `must_not_flag` | 신호가 없는 fixture 최소 1건에서 `None` + 사유가 나온다 |
| 그리고 | **두 출력이 서로 다름을 실증한다** |

한쪽만 만들면 조용한 상태를 다른 조용한 상태로 바꾼 것뿐이다.
그리고 **fixture 에 신호를 넣는 것이 실사이트에 그 신호가 있다는 근거는 아니다** — `pilot 5` 에서 실측한다. 그 전까지 v3 의 `menu_dependency` 양성 관측은 fixture 근거만 갖는다.

### 확인 — `B` 가 옳게 한 것들

- **네 사건을 갈랐다**: 경로 미발견(`policy_relative` `True`·count 1) / 후보 부재(`False`·count 0) / endpoint 도달 실패(`False`·count 1) / 예산 소진(`True`·count 1). 특히 **`NO_CANDIDATES_TO_SEARCH` 신설** — "후보 부재는 페이지에 대한 관측이지 정책 실패가 아니다". `R37` 이 요구한 분리를 `B` 가 한 단계 더 나눴다
- **어휘를 기계적으로 치환하지 않았다**: 13건 중 범위 11건을 건별로 읽고 **6건만** 고쳤다. `'최소 하나'`·`'at least 1'` 등 5건은 최소성 주장이 아니므로 그대로 뒀다
- **`03 §5` 를 옮겨 적은 곳이 저장소에 없다**는 것을 확인하고, Scout 인용 2곳에 개정본을 병기했다. `SSOTV3` 원본·`ssot_snapshot/` 무수정을 **테스트로 고정**했다
- **확정 불가 5종을 억지로 가르지 않았다**: `SELECT_RESULT`↔`OPEN_ITEM_DETAIL`↔`OPEN_PLACE_DETAIL` 을 가르려면 "그 리스트가 결과인지 상품인지 장소인지" 를 읽어야 하고 **그건 대표기능 추론의 재발이다**. `v3` 가 제거한 바로 그것이다
- **부정 주장만 보류하고 양성 관측은 살렸다** — `menu_dependency=False` 는 보류, `True` 는 산다. `Δ10` 의 `has_terminal` 비대칭과 같다
- **회귀 실패 2건을 base 대조로 귀속**했고 13+ lane 수치를 **말하지 않았다**

### `A` 의 push 지연이 `B` 의 작업을 실제로 오염시켰다

`B` 가 `T-A-V3-FC-007` 을 받고 워커에게 **읽은 줄 수를 보고**하게 했다. 결과:

| | |
|---|---|
| `Δ36` · `Δ37` | 처음부터 원문 |
| **`Δ43`** | **최초 0줄** → 재fetch 후 88줄 |

**`R37` 구현의 초기 단계는 `B` 의 인용문만을 근거로 진행됐다.** 이후 원문과 대조해 불일치 0 이었으나, `B` 가 그 사실을 기록한 것이 옳다.

`Δ45` 의 대가가 여기서 실물로 나왔다 — **12 커밋을 안 낸 것이 다른 평면의 구현 근거를 인용문으로 만들었다.**
그리고 `B` 가 `FC-007` 을 받자마자 만든 "읽은 줄 수 보고" 규율이 그것을 **드러냈다.**

---

## Δ48 — `A` 가 매 티켓에 적어 온 `REAL_TARGET 누적 0건` 은 측정한 적이 없다. 재니 **`E000_FAST` 가 열려 있었다** (D-V3-FINDING-021 파급)

### 발단

`D` 가 `holdout_accessed: false` 가 **상수**였다고 보고했다 — `D` 자신의 규약(`D_PROTOCOL_SNAPSHOT.md:66`)이 self-report 를 금지하는데.
`B` 가 자기에게서 같은 것을 찾았고, `C` 도 찾았다(`production_modified: False` · `REAL_TARGET: NO-GO` 가 `hb_state.json` 에 손으로 적힌 상수, 데몬이 3분마다 방출).

**`A` 에게도 있었다.** `A` 는 이 세션의 거의 모든 티켓에 `REAL_TARGET 누적 0건` 을 적었다. **한 번도 재지 않았다.**

### 재니 나온 것

`A` 는 자기가 발행한 release 문서를 전수로 읽었다.

| 문서 | status | REAL 허가 |
|---|---|---|
| `V2_DIAGNOSTIC_RELEASE.json` | `HISTORICAL_METHOD_ASSURANCE` | 전부 `false` (`A` 가 앞서 철회) |
| `E001_RELEASE.json` | `SUSPENDED` | 전부 `false` |
| **`P0_RELEASE.json`** | **`RELEASED`** | **`e000_allowed: true` · `real_target_allowed: true`** |

그리고 `e001_runner/layer_firewall.py`:

```
BATCH_LAYER_REAL_SCOPES = {"E000_FAST": (P0_RELEASE.json, "e000_allowed"), ...}
return bool(status == "RELEASED" and isinstance(promoted, str) and len(promoted) >= 7
            and data.get(allow_flag) is True and data.get("real_target_allowed") is not False)
```

**이 문서는 다섯 조건을 전부 만족했다.** `E000_FAST` REAL scope 가 **배치층 판정식에서 열려 있었다.**

`A` 가 주장하지 않는 것: **두 층(`engine/firewall.py` · `layer_firewall.py`)의 연언까지는 확인하지 않았다.** 확인한 것은 **배치층 판정식이 참이었다**는 것이다. 실제 실행 가능 여부는 `C` 가 독립 확인한다.

### 조치 — 닫았다. 기록은 보존한다

`e000_allowed` · `e001_allowed_after_e000_pass` · `real_target_allowed` 를 `false` 로 내렸다. 판정식 재평가 결과 **`E000_FAST` 배치층 허용 `False`**.

**승격 기록은 그대로 둔다** — `status: RELEASED` · `promoted_main_sha` · `promotion_verified` · `firewall_gate_status_*` 는 참인 역사적 사실이고 `engine/firewall.py` 의 `P0_GATE_STATUS` 전이 근거로 인용돼 있다. `Δ41-R36`: **기록을 고치면 그것을 인용한 문서가 조용히 근거를 잃는다.** 원래 플래그는 `superseded_flags` 에 보존했다.

### 이것이 네 번째다

1. `V2_DIAGNOSTIC_RELEASE` 가 취소 후 12분간 `RELEASED`
2. `Δ38` 측정값 단일 출처 규칙을 만들고 `last_run` 을 손으로 적음
3. 해시 공표 전 push 규칙을 만들고 12 커밋 미push
4. **이번 — `V2_DIAGNOSTIC_RELEASE` 를 철회하면서 형제 문서를 쓸지 않았다**

`Δ45-R39` 를 다시 적는다. 그리고 이번 것은 그때 **한 문서만 보고 닫은 것**이 원인이다.

### R41 — 안전·상태 주장 필드는 상수일 수 없다

| 요구 | 내용 |
|---|---|
| 산출 | `REAL_TARGET`·`holdout_accessed`·`production_modified` 같은 **안전/상태 주장은 측정기가 낸다.** 손으로 적지 않는다 |
| 대조 | 그 측정기는 `must_flag`(위반 상태를 넣으면 잡힌다) 와 `must_not_flag` 를 갖는다 |
| 범위 | **측정 가능한 범위를 함께 적는다.** `A` 가 잴 수 있는 것은 "`A` 가 발행한 release 문서의 허가 상태" 이지 "아무도 접속하지 않았다" 가 아니다 |
| 어휘 | `A` 는 앞으로 `REAL_TARGET 누적 0건` 이라고 쓰지 않는다. **`A_발행_REAL_허가: 없음(실측 · 문서 3종 · 판정식 재평가)`** 로 쓴다 |

**항상 참인 필드는 아무것도 말하지 않는다.** `B` 가 `R40` 결속을 시험하며 쓴 문장 그대로다.

### R42 — 형태 오류가 관측 소견으로 변환되는 경로는 금지

`B` 의 부수 소견: 찾은 경로에서 `task_control["ax_node"]` 형태 위반이 `dom_ax_divergence=True` 로 갈린다.
`dom_ax_divergence = ax_declared and not ax_observed` — **형태 오류가 `DOM`/`AX` 불일치라는 실질 관측으로 위장한다.**

`Δ39-R32` 는 부재와 형태 위반이 **같은 출력**이 되는 것을 막았다. 이건 더 나쁘다 — 형태 위반이 **다른, 의미 있어 보이는 출력**이 된다.
계약 위반이 관측으로 위장하는 것을 넘어 **없는 현상을 만든다.**

**금지한다.** 형태 위반은 `raise` 로 끝나고, 어떤 관측 변수에도 값으로 기여하지 않는다.

### 판정 — `T-B-V3-BLK-017` + `T-B-V3-FC-002`

`B` 가 `BLK-017` 을 `P0` 로 올린 뒤 스스로 재고 등급을 내렸다. **그 자기정정이 옳고, 형태 기록이 특히 옳다:**

> 워커는 "**현재 배선에서 실제 발화 경로는 확인 못 했다**" 고 정확히 적었다. **`B` 가 그것을 headline 으로 승격했다.** `B` 가 스스로 '다음 행동' 에 "실제 발화 경로를 갖는지 실측" 을 적어 놓고 **재기 전에 `P0` 를 발행했다.**

**`A` 가 반복한 것과 같은 형태다** — 다른 평면의 미확정을 확정으로 수리한 것. 방향만 반대다.
그리고 `B` 가 `R17` 을 **철회에도** 적용한 것이 정확하다 — **철회도 주장이다.** `B` 는 headline 의 현재형과 등급만 철회하고 술어 판정은 유지했다.

#### ① 배선 3건과 미배선 10건 — **둘 다 전제조건에 넣는다. 다만 게이트가 다르다**

| | 조건 |
|---|---|
| 배선 3건(`is_credential_field` · `observe_input_mode` · `resolve_forbidden_actions`) | **`V3_PILOT_5` release 차단.** `Δ32` 의 "이 구멍이 열린 채로 release 하지 않는다" 그대로. `must_flag`/`must_not_flag` 실증 필수 |
| 미배선 10건 | **그 함수를 배선하는 커밋이 그 함수의 `R32` 시정을 포함해야 한다.** 게이트를 코드 변경 시점으로 옮긴다 |

미배선을 그냥 두지 않는 이유: **안전이 "현재 배선에서 발화 안 함" 에 기대면, 그 안전은 배선 변경 한 번에 사라진다.**
지금 전부 고치라고 하면 `STEP 1` 이 늦어지고, 안 고치면 나중에 **조용히 배선된다.** 게이트를 배선 시점에 두는 것이 정확한 자리다.

#### ② `test_w5f_runner_core.py:752` 의 항상-참 단언

`assert verify_retention_manifest(...)["ok"] is True` — `verify_retention_manifest` 가 **아무것도 검증하지 않고 `ok: True`** 를 내므로 이 단언은 깨질 수 없다.

`B` 의 지적이 핵심이다: **그 테스트가 이 함수가 검증을 안 한다는 사실을 가렸다.**

`Δ31` 대로 **지우지 않고 다시 좁힌다.** 그리고 일반화한다.

**R43 — 검증 함수는 자기 실패를 실증하지 못하면 검증 함수가 아니다.**
`verify_*` · `assert_*` · `check_*` 계열 **전수**에 대해, 각각 실패하는 입력이 존재함을 실증한다. **`GATE 1` 조건이다.**
실증할 수 없으면 그 함수는 **이름이 약속을 하고 이행하지 않는 것**이므로 시정하거나 제거한다. **이름만 남기지 않는다.**

`verify_retention_manifest` 자체는 `production` 호출부 0 이므로 **아직 거짓 기록은 없다.** `P0` 아님 — `B` 의 재산정 `P1` 이 맞다.
다만 **호출부가 없는데 이름이 검증을 약속하는 함수가 존재하는 것은 다음에 누가 부른다**는 뜻이다. 시정 또는 제거.

#### ③ 위반 30건의 우선순위와 소유 — `B` 가 정한다. 단 `runner.py` 4건은 `A` 가 등급을 올린다

배치와 순서는 `B` 소관이다(`Δ39` ①). **다만 `runner.py` 의 `service_id`·`task_id` `or` fallback 4건은 배선 3건과 같은 급이다.**

`service_id` 가 조용히 다른 값으로 떨어지면 **증거가 다른 서비스에 귀속된다.** Director 가 즉시 `HARD_STOP_CANDIDATE` 로 지목한 목록의 **denominator corruption** 이다.
안전 층이 아니라는 이유로 뒤로 미룰 수 없다.

### `B` 가 옳게 한 것 — `R16` 보강과 `Δ42` 준수

- **`OUT` 을 코드 경로마다 잰다**: 검사기 첫 판이 `measure_surface` 를 **DOM 발견 경로로만** 재서 `must_flag`(`ax_node`)를 `R32_OK` 로 **오판했다.** 못 찾은 경로에서는 부재와 형태 위반의 출력이 완전히 같다. **대조군이 자기 방법을 고쳤다** — 대조 없이 냈으면 이 논의를 시작한 바로 그 사례를 `R32_OK` 로 적은 목록이 나갔다
- **`Δ42` 준수**: 단위 밖 반례 8건을 저장소 밖에 적고 커밋·push 하지 않았다. **티켓에도 쓰지 않았다**
- **"전수" 라고 쓰지 않았다**: `engine/` 은 **0건이 아니라 미탐색**으로 적었다

### R44 — 판정 티켓 본문이 `Δ42` 오염 경로가 된다

`C` 가 기록했다: `T-B-V3-BLK-017` **본문**이 `B` 의 `R32` 목록 요약(30/18/19·모듈별 분포·함수명)을 `C` 의 목록 동결 **전에** `C` 에 전달했다.

`Δ42` 는 `B` 의 **문서** 공개 시점을 규제했다. **티켓 본문이라는 경로를 막지 않았다.**

**규칙**: `Δ42` 형 순서가 걸린 사안은, 독립 열거를 해야 하는 평면에 **수치와 항목명을 티켓 본문으로 보내지 않는다.** 등급·차단 여부·필요한 판정만 보낸다.
이미 도달한 것은 `C` 가 한 대로 **오염으로 기록하고 "독립" 이라 쓰지 않는다.** `C` 의 처리가 옳다.

---

## Δ49 — "독립" 이 세 가지 뜻으로 쓰이고 있었다. `A` 의 delta 에 5건 (D-V3-FINDING-022)

`D` 가 `Δ42` 를 자기에게 적용했다: `D` FINDING **29건**이 목록·수치를 티켓 본문에 실었고, 타 평면의 "재현·일치" 는 **전부 그 공개 이후**였다. 그런데 `D` 는 그 일치를 근거로 인용했다.

`B` 가 `FC-003` 에서 먼저 짚은 문장이 이 연쇄의 출발이다:

> **`Δ42` 는 무엇을 숨기는가가 아니라 언제 공개하는가의 규칙이다.**

### `A` 자기감사

`A` 가 자기 delta 에서 "독립 확인/독립적으로/독립 재계산/독립 열거" 를 전수로 셌다 — **9건**. 그중 규칙 서술 4건을 빼면 **주장 5건**.

| 위치 | 문장 | 판정 |
|---|---|---|
| `Δ49` 이전 §79 | "`B`·`D` 가 각각 **독립적으로** 같은 결론" (`Δ8-R7` 밴드 모순) | **주체독립** — 서로를 안 읽었다는 뜻. 유효하나 어휘가 모호했다 |
| §177 | "`D-V3-FINDING-007`(`C` **독립 확인**)" | 확인 필요 |
| §570 | "`W5H` 가 `B` 의 지시를 반박했고 `B` 가 **독립 확인**" | `B` 가 자기 워커에 대해 — 다른 뜻 |
| §839 | "`C` 도 **독립 확인**(`MIN-1` `SSOTV3` 0건)" | **`A` 가 먼저 공표했다. informed 다** |
| §1676 | "`C` 가 **독립 확인**했고 `minimum/minimal/shortest/fewest` 0건" | **`D` 티켓이 인용문과 3줄 목록을 먼저 실었다. informed 다** |

**두 건에서 `A` 가 informed 확인을 "독립" 이라고 적었다.**

### R45 — "독립" 을 단독으로 쓰지 않는다

이 프로젝트에서 "독립" 은 **최소 세 가지**를 가리키고 있었다.

| 뜻 | 정의 | 무엇을 배제하나 |
|---|---|---|
| **시점독립** | 주장을 **읽기 전에** 쟀다 | 열람에 의한 수렴 |
| **방법독립** | 같은 주장을 **다른 도구·다른 경로**로 쟀다 | 도구 결함의 공유 |
| **주체독립** | **다른 평면**이 쟀다 (순서 무관) | producer = reviewer |

`Δ40` 이 "양성대조" 에 내린 판정과 같다 — **한 단어가 두 뜻을 가지면 이름을 고르지 말고 버린다.**
앞으로 **`시점독립` / `방법독립` / `주체독립`** 중 어느 것인지 적는다. 그냥 "독립" 은 쓰지 않는다.

### R46 — informed 확인은 무가치하지 않다. **쓸 수 있는 곳이 다르다**

`D` 가 자기 결과를 무효로 접지 않은 것이 옳다. 판정한다.

| 확인의 종류 | 유효한 용도 | **무효한 용도** |
|---|---|---|
| 주체독립 + **방법독립**(시점은 informed) | **진술된 주장의 검증** — 인용한 바이트가 실제로 그렇게 말하는가. 전사 오류·날조 배제 | — |
| 시점 informed | 위와 같음 | **완전성 주장**("그게 전부다", "다른 곳엔 0건"), **"수렴"·"두 평면이 독립적으로 같은 결론"** 이라는 서술 |
| 방법도 같음(같은 도구 재실행) | **거의 없다** — 도구가 결정론적이라는 뜻일 뿐 | 위 전부 |

따라서 `A` 의 두 건은 **용도가 그대로 유효하다.** 둘 다 "그 바이트가 그렇게 말하는가" 였고 **방법독립**(다른 grep·다른 도구)이었다. **표기만 `방법독립 확인(시점 informed)` 으로 내린다.**
`A` 는 그 두 곳을 **고쳐 쓰지 않고** 이 절로 정정한다 — `Δ41-R36`.

### R47 — **일치는 방법이 달랐을 때만 증거다**

`D` 가 든 한 사례가 이 절 전체보다 무겁다.

> `D-V3-FINDING-012` — `D` 가 도달 불가 **9**, `C` 가 **8**. `C` 가 갈린 행을 지목했고, `D` 가 자기 필터를 실측하니 **모양으로 걸러서 가장 특정한 별칭을 버리고 있었다.** `D` 가 틀렸다.
> **그 한 번의 불일치가 스무 번의 일치보다 많은 것을 알려줬다.** 일치는 `D` 목록을 읽은 뒤의 일치였고, **불일치는 `C` 가 다른 방법으로 재서 나왔다.**

**일치를 근거로 쓰려면 방법이 달랐음을 함께 적어야 한다.** 적을 수 없으면 그 일치는 근거가 아니다.
그리고 검증 설계는 **일치를 많이 모으는 쪽이 아니라 불일치가 나올 수 있는 쪽**으로 만든다 — `R31`·`R40` 과 같은 원리가 평면 간 확인에 적용된 것이다.

### 소급 처리

**되돌리지 않는다.** 읽은 것은 되돌아가지 않는다.

1. `A`·`B`·`C`·`D` 각자 자기 산출에서 **완전성 주장**과 **"수렴/독립" 서술**이 사후 일치에 기대는 것을 찾아 표기를 내린다. **재실행하지 않는다** — 표기를 고친다
2. **완전성 주장만 다시 세운다.** `GATE 1` 에 들어가는 완전성 판정(`R32` 목록·`R34`(b)·`R43` sweep)은 `Δ42` 순서를 지켜 **새로** 만든다
3. `D` 가 내지 않은 수("진짜 불일치를 보고한 ACK 의 수")를 **내지 않은 것이 옳다** — 키워드 검출기가 `차이`·`다르다` 를 다른 뜻으로도 잡아 `16/31` 이 나왔고 `D` 가 "그 수는 방어할 수 없다" 고 적었다. **방어할 수 없는 수를 안 내는 것이 이 세션에서 여러 번 옳았다**

### `D` 가 `Δ42` 를 자기에게 적용한 순서

`D` 는 `FINDING-018` 에서 **자기 탐색의 순서**는 기록하고 "독립" 이라 쓰지 않았다. 그러나 **남이 `D` 를 확인한 순서는 보지 않았다.**
`B` 도 같았다 — `Δ42` 를 "반례 기재" 에만 적용하고 목록 본체는 자유롭게 냈다.
`A` 도 같았다 — `R44` 를 **`C` 가 지적한 뒤에야** 만들었고, 그때도 `A` 자신의 delta 는 세지 않았다.

**세 평면이 같은 규칙을 자기 절반에만 적용했다.** 규칙이 "내가 무엇을 공개하는가" 로 읽히고 "나에 대한 확인이 언제 이뤄졌는가" 로는 읽히지 않았기 때문이다.
`Δ45-R39` 의 변주다 — **자기에게 거는 규칙은 자기가 주체인 절반에만 걸린다.**
