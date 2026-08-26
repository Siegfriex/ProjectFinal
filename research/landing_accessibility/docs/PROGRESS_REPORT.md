# 진행 현황 보고 — v4.0 Closing Sprint 중간

> **이 문서는 `FINAL_CLOSURE_REPORT` 가 아니다.**
> `READY_FOR_E001` 에 도달하지 않았으므로 최종 보고서를 생성할 수 없다.
> 아래는 그 시점까지의 실측 현황이다.

**작성** 2026-08-26 · 오케스트레이터
**적용 지시** orchestrator-constitution-v3 → hardening-directive-v3.1 → **FINAL_CLOSURE_DIRECTIVE_v4.0**

---

## 0. 한 줄 답

**아직 수행하지 않았다.** Bundle A(Target Frame Closure)가 진행 중이고 B·C·D가 남았다.

```
PRE-E001 STATUS      NOT READY
FULL COLLECTION      NOT STARTED
현재 진행             Bundle A / C013 executor 작업 중
```

---

## 1. 원격 실측 (v4.0 §0)

`CONTROL_STATE_RECONCILIATION_REQUIRED = false` — remote 와 `control/state.json` 이 일치한다.

| 브랜치 | SHA | 상태 |
|---|---|---|
| `research/refcohort-r1` | `32460b87334a67f6` | Pilot, lock_branch, 불변 |
| `research/landing-accessibility-main` | `5a9015d1e95b1530` | **PROM-002 승격본** |
| `agent/landing-exec` | `5a9015d1e95b1530` | C013 미커밋 21파일 작업 중 |
| `audit/landing-adversarial` | `510d5f21a4de3d64` | C012 감사 완료 |
| `audit/landing-ssot` | `1bc2c71b2c48f060` | C012 감사 완료 |
| `control/landing-orchestrator` | `c3f8507` | 로컬=원격 |

```
audit lag depth   0
open P0           0
open P1           0
open P2          24  (E001_BLOCKING 6 / POST_E001 9 / PUBLICATION 6 / CLOSED 3)
full_collection   PROHIBITED
evidence/         부재
```

---

## 2. 완료된 것 — 승격으로 검증된 범위

두 번의 promotion 이 독립감사 2건 + 재결을 통과했다.

```
main   32460b87  →  edb0478f (PROM-001)  →  5a9015d1 (PROM-002)
```

### 2-1. PRE_MEASUREMENT_VERIFIED_BASELINE (v4.0 §1 동결 대상)

| 항목 | 값 | 검증 |
|---|---|---|
| A1 모집단 권위 | Wiseapp Insight 933 | raw 6종 sha256 불변, git log 상 수정 0건 |
| 원문 구조 | 4 chapter / 11 section / 17 panel | INDEX verbatim SAME 15 / MISMATCH 0 |
| source rows | **261** | 승격 baseline 대비 `assert_frame_equal` IDENTICAL |
| APP / RETAIL | 137 + 124 = 261 | domain × axis_type 별도 컬럼 |
| measurement entity | **81** | service_id 한글 0자·충돌 0 |
| entity alias | 82 | 키 = (entity_name_raw, domain) |
| source membership | 142 | (service_id, panel_id) 유일 |
| web target group | 68 | `web_target_url` 전 행 null |
| A2 인증 스냅샷 | `KWACC_WA_20260826` | COMPLETE, 2,283행, 감사일 유효 226 |
| legacy xlsx | `UNSOURCED_INCOMPATIBLE_PANEL_SET` | 유입 0건 |

### 2-2. 원문에서만 얻은 조작적 정의

파생자료에 전혀 없던 것들이다. 모집단 정의를 방어하려면 필요하다.

```
코호트        액티브시니어+ 세대 = 50대 이상
측정기간      25년 7월~12월 월간 평균 (fig07 만 25년 12월 / 전년 동월)
APP 모집단    한국인 Android+iOS 스마트폰 사용자 추정        (본문 5회)
RETAIL 모집단 계좌이체·현금거래·상품권 결제액 미포함          (본문 6회)
점유율 모수   월간 사용자 평균 200만 명 이상 앱
성장률 모수   200만 명 이상 AND 시니어 비율 25% 이상
결제 성장률   순 결제추정금액 5천억 원 이상 AND 비율 30% 이상
```

