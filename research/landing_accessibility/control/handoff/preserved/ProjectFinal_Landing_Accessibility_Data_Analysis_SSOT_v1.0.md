> ## ⚠ SUPERSEDED_FOR_EXECUTION / PRESERVED_FOR_HISTORY
>
> **이 문서는 v1 분석 SSOT 이며 현행 실행권위가 아니다.**
> 현행: `research/landing-accessibility-main` 의 `research/landing_accessibility/docs/v2/00_SSOT_v2.0.md`.
>
> - 유효: 검증된 사실(SHA·카운트·source provenance)과 이력.
> - 무효: 목표·범위·단위·해석·phase. v2 SSOT 가 대체한다.
> - 이 문서는 이력·회귀검증용으로 **삭제·이동하지 않는다.**
>
> 근거: adversarial V2-C001 `orchestrator-entrypoint-still-routes-to-v1-scope`. 시정: V2-C002.

---

# ProjectFinal — 고령층 실사용 모바일웹 랜딩 접근성 데이터분석 SSOT

**문서 지위**: DATA ANALYSIS SSOT / PRE-E001  
**기준시각**: 2026-08-26 KST  
**현재 검증 기준선**: `research/landing-accessibility-main @ 5a9015d1e95b15304aaf53a73efb475934610b82`  
**현재 운영 단계**: `P2_WEB_ELIGIBILITY_AND_URL_IDENTITY`  
**본수집 상태**: `E001 NOT STARTED / PROHIBITED UNTIL GO`  
**분석 원칙**: 현재 동결된 모집단·권위·관측범위·판정체계를 유지하며, 향후 변경은 오류 수정 또는 명시적 Research Director 결정에 한정

---

## 0. Executive Summary

본 연구는 **고령층이 실제로 많이 사용하는 서비스 생태계**를 먼저 외부 실사용 자료에서 고정한 뒤, 그중 **공식 모바일웹 랜딩이 존재하는 서비스**를 대상으로 KWCAG 2.2 기반 접근성 상태를 관측하는 실증 연구임.

모집단의 출발점은 Wiseapp Insight 933의 공개 패널이며, 웹접근성 품질인증 목록은 모집단을 구성하는 자료가 아니라 각 웹 대상에 결합하는 외부 속성임. 따라서 분석은 다음 두 질문을 분리함.

1. **제도 도달성**: 고령층 실사용 서비스 중 공식 웹으로 관측 가능한 대상에 현재 유효 웹접근성 품질인증이 어느 정도 도달하는가.
2. **실제 랜딩 접근성 상태**: 동일한 실사용 서비스의 공식 모바일웹 최초 랜딩에서 어떤 KWCAG 2.2 미흡·불확정 패턴이 관측되는가.

인증 O/X 비교는 전체 연구의 성립조건이 아님. 인증 교차점이 충분한 경우에만 조건부 분석으로 수행하며, 교차점이 작으면 **인증 도달범위 + 전체 실사용 웹서비스 접근성 실태**가 주 분석이 됨.

본 연구는 웹사이트 전체 인증평가, 로그인 이후 과업 성공률, 고령 사용자 개인의 실제 사용성, 인증의 인과효과를 추정하지 않음. 관측 범위는 **공식 모바일웹 최초 랜딩과 동일 문서의 정적 DOM/AX 구조**임.

---

# 1. 연구 목적

## 1.1 분석 목적

고령층의 디지털 문제를 단순 기기 보유 여부가 아니라 실제 생활서비스 이용에서 발생하는 마찰의 문제로 접근함. 기존 문제정의 자료에서도 스마트폰 보유·기본기능 사용 증가와 별개로 거래·구매·위치·배송 등 생활서비스 활용 폭이 빠르게 감소하는 패턴이 확인된 바 있음.

본 단계의 역할은 개인 수준의 독립수행 원인을 직접 설명하는 것이 아니라, 그 개인이 접하게 되는 **실제 서비스 환경 측 마찰**을 관측 가능한 단위로 측정하는 것임.

따라서 본 연구의 직접 목적은 다음과 같음.

- 고령층 실사용 상위 서비스의 웹 관측 가능 범위 확정
- 해당 웹 대상에 대한 현재 유효 웹접근성 품질인증 도달범위 측정
- KWCAG 2.2 criterion 단위 접근성 결과 산출
- 서비스별·criterion별 미흡 및 불확정 분포 구조 파악
- 접근성 적응기능의 존재·발견 가능성·활성화 가능성 관측
- 반복적으로 나타나는 접근성 장벽의 우선순위 선정
- 기사·보고서에서 인용 가능한 claim과 인용 불가능한 claim의 경계 확정

---

# 2. 연구질문

## RQ0. 웹 관측 가능 범위

Wiseapp 933에 등장하는 measurement entity 중 공식 웹서비스 랜딩으로 관측 가능한 대상은 어느 정도인가.

핵심 산출:

- source entity 수
- web target 수
- `WEB_SERVICE` 수
- `APP_ONLY / SYSTEM_APP / OFFICIAL_PRODUCT_PAGE / RETAIL_OFFLINE_ONLY / UNRESOLVED` 수
- 웹 관측 가능 비율

## RQ1. 인증제도 도달범위

웹 관측 가능한 실사용 서비스 중 감사일 기준 유효한 웹접근성 품질인증을 보유한 비율은 어느 정도인가.

\[
CertificationReach
=
\frac{N(\text{certified\_current}=1)}
{N(\text{WEB\_SERVICE})}
\]

이 비율은 **동결된 Wiseapp 기반 웹 대상 frame의 기술통계**이며 전국 서비스 생태계 전체에 대한 확률표본 추정치로 해석하지 않음.

## RQ2. 랜딩 접근성 상태

공식 모바일웹 랜딩에서 KWCAG 2.2 criterion별로 확인되는 `PASS / FAIL / UNDETERMINED / NA` 분포는 어떠한가.

주요 관심:

- confirmed FAIL이 자주 발생하는 criterion
- 적용기회가 많지만 불확정 비율이 높은 criterion
- 서비스별 접근성 부담의 분포
- 최초 viewport와 전체 landing document의 차이

## RQ3. 서비스 간·소스 패널 간 이질성

접근성 결과가 Wiseapp의 원천 패널, APP/RETAIL domain, 서비스 노출 정도, 웹 대상 특성에 따라 어떻게 달라지는가.

원칙:

- Wiseapp가 제공하지 않은 연구자 임의 task category를 만들지 않음
- 원문 `panel_id / source_section / domain / axis_type`을 분석 strata로 사용
- 동일 서비스가 여러 패널에 등장하더라도 전체 pooled 분석에서 반복 독립표본으로 세지 않음

## RQ4. 접근성 적응기능

랜딩에서 고령층·저시력 사용자 등을 위한 접근성 적응기능이 얼마나 존재하며, 최초 화면에서 발견 가능하고 실제 활성화 가능한가.

관측 분류:

- `SENIOR_MODE`
- `EASY_MODE`
- `LARGE_TEXT`
- `FONT_RESIZE`
- `HIGH_CONTRAST`
- `ACCESSIBILITY_MENU`
- `OTHER`
- `NONE`

적응기능은 KWCAG 준수의 대체지표로 사용하지 않음.

## RQ5. 인증 O/X 접근성 차이 — 조건부 분석

최종 feasibility에서 인증군과 비인증군이 분석 가능한 규모를 확보하는 경우에만, 동일 source-native strata 안에서 랜딩 접근성 특성 차이를 탐색함.

비교가 불가능한 경우:

- 비교를 위해 모집단을 확장하지 않음
- 인증 목록에서 별도 비교집단을 끌어오지 않음
- RQ5는 `NOT FEASIBLE`로 종료
- RQ1 인증 도달범위와 RQ2 전체 접근성 실태를 주 결과로 유지

---

# 3. 권위 및 데이터 경계

## 3.1 권위 순서

| Rank | Source | 역할 |
|---|---|---|
| A0 | Research Director 명시 결정 | 연구 범위·동결·GO |
| A1 | Wiseapp Insight 933 동결본 | 실사용 모집단·패널·순위의 권위 |
| A2 | 한국디지털접근성진흥원 웹접근성 인증 목록 | `certified_current` 권위 |
| A3 | KWCAG 2.2 공식 원문 | 접근성 criterion의 규범적 기준 |
| A4 | 공식·검증된 KWCAG 해설자료 | 적용·예외·경계값 해석 보조 |
| A5 | Main Study 파생 데이터 | 분석용 구조화 데이터 |

A2는 모집단 source가 아니며 A3/A4는 서비스 선정 source가 아님.

## 3.2 현재 검증된 Source Frame

현재 promoted baseline 기준:

| 항목 | 현재 값 |
|---|---:|
| Wiseapp raw structured rows | 261 |
| APP rows | 137 |
| RETAIL rows | 124 |
| Source panels | 17 |
| Measurement entities | 81 |
| Entity aliases | 82 |
| Source memberships | 142 |
| Web target groups | 68 |
| Human entity review unresolved | 0 |
| Confirmed official landing URL | 현재 동결 기준 미확정 |
| E001 Evidence | 0 |

Wiseapp 원문은 서로 다른 지표·단위·기간을 가진 여러 패널의 집합임. 따라서 261행을 하나의 동일척도 테이블처럼 평균·합산하지 않음.

현재 period axis는 패널별로 보존하며, 반기 패널과 단월 패널의 raw metric을 직접 비교하지 않음.

## 3.3 인증 Snapshot

현재 A2 snapshot:

- `snapshot_id = KWACC_WA_20260826`
- raw rows: 2,283
- 감사일 유효 인증: 226
- snapshot status: `COMPLETE`
- 인증 대상 URL 보유: 2,279
- 감사일 기준 status는 목록 라벨이 아니라 인증 시작·종료일을 직접 계산

