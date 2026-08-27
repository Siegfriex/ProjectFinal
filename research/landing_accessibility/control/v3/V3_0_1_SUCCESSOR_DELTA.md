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

**hard stop 어휘**: runbook 과 `T-A-V3-P0-001` 의 어휘가 다르나 일대일 대응한다(scope leak↔wrong scope · task contract drift↔task/outcome leakage · evidence mutation↔evidence overwrite). **정본은 `T-A-V3-P0-001` 의 6종**이다. B·C 가 이미 같은 판단을 했다.

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
