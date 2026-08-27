# Task Family & Target Frame v3.0

## 1. 표본 원칙

본 연구의 sampling unit은 `service × frozen task`다. 공급자의 사업 domain을 보고 대표기능을 추론하지 않는다. Task family는 문제정의와 생활과업 relevance를 바탕으로 연구 시작 전에 고정한다.

### 포함
- 공식 public mobile web이 존재하고 390×844 mobile UA에서 실제 렌더 가능.
- 동일 family task를 수행할 수 있는 service.
- endpoint를 credential/transaction 수행 없이 관측 가능하거나 legitimate AUTH_GATE로 종료 가능.

### 제외
- 앱 설치/앱 전환만 강제하고 public mobile web task surface가 없는 경우.
- 다른 서비스와 과업 의미가 근본적으로 달라 matched comparison이 성립하지 않는 경우.
- 결과를 본 뒤 unfavorable case라는 이유로 제외 금지.

### replacement
precheck에서 부적격이면 같은 family, 가능하면 같은 provider subtype/mode의 replacement로 **collection 전에** 교체하고 manifest를 다시 freeze한다. freeze 후 교체는 별도 새 frame/version.

## 2. Frozen Task Families

| ID | task family | matched task | fixture | endpoint | n |
|---|---|---|---|---|---|
| F1 | BANK_TRANSFER_ENTRY | 개인뱅킹 계좌이체/송금 기능 진입 | 없음 | 사용자가 이체/송금 경로를 선택한 뒤 task-specific transfer surface가 열리거나 LOGIN/IDENTITY gate가 불가피하게 나타나는 최초 상태. 자격정보 입력·login submit·수취계좌/금액 입력·이체 실행 금지. | 10 |
| F2 | SHOPPING_ITEM_DETAIL | 상품 검색/탐색 후 상품 상세 진입 | 검색어=생수 | 개별 상품 상세면에서 상품명과 가격 또는 가격정보가 확인되는 최초 상태. 장바구니/구매/결제 control은 존재만 관측하고 활성화 금지. | 10 |
| F3 | DELIVERY_TRACKING_ENTRY | 택배 배송조회/운송장조회 기능 진입 | 실제 운송장번호 입력 없음 | 운송장/등기번호 입력 control과 조회 실행 control이 관측 가능한 최초 상태. 실사용 번호·개인정보 입력 및 조회 submit 금지. | 10 |
| F4 | HEALTH_PROVIDER_FINDING | 병원·약국/의료기관 찾기 | 지역=서울특별시 중구; 진료과/키워드=내과; 위치권한 허용 안 함 | 검색 폼에서 고정 조건을 적용한 뒤 기관 결과목록 또는 지도 결과가 표시되는 최초 상태. 예약·전화·외부앱 실행 금지. | 10 |
| F5 | INTERCITY_SCHEDULE_SEARCH | 서울권→부산권, T+1 운행편/항공편 조회 | 서울권→부산권; 날짜=T+1; 성인=1. mode별 출발/도착 지점은 target row의 fixture_override 사용. | 조건 입력 후 시간·편명/운행편·가격 또는 예약가능성 정보를 포함한 결과목록이 표시되는 최초 상태. 좌석선택·예약·결제 금지. | 10 |

## 3. 금융 secondary repeated task

F1 10개 은행에 `보유계좌/잔액조회 기능 진입`을 선택적으로 추가할 수 있다. 이는 main n=50을 60으로 늘리는 것이 아니라 동일 provider의 within-provider repeated task다. 반드시 primary 송금 task와 별도 `task_id`로 저장한다.

## 4. 50 Candidate Targets