최종 `certified_current=1` 조건:

\[
valid\_on\_audit\_date
\land
target\_scope\_match
\land
service\_identity\_match
\]

등록도메인 일치만으로 인증을 부여하지 않음.

---

# 4. 분석 객체와 단위

본 연구는 서로 다른 분석단위를 명시적으로 분리함.

## 4.1 Source Row

Wiseapp 원문 패널의 한 순위 행.

`panel_id × rank × raw_entity_name × value × unit`

역할:

- 모집단 provenance 보존
- 서비스 노출 위치와 원자료 맥락 보존

접근성 outcome의 독립 관측 단위가 아님.

## 4.2 Measurement Entity

Wiseapp에서 측정 의미상 구분되는 서비스 개체.

- 동일 브랜드라도 APP과 RETAIL에서 측정 의미가 다르면 별도 measurement entity 가능
- 원문 label은 alias mapping으로 보존

역할:

- source row 정규화
- source membership 유지

## 4.3 Web Target

실제 접근성 측정을 수행하는 웹 랜딩 단위.

여러 measurement entity가 실제 동일한 공식 랜딩 URL을 가리키는 경우 관측은 한 번만 수행함.

**Primary accessibility weighting unit = unique web target**

## 4.4 Observation

\[
Observation
=
service\_id
\times official\_landing\_url
\times audit\_date
\times protocol\_version
\]

한 observation은 정확히 하나의 DOM, AX tree, screenshot, probe, evidence manifest record와 대응함.

## 4.5 Service × Criterion

접근성 분석의 핵심 Long-form 단위.

한 행은 `observation_id × criterion_id`이며 다음을 가짐.

- applicability
- applicable_count
- pass_count
- fail_count
- undetermined_count
- machine_confirmed_fail
- review_required_flag
- human_final_verdict

---

# 5. 분석 데이터 모델

## 5.1 계보 모델

```text
A1 Wiseapp Source
      │
      ▼
panel_registry
      │
      ▼
source_ranking_rows
      │
      ▼
measurement_entity ───── entity_alias_map
      │
      ├──────────── source_membership
      ▼
web_target
      │
      ├──────────── web_eligibility / url_review
      │
      ├──────────── A2 certification_match
      ▼
landing_observation
      │
      ├── DOM
      ├── AX
      ├── Screen
      └── Probe
      │
      ▼
criterion_opportunity
      │
      ▼
criterion_result
      │
      ├── machine result
      └── human review
      ▼
final_judgment
      │
      ▼
analysis marts
      │
      ├── service-level
      ├── service × criterion
      ├── panel × service
      └── adaptive-control
```

## 5.2 권장 분석용 테이블

### `dim_panel`

- panel_id
- source_chapter
- source_section
- domain (`APP | RETAIL`)
- axis_type
- metric_name
- unit
- period_axis
- panel_n

### `fact_source_ranking`

- source_row_id
- panel_id
- measurement_entity_id
- rank
- raw_label
- raw_value
- raw_unit

### `dim_measurement_entity`

- measurement_entity_id
- canonical_name
- entity_type
- source_domain
- entity_review_status

### `bridge_source_membership`

- measurement_entity_id
- panel_id
- source_row_id

### `dim_web_target`

- web_target_id
- web_eligibility_status
- official_landing_url
- final_url
- registered_domain
- url_confidence
- web_target_group_status

### `dim_certification`

- web_target_id
- certified_current
- cert_match_basis
- certification_number
- cert_start_date
- cert_end_date
- cert_match_evidence

### `fact_observation`

- evidence_run_id
- observation_id
- web_target_id
- audit_date
- protocol_version
- measurement_status
- target_url
- final_url
- static_evidence_complete
- interpretation_limits

### `fact_criterion_result`

- observation_id
- criterion_id
- applicability
- applicable_count
- pass_count
- fail_count
- undetermined_count
- verdict_state
- automation_grade
- machine_confirmed_fail
- review_required_flag
- human_final_verdict

### `fact_adaptive_control`

- observation_id
- control_type
- detected
- initial_viewport_visible
- accessible_name_present
- activation_attempted
- activation_success
- paired_observation_id

---

# 6. 파생변수 및 지표 정의

## 6.1 Source prominence 지표

Wiseapp panel은 서로 다른 metric과 단위를 사용하므로 raw value를 하나의 popularity score로 합치지 않음.

### Panel-normalized rank

\[
rank\_position_{ip}
=
1-\frac{rank_{ip}-1}{N_p-1}
\]

- 1에 가까울수록 해당 panel 상위
- panel 내부 비교에만 사용

### Panel appearance count

\[
panel\_appearance_i
=
\#\{p: i \in p\}
\]

동일 entity가 몇 개의 Wiseapp panel에 반복 등장하는지 나타내는 노출 범위 지표.

이 지표는 확률적 이용률 추정치가 아니며 분석 가중치로 사용하지 않음.

