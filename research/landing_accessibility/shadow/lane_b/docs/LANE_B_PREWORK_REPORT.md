# LANE B — P-B PREWORK 결과 보고

```
status                          = SHADOW_PREPARATORY
shadow_lane                     = LANE_B
base_sha                        = d5f1da5652953542d5c8be377026cc3293f2075a
created_before_p0_close         = true
authoritative                   = false
real_target_outcome_used        = false
real_target_measurement         = false
requires_post_p0_reconciliation = true
```

> **이 산출물은 권위본이 아니다.** `PHASE_GATES §4.7` 에 따라 P0 종료 후
> frozen main SHA 확인 → drift 확인 → deterministic rerun → 오염검사 → 감사를
> 거쳐야만 승격 대상이 된다. "이미 했으니 PASS" 는 금지다.

---

## 0. 오염 검사 — 먼저 밝힌다

| 검사 | 결과 |
|---|---|
| 접근성 verdict 생성 건수 | **0** |
| KWCAG criterion / popup / obstruction / MPFED / NED / IED 산출 | **0** |
| 금지 토큰 스캔 (산출물 전량) | **hit 0** |
| `evidence/` 디렉터리 생성 | **없음** |
| Pilot `state/*.parquet` 수정 | **없음** (읽기 전용으로만 열었다) |
| 다른 워크트리 수정 | **없음** |
| `research/landing-accessibility-main` merge·promotion | **없음** |
| 인증 결과로 target 선정 | **없음** (`assert_not_used_for_selection()` 이 실행 시점 검사) |
| 접근성 결과로 task 선정 | **없음** (`assign_candidate()` 시그니처에 인자 자체가 없다) |
| `mapping_status = FROZEN` 생성 | **0** |

URL probe 는 `PHASE_GATES §4.5` 가 허용한 target-preparation 이며,
`probe_official_urls_shadow.py` 의 `_firewall_assert()` 가 매 실행마다 산출물에
금지 필드가 없음을 확인하고, 응답 본문은 제목 추출 직후 `del` 로 폐기한다.

---

## 1. 관측

| 항목 | 값 |
|---|---|
| 후보 URL | 179 (C013 탐색 결과 재사용 — **가설 입력**) |
| 관측 | **358** (모바일 UA 179 + 데스크톱 UA 179) |
| HTTP 200 | 322 |
| 봇차단(403) | 12 · 404 10 · 500 2 · 400 2 · 무응답 10 |
| 요청 간격 | 1.2s 순차, 병렬 없음 |

**C013 대비 핵심 변경**: C013 은 데스크톱 UA 하나로만 관측했다. P-B 가 확정해야 하는 것은
**공식 모바일웹 랜딩**인데 한국 사이트 다수가 UA 를 보고 `m.` 서브도메인으로 보내므로
데스크톱 관측의 `final_url` 은 모바일 랜딩의 근거가 되지 못한다. 모바일을 1차 posture 로 두고
데스크톱을 대조군으로 함께 기록했다 (실측: `www.naver.com` → 모바일 UA 에서 `m.naver.com`).

---

## 2. Web eligibility 판정 — 81건 전량

| `web_eligibility_status` | 규칙 | 건 |
|---|---|---|
| `ELIGIBLE_WEB` | E-2 | **60** |
| `EXCLUDED_INDUSTRY_AXIS` | E-1 | **10** |
| `UNDETERMINED_URL_EVIDENCE` | E-5 | **10** |
| `EXCLUDED_APP_ONLY` | E-3 | **1** |
| `NOT_ASSESSED` | — | **0** (71건 전량 판정 완료) |
| `EXCLUDED_NO_PUBLIC_WEB_LANDING` | E-4 | 0 (규칙은 구현했으나 발화하지 않았다) |

`url_confidence`: HIGH 59 · MEDIUM 1 · LOW 11 · N/A 10(업종축).

### 2.1 C013 대비 30건이 뒤집힌 이유 — 두 축을 다시 갈랐다

C013 판정: `WEB_SERVICE` 33 · `OFFICIAL_PRODUCT_PAGE` 16 · `RETAIL_OFFLINE_ONLY` 14 ·
`UNRESOLVED` 4 · `SYSTEM_APP` 3 · `APP_ONLY` 1.

