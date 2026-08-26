# 05 — 오케스트레이션 실행 로그 (Phase 1)

**하네스** orchestrator-constitution-v3 + hardening-directive-v3.1 · **Phase** P1_ISOLATION_AND_SOURCE_REFREEZE
**정지 목표** `READY_FOR_E001` — E001 본수집은 Research Director GO 없이 실행하지 않는다.

## 0. 역할 격리 구조

```
research/refcohort-r1            Pilot        READ_ONLY  (32460b87 고정)
control/landing-orchestrator     지시·재결    orchestrator 전용 쓰기
agent/landing-exec               구현         executor 전용 쓰기
audit/landing-adversarial        적대적 감사   auditor 전용 쓰기
audit/landing-ssot               준수 감사     auditor 전용 쓰기
research/landing-accessibility-main  승격 대상 orchestrator 만 promotion
```

워크트리 4개를 `.agent_worktrees/` 아래 물리 분리했다.
**실행자는 감사 브랜치에 쓰지 못하고, 감사자는 구현 브랜치에 쓰지 못하며, main 승격은 오케스트레이터만 한다.**

## 1. 트리거 루프 (실측 작동 확인)

```
orchestrator commit ─┐
                     ├─→ Monitor(60s poll) ─→ DIRECTIVE_UPDATED  (executor 트리거만)
executor commit ─────┴─→ Monitor          ─→ AUDIT_REQUIRED     (auditor 2종 병렬)
Pilot 브랜치 이동/워크트리 오염 ───────────→ P0_VIOLATION       (즉시)
```

감사 커밋은 오케스트레이터만 트리거한다 — 감사가 감사를 부르는 무한 루프를 차단한다.
Monitor는 세션 시작부터 persistent로 가동 중이며 `DIRECTIVE_UPDATED` · `AUDIT_REQUIRED` 발행을 실측 확인했다.

## 2. 사이클 기록

| Cycle | 주체 | 산출 | 결과 |
|---|---|---|---|
| C001 | orchestrator | state.json 초기화, Wiseapp 933 을 A1 모집단 권위로 선언 | `97968c9` |
| C001 | executor | Wiseapp 933 원문 2경로 취득 + A1 권위 매니페스트 | `fa7a976` |
| C001 | ssot audit | PASS / P0 0 / P1 7 | `6c22f31` |
| C001 | adversarial audit | **REWORK** / P0 1 / P1 2 / P2 3 | `f98f222` |
| C002 | executor | figure 11종 → panel_registry 17 · source_ranking_rows 261 | `1a7cd64` |
| C003 | executor | canonical entity 80 · alias 81 · membership 142 | `933096a` |
| C002-3 | ssot audit | PASS / P0 0 / P1 2 | `68404d9` |
| C002-3 | adversarial audit | PASS / P0 0 / P1 1 / P2 5 | `e302d31` |
| C006 | executor | A2 인증 레지스트리 자체 스냅샷 `KWACC_WA_20260826` | `bf5d16e` |
| C009 | executor | 감사 수용 12건 시정 · 2층 분리 · 축 컬럼 분리 | `fe86e19` |
| C009 | ssot audit | PASS / P0 0 / P1 2 | `7c928f5` |
| C009 | adversarial audit | PASS / P0 0 / P1 2 / P2 5 | `fd9773a` |
| C009 | **orchestrator 재결** | accepted 8 / rejected 0 / deferred 0 · promotion BLOCKED | `bc248ff` |
| C011 | executor | P1 3건 + P2 5건 시정 | 진행 중 |

오케스트레이터 재결·문서 커밋:
`441a31b` `1b3ec23` `74a5db3` `30c664f` `1c45d29` `973bce9` `2961713` `ff16bdb` `44ee6c6`
`7b6b3c2` `1d46c8b` `16cef85` `188e2e3` `3ada6be` `bc76afb` `bc248ff` `9220b83`

오케스트레이터 재결·문서 커밋:
`441a31b` `1b3ec23` `74a5db3` `30c664f` `1c45d29` `973bce9` `2961713` `ff16bdb` `44ee6c6` `7b6b3c2` `1d46c8b` `16cef85` `188e2e3`

오케스트레이터 재결 커밋: `441a31b` `1b3ec23` `74a5db3` `30c664f` `1c45d29`

