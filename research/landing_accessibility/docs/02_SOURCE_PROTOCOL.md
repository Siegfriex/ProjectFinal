# 02 — Source Layer 규약

**원칙** 모든 파생자료는 authority source 까지 역추적 가능해야 한다.
`이 파일이 존재한다` 가 아니라 **`왜 이 파일이 존재하며 어떤 권위자료에서 파생됐는지`** 가 추적돼야 한다.

---

## 1. 계보

```
A1  Wiseapp Insight 933 원문
      │  POST /insight/detail/getDetail.json {"insightNid":"933","preview":0}
      │  playwright chromium render
      ▼
    sources/wiseapp/raw/          원문 스냅샷 4종 + CDN figure 11종
      │  figure 판독 (독립 판독 + 적대적 재확인)
      ▼
    state/panel_registry          17 패널   ← 원문 4 chapter / 11 section 과 1:1
    state/source_ranking_rows     261 행    ← 삭제·수정 금지
      │  canonicalization
      ▼
    state/entity_alias_map        81 별칭
    state/service_master          measurement entity
    state/source_membership       (entity × panel) 다대다
      │
      ▼
    state/web_target_group        수집 단위 — measurement entity 와 별개 축

A2  KWACC 인증목록 (KWACC_WA_20260826)
      │  230 페이지 전수, 완결성 게이트 통과
      ▼
    sources/certification/certification_registry   2,283 행
      │  join (도메인만으로 판정하지 않음)
      ▼
    state/certification_match     certified_current ∈ {0,1}
```

---

## 2. 불변 규칙

### 2-1. 원자료 행은 삭제하지 않는다

`source_ranking_rows` 261행은 어떤 단계에서도 줄거나 늘지 않는다.
한 서비스가 여러 패널·순위에 등장하면 **여러 행이 그대로 남고**, 웹 수집만 서비스 기준 1회다.

Pilot 은 같은 서비스의 여러 랭킹 행을 `evidence_rows` 배열로 묶었다.
서비스 식별에는 편했지만 패널 분석에서 원자료 행의 역할이 흐려졌다.

### 2-2. 원문 표기를 임의로 합치지 않는다

| 원문 표기 | 처리 |
|---|---|
| `네이버` (APP) vs `네이버/네이버페이` (RETAIL) | 별개 measurement entity. 같은 회사라도 다른 측정 대상 |
| `G마켓` (APP) vs `G마켓/옥션` (RETAIL) | 별개 |
| `현대홈쇼핑/현대Hmall` vs `현대홈쇼핑/현대Hmallord` | 발행물 오타로 확인 → canonical 에서만 흡수, 원자료 무수정 |
| 슬래시 묶음 (`파리바게뜨/파리크라상` 등) | **분해하지 않는다.** 원문 단위가 측정 단위다 |

합칠 근거가 애매하면 `needs_human_review=true` 로 두고 분리를 유지한다.
**애매함을 분석값으로 굳히지 않는다.**

### 2-3. 측정 단위와 수집 단위를 분리한다

```
measurement_entity   원문 패널의 측정 대상.
                     APP 지표(사용자·사용시간)와 RETAIL 지표(카드 결제추정금액)는
                     서로 다른 것을 재므로 같은 브랜드라도 별개다. 쿠팡도 예외가 아니다.

web_target           실제 방문할 랜딩 URL.
                     여러 measurement_entity 가 같은 web_target 을 가리킬 수 있고,
                     그 경우 관측은 정확히 1회만 수행한다.
```

**금지** — measurement_entity 축에서 APP 지표와 RETAIL 지표를 합산·평균하지 않는다.
`source_row_count` 를 도메인 교차로 합산하지 않는다.

### 2-4. APP / RETAIL 은 원자료 단계에서 섞지 않는다

발행처가 앱시장 데이터와 리테일 브랜드 데이터를 서로 다른 추정 데이터 유형으로 제공한다.
`bapp=1`, `bretail=1` 이 원문 메타에 별도 플래그로 있다.

`domain` 축과 `axis_type` 축을 **별도 컬럼**으로 유지한다.
한 컬럼에 섞으면 `== 'RETAIL_BRAND'` 같은 필터가 리테일 1위 쿠팡을 조용히 누락시킨다.

### 2-5. 연구자 임의 분류를 Source Layer 에 두지 않는다

폐기 대상: `BUY_RESERVE` · `TRANSFER_ENTRY` · `COMMUNITY_PARTICIPATION` · `PUBLIC` ·
`MOBILITY_MAP` · `CULTURE_EDU` · `HEALTH_WELFARE` · `OTHER_UTILITY` · `SEARCH_INFO` ·
`CLASSIFY_RULES` · `TYPE_MAP` · `TASK_ENTRY`

Source Layer 는 **원문이 준 구조만** 담는다.

```
Source Panel → Raw Ranking Row → Canonical Entity → Source Membership
```

Pilot 의 `classify()` 는 서비스명과 기관명을 한 문자열로 합쳐 부분문자열 정규식을 순서대로 적용했다.
결과적으로 226건 중 49건이 기관명 때문에 코드가 결정됐고, `공주문화관광재단` 의 `공주문화` 에서
`주문` 이 매칭돼 `백제문화전당` 이 BUY 로 분류됐다.

---

## 3. 원문에서 확정된 조작적 정의

파생자료에 없던 것들이다. **모집단 정의를 방어하려면 반드시 필요하다.**