`OFFICIAL_PRODUCT_PAGE` 16 + `RETAIL_OFFLINE_ONLY` 14 = **30건**의 배제 사유는 실제로는
*"이 랜딩에서 앱의 핵심기능이 되지 않는다"* 였다. 그것은 `A2 §1.3` 이 묻는
**"공식 모바일웹 랜딩이 존재하는가"** 가 아니라 `A2 §1.9` `mapping_status` 가 묻는
**"여기서 대표 task 를 정의할 수 있는가"** 다. 두 축을 접으면 랜딩이 멀쩡히 존재하는
30건이 표본에서 조용히 빠진다.

더구나 그 기준문은 전부 "**그 URL 에** 웹 애플리케이션이 없다" 형태의 **depth-0 시험**이고,
v2 SCOPE 는 `L0_INITIAL_LANDING + L1_SHALLOW_REPRESENTATIVE_ENTRY` 다.

→ LANE B 는 적격성을 **랜딩 존재만으로** 판정하고, 기능 가용성은 task candidate 로 넘겼다.

### 2.2 `EXCLUDED_APP_ONLY` 1건

`samsung_calculator` — 살아있는 후보가 앱스토어 등재면뿐이고, C013 이 남긴 부재 확인
절차 진술(삼성전자 공식 앱 색인 `samsung.com/sec/apps/` 전수 확인)이 있다.
**진술이 없으면 배제하지 않는다** — `device_care`·`my_files` 는 같은 성격이지만
`samsungsvc.co.kr` 후보가 응답해 `ELIGIBLE_WEB` 로 갔다.
"선탑재 앱이니 웹이 없다" 는 추론은 근거로 쓰지 않았다 (C013 06 §2-3 규율 계승).

### 2.3 `UNDETERMINED_URL_EVIDENCE` 10건 — 확정하지 못한 이유

| 사유 | 건 | 대상 |
|---|---|---|
| slash pair 후보 상충 | 5 | `gmarket_auction` · `gs_homeshopping_gsshop` · `naver_naverpay` · `nc_dept_newcore_outlet` · `paris_baguette_pariscroissant` |
| 부수(기업·지원) 사이트만 확인됨 | 3 | `coupang_app` · `google_photos` · `tiktok_lite` |
| 봇차단으로 랜딩 미확인 | 1 | `coupang_retail` |
| 무응답 (read timeout) | 1 | `korean_air` |

**slash pair 5건**은 `네이버/네이버페이` 처럼 두 브랜드를 합산한 measurement entity 이며
후보 랜딩이 서로 다른 브랜드로 갈린다. 제목이 우연히 한쪽 토큰과 맞는다는 이유로 고르면
나머지 절반이 조용히 사라지므로 확정하지 않았다.

**`coupang`** 은 `www.coupang.com` 이 WAF 로 403 을 주고 그 응답 제목이 `Access Denied`
라 브랜드를 식별할 수 없었다. 200 을 주는 후보는 `news.coupang.com/company/`(뉴스룸)뿐이라
소비자 서비스 랜딩으로 확정하지 않았다. **HTTP 클라이언트 방식의 한계이며 실제 부재가 아니다.**

**`korean_air`** 은 20s·75s 두 번 모두 read timeout 이다.

---

## 3. 그룹 가설 3건 검정 — falsifier 를 **문안 그대로** 적용했다

세 그룹의 falsifier 문안이 서로 다르다 (`state/web_target_group.parquet` 실측).

| 그룹 | 선언된 falsifier | 적용 scope |
|---|---|---|
| `coupang` | "두 measurement_entity 의 official_landing_url 이 서로 다른 **PSL 등록도메인**으로 확정되면 SPLIT" | `REGISTERED_DOMAIN_ONLY` |
| `gmarket` | "RETAIL entity 의 랜딩이 APP entity 와 다른 등록도메인 **또는 다른 경로**로 확정되면 SPLIT" | `REGISTERED_DOMAIN_OR_PATH` |
| `naver` | 동일 | `REGISTERED_DOMAIN_OR_PATH` |