## 3. 재결에서 실제로 뒤집힌 판단

이 하네스의 존재 이유는 **누구도 혼자 정답을 결정하지 못하게 하는 것**이다. 실제로 세 방향 모두에서 정정이 일어났다.

### 3-1. executor 주장이 감사로 뒤집힌 것 (P0)

executor는 기존 xlsx 와 원문의 차이를 "카카오톡 1,377만 vs 1379만 — 값 불일치 2만 명"으로 기록했다.
적대적 감사가 항목별로 대조해 **두 자료가 애초에 다른 패널 집합**임을 증명했다.

- 원문 rank3 = Google 1,278만 — xlsx 에 부재. xlsx rank3 = 네이버 1224만
- 드리프트 비일관: 카카오톡 −0.15% / 유튜브 −1.8% / 네이버 −2.5%
- 점유율 미중첩: 원문 다음 54.1%(1위) vs xlsx 다음 38.7%(5위)
- 리테일 서수 역전: 원문 농협하나로마트#3·이마트#4 vs xlsx 이마트#3·농협하나로마트#6
- 깊이 불일치 양방향: 원문 Ch1(1) TOP15 vs xlsx Top10, 원문 Ch3(1) TOP15 vs xlsx Top20
- provenance 전무: `creator=openpyxl`, 문서속성 전부 None, `insight/detail/<id>` 참조 0건

→ A7 을 `UNSOURCED_INCOMPATIBLE_PANEL_SET` 으로 재정의. **셀 패치(1379→1377)에 의한 패널 융합을 금지**한다.
그대로 뒀다면 두 비호환 패널이 하나의 권위 레코드로 융합됐을 것이다.

### 3-2. 오케스트레이터 진단이 executor 에게 뒤집힌 것

오케스트레이터가 `현대홈쇼핑/현대Hmallord` 를 "판독 오염"으로 지목했다.
executor 가 `fig10.png` 를 4배 확대 판독해 **발행물 원문 자체의 오타**임을 확인했고,
원자료를 수정하지 않은 채 canonical 레이어에서만 흡수했다 (`needs_human_review=True`).
적대적 감사가 독립적으로 재확인했다 (`grep -o '현대Hmall[a-z]*'` → raw/manifest 12건 전부 `현대Hmall`, `Hmallord` 0건).

→ **오케스트레이터의 진단도 증거 대조 전에는 지시가 될 수 없다.** 원자료 값 시정 0건이 옳은 처리였다.

### 3-3. 감사 주장이 오케스트레이터에게 기각된 것

ssot 감사가 C002 산출물을 "panel_registry 15 panel / source_ranking_rows 262행"으로 스팟체크했다.
오케스트레이터가 `git archive 1a7cd649` 고정 트리에서 직접 재계산 → **17 panel / 261행**.
`sum(n_metrics × rows_extracted) = 261` 로 패널 정의와 행 테이블이 완전 정합함을 확인하고 기각했다.

→ 헌장 CASE 5. 어느 에이전트의 주장도 자동 우선하지 않는다.

### 3-4. 두 감사가 독립적으로 같은 결함을 반대편에서 도출

| 감사 | finding | 각도 |
|---|---|---|
| ssot | `coupang-cross-domain-merge-rule-inconsistent` | 쿠팡을 `BOTH` 로 **합친 것**의 부정합 |
| adversarial | `duplicate-web-collection-targets-naver-gmarket` | 네이버·G마켓을 **분리한 것**이 수집단위까지 전파 |

실제 분기 기준이 '측정 대상 동일성'이 아니라 '원문 문자열 우연 일치'였다는 동일 결함의 양면이다.

→ 오케스트레이터 결정: **measurement_entity / web_target 2층 분리**
- `measurement_entity` — 원문 패널의 측정 대상. APP 지표(사용자·사용시간)와 RETAIL 지표(카드 결제추정금액)는
  다른 것을 재므로 같은 브랜드라도 별개다. 쿠팡도 예외가 아니다.
- `web_target` — 실제 방문할 랜딩 URL. 여러 entity 가 같은 target 을 가리키면 관측은 정확히 1회.
- 금지 — entity 축에서 APP/RETAIL 지표를 합산·평균하지 않는다.

