# P-A A5 Pilot Mapping — SHADOW 실행 보고

| 항목 | 값 |
|---|---|
| 상태 | **`SHADOW_PREPARATORY`** · lane `LANE_A` · base `d5f1da5` (`PHASE_GATES` §4.3) |
| 목적 | 매핑 **결과**가 아니라 cascade **구조가 실제로 작동하는가**의 실증 |
| 스크립트 | `analysis/pilot/pilot_mapping.py` |
| 산출 | `analysis/out/pilot/pilot_mapping.jsonl` · `mapping_run_manifest.json` |
| 입력 tier | **T1 (source context) 전용** — codebook `mapping_rules.input_allowlist` |
| Gate | `ANALYSIS_AND_TASK_CODEBOOK_FROZEN` **닫지 않았다.** 전 행이 `CANDIDATE` 또는 `AMBIGUOUS_UNRESOLVED` (CR-002 시정 반영, `DRAFT` 최종값 없음) |

---

## 1. 결과 한 줄

**표본 15건 · 해소 9건(전부 stage 1) · abstain 6건 · FROZEN 0건 · 오염 검사 CLEAN.**

| 지표 | 값 |
|---|---|
| 표본 | 15 (`SERVICE_BRAND` 71 중) |
| stage 1(deterministic rule)에서 해소 | **9** |
| stage 2(source context)에서 해소 | **0** |
| stage 3(embedding)에서 해소 | **0** — 구조상 확정하지 않는다 |
| stage 4(AI reviewer)에서 해소 | **0** — 실행 불가 |
| `AMBIGUOUS_UNRESOLVED` (abstain) | **6** |
| `FROZEN` | **0** |

domain 분포 `SHOPPING_COMMERCE` 4 / `FINANCE_PAYMENT` 2 / `UTILITY_OTHER` 2 / `PORTAL_SEARCH` 1.
archetype 분포 `ITEM_DETAIL` 4 / `FINANCIAL_ACTION_ENTRY` 2 / `UTILITY_ENTRY` 2 / `QUERY` 1.

**이 수치는 매핑의 품질 지표가 아니다.** 표본이 15건이고 stage 3·4가 구조적으로 막혀 있으므로
해소율 9/15는 "규칙 사전이 표본의 절반을 덮었다" 이상을 뜻하지 않는다.

---

## 2. 표본 선정 — outcome-blind

`axis_type = SERVICE_BRAND`(71건, EDA-00 F-10) 중 `canonical_service_key` 정렬 후
domain 층별 균등 stride로 15건. **정렬 키·층·표본 크기 어느 것도 접근성·인증 결과를 쓰지 않는다.**
선정이 결정적이므로 재실행하면 같은 15건이 나온다.

---

## 3. 무엇을 가렸는가 — 절차로 기록한 차단

`PHASE_GATES` §4.6과 codebook 규칙 IN-2를 **선언이 아니라 강제수단**으로 구현했다.

### 3.1 파일 차단

`builtins.open`을 감싸 이 프로세스가 여는 **모든 경로를 기록**하고, denylist 조각
(`certification` · `인증` · `criterion_result` · `landing_observation` · `interrupt_element` ·
`task_entry` · `task_step` · `ai_adjudication` · `mart_` · `evidence/` · `kwcag`)에 걸리면
`InputAllowlistViolation`으로 **끊는다.** `pandas.read_parquet`도 이 `open`을 거친다.

### 3.2 컬럼 차단

T1은 `service_master`의 **네 컬럼**만 허용한다. 로드 직후 그 컬럼(+조인 키 `service_id`)만
남기고 나머지를 버린다 — `web_eligibility_status` · `web_target_group_id` · `review_*` ·
`decision_*`은 이 run의 메모리에 **존재하지 않는다.**

`state/web_target_group.parquet`은 T2(target identity)라 **allowlist에 넣지 않았다.**

### 3.3 차단이 살아 있는지의 자체 시험

선언만 남기고 넘어가면 `V2-C001` 감사가 지적한 `선언과 강제수단의 간극`과 같은 결함이 된다.
그래서 run 시작 시 **실재하는 denylist 경로**(`sources/certification/certification_registry.parquet`)를
일부러 열어 본다.

| 항목 | 결과 |
|---|---|
| probe 경로 존재 | `true` (없는 경로로 시험하면 시험이 무의미하다) |
| 차단 발화 | **`true`** |
| 판정 | **`GUARD_WORKS`** |

시도는 `refused_open_attempts`에 남고 `research_root_paths_opened`에는 **들어가지 않는다** —
열리지 않았으므로 읽힌 바이트가 0이기 때문이다.

