# 06 — Web Eligibility · URL Review · Certification Join 규약

**상태** 다음 3개 게이트의 SSOT. executor 는 이 문서를 따른다.
**전제** measurement_entity 81 / web_target_group 68 이 확정된 상태에서 시작한다.

---

## 1. 판정 순서와 의존

```
web_eligibility   entity 가 웹으로 관측 가능한 대상인가
      ↓
url_review        관측 가능하다면 어느 URL 인가
      ↓
web_target_group  같은 URL 을 가리키는 entity 들을 묶는다 (여기서 CONFIRMED 로 승격)
      ↓
certification_join  각 web target 에 인증 0/1 을 붙인다
      ↓
feasibility       패널·카테고리별 인증 0/1 분포를 재산출한다
```

**앞 단계가 확정되기 전에 뒤 단계 값을 채우지 않는다.**
현재 `web_target_group` 68건이 전부 `*_PENDING_URL_REVIEW` 이고 `web_target_url` 이 null 인 것은 이 규칙을 지킨 상태다.

---

## 2. web_eligibility 판정

### 2-1. 상태값

```
NOT_ASSESSED             초기값. 아직 판정하지 않음
WEB_SERVICE              사용자가 실제 기능에 진입하는 공식 웹서비스 랜딩이 존재
OFFICIAL_PRODUCT_PAGE    앱/서비스 소개·마케팅 페이지만 존재
APP_ONLY                 실질적 웹서비스 랜딩 없음
SYSTEM_APP               단말 선탑재·OS 구성요소. 공개 웹 랜딩 개념이 성립하지 않음
RETAIL_OFFLINE_ONLY      오프라인 결제 브랜드로 웹 랜딩이 측정 대상과 무관
EXCLUDED_INDUSTRY_AXIS   업종 카테고리. 서비스가 아니므로 대상 아님 (확정)
UNRESOLVED               공식 URL 미확정
```

**주 분석은 `WEB_SERVICE` 만 사용한다.**

### 2-2. 판정 근거 요건

각 entity 에 대해 다음을 기록한다. 근거 없는 상태 부여를 금지한다.

```
web_eligibility_status
eligibility_basis        무엇을 보고 판정했는가 (실제 확인한 URL·페이지 제목·리다이렉트 결과)
eligibility_reviewer     자동 규칙명 또는 사람
eligibility_confidence   HIGH | MEDIUM | LOW
needs_human_review       bool
```

### 2-3. `SYSTEM_APP_CANDIDATE` 11건 처리

현재 `삼성 계산기`·`내 파일`·`디바이스 케어`·`삼성 노트`·`삼성 월렛`·`삼성 인터넷 브라우저`·
`Chrome`·`Google`·`Google 포토`·`에이닷 전화`·`V3 Mobile Plus` 가 후보로 표시돼 있다.

**이것은 확정이 아니다.** 판정 근거가 원문에 없고 상식 판단이기 때문이다.
`SYSTEM_APP` 으로 확정하려면 다음 중 하나가 필요하다.

- 해당 앱에 공식 웹 랜딩이 존재하지 않음을 실제 확인
- 존재하지만 `OFFICIAL_PRODUCT_PAGE` 임을 확인

**선탑재 여부 자체는 판정 근거가 아니다.** 제조사·통신사·출고시기에 따라 다르고, 원문이 그 정보를 주지 않는다.
확인 불가면 `UNRESOLVED` 로 두고 `needs_human_review=true` 를 붙인다.

**확인 불가를 제외로 바꾸지 않는다.** Pilot 이 NA 와 UNDETERMINED 를 뭉갠 것과 같은 실수다.

---

## 3. url_review 판정

### 3-1. 원칙

**서비스 하나에 URL 하나를 배정하되, 그 URL 이 왜 공식인지 근거를 남긴다.**

```
official_landing_url
url_type                 WEB_SERVICE_LANDING | OFFICIAL_PRODUCT_PAGE | APP_ONLY | UNRESOLVED
url_discovery_method     어떻게 찾았는가
url_evidence             확인한 근거 (공식 도메인 표기·앱스토어 링크·사업자 정보 등)
url_reviewer
url_confidence
```

### 3-2. 금지

- **추측으로 URL 을 만들지 않는다.** `<브랜드>.co.kr` 식 패턴 생성 금지.
- **검색 결과 1위를 자동 채택하지 않는다.** 근거를 남길 수 없으면 `UNRESOLVED` 다.
- Pilot 의 `TASK_ENTRY` 처럼 관측하지 않은 것을 관측했다고 기록하지 않는다.

### 3-3. redirect

`target_url` · `final_url` · `redirect_chain` 을 전부 보존한다.
등록도메인 비교는 **Public Suffix List 파서**로 한다 — 마지막 두 라벨 문자열 비교는 금지다
(`.co.kr` / `.or.kr` / `.go.kr` 에서 무관한 사이트를 같은 도메인으로 오판한다).

외부 파트너 도메인으로 최종 이동하면 자동으로 같은 서비스라 가정하지 않고 **QA 큐**로 보낸다.

### 3-4. web_target_group 승격

URL 이 확정된 뒤에만 그룹을 `CONFIRMED` 로 올린다.

```
CANDIDATE_PENDING_URL_REVIEW  →  URL 확정 후 실제로 같은 URL 이면  →  CONFIRMED_SHARED_TARGET
                              →  다른 URL 로 밝혀지면              →  SPLIT (그룹 해체)
```