헌장 §24 "서로 독립된 증거가 일치할 때만 승격" 조건을 충족한 결정이다.

### 3-5. 하네스가 오케스트레이터 자신의 위반을 잡은 것 (P0)

오케스트레이터가 문서를 생성할 때 Bash cwd 가 메인 워크트리에 있었고, 이어지는
`cd .agent_worktrees/landing_orchestrator` 가 체인에서 기대대로 적용되지 않아
`git add/commit` 이 **Pilot 브랜치(`research/refcohort-r1`)에서 실행됐다.**

Monitor 가 즉시 발행했다.

```
P0_VIOLATION pilot branch moved 32460b87 -> f26ca974 — Pilot is READ_ONLY
```

원격은 오염되지 않았고(push 대상이 `control/landing-orchestrator` 라 no-op),
Pilot 추적 파일의 내용 변경은 0이었다(신규 파일 1개 추가 커밋).

시정: `git reset --mixed 32460b8`. `--hard` 를 쓰지 않은 이유는 `CLAUDE.md` · `tsconfig.json` 의
기존 미커밋 수정을 보존하기 위해서다. Monitor 가 원복도 감지했다(`f26ca974 -> 32460b87`).

예방: **오케스트레이터 파일 조작은 절대경로만 사용한다. cd 의존 금지.**

→ 이 사건의 의미는 하네스가 관리자 자신에게도 작동한다는 것이다.
`harness_incidents` 에 P0 로 기록했다.

### 3-6. executor 가 지시 범위 밖에서 오류를 찾은 것

C009 에서 `imgInfoList` 13 vs 11 을 문서화하라는 지시를 수행하다가,
제외 대상 `4796` 의 후속본 `f43af706` 이 fig08 이 아니라 **fig07** 임을 발견했다.
evidence manifest sha256 대조로 확인했고 403/200 도 직접 확인했다(제외 2건 403, 채택본 200).

같은 사이클에서 **업종 축 10건이 RETAIL 도메인 "안에" 있다**는 구조적 사실도 드러냈다.
`domain == 'RETAIL'` 필터만으로는 업종 카테고리가 걸러지지 않으므로
리테일 브랜드 집계에는 `axis_type == 'SERVICE_BRAND'` 를 함께 걸어야 한다. 테스트로 고정했다.


### 3-7. 감사가 오케스트레이터가 제공한 근거의 오류를 잡은 것

C004 에서 오케스트레이터가 xlsx 재정의 근거를 executor 에게 넘겼다.
C009 적대적 감사가 그 근거 두 개를 반증했다.

| 오케스트레이터 주장 | 실제 |
|---|---|
| 드리프트 = 카카오톡 −0.15% / 유튜브 −1.8% / 네이버 −2.5% (전부 음수) | **카카오톡만 부호가 반대다.** 원문 1,377만 < xlsx 1379만 이므로 `(xlsx−원문)/원문 = +0.15%` |
| xlsx 문서 속성이 **전부** None | `created` / `modified` 는 채워져 있다 (2026-08-25 15:54:10). 실재하는 provenance 단서를 없다고 적었다 |

두 오류 모두 판정 자체(`UNSOURCED_INCOMPATIBLE_PANEL_SET`)를 뒤집지 않는다 — EV-1/3/4/5 로 독립 성립한다.
그러나 **부호가 갈린다는 사실은 오히려 "비일관 드리프트" 논거의 최강 형태**이고,
타임스탬프는 판정을 강화하는 단서다. 부정확한 근거가 더 약한 주장을 만들고 있었다.

→ **오케스트레이터가 감사에 제공한 근거도 감사 대상이다.**

### 3-8. 테스트가 통과를 위장하고 있던 것

C009 재현 스크립트의 `matches_existing_c002_output` 이 실제 비교가 아니라 `existing.exists()` 였다.
파일이 존재하기만 하면 통과한다. 적대적 감사가 diff 를 정독해 잡았다.

같은 감사에서 저널 스크립트를 단독 실행하면 `panel_registry` 가 26→25 컬럼이 되어
(`panel_scope` 소실) 다른 테스트가 실제로 FAILED 하는 것도 실증했다.

