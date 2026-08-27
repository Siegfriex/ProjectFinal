# FRAME INTEGRITY — A 발견 2건 (P1)

**ID** `LA-FRAME-A-001` · **발행** Claude A · **assertion_type** `OBSERVATION`
**작성** 2026-08-27T21:20:46+09:00 (`date` 판독값) · **계기** labeler L3/L4 보고에서 촉발, A 가 전수 확인

> 이 문서는 판정이 아니라 **관측**이다. 처리 방침은 §3 의 DECISION 이다.

---

## F-A1 — mart 56행 중 3건이 `FAILED_EVIDENCE_INCOMPLETE` 다 · P1

```
mart 56행의 measurement_status
  MEASURED                    53
  FAILED_EVIDENCE_INCOMPLETE   3
     wtg_054d78ed187cdd9f   https://www.coupangeats.com/
     wtg_64d30ef262d8782d   https://bank.shinhan.com/
     wtg_ef06dc942ef3ccc9   https://www.e-himart.co.kr/index.jsp
```

**`D-R0-45` 가 정정한 분모가 한 겹 더 필요하다.** 프레임은 3층이다.

```
attempted              59      E001 task frame
evidence bytes 존재     56      = mart 행 수
measurement MEASURED    53      실제로 관측이 성립한 것
unobserved               3      evidence 바이트 0 (삼성 3종)
```

```
DECISION 필요  "observed 56" 은 "성공 관측 56" 이 아니다.
              분석에서 어느 층을 분모로 쓰는지 매 지표마다 명시해야 한다.
```

### evidence 실측 — 크기 기준 스캔 5건 (**이 기준은 부적절했다, 아래 참조**)

`dom.html < 5KB` 또는 `ax.json < 2KB` 인 관측:

| web_target_id | dom | ax | final_url | mart status |
|---|---|---|---|---|
| `wtg_ef06dc942ef3ccc9` | 314 | 391 | e-himart | FAILED |
| `wtg_95967b50683649f2` | 1,657 | 371 | m.nonghyup.com | **MEASURED** |
| `wtg_fb3d1841dddfd982` | 1,657 | 371 | m.nonghyup.com | **MEASURED** |
| `wtg_64d30ef262d8782d` | 6,072 | 294 | bank.shinhan.com | FAILED |
| `wtg_49a5eca8b58f7270` | 16,653 | 1,113 | m.11st.co.kr | **MEASURED** |

**`MEASURED` 인데 상호작용 구조가 관측되지 않는 것이 3건 있다.** status 플래그만으로는
evidence 사용가능성을 판단할 수 없다.

### F-A1b — **크기는 degenerate capture 의 대리변수가 아니다** (A 자체 정정)

A 는 `dom<5KB` 로 스캔했다. labeler 보고를 받고 대조하니 그 기준이 **필요조건도 충분조건도
아니었다.**

| web_target_id | dom | ax | mart status | labeler 판정 | 크기 스캔 |
|---|---|---|---|---|---|
| `wtg_054d78ed187cdd9f` coupangeats | 132,077 | 30,178 | **FAILED** | 순수 마케팅 스플래시, 검색·상품카드·가격·폼 전무 | **놓침** |
| `wtg_13ed070478ef62c3` netflix/kr/login | 675,876 | 19,065 | MEASURED | 로그인 폼 단독, 콘텐츠 region 없음 | **놓침** |
| `wtg_d5ae5426eac23877` monimo | 20,481 | 3,445 | MEASURED | DOM/AX/스크린샷 전부 "컨텐츠 불러오는 중" 스피너 | **놓침** |
| `wtg_51484a735cdb487b` composecoffee | 8,174 | 3,806 | MEASURED | 링크 2개짜리 게이트웨이 | **놓침** |

**크기가 가장 큰 축에 속하는 것(676KB)이 구조적으로는 비어 있었다.**
이 프로젝트가 반복해서 만나는 형태다 — **대리변수가 답을 만든다.**
degenerate 판정은 크기가 아니라 **관측된 상호작용 구조**로 한다.

`labeler 가 evidence 구조를 읽어 잡은 목록이 A 의 크기 스캔보다 정확하다.`
A 의 §4 "경계 사례는 스캔하지 않았다" 는 실제 구멍이었고 labeler 가 메웠다.

### labeler 가 abstain 한 degenerate 후보 (evidence-only 판정)

```
coupangeats     마케팅 스플래시            L1   (mart 도 FAILED)
netflix/kr/login 로그인 폼 단독            L1   ← frame 이 로그인 URL 을 target 으로 잡았다
composecoffee   링크 2개 게이트웨이         L1
monimo          로딩 스피너 상태 캡처       L1
bank.shinhan    NetFunnel/SPA bootstrap    L3   (mart 도 FAILED)
m.nonghyup      NetFunnel/SPA bootstrap    L3
e-himart        body 없음, ax busy:1       L4   (mart 도 FAILED)
band.us         about/마케팅 페이지         L3
navercorp/map   기업 서비스소개 페이지      L3
kakaocorp       404                        L4
```