## 6.2 인증 도달률

주 분모는 `WEB_SERVICE`로 확정된 unique web target.

\[
CertificationReach
=
\frac{CertifiedWebTargets}{EligibleWebTargets}
\]

보조적으로 source universe 대비 인증 수를 별도 제시할 수 있으나, `APP_ONLY` 등을 웹인증 분모에 넣어 주 도달률을 계산하지 않음.

## 6.3 Criterion 상태

```text
FAIL           fail_count > 0
UNDETERMINED   fail_count = 0 AND undetermined_count > 0
PASS           applicable_count > 0 AND 전 적용기회 결정 완료 AND fail_count = 0
NA             적용기회 없음
```

NA와 UNDETERMINED는 PASS로 환산하지 않음.

## 6.4 서비스 수준 접근성 burden

서비스 i에 대해:

\[
ConfirmedFailRate_i = \frac{F_i}{F_i+P_i}
\]

\[
UndeterminedShare_i = \frac{U_i}{F_i+P_i+U_i}
\]

\[
DecisionCoverage_i = \frac{F_i+P_i}{F_i+P_i+U_i}
\]

세 지표를 동시에 제시함.

`ConfirmedFailRate`만 단독 순위화하면 관측불확정이 많은 서비스를 과소평가할 수 있으므로 반드시 `DecisionCoverage`와 병기함.

## 6.5 Criterion 수준 prevalence

criterion j:

\[
FailPrev^{decided}_j
=
\frac{N_j(FAIL)}{N_j(FAIL)+N_j(PASS)}
\]

\[
FailShare^{applicable}_j
=
\frac{N_j(FAIL)}{N_j(FAIL)+N_j(PASS)+N_j(UNDETERMINED)}
\]

\[
UndeterminedShare_j
=
\frac{N_j(UNDETERMINED)}{N_j(FAIL)+N_j(PASS)+N_j(UNDETERMINED)}
\]

Top barrier 선정 시 단순 fail rate뿐 아니라 applicable service 수, confirmed fail 수, undetermined share, human review 완료 여부를 함께 사용함.

---

# 7. 관측 및 수집 프로토콜

## 7.1 브라우저 baseline

- viewport: `390 × 844 CSS px`
- device scale factor: `3`
- locale: `ko-KR`
- timezone: `Asia/Seoul`
- mobile context
- touch enabled
- fresh browser context
- 로그인·쿠키·저장세션 없음
- 동일 protocol version

## 7.2 관측 범위

### INITIAL_VIEWPORT

스크롤 전 최초 가시영역.

주 관측:

- 적응기능 노출
- 팝업/overlay
- 텍스트 대비
- 조작요소 크기
- accessible name

### LANDING_DOCUMENT

동일 랜딩 문서의 DOM/AX 전체 정적 관측.

주 관측:

- image alt
- label/form relation
- link text
- contrast
- operable target
- language/title
- autoplay
- validated KWCAG opportunity

로그인·결제·검색 결과·본인확인 이후는 주 분석에서 제외함.

---

# 8. E001 진입 전 Data Quality Gate

다음 조건이 모두 충족되어야 E001 수집 가능.

## Target Frame

- 모든 web target eligibility 판정 완료
- `UNRESOLVED=0` 또는 명시적 제외결정 존재
- 모든 `WEB_SERVICE` official landing URL 존재
- URL identity conflict 0

## Certification

- A2 snapshot `COMPLETE`
- 모든 web target `certified_current ∈ {0,1}`
- ambiguous certification match 0

## Evidence Engine

- hash 기반 service/observation ID
- observation ID collision 0
- append-only 강제
- raw evidence manifest 필수
- DOM=AX=Screen=Probe=Manifest 1:1 불변식
- target/final/probe URL binding 검증
- overwrite guard
- symlink/path escape guard

## Judgment

- PASS/FAIL/NA/UNDETERMINED 의미론 동결
- AUTO_DECIDABLE / AUTO_FLAG_ONLY 분리
- criterion별 raw feature coverage 확인
- `validated_for_main_study` 명시

## Smoke

- E000 8~12 target 수행
- collision 0
- wrong evidence reference 0
- silent loss 0
- overwrite 0
- unexplained exclusion 0

---

# 9. EDA 전체 구조

EDA는 한 번에 수행하지 않고 데이터 생성 단계와 일치하도록 분리함.

```text
EDA-00  Frame & Provenance Audit
EDA-01  Wiseapp Source Structure
EDA-02  Web Eligibility & Target Frame
EDA-03  Certification Reach
──────────── E001 ────────────
EDA-04  Evidence Completeness
──────────── JUDGMENT ────────
EDA-05  Service Accessibility Profile
EDA-06  Criterion Barrier Profile
EDA-07  Adaptive Accessibility Controls
EDA-08  Source-Panel Heterogeneity
EDA-09  Certification Contrast [conditional]
EDA-10  Robustness / Sensitivity
EDA-11  Case Selection / Publication Mart
```