→ **`pytest PASS` 는 연구무결성 PASS 가 아니다.** 테스트가 무엇을 검사하는지 읽어야 한다.


## 4. A1 권위자료 취득 기록

원문은 SPA 라 HTML 에 데이터가 없었다. 두 경로로 확보하고 상호 교차검증했다.

```
1) 내부 API   POST /insight/detail/getDetail.json  body {"insightNid":"933","preview":0}  → 154KB JSON
2) 렌더링     playwright chromium → HTML · 본문텍스트 · full-page 스크린샷 · CDN 이미지 11종
```

`InsightAjax.js` → `InsightDetail.js` → `Common.requstPost` 순으로 읽어 엔드포인트와 파라미터 형태를 특정했다.
`preview` 는 `Number(0)` 이라 `false` 로 보내면 400 이 난다.

**본문 `<table>` 0개 / `<img>` 11개** — 모든 순위표가 이미지다. 텍스트 파싱 경로가 없어 figure 판독이 유일하다.

## 4-B. A2 인증 레지스트리 자체 스냅샷

Pilot 수집분은 A6 자산이라 A2 권위로 쓸 수 없어 Main Study 자체 스냅샷을 만들었다.

```
snapshot_id   KWACC_WA_20260826
pages         230 (카드 보유 229 + 빈 종료 페이지 1)
stop_reason   NO_CARDS_AT_DECLARED_END
status        COMPLETE
rows          2,283 (중복 0)  VALID 227 / EXPIRED 2,056 / UNKNOWN 0
valid_at_audit 226            target_url 보유 2,279
```

완결성 게이트를 코드로 강제했다 — `valid_at_audit_rows()` 가 INCOMPLETE 매니페스트에서
`IncompleteSnapshotError` 를 던져 **"목록에 없음 = 인증 0"** 을 차단한다.

### 독립성 주장의 범위

230페이지 sha256 이 Pilot 수집분과 전건 동일했다. executor 가 스스로 과잉 해석을 차단했다.

```
주장 가능   수집 절차의 독립성 — 자체 요청·자체 원문·자체 매니페스트, Pilot 산출물 미사용
주장 금지   내용의 독립 검증 — 같은 서버 응답을 두 번 받은 것이며,
                              서버가 틀리면 두 스냅샷이 같은 방식으로 틀린다
```

### 레지스트리 원문 자체의 결함

| 결함 | 건수 | 비고 |
|---|---:|---|
| **VALID 인데 감사일 기간 밖** | **1** | 2521 국립망향의동산, 인증기간 2026-08-27 시작 — **감사일 다음 날** |
| 대상 URL 링크 부재 | 4 | 전부 EXPIRED |
| 스킴 없는 href | 26 | `namdogallery.or.kr` 등 |
| URL 자리에 텍스트 | 3 | `보건복지부 홈페이지`(27) · `국립중앙도서관 홈페이지`(25) · `-`(1812) |
| 인증기간 공란 | 1 | 1812번, service_name 도 `-` |

**VALID 227 과 감사일 유효 226 의 차이가 정확히 국립망향의동산 1건이다.**
설계서가 경고한 "유효 표시인데 시작일이 미래" 사례가 실재함을 확인했다.
목록의 상태 플래그를 그대로 신뢰하면 안 된다는 실증이다.


## 5. figure 판독 워크플로

```
22 agent · error 0 · 875,963 tokens · 192s
pipeline: figure별 독립 판독(schema 강제) → figure별 적대적 재확인(즉시)
결과: 이의제기 0건, agrees=false 0건, row_count_ok=false 0건
```

행 수 보존이 17패널 전부에서 성립했다. 다만 적대적 감사가 지적했듯 **8개 패널은 TOP N 미표기라
이 불변식이 구성상 항상 참**이며, 해당 32행은 감사자가 육안 계수로 별도 확인했다(누락 0).
항상 참인 불변식을 통과로 계상하지 않도록 C008 에서 시정한다.

## 6. 원문에서만 얻은 조작적 정의

파생자료에 전혀 없던 것들이다. 모집단 정의를 방어하려면 반드시 필요하다.