통일 규칙을 쓰면 선언된 falsifier 를 지키지 않는 것이므로 그룹별로 적용했다.

### 검정 결과

| 그룹 | 결과 | 근거 |
|---|---|---|
| **`gmarket`** | **SPLIT** | member 별 확인 랜딩 집합이 `gmarket_app {m.gmarket.co.kr, www.gmarket.co.kr}` vs `gmarket_auction {www.auction.co.kr, www.gmarket.co.kr}` 로 갈린다. RETAIL entity `G마켓/옥션` 은 APP entity 에 없는 **`auction.co.kr` 등록도메인**을 포함한다 (403 이지만 응답 제목 `옥션 - 쇼핑은 옥션` 으로 브랜드 확인). 자체 기록이 "세 후보 중 가장 약하다" 고 한 가설이 실제로 반증됐다 |
| **`naver`** | **SPLIT** | `naver_naverpay` 가 `home.pay.naver.com/`(제목 `Npay 금융`, HTTP 200) 을, `naver_app` 이 `m.naver.com/`(제목 `NAVER`) 을 준다. 등록도메인은 `naver.com` 으로 같으나 **경로가 다르다** → 선언된 falsifier 가 발화 |
| **`coupang`** | **NOT_TESTABLE** | 두 member 모두 랜딩을 확정하지 못했고, 확인된 랜딩 집합도 갈리지 않는다. 두 member 의 후보가 `www.coupang.com` 하나로 동일해 divergence 증거 자체가 없다. **확인된 것으로도 반증된 것으로도 처리하지 않는다** |

### 반증에 단일 랜딩 선택이 필요하지 않다

선언된 falsifier 는 "**다른** 등록도메인 또는 경로로 확정되면 SPLIT" 이다.
따라서 한 member 의 확인된 랜딩 **하나만** 달라도 반증에 충분하며, 어느 것이 그 member 의
대표 랜딩인지까지 정할 필요가 없다. `gmarket_auction`·`naver_naverpay` 가
`UNDETERMINED_URL_EVIDENCE` 인 채로도 SPLIT 판정이 성립하는 이유다.

### 최종 web target 수

```
68 groups → gmarket SPLIT(+1) → naver SPLIT(+1) → coupang 미검정(±0) → 70
```

**web target = 70**, 지시받은 범위 `[68, 71]` 안이다.
`coupang` 이 나중에 SPLIT 으로 확정되면 71, CONFIRM 되면 70 으로 유지된다.

---

## 4. 인증 join — 규칙은 `docs/CERTIFICATION_JOIN_RULES.md`

| `join_outcome` | 건 |
|---|---|
| `NOT_CERTIFIED` | 55 |
| `UNDETERMINED` | 13 (URL 미확정 10 · 이름 불일치 3) |
| `CERTIFIED_CURRENT` | **0** |

**1:1 성립률**: 레지스트리 내부에서 요건1+2 통과 후 등록도메인당 생존자가 1건인 비율은
**127 / 151 = 84.1%**. 그러나 실제 join 에서 요건1·2 를 통과한 인증이 걸린 target 은 3건뿐이고
그 3건은 전부 요건3(이름 대응)에서 떨어져 **1:1 성립 0건**이다.

원인은 규칙의 약함이 아니다. 358건 관측의 모든 후보 등록도메인을 유효인증 154 등록도메인과
교차하면 겹치는 것이 **`samsung.com` 하나**이고, 그 유일한 유효인증은 `삼성전자승마단` 이다.
레지스트리 유효 226건은 `.go.kr`/`.or.kr`/`.ac.kr` 이 압도적이고 상용 도메인은 46건이며,
그중 이 코호트와 이름이 겹치는 것은 `대한항공` 1건이다.

경계 결함 2건(+1)은 전부 fail-closed 로 처리했다 — 상세는 join 규칙 문서 §2.1.

---

## 5. 대표 task candidate — 71행, `FROZEN` 0건

| `mapping_status` | 건 |
|---|---|
| `CANDIDATE` | 59 |
| `AMBIGUOUS_UNRESOLVED` | 12 |
| `FROZEN` | **0** |

