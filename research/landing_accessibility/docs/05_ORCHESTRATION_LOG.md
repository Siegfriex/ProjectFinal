# 05 — 오케스트레이션 실행 로그 (Phase 1)

**하네스** orchestrator-constitution-v3 · **Phase** P1_ISOLATION_AND_SOURCE_REFREEZE
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
| C006 | executor | A2 인증 레지스트리 자체 스냅샷 | 진행 중 |

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

## 4. A1 권위자료 취득 기록

원문은 SPA 라 HTML 에 데이터가 없었다. 두 경로로 확보하고 상호 교차검증했다.

```
1) 내부 API   POST /insight/detail/getDetail.json  body {"insightNid":"933","preview":0}  → 154KB JSON
2) 렌더링     playwright chromium → HTML · 본문텍스트 · full-page 스크린샷 · CDN 이미지 11종
```

`InsightAjax.js` → `InsightDetail.js` → `Common.requstPost` 순으로 읽어 엔드포인트와 파라미터 형태를 특정했다.
`preview` 는 `Number(0)` 이라 `false` 로 보내면 400 이 난다.

**본문 `<table>` 0개 / `<img>` 11개** — 모든 순위표가 이미지다. 텍스트 파싱 경로가 없어 figure 판독이 유일하다.

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