| 항목 | 원문 문구 |
|---|---|
| 측정기간 | 25년 7월부터 12월까지 월간 평균 |
| APP 모집단 | 한국인 Android+iOS 스마트폰 사용자 추정 (본문 5회) |
| RETAIL 모집단 | **계좌이체, 현금거래, 상품권으로 결제한 금액은 포함되지 않음** (본문 6회) |
| 점유율 모수 | 월간 사용자 평균 200만 명 이상인 앱 |
| 성장률 모수 | 200만 명 이상 AND 시니어 비율 25% 이상 |
| 결제 성장률 모수 | 순 결제추정금액 5천억 원 이상 AND 비율 30% 이상 |
| fig07 기간 | 25년 12월 / 전년 **동월** 대비 — 나머지 반기 패널과 기간축이 다르다 |

**RETAIL 지표가 카드 결제 표본이라는 사실이 연구 한계의 핵심이다.**
현금·계좌이체 비중이 높은 고령 세그먼트가 구조적으로 과소집계된다 — 이 연구가 겨냥하는 바로 그 집단이다.
기사 인용 시 반드시 병기한다.

## 7. A1 동결 유효창

발행처가 **2026-08-25 09:00** 에 "모집단 변경 사전 안내"(nid=127, 종료일 없음)를 게시했다.
우리는 그 다음 날 원문을 취득했다.

→ 동결본을 **"2026-08-26 시점에 게시돼 있던 933 판본"** 으로 유효창을 한정한다.
발행처 모집단 변경 이후 수치와 혼용하지 않는다.

## 8. Pilot 실패의 재발 차단 확인

| Pilot CRITICAL | Main Study 상태 |
|---|---|
| 표시명 기반 파일키 → 증거 덮어쓰기 | `service_id = svc_ + sha256(로마자슬러그)[:16]`, 한글 0자, 충돌 0 (감사 실측) |
| 레코드↔증거 오대응 | figure 파일↔URL 바인딩을 IHDR 높이 대조로 검증, 11/11 일치 |
| append-only 미강제 | `engine_integrity` gate NOT_RUN — E001 전 필수 |
| UNDETERMINED → PASS 흡수 | `judgment_semantics` gate NOT_RUN — E001 전 필수 |

## 9. 현재 게이트 상태

```
pilot_archive              PASS_WITH_LOGICAL_BACKUP_ONLY   (물리 이중화 미완)
source_asset_discovery     PASS
population_source_freeze   PASS
source_row_reconciliation  PASS_FIGURE_LEVEL
canonical_entity           PASS_PENDING_AUDIT
membership_preservation    PASS_PENDING_AUDIT
ssot_audit                 PASS_C002_C003_P1_2
adversarial_audit          PASS_C002_C003_P1_1_P2_5
certification_join         NOT_RUN
web_eligibility            NOT_RUN
url_review                 NOT_RUN
feasibility                INVALIDATED_BY_SOURCE_MISMATCH
engine_integrity           NOT_RUN
evidence_identity          NOT_RUN
append_only                NOT_RUN
judgment_semantics         NOT_RUN
automation_split           NOT_RUN
criterion_probe_coverage   NOT_RUN
smoke_e000                 NOT_RUN

full_collection            PROHIBITED
e001_authorization         REQUIRES_RESEARCH_DIRECTOR_GO
promotion                  HOLD
```

## 10. 철회된 결론

| id | 상태 | 사유 |
|---|---|---|
| `RQ2_RQ3_RQ4_NO_GO` | `WITHDRAWN_PENDING_SOURCE_REFREEZE` | 이전 NO-GO 판정이 A7 파생 frame 위에서 산출됨 |
| `OLD_CATEGORY_FEASIBILITY` | `INVALIDATED_BY_SOURCE_MISMATCH` | 동일. 파일은 삭제하지 않고 보존 |

**철회는 "틀렸다"가 아니라 "권위 없는 입력으로 계산됐다"는 뜻이다.**
A1 기준으로 재산출하면 같은 결론이 다시 나올 수 있고, 그때는 근거를 갖는다.

## 11. v3.1 하네스 하드닝

### 11-1. 신뢰 경계 — PROMOTION != EXECUTION

```
EXECUTED                     구현 commit 존재
ORCHESTRATOR_PRECHECK_PASS   오케스트레이터 자체 점검 통과
INDEPENDENTLY_AUDITED        adversarial + SSOT 가 동일 exec SHA 를 독립검토
RECONCILED                   orchestrator 가 두 audit 을 증거 기반으로 재결
PROMOTED                     verified baseline 으로 main 에 승격
```