| ID | service | provider | URL | task | eligibility |
|---|---|---|---|---|---|
| F1-01 | NH농협은행 | 은행 | https://bank.nonghyup.com/ | 개인뱅킹 계좌이체/송금 기능 진입 | PRECHECK_REQUIRED |
| F1-02 | KB국민은행 | 은행 | https://obank.kbstar.com/ | 개인뱅킹 계좌이체/송금 기능 진입 | PRECHECK_REQUIRED |
| F1-03 | 신한은행 | 은행 | https://bank.shinhan.com/ | 개인뱅킹 계좌이체/송금 기능 진입 | PRECHECK_REQUIRED |
| F1-04 | 하나은행 | 은행 | https://m.hanabank.com/ | 개인뱅킹 계좌이체/송금 기능 진입 | PRECHECK_REQUIRED |
| F1-05 | 우리은행 | 은행 | https://spib.wooribank.com/ | 개인뱅킹 계좌이체/송금 기능 진입 | PRECHECK_REQUIRED |
| F1-06 | IBK기업은행 | 은행 | https://mybank.ibk.co.kr/ | 개인뱅킹 계좌이체/송금 기능 진입 | PRECHECK_REQUIRED |
| F1-07 | SC제일은행 | 은행 | https://www.standardchartered.co.kr/ | 개인뱅킹 계좌이체/송금 기능 진입 | PRECHECK_REQUIRED |
| F1-08 | BNK부산은행 | 지방은행 | https://www.busanbank.co.kr/ | 개인뱅킹 계좌이체/송금 기능 진입 | PRECHECK_REQUIRED |
| F1-09 | BNK경남은행 | 지방은행 | https://www.knbank.co.kr/ | 개인뱅킹 계좌이체/송금 기능 진입 | PRECHECK_REQUIRED |
| F1-10 | iM뱅크 | 지방은행 | https://www.imbank.co.kr/ | 개인뱅킹 계좌이체/송금 기능 진입 | PRECHECK_REQUIRED |
| F2-01 | G마켓 | 오픈마켓 | https://www.gmarket.co.kr/ | 상품 검색/탐색 후 상품 상세 진입 | PRECHECK_REQUIRED |
| F2-02 | 11번가 | 오픈마켓 | https://www.11st.co.kr/ | 상품 검색/탐색 후 상품 상세 진입 | PRECHECK_REQUIRED |
| F2-03 | 쿠팡 | 종합커머스 | https://www.coupang.com/ | 상품 검색/탐색 후 상품 상세 진입 | PRECHECK_REQUIRED |
| F2-04 | 네이버쇼핑 | 쇼핑검색/커머스 | https://shopping.naver.com/ | 상품 검색/탐색 후 상품 상세 진입 | PRECHECK_REQUIRED |
| F2-05 | SSG.COM | 종합커머스 | https://www.ssg.com/ | 상품 검색/탐색 후 상품 상세 진입 | PRECHECK_REQUIRED |
| F2-06 | 롯데ON | 종합커머스 | https://www.lotteon.com/ | 상품 검색/탐색 후 상품 상세 진입 | PRECHECK_REQUIRED |
| F2-07 | 옥션 | 오픈마켓 | https://www.auction.co.kr/ | 상품 검색/탐색 후 상품 상세 진입 | PRECHECK_REQUIRED |
| F2-08 | GS SHOP | 홈쇼핑/커머스 | https://www.gsshop.com/ | 상품 검색/탐색 후 상품 상세 진입 | PRECHECK_REQUIRED |
| F2-09 | CJ온스타일 | 홈쇼핑/커머스 | https://www.cjonstyle.com/ | 상품 검색/탐색 후 상품 상세 진입 | PRECHECK_REQUIRED |
| F2-10 | 홈플러스 | 리테일커머스 | https://front.homeplus.co.kr/ | 상품 검색/탐색 후 상품 상세 진입 | PRECHECK_REQUIRED |
| F3-01 | CJ대한통운 | 택배 | https://www.cjlogistics.com/ko/tool/parcel/tracking | 택배 배송조회/운송장조회 기능 진입 | PRECHECK_REQUIRED |
| F3-02 | 한진택배 | 택배 | https://www.hanjin.com/ | 택배 배송조회/운송장조회 기능 진입 | PRECHECK_REQUIRED |
| F3-03 | 롯데글로벌로지스 | 택배 | https://www.lotteglogis.com/ | 택배 배송조회/운송장조회 기능 진입 | PRECHECK_REQUIRED |
| F3-04 | 로젠택배 | 택배 | https://www.ilogen.com/ | 택배 배송조회/운송장조회 기능 진입 | PRECHECK_REQUIRED |
| F3-05 | 우체국택배 | 공공 물류 | https://service.epost.go.kr/ | 택배 배송조회/운송장조회 기능 진입 | PRECHECK_REQUIRED |
| F3-06 | 경동택배 | 택배 | https://kdexp.com/ | 택배 배송조회/운송장조회 기능 진입 | PRECHECK_REQUIRED |
| F3-07 | 대신택배 | 택배 | https://www.ds3211.co.kr/ | 택배 배송조회/운송장조회 기능 진입 | PRECHECK_REQUIRED |
| F3-08 | 일양로지스 | 택배/국제물류 | https://www.ilyanglogis.co.kr/ | 택배 배송조회/운송장조회 기능 진입 | PRECHECK_REQUIRED |
| F3-09 | 합동택배 | 택배 | https://hdexp.co.kr/ | 택배 배송조회/운송장조회 기능 진입 | PRECHECK_REQUIRED |
| F3-10 | 건영택배 | 택배 | https://www.kunyoung.com/ | 택배 배송조회/운송장조회 기능 진입 | PRECHECK_REQUIRED |
| F4-01 | 건강보험심사평가원 병원·약국찾기 | 공공 전문검색 | https://www.hira.or.kr/ra/hosp/getHealthMap.do?tabgbn=02 | 병원·약국/의료기관 찾기 | PRECHECK_REQUIRED |
| F4-02 | E-Gen 응급의료포털 | 공공 전문검색 | https://www.e-gen.or.kr/ | 병원·약국/의료기관 찾기 | PRECHECK_REQUIRED |
| F4-03 | 예방접종도우미 위탁의료기관 찾기 | 국가 전문검색 | https://nip.kdca.go.kr/irhp/ | 병원·약국/의료기관 찾기 | PRECHECK_REQUIRED |
| F4-04 | e보건소 보건기관 찾기 | 국가 전문검색 | https://e-health.go.kr/gh/heSrvc/selectHeOrgMainInfo.do | 병원·약국/의료기관 찾기 | PRECHECK_REQUIRED |
| F4-05 | 중앙치매센터 치매안심센터 찾기 | 공공 전문검색 | https://www.nid.or.kr/info/facility_list.aspx | 병원·약국/의료기관 찾기 | PRECHECK_REQUIRED |
| F4-06 | 네이버지도 병원검색 | 일반 지도검색 | https://map.naver.com/ | 병원·약국/의료기관 찾기 | PRECHECK_REQUIRED |
| F4-07 | 카카오맵 병원검색 | 일반 지도검색 | https://map.kakao.com/ | 병원·약국/의료기관 찾기 | PRECHECK_REQUIRED |
| F4-08 | Google Maps 병원검색 | 일반 지도검색 | https://www.google.com/maps | 병원·약국/의료기관 찾기 | PRECHECK_REQUIRED |
| F4-09 | 굿닥 병원검색 | 민간 의료검색 | https://www.goodoc.co.kr/ | 병원·약국/의료기관 찾기 | PRECHECK_REQUIRED |
| F4-10 | 모두닥 병원검색 | 민간 의료검색 | https://www.modoodoc.com/ | 병원·약국/의료기관 찾기 | PRECHECK_REQUIRED |
| F5-01 | 코레일 | 철도 | https://www.korail.com/ | 서울권→부산권, T+1 운행편/항공편 조회 | PRECHECK_REQUIRED |
| F5-02 | SRT | 철도 | https://etk.srail.kr/ | 서울권→부산권, T+1 운행편/항공편 조회 | PRECHECK_REQUIRED |
| F5-03 | KOBUS | 고속버스 | https://www.kobus.co.kr/ | 서울권→부산권, T+1 운행편/항공편 조회 | PRECHECK_REQUIRED |
| F5-04 | 버스타고 | 시외버스 | https://www.bustago.or.kr/ | 서울권→부산권, T+1 운행편/항공편 조회 | PRECHECK_REQUIRED |
| F5-05 | 티머니 시외버스 | 시외버스 | https://txbus.t-money.co.kr/ | 서울권→부산권, T+1 운행편/항공편 조회 | PRECHECK_REQUIRED |
| F5-06 | 대한항공 | 항공 | https://www.koreanair.com/ | 서울권→부산권, T+1 운행편/항공편 조회 | PRECHECK_REQUIRED |
| F5-07 | 아시아나항공 | 항공 | https://flyasiana.com/ | 서울권→부산권, T+1 운행편/항공편 조회 | PRECHECK_REQUIRED |
| F5-08 | 제주항공 | 항공 | https://www.jejuair.net/ | 서울권→부산권, T+1 운행편/항공편 조회 | PRECHECK_REQUIRED |
| F5-09 | 티웨이항공 | 항공 | https://www.twayair.com/ | 서울권→부산권, T+1 운행편/항공편 조회 | PRECHECK_REQUIRED |
| F5-10 | 진에어 | 항공 | https://www.jinair.com/ | 서울권→부산권, T+1 운행편/항공편 조회 | PRECHECK_REQUIRED |

## 5. Freeze contract

최종 main manifest는 최소 다음을 포함한다.

```json
{
  "frame_id": "CROSS_SERVICE_MATCHED_50_V3",
  "version": "3.0",
  "target_count": 50,
  "task_family_count": 5,
  "targets": ["..."],
  "task_contract_sha256": "...",
  "manifest_sha256": "...",
  "frozen_at_kst": "...",
  "authority_sha": "..."
}
```

`manifest_sha256` mismatch면 REAL 실행을 거부한다.