### 3.4 실제로 열린 경로 (전부)

`state/` 아래 5개 parquet(`panel_registry` · `source_ranking_rows` · `source_membership` ·
`service_master` · `entity_alias_map`)과 `analysis/codebook/codebook.json` 뿐이다.
`outside_allowlist = []`, `denylist_paths_touched = []`, **verdict `CLEAN`**.

각 허용 입력의 sha256은 `mapping_run_manifest.json`(codebook `freeze_protocol` F0)에 기록했다.

---

## 4. cascade 단계별로 무엇이 일어났는가

### stage 1 — deterministic rule (해소 9)

사전은 **브랜드명이 아니라 기능어**로만 짰다. 브랜드를 열거하면 그것은 규칙이 아니라 손라벨이고,
미등재 브랜드에서 조용히 무너진다. domain·archetype은 **독립 사전**으로 판정한다(규칙 MAP-7).
다중 매칭은 확정으로 치지 않는다 — 임의로 하나를 고르면 강제분류다(규칙 AB-2).

해소: `emart` · `lotte_himart` · `gs_homeshopping_gsshop` · `hyundai_homeshopping_hmall`(→ `ITEM_DETAIL`),
`hana_bank` · `nh_cok_bank`(→ `FINANCIAL_ACTION_ENTRY`), `device_care` · `my_files`(→ `UTILITY_ENTRY`),
`samsung_internet_browser`(→ `QUERY`).

**사전을 두 번 고쳤고, 둘 다 source context만 보고 고쳤다.**

| 수정 | 이유 |
|---|---|
| `뱅크` 추가 | `NH콕뱅크`가 `은행|뱅킹|bank`에 걸리지 않아 abstain으로 갔다. 한국어 표기 변이이며 결과를 본 뒤의 수정이 아니다 |
| `전화` 제거 (`MAP_MOBILITY`) | codebook `MAP_MOBILITY.inclusion`(지도·내비·대중교통·택시·대여)에 전화가 없다. 근거 없는 규칙이었다 |

### stage 2 — source context (해소 0)

패널 문맥(`source_section_title` · `table_title` · `panel_label` · `universe_definition`)이
`주요 금융 앱` · `주요 쇼핑 앱` · `홈쇼핑 리테일 브랜드` 같은 **domain 힌트**를 준다.
`11st`에서 실제로 `SHOPPING_COMMERCE` 후보가 잡혔다.

**그럼에도 이 단계 단독 해소는 구조적으로 0이다.** codebook이 이미
"패널 카테고리는 사업분류라 archetype(행위 구조)을 직접 답하지 못한다"고 적었고,
규칙 MAP-7이 domain·archetype 둘 다 없으면 확정을 막는다. 설계대로 작동했다.

### stage 3 — embedding (해소 0, **대체구현**)

정본 입력은 `02 §6` 후보 control의 accessible name·visible text다. 그것은 **real-target DOM/AX**이며
P0 종료 전 수집이 금지다(`PHASE_GATES` §4.1 2항). 그래서 입력을 source context 텍스트로 대체하고
유사도도 네트워크 없는 결정적 char 2-gram TF-IDF cosine으로 뒀다 (`fidelity = SOURCE_TEXT_SUBSTITUTE`).

**대체구현은 쓸 만한 신호를 내지 못했다.** 이것이 이 단계의 실질적 결과다:

| entity | top1 | score | top2 | score |
|---|---|---|---|---|
| `baemin`(배달의민족) | `FINANCIAL_ACTION_ENTRY` | 0.0204 | `CONTENT_OPEN` | 0.0089 |
| `mega_coffee`(메가커피) | `FINANCIAL_ACTION_ENTRY` | 0.0204 | `CONTENT_OPEN` | 0.0088 |
| `kakaotalk` | `CONTENT_OPEN` | 0.0050 | `FINANCIAL_ACTION_ENTRY` | 0.0038 |
| `chrome` | `QUERY` | 0.0110 | `FINANCIAL_ACTION_ENTRY` | 0.0057 |

점수가 0.02 이하이고 순위가 의미를 이루지 않는다(배달앱 1위가 금융). 이는 실패가 아니라
**codebook이 stage 3의 입력을 `02 §6` 후보 control로 규정한 이유의 실증**이다.
서비스명과 패널 제목만으로는 **행위 구조**를 알 수 없다. 대체구현으로 확정했다면
그것이야말로 억지 분류였다.

### stage 4 — AI reviewer (실행 불가)

