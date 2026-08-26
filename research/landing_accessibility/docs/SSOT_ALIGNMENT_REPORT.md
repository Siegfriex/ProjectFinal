# 분석 SSOT v1.0 대조 — 현황 보고

**대상 문서** `docs/ProjectFinal_Landing_Accessibility_Data_Analysis_SSOT_v1.0.md` (1,382행 / 30개 절)
**대조 기준** `research/landing-accessibility-main @ 5a9015d1e95b15304aaf53a73efb475934610b82` (PROM-002)
**작성** 2026-08-26 · 오케스트레이터 · automation HALTED 상태에서 작성

---

## 0. 결론 먼저

**분석 SSOT 문서와 현재 파이프라인 상태가 완전히 일치한다. drift 0건이다.**

SSOT §27이 선언한 12개 상태를 승격 artifact에서 재계산해 전건 대조했고 불일치가 없었다.
따라서 이 문서는 **현재 검증된 것 위에 세워진 분석 계약**이며, 새로 맞춰야 할 것이 없다.

다만 **분석을 시작할 수 있는 것과 없는 것이 명확히 갈린다** — §3에 정리했다.

---

## 1. SSOT §27 선언 vs 승격 artifact 실측

`scripts/materialize_state.py` 로 promoted SHA 트리에서 직접 계산한 값이다.

| SSOT §27 선언 | 실측 | 판정 |
|---|---|---|
| Population Authority: FROZEN | Wiseapp 933, raw 6종 sha256 불변 | **일치** |
| Source rows: VERIFIED | **261행** / 고유 id 261 / APP 137 · RETAIL 124 | **일치** |
| Entity / membership: VERIFIED | entity **81** / alias **82** / membership **142** | **일치** |
| Web target structure: VERIFIED PRE-URL | group **68**, `web_target_url` **전 행 null** | **일치** |
| Certification snapshot: COMPLETE | `KWACC_WA_20260826` 2,283행 / 감사일 유효 226 | **일치** |
| Web eligibility: PENDING | `NOT_ASSESSED 71` / `EXCLUDED_INDUSTRY_AXIS 10` | **일치** |
| Official landing URL: PENDING | 미승격 (C013 중단) | **일치** |
| Certification join: PENDING | `certified_current` 미산출 | **일치** |
| Feasibility: PENDING RECOMPUTE | 이전 결과 `INVALIDATED_BY_SOURCE_MISMATCH` 보존 | **일치** |
| Measurement Engine: PENDING | 전 항목 NOT_RUN | **일치** |
| E000: PENDING | 미실행 | **일치** |
| E001: NOT STARTED | `evidence/` 부재 (4개 워크트리 전수 확인) | **일치** |

패널 축도 일치한다 — `SERVICE_BRAND 16 / INDUSTRY_CATEGORY 1`, entity 축 `SERVICE_BRAND 71 / INDUSTRY_CATEGORY 10`.

> SSOT가 *"작업 중인 미승격 executor 산출물은 확정 데이터로 사용하지 않음"* 이라 못박은 규칙과
> 현재 운영이 일치한다. C013의 미커밋 21파일은 어떤 수치에도 반영하지 않았다.

---

## 2. SSOT §28 실행 순서 vs v4.0 Bundle 매핑

두 체계가 충돌하지 않는다. 정확히 겹친다.

| SSOT §28 | v4.0 Bundle | 상태 |
|---|---|---|
| [1] Web Eligibility 확정 | **A** TARGET FRAME | **진행 중 — C013 세션 한도로 중단** |
| [2] Official Landing URL 확정 | A | 미완 (산출물 미커밋) |
| [3] Web Target Frame Freeze | A | 미착수 |
| [4] Certification Join | **B** | 미착수 |
| [5] Certification Reach + Feasibility | B | 미착수 |
| [6] Measurement Engine / Probe Freeze | **C** | 미착수 |
| [7] E000 Smoke | **D** | 미착수 |
| [8] READY_FOR_E001 | D | **정지점** |
| [9]~[15] E001 이후 | — | GO 이후 |

**현재 위치는 [1]과 [2] 사이다.**

---

## 3. EDA 12모듈 — 지금 할 수 있는 것과 없는 것