---

# 10. EDA-00 — Frame & Provenance Audit

## 목적

분석 전에 데이터 계보가 끊기지 않았는지 확인.

## 검사항목

- source_row_id unique = 261
- source row 261 conservation
- APP + RETAIL = 261
- entity → membership orphan 0
- web target → entity orphan 0
- duplicate official URL review
- ID collision
- source panel expected N vs actual N
- period axis completeness
- source raw hash consistency
- certification snapshot completeness
- analysis table이 invalidated legacy source를 참조하는지 여부

## 출력

- `qa_frame_summary.csv`
- `qa_orphan_registry.csv`
- `qa_duplicate_identity.csv`
- `qa_provenance_gate.json`

**Gate 실패 시 이후 EDA 중단.**

---

# 11. EDA-01 — Wiseapp Source Structure

## 분석질문

- 17개 패널의 구성은 어떠한가.
- APP/RETAIL row와 entity가 어떻게 분포하는가.
- 어떤 entity가 여러 panel에 반복 노출되는가.
- source-native panel 구조가 web target frame으로 축약될 때 어떤 정보가 유지·소실되는가.

## 표

1. panel별 row 수
2. panel별 unique entity 수
3. entity별 panel appearance count
4. domain별 entity 수
5. axis_type별 구성
6. period axis별 panel 수

## 시각화

- panel × entity presence heatmap
- panel별 Top-N depth bar
- APP/RETAIL entity overlap
- entity panel appearance histogram
- source rows → entities → web targets 흐름도

## 금지

- 서로 다른 panel raw value 평균
- APP user count와 RETAIL payment index의 숫자 비교
- single-month와 half-year metric 직접 비교
- raw rank를 전체 서비스 절대순위로 재구성

---

# 12. EDA-02 — Web Eligibility & Target Frame

## 분석질문

- 68 web target group 중 실제 `WEB_SERVICE`는 몇 개인가.
- 어떤 이유로 웹 측정대상에서 제외되는가.
- source domain에 따라 web eligibility가 다른가.
- 공유 target 가설이 실제 URL 검수 후 유지되는가.

## 핵심 표

- `web_eligibility_status × count`
- `domain × web_eligibility_status`
- `exclusion_reason × count`

## 시각화

- eligibility status bar
- APP/RETAIL별 eligibility stacked bar
- source entity → web target → eligible target funnel
- shared target split/merge summary

## 품질조건

- exclusion은 반드시 근거와 reviewer를 가짐
- 확인 불가를 APP_ONLY/SYSTEM_APP로 변환하지 않음
- `UNRESOLVED`는 별도 상태

---

# 13. EDA-03 — Certification Reach

## 분석질문

- web-eligible target 중 현재 유효 인증은 몇 개인가.
- 인증은 어떤 source panel/domain에 도달하는가.
- 인증 이력과 현재 유효 인증을 구분하면 구조가 어떻게 달라지는가.

## 핵심지표

- `N_web_eligible`
- `N_certified_current`
- `N_noncertified`
- `CertificationReach`
- panel별 certified/non-certified count
- domain별 certified/non-certified count

## 시각화

- certification reach count/proportion
- panel × certification matrix
- domain별 certified count
- source-to-certification intersection diagram

## Feasibility 판정

### TIER_C

한쪽 그룹이 0 또는 1인 strata.

→ 집단 gap을 결과로 제시하지 않음.

### TIER_B

양쪽이 존재하나 매우 작은 strata.

→ 기술통계·개별 사례만 허용.

### TIER_A

양쪽이 충분히 존재하고 service-resampling 기반 안정성 분석이 가능한 strata.

→ 조건부 group comparison 허용.

TIER의 최종 수치경계는 **최초 feasibility 결과를 확인한 직후 outcome을 보기 전에 동결**함.

---

# 14. EDA-04 — Evidence Completeness

E001 직후 outcome을 보기 전에 수행.

## 분석질문

- 모든 측정 성공 observation에 4종 raw evidence가 존재하는가.
- 차단/transport failure가 특정 서비스군에 집중되는가.
- static evidence coverage가 criterion별로 충분한가.

## 핵심지표

- measured
- access_blocked
- transport_failed
- DOM count
- AX count
- screenshot count
- probe count
- manifest count
- static_evidence_complete rate

## 시각화

- observation × evidence type completeness matrix
- measurement status bar
- failure reason distribution

**Evidence completeness가 깨지면 outcome EDA 금지.**

---

# 15. EDA-05 — Service Accessibility Profile

## 분석단위

unique web target.

## 핵심지표

- confirmed fail count
- confirmed fail rate
- undetermined share
- decision coverage
- applicable criterion count
- review-required count
- adaptive control presence

## 시각화

- 서비스별 confirmed fail rate dot plot
- fail rate × decision coverage scatter
- 서비스별 verdict composition stacked bar
- burden 상위 서비스 상세 table

## 해석