`ORCHESTRATOR_PRECHECK_PASS` 를 `ACCEPTED` / `VERIFIED` / `PROMOTED` 와 동의어로 쓰지 않는다.

### 11-2. audit lag invariant

```
MAX_UNAUDITED_EXEC_CYCLES = 1
unaudited_cycle_depth = latest_exec_cycle − latest_fully_audited_cycle
```

`fully_audited` 는 `adversarial.target_exec_sha == exec_sha` **AND** `ssot.target_exec_sha == exec_sha`
**AND** orchestrator reconciliation complete 를 모두 만족할 때만이다.

state.json 에 8개 필드로 추적하고 watchdog 이 매 120초 검증한다.

### 11-3. main branch write protection — 3중

| 층 | 내용 | 검증 |
|---|---|---|
| server-side | `research/landing-accessibility-main` force-push 금지·삭제 금지·linear history | gh CLI 설정 완료 |
| server-side | `research/refcohort-r1` **lock_branch=true + enforce_admins=true** | Pilot 완전 잠금 |
| client-side | `.git/hooks/pre-push` — main 은 `LA_PROMOTION` 없이 차단, Pilot 은 무조건 차단 | 다른 SHA push 시도 → **실제 BLOCKED 확인** |
| script | `scripts/promote_landing_main.sh` 6개 검사 | hook 을 유일 보증수단으로 삼지 않는다 |

`SERVER_PROTECTION_UNAVAILABLE` 이 아니다 — 원격 보호가 실제로 활성화됐다.

### 11-4. watchdog 감시 항목 (120초)

```
P0  PILOT_WRITE                 브랜치 SHA 이동 + 워크트리 변경
P0  E001_UNAUTHORIZED           4개 워크트리의 evidence/ 파일 존재
    AUDIT_REQUIRED              exec HEAD 변화
    AUDIT_LANDED                감사 브랜치 변화
    AUDIT_LAG                   exec sha vs audit target sha 불일치
    SOURCE_AUTHORITY_CHANGED    authority_manifest sha256 변화
    DIRECTIVE_UPDATED           control HEAD 변화
```

### 11-5. cycle artifact

`control/cycles/Cxxx.json` 에 directive / executor / audit_adversarial / audit_ssot /
reconciliation / promotion / gate_before / gate_after / accepted·rejected·deferred findings / open_debt 를 기록한다.

**commit message 를 상태 데이터베이스로 쓰지 않는다.**

## 12. PROM-001 — closed loop 완주

```
main   32460b87334a67f6a74823ac55f85ca80a9f8980  →  edb0478f56d06ed65cd03680727e366700ac7e84
Pilot  32460b87  (lock_branch, 불변)
```

### 12-1. 승격까지의 경로

```
C009 executor        감사 수용 12건 시정                       fe86e190
  ├ adversarial      PASS  P0 0 / P1 2 / P2 5                fd9773a1
  └ ssot             PASS  P0 0 / P1 2                       7c928f5b
C009 재결            accepted 8 / rejected 0 → promotion BLOCKED   bc248ff1
C011 executor        P1 3건 + P2 5건 시정                      edb0478f
  ├ adversarial      PASS  P0 0 / P1 0 / P2 5                903e2472
  │                  p1_remediation_verified 3/3 true
  └ ssot             PASS  P0 0 / P1 0 / P2 7                695caed7
                     a1_source_unmodified true
C011 재결            accepted 11 / rejected 0 / deferred 11    27bbbf37
PROM-001             3중 보호 통과 후 승격
```

**감사가 promotion 을 실제로 두 번 막았다.** C009 의 P1 3건이 identity/source/provenance 를 깨고 있었고,
그것이 해소되기 전에는 어떤 executor 주장으로도 문이 열리지 않았다.

### 12-2. 승격 결정 필드

두 감사관에게 promotion 가부를 직접 결정하는 필드를 심었다.

| 필드 | 담당 | 의미 |
|---|---|---|
| `p1_remediation_verified` | adversarial | P1 3건이 **실제로** 해소됐는가 |
| `a1_source_unmodified` | ssot | verbatim 복원을 **원문 수정으로 맞춘 것은 아닌가** |

