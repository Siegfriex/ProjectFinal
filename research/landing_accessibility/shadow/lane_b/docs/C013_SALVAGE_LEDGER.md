# C013 SELECTIVE SALVAGE — 파일 단위 원장

```
status                          = SHADOW_PREPARATORY
shadow_lane                     = LANE_B
base_sha                        = d5f1da5652953542d5c8be377026cc3293f2075a
salvage_source                  = agent/landing-exec @ 87a0464e8159d5526069d5e654e648b0dae506ca
salvage_source_status           = UNVERIFIED_WIP · NOT_AUDITED · NOT_PROMOTED
authoritative                   = false
real_target_outcome_used        = false
requires_post_p0_reconciliation = true
```

**전체 merge 를 하지 않았다.** 아래 표의 판정 단위는 파일·함수·상수이며, 각 항목마다
가져온 이유 또는 버린 이유를 적었다. 이 원장 자체가 재감사 대상이다.

---

## 0. 살베지 전에 확인한 것 — C013 의 구조

C013 `build_web_eligibility_and_url_review.py` 는 이름과 달리 **규칙 엔진이 아니다.**
`ELIGIBILITY_DECISIONS` (212–744행) 라는 **71건 하드코딩 판정표**가 있고, 스크립트가
하는 일은 그 손판정을 검증·서식화하는 것이다.

```python
decision = ELIGIBILITY_DECISIONS[ckey]   # 871행
status = decision["status"]              # 872행 — 계산이 아니라 조회다
```

이 사실이 살베지 방침을 결정했다. **관측 메커니즘과 무결성 가드는 재사용 가치가 높고,
판정값 자체는 재사용할 수 없다.**

두 번째 구조적 사실: C013 의 상태 어휘 7값(`WEB_SERVICE` / `OFFICIAL_PRODUCT_PAGE` /
`APP_ONLY` / `SYSTEM_APP` / `RETAIL_OFFLINE_ONLY` / `EXCLUDED_INDUSTRY_AXIS` / `UNRESOLVED`)은
`A2 §1.3` 의 `web_eligibility_status` 6값과 **다른 어휘다.** 문자열 하나도 겹치지 않는다
(`EXCLUDED_INDUSTRY_AXIS` 제외). 따라서 값 매핑이 아니라 재판정이다.

---

## 1. 가져온 것

| 대상 | 원본 | 반입 위치 | 왜 |
|---|---|---|---|
| `registered_domain.py` **전체** | `src/landing_accessibility/registered_domain.py` (93행) | `src/landing_accessibility/registered_domain.py` (그대로) | PSL 파서 기반 등록도메인 판정 + `psl_provenance()` 의 목록 파일 sha256 고정. 측정 깊이(L0/L1)와 무관하며, 이 모듈이 없으면 `www.gmarket.co.kr` 과 `www.auction.co.kr` 이 둘 다 `co.kr` 로 접혀 그룹 가설 검정이 조용히 틀린다. **정확히 이 프로젝트가 검정해야 할 gmarket 가설이 그 버그의 사정권이다.** |
| probe 메커니즘 4종 | `scripts/probe_official_urls.py` — `_decode`(EUC-KR/CP949 폴백) · `_LegacyTLSAdapter`(OpenSSL3 legacy renegotiation) · `_clean_title` · 본문 즉시 폐기(`del body`) | `shadow/lane_b/scripts/probe_official_urls_shadow.py` | 한국 사이트 실측 대응이며 판정 논리가 아니다. charset 폴백이 없으면 제목이 깨진 채 근거로 남고, legacy TLS 없이는 현대카드가 접속 가능한데도 '확인 불가'로 기록된다. |
| 접속 예의 규약 | 같은 파일 — 순차 요청 · `DELAY_SEC=1.2` · 연구목적 명시 UA · 연락처 | 동일 | A2 레지스트리 수집기와 같은 규약을 유지한다. |
| 빌드/네트워크 분리 원칙 | 같은 파일 docstring 23–31행 | 동일 구조 채택 | 네트워크 결과는 재현되지 않으므로 관측을 JSON 으로 동결하고 빌드는 그 JSON 만 읽는다. 멱등성 검사가 성립한다. |
| `confidence_of()` — 관측품질 → HIGH/MEDIUM/LOW | build 스크립트 752–761행 | `build_web_eligibility_shadow.py` | **손으로 올리고 내릴 수 없는** 유도값이라는 설계가 핵심이다. 다만 닫힌집합·assert 가 없던 결함은 반입하면서 고쳤다(§3). |
| `BLOCKED_STATUSES` | 197행 | 동일 | 봇차단 상태코드 목록. 실측 기반. |
| `brand_tokens()` · `title_identifies_brand()` | 764–793행 | `build_web_eligibility_shadow.py` | 브랜드 토큰을 **기계적으로만** 만들고 손으로 별칭을 못 넣게 막은 설계. 별칭을 허용하면 검사가 원하는 답 쪽으로 휜다. |
| `crossed_registered_domain()` | 796–802행 | 동일 | 리다이렉트가 등록도메인을 넘었는지. 그룹 가설 검정의 직접 입력이다. |
| review_reasons 의 **기계/사람 append-only 분리** | 908–927행 | 동일 | 사람은 플래그를 **추가만** 할 수 있고 기계가 올린 플래그를 지울 수 없다. laundering 차단 설계. |
| 관측신뢰도 ↔ 확정신뢰도 **2축 분리** | 886–892행 | 동일 | "페이지를 봤다는 확신"과 "이것이 공식 랜딩이라는 확신"은 다른 축이다. |
| 멱등성 가드 | 836–844행 — 대상 집합을 현재 상태값이 아니라 `axis_type` 에서 뽑는다 | 동일 | 현재 상태를 키로 삼으면 두 번 돌릴 때 대상이 달라진다. |
| **반증된 가설을 지우지 못하게 하는 불변식** | 1119–1137행 | `build_web_eligibility_shadow.py` | 가설 선언과 그 반증 결과가 같은 행에 남아야 한다. 이 프로젝트의 핵심 규율. |
| 후보 URL 풀 (71 entity / 179 URL) | `state/url_review_candidates.json` | `shadow/lane_b/state/c013_candidate_seed_UNVERIFIED.json` — **격리 파일명** | 판정이 아니라 **탐색 결과**다. 각 URL 에 `evidence`·`source` 가 붙어 있고 `discovery_protocol.forbidden` 이 추측 URL 생성·검색 1위 자동채택을 금지한 상태로 만들어졌다. 재사용하되 **가설 입력**으로만 쓰고 판정은 새로 관측해서 내린다. |
| 부재 확인 진술(`absence_check`) 3건 | `ELIGIBILITY_DECISIONS` 의 `device_care` · `my_files` · `samsung_calculator` | 증거 텍스트로 인용 | "삼성 공식 앱 색인을 전수 확인했고 해당 페이지가 없었다" 는 **재검증 가능한 절차 진술**이다. 판정값이 아니라 근거로 인용한다. 선탑재 사실 자체를 근거로 쓰지 않은 점도 그대로 유지한다. |