서비스의 fail count가 높더라도 applicable criterion이 많은 서비스일 수 있으므로 절대 fail count와 rate를 병기함.

---

# 16. EDA-06 — Criterion Barrier Profile

## 목적

반복적으로 나타나는 접근성 장벽 식별.

## criterion별 산출

- applicable service n
- PASS n
- FAIL n
- UNDETERMINED n
- NA n
- confirmed fail prevalence
- applicable denominator fail share
- undetermined share
- AUTO_DECIDABLE / HUMAN_CONFIRMED 구분

## 시각화

### 1. Barrier ranking

y = criterion  
x = confirmed fail share  
점 크기 = applicable service n  
별도 표시 = undetermined share

### 2. Service × criterion heatmap

- PASS
- FAIL
- UNDETERMINED
- NA

4상태 행렬.

### 3. Evidence uncertainty plot

criterion별 decided coverage와 fail prevalence 병치.

## Top Barrier 선정조건

- `validated_for_main_study=true`
- 충분한 applicable n
- confirmed FAIL 근거
- human review 필요항목 검토 완료
- 단순 UNDETERMINED 비율만 높은 항목 제외

---

# 17. EDA-07 — Adaptive Accessibility Controls

## 핵심질문

- 적응기능이 있는 서비스 비율
- 어떤 유형이 가장 흔한가
- 최초 viewport에서 발견 가능한가
- accessible name이 있는가
- 실제 1회 활성화가 가능한가

## 지표

\[
AdaptiveControlPrevalence
=
\frac{N(\text{control detected})}{N(\text{web targets})}
\]

추가:

- viewport visibility rate
- accessible-name rate
- activation success rate

## Paired 분석

기능이 있는 경우 `default landing` vs `adaptive-mode landing`을 같은 서비스 내부 paired observation으로만 비교.

관심:

- text size
- contrast
- layout/overlay
- accessible-name 변화

이 결과를 KWCAG 인증 대체점수로 사용하지 않음.

---

# 18. EDA-08 — Source-Panel Heterogeneity

## 목적

접근성 outcome이 Wiseapp source 구조에 따라 달라지는지 탐색.

## 원칙

동일 web target이 여러 panel에 등장할 수 있으므로 panel별 표에서는 중복 membership을 허용하지만, 전체 pooled 평균에서 반복서비스를 독립표본으로 세지 않음.

## 분석

- panel별 median confirmed fail rate
- domain별 distribution
- panel appearance count와 burden의 Spearman correlation
- panel-normalized rank와 burden의 within-panel exploratory correlation

### correlation 조건

- 동일 metric family 내부 또는 panel 내부만 사용
- 서로 다른 Wiseapp metric raw value를 한 회귀식에 넣지 않음

---

# 19. EDA-09 — Certification Contrast [조건부]

Feasibility가 허용하는 경우에만 실행.

## Primary effect description

criterion별:

\[
RiskDifference_j
=
P(FAIL_j \mid Certified)-P(FAIL_j \mid NonCertified)
\]

서비스 수준:

- median confirmed fail rate difference
- median decision coverage difference
- adaptive-control prevalence difference

## 추론방법

본 frame은 확률표본이 아니므로 일반 모집단에 대한 고전적 CI로 과장하지 않음.

bootstrap은 **표본추출 오차 추정**이 아니라 **관측 서비스 구성에 대한 결과 안정성 진단**으로 사용.

- resampling unit = unique web target
- 5,000 bootstrap 반복 권장
- median difference / risk difference distribution
- leave-one-service-out 병행

criterion별 p-value를 산출할 경우 exploratory supplement로만 사용하고, 다중검정에는 Benjamini-Hochberg FDR 적용. 기사 주장은 p-value 순위가 아니라 effect size와 support count 중심.

인증군 n이 매우 작으면 본 EDA 자체를 실행하지 않음.

---

# 20. EDA-10 — Robustness / Sensitivity

## 20.1 UNDETERMINED sensitivity

각 criterion의 미확정 결과에 대해:

\[
LB_j = \frac{FAIL}{FAIL+PASS+UNDET}
\]

\[
UB_j = \frac{FAIL+UNDET}{FAIL+PASS+UNDET}
\]

기사에서는 확정수치와 불확정 폭을 분리함.

## 20.2 Leave-One-Service-Out

특정 대형·복잡 서비스 한 곳이 전체 결과를 지배하는지 확인.

모든 핵심 service-level summary에서:

- 전체값
- 최대 변화폭
- 결과방향 유지 여부

보고.

## 20.3 Source-membership sensitivity

여러 panel에 반복 등장하는 서비스 처리에 대해:

1. service equal weighting
2. panel-specific descriptive
3. one-service-one-vote

결과 비교.

주 결과는 1번.

## 20.4 Access-block sensitivity

ACCESS_BLOCKED를 접근성 FAIL로 처리하지 않음.

분리:

- measurement failure
- accessibility result

blocked 서비스 제외가 frame composition을 바꾸는 정도를 별도 보고.

