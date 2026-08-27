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