---

## 2. 버린 것

| 대상 | 원본 | 왜 버렸는가 |
|---|---|---|
| **`ELIGIBILITY_DECISIONS` 71건 판정값** | 212–744행 | (a) 손판정이며 감사받지 않았다. (b) 어휘가 `A2 §1.3` 과 다르다. (c) **약 22건(31%)이 scope 변경만으로 재개방된다** — 아래 §4. 값을 옮기는 것은 감사되지 않은 판정을 세탁하는 일이다. |
| `STATUS_CRITERIA` 7값 rubric | 86–106행 | 어휘 자체가 폐기 대상이다. 그리고 문안이 전부 "**그 URL 에** 웹 애플리케이션이 없다" 형태로 **depth-0 시험**을 전제한다. |
| `RETAIL_LANDING_SELECTION_RULE` | 109–115행 | "기업사이트 **또는** 거래사이트 중 하나를 랜딩으로 고른다"는 양자택일 규칙이다. `L0_INITIAL_LANDING + L1_SHALLOW_REPRESENTATIVE_ENTRY` 에서는 기업사이트가 L0, 거래관이 L1 이 될 수 있어 양자택일이 해소된다. 이식이 아니라 재작성 대상. |
| `STATUS_TO_URL_TYPE` · `URL_TYPE_*` 4값 | 118–140행 | `URL_TYPE_WEB_SERVICE_LANDING` 이라는 **이름 자체가 landing-only 를 주장**한다. 게다가 `RETAIL_OFFLINE_ONLY → PRODUCT_PAGE`, `SYSTEM_APP → APP_ONLY` 두 접힘은 서로 다른 사실을 같은 칸에 넣는다. |
| `GROUPING_*` 6값 | 143–159행 | 6번째 값 `SINGLETON_NOT_A_WEB_TARGET` 은 C013 이 지역적으로 만든 값이고, `A2 §1.4` 의 `web_target_status` 5값·`web_target_group.grouping_status` 실측 2값과 어긋난다. |
| 그룹 확정 술어 `all(web_service) and len(distinct) == 1` | 1062행 | **랜딩 URL 문자열 완전일치**만 본다. L0+L1 에서는 두 member 가 L0 는 같고 L1 에서 갈릴 수 있고 그 반대도 가능하다. 양방향 모두 미처리다. 재작성. |
| `ANALYSIS_STATUS = {WEB_SERVICE}` | 82행 | 선언만 되고 파일 어디서도 참조되지 않는 죽은 상수. |
| `url_rows` 28컬럼 스키마 | 948–982행 | entity 당 URL 이 정확히 하나라는 형태(`official_landing_url` 1개 · `observed_url` 1개)여서 L1 진입 URL 을 담을 칸이 없다. 술어 수정이 아니라 스키마 변경이 필요하다. |
| `state/url_review.parquet` · `url_review_ledger.json` 산출물 | C013 state | 위 판정값의 결과물이다. 입력이 폐기 대상이면 산출물도 폐기 대상이다. |
| **C013 이 `state/service_master.parquet` · `web_target_group.parquet` 을 덮어쓴 판본** | C013 state | Pilot READ_ONLY 규율. 그리고 그 판본은 감사받지 않은 판정을 담고 있다. 우리는 base 판본을 읽기 전용으로 쓰고 산출물은 `shadow/lane_b/state/` 아래 **별도 파일**로 만든다. |
| `test_c013_*.py` 2종 | tests/ | 폐기한 어휘·스키마를 검증하는 테스트다. 통과시키려면 폐기 대상을 되살려야 한다. |