---

# 21. 분석 모델링 전략

본 연구의 주 목적은 예측모형 개발이 아니라 **관측 구조의 정확한 기술·비교**임. 따라서 복잡한 ML score는 주 분석으로 사용하지 않음.

## Model 0 — Frame Model

`SourceRow → Entity → WebTarget`

목적:

- 모집단 구조
- 웹 관측범위
- 인증 도달범위

## Model 1 — Criterion Prevalence Model

`WebTarget × Criterion`

목적:

- criterion별 FAIL/UNDET 구조
- 서비스 간 접근성 장벽 profile

주 분석.

## Model 2 — Service Burden Model

서비스 단위 vector:

```text
confirmed_fail_rate
undetermined_share
decision_coverage
applicable_criterion_n
adaptive_control_presence
```

목적:

- 서비스 간 상대적 접근성 상태 파악
- 사례선정

단일 종합점수 하나로 압축하지 않음.

## Model 3 — Source Heterogeneity Model

설명변수:

- source domain
- panel membership
- panel appearance count
- within-panel normalized rank

결과:

- confirmed_fail_rate
- criterion-specific fail state

목적:

원자료 구조별 이질성 탐색.

인과해석 금지.

## Model 4 — Certification Contrast Model [conditional]

Feasibility가 충분한 경우:

- binary criterion outcome의 risk difference
- 서비스 burden median difference
- bootstrap stability
- leave-one-out

필요 시 보조적으로 Fisher exact test 사용.

복잡한 다변량 회귀나 propensity score는 표본규모·모집단 구조상 기본계획에서 제외.

---

# 22. Notebook 및 산출물 설계

권장 구조:

```text
research/landing_accessibility/analysis/
├── README.md
├── config/
│   └── analysis_freeze.yaml
├── notebooks/
│   ├── 00_frame_provenance_audit.ipynb
│   ├── 01_source_structure_eda.ipynb
│   ├── 02_web_target_eda.ipynb
│   ├── 03_certification_reach_eda.ipynb
│   ├── 04_evidence_completeness_eda.ipynb
│   ├── 05_service_accessibility_eda.ipynb
│   ├── 06_criterion_barrier_eda.ipynb
│   ├── 07_adaptive_control_eda.ipynb
│   ├── 08_source_heterogeneity.ipynb
│   ├── 09_certification_contrast.ipynb
│   ├── 10_robustness_sensitivity.ipynb
│   └── 11_publication_case_selection.ipynb
├── marts/
│   ├── mart_web_target.parquet
│   ├── mart_service_criterion.parquet
│   ├── mart_service_summary.parquet
│   ├── mart_panel_service.parquet
│   └── mart_adaptive_control.parquet
├── outputs/
│   ├── tables/
│   ├── figures/
│   └── qa/
└── registry/
    ├── analysis_manifest.json
    └── publication_claim_registry.csv
```

---

# 23. 분석 Freeze Manifest

E001 이전:

```text
TARGET_FRAME_SHA
PROTOCOL_SHA
COLLECTOR_SHA
PROBE_SHA
CODEBOOK_SHA
```

E001 이후:

```text
EVIDENCE_RUN_ID
EVIDENCE_MANIFEST_SHA
```

판정 이후:

```text
JUDGMENT_RUN_ID
JUDGMENT_RULE_SHA
HUMAN_REVIEW_FREEZE_SHA
```

분석 실행마다:

```text
ANALYSIS_RUN_ID
INPUT_MART_SHA
NOTEBOOK_SHA
OUTPUT_TABLE_SHA
OUTPUT_FIGURE_SHA
```

같은 데이터로 threshold만 바뀌면 Evidence를 다시 수집하지 않고 Judgment version을 분리함.

---

# 24. Publication Claim Registry

최종 기사·보고서의 모든 주요 문장은 다음 구조로 추적함.

| claim_id | claim_text | status | metric | numerator | denominator | source_artifact | analysis_run | limitation |
|---|---|---|---|---:|---:|---|---|---|

허용 status:

- `SUPPORTED`
- `CONDITIONAL`
- `NOT_SUPPORTED`
- `BLOCKED`

기사 문장이 수치보다 먼저 정해져 분석결과를 끌어맞추는 것을 금지함.

---

# 25. 최종 주요 시각화 후보

## Figure 1. Source-to-Measurement Funnel

`261 source rows → 81 entities → 68 target groups → web eligible → certified current`

## Figure 2. Certification Reach

웹 관측 가능 실사용 서비스 중 현재 유효 인증의 도달 범위.

## Figure 3. Criterion Barrier Ranking

criterion별 confirmed fail share + applicable N + undetermined share.

## Figure 4. Service × Criterion Heatmap

서비스별 PASS/FAIL/UNDET/NA.

## Figure 5. Accessibility Burden vs Evidence Coverage

x = decision coverage  
y = confirmed fail rate

## Figure 6. Adaptive Control Landscape