`mapping_basis = RULE` 전량. LANE A codebook
(`analysis/codebook/codebook.json`, `adoption_status = SHADOW_PREPARATORY_PENDING_PA_AUDIT`) 을
`landing_pa_shadow` 워크트리에서 **읽기 전용으로** 참조했고 sha256
`49cc10484fa4f5cf344be96ed828dcb1ae93ccbab61b4e59caeaec1b8deb239e` 를 매니페스트에 고정했다.
LANE A 는 이 작업 도중 `agent/landing-pa-shadow @ 0f46203` 로 커밋했고 codebook 이 한 번
바뀌었다 (이전 sha `dad7f853…`). 본 산출물은 **커밋 후 판본**으로 생성됐다.
codebook 이 P-A 감사에서 다시 바뀌면 이 산출물은 재생성 대상이다 (reconciliation 항목).

`region_signal_type`: `DOM_AX_ROLE` 63 · `CODEBOOK_PENDING` 8.
`CODEBOOK_PENDING` 8건은 전부 `UTILITY_ENTRY` archetype 이며, codebook 규칙 P-2 가
채택 전까지 `FROZEN` 전이를 금지한 대상과 일치한다.

`human_final_required = 1` 은 **5건** — `HUMAN_FINAL_REVIEW_MAX = 5` 예산과 같다.
추가 abstain 이 생기면 예산을 넘으므로 reconciliation 에서 재배분이 필요하다.

`assign_candidate()` 의 시그니처에는 인증·접근성 인자가 **없다.** 교차오염 금지를
문서가 아니라 함수 시그니처로 막았다.

---

## 6. Reconciliation 에 넘기는 항목

1. **LANE A codebook 이 커밋·감사되면 task candidate 재생성** — 현재 참조본은 워크트리 미커밋본
2. **`coupang` · `korean_air` · `google_photos` · `tiktok_lite` 재관측** — HTTP 클라이언트가 아니라 실제 브라우저(Playwright)로 열면 확정될 가능성이 높다. 현재의 `UNDETERMINED` 는 **방법의 한계**이지 부재의 증거가 아니다
3. **slash pair 5건의 measurement entity 분해 여부** — P-A 소관. 분해하면 web target 수가 다시 바뀐다
4. **`coupang` 그룹 가설 미검정** — web target 이 70 인지 71 인지가 여기에 달려 있다
5. **`human_final_required` 5건이 예산 상한과 같다** — 추가 abstain 발생 시 재배분
6. **인증이 이 코호트에서 사실상 상수(0)** — 층화·설명변수 설계의 재검토가 필요한지는 Research Director 판단 사항

---

## 7. 산출물

```
shadow/lane_b/state/
  url_probe_shadow.json                        358 관측 + PSL provenance + firewall 선언
  web_eligibility_shadow.{parquet,csv}         81행 적격성 판정
  web_target_group_shadow.{parquet,csv}        68행 그룹 가설 검정
  certification_join_shadow.{parquet,csv}      68행 인증 join
  representative_task_candidate_shadow.{parquet,csv}  71행 task candidate
  LANE_B_SHADOW_MANIFEST.json                  provenance + 분포 + 오염검사
  c013_candidate_seed_UNVERIFIED.json          C013 후보 (격리 · 가설 입력)
  c013_absence_checks.json                     C013 부재확인 진술 3건

shadow/lane_b/scripts/
  probe_official_urls_shadow.py                target-preparation probe
  build_web_eligibility_shadow.py              적격성 판정 규칙
  certification_join.py                        인증 join infrastructure
  task_candidate_rules.py                      task candidate 규칙
  run_lane_b.py                                조립 드라이버

shadow/lane_b/docs/
  C013_SALVAGE_LEDGER.md                       파일 단위 살베지 원장
  CERTIFICATION_JOIN_RULES.md                  3요건 조작화
  LANE_B_PREWORK_REPORT.md                     이 문서

src/landing_accessibility/registered_domain.py C013 살베지 (PSL 판정)
```

모든 parquet/csv 에 `_status` · `_base_sha` · `_shadow_lane` · `_authoritative` ·
`_real_target_outcome_used` · `_requires_post_p0_reconciliation` 컬럼이 붙어 있다.