**RETAIL 지표가 카드 결제 표본이라는 사실이 연구 한계의 핵심이다.**
현금·계좌이체 비중이 높은 고령 세그먼트가 구조적으로 과소집계된다 — 이 연구가 겨냥하는 바로 그 집단이다.

### 2-3. A1 동결 유효창

발행처가 **2026-08-25 09:00** 에 `[와이즈앱] 모집단 변경 사전 안내`(nid=127, 종료일 없음)를 게시했다.
원문 취득은 그 다음 날이다. 동결본을 **"2026-08-26 시점 게시 판본"** 으로 한정했다.

---

## 3. 남은 것 (v4.0 §5 Critical Path)

| Bundle | 내용 | 상태 |
|---|---|---|
| **A** TARGET FRAME | web eligibility 71건 판정 · official landing URL · 그룹 승격/해체 | **진행 중 (C013)** |
| **B** CERT + FEASIBILITY | certification join · feasibility 재산출 · RQ2/RQ3 생존 판정 | 미착수 |
| **C** MEASUREMENT READINESS | observation identity · evidence 1:1 · append-only · manifest · URL binding · judgment semantics · automation split · probe coverage | 미착수 |
| **D** E000 + FINAL | 스모크 8~12건 · 최종 보고서 · automation hold | 미착수 |

### 현재 UNVERIFIED 범위

```
web eligibility        NOT_ASSESSED 71건 — 판정 미착수
official landing URL   url_review 산출 중, 미커밋
certification join     certified_current 미산출
feasibility            INVALIDATED 상태, A1 기준 재산출 미실시
measurement engine     전부 NOT_RUN
judgment semantics     미구현
E000 smoke             미실행
RQ2/RQ3/RQ4 성립여부    이전 NO-GO 는 철회 상태, 재판단 전
```

---

## 4. 하네스가 실제로 한 일

이 하네스의 전제는 **"누구도 혼자 정답을 결정하지 못한다"** 이다. 실제로 네 방향 모두에서 정정이 일어났다.

### 4-1. executor 주장이 감사로 뒤집힘

xlsx 와 원문의 차이를 "값 불일치 2만 명" 으로 기록했으나, 적대적 감사가 항목별로 대조해
**애초에 다른 패널 집합** 임을 증명했다. Google 1,278만이 xlsx 에 없고, 점유율 패널은
다음이 54.1%(1위) vs 38.7%(5위) 로 겹치지 않으며, 리테일 순서가 역전돼 있고, provenance 가 전무하다.
→ `A7 = UNSOURCED_INCOMPATIBLE_PANEL_SET`. 셀 패치(`1379→1377`)에 의한 패널 융합을 금지했다.

### 4-2. 오케스트레이터 진단이 executor 에게 반증됨

`현대홈쇼핑/현대Hmallord` 를 "판독 오염" 으로 지목했으나 **발행물 원문 자체의 오타**였다.
executor 가 `fig10.png` 를 4배 확대 판독해 확인했고, 원자료를 수정하지 않은 채 canonical 층에서만 흡수했다.

### 4-3. 감사 주장이 오케스트레이터에게 기각됨

ssot 이 C002 산출물을 "15 panel / 262행" 으로 스팟체크했다. 고정 트리에서 직접 재계산해
**17 panel / 261행** 을 확인하고 `sum(n_metrics × rows_extracted) = 261` 정합까지 검증해 기각했다.

### 4-4. 두 감사가 같은 결함을 반대편에서 도출

| 감사 | finding | 각도 |
|---|---|---|
| ssot | `coupang-cross-domain-merge-rule-inconsistent` | 쿠팡을 **합친 것**의 부정합 |
| adversarial | `duplicate-web-collection-targets-naver-gmarket` | 네이버·G마켓을 **분리한 것**의 부작용 |

동일 결함의 양면이었다. → `measurement_entity` / `web_target` 2층 분리로 동시 해소.