적응기능 유형·발견가능성·활성화 성공률.

## Figure 7. Certified vs Non-certified [conditional]

feasibility가 충족될 때만 사용.

---

# 26. 해석 금지사항

다음 표현은 본 데이터만으로 사용하지 않음.

- “인증이 접근성을 개선했다.”
- “미인증이라 접근성이 나쁘다.”
- “고령자는 이 페이지를 사용할 수 없다.”
- “이 서비스는 KWCAG 전체를 위반한다.”
- “이 결과가 65세 이상 전체 인구의 평균이다.”
- “Wiseapp raw value가 높은 서비스일수록 접근성이 나쁘다/좋다.” — 별도 적절한 분석 없이 금지
- “웹 랜딩에서 문제가 없으므로 실제 결제·예약과업도 접근 가능하다.”
- “UNDETERMINED는 PASS다.”
- “ACCESS_BLOCKED는 접근성 FAIL이다.”

허용되는 서술은 관측범위에 한정함.

예:

- “감사일 기준 해당 랜딩의 정적 관측에서 criterion X의 confirmed fail이 확인됨.”
- “동결된 Wiseapp 기반 웹 대상 frame 중 현재 유효 인증이 확인된 비율은 X/Y임.”
- “criterion X는 적용 가능했던 서비스 중 confirmed fail이 상대적으로 자주 관측됨.”

---

# 27. 현재 State와 다음 Gate

## 현재 권위 있는 상태

- Population Authority: FROZEN
- Source rows: VERIFIED
- Entity / membership: VERIFIED
- Web target structure: VERIFIED PRE-URL
- Certification registry snapshot: COMPLETE
- Web eligibility: PENDING
- Official landing URL: PENDING
- Certification join: PENDING
- Feasibility: PENDING RECOMPUTE
- Measurement Engine: PENDING
- E000: PENDING
- E001: NOT STARTED

현재 authoritative baseline은 promoted Main SHA를 기준으로 함. 작업 중인 미승격 executor 산출물은 본 SSOT의 확정 데이터로 사용하지 않음.

---

# 28. 실행 순서

```text
[1] Web Eligibility 확정
        ↓
[2] Official Landing URL 확정
        ↓
[3] Web Target Frame Freeze
        ↓
[4] Certification Join
        ↓
[5] Certification Reach + Feasibility
        ↓
[6] Measurement Engine / Criterion Probe Freeze
        ↓
[7] E000 Smoke
        ↓
[8] READY_FOR_E001
        ↓
Research Director GO
        ↓
[9] E001 Evidence Collection
        ↓
[10] J001 Machine Judgment
        ↓
[11] Human Review
        ↓
[12] Final Judgment Freeze
        ↓
[13] EDA-04 ~ EDA-10
        ↓
[14] Publication Claim Registry
        ↓
[15] Article Tables / Figures / Case Reconstruction
```

---

# 29. READY_FOR_E001 정의

다음이 전부 충족되는 순간 수집 직전 준비 완료로 판정함.

```text
Population Authority        PASS
Source Provenance           PASS
Target Frame                PASS
Official URL                PASS
Certification Join          PASS
Feasibility                 PASS
Protocol Freeze             PASS
Collector Integrity         PASS
Evidence Identity           PASS
Append-only                 PASS
Judgment Semantics          PASS
Automation Split            PASS
Criterion Probe Coverage    PASS
E000                        PASS
Adversarial Audit           PASS
SSOT Audit                  PASS
Open P0                     0
Open E001-blocking P1       0
Open E001-blocking P2       0

FULL COLLECTION             NOT STARTED
```

해당 상태에서 자동화는 정지하며 E001은 Research Director의 명시적 GO 이후에만 실행함.

---

# 30. 최종 분석 원칙

1. **Source와 Outcome 분리**  
   Wiseapp는 서비스 사용 맥락, KWCAG 관측은 접근성 outcome을 담당함.

2. **Entity와 Web Target 분리**  
   원자료 의미를 보존하면서 실제 측정 중복을 제거함.

3. **인증은 Attribute**  
   인증 여부가 모집단을 정의하지 않음.

4. **Service Equal Weighting 우선**  
   전체 접근성 결과에서 unique web target 하나를 한 표로 취급함.

5. **원천 패널 보존**  
   임의 재분류보다 Wiseapp의 panel/domain/axis를 우선함.

6. **PASS와 Unknown 분리**  
   미관측·불확정은 접근성 충족의 증거가 아님.

7. **Evidence와 Judgment 분리**  
   raw feature를 먼저 보존하고 판정규칙은 versioning함.

8. **통계보다 계보 우선**  
   분모·대상·증거가 명확하지 않은 수치는 산출하지 않음.

9. **조건부 비교**  
   인증 O/X 비교가 성립하지 않아도 전체 연구는 성립함.

10. **인과표현 금지**  
    본 연구는 frozen service frame의 접근성 상태와 인증 도달범위에 대한 관측 연구임.