**`netflix.com/kr/login` 은 capture 결함이 아니라 frame 결함이다** — 연구가 로그인 페이지를
target URL 로 잡았다. `kakaocorp` 404 · `navercorp/map` 기업소개 · `band.us` about 도 같은 계열이다:
**대표기능 랜딩이 아닌 URL 이 frame 에 들어와 있다.** 이것은 W1/W2 로 고쳐지지 않는다.

### 독립 교차 확인 — labeler 가 detector 없이 같은 것을 짚었다

```
L3  bank.shinhan.com · m.nonghyup.com  →  "NetFunnel/SPA bootstrap 빈 페이지,
                                            렌더된 서비스 표면 없음" 으로 abstain
L4  e-himart                            →  "dom 314 bytes, SSO script 만, body 없음,
                                            ax 는 RootWebArea busy:1" 으로 abstain
```

labeler 는 mart 도 detector 출력도 보지 않았다. 그런데 **mart 의 FAILED 플래그 3건 중 2건과
degenerate capture 를 독립적으로 재발견했다.** 이것은 두 가지를 동시에 지지한다 —
labeler 독립성이 실제로 작동했고, degenerate capture 판정이 evidence 만으로 재현 가능하다.

---

## F-A2 — 두 개의 서로 다른 서비스가 동일한 바이트를 공유한다 · P1

```
wtg_95967b50683649f2   NH스마트뱅킹   FINANCIAL_ACTION_ENTRY
wtg_fb3d1841dddfd982   NH콕뱅크       FINANCIAL_ACTION_ENTRY

frame 의 web_target_url   둘 다  https://banking.nonghyup.com/nhbank.html
관측된 final_url          둘 다  https://m.nonghyup.com/index_mobile.html
dom.html sha256           둘 다  b783cbd0ec7630f3…   ← 완전히 동일한 바이트
```

전수 확인 결과 **동일 dom 바이트를 공유하는 관측군은 이 1군뿐**이고, 동일 `final_url` 관측군도
이 1군뿐이다.

### 왜 P1 인가

```
두 관측은 독립이 아니다.
n=56 을 독립 관측으로 세면 FINANCIAL_ACTION_ENTRY 에서 같은 페이지가 2번 계수된다.
SSOT §12 의 Spearman / Kruskal–Wallis / leave-one-service-out 은 전부 관측 독립을 전제한다.
```

**이것은 수집 결함이 아니라 frame 결함일 수 있다.** NH스마트뱅킹과 NH콕뱅크는 실제로 서로 다른
서비스지만 **모바일웹 랜딩이 같은 곳으로 수렴한다** — 앱 중심 서비스에서 예상되는 패턴이다.
연구 frame 이 `서비스` 단위인데 관측이 `랜딩 페이지` 단위라서 생긴 입도 불일치다.

---

## §3 A 의 처리 방침 — DECISION 후보 (B/C 검토 요청)

이 문서는 결정을 **미리 확정하지 않는다.** 세 축 모두에 영향이 있고 C 의 독립 판단이 필요하다.

```
D-A-후보-1   분석 분모를 매 지표마다 명시한다 (attempted 59 / bytes 56 / MEASURED 53).
             단일 n 으로 보고하지 않는다.
D-A-후보-2   NH 2건은 분석에서 서비스 단위 중복으로 표시한다. 삭제하지 않는다 —
             삭제하면 "왜 FINANCIAL 이 하나 적은가" 가 사라진다.
             통계에서는 leave-one-service-out 과 별도로 이 쌍을 하나로 묶는 감도분석을 한다.
D-A-후보-3   degenerate capture 3건(MEASURED 이지만 구조 없음)의 처리 —
             UNDETERMINED 로 남기되 FAIL 로 전이하지 않는다 (D-R0-23).
D-A-후보-4   informative missingness 후보를 확장한다.
             삼성 3종(unobserved) + 금융 3종(shinhan · NH×2) + coupangeats + e-himart.
             금융·앱중심 서비스에 결측이 몰리는지 W4 에서 검정한다.
```

**`D-A-후보-4` 가 가장 중요하다.** 결측이 무작위가 아니라 **특정 업종/구조에 몰린다면**,
그 결측 자체가 접근성 관련 발견이지 단순 수집 실패가 아니다. 그러나 지금 그렇게 주장하지 않는다 —
n 이 작고 원인이 규명되지 않았다.

## §4 이 발견이 검증하지 않은 것

```
degenerate capture 의 원인      NetFunnel/WAF/JS 미완료 중 무엇인지 미규명
NH 수렴이 실제 서비스 구조인지  m.nonghyup.com 이 두 서비스의 공통 랜딩인지 미확인
재수집하면 달라지는지            W1/W2 이후 재관측 대상
다른 archetype 의 유사 사례      dom<5KB 기준을 넘는 경계 사례는 스캔하지 않았다
```