### 4-5. 오케스트레이터가 제공한 근거의 오류

내가 감사에 넘긴 EV-2 드리프트 3개를 전부 음수로 적었는데 **카카오톡만 `+0.15%`** 였다.
EV-6 의 "문서 속성 전부 None" 도 과장이었다(`created`/`modified` 는 존재).
부정확한 근거가 오히려 **더 약한 주장**을 만들고 있었다 — 부호가 갈린다는 사실이 "비일관 드리프트" 의 최강 형태다.

### 4-6. 내 지시서의 오류

review queue 를 5건이라 지시했으나 실제 **7건**이었다. `state.json` 은 7인데 요약 표가 3줄(=5건)만 적었고
그것을 그대로 넘겼다. executor 가 7건 전부 판정했다.

---

## 5. 검증 방법론에서 확립된 원칙

### 5-1. 검증의 한쪽 끝은 원본이어야 한다

"원문 index 11개 절과 1:1 대조가 코드로 강제된다" 는 주장이 실제로는
`index_from_source`(파생 A) 와 `source_section_title`(파생 B) 의 일치였다.
**둘 다 같은 방식으로 원문에서 벗어나면 통과한다.** 실제로 11개 절 전부 그랬다.

→ 테스트의 한쪽 끝을 `raw/wiseapp933_text.txt` 파싱으로 교체. 감사가 코드로 확인.

### 5-2. U+00A0 — verbatim 의 진짜 의미

원문 INDEX 는 Chapter 1 세 절만 `세대` 뒤에 U+00A0 를 쓰고 Ch2~4 여덟 절은 쓰지 않는다.
**그 비대칭까지 그대로** 복원했고, ssot 이 원문에 94회 실재하며 정확히 그 세 절에만 있음을 독립 확인했다.

```
C009  SAME  0 / MISMATCH 11
C011  SAME 15 / MISMATCH  0
```

### 5-3. `pytest PASS` 는 연구무결성 PASS 가 아니다

- `matches_existing_c002_output` 이 실제 비교가 아니라 `existing.exists()` 였다 — **통과 위장**
- 감사관이 **반례를 주입**했다: naver `member_domains` 순서만 뒤집기(집합 불변), 큐에서 항목 빼기,
  인용 위조, 근거 그대로 두고 판정값만 뒤집기 → 신규 테스트가 잡음
- 다만 **빌드 스크립트는 셋 다 `exit 0` 으로 통과**시켰고, 잡은 것도 구조 규칙이 아니라
  `EXPECTED_QUEUE_SIZE=7` 하드코딩 리터럴이다. 게이트 우회 불가는 현재 테스트 구성에 의존한다.

### 5-4. 게이트 플래그를 손으로 쓸 수 있으면 게이트가 아니다

`needs_human_review` 가 손입력 bool 이라 **판정 없이 False 로 바꾸는 것만으로 큐를 비울 수 있었다.**
→ 파생값 전환(`= review_decision == 'UNRESOLVED'`).
다만 **큐에 오르는지 자체**는 여전히 손입력이라 C013 에서 구조 도출로 바꾸는 중이다.

### 5-5. 확인 불가를 확정으로 바꾸지 않는다

`SYSTEM_APP_CANDIDATE` 11건의 근거가 하드코딩 dict 에 "…로 알려져 있다" 형식이었고 인용이 0건이었다.
적대적 감사가 임의성의 증거를 찾았다 — **같은 GMS 번들인데 Google 포토는 찍고 YouTube 는 안 찍었다.**
→ `NOT_ASSESSED` 로 되돌리고 가설은 `_researcher_priors/` 로 분리(write-only, 읽는 코드 0건).

---

## 6. 하네스가 관리자 자신을 세 번 잡았다

| # | 사건 | 탐지 | 결과 |
|---|---|---|---|
| P0 #1 | cwd 오염으로 **Pilot 브랜치에 커밋** | watchdog `P0_VIOLATION pilot branch moved` | `reset --mixed` 원복, 원격 미오염 |
| P0 #2 | **exec 워크트리에 커밋** — executor 진행 중 작업 16파일을 삼킴 | watchdog `AUDIT_REQUIRED` + `AUDIT_LAG` | 원복, 작업 17파일 전량 보존 |
| P0 #3 | executor 가 `ruff format` 전체 실행 → **Pilot 파일 수정** | **watchdog 놓침 — 수동 점검으로 발견** | 원복, executor 경고, watchdog v2 |