SSOT §9가 EDA를 데이터 생성 단계에 맞춰 분리했다. 그 경계를 현재 상태에 대면 이렇게 갈린다.

```
EDA-00  Frame & Provenance Audit        ← 지금 실행 가능
EDA-01  Wiseapp Source Structure        ← 지금 실행 가능
EDA-02  Web Eligibility & Target Frame  ← [1][2] 완료 후
EDA-03  Certification Reach             ← [4][5] 완료 후
──────────── E001 ────────────
EDA-04  Evidence Completeness           ← 수집 후
──────────── JUDGMENT ────────
EDA-05  Service Accessibility Profile   ← 판정 후
EDA-06  Criterion Barrier Profile       ← 판정 후
EDA-07  Adaptive Accessibility Controls ← 판정 후
EDA-08  Source-Panel Heterogeneity      ← 판정 후
EDA-09  Certification Contrast [조건부] ← feasibility 통과 시
EDA-10  Robustness / Sensitivity        ← 판정 후
EDA-11  Case Selection / Publication    ← 최종
```

### 3-1. 즉시 실행 가능 — EDA-00 · EDA-01

**둘 다 승격된 baseline만으로 성립한다.** E001을 기다릴 필요가 없다.

- **EDA-00 Frame & Provenance Audit** — 계보 무결성 검사다. 필요한 입력이 전부 승격돼 있다.
  A1 원문 해시, 261행 provenance, entity/alias/membership 정합, panel 17, 인증 스냅샷 완결성.
  실제로 지금까지 감사관들이 수행한 검증과 상당 부분 겹치며, 그 결과가
  `control/cycles/*.json` 과 `audits/*.json` 에 이미 기계 판독 가능한 형태로 남아 있다.
- **EDA-01 Wiseapp Source Structure** — 원자료 구조 기술이다. 261행 · 17패널 · panel별 rank/value 분포,
  APP/RETAIL 축, TOP-N depth, entity 중복 출현 구조가 전부 확정 상태다.

### 3-2. 차단 — EDA-02 이후

| 모듈 | 차단 사유 |
|---|---|
| EDA-02 | `web_eligibility_status` 71건이 `NOT_ASSESSED`. 판정 자체가 없다 |
| EDA-03 | `certified_current` 미산출. web target에 인증을 붙이려면 URL이 먼저 확정돼야 한다 |
| EDA-04~11 | E001 미실행 · J001 미실행 |

**EDA-09(Certification Contrast)는 조건부다.** SSOT §13이 TIER_A/B/C 판정을 요구하는데,
그 입력인 feasibility가 아직 재산출 전이다. 이전 48-service 기준 결과는 `INVALIDATED` 로 보존돼 있고
분석 근거로 쓰지 않는다.

---

## 4. READY_FOR_E001 (§29) 18항목 대비

| 항목 | 상태 | 근거 |
|---|---|---|
| Population Authority | **PASS** | A1 raw 6종 sha256 불변, manifest revision 추적 |
| Source Provenance | **PASS** | 261행, 저널 재생성 스크립트 커밋, 두 경로 멱등 확인 |
| Target Frame | PENDING | web eligibility 미판정 |
| Official URL | PENDING | C013 중단 |
| Certification Join | PENDING | — |
| Feasibility | PENDING | 재산출 전 |
| Protocol Freeze | PARTIAL | `docs/03_MEASUREMENT_PROTOCOL.md` 존재, SHA 동결 미실시 |
| Collector Integrity | NOT_RUN | Bundle C |
| Evidence Identity | NOT_RUN | Bundle C |
| Append-only | PARTIAL | evidence manifest 계약 확립, 실행 경로 강제는 Bundle C |
| Judgment Semantics | NOT_RUN | Bundle C |
| Automation Split | NOT_RUN | Bundle C |
| Criterion Probe Coverage | NOT_RUN | Bundle C |
| E000 | NOT_RUN | Bundle D |
| Adversarial Audit | **PASS** (C012까지) | `510d5f21` |
| SSOT Audit | **PASS** (C012까지) | `1bc2c71b` |
| Open P0 | **0** | — |
| Open E001-blocking P1 | **0** | — |
| Open E001-blocking P2 | **6** | C013 처리중 4 + Bundle C 2 |