후자가 특히 중요했다. 원문을 고쳐서 일치시켰다면 그것은 A1 변조이고 즉시 P0다.
ssot 은 `git diff fe86e190..edb0478 -- sources/wiseapp/raw` 가 빈 출력임을 확인하고,
raw 4종 sha256 을 재계산해 매니페스트와 전건 일치시켰다.

### 12-3. U+00A0 — verbatim 의 진짜 의미

원문 INDEX 의 Chapter 1 세 절은 `세대` 뒤에 U+00A0 를 쓰고, Ch2~4 의 8개 절은 쓰지 않는다.
executor 가 그 **비대칭까지 그대로** 복원했고, ssot 이 원문에 U+00A0 가 94회 실재하며
INDEX 에서는 정확히 그 세 절에만 나타남을 독립 확인했다.

```
C009  SAME  0 / MISMATCH 11
C011  SAME 15 / MISMATCH  0   (chapter 4 + section 11)
```

**"비슷하게 맞췄다" 는 verbatim 이 아니다.**

### 12-4. 검증의 한쪽 끝은 원본이어야 한다

C009 의 "1:1 대조가 코드로 강제된다" 는 주장은 실제로는
`index_from_source`(파생 A) 와 `source_section_title`(파생 B) 의 일치였다.
둘 다 같은 방식으로 원문에서 벗어나면 통과한다. 실제로 그랬다.

C011 은 테스트의 한쪽 끝을 `raw/wiseapp933_text.txt` 파싱으로 바꿨고,
adversarial 이 `BODY_TEXT` 가 정말 그 파일을 읽는지 **코드로** 확인했다.

### 12-5. 반례 주입 — 테스트가 진짜 잡는지 검사

adversarial 이 P1-1 위치정렬 시정을 검증할 때 naver 그룹의 `member_domains` 순서만 뒤집었다.
집합은 불변이므로 C009 의 기존 테스트는 통과한다. 신규 테스트는 정확한 위치와 이유를 찍고 실패했다.

**테스트가 무엇을 검사하는지 읽지 않으면 `pytest PASS` 는 아무 의미가 없다.**
같은 감사에서 `matches_existing_c002_output` 이 실제 비교가 아니라 `existing.exists()` 였음도 드러났다.

### 12-6. VERIFIED / UNVERIFIED 분리

promotion 은 전체 연구의 PASS 가 아니다. `control/promotions/PROM-001.json` 에 범위를 못박았다.

**VERIFIED (소스 계층 한정)** — A1 원문 무결 · 원문 구조 4/11/17 · INDEX verbatim ·
261행 값 불변 · entity 81/82/142 · APP·RETAIL 137+124 · web_target_group 정렬 무결 ·
사전판단 write-only 분리 · A2 스냅샷 COMPLETE · xlsx 유입 0

**UNVERIFIED** — web eligibility · URL · certification join · feasibility ·
measurement engine · judgment semantics · probe coverage · E000 · RQ2~4 성립 여부

**KNOWN DEBT 11건** — 전부 P2, 검증 가능성 계열. ssot 이 *"명시적으로 유예하지 않으면 부채가
조용히 사라진다"* 고 지적해 artifact 에 전량 기록했다.

### 12-7. 하네스가 관리자 자신을 두 번 잡았다

| # | 사건 | 탐지 | 시정 |
|---|---|---|---|
| P0 #1 | cwd 오염으로 Pilot 브랜치에 커밋 | `P0_VIOLATION pilot branch moved` | `git reset --mixed`, 원격 미오염 |
| P0 #2 | exec 워크트리에 커밋 — executor 진행 중 작업 16파일을 삼킴 | `AUDIT_REQUIRED exec=2922af49` + `AUDIT_LAG` | `git -C reset --mixed`, 작업 17파일 전량 보존 |

#1 의 예방책("절대경로 사용")이 **파일 경로에만 적용되고 git 명령에는 적용되지 않아** #2 가 재발했다.
예방 v2 는 `git -C <절대경로>` 강제이고 cwd 의존 자체를 제거한다.

**예방책이 근본원인의 일부만 덮으면 재발한다.**