---

## 3. 반입하면서 고친 결함

| 결함 | C013 실태 | 조치 |
|---|---|---|
| `url_confidence` 에 닫힌집합·assert 부재 | status·url_type·grouping_status 는 전부 `ALLOWED_*` + assert 가 있는데 confidence 만 맨 문자열이다 | 닫힌집합 + 검증 추가 |
| `extra_review_reason` 이 자유문자열 | 8건에 6종이 들어갔으나 검증 없음 | 닫힌집합화 |
| probe 를 **데스크톱 UA 하나로만** 관측 | 확정해야 하는 것은 **공식 모바일웹 랜딩**인데 한국 사이트 다수가 UA 를 보고 `m.` 서브도메인으로 보낸다. 데스크톱 UA 의 `final_url` 은 모바일 랜딩의 근거가 아니다 | 모바일 UA 를 1차 posture 로 두고 데스크톱을 대조군으로 **둘 다** 관측 (179 → 358 관측) |
| IP 리터럴이 PSL 을 통과 | 레지스트리 실측 `http://210.118.135.41` 이 등록도메인 `135.41` 로 나온다 | `certification_join.rd_of()` 에 IP·IPv6 가드 추가 |

---

## 4. scope 변경으로 재개방되는 판정 — 살베지 금지의 근거

v1 은 `LANDING_ONLY`, v2 SCOPE 는 `L0_INITIAL_LANDING + L1_SHALLOW_REPRESENTATIVE_ENTRY` 다.
C013 판정표에서 **문안이 depth-0 시험에 의존하는 건**은 다음과 같다.

| C013 상태 | 건수 | 재개방 사유 |
|---|---|---|
| `OFFICIAL_PRODUCT_PAGE` | 16 | 기준문이 "**그 URL 에** 웹 애플리케이션이 없다"다. `monimo` 는 자기 판정문에 *"JS 렌더링이라 웹 애플리케이션 진입점인지까지는 확인하지 못했다"* 고 적혀 있다. |
| `RETAIL_OFFLINE_ONLY` | 14 (그중 4건 명시적) | 기준문이 "그 결제가 **이 랜딩에서** 일어나지 않는다"다. `hyundai_department_store`·`shinsegae_department_store`·`lotte_department_store`·`lotte_mart` 는 거래채널이 **존재하는데 단일 랜딩으로 못 박지 못했다**는 사유가 붙어 있다. 통합몰 안의 한 관은 L1 진입으로 자연스럽다. |
| `UNRESOLVED` 중 slash-pair 2건 | 2 | `gmarket_auction`·`naver_naverpay` 의 논거가 *"어느 한쪽을 **단일** 공식 랜딩으로 고를 근거가 없다"* 다. '단일' 이 landing-only 산물이다. 게다가 `naver_naverpay` 배제 사유가 "pay.naver.com 이 로그인 벽으로 이동한다"인데, C013 자신의 `WEB_SERVICE` 기준문 88행이 *"로그인 벽이 있어도 진입점은 진입점이다"* 라 내부모순이다. |

**합계 약 22/71 (31%)**. 나머지 중 `SYSTEM_APP` 3건 + `APP_ONLY` 1건은 "공개 웹 랜딩이 아예 없다"는
주장이라 깊이와 무관하고, `korean_air` UNRESOLVED 는 read timeout(20s·45s) 이라 재관측 대상이다.

### 더 근본적인 지적 — C013 은 두 컬럼을 하나로 접었다

`OFFICIAL_PRODUCT_PAGE` 와 `RETAIL_OFFLINE_ONLY` 는 사실 **"공식 모바일웹 랜딩이 존재하는가"**(적격성)가
아니라 **"거기서 대표 task 를 정의할 수 있는가"**(매핑 가능성)를 판정한 값이다.
v2 스키마에서 둘은 다른 컬럼이다 — `web_eligibility_status`(`A2 §1.3`) 와
`mapping_status`(`A2 §1.9`). C013 은 랜딩이 있는데도 앱 기능이 브라우저에 없다는 이유로
**적격성 쪽에서** 배제했고, 그래서 30건이 표본에서 조용히 빠졌다.

LANE B 는 두 축을 분리해 판정한다. 이것이 살베지에서 판정값을 버린 가장 큰 이유다.