| 항목 | 원문 문구 |
|---|---|
| 코호트 | 액티브시니어+ 세대 = **50대 이상** |
| 측정기간 | 25년 7월부터 12월까지 월간 평균 |
| 비교기준 | 전년 동기간 (단, fig07 은 **전년 동월**) |
| APP 모집단 | `한국인 Android+iOS 스마트폰 사용자 추정` (본문 5회) |
| RETAIL 모집단 | `계좌이체, 현금거래, 상품권으로 결제한 금액은 포함되지 않음` (본문 6회) |
| 점유율 모수 | 월간 사용자 평균 200만 명 이상인 앱 |
| 성장률 모수 | 200만 명 이상 AND 시니어 비율 25% 이상 |
| 결제 성장률 모수 | 순 결제추정금액 5천억 원 이상 AND 비율 30% 이상 |

**RETAIL 지표가 카드 결제 표본이라는 사실이 연구 한계의 핵심이다.**
현금·계좌이체 비중이 높은 고령 세그먼트가 구조적으로 과소집계된다 — 이 연구가 겨냥하는 바로 그 집단이다.
기사 인용 시 반드시 병기한다.

---

## 4. A7 — 기존 xlsx 의 지위

`50plus_all_rankings_real_url_mapping.xlsx` 는 **933 의 파생자료가 아니다.**
서로 다른 패널 집합이며, 대조 기준으로도 쓸 수 없다.

| 근거 | 내용 |
|---|---|
| 항목 부재 | 원문 rank3 = Google 1,278만 — xlsx 에 없음. xlsx rank3 = 네이버 1224만 |
| 드리프트 비일관 | 카카오톡 −0.15% / 유튜브 −1.8% / 네이버 −2.5% |
| 패널 미중첩 | 원문 다음 54.1%(1위) vs xlsx 다음 38.7%(5위) |
| 서수 역전 | 원문 농협하나로마트#3·이마트#4 vs xlsx 이마트#3·농협하나로마트#6 |
| 깊이 양방향 불일치 | 원문 Ch1(1) TOP15 vs xlsx Top10 / 원문 Ch3(1) TOP15 vs xlsx Top20 |
| provenance 전무 | `creator=openpyxl`, 문서속성 전부 None, `insight/detail/<id>` 참조 0건 |

**금지** — 셀 단위 패치(`1379 → 1377`)로 두 패널을 융합하는 것.
모집단·대조·보정 어느 용도로도 사용하지 않는다. 파일은 `state/_invalidated/` 에 보존한다.

---

## 5. A2 인증 결합 규칙

인증목록은 **모집단이 아니라 lookup** 이다.

```
certified_current = 1  ⟺  valid_on_audit_date
                        AND certification_target_scope_match
                        AND service_identity_match
```

### 5-1. 등록도메인 일치만으로 1 을 부여하지 않는다

Pilot 에서 실제로 발생한 오탐:

```
삼성월렛 → samsung.com → 매칭된 인증 대상: "삼성전자승마단"
```

서비스 정체성 확인 없이 도메인만 보면 이런 결합이 통과한다.

### 5-2. 목록의 상태 플래그를 그대로 신뢰하지 않는다

A2 스냅샷에서 실제로 확인된 사례:

```
인증번호 2521 국립망향의동산
  목록 상태 = VALID
  인증기간  = 2026-08-27 ~ 2027-08-26   ← 감사일(2026-08-26) 다음 날 시작
  → cert_valid_candidate = 0
```

VALID 227 과 감사일 유효 226 의 차이가 정확히 이 1건이다.
**`in_period_at_audit` 를 독립적으로 계산해 측정 레코드에 보존한다.**

### 5-3. 완결성 게이트

`목록에 없음 = 인증 0` 은 스냅샷이 정상 종료됐을 때만 허용된다.

```
COMPLETE   : NO_CARDS_AT_DECLARED_END
INCOMPLETE : TRANSPORT_OR_STATUS / EARLY_PAGE_TERMINATION / RAW_SNAPSHOT_MISSING /
             DUPLICATE_PAGE / DECLARED_LAST_PAGE_EXCEEDED / UNKNOWN_LAST_PAGE / MAX_PAGES_EXHAUSTED
```

`valid_at_audit_rows()` 가 INCOMPLETE 매니페스트에서 `IncompleteSnapshotError` 를 던져
코드 수준에서 차단한다.

### 5-4. 레지스트리 원문 결함 — 하류가 처리해야 함

| 결함 | 건수 | 처리 |
|---|---:|---|
| 대상 URL 링크 부재 | 4 | 전부 EXPIRED. UNRESOLVED |
| 스킴 없는 href | 26 | 원문 보존, 정규화 시 스킴 보충 |
| **URL 자리에 텍스트** | 3 | `보건복지부 홈페이지`(27) · `국립중앙도서관 홈페이지`(25) · `-`(1812) → **UNRESOLVED**. URL 로 파싱하면 조용히 실패한다 |
| 인증기간 공란 | 1 | 1812번, service_name 도 `-` |

---

## 6. 독립성 주장의 범위

A2 스냅샷 230페이지의 sha256 이 Pilot 수집분과 전건 동일했다. 이것으로 주장할 수 있는 것과 없는 것을 구분한다.

```
주장 가능   수집 절차의 독립성 — 자체 요청·자체 원문·자체 매니페스트, Pilot 산출물 미사용
주장 금지   내용의 독립 검증 — 같은 서버 응답을 두 번 받은 것이며,
                              서버가 틀리면 두 스냅샷이 같은 방식으로 틀린다
```

---

## 7. A1 동결 유효창

발행처가 **2026-08-25 09:00** 에 `[와이즈앱] 모집단 변경 사전 안내`(nid=127, 종료일 없음)를 게시했다.
원문 취득은 그 다음 날이다.

→ 동결본을 **"2026-08-26 시점에 게시돼 있던 933 판본"** 으로 한정한다.
발행처 모집단 변경 이후 수치와 혼용하지 않는다.