현재 후보 3건(`coupang_app`+`coupang_retail`, `naver_app`+`naver_naverpay`, `gmarket_app`+`gmarket_auction`)은
**이름 유사성만으로 묶인 것이며 URL 증거가 없다.** 셋 다 해체될 수 있다.

---

## 4. certification_join 판정

### 4-1. 결합 조건 — 세 가지를 모두 만족해야 1

```
certified_current = 1  ⟺  valid_on_audit_date
                        AND certification_target_scope_match
                        AND service_identity_match
```

| 조건 | 의미 | 검증 방법 |
|---|---|---|
| `valid_on_audit_date` | 감사일이 인증기간 안 | **목록의 VALID 플래그를 믿지 않고 날짜를 직접 계산** |
| `certification_target_scope_match` | 인증 대상 URL 이 우리 랜딩과 같은 범위 | PSL 등록도메인 + 경로 비교 |
| `service_identity_match` | 인증받은 서비스가 우리 서비스와 동일 | 서비스명·기관명 대조, 사람 확인 |

### 4-2. 등록도메인 일치만으로 1 을 주지 않는다

Pilot 실측 오탐:

```
삼성월렛 → samsung.com → 매칭된 인증 대상: "삼성전자승마단"
```

`service_identity_match` 없이 도메인만 보면 통과한다.

### 4-3. 목록 상태 플래그를 신뢰하지 않는다

A2 스냅샷 실측:

```
인증번호 2521 국립망향의동산
  목록 상태 = VALID
  인증기간  = 2026-08-27 ~ 2027-08-26   ← 감사일(2026-08-26) 다음 날 시작
  → cert_valid_candidate = 0
```

**VALID 227 과 감사일 유효 226 의 차이가 정확히 이 1건이다.**

### 4-4. 0 을 확정하기 위한 선행조건

`목록에 없음 = 인증 0` 은 스냅샷이 `COMPLETE` 일 때만 허용된다.
`KWACC_WA_20260826` 은 `NO_CARDS_AT_DECLARED_END` 로 정상 종료돼 `COMPLETE` 다.
`valid_at_audit_rows()` 가 INCOMPLETE 매니페스트에서 예외를 던져 코드로 차단한다.

### 4-5. 레지스트리 원문 결함 처리

| 결함 | 건수 | 처리 |
|---|---:|---|
| 대상 URL 링크 부재 | 4 | 전부 EXPIRED. join 대상 아님 |
| 스킴 없는 href | 26 | `https://` 보충 후 정규화. 보충 사실을 기록 |
| **URL 자리에 텍스트** | 3 | `보건복지부 홈페이지`(27) · `국립중앙도서관 홈페이지`(25) · `-`(1812) → **UNRESOLVED**. URL 파싱을 시도하면 조용히 실패한다 |
| 인증기간 공란 | 1 | 1812번. `valid_on_audit_date` 판정 불가 → 후보에서 제외하되 기록 |

### 4-6. 애매함을 분석값으로 굳히지 않는다

최종 분석 테이블에는 `certified_current ∈ {0,1}` 만 남는다.
그러나 **매칭 과정에는 QA 상태를 둔다.**

```
cert_match_basis   EXACT_URL | SAME_SERVICE_REVIEWED | NOT_FOUND | AMBIGUOUS_PENDING_REVIEW
certification_number / certified_target_url / cert_start_date / cert_end_date
cert_match_reviewer / cert_match_evidence
```

`AMBIGUOUS_PENDING_REVIEW` 는 **분석 진입 전에 반드시 0 또는 1 로 해소**한다.
해소되지 않은 채로 feasibility 를 산출하지 않는다.

---

## 5. feasibility 재산출

이전 feasibility 는 `INVALIDATED_BY_SOURCE_MISMATCH` 다. A1 기준으로 새로 만든다.

### 5-1. 산출 단위

**패널 단위와 카테고리 단위를 구분한다.** 원문이 준 구조는 패널이고, 카테고리는 없다.
Pilot 의 `primary_task_code` 같은 연구자 임의 분류를 다시 만들지 않는다.

```
panel_id / source_chapter / source_section / domain / axis_type
entity_n / web_service_n / certified_n / noncertified_n / unresolved_n
comparison_tier / reason
```

### 5-2. TIER 경계

```
TIER_A  인증·비인증 양쪽이 충분해 bootstrap 비교 가능
TIER_B  양쪽 존재하나 소표본 → 기술통계·사례 중심
TIER_C  한쪽이 0 또는 1 → 집단 gap 을 주 결과로 제시하지 않음
```

**숫자 경계는 feasibility 결과를 본 뒤 고정하고, 고정 후 사후적으로 유리하게 바꾸지 않는다.**

### 5-3. 이전 NO-GO 판정의 지위

`RQ2_RQ3_RQ4_NO_GO` 는 `WITHDRAWN_PENDING_SOURCE_REFREEZE` 다.
A1 기준 재산출 결과가 같은 결론이면 그때 비로소 근거를 갖는다.
**철회는 "틀렸다"가 아니라 "권위 없는 입력으로 계산됐다"는 뜻이다.**

---

## 6. 이 단계에서 하지 않는 것

- **E001 본수집 금지.** URL 확정을 위해 페이지를 열어보는 것과 측정 수집은 다르다.
  URL 확인 목적의 접속은 허용하되 **DOM/AX/screen/probe 를 저장하지 않는다.**
- 인증목록으로 모집단을 넓히지 않는다. 인증은 attribute 이지 모집단이 아니다.
- 확인 불가를 제외로 바꾸지 않는다.
- 근거 없이 URL 을 생성하지 않는다.
