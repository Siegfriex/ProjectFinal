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