**PASS 5 / PARTIAL 2 / PENDING 4 / NOT_RUN 6 / 미충족 1.**

---

## 5. SSOT가 요구하는 것 중 아직 구조가 없는 것

문서를 읽고 확인한 결과, 다음은 **개념은 정의됐으나 산출물이 없다.**

| SSOT 절 | 요구 | 현재 |
|---|---|---|
| §5.2 | `dim_panel` `fact_source_ranking` `dim_measurement_entity` `bridge_source_membership` `dim_web_target` `dim_certification` `fact_observation` `fact_criterion_result` `fact_adaptive_control` | 앞의 4개는 현 parquet에 사실상 존재하나 **이름과 스키마가 SSOT 명세와 다르다.** 뒤의 3개는 E001/J001 산출물이라 부재 |
| §6.1 | Panel-normalized rank, Panel appearance count | 미산출 — EDA-01에서 만들 수 있다 |
| §6.4 | 서비스 수준 accessibility burden | 판정 후 |
| §6.5 | Criterion 수준 prevalence | 판정 후 |
| §23 | 분석 Freeze Manifest | 미작성 |
| §24 | Publication Claim Registry | 미작성 |

**§5.2 테이블 명세 정합은 지금 결정해야 할 사항이다.** 현재 `state/*.parquet` 을 SSOT 명세 이름으로
재편할지, 아니면 매핑 레이어를 둘지가 갈린다. 데이터를 다시 만들 필요는 없다 — 뷰 또는 리네임 수준이다.

---

## 6. 정지 시점의 미결 사항

| # | 항목 | 성격 |
|---|---|---|
| 1 | **C013 재개** | executor 세션 한도 (15:40 리셋). 미커밋 21파일 보존됨. baseline 무오염 |
| 2 | **§5.2 분석 테이블 명세 정합** | 리네임 vs 매핑 레이어 결정 |
| 3 | **Protocol SHA 동결** | 문서는 있으나 `PROTOCOL_SHA` 미산출 |
| 4 | Pilot 원증거 물리 이중화 | 논리 이중화만 확보 (`/mnt/c`). 외장/원격 위치 미지정 |
| 5 | Wiseapp 조사 상세 | 표본 크기·조사 방법 전체 기술이 원문에 없음 |
| 6 | 발행처 모집단 변경 공지 | 2026-08-25 게시, 변경 내용 자체는 미확인 |

---

## 7. 지금 할 수 있는 것 — 권고

automation은 정지 상태다. 재개한다면 두 갈래가 병렬 가능하다.

**갈래 A — Critical Path 재개**
`C013 이어서 실행 → 독립감사 2건 → 재결 → PROM-003` 로 Bundle A를 닫는다.
이후 B → C → D 순으로 `READY_FOR_E001` 까지 간다.

**갈래 B — EDA-00 / EDA-01 선행**
승격 baseline만으로 실행 가능하고 Critical Path와 충돌하지 않는다.
`§6.1` 파생지표(panel-normalized rank, appearance count)와 `§5.2` 테이블 정합을 여기서 해결하면,
Bundle B의 feasibility 산출이 훨씬 빨라진다.

둘은 **입력이 겹치지 않는다** — 갈래 A는 `web_eligibility`/`url_review` 를 쓰고,
갈래 B는 이미 동결된 `source_ranking_rows`/`panel_registry` 만 쓴다.
다만 v4.0 §4의 `MAX_UNAUDITED_EXEC_CYCLES = 1` 때문에 **state-changing 커밋은 한 번에 하나**여야 한다.

---

## 8. 이 보고가 확인한 것

- 분석 SSOT v1.0은 **현재 검증된 것 위에 정확히 세워져 있다.** 조정할 drift가 없다.
- SSOT §28 실행순서와 v4.0 Bundle이 충돌 없이 매핑된다.
- **EDA 12모듈 중 2개(EDA-00, EDA-01)는 지금 실행 가능하다.** 나머지 10개는 [1]~[7] 또는 E001/J001에 걸려 있다.
- `READY_FOR_E001` 18항목 중 5개가 PASS다.
- E001은 여전히 `NOT STARTED / PROHIBITED`. `evidence/` 는 4개 워크트리 전수에서 부재를 확인했다.