`02 §10` evidence package(screenshot crop · DOM/AX fact · bbox)는 real-target 수집 산물이라
P0 종료 전 금지다. 이 단계는 `UNAVAILABLE_PRE_P0`를 반환한다.
**근거 없이 라벨을 생성하지 않는 것이 이 단계의 올바른 동작이다.**

---

## 5. abstain 6건 — 왜 강제 분류하지 않았는가

| entity | stage 1 | stage 2 | 처리 |
|---|---|---|---|
| `11st`(11번가) | `NO_RULE_MATCH` | domain 후보 `SHOPPING_COMMERCE` | archetype 미확정 → MAP-7 |
| `baemin`(배달의민족) | `PARTIAL` — domain만 (`배달`) | 신호 없음 | archetype 미확정 → MAP-7 |
| `coupang_eats`(쿠팡이츠) | `PARTIAL` — domain만 (`이츠`) | 신호 없음 | archetype 미확정 → MAP-7 |
| `chrome`(Chrome) | `NO_RULE_MATCH` | 신호 없음 | 브랜드명만으로는 규칙이 없다 |
| `kakaotalk`(카카오톡) | `NO_RULE_MATCH` | 신호 없음 | 동상 |
| `mega_coffee`(메가커피) | `NO_RULE_MATCH` | 신호 없음 | 동상 |

**`UTILITY_OTHER`/`UTILITY_ENTRY`로 밀지 않았다** (규칙 AB-2 — 잔여값은 근거가 없을 때 쓰는 값이지
판단이 안 될 때 쓰는 값이 아니다). 6건 모두 `mapping_status = AMBIGUOUS_UNRESOLVED` +
`mapping_ai_review_status = ABSTAINED` + `abstain_reason = AI_REVIEW_UNAVAILABLE_PRE_P0`이며
`counts_toward_archetype_denominator = false`다 (규칙 AB-3).

**`PHASE_GATES` P-A가 요구한 "abstain 가능함의 실증"(규칙 AB-4)은 주입 시험 없이 충족됐다** —
실제 표본에서 6건이 그 경로로 나갔다.

주의: 이 6건의 abstain 사유는 **서비스가 모호해서가 아니라 stage 4가 P0 전이라 막혀서**다.
P0 종료 후 evidence package가 생기면 상당수가 해소될 가능성이 높다.
이 abstain 비율을 그대로 P-B 예측치로 쓰면 안 된다.

---

## 6. 이 실행이 하지 **않은** 것

- `mapping_status`를 `FROZEN`으로 올리지 않았다. `ANALYSIS_AND_TASK_CODEBOOK_FROZEN`은 P0 종료 전이라 닫을 수 없다.
- `UTILITY_ENTRY` 2건은 `region_signal_type = CODEBOOK_PENDING`이라 규칙 FRZ-4로 **동결 자체가 불가**다 (미결 Q-2).
- 전수 71건 매핑을 하지 않았다 — P-B 소관이다.
- `web_target_group`을 열지 않았다 — T2다.
- 실제 서비스에 **한 번도 연결하지 않았다.**

## 7. 이 실행이 만든 발견

| id | 심각도 | 내용 |
|---|---|---|
| `PILOT-CASCADE-STAGE3-NO-SIGNAL` | P2 | source-context 텍스트만으로 하는 archetype 유사도는 신호를 내지 못한다. stage 3은 `02 §6` 후보 control 없이는 **동작 불가**이며, P-C 엔진 준비 전에는 cascade가 실질 2단계다 |
| `PILOT-CAS2-VS-STAGE3-THRESHOLD` | P2 | codebook 규칙 CAS-2는 "1·2위가 근접하면 4단계로 올린다"(= 근접하지 않으면 확정 가능)인데 stage 3의 `cannot_see_or_do`는 "임계값 자동 확정 금지"다. 두 문장이 한 단계에서 양립하지 않는다. 이 run은 보수적으로 **stage 3 확정 없음**을 택했고 그 선택을 기록한다 |
| `PILOT-ABSTAIN-CAUSE-IS-GATE-NOT-AMBIGUITY` | P2 | abstain 6건의 사유가 대상의 모호성이 아니라 **P0 차단**이다. 이 수치를 P-B 예측이나 품질지표(`A2` §4.5 abstention rate)로 전용하면 안 된다 |
| `PILOT-Q8-MANIFEST-SLOT-UNRESOLVED` | P2 | `mapping_run_manifest`의 물리 저장 슬롯이 미결(Q-8)이라 임시로 `analysis/out/pilot/`에 뒀다. 확정 시 이동 필요 |