**#3 이 가장 중요하다.** 기존 watchdog 의 Pilot 워크트리 검사가 **메인 워크트리만** 봤고,
4개 에이전트 워크트리는 감시 범위 밖이었다.

→ watchdog v2 는 4개 워크트리 전부를 감시한다.
→ **감시 범위가 실행 범위보다 좁으면 감시가 아니다.**

#1 의 예방책("절대경로 사용")이 파일 경로에만 적용되고 git 명령에는 적용되지 않아 #2 가 재발했다.
**예방책이 근본원인의 일부만 덮으면 재발한다.**

---

## 7. 보호 장치 현황

| 층 | 내용 | 검증 |
|---|---|---|
| server-side | main: force-push·삭제 금지, linear history | gh CLI 설정 완료 |
| server-side | Pilot: `lock_branch=true` + `enforce_admins=true` | 완전 잠금 |
| client hook | main 은 `LA_PROMOTION` 없이 차단, Pilot 무조건 차단 | 다른 SHA push 시도 → **실제 BLOCKED** |
| promotion script | 6개 검사 중복 수행 | C011 SHA 로 시도 → **exit 1 차단 확인** |
| watchdog v2 | Pilot(4워크트리)·E001·audit lag·권위변조·감사착지 | 120초 주기 |
| audit lag | `MAX_UNAUDITED_EXEC_CYCLES = 1` | state + watchdog 이중 |

---

## 8. 부채 현황 (v4.0 §2 triage)

목적함수가 `ZERO FINDINGS` 가 아니라 **`ZERO E001-BLOCKING FINDINGS`** 로 바뀌었다.

| 분류 | 수 | 처리 |
|---|---:|---|
| `E001_BLOCKING` | 6 | C013 처리중 4 + Bundle C 2 |
| `POST_E001_DEBT` | 9 | READY 선언을 막지 않음 |
| `PUBLICATION_DEBT` | 6 | 기사 작성 시 |
| `CLOSED` | 3 | 감사 검증 완료 |

**Bundle C 로 넘긴 2건이 진짜 증거무결성 문제다.**

- `verify_run` 이 **심링크로 relpath 가드를 우회**하고 mode 를 오라벨한다
- `.gitignore` 가 `evidence/*/dom/` **한 단계만** 잡아 `evidence/<run>/har/*` 를 놓친다

---

## 9. 지금 말할 수 있는 것 / 없는 것

### 말할 수 있음

- Wiseapp 933 원문을 두 경로로 취득해 무결성을 유지한 채 261행으로 구조화했다
- 원문의 조작적 정의(측정기간·모수 조건·카드결제 한계)를 확보했다
- 인증 이력 2,283건 전수 스냅샷을 완결성 게이트와 함께 확보했다
- 기존 xlsx 가 933 의 파생물이 아님을 6개 근거로 확정했다

### 말할 수 없음

- **web eligibility 판정 결과** — 71건 미판정
- **인증 도달률** — certification join 미실시
- **RQ2/RQ3 성립 여부** — 이전 NO-GO 는 철회 상태, 재산출 전
- **접근성 측정 결과 일체** — E001 미실행
- 인과·고령자 실사용성 효과·인증 효과·65+ 일반화

---

## 10. 다음 단계

```
C013 완료 → 독립감사 2건 → 재결 → PROM-003        (Bundle A 종료)
Bundle B  certification join · feasibility · RQ 생존 판정
Bundle C  measurement engine (E001_BLOCKING 2건 포함)
Bundle D  E000 스모크 → FINAL_CLOSURE_REPORT → automation HOLD
                                    ↓
                        READY_FOR_E001 에서 정지
                        Research Director GO/HOLD 요청
```

**E001 은 여전히 `PROHIBITED` 다.** 승인 없이 실행하지 않는다.
